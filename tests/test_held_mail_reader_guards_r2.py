#!/usr/bin/env python3
"""The held-mail readers bundle, review round 2: the kernel-side fixes the closing round found, each pinned by a case that
fails over a git archive of the round 1 fix commit and passes here. The rule is the bundle's, as round 1 stated it: a
reader that cannot parse must not report absent and must not take down callers that had nothing to do with the bad row;
skip the row, name the session and the key in the log, keep the board.

The cases: a notice line that is not UTF-8 skips and is said once instead of raising UnicodeDecodeError out of every
feed build, and a file saved with a UTF-8 BOM keeps its first row; the rows split on every line boundary main split on,
so a file with CR endings reads whole (the closing pass); a notices directory or file the kernel cannot list,
stat or read is said once per episode on the bell instead of drawing a clean board; a hold nested past the interpreter's
limit (RecursionError; on the free-threaded Python 3.14, whose parser takes the depth, the bare deep list is moved aside
as a non-object and a record whose body is the deep list keeps its card with the body named by its type, since a record
that parsed is never refused for a field's type: the manager's round 1, extra8-1), a hold whose record names another
message id than its file, and a dangling .json symlink are moved aside and said like the other records that cannot be
parsed; the said-once registry's prune reads a snapshot, so two overlapping builds cannot raise RuntimeError out of one
another, and a removed directory ends the episodes under it; Undo and the two ledger counts pass over an older ledger's
hold rows; and the type-wrong row's log line names the key only when it is a valid key. Two classes from the manager's
round 1 ride here beside the classes they pin the neighbours of: the card's coercion of a hold's fields of another type
(tests-2) and the writer-side say-once for a notice file the sweep cannot read (tests-3).

The harness is the round 1 module's (tests/test_held_mail_reader_guards.py: its hermetic root, its private synthetic sid,
its fixtures), imported the way the api-health modules share theirs. Synthetic only: TESTHOST, placeholder ids, invented
text; every root writes `off` into <root>/session-hosts (repo rule, 2026-09-11) and no goals are minted."""
import contextlib
import io
import json
import os
import shutil
import sys
import threading
from unittest import mock

from tests.test_held_mail_reader_guards import (_Case, _asks, _client, _good, _refused, _skip_as_root, _writer_rows, km,   # noqa: E402
                                                NOTICE_ID, SID)

SID2 = "11111111-2222-3333-4444-bbbbbbbb0920"      # a second PRIVATE synthetic sid: the file beside the good one
UTF8_BOM = b"\xef\xbb\xbf"
DEPTH = 100000                                     # past every Python's recursion limit; the free-threaded 3.14 parser takes it
DEEP = "[" * DEPTH + "]" * DEPTH                   # the document, as a bare list
DEEP_BODY_DOC = '{"mid": "%s", "to": "web", "at": 1000, "body": ' + DEEP + "}"   # the document as a record's body


def _deep_list(depth=DEPTH):
    """The value the free-threaded 3.14 parser returns for DEEP, built iteratively: nothing here parses or formats it."""
    v = []
    for _ in range(depth):
        v = [v]
    return v


@contextlib.contextmanager
def _parser_returning(values):
    """json.loads as the free-threaded Python 3.14 answers a document nested past its predecessors' limit, on every
    Python: a text that starts with one of `values`' keys returns that value, and every other text goes to the real
    parser (the good hold beside it). The kernel calls json.loads through the module, so the patch on the module's
    attribute is what its reader sees; every other caller in the block is delegated to the real parser unchanged."""
    real = json.loads

    def loads(text, *a, **kw):
        for prefix, value in values.items():
            if text.startswith(prefix):
                return value
        return real(text, *a, **kw)
    with mock.patch.object(json, "loads", loads):
        yield


class _R2Case(_Case):
    """The round 1 harness plus the SDK backend's once-per-process import notice absorbed up front: it lands on the first
    build_feed of a process (claude_agent_sdk is absent in the test venv and on CI), so a case that asserts on its captured
    stderr must not depend on which case built first (the round 1 module's order dependence, found this round)."""

    def setUp(self):
        super().setUp()
        with contextlib.redirect_stderr(io.StringIO()):
            km._sdk()

    def _notice_ids(self, feed):
        return [c["itemId"] for c in _asks(feed, "notice:")]

    def _write_bytes(self, sid, payload):
        d = km._notice_dir()
        d.mkdir(parents=True, exist_ok=True)
        km._notice_path(sid).write_bytes(payload)


