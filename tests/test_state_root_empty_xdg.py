#!/usr/bin/env python3
"""An EMPTY XDG_STATE_HOME is unset, for the kernel's Python as for every bash reader.

bin/romp-serve, bin/romp-sdk-setup, bin/romp-service and bin/romp resolve the state root with
`${XDG_STATE_HOME:-$HOME/.local/state}/romp`, and the manager with `process.env.XDG_STATE_HOME ||`;
both treat an empty value as unset, as the XDG Base Directory spec requires. kernel/event_model.py and
kernel/judge.py used `os.environ.get("XDG_STATE_HOME", default)`, which keeps an empty value and made
the state root the RELATIVE path `romp` (wherever the process happened to be). A `XDG_STATE_HOME=` line
in service.env then had romp-serve find the SDK venv under ~/.local/state/romp and run its interpreter
while the kernel looked for it under ./romp and reported the SDK as not installed (review 2026-09-06).

Pinned here in a child process, because both modules resolve STATE at import time: with an empty
XDG_STATE_HOME the root is $HOME/.local/state/romp; with a value it is that value plus /romp; with
ROMP_STATE_DIR set that wins. HOME is a temp dir in the child, so judge.py's import-time mkdir of the
root lands nowhere real."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
KERNEL = os.path.join(os.path.dirname(HERE), "kernel")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

CHILD = r"""
import json, os, sys
from importlib.machinery import SourceFileLoader
em = SourceFileLoader("romp_event_model_xdg", os.path.join(sys.argv[1], "event_model.py")).load_module()
jd = SourceFileLoader("romp_judge_xdg", os.path.join(sys.argv[1], "judge.py")).load_module()
print(json.dumps({"event_model": str(em.STATE), "judge": str(jd.STATE)}))
"""


def _roots(env_over):
    home = tempfile.mkdtemp()
    env = {"HOME": home, "PATH": os.environ.get("PATH", "")}
    env.update(env_over)
    out = subprocess.run([sys.executable, "-c", CHILD, KERNEL], env=env, capture_output=True, text=True,
                         timeout=120, check=True).stdout
    return home, json.loads(out.strip().splitlines()[-1])


class EmptyXdgStateHome(unittest.TestCase):
    def test_empty_is_unset(self):
        home, roots = _roots({"XDG_STATE_HOME": ""})
        want = os.path.join(home, ".local", "state", "romp")
        self.assertEqual(roots, {"event_model": want, "judge": want},
                         "the bash pickers read an empty value as unset; the kernel must agree")

    def test_a_value_is_honored(self):
        base = tempfile.mkdtemp()
        _, roots = _roots({"XDG_STATE_HOME": base})
        want = os.path.join(base, "romp")
        self.assertEqual(roots, {"event_model": want, "judge": want})

    def test_romp_state_dir_outranks_both(self):
        base = tempfile.mkdtemp()
        _, roots = _roots({"XDG_STATE_HOME": "", "ROMP_STATE_DIR": base})
        self.assertEqual(roots, {"event_model": base, "judge": base})


if __name__ == "__main__":
    unittest.main()
