// Pins for tools/file-comments-host.mjs from the Slice 5 review (plans/file-review.md, "The
// comments log", "Security posture", "Consent, trace, routing"):
//   * once a verb's primary write has landed, nothing after it fails the verb — a comments-log
//     append that fails, or a log that cannot be read back, is reported in the reply (`logged`,
//     `logWarning`) on an ok reply that carries the new mtimes, so the kernel still traces the
//     write to the session and the client's fences are right; a `status` on the same file still
//     fails loudly;
//   * nothing is written on a client's word that the kernel cannot carry back in one reply
//     (REPLY_MAX_BYTES, the kernel's _FILE_COMMENTS_REPLY_MAX): an oversized record, decision or
//     note refuses `too-large` before any write;
//   * `save` refuses what the kernel's saveFile refuses — a name outside the viewer's text scope
//     (TEXT_EXT, TEXT_NAMES, mirrored from kernel.py) and a file past the 2 MB cap on disk. The
//     NAME rule is save's alone: reject and reject-all write back only what the sidecar recorded, so
//     they keep Slice 2's scope, every tracked UTF-8 file whatever its name (the review, round 3;
//     the full contract is pinned in file-comments-host-scope.test.mjs). The SIZE cap is every
//     file-writing verb's;
//   * a path inside .trackchanges/ is never logged, and `save` logs only a file that already has a
//     sidecar, a log, or a tracked flag.
// Same hermetic harness as file-comments-host-save.test.mjs: the synthetic `notes-api` world under
// a scratch directory, the script driven as the kernel drives it, every change recorded by the REAL
// vendored track-edit. Run: node --test tools/file-comments-host-landed.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { storePathFor, writeTrackedPaths } from '../vendor/track-changents/store-io.mjs';
import {
  handle, statNs, logPathFor, isTextPath, underTrackchanges, human,
  TEXT_MAX_BYTES, REPLY_MAX_BYTES, TEXT_EXT, TEXT_NAMES, TRACKCHANGES_DIR,
} from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';
const MB = 1024 * 1024;
// Directory and file modes mean nothing to root, so the permission cases skip there.
const ROOT_USER = typeof process.getuid === 'function' && process.getuid() === 0;
const skipAsRoot = { skip: ROOT_USER ? 'root ignores file modes' : false };

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-landed-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  fs.copyFileSync(path.join(FIX, 'index.md'), path.join(root, 'index.md'));
  const looseDir = path.join(home, 'loose');
  fs.mkdirSync(looseDir);
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(looseDir, 'report.md'));
  return {
    home, root, looseDir,
    report: path.join(root, 'docs', 'report.md'),
    index: path.join(root, 'index.md'),
    loose: path.join(looseDir, 'report.md'),
    text: fs.readFileSync(path.join(FIX, 'report.md'), 'utf8'),
  };
}

