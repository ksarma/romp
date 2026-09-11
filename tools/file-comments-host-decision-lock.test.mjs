// The decision verbs LOAD under the sidecar's lock (plans/file-review.md, decision 49; decideUnderLock
// in the host): accept, reject and save hold `<sidecar>.lock` from their fence stat and their reads
// of the file and the sidecar through their last rename or prune. tools/file-comments-host-store-lock
// pins the wait for `comment` and `track-reply`, and tools/file-comments-host-race pins that a reject
// HOLDS the lock across its writes; neither says where a decision's load sits. A decideUnderLock
// that ran loadForDecision (the fence stat, the file read, the sidecar load) before taking the lock
// and only the writes inside it passed every one of them, and reintroduced the lost update for the
// three verbs that rewrite the most: the fence checked against a sidecar another writer was about
// to rename, the wait for that writer's release, then the stale store written over its write. For
// a reject-all or an accept that is the sidecar pruned with the other writer's comment in it; for a
// save, a sidecar with no comments where there was one.
// Here the other writer is the test itself, as in the store-lock module: it loads the store, takes
// the lock the way withStoreLock takes it (an O_EXCL create of `<sidecar>.lock` holding "pid ts"),
// and saves a comment 300 ms later, just before the release. A decision that loads under the lock
// answers after that save, sees the moved fence and refuses store-moved (the panel's copy IS
// stale: it lacks the comment), and the panel's one retry lands both the comment and the decision.
// One case per handler: reject-all (doReject, which reject shares), accept by id (doAccept, which
// accept-all shares), save with a rejection from the editor (doSave).
// Same hermetic harness as file-comments-host-store-lock.test.mjs (the synthetic notes-api world
// under a scratch directory, FILE_COMMENTS_HOME for "~"); synthetic ids and text only.
// Run: node --test tools/file-comments-host-decision-lock.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import engine from '../vendor/track-changents/engine.js';
import { storePathFor, storeLockPathFor, loadStore, saveStore } from '../vendor/track-changents/store-io.mjs';
import { addComment } from '../vendor/track-changents/cli/track-comment.mjs';
import { applyEdits, logPathFor } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');

const SID = '11111111-2222-3333-4444-555555555555';
const HOLD_MS = 300;
const OLD = 'cut p95 latency by 40%';
const NEW = 'reduced p95 latency by 35%';
const NOTE = 'Still true?';

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-decision-lock-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  const report = path.join(root, 'docs', 'report.md');
  return { home, root, report, original: fs.readFileSync(report, 'utf8'), storePath: storePathFor(root, report) };
}

function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home, ...(extra || {}) };
  delete e.TRACKCHANGES_ROOT;
  delete e.FILE_COMMENTS_TEST_PAUSE_MS;
  if (!extra || !('ROMP_SID' in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
  return e;
}

// The kernel's call of the host: the request on stdin, run to completion. `endedAt` is Date.now()
// at exit, for the "answered after the holder saved" assertion.
function host(w, req) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [HOST], { env: env(w) });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8'); child.stdout.on('data', (c) => { stdout += c; });
    child.stderr.setEncoding('utf8'); child.stderr.on('data', (c) => { stderr += c; });
    child.on('error', reject);
    child.on('close', (code) => {
      let json = null;
      try { json = JSON.parse(stdout); } catch { json = null; }
      resolve({ code, stdout, stderr, json, endedAt: Date.now() });
    });
    child.stdin.end(JSON.stringify(req));
  });
}
function hostSync(w, req) {
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w) });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  assert.equal(r.status, 0, `exit ${r.status}: ${r.stderr}`);
  assert.ok(json, r.stdout);
  return json;
}
function status(w) {
  const j = hostSync(w, { verb: 'status', path: w.report, args: {} });
  assert.equal(j.ok, true, JSON.stringify(j));
  return j;
}
const fenceFor = (st) => ({ storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs });
const fileFenceFor = (st) => ({ ...fenceFor(st), fileMtimeNs: st.fileMtimeNs });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const readSidecar = (sp) => JSON.parse(fs.readFileSync(sp, 'utf8'));
const readLogKinds = (sp) => fs.readFileSync(logPathFor(sp), 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l).kind);

