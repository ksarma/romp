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
import threading
import unittest
from unittest import mock

from tests.test_held_mail_reader_guards import (_Case, _asks, _client, _good, _refused, _skip_as_root, km,   # noqa: E402
                                                NOTICE_ID, RELAYED_MID, SID)

SID2 = "11111111-2222-3333-4444-eeeeeeee0920"      # this module's PRIVATE synthetic sids: the files beside the good one
SID3 = "11111111-2222-3333-4444-eeeeeeee0921"
SID4 = "11111111-2222-3333-4444-eeeeeeee0922"
BODY_MARKER = "SECRET-BODY-MARKER-TEXT"            # a held record's body: must never reach a log line or a bell row
TITLE_MARKER = "SECRET-TITLE-MARKER-TEXT"          # a notice row's title: the same
PLACEHOLDERS = ("provisional:", "awaiting:", "blocked:", "usertodo:")   # the stand-ins build_feed re-lists whatever the ledger holds:
#                                                                          the census's EXPECTED value, never its source (the minters are)
LEDGER_HONOURING = ("parked:", "notice:")   # the two families whose readers honour the ledger, so a clear of them is a real dismissal
KERNEL_SRC = os.path.realpath(km.__file__)
FEED_TS = os.path.join(os.path.dirname(os.path.dirname(KERNEL_SRC)), "ui", "webview", "feed.ts")


def _minted_families(src):
    """The id families kernel.py's card minters spell, derived from the source rather than kept by hand (the manager's
    round 2, LENS TWO: regression-4, correctness-7, kernel-5, extra7-1, tests-1). Three mint forms are read: the
    placeholder form (`"itemId": "<family>:" + <expr>`, the colon captured, since the constant's members carry it), the
    variable form (`item_id = "<family>:" + <expr>`, the hold card's and the parked handoff's), and the helper form
    (`item_id = <helper>(`, the notice card's, whose helper's return spells its family). A coarser read counts every
    itemId built from a string or f-string literal inline and every item_id assignment from a literal, an f-string or a
    call, and a site the fine reads do not account for (an f-string, a literal in another shape, a helper this function
    does not know) fails loudly instead of vanishing from the census; a frame's `"itemId": str(...)` is no mint and is
    not counted. Returns (families, sites): the set of prefixes and the number of mint sites they came from."""
    fine = re.findall(r'"itemId": "(\w+:)" \+ \w+', src) + re.findall(r'^\s+item_id = "(\w+:)" \+ ', src, re.M)
    helpers = re.findall(r'^\s+item_id = (\w+)\(', src, re.M)
    for h in helpers:
        m = re.search(r'^def %s\([^)]*\):\n\s+return "(\w+:)' % re.escape(h), src, re.M)
        if m is None:
            raise AssertionError("an itemId helper the census cannot read: %s" % h)
        fine.append(m.group(1))
    coarse = len(re.findall(r'"itemId": f?"', src)) + len(re.findall(r'^\s+item_id = (?:f?"|\w+\()', src, re.M))
    if coarse != len(fine):
        raise AssertionError("%d itemId mint sites, %d read by the census: a mint shape it does not recognise" % (coarse, len(fine)))
    return set(fine), len(fine)


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
        """The subject is the aside registry itself (_HOLD_ASIDE_SAID, 0a589d1e4's), so over the 0a589d1e4 archive this case
        errors on the registry's name before its assertion: an error-shaped red legitimate for a case whose subject is the
        new API, named as such; the behaviour a user sees (the aside said again after a restart) is the sibling cases',
        red there at the row count."""
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


    def test_a_relayed_holds_aside_row_keeps_its_stamp_whole_and_the_advice_goes_first(self):
        """correctness-5, the manager's round 2: _hold_bell_text shortened the file NAME before dropping the advice tail, so
        the standing-aside row for a relayed hold (a 91-character aside name) cut the UTC stamp, the part that tells one
        aside from the next, while 89 characters of generic advice stayed whole. The name whole with the tail dropped is
        tried first; the stderr line carries the advice. Fails before over the 085e08deb archive: the stamp is cut."""
        self.r.write_torn_hold(RELAYED_MID)
        self._cards()
        aside = self._asides(RELAYED_MID)[0]
        self.assertGreater(len(aside), km._HOLD_NAME_FIT, "the aside's name is over the width the bell shortens at")
        self._restart()
        cards, log = self._cards()
        rows = _refused()
        self.assertEqual(len(rows), 1)
        self.assertIn(aside, rows[0], "the aside is named whole, its UTC stamp included: the name the user must find")
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)
        self.assertNotIn("rename it without", rows[0], "the generic advice went first")
        self.assertIn("rename it without the .corrupt- suffix", log, "the stderr line carries it")
        self.assertIn(aside, log)

    def test_an_aside_from_an_undecidable_name_gets_the_id_advice_and_a_torn_record_the_rename_advice(self):
        """extra8-3, the manager's round 2: the standing-aside row told the user to rename the file back without its
        suffix to try again, but a record moved aside because the bus cannot decide its id has the NAME as its fault, so
        that advice loops forever. The class is read from the aside's own de-suffixed stem (_say_hold_asides opens no
        file): a stem _safe_id refuses gets the advice that works, a name the bus can decide with a matching message id;
        every other aside keeps the rename advice; the two classes are two fold heads, so two rows. Both rows fit. Fails
        before over the 085e08deb archive: one folded row with the rename advice for both."""
        self._write_raw_hold("with space.json", _hold_doc("with space"))   # refused as undecidable (correctness-1) and moved aside
        self.r.write_torn_hold("qc-torn")
        self._cards()
        self.assertEqual((len([n for n in self._listing() if n.startswith("with space.json.corrupt-")]), len(self._asides("qc-torn"))), (1, 1))
        self._restart()
        cards, log = self._cards()
        rows = _refused()
        by_id = [r for r in rows if "with space.json.corrupt-" in r]
        by_rename = [r for r in rows if "qc-torn.json.corrupt-" in r]
        self.assertEqual((len(rows), len(by_id), len(by_rename)), (2, 1, 1), "two classes, two rows: %r" % rows)
        self.assertIn("give it a name the bus can decide and a matching message id", by_id[0])
        self.assertNotIn("rename it without", by_id[0], "renaming it back cannot succeed: the name itself is the fault")
        self.assertIn("rename it without the .corrupt- suffix", by_rename[0])
        for r in rows:
            self.assertLessEqual(len(r), km.SYNC_NOTICE_FIT)
        self.assertIn("its message id is not one the bus can decide, so renaming it back cannot succeed", log)
        self.assertEqual(log.count("romp-kernel:"), 2)


