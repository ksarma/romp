#!/usr/bin/env python3
"""The held-mail readers bundle, the manager's round 1 on the fork PR: the kernel-side fixes the round ruled, each pinned
by a case that fails over a git archive of the reviewed head (35fad278c; the base bc88256e8 where the ruling says so) and
passes here. The rule is the bundle's, sharpened by the round into three states a reader of a store meets (stated once,
at _note_read_fault_once): bytes that could not be READ are skipped and retried on the next build and never renamed,
because a rename is terminal and the bytes may be a good record; bytes read and not PARSED, or read and refused by
shape, earn the move aside; a record that parsed whose FIELD has an unexpected type is handled by naming the type and is
never refused for it. Unreadable is not unparseable, and neither is corrupt. Beside the states: a reader that did not
read never reports absent, on the writer's side (post_notice, expire_notice, the sweep) and in the gesture layer (the
notice card's action door, the footer's Clear all); every reader fault reaches the bell, the row-level notice fault
included, and every skipped notice line is said before the sweep archives it; a directory-level fault is said once for
the directory and not once per file, so one chmod cannot evict every other notice from the forty-row ring; a said-once
episode ends on any successful read of its subject, wherever that read happens; a file name or session id from a
directory listing forges no log or bell line; and an id the bus cannot decide never becomes a card that can be neither
decided nor dismissed.

The harness is the round 1 module's (tests/test_held_mail_reader_guards.py: its hermetic root, its private synthetic
sid, its fixtures), imported the way tests/test_held_mail_reader_guards_r2.py imports it, and its import is the state
preamble (that module makes its root hermetic before it loads the kernel). Synthetic only: TESTHOST, placeholder ids,
invented text; every root writes `off` into <root>/session-hosts (repo rule, 2026-09-11) and no goals are minted."""
import contextlib
import errno
import inspect
import io
import json
import os
import shutil
import subprocess
import unittest
from unittest import mock

from tests.test_held_mail_reader_guards import (_Case, _Root, _asks, _client, _good, _refused, _skip_as_root, km,   # noqa: E402
                                                NOTICE_ID, SID)

SID2 = "11111111-2222-3333-4444-dddddddd0920"      # a second PRIVATE synthetic sid: the file beside the good one
BODY_MARKER = "SECRET-BODY-MARKER-TEXT"            # a held record's body: must never reach a log line or a bell row
TITLE_MARKER = "SECRET-TITLE-MARKER-TEXT"          # a notice row's title: the same
RELAYED_MID = "px-1758300000.12345_%s.TESTHOST" % ("0123456789abcdef" * 2)   # the bus's mid shape for a relayed message: 61 characters
DEPTH = 100000
DEEP_BODY_DOC = '{"mid": "%s", "to": "web", "at": 1000, "body": ' + "[" * DEPTH + "]" * DEPTH + "}"


def _deep_list(depth=DEPTH):
    """The value the free-threaded 3.14 parser returns for a document nested past its predecessors' limit, built
    iteratively: nothing here parses or formats it."""
    v = []
    for _ in range(depth):
        v = [v]
    return v


@contextlib.contextmanager
def _parser_returning(values):
    """json.loads as the free-threaded Python 3.14 answers a deep document, on every Python (the round 2 module's stand-in,
    copied: it is private to that module): a text that starts with one of `values`' keys returns that value, and every
    other text goes to the real parser."""
    real = json.loads

    def loads(text, *a, **kw):
        for prefix, value in values.items():
            if text.startswith(prefix):
                return value
        return real(text, *a, **kw)
    with mock.patch.object(json, "loads", loads):
        yield


def _hold_doc(mid, body='"ship the parser fix"', at="1000"):
    """One held record as raw JSON text, `body` and `at` written as given so a literal json.dumps cannot emit reaches the
    parser as written."""
    return ('{"mid": %s, "to": "web", "toId": "%s", "frm": "api", "frmId": "id-api", "body": %s, "kind": "coordinate", '
            '"origin": "TESTHOST", "at": %s}' % (json.dumps(mid), SID, body, at))


class _MCase(_Case):
    """The round 1 harness plus the SDK backend's once-per-process import notice absorbed up front, as the round 2 module
    does: it lands on the first build_feed of a process, so a case that asserts on its captured stderr must not depend
    on which case built first."""

    def setUp(self):
        super().setUp()
        with contextlib.redirect_stderr(io.StringIO()):
            km._sdk()

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


class ReadFaultLeavesTheFileInPlace(_MCase):
    """correctness-2, ruled up to high: _held_records treated a hold file it could not READ (EACCES, EIO) exactly like one
    it could not PARSE, and when the pre-read stat had succeeded it renamed the file to <name>.json.corrupt-<stamp>. The
    bytes may be a perfectly good held message and the rename is terminal (the sender was acked at hold time), so a
    transient read fault destroyed real undelivered mail, a regression against main, where the fault was skipped and
    the hold came back on the next build. State one of the three: skip, say once per (file, errno) per episode naming
    the file and the errno, retry next build, never rename. The rename is reserved for bytes actually read and not
    parsed (the control case). Fails before over the 35fad278c archive: the mode-000 file is renamed on the first build
    and the EMFILE listing takes every hold off the board for good."""

    def test_a_file_that_cannot_be_read_is_not_renamed_and_comes_back(self):
        _skip_as_root(self)
        self.r.write_hold("qc-good")
        locked = self._write_raw_hold("qc-locked.json", _hold_doc("qc-locked", body='"%s"' % BODY_MARKER))
        before = locked.read_bytes()
        self.r.chmod(locked, 0)
        cards, log = self._cards()
        self.assertEqual(cards, ["quarantine:qc-good"], "the readable hold stands; the unreadable one waits")
        self.assertEqual(self._listing(), ["qc-good.json", "qc-locked.json"], "the listing is unchanged: nothing renamed")
        self.assertEqual(self._asides("qc-locked"), [], "never moved aside on a read fault")
        self.assertEqual(log.count("romp-kernel:"), 1, log)
        self.assertIn("held mail: qc-locked.json could not be read ([Errno 13] Permission denied)", log)
        self.assertIn("skipped and left in place for the next build", log)
        self.assertNotIn("moved aside", log, "the words say nothing was attempted on the file")
        self.assertNotIn(BODY_MARKER, log)
        rows = _refused()
        self.assertEqual(len(rows), 1, "one bell row for the one file")
        self.assertIn("qc-locked.json could not be read", rows[0])
        self.assertIn("Permission denied", rows[0])
        self.assertNotIn(BODY_MARKER, rows[0])
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)
        cards, log = self._cards()
        self.assertEqual((cards, log, len(_refused())), (["quarantine:qc-good"], "", 1), "said once per episode")
        self.r.chmod(locked, 0o600)
        cards, log = self._cards()
        self.assertEqual((cards, log), (["quarantine:qc-good", "quarantine:qc-locked"], ""), "readable again: the hold is back")
        self.assertEqual(locked.read_bytes(), before, "byte-identical: the file was never touched")
        self.assertEqual([k for k in km._HOLD_UNREADABLE_SAID if k[0].startswith(str(self.r.qdir))], [], "the episode is over")

    def test_a_directory_wide_read_fault_leaves_every_file_in_place(self):
        names = ["qc-%d" % i for i in range(5)]
        for n in names:
            self.r.write_hold(n)
        listing = self._listing()

        def refusing_read(self_path, *a, **kw):
            raise OSError(errno.EMFILE, "Too many open files")
        with mock.patch.object(km.Path, "read_text", refusing_read):
            cards, log = self._cards()
            self.assertEqual(cards, [], "nothing could be read...")
            self.assertEqual(self._listing(), listing, "...and every file is where it was")
            self.assertEqual(log.count("could not be read ([Errno 24] Too many open files)"), 5, log)
            rows = _refused()
            self.assertEqual(len(rows), 1, "one cause, one row (correctness-3)")
            self.assertIn("5 files could not be read ([Errno 24] Too many open files)", rows[0])
            self.assertIn("skipped and left in place for the next build", rows[0])
            cards, log = self._cards()
            self.assertEqual((cards, log, len(_refused())), ([], "", 1), "quiet while the fault lasts")
        cards, log = self._cards()
        self.assertEqual((sorted(cards), log), (sorted("quarantine:" + n for n in names), ""), "the next build has them all")
        self.assertEqual([k for k in km._HOLD_UNREADABLE_SAID if k[0].startswith(str(self.r.qdir))], [])

    def test_bytes_that_do_not_parse_are_still_moved_aside(self):
        self.r.write_hold("qc-good")
        self.r.write_torn_hold("qc-torn")
        cards, log = self._cards()
        self.assertEqual(cards, ["quarantine:qc-good"])
        self.assertEqual(len(self._asides("qc-torn")), 1, "read whole and not parsed: the rename is earned")
        self.assertIn("qc-torn.json could not be parsed (", log)

    def test_the_three_states_are_stated_once_where_both_readers_cite_them(self):
        doc = km._note_read_fault_once.__doc__
        for phrase in ("THE THREE STATES", "could not be READ", "could not be PARSED", "FIELD has an unexpected type",
                       "unreadable is not unparseable"):
            self.assertIn(phrase, doc)
        for fn in (km._held_records, km._say_hold_unreadable_once, km._hold_text):
            self.assertIn("_note_read_fault_once", fn.__doc__, "%s cites the statement rather than restating it" % fn.__name__)
        arm = inspect.getsource(km._held_records)
        self.assertIn("_say_hold_unreadable_once(f, e, fold, read=True)", arm, "the read fault's arm skips and says; no aside follows it")


