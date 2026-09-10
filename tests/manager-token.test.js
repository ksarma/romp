// The manager's write gate (2026-09-10): a local process restarted every session on a machine by
// posting to the control port, which took POST /restart-all from anything on loopback. Every
// state-changing door (/restart-all, /restart, /stop, /ensure) now requires the kernel's serve token in
// X-Romp-Token, read fresh per request from the same 0600 file the kernel gates its own writes with;
// GET /status stays open; a manager that cannot read the token refuses writes (503), never opens them.
// A real manager on an ephemeral loopback port with a stand-in kernel (tests/manager-down.test.js's
// shape), a private state root, and invented tokens. Run: node --test tests/manager-token.test.js
'use strict';
const { test, after } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const http = require('node:http');
const { spawn } = require('node:child_process');

const MGR = path.join(__dirname, '..', 'bin', 'romp-manager');
// The module's STATE_ROOT is fixed at require time: a private root, and no env spelling of the token, so
// the pure-function tests below read a file this test wrote.
const MODULE_STATE = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-token-module-'));
after(() => fs.rmSync(MODULE_STATE, { recursive: true, force: true }));   // one leaked dir per run otherwise
process.env.ROMP_STATE_DIR = MODULE_STATE;
delete process.env.ROMP_SERVE_TOKEN;
const { writeGate, serveToken, acceptedTokens, mintServeTokenIfAbsent } = require(MGR);

const TOKEN = 'zq9-not-a-real-token-zq9';   // synthetic; the tests assert it never reaches a log or a body

// A loopback port nothing holds right now: bound, then released. The window to the manager's own bind
// is milliseconds; a fixed literal collides with a peer checkout's run every time.
function freePort() {
  return new Promise((resolve, reject) => {
    const s = net.createServer();
    s.on('error', reject);
    s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => resolve(p)); });
  });
}

// A real manager in a private world: its own state root (with or without a token file), a no-op tmux,
// a stand-in kernel that stays up, and no ROMP_SERVE_TOKEN in its environment, so the FILE is the token.
// `profile`: a kernels.json entry with its own stateDir holding `profile.token` (a second stand-in
// kernel is spawned for it). `unreadable`: a directory at the token path, a file the manager can neither
// read nor mint over.
async function manager({ token, profile, unreadable } = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-token-'));
  const bin = path.join(dir, 'bin'), state = path.join(dir, 'state');
  for (const d of [bin, state, path.join(dir, 'tmux')]) fs.mkdirSync(d);
  fs.writeFileSync(path.join(bin, 'tmux'), '#!/bin/sh\nexit 0\n', { mode: 0o755 });
  if (token) fs.writeFileSync(path.join(state, 'serve-token'), token + '\n', { mode: 0o600 });
  if (unreadable) fs.mkdirSync(path.join(state, 'serve-token'));
  const serve = path.join(dir, 'fake-serve');
  fs.writeFileSync(serve, `#!/bin/sh\nexec "${process.execPath}" -e "setInterval(() => {}, 1000)"\n`, { mode: 0o755 });
  const port = await freePort(), servePort = await freePort();
  let profileRoot = '';
  if (profile) {
    profileRoot = path.join(dir, 'profile-state');
    fs.mkdirSync(profileRoot);
    fs.writeFileSync(path.join(profileRoot, 'serve-token'), profile.token + '\n', { mode: 0o600 });
    fs.writeFileSync(path.join(state, 'kernels.json'),
      JSON.stringify({ kernels: [{ id: profile.id, port: await freePort(), stateDir: profileRoot }] }));
  }
  const env = Object.assign({}, process.env, {
    PATH: bin, TMUX_TMPDIR: path.join(dir, 'tmux'), ROMP_CLI_SCOPE: '0',
    ROMP_STATE_DIR: state, ROMP_MANAGER_PORT: String(port), ROMP_SERVE_PORT: String(servePort),
    ROMP_SERVE_BIN: serve, ROMP_SHUTDOWN_GRACE_MS: '500',
  });
  delete env.ROMP_SUPERVISED;
  delete env.ROMP_SERVE_TOKEN;
  delete env.XDG_STATE_HOME;
  const mgr = spawn(process.execPath, [MGR, 'up'], { env, stdio: ['ignore', 'ignore', 'pipe'] });
  const h = { dir, state, profileRoot, port, mgr, log: '', pids: new Set() };   // pids: every kernel the manager reported, reaped at cleanup
  mgr.stderr.on('data', (d) => { h.log += d; });
  h.exited = new Promise((resolve) => mgr.on('exit', (code, sig) => resolve({ code, sig })));
  h.sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  h.req = (p, method, headers) => new Promise((resolve, reject) => {
    const r = http.request({ host: '127.0.0.1', port, path: p, method, timeout: 3000, headers: headers || {} }, (res) => {
      let b = ''; res.on('data', (d) => (b += d)); res.on('end', () => resolve({ code: res.statusCode, body: b }));
    });
    r.on('error', reject); r.on('timeout', () => { r.destroy(); reject(new Error('timeout')); }); r.end();
  });
  h.kernels = async () => {
    const st = JSON.parse((await h.req('/status', 'GET')).body);
    for (const k of st.kernels || []) if (k.pid) h.pids.add(k.pid);
    return st.kernels || [];
  };
  h.kernel = async () => (await h.kernels())[0] || {};
  const want = profile ? 2 : 1;
  for (let i = 0; i < 100; i++) {                       // up: /status answers and names every kernel
    try { if ((await h.kernels()).filter((k) => k.pid).length >= want) break; } catch (e) { /* not yet */ }
    await h.sleep(50);
  }
  h.cleanup = async () => {
    try { mgr.kill('SIGTERM'); } catch (e) { /* gone */ }   // the orderly way first: shutdownAll stops the kernels
    await Promise.race([h.exited, h.sleep(2000)]);
    try { mgr.kill('SIGKILL'); } catch (e) { /* gone */ }
    for (const p of h.pids) { try { process.kill(p, 'SIGKILL'); } catch (e) { /* gone */ } }
    fs.rmSync(dir, { recursive: true, force: true });
  };
  return h;
}

