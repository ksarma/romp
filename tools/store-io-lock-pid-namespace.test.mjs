// withStoreLock (plans/file-review.md, decision 49; vendor patch 0008) judges a lock's writer dead by
// kill(pid, 0) answering ESRCH. Pids are per pid namespace. From a child pid namespace (a sandboxed tool
// shell: bubblewrap's --unshare-pid, which the Codex and Claude Code sandboxes both pass) every process
// outside is ESRCH, alive or not, so a CLI in such a sandbox read an editor host's live lock as a dead
// writer's, broke it at once and wrote inside the host's load-to-rename; and a pid stamped inside such a
// sandbox names, outside it, whatever process has that number there, so the host read the sandboxed
// CLI's live lock as a dead writer's whenever its in-namespace pid was a free number outside, broke it
// and wrote inside the CLI's load-to-rename: the lost update the lock exists to close, in both
// directions (the review of 2026-09-11, its first and third rounds). Now a writer outside the initial
// namespace names its own on a second line of the stamp, `ns <inode>` (of /proc/self/ns/pid; the
// initial namespace, one inode number on every Linux, is named by the line's absence), and a reader
// judges the pid only when the lock names the reader's own namespace, else by the stamp's age alone.
// Each case is a child process; the namespace is read through a stand-in for fs.readlinkSync installed
// before store-io is imported, so the cases run on any machine, and one real child namespace where
// `unshare` can make one unprivileged (skipped where it cannot):
//   * in a child namespace, an initial-namespace writer's lock (no `ns` line) stamped with a dead pid
//     and a fresh ts is left alone: the writer waits the bound out and refuses as held
//   * there, a stamp past the stale bound is still broken
//   * in the initial namespace (the stand-in says so), the dead pid's lock is broken at once, as before
//   * without the stand-in, this machine: the same when this process is in the initial namespace, the
//     wait when it is not
//   * a writer in a child namespace stamps `pid ts` and then `ns <inode>`; one in the initial namespace
//     stamps `pid ts` alone
//   * (third round) a child-namespace writer's live lock, its pid a free number here, is left alone by a
//     writer in the initial namespace, which waits the bound out and refuses as held; before, it was
//     broken at once and the write went through
//   * the pid is judged in the namespace that stamped it: the same lock read from that namespace is
//     broken at once when the pid is dead there; read from a third namespace it is waited out
//   * a real child pid namespace: the vendored track-comment, against a lock a live process outside it
//     holds, prints the line for a held lock and exits 1, the lock intact and nothing written; and a
//     holder inside it stamps the namespace's inode, which a writer outside waits behind
// Synthetic paths only, under a scratch directory.
// Run: node --test tools/store-io-lock-pid-namespace.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { storeLockPathFor, storePathFor, withStoreLock, StoreLockError } from '../vendor/track-changents/store-io.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const VENDOR = fs.realpathSync(path.resolve(HERE, '..', 'vendor', 'track-changents'));
const STORE_IO = pathToFileURL(path.join(VENDOR, 'store-io.mjs')).href;
const TRACK_COMMENT = path.join(VENDOR, 'cli', 'track-comment.mjs');
const INIT_NS = 'pid:[4026531836]';     // PROC_PID_INIT_INO, the initial pid namespace on every Linux
const CHILD_NS = 'pid:[4026532101]';    // any other: a namespace of its own
const CHILD_NS_2 = 'pid:[4026532345]';  // a third
const inoOf = (ns) => /^pid:\[(\d+)\]$/.exec(ns)[1];

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-store-io-lock-pidns-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
// A root with a landmark, one note and its `.trackchanges/`; the note's sidecar and lock paths.
function world() {
  const root = path.join(SCRATCH, `w${++worlds}`, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  const note = path.join(root, 'docs', 'report.md');
  fs.writeFileSync(note, '# Latency report\n\nStep one: warm the cache before the first request.\n');
  const storePath = storePathFor(root, note);
  fs.mkdirSync(path.dirname(storePath));
  return { root, note, dir: path.dirname(storePath), storePath, lockPath: storeLockPathFor(storePath) };
}

function deadPid() {
  const gone = spawnSync(process.execPath, ['-e', ''], { encoding: 'utf8' });
  assert.equal(gone.status, 0);
  return gone.pid;
}

function sleepMs(ms) { Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms); }

