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
//     allocator hands back the dead lock's number in most rounds, not all); with the descriptor closed
//     it fails when it does. The order is set by what the children report, never by the clock: each
//     reports once it has loaded store-io and waits to be let go; the breaker goes first and reports its
//     stall at the look; only then does the waiter go; the breaker looks on the waiter's report that it
//     is in, and the waiter leaves on the breaker's report of its next step. Started at fixed times by
//     the clock (until 2026-10-07), a child that loaded store-io late on a loaded machine let the waiter
//     break the dead lock and go in before the breaker stalled, and the case failed its own setup.
// A filesystem that never reuses an inode number (tmpfs) cannot tell the descriptor open from closed, so
// neither case fails there with it closed; both do where the scratch directory reuses numbers (ext4).
// Synthetic paths only, under a scratch directory.
// Run: node --test tools/store-io-lock-inode-reuse.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { storeLockPathFor, withStoreLock, StoreLockError, STORE_LOCK_STALE_MS } from '../vendor/track-changents/store-io.mjs';

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

// One real writer, driven by the parent through its reports. It loads store-io, reports `ready` and waits
// to be let go (a byte on its stdin; the end of stdin, its parent gone, ends it). Then it takes the lock
// and inside fn puts a marker down, counts the markers it sees (a second one is another writer inside with
// it), reports `in`, waits to be let go again when it is the waiter, counts again and leaves; at the end
// it reports `done` with what it saw. The breaker (`breaker` 1) is let go a second time at its look for
// the unlink (the third read-only open of the lock in this process): it reports `stalled` there and
// waits, and once let go it looks, reports `looked` with what it found at the name, and reports `waiting`
// at its next look (a writer waiting at a held lock looks again). Each report is one JSON line on stdout,
// written before the step that follows it.
const WRITER = `
import fs from 'node:fs';
import path from 'node:path';
const [storeIo, store, markers, tag, waitMs, staleMs, breaker] = process.argv.slice(1);   // -e: no script path in argv
const lock = store + '.lock';
const claim = lock + '.break';
const report = (ev, more) => fs.writeSync(1, JSON.stringify({ ev, tag, pid: process.pid, t: Date.now(), ...more }) + '\\n');
const gate = (name) => {
  const b = Buffer.alloc(1);
  for (;;) {
    let n;
    try { n = fs.readSync(0, b, 0, 1, null); } catch (e) {
      if (e && e.code === 'EAGAIN') { Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1); continue; }
      throw e;
    }
    if (n === 1) return;
    report('abandoned', { gate: name });
    process.exit(3);
  }
};
// What is at a name now; read by path, not by the look's flags, so the breaker's count of its looks holds.
const read = (p) => { try { return fs.readFileSync(p, 'utf8'); } catch { return null; } };
const ino = (p) => { try { return String(fs.lstatSync(p, { bigint: true }).ino); } catch { return null; } };
const { withStoreLock, StoreLockError } = await import(storeIo);
if (breaker === '1') {
  const LOOK = fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK;
  const real = fs.openSync;
  let looks = 0;
  fs.openSync = function (p, flags, ...rest) {
    if (p !== lock || flags !== LOOK) return real.call(fs, p, flags, ...rest);
    ++looks;
    if (looks === 3) {
      report('stalled', { claim: read(claim), lock: read(lock), ino: ino(lock) });
      gate('resume');
      let fd;
      try { fd = real.call(fs, p, flags, ...rest); } catch (e) { report('looked', { ino: null, lock: null, err: String(e && e.code) }); throw e; }
      report('looked', { ino: String(fs.fstatSync(fd, { bigint: true }).ino), lock: read(lock) });
      return fd;
    }
    if (looks === 4) report('waiting', { lock: read(lock) });
    return real.call(fs, p, flags, ...rest);
  };
}
report('ready');
gate('go');
const out = { held: false, overlap: 0, in: null, out: null, err: null };
try {
  withStoreLock(store, () => {
    out.held = true; out.in = Date.now();
    const seen = () => fs.readdirSync(markers).filter((n) => n.startsWith('h-')).length;
    const mine = path.join(markers, 'h-' + tag);
    fs.writeFileSync(mine, '', { flag: 'wx' });
    out.overlap = Math.max(out.overlap, seen());
    report('in', { ino: ino(lock), lock: read(lock), claim: read(claim) });
    if (breaker !== '1') gate('leave');
    out.overlap = Math.max(out.overlap, seen());
    fs.unlinkSync(mine);
    out.out = Date.now();
  }, { waitMs: Number(waitMs), staleMs: Number(staleMs) });
} catch (e) {
  out.err = e instanceof StoreLockError ? 'StoreLockError held=' + e.held : String(e && e.stack || e);
}
report('done', out);
`;
// next(...names) resolves with the child's first report of any of those names, and fails, with its reports
// and stderr, when the child exits without one; open() lets the child go past the gate it waits at.
function writer(w, markers, { tag, waitMs, staleMs, breaker = false }) {
  const child = spawn(process.execPath, ['--input-type=module', '-e', WRITER, '--', STORE_IO, w.storePath, markers, tag, String(waitMs), String(staleMs), breaker ? '1' : '0']);
  const reports = [];
  const pending = [];
  let stdout = '';
  let stderr = '';
  let exit = null;
  const settle = () => {
    for (let i = pending.length - 1; i >= 0; i--) {
      const { names, resolve, reject } = pending[i];
      const hit = reports.find((r) => names.includes(r.ev));
      if (hit) { pending.splice(i, 1); resolve(hit); continue; }
      if (exit) { pending.splice(i, 1); reject(new Error(`${tag} exited (${exit}) without reporting ${names.join(' or ')}; its reports: ${JSON.stringify(reports)}; stderr: ${stderr}`)); }
    }
  };
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', (c) => {
    stdout += c;
    let nl;
    while ((nl = stdout.indexOf('\n')) >= 0) {
      const line = stdout.slice(0, nl);
      stdout = stdout.slice(nl + 1);
      try { reports.push(JSON.parse(line)); } catch { reports.push({ ev: 'unparsed', line }); }
    }
    settle();
  });
  child.stderr.setEncoding('utf8'); child.stderr.on('data', (c) => { stderr += c; });
  child.stdin.on('error', () => { /* the child is gone: the wait for its report fails with its exit */ });
  child.on('close', (code, signal) => { exit = signal || `code ${code}`; settle(); });
  return {
    next: (...names) => new Promise((resolve, reject) => { pending.push({ names, resolve, reject }); settle(); }),
    open: () => { child.stdin.write('g'); },
    kill: () => { if (!exit) child.kill('SIGKILL'); },
  };
}

