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
  `TMUX_TMPDIR` names a missing one), and `tmux_private_kill` in teardown
  before the `rm -rf` (it fails the test if the directory is already gone,
  since a server started under it has then leaked). Tests that start the real
  `bin/romp-manager` must also floor `ROMP_CLI_SCOPE=0`, so the manager never
  starts a transient systemd scope on the live user manager; the hook suites
  need not. A tmux mock on PATH covers only the tests that install one: on
  2026-09-06 a sweep ran `romp-manager-ensure.bats` while the machine's
  default tmux server was down, the real manager it starts ran `tmux
  start-server` on the default socket, and for the rest of the day the
  machine's tmux server was the test's, carrying the sweep's environment
  inside the service's cgroup.
- **node suites** — live beside their sources in `ui/webview/*.test.ts` and
  `vscode-extension/src/*.test.ts`, run with `npm test` from
  `vscode-extension/`. Many pin lines of `kernel/kernel.py` as strings — run
  BOTH this and pytest on every kernel change.
- **`manager-*.test.js`** — the node supervisor (`bin/romp-manager`): restart
  gating, the kernel registry, and the drain-poll handshake. Run:
  `node --test tests/manager-*.test.js`.

**Temp files and git are hermetic, suite-wide.** `tests/conftest.py` points the
process temp dir (`tempfile.tempdir` and `TMPDIR`, so every child the tests
spawn inherits it) at one private `romp-tests-*` root under the system temp dir
and removes the root when the run ends, so a `mkdtemp()` a test never cleans up
cannot outlive the run (before this, a full run left ~5,600 entries in `/tmp`
and 1.8 million had piled up). Still clean up what you create — `with
tempfile.TemporaryDirectory()`, `self.addCleanup(shutil.rmtree, ...)`, or the
module-level `atexit.register(shutil.rmtree, ...)` line after a preamble's
`mkdtemp()` — so a module is also correct under a bare unittest run, where
conftest never loads; bats suites use `mktemp -d` in `setup` and `rm -rf` it in
`teardown`. The same conftest gives git no global or system config
(`GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`) and a synthetic identity through
`GIT_AUTHOR_*` / `GIT_COMMITTER_*`; bats suites that run git get the same from
`load git-hermetic` + `git_hermetic` in `setup`. A fixture must not depend on
the developer's git configuration (CI has none), and the env identity outranks
`git config user.*` and `-c user.*` — a test that must pin a particular author
exports its own `GIT_AUTHOR_*` after the floor. `tests/test_temp_hygiene.py`
and `tests/git-hermetic.bats` pin both.

`fixtures/` must stay SYNTHETIC: invented prompts, placeholder UUIDs, hostname
`TESTHOST` — never real session data.