class ANonTextBodyKeepsItsCard(_MCase):
    """extra8-1, high: the PR's last commit refused a record whose `body` is not text and moved the file aside as corrupt,
    so a held message the bus's writer had accepted left the board with no card and could be neither approved nor
    denied. State three: a record that was READ AND PARSED is never declared corrupt for a field's TYPE; the card names
    the body by its type (_hold_text) and never formats it, on whichever parser the interpreter carries. Approve and
    Deny reach the bus with the hold's id (the bus's own roads are the postal unit's). Fails before over the 35fad278c
    archive: the record moves aside and no card is built (on this interpreter the deep DOCUMENT still raises in
    json.loads and stays a parse fault, which is right, so the deep-body case runs through the parser stand-in)."""

    def _decide(self, mid, action):
        sent, acted = [], []

        def _act(body):
            acted.append(body)
            return True, ""
        with mock.patch.object(km, "_bus_quarantine_act", _act):
            self._dispatch({"type": "quarantineDecision", "mid": mid, "action": action, "sid": SID}, _client(sent))
        self.assertEqual([m for m in sent if m.get("type") == "quarantineRefused"], [])
        self.assertEqual([(b["mid"], b["action"]) for b in acted], [(mid, action)], "the decision reaches the bus with the hold's id")

    def test_a_list_body_and_a_dict_body_build_decidable_cards(self):
        self.r.write_hold("qc-good")
        self._write_raw_hold("qc-lbody.json", _hold_doc("qc-lbody", body='["%s", 2, 3]' % BODY_MARKER))
        self._write_raw_hold("qc-dbody.json", _hold_doc("qc-dbody", body='{"%s": 1}' % BODY_MARKER))
        feed, log = self._feed()
        held = {c["itemId"]: c for c in _asks(feed, "quarantine:")}
        self.assertEqual(sorted(held), ["quarantine:qc-dbody", "quarantine:qc-good", "quarantine:qc-lbody"], "every card stands")
        self.assertEqual((held["quarantine:qc-lbody"]["blocked"]["body"], held["quarantine:qc-lbody"]["blocked"]["gist"]), ("list", "list"))
        self.assertEqual(held["quarantine:qc-dbody"]["blocked"]["body"], "dict")
        self.assertNotIn(BODY_MARKER, json.dumps(feed), "the type is named, the value never formatted")
        self.assertEqual((log, _refused()), ("", []), "nothing to say: the record is fine")
        self.assertEqual(self._listing(), ["qc-dbody.json", "qc-good.json", "qc-lbody.json"], "no aside")
        self._decide("qc-lbody", "approve")
        self._decide("qc-dbody", "deny")

    def test_a_deep_body_the_parser_returns_builds_a_card_named_by_type(self):
        self.r.write_hold("qc-good")
        self._write_raw_hold("qc-deep.json", DEEP_BODY_DOC % "qc-deep")
        with _parser_returning({'{"mid": "qc-deep"': {"mid": "qc-deep", "to": "web", "toId": SID, "frm": "api", "at": 1000,
                                                      "body": _deep_list()}}):
            feed, log = self._feed()
        held = {c["itemId"]: c for c in _asks(feed, "quarantine:")}
        self.assertEqual(sorted(held), ["quarantine:qc-deep", "quarantine:qc-good"])
        self.assertEqual(held["quarantine:qc-deep"]["blocked"]["body"], "list", "named by type: no repr of the document anywhere")
        self.assertLess(len(json.dumps(held["quarantine:qc-deep"])), 2000)
        self.assertEqual((log, _refused(), self._asides("qc-deep")), ("", [], []))
        self._decide("qc-deep", "approve")


