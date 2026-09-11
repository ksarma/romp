// store-io's lock, `<sidecar>.lock` (withStoreLock; plans/file-review.md, decision 49; vendor patch
// 0008), on the paths the review of 2026-09-11 found open. Each case here failed against the lock as
// first built and holds now:
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
