#!/usr/bin/env python3
"""Requests from sessions (plans/user-todos.md): a need an agent files with the person it works for, a
decision, an input or an action only they can provide, held open while the agent keeps working. Exactly
three events clear one: the user answers, the user dismisses, or the agent withdraws. Nothing that reasons
by inference may write the store (the authority tier).

Covered here, kernel side:
- the store (user-todos.json under STATE): round-trip, stamps-not-deletes, sid-keying, id stability, the
  optional `blocking` flag, the loud unknown-id refusal, the mtime cache, the caps, the resolved-history
  bound, the shape guard, and the could-not-read flag (a stat or read failure other than absence is the SAME
  flagged state as a file that is not a store, said once per errno; a missing file stays the empty store);
- the store lock: every read-modify-write holds it, concurrent registrations lose nothing, and a racing
  answer and withdraw cannot both succeed;
- the ended gate (_user_todo_session_ended) for both backends: the SDK registry's alive bit, or a reg-less
  sid's durable death record superseded by newer states evidence;
- the prune: resolved rows leave only with a corroborated death, open rows never, and it runs once per
  housekeeping pass and never from a per-session or tab build;
- the per-sid chat signature component (_user_todo_fp): the rows, the switch's prefix, the 'unreadable' value;
- the POST routes (/usertodo, /usertodo/withdraw) over the fake-socket harness: auth, the 400 shapes, the
  409 while off, the 503 on a flagged store, the remote forward with its status, the ack-fast contract;
- the withdraw account (state / at / owner / error);
- build_session's `userTodos` field and the to-do event that carries the rows, the answer-queued mark read
  off the sid's parked ops, the ended gate, the byte-identical card when no row is open, the
  `userTodosError` key, and the chatTail frames that attach the field only while the switch is on;
- the answer body and the two drive ops (userTodoAnswer, userTodoDismiss);
- the handover-keyed stamp through the real park machinery, the recall reopen on both unqueue arms, the
  loss seam with its landed check and its wiring into the SDK backend, and the boot pass over persisted
  drop marks;
- the authority tier as a grep-provable pin: judge.py never names the store or its helpers, and every
  call of a store writer in kernel.py resolves to an allow-listed def;
- memory across context loss (segment C): the rendered block a resumed, compacted or cleared session gets
  back (_user_todo_context_block: the agent's own notes, newest first, cut at the card's twelve, a pure
  read), its read-only route POST /usertodo/context over the same harness (token, the 400 shapes, `enabled`,
  never a forward, never a push), and the hook's wiring (the switch file's name, install.sh's link and sync
  SessionStart entry, bin/romp-uninstall's removal, the executable bit);
- the idle endgame (segment E): the floor's arming read (_user_todo_idle: the settle on blocking ids alone, the arm
  record and the events that spend it, the bounded tail walk), its wiring through the real build_feed (the yield to
  every live floor, the focus card's field pair and story, the goal-less placeholder, the memo components that key
  every input the floor reads, one interrupt presentation per session), the push latch on the floored blocking set,
  the badge's per-card rule over a floored card, the status nudge's stand-down, and the prune's arm records.

Synthetic fixtures only: private placeholder uuids, the notes-api demo world.
"""
import ast
import contextlib
import errno
import inspect
import io
import json
import os
import re
import shutil
import stat
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_SERVE_TOKEN"] = "testtok"
km = load_source("romp_kernel_usertodos", os.path.join(BIN, "romp-kernel"))
jd = km.jd
sb = load_source("romp_sdk_backend_usertodos", os.path.join(BIN, "romp_sdk_backend.py"))

# this module's private synthetic sids (the fixture rule: never the shared placeholder)
SID = "5a5a5a5a-1111-4222-8333-944444444401"
SID2 = "5a5a5a5a-1111-4222-8333-944444444402"
NOW = 1781200000


def _hosts_off(root):
    """Per-session hosts are on by default: a fixture that mints its own state root writes `off` into it."""
    Path(root, "session-hosts").write_text("off")


@contextlib.contextmanager
def _store_stat_fails(err=errno.EIO):
    """The store's stat raises `err` (EIO by default: the disk, not the file's absence); every other path's stat runs as
    before. The failure the project's reviewer executed against the reader (a stat raising EIO read as the EMPTY store),
    as a context manager for every surface's test. By NAME, so the same fault reaches the store under any state root."""
    real = Path.stat

    def fake(self, *a, **k):
        if self.name == "user-todos.json":
            raise OSError(err, os.strerror(err), str(self))
        return real(self, *a, **k)

    with mock.patch.object(Path, "stat", fake):
        yield


@contextlib.contextmanager
def _store_read_fails(err=errno.EIO):
    """The store's stat succeeds but its bytes cannot be read (read_text raises `err`): the second face of could-not-read."""
    real = Path.read_text

    def fake(self, *a, **k):
        if self.name == "user-todos.json":
            raise OSError(err, os.strerror(err), str(self))
        return real(self, *a, **k)

    with mock.patch.object(Path, "read_text", fake):
        yield


class _StoreSandbox(unittest.TestCase):
    """Per-test STATE sandbox with the caches reset and the switch ON (it is OFF by default; the OFF side
    lives in test_user_todos_switch.py)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        self.addCleanup(setattr, jd, "STATE", jd.STATE)   # holds even when a later setUp line raises (no tearDown then)
        jd.STATE = Path(self.td.name)
        _hosts_off(self.td.name)
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._user_todos_switch_cache.clear()
        km._set_user_todos(True)

    def tearDown(self):
        jd.STATE = self.saved
        self.td.cleanup()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._user_todos_switch_cache.clear()


class StoreRoundTrip(_StoreSandbox):
    def test_add_mints_a_ut_id_and_persists_the_record(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", "OAuth vs cookie")
        self.assertRegex(tid, r"^ut-[0-9a-f]{8}$")
        rec = km._user_todos()[SID][0]
        self.assertEqual(rec["id"], tid)
        self.assertEqual(rec["text"], "Need the auth-scheme decision to wire login")
        self.assertEqual(rec["detail"], "OAuth vs cookie")
        self.assertIsInstance(rec["createdT"], int)
        self.assertNotIn("resolved", rec, "a fresh request is open")

    def test_detail_is_optional_and_absent_when_empty(self):
        km._add_user_todo(SID, "Need a test credential for the api session")
        self.assertNotIn("detail", km._user_todos()[SID][0])

    def test_blocking_is_stored_only_when_set(self):
        # the flag is stored and shipped, never read here: the row carries the key only when the agent set it, so
        # a bare row is byte-identical to one filed before the flag existed
        a = km._add_user_todo(SID, "Need the staging port", blocking=True)
        b = km._add_user_todo(SID, "Need a name for the new tab")
        c = km._add_user_todo(SID, "Need the fixture format pick", blocking=False)
        rows = {t["id"]: t for t in km._user_todos()[SID]}
        self.assertIs(rows[a]["blocking"], True)
        self.assertNotIn("blocking", rows[b])
        self.assertNotIn("blocking", rows[c], "False stores no key")
        open_rows = {t["id"]: t for t in km._open_user_todos(SID)}
        self.assertIs(open_rows[a]["blocking"], True, "the payload row carries the flag when true")
        self.assertNotIn("blocking", open_rows[b])
        self.assertEqual(set(open_rows[a]), {"id", "text", "createdT", "blocking"})

    def test_the_mtime_cache_sees_the_write(self):
        self.assertEqual(km._user_todos(), {})            # primes the (empty) read path
        km._add_user_todo(SID, "Need your pick of the two route layouts")
        self.assertTrue(km._user_todos().get(SID), "the (mtime_ns, size) cache key sees the write")

    def test_ids_never_collide_within_a_session(self):
        ids = {km._add_user_todo(SID, "request %d" % i) for i in range(20)}
        self.assertEqual(len(ids), 20)

    def test_the_store_is_sid_keyed(self):
        km._add_user_todo(SID, "web: need the staging port")
        km._add_user_todo(SID2, "api: need the auth decision")
        self.assertEqual(len(km._open_user_todos(SID)), 1)
        self.assertEqual(len(km._open_user_todos(SID2)), 1)
        self.assertEqual(km._open_user_todos(SID)[0]["text"], "web: need the staging port")

    def test_open_list_sorts_by_createdT_oldest_first(self):
        # written newest-first on purpose: the sort must come from createdT, not file order
        (jd.STATE / "user-todos.json").write_text(json.dumps({SID: [
            {"id": "ut-bbbbbbbb", "text": "second", "createdT": NOW + 60},
            {"id": "ut-aaaaaaaa", "text": "first", "createdT": NOW}]}))
        self.assertEqual([t["id"] for t in km._open_user_todos(SID)], ["ut-aaaaaaaa", "ut-bbbbbbbb"])

    def test_open_rows_ship_store_values_only(self):
        # the rows ride the dedup-compared chat payload: a derived per-build value here (an age, a `now`)
        # would defeat the serialized-payload dedup and re-send the full chat every push
        km._add_user_todo(SID, "Need the auth-scheme decision", "OAuth vs cookie")
        km._add_user_todo(SID, "Need a staging API key")
        rows = {t["text"]: t for t in km._open_user_todos(SID)}
        self.assertEqual(set(rows["Need the auth-scheme decision"]), {"id", "text", "createdT", "detail"})
        self.assertEqual(set(rows["Need a staging API key"]), {"id", "text", "createdT"},
                         "detail rides iff the request has one")
        self.assertEqual(km._open_user_todos(SID), km._open_user_todos(SID), "byte-stable across builds")
        self.assertNotIn("time.time()", inspect.getsource(km._open_user_todos), "no build clock reaches the rows")

    def test_a_garbled_or_non_dict_file_reads_as_empty_and_refuses_writes(self):
        p = jd.STATE / "user-todos.json"
        for junk in ("not json", json.dumps(["enabled"])):
            km._user_todos_cache.clear(); km._user_todos_bad.clear()
            p.write_text(junk)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(km._user_todos(), {}, junk)
                self.assertIn("is not a request store", err.getvalue(), junk)
                with self.assertRaises(RuntimeError):
                    km._add_user_todo(SID, "Need the staging port")
            self.assertEqual(p.read_text(), junk, "the unreadable store is never replaced")


class UnreadableStore(_StoreSandbox):
    """A stat or read failure other than absence is could-not-read, never the empty store (the project's reviewer executed a
    stat raising EIO: the reader answered {} with no line and no flag, the prune then spent every arm record on that
    read, and no writer had a flag to refuse on). The reader answers the same FLAGGED state the shape guard answers for
    a file that is not a store: the empty stand-in, _user_todos_unreadable True, one stderr line per errno, every write
    refused until a read succeeds. A missing file stays the empty store, silent by design."""

    def _one_line(self, err):
        lines = err.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("could not be read", lines[0])
        self.assertIn("user-todos.json", lines[0])
        return lines[0]

    def test_a_stat_failure_is_the_flagged_store_said_once_per_errno(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        err = io.StringIO()
        with _store_stat_fails(errno.EIO), contextlib.redirect_stderr(err):
            for _ in range(3):
                self.assertEqual(km._user_todos(), {}, "the empty stand-in, never a partial store")
                self.assertTrue(km._user_todos_unreadable(), "could-not-read, not no-store")
        self.assertIn("[Errno %d]" % errno.EIO, self._one_line(err))
        with _store_stat_fails(errno.EACCES), contextlib.redirect_stderr(err):
            km._user_todos(); km._user_todos()
        self.assertEqual(len(err.getvalue().splitlines()), 2, "a second errno is news")
        self.assertIn("[Errno %d]" % errno.EACCES, err.getvalue().splitlines()[1])
        with _store_stat_fails(errno.EACCES), contextlib.redirect_stderr(err):
            km._user_todos()
        self.assertEqual(len(err.getvalue().splitlines()), 2, "the same errno again is not")
        # the disk back: the rows read again, the flag lifts, and the outage wrote nothing
        with contextlib.redirect_stderr(err):
            self.assertEqual([t["id"] for t in km._user_todos()[SID]], [tid])
            self.assertFalse(km._user_todos_unreadable())
        self.assertEqual(len(err.getvalue().splitlines()), 2, "recovery says nothing")

    def test_a_read_failure_is_the_same_flagged_state(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        km._user_todos_cache.clear()                     # the version's cache would answer the rows without a read
        err = io.StringIO()
        with _store_read_fails(errno.EIO), contextlib.redirect_stderr(err):
            for _ in range(3):
                self.assertEqual(km._user_todos(), {})
                self.assertTrue(km._user_todos_unreadable())
        self.assertIn("[Errno %d]" % errno.EIO, self._one_line(err))
        refused = io.StringIO()
        with _store_read_fails(errno.EIO), contextlib.redirect_stderr(refused):
            with self.assertRaises(RuntimeError):
                km._add_user_todo(SID, "Need the auth-scheme decision")
        self.assertEqual(len(refused.getvalue().splitlines()), 1, refused.getvalue())
        self.assertIn("refusing to overwrite", refused.getvalue(), "the writer's own line, the reader's said once already")
        self.assertEqual([t["id"] for t in km._user_todos()[SID]], [tid], "readable again: the rows, and the flag lifts")
        self.assertFalse(km._user_todos_unreadable())

    def test_a_missing_file_is_the_empty_store_and_silent(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(km._user_todos(), {})
            self.assertFalse(km._user_todos_unreadable())
            tid = km._add_user_todo(SID, "Need the staging port")   # nothing to protect: the writer writes through
        self.assertEqual(err.getvalue(), "")
        self.assertEqual([t["id"] for t in km._user_todos()[SID]], [tid])

    def test_every_writer_refuses_while_the_store_cannot_be_read(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        t2 = km._add_user_todo(SID, "Need the auth-scheme decision")
        km._resolve_user_todo(SID, t2, "answered")
        p = jd.STATE / "user-todos.json"
        before = p.read_bytes()
        with _store_stat_fails(), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(RuntimeError):
                km._add_user_todo(SID, "Need a staging API key")   # the one writer that reaches the file off an empty read
            self.assertFalse(km._resolve_user_todo(SID, tid, "dismissed"), "no row in the stand-in to stamp")
            self.assertFalse(km._reopen_user_todo(SID, t2), "none to lift")
            with self.assertRaises(RuntimeError):
                km._write_user_todos({})
        self.assertEqual(p.read_bytes(), before, "the store is never replaced by a copy of the empty stand-in")
        self.assertEqual(len(km._user_todos()[SID]), 2)

    def test_the_withdraw_account_and_the_signature_read_the_flag(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        with _store_stat_fails(), contextlib.redirect_stderr(io.StringIO()):
            acct = km._withdraw_user_todo(SID, tid)
            self.assertEqual(acct, {"ok": False, "state": "unknown", "at": None, "owner": None,
                                    "error": km._USER_TODOS_UNREADABLE_ERR}, "could not look: never 'not yours'")
            self.assertEqual(km._user_todo_fp(SID), "unreadable", "the card rebuilds to show the error")
            self.assertEqual(km._user_todo_fp(SID2), "unreadable")
        self.assertNotIn("resolved", km._user_todos()[SID][0])

    def test_a_stat_fault_lifting_on_a_file_that_is_not_a_store_keeps_that_version_flagged(self):
        # the two flags share one slot in _user_todos_bad: a stat fault on a file the shape guard had flagged took the
        # version flag's place, and the fault's lift (a stat succeeding again) popped the slot while the cache still
        # answered that version's empty stand-in, so the not-a-store file read as a healthy EMPTY store with no flag
        # left for the writer to refuse on, and the next write would have replaced the very file the guard protects.
        # The lift reads the file again, never answers it from the cache; the version is said again, once, after the
        # outage, because the re-read is what re-flags it
        p = jd.STATE / "user-todos.json"
        junk = json.dumps({"enabled": True})
        p.write_text(junk)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(km._user_todos(), {})
            self.assertTrue(km._user_todos_unreadable(), "the shape guard's flag")
            with _store_stat_fails():
                self.assertEqual(km._user_todos(), {})
                self.assertTrue(km._user_todos_unreadable(), "the fault's flag")
            # the disk back, the file untouched: still not a store
            self.assertEqual(km._user_todos(), {})
            self.assertTrue(km._user_todos_unreadable(), "the version stays flagged after the fault lifts")
            with self.assertRaises(RuntimeError):
                km._write_user_todos({})
        self.assertEqual(p.read_text(), junk, "the not-a-store file is never replaced")
        said = [l for l in err.getvalue().splitlines() if "top-level keys must be session ids" in l]   # the reader's line
        self.assertEqual(len(said), 2, "the version is re-flagged by a read after the outage, and said once more")
        self.assertEqual(sum("Fix or remove the file first" in l for l in err.getvalue().splitlines()), 1, "the writer's own line")


class WriterCarriesItsOwnVerdict(_StoreSandbox):
    """A writer refuses on the outcome of the read it COPIED, never on the flag slot's state at its write moment. The
    readers on other threads (the pusher's _open_user_todos and _user_todo_fp) take no lock and lift a could-not-read
    flag the instant a stat succeeds again, so between a writer's faulted read and its write a healthy read elsewhere
    cleared the slot, the write's slot check found nothing to refuse on, and the empty stand-in plus the new row
    replaced the store: DATA LOSS, the store holding only the new row. The project's reviewer executed it: one row on
    disk, a stat raising EIO on the writer's read alone, a healthy _user_todos() before the write. The window came in
    with the shape guard and its version flag; the could-not-read flag widened its trigger from a rare version race to
    a disk blink. The writer's read answers its own verdict now (_user_todos_read), and _write_user_todos takes it."""

    def _one_shot_stat_fault(self):
        """The store's stat raises EIO on its FIRST call alone (the writer's read); every later stat runs as before
        (the disk back by the time anything else looks)."""
        real = Path.stat
        looks = []

        def fake(path, *a, **k):
            if path.name == "user-todos.json":
                looks.append(1)
                if len(looks) == 1:
                    raise OSError(errno.EIO, os.strerror(errno.EIO), str(path))
            return real(path, *a, **k)

        return mock.patch.object(Path, "stat", fake)

    def test_a_reader_lifting_the_flag_between_the_writers_read_and_its_write_does_not_let_the_write_through(self):
        # the reviewer's probe: one row on disk; a stat raising EIO on the writer's read alone; a healthy read before
        # the write, inline, the way a concurrent reader on the pusher's thread runs (the writer holds the store lock,
        # which the readers never take)
        tid = km._add_user_todo(SID, "Need the staging port")
        p = jd.STATE / "user-todos.json"
        before = p.read_bytes()
        real_write = km._write_user_todos
        slot_at_write = []

        def reader_then_write(cur, *a, **k):
            km._user_todos()                             # the concurrent reader: the disk is back, so its read lifts the flag
            slot_at_write.append(dict(km._user_todos_bad))
            return real_write(cur, *a, **k)

        err = io.StringIO()
        with self._one_shot_stat_fault(), mock.patch.object(km, "_write_user_todos", reader_then_write), \
                contextlib.redirect_stderr(err):
            with self.assertRaises(RuntimeError):
                km._add_user_todo(SID, "Need a staging API key")
        self.assertEqual(slot_at_write, [{}], "the probe's premise: the reader lifted the flag before the write")
        self.assertEqual(p.read_bytes(), before, "byte for byte as it was: never the stand-in plus the new row")
        self.assertEqual([t["id"] for t in km._user_todos()[SID]], [tid])
        self.assertIn("refusing to overwrite", err.getvalue(), "the writer's own line")

    def test_with_nothing_reading_between_the_write_is_still_refused(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        p = jd.STATE / "user-todos.json"
        before = p.read_bytes()
        with self._one_shot_stat_fault(), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(RuntimeError):
                km._add_user_todo(SID, "Need a staging API key")
        self.assertEqual(p.read_bytes(), before, "byte for byte as it was")
        self.assertEqual([t["id"] for t in km._user_todos()[SID]], [tid], "the disk back: the row reads again")

    def test_the_reader_answers_its_own_verdict(self):
        # (store, flag): None for a healthy read or no file; the could-not-read flag this read set or kept; the version
        # key of a file that is not a store, from the read and from the cache alike
        p = jd.STATE / "user-todos.json"
        self.assertEqual(km._user_todos_read(), ({}, None), "no file: the empty store, no flag")
        tid = km._add_user_todo(SID, "Need the staging port")
        rows, flag = km._user_todos_read()
        self.assertEqual(([t["id"] for t in rows[SID]], flag), ([tid], None))
        self.assertIs(km._user_todos(), rows, "the plain reader is the same read, without the verdict")
        with _store_stat_fails(errno.EIO), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todos_read(), ({}, ("stat", errno.EIO)))
        with _store_read_fails(errno.EACCES), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todos_read(), ({}, ("read", errno.EACCES)))
        self.assertEqual(km._user_todos_read()[1], None, "the disk back: the flag lifts with the read")
        p.write_text(json.dumps({"enabled": True}))
        st = p.stat()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todos_read(), ({}, (st.st_mtime_ns, st.st_size)), "not a store: its version is the flag")
            self.assertEqual(km._user_todos_read(), ({}, (st.st_mtime_ns, st.st_size)), "and the same from the cache")
            self.assertTrue(km._user_todos_unreadable(), "the unreadable check is that read's verdict")

    def test_a_cache_hit_answers_the_cached_versions_verdict_never_the_slot_at_its_look(self):
        # the interleaving a slot look cannot survive: a not-a-store version is on disk. A reader on another thread is
        # mid-lift after a stat-fault blink (its fault-lift block popped the slot and the cache), THIS read looks at
        # the slot in that gap (nothing there), and that reader's re-read re-sets both before this read looks at the
        # cache (a hit). A verdict taken off the slot look answered healthy for the empty stand-in: a writer copying
        # it fell to the slot check, and _user_todos_unreadable's callers answered a definite state (no such row,
        # nothing to show) off a file the kernel could not read as a store. The verdict rides the cache entry beside
        # the stand-in it describes, so a hit answers the version's verdict whatever the slot read. The other
        # reader's completion runs inline, once, at the one seam between the two looks (_ut_flag_is_fault on the
        # slot's value); the case asserts its premise: the slot look found nothing, and the slot holds the version
        # again by the cache look
        p = jd.STATE / "user-todos.json"
        p.write_text(json.dumps({"enabled": True}))
        st = p.stat(); key = (st.st_mtime_ns, st.st_size)
        real_is_fault = km._ut_flag_is_fault
        real_read = km._user_todos_read
        fired = []

        def other_reader_finishes_here(flag):
            if not fired:
                fired.append(flag)
                real_read()                              # its re-read: the slot holds the key, the cache the stand-in
            return real_is_fault(flag)

        def mid_lift():
            km._user_todos_bad.clear(); km._user_todos_cache.clear(); fired.clear()

        with mock.patch.object(km, "_ut_flag_is_fault", other_reader_finishes_here), \
                contextlib.redirect_stderr(io.StringIO()):
            mid_lift()
            store, flag = km._user_todos_read()
            self.assertEqual(fired, [None], "the premise: this read's slot look found nothing")
            self.assertEqual(km._user_todos_bad.get(str(p)), key, "and the slot holds the version by the cache look")
            self.assertEqual((store, flag), ({}, key), "a cache hit on a not-a-store version: its key, whatever the slot read")
            mid_lift()
            self.assertTrue(km._user_todos_unreadable(), "the unreadable check answers that verdict")
            mid_lift()
            err = io.StringIO()
            with contextlib.redirect_stderr(err), self.assertRaises(RuntimeError):
                cur, flag = km._user_todos_read()
                km._write_user_todos(dict(cur), flag)
            self.assertIn("the read this write copied came back flagged", err.getvalue(),
                          "a writer under it refuses on its own read's verdict, before the slot check")

    def test_every_kernel_call_of_the_writer_hands_it_the_flag_of_the_read_it_copied(self):
        # a writer that leaves the flag out leans on the slot alone, the window this class exists for
        src = (Path(HERE).parent / "kernel" / "kernel.py").read_text()
        calls = [n for n in ast.walk(ast.parse(src))
                 if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_write_user_todos"]
        self.assertGreaterEqual(len(calls), 4, "the writers: register, stamp, reopen, prune")
        for c in calls:
            self.assertTrue(len(c.args) == 2 or any(k.arg == "read_flag" for k in c.keywords),
                            "kernel.py:%d calls _write_user_todos without the flag of the read its copy came from" % c.lineno)


class RegistrationCaps(_StoreSandbox):
    """`text` and `detail` are agent-supplied and ride every chat payload and every chat-signature component of the
    owning session, so both are bounded at the one writer that mints rows (_USER_TODO_TEXT_CAP,
    _USER_TODO_DETAIL_CAP: a line and a page). Over the cap is refused (ValueError, the route's 400, worded
    for the agent), never truncated."""

    def setUp(self):
        super().setUp()
        self._push = (km._push_all, km._push_soon)
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(AssertionError("synchronous _push_all"))
        km._push_soon = lambda: None

    def tearDown(self):
        km._push_all, km._push_soon = self._push
        super().tearDown()

    def _route(self, body):
        code, out = _serve_post("/usertodo", body, {"X-Romp-Token": km.TOKEN})
        return code, json.loads(out.decode() or "{}")

    def test_the_caps_are_a_line_and_a_page(self):
        self.assertEqual((km._USER_TODO_TEXT_CAP, km._USER_TODO_DETAIL_CAP), (500, 4000))

    def test_a_100_kb_detail_is_refused_before_any_write(self):
        with self.assertRaises(ValueError) as cm:
            km._add_user_todo(SID, "Need the auth-scheme decision", "x" * 100_000)
        self.assertIn("detail", str(cm.exception))
        self.assertIn("one line", str(cm.exception))
        self.assertFalse((jd.STATE / "user-todos.json").exists(), "nothing written")

    def test_an_oversize_text_is_refused_too(self):
        with self.assertRaises(ValueError) as cm:
            km._add_user_todo(SID, "n" * (km._USER_TODO_TEXT_CAP + 1))
        self.assertIn("text", str(cm.exception))
        self.assertEqual(km._user_todos(), {})

    def test_a_text_and_a_detail_at_the_cap_are_stored_whole(self):
        text = "N" * km._USER_TODO_TEXT_CAP
        detail = "d" * km._USER_TODO_DETAIL_CAP
        tid = km._add_user_todo(SID, text, detail)
        rec = km._user_todos()[SID][0]
        self.assertEqual((rec["id"], rec["text"], rec["detail"]), (tid, text, detail), "at the cap: whole, never trimmed")
        self.assertEqual(km._open_user_todos(SID)[0]["detail"], detail)

    def test_the_route_answers_400_with_the_one_line_wording_and_writes_nothing(self):
        code, res = self._route({"id": SID, "text": "Need the auth-scheme decision", "detail": "x" * 100_000})
        self.assertEqual(code, 400)
        self.assertFalse(res["ok"])
        self.assertIn("one line", res["error"])
        self.assertIn("rest in your reply", res["error"])
        self.assertEqual(km._user_todos(), {})
        code, res = self._route({"id": SID, "text": "n" * (km._USER_TODO_TEXT_CAP + 1)})
        self.assertEqual((code, res["ok"]), (400, False))
        # before any forward: the local kernel words the refusal and a remote never sees the bulk
        with mock.patch.object(km, "_host_for_sid", lambda sid: {"host": "TESTHOST"}), \
                mock.patch.object(km, "_remote_forward_status", side_effect=AssertionError("forwarded an oversize request")):
            self.assertEqual(self._route({"id": SID, "text": "Need the port", "detail": "x" * 100_000})[0], 400)
        # at the cap the route stores it whole
        code, res = self._route({"id": SID, "text": "N" * km._USER_TODO_TEXT_CAP, "detail": "d" * km._USER_TODO_DETAIL_CAP})
        self.assertEqual((code, res["ok"]), (200, True))
        self.assertEqual(km._user_todos()[SID][0]["detail"], "d" * km._USER_TODO_DETAIL_CAP)


class ResolutionStamps(_StoreSandbox):
    """Resolution stamps rather than deletes: the record carries its own history."""

    def test_each_clearing_event_stamps_its_own_kind(self):
        for kind in ("answered", "dismissed", "withdrawn"):
            tid = km._add_user_todo(SID, "need for %s" % kind)
            self.assertTrue(km._resolve_user_todo(SID, tid, kind))
            rec = next(t for t in km._user_todos()[SID] if t["id"] == tid)
            self.assertEqual(rec["resolved"]["kind"], kind)
            self.assertIsInstance(rec["resolved"]["t"], int)

    def test_a_resolved_request_leaves_the_open_list_but_not_the_file(self):
        tid = km._add_user_todo(SID, "Need the rate-limit ceiling")
        km._resolve_user_todo(SID, tid, "answered")
        self.assertEqual(km._open_user_todos(SID), [])
        self.assertEqual(len(km._user_todos()[SID]), 1, "stamped, never deleted")

    def test_unknown_id_is_refused_never_a_silent_success(self):
        self.assertFalse(km._resolve_user_todo(SID, "ut-deadbeef", "withdrawn"))

    def test_a_second_stamp_is_refused_and_the_first_survives(self):
        tid = km._add_user_todo(SID, "Need the schema review")
        self.assertTrue(km._resolve_user_todo(SID, tid, "answered"))
        self.assertFalse(km._resolve_user_todo(SID, tid, "withdrawn"), "already cleared: the withdraw is told so")
        rec = km._user_todos()[SID][0]
        self.assertEqual(rec["resolved"]["kind"], "answered", "the first stamp is the history")

    def test_reopen_lifts_an_answered_stamp_only(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        self.assertFalse(km._reopen_user_todo(SID, tid), "an OPEN row has nothing to lift")
        km._resolve_user_todo(SID, tid, "answered")
        self.assertTrue(km._reopen_user_todo(SID, tid))
        self.assertEqual([t["id"] for t in km._open_user_todos(SID)], [tid], "open again")
        self.assertNotIn("resolved", km._user_todos()[SID][0])
        for kind in ("dismissed", "withdrawn"):
            t2 = km._add_user_todo(SID, "cleared by %s" % kind)
            km._resolve_user_todo(SID, t2, kind)
            self.assertFalse(km._reopen_user_todo(SID, t2), "%s is never lifted" % kind)
        self.assertFalse(km._reopen_user_todo(SID, "ut-deadbeef"), "unknown ids are refused")


class StoreLock(_StoreSandbox):
    """The store lock: the routes' HTTP threads, the WS dispatch threads and the housekeeping pass all
    read-modify-write this file, so without it two buses registering concurrently lost confirmed rows and a
    racing answer plus withdraw both reported success with last-write-wins on the surviving stamp."""

    def test_every_store_mutation_runs_under_the_lock(self):
        real_write = km._write_user_todos
        seen = []

        def guarded(cur, *a, **k):
            # the lock is re-entrant and an RLock has no .locked(): _is_owned() is the claim, since every
            # mutation publishes on the thread that took the lock
            seen.append(km._user_todos_lock._is_owned())
            real_write(cur, *a, **k)

        km._write_user_todos = guarded
        try:
            tid = km._add_user_todo(SID, "Need the auth-scheme decision")
            km._resolve_user_todo(SID, tid, "answered")
            km._reopen_user_todo(SID, tid)
            (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
            (jd.STATE / "gone" / (SID2 + ".json")).write_text(json.dumps({"t": NOW, "by": "gone"}))
            t2 = km._add_user_todo(SID2, "dead session's row")
            km._resolve_user_todo(SID2, t2, "dismissed")
            km._user_todos_cache.clear()
            km._prune_user_todos()
        finally:
            km._write_user_todos = real_write
        self.assertGreaterEqual(len(seen), 5)
        self.assertTrue(all(seen), "a store write outside the lock is the lost-update bug")

    def test_concurrent_registrations_lose_nothing(self):
        n = 20
        barrier = threading.Barrier(2)

        def writer(sid):
            barrier.wait()
            for i in range(n):
                km._add_user_todo(sid, "request %d" % i)

        ts = [threading.Thread(target=writer, args=(s,)) for s in (SID, SID2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        km._user_todos_cache.clear()
        d = json.loads((jd.STATE / "user-todos.json").read_text())
        self.assertEqual(len(d.get(SID) or []) + len(d.get(SID2) or []), 2 * n,
                         "registrations lost to an unlocked read-modify-write")

    def test_a_racing_answer_and_withdraw_cannot_both_succeed(self):
        for attempt in range(40):
            km._user_todos_cache.clear()
            (jd.STATE / "user-todos.json").write_text(json.dumps(
                {SID: [{"id": "ut-aaaaaaaa", "text": "need x", "createdT": 1}]}))
            barrier = threading.Barrier(2)
            out = [None, None]

            def r(i, kind):
                barrier.wait()
                out[i] = km._resolve_user_todo(SID, "ut-aaaaaaaa", kind)

            ts = [threading.Thread(target=r, args=(0, "answered")),
                  threading.Thread(target=r, args=(1, "withdrawn"))]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual([out[0], out[1]].count(True), 1,
                             "attempt %d: first-stamp-wins must be real under concurrency" % attempt)
            km._user_todos_cache.clear()
            kind = km._user_todos()[SID][0]["resolved"]["kind"]
            self.assertEqual(kind, "answered" if out[0] else "withdrawn",
                             "the surviving stamp must be the winner's, never last-write-wins")


class EndedGate(_StoreSandbox):
    """_user_todo_session_ended: has this request's session ENDED, by corroborated evidence only. An
    SDK-owned sid answers from the registry's alive bit; a reg-less sid from the durable death record under
    STATE/gone, which counts only while it is the newest event. A raw listing miss is never evidence."""

    def _mark_dead(self, sid, t=NOW):
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (sid + ".json")).write_text(json.dumps({"t": t, "by": "gone"}))

    def test_no_evidence_means_not_ended(self):
        self.assertFalse(km._user_todo_session_ended(SID), "a listing miss is not a death")

    def test_an_sdk_registry_answers_from_its_alive_bit(self):
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        self.assertTrue(km._user_todo_session_ended(SID), "ended-but-revivable")
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": True}))
        self.assertFalse(km._user_todo_session_ended(SID), "dormant (alive, no thread) is not ended")

    def test_a_reg_less_sid_answers_from_the_durable_death_record(self):
        self._mark_dead(SID, t=NOW)
        self.assertTrue(km._user_todo_session_ended(SID))
        (jd.STATE / "states").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "states" / (SID + ".jsonl")).write_text(
            json.dumps({"t": NOW + 60, "state": "idle"}) + "\n")
        self.assertFalse(km._user_todo_session_ended(SID), "the marker counts only while newest")

    def test_a_garbled_marker_is_not_a_death(self):
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text("not json")
        self.assertFalse(km._user_todo_session_ended(SID))
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps(["gone"]))
        self.assertFalse(km._user_todo_session_ended(SID))


class PruneSweep(_StoreSandbox):
    """The prune keys on the rows' own corroborated evidence (resolved AND a durable death record), never
    on a display set, and runs once per housekeeping pass."""

    def _mark_dead(self, sid, t=NOW):
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (sid + ".json")).write_text(json.dumps({"t": t, "by": "gone"}))

    def test_open_requests_survive_regardless_of_any_display_set(self):
        km._add_user_todo(SID, "live but idle: a list collapse must not delete me")
        km._add_user_todo(SID2, "aged out of the discover window, still standing")
        km._prune_user_todos()
        self.assertEqual(set(km._user_todos()), {SID, SID2})

    def test_open_requests_of_a_dead_session_survive_too(self):
        km._add_user_todo(SID, "my session died; revive returns me")
        self._mark_dead(SID)
        km._prune_user_todos()
        self.assertEqual(len(km._open_user_todos(SID)), 1, "hidden by the ended gate, never deleted")

    def test_resolved_rows_of_a_dead_session_leave(self):
        tid = km._add_user_todo(SID, "answered, then the session died")
        km._resolve_user_todo(SID, tid, "answered")
        self._mark_dead(SID)
        km._prune_user_todos()
        self.assertNotIn(SID, km._user_todos(), "nothing open, session dead: the sid leaves")

    def test_resolved_rows_of_a_live_session_stay(self):
        tid = km._add_user_todo(SID, "answered but the session lives")
        km._resolve_user_todo(SID, tid, "answered")
        km._prune_user_todos()
        self.assertEqual(len(km._user_todos()[SID]), 1, "history rides until the session dies")

    def test_an_sdk_ended_registry_counts_as_the_death_record(self):
        tid = km._add_user_todo(SID, "answered on an ended SDK session")
        km._resolve_user_todo(SID, tid, "answered")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        km._prune_user_todos()
        self.assertNotIn(SID, km._user_todos())

    def test_a_revived_session_is_not_dead_and_keeps_its_rows(self):
        tid = km._add_user_todo(SID, "answered, session died, then revived")
        km._resolve_user_todo(SID, tid, "answered")
        self._mark_dead(SID, t=NOW)
        (jd.STATE / "states").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "states" / (SID + ".jsonl")).write_text(
            json.dumps({"t": NOW + 60, "state": "idle"}) + "\n")
        km._prune_user_todos()
        self.assertEqual(len(km._user_todos()[SID]), 1, "revived: not ended, the history stays")

    def test_open_rows_survive_the_death_gated_removal_of_their_resolved_siblings(self):
        # the row filter's one job: a dead session holding a resolved row AND an open one loses the first alone (a
        # filter that dropped the sid whole would take the open request with it); both death records
        for marker, kind in (("gone", "withdrawn"), ("sdk", "answered")):
            with self.subTest(marker=marker):
                sid = SID if marker == "gone" else SID2
                done = km._add_user_todo(sid, "settled before the session died")
                km._resolve_user_todo(sid, done, kind)
                kept = km._add_user_todo(sid, "still waiting when the session died")
                if marker == "gone":
                    self._mark_dead(sid)
                else:
                    (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
                    (jd.STATE / "sdk" / (sid + ".json")).write_text(json.dumps({"alive": False}))
                km._prune_user_todos()
                rows = km._user_todos()[sid]
                self.assertEqual([t["id"] for t in rows], [kept], "the open row is the only row left")
                self.assertNotIn("resolved", rows[0])
                self.assertEqual(len(km._open_user_todos(sid)), 1)

    def test_an_answered_row_whose_loss_is_still_being_checked_is_held_for_the_seam(self):
        # the race the hold closes: kill() writes alive:false, shutdown() drop-marks the stranded echo and hands the
        # loss to the seam's thread; a housekeeping pass between the hand-over and the thread's reopen deleted the
        # row, and the thread found nothing to lift. With the mark on the reg the prune keeps the row, and the seam
        # then reopens it (the transcript stubbed empty: nothing landed)
        self.addCleanup(setattr, km, "_sessions", km._sessions)
        self.addCleanup(setattr, km, "_parse", km._parse)
        km._sessions = lambda now, window=None, forks=True: [{"sid": SID, "path": "/dev/null"}]
        km._parse = lambda path, sid, now: {"turns": []}
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        km._stamp_user_todo_answered(SID, tid)
        gone = km._add_user_todo(SID, "a dismissed sibling leaves as before")
        km._resolve_user_todo(SID, gone, "dismissed")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps(
            {"sid": SID, "alive": False,
             "echoes": [{"t": 1, "text": body, "author": "human", "dropped": True, "todo": tid}]}))
        km._prune_user_todos()
        rows = km._user_todos().get(SID) or []
        self.assertEqual([t["id"] for t in rows], [tid], "the held row stays; the dismissed sibling left")
        self.assertEqual(rows[0]["resolved"]["kind"], "answered", "held as the seam left it, never reopened by the prune")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_answer_lost(SID, tid, body, wait=True), "reopened")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the request is open again")
        km._prune_user_todos()
        self.assertEqual(len(km._open_user_todos(SID)), 1, "open rows never leave")

    def test_a_drop_mark_holds_only_the_answered_row_it_names(self):
        # the hold is by id: another request's answered row (its echo not drop-marked) leaves with the dead session
        tid = km._add_user_todo(SID, "Need the staging port")
        km._stamp_user_todo_answered(SID, tid)
        other = km._add_user_todo(SID, "Need the auth-scheme decision")
        km._stamp_user_todo_answered(SID, other)
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps(
            {"sid": SID, "alive": False,
             "echoes": [{"t": 1, "text": "x", "author": "human", "dropped": True, "todo": tid},
                        {"t": 2, "text": "y", "author": "human", "dropped": False, "todo": other}]}))
        self.assertEqual(km._user_todo_losses_pending(SID), {tid})
        self.assertEqual(km._user_todo_losses_pending(SID2), set(), "a reg-less sid has no marks")
        km._prune_user_todos()
        self.assertEqual([t["id"] for t in km._user_todos()[SID]], [tid], "an echo not drop-marked holds nothing")

    def test_a_noop_prune_never_writes(self):
        km._add_user_todo(SID, "still here")
        p = jd.STATE / "user-todos.json"
        before = p.stat().st_mtime_ns
        km._prune_user_todos()
        self.assertEqual(p.stat().st_mtime_ns, before, "nothing gone: no write")

    def test_a_store_that_cannot_be_read_leaves_every_row_and_arm_record_alone(self):
        # the project's reviewer executed this: a stat raising EIO read as the EMPTY store, and the empty-store arm spent
        # every arm record on it (a record no row backs is stale, on a store that HAS rows). Could-not-read is refused,
        # never treated as no records: no row leaves, no record is spent, nothing is written. The not-a-store version
        # is the same flagged state and is refused the same way; a readable store runs the sweep as before, and a
        # genuinely empty one still spends the stale records
        tid = km._add_user_todo(SID, "answered, then the session died")
        km._resolve_user_todo(SID, tid, "answered")
        self._mark_dead(SID)                             # on a readable store the sweep drops this sid
        self.addCleanup(km._UT_FLOOR_ARM.clear)
        with km._UT_FLOOR_ARM_LOCK:
            km._UT_FLOOR_ARM[SID2] = (frozenset({"ut-22222222"}), NOW - 30)
        p = jd.STATE / "user-todos.json"
        before = p.read_bytes()
        for fault in (_store_stat_fails, _store_read_fails):
            with self.subTest(fault=fault.__name__):
                km._user_todos_cache.clear()
                with fault(), contextlib.redirect_stderr(io.StringIO()):
                    km._prune_user_todos()
                self.assertEqual(p.read_bytes(), before, "nothing written")
                self.assertEqual(km._UT_FLOOR_ARM.get(SID2), (frozenset({"ut-22222222"}), NOW - 30), "the record stands")
        km._user_todos_cache.clear(); km._user_todos_bad.clear()
        p.write_text(json.dumps({"enabled": True, "gt": 1}))   # not a store: the same flagged state
        with contextlib.redirect_stderr(io.StringIO()):
            km._prune_user_todos()
        self.assertEqual(km._UT_FLOOR_ARM.get(SID2), (frozenset({"ut-22222222"}), NOW - 30))
        p.write_bytes(before)
        km._user_todos_cache.clear(); km._user_todos_bad.clear()
        km._prune_user_todos()
        self.assertNotIn(SID, km._user_todos(), "readable again: the dead session's resolved row leaves")
        self.assertIn(SID2, km._UT_FLOOR_ARM, "spent only on a death record, and there is none")
        km._prune_user_todos()
        self.assertNotIn(SID2, km._UT_FLOOR_ARM, "an EMPTY store (read, not failed) still spends a record no row backs")

    def test_a_fault_that_begins_after_the_prunes_first_read_leaves_every_arm_record_alone(self):
        # round four's refusal asked _user_todos_unreadable (a read) and the empty-store arm then read the store AGAIN, so
        # a fault beginning between the two reads answered the empty stand-in at the second with the flag set, and the
        # arm spent every arm record off a read the refusal had never seen. The pass reads ONCE now, under the store
        # lock, and every arm branches on that read's flag: a stat that succeeds on the first call and raises EIO from
        # the second on leaves every row and record alone, writes nothing, and never reaches the reader as a fault
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        self.addCleanup(km._UT_FLOOR_ARM.clear)
        with km._UT_FLOOR_ARM_LOCK:
            km._UT_FLOOR_ARM[SID] = (frozenset({"ut-11111111"}), NOW - 30)
            km._UT_FLOOR_ARM[SID2] = (frozenset({"ut-22222222"}), NOW - 30)
        p = jd.STATE / "user-todos.json"
        before = p.read_bytes()
        km._user_todos_cache.clear()
        real = Path.stat
        looks = []

        def fake(path, *a, **k):
            if path.name == "user-todos.json":
                looks.append(1)
                if len(looks) > 1:
                    raise OSError(errno.EIO, os.strerror(errno.EIO), str(path))
            return real(path, *a, **k)

        err = io.StringIO()
        with mock.patch.object(Path, "stat", fake), contextlib.redirect_stderr(err):
            km._prune_user_todos()
        self.assertEqual(km._UT_FLOOR_ARM.get(SID), (frozenset({"ut-11111111"}), NOW - 30), "the record stands")
        self.assertEqual(km._UT_FLOOR_ARM.get(SID2), (frozenset({"ut-22222222"}), NOW - 30),
                         "and so does the one no row backs: on a store with rows only a death record spends it")
        self.assertEqual(p.read_bytes(), before, "nothing written")
        self.assertEqual(len(km._open_user_todos(SID)), 1, "the open row too")
        self.assertNotIn("could not be read", err.getvalue(), "no fault reached the reader")
        self.assertEqual(len(looks), 1, "one read per pass: nothing left for a later fault to reach")

    def test_the_sweep_runs_once_per_housekeeping_pass_and_never_from_a_build(self):
        # one call per pass of the housekeeping jobs, as its own stage; never from a per-session or tab
        # build (the first cut called it from the tab-list build several times per cycle). The executed count,
        # one per jobs cycle and none per pusher cycle, is tests/test_jobs_thread_split.py's
        src = inspect.getsource(km._jobs_pass)
        self.assertIn("_job_stage('pruneUserTodos', lambda: _prune_user_todos())", src)
        self.assertIn("pruneUserTodos", km._PerfStats.JOBS)
        for fn in (km.build_session, km._chat_tab_sessions, km.build_feed, km._pusher_cycle_jobs):
            self.assertNotIn("_prune_user_todos", inspect.getsource(fn), fn.__name__)