class NoticeLineNotUtf8(_R2Case):
    """Both readers decoded the whole file with read_text under `except OSError`; UnicodeDecodeError is a ValueError, so
    one Latin-1 byte in one row, or a file saved as UTF-16, raised out of _notice_rows, the projection, build_feed, the
    push cycle, GET /feed.json and the sweep, and every session's cards went with it. The parse takes the bytes now and
    decodes each line on its own: a line that is not UTF-8 skips, is said once per episode (never its text), rides the
    sweep's archive with its bytes escaped, and the other rows and the other sessions stand. Red over the 4383cc9af
    archive on the defect itself, the UnicodeDecodeError out of the build (two cases) and out of the sweep (the third);
    the first case's pair read through the writer's reader is the manager's round 1 adaptation (_writer_rows), green
    over 35fad278c and pinning nothing there (LENS ONE)."""

    def test_one_latin1_byte_in_one_row_skips_that_row_and_keeps_the_board(self):
        bad = ('{"op": "post", "key": "menu", "rev": 2, "t": %d, "at": %d, "title": "caf\xe9 MARKER-ROW-TEXT", '
               '"producer": "menu", "needsYou": true}\n' % (self.now - 5, self.now - 5)).encode("latin-1")
        self._write_bytes(SID, (json.dumps(_good(self.now)) + "\n").encode() + bad)
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), [NOTICE_ID], "the good row's card stands; the damaged row skips")
        self.assertEqual(log.count("romp-kernel:"), 1, log)
        self.assertIn("notices/%s.jsonl: a line is not UTF-8 text; the row is skipped" % SID, log)
        self.assertNotIn("MARKER-ROW-TEXT", log, "never the line's text")
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), log), ([NOTICE_ID], ""), "said once per episode")
        with contextlib.redirect_stderr(io.StringIO()):
            rows, err = _writer_rows(SID)              # the rows on either shape: the pair read is an adaptation (LENS ONE)
        self.assertEqual([r["key"] for r in rows], ["figure"], "the writer's reader skips it too")
        self.assertEqual(err, "", "a file that read is no fault")

    def test_a_utf16_file_beside_a_good_one_takes_only_its_own_session_off(self):
        self.r.write_notice_rows([_good(self.now)])
        self._write_bytes(SID2, (json.dumps(_good(self.now, key="other")) + "\n").encode("utf-16"))
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), [NOTICE_ID], "one session's file, one session's cards")
        self.assertIn("notices/%s.jsonl: a line is not UTF-8 text" % SID2, log)
        self.assertNotIn("notices/%s.jsonl" % SID, log, "the good session's file is not named")
        self.assertEqual(log.count("a line is not UTF-8 text"), 1, "one fact for the file, however many lines fail")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._compact_notices(self.now), 0, "the sweep reads past it")

    def test_the_sweep_archives_the_damaged_line_with_its_bytes_escaped(self):
        bad = b'{"op": "post", "key": "menu", "rev": 1, "t": 5, "title": "caf\xe9"}\n'
        self._write_bytes(SID, (json.dumps(dict(_good(self.now), t=self.now - 100)) + "\n").encode()
                          + (json.dumps({"op": "expire", "key": "figure", "rev": 1, "t": self.now - 50}) + "\n").encode() + bad)
        with contextlib.redirect_stderr(io.StringIO()):
            moved = km._compact_notices(self.now)
        self.assertEqual(moved, 2, "the retired post and its expire row")
        ap = km._notice_archive_dir() / (SID + ".jsonl")
        rows = [json.loads(l) for l in ap.read_text().splitlines() if l.strip()]
        self.assertEqual([r["op"] for r in rows], ["post", "expire", "skipped"], "the damaged line rides the same block")
        self.assertEqual(rows[-1]["raw"], '{"op": "post", "key": "menu", "rev": 1, "t": 5, "title": "caf\\xe9"}', "its bytes kept as escapes")
        self.assertEqual(km._notice_path(SID).read_bytes(), b"", "the live file is rewritten without it")


class NoticeFileWithABom(_R2Case):
    """json.loads refuses a line that begins with U+FEFF, so the first row of a file an editor saved with a BOM was skipped
    as a non-JSON line with nothing said; the parse drops a leading BOM before the first line. Red over the 4383cc9af
    archive at the card list (the first row skipped); the pair read through the writer's reader is the manager's round 1
    adaptation (_writer_rows), green over 35fad278c and pinning nothing there (LENS ONE)."""

    def test_the_first_row_of_a_bom_prefixed_file_stands(self):
        self._write_bytes(SID, UTF8_BOM + (json.dumps(_good(self.now)) + "\n").encode())
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), log), ([NOTICE_ID], ""))
        with contextlib.redirect_stderr(io.StringIO()):
            rows, err = _writer_rows(SID)              # the rows on either shape: the pair read is an adaptation (LENS ONE)
        self.assertEqual(([r["key"] for r in rows], err), (["figure"], ""))


