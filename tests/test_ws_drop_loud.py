#!/usr/bin/env python3
"""A client the kernel drops is LOUD — one stderr line and one bell row per drop.

_mk_ws_send raises when a client is WS_QUEUE_BYTES behind (tests/test_ws_send_bounded.py owns that
guarantee); every caller caught it with a bare `c["alive"] = False`. So a dashboard dropped every few
minutes for a day (~120 times, 2026-09-02 — full 5.76 MB feed frames outran the pane) left NO trace in the
kernel log, and the shim logged nothing on its side, and the symptom read as a flaky network for weeks.
Pinned: one line per drop naming the pane, dashboard id, backlog, the exception and — for a push-path drop —
the slot whose frame tipped the budget (the raise site has no key of its own; _client_send leaves the slot in
flight on the client for the length of its call, and a one-shot reply reads `slot=-`, honestly); a row for
the bell via the kernel-problems channel (_sdk_problem_rows → feed sdkNotices); the log lives at the RAISE
site (_mk_ws_send → _note_ws_drop), so the ~60 one-shot `client["send"]` replies are covered too, not only the
push paths that go through _client_send (the 2026-09-03 review found that gap, then found the slot lost to
the move); and the bell shows at most a few RECENT drop rows, merged by time with the backend's problems —
twenty drops appended last and sliced positionally used to hide every later backend problem for the rest of
the kernel's life.

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
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_wsdroploud", os.path.join(BIN, "romp-kernel"))


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

    def _budgeted(self, app, wid):
        """A client with the kernel's OWN send (_mk_ws_send), ten bytes under the drop budget: the next frame tips it."""
        class _Sock:
            def shutdown(self, how):
                pass
        client = {"app": app, "wid": wid, "alive": True, "qbytes": km.WS_QUEUE_BYTES - 10,
                  "qlock": threading.Lock()}
        client["send"] = km._mk_ws_send(queue.Queue(), _Sock(), client)
        return client

    def _drop_lines(self, err):
        return [l for l in err.getvalue().splitlines() if l.startswith("ws drop:")]

    def test_a_drop_through_a_direct_send_is_loud_too(self):
        # the RAISE site logs, so whichever caller's frame tips the budget — a one-shot reply through a
        # bare client["send"], with no helper in sight — leaves the line and the bell row
        client = self._budgeted("chat", "w3")
        n0 = len(km._WS_DROPS)
        err, old = io.StringIO(), sys.stderr
        sys.stderr = err
        try:
            with self.assertRaises(OSError):
                client["send"]('{"type":"renamed"}' + "x" * 100)
            # the line is on stderr the moment the raise site fires — BEFORE any helper has run on this
            # client (the 2026-09-03 review: with the helper's own later line counted, this test passed
            # with the raise-site log removed)
            lines = self._drop_lines(err)
            self.assertEqual(len(lines), 1, err.getvalue())
            self.assertIn("slot=-", lines[0], "a one-shot reply has no push slot, and the line says so")
            self.assertEqual(len(km._WS_DROPS), n0 + 1)
            km._client_send(client, "a later frame", ("chat", "x"))   # the helper on the same dead client: latched
        finally:
            sys.stderr = old
        lines = self._drop_lines(err)
        self.assertEqual(len(lines), 1, "no second line for the same drop: " + err.getvalue())
        self.assertIn("app=chat", lines[0]); self.assertIn("wid=w3", lines[0]); self.assertIn("bytes behind", lines[0])
        self.assertFalse(client["alive"])
        self.assertEqual(len(km._WS_DROPS), n0 + 1)
        self.assertIn("chat pane", km._WS_DROPS[-1]["text"])

    def test_a_push_path_drop_names_the_slot_whose_frame_tipped_the_budget(self):
        # the raise site has no key of its own; _client_send leaves the slot in flight on the client for
        # the length of the call, so the line names the frame — feed, a chat sid, the tab order — that
        # did it (the 2026-09-03 review: after the log moved to the raise site every line read `slot=-`)
        sid = "11111111-2222-3333-4444-555555555555"
        for key, named in ((("feed",), "slot=feed "), (("chat", sid), "slot=chat:11111111 "), (("taborder",), "slot=taborder ")):
            client = self._budgeted("feed", "w9")
            err, old = io.StringIO(), sys.stderr
            sys.stderr = err
            try:
                self.assertFalse(km._client_send(client, "x" * 100, key))
            finally:
                sys.stderr = old
            lines = self._drop_lines(err)
            self.assertEqual(len(lines), 1, err.getvalue())
            self.assertIn(named, lines[0], key)
            self.assertNotIn("slot=-", lines[0])
            self.assertIn("frame=100B", lines[0])
            self.assertNotIn("curSlot", client, "the slot in flight is cleared after the call: a later one-shot reads `-`")
        # a client whose push-path drop was logged: a later direct send raises again, latched, no second line
        client = self._budgeted("feed", "w9")
        err, old = io.StringIO(), sys.stderr
        sys.stderr = err
        try:
            km._client_send(client, "x" * 100, ("feed",))
            with self.assertRaises(OSError):
                client["send"]("y" * 100)
        finally:
            sys.stderr = old
        self.assertEqual(len(self._drop_lines(err)), 1)

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