class ChatSigComponent(_StoreSandbox):
    """The per-sid chat signature component (_user_todo_fp): a store write changes neither the transcript nor
    the states file, so without it a background tab's cached chat never showed the new row. Keyed per sid:
    another session's write is not this tab's repaint. The switch and the flagged store ride the same component."""

    def setUp(self):
        super().setUp()
        self.tpath = jd.STATE / (SID + ".jsonl")
        self.tpath.write_text("")
        self.saved_sdk = km._sdk
        km._sdk = lambda: None

    def tearDown(self):
        km._sdk = self.saved_sdk
        super().tearDown()

    def test_a_request_write_busts_the_chat_build_cache(self):
        sess = {"path": str(self.tpath), "sid": SID, "anchor": ""}
        before = km._chat_build_sig(sess)
        km._add_user_todo(SID, "Need the auth-scheme decision")
        self.assertNotEqual(before, km._chat_build_sig(sess))

    def test_another_sessions_write_busts_no_one_elses_cache(self):
        sess = {"path": str(self.tpath), "sid": SID, "anchor": ""}
        before = km._chat_build_sig(sess)
        km._add_user_todo(SID2, "api: need the auth decision")
        self.assertEqual(before, km._chat_build_sig(sess), "another session's row is not this tab's repaint")

    def test_the_component_is_byte_stable_while_the_rows_stand(self):
        km._add_user_todo(SID, "Need the auth-scheme decision")
        sess = {"path": str(self.tpath), "sid": SID, "anchor": ""}
        self.assertEqual(km._chat_build_sig(sess), km._chat_build_sig(sess))
        self.assertIsNone(km._user_todo_fp(SID2), "no rows: nothing to key")
        self.assertTrue(km._user_todo_fp(SID))

    def test_a_stamp_busts_the_owning_cache_too(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        sess = {"path": str(self.tpath), "sid": SID, "anchor": ""}
        before = km._chat_build_sig(sess)
        km._resolve_user_todo(SID, tid, "withdrawn")
        self.assertNotEqual(before, km._chat_build_sig(sess))

    def test_the_component_carries_the_switch_prefix_and_the_unreadable_value(self):
        km._add_user_todo(SID, "Need the auth-scheme decision")
        on = km._user_todo_fp(SID)
        self.assertTrue(on.startswith("on:"))
        km._set_user_todos(False)
        off = km._user_todo_fp(SID)
        self.assertTrue(off.startswith("off:"))
        self.assertNotEqual(on, off, "a flip changes the card with no store write")
        km._set_user_todos(True)
        self.assertIsNone(km._user_todo_fp(SID2))
        (jd.STATE / "user-todos.json").write_text(json.dumps({"enabled": True, "gt": 1}))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_fp(SID2), "unreadable", "a flagged store is news to a rowless tab too")
            km._set_user_todos(False)
            self.assertIsNone(km._user_todo_fp(SID2), "off: the switch changes nothing this card shows")


def _serve_post(path, body=None, headers=None):
    """Drive the REAL do_POST dispatcher over a fake socket (the auth-hardening harness)."""
    raw = json.dumps(body).encode() if isinstance(body, (dict, list)) else (body or b"")
    h = km.Handler.__new__(km.Handler)
    h.client_address = ("127.0.0.1", 0)
    hdrs = dict(headers or {})
    hdrs.setdefault("Content-Length", str(len(raw)))
    h.headers = hdrs
    h.path = path
    h.command = "POST"
    h.request_version = "HTTP/1.1"
    h.wfile = io.BytesIO()
    h.rfile = io.BytesIO(raw)
    h.close_connection = True
    captured = {}
    h.send_response = lambda code, *a: captured.__setitem__("status", code)
    h.send_header = lambda k, v: None
    h.end_headers = lambda: None
    h.log_message = lambda *a: None
    h.do_POST()
    return captured.get("status"), h.wfile.getvalue()


class Routes(_StoreSandbox):
    """POST /usertodo and /usertodo/withdraw: the kernel legs the postal tools stand on."""

    def setUp(self):
        super().setUp()
        self._push = (km._push_all, km._push_soon)
        self.pushed_soon = []
        # the routes must never build views synchronously (the ack-fast contract): a stray _push_all
        # here is a bug, so it blows up instead of silently passing
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synchronous _push_all on a postal-called route"))
        km._push_soon = lambda: self.pushed_soon.append(True)

    def tearDown(self):
        km._push_all, km._push_soon = self._push
        super().tearDown()

    def _post(self, path, body, token=True):
        hdrs = {"X-Romp-Token": km.TOKEN} if token else {}
        code, out = _serve_post(path, body, hdrs)
        try:
            return code, json.loads(out.decode() or "{}")
        except ValueError:
            return code, {}

    def test_register_requires_the_serve_token(self):
        code, _ = self._post("/usertodo", {"id": SID, "text": "x"}, token=False)
        self.assertEqual(code, 403)
        self.assertEqual(km._user_todos(), {}, "nothing written")

    def test_a_withdraw_whose_write_is_refused_answers_503_not_a_traceback(self):
        # the store went bad under the account's own unreadable check (the writer's RuntimeError): the route's
        # answer is the register route's 503 with the cause, never the generic handler's 500 traceback
        tid = km._add_user_todo(SID, "Need the staging port")
        with mock.patch.object(km, "_write_user_todos", side_effect=RuntimeError("write refused")):
            code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": tid})
        self.assertEqual(code, 503)
        self.assertEqual(out, {"ok": False, "error": km._USER_TODOS_UNREADABLE_ERR})
        self.assertNotIn("resolved", km._user_todos()[SID][0], "nothing stamped")
        self.assertEqual(self.pushed_soon, [])

    def test_register_returns_the_minted_id_and_writes_the_store(self):
        code, res = self._post("/usertodo", {"id": SID, "text": "Need the auth-scheme decision",
                                             "detail": "OAuth vs cookie: either unblocks login"})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        self.assertRegex(res["todoId"], r"^ut-[0-9a-f]{8}$")
        rec = km._user_todos()[SID][0]
        self.assertEqual(rec["id"], res["todoId"])
        self.assertEqual(rec["detail"], "OAuth vs cookie: either unblocks login")
        self.assertNotIn("blocking", rec, "an unset flag stores no key")

    def test_a_blocking_request_lands_on_the_row_and_a_non_boolean_is_refused(self):
        code, res = self._post("/usertodo", {"id": SID, "text": "Need the port", "blocking": True})
        self.assertEqual((code, res["ok"]), (200, True))
        self.assertIs(km._user_todos()[SID][0]["blocking"], True)
        for bad in ("true", 1, "false", [True]):
            code, res = self._post("/usertodo", {"id": SID, "text": "Need the port", "blocking": bad})
            self.assertEqual(code, 400, repr(bad))
            self.assertIn("blocking", res["error"])
            self.assertIn("true or false", res["error"])
        code, res = self._post("/usertodo", {"id": SID, "text": "Need the port", "blocking": None})
        self.assertEqual((code, res["ok"]), (200, True), "null is the absent case spelled out")
        self.assertEqual(len(km._user_todos()[SID]), 2)

    def test_register_refuses_a_bodyless_or_textless_request(self):
        self.assertEqual(self._post("/usertodo", {"id": SID})[0], 400)
        self.assertEqual(self._post("/usertodo", {"id": SID, "text": "   "})[0], 400)
        self.assertEqual(self._post("/usertodo", {"text": "no sid"})[0], 400)
        code, _ = _serve_post("/usertodo", b"not json", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400)
        code, _ = _serve_post("/usertodo", b"[1, 2]", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400, "a JSON list is not an object")
        self.assertEqual(km._user_todos(), {}, "a refused register writes nothing")

    def test_register_refuses_a_malformed_sid_before_the_switch_and_the_forward(self):
        km._set_user_todos(False)
        with mock.patch.object(km, "_host_for_sid", lambda sid: {"host": "TESTHOST"}), \
                mock.patch.object(km, "_remote_forward_status", side_effect=AssertionError("forwarded a malformed id")):
            code, res = self._post("/usertodo", {"id": "web/" + SID, "text": "Need the port"})
        self.assertEqual((code, res), (400, {"ok": False, "error": "id must be a session id"}))

    def test_register_is_409_while_off_and_503_while_the_store_is_flagged(self):
        km._set_user_todos(False)
        code, res = self._post("/usertodo", {"id": SID, "text": "Need the port"})
        self.assertEqual(code, 409)
        self.assertEqual(res["error"], km._USER_TODOS_OFF_ERR)
        km._set_user_todos(True)
        (jd.STATE / "user-todos.json").write_text(json.dumps({"enabled": True, "gt": 1}))
        with contextlib.redirect_stderr(io.StringIO()):
            code, res = self._post("/usertodo", {"id": SID, "text": "Need the port"})
        self.assertEqual(code, 503)
        self.assertEqual(res["error"], km._USER_TODOS_UNREADABLE_ERR)
        self.assertEqual(self.pushed_soon, [], "nothing changed, nothing to push")

    def test_withdraw_requires_the_serve_token(self):
        code, _ = self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-deadbeef"}, token=False)
        self.assertEqual(code, 403)

    def test_withdraw_stamps_withdrawn(self):
        _, res = self._post("/usertodo", {"id": SID, "text": "Need the fixture format pick"})
        code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        self.assertEqual(code, 200)
        self.assertTrue(out["ok"])
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "withdrawn")

    def test_withdraw_refuses_a_bodyless_request_and_the_switch(self):
        self.assertEqual(self._post("/usertodo/withdraw", {"id": SID})[0], 400)
        self.assertEqual(self._post("/usertodo/withdraw", {"todoId": "ut-deadbeef"})[0], 400)
        code, _ = _serve_post("/usertodo/withdraw", b"not json", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400)
        km._set_user_todos(False)
        code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-deadbeef"})
        self.assertEqual((code, out["error"]), (409, km._USER_TODOS_OFF_ERR))

    def test_withdraw_of_an_unknown_or_cleared_id_answers_ok_false(self):
        code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-deadbeef"})
        self.assertEqual(code, 200)
        self.assertFalse(out["ok"], "a loud, plain answer, never a silent success")
        self.assertTrue(out.get("error"))
        _, res = self._post("/usertodo", {"id": SID, "text": "once"})
        self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        _, again = self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        self.assertFalse(again["ok"])

    def test_the_routes_ack_fast_and_never_push_synchronously(self):
        code, res = self._post("/usertodo", {"id": SID, "text": "Need the auth-scheme decision"})
        self.assertEqual((code, res["ok"]), (200, True))
        code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        self.assertEqual((code, out["ok"]), (200, True))
        self.assertEqual(len(self.pushed_soon), 2, "each route wakes the pusher instead")

    def test_a_refused_withdraw_wakes_nothing(self):
        self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-deadbeef"})
        self.assertEqual(self.pushed_soon, [])

    def test_a_remote_session_is_forwarded_and_the_answer_relayed(self):
        saved = (km._host_for_sid, km._remote_forward_status)
        calls = []
        km._host_for_sid = lambda sid: {"host": "TESTHOST"} if sid == SID else None
        km._remote_forward_status = lambda r, path, body: (calls.append((path, body)) or
                                                           (200, {"ok": True, "todoId": "ut-9f2c1a34"}))
        try:
            code, res = self._post("/usertodo", {"id": SID, "text": "Need the port", "detail": "8443?", "blocking": True})
            self.assertEqual((code, res), (200, {"ok": True, "todoId": "ut-9f2c1a34"}))
            code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-9f2c1a34"})
            self.assertEqual((code, out), (200, {"ok": True}))
        finally:
            km._host_for_sid, km._remote_forward_status = saved
        self.assertEqual(calls, [("/usertodo", {"id": SID, "text": "Need the port", "detail": "8443?", "blocking": True}),
                                 ("/usertodo/withdraw", {"id": SID, "todoId": "ut-9f2c1a34"})])
        self.assertEqual(km._user_todos(), {}, "the remote kernel owns that session's store")

    def test_a_remote_forward_that_fails_is_reported_not_faked(self):
        saved = (km._host_for_sid, km._remote_forward_status)
        km._host_for_sid = lambda sid: {"host": "TESTHOST"}
        km._remote_forward_status = lambda r, path, body: (0, None)       # a dead tunnel
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                code, res = self._post("/usertodo", {"id": SID, "text": "Need the port"})
            self.assertEqual(code, 502)
            self.assertFalse(res["ok"])
            self.assertIn("not answering", res["error"])
            with contextlib.redirect_stderr(io.StringIO()):
                code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-9f2c1a34"})
            self.assertEqual(code, 502)
            self.assertFalse(out["ok"])
        finally:
            km._host_for_sid, km._remote_forward_status = saved


WSID = "5a5a5a5a-1111-4222-8333-944444444411"
WSID2 = "5a5a5a5a-1111-4222-8333-944444444412"


