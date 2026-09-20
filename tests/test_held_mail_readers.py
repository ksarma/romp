#!/usr/bin/env python3
"""The held-mail (quarantine) card road's readers, kernel side (2026-09-19). One rule runs through every case here: a
reader that cannot parse must not report ABSENT and must not take down callers that had nothing to do with the bad row.
Skip the row, name the session and the key in the log, keep the board.

The cases: the footer's Clear-all reaches _clear_all with every ask id, a hold's included, and the hold's card must stand
(a hold is decided by Approve or Deny, never dismissed); one type-wrong value in one notice row must not raise out of
every feed build; the quarantine directory reader must name a directory it cannot list, move a record it cannot parse
aside once with the other holds still built, leave a record it cannot READ in place for the next build, and name a
record with no message id.

Synthetic only: a hermetic temp state root, placeholder session ids, invented hold and notice text, TESTHOST. Every root
this module mints writes `off` into <root>/session-hosts (repo rule, 2026-09-11) and no goals are minted."""
import contextlib
import inspect
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


def _qcards(now):
    """The reader at HEAD takes (now); the fails-before run over the base commit meets the older (now, cleared) and gets
    the empty set there, so that run fails on the reader's defects and not on the signature."""
    if len(inspect.signature(km._quarantine_cards).parameters) == 1:
        return km._quarantine_cards(now)
    return km._quarantine_cards(now, set())


class ClearAllLeavesHolds(unittest.TestCase):
    """F1: the feed footer's Clear-all posts {type: "clearAll"} with no filter; the kernel builds the feed and hands
    _clear_all EVERY ask id, a held message's included. The reader used to honour the cleared ledger for a hold, so one
    click hid every held message server-side, and the badge with it, while the files sat undelivered (the manager's
    reproduction, 2026-09-19: eight cards to none, eight files still held). The rule, not a list: a hold is decided,
    never dismissed, so _quarantine_cards reads no ledger, and every Clear door is covered without being named. Driven
    through the real handler (Handler._dispatch_ws), as the sibling trust tests drive the decision.

    Fails before: over a git archive of bc88256e8 (kernel/, bin/, postal/, cli/ and tests/ with the conftest) with this
    module copied in, all three cases fail on the defect itself, each at the assertion that the hold's card stands after
    the click (the first with 'Lists differ: [] != [quarantine:qc-hold-1]', the other two with '0 != 1'); _qcards meets
    the reader's older (now, cleared) signature there, so none fails on the signature. Green here."""

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
        self.assertNotIn("quarantine:qc-hold-1", km._cleared_ids(),
                         "the ledger takes no hold id: _clear_all declines it at the write, and the reader would make the row inert anyway")
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
        self.assertEqual(_qcards(self.now), [], "decided: the file is gone, so the card is")
        self.assertEqual(_asks(self._feed(), "quarantine:"), [])


