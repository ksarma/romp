"""A test run leaves nothing in the system temp dir, and its git reads none of the developer's
configuration (2026-09-06).

Two mechanisms, one per half, both in tests/__init__.py (the second was conftest.py's until
2026-09-14). The package wraps tempfile.mkdtemp so every directory the test process mints is
recorded and removed when the run ends (under pytest at session end, under `python -m unittest` at
exit): that is the in-process half, and it covers the 300-odd module preambles and the per-test
mkdtemp calls nobody cleans up. And it covers what the hook cannot see — directories made by child
processes (kernels, git, a shell's `mktemp -d`), mkstemp files, os.mkdir paths — by pointing the
process temp dir (tempfile.tempdir and TMPDIR, so children inherit it) at one private
`romp-tests-*` root, minted before its own state dir so that dir sits inside, marked with the
owning pid for the kernel's dead-run sweep, and removed whole at exit; tests/conftest.py keeps the
pytest side of that removal, at run end with a survivor named. Before both, a full run left ~5,600
entries in /tmp and over a million had piled up; while the root was conftest's, a bare run
(`python -m unittest tests.test_x`) had no redirect and no marker, so every child's `mktemp -d`
and every mkstemp file landed loose in the system temp dir, and a run killed mid-test left
everything it made there, unsweepable. The same conftest points git at no global or system config
(GIT_CONFIG_GLOBAL, GIT_CONFIG_NOSYSTEM) with a synthetic identity: the seed commits had been
running the developer's global pre-commit hook.

Pinned five ways. Hygiene (the hook): it is installed, and a child run of this module under pytest
and under unittest leaves neither the directory it made nor its state root (ROMP_HYGIENE_MARKER
names the file where the child writes both paths). From inside a run, under either entry point:
the floors are in place and children inherit them, and no test pins a temp path to a literal
directory; under pytest, a root that survives removal is named on stderr, and a global and a
system hooksPath cannot reach a fixture commit. End to end: a nested pytest on a leaking module
leaves the system temp dir it was given exactly as it found it, serial and under xdist. Bare, end
to end, in both shapes: a child run of a leaking module shaped like `python -m unittest tests.test_x`
(the package first) and one shaped like `python3 tests/test_x.py` (nothing before the module; its
`from romp_load import load_source` is where the direct run's floor comes from, since 2026-09-14) each
leave their system temp dir as they found it, and killed mid-test each leave exactly one marked root,
which the kernel's sweep removes. And the socket path budget (2026-09-21): under xdist a worker's root
sits BESIDE the controller's in the recorded system temp dir, never inside it, so every process spends
one `romp-tests-XXXXXXXX` level; HarnessSocketBudget proves the placement by execution (a worker-shaped
process minted against a controller-shaped root, a killed one cleaned by its parent) and DERIVES the
longest hosts-on socket path the harness can produce — the level measured on roots it makes, the lab
shapes read from the tests' own text by AST, the socket tail from the kernel's builders — against the
kernel's SOCK_PATH_MAX, with the margin in the message and a red check on planted inputs. The
conftest-only classes skip under a bare unittest run, where conftest never loaded and there is nothing
to pin; the rest run either way. This module loads romp code in two tests only (the sweep and the
budget), never at import.
"""
import ast
import collections
import contextlib
import glob
import importlib.util
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
import uuid
from unittest.mock import patch

from git_fixture import git, init_repo

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
if "tests" not in sys.modules:
    # A direct script run (`python3 tests/test_tempdir_hygiene.py`) never imports the tests package, so
    # the mkdtemp hook and the temp root would be absent: the first Hygiene check failed and the child
    # runs left two romp-hygiene-* directories behind (the #944 review). Since 2026-09-14 a direct run
    # gets the package from the module's `from romp_load import load_source` (tests/romp_load.py), but
    # this module makes that import inside one test only, after every module-level line, so it imports
    # the package here itself, ahead of the preamble below, so that preamble's directory is tracked and
    # inside the root rather than the one leak this module makes itself; the package also floors
    # XDG_STATE_HOME, as for a unittest run.
    sys.path.insert(0, ROOT)
    import tests  # noqa: F401
# Hermetic state BEFORE the one load this module makes (kernel/sdk_backend.py, inside BareRunLeavesNothing):
# never at import, but tests/test_state_isolation_order.py reads the file, not the run, and these cost nothing.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
IDENT = "romp tests <tests@example.invalid>"

under_conftest = unittest.skipUnless("tests.conftest" in sys.modules,
                                     "the floors under test are tests/conftest.py's (pytest-only)")


def _run(cmd, **kw):
    # T299: a git handed a cwd runs against a FIXTURE repository here and goes through the suite's shared runner
    # (tests/git_fixture.py), which forbids BACKGROUND work on every invocation: `git commit` spawns
    # `git maintenance run --auto`, which on recent git detaches and can still be writing into .git while the
    # TemporaryDirectory removes the repo (the CI flake "Directory not empty: '.git'",
    # tests/test_restart_classifier.py, 2026-09-10). A git with no cwd reads the checkout running the tests, or
    # no repository at all (`--version`, `config --global --list`), and stays the plain run it was.
    if cmd[0] == "git" and "cwd" in kw:
        return git(kw.pop("cwd"), *cmd[1:], check=kw.pop("check", False), timeout=60, **kw)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kw)


MARKER_ENV = "ROMP_HYGIENE_MARKER"


class Hygiene(unittest.TestCase):
    def test_mkdtemp_is_tracked_in_process(self):
        self.assertTrue(getattr(tempfile.mkdtemp, "romp_tracked", False),
                        "the tests package's mkdtemp hook is not installed")
        marker = os.environ.get(MARKER_ENV)
        if marker:                                   # child mode: leave the evidence the parent checks
            d = tempfile.mkdtemp(prefix="romp-hygiene-child-")
            self.assertTrue(os.path.isdir(d))
            with open(marker, "w") as fh:
                fh.write(d + "\n" + os.environ["XDG_STATE_HOME"] + "\n")

    def _run_child(self, argv):
        scratch = tempfile.mkdtemp(prefix="romp-hygiene-")      # tracked: swept when THIS session ends
        marker = os.path.join(scratch, "paths.txt")
        env = dict(os.environ, **{MARKER_ENV: marker})
        r = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(marker) as fh:
            made, state_root = fh.read().split("\n")[:2]
        self.assertTrue(made and state_root, "the child left no evidence")
        self.assertFalse(os.path.exists(made), "the child's mkdtemp directory survived: " + made)
        self.assertFalse(os.path.exists(state_root), "the child's state root survived: " + state_root)

    @unittest.skipIf(os.environ.get(MARKER_ENV), "child mode")
    def test_pytest_child_session_removes_its_dirs_and_state_root(self):
        self._run_child([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:anyio",
                         "tests/test_tempdir_hygiene.py::Hygiene::test_mkdtemp_is_tracked_in_process"])

    @unittest.skipIf(os.environ.get(MARKER_ENV), "child mode")
    def test_unittest_child_run_removes_its_dirs_and_state_root(self):
        self._run_child([sys.executable, "-m", "unittest", "-q",
                         "tests.test_tempdir_hygiene.Hygiene.test_mkdtemp_is_tracked_in_process"])


class PrivateTempRoot(unittest.TestCase):
    """Not under_conftest: the root is the package's, so these hold under `python -m unittest` too."""

    def test_the_process_temp_dir_is_the_private_root(self):
        root = tempfile.gettempdir()
        self.assertTrue(os.path.basename(root).startswith("romp-tests-"), root)
        self.assertTrue(os.path.isdir(root))
        self.assertEqual(os.environ.get("TMPDIR"), root, "children find the root through TMPDIR")

    def test_module_level_state_roots_land_inside_it(self):
        # Whichever module's preamble wrote XDG_STATE_HOME last at collection, it minted the dir
        # after the package redirected the temp root, so it sits inside; so does the package's own.
        root = tempfile.gettempdir()
        xdg = os.environ["XDG_STATE_HOME"]
        self.assertEqual(os.path.commonpath([root, xdg]), root, xdg)
        pkg = sys.modules["tests"]
        self.assertEqual(os.path.realpath(root), os.path.realpath(pkg.TMP_ROOT))
        self.assertEqual(os.path.commonpath([root, pkg.STATE_DIR]), root, pkg.STATE_DIR)
        self.assertTrue(os.path.isdir(pkg.STATE_DIR), pkg.STATE_DIR)

    def test_children_inherit_the_root(self):
        root = tempfile.gettempdir()
        py = _run([sys.executable, "-c", "import tempfile, sys; sys.stdout.write(tempfile.gettempdir())"])
        self.assertEqual(py.stdout, root, "a Python child's tempfile answers with the root")
        with self.subTest(child="mktemp -d"):
            if sys.platform == "darwin":
                # macOS mktemp(1) with no template names its directory from the per-user temp root (the Darwin
                # confstr), not from TMPDIR, so the shell half cannot hold there; no product script relies on it
                # (bin/romp-serve and bin/romp-uninstall hand mktemp an explicit template under a dir they choose)
                self.skipTest("macOS mktemp(1) without a template ignores TMPDIR")
            sh = _run(["mktemp", "-d", "-u"])   # -u: name only, nothing created
            self.assertEqual(os.path.dirname(sh.stdout.strip()), root, "a shell's mktemp -d lands in it")

    def test_the_handed_temp_dir_is_recorded_once_and_every_root_sits_directly_under_it(self):
        # The one sanctioned way out of the root (tests/test_host_transport.py's two reads, in
        # TransportOverSocket._path and BackendHostRules._be, for an AF_UNIX socket path that
        # would not fit sun_path; and tests/test_session_host.py's system_tmp, for the padded
        # socket roots its budget cases build to an exact byte length) goes to the dir the RUN
        # was handed, never to a literal system path. Recorded once, and every process's root sits
        # DIRECTLY in it: a nested process (an xdist worker, handed the controller's root as its
        # TMPDIR) mints BESIDE its parent, never inside (2026-09-21; until then a worker's root
        # nested one level deeper, and the level cost the AF_UNIX socket path 20 bytes —
        # HarnessSocketBudget has the arithmetic). A nested process also tells its parent where it
        # minted, so the parent can remove the root of a child that died without its hooks.
        pkg = sys.modules["tests"]
        handed = os.environ.get("ROMP_TESTS_SYSTEM_TMPDIR")
        self.assertTrue(handed, "the package records the temp dir it replaced")
        self.assertEqual(handed, pkg.SYSTEM_TMPDIR)
        handed, root = os.path.realpath(handed), os.path.realpath(tempfile.gettempdir())
        self.assertFalse(os.path.basename(handed).startswith("romp-tests-"), handed)
        self.assertTrue(os.path.basename(root).startswith("romp-tests-"), root)
        self.assertEqual(os.path.dirname(root), handed,
                         "one root level in every process, beside the parent's: %r" % os.path.relpath(root, handed))
        if os.environ.get("PYTEST_XDIST_WORKER"):
            self.assertIsNotNone(pkg.PARENT_ROOT, "an xdist worker was handed the controller's root as its TMPDIR")
        if pkg.PARENT_ROOT:
            parent = os.path.realpath(pkg.PARENT_ROOT)
            self.assertTrue(os.path.basename(parent).startswith("romp-tests-"), parent)
            self.assertEqual(os.path.dirname(parent), handed, "the parent's root sits in the same dir")
            self.assertNotEqual(parent, root)
            self.assertNotEqual(os.path.commonpath([parent, root]), parent, "beside, not inside: %s / %s" % (parent, root))
            with open(os.path.join(pkg.PARENT_ROOT, pkg.TEST_ROOT_CHILDREN), encoding="utf-8") as fh:
                listed = [json.loads(line) for line in fh.read().splitlines()]
            self.assertIn({"pid": os.getpid(), "root": pkg.TMP_ROOT}, listed, "this process told its parent where it minted")

    def test_no_test_pins_a_temp_path_to_a_literal_directory(self):
        # A literal directory as a tempfile call's `dir` bypasses the redirect: the socket tests
        # carried dir="/tmp" and left three rompsock* directories in the real /tmp per run, where the
        # nested-run check below could not see them. Static, so it covers every module whether or
        # not a run exercises it; the rule and its shapes are _python_pins' and _shell_pins' (the
        # LiteralPinChecker class pins them on synthetic sources), this applies them to the tree.
        bad = []
        for path in sorted(glob.glob(os.path.join(HERE, "*.py"))):
            src = open(path, encoding="utf-8").read()
            if any(c in src for c in TEMPFILE_DIR_POSITION):     # a text prefilter keeps the parse to candidates
                bad += _python_pins(src, os.path.relpath(path, ROOT))
        for path in sorted(glob.glob(os.path.join(HERE, "*.bats")) + glob.glob(os.path.join(HERE, "*.bash"))):
            bad += _shell_pins(open(path, encoding="utf-8").read(), os.path.relpath(path, ROOT))
        self.assertEqual(bad, [], "temp paths take the process temp dir (the private root); a test that "
                         "must leave it falls back to ROMP_TESTS_SYSTEM_TMPDIR, as "
                         "tests/test_host_transport.py's two socket dirs and tests/test_session_host.py's "
                         "padded roots do")


# The literal-directory rule, one function per language. Python: the `dir` argument of a tempfile
# call — the keyword, or the positional slot the module's signatures give it (the third of mkdtemp,
# mkstemp, mktemp and TemporaryDirectory; the seventh of NamedTemporaryFile and TemporaryFile; the
# eighth of SpooledTemporaryFile) — is a pin when it is a string literal of any value, when any
# string literal inside its expression is an absolute path (an f-string piece, an operand of `+`,
# an os.path.join argument, the default of os.environ.get), or when it is a name or attribute the
# same file assigns such an expression to (followed through assignments a few levels deep). A
# relative literal inside a composed expression (os.path.join(self.dir, "sub")) is a component, not
# a pin; a call that names no absolute path (tempfile.gettempdir(), str(home), self.td.name,
# os.environ.get("X") or ...) is where a dir should come from. Only the tempfile names are read, so
# parse_session(dir="/TESTDIR") is not a hit and a call split over lines is. Shell: `mktemp` handed
# a path under a system temp dir on the same command — as the template, as `-p`'s or `--tmpdir`'s
# value, spaced, attached or `=`-joined, quoted or bare — and any `TMPDIR=` assignment to one (the
# `TMPDIR=/tmp mktemp -d` prefix and an `export` alike: both redirect every child there). A trailing
# comment is not reached and a comment line is skipped. The round-2 review (2026-09-06) found the
# first version reading only the keyword form and only an unquoted, space-separated shell path.
TEMPFILE_DIR_POSITION = {"mkdtemp": 2, "mkstemp": 2, "mktemp": 2, "TemporaryDirectory": 2,
                         "NamedTemporaryFile": 6, "TemporaryFile": 6, "SpooledTemporaryFile": 7}
_SYSTEM_TEMP = r"/(?:tmp|var/tmp|private/tmp|var/folders|dev/shm)\b"
_SH_PIN = re.compile(r"\bmktemp\b[^\n|;&#]*(?:\s-p\s*|[\s=])[\"']?" + _SYSTEM_TEMP
                     + r"|\bTMPDIR=[\"']?" + _SYSTEM_TEMP)


def _dir_argument(call):
    """The `dir` argument's node, from the keyword or the positional slot; None when absent or when a
    starred argument makes the positions unknowable."""
    for kw in call.keywords:
        if kw.arg == "dir":
            return kw.value
    pos = TEMPFILE_DIR_POSITION[_call_name(call)]
    if len(call.args) > pos and not any(isinstance(a, ast.Starred) for a in call.args):
        return call.args[pos]
    return None


def _call_name(call):
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None


def _bind(out, target, value):
    """Record `target = value`: a name or attribute by its source text; a tuple or list target element by element when
    the value is a tuple or list of the same length (a loop over rows binds each column). A value that is the target's
    own name (`f(x)` passing `x` to a parameter named `x`) is not a binding, so a follow never cycles on it."""
    if isinstance(target, (ast.Name, ast.Attribute)):
        key = ast.unparse(target)
        if ast.unparse(value) != key:
            out.setdefault(key, []).append(value)
    elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List)) \
            and len(target.elts) == len(value.elts):
        for t, v in zip(target.elts, value.elts):
            _bind(out, t, v)


class _Bindings:
    """Every value a name can hold in a module, keyed by the target's source text (`name`, `self.name`), read in ONE
    walk on first use: `name = value` (annotated or augmented too); a `for name in (<literal>, ...)` loop's or comprehension's
    target, bound to each element (a tuple target over rows, column by column; an enumerate() target's second name), a
    lambda's first parameter over the literal a map() or filter() hands it, an import alias of the kernel's
    SESSION_HOSTS_SETTING; and a function's parameters, bound to what every call
    site in the module passes for them (by position, `self`/`cls` skipped; by keyword) and to their defaults, so a value
    that reaches a write through a helper's argument is still read (2026-09-21). Two views of the same walk: `module`,
    everything; `local[f]`, what function `f` binds itself (its own parameters included; an inner function's bindings
    are the inner function's); and `owner[node]`, the innermost function a node sits in; `functions[name]` and `calls[name]`, the module's defs and
    its calls by name, for a helper that builds or receives a path (2026-09-21). A reader resolves a name in
    its enclosing function first and the module second (_Scope), since a 13,000-line module binds `root` to a hundred
    things and only the enclosing function's binding is the write's. Lazy: a module whose tempfile calls all name a
    literal and no `dir=` never asks, and costs its parse alone. A `with open(...) as fh` handle is NOT recorded: it is
    scoped to its statement by _session_hosts_writes, since a module reuses `fh` for every file it writes."""

    def __init__(self, tree):
        self.tree, self.module, self.local, self.owner, self.functions, self.calls = tree, None, None, None, None, None

    def built(self):
        if self.module is None:
            self._build()
        return self

    def _build(self):
        module, local, owner, calls, funcs = {}, {}, {}, collections.defaultdict(list), []
        todo = [(self.tree, None)]
        while todo:                                        # loop-ok: an explicit stack, one visit per node
            node, func = todo.pop()
            if func is not None:
                owner[node] = func
            if isinstance(node, ast.Call) and _call_name(node):
                calls[_call_name(node)].append(node)
            here = local.get(func) if func is not None else None
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    _bind(module, t, node.value)
                    if here is not None:
                        _bind(here, t, node.value)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value is not None:
                _bind(module, node.target, node.value)
                if here is not None:
                    _bind(here, node.target, node.value)
            elif isinstance(node, (ast.For, ast.comprehension)):
                target, it = node.target, node.iter                # a loop or a comprehension over a literal tuple or list,
                if (isinstance(it, ast.Call) and _call_name(it) == "enumerate" and it.args                 # or enumerate() of one
                        and isinstance(target, (ast.Tuple, ast.List)) and len(target.elts) == 2):
                    target, it = target.elts[1], it.args[0]
                if isinstance(it, (ast.Tuple, ast.List)):
                    for elt in it.elts:
                        _bind(module, target, elt)
                        if here is not None:
                            _bind(here, target, elt)
            elif (isinstance(node, ast.Call) and _call_name(node) in ("map", "filter") and len(node.args) >= 2
                    and isinstance(node.args[0], ast.Lambda) and isinstance(node.args[1], (ast.Tuple, ast.List))
                    and node.args[0].args.args):                    # map(lambda p: ..., (<literal>, ...)): p over the elements
                for elt in node.args[1].elts:
                    _bind(module, ast.Name(node.args[0].args.args[0].arg), elt)
                    if here is not None:
                        _bind(here, ast.Name(node.args[0].args.args[0].arg), elt)
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:                               # `from ... import SESSION_HOSTS_SETTING as TOGGLE`: TOGGLE spells it
                    if a.name.endswith("SESSION_HOSTS_SETTING") and a.asname:
                        _bind(module, ast.Name(a.asname), ast.Name(a.name))
            inner = func
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs.append(node)
                local[node] = {}
                inner = node
            todo.extend((child, inner) for child in ast.iter_child_nodes(node))
        for f in funcs:                                    # the parameters, once every call in the module is indexed
            params = list(f.args.posonlyargs + f.args.args)
            if params and params[0].arg in ("self", "cls"):
                params = params[1:]
            values = []
            defaults = f.args.defaults
            values += [(a.arg, d) for a, d in zip(params[len(params) - len(defaults):], defaults)]
            values += [(a.arg, d) for a, d in zip(f.args.kwonlyargs, f.args.kw_defaults) if d is not None]
            names = {a.arg for a in params + f.args.kwonlyargs}
            for call in calls.get(f.name, ()):
                for a, v in zip(params, call.args):
                    if isinstance(v, ast.Starred):
                        break
                    values.append((a.arg, v))
                values += [(kw.arg, kw.value) for kw in call.keywords if kw.arg in names]
            for name, v in values:
                _bind(module, ast.Name(name), v)
                _bind(local[f], ast.Name(name), v)
        functions = collections.defaultdict(list)
        for f in funcs:
            functions[f.name].append(f)
        self.module, self.local, self.owner, self.functions, self.calls = module, local, owner, dict(functions), dict(calls)