class WithdrawAccount(_StoreSandbox):
    """POST /usertodo/withdraw accounts for what it found: `ok` keeps its meaning (this call stamped the
    row), and `state` / `at` / `owner` say which kind of nothing-to-do an ok:false was. The route describes
    the asker's own rows only: another session's id is `unknown`, never described."""

    def setUp(self):
        super().setUp()
        self._push = (km._push_all, km._push_soon)
        self.pushed_soon = []
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synchronous _push_all on a postal-called route"))
        km._push_soon = lambda: self.pushed_soon.append(True)

    def tearDown(self):
        km._push_all, km._push_soon = self._push
        super().tearDown()

    def _post(self, path, body):
        code, out = _serve_post(path, body, {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 200)
        return json.loads(out.decode() or "{}")

    def _file(self, text="Need the auth-scheme decision", sid=WSID):
        tid = self._post("/usertodo", {"id": sid, "text": text})["todoId"]
        self.pushed_soon.clear()
        return tid

    def _withdraw(self, tid, sid=WSID):
        return self._post("/usertodo/withdraw", {"id": sid, "todoId": tid})

    def test_a_fresh_withdraw_is_ok_and_accounts_the_stamp_it_made(self):
        tid = self._file()
        out = self._withdraw(tid)
        row = km._user_todos()[WSID][0]
        self.assertEqual(row["resolved"]["kind"], "withdrawn")
        self.assertEqual(out, {"ok": True, "state": "withdrawn", "at": row["resolved"]["t"], "owner": True})
        self.assertIsInstance(out["at"], int)
        self.assertEqual(len(self.pushed_soon), 1, "the row leaves the card")

    def test_a_row_the_person_answered_is_accounted_answered_and_left_alone(self):
        tid = self._file()
        self.assertTrue(km._resolve_user_todo(WSID, tid, "answered"))
        stamp = km._user_todos()[WSID][0]["resolved"]
        out = self._withdraw(tid)
        self.assertFalse(out["ok"])
        self.assertEqual((out["state"], out["at"], out["owner"]), ("answered", stamp["t"], True))
        self.assertTrue(out.get("error"), "the one-size error text still rides along")
        self.assertEqual(km._user_todos()[WSID][0]["resolved"], stamp, "a withdraw never overwrites a stamp")
        self.assertEqual(self.pushed_soon, [], "nothing changed, nothing to push")

    def test_a_row_the_person_dismissed_is_accounted_dismissed(self):
        tid = self._file()
        self.assertTrue(km._resolve_user_todo(WSID, tid, "dismissed"))
        stamp = km._user_todos()[WSID][0]["resolved"]
        out = self._withdraw(tid)
        self.assertFalse(out["ok"])
        self.assertEqual((out["state"], out["at"], out["owner"]), ("dismissed", stamp["t"], True))

    def test_a_second_withdraw_accounts_the_first_ones_stamp(self):
        tid = self._file()
        first = self._withdraw(tid)
        again = self._withdraw(tid)
        self.assertFalse(again["ok"])
        self.assertEqual((again["state"], again["at"], again["owner"]), ("withdrawn", first["at"], True))
        self.assertEqual(len(self.pushed_soon), 1, "only the stamping call woke the pusher")

    def test_an_unknown_id_is_unknown_and_not_owned(self):
        out = self._withdraw("ut-deadbeef")
        self.assertFalse(out["ok"])
        self.assertEqual((out["state"], out["at"], out["owner"]), ("unknown", None, False))
        self.assertTrue(out.get("error"))

    def test_another_sessions_id_is_unknown_to_the_asker_and_stays_open(self):
        tid = self._file(sid=WSID2)
        out = self._withdraw(tid, sid=WSID)
        self.assertFalse(out["ok"])
        self.assertEqual((out["state"], out["owner"]), ("unknown", False), "never described, never stamped")
        self.assertNotIn("resolved", km._user_todos()[WSID2][0], "the other session's request still stands")
        self.assertEqual(self.pushed_soon, [])

    def test_the_lookup_and_the_stamp_share_one_critical_section(self):
        held = []
        real = km._resolve_user_todo
        km._resolve_user_todo = lambda *a, **k: (held.append(km._user_todos_lock._is_owned()) or real(*a, **k))
        try:
            tid = self._file()
            self.assertTrue(self._withdraw(tid)["ok"])
        finally:
            km._resolve_user_todo = real
        self.assertEqual(held, [True], "the stamp ran inside the look-up's lock")

    def _seed_row(self, resolved, sid=WSID):
        row = {"id": "ut-11111111", "text": "Need the auth-scheme decision", "createdT": NOW - 60,
               "resolved": resolved}
        (jd.STATE / "user-todos.json").write_text(json.dumps({sid: [row]}))
        km._user_todos_cache.clear()
        return row

    def test_a_malformed_closing_stamp_is_unknown_and_named_never_open(self):
        for stamp in (True, "withdrawn", 1781200000, {"t": 1781200000}, {"kind": "", "t": 1781200000},
                      {"kind": "lost", "t": 1781200000}, {"kind": ["withdrawn"], "t": 1781200000}):
            with self.subTest(stamp=stamp):
                row = self._seed_row(stamp)
                out = self._withdraw("ut-11111111")
                self.assertFalse(out["ok"])
                self.assertEqual((out["state"], out["at"], out["owner"]), ("unknown", None, True))
                self.assertIn("malformed closing stamp on ut-11111111", out["error"])
                self.assertIn(repr(stamp), out["error"], "names the stamp it could not read")
                self.assertIn("answered | dismissed | withdrawn", out["error"], "and the shape it expected")
                self.assertEqual(km._user_todos()[WSID][0], row, "the damage is reported, not papered over")
                self.assertEqual(self.pushed_soon, [])

    def test_a_well_formed_stamp_of_each_kind_is_still_its_own_state(self):
        for kind in ("answered", "dismissed", "withdrawn"):
            with self.subTest(kind=kind):
                self._seed_row({"kind": kind, "t": 1781200000})
                out = self._withdraw("ut-11111111")
                self.assertEqual((out["ok"], out["state"], out["at"], out["owner"]),
                                 (False, kind, 1781200000, True))
                self.assertNotIn("malformed", out.get("error", ""))

    def test_an_unreadable_store_is_owner_none_with_the_error_never_unknown_not_yours(self):
        tid = self._file()
        (jd.STATE / "user-todos.json").write_text(json.dumps({"enabled": True, "gt": 1}))
        km._user_todos_cache.clear()
        with contextlib.redirect_stderr(io.StringIO()):
            acct = km._withdraw_user_todo(WSID, tid)
            out = self._withdraw(tid)
        self.assertEqual((acct["ok"], acct["state"], acct["at"], acct["owner"]), (False, "unknown", None, None))
        self.assertEqual(acct["error"], km._USER_TODOS_UNREADABLE_ERR)
        self.assertFalse(out["ok"])
        self.assertIsNone(out["owner"])
        self.assertIn("unreadable", out["error"])
        self.assertNotIn("no open request", out["error"], "never the already-settled story")
        self.assertEqual(self.pushed_soon, [])

    def _forward(self, st, res, sid=WSID):
        saved = (km._host_for_sid, km._remote_forward_status)
        km._host_for_sid = lambda s: {"host": "TESTHOST", "local_port": 1, "token": "t"}
        km._remote_forward_status = lambda r, path, body: (st, res)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                code, out = _serve_post("/usertodo/withdraw", {"id": sid, "todoId": "ut-9f2c1a34"},
                                        {"X-Romp-Token": km.TOKEN})
        finally:
            km._host_for_sid, km._remote_forward_status = saved
        return code, json.loads(out.decode() or "{}")

    def test_the_remote_forward_passes_the_account_through(self):
        acct = {"ok": False, "state": "answered", "at": 1781200000, "owner": True}
        self.assertEqual(self._forward(200, acct), (200, acct))
        self.assertEqual(self._forward(200, {"ok": False}), (200, {"ok": False}), "an older kernel's ok alone: nothing invented")
        bad = {"ok": False, "state": "unknown", "at": None, "owner": True,
               "error": "malformed closing stamp on ut-9f2c1a34: resolved=True (a stamp is {kind: answered | dismissed | withdrawn, t})"}
        self.assertEqual(self._forward(200, bad), (200, bad))
        self.assertEqual(self.pushed_soon, [], "a forwarded withdraw changes nothing here")

    def test_a_remote_that_gave_no_account_is_a_502_never_already_closed(self):
        for st, res, words in ((0, None, ("tunnel to TESTHOST", "not answering")),
                               (404, None, ("kernel on TESTHOST", "predates /usertodo/withdraw")),
                               (500, None, ("kernel on TESTHOST", "HTTP 500")),
                               (200, None, ("kernel on TESTHOST", "not JSON"))):
            with self.subTest(status=st):
                code, out = self._forward(st, res)
                self.assertEqual(code, 502)
                self.assertFalse(out["ok"])
                self.assertEqual(out["host"], "TESTHOST")
                self.assertNotIn("state", out, "no account is invented")
                for w in words:
                    self.assertIn(w, out["error"])
        self.assertEqual(self.pushed_soon, [])


class ResolvedRowsAreBounded(_StoreSandbox):
    """A never-dying session's resolved rows would accumulate without bound: a per-sid size cap on resolved
    rows only. The newest _USER_TODO_RESOLVED_KEEP stay, the oldest leave; open rows are never capped."""

    def test_resolved_rows_keep_only_the_newest_K(self):
        K = km._USER_TODO_RESOLVED_KEEP
        first = km._add_user_todo(SID, "the oldest resolved row")
        km._resolve_user_todo(SID, first, "dismissed")
        for i in range(K):
            t = km._add_user_todo(SID, "later request %d" % i)
            km._resolve_user_todo(SID, t, "answered")
        resolved = [t for t in km._user_todos()[SID] if t.get("resolved")]
        self.assertEqual(len(resolved), K, "a size bound, not a time heuristic")
        self.assertNotIn(first, [t["id"] for t in resolved], "the oldest row is the one that left")

    def test_every_stamp_kind_is_capped_the_same_way(self):
        K = km._USER_TODO_RESOLVED_KEEP
        for i in range(K + 7):
            t = km._add_user_todo(SID, "request %d" % i)
            km._resolve_user_todo(SID, t, ("answered", "dismissed", "withdrawn")[i % 3])
        self.assertEqual(len([t for t in km._user_todos()[SID] if t.get("resolved")]), K)

    def test_open_rows_are_never_capped(self):
        K = km._USER_TODO_RESOLVED_KEEP
        opens = [km._add_user_todo(SID, "open %d" % i) for i in range(K + 5)]
        for i in range(K + 5):
            t = km._add_user_todo(SID, "resolved %d" % i)
            km._resolve_user_todo(SID, t, "answered")
        got = km._user_todos()[SID]
        self.assertEqual([t["id"] for t in got if not t.get("resolved")], opens,
                         "every open request survives: the cap reads resolved rows only")
        self.assertEqual(len([t for t in got if t.get("resolved")]), K)

    def test_the_fp_is_bounded_by_the_cap(self):
        K = km._USER_TODO_RESOLVED_KEEP
        for i in range(K * 2):
            t = km._add_user_todo(SID, "request %d" % i)
            km._resolve_user_todo(SID, t, "answered")
        self.assertEqual(len(km._user_todos()[SID]), K)
        self.assertTrue(km._user_todo_fp(SID))


class BuildSessionSeam(unittest.TestCase):
    """The chat payload: the top-level `userTodos` field (the upsert merge seam) and the to-do event that
    carries the same rows (the chatTail wire re-sends changed events only), the answer-queued mark, the
    ended gate, the byte-identical card when no row is open, and the two chatTail frame shapes. The world
    is the chat-signature module's: a discoverable transcript, a liveness row, no backend owning the sid."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        cdir = td / "launchdir"
        cdir.mkdir()
        proj = td / "projects"
        pdir = proj / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
        pdir.mkdir(parents=True)
        self.tpath = pdir / (SID + ".jsonl")
        rows = [
            {"type": "user", "uuid": "u1", "timestamp": "2026-06-01T00:00:00Z",
             "sessionId": SID, "message": {"role": "user", "content": "wire the login routes"}},
            {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "timestamp": "2026-06-01T00:00:05Z",
             "sessionId": SID,
             "message": {"role": "assistant", "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": "starting on the open routes"}]}},
        ]
        self.tpath.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        state = td / "state"
        state.mkdir()
        _hosts_off(state)
        self.saved = (jd.STATE, jd.PROJECTS, km.NAMES, km.WORKING_DIR, km._GLOBAL_CLAUDE_MD, km._live_map, km._sdk,
                      os.environ.get("CLAUDE_CONFIG_DIR"), km._read_task_store, km._fold_tasks, dict(km._pending_ops))
        jd._rebind_state(state)                       # every STATE-derived dir (goals, states, gone, sdk, ...)
        jd.PROJECTS = proj
        jd.NAMES.mkdir()
        (jd.NAMES / SID).write_text("web\t%s\t#1EA1EB\twhite\n" % cdir)
        km.NAMES = jd.NAMES
        km.WORKING_DIR = state / "working"
        km._GLOBAL_CLAUDE_MD = td / "no-global-claude.md"
        os.environ["CLAUDE_CONFIG_DIR"] = str(td / "claude")
        self.row = {"state": "idle", "since": NOW - 100, "model": "", "effort": "", "context": None,
                    "compactPct": None, "color": None, "backend": "sdk"}
        self.live_map = {SID: self.row}
        km._live_map = lambda: self.live_map
        km._sdk = lambda: None
        km._read_task_store = lambda fsid, fold=None: []
        km._pending_ops.clear()
        km._built_chat.clear()
        km._parse_cache.clear()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._user_todos_switch_cache.clear()
        km._set_user_todos(True)

    def tearDown(self):
        (state, proj, names, wdir, gmd, live_fn, sdk, cfg, rts, ft, ops) = self.saved
        jd._rebind_state(state)
        jd.PROJECTS = proj
        km.NAMES, km.WORKING_DIR, km._GLOBAL_CLAUDE_MD, km._live_map, km._sdk = names, wdir, gmd, live_fn, sdk
        km._read_task_store, km._fold_tasks = rts, ft
        if cfg is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = cfg
        km._pending_ops.clear()
        km._pending_ops.update(ops)
        km._built_chat.clear()
        km._parse_cache.clear()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._user_todos_switch_cache.clear()
        self.td.cleanup()

    def build(self):
        km._parse_cache.clear()
        return km.build_session(SID, NOW, live_map=self.live_map)

    def _todo_events(self, payload):
        return [e for e in payload["events"] if e.get("kind") == "todo"]

    def test_no_requests_and_no_tasks_mean_no_event_and_an_empty_field(self):
        payload = self.build()
        self.assertEqual(payload["userTodos"], [])
        self.assertEqual(self._todo_events(payload), [])

    def test_open_requests_ride_both_the_field_and_the_event(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", "OAuth vs cookie")
        payload = self.build()
        self.assertEqual([t["id"] for t in payload["userTodos"]], [tid])
        evs = self._todo_events(payload)
        self.assertEqual(len(evs), 1, "one card, by the composer")
        self.assertEqual(evs[0]["tasks"], [])
        self.assertEqual(evs[0]["userTodos"], payload["userTodos"],
                         "the event carries the rows: the chatTail delta re-sends events only")
        self.assertIs(payload["events"][-1], evs[0], "appended last: the card sits by the composer")

    def test_agent_tasks_and_requests_share_one_card(self):
        km._read_task_store = lambda fsid, fold=None: [
            {"id": "1", "subject": "Build the fixtures", "activeForm": None, "status": "pending"}]
        km._add_user_todo(SID, "Need a test credential for the api session")
        evs = self._todo_events(self.build())
        self.assertEqual(len(evs), 1)
        self.assertEqual(len(evs[0]["tasks"]), 1)
        self.assertEqual(len(evs[0]["userTodos"]), 1)

    def test_a_card_without_requests_keeps_its_pre_existing_shape(self):
        km._read_task_store = lambda fsid, fold=None: [
            {"id": "1", "subject": "Build the fixtures", "activeForm": None, "status": "pending"}]
        evs = self._todo_events(self.build())
        self.assertEqual(len(evs), 1)
        self.assertEqual(set(evs[0]) - {"uuid"}, {"kind", "tasks"}, "no userTodos key at all: byte-identical to today's card")
        self.assertNotIn("userTodosError", evs[0])

    def test_an_unreadable_task_store_still_carries_the_rows(self):
        km._read_task_store = lambda fsid, fold=None: None
        km._fold_tasks = lambda session, sid=None: [{"id": "1", "subject": "Build the fixtures",
                                                     "activeForm": None, "status": "pending"}]
        km._add_user_todo(SID, "Need the staging port")
        evs = self._todo_events(self.build())
        self.assertEqual(len(evs), 1)
        self.assertTrue(evs[0]["error"])
        self.assertEqual(evs[0]["tasks"], [])
        self.assertEqual(len(evs[0]["userTodos"]), 1)
        km._user_todos_cache.clear()
        (jd.STATE / "user-todos.json").write_text("{}")
        evs = self._todo_events(self.build())
        self.assertEqual(set(evs[0]) - {"uuid"}, {"kind", "tasks", "error"})

    def test_a_flagged_store_rides_its_own_key_beside_the_checklist(self):
        km._read_task_store = lambda fsid, fold=None: [
            {"id": "1", "subject": "Build the fixtures", "activeForm": None, "status": "pending"}]
        (jd.STATE / "user-todos.json").write_text(json.dumps({"enabled": True, "gt": 1}))
        with contextlib.redirect_stderr(io.StringIO()):
            payload = self.build()
        evs = self._todo_events(payload)
        self.assertEqual(payload["userTodos"], [])
        self.assertEqual(len(evs), 1)
        self.assertEqual(len(evs[0]["tasks"]), 1, "the checklist stays")
        self.assertNotIn("error", evs[0], "the task store's key is not borrowed")
        self.assertIn("Can't read romp's request store", evs[0]["userTodosError"])
        self.assertIn("user-todos.json", evs[0]["userTodosError"])
        self.assertNotIn(str(Path.home()), evs[0]["userTodosError"], "the home directory reads as ~")
        km._set_user_todos(False)
        with contextlib.redirect_stderr(io.StringIO()):
            evs = self._todo_events(self.build())
        self.assertNotIn("userTodosError", evs[0], "off: the surfaces are quiet")

    def test_a_store_whose_stat_fails_rides_the_same_error_key(self):
        # could-not-read is the flagged state, so the card shows the store's error where the rows were, never an empty
        # section that reads as "nothing open"
        km._add_user_todo(SID, "Need the staging port")
        with _store_stat_fails(), contextlib.redirect_stderr(io.StringIO()):
            payload = self.build()
        evs = self._todo_events(payload)
        self.assertEqual(payload["userTodos"], [])
        self.assertEqual(len(evs), 1)
        self.assertIn("Can't read romp's request store", evs[0]["userTodosError"])
        self.assertIn("user-todos.json", evs[0]["userTodosError"])
        km._parse_cache.clear()
        evs = self._todo_events(self.build())
        self.assertNotIn("userTodosError", evs[0], "readable again: the rows are back")
        self.assertEqual(len(evs[0]["userTodos"]), 1)

    def test_resolved_requests_ship_nowhere(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "dismissed")
        payload = self.build()
        self.assertEqual(payload["userTodos"], [])
        self.assertEqual(self._todo_events(payload), [])

    def test_the_field_is_clock_invariant(self):
        km._add_user_todo(SID, "Need the auth-scheme decision")
        a = self.build()
        km._parse_cache.clear()
        b = km.build_session(SID, NOW + 600, live_map=self.live_map)
        self.assertEqual(json.dumps(a["userTodos"]), json.dumps(b["userTodos"]))

    def test_an_ended_session_hides_its_requests_without_clearing_them(self):
        km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        payload = self.build()
        self.assertEqual(payload["userTodos"], [], "ended (registry alive:false): hidden everywhere")
        self.assertEqual(self._todo_events(payload), [])
        self.assertEqual(len(km._open_user_todos(SID)), 1, "hidden, not cleared: a revive returns them")
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": True}))
        self.assertEqual(len(self.build()["userTodos"]), 1, "a dormant session still shows its requests")

    def test_a_reg_less_dead_session_hides_its_requests_too(self):
        km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps({"t": NOW - 50, "by": "gone"}))
        payload = self.build()
        self.assertEqual(payload["userTodos"], [])
        self.assertEqual(self._todo_events(payload), [])
        (jd.STATE / "states").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "states" / (SID + ".jsonl")).write_text(json.dumps({"t": NOW - 10, "state": "idle"}) + "\n")
        self.assertEqual(len(self.build()["userTodos"]), 1, "revived: the requests return with the session")

    def test_a_row_carries_detail_iff_the_request_has_one(self):
        (jd.STATE / "user-todos.json").write_text(json.dumps({SID: [
            {"id": "ut-aaaaaaaa", "text": "Need the auth-scheme decision to wire login",
             "createdT": NOW - 40, "detail": "OAuth vs cookie: either unblocks login"},
            {"id": "ut-bbbbbbbb", "text": "Need a test credential for the api session", "createdT": NOW - 30},
            {"id": "ut-cccccccc", "text": "Need your pick of the two route layouts",
             "createdT": NOW - 20, "detail": "  \n\t "},
            {"id": "ut-dddddddd", "text": "Need the staging port", "createdT": NOW - 10, "detail": ""}]}))
        km._user_todos_cache.clear()
        payload = self.build()
        rows = {t["id"]: t for t in payload["userTodos"]}
        self.assertEqual(rows["ut-aaaaaaaa"]["detail"], "OAuth vs cookie: either unblocks login")
        for tid in ("ut-bbbbbbbb", "ut-cccccccc", "ut-dddddddd"):
            self.assertNotIn("detail", rows[tid], tid)
        ev_rows = {t["id"]: t for t in self._todo_events(payload)[0]["userTodos"]}
        self.assertEqual({k: ("detail" in v) for k, v in ev_rows.items()},
                         {k: ("detail" in v) for k, v in rows.items()})

    def test_a_parked_answer_marks_its_row_queued_until_the_op_leaves(self):
        # the answer-queued mark: a seven-slot op in the sid's kernel FIFO whose _op_todo equals a row's id marks
        # that row queued (the answer waits behind a compaction, a hold or a queue; the bubble's cancel recalls
        # it); another row is not marked, and the mark is gone once the op leaves the FIFO
        a = km._add_user_todo(SID, "Need the auth-scheme decision")
        b = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the auth-scheme decision", "Cookie.")
        km._pending_ops[SID] = [("send", body, None, None, True, None, a)]
        payload = self.build()
        rows = {t["id"]: t for t in payload["userTodos"]}
        self.assertIs(rows[a]["queued"], True)
        self.assertNotIn("queued", rows[b])
        ev_rows = {t["id"]: t for t in self._todo_events(payload)[0]["userTodos"]}
        self.assertIs(ev_rows[a]["queued"], True, "the event rows carry the mark too")
        self.assertEqual(json.dumps(payload["userTodos"]), json.dumps(self.build()["userTodos"]), "byte-stable while parked")
        km._pending_ops.pop(SID, None)
        rows = {t["id"]: t for t in self.build()["userTodos"]}
        self.assertNotIn("queued", rows[a], "the op drained or was recalled: the row is plain again")
        self.assertEqual(set(rows[a]), {"id", "text", "createdT"})

    def _tail_client(self, proto2, sent):
        c = {"send": lambda s: sent.append(json.loads(s)), "sent": {}}
        if proto2:
            c["proto"] = 2
            c["echat"] = {SID: {"first": "u1", "last": "a1"}}
        else:
            c["echat"] = {SID: ("u1", 0)}
        return c

    def _frame(self, rows):
        evs = [{"uuid": "u1", "kind": "user", "text": "wire the login routes"},
               {"uuid": "a1", "kind": "assistant", "text": "starting"}]
        m = {"type": "session", "id": SID, "events": evs, "status": {"state": "idle"}, "userTodos": rows}
        if rows:
            evs.append({"kind": "todo", "tasks": [], "userTodos": rows})
        return m

    def test_the_chat_tail_frames_carry_the_field_while_on_and_no_key_while_off(self):
        rows = [{"id": "ut-aaaaaaaa", "text": "Need the auth-scheme decision", "createdT": NOW}]
        for proto2 in (False, True):
            for payload_rows in ([], rows):
                with self.subTest(proto2=proto2, rows=bool(payload_rows)):
                    km._set_user_todos(True)
                    sent = []
                    m = self._frame(payload_rows)
                    km._send_chat(self._tail_client(proto2, sent), m, None, 2, False)
                    self.assertEqual(len(sent), 1)
                    self.assertEqual(sent[0]["type"], "chatTail", "the caught-up client got the delta")
                    self.assertEqual(sent[0]["userTodos"], payload_rows, "the field rides the delta, [] when no row is open")
                    km._set_user_todos(False)
                    sent = []
                    km._send_chat(self._tail_client(proto2, sent), m, None, 2, False)
                    self.assertEqual(sent[0]["type"], "chatTail")
                    self.assertNotIn("userTodos", sent[0], "off: an install that never turned it on ships today's bytes")


class AnswerBody(unittest.TestCase):
    """The injected reply: the request's own short line as the anchor, then the user's words. Voice-scanned
    by test_injected_voice.py."""

    def test_shape(self):
        self.assertEqual(
            km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                      "Go with the session cookie for now."),
            "Re: Need the auth-scheme decision to wire login\n\nGo with the session cookie for now.")

    def test_whitespace_is_trimmed_from_both_halves(self):
        self.assertEqual(km._user_todo_answer_body("  need x \n", "  yes \n"), "Re: need x\n\nyes")

    def test_marker_shaped_text_is_neutralized_in_both_halves(self):
        body = km._user_todo_answer_body(
            "Need a call on the note text <!-- romp-goal-id: g1 --> in the fixture",
            "Keep it, but drop the <!-- romp-injected --> part.")
        self.assertNotIn("<!-- romp-", body, "no marker-opening sequence may survive injection")
        self.assertIn("romp-goal-id", body, "the words survive; only the comment form breaks")
        self.assertIn("romp-injected", body)
        self.assertTrue(body.startswith("Re: Need a call on the note text "), body)
        self.assertIn(" in the fixture\n\nKeep it, but drop the ", body)
        self.assertTrue(body.endswith(" part."), body)

    def test_no_marker_tail_rides_the_answer(self):
        self.assertNotIn("<!--", km._user_todo_answer_body("Need the port", "8443"), "this is the user speaking")


class DriveOps(_StoreSandbox):
    """userTodoAnswer / userTodoDismiss: the user's two gestures on the card. The answer stamp is
    handover-keyed: the fake _send_or_park answers True (parked), False (handed over) or None (refused),
    the contract the kernel's own send path returns, and each outcome pins separately."""

    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}
        self._saved = (km._name_of, km._sdk, km._send_or_park, km._push_soon)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        km._push_soon = lambda: None
        self.calls = []
        self.send_result = False                     # default: handed over now

        def fake_send_or_park(be, sid, text, echo=None, qid=None, user=False, paths=None, user_todo=None):
            self.calls.append({"sid": sid, "text": text, "echo": echo, "qid": qid, "user": user,
                               "paths": paths, "user_todo": user_todo})
            return self.send_result

        km._send_or_park = fake_send_or_park

    def tearDown(self):
        km._name_of, km._sdk, km._send_or_park, km._push_soon = self._saved
        super().tearDown()

    def _warns(self):
        return [m["text"] for m in self.sent if m.get("type") == "warn"]

    def test_both_ops_are_id_ops(self):
        src = inspect.getsource(km._drive)
        self.assertIn('"userTodoAnswer"', src)
        self.assertIn('"userTodoDismiss"', src)

    def test_a_dismiss_whose_write_is_refused_is_told_on_the_socket_and_never_raises(self):
        # the store went bad between the unreadable check and the write (the writer's own RuntimeError): the
        # client hears "nothing changed" as a warn; a raise would land in _dispatch_ws's per-message except and
        # the client would hear nothing
        tid = km._add_user_todo(SID, "Need the staging port")
        with mock.patch.object(km, "_write_user_todos", side_effect=RuntimeError("write refused")), \
                contextlib.redirect_stderr(io.StringIO()):
            handled = km._drive({"type": "userTodoDismiss", "id": SID, "todoId": tid}, self.client)
        self.assertTrue(handled)
        self.assertEqual(self._warns(), [km._USER_TODOS_UNREADABLE_WARN])
        self.assertNotIn("resolved", km._user_todos()[SID][0], "nothing changed")

    def test_a_dismiss_whose_write_fails_is_told_on_the_socket_and_never_raises(self):
        # what the writer actually raises when the disk, not the store's shape, is the fault: _atomic_write re-raises an
        # OSError (a disk error, a permission), and the arm above caught RuntimeError alone. Executed over a real loopback
        # WebSocket at this change's parent commit: the OSError left _drive and _dispatch_ws, the reader loop's socket-failure arm
        # re-raised it, and the client's connection was torn down with no frame and no stderr line, the row still open;
        # on screen the row dropped at the click and came back with the reconnect, nothing naming the dismiss. Caught now
        # the way the recall's reopen is (_cancel_backend_queued), worded by class: the warn says the dismiss could not be
        # recorded and the request stays listed, and one stderr line names the id and the fault
        tid = km._add_user_todo(SID, "Need the staging port")
        err = io.StringIO()
        with mock.patch.object(km, "_atomic_write", side_effect=OSError(errno.EIO, "Input/output error")), \
                contextlib.redirect_stderr(err):
            handled = km._drive({"type": "userTodoDismiss", "id": SID, "todoId": tid}, self.client)
        self.assertTrue(handled, "handled, never raised")
        self.assertEqual([m["type"] for m in self.sent], ["warn"], "exactly one frame, a warn")
        self.assertEqual(self._warns(), [km._USER_TODO_DISMISS_FAILED_WARN],
                         "the failed write's account, not the unreadable store's")
        self.assertEqual(self.sent[0].get("sid"), SID, "names its session: toasted, never read as a create's verdict")
        lines = err.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("dismiss of %s could not be written" % tid, lines[0])
        self.assertIn("Input/output error", lines[0], "the fault is named")
        self.assertNotIn("refused", lines[0], "a failed write is not the writer's refusal")
        self.assertEqual(self.calls, [], "nothing sent to the session")
        on_disk = json.loads((jd.STATE / "user-todos.json").read_text())[SID][0]
        self.assertEqual(on_disk["id"], tid)
        self.assertNotIn("resolved", on_disk, "the row on disk is still open")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "and so is the kernel's read of it")

    @unittest.skipIf(os.geteuid() == 0, "root writes into a read-only directory")
    def test_a_dismiss_into_a_state_directory_the_kernel_cannot_write_is_told_and_never_raises(self):
        # the same arm off a real permission fault, no mock on the writer: the state directory goes read-only after the
        # row is filed, so the writer's temp file cannot be created (EACCES) while the store itself still reads. _codex
        # is stubbed out the way the harness stubs _sdk: on a worker where no earlier test built the Codex backend, the
        # backend lookup's first construction would mkdir under this read-only root and print its own traceback, and
        # the stderr count below would read harness noise as the arm's
        tid = km._add_user_todo(SID, "Need the staging port")
        err = io.StringIO()
        os.chmod(jd.STATE, 0o500)
        try:
            with mock.patch.object(km, "_codex", lambda: None), contextlib.redirect_stderr(err):
                handled = km._drive({"type": "userTodoDismiss", "id": SID, "todoId": tid}, self.client)
        finally:
            os.chmod(jd.STATE, 0o700)
        self.assertTrue(handled, "handled, never raised")
        self.assertEqual(self._warns(), [km._USER_TODO_DISMISS_FAILED_WARN])
        self.assertEqual(self.sent[0].get("sid"), SID)
        lines = err.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("dismiss of %s could not be written" % tid, lines[0])
        self.assertIn("[Errno %d]" % errno.EACCES, lines[0], "the permission fault is named")
        self.assertNotIn("resolved", json.loads((jd.STATE / "user-todos.json").read_text())[SID][0],
                         "the row on disk is still open")

    def test_a_dismiss_of_a_settled_row_to_a_client_being_dropped_says_nothing_of_a_failed_write(self):
        # the arm's try holds the writer alone. The client's send raises OSError itself when the peer has stopped
        # draining (_mk_ws_send: over the byte budget it marks the client dead, shuts the socket and raises, and every
        # caller lets that raise mark the client dead). With the settled-row warn's send inside the try, the arm read
        # that raise as the store's failed write: one stderr line said the dismiss could not be written when the row
        # was settled and no write was attempted, and a second send to the dead client raised the same OSError out
        tid = km._add_user_todo(SID, "Need the staging port")
        self.assertTrue(km._resolve_user_todo(SID, tid, "dismissed"), "settled before this click reaches the kernel")
        dropping = {"send": mock.Mock(side_effect=OSError("ws client chat is 17000000 bytes behind, dropping"))}
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(OSError):
            km._drive({"type": "userTodoDismiss", "id": SID, "todoId": tid}, dropping)
        self.assertEqual(err.getvalue(), "", "no store write was attempted, so no line says one failed")
        self.assertEqual(dropping["send"].call_count, 1, "the settled warn's send alone, no second frame to a dead client")
        self.assertEqual(json.loads(dropping["send"].call_args[0][0])["text"], km._USER_TODO_DISMISS_SETTLED_WARN)

    def test_both_ops_refuse_on_a_store_that_cannot_be_read_never_with_the_settled_story(self):
        # the flagged store comes before the settled-row read on both ops: off an unflagged empty stand-in the answer
        # told the person the request was "already settled" and the dismiss the same, when the kernel could not read
        tid = km._add_user_todo(SID, "Need the staging port")
        with _store_stat_fails(), contextlib.redirect_stderr(io.StringIO()):
            km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "8443."}, self.client)
            km._drive({"type": "userTodoDismiss", "id": SID, "todoId": tid}, self.client)
        self.assertEqual(self._warns(), [km._USER_TODOS_UNREADABLE_WARN] * 2)
        self.assertEqual([m.get("sid") for m in self.sent], [SID] * 2)
        self.assertEqual(self.calls, [], "nothing sent to the session")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "nothing stamped")

    def test_dismiss_stamps_dismissed_and_sends_nothing(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        handled = km._drive({"type": "userTodoDismiss", "id": SID, "todoId": tid}, self.client)
        self.assertTrue(handled)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed")
        self.assertEqual(self.calls, [], "dismiss sends nothing into the session")
        self.assertEqual(self.sent, [], "a clean dismiss raises no warning")

    def test_dismiss_of_a_settled_id_warns_loudly(self):
        km._drive({"type": "userTodoDismiss", "id": SID, "todoId": "ut-deadbeef"}, self.client)
        self.assertEqual(len(self._warns()), 1)
        self.assertIn("already settled", self._warns()[0])

    def test_answer_sends_the_anchored_reply_as_the_user_with_the_id_and_no_echo(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Go with the session cookie for now."}, self.client)
        self.assertEqual(len(self.calls), 1)
        call = self.calls[0]
        self.assertEqual(call["sid"], SID)
        self.assertEqual(call["text"], km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                                                 "Go with the session cookie for now."))
        self.assertEqual(call["user_todo"], tid, "the request id rides the send for the park path")
        self.assertIs(call["user"], True, "the answer goes out as the user's words")
        self.assertIsNone(call["echo"], "no echo argument: the backends echo inside send()")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "handed over now: stamped now, the user's gesture, never a judgment")
        self.assertEqual(self.sent, [])

    def test_a_parked_answer_stamps_nothing_and_warns_nothing(self):
        self.send_result = True
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "Session cookie."}, self.client)
        self.assertEqual(len(self.calls), 1, "the answer went to the FIFO")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "parked is not delivered: the drain stamps")
        self.assertEqual(self.sent, [], "a park is normal flow, not an error")

    def test_a_refused_send_warns_and_leaves_the_request_open(self):
        self.send_result = None
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "Session cookie."}, self.client)
        self.assertNotIn("resolved", km._user_todos()[SID][0])
        self.assertEqual(self._warns(), [km._USER_TODO_UNDELIVERED_WARN])

    def test_a_stamp_that_raises_after_a_handover_is_said_and_never_propagates(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        with mock.patch.object(km, "_stamp_user_todo_answered", side_effect=RuntimeError("store went bad")), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "8443."}, self.client)
        self.assertEqual(len(self.calls), 1, "delivered")
        self.assertEqual(self._warns(), [km._USER_TODO_STAMP_FAILED_WARN])
        self.assertIn("answered stamp for %s failed after delivery" % tid, err.getvalue())

    def test_answer_to_an_ended_sdk_session_is_refused_loudly(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "Session cookie."}, self.client)
        self.assertEqual(self.calls, [], "nothing may be sent into the void")
        self.assertEqual(self._warns(), [km._USER_TODO_ENDED_WARN])
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the request still stands")

    def test_answer_to_a_reg_less_dead_session_is_refused_loudly(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps({"t": NOW, "by": "gone"}))
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "Session cookie."}, self.client)
        self.assertEqual(self.calls, [])
        self.assertEqual(self._warns(), [km._USER_TODO_ENDED_WARN])

    def test_a_dormant_sdk_session_still_takes_the_answer(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": True}))
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "Session cookie."}, self.client)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_answer_to_a_settled_id_sends_nothing_and_warns(self):
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": "ut-deadbeef", "text": "too late"}, self.client)
        self.assertEqual(self.calls, [])
        self.assertEqual(self._warns(), [km._USER_TODO_SETTLED_WARN])

    def test_an_empty_answer_is_not_a_drive_op(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        self.assertFalse(km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "   "}, self.client))
        self.assertEqual(km._open_user_todos(SID)[0]["id"], tid, "nothing was stamped")

    def test_the_warnings_say_request_and_speak_to_the_person(self):
        for text in (km._USER_TODO_SETTLED_WARN, km._USER_TODO_ENDED_WARN, km._USER_TODO_UNDELIVERED_WARN,
                     km._USER_TODO_STAMP_FAILED_WARN, km._USER_TODO_DISMISS_SETTLED_WARN,
                     km._USER_TODO_DISMISS_FAILED_WARN):
            low = text.lower()
            self.assertIn("request", low, text)
            for noun in ("store", "stamp", "queue", "todo", "nonce", "mark"):
                self.assertNotIn(noun, low, "%r names machinery: %s" % (text, noun))

    def test_every_refusal_names_its_session_so_the_client_only_toasts_it(self):
        # the client reads a warn WITHOUT a sid that arrives while it is creating a session as that create's verdict
        # and takes the provisional tab down with the request's text in a dialog; a warn that names a session is only
        # toasted (the refused-slash warn's shape). Every refusal the two ops send names its session: the settled id,
        # the dismiss of one, the refused send, the ended session, the stamp that fails after a handover, the dismiss
        # whose write is refused, and the unreadable store on either op (the OFF refusals are pinned with the switch).
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": "ut-deadbeef", "text": "too late"}, self.client)
        km._drive({"type": "userTodoDismiss", "id": SID, "todoId": "ut-deadbeef"}, self.client)
        tid = km._add_user_todo(SID, "Need the staging port")
        self.send_result = None
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "8443."}, self.client)
        self.send_result = False
        with mock.patch.object(km, "_stamp_user_todo_answered", side_effect=RuntimeError("store went bad")), \
                contextlib.redirect_stderr(io.StringIO()):
            km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "8443."}, self.client)
        with mock.patch.object(km, "_write_user_todos", side_effect=RuntimeError("write refused")), \
                contextlib.redirect_stderr(io.StringIO()):
            km._drive({"type": "userTodoDismiss", "id": SID, "todoId": tid}, self.client)
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "8443."}, self.client)
        (jd.STATE / "user-todos.json").write_text(json.dumps({"enabled": True, "gt": 1}))   # not a store: unreadable
        km._user_todos_cache.clear()
        with contextlib.redirect_stderr(io.StringIO()):
            km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "8443."}, self.client)
            km._drive({"type": "userTodoDismiss", "id": SID, "todoId": tid}, self.client)
        self.assertEqual([m["type"] for m in self.sent], ["warn"] * 8, "eight refusals, nothing else on the socket")
        self.assertEqual(self._warns(), [km._USER_TODO_SETTLED_WARN, km._USER_TODO_DISMISS_SETTLED_WARN,
                                         km._USER_TODO_UNDELIVERED_WARN, km._USER_TODO_STAMP_FAILED_WARN,
                                         km._USER_TODOS_UNREADABLE_WARN, km._USER_TODO_ENDED_WARN,
                                         km._USER_TODOS_UNREADABLE_WARN, km._USER_TODOS_UNREADABLE_WARN])
        self.assertEqual([m.get("sid") for m in self.sent], [SID] * 8, "every refusal names its session")


