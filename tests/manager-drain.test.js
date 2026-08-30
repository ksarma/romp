// The drain gate's silent degradation (fixer round 3, 2026-08-30): kernelToken() swallowed every
// token-read failure into '' with zero log, and fetchBusy parsed only `.busy` out of the kernel's
// response, DISCARDING the `draining` field — the kernel's own refusal signal — so a parked deploy
// could believe new turn starts were held while the kernel armed nothing; busy never quieted, and
// the 15-minute backstop SIGTERM'd the kernel MID-TURN with no line anywhere naming the cause.
// The degrade BEHAVIOR is deliberately unchanged (count-only polling keeps working; the /busy read
// arm needs no token) — these tests pin that the degradation is now VISIBLE, once per park.
// Run: node --test tests/manager-drain.test.js
'use strict';
const { test, beforeEach } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

// STATE_ROOT bakes from env when the manager module loads — point it at a temp dir BEFORE the
// require (this file runs in its own process under node --test, so no other suite is disturbed).
const STATE = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-drain-'));
process.env.ROMP_STATE_DIR = STATE;
delete process.env.ROMP_SERVE_TOKEN;
const { kernelToken, fetchBusy, resetDrainNotices } =
  require(path.join(__dirname, '..', 'bin', 'romp-manager'));

const TOKEN_FILE = path.join(STATE, 'serve-token');

// One /busy stub per test: records the request, answers with a fixed body.
function serve(body) {
  return new Promise((resolve) => {
    const seen = [];
    const srv = http.createServer((req, res) => {
      seen.push({ url: req.url, token: req.headers['x-romp-token'] || null });
      res.setHeader('Content-Type', 'application/json');
      res.end(body);
    });
    srv.listen(0, '127.0.0.1', () =>
      resolve({ port: srv.address().port, seen, close: () => new Promise((r) => srv.close(r)) }));
  });
}

const poll = (port, p) =>
  new Promise((resolve) => fetchBusy(port, (busy, draining) => resolve({ busy, draining }), p));

// The notices go through the manager's log() → process.stderr; capture around each probe.
async function captured(fn) {
  const orig = process.stderr.write;
  let out = '';
  process.stderr.write = (chunk) => { out += chunk; return true; };
  try { await fn(); } finally { process.stderr.write = orig; }
  return out;
}

beforeEach(() => {
  resetDrainNotices();
  try { fs.unlinkSync(TOKEN_FILE); } catch (e) { /* absent is fine */ }
});

test('a readable token file rides every poll as X-Romp-Token, with no notice', async () => {
  fs.writeFileSync(TOKEN_FILE, 'drain-probe-credential\n');
  const s = await serve(JSON.stringify({ busy: 1, draining: true }));
  let logged = '';
  let got;
  try {
    logged = await captured(async () => { got = await poll(s.port, '/busy?drain=1'); });
  } finally { await s.close(); }
  assert.equal(s.seen[0].token, 'drain-probe-credential', 'the 0600 token file is read fresh and attached');
  assert.equal(got.busy, 1);
  assert.equal(got.draining, true, 'the callback now carries the kernel’s draining answer');
  assert.equal(logged, '', 'a healthy handshake logs nothing');
});

test('an unreadable token file polls token-less and says so ONCE, naming path and error', async () => {
  const s = await serve(JSON.stringify({ busy: 0, draining: false }));
  let logged = '';
  let first, second;
  try {
    logged = await captured(async () => {
      first = await poll(s.port);          // plain /busy — the read arm, no drain ask
      second = await poll(s.port);
    });
  } finally { await s.close(); }
  assert.equal(s.seen[0].token, null, 'no invented header — the poll goes token-less');
  assert.equal(first.busy, 0, 'count-only polling still works (degrade behavior unchanged)');
  assert.equal(second.busy, 0);
  const lines = logged.split('\n').filter((l) => /serve token/.test(l));
  assert.equal(lines.length, 1, 'ONE clear line, not one per 3s poll');
  assert.match(lines[0], /serve-token/, 'the line names the token path');
  assert.match(lines[0], /ENOENT|no such file/i, 'the line names the read error');
});

