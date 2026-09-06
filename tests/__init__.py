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
# Under pytest this dir is minted BEFORE conftest.py redirects the temp root (the package imports
# first), so it sits beside the root in the system temp dir rather than inside it; conftest reads
# STATE_DIR and removes it with the root when the run ends. This atexit is for unittest runs,
# where conftest never loads. Neither runs after an os._exit (pytest-timeout's thread method), so
# a hung run leaves this dir beside the root.
STATE_DIR = os.environ["XDG_STATE_HOME"]
atexit.register(shutil.rmtree, STATE_DIR, ignore_errors=True)
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