class _TodoStr(str):
    """The queue-entry contract the kernel reads back: a plain str for every consumer, with the request id
    riding as a `todo` attribute (getattr(entry, "todo", ""), duck-typed like the SDK's own _TodoText)."""

    def __new__(cls, text, todo):
        o = str.__new__(cls, text)
        o.todo = todo
        return o


class _FakeBackend:
    """A forwards_sends backend double for the park, drain and recall pipeline, shaped like SdkBackend where
    the kernel reads it: send takes user_todo and stores the id on its queue entry; pending_queued lists the
    texts; unqueue takes an index and body, or the copy's id (qid), and hands back the entry it removed."""

    def __init__(self, ok=True):
        self.sent = []
        self.ok = ok
        self.queue = []
        self.meta = []

    def forwards_sends(self):
        return True

    def send(self, sid, text, qid=None, user=False, paths=None, user_todo=None):
        if self.ok is False:
            return False
        key = qid or "echo:" + uuid.uuid4().hex
        entry = _TodoStr(text, user_todo) if user_todo else text
        self.sent.append((sid, text, user, user_todo))
        self.queue.append(entry)
        self.meta.append({"qid": key})
        return self.ok

    def pending_queued(self, sid):
        return [str(q) for q in self.queue]

    def unqueue(self, sid, idx, expect=None, qid=None):
        if qid:
            idx = next((i for i, m in enumerate(self.meta) if m["qid"] == qid), -1)
        elif expect is not None and not (0 <= idx < len(self.queue) and self.queue[idx] == expect):
            idx = next((i for i, q in enumerate(self.queue) if q == expect), -1)
        if 0 <= idx < len(self.queue):
            self.meta.pop(idx)
            return self.queue.pop(idx)
        return None


class HandoverKeyedStamp(_StoreSandbox):
    """The answer stamp keys on the handover, end to end through the real park machinery: a parked answer
    carries its id, stamps only when the drain's send is accepted, and a refused drain leaves the request
    open. The drain reports through _parked_answer_handed_over, whose body is the stamp."""

    def setUp(self):
        super().setUp()
        self._saved = (km._name_of, km._sdk, km._compacting_now, km._working_now, km._limit_hold,
                       km.Sessions.backend_for, km._push_soon, dict(km._pending_ops))
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        km._working_now = lambda sid: False
        km._limit_hold = lambda sid: False
        km._push_soon = lambda: None
        km._pending_ops.clear()
        km._drain_hold.pop(SID, None)
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}
        self.be = _FakeBackend()                     # the sid's backend, from the drive op through the drain
        km.Sessions.backend_for = staticmethod(lambda sid: self.be)

    def tearDown(self):
        (km._name_of, km._sdk, km._compacting_now, km._working_now, km._limit_hold, bf,
         km._push_soon, ops) = self._saved
        km.Sessions.backend_for = staticmethod(bf)
        km._pending_ops.clear()
        km._pending_ops.update(ops)
        super().tearDown()

    def _park_an_answer(self):
        km._compacting_now = lambda sid, **k: sid == SID
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        handled = km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                             "text": "Go with the session cookie."}, self.client)
        self.assertTrue(handled)
        ops = km._pending_ops.get(SID) or []
        self.assertTrue(ops and ops[0][0] == "send", "the answer parked (compaction)")
        self.assertEqual(km._op_todo(ops[0]), tid, "the parked op carries the request id for the drain's stamp")
        self.assertEqual(len(ops[0]), 7, "the seventh slot")
        self.assertIs(ops[0][4], True, "parked as the user's words")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "no stamp at park time")
        self.assertEqual(self.sent, [], "a park is normal flow")
        return tid, ops

    def _drain(self):
        km._compacting_now = lambda sid, **k: False
        km._apply_pending_ops()

    def test_cancelling_the_parked_answer_leaves_the_request_open(self):
        tid, ops = self._park_an_answer()
        err = km._cancel_parked(SID, 0, km._parked_md(ops[0]))
        self.assertIsNone(err, "the cancel succeeds")
        self.assertFalse(km._pending_ops.get(SID), "the answer will never be delivered")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "recalled is not answered")

    def test_the_drain_delivers_and_stamps(self):
        tid, _ = self._park_an_answer()
        self._drain()
        be = self.be
        self.assertEqual(len(be.sent), 1, "the parked answer drained into a real send")
        self.assertIn("Re: Need the auth-scheme decision", be.sent[0][1])
        self.assertEqual(be.sent[0][2:], (True, tid), "as the user, with the id")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "the handover event, the drain, is where the stamp fires")

    def test_a_refused_drain_send_stamps_nothing_and_says_so(self):
        tid, _ = self._park_an_answer()
        self.be.ok = False
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self._drain()
        self.assertEqual(self.be.sent, [])
        self.assertNotIn("resolved", km._user_todos()[SID][0], "a refused send stamps nothing")
        self.assertIn("refused by the backend at the drain", err.getvalue())
        self.assertIn(tid, err.getvalue())

    def test_a_dropped_dead_session_queue_leaves_the_request_open(self):
        tid, _ = self._park_an_answer()
        km._compacting_now = lambda sid, **k: False
        km.Sessions.backend_for = staticmethod(lambda sid: (_ for _ in ()).throw(RuntimeError("session is gone")))
        with contextlib.redirect_stderr(io.StringIO()):
            km._apply_pending_ops()
        self.assertFalse(km._pending_ops.get(SID), "the dead session's queue was dropped")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "dropped is not delivered")

    def test_the_hook_stamps_on_acceptance_and_a_raising_stamp_is_said_not_raised(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertIsNone(km._parked_answer_handed_over(SID, tid, None, False))
        self.assertNotIn("resolved", km._user_todos()[SID][0])
        self.assertIn("still waiting on the user", err.getvalue())
        km._parked_answer_handed_over(SID, tid, "echo:1", True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")
        with mock.patch.object(km, "_resolve_user_todo", side_effect=RuntimeError("store went bad")), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            km._parked_answer_handed_over(SID, "ut-00000000", None, True)   # never raised into the drain
        self.assertIn("answered stamp for ut-00000000 failed after delivery", err.getvalue())
        self.assertNotEqual(inspect.getsource(km._parked_answer_handed_over).strip().splitlines()[-1].strip(),
                            "return None", "the hook is no longer the no-op the send path left")

    def test_a_raising_stamp_at_the_drain_still_drains_the_rest_of_the_queue(self):
        tid, _ = self._park_an_answer()
        km._park_op(SID, ("send", "and one more thing", None))
        with mock.patch.object(km, "_resolve_user_todo", side_effect=RuntimeError("store went bad")), \
                contextlib.redirect_stderr(io.StringIO()):
            self._drain()
        self.assertEqual([s[1] for s in self.be.sent][-1], "and one more thing", "the sid's remaining ops still drained")
        self.assertFalse(km._pending_ops.get(SID))

    def test_a_dismiss_that_won_the_race_keeps_its_stamp(self):
        be = _FakeBackend()
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        self.assertTrue(km._resolve_user_todo(SID, tid, "dismissed"))
        km._deliver_send_batch(be, SID, [("send", body, None, None, True, None, tid)])
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed",
                         "the drain's stamp never overwrites the dismiss: the first stamp is the history")


class RecallRidesTheEntry(_StoreSandbox):
    """A recall of a still-queued answer reopens its request, on BOTH unqueue arms: the copy's id (the arm an
    SDK recall takes, since every entry there wears an echo: id) and the index with the body. The id rides the
    entry the backend hands back, never a kernel-side table, because the queue is persisted and a table would
    be empty after a restart."""

    def _answered(self, be, text="Need the auth-scheme decision to wire login", reply="Go with the session cookie."):
        tid = km._add_user_todo(SID, text)
        body = km._user_todo_answer_body(text, reply)
        self.assertIs(km._send_or_park(be, SID, body, user=True, user_todo=tid), False, "handed over now")
        km._stamp_user_todo_answered(SID, tid)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")
        return tid, body

    def setUp(self):
        super().setUp()
        self._saved = (km._compacting_now, km._working_now, km._limit_hold, dict(km._pending_ops))
        km._compacting_now = lambda sid, **k: False
        km._working_now = lambda sid: False
        km._limit_hold = lambda sid: False
        km._pending_ops.clear()

    def tearDown(self):
        km._compacting_now, km._working_now, km._limit_hold, ops = self._saved
        km._pending_ops.clear()
        km._pending_ops.update(ops)
        super().tearDown()

    def test_a_recall_by_the_copys_id_reopens(self):
        be = _FakeBackend()
        tid, body = self._answered(be)
        qid = be.meta[0]["qid"]
        self.assertRegex(qid, r"^echo:[0-9a-f]{32}$", "the shape an SDK recall carries")
        self.assertIsNone(km._cancel_backend_queued(be, SID, -1, None, qid=qid))
        self.assertEqual(be.queue, [], "the entry left the queue")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "recalled before it forwarded: the request stands again")

    def test_a_reopen_the_store_refuses_is_said_and_the_recall_still_answers(self):
        # the writer's RuntimeError (the store went bad between the recall and this write) never leaves the recall:
        # the entry is gone from the queue, the caller gets its None for the cancelResult, and stderr says why the
        # row still reads answered
        be = _FakeBackend()
        tid, body = self._answered(be)
        qid = be.meta[0]["qid"]
        err = io.StringIO()
        with mock.patch.object(km, "_write_user_todos", side_effect=RuntimeError("write refused")), \
                contextlib.redirect_stderr(err):
            self.assertIsNone(km._cancel_backend_queued(be, SID, -1, None, qid=qid))
        self.assertEqual(be.queue, [], "the recall itself succeeded")
        self.assertIn("refused the reopen", err.getvalue())
        self.assertIn(tid, err.getvalue())
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered", "the row is as it was")

    def test_a_reopen_whose_write_fails_is_said_and_the_recall_still_answers(self):
        # what the writer actually raises: _atomic_write re-raises an OSError (a disk error, a permission). The recall
        # itself succeeded, so the fault is said, with the fact that the recall's result still goes to the client, and
        # never raised: before this arm only RuntimeError was caught, against the function's own comment that the
        # cancelResult must reach the client, and an OSError left it for _dispatch_ws's per-message except
        be = _FakeBackend()
        tid, body = self._answered(be)
        qid = be.meta[0]["qid"]
        err = io.StringIO()
        with mock.patch.object(km, "_atomic_write", side_effect=OSError(errno.EIO, "Input/output error")), \
                contextlib.redirect_stderr(err):
            self.assertIsNone(km._cancel_backend_queued(be, SID, -1, None, qid=qid))
        self.assertEqual(be.queue, [], "the recall itself succeeded")
        lines = err.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertIn(tid, lines[0])
        self.assertIn("Input/output error", lines[0], "the fault is named")
        self.assertIn("still", lines[0], "and so is the fact that the recall's result is still sent")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered", "the row is as it was")

    def test_a_recall_by_index_and_body_reopens_too(self):
        be = _FakeBackend()
        tid, body = self._answered(be)
        self.assertIsNone(km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1]))
        self.assertNotIn("resolved", km._user_todos()[SID][0])

    def test_an_entry_reseeded_from_a_mirror_is_read_by_the_same_attribute(self):
        # a kernel restart: the queue is rebuilt from the registry mirror onto the SDK's own _TodoText, and the
        # recall reads the id off that object, so no kernel-side memory of the send is needed
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        km._stamp_user_todo_answered(SID, tid)
        mirror = {"text": body, "qid": "echo:" + "a" * 32, "qts": 1000, "todo": tid}
        be = _FakeBackend()
        be.queue.append(sb._TodoText(mirror["text"], mirror["todo"]))
        be.meta.append({"qid": mirror["qid"]})
        self.assertIsNone(km._cancel_backend_queued(be, SID, -1, None, qid=mirror["qid"]))
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the reseeded entry knows its request")

    def test_a_plain_entry_reopens_nothing(self):
        be = _FakeBackend()
        tid, body = self._answered(be)
        be.queue.pop(0); be.meta.pop(0)               # the input generator forwarded it: delivered
        be.send(SID, body, qid="echo:" + "b" * 32)   # a plain send, byte-identical, no user_todo
        self.assertIsNone(km._cancel_backend_queued(be, SID, -1, None, qid="echo:" + "b" * 32))
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "the delivered answer stands: nothing rode the lookalike entry")

    def test_a_recall_whose_row_is_not_answered_logs_and_returns_none(self):
        be = _FakeBackend()
        body = "Re: Need the staging port\n\n8443."
        be.send(SID, body, qid="echo:" + "c" * 32, user_todo="ut-00000000")
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertIsNone(km._cancel_backend_queued(be, SID, -1, None, qid="echo:" + "c" * 32))
        self.assertIn("nothing reopened", err.getvalue())
        self.assertIn("ut-00000000", err.getvalue())
        tid = km._add_user_todo(SID, "Need the port")
        km._resolve_user_todo(SID, tid, "dismissed")
        be.send(SID, "Re: Need the port\n\n8443.", qid="echo:" + "d" * 32, user_todo=tid)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(km._cancel_backend_queued(be, SID, 0, km._split_followup("Re: Need the port\n\n8443.")[1]))
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed", "a dismiss is never lifted")

    def test_a_miss_returns_the_too_late_text_on_both_arms(self):
        be = _FakeBackend()
        tid, body = self._answered(be)
        self.assertTrue(km._cancel_backend_queued(be, SID, -1, None, qid="echo:" + "f" * 32), "an unknown id is the miss")
        self.assertTrue(km._cancel_backend_queued(be, SID, 3, "not queued"), "an unknown body is the miss")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered", "a miss reopens nothing")

    def test_no_kernel_side_recall_table_exists(self):
        for name in ("_user_todo_recalls", "_USER_TODO_RECALLS_CAP", "_record_user_todo_recall"):
            self.assertFalse(hasattr(km, name), "%s must not exist: the id rides the queue entry" % name)


class LostAnswerReopens(_StoreSandbox):
    """A kernel death in the fed-but-unlanded window strands a stamped answer. The SDK backend hands the
    request id to _user_todo_answer_lost at the exact events that lose one, and the request visibly returns
    to the open rows unless the transcript proves the text landed."""

    def setUp(self):
        super().setUp()
        self._saved = (km._sessions, km._parse)
        self.turns = []
        km._sessions = lambda now, window=None, forks=True: [{"sid": SID, "path": "/dev/null"}]
        km._parse = lambda path, sid, now: {"turns": self.turns}

    def tearDown(self):
        km._sessions, km._parse = self._saved
        super().tearDown()

    def _stamped(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        body = km._user_todo_answer_body("Need the auth-scheme decision", "Cookie.")
        km._stamp_user_todo_answered(SID, tid)
        return tid, body

    def _land(self, text):
        self.turns = [{"atoms": [{"type": "user", "author": "human", "uuid": "u1",
                                  "message": {"role": "user", "content": [{"type": "text", "text": text}]}}]}]

    def test_a_lost_answer_reopens_the_request(self):
        tid, body = self._stamped()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_answer_lost(SID, tid, body, wait=True), "reopened")
        self.assertNotIn("resolved", km._user_todos()[SID][0])

    def test_a_landed_answer_keeps_its_stamp(self):
        tid, body = self._stamped()
        self._land(body)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_answer_lost(SID, tid, body, wait=True), "landed")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_a_landed_text_block_inside_a_bundle_counts(self):
        tid, body = self._stamped()
        self.turns = [{"atoms": [{"type": "user", "author": "human", "uuid": "u1",
                                  "message": {"role": "user", "content": [
                                      {"type": "text", "text": "a restart notice"},
                                      {"type": "text", "text": body}]}}]}]
        with contextlib.redirect_stderr(io.StringIO()):
            km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_an_image_path_rewritten_by_the_cli_still_reads_as_landed(self):
        # the CLI rewrites a pasted image path to [Image #N] before the submit: that form is the delivery too
        tid = km._add_user_todo(SID, "Need the mockup")
        body = km._user_todo_answer_body("Need the mockup", "Here: /TESTDIR/shots/login.png and done.")
        km._stamp_user_todo_answered(SID, tid)
        forms = km._paste_landed_texts(body)
        self.assertIn(body.strip(), forms)
        self.assertEqual(len(forms), 2)
        rewritten = next(f for f in forms if "[Image #1]" in f)
        self._land(rewritten)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_answer_lost(SID, tid, body, wait=True), "landed")

    def test_an_edge_whitespace_answer_reads_as_landed(self):
        tid, body = self._stamped()
        self._land(body + "\n")
        with contextlib.redirect_stderr(io.StringIO()):
            km._user_todo_answer_lost(SID, tid, body + "\n", wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_the_landed_match_is_exact_never_substring(self):
        tid, body = self._stamped()
        self._land("Quoting what I never received: " + body)
        with contextlib.redirect_stderr(io.StringIO()):
            km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertNotIn("resolved", km._user_todos()[SID][0], "an embedded match is not a delivery")

    def test_the_loss_path_never_lifts_a_dismiss(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "dismissed")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_answer_lost(SID, tid, "Re: Need the staging port\n\n8443.", wait=True), "stale")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed")

    def test_an_unparsable_transcript_fails_toward_the_visible_request(self):
        tid, body = self._stamped()

        def boom(path, sid, now):
            raise RuntimeError("corrupt transcript")

        km._parse = boom
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertNotIn("resolved", km._user_todos()[SID][0])
        self.assertIn("failed", err.getvalue(), "the broken check is said, not swallowed")

    def test_the_verdicts_name_what_happened(self):
        tid, body = self._stamped()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_answer_lost(SID, tid, body, wait=True), "reopened")
            self.assertEqual(km._user_todo_answer_lost(SID, tid, body, wait=True), "open",
                             "the row is open already: nothing to lift")
            km._resolve_user_todo(SID, tid, "dismissed")
            self.assertEqual(km._user_todo_answer_lost(SID, tid, body, wait=True), "stale")
            tid2, body2 = self._stamped()
            self._land(body2)
            self.assertEqual(km._user_todo_answer_lost(SID, tid2, body2, wait=True), "landed")
        with mock.patch.object(km.threading, "Thread") as th:
            self.assertIsNone(km._user_todo_answer_lost(SID, tid2, body2), "the threaded default answers nothing")
            self.assertTrue(th.called, "the check runs on a thread: the callers hold locks the check must not take")

    def test_a_sid_outside_the_48h_window_still_gets_the_landed_check(self):
        tid, body = self._stamped()
        self._land(body)
        km._sessions = self._saved[0]
        saved = km.jd.discover
        try:
            km.jd.discover = (lambda now, window=None, forks=True:
                              [] if window is None else [(SID, "/dev/null", SID, "web")])
            with contextlib.redirect_stderr(io.StringIO()):
                km._user_todo_answer_lost(SID, tid, body, wait=True)
        finally:
            km.jd.discover = saved
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "the transcript exists (the wide walk) and holds the answer: delivered")

    def test_no_transcript_anywhere_reopens_and_logs_the_skipped_check(self):
        tid, body = self._stamped()
        km._sessions = self._saved[0]
        saved = km.jd.discover
        try:
            km.jd.discover = lambda now, window=None, forks=True: []
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                km._user_todo_answer_lost(SID, tid, body, wait=True)
        finally:
            km.jd.discover = saved
        self.assertNotIn("resolved", km._user_todos()[SID][0], "no transcript to check: reopen anyway")
        self.assertIn("cannot run", err.getvalue(), "the skipped check is said, not silent")
        self.assertIn(tid, err.getvalue())

    def test_a_reopen_that_finds_no_answered_row_is_loud(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._user_todo_answer_lost(SID, "ut-00000000", "Re: Need the staging port\n\n8443.", wait=True)
        self.assertIn("nothing reopened", err.getvalue())
        self.assertIn("ut-00000000", err.getvalue())

    def test_a_reopen_the_store_cannot_write_is_said_and_the_seams_thread_ends_without_a_traceback(self):
        # what the writer raises: _atomic_write re-raises an OSError (a disk error, a permission), and _write_user_todos
        # raises RuntimeError while the store stands flagged. The reopen ran under the store lock with no catch, inside a
        # daemon thread whose other failures are caught and said, so the thread ended with a traceback and no verdict
        # line while the row went on reading answered. Caught now the way the recall's reopen is
        # (_cancel_backend_queued): one line naming the fault and what stands, and the inline verdict names it
        tid, body = self._stamped()
        fault = OSError(errno.EIO, "Input/output error")
        err = io.StringIO()
        with mock.patch.object(km, "_atomic_write", side_effect=fault), contextlib.redirect_stderr(err):
            self.assertIsNone(km._user_todo_answer_lost(SID, tid, body), "the threaded default")
            for t in threading.enumerate():
                if t.name == "user-todo-lost":
                    t.join(30)
                    self.assertFalse(t.is_alive(), "the seam's thread ended")
        self.assertNotIn("Traceback", err.getvalue(), err.getvalue())
        lines = err.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertIn(tid, lines[0])
        self.assertIn("Input/output error", lines[0], "the fault is named")
        self.assertIn("still", lines[0], "and what stands: the row still reads answered")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered", "the row is as it was")
        err = io.StringIO()
        with mock.patch.object(km, "_atomic_write", side_effect=fault), contextlib.redirect_stderr(err):
            self.assertEqual(km._user_todo_answer_lost(SID, tid, body, wait=True), "unwritten", "the verdict names it")
        self.assertEqual(len(err.getvalue().splitlines()), 1, err.getvalue())
        self.assertIn("could not write the reopen", err.getvalue())
        with mock.patch.object(km, "_write_user_todos", side_effect=RuntimeError("write refused")), \
                contextlib.redirect_stderr(err):
            self.assertEqual(km._user_todo_answer_lost(SID, tid, body, wait=True), "unwritten")
        self.assertIn("refused the reopen", err.getvalue(), "the writer's own refusal while the store stands flagged")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_the_kernel_passes_the_seam_to_the_backend_at_construction(self):
        # the callback must ride construction: the boot reseed fires drop marks from inside __init__
        src = inspect.getsource(km._sdk_locked)
        self.assertIn("todo_lost=_user_todo_answer_lost", src)

    def test_each_of_the_backends_four_loss_sites_reaches_a_constructor_callback(self):
        # executed against the real SDK backend on a sandbox root: an echo flagged dropped, a refused echo, a live
        # echo overtaken by a later turn, and a rewind-refused queue head each hand (sid, tid, text) to the
        # callback the kernel now passes; the kernel's own seam is exercised above, so a recorder stands in here
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        _hosts_off(root)
        lost = []
        be = sb.SdkBackend(root, "/bin/true", lambda *a, **k: None, reconcile=False,
                           todo_lost=lambda sid, tid, text: lost.append((sid, tid, text)))
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        answer = "Re: the staging port\n\n8443."

        def echo(key, t):
            return key, {"uuid": key, "t": t, "_echo_text": answer, "_echo_key": key, "author": "human", "rompAuto": False,
                         "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": answer}]},
                         "_todo": "ut-11111111"}
        k, e = echo("echo:1", 1000)
        be._live[SID] = {k: e}
        be._mark_dropped_echoes(SID, [], refeed=False)                   # a spawn or boot orphaned the send
        self.assertEqual(lost, [(SID, "ut-11111111", answer)], "the drop mark names the request once")
        k, e = echo("echo:2", int(time.time()))
        be._live[SID] = {k: e}
        self.assertEqual(be.mark_echo_refused(SID, answer, "a replayed schedule slot"), 1)
        self.assertEqual(lost[-1], (SID, "ut-11111111", answer), "the refusal names it")
        k, e = echo("echo:3", 1000)
        be._live[SID] = {k: e}
        be.settle_echoes(SID, human_floor=2000)
        self.assertEqual(lost[-1], (SID, "ut-11111111", answer), "the live settle names it")
        self.assertEqual(len(lost), 3)
        s = sb.SdkSession(be, sb.read_reg(Path(root), SID))
        s.enqueue(answer, todo="ut-22222222")
        s._rewind_to = "5a5a5a5a-1111-4222-8333-944444444499"
        s._rewind_bare = False
        s._rewind_failed(RuntimeError("refused"))
        self.assertEqual(lost[-1], (SID, "ut-22222222", answer), "the refused rewind names the head's request")
        self.assertEqual(len(lost), 4, "one call per site")