class NoticeRowFaultsReachTheBell(_MCase):
    """extra5-1 (high), kernel-3, kernel-4 and extra6-3, one fix. The notices reader's say-so for a row it could not parse
    was a bare stderr line with no bell row, so a skipped row was silent to the user while the same PR rang the bell for
    every store-level fault (extra6-2: of the PR's four readers, the row-level one alone was silent); and a line that is
    not JSON at all, a JSON value that is not an object, a row with no op or no key, and a row whose op is not text were
    skipped with NOTHING said on either surface, then archived by the sweep, which rewrote the live file without them.
    Every skipped line is a fact now, said once per episode on stderr, and the facts new to the episode are ONE bell row
    for the file (never one per fact: sixty facts from one file filled the forty-row ring). Fails before over the
    35fad278c archive (the PR's parse skipped with stderr alone, and the unparseable population in silence); over
    bc88256e8 the type-wrong rows raised out of the build and the unparseable lines were skipped in silence too, a
    different red."""

    def test_a_bad_row_files_one_refused_row_naming_the_session_and_key_never_the_title(self):
        self.r.write_notice_rows([_good(self.now), dict(_good(self.now, key="sweep"), rev="not-a-rev", title=TITLE_MARKER, body=BODY_MARKER)])
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), [NOTICE_ID], "the good row's card stands; the bad row skips")
        self.assertIn("a row for key sweep carries a str where rev needs an integer", log)
        rows = _refused()
        self.assertEqual(len(rows), 1, "and the bell says so")
        self.assertIn("notices/%s.jsonl" % SID, rows[0], "the session")
        self.assertIn("sweep", rows[0], "and the key")
        self.assertIn("1 line skipped", rows[0])
        for marker in (TITLE_MARKER, BODY_MARKER, "not-a-rev"):
            self.assertNotIn(marker, rows[0] + log, "never a title, a body or a value's text")
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), log, len(_refused())), ([NOTICE_ID], "", 1), "said once per episode")
        self.r.write_notice_rows([_good(self.now, key="other")])       # the file moved: a fresh parse meets the same row
        feed, log = self._feed()
        self.assertEqual((len(self._notice_ids(feed)), log, len(_refused())), (2, "", 1), "the same fact re-files nothing")

    def test_many_facts_from_one_file_are_one_row_and_the_ring_keeps_its_other_rows(self):
        seeds = self._seed_refused(20)
        self.r.write_notice_rows([_good(self.now)] + [dict(_good(self.now, key="k%02d" % i), rev="x%d" % i) for i in range(60)])
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), [NOTICE_ID])
        self.assertEqual(log.count("needs an integer"), 60, "every fact on stderr")
        rows = _refused()
        self.assertEqual(len(rows), 21, "one row for the file beside the twenty that were there")
        for t in seeds:
            self.assertIn(t, rows, "an unrelated refusal was not evicted")
        new = [r for r in rows if r not in seeds]
        self.assertEqual(len(new), 1)
        self.assertIn("60 lines skipped", new[0])
        self.assertIn("keys k00, k01", new[0])
        self.assertIn(" more", new[0], "the keys past the fit are counted")
        self.assertLessEqual(len(new[0]), km.SYNC_NOTICE_FIT)

    _SHAPES = ['{"op": "post", "key": "torn", "rev": 1',                  # a truncated object: the tail a killed writer leaves
               '{"op": "post", "key": "garb", "rev": 1, "t": 1} MARK-GARBAGE-TEXT',   # trailing garbage after an object
               '[1, 2]', 'null', '"MARK-STRING-TEXT"', '42', '{}',           # a list, null, a string, a number, an empty object
               '{"key": "noop", "rev": 1, "t": 1}',                       # no op
               '{"op": "post", "rev": 1, "t": 1}',                         # no key
               '{"op": 7, "key": "opnum", "rev": 1, "t": 1}',              # an op that is a number: ADMITTED before this round
               '{"op": "post", "key": ["MARK-LISTKEY-TEXT"], "rev": 1, "t": 1}']   # a key that is a list

    _SAID = ("a line is not JSON (a torn line, or trailing garbage) and is not a notice row",
             "a line is a JSON list, not a notice row", "a line is a JSON null, not a notice row",
             "a line is a JSON str, not a notice row", "a line is a JSON int, not a notice row",
             "a row has no op", "a row has no key",
             "a row for key opnum carries a int where op needs text",
             "a row carries a key of type list where text is needed")

    def test_every_unparseable_shape_is_said_once_and_archived_by_the_sweep(self):
        self.r.write_notice_rows([dict(_good(self.now), t=self.now - 100), {"op": "expire", "key": "figure", "rev": 1, "t": self.now - 50},
                                  _good(self.now, key="keep")] + self._SHAPES)
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), ["notice:%s:keep:1" % SID], "the good row stands, every bad line skips")
        for s in self._SAID:
            self.assertEqual(log.count(s), 1, (s, log))
        self.assertEqual(log.count("romp-kernel:"), len(self._SAID), "each fact once: the two not-JSON lines are one fact")
        for marker in ("MARK-GARBAGE-TEXT", "MARK-STRING-TEXT", "MARK-LISTKEY-TEXT"):
            self.assertNotIn(marker, log + "".join(_refused()), "never the line's text")
        rows = _refused()
        self.assertEqual(len(rows), 1, "one bell row for the file")
        self.assertIn("%d lines skipped" % len(self._SHAPES), rows[0])
        moved, log2 = self._sweep()
        self.assertEqual(moved, 2, "the retired post and its expire row")
        self.assertEqual(log2, "", "the sweep's parse meets the same facts: quiet")
        ap = km._notice_archive_dir() / (SID + ".jsonl")
        arch = [json.loads(l) for l in ap.read_text().splitlines() if l.strip()]
        self.assertEqual([r["op"] for r in arch], ["post", "expire"] + ["skipped"] * len(self._SHAPES), "every skipped line archived")
        self.assertEqual([r["raw"] for r in arch if r["op"] == "skipped"], self._SHAPES, "each with its text, in file order")
        feed, log3 = self._feed()
        self.assertEqual((self._notice_ids(feed), log3, len(_refused())), (["notice:%s:keep:1" % SID], "", 1), "archived: the episode ends quietly")

    def test_the_sweep_alone_says_the_lines_before_it_archives_them(self):
        self.r.write_notice_rows([dict(_good(self.now), t=self.now - 100), {"op": "expire", "key": "figure", "rev": 1, "t": self.now - 50},
                                  "not json at all", '{"op": "post", "rev": 1}'])
        moved, log = self._sweep()
        self.assertEqual(moved, 2)
        self.assertIn("a line is not JSON", log, "said by the sweep's own parse, before the archive")
        self.assertIn("a row has no key", log)
        self.assertEqual(len(_refused()), 1)
        ap = km._notice_archive_dir() / (SID + ".jsonl")
        self.assertEqual([json.loads(l)["op"] for l in ap.read_text().splitlines() if l.strip()], ["post", "expire", "skipped", "skipped"])

    def test_an_op_that_is_not_text_skips_instead_of_being_admitted(self):
        self.r.write_notice_rows([_good(self.now), '{"op": 7, "key": "opnum", "rev": 1, "t": %d, "title": "%s"}' % (self.now, TITLE_MARKER)])
        with contextlib.redirect_stderr(io.StringIO()) as err:
            rows, rerr = km._notice_rows_unlocked(SID)
        self.assertEqual(([r["key"] for r in rows], rerr), (["figure"], ""), "the row is skipped, not admitted as an op nobody knows")
        self.assertIn("a row for key opnum carries a int where op needs text", err.getvalue())
        self.assertNotIn(TITLE_MARKER, err.getvalue())