function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home, ...(extra || {}) };
  delete e.TRACKCHANGES_ROOT;
  if (!extra || !('ROMP_SID' in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
  return e;
}
function host(w, req) {
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w), maxBuffer: 256 * MB });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  return { code: r.status, stdout: r.stdout, stderr: r.stderr, json };
}
function ok(w, req) {
  const r = host(w, req);
  assert.equal(r.code, 0, `exit ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === true, `expected ok:true, got ${r.stdout}`);
  assert.equal(r.json.verb, req.verb);
  return r.json;
}
function refused(w, req, code) {
  const r = host(w, req);
  assert.equal(r.code, 0, `a refusal exits 0; got ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === false, `expected ok:false, got ${r.stdout}`);
  assert.equal(r.json.code, code, r.json.error);
  assert.equal(typeof r.json.error, 'string');
  assert.equal(r.json.error.includes(w.home), false, `home path leaked: ${r.json.error}`);
  return r.json;
}
function cli(w, name, args) {
  return spawnSync(process.execPath, [path.join(VENDOR, 'cli', `track-${name}.mjs`), ...args],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
}
function cliOk(w, name, args) {
  const r = cli(w, name, args);
  assert.equal(r.status, 0, `track-${name} failed: ${r.stderr}`);
  return r;
}
function status(w, file, args) { return ok(w, { verb: 'status', path: file, args: args || {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function fileFenceFor(st) { return { ...fenceFor(st), fileMtimeNs: st.fileMtimeNs }; }
function edit(w, file, oldText, newText) {
  cliOk(w, 'edit', ['--file', file, '--old', oldText, '--new', newText]);
  return status(w, file);
}
function saveReq(file, st, content, suggestions, accepted, rejected) {
  return { verb: 'save', path: file, args: { content, suggestions, accepted: accepted || [], rejected: rejected || [] }, fence: fileFenceFor(st) };
}
function typed(text, records, from, to, insert) {
  return { content: text.slice(0, from) + insert + text.slice(to), records: engine.ingestHumanChanges(records, [{ from, to, insert }]) };
}
function fileBytes(p) { try { return fs.readFileSync(p); } catch { return null; } }
function readLogLines(lp) { return fs.readFileSync(lp, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)); }
function fits(text, h) { return text.slice(h.curFrom, h.curTo) === h.newText; }
// The disk as a refused verb must leave it: the file, the sidecar and the log byte for byte.
function snapshot(w, file) {
  const sp = storePathFor(w.root, file);
  return { file: fileBytes(file), sidecar: fileBytes(sp), log: fileBytes(logPathFor(sp)), ino: fs.statSync(file).ino };
}
function untouched(w, file, before) {
  const now = snapshot(w, file);
  assert.deepEqual(now.file, before.file, 'the file is untouched');
  assert.equal(now.ino, before.ino, 'the file was not replaced');
  assert.deepEqual(now.sidecar, before.sidecar, 'the sidecar is untouched');
  assert.deepEqual(now.log, before.log, 'the log is untouched');
}
// A tracked file with one pending change and its comments log on disk (the tracking toggle wrote a
// set-tracked entry), the state every landed case starts from.
function trackedWithChange(w) {
  const s0 = status(w, w.report);
  ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: { configMtimeNs: s0.configMtimeNs == null ? '' : s0.configMtimeNs } });
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const lp = logPathFor(st.storePath);
  assert.deepEqual(readLogLines(lp).map((e) => e.kind), ['set-tracked']);
  return { st, lp, cur: fs.readFileSync(w.report, 'utf8') };
}

// ── a landed write is never reported as a failure ───────────────────

test('save: a log append that fails after the file write answers ok with logged:false and logWarning; the file, the sidecar and the mtimes are the write\'s own, and the next save with those fences succeeds', skipAsRoot, () => {
  const w = world();
  const { st, lp, cur } = trackedWithChange(w);
  const { content, records } = typed(cur, st.store.suggestions, 0, 0, 'Preface.\n');
  const logBefore = fileBytes(lp);
  fs.chmodSync(lp, 0o444);
  let r;
  try {
    r = ok(w, saveReq(w.report, st, content, records));
  } finally {
    fs.chmodSync(lp, 0o644);
  }
  // The write landed and the reply says so, in the kernel's own terms: ok, the new mtimes, the
  // remapped sidecar — and the append that failed, in words and with the OS text.
  assert.equal(fs.readFileSync(w.report, 'utf8'), content, 'the file holds the saved text');
  assert.equal(r.fileMtimeNs, statNs(w.report));
  assert.equal(r.storeMtimeNs, statNs(st.storePath));
  assert.equal(r.hunks.length, 1);
  assert.ok(fits(content, r.hunks[0]), 'the record was remapped below the preface');
  assert.equal(r.logged, false);
  assert.match(r.logWarning, /^saved, but not written to the comments log for ~\/notes-api\/docs\/report\.md: /);
  assert.match(r.logWarning, /EACCES|EPERM/);
  assert.equal(r.logWarning.includes(w.home), false, 'the warning tilde-collapses the home path');
  assert.equal(r.logWarning.includes('read back'), false, 'a readable log is read back as usual');
  // The log itself is as it was — readable, so the reply's Log is the tail on disk, not empty.
  assert.deepEqual(fileBytes(lp), logBefore);
  assert.deepEqual(r.log.map((e) => e.kind), ['set-tracked']);
  // The client applies the reply as its status: a save fenced on it goes through, and this one is
  // logged (the log is writable again) with no warning.
  const content2 = content + 'More.\n';
  const r2 = ok(w, saveReq(w.report, r, content2, r.store.suggestions));
  assert.equal(r2.logged, true);
  assert.equal('logWarning' in r2, false);
  assert.deepEqual(r2.log.map((e) => e.kind), ['set-tracked', 'edit']);
  assert.equal(fs.readFileSync(w.report, 'utf8'), content2);
});

test('a log that cannot be read refuses unreadable BEFORE any write — save and status alike — naming the log, and the disk is left as it was', skipAsRoot, () => {
  const w = world();
  const { st, lp, cur } = trackedWithChange(w);
  const { content, records } = typed(cur, st.store.suggestions, 0, 0, 'Preface.\n');
  const before = snapshot(w, w.report);
  fs.chmodSync(lp, 0o000);
  let r;
  let probe;
  try {
    r = refused(w, saveReq(w.report, st, content, records), 'unreadable');
    probe = refused(w, { verb: 'status', path: w.report, args: {} }, 'unreadable');
  } finally {
    fs.chmodSync(lp, 0o644);
  }
  // The log is the only state for what is unsent, and the reply the client applies as its status
  // derives from it: a save that could not read it refuses with nothing written, rather than
  // landing a write whose reply would report a derivation from nothing (the file stays in the
  // editor, the person fixes the log and saves again). The same disk state is a refusal for a
  // read-only verb too, not a crash the kernel would report as the helper failing.
  const shape = /^cannot read the comments log for ~\/notes-api\/docs\/report\.md \(~\/notes-api\/\.trackchanges\/docs%2Freport\.md\.comments-log\.jsonl\): .*(EACCES|EPERM).*; nothing was changed$/;
  assert.match(r.error, shape);
  assert.match(probe.error, shape);
  untouched(w, w.report, before);
  // Readable again: the log is intact and the same save goes through, logged.
  assert.deepEqual(readLogLines(lp).map((e) => e.kind), ['set-tracked']);
  const st2 = status(w, w.report);
  assert.deepEqual(st2.log.map((e) => e.kind), ['set-tracked']);
  const r2 = ok(w, saveReq(w.report, st2, content, records));
  assert.equal(r2.logged, true);
  assert.deepEqual(r2.log.map((e) => e.kind), ['set-tracked', 'edit']);
});

test('after the write lands, a sidecar or a log that cannot be read back is reported in logWarning beside the failed append, never a failure (in-process: the disk failing between the write and the reply)', () => {
  // A permission the test could set would refuse before the write (above); a disk that fails only
  // AFTER the write — a writer replacing the sidecar in the same instant, an I/O error — is driven
  // in-process through handle(), with fs failing exactly the reads that follow the write: the
  // sidecar's third read (its load, the prior bytes, then the read-back) and the log's second (the
  // estimate before the write, then the reply's), and every append.
  const w = world();
  const { st, lp, cur } = trackedWithChange(w);
  const { content, records } = typed(cur, st.store.suggestions, 0, 0, 'Preface.\n');
  const realRead = fs.readFileSync;
  const realAppend = fs.appendFileSync;
  const prevHome = process.env.FILE_COMMENTS_HOME;
  process.env.FILE_COMMENTS_HOME = w.home;
  let sidecarReads = 0;
  let logReads = 0;
  const eacces = (p) => { const e = new Error(`EACCES: permission denied, open '${p}'`); e.code = 'EACCES'; return e; };
  fs.readFileSync = function (p, ...rest) {
    if (p === st.storePath && ++sidecarReads === 3) throw eacces(p);
    if (p === lp && ++logReads === 2) throw eacces(p);
    return realRead.call(fs, p, ...rest);
  };
  fs.appendFileSync = function (p, ...rest) {
    if (p === lp) throw eacces(p);
    return realAppend.call(fs, p, ...rest);
  };
  let out;
  try {
    out = handle(saveReq(w.report, st, content, records));
  } finally {
    fs.readFileSync = realRead;
    fs.appendFileSync = realAppend;
    if (prevHome === undefined) delete process.env.FILE_COMMENTS_HOME; else process.env.FILE_COMMENTS_HOME = prevHome;
  }
  assert.equal(sidecarReads, 3, 'the read-back was the third read of the sidecar');
  assert.equal(logReads, 2, 'the reply read the log after the estimate did');
  assert.equal(out.ok, true);
  assert.equal(fs.readFileSync(w.report, 'utf8'), content, 'the file holds the saved text');
  assert.equal(out.fileMtimeNs, statNs(w.report));
  assert.equal(out.storeMtimeNs, statNs(st.storePath));
  assert.equal(out.logged, false);
  assert.match(out.logWarning, /^saved, but not written to the comments log for ~\/notes-api\/docs\/report\.md: .*EACCES/);
  assert.match(out.logWarning, /; and the comments for ~\/notes-api\/docs\/report\.md could not be read back after the write: cannot read the comments for ~\/notes-api\/docs\/report\.md \(~\/notes-api\/\.trackchanges\/docs%2Freport\.md\.json\) — reload/);
  assert.match(out.logWarning, /; and the comments log for ~\/notes-api\/docs\/report\.md could not be read back: .*EACCES/);
  assert.equal(out.logWarning.includes(w.home), false);
  assert.equal(out.logWarning.includes('nothing was changed'), false, 'a landed write never claims nothing changed');
  assert.deepEqual(out.log, []);
  assert.equal(out.logTruncated, false);
  // The records this process wrote stand in for the sidecar it could not re-read, remapped as saved.
  assert.equal(out.hunks.length, 1);
  assert.ok(fits(content, out.hunks[0]));
  assert.equal(out.store.suggestions.length, 1);
  // The disk agrees with the reply once it answers again: the same sidecar, the log as it was.
  const again = status(w, w.report);
  assert.deepEqual(again.hunks, out.hunks);
  assert.deepEqual(again.log.map((e) => e.kind), ['set-tracked']);
});

test('save: a tracked file with no log yet in a .trackchanges/ that cannot be written to (a folder entry covers it) is saved and reports the log it could not create', skipAsRoot, () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/']);
  const other = path.join(w.root, 'docs', 'other.md');
  fs.writeFileSync(other, 'Some text.\n');
  const st = status(w, other);
  assert.deepEqual(st.trackedBy, { kind: 'folder', entry: 'docs/' });
  const lp = logPathFor(st.storePath);
  assert.equal(fs.existsSync(lp), false);
  const tc = path.join(w.root, '.trackchanges');
  fs.chmodSync(tc, 0o555);
  let r;
  try {
    r = ok(w, saveReq(other, st, 'Some text.\nMore.\n', []));
  } finally {
    fs.chmodSync(tc, 0o755);
  }
  assert.equal(fs.readFileSync(other, 'utf8'), 'Some text.\nMore.\n');
  assert.equal(r.fileMtimeNs, statNs(other));
  assert.equal(r.logged, false);
  assert.match(r.logWarning, /^saved, but not written to the comments log for ~\/notes-api\/docs\/other\.md: .*(EACCES|EPERM)/);
  assert.equal(fs.existsSync(lp), false);
  assert.deepEqual(r.log, []);
});

test('reject-all and accept: a log append that fails after the write answers ok, names the decision, and still prunes the emptied sidecar', skipAsRoot, () => {
  // reject-all: the file holds the baseline, the reply carries `rejected` (the kernel traces from
  // it), and the sidecar is gone because nothing is pending.
  const w = world();
  const { st, lp, cur } = trackedWithChange(w);
  fs.chmodSync(lp, 0o444);
  let r;
  try {
    r = ok(w, { verb: 'reject-all', path: w.report, args: {}, fence: fileFenceFor(st) });
  } finally {
    fs.chmodSync(lp, 0o644);
  }
  assert.deepEqual(r.rejected, [st.hunks[0].id]);
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text, 'the file holds the baseline');
  assert.notEqual(fs.readFileSync(w.report, 'utf8'), cur);
  assert.equal(r.fileMtimeNs, statNs(w.report));
  assert.equal(r.store, null);
  assert.equal(r.storeMtimeNs, null);
  assert.equal(fs.existsSync(st.storePath), false, 'the emptied sidecar is pruned');
  assert.equal(r.logged, false);
  assert.match(r.logWarning, /^the changes were rejected, but not written to the comments log for ~\/notes-api\/docs\/report\.md: .*(EACCES|EPERM)/);
  assert.equal(r.logWarning.includes('read back'), false);
  assert.deepEqual(readLogLines(lp).map((e) => e.kind), ['set-tracked']);
  // accept: the sidecar write landed (the record is gone), the reply carries `accepted`.
  const w2 = world();
  const t2 = trackedWithChange(w2);
  fs.chmodSync(t2.lp, 0o444);
  let r2;
  try {
    r2 = ok(w2, { verb: 'accept', path: w2.report, args: { ids: [t2.st.hunks[0].id] }, fence: fenceFor(t2.st) });
  } finally {
    fs.chmodSync(t2.lp, 0o644);
  }
  assert.deepEqual(r2.accepted, [t2.st.hunks[0].id]);
  assert.equal(fs.readFileSync(w2.report, 'utf8'), t2.cur, 'accept leaves the file alone');
  assert.equal(r2.store, null);
  assert.equal(fs.existsSync(t2.st.storePath), false);
  assert.equal(r2.logged, false);
  assert.match(r2.logWarning, /^the changes were accepted, but not written to the comments log for ~\/notes-api\/docs\/report\.md: .*(EACCES|EPERM)/);
  // The happy path says logged:true and carries no warning at all.
  const w3 = world();
  const t3 = trackedWithChange(w3);
  const r3 = ok(w3, { verb: 'accept-all', path: w3.report, args: {}, fence: fenceFor(t3.st) });
  assert.equal(r3.logged, true);
  assert.equal('logWarning' in r3, false);
  assert.deepEqual(readLogLines(t3.lp).map((e) => e.kind), ['set-tracked', 'accept']);
});

