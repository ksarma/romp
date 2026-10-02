// romp-manager's multi-kernel registry (plans/multi-kernel.md phase 3): kernels.json profiles are
// parsed FRESH at every consult and validated hard — a malformed entry is DROPPED with a loud error,
// never half-applied — and specEnv is the whole per-kernel isolation story (state root, Claude config
// dir, postal port ride the child env). fileStamp backs the --refresh stale-manager
// detection (the user 2026-07-24: a long-lived manager respawned kernels on start-time defaults the
// disk had moved past, with everything reporting success). The second half pins one kernel per state
// root at the source (2026-10-02): the manager never starts a kernel other than main whose state root
// resolves to the primary's, on any road (the boot pass, the crash respawn, /ensure), and says so once.
// Run: node --test tests/manager-registry.test.js
const { test } = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const http = require('node:http');
const { spawn, spawnSync } = require('node:child_process');
const { freePort } = require(path.join(__dirname, 'manager-ports'));
const MGR = path.join(__dirname, '..', 'bin', 'romp-manager');
const { loadSpecs, specEnv, fileStamp } = require(MGR);

const MAIN = 29855, CTRL = 7432;

function withFile(content, fn) {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-kernels-'));
  const f = path.join(d, 'kernels.json');
  if (content !== null) fs.writeFileSync(f, content);
  try { return fn(f); } finally { fs.rmSync(d, { recursive: true, force: true }); }
}

test('no kernels.json → just main, no errors (single-kernel default)', () => {
  withFile(null, (f) => {
    const { specs, errors } = loadSpecs(f, MAIN, CTRL);
    assert.deepEqual(specs, [{ id: 'main', port: MAIN }]);
    assert.deepEqual(errors, []);
  });
});

test('a full profile parses with every isolation field', () => {
  withFile(JSON.stringify({ kernels: [{ id: 'alice', port: 30001, postalPort: 30002,
    stateDir: '/tmp/romp-alice', claudeConfigDir: '/tmp/claude-alice' }] }), (f) => {
    const { specs, errors } = loadSpecs(f, MAIN, CTRL);
    assert.deepEqual(errors, []);
    assert.equal(specs.length, 2);
    assert.deepEqual(specs[1], { id: 'alice', port: 30001, postalPort: 30002,
      stateDir: '/tmp/romp-alice', claudeConfigDir: '/tmp/claude-alice' });
  });
});

test('unreadable JSON drops the whole file loudly and keeps main', () => {
  withFile('{not json', (f) => {
    const { specs, errors } = loadSpecs(f, MAIN, CTRL);
    assert.deepEqual(specs, [{ id: 'main', port: MAIN }]);
    assert.equal(errors.length, 1);
    assert.match(errors[0], /unreadable JSON/);
  });
});

test('duplicate ids, taken ports, and malformed fields drop per-entry with errors; an unknown key is ignored', () => {
  withFile(JSON.stringify({ kernels: [
    { id: 'a', port: 30001 },
    { id: 'a', port: 30002 },                       // dup id
    { id: 'b', port: 30001 },                       // dup port
    { id: 'c', port: MAIN },                        // collides with main
    { id: 'd', port: CTRL },                        // collides with the control port
    { id: 'BAD ID', port: 30003 },                  // malformed id
    { id: 'e', port: 30004, stateDir: 'relative/nope' },   // malformed stateDir
    { id: 'f', port: 30005, claudeConfigDir: 'relative/nope' },   // malformed claudeConfigDir
    { id: 'g', port: 30006 },                       // fine
    { id: 'h', port: 30007, retiredField: 'x' },    // an unknown key (a profile field since retired, say) is not the entry's problem
  ] }), (f) => {
    const { specs, errors } = loadSpecs(f, MAIN, CTRL);
    assert.deepEqual(specs.map((s) => s.id), ['main', 'a', 'g', 'h']);
    assert.deepEqual(specs[3], { id: 'h', port: 30007 }, 'the unknown key is dropped from the spec, the entry kept');
    assert.equal(errors.length, 7, errors.join('\n'));   // one per dropped entry above
  });
});

test('a main entry overrides only the port — the stale-env escape hatch', () => {
  withFile(JSON.stringify({ kernels: [{ id: 'main', port: 31000, stateDir: '/tmp/x' }] }), (f) => {
    const { specs } = loadSpecs(f, MAIN, CTRL);
    assert.deepEqual(specs[0], { id: 'main', port: 31000 }, 'port moves; main keeps the primary state root');
  });
});

