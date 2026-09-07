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
const MGR = path.join(__dirname, '..', 'bin', 'romp-manager');
const { exitLine, auditSigterm, restartKernel, restartAll, stopKernel, stopTrigger, kernels, DOWN_MARKER } = require(MGR);
const { spawnSync } = require('node:child_process');

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
  assert.equal(l.respawn, true);
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
  assert.equal(r.trigger, 'restart');      // no trigger given: the reason stands in
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

// ── the wiring: the row goes on disk BEFORE the signal, and the record says what was asked ────────
// The pure functions above would stay green if restartKernel moved its auditSigterm below the kill,
// dropped `rec.requested`, or stopKernel lost its row; on a live box each of those makes the kernel's
// "no request on record" verdict false for every manager kill. A stand-in child records the ledger
// as it stood at the moment of each kill, so "row before signal" is asserted on ORDER.
const ledger = (root) => {
  try { return fs.readFileSync(path.join(root, 'restart-audit.jsonl'), 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse); }
  catch (e) { return []; }
};
function seed(id, spec, pid) {
  const root = spec.stateDir || STATE;
  const child = { pid, kills: [] };
  child.kill = (sig) => child.kills.push({ sig, rowsAtKill: ledger(root) });
  const r = { spec, child, restarts: 0, quickCrashes: 0, startedAt: Date.now(), stopping: false, requested: null };
  kernels.set(id, r);
  return r;
}

test('restartKernel: the row is on disk when the SIGTERM goes out, and the exit is marked requested', () => {
  const before = ledger(STATE).length;
  const r = seed('main', { id: 'main', port: 29855 }, 4242);
  try {
    assert.equal(restartKernel('main'), true);
    assert.deepEqual(r.child.kills.map((k) => k.sig), ['SIGTERM']);
    const seen = r.child.kills[0].rowsAtKill;
    assert.equal(seen.length, before + 1);                    // written before, not after, the kill
    const row = seen[seen.length - 1];
    assert.deepEqual([row.action, row.kernel, row.pid, row.reason, row.trigger],
      ['manager-sigterm', 'main', 4242, 'restart', 'restart']);
    assert.equal(typeof r.requested, 'number');               // exitLine: asked for, not a stray signal
    assert.equal(r.stopping, false);                          // ...and respawned, not reaped
  } finally { kernels.delete('main'); }
});

test('restartAll (romp refresh) names its trigger on every kernel, each row under that kernel\'s own root', () => {
  const aux = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-exit-aux2-'));
  const m = seed('main', { id: 'main', port: 29855 }, 1);
  const a = seed('aux', { id: 'aux', port: 29900, stateDir: aux }, 2);
  try {
    assert.deepEqual(restartAll().sort(), ['aux', 'main']);
    const mrow = m.child.kills[0].rowsAtKill.pop();
    const arow = a.child.kills[0].rowsAtKill.pop();
    assert.deepEqual([mrow.kernel, mrow.reason, mrow.trigger], ['main', 'restart', 'restart-all']);
    assert.deepEqual([arow.kernel, arow.reason, arow.trigger], ['aux', 'restart', 'restart-all']);
    assert.equal(ledger(aux).length, 1);                      // the aux row went to the aux root only
  } finally { kernels.delete('main'); kernels.delete('aux'); }
});

test('stopKernel: the stop row precedes the SIGTERM, the record is marked stopping, the trigger is "stop"', () => {
  const r = seed('main', { id: 'main', port: 29855 }, 4243);
  try {
    assert.equal(stopKernel('main'), true);
    assert.equal(r.stopping, true);
    const row = r.child.kills[0].rowsAtKill.pop();
    assert.deepEqual([row.action, row.pid, row.reason, row.trigger], ['manager-sigterm', 4243, 'stop', 'stop']);
  } finally { kernels.delete('main'); }
});

test('stopTrigger reads romp down\'s marker at stop time: present means the CLI asked (cli-down)', () => {
  assert.equal(stopTrigger(), 'stop');
  assert.equal(DOWN_MARKER, path.join(STATE, 'down-by-romp'));
  fs.writeFileSync(DOWN_MARKER, '{"t": 1, "cmd": "romp down"}\n');
  try {
    assert.equal(stopTrigger(), 'cli-down');
    const r = seed('main', { id: 'main', port: 29855 }, 4244);
    try {
      stopKernel('main');
      assert.equal(r.child.kills[0].rowsAtKill.pop().trigger, 'cli-down');
    } finally { kernels.delete('main'); }
  } finally { fs.unlinkSync(DOWN_MARKER); }
  assert.equal(stopTrigger(), 'stop');
});

// shutdownAll exits the process (after 800 ms) and latches, so each case runs in a child node that
// seeds a stand-in kernel, calls it, and is allowed to exit on its own: the real path, no stubbing.
function shutdownCase(withMarker, trigger) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-exit-down-'));
  const script = `
    const fs = require('fs'), path = require('path');
    const m = require(${JSON.stringify(MGR)});
    const root = process.env.ROMP_STATE_DIR;
    if (${withMarker ? 'true' : 'false'}) fs.writeFileSync(m.DOWN_MARKER, '{}');
    const rowsNow = () => { try { return fs.readFileSync(path.join(root, 'restart-audit.jsonl'), 'utf8').trim().split('\\n').filter(Boolean).length; } catch (e) { return 0; } };
    const child = { pid: 777, kill(sig) { fs.appendFileSync(path.join(root, 'kills.txt'), sig + ' rows=' + rowsNow() + '\\n'); } };
    m.kernels.set('main', { spec: { id: 'main', port: 1 }, child, restarts: 0, quickCrashes: 0, startedAt: Date.now(), stopping: false, requested: null });
    m.shutdownAll(0${trigger ? ', ' + JSON.stringify(trigger) : ''});
  `;
  const env = Object.assign({}, process.env, { ROMP_STATE_DIR: root });
  delete env.XDG_STATE_HOME;
  const r = spawnSync(process.execPath, ['-e', script], { env, encoding: 'utf8', timeout: 10000 });
  assert.equal(r.status, 0, r.stderr);
  return { rows: ledger(root), kills: fs.readFileSync(path.join(root, 'kills.txt'), 'utf8').trim().split('\n') };
}

test('shutdownAll with romp down\'s marker on disk: every kernel\'s stop row says cli-down, before the kill', () => {
  const { rows, kills } = shutdownCase(true);
  assert.equal(rows.length, 1);
  assert.deepEqual([rows[0].action, rows[0].reason, rows[0].trigger, rows[0].pid], ['manager-sigterm', 'stop', 'cli-down', 777]);
  assert.deepEqual(kills, ['SIGTERM rows=1']);               // the row was there when the signal went out
});

test('shutdownAll with no marker (a service stop by hand, Ctrl+C): the trigger is stop', () => {
  const { rows } = shutdownCase(false);
  assert.equal(rows[0].trigger, 'stop');
});

test('the stale-manager self-bounce stops its kernels with trigger refresh (they are coming back)', () => {
  const { rows } = shutdownCase(false, 'refresh');
  assert.deepEqual([rows[0].reason, rows[0].trigger], ['stop', 'refresh']);
});
