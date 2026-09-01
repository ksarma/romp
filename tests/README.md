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
- **node suites** — live beside their sources in `ui/webview/*.test.ts` and
  `vscode-extension/src/*.test.ts`, run with `npm test` from
  `vscode-extension/`. Many pin lines of `kernel/kernel.py` as strings — run
  BOTH this and pytest on every kernel change.
- **`manager-*.test.js`** — the node supervisor (`bin/romp-manager`): restart
  gating, the kernel registry, and the drain-poll handshake. Run:
  `node --test tests/manager-*.test.js`.

`fixtures/` must stay SYNTHETIC: invented prompts, placeholder UUIDs, hostname
`TESTHOST` — never real session data.