class WriterRefusesOverAnUnreadableFile(_MCase):
    """regression-2: the writer-side reader (_notice_rows_unlocked) answered [] for a file it could not read, so
    expire_notice reported a false absence (`no notice with key`) over a notice that WAS present, post_notice minted a
    revision blind over the revisions it could not read, and the sweep read the file as nothing to keep. The reader
    answers (rows, error) now, the pair its callers already take from _notice_archive_rev_unlocked, and every caller
    refuses on it; an absent file stays ([], "") so a session's first post makes the file. Fails before over the
    35fad278c archive (the line the PR changed)."""

    def setUp(self):
        super().setUp()
        self.known = mock.patch.object(km, "_notice_session_known", lambda sid: True)
        self.known.start()
        self.addCleanup(self.known.stop)

    def test_expire_refuses_with_the_fault_not_the_absence(self):
        _skip_as_root(self)
        self.r.write_notice_rows([_good(self.now)])
        p = km._notice_path(SID)
        before = p.read_bytes()
        self.r.chmod(p, 0)
        with contextlib.redirect_stderr(io.StringIO()):
            row, err = km.expire_notice(SID, "figure", now=self.now)
        self.assertIsNone(row)
        self.assertIn("notices/%s.jsonl could not be read ([Errno 13] Permission denied)" % SID, err)
        self.assertIn("so nothing was retired", err)
        self.assertNotIn("no notice with key", err, "a fault, never a false absence")
        self.assertEqual(len(_refused()), 1, "and the bell carries the fault")
        self.r.chmod(p, 0o600)
        self.assertEqual(p.read_bytes(), before, "nothing appended")

    def test_post_refuses_over_a_file_it_cannot_read_and_appends_nothing(self):
        _skip_as_root(self)
        self.r.write_notice_rows([_good(self.now), _good(self.now, rev=2), _good(self.now, rev=3)])
        p = km._notice_path(SID)
        before = p.read_bytes()
        self.r.chmod(p, 0o222)                       # writable, unreadable: the blind mint's shape
        with contextlib.redirect_stderr(io.StringIO()):
            row, err = km.post_notice(SID, "figure", "The figure is ready", producer="figure", now=self.now)
        self.assertIsNone(row)
        self.assertIn("notices/%s.jsonl could not be read" % SID, err)
        self.assertIn("so no revision was assigned", err)
        self.r.chmod(p, 0o600)
        self.assertEqual(p.read_bytes(), before, "no revision minted blind: the file's bytes are unchanged")

    def test_the_sweep_leaves_the_unreadable_file_and_the_other_session_alone(self):
        _skip_as_root(self)
        self.r.write_notice_rows([dict(_good(self.now), t=self.now - 100), {"op": "expire", "key": "figure", "rev": 1, "t": self.now - 50}])
        self.r.write_notice_rows([_good(self.now, key="other")], sid=SID2)
        p, p2 = km._notice_path(SID), km._notice_path(SID2)
        before, before2 = p.read_bytes(), p2.read_bytes()
        self.r.chmod(p, 0)
        moved, log = self._sweep()
        self.assertEqual(moved, 0, "nothing archived from a file that could not be read")
        self.assertIn("notices/%s.jsonl could not be read" % SID, log)
        self.assertFalse((km._notice_archive_dir() / (SID + ".jsonl")).exists(), "the rows stay live")
        self.r.chmod(p, 0o600)
        self.assertEqual((p.read_bytes(), p2.read_bytes()), (before, before2), "both files untouched")
        moved, log = self._sweep()
        self.assertEqual(moved, 2, "readable again: the next pass archives them")

    def test_a_fresh_sessions_first_post_still_succeeds(self):
        with contextlib.redirect_stderr(io.StringIO()):
            row, err = km.post_notice(SID2, "first", "The first notice", producer="figure", now=self.now)
        self.assertEqual((err, row["rev"], row["key"]), (None, 1, "first"), "an absent file is nothing posted, not a fault")
        self.assertTrue(km._notice_path(SID2).exists())
        self.assertEqual(_refused(), [])


class AnIdTheBusCannotDecideNeverBecomesACard(_MCase):
    """correctness-1: round 2's undecidable-hold guard checked only that the record's mid was the file's stem, so a hold
    whose file name the bus's _safe_id refuses (a leading dot, a space, an out-of-class character, over 128 characters)
    built a needs-you card the bus then refused to decide, and since a hold is never dismissed the card could never
    leave the board. The guard is the bus's own predicate, the kernel's _safe_id (its twin, pinned identical to the
    bus's by tests/test_postal_self_host.py SafeIdTwins, which compares the regex pattern and the function body's AST
    and drives both over a probe set), never a third copy or a stem comparison: such a record is refused by shape and
    moved aside, said with the file named and never the body, and the head reads `could not be taken`, true of a record
    that parsed cleanly. Fails before over the 35fad278c archive (the guard let the six through, and F1 had removed the
    Clear escape; over bc88256e8 the cards were built too, but Clear all hid them)."""

    REFUSED = [".hidden", "with space", "bad*char", "x" * 129, "back\\slash", "héllo"]

    def test_seven_files_one_card_six_asides_and_the_good_hold_is_still_decidable(self):
        self.r.write_hold("qc-good")
        for stem in self.REFUSED:
            self._write_raw_hold(stem + ".json", _hold_doc(stem, body='"%s"' % BODY_MARKER))
        cards, log = self._cards()
        self.assertEqual(cards, ["quarantine:qc-good"], "no card the bus would refuse to decide")
        for stem in self.REFUSED:
            self.assertEqual(len(self._asides(stem)), 1, repr(stem))
            self.assertFalse((self.r.qdir / (stem + ".json")).exists())
        self.assertEqual(log.count("could not be taken (the message id is not one the bus can decide)"), 6, log)
        self.assertNotIn("could not be parsed", log, "a record that parsed is not said to have failed the parse")
        rows = _refused()
        self.assertEqual(len(rows), 1, "six asides of one kind in one listing: one row (correctness-3)")
        self.assertIn("6 files could not be taken and were moved aside", rows[0])
        self.assertNotIn(BODY_MARKER, log + "".join(rows), "the file is named, never the body")
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)
        sent, acted = [], []
        with mock.patch.object(km, "_bus_quarantine_act", lambda body: (acted.append(body), (True, ""))[1]):
            self._dispatch({"type": "quarantineDecision", "mid": "qc-good", "action": "approve", "sid": SID}, _client(sent))
        self.assertEqual(([b["mid"] for b in acted], [m for m in sent if m.get("type") == "quarantineRefused"]), (["qc-good"], []))

    def test_the_guard_is_the_bus_predicate_not_a_stem_comparison(self):
        src = inspect.getsource(km._held_records)
        self.assertIn("if not _safe_id(mid):", src, "the bus's own gate, the kernel's twin of it")
        self.assertIn("raise _HoldUndecidable(", src)
        self.assertTrue(issubclass(km._HoldUndecidable, ValueError), "the parse arm takes it")


class ADirectoryFaultIsSaidOnceForTheDirectory(_MCase):
    """correctness-3: both readers said a DIRECTORY-level fault once PER FILE on the bell, and the ring holds forty rows
    (SYNC_RING) of which the feed shows twenty, so one chmod on the notices or held-mail directory filled the ring with
    near-identical rows in one build and evicted every other notice the user had. The fold lives at the listing seams
    (_held_records, _notice_cards, _compact_notices) with a collector (_FaultFold): one listing that skips several files
    for one cause files ONE row naming the store, the fault and the count with as many names as fit; the per-file detail
    stays on stderr; the moved-aside rows fold the same way; the episode key stays the per-file fact, never the rendered
    row with its count. A single file's fault stays one row naming that file. Fails before over the 35fad278c archive
    (45 rows, the seeds evicted)."""

    def test_a_mode_400_held_mail_directory_over_45_files_is_one_row(self):
        _skip_as_root(self)
        names = ["qc-%02d" % i for i in range(45)]
        for n in names:
            self.r.write_hold(n)
        seeds = self._seed_refused(20)
        self.r.chmod(self.r.qdir, 0o400)             # lists, cannot be searched: every stat is refused
        cards, log = self._cards()
        self.assertEqual(cards, [])
        self.assertEqual(log.count("could not be read ([Errno 13] Permission denied)"), 45, "the detail per file, on stderr")
        rows = _refused()
        self.assertEqual(len(rows), 21, "one row for the directory's fault, the twenty seeds untouched")
        for t in seeds:
            self.assertIn(t, rows)
        new = [r for r in rows if r not in seeds][0]
        self.assertIn("45 files could not be read ([Errno 13] Permission denied)", new)
        self.assertIn("qc-00.json", new)
        self.assertIn(" more", new, "the names past the fit are counted")
        self.assertLessEqual(len(new), km.SYNC_NOTICE_FIT)
        cards, log = self._cards()
        self.assertEqual((cards, log, len(_refused())), ([], "", 21), "a second build over the same fault files nothing")
        self.r.chmod(self.r.qdir, 0o700)
        cards, log = self._cards()
        self.assertEqual((len(cards), log), (45, ""), "back")

    def test_a_mode_400_notices_directory_over_45_session_files_is_one_row(self):
        _skip_as_root(self)
        sids = ["11111111-2222-3333-4444-cccccccc%04d" % i for i in range(45)]
        for s in sids:
            self.r.write_notice_rows([_good(self.now)], sid=s)
        seeds = self._seed_refused(20)
        d = km._notice_dir()
        self.r.chmod(d, 0o400)
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), [])
        self.assertEqual(log.count("could not be read (stat failed: [Errno 13] Permission denied)"), 45)
        rows = _refused()
        self.assertEqual(len(rows), 21)
        new = [r for r in rows if r not in seeds][0]
        self.assertIn("notices: 45 session files could not be read (stat failed: [Errno 13] Permission denied)", new)
        self.assertIn(sids[0], new)
        self.assertLessEqual(len(new), km.SYNC_NOTICE_FIT)
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), log, len(_refused())), ([], "", 21))
        self.r.chmod(d, 0o700)
        feed, log = self._feed()
        self.assertEqual((len(self._notice_ids(feed)), log), (45, ""))

    def test_a_single_unreadable_file_still_files_its_own_row(self):
        _skip_as_root(self)
        self.r.write_notice_rows([_good(self.now)])
        self.r.write_notice_rows([_good(self.now, key="other")], sid=SID2)
        self.r.chmod(km._notice_path(SID), 0)
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), ["notice:%s:other:1" % SID2])
        rows = _refused()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].startswith("notices/%s.jsonl could not be read ([Errno 13] Permission denied)" % SID), rows[0])

    def test_several_asides_in_one_listing_are_one_row(self):
        self.r.write_hold("qc-good")
        for n in ("qc-torn-1", "qc-torn-2", "qc-torn-3"):
            self.r.write_torn_hold(n)
        cards, log = self._cards()
        self.assertEqual(cards, ["quarantine:qc-good"])
        self.assertEqual(log.count("could not be parsed ("), 3, "each aside on stderr with its own reason")
        rows = _refused()
        self.assertEqual(len(rows), 1)
        self.assertIn("3 files could not be parsed and were moved aside", rows[0])
        self.assertIn("qc-torn-1.json, qc-torn-2.json, qc-torn-3.json", rows[0])