test('a drain=1 poll the kernel answers draining:false logs the refusal ONCE per park', async () => {
  fs.writeFileSync(TOKEN_FILE, 'drain-probe-credential\n');
  const s = await serve(JSON.stringify({ busy: 3, draining: false }));
  let logged = '';
  let got;
  try {
    logged = await captured(async () => {
      got = await poll(s.port, '/busy?drain=1');
      await poll(s.port, '/busy?drain=1');   // the 3s re-poll must not repeat the line
    });
  } finally { await s.close(); }
  assert.equal(got.busy, 3, 'the count still reads — the refusal degrades, never breaks, the poll');
  assert.equal(got.draining, false);
  const lines = logged.split('\n').filter((l) => /refused the drain/i.test(l));
  assert.equal(lines.length, 1, 'rate-limited: once per park, not per poll');
  assert.match(lines[0], /not held/i, 'the line says what the refusal means: no hold armed');
});

test('a fresh park re-arms the refusal notice (resetDrainNotices is the per-park seam)', async () => {
  fs.writeFileSync(TOKEN_FILE, 'drain-probe-credential\n');
  const s = await serve(JSON.stringify({ busy: 2, draining: false }));
  let logged = '';
  try {
    logged = await captured(async () => {
      await poll(s.port, '/busy?drain=1');
      resetDrainNotices();                   // queueQuietRestart calls this when a new park begins
      await poll(s.port, '/busy?drain=1');
    });
  } finally { await s.close(); }
  assert.equal(logged.split('\n').filter((l) => /refused the drain/i.test(l)).length, 2);
});

test('a plain /busy read never cries refusal — only a poll that ASKED for the drain', async () => {
  fs.writeFileSync(TOKEN_FILE, 'drain-probe-credential\n');
  const s = await serve(JSON.stringify({ busy: 5, draining: false }));
  let logged = '';
  try {
    logged = await captured(async () => { await poll(s.port); });
  } finally { await s.close(); }
  assert.equal(logged, '', 'draining:false on a read-only poll is normal, not a refusal');
});

test('an older kernel without the draining field stays silent (unknown is not refused)', async () => {
  fs.writeFileSync(TOKEN_FILE, 'drain-probe-credential\n');
  const s = await serve(JSON.stringify({ busy: 2 }));
  let logged = '';
  let got;
  try {
    logged = await captured(async () => { got = await poll(s.port, '/busy?drain=1'); });
  } finally { await s.close(); }
  assert.equal(got.busy, 2);
  assert.equal(got.draining, null);
  assert.equal(logged, '', 'no field is no evidence — never a false refusal line against an old kernel');
});

test('kernelToken prefers the env, then the token file', () => {
  fs.writeFileSync(TOKEN_FILE, 'file-credential\n');
  assert.equal(kernelToken(), 'file-credential');
  process.env.ROMP_SERVE_TOKEN = 'env-credential';
  try { assert.equal(kernelToken(), 'env-credential'); }
  finally { delete process.env.ROMP_SERVE_TOKEN; }
});

// The park half of the wiring lives inside queueQuietRestart's closures (module state: pendingQuiet,
// KERNEL_PORT), so it is pinned at the source like the suite's other closure pins (T121/T160): the
// park records a refused hold, and the backstop apply line names that the hold was never armed —
// a mid-turn cut now has a cause on record.
test('the park records a refused hold and the backstop line names it (source pin)', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'bin', 'romp-manager'), 'utf8');
  assert.match(src, /drainRefused/, 'the park carries the refused-hold bit');
  assert.ok(src.includes("fetchBusy(KERNEL_PORT, cb, '/busy?drain=1')"),
    'the parked poll still binds the drain-refresh spelling of the probe');
  assert.match(src, /never armed/, 'the backstop apply line says the hold was never armed');
  assert.match(src, /resetDrainNotices\(\)/, 'a fresh park re-arms the once-per-park notices');
});
