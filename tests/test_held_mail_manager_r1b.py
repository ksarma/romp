#!/usr/bin/env python3
"""The held-mail readers bundle, the manager's round 1 on the fork PR, the follow-on: the kernel-side items the round's
addendum routed to a second commit on the same branch, each pinned by a case that fails over a git archive of the round's
fix commit (0a589d1e4; the reviewed head 35fad278c where the addendum's evidence is older) and passes here. Three items.
A held record the reader moves aside is gone from its store for good (os.replace takes the file out of the `.json`
listing) while the row that said so was one of forty in memory, so a restart or forty later rows left the aside with no
record that it had existed: the listing reads the asides too now and says each again, folded, whenever the row that
carried it has left the ring, until the user deletes it or renames it back (extra6-4). The clear door's rule that a hold's
id takes no ledger was keyed on the one prefix while the placeholders build_feed re-lists whatever the ledger holds were
enumerated beside it, so a placeholder-only Clear all journaled an inert row per press and lit an Undo whose first press
restored nothing: the write and the read share one derived constant now (extra7-2). And the parity the addendum cites for
the row-level notice fault, the one reader of the PR's four that rang no bell before the round, is pinned in one build
over all four and on each road that parses a notice file (extra6-2, no separate fix: the round's fix covers every road).

The harness is the round 1 module's (tests/test_held_mail_reader_guards.py: its hermetic root, its private synthetic
sid, its fixtures), imported the way tests/test_held_mail_manager_r1.py imports it, and its import is the state
preamble (that module makes its root hermetic before it loads the kernel). Synthetic only: TESTHOST, placeholder ids,
invented text; every root writes `off` into <root>/session-hosts (repo rule, 2026-09-11) and no goals are minted."""
import contextlib
import inspect
import io
import json
import os
import re
import unittest
from unittest import mock

from tests.test_held_mail_reader_guards import (_Case, _asks, _client, _good, _refused, _skip_as_root, km,   # noqa: E402
                                                NOTICE_ID, SID)

SID2 = "11111111-2222-3333-4444-eeeeeeee0920"      # this module's PRIVATE synthetic sids: the files beside the good one
SID3 = "11111111-2222-3333-4444-eeeeeeee0921"
SID4 = "11111111-2222-3333-4444-eeeeeeee0922"
BODY_MARKER = "SECRET-BODY-MARKER-TEXT"            # a held record's body: must never reach a log line or a bell row
TITLE_MARKER = "SECRET-TITLE-MARKER-TEXT"          # a notice row's title: the same
PLACEHOLDERS = ("provisional:", "awaiting:", "blocked:", "usertodo:")   # the stand-ins build_feed re-lists whatever the ledger holds


def _hold_doc(mid, body='"ship the parser fix"', at="1000"):
    """One held record as raw JSON text, `body` and `at` written as given."""
    return ('{"mid": %s, "to": "web", "toId": "%s", "frm": "api", "frmId": "id-api", "body": %s, "kind": "coordinate", '
            '"origin": "TESTHOST", "at": %s}' % (json.dumps(mid), SID, body, at))


def _stand_in(prefix, sid=SID2):
    """A placeholder card as build_feed lists one: the id family and the `provisional` bit the pane's clearable reads."""
    return {"itemId": prefix + sid, "sid": sid, "name": "web", "color": "#888", "text": "Working", "t": 1000, "live": True,
            "turnId": None, "origin": None, "followupPending": None, "summary": None, "blockSummary": None,
            "background": None, "blocked": None, "column": "working", "provisional": True, "tree": []}


