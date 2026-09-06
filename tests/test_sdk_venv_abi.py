#!/usr/bin/env python3
"""The kernel adds the SDK venv's site-packages only when they were built for the interpreter it runs.

bin/romp-sdk-setup builds the venv under STATE/sdkvenv with one python; the kernel's
_ensure_sdk_on_path used to add EVERY sdkvenv/lib/python3.*/site-packages it found to sys.path. When
the kernel came up on a different python (2026-09-06: a newer interpreter appeared on the box between
two respawns), the 3.X venv joined a 3.Y process, the SDK's compiled dependency failed to import, and
the error every session showed blamed a missing install that was in fact present and intact.

Pinned here: only the site-packages whose python3.X matches sys.version_info is added; a venv present
for another version adds nothing and logs one line naming both versions and the two remedies; no venv
at all stays the plain "not importable" path with no version talk. Hermetic state; find_spec is
stubbed so the outcome does not depend on whether this machine has the SDK installed."""
import io
import os
import shutil
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel_venv_abi", os.path.join(BIN, "romp-kernel")).load_module()
jd = km.jd

RUNNING = "python%d.%d" % sys.version_info[:2]


class EnsureSdkOnPath(unittest.TestCase):
    def setUp(self):
        self.venv = jd.STATE / "sdkvenv"
        shutil.rmtree(self.venv, ignore_errors=True)
        self.path_before = list(sys.path)
        self.err = io.StringIO()
        km._SDK_VENV_BUILT_FOR = []            # the once-per-verdict dedupe must not leak across tests

    def tearDown(self):
        shutil.rmtree(self.venv, ignore_errors=True)
        sys.path[:] = self.path_before

    def _site(self, pyname):
        sp = self.venv / "lib" / pyname / "site-packages"
        sp.mkdir(parents=True)
        return str(sp)

    def _run(self, importable_from=None):
        """Call _ensure_sdk_on_path with find_spec stubbed: the SDK is importable only once a directory
        under `importable_from` is on sys.path (the real finder would answer from this machine)."""
        import importlib.util

        def fake_find_spec(name, *a, **k):
            if name != "claude_agent_sdk":
                return importlib.util.find_spec.__wrapped__(name, *a, **k)
            if importable_from and any(p.startswith(importable_from) for p in sys.path):
                return SimpleNamespace(name=name)
            return None
        fake_find_spec.__wrapped__ = importlib.util.find_spec
        with mock.patch.object(importlib.util, "find_spec", fake_find_spec), \
             mock.patch.object(sys, "stderr", self.err):
            return km._ensure_sdk_on_path()

    def test_a_venv_for_another_python_is_not_added_and_is_named(self):
        sp = self._site("python3.99")
        self.assertFalse(self._run(importable_from=sp))
        self.assertNotIn(sp, sys.path, "a 3.99 venv must never join a %s process" % RUNNING)
        line = self.err.getvalue()
        self.assertIn("3.99", line, "names what the venv was built for")
        self.assertIn("%d.%d" % sys.version_info[:2], line, "and what the kernel runs")
        self.assertIn("romp-sdk-setup", line)
        self.assertIn("ROMP_PYTHON", line, "both remedies: rebuild, or run the venv's interpreter")
        self.assertNotIn("not installed", line)

    def test_a_matching_venv_is_added_and_the_sdk_imports(self):
        sp = self._site(RUNNING)
        self.assertTrue(self._run(importable_from=sp))
        self.assertIn(sp, sys.path)
        self.assertEqual(self.err.getvalue(), "", "nothing to say when the venv matches")

    def test_only_the_matching_directory_joins_when_both_exist(self):
        # a rebuilt venv can leave the old lib/python3.X beside the new one; add the match only
        old = self._site("python3.99")
        new = self._site(RUNNING)
        self.assertTrue(self._run(importable_from=new))
        self.assertIn(new, sys.path)
        self.assertNotIn(old, sys.path)
        self.assertEqual(self.err.getvalue(), "")

    def test_the_creation_refusal_follows_the_verdict(self):
        # `romp new` / the browser's create both refuse with _sdk_setup_hint(): after a mismatch it
        # names the versions and both remedies; otherwise it is the install hint, unchanged
        self._run(importable_from=self._site("python3.99"))
        hint = km._sdk_setup_hint()
        self.assertIn("3.99", hint)
        self.assertIn("%d.%d" % sys.version_info[:2], hint)
        self.assertIn("ROMP_PYTHON", hint)
        self.assertIn("romp-sdk-setup", hint)
        self.assertNotIn("isn't installed", hint)
        shutil.rmtree(self.venv)
        self._run()
        self.assertEqual(km._sdk_setup_hint(), km.SDK_SETUP_HINT)

    def test_no_venv_is_the_plain_not_importable_path(self):
        self.assertFalse(self._run())
        self.assertEqual(sys.path, self.path_before)
        self.assertEqual(self.err.getvalue(), "", "no venv: nothing to say here (the backend reports it)")


if __name__ == "__main__":
    unittest.main()
