// A kernel exit the manager did not ask for is the one worth a line (2026-09-06: a SIGTERM reached
// the kernel pid directly, the manager respawned it with its usual "exited ... respawning" line, and
// nothing said the restart was unrequested; the respawn landed on a different python and every SDK
// session was down for two hours). exitLine is the pure decision: stopped / requested / unrequested,
// and the unrequested case says so. auditSigterm is the manager's own note in restart-audit.jsonl
// before each SIGTERM it sends, so the kernel's "no request on record" verdict is true when it fires.
// Run: node --test tests/manager-exit-attribution.test.js
'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

// STATE_ROOT bakes from env when the manager module loads: point it at a temp dir BEFORE the require.
const STATE = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-exit-'));
process.env.ROMP_STATE_DIR = STATE;
const { exitLine, auditSigterm } = require(path.join(__dirname, '..', 'bin', 'romp-manager'));

const rec = (over) => Object.assign({ spec: { id: 'main', port: 29855 }, child: { pid: 4242 },
  restarts: 3, stopping: false, requested: null }, over);

test('a stopped kernel (stop or shutdown) is reaped, not respawned: the line says stopped', () => {
  const l = exitLine(rec({ stopping: true }), 0, null, 0);
  assert.equal(l.respawn, false);
  assert.match(l.line, /stopped/);
});

test('a kernel the manager SIGTERMed for a restart keeps the plain respawn line', () => {
  const l = exitLine(rec({ requested: 1000 }), null, 'SIGTERM', 0);
  assert.equal(l.respawn, true);
  assert.match(l.line, /respawning in 0ms/);
  assert.doesNotMatch(l.line, /without a restart request/);
});

test('a kernel that exited with no request from the manager says so: signal or crash', () => {
  const l = exitLine(rec(), null, 'SIGTERM', 1000);
  assert.equal(l.respawn, true);
  assert.match(l.line, /kernel 'main' \(pid 4242\) exited without a restart request \(signal or crash\); respawning in 1000ms/);
  assert.match(l.line, /sig=SIGTERM/);
});

test('a crash (exit code, no signal) reads the same way: the manager did not ask', () => {
  const l = exitLine(rec(), 1, null, 2000);
  assert.match(l.line, /without a restart request/);
  assert.match(l.line, /code=1/);
});

test('auditSigterm appends the manager\'s own row to the primary state root by default', () => {
  const t = auditSigterm({ id: 'main', port: 29855 }, 4242, 'restart');
  const rows = fs.readFileSync(path.join(STATE, 'restart-audit.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  const r = rows[rows.length - 1];
  assert.equal(r.action, 'manager-sigterm');
  assert.equal(r.kernel, 'main');
  assert.equal(r.pid, 4242);
  assert.equal(r.reason, 'restart');
  assert.equal(typeof r.t, 'number');
  assert.equal(r.t, t);
});

test('an aux kernel\'s row goes to ITS state root (the kernel reads the audit file under its own root)', () => {
  const aux = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-exit-aux-'));
  auditSigterm({ id: 'aux', port: 29900, stateDir: aux }, 7, 'stop');
  const rows = fs.readFileSync(path.join(aux, 'restart-audit.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  assert.equal(rows[0].kernel, 'aux');
  assert.equal(rows[0].reason, 'stop');
});

test('auditSigterm never throws: an unwritable root is a lost note, not a lost restart', () => {
  assert.doesNotThrow(() => auditSigterm({ id: 'x', port: 1, stateDir: path.join(STATE, 'no', 'such', 'file.txt', 'dir') }, 1, 'restart'));
});
