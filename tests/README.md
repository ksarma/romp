# tests/ — every suite in one place

Every bug fix or feature change lands with a test (repo rule). Four suites:

- **`test_*.py`** (pytest) — the Python pipeline: event model, judges, kernel,
  backends, postal. They load the sources by file path via `SourceFileLoader`
  (through the stable `bin/` names) and isolate state with `XDG_STATE_HOME`.
  Golden transcript fixtures: `test_romp_events_golden.py` + `fixtures/`.
  Run: `python3 -m pytest tests/ -q` (~20s; a stalled run is a hang, not slow).
  The `_HAVE_SDK`-gated classes in `test_sdk_backend.py` (OptionsAssembly, the
  runner and can_use_tool bridge suites) SKIP unless `claude_agent_sdk` imports,
  and a skip reads as green — to execute them, put romp's SDK venv on the path:
  `PYTHONPATH=~/.local/state/romp/sdkvenv/lib/python3.12/site-packages python3 -m
  pytest tests/test_sdk_backend.py -q` (the venv `bin/romp-sdk-setup` creates;
  match the python version to it).
- **`*.bats`** — the shell surfaces: `bin/romp`, the launch chain, hooks,
  postal CLI. Keep them GNU/BSD-portable (CI runs bats on ubuntu).
  Run: `bats tests/*.bats`.
  Any test whose subject shells out to tmux must isolate the tmux socket
  directory: `load tmux-private`, `tmux_private_socket_dir "$TEST_DIR"` in
  setup (it exports `TMUX_TMPDIR` under the test dir and creates it first;
  tmux 3.4 silently uses the machine's default socket directory when
  `TMUX_TMPDIR` names a missing one), and `tmux_private_kill && rm -rf
  "$TEST_DIR"` as the last line of teardown (the kill fails when the
  directory is already gone, since a server started under it has then
  leaked; it has to be teardown's final status, because bats swallows a
  failing command mid-teardown). A tmux mock on PATH
  covers only the tests that install one: on 2026-09-06 a full bats run
  ran `romp-manager-ensure.bats` while the machine's default tmux server
  was down, the real manager it starts ran `tmux start-server` on the
  default socket, and for the rest of the day the machine's tmux server was
  the test's, carrying the run's environment inside the service's cgroup.
  The same helper call floors `ROMP_CLI_SCOPE=0`: under `ROMP_SUPERVISED`
  (set by the service's unit, and inherited by a tool shell under a
  self-hosted install) `bin/romp-manager` starts that server through
  `systemd-run --scope` and the kernel spawns session CLIs the same way, so
  a suite that starts the real manager would otherwise leave a transient
  scope on the developer's user manager. Every suite that isolates tmux
  inherits the floor; `romp-manager-tmux-scope.bats` turns the switch back
  on only behind a fake `systemd-run` first on PATH. pytest's floor is
  `conftest.py`; `test_cli_scope_floor.py` pins both halves of it on the
  source, since a test that reads the value cannot tell the floor from
  `test_cli_scope.py`'s own import-time set.
  Any test whose subject binds a loopback port picks it with `load
  free-port` + `free_port VAR...`, never a literal: a literal shared by two
  files collided within one run (`romp-manager-ensure.bats` once used
  `romp-manager-origin.bats`'s control port), and any literal collides when
  two checkouts run bats at once on one machine. The helper picks below
  the ephemeral range, so a transient source port cannot hold the pick.
- **node suites** — live beside their sources in `ui/webview/*.test.ts` and
  `vscode-extension/src/*.test.ts`, run with `npm test` from
  `vscode-extension/`. Many pin lines of `kernel/kernel.py` as strings — run
  BOTH this and pytest on every kernel change.
- **`manager-*.test.js`** — the node supervisor (`bin/romp-manager`): restart
  gating, the kernel registry, and the drain-poll handshake. Run:
  `node --test tests/manager-*.test.js`.

`fixtures/` must stay SYNTHETIC: invented prompts, placeholder UUIDs, hostname
`TESTHOST` — never real session data.