test('specEnv carries the whole isolation story, and only what the spec sets', () => {
  const base = { PATH: '/usr/bin', HOME: '/home/u' };
  const ids = { managerPid: 42, controlPort: CTRL };
  const full = specEnv({ id: 'alice', port: 30001, postalPort: 30002, stateDir: '/tmp/ra',
                         claudeConfigDir: '/tmp/ca' }, base, ids);
  assert.equal(full.ROMP_SERVE_PORT, '30001');
  assert.equal(full.ROMP_KERNEL_PORT, '30001', 'both spellings of the listen port move together');
  assert.equal(full.ROMP_POSTAL_PORT, '30002');
  assert.equal(full.ROMP_STATE_DIR, '/tmp/ra');
  assert.equal(full.CLAUDE_CONFIG_DIR, '/tmp/ca');
  assert.equal(full.ROMP_MANAGER_PID, '42');
  assert.equal(full.PATH, '/usr/bin', 'base env rides through');
  const bare = specEnv({ id: 'main', port: MAIN }, base, ids);
  for (const k of ['ROMP_POSTAL_PORT', 'ROMP_STATE_DIR', 'CLAUDE_CONFIG_DIR']) {
    assert.ok(!(k in bare), k + ' must not leak into an unscoped kernel (main keeps the process defaults)');
  }
  assert.ok(!('ROMP_STATE_DIR' in base), 'the base object is never mutated');
});

test('specEnv overwrites a stale inherited ROMP_KERNEL_PORT from the base env', () => {
  // The manager's own env may carry the PRIMARY kernel's port under the other spelling. An aux
  // kernel inheriting that copy is how one profile's sessions end up addressing another
  // profile's kernel, so the spec's port has to win under BOTH names.
  const base = { PATH: '/usr/bin', ROMP_KERNEL_PORT: '29855', ROMP_SERVE_PORT: '29855' };
  const env = specEnv({ id: 'alice', port: 30001 }, base, { managerPid: 42, controlPort: CTRL });
  assert.equal(env.ROMP_KERNEL_PORT, '30001');
  assert.equal(env.ROMP_SERVE_PORT, '30001');
});

test('fileStamp changes when the file changes — the staleness detector', () => {
  withFile('one', (f) => {
    const a = fileStamp(f);
    assert.notEqual(a, '', 'a real file stamps non-empty');
    fs.writeFileSync(f, 'two-longer');
    assert.notEqual(fileStamp(f), a, 'a rewrite moves the stamp');
    assert.equal(fileStamp(f + '.missing'), '', 'a missing file stamps empty');
  });
});

// ── one kernel per state root, refused at the source (2026-10-02) ──────────────────────────────────
// A kernel locks <its state root>/kernel.lock before it writes there and the first to take it serves
// (kernel/kernel.py _kernel_lock_acquire). The kernel cannot tell the primary from a second kernel the
// manager started on the primary's root, so a kernels.json profile with no stateDir, or an /ensure for a
// port no profile names, could take the primary's root and lock the primary out. The manager refuses such
// a kernel before it starts (bin/romp-manager rootConflict), keyed on the root it would resolve.
//
// The harness: a real manager in a private world (tests/manager-token.test.js's shape), its own state root
// holding a serve token, ports from this file's block (tests/manager-ports.js), and a stand-in kernel that
// records each start in a log and takes the kernel's instance lock as the kernel does: an exclusive flock
// on kernel.lock under the root kernel/judge.py would resolve from its environment, exit 75 when another
// process holds it. Python for the flock (node has none); FAKE_LATE_PORT makes one port reach its lock
// point late, FAKE_CRASH_PORT and FAKE_CRASHES make one port's first starts exit soon after they serve.

