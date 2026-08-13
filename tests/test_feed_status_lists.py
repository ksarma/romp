"""The feed's per-session status partition is TOTAL — a KNOWN state never renders as nothing.

Sessions whose kernel-recorded state was `waiting` drew NO pip on the dashboard, while a same-state
session that happened to be awaiting background work drew a straw one — so a blank pip was
indistinguishable from a rendering hole (the user 2026-08-09). build_feed now emits `ready` (alive and
quiet) and `stateUnknown` (listed while its live state could not be read) beside the existing
`working`/`awaiting` name lists, so every listed session lands in exactly ONE of the four and the client
can render each explicitly; a bare name is reserved for payloads that predate the lists (an old kernel).
"""
import json
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()   # hermetic BEFORE any romp code loads
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel", os.path.join(BIN, "romp-kernel")).load_module()

SID_WORKING = "11111111-2222-3333-4444-555555555551"
SID_AWAITING = "11111111-2222-3333-4444-555555555552"
SID_QUIET = "11111111-2222-3333-4444-555555555553"
SID_NO_ROW = "11111111-2222-3333-4444-555555555554"
SID_HIDDEN = "11111111-2222-3333-4444-555555555555"


def _alive(*pairs):
    return [{"sid": sid, "name": name} for sid, name in pairs]


class FeedStatusPartition(unittest.TestCase):
    """_feed_status_names completes the partition build_feed's card pass began."""

    def setUp(self):
        # An isolated STATE dir so _session_flag never reads (or, worse, a stray future edit never
        # writes) the live machine's session-flags.json. jd.STATE is read at CALL time, so swapping
        # the attribute is enough; restored in tearDown.
        self._tmp = tempfile.TemporaryDirectory()
        self._old_state = km.jd.STATE
        km.jd.STATE = Path(self._tmp.name)

    def tearDown(self):
        km.jd.STATE = self._old_state
        self._tmp.cleanup()

    def test_every_listed_session_lands_in_exactly_one_of_the_four_lists(self):
        alive = _alive((SID_WORKING, "web"), (SID_AWAITING, "api"),
                       (SID_QUIET, "tests"), (SID_NO_ROW, "docs"))
        # the merged live map has a row for all but "docs" (its state could not be read)
        tmux = {SID_WORKING: {"state": "working"}, SID_AWAITING: {"state": "waiting"},
                SID_QUIET: {"state": "waiting"}}
        ready, unknown = km._feed_status_names(alive, tmux, ["web"], ["api"])
        self.assertEqual(ready, ["tests"], "alive + quiet -> ready, no longer encoded as nothing")
        self.assertEqual(unknown, ["docs"], "listed but unreadable -> explicit stateUnknown, fail loudly")
        # the partition is total and disjoint: 4 sessions, one list each
        names = ["web"] + ["api"] + ready + unknown
        self.assertEqual(sorted(names), ["api", "docs", "tests", "web"])

    def test_the_reported_shape_two_waiting_sessions_only_the_awaiting_one_had_a_pip(self):
        # The verified evidence (2026-08-09): two sessions with the IDENTICAL latest state record
        # (`waiting`); the one awaiting background work drew a straw pip, the plain-quiet one drew
        # NOTHING. The quiet one now lands in `ready`, so the renderer shows its actual known state.
        alive = _alive((SID_AWAITING, "api"), (SID_QUIET, "tests"))
        tmux = {SID_AWAITING: {"state": "waiting"}, SID_QUIET: {"state": "waiting"}}
        ready, unknown = km._feed_status_names(alive, tmux, [], ["api"])
        self.assertEqual((ready, unknown), (["tests"], []))

    def test_hidden_from_feed_sessions_are_in_no_list_matching_their_absent_cards(self):
        (Path(self._tmp.name) / "session-flags.json").write_text(
            json.dumps({SID_HIDDEN: {"hideFromFeed": True}}))
        alive = _alive((SID_HIDDEN, "web"), (SID_QUIET, "tests"))
        tmux = {SID_HIDDEN: {"state": "waiting"}, SID_QUIET: {"state": "waiting"}}
        ready, unknown = km._feed_status_names(alive, tmux, [], [])
        self.assertEqual((ready, unknown), (["tests"], []),
                         "a muted session shows no cards, so it must carry no status entry either")


class BuildFeedEmitsThePartition(unittest.TestCase):
    def test_build_feed_payload_carries_ready_and_state_unknown(self):
        import inspect
        src = inspect.getsource(km.build_feed)
        self.assertIn('_feed_status_names(alive, tmux, working, awaiting)', src)
        self.assertIn('"ready": ready, "stateUnknown": state_unknown', src)


if __name__ == "__main__":
    unittest.main()
