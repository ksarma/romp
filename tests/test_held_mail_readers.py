#!/usr/bin/env python3
"""The held-mail (quarantine) card road's readers, kernel side (2026-09-19). One rule runs through every case here: a
reader that cannot parse must not report ABSENT and must not take down callers that had nothing to do with the bad row.
Skip the row, name the session and the key in the log, keep the board.

The cases: the footer's Clear-all reaches _clear_all with every ask id, a hold's included, and the hold's card must stand
(a hold is decided by Approve or Deny, never dismissed); one type-wrong value in one notice row must not raise out of
every feed build; the quarantine directory reader must name a directory it cannot list, move a record it cannot read
aside once with the other holds still built, and name a record with no message id.

Synthetic only: a hermetic temp state root, placeholder session ids, invented hold and notice text, TESTHOST. Every root
this module mints writes `off` into <root>/session-hosts (repo rule, 2026-09-11) and no goals are minted."""
import contextlib
import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
_XDG = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = _XDG
os.environ.pop("ROMP_STATE_DIR", None)
os.makedirs(os.path.join(_XDG, "romp"), exist_ok=True)
open(os.path.join(_XDG, "romp", "session-hosts"), "w").write("off\n")
km = load_source("romp_kernel_held_mail", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-aaaaaaaa0919"      # a PRIVATE synthetic sid for this module's notice rows (repo rule, 2026-08-24)


class _Root:
    """A hermetic state root the kernel is rebound to for one test, with no live sessions; close() puts everything back.
    Every memo keyed on a state path is dropped on both sides so no other module's parse is served here."""

    def __init__(self):
        self.td = tempfile.TemporaryDirectory()
        self.state = Path(self.td.name) / "state"
        self.orig_state, self.orig_names = km.jd.STATE, km.NAMES
        km.jd._rebind_state(self.state)
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / "session-hosts").write_text("off\n")
        km.NAMES = km.jd.NAMES
        self.saved = (km._live_map, km.Sessions.live, km._mark_views_dirty, km._push_soon, km._bus_quarantine_act)
        km._live_map = lambda: {}
        km.Sessions.live = staticmethod(lambda: {})
        self.dirty = []
        km._mark_views_dirty = lambda: self.dirty.append(1)
        km._push_soon = lambda: None
        self._reset_memos()

    @staticmethod
    def _reset_memos():
        km._NOTICE_MEMO.clear()
        km._CLEARED_MEMO["slot"] = None

    def close(self):
        (km._live_map, km.Sessions.live, km._mark_views_dirty, km._push_soon, km._bus_quarantine_act) = self.saved
        km.jd._rebind_state(self.orig_state)
        km.NAMES = self.orig_names
        self._reset_memos()
        self.td.cleanup()

    @property
    def qdir(self):
        return self.state / "postal" / "quarantine"

    def write_hold(self, mid, **extra):
        """One held record the bus's _quarantine_put shape, under <mid>.json."""
        self.qdir.mkdir(parents=True, exist_ok=True)
        rec = {"mid": mid, "to": "web", "toId": SID, "frm": "api", "frmId": "id-api", "body": "ship the parser fix",
               "kind": "coordinate", "origin": "TESTHOST", "at": 1000}
        rec.update(extra)
        p = self.qdir / (mid + ".json")
        p.write_text(json.dumps(rec))
        return p

    def write_notice_rows(self, rows, sid=SID):
        d = km._notice_dir()
        d.mkdir(parents=True, exist_ok=True)
        with open(km._notice_path(sid), "a") as f:
            for r in rows:
                f.write((r if isinstance(r, str) else json.dumps(r)) + "\n")


def _client(sent):
    return {"app": "feed", "wid": "w1", "alive": True, "send": lambda raw: sent.append(json.loads(raw))}


def _asks(feed, prefix):
    return [a for a in feed["asks"] if str(a["itemId"]).startswith(prefix)]