class LossBootPass(_StoreSandbox):
    """_user_todo_loss_boot_pass: every boot re-derives the pending losses from the persisted world (an echo
    drop-marked, carrying a request id, whose store row still reads answered) and hands each to the
    landed-check-then-reopen seam. An install with no answered row reads the store and nothing else."""

    def setUp(self):
        super().setUp()
        self._saved = (km._sessions, km._parse)
        self.turns = []
        km._sessions = lambda now, window=None, forks=True: [{"sid": SID, "path": "/dev/null"}]
        km._parse = lambda path, sid, now: {"turns": self.turns}

    def tearDown(self):
        km._sessions, km._parse = self._saved
        super().tearDown()

    def _reg(self, echoes, sid=SID):
        d = jd.STATE / "sdk"
        d.mkdir(parents=True, exist_ok=True)
        (d / (sid + ".json")).write_text(json.dumps({"sid": sid, "alive": True, "echoes": echoes}))

    def _stamped(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        km._stamp_user_todo_answered(SID, tid)
        return tid, body

    def test_a_marked_then_died_loss_reopens_on_the_next_boot(self):
        tid, body = self._stamped()
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": True, "todo": tid}])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 1)
        self.assertNotIn("resolved", km._user_todos()[SID][0])

    def test_a_landed_answer_keeps_its_stamp_through_the_pass(self):
        tid, body = self._stamped()
        self.turns = [{"atoms": [{"type": "user", "author": "human", "uuid": "u1",
                                  "message": {"role": "user", "content": [{"type": "text", "text": body}]}}]}]
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": True, "todo": tid}])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 1)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_rows_not_reading_answered_are_not_offered(self):
        tid, body = self._stamped()
        km._reopen_user_todo(SID, tid)
        tid2 = km._add_user_todo(SID, "Need the auth-scheme decision")
        km._resolve_user_todo(SID, tid2, "dismissed")
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": True, "todo": tid},
                   {"t": 2, "text": "Re: auth\n\ncookie.", "author": "human", "dropped": True, "todo": tid2}])
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0)
        self.assertNotIn("resolved", km._user_todos()[SID][0])
        self.assertEqual(km._user_todos()[SID][1]["resolved"]["kind"], "dismissed")

    def test_unmarked_or_idless_echoes_are_not_offered(self):
        tid, body = self._stamped()
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": False, "todo": tid},
                   {"t": 2, "text": "an ordinary lost send", "author": "human", "dropped": True}])
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_one_offer_per_request_however_many_echoes_carry_it(self):
        tid, body = self._stamped()
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": True, "todo": tid},
                   {"t": 2, "text": body, "author": "human", "dropped": True, "todo": tid}])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 1)

    def test_a_store_with_no_answered_row_reads_no_registry_at_all(self):
        # the short-circuit: off, or never answered, means the boot pays one store read and nothing else
        tid = km._add_user_todo(SID, "Need the staging port")
        self._reg([{"t": 1, "text": "x", "author": "human", "dropped": True, "todo": tid}])
        read = []
        real = Path.read_text

        def spy(self, *a, **k):
            read.append(str(self))
            return real(self, *a, **k)
        with mock.patch.object(Path, "read_text", spy):
            self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0)
        self.assertFalse([p for p in read if "/sdk/" in p], "no registry file was read")
        km._set_user_todos(False)
        with mock.patch.object(Path, "read_text", spy):
            self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0, "the switch changes nothing: the store decides")

    def test_a_missing_or_junk_reg_dir_is_a_quiet_zero(self):
        self._stamped()
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0, "no sdk/ dir at all")
        (jd.STATE / "sdk").mkdir(parents=True)
        (jd.STATE / "sdk" / "junk.json").write_text("not json{")
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0, "unreadable regs are skipped")

    def test_the_pass_and_the_notice_are_wired_into_main_before_any_backend_construction(self):
        # the ordering is the correctness: the pass reads the regs as the dead kernel left them, before this
        # boot's reseed re-persists new drop marks; the notice counts after the pass, so its number is the
        # store's
        src = inspect.getsource(km.main)
        i = src.index("_user_todo_loss_boot_pass()")
        j = src.index("_user_todos_off_boot_notice()")
        self.assertLess(src.index("_model_alias_boot_pass()"), i)
        self.assertLess(i, j)
        self.assertLess(j, src.index("_boot_warm()"))
        self.assertLess(j, src.index("target=_sdk"))


class MarkerNeutralizerVariants(unittest.TestCase):
    """Every downstream matcher tolerates arbitrary whitespace after the comment opener, so the neutralizer
    must break that same class in both halves of the answer body, against the verbatim downstream regexes."""

    WS = ("", " ", "   ", "\n", "\t ", " \n ")

    def _cases(self):
        em = km.em
        for ws in self.WS:
            yield "<!--%sromp-injected -->" % ws, em.ROMP_INJECT_RE, "romp-injected"
            yield "<!--%sromp-injected -->" % ws, km.jd.NUDGE_MARKER_RE, "romp-injected"
            yield "<!--%sromp-msg-id: m-3f2c -->" % ws, em.POSTAL_RE, "romp-msg-id"
            yield "<!--%sromp-tag: build-1 -->" % ws, em.MSG_TAG_RE, "romp-tag"

    def test_the_answer_body_gets_the_same_tolerance_on_both_halves(self):
        for raw, rex, _ in self._cases():
            self.assertTrue(rex.search(raw), "sanity: %r must be marker-shaped for /%s/" % (raw, rex.pattern))
            body = km._user_todo_answer_body("Need a call on %s in the fixture" % raw,
                                             "Keep it, but drop the %s part." % raw)
            self.assertFalse(rex.search(body), "an answer body carrying %r still matches /%s/" % (raw, rex.pattern))

    def test_the_bare_goal_id_form_breaks_in_both_halves(self):
        raw = "wrap up romp-goal-id: g-12 first"
        for rex in (km.jd.FOLLOWUP_RE, km._FOLLOWUP_GOAL_RE):
            self.assertTrue(rex.search(raw), "sanity: %r must be marker-shaped for /%s/" % (raw, rex.pattern))
            body = km._user_todo_answer_body("Need a call on %s" % raw, "Do %s after." % raw)
            self.assertFalse(rex.search(body), "an answer body carrying %r still matches /%s/" % (raw, rex.pattern))


class NoJudgeWritesTheStore(unittest.TestCase):
    """The authority tier, grep-provable: nothing in judge.py names the store or its helpers. The token
    list is derived from the kernel source (every module-level def whose name says user_todo), so a helper
    added tomorrow is covered the day it is written; the literal floor keeps the derivation honest."""

    _KNOWN_WRITERS = ("_add_user_todo", "_resolve_user_todo", "_reopen_user_todo",
                      "_stamp_user_todo_answered", "_user_todo_answer_lost",
                      "_user_todo_loss_boot_pass", "_write_user_todos", "_withdraw_user_todo", "_prune_user_todos")

    def test_judge_py_never_touches_the_store(self):
        kdir = Path(HERE).parent / "kernel"
        src = (kdir / "judge.py").read_text()
        tokens = set(re.findall(r"^def (\w*user_todo\w*)\(", (kdir / "kernel.py").read_text(), re.M))
        for w in self._KNOWN_WRITERS:
            self.assertIn(w, tokens, "the derivation no longer sees %s: fix the pattern, never the floor" % w)
        tokens |= {"user-todos.json", "_user_todos"}
        for token in sorted(tokens):
            self.assertNotIn(token, src)


class NoInferenceWritesTheStore(unittest.TestCase):
    """NoJudgeWritesTheStore's sibling, one file over: the kernel holds card movers of its own outside
    judge.py, so this parses kernel.py and resolves every call of a store writer to the def or method it
    runs in (a nested def resolves to its outermost one). That set must be exactly the allow-list: each
    entry acts on an event the person or the agent produced, never on a judgment."""

    WRITERS = ("_add_user_todo", "_resolve_user_todo", "_reopen_user_todo", "_write_user_todos",
               "_stamp_user_todo_answered", "_user_todo_answer_lost", "_withdraw_user_todo",
               "_prune_user_todos")

    ALLOWED = {
        # the helpers calling each other: the tier's own plumbing
        "_add_user_todo", "_resolve_user_todo", "_reopen_user_todo", "_stamp_user_todo_answered",
        "_user_todo_answer_lost", "_withdraw_user_todo", "_prune_user_todos",
        # the routes' own functions (the agent's tool call, by the postal bus's POST or the Codex postal tool's
        # direct call) and the drive handler (the person's click)
        "_user_todo_register_route", "_user_todo_withdraw_route", "_drive",
        # the drain's handover report (the delivery verdict)
        "_parked_answer_handed_over",
        # the person's own recall of a queued answer
        "_cancel_backend_queued",
        # the boot pass over persisted loss marks, and the housekeeping pass the prune rides
        "_user_todo_loss_boot_pass", "_jobs_pass",
    }
    # the kernel's card movers, named in the equality pin's message: none of them may become a caller
    MOVERS = ("_mark_nudge_failed", "_nudge_fire_list", "_record_interrupt_block", "_lift_interrupt_block",
              "build_feed", "build_session", "_auto_nudge_tick", "_chat_tab_sessions")

    @classmethod
    def _callers(cls):
        src = (Path(HERE).parent / "kernel" / "kernel.py").read_text()
        tree = ast.parse(src)
        defs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        found = {}

        def qual(chain):
            if not chain:
                return "<module>"
            kind, name = chain[0]
            if kind == "class" and len(chain) > 1:
                return name + "." + chain[1][1]
            return name

        def walk(node, chain):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.ClassDef):
                    walk(child, chain + [("class", child.name)])
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    walk(child, chain + [("def", child.name)])
                else:
                    if isinstance(child, ast.Call):
                        f = child.func
                        name = (f.id if isinstance(f, ast.Name)
                                else f.attr if isinstance(f, ast.Attribute) else None)
                        if name in cls.WRITERS:
                            found.setdefault(qual(chain), set()).add(name)
                    walk(child, chain)
        walk(tree, [])
        return defs, found

    def test_every_store_writer_is_called_only_from_the_allow_list(self):
        defs, found = self._callers()
        for w in self.WRITERS:
            self.assertIn(w, defs, "the writer list names a def kernel.py no longer has: %s" % w)
        self.assertEqual(set(found), self.ALLOWED,
                         "store writers are called from defs outside the allow-list (or an allow-listed def no "
                         "longer calls one: prune it); the kernel's own card movers (%s) stay outside it, since a "
                         "request is the session's word and never an inference: %s"
                         % (", ".join(self.MOVERS), sorted(set(found) ^ self.ALLOWED)))

    def test_the_derivation_sees_the_helpers_calling_each_other(self):
        _defs, found = self._callers()
        self.assertEqual(found["_add_user_todo"], {"_write_user_todos"})
        self.assertEqual(found["_stamp_user_todo_answered"], {"_resolve_user_todo"})
        self.assertEqual(found["_parked_answer_handed_over"], {"_stamp_user_todo_answered"})
        self.assertEqual(found["_cancel_backend_queued"], {"_reopen_user_todo"})


class ContextBlock(_StoreSandbox):
    """Memory across context loss (plans/user-todos.md, segment C): _user_todo_context_block renders a session's
    OPEN requests as the agent's OWN outstanding notes to the person it works for, the passive block the
    SessionStart hook (hooks/romp-usertodo-context.sh) hands to a resumed, compacted or cleared session over
    POST /usertodo/context, so an agent whose working memory was wiped remembers what it asked for and
    withdraws the ones that are met or moot. Voice-scanned by tests/test_injected_voice.py."""

    HEADER = "Notes you still have open with the person you work for, things you said you needed from them:"
    WITHDRAW = "If one is met or moot now, withdraw it (withdraw_user_todo); otherwise leave it standing."

    def _seed(self, rows, sid=SID):
        (jd.STATE / "user-todos.json").write_text(json.dumps({sid: rows}))
        km._user_todos_cache.clear()

    def test_no_open_rows_mean_no_block_at_all(self):
        # a session with nothing open gets NOTHING: the hook prints no line, so no noise on every resume
        self.assertEqual(km._user_todo_context_block(SID), "")
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "withdrawn")
        self.assertEqual(km._user_todo_context_block(SID), "", "resolved rows render nothing")

    def test_the_block_is_the_header_one_bullet_per_row_and_the_withdraw_line(self):
        self._seed([{"id": "ut-11111111", "createdT": NOW - 86400,
                     "text": "Need the auth-scheme decision to wire login"}])
        block = km._user_todo_context_block(SID)
        day = km.time.strftime("%Y-%m-%d", km.time.localtime(NOW - 86400))
        self.assertEqual(block.splitlines(), [
            self.HEADER,
            "- Need the auth-scheme decision to wire login (ut-11111111, opened %s)" % day,
            "",
            self.WITHDRAW])
        self.assertTrue(block.isascii(), "plain ASCII throughout: no dash or ellipsis glyphs")

    def test_a_row_without_text_or_date_still_renders(self):
        # a garbled row (no text, no clock) is still the agent's own open note: a placeholder title and no
        # date rather than a vanished row or a raise
        self._seed([{"id": "ut-11111111"}])
        block = km._user_todo_context_block(SID)
        self.assertIn("- (untitled) (ut-11111111)", block)
        self.assertNotIn("opened", block)

    def test_detail_stays_behind_the_short_line(self):
        # the block carries the one short line only; the longer context lives on the card
        self._seed([{"id": "ut-11111111", "createdT": NOW, "text": "Need the auth-scheme decision",
                     "detail": "OAuth vs cookie: either unblocks login"}])
        self.assertNotIn("OAuth vs cookie", km._user_todo_context_block(SID))

    def test_newest_first_and_cut_at_twelve_with_a_tail(self):
        cut = km._USER_TODO_CONTEXT_CAP
        self._seed([{"id": "ut-%08d" % i, "createdT": NOW + i, "text": "Need decision %d" % i}
                    for i in range(cut + 3)])
        block = km._user_todo_context_block(SID)
        bullets = [ln for ln in block.splitlines() if ln.startswith("- ")]
        self.assertEqual(len(bullets), cut + 1, "twelve bullets plus the tail")
        self.assertIn("Need decision %d" % (cut + 2), bullets[0], "the newest ask leads")
        self.assertEqual(bullets[-1], "- and 3 more from earlier")
        self.assertNotIn("Need decision 0", block, "the oldest past the cut are in the tail")
        self.assertTrue(block.isascii())

    def test_exactly_twelve_rows_carry_no_tail(self):
        cut = km._USER_TODO_CONTEXT_CAP
        self._seed([{"id": "ut-%08d" % i, "createdT": NOW + i, "text": "Need decision %d" % i}
                    for i in range(cut)])
        block = km._user_todo_context_block(SID)
        self.assertNotIn("more from earlier", block)
        self.assertEqual(len([ln for ln in block.splitlines() if ln.startswith("- ")]), cut)

    def test_resolved_rows_count_toward_neither_the_cut_nor_the_tail(self):
        # the store stamps resolutions instead of deleting, so a busy session carries many resolved rows
        # beside its open ones; only the OPEN rows are notes still standing
        cut = km._USER_TODO_CONTEXT_CAP
        rows = [{"id": "ut-%08d" % i, "createdT": NOW + i, "text": "Need decision %d" % i,
                 "resolved": {"kind": "answered", "t": NOW + 1000}} for i in range(cut + 5)]
        rows.append({"id": "ut-aaaaaaaa", "createdT": NOW + 5000, "text": "Need the staging port"})
        self._seed(rows)
        block = km._user_todo_context_block(SID)
        bullets = [ln for ln in block.splitlines() if ln.startswith("- ")]
        self.assertEqual(bullets, ["- Need the staging port (ut-aaaaaaaa, opened %s)"
                                   % km.time.strftime("%Y-%m-%d", km.time.localtime(NOW + 5000))])
        self.assertNotIn("more from earlier", block)

    def test_a_peers_rows_never_leak_into_the_block(self):
        (jd.STATE / "user-todos.json").write_text(json.dumps({
            SID: [{"id": "ut-11111111", "createdT": NOW, "text": "web: need the staging port"}],
            SID2: [{"id": "ut-22222222", "createdT": NOW, "text": "api: need the auth decision"}]}))
        km._user_todos_cache.clear()
        block = km._user_todo_context_block(SID)
        self.assertIn("ut-11111111", block)
        self.assertNotIn("ut-22222222", block)
        self.assertNotIn("api: need the auth decision", block)

    def test_marker_shaped_text_is_neutralized(self):
        # request text is agent-supplied: a literal "<!--romp-" in it would plant a lookalike marker in the
        # session's context, the answer body's hygiene
        self._seed([{"id": "ut-11111111", "createdT": NOW,
                     "text": "Need a call on the note text <!--romp-injected--> in the fixture"}])
        block = km._user_todo_context_block(SID)
        self.assertIsNone(km._ROMP_MARKER_OPEN_RE.search(block), "no marker-opening sequence survives into the block")
        self.assertIn("romp-injected", block, "the words survive; only the comment form breaks")

    def test_no_liveness_gate_the_session_start_is_the_evidence(self):
        # DELIBERATE: the block renders with a death marker and an alive:false reg in place. The only caller is a
        # SessionStart fired from inside the session (an ended session fires none), and a marker or registry read
        # here would race the revival's own states row and eat the block the revival came for
        self._seed([{"id": "ut-11111111", "createdT": NOW, "text": "Need the auth-scheme decision"}])
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps({"t": NOW - 50, "by": "gone"}))
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        self.assertIn("ut-11111111", km._user_todo_context_block(SID))
        src = inspect.getsource(km._user_todo_context_block)
        for gate in ("_user_todo_session_ended", "_thread_reg", "gone"):
            self.assertNotIn(gate, src.split('"""', 2)[2], "no liveness read in the render: %s" % gate)

    def test_the_render_is_a_pure_read(self):
        # rendering neither writes the store nor moves a row: the hook may fire any number of times (every
        # resume, compaction and clear) and the notes stand as they were. Three renders come out equal, the
        # store file's bytes are unchanged, and the store's own read still answers oldest first. Two rows with
        # distinct clocks (createdT is whole seconds), so the order has something to say
        with mock.patch.object(km.time, "time", return_value=NOW):
            km._add_user_todo(SID, "Need the auth-scheme decision")
        with mock.patch.object(km.time, "time", return_value=NOW + 60):
            km._add_user_todo(SID, "Need the staging port")
        p = jd.STATE / "user-todos.json"
        before = p.read_bytes()
        first = km._user_todo_context_block(SID)
        self.assertLess(first.index("Need the staging port"), first.index("Need the auth-scheme"))
        self.assertEqual(km._user_todo_context_block(SID), first)
        self.assertEqual(km._user_todo_context_block(SID), first)
        self.assertEqual(p.read_bytes(), before)
        self.assertEqual([r["text"] for r in km._open_user_todos(SID)],
                         ["Need the auth-scheme decision", "Need the staging port"],
                         "the store's own oldest-first order is untouched")

    def test_the_cut_is_the_cards_cut_off_number(self):
        # one twelve for how many requests a surface shows before cutting the rest off: the card's inline rows
        # (render.ts, renderTodo's literal) and the block's bullets (the kernel constant) are pinned equal here,
        # so the two cannot drift without failing this test
        render = (Path(HERE).parent / "ui" / "webview" / "render.ts").read_text()
        m = re.search(r"const UT_INLINE_ROWS = (\d+);", render)
        self.assertIsNotNone(m, "the card's inline-rows constant moved: re-point this pin")
        self.assertEqual(km._USER_TODO_CONTEXT_CAP, int(m.group(1)))
        self.assertEqual(km._USER_TODO_CONTEXT_CAP, 12)