class OverlappingListingsSayTheAsideOnce(_MCase):
    """kernel-2, the manager's round 2: the standing-aside say-once was a check-then-act across a whole listing, the
    registry read at the top of _say_hold_asides and written only after the fold's rows were filed, so two listings of the
    held-mail directory overlapping (the pusher's thread and a GET /feed.json) each said the same aside, two log lines and
    two ring slots per episode. The check, the say and the write of the row's seq run under one lock now
    (_HOLD_ASIDE_LOCK). The two listings are released together at a barrier inside the section, keyed on events (the
    second listing's arrival at the section's door, or inside it on a head with no door), never a timer. Fails before over
    the 085e08deb archive: two lines, two rows."""

    def test_two_listings_released_together_say_a_standing_aside_once(self):
        self.r.write_torn_hold("qc-torn")
        self._cards()
        aside = self._asides("qc-torn")[0]
        self._restart()                              # the ring empty: the next listing must say the aside again
        real = km._sync_notice_standing
        a_inside, b_arrived, release = threading.Event(), threading.Event(), threading.Event()
        calls, guard = [], threading.Lock()

        def standing(seq):
            with guard:
                calls.append(seq)
                n = len(calls)
            if n == 1:                               # the first listing, inside the section: waits for the second to arrive
                a_inside.set()
                release.wait(60)
            else:                                    # the second listing reached the check too (a head with no lock)
                b_arrived.set()
            return real(seq)
        patches = [mock.patch.object(km, "_sync_notice_standing", standing)]
        door = getattr(km, "_HOLD_ASIDE_LOCK", None)
        if door is not None:
            class _Door:                             # the second listing's arrival at the lock is its arrival at the section
                def __enter__(self_):
                    if a_inside.is_set():
                        b_arrived.set()
                    return door.__enter__()

                def __exit__(self_, *a):
                    return door.__exit__(*a)
            patches.append(mock.patch.object(km, "_HOLD_ASIDE_LOCK", _Door()))
        err = io.StringIO()
        results = {}

        def listing(name):
            results[name] = km._quarantine_cards(self.now)
        a, b = threading.Thread(target=listing, args=("a",)), threading.Thread(target=listing, args=("b",))
        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            stack.enter_context(contextlib.redirect_stderr(err))
            a.start()
            self.assertTrue(a_inside.wait(60), "the first listing reached the aside check")
            b.start()
            self.assertTrue(b_arrived.wait(60), "the second listing arrived while the first stood inside the section")
            release.set()
            a.join(60)
            b.join(60)
        self.assertFalse(a.is_alive() or b.is_alive(), "both listings finished")
        self.assertEqual((results["a"], results["b"]), ([], []))
        log = err.getvalue()
        self.assertEqual(log.count("romp-kernel:"), 1, "one log line for the aside across the two listings:\n%s" % log)
        rows = _refused()
        self.assertEqual(len(rows), 1, "one ring slot: %r" % rows)
        self.assertIn(aside, rows[0])
        self.assertTrue(km._sync_notice_standing(km._HOLD_ASIDE_SAID[str(self.r.qdir / aside)]), "the registry holds the row that carries it")


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
        """The census (the manager's round 2, LENS TWO): the population is DERIVED from kernel.py's minters at run time
        and every derived family must be classified, into _CLEARED_NO_LEDGER (the kernel's) or into LEDGER_HONOURING (the
        expected value kept here), by equality both ways, so a family minted later reds UNTIL CLASSIFIED and a member
        with no minter reds too; the literals PLACEHOLDERS and LEDGER_HONOURING are the census's expected values, never
        its source. The floor (no fewer than the seven families read today) reds a regex that stops matching; the
        coarse count reds a mint shape the census does not read. kernel-5's extension: the pane's clearable predicate
        (feed.ts, read by name) is a live-value test over the card's own fields, so what is pinned is that its inputs are
        what every derived no-ledger family's card carries and nothing a ledger-honouring family's card carries. Red by
        mutation at this head (a sixth family minted and left unclassified; a member dropped from the constant; the
        regex written without the colon), green here; the write and the answer are driven over the derived set. Over the
        0a589d1e4 archive it errors on the constant's name (an error before its assertion, not evidence); over 085e08deb
        it is green, as a census on correct input should be; the mutations are the evidence."""
        src = open(KERNEL_SRC, encoding="utf-8").read()
        derived, sites = _minted_families(src)
        self.assertTrue(derived, "the census read nothing")
        self.assertGreaterEqual(len(derived), 7, "the floor: the seven families read today (%r)" % sorted(derived))
        self.assertGreaterEqual(sites, 7)
        for fam in derived:
            self.assertRegex(fam, r"^\w+:$", "a family carries its colon, as the constant's members do")
        no_ledger, honouring = set(km._CLEARED_NO_LEDGER), set(LEDGER_HONOURING)
        self.assertEqual(no_ledger & honouring, set(), "a family is classified into exactly one of the two")
        self.assertEqual(derived, no_ledger | honouring, "every minted family is classified, and every classified family is minted")
        self.assertEqual(set(km._CLEARED_NO_SESSION), derived, "the no-session list is the whole derived population")
        self.assertEqual(no_ledger, {"quarantine:"} | set(PLACEHOLDERS), "the expected value: the hold and every placeholder family")
        definition = re.search(r"^_CLEARED_NO_SESSION = (.*)$", src, re.M).group(1)
        self.assertIn("_CLEARED_NO_LEDGER", definition, "the session list is derived from the ledger list, not spelled twice")
        for fn in (km._clear_all, km._cleared_undoable):
            body = inspect.getsource(fn)
            self.assertIn("startswith(_CLEARED_NO_LEDGER)", body, fn.__name__)
            self.assertNotIn('startswith("quarantine:")', body, "%s: no literal member beside the constant" % fn.__name__)
        for p in sorted(no_ledger - {"quarantine:"}):
            self.assertFalse('startswith("%s")' % p in src, "no reader keys on the %s family by hand" % p)
        held_counts = [l for l in src.splitlines() if 'startswith("quarantine:")' in l]
        self.assertEqual(len(held_counts), 1, "the one literal left is the clearAll door's count of the held messages it names")
        self.assertIn("_held = ", held_counts[0])
        # the read half over the derived set
        ledger = {p + "s": float(i) for i, p in enumerate(sorted(derived), 1)}
        ledger.update({NOTICE_ID: 20.0, "%s:g1" % SID: 21.0})
        kept = km._cleared_undoable(ledger)
        self.assertEqual(set(kept), {p + "s" for p in honouring} | {NOTICE_ID, "%s:g1" % SID}, "Undo passes over every no-ledger family's rows")
        # the write half and the answer over the derived set: one card per no-ledger family beside one ordinary card
        placeholders = sorted(derived & no_ledger - {"quarantine:"})
        self.stand = [_stand_in(p) for p in placeholders]
        self.r.write_hold("qc-hold-1")
        self.r.write_notice_rows([_good(self.now)])
        self._dispatch({"type": "clearAll"}, self.client)
        self.assertEqual([(r["id"], r["op"]) for r in self.r.ledger_rows()], [(NOTICE_ID, "clear")], "the ordinary card alone is written")
        res = self._results()
        self.assertEqual(len(res), 1)
        self.assertEqual((res[0]["ok"], res[0]["cleared"], res[0]["left"], res[0]["held"]), (True, 1, len(placeholders) + 1, 1),
                         "cleared 1; the stand-ins and the held message counted by family")
        self.assertIn("%d session stand-in" % len(placeholders), res[0]["text"])
        self.assertIn("1 held message", res[0]["text"])
        # kernel-5: the pane's predicate over the same derived set
        ts = open(FEED_TS, encoding="utf-8").read()
        m = re.search(r"^function clearable\(it: AskItem\): boolean \{\n  return (.*);\n\}", ts, re.M)
        self.assertIsNotNone(m, "feed.ts's clearable, read by name")
        self.assertEqual(m.group(1), '!it.provisional && it.blocked?.state !== "quarantine"',
                         "the predicate's inputs: the provisional bit and the hold's blocked state, nothing keyed on a family list")
        clearable = lambda c: not c.get("provisional") and (c.get("blocked") or {}).get("state") != "quarantine"
        feed, _ = self._feed()
        cards = {c["itemId"].split(":", 1)[0] + ":": c for c in feed["asks"]}   # one card per family the board holds
        self.assertEqual(set(cards), set(placeholders) | {"quarantine:"}, "the board holds every no-ledger family after the clear")
        for fam in placeholders:
            self.assertFalse(clearable(cards[fam]), "%s: a stand-in fails the pane's predicate (provisional)" % fam)
            mint = src[src.index('"itemId": "%s" + ' % fam):]
            mint = mint[:mint.index('"tree": []}') + 1]           # the card literal, to its last key
            self.assertIn('"provisional": True', mint, "%s: its mint sets the bit the predicate reads" % fam)
        self.assertFalse(clearable(cards["quarantine:"]), "a hold fails it (blocked.state quarantine)")
        self.assertEqual(cards["quarantine:"]["blocked"]["state"], "quarantine")
        self._dispatch({"type": "undoClear"}, self.client)
        feed, _ = self._feed()
        notice = [c for c in feed["asks"] if c["itemId"] == NOTICE_ID]
        self.assertEqual(len(notice), 1)
        self.assertTrue(clearable(notice[0]), "a ledger-honouring family's card passes it: the notice card carries neither input")
        parked = src[src.index('item_id = "parked:" + '):]
        parked = parked[:parked.index('"tree": []})') + 1]
        self.assertNotIn('"provisional"', parked, "the parked handoff's mint sets no provisional bit...")
        self.assertIn('"blocked": {"state": "parkedHandoff"', parked, "...and its blocked state is not the hold's: it passes the predicate")


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