def _assignments(tree):
    """The module-wide view of _Bindings, for the literal-pin rule."""
    return _Bindings(tree).built().module


class _Scope:
    """The bindings a name at `node` resolves through: its enclosing function's first, the module's for a name the
    function never binds (`self.lab` set in setUp, a module-level root). `.get(key, default)` is the one method the
    readers use; `.module` is the module-wide view, for a root a caller handed in."""

    def __init__(self, bindings, node):
        self.bindings, self.node = bindings, node

    def get(self, key, default=()):
        b = self.bindings.built()
        local = b.local.get(b.owner.get(self.node))
        return (local.get(key) if local else None) or b.module.get(key, default)

    def functions(self, name):
        """The module's defs named `name`, for a helper that returns a session-hosts path."""
        return self.bindings.built().functions.get(name, ())

    @property
    def module(self):
        return self.bindings.built().module


def _scoper(tree):
    """scope_of(node) -> the _Scope a name at `node` resolves through, over one lazy _Bindings of the module."""
    bindings = _Bindings(tree)
    return lambda node: _Scope(bindings, node)


def _pinned(node, assigned, depth=3):
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if any(isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub.value.startswith("/")
           for sub in ast.walk(node)):
        return True
    if depth and isinstance(node, (ast.Name, ast.Attribute)):
        return any(_pinned(v, assigned, depth - 1) for v in assigned.get(ast.unparse(node), ()))
    return False


def _python_pins(src, label):
    """`label:line: call` for every tempfile call in `src` whose dir is a literal directory."""
    tree = ast.parse(src)
    assigned = _assignments(tree)
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node) in TEMPFILE_DIR_POSITION:
            d = _dir_argument(node)
            if d is not None and _pinned(d, assigned):
                bad.append("%s:%d: %s" % (label, node.lineno, ast.get_source_segment(src, node).splitlines()[0]))
    return bad


def _shell_pins(text, label):
    """`label:line: text` for every line of a shell source that points mktemp, or TMPDIR, at a
    literal system temp dir."""
    return ["%s:%d: %s" % (label, n, line.strip()) for n, line in enumerate(text.splitlines(), 1)
            if not line.lstrip().startswith("#") and _SH_PIN.search(line)]


class LiteralPinChecker(unittest.TestCase):
    """The rule on synthetic sources: every shape the round-2 review listed as passing the first
    version is a hit, and every legitimate spelling in the tree is not."""

    PREAMBLE = textwrap.dedent('''\
        import os, tempfile
        from tempfile import mkdtemp
        PINNED = "/tmp"
        VIA = PINNED
        root = tempfile.mkdtemp()
        home = root

        class T:
            def setUp(self):
                self.pinned = "/tmp/" + "x"
                self.dir = os.path.realpath(tempfile.mkdtemp())
                self.td = tempfile.TemporaryDirectory()
                name = "x"
                CALL
    ''')

    PINNED_PY = [
        'tempfile.mkdtemp(dir="/tmp")',
        'tempfile.mkdtemp(prefix="x",\n                 dir="/tmp")',                 # split over lines
        'mkdtemp(dir="/tmp")',                                                       # the bare name
        'tempfile.mkdtemp("", "x", "/tmp")',                                         # by position
        'tempfile.mkstemp("", "x", "/tmp")',
        'tempfile.mktemp("", "x", "/tmp")',
        'tempfile.TemporaryDirectory(None, None, "/tmp")',
        'tempfile.NamedTemporaryFile("w", -1, None, None, ".jsonl", "x", "/tmp")',  # the seventh
        'tempfile.TemporaryFile("w+b", -1, None, None, None, None, "/var/tmp")',
        'tempfile.SpooledTemporaryFile(0, "w+b", -1, None, None, None, None, "/tmp")',
        'tempfile.mkdtemp(dir=f"/tmp/{name}")',                                       # composed
        'tempfile.mkdtemp(dir="/tmp/" + name)',
        'tempfile.mkdtemp(dir=os.path.join("/tmp", name))',
        'tempfile.mkdtemp(dir=os.environ.get("TMPDIR", "/tmp"))',
        'tempfile.mkdtemp(dir=PINNED)',                                              # a name bound to one
        'tempfile.mkdtemp(dir=VIA)',
        'tempfile.mkdtemp(dir=self.pinned)',
        'tempfile.mkdtemp(dir="fixtures")',                                          # any plain literal
        'tempfile.mkdtemp(dir="/TESTDIR")',
    ]
    UNPINNED_PY = [
        'tempfile.mkdtemp()',
        'tempfile.mkdtemp(prefix="rompsock")',
        'tempfile.mkdtemp(dir=tempfile.gettempdir())',
        'tempfile.mkdtemp(prefix="rompsock", dir=os.environ.get("ROMP_TESTS_SYSTEM_TMPDIR") or tempfile.gettempdir())',
        'tempfile.TemporaryDirectory(dir=str(home))',
        'tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, dir=self.td.name)',
        'tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)',
        'tempfile.mkdtemp(dir=os.path.join(self.dir, "sub"))',                       # a relative component
        'tempfile.mkdtemp(dir=None)',
        'tempfile.mkdtemp("", "x", None)',
        'tempfile.mkdtemp(dir=root)',                                                # bound to a mkdtemp
        'tempfile.mkdtemp(dir=self.dir)',
        'tempfile.mkdtemp(dir=home)',
        'parse_session(dir="/TESTDIR")',                                             # not a tempfile call
        'shutil.rmtree("/tmp/x")',
        'open("/tmp/x").read()',
    ]

    def _pins(self, call):
        src = self.PREAMBLE.replace("CALL", textwrap.indent(call, " " * 8).lstrip())
        return _python_pins(src, "t.py")

    def test_python_shapes_that_pin_are_hits(self):
        for call in self.PINNED_PY:
            with self.subTest(call=call):
                pins = self._pins(call)
                self.assertEqual(len(pins), 1, pins)
                self.assertTrue(pins[0].startswith("t.py:%d: " % (self.PREAMBLE[:self.PREAMBLE.index("CALL")].count("\n") + 1)), pins)
                self.assertIn(call.splitlines()[0], pins[0])

    def test_python_shapes_that_do_not_pin_are_clean(self):
        for call in self.UNPINNED_PY:
            with self.subTest(call=call):
                self.assertEqual(self._pins(call), [])

    PINNED_SH = [
        'TEST_DIR="$(mktemp -d /tmp/x.XXXX)"',
        'TEST_DIR="$(mktemp -d "/tmp/x.XXXX")"',                # quoted
        "TEST_DIR=\"$(mktemp -d '/tmp/x.XXXX')\"",
        'd=$(mktemp -p /tmp)',
        'd=$(mktemp -p "/tmp")',
        'd=$(mktemp -p/tmp -d)',                                 # attached
        'd=$(mktemp -d --tmpdir=/tmp)',                          # =-joined
        'd=$(mktemp --tmpdir="/var/tmp" -d)',
        'd=$(mktemp --tmpdir /private/tmp)',
        'd=$(TMPDIR=/tmp mktemp -d)',                            # the prefix form
        'd=$(TMPDIR="/tmp" mktemp -d)',
        'export TMPDIR=/tmp',                                    # redirects every child there
        'TMPDIR=/var/folders/x/T',
        '    mktemp -d /var/tmp/x.XXXX',
        'run mktemp -d /dev/shm/x.XXXX',
    ]
    UNPINNED_SH = [
        'TEST_DIR="$(mktemp -d)"',
        'TEST_DIR="$(mktemp -d "$TMPDIR/x.XXXX")"',
        'd=$(mktemp -p "$TMPDIR")',
        'd=$(mktemp --tmpdir="$TEST_DIR")',
        'd=$(TMPDIR="$TEST_DIR" mktemp -d)',
        'export FAKE_TMPDIR="$TEST_DIR/fake"',                   # a name ENDING in TMPDIR is not the variable
        'export TMPDIR=/nonexistent',
        'TEST_DIR="$(mktemp -d -u)"',
        '# mktemp -d /tmp/x.XXXX',                               # a comment line
        '    # d=$(TMPDIR=/tmp mktemp -d)',
        'TEST_DIR="$(mktemp -d)"   # not /tmp',                  # a trailing comment
        '[ -d /tmp ]',
        'grep -qxF "FAKE_TMPDIR=$TEST_DIR/fake" "$FAKE_ENV"',
    ]

    def test_shell_shapes_that_pin_are_hits(self):
        for line in self.PINNED_SH:
            with self.subTest(line=line):
                self.assertEqual(_shell_pins("setup() {\n" + line + "\n}\n", "t.bats"), ["t.bats:2: " + line.strip()])

    def test_shell_shapes_that_do_not_pin_are_clean(self):
        for line in self.UNPINNED_SH:
            with self.subTest(line=line):
                self.assertEqual(_shell_pins("setup() {\n" + line + "\n}\n", "t.bats"), [])


@under_conftest
class RunEndNotice(unittest.TestCase):
    """A root that survives the run-end removal is named on stderr, once, rather than left standing
    with the run green. `shutil.rmtree(..., ignore_errors=True)` swallows a child still writing under
    the root and a 000-mode directory a test left behind (shutil's fd-based walk cannot open it, so
    the root's rmdir is never reached); the stand-in here is the latter."""

    def test_conftest_removes_the_packages_root_which_holds_the_state_dir(self):
        # One root per process, the package's: conftest imports it rather than minting a second, and the
        # package's state dir sits INSIDE it (minted after the redirect), so the root is the one thing a
        # run puts in the system temp dir and the one thing conftest removes (BareRunLeavesNothing counts
        # it, in a system temp dir of its own). Until 2026-09-14 the state dir was minted before conftest's
        # redirect and sat BESIDE the root, a second top-level entry conftest held (and marked) for the
        # run-end removal on its own.
        conftest, pkg = sys.modules["tests.conftest"], sys.modules["tests"]
        root = tempfile.gettempdir()
        self.assertEqual(os.path.realpath(root), os.path.realpath(pkg.TMP_ROOT))
        self.assertEqual(conftest._TMP_ROOT, pkg.TMP_ROOT, "conftest removes the package's root, not one of its own")
        self.assertEqual(os.path.commonpath([root, pkg.STATE_DIR]), root, pkg.STATE_DIR)

    @unittest.skipIf(os.geteuid() == 0, "root can remove a 000-mode directory")
    def test_a_root_that_survives_removal_is_named_on_stderr(self):
        conftest = sys.modules["tests.conftest"]
        root = tempfile.mkdtemp()                       # a stand-in root, inside the real one
        locked = os.path.join(root, "locked")
        os.mkdir(locked)
        open(os.path.join(locked, "f"), "w").close()
        os.chmod(locked, 0)
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        self.addCleanup(lambda: os.path.isdir(locked) and os.chmod(locked, 0o700))

        # The real hook, on the stand-in only (the run's own root is live and not this test's).
        with patch.object(conftest, "_TMP_ROOT", root):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                conftest.pytest_unconfigure(None)
            self.assertTrue(os.path.isdir(root), "the 000-mode child keeps the root standing")
            self.assertEqual(err.getvalue(), "[tests] not removed at run end: %s\n" % root)

            err = io.StringIO()                          # the atexit fallback: same survivor, silent
            with contextlib.redirect_stderr(err):
                conftest._remove_run_dirs()
            self.assertEqual(err.getvalue(), "")

            os.chmod(locked, 0o700)                      # control: a removable root says nothing
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                conftest.pytest_unconfigure(None)
            self.assertFalse(os.path.exists(root))
            self.assertEqual(err.getvalue(), "")


def _git_version():
    out = _run(["git", "--version"]).stdout.split()
    m = re.match(r"(\d+)\.(\d+)", out[2] if len(out) > 2 else "")
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


@under_conftest
@unittest.skipIf(_git_version() < (2, 32), "GIT_CONFIG_GLOBAL needs git >= 2.32")
class GitFloor(unittest.TestCase):
    def test_git_reads_no_global_config_and_has_the_synthetic_identity(self):
        self.assertEqual(_run(["git", "config", "--global", "--list"]).stdout, "")
        self.assertTrue(_run(["git", "var", "GIT_AUTHOR_IDENT"]).stdout.startswith(IDENT + " "))
        self.assertTrue(_run(["git", "var", "GIT_COMMITTER_IDENT"]).stdout.startswith(IDENT + " "))

    def _hostile_repo(self, td):
        """A stand-in for the developer's configuration: a pre-commit hook that refuses every commit
        and leaves a marker, a config file wiring it in through core.hooksPath, and a repo with one
        staged file. Returns (marker, cfg, repo)."""
        hooks = os.path.join(td, "hooks")
        os.makedirs(hooks)
        marker = os.path.join(td, "hook-ran")
        with open(os.path.join(hooks, "pre-commit"), "w") as f:
            f.write("#!/bin/sh\necho ran > '%s'\nexit 1\n" % marker)
        os.chmod(os.path.join(hooks, "pre-commit"), 0o755)
        cfg = os.path.join(td, "gitconfig")
        with open(cfg, "w") as f:
            f.write("[core]\n\thooksPath = %s\n" % hooks)
        repo = os.path.join(td, "repo")
        os.makedirs(repo)
        init_repo(repo, "-q")   # no ident: the commit below pins the conftest floor's identity, not a local one
        with open(os.path.join(repo, "a.txt"), "w") as f:
            f.write("a\n")
        _run(["git", "add", "a.txt"], cwd=repo, check=True)
        return marker, cfg, repo

    COMMIT = ["git", "commit", "-q", "-m", "seed"]

    def test_a_global_hooks_path_cannot_reach_a_fixture_commit(self):
        # The hostile config as the GLOBAL file. Live first, then floored (the suite's own env).
        with tempfile.TemporaryDirectory() as td:
            marker, cfg, repo = self._hostile_repo(td)
            live = _run(self.COMMIT, cwd=repo, env=dict(os.environ, GIT_CONFIG_GLOBAL=cfg))
            self.assertNotEqual(live.returncode, 0, "the probe is live: the hook blocks the commit")
            self.assertTrue(os.path.exists(marker))
            os.remove(marker)

            floored = _run(self.COMMIT, cwd=repo)
            self.assertEqual(floored.returncode, 0, floored.stderr)
            self.assertFalse(os.path.exists(marker), "no global hook reaches a fixture commit")
            self.assertEqual(_run(["git", "log", "-1", "--format=%an <%ae>"], cwd=repo).stdout.strip(), IDENT)

    def test_a_system_hooks_path_cannot_reach_a_fixture_commit_either(self):
        # The hostile config as the SYSTEM file: GIT_CONFIG_SYSTEM (git >= 2.32, like GIT_CONFIG_GLOBAL)
        # is a root-free stand-in for /etc/gitconfig, and GIT_CONFIG_NOSYSTEM=1 is the half of the
        # floor that hides it — the global probe above says nothing about it. The assertion is the
        # commit's outcome: `git config --system --list` prints the file under NOSYSTEM too.
        with tempfile.TemporaryDirectory() as td:
            marker, cfg, repo = self._hostile_repo(td)
            live_env = dict(os.environ, GIT_CONFIG_SYSTEM=cfg)
            live_env.pop("GIT_CONFIG_NOSYSTEM", None)
            live = _run(self.COMMIT, cwd=repo, env=live_env)
            self.assertNotEqual(live.returncode, 0, "the probe is live: the system hook blocks the commit")
            self.assertTrue(os.path.exists(marker))
            os.remove(marker)

            floored = _run(self.COMMIT, cwd=repo, env=dict(os.environ, GIT_CONFIG_SYSTEM=cfg))
            self.assertEqual(floored.returncode, 0, floored.stderr)
            self.assertFalse(os.path.exists(marker), "no system hook reaches a fixture commit")


LEAKY_MODULE = textwrap.dedent('''\
    import os, subprocess, sys, tempfile, unittest
    from git_fixture import git, init_repo    # the suite's runner (tests/__init__.py registers it under tests.conftest)
    ROOT = os.environ["TMPDIR"]
    STATE = tempfile.mkdtemp()            # a module preamble's state root: never cleaned by the module

    class Leak(unittest.TestCase):
        def test_everything_lands_under_the_private_root(self):
            self.assertTrue(os.path.basename(ROOT).startswith("romp-tests-"), ROOT)
            d = tempfile.mkdtemp()            # a seed repo, the shape that leaked: never cleaned
            fd, f = tempfile.mkstemp()
            os.close(fd)
            init_repo(d, "-q")                # no background git work: a detached maintenance would outlive the run
            open(os.path.join(d, "a.txt"), "w").write("a\\n")
            git(d, "add", "a.txt")
            git(d, "commit", "-q", "-m", "seed")
            made = [STATE, d, f]
            if sys.platform != "darwin":      # macOS mktemp(1) without a template ignores TMPDIR (the Darwin per-user root)
                made.append(subprocess.run(["mktemp", "-d"], capture_output=True, text=True, check=True).stdout.strip())
            for p in made:
                self.assertEqual(os.path.commonpath([ROOT, p]), ROOT, p)
''')