// The seed: one pending change by the `api` session, written by the real track-edit; then the
// status the panel would hold, with the one hunk and the fence for each verb.
function seeded(w) {
  const r = spawnSync(process.execPath, [path.join(VENDOR, 'cli', 'track-edit.mjs'), '--file', w.report, '--old', OLD, '--new', NEW],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'api', ROMP_SID: SID }) });
  assert.equal(r.status, 0, r.stderr);
  const st = status(w);
  assert.equal(st.hunks.length, 1);
  assert.equal(st.hunks[0].newText, NEW);
  const text = fs.readFileSync(w.report, 'utf8');
  assert.ok(text.includes(NEW), 'the change is in the file');
  return { st, hunk: st.hunks[0], text, lockPath: storeLockPathFor(w.storePath) };
}

// A writer mid-write: the store loaded, the lock taken as withStoreLock takes it. `save()` lands
// its comment and releases, and says when it did.
function holdAsWriter(w, text, lockPath) {
  const held = loadStore(w.storePath, text);
  fs.writeFileSync(lockPath, `${process.pid} ${Date.now()}\n`, { flag: 'wx' });
  return {
    save() {
      assert.equal(addComment(held, text, 'Cold starts remain slow', NOTE, 'you', Date.now(), null).error, undefined);
      saveStore(w.root, w.storePath, held, text);
      const savedAt = Date.now();
      fs.unlinkSync(lockPath);
      return savedAt;
    },
    release() { try { fs.unlinkSync(lockPath); } catch { /* ignore */ } },
  };
}

// The decision sent against a held lock, the holder's comment saved HOLD_MS later, then the
// release: the decision must answer after that save and refuse store-moved, with nothing of its
// own on disk (the change still pending, the file still holding it, the comment there, no log
// entry). Returns the status the panel re-reads for its one retry.
async function decisionAgainstHeldLock(w, seed, req) {
  const writer = holdAsWriter(w, seed.text, seed.lockPath);
  let savedAt = 0;
  let r;
  try {
    const pending = host(w, req);
    await sleep(HOLD_MS);
    savedAt = writer.save();
    r = await pending;
  } finally {
    writer.release();
  }
  assert.equal(r.code, 0, r.stderr);
  assert.ok(r.json, r.stdout);
  assert.ok(r.endedAt >= savedAt, `the ${req.verb} answered ${savedAt - r.endedAt} ms BEFORE the lock holder saved`);
  // The holder's rename moved the fence the status held. Loaded under the lock, the decision sees
  // that and refuses; loaded before it, the fence matched a sidecar about to be renamed and the
  // decision would have answered ok and written the holder's comment away.
  assert.equal(r.json.ok, false, `the ${req.verb} did not see the holder's write: ${r.stdout}`);
  assert.equal(r.json.code, 'store-moved', r.json.error);
  const disk = readSidecar(w.storePath);
  assert.equal(disk.suggestions.length, 1, 'the change is still pending');
  assert.equal(disk.comments.length, 1, 'the holder\'s comment is on disk');
  assert.equal(disk.comments[0].body, NOTE);
  assert.equal(fs.readFileSync(w.report, 'utf8'), seed.text, 'the file is as the change left it');
  assert.equal(fs.existsSync(logPathFor(w.storePath)), false, 'the refused decision logged nothing');
  assert.equal(fs.existsSync(seed.lockPath), false, 'the lock is released');
  const again = status(w);
  assert.equal(again.store.comments.length, 1, 'the holder\'s comment is there to be seen');
  assert.equal(again.hunks.length, 1);
  return again;
}