class NoticeRowsSplitOnEveryLineBoundary(_R2Case):
    """Round 2's per-line decode split the bytes on the LF byte alone, so a file with CR endings, which main read whole
    through str.splitlines, read as no rows and every notice card of the session left the board (the closing pass: a
    regression against main). The parse splits on the boundaries str.splitlines uses, in two steps: CR, LF and CRLF on
    the bytes, then VT, FF, FS, GS, RS, NEL, LINE SEPARATOR and PARAGRAPH SEPARATOR in each line that decodes. A line
    that is not UTF-8 still skips and is said once, and the sweep's skipped lines keep file order and carry no line
    ending, as main's did. Over the round 2 archive (cdfa72e6e) the CR case and the boundary case read no rows; the CRLF
    case fails there on the skipped line's text alone (json.loads takes a trailing CR as whitespace, so its rows already
    read).
    Since the manager's round 1 a line that is not JSON is said too (kernel-4, extra6-3: the parse skipped it in silence
    on both surfaces and the sweep then archived it unsaid), and every fact new to the episode is ONE refused bell row
    for the file (extra5-1, kernel-3), so the two cases that stage such a line assert the line and the row where they
    asserted an empty log; over the 35fad278c archive both are red there (a silent skip, one line where two are due). The
    CR and boundary cases' pair read through the writer's reader (_rows, over _writer_rows) is the manager's round 1
    adaptation, green over 35fad278c and pinning nothing there (LENS ONE); their red is over cdfa72e6e, at the rows."""

    MENU_ID = "notice:%s:menu:1" % SID

    def _rows(self, skipped=None):
        with contextlib.redirect_stderr(io.StringIO()):
            rows, err = _writer_rows(SID, skipped)     # the rows on either shape: the pair read is an adaptation (LENS ONE)
        keys = [r["key"] for r in rows]
        self.assertEqual(err, "", "a file that read is no fault")
        return keys

    def _two_rows(self, ending):
        return ending.join(json.dumps(_good(self.now, key=k)).encode() for k in ("figure", "menu")) + ending

    def test_cr_endings_read_every_row(self):
        self._write_bytes(SID, self._two_rows(b"\r"))
        feed, log = self._feed()
        self.assertEqual((sorted(self._notice_ids(feed)), log), ([NOTICE_ID, self.MENU_ID], ""), "both cards stand, nothing said")
        self.assertEqual(self._rows(), ["figure", "menu"], "the writer's reader reads them too")

    def test_crlf_endings_read_every_row_and_a_skipped_line_carries_no_ending(self):
        self._write_bytes(SID, b"not json\r\n" + self._two_rows(b"\r\n"))
        feed, log = self._feed()
        self.assertEqual(sorted(self._notice_ids(feed)), [NOTICE_ID, self.MENU_ID], "both cards stand")
        # the line that is not JSON is said once and rings once for the file (the manager's round 1, kernel-4 and extra5-1)
        self.assertEqual(log.count("romp-kernel:"), 1, log)
        self.assertIn("notices/%s.jsonl: a line is not JSON (a torn line, or trailing garbage) and is not a notice row" % SID, log)
        rows = _refused()
        self.assertEqual(len(rows), 1, "one refused row for the file")
        self.assertIn("notices/%s.jsonl: 1 line skipped" % SID, rows[0])
        skipped = []
        self.assertEqual(self._rows(skipped), ["figure", "menu"])
        self.assertEqual(skipped, ["not json"], "the line the sweep archives, without its CR")
        self.assertEqual(len(_refused()), 1, "the writer's reader meets the same fact: no second row")

    def test_the_other_boundaries_split_as_main_did(self):
        seps = ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"]      # VT FF FS GS RS NEL LS PS
        keys = ["k%d" % i for i in range(len(seps) + 1)]
        text = "".join(json.dumps(_good(self.now, key=k)) + s for k, s in zip(keys, seps + ["\n"]))
        self._write_bytes(SID, text.encode("utf-8"))
        self.assertEqual(self._rows(), keys, "nine rows over eight boundaries, str.splitlines' set")

    def test_a_row_that_is_not_utf8_among_cr_rows_still_skips_and_is_said_once(self):
        bad = ('{"op": "post", "key": "menu", "rev": 1, "t": %d, "title": "caf\xe9 MARKER-ROW-TEXT"}'
               % (self.now - 5)).encode("latin-1")
        self._write_bytes(SID, b"not json\r" + bad + b"\r" + json.dumps(_good(self.now)).encode() + b"\r")
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), [NOTICE_ID], "the good row's card stands; the damaged row skips")
        self.assertEqual(log.count("romp-kernel:"), 2, log)   # two facts, each once: not UTF-8, and not JSON (kernel-4)
        self.assertIn("notices/%s.jsonl: a line is not UTF-8 text; the row is skipped" % SID, log)
        self.assertIn("notices/%s.jsonl: a line is not JSON (a torn line, or trailing garbage) and is not a notice row" % SID, log)
        self.assertNotIn("MARKER-ROW-TEXT", log, "never the line's text")
        rows = _refused()
        self.assertEqual(len(rows), 1, "the two facts are one refused row for the file")
        self.assertIn("notices/%s.jsonl: 2 lines skipped" % SID, rows[0])
        self.assertNotIn("MARKER-ROW-TEXT", rows[0])
        skipped = []
        self.assertEqual(self._rows(skipped), ["figure"])
        self.assertEqual(skipped, ["not json", bad.decode("utf-8", "backslashreplace")], "the lines left out, in file order")
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), log, len(_refused())), ([NOTICE_ID], "", 1), "said once per episode")