class EpisodesEndOnASuccessfulRead(_MCase):
    """correctness-4, kernel-1 and kernel-2, one rule: an episode ends on any successful read of its subject, wherever
    that read happens. Three ways an episode opened and never closed, after which the same fault returning was silent
    on both surfaces for the life of the process: the notices listing had no per-file cleanup when the store went away
    (_end_notice_file_episodes now, the hold side's _end_hold_unreadable_episodes ported); _notice_rows returned on a
    memo HIT without clearing the file's episode; and _compact_notices never cleared the directory's episode after a
    clean listing, so with task tracking off, the sweep being the only reader, it never ended. Fails before over the
    35fad278c archive."""

    def test_a_notice_file_fault_is_said_again_after_the_store_is_recreated(self):
        _skip_as_root(self)
        self.r.write_notice_rows([_good(self.now)])
        d, p = km._notice_dir(), km._notice_path(SID)
        self.r.chmod(p, 0)
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), len(_refused())), ([], 1))
        os.chmod(p, 0o600)
        shutil.rmtree(d)
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), log, len(_refused())), ([], "", 1), "nothing posted, nothing said")
        self.assertEqual([k for k in km._state_fault_seen if k.startswith(str(d))], [], "the store's episodes ended with it")
        self.r.write_notice_rows([_good(self.now)])
        self.r.chmod(km._notice_path(SID), 0)
        feed, log = self._feed()
        self.assertEqual(len(_refused()), 2, "the same fault in the recreated store is a new episode")
        self.assertIn("could not be read", log)

    def test_a_fault_healed_with_the_stat_key_unchanged_is_said_again(self):
        _skip_as_root(self)
        self.r.write_notice_rows([_good(self.now)])
        d = km._notice_dir()

        def rows():
            with contextlib.redirect_stderr(io.StringIO()) as err:
                r = km._notice_rows(SID)             # the reader alone: no listing runs, so only the memo hit can end the episode
            return [x["key"] for x in r], err.getvalue()
        self.assertEqual(rows(), (["figure"], ""))
        self.r.chmod(d, 0o400)                       # the file's stat refuses; its stat key is untouched by the directory's mode
        r, log = rows()
        self.assertEqual(r, [])
        self.assertIn("could not be read (stat failed: [Errno 13] Permission denied)", log, "the fault is said...")
        self.assertEqual(len(_refused()), 1, "...once")
        self.r.chmod(d, 0o700)
        self.assertEqual(rows(), (["figure"], ""), "healed: the memo serves the unchanged key, a proved clean read")
        self.assertNotIn(str(km._notice_path(SID)), km._state_fault_seen, "the memo hit ended the episode")
        self.r.chmod(d, 0o400)
        rows()
        self.assertEqual(len(_refused()), 2, "the fault that returns is said again")
        self.r.chmod(d, 0o700)
        with contextlib.redirect_stderr(io.StringIO()):
            os.utime(km._notice_path(SID))           # the control the refuters ran: a moved stat key misses the memo and re-says too
        self.r.chmod(d, 0o400)
        rows()
        self.assertEqual(len(_refused()), 2, "one episode still open, nothing new to say")

    def test_the_sweep_alone_ends_a_directory_episode(self):
        _skip_as_root(self)
        (self.r.state / km.TASK_TRACKING_FILE).write_text(json.dumps({"enabled": False}))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(km._task_tracking_on(), "the scene: tracking off, the sweep is the directory's only reader")
        self.r.write_notice_rows([_good(self.now)])
        d = km._notice_dir()
        self.r.chmod(d, 0)
        moved, log = self._sweep()
        self.assertEqual((moved, len(_refused())), (0, 1))
        self.assertIn("the notices directory (notices) could not be listed", log)
        self.r.chmod(d, 0o700)
        moved, log = self._sweep()
        self.assertEqual((moved, log), (0, ""))
        self.assertNotIn(str(d), km._state_fault_seen, "a clean listing by the sweep ends the episode")
        self.r.chmod(d, 0)
        moved, log = self._sweep()
        self.assertEqual(len(_refused()), 2, "the fault that returns is said again")
        os.chmod(d, 0o700)
        self.r.chmod(km._notice_path(SID), 0)
        self._sweep()
        self.assertEqual(len(_refused()), 3, "a file the sweep cannot read opens its own episode")
        os.chmod(km._notice_path(SID), 0o600)
        shutil.rmtree(d)
        moved, log = self._sweep()
        self.assertEqual((moved, log, [k for k in km._state_fault_seen if k.startswith(str(d))]), (0, "", []),
                         "a removed store ends every episode under it, its own included")


