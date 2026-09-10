#!/usr/bin/env python3
"""An EMPTY XDG_STATE_HOME is unset, for every Python reader as for every bash reader.

bin/romp-serve, bin/romp-sdk-setup, bin/romp-service and bin/romp resolve the state root with
`${XDG_STATE_HOME:-$HOME/.local/state}/romp`, and the manager with `process.env.XDG_STATE_HOME ||`;
both treat an empty value as unset, as the XDG Base Directory spec requires. kernel/event_model.py and
kernel/judge.py used `os.environ.get("XDG_STATE_HOME", default)`, which keeps an empty value and made
the state root the RELATIVE path `romp` (wherever the process happened to be). A `XDG_STATE_HOME=` line
in service.env then had romp-serve find the SDK venv under ~/.local/state/romp and run its interpreter
while the kernel looked for it under ./romp and reported the SDK as not installed (review 2026-09-06).
postal/postal_service.py and cli/idle_dots.py carried the same .get default, so the postal bus's mail and
the idle-dots pidfile would have moved with the cwd the same way; all four readers now use `or`.

Pinned in a child process, because every one of these modules resolves STATE at import time. The
empty-value case and the honored-value case are pinned upstream since #1211 in
tests/test_state_dir_override.py (PythonSurfaces.test_empty_xdg_state_home_is_unset and
test_default_is_untouched_without_the_override, over the same readers plus the postal NAMES_DIR); this
module keeps the one case those do not run: ROMP_STATE_DIR set BESIDE an empty XDG_STATE_HOME wins
(PythonSurfaces' override case has no XDG_STATE_HOME in its env at all). HOME is a temp dir in the child,
so judge.py's import-time mkdir of the root lands nowhere real."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
KERNEL = os.path.join(ROOT, "kernel")
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

# Four readers, one answer each: the kernel's two modules give the root itself; the postal bus's STATE is
# <root>/postal (its parent is the root); idle-dots gives the root.
CHILD = r"""
import json, os, sys
root = sys.argv[1]
sys.path.insert(0, os.path.join(root, "tests"))   # tests/romp_load.py: the suite's file-path importer
from romp_load import load_source
em = load_source("romp_event_model_xdg", os.path.join(root, "kernel", "event_model.py"))
jd = load_source("romp_judge_xdg", os.path.join(root, "kernel", "judge.py"))
ps = load_source("romp_postal_xdg", os.path.join(root, "postal", "postal_service.py"))
idl = load_source("romp_idle_dots_xdg", os.path.join(root, "cli", "idle_dots.py"))
print(json.dumps({"event_model": str(em.STATE), "judge": str(jd.STATE),
                  "postal": str(ps.STATE.parent), "idle_dots": str(idl.STATE)}))
"""
READERS = ("event_model", "judge", "postal", "idle_dots")


def _roots(env_over):
    home = tempfile.mkdtemp()
    env = {"HOME": home, "PATH": os.environ.get("PATH", "")}
    env.update(env_over)
    out = subprocess.run([sys.executable, "-c", CHILD, ROOT], env=env, capture_output=True, text=True,
                         timeout=120, check=True).stdout
    return home, json.loads(out.strip().splitlines()[-1])


class EmptyXdgStateHome(unittest.TestCase):
    def test_romp_state_dir_outranks_both(self):
        # an EMPTY XDG_STATE_HOME beside the override: the override is read first and the empty value
        # never gates it (test_state_dir_override.py's override case runs with no XDG_STATE_HOME set)
        base = tempfile.mkdtemp()
        _, roots = _roots({"XDG_STATE_HOME": "", "ROMP_STATE_DIR": base})
        self.assertEqual(roots, {r: base for r in READERS})


if __name__ == "__main__":
    unittest.main()
