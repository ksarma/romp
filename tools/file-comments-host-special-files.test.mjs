// Special-file pins for tools/file-comments-host.mjs: every verb that opens the file refuses a
// FIFO or a device as `unreadable` at once, whichever route brings it to the file. Before this,
// the text-reading route (a `status` with `baseline: true`, any `status` or `set-tracked` once a
// sidecar exists, and comment/reply/resolve always) opened the path with a plain open(), which on
// a FIFO with no writer blocks until one arrives: the host sat until the kernel's 10 s deadline
// killed it and the person saw a host-error about a hang, where the stat-only route on the same
// path had refused `unreadable` in milliseconds. Same hermetic harness as
// file-comments-host.test.mjs: the synthetic `notes-api` world under a scratch directory, the
// script driven as the kernel drives it — here with a kill guard on the spawn, so a regression
// fails the test instead of hanging the suite.
// Run: node --test tools/file-comments-host-special-files.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { storePathFor } from '../vendor/track-changents/store-io.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');

// Long enough that a slow CI runner answers within it, short enough that a regression (the host
// blocked in open() until killed) fails the test in seconds rather than hanging the suite.
const GUARD_MS = 8000;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-special-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  const looseDir = path.join(home, 'loose');
  fs.mkdirSync(looseDir);
  return {
    home, root, looseDir,
    report: path.join(root, 'docs', 'report.md'),
    cfg: path.join(root, '.trackchanges', 'config.json'),
  };
}