class NoticeRowTypeFault(unittest.TestCase):
    """F2: every consumer of a notice row coerces rev, t and expiresAt with int(), so ONE type-wrong value in ONE row of ONE
    session's notices/<sid>.jsonl raised ValueError out of every feed build (the manager's reproduction, 2026-09-19: the
    push cycle and GET /feed.json answering 500 alike, the whole board gone over a row no other session had anything to do
    with). The rule: skip the row, say once which session, key and field, and the value's type, never its text; keep the
    board with the good rows' cards on it."""

    def setUp(self):
        self.r = _Root()
        self.now = int(time.time())
        getattr(km, "_NOTICE_BAD_ROW_SAID", {}).clear()

    def tearDown(self):
        self.r.close()

    def _good(self, key="figure", rev=1):
        return {"op": "post", "key": key, "rev": rev, "t": self.now - 10, "at": self.now - 10,
                "title": "The accuracy figure is ready", "body": "", "producer": "figure", "needsYou": True}

    def _build(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            feed = km.build_feed(self.now)
        return feed, err.getvalue()

    def test_one_type_wrong_row_skips_and_the_good_row_keeps_its_card(self):
        self.r.write_notice_rows([self._good(), dict(self._good(key="sweep"), rev="abc-not-a-rev")])
        feed, log = self._build()                    # no exception: the build survives the row
        self.assertEqual([c["itemId"] for c in _asks(feed, "notice:")], ["notice:%s:figure:1" % SID],
                         "the good row's card is on the board; the bad row's is not")
        self.assertEqual(log.count("needs an integer"), 1, log)
        self.assertIn(SID, log, "the log names the session")
        self.assertIn("key sweep", log, "and the key")
        self.assertIn("rev", log, "and the field")
        self.assertIn("carries a str", log, "and the value's type")
        self.assertNotIn("abc-not-a-rev", log, "never the value's text")

    def test_a_bad_t_and_a_bad_expiresAt_skip_the_same_way(self):
        self.r.write_notice_rows([self._good(), dict(self._good(key="noon"), t="noon"),
                                  dict(self._good(key="later"), expiresAt=[1])])
        feed, log = self._build()
        self.assertEqual([c["itemId"] for c in _asks(feed, "notice:")], ["notice:%s:figure:1" % SID])
        self.assertIn("key noon carries a str where t needs an integer", log)
        self.assertIn("key later carries a list where expiresAt needs an integer", log)

    def test_the_row_is_said_once_per_episode_not_per_parse(self):
        self.r.write_notice_rows([self._good(), dict(self._good(key="sweep"), rev="abc-not-a-rev")])
        _, log1 = self._build()
        self.assertEqual(log1.count("needs an integer"), 1)
        self.r.write_notice_rows([self._good(key="other")])       # the file moved: a fresh parse meets the same row
        feed, log2 = self._build()
        self.assertEqual(len(_asks(feed, "notice:")), 2, "the appended good row's card joins the board")
        self.assertEqual(log2, "", "the same fact is not said again")
        # the episode ends when a parse meets no bad row (the sweep archived it, or the file was rewritten)...
        km._notice_path(SID).write_text(json.dumps(self._good()) + "\n")
        self._build()
        self.assertNotIn(SID, km._NOTICE_BAD_ROW_SAID)
        # ...so the next such row is a new episode and is said again
        self.r.write_notice_rows([dict(self._good(key="sweep"), rev="abc-not-a-rev")])
        _, log3 = self._build()
        self.assertEqual(log3.count("needs an integer"), 1)

    def test_the_writer_side_reader_skips_the_row_too(self):
        # post_notice counts a key's revisions over _notice_rows_unlocked; a type-wrong row there raised for the writer.
        # The writer's reader answers (rows, error) since the manager's round 1 (regression-2: a file it could not read
        # was folded to [], a false absence for expire_notice and a blind revision for post_notice); a clean read is ""
        self.r.write_notice_rows([self._good(), dict(self._good(key="sweep"), rev="abc-not-a-rev")])
        with contextlib.redirect_stderr(io.StringIO()):
            rows, err = km._notice_rows_unlocked(SID)
        self.assertEqual(err, "", "a file that read is no fault")
        self.assertEqual([r["key"] for r in rows], ["figure"])


def _forget_said_once():
    """What a case of HeldMailReader must not inherit from an earlier one: the bell ring and every said-once registry the
    held-mail reader keys on a path under a root, a file it could not read (_HOLD_UNREADABLE_SAID), a record moved aside
    that it says again once its row has left the ring (_HOLD_ASIDE_SAID, the manager's round 1 follow-on, extra6-4) and a
    store fault (_state_fault_seen). Called on both sides of every case, so the class leaves nothing to the next module in
    the process either. getattr with a default: the fails-before runs of this module meet kernels that keep neither hold
    registry."""
    getattr(km, "_HOLD_UNREADABLE_SAID", set()).clear()
    getattr(km, "_HOLD_ASIDE_SAID", {}).clear()
    km._state_fault_seen.clear()
    with km._SYNC_LOCK:
        del km._SYNC_NOTICES[:]


class HeldMailReader(unittest.TestCase):
    """F3, F4 and F5, one fix with three faces: the quarantine directory reader. F3: a fault listing the directory returned
    [] with nothing said, so an unreadable directory drew a clean board with every hold invisible (and on this Python the
    glob swallowed the PermissionError itself, so the reader's except never even ran). F4: the try wrapped json.loads
    alone, so a hold file whose JSON is not an object raised AttributeError, and a non-integer `at` ValueError, out of
    _quarantine_cards and build_feed. F5: a torn file, or a record with no mid, was skipped silently forever with the file
    left in place. The port of the postal bus's _list_json_records, precondition included: a record that reads but
    cannot be parsed is moved aside ONCE to <name>.corrupt-<utc stamp> with a line naming the file, the other holds stay
    on the board, a file rewritten under the read is left for the next build, and a directory fault names itself (one
    stderr line and one bell row under the refused kind, once per episode) instead of returning an empty board. A record
    whose bytes could not be READ is not this class's: since the manager's round 1 (correctness-2) it is skipped and left
    in place for the next build, never renamed, because a rename is terminal and the bytes may be a good message
    (tests/test_held_mail_manager_r1.py ReadFaultLeavesTheFileInPlace)."""

    def setUp(self):
        self.r = _Root()
        self.now = int(time.time())
        self._modes = []
        _forget_said_once()

    def tearDown(self):
        for p, mode in self._modes:                  # restore every mode this test changed, so the root can be removed
            try:
                os.chmod(p, mode)
            except OSError:
                pass
        _forget_said_once()
        self.r.close()

    def _chmod(self, p, mode):
        self._modes.append((p, 0o700))
        os.chmod(p, mode)

    def _cards(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            cards = _qcards(self.now)
        return cards, err.getvalue()

    def _refused(self):
        return [r for r in km._sync_notice_rows() if r["kind"] == "refused"]

    def _asides(self, stem):
        return sorted(p.name for p in self.r.qdir.iterdir() if p.name.startswith(stem + ".json.corrupt-"))

    def _skip_as_root(self):
        if os.geteuid() == 0:
            self.skipTest("SKIPPED LOUDLY: running as root, so a mode of 000 does not refuse the read this test injects")

    def test_an_unlistable_directory_is_a_named_fault_not_a_clean_board(self):
        self._skip_as_root()
        self.r.write_hold("qc-1")
        self._chmod(self.r.qdir, 0)
        cards, log = self._cards()
        self.assertEqual(cards, [], "nothing could be read...")
        rows = self._refused()
        self.assertEqual(len(rows), 1, "...and the fault is on the board's bell, under the refused kind")
        self.assertIn("postal/quarantine", rows[0]["text"], "it names the directory")
        self.assertIn("could not be listed", rows[0]["text"])
        self.assertIn("Permission denied", rows[0]["text"])
        self.assertIn("none was delivered or dropped", rows[0]["text"])
        self.assertEqual(log.count("could not be listed"), 1, "and stderr carries the same line")
        cards, log = self._cards()                   # the next build meets the same fault: quiet, one episode
        self.assertEqual((cards, log, len(self._refused())), ([], "", 1))
        self._chmod(self.r.qdir, 0o700)
        cards, log = self._cards()                   # readable again: the holds are back and the episode ends
        self.assertEqual([c["itemId"] for c in cards], ["quarantine:qc-1"])
        self.assertNotIn(str(self.r.qdir), km._state_fault_seen)
        self._chmod(self.r.qdir, 0)
        cards, log = self._cards()                   # a new fault is a new episode: said again
        self.assertEqual(len(self._refused()), 2)
        self.assertEqual(log.count("could not be listed"), 1)

    def test_a_missing_directory_is_nothing_held_and_no_fault(self):
        cards, log = self._cards()
        self.assertEqual((cards, log, self._refused()), ([], "", []))

    def test_a_non_object_hold_moves_aside_and_the_other_holds_stand(self):
        self.r.write_hold("qc-good")
        (self.r.qdir / "qc-list.json").write_text(json.dumps([1, 2, 3]))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            feed = km.build_feed(self.now)           # the whole build survives it (it raised AttributeError before)
        self.assertEqual([c["itemId"] for c in _asks(feed, "quarantine:")], ["quarantine:qc-good"])
        self.assertFalse((self.r.qdir / "qc-list.json").exists(), "moved aside...")
        self.assertEqual(len(self._asides("qc-list")), 1, "...to <name>.json.corrupt-<stamp> beside the others")
        self.assertTrue((self.r.qdir / "qc-good.json").exists(), "the readable hold is untouched")
        log = err.getvalue()
        self.assertIn("qc-list.json could not be parsed (not a JSON object)", log)
        self.assertIn("moved aside to qc-list.json.corrupt-", log)
        rows = self._refused()
        self.assertEqual(len(rows), 1, "and the bell carries it")
        self.assertIn("qc-list.json", rows[0]["text"])

    def test_a_non_integer_at_moves_aside_naming_the_type_not_the_text(self):
        self.r.write_hold("qc-good")
        self.r.write_hold("qc-when", at="yesterday-at-noon")
        cards, log = self._cards()
        self.assertEqual([c["itemId"] for c in cards], ["quarantine:qc-good"])
        self.assertEqual(len(self._asides("qc-when")), 1)
        self.assertIn("qc-when.json could not be parsed (`at` is a str, not an integer)", log)
        self.assertNotIn("yesterday-at-noon", log)

    def test_a_torn_file_moves_aside_once_and_is_not_read_again(self):
        self.r.write_hold("qc-good")
        (self.r.qdir / "qc-torn.json").write_text('{"mid": "qc-torn", "to": "web", "at": 10')
        cards, log = self._cards()
        self.assertEqual([c["itemId"] for c in cards], ["quarantine:qc-good"])
        self.assertEqual(len(self._asides("qc-torn")), 1)
        self.assertIn("qc-torn.json could not be parsed", log)
        cards, log = self._cards()                   # the next build: the listing never meets the file again
        self.assertEqual([c["itemId"] for c in cards], ["quarantine:qc-good"])
        self.assertEqual((log, len(self._asides("qc-torn")), len(self._refused())), ("", 1, 1))

    def test_a_record_with_no_mid_is_named(self):
        self.r.write_hold("qc-good")
        (self.r.qdir / "qc-nomid.json").write_text(json.dumps({"to": "web", "toId": SID, "frm": "api", "at": 1000}))
        (self.r.qdir / "qc-intmid.json").write_text(json.dumps({"mid": 7, "to": "web", "at": 1000}))
        cards, log = self._cards()
        self.assertEqual([c["itemId"] for c in cards], ["quarantine:qc-good"])
        self.assertIn("qc-nomid.json could not be parsed (no message id)", log)
        self.assertIn("qc-intmid.json could not be parsed (no message id)", log, "a mid that is not text is no mid")
        self.assertEqual((len(self._asides("qc-nomid")), len(self._asides("qc-intmid"))), (1, 1))

    def test_a_file_rewritten_under_the_read_is_left_for_the_next_build(self):
        # the precondition: the stat taken before the read must still match when the parse fails, else a writer's
        # atomic publish raced the read and the healthy new bytes must not be moved aside
        self.r.write_hold("qc-good")
        p = self.r.qdir / "qc-race.json"
        p.write_text('{"mid": "qc-race", "to": "web", "at": 10')
        real_loads = km.json.loads

        def racing_loads(text, *a, **kw):
            if text.startswith('{"mid": "qc-race"') and not text.endswith("}"):
                self.r.write_hold("qc-race", body="the second publish, whole")   # a different size: the stat moves
            return real_loads(text, *a, **kw)
        km.json.loads = racing_loads
        try:
            cards, log = self._cards()
        finally:
            km.json.loads = real_loads
        self.assertEqual([c["itemId"] for c in cards], ["quarantine:qc-good"], "the torn read carded nothing...")
        self.assertTrue(p.exists(), "...and the rewritten file stands where it is")
        self.assertEqual((self._asides("qc-race"), log, self._refused()), ([], "", []))
        cards, log = self._cards()                   # the next build reads the new bytes
        self.assertEqual([c["itemId"] for c in cards], ["quarantine:qc-good", "quarantine:qc-race"])

    def test_a_file_that_cannot_be_moved_aside_is_said_once_and_left(self):
        self._skip_as_root()
        self.r.write_hold("qc-good")
        (self.r.qdir / "qc-torn.json").write_text('{"mid": "qc-torn", "to": "web", "at": 10')
        self._chmod(self.r.qdir, 0o500)              # listable and readable, but no rename inside it
        cards, log = self._cards()
        self.assertEqual([c["itemId"] for c in cards], ["quarantine:qc-good"], "the readable hold stands")
        self.assertTrue((self.r.qdir / "qc-torn.json").exists(), "the file could not be moved: it stays")
        self.assertIn("qc-torn.json could not be read or parsed and could not be moved aside", log)
        self.assertIn("Permission denied", log)
        self.assertEqual(log.count("qc-torn.json"), 1)
        cards, log = self._cards()                   # said once per (file, errno), not per build
        self.assertEqual((log, [c["itemId"] for c in cards]), ("", ["quarantine:qc-good"]))

    def test_the_directory_is_listed_never_globbed(self):
        src = inspect.getsource(km._held_records)
        self.assertIn("os.listdir(qdir)", src, "the listing raises on an unreadable directory")
        self.assertNotIn(".glob(", src, "Path.glob swallows a PermissionError on this Python and yields nothing")

    def test_the_next_case_inherits_no_aside_episode(self):
        """The aside registry the manager's round 1 follow-on added (extra6-4; _HOLD_ASIDE_SAID, an aside's path to the seq
        of the bell row that carries it) is dropped between cases with the read-fault registry and the ring: without that,
        a case of this class that moved a hold aside left its entry, keyed on a root that no longer existed, to every later
        case in the process. Fails under a mutation that drops the clear from _forget_said_once over the tree (the root's
        key is still listed at the assertion after the call); over the 0a589d1e4 archive the kernel keeps no such
        registry, the premise. Green here."""
        self.r.write_hold("qc-good")
        (self.r.qdir / "qc-list.json").write_text(json.dumps([1, 2, 3]))
        cards, _ = self._cards()
        self.assertEqual([c["itemId"] for c in cards], ["quarantine:qc-good"])
        qdir = str(self.r.qdir)
        self.assertEqual(len([k for k in km._HOLD_ASIDE_SAID if k.startswith(qdir)]), 1, "the scene: the aside's episode is open")
        self.assertEqual(len(self._refused()), 1)
        _forget_said_once()
        self.assertEqual([k for k in km._HOLD_ASIDE_SAID if k.startswith(qdir)], [], "what the next case's setUp forgets")
        self.assertEqual(self._refused(), [], "and the ring with it")


if __name__ == "__main__":
    unittest.main()
