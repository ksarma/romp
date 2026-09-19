#!/usr/bin/env python3
"""The held-mail readers bundle, review round 1: the kernel-side fixes the round found, each pinned by a case that fails
over a git archive of the build's consolidation commit and passes here. The rule is the bundle's: a reader that cannot
parse must not report absent and must not take down callers that had nothing to do with the bad row; skip the row, name
the session and the key in the log, keep the board.

The cases: a notice row whose key is not text (a list, an object, a number) skips like a type-wrong integer field
instead of raising TypeError out of the projection; a float infinity in rev, t, expiresAt or a hold's `at` (json's
1e400, Infinity) skips or moves aside instead of raising OverflowError past the (TypeError, ValueError) guards; the
cleared ledger never takes a hold's id, whichever door sends it, so a hold-only Clear-all lights no Undo that restores
nothing; a held file that cannot be read and cannot be moved aside files a bell row, once per episode, the episode
ending when a listing no longer has to skip it; the bell's row for a moved-aside hold fits SYNC_NOTICE_FIT for a
relayed message's sixty-character mid; and the notice sweep archives the lines the parse left out instead of deleting
them when it rewrites the live file.

Synthetic only: a hermetic temp state root, a placeholder session id private to this module (the goal-store rule,
2026-08-24), invented hold and notice text, TESTHOST. Every root this module mints writes `off` into
<root>/session-hosts (repo rule, 2026-09-11) and no goals are minted."""
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
km = load_source("romp_kernel_held_mail_guards", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-bbbbbbbb0919"      # this module's PRIVATE synthetic sid for its notice rows
HEX32 = "0123456789abcdef0123456789abcdef"
RELAYED_MID = "px-1758300000.12345_%s.TESTHOST" % HEX32   # the bus's mid shape for a relayed message: 61 characters
NOTICE_ID = "notice:%s:figure:1" % SID


class _Root:
    """A hermetic state root the kernel is rebound to for one test, with no live sessions; close() puts everything back.
    Every memo and every said-once registry keyed on a state path is dropped on both sides."""

    def __init__(self):
        self.td = tempfile.TemporaryDirectory()
        self.state = Path(self.td.name) / "state"
        self.orig_state, self.orig_names = km.jd.STATE, km.NAMES
        km.jd._rebind_state(self.state)
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / "session-hosts").write_text("off\n")
        km.NAMES = km.jd.NAMES
        self.saved = (km._live_map, km.Sessions.live, km._mark_views_dirty, km._push_soon)
        km._live_map = lambda: {}
        km.Sessions.live = staticmethod(lambda: {})
        km._mark_views_dirty = lambda: None
        km._push_soon = lambda: None
        self.modes = []
        self._reset()

    @staticmethod
    def _reset():
        km._NOTICE_MEMO.clear()
        km._CLEARED_MEMO["slot"] = None
        getattr(km, "_NOTICE_BAD_ROW_SAID", {}).clear()
        getattr(km, "_NOTICE_SWEPT", {}).clear()
        getattr(km, "_HOLD_UNREADABLE_SAID", set()).clear()
        km._state_fault_seen.clear()
        with km._SYNC_LOCK:
            del km._SYNC_NOTICES[:]

    def close(self):
        for p in self.modes:                          # a mode a test lowered is raised before the root is removed
            try:
                os.chmod(p, 0o700)
            except OSError:
                pass
        (km._live_map, km.Sessions.live, km._mark_views_dirty, km._push_soon) = self.saved
        km.jd._rebind_state(self.orig_state)
        km.NAMES = self.orig_names
        self._reset()
        self.td.cleanup()

    def chmod(self, p, mode):
        self.modes.append(p)
        os.chmod(p, mode)

    @property
    def qdir(self):
        return self.state / "postal" / "quarantine"

    def write_hold(self, mid, at="1000"):
        """One held record in the bus's _quarantine_put shape under <mid>.json; `at` is written as raw JSON text so a
        literal json.dumps cannot emit (1e400, Infinity) reaches json.loads as written."""
        self.qdir.mkdir(parents=True, exist_ok=True)
        text = ('{"mid": "%s", "to": "web", "toId": "%s", "frm": "api", "frmId": "id-api", "body": "ship the parser fix", '
                '"kind": "coordinate", "origin": "TESTHOST", "at": %s}' % (mid, SID, at))
        p = self.qdir / (mid + ".json")
        p.write_text(text)
        return p

    def write_torn_hold(self, mid):
        self.qdir.mkdir(parents=True, exist_ok=True)
        p = self.qdir / (mid + ".json")
        p.write_text('{"mid": "%s", "to": "web", "at": 10' % mid)
        return p

    def write_notice_rows(self, rows, sid=SID):
        """Rows as dicts, or as raw text for a literal json.dumps cannot emit."""
        d = km._notice_dir()
        d.mkdir(parents=True, exist_ok=True)
        with open(km._notice_path(sid), "a") as f:
            for r in rows:
                f.write((r if isinstance(r, str) else json.dumps(r)) + "\n")

    def ledger_rows(self):
        p = self.state / "cleared.jsonl"
        if not p.exists():
            return []
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def _good(now, key="figure", rev=1):
    return {"op": "post", "key": key, "rev": rev, "t": now - 10, "at": now - 10, "title": "The accuracy figure is ready",
            "body": "", "producer": "figure", "needsYou": True}