@under_conftest
class RunLeavesNothing(unittest.TestCase):
    """A nested pytest, handed a fresh directory as its system temp dir and loading this repo's
    conftest as a plugin, runs a module that leaks every way the suite does: after it exits the
    directory holds exactly what it held before.

    The fresh directory is the whole check; the machine's real system temp dir is not diffed. It
    would be cheap (a prefix-filtered os.scandir over 101k entries measured 0.10 s, 2026-09-06) but
    not attributable: that dir is shared with every process on the box, and with other checkouts
    running this suite beside it, romp-prefixed entries appeared there about twice a minute (345
    bursts in three hours, measured the same day) — a before/after diff over a nested run of a few
    seconds would fail a third of the time with nothing wrong. Only a literal path can reach it past
    TMPDIR, and PrivateTempRoot pins that class statically."""

    def _nested(self, *extra):
        fresh = tempfile.mkdtemp()
        case = os.path.join(fresh, "case")
        os.makedirs(case)
        with open(os.path.join(case, "test_leak.py"), "w") as f:
            f.write(LEAKY_MODULE)
        env = dict(os.environ, TMPDIR=fresh, PYTHONDONTWRITEBYTECODE="1")
        for var in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_CURRENT_TEST",
            "PYTEST_XDIST_WORKER", "PYTEST_XDIST_WORKER_COUNT",
            "ROMP_TESTS_SYSTEM_TMPDIR"):        # a fresh run records its own handed dir (the package setdefaults it)
            env.pop(var, None)
        r = subprocess.run([sys.executable, "-m", "pytest", "-p", "tests.conftest", "-p", "no:cacheprovider", "-p", "no:anyio",
                            "-q", *extra, os.path.join(case, "test_leak.py")],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("1 passed", r.stdout)
        self.assertEqual(sorted(os.listdir(fresh)), ["case"],
                         "the run must leave the system temp dir as it found it")

    def test_a_run_removes_everything_it_created_under_the_system_temp_dir(self):
        self._nested()

    @unittest.skipUnless(importlib.util.find_spec("xdist"), "pytest-xdist not installed")
    def test_under_xdist_the_run_leaves_nothing_either(self):
        # Each process's own removal: a worker's root sits BESIDE the controller's (2026-09-21), so the
        # controller's rmtree no longer covers the workers and this holds only if every worker removes
        # its own root at exit (until then the nesting made the controller's removal enough).
        self._nested("-n", "2")

    @unittest.skipUnless(importlib.util.find_spec("xdist"), "pytest-xdist not installed")
    def test_under_xdist_a_worker_killed_mid_test_leaves_nothing_once_the_controller_exits(self):
        """The parent-side sweep, end to end under pytest: a worker SIGKILLed mid-test (no hooks, no atexit, as
        pytest-timeout's os._exit, an OOM kill or a crashed node leave it) leaves its root standing beside the
        controller's, and the controller's run-end removal reads `romp-tests-children` and takes it. Until
        2026-09-21 the nesting gave this for free; beside, it is the children file's job, and xdist tears the
        nodes down before the controller's unconfigure runs. The kill waits on the worker's own ready-file."""
        fresh = tempfile.mkdtemp()
        case = os.path.join(fresh, "case")
        os.makedirs(case)
        with open(os.path.join(case, "test_leak.py"), "w") as f:
            f.write(KILLED_WORKER_MODULE)
        ready = os.path.join(tempfile.mkdtemp(prefix="romp-hygiene-ready-"), "ready")   # tracked, outside `fresh`
        env = dict(os.environ, TMPDIR=fresh, PYTHONDONTWRITEBYTECODE="1", ROMP_HYGIENE_READY=ready)
        for var in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_CURRENT_TEST",
                    "PYTEST_XDIST_WORKER", "PYTEST_XDIST_WORKER_COUNT", "ROMP_TESTS_SYSTEM_TMPDIR"):
            env.pop(var, None)
        proc = subprocess.Popen([sys.executable, "-m", "pytest", "-p", "tests.conftest", "-p", "no:cacheprovider", "-q",
                                 "-n", "2", "--max-worker-restart=0", os.path.join(case, "test_leak.py")],
                                cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        def _reap():
            if proc.poll() is None:
                proc.kill()
            if proc.stdout is not None and not proc.stdout.closed:
                proc.communicate()
            else:
                proc.wait()
        self.addCleanup(_reap)
        deadline = time.monotonic() + 120
        while not os.path.exists(ready):           # loop-ok: bounded wait on the worker's ready-file, the event itself
            if proc.poll() is not None:
                self.fail("the nested run ended before its worker was ready:\n" + proc.communicate()[0])
            self.assertLess(time.monotonic(), deadline, "the worker never said it was ready")
            time.sleep(0.05)
        with open(ready) as fh:
            worker_pid, worker_root = fh.read().split("\n")[:2]
        worker_pid = int(worker_pid)
        self.assertEqual(os.path.dirname(worker_root), fresh, "the worker minted beside the controller: " + worker_root)
        self.assertTrue(os.path.isdir(worker_root))
        os.kill(worker_pid, signal.SIGKILL)
        out, _ = proc.communicate(timeout=120)
        self.assertNotEqual(proc.returncode, 0, "a crashed worker is a failed run:\n" + out)
        self.assertIn("crashed", out)
        self.assertEqual(sorted(os.listdir(fresh)), ["case"],
                         "the controller removed the dead worker's root along with its own:\n" + out)


KILLED_WORKER_MODULE = textwrap.dedent('''\
    import os, tempfile, time, unittest
    STATE = tempfile.mkdtemp()            # a module preamble's state root, inside this worker's root

    class Leak(unittest.TestCase):
        def test_waits_to_be_killed(self):
            tempfile.mkdtemp()
            ready = os.environ["ROMP_HYGIENE_READY"]
            with open(ready + ".tmp", "w") as fh:            # pid and root, then an atomic rename: the parent reads whole lines
                fh.write("%d\\n%s\\n" % (os.getpid(), os.environ["TMPDIR"]))
            os.replace(ready + ".tmp", ready)
            time.sleep(600)                                  # the kill ends this

        def test_the_other_worker_finishes(self):
            self.assertTrue(os.path.basename(os.environ["TMPDIR"]).startswith("romp-tests-"))
''')


BARE_LEAKY_MODULE = textwrap.dedent('''\
    import os, subprocess, sys, tempfile, time, unittest
    FIRST_IMPORTS
    os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()   # the module preamble's state root, AFTER the import as in every module
    os.environ.pop("ROMP_STATE_DIR", None)
    READY = os.environ.get("ROMP_HYGIENE_READY")

    class Leak(unittest.TestCase):
        def test_leaks_every_way_a_bare_run_can(self):
            tempfile.mkdtemp()                                                  # tracked: the hook's exit sweep removes it
            fd, _ = tempfile.mkstemp()                                          # a file: the hook never sees it
            os.close(fd)
            subprocess.run(["mktemp", "-d"], check=True, capture_output=True)   # a child's directory: nor that
            if READY:                                                           # the killed leg: say so, then wait for the kill
                open(READY, "w").close()
                time.sleep(600)

    if __name__ == "__main__":
        unittest.main()
''')
# The module's first imports, one set per shape of bare run. `python -m unittest tests.test_x` imports the
# package before the module, so the module's own `from romp_load import load_source` finds the name the
# package registered; a direct `python3 tests/test_x.py` imports nothing before the module, and that same
# line is where the package comes from (tests/romp_load.py's bootstrap, 2026-09-14).
UNITTEST_SHAPED_IMPORTS = ("import tests   # noqa: F401  the package first, then the module: the order `python -m unittest tests.test_x` runs them in\n"
                           "from romp_load import load_source   # noqa: F401  every module's one import; here the package's registration")
DIRECT_SHAPED_IMPORTS = "from romp_load import load_source   # noqa: F401  every module's one import, and here the first thing that runs"


class BareRunLeavesNothing(unittest.TestCase):
    """A bare run, handed a fresh directory as its system temp dir, runs a module that leaks every way a bare
    run can: a module preamble's mkdtemp, a tracked mkdtemp in a test, a mkstemp file, a child's `mktemp -d`.
    Finished, it leaves the directory as it found it; killed mid-test (SIGKILL, as a kernel restart cutting
    the tool shell does: no atexit, no sweep, no removal), it leaves exactly one entry, a `romp-tests-*` root
    whose marker names the dead pid, and the kernel's boot sweep removes it. Two shapes of bare run, each
    both ways: the tests package imported before the module and no conftest, which is what `python -m
    unittest tests.test_x` is; and the module alone, which is what `python3 tests/test_x.py` is, where
    nothing imports the package and the module's `from romp_load import load_source`, its first import as in
    every module, is where the floor comes from (tests/romp_load.py's bootstrap). Until 2026-09-14 the root
    and the marker were conftest's, so a bare run of either shape left the mkstemp file and the `mktemp -d`
    directory loose on a normal exit and, killed, everything it made plus an unmarked romp-tests-state-* dir
    the sweep had to refuse; the package took them the same day, and the direct run still had nothing, not
    even the hook: `python3 tests/test_credentials.py` left 86 loose tmp* directories in a fresh TMPDIR where
    `python3 -m unittest tests.test_credentials` left none. The child is the subject, so this runs under
    pytest and under a bare run of this module alike. The kill waits on the child's own ready-file, never on
    a timer."""

    def _bare_child(self, kill=False, direct=False):
        """(Popen, fresh, ready): the leaky module, `test_bare_leak.py` (a test module's name), written OUTSIDE
        `fresh` and run as a script with TMPDIR at `fresh`, none of the parent run's own names, and a
        ready-file to write before it sleeps when `kill` is asked. Two shapes. The unittest-shaped child (the
        default) has the checkout on its PYTHONPATH and imports the package first, as `python -m unittest
        tests.test_x` does before the module. The direct-shaped child has the checkout's tests/ directory on
        its PYTHONPATH instead, the stand-in for sys.path[0], which a module IN tests/ gets for free: its
        `from romp_load import load_source` resolves the file under its bare name as `python3 tests/test_x.py`
        does, nothing has imported the package, and this test puts the checkout root on no path (the loader
        does). Its cwd is a directory of its own: a script run never has the cwd on sys.path, and the floor
        must not depend on where the run started."""
        scratch = tempfile.mkdtemp(prefix="romp-hygiene-bare-")      # tracked: inside this run's root
        fresh = os.path.join(scratch, "systmp")
        os.mkdir(fresh)
        module = os.path.join(scratch, "test_bare_leak.py")
        with open(module, "w") as fh:
            fh.write(BARE_LEAKY_MODULE.replace("FIRST_IMPORTS", DIRECT_SHAPED_IMPORTS if direct else UNITTEST_SHAPED_IMPORTS))
        on_path = HERE if direct else ROOT
        env = dict(os.environ, TMPDIR=fresh, PYTHONDONTWRITEBYTECODE="1",
                   PYTHONPATH=os.pathsep.join(p for p in (on_path, os.environ.get("PYTHONPATH")) if p))
        for var in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_CURRENT_TEST",
                    "PYTEST_XDIST_WORKER", "PYTEST_XDIST_WORKER_COUNT", MARKER_ENV,
                    "ROMP_TESTS_SYSTEM_TMPDIR"):        # a fresh run records its own handed dir (the package setdefaults it)
            env.pop(var, None)
        ready = os.path.join(scratch, "ready")
        if kill:
            env["ROMP_HYGIENE_READY"] = ready
        cwd = ROOT
        if direct:
            cwd = os.path.join(scratch, "cwd")
            os.mkdir(cwd)
        proc = subprocess.Popen([sys.executable, module], cwd=cwd, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        def _reap():
            # kill a child still running on a failure path, then reap it: a killed child left unwaited
            # is a zombie until this process exits. Drain the pipe only while it is still open (a test
            # that already read the child to its end has closed it, and a second communicate raises)
            if proc.poll() is None:
                proc.kill()
            if proc.stdout is not None and not proc.stdout.closed:
                proc.communicate()
            else:
                proc.wait()
        self.addCleanup(_reap)
        return proc, fresh, ready

    def _finished_run_leaves_nothing(self, direct):
        proc, fresh, _ = self._bare_child(direct=direct)
        out, _ = proc.communicate(timeout=120)
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("Ran 1 test", out)
        self.assertEqual(os.listdir(fresh), [], "a %s run must leave the system temp dir as it found it"
                         % ("direct" if direct else "bare"))

    def _killed_run_leaves_one_marked_root_the_sweep_removes(self, direct):
        proc, fresh, ready = self._bare_child(kill=True, direct=direct)
        deadline = time.monotonic() + 60
        while not os.path.exists(ready):           # loop-ok: bounded wait on the child's ready-file, the event itself
            if proc.poll() is not None:
                self.fail("the child ended before it was ready:\n" + proc.communicate()[0])
            self.assertLess(time.monotonic(), deadline, "the child never said it was ready")
            time.sleep(0.02)
        proc.kill()
        proc.communicate()
        entries = os.listdir(fresh)
        self.assertEqual(len(entries), 1, "a killed %s run leaves exactly its root, marked: %r"
                         % ("direct" if direct else "bare", entries))
        root = os.path.join(fresh, entries[0])
        self.assertTrue(entries[0].startswith("romp-tests-") and os.path.isdir(root), entries)
        with open(os.path.join(root, "romp-tests-owner.json")) as fh:
            self.assertEqual(json.load(fh)["pid"], proc.pid, "the marker names the dead run")
        # ...and the kernel's boot sweep over that system temp dir sees a dead owner and removes it. Loaded
        # here, not at import: this module loads no romp code until this line (a private name, as the
        # siblings that load the backend do).
        from romp_load import load_source
        sb = load_source("romp_sdk_backend_hygiene", os.path.join(ROOT, "bin", "romp_sdk_backend.py"))
        self.assertEqual(sb.sweep_dead_test_roots(fresh), 1)
        self.assertEqual(os.listdir(fresh), [])

    def test_a_finished_bare_run_leaves_the_system_temp_dir_as_it_found_it(self):
        self._finished_run_leaves_nothing(direct=False)

    def test_a_bare_run_killed_mid_test_leaves_one_marked_root_the_sweep_removes(self):
        self._killed_run_leaves_one_marked_root_the_sweep_removes(direct=False)

    def test_a_finished_direct_run_leaves_the_system_temp_dir_as_it_found_it(self):
        # Red before the loader's bootstrap: the direct child had no hook, no root and no redirect, so the
        # preamble's dir, the test's mkdtemp, the mkstemp file and the `mktemp -d` dir all survived, loose.
        self._finished_run_leaves_nothing(direct=True)

    def test_a_direct_run_killed_mid_test_leaves_one_marked_root_the_sweep_removes(self):
        # Red before it too: the same four entries, none of them a marked root the sweep would take.
        self._killed_run_leaves_one_marked_root_the_sweep_removes(direct=True)


# The harness's socket path budget, DERIVED (2026-09-21). A session host binds an AF_UNIX socket at
# `<state root>/hosts/<sid8>.sock`, and sun_path holds 107 usable bytes on Linux (kernel/session_host.py
# SOCK_PATH_MAX, itself measured by tests/test_session_host.py SocketBudget). Under the harness the state
# root of a hosts-on lab is `<TMPDIR>/<the process's romp-tests-* root>/<the lab's mkdtemp dir>/<its
# state suffix>`, so the budget is spent four ways: the TMPDIR the run was handed, the root level(s)
# the harness adds, the lab's own shape, and the socket tail. Until 2026-09-21 an xdist worker's root
# nested inside the controller's, a second 20-byte level, and the deepest hosts-on lab
# (tests/test_session_host_restart.py: `host-served-XXXXXXXX/xdg/romp`) came to 107 bytes exactly under
# the sweep's 17-byte TMPDIR: at 18 that lab's test (ServedRestart, TMPDIR + 90) overflowed under -n and
# passed alone, the TMPDIR + 72 shapes (HostProcess, EndToEnd, AttachStandDown: a bare mkdtemp root)
# overflowed from a 36-byte TMPDIR under -n, and 76 sweep logs read the red as a flake. Nothing here is
# typed from that story: the level is measured on
# roots the harness mints (a controller-shaped and a worker-shaped process, by execution), the lab shapes
# are read from the tests' own text (every write into a `session-hosts` file whose value is not the literal
# off — a loop variable, a helper's argument and a with-open handle read through their bindings, a value
# the reader cannot read listed by site and counted, a removal or a touch read as on; every OTHER occurrence of
# the name in a module accounted for by shape or listed as unaccounted, the ledger below — its state-root
# expression followed through the
# enclosing function's assignments, then the module's, to the mkdtemp that made it), the socket tail
# comes from the kernel's own host_sock and sock_names, and the budget is the kernel's constant. The
# canonical TMPDIR is the box rule's input, `mktemp -d /tmp/sweep-XXXXXX`, 17 bytes, and stated as such.
# THE SOCKET IS ONE SHAPE (the widening, 2026-09-21 19:15Z): every shape the harness mints under a root has its
# own ceiling, so the same scan also follows every mkdtemp/TemporaryDirectory in the tree (the nesting through
# dir=, a suffix, a parameter's call sites) to the longest DIRECTORY path under xdist nesting, held against
# PC_PATH_MAX, and the longest single COMPONENT (the tree's prefixes + tail, the harness's own names, the
# kernel's socket names), held against PC_NAME_MAX. Every figure here is the longest the harness can produce
# UNDER XDIST NESTING, measured on a worker-shaped root: an alone run verifies none of them.
Lab = collections.namedtuple("Lab", "bytes file line prefix comps note")
Harness = collections.namedtuple("Harness", "bytes levels controller worker system")
SWEEP_TMPDIR_TEMPLATE = "/tmp/sweep-XXXXXX"           # the box rule: a full sweep's TMPDIR is `mktemp -d` of this, 17 bytes
_MINTING_CHILD = textwrap.dedent('''\
    import json, os, sys
    sys.path.insert(0, %r)
    import tests
    # getattr: run against a package without the beside placement (the red check at the nesting head), the child still
    # reports where it minted, so the assertions fail on the property and not on a missing name
    print(json.dumps({"root": tests.TMP_ROOT, "parent": getattr(tests, "PARENT_ROOT", None),
                      "system": getattr(tests, "SYSTEM_TMPDIR", os.environ["ROMP_TESTS_SYSTEM_TMPDIR"]),
                      "pid": os.getpid()}), flush=True)
    sys.stdin.readline()                              # held here until the parent releases it, so its root stands
''') % ROOT


def _tmp_name_tail_bytes():
    """The bytes mkdtemp appends to a prefix (its random tail), measured on one directory minted here."""
    d = tempfile.mkdtemp(prefix="tail-")
    try:
        return len(os.fsencode(os.path.basename(d))) - len(b"tail-")
    finally:
        os.rmdir(d)


def _prefix_of(call):
    """The literal prefix a mkdtemp/TemporaryDirectory call names, "tmp" (the module default) when it names none,
    None when it is not a literal."""
    for kw in call.keywords:
        if kw.arg == "prefix":
            return kw.value.value if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str) else None
    if len(call.args) > 1 and not any(isinstance(a, ast.Starred) for a in call.args):
        a = call.args[1]
        return a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else None
    return "tmp"


def _lab_shapes(expr, assigned, depth=4):
    """[(prefix, comps, note, the mkdtemp call)] for every temp directory `expr` can name: a mkdtemp/TemporaryDirectory
    call gives its prefix (and a note when it passes `dir=`, since that dir may sit above or below the root: the caller
    then measures the nesting with _dir_bytes on the call); os.path.join,
    Path, `/` and str(...) over one carry their literal components; a name or attribute is followed through the
    module's assignments (every value it is ever bound to, so a shared local like `d` yields each of its shapes)."""
    if isinstance(expr, ast.Call):
        name = _call_name(expr)
        if name in ("mkdtemp", "TemporaryDirectory"):
            d = _dir_argument(expr)
            note = None if d is None or (isinstance(d, ast.Constant) and d.value is None) else "dir=" + ast.unparse(d)
            return [(_prefix_of(expr), (), note, expr)]
        if name in ("Path", "join", "str", "realpath", "abspath", "fspath") and expr.args:
            rest = expr.args[1:]
            if all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in rest):
                comps = tuple(a.value for a in rest)
                return [(p, c + comps, n, k) for p, c, n, k in _lab_shapes(expr.args[0], assigned, depth)]
            return []
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div) and isinstance(expr.right, ast.Constant):
        return [(p, c + (expr.right.value,), n, k) for p, c, n, k in _lab_shapes(expr.left, assigned, depth)]
    if isinstance(expr, ast.Attribute) and expr.attr == "name":          # TemporaryDirectory().name
        return _lab_shapes(expr.value, assigned, depth)
    if isinstance(expr, (ast.Name, ast.Attribute)) and depth:
        out = []
        for v in assigned.get(ast.unparse(expr), ()):
            out += _lab_shapes(v, assigned, depth - 1)
        return out
    return []


def _names_setting(node):
    """Whether `node` spells the kernel's constant by name: `SESSION_HOSTS_SETTING`, `ht.SESSION_HOSTS_SETTING`, or a
    module's own alias ending in it (kernel/host_transport.py binds it to the literal; no test spells it today, and one
    that starts to is an occurrence the ledger accounts for like the literal)."""
    return ((isinstance(node, ast.Name) and node.id.endswith("SESSION_HOSTS_SETTING"))
            or (isinstance(node, ast.Attribute) and node.attr.endswith("SESSION_HOSTS_SETTING")))


def _setting_leaves(expr, assigned, depth=2):
    """The nodes through which `expr` names the session-hosts FILE NAME: the literal (str or bytes), the kernel's constant
    by name, a name bound to either (the name itself, followed through the bindings), an arm of a conditional. [] when it
    names something else. Every node listed is what the ledger marks as reached by the write that consumed it."""
    if isinstance(expr, ast.Constant):
        return [expr] if expr.value in ("session-hosts", b"session-hosts") else []
    if _names_setting(expr):
        return [expr]
    if isinstance(expr, ast.IfExp):
        return _setting_leaves(expr.body, assigned, depth) + _setting_leaves(expr.orelse, assigned, depth)
    if isinstance(expr, (ast.Name, ast.Attribute)) and depth:
        # The NAME is the consumed node, not the literal behind it: the literal's own site (the assignment, the loop) is
        # accounted for only when EVERY use of the name is, so a second use in an unknown shape is never hidden by this one.
        return [expr] if any(_setting_leaves(v, assigned, depth - 1) for v in assigned.get(ast.unparse(expr), ())) else []
    return []


def _returns(func):
    """The values `func`'s own body returns (a nested def's or lambda's are its own)."""
    out, todo = [], list(func.body)
    while todo:                                                    # loop-ok: an explicit stack, one visit per node
        n = todo.pop()
        if isinstance(n, ast.Return) and n.value is not None:
            out.append(n.value)
        elif not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            todo.extend(ast.iter_child_nodes(n))
    return out