class _MCase(_Case):
    """The round 1 harness plus the SDK backend's once-per-process import notice absorbed up front, as the round 2 module
    does: it lands on the first build_feed of a process, so a case that asserts on its captured stderr must not depend
    on which case built first. The aside registry this follow-on adds is cleared on both sides here as well as by the
    harness (_Root._reset drops it since the same follow-on), so the module stands alone over an archive whose harness
    predates the registry."""

    def setUp(self):
        super().setUp()
        getattr(km, "_HOLD_ASIDE_SAID", {}).clear()
        with contextlib.redirect_stderr(io.StringIO()):
            km._sdk()

    def tearDown(self):
        getattr(km, "_HOLD_ASIDE_SAID", {}).clear()
        super().tearDown()

    def _notice_ids(self, feed):
        return [c["itemId"] for c in _asks(feed, "notice:")]

    def _write_raw_hold(self, name, text):
        self.r.qdir.mkdir(parents=True, exist_ok=True)
        p = self.r.qdir / name
        p.write_text(text)
        return p

    def _listing(self):
        return sorted(os.listdir(self.r.qdir))

    def _seed_refused(self, n=20):
        texts = ["an unrelated refusal %d stands on the ring" % i for i in range(n)]
        for t in texts:
            km._sync_notice(t, ok=False, kind="refused")
        return texts

    def _sweep(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            moved = km._compact_notices(self.now)
        return moved, err.getvalue()

    def _dispatch(self, msg, client):
        with contextlib.redirect_stderr(io.StringIO()):
            km.Handler._dispatch_ws(None, msg, client)

    def _restart(self):
        """What a kernel restart forgets, and nothing else: the bell ring and every said-once registry (the state-fault
        registry, the hold registries, the notice row facts). The stores on disk stand."""
        with km._SYNC_LOCK:
            del km._SYNC_NOTICES[:]
        km._state_fault_seen.clear()
        km._HOLD_UNREADABLE_SAID.clear()
        getattr(km, "_HOLD_ASIDE_SAID", {}).clear()
        getattr(km, "_NOTICE_BAD_ROW_SAID", {}).clear()

    def _aside_rows(self, name):
        """The refused rows that name the file `name` was listed under: the move-aside row names the file and the suffix,
        the standing-aside row the aside whole, and both carry the listed name."""
        return [r for r in _refused() if name in r]


class AMovedAsideRecordOutlivesTheRing(_MCase):
    """extra6-4: for every shape the reader moves aside, the rename is durable (os.replace takes the file out of the
    `.json` listing for good) and the say-so was not (one row on the forty-row in-memory ring), so after a kernel restart,
    or forty later bell rows, the held message was off the board, out of every count, and the only record that it had
    ever existed was gone with it. Every listing of the held-mail directory reads its `.json.corrupt-<stamp>` asides too
    now and says each once per episode, on stderr and as one folded bell row per listing, whenever the row that carried
    its fact has left the ring (the ring turned over, or a restart emptied it: the ring's own event, never a timer); the
    row names the file and what the user can do (rename it without the suffix to try again, or delete it), never its
    contents; the episode ends when the aside is gone. Nothing here renames a file: correctness-2's rule stands. Fails
    before over the 0a589d1e4 archive: the aside is silent once the ring turns over or the process restarts."""

    def test_a_restart_re_says_the_aside_once_naming_the_file_and_never_the_body(self):
        self.r.write_hold("qc-good")
        self._write_raw_hold("qc-torn.json", '{"mid": "qc-torn", "to": "web", "body": "%s", "at": 10' % BODY_MARKER)
        cards, log = self._cards()
        self.assertEqual(cards, ["quarantine:qc-good"])
        asides = self._asides("qc-torn")
        self.assertEqual(len(asides), 1, "read and not parsed: moved aside")
        self.assertEqual(len(_refused()), 1, "the move-aside row")
        cards, log = self._cards()
        self.assertEqual((cards, log, len(_refused())), (["quarantine:qc-good"], "", 1), "quiet while its row stands on the ring")
        listing = self._listing()
        self._restart()
        cards, log = self._cards()
        rows = _refused()
        self.assertEqual(len(rows), 1, "the aside is said again after a restart: one row")
        self.assertIn(asides[0], rows[0], "naming the aside")
        self.assertIn("was moved aside", rows[0])
        self.assertIn("rename it without the .corrupt- suffix", rows[0])
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)
        self.assertEqual(log.count("romp-kernel:"), 1, log)
        self.assertIn(asides[0], log)
        self.assertNotIn(BODY_MARKER, rows[0] + log, "never the record's text")
        self.assertEqual((cards, self._listing()), (["quarantine:qc-good"], listing), "the board and the store are unchanged: nothing renamed")
        cards, log = self._cards()
        self.assertEqual((log, len(_refused())), ("", 1), "and said once")

    def test_forty_later_rows_turn_the_ring_over_and_the_aside_is_said_again_exactly_once(self):
        self.r.write_torn_hold("qc-torn")
        self._cards()
        aside = "qc-torn.json"
        self.assertEqual(len(self._aside_rows(aside)), 1)
        self._seed_refused(km.SYNC_RING)             # forty unrelated refused rows after the aside: its row is off the ring
        self.assertEqual(self._aside_rows(aside), [], "evicted")
        cards, log = self._cards()
        self.assertEqual(len(self._aside_rows(aside)), 1, "present again exactly once")
        self.assertEqual(len(_refused()), km.SYNC_RING, "one row filed, the oldest seed gone: the ring is full")
        self.assertEqual(log.count("romp-kernel:"), 1)
        cards, log = self._cards()
        self.assertEqual((log, len(self._aside_rows(aside))), ("", 1), "quiet while the new row stands")
        self._seed_refused(km.SYNC_RING - 1)         # thirty-nine more: the row is the ring's oldest and still on it
        cards, log = self._cards()
        self.assertEqual((log, len(self._aside_rows(aside))), ("", 1), "still standing: nothing re-filed")
        self._seed_refused(1)                        # the fortieth evicts it
        cards, log = self._cards()
        self.assertEqual((log.count("romp-kernel:"), len(self._aside_rows(aside))), (1, 1), "the ring's own event, said again")

    def test_three_asides_in_one_directory_fold_to_one_row(self):
        for n in ("qc-torn-1", "qc-torn-2", "qc-torn-3"):
            self.r.write_torn_hold(n)
        self._cards()
        self.assertEqual(len(_refused()), 1, "the move-aside rows folded")
        self._restart()
        cards, log = self._cards()
        rows = _refused()
        self.assertEqual(len(rows), 1, "three asides after a restart: one row")
        self.assertIn("3 files moved aside on earlier builds", rows[0])
        self.assertIn("qc-torn-1.json.corrupt-", rows[0])
        self.assertIn(" more", rows[0], "the names past the fit are counted")
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)
        self.assertEqual(log.count("romp-kernel:"), 3, "each aside on stderr")
        for n in ("qc-torn-1", "qc-torn-2", "qc-torn-3"):
            self.assertIn(self._asides(n)[0], log)

    def test_removing_the_aside_ends_the_episode_and_a_new_aside_is_a_new_one(self):
        self.r.write_torn_hold("qc-torn")
        self._cards()
        aside = self._asides("qc-torn")[0]
        self._restart()
        self._cards()
        self.assertEqual(len(_refused()), 1, "said after the restart")
        (self.r.qdir / aside).unlink()               # the user deletes it
        cards, log = self._cards()
        self.assertEqual((log, len(_refused())), ("", 1), "the aside is gone: nothing filed")
        self.assertEqual([k for k in km._HOLD_ASIDE_SAID if k.startswith(str(self.r.qdir))], [], "the episode is over")
        self._restart()
        cards, log = self._cards()
        self.assertEqual((log, len(_refused())), ("", 0), "nothing stands, nothing is said")
        self.r.write_torn_hold("qc-torn")            # a new bad record under the same name
        cards, log = self._cards()
        self.assertEqual(len(self._asides("qc-torn")), 1)
        self.assertEqual(len(_refused()), 1, "a new aside is a new episode: its move-aside row")
        self.assertIn("could not be parsed", _refused()[0])
        cards, log = self._cards()
        self.assertEqual((log, len(_refused())), ("", 1), "quiet while that row stands")

    def test_renaming_the_aside_back_ends_the_episode_and_the_record_is_read_again(self):
        self.r.write_torn_hold("qc-torn")
        self._cards()
        aside = self.r.qdir / self._asides("qc-torn")[0]
        self._restart()
        self._cards()
        self.assertEqual(len(_refused()), 1)
        aside.write_text(_hold_doc("qc-torn"))       # the user repairs the bytes and renames the file back to try again
        os.replace(aside, self.r.qdir / "qc-torn.json")
        cards, log = self._cards()
        self.assertEqual((cards, log, len(_refused())), (["quarantine:qc-torn"], "", 1), "read: its card stands, nothing said")
        self.assertEqual([k for k in km._HOLD_ASIDE_SAID if k.startswith(str(self.r.qdir))], [])

    def test_a_directory_that_is_gone_ends_every_aside_episode(self):
        self.r.write_torn_hold("qc-torn")
        self._cards()
        self.assertEqual(len([k for k in km._HOLD_ASIDE_SAID if k.startswith(str(self.r.qdir))]), 1)
        for p in self.r.qdir.iterdir():
            p.unlink()
        self.r.qdir.rmdir()
        cards, log = self._cards()
        self.assertEqual((cards, log), ([], ""))
        self.assertEqual([k for k in km._HOLD_ASIDE_SAID if k.startswith(str(self.r.qdir))], [])

    def test_an_aside_whose_name_carries_a_line_break_forges_no_line(self):
        self._write_raw_hold("qc\nforged.json", "not json")
        self._cards()
        self.assertEqual(len([n for n in self._listing() if ".json.corrupt-" in n]), 1)
        self._restart()
        cards, log = self._cards()
        rows = _refused()
        self.assertEqual((len(rows), log.count("\n"), log.count("romp-kernel:")), (1, 1, 1), "one line, one row")
        self.assertIn("�", log)
        self.assertNotIn("\n", rows[0])