test('set-tracked: a log append that fails after config.json was written answers ok with the new verdict and the warning', skipAsRoot, () => {
  const w = world();
  const s0 = status(w, w.report);
  const on = ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: { configMtimeNs: '' } });
  assert.equal(on.logged, true);
  assert.deepEqual(on.trackedBy, { kind: 'file', entry: 'docs/report.md' });
  const lp = logPathFor(storePathFor(w.root, w.report));
  fs.chmodSync(lp, 0o444);
  let off;
  try {
    off = ok(w, { verb: 'set-tracked', path: w.report, args: { on: false }, fence: { configMtimeNs: on.configMtimeNs } });
  } finally {
    fs.chmodSync(lp, 0o644);
  }
  assert.equal(off.trackedBy, null, 'the config write landed');
  assert.equal(off.configMtimeNs, statNs(path.join(w.root, '.trackchanges', 'config.json')));
  assert.equal(off.logged, false);
  assert.match(off.logWarning, /^the tracking setting was written, but not written to the comments log for ~\/notes-api\/docs\/report\.md: .*(EACCES|EPERM)/);
  assert.deepEqual(readLogLines(lp).map((e) => [e.kind, e.on]), [['set-tracked', true]]);
  assert.equal(s0.trackedBy, null);
});

// ── the reply cap ───────────────────────────────────────────────────

