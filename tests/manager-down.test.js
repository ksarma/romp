'use strict';
// The `romp down` marker as the manager sees it (2026-09-06). bin/romp writes STATE/down-by-romp
// when it stops the kernel on purpose; here two consumers: `ensure` (the SessionStart auto-start)
// must refuse to bring the manager back while the marker exists — the one door that would undo a
// deliberate stop with nobody asking — and a deliberate `up` clears it. Run from the repo root:
//   node --test tests/manager-*.test.js
const { test, after } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-down-marker-'));
after(() => fs.rmSync(stateDir, { recursive: true, force: true }));   // one leaked dir per run otherwise
process.env.ROMP_STATE_DIR = stateDir;       // baked at require time (STATE_ROOT)
delete process.env.ROMP_SUPERVISED;
const { ensureDecision, downMarkerHeld, clearDownMarker, DOWN_MARKER } =
  require(path.join(__dirname, '..', 'bin', 'romp-manager'));

test('the marker lives under the state root as down-by-romp — the path bin/romp and romp-service write', () => {
  assert.equal(DOWN_MARKER, path.join(stateDir, 'down-by-romp'));
});

test('ensure: a live manager is a no-op, a held marker refuses, otherwise spawn', () => {
  assert.equal(ensureDecision({ alive: true, held: false }), 'noop');
  assert.equal(ensureDecision({ alive: true, held: true }), 'noop', 'a running manager outranks a stale marker');
  assert.equal(ensureDecision({ alive: false, held: true }), 'held', 'down on purpose: auto-start must not undo it');
  assert.equal(ensureDecision({ alive: false, held: false }), 'spawn');
});

test('downMarkerHeld reads the file; clearDownMarker removes it and reports whether there was one', () => {
  const f = path.join(stateDir, 'down-by-romp');
  assert.equal(downMarkerHeld(f), false);
  assert.equal(clearDownMarker(f), false, 'nothing to clear says so — the start log stays quiet');
  fs.writeFileSync(f, JSON.stringify({ t: 1700000000, cmd: 'romp down' }) + '\n');
  assert.equal(downMarkerHeld(f), true);
  assert.equal(clearDownMarker(f), true, 'a deliberate start clears the marker');
  assert.equal(fs.existsSync(f), false);
  assert.equal(downMarkerHeld(f), false);
});

test('startManager clears the marker before anything else (source pin: a deliberate start brings the kernels back)', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'bin', 'romp-manager'), 'utf8');
  const i = src.indexOf('function startManager() {');
  assert.ok(i > 0);
  const body = src.slice(i, i + 400);
  assert.ok(body.indexOf('clearDownMarker()') > 0 && body.indexOf('clearDownMarker()') < body.indexOf('startTmuxServer()'),
    'the clear is the first thing a starting manager does');
});
