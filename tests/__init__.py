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

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp(prefix="romp-tests-state-")
# Removed at exit: under pytest this dir is minted BEFORE conftest.py redirects the temp root
# (the package imports first), so it is the one state dir the run-wide backstop cannot reach.
atexit.register(shutil.rmtree, os.environ["XDG_STATE_HOME"], ignore_errors=True)
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