// The waiter breaks the stalled breaker's claim once the claim is older than its bound, so the stall runs
// past the bound by the lock's own rule, however long the machine takes. The breaker judges by the
// callers' bound (STORE_LOCK_STALE_MS, 15 s), so the waiter's live lock stays fresh to it while the steps
// between the reports take less than that; judged by the waiter's bound, a slow step would let the breaker
// break that lock by its age and enter beside it, the very failure this case looks for. Both wait far
// longer than the case takes: a writer that gives up fails the case.
const WAITER_STALE_MS = 1000;
const WAIT_MS = 30000;

test('real processes: a breaker stalled past the stale bound at its look for the unlink, whose claim and dead lock a waiter broke meanwhile, waits for that waiter\'s write instead of removing its lock and entering beside it', { timeout: 120000 }, async (t) => {
  const w = world();
  const markers = path.join(path.dirname(w.root), 'markers');
  fs.mkdirSync(markers);
  const deadStamp = `${deadPid()} ${Date.now()}\n`;
  fs.writeFileSync(w.lockPath, deadStamp);
  const dead = fs.statSync(w.lockPath, { bigint: true });
  const X = writer(w, markers, { tag: 'X', waitMs: WAIT_MS, staleMs: STORE_LOCK_STALE_MS, breaker: true });
  const Y = writer(w, markers, { tag: 'Y', waitMs: WAIT_MS, staleMs: WAITER_STALE_MS });
  // A child waiting at its gate keeps this process alive, so the case's timeout ends them too.
  t.signal.addEventListener('abort', () => { X.kill(); Y.kill(); }, { once: true });
  try {
    // Each step waits for the report that makes it the next one, and its setup is checked on that report,
    // so a setup not reached fails there.
    await Promise.all([X.next('ready'), Y.next('ready')]);
    X.open();   // the breaker alone: the dead lock judged, its claim taken
    const stalled = await X.next('stalled');
    assert.equal(stalled.lock, deadStamp, 'the breaker stalled at its look for the unlink with the dead lock still at the name');
    assert.equal(stalled.ino, String(dead.ino), 'the dead lock\'s own inode');
    const claimed = new RegExp(`^${stalled.pid} (\\d+)$`, 'm').exec(stalled.claim || '');
    assert.ok(claimed, `the breaker stalled holding its own claim (the claim: ${JSON.stringify(stalled.claim)})`);
    Y.open();   // the waiter: waits the claim out, breaks it and the dead lock, goes in
    const yIn = await Y.next('in');
    assert.equal(yIn.claim, null, 'the waiter broke the stalled breaker\'s claim before it went in');
    assert.ok(yIn.lock && yIn.lock.startsWith(`${yIn.pid} `), `the waiter holds a lock of its own (${JSON.stringify(yIn.lock)})`);
    X.open();   // the breaker looks for the unlink
    const looked = await X.next('looked');
    assert.ok(looked.t - Number(claimed[1]) > WAITER_STALE_MS, `the stall ran past the bound (${looked.t - Number(claimed[1])} ms from the claim's stamp)`);
    assert.equal(looked.lock, yIn.lock, 'the breaker\'s look for the unlink found the waiter\'s fresh lock at the name');
    assert.equal(looked.ino, yIn.ino, 'the waiter\'s lock itself');
    // The lock's guarantee.
    assert.notEqual(looked.ino, String(dead.ino), 'the judged inode was still open in the breaker, so the fresh lock could not take its number');
    const nextStep = await X.next('waiting', 'in');   // waits at that lock, or removed it and went in
    assert.equal(nextStep.ev, 'waiting', 'the breaker went in while the waiter held its lock: it removed that lock');
    assert.equal(nextStep.lock, yIn.lock, 'the breaker waits at the waiter\'s lock');
    Y.open();   // the waiter leaves
    const [x, y] = await Promise.all([X.next('done'), Y.next('done')]);
    for (const j of [x, y]) assert.equal(j.err, null, `${j.tag}: ${j.err}`);
    // One clock in whole milliseconds: the waiter's entry and the breaker's look on its report can share one.
    assert.ok(y.in >= stalled.t && y.in <= looked.t, `the waiter broke in during the stall (Y in at ${y.in - stalled.t} ms of it, the stall ${looked.t - stalled.t} ms)`);
    assert.equal(y.held, true, 'the waiter wrote');
    assert.equal(x.held, true, 'the breaker wrote, after the waiter');
    assert.ok(x.in >= y.out, `the breaker entered ${y.out - x.in} ms before the waiter left: it removed the waiter's live lock`);
    assert.equal(y.overlap, 1, 'the waiter had the lock alone');
    assert.equal(x.overlap, 1);
    assert.deepEqual(fs.readdirSync(w.dir), [], `left behind: ${fs.readdirSync(w.dir)}`);
  } finally {
    X.kill(); Y.kill();
  }
});