class AFileNameForgesNoLogOrBellLine(_MCase):
    """extra8-2: log and bell injection through a file name. The hold say-so interpolated the file name from the directory
    listing raw into the stderr line and the bell row, so a name carrying a newline forged a second `romp-kernel:` line
    and split the bell row, and a long name put a row past SYNC_NOTICE_FIT (the widest name the bus itself writes, 128
    characters plus `.json`, already overran it). A name whose stem clears _safe_id (the bus's) renders as it is; any
    other renders with every line boundary of _HDR_BREAK_RE replaced (a fixed phrase would not do: the name IS the key
    the user needs to act), and the width lives in _hold_bell_text, which shortens a long name before the reason goes.
    The notices half takes the same gate on the session id the listing supplies. With correctness-1 landed a name with a
    newline is refused as undecidable, so the moved-aside head is the row under test; a mode-000 file with such a name
    tests the read-fault head. Fails before over the 35fad278c archive (a forged second line and an over-wide row)."""

    def _one_line_one_row(self, log):
        lines = log.splitlines()
        self.assertEqual(len(lines), 1, "one stderr line: the forged prefix inside the name starts no second one")
        self.assertTrue(lines[0].startswith("romp-kernel: held mail: qc\ufffdromp-kernel: FORGED"), lines[0])
        self.assertIsNone(km._HDR_BREAK_RE.search(lines[0]), "the line boundary is replaced, not written")
        rows = _refused()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(km._HDR_BREAK_RE.search(rows[0]), "no line boundary in the bell row")
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)
        return rows[0]

    def test_a_name_with_a_newline_forges_no_second_line(self):
        stem = "qc\nromp-kernel: FORGED-LINE-MARKER"
        self._write_raw_hold(stem + ".json", _hold_doc(stem))
        cards, log = self._cards()
        self.assertEqual(cards, [])
        self.assertEqual(len(list(self.r.qdir.iterdir())), 1, "moved aside under its own name")
        self._one_line_one_row(log)
        self.assertNotIn("\nromp-kernel: FORGED", log)

    def test_a_name_with_a_line_separator_the_same_way(self):
        stem = "qc romp-kernel: FORGED-LINE-MARKER"
        self._write_raw_hold(stem + ".json", _hold_doc(stem))
        cards, log = self._cards()
        self.assertNotIn(" ", log)
        self._one_line_one_row(log)

    def test_an_unreadable_file_with_such_a_name_is_said_on_one_line(self):
        _skip_as_root(self)
        stem = "qc\nromp-kernel: FORGED-LINE-MARKER"
        p = self._write_raw_hold(stem + ".json", _hold_doc(stem))
        self.r.chmod(p, 0)
        cards, log = self._cards()
        self.assertTrue(p.exists(), "a read fault: left in place")
        row = self._one_line_one_row(log)
        self.assertIn("could not be read; skipped and left in place for the next build", row)
        self.assertIn("(Errno 13] Permission denied)"[1:], row)

    def test_the_widest_name_the_bus_writes_fits_and_a_longer_one_is_shortened(self):
        stem = "a" * 128                             # clears _safe_id: the widest mid the bus writes, 133 characters with .json
        self._write_raw_hold(stem + ".json", '{"mid": "%s", "to": "web", "at": 10' % stem)
        cards, log = self._cards()
        self.assertEqual(len(self._asides(stem)), 1, "a parse fault: moved aside")
        rows = _refused()
        self.assertEqual(len(rows), 1)
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT, rows[0])
        self.assertIn("could not be parsed", rows[0])
        long = "n" * 300 + ".json"
        row = km._hold_bell_text("held mail: %s could not be parsed" % long, "moved aside with the suffix .corrupt-20260920T000000Z",
                                 "the held messages that could be read are on the board", "Expecting value", name=long)
        self.assertLessEqual(len(row), km.SYNC_NOTICE_FIT)
        self.assertIn("n" * 40 + "…", row, "the name is shortened with an ellipsis...")
        self.assertIn("(Expecting value)", row, "...before the reason goes")
        plain = RELAYED_MID + ".json"
        row = km._hold_bell_text("held mail: %s could not be parsed" % plain, "moved aside with the suffix .corrupt-20260920T000000Z",
                                 "the held messages that could be read are on the board", "Expecting value", name=plain)
        self.assertIn(plain, row, "a relayed message's real mid renders whole")
        self.assertLessEqual(len(row), km.SYNC_NOTICE_FIT)
        self.assertEqual(km._hold_name_text("qc-1.json"), "qc-1.json")
        self.assertEqual(km._hold_name_text("q\nc.json"), "q�c.json")

    def test_a_session_file_name_that_is_not_a_uuid_is_rendered_safely(self):
        forged = "s\nromp-kernel: FORGED-LINE-MARKER"
        self.r.write_notice_rows([dict(_good(self.now), rev="x")], sid=forged)
        feed, log = self._feed()
        lines = log.splitlines()
        self.assertEqual(len(lines), 1, log)
        self.assertTrue(lines[0].startswith("romp-kernel: notices/s\ufffdromp-kernel: FORGED"), lines[0])
        rows = _refused()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(km._HDR_BREAK_RE.search(rows[0]))
        self.assertEqual(km._notice_sid_text(SID), SID, "a session id clears the gate and renders as it is")


class ClearAllAnswersTruthfully(_MCase):
    """extra7-1 (upgrading regression-1 from a silent click to visible and false): F1 made the footer's Clear all unable
    to clear anything on a board of holds alone, but the handler still told the chat app that every composer citation
    chip was gone (dropCitationsAll, unconditionally) and sent the pane nothing. _clear_all reports the ids it actually
    wrote (`written`), the handler drops only those ids' chips (the per-id dropCitation the chat app already handles,
    subtrees included), and a press that cleared nothing, or fewer than it asked, is answered on the delivering socket
    with a clearAllResult frame naming the held messages awaiting a decision (a refusal when nothing moved, a count
    otherwise); a press that cleared all it asked answers nothing. The kernel does not change which ids _clear_all
    declines. Fails before over the 35fad278c archive (dropCitationsAll and no answer; over bc88256e8 the press cleared
    the holds, a different behaviour)."""

    def setUp(self):
        super().setUp()
        self.sent, self.apps = [], []
        self.client = _client(self.sent)
        self.sends = mock.patch.object(km, "_send_to_app", lambda app, msg: self.apps.append((app, msg)))
        self.sends.start()
        self.addCleanup(self.sends.stop)

    def _results(self):
        return [m for m in self.sent if m.get("type") == "clearAllResult"]

    def test_a_mixed_board_drops_only_the_cleared_chip_and_reports_the_count(self):
        self.r.write_hold("qc-hold-1")
        self.r.write_notice_rows([_good(self.now)])
        self._dispatch({"type": "clearAll"}, self.client)
        self.assertEqual([(r["id"], r["op"]) for r in self.r.ledger_rows()], [(NOTICE_ID, "clear")], "one row: the card that can be cleared")
        chat = [m for a, m in self.apps if a == "chat"]
        self.assertEqual([m["type"] for m in chat], ["dropCitation"], "the chip drop follows the write: no dropCitationsAll")
        self.assertEqual(chat[0]["itemId"], NOTICE_ID)
        self.assertIn(NOTICE_ID, chat[0]["itemIds"])
        self.assertEqual([m for m in self.sent if m.get("type") == "err"], [])
        self.assertEqual([m for m in self._results() if not m["ok"]], [], "no refusal: the ordinary card cleared")
        res = self._results()
        self.assertEqual(len(res), 1, "the count the pane can show")
        self.assertEqual((res[0]["cleared"], res[0]["left"], res[0]["held"]), (1, 1, 1))
        self.assertIn("1 held message awaiting your decision", res[0]["text"])
        feed, _ = self._feed()
        self.assertEqual(([c["itemId"] for c in _asks(feed, "quarantine:")], self._notice_ids(feed)), (["quarantine:qc-hold-1"], []))

    def test_a_board_of_holds_alone_is_refused_with_nothing_written_and_no_chip_drop(self):
        self.r.write_hold("qc-hold-1")
        self.r.write_hold("qc-hold-2")
        self._dispatch({"type": "clearAll"}, self.client)
        self.assertEqual(self.r.ledger_rows(), [], "nothing written")
        self.assertEqual([m for a, m in self.apps if a == "chat"], [], "no chip drop at all")
        res = self._results()
        self.assertEqual(len(res), 1, "the pane hears the refusal")
        self.assertEqual((res[0]["ok"], res[0]["cleared"], res[0]["held"]), (False, 0, 2))
        self.assertIn("nothing was cleared", res[0]["text"])
        self.assertIn("2 held messages awaiting your decision", res[0]["text"])
        self.assertEqual([m for m in self.sent if m.get("type") == "err"], [])

    def test_a_board_cleared_whole_answers_nothing(self):
        self.r.write_notice_rows([_good(self.now)])
        self._dispatch({"type": "clearAll"}, self.client)
        self.assertEqual(self._results(), [], "success is silent: the next payload is the answer")
        self.assertEqual([m["type"] for a, m in self.apps if a == "chat"], ["dropCitation"])

    def test_clear_all_reports_the_ids_it_wrote(self):
        written = []
        self.assertEqual(km._clear_all(["quarantine:qc-hold-1", NOTICE_ID, ""], written=written), {}, "the return every door reads stands")
        self.assertEqual(written, [NOTICE_ID], "the hold's id is declined, the empty one dropped, the card's written")
        written = []
        self.assertEqual(km._clear_all(["quarantine:qc-hold-1"], written=written), {})
        self.assertEqual(written, [])


