#!/usr/bin/env python3
"""A pytest run leaves nothing in the system temp dir, and its git reads none of the developer's
configuration (2026-09-06).

The suite mints thousands of temp directories per run — 500+ module preambles `mkdtemp()` a state
root that the kernel stamps with romp/repo-root, per-test mkdtemp/mkstemp calls rarely get a
tearDown, and a seed-repo fixture built its `repo` in a class-level mkdtemp with no tearDownClass —
and cleaned up almost none of them: ~5,600 entries per full run, at up to ten a second, until /tmp
held 1.8 million and `ls /tmp` took ten seconds. tests/conftest.py now redirects the process temp
dir (tempfile.tempdir and TMPDIR, so children inherit it) into one private `romp-tests-*` root at
import time and removes the root when the run ends; tests/__init__.py removes its own state dir at
exit, since the package imports before conftest can redirect anything. The same conftest points git
at no global or system config (GIT_CONFIG_GLOBAL, GIT_CONFIG_NOSYSTEM) with a synthetic identity: the
seed commits had been running the developer's global pre-commit hook.

Pinned here from inside a run (the floors are in place and children inherit them; no test pins a
temp path to a literal directory) and end to end
(a nested pytest on a leaking module leaves the system temp dir it was given exactly as it found
it). This module loads no romp code, so it needs no state-root preamble. Everything skips under a
bare unittest run, where conftest never loaded and there is nothing to pin.
"""
import ast
import glob
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
IDENT = "romp tests <tests@example.invalid>"

under_conftest = unittest.skipUnless("tests.conftest" in sys.modules,
                                     "the floors under test are tests/conftest.py's (pytest-only)")


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kw)


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

    def test_the_handed_temp_dir_is_recorded_and_is_the_roots_parent(self):
        # The one sanctioned way out of the root (tests/test_kernel_socket_deliver._socket_dir, for
        # a socket path that would not fit sun_path) goes to the dir the run was handed, never to a
        # literal system path.
        handed = os.environ.get("ROMP_TESTS_SYSTEM_TMPDIR")
        self.assertTrue(handed, "conftest records the temp dir it replaced")
        self.assertEqual(os.path.realpath(os.path.dirname(tempfile.gettempdir())), os.path.realpath(handed))

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

    def test_a_global_hooks_path_cannot_reach_a_fixture_commit(self):
        # A stand-in for the developer's global config: a pre-commit hook that refuses every commit
        # and leaves a marker, wired in through core.hooksPath. Live first, then floored.
        with tempfile.TemporaryDirectory() as td:
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

            live = _run(["git", "commit", "-q", "-m", "seed"], cwd=repo,
                        env=dict(os.environ, GIT_CONFIG_GLOBAL=cfg))
            self.assertNotEqual(live.returncode, 0, "the probe is live: the hook blocks the commit")
            self.assertTrue(os.path.exists(marker))
            os.remove(marker)

            floored = _run(["git", "commit", "-q", "-m", "seed"], cwd=repo)   # the suite's own env
            self.assertEqual(floored.returncode, 0, floored.stderr)
            self.assertFalse(os.path.exists(marker), "no global hook reaches a fixture commit")
            self.assertEqual(_run(["git", "log", "-1", "--format=%an <%ae>"], cwd=repo).stdout.strip(), IDENT)


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
            "PYTEST_XDIST_WORKER", "PYTEST_XDIST_WORKER_COUNT"):
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