const REGISTRY_TOKEN = 'zq9-registry-token-zq9';   // synthetic
const PY3 = (() => {
  const r = spawnSync('python3', ['-c', 'import sys; print(sys.executable)'], { encoding: 'utf8' });
  return r.status === 0 ? r.stdout.trim() : '';
})();
const FAKE_KERNEL = String.raw`
import fcntl, json, os, sys, time
env = os.environ
root = env.get("ROMP_STATE_DIR") or os.path.join(env.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state"), "romp")
port = int(env["ROMP_SERVE_PORT"])
log = env["FAKE_KERNEL_LOG"]

def note(event):
    with open(log, "a") as fh:
        fh.write(json.dumps({"event": event, "port": port, "pid": os.getpid(), "root": os.path.realpath(root)}) + "\n")

def starts_before():
    try:
        with open(log) as fh:
            rows = [json.loads(ln) for ln in fh if ln.strip()]
    except OSError:
        return 0
    return len([r for r in rows if r["port"] == port and r["event"] == "start"])

crash = str(port) == env.get("FAKE_CRASH_PORT") and starts_before() < int(env.get("FAKE_CRASHES", "0"))
note("start")
if str(port) == env.get("FAKE_LATE_PORT"):
    time.sleep(float(env.get("FAKE_LATE_S", "0")))
os.makedirs(root, exist_ok=True)
fd = os.open(os.path.join(root, "kernel.lock"), os.O_RDWR | os.O_CREAT, 0o600)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    note("refused")
    sys.exit(75)
note("serving")
if crash:
    time.sleep(0.1)
    note("crash")
    sys.exit(1)
while True:
    time.sleep(3600)
`;

// A private world: h.state is the manager's state root (the primary's), h.writeKernels(list) writes its
// kernels.json, h.start(env) starts the manager, h.rows() reads the stand-in's log, h.cleanup() ends it all.
async function world() {
  assert.ok(PY3, 'python3 runs the stand-in kernel (its flock is the kernel lock\'s), and none answered on PATH');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-registry-'));
  const bin = path.join(dir, 'bin'), state = path.join(dir, 'state');
  for (const d of [bin, state]) fs.mkdirSync(d);
  fs.writeFileSync(path.join(state, 'serve-token'), REGISTRY_TOKEN + '\n', { mode: 0o600 });
  const kernelPy = path.join(dir, 'fake_kernel.py');
  fs.writeFileSync(kernelPy, FAKE_KERNEL);
  const serve = path.join(dir, 'fake-serve');
  fs.writeFileSync(serve, `#!/bin/sh\nexec "${PY3}" -I "${kernelPy}" "$@"\n`, { mode: 0o755 });
  const h = { dir, state, log: '', starts: path.join(dir, 'starts.jsonl'), mgr: null, exited: null,
              port: await freePort(__filename), mainPort: await freePort(__filename) };
  h.sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  h.writeKernels = (list) => fs.writeFileSync(path.join(state, 'kernels.json'), JSON.stringify({ kernels: list }));
  h.rows = () => {
    let raw = '';
    try { raw = fs.readFileSync(h.starts, 'utf8'); } catch (e) { return []; }
    return raw.split('\n').filter((l) => l.trim()).map((l) => JSON.parse(l));
  };
  h.at = (port, event) => h.rows().filter((r) => r.port === port && (!event || r.event === event));
  h.until = async (pred, ms, what) => {
    const end = Date.now() + ms;
    while (Date.now() < end) { if (pred()) return; await h.sleep(50); }
    assert.fail(`${what}, not within ${ms} ms; manager log:\n${h.log}\nstand-in log:\n${JSON.stringify(h.rows(), null, 1)}`);
  };
  h.req = (p, method) => new Promise((resolve, reject) => {
    const headers = method === 'GET' ? {} : { 'X-Romp-Token': REGISTRY_TOKEN };
    const r = http.request({ host: '127.0.0.1', port: h.port, path: p, method, timeout: 3000, headers }, (res) => {
      let b = ''; res.on('data', (d) => (b += d)); res.on('end', () => resolve({ code: res.statusCode, body: b }));
    });
    r.on('error', reject); r.on('timeout', () => { r.destroy(); reject(new Error('timeout')); }); r.end();
  });
  h.kernels = async () => (JSON.parse((await h.req('/status', 'GET')).body).kernels || []);
  // the lines saying kernel `id` was not started
  h.refusals = (id) => h.log.split('\n').filter((l) => l.includes(`kernel '${id}' (port `) && l.includes('is not started'));
  h.start = async (extra) => {
    const env = Object.assign({}, process.env, {
      PATH: bin, ROMP_CLI_SCOPE: '0',
      ROMP_STATE_DIR: state, ROMP_MANAGER_PORT: String(h.port), ROMP_SERVE_PORT: String(h.mainPort),
      ROMP_SERVE_BIN: serve, ROMP_SHUTDOWN_GRACE_MS: '500', FAKE_KERNEL_LOG: h.starts,
    }, extra || {});
    for (const k of ['ROMP_SUPERVISED', 'ROMP_SERVE_TOKEN', 'XDG_STATE_HOME', 'ROMP_KERNEL_PORT']) delete env[k];
    h.mgr = spawn(process.execPath, [MGR, 'up'], { env, stdio: ['ignore', 'ignore', 'pipe'] });
    h.mgr.stderr.on('data', (d) => { h.log += d; });
    h.exited = new Promise((resolve) => h.mgr.on('exit', (code, sig) => resolve({ code, sig })));
    await h.until(() => h.log.includes(`kernel 'main' → :${h.mainPort}`), 10000, 'the manager did not start main');
    // the boot pass spawns every spec in one synchronous loop, so by main's own start a spec the pass
    // started has its spawn line in the log too; the settle lets a stand-in it started reach its log
    await h.until(() => h.at(h.mainPort, 'start').length >= 1, 10000, 'main\'s stand-in did not start');
    await h.sleep(400);
  };
  h.cleanup = async () => {
    if (h.mgr) {
      try { h.mgr.kill('SIGTERM'); } catch (e) { /* gone */ }   // shutdownAll stops the kernels
      await Promise.race([h.exited, h.sleep(3000)]);
      try { h.mgr.kill('SIGKILL'); } catch (e) { /* gone */ }
    }
    for (const pid of new Set(h.rows().map((r) => r.pid))) {    // only a stand-in this world started, still running
      let mine = true;
      try { mine = fs.readFileSync(`/proc/${pid}/cmdline`, 'utf8').includes(dir); } catch (e) { mine = !fs.existsSync('/proc/self'); }
      if (mine) { try { process.kill(pid, 'SIGKILL'); } catch (e) { /* gone */ } }
    }
    fs.rmSync(dir, { recursive: true, force: true });
  };
  return h;
}

