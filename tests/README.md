# tests/ — every suite in one place

Every bug fix or feature change lands with a test (repo rule). Five suites:

- **`test_*.py`** (pytest) — the Python pipeline: event model, judges, kernel,
  backends, postal. They load the sources by file path through the stable
  `bin/` names with `from romp_load import load_source` (`tests/romp_load.py`,
  which reaches `kernel/loadsource.py`) and isolate state with `XDG_STATE_HOME`.
  The older `SourceFileLoader(...).load_module()` form is deprecated, with
  removal documented for Python 3.15: `tools/loadsource-sweep.py` rewrites a
  module still written that way (idempotent; `--check` reports without writing),
  and `test_state_isolation_order.py` refuses the call by file and line, naming
  that command. Both read the AST, so the idiom inside a string handed to a
  child process is a hand edit; so is the `sys.path` line a module needs before
  `from romp_load import load_source` when another test executes it by file
  path from outside this directory (`smoke_codex_live.py` carries one). Name
  every module `test_<stem>.py`: pytest also collects `<stem>_test.py`, but
  unittest's discovery (`test*.py`), the state-isolation check and the fixture
  scan in `test_postal_marker_form.py` take the `test_` prefix only, and
  `test_state_isolation_order.py` pins that.
  Every browser-driven served lab (a module that serves the dashboard from a copy of
  the built bundles) takes that copy from `lab_dist.copy_dist` (`tests/lab_dist.py`):
  one esbuild run per checkout state under a file lock, so xdist workers never copy
  a build in flight; the state is keyed on the trees `esbuild.js`'s exported configs
  name (node requires the module, which builds only as a script; no text scan), the
  config's own tree, and their imports. A checkout whose environment cannot build
  (the extension's node_modules absent, or esbuild failing) skips the served labs
  with the reason; the harness's own failures raise. The two pins that compare the
  derivation against the real tree run without node_modules too, through
  `tests/lab_dist_stub.py` (a node preload that stands in for a bare package the
  config itself requires and node cannot find, on a checkout with no node_modules
  beside the config, a dependency of the build and not of the exported data; a
  node_modules that exists and lacks the package makes it throw, and a skip
  inside its block is a failure). `tests/test_lab_dist.py`
  refuses a module that builds or copies dist on its own.
  Golden transcript fixtures: `test_romp_events_golden.py` + `fixtures/`.
  Run: `python3 -m pytest tests/ -q` (~20s; a stalled run is a hang, not slow).
  The `_HAVE_SDK`-gated classes in `test_sdk_backend.py` (OptionsAssembly, the
  runner and can_use_tool bridge suites) SKIP unless `claude_agent_sdk` imports,
  and a skip reads as green — to execute them, put romp's SDK venv on the path:
  `PYTHONPATH=~/.local/state/romp/sdkvenv/lib/python3.12/site-packages python3 -m
  pytest tests/test_sdk_backend.py -q` (the venv `bin/romp-sdk-setup` creates;
  match the python version to it).
  Under pytest-xdist (`python3 -m pytest tests/ -n 4`) two import-time effects of
  `tests/test_host_transport.py` decide what a red means. It puts that same SDK venv
  on `sys.path` at import (the kernel's own idiom), and every worker imports every
  collected module before it runs a test, so over the whole directory the SDK is
  importable in each worker from then on: the `_HAVE_SDK`-gated classes above RUN
  (the module alone, or beside one that leaves the path alone, skips them). Five of
  their cases (OptionsAssembly, FastModeReportedState, ApiRetryState twice,
  ReconnectReconcilesInflight) were red against the installed SDK that way until
  2026-09-16 and pass both ways now; judge the module both ways, plain and under the
  `PYTHONPATH` recipe. Its cases that build SDK
  options with a `can_use_tool` callback raise
  `claude_agent_sdk.types.CanUseToolShadowedWarning` (a `UserWarning` subclass); a
  worker ships the warning to the controller, whose venv cannot import the class, and
  xdist's `unserialize_warning_message` takes the run down with an INTERNALERROR.
  `conftest.py`'s `pytest_configure` ignores it by MESSAGE prefix
  (`ignore:can_use_tool will not be invoked:UserWarning`): pytest re-parses the
  entries at every application, and one naming a class it cannot import is dropped
  with a PytestConfigWarning (every worker until the venv path is inserted, the
  controller always, CI always); a module-level `warnings.filterwarnings` does not
  survive pytest's per-test `catch_warnings`. So `-p no:warnings` is no longer part of an
  `-n` run. One more import-time leak reached the postal suite the same way until
  2026-09-18: `tests/test_kernel_tunnels.py` set `ROMP_POSTAL_PEERS=0` at module
  level, the kernel and the postal service read it per call, and every worker imports
  every collected module before it runs a test, so in any run that collected the
  tunnels module `test_postal_via_dedupe.py`'s PeerRoutePrefersDirect resolve case
  answered an error instead of a relay and `test_kernel_remote_identity.py`'s absorb
  case missed its bus notice (5 of 6 full runs). The same shape, wider, on 2026-09-22
  (fork PR #813's CI, the 3.10 cell): a real postal bus started from the peer-notify
  guard test's revive road with the environment of the test process, which carried
  the tunnels module's module-level `ROMP_POSTAL_PORT` (the run's own, so the bus's
  fixed-port belt licensed the bind) and `ROMP_POSTAL_CLIENT_ONLY` (inert with peers
  on) and the `ROMP_SESSIONS_FILE` seam ten postal modules wrote at module level
  (one live row, so the bus never autostopped); it wrote into a shared state root
  every 30 s and turned another module's snapshot test red. What put the first write
  inside that test's 50 ms window on the cell stays unknown. Reading ruled out a kick,
  a restart road or a removal of `postal/` in the 21 modules between the bus-restore
  module and the asserting module (`server.pid` and `server.log` were not among the
  files added, so no bus started inside the window), but it read only those modules.
  It did not rule out one source that ran in every run at the round-1 head of fork
  PR #894 and showed in 4 of 5 CI cells. Every kernel a test module loads in-process read
  `BUS_PORT` 25302, the machine's fixed bus port, because conftest pops
  `ROMP_POSTAL_PORT`, so its bus calls reached whatever bus a developer's box runs
  there. The postal service loaded in-process built its client's `BASE` from the same
  popped name, and three set_working tests of `tests/test_postal_relay_honesty.py`
  sent heartbeats through it. Where nothing listened, the refused detach notify of
  three tests (`tests/test_kernel_known_hosts.py`'s two `KnownHostMemory` detach tests
  and `tests/test_peer_reconnect.py`'s `test_detach_is_the_one_end_of_intent`) revived
  the bus with a real `romp-postal-service ensure` from the test process; a revive
  still in flight absorbs a later one, so a run records two or three. This is closed
  now: conftest's `_dead_bus_port` gives every loaded `romp_kernel*` module a dead
  `BUS_PORT` and every loaded `romp_postal*` module a dead `BASE` for each test and
  puts them back after it, and the three detach tests stub the revive. The hermetic
  module's pin runs the modules whose calls dialled the fixed port
  (`BUS_DIALLING_MODULES`, derived by a spy over one full serial run) together in both
  orders under a connect and spawn spy, and asserts no connect to 25302 and no
  postal-service process. Two things would settle fork PR #813's cell: that spy over
  one serial run of its head, or `PYTEST_CURRENT_TEST` and the thread name logged
  beside the kernel's refusal line. The disclosure is conditional: a run carries
  the contaminant only when the revive wins the race AND a write lands in an asserting
  window; the witness is the leaked process the run's log names, with the test name
  when the spawn carried it. THE RULE, a property and
  not a list of names: **no test module writes an environment variable at module
  level that a spawned child could inherit**, outside a licensed set. A module-level
  write executes at COLLECTION and holds for every test in the process and for every
  child any test spawns, whether or not the writing module's own tests run
  (deselecting does not help). It has two halves, held differently.
  The import-time half is pinned for every `.py` under `tests/`, walked recursively
  so `fixtures/` is read too (the test checks its glob against an independent walk,
  so no file is silently unscanned), by `tests/test_hermetic_kernel_postal.py`: the
  set of names the test modules write in everything that EXECUTES AT IMPORT
  (module-level `if`, `try`, `for` and `with` bodies and their header expressions,
  class bodies, the decorators and default argument values of a def, the decorators
  and bases of a class, and the writes reached through a call at import the scan can
  resolve to a def or class under `tests/`: a module-local helper, a name imported
  from a tests-local module, by its dotted name or by a star import, a bare
  decorator, an instantiation), in every shape a write takes (a subscript assignment,
  `setdefault`, `update` of a dict literal, of keywords or of a module-level name
  bound to a dict literal, `|=`, `os.putenv`, the dunder spellings `__setitem__` and
  `__ior__` on the mapping or unbound with the mapping as the first argument, through
  `os.environ` or `os.environb` or any name bound to either, a subscript whose key a
  `for` over string literals binds), EQUALS the licensed set
  `LICENSED_MODULE_LEVEL_WRITES` there, an equality and never a floor, and every write
  meets its licence's condition. Outside the scan, named in the module above
  `_Module`: a callee it cannot resolve (product code loaded by path, the standard
  library, a method on an instance, a lambda, a name bound to a call's result,
  `exec`), and a write that reaches the mapping other than by a method called on it
  (`operator.setitem`, a bound method held in a name or fetched by `getattr`, a
  `functools.partial`, `posix.putenv`, an unbound `update` on the mapping's class,
  which the scan cannot tell from `saved.update(os.environ)`, a read). The licences
  are per name and checkable, each with a condition on
  the written value (read through a module-level name bound once, so
  `_ROOT = tempfile.mkdtemp()` is read as the mkdtemp): the state preamble
  (`XDG_STATE_HOME` a bare mkdtemp or one with a literal prefix, never a `dir=`;
  `ROMP_STATE_DIR` a private root of the same shape or the shell's value put back;
  `tests/test_state_isolation_order.py` mandates the preamble),
  `ROMP_SERVE_TOKEN` (a string literal, or the shell's value put back) and
  `ROMP_KERNEL_NO_OPEN` (the value "1"), the four of them dated 2026-09-22 and
  pointed at the class item fork PR #871 filed in the notes (import-time writers
  migrate into fixtures or the floor), the dead ports and the catalog, scope,
  claude-config and service-env floors (one value or a path under the module's
  root, and `tests/conftest.py` re-asserts the name in an autouse fixture, so the
  module value cannot outlive collection), and `ROMP_MODELS_URL` (read at kernel
  import, a dead loopback URL); a check over the table itself holds every licence to
  a per-write condition and every temporary one to a since date and a named item.
  The two floor modules, `tests/conftest.py` and `tests/__init__.py`, are the one
  home of run-wide values and are licensed wholesale, except for the five names a
  module-level write of which is the leak itself (the postal peers, port, client-only
  and host, and the sessions-file seam): of those a floor module may write only
  upstream's client-only floor of "1". A write whose keys the scan
  cannot read fails the test naming the file and line rather than passing unread. A
  module-level `pop` is outside that pin: unset is the production default and what a
  clean shell gives every module. Writes at a module's setup rather than its import
  (`setUpModule`, `setUpClass`, a module- or class-scoped fixture) are outside the
  census and checked by conftest's `_module_env_restored` for the names it watches
  (`MODULE_WATCHED_ENV_NAMES`: the seams below and the postal trio): it takes its
  snapshot before the module's `setUpModule`, `setUpClass` and module- and
  class-scoped fixtures run and fails naming the module when a watched name differs
  after the module's teardown (the port against its floor, unset, since conftest pops
  it before every test); every other name is outside it. conftest pops every watched
  name at import, so the developer's shell does not change what the check reads. A
  write by a session- or package-scoped fixture is never read by the per-test check,
  and is read by this one only when a later test of a module is the first to use the
  fixture: one first set up for a module's first test (an autouse one always is) runs
  before this check's snapshot, so both snapshots already carry its write. The tree
  has no fixture scoped above module, and the hermetic module holds that list at
  empty.
  `python -m tests.test_hermetic_kernel_postal --census` prints the counts by name
  and shape. The per-test half, set in setUp and put back by a cleanup registered
  right after the write (`restore_env` from `tests/conftest.py`, or a method of the
  class; a tearDown restore is skipped when a subclass's setUp fails part-way, and
  the value leaks the same way), is a convention and not a pinned rule, except for
  the tunnels module, whose placement the hermetic module checks by position: all
  three postal legs and the kernel's `BUS_PORT` (read at import) set in the setUp of
  every class that attaches or detaches, its `_ensure_postal_bus` revive road stubbed
  there with a recorder, all put back by cleanups, none at module level (a probe runs
  the stub: a revive after the setUp lands in the recorder, the cleanups fail on it and
  put the road back). The same shape leaked `ROMP_SESSIONS_FILE` from `test_postal_bus_lifetime.py`
  (a tearDown that put back only a prior value; fixed 2026-09-18 with a cleanup and a
  pin that runs the case). conftest's `_shared_state_restored` names such a leftover
  in any run, since no module writes the seam at import, and it watches the bus-name
  seam `ROMP_POSTAL_HOST` too; each fires only in a run where nothing set the name
  beforehand (a leftover equal to what an earlier test left is no change; the
  developer's shell never sets one, since conftest pops every name the two checks
  watch at import). The port the kernel reads at import used to be the
  one leg allowed before the load; since 2026-09-22 it is set per test beside
  `km.BUS_PORT`, and conftest pops `ROMP_POSTAL_PORT` before every test (the
  dead-port fixture), so a stray value never reaches a child; and since a kernel
  loaded at import then reads the machine's fixed bus port, conftest's
  `_dead_bus_port` gives every loaded kernel module a dead `BUS_PORT` for each test,
  and every loaded postal module a dead `BASE` (the unknown above). A red in one of these
  under `-n` is still judged by the module alone: `python3 -m pytest tests/<module>.py -q`.
- **No process of a run outlives the run** (2026-09-22). At the controller's session
  end `tests/conftest.py` reads `/proc` for every live process whose environment
  carries one of the run's temp roots (the controller's and its recorded children's,
  an xdist worker's or a nested pytest's) or a path under one, a `:`-joined value
  counted per component, or whose cwd is under one; it waits for the one event it can
  observe, each holder's exit, up to `LEAK_EXIT_BOUND_S` (5 s: a signalled child exits
  well inside it, a clean run pays nothing because the wait starts only when a holder
  is seen), and if any still hold a root the run is RED and each is named: pid,
  parent, command line, the names it holds the root through, and the test phase
  current at its spawn (`PYTEST_CURRENT_TEST` in the environment it inherited; a
  child a background thread spawns may carry a later phase or none, so the pid and
  the command line are the witness and the phase is a pointer when there is one).
  Keyed on that
  property, never on a binary's name: a postal bus, a kernel, a session host and a
  mock ssh's orphaned `sleep` are the same leak (the tunnels module's mocks `exec`
  their trailing sleep since the check found the orphans). The check never kills; it
  names the pid. Another user's process has an unreadable environ and is counted, not
  judged; a platform without procfs says so once and runs no check.
  `tests/test_run_end_leaked_processes.py` pins the scan, the wait, the roots and the
  red run end by execution, in a child pytest process.