class NoticeStoreUnreadableIsSaid(_R2Case):
    """_notice_cards returned [] on any OSError from the directory listing and _notice_rows [] on a stat or read fault,
    uncached and silent, so a directory or file the kernel could not read took every notice card, or one session's, off
    the board on every build with no stderr line and no bell row, the F3 shape on the notices side. Each is said once per
    episode under the refused kind through the surface the held-mail directory uses (_note_read_fault_once), the episode
    ending on a clean listing or read; an absent directory or file stays what it was, nothing posted and no fault."""

    def _dir_rows(self):
        return [r for r in _refused() if "the notices directory (notices) could not be listed" in r]

    def test_an_unlistable_directory_rings_the_bell_once_per_episode(self):
        _skip_as_root(self)
        self.r.write_notice_rows([_good(self.now)])
        d = km._notice_dir()
        feed, _ = self._feed()
        self.assertEqual(self._notice_ids(feed), [NOTICE_ID])
        self.r.chmod(d, 0)
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), [], "nothing could be listed...")
        rows = self._dir_rows()
        self.assertEqual(len(rows), 1, "...and the bell says so, under the refused kind")
        self.assertIn("Permission denied", rows[0])
        self.assertIn("every session's notices are off the board", rows[0])
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)
        self.assertEqual(log.count("could not be listed"), 1, "stderr carries the same line")
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), log, len(self._dir_rows())), ([], "", 1), "quiet while the episode lasts")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._compact_notices(self.now), 0)
        self.assertEqual(len(self._dir_rows()), 1, "the sweep meets the same episode: one row for both readers")
        self.r.chmod(d, 0o700)
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), log), ([NOTICE_ID], ""), "back, quietly")
        self.assertNotIn(str(d), km._state_fault_seen, "the episode is over")
        self.r.chmod(d, 0)
        self._feed()
        self.assertEqual(len(self._dir_rows()), 2, "a fault that returns is said again")

    def test_an_unreadable_file_takes_one_session_off_and_says_so_once(self):
        _skip_as_root(self)
        self.r.write_notice_rows([_good(self.now)])
        self.r.write_notice_rows([_good(self.now, key="other")], sid=SID2)
        p = km._notice_path(SID)
        feed, _ = self._feed()
        self.assertEqual(len(self._notice_ids(feed)), 2)
        self.r.chmod(p, 0)
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), ["notice:%s:other:1" % SID2], "the other session's card stands")
        rows = [r for r in _refused() if "notices/%s.jsonl could not be read" % SID in r]
        self.assertEqual(len(rows), 1)
        self.assertIn("Permission denied", rows[0])
        self.assertIn("the session's notices are off the board", rows[0])
        self.assertEqual(log.count("romp-kernel:"), 1, log)
        feed, log = self._feed()
        self.assertEqual((len(self._notice_ids(feed)), log), (1, ""), "said once: every build re-reads and stays quiet")
        self.r.chmod(p, 0o600)
        feed, log = self._feed()
        self.assertEqual((len(self._notice_ids(feed)), log), (2, ""))
        self.assertNotIn(str(p), km._state_fault_seen)

    def test_a_directory_that_lists_but_cannot_be_searched_is_a_stat_fault_said_once(self):
        _skip_as_root(self)
        self.r.write_notice_rows([_good(self.now)])
        d = km._notice_dir()
        self.r.chmod(d, 0o400)                       # os.listdir succeeds, every stat is refused
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), [])
        rows = [r for r in _refused() if "notices/%s.jsonl could not be read (stat failed" % SID in r]
        self.assertEqual(len(rows), 1, "an absent file and one whose stat is refused are told apart")
        self.assertIn("Permission denied", rows[0])
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), log), ([], ""))
        self.r.chmod(d, 0o700)
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), log), ([NOTICE_ID], ""))

    def test_an_absent_directory_or_file_is_nothing_posted_and_no_fault(self):
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), log, _refused()), ([], "", []))
        self.assertEqual(km._notice_rows(SID), [])
        self.assertEqual(km._state_fault_seen, {})


class WriterSideUnreadableFileIsSaidOnce(_R2Case):
    """tests-3 (the manager's round 1): the writer-side say-once for a notice file the kernel cannot read
    (_notice_rows_unlocked's OSError arm, reached by the sweep, post_notice and expire_notice) had no test; the class above
    covers the reader's arm, which never reaches it, and deleting the writer's call was green. The sweep is the vehicle,
    over a mode-000 file with no reader in the episode before it. One refused bell row names the file and the errno and
    never a row's text; the sweep returns 0 with the file's bytes unchanged (the rows stay live: since regression-2 the
    writer's reader answers the fault and the sweep passes the session by, where the fold to [] read as nothing to keep);
    a following build_feed, the reader's arm over the same fault, adds no second line and no second row (writer and
    reader are one episode); and the writer's reader answers (rows, error) with the fault named.

    Fails before by mutation: with the _note_notice_file_fault call deleted from the writer's OSError arm in a scratch
    copy of the kernel, red at the bell assertion (no row after the sweep). Over the 35fad278c archive red at the assertion
    that an unreadable file is not answered as an empty one (that writer answered a bare [], indistinguishable from an
    empty file; the pair is unpacked only after that assertion, so the red is the false absence and never a tuple unpack),
    the row, the untouched bytes and the one episode already true there."""

    def test_the_sweep_alone_says_the_file_once_and_the_reader_adds_no_second_row(self):
        _skip_as_root(self)
        self.r.write_notice_rows([dict(_good(self.now), title="SECRET-TITLE-MARKER-TEXT")])
        self.r.write_notice_rows([_good(self.now, key="other")], sid=SID2)
        p = km._notice_path(SID)
        before = p.read_bytes()
        self.r.chmod(p, 0)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            moved = km._compact_notices(self.now)
        log = err.getvalue()
        self.assertEqual(moved, 0, "nothing is archived from a file that did not read")
        rows = _refused()
        self.assertEqual(len(rows), 1, "the writer's fault is on the bell, under the refused kind: %r" % rows)
        self.assertIn("notices/%s.jsonl could not be read" % SID, rows[0])
        self.assertIn("Permission denied", rows[0])
        self.assertIn("the session's notices are off the board", rows[0])
        self.assertEqual(log.count("romp-kernel:"), 1, log)
        self.assertIn("notices/%s.jsonl could not be read" % SID, log)
        self.assertNotIn("SECRET-TITLE-MARKER-TEXT", log + rows[0], "never a row's text")
        self.assertNotIn("notices/%s.jsonl" % SID2, log, "the other session's file is not named")
        self.r.chmod(p, 0o600)
        self.assertEqual(p.read_bytes(), before, "the rows stay live: the file is not rewritten from an empty read")
        self.r.chmod(p, 0)
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), ["notice:%s:other:1" % SID2], "the other session's card stands")
        self.assertEqual((log, len(_refused())), ("", 1), "the reader meets the same episode: no second line, no second row")
        with contextlib.redirect_stderr(io.StringIO()):
            got = km._notice_rows_unlocked(SID)
        self.assertNotEqual(got, [], "an unreadable file is not an empty one: the writer's reader answers the fault beside the "
                                     "rows, where it folded the file to a bare [] that every caller read as nothing there (regression-2)")
        rows, fault = got
        self.assertEqual(rows, [])
        self.assertIn("notices/%s.jsonl could not be read" % SID, fault)
        self.assertIn("Permission denied", fault)
        self.assertNotIn("SECRET-TITLE-MARKER-TEXT", fault)
        self.assertEqual(len(_refused()), 1, "still one episode")


