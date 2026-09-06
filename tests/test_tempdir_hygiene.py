"""A pytest run leaves nothing in the system temp dir, and its git reads none of the developer's
configuration (2026-09-06).

Two mechanisms, one per half. tests/__init__.py wraps tempfile.mkdtemp so every directory the test
process mints is recorded and removed when the run ends (under pytest at session end, under
`python -m unittest` at exit): that is the in-process half, and it covers the 300-odd module
preambles and the per-test mkdtemp calls nobody cleans up. tests/conftest.py covers what the hook
cannot see — directories made by child processes (kernels, git, a shell's `mktemp -d`), mkstemp
files, os.mkdir paths — by pointing the process temp dir (tempfile.tempdir and TMPDIR, so children
inherit it) at one private `romp-tests-*` root and removing the root when the run ends; the
package's state dir, minted before the redirect, goes with it. Before both, a full run left ~5,600
entries in /tmp and over a million had piled up. The same conftest points git at no global or
system config (GIT_CONFIG_GLOBAL, GIT_CONFIG_NOSYSTEM) with a synthetic identity: the seed commits
had been running the developer's global pre-commit hook.

Pinned four ways. Hygiene (the hook): it is installed, and a child run of this module under pytest
and under unittest leaves neither the directory it made nor its state root (ROMP_HYGIENE_MARKER
names the file where the child writes both paths). From inside a run: the floors are in place and
children inherit them; no test pins a temp path to a literal directory; a root that survives
removal is named on stderr; a global and a system hooksPath cannot reach a fixture commit. End to
end: a nested pytest on a leaking module leaves the system temp dir it was given exactly as it
found it, serial and under xdist. The in-run and end-to-end classes skip under a bare unittest run,
where conftest never loaded and there is nothing to pin; the hook checks run either way. This
module loads no romp code, so it needs no state-root preamble.
"""
import ast
import contextlib
import glob
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
IDENT = "romp tests <tests@example.invalid>"

under_conftest = unittest.skipUnless("tests.conftest" in sys.modules,
                                     "the floors under test are tests/conftest.py's (pytest-only)")