- **`*.bats`** — the shell surfaces: `bin/romp`, the launch chain, hooks,
  postal CLI. Keep them GNU/BSD-portable (CI runs bats on ubuntu).
  Run: `bats tests/*.bats`.
  Any suite that starts the real manager or the launch chain floors
  `ROMP_CLI_SCOPE=0` in setup: under `ROMP_SUPERVISED` (set by the service's
  unit, and inherited by a tool shell under a self-hosted install) the kernel
  spawns session CLIs through `systemd-run --scope`, so such a suite would
  otherwise leave a transient scope on the developer's user manager. The
  floor is `load cli-scope-floor` and `cli_scope_floor` in setup()
  (`tests/cli-scope-floor.bash`; until 2026-09-11 it rode the retired
  terminal backend's socket-directory helper). pytest's floor is
  `conftest.py`; `test_cli_scope_floor.py` pins both halves of it on the
  source, since a test that reads the value cannot tell the floor from
  `test_cli_scope.py`'s own import-time set.
  `conftest.py` also unsets the four `ROMP_CLI_SCOPE_*` limit variables
  (`ROMP_CLI_SCOPE_MEMORY_MAX` and the others) and the kernel's
  `ROMP_CLI_SCOPE_OOM_POLICY_REJECTED` marker: the kernel hands them to every
  session's CLI and a tool shell inherits them, so a suite run from a session on
  a self-hosted install would otherwise see them at every backend construction
  and in every exact argv pin. The marker rides every launch (`1` or empty), so a
  self-hosted tool shell always carries it, unlike the limits, which need
  `service.env`.
  `conftest.py` and `__init__.py` set
  `ROMP_MANAGER_PORT`, `ROMP_KERNEL_PORT` and `ROMP_SERVE_PORT` to a dead port
  (never unset: to every reader an absent variable means the live default), so
  no test dials a live manager or kernel through an inherited value.
  Any suite that starts the real `bin/romp-manager` also gives it a state
  root of its own before its first `@test` (`unset ROMP_STATE_DIR` plus
  `export XDG_STATE_HOME="$TEST_DIR/state"`, or an exported
  `ROMP_STATE_DIR`), since the manager boots from its state root's
  `kernels.json` and reads the serve token there; `bats-state-isolation.bats`
  is the ratchet.
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
  `node --test tests/manager-*.test.js`. The runner runs the files
  concurrently, so a file that starts a real manager takes its ports from
  `tests/manager-ports.js` (`freePort(__filename)`), which owns a disjoint
  block per file and probes inside it; a listen-on-zero pick was handed to two
  files at once in the window between its close and the manager's bind.
  `manager-ports.test.js` pins the table against the files on disk, so a new
  `manager-*.test.js` needs a block there before it runs.
- **`ui-bench.test.mjs`** — the dashboard pane bench (`tools/ui-bench.mjs`):
  the classifier, synthesizer, temp-path guard, recording client, front
  server, Handler-subprocess isolation, in-page instrument, profile fold, and
  real headless replays of synthetic feed and timeline streams.
  Run `node --test tests/ui-bench.test.mjs` from the repo root after
  `cd vscode-extension && npm ci && npm run build`. The browser tests skip,
  saying why, when no Chromium, `python3` or dist is present;
  `ROMP_UI_BENCH_REQUIRE=1` (CI) turns that skip into a failure, and
  `ROMP_UI_BENCH_TIMING=1` (a quiet machine, never CI) also asserts the timing
  relations the replays otherwise report as diagnostics.

**Temp files and git are hermetic, suite-wide.** Two mechanisms, one per half,
both in `tests/__init__.py`, which every entry point imports first (pytest before
`conftest.py`, `python -m unittest tests.test_x` before the module; a direct
`python3 tests/test_x.py` gets it through the module's own `from romp_load
import load_source`: imported under its bare name by a `test_*.py` run as a
script, `tests/romp_load.py` puts the checkout on `sys.path` and imports the
package (since 2026-09-14), so that import goes above the state preamble in
every module, which `test_state_isolation_order.py` holds; only `cd tests &&
python -m unittest test_x` has neither). It wraps
`tempfile.mkdtemp` so every directory the test process mints is recorded and
removed when the run ends (under pytest at session end, under `python -m
unittest` at exit): the in-process half, covering the 300-odd module preambles
and the per-test `mkdtemp()` calls nobody cleans up. And it covers what that
hook cannot see — directories made by child processes (kernels, git, a shell's
`mktemp -d`), `mkstemp` files, `os.mkdir` paths — by pointing the process temp
dir (`tempfile.tempdir` and `TMPDIR`, so every child inherits it) at one private
`romp-tests-*` root under the system temp dir, removed whole when the run ends
(before both, a full run left ~5,600 entries in `/tmp` and over a million had
piled up; until 2026-09-14 the root was `conftest.py`'s, so a bare unittest run
had none, and one killed mid-run left everything it made loose; a direct run
imported no package at all, and one module's left 86 loose `tmp*` directories in
a fresh `TMPDIR`). `conftest.py`
keeps the pytest side of that removal, with a survivor named (below). A run that
dies before any removal (pytest-timeout's `os._exit`, a killed shell) leaves the
root standing, so the package also writes an owner marker,
`romp-tests-owner.json` naming the run's pid, into the root at mint time. The
kernel's boot reconcile (`sweep_dead_test_roots` in `kernel/sdk_backend.py`)
removes `romp-tests-*` roots under the system temp dir whose marker names a
dead pid, renaming each to `<name>.sweeping` before deleting it so a partial
delete leaves a tombstone the next boot finishes. A root without a marker (a
foreign directory, a pre-marker root) is never touched by the sweep.
`test_tempdir_hygiene.py`'s `BareRunLeavesNothing` runs a leaking module as a
child in each bare shape, `python -m unittest` and a direct script, finished and
killed, and counts what is left. Still
clean up what you create — `with tempfile.TemporaryDirectory()`,
`self.addCleanup(shutil.rmtree, ...)`, a `tearDownClass` for a class-level
fixture — so a fixture is gone when its test is, not at exit; bats suites use
`mktemp -d` in `setup` and `rm -rf` it in `teardown`, and stand in for any
subject that detaches work (a detached launcher probe once re-created four to
six test dirs per run by minting a serve-token after the teardown). Never give
a tempfile call a literal
directory as its `dir` — by keyword or position, composed (`f"/tmp/{x}"`,
`os.path.join("/tmp", x)`) or through a name bound to one — and never point
`mktemp` (`-p`, `--tmpdir`, a `TMPDIR=` prefix) at a path under `/tmp`: that
bypasses the redirect, and the hygiene test reads every test file for those
shapes. The tests that must leave the root (`tests/test_host_transport.py`'s
AF_UNIX socket paths, which would not fit `sun_path` under a long TMPDIR, and
`tests/test_session_host.py`'s padded socket roots, which `padded_root` builds
to an exact byte length for the budget cases) fall back to
`ROMP_TESTS_SYSTEM_TMPDIR`, the system temp dir the package recorded
once per run before redirecting (an xdist worker inherits the controller's
record), and remove what they made with an `addCleanup` (a directory outside
the root is outside the exit sweep's scope, so nothing else removes it; nine
per run leaked before). Under xdist a worker's root sits BESIDE the
controller's in that recorded dir, never inside it (2026-09-21): every
process's paths are one `romp-tests-XXXXXXXX` level (20 bytes) under the
handed dir whatever the worker count, so the deepest hosts-on lab's socket
path (`tests/test_session_host_restart.py`, `host-served-XXXXXXXX/xdg/romp/
hosts/<sid8>.sock`) is TMPDIR + 70 bytes and a run's TMPDIR may be up to 37
bytes (the nesting before it cost a second level: 107 = `SOCK_PATH_MAX` exactly
at 17 bytes under `-n`; at 18 that lab's test, ServedRestart, overflowed under
xdist while it passed alone, and the TMPDIR + 72 shapes — HostProcess, EndToEnd,
AttachStandDown, a bare mkdtemp root — overflowed from a 36-byte TMPDIR under
`-n`). A nested process lists its pid and root in
`<parent root>/romp-tests-children`; the parent removes a dead child's root at
run end, so a worker killed mid-run leaks nothing. `tests/test_tempdir_hygiene.py`
`HarnessSocketBudget` derives the bound from the roots the harness makes and
the tests' own lab shapes, and from the same scan holds the longest directory
path and the longest single component the harness can produce under xdist
nesting against `PC_PATH_MAX` and `PC_NAME_MAX` (every shape has its own
ceiling; the socket is one). A root that cannot be removed at run end (a child
still writing under it, a 000-mode directory a test left behind) is named on
stderr: `[tests] not removed at run end: <path>`, instead of the run ending
green over it. The same conftest gives git no global or system config
(`GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`) and a synthetic identity through
`GIT_AUTHOR_*` / `GIT_COMMITTER_*`; bats suites that run git get the same from
`load git-hermetic` + `git_hermetic` in `setup`, with a global config file of
the floor's own in place of none. That floor also forbids background git work:
the five no-background keys of `tests/git_fixture.py` (below) ride the
environment as `GIT_CONFIG_COUNT` pairs, inherited by every git a test, a script
under test or a hook runs, and sit in the floor's global file, which receive-pack
in a bare fixture remote reads (a push over a local path starts it without the
pairs); so no detached `git maintenance` writes into a fixture repo while its
teardown removes it. A fixture must not depend on the developer's git
configuration (CI has none), and the env identity outranks
`git config user.*` and `-c user.*` — a test that must pin a particular author
exports its own `GIT_AUTHOR_*` after the floor. `tests/test_tempdir_hygiene.py`
and `tests/git-hermetic.bats` pin all of it.

**A fixture that builds a throwaway git repository runs git through
`tests/git_fixture.py`** (`from git_fixture import git, init_repo,
forbid_background`, registered under the bare name like `romp_load`). Every
command it runs carries `-c` flags that forbid background work
(`maintenance.auto`, `maintenance.autoDetach`, `gc.auto`, `gc.autoDetach`,
`core.fsmonitor`), `init_repo` writes the same keys into the repo's own config,
and `forbid_background` does so for a clone or worktree the kernel will run git
against: `git commit`, fetch and merge spawn `git maintenance run --auto`,
which on recent git detaches from its parent and can still be writing into
`.git` while the fixture's `TemporaryDirectory` removes the repo (the CI flake
`Directory not empty: '.git'` from `rmtree`, 2026-09-10). A file keeps its own
thin runner (its identity, timeout and return shape) and delegates the body;
read-only git against the real checkout stays a plain `subprocess.run`.
`tests/test_git_fixture.py` pins the runner with git's own trace: a commit
through it, and a plain fetch in a `forbid_background` clone, spawn no
maintenance or gc child.

**A served-page class copies the built `vscode-extension/dist/` with
`lab_dist.copy_dist` (the locked shape the fork keeps, described above), never
`shutil.copytree` and never `tests.dist_copy.copy_dist` directly.** Under
`pytest -n` a sibling class's build renames or removes its staging files
(`.<name>.tmp-<pid>-<n>`, `stagingPath` in `esbuild.js`) between the listing
and the copy, and a plain copytree raises `shutil.Error` before the class's
first test; the copy skips that shape. `tests/test_dist_copy_staging.py` pins
the copy and refuses a raw copytree of dist in any test module, and
`tests/test_lab_dist.py` refuses a `dist_copy` caller outside its allowlist.

**No test report shows a process-environment value or a credential-shaped
token.** An assertion whose container is an environment mapping prints the
whole mapping when it fails (`assertNotIn("X", os.environ)` renders every
variable), and on a developer's machine that mapping can hold a live key. The
fix is to test membership and name the key; the report hook in
`tests/conftest.py` is the net for an assertion still written the other way.
It redacts two things from every report's text and captured-output sections,
whatever the outcome (so `-rA`/`-rP` output for passed tests too), and from
collection reports: a value present in the process environment that is 16
characters or longer becomes `[REDACTED-ENV-VALUE]`, whole, per
whitespace-separated chunk, and per piece left beside a cut pytest or
unittest made (`'<head>...<tail>'`, `[N chars]`) when that piece is a
substring of the value (values are noted at the moment they are written
into `os.environ`, so one set inside `mock.patch.dict` and gone before the
assertion is caught too; exempt, never when the name is credential-shaped,
are path-valued names such as `PWD`, `HOME`, `TMPDIR` and the interpreter
paths GitHub Actions exports, the names whose values are public, the ones
GitHub Actions describes a run in (`GITHUB_REF`, `GITHUB_REPOSITORY`,
`GITHUB_ACTOR` and the rest) and the conftest's own synthetic git identity,
the `XDG_*` and `PYTEST_*` families, and any value that is an absolute path
this machine has), and a credential-shaped token becomes
`[REDACTED-CREDENTIAL]` wherever it came from, by the patterns in
`tests/credential_patterns.py` (public key prefixes, a JWT by its shape, a
long token where a value sits, pytest's own renderings of a failed comparison
included; a named git sha and a dated Anthropic model id are left alone). A
report the hook changes is rebuilt from the scrubbed text with
its crash location kept, so the short test summary still ends in the
assertion message; that report loses pytest's colour and source highlighting.
One it leaves alone keeps pytest's own rendering.
`tests/test_env_value_redaction.py` pins the rule, the write-time capture,
the patterns, the scrub's cost and the hook end to end.

**A lab kernel's environment is built from a list of names, and the file a
relaunch reads from carries a shorter list.** Every module that boots a hermetic
kernel (`bin/romp-kernel` under a lab's own `XDG_STATE_HOME`,
`CLAUDE_CONFIG_DIR` and `ROMP_DIST_DIR`, at a free port with a synthetic serve
token) builds its environment with `kernel_env` in `tests/test_ship_reship_served.py`,
never from a copy of the runner's. A run from a shell on a machine running romp
carries the live kernel's exports, and a lab kernel that inherited them exited
when the live manager restarted (`ROMP_MANAGER_PID`, the kernel's parent-death
watchdog), bound where the live kernel serves (`ROMP_SERVE_HOST`) and dialled
the machine's postal bus, or started one that nothing stops. From the runner
`kernel_env` takes `PATH`, `HOME`, the `XDG_*` names and, of the floor
the suite sets for the run's children (`TMPDIR` the tests package's since
2026-09-14, the rest `tests/conftest.py`'s), `TMPDIR`,
`GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`, `ROMP_SERVICE_ENV_FILE`,
`ROMP_SERVICE_ENV`, `ROMP_CLAUDE_BIN` and `ROMP_CLI_SCOPE`; over those go the
lab's roots and seams, any seam the lab adds by keyword, and a postal bus of its
own that is never started (`ROMP_POSTAL_PORT` at a free port,
`ROMP_POSTAL_PEERS=0`, `ROMP_POSTAL_CLIENT_ONLY=1`). The served labs whose
driver kills and relaunches the kernel (`test_ship_reship_served.py`,
`test_dashboard_reload_served.py`) write the relaunch's command, environment and
log to the lab's `cfg.json` through `relaunch_cfg`, and the environment in that
file is narrowed once more by `relaunch_env`: the `ROMP_*` and `XDG_*` names,
`CLAUDE_CONFIG_DIR`, `PATH`, `HOME`, `TMPDIR`,
`GIT_CONFIG_GLOBAL` and `GIT_CONFIG_NOSYSTEM`, less the `ROMP_TESTS_*` names,
which the tests package (conftest until 2026-09-14) exports for the run's own tests (such as
`ROMP_TESTS_SYSTEM_TMPDIR` above) and no kernel reads. Nothing else a lab put in
its kernel's environment reaches the file; each served lab plants a probe name
in that environment and checks the written file for its absence. To give a lab
kernel another name of the runner's, add the name to the list with its reason
beside it. `LabKernelEnv` and `RelaunchEnv` in `tests/test_ship_reship_served.py` pin
both functions; the served legs check the file itself.

`fixtures/` must stay SYNTHETIC: invented prompts, placeholder UUIDs, hostname
`TESTHOST` — never real session data.