test('REPLY_MAX_BYTES is the kernel\'s _FILE_COMMENTS_REPLY_MAX, and the text and sidecar constants mirror the kernel\'s', () => {
  const src = fs.readFileSync(path.join(REPO, 'kernel', 'kernel.py'), 'utf8');
  assert.match(src, /^_FILE_COMMENTS_REPLY_MAX = 16 \* 1024 \* 1024/m);
  assert.equal(REPLY_MAX_BYTES, 16 * 1024 * 1024);
  assert.match(src, /^_TEXT_MAX_BYTES = 2 \* 1024 \* 1024/m);
  assert.equal(TEXT_MAX_BYTES, 2 * 1024 * 1024);
  assert.match(src, /^_TRACKCHANGES_DIR = "\.trackchanges"/m);
  assert.equal(TRACKCHANGES_DIR, '.trackchanges');
  assert.equal(human(2 * MB + 1), '2.0 MB');
  assert.equal(human(9 * MB), '9.0 MB');
  assert.equal(human(512), '512 bytes');
  assert.equal(human(1536), '1.5 KB');
});

test('save refuses too-large before any write when a record\'s oldText or author would take the reply past the kernel\'s cap; a record under it saves', () => {
  const w = world();
  const { st, cur } = trackedWithChange(w);
  const rec = st.store.suggestions[0];
  const before = snapshot(w, w.report);
  // oldText is carried twice, as the store's record and as its hunk: 9 MB of it is an 18 MB reply.
  const bloated = refused(w, saveReq(w.report, st, cur, [{ ...rec, oldText: 'x'.repeat(9 * MB) }]), 'too-large');
  assert.match(bloated.error, /^cannot write the comments for ~\/notes-api\/docs\/report\.md: with the change records and the decisions taken in the editor they come to 1[89]\.\d MB in one reply, past the 16\.0 MB the dashboard can carry back; nothing was changed$/);
  untouched(w, w.report, before);
  // The author label rides in both places too — but a record the sidecar roots must name its root's author
  // (recordsMisattributed, checked before the reply is measured), so a bloated label on this record refuses
  // desync, never too-large; the oldText and decision-text cases around it pin the cap itself.
  refused(w, saveReq(w.report, st, cur, [{ ...rec, author: 'a'.repeat(20 * MB) }]), 'desync');
  untouched(w, w.report, before);
  // A decision's texts go to the log, whose tail every reply carries: one 17 MB entry is past the cap.
  refused(w, saveReq(w.report, st, cur, [], [], [{ id: rec.id, oldText: 'x'.repeat(17 * MB), newText: rec.newText }]), 'too-large');
  untouched(w, w.report, before);
  // Every later status is the proof the file's comments are still usable — nothing was written.
  const again = status(w, w.report);
  assert.deepEqual(again.hunks, st.hunks);
  // A record with a large but carryable oldText saves: the cap is the kernel's, not a guess at
  // what a change may hold.
  const big = ok(w, saveReq(w.report, st, cur, [{ ...rec, oldText: 'y'.repeat(1 * MB) }]));
  assert.equal(big.hunks[0].oldText.length, 1 * MB);
  assert.equal(big.logged, true);
  assert.equal(status(w, w.report).hunks[0].oldText.length, 1 * MB);
});