// This process's own pid namespace link, or null where /proc cannot be read (every pid is judged).
function ownNs() {
  try { return fs.readlinkSync('/proc/self/ns/pid'); } catch { return null; }
}

// One writer in a child process: with `ns`, fs.readlinkSync answers it for /proc/self/ns/pid before
// store-io is imported (store-io reads the link once, on its first use); then one withStoreLock, which
// reads its own lock back while it holds (`seen`), touches `ready` when given, and holds `holdMs`.
const WRITER = `
import fs from 'node:fs';
const [storeIo, store, ns, waitMs, staleMs, holdMs, ready] = process.argv.slice(1);   // -e: no script path in argv
if (ns) {
  const real = fs.readlinkSync;
  fs.readlinkSync = function (p, ...rest) { return p === '/proc/self/ns/pid' ? ns : real.call(fs, p, ...rest); };
}
const { withStoreLock, StoreLockError, storeLockPathFor } = await import(storeIo);
const out = { ran: false, seen: null, err: null, took: 0 };
const t0 = Date.now();
try {
  withStoreLock(store, () => {
    out.ran = true;
    out.seen = fs.readFileSync(storeLockPathFor(store), 'utf8');
    if (ready) fs.writeFileSync(ready, '');
    const until = Date.now() + Number(holdMs || 0);
    while (Date.now() < until) Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 5);
  }, { waitMs: Number(waitMs), staleMs: Number(staleMs) });
} catch (e) {
  out.err = e instanceof StoreLockError ? 'StoreLockError held=' + e.held : String(e && e.stack || e);
}
out.took = Date.now() - t0;
process.stdout.write(JSON.stringify(out));
`;
function writerArgs(w, { ns = '', waitMs = 150, staleMs = 15000, holdMs = 0, ready = '' } = {}) {
  return ['--input-type=module', '-e', WRITER, '--', STORE_IO, w.storePath, ns, String(waitMs), String(staleMs), String(holdMs), ready];
}
function writer(w, opts) {
  const r = spawnSync(process.execPath, writerArgs(w, opts), { encoding: 'utf8' });
  assert.equal(r.status, 0, `the writer exited ${r.status}: ${r.stderr}`);
  return JSON.parse(r.stdout);
}

test('in a child pid namespace an initial-namespace writer\'s lock stamped with a dead pid and a fresh ts is left alone: the writer waits the bound out and refuses as held', () => {
  const w = world();
  const stamp = `${deadPid()} ${Date.now()}\n`;
  fs.writeFileSync(w.lockPath, stamp);
  const out = writer(w, { ns: CHILD_NS, waitMs: 150 });
  assert.equal(out.ran, false, 'a pid this process cannot see was read as a dead writer\'s, and its lock broken');
  assert.equal(out.err, 'StoreLockError held=true');
  assert.ok(out.took >= 150, `waited ${out.took} ms`);
  assert.equal(fs.readFileSync(w.lockPath, 'utf8'), stamp, 'the lock is intact');
  assert.deepEqual(fs.readdirSync(w.dir), [path.basename(w.lockPath)], 'no claim was left either');
});

test('in a child pid namespace a stamp past the stale bound is still broken, whatever its pid', () => {
  const w = world();
  fs.writeFileSync(w.lockPath, `${process.pid} ${Date.now() - 20000}\n`);   // a live pid, a stamp 20 s old
  const out = writer(w, { ns: CHILD_NS, waitMs: 1000, staleMs: 15000 });
  assert.equal(out.err, null);
  assert.equal(out.ran, true);
  assert.ok(out.took < 1000, `no wait behind a stamp past the bound (took ${out.took} ms)`);
  assert.deepEqual(fs.readdirSync(w.dir), []);
});