PATH_ARGS = ("Path", "PurePath", "PurePosixPath", "join", "str", "fspath", "realpath", "abspath", "normpath")


def _session_hosts_path(expr, assigned, depth=3):
    """[(state expression, trailing literal components, occurrence nodes consumed)] for every `session-hosts` file `expr`
    can name: Path(<state>, ..., <name>) or os.path.join(...) with literal middle components, `<state> / <name>`,
    Path(<state>).joinpath(..., <name>), open(<one of those>, ...), os.open(...), os.fdopen(<a descriptor bound to one>),
    Path(<one of those>).open(...), Path(<name>), either arm of a conditional, a call to a module function
    that returns one (`toggle(root)` with `def toggle(root): return Path(root, "session-hosts")`), and a name or attribute
    bound to one of those (followed through the bindings: `toggle = os.path.join(root, "session-hosts")` then
    `open(toggle, "w")`; `fd = os.open(...)` then `os.write(fd, ...)`). <name> is the literal, the kernel's constant by
    name or a name bound to either (_setting_leaves). [] when `expr` names no such file. The LAST component decides:
    this reads paths, not values. The consumed nodes are what the ledger marks as reached: the literal when the write's
    own expression holds it, otherwise the indirection (the name, the helper call), so the literal's site is accounted
    for only when every use of that indirection is."""
    if isinstance(expr, ast.IfExp):
        return _session_hosts_path(expr.body, assigned, depth) + _session_hosts_path(expr.orelse, assigned, depth)
    if (isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute) and not expr.args
            and expr.func.attr in ("resolve", "absolute", "expanduser")):
        return _session_hosts_path(expr.func.value, assigned, depth)  # Path(<path>).resolve(): the same path
    if isinstance(expr, ast.Call) and expr.args:
        name = _call_name(expr)
        if name in ("open", "fdopen") and isinstance(expr.func, ast.Attribute) and ast.unparse(expr.func.value) not in MODULES:
            return _session_hosts_path(expr.func.value, assigned, depth)   # Path(<path>).open(mode): the receiver is the path
        if name == "joinpath" and isinstance(expr.func, ast.Attribute):    # Path(<root>).joinpath(..., <name>)
            last, mid = expr.args[-1], expr.args[:-1]
            leaves = _setting_leaves(last, assigned)
            if leaves and all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in mid):
                return [(expr.func.value, tuple(a.value for a in mid), leaves)]
            return []
        if name in PATH_ARGS + ("open", "fdopen"):
            if len(expr.args) >= 2 and name not in ("open", "fdopen"):
                last, mid = expr.args[-1], expr.args[1:-1]
                leaves = _setting_leaves(last, assigned)
                if leaves and all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in mid):
                    return [(expr.args[0], tuple(a.value for a in mid), leaves)]
                return []
            return _session_hosts_path(expr.args[0], assigned, depth)
        if depth:                                                  # a helper of the module that builds the path
            out = []
            for f in assigned.functions(name):
                for r in _returns(f):
                    out += [(s, c, [expr]) for s, c, _ in _session_hosts_path(r, assigned, depth - 1)]
            return out
        return []
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div):
        leaves = _setting_leaves(expr.right, assigned)
        return [(expr.left, (), leaves)] if leaves else []
    if isinstance(expr, (ast.Name, ast.Attribute)) and depth:
        out = []
        for v in assigned.get(ast.unparse(expr), ()):
            out += [(s, c, [expr]) for s, c, _ in _session_hosts_path(v, assigned, depth - 1)]
        return out
    return []


def _written_word(expr, assigned, seen=()):
    """What a session-hosts write puts in the file, read from its value expression: "off" for the literal off (case and
    surrounding whitespace aside, str or bytes), "on" for ANY other literal — the kernel reads the on words and a blank
    file as on and a stray word as off (kernel/host_transport.py session_hosts_read), but the derivation counts every
    write that is not the literal off as a lab that may bind a socket, which is the conservative side; a conditional
    (`"on" if x else "off"`) or a name bound to literals (an assignment, a loop over a literal tuple, a call site's
    argument, a default) by the set of them, any "on" among them making it "on"; None when no literal can be read (a
    call, a formatted string, a name never bound to a literal). None is the LOUD answer: hosts_on_labs lists the site."""
    if isinstance(expr, ast.Constant):
        if isinstance(expr.value, bytes):
            return "off" if expr.value.strip().lower() == b"off" else "on"
        if isinstance(expr.value, str):
            return "off" if expr.value.strip().lower() == "off" else "on"
        return None
    if isinstance(expr, ast.IfExp):
        words = [_written_word(expr.body, assigned, seen), _written_word(expr.orelse, assigned, seen)]
    elif isinstance(expr, (ast.Name, ast.Attribute)):
        key = ast.unparse(expr)
        if key in seen:
            return None
        words = [_written_word(v, assigned, seen + (key,)) for v in assigned.get(key, ())]
    else:
        return None
    if not words or None in words:
        return None
    return "on" if "on" in words else "off"


def _session_hosts_writes(tree, scope_of):
    """(call, [(state expression, components, consumed nodes)], value expression or None, scope) for every write into a
    `session-hosts` file the module makes: `<path>.write_text(v)`, `<path>.write_bytes(v)`, `open(<path>, ...).write(v)`,
    `<name>.write(v)` for a name or attribute bound to an open(<path>) anywhere in the module (a handle bound in setUp,
    written in a test), `fh.write(v)` inside a `with open(<path>, ...) as fh` (the handle scoped to that statement's body,
    since a module reuses one handle name for every file it writes), `os.write(fd, v)` for a descriptor bound to
    os.open(<path>, ...); and, with value None, a REMOVAL or a TOUCH of the file — `<path>.unlink()`, `os.remove(<path>)`,
    `os.unlink(<path>)`, `<path>.touch()`, a truncating open with no handle kept (`with open(<path>, "w"): ...`,
    `open(<path>, "w").close()`) — which leaves no file or an empty one, both of which the kernel reads as on
    (session_hosts_read: the default). The fifth element is the nodes the write consumed, for the ledger to mark: the
    handle name at a `fh.write` (the path's own site is accounted through the handle's every use), else the path's leaves.
    `scope_of(node)` gives the bindings a path or value at that node resolves through (its enclosing function's first)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                if (isinstance(item.optional_vars, ast.Name) and isinstance(item.context_expr, ast.Call)
                        and _call_name(item.context_expr) in ("open", "fdopen") and item.context_expr.args):
                    assigned = scope_of(node)
                    hits = _session_hosts_path(item.context_expr, assigned)
                    if not hits:
                        continue
                    for sub in ast.walk(node):
                        if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "write"
                                and isinstance(sub.func.value, ast.Name) and sub.func.value.id == item.optional_vars.id
                                and sub.args):
                            yield sub, hits, sub.args[0], assigned, [sub.func.value]
                elif (item.optional_vars is None and isinstance(item.context_expr, ast.Call)
                        and _call_name(item.context_expr) == "open" and item.context_expr.args
                        and not _open_reads(item.context_expr)):
                    assigned = scope_of(node)                                  # with open(<path>, "w"): a truncating open
                    hits = _session_hosts_path(item.context_expr, assigned)
                    if hits:
                        yield item.context_expr, hits, None, assigned, [leaf for _, _, leaves in hits for leaf in leaves]
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr, recv = node.func.attr, node.func.value
            on_os = isinstance(recv, ast.Name) and recv.id == "os"
            if on_os and attr == "write" and len(node.args) >= 2:              # os.write(fd, v)
                path, value = node.args[0], node.args[1]
            elif on_os and attr in ("remove", "unlink") and node.args:         # a removal: no file reads as on
                path, value = node.args[0], None
            elif not on_os and attr in ("write_text", "write_bytes", "write") and node.args:
                path, value = recv, node.args[0]
            elif not on_os and attr in ("unlink", "touch"):                    # Path.unlink, Path.touch: none or empty, on
                path, value = recv, None
            elif (attr == "close" and isinstance(recv, ast.Call) and _call_name(recv) == "open" and recv.args
                    and not _open_reads(recv)):                                # open(<path>, "w").close(): truncated, on
                path, value = recv, None
            else:
                continue
            assigned = scope_of(node)
            hits = _session_hosts_path(path, assigned)
            if hits:
                yield node, hits, value, assigned, [leaf for _, _, leaves in hits for leaf in leaves]


# THE LEDGER (2026-09-21, the refuter's finding on the round-2 reader): the guarantee above is closed only over the write
# idioms _session_hosts_writes knows, so a write in any other shape — a copy, a json.dump into a handle, a shell one-liner,
# a Path built through a helper — dropped its lab in silence. Now EVERY occurrence of the session-hosts name in a scanned
# module (every str or bytes constant containing it, every Name or Attribute ending in SESSION_HOSTS_SETTING) is walked
# up to the expression that consumes it and must be REACHED by one of the shapes below, or it is listed in
# `unaccounted` by file, line and source line for the pin to refuse. No per-file allowlist: the shapes are by construction,
# each with the reason it reads or writes nothing the derivation would need to count.
NON_WRITE_SHAPES = {
    "read": "read_text / read_bytes / exists / is_file / is_dir / stat / lstat / samefile on the path, os.path.exists / "
            "isfile / isdir / getsize / getmtime / access / os.stat / os.read on it, open() or Path.open() in a read-only "
            "mode: the file's content is read, never written (resolve / absolute / expanduser / fileno hand the same path "
            "or handle on, and its consumer decides)",
    "comparison": "an operand of ==, !=, in, not in (`last.value == <name>`, `<name> in os.listdir(d)`): a string compared, "
                  "not a path opened",
    "assertion": "an argument of a unittest assert* method (a compared value or its message): compared or printed, never opened",
    "message": "the text of print / fail / skipTest / a log call / an exception being raised / a bare `assert`'s message, or "
               "the VALUE written by .write / .write_text into some file (the word, not the file): displayed or stored as text",
    "docstring": "a string statement (a docstring, a bare string): documentation",
    "parent-dir": "os.path.dirname(<path>) or <path>.parent: the file's own name is dropped and the result names its "
                  "directory (conftest's os.makedirs of it); nothing about the toggle is read or written, unless that "
                  "directory is then removed, renamed or copied into (rmtree, rmdir, rename, move, copytree): unaccounted",
    "inspection": "len / repr / hash / isinstance / type / bool / id of the text, or a str method returning a bool or an int "
                  "(startswith, endswith, count, find, index): a scalar comes out, the text is looked at, not used",
    "reader input": "a (label, text) pair handed to this module's own readers (hosts_on_labs, session_hosts_ledger, "
                    "harness_dirs, longest_prefix, _python_pins): planted source under test, read by the reader in that test",
    "child source": "a Python source handed to a child interpreter (subprocess.run([sys.executable, \"-c\", <text>]), the "
                    "text joined from literal lines, or a command string run whole) is parsed and read as a nested module: "
                    "its writes are classified and its labs counted under `<file>:<line> (a child Python's source)`; a text "
                    "that is not Python (a shell one-liner), or an argv element other than the -c text (a path handed to cp, "
                    "rm, tee), is unaccounted",
    "bound": "a name or attribute bound to the path or the text (`toggle = os.path.join(root, <name>)`, a loop target, a "
             "parameter's default, a helper's return value or parameter): accounted when EVERY use of it, in the binding's "
             "scope, is a classified write or one of the shapes here",
    "handle": "open(<path>, a write mode) or os.open(<path>, flags) bound to a name or a with-target: the path is written "
              "through the handle, so EVERY use of the handle must be a classified write (fh.write, os.write), a read "
              "(os.read) or housekeeping; a handle nothing uses, or one handed to json.dump, is unaccounted",
    "housekeeping": "close / flush / seek / tell on a handle, os.close / os.fsync on a descriptor: nothing written",
}
READ_METHODS = ("read_text", "read_bytes", "exists", "is_file", "is_dir", "is_symlink", "stat", "lstat", "samefile",
                "owner", "group")
SAME_PATH_METHODS = ("resolve", "absolute", "expanduser", "as_posix", "readlink", "fileno")   # the same path or handle again
READ_FUNCTIONS = ("exists", "lexists", "isfile", "isdir", "islink", "stat", "lstat", "fstat", "getsize", "getmtime",
                  "getctime", "getatime", "access", "samefile", "readlink", "read", "pread")
HOUSEKEEPING_METHODS = ("close", "flush", "seek", "tell", "isatty", "readable", "writable", "seekable")
HOUSEKEEPING_FUNCTIONS = ("close", "fsync", "fdatasync", "set_inheritable", "get_inheritable")
MODULES = ("os", "os.path", "shutil", "subprocess", "pathlib", "json", "io", "tempfile", "sys")
DIR_REMOVERS = ("rmtree", "rmdir", "removedirs", "rename", "replace", "move", "copytree")   # the toggle's directory removed,
#                                                                                              renamed or written into
STRING_TEXT_METHODS = ("replace", "strip", "lstrip", "rstrip", "lower", "upper", "format", "join", "split", "rsplit",
                       "splitlines", "encode", "decode", "partition", "rpartition", "removeprefix", "removesuffix",
                       "casefold", "title", "capitalize", "center", "ljust", "rjust", "expandtabs", "translate", "zfill",
                       "items", "keys", "values", "get", "copy")           # a container's texts flow on to its consumer
STRING_INSPECT_METHODS = ("startswith", "endswith", "count", "find", "rfind", "index", "rindex", "isdigit", "isalpha",
                          "isalnum", "isspace", "islower", "isupper", "isidentifier")
PASS_CALLS = PATH_ARGS + ("bytes", "expanduser", "basename", "dedent", "sorted", "list", "set", "tuple", "dict", "frozenset",
                          "reversed", "iter", "next", "map", "filter", "zip", "min", "max", "enumerate", "any", "all", "sum")
INSPECTORS = ("len", "repr", "hash", "isinstance", "type", "bool", "id")
MESSAGE_SINKS = ("print", "fail", "skipTest", "skip", "log", "debug", "info", "warning", "warn", "error", "exception",
                 "critical", "_log")
WRITE_METHODS = ("write", "write_text", "write_bytes")
EXECUTORS = ("run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput", "system", "popen",
             "exec", "eval", "execv", "execvp", "execve", "execvpe", "spawnv", "spawnvp", "spawnl", "spawnlp")
READER_FUNCTIONS = ("hosts_on_labs", "session_hosts_ledger", "harness_dirs", "longest_prefix", "_python_pins", "_shell_pins")
TEXT_PASS_NODES = (ast.JoinedStr, ast.FormattedValue, ast.Tuple, ast.List, ast.Set, ast.Dict, ast.IfExp, ast.keyword,
                   ast.Starred, ast.Subscript, ast.BinOp, ast.BoolOp, ast.Await, ast.Yield, ast.ListComp, ast.SetComp,
                   ast.GeneratorExp, ast.DictComp, ast.comprehension, ast.Slice)


def _path_method(call):
    """A call spelled like a str method that is a path's or a module's instead: `replace` with one argument is
    Path.replace(target) (str.replace takes two), `copy` with any argument is shutil's (a container's copy takes none),
    and a bare name (`from shutil import copy; copy(...)`) is never a str method."""
    if not isinstance(call.func, ast.Attribute) or _on_module(call):
        return True
    name = call.func.attr
    return (name == "replace" and len(call.args) < 2) or (name == "copy" and bool(call.args))


def _on_module(call):
    """Whether `call` is a module's function (os.replace, shutil.copy) rather than a method on a value (a str's replace)."""
    return isinstance(call.func, ast.Attribute) and ast.unparse(call.func.value) in MODULES


def _open_reads(call):
    """True when an open(...) call reads only: no mode, or a literal mode without w, a, x or +. The mode is the second
    argument of the builtin open, os.open (whose flags the reader cannot read: False) and os.fdopen, the first of Path.open."""
    method = isinstance(call.func, ast.Attribute) and ast.unparse(call.func.value) not in MODULES
    return _read_mode(call, 0 if method else 1)


def _read_mode(call, pos):
    """True when an open(...) (pos 1) or Path.open(...) (pos 0) reads only: no mode, or a literal without w, a, x or +."""
    mode = next((k.value for k in call.keywords if k.arg == "mode"), None)
    if mode is None and len(call.args) > pos:
        mode = call.args[pos]
    if mode is None:
        return True
    return isinstance(mode, ast.Constant) and isinstance(mode.value, str) and not any(c in mode.value for c in "wax+")


def _occurrences(tree):
    """Every node that spells the session-hosts name: a str constant containing it (a path component, a message, a
    docstring, a script) or containing the constant's name (`getattr(ht, "SESSION_HOSTS_SETTING")`), a bytes constant
    containing it, a Name or Attribute ending in SESSION_HOSTS_SETTING, an import alias of it. The name spelled in pieces
    (`"session-" + "hosts"`) is outside the reader."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            v = node.value
            if (isinstance(v, str) and ("session-hosts" in v or "SESSION_HOSTS_SETTING" in v)) or (isinstance(v, bytes) and b"session-hosts" in v):
                yield node
        elif _names_setting(node) and isinstance(node.ctx, ast.Load):    # a Store target is the binding, not a use
            yield node
        elif isinstance(node, ast.alias) and node.name.endswith("SESSION_HOSTS_SETTING"):
            yield node                                             # `from kernel.host_transport import SESSION_HOSTS_SETTING as X`


def _child_source(chain):
    """The Python text a child interpreter is handed, reconstructed from the constants on the way from an occurrence to
    the executor: `<sep>.join([...])` of literal lines (a non-literal element becomes `pass`, so the line count holds),
    else the occurrence's own string. None when neither is a string."""
    for node in chain:
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "join"
                and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str)
                and node.args and isinstance(node.args[0], (ast.List, ast.Tuple))):
            return node.func.value.value.join(e.value if isinstance(e, ast.Constant) and isinstance(e.value, str) else "pass"
                                              for e in node.args[0].elts)
    leaf = chain[0]
    return leaf.value if isinstance(leaf, ast.Constant) and isinstance(leaf.value, str) else None


def _loop_target(target, iterable, chain):
    """The Name a loop binds the occurrence to: the target itself; the column of a loop over rows (`for name, value in
    ((<name>, "on"),)`); the second element of an `enumerate(...)` target. None when the reader cannot map it."""
    if isinstance(iterable, ast.Call) and _call_name(iterable) == "enumerate" and isinstance(target, (ast.Tuple, ast.List)):
        target = target.elts[1] if len(target.elts) == 2 else None
    elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(iterable, (ast.Tuple, ast.List)):
        row = next((e for e in iterable.elts if isinstance(e, (ast.Tuple, ast.List)) and any(c in e.elts for c in chain)), None)
        j = next((i for i, c in enumerate(row.elts) if c in chain), None) if row is not None else None
        target = target.elts[j] if j is not None and j < len(target.elts) else None
    return target if isinstance(target, ast.Name) else None


BINDING_HOPS = 6      # bindings followed from an occurrence to its uses (a name, a handle, a lambda, a helper...); cycles are
#                       caught by `seen`, so this only bounds the walk (a test's text bound four names deep needed 4)


def _executed(chain):
    """Whether the text on `chain` (from the occurrence up to the executor's argument) is what the child EXECUTES: the
    command string itself (`run("...", shell=True)`, `os.system`, `exec`), or the element after `-c` in an argv list. Any
    other argv element (`["cp", src, <the toggle's path>]`, `["rm", "-f", ...]`) is a path or a word handed to a program:
    not a source the reader can read, so unaccounted (the refuter's second pass, 2026-09-21)."""
    top = chain[-1]
    if isinstance(top, (ast.List, ast.Tuple)):
        inner = next((e for e in top.elts if e in chain), None)
        j = top.elts.index(inner) if inner is not None else -1
        return j >= 1 and isinstance(top.elts[j - 1], ast.Constant) and top.elts[j - 1].value == "-c"
    return not isinstance(top, ast.keyword) or top.arg in ("args", "cmd", "command")