class ContextRoute(_StoreSandbox):
    """POST /usertodo/context, the read the SessionStart hook stands on. Token-gated like its siblings;
    READ-ONLY: it neither writes the store nor wakes the pusher (nothing changed); answered by THIS kernel
    from its own store, never forwarded (the hook asks the kernel on the session's own host, which owns
    that session's store); no liveness gate (the SessionStart is the evidence)."""

    def setUp(self):
        super().setUp()
        self._push = (km._push_all, km._push_soon)
        self.addCleanup(setattr, km, "_push_all", km._push_all)
        self.addCleanup(setattr, km, "_push_soon", km._push_soon)
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synchronous _push_all on the context read"))
        km._push_soon = lambda: (_ for _ in ()).throw(
            AssertionError("_push_soon on a read-only route: nothing changed"))

    def tearDown(self):
        km._push_all, km._push_soon = self._push
        super().tearDown()

    def _post(self, path, body, token=True):
        hdrs = {"X-Romp-Token": km.TOKEN} if token else {}
        code, out = _serve_post(path, body, hdrs)
        try:
            return code, json.loads(out.decode() or "{}")
        except ValueError:
            return code, {}

    def test_requires_the_serve_token(self):
        code, _ = self._post("/usertodo/context", {"id": SID}, token=False)
        self.assertEqual(code, 403)
        code, res = self._post("/usertodo/context", {"id": SID})
        self.assertEqual((code, res.get("ok")), (200, True),
                         "the same ask with the token is answered, so the 403 gated a route that exists")

    def test_refuses_a_bodyless_or_idless_ask(self):
        code, res = self._post("/usertodo/context", {})
        self.assertEqual((code, res), (400, {"ok": False, "error": "id required"}))
        code, _ = _serve_post("/usertodo/context", b"not json", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400)

    def test_a_body_that_is_not_an_object_is_a_400_never_a_crash(self):
        # through _json_object_body, the session-management routes' one parser: a list decodes and is refused
        # with the helper's own wording, not an AttributeError into the dispatcher's 500
        code, res = self._post("/usertodo/context", ["not", "an", "object"])
        self.assertEqual(code, 400)
        self.assertIs(res.get("ok"), False)
        self.assertIn("JSON object", res.get("error", ""))

    def test_returns_the_rendered_block_for_open_rows(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        code, res = self._post("/usertodo/context", {"id": SID})
        self.assertEqual(code, 200)
        self.assertIs(res["ok"], True)
        self.assertIs(res["enabled"], True)
        self.assertEqual(res["block"], km._user_todo_context_block(SID))
        self.assertIn(ContextBlock.HEADER, res["block"])

    def test_an_unknown_sid_answers_an_empty_block_not_an_error(self):
        # the hook fires for every romp session that resumes, compacts or clears: nothing to say is the
        # common case and a clean empty answer, never a loud one
        code, res = self._post("/usertodo/context", {"id": SID2})
        self.assertEqual(code, 200)
        self.assertIs(res["ok"], True)
        self.assertEqual(res["block"], "")

    def test_the_read_never_writes_the_store(self):
        km._add_user_todo(SID, "Need the auth-scheme decision")
        p = jd.STATE / "user-todos.json"
        before = p.read_bytes()
        code, res = self._post("/usertodo/context", {"id": SID})
        self.assertEqual((code, res.get("ok")), (200, True), "the read happened")
        self.assertEqual(p.read_bytes(), before)

    def test_an_ended_session_is_still_answered(self):
        km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        code, res = self._post("/usertodo/context", {"id": SID})
        self.assertEqual(code, 200)
        self.assertIn("Need the auth-scheme decision", res["block"])

    def test_answers_with_task_tracking_off(self):
        # independent of the Task tracking switch (T404): the route answers from the store read and never runs the
        # feed build, so the block arrives with tracking off, like the card. Nothing here reads the tracking file
        (jd.STATE / km.TASK_TRACKING_FILE).write_text(json.dumps({"enabled": False, "gt": 1}))
        self.assertFalse(km._task_tracking_on(), "the fixture: tracking is off")
        km._add_user_todo(SID, "Need the auth-scheme decision")
        code, res = self._post("/usertodo/context", {"id": SID})
        self.assertEqual(code, 200)
        self.assertIs(res["enabled"], True)
        self.assertIn("Need the auth-scheme decision", res["block"])

    def test_a_remote_sid_is_answered_locally_never_forwarded(self):
        # /usertodo and /usertodo/withdraw forward to the session's host; this read must not: the only caller
        # is the hook on the session's OWN host, and a forward from a dashboard host that federates this
        # session would ask a kernel with no such SessionStart in flight
        km._add_user_todo(SID, "Need the auth-scheme decision")
        with mock.patch.object(km, "_host_for_sid", lambda sid: {"host": "TESTHOST"}), \
                mock.patch.object(km, "_remote_forward", side_effect=AssertionError("the context read forwarded")), \
                mock.patch.object(km, "_remote_forward_status", side_effect=AssertionError("the context read forwarded")):
            code, res = self._post("/usertodo/context", {"id": SID})
        self.assertEqual(code, 200)
        self.assertIn("Need the auth-scheme decision", res["block"])


# ── the ambient surfaces' data (plans/user-todos.md): the feed frame's request map and the status rows' count ─────────
def _ut_memo_snapshot():
    """(the entries, the counters, the fault episodes) as they stand, handed back in tearDown."""
    with km._feed_memo_lock:
        return (dict(km._feed_memo), json.loads(json.dumps(km._FEED_MEMO_STATS)), dict(km._FEED_DERIVE_FAILED))


def _ut_memo_restore(snap):
    entries, stats, failed = snap
    with km._feed_memo_lock:
        km._feed_memo.clear(); km._feed_memo.update(entries)
        km._FEED_MEMO_STATS.clear(); km._FEED_MEMO_STATS.update(stats)
        km._FEED_DERIVE_FAILED.clear(); km._FEED_DERIVE_FAILED.update(failed)


def _ut_memo_reset():
    """The feed memo empty and its counters at zero (tests/test_feed_session_memo.py's idiom): every case starts cold."""
    with km._feed_memo_lock:
        km._feed_memo.clear()
        st = km._FEED_MEMO_STATS
        for k in ("hit", "miss", "evict", "derived", "entries", "bytes", "failed", "coldLive", "coldFlip"):
            if k in st:
                st[k] = 0
        for k in st["miss_by"]:
            st["miss_by"][k] = 0
        for k in st.get("row_by", {}):
            st["row_by"][k] = 0
        km._FEED_DERIVE_FAILED.clear()


class FeedSeamUserTodos(unittest.TestCase):
    """The data behind the ambient surfaces (the request flag on the tab, the quiet marker on the feed cards, the
    phone's mirror): build_feed's sid-keyed `userTodos` map of OPEN request counts, derived inside the memoized
    per-session entry with the sorted open ids as a key component (a register, answer, dismiss or withdraw moves the
    owning session's key and no other; a text edit moves nothing), and the status rows' `openRequests` count on
    build_session and _light_status (one reader and one gate behind the rows and the count, so the tab and the card
    cannot disagree). The ended gate here is the live map: a session build_feed's loop never visits (not alive)
    contributes nothing and its rows stay in the store; a muted session contributes nothing while its status keeps
    the count (the feed goes quiet, the tab stays truthful). The requests switch is read through the store reader
    alone: off reads zero everywhere and the rows stay.

    World: BuildSessionSeam's for two sessions (web and api), a discoverable transcript and a names entry each,
    `_sessions` patched to the two rows (the cold-start shape: no parse, no anchor), the live map handed to
    build_feed so _alive_sessions is the REAL filter, `_warm_fleet_bg` a no-op, the feed memo reset per case.
    Private synthetic sids; every case builds the real build_feed, build_session and _light_status."""
    WEB, API = SID, SID2

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        proj = td / "projects"
        state = td / "state"
        state.mkdir()
        _hosts_off(state)
        self.saved = (jd.STATE, jd.PROJECTS, km.NAMES, km.WORKING_DIR, km._GLOBAL_CLAUDE_MD, km._live_map, km._sdk,
                      km._sessions, km._warm_fleet_bg, os.environ.get("CLAUDE_CONFIG_DIR"), km._read_task_store,
                      dict(km._pending_ops))
        self.saved_memo = _ut_memo_snapshot()
        jd._rebind_state(state)                       # every STATE-derived dir (goals, states, gone, sdk, ...)
        jd.PROJECTS = proj
        jd.NAMES.mkdir()
        km.NAMES = jd.NAMES
        km.WORKING_DIR = state / "working"
        km._GLOBAL_CLAUDE_MD = td / "no-global-claude.md"
        os.environ["CLAUDE_CONFIG_DIR"] = str(td / "claude")
        self.tpath, self.rows = {}, []
        for sid, name, color in ((self.WEB, "web", "#1EA1EB"), (self.API, "api", "#E67E22")):
            cdir = td / ("launch-" + name)
            cdir.mkdir()
            pdir = proj / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
            pdir.mkdir(parents=True)
            tp = pdir / (sid + ".jsonl")
            tp.write_text("\n".join(json.dumps(r) for r in [
                {"type": "user", "uuid": "u1", "timestamp": "2026-06-01T00:00:00Z", "sessionId": sid,
                 "message": {"role": "user", "content": "wire the notes-api %s routes" % name}},
                {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "timestamp": "2026-06-01T00:00:05Z",
                 "sessionId": sid, "message": {"role": "assistant", "stop_reason": "end_turn",
                                               "content": [{"type": "text", "text": "starting on the routes"}]}},
            ]) + "\n")
            (jd.NAMES / sid).write_text("%s\t%s\t%s\twhite\n" % (name, cdir, color))
            self.tpath[sid] = tp
            self.rows.append({"sid": sid, "name": name, "anchor": None, "path": str(tp), "mtime": 0})
        self.live = {self.WEB: self._row(), self.API: self._row()}
        km._live_map = lambda: self.live
        km._sdk = lambda: None
        km._sessions = lambda now, window=None, forks=True: [dict(r) for r in self.rows]
        km._warm_fleet_bg = lambda now: None
        km._read_task_store = lambda fsid, fold=None: []
        km._pending_ops.clear()
        km._built_chat.clear()
        km._parse_cache.clear()
        km._flags_cache.clear()
        km._live_scope.names = None
        km._live_scope.snapshot = None
        km._live_scope.sessions = None
        jd._discover_cache.clear()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._user_todos_switch_cache.clear()
        km._set_user_todos(True)
        _ut_memo_reset()

    def tearDown(self):
        (state, proj, names, wdir, gmd, live_fn, sdk, sessions, warm, cfg, rts, ops) = self.saved
        _ut_memo_restore(self.saved_memo)
        jd._rebind_state(state)
        jd.PROJECTS = proj
        km.NAMES, km.WORKING_DIR, km._GLOBAL_CLAUDE_MD, km._live_map, km._sdk = names, wdir, gmd, live_fn, sdk
        km._sessions, km._warm_fleet_bg, km._read_task_store = sessions, warm, rts
        if cfg is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = cfg
        km._pending_ops.clear()
        km._pending_ops.update(ops)
        km._built_chat.clear()
        km._parse_cache.clear()
        km._flags_cache.clear()
        km._live_scope.names = None
        km._live_scope.snapshot = None
        km._live_scope.sessions = None
        jd._discover_cache.clear()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._user_todos_switch_cache.clear()
        self.td.cleanup()

    @staticmethod
    def _row():
        return {"state": "idle", "since": NOW - 100, "model": "", "effort": "", "context": None,
                "compactPct": None, "color": None, "backend": "sdk"}

    def _feed(self, now=NOW, live=None):
        f = km.build_feed(now, self.live if live is None else live)
        self.assertEqual(km._FEED_DERIVE_FAILED, {}, "a session's card build raised inside build_feed")
        return f

    def _session(self, sid):
        km._parse_cache.clear()
        km._built_chat.clear()
        return km.build_session(sid, NOW, live_map=self.live)

    def _light(self, sid):
        return km._light_status(sid, str(self.tpath[sid]), self.live[sid], NOW)

    def _delta(self, fn):
        """(the memo counters' movement over fn(), fn's result): hit / derived and the non-zero miss attributions."""
        b = km._feed_memo_report()
        out = fn()
        a = km._feed_memo_report()
        d = {k: a[k] - b[k] for k in ("hit", "miss", "derived")}
        d["miss_by"] = {k: v - b["miss_by"].get(k, 0) for k, v in a["miss_by"].items() if v - b["miss_by"].get(k, 0)}
        return d, out

    def test_the_map_carries_open_counts_per_sid(self):
        km._add_user_todo(self.WEB, "Need your pick of the two route layouts")
        km._add_user_todo(self.WEB, "Need the staging database name")
        tid = km._add_user_todo(self.API, "Need a test credential for the api session")
        km._withdraw_user_todo(self.API, tid)
        self.assertEqual(self._feed()["userTodos"], {self.WEB: 2}, "open rows only: a resolved-only session is absent")

    def test_the_key_always_rides_and_reads_empty_for_a_request_less_world(self):
        f = self._feed()
        self.assertIn("userTodos", f, "a dict, never a missing key: federation's merge and the client's guard see an honest empty map")
        self.assertEqual(f["userTodos"], {})

    def test_a_session_absent_from_the_live_map_contributes_nothing_and_its_rows_stay(self):
        km._add_user_todo(self.WEB, "Need your pick of the two route layouts")
        live = {self.API: self.live[self.API]}          # web is not alive: _alive_sessions drops it, the map has no key for it
        self.assertEqual(self._feed(live=live)["userTodos"], {})
        self.assertTrue(km._open_user_todos(self.WEB), "hidden, not cleared: the row stays for the revival")

    def test_a_revived_session_counts_again(self):
        km._add_user_todo(self.WEB, "Need your pick of the two route layouts")
        self.assertEqual(self._feed(live={self.API: self.live[self.API]})["userTodos"], {})
        self.assertEqual(self._feed()["userTodos"], {self.WEB: 1}, "back in the live map: the count is back")

    def test_a_muted_session_contributes_nothing_while_its_status_keeps_the_count(self):
        km._add_user_todo(self.WEB, "Need your pick of the two route layouts")
        (jd.STATE / "session-flags.json").write_text(json.dumps({self.WEB: {"hideFromFeed": True}}))
        km._flags_cache.clear()
        self.assertEqual(self._feed()["userTodos"], {}, "the feed goes quiet for a muted session")
        self.assertEqual(self._session(self.WEB)["status"]["openRequests"], 1, "the tab stays truthful about what its session holds")
        self.assertEqual(self._light(self.WEB)["openRequests"], 1)

    def test_an_ended_session_reads_zero_on_both_status_rows_while_its_rows_stay(self):
        km._add_user_todo(self.WEB, "Need your pick of the two route layouts")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        reg = jd.STATE / "sdk" / (self.WEB + ".json")
        reg.write_text(json.dumps({"alive": False}))    # ended-but-revivable: the registry's alive bit, build_session's own gate
        self.assertEqual(self._light(self.WEB)["openRequests"], 0, "an unbuilt tab's flag is off while its session is ended")
        sess = self._session(self.WEB)
        self.assertEqual(sess["status"]["openRequests"], 0, "and the built status agrees: one gate behind both legs")
        self.assertEqual(sess["userTodos"], [], "the card hides the rows the same way")
        self.assertEqual(len(km._open_user_todos(self.WEB)), 1, "hidden, not cleared: the row stays for the revival")
        reg.write_text(json.dumps({"alive": True}))
        self.assertEqual(self._light(self.WEB)["openRequests"], 1, "revived: both legs read the row again")
        self.assertEqual(self._session(self.WEB)["status"]["openRequests"], 1)

    def test_the_map_serializes_stably_across_builds_and_clocks(self):
        km._add_user_todo(self.API, "Need a test credential for the api session")
        km._add_user_todo(self.WEB, "Need your pick of the two route layouts")
        a = json.dumps(self._feed()["userTodos"])
        b = json.dumps(self._feed(now=NOW + 3600)["userTodos"])
        self.assertEqual(a, b, "store values only: an hour later, the same bytes")
        self.assertEqual(set(json.loads(a)), {self.WEB, self.API})
        # The alive order REVERSED: _alive_sessions keeps _sessions' order, which follows the listing (mtimes, in
        # production), so the loop now visits api before web while the sid order is web (...01) before api (...02).
        # An unsorted map would carry the listing order and re-send the frame on every listing move.
        km._sessions = lambda now, window=None, forks=True: [dict(r) for r in reversed(self.rows)]
        c = self._feed()["userTodos"]
        self.assertEqual(list(c), sorted([self.WEB, self.API]), "sid-sorted whatever the alive order")
        self.assertEqual(json.dumps(c), a, "the same bytes from the other listing order: the frame's dedup holds")

    def test_a_register_re_derives_the_owning_session_alone_through_a_warm_memo(self):
        self._feed()
        d, _ = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"]), (0, 2), "warm: an unchanged rebuild derives nothing")
        km._add_user_todo(self.API, "Need a test credential for the api session")
        d, f = self._delta(self._feed)
        self.assertEqual(f["userTodos"], {self.API: 1})
        self.assertEqual((d["derived"], d["hit"]), (1, 1), "the register re-derived api and served web: %r" % d)
        self.assertEqual(d["miss_by"], {"usertodos": 1}, "attributed to the request component")
        d, f = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"]), (0, 2), "and stands: a hit")
        self.assertEqual(f["userTodos"], {self.API: 1})

    def test_the_view_sig_watches_the_store(self):
        before = km._fleet_view_sig(NOW, self.live)
        self.assertEqual(before, km._fleet_view_sig(NOW, self.live), "the signature is a function of the inputs")
        km._add_user_todo(self.WEB, "Need your pick of the two route layouts")
        self.assertNotEqual(before, km._fleet_view_sig(NOW, self.live), "a register moves the feed's signature at once, not at the 5 s bucket")

    def test_the_off_frame_carries_no_map_and_the_status_rows_keep_the_count(self):
        km._add_user_todo(self.WEB, "Need your pick of the two route layouts")
        self.assertNotIn("userTodos", km._feed_off_frame(NOW, self.live), "the off frame is unchanged: no map")
        self.assertEqual(self._light(self.WEB)["openRequests"], 1, "the tab flag survives tracking off")
        self.assertEqual(self._session(self.WEB)["status"]["openRequests"], 1)

    def test_the_requests_switch_off_reads_zero_everywhere_and_keeps_the_rows(self):
        km._add_user_todo(self.WEB, "Need your pick of the two route layouts")
        self.assertEqual(self._feed()["userTodos"], {self.WEB: 1})
        km._set_user_todos(False)
        self.assertEqual(self._feed()["userTodos"], {})
        self.assertEqual(self._session(self.WEB)["status"]["openRequests"], 0)
        self.assertEqual(self._light(self.WEB)["openRequests"], 0)
        self.assertEqual(len(km._user_todos().get(self.WEB) or []), 1, "the store keeps the row for the day the switch flips back")

    def test_the_status_count_is_the_payload_rows_count(self):
        for n in (0, 1, 3):
            while len(km._open_user_todos(self.WEB)) < n:
                km._add_user_todo(self.WEB, "Need your pick of layout %d" % len(km._open_user_todos(self.WEB)))
            sess = self._session(self.WEB)
            self.assertEqual(len(sess["userTodos"]), n)
            self.assertEqual(sess["status"]["openRequests"], n, "one reader, one gate: the tab and the card cannot disagree")
            self.assertEqual(self._light(self.WEB)["openRequests"], n)


class HookWiring(unittest.TestCase):
    """The hook, the installer and the uninstaller agree on one file, one route and one name (repo text, read
    the way the shell suites read it): a rename in one place fails here instead of silently disabling the hook
    on every install."""

    ROOT = Path(HERE).parent

    def test_the_hook_stats_the_kernels_switch_file_and_asks_its_route(self):
        text = (self.ROOT / "hooks" / "romp-usertodo-context.sh").read_text()
        self.assertIn(km.USER_TODOS_SWITCH_FILE, text, "the stat and the kernel name one file")
        self.assertIn("/usertodo/context", text)
        self.assertIn("resume|compact|clear", text, "the three sources, as one case list")

    def test_install_sh_links_it_and_registers_it_sync_at_session_start(self):
        text = (self.ROOT / "install.sh").read_text()
        loop = text[text.index("for h in romp-postal-drain.sh"):]
        self.assertIn("romp-usertodo-context.sh", loop[:loop.index("; do")], "the symlink loop names it")
        want = text[text.index('"SessionStart":'):text.index('"UserPromptSubmit":')]
        self.assertIn('("romp-usertodo-context.sh", 5, False)', want,
                      "sync with a 5 s timeout: an async SessionStart hook's additionalContext is not read")

    def test_romp_uninstall_removes_the_link_and_the_registration(self):
        text = (self.ROOT / "bin" / "romp-uninstall").read_text()
        loop = text[text.index("for h in romp-summarize.sh"):]
        self.assertIn("romp-usertodo-context.sh", loop[:loop.index("; do")], "the rm loop names it")
        ours = text[text.index("OURS = {"):]
        self.assertIn('"romp-usertodo-context.sh"', ours[:ours.index("}")], "OURS names it")

    def test_the_hook_is_executable(self):
        p = self.ROOT / "hooks" / "romp-usertodo-context.sh"
        self.assertTrue(p.exists(), "no hook file")
        self.assertTrue(p.stat().st_mode & stat.S_IXUSR, "the execute bit is off: Claude Code cannot run it")


# ── segment E: the idle floor, the nudge stand-down, the badge and the latch ───────────────────────────────────────

class EscalationFloorPredicate(_StoreSandbox):
    """The floor's ARMING read (_user_todo_idle): True only when the session has SETTLED idle with a BLOCKING request
    open and nothing else in motion (no open turn, nothing dispatched, no live prompt, no compaction, no human message on
    its way in, no peer owing it a reply), the exact idle the status nudge requires. The queued-intent bit and the
    compaction bit are ARGUMENTS the key computes (both values driven here); the states log and the interrupt gate are
    read through their own helpers. Every stand-down is a real event; a mid-turn lull never arms; a settled record holds
    the floor through a turn the user did not open. Synthetic turns and a private state root."""

    PS = {"turns": [{"id": "t1", "t": NOW - 60, "end": NOW - 30, "ended": True, "atoms": []}]}
    BLOCKING = ["ut-11111111"]

    def setUp(self):
        super().setUp()
        km._UT_FLOOR_ARM.clear()
        self.addCleanup(km._UT_FLOOR_ARM.clear)

    def _idle(self, sid=SID, ps=None, who_working=False, awaiting=None, perm_state=None, aerr=None,
              last_state=("waiting", NOW - 20), queued=False, compacting=False, interrupted=False,
              peer_wait=None, blocking=None):
        patches = [
            mock.patch.object(km, "_last_state", lambda s: last_state),
            mock.patch.object(km, "_interrupt_suppresses_nudge", lambda turns, s="", **k: interrupted),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return km._user_todo_idle(sid, self.PS if ps is None else ps, who_working, awaiting, perm_state, aerr,
                                  peer_wait, queued, compacting, self.BLOCKING if blocking is None else blocking)

    def test_a_settled_idle_session_with_a_blocking_request_arms(self):
        self.assertTrue(self._idle())
        self.assertEqual(km._UT_FLOOR_ARM.get(SID), (frozenset(self.BLOCKING), NOW - 30),
                         "the record: the blocking set and the settled turn's end")
        self.assertEqual(km._ut_floor_record(SID), (("ut-11111111",), NOW - 30), "the key's view of it, sorted")

    def test_only_non_blocking_requests_never_arm(self):
        self.assertFalse(self._idle(blocking=[]), "a non-blocking request is information the card shows, not a stop")
        self.assertNotIn(SID, km._UT_FLOOR_ARM)
        self.assertIsNone(km._ut_floor_record(SID))

    def test_an_open_turn_never_arms(self):
        self.assertFalse(self._idle(who_working=True))
        self.assertNotIn(SID, km._UT_FLOOR_ARM)

    def test_dispatched_background_work_never_arms(self):
        self.assertFalse(self._idle(awaiting="waiting on 2 agents"))

    def test_a_live_prompt_or_the_compaction_bit_never_arms(self):
        self.assertFalse(self._idle(perm_state="permission"))
        self.assertFalse(self._idle(perm_state="picker"))
        self.assertFalse(self._idle(perm_state="compacting"))
        self.assertFalse(self._idle(compacting=True), "the bit is the argument; the predicate reads no clock")
        self.assertNotIn(SID, km._UT_FLOOR_ARM)

    def test_an_api_error_wins(self):
        self.assertFalse(self._idle(aerr={"status": 529, "text": "overloaded"}))

    def test_a_human_message_on_its_way_in_spends_the_record_and_a_machine_entry_holds_it(self):
        self.assertTrue(self._idle(), "armed at the settle")
        self.assertTrue(self._idle(who_working=True, queued=False),
                        "a turn the user did not open, nothing of theirs queued: the record holds the floor")
        self.assertFalse(self._idle(who_working=True, queued=True), "the user's message is queued: their move")
        self.assertNotIn(SID, km._UT_FLOOR_ARM, "spent, not suppressed")
        self.assertFalse(self._idle(who_working=True), "no record: an open turn is not idle")
        self.assertFalse(self._idle(queued=True), "and a settle under queued intent does not arm either")

    def test_a_user_interrupt_spends_it(self):
        self.assertTrue(self._idle())
        self.assertFalse(self._idle(interrupted=True))
        self.assertNotIn(SID, km._UT_FLOOR_ARM)

    def test_an_unreadable_interrupt_gate_reads_unknown_never_idle(self):
        seen = []

        def boom(turns, sid="", **k):
            seen.append((len(turns), sid))
            raise RuntimeError("unreadable")
        self.assertTrue(self._idle(), "armed first")
        with mock.patch.object(km, "_last_state", lambda s: ("waiting", NOW - 20)), \
             mock.patch.object(km, "_interrupt_suppresses_nudge", boom):
            self.assertFalse(km._user_todo_idle(SID, self.PS, False, None, None, None, None, False, False,
                                                self.BLOCKING))
        self.assertEqual(seen, [(1, SID)], "asked once, with the turns and the sid")
        self.assertIn(SID, km._UT_FLOOR_ARM, "unknown touches nothing: the record stands")

    def test_waiting_on_a_live_peer_never_floors_and_the_edge_lifting_lets_it_arm(self):
        edge = {"peerSid": SID2, "name": "api", "color": None, "inCycle": False, "since": NOW - 900, "kind": "question"}
        self.assertFalse(self._idle(peer_wait=edge), "the idle is the peer's to explain")
        self.assertNotIn(SID, km._UT_FLOOR_ARM)
        self.assertTrue(self._idle(peer_wait=None), "the peer's reply drops the edge: the floor may claim the idle")
        self.assertFalse(self._idle(peer_wait=edge), "a new ask to a live peer spends the record")
        self.assertNotIn(SID, km._UT_FLOOR_ARM)

    def test_no_parse_or_no_turns_reads_unknown_never_idle(self):
        self.assertFalse(self._idle(ps={}))
        self.assertFalse(self._idle(ps={"turns": []}))
        self.assertFalse(km._user_todo_idle(SID, None, False, None, None, None, None, False, False, self.BLOCKING))
        self.assertNotIn(SID, km._UT_FLOOR_ARM)

    def test_a_mid_turn_lull_never_arms(self):
        # the states log progressing AT or AFTER the parsed turn's end: the stop is not real (the nudge's own discriminator)
        self.assertFalse(self._idle(last_state=("working", NOW - 10)))
        self.assertFalse(self._idle(last_state=("working", NOW - 30)))
        self.assertNotIn(SID, km._UT_FLOOR_ARM)

    def test_a_stale_progressing_record_before_the_turn_end_does_not_wedge(self):
        self.assertTrue(self._idle(last_state=("working", NOW - 40)), "a lost post-turn write must not pin the floor off")

    def test_the_deciding_events_re_derive_it_cleanly(self):
        def opened_by(author, text="a word from someone"):
            settled = dict(self.PS["turns"][0])
            atom = {"uuid": "u2", "type": "user", "author": author, "t": NOW - 10,
                    "message": {"role": "user", "content": text}}
            return {"turns": [settled, {"id": "t2", "t": NOW - 10, "trigger": {"uuid": "u2"}, "atoms": [atom]}]}

        def absorbed(author):
            held = dict(self.PS["turns"][0])
            held.pop("end", None)
            held.pop("ended", None)
            held["atoms"] = [{"uuid": "u2", "type": "user", "author": author, "t": NOW - 10,
                              "message": {"role": "user", "content": "a word from someone"}}]
            return {"turns": [held]}
        peer = {"peer": SID2, "mid": "m-11111111", "kind": "coordinate"}
        self.assertFalse(self._idle(who_working=True), "nothing armed: an open turn is not idle")
        self.assertTrue(self._idle(), "the settle arms the record")
        self.assertTrue(self._idle(ps=opened_by(peer), who_working=True), "a peer-opened turn holds the floor")
        self.assertTrue(self._idle(ps=opened_by("romp"), who_working=True), "a romp reminder holds it")
        self.assertTrue(self._idle(ps=absorbed("system"), who_working=True), "a harness notification absorbed into the settled turn holds it")
        self.assertFalse(self._idle(ps=absorbed("human"), who_working=True), "the human's message absorbed into a turn they did not open stands it down")
        self.assertTrue(self._idle(), "the next settle re-arms it")
        self.assertFalse(self._idle(ps=opened_by("human"), who_working=True), "the human opening a turn stands it down")
        self.assertFalse(self._idle(ps=opened_by(peer), who_working=True), "and spends the record: the next peer turn finds nothing to hold")
        self.assertTrue(self._idle(), "the next settle re-arms it")
        self.assertTrue(self._idle(blocking=["ut-11111111", "ut-22222222"]),
                        "the blocking set changing spends the old record; settled idle under the new set, the same read re-arms on it")
        self.assertEqual(km._UT_FLOOR_ARM.get(SID), (frozenset({"ut-11111111", "ut-22222222"}), NOW - 30),
                         "the new set is the record")
        self.assertFalse(self._idle(ps=opened_by(peer), who_working=True, blocking=["ut-11111111"]),
                         "under an open turn the set changing stands the floor down: the record is spent and nothing holds")

    def test_a_same_count_swap_of_the_blocking_set_is_a_set_change(self):
        # the record is the blocking IDS, never their count: one withdrawn and another filed in one step spends it
        self.assertTrue(self._idle(blocking=["ut-11111111"]))
        self.assertFalse(self._idle(who_working=True, blocking=["ut-22222222"]),
                         "under an open turn the swapped set stands the floor down: the record is spent and nothing holds")
        self.assertNotIn(SID, km._UT_FLOOR_ARM)
        self.assertTrue(self._idle(blocking=["ut-22222222"]), "the settle re-arms on the new id")
        self.assertEqual(km._UT_FLOOR_ARM.get(SID), (frozenset({"ut-22222222"}), NOW - 30))

    def test_the_stand_down_read_is_a_bounded_tail_walk(self):
        # 400 ended turns before the arm, then a turn a peer opened: the walk scans the atoms of the turns after the
        # settled one alone and stops at the first turn that closed at or before the record's end, so a re-derivation
        # of a long session costs the tail, not the transcript. The earlier turns' atom lists count their iterations
        reads = []

        class Counted(list):
            def __iter__(self):
                reads.append(len(self))
                return super().__iter__()
        turns = []
        for i in range(400):
            t = NOW - 100000 + i * 100
            turns.append({"id": "t%d" % i, "t": t, "end": t + 30, "ended": True, "trigger": {"uuid": "u%d" % i},
                          "atoms": Counted([{"uuid": "u%d" % i, "type": "user", "author": "human", "t": t,
                                             "message": {"role": "user", "content": "step %d" % i}}])})
        settled_end = turns[-1]["end"]
        self.assertTrue(self._idle(ps={"turns": list(turns)}))
        self.assertEqual(km._UT_FLOOR_ARM[SID][1], settled_end)
        peer = {"peer": SID2, "mid": "m-11111111", "kind": "coordinate"}
        held = {"id": "t400", "t": NOW - 10, "trigger": {"uuid": "u400"},
                "atoms": [{"uuid": "u400", "type": "user", "author": peer, "t": NOW - 10,
                           "message": {"role": "user", "content": "a word from a peer"}}]}
        self.assertTrue(self._idle(ps={"turns": turns + [held]}, who_working=True), "a peer-opened turn: held")
        self.assertEqual(reads, [], "no atom of the 400 earlier turns was read: the walk stopped at the settled turn")
        self.assertIn(SID, km._UT_FLOOR_ARM, "the record stands")
        # the bound is the TURN's end, not the atom's stamp: an atom stamped after the arm inside a turn that closed at
        # or before it is never reached (the walk stops before that turn), where a walk over every turn would read it
        planted = dict(turns[-1], atoms=[dict(turns[-1]["atoms"][0], uuid="u399-late", t=settled_end + 5)])
        self.assertFalse(km._human_atom_since(turns[:-1] + [planted, held], settled_end))
        self.assertEqual(reads, [])
        # the human speaking in the tail is found with one read, the tail's own
        after = dict(held, atoms=[{"uuid": "u400", "type": "user", "author": "human", "t": NOW - 10,
                                   "message": {"role": "user", "content": "the cookie, for now"}}])
        seen = []
        real = km.em.is_interrupt_record

        def counting(a):
            seen.append(a.get("uuid"))
            return real(a)
        with mock.patch.object(km.em, "is_interrupt_record", counting):
            self.assertFalse(self._idle(ps={"turns": turns + [after]}, who_working=True), "the human spoke: spent")
        self.assertEqual(seen, ["u400"], "one atom read: the turn after the arm, never the 400 before it")
        self.assertEqual(reads, [], "and still none of the earlier turns' atoms")
        self.assertNotIn(SID, km._UT_FLOOR_ARM)

    def test_the_tail_walk_reads_the_resumed_last_turn_whole(self):
        # an idle-led turn that resumed keeps the new prompt in the SAME last turn: the last turn is scanned whole even
        # when its own time is before the record's end
        held = dict(self.PS["turns"][0])
        held.pop("end", None)
        held.pop("ended", None)
        held["atoms"] = [{"uuid": "u0", "type": "user", "author": "human", "t": NOW - 60,
                          "message": {"role": "user", "content": "wire the login routes"}}]
        self.assertTrue(km._human_atom_since({"turns": [held]}["turns"], NOW - 30) is False,
                        "the arm's own human atom is at or before the settle: not news")
        held["atoms"].append({"uuid": "u1", "type": "user", "author": "human", "t": NOW - 5,
                              "message": {"role": "user", "content": "use the cookie"}})
        self.assertTrue(km._human_atom_since([held], NOW - 30), "the resumed turn's new human atom is news")
        rec = {"uuid": "u2", "type": "user", "author": "human", "t": NOW - 4,
               "message": {"role": "user", "content": [{"type": "text", "text": "[Request interrupted by user]"}]}}
        self.assertFalse(km._human_atom_since([dict(held, atoms=[held["atoms"][0], rec])], NOW - 30),
                         "an interrupt record authors human and is excluded (the interrupt gate owns it)")


class _FloorWorld(unittest.TestCase):
    """FeedSeamUserTodos' world (two live sessions, real transcripts, the real build_feed over the live map, the memo
    reset per case) with the parse, the peer-wait graph and the judge-auth latch under the test's hand, a raw goal
    store per session and the states log written under STATE. Borrows the seam class's setUp and tearDown as functions,
    so D's cases run once and not under every class here."""
    WEB, API = FeedSeamUserTodos.WEB, FeedSeamUserTodos.API
    _row = staticmethod(FeedSeamUserTodos._row)
    _feed = FeedSeamUserTodos._feed
    _delta = FeedSeamUserTodos._delta
    PEER = {"peer": FeedSeamUserTodos.API, "mid": "m-11111111", "kind": "coordinate"}

    def setUp(self):
        FeedSeamUserTodos.setUp(self)
        self._by_path = {str(p): sid for sid, p in self.tpath.items()}
        self._ps = {}
        self.wmap = {}
        self.jauth = {}
        patches = [
            mock.patch.object(km, "_parse_cached", lambda path: self._ps.get(self._by_path.get(str(path)))),
            mock.patch.object(km, "_merge_live_atoms", lambda ps, sid: ps),
            mock.patch.object(km, "_wait_for_graph", lambda now, sids: dict(self.wmap)),
            mock.patch.object(jd, "_auth_down_map", lambda: dict(self.jauth)),
            mock.patch.object(km, "_provisional_card", lambda *a, **k: None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        km._UT_FLOOR_ARM.clear()
        km._last_state_cache.clear()
        self.addCleanup(km._UT_FLOOR_ARM.clear)
        self.addCleanup(km._last_state_cache.clear)

    def tearDown(self):
        FeedSeamUserTodos.tearDown(self)

    # ── the world's writers ──
    @staticmethod
    def _turn(tid, t, author, ended=True, text="wire the login routes"):
        """One parsed turn whose trigger atom carries `author`: 'human', 'romp' or a peer's postal author dict. An ended
        turn ends 30 s after it opens; an open one has no end and no idle tail, what _session_working reads as open."""
        atom = {"uuid": tid + "-u", "type": "user", "author": author, "t": t, "message": {"role": "user", "content": text}}
        turn = {"id": tid, "t": t, "trigger": {"uuid": tid + "-u"}, "atoms": [atom]}
        if ended:
            turn["end"] = t + 30
            turn["ended"] = True
        return turn

    def _set_turns(self, sid, turns):
        self._ps[sid] = {"turns": list(turns)}

    def _states(self, sid, *rows):
        d = jd.STATE / "states"
        d.mkdir(parents=True, exist_ok=True)
        (d / (sid + ".jsonl")).write_text("".join(json.dumps({"t": t, "state": v}) + "\n" for v, t in rows))
        km._last_state_cache.clear()

    def _store(self, sid, nodes, status, last, confirming=()):
        full = {}
        for gid, nd in nodes.items():
            full[gid] = dict({"id": gid, "parentId": None, "t": NOW - 500, "mt": NOW - 500, "nodeComplete": False,
                              "blocked": False, "cleared": False, "trail": ["s1"], "log": []}, **nd)
        store = {"rompUuid": sid, "seq": 1, "rev": 1, "placementsV": jd.PLACEMENTS_V, "placements": {},
                 "nodes": full, "status": dict(status), "lastNode": last, "confirming": list(confirming)}
        p = jd.GOALDIR / (sid + ".json")
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(store))
        os.replace(tmp, p)

    def _one_goal(self, sid, text="wire the login flow"):
        self._store(sid, {"g1": {"text": text}}, {"g1": "working"}, "g1")

    def _settle(self, sid):
        """The arming shape: one human turn ended at NOW-30 and the post-turn 'waiting' row after it."""
        self._set_turns(sid, [self._turn("t1", NOW - 60, "human")])
        self._states(sid, ("working", NOW - 55), ("waiting", NOW - 25))

    # ── the backend's queue read ──
    _NO_META = object()                                # the shape of a backend without pending_queued_meta (Codex)

    def _queue_meta(self, meta):
        """km.Sessions.backend_for answers a stand-in over the backend the world resolves, whose pending_queued_meta(sid)
        reads self._qmeta[sid] at call time: a list of entry metas, None for identities the backend cannot vouch for, an
        exception instance to raise, [] for a sid absent from it; self._qmeta set to _NO_META leaves the method off the
        stand-in altogether. Every other attribute is the resolved backend's own. Restored at cleanup."""
        self._qmeta = meta
        real = km.Sessions.backend_for
        world = self

        class Stub:
            def __init__(self, inner):
                self._inner = inner

            def __getattr__(self, name):
                if name == "pending_queued_meta":
                    if world._qmeta is _FloorWorld._NO_META:
                        raise AttributeError(name)

                    def read(sid):
                        v = world._qmeta.get(str(sid), [])
                        if isinstance(v, BaseException):
                            raise v
                        return v
                    return read
                return getattr(self._inner, name)
        p = mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: Stub(real(sid))))
        p.start()
        self.addCleanup(p.stop)

    # ── the reads ──
    @staticmethod
    def _card(feed, iid):
        return next(a for a in feed["asks"] if a["itemId"] == iid)

    @staticmethod
    def _mine(feed, sid):
        return [a for a in feed["asks"] if str(a.get("sid")) == sid]

    def _column(self, sid=None, iid="g1"):
        return self._card(self._feed(), iid)["column"]


class EscalationFloorWiring(_FloorWorld):
    """The floor through the REAL build_feed: it yields to every live interrupt, files the focus card under needs_input
    with the board's field pair and the story, gives a goal-less session the placeholder (its `_ageT` in the memoized
    entry, its trgb stamped on the wire), treats a floored card as working-equivalent in the provisional chain, and
    stands down on the peer-wait edge."""

    def setUp(self):
        super().setUp()
        self.tid = km._add_user_todo(self.WEB, "Need the auth-scheme decision to wire login", blocking=True)
        self._one_goal(self.WEB)
        self._settle(self.WEB)

    def test_a_settled_idle_session_floors_the_focus_card_with_the_story(self):
        feed = self._feed()
        g1 = self._card(feed, "g1")
        self.assertEqual((g1["column"], g1["board"], g1["category"]), ("needs_input", "feed", "needs_input"))
        self.assertEqual(g1["blocked"], {"state": "userTodos", "count": 1, "open": 1, "what": km._USER_TODO_BLOCK_WHAT})
        self.assertEqual(g1["distillState"], "blocked", "the brief keys on the genuine block")
        self.assertNotIn("usertodo:" + self.WEB, [a["itemId"] for a in feed["asks"]], "the focus card carries the story: no placeholder beside it")
        self.assertEqual(feed["userTodos"], {self.WEB: 1}, "the marker's map still rides")
        self.assertEqual(km._UT_FLOOR_ARM.get(self.WEB), (frozenset({self.tid}), NOW - 30), "armed at the settle")

    def test_the_count_is_the_blocking_count_and_open_is_every_open_row(self):
        km._add_user_todo(self.WEB, "Need a staging credential for the tests")   # not blocking
        km._add_user_todo(self.WEB, "Need the staging port", blocking=True)
        g1 = self._card(self._feed(), "g1")
        self.assertEqual((g1["blocked"]["count"], g1["blocked"]["open"]), (2, 3))

    def test_a_non_blocking_request_alone_never_floors(self):
        km._withdraw_user_todo(self.WEB, self.tid)
        km._add_user_todo(self.WEB, "Need your opinion on the route names")
        feed = self._feed()
        g1 = self._card(feed, "g1")
        self.assertEqual(g1["column"], "working")
        self.assertIsNone(g1.get("blocked"))
        self.assertEqual(feed["userTodos"], {self.WEB: 1}, "the marker shows it; no card moves")
        self.assertNotIn(self.WEB, km._UT_FLOOR_ARM)

    def test_the_floor_yields_to_every_live_interrupt(self):
        # a live permission prompt: the perm floor takes the card in the same column, wearing its own story
        self.live[self.WEB]["state"] = "permission"
        g1 = self._card(self._feed(), "g1")
        self.assertEqual((g1["column"], g1["blocked"]["state"]), ("needs_input", "permission"))
        self.live[self.WEB]["state"] = "idle"
        # the judges' credential refused: the judge-auth floor wins
        self.jauth = {self.WEB: {"mode": "key", "t": NOW - 100}}
        g1 = self._card(self._feed(), "g1")
        self.assertEqual((g1["column"], g1["blocked"]["state"]), ("needs_input", "judgeAuth"))
        self.jauth = {}
        # an API error on the transcript's tail that is on the user (the prompt too long): the api floor wins. The
        # patched read is not a keyed input (the real error sits in the transcript the key reads), so the memo is
        # reset between these phases, the way the memo tests reset it
        _ut_memo_reset()
        with mock.patch.object(km, "_api_error", lambda path: {"status": 400, "text": "prompt is too long", "tooLong": True, "t": NOW - 20}):
            g1 = self._card(self._feed(), "g1")
        self.assertEqual((g1["column"], g1["blocked"]["state"]), ("needs_input", "apiError"))
        # a transient API error keeps the api floor's own Working-with-badge shape, and the request floor still yields to it
        _ut_memo_reset()
        with mock.patch.object(km, "_api_error", lambda path: {"status": 529, "text": "overloaded", "t": NOW - 20}):
            g1 = self._card(self._feed(), "g1")
        self.assertEqual((g1["column"], g1["blocked"]["state"]), ("working", "apiError"))
        _ut_memo_reset()
        g1 = self._card(self._feed(), "g1")
        self.assertEqual(g1["blocked"]["state"], "userTodos", "the present event gone, the floor returns at the same settle")

    def test_a_goal_less_session_gets_the_placeholder_with_age_in_the_entry_and_tint_on_the_wire(self):
        self._store(self.WEB, {}, {}, None)
        feed = self._feed()
        mine = self._mine(feed, self.WEB)
        self.assertEqual([a["itemId"] for a in mine], ["usertodo:" + self.WEB])
        ph = mine[0]
        self.assertTrue(ph["provisional"])
        self.assertEqual((ph["column"], ph["board"], ph["category"]), ("needs_input", "feed", "needs_input"))
        self.assertEqual(ph["blocked"], {"state": "userTodos", "count": 1, "open": 1, "what": km._USER_TODO_BLOCK_WHAT})
        self.assertEqual(ph["text"], "Need the auth-scheme decision to wire login", "the oldest blocking request titles it")
        self.assertEqual(ph["tree"], [])
        self.assertIn("trgb", ph, "_feed_fold_card stamps the tint on the wire")
        self.assertNotIn("_ageT", ph)
        ent = json.loads(km._feed_memo_get(self.WEB)[1])
        held = ent["asks"][0]
        self.assertIn("_ageT", held, "the memoized entry holds the epoch, never the tint")
        self.assertNotIn("trgb", held)
        self.assertEqual(held["t"], held["_ageT"], "the newest blocking request's time")
        self.assertEqual(feed["userTodos"], {self.WEB: 1})

    def test_the_placeholder_titles_the_oldest_blocking_request_and_counts_the_other_blocking_ones(self):
        km._add_user_todo(self.WEB, "Need your opinion on the route names")               # not blocking: not in the title
        km._add_user_todo(self.WEB, "Need the staging port", blocking=True)
        with km._user_todos_lock:                              # date the rows: minted in one second, the store's sort would tie on id
            cur = dict(km._user_todos())
            rows = [dict(t) for t in cur.get(self.WEB) or []]
            for t in rows:
                t["createdT"] = NOW - 300 if t["id"] == self.tid else NOW - 100
            cur[self.WEB] = rows
            km._write_user_todos(cur)
        self._store(self.WEB, {}, {}, None)
        ph = self._mine(self._feed(), self.WEB)[0]
        self.assertEqual(ph["text"], "Need the auth-scheme decision to wire login  (+1 more)")
        self.assertEqual((ph["blocked"]["count"], ph["blocked"]["open"]), (2, 3))

    def test_the_provisional_chain_treats_a_floored_card_as_working(self):
        dummy = {"itemId": "provisional:" + self.WEB, "sid": self.WEB, "name": "web", "color": None,
                 "text": "Analyzing: wire the login flow", "t": NOW, "live": True, "_ageT": None,
                 "turnId": None, "origin": None, "followupPending": None, "summary": None, "blockSummary": None,
                 "background": None, "blocked": None, "column": "working", "board": "feed", "category": "working",
                 "provisional": True, "tree": []}
        with mock.patch.object(km, "_provisional_card", lambda *a, **k: dict(dummy)):
            feed = self._feed()
        ids = [a["itemId"] for a in self._mine(feed, self.WEB)]
        self.assertEqual(ids, ["g1"], "no Analyzing placeholder beside the floored card: %r" % ids)
        self.assertEqual(self._card(feed, "g1")["blocked"]["state"], "userTodos")

    def test_the_floor_is_not_a_judge_verdict(self):
        # the store file is untouched by the move (NoInferenceWritesTheStore holds the writer allow-list; here the
        # goal store): the column is derived, never filed
        p = jd.GOALDIR / (self.WEB + ".json")
        before = p.read_bytes()
        self.assertEqual(self._column(), "needs_input")
        self.assertEqual(p.read_bytes(), before, "the goal store is read, never written, by the floor")
        self.assertNotIn("resolved", km._user_todos()[self.WEB][0], "and the request store is untouched")

    def test_the_peer_wait_edge_stands_it_down(self):
        self.assertEqual(self._column(), "needs_input")
        self.wmap = {self.WEB: {"peerSid": self.API, "name": "api", "color": None, "inCycle": False,
                                "since": NOW - 5, "kind": "question"}}
        g1 = self._card(self._feed(), "g1")
        self.assertEqual(g1["column"], "working", "a live peer owes this session a reply: the idle is the peer's")
        self.assertNotIn(self.WEB, km._UT_FLOOR_ARM, "spent")


class EscalationFloorLive(_FloorWorld):
    """The stand-down stories through the real build: the events that move the card (the human speaking, a
    human-authored parked message, a set change, a peer wait) and the events that hold it (a peer-opened turn, a romp
    reminder, a harness notification, a lull, a machine parked message)."""

    def setUp(self):
        super().setUp()
        self.tid = km._add_user_todo(self.WEB, "Need the auth-scheme decision to wire login", blocking=True)
        self._one_goal(self.WEB)

    def _turns(self, *turns):
        self._set_turns(self.WEB, list(turns))

    def test_an_open_turn_with_no_record_keeps_the_card_working(self):
        self._turns(self._turn("t1", NOW - 60, "human", ended=False))
        self._states(self.WEB, ("working", NOW - 55))
        g1 = self._card(self._feed(), "g1")
        self.assertEqual(g1["column"], "working")
        self.assertIsNone(g1.get("blocked"))

    def test_a_progressing_state_after_the_turn_end_is_a_lull_not_a_stop(self):
        self._turns(self._turn("t1", NOW - 60, "human"))
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 20))
        self.assertEqual(self._column(), "working")
        self.assertNotIn(self.WEB, km._UT_FLOOR_ARM)

    def test_a_withdraw_stands_the_floor_down(self):
        self._settle(self.WEB)
        self.assertEqual(self._column(), "needs_input")
        km._withdraw_user_todo(self.WEB, self.tid)
        feed = self._feed()
        self.assertEqual(self._card(feed, "g1")["column"], "working")
        self.assertEqual(feed["userTodos"], {})
        self.assertNotIn(self.WEB, km._UT_FLOOR_ARM, "the request's own resolution spends the record")

    def test_a_turn_the_human_did_not_open_holds_the_floor(self):
        self._settle(self.WEB)
        self.assertEqual(self._column(), "needs_input")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, self.PEER, ended=False))
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 10))
        g1 = self._card(self._feed(), "g1")
        self.assertEqual(g1["column"], "needs_input", "a peer-opened turn is not the user acting")
        self.assertEqual(g1["blocked"]["state"], "userTodos")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, self.PEER))
        self.assertEqual(self._column(), "needs_input", "a lull inside the held turn is not news either")
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 10), ("waiting", NOW - 8))
        self.assertEqual(self._column(), "needs_input", "the peer turn settled: still Blocked, no move")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, self.PEER),
                    self._turn("t3", NOW - 6, "romp", ended=False))
        self.assertEqual(self._column(), "needs_input", "a romp reminder holds it")

    def test_a_turn_the_human_opened_stands_it_down_and_the_next_settle_re_arms(self):
        self._settle(self.WEB)
        self.assertEqual(self._column(), "needs_input")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, "human", ended=False))
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 10))
        self.assertEqual(self._column(), "working", "the user spoke to the session: their move")
        self.assertNotIn(self.WEB, km._UT_FLOOR_ARM, "spent, not suppressed")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, "human"))
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 10), ("waiting", NOW + 21))
        self.assertEqual(self._column(), "needs_input", "the exchange settled with the request still open")

    def test_a_card_reply_is_the_human_acting_too(self):
        self._settle(self.WEB)
        self.assertEqual(self._column(), "needs_input")
        self._turns(self._turn("t1", NOW - 60, "human"),
                    self._turn("t2", NOW - 10, "human", ended=False, text="the cookie, for now <!-- romp-goal-id: g1 -->"))
        self.assertEqual(self._column(), "working")

    def test_a_human_turn_in_the_history_spends_the_record_under_a_later_peer_turn(self):
        self._settle(self.WEB)
        self.assertEqual(self._column(), "needs_input")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 20, "human"),
                    self._turn("t3", NOW - 5, self.PEER, ended=False))
        self.assertEqual(self._column(), "working")
        self._turns(self._turn("t1", NOW - 60, "human"),
                    self._turn("t2", NOW - 20, "human", text="the cookie, for now <!-- romp-goal-id: g1 -->"),
                    self._turn("t3", NOW - 5, self.PEER, ended=False))
        self.assertEqual(self._column(), "working", "a card reply in the history likewise")

    def test_a_message_absorbed_into_a_turn_the_human_did_not_open_stands_it_down(self):
        self._settle(self.WEB)
        self.assertEqual(self._column(), "needs_input")
        t2 = self._turn("t2", NOW - 10, self.PEER, ended=False)
        t2["atoms"].append({"uuid": "t2-h", "type": "user", "author": "human", "t": NOW - 5,
                            "message": {"role": "user", "content": "use the cookie for now"}})
        self._turns(self._turn("t1", NOW - 60, "human"), t2)
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 10))
        self.assertEqual(self._column(), "working")
        self.assertNotIn(self.WEB, km._UT_FLOOR_ARM)

    def test_a_harness_notification_absorbed_into_the_settled_turn_holds_the_floor(self):
        self._settle(self.WEB)
        self.assertEqual(self._column(), "needs_input")
        held = self._turn("t1", NOW - 60, "human")
        held.pop("end"); held.pop("ended")
        held["atoms"].append({"uuid": "t1-sys", "type": "user", "author": "system", "t": NOW - 10,
                              "message": {"role": "user", "content": "<task-notification>the build finished</task-notification>"}})
        self._turns(held)
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 10))
        self.assertEqual(self._column(), "needs_input", "a harness notification is not the user acting")
        self.assertEqual(km._UT_FLOOR_ARM.get(self.WEB), (frozenset({self.tid}), NOW - 30), "the record stands")

    def test_a_human_parked_message_spends_the_record_and_a_machine_one_holds_it(self):
        self._settle(self.WEB)
        self.assertEqual(self._column(), "needs_input")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, self.PEER, ended=False))
        km._pending_ops[self.WEB] = [("send", "a watch notice", None)]              # a machine op: three slots, no author
        self.assertEqual(self._column(), "needs_input", "a machine entry is not the user acting")
        km._pending_ops[self.WEB] = [("send", "the cookie", None, "q-1", True)]      # the user's own parked send (_op_user)
        self.assertEqual(self._column(), "working", "the user's message is on its way in")
        self.assertNotIn(self.WEB, km._UT_FLOOR_ARM, "spent")
        km._pending_ops.pop(self.WEB, None)
        self.assertEqual(self._column(), "working", "spent: the drain alone does not re-floor an open turn")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, self.PEER))
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 10), ("waiting", NOW + 21))
        self.assertEqual(self._column(), "needs_input", "the settle does")

    def test_a_queue_entry_the_user_sent_spends_the_record_and_one_the_backend_cannot_vouch_for_holds_it(self):
        # the second slot of the key's queued triple (_backend_queued_by_user): the `user` bit SdkBackend.send records
        # on the entry's meta, read through the backend the session resolves to
        self._settle(self.WEB)
        meta = {}
        self._queue_meta(meta)
        self.assertEqual(self._column(), "needs_input")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, self.PEER, ended=False))
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 10))
        meta[self.WEB] = [{"md": "a watch notice", "qid": "q-0", "qts": 1}]         # a machine entry: no author bit
        self.assertEqual(self._column(), "needs_input", "a machine entry is not the user acting")
        meta[self.WEB] = None                                                        # identities the backend cannot vouch for
        self.assertEqual(self._column(), "needs_input", "an unknown author holds the floor")
        meta[self.WEB] = RuntimeError("the queue read failed")
        self.assertEqual(self._column(), "needs_input", "a backend hiccup reads no human intent")
        self._qmeta = self._NO_META                                                  # a backend without the read (Codex)
        self.assertEqual(self._column(), "needs_input", "a backend that cannot say who queued holds it too")
        self.assertEqual(km._UT_FLOOR_ARM.get(self.WEB), (frozenset({self.tid}), NOW - 30), "the record stands through all four")
        self._qmeta = meta
        meta[self.WEB] = [{"md": "a watch notice", "qid": "q-0", "qts": 1},
                          {"md": "use the cookie", "qid": "q-1", "qts": 2, "user": True}]   # the user's own send, queued behind it
        self.assertEqual(self._column(), "working", "the user's message is on its way in")
        self.assertNotIn(self.WEB, km._UT_FLOOR_ARM, "spent")
        meta[self.WEB] = []                                                          # the queue drained into the turn
        self.assertEqual(self._column(), "working", "spent: the drain alone does not re-floor an open turn")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, self.PEER))
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 10), ("waiting", NOW + 21))
        self.assertEqual(self._column(), "needs_input", "the settle does")

    def test_a_same_count_swap_under_a_peer_turn_stands_it_down_and_the_settle_re_arms_on_the_new_id(self):
        # the record is the blocking IDS, never their count: one withdrawn and another filed in the same step is news
        self._settle(self.WEB)
        self.assertEqual(self._column(), "needs_input")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, self.PEER, ended=False))
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 10))
        self.assertEqual(self._column(), "needs_input", "held through the peer's turn")
        km._withdraw_user_todo(self.WEB, self.tid)
        new = km._add_user_todo(self.WEB, "Need the staging port", blocking=True)
        feed = self._feed()
        g1 = self._card(feed, "g1")
        self.assertEqual(g1["column"], "working", "the blocking set changed with its count unchanged: news")
        self.assertIsNone(g1.get("blocked"))
        self.assertEqual(feed["userTodos"], {self.WEB: 1})
        self.assertNotIn(self.WEB, km._UT_FLOOR_ARM, "spent")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, self.PEER))
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 10), ("waiting", NOW + 21))
        g1 = self._card(self._feed(), "g1")
        self.assertEqual((g1["column"], g1["blocked"]["count"]), ("needs_input", 1), "the same count, floored on the new id")
        self.assertEqual(km._UT_FLOOR_ARM.get(self.WEB), (frozenset({new}), NOW + 20), "armed on the new id at the settle")

    def test_a_set_change_under_a_peer_turn_stands_it_down_and_the_settle_returns_the_new_count(self):
        self._settle(self.WEB)
        self.assertEqual(self._column(), "needs_input")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, self.PEER, ended=False))
        km._add_user_todo(self.WEB, "Need the staging port", blocking=True)
        feed = self._feed()
        self.assertEqual(self._card(feed, "g1")["column"], "working", "the blocking set changed: news")
        self.assertEqual(feed["userTodos"], {self.WEB: 2})
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, self.PEER))
        self._states(self.WEB, ("working", NOW - 55), ("waiting", NOW - 25), ("working", NOW - 10), ("waiting", NOW + 21))
        g1 = self._card(self._feed(), "g1")
        self.assertEqual((g1["column"], g1["blocked"]["count"]), ("needs_input", 2))

    def test_a_non_blocking_add_under_a_peer_turn_moves_no_record(self):
        self._settle(self.WEB)
        self.assertEqual(self._column(), "needs_input")
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 10, self.PEER, ended=False))
        km._add_user_todo(self.WEB, "Need your opinion on the route names")
        g1 = self._card(self._feed(), "g1")
        self.assertEqual((g1["column"], g1["blocked"]["count"], g1["blocked"]["open"]), ("needs_input", 1, 2),
                         "the record holds the blocking set; a non-blocking add is not a stop")

    def test_a_peer_wait_spends_the_record(self):
        self._settle(self.WEB)
        self.assertEqual(self._column(), "needs_input")
        self.wmap = {self.WEB: {"peerSid": self.API, "name": "api", "color": None, "inCycle": False, "since": NOW - 5, "kind": "question"}}
        self.assertEqual(self._column(), "working")
        self.assertNotIn(self.WEB, km._UT_FLOOR_ARM)
        self.wmap = {}
        self._turns(self._turn("t1", NOW - 60, "human"), self._turn("t2", NOW - 3, self.PEER, ended=False))
        self.assertEqual(self._column(), "working", "no record to hold: the reply's turn is a plain turn")