test('writeGate: no token to compare against is 503, a missing or wrong header is 401, a match against any held token is ok, and no answer carries a token', () => {
  const have = { tokens: [TOKEN] };
  assert.deepEqual([writeGate(undefined, have).code, writeGate('', have).code, writeGate('zq9-other-zq9', have).code, writeGate(TOKEN + 'x', have).code], [401, 401, 401, 401]);
  assert.equal(writeGate(TOKEN, have).ok, true);
  assert.equal(writeGate(' ' + TOKEN + '\n', have).ok, true, 'a trailing newline from a `cat` is not a different token');
  const two = { tokens: [TOKEN, 'zq9-profile-zq9'] };                   // a kernels.json profile's own token
  assert.equal(writeGate('zq9-profile-zq9', two).ok, true, 'a profile kernel presents its own root\'s token');
  assert.equal(writeGate(TOKEN, two).ok, true, 'and the primary still matches');
  assert.equal(writeGate('zq9-third-zq9', two).code, 401);
  for (const g of [writeGate(undefined, have), writeGate('zq9-other-zq9', have)]) {
    assert.match(g.error, /X-Romp-Token/);
    assert.match(g.error, /serve-token/);                       // the body names the file to read
    assert.match(g.error, /stateDir/);                          // and that a profile's own file is accepted
    assert.doesNotMatch(JSON.stringify(g), /zq9/);              // never the token, presented or held
  }
  const missing = writeGate(TOKEN, { tokens: [], why: '/x/state/serve-token: ENOENT' });
  assert.equal(missing.code, 503);
  assert.match(missing.error, /cannot read the serve token/);
  assert.match(missing.error, /ENOENT/);                        // what to repair
  assert.equal(writeGate(TOKEN, { tokens: [''] }).code, 503);
  assert.equal(writeGate(TOKEN, undefined).code, 503);
});