def _raw(now, key, field, literal):
    """A good row with `field` written as the raw JSON `literal`."""
    o = _good(now, key=key)
    o.pop(field, None)
    return json.dumps(o)[:-1] + ', "%s": %s}' % (field, literal)


def _asks(feed, prefix):
    return [a for a in feed["asks"] if str(a["itemId"]).startswith(prefix)]


def _refused():
    return [r["text"] for r in km._sync_notice_rows(limit=40) if r["kind"] == "refused"]


def _client(sent):
    return {"app": "feed", "wid": "w1", "alive": True, "send": lambda raw: sent.append(json.loads(raw))}


def _skip_as_root(case):
    if os.geteuid() == 0:
        case.skipTest("root ignores mode bits")


class _Case(unittest.TestCase):
    def setUp(self):
        self.r = _Root()
        self.now = int(time.time())

    def tearDown(self):
        self.r.close()

    def _feed(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            feed = km.build_feed(self.now)
        return feed, err.getvalue()

    def _cards(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            cards = km._quarantine_cards(self.now)
        return [c["itemId"] for c in cards], err.getvalue()

    def _asides(self, mid):
        return sorted(p.name for p in self.r.qdir.iterdir() if p.name.startswith(mid + ".json.corrupt-"))


class NoticeKeyNotText(_Case):
    """A notice row's key is hashed by every reader (a dict key in the projection, a set member for expire and acted rows,
    the sweep's newest map) and sorted on, so a key that is a list, an object or a number raised TypeError out of every
    feed build and out of the sweep, the F2 shape the int-field check left open. The parse now treats a key that is not
    text as a bad field: the row skips, is said once naming the type (a key that is not text has no name to give), and
    the board stands."""

    def test_a_key_that_is_not_text_skips_the_row_and_keeps_the_board(self):
        self.r.write_notice_rows([_good(self.now),
                                  dict(_good(self.now), key=["secret-key-text", "b"]),
                                  dict(_good(self.now), key={"secret-key-text": 1}),
                                  dict(_good(self.now), key=7),
                                  {"op": "expire", "key": ["secret-key-text"], "rev": 1, "t": self.now}])
        feed, log = self._feed()
        self.assertEqual([c["itemId"] for c in _asks(feed, "notice:")], [NOTICE_ID], "the good row's card stands alone")
        self.assertIn("a row carries a key of type list where text is needed", log)
        self.assertIn("a row carries a key of type dict where text is needed", log)
        self.assertIn("a row carries a key of type int where text is needed", log)
        self.assertEqual(log.count("where text is needed"), 3, "one line per fact: the two list keys are one fact")
        self.assertIn(SID, log, "the log names the session")
        self.assertNotIn("secret-key-text", log, "never the value's text")
        feed, log = self._feed()
        self.assertEqual(len(_asks(feed, "notice:")), 1)
        self.assertEqual(log, "", "the same facts are not said again")

    def test_the_writer_and_the_sweep_read_past_it_too(self):
        self.r.write_notice_rows([_good(self.now), dict(_good(self.now), key=[1])])
        with contextlib.redirect_stderr(io.StringIO()):
            rows = km._notice_rows_unlocked(SID)
            moved = km._compact_notices(self.now)
        self.assertEqual([r["key"] for r in rows], ["figure"])
        self.assertEqual(moved, 0)


class NonFiniteNumbers(_Case):
    """json.loads turns 1e400, Infinity and -Infinity into a float infinity, and int() refuses it with OverflowError, an
    ArithmeticError the (TypeError, ValueError) guards of _notice_row_bad_field and _held_records did not name: one such
    value in one notice row, or in a hold's `at`, still raised out of every feed build, the F2 and F4 shapes with one more
    literal. Both guards name it now: the row skips and is said, the hold is moved aside with the float reason."""

    def test_an_infinite_rev_t_or_expiresat_skips_the_row(self):
        self.r.write_notice_rows([_good(self.now),
                                  _raw(self.now, "sweep", "rev", "1e400"),
                                  _raw(self.now, "infy", "rev", "Infinity"),
                                  _raw(self.now, "noon", "t", "-Infinity"),
                                  _raw(self.now, "later", "expiresAt", "1e400"),
                                  _raw(self.now, "nan", "rev", "NaN")])
        feed, log = self._feed()
        self.assertEqual([c["itemId"] for c in _asks(feed, "notice:")], [NOTICE_ID])
        for key, field in (("sweep", "rev"), ("infy", "rev"), ("noon", "t"), ("later", "expiresAt"), ("nan", "rev")):
            self.assertIn("a row for key %s carries a float where %s needs an integer" % (key, field), log)
        with contextlib.redirect_stderr(io.StringIO()):
            rows = km._notice_rows_unlocked(SID)
        self.assertEqual([r["key"] for r in rows], ["figure"], "the writer's reader skips them too")

    def test_an_infinite_at_moves_the_hold_aside(self):
        self.r.write_hold("qc-good")
        self.r.write_hold("qc-inf", at="1e400")
        self.r.write_hold("qc-neg", at="-Infinity")
        self.r.write_hold("qc-word", at="Infinity")
        cards, log = self._cards()
        self.assertEqual(cards, ["quarantine:qc-good"], "the readable hold stands")
        for mid in ("qc-inf", "qc-neg", "qc-word"):
            self.assertEqual(len(self._asides(mid)), 1, mid)
            self.assertIn("%s.json could not be parsed (`at` is a float, not an integer)" % mid, log)
        feed, log = self._feed()
        self.assertEqual([c["itemId"] for c in _asks(feed, "quarantine:")], ["quarantine:qc-good"])
        self.assertEqual(log, "", "moved aside once: the next build meets no such file")


class HoldIdsNeverJournaled(_Case):
    """A hold is decided by Approve, Edit or Deny, never dismissed, and its card takes no ledger (F1). The ledger still
    took its id from every Clear door: the row was inert for the card but lit canUndoClear and formed an Undo batch that
    restored nothing (after a hold-only Clear-all the first Undo did nothing and the second brought back an earlier
    clear), and the id's pseudo-sid 'quarantine' read a goal store that is no session's. _clear_all declines the id at the
    one write every door reaches: no door is named, the reader's rule stands, and the ledger holds only what Undo can
    restore."""

    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = _client(self.sent)
        self.holds = [self.r.write_hold("qc-hold-1"), self.r.write_hold("qc-hold-2")]
        self.r.write_notice_rows([_good(self.now)])
        self.read_sids = []
        self.orig = {n: getattr(km.jd, n) for n in ("load_goals", "load_goals_or_fault", "load_goal_archive")}

        def _wrap(fn):
            def w(sid, *a, **kw):
                self.read_sids.append(str(sid))
                return fn(sid, *a, **kw)
            return w
        for n, f in self.orig.items():
            setattr(km.jd, n, _wrap(f))

    def tearDown(self):
        for n, f in self.orig.items():
            setattr(km.jd, n, f)
        super().tearDown()

    def _dispatch(self, msg):
        with contextlib.redirect_stderr(io.StringIO()):
            km.Handler._dispatch_ws(None, msg, self.client)

    def _ids(self, feed, prefix):
        return [c["itemId"] for c in _asks(feed, prefix)]

    def test_clear_all_journals_the_ordinary_card_alone(self):
        self._dispatch({"type": "clearAll"})
        rows = self.r.ledger_rows()
        self.assertEqual([(r["id"], r["op"]) for r in rows], [(NOTICE_ID, "clear")], "one row: the card that can be cleared")
        self.assertEqual([i for i in km._cleared_ids() if i.startswith("quarantine:")], [])
        self.assertNotIn("quarantine", self.read_sids, "no goal store is read for the pseudo-sid")
        feed, _ = self._feed()
        self.assertEqual(self._ids(feed, "notice:"), [])
        self.assertEqual(self._ids(feed, "quarantine:"), ["quarantine:qc-hold-1", "quarantine:qc-hold-2"])
        self.assertTrue(feed["canUndoClear"], "the ordinary card's clear is what Undo offers")
        self.assertEqual([m for m in self.sent if m.get("type") == "err"], [])
        self._dispatch({"type": "undoClear"})
        feed, _ = self._feed()
        self.assertEqual(self._ids(feed, "notice:"), [NOTICE_ID], "Undo restores the ordinary card")
        self.assertFalse(feed["canUndoClear"])
        self.assertEqual([r for r in self.r.ledger_rows() if str(r["id"]).startswith("quarantine:")], [],
                         "no hold row of either op, ever")
        self.assertTrue(all(p.exists() for p in self.holds), "the held files are untouched")

    def test_a_hold_only_clear_all_offers_no_undo(self):
        self._dispatch({"type": "askClear", "itemId": NOTICE_ID})      # an earlier, deliberate clear
        feed, _ = self._feed()
        self.assertEqual((self._ids(feed, "notice:"), feed["canUndoClear"]), ([], True))
        rows_before = self.r.ledger_rows()
        self._dispatch({"type": "clearAll"})                             # the board holds the two holds alone
        feed, _ = self._feed()
        self.assertEqual(self.r.ledger_rows(), rows_before, "nothing is journaled for a board of holds")
        self.assertEqual(len(self._ids(feed, "quarantine:")), 2, "the holds stand")
        self.assertEqual([m for m in self.sent if m.get("type") == "err"], [])
        self._dispatch({"type": "undoClear"})                            # the FIRST Undo restores the clear the user made
        feed, _ = self._feed()
        self.assertEqual(self._ids(feed, "notice:"), [NOTICE_ID], "Undo brings back the earlier clear at the first press")
        self.assertFalse(feed["canUndoClear"], "and nothing phantom is left to undo")

    def test_a_board_of_holds_alone_lights_no_undo(self):
        self._dispatch({"type": "askClear", "itemId": NOTICE_ID})
        self._dispatch({"type": "undoClear"})
        self.r.write_notice_rows([{"op": "expire", "key": "figure", "rev": 1, "t": self.now}])   # the ordinary card retires itself
        feed, _ = self._feed()
        self.assertEqual((self._ids(feed, "notice:"), len(self._ids(feed, "quarantine:")), feed["canUndoClear"]), ([], 2, False))
        self._dispatch({"type": "clearAll"})
        feed, _ = self._feed()
        self.assertFalse(feed["canUndoClear"], "Clear-all over holds alone offers no Undo: nothing moved")
        self.assertEqual(len(self._ids(feed, "quarantine:")), 2)

    def test_a_single_clear_of_a_hold_id_journals_nothing(self):
        self._dispatch({"type": "askClear", "itemId": "quarantine:qc-hold-1"})   # a stale or foreign client's gesture
        self._dispatch({"type": "askClearMany", "itemIds": ["quarantine:qc-hold-2"]})
        feed, _ = self._feed()
        self.assertEqual(self.r.ledger_rows(), [])
        self.assertFalse(feed["canUndoClear"])
        self.assertEqual(len(self._ids(feed, "quarantine:")), 2)
        self.assertEqual([m for m in self.sent if m.get("type") == "err"], [], "declined quietly: nothing to refuse")
        self.assertEqual(km._clear_all(["quarantine:qc-hold-1", ""]), {})


class UnreadableHoldRingsTheBell(_Case):
    """A held file the reader could not read AND could not move aside was said on stderr alone, once per kernel run,
    where the reader's two other faults (a moved-aside record, a directory that cannot be listed) file a refused bell
    row; a directory that lists but cannot be searched (mode 400) fails every stat, so every hold left the board behind
    a clean bell and two stderr lines, and the second build said nothing. The line files the bell row now, and its
    episode ends when a listing no longer has to skip the file, so a fault that returns is said again."""

    def test_a_file_that_cannot_be_moved_aside_rings_the_bell_once_per_episode(self):
        _skip_as_root(self)
        self.r.write_hold("qc-good")
        self.r.write_torn_hold("qc-torn")
        self.r.chmod(self.r.qdir, 0o500)             # listable and readable, no rename inside it
        cards, log = self._cards()
        self.assertEqual(cards, ["quarantine:qc-good"])
        rows = _refused()
        self.assertEqual(len(rows), 1, "the fault is on the bell, under the refused kind")
        self.assertIn("qc-torn.json could not be read or parsed and could not be moved aside", rows[0])
        self.assertIn("Permission denied", rows[0])
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)
        self.assertEqual(log.count("qc-torn.json"), 1, "and stderr carries it once")
        cards, log = self._cards()
        self.assertEqual((cards, log, len(_refused())), (["quarantine:qc-good"], "", 1), "quiet while the episode lasts")
        self.r.chmod(self.r.qdir, 0o700)
        cards, log = self._cards()                   # the next listing moves the file aside: the episode is over
        self.assertEqual(len(self._asides("qc-torn")), 1)
        self.assertEqual(len(_refused()), 2, "the moved-aside row")
        self.assertEqual([k for k in km._HOLD_UNREADABLE_SAID if k[0].startswith(str(self.r.qdir))], [])
        self.r.write_torn_hold("qc-torn")
        self.r.chmod(self.r.qdir, 0o500)
        cards, log = self._cards()                   # the same fault again is a new episode
        self.assertEqual(len(_refused()), 3, "said again")
        self.assertIn("qc-torn.json could not be read or parsed and could not be moved aside", log)

    def test_a_directory_that_lists_but_cannot_be_searched_rings_the_bell(self):
        _skip_as_root(self)
        self.r.write_hold("qc-1")
        self.r.write_hold("qc-2")
        self.r.chmod(self.r.qdir, 0o400)             # os.listdir succeeds, every stat is refused
        cards, log = self._cards()
        self.assertEqual(cards, [], "nothing could be read...")
        rows = _refused()
        self.assertEqual(len(rows), 2, "...and the bell says so, one row per file")
        self.assertTrue(all("could not be moved aside" in r and "Permission denied" in r for r in rows))
        self.assertTrue(all(len(r) <= km.SYNC_NOTICE_FIT for r in rows))
        self.assertNotIn("the other held messages are on the board", "".join(rows), "no false reassurance: none is")
        cards, log = self._cards()
        self.assertEqual((cards, log, len(_refused())), ([], "", 2))
        self.r.chmod(self.r.qdir, 0o700)
        cards, log = self._cards()
        self.assertEqual((cards, log, len(_refused())), (["quarantine:qc-1", "quarantine:qc-2"], "", 2), "back, quietly")
        self.assertEqual([k for k in km._HOLD_UNREADABLE_SAID if k[0].startswith(str(self.r.qdir))], [], "the episode is over")
        self.r.chmod(self.r.qdir, 0o400)
        cards, log = self._cards()
        self.assertEqual((cards, len(_refused())), ([], 4), "a fault that returns is said again")


class BellRowFits(_Case):
    """The moved-aside bell row named the file twice (the aside's name is the file's plus a suffix), so for a relayed
    message's sixty-one-character mid the row ran to 300 characters and the bell cut it inside the aside name. The
    stderr line keeps the whole row; the bell's is fitted to SYNC_NOTICE_FIT with the file named once, the aside as its
    suffix, and the reason last, cut before the reassurance."""

    def test_the_moved_aside_row_fits_the_bell_for_a_relayed_mid(self):
        self.r.write_hold("qc-good")
        self.r.write_torn_hold(RELAYED_MID)
        cards, log = self._cards()
        self.assertEqual(cards, ["quarantine:qc-good"])
        self.assertEqual(len(self._asides(RELAYED_MID)), 1)
        rows = _refused()
        self.assertEqual(len(rows), 1)
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT, rows[0])
        self.assertTrue(rows[0].startswith("held mail: %s.json could not be parsed; moved aside with the suffix .corrupt-" % RELAYED_MID), rows[0])
        self.assertIn("the held messages that could be read are on the board", rows[0])
        self.assertEqual(rows[0].count(RELAYED_MID), 1, "the file is named once")
        self.assertIn("%s.json could not be parsed (Expecting" % RELAYED_MID, log, "stderr keeps the reason where it happened")
        self.assertIn("moved aside to %s" % self._asides(RELAYED_MID)[0], log, "and the aside's full name")

    def test_the_unmovable_row_fits_too(self):
        _skip_as_root(self)
        self.r.write_torn_hold(RELAYED_MID)
        self.r.chmod(self.r.qdir, 0o500)
        cards, log = self._cards()
        rows = _refused()
        self.assertEqual((cards, len(rows)), ([], 1))
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT, rows[0])
        self.assertEqual(rows[0].count(RELAYED_MID), 1)

    def test_the_fit_cuts_the_reason_first_and_the_tail_last(self):
        fit = km.SYNC_NOTICE_FIT
        short = km._hold_bell_text("held mail: a.json could not be parsed", "moved aside with the suffix .corrupt-1", "the rest stand", "why")
        self.assertEqual(short, "held mail: a.json could not be parsed; moved aside with the suffix .corrupt-1, the rest stand (why)")
        head = "held mail: %s could not be parsed" % ("x" * 120)
        cut = km._hold_bell_text(head, "moved aside with the suffix .corrupt-20260919T000000Z", "the rest stand", "r" * 100)
        self.assertEqual(len(cut), fit)
        self.assertTrue(cut.startswith(head + "; moved aside with the suffix .corrupt-20260919T000000Z, the rest stand (rrr"))
        self.assertTrue(cut.endswith("…)"), "the reason is what gets cut, with an ellipsis")
        whole = km._hold_bell_text("h" * 200, "m" * 30, "the rest stand", "why")
        self.assertEqual(whole, "h" * 200 + "; " + "m" * 30 + " (why)", "the tail goes first; a reason that fits whole is not cut")
        tight = km._hold_bell_text("h" * 200, "m" * 30, "the rest stand", "r" * 40)
        self.assertEqual(tight, "h" * 200 + "; " + "m" * 30, "the point alone when neither the tail nor a dozen characters of reason fit")


