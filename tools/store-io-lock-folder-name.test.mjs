// withStoreLock (plans/file-review.md, decision 49; vendor patch 0008) makes `.trackchanges/` for the
// lock when a first write finds none, and tries the create again when another writer made it first
// (mkdir says EEXIST). An entry at the folder's name that is not a directory, a link to nothing above
// all, gives the create ENOENT through it and mkdir EEXIST at it on every turn: the loop spun the whole
// wait and threw as held, so track-edit, track-comment and track-reply printed the line for a live
// writer, with no writer anywhere, and told the agent to retry, every retry the same two seconds (the
// review of 2026-09-11; the host refuses such an entry before it locks, and the CLIs do not look). Now
// the entry is refused at once, held false, naming it. Cases:
//   * a link to nothing at `.trackchanges`: a StoreLockError with held false, at once, naming the link;
//     nothing created, the link left alone
//   * a regular file there: refused at once as before (ENOTDIR from the create), held false
//   * a link to a directory there: the lock works through it, and the folder behind the link stays
//   * the real track-comment on such a root prints that line and exits 1 in well under the wait
// Synthetic paths only, under a scratch directory.
// Run: node --test tools/store-io-lock-folder-name.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { storeLockPathFor, storePathFor, withStoreLock, StoreLockError, STORE_LOCK_WAIT_MS } from '../vendor/track-changents/store-io.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
// Real paths: a CLI runs only when process.argv[1]'s real path is its own module's.
const VENDOR = fs.realpathSync(path.resolve(HERE, '..', 'vendor', 'track-changents'));
const TRACK_COMMENT = path.join(VENDOR, 'cli', 'track-comment.mjs');

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-store-io-lock-folder-name-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
// A root with a landmark and one note, and NO `.trackchanges/` yet; the note's sidecar and lock paths.
function world() {
  const root = path.join(SCRATCH, `w${++worlds}`, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  const note = path.join(root, 'docs', 'report.md');
  fs.writeFileSync(note, '# Latency report\n\nStep one: warm the cache before the first request.\n');
  const storePath = storePathFor(root, note);
  const dir = path.dirname(storePath);
  assert.equal(dir, path.join(root, '.trackchanges'));
  return { root, note, dir, storePath, lockPath: storeLockPathFor(storePath) };
}

test('a link to nothing at .trackchanges refuses at once, held false, naming the link; nothing is created and the link is left alone', () => {
  const w = world();
  fs.symlinkSync(path.join(w.root, 'nowhere'), w.dir);
  const t0 = Date.now();
  let ran = false;
  let err = null;
  try { withStoreLock(w.storePath, () => { ran = true; }); } catch (e) { err = e; }
  const took = Date.now() - t0;
  assert.equal(ran, false);
  assert.ok(err instanceof StoreLockError, `a StoreLockError, not a raw OS error: ${err && err.stack}`);
  assert.equal(err.held, false, 'not busy: no writer holds anything');
  assert.equal(err.lockPath, w.lockPath);
  assert.equal(err.message, `cannot create ${w.lockPath}: ${w.dir} is a symbolic link to nothing, not a directory`);
  assert.ok(took < 1000, `refused at once, not after the wait (${took} ms; the wait is ${STORE_LOCK_WAIT_MS} ms)`);
  assert.equal(fs.lstatSync(w.dir).isSymbolicLink(), true, 'the link is left alone');
  assert.equal(fs.readlinkSync(w.dir), path.join(w.root, 'nowhere'));
  assert.equal(fs.existsSync(path.join(w.root, 'nowhere')), false, 'nothing was created behind it');
});

test('a regular file at .trackchanges refuses at once too, held false, with the OS error; a link to a directory is followed, the lock works through it and the folder behind it stays', () => {
  const w = world();
  fs.writeFileSync(w.dir, 'not a folder\n');
  const t0 = Date.now();
  let err = null;
  try { withStoreLock(w.storePath, () => 'ran'); } catch (e) { err = e; }
  assert.ok(err instanceof StoreLockError, String(err && err.stack));
  assert.equal(err.held, false);
  assert.equal(err.cause && err.cause.code, 'ENOTDIR');
  assert.ok(Date.now() - t0 < 1000);
  assert.equal(fs.readFileSync(w.dir, 'utf8'), 'not a folder\n', 'the file is left alone');
  const w2 = world();
  const behind = path.join(w2.root, 'elsewhere');
  fs.mkdirSync(behind);
  fs.symlinkSync(behind, w2.dir);
  assert.equal(withStoreLock(w2.storePath, () => 'ran'), 'ran');
  assert.equal(fs.lstatSync(w2.dir).isSymbolicLink(), true);
  assert.deepEqual(fs.readdirSync(behind), [], 'no lock left behind the link, and the folder this writer did not make stays');
});

test('the real track-comment on a root whose .trackchanges is a link to nothing prints that line, exits 1 at once and writes nothing', () => {
  const w = world();
  fs.symlinkSync(path.join(w.root, 'nowhere'), w.dir);
  const env = { ...process.env };
  for (const k of ['TRACKCHANGES_ROOT', 'TRACKCHANGES_SESSION', 'ROMP_SID', 'ROMP_SESSION_NAME']) delete env[k];
  const before = fs.readFileSync(w.note, 'utf8');
  const t0 = Date.now();
  const r = spawnSync(process.execPath, [TRACK_COMMENT, '--file', w.note, '--anchor', 'Step one', '--note', 'Which cache?'], { env, encoding: 'utf8' });
  const took = Date.now() - t0;
  assert.equal(r.status, 1, `exit ${r.status}: ${r.stdout} ${r.stderr}`);
  assert.equal(r.stdout, '');
  assert.equal(r.stderr, `cannot create ${w.lockPath}: ${w.dir} is a symbolic link to nothing, not a directory\n`);
  assert.ok(took < STORE_LOCK_WAIT_MS, `the CLI took ${took} ms: it waited the lock's bound out for an entry no wait changes`);
  assert.equal(fs.lstatSync(w.dir).isSymbolicLink(), true, 'the link is left alone');
  assert.equal(fs.existsSync(path.join(w.root, 'nowhere')), false);
  assert.equal(fs.readFileSync(w.note, 'utf8'), before, 'the note is untouched');
});
