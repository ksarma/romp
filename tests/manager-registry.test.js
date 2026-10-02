// romp-manager's multi-kernel registry (plans/multi-kernel.md phase 3): kernels.json profiles are
// parsed FRESH at every consult and validated hard — a malformed entry is DROPPED with a loud error,
// never half-applied — and specEnv is the whole per-kernel isolation story (state root, Claude config
// dir, postal port ride the child env). fileStamp backs the --refresh stale-manager
// detection (the user 2026-07-24: a long-lived manager respawned kernels on start-time defaults the
// disk had moved past, with everything reporting success). The second half pins one kernel per state
// root at the source (2026-10-02): the manager never starts two kernels on one resolved state root (main
// first; a running kernel keeps the root it was started on until it stops, wherever its entry sits in
// kernels.json; among the profiles not running, the file's order), on any road (the boot pass, the crash
// respawn, a restart, /ensure), and says each conflict once.
// Those cases run a real manager with HOME and XDG_STATE_HOME floored under a private world (the harness
// comment below says how, and how the stand-in kernel refuses a root outside it).
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
// port no profile names, could take the primary's root and lock the primary out, and of two profiles on
// one root the one that lost the lock crash-looped on it. The manager refuses a kernel whose root another
// kernel holds before it starts (bin/romp-manager rootConflict), keyed on the root each would resolve.
//
// The harness: a real manager in a private world (tests/manager-token.test.js's shape), its own state root
// holding a serve token, ports from this file's block (tests/manager-ports.js), and a stand-in kernel that
// records each start in a log and takes the kernel's instance lock as the kernel does: an exclusive flock
// on kernel.lock under the root kernel/judge.py would resolve from its environment, exit 75 when another
// process holds it. Python for the flock (node has none); FAKE_LATE_PORT makes one port reach its lock
// point late, FAKE_CRASH_PORT and FAKE_CRASHES make one port's first starts exit soon after they serve.
// HOME and XDG_STATE_HOME are floored under the world for the manager and every stand-in it starts (HOME
// to <world>/home, XDG_STATE_HOME to <world>/home/xdg-state), so a manager that handed a kernel no state
// root of its own resolves one inside the world, never the runner's own. Behind that floor the stand-in
// checks the root it resolved: one that is not under the world (FAKE_WORLD) makes it say so on stderr and
// exit 2 before it opens anything, so the stand-in makes no lock file, log row or directory there. The
// manager itself still writes under a profile's stateDir as written: its notes in restart-audit.jsonl
// (auditSigterm before each stop or restart it signals, auditNote for a folded or trailing restart) create
// that directory when it is missing, so a profile naming a root outside the world gets that file there
// when its kernel is stopped or restarted (the harness case below removes its outside directory itself).
// A pid is signalled only once it is checked to be this world's stand-in (h.standIn: its command line
// names the world, read from /proc where there is one and from ps where there is not, as on macOS).

const REGISTRY_TOKEN = 'zq9-registry-token-zq9';   // synthetic
// every refusal names the other road's remedy too: a kernel started by hand is outside the manager's view
const BY_HAND_REMEDY = 'A kernel started by hand, which the manager does not see, needs its own ROMP_STATE_DIR.';
const PY3 = (() => {
  const r = spawnSync('python3', ['-c', 'import sys; print(sys.executable)'], { encoding: 'utf8' });
  return r.status === 0 ? r.stdout.trim() : '';
})();
const FAKE_KERNEL = String.raw`
import fcntl, json, os, sys, time
env = os.environ
root = env.get("ROMP_STATE_DIR") or os.path.join(env.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state"), "romp")
if not env.get("FAKE_WORLD") or not os.path.realpath(root).startswith(os.path.realpath(env["FAKE_WORLD"]) + os.sep):
    sys.stderr.write("fake kernel: state root %r is outside the test's world %r; exit 2, nothing opened\n" % (root, env.get("FAKE_WORLD")))
    sys.exit(2)
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
  const bin = path.join(dir, 'bin'), state = path.join(dir, 'state'), home = path.join(dir, 'home');
  for (const d of [bin, state, home]) fs.mkdirSync(d);
  fs.writeFileSync(path.join(state, 'serve-token'), REGISTRY_TOKEN + '\n', { mode: 0o600 });
  const kernelPy = path.join(dir, 'fake_kernel.py');
  fs.writeFileSync(kernelPy, FAKE_KERNEL);
  const serve = path.join(dir, 'fake-serve');
  fs.writeFileSync(serve, `#!/bin/sh\nexec "${PY3}" -I "${kernelPy}" "$@"\n`, { mode: 0o755 });
  const h = { dir, state, home, log: '', starts: path.join(dir, 'starts.jsonl'), mgr: null, exited: null,
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
  // Whether `pid` is a process of this world, still running: its command line names the world's directory (a stand-in
  // runs <world>/fake_kernel.py). Read from /proc/<pid>/cmdline where there is a /proc, else from `ps -o command=`, which
  // a host without /proc has (the manager leg's macOS cells); a pid neither can read is not this world's. h.procRoot is
  // /proc; a test points it at a path that does not exist to take the road a host without /proc takes.
  h.procRoot = '/proc';
  h.standIn = (pid) => {
    let cmd = null;
    if (fs.existsSync(path.join(h.procRoot, 'self'))) {
      try { cmd = fs.readFileSync(path.join(h.procRoot, String(pid), 'cmdline'), 'utf8'); } catch (e) { cmd = null; }
    } else {
      const r = spawnSync('ps', ['-ww', '-o', 'command=', '-p', String(pid)], { encoding: 'utf8' });
      cmd = r.status === 0 ? r.stdout : null;
    }
    return cmd !== null && cmd.includes(dir);
  };
  // the lines saying kernel `id` was not started (as their subject: a refusal of another kernel names `id` as the holder)
  h.refusals = (id) => h.log.split('\n').filter((l) => new RegExp(`^\\[romp-manager\\] kernel '${id}' \\(port \\d+\\) is not started: `).test(l));
  h.start = async (extra) => {
    const env = Object.assign({}, process.env, {
      PATH: bin, ROMP_CLI_SCOPE: '0', HOME: home, XDG_STATE_HOME: path.join(home, 'xdg-state'),
      ROMP_STATE_DIR: state, ROMP_MANAGER_PORT: String(h.port), ROMP_SERVE_PORT: String(h.mainPort),
      ROMP_SERVE_BIN: serve, ROMP_SHUTDOWN_GRACE_MS: '500', FAKE_KERNEL_LOG: h.starts, FAKE_WORLD: dir,
    }, extra || {});
    for (const k of ['ROMP_SUPERVISED', 'ROMP_SERVE_TOKEN', 'ROMP_KERNEL_PORT']) delete env[k];
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
      if (h.standIn(pid)) { try { process.kill(pid, 'SIGKILL'); } catch (e) { /* gone */ } }
    }
    fs.rmSync(dir, { recursive: true, force: true });
  };
  return h;
}