test('a profile with no stateDir is not started, and the one line naming it and the remedy is said once across respawn ticks and /ensure retries', async () => {
  const h = await world();
  try {
    const aux = await freePort(__filename);
    h.writeKernels([{ id: 'aux', port: aux }]);
    // main's first two starts exit soon after serving, so the manager respawns it twice: each respawn re-reads kernels.json
    await h.start({ FAKE_CRASH_PORT: String(h.mainPort), FAKE_CRASHES: '2' });
    await h.until(() => h.at(h.mainPort, 'serving').length >= 3, 15000, 'main was not respawned twice');
    for (let i = 0; i < 2; i++) {
      const r = await h.req(`/ensure?port=${aux}`, 'POST');   // the extension's retry, twice
      assert.equal(r.code, 409, r.body);
    }
    await h.sleep(300);
    assert.deepEqual(h.at(aux), [], 'the profile with no stateDir was started');
    assert.doesNotMatch(h.log, new RegExp(`kernel 'aux' → :${aux}`), 'the manager spawned the profile');
    const lines = h.refusals('aux');
    assert.equal(lines.length, 1, `one line for the profile across the boot pass, two respawn ticks and two /ensure retries:\n${h.log}`);
    assert.match(lines[0], new RegExp(`kernel 'aux' \\(port ${aux}\\)`), 'the line names the profile');
    assert.match(lines[0], /has no stateDir/);
    assert.match(lines[0], /Give the profile its own stateDir in .*kernels\.json/, 'the line names the remedy');
    assert.deepEqual((await h.kernels()).map((k) => k.id), ['main']);
  } finally { await h.cleanup(); }
});

test('a profile whose stateDir resolves to the primary\'s root, through a symlink or with a trailing slash, is refused the same way', async () => {
  const h = await world();
  try {
    const [viaLink, slashed] = [await freePort(__filename), await freePort(__filename)];
    const link = path.join(h.dir, 'state-link');
    fs.symlinkSync(h.state, link);
    h.writeKernels([{ id: 'linked', port: viaLink, stateDir: link }, { id: 'slashed', port: slashed, stateDir: h.state + '/' }]);
    await h.start();
    for (const [id, port, dirAsWritten] of [['linked', viaLink, link], ['slashed', slashed, h.state + '/']]) {
      assert.deepEqual(h.at(port), [], `${id} was started on the primary's root`);
      assert.equal((await h.req(`/ensure?port=${port}`, 'POST')).code, 409, `/ensure for ${id}`);
      const lines = h.refusals(id);
      assert.equal(lines.length, 1, `one line for ${id}:\n${h.log}`);
      assert.ok(lines[0].includes(`stateDir ${JSON.stringify(dirAsWritten)} resolves to the primary kernel's state root`), lines[0]);
      assert.match(lines[0], /Give the profile its own stateDir/);
    }
    await h.sleep(300);
    assert.deepEqual(h.rows().filter((r) => r.port !== h.mainPort), [], 'nothing but main started');
    assert.deepEqual((await h.kernels()).map((k) => k.id), ['main']);
  } finally { await h.cleanup(); }
});

