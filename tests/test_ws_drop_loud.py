#!/usr/bin/env python3
"""A client the kernel drops is LOUD — one stderr line and one bell row per drop.

_mk_ws_send raises when a client is WS_QUEUE_BYTES behind (tests/test_ws_send_bounded.py owns that
guarantee); every caller caught it with a bare `c["alive"] = False`. So a dashboard dropped every few
minutes for a day (~120 times, 2026-09-02 — full 5.76 MB feed frames outran the pane) left NO trace in the
kernel log, and the shim logged nothing on its side, and the symptom read as a flaky network for weeks.
Pinned: one line per drop naming the pane, dashboard id, backlog and the exception; a row for the bell via
the kernel-problems channel (_sdk_problem_rows → feed sdkNotices); every send path uses the helper.

Synthetic only: no session data.
"""
import io
import os
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel_wsdroploud", os.path.join(BIN, "romp-kernel")).load_module()


class DroppedClientsAreLoud(unittest.TestCase):
    def _dropping(self):
        def boom(_s):
            raise OSError("ws client feed is 17000000 bytes behind — dropping")
        return {"app": "feed", "alive": True, "wid": "w9", "qbytes": 17000000, "send": boom}

    def test_one_stderr_line_per_drop_naming_pane_dashboard_and_backlog(self):
        c = self._dropping()
        err, old = io.StringIO(), sys.stderr
        sys.stderr = err
        try:
            km._send_client(c, ("feed",), {"type": "feed", "asks": []})
            km._send_client(c, ("working",), {"type": "working"})   # the same cycle's next frame fails too
        finally:
            sys.stderr = old
        lines = [l for l in err.getvalue().splitlines() if l.startswith("ws drop:")]
        self.assertEqual(len(lines), 1, err.getvalue())
        self.assertIn("app=feed", lines[0]); self.assertIn("wid=w9", lines[0])
        self.assertIn("queued=17000000B", lines[0]); self.assertIn("17000000 bytes behind", lines[0])
        self.assertFalse(c["alive"])

    def test_the_drop_reaches_the_bell_through_the_kernel_problem_rows(self):
        n0 = len(km._WS_DROPS)
        old = sys.stderr; sys.stderr = io.StringIO()
        try:
            km._send_client(self._dropping(), ("feed",), {"type": "feed"})
        finally:
            sys.stderr = old
        self.assertEqual(len(km._WS_DROPS), n0 + 1)
        row = km._WS_DROPS[-1]
        self.assertIn("feed pane", row["text"]); self.assertIn("17.0 MB", row["text"])
        self.assertTrue(any(r["text"] == row["text"] and r["sig"].startswith("sdk|") and "|ws|" in r["sig"]
                            for r in km._sdk_problem_rows()), "rides the feed's sdkNotices → the bell")

    def test_every_send_path_goes_through_the_loud_helper(self):
        src = open(os.path.join(BIN, "romp-kernel"), encoding="utf-8").read()
        body = src[src.index("def _send_to_app("):src.index("def _reveal_chat_for(")]
        self.assertNotIn('except Exception:\n            c["alive"] = False', body,
                         "_send_to_app / _keepalive_all / _send_to_view no longer swallow a drop")
        self.assertEqual(body.count("_client_send(c, s)"), 3)


if __name__ == "__main__":
    unittest.main()