test('in the initial pid namespace the dead pid\'s lock is broken at once, as before; without the stand-in, this machine judges by its own namespace', () => {
  const w = world();
  fs.writeFileSync(w.lockPath, `${deadPid()} ${Date.now()}\n`);
  const init = writer(w, { ns: INIT_NS, waitMs: 1000 });
  assert.equal(init.err, null);
  assert.equal(init.ran, true, 'a dead pid in the writer\'s own namespace is a dead writer');
  assert.ok(init.took < 1000, `no wait behind a dead writer (took ${init.took} ms)`);
  assert.deepEqual(fs.readdirSync(w.dir), []);
  // the control on the seam: the real link, read by this process too
  const here = ownNs();
  fs.writeFileSync(w.lockPath, `${deadPid()} ${Date.now()}\n`);
  const plain = writer(w, { waitMs: 150 });
  if (here === null || here === INIT_NS) {
    assert.equal(plain.err, null, `this process is in the initial namespace (${here}), so the dead pid's lock is broken: ${plain.err}`);
    assert.equal(plain.ran, true);
  } else {
    assert.equal(plain.ran, false, `this process is in a child namespace (${here}), so the pid is not judged`);
    assert.equal(plain.err, 'StoreLockError held=true');
  }
});

test('a writer in a child pid namespace stamps "pid ts" and then "ns <inode>"; one in the initial namespace stamps "pid ts" alone', () => {
  const w = world();
  const child = writer(w, { ns: CHILD_NS });
  assert.equal(child.err, null);
  assert.equal(child.ran, true);
  assert.match(child.seen, new RegExp(`^\\d+ \\d+\\nns ${inoOf(CHILD_NS)}\\n$`), `the lock names the writer's namespace: ${JSON.stringify(child.seen)}`);
  const init = writer(w, { ns: INIT_NS });
  assert.equal(init.err, null);
  assert.match(init.seen, /^\d+ \d+\n$/, `an initial-namespace writer's lock is the stamp alone: ${JSON.stringify(init.seen)}`);
  assert.deepEqual(fs.readdirSync(w.dir), [], 'both released');
});

test('a child-namespace writer\'s live lock whose pid is a free number here is left alone by a writer in the initial namespace: it waits the bound out and refuses as held', () => {
  // What a sandboxed CLI's lock looks like from outside: its in-namespace pid (small, climbing with
  // every command the session ran) is a number no process here has, and the lock names the sandbox.
  const w = world();
  const stamp = `${deadPid()} ${Date.now()}\nns ${inoOf(CHILD_NS)}\n`;
  fs.writeFileSync(w.lockPath, stamp);
  const out = writer(w, { ns: INIT_NS, waitMs: 150 });
  assert.equal(out.ran, false, 'the sandboxed writer\'s live lock was broken and the write went through');
  assert.equal(out.err, 'StoreLockError held=true');
  assert.ok(out.took >= 150, `waited ${out.took} ms`);
  assert.equal(fs.readFileSync(w.lockPath, 'utf8'), stamp, 'the lock is intact');
  assert.deepEqual(fs.readdirSync(w.dir), [path.basename(w.lockPath)], 'no claim was left either');
  // the same without the stand-in, where this machine is in the initial namespace
  if (ownNs() === INIT_NS) {
    const plain = writer(w, { waitMs: 150 });
    assert.equal(plain.ran, false);
    assert.equal(plain.err, 'StoreLockError held=true');
    assert.equal(fs.readFileSync(w.lockPath, 'utf8'), stamp, 'the lock is intact');
  }
  // a stamp past the bound is a dead writer's whatever namespace it names
  fs.writeFileSync(w.lockPath, `${deadPid()} ${Date.now() - 20000}\nns ${inoOf(CHILD_NS)}\n`);
  const old = writer(w, { ns: INIT_NS, waitMs: 1000 });
  assert.equal(old.err, null);
  assert.equal(old.ran, true);
  assert.ok(old.took < 1000, `no wait behind a stamp past the bound (took ${old.took} ms)`);
  assert.deepEqual(fs.readdirSync(w.dir), []);
});

test('the pid is judged in the namespace that stamped it: read from that namespace a dead pid\'s lock is broken at once; read from a third namespace it is waited out', () => {
  const w = world();
  const stamp = `${deadPid()} ${Date.now()}\nns ${inoOf(CHILD_NS)}\n`;
  fs.writeFileSync(w.lockPath, stamp);
  const third = writer(w, { ns: CHILD_NS_2, waitMs: 150 });
  assert.equal(third.ran, false, 'a namespace that cannot judge the pid broke the lock');
  assert.equal(third.err, 'StoreLockError held=true');
  assert.equal(fs.readFileSync(w.lockPath, 'utf8'), stamp, 'the lock is intact');
  const same = writer(w, { ns: CHILD_NS, waitMs: 1000 });
  assert.equal(same.err, null);
  assert.equal(same.ran, true, 'in its own namespace the dead pid is a dead writer');
  assert.ok(same.took < 1000, `no wait behind a dead writer (took ${same.took} ms)`);
  assert.deepEqual(fs.readdirSync(w.dir), []);
});