class _Ledger:
    """One module's account of the session-hosts name (hosts_on_labs runs one per module, and one per child source it
    finds): the writes _session_hosts_writes classifies mark the nodes they consumed as reached; every other occurrence is
    walked up from its node to the expression that consumes it and given a NON_WRITE_SHAPES category, or None. Results:
    `labs`, `unresolved`, `opaque` as hosts_on_labs documents them; `unaccounted`, the `label:line: source line` of every
    occurrence with no category (a bound name's first unaccounted use named); `entries`, [(line, category, source line)]
    for every occurrence of this module's own text."""

    def __init__(self, label, text, tail, depth=2, tree=None):
        self.label, self.text, self.tail, self.depth = label, text, tail, depth
        self.tree = tree if tree is not None else ast.parse(text)
        self.lines = text.splitlines()
        self.bindings = _Bindings(self.tree)
        self.parents = {c: p for p in ast.walk(self.tree) for c in ast.iter_child_nodes(p)}
        self.reached, self.why = {}, {}
        self.labs, self.unresolved, self.opaque, self.unaccounted, self.entries = [], [], [], [], []
        self._run()

    def _scope(self, node):
        return _Scope(self.bindings, node)

    def _site(self, node):
        return "%s:%d: %s" % (self.label, node.lineno, self.lines[node.lineno - 1].strip())

    def _run(self):
        for node, hits, value, assigned, consumed in _session_hosts_writes(self.tree, self._scope):
            word = "on" if value is None else _written_word(value, assigned)  # None value: a removal, a touch, a truncation
            category = "write:" + (word or "opaque")
            for leaf in consumed:
                self.reached.setdefault(id(leaf), set()).add(category)
            if word == "off":
                continue
            if word is None:
                self.opaque.append("%s:%d: %s" % (self.label, node.lineno, ast.unparse(value)))
            for expr, comps, _ in hits:
                shapes = _lab_shapes(expr, assigned)              # the enclosing function's bindings first...
                if not shapes:
                    shapes = _lab_shapes(expr, assigned.module)   # ...then the module's, for a root a caller handed in
                shapes = [(p, c + comps, n, k) for p, c, n, k in shapes]
                if not shapes or any(p is None for p, _, _, _ in shapes):
                    self.unresolved.append("%s:%d: %s" % (self.label, node.lineno, ast.unparse(expr)))
                    continue
                note = "no file, or an empty one, reads as on (a removal, a touch, a truncating open)" if value is None else None
                by_shape = {}                                      # one lab per SHAPE (prefix, components, note), whichever call
                for prefix, cs, n, call in shapes:
                    by_shape.setdefault((prefix, cs, n), call)
                for (prefix, cs, n), call in by_shape.items():
                    tail_bytes = sum(1 + len(os.fsencode(c)) for c in cs)
                    if n:                                          # minted under dir=: the nesting counted, as harness_dirs counts it
                        deep = [b for b, _, _ in _dir_bytes(call, assigned, self.tail)]
                        if not deep or None in deep:
                            self.unresolved.append("%s:%d: %s (%s)" % (self.label, node.lineno, ast.unparse(expr), n))
                            continue
                        below = max(deep) + tail_bytes
                    else:
                        below = 1 + len(os.fsencode(prefix)) + self.tail + tail_bytes
                    self.labs.append(Lab(below, self.label, node.lineno, prefix, cs, n or note))
        for leaf in _occurrences(self.tree):
            cats = self.reached.get(id(leaf))
            category = ", ".join(sorted(cats)) if cats else self._account(leaf, (), BINDING_HOPS)
            self.entries.append((leaf.lineno, category, self.lines[leaf.lineno - 1].strip()))
            if category is None:
                why = self.why.get(id(leaf)) or next((w for w in self.why.values()), None) if self.why else None
                self.unaccounted.append(self._site(leaf) + (" (%s)" % why if why else ""))
            self.why.clear()

    def _uses(self, key, at):
        """Every load of `key` (a Name's or Attribute's source text) in scope at `at`: the enclosing function's body for a
        plain local name, the whole module for an attribute or a module-level name."""
        owner = self.bindings.built().owner.get(at)
        scope = owner if owner is not None and "." not in key else self.tree
        keys = {key}
        if isinstance(self.parents.get(at), ast.ClassDef):          # a class attribute: read as self.<name> or cls.<name> too
            keys |= {"self." + key, "cls." + key}
        return [n for n in ast.walk(scope) if isinstance(n, (ast.Name, ast.Attribute))
                and isinstance(n.ctx, ast.Load) and ast.unparse(n) in keys]

    def _all(self, nodes, seen, depth, origin):
        """The atomic categories of every node in `nodes` (a bound name's uses, a helper's calls, a parameter's reads, a
        handle's uses), or None when one is unaccounted, its site recorded against `origin`. No uses at all is None too: a
        dead binding, a handle nothing writes through."""
        if not nodes or not depth:
            return None
        cats = set()
        for n in nodes:
            if id(n) in self.reached:
                cats |= self.reached[id(n)]
                continue
            c = self._account(n, seen, depth - 1)
            if c is None:
                self.why.setdefault(id(origin), "through " + self._site(n))
                return None
            for prefix in ("bound: ", "handle: "):
                if c.startswith(prefix):
                    c = c[len(prefix):]
            cats |= set(c.split(", "))
        return cats

    def _account(self, leaf, seen, depth):
        """The NON_WRITE_SHAPES category through which the occurrence `leaf` is accounted for, or None."""
        if id(leaf) in seen:
            return None
        seen = seen + (id(leaf),)
        node, chain = leaf, [leaf]
        while True:                                                # loop-ok: one step up the tree per turn, ends at a stmt
            parent = self.parents.get(node)
            if parent is None:
                return None
            if isinstance(parent, ast.Expr):
                return "docstring" if isinstance(node, (ast.Constant, ast.JoinedStr)) else None
            if isinstance(parent, ast.Compare):
                return "comparison"
            if isinstance(parent, ast.Assert):
                return "message"
            if isinstance(parent, TEXT_PASS_NODES):
                node = parent
                chain.append(node)
                continue
            if isinstance(parent, ast.Attribute):
                grand = self.parents.get(parent)
                if isinstance(grand, ast.Call) and grand.func is parent:
                    m = parent.attr
                    if m in SAME_PATH_METHODS or (m in STRING_TEXT_METHODS and not _path_method(grand)):
                        node = grand                               # the same path, handle or text again: its consumer decides
                        chain.append(node)
                        continue
                    if m in READ_METHODS:
                        return "read"
                    if m == "open":
                        return "read" if _open_reads(grand) else self._handle(grand, seen, depth)
                    if m in STRING_INSPECT_METHODS:
                        return "inspection"
                    if m in HOUSEKEEPING_METHODS:
                        return "housekeeping"
                    return None                                    # a write, a removal, a rename the reader did not classify
                if parent.attr in ("parent", "parents"):
                    return self._parent_dir(parent)
                if parent.attr in ("name", "stem", "suffix", "suffixes", "parts", "anchor"):
                    node = parent
                    chain.append(node)
                    continue
                return None
            if isinstance(parent, ast.Call):
                name = _call_name(parent)
                if parent.func is node:                            # a bound lambda's name called: its result flows on
                    node = parent
                    chain.append(node)
                    continue
                if name in READER_FUNCTIONS:
                    return "reader input"                          # this module's own readers: the text is what they read
                funcs = list(self.bindings.built().functions.get(name, ()))      # a def of the module, or a lambda bound
                funcs += [v for v in self._scope(parent).get(name, ()) if isinstance(v, ast.Lambda)]   # to the name
                if funcs:                                          # before the sink rules: a module's own `write` or `log` is followed
                    return self._joined("bound", self._all(self._param_uses(funcs, parent, node), seen, depth, leaf))
                if name == "print" and isinstance(node, ast.keyword) and node.arg == "file":
                    return None                                    # print(..., file=fh): a write through the handle
                if name in PASS_CALLS or (name in STRING_TEXT_METHODS and not _path_method(parent)):
                    node = parent                                  # the result is a path or a text again: its consumer decides
                    chain.append(node)
                    continue
                if name in STRING_INSPECT_METHODS and not _path_method(parent):
                    return "inspection"
                if name == "dirname":
                    return self._parent_dir(parent)
                if name in READ_FUNCTIONS:
                    return "read"
                if name in ("open", "fdopen"):
                    return "read" if _open_reads(parent) else self._handle(parent, seen, depth)
                if name in HOUSEKEEPING_FUNCTIONS:
                    return "housekeeping"
                if name and name.startswith("assert"):
                    return "assertion"
                if name in MESSAGE_SINKS or isinstance(self.parents.get(parent), ast.Raise):
                    return "message"
                if name in WRITE_METHODS and node in parent.args:
                    return "message"
                if name in INSPECTORS:
                    return "inspection"
                if name in EXECUTORS:
                    return self._child(leaf, chain)
                return None
            if isinstance(parent, (ast.Assign, ast.AnnAssign)) and node is parent.value:
                targets = parent.targets if isinstance(parent, ast.Assign) else [parent.target]
                uses = []
                for t in targets:
                    if isinstance(t, (ast.Tuple, ast.List)) and isinstance(node, (ast.Tuple, ast.List)) and len(t.elts) == len(node.elts):
                        j = next((i for i, e in enumerate(node.elts) if e in chain), None)     # `a, p = 1, <path>`: p
                        t = t.elts[j] if j is not None else None
                    if isinstance(t, (ast.Name, ast.Attribute)):
                        uses += self._uses(ast.unparse(t), parent)
                    else:
                        return None                                # a target the reader cannot map
                return self._joined("bound", self._all(uses, seen, depth, leaf))
            if isinstance(parent, ast.For) and node is parent.iter:
                target = _loop_target(parent.target, node, chain)
                if target is None:
                    return None
                uses = [n for n in ast.walk(parent) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == target.id]
                return self._joined("bound", self._all(uses, seen, depth, leaf))
            if isinstance(parent, ast.ImportFrom):
                return self._joined("bound", self._all(self._uses(node.asname or node.name, parent), seen, depth, leaf))
            if isinstance(parent, ast.Lambda) and node is parent.body:
                binding = self.parents.get(parent)                 # `line = lambda m: ...`: the lambda's value reaches its callers
                if isinstance(binding, ast.Assign) and binding.value is parent:
                    uses = []
                    for t in binding.targets:
                        if not isinstance(t, (ast.Name, ast.Attribute)):
                            return None
                        uses += self._uses(ast.unparse(t), binding)
                    return self._joined("bound", self._all(uses, seen, depth, leaf))
                node = parent                                      # an inline lambda: its consumer decides
                chain.append(node)
                continue
            if isinstance(parent, ast.comprehension) and node is parent.iter:
                target = _loop_target(parent.target, node, chain)
                if target is None:
                    return None
                comp = self.parents.get(parent)
                uses = [n for n in ast.walk(comp) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == target.id]
                return self._joined("bound", self._all(uses, seen, depth, leaf))
            if isinstance(parent, ast.Return):
                func = self.bindings.built().owner.get(parent)
                calls = self.bindings.built().calls.get(func.name, ()) if func is not None else ()
                return self._joined("bound", self._all(list(calls), seen, depth, leaf))
            if isinstance(parent, ast.arguments):
                func = self.parents.get(parent)
                params = parent.posonlyargs + parent.args
                named = dict(zip(params[len(params) - len(parent.defaults):], parent.defaults))
                named.update((a, d) for a, d in zip(parent.kwonlyargs, parent.kw_defaults) if d is not None)
                for arg, default in named.items():
                    if default is node:
                        uses = [n for n in ast.walk(func) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                                and n.id == arg.arg]
                        return self._joined("bound", self._all(uses, seen, depth, leaf))
                return None
            return None

    def _parent_dir(self, node):
        """os.path.dirname(<path>) or <path>.parent: the file's own name is dropped, unless the directory is then removed or
        renamed (shutil.rmtree, os.rmdir, .rmdir(), os.rename, shutil.move), which takes the toggle with it: a removal the
        reader does not classify, so None."""
        consumer = self.parents.get(node)
        if isinstance(consumer, ast.Call) and node in consumer.args and _call_name(consumer) in DIR_REMOVERS:
            return None
        if isinstance(consumer, ast.Attribute) and consumer.attr in DIR_REMOVERS:
            grand = self.parents.get(consumer)
            if isinstance(grand, ast.Call) and grand.func is consumer:
                return None
        return "parent-dir"

    def _handle(self, call, seen, depth):
        """A write-mode (or unreadable-mode) open of the path: the handle is bound by an assignment or a with-target, and
        every use of it decides (a classified `fh.write` / `os.write` is marked; os.read is a read; close is housekeeping;
        anything else is unaccounted). An open whose handle nothing keeps is None: a truncating open the write reader did
        not classify."""
        parent = self.parents.get(call)
        if isinstance(parent, (ast.Assign, ast.AnnAssign)) and call is parent.value:
            uses = []
            for t in (parent.targets if isinstance(parent, ast.Assign) else [parent.target]):
                if not isinstance(t, (ast.Name, ast.Attribute)):
                    return None
                uses += self._uses(ast.unparse(t), parent)
        elif isinstance(parent, ast.withitem) and isinstance(parent.optional_vars, ast.Name):
            with_node = self.parents.get(parent)
            uses = [n for n in ast.walk(with_node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                    and n.id == parent.optional_vars.id]
        else:
            return None
        atoms = self._all(uses, seen, depth, call)
        if atoms is not None and not any(a.startswith("write:") or a == "read" for a in atoms):
            # Opened for writing (or with flags the reader cannot read), never written through, never read: `open(p, "w")`
            # truncates the file to empty, which reads as on — a write the reader has not classified, so the site is named.
            self.why.setdefault(id(call), "a handle opened for writing that nothing writes through or reads: %s; the empty "
                                          "file reads as on" % "; ".join(self._site(u) for u in uses))
            return None
        return self._joined("handle", atoms)

    @staticmethod
    def _joined(prefix, atoms):
        return None if atoms is None else "%s: %s" % (prefix, ", ".join(sorted(atoms)))

    def _param_uses(self, funcs, call, arg):
        """The loads, inside each of `funcs` (defs or lambdas), of the parameter that `arg` (a positional or keyword
        argument of `call`) binds — the path or text flows into the helper; its uses there are what must be accounted."""
        uses = []
        for f in funcs:
            params = [a.arg for a in f.args.posonlyargs + f.args.args]
            if params and params[0] in ("self", "cls"):
                params = params[1:]
            name = None
            if isinstance(arg, ast.keyword):
                name = arg.arg if arg.arg in params + [a.arg for a in f.args.kwonlyargs] else None
            elif arg in call.args and not any(isinstance(a, ast.Starred) for a in call.args):
                i = call.args.index(arg)
                name = params[i] if i < len(params) else None
            else:
                name = next((k.arg for k in call.keywords if k.value is arg), None)
            if name:
                uses += [n for n in ast.walk(f) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == name]
        return uses

    def _child(self, leaf, chain):
        """A text handed to an executor: Python is read as a nested module (its labs and holes merged here under a label
        naming the site); anything else is unaccounted."""
        text = _child_source(chain)
        if text is None or not self.depth or not _executed(chain):
            return None
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return None
        nested = _Ledger("%s:%d (a child Python's source)" % (self.label, leaf.lineno), text, self.tail, self.depth - 1, tree)
        if not nested.entries:
            return None                                            # the name is not in the text as Python reads it
        self.labs += nested.labs
        self.unresolved += nested.unresolved
        self.opaque += nested.opaque
        self.unaccounted += nested.unaccounted
        return "child source"


def session_hosts_ledger(label, text, tail):
    """(labs, unresolved, opaque, unaccounted, entries) for one module's text: hosts_on_labs's four lists for it, and
    [(line, category, source line)] for EVERY occurrence of the session-hosts name in it, category None for one nothing
    reached (the same occurrence is then in `unaccounted`). For the planted-source tests and a reader's probe."""
    ledger = _Ledger(label, text, tail)
    return ledger.labs, ledger.unresolved, ledger.opaque, ledger.unaccounted, ledger.entries


def hosts_on_labs(sources, tail):
    """(labs, unresolved, opaque, unaccounted): one Lab per shape of state root a test turns hosts ON in, read from
    `sources` ([(label, text)]): bytes below the process temp root = `/` + prefix + mkdtemp's tail + each `/component`.
    EVERY write into a `session-hosts` file counts as hosts-on unless its value reads as the literal off (2026-09-21; until
    then only a literal "on" counted, and a value the reader could not see — a loop variable, a helper's argument, a
    handle — silently dropped its lab from the bound); a removal or a touch of the file counts too (no file, or an empty
    one, reads as on). `unresolved` lists the hosts-on sites whose state root the reader could not follow to a mkdtemp;
    `opaque` lists the writes whose VALUE it could not read (their labs are counted all the same, as hosts-on);
    `unaccounted` lists every occurrence of the session-hosts name (the literal in any string, the kernel's constant by
    name) that no classified write, read, comparison, message, docstring, bound name or child source reached
    (NON_WRITE_SHAPES; the refuter's finding of 2026-09-21: until then a write in an unknown shape was dropped in silence).
    All three are holes in the bound, for the caller to refuse by name. Outside the reader, stated: the name spelled in
    pieces (`"session-" + "hosts"`), and a helper's parameter bound from a call in ANOTHER module (the bindings are per
    module; such a helper's own module gives its labs)."""
    labs, unresolved, opaque, unaccounted = [], [], [], []
    for label, text in sources:
        if "session-hosts" not in text and "SESSION_HOSTS_SETTING" not in text:
            continue
        ledger = _Ledger(label, text, tail)
        labs += ledger.labs
        unresolved += ledger.unresolved
        opaque += ledger.opaque
        unaccounted += ledger.unaccounted
    return labs, unresolved, opaque, unaccounted


def longest_prefix(sources):
    """(bytes, prefix, label, line) of the longest literal prefix any tempfile.mkdtemp or TemporaryDirectory
    in `sources` names — every test module, whether or not its lab turns hosts on."""
    best = (0, "", "", 0)
    for label, text in sources:
        if "mkdtemp" not in text and "TemporaryDirectory" not in text:
            continue
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Call) and _call_name(node) in ("mkdtemp", "TemporaryDirectory"):
                p = _prefix_of(node)
                if p is not None and len(os.fsencode(p)) > best[0]:
                    best = (len(os.fsencode(p)), p, label, node.lineno)
    return best


Dir = collections.namedtuple("Dir", "bytes file line chain")


def _literal_str(expr, assigned, seen=()):
    """The LONGEST string `expr` can be, read statically: a literal; `a + b` of two readable parts; a name or attribute
    through every binding it has (a parameter through its call sites), the longest of them. None when any part cannot
    be read (a call, a formatted string, a name never bound to a literal)."""
    if isinstance(expr, ast.Constant):
        return expr.value if isinstance(expr.value, str) else None
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
        left, right = _literal_str(expr.left, assigned, seen), _literal_str(expr.right, assigned, seen)
        return None if left is None or right is None else left + right
    if isinstance(expr, (ast.Name, ast.Attribute)):
        key = ast.unparse(expr)
        if key in seen:
            return None
        values = [_literal_str(v, assigned, seen + (key,)) for v in assigned.get(key, ())]
        if not values or None in values:
            return None
        return max(values, key=lambda v: len(os.fsencode(v)))
    return None


def _name_part(call, part, assigned):
    """The `prefix` or `suffix` a mkdtemp/TemporaryDirectory call names (keyword or positional: suffix, prefix, dir),
    followed through a name's bindings to the longest string it can be; the default ("tmp" for the prefix, "" for the
    suffix) when it names none or None; None when it cannot be read."""
    pos = {"suffix": 0, "prefix": 1}[part]
    expr = next((k.value for k in call.keywords if k.arg == part), None)
    if expr is None and len(call.args) > pos and not any(isinstance(a, ast.Starred) for a in call.args):
        expr = call.args[pos]
    if expr is None or (isinstance(expr, ast.Constant) and expr.value is None):
        return "tmp" if part == "prefix" else ""
    return _literal_str(expr, assigned)


