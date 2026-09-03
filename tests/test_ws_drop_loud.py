#!/usr/bin/env python3
"""A client the kernel drops is LOUD — one stderr line and one bell row per drop.

_mk_ws_send raises when a client is WS_QUEUE_BYTES behind (tests/test_ws_send_bounded.py owns that
guarantee); every caller caught it with a bare `c["alive"] = False`. So a dashboard dropped every few
minutes for a day (~120 times, 2026-09-02 — full 5.76 MB feed frames outran the pane) left NO trace in the
kernel log, and the shim logged nothing on its side, and the symptom read as a flaky network for weeks.
Pinned: one line per drop naming the pane, dashboard id, backlog and the exception; a row for the bell via
the kernel-problems channel (_sdk_problem_rows → feed sdkNotices); the log lives at the RAISE site
(_mk_ws_send → _note_ws_drop), so the ~60 one-shot `client["send"]` replies are covered too, not only the
push paths that go through _client_send (the 2026-09-03 review found that gap); and the bell shows at most a
few RECENT drop rows, merged by time with the backend's problems — twenty drops appended last and sliced
positionally used to hide every later backend problem for the rest of the kernel's life.

Synthetic only: no session data.
"""
import io
import os
import queue
import sys
import threading
import time
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

    def test_a_drop_through_a_direct_send_is_loud_too(self):
        # the RAISE site logs, so whichever caller's frame tips the budget — a one-shot reply through a
        # bare client["send"], with no helper in sight — leaves the line and the bell row
        class _Sock:
            def shutdown(self, how):
                pass
        client = {"app": "chat", "wid": "w3", "alive": True, "qbytes": km.WS_QUEUE_BYTES - 10,
                  "qlock": threading.Lock()}
        client["send"] = km._mk_ws_send(queue.Queue(), _Sock(), client)
        n0 = len(km._WS_DROPS)
        err, old = io.StringIO(), sys.stderr
        sys.stderr = err
        try:
            with self.assertRaises(OSError):
                client["send"]('{"type":"renamed"}' + "x" * 100)
            km._client_send(client, "a later frame")   # the helper on the same dead client: latched, no second line
        finally:
            sys.stderr = old
        lines = [l for l in err.getvalue().splitlines() if l.startswith("ws drop:")]
        self.assertEqual(len(lines), 1, err.getvalue())
        self.assertIn("app=chat", lines[0]); self.assertIn("wid=w3", lines[0]); self.assertIn("bytes behind", lines[0])
        self.assertFalse(client["alive"])
        self.assertEqual(len(km._WS_DROPS), n0 + 1)
        self.assertIn("chat pane", km._WS_DROPS[-1]["text"])

    def test_drop_rows_never_crowd_a_backend_problem_out_of_the_bell(self):
        class _Be:
            def problems(self, limit=0):
                return [{"seq": 7, "t": time.time(), "text": "sdk session web crashed"}]

            def problem_seq(self):
                return 7
        saved = (list(km._WS_DROPS), km._sdk_backend)
        old = sys.stderr
        sys.stderr = io.StringIO()
        try:
            km._WS_DROPS[:] = []
            for _ in range(25):
                km._send_client(self._dropping(), ("feed",), {"type": "feed"})
            km._sdk_backend = _Be()
            rows = km._sdk_problem_rows()
            kinds = [r["sig"].split("|")[2] for r in rows]
            self.assertIn("be", kinds, "the backend problem shows beside the drops: %r" % kinds)
            self.assertLessEqual(kinds.count("ws"), km._WS_DROP_BELL_ROWS, "a few drop rows at most")
            self.assertEqual([r["t"] for r in rows], sorted(r["t"] for r in rows), "merged by time")
            for r in km._WS_DROPS:
                r["t"] -= km._WS_DROP_TTL_S + 1
            self.assertEqual([r["sig"].split("|")[2] for r in km._sdk_problem_rows()], ["be"],
                             "an hour-old drop has left the bell (the log keeps it)")
        finally:
            sys.stderr = old
            km._WS_DROPS[:] = saved[0]
            km._sdk_backend = saved[1]

    def test_every_send_path_goes_through_the_loud_helper(self):
        src = open(os.path.join(BIN, "romp-kernel"), encoding="utf-8").read()
        body = src[src.index("def _send_to_app("):src.index("def _reveal_chat_for(")]
        self.assertNotIn('except Exception:\n            c["alive"] = False', body,
                         "_send_to_app / _keepalive_all / _send_to_view no longer swallow a drop")
        self.assertEqual(body.count("_client_send(c, s)"), 3)
        raise_site = src[src.index("def _mk_ws_send("):src.index("def _ws_send(")]
        self.assertIn("_note_ws_drop(client, e, len(s))\n                raise e", raise_site,
                      "the raise site logs, so every direct caller is covered")


if __name__ == "__main__":
    unittest.main()