class HeldRecordFaultsWidened(_R2Case):
    """_held_records caught FileNotFoundError, OSError and ValueError around the parse. Three inputs slipped past: a
    document nested past the interpreter's limit raised RecursionError (a RuntimeError) out of every feed build with the
    file left in place; a record whose `mid` was not the file's name built a card the bus refused to decide (it looks a
    hold up by file name) and the card's Clear refuses a hold, so it stood forever; a `.json` symlink whose target was
    gone raised FileNotFoundError from the stat, which read as `decided meanwhile`, so it was listed on every build and
    never said. Each is moved aside and said now like any record the reader cannot take. A record whose BODY is the deep
    value is not one of them: the closing commit refused it by type and moved it aside, and the manager's round 1
    (extra8-1) ruled that a record that parsed is never declared corrupt for a field's type, so its card stands with the
    body named `list` and never formatted (_hold_text); the two deep cases assert that outcome where they asserted the
    aside, and over the 35fad278c archive the parser-returning case is red there (the record moved aside, no card). The
    unmovable link's line names the class it was refused for, `could not be read and could not be moved aside` (the link
    is the labelled exception to state one's never-rename, and its class is `read`; regression-7, the manager's round 2:
    the arm said `read or parsed` of every unmovable file); over the 085e08deb archive that case is red at the wording,
    the stated reason."""

    def _full_cards(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            cards = km._quarantine_cards(self.now)
        return cards, err.getvalue()

    def _assert_said_deep(self, log, name, reasons):
        """Exactly one stderr line names `name`.json, with one of `reasons` where the reader says why, and no line carries
        the value: a repr of the document would run to 200000 characters, so a bound on the line is the pin."""
        lines = [l for l in log.splitlines() if name + ".json" in l]
        self.assertEqual(len(lines), 1, log)
        self.assertIn("%s.json could not be parsed (" % name, lines[0])
        self.assertTrue(any(r in lines[0] for r in reasons), lines[0])
        self.assertLess(len(lines[0]), 400, "the file and the type are named, never the value")
        self.assertNotIn("[[", lines[0])

    def test_a_document_nested_past_the_limit_moves_aside(self):
        """The real parser on the running Python. Through 3.13 json.loads raises RecursionError at the depth and the
        record lands in the parser's arm: moved aside, said once, the readable hold on the board. The free-threaded 3.14
        parses it and hands back a record whose body is the deep list, and a record that parsed is never refused for a
        field's type (the manager's round 1, extra8-1): its card stands beside the readable hold with the body named
        `list` and never formatted (the sibling case below pins that outcome on every Python). Which arm the running
        parser takes is read from the parser itself, never assumed. The rewrite (the manager's round 1) pins only the arm
        a parser that RETURNS the deep value takes, so this case is green over the 35fad278c archive on Python 3.12, the
        interpreter every local figure was measured on, and its red-before is CI's 3.14t cell alone, unverified locally:
        the free-threaded 3.14.6 build available locally still raises RecursionError at this depth, so no locally
        available interpreter makes this case a red-before/green-after pair (tests-2, the manager's round 2)."""
        self.r.write_hold("qc-good")
        (self.r.qdir / "qc-deep.json").write_text(DEEP_BODY_DOC % "qc-deep")
        try:
            json.loads(DEEP)
            parser_takes_the_depth = True
        except RecursionError:
            parser_takes_the_depth = False
        full, log = self._full_cards()
        cards = [c["itemId"] for c in full]
        if parser_takes_the_depth:
            self.assertEqual(cards, ["quarantine:qc-deep", "quarantine:qc-good"], "the record parsed: its card stands")
            self.assertEqual((full[0]["blocked"]["body"], full[0]["blocked"]["gist"]), ("list", "list"), "the body by its type")
            self.assertNotIn("[[", json.dumps(full))
            self.assertEqual((self._asides("qc-deep"), log, _refused()), ([], "", []), "nothing moved, nothing said")
            expected = ["quarantine:qc-deep", "quarantine:qc-good"]
        else:
            self.assertEqual(cards, ["quarantine:qc-good"], "the readable hold stands")
            self.assertEqual(len(self._asides("qc-deep")), 1, "moved aside like any record that cannot be parsed")
            self._assert_said_deep(log, "qc-deep", ("maximum recursion depth exceeded",))
            self.assertEqual(len(_refused()), 1)
            expected = ["quarantine:qc-good"]
        feed, log = self._feed()
        self.assertEqual(([c["itemId"] for c in _asks(feed, "quarantine:")], log), (expected, ""),
                         "the build survives it, and the next build says nothing new")

    def test_a_deep_document_the_parser_returns_is_moved_aside_as_a_list_and_kept_as_a_body_named_by_type(self):
        """json.loads as the free-threaded Python 3.14 answers the deep document, made deterministic here: the parser
        returns the 100000-deep value instead of raising. As a bare list it is not an object: moved aside and said by
        type alone. As a record's BODY it is a field of another type in a record that parsed: the card stands with the
        body named `list`, nothing is moved and nothing is said for it (the manager's round 1, extra8-1; the closing
        commit had refused the record by type and moved it aside, so a held message the bus's writer accepted left the
        board with no card and no decision). Before the closing commit the record with the deep body was taken and the
        card's gist, str() of the body, overflowed the stack out of every feed build (the 3.14t CI job: `Stack overflow
        ... while getting the repr of an object`); nothing formats the value now on any Python. Over the 35fad278c
        archive this case is red at the card list (the record moved aside, no card)."""
        self.r.write_hold("qc-good")
        (self.r.qdir / "qc-list.json").write_text(DEEP)
        (self.r.qdir / "qc-body.json").write_text(DEEP_BODY_DOC % "qc-body")
        deep = _deep_list()
        answers = {"[": deep, '{"mid": "qc-body"': {"mid": "qc-body", "to": "web", "at": 1000, "body": deep}}
        with _parser_returning(answers):
            full, log = self._full_cards()
        cards = [c["itemId"] for c in full]
        self.assertEqual(cards, ["quarantine:qc-body", "quarantine:qc-good"], "the list is refused; the record with the deep body keeps its card")
        self.assertEqual((len(self._asides("qc-list")), len(self._asides("qc-body"))), (1, 0), "the list moved aside, the record left where it is")
        self.assertEqual((full[0]["blocked"]["body"], full[0]["blocked"]["gist"]), ("list", "list"), "the body named by its type, never formatted")
        self.assertLess(len(json.dumps(full)), 4000, "no field carries the value")
        self.assertNotIn("[[", json.dumps(full))
        self._assert_said_deep(log, "qc-list", ("not a JSON object",))
        self.assertEqual(log.count("romp-kernel:"), 1, log)
        rows = _refused()
        self.assertEqual(len(rows), 1, "one row: the list's")
        self.assertIn("qc-list.json", rows[0])
        self.assertNotIn("qc-body", rows[0])
        self.assertTrue(len(rows[0]) < 400 and "[[" not in rows[0], rows[0])
        with _parser_returning(answers):
            feed, log = self._feed()
        self.assertEqual(([c["itemId"] for c in _asks(feed, "quarantine:")], log), (["quarantine:qc-body", "quarantine:qc-good"], ""),
                         "the next build meets the list no more and the record still, quietly")

    def test_a_record_that_names_another_message_id_moves_aside(self):
        self.r.write_hold("qc-good")
        (self.r.qdir / "qc-bad.json").write_text(json.dumps({"mid": "somebody-else", "to": "web", "toId": SID, "frm": "api", "at": 1000}))
        cards, log = self._cards()
        self.assertEqual(cards, ["quarantine:qc-good"], "no card the bus would refuse to decide")
        self.assertEqual(len(self._asides("qc-bad")), 1)
        self.assertIn("qc-bad.json could not be parsed (the record's message id is not the file's name)", log)
        self.assertNotIn("somebody-else", log, "the file is named, the record's id is not repeated")

    def test_a_dangling_symlink_is_moved_aside_by_its_own_name(self):
        self.r.write_hold("qc-good")
        link = self.r.qdir / "qc-link.json"
        os.symlink("nowhere.json", link)
        cards, log = self._cards()
        self.assertEqual(cards, ["quarantine:qc-good"])
        self.assertFalse(os.path.lexists(link), "the link itself leaves the .json listing...")
        self.assertEqual(len(self._asides("qc-link")), 1, "...moved aside beside the others")
        self.assertIn("qc-link.json could not be read (a link to a file that is gone); moved aside to qc-link.json.corrupt-", log)
        rows = _refused()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].startswith("held mail: qc-link.json could not be read; moved aside with the suffix .corrupt-"), rows[0])
        cards, log = self._cards()
        self.assertEqual((cards, log, len(_refused())), (["quarantine:qc-good"], "", 1), "never met again")

    def test_a_dangling_symlink_that_cannot_be_moved_is_said_once(self):
        _skip_as_root(self)
        self.r.write_hold("qc-good")
        os.symlink("nowhere.json", self.r.qdir / "qc-link.json")
        self.r.chmod(self.r.qdir, 0o500)             # listable and readable, no rename inside it
        cards, log = self._cards()
        self.assertEqual((cards, len(_refused())), (["quarantine:qc-good"], 1))
        self.assertIn("qc-link.json could not be read and could not be moved aside", log, "the link's class is `read` (regression-7)")
        cards, log = self._cards()
        self.assertEqual((cards, log, len(_refused())), (["quarantine:qc-good"], "", 1), "said once per episode")
        self.r.chmod(self.r.qdir, 0o700)
        cards, log = self._cards()
        self.assertEqual((len(self._asides("qc-link")), len(_refused())), (1, 2), "the next listing moves it aside")