def _run(cmd, **kw):
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
        self._run_child([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_tempdir_hygiene.py::Hygiene::test_mkdtemp_is_tracked_in_process"])

    @unittest.skipIf(os.environ.get(MARKER_ENV), "child mode")
    def test_unittest_child_run_removes_its_dirs_and_state_root(self):
        self._run_child([sys.executable, "-m", "unittest", "-q",
                         "tests.test_tempdir_hygiene.Hygiene.test_mkdtemp_is_tracked_in_process"])


@under_conftest
class PrivateTempRoot(unittest.TestCase):
    def test_the_process_temp_dir_is_the_private_root(self):
        root = tempfile.gettempdir()
        self.assertTrue(os.path.basename(root).startswith("romp-tests-"), root)
        self.assertTrue(os.path.isdir(root))
        self.assertEqual(os.environ.get("TMPDIR"), root, "children find the root through TMPDIR")

    def test_module_level_state_roots_land_inside_it(self):
        # Whichever module's preamble wrote XDG_STATE_HOME last at collection, it minted the dir
        # after conftest redirected the temp root, so it sits inside.
        root = tempfile.gettempdir()
        xdg = os.environ["XDG_STATE_HOME"]
        self.assertEqual(os.path.commonpath([root, xdg]), root, xdg)

    def test_children_inherit_the_root(self):
        root = tempfile.gettempdir()
        py = _run([sys.executable, "-c", "import tempfile, sys; sys.stdout.write(tempfile.gettempdir())"])
        self.assertEqual(py.stdout, root, "a Python child's tempfile answers with the root")
        sh = _run(["mktemp", "-d", "-u"])   # -u: name only, nothing created
        self.assertEqual(os.path.dirname(sh.stdout.strip()), root, "a shell's mktemp -d lands in it")

    def test_the_handed_temp_dir_is_recorded_once_and_the_roots_nest_under_it(self):
        # The one sanctioned way out of the root (tests/test_kernel_socket_deliver._socket_dir, for
        # a socket path that would not fit sun_path) goes to the dir the RUN was handed, never to a
        # literal system path. Recorded once: serially the root sits directly in it; in an xdist
        # worker the worker's root sits inside the controller's and the record is still the dir
        # above both — a worker that re-recorded its own gettempdir() would name the controller's
        # root, one level too deep for the socket under a long TMPDIR.
        handed = os.environ.get("ROMP_TESTS_SYSTEM_TMPDIR")
        self.assertTrue(handed, "conftest records the temp dir it replaced")
        handed, root = os.path.realpath(handed), os.path.realpath(tempfile.gettempdir())
        self.assertFalse(os.path.basename(handed).startswith("romp-tests-"), handed)
        self.assertEqual(os.path.commonpath([handed, root]), handed, root)
        between = os.path.relpath(root, handed).split(os.sep)
        self.assertTrue(all(p.startswith("romp-tests-") for p in between), between)
        self.assertEqual(len(between), 2 if os.environ.get("PYTEST_XDIST_WORKER") else 1, between)

    TEMPFILE_CALLS = ("mkdtemp", "mkstemp", "mktemp", "TemporaryDirectory", "NamedTemporaryFile",
                      "TemporaryFile", "SpooledTemporaryFile")

    def test_no_test_pins_a_temp_path_to_a_literal_directory(self):
        # A string literal as the `dir=` of a tempfile call bypasses the redirect: the socket tests
        # carried dir="/tmp" and left three rompsock* directories in the real /tmp per run, where the
        # nested-run check below could not see them. Static, so it covers every module whether or
        # not a run exercises it. Python files are read as syntax (a call's keyword, so
        # parse_session(dir="/TESTDIR") is not a hit and a call split over lines is), after a text
        # prefilter that keeps the parse to the files that could match; a bats `mktemp` naming /tmp
        # is the shell shape.
        bad = []
        might = re.compile(r"\bdir\s*=")
        for path in sorted(glob.glob(os.path.join(HERE, "*.py"))):
            src = open(path, encoding="utf-8").read()
            if not (might.search(src) and any(c in src for c in self.TEMPFILE_CALLS)):
                continue
            for node in ast.walk(ast.parse(src)):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
                if name in self.TEMPFILE_CALLS and any(
                        kw.arg == "dir" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str)
                        for kw in node.keywords):
                    bad.append("%s:%d: %s" % (os.path.relpath(path, ROOT), node.lineno,
                                              ast.get_source_segment(src, node).splitlines()[0]))
        sh_pin = re.compile(r"\bmktemp\b[^\n|;&#]*(?:\s-p\s*|\s)/(?:tmp|var/tmp|private/tmp)\b")
        for path in sorted(glob.glob(os.path.join(HERE, "*.bats")) + glob.glob(os.path.join(HERE, "*.bash"))):
            for n, line in enumerate(open(path, encoding="utf-8"), 1):
                if sh_pin.search(line) and not line.lstrip().startswith("#"):
                    bad.append("%s:%d: %s" % (os.path.relpath(path, ROOT), n, line.strip()))
        self.assertEqual(bad, [], "temp paths take the process temp dir (the private root); a test that "
                         "must leave it falls back to ROMP_TESTS_SYSTEM_TMPDIR — see _socket_dir")


@under_conftest
class RunEndNotice(unittest.TestCase):
    """A root that survives the run-end removal is named on stderr, once, rather than left standing
    with the run green. `shutil.rmtree(..., ignore_errors=True)` swallows a child still writing under
    the root and a 000-mode directory a test left behind (shutil's fd-based walk cannot open it, so
    the root's rmdir is never reached); the stand-in here is the latter."""

    def test_the_package_state_dir_is_removed_with_the_root(self):
        # tests/__init__.py minted it before conftest redirected the temp root, so it is the one
        # thing outside the root; conftest holds it for the run-end removal rather than leaving it
        # to __init__'s atexit alone.
        conftest = sys.modules["tests.conftest"]
        pkg_dir = conftest._PACKAGE_STATE_DIR
        self.assertEqual(pkg_dir, sys.modules["tests"].STATE_DIR)
        self.assertTrue(os.path.isdir(pkg_dir), pkg_dir)
        root = tempfile.gettempdir()
        # A sibling of the root, not a child: both were minted in the dir this process started with
        # (the system temp dir, or the controller's root in an xdist worker) before the redirect.
        self.assertEqual(os.path.realpath(os.path.dirname(pkg_dir)), os.path.realpath(os.path.dirname(root)))
        self.assertNotEqual(os.path.commonpath([root, pkg_dir]), root)

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

        # The real hook, on the stand-in only (the package state dir is live and not this test's).
        with patch.object(conftest, "_TMP_ROOT", root), patch.object(conftest, "_PACKAGE_STATE_DIR", None):
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
        _run(["git", "init", "-q"], cwd=repo, check=True)
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
    import os, subprocess, tempfile, unittest
    ROOT = os.environ["TMPDIR"]
    STATE = tempfile.mkdtemp()            # a module preamble's state root: never cleaned by the module

    class Leak(unittest.TestCase):
        def test_everything_lands_under_the_private_root(self):
            self.assertTrue(os.path.basename(ROOT).startswith("romp-tests-"), ROOT)
            d = tempfile.mkdtemp()            # a seed repo, the shape that leaked: never cleaned
            fd, f = tempfile.mkstemp()
            os.close(fd)
            subprocess.run(["git", "init", "-q", d], check=True)
            open(os.path.join(d, "a.txt"), "w").write("a\\n")
            subprocess.run(["git", "-C", d, "add", "a.txt"], check=True)
            subprocess.run(["git", "-C", d, "commit", "-q", "-m", "seed"], check=True)
            sh = subprocess.run(["mktemp", "-d"], capture_output=True, text=True, check=True).stdout.strip()
            for p in (STATE, d, f, sh):
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
            "ROMP_TESTS_SYSTEM_TMPDIR"):        # a fresh run records its own handed dir (conftest setdefaults it)
            env.pop(var, None)
        r = subprocess.run([sys.executable, "-m", "pytest", "-p", "tests.conftest", "-p", "no:cacheprovider",
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
        # Pins the outcome, not each process's hook: a worker's root sits inside the controller's
        # (it inherits that TMPDIR), so the controller's removal alone would satisfy this.
        self._nested("-n", "2")


if __name__ == "__main__":
    unittest.main()