test('a real child pid namespace: track-comment against a lock a live process outside holds prints the line for a held lock and exits 1, the lock intact; a holder inside stamps the namespace, and a writer outside waits behind it', async (t) => {
  const probe = spawnSync('unshare', ['-Urpf', '--mount-proc', process.execPath, '-e', 'process.stdout.write(require("fs").readlinkSync("/proc/self/ns/pid"))'], { encoding: 'utf8' });
  if (probe.status !== 0 || !/^pid:\[\d+\]$/.test(probe.stdout) || probe.stdout === INIT_NS || probe.stdout === ownNs()) {
    t.skip(`no unprivileged child pid namespace here (unshare exit ${probe.status}: ${(probe.stderr || '').trim()})`);
    return;
  }
  const w = world();
  const stamp = `${process.pid} ${Date.now()}\n`;   // this process: alive outside the namespace, and this test runs for less than the stale bound
  fs.writeFileSync(w.lockPath, stamp);
  const env = { ...process.env };
  for (const k of ['TRACKCHANGES_ROOT', 'TRACKCHANGES_SESSION', 'ROMP_SID', 'ROMP_SESSION_NAME']) delete env[k];
  const t0 = Date.now();
  const r = spawnSync('unshare', ['-Urpf', '--mount-proc', process.execPath, TRACK_COMMENT, '--file', w.note, '--anchor', 'Step one', '--note', 'Which cache?'], { env, encoding: 'utf8' });
  const took = Date.now() - t0;
  assert.equal(r.status, 1, `exit ${r.status}: ${r.stdout} ${r.stderr}`);
  assert.equal(r.stdout, '');
  assert.equal(r.stderr, 'another editor is writing this file; retry\n');
  assert.ok(took >= 2000, `waited the bound out (${took} ms)`);
  assert.equal(fs.readFileSync(w.lockPath, 'utf8'), stamp, 'the live lock was not broken');
  assert.equal(fs.existsSync(w.storePath), false, 'nothing was written');
  fs.unlinkSync(w.lockPath);

  // The other direction: a holder inside the namespace, this process outside it.
  const ready = path.join(w.root, 'ready');
  const holder = spawn('unshare', ['-Urpf', '--mount-proc', process.execPath, ...writerArgs(w, { waitMs: 1000, holdMs: 1500, ready })], { stdio: ['ignore', 'pipe', 'pipe'] });
  let stdout = '', stderr = '';
  holder.stdout.on('data', (d) => { stdout += d; });
  holder.stderr.on('data', (d) => { stderr += d; });
  const done = new Promise((resolve) => holder.on('close', (code) => resolve(code)));
  const until = Date.now() + 8000;
  while (!fs.existsSync(ready) && Date.now() < until) sleepMs(5);
  assert.ok(fs.existsSync(ready), `the holder took its lock (${stderr})`);
  const held = fs.readFileSync(w.lockPath, 'utf8');
  const m = /^\d+ \d+\nns (\d+)\n$/.exec(held);
  assert.ok(m, `the holder's lock names its namespace: ${JSON.stringify(held)}`);
  const here = ownNs();
  if (here) assert.notEqual(m[1], inoOf(here), 'a namespace other than this process\'s');
  const t1 = Date.now();
  assert.throws(() => withStoreLock(w.storePath, () => {}, { waitMs: 300 }), (e) => e instanceof StoreLockError && e.held === true);
  assert.ok(Date.now() - t1 >= 300, 'this process waited the bound out behind the sandboxed holder');
  assert.equal(fs.readFileSync(w.lockPath, 'utf8'), held, 'the live lock was not broken');
  const code = await done;
  assert.equal(code, 0, `the holder exited ${code}: ${stderr}`);
  const out = JSON.parse(stdout);
  assert.equal(out.err, null);
  assert.equal(out.ran, true);
  assert.equal(fs.existsSync(w.lockPath), false, 'released');
});
