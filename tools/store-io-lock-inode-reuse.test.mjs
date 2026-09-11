// store-io's lock (withStoreLock; plans/file-review.md, decision 49; vendor patch 0008) removes a dead
// lock or a dead claim only while the entry at the name is still the inode it judged. Judged by inode
// NUMBER alone, that guard is defeated by the filesystem's reuse of the number: an unlink and then a
// create in one folder hands the new entry the number just freed (ext4 did so 20 times of 20), so a
// breaker suspended past the stale bound between its claim check and its look for the unlink removed
// the fresh live lock a waiter had put at the name (the waiter had broken the breaker's stale claim by
// its age and then the dead lock) and entered beside that waiter: the lost update the lock exists to
// close, on the break path (the review of 2026-09-11). Now the judged entry's descriptor stays open
// from the judgment through the unlink, and an inode with a descriptor open keeps its number, so the
// fresh lock is another inode and is left alone. The cases in tools/store-io-lock.test.mjs that put the
// fresh entry under a NEW number (a create beside, then a rename) hold with the descriptor closed too;
// these two do not:
//   * in-process, one interleaving driven by hand: the breaker is this process, and before its look for
//     the unlink (the third read-only open of the lock: the waiter's look, the judgment under the claim,
//     the look for the unlink) the waiter's work is done at the names by unlink and create. This is the
//     pin: with the descriptor closed after the judgment it fails every run on a filesystem that reuses
//     inode numbers, the fresh lock taking the dead lock's number.
//   * with real processes: a breaker child that stalls at that look past the stale bound, and a real
//     writer that arrives during the stall, breaks the stalled claim by its age and the dead lock,
//     writes and leaves; the breaker waits for it instead of entering beside it. The defect's own shape
//     (a claim is created and freed between the dead lock's unlink and the fresh lock's create, so the
//     allocator hands back the dead lock's number in most rounds, not all: 1 of 3 here); with the
//     descriptor closed it fails when it does.
// Synthetic paths only, under a scratch directory.
// Run: node --test tools/store-io-lock-inode-reuse.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { storeLockPathFor, withStoreLock, StoreLockError } from '../vendor/track-changents/store-io.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const STORE_IO = pathToFileURL(path.resolve(HERE, '..', 'vendor', 'track-changents', 'store-io.mjs')).href;
// inspectLock's open: read-only, no link followed, non-blocking.
const LOOK = fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-store-io-lock-reuse-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
// A root with a landmark and its `.trackchanges/`; the sidecar path of one note in it.
function world() {
  const root = path.join(SCRATCH, `w${++worlds}`, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  const dir = path.join(root, '.trackchanges');
  fs.mkdirSync(dir);
  const storePath = path.join(dir, 'docs%2Freport.md.json');
  return { root, dir, storePath, lockPath: storeLockPathFor(storePath) };
}

// The pid of a process that has exited (spawnSync returns only after it did).
function deadPid() {
  const gone = spawnSync(process.execPath, ['-e', ''], { encoding: 'utf8' });
  assert.equal(gone.status, 0);
  return gone.pid;
}

test('a breaker whose look for the unlink comes after a waiter broke its stale claim and the dead lock, and put a fresh lock at the name, leaves that lock alone: the judged inode was still open, so the fresh lock could not take its number', () => {
  const w = world();
  const claim = `${w.lockPath}.break`;
  const gone = deadPid();
  fs.writeFileSync(w.lockPath, `${gone} ${Date.now()}\n`);
  const dead = fs.statSync(w.lockPath, { bigint: true });
  const fresh = `${process.pid} ${Date.now()}\n`;   // the waiter's lock, live
  const real = fs.openSync;
  let looks = 0;
  let swapped = null;
  fs.openSync = function (p, flags, ...rest) {
    if (p === w.lockPath && flags === LOOK && ++looks === 3) {
      // The waiter's work while this breaker was suspended past the bound: the breaker's claim judged
      // stale by its age and removed, the dead lock removed, the waiter's own lock created and stamped
      // at the name, its claim released. An unlink and then a create at one name: the fresh lock gets
      // the freed number back unless the judged inode is still open.
      fs.unlinkSync(claim);
      fs.unlinkSync(w.lockPath);
      fs.writeFileSync(w.lockPath, fresh, { flag: 'wx' });
      swapped = fs.statSync(w.lockPath, { bigint: true });
    }
    return real.call(fs, p, flags, ...rest);
  };
  let ran = false;
  let err = null;
  try { withStoreLock(w.storePath, () => { ran = true; }, { waitMs: 150 }); } catch (e) { err = e; } finally { fs.openSync = real; }
  assert.ok(swapped, `the look for the unlink never came (${looks} looks at the lock)`);
  assert.notEqual(swapped.ino, dead.ino, 'the judged inode was still open in the breaker, so the fresh lock could not take its number');
  assert.equal(ran, false, 'the breaker removed the fresh live lock and entered beside its writer');
  assert.ok(err instanceof StoreLockError, String(err && err.stack));
  assert.equal(err.held, true, 'held: the fresh lock is a live writer\'s');
  assert.equal(fs.readFileSync(w.lockPath, 'utf8'), fresh, 'the fresh lock stands');
  assert.deepEqual(fs.readdirSync(w.dir), [path.basename(w.lockPath)], 'the breaker\'s claim went with its release; nothing else was left');
  fs.unlinkSync(w.lockPath);
});

// One real writer: spins to the instant `at`, takes the lock with the given bounds, and inside fn puts a
// marker down, counts the markers it sees (a second one is another writer inside with it), holds for
// `hold` ms, counts again, and leaves. With `stallMs`, it is the breaker under test: it stalls that long
// at its look for the unlink (the third read-only open of the lock in this process). Prints one JSON line.
const WRITER = `
import fs from 'node:fs';
import path from 'node:path';
const [storeIo, store, at, hold, markers, tag, waitMs, staleMs, stallMs] = process.argv.slice(1);   // -e: no script path in argv
const { withStoreLock, StoreLockError } = await import(storeIo);
const out = { tag, held: false, overlap: 0, in: null, out: null, stalled: null, err: null };
if (Number(stallMs) > 0) {
  const LOOK = fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK;
  const lock = store + '.lock';
  const real = fs.openSync;
  let looks = 0;
  fs.openSync = function (p, flags, ...rest) {
    if (p === lock && flags === LOOK && ++looks === 3) {
      out.stalled = Date.now();
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, Number(stallMs));
    }
    return real.call(fs, p, flags, ...rest);
  };
}
while (Date.now() < Number(at)) { /* spin */ }
try {
  withStoreLock(store, () => {
    out.held = true; out.in = Date.now();
    const seen = () => fs.readdirSync(markers).filter((n) => n.startsWith('h-')).length;
    const mine = path.join(markers, 'h-' + tag);
    fs.writeFileSync(mine, '', { flag: 'wx' });
    out.overlap = Math.max(out.overlap, seen());
    const until = Date.now() + Number(hold);
    while (Date.now() < until) { /* hold */ }
    out.overlap = Math.max(out.overlap, seen());
    fs.unlinkSync(mine);
    out.out = Date.now();
  }, { waitMs: Number(waitMs), staleMs: Number(staleMs) });
} catch (e) {
  out.err = e instanceof StoreLockError ? 'StoreLockError held=' + e.held : String(e && e.stack || e);
}
process.stdout.write(JSON.stringify(out) + '\\n');
`;
function writer(w, markers, { at, hold, tag, waitMs, staleMs, stallMs = 0 }) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, ['--input-type=module', '-e', WRITER, '--', STORE_IO, w.storePath, String(at), String(hold), markers, tag, String(waitMs), String(staleMs), String(stallMs)]);
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8'); child.stdout.on('data', (c) => { stdout += c; });
    child.stderr.setEncoding('utf8'); child.stderr.on('data', (c) => { stderr += c; });
    child.on('close', () => {
      let json = null;
      try { json = JSON.parse(stdout); } catch { json = { tag, err: `no JSON line: ${stdout} ${stderr}` }; }
      resolve(json);
    });
  });
}

