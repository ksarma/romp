// The clocks a reply carries are taken before the bytes they describe are read (plans/file-review.md,
// decision 50). The panel baselines its poll on the reply's `storeMtimeNs` and `configMtimeNs` and
// refreshes when the disk's clock differs; read first and stat'ed at reply time, a write landing
// between the two handed the panel the writer's clock over the earlier bytes, so the poll saw
// nothing to refresh and the panel showed a store one write behind until something else moved it
// (the blind poll: 11 misses in 147 rounds of the lost-update probe, 2026-09-09). The host now
// takes the clock first (loadOrRefuse, loadFile, configStatus; set-tracked's own write; a prune
// sets the sidecar's to null) and the reply carries that (clockOf), never a stat now.
// The window is opened here by interposing fs.readFileSync in this process: the first read of the
// sidecar (or the config) lands a NEWER file on disk, with a later mtime, and every read answers the
// bytes as they were, so the reply's store is the earlier state. The invariant: the clock the reply
// carries is never newer than the bytes it carries, so it differs from the disk's after the write.
// The host module is imported and driven in-process through handle(), the same code the kernel's
// child runs; FILE_COMMENTS_HOME points "~" at the scratch world. Synthetic ids and text only.
// Run: node --test tools/file-comments-host-clocks.test.mjs
import { test, before, after, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { storePathFor, configPathFor, saveStore, writeTrackedPaths, recordAgentEdit } from '../vendor/track-changents/store-io.mjs';
import { handle, statNs } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const SID = '11111111-2222-3333-4444-555555555555';
const T0 = 1757145600000;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-clocks-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

const realRead = fs.readFileSync;
const realUnlink = fs.unlinkSync;
const homeBefore = process.env.FILE_COMMENTS_HOME;
afterEach(() => {
  fs.readFileSync = realRead;
  fs.unlinkSync = realUnlink;
  if (homeBefore === undefined) delete process.env.FILE_COMMENTS_HOME; else process.env.FILE_COMMENTS_HOME = homeBefore;
});

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  process.env.FILE_COMMENTS_HOME = home;
  const report = path.join(root, 'docs', 'report.md');
  return { home, root, report, text: fs.readFileSync(report, 'utf8'), storePath: storePathFor(root, report), configPath: configPathFor(root) };
}
const comment = (id, body) => ({ id, author: 'you', ts: T0, body, replies: [], resolved: false });

// A file's bytes as they are now, and a newer version of it landed on disk with a later mtime; every
// later read of that path through fs.readFileSync answers the earlier bytes. `landAfterRead` = the
// write lands right after the Nth read of the path (1 = the first), the shape of a writer's rename
// arriving between a reader's read and its stat.
function interpose(p, newer, landAfterRead) {
  const before = realRead.call(fs, p);
  const later = (Date.now() + 5000) / 1000;
  let reads = 0;
  let landedAt = null;
  fs.readFileSync = function (q, ...rest) {
    if (typeof q === 'string' && path.resolve(q) === p) {
      reads++;
      if (reads === landAfterRead) {
        fs.writeFileSync(p, newer);
        fs.utimesSync(p, later, later);
        landedAt = statNs(p);
      }
      const enc = rest[0] && (typeof rest[0] === 'string' ? rest[0] : rest[0].encoding);
      return enc ? before.toString(enc) : Buffer.from(before);
    }
    return realRead.call(fs, q, ...rest);
  };
  return { clockBefore: statNs(p), landed: () => landedAt };
}

test('status: a sidecar written right after the host read it; the reply carries the clock of the bytes it got, not the newer disk\'s', () => {
  const w = world();
  saveStore(w.root, w.storePath, { v: 3, path: 'docs/report.md', suggestions: [], comments: [comment(`${T0}-4`, 'Which figure?')] }, w.text);
  const newer = JSON.stringify({ ...JSON.parse(realRead.call(fs, w.storePath, 'utf8')), comments: [comment(`${T0}-4`, 'Which figure?'), comment(`${T0 + 1}-40`, 'Landed after the read.')] });
  const { clockBefore, landed } = interpose(w.storePath, newer, 1);
  const r = handle({ verb: 'status', path: w.report, args: {} });
  assert.equal(r.ok, true);
  assert.ok(landed(), 'the newer sidecar landed during the verb');
  assert.notEqual(landed(), clockBefore, 'with a later mtime');
  assert.equal(r.store.comments.length, 1, 'the reply\'s store is the bytes the host read');
  const carriesTheWrite = r.store.comments.some((c) => c.body === 'Landed after the read.');
  assert.ok(carriesTheWrite || r.storeMtimeNs !== statNs(w.storePath),
    `the reply carries the write or a clock that differs from the disk's; got the disk's clock ${r.storeMtimeNs} over bytes without the write`);
  assert.equal(r.storeMtimeNs, clockBefore, 'the clock of the bytes it got');
});