class PlaceholdersTakeNoLedger(_MCase):
    """extra7-2: _clear_all declined a hold's id and _cleared_undoable passed over the hold namespace, both keyed on the one
    prefix "quarantine:", while the placeholders build_feed re-lists every build whatever the ledger holds (provisional:,
    awaiting:, blocked:, and the fork's usertodo: stand-in) were enumerated beside them in _CLEARED_NO_SESSION, so a
    placeholder-only Clear all journaled an inert row per press (the accumulation the constant's comment already named)
    and lit an Undo whose first press restored nothing and whose second undid an earlier deliberate clear. The rule is a
    pair (the decline at the write, the filter at the read) and both halves read one derived constant, _CLEARED_NO_LEDGER.
    The placeholders ride the board through build_feed's own asks list, the shape the door reads, since no fixture here
    mints a live session. Fails before over the 0a589d1e4 archive: the write journals placeholder rows and the first Undo
    restores nothing."""

    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = _client(self.sent)
        self.stand = [_stand_in(p) for p in PLACEHOLDERS]
        real = km.build_feed

        def build(now, *a, **kw):
            f = real(now, *a, **kw)
            f["asks"] = list(f["asks"]) + [dict(c) for c in self.stand]
            return f
        self.patch = mock.patch.object(km, "build_feed", build)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.apps = []
        self.sends = mock.patch.object(km, "_send_to_app", lambda app, msg: self.apps.append((app, msg)))
        self.sends.start()
        self.addCleanup(self.sends.stop)

    def _results(self):
        return [m for m in self.sent if m.get("type") == "clearAllResult"]

    def _ids(self, feed, prefix):
        return [c["itemId"] for c in _asks(feed, prefix)]

    def test_a_clear_all_over_placeholders_alone_journals_nothing_and_lights_no_undo(self):
        feed, _ = self._feed()
        self.assertEqual(sorted(a["itemId"] for a in feed["asks"]), sorted(p + SID2 for p in PLACEHOLDERS), "the board: stand-ins alone")
        self._dispatch({"type": "clearAll"}, self.client)
        self.assertEqual(self.r.ledger_rows(), [], "nothing journaled for a board of placeholders")
        feed, _ = self._feed()
        self.assertEqual((feed["canUndoClear"], feed["dismissedCount"]), (False, 0), "no Undo over nothing")
        self.assertEqual([m for m in self.sent if m.get("type") == "err"], [])
        res = self._results()
        self.assertEqual(len(res), 1, "the press is answered, not ignored")
        self.assertEqual((res[0]["ok"], res[0]["cleared"], res[0]["left"], res[0]["held"]), (False, 0, 4, 0))
        self.assertIn("nothing was cleared", res[0]["text"])
        self.assertIn("4 session stand-ins", res[0]["text"])
        self.assertNotIn("approve or deny", res[0]["text"], "no decision is owed on a stand-in")
        self._dispatch({"type": "clearAll"}, self.client)
        self.assertEqual(self.r.ledger_rows(), [], "a second press accumulates nothing")

    def test_the_first_undo_after_a_placeholder_only_clear_all_restores_the_earlier_clear(self):
        self.r.write_notice_rows([_good(self.now)])
        self._dispatch({"type": "askClear", "itemId": NOTICE_ID}, self.client)   # an earlier, deliberate clear
        feed, _ = self._feed()
        self.assertEqual((self._ids(feed, "notice:"), feed["canUndoClear"]), ([], True))
        rows_before = self.r.ledger_rows()
        self._dispatch({"type": "clearAll"}, self.client)                          # the board holds the stand-ins alone
        self.assertEqual(self.r.ledger_rows(), rows_before, "nothing journaled")
        self._dispatch({"type": "undoClear"}, self.client)                         # the FIRST Undo restores the user's clear
        feed, _ = self._feed()
        self.assertEqual(self._ids(feed, "notice:"), [NOTICE_ID], "the earlier clear comes back at the first press")
        self.assertFalse(feed["canUndoClear"], "and nothing phantom is left to undo")
        self.assertEqual([m for m in self.sent if m.get("type") == "err"], [])

    def test_a_mixed_board_clears_the_card_and_answers_with_the_stand_ins_named_for_what_they_are(self):
        self.r.write_notice_rows([_good(self.now)])
        self.r.write_hold("qc-hold-1")
        self._dispatch({"type": "clearAll"}, self.client)
        self.assertEqual([(r["id"], r["op"]) for r in self.r.ledger_rows()], [(NOTICE_ID, "clear")], "one row: the card that takes the clear")
        res = self._results()
        self.assertEqual(len(res), 1)
        self.assertEqual((res[0]["ok"], res[0]["cleared"], res[0]["left"], res[0]["held"]), (True, 1, 5, 1))
        self.assertIn("1 card cleared", res[0]["text"])
        self.assertIn("1 held message awaiting your decision and 4 session stand-ins", res[0]["text"])
        self.assertTrue(res[0]["text"].endswith("stay on the board"), res[0]["text"])
        feed, _ = self._feed()
        self.assertEqual((self._ids(feed, "notice:"), self._ids(feed, "quarantine:"), feed["canUndoClear"]), ([], ["quarantine:qc-hold-1"], True))

    def test_an_older_ledger_holding_placeholder_rows_at_a_newer_stamp_is_no_batch(self):
        self.r.write_notice_rows([_good(self.now)])
        t1, t2 = float(self.now - 100), float(self.now - 50)   # the user's clear, then a Clear all over placeholders before this round
        with (self.r.state / "cleared.jsonl").open("w") as f:
            f.write(json.dumps({"id": NOTICE_ID, "t": t1, "op": "clear"}) + "\n")
            for p in PLACEHOLDERS:
                f.write(json.dumps({"id": p + SID2, "t": t2, "op": "clear"}) + "\n")
        feed, _ = self._feed()
        self.assertEqual((feed["canUndoClear"], feed["dismissedCount"]), (True, 1), "Undo offers the user's clear; the placeholder rows count for nothing")
        off = km._feed_off_frame(self.now)
        self.assertEqual((off["canUndoClear"], off["dismissedCount"]), (True, 1), "the off frame reads the same rule")
        self._dispatch({"type": "undoClear"}, self.client)
        feed, _ = self._feed()
        self.assertEqual(self._ids(feed, "notice:"), [NOTICE_ID], "the FIRST press restores the user's clear")
        self.assertEqual((feed["canUndoClear"], feed["dismissedCount"]), (False, 0))
        self.assertEqual([(r["id"], r["op"]) for r in self.r.ledger_rows()[5:]], [(NOTICE_ID, "undo")], "one undo row, none for a placeholder")
        self.assertEqual([m for m in self.sent if m.get("type") == "err"], [])

    def test_the_constant_is_the_one_place_the_families_are_spelled_and_both_halves_read_it(self):
        self.assertEqual(set(km._CLEARED_NO_LEDGER), {"quarantine:"} | set(PLACEHOLDERS), "the population: the hold and every placeholder family")
        self.assertTrue(set(km._CLEARED_NO_LEDGER) <= set(km._CLEARED_NO_SESSION), "every no-ledger family names no session")
        self.assertEqual(set(km._CLEARED_NO_SESSION) - set(km._CLEARED_NO_LEDGER), {"parked:", "notice:"}, "the two whose readers honour the ledger")
        src = open(km.__file__, encoding="utf-8").read()
        definition = re.search(r"^_CLEARED_NO_SESSION = (.*)$", src, re.M).group(1)
        self.assertIn("_CLEARED_NO_LEDGER", definition, "the session list is derived from the ledger list, not spelled twice")
        for fn in (km._clear_all, km._cleared_undoable):
            body = inspect.getsource(fn)
            self.assertIn("startswith(_CLEARED_NO_LEDGER)", body, fn.__name__)
            self.assertNotIn('startswith("quarantine:")', body, "%s: no literal member beside the constant" % fn.__name__)
        for p in PLACEHOLDERS:
            self.assertNotIn('startswith("%s")' % p, src, "no reader keys on one placeholder family by hand")
        held_counts = [l for l in src.splitlines() if 'startswith("quarantine:")' in l]
        self.assertEqual(len(held_counts), 1, "the one literal left is the clearAll door's count of the held messages it names")
        self.assertIn("_held = ", held_counts[0])
        self.assertEqual(km._cleared_undoable({"quarantine:x": 1.0, "provisional:s": 2.0, "awaiting:s": 3.0, "blocked:s": 4.0,
                                               "usertodo:s": 5.0, "parked:m": 6.0, NOTICE_ID: 7.0, "%s:g1" % SID: 8.0}),
                         {"parked:m": 6.0, NOTICE_ID: 7.0, "%s:g1" % SID: 8.0})
        written = []
        self.assertEqual(km._clear_all([p + SID2 for p in PLACEHOLDERS] + ["quarantine:qc-1", ""], written=written), {})
        self.assertEqual((written, self.r.ledger_rows()), ([], []), "every no-ledger id declined at the write, nothing journaled")