test('/ensure for a port no profile names, or for a profile whose root is the primary\'s, answers 409 naming the kernel, the primary\'s port and the remedy, and starts nothing', async () => {
  const h = await world();
  try {
    const [bare, prof] = [await freePort(__filename), await freePort(__filename)];
    h.writeKernels([{ id: 'nodir', port: prof }]);
    await h.start();
    for (const [port, id, remedy] of [[bare, `k${bare}`, `Add a profile for port ${bare} with its own stateDir`],
                                      [prof, 'nodir', 'Give the profile its own stateDir']]) {
      for (let i = 0; i < 2; i++) {
        const r = await h.req(`/ensure?port=${port}`, 'POST');
        assert.equal(r.code, 409, `${id}: ${r.body}`);       // >= 400 and neither 401 nor 503: the extension's refusal toast
        const body = JSON.parse(r.body);
        assert.equal(body.ok, false);
        assert.equal(body.id, id);
        assert.equal(body.primaryPort, h.mainPort);
        assert.ok(body.error.includes(`kernel '${id}' (port ${port})`), `the body names the kernel: ${body.error}`);
        assert.ok(body.error.includes(`the primary kernel on port ${h.mainPort}`), `the body names the primary's port: ${body.error}`);
        assert.ok(body.error.includes(remedy), `the body names the remedy: ${body.error}`);
      }
      assert.equal(h.refusals(id).length, 1, `one line for ${id} across its two requests:\n${h.log}`);
    }
    await h.sleep(300);
    assert.deepEqual(h.rows().filter((r) => r.port !== h.mainPort), [], 'no kernel was started for either port');
    assert.deepEqual((await h.kernels()).map((k) => k.id), ['main']);
  } finally { await h.cleanup(); }
});

test('a profile with a stateDir of its own starts as before, one that shares the primary\'s path as a prefix and one that does not exist yet alike', async () => {
  const h = await world();
  try {
    const [sib, later] = [await freePort(__filename), await freePort(__filename)];
    const sibDir = h.state + '-own';                       // a string prefix of the primary's root is not that root
    fs.mkdirSync(sibDir);
    const laterDir = path.join(h.dir, 'later', 'aux-state');   // created by its kernel at its first start
    h.writeKernels([{ id: 'sib', port: sib, stateDir: sibDir }, { id: 'later', port: later, stateDir: laterDir }]);
    await h.start();
    await h.until(() => h.at(sib, 'serving').length === 1 && h.at(later, 'serving').length === 1, 10000, 'both profiles serve');
    assert.equal(h.at(sib, 'serving')[0].root, fs.realpathSync(sibDir));
    assert.equal(h.at(later, 'serving')[0].root, fs.realpathSync(laterDir));
    assert.doesNotMatch(h.log, /is not started/, 'no profile was refused');
    assert.deepEqual((await h.kernels()).map((k) => k.id).sort(), ['later', 'main', 'sib']);
    const again = await h.req(`/ensure?port=${sib}`, 'POST');
    assert.equal(again.code, 200, again.body);
    assert.equal(JSON.parse(again.body).spawned, false, '/ensure attaches to the running profile');
  } finally { await h.cleanup(); }
});

test('the primary is never refused at boot with a profile on its root present, even when it reaches its lock point after that profile would', async () => {
  const h = await world();
  try {
    const [aux, linked] = [await freePort(__filename), await freePort(__filename)];
    const link = path.join(h.dir, 'state-link');
    fs.symlinkSync(h.state, link);
    h.writeKernels([{ id: 'aux', port: aux }, { id: 'linked', port: linked, stateDir: link }]);
    // main's stand-in waits 0.6 s before its lock, so a profile started beside it in the boot pass would take the lock first
    await h.start({ FAKE_LATE_PORT: String(h.mainPort), FAKE_LATE_S: '0.6' });
    await h.until(() => h.at(h.mainPort, 'serving').length + h.at(h.mainPort, 'refused').length >= 1, 10000, 'main reached its lock');
    await h.sleep(1500);                                    // a refused main's backoff respawn would refuse again here
    assert.deepEqual(h.at(h.mainPort, 'refused'), [], `the primary was refused its own root:\n${JSON.stringify(h.rows())}`);
    assert.equal(h.at(h.mainPort, 'serving').length, 1, 'the primary serves, started once');
    assert.equal(h.at(h.mainPort, 'serving')[0].root, fs.realpathSync(h.state));
    assert.doesNotMatch(h.log, /kernel 'main' .*exited/, 'the primary never exited');
    assert.deepEqual(h.rows().filter((r) => r.port !== h.mainPort), [], 'neither profile on the primary\'s root started');
  } finally { await h.cleanup(); }
});

