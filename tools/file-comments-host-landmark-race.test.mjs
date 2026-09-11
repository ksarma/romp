// Two first writes on one loose file at once (plans/file-review.md, decision 49). A file with no
// landmark above it gets its `.trackchanges/` from its first comment or tracking toggle
// (createLandmark), and the kernel runs every host verb on its own thread, so two clients' first
// writes, or one client's comment and its toggle, race for the landmark. The lock cannot be taken
// before the landmark exists, so the loose path takes it after createLandmark and checks its ""
// fence again under it: the second writer meets the first's sidecar (store-moved) or config
// (config-moved), which the panel re-reads and retries. That holds for BOTH orderings the race has:
//   * the first's whole write landed before the second looked at the landmark's name: createLandmark
//     finds a directory there and builds nothing over it (before: it refused `unreadable` with
//     "already exists as a directory, not a directory" and told the person to remove the folder that
//     now held the other writer's comment; the panel never retries `unreadable`);
//   * the first's mkdir fell between the second's look and its own mkdir (a no-op over the directory):
//     the "" fence re-check under the lock is what refuses, and without it the second's one-comment
//     store would be renamed over the first's, losing the first comment with no refusal.
// A comment and a toggle at once both land: the comment's fence is the sidecar's and the toggle's is
// the config's. The last case runs the real host twice at once in a loop: no reply is ever
// `unreadable`, and both comments are on disk after the panel's retry.
// The host module is driven in-process through handle() with fs.lstatSync or fs.mkdirSync interposed
// to land the other writer's files at the exact step; FILE_COMMENTS_HOME points "~" at the scratch
// world. Synthetic ids and text only.
// Run: node --test tools/file-comments-host-landmark-race.test.mjs
import { test, before, after, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { storePathFor, configPathFor, saveStore, findVaultRoot, readConfig, STORE_VERSION } from '../vendor/track-changents/store-io.mjs';
import { handle, Refusal, statNs } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const T0 = 1757145600000;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-landmark-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

const realLstat = fs.lstatSync;
const realMkdir = fs.mkdirSync;
const homeBefore = process.env.FILE_COMMENTS_HOME;
afterEach(() => {
  fs.lstatSync = realLstat;
  fs.mkdirSync = realMkdir;
  if (homeBefore === undefined) delete process.env.FILE_COMMENTS_HOME; else process.env.FILE_COMMENTS_HOME = homeBefore;
});

// <scratch>/wN/home/loose/report.md: a file with no landmark above it (no .git, .obsidian or
// .trackchanges in any ancestor), and a sibling for the toggle cases.
let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const looseDir = path.join(home, 'loose');
  fs.mkdirSync(looseDir, { recursive: true });
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(looseDir, 'report.md'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(looseDir, 'other.md'));
  const loose = path.join(looseDir, 'report.md');
  assert.equal(findVaultRoot(loose), null, `the scratch directory ${SCRATCH} has a landmark above it; these cases need a loose file`);
  process.env.FILE_COMMENTS_HOME = home;
  return {
    home, looseDir, loose,
    other: path.join(looseDir, 'other.md'),
    mark: path.join(looseDir, '.trackchanges'),
    storePath: storePathFor(looseDir, loose),
    configPath: configPathFor(looseDir),
    text: fs.readFileSync(loose, 'utf8'),
  };
}
const readSidecar = (sp) => JSON.parse(fs.readFileSync(sp, 'utf8'));
const bodies = (sp) => readSidecar(sp).comments.map((c) => c.body);

// The other writer's whole first write, as the disk holds it once it has landed: a first comment
// (the landmark and a one-comment sidecar, saveStore's bytes) or a first toggle on the sibling
// (the landmark and config.json with the sibling's entry).
function otherFirstComment(w) {
  fs.mkdirSync(w.mark, { recursive: true });
  const store = { v: STORE_VERSION, path: 'report.md', suggestions: [], comments: [{ id: '1-0', author: 'you', ts: T0, body: 'The first comment.', replies: [], resolved: false }] };
  saveStore(w.looseDir, w.storePath, store, w.text);
}
function otherFirstToggle(w) {
  fs.mkdirSync(w.mark, { recursive: true });
  fs.writeFileSync(w.configPath, JSON.stringify({ v: 2, tracked: ['other.md'] }, null, 2) + '\n');
}

// The other writer's write lands between this verb's root discovery (findVaultRoot saw nothing)
// and createLandmark's look at the landmark's name: the lstat finds a directory.
function landBeforeLstat(w, land) {
  let done = false;
  fs.lstatSync = function (p, ...rest) {
    if (!done && typeof p === 'string' && path.resolve(p) === w.mark) { done = true; land(); }
    return realLstat.call(fs, p, ...rest);
  };
}
// ... lands between that look (nothing there) and this verb's own mkdir, which is a no-op over
// the directory: only the "" fence re-check under the lock can meet the other writer.
function landInsideMkdir(w, land) {
  let done = false;
  fs.mkdirSync = function (p, ...rest) {
    if (!done && typeof p === 'string' && path.resolve(p) === w.mark) { done = true; land(); }
    return realMkdir.call(fs, p, ...rest);
  };
}