test('a profile with no stateDir is not started, and the one line naming it and both remedies is said once across the primary\'s two respawns and two /ensure retries', async () => {
  const h = await world();
  try {
    const aux = await freePort(__filename);
    h.writeKernels([{ id: 'aux', port: aux }]);
    // main's first two starts exit soon after serving, so the manager respawns it twice: each respawn re-reads
    // kernels.json, and neither says the profile's refusal again (the refused profile itself has no record, so no
    // respawn of its own)
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
    assert.equal(lines.length, 1, `one line for the profile across the boot pass, the primary's two respawns and two /ensure retries:\n${h.log}`);
    assert.match(lines[0], new RegExp(`kernel 'aux' \\(port ${aux}\\)`), 'the line names the profile');
    assert.match(lines[0], /has no stateDir/);
    assert.match(lines[0], /Give the profile a stateDir no other kernel uses in .*kernels\.json/, 'the line names the profile\'s remedy');
    assert.ok(lines[0].includes(BY_HAND_REMEDY), `the line names the remedy for a kernel started by hand: ${lines[0]}`);
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
      assert.match(lines[0], /Give the profile a stateDir no other kernel uses/);
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
    for (const [port, id, remedy] of [[bare, `k${bare}`, `Add a profile for port ${bare} with a stateDir no other kernel uses`],
                                      [prof, 'nodir', 'Give the profile a stateDir no other kernel uses']]) {
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
        assert.ok(body.error.includes(BY_HAND_REMEDY), `the body names the remedy for a kernel started by hand: ${body.error}`);
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

test('a running profile whose entry loses its stateDir and then exits unasked (a crash, no restart request) is not respawned onto the primary\'s root, and the refusal is said once after the exit line', async () => {
  const h = await world();
  try {
    const aux = await freePort(__filename);
    const own = path.join(h.dir, 'aux-state');
    h.writeKernels([{ id: 'aux', port: aux, stateDir: own }]);
    await h.start();
    await h.until(() => h.at(aux, 'serving').length === 1, 10000, 'the profile serves on its own root');
    const pid = h.at(aux, 'serving')[0].pid;
    // the pid is the one the manager spawned for the profile, by the manager's own spawn line (fake-serve execs the
    // stand-in, so the child's pid is the stand-in's), and a process of this world still running: killed only then
    assert.ok(h.log.includes(`kernel 'aux' → :${aux} (pid ${pid})`), `the serving row's pid is not the profile's spawn:\n${h.log}`);
    assert.ok(h.standIn(pid), 'the serving row\'s pid is this world\'s stand-in, still running');
    h.writeKernels([{ id: 'aux', port: aux }]);            // the edit lands on the kernel's next start (the spawn-time re-read)
    process.kill(pid, 'SIGKILL');                          // the crash road: nothing asked for this exit
    await h.until(() => h.log.includes(`kernel 'aux' (pid ${pid}) exited without a restart request`), 10000, 'the manager did not log the exit');
    await h.until(() => h.refusals('aux').length === 1, 5000, 'the crash respawn was not refused, or not said');
    const exited = h.log.indexOf(`kernel 'aux' (pid ${pid}) exited`);
    assert.ok(h.log.indexOf(h.refusals('aux')[0]) > exited, 'the refusal follows the exit line');
    assert.match(h.refusals('aux')[0], /its kernels\.json profile has no stateDir, so it would run on the primary kernel's state root/);
    await h.sleep(2500);                                    // past the crash backoff (1 s after a quick exit): a respawn would be here
    assert.equal(h.at(aux, 'start').length, 1, `the profile was started again after its unasked exit:\n${JSON.stringify(h.rows())}`);
    assert.equal(h.refusals('aux').length, 1, h.log);
    assert.deepEqual((await h.kernels()).map((k) => k.id), ['main'], '/status still lists the refused profile');
    assert.equal(h.at(h.mainPort, 'start').length, 1, 'main untouched');
  } finally { await h.cleanup(); }
});

test('two profiles on one state root, written literally, through a symlink or with a trailing slash: the first runs, and each later one is refused once, named in its line and in /ensure\'s 409, and never started, nor once the first stops', async () => {
  const h = await world();
  try {
    const [first, literal, viaLink, slashed] = [await freePort(__filename), await freePort(__filename),
                                                await freePort(__filename), await freePort(__filename)];
    const shared = path.join(h.dir, 'shared-state');
    fs.mkdirSync(shared);
    const link = path.join(h.dir, 'shared-link');
    fs.symlinkSync(shared, link);
    const later = [['literal', literal, shared], ['linked', viaLink, link], ['slashed', slashed, shared + '/']];
    h.writeKernels([{ id: 'first', port: first, stateDir: shared }].concat(later.map(([id, port, dir]) => ({ id, port, stateDir: dir }))));
    await h.start();
    await h.until(() => h.at(first, 'serving').length === 1, 10000, 'the first profile on the root serves');
    assert.equal(h.at(first, 'serving')[0].root, fs.realpathSync(shared));
    for (const [id, port, asWritten] of later) {
      for (let i = 0; i < 2; i++) {
        const r = await h.req(`/ensure?port=${port}`, 'POST');
        assert.equal(r.code, 409, `/ensure for ${id}: ${r.body}`);
        const body = JSON.parse(r.body);
        assert.equal(body.id, id);
        // the boot pass started 'first' before any later profile, and it runs: the refusal names it as running
        assert.ok(body.error.includes(`kernel '${id}' (port ${port}) is not started: its kernels.json profile's stateDir ` +
                                      `${JSON.stringify(asWritten)} resolves to the state root ${fs.realpathSync(shared)} of kernel 'first' ` +
                                      `(port ${first}), which is running and keeps that root until it stops`), body.error);
        assert.ok(body.error.includes('Give the profile a stateDir no other kernel uses'), body.error);
        assert.ok(body.error.includes(BY_HAND_REMEDY), body.error);
        const lines = h.refusals(id);
        assert.equal(lines.length, 1, `one line for ${id} across the boot pass and ${i + 1} /ensure request(s):\n${h.log}`);
        assert.ok(lines[0].endsWith(body.error), `the line and the 409 say the same:\n${lines[0]}\n${body.error}`);
      }
    }
    await h.sleep(2500);                                    // a later profile started anyway would crash-loop on the lock by here
    for (const [id, port] of later) assert.deepEqual(h.at(port), [], `${id} was started: ${JSON.stringify(h.rows())}`);
    assert.equal(h.at(first, 'start').length, 1, 'the first profile was started once');
    assert.equal(h.at(h.mainPort, 'start').length, 1, 'main untouched');
    assert.deepEqual((await h.kernels()).map((k) => k.id).sort(), ['first', 'main']);
    // 'first' stopped: no kernel holds the root now, and among the profiles not running the file's order decides, so
    // a later one is still refused, the refusal now naming 'first' as the profile before it; the same conflict (the
    // kernel, the holder, the root, the reason), so no new line
    assert.equal((await h.req('/stop?kernel=first', 'POST')).code, 200);
    await h.until(() => h.log.includes(`kernel 'first' stopped`), 10000, 'the first profile did not stop');
    const r = await h.req(`/ensure?port=${literal}`, 'POST');
    assert.equal(r.code, 409, r.body);
    assert.ok(JSON.parse(r.body).error.includes(`of kernel 'first' (port ${first}), whose profile comes before it in kernels.json`), r.body);
    assert.equal(h.refusals('literal').length, 1, h.log);
    assert.deepEqual(h.at(literal), [], 'the later profile was started once the first stopped');
  } finally { await h.cleanup(); }
});

test('a running kernel whose entry left kernels.json still holds its root: a profile added on that root is refused, and the running kernel is respawned there', async () => {
  const h = await world();
  try {
    const [old, added] = [await freePort(__filename), await freePort(__filename)];
    const own = path.join(h.dir, 'old-state');
    h.writeKernels([{ id: 'old', port: old, stateDir: own }]);
    await h.start();
    await h.until(() => h.at(old, 'serving').length === 1, 10000, 'the profile serves on its own root');
    h.writeKernels([{ id: 'added', port: added, stateDir: own }]);   // 'old' leaves the file; the registry keeps its spec
    const r = await h.req(`/ensure?port=${added}`, 'POST');
    assert.equal(r.code, 409, r.body);
    const body = JSON.parse(r.body);
    assert.ok(body.error.includes(`kernel 'added' (port ${added}) is not started: its kernels.json profile's stateDir ` +
                                  `${JSON.stringify(own)} resolves to the state root ${fs.realpathSync(own)} of kernel 'old' (port ${old}), ` +
                                  'which is running from a profile kernels.json no longer holds'), body.error);
    await h.sleep(1500);                                    // a profile started on the held root would crash-loop on the lock by here
    assert.deepEqual(h.at(added), [], `the added profile was started on the running kernel's root: ${JSON.stringify(h.rows())}`);
    // the running kernel counts as started before the added profile, so its own respawn is not refused
    assert.equal((await h.req('/restart?kernel=old', 'POST')).code, 200);
    await h.until(() => h.at(old, 'serving').length === 2, 10000, 'the kernel whose entry left the file was not respawned');
    assert.equal(h.at(old, 'serving')[1].root, fs.realpathSync(own));
    assert.equal(h.refusals('old').length, 0, h.log);
    assert.equal(h.refusals('added').length, 1, h.log);
    assert.deepEqual(h.at(added), []);
    assert.deepEqual((await h.kernels()).map((k) => k.id).sort(), ['main', 'old']);
  } finally { await h.cleanup(); }
});

// A running kernel keeps the root it was started on until it stops, wherever its entry sits in kernels.json. The
// roads below start a profile listed BEFORE a running profile on that running profile's root: an /ensure for a profile
// added ahead of it, and a restart and an unasked exit of an earlier profile edited onto it; and a profile on the old
// root of a running kernel whose entry now names another stateDir. Each is refused once, by a line naming the running
// holder, is never started (so never crash-loops on the kernel lock), and the running holder keeps serving, through
// its own restart and crash respawn too: a running kernel keeps its root ahead of a profile that is not running.
const RUNNING_HOLDER = 'which is running and keeps that root until it stops';

test('a profile added ahead of a running profile, on its root, is refused when /ensure asks for it: 409 naming the running profile, one line, never started, and the running profile keeps serving', async () => {
  const h = await world();
  try {
    const [early, late] = [await freePort(__filename), await freePort(__filename)];
    const shared = path.join(h.dir, 'shared-state');
    h.writeKernels([{ id: 'late', port: late, stateDir: shared }]);
    await h.start();
    await h.until(() => h.at(late, 'serving').length === 1, 10000, 'the running profile serves');
    h.writeKernels([{ id: 'early', port: early, stateDir: shared }, { id: 'late', port: late, stateDir: shared }]);
    for (let i = 0; i < 2; i++) {                           // the extension's retry
      const r = await h.req(`/ensure?port=${early}`, 'POST');
      assert.equal(r.code, 409, `/ensure for the profile added ahead of the running one: ${r.body}`);
      const body = JSON.parse(r.body);
      assert.equal(body.id, 'early');
      assert.ok(body.error.includes(`kernel 'early' (port ${early}) is not started: its kernels.json profile's stateDir ` +
                                    `${JSON.stringify(shared)} resolves to the state root ${fs.realpathSync(shared)} of kernel 'late' ` +
                                    `(port ${late}), ${RUNNING_HOLDER}`), body.error);
      assert.ok(body.error.includes('Give the profile a stateDir no other kernel uses'), body.error);
    }
    await h.sleep(2500);                                    // a profile started on the held root would crash-loop on the lock by here
    assert.deepEqual(h.at(early), [], `the profile added ahead was started on the running profile's root: ${JSON.stringify(h.rows())}`);
    assert.doesNotMatch(h.log, new RegExp(`kernel 'early' → :${early}`), 'the manager spawned the profile added ahead');
    assert.equal(h.refusals('early').length, 1, h.log);
    assert.deepEqual(h.at(late).map((r) => r.event), ['start', 'serving'], 'the running profile was disturbed');
    assert.equal(h.refusals('late').length, 0, h.log);
    assert.deepEqual((await h.kernels()).map((k) => k.id).sort(), ['late', 'main']);
  } finally { await h.cleanup(); }
});

test('an earlier running profile edited onto a later running profile\'s root is refused at its restart, once and after its exit line, naming the running profile, and never started there; the running profile keeps its root through restart-all, and the refused one stays down', async () => {
  const h = await world();
  try {
    const [pa, pb] = [await freePort(__filename), await freePort(__filename)];
    const ra = path.join(h.dir, 'a-state'), rb = path.join(h.dir, 'b-state');
    h.writeKernels([{ id: 'a', port: pa, stateDir: ra }, { id: 'b', port: pb, stateDir: rb }]);
    await h.start();
    await h.until(() => h.at(pa, 'serving').length === 1 && h.at(pb, 'serving').length === 1, 10000, 'both profiles serve');
    h.writeKernels([{ id: 'a', port: pa, stateDir: rb }, { id: 'b', port: pb, stateDir: rb }]);   // lands at a's next start
    assert.equal((await h.req('/restart?kernel=a', 'POST')).code, 200);
    await h.until(() => h.refusals('a').length === 1, 10000, 'the restart of the edited profile was not refused, or not said');
    const exited = h.log.indexOf(`kernel 'a' exited`);
    assert.ok(exited >= 0 && h.log.indexOf(h.refusals('a')[0]) > exited, 'the refusal follows the exit line');
    assert.ok(h.refusals('a')[0].includes(`resolves to the state root ${fs.realpathSync(rb)} of kernel 'b' (port ${pb}), ${RUNNING_HOLDER}`),
              h.refusals('a')[0]);
    await h.sleep(2500);                                    // past the crash backoff: a respawn onto b's root would be here
    const rowsOf = (port) => h.at(port).map((r) => `${r.event}@${path.basename(r.root)}`);
    assert.deepEqual(rowsOf(pa), ['start@a-state', 'serving@a-state'], 'the edited profile was started again');
    assert.deepEqual((await h.kernels()).map((k) => k.id).sort(), ['b', 'main'], '/status still lists the refused profile');
    // restart-all restarts every kernel the manager runs: b comes back on the root it holds, ahead of a (listed before
    // it, but not running), so the root does not change hands, and a, which has no record, is not started
    const all = await h.req('/restart-all', 'POST');
    assert.equal(all.code, 200, all.body);
    await h.until(() => h.at(pb, 'serving').length === 2 || h.refusals('b').length > 0, 10000, 'b was not restarted by restart-all');
    await h.sleep(1500);
    assert.equal(h.refusals('b').length, 0, `the running profile's restart was refused:\n${h.log}`);
    assert.deepEqual(rowsOf(pb), ['start@b-state', 'serving@b-state', 'start@b-state', 'serving@b-state']);
    assert.deepEqual(rowsOf(pa), ['start@a-state', 'serving@a-state'], 'restart-all started the refused profile');
    assert.equal(h.refusals('a').length, 1, h.log);
    assert.deepEqual((await h.kernels()).map((k) => k.id).sort(), ['b', 'main']);
  } finally { await h.cleanup(); }
});

test('an earlier running profile edited onto a later running profile\'s root and then killed (an unasked exit) is not respawned there, the one line after the exit line naming the running profile; the running profile\'s own crash respawn keeps its root', async () => {
  const h = await world();
  try {
    const [pa, pb] = [await freePort(__filename), await freePort(__filename)];
    const ra = path.join(h.dir, 'a-state'), rb = path.join(h.dir, 'b-state');
    h.writeKernels([{ id: 'a', port: pa, stateDir: ra }, { id: 'b', port: pb, stateDir: rb }]);
    await h.start();
    await h.until(() => h.at(pa, 'serving').length === 1 && h.at(pb, 'serving').length === 1, 10000, 'both profiles serve');
    h.writeKernels([{ id: 'a', port: pa, stateDir: rb }, { id: 'b', port: pb, stateDir: rb }]);   // lands at a's next start
    const pid = h.at(pa, 'serving')[0].pid;
    assert.ok(h.log.includes(`kernel 'a' → :${pa} (pid ${pid})`) && h.standIn(pid), 'the pid is the edited profile\'s stand-in');
    process.kill(pid, 'SIGKILL');                          // the crash road: nothing asked for this exit
    await h.until(() => h.log.includes(`kernel 'a' (pid ${pid}) exited without a restart request`), 10000, 'the manager did not log the exit');
    await h.until(() => h.refusals('a').length === 1, 5000, 'the crash respawn was not refused, or not said');
    assert.ok(h.log.indexOf(h.refusals('a')[0]) > h.log.indexOf(`kernel 'a' (pid ${pid}) exited`), 'the refusal follows the exit line');
    assert.ok(h.refusals('a')[0].includes(`resolves to the state root ${fs.realpathSync(rb)} of kernel 'b' (port ${pb}), ${RUNNING_HOLDER}`),
              h.refusals('a')[0]);
    await h.sleep(2500);                                    // past the crash backoff: a respawn onto b's root would be here
    const rowsOf = (port) => h.at(port).map((r) => `${r.event}@${path.basename(r.root)}`);
    assert.deepEqual(rowsOf(pa), ['start@a-state', 'serving@a-state'], 'the edited profile was started again');
    // b's crash: its respawn is of the kernel holding the root, so a (listed before it, not running) does not take it
    const pidB = h.at(pb, 'serving')[0].pid;
    assert.ok(h.log.includes(`kernel 'b' → :${pb} (pid ${pidB})`) && h.standIn(pidB), 'the pid is the running profile\'s stand-in');
    process.kill(pidB, 'SIGKILL');
    await h.until(() => h.at(pb, 'serving').length === 2 || h.refusals('b').length > 0, 10000, 'the running profile was not respawned');
    await h.sleep(500);
    assert.equal(h.refusals('b').length, 0, `the running profile's crash respawn was refused:\n${h.log}`);
    assert.deepEqual(rowsOf(pb), ['start@b-state', 'serving@b-state', 'start@b-state', 'serving@b-state']);
    assert.deepEqual(rowsOf(pa), ['start@a-state', 'serving@a-state']);
    assert.equal(h.refusals('a').length, 1, h.log);
    assert.deepEqual((await h.kernels()).map((k) => k.id).sort(), ['b', 'main']);
  } finally { await h.cleanup(); }
});

test('a running kernel whose entry now names another stateDir keeps the root it was started on: a profile on that root is refused naming it, and starts there once the kernel\'s restart has moved it', async () => {
  const h = await world();
  try {
    const [po, pp] = [await freePort(__filename), await freePort(__filename)];
    const r1 = path.join(h.dir, 'r1-state'), r3 = path.join(h.dir, 'r3-state');
    h.writeKernels([{ id: 'o', port: po, stateDir: r1 }]);
    await h.start();
    await h.until(() => h.at(po, 'serving').length === 1, 10000, 'the profile serves on its first root');
    // o's entry moves to r3, which lands at o's next start; p, listed first, names r1, the root o still runs on
    h.writeKernels([{ id: 'p', port: pp, stateDir: r1 }, { id: 'o', port: po, stateDir: r3 }]);
    for (let i = 0; i < 2; i++) {
      const r = await h.req(`/ensure?port=${pp}`, 'POST');
      assert.equal(r.code, 409, r.body);
      assert.ok(JSON.parse(r.body).error.includes(`resolves to the state root ${fs.realpathSync(r1)} of kernel 'o' (port ${po}), which is ` +
                                                  'running from the stateDir its kernels.json profile named when it started and keeps that ' +
                                                  'root until it stops'), r.body);
    }
    await h.sleep(1500);                                    // a profile started on the held root would crash-loop on the lock by here
    assert.deepEqual(h.at(pp), [], `the profile was started on the root the running kernel holds: ${JSON.stringify(h.rows())}`);
    assert.equal(h.refusals('p').length, 1, h.log);
    // o's restart takes the root its entry names now; r1 is free, and /ensure starts p there
    assert.equal((await h.req('/restart?kernel=o', 'POST')).code, 200);
    await h.until(() => h.at(po, 'serving').length === 2 || h.refusals('o').length > 0, 10000, 'the moved profile was not restarted');
    assert.equal(h.refusals('o').length, 0, h.log);
    assert.equal(h.at(po, 'serving')[1].root, fs.realpathSync(r3), 'the restart did not move the kernel to the root its entry names');
    const e = await h.req(`/ensure?port=${pp}`, 'POST');
    assert.equal(e.code, 200, e.body);
    assert.equal(JSON.parse(e.body).spawned, true, e.body);
    await h.until(() => h.at(pp, 'serving').length === 1, 10000, 'the profile does not serve on the freed root');
    assert.equal(h.at(pp, 'serving')[0].root, fs.realpathSync(r1));
    assert.deepEqual(h.rows().filter((r) => r.event === 'refused'), [], 'a kernel met another on its root');
    assert.equal(h.refusals('p').length, 1, h.log);
    assert.deepEqual((await h.kernels()).map((k) => k.id).sort(), ['main', 'o', 'p']);
  } finally { await h.cleanup(); }
});

// A running kernel keeps the root it runs on, not the root its entry names since. Two roads where the two differ: a
// running profile whose entry moved onto the root of an earlier profile that is not running is a new start there at
// its restart, where the file's order applies, so it is refused naming that profile (its own record keeps only the
// root it runs on); and the root a running earlier profile's entry moved to, which that kernel does not run on yet,
// is no running kernel's, so a later profile on it starts, and the earlier kernel's restart onto it is refused naming
// the later one as running.
test('a running profile restarted onto the root of an earlier profile that is not running is refused naming that profile, is never started there, and the earlier profile then starts on its root', async () => {
  const h = await world();
  try {
    const [px, py] = [await freePort(__filename), await freePort(__filename)];
    const rx = path.join(h.dir, 'x-state'), ry = path.join(h.dir, 'y-state');
    h.writeKernels([{ id: 'x', port: px, stateDir: rx }, { id: 'y', port: py, stateDir: ry }]);
    await h.start();
    await h.until(() => h.at(px, 'serving').length === 1 && h.at(py, 'serving').length === 1, 10000, 'both profiles serve');
    assert.equal((await h.req('/stop?kernel=x', 'POST')).code, 200);
    await h.until(() => h.log.includes("kernel 'x' stopped"), 10000, 'x did not stop');
    // y's entry moves onto x's root, which lands at y's next start; x, listed before it, is not running
    h.writeKernels([{ id: 'x', port: px, stateDir: rx }, { id: 'y', port: py, stateDir: rx }]);
    assert.equal((await h.req('/restart?kernel=y', 'POST')).code, 200);
    await h.until(() => h.refusals('y').length > 0 || h.at(py, 'serving').length === 2, 10000, 'y was neither refused nor restarted');
    await h.sleep(1500);                                    // past the crash backoff: a respawn onto x's root would be here
    assert.equal(h.refusals('y').length, 1, `y's restart onto the earlier profile's root was not refused, or not said once:\n${h.log}`);
    assert.ok(h.refusals('y')[0].includes(`its kernels.json profile's stateDir ${JSON.stringify(rx)} resolves to the state root ` +
                                          `${fs.realpathSync(rx)} of kernel 'x' (port ${px}), whose profile comes before it in kernels.json`),
              h.refusals('y')[0]);
    const rowsOf = (port) => h.at(port).map((r) => `${r.event}@${path.basename(r.root)}`);
    assert.deepEqual(rowsOf(py), ['start@y-state', 'serving@y-state'], 'y was started again');
    assert.deepEqual((await h.kernels()).map((k) => k.id).sort(), ['main'], '/status still lists the refused profile');
    // the root is x's by the file's order: /ensure starts x there
    const e = await h.req(`/ensure?port=${px}`, 'POST');
    assert.equal(e.code, 200, e.body);
    assert.equal(JSON.parse(e.body).spawned, true, e.body);
    await h.until(() => h.at(px, 'serving').length === 2, 10000, 'x does not serve on its root again');
    assert.equal(h.at(px, 'serving')[1].root, fs.realpathSync(rx));
    assert.deepEqual(h.rows().filter((r) => r.event === 'refused'), [], 'a kernel met another on its root');
    assert.equal(h.refusals('y').length, 1, h.log);
  } finally { await h.cleanup(); }
});

test('a later profile on the root a running earlier profile\'s entry moved to starts while that kernel still runs on its old root, and the earlier kernel\'s restart onto it is then refused naming the later one as running', async () => {
  const h = await world();
  try {
    const [pe, ps] = [await freePort(__filename), await freePort(__filename)];
    const r1 = path.join(h.dir, 'r1-state'), r2 = path.join(h.dir, 'r2-state');
    h.writeKernels([{ id: 'e', port: pe, stateDir: r1 }]);
    await h.start();
    await h.until(() => h.at(pe, 'serving').length === 1, 10000, 'e serves on its first root');
    // e's entry moves to r2, which lands at e's next start; s, listed after it, names r2, which no kernel runs on
    h.writeKernels([{ id: 'e', port: pe, stateDir: r2 }, { id: 's', port: ps, stateDir: r2 }]);
    const r = await h.req(`/ensure?port=${ps}`, 'POST');
    assert.equal(r.code, 200, `the running earlier profile was counted at the root its entry names, not the one it runs on: ${r.body}`);
    assert.equal(JSON.parse(r.body).spawned, true, r.body);
    await h.until(() => h.at(ps, 'serving').length === 1, 10000, 's does not serve');
    assert.equal(h.at(ps, 'serving')[0].root, fs.realpathSync(r2));
    assert.equal(h.refusals('s').length, 0, h.log);
    // e's restart is a new start on r2, which s now holds as a running kernel
    assert.equal((await h.req('/restart?kernel=e', 'POST')).code, 200);
    await h.until(() => h.refusals('e').length > 0 || h.at(pe, 'serving').length === 2, 10000, 'e was neither refused nor restarted');
    await h.sleep(500);
    assert.equal(h.refusals('e').length, 1, h.log);
    assert.ok(h.refusals('e')[0].includes(`resolves to the state root ${fs.realpathSync(r2)} of kernel 's' (port ${ps}), ${RUNNING_HOLDER}`),
              h.refusals('e')[0]);
    assert.deepEqual(h.at(pe).map((x) => `${x.event}@${path.basename(x.root)}`), ['start@r1-state', 'serving@r1-state'], 'e was started again');
    assert.deepEqual(h.rows().filter((x) => x.event === 'refused'), [], 'a kernel met another on its root');
    assert.deepEqual((await h.kernels()).map((k) => k.id).sort(), ['main', 's']);
  } finally { await h.cleanup(); }
});

test('kernels.json\'s errors are said once per text per manager life, across the boot pass and refused /ensure retries, and /ensure for a dropped entry\'s port says that entry was dropped and why', async () => {
  const h = await world();
  try {
    const [bad, bare, later] = [await freePort(__filename), await freePort(__filename), await freePort(__filename)];
    h.writeKernels([{ id: 'aux', port: bad, stateDir: 'relative/aux-state' }]);   // a relative stateDir: the entry is dropped
    await h.start();
    const dropLines = () => h.log.split('\n').filter((l) => l.includes('kernels.json: dropped entry'));
    assert.equal(dropLines().length, 1, `the boot pass says the dropped entry once, not once more per spec it spawns:\n${h.log}`);
    for (let i = 0; i < 5; i++) {
      for (const port of [bad, bare]) assert.equal((await h.req(`/ensure?port=${port}`, 'POST')).code, 409, `/ensure for ${port}`);
    }
    assert.equal(dropLines().length, 1, `ten refused /ensure requests said the dropped entry again:\n${h.log}`);
    const r = await h.req(`/ensure?port=${bad}`, 'POST');
    assert.equal(r.code, 409, r.body);
    const body = JSON.parse(r.body);
    assert.equal(body.id, `k${bad}`);
    assert.ok(body.error.includes(`kernel 'k${bad}' (port ${bad}) is not started: kernels.json's entry for port ${bad} was dropped ` +
                                  '(stateDir is malformed), so no profile names the port and it would run on the primary kernel\'s state root'), body.error);
    assert.ok(body.error.includes(`Repair that entry in ${path.join(h.state, 'kernels.json')}, with a stateDir no other kernel uses.`), body.error);
    assert.ok(!body.error.includes(`no kernels.json profile names port ${bad}`), body.error);
    const plain = JSON.parse((await h.req(`/ensure?port=${bare}`, 'POST')).body);   // a port no entry names keeps the plain account
    assert.ok(plain.error.includes(`no kernels.json profile names port ${bare}, so it would run on`), plain.error);
    // a new fault in the file is a new text: said once, at the first read that finds it
    h.writeKernels([{ id: 'aux', port: bad, stateDir: 'relative/aux-state' }, { id: 'BAD ID', port: later }]);
    for (let i = 0; i < 3; i++) assert.equal((await h.req(`/ensure?port=${bare}`, 'POST')).code, 409);
    assert.equal(dropLines().length, 2, `the new fault said once, the old one not again:\n${h.log}`);
    assert.equal(dropLines().filter((l) => l.includes('"BAD ID"')).length, 1, h.log);
    assert.deepEqual(h.rows().filter((row) => row.port !== h.mainPort), [], 'a kernel was started for a refused port');
  } finally { await h.cleanup(); }
});

test('/ensure for the port of a dropped main entry says the main entry was dropped and why, and that its port needs repair, not a stateDir it has no field for', async () => {
  const h = await world();
  try {
    h.writeKernels([{ id: 'main', port: 80 }]);            // below 1024: the main override is dropped, the primary stays on its port
    await h.start();
    const r = await h.req('/ensure?port=80', 'POST');
    assert.equal(r.code, 409, r.body);
    const body = JSON.parse(r.body);
    assert.equal(body.id, 'k80');
    assert.equal(body.primaryPort, h.mainPort);
    assert.ok(body.error.includes("kernel 'k80' (port 80) is not started: kernels.json's main entry for port 80 was dropped " +
                                  '(main override needs a free port in [1024,65535]), so the primary kernel is not moved there and it ' +
                                  'would run on the primary kernel\'s state root'), body.error);
    assert.ok(body.error.includes(`Repair the main entry's port in ${path.join(h.state, 'kernels.json')}.`), body.error);
    assert.ok(!body.error.includes('stateDir'), `a main entry carries a port only, so a stateDir is no part of its repair: ${body.error}`);
    assert.ok(body.error.includes(BY_HAND_REMEDY), body.error);
    assert.deepEqual(h.rows().filter((row) => row.port !== h.mainPort), [], 'a kernel was started for the refused port');
  } finally { await h.cleanup(); }
});

test('the refusal and the 409\'s primaryPort give the running primary\'s port, not a main port edited into kernels.json since it started, and the configured port once main is stopped', async () => {
  const h = await world();
  try {
    const [bare, newMain] = [await freePort(__filename), await freePort(__filename)];
    await h.start();
    h.writeKernels([{ id: 'main', port: newMain }]);       // lands on main's next start; the primary still serves h.mainPort
    let r = await h.req(`/ensure?port=${bare}`, 'POST');
    assert.equal(r.code, 409, r.body);
    let body = JSON.parse(r.body);
    assert.equal(body.primaryPort, h.mainPort, body.error);
    assert.ok(body.error.includes(`which the primary kernel on port ${h.mainPort} serves,`), body.error);
    assert.ok(!body.error.includes(String(newMain)), body.error);
    assert.deepEqual((await h.kernels()).map((k) => `${k.id}:${k.port}`), [`main:${h.mainPort}`]);
    // main stopped: no primary runs, so the port a start would give it is the configured one
    assert.equal((await h.req('/stop?kernel=main', 'POST')).code, 200);
    await h.until(() => h.log.includes(`kernel 'main' stopped`), 10000, 'main did not stop');
    r = await h.req(`/ensure?port=${bare}`, 'POST');
    assert.equal(r.code, 409, r.body);
    body = JSON.parse(r.body);
    assert.equal(body.primaryPort, newMain, body.error);
    assert.ok(body.error.includes(`which the primary kernel on port ${newMain} is configured to serve,`), body.error);
    assert.deepEqual(h.rows().filter((row) => row.port !== h.mainPort), [], 'a kernel was started for the refused port');
  } finally { await h.cleanup(); }
});

test('one conflict is said once across the primary stopping, coming back and moving port: the line is keyed on the conflict, not on the text, which names the primary\'s port and whether it runs', async () => {
  const h = await world();
  try {
    const [nodir, newMain] = [await freePort(__filename), await freePort(__filename)];
    h.writeKernels([{ id: 'nodir', port: nodir }]);
    await h.start();
    const ensure = async (says) => {
      const r = await h.req(`/ensure?port=${nodir}`, 'POST');
      assert.equal(r.code, 409, r.body);
      assert.ok(JSON.parse(r.body).error.includes(says), `the 409 does not say "${says}": ${r.body}`);
    };
    await ensure(`which the primary kernel on port ${h.mainPort} serves,`);
    assert.equal((await h.req('/stop?kernel=main', 'POST')).code, 200);
    await h.until(() => h.log.includes(`kernel 'main' stopped`), 10000, 'main did not stop');
    await ensure(`which the primary kernel on port ${h.mainPort} is configured to serve,`);
    assert.equal((await h.req(`/ensure?port=${h.mainPort}`, 'POST')).code, 200);   // main back
    await h.until(() => h.at(h.mainPort, 'serving').length === 2, 10000, 'main did not come back');
    await ensure(`which the primary kernel on port ${h.mainPort} serves,`);
    h.writeKernels([{ id: 'main', port: newMain }, { id: 'nodir', port: nodir }]);
    assert.equal((await h.req('/restart?kernel=main', 'POST')).code, 200);
    await h.until(() => h.at(newMain, 'serving').length === 1, 10000, 'main did not move to its new port');
    await ensure(`which the primary kernel on port ${newMain} serves,`);
    await h.sleep(300);
    const lines = h.refusals('nodir');
    assert.equal(lines.length, 1, `one conflict (nodir on the primary's root) said ${lines.length} times:\n${lines.join('\n')}`);
    assert.deepEqual(h.at(nodir), [], 'the profile with no stateDir was started');
  } finally { await h.cleanup(); }
});

test('a profile refused at boot for one conflict and edited into another, onto an earlier profile\'s root, has the new conflict said: two lines, the second naming the earlier profile', async () => {
  const h = await world();
  try {
    const [first, aux] = [await freePort(__filename), await freePort(__filename)];
    const shared = path.join(h.dir, 'shared-state');
    h.writeKernels([{ id: 'aux', port: aux }]);
    await h.start();
    assert.equal(h.refusals('aux').length, 1, `refused at boot:\n${h.log}`);
    assert.match(h.refusals('aux')[0], /its kernels\.json profile has no stateDir, so it would run on the primary kernel's state root/);
    h.writeKernels([{ id: 'first', port: first, stateDir: shared }, { id: 'aux', port: aux, stateDir: shared }]);
    assert.equal((await h.req(`/ensure?port=${first}`, 'POST')).code, 200);
    await h.until(() => h.at(first, 'serving').length === 1, 10000, 'the earlier profile does not serve');
    for (let i = 0; i < 2; i++) assert.equal((await h.req(`/ensure?port=${aux}`, 'POST')).code, 409);
    await h.sleep(300);
    const lines = h.refusals('aux');
    assert.equal(lines.length, 2, `the new conflict on the same profile was not said, or was said again:\n${h.log}`);
    assert.ok(lines[1].includes(`its kernels.json profile's stateDir ${JSON.stringify(shared)} resolves to the state root ` +
                                `${fs.realpathSync(shared)} of kernel 'first' (port ${first})`), lines[1]);
    assert.deepEqual(h.at(aux), [], 'the refused profile was started');
  } finally { await h.cleanup(); }
});

// The line's key is the conflict, each part of it: the kernel, the kernel holding the root, the root and the reason. The
// case above changes the holder, the root and the reason at once; the four below change one part each, the holder alone,
// the reason alone, the kernel alone and the root alone, and each is a new conflict, said once. Each goes red when its
// part is dropped from the key (spawnKernel's rootRefusalsSaid key).
test('a refused profile whose root comes to be held by another kernel, with its root and reason the same, has the new holder said: two lines, the second naming it', async () => {
  const h = await world();
  try {
    const [pe, ps, pk] = [await freePort(__filename), await freePort(__filename), await freePort(__filename)];
    const shared = path.join(h.dir, 'shared-state'), r3 = path.join(h.dir, 'r3-state');
    h.writeKernels([{ id: 'e', port: pe, stateDir: shared }, { id: 's', port: ps, stateDir: shared }]);
    await h.start();
    await h.until(() => h.at(pe, 'serving').length === 1, 10000, 'e serves');
    assert.equal(h.refusals('s').length, 1, `refused at boot:\n${h.log}`);
    assert.ok(h.refusals('s')[0].includes(`of kernel 'e' (port ${pe}), ${RUNNING_HOLDER}`), h.refusals('s')[0]);
    // e stops and its entry moves to r3; k, added first, names the shared root: s's root and reason stay, its holder is k
    assert.equal((await h.req('/stop?kernel=e', 'POST')).code, 200);
    await h.until(() => h.log.includes("kernel 'e' stopped"), 10000, 'e did not stop');
    h.writeKernels([{ id: 'k', port: pk, stateDir: shared }, { id: 'e', port: pe, stateDir: r3 }, { id: 's', port: ps, stateDir: shared }]);
    for (let i = 0; i < 2; i++) {                           // the extension's retry
      const r = await h.req(`/ensure?port=${ps}`, 'POST');
      assert.equal(r.code, 409, r.body);
      assert.ok(JSON.parse(r.body).error.includes(`of kernel 'k' (port ${pk}), whose profile comes before it in kernels.json`), r.body);
    }
    await h.sleep(300);
    const lines = h.refusals('s');
    assert.equal(lines.length, 2, `the new holder was not said, or was said again:\n${h.log}`);
    assert.ok(lines[1].includes(`its kernels.json profile's stateDir ${JSON.stringify(shared)} resolves to the state root ` +
                                `${fs.realpathSync(shared)} of kernel 'k' (port ${pk}), whose profile comes before it in kernels.json`), lines[1]);
    assert.deepEqual(h.at(ps), [], 'the refused profile was started');
  } finally { await h.cleanup(); }
});

test('a refused profile whose reason changes, with its root and holder the same, has the new reason said: two lines, the second giving the stateDir it names', async () => {
  const h = await world();
  try {
    const aux = await freePort(__filename);
    h.writeKernels([{ id: 'aux', port: aux }]);
    await h.start();
    assert.equal(h.refusals('aux').length, 1, `refused at boot:\n${h.log}`);
    assert.match(h.refusals('aux')[0], /its kernels\.json profile has no stateDir, so it would run on the primary kernel's state root/);
    // the entry now names the primary's root with a trailing slash: the same root and the same holder, for another reason
    const named = h.state + '/';
    h.writeKernels([{ id: 'aux', port: aux, stateDir: named }]);
    for (let i = 0; i < 2; i++) {                           // the extension's retry
      const r = await h.req(`/ensure?port=${aux}`, 'POST');
      assert.equal(r.code, 409, r.body);
    }
    await h.sleep(300);
    const lines = h.refusals('aux');
    assert.equal(lines.length, 2, `the new reason was not said, or was said again:\n${h.log}`);
    assert.ok(lines[1].includes(`its kernels.json profile's stateDir ${JSON.stringify(named)} resolves to the primary kernel's state root ` +
                                `${fs.realpathSync(h.state)},`), lines[1]);
    assert.deepEqual(h.at(aux), [], 'the refused profile was started');
  } finally { await h.cleanup(); }
});

test('two profiles with no stateDir, the same holder, root and reason, are each refused at boot in a line of their own naming that profile', async () => {
  const h = await world();
  try {
    const [pa, pb] = [await freePort(__filename), await freePort(__filename)];
    h.writeKernels([{ id: 'a', port: pa }, { id: 'b', port: pb }]);
    await h.start();
    for (const port of [pa, pb]) {
      for (let i = 0; i < 2; i++) {                         // the extension's retry
        const r = await h.req(`/ensure?port=${port}`, 'POST');
        assert.equal(r.code, 409, r.body);
      }
    }
    await h.sleep(300);
    for (const [id, port] of [['a', pa], ['b', pb]]) {
      const lines = h.refusals(id);
      assert.equal(lines.length, 1, `one line for '${id}', which another profile's line on the same conflict does not stand for:\n${h.log}`);
      assert.match(lines[0], new RegExp(`^\\[romp-manager\\] kernel '${id}' \\(port ${port}\\) is not started: its kernels\\.json profile has no stateDir, ` +
                                        'so it would run on the primary kernel\'s state root'), lines[0]);
      assert.deepEqual(h.at(port), [], `'${id}' was started`);
    }
    assert.deepEqual((await h.kernels()).map((k) => k.id), ['main']);
  } finally { await h.cleanup(); }
});

test('a refused profile whose root alone changes, its holder and its reason the same, has the new root said: two lines, the second naming it', async () => {
  const h = await world();
  try {
    const [pe, ps] = [await freePort(__filename), await freePort(__filename)];
    const r1 = path.join(h.dir, 'r1-state'), r2 = path.join(h.dir, 'r2-state'), link = path.join(h.dir, 'state-link');
    for (const d of [r1, r2]) fs.mkdirSync(d);
    fs.symlinkSync(r1, link);
    h.writeKernels([{ id: 'e', port: pe, stateDir: r1 }, { id: 's', port: ps, stateDir: link }]);
    await h.start();
    await h.until(() => h.at(pe, 'serving').length === 1, 10000, 'e serves');
    assert.equal(h.refusals('s').length, 1, `refused at boot:\n${h.log}`);
    assert.ok(h.refusals('s')[0].includes(`its kernels.json profile's stateDir ${JSON.stringify(link)} resolves to the state root ` +
                                          `${fs.realpathSync(r1)} of kernel 'e' (port ${pe}), ${RUNNING_HOLDER}`), h.refusals('s')[0]);
    // e stops first, since a running kernel keeps the root it runs on and s would then start on the moved link; then e's
    // entry and the link both move to r2. s's holder (e) and its reason (the stateDir as written, the link) stay the same,
    // and only the root they resolve to changes
    assert.equal((await h.req('/stop?kernel=e', 'POST')).code, 200);
    await h.until(() => h.log.includes("kernel 'e' stopped"), 10000, 'e did not stop');
    fs.unlinkSync(link);
    fs.symlinkSync(r2, link);
    h.writeKernels([{ id: 'e', port: pe, stateDir: r2 }, { id: 's', port: ps, stateDir: link }]);
    for (let i = 0; i < 2; i++) {                           // the extension's retry
      const r = await h.req(`/ensure?port=${ps}`, 'POST');
      assert.equal(r.code, 409, r.body);
      assert.ok(JSON.parse(r.body).error.includes(`resolves to the state root ${fs.realpathSync(r2)} of kernel 'e' (port ${pe}), ` +
                                                  'whose profile comes before it in kernels.json'), r.body);
    }
    await h.sleep(300);
    const lines = h.refusals('s');
    assert.equal(lines.length, 2, `the new root was not said, or was said again:\n${h.log}`);
    assert.ok(lines[1].includes(`its kernels.json profile's stateDir ${JSON.stringify(link)} resolves to the state root ` +
                                `${fs.realpathSync(r2)} of kernel 'e' (port ${pe}), whose profile comes before it in kernels.json`), lines[1]);
    assert.deepEqual(h.at(ps), [], 'the refused profile was started');
  } finally { await h.cleanup(); }
});

test('the harness: the stand-in kernel says so and exits 2, opening nothing, when the root it resolves is outside the test\'s world', async () => {
  const h = await world();
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-registry-outside-'));
  try {
    const stray = await freePort(__filename);
    const root = path.join(outside, 'stray-state');           // not under the world, and not made yet
    h.writeKernels([{ id: 'stray', port: stray, stateDir: root }]);
    await h.start();
    await h.until(() => /kernel 'stray' \(pid \d+\) exited .*code=2 /.test(h.log), 10000, 'the stand-in for a root outside the world did not exit 2');
    assert.ok(h.log.includes(`fake kernel: state root '${root}' is outside the test's world`), h.log);
    assert.ok(!fs.existsSync(root), 'the stand-in made a state root outside its world');
    assert.deepEqual(h.at(stray), [], 'the stand-in wrote a row before it checked its root');
    assert.equal(h.at(h.mainPort, 'serving').length, 1, 'main, inside the world, serves');
    assert.equal(h.at(h.mainPort, 'serving')[0].root, fs.realpathSync(h.state));
  } finally { await h.cleanup(); fs.rmSync(outside, { recursive: true, force: true }); }
});

test('the harness: h.cleanup signals a pid from the stand-in log only once it is checked to be this world\'s, on the /proc road and on the ps road a host without /proc takes', async () => {
  for (const road of ['proc', 'ps']) {
    const h = await world();
    if (road === 'ps') h.procRoot = path.join(h.dir, 'no-proc-here');   // as on a host without /proc
    // a process of this world (its command line names the world, as a stand-in's does) and one that is not, each
    // with a row in the stand-in log, as a pid that exited and was reused by another process would have
    const ours = spawn(PY3, ['-c', 'import time; time.sleep(60)', h.dir], { stdio: 'ignore' });
    const foreign = spawn(PY3, ['-c', 'import time; time.sleep(60)'], { stdio: 'ignore' });
    const exits = [ours, foreign].map((c) => new Promise((resolve) => c.on('exit', (code, sig) => resolve(sig || `code ${code}`))));
    try {
      await h.until(() => h.standIn(ours.pid), 5000, `${road}: the world's process was not seen as the world's`);
      assert.ok(!h.standIn(foreign.pid), `${road}: a process that does not name the world was taken for the world's`);
      fs.writeFileSync(h.starts, [ours, foreign].map((c) => JSON.stringify({ event: 'serving', port: 1, pid: c.pid, root: h.dir }) + '\n').join(''));
      await h.cleanup();
      assert.equal(await Promise.race([exits[0], h.sleep(3000).then(() => 'still running')]), 'SIGKILL', `${road}: the world's process was not killed`);
      assert.equal(await Promise.race([exits[1].then((s) => `exited (${s})`), h.sleep(1000).then(() => 'still running')]), 'still running',
                   `${road}: h.cleanup signalled a pid it could not check to be this world's`);
    } finally {
      for (const c of [ours, foreign]) { try { c.kill('SIGKILL'); } catch (e) { /* gone */ } }   // this test's own children
      await Promise.all(exits);
      fs.rmSync(h.dir, { recursive: true, force: true });
    }
  }
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