function env(w) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home };
  delete e.TRACKCHANGES_ROOT;
  delete e.ROMP_SID;
  delete e.ROMP_SESSION_NAME;
  return e;
}
// The spawn carries a kill guard: a host that blocks in open() comes back with `signal` set and
// no status, which `refused` names as the failure (the pre-fix behavior) rather than a timeout.
function host(w, req) {
  const r = spawnSync(process.execPath, [HOST], {
    input: JSON.stringify(req), encoding: 'utf8', env: env(w), timeout: GUARD_MS, killSignal: 'SIGKILL',
  });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  return { code: r.status, signal: r.signal, stdout: r.stdout, stderr: r.stderr, json };
}
function ok(w, req) {
  const r = host(w, req);
  assert.equal(r.signal, null, `${req.verb} did not answer within ${GUARD_MS} ms (killed with ${r.signal}): the host blocked on the file`);
  assert.equal(r.code, 0, `exit ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === true, `expected ok:true, got ${r.stdout}`);
  return r.json;
}
function refused(w, req, code) {
  const r = host(w, req);
  assert.equal(r.signal, null, `${req.verb} did not answer within ${GUARD_MS} ms (killed with ${r.signal}): the host blocked on the file`);
  assert.equal(r.code, 0, `a refusal exits 0; got ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === false, `expected ok:false, got ${r.stdout}`);
  assert.equal(r.json.code, code, r.json.error);
  assert.equal(typeof r.json.error, 'string');
  return r.json;
}
// A refusal for a file that is not a regular one: the code, the wording, the path as the person
// sees it, and no home path anywhere in it.
function notRegular(w, req, shown) {
  const r = refused(w, req, 'unreadable');
  assert.deepEqual(Object.keys(r).sort(), ['code', 'error', 'ok']);
  assert.match(r.error, /not a regular file/);
  assert.ok(r.error.includes(shown), r.error);
  assert.equal(r.error.includes(w.home), false, r.error);
  return r;
}
function status(w, file, args) { return ok(w, { verb: 'status', path: file, args: args || {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function fileBytes(p) { try { return fs.readFileSync(p); } catch { return null; } }

// Node has no mkfifo; the coreutils/BSD binary is on every platform the host runs on. A world
// without it (or a Windows runner) skips the FIFO tests rather than failing them.
function mkfifo(p) {
  if (process.platform === 'win32') return false;
  const r = spawnSync('mkfifo', [p], { encoding: 'utf8' });
  if (r.status !== 0) return false;
  return fs.statSync(p).isFIFO();
}
function fifoOrSkip(t, p) {
  if (mkfifo(p)) return true;
  t.skip('mkfifo is not available here');
  return false;
}

// ── the FIFO ────────────────────────────────────────────────────────

test('status with baseline on a FIFO refuses unreadable at once, under a landmark and loose alike', (t) => {
  const w = world();
  const fifo = path.join(w.root, 'docs', 'pipe.md');
  if (!fifoOrSkip(t, fifo)) return;
  // The stat-only route already refused; the text-reading route now answers the same, and as fast.
  notRegular(w, { verb: 'status', path: fifo, args: {} }, '~/notes-api/docs/pipe.md');
  notRegular(w, { verb: 'status', path: fifo, args: { baseline: true } }, '~/notes-api/docs/pipe.md');
  assert.ok(fs.statSync(fifo).isFIFO(), 'the FIFO is still there, untouched');
  // A loose FIFO (no landmark above it) takes the same route with no root, and leaves no landmark.
  const loose = path.join(w.looseDir, 'pipe.md');
  assert.ok(mkfifo(loose));
  notRegular(w, { verb: 'status', path: loose, args: { baseline: true } }, '~/loose/pipe.md');
  assert.equal(fs.existsSync(path.join(w.looseDir, '.trackchanges')), false, 'a refused status creates nothing');
});

test('once a sidecar exists, plain status and set-tracked on a path that has become a FIFO refuse unreadable instead of blocking', (t) => {
  const w = world();
  const probe = path.join(w.root, 'docs', 'probe.fifo');
  if (!fifoOrSkip(t, probe)) return;
  fs.unlinkSync(probe);
  const st = status(w, w.report);
  const c = ok(w, { verb: 'comment', path: w.report, args: { note: 'whole file' }, fence: fenceFor(st) });
  assert.equal(c.store.comments.length, 1);
  const storePath = storePathFor(w.root, w.report);
  const storeBytes = fileBytes(storePath);
  assert.ok(storeBytes, 'the comment wrote a sidecar');
  // The file is replaced by a FIFO under the same name: every viewer open now takes the text
  // route (a sidecar to rebase against), which used to block in open().
  fs.unlinkSync(w.report);
  assert.ok(mkfifo(w.report));
  notRegular(w, { verb: 'status', path: w.report, args: {} }, '~/notes-api/docs/report.md');
  notRegular(w, { verb: 'status', path: w.report, args: { baseline: true } }, '~/notes-api/docs/report.md');
  const cfgBefore = fileBytes(w.cfg);
  notRegular(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: { configMtimeNs: '' } }, '~/notes-api/docs/report.md');
  assert.deepEqual(fileBytes(w.cfg), cfgBefore, 'a refused toggle writes no config');
  assert.deepEqual(fileBytes(storePath), storeBytes, 'the sidecar is untouched');
  assert.ok(fs.statSync(w.report).isFIFO());
});

test('comment, reply and resolve on a FIFO refuse unreadable before the sidecar is consulted, and a loose FIFO gets no landmark', (t) => {
  const w = world();
  const fifo = path.join(w.root, 'docs', 'pipe.md');
  if (!fifoOrSkip(t, fifo)) return;
  const verbs = [
    { verb: 'comment', path: fifo, args: { note: 'on a pipe' }, fence: { storeMtimeNs: '' } },
    { verb: 'reply', path: fifo, args: { commentId: '1', note: 'still a pipe' }, fence: { storeMtimeNs: '' } },
    { verb: 'resolve', path: fifo, args: { commentId: '1', on: true }, fence: { storeMtimeNs: '' } },
  ];
  for (const req of verbs) notRegular(w, req, '~/notes-api/docs/pipe.md');
  assert.equal(fs.existsSync(storePathFor(w.root, fifo)), false, 'no sidecar was seeded for a refused comment');
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false, 'nothing was written under the root');
  // Loose: the refusal comes before the landmark, so the directory stays as it was (decision 37).
  const loose = path.join(w.looseDir, 'pipe.md');
  assert.ok(mkfifo(loose));
  notRegular(w, { verb: 'comment', path: loose, args: { note: 'on a pipe' }, fence: { storeMtimeNs: '' } }, '~/loose/pipe.md');
  assert.deepEqual(fs.readdirSync(w.looseDir), ['pipe.md'], 'no landmark beside a loose FIFO');
});

// ── the device ──────────────────────────────────────────────────────

test('a character device refuses unreadable on both routes', (t) => {
  const w = world();
  const dev = '/dev/null';
  let st;
  try { st = fs.statSync(dev); } catch { st = null; }
  if (!st || !st.isCharacterDevice()) { t.skip(`${dev} is not a character device here`); return; }
  notRegular(w, { verb: 'status', path: dev, args: {} }, dev);
  notRegular(w, { verb: 'status', path: dev, args: { baseline: true } }, dev);
  notRegular(w, { verb: 'comment', path: dev, args: { note: 'on a device' }, fence: { storeMtimeNs: '' } }, dev);
});

// ── the regular file, unchanged ─────────────────────────────────────

test('a regular file still reads on the text route: baseline is the text and fileMtimeNs is its stat', () => {
  const w = world();
  const plain = path.join(w.root, 'docs', 'plain.md');
  fs.writeFileSync(plain, 'Plain text.\n');
  const r = status(w, plain, { baseline: true });
  assert.equal(r.baseline, 'Plain text.\n');
  assert.equal(r.fileMtimeNs, fs.statSync(plain, { bigint: true }).mtimeNs.toString());
  const bare = status(w, plain);
  assert.equal('baseline' in bare, false);
  assert.equal(bare.fileMtimeNs, r.fileMtimeNs, 'both routes stamp the same mtime');
});