function refusal(fn) {
  try { fn(); } catch (e) { if (e instanceof Refusal) return e; throw e; }
  return assert.fail('expected a refusal');
}
const status = (p) => handle({ verb: 'status', path: p, args: {} });
const firstComment = (w, fence) => handle({ verb: 'comment', path: w.loose, args: { note: 'Whole-file note.' }, fence: { storeMtimeNs: fence == null ? '' : fence } });
const firstToggle = (w, fence) => handle({ verb: 'set-tracked', path: w.loose, args: { on: true, scope: 'file' }, fence: { configMtimeNs: fence == null ? '' : fence } });

// ── two first comments ──────────────────────────────────────────────

for (const [when, interpose] of [['landed before this comment looked at the landmark', landBeforeLstat], ['made its landmark inside this comment\'s mkdir', landInsideMkdir]]) {
  test(`two first comments on a loose file: the other's ${when}; this one refuses store-moved, the first comment stays, and the retry lands both`, () => {
    const w = world();
    interpose(w, () => otherFirstComment(w));
    const e = refusal(() => firstComment(w));
    assert.equal(e.code, 'store-moved', e.message);
    assert.match(e.message, /appeared on disk since you opened the file/);
    assert.ok(!/remove it/.test(e.message), 'no remedy that would delete the other writer\'s comment');
    assert.deepEqual(bodies(w.storePath), ['The first comment.'], 'the first comment is on disk, alone');
    assert.equal(fs.existsSync(`${w.storePath}.lock`), false, 'the lock is released');
    assert.ok(fs.statSync(w.mark).isDirectory(), 'the landmark stands');
    // the panel's one retry, from a fresh read
    fs.lstatSync = realLstat;
    fs.mkdirSync = realMkdir;
    const st = status(w.loose);
    assert.equal(st.root, w.looseDir, 'the landmark is the root from now on');
    assert.equal(st.storeMtimeNs, statNs(w.storePath));
    const r = firstComment(w, st.storeMtimeNs);
    assert.equal(r.ok, true);
    assert.deepEqual(bodies(w.storePath), ['The first comment.', 'Whole-file note.'], 'both writes survive');
    assert.equal(r.storeMtimeNs, statNs(w.storePath));
  });
}

// ── two first toggles ───────────────────────────────────────────────

for (const [when, interpose] of [['landed before this toggle looked at the landmark', landBeforeLstat], ['made its landmark inside this toggle\'s mkdir', landInsideMkdir]]) {
  test(`two first toggles under one loose directory: the sibling's ${when}; this one refuses config-moved, the sibling's entry stays, and the retry lands both`, () => {
    const w = world();
    interpose(w, () => otherFirstToggle(w));
    const e = refusal(() => firstToggle(w));
    assert.equal(e.code, 'config-moved', e.message);
    assert.match(e.message, /appeared on disk since you opened the file/);
    assert.ok(!/remove it/.test(e.message));
    assert.deepEqual(readConfig(w.looseDir), { v: 2, tracked: ['other.md'] }, 'the sibling\'s toggle is on disk, alone');
    assert.equal(fs.existsSync(`${w.configPath}.lock`), false, 'the lock is released');
    fs.lstatSync = realLstat;
    fs.mkdirSync = realMkdir;
    const st = status(w.loose);
    assert.equal(st.root, w.looseDir);
    assert.equal(st.configMtimeNs, statNs(w.configPath));
    const r = firstToggle(w, st.configMtimeNs);
    assert.equal(r.ok, true);
    assert.deepEqual(readConfig(w.looseDir), { v: 2, tracked: ['other.md', 'report.md'] }, 'both toggles survive');
    assert.deepEqual(r.trackedBy, { kind: 'file', entry: 'report.md' });
    assert.equal(r.configMtimeNs, statNs(w.configPath));
  });
}

// ── a comment and a toggle ──────────────────────────────────────────

test('a first comment whose landmark a first toggle made a moment earlier lands: the toggle\'s config is not the comment\'s fence, and both are on disk', () => {
  const w = world();
  landBeforeLstat(w, () => otherFirstToggle(w));
  const r = firstComment(w);
  assert.equal(r.ok, true);
  assert.equal(r.root, w.looseDir);
  assert.deepEqual(bodies(w.storePath), ['Whole-file note.']);
  assert.deepEqual(readConfig(w.looseDir), { v: 2, tracked: ['other.md'] }, 'the toggle\'s write stands');
  assert.equal(r.storeMtimeNs, statNs(w.storePath));
  assert.equal(fs.existsSync(`${w.storePath}.lock`), false);
});

