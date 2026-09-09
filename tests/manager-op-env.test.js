// romp-manager's tmux server start environment (2026-09-08): romp holds no API key and runs no secret-manager
// CLI, so the manager hands `tmux start-server` its environment UNCHANGED (withoutOpCredentials is a plain copy;
// the provider-gated scrub is retired with the providers). What guards the panes instead is the refusal to start
// at all while the environment carries a retired provider variable: every pane the server creates inherits the
// SERVER's globals, and a `romp new -t` session's `exec claude` would read a leftover ANTHROPIC_API_KEY from there
// while the kernel alone refused to boot. The last case runs a real `romp-manager up` on private ports and reads
// the refusal off its log: it names every retired variable found (the 2026-09-09 fold review, ruling 6). Synthetic
// values throughout.
// Run: node --test tests/manager-*.test.js
'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

process.env.ROMP_STATE_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-op-env-'));
const mgr = require(path.join(__dirname, '..', 'bin', 'romp-manager'));
const { withoutOpCredentials, retiredCredentialNames, retiredCredentialMessage } = mgr;

const ENV = { PATH: '/usr/bin', HOME: '/nonexistent', ANTHROPIC_AUTH_TOKEN: 'synthetic-bearer', ROMP_EXPECTED_AUTH: 'key' };

test('the tmux start environment is a plain copy: nothing scrubbed, nothing mutated', () => {
  const out = withoutOpCredentials(ENV);
  assert.deepEqual(out, ENV);
  assert.notStrictEqual(out, ENV, 'a copy, so a caller cannot mutate the manager environment through it');
  assert.equal(mgr.serviceEnvHasRef, undefined, 'the provider-file reader is retired with the providers');
});

test('a retired provider variable in the environment is named, never valued, and refuses the start', () => {
  assert.deepEqual(retiredCredentialNames(ENV), [], 'the declaration and a login token are not retired names');
  for (const name of ['ROMP_API_KEY_CMD', 'ROMP_API_KEY_REF', 'ANTHROPIC_API_KEY']) {
    const found = retiredCredentialNames({ ...ENV, [name]: 'synthetic-value-never-printed' });
    assert.deepEqual(found, [name]);
    const msg = retiredCredentialMessage(found);
    assert.match(msg, /did NOT start/);
    assert.match(msg, new RegExp(name));
    assert.match(msg, /apiKeyHelper/);
    assert.match(msg, /ROMP_EXPECTED_AUTH=key/);
    assert.doesNotMatch(msg, /synthetic-value/, 'names and files only, never a value');
  }
  assert.deepEqual(retiredCredentialNames({ ...ENV, ANTHROPIC_API_KEY: '', ROMP_API_KEY_REF: 'op://v/i/f' }),
                   ['ROMP_API_KEY_REF', 'ANTHROPIC_API_KEY'], 'an empty value is still the variable');
});

test('the 1Password CLI names are refused like the provider variables, and the message says why', () => {
  const clean = { PATH: '/usr/bin', HOME: '/nonexistent', ROMP_EXPECTED_AUTH: 'key' };
  assert.deepEqual(retiredCredentialNames(clean), []);
  const found = retiredCredentialNames({ ...clean, OP_SERVICE_ACCOUNT_TOKEN: 'synthetic-op-token', OP_SESSION_acct: 'synthetic-session' });
  assert.deepEqual(found, ['OP_SERVICE_ACCOUNT_TOKEN', 'OP_SESSION_acct']);
  const msg = retiredCredentialMessage(found);
  assert.match(msg, /did NOT start/);
  assert.match(msg, /OP_SERVICE_ACCOUNT_TOKEN/);
  assert.match(msg, /no longer runs op/);
  assert.doesNotMatch(msg, /synthetic-/, 'names only');
});

test('startManager refuses before the tmux server starts (source pin: the check is its first statement)', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'bin', 'romp-manager'), 'utf8');
  const body = src.slice(src.indexOf('function startManager() {'));
  const check = body.indexOf('retiredCredentialNames(process.env)');
  const tmux = body.indexOf('startTmuxServer();');
  assert.ok(check > 0 && tmux > 0 && check < tmux, 'the refusal runs before startTmuxServer()');
  assert.ok(body.slice(check, tmux).includes('process.exit(1)'), 'and it exits rather than warns');
});

// The refusal, executed (the 2026-09-09 fold review, ruling 6): `romp-manager up` with retired names in its
// environment exits 1 and its one log line NAMES the variables to remove, never their values, so the operator
// reading manager.log knows which lines to take out of service.env. Two more facts of the resolved order ride
// along: the `romp down` marker is cleared first (the start was asked for, so `romp status` does not call the
// kernel stopped on purpose while the manager refuses to run), and the tmux server is never started (the stub
// tmux on PATH leaves a witness file when it runs). Private ports: on the default port a live manager would
// answer the probe and the exit would be its "already running" refusal, not this one.
test('romp-manager up: the exit-1 line names every retired variable found, values stay out, the marker is cleared, tmux never starts', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-refusal-'));
  try {
    const bin = path.join(dir, 'bin'), state = path.join(dir, 'state'), witness = path.join(dir, 'tmux-ran');
    fs.mkdirSync(bin); fs.mkdirSync(state);
    fs.writeFileSync(path.join(bin, 'tmux'), '#!/bin/sh\necho ran >> "$ROMP_TEST_TMUX_LOG"\nexit 0\n', { mode: 0o755 });
    const marker = path.join(state, 'down-by-romp');
    fs.writeFileSync(marker, JSON.stringify({ t: 1700000000, cmd: 'romp down' }) + '\n');
    const env = { PATH: bin, HOME: '/nonexistent', ROMP_STATE_DIR: state, ROMP_MANAGER_PORT: '7625', ROMP_SERVE_PORT: '7626',
      ROMP_TEST_TMUX_LOG: witness, ROMP_EXPECTED_AUTH: 'key',
      ANTHROPIC_API_KEY: 'synthetic-value-never-printed', ROMP_API_KEY_REF: 'op://synthetic-vault/synthetic-item/field' };
    const r = spawnSync(process.execPath, [path.join(__dirname, '..', 'bin', 'romp-manager'), 'up'], { env, encoding: 'utf8', timeout: 20000 });
    assert.equal(r.status, 1, `exit 1: ${r.stderr}`);
    const line = r.stderr.split('\n').find((l) => /did NOT start/.test(l)) || '';
    assert.ok(line, `the refusal is on the log: ${r.stderr}`);
    assert.match(line, /its environment carries ROMP_API_KEY_REF, ANTHROPIC_API_KEY\. /, 'every retired name found, each spelled out');
    assert.doesNotMatch(r.stderr, /synthetic-value|op:\/\//, 'names only, never a value');
    assert.doesNotMatch(r.stderr, /already running/, 'the private port held no manager: this is the retired-names refusal');
    assert.match(r.stderr, /cleared the `romp down` marker/, 'the clear runs first and says so');
    assert.equal(fs.existsSync(marker), false, 'the marker is gone: a refused start still counts as asked for');
    assert.equal(fs.existsSync(witness), false, 'the refusal precedes startTmuxServer(): the stub tmux never ran');
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
