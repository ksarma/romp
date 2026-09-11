// One writer per sidecar at a time (plans/file-review.md, decision 49): the host and the vendored
// CLIs take store-io's lock (`<sidecar>.lock`, withStoreLock; vendor patch 0008) around their
// load-to-rename, so a writer that arrives while another is mid-write WAITS for its rename and
// loads after it. Before the lock, each loaded before the other's rename and the second rename
// erased the first's write; against the real host and CLIs, one write in five was lost at a
// stagger of 4 to 20 ms (the lost-update probe, 2026-09-09). Here the mid-write writer is the
// test itself: it loads the store, takes the lock the way a writer does, and saves 300 ms later.
//   * the host's `comment` waits for the release; the holder's rename moved the fence, so the host
//     refuses store-moved (the panel's copy IS stale now) and the panel's one retry lands; both
//     writes survive. Before: the host answered about 150 ms BEFORE the holder saved, and the
//     holder's save erased its comment.
//   * the same with the real track-reply, which has no fence: it waits, then loads the holder's
//     write and adds its reply to it. Before: its reply was erased.
//   * a lock held past store-io's wait refuses `busy` (host) and exits 1 with one plain line (CLI),
//     nothing written and the holder's lock left alone.
//   * a dead writer's lock (its pid gone, or its stamp older than the stale bound) is broken and
//     the write proceeds at once.
//   * withStoreLock itself: the stamp, the release on return and on throw, the folder made for the
//     lock and taken away when nothing else landed in it, a non-lock at the lock's name refused.
// Same hermetic harness as file-comments-host.test.mjs (the synthetic notes-api world under a
// scratch directory, FILE_COMMENTS_HOME for "~"); synthetic ids and text only.
// Run: node --test tools/file-comments-host-store-lock.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import {
  storePathFor, storeLockPathFor, loadStore, saveStore, withStoreLock, StoreLockError, STORE_LOCK_WAIT_MS,
} from '../vendor/track-changents/store-io.mjs';
import { addReply } from '../vendor/track-changents/cli/track-reply.mjs';
import { addComment } from '../vendor/track-changents/cli/track-comment.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');

const SID = '11111111-2222-3333-4444-555555555555';
const HOLD_MS = 300;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-lock-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  return { home, root, report: path.join(root, 'docs', 'report.md'), text: fs.readFileSync(path.join(FIX, 'report.md'), 'utf8') };
}

