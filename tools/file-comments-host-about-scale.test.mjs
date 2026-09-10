// Cost pins for tools/file-comments-host.mjs readChangeIds and buildComment's missing-id check (the about
// follow-on, plans/file-review.md "The about follow-on (2026-09-10)" under Slice 2; its review, 2026-09-10).
// The kernel forwards a `comment` request's args unread, admits one up to _FILE_COMMENTS_REPLY_MAX serialized
// and kills the host at _FILE_COMMENTS_TIMEOUT, reporting host-error. The review found readChangeIds deduping
// with an includes() scan per id, quadratic in the list: a request naming a hundred thousand ids, about a
// megabyte and far under the cap, ran past the deadline, so a bad list came back as "the comments helper did
// not answer" where `accept {ids}` with the same list refuses `no-change` in milliseconds. This module pins:
//   * the rule the walk keeps: repeats once, in the order first named, as strings; every named id looked up
//     against the sidecar's pending and detached changes, the missing ones alone in the refusal, in order;
//   * cost, in CPU time (immune to the machine's load): a list far past the review's size is read and checked
//     inside a fifth of the kernel's deadline, whether the ids are all missing or all held;
//   * the scenario, through the script as the kernel drives it: a request the kernel admits, a hundred
//     thousand change-shaped ids beside one real pending change, refuses `no-change` inside the deadline and
//     writes nothing, and `accept` with the same list refuses the same way.
// Hermetic: the synthetic notes-api world under a scratch directory (tests/fixtures/file_comments/), as the
// sibling modules build it. Run: node --test tools/file-comments-host-about-scale.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { buildComment } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');

const SID = '11111111-2222-3333-4444-555555555555';