test('comment: the read-back after the host\'s own rename is clocked before it is read, so a write landing in that instant is not baselined blind', () => {
  const w = world();
  saveStore(w.root, w.storePath, { v: 3, path: 'docs/report.md', suggestions: [], comments: [comment(`${T0}-4`, 'Which figure?')] }, w.text);
  const st = handle({ verb: 'status', path: w.report, args: {} });
  // the host reads the sidecar twice in a comment: the load, and the read-back after its rename; the
  // newer file lands right after the second read, answering the host's own bytes to it
  const newer = JSON.stringify({ ...JSON.parse(realRead.call(fs, w.storePath, 'utf8')), comments: [comment(`${T0}-4`, 'Which figure?'), comment(`${T0 + 1}-40`, 'Landed after the read.')] });
  const { landed } = interpose(w.storePath, newer, 2);
  // the interposer answers the pre-comment bytes to every read of the sidecar, including the host's read-back, so
  // the reply's store is the loaded one plus nothing; what this test judges is the CLOCK beside those bytes
  const r = handle({ verb: 'comment', path: w.report, args: { note: 'Whole-file note.' }, fence: { storeMtimeNs: st.storeMtimeNs } });
  assert.equal(r.ok, true, r.error);
  assert.ok(landed(), 'the newer sidecar landed during the read-back');
  const carriesTheWrite = r.store.comments.some((c) => c.body === 'Landed after the read.');
  assert.ok(carriesTheWrite || r.storeMtimeNs !== statNs(w.storePath),
    `the reply carries the write or a clock that differs from the disk's; got the disk's clock ${r.storeMtimeNs}`);
});

test('status: a config written right after the host read it; the reply\'s configMtimeNs is the clock of the config it judged and answered from', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const newer = JSON.stringify({ v: 2, tracked: [] }, null, 2) + '\n';
  const { clockBefore, landed } = interpose(w.configPath, newer, 1);
  const r = handle({ verb: 'status', path: w.report, args: {} });
  assert.equal(r.ok, true);
  assert.ok(landed(), 'the newer config landed during the verb');
  assert.deepEqual(r.trackedBy, { kind: 'file', entry: 'docs/report.md' }, 'the verdict is from the bytes the host read');
  assert.notEqual(r.configMtimeNs, statNs(w.configPath), 'so the clock is not the newer disk\'s');
  assert.equal(r.configMtimeNs, clockBefore);
});

test('accept-all that prunes the sidecar: the reply says absent with a null clock, even when a new sidecar lands in the instant after the prune', () => {
  const w = world();
  const from = w.text.indexOf('cut');
  const text1 = w.text.replace('cut', 'reduced');
  fs.writeFileSync(w.report, text1);
  recordAgentEdit(w.root, w.report, w.text, { from, to: from + 3, insert: 'reduced' }, 'api', T0, SID);
  const st = handle({ verb: 'status', path: w.report, args: {} });
  assert.equal(st.hunks.length, 1);
  // right after the prune unlinks the emptied sidecar, another writer's lands under the name
  fs.unlinkSync = function (q, ...rest) {
    const out = realUnlink.call(fs, q, ...rest);
    if (typeof q === 'string' && path.resolve(q) === w.storePath) {
      fs.writeFileSync(w.storePath, JSON.stringify({ v: 3, path: 'docs/report.md', suggestions: [], comments: [comment(`${T0 + 2}-4`, 'After the prune.')] }));
    }
    return out;
  };
  const r = handle({ verb: 'accept-all', path: w.report, args: {}, fence: { storeMtimeNs: st.storeMtimeNs } });
  assert.equal(r.ok, true, r.error);
  assert.equal(r.store, null, 'the reply\'s store is the pruned one');
  assert.equal(r.storeMtimeNs, null, 'and so is its clock: the disk\'s later sidecar is for the next poll to find');
  assert.ok(fs.existsSync(w.storePath), 'the later writer\'s sidecar stands');
  assert.notEqual(statNs(w.storePath), null);
});

test('the source: every reader of the two files takes its clock first, the reply never stats them, and a verb without a clock is a program error', () => {
  const src = fs.readFileSync(HOST, 'utf8');
  const fn = (name) => {
    const i = src.indexOf(`\nfunction ${name}(`);
    assert.ok(i >= 0, name);
    const j = src.indexOf('\n}\n', i);
    return src.slice(i, j + 3);
  };
  assert.match(fn('loadOrRefuse'), /^\nfunction loadOrRefuse\(ctx, paths, text\) \{\n  ctx\.storeClock = statNs\(paths\.storePath\);/, 'the sidecar\'s clock is the first statement of its loader');
  assert.match(fn('configStatus'), /^\nfunction configStatus\(ctx, paths\) \{\n  ctx\.configClock = statNs\(paths\.configPath\);/, 'the config\'s clock is the first statement of its reader');
  assert.match(fn('loadFile'), /if \(paths\) ctx\.storeClock = statNs\(paths\.storePath\);[^\n]*\n  const read = ctx\.args\.baseline === true \|\| \(paths != null && ctx\.storeClock != null\);/, 'loadFile decides from the clock, not a second stat');
  assert.match(fn('afterDecision'), /if \(pruneIfClean\(paths\.storePath, store\)\) \{\n    ctx\.storeClock = null;/, 'a prune clocks the sidecar absent');
  const reply = fn('reply');
  assert.equal(/statNs\(/.test(reply), false, 'the reply stats nothing under .trackchanges/');
  assert.match(reply, /storeMtimeNs: paths \? clockOf\(ctx, 'storeClock', paths\.storePath\) : null,\n\s*configMtimeNs: paths \? clockOf\(ctx, 'configClock', paths\.configPath\) : null,/);
  assert.match(fn('clockOf'), /if \(!\(key in ctx\)\) throw new Error\(/, 'no clock: a program error, never a stat now');
  assert.equal((src.match(/configStatus\(paths\)/g) || []).length, 0, 'no reader of the config bypasses the clock');
});