class SweepArchivesSkippedLines(_Case):
    """_compact_notices rewrites the live file from the parsed rows, so a line the parse left out (a type-wrong row, a line
    that is not JSON) was deleted by the first pass that had anything else to archive, against the sweep's own contract
    ('nothing is deleted') and the parse's account of the episode's end ('the sweep archived the row'). The pass archives
    those lines now as `skipped` rows carrying their text, in the same block as the rows, and the archive's readers pass
    them by."""

    def _archive_rows(self):
        ap = km._notice_archive_dir() / (SID + ".jsonl")
        return [json.loads(l) for l in ap.read_text().splitlines() if l.strip()] if ap.exists() else None

    def test_the_sweep_archives_what_it_will_not_keep(self):
        bad = json.dumps(dict(_good(self.now, key="sweep"), rev="abc-not-a-rev", title="the sweep's own row"))
        garbage = "this line is not json MARK-GARBAGE"
        self.r.write_notice_rows([dict(_good(self.now), t=self.now - 100),
                                  {"op": "expire", "key": "figure", "rev": 1, "t": self.now - 50}, bad, garbage])
        feed, log = self._feed()
        self.assertEqual(log.count("needs an integer"), 1)
        with contextlib.redirect_stderr(io.StringIO()):
            moved = km._compact_notices(self.now)
        self.assertEqual(moved, 2, "the retired post and its expire row")
        self.assertEqual(km._notice_path(SID).read_text(), "", "the live file is rewritten without them")
        rows = self._archive_rows()
        self.assertEqual([r["op"] for r in rows], ["post", "expire", "skipped", "skipped"], "the skipped lines ride the same block")
        self.assertEqual([r["raw"] for r in rows if r["op"] == "skipped"], [bad, garbage], "each with its text, in file order")
        self.assertTrue(all(r["archivedAt"] == self.now for r in rows))
        feed, log = self._feed()
        self.assertEqual((_asks(feed, "notice:"), log), ([], ""))
        self.assertNotIn(SID, km._NOTICE_BAD_ROW_SAID, "the episode ends: the row was archived")
        km._notice_revs_path(SID).unlink()           # the index rebuilt from the archive passes the skipped rows by
        with km._notice_lock:
            revs, err = km._notice_revs_index_unlocked(SID)
        self.assertEqual((revs, err), ({"figure": 1}, ""))

    def test_nothing_to_archive_leaves_the_skipped_line_live(self):
        bad = json.dumps(dict(_good(self.now, key="sweep"), rev="abc-not-a-rev"))
        self.r.write_notice_rows([_good(self.now), bad])
        with contextlib.redirect_stderr(io.StringIO()):
            moved = km._compact_notices(self.now)
        self.assertEqual(moved, 0)
        self.assertIn(bad, km._notice_path(SID).read_text(), "no rewrite, nothing moved: the line stays where it was")
        self.assertIsNone(self._archive_rows())

    def test_undo_reads_past_the_skipped_rows(self):
        bad = json.dumps(dict(_good(self.now, key="sweep"), rev="abc-not-a-rev"))
        self.r.write_notice_rows([dict(_good(self.now), t=self.now - 100), bad])
        sent = []
        with contextlib.redirect_stderr(io.StringIO()):
            km.Handler._dispatch_ws(None, {"type": "askClear", "itemId": NOTICE_ID}, _client(sent))
            moved = km._compact_notices(self.now)
        self.assertEqual(moved, 1, "the cleared post is archived...")
        self.assertEqual([r["op"] for r in self._archive_rows()], ["post", "skipped"], "...with the skipped line")
        with contextlib.redirect_stderr(io.StringIO()):
            km.Handler._dispatch_ws(None, {"type": "undoClear"}, _client(sent))
        feed, _ = self._feed()
        self.assertEqual([c["itemId"] for c in _asks(feed, "notice:")], [NOTICE_ID], "Undo brings the card back")
        self.assertEqual([r["op"] for r in self._archive_rows()], ["skipped"], "the skipped row stays archived")
        self.assertEqual([m for m in sent if m.get("type") == "undoClearResult"], [])


if __name__ == "__main__":
    unittest.main()