class FourReadersRingAlike(_MCase):
    """extra6-2, the evidence the addendum cites with extra5-1: every notice-row fault was written to stderr alone and rang
    no bell while the PR's three other readers (the notice file, the directory, the held record) each filed a refused
    row, the asymmetry inside one PR between four readers. The round's fix files the row-level fault's bell row inside the
    shared parse, so every road that parses a notice file (the display reader through _notice_rows, the writer's reader
    through _notice_rows_unlocked, the sweep) files it; this class pins the four-reader parity in one build and the row
    fault on each road, one row per episode. Over the 35fad278c archive the row-fault legs are red with zero rows, the
    evidence the addendum cites; over 0a589d1e4 every case is green, so the item needs no separate fix. A listing fault
    on the notices directory precludes its file and row faults in the same build (the listing is the entry to both), so
    the one-build case realises the directory-level fault as the fold's row for a cause two session files share, said
    once for the directory (correctness-3), and a second case pins the two directory listers' own rows beside the record
    readers they do not preclude."""

    def _bad_row(self):
        return dict(_good(self.now, key="sweep"), rev="not-a-rev", title=TITLE_MARKER)

    def test_the_four_readers_each_file_one_row_in_one_build_and_none_on_the_next(self):
        self.r.write_notice_rows([_good(self.now), self._bad_row()])                    # the row reader: one type-wrong row
        loop = km._notice_path(SID2)
        loop.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(loop.name, loop)                                                       # the file reader: a stat fault (ELOOP)
        for s in (SID3, SID4):
            km._notice_path(s).mkdir()                                                    # the directory-level fold: two files, one cause (EISDIR)
        self.r.write_hold("qc-good")
        self._write_raw_hold("qc-torn.json", '{"mid": "qc-torn", "to": "web", "body": "%s", "at": 10' % BODY_MARKER)   # the held record
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), [NOTICE_ID], "the good row's card stands")
        self.assertEqual([c["itemId"] for c in _asks(feed, "quarantine:")], ["quarantine:qc-good"])
        rows = _refused()
        by = {"row": [r for r in rows if r.startswith("notices/%s.jsonl: 1 line skipped" % SID)],
              "file": [r for r in rows if r.startswith("notices/%s.jsonl could not be read (stat failed:" % SID2)],
              "directory": [r for r in rows if r.startswith("notices: 2 session files could not be read (")],
              "held record": [r for r in rows if r.startswith("held mail: qc-torn.json could not be parsed")]}
        for reader in ("row", "file", "directory", "held record"):
            self.assertEqual(len(by[reader]), 1, "the %s reader files exactly one refused row; the ring holds %r" % (reader, rows))
        self.assertEqual(len(rows), 4, rows)
        for marker in (TITLE_MARKER, BODY_MARKER, "not-a-rev"):
            self.assertNotIn(marker, "".join(rows) + log, "never a title, a body or a value's text")
        feed, log = self._feed()
        self.assertEqual((len(_refused()), log), (4, ""), "a second build over the unchanged stores files none")

    def test_the_two_directory_listers_ring_beside_the_record_readers_they_do_not_preclude(self):
        km._notice_dir().parent.mkdir(parents=True, exist_ok=True)
        km._notice_dir().write_text("")                                                   # the notices directory cannot be listed (ENOTDIR)
        self.r.write_hold("qc-good")
        self.r.write_torn_hold("qc-torn")                                                 # beside a held record read and not parsed
        feed, log = self._feed()
        rows = _refused()
        self.assertEqual(len(rows), 2, rows)
        self.assertEqual(len([r for r in rows if r.startswith("the notices directory (notices) could not be listed (")]), 1)
        self.assertEqual(len([r for r in rows if r.startswith("held mail: qc-torn.json could not be parsed")]), 1)
        feed, log = self._feed()
        self.assertEqual((len(_refused()), log), (2, ""))
        self.r.close()                                                                     # a fresh root for the other pairing
        self.r = type(self.r)()
        self.r.qdir.parent.mkdir(parents=True, exist_ok=True)
        self.r.qdir.write_text("")                                                         # the held-mail directory cannot be listed (ENOTDIR)
        self.r.write_notice_rows([_good(self.now), self._bad_row()])                      # beside a row fault and a file fault
        loop = km._notice_path(SID2)
        os.symlink(loop.name, loop)
        feed, log = self._feed()
        rows = _refused()
        self.assertEqual(len(rows), 3, rows)
        self.assertEqual(len([r for r in rows if r.startswith("the held-mail directory (postal/quarantine) could not be listed (")]), 1)
        self.assertEqual(len([r for r in rows if r.startswith("notices/%s.jsonl: 1 line skipped" % SID)]), 1)
        self.assertEqual(len([r for r in rows if r.startswith("notices/%s.jsonl could not be read (stat failed:" % SID2)]), 1)
        feed, log = self._feed()
        self.assertEqual((len(_refused()), log), (3, ""))

    def test_the_display_reader_files_one_row_per_episode(self):
        self.r.write_notice_rows([_good(self.now), self._bad_row()])
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), [NOTICE_ID])
        rows = _refused()
        self.assertEqual(len(rows), 1, "the display reader's parse files the row")
        self.assertIn("notices/%s.jsonl" % SID, rows[0])
        self.assertIn("sweep", rows[0])
        self.assertNotIn(TITLE_MARKER, rows[0] + log)
        feed, log = self._feed()
        self.assertEqual((len(_refused()), log), (1, ""), "once per episode: the memo serves the second build")
        self.r.write_notice_rows([_good(self.now, key="other")])                          # the file moves: a fresh parse, the same fact
        feed, log = self._feed()
        self.assertEqual((len(self._notice_ids(feed)), len(_refused()), log), (2, 1, ""))

    def test_a_post_through_the_writers_reader_files_one_row_and_still_posts(self):
        known = mock.patch.object(km, "_notice_session_known", lambda sid: True)   # the harness has no live session to post to
        known.start()
        self.addCleanup(known.stop)
        self.r.write_notice_rows([_good(self.now), self._bad_row()])
        with contextlib.redirect_stderr(io.StringIO()) as err:
            row, perr = km.post_notice(SID, "later", "A later figure is ready", producer="figure", now=self.now)
        self.assertEqual((perr, row["rev"]), (None, 1), "the bad row skips; the post lands")
        rows = _refused()
        self.assertEqual(len(rows), 1, "the writer's reader files the row")
        self.assertIn("notices/%s.jsonl" % SID, rows[0])
        self.assertNotIn(TITLE_MARKER, rows[0] + err.getvalue())
        with contextlib.redirect_stderr(io.StringIO()) as err:
            row, perr = km.post_notice(SID, "later", "A later figure is ready again", producer="figure", now=self.now)
        self.assertEqual((perr, row["rev"], len(_refused()), err.getvalue().count("romp-kernel:")), (None, 2, 1, 0),
                         "a second post: the same fact, nothing re-filed and nothing re-said (the post's own log line aside)")

    def test_the_sweep_alone_files_one_row_per_episode(self):
        self.r.write_notice_rows([_good(self.now), self._bad_row()])
        moved, log = self._sweep()
        self.assertEqual(moved, 0)
        rows = _refused()
        self.assertEqual(len(rows), 1, "the sweep's parse files the row")
        self.assertIn("notices/%s.jsonl" % SID, rows[0])
        self.assertIn("needs an integer", log)
        self.assertNotIn(TITLE_MARKER, rows[0] + log)
        moved, log = self._sweep()
        self.assertEqual((moved, len(_refused()), log), (0, 1, ""), "a second pass: nothing re-filed")


if __name__ == "__main__":
    unittest.main()