test('comment and reply refuse too-large before any write when the note would take the reply past the cap: no sidecar, no landmark for a loose file', () => {
  const w = world();
  // A loose file: the refusal comes before the landmark, so no .trackchanges/ appears beside it.
  const s0 = status(w, w.loose);
  assert.equal(s0.root, null);
  const r = refused(w, { verb: 'comment', path: w.loose, args: { note: 'n'.repeat(17 * MB) }, fence: fenceFor(s0) }, 'too-large');
  assert.match(r.error, /with this comment they come to 1[67]\.\d MB in one reply, past the 16\.0 MB/);
  assert.equal(fs.existsSync(path.join(w.looseDir, '.trackchanges')), false, 'refused before the landmark');
  assert.equal(fs.readFileSync(w.loose, 'utf8'), w.text);
  // A rooted file: no sidecar is created, and a note under the cap then goes through.
  const s1 = status(w, w.report);
  refused(w, { verb: 'comment', path: w.report, args: { note: 'n'.repeat(17 * MB) }, fence: fenceFor(s1) }, 'too-large');
  assert.equal(fs.existsSync(storePathFor(w.root, w.report)), false);
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);
  const c = ok(w, { verb: 'comment', path: w.report, args: { note: 'a short note' }, fence: fenceFor(s1) });
  assert.equal(c.store.comments.length, 1);
  // A reply that would not fit refuses and leaves the sidecar as it was.
  const sidecar = fileBytes(c.storePath);
  const rr = refused(w, { verb: 'reply', path: w.report, args: { commentId: c.store.comments[0].id, note: 'r'.repeat(17 * MB) }, fence: fenceFor(c) }, 'too-large');
  assert.match(rr.error, /with this reply/);
  assert.deepEqual(fileBytes(c.storePath), sidecar);
});

