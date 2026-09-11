// store-io's lock, `<sidecar>.lock` (withStoreLock; plans/file-review.md, decision 49; vendor patch
// 0008), on the paths the review of 2026-09-11 found open. Each case here failed against the lock before
// the review round that added it and holds now:
//   * the break of a dead writer's lock has ONE winner. Judged and removed by name alone, two waiters
//     that read one dead lock together both removed it, the second taking away the first's fresh
//     lock, and both wrote: three real writers on a dead pid's lock held together in 54 rounds of 100.
//     Now the breakers serialize on `<lock>.break` and judge the lock again under it: never together,
//     with real processes racing to one instant; a live claim excludes every other breaker and a dead
//     breaker's claim is removed by the lock's own rule.
//   * a holder broken as stale while alive (a writer stalled past the bound, a machine suspended
//     mid-write) releases only its own lock: the breaker's fresh lock at the name is left alone, so a
//     third writer waits for the breaker instead of entering beside it.
//   * a stamp that cannot be written (the disk full) leaves no empty lock behind, which its age alone
//     would have held every writer to `busy` for fifteen seconds, and no folder made for it; the
//     failure is a StoreLockError naming the lock, never a raw OS error.
//   * two first writers on two sidecars of a fresh root leave no `.trackchanges/` behind: the maker
//     hands the folder to the lock still in it, and its holder, or the breaker of that lock should the
//     holder die, takes the folder away; a folder the lock did not make, or one holding anything else,
//     stays.
//   * a lock this process cannot read refuses as a StoreLockError with the OS error, naming the lock,
//     so a CLI prints its one line and a host refuses; the lock is left alone.
//   * (second round) a dead lock or claim is removed only while the entry at its name is still the inode
//     judged: a fresh entry another writer put there between the judging look and the unlink is left
//     alone, so a waiter never breaks beside a live breaker, nor a breaker beside a fresh writer.
//   * (second round) a maker that gives up waiting takes the folder it made away, or hands it to the lock
//     that outwaited it; left out, an empty folder stayed behind such a maker.
//   * (second round) the stamp appends (O_APPEND) and a holder reads its lock back through its own
//     descriptor after the unlink, so a handover line put on the lock, or on the breaker's claim, between
//     its create and its stamp, or between the release's look and its unlink, is honored, and a waiter
//     finds the stamp behind the line; written at the start of the file, the stamp took the line's place
//     and the folder stayed.
// Real writers here are node processes importing the vendored store-io and spinning to one shared
// instant; the in-process cases drive one interleaving by hand. Synthetic paths only, under a scratch
// directory.
// Run: node --test tools/store-io-lock.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { storeLockPathFor, withStoreLock, StoreLockError, STORE_LOCK_WAIT_MS } from '../vendor/track-changents/store-io.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const STORE_IO = pathToFileURL(path.resolve(HERE, '..', 'vendor', 'track-changents', 'store-io.mjs')).href;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-store-io-lock-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
// A root with a landmark and, unless `fresh`, its `.trackchanges/`; the sidecar path of one note in it.
function world(fresh) {
  const root = path.join(SCRATCH, `w${++worlds}`, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  const dir = path.join(root, '.trackchanges');
  if (!fresh) fs.mkdirSync(dir);
  const storePath = path.join(dir, 'docs%2Freport.md.json');
  return { root, dir, storePath, lockPath: storeLockPathFor(storePath) };
}

// The pid of a process that has exited (spawnSync returns only after it did).
function deadPid() {
  const gone = spawnSync(process.execPath, ['-e', ''], { encoding: 'utf8' });
  assert.equal(gone.status, 0);
  return gone.pid;
}

// One real writer: spins to the instant `at`, takes the lock with the given bounds, and inside fn
// registers a marker, counts the markers it sees (a second one is another writer inside with it),
// holds for `hold` ms, counts again, and leaves. Prints one JSON line.
const WRITER = `
import fs from 'node:fs';
import path from 'node:path';
const [storeIo, store, at, hold, markers, tag, waitMs, staleMs] = process.argv.slice(1);   // -e: no script path in argv
const { withStoreLock, StoreLockError } = await import(storeIo);
while (Date.now() < Number(at)) { /* spin */ }
const out = { tag, held: false, overlap: 0, in: null, out: null, err: null };
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
function writer(w, markers, { at, hold, tag, waitMs = STORE_LOCK_WAIT_MS, staleMs = 15000 }) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, ['--input-type=module', '-e', WRITER, '--', STORE_IO, w.storePath, String(at), String(hold), markers, tag, String(waitMs), String(staleMs)]);
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
function markersDir(w) {
  const d = path.join(path.dirname(w.root), 'markers');
  fs.mkdirSync(d, { recursive: true });
  for (const n of fs.readdirSync(d)) fs.unlinkSync(path.join(d, n));
  return d;
}

// ── the break has one winner ────────────────────────────────────────

test('real writers racing to one instant on a dead pid\'s lock, or on a stamp past the bound, never hold together, and every one of them writes', async () => {
  const w = world(false);
  const markers = markersDir(w);
  const gone = deadPid();
  let rounds = 0;
  for (const seed of [() => `${gone} ${Date.now()}\n`, () => `${process.pid} ${Date.now() - 20000}\n`]) {
    for (let r = 0; r < 12; r++, rounds++) {
      for (const n of fs.readdirSync(w.dir)) fs.unlinkSync(path.join(w.dir, n));
      fs.writeFileSync(w.lockPath, seed());
      const at = Date.now() + 200;
      const res = await Promise.all([0, 1, 2].map((i) => writer(w, markers, { at, hold: 15, tag: `${rounds}-${i}` })));
      for (const j of res) {
        assert.equal(j.err, null, `writer ${j.tag}: ${j.err}`);
        assert.equal(j.held, true, `writer ${j.tag} wrote`);
        assert.equal(j.overlap, 1, `writer ${j.tag} saw ${j.overlap} writers inside the lock at once (round ${rounds})`);
      }
      assert.deepEqual(fs.readdirSync(w.dir), [], `round ${rounds} left ${fs.readdirSync(w.dir)} behind`);
    }
  }
  assert.equal(rounds, 24);
});

test('a live breaker\'s claim excludes every other breaker: a dead lock under it is left and the waiter refuses after the wait; a dead breaker\'s claim is removed and the break proceeds', () => {
  const w = world(false);
  const claim = `${w.lockPath}.break`;
  const gone = deadPid();
  fs.writeFileSync(w.lockPath, `${gone} ${Date.now()}\n`);
  fs.writeFileSync(claim, `${process.pid} ${Date.now()}\n`);   // this process, mid-break
  const t0 = Date.now();
  let err = null;
  try { withStoreLock(w.storePath, () => 'ran', { waitMs: 120 }); } catch (e) { err = e; }
  assert.ok(err instanceof StoreLockError, String(err));
  assert.equal(err.held, true, 'the waiter waited out the bound, as behind any live writer');
  assert.ok(Date.now() - t0 >= 120);
  assert.match(fs.readFileSync(w.lockPath, 'utf8'), new RegExp(`^${gone} \\d+\\n$`), 'the dead lock is untouched under a live claim');
  assert.ok(fs.existsSync(claim), 'the live claim is left alone');
  // the breaker died holding its claim: the claim is a dead writer's, judged by the lock's own rule
  fs.writeFileSync(claim, `${gone} ${Date.now()}\n`);
  let ran = false;
  const t1 = Date.now();
  withStoreLock(w.storePath, () => { ran = true; }, { waitMs: 1000 });
  assert.equal(ran, true);
  assert.ok(Date.now() - t1 < 1000, `no wait behind a dead breaker (took ${Date.now() - t1} ms)`);
  assert.equal(fs.existsSync(w.lockPath), false);
  assert.equal(fs.existsSync(claim), false, 'the dead claim went with the break, and the breaker\'s own with its release');
  assert.deepEqual(fs.readdirSync(w.dir), []);
});

// ── a holder releases only its own lock ─────────────────────────────

test('a holder whose lock another writer broke while it was alive leaves that writer\'s lock alone at release', () => {
  const w = world(false);
  const foreign = `${deadPid()} ${Date.now()}\n`;   // any other writer's stamp; its content is what must survive
  const out = withStoreLock(w.storePath, () => {
    // the breaker's work, done under the claim while this holder runs: the lock judged stale and
    // removed, a fresh one created at the name
    fs.unlinkSync(w.lockPath);
    fs.writeFileSync(w.lockPath, foreign, { flag: 'wx' });
    return 'ran';
  });
  assert.equal(out, 'ran');
  assert.equal(fs.readFileSync(w.lockPath, 'utf8'), foreign, 'the breaker\'s lock stands after the broken holder left');
  assert.ok(fs.existsSync(w.dir), 'a folder the lock did not make stays');
  fs.unlinkSync(w.lockPath);
});

test('real writers: A runs past the bound, B breaks A\'s lock and writes, C arrives while B writes and waits for B (before: A\'s release removed B\'s lock and C entered beside B)', async () => {
  const w = world(false);
  const markers = markersDir(w);
  const base = Date.now() + 200;
  const [A, B, C] = await Promise.all([
    writer(w, markers, { at: base, hold: 600, tag: 'A', staleMs: 100, waitMs: 1500 }),
    writer(w, markers, { at: base + 250, hold: 800, tag: 'B', staleMs: 100, waitMs: 1500 }),
    writer(w, markers, { at: base + 750, hold: 50, tag: 'C', staleMs: 100000, waitMs: 1500 }),
  ]);
  for (const j of [A, B, C]) assert.equal(j.err, null, `${j.tag}: ${j.err}`);
  assert.ok(B.in < A.out, 'B broke A\'s lock while A was inside (the stale bound at 100 ms for this test)');
  assert.ok(C.in >= B.out, `C entered ${B.out - C.in} ms before B left`);
  assert.equal(C.overlap, 1);
  assert.deepEqual(fs.readdirSync(w.dir), [], 'no lock left');
});

// ── a stamp that cannot be written ──────────────────────────────────

test('a stamp write that fails after the O_EXCL create leaves no lock and no folder behind, fails as a StoreLockError naming the lock, and the next writer takes the lock at once', () => {
  const w = world(true);
  const real = fs.writeFileSync;
  let armed = true;
  fs.writeFileSync = function (target, ...rest) {
    if (armed && typeof target === 'number') {
      armed = false;
      const e = new Error('ENOSPC: no space left on device, write');
      e.code = 'ENOSPC';
      throw e;
    }
    return real.call(fs, target, ...rest);
  };
  let ran = false;
  let err = null;
  try { withStoreLock(w.storePath, () => { ran = true; }); } catch (e) { err = e; } finally { fs.writeFileSync = real; }
  assert.equal(ran, false);
  assert.ok(err instanceof StoreLockError, `a StoreLockError, not a raw OS error: ${err && err.stack}`);
  assert.equal(err.held, false);
  assert.equal(err.message, `cannot write ${w.lockPath}: ENOSPC: no space left on device, write`);
  assert.equal(err.cause.code, 'ENOSPC');
  assert.equal(fs.existsSync(w.lockPath), false, 'no empty lock left to be judged by its age');
  assert.equal(fs.existsSync(w.dir), false, 'the folder made for the lock went with it');
  const t0 = Date.now();
  assert.equal(withStoreLock(w.storePath, () => 'ran'), 'ran');
  assert.ok(Date.now() - t0 < 500, `the next writer waited ${Date.now() - t0} ms`);
  assert.equal(fs.existsSync(w.dir), false);
});

// ── the folder made for a lock ──────────────────────────────────────

test('real writers: two first writes on two sidecars of a fresh root, neither landing anything, leave no .trackchanges/ behind', async () => {
  const w = world(true);
  const markers = markersDir(w);
  const other = { ...w, storePath: path.join(w.dir, 'docs%2Fother.md.json') };
  const base = Date.now() + 200;
  const [A, B] = await Promise.all([
    writer(w, markers, { at: base, hold: 300, tag: 'A' }),
    writer(other, markers, { at: base + 100, hold: 500, tag: 'B' }),
  ]);
  for (const j of [A, B]) assert.equal(j.err, null, `${j.tag}: ${j.err}`);
  assert.ok(A.out < B.out, 'A, which made the folder, left first, with B\'s lock still in it');
  assert.equal(fs.existsSync(w.dir), false, `an empty .trackchanges/ was left behind: ${fs.existsSync(w.dir) && fs.readdirSync(w.dir)}`);
});

test('the maker hands the folder to the lock still in it: a line on that lock, honored by its holder at release, or by the breaker of that lock when the holder died', () => {
  // the maker leaves while a sibling sidecar's lock is in the folder it made
  const w = world(true);
  const sibling = path.join(w.dir, 'docs%2Fother.md.json.lock');
  const gone = deadPid();
  withStoreLock(w.storePath, () => {
    fs.writeFileSync(sibling, `${gone} ${Date.now()}\n`, { flag: 'wx' });   // a second first writer's lock, as it takes it
  });
  assert.ok(fs.existsSync(w.dir), 'the folder stays while the other lock is in it');
  assert.match(fs.readFileSync(sibling, 'utf8'), new RegExp(`^${gone} \\d+\\nmade-dir\\n$`), 'the handover line is on the other lock');
  assert.equal(fs.existsSync(w.lockPath), false);
  // that writer died holding its lock: the next writer of its sidecar breaks the lock and inherits
  withStoreLock(path.join(w.dir, 'docs%2Fother.md.json'), () => 'ran');
  assert.equal(fs.existsSync(w.dir), false, 'the breaker of the handed lock took the folder away');
  // the maker leaves while only a breaker's claim is in the folder (the breaker between removing a
  // dead lock and taking its own): the line lands on the claim and the breaker carries it to its lock
  const w2 = world(false);   // the folder stands in for one a maker made and is about to hand over
  fs.writeFileSync(w2.lockPath, `${gone} ${Date.now()}\n`);
  const real = fs.writeFileSync;
  let stamps = 0;
  fs.writeFileSync = function (target, ...rest) {
    const r = real.call(fs, target, ...rest);
    if (typeof target === 'number' && ++stamps === 1) real.call(fs, target, 'made-dir\n');   // the first stamp is the claim's
    return r;
  };
  try { withStoreLock(w2.storePath, () => 'ran'); } finally { fs.writeFileSync = real; }
  assert.equal(stamps, 2, 'the claim\'s stamp, then the lock\'s');
  assert.equal(fs.existsSync(w2.dir), false, 'the breaker handed the folder through its claim took it away');
});

test('a holder handed the folder mid-hold takes it away when nothing else landed; one whose folder holds a sidecar, or that was never handed it, leaves the folder', () => {
  // handed mid-hold: the line lands on this holder's lock while it works, as the maker's release puts it
  const w = world(false);
  withStoreLock(w.storePath, () => { fs.appendFileSync(w.lockPath, 'made-dir\n'); });
  assert.equal(fs.existsSync(w.dir), false, 'the handed folder is gone');
  // handed, but a sidecar landed: the folder is in use
  const w2 = world(false);
  withStoreLock(w2.storePath, () => { fs.appendFileSync(w2.lockPath, 'made-dir\n'); fs.writeFileSync(w2.storePath, '{}'); });
  assert.ok(fs.existsSync(w2.dir) && fs.existsSync(w2.storePath), 'a folder with a sidecar stays');
  assert.equal(fs.existsSync(w2.lockPath), false);
  // never handed, nothing landed: a folder the lock did not make is not its to remove
  const w3 = world(false);
  withStoreLock(w3.storePath, () => 'ran');
  assert.ok(fs.existsSync(w3.dir), 'a pre-existing folder stays');
  assert.deepEqual(fs.readdirSync(w3.dir), []);
  // the maker's own lock never carries the line: the stamp is "pid ts" alone
  const w4 = world(true);
  let seen = null;
  withStoreLock(w4.storePath, () => { seen = fs.readFileSync(w4.lockPath, 'utf8'); });
  assert.match(seen, /^\d+ \d+\n$/);
  assert.equal(fs.existsSync(w4.dir), false);
});

// ── a lock this process cannot read ─────────────────────────────────

test('a lock this process cannot read refuses as a StoreLockError with held false, naming the lock and the OS error; the lock is left alone', { skip: typeof process.getuid === 'function' && process.getuid() === 0 ? 'root reads every file' : false }, () => {
  const w = world(false);
  fs.writeFileSync(w.lockPath, `${process.pid} ${Date.now()}\n`);
  fs.chmodSync(w.lockPath, 0);
  let err = null;
  try {
    try { withStoreLock(w.storePath, () => 'ran', { waitMs: 200 }); } catch (e) { err = e; }
  } finally {
    fs.chmodSync(w.lockPath, 0o644);
  }
  assert.ok(err instanceof StoreLockError, `a StoreLockError, not a raw OS error: ${err && err.stack}`);
  assert.equal(err.held, false, 'not "busy": the writer cannot tell whether the lock is live, and says so');
  assert.equal(err.lockPath, w.lockPath);
  assert.match(err.message, new RegExp(`^cannot read ${w.lockPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}: EACCES`));
  assert.equal(err.cause.code, 'EACCES');
  assert.ok(fs.existsSync(w.lockPath), 'left alone');
});

// ── a removal only of the inode judged (second round) ───────────────
// The hooks below stand in for another process at the one instant that matters: a public `fs` function
// (or `Date.now`) the lock calls at that step, wrapped to do the other writer's work there and then carry
// on. Tests in this file run one at a time, and every hook is restored in `finally`.

// Put a fresh entry at `p` under a NEW inode, as another writer's O_EXCL create after its remove would:
// created beside the old entry first, while the old inode still holds its number, and renamed over the
// name. An unlink and then a create hands the new file the old number back on this filesystem, and the
// inode check under test would pass it as the entry judged.
function replaceAt(p, content) {
  const tmp = `${p}.fresh`;
  fs.writeFileSync(tmp, content, { flag: 'wx' });
  fs.renameSync(tmp, p);
}

test('a dead breaker\'s claim replaced by another breaker\'s fresh claim after the judging look is left alone: the waiter waits behind the live breaker instead of breaking beside it', () => {
  const w = world(false);
  const claim = `${w.lockPath}.break`;
  const gone = deadPid();
  const t = Date.now();
  const deadLock = `${gone} ${t}\n`;
  const deadClaim = `${gone} ${t + 1}\n`;   // not the lock's text, so the hook tells the claim's read from the lock's
  const fresh = `${process.pid} ${t}\n`;   // the other breaker's claim, live
  fs.writeFileSync(w.lockPath, deadLock);
  fs.writeFileSync(claim, deadClaim);
  const real = fs.readFileSync;
  let armed = true;
  fs.readFileSync = function (target, ...rest) {
    const out = real.call(fs, target, ...rest);
    // the judging look at the dead claim has read it: before this waiter's unlink, another breaker
    // removes the dead claim and puts its own at the name
    if (armed && typeof target === 'number' && out === deadClaim) { armed = false; replaceAt(claim, fresh); }
    return out;
  };
  let ran = false;
  let err = null;
  try { withStoreLock(w.storePath, () => { ran = true; }, { waitMs: 150 }); } catch (e) { err = e; } finally { fs.readFileSync = real; }
  assert.equal(armed, false, 'the dead claim was judged');
  assert.equal(ran, false, 'the waiter took the lock beside the live breaker');
  assert.ok(err instanceof StoreLockError, String(err));
  assert.equal(err.held, true, 'held: a live breaker holds the claim');
  assert.equal(fs.readFileSync(claim, 'utf8'), fresh, 'the fresh claim was removed');
  assert.equal(fs.readFileSync(w.lockPath, 'utf8'), deadLock, 'the dead lock is untouched under the live claim');
  assert.deepEqual(fs.readdirSync(w.dir).sort(), [path.basename(w.lockPath), path.basename(claim)]);
});

test('a stale lock replaced by a fresh writer\'s lock after the breaker\'s judging look is left alone under the claim: the breaker waits behind that writer', () => {
  const w = world(false);
  const claim = `${w.lockPath}.break`;
  const deadLock = `${deadPid()} ${Date.now()}\n`;
  const fresh = `${process.pid} ${Date.now()}\n`;   // the writer that took the lock next, live
  fs.writeFileSync(w.lockPath, deadLock);
  const real = fs.readFileSync;
  let armed = true;
  fs.readFileSync = function (target, ...rest) {
    const out = real.call(fs, target, ...rest);
    // the breaker's judging look, under its claim (the waiter's own look before the claim is not it):
    // the stale holder releases and a fresh writer takes the lock before the breaker's unlink
    if (armed && typeof target === 'number' && out === deadLock && fs.existsSync(claim)) { armed = false; replaceAt(w.lockPath, fresh); }
    return out;
  };
  let ran = false;
  let err = null;
  try { withStoreLock(w.storePath, () => { ran = true; }, { waitMs: 150 }); } catch (e) { err = e; } finally { fs.readFileSync = real; }
  assert.equal(armed, false, 'the lock was judged under the claim');
  assert.equal(ran, false, 'the breaker removed the fresh lock and entered beside its writer');
  assert.ok(err instanceof StoreLockError, String(err));
  assert.equal(err.held, true, 'held: a live writer holds the lock');
  assert.equal(fs.readFileSync(w.lockPath, 'utf8'), fresh, 'the fresh lock stands');
  assert.equal(fs.existsSync(claim), false, 'the breaker released its claim');
  assert.deepEqual(fs.readdirSync(w.dir), [path.basename(w.lockPath)]);
});

// ── the folder made for a lock, at a wait given up (second round) ───

test('a maker that gives up waiting hands the folder it made to the lock that outwaited it: the line lands on that lock, and the folder goes with that lock', () => {
  const w = world(true);
  const foreign = `${process.pid} ${Date.now()}\n`;   // a live writer's stamp (this process's pid), never judged dead
  const real = fs.mkdirSync;
  let made = 0;
  fs.mkdirSync = function (target, ...rest) {
    const r = real.call(fs, target, ...rest);
    // another writer's first write on this sidecar takes the lock in the folder this maker just made
    if (target === w.dir) { made++; fs.writeFileSync(w.lockPath, foreign, { flag: 'wx' }); }
    return r;
  };
  let ran = false;
  let err = null;
  const t0 = Date.now();
  try { withStoreLock(w.storePath, () => { ran = true; }, { waitMs: 100 }); } catch (e) { err = e; } finally { fs.mkdirSync = real; }
  assert.equal(made, 1, 'the maker made the folder once');
  assert.equal(ran, false);
  assert.ok(err instanceof StoreLockError, String(err));
  assert.equal(err.held, true);
  assert.ok(Date.now() - t0 >= 100, 'the maker waited out the bound');
  assert.ok(fs.existsSync(w.dir), 'the folder stays while the other lock is in it');
  assert.equal(fs.readFileSync(w.lockPath, 'utf8'), `${foreign}made-dir\n`, 'the handover line is on the lock that outwaited the maker');
  assert.deepEqual(fs.readdirSync(w.dir), [path.basename(w.lockPath)], 'nothing else of the maker\'s is left');
  // that holder dies with the line on its lock: the next writer breaks it, inherits the duty and takes the folder away
  fs.writeFileSync(w.lockPath, `${deadPid()} ${Date.now()}\nmade-dir\n`);
  withStoreLock(w.storePath, () => 'ran');
  assert.equal(fs.existsSync(w.dir), false, 'the folder went with the handed lock');
});

test('a maker that gives up waiting as the lock that outwaited it is released takes the empty folder away', () => {
  const w = world(true);
  const realNow = Date.now;
  const foreign = `${process.pid} ${realNow()}\n`;
  const realMkdir = fs.mkdirSync;
  const realRead = fs.readFileSync;
  let made = false;
  let jumped = false;
  let released = false;
  fs.mkdirSync = function (target, ...rest) {
    const r = realMkdir.call(fs, target, ...rest);
    if (target === w.dir) { made = true; fs.writeFileSync(w.lockPath, foreign, { flag: 'wx' }); }
    return r;
  };
  // The clock the wait reads jumps past the bound (and short of the stale bound) at the first look after
  // the folder was made, so that look is the maker's last and it gives up right after it, whatever the
  // box's pace ...
  Date.now = function () {
    const t = realNow();
    if (made && !jumped) { jumped = true; return t + 1000; }
    return t;
  };
  // ... and the other holder releases between that look and the give-up.
  fs.readFileSync = function (target, ...rest) {
    const out = realRead.call(fs, target, ...rest);
    if (jumped && !released && typeof target === 'number' && out === foreign) { released = true; fs.unlinkSync(w.lockPath); }
    return out;
  };
  let ran = false;
  let err = null;
  try {
    withStoreLock(w.storePath, () => { ran = true; }, { waitMs: 100 });
  } catch (e) {
    err = e;
  } finally {
    Date.now = realNow; fs.mkdirSync = realMkdir; fs.readFileSync = realRead;
  }
  assert.deepEqual({ made, jumped, released }, { made: true, jumped: true, released: true }, 'the interleaving ran as written');
  assert.equal(ran, false);
  assert.ok(err instanceof StoreLockError, String(err));
  assert.equal(err.held, true);
  assert.equal(fs.existsSync(w.dir), false, 'an empty folder stayed behind the maker that gave up');
});

// ── a line before the stamp, a line after the look (second round) ───

test('a handover line put on the lock between its create and its stamp keeps its place: the stamp appends after it, the holder honors it, and a waiter finds the stamp behind it', () => {
  // the maker's release lands the line on this writer's lock the instant the name appears, before the stamp
  const w = world(false);   // a folder this writer did not make: only the line makes it this writer's to remove
  const real = fs.fstatSync;
  let armed = true;
  fs.fstatSync = function (target, ...rest) {
    const st = real.call(fs, target, ...rest);
    // the first fstat on the lock's inode is the holder's own, between the create and the stamp
    if (armed && typeof target === 'number' && fs.existsSync(w.lockPath) && Number(st.ino) === fs.statSync(w.lockPath).ino) {
      armed = false;
      fs.appendFileSync(w.lockPath, 'made-dir\n');
    }
    return st;
  };
  let seen = null;
  try { withStoreLock(w.storePath, () => { seen = fs.readFileSync(w.lockPath, 'utf8'); }); } finally { fs.fstatSync = real; }
  assert.equal(armed, false, 'the line landed before the stamp');
  assert.match(seen, /^made-dir\n\d+ \d+\n$/, 'the stamp took the line\'s place');
  assert.equal(fs.existsSync(w.lockPath), false);
  assert.equal(fs.existsSync(w.dir), false, 'the holder did not honor the line put before its stamp');
  // a waiter judges such a lock by the stamp behind the line: a dead pid's is broken at once, not held to the
  // bound by its fresh mtime, and the breaker inherits the line
  const w2 = world(false);
  fs.writeFileSync(w2.lockPath, `made-dir\n${deadPid()} ${Date.now()}\n`);
  let ran = false;
  let err = null;
  const t0 = Date.now();
  try { withStoreLock(w2.storePath, () => { ran = true; }, { waitMs: 1000 }); } catch (e) { err = e; }
  assert.equal(err, null, `the waiter did not find the stamp behind the line and held the dead lock to the bound: ${err && err.message}`);
  assert.equal(ran, true);
  assert.ok(Date.now() - t0 < 1000, `the waiter waited ${Date.now() - t0} ms behind a dead lock`);
  assert.equal(fs.existsSync(w2.dir), false, 'the breaker of the dead lock inherited the line on it');
});

test('a handover line landing between the holder\'s look and its unlink is read back through the holder\'s own descriptor and honored', () => {
  const w = world(false);   // a folder this writer did not make
  const real = fs.unlinkSync;
  let armed = true;
  fs.unlinkSync = function (target, ...rest) {
    // the release's look has passed; the maker's line lands as the unlink is called
    if (armed && target === w.lockPath) { armed = false; fs.appendFileSync(w.lockPath, 'made-dir\n'); }
    return real.call(fs, target, ...rest);
  };
  try { assert.equal(withStoreLock(w.storePath, () => 'ran'), 'ran'); } finally { fs.unlinkSync = real; }
  assert.equal(armed, false, 'the line landed at the unlink');
  assert.equal(fs.existsSync(w.lockPath), false, 'released');
  assert.equal(fs.existsSync(w.dir), false, 'the line landing after the look was not read back, and the folder stayed');
});

test('the breaker\'s claim honors the line the same way: put on it between its create and its stamp, or between the breaker\'s look at it and its unlink', () => {
  // between the claim's create and its stamp
  const w = world(false);
  const claim = `${w.lockPath}.break`;
  fs.writeFileSync(w.lockPath, `${deadPid()} ${Date.now()}\n`);
  const realFstat = fs.fstatSync;
  let armed = true;
  fs.fstatSync = function (target, ...rest) {
    const st = realFstat.call(fs, target, ...rest);
    // the first fstat on the claim's inode is the breaker's own, between the create and the stamp
    if (armed && typeof target === 'number' && fs.existsSync(claim) && Number(st.ino) === fs.statSync(claim).ino) {
      armed = false;
      fs.appendFileSync(claim, 'made-dir\n');
    }
    return st;
  };
  let ran = false;
  try { withStoreLock(w.storePath, () => { ran = true; }); } finally { fs.fstatSync = realFstat; }
  assert.equal(armed, false, 'the line landed before the claim\'s stamp');
  assert.equal(ran, true);
  assert.equal(fs.existsSync(claim), false);
  assert.equal(fs.existsSync(w.dir), false, 'the stamp took the line\'s place on the claim, and the folder stayed');
  // between the breaker's look at its claim and its unlink
  const w2 = world(false);
  const claim2 = `${w2.lockPath}.break`;
  fs.writeFileSync(w2.lockPath, `${deadPid()} ${Date.now()}\n`);
  const realUnlink = fs.unlinkSync;
  let armed2 = true;
  fs.unlinkSync = function (target, ...rest) {
    if (armed2 && target === claim2) { armed2 = false; fs.appendFileSync(claim2, 'made-dir\n'); }
    return realUnlink.call(fs, target, ...rest);
  };
  let ran2 = false;
  try { withStoreLock(w2.storePath, () => { ran2 = true; }); } finally { fs.unlinkSync = realUnlink; }
  assert.equal(armed2, false, 'the line landed at the claim\'s unlink');
  assert.equal(ran2, true);
  assert.equal(fs.existsSync(claim2), false);
  assert.equal(fs.existsSync(w2.dir), false, 'the line landing after the breaker\'s look was not read back, and the folder stayed');
});
