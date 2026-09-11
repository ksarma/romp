// withStoreLock (plans/file-review.md, decision 49; vendor patch 0008) breaks a lock whose stamp is
// older than STORE_LOCK_STALE_MS. Judged by age behind alone, a stamp AHEAD of the clock was never
// stale: with a pid alive to the reader (1 is, to every reader in the initial pid namespace, since
// kill(1, 0) answers EPERM, which reads as alive), a `.lock` that reached `.trackchanges/` in a
// checkout from a machine whose clock ran ahead (decision 48 asks sessions to commit the folder), or
// was planted there, held every CLI and host write to that file's comments to `busy` for as long as
// its stamp stayed in the future, and no message named it (the review of 2026-09-11). Now a stamp more
// than the bound from this clock in either direction is a dead writer's, and so is a stampless lock
// whose mtime is. Cases:
//   * a lock stamped `1 <an hour ahead>` is broken at once: the writer runs, no lock and no claim remain
//   * a live pid's lock stamped an hour ahead: the same
//   * a live pid's lock stamped five seconds ahead is a live writer's on a clock a little ahead: the
//     writer waits the bound out and refuses as held, the lock intact
//   * a stampless lock (the stamp not written yet) with its mtime an hour ahead is broken; five
//     seconds ahead, it is waited behind
//   * a dead breaker's claim stamped an hour ahead beside a dead lock is removed and the break proceeds
//   * the real track-comment against `1 <an hour ahead>` lands its comment and exits 0 in well under
//     the wait, the lock gone
// Synthetic paths only, under a scratch directory.
// Run: node --test tools/store-io-lock-clock.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { storeLockPathFor, storePathFor, withStoreLock, StoreLockError, STORE_LOCK_WAIT_MS } from '../vendor/track-changents/store-io.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const VENDOR = fs.realpathSync(path.resolve(HERE, '..', 'vendor', 'track-changents'));
const TRACK_COMMENT = path.join(VENDOR, 'cli', 'track-comment.mjs');
const HOUR = 3600 * 1000;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-store-io-lock-clock-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
// A root with a landmark, one note and its `.trackchanges/`; the note's sidecar, lock and claim paths.
function world() {
  const root = path.join(SCRATCH, `w${++worlds}`, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  const note = path.join(root, 'docs', 'report.md');
  fs.writeFileSync(note, '# Latency report\n\nStep one: warm the cache before the first request.\n');
  const storePath = storePathFor(root, note);
  fs.mkdirSync(path.dirname(storePath));
  const lockPath = storeLockPathFor(storePath);
  return { root, note, dir: path.dirname(storePath), storePath, lockPath, claim: `${lockPath}.break` };
}

function deadPid() {
  const gone = spawnSync(process.execPath, ['-e', ''], { encoding: 'utf8' });
  assert.equal(gone.status, 0);
  return gone.pid;
}

// One take of the lock with a short wait: whether fn ran, the error if any, and the time it took.
function take(w, waitMs) {
  const out = { ran: false, err: null, took: 0 };
  const t0 = Date.now();
  try {
    withStoreLock(w.storePath, () => { out.ran = true; }, { waitMs });
  } catch (e) {
    out.err = e;
  }
  out.took = Date.now() - t0;
  return out;
}

function brokenAtOnce(w, out, what) {
  assert.equal(out.err, null, `${what}: ${out.err && out.err.message}`);
  assert.equal(out.ran, true, `${what}: the writer ran`);
  assert.ok(out.took < 1000, `${what}: no wait (took ${out.took} ms)`);
  assert.deepEqual(fs.readdirSync(w.dir), [], `${what}: no lock and no claim remain`);
}

function waitedOut(w, out, content, what) {
  assert.equal(out.ran, false, `${what}: the lock was broken and the writer ran`);
  assert.ok(out.err instanceof StoreLockError && out.err.held === true, `${what}: refused as held: ${out.err && out.err.message}`);
  assert.ok(out.took >= 150, `${what}: waited the bound out (${out.took} ms)`);
  assert.equal(fs.readFileSync(w.lockPath, 'utf8'), content, `${what}: the lock is intact`);
  assert.deepEqual(fs.readdirSync(w.dir), [path.basename(w.lockPath)], `${what}: no claim was left`);
}

test('a lock stamped "1 <an hour ahead>" is broken at once, pid 1 alive to every reader or not', () => {
  const w = world();
  fs.writeFileSync(w.lockPath, `1 ${Date.now() + HOUR}\n`);
  brokenAtOnce(w, take(w, 1000), 'pid 1, an hour ahead');
});

test('a live pid\'s lock stamped an hour ahead is broken at once; stamped five seconds ahead it is a live writer\'s and waited out', () => {
  const w = world();
  fs.writeFileSync(w.lockPath, `${process.pid} ${Date.now() + HOUR}\n`);
  brokenAtOnce(w, take(w, 1000), 'a live pid, an hour ahead');
  const near = `${process.pid} ${Date.now() + 5000}\n`;
  fs.writeFileSync(w.lockPath, near);
  waitedOut(w, take(w, 150), near, 'a live pid, five seconds ahead');
});

test('a stampless lock whose mtime is an hour ahead is broken at once; five seconds ahead it is waited out', () => {
  const w = world();
  fs.writeFileSync(w.lockPath, '');
  const far = new Date(Date.now() + HOUR);
  fs.utimesSync(w.lockPath, far, far);
  brokenAtOnce(w, take(w, 1000), 'stampless, mtime an hour ahead');
  fs.writeFileSync(w.lockPath, '');
  const near = new Date(Date.now() + 5000);
  fs.utimesSync(w.lockPath, near, near);
  waitedOut(w, take(w, 150), '', 'stampless, mtime five seconds ahead');
});

test('a dead breaker\'s claim stamped an hour ahead beside a dead lock is removed and the break proceeds', () => {
  const w = world();
  fs.writeFileSync(w.lockPath, `${deadPid()} ${Date.now()}\n`);
  fs.writeFileSync(w.claim, `1 ${Date.now() + HOUR}\n`);
  brokenAtOnce(w, take(w, 1000), 'a dead lock under a claim an hour ahead');
});

test('the real track-comment against a lock stamped "1 <an hour ahead>" lands its comment and exits 0 in well under the wait, the lock gone', () => {
  const w = world();
  fs.writeFileSync(w.lockPath, `1 ${Date.now() + HOUR}\n`);
  const env = { ...process.env };
  for (const k of ['TRACKCHANGES_ROOT', 'TRACKCHANGES_SESSION', 'ROMP_SID', 'ROMP_SESSION_NAME']) delete env[k];
  const t0 = Date.now();
  const r = spawnSync(process.execPath, [TRACK_COMMENT, '--file', w.note, '--anchor', 'Step one', '--note', 'Which cache?'], { env, encoding: 'utf8' });
  const took = Date.now() - t0;
  assert.equal(r.status, 0, `exit ${r.status}: ${r.stdout} ${r.stderr}`);
  assert.ok(took < STORE_LOCK_WAIT_MS, `no wait behind the planted lock (took ${took} ms)`);
  const disk = JSON.parse(fs.readFileSync(w.storePath, 'utf8'));
  assert.equal(disk.comments.length, 1);
  assert.equal(disk.comments[0].body, 'Which cache?');
  assert.deepEqual(fs.readdirSync(w.dir), [path.basename(w.storePath)], 'the sidecar alone: the lock is gone, no claim remains');
});