test('a profile refused at boot starts once its stateDir is its own, and is not respawned onto the primary\'s root when the entry loses it again, which is said again', async () => {
  const h = await world();
  try {
    const aux = await freePort(__filename);
    const own = path.join(h.dir, 'aux-state');
    h.writeKernels([{ id: 'aux', port: aux }]);
    await h.start();
    assert.equal(h.refusals('aux').length, 1, `refused at boot:\n${h.log}`);
    h.writeKernels([{ id: 'aux', port: aux, stateDir: own }]);   // the remedy: a refusal said before does not hold back the fixed profile
    const r = await h.req(`/ensure?port=${aux}`, 'POST');
    assert.equal(r.code, 200, r.body);
    assert.equal(JSON.parse(r.body).spawned, true);
    await h.until(() => h.at(aux, 'serving').length === 1, 10000, 'the profile serves on its own root');
    assert.equal(h.at(aux, 'serving')[0].root, fs.realpathSync(own));
    h.writeKernels([{ id: 'aux', port: aux }]);            // the edit lands on the kernel's next start (the spawn-time re-read)
    assert.equal((await h.req('/restart?kernel=aux', 'POST')).code, 200);
    // the same refusal as at boot, said again: it ends a kernel that was running, after an exit line that promised a respawn
    await h.until(() => h.refusals('aux').length === 2, 10000, 'the respawn was not refused, or not said');
    const exited = h.log.indexOf(`kernel 'aux' exited`);
    assert.ok(exited >= 0 && h.log.lastIndexOf(h.refusals('aux')[1]) > exited, 'the refusal follows the exit line');
    assert.equal(h.refusals('aux')[1], h.refusals('aux')[0]);
    await h.sleep(1500);                                    // the crash backoff's first delay is 1 s: a respawn would be here
    assert.equal(h.at(aux, 'start').length, 1, `the profile was started again:\n${JSON.stringify(h.rows())}`);
    assert.equal(h.refusals('aux').length, 2);
    assert.deepEqual((await h.kernels()).map((k) => k.id), ['main'], '/status no longer lists the refused profile');
    assert.equal(h.at(h.mainPort, 'start').length, 1, 'main untouched');
  } finally { await h.cleanup(); }
});

test('resolveStateRoot: a symlink, a trailing slash, a tail that does not exist yet and a dangling link resolve to the real path the kernel will use', () => {
  const { resolveStateRoot } = require(MGR);
  assert.equal(typeof resolveStateRoot, 'function', 'bin/romp-manager exports resolveStateRoot');
  const d = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'romp-root-resolve-')));
  try {
    const real = path.join(d, 'x', 'real'), other = path.join(d, 'x', 'other');
    fs.mkdirSync(real, { recursive: true });
    fs.mkdirSync(other);
    fs.symlinkSync(real, path.join(d, 'link'));
    fs.symlinkSync(path.join(d, 'not-yet'), path.join(d, 'dangling'));
    assert.equal(resolveStateRoot(path.join(d, 'link')), real, 'a symlink resolves to its target');
    assert.equal(resolveStateRoot(real + '/'), real, 'a trailing slash is stripped');
    assert.equal(resolveStateRoot(real + '//'), real);
    assert.equal(resolveStateRoot(path.join(d, 'link', 'a', 'b')), path.join(real, 'a', 'b'), 'a missing tail under a link');
    assert.equal(resolveStateRoot(path.join(d, 'dangling')), path.join(d, 'not-yet'), 'a dangling link is followed');
    assert.equal(resolveStateRoot(path.join(d, 'dangling') + '/sub'), path.join(d, 'not-yet', 'sub'), 'and so is one above a missing tail');
    assert.equal(resolveStateRoot(path.join(d, 'link') + '/../other'), other, '.. after a link is the target\'s parent, as the kernel opens it');
    assert.equal(resolveStateRoot(path.relative(process.cwd(), real)), real, 'a relative path is the working directory\'s');
  } finally { fs.rmSync(d, { recursive: true, force: true }); }
});
