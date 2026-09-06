"""unittest-side twin of conftest.py's state floor (2026-08-12): `python -m unittest tests.test_x`
imports this package first, so the floor lands before any test module loads bin/romp-* — which
resolve their state root at import time. conftest.py covers only pytest; without this, a bare
unittest run operated on the REAL ~/.local/state/romp (tests/test_kernel.py overwrote the real
remotes.json that way today). Does NOT cover `cd tests && python -m unittest test_x` or a direct
script run — the per-module preambles do, and tests/test_state_isolation_order.py enforces them."""
import atexit
import os
import shutil
import tempfile

# Temp-directory hygiene (2026-09-06): the suite used to leak every directory it made. This floor and
# conftest.py's each minted a state root per process and never removed it (two per pytest process:
# eighteen for a `pytest -n 8` run), and about three hundred test modules call tempfile.mkdtemp with
# no cleanup of their own. On a developer machine that ran the suite many times a day that left about
# 1.9 million directories under the system temp directory, enough that listing it took minutes and
# tens of gigabytes of memory, and the out-of-memory kills that followed took a running romp kernel
# down. The fix is at the source: every tempfile.mkdtemp call made in this process is recorded, and
# everything recorded is removed at interpreter exit (and, under pytest, at session end; see
# conftest.py). Only directories this process created, and only under the system temp directory, are
# ever removed. tempfile.TemporaryDirectory goes through the same mkdtemp and cleans itself first, so
# the exit sweep finds nothing of it. This package imports before conftest.py (pytest imports
# `tests.conftest` through the package), so conftest's own root is recorded too.
_MADE_DIRS = []
_REAL_MKDTEMP = tempfile.mkdtemp


def _tracked_mkdtemp(*a, **k):
    p = _REAL_MKDTEMP(*a, **k)
    _MADE_DIRS.append(p)
    return p


_tracked_mkdtemp.romp_tracked = True          # tests/test_tempdir_hygiene.py asserts the hook is installed
if not getattr(tempfile.mkdtemp, "romp_tracked", False):
    tempfile.mkdtemp = _tracked_mkdtemp


def remove_made_dirs():
    """Remove every directory this process minted through tempfile.mkdtemp. Idempotent; registered
    with atexit here and called again from conftest's pytest_sessionfinish."""
    root = os.path.realpath(tempfile.gettempdir())
    for p in reversed(list(_MADE_DIRS)):
        try:
            rp = os.path.realpath(p)
            if rp != root and rp.startswith(root + os.sep) and os.path.isdir(rp) and not os.path.islink(p):
                shutil.rmtree(rp, ignore_errors=True)
        except Exception:
            pass
    _MADE_DIRS.clear()


atexit.register(remove_made_dirs)

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp(prefix="romp-tests-state-")
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