class HoldFieldsOfAnotherTypeAreNamedNeverFormatted(_R2Case):
    """tests-2 (the manager's round 1): _hold_text's coercion of the card's toId, frm, to, origin and body was covered by
    no test, and removing it was green. It is the belt that keeps a value no repr survives out of the card, the failure
    class the closing commit exists to remove, and since extra8-1 dropped the body arm in _held_records it is the only
    thing between a peer-sent container and the card. A container (a list, an object) renders as its type name alone, a
    number spelled out, text as it is, a falsy value as the field's default; the card's sid and name stay text; the
    build does not raise; and a container in those fields is QUIET (the card stands, no stderr line, no bell row, no
    aside), which is intended and not accidental: the record parsed, and a record that parsed is never refused for a
    field's type (state three at _note_read_fault_once), where a line the parser refuses is loud.

    Fails before by mutation, not by archive (the belt exists at 35fad278c; the finding is that nothing pinned it): with
    _hold_text's coercion removed in a scratch copy of the kernel (the raw value handed back) both cases are red with
    AttributeError out of the build, the card's gist splitting the raw body (a dict's in the first case, the deep list's
    in the second) before any repr is reached; green here. Over the 35fad278c archive both are red too, but at the card
    list and for another reason (that head's body arm moved these records aside), so the mutation is the evidence."""

    FIELDS = ("toId", "frm", "to", "origin", "body")

    def _full_cards(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            cards = km._quarantine_cards(self.now)
        return cards, err.getvalue()

    @staticmethod
    def _shown(card):
        b = card["blocked"]
        return (card["sid"], card["name"], b["frm"], b["to"], b["origin"], b["body"], b["gist"])

    def test_a_list_a_dict_and_a_number_in_the_cards_fields_are_named_by_type(self):
        self.r.write_hold("qc-good")
        docs = {"qc-list": dict(zip(self.FIELDS, (["SECRET-FIELD-TEXT"], ["a", "b"], ["web"], ["TESTHOST"], ["SECRET-FIELD-TEXT"]))),
                "qc-dict": dict(zip(self.FIELDS, ({"SECRET-FIELD-TEXT": 1}, {"k": "v"}, {"n": "web"}, {"h": 1}, {"SECRET-FIELD-TEXT": 2}))),
                "qc-num": dict(zip(self.FIELDS, (7, 3.5, 42, 0, 12345)))}
        for mid, fields in docs.items():
            (self.r.qdir / (mid + ".json")).write_text(json.dumps(dict({"mid": mid, "at": 1000}, **fields)))
        cards, log = self._full_cards()
        by = {c["itemId"]: c for c in cards}
        self.assertEqual(sorted(by), ["quarantine:qc-dict", "quarantine:qc-good", "quarantine:qc-list", "quarantine:qc-num"],
                         "every record parsed, so every card stands")
        self.assertEqual(self._shown(by["quarantine:qc-list"]), ("list",) * 7, "a list is its type name in every field")
        self.assertEqual(self._shown(by["quarantine:qc-dict"]), ("dict",) * 7, "an object the same")
        self.assertEqual(self._shown(by["quarantine:qc-num"]), ("7", "42", "3.5", "42", "?", "12345", "12345"),
                         "a number is spelled out; a falsy value takes the field's default")
        for c in cards:
            self.assertIsInstance(c["sid"], str)
            self.assertIsInstance(c["name"], str)
            for k in ("frm", "to", "origin", "body", "gist", "what"):
                self.assertIsInstance(c["blocked"][k], str, k)
        self.assertNotIn("SECRET-FIELD-TEXT", json.dumps(cards), "a container's contents never reach the card")
        self.assertEqual((log, _refused()), ("", []), "quiet: the records parsed, so nothing is said")
        self.assertEqual(sorted(p.name for p in self.r.qdir.iterdir()), ["qc-dict.json", "qc-good.json", "qc-list.json", "qc-num.json"],
                         "and nothing is moved aside")
        feed, log = self._feed()
        self.assertEqual((len(_asks(feed, "quarantine:")), log), (4, ""), "the whole build survives them")

    def test_a_deep_value_the_parser_returns_in_every_field_is_named_never_formatted(self):
        self.r.write_hold("qc-good")
        (self.r.qdir / "qc-deep.json").write_text(DEEP_BODY_DOC % "qc-deep")   # the bytes stand in; the parser's answer is below
        deep = _deep_list()
        rec = dict({"mid": "qc-deep", "at": 1000}, **{k: deep for k in self.FIELDS})
        with _parser_returning({'{"mid": "qc-deep"': rec}):
            cards, log = self._full_cards()
            feed, flog = self._feed()
        by = {c["itemId"]: c for c in cards}
        self.assertEqual(sorted(by), ["quarantine:qc-deep", "quarantine:qc-good"])
        self.assertEqual(self._shown(by["quarantine:qc-deep"]), ("list",) * 7, "every field by its type alone")
        self.assertLess(len(json.dumps(by["quarantine:qc-deep"])), 2000, "no field carries the value")
        self.assertNotIn("[[", json.dumps(cards))
        self.assertEqual((log, flog, _refused()), ("", "", []), "quiet")
        self.assertEqual(sorted(a["itemId"] for a in _asks(feed, "quarantine:")), ["quarantine:qc-deep", "quarantine:qc-good"])
        self.assertTrue((self.r.qdir / "qc-deep.json").exists(), "the record is left where it is")


class SaidOncePruneReadsASnapshot(_R2Case):
    """build_feed runs on the pusher's thread, on GET /feed.json and on the clearAll handler, under three different locks
    or none, so two _held_records over the same directory overlap. The end-of-listing prune iterated the module-level
    registry live in a comprehension, so the other listing's difference_update landed mid-iteration and raised
    RuntimeError (`Set changed size during iteration`) out of the build. The prune reads a snapshot now."""

    def test_two_overlapping_listings_never_raise_out_of_one_another(self):
        self.r.qdir.mkdir(parents=True)               # present and empty: every key under it is stale, and both listings prune them all
        keys = [(str(self.r.qdir / ("qc-%d.json" % i)), 13) for i in range(3000)]
        saved = sys.getswitchinterval()
        sys.setswitchinterval(1e-5)                   # the other thread runs every few bytecodes: the interleaving three doors can produce, made certain
        errors = []
        try:
            for _ in range(40):
                km._HOLD_UNREADABLE_SAID.update(keys)
                bar = threading.Barrier(2)

                def listing():
                    try:
                        bar.wait(10)
                        km._held_records(self.r.qdir, self.now)
                    except Exception as e:            # the failure under test, carried to the assertion
                        errors.append(repr(e))
                ts = [threading.Thread(target=listing) for _ in range(2)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join(30)
                if errors:
                    break
        finally:
            sys.setswitchinterval(saved)
        self.assertEqual(errors, [], "a listing raised out of the build over the other's prune")
        self.assertEqual([k for k in km._HOLD_UNREADABLE_SAID if k[0].startswith(str(self.r.qdir))], [], "both pruned every stale key")


class UnreadableEpisodeEndsWithTheDirectory(_R2Case):
    """The listing's FileNotFoundError arm returned before the prune that ends a said-once episode, so when the held-mail
    directory was removed, every file in it with it, the entries under it stood; the same fault in a recreated directory
    was skipped with nothing said for the rest of the run. The arm ends the directory's episodes now. The line names the
    class the record was refused for, `could not be parsed and could not be moved aside` for the torn record
    (regression-7, the manager's round 2); over the 085e08deb archive the case is red at that wording, the stated
    reason, and over the 4383cc9af archive at the recreated directory's row count, its own."""

    def test_the_same_fault_in_a_recreated_directory_is_said_again(self):
        _skip_as_root(self)
        self.r.write_torn_hold("qc-torn")
        self.r.chmod(self.r.qdir, 0o500)
        cards, log = self._cards()
        self.assertEqual((cards, len(_refused())), ([], 1))
        self.assertIn("qc-torn.json could not be parsed and could not be moved aside", log, "the class it was refused for (regression-7)")
        os.chmod(self.r.qdir, 0o700)
        shutil.rmtree(self.r.qdir)
        cards, log = self._cards()
        self.assertEqual((cards, log, len(_refused())), ([], "", 1), "nothing held, nothing said")
        self.assertEqual([k for k in km._HOLD_UNREADABLE_SAID if k[0].startswith(str(self.r.qdir))], [], "the directory's episodes ended with it")
        self.r.write_torn_hold("qc-torn")
        self.r.chmod(self.r.qdir, 0o500)
        cards, log = self._cards()
        self.assertEqual(len(_refused()), 2, "the fault in the recreated directory is a new episode")
        self.assertIn("qc-torn.json could not be parsed and could not be moved aside", log)


class OlderLedgerHoldRowsAreNoBatch(_R2Case):
    """Round 1 stopped _clear_all from journaling a hold's id, but a ledger written before it (every box where Clear-all
    ran over holds) keeps a batch of quarantine:<mid> rows that _undo_clear took whole (the newest stamp) and build_feed
    counted (canUndoClear, dismissedCount): Undo lit, the first press restored nothing and journaled undo rows for the
    holds, and only the second reached the user's real clear. The three readers pass over the hold namespace now
    (_cleared_undoable); the rows stay in the ledger, inert."""

    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = _client(self.sent)

    def _dispatch(self, msg):
        with contextlib.redirect_stderr(io.StringIO()):
            km.Handler._dispatch_ws(None, msg, self.client)

    def test_undo_and_the_counts_pass_over_them(self):
        for mid in ("qa-1", "qa-2", "qb-1"):
            self.r.write_hold(mid)
        self.r.write_notice_rows([_good(self.now)])
        t1, t2 = float(self.now - 100), float(self.now - 50)   # the user's clear, then a Clear-all over the holds before round 1
        with (self.r.state / "cleared.jsonl").open("w") as f:
            f.write(json.dumps({"id": NOTICE_ID, "t": t1, "op": "clear"}) + "\n")
            for mid in ("qa-1", "qa-2", "qb-1"):
                f.write(json.dumps({"id": "quarantine:" + mid, "t": t2, "op": "clear"}) + "\n")
        feed, _ = self._feed()
        self.assertEqual(len(_asks(feed, "quarantine:")), 3, "the holds stand: the rows are inert for the card")
        self.assertEqual(self._notice_ids(feed), [])
        self.assertEqual((feed["canUndoClear"], feed["dismissedCount"]), (True, 1),
                         "Undo offers the user's clear; the hold rows count for nothing")
        self._dispatch({"type": "undoClear"})
        feed, _ = self._feed()
        self.assertEqual(self._notice_ids(feed), [NOTICE_ID], "the FIRST press restores the user's clear")
        self.assertEqual((feed["canUndoClear"], feed["dismissedCount"]), (False, 0))
        self.assertEqual([(r["id"], r["op"]) for r in self.r.ledger_rows()[4:]], [(NOTICE_ID, "undo")], "one undo row, none for a hold")
        self.assertEqual([m for m in self.sent if m.get("type") == "err"], [])
        self.assertEqual(len(_asks(feed, "quarantine:")), 3)


class TypeWrongRowKeyNamedOnlyWhenValid(_R2Case):
    """The F2 log line named the type-wrong row's key as written: a hand-edited key holding a newline forged a second
    `romp-kernel:` line, and a long one wrote a line of its length. The key is named only when it is a key by the writer's
    grammar (NOTICE_KEY_RE); any other reads `a row whose key is not a valid key`."""

    def test_a_key_that_is_not_a_valid_key_is_not_named(self):
        forged = "k\nromp-kernel: FORGED LINE MARKER-KEY-TEXT"
        self.r.write_notice_rows([_good(self.now),
                                  dict(_good(self.now), key=forged, rev="x"),
                                  dict(_good(self.now), key="K" * 200000, rev="x"),
                                  dict(_good(self.now), key="sweep", rev="x")])
        feed, log = self._feed()
        self.assertEqual(self._notice_ids(feed), [NOTICE_ID])
        lines = log.splitlines()
        self.assertEqual(len(lines), 2, log[:300])   # the two invalid keys are one fact; the valid one its own
        self.assertTrue(all(l.startswith("romp-kernel: notices/%s.jsonl: " % SID) for l in lines), lines)
        self.assertNotIn("MARKER-KEY-TEXT", log)
        self.assertNotIn("FORGED", log)
        self.assertIn("a row whose key is not a valid key carries a str where rev needs an integer", log)
        self.assertIn("a row for key sweep carries a str where rev needs an integer", log)
        self.assertLess(len(log), 600, "a long key never writes a line of its length")
        feed, log = self._feed()
        self.assertEqual((self._notice_ids(feed), log), ([NOTICE_ID], ""), "said once per episode")


if __name__ == "__main__":
    import unittest
    unittest.main()