// ── save keeps saveFile's scope; the size cap is every file-writing verb's ──

test('TEXT_EXT and TEXT_NAMES mirror the kernel\'s _TEXT_EXT and _TEXT_NAMES; isTextPath follows _is_text_path', () => {
  const src = fs.readFileSync(path.join(REPO, 'kernel', 'kernel.py'), 'utf8');
  const extBlock = src.match(/^_TEXT_EXT = set\(\(([\s\S]*?)\)\.split\(\)\)/m);
  assert.ok(extBlock, 'kernel.py defines _TEXT_EXT as set((...).split())');
  const exts = [...extBlock[1].matchAll(/"([^"]*)"/g)].map((m) => m[1]).join(' ').split(/\s+/).filter(Boolean);
  assert.deepEqual([...TEXT_EXT].sort(), [...new Set(exts)].sort());
  const namesBlock = src.match(/^_TEXT_NAMES = \{([\s\S]*?)\}/m);
  assert.ok(namesBlock, 'kernel.py defines _TEXT_NAMES as a set literal');
  const names = [...namesBlock[1].matchAll(/"([^"]*)"/g)].map((m) => m[1]);
  assert.deepEqual([...TEXT_NAMES].sort(), [...new Set(names)].sort());
  for (const p of ['/x/report.md', '/x/notes.MD', '/x/Makefile', '/x/.gitignore', '/x/config.json', '/x/run.sh', '/x/.env']) {
    assert.equal(isTextPath(p), true, p);
  }
  for (const p of ['/x/authorized_keys', '/x/id_rsa', '/x/a.tar.gz', '/x/notes.tex', '/x/log.jsonl', '/x/..md', '/x/report.md.bak', '/x/']) {
    assert.equal(isTextPath(p), false, p);
  }
});

