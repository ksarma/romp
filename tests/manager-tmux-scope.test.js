// romp-manager's default tmux server and the service cgroup (2026-09-05): the manager runs as a
// systemd user service that relies on systemd's default KillMode=control-group, so a tmux server it
// starts bare dies with `systemctl --user restart romp-manager`, and every session's tmux jobs die
// with it. tmuxStartArgv is the pure argv choice, and it mirrors the kernel's cli_scope_supported
// exactly: scoped when ROMP_CLI_SCOPE=1, or under ROMP_SUPERVISED unless ROMP_CLI_SCOPE=0 — and then
// only on Linux with systemd-run on PATH. A terminal-run manager scopes nothing unless asked. No tmux
// on PATH → null: nothing to start, nothing to log (the behaviour before the scopes).
// Run: node --test tests/manager-*.test.js
'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

process.env.ROMP_STATE_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-tmux-scope-'));
const { tmuxStartArgv, commandOnPath, TMUX_START_ARGV } = require(path.join(__dirname, '..', 'bin', 'romp-manager'));

const BARE = ['tmux', 'start-server', ';', 'set', '-g', 'exit-empty', 'off'];
const both = (name) => name === 'systemd-run' || name === 'tmux';   // a Linux box with both installed
const tmuxOnly = (name) => name === 'tmux';                         // no systemd-run
const SUPERVISED = { ROMP_SUPERVISED: '1' };                         // what bin/romp-service's unit sets
const pick = (env, opts = {}) => tmuxStartArgv({ platform: 'linux', env, onPath: both, now: () => 1725000000000, ...opts });

test('the bare tmux argv is the one the manager always used', () => {
  assert.deepEqual(TMUX_START_ARGV, BARE);
});

test('under the supervised service on linux with systemd-run: the server starts inside a transient scope', () => {
  const p = pick(SUPERVISED);
  assert.equal(p.scoped, true);
  assert.equal(p.argv[0], 'systemd-run');
  for (const flag of ['--user', '--scope', '--quiet', '--collect']) assert.ok(p.argv.includes(flag), flag);
  const unit = p.argv.find((a) => a.startsWith('--unit='));
  assert.equal(unit, '--unit=romp-tmux-1725000000000');
  // the tmux argv follows `--`, verbatim
  const dash = p.argv.indexOf('--');
  assert.ok(dash > 0);
  assert.deepEqual(p.argv.slice(dash + 1), BARE);
});

test('two picks get two unit names (systemd refuses a duplicate as "already loaded")', () => {
  let t = 1;
  const a = pick(SUPERVISED, { now: () => t++ });
  const b = pick(SUPERVISED, { now: () => t++ });
  assert.notEqual(a.argv.find((x) => x.startsWith('--unit=')), b.argv.find((x) => x.startsWith('--unit=')));
});

// The switch mirrors the kernel's (cli_scope_supported): the same environment gives the same answer.
test('a terminal-run manager (ROMP_SUPERVISED unset) scopes nothing, systemd-run or not', () => {
  assert.deepEqual(pick({}), { argv: BARE, scoped: false });
  assert.deepEqual(pick({ ROMP_SUPERVISED: '' }), { argv: BARE, scoped: false }, 'an empty value is unset');
});

test('ROMP_CLI_SCOPE=1 turns the scope on for a manager run outside the service', () => {
  assert.equal(pick({ ROMP_CLI_SCOPE: '1' }).scoped, true);
});

test('ROMP_CLI_SCOPE=0 turns the scope off under the service', () => {
  assert.deepEqual(pick({ ...SUPERVISED, ROMP_CLI_SCOPE: '0' }), { argv: BARE, scoped: false });
});

test('an empty ROMP_CLI_SCOPE under the service is the default (on), as in the kernel', () => {
  assert.equal(pick({ ...SUPERVISED, ROMP_CLI_SCOPE: '' }).scoped, true);
});

test('systemd-run absent: the bare call, even under the service', () => {
  assert.deepEqual(pick(SUPERVISED, { onPath: tmuxOnly }), { argv: BARE, scoped: false });
});

test('darwin: the bare call, whatever is on PATH or in the environment (launchd owns the lineage there)', () => {
  assert.deepEqual(pick(SUPERVISED, { platform: 'darwin' }), { argv: BARE, scoped: false });
  assert.deepEqual(pick({ ROMP_CLI_SCOPE: '1' }, { platform: 'darwin' }), { argv: BARE, scoped: false });
});

// tmux is checked FIRST: a tmux-less box used to log "systemd-run could not start the tmux server in
// a scope … " at every start, because the scoped call failed on the missing tmux inside the scope.
test('tmux absent: null — nothing to start, nothing to log, whatever else is on PATH', () => {
  const systemdRunOnly = (name) => name === 'systemd-run';
  assert.equal(pick(SUPERVISED, { onPath: systemdRunOnly }), null);
  assert.equal(pick({ ROMP_CLI_SCOPE: '1' }, { onPath: systemdRunOnly }), null);
  assert.equal(pick({}, { onPath: () => false }), null);
  assert.equal(pick({}, { platform: 'darwin', onPath: () => false }), null);
});

test('the returned bare argv is a copy — a caller cannot mutate the constant', () => {
  const p = pick({});
  p.argv.push('x');
  assert.deepEqual(TMUX_START_ARGV, BARE);
});

test('commandOnPath finds an executable on the given PATH and nothing else', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-onpath-'));
  fs.writeFileSync(path.join(dir, 'systemd-run'), '#!/bin/sh\nexit 0\n', { mode: 0o755 });
  fs.writeFileSync(path.join(dir, 'not-exec'), 'x', { mode: 0o644 });
  const env = { PATH: ['', dir, '/nonexistent-dir'].join(path.delimiter) };
  assert.equal(commandOnPath('systemd-run', env), true);
  assert.equal(commandOnPath('not-exec', env), false);
  assert.equal(commandOnPath('missing', env), false);
  assert.equal(commandOnPath('systemd-run', { PATH: '' }), false);
  assert.equal(commandOnPath('systemd-run', {}), false);
});
