#!/usr/bin/env python3
"""The chat page's approval box, kernel side (plans/notice-cards.md, "Action kinds and the held-mail card", 2026-09-19).
Upstream's box reads _chat_notices on the session frame's status and in the chat signature; this fork holds _chat_notices and
both call sites out with the held-mail backfill that fed it (kernel.py, "THIS FORK HOLDS OUT"), so the tests of the rows, the
slice and the signature left with it (fold 4 of the upstream work, 2026-10-02). What stays is the box's mount: the chat page's
markup places the inert #notices div between the transcript and the background box, where the chat renderer and the skeleton
page look for it. Synthetic: a placeholder sid, invented names and text."""
import inspect
import json
import os
import sys
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-000000000902"   # a PRIVATE synthetic sid: the suite shares one state root across modules, and a names
#                                                entry left under the shared placeholder poisons a later module's route test (2026-09-19)
KSRC = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")).read()


def _held(mid):
    return [{"label": "Approve", "kind": "quarantine", "body": {"mid": mid, "verdict": "approve"}},
            {"label": "Deny", "kind": "quarantine", "body": {"mid": mid, "verdict": "deny"}}]


class ChatNotices(unittest.TestCase):
    # the suite runs every module in one process over one state root: these tests restore the SHARED files they append to (the
    # owner-less home, its archive and index, the cleared ledger) and unlink only their own sid's files (the review of PR 1890,
    # low c, the 1885 round-two rule)
    @staticmethod
    def _shared():
        out = {}
        f = km.jd.STATE / "cleared.jsonl"
        out["cleared.jsonl"] = f.read_bytes() if f.exists() else None
        for d in ("notices", "notices-archive"):
            dd = km.jd.STATE / d
            if dd.exists():
                for f in dd.iterdir():
                    if f.name.startswith("notes"):
                        out[d + "/" + f.name] = f.read_bytes()
        return out

    def setUp(self):
        self._before = self._shared()
        km.jd.NAMES.mkdir(parents=True, exist_ok=True)
        (km.jd.NAMES / SID).write_text("web\t%s\t#1EA1EB\t#ffffff\n" % (km.jd.STATE / "notes-api"))
        km.NAMES = km.jd.NAMES
        km._live_scope.names = None
        km._NOTICE_MEMO.clear(); km._CLEARED_MEMO["slot"] = None
        self._needs = km._feed_needs_input[0]
        km._feed_needs_input[0] = frozenset()             # a feed build happened: the slice answers (the gate is its own test)

    def tearDown(self):
        km._feed_needs_input[0] = self._needs
        for f in (km.jd.NAMES / SID, km.jd.STATE / "notices" / (SID + ".jsonl"), km.jd.STATE / "notices-archive" / (SID + ".jsonl"),
                  km.jd.STATE / "notices-archive" / (SID + ".revs.json")):
            if f.exists():
                f.unlink()
        after = self._shared()
        for rel in set(after) | set(self._before):
            f = km.jd.STATE / rel
            before = self._before.get(rel)
            if before is None:
                if f.exists():
                    f.unlink()
            elif after.get(rel) != before:
                f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(before)
        km._NOTICE_MEMO.clear(); km._CLEARED_MEMO["slot"] = None

    def test_the_chat_page_places_the_box_between_the_transcript_and_the_background_box(self):
        body = km._chat_body()
        self.assertIn('<div id="notices" style="display:none"></div>', body)
        self.assertLess(body.index('id="content"'), body.index('id="notices"'), "after the transcript")
        self.assertLess(body.index('id="notices"'), body.index('id="bg-tasks"'), "above the background box (the user: a decision sits nearest the composer's eye line, above the agents)")
        self.assertLess(body.index('id="bg-tasks"'), body.index('id="composer"'))


if __name__ == "__main__":
    unittest.main()