class MemoRehome(_FloorWorld):
    """Every input the floor reads is a key component, so a floored card never serves stale (the memo's counters
    through _feed_memo_report, as the seam tests read them): an unchanged rebuild after a floored build derives nothing
    (the arm's own write is re-keyed by the deps re-evaluation), the answer stamp moves the session under usertodos, a
    human-authored parked message under queued and a machine one not at all, the compaction bracket under compacting,
    and a peer session's request write moves nothing of this session."""

    def setUp(self):
        super().setUp()
        self.tid = km._add_user_todo(self.WEB, "Need the auth-scheme decision to wire login", blocking=True)
        self._one_goal(self.WEB)
        self._one_goal(self.API, "add the notes-api list endpoint")
        self._settle(self.WEB)

    def test_the_arms_own_write_costs_exactly_the_derivation_that_made_it(self):
        d, feed = self._delta(self._feed)
        self.assertEqual(d["derived"], 2, "cold: both sessions")
        self.assertEqual(self._card(feed, "g1")["column"], "needs_input")
        self.assertIn(self.WEB, km._UT_FLOOR_ARM, "the derivation armed the record")
        d, feed = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"], d["miss_by"]), (0, 2, {}),
                         "the stored key carries the record the derivation left: an unchanged rebuild hits (%r)" % d)
        self.assertEqual(self._card(feed, "g1")["column"], "needs_input")

    def test_the_answer_stamp_moves_the_session_under_usertodos_and_the_card_leaves_blocked(self):
        self._feed()
        self.assertTrue(km._resolve_user_todo(self.WEB, self.tid, "answered"))
        d, feed = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"], d["miss_by"]), (1, 1, {"usertodos": 1}), d)
        self.assertEqual(self._card(feed, "g1")["column"], "working")
        self.assertNotIn(self.WEB, km._UT_FLOOR_ARM)
        d, _ = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"]), (0, 2), "and stands")

    def test_a_human_parked_message_moves_the_session_under_queued_and_a_machine_one_moves_nothing(self):
        self._feed()
        km._pending_ops[self.WEB] = [("send", "a watch notice", None)]
        d, feed = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"], d["miss_by"]), (0, 2, {}), "a machine entry moves no key: %r" % d)
        self.assertEqual(self._card(feed, "g1")["column"], "needs_input")
        km._pending_ops[self.WEB] = [("send", "a watch notice", None), ("send", "the cookie", None, "q-1", True)]
        d, feed = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"], d["miss_by"]), (1, 1, {"queued": 1}), d)
        self.assertEqual(self._card(feed, "g1")["column"], "working")
        d, _ = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"], d["miss_by"]), (0, 2, {}), "the spent record is re-keyed by the same derivation: %r" % d)

    def test_a_queue_entry_the_user_sent_moves_the_session_under_queued_and_a_machine_one_moves_nothing(self):
        meta = {}
        self._queue_meta(meta)
        self._feed()
        meta[self.WEB] = [{"md": "a watch notice", "qid": "q-0", "qts": 1}]
        d, feed = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"], d["miss_by"]), (0, 2, {}), "a machine entry moves no key: %r" % d)
        self.assertEqual(self._card(feed, "g1")["column"], "needs_input")
        meta[self.WEB] = meta[self.WEB] + [{"md": "use the cookie", "qid": "q-1", "qts": 2, "user": True}]
        d, feed = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"], d["miss_by"]), (1, 1, {"queued": 1}), d)
        self.assertEqual(self._card(feed, "g1")["column"], "working")
        self.assertNotIn(self.WEB, km._UT_FLOOR_ARM)
        d, _ = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"], d["miss_by"]), (0, 2, {}), "the spent record is re-keyed by the same derivation: %r" % d)

    def test_a_same_count_swap_moves_the_session_under_usertodos_and_re_arms_the_record_on_the_new_id(self):
        # the component is the sorted open IDS, never their count
        self._feed()
        self.assertEqual(km._UT_FLOOR_ARM.get(self.WEB), (frozenset({self.tid}), NOW - 30))
        km._withdraw_user_todo(self.WEB, self.tid)
        new = km._add_user_todo(self.WEB, "Need the staging port", blocking=True)
        d, feed = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"], d["miss_by"]), (1, 1, {"usertodos": 1}), d)
        g1 = self._card(feed, "g1")
        self.assertEqual((g1["column"], g1["blocked"]["count"]), ("needs_input", 1),
                         "settled idle under the new set: the old record spent and the new one armed in the same derivation")
        self.assertEqual(km._UT_FLOOR_ARM.get(self.WEB), (frozenset({new}), NOW - 30))
        d, _ = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"], d["miss_by"]), (0, 2, {}), "and stands")

    def test_the_compaction_brackets_flip_moves_the_session_under_compacting(self):
        self._feed()
        flag = {self.WEB: True}
        with mock.patch.object(km, "_compacting_now", lambda sid, tm=None, path=None: bool(flag.get(str(sid)))):
            d, feed = self._delta(self._feed)
            self.assertEqual((d["derived"], d["hit"], d["miss_by"]), (1, 1, {"compacting": 1}), d)
            self.assertEqual(self._card(feed, "g1")["column"], "working", "a live story outranks the floor")
            self.assertIn(self.WEB, km._UT_FLOOR_ARM, "and leaves the record: none of it is the user acting")
            flag.clear()
            d, feed = self._delta(self._feed)
            self.assertEqual((d["derived"], d["miss_by"]), (1, {"compacting": 1}), d)
            self.assertEqual(self._card(feed, "g1")["column"], "needs_input", "the floor returns with the record")

    def test_a_peer_sessions_request_write_moves_nothing_of_this_session(self):
        self._feed()
        km._add_user_todo(self.API, "Need a test credential for the api session", blocking=True)
        d, feed = self._delta(self._feed)
        self.assertEqual((d["derived"], d["hit"], d["miss_by"]), (1, 1, {"usertodos": 1}), d)
        self.assertEqual(self._card(feed, "g1")["column"], "needs_input", "web's card is served, unchanged")
        self.assertEqual(feed["userTodos"], {self.WEB: 1, self.API: 1})