// The kernel's bounds for one verb, read from its source so the numbers below are the real ones.
function kernelSource() { return fs.readFileSync(path.join(REPO, 'kernel', 'kernel.py'), 'utf8'); }
function kernelDeadlineMs() {
  const m = /^_FILE_COMMENTS_TIMEOUT = (\d+)/m.exec(kernelSource());
  assert.ok(m, 'kernel.py defines _FILE_COMMENTS_TIMEOUT');
  return Number(m[1]) * 1000;
}
function kernelRequestMax() {
  const m = /^_FILE_COMMENTS_REPLY_MAX = ([\d* ]+?)\s*(?:#|$)/m.exec(kernelSource());
  assert.ok(m, 'kernel.py defines _FILE_COMMENTS_REPLY_MAX');
  return m[1].split('*').map((s) => Number(s.trim())).reduce((a, b) => a * b, 1);
}

// Change ids as the engine mints them: a millisecond timestamp, a dash, a number, so the strings share a long prefix.
const changeId = (i) => `1700000000000-${i}`;
const cpuMs = (t0) => { const u = process.cpuUsage(t0); return (u.user + u.system) / 1000; };

// ── in process ──────────────────────────────────────────────────────

const N = 200_000;
const TEXT = fs.readFileSync(path.join(FIX, 'report.md'), 'utf8');

test('a list far past the review\'s size, every id missing: the refusal names each once, in the order first named, inside a fifth of the deadline in CPU time', () => {
  const named = [];
  for (let i = 0; i < N; i++) named.push(changeId(i));
  for (let i = 0; i < N; i++) named.push(changeId(i));   // every id named twice, the whole list over again
  const t0 = process.cpuUsage();
  const r = buildComment(TEXT, { changeIds: named, note: 'On these.' }, 1700000001000, [], []);
  const ms = cpuMs(t0);
  assert.equal(r.error, 'no-change');
  assert.equal(r.ids.length, N, 'once each');
  assert.equal(r.ids[0], changeId(0));
  assert.equal(r.ids[N - 1], changeId(N - 1));
  assert.equal(r.ids.join('\n') === named.slice(0, N).join('\n'), true, 'in the order first named');
  const bound = kernelDeadlineMs() / 5;
  assert.ok(ms < bound, `${ms.toFixed(0)} ms of CPU for ${named.length} ids, bound ${bound} ms`);
});

test('a list far past the review\'s size, every id held: the comment names each once, in order, its id from the first, inside a fifth of the deadline in CPU time', () => {
  const detached = [];
  for (let i = 0; i < N; i++) detached.push({ id: changeId(i), from: 40 + i });
  const named = [];
  for (let i = 0; i < N; i++) named.push(changeId(i), changeId(i));   // each twice, adjacent
  named.push(changeId(0));                                              // and the first once more at the end
  const t0 = process.cpuUsage();
  const r = buildComment(TEXT, { changeIds: named, note: 'On all of these.' }, 1700000001000, [], detached);
  const ms = cpuMs(t0);
  assert.equal(r.error, undefined);
  assert.equal(r.comment.changeIds.length, N, 'once each');
  assert.equal(r.comment.changeIds.join('\n') === detached.map((d) => d.id).join('\n'), true, 'in the order first named');
  assert.equal(r.comment.id, '1700000001000-40', 'the first named change\'s current offset');
  assert.equal(r.comment.body, 'On all of these.');
  const bound = kernelDeadlineMs() / 5;
  assert.ok(ms < bound, `${ms.toFixed(0)} ms of CPU for ${named.length} ids over ${N} changes, bound ${bound} ms`);
});

test('numbers are kept as strings and a repeat under either spelling is one id', () => {
  const r = buildComment(TEXT, { changeIds: [7, '7', 8, '9', 8], note: 'n' }, 1, [], [{ id: 7, from: 3 }, { id: 8, from: 5 }, { id: '9', from: 6 }]);
  assert.deepEqual(r.comment.changeIds, ['7', '8', '9']);
  assert.equal(r.comment.id, '1-3');
});

// ── the scenario, through the script ────────────────────────────────

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-about-scale-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  fs.copyFileSync(path.join(FIX, 'index.md'), path.join(root, 'index.md'));
  return { home, root, report: path.join(root, 'docs', 'report.md') };
}
function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home, ...(extra || {}) };
  delete e.TRACKCHANGES_ROOT;
  if (!extra || !('ROMP_SID' in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
  return e;
}
// The script as the kernel drives it: the request on stdin, the reply on stdout, timed as the kernel's deadline
// would see it. The reply names every missing id, megabytes for the lists below, so the buffer is raised.
function host(w, req) {
  const t0 = performance.now();
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w), maxBuffer: 64 * 1024 * 1024 });
  const ms = performance.now() - t0;
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  return { code: r.status, stdout: r.stdout, stderr: r.stderr, json, ms };
}
function ok(w, req) {
  const r = host(w, req);
  assert.equal(r.code, 0, `exit ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === true, `expected ok:true, got ${r.stdout.slice(0, 400)}`);
  return r.json;
}
function refused(w, req, code) {
  const r = host(w, req);
  assert.equal(r.code, 0, `a refusal exits 0; got ${r.code}: ${r.stderr.slice(0, 400)}`);
  assert.ok(r.json && r.json.ok === false, `expected ok:false, got ${r.stdout.slice(0, 400)}`);
  assert.equal(r.json.code, code, (r.json.error || '').slice(0, 400));
  return { json: r.json, ms: r.ms };
}
function cliOk(w, name, args) {
  const r = spawnSync(process.execPath, [path.join(VENDOR, 'cli', `track-${name}.mjs`), ...args],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
  assert.equal(r.status, 0, `track-${name} failed: ${r.stderr}`);
  return r;
}
function status(w, file) { return ok(w, { verb: 'status', path: file, args: {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }

test('a request the kernel admits, a hundred thousand ids beside one real change, refuses no-change inside the deadline and writes nothing; accept with the same list refuses the same way', () => {
  const w = world();
  cliOk(w, 'edit', ['--file', w.report, '--old', 'cut p95 latency by 40%', '--new', 'reduced p95 latency by 40%']);
  const st = status(w, w.report);
  const real = st.hunks[0].id;
  const bytes = fs.readFileSync(st.storePath);
  const M = 100_000;
  const ids = [real];
  for (let i = 0; i < M; i++) ids.push(changeId(i));
  const req = { verb: 'comment', path: w.report, args: { changeIds: ids, note: 'On all of these.' }, fence: fenceFor(st) };
  const size = JSON.stringify(req).length;
  assert.ok(size > 1024 * 1024 && size < kernelRequestMax(), `${size} bytes: past a megabyte, under the kernel's request cap`);
  const deadline = kernelDeadlineMs();
  const r = refused(w, req, 'no-change');
  assert.ok(r.ms < deadline, `comment took ${r.ms.toFixed(0)} ms, the kernel's deadline is ${deadline} ms`);
  assert.ok(r.json.error.startsWith(`changes ${changeId(0)}, ${changeId(1)}, `), 'the missing ids, in order: ' + r.json.error.slice(0, 200));
  assert.ok(r.json.error.endsWith(` are no longer pending in ~/notes-api/docs/report.md — reload and retry`), 'one plain line: ' + r.json.error.slice(-120));
  assert.equal(r.json.error.includes(real), false, 'the held change is not among the missing');
  assert.equal(r.json.error.split(', ').length, M, 'each missing id once');
  assert.deepEqual(fs.readFileSync(st.storePath), bytes, 'nothing written');
  assert.deepEqual(status(w, w.report).store.comments, []);
  // the sibling path, the same list under accept: the same refusal, the same order of cost
  const a = refused(w, { verb: 'accept', path: w.report, args: { ids }, fence: fenceFor(st) }, 'no-change');
  assert.ok(a.ms < deadline, `accept took ${a.ms.toFixed(0)} ms, the kernel's deadline is ${deadline} ms`);
  assert.ok(a.json.error.startsWith(`changes ${changeId(0)}, ${changeId(1)}, `), a.json.error.slice(0, 200));
  assert.deepEqual(fs.readFileSync(st.storePath), bytes, 'nothing written by accept either');
});
