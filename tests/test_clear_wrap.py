#!/usr/bin/env python3
"""Clear is a SILENT discard (the user 2026-08-23, reversing the 2026-07-24 one-round wrap-up).

The wrap-up told the owning session its open card was being dismissed; the response turn then
routinely re-minted the very card the user had just cleared — a discard that answered back. The
gesture now only discards: the session hears NOTHING, and if anything real remains it is on the
user to ask a follow-up or say so themselves. Judge-side recognition of the historical
<!-- romp-clear-wrap --> marker STAYS: recorded transcripts still contain old wraps, and re-parsing
them must keep classifying those turns correctly. SYNTHETIC fixtures only."""
import json
import os
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_clearwrap", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "33333333-4444-5555-6666-777777777777"   # private to this module (the repo's goal-store fixture
#                                                   rule): the clear below appends a row for <sid>:g1 to the
#                                                   worker's shared cleared.jsonl, and under the shared
#                                                   placeholder sid that row sealed every later fresh store's
#                                                   g1 (open_menu reads _view_cleared) — test_judge's
#                                                   KnownTargetContext failed whenever this module ran first
#                                                   on its worker (2026-09-06)
G_OPEN = SID + ":g1"
NOW = 1781100000


class SentNothing:
    def __init__(self):
        self.sent = []

    def send(self, sid, text):
        self.sent.append((sid, text))


class ClearIsSilent(unittest.TestCase):
    # The clear writes three files under the worker's shared state root (cleared.jsonl, this sid's goal
    # store, its override journal); each goes back to what it was, or away, so no later test reads them.
    def setUp(self):
        paths = (jd.STATE / "cleared.jsonl", jd.GOALDIR / (SID + ".json"), jd._overrides_dir() / (SID + ".jsonl"))
        self._before = [(q, q.read_bytes() if q.exists() else None) for q in paths]

    def tearDown(self):
        for q, data in self._before:
            if data is None:
                q.unlink(missing_ok=True)
            else:
                q.write_bytes(data)

    def test_clearing_an_open_card_sends_the_session_nothing(self):
        store = jd.load_goals(SID)
        store["nodes"][G_OPEN] = jd.GuardedNode({"id": G_OPEN, "text": "build the exporter",
                                                 "parentId": None, "nodeComplete": False,
                                                 "blocked": False, "cleared": False,
                                                 "t": NOW - 600, "mt": NOW - 60, "log": []})
        store["status"] = {G_OPEN: "working"}
        jd.save_goals(SID, store)
        be = SentNothing()
        saved = (km.Sessions.backend_for, km._tmux_sessions)
        km.Sessions.backend_for = staticmethod(lambda sid: be)
        km._tmux_sessions = lambda: {SID: {"state": "idle"}}
        try:
            km._clear_all([G_OPEN])
        finally:
            km.Sessions.backend_for, km._tmux_sessions = saved
        self.assertEqual(be.sent, [], "a discard that answers back is the loop this retirement ends")
        rows = [json.loads(l) for l in (jd.STATE / "cleared.jsonl").read_text().splitlines()]
        self.assertTrue(any(r.get("id") == G_OPEN and r.get("op") == "clear" for r in rows),
                        "the discard itself still lands")

    def test_the_sender_machinery_is_gone_and_the_tombstone_stands(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertNotIn("def _clear_wrap_notify", src)
        self.assertNotIn("def _clear_wrap_body", src)
        self.assertIn("CLEAR IS SILENT", src)

    def test_the_judge_still_recognizes_historical_wrap_markers(self):
        src = open(os.path.join(BIN, "romp-judge")).read()
        self.assertIn("romp-clear-wrap", src,
                      "recorded transcripts contain old wraps; re-parsing must keep classifying them")


if __name__ == "__main__":
    unittest.main()