function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home, ...(extra || {}) };
  delete e.TRACKCHANGES_ROOT;
  if (!extra || !('ROMP_SID' in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
  return e;
}

// A child process run to completion: the kernel's call of the host (the request on stdin) or a
// session's run of a CLI. `endedAt` is Date.now() at exit, for the "waited" assertions.
function run(file, args, opts) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [file, ...args], { env: opts.env });
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
    if (opts.input != null) child.stdin.end(opts.input); else child.stdin.end();
  });
}
const host = (w, req) => run(HOST, [], { input: JSON.stringify(req), env: env(w) });
const cli = (w, name, args) => run(path.join(VENDOR, 'cli', `track-${name}.mjs`), args, { env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
function hostSync(w, req) {
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w) });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  assert.equal(r.status, 0, `exit ${r.status}: ${r.stderr}`);
  return json;
}
function status(w) {
  const j = hostSync(w, { verb: 'status', path: w.report, args: {} });
  assert.ok(j && j.ok === true, JSON.stringify(j));
  return j;
}
const fenceFor = (st) => ({ storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const readSidecar = (sp) => JSON.parse(fs.readFileSync(sp, 'utf8'));

// The seed: one comment by the `web` session, written by the real track-comment.
async function seeded(w) {
  const r = await cli(w, 'comment', ['--file', w.report, '--anchor', 'p95 latency', '--note', 'Which latency figure is this?']);
  assert.equal(r.code, 0, r.stderr);
  const storePath = storePathFor(w.root, w.report);
  const c0 = readSidecar(storePath).comments[0];
  return { storePath, lockPath: storeLockPathFor(storePath), c0 };
}

// A writer mid-write: the store loaded, the lock taken as withStoreLock takes it (an O_EXCL create
// holding "pid ts"). `save(mutate)` lands its write and releases, and says when it did.
function holdAsWriter(w, storePath, lockPath) {
  const held = loadStore(storePath, w.text);
  fs.writeFileSync(lockPath, `${process.pid} ${Date.now()}\n`, { flag: 'wx' });
  return {
    held,
    save(mutate) {
      mutate(held);
      saveStore(w.root, storePath, held, w.text);
      const savedAt = Date.now();
      fs.unlinkSync(lockPath);
      return savedAt;
    },
    release() { try { fs.unlinkSync(lockPath); } catch { /* ignore */ } },
  };
}

// ── the host waits ──────────────────────────────────────────────────

test('the host waits for a held lock: a reply the holder saves 300 ms later moves the fence, the host refuses store-moved, and the retry lands both writes', async () => {
  const w = world();
  const { storePath, lockPath, c0 } = await seeded(w);
  const st = status(w);
  const writer = holdAsWriter(w, storePath, lockPath);
  let savedAt = 0;
  let r;
  try {
    const pending = host(w, { verb: 'comment', path: w.report, args: { note: 'Whole-file note.' }, fence: fenceFor(st) });
    await sleep(HOLD_MS);
    savedAt = writer.save((s) => { assert.equal(addReply(s, c0.id, 'web', 'The p95 over the last week.', Date.now(), SID).error, undefined); });
    r = await pending;
  } finally {
    writer.release();
  }
  assert.equal(r.code, 0, r.stderr);
  assert.ok(r.json, r.stdout);
  assert.ok(r.endedAt >= savedAt, `the host answered ${savedAt - r.endedAt} ms BEFORE the lock holder saved`);
  // The holder's rename moved the fence the status held: the panel's copy is stale (it lacks the
  // reply), so the write refuses and the panel re-reads and retries once (MOVED).
  assert.equal(r.json.ok, false, r.stdout);
  assert.equal(r.json.code, 'store-moved', r.json.error);
  const again = status(w);
  assert.equal(again.store.comments[0].replies.length, 1, 'the holder\'s reply is there to be seen');
  const retry = hostSync(w, { verb: 'comment', path: w.report, args: { note: 'Whole-file note.' }, fence: fenceFor(again) });
  assert.equal(retry.ok, true, retry.error);
  const disk = readSidecar(storePath);
  assert.equal(disk.comments.length, 2, 'both writes survive');
  assert.equal(disk.comments[0].id, c0.id);
  assert.equal(disk.comments[0].replies.length, 1, 'the holder\'s reply');
  assert.equal(disk.comments[0].replies[0].body, 'The p95 over the last week.');
  assert.equal(disk.comments[1].body, 'Whole-file note.', 'the host\'s comment');
  assert.equal(fs.existsSync(lockPath), false, 'the lock is released');
});

test('track-reply waits for a held lock: it loads the comment the holder saves 300 ms later and adds its reply to it; both writes survive', async () => {
  const w = world();
  const { storePath, lockPath, c0 } = await seeded(w);
  const writer = holdAsWriter(w, storePath, lockPath);
  let savedAt = 0;
  let r;
  try {
    const pending = cli(w, 'reply', ['--file', w.report, '--thread', c0.id, '--note', 'The p95 over the last week.']);
    await sleep(HOLD_MS);
    savedAt = writer.save((s) => {
      assert.equal(addComment(s, w.text, 'Cold starts remain slow', 'Still true?', 'you', Date.now(), null).error, undefined);
    });
    r = await pending;
  } finally {
    writer.release();
  }
  assert.equal(r.code, 0, r.stderr);
  assert.ok(r.endedAt >= savedAt, `track-reply exited ${savedAt - r.endedAt} ms BEFORE the lock holder saved`);
  assert.equal(r.stdout, 'Reply posted to thread.\n');
  const disk = readSidecar(storePath);
  assert.equal(disk.comments.length, 2, 'both writes survive');
  assert.equal(disk.comments[0].id, c0.id);
  assert.equal(disk.comments[0].replies.length, 1, 'the reply, into the store the holder saved');
  assert.equal(disk.comments[0].replies[0].body, 'The p95 over the last week.');
  assert.equal(disk.comments[1].body, 'Still true?', 'the holder\'s comment');
  assert.equal(fs.existsSync(lockPath), false, 'the lock is released');
});

// ── the refusal and the stale lock ──────────────────────────────────

test('a lock held past the wait: the host refuses busy and the CLIs exit 1 with one plain line; nothing is written and the holder\'s lock stands', async () => {
  const w = world();
  const { storePath, lockPath, c0 } = await seeded(w);
  const st = status(w);
  const before = fs.readFileSync(storePath);
  fs.writeFileSync(lockPath, `${process.pid} ${Date.now()}\n`, { flag: 'wx' });
  const startedAt = Date.now();
  try {
    const [h, c, e, rp] = await Promise.all([
      host(w, { verb: 'comment', path: w.report, args: { note: 'Whole-file note.' }, fence: fenceFor(st) }),
      cli(w, 'comment', ['--file', w.report, '--anchor', 'Cold starts', '--note', 'Still true?']),
      cli(w, 'edit', ['--file', w.report, '--old', 'v1.2', '--new', 'v1.3']),
      cli(w, 'reply', ['--file', w.report, '--thread', c0.id, '--note', 'Yes.']),
    ]);
    assert.ok(Date.now() - startedAt >= STORE_LOCK_WAIT_MS, 'each waited out the bound before giving up');
    assert.equal(h.code, 0, h.stderr);
    assert.deepEqual(h.json, { ok: false, code: 'busy', error: 'another editor is writing ~/notes-api/docs/report.md; retry' });
    for (const r of [c, e, rp]) {
      assert.equal(r.code, 1, r.stdout);
      assert.equal(r.stderr, 'another editor is writing this file; retry\n');
      assert.equal(r.stdout, '');
    }
  } finally {
    fs.unlinkSync(lockPath);
  }
  assert.ok(fs.readFileSync(storePath).equals(before), 'the sidecar is untouched');
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text, 'the file is untouched');
});

test('a dead writer\'s lock is broken: a pid that is gone, or a stamp past the stale bound, and the write proceeds at once', async () => {
  const w = world();
  const { storePath, lockPath } = await seeded(w);
  const gone = spawnSync(process.execPath, ['-e', ''], { encoding: 'utf8' });
  assert.equal(gone.status, 0);
  // the pid of a process that has exited (spawnSync returns only after it did)
  fs.writeFileSync(lockPath, `${gone.pid} ${Date.now()}\n`, { flag: 'wx' });
  let st = status(w);
  let t0 = Date.now();
  let r = await host(w, { verb: 'comment', path: w.report, args: { note: 'First note.' }, fence: fenceFor(st) });
  assert.equal(r.json && r.json.ok, true, r.stdout + r.stderr);
  assert.ok(r.endedAt - t0 < STORE_LOCK_WAIT_MS, `no wait for a dead writer (took ${r.endedAt - t0} ms)`);
  assert.equal(fs.existsSync(lockPath), false, 'the broken lock is gone with the write\'s own');
  // a live pid (this process) whose stamp is older than the stale bound: the writer was killed and
  // its pid reused, or it hung past the kernel's deadline
  fs.writeFileSync(lockPath, `${process.pid} ${Date.now() - 20000}\n`, { flag: 'wx' });
  st = status(w);
  t0 = Date.now();
  r = await cli(w, 'reply', ['--file', w.report, '--thread', readSidecar(storePath).comments[0].id, '--note', 'Yes.']);
  assert.equal(r.code, 0, r.stderr);
  assert.ok(r.endedAt - t0 < STORE_LOCK_WAIT_MS, `no wait for a stale stamp (took ${r.endedAt - t0} ms)`);
  assert.equal(fs.existsSync(lockPath), false);
  const disk = readSidecar(storePath);
  assert.equal(disk.comments.length, 2);
  assert.equal(disk.comments[0].replies.length, 1);
});

// ── withStoreLock itself ────────────────────────────────────────────

test('withStoreLock: the lock holds "pid ts" while fn runs and is gone after, on return and on throw', () => {
  const w = world();
  const storePath = storePathFor(w.root, w.report);
  const lockPath = storeLockPathFor(storePath);
  fs.mkdirSync(path.dirname(storePath));
  let seen = null;
  const out = withStoreLock(storePath, () => { seen = fs.readFileSync(lockPath, 'utf8'); return 42; });
  assert.equal(out, 42);
  const m = /^(\d+) (\d+)\n$/.exec(seen);
  assert.ok(m, `the stamp is "pid ts": ${JSON.stringify(seen)}`);
  assert.equal(Number(m[1]), process.pid);
  assert.ok(Math.abs(Number(m[2]) - Date.now()) < 5000);
  assert.equal(fs.existsSync(lockPath), false);
  assert.throws(() => withStoreLock(storePath, () => { throw new Error('inside'); }), /inside/);
  assert.equal(fs.existsSync(lockPath), false, 'released on the way out of a throw');
});

test('withStoreLock: a missing .trackchanges/ is made for the lock and taken away when nothing else landed in it, kept when something did', () => {
  const w = world();
  const storePath = storePathFor(w.root, w.report);
  const dir = path.dirname(storePath);
  assert.equal(fs.existsSync(dir), false);
  withStoreLock(storePath, () => { assert.ok(fs.existsSync(storeLockPathFor(storePath)), 'the lock exists in the folder made for it'); });
  assert.equal(fs.existsSync(dir), false, 'a refused or empty write leaves no folder behind');
  assert.throws(() => withStoreLock(storePath, () => { throw new Error('refused'); }), /refused/);
  assert.equal(fs.existsSync(dir), false);
  withStoreLock(storePath, () => { fs.writeFileSync(storePath, '{}'); });
  assert.ok(fs.existsSync(dir) && fs.existsSync(storePath), 'a write that landed keeps its folder');
  assert.equal(fs.existsSync(storeLockPathFor(storePath)), false);
});

test('withStoreLock: a held lock refuses after the wait with the one plain line; a non-lock at the lock\'s name refuses at once and is left alone', () => {
  const w = world();
  const storePath = storePathFor(w.root, w.report);
  const lockPath = storeLockPathFor(storePath);
  fs.mkdirSync(path.dirname(storePath));
  fs.writeFileSync(lockPath, `${process.pid} ${Date.now()}\n`);
  const t0 = Date.now();
  let err = null;
  try { withStoreLock(storePath, () => 'ran', { waitMs: 60 }); } catch (e) { err = e; }
  assert.ok(err instanceof StoreLockError, String(err));
  assert.equal(err.held, true);
  assert.equal(err.message, 'another editor is writing this file; retry');
  assert.ok(Date.now() - t0 >= 60);
  assert.ok(fs.existsSync(lockPath), 'a live holder\'s lock is never removed');
  fs.unlinkSync(lockPath);
  fs.mkdirSync(lockPath);   // a directory where the lock would go
  err = null;
  try { withStoreLock(storePath, () => 'ran', { waitMs: 60 }); } catch (e) { err = e; }
  assert.ok(err instanceof StoreLockError, String(err));
  assert.equal(err.held, false);
  assert.match(err.message, /is not a regular file/);
  assert.ok(fs.statSync(lockPath).isDirectory(), 'never removed');
});