class TheActionDoorTellsAFaultFromAnAbsence(_MCase):
    """fresh-1: the notice card's action door answered a click with `that notice is gone` when the kernel could not READ
    that session's notice file, so a gesture on a card still on the board was told the card did not exist, reported
    absent in the gesture layer. _notice_rows_or_fault answers (rows, fault), the unproved-versus-absent split the hold
    reader has, and both of the door's reads take it: a fault is answered in its own words and runs nothing, the gone
    answer stays for a genuinely absent row, and an unreadable store at the second read (the acted-mark check) never
    lets a dismissOnAction card's action run twice. The answer rides the door's existing frame (noticeActionDone), so the
    pane learns nothing new. Fails before over the bc88256e8 archive as over 35fad278c: the door's fold is the base's
    too, so both give the same false answer."""

    ACTION = {"label": "Retry", "route": "/send", "body": {"text": "please retry the sweep"}}

    def setUp(self):
        super().setUp()
        self.delivered = []
        self.deliver = mock.patch.object(km, "_deliver_text", lambda target, text, plain=False: (self.delivered.append((target, text)), (True, "", False))[1])
        self.deliver.start()
        self.addCleanup(self.deliver.stop)

    def _card(self, dismiss=False):
        self.r.write_notice_rows([dict(_good(self.now), actions=[self.ACTION], dismissOnAction=dismiss)])

    def _click(self, iid=NOTICE_ID):
        with contextlib.redirect_stderr(io.StringIO()):
            return km._notice_action(iid, "/send", dict(self.ACTION["body"]))

    def test_an_unreadable_file_answers_the_fault_and_runs_nothing(self):
        _skip_as_root(self)
        self._card()
        p = km._notice_path(SID)
        before = p.read_bytes()
        self.r.chmod(p, 0)
        ok, err = self._click()
        self.assertFalse(ok)
        self.assertIn("could not be read just now", err)
        self.assertIn("Permission denied", err)
        self.assertNotIn("gone", err, "a fault, never an absence")
        self.assertEqual(self.delivered, [], "the action did not run")
        self.r.chmod(p, 0o600)
        self.assertEqual(p.read_bytes(), before, "the file is untouched")
        ok, err = self._click()
        self.assertEqual((ok, err, len(self.delivered)), (True, "", 1), "readable again: the click lands")

    def test_an_unlistable_directory_the_same_way(self):
        _skip_as_root(self)
        self._card()
        self.r.chmod(km._notice_dir(), 0)
        ok, err = self._click()
        self.assertEqual((ok, self.delivered), (False, []))
        self.assertIn("could not be read just now (stat failed", err)

    def test_a_genuinely_absent_row_still_answers_gone(self):
        self._card()
        self.assertEqual(self._click("notice:%s:gone:1" % SID), (False, "that notice is gone"))
        self.assertEqual(self._click("notice:%s:figure:9" % SID), (False, "that notice is gone"))

    def test_a_dismiss_on_action_card_runs_exactly_once_when_the_second_read_faults(self):
        self._card(dismiss=True)
        real = km._notice_rows_or_fault

        def faulting_second_read():
            calls = []

            def read(sid, fold=None):
                calls.append(sid)
                if len(calls) == 2:
                    return [], "[Errno 5] Input/output error"
                return real(sid, fold)
            return mock.patch.object(km, "_notice_rows_or_fault", read)
        with faulting_second_read():
            ok, err = self._click()
        self.assertEqual((ok, self.delivered), (False, []), "a fault at the acted-mark check never runs the action")
        self.assertIn("could not be read just now", err)
        self.assertEqual(self._click(), (True, ""), "the store reads: the action runs")
        self.assertEqual(len(self.delivered), 1)
        with faulting_second_read():
            ok, err = self._click()
        self.assertEqual((ok, len(self.delivered)), (False, 1), "the spent card's action never runs a second time over a fault")
        self.assertIn("could not be read just now", err)
        self.assertEqual(self._click(), (False, "that card's action ran already"))
        self.assertEqual(len(self.delivered), 1)


# The remotes popover's DOM stub, the shape tests/test_remotes_panel_render.py executes the same served JS against (that
# module's harness is module-level state beside a second kernel load, so it is not imported here): enough of a document,
# a window, a fetch and a storage for the panel IIFE to wire itself up, open, poll /tunnels once and render. Every
# element the panel asks for exists; innerHTML is a string sink the measurement reads back, never parsed.
PANEL_STUB = r"""
'use strict';
function mkEl(id){var cls=new Set();return {id:id,hidden:true,_text:'',title:'',style:{},value:'',children:[],_html:'',
  get className(){return Array.from(cls).join(' ');},
  set className(v){cls.clear();String(v).split(/\s+/).filter(Boolean).forEach(function(c){cls.add(c);});},
  get innerHTML(){return this._html;}, set innerHTML(v){this._html=String(v);this.children=[];},
  get textContent(){return this._text;}, set textContent(v){this._text=v;this.children=[];},
  classList:{add(c){cls.add(c);},remove(c){cls.delete(c);},toggle(c,v){if(v===undefined)v=!cls.has(c);if(v)cls.add(c);else cls.delete(c);return v;},contains(c){return cls.has(c);}},
  appendChild(c){this.children.push(c);return c;}, querySelector(){return null;}, querySelectorAll(){return [];},
  addEventListener(){}, removeEventListener(){}, setAttribute(){}, getAttribute(){return null;}, focus(){}, select(){}, remove(){},
  get firstChild(){return this.children[0]||null;}};}
const ELS={};
const document={getElementById(id){if(!ELS[id])ELS[id]=mkEl(id);return ELS[id];},createElement(t){return mkEl(t);},
  querySelector(){return null;},querySelectorAll(){return [];},addEventListener(){},body:mkEl('body')};
const localStorage={getItem(){return null;},setItem(){}};
const TUNNELS=__TUNNELS__;
function fetch(url,opts){
  if(opts&&opts.method==='POST')return Promise.resolve({ok:true,json(){return Promise.resolve({ok:true});}});
  var body=url.indexOf('/ssh-hosts')>=0?{hosts:['TESTHOST']}:(url.indexOf('/tunnels/pairs')>=0?{pairs:[],hosts:{}}:TUNNELS);
  return Promise.resolve({ok:true,status:200,json(){return Promise.resolve(body);}});}
function alert(){}
const setTimeout_=setTimeout;
const window={_l:{},addEventListener(k,f){(this._l[k]=this._l[k]||[]).push(f);},location:{reload(){}}};
const errors=[];
const console={error(){errors.push(Array.prototype.map.call(arguments,String).join(' '));},log(){},warn(){}};
__PANEL_JS__
ELS['rnet-back'].hidden=false;
window.__rompOpenNet&&window.__rompOpenNet();
function collect(el){var s=String(el.className||'')+' '+String(el.innerHTML||el.textContent||'');
  (el.children||[]).forEach(function(c){s+=' '+collect(c);});return s;}
setTimeout_(function(){setTimeout_(function(){var list=ELS['rnet-list'];
  process.stdout.write(JSON.stringify({rows:list.children.map(collect),errors:errors}),function(){process.exit(0);});},40);},60);
"""