test('acceptedTokens: the primary root\'s token plus each kernels.json profile\'s own, read fresh; an unreadable profile file drops out', () => {
  const file = path.join(MODULE_STATE, 'serve-token');
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-token-prof-'));
  try {
    fs.writeFileSync(file, TOKEN + '\n');
    fs.writeFileSync(path.join(MODULE_STATE, 'kernels.json'), JSON.stringify({ kernels: [
      { id: 'k2', port: 30111, stateDir: prof }, { id: 'k3', port: 30112, stateDir: path.join(prof, 'absent') }] }));
    assert.deepEqual(acceptedTokens(), { tokens: [TOKEN], why: '' }, 'no profile file yet: the primary alone');
    fs.writeFileSync(path.join(prof, 'serve-token'), 'zq9-prof-zq9\n');
    assert.deepEqual(acceptedTokens(), { tokens: [TOKEN, 'zq9-prof-zq9'], why: '' }, 'the profile\'s file, on the next read');
    fs.unlinkSync(file);
    const r = acceptedTokens();
    assert.deepEqual(r.tokens, ['zq9-prof-zq9'], 'the primary unreadable: the profile\'s still accepted');
    assert.match(r.why, /serve-token/);
  } finally {
    fs.rmSync(prof, { recursive: true, force: true });
    fs.rmSync(path.join(MODULE_STATE, 'kernels.json'), { force: true });
    fs.rmSync(file, { force: true });
  }
});

