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
  case missed its bus notice (5 of 6 full runs). The tunnels module now sets the value
  per test (a setUp that saves what it found and registers the restore as a cleanup; a
  tearDown restore is skipped when a subclass's setUp fails part-way, and the value
  leaks the same way), both readers pin the default the same way (review round 2,
  2026-09-18, moved their restores, `RemoteIdentity`'s and the dedupe module's
  `_Seeded`'s, from tearDown onto a cleanup too, each with an executed pin that runs a
  subclass setUp that raises), and `tests/test_hermetic_kernel_postal.py` holds the
  placement. The rule from now on has two halves, held differently. The import-time half
  is pinned for every `.py` under `tests/`, walked recursively so `fixtures/` is read too
  (941 files on 2026-09-18: 925 `test_*.py`, 13 helpers beside them and 3 under
  `fixtures/`; the test checks its glob against an independent walk, so no file is
  silently unscanned): no module-level write of `ROMP_POSTAL_PEERS`, module-level `if`,
  `try`, `for` and `with` bodies included, in every shape a write takes (a subscript
  assignment, `setdefault`, `update` of a dict literal, of keywords or of a module-level
  name bound to a dict literal, `|=`, `os.putenv`, through `os.environ` or any name bound
  to it), and a write whose keys the scan cannot read fails the test naming the file and
  line rather than passing unread (review round 2: the subscript and `setdefault` alone
  had left a module-level `update` invisible). A module-level `pop` is outside that pin:
  unset is the production default and what a clean shell gives every module. The
  per-test half, set in setUp and put back by a cleanup registered right after the write
  (`restore_env` from `tests/conftest.py`, or a method of the class), is a convention and
  not a pinned rule: the hermetic module checks it for the tunnels module alone. The same
  shape leaked `ROMP_SESSIONS_FILE` from `test_postal_bus_lifetime.py` (a tearDown that
  put back only a prior value; fixed 2026-09-18 with a cleanup and a pin that runs the
  case). conftest's
  `_shared_state_restored` names such a leftover, but only in a run that collects no
  module writing the seam at import, so the module alone is the run that shows it.
  `ROMP_POSTAL_PORT` is the one postal leg the kernel reads at import, and it stays
  before the load. A red in one of these under `-n` is still judged by the module alone:
  `python3 -m pytest tests/<module>.py -q`.
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
- **`romp-service-differential.py`**, a documented command, not a test: the
  unit oracle in `romp-service.bats` (`_sd`, a python that reads a unit the
  way systemd 255 does) run against the real `systemd-analyze --user verify`,
  offline, over the fixture set round 4 of fork PR #778's review used as a lens
  (684 synthetic units: every specifier letter on three surfaces, the escape
  set on six, the ExecStart forms) plus a small batch the fold added and its
  addendum added to (the accepted side of each refused Unicode range, the last
  plane's noncharacters, the 255-byte name and component, the continuation
  shapes a comment, a blank or a whitespace-only line follows). It needs
  a `systemd-analyze` on PATH and exits 2 saying so when there is none; it
  never skips, and it is not a bats case because its counts are a claim about
  one systemd build (a mac has no systemd-analyze, and a runner's build may
  differ from the one below), so a case that must fail loudly without one
  would fail every mac run and go red on a build change with no change here.
  Run it when the oracle or the reader in `bin/romp-service` changes:
  `python3 tests/romp-service-differential.py` (about ten seconds, four
  verify runs at a time; `--list` prints the fixtures without running).
  A disagreement in the dangerous direction (the oracle reporting what
  systemd does not set, run or read: a value systemd leaves unset or sets to
  something else, a unit systemd fails to load, as many commands or
  EnvironmentFile paths as systemd's or more with a difference among them,
  another exec path) is a defect in the oracle, and where the reader follows
  the oracle, in the reader; the other direction (the oracle refusing or
  leaving unset what systemd sets, or listing fewer commands or files) is a
  false refusal. Until fork PR #778's round-5 preface the mark covered
  systemd-unset-oracle-set, more commands and more files alone, so a value
  both set and different, the direction's worst member since it is
  confidently wrong, went unmarked.
  Taken against `systemd 255 (255.4-1ubuntu8.17)` at the fold head
  (2026-09-19; 256 may move any class, and a different build prints a notice
  beside the counts):

  | class | cases | agree | REFUSES | DISAGREE |
  |---|---|---|---|---|
  | A (% before a non-alphanumerical character) | 31 | 31 | 0 | 0 |
  | B (the deprecated %c %r %R) | 9 | 0 | 9 | 0 |
  | C (\u noncharacter escapes) | 8 | 8 | 0 | 0 |
  | D (\U surrogate or noncharacter escapes) | 42 | 42 | 0 | 0 |
  | E (a trailing backslash on the last line) | 2 | 2 | 0 | 0 |
  | F (the @ prefix's argv) | 7 | 7 | 0 | 0 |
  | G (repeated or conflicting prefixes) | 8 | 8 | 0 | 0 |
  | H (a quoted or escaped ; argument) | 3 | 3 | 0 | 0 |
  | I (filename and path validity) | 4 | 4 | 0 | 0 |
  | J (the simplified exec path) | 3 | 3 | 0 | 0 |
  | K (the - prefix's downgrade) | 8 | 8 | 0 | 0 |
  | (none) | 559 | 421 | 138 | 0 |
  | total | 684 | 537 | 147 | 0 |

  REFUSES is the oracle raising NotImplementedError on a form it does not
  model (a specifier whose value is the host's, the cgroup's or the unit
  path's), not a disagreement; the fold batch agreed 10 of 10 at the fold
  head, 27 of 27 with the addendum's 17, and 35 of 35 with the round-5
  preface's 8 EnvironmentFile forms (a doubled slash, a `.` component, a
  trailing slash with and without the `-` prefix, a trailing `.` component,
  `//`, and a `..` component in two places, which systemd ignores as not
  normalized; the oracle models `path_simplify_and_warn` for
  `EnvironmentFile=` since that commit, where it raised on a doubled slash,
  `/./` and a trailing slash and, unguarded, read `/x/env/.` as written and a
  `..` path as a file: 3 dangerous rows against the previous oracle). Pasted
  from its run: `fold batch: 35 cases, 35 agree, 0 REFUSES, 0 DISAGREE, 0
  dangerous`; the dangerous-direction count is 0. Before the fold the lens
  counted 421 agree, 138 REFUSES and 125 DISAGREE over the same 684.
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
shapes. The tests that must leave the root — `tests/test_host_transport.py`'s
AF_UNIX socket paths, which would not fit `sun_path` under a nested root — fall
back to `ROMP_TESTS_SYSTEM_TMPDIR`, the system temp dir the package recorded
once per run before redirecting (an xdist worker inherits the controller's
record), and remove what they made with an `addCleanup` (a directory outside
the root is outside the exit sweep's scope, so nothing else removes it; nine
per run leaked before). A root that cannot be removed at run end (a child
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