class OneInterruptStory(_FloorWorld):
    """A session shows ONE interrupt presentation at a time: the judge-auth floor stands alone, a floored card gets no
    working placeholder beside it, a completed focus falls back to the working top, the fallback yields to the live
    floors and skips a done-confirming top, and a goal-less idle session gets the placeholder once. The predicate is
    force-armed here: these shapes exercise the guards, not the arming (EscalationFloorPredicate)."""

    def setUp(self):
        super().setUp()
        km._add_user_todo(self.WEB, "Need the auth-scheme decision to wire login", blocking=True)
        self._set_turns(self.WEB, [{"id": "t1", "t": NOW - 60, "end": NOW - 30, "ended": True, "atoms": []}])
        p = mock.patch.object(km, "_user_todo_idle", lambda *a, **k: True)
        p.start()
        self.addCleanup(p.stop)

    def _needs_input(self, feed):
        return [a for a in self._mine(feed, self.WEB) if a.get("column") == "needs_input"]

    def test_the_jauth_floor_stands_alone(self):
        self._one_goal(self.WEB)
        self.jauth = {self.WEB: {"mode": "key", "t": NOW - 100}}
        ni = self._needs_input(self._feed())
        self.assertEqual([(a["itemId"], a["blocked"]["state"]) for a in ni], [("g1", "judgeAuth")])

    def test_the_floored_card_wears_count_and_story_and_no_working_placeholder_beside_it(self):
        km._add_user_todo(self.WEB, "Need a staging credential for the tests", blocking=True)
        self._one_goal(self.WEB)
        dummy = {"itemId": "provisional:" + self.WEB, "sid": self.WEB, "name": "web", "color": None,
                 "text": "Analyzing: wire the login flow", "t": NOW, "live": True, "_ageT": None,
                 "turnId": None, "origin": None, "followupPending": None, "summary": None, "blockSummary": None,
                 "background": None, "blocked": None, "column": "working", "board": "feed", "category": "working",
                 "provisional": True, "tree": []}
        with mock.patch.object(km, "_provisional_card", lambda *a, **k: dict(dummy)):
            feed = self._feed()
        self.assertEqual([a["itemId"] for a in self._mine(feed, self.WEB)], ["g1"])
        self.assertEqual(self._card(feed, "g1")["blocked"], {"state": "userTodos", "count": 2, "open": 2, "what": km._USER_TODO_BLOCK_WHAT})

    def test_a_completed_focus_falls_back_to_the_working_top(self):
        self._store(self.WEB, {"g1": {"text": "ship the fixtures", "t": NOW - 900}, "g2": {"text": "wire the login flow"}},
                    {"g1": "completed", "g2": "working"}, "g1")
        feed = self._feed()
        ni = self._needs_input(feed)
        self.assertEqual([a["itemId"] for a in ni], ["g2"], "the still-working top takes the floor when the focus walk dead-ends")
        self.assertEqual(ni[0]["blocked"]["state"], "userTodos")
        self.assertNotIn("usertodo:" + self.WEB, [a["itemId"] for a in feed["asks"]])

    def test_the_fallback_still_yields_to_jauth(self):
        self._store(self.WEB, {"g1": {"text": "ship the fixtures", "t": NOW - 900}, "g2": {"text": "wire the login flow"}},
                    {"g1": "working", "g2": "working"}, "g1")
        self.jauth = {self.WEB: {"mode": "key", "t": NOW - 100}}
        ni = self._needs_input(self._feed())
        self.assertEqual(len(ni), 1)
        self.assertEqual(ni[0]["blocked"]["state"], "judgeAuth")

    def test_a_done_confirming_focus_is_never_floored_and_the_fallback_skips_a_confirming_top(self):
        self._store(self.WEB, {"g1": {"text": "ship the fixtures", "t": NOW - 900}, "g2": {"text": "wire the login flow"}},
                    {"g1": "working", "g2": "working"}, "g1", confirming=["g1"])
        feed = self._feed()
        self.assertEqual([a["itemId"] for a in self._needs_input(feed)], ["g2"], "the confirming focus belongs to the settle gate")
        self.assertTrue(self._card(feed, "g1").get("doneConfirming"))
        self._store(self.WEB, {"g1": {"text": "ship the fixtures", "t": NOW - 900}, "g2": {"text": "wire the login flow"}},
                    {"g1": "completed", "g2": "working"}, "g1", confirming=["g2"])
        feed = self._feed()
        self.assertEqual(self._needs_input(feed), [], "no floor while the only candidate is done-confirming")
        self.assertEqual(self._card(feed, "g2")["column"], "working")

    def test_a_goal_less_idle_session_gets_the_placeholder_once(self):
        self._store(self.WEB, {}, {}, None)
        feed = self._feed()
        mine = self._mine(feed, self.WEB)
        self.assertEqual([a["itemId"] for a in mine], ["usertodo:" + self.WEB])
        self.assertTrue(mine[0]["provisional"])
        self.assertEqual(mine[0]["blocked"]["state"], "userTodos")

    def test_the_floor_takes_a_plain_working_focus_only(self):
        # the awaiting flavor rides Working and a judge's block is its own latch: neither wears the request story while
        # the predicate reads idle (the `col == "working"` guard on _todo_block), and a focus card exists, so nothing floors
        self._store(self.WEB, {"g1": {"text": "run the fixture pass", "awaitingWhy": "the pass it dispatched; reports when done",
                                      "awaitingAt": NOW - 400}}, {"g1": "working"}, "g1")
        feed = self._feed()
        g1 = self._card(feed, "g1")
        self.assertEqual(self._needs_input(feed), [])
        self.assertEqual((g1["column"], g1.get("blocked"), g1["distillState"]), ("working", None, None))
        self.assertEqual((g1["awaiting"] or {}).get("why"), "the pass it dispatched; reports when done", "the awaiting flavor stands")
        self._store(self.WEB, {"g1": {"text": "wire the login flow", "blocked": True}}, {"g1": "blocked"}, "g1")
        feed = self._feed()
        g1 = self._card(feed, "g1")
        self.assertEqual((g1["column"], g1["distillState"]), ("needs_input", "blocked"), "the judges' block files the card")
        self.assertIsNone(g1.get("blocked"), "with its own story: no request chip over a judge's block")
        self.assertEqual([a["itemId"] for a in self._mine(feed, self.WEB)], ["g1"], "and no placeholder beside it")

    def test_a_working_session_floors_nothing(self):
        self._one_goal(self.WEB)
        with mock.patch.object(km, "_user_todo_idle", lambda *a, **k: False):
            feed = self._feed()
        self.assertEqual(self._needs_input(feed), [])
        g1 = self._card(feed, "g1")
        self.assertEqual(g1["column"], "working")
        self.assertIsNone(g1.get("blocked"))
        self.assertEqual(feed["userTodos"], {self.WEB: 1}, "the marker's data still rides")


class PeerWaitScopeIsLocalOnly(_StoreSandbox):
    """The peer-wait stand-down is local-host only, a documented limitation: _wait_for_graph keeps an edge only when
    the awaited peer is in THIS kernel's alive set, so an unanswered ask to a federated peer makes no edge and the
    floor still fires over an idle a remote peer explains. The chip and the nudge's skip read the same graph, so
    widening it there lifts every surface at once. If these fail because the graph learned federated edges, move the
    floor's expectation with the chip's."""

    def setUp(self):
        super().setUp()
        self.mfile = Path(self.td.name) / "timeline" / "messages.jsonl"
        self._saved_messages = jd.MESSAGES
        jd.MESSAGES = self.mfile
        self._saved_cache = list(km._POSTAL_WAIT_CACHE)
        km._POSTAL_WAIT_CACHE[:] = [None, None]

    def tearDown(self):
        jd.MESSAGES = self._saved_messages
        km._POSTAL_WAIT_CACHE[:] = self._saved_cache
        super().tearDown()

    def _rows(self, rows):
        self.mfile.parent.mkdir(parents=True, exist_ok=True)
        self.mfile.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        km._POSTAL_WAIT_CACHE[:] = [None, None]

    def test_a_local_alive_peer_makes_the_edge(self):
        self._rows([{"from_id": SID, "to_id": SID2, "t": NOW - 300, "kind": "question", "body": "Which port does staging use?"}])
        wmap = km._wait_for_graph(NOW, {SID, SID2})
        self.assertEqual(wmap[SID]["peerSid"], SID2)

    def test_a_relay_addressed_ask_makes_no_edge_so_the_floor_still_fires(self):
        self._rows([{"from_id": SID, "to_id": "peer:TESTHOST", "toName": "TESTHOST:api", "t": NOW - 300,
                     "kind": "question", "body": "Which port does staging use?"}])
        self.assertNotIn(SID, km._wait_for_graph(NOW, {SID}), "no edge to a federated peer: the graph is local-host scope")

    def test_even_a_resolved_remote_sid_makes_no_edge(self):
        self._rows([
            {"from_id": SID2, "from": "api", "from_host": "TESTHOST", "to_id": SID, "t": NOW - 900, "kind": "coordinate",
             "body": "Staging is rebuilt nightly."},
            {"from_id": SID, "to_id": "peer:TESTHOST", "toName": "TESTHOST:api", "t": NOW - 300, "kind": "question",
             "body": "Which port does staging use?"},
        ])
        self.assertNotIn(SID, km._wait_for_graph(NOW, {SID}), "a resolvable but non-local peer still makes no edge")


class FloorNotificationDedup(_StoreSandbox):
    """The push for a request-floored card is latched on the FLOORED BLOCKING SET (the REAL _feed_notifications under a
    private state root): the card's designed dips and re-entries are not news, a blocking id joining is, the first
    build of a kernel life seeds the latch from the floored world, a corroborated answer loss un-latches its id, the
    user's own recall does not, and the two writers share one lock."""

    def setUp(self):
        super().setUp()
        km._NOTIFY_PREV[0] = None
        km._NOTIFY_UT_FIRED[0].clear()
        km._notify_cards_cache.clear()
        km._flags_cache.clear()
        patches = [
            mock.patch.object(km, "_notify_card_effective", lambda cards, iid, sid: True),
            mock.patch.object(km, "_prune_notify_cards", lambda live: None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        km._NOTIFY_PREV[0] = None
        km._NOTIFY_UT_FIRED[0].clear()
        super().tearDown()

    @staticmethod
    def _card(floored, state="userTodos", sid=SID):
        blocked = {"state": state, "count": 1, "what": "stopped"} if floored else None
        col = "needs_input" if floored else "working"
        return {"asks": [{"itemId": sid + ":g1", "sid": sid, "name": "web", "text": "wire the login flow",
                          "column": col, "board": "feed", "category": col, "blocked": blocked}]}

    def test_a_dip_and_re_entry_with_the_same_set_is_not_news(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        km._feed_notifications(self._card(False))                        # the baseline build
        fired = len(km._feed_notifications(self._card(True)))
        self.assertEqual(fired, 1, "the first floor: the one push")
        for _cycle in range(3):
            self.assertEqual(km._feed_notifications(self._card(False)), [])
            fired += len(km._feed_notifications(self._card(True)))
        self.assertEqual(fired, 1, "re-entry with an identical blocking set is not news")

    def test_a_new_blocking_request_re_arms_the_push_and_a_non_blocking_one_does_not(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        km._feed_notifications(self._card(False))
        self.assertEqual(len(km._feed_notifications(self._card(True))), 1)
        km._feed_notifications(self._card(False))
        km._add_user_todo(SID, "Need your opinion on the route names")
        self.assertEqual(km._feed_notifications(self._card(True)), [], "a non-blocking request joins no floored set")
        km._feed_notifications(self._card(False))
        km._add_user_todo(SID, "Need a staging credential for the tests", blocking=True)
        self.assertEqual(len(km._feed_notifications(self._card(True))), 1, "a blocking id joining the floored set IS news")

    def test_the_dedup_is_scoped_to_the_floor(self):
        km._feed_notifications(self._card(False))
        self.assertEqual(len(km._feed_notifications(self._card(True, state="permission"))), 1)
        km._feed_notifications(self._card(False))
        self.assertEqual(km._feed_notifications(self._card(True, state="permission")), [],
                         "a permission card keeps the announced rule: told already, silent")
        self.assertEqual(km._NOTIFY_UT_FIRED[0], {}, "the latch never saw the permission card")

    def test_a_restart_baseline_seeds_the_latch_from_the_floored_world(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        km._feed_notifications(self._card(False))
        self.assertEqual(len(km._feed_notifications(self._card(True))), 1)
        km._NOTIFY_PREV[0] = None                                        # a kernel restart: both in-memory latches re-baseline
        km._NOTIFY_UT_FIRED[0].clear()
        self.assertEqual(km._feed_notifications(self._card(True)), [], "the first build is status, not news")
        self.assertEqual(km._feed_notifications(self._card(False)), [])
        self.assertEqual(km._feed_notifications(self._card(True)), [], "the routine dip and re-entry after a restart is not news")

    def test_the_seed_suppresses_only_what_was_floored(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        self.assertEqual(km._feed_notifications(self._card(True)), [], "floored at boot: silent, and the latch seeded")
        km._add_user_todo(SID, "Need a staging credential for the tests", blocking=True)
        self.assertEqual(km._feed_notifications(self._card(False)), [])
        self.assertEqual(len(km._feed_notifications(self._card(True))), 1, "the id that joined after the seed is news")

    def test_an_id_joining_while_floored_pushes_with_no_observed_dip(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        km._feed_notifications(self._card(False))
        self.assertEqual(len(km._feed_notifications(self._card(True))), 1)
        km._add_user_todo(SID, "Need a staging credential for the tests", blocking=True)
        self.assertEqual(len(km._feed_notifications(self._card(True))), 1, "news with no column transition")
        self.assertEqual(km._feed_notifications(self._card(True)), [], "and exactly once")

    def test_a_same_count_swap_while_floored_is_news_once(self):
        # the latch is the floored SET, never its size: one blocking request answered and another filed reads as the new id
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        km._feed_notifications(self._card(False))
        self.assertEqual(len(km._feed_notifications(self._card(True))), 1)
        self.assertTrue(km._resolve_user_todo(SID, tid, "answered"))
        km._add_user_todo(SID, "Need the staging port", blocking=True)
        self.assertEqual(len(km._feed_notifications(self._card(True))), 1, "one id for one: the set changed, the count did not")
        self.assertEqual(km._feed_notifications(self._card(True)), [], "and exactly once")

    def test_a_lost_answers_reopen_re_arms_the_push(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        km._feed_notifications(self._card(False))
        self.assertEqual(len(km._feed_notifications(self._card(True))), 1)
        self.assertTrue(km._resolve_user_todo(SID, tid, "answered"))
        self.assertEqual(km._feed_notifications(self._card(False)), [])
        with mock.patch.object(km, "_sessions", lambda now, window=None, forks=True: [{"sid": SID, "path": "/dev/null"}]), \
             mock.patch.object(km, "_parse", lambda path, sid, now: {"turns": []}), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_answer_lost(SID, tid, "Re: the decision. Cookie.", wait=True), "reopened")
        self.assertEqual(len(km._feed_notifications(self._card(True))), 1, "the re-floor after a lost answer pushes")

    def test_the_users_own_recall_stays_silent(self):
        be = _FakeBackend()
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        km._feed_notifications(self._card(False))
        self.assertEqual(len(km._feed_notifications(self._card(True))), 1)
        body = km._user_todo_answer_body("Need the auth-scheme decision to wire login", "Go with the session cookie.")
        with mock.patch.object(km, "_compacting_now", lambda sid, **k: False), \
             mock.patch.object(km, "_working_now", lambda sid: False), \
             mock.patch.object(km, "_limit_hold", lambda sid: False), \
             mock.patch.dict(km._pending_ops, {}, clear=True):
            self.assertIs(km._send_or_park(be, SID, body, user=True, user_todo=tid), False, "handed over now")
            km._stamp_user_todo_answered(SID, tid)
            self.assertEqual(km._feed_notifications(self._card(False)), [])
            self.assertIsNone(km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1]))
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the recall reopened the request")
        self.assertEqual(km._feed_notifications(self._card(True)), [], "the user pulled the answer back themselves: no push")

    def test_the_unlatch_touches_one_id_of_one_session(self):
        km._NOTIFY_UT_FIRED[0][SID] = frozenset({"ut-aaaaaaaa", "ut-bbbbbbbb"})
        km._NOTIFY_UT_FIRED[0][SID2] = frozenset({"ut-cccccccc"})
        km._notify_ut_unlatch(SID, "ut-aaaaaaaa")
        self.assertEqual(km._NOTIFY_UT_FIRED[0][SID], frozenset({"ut-bbbbbbbb"}))
        self.assertEqual(km._NOTIFY_UT_FIRED[0][SID2], frozenset({"ut-cccccccc"}))
        km._notify_ut_unlatch(SID, "ut-not-there")
        km._notify_ut_unlatch("33333333-4444-5555-6666-777777777777", "ut-aaaaaaaa")
        self.assertEqual(set(km._NOTIFY_UT_FIRED[0]), {SID, SID2}, "no entry minted for a stranger")

    def test_the_two_writers_share_one_lock(self):
        for fn in (km._feed_notifications_diff, km._notify_ut_unlatch):
            self.assertIn("with _NOTIFY_UT_LOCK", inspect.getsource(fn), fn.__name__)

    def test_a_goal_less_floored_sessions_placeholder_stays_silent(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        km._feed_notifications(self._card(False))
        ph = {"asks": [{"itemId": "usertodo:" + SID, "sid": SID, "name": "web", "text": "Need the auth-scheme decision",
                        "column": "needs_input", "board": "feed", "category": "needs_input", "provisional": True,
                        "blocked": {"state": "userTodos", "count": 1, "open": 1, "what": "stopped"}}]}
        self.assertEqual(km._feed_notifications(ph), [], "provisional, like the permission twin: the diff skips it")


class BadgeArithmetic(unittest.TestCase):
    """_needs_you_count keeps the per-card, board-aware rule and adds one thing: a request-floored presentation counts its
    BLOCKING requests instead of itself, provisional or not. Feed dicts in the card shape the constructors set."""

    @staticmethod
    def _floored(sid, count, iid="g1", provisional=False):
        c = {"itemId": sid + ":" + iid, "sid": sid, "column": "needs_input", "board": "feed", "category": "needs_input",
             "blocked": {"state": "userTodos", "count": count, "open": count, "what": "stopped"}}
        if provisional:
            c["provisional"] = True
        return c

    @staticmethod
    def _hard(sid, iid, state="permission"):
        return {"itemId": sid + ":" + iid, "sid": sid, "column": "needs_input", "board": "feed", "category": "needs_input",
                "blocked": {"state": state, "what": "stopped"}}

    def test_a_floored_card_badges_its_blocking_count_not_one(self):
        self.assertEqual(km._needs_you_count({"asks": [self._floored("S1", 3)]}), 3)

    def test_a_floored_placeholder_badges_its_count_though_provisional(self):
        self.assertEqual(km._needs_you_count({"asks": [self._floored("S1", 2, iid="ph", provisional=True)]}), 2)

    def test_hard_stops_count_per_card(self):
        self.assertEqual(km._needs_you_count({"asks": [self._hard("S1", "a"), self._hard("S1", "b")]}), 2)

    def test_a_session_hard_stopped_on_a_prompt_while_it_holds_requests_badges_once(self):
        # the perm floor won the card: no floored presentation exists, and the requests ride the marker alone
        self.assertEqual(km._needs_you_count({"asks": [self._hard("S1", "a")], "userTodos": {"S1": 2}}), 1)

    def test_a_notice_card_that_needs_you_counts_once(self):
        c = {"itemId": "notice:S1:k:1", "sid": "S1", "column": "needs_input", "board": "feed", "category": "needs_input",
             "blocked": None, "notice": {"producer": "x", "key": "k", "rev": 1, "body": ""}}
        self.assertEqual(km._needs_you_count({"asks": [c]}), 1)

    def test_a_provisional_non_floored_card_stays_out(self):
        c = dict(self._hard("S1", "a"), provisional=True)
        self.assertEqual(km._needs_you_count({"asks": [c, {"itemId": "b", "sid": "S2", "column": "working", "board": "feed", "category": "working"}]}), 0)

    def test_a_sid_less_card_counts(self):
        self.assertEqual(km._needs_you_count({"asks": [{"itemId": "q1", "column": "needs_input"}, {"itemId": "q2", "column": "needs_input"}]}), 2)

    def test_a_floored_card_with_a_malformed_blocked_field_contributes_nothing_and_raises_nothing(self):
        c = self._floored("S1", 2)
        c["blocked"] = {"state": "userTodos", "count": "many"}
        self.assertEqual(km._needs_you_count({"asks": [c]}), 0)
        c["blocked"] = {"state": "userTodos"}
        self.assertEqual(km._needs_you_count({"asks": [c]}), 0)
        c["blocked"] = {"state": "userTodos", "count": None}
        self.assertEqual(km._needs_you_count({"asks": [c, self._hard("S2", "a")]}), 1)

    def test_a_board_that_never_badges_keeps_its_floored_card_out(self):
        c = dict(self._floored("S1", 2), board="no-such-board", category="needs_input")
        self.assertEqual(km._needs_you_count({"asks": [c]}), 2, "an unknown board reads as the feed's")
        with mock.patch.object(km, "_board_needs_you", lambda board: None):
            self.assertEqual(km._needs_you_count({"asks": [c]}), 0)

    def test_an_empty_feed_is_zero(self):
        self.assertEqual(km._needs_you_count({"asks": []}), 0)
        self.assertEqual(km._needs_you_count({}), 0)


class NudgeStandsDownForBlockingRequests(_StoreSandbox):
    """The status nudge stands down while a BLOCKING request is open (the request already says what a status check
    would fish for); a non-blocking request does not stand it down; the gate lifts when the last blocking request
    clears; the awaiting WAKE and the DEBT reminder flow past it. Synthetic fixtures, the notes-api world."""

    S = {"sid": SID, "name": "web", "path": "/nonexistent/%s.jsonl" % SID, "anchor": 0, "mtime": 0}
    TURNS = [{"id": "t1", "t": NOW - 600, "end": NOW - 500, "ended": True, "trigger": None, "atoms": []}]

    def setUp(self):
        super().setUp()
        self.saved_goaldir = jd.GOALDIR
        self.addCleanup(setattr, jd, "GOALDIR", jd.GOALDIR)
        jd.GOALDIR = jd.STATE / "goals"
        jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        km._autonudge_cache.clear()
        km._SESSION_STAMP_CACHE.clear()
        km._flags_cache.clear()
        self.sent = []
        rec = self

        class _Backend:
            def send(self, sid, body, **kw):
                rec.sent.append((sid, body))
                return True

        self.saved_backend = km.Sessions.backend_for
        self.addCleanup(setattr, km.Sessions, "backend_for", staticmethod(self.saved_backend))
        km.Sessions.backend_for = staticmethod(lambda sid: _Backend())
        patches = [
            mock.patch.object(km, "_api_error", lambda path: None),
            mock.patch.object(jd, "parsed_session", lambda sid, paths, now: {"turns": list(self.TURNS)}),
            mock.patch.object(km, "_session_working", lambda turns: False),
            mock.patch.object(km, "_interrupt_suppresses_nudge", lambda turns, s="", **k: False),
            mock.patch.object(km, "_backend_queued", lambda s: False),
            mock.patch.object(km, "_backend_rewind_pending", lambda s: False),
            mock.patch.object(km, "_compacting_now", lambda s, **k: False),
            mock.patch.object(km, "_last_state", lambda s: ("waiting", 0)),
            mock.patch.object(km, "_session_awaiting", lambda sid, path, idle, stamp=False: None),
            mock.patch.object(km, "_closer_settled", lambda *a, **k: True),
            mock.patch.object(jd, "plan_units", lambda ps, store: []),
            mock.patch.object(km, "_revivers_pending", lambda *a, **k: ""),
            mock.patch.object(km, "_peer_answered_at", lambda sid: 0),
            mock.patch.object(km, "_log_nudge_event", lambda *a, **k: None),
            mock.patch.dict(km._pending_ops, {}, clear=True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        jd.GOALDIR = self.saved_goaldir
        km.Sessions.backend_for = self.saved_backend
        km._autonudge_cache.clear()
        km._SESSION_STAMP_CACHE.clear()
        super().tearDown()

    def _seed_goals(self, nodes, status=None):
        (jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 1, "placements": {}, "status": status or {}, "nodes": nodes}))

    def _plain_top(self):
        return {"g1": {"id": "g1", "text": "wire the login flow", "parentId": None, "t": NOW - 900, "mt": NOW - 900,
                       "nodeComplete": False, "blocked": False, "cleared": False, "trail": []}}

    def _stamped_top(self, at):
        return {"g1": {"id": "g1", "text": "run the fixture pass", "parentId": None, "t": NOW - 90000, "mt": NOW - 90000,
                       "nodeComplete": False, "blocked": False, "cleared": False, "trail": [],
                       "awaitingWhy": "the pass it dispatched; reports when done", "awaitingAt": at,
                       "log": [{"ev_t": at, "src": "closer", "kind": "awaiting",
                                "why": "the pass it dispatched; reports when done", "at": at + 5}]}}

    def _run(self, alive_ids=None):
        km._autonudge_cache.clear()
        km._SESSION_STAMP_CACHE.clear()
        return km._auto_nudge_session(self.S, NOW, {SID: {"state": ""}}, {}, {}, alive_ids=alive_ids)

    def test_the_status_nudge_stands_down_while_a_blocking_request_is_open(self):
        self._seed_goals(self._plain_top(), status={"g1": "working"})
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        self.assertFalse(self._run())
        self.assertEqual(self.sent, [], "the request already names what a status check would ask")
        self.assertEqual(km._auto_nudge_data().get("nudged", {}), {}, "no record armed either")

    def test_a_non_blocking_request_does_not_stand_it_down(self):
        self._seed_goals(self._plain_top(), status={"g1": "working"})
        km._add_user_todo(SID, "Need your opinion on the route names")
        self.assertTrue(self._run(), "a non-blocking request is information, not a stop: the status nudge proceeds")
        self.assertEqual(len(self.sent), 1)

    def test_the_gate_lifts_the_moment_the_last_blocking_request_clears(self):
        self._seed_goals(self._plain_top(), status={"g1": "working"})
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        km._resolve_user_todo(SID, tid, "dismissed")
        self.assertTrue(self._run())
        self.assertEqual(len(self.sent), 1)

    def test_the_awaiting_wake_flows_past_a_blocking_request(self):
        self._seed_goals(self._stamped_top(at=NOW - 7 * 3600), status={"g1": "working"})
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        self.assertTrue(self._run(), "the wake fired despite the open request")
        self.assertEqual(len(self.sent), 1)
        self.assertTrue(km._auto_nudge_data()["nudged"]["g1"].get("wake"), "the WAKE's record, not a status nudge's")

    def test_the_debt_reminder_flows_past_a_blocking_request(self):
        self._seed_goals({}, status={})
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)      # the asker's registry row, alive: the debt reader keys on it
        (jd.STATE / "sdk" / (SID2 + ".json")).write_text(json.dumps({"sid": SID2, "alive": True}))
        t_ask = NOW - 1800
        maps = ({(SID2, SID): t_ask}, {(SID2, SID): (t_ask, "question", "Which port should the staging server use?")}, {})
        patches = [
            mock.patch.object(km, "_postal_wait_maps", lambda: maps),
            mock.patch.object(km, "_name_of", lambda sid: {SID2: "api", SID: "web"}.get(sid)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.assertTrue(self._run(alive_ids={SID, SID2}), "the reminder fired despite the request")
        self.assertEqual(len(self.sent), 1)
        self.assertIn("api asked you", self.sent[0][1])

    def test_the_gate_sits_after_the_re_arm_block_and_before_the_last_resort_gate(self):
        src = inspect.getsource(km._auto_nudge_session)
        i_park = src.index("# PARK GATE")
        i_gate = src.index("if _req_standdown:")
        i_last = src.index("# LAST-RESORT GATE")
        i_fire = src.index("to_fire.append(")
        self.assertLess(i_park, i_gate)
        self.assertLess(i_gate, i_last)
        self.assertLess(i_last, i_fire)
        self.assertEqual(src.count("if _req_standdown:"), 1, "one gate, on the goal walk alone")


class PruneArmRecords(_StoreSandbox):
    """The housekeeping prune also spends the floor's arm record of a session whose death is corroborated (the same
    evidence the row prune reads), keeps a live session's, and returns before any death read when the store is empty."""

    def _mark_dead(self, sid, t=NOW):
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (sid + ".json")).write_text(json.dumps({"t": t, "by": "gone"}))

    def setUp(self):
        super().setUp()
        km._UT_FLOOR_ARM.clear()
        self.addCleanup(km._UT_FLOOR_ARM.clear)

    def test_the_prune_drops_a_dead_sids_record_and_keeps_a_live_ones(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        km._add_user_todo(SID2, "Need a test credential for the api session", blocking=True)
        km._UT_FLOOR_ARM[SID] = (frozenset({"ut-11111111"}), NOW - 30)
        km._UT_FLOOR_ARM[SID2] = (frozenset({"ut-22222222"}), NOW - 30)
        self._mark_dead(SID)
        km._prune_user_todos()
        self.assertEqual(set(km._UT_FLOOR_ARM), {SID2}, "the dead session's record leaves; the live one stands")
        self.assertEqual(len(km._open_user_todos(SID2)), 1, "open rows never leave")

    def test_an_empty_store_returns_before_any_death_read(self):
        seen = []
        km._UT_FLOOR_ARM[SID] = (frozenset({"ut-11111111"}), NOW - 30)   # a record with no rows behind it: stale
        with mock.patch.object(km, "_user_todo_session_ended", lambda sid: seen.append(sid) or True):
            km._prune_user_todos()
        self.assertEqual(seen, [], "no rows, no death read")
        self.assertEqual(km._UT_FLOOR_ARM, {}, "a record no row backs is dropped: the body disarms such a sid anyway")

    def test_the_prune_is_the_housekeeping_stage_and_no_build_calls_it(self):
        self.assertIn("_job_stage('pruneUserTodos', lambda: _prune_user_todos())", inspect.getsource(km._jobs_pass))
        for fn in (km._chat_tab_sessions, km._pusher_cycle_jobs, km.build_feed, km._feed_session_entry):
            self.assertNotIn("_prune_user_todos", inspect.getsource(fn), fn.__name__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