// After the retry: the decision landed and the holder's comment survived it. The sidecar is kept
// (a comment keeps it; afterDecision prunes only an emptied one).
function bothLanded(w, seed, fileText, logKinds) {
  const disk = readSidecar(w.storePath);
  assert.deepEqual(disk.suggestions, [], 'the change is decided');
  assert.equal(disk.comments.length, 1, 'the holder\'s comment survives the decision');
  assert.equal(disk.comments[0].body, NOTE);
  assert.equal(fs.readFileSync(w.report, 'utf8'), fileText);
  assert.deepEqual(readLogKinds(w.storePath), logKinds);
  assert.equal(fs.existsSync(seed.lockPath), false, 'the lock is released');
}

test('reject-all loads under the lock: a comment the holder saves 300 ms later moves the fence, the reject refuses store-moved, and the retry lands both', async () => {
  const w = world();
  const seed = seeded(w);
  const again = await decisionAgainstHeldLock(w, seed, { verb: 'reject-all', path: w.report, args: {}, fence: fileFenceFor(seed.st) });
  const retry = hostSync(w, { verb: 'reject-all', path: w.report, args: {}, fence: fileFenceFor(again) });
  assert.equal(retry.ok, true, retry.error);
  assert.deepEqual(retry.rejected, [seed.hunk.id]);
  bothLanded(w, seed, w.original, ['reject']);
});

test('accept loads under the lock: the same, with the change accepted by id and the file untouched', async () => {
  const w = world();
  const seed = seeded(w);
  const again = await decisionAgainstHeldLock(w, seed, { verb: 'accept', path: w.report, args: { ids: [seed.hunk.id] }, fence: fenceFor(seed.st) });
  const retry = hostSync(w, { verb: 'accept', path: w.report, args: { ids: [seed.hunk.id] }, fence: fenceFor(again) });
  assert.equal(retry.ok, true, retry.error);
  assert.deepEqual(retry.accepted, [seed.hunk.id]);
  bothLanded(w, seed, seed.text, ['accept']);
});

test('save loads under the lock: the same, with the rejection made in the editor and its content the old text back', async () => {
  const w = world();
  const seed = seeded(w);
  // In the editor: reject the change (the engine's reverse edit lands in the buffer).
  const res = engine.rejectSuggestion(seed.st.store.suggestions, seed.hunk.id);
  const content = applyEdits(seed.text, [res.edit]);
  assert.deepEqual(res.suggestions, []);
  assert.equal(content, w.original);
  const decision = { id: seed.hunk.id, oldText: seed.hunk.oldText, newText: seed.hunk.newText };
  const saveOf = (st) => ({ verb: 'save', path: w.report, args: { content, suggestions: res.suggestions, accepted: [], rejected: [decision] }, fence: fileFenceFor(st) });
  const again = await decisionAgainstHeldLock(w, seed, saveOf(seed.st));
  const retry = hostSync(w, saveOf(again));
  assert.equal(retry.ok, true, retry.error);
  assert.equal(retry.logged, true);
  // save logs the buffer's own text change (the reversal, as a direct edit) ahead of the rejection
  bothLanded(w, seed, w.original, ['edit', 'reject']);
});

test('decideUnderLock loads inside the lock: loadForDecision is called only within the function underStoreLock runs', () => {
  // The source shape the cases above prove: a hoisted load would pass every wait-and-hold pin
  // but these. Kept beside them so a reader finds the rule where the behaviour is pinned.
  const src = fs.readFileSync(HOST, 'utf8');
  const i = src.indexOf('\nfunction decideUnderLock(');
  assert.ok(i >= 0);
  const fn = src.slice(i, src.indexOf('\n}\n', i) + 3);
  assert.match(fn, /const run = \(\) => decide\(loadForDecision\(ctx, writesFile, root, paths\)\);/, 'the load is inside the function the lock runs');
  assert.match(fn, /underStoreLock\(ctx, paths\.storePath, run\)/);
  assert.equal((src.match(/loadForDecision\(/g) || []).length, 2, 'defined once, called once: from inside run');
});