class ClearAllLeavesHolds(unittest.TestCase):
    """F1: the feed footer's Clear-all posts {type: "clearAll"} with no filter; the kernel builds the feed and hands
    _clear_all EVERY ask id, a held message's included. The reader used to honour the cleared ledger for a hold, so one
    click hid every held message server-side, and the badge with it, while the files sat undelivered (the manager's
    reproduction, 2026-09-19: eight cards to none, eight files still held). The rule, not a list: a hold is decided,
    never dismissed, so _quarantine_cards reads no ledger, and every Clear door is covered without being named. Driven
    through the real handler (Handler._dispatch_ws), as the sibling trust tests drive the decision."""

    def setUp(self):
        self.r = _Root()
        self.sent = []
        self.client = _client(self.sent)
        self.now = int(time.time())
        self.hold = self.r.write_hold("qc-hold-1")
        # the ORDINARY card beside it: a producer's notice card asking for the user (goal-less, rides the ledger)
        self.r.write_notice_rows([{"op": "post", "key": "figure", "rev": 1, "t": self.now - 10, "at": self.now - 10,
                                   "title": "The accuracy figure is ready", "body": "", "producer": "figure",
                                   "needsYou": True}])

    def tearDown(self):
        self.r.close()

    def _feed(self):
        return km.build_feed(self.now)

    def test_clear_all_clears_the_ordinary_card_and_leaves_the_hold(self):
        before = self._feed()
        self.assertEqual(len(_asks(before, "quarantine:")), 1, "the hold cards before the click")
        self.assertEqual(len(_asks(before, "notice:")), 1, "the ordinary card cards before the click")
        self.assertEqual(km._needs_you_count(before), 2)

        km.Handler._dispatch_ws(None, {"type": "clearAll"}, self.client)

        after = self._feed()
        self.assertEqual(_asks(after, "notice:"), [], "the ordinary card is cleared")
        held = _asks(after, "quarantine:")
        self.assertEqual([c["itemId"] for c in held], ["quarantine:qc-hold-1"], "the hold's card still stands")
        self.assertEqual(held[0]["blocked"]["state"], "quarantine")
        self.assertEqual(km._needs_you_count(after), 1, "the badge still counts the decision")
        self.assertTrue(self.hold.exists(), "the held file is untouched: nothing was delivered or dropped")
        self.assertIn("quarantine:qc-hold-1", km._cleared_ids(),
                      "the door still wrote the id (it is not filtered there); the reader makes the row inert")
        self.assertEqual([m for m in self.sent if m.get("type") == "err"], [], "no refusal: the clear landed")

    def test_a_later_undo_of_that_clear_does_not_double_the_hold(self):
        km.Handler._dispatch_ws(None, {"type": "clearAll"}, self.client)
        mid = self._feed()
        self.assertEqual(_asks(mid, "notice:"), [])
        self.assertEqual(len(_asks(mid, "quarantine:")), 1, "the hold stands through the clear (never hidden)")
        km.Handler._dispatch_ws(None, {"type": "undoClear"}, self.client)
        feed = self._feed()
        self.assertEqual(len(_asks(feed, "notice:")), 1, "Undo restores the ordinary card")
        self.assertEqual([c["itemId"] for c in _asks(feed, "quarantine:")], ["quarantine:qc-hold-1"],
                         "the hold, never hidden, is not restored a second time")
        self.assertEqual(km._needs_you_count(feed), 2)
        self.assertEqual([m for m in self.sent if m.get("type") == "undoClearResult"], [], "no undo refusal")

    def test_the_hold_still_leaves_the_board_when_it_is_decided(self):
        # the existing path: the pane's Approve or Deny reaches the bus, which removes the held file; the next build
        # drops the card because the file is gone, the event the card is keyed on
        km.Handler._dispatch_ws(None, {"type": "clearAll"}, self.client)
        self.assertEqual(len(_asks(self._feed(), "quarantine:")), 1, "cleared-all, still standing")

        def _act(body):
            self.assertEqual(body.get("mid"), "qc-hold-1")
            self.hold.unlink()
            return True, ""
        km._bus_quarantine_act = _act
        km.Handler._dispatch_ws(None, {"type": "quarantineDecision", "mid": "qc-hold-1", "action": "approve",
                                       "sid": SID}, self.client)
        self.assertEqual([m for m in self.sent if m.get("type") == "quarantineRefused"], [])
        self.assertEqual(km._quarantine_cards(self.now), [], "decided: the file is gone, so the card is")
        self.assertEqual(_asks(self._feed(), "quarantine:"), [])


if __name__ == "__main__":
    unittest.main()
