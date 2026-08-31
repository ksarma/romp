#!/usr/bin/env python3
"""live_sessions is guarded PER SESSION (2026-08-31): the row loop used to run unguarded under the
kernel merge's single try, so ONE session's snapshot() exception silently dropped EVERY SDK session
from an otherwise-successful listing — and absence from a listing reads as death downstream (the
postal bus refused sends to live peers over exactly this class of gap). One bad row now keeps its
other sessions listed, and the failing session itself stays visible as a minimal waiting row.
Synthetic; hermetic state."""
import os
import tempfile
import unittest
from unittest import mock
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sb = SourceFileLoader("romp_sdk_backend_liverows", os.path.join(BIN, "romp_sdk_backend.py")).load_module()

SID_A = "11111111-2222-3333-4444-aaaaaaaaaaaa"
SID_B = "11111111-2222-3333-4444-bbbbbbbbbbbb"


class LiveRowsGuard(unittest.TestCase):
    def setUp(self):
        self.be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        for sid, name in ((SID_A, "web"), (SID_B, "api")):
            sb.write_reg(self.be.state_dir, sid,
                         {"sid": sid, "name": name, "alive": True, "model": "opus"})

    def test_one_bad_snapshot_never_hides_the_others(self):
        broken = mock.Mock()
        broken.thread.is_alive.return_value = True
        broken.snapshot.side_effect = RuntimeError("mid-reconnect blink")
        self.be.sessions[SID_A] = broken
        out = self.be.live_sessions()
        self.assertEqual(set(out), {SID_A, SID_B},
                         "the whole point: a bad row keeps the OTHER sessions listed")
        self.assertEqual(out[SID_A]["state"], "waiting",
                         "the failing session stays visible as a minimal row — absent reads as dead")
        self.assertEqual(out[SID_B]["state"], "waiting", "the dormant sibling's real row")
        self.assertEqual(out[SID_B]["model"], "Opus")

    def test_a_sidless_reg_dict_is_not_fatal(self):
        # list_regs injects the filename as sid for a reg missing the field; either way the
        # loop must survive it and keep the real sessions listed
        sb.write_reg(self.be.state_dir, "nosid", {"alive": True})
        out = self.be.live_sessions()
        self.assertIn(SID_A, out)
        self.assertIn(SID_B, out)


if __name__ == "__main__":
    unittest.main()