# A mkdtemp's `dir=` that names a directory AT OR ABOVE the run's root, by shape, each with the reason it is scored as
# directly under the root (the deeper of the two readings) rather than listed as unfollowed.
ABOVE_ROOT_DIR_SHAPES = {
    "system_tmp()": "tests/test_session_host.py's system_tmp(): the recorded system dir (ROMP_TESTS_SYSTEM_TMPDIR), above the "
                    "run's root, the sanctioned way out of it for an AF_UNIX path built to an exact length",
    "ROMP_TESTS_SYSTEM_TMPDIR": "the recorded system dir read directly (os.environ[...], os.environ.get(...), the package's "
                                "SYSTEM_TMPDIR), alone or with `or tempfile.gettempdir()`, `or None`, or in a conditional whose "
                                "other arm is None: above the run's root, or the default when the record is unset",
    "tempfile.gettempdir()": "the process temp dir, which the package redirected to the root: a mint there sits directly under "
                             "it, the default reading",
    "~": "the user's home (os.path.expanduser(\"~\"), Path.home(), os.environ[\"HOME\"], through str() or Path() and a "
         "name bound to one): outside the run's root altogether (tests/test_kernel_sysmeta.py fabricates a repo under HOME "
         "to see the ~ abbreviation); scored as directly under the root, since HOME is no path the harness makes or bounds",
}


def _above_root_leaf(expr, assigned, depth):
    if isinstance(expr, ast.Call):
        name = _call_name(expr)
        if name == "system_tmp":
            return "system_tmp()"
        if name == "gettempdir":
            return "tempfile.gettempdir()"
        if name == "expanduser" and len(expr.args) == 1 and isinstance(expr.args[0], ast.Constant) and expr.args[0].value == "~":
            return "~"
        if name == "home" and isinstance(expr.func, ast.Attribute) and ast.unparse(expr.func.value) == "Path" and not expr.args:
            return "~"
        if name in ("str", "Path", "fspath") and len(expr.args) == 1:
            return _above_root(expr.args[0], assigned, depth)
        if (name == "get" and isinstance(expr.func, ast.Attribute) and ast.unparse(expr.func.value) == "os.environ"
                and expr.args and isinstance(expr.args[0], ast.Constant) and expr.args[0].value == "ROMP_TESTS_SYSTEM_TMPDIR"
                and (len(expr.args) == 1 or _above_root(expr.args[1]))):
            return "ROMP_TESTS_SYSTEM_TMPDIR"
        return None
    if isinstance(expr, ast.Subscript) and ast.unparse(expr.value) == "os.environ" and isinstance(expr.slice, ast.Constant):
        return {"ROMP_TESTS_SYSTEM_TMPDIR": "ROMP_TESTS_SYSTEM_TMPDIR", "HOME": "~"}.get(expr.slice.value)
    if isinstance(expr, (ast.Name, ast.Attribute)):
        if ast.unparse(expr).endswith("SYSTEM_TMPDIR"):
            return "ROMP_TESTS_SYSTEM_TMPDIR"
        if assigned is not None and depth:                         # `home = Path(os.path.expanduser("~"))` then dir=str(home)
            keys = [_above_root(v, assigned, depth - 1) for v in assigned.get(ast.unparse(expr), ())]
            return keys[0] if keys and None not in keys and len(set(keys)) == 1 else None
    return None


def _above_root(expr, assigned=None, depth=3):
    """The ABOVE_ROOT_DIR_SHAPES key `expr` matches ("None" for the literal None, the default), or None. EVERY leaf of the
    expression, through `or`, a conditional, str()/Path() and a name's bindings, must be one of the shapes or None, so a
    dir= the reader cannot follow is never waved through because a system-dir read sits somewhere inside it."""
    if isinstance(expr, ast.Constant) and expr.value is None:
        return "None"
    if isinstance(expr, ast.BoolOp) and isinstance(expr.op, ast.Or):
        keys = [_above_root(v, assigned, depth) for v in expr.values]
    elif isinstance(expr, ast.IfExp):
        keys = [_above_root(expr.body, assigned, depth), _above_root(expr.orelse, assigned, depth)]
    else:
        keys = [_above_root_leaf(expr, assigned, depth)]
    if None in keys:
        return None
    return next((k for k in keys if k != "None"), "None")


def _dir_bytes(expr, assigned, tail, depth=4):
    """[(bytes below the process temp root, chain)] for every directory `expr` can name, NESTING INCLUDED: a
    mkdtemp/TemporaryDirectory with no `dir=` sits directly under the root (`/` + prefix + tail + suffix); one with
    `dir=<expr>` sits under each directory <expr> names, its bytes added; one whose `dir=` the reader cannot follow is a
    hole the caller lists, unless the dir is one of the ABOVE_ROOT_DIR_SHAPES (the recorded system dir, system_tmp(),
    the process temp dir), which sit at or above the root and are scored as directly under it, the deeper reading (until
    2026-09-21 EVERY unfollowed dir= was scored that way, in silence); os.path.join, Path, `/` and str(...) add their
    literal components; a name is followed through its bindings. Each answer is (bytes, chain, problem): a prefix or
    suffix that cannot be read, or a dir= neither followed nor one of those shapes, gives bytes None with the call's text
    as the chain and the problem named ("unreadable", "unfollowed"): the caller lists it."""
    if isinstance(expr, ast.Call):
        name = _call_name(expr)
        if name in ("mkdtemp", "TemporaryDirectory"):
            prefix, suffix = _name_part(expr, "prefix", assigned), _name_part(expr, "suffix", assigned)
            if prefix is None or suffix is None:
                return [(None, ast.unparse(expr), "unreadable")]
            own = 1 + len(os.fsencode(prefix)) + tail + len(os.fsencode(suffix))
            chain = "/" + prefix + "X" * tail + suffix
            d = _dir_argument(expr)
            if d is None or (isinstance(d, ast.Constant) and d.value is None):
                return [(own, chain, None)]
            parents = _dir_bytes(d, assigned, tail, depth)
            if parents:
                return [(None, c, p) if b is None else (b + own, c + chain, None) for b, c, p in parents]
            if _above_root(d, assigned):
                return [(own, chain, None)]               # at or above the root: scored as directly under it, the deeper reading
            return [(None, chain + " dir=" + ast.unparse(d), "unfollowed")]
        if name in ("Path", "join", "str", "realpath", "abspath", "fspath") and expr.args:
            rest = expr.args[1:]
            if all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in rest):
                add, comps = sum(1 + len(os.fsencode(a.value)) for a in rest), "".join("/" + a.value for a in rest)
                return [(None, c, p) if b is None else (b + add, c + comps, None)
                        for b, c, p in _dir_bytes(expr.args[0], assigned, tail, depth)]
        return []
    if (isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div) and isinstance(expr.right, ast.Constant)
            and isinstance(expr.right.value, str)):
        add = 1 + len(os.fsencode(expr.right.value))
        return [(None, c, p) if b is None else (b + add, c + "/" + expr.right.value, None)
                for b, c, p in _dir_bytes(expr.left, assigned, tail, depth)]
    if isinstance(expr, ast.Attribute) and expr.attr == "name":          # TemporaryDirectory().name
        return _dir_bytes(expr.value, assigned, tail, depth)
    if isinstance(expr, (ast.Name, ast.Attribute)) and depth:
        out = []
        for v in assigned.get(ast.unparse(expr), ()):
            out += _dir_bytes(v, assigned, tail, depth - 1)
        return out
    return []