PANEL_TUNNELS = {
    "tunnels": [{"host": "TESTHOST", "kernelPort": 29855, "localPort": 51000, "busPort": 51001, "checkin": False,
                 "checkinPeer": False, "hasToken": True, "status": "up", "detail": "", "sids": [SID], "trust": "directed",
                 "kernelSha": "abc1234", "localSha": "abc1234", "outOfDate": False, "behindBy": 0, "aheadBy": 0,
                 "kernelDate": "", "gaveUp": False, "fails": 0, "maxTries": 5}],
    "known": [],
    "peersMode": True,
}
HOLD_GIST = "SECRET-HOLD-GIST-TEXT"                  # an ordinary hold's gist rides the hover title, as it always did
FAULT_TEXT = "held mail cannot be listed (PermissionError, errno 13: Permission denied)"   # the bus's _hold_fault_row text


def _hold_row(at_host, mid, gist=HOLD_GIST):
    return {"mid": mid, "frm": "api", "to": "web", "origin": "", "at": 1000, "gist": gist, "atHost": at_host}


def _fault_row(at_host, fault=FAULT_TEXT, **extra):
    """The contract's row as the viewing kernel receives it: `fault` beside the ordinary keys, empty, `atHost` stamped by
    remote_holds and `via` by the one hop. `extra` overrides fields with markers so a case can pin that nothing of the
    row but the fault is rendered."""
    row = {"fault": fault, "mid": "", "frm": "", "to": "", "origin": "", "at": 0, "gist": "", "atHost": at_host, "via": "TESTHOST"}
    row.update(extra)
    return row


class AHoldersFaultRowReachesTheViewingPanel(unittest.TestCase):
    """extra5-3, the kernel half. A holder whose held-mail store cannot be listed answers the exchange one row carrying
    `fault` (the bus's _hold_fault_row) in place of its holds; the kernel's _bus_remote_holds proxies the bus's /peers
    snapshot through unfiltered, and the served panel JS (the Held for approval elsewhere block of _LANDING_REMOTES_JS)
    must read that key FIRST: the faulted host gets a line naming the fault (its kind and errno text, never a gist or a
    record's text) and saying it is retried on the next refresh, is never counted as a held message, and the other hosts'
    rows and the section stand. Before this the panel counted the fault row as one message held for your approval:
    visible and false on the viewing machine, where the section had simply vanished before the bus's fix.

    The real panel JS runs in node against PANEL_STUB, the idiom of tests/test_remotes_panel_render.py; no state root is
    touched, so this is a plain TestCase. Synthetic only: TESTHOST and invented host names, placeholder texts."""

    def _render(self, remote_holds):
        tunnels = dict(PANEL_TUNNELS, remoteHolds=remote_holds)
        js = PANEL_STUB.replace("__PANEL_JS__", km._LANDING_REMOTES_JS).replace("__TUNNELS__", json.dumps(tunnels))
        p = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, "the panel JS crashed:\n%s" % p.stderr[-2000:])
        out = json.loads(p.stdout or "{}")
        self.assertEqual(out.get("errors"), [], "the panel names a failed refresh in the console; there must be none")
        rows = out["rows"]
        heads = [i for i, r in enumerate(rows) if "Held for approval elsewhere" in r]
        section = rows[heads[0] + 1:] if heads else []
        return rows, heads, [r for r in section if "rnet-khead" not in r]

    def _host_rows(self, section, host):
        return [r for r in section if "<b>%s</b>" % host in r]

    def test_a_faulted_holder_gets_a_fault_line_and_the_other_holders_rows_stand(self):
        rows, heads, section = self._render([
            _hold_row("HOLDER-A", "px-1"), _hold_row("HOLDER-A", "px-2"),
            # the contract's fields are empty; markers here pin that the panel renders nothing of a fault row but its fault
            _fault_row("HOLDER-B", frm="SECRET-FRM-MARKER", to="SECRET-TO-MARKER", gist="SECRET-FAULT-GIST-MARKER", mid="SECRET-MID-MARKER"),
        ])
        self.assertEqual(len(heads), 1, "the section renders once:\n%s" % "\n".join(rows))
        a = self._host_rows(section, "HOLDER-A")
        self.assertEqual(len(a), 1, section)
        self.assertIn("2 messages held for your approval", a[0])
        self.assertIn(HOLD_GIST, a[0], "an ordinary hold's gist still rides its hover title")
        b = self._host_rows(section, "HOLDER-B")
        self.assertEqual(len(b), 1, "the faulted holder has exactly one line:\n%s" % "\n".join(section))
        self.assertIn("held mail could not be read: " + FAULT_TEXT, b[0])
        self.assertIn("retried on the next refresh", b[0])
        self.assertNotIn("held for your approval", b[0], "a fault row is not a held message and is never counted as one")
        joined = "\n".join(rows)
        for marker in ("SECRET-FRM-MARKER", "SECRET-TO-MARKER", "SECRET-FAULT-GIST-MARKER", "SECRET-MID-MARKER"):
            self.assertNotIn(marker, joined, "nothing of a fault row but its fault is rendered")
        self.assertEqual(len(section), 2, "one line per host, nothing else in the section:\n%s" % "\n".join(section))

    def test_a_fault_row_alone_still_renders_the_section_and_no_rows_render_none(self):
        rows, heads, section = self._render([_fault_row("HOLDER-B")])
        self.assertEqual(len(heads), 1, "the section stands on a fault row alone: this is the line that vanished before:\n%s" % "\n".join(rows))
        self.assertEqual(len(section), 1, section)
        self.assertIn("<b>HOLDER-B</b>", section[0])
        self.assertIn(FAULT_TEXT, section[0])
        self.assertNotIn("message", section[0].split("</b>", 1)[1].split("</span></span>")[0].replace("held mail", ""),
                         "no count is claimed for a holder whose store could not be read")
        rows, heads, section = self._render([])
        self.assertEqual((heads, section), ([], []), "no holds and no fault: no section, as before")

    def test_the_fault_text_is_escaped_and_a_fault_that_is_not_text_is_named_by_type(self):
        rows, heads, section = self._render([
            _fault_row("HOLDER-B", fault='<b>forged</b> "quoted" & <img src=x onerror=alert(1)>'),
            _fault_row("HOLDER-C", fault={"errno": 13}),
            _fault_row("HOLDER-C", fault={"errno": 13}),      # the same fault twice (a direct row and a relayed one): one line
        ])
        self.assertEqual(len(heads), 1)
        b = self._host_rows(section, "HOLDER-B")
        self.assertEqual(len(b), 1, section)
        self.assertIn("&lt;b&gt;forged&lt;/b&gt; &quot;quoted&quot; &amp; &lt;img", b[0], "esc on the interpolated fault")
        self.assertNotIn("<img", b[0])
        c = self._host_rows(section, "HOLDER-C")
        self.assertEqual(len(c), 1, "one line per distinct fault per host:\n%s" % "\n".join(section))
        self.assertIn("a fault of type object", c[0])
        self.assertNotIn("[object Object]", c[0])
        self.assertNotIn("errno", c[0], "a value that is not text is named by its type, never formatted")


if __name__ == "__main__":
    unittest.main()
