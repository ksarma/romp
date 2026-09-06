'use strict';
// The `romp down` marker as the manager sees it (2026-09-06). bin/romp writes STATE/down-by-romp
// when it stops the kernel on purpose; here two consumers: `ensure` (the supervised start that the
// far-host scripts of `romp update <host>` and the dashboard's remote restart run) must refuse to
// bring the manager back while the marker exists, since it is the one door that would undo a
// deliberate stop with nobody asking, and a deliberate `up` clears it. Then shutdownAll's other half
// of `romp down`: a kernel that ignores SIGTERM is SIGKILLed, so it never outlives its manager. Run
// from the repo root:
//   node --test tests/manager-*.test.js
const { test, after } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

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

// shutdownAll's escalation (review 2026-09-06, finding 1): the manager used to exit 800ms after one
// SIGTERM, so a kernel that ignored the signal outlived it, still holding its port and its sessions
// under a `romp down` marker that said otherwise. A REAL manager on ports no other suite binds
// (7621/7622) with a stand-in kernel that swallows SIGTERM; ROMP_SHUTDOWN_GRACE_MS shortens the 5s
// grace so the case stays bounded. PATH holds only a no-op tmux, so startTmuxServer() never reaches
// the machine's server (tests/tmux-private.bash has the incident), and the socket directory is
// private too.
test('shutdownAll: a kernel that ignores SIGTERM is SIGKILLed when the grace runs out, and the manager still exits', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-shutdown-'));
  const bin = path.join(dir, 'bin');
  for (const d of [bin, path.join(dir, 'tmux'), path.join(dir, 'state')]) fs.mkdirSync(d);
  fs.writeFileSync(path.join(bin, 'tmux'), '#!/bin/sh\nexit 0\n', { mode: 0o755 });
  const ready = path.join(dir, 'kernel-ready');   // written once the handler is installed: a SIGTERM before that would simply kill the stand-in
  const serve = path.join(dir, 'fake-serve');
  fs.writeFileSync(serve, `#!/bin/sh\nexec "${process.execPath}" -e "process.on('SIGTERM', () => {}); require('fs').writeFileSync(process.env.ROMP_TEST_READY, 'ready'); setInterval(() => {}, 1000)"\n`, { mode: 0o755 });
  const env = Object.assign({}, process.env, {
    PATH: bin, TMUX_TMPDIR: path.join(dir, 'tmux'), ROMP_CLI_SCOPE: '0',
    ROMP_STATE_DIR: path.join(dir, 'state'), ROMP_MANAGER_PORT: '7621', ROMP_SERVE_PORT: '7622',
    ROMP_SERVE_BIN: serve, ROMP_SHUTDOWN_GRACE_MS: '1000', ROMP_TEST_READY: ready,
  });
  delete env.ROMP_SUPERVISED;
  const mgr = spawn(process.execPath, [path.join(__dirname, '..', 'bin', 'romp-manager'), 'up'], { env, stdio: ['ignore', 'ignore', 'pipe'] });
  let log = '';
  mgr.stderr.on('data', (d) => { log += d; });
  const exited = new Promise((resolve) => mgr.on('exit', (code, sig) => resolve({ code, sig })));
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const req = (p, method) => new Promise((resolve, reject) => {
    const r = http.request({ host: '127.0.0.1', port: 7621, path: p, method, timeout: 2000 }, (res) => {
      let b = ''; res.on('data', (d) => (b += d)); res.on('end', () => resolve({ code: res.statusCode, body: b }));
    });
    r.on('error', reject); r.on('timeout', () => { r.destroy(); reject(new Error('timeout')); }); r.end();
  });
  let kpid = 0;
  try {
    for (let i = 0; i < 50 && !(kpid && fs.existsSync(ready)); i++) {   // up to 5s for the control port, the spawn and the handler
      if (!kpid) { try { kpid = ((JSON.parse((await req('/status', 'GET')).body).kernels || [])[0] || {}).pid || 0; } catch (e) { /* not yet */ } }
      if (!(kpid && fs.existsSync(ready))) await sleep(100);
    }
    assert.ok(kpid > 0, `the manager never reported its kernel: ${log}`);
    assert.ok(fs.existsSync(ready), `the stand-in kernel never installed its SIGTERM handler: ${log}`);
    process.kill(kpid, 0);                                  // alive before the stop
    const t0 = Date.now();
    assert.equal((await req('/stop', 'POST')).code, 200);
    const outcome = await Promise.race([exited, sleep(5000).then(() => null)]);
    const elapsed = Date.now() - t0;
    assert.ok(outcome !== null, `the manager was still running ${elapsed}ms after /stop: ${log}`);
    assert.ok(elapsed >= 1000, `the manager left ${elapsed}ms after /stop, before the grace ran out: the kernel had no time to drain`);
    assert.ok(elapsed < 4000, `the manager took ${elapsed}ms to leave after a 1000ms grace`);
    assert.match(log, /pid \d+\) still running 1000ms after SIGTERM; sending SIGKILL/, `the escalation is on the manager log: ${log}`);
    let alive = true;                                       // gone, not merely signalled: SIGKILL cannot be ignored
    for (let i = 0; i < 30 && alive; i++) { try { process.kill(kpid, 0); await sleep(100); } catch (e) { alive = false; } }
    assert.equal(alive, false, `the kernel stand-in (pid ${kpid}) survived the manager`);
  } finally {
    try { mgr.kill('SIGKILL'); } catch (e) { /* gone */ }
    if (kpid) { try { process.kill(kpid, 'SIGKILL'); } catch (e) { /* gone */ } }
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