test('real processes: a breaker stalled past the stale bound at its look for the unlink, whose claim and dead lock a waiter broke meanwhile, waits for that waiter\'s write instead of removing its lock and entering beside it', async () => {
  const w = world();
  const markers = path.join(path.dirname(w.root), 'markers');
  fs.mkdirSync(markers);
  fs.writeFileSync(w.lockPath, `${deadPid()} ${Date.now()}\n`);
  // The bound is 1000 ms here so the stall (1500 ms) puts the breaker's claim past it while the waiter
  // (arriving 300 ms in) is looking, and the waiter's fresh lock (about 500 ms old when the breaker
  // wakes) is not: the breaker finds a live lock at the name and must wait for it.
  const base = Date.now() + 200;
  const [X, Y] = await Promise.all([
    writer(w, markers, { at: base, hold: 50, tag: 'X', waitMs: 4000, staleMs: 1000, stallMs: 1500 }),
    writer(w, markers, { at: base + 300, hold: 600, tag: 'Y', waitMs: 4000, staleMs: 1000 }),
  ]);
  for (const j of [X, Y]) assert.equal(j.err, null, `${j.tag}: ${j.err}`);
  assert.ok(X.stalled, 'the breaker reached its look for the unlink and stalled there');
  assert.ok(Y.in > X.stalled && Y.in < X.stalled + 1500, `the waiter broke in during the stall (Y in at ${Y.in - X.stalled} ms of it)`);
  assert.equal(Y.held, true, 'the waiter wrote');
  assert.equal(X.held, true, 'the breaker wrote, after the waiter');
  assert.ok(X.in >= Y.out, `the breaker entered ${Y.out - X.in} ms before the waiter left: it removed the waiter's live lock`);
  assert.equal(Y.overlap, 1, 'the waiter had the lock alone');
  assert.equal(X.overlap, 1);
  assert.deepEqual(fs.readdirSync(w.dir), [], `left behind: ${fs.readdirSync(w.dir)}`);
});
