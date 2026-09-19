#!/usr/bin/env python3
"""Requests from sessions (plans/user-todos.md): a need an agent files with the person it works for, a
decision, an input or an action only they can provide, held open while the agent keeps working. Exactly
three events clear one: the user answers, the user dismisses, or the agent withdraws. Nothing that reasons
by inference may write the store (the authority tier).

Covered here, kernel side:
- the store (user-todos.json under STATE): round-trip, stamps-not-deletes, sid-keying, id stability, the
  optional `blocking` flag, the loud unknown-id refusal, the mtime cache, the caps, the resolved-history
  bound, the shape guard;
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
  call of a store writer in kernel.py resolves to an allow-listed def.

Synthetic fixtures only: private placeholder uuids, the notes-api demo world.
"""
import ast
import contextlib
import inspect
import io
import json
import os
import re
import shutil
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


class _StoreSandbox(unittest.TestCase):
    """Per-test STATE sandbox with the caches reset and the switch ON (it is OFF by default; the OFF side
    lives in test_user_todos_switch.py)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
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

        def guarded(cur):
            # the lock is re-entrant and an RLock has no .locked(): _is_owned() is the claim, since every
            # mutation publishes on the thread that took the lock
            seen.append(km._user_todos_lock._is_owned())
            real_write(cur)

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

    def test_no_context_route_exists(self):
        # no route hands a session its open requests: the path is an unknown route, answered as the dispatcher
        # answers every unknown path
        code, out = _serve_post("/usertodo/context", {"id": SID}, {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 404)
        self.assertNotIn("/usertodo/context", inspect.getsource(km.Handler.do_POST))

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
                     km._USER_TODO_STAMP_FAILED_WARN, km._USER_TODO_DISMISS_SETTLED_WARN):
            low = text.lower()
            self.assertIn("request", low, text)
            for noun in ("store", "stamp", "queue", "todo", "nonce", "mark"):
                self.assertNotIn(noun, low, "%r names machinery: %s" % (text, noun))


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
        # the routes (the agent's tool call) and the drive handler (the person's click)
        "Handler.do_POST", "_drive",
        # the drain's handover report (the delivery verdict)
        "_parked_answer_handed_over",
        # the person's own recall of a queued answer
        "_cancel_backend_queued",
        # the boot pass over persisted loss marks, and the housekeeping pass the prune rides
        "_user_todo_loss_boot_pass", "_jobs_pass",
    }

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
                         "longer calls one: prune it): %s" % sorted(set(found) ^ self.ALLOWED))

    def test_the_kernels_own_card_movers_are_not_callers(self):
        _defs, found = self._callers()
        for mover in ("_mark_nudge_failed", "_nudge_fire_list", "_record_interrupt_block",
                      "_lift_interrupt_block", "build_feed", "build_session", "_auto_nudge_tick", "_chat_tab_sessions"):
            self.assertNotIn(mover, found)

    def test_the_derivation_sees_the_helpers_calling_each_other(self):
        _defs, found = self._callers()
        self.assertEqual(found["_add_user_todo"], {"_write_user_todos"})
        self.assertEqual(found["_stamp_user_todo_answered"], {"_resolve_user_todo"})
        self.assertEqual(found["_parked_answer_handed_over"], {"_stamp_user_todo_answered"})
        self.assertEqual(found["_cancel_backend_queued"], {"_reopen_user_todo"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
