// romp-manager's default tmux server and the service cgroup (2026-09-05): the manager runs as a
// systemd user service with KillMode=control-group, so a tmux server it starts bare dies with
// `systemctl --user restart romp-manager`, and every session's tmux jobs die with it. On Linux with
// systemd-run on PATH the server now starts inside a transient scope of its own; everywhere else,
// and with ROMP_CLI_SCOPE=0, the bare call is unchanged. tmuxStartArgv is the pure argv choice.
// Run: node --test tests/manager-tmux-scope.test.js
'use strict';
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

process.env.ROMP_STATE_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-mgr-tmux-scope-'));
const { tmuxStartArgv, commandOnPath, TMUX_START_ARGV } = require(path.join(__dirname, '..', 'bin', 'romp-manager'));

const BARE = ['tmux', 'start-server', ';', 'set', '-g', 'exit-empty', 'off'];
const present = (name) => name === 'systemd-run';
const absent = () => false;

test('the bare tmux argv is the one the manager always used', () => {
  assert.deepEqual(TMUX_START_ARGV, BARE);
});

test('linux + systemd-run on PATH: the server starts inside a transient scope', () => {
  const pick = tmuxStartArgv({ platform: 'linux', env: {}, onPath: present, now: () => 1725000000000 });
  assert.equal(pick.scoped, true);
  assert.equal(pick.argv[0], 'systemd-run');
  for (const flag of ['--user', '--scope', '--quiet', '--collect']) assert.ok(pick.argv.includes(flag), flag);
  const unit = pick.argv.find((a) => a.startsWith('--unit='));
  assert.equal(unit, '--unit=romp-tmux-1725000000000');
  // the tmux argv rides after `--`, verbatim
  const dash = pick.argv.indexOf('--');
  assert.ok(dash > 0);
  assert.deepEqual(pick.argv.slice(dash + 1), BARE);
});

test('two picks get two unit names (systemd refuses a duplicate as "already loaded")', () => {
  let t = 1;
  const a = tmuxStartArgv({ platform: 'linux', env: {}, onPath: present, now: () => t++ });
  const b = tmuxStartArgv({ platform: 'linux', env: {}, onPath: present, now: () => t++ });
  assert.notEqual(a.argv.find((x) => x.startsWith('--unit=')), b.argv.find((x) => x.startsWith('--unit=')));
});

test('systemd-run absent: the bare call', () => {
  assert.deepEqual(tmuxStartArgv({ platform: 'linux', env: {}, onPath: absent }), { argv: BARE, scoped: false });
});

test('ROMP_CLI_SCOPE=0 turns the scope off even with systemd-run present', () => {
  assert.deepEqual(tmuxStartArgv({ platform: 'linux', env: { ROMP_CLI_SCOPE: '0' }, onPath: present }),
                   { argv: BARE, scoped: false });
});

test('darwin: the bare call, whatever is on PATH (launchd owns the lineage there)', () => {
  assert.deepEqual(tmuxStartArgv({ platform: 'darwin', env: {}, onPath: present }), { argv: BARE, scoped: false });
});

test('the returned bare argv is a copy — a caller cannot mutate the constant', () => {
  const pick = tmuxStartArgv({ platform: 'darwin', env: {}, onPath: present });
  pick.argv.push('x');
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
