"""Fast mode's kernel plumbing (fork additions on top of the upstream toggle — the toggle itself is
pinned by ui/webview/fast-toggle.test.ts and driven end-to-end in tests/test_kernel_send_park.py).

Two things live here: the drive/park wiring stays registered on both surfaces, and the parked-op
FIFO's compatibility shim — a queue written by a pre-2026-08-09 kernel stored fast ops as BOOLS,
and today's string-validating set_fast would refuse them, so the replay coerces. SYNTHETIC fixtures
only."""
import os
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()   # hermetic BEFORE any romp code loads
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_fastmode", os.path.join(BIN, "romp-kernel"))

# Neutralize the ACCOUNT gate (_limit_hold), exactly as tests/test_kernel_send_park.py does: left
# live, the replay test would read the REAL machine's usage.json and park for a reason it isn't about.
km._limit_hold = lambda sid: None

SID = "11111111-2222-3333-4444-555555555555"


class _FakeBackend:
    def __init__(self):
        self.calls = []

    def set_fast(self, sid, value):
        if value not in ("on", "off"):     # the real contract: set_fast validates the string form
            return False
        self.calls.append(("fast", value))
        return True


class FastModeWiring(unittest.TestCase):
    def test_the_drive_op_is_registered(self):
        import inspect
        self.assertIn('"setFast"', inspect.getsource(km._drive))

    def test_the_park_queue_understands_the_fast_op(self):
        import inspect
        self.assertIn('elif op[0] == "fast":', inspect.getsource(km._apply_pending_ops))

    def test_both_surfaces_read_the_same_word(self):
        # the chat chip and the timeline lane's asterisk are two renderings of ONE server-side answer —
        # the CLI's init word, blanked when a disabled_reason means /fast would refuse — so neither can
        # drift from the other (the user 2026-08-08 asked for the compact form on the lane)
        import inspect
        blanked = '"" if tm.get("fastReason") else tm.get("fast", "")'
        self.assertIn(blanked, inspect.getsource(km.build_session))
        self.assertIn(blanked, inspect.getsource(km.build_timeline))


class ParkedBoolCoercion(unittest.TestCase):
    """A parked fast op that survived the 2026-08-09 upgrade stores a BOOL (the old set_fast took one);
    the replay must coerce it to the string form or the op is refused and the user's parked pick
    silently evaporates."""

    def setUp(self):
        self.be = _FakeBackend()
        self._saved = (km._compacting_now, km._working_now, km.Sessions.backend_for, km._push_all)
        km._push_all = lambda: None
        km._compacting_now = lambda sid: False
        km._working_now = lambda sid: False
        km.Sessions.backend_for = lambda sid: self.be
        km._pending_ops.clear()

    def tearDown(self):
        (km._compacting_now, km._working_now, km.Sessions.backend_for, km._push_all) = self._saved
        km._pending_ops.clear()

    def test_a_parked_bool_replays_as_the_string_the_backend_takes(self):
        km._pending_ops[SID] = [("fast", True)]
        km._apply_pending_ops()
        self.assertEqual(self.be.calls, [("fast", "on")], "True → 'on', delivered, not refused")
        self.assertNotIn(SID, km._pending_ops, "the queue drains instead of wedging")
        km._pending_ops[SID] = [("fast", False)]
        km._apply_pending_ops()
        self.assertEqual(self.be.calls[-1], ("fast", "off"))

    def test_a_string_op_passes_through_untouched(self):
        km._pending_ops[SID] = [("fast", "on")]
        km._apply_pending_ops()
        self.assertEqual(self.be.calls, [("fast", "on")])


if __name__ == "__main__":
    unittest.main()