test('save refuses not-text on a name outside the viewer\'s text scope, before any read or write; reject on such a name is not refused by name', () => {
  const w = world();
  // save: an extensionless file no allowlist names, with the fences a raw client could send.
  const keys = path.join(w.root, 'authorized_keys');
  fs.writeFileSync(keys, 'ssh-ed25519 AAAA example\n');
  const s0 = status(w, keys);
  const before = snapshot(w, keys);
  const r = refused(w, saveReq(keys, s0, 'replaced\n', []), 'not-text');
  assert.equal(r.error, 'cannot save ~/notes-api/authorized_keys: not a text file the viewer edits; nothing was changed');
  untouched(w, keys, before);
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);
  // The same name rule on a tracked file the CLIs edit under any name, which the viewer serves
  // download-only: save refuses it in saveFile's phrase, and nothing is read or written. reject and
  // reject-all do NOT carry that rule (round 3: the text they write is the sidecar's own record, not
  // the client's, so they keep Slice 2's scope) — the change is reverted and the decision logged.
  // file-comments-host-scope.test.mjs pins the reject side in full; this is the boundary between
  // the two verbs on one file.
  const tex = path.join(w.root, 'docs', 'notes.tex');
  fs.writeFileSync(tex, 'Hello world.\n');
  const st = edit(w, tex, 'world', 'there');
  assert.equal(st.hunks.length, 1);
  assert.equal(fs.readFileSync(tex, 'utf8'), 'Hello there.\n');
  const before2 = snapshot(w, tex);
  const r2 = refused(w, saveReq(tex, st, 'Hello there!\n', st.store.suggestions), 'not-text');
  assert.equal(r2.error, 'cannot save ~/notes-api/docs/notes.tex: not a text file the viewer edits; nothing was changed');
  untouched(w, tex, before2);
  const rj = ok(w, { verb: 'reject', path: tex, args: { ids: [st.hunks[0].id] }, fence: fileFenceFor(st) });
  assert.deepEqual(rj.rejected, [st.hunks[0].id]);
  assert.deepEqual(rj.hunks, []);
  assert.equal(fs.readFileSync(tex, 'utf8'), 'Hello world.\n', 'the old text is back');
  assert.deepEqual(rj.log.map((e) => e.kind), ['reject']);
  assert.equal(rj.logged, true);
});

