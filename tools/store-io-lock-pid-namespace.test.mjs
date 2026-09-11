// withStoreLock (plans/file-review.md, decision 49; vendor patch 0008) judges a lock's writer dead by
// kill(pid, 0) answering ESRCH. From a child pid namespace (a sandboxed tool shell: bubblewrap's
// --unshare-pid, which the Codex and Claude Code sandboxes both pass) every process outside is ESRCH,
// alive or not, so a CLI in such a sandbox read an editor host's live lock as a dead writer's, broke it
// at once and wrote inside the host's load-to-rename: the lost update the lock exists to close (the
// review of 2026-09-11). Now a writer whose own pid namespace is not the initial one (/proc/self/ns/pid
// against PROC_PID_INIT_INO) judges a lock by its stamp's age alone. Each case is a child process; the
// namespace is read through a stand-in for fs.readlinkSync installed before store-io is imported, so
// the cases run on any machine, and one real child namespace where `unshare` can make one unprivileged
// (skipped where it cannot):
//   * in a child namespace, a lock stamped with a dead pid and a fresh ts is left alone: the writer
//     waits the bound out and refuses as held
//   * there, a stamp past the stale bound is still broken
//   * in the initial namespace (the stand-in says so), the dead pid's lock is broken at once, as before
//   * without the stand-in, this machine: the same when this process is in the initial namespace, the
//     wait when it is not
//   * a real child pid namespace: the vendored track-comment, against a lock a live process outside it
//     holds, prints the line for a held lock and exits 1, the lock intact and nothing written
// Synthetic paths only, under a scratch directory.
// Run: node --test tools/store-io-lock-pid-namespace.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { storeLockPathFor, storePathFor } from '../vendor/track-changents/store-io.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const VENDOR = fs.realpathSync(path.resolve(HERE, '..', 'vendor', 'track-changents'));
const STORE_IO = pathToFileURL(path.join(VENDOR, 'store-io.mjs')).href;
const TRACK_COMMENT = path.join(VENDOR, 'cli', 'track-comment.mjs');
const INIT_NS = 'pid:[4026531836]';    // PROC_PID_INIT_INO, the initial pid namespace on every Linux
const CHILD_NS = 'pid:[4026532101]';   // any other: a namespace of its own

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

// One writer in a child process: with `ns`, fs.readlinkSync answers it for /proc/self/ns/pid before
// store-io is imported (store-io reads the link once, on its first judgment); then one withStoreLock.
const WRITER = `
import fs from 'node:fs';
const [storeIo, store, ns, waitMs, staleMs] = process.argv.slice(1);   // -e: no script path in argv
if (ns) {
  const real = fs.readlinkSync;
  fs.readlinkSync = function (p, ...rest) { return p === '/proc/self/ns/pid' ? ns : real.call(fs, p, ...rest); };
}
const { withStoreLock, StoreLockError } = await import(storeIo);
const out = { ran: false, err: null, took: 0 };
const t0 = Date.now();
try {
  withStoreLock(store, () => { out.ran = true; }, { waitMs: Number(waitMs), staleMs: Number(staleMs) });
} catch (e) {
  out.err = e instanceof StoreLockError ? 'StoreLockError held=' + e.held : String(e && e.stack || e);
}
out.took = Date.now() - t0;
process.stdout.write(JSON.stringify(out));
`;
function writer(w, { ns = '', waitMs = 150, staleMs = 15000 } = {}) {
  const r = spawnSync(process.execPath, ['--input-type=module', '-e', WRITER, '--', STORE_IO, w.storePath, ns, String(waitMs), String(staleMs)], { encoding: 'utf8' });
  assert.equal(r.status, 0, `the writer exited ${r.status}: ${r.stderr}`);
  return JSON.parse(r.stdout);
}

test('in a child pid namespace a lock stamped with a dead pid and a fresh ts is left alone: the writer waits the bound out and refuses as held', () => {
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
  let here = null;
  try { here = fs.readlinkSync('/proc/self/ns/pid'); } catch { /* no /proc: every pid is judged */ }
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

test('a real child pid namespace: track-comment against a lock a live process outside holds prints the line for a held lock and exits 1, the lock intact', (t) => {
  const probe = spawnSync('unshare', ['-Urpf', '--mount-proc', process.execPath, '-e', 'process.stdout.write(require("fs").readlinkSync("/proc/self/ns/pid"))'], { encoding: 'utf8' });
  if (probe.status !== 0 || !/^pid:\[\d+\]$/.test(probe.stdout) || probe.stdout === INIT_NS) {
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
});