test('a first toggle whose landmark a first comment made a moment earlier lands: the comment\'s sidecar is not the toggle\'s fence, and both are on disk', () => {
  const w = world();
  landBeforeLstat(w, () => otherFirstComment(w));
  const r = firstToggle(w);
  assert.equal(r.ok, true);
  assert.equal(r.root, w.looseDir);
  assert.deepEqual(readConfig(w.looseDir), { v: 2, tracked: ['report.md'] });
  assert.deepEqual(bodies(w.storePath), ['The first comment.'], 'the comment stands');
  assert.deepEqual(r.trackedBy, { kind: 'file', entry: 'report.md' });
  assert.equal(r.configMtimeNs, statNs(w.configPath));
  assert.equal(fs.existsSync(`${w.configPath}.lock`), false);
});

// ── what still refuses ──────────────────────────────────────────────

test('a directory at the landmark\'s name is built over, a link to nothing is not: the refusal stays for the link and never names a directory', () => {
  const w = world();
  fs.symlinkSync(path.join(w.home, 'nowhere'), w.mark);
  const e = refusal(() => firstComment(w));
  assert.equal(e.code, 'unreadable');
  assert.match(e.message, /already exists as a symbolic link to nothing, not a directory/);
  assert.ok(fs.lstatSync(w.mark).isSymbolicLink(), 'neither followed nor replaced');
  fs.unlinkSync(w.mark);
  // the same verb over a directory that appeared after its root discovery (the case above) never
  // says "a directory, not a directory"
  landBeforeLstat(w, () => fs.mkdirSync(w.mark));
  const r = firstComment(w);
  assert.equal(r.ok, true, 'an empty directory another first write made is the landmark');
  assert.deepEqual(bodies(w.storePath), ['Whole-file note.']);
});

// ── the real host, twice at once ────────────────────────────────────

function run(w, req) {
  return new Promise((resolve, reject) => {
    const env = { ...process.env, FILE_COMMENTS_HOME: w.home };
    delete env.TRACKCHANGES_ROOT;
    delete env.ROMP_SID;
    delete env.ROMP_SESSION_NAME;
    const child = spawn(process.execPath, [HOST], { env });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8'); child.stdout.on('data', (c) => { stdout += c; });
    child.stderr.setEncoding('utf8'); child.stderr.on('data', (c) => { stderr += c; });
    child.on('error', reject);
    child.on('close', (code) => {
      let json = null;
      try { json = JSON.parse(stdout); } catch { json = null; }
      resolve({ code, stdout, stderr, json });
    });
    child.stdin.end(JSON.stringify(req));
  });
}

test('two host processes each send a first comment on the same loose file at once, in a loop: every reply is ok or a moved fence, never unreadable, and the retry lands both', async () => {
  const ROUNDS = 6;
  const seen = new Set();
  for (let round = 0; round < ROUNDS; round++) {
    const w = world();
    const notes = ['First note.', 'Second note.'];
    const replies = await Promise.all(notes.map((note) => run(w, { verb: 'comment', path: w.loose, args: { note }, fence: { storeMtimeNs: '' } })));
    for (const r of replies) {
      assert.equal(r.code, 0, `round ${round}: exit ${r.code}: ${r.stderr}`);
      assert.ok(r.json, `round ${round}: ${r.stdout}`);
      if (r.json.ok) { seen.add('ok'); continue; }
      seen.add(r.json.code);
      assert.ok(r.json.code === 'store-moved' || r.json.code === 'busy', `round ${round}: refused ${r.json.code}: ${r.json.error}`);
    }
    assert.ok(replies.some((r) => r.json.ok), `round ${round}: one first comment lands`);
    for (let i = 0; i < notes.length; i++) {
      if (replies[i].json.ok) continue;
      const st = await run(w, { verb: 'status', path: w.loose, args: {} });
      assert.equal(st.json && st.json.ok, true, st.stdout + st.stderr);
      const again = await run(w, { verb: 'comment', path: w.loose, args: { note: notes[i] }, fence: { storeMtimeNs: st.json.storeMtimeNs == null ? '' : st.json.storeMtimeNs } });
      assert.equal(again.json && again.json.ok, true, `round ${round}: the retry: ${again.stdout}${again.stderr}`);
    }
    assert.deepEqual(bodies(w.storePath).sort(), notes.slice().sort(), `round ${round}: both comments are on disk`);
    assert.equal(fs.existsSync(`${w.storePath}.lock`), false);
  }
  assert.ok(seen.has('ok'), `outcomes seen: ${[...seen].join(', ')}`);
});