test('save and reject refuse too-large on a file past the text cap on disk, the file the viewer never loaded, before any write', () => {
  const w = world();
  const big = path.join(w.root, 'docs', 'big.md');
  const body = 'a'.repeat(TEXT_MAX_BYTES - 13) + '\nHello world.\n';        // one byte over the cap
  fs.writeFileSync(big, body);
  assert.equal(fs.statSync(big).size, TEXT_MAX_BYTES + 1);
  writeTrackedPaths(w.root, ['docs/big.md']);
  const s0 = status(w, big);
  assert.deepEqual(s0.trackedBy, { kind: 'file', entry: 'docs/big.md' });
  const before = snapshot(w, big);
  const r = refused(w, saveReq(big, s0, 'tiny\n', []), 'too-large');
  assert.equal(r.error, `cannot save ~/notes-api/docs/big.md: the file on disk is ${human(TEXT_MAX_BYTES + 1)}, past the ${human(TEXT_MAX_BYTES)} text cap the viewer loads; nothing was changed`);
  untouched(w, big, before);
  // A pending change on it: reject would write a file under the cap, and still refuses — the text
  // it would write is derived from a file the person never saw.
  const st = edit(w, big, 'world', 'there');
  assert.equal(st.hunks.length, 1);
  const before2 = snapshot(w, big);
  const r2 = refused(w, { verb: 'reject-all', path: big, args: {}, fence: fileFenceFor(st) }, 'too-large');
  assert.match(r2.error, /^cannot write ~\/notes-api\/docs\/big\.md: the file on disk is 2\.0 MB, past the 2\.0 MB text cap the viewer loads; nothing was changed$/);
  untouched(w, big, before2);
});

// ── .trackchanges/ and the log rule ─────────────────────────────────

test('underTrackchanges is the kernel\'s _under_trackchanges: a directory segment, never the basename', () => {
  assert.equal(underTrackchanges('/p/.trackchanges/docs%2Freport.md.json'), true);
  assert.equal(underTrackchanges('/p/.trackchanges/config.json'), true);
  assert.equal(underTrackchanges('/p/sub/.trackchanges/x.comments-log.jsonl'), true);
  assert.equal(underTrackchanges('/p/.trackchanges'), false);
  assert.equal(underTrackchanges('/p/x.trackchanges/y.md'), false);
  assert.equal(underTrackchanges('/p/docs/report.md'), false);
});

test('save on a path inside .trackchanges/ writes the file and logs nothing — no sidecar-of-the-sidecar log — tracked or not', () => {
  const w = world();
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  const tc = path.join(w.root, '.trackchanges');
  const sidecar = st.storePath;
  assert.equal(path.dirname(sidecar), tc);
  const listing = () => fs.readdirSync(tc).sort();
  assert.deepEqual(listing(), [path.basename(sidecar)]);
  // The viewer can open the sidecar as a .json file and save it; the fence is the one a client
  // would send for a file with no sidecar of its own.
  const own = status(w, sidecar);
  assert.equal(own.store, null);
  const text = fs.readFileSync(sidecar, 'utf8');
  const r = ok(w, saveReq(sidecar, own, text + '\n', []));
  assert.equal(fs.readFileSync(sidecar, 'utf8'), text + '\n', 'the file is written');
  assert.equal(r.fileMtimeNs, statNs(sidecar));
  assert.equal(r.logged, false);
  assert.equal('logWarning' in r, false);
  assert.deepEqual(r.log, []);
  assert.deepEqual(listing(), [path.basename(sidecar)], 'nothing new in .trackchanges/');
  // Even a folder entry covering .trackchanges/ does not make it the log's business.
  writeTrackedPaths(w.root, ['.trackchanges/']);
  const own2 = status(w, sidecar);
  assert.deepEqual(own2.trackedBy, { kind: 'folder', entry: '.trackchanges/' });
  const r2 = ok(w, saveReq(sidecar, own2, text + '\n\n', []));
  assert.equal(r2.logged, false);
  assert.deepEqual(r2.log, []);
  assert.deepEqual(listing(), ['config.json', path.basename(sidecar)]);
  // The same file through log-edit, the kernel's saveFile path: the kernel never calls it for a
  // path inside .trackchanges/, and the host logs nothing for one either.
  const le = ok(w, { verb: 'log-edit', path: sidecar, args: { summary: { mtimeBeforeNs: '1', mtimeAfterNs: '2', bytesBefore: 1, bytesAfter: 2, diff: '', truncated: false } } });
  assert.equal(le.logged, false);
  assert.deepEqual(listing(), ['config.json', path.basename(sidecar)]);
});