def harness_dirs(sources, tail):
    """(dirs, unreadable, unfollowed): every directory the tests' own tempfile.mkdtemp and TemporaryDirectory calls can
    make, one Dir per shape (bytes below the process temp root with the nesting through `dir=` followed, the module, the
    line, the chain of names with mkdtemp's tail as X's); `unreadable` lists the calls whose prefix or suffix the reader
    cannot read; `unfollowed` lists the calls whose `dir=` it can neither follow to a mkdtemp nor match to one of the
    ABOVE_ROOT_DIR_SHAPES (until 2026-09-21 such a call was scored as sitting directly under the root, in silence). Both
    are holes in the bound for the caller to refuse by name. The mints of romp itself under a state root (sdk/,
    hosts/<sid>/, sessions/) are the product's shapes, not the harness's, and a directory a test makes with os.mkdir or
    os.makedirs under one of these is outside the scan too: the arms measure the mkdtemp/TemporaryDirectory paths."""
    dirs, unreadable, unfollowed = [], [], []
    for label, text in sources:
        if "mkdtemp" not in text and "TemporaryDirectory" not in text:
            continue
        tree = ast.parse(text)
        scope_of = _scoper(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_name(node) in ("mkdtemp", "TemporaryDirectory"):
                for b, chain, problem in dict.fromkeys(_dir_bytes(node, scope_of(node), tail)):
                    if b is None:
                        (unfollowed if problem == "unfollowed" else unreadable).append("%s:%d: %s" % (label, node.lineno, chain))
                    else:
                        dirs.append(Dir(b, label, node.lineno, chain))
    return dirs, unreadable, unfollowed


def tree_sources():
    """(label, text) for every tests/*.py: the same glob the literal-pin rule reads."""
    return [(os.path.relpath(path, ROOT), open(path, encoding="utf-8").read())
            for path in sorted(glob.glob(os.path.join(HERE, "*.py")))]


def harness_bytes(root, system):
    """(bytes, levels) the harness spends between the recorded system dir and a process's root: the `/`-led
    relative path's byte length and its component count, measured on the root itself."""
    rel = os.path.relpath(os.path.realpath(root), os.path.realpath(system))
    return len(os.fsencode(rel)) + 1, len(rel.split(os.sep))


def deepest_socket_path(tmpdir_bytes, harness, lab, sock_bytes):
    return tmpdir_bytes + harness.bytes + lab.bytes + sock_bytes


def assert_socket_fits(case, what, tmpdir_bytes, harness, lab, sock_bytes, budget, min_margin=0):
    """The one assertion, with the whole derivation in its message; returns (total, margin)."""
    total = deepest_socket_path(tmpdir_bytes, harness, lab, sock_bytes)
    margin = budget - total
    shape = "`%s` + mkdtemp tail%s" % (lab.prefix, "".join("/" + c for c in lab.comps) and " + `%s`" % "".join("/" + c for c in lab.comps))
    case.assertGreaterEqual(
        margin, min_margin,
        "%s: the longest hosts-on socket path the harness can produce UNDER XDIST NESTING (a worker's root beside the "
        "controller's, measured on roots minted that way; running the lab's test alone verifies nothing about this figure) "
        "is %d bytes = %d (TMPDIR) + %d (%d romp-tests-* root level(s), measured on roots the harness minted) + %d (the lab: "
        "%s, %s:%d%s) + %d (`/hosts/<sid8>.sock`, the kernel's host_sock and sock_names); held against SOCK_PATH_MAX = %d "
        "(sun_path less its NUL, kernel/session_host.py), so the margin is %d and at least %d is required. Every process "
        "must mint its root directly under the recorded system temp dir (beside its parent, never inside), and the run's "
        "TMPDIR may be at most %d bytes."
        % (what, total, tmpdir_bytes, harness.bytes, harness.levels, lab.bytes, shape, lab.file, lab.line,
           "; " + lab.note if lab.note else "", sock_bytes, budget, margin, min_margin, budget - (total - tmpdir_bytes)))
    return total, margin


def _pathconf(path, name, default):
    """os.pathconf(path, name), or `default` where the name or the call is unavailable."""
    try:
        value = os.pathconf(path, name)
        return value if value and value > 0 else default
    except (OSError, ValueError, AttributeError):
        return default


def assert_path_fits(case, what, tmpdir_bytes, harness, deepest, ceiling):
    """The directory arm: `deepest` is a Dir measured below the process root; PC_PATH_MAX counts the terminating NUL, so
    the usable length is one less. Returns (total, slack)."""
    total = tmpdir_bytes + harness.bytes + deepest.bytes
    slack = ceiling - 1 - total
    case.assertGreaterEqual(
        slack, 0,
        "%s: the longest mkdtemp/TemporaryDirectory path the harness can produce UNDER XDIST NESTING (a worker's root beside the controller's, "
        "measured on roots minted that way; an alone run verifies nothing about this figure) is %d bytes = %d (TMPDIR) + %d "
        "(%d romp-tests-* root level(s), measured on roots the harness minted) + %d (%s, %s:%d, the nesting through dir= "
        "followed); held against PC_PATH_MAX = %d (the NUL included, so %d usable), slack %d."
        % (what, total, tmpdir_bytes, harness.bytes, harness.levels, deepest.bytes, deepest.chain, deepest.file, deepest.line,
           ceiling, ceiling - 1, slack))
    return total, slack


def assert_name_fits(case, what, name, source, ceiling):
    """The component arm: one path component against PC_NAME_MAX (no NUL in the count). Returns (bytes, slack)."""
    n = len(os.fsencode(name))
    slack = ceiling - n
    case.assertGreaterEqual(
        slack, 0,
        "%s: the longest single component of any mkdtemp/TemporaryDirectory path the harness can produce UNDER XDIST NESTING, or of its own "
        "names (a root, the state dir, the children file, the marker, the kernel's socket names), is %d bytes (%r, from %s; "
        "a name is the same length alone and nested, but the figure is the tree's, not one run's); held against "
        "PC_NAME_MAX = %d, slack %d." % (what, n, name, source, ceiling, slack))
    return n, slack


class HarnessSocketBudget(unittest.TestCase):
    """Beside, not inside, proven by execution; and the longest hosts-on socket path the harness can produce,
    derived and held against the kernel's budget. Not under_conftest: the placement is the package's.

    ARM 1 HAS ZERO SLACK BY DESIGN. The sweep arm holds the deepest hosts-on lab at the box rule's 17-byte TMPDIR
    to a margin of at least one root level (20 bytes), and today's figure is 17 + 20 + 30 + 20 = 87 against 107:
    the margin IS one level, exactly. So the deepest hosts-on lab (tests/test_session_host_restart.py's
    `host-served-XXXXXXXX/xdg/romp`, 30 bytes below the root) cannot grow by a byte, and a new hosts-on lab may be
    at most as deep. A maintainer who hits this arm has three honest moves: shorten the lab (its prefix or its
    state suffix), shrink the box rule's TMPDIR template (SWEEP_TMPDIR_TEMPLATE, and the rule it states), or relax
    the margin requirement (min_margin=level). Never widen the budget, which is the kernel's sun_path. Relaxing the
    margin does NOT let a re-nested worker root through: the unconditional catch for that is the arm's
    `assertEqual(harness.levels, 1)`, which runs before assert_socket_fits and reds on its own; the margin is a
    second, independent guard (with two levels the margin computes to 0 against the 20 required), verified by
    execution in review (2026-09-21: the re-nesting mutant reds at the levels line first).

    THE LEDGER (2026-09-21): every occurrence of the session-hosts name in a module is accounted for — a classified
    write (on, off, opaque; a removal, a touch or a truncating open reads as on), a read, a comparison, a message, a
    docstring, a bound name or handle whose every use is one of those, a child Python's source read the same way — or
    named in `unaccounted` (NON_WRITE_SHAPES lists each shape with its reason), so a write in a shape the reader does not
    know is red by name, never dropped.

    THE SCAN'S POPULATION. The directory and component arms read every tempfile.mkdtemp and TemporaryDirectory call in
    tests/*.py (the nesting through dir= followed; a dir= the reader cannot follow is refused unless it is one of the
    ABOVE_ROOT_DIR_SHAPES) and the hosts-on labs' state suffixes; a directory a test makes with os.mkdir or os.makedirs
    under one of those, and romp's own mints under a state root, are outside the scan."""

    def _child(self, env_overrides, hold_dir):
        """A Python process that imports the tests package under the environment given and reports its root, its
        parent link and the record; held on stdin (release() lets it exit and remove its root)."""
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("PYTEST_", "ROMP_TESTS_")) and k not in (MARKER_ENV, "ROMP_HYGIENE_READY")}
        env.update(PYTHONDONTWRITEBYTECODE="1", **env_overrides)
        proc = subprocess.Popen([sys.executable, "-c", _MINTING_CHILD], cwd=hold_dir, env=env, text=True,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def _reap():
            if proc.poll() is None:
                proc.kill()
            proc.communicate()
        self.addCleanup(_reap)
        line = proc.stdout.readline()
        if not line:
            self.fail("the child minted no root: " + proc.communicate()[1])
        return proc, json.loads(line)

    @staticmethod
    def _release(proc):
        proc.stdin.write("\n")
        proc.stdin.flush()
        proc.wait(timeout=60)

    def _mint_pair(self, synthetic):
        """A controller-shaped process handed `synthetic` as its TMPDIR (the record cleared, as a run's first
        process has it), then a worker-shaped one handed the controller's root as its TMPDIR with the controller's
        record and xdist's worker variables, exactly the environment xdist spawns a worker with. Returns
        (controller proc, controller record, worker proc, worker record)."""
        ctl, c = self._child({"TMPDIR": synthetic}, synthetic)
        self.assertEqual(os.path.realpath(c["system"]), os.path.realpath(synthetic), "the first process records what it was handed")
        self.assertIsNone(c["parent"])
        wrk, w = self._child({"TMPDIR": c["root"], "ROMP_TESTS_SYSTEM_TMPDIR": c["system"], "PYTEST_XDIST_WORKER": "gw0",
                              "PYTEST_XDIST_WORKER_COUNT": "1", "PYTEST_XDIST_TESTRUNUID": uuid.uuid4().hex}, synthetic)
        return ctl, c, wrk, w

    def test_a_worker_shaped_root_is_minted_beside_the_controllers_not_inside_it(self):
        """Red at the nesting head: the worker's root was `<controller root>/romp-tests-*`."""
        synthetic = tempfile.mkdtemp(prefix="harness-")
        ctl, c, wrk, w = self._mint_pair(synthetic)
        for rec in (c, w):
            self.assertTrue(os.path.basename(rec["root"]).startswith("romp-tests-"), rec)
            self.assertTrue(os.path.isdir(rec["root"]), rec)
        self.assertEqual(os.path.dirname(w["root"]), synthetic, "the worker minted directly in the recorded system dir")
        self.assertNotEqual(os.path.commonpath([c["root"], w["root"]]), c["root"], "beside, not inside: %r" % (w["root"],))
        self.assertEqual(w["parent"], c["root"], "the worker knows whose root it was handed")
        self.assertEqual(w["system"], c["system"], "and keeps the controller's record")
        self.assertEqual(len(os.path.basename(w["root"])), len(os.path.basename(c["root"])), "the same 19-byte name: the gain is the level")
        with open(os.path.join(c["root"], "romp-tests-children"), encoding="utf-8") as fh:
            self.assertEqual([json.loads(l) for l in fh.read().splitlines()], [{"pid": w["pid"], "root": w["root"]}],
                             "the worker listed itself in the controller's root")
        self.assertEqual(sorted(os.listdir(synthetic)), sorted(os.path.basename(r["root"]) for r in (c, w)))
        self._release(wrk)
        self.assertEqual(os.listdir(synthetic), [os.path.basename(c["root"])], "the worker removed its own root at exit")
        self._release(ctl)
        self.assertEqual(os.listdir(synthetic), [], "the controller removed its own; nothing of either is left")

    def test_only_a_root_directly_under_the_recorded_system_dir_is_a_parent(self):
        """The placement rule on the parent, not the name (the review of 2026-09-21): a `romp-tests-*` dir that is NOT
        directly under the recorded system dir — the package's own `romp-tests-state-*` inside a root, conftest's
        `romp-tests-claude-*`, a root under some other dir — handed as a process's TMPDIR is no parent, and that process
        mints INSIDE it, as a first process does. Pure on tests.parent_root and tests.mint_root, then by execution: a
        child handed a state-shaped dir inside the controller's root, with the controller's record."""
        pkg = sys.modules["tests"]
        system = tempfile.mkdtemp(prefix="placement-")
        root = tempfile.mkdtemp(prefix="romp-tests-", dir=system)
        state = tempfile.mkdtemp(prefix="romp-tests-state-", dir=root)               # the package's state dir, inside a root
        claude = tempfile.mkdtemp(prefix="romp-tests-claude-", dir=root)             # conftest's, inside a root
        elsewhere = tempfile.mkdtemp(prefix="romp-tests-", dir=tempfile.mkdtemp(prefix="other-", dir=system))
        self.assertEqual(pkg.parent_root(root, system), root, "a root directly under the recorded dir is the parent")
        for handed, why in ((state, "the package's state dir, inside a root"), (claude, "conftest's claude dir, inside a root"),
                            (elsewhere, "a root under some other dir"), (system, "the recorded dir itself")):
            self.assertIsNone(pkg.parent_root(handed, system), why)
        self.assertIsNone(pkg.parent_root(root, os.path.join(system, "gone")), "a recorded dir that is gone: no parent")
        minted, parent = pkg.mint_root(state, system)
        self.assertIsNone(parent)
        self.assertEqual(os.path.dirname(minted), state, "handed the state dir, a process mints inside it: %r" % minted)
        shutil.rmtree(minted)
        # By execution: a child handed a state-shaped dir inside the controller's root, with the controller's record.
        synthetic = tempfile.mkdtemp(prefix="harness-")
        ctl, c = self._child({"TMPDIR": synthetic}, synthetic)
        planted = os.path.join(c["root"], "romp-tests-state-planted")
        os.mkdir(planted)
        wrk, w = self._child({"TMPDIR": planted, "ROMP_TESTS_SYSTEM_TMPDIR": c["system"]}, synthetic)
        self.assertIsNone(w["parent"], "a state-shaped dir is no parent root: %r" % (w,))
        self.assertEqual(os.path.dirname(w["root"]), planted, "the child minted inside what it was handed: %r" % (w["root"],))
        self.assertEqual(os.listdir(synthetic), [os.path.basename(c["root"])], "nothing new beside the controller's root")
        self._release(wrk)
        self.assertEqual(os.listdir(planted), [], "the child removed its own root at exit")
        self._release(ctl)
        self.assertEqual(os.listdir(synthetic), [])

    def test_a_worker_killed_without_its_hooks_is_removed_by_the_controller_at_exit(self):
        """The parent-side sweep at the package level (RunLeavesNothing has it under pytest): the worker SIGKILLed,
        its root stands with a dead owner; the controller's exit takes it, then its own."""
        synthetic = tempfile.mkdtemp(prefix="harness-")
        ctl, c, wrk, w = self._mint_pair(synthetic)
        os.kill(wrk.pid, signal.SIGKILL)
        wrk.wait(timeout=60)
        self.assertTrue(os.path.isdir(w["root"]), "a killed worker leaves its root standing")
        self._release(ctl)
        self.assertEqual(os.listdir(synthetic), [], "the controller removed the dead worker's root along with its own")

    @unittest.skipUnless(os.path.isdir("/proc"), "procfs: the zombie state is read from /proc/<pid>/stat")
    def test_a_zombie_child_is_dead_and_its_listed_root_is_removed(self):
        """A child that exited but was never reaped (state Z) owns nothing: the package's _pid_alive says dead where
        signal 0 still says alive, and remove_dead_children takes the root it listed (2026-09-21; until then a zombie
        worker's root survived the parent's exit)."""
        pkg = sys.modules["tests"]
        system = tempfile.mkdtemp(prefix="zombie-")
        parent = tempfile.mkdtemp(prefix="romp-tests-", dir=system)
        child_root = tempfile.mkdtemp(prefix="romp-tests-", dir=system)
        proc = subprocess.Popen([sys.executable, "-c", "pass"])
        self.addCleanup(proc.wait)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:                                     # loop-ok: bounded wait for the exit itself
            with open("/proc/%d/stat" % proc.pid, "rb") as fh:
                stat = fh.read()
            if stat[stat.rindex(b")") + 1:].split()[0] == b"Z":
                break
            time.sleep(0.01)
        else:
            self.fail("the child never reached the zombie state")
        os.kill(proc.pid, 0)                                                   # signal 0 still finds it: the rule this replaces
        self.assertFalse(pkg._pid_alive(proc.pid), "a zombie is dead")
        self.assertTrue(pkg._pid_alive(os.getpid()), "this process is alive")
        with open(os.path.join(parent, pkg.TEST_ROOT_CHILDREN), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"pid": proc.pid, "root": child_root}) + "\n")
        self.assertEqual(pkg.remove_dead_children(parent, system), [])
        self.assertFalse(os.path.isdir(child_root), "the zombie's root is removed")
        proc.wait()
        self.assertFalse(pkg._pid_alive(proc.pid), "and reaped, it stays dead")

    def test_a_live_child_keeps_its_root_when_the_parent_exits(self):
        """The other direction: a child still alive at the parent's exit owns its root; the parent leaves it, and the
        child removes it itself. (A nested pytest that outlives its test is such a child.)"""
        synthetic = tempfile.mkdtemp(prefix="harness-")
        ctl, c, wrk, w = self._mint_pair(synthetic)
        self._release(ctl)
        self.assertEqual(os.listdir(synthetic), [os.path.basename(w["root"])], "the live worker's root stands after the controller's exit")
        self._release(wrk)
        self.assertEqual(os.listdir(synthetic), [])

    def _kernel(self):
        # Loaded here, not at import: this module loads no romp code before a test asks (a private name shared with
        # BareRunLeavesNothing's load, so the backend is read once per process).
        from romp_load import load_source
        sb = load_source("romp_sdk_backend_hygiene", os.path.join(ROOT, "bin", "romp_sdk_backend.py"))
        ht = sb._ht()
        return ht, ht.sh

    def _socket_tail(self, ht, sh):
        """`/hosts/<sid8>.sock` from the kernel's two builders, for a uuid sid: host_sock builds the path the kernel
        connects to, sock_names the name the host publishes, and they must agree."""
        sid = str(uuid.uuid4())
        published = sh.sock_names(sid)[0]
        tail = "/" + os.path.relpath(str(ht.host_sock("", sid)), "")
        self.assertEqual(os.path.basename(tail), published, "host_sock and sock_names name the same socket")
        self.assertEqual(os.path.dirname(tail), "/hosts")
        return len(os.fsencode(tail))

    def test_the_deepest_hosts_on_socket_path_the_harness_can_produce_fits_sun_path_with_the_margin_stated(self):
        ht, sh = self._kernel()
        budget = sh.SOCK_PATH_MAX
        tail = _tmp_name_tail_bytes()
        sock = self._socket_tail(ht, sh)
        # The harness's share, measured on roots it minted: a worker-shaped process against a controller-shaped one.
        synthetic = tempfile.mkdtemp(prefix="harness-")
        ctl, c, wrk, w = self._mint_pair(synthetic)
        harness = Harness(*harness_bytes(w["root"], synthetic), c["root"], w["root"], synthetic)
        self._release(wrk)
        self._release(ctl)
        self.assertEqual(harness.levels, 1, "one romp-tests-* level for a worker: %r" % (harness,))
        level = harness.bytes // harness.levels
        # ...and on THIS process's root, whatever shape the run has (serial, a worker, a nested child).
        own = Harness(*harness_bytes(tempfile.gettempdir(), os.environ["ROMP_TESTS_SYSTEM_TMPDIR"]), None, tempfile.gettempdir(),
                      os.environ["ROMP_TESTS_SYSTEM_TMPDIR"])
        self.assertEqual(own.levels, 1, "one romp-tests-* level for this process: %r" % (own,))
        self.assertEqual(own.bytes, harness.bytes)
        # The labs' share, read from the tests' text: every state root a test turns hosts on in, and the deepest wins.
        sources = tree_sources()
        self.assertEqual(ht.SESSION_HOSTS_SETTING, "session-hosts", "the reader's literal is the kernel's setting name (kernel/host_transport.py)")
        labs, unresolved, opaque, unaccounted = hosts_on_labs(sources, tail)
        self.assertEqual(unaccounted, [], "an occurrence of the toggle's name that no classified write and none of the non-write "
                         "shapes reached: a write in a shape the reader does not know is a hole in the bound. At each site, teach "
                         "the reader the shape (_session_hosts_writes for a write, _Ledger._account for a non-write) or move the "
                         "write to a recognised idiom: <path>.write_text(v), open(<path>, \"w\").write(v), `with open(<path>, "
                         "\"w\") as fh: fh.write(v)`, with <path> as Path(<root>, \"session-hosts\") or os.path.join(<root>, "
                         "\"session-hosts\"). The non-write shapes and their reasons:\n"
                         + "\n".join("  %s: %s" % kv for kv in sorted(NON_WRITE_SHAPES.items())))
        self.assertEqual(opaque, [], "a session-hosts write whose VALUE the reader cannot read is counted as hosts-on but is "
                         "a hole in the reader: at each site write the literal (\"on\" or \"off\"), or bind the name to "
                         "literals it can follow (an assignment, a loop over a literal tuple, a call site passing a "
                         "literal, a default), or extend _written_word")
        self.assertEqual(unresolved, [], "a hosts-on state root the reader cannot follow to its mkdtemp is a hole in the "
                         "bound: mint it with a literal prefix (or none) and a literal suffix, or extend _lab_shapes")
        self.assertTrue(labs, "no test turns hosts on? the reader found no session-hosts write other than the literal off")
        lab = max(labs, key=lambda l: l.bytes)
        print("\nHarnessSocketBudget: %d hosts-on labs in %d modules (unresolved, opaque and unaccounted all empty); the deepest "
              "%s:%d (%r + %r, %d bytes below the root); harness %d bytes x %d level; socket tail %d; SOCK_PATH_MAX %d"
              % (len(labs), len({l.file for l in labs}), lab.file, lab.line, lab.prefix, "/".join(lab.comps), lab.bytes,
                 harness.bytes, harness.levels, sock, budget), file=sys.stderr)
        canonical = len(os.fsencode(SWEEP_TMPDIR_TEMPLATE))
        with self.subTest(arm="the sweep convention: TMPDIR = mktemp -d %s (%d bytes), margin of at least one root level"
                          % (SWEEP_TMPDIR_TEMPLATE, canonical)):
            # A margin under one level means a re-nesting (the shape before 2026-09-21) would break the bind: red there.
            assert_socket_fits(self, "under the box rule's %d-byte TMPDIR" % canonical, canonical, harness, lab, sock, budget,
                               min_margin=level)
        with self.subTest(arm="this run's TMPDIR"):
            # abspath, not realpath: tempfile takes the handed TMPDIR through os.path.abspath, the roots are minted under
            # that string and the host binds the path built from it, so the length the bind sees is the abspath's (a
            # TMPDIR through a symlink — macOS's /tmp, a /var/folders link — resolves to a different length).
            system = os.path.abspath(os.environ["ROMP_TESTS_SYSTEM_TMPDIR"])
            if sys.platform == "darwin" and deepest_socket_path(len(os.fsencode(system)), own, lab, sock) > budget:
                # The Darwin per-user TMPDIR (/var/folders/.../T, about 49 bytes) is over the bound for the deepest lab,
                # which needs romp's SDK venv and skips on a checkout without it, so a Mac run without the venv is not
                # invalid for anything it runs; a Mac run with the venv sees that lab's own failure.
                self.skipTest("the Darwin per-user TMPDIR %s is over the bound for %s; run under a shorter TMPDIR" % (system, lab.file))
            # A run under a TMPDIR too long for the deepest lab is INVALID for the session-host tests, not red: this
            # names the cause and the remedy where a sweep log would otherwise show only the host failing to bind.
            assert_socket_fits(self, "under this run's TMPDIR %s (%d bytes)" % (system, len(os.fsencode(system))),
                               len(os.fsencode(system)), harness, lab, sock, budget)
        with self.subTest(arm="the longest prefix any test module names, as if its lab turned hosts on"):
            # Conservative: a lab that never binds a socket, but any lab may turn hosts on tomorrow and a prefix is
            # arbitrary; the deepest hosts-on suffix in the tree stands in for its state root's.
            n, prefix, label, line = longest_prefix(sources)
            widest = Lab(1 + n + tail + sum(1 + len(os.fsencode(c)) for c in lab.comps), label, line, prefix, lab.comps, None)
            assert_socket_fits(self, "under the box rule's %d-byte TMPDIR with the tree's longest mkdtemp prefix" % canonical,
                               canonical, harness, widest, sock, budget)

    def test_the_longest_directory_path_and_component_the_harness_can_produce_fit_the_filesystems_limits(self):
        """The widening (romp-manager, 2026-09-21 19:15Z): the socket is one shape with one ceiling, and every shape the
        harness mints under a test root has its own. From the same AST scan — every tempfile.mkdtemp and
        TemporaryDirectory in tests/*.py with the nesting through `dir=` followed, and the hosts-on labs' state suffixes —
        and the same root level measured on minted roots: the longest DIRECTORY path under xdist nesting at the box rule's
        TMPDIR (and at this run's), held against PC_PATH_MAX; and the longest single COMPONENT — the tree's longest
        prefix + tail, the harness's own names (a root, the state dir, the children file, the marker) and the kernel's two
        socket names — held against PC_NAME_MAX. Figures and slack printed. Both ceilings sit far above today's tree;
        the arm exists so that a shape that reaches one is red by name, not a mystery in a sweep log."""
        ht, sh = self._kernel()
        tail = _tmp_name_tail_bytes()
        synthetic = tempfile.mkdtemp(prefix="harness-")
        ctl, c, wrk, w = self._mint_pair(synthetic)
        harness = Harness(*harness_bytes(w["root"], synthetic), c["root"], w["root"], synthetic)
        root_name = os.path.basename(w["root"])
        self._release(wrk)
        self._release(ctl)
        self.assertEqual(harness.levels, 1, "one romp-tests-* level for a worker under xdist nesting: %r" % (harness,))
        sources = tree_sources()
        dirs, unreadable, unfollowed = harness_dirs(sources, tail)
        self.assertEqual(unreadable, [], "a mkdtemp whose prefix or suffix the reader cannot read is a hole in the directory "
                         "and component bounds: name it with a literal (a unique marker comes from the minted basename, not "
                         "into the prefix), or extend _literal_str")
        self.assertEqual(unfollowed, [], "a mkdtemp/TemporaryDirectory whose dir= the reader can neither follow to a mkdtemp nor "
                         "match to an ABOVE_ROOT_DIR_SHAPES entry was, until 2026-09-21, scored as sitting directly under the root "
                         "in silence: bind the dir to a mkdtemp the reader can see, spell an above-root dir in one of those shapes, "
                         "or extend _dir_bytes / ABOVE_ROOT_DIR_SHAPES with the shape and its reason:\n"
                         + "\n".join("  %s: %s" % kv for kv in sorted(ABOVE_ROOT_DIR_SHAPES.items())))
        self.assertTrue(dirs, "no mkdtemp in the tree? the reader found no directory")
        labs = hosts_on_labs(sources, tail)[0]
        state_roots = [Dir(lab.bytes, lab.file, lab.line, "/" + lab.prefix + "X" * tail + "".join("/" + comp for comp in lab.comps))
                       for lab in labs]
        deepest = max(dirs + state_roots, key=lambda d: d.bytes)
        canonical = len(os.fsencode(SWEEP_TMPDIR_TEMPLATE))
        system = os.path.abspath(os.environ["ROMP_TESTS_SYSTEM_TMPDIR"])
        path_max, name_max = _pathconf("/", "PC_PATH_MAX", 4096), _pathconf(system, "PC_NAME_MAX", 255)
        pkg = sys.modules["tests"]
        published, temp = sh.sock_names(str(uuid.uuid4()))
        names = {root_name: "a romp-tests-* root, measured on a minted one", os.path.basename(pkg.STATE_DIR): "the package's state dir",
                 pkg.TEST_ROOT_CHILDREN: "the children file", pkg.TEST_ROOT_OWNER_MARKER: "the owner marker",
                 published: "the published socket name (sock_names)", temp: "the socket's temp name (sock_names)"}
        for d in dirs + state_roots:
            for comp in d.chain.split("/"):
                if comp:
                    names.setdefault(comp, "%s:%d" % (d.file, d.line))
        longest_name = max(names, key=lambda n: len(os.fsencode(n)))
        total = canonical + harness.bytes + deepest.bytes
        print("\nHarnessSocketBudget (directory and component): %d mkdtemp/TemporaryDirectory shapes in %d modules; the deepest "
              "mkdtemp/TemporaryDirectory path below a root %d bytes (%s, %s:%d); under xdist nesting at the %d-byte TMPDIR %d = %d + %d + %d, PC_PATH_MAX %d (%d "
              "usable), slack %d; longest component %d bytes (%r, %s), PC_NAME_MAX %d, slack %d"
              % (len(dirs), len({d.file for d in dirs}), deepest.bytes, deepest.chain, deepest.file, deepest.line, canonical, total,
                 canonical, harness.bytes, deepest.bytes, path_max, path_max - 1, path_max - 1 - total, len(os.fsencode(longest_name)),
                 longest_name, names[longest_name], name_max, name_max - len(os.fsencode(longest_name))), file=sys.stderr)
        with self.subTest(arm="the longest directory path under the box rule's %d-byte TMPDIR, against PC_PATH_MAX" % canonical):
            assert_path_fits(self, "under the box rule's %d-byte TMPDIR" % canonical, canonical, harness, deepest, path_max)
        with self.subTest(arm="the longest directory path under this run's TMPDIR, against PC_PATH_MAX"):
            assert_path_fits(self, "under this run's TMPDIR %s (%d bytes)" % (system, len(os.fsencode(system))),
                             len(os.fsencode(system)), harness, deepest, path_max)
        with self.subTest(arm="the longest single component, against PC_NAME_MAX"):
            assert_name_fits(self, "in the tree and the harness's own names", longest_name, names[longest_name], name_max)

    def test_the_directory_and_component_arms_red_on_planted_overruns(self):
        """The two new arms against planted inputs: the reader follows nesting through dir=, a suffix, a parameter's call
        sites and a `/` join, sums the chain, lists a prefix it cannot read, and the assertions fail past their ceilings
        with the chain, the figures and the ceiling in the message."""
        tail = _tmp_name_tail_bytes()
        system = tempfile.mkdtemp(prefix="planted-")
        root = tempfile.mkdtemp(prefix="romp-tests-", dir=system)
        flat = Harness(*harness_bytes(root, system), root, root, system)
        planted = textwrap.dedent('''\
            import os, tempfile
            from pathlib import Path
            def helper(prefix):
                return tempfile.mkdtemp(prefix=prefix)
            class T:
                def setUp(self):
                    self.a = tempfile.mkdtemp(prefix="aa-", suffix="-s")
                    self.b = tempfile.mkdtemp(prefix="bb-", dir=self.a)
                    self.c = tempfile.mkdtemp(prefix="cc-", dir=os.path.join(self.b, "x", "yy"))
                    self.d = tempfile.TemporaryDirectory(prefix="dd-", dir=Path(self.c) / "z")
                    helper("long-one-")
                    helper("s-")
                    tempfile.mkdtemp(prefix=make_prefix())
                    tempfile.mkdtemp(prefix="ee-", dir=make_dir())
                    tempfile.mkdtemp(prefix="ff-", dir=system_tmp())
                    tempfile.mkdtemp(prefix="gg-", dir=os.environ.get("ROMP_TESTS_SYSTEM_TMPDIR") or None)
                    tempfile.mkdtemp(prefix="hh-", dir=(os.environ.get("ROMP_TESTS_SYSTEM_TMPDIR") or tempfile.gettempdir()) if short else None)
                    tempfile.mkdtemp(prefix="ii-", dir=os.path.join(make_dir(), "x"))
                    tempfile.mkdtemp(prefix="jj-", dir=os.environ.get("ROMP_TESTS_SYSTEM_TMPDIR") or make_dir())
                    home = Path(os.path.expanduser("~"))
                    tempfile.mkdtemp(prefix="kk-", dir=str(home))
        ''')
        dirs, unreadable, unfollowed = harness_dirs([("t.py", planted)], tail)
        self.assertEqual(unreadable, ["t.py:13: tempfile.mkdtemp(prefix=make_prefix())"])
        self.assertEqual(unfollowed, ["t.py:14: /ee-%s dir=make_dir()" % ("X" * tail),
                                      "t.py:18: /ii-%s dir=os.path.join(make_dir(), 'x')" % ("X" * tail),
                                      "t.py:19: /jj-%s dir=os.environ.get('ROMP_TESTS_SYSTEM_TMPDIR') or make_dir()" % ("X" * tail)],
                         "a dir= the reader can neither follow nor match whole to an above-root shape is listed, not scored under the root")
        by_line = {d.line: d for d in dirs}
        for n, p in ((15, "ff-"), (16, "gg-"), (17, "hh-"), (21, "kk-")):
            self.assertEqual((by_line[n].bytes, by_line[n].chain), (1 + 3 + tail, "/" + p + "X" * tail),
                             "an above-root shape (ABOVE_ROOT_DIR_SHAPES): scored as directly under the root")
        self.assertEqual(by_line[7].bytes, 1 + 3 + tail + 2)
        self.assertEqual(by_line[8].bytes, by_line[7].bytes + 1 + 3 + tail)
        self.assertEqual(by_line[9].bytes, by_line[8].bytes + 2 + 3 + 1 + 3 + tail, by_line[9])
        self.assertEqual(by_line[10].bytes, by_line[9].bytes + 2 + 1 + 3 + tail, by_line[10])
        self.assertEqual(by_line[10].chain, "/aa-%s-s/bb-%s/x/yy/cc-%s/z/dd-%s" % ((("X" * tail),) * 4))
        self.assertEqual(by_line[4].bytes, 1 + len("long-one-") + tail, "a parameter: the longest literal any call site passes")
        deepest = max(dirs, key=lambda d: d.bytes)
        total, slack = assert_path_fits(self, "planted control", 17, flat, deepest, 4096)
        self.assertEqual(total, 17 + flat.bytes + by_line[10].bytes)
        with self.assertRaises(AssertionError) as cm:
            assert_path_fits(self, "planted ceiling", 17, flat, deepest, total)        # one byte short of fitting (the NUL)
        self.assertIn(by_line[10].chain, str(cm.exception))
        self.assertIn("PC_PATH_MAX = %d" % total, str(cm.exception))
        self.assertIn("UNDER XDIST NESTING", str(cm.exception))
        assert_path_fits(self, "planted fit", 17, flat, deepest, total + 1)
        with self.assertRaises(AssertionError) as cm:
            assert_name_fits(self, "planted name", "n" * 256, "t.py:1", 255)
        self.assertIn("256 bytes", str(cm.exception))
        self.assertIn("PC_NAME_MAX = 255", str(cm.exception))
        assert_name_fits(self, "planted name", "n" * 255, "t.py:1", 255)

    def test_the_derivation_reds_on_a_planted_extra_level_or_a_longer_prefix(self):
        """The pin against planted inputs, not the tree: a nested worker root (the shape before 2026-09-21) measured
        by the same function fails the sweep arm at margin 0, and a hosts-on lab with a longer prefix read by the
        same reader overruns the budget; the tree's own shapes pass both."""
        ht, sh = self._kernel()
        budget, tail, sock = sh.SOCK_PATH_MAX, _tmp_name_tail_bytes(), self._socket_tail(ht, sh)
        canonical = len(os.fsencode(SWEEP_TMPDIR_TEMPLATE))
        system = tempfile.mkdtemp(prefix="planted-")
        one = tempfile.mkdtemp(prefix="romp-tests-", dir=system)                    # a controller-shaped root
        nested = tempfile.mkdtemp(prefix="romp-tests-", dir=one)                    # a worker's, INSIDE it: the old shape
        beside = tempfile.mkdtemp(prefix="romp-tests-", dir=system)                 # a worker's beside: the shape now
        flat, deep = Harness(*harness_bytes(beside, system), one, beside, system), Harness(*harness_bytes(nested, system), one, nested, system)
        self.assertEqual((flat.levels, deep.levels), (1, 2))
        self.assertEqual(deep.bytes, 2 * flat.bytes)
        level = flat.bytes
        planted = textwrap.dedent('''\
            import os, tempfile
            from pathlib import Path
            class T:
                def setUp(self):
                    self.lab = tempfile.mkdtemp(prefix="host-served-")
                    self.state = os.path.join(self.lab, "xdg", "romp")
                def run(self):
                    Path(self.state, "session-hosts").write_text("on" if True else "off")
        ''')
        labs, unresolved, opaque, unaccounted = hosts_on_labs([("t.py", planted)], tail)
        self.assertEqual((unresolved, opaque, unaccounted), ([], [], []))
        lab = max(labs, key=lambda l: l.bytes)
        self.assertEqual((lab.prefix, lab.comps, lab.bytes), ("host-served-", ("xdg", "romp"), 1 + 12 + tail + 9))
        total, margin = assert_socket_fits(self, "planted control", canonical, flat, lab, sock, budget, min_margin=level)
        self.assertGreaterEqual(margin, level)
        # An extra level: the sweep arm fails, and its message carries the shape and the margin.
        with self.assertRaises(AssertionError) as cm:
            assert_socket_fits(self, "planted nesting", canonical, deep, lab, sock, budget, min_margin=level)
        self.assertIn("2 romp-tests-* root level(s)", str(cm.exception))
        self.assertIn("the margin is %d" % (budget - (total + level)), str(cm.exception))
        # A longer prefix, read by the same reader: over the budget outright.
        longer = planted.replace('prefix="host-served-"', 'prefix="host-served-%s-"' % ("x" * (margin + 1 - level)))
        labs2 = hosts_on_labs([("t.py", longer)], tail)[0]
        lab2 = max(labs2, key=lambda l: l.bytes)
        self.assertEqual(lab2.bytes, lab.bytes + margin + 1 - level + 1)
        with self.assertRaises(AssertionError) as cm:
            assert_socket_fits(self, "planted prefix", canonical, flat, lab2, sock, budget, min_margin=level)
        self.assertIn("host-served-x", str(cm.exception))
        with self.assertRaises(AssertionError):
            assert_socket_fits(self, "planted prefix, no margin asked", canonical + level, flat, lab2, sock, budget)
        # The reader itself: a hosts-on site whose root it cannot follow is reported, not dropped.
        unfollowable = planted.replace('self.lab = tempfile.mkdtemp(prefix="host-served-")', "self.lab = make_lab()")
        labs3, unresolved3, opaque3, unaccounted3 = hosts_on_labs([("t.py", unfollowable)], tail)
        self.assertEqual((labs3, opaque3, unaccounted3), ([], [], []))
        self.assertEqual(unresolved3, ["t.py:8: self.state"])

    def test_the_reader_counts_every_write_that_is_not_the_literal_off_and_names_a_value_it_cannot_read(self):
        """The reader's classification on planted sources (2026-09-21; until then only a literal "on" counted, and a value
        it could not see dropped its lab from the bound in silence). Counted as hosts-on: a literal that is not off (an
        on word, a stray word, a blank), a conditional with an on arm, a loop variable over literals with an on word, a
        helper's parameter that some call site passes an on word, write_bytes, a with-open handle, a receiver bound to a
        name, an unreadable value (listed in `opaque` too, by site). Not counted: the literal off in any case or padding,
        str or bytes, through every one of those roads. The enclosing function's binding of a root wins over the module's
        other bindings of the same name, and a root a caller hands in is followed through the module's."""
        tail = _tmp_name_tail_bytes()
        src = textwrap.dedent('''\
            import os, tempfile
            from pathlib import Path
            OFF = "off"
            def helper(state, word):
                Path(state, "session-hosts").write_text(word)                       # a parameter, from the call sites
            class T:
                def setUp(self):
                    self.lab = tempfile.mkdtemp(prefix="ab-")
                    self.state = os.path.join(self.lab, "xdg")
                def on_words(self):
                    d = tempfile.mkdtemp(prefix="loop-")
                    for word in ("on", "1", "true", "yes", "On\\n"):
                        Path(d, "session-hosts").write_text(word)                   # a loop over on words
                    for blank in ("", "  \\n\\t"):
                        Path(d, "session-hosts").write_text(blank)                  # blank reads as on
                    Path(d, "session-hosts").write_text("maybe")                    # a stray word: not the literal off
                    Path(d, "session-hosts").write_bytes(b"ON")                     # bytes
                def off_words(self):
                    e = tempfile.mkdtemp(prefix="quiet-")
                    for word in ("off", "OFF", " Off\\n"):
                        Path(e, "session-hosts").write_text(word)                   # off in any case or padding
                    Path(e, "session-hosts").write_bytes(b"off\\n")                 # off bytes
                    Path(e, "session-hosts").write_text(OFF)                        # a name bound to off only
                    with open(os.path.join(e, "session-hosts"), "w") as fh:
                        fh.write("off\\n")                                          # a handle
                    toggle = os.path.join(e, "session-hosts")
                    with open(toggle, "w") as fh:
                        fh.write("off")                                             # a receiver bound to a name
                    with open(os.path.join(e, "notes"), "w") as fh:
                        fh.write(os.environ["NOT_A_TOGGLE"])                        # another file's handle: not a write here
                def handles(self):
                    f = tempfile.mkdtemp(prefix="handle-")
                    with open(os.path.join(f, "session-hosts"), "w") as fh:
                        fh.write("on")                                              # a handle writing on
                    toggle = os.path.join(f, "session-hosts")
                    open(toggle, "w").write("on" if self.x else "off")              # a receiver bound to a name, a conditional
                    helper(f, "on")
                    helper(f, "off")
                def unreadable(self):
                    g = tempfile.mkdtemp(prefix="unread-")
                    Path(g, "session-hosts").write_text(os.environ["WORD"])         # opaque, counted all the same
                def own_root(self):
                    lab = tempfile.mkdtemp(prefix="own-")                          # the enclosing function's `lab`, not setUp's
                    Path(lab, "session-hosts").write_text("on")                     # own_root_write
        ''')
        line = lambda marker: next(i for i, l in enumerate(src.splitlines(), 1) if marker in l)
        labs, unresolved, opaque, unaccounted = hosts_on_labs([("t.py", src)], tail)
        self.assertEqual((unresolved, unaccounted), ([], []), "every occurrence here is a write the reader classifies")
        self.assertEqual(opaque, ["t.py:%d: os.environ['WORD']" % line("opaque, counted")],
                         "the unreadable value is named by site, with its expression")
        by_line = collections.defaultdict(set)
        for lab in labs:
            by_line[lab.line].add((lab.prefix, lab.comps))
        counted = ["a parameter, from the call sites", "a loop over on words", "blank reads as on", "a stray word",
                   "bytes", "a handle writing on", "a conditional", "opaque, counted", "own_root_write"]
        self.assertEqual(sorted(by_line), sorted(line(m) for m in counted), "every non-off write and only those")
        self.assertEqual(by_line[line("a parameter, from the call sites")], {("handle-", ())},
                         "a parameter: the call sites' roots, one on word among them")
        self.assertEqual(by_line[line("a loop over on words")], {("loop-", ())})
        self.assertEqual(by_line[line("a handle writing on")], {("handle-", ())})
        self.assertEqual(by_line[line("a conditional")], {("handle-", ())})
        self.assertEqual(by_line[line("opaque, counted")], {("unread-", ())})
        self.assertEqual(by_line[line("own_root_write")], {("own-", ())}, "the enclosing function's binding, not setUp's `self.lab`")
        self.assertEqual({lab.bytes for lab in labs if lab.line == line("opaque, counted")}, {1 + len("unread-") + tail})
        # A parameter no call site passes an on word to reads as off, and a root handed in is followed to the caller's mint.
        quiet = src.replace('helper(f, "on")', 'helper(f, "off")')
        labs_q, unresolved_q, opaque_q, unaccounted_q = hosts_on_labs([("t.py", quiet)], tail)
        self.assertEqual((unresolved_q, opaque_q, unaccounted_q), ([], opaque, []), "the same opaque site; nothing else changed")
        self.assertNotIn(line("a parameter, from the call sites"), {lab.line for lab in labs_q})
        # A helper whose root comes from a caller's variable: the module's bindings of that name give the shape.
        handed = textwrap.dedent('''\
            import tempfile
            from pathlib import Path
            def turn_on(state):
                Path(state, "session-hosts").write_text("on")
            def caller():
                state = tempfile.mkdtemp(prefix="caller-")
                turn_on(state)
        ''')
        labs_h, unresolved_h, opaque_h, unaccounted_h = hosts_on_labs([("h.py", handed)], tail)
        self.assertEqual((unresolved_h, opaque_h, unaccounted_h), ([], [], []))
        self.assertEqual([(lab.prefix, lab.line) for lab in labs_h], [("caller-", 4)])

    def test_every_occurrence_of_the_session_hosts_name_is_accounted_for_or_named(self):
        """The ledger on planted sources (the refuter's finding, 2026-09-21: the round-2 reader was closed over its write
        idioms, and of nine planted write shapes it reported one, dropping eight in silence). Ten shapes: the idiom it knew;
        a handle bound in setUp and written in a test; os.write on a descriptor from os.open; a Path built through a helper;
        a shutil.copy onto the file; a json.dump into a with-open handle; a shell one-liner; open(...).write chained; a
        conditional receiver; a child Python's source. Six are classified as writes (their labs counted), the child source
        is read as a nested module (its lab counted under the site's label), and the copy, the dump and the shell line are
        listed in `unaccounted` with their source lines. Not one occurrence is without a ledger entry. Then the tree's own
        non-write shapes on a second source — a bound name made a dir, read, written off and compared; a docstring; an
        assertion's value and message; a parent dir; a print; a child Python writing off — each with their category and
        none a lab."""
        tail = _tmp_name_tail_bytes()
        src = textwrap.dedent('''\
            import json, os, shutil, subprocess, sys, tempfile
            from pathlib import Path
            def toggle(root):
                return Path(root, "session-hosts")
            class T:
                def setUp(self):
                    self.d = tempfile.mkdtemp(prefix="nine-")
                    self.fh = open(os.path.join(self.d, "session-hosts"), "w")
                def plain(self):
                    Path(self.d, "session-hosts").write_text("on")
                def handle_outside(self):
                    self.fh.write("on")
                def descriptor(self):
                    fd = os.open(os.path.join(self.d, "session-hosts"), os.O_WRONLY | os.O_CREAT)
                    os.write(fd, b"on")
                def helper_path(self):
                    toggle(self.d).write_text("on")
                def copied(self):
                    shutil.copy(self.src, os.path.join(self.d, "session-hosts"))
                def dumped(self):
                    with open(os.path.join(self.d, "session-hosts"), "w") as fh:
                        json.dump("on", fh)
                def shell(self):
                    subprocess.run(["sh", "-c", "echo on > %s/session-hosts" % self.d])
                def chained(self):
                    open(os.path.join(self.d, "session-hosts"), "w").write("on")
                def conditional(self):
                    (Path(self.d, "session-hosts") if self.x else Path(self.d, "notes")).write_text("on")
                def child(self):
                    subprocess.run([sys.executable, "-c", "\\n".join([
                        "import os, tempfile",
                        "root = tempfile.mkdtemp(prefix='child-')",
                        "open(os.path.join(root, 'session-hosts'), 'w').write('on')"])])
        ''')
        rows = src.splitlines()
        line = lambda marker: next(i for i, l in enumerate(rows, 1) if marker in l)
        labs, unresolved, opaque, unaccounted, entries = session_hosts_ledger("t.py", src, tail)
        self.assertEqual(sorted(e[0] for e in entries), sorted(i for i, l in enumerate(rows, 1) if "session-hosts" in l),
                         "one ledger entry per occurrence: nothing dropped")
        expected = {"return Path(root": "bound: write:on", "self.fh = open(": "handle: write:on",
                    'Path(self.d, "session-hosts").write_text': "write:on", "fd = os.open(": "handle: write:on", "shutil.copy(": None, 'with open(os.path.join(self.d, "session-hosts"), "w") as fh': None,
                    "echo on >": None, 'open(os.path.join(self.d, "session-hosts"), "w").write("on")': "write:on",
                    "if self.x else": "write:on", "'w').write('on')": "child source"}
        self.assertEqual({e[0]: e[1] for e in entries}, {line(m): c for m, c in expected.items()})
        writes = ['Path(self.d, "session-hosts").write_text', "self.fh.write(", "os.write(fd", "toggle(self.d).write_text",
                  'open(os.path.join(self.d, "session-hosts"), "w").write("on")', "if self.x else"]
        self.assertEqual(sorted((l.file, l.line, l.prefix) for l in labs),
                         sorted([("t.py", line(m), "nine-") for m in writes]
                                + [("t.py:%d (a child Python's source)" % line("'w').write('on')"), 3, "child-")]),
                         "six writes classified on, the child's counted under the site's label")
        self.assertEqual((unresolved, opaque), ([], []))
        dump = line('with open(os.path.join(self.d, "session-hosts"), "w") as fh')
        self.assertEqual(unaccounted, ["t.py:%d: %s" % (line("shutil.copy("), rows[line("shutil.copy(") - 1].strip()),
                                       "t.py:%d: %s (through t.py:%d: %s)" % (dump, rows[dump - 1].strip(), dump + 1, rows[dump].strip()),
                                       "t.py:%d: %s" % (line("echo on >"), rows[line("echo on >") - 1].strip())],
                         "the copy, the dump (through the handle's one use) and the shell line are named with their source lines")
        # The tree's non-write shapes, each with its category and none a lab.
        shapes = textwrap.dedent('''\
            """A module whose docstring speaks of the session-hosts file."""
            import os, subprocess, sys, tempfile
            from pathlib import Path
            ROOT = tempfile.mkdtemp(prefix="floor-")
            TOGGLE = os.path.join(ROOT, "romp", "session-hosts")
            def floor():
                os.makedirs(os.path.dirname(TOGGLE), exist_ok=True)
                if not os.path.exists(TOGGLE) or open(TOGGLE).read().strip() != "off":
                    with open(TOGGLE, "w") as f:
                        f.write("off\\n")
            def helper(state):
                (state / "session-hosts").parent.mkdir(parents=True, exist_ok=True)
                (state / "session-hosts").write_text("off\\n")
            class T:
                def test_it(self):
                    self.assertEqual(sorted(os.listdir(ROOT)), ["session-hosts"], "the session-hosts file is the only entry")
                    if os.path.basename(TOGGLE) == "session-hosts":
                        print("session-hosts: read back")
                    child = subprocess.run([sys.executable, "-c", "\\n".join(["import os, tempfile", "root = tempfile.mkdtemp()",
                        "open(os.path.join(root, 'romp', 'session-hosts'), 'w').write('off')"])])
        ''')
        labs, unresolved, opaque, unaccounted, entries = session_hosts_ledger("s.py", shapes, tail)
        self.assertEqual((labs, unresolved, opaque, unaccounted), ([], [], [], []), "every shape accounted, none a hosts-on lab")
        self.assertEqual(sorted((l, c) for l, c, _ in entries),
                         [(1, "docstring"), (5, "bound: comparison, parent-dir, read, write:off"), (12, "parent-dir"), (13, "write:off"),
                          (16, "assertion"), (16, "assertion"), (17, "comparison"), (18, "message"), (20, "child source")])
        # A bound name with one use the reader cannot account for names that use, and a shell line stays unaccounted whatever
        # wraps it.
        leaky = shapes.replace('print("session-hosts: read back")', "shutil.copy(TOGGLE, ROOT)")
        labs, unresolved, opaque, unaccounted, entries = session_hosts_ledger("s.py", leaky, tail)
        self.assertEqual(unaccounted, ["s.py:5: %s (through s.py:18: shutil.copy(TOGGLE, ROOT))" % leaky.splitlines()[4].strip()],
                         "the binding is unaccounted through its one unaccounted use, both named")
        self.assertEqual([c for l, c, _ in entries if l == 5], [None])
        # The shapes that leave the file empty or absent, which the kernel reads as on: each a lab, each noted.
        truncating = textwrap.dedent('''\
            import os, tempfile
            d = tempfile.mkdtemp(prefix="trunc-")
            with open(os.path.join(d, "session-hosts"), "w"):
                pass
            open(os.path.join(d, "session-hosts"), "w").close()
            os.remove(os.path.join(d, "session-hosts"))
            fh = open(os.path.join(d, "session-hosts"), "w")
            fh.close()
        ''')
        labs, unresolved, opaque, unaccounted, entries = session_hosts_ledger("u.py", truncating, tail)
        note = "no file, or an empty one, reads as on (a removal, a touch, a truncating open)"
        self.assertEqual(sorted((l.line, l.prefix, l.note) for l in labs), [(3, "trunc-", note), (5, "trunc-", note), (6, "trunc-", note)])
        self.assertEqual((unresolved, opaque), ([], []))
        self.assertEqual(unaccounted, ["u.py:7: %s (a handle opened for writing that nothing writes through or reads: u.py:8: "
                                       "fh.close(); the empty file reads as on)" % truncating.splitlines()[6].strip()],
                         "a handle opened for writing and only closed truncates the file to empty, which reads as on: no write "
                         "through it is classified, so the site is named with the handle's uses")


if __name__ == "__main__":
    unittest.main()      # the package import for a direct run is at the top of the module, with the reason