test('mintServeTokenIfAbsent: an absent path gets a 0600 file in the kernel\'s shape; anything already there is left alone', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-token-mint-'));
  try {
    const file = path.join(root, 'serve-token');
    const r = mintServeTokenIfAbsent(root);
    assert.deepEqual(r, { minted: true, file });
    const v = fs.readFileSync(file, 'utf8');
    assert.match(v, /^[A-Za-z0-9_-]{24}$/, 'base64url of 18 bytes, no padding, no newline: _serve_token_read_or_mint\'s shape');
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    assert.deepEqual(fs.readdirSync(root), ['serve-token'], 'no temp file left');
    assert.deepEqual(mintServeTokenIfAbsent(root), { minted: false }, 'a file already there stands');
    assert.equal(fs.readFileSync(file, 'utf8'), v, 'and is not replaced');
    fs.writeFileSync(file, '');
    assert.deepEqual(mintServeTokenIfAbsent(root), { minted: false }, 'an empty file is the kernel\'s to judge, not minted over');
    fs.unlinkSync(file); fs.mkdirSync(file);
    assert.deepEqual(mintServeTokenIfAbsent(root), { minted: false }, 'a directory at the path is left alone');
    process.env.ROMP_SERVE_TOKEN = 'env-spelling';
    try { assert.deepEqual(mintServeTokenIfAbsent(path.join(root, 'none')), { minted: false }, 'the env is the token: nothing to mint'); }
    finally { delete process.env.ROMP_SERVE_TOKEN; }
    assert.equal(fs.existsSync(path.join(root, 'none')), false);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('serveToken: the env spelling first, else the file under the state root, else why', () => {
  const file = path.join(MODULE_STATE, 'serve-token');
  const r0 = serveToken();
  assert.equal(r0.token, '');
  assert.match(r0.why, /serve-token/);
  fs.writeFileSync(file, TOKEN + '\n');
  assert.deepEqual(serveToken(), { token: TOKEN });
  fs.writeFileSync(file, '\n');
  assert.match(serveToken().why, /empty/);
  process.env.ROMP_SERVE_TOKEN = 'env-spelling';
  try { assert.deepEqual(serveToken(), { token: 'env-spelling' }); } finally { delete process.env.ROMP_SERVE_TOKEN; }
  fs.unlinkSync(file);
});

test('a tokenless POST /restart-all is refused with 401, one line, and restarts nothing; the log names the address and the door, never the token', async () => {
  const h = await manager({ token: TOKEN });
  try {
    const before = await h.kernel();
    assert.ok(before.pid, `no kernel came up: ${h.log}`);
    const r = await h.req('/restart-all', 'POST');
    assert.equal(r.code, 401, r.body);
    const body = JSON.parse(r.body);
    assert.equal(body.ok, false);
    assert.match(body.error, /X-Romp-Token/);
    assert.equal(r.body.trim().split('\n').length, 1);
    await h.sleep(400);
    const after = await h.kernel();
    assert.equal(after.pid, before.pid, 'the kernel was not restarted');
    assert.equal(after.restarts, 0);
    assert.match(h.log, /refused POST \/restart-all from 127\.0\.0\.1: no serve token presented/);
    assert.doesNotMatch(h.log, /restart-all requested/, 'the door\'s own line never ran');
    assert.doesNotMatch(h.log, /zq9/);
  } finally { await h.cleanup(); }
});

test('a wrong token is 401 and restarts nothing; the log says it did not match and shows neither token', async () => {
  const h = await manager({ token: TOKEN });
  try {
    const before = await h.kernel();
    const r = await h.req('/restart-all', 'POST', { 'X-Romp-Token': 'zq9-wrong-zq9' });
    assert.equal(r.code, 401, r.body);
    await h.sleep(400);
    assert.equal((await h.kernel()).pid, before.pid);
    assert.match(h.log, /refused POST \/restart-all from 127\.0\.0\.1: the serve token did not match/);
    assert.doesNotMatch(h.log, /zq9/);
  } finally { await h.cleanup(); }
});

test('the right token is accepted: /restart-all answers 200, the kernel is respawned, and the door logs its source as before', async () => {
  const h = await manager({ token: TOKEN });
  try {
    const before = await h.kernel();
    const r = await h.req('/restart-all', 'POST', { 'X-Romp-Token': TOKEN });
    assert.equal(r.code, 200, r.body);
    assert.deepEqual(JSON.parse(r.body).restarted, ['main']);
    let after = before;
    for (let i = 0; i < 100 && (!after.pid || after.pid === before.pid); i++) { await h.sleep(50); after = await h.kernel(); }
    assert.notEqual(after.pid, before.pid, `the kernel was not respawned: ${h.log}`);
    assert.match(h.log, /restart-all requested \(IMMEDIATE\) from 127\.0\.0\.1/);
    assert.doesNotMatch(h.log, /refused POST/);
  } finally { await h.cleanup(); }
});

test('GET /status needs no token, and ignores a wrong one: a read is not a door', async () => {
  const h = await manager({ token: TOKEN });
  try {
    assert.equal((await h.req('/status', 'GET')).code, 200);
    assert.equal((await h.req('/status', 'GET', { 'X-Romp-Token': 'zq9-wrong-zq9' })).code, 200);
    assert.doesNotMatch(h.log, /refused/);
  } finally { await h.cleanup(); }
});

test('every write door is behind the gate: /restart, /ensure and /stop without a token are 401 and change nothing', async () => {
  const h = await manager({ token: TOKEN });
  try {
    const before = await h.kernel();
    const extra = await freePort();
    for (const p of ['/restart', `/ensure?port=${extra}`, '/stop']) assert.equal((await h.req(p, 'POST')).code, 401, p);
    await h.sleep(400);
    const st = JSON.parse((await h.req('/status', 'GET')).body);   // the manager still answers: /stop did nothing
    assert.equal(st.kernels.length, 1, 'no kernel was ensured');
    assert.equal(st.kernels[0].pid, before.pid, 'no kernel was restarted');
    assert.match(h.log, /refused POST \/restart from/);
    assert.match(h.log, /refused POST \/ensure from/);
    assert.match(h.log, /refused POST \/stop from/);
    // a tokened /stop then lands, so the test leaves nothing behind
    assert.equal((await h.req('/stop', 'POST', { 'X-Romp-Token': TOKEN })).code, 200);
    const out = await Promise.race([h.exited, h.sleep(4000).then(() => null)]);
    assert.ok(out !== null, `the manager did not leave after a tokened /stop: ${h.log}`);
  } finally { await h.cleanup(); }
});

test('an unreadable token path: writes are refused with 503 (never open) while reads work; the file appearing opens the doors with no manager restart', async () => {
  // a directory at the path: the manager can neither read it nor mint over it (only an ABSENT path is
  // minted at start, see the test below), so it holds no token to compare against
  const h = await manager({ unreadable: true });
  try {
    const before = await h.kernel();
    assert.ok(before.pid, `no kernel came up: ${h.log}`);
    assert.doesNotMatch(h.log, /minted the serve token/, 'something at the path is left alone, quietly: the refusals below are the log');
    const r = await h.req('/restart-all', 'POST', { 'X-Romp-Token': TOKEN });
    assert.equal(r.code, 503, r.body);
    const body = JSON.parse(r.body);
    assert.equal(body.ok, false);
    assert.match(body.error, /cannot read the serve token/);
    assert.match(body.error, /serve-token/);
    assert.equal(r.body.trim().split('\n').length, 1);
    assert.equal((await h.req('/restart-all', 'POST')).code, 503, 'tokenless is the same refusal: nothing to compare against');
    assert.equal((await h.req('/status', 'GET')).code, 200);
    await h.sleep(400);
    assert.equal((await h.kernel()).pid, before.pid, 'nothing restarted');
    assert.match(h.log, /refused POST \/restart-all from 127\.0\.0\.1: the serve token is unavailable/);
    // the token file arrives (a kernel booted and minted it): the next request is compared against it
    fs.rmdirSync(path.join(h.state, 'serve-token'));
    fs.writeFileSync(path.join(h.state, 'serve-token'), TOKEN + '\n', { mode: 0o600 });
    assert.equal((await h.req('/restart-all', 'POST', { 'X-Romp-Token': 'zq9-wrong-zq9' })).code, 401);
    assert.equal((await h.req('/restart-all', 'POST', { 'X-Romp-Token': TOKEN })).code, 200);
  } finally { await h.cleanup(); }
});

test('no token file at start: the manager mints one (0600, the kernel\'s shape) before its port opens, and /stop with it lands', async () => {
  // before this a manager whose kernel never minted a token (romp-serve exiting before its exec, a
  // crash loop) answered 503 to every write, and `romp down` could not stop it
  const h = await manager({});
  try {
    const file = path.join(h.state, 'serve-token');
    assert.ok(fs.existsSync(file), `no token was minted: ${h.log}`);
    const tok = fs.readFileSync(file, 'utf8').trim();
    assert.match(tok, /^[A-Za-z0-9_-]{24}$/);
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    assert.match(h.log, /minted the serve token at .*serve-token \(nothing was there\)/);
    assert.ok(h.log.indexOf('minted the serve token') < h.log.indexOf('control :'), 'minted before the port opened');
    assert.equal((await h.req('/restart-all', 'POST')).code, 401, 'still gated');
    assert.equal((await h.req('/restart-all', 'POST', { 'X-Romp-Token': 'zq9-wrong-zq9' })).code, 401);
    assert.equal((await h.req('/stop', 'POST', { 'X-Romp-Token': tok })).code, 200);
    const out = await Promise.race([h.exited, h.sleep(4000).then(() => null)]);
    assert.ok(out !== null, `the manager did not leave after /stop with the minted token: ${h.log}`);
  } finally { await h.cleanup(); }
});

test('a kernels.json profile\'s own token is accepted on every door, a foreign one refused, the primary still accepted', async () => {
  // a profile kernel serves with its own root's token (specEnv: ROMP_STATE_DIR = stateDir) and presents
  // it when its dashboard's Restart or its converge posts here; the gate compared against the primary
  // alone and refused it with 401 (review round 1, 2026-09-10)
  const h = await manager({ token: TOKEN, profile: { id: 'k2', token: 'zq9-profile-zq9' } });
  try {
    const before = await h.kernels();
    assert.deepEqual(before.map((k) => k.id).sort(), ['k2', 'main'], `both kernels up: ${h.log}`);
    assert.equal((await h.req('/restart?kernel=k2', 'POST', { 'X-Romp-Token': 'zq9-profile-zq9' })).code, 200, 'the profile token restarts its own kernel');
    assert.equal((await h.req('/restart-all', 'POST', { 'X-Romp-Token': 'zq9-third-zq9' })).code, 401, 'a foreign token is still refused');
    const all = await h.req('/restart-all', 'POST', { 'X-Romp-Token': 'zq9-profile-zq9' });
    assert.equal(all.code, 200, all.body);
    assert.deepEqual(JSON.parse(all.body).restarted.sort(), ['k2', 'main']);
    assert.equal((await h.req('/restart-all', 'POST', { 'X-Romp-Token': TOKEN })).code, 200, 'the primary still matches');
    // re-read per request: the profile remints, the new value is honoured and the old refused
    fs.writeFileSync(path.join(h.profileRoot, 'serve-token'), 'zq9-profile-2-zq9\n', { mode: 0o600 });
    assert.equal((await h.req('/restart-all', 'POST', { 'X-Romp-Token': 'zq9-profile-zq9' })).code, 401);
    assert.equal((await h.req('/restart-all', 'POST', { 'X-Romp-Token': 'zq9-profile-2-zq9' })).code, 200);
    assert.doesNotMatch(h.log, /zq9/);
    // the control client run under the profile's root (its shell) reaches the doors too
    const env = Object.assign({}, process.env, { ROMP_MANAGER_PORT: String(h.port), ROMP_STATE_DIR: h.profileRoot });
    delete env.ROMP_SERVE_TOKEN;
    const r = await runClient(['restart', 'k2'], env);
    assert.equal(r.status, 0, `${r.stdout}${r.stderr}`);
    await h.kernels();                                          // record the respawned pids for cleanup
  } finally { await h.cleanup(); }
});

test('a reminted token is honoured on the next request: the old one is refused, the new one accepted', async () => {
  const h = await manager({ token: TOKEN });
  try {
    fs.writeFileSync(path.join(h.state, 'serve-token'), 'zq9-second-zq9\n', { mode: 0o600 });
    assert.equal((await h.req('/restart-all', 'POST', { 'X-Romp-Token': TOKEN })).code, 401);
    assert.equal((await h.req('/restart-all', 'POST', { 'X-Romp-Token': 'zq9-second-zq9' })).code, 200);
  } finally { await h.cleanup(); }
});

// The control client is how `romp refresh` (restart-all), `romp down` (down) and `romp-manager restart
// [kernel]` reach the doors: it reads the same file and sends the header; the read verb sends none. The
// stand-in below serves on this process's event loop, so the client runs asynchronously (a spawnSync
// would block the loop and the stand-in with it, and the client would time out).
function runClient(argv, env) {
  return new Promise((resolve) => {
    const c = spawn(process.execPath, [MGR, ...argv], { env, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    c.stdout.on('data', (d) => (stdout += d)); c.stderr.on('data', (d) => (stderr += d));
    c.on('exit', (status) => resolve({ status, stdout, stderr }));
  });
}
function recordingStandIn(answer) {
  const seen = [];
  const srv = http.createServer((req, res) => {
    seen.push([req.method, req.url.split('?')[0], req.headers['x-romp-token']]);
    res.writeHead(answer.code, { 'Content-Type': 'application/json' });
    res.end(answer.body);
  });
  return new Promise((resolve) => srv.listen(0, '127.0.0.1', () => resolve({ srv, seen, port: srv.address().port })));
}

test('the control client sends the token file\'s value on restart-all, restart and down, and none on status', async () => {
  const { srv, seen, port } = await recordingStandIn({ code: 200, body: '{"ok":true}' });
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-cli-'));
  try {
    fs.writeFileSync(path.join(dir, 'serve-token'), 'zq9-cli-zq9\n', { mode: 0o600 });
    const env = Object.assign({}, process.env, { ROMP_MANAGER_PORT: String(port), ROMP_STATE_DIR: dir });
    delete env.ROMP_SERVE_TOKEN;
    for (const argv of [['restart-all'], ['restart-all', '--quiet'], ['restart', 'main'], ['down'], ['status']]) {
      const r = await runClient(argv, env);
      assert.equal(r.status, 0, `${argv.join(' ')}: ${r.stderr}`);
      assert.doesNotMatch(r.stderr, /serve token/, 'a readable token draws no line');
    }
    assert.deepEqual(seen, [
      ['POST', '/restart-all', 'zq9-cli-zq9'], ['POST', '/restart-all', 'zq9-cli-zq9'],
      ['POST', '/restart', 'zq9-cli-zq9'], ['POST', '/stop', 'zq9-cli-zq9'], ['GET', '/status', undefined]]);
  } finally { srv.close(); fs.rmSync(dir, { recursive: true, force: true }); }
});

test('the control client with no token to send says so once on stderr, still asks, and exits 1 on the refusal, printing it', async () => {
  const { srv, seen, port } = await recordingStandIn({ code: 401, body: '{"ok":false,"error":"serve token required"}' });
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-cli-none-'));
  try {
    const env = Object.assign({}, process.env, { ROMP_MANAGER_PORT: String(port), ROMP_STATE_DIR: dir });
    delete env.ROMP_SERVE_TOKEN;
    const r = await runClient(['restart-all'], env);
    assert.equal(r.status, 1, r.stderr);
    assert.equal((r.stderr.match(/the serve token could not be read/g) || []).length, 1, r.stderr);
    assert.match(r.stderr, /serve-token/);                      // the file to repair
    assert.match(r.stdout, /serve token required/);            // the manager's own answer, printed
    assert.deepEqual(seen, [['POST', '/restart-all', undefined]]);
  } finally { srv.close(); fs.rmSync(dir, { recursive: true, force: true }); }
});
