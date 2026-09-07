#!/usr/bin/env python3
"""User todos (plans/user-todos.md; docs/adr/0001): a need an agent registers with the person it
works for — a decision, input, or action only they can provide — held open while the agent keeps
working. Exactly three events clear one: the user answers, the user dismisses, or the agent
withdraws. Nothing that reasons by inference may write the store (the authority tier).

Covered here, kernel-side:
- the store (user-todos.json under STATE): round-trip, stamps-not-deletes, sid-keying, id
  stability, the loud unknown-id refusal, the mtime-cache, the prune sweep;
- the store LOCK (_user_todos_lock, the _comments_lock doctrine): every read-modify-write holds
  it, concurrent registrations lose nothing, and a racing answer + withdraw cannot both succeed
  — first-stamp-wins is real, not single-threaded prose;
- the ended gate (_user_todo_session_ended) for BOTH backends: the SDK registry's alive:false, or
  a reg-less tmux sid's durable death record superseded by newer states evidence — corroborated
  evidence only, never a raw listing miss;
- the POST routes (/usertodo, /usertodo/withdraw) incl. route auth, driven over the fake-socket
  harness (the auth-hardening idiom: ask the real dispatcher, don't pin source positions), and
  the ack-fast contract: the reply never waits behind a synchronous every-session build;
- the per-sid chat-build-sig fold (a todo write busts the owning session's cache only);
- build_session's `userTodos` field + the split-card `todo` event that carries the rows (the
  chatTail wire re-sends changed EVENTS only, so the rows must ride the event), clock-invariant
  per the serialized-payload dedup rule, hidden for an ended session, and the pre-existing
  card's shape kept byte-for-byte when no todo is open — and _send_chat's chatTail frame
  carrying the field on every delta (BuildSessionSeam);
- resolved rows are size-capped per sid while open rows never are (ResolvedRowsAreBounded);
- the answer body (`Re: <text> — <reply>`, both halves marker-neutralized) and the two drive
  ops, userTodoAnswer / userTodoDismiss (AnswerBody, DriveOps, MarkerNeutralizerVariants);
- the DELIVERY-keyed stamp end to end: a parked answer carries its id and stamps at the drain,
  a recall reads the id off the queue entry it removes and reopens, a corroborated loss (a
  drop-marked echo, a rewind-dropped head) reopens unless the transcript proves the text landed,
  and the boot pass re-offers marks whose reopen a kernel death cut short (DeliveryKeyedStamp,
  RecallRidesTheEntry, LostAnswerReopens, LossBootPass);
- the tmux refusal seam: TmuxBackend.send is fire-and-forget and _tmux_send's clear-guard can
  refuse the paste on its thread, so the send carries the id, persists a pending-paste mark
  before returning its nonce, and the paste thread's verdict reopens (refused) or clears
  (delivered); a refusal that outruns the stamp flips the mark and the stamp stands down at its
  own write moment, matched BY NONCE so a stale flag never eats a later delivered answer; the
  boot pass re-offers marks a dead kernel left (TmuxPasteRefusalReopens, TmuxPendingPasteMarks,
  TmuxStampStandDown, SeamOrderPins, TmuxBatchDuplicateAnswers);
- the authority tier as a grep-provable pin: judge.py never names the store or its helpers
  (NoJudgeWritesTheStore).

SYNTHETIC fixtures only: placeholder UUIDs, the notes-api demo world.
"""
import contextlib
import inspect
import io
import json
import os
import re
import tempfile
import threading
import time
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_SERVE_TOKEN"] = "testtok"
km = SourceFileLoader("romp_kernel_usertodos", os.path.join(BIN, "romp-kernel")).load_module()
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
SID2 = "22222222-3333-4444-5555-666666666666"
NOW = 1781200000


class _StoreSandbox(unittest.TestCase):
    """Per-test STATE sandbox + cache reset — the _session_flags test idiom."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = Path(self.td.name)
        km._user_todos_cache.clear()

    def tearDown(self):
        jd.STATE = self.saved
        self.td.cleanup()
        km._user_todos_cache.clear()


class StoreRoundTrip(_StoreSandbox):
    def test_add_mints_a_ut_id_and_persists_the_record(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", "OAuth vs cookie")
        self.assertRegex(tid, r"^ut-[0-9a-f]{8}$")
        rec = km._user_todos()[SID][0]
        self.assertEqual(rec["id"], tid)
        self.assertEqual(rec["text"], "Need the auth-scheme decision to wire login")
        self.assertEqual(rec["detail"], "OAuth vs cookie")
        self.assertIsInstance(rec["createdT"], int)
        self.assertNotIn("resolved", rec, "a fresh todo is open")

    def test_detail_is_optional_and_absent_when_empty(self):
        km._add_user_todo(SID, "Need a test credential for the api session")
        self.assertNotIn("detail", km._user_todos()[SID][0])

    def test_the_mtime_cache_sees_the_write(self):
        self.assertEqual(km._user_todos(), {})            # primes the (empty) read path
        km._add_user_todo(SID, "Need your pick of the two route layouts")
        self.assertTrue(km._user_todos().get(SID), "the (mtime_ns,size) cache key sees the write")

    def test_ids_never_collide_within_a_session(self):
        ids = {km._add_user_todo(SID, "todo %d" % i) for i in range(20)}
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
        # the rows ride the dedup-compared chat payload: a derived per-build value here (an age, a
        # `now`) would defeat the serialized-payload dedup and re-send the full chat every push
        km._add_user_todo(SID, "Need the auth-scheme decision", "OAuth vs cookie")
        km._add_user_todo(SID, "Need a staging API key")
        rows = {t["text"]: t for t in km._open_user_todos(SID)}
        self.assertEqual(set(rows["Need the auth-scheme decision"]), {"id", "text", "createdT", "detail"})
        self.assertEqual(set(rows["Need a staging API key"]), {"id", "text", "createdT"},
                         "detail rides iff the ask has one")
        self.assertEqual(km._open_user_todos(SID), km._open_user_todos(SID), "byte-stable across builds")

    def test_a_garbled_or_non_dict_file_reads_as_empty(self):
        p = jd.STATE / "user-todos.json"
        p.write_text("not json")
        self.assertEqual(km._user_todos(), {})
        km._user_todos_cache.clear()
        p.write_text(json.dumps(["enabled"]))
        self.assertEqual(km._user_todos(), {})


class ResolutionStamps(_StoreSandbox):
    """Resolution STAMPS rather than deletes — the record carries its own history."""

    def test_each_clearing_event_stamps_its_own_kind(self):
        for kind in ("answered", "dismissed", "withdrawn"):
            tid = km._add_user_todo(SID, "need for %s" % kind)
            self.assertTrue(km._resolve_user_todo(SID, tid, kind))
            rec = next(t for t in km._user_todos()[SID] if t["id"] == tid)
            self.assertEqual(rec["resolved"]["kind"], kind)
            self.assertIsInstance(rec["resolved"]["t"], int)

    def test_a_resolved_todo_leaves_the_open_list_but_not_the_file(self):
        tid = km._add_user_todo(SID, "Need the rate-limit ceiling")
        km._resolve_user_todo(SID, tid, "answered")
        self.assertEqual(km._open_user_todos(SID), [])
        self.assertEqual(len(km._user_todos()[SID]), 1, "stamped, never deleted")

    def test_unknown_id_is_refused_never_a_silent_success(self):
        self.assertFalse(km._resolve_user_todo(SID, "ut-deadbeef", "withdrawn"))

    def test_a_second_stamp_is_refused_and_the_first_survives(self):
        tid = km._add_user_todo(SID, "Need the schema review")
        self.assertTrue(km._resolve_user_todo(SID, tid, "answered"))
        self.assertFalse(km._resolve_user_todo(SID, tid, "withdrawn"),
                         "already cleared — the withdraw must be told so, loudly")
        rec = km._user_todos()[SID][0]
        self.assertEqual(rec["resolved"]["kind"], "answered", "the first stamp is the history")

    def test_reopen_lifts_an_answered_stamp_only(self):
        # the ONE un-stamp: an answer whose delivery came undone puts the ask back; a dismiss or a
        # withdraw had no delivery to fail and never reopens
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
    """The store lock (_user_todos_lock, the _comments_lock doctrine): the routes' HTTP threads,
    the WS dispatch threads and the pusher all read-modify-write this file, so without the lock
    two postal buses registering concurrently silently lost CONFIRMED rows, and a racing answer +
    withdraw both reported success with last-write-wins on the surviving stamp."""

    def test_every_store_mutation_runs_under_the_lock(self):
        # deterministic pin: the publish step of every mutation must hold the lock — the exact
        # interleaving the concurrent shapes below hammer probabilistically
        real_write = km._write_user_todos
        seen = []

        def guarded(cur):
            # the lock is re-entrant (an answered stamp's stand-down decides and records inside ONE
            # critical section), and an RLock has no .locked() on 3.12 — _is_owned() is the sharper
            # predicate anyway: every mutation publishes on the thread that took the lock, so "the
            # CALLING thread holds it" is exactly the claim, where .locked() would settle for
            # "someone does"
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
        # two threads (two postal buses' route threads) register in parallel; every row postal
        # confirmed must be in the file afterwards
        n = 60
        barrier = threading.Barrier(2)

        def writer(sid):
            barrier.wait()
            for i in range(n):
                km._add_user_todo(sid, "todo %d" % i)

        ts = [threading.Thread(target=writer, args=(s,)) for s in (SID, SID2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        km._user_todos_cache.clear()
        d = json.loads((jd.STATE / "user-todos.json").read_text())
        self.assertEqual(len(d.get(SID) or []) + len(d.get(SID2) or []), 2 * n,
                         "registrations lost to an unlocked read-modify-write")

    def test_a_racing_answer_and_withdraw_cannot_both_succeed(self):
        # whatever the schedule, exactly ONE clearing event wins and the surviving stamp is the
        # winner's — the loser is told loudly (False)
        for attempt in range(100):
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
    """_user_todo_session_ended: has this todo's session ENDED, by CORROBORATED evidence only. An
    SDK-owned sid answers from the registry's alive bit; a reg-less (tmux) sid from the durable
    death record under STATE/gone, which counts only while it is the NEWEST event — a revival's
    fresh states row un-ends the session without anyone deleting the marker. A raw listing miss
    (a tmux list collapse) is never evidence: no marker means not ended."""

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
        # a REVIVAL supersedes the marker with newer states evidence, without deleting it
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
    """The sweep keys on the rows' own corroborated evidence — resolved AND a durable death
    record — NEVER on a display/known-set: the tab-GC's set drops alive-but-idle tmux sessions
    during list-collapse cycles and 48h transcript ageouts, and a first cut deleted a LIVE
    session's open asks on exactly that evidence (the vanishing the ADR exists to stop)."""

    def _mark_dead(self, sid, t=NOW):
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (sid + ".json")).write_text(json.dumps({"t": t, "by": "gone"}))

    def test_open_todos_survive_regardless_of_any_display_set(self):
        km._add_user_todo(SID, "live but idle — a list collapse must not delete me")
        km._add_user_todo(SID2, "aged out of the discover window — still standing")
        km._prune_user_todos()
        self.assertEqual(set(km._user_todos()), {SID, SID2},
                         "open todos persist until user dismiss / agent withdraw — no set miss")

    def test_open_todos_of_a_dead_session_survive_too(self):
        km._add_user_todo(SID, "my session died — revive returns me")
        self._mark_dead(SID)
        km._prune_user_todos()
        self.assertEqual(len(km._open_user_todos(SID)), 1,
                         "hidden by the ended gate, never deleted — the ADR's whole point")

    def test_resolved_rows_of_a_dead_session_leave(self):
        tid = km._add_user_todo(SID, "answered, then the session died")
        km._resolve_user_todo(SID, tid, "answered")
        self._mark_dead(SID)
        km._prune_user_todos()
        self.assertNotIn(SID, km._user_todos(), "nothing open, session dead → the sid leaves")

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
        # the marker counts only while it is the NEWEST event (_death_stamp_due's time key):
        # a revival's fresh states row un-ends the session without deleting the marker
        tid = km._add_user_todo(SID, "answered, session died, then revived")
        km._resolve_user_todo(SID, tid, "answered")
        self._mark_dead(SID, t=NOW)
        (jd.STATE / "states").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "states" / (SID + ".jsonl")).write_text(
            json.dumps({"t": NOW + 60, "state": "idle"}) + "\n")
        km._prune_user_todos()
        self.assertEqual(len(km._user_todos()[SID]), 1, "revived → not ended → history stays")

    def test_a_noop_prune_never_writes(self):
        km._add_user_todo(SID, "still here")
        p = jd.STATE / "user-todos.json"
        before = p.stat().st_mtime_ns
        km._prune_user_todos()
        self.assertEqual(p.stat().st_mtime_ns, before, "nothing gone → no write (no hot-path churn)")

    def test_the_sweep_rides_the_tab_session_pass_but_not_its_known_set(self):
        # wired where the session-order GC runs — one call per pusher pass — but keyed on its own
        # corroborated evidence, never the display set the tab-GC prunes by
        src = inspect.getsource(km._chat_tab_sessions)
        self.assertIn("_prune_user_todos()", src)
        self.assertNotIn("_prune_user_todos(known", src)
        self.assertNotIn("_prune_user_todos(live", src)


class ChatSigFold(_StoreSandbox):
    """The per-sid chat-build-sig fold (_user_todo_fp): a todo write changes neither the transcript
    nor the states file, so without the store in the signature a background tab's cached chat never
    showed the new row. Folded PER-SID: another session's write is not this tab's repaint."""

    def setUp(self):
        super().setUp()
        self.tpath = jd.STATE / (SID + ".jsonl")
        self.tpath.write_text("")
        self.saved_sdk = km._sdk
        km._sdk = lambda: None

    def tearDown(self):
        km._sdk = self.saved_sdk
        super().tearDown()

    def test_a_todo_write_busts_the_chat_build_cache(self):
        sess = {"path": str(self.tpath), "sid": SID, "anchor": ""}
        before = km._chat_build_sig(sess)
        km._add_user_todo(SID, "Need the auth-scheme decision")
        after = km._chat_build_sig(sess)
        self.assertNotEqual(before, after)

    def test_another_sessions_todo_write_busts_no_one_elses_cache(self):
        sess = {"path": str(self.tpath), "sid": SID, "anchor": ""}
        before = km._chat_build_sig(sess)
        km._add_user_todo(SID2, "api: need the auth decision")
        after = km._chat_build_sig(sess)
        self.assertEqual(before, after, "another session's row is not this tab's repaint")

    def test_the_fold_is_byte_stable_while_the_rows_stand(self):
        km._add_user_todo(SID, "Need the auth-scheme decision")
        sess = {"path": str(self.tpath), "sid": SID, "anchor": ""}
        self.assertEqual(km._chat_build_sig(sess), km._chat_build_sig(sess))
        self.assertIsNone(km._user_todo_fp(SID2), "no rows: nothing to fold")
        self.assertTrue(km._user_todo_fp(SID))

    def test_a_stamp_busts_the_owning_cache_too(self):
        # a withdraw / answer / dismiss changes the split card with no transcript write either
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        sess = {"path": str(self.tpath), "sid": SID, "anchor": ""}
        before = km._chat_build_sig(sess)
        km._resolve_user_todo(SID, tid, "withdrawn")
        self.assertNotEqual(before, km._chat_build_sig(sess))


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
    """POST /usertodo and /usertodo/withdraw — the kernel legs the postal tools stand on."""

    def setUp(self):
        super().setUp()
        self._push = (km._push_all, km._push_soon)
        self.pushed_soon = []
        # the routes must never build views synchronously (the ack-fast contract below) — a stray
        # _push_all here is a bug, so it BLOWS UP instead of silently passing
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

    def test_register_returns_the_minted_id_and_writes_the_store(self):
        code, res = self._post("/usertodo", {"id": SID, "text": "Need the auth-scheme decision",
                                             "detail": "OAuth vs cookie — either unblocks login"})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        self.assertRegex(res["todoId"], r"^ut-[0-9a-f]{8}$")
        rec = km._user_todos()[SID][0]
        self.assertEqual(rec["id"], res["todoId"])
        self.assertEqual(rec["detail"], "OAuth vs cookie — either unblocks login")

    def test_register_refuses_a_bodyless_or_textless_ask(self):
        self.assertEqual(self._post("/usertodo", {"id": SID})[0], 400)
        self.assertEqual(self._post("/usertodo", {"id": SID, "text": "   "})[0], 400)
        self.assertEqual(self._post("/usertodo", {"text": "no sid"})[0], 400)
        code, _ = _serve_post("/usertodo", b"not json", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400)
        self.assertEqual(km._user_todos(), {}, "a refused register writes nothing")

    def test_withdraw_requires_the_serve_token(self):
        code, _ = self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-deadbeef"}, token=False)
        self.assertEqual(code, 403)

    def test_withdraw_stamps_withdrawn(self):
        _, res = self._post("/usertodo", {"id": SID, "text": "Need the fixture format pick"})
        code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        self.assertEqual(code, 200)
        self.assertTrue(out["ok"])
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "withdrawn")

    def test_withdraw_refuses_a_bodyless_ask(self):
        self.assertEqual(self._post("/usertodo/withdraw", {"id": SID})[0], 400)
        self.assertEqual(self._post("/usertodo/withdraw", {"todoId": "ut-deadbeef"})[0], 400)
        code, _ = _serve_post("/usertodo/withdraw", b"not json", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400)

    def test_withdraw_of_an_unknown_or_cleared_id_answers_ok_false(self):
        code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-deadbeef"})
        self.assertEqual(code, 200)
        self.assertFalse(out["ok"], "a loud, plain answer — never a silent success")
        self.assertTrue(out.get("error"))
        _, res = self._post("/usertodo", {"id": SID, "text": "once"})
        self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        _, again = self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        self.assertFalse(again["ok"])

    def test_the_routes_ack_fast_and_never_push_synchronously(self):
        # the postal bus times its POST out at 2s: an inline _push_all (a synchronous build of
        # every session's payload) outran it, so a SAVED todo came back as a loud false failure
        # ("will NOT see it — try again") and the agent's retry filed a duplicate. The setUp
        # _push_all stub raises, so this passing IS the proof; the woken pusher carries the row.
        code, res = self._post("/usertodo", {"id": SID, "text": "Need the auth-scheme decision"})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        self.assertEqual(code, 200)
        self.assertTrue(out["ok"])
        self.assertEqual(len(self.pushed_soon), 2, "each route wakes the pusher instead")

    def test_a_refused_withdraw_wakes_nothing(self):
        # nothing changed, so there is nothing for the pusher to carry
        self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-deadbeef"})
        self.assertEqual(self.pushed_soon, [])

    def test_a_remote_session_is_forwarded_and_the_answer_relayed(self):
        # a sid that lives on a federated kernel: the local route forwards over that host's tunnel
        # (the /working shape) and relays the remote's answer; the local store stays untouched
        saved = (km._host_for_sid, km._remote_forward)
        calls = []
        km._host_for_sid = lambda sid: {"host": "TESTHOST"} if sid == SID else None
        km._remote_forward = lambda r, path, body: (calls.append((path, body)) or
                                                    {"ok": True, "todoId": "ut-9f2c1a34"})
        try:
            code, res = self._post("/usertodo", {"id": SID, "text": "Need the port", "detail": "8443?"})
            self.assertEqual((code, res), (200, {"ok": True, "todoId": "ut-9f2c1a34"}))
            code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-9f2c1a34"})
            self.assertEqual((code, out), (200, {"ok": True}))
        finally:
            km._host_for_sid, km._remote_forward = saved
        self.assertEqual(calls, [("/usertodo", {"id": SID, "text": "Need the port", "detail": "8443?"}),
                                 ("/usertodo/withdraw", {"id": SID, "todoId": "ut-9f2c1a34"})])
        self.assertEqual(km._user_todos(), {}, "the remote kernel owns that session's store")

    def test_a_remote_forward_that_fails_is_reported_not_faked(self):
        saved = (km._host_for_sid, km._remote_forward)
        km._host_for_sid = lambda sid: {"host": "TESTHOST"}
        km._remote_forward = lambda r, path, body: None
        try:
            code, res = self._post("/usertodo", {"id": SID, "text": "Need the port"})
            self.assertEqual(code, 200)
            self.assertFalse(res["ok"], "no id came back, so the agent must not hear 'noted'")
            code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-9f2c1a34"})
            self.assertFalse(out["ok"])
        finally:
            km._host_for_sid, km._remote_forward = saved


class ResolvedRowsAreBounded(_StoreSandbox):
    """A never-dying session's resolved rows would accumulate without bound (the prune clears them
    only at session death — right for history, wrong as an invariant on a box whose sessions live
    for weeks), and _user_todo_fp re-serializes every row on every chat build. A per-sid SIZE cap
    on RESOLVED rows only: the newest _USER_TODO_RESOLVED_KEEP stay, the oldest leave. OPEN rows are
    NEVER capped — the ADR's authority tier: an open ask leaves the store by answer/dismiss/withdraw
    alone, never by volume."""

    def test_resolved_rows_keep_only_the_newest_K(self):
        K = km._USER_TODO_RESOLVED_KEEP
        first = km._add_user_todo(SID, "the oldest resolved row")
        km._resolve_user_todo(SID, first, "dismissed")
        for i in range(K):
            t = km._add_user_todo(SID, "later todo %d" % i)
            km._resolve_user_todo(SID, t, "answered")
        resolved = [t for t in km._user_todos()[SID] if t.get("resolved")]
        self.assertEqual(len(resolved), K, "a size bound, not a time heuristic")
        self.assertNotIn(first, [t["id"] for t in resolved], "the OLDEST row is the one that left")

    def test_every_stamp_kind_is_capped_the_same_way(self):
        K = km._USER_TODO_RESOLVED_KEEP
        for i in range(K + 7):
            t = km._add_user_todo(SID, "todo %d" % i)
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
                         "every open ask survives — the cap reads resolved rows only")
        self.assertEqual(len([t for t in got if t.get("resolved")]), K)

    def test_the_fp_is_bounded_by_the_cap(self):
        K = km._USER_TODO_RESOLVED_KEEP
        for i in range(K * 2):
            t = km._add_user_todo(SID, "todo %d" % i)
            km._resolve_user_todo(SID, t, "answered")
        self.assertEqual(len(km._user_todos()[SID]), K,
                         "the per-sid fold hashes at most K resolved rows, forever")
        self.assertTrue(km._user_todo_fp(SID))


class BuildSessionSeam(unittest.TestCase):
    """The chat payload: the top-level `userTodos` field (the upsert merge seam) AND the split-card
    `todo` event that carries the same rows — the chatTail wire re-sends changed EVENTS only, so a
    row change must be an event change or a caught-up client never hears of it. Fixture mirrors
    the build_session suites' discover setup (names + transcript in the munged dir)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        cdir = td / "launchdir"
        cdir.mkdir()
        proj = td / "projects"
        pdir = proj / jd.re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
        pdir.mkdir(parents=True)
        self.tpath = pdir / (SID + ".jsonl")
        names = td / "names"
        names.mkdir()
        (names / SID).write_text("web\t%s\t#abcdef\n" % str(cdir))
        self.saved = (jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATE, km.NAMES,
                      km._read_task_store, km._fold_tasks, km._tmux_sessions, km._GLOBAL_CLAUDE_MD)
        jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATE = names, proj, td / "goals", td
        km.NAMES = names
        km._GLOBAL_CLAUDE_MD = td / "no-global.md"           # keep a real ~/.claude/CLAUDE.md out of the fixture
        km._read_task_store = lambda fsid, fold=None: []
        km._tmux_sessions = lambda: {SID: {"state": "idle", "since": NOW - 100, "model": "", "effort": "",
                                           "context": None, "compactPct": None, "color": None}}
        jd.GOALDIR.mkdir(parents=True)
        km._parse_cache.clear()
        km._user_todos_cache.clear()
        rows = [
            {"type": "user", "uuid": "u1", "timestamp": "2026-06-01T00:00:00Z",
             "sessionId": SID, "message": {"role": "user", "content": "wire the login routes"}},
            {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "timestamp": "2026-06-01T00:00:05Z",
             "sessionId": SID,
             "message": {"role": "assistant", "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": "starting on the open routes"}]}},
        ]
        self.tpath.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def tearDown(self):
        (jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATE, km.NAMES,
         km._read_task_store, km._fold_tasks, km._tmux_sessions, km._GLOBAL_CLAUDE_MD) = self.saved
        km._parse_cache.clear()
        km._user_todos_cache.clear()
        self.td.cleanup()

    def _todo_events(self, payload):
        return [e for e in payload["events"] if e.get("kind") == "todo"]

    def test_no_todos_and_no_tasks_mean_no_event_and_an_empty_field(self):
        payload = km.build_session(SID, NOW)
        self.assertEqual(payload["userTodos"], [])
        self.assertEqual(self._todo_events(payload), [])

    def test_open_todos_ride_both_the_field_and_the_event(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", "OAuth vs cookie")
        payload = km.build_session(SID, NOW)
        self.assertEqual([t["id"] for t in payload["userTodos"]], [tid])
        evs = self._todo_events(payload)
        self.assertEqual(len(evs), 1, "one split card, by the composer")
        self.assertEqual(evs[0]["tasks"], [])
        self.assertEqual(evs[0]["userTodos"], payload["userTodos"],
                         "the event carries the rows — the chatTail delta re-sends events only")
        self.assertIs(payload["events"][-1], evs[0], "appended last: the card sits by the composer")

    def test_agent_tasks_and_user_todos_share_one_card(self):
        km._read_task_store = lambda fsid, fold=None: [
            {"id": "1", "subject": "Build the fixtures", "activeForm": None, "status": "pending"}]
        km._add_user_todo(SID, "Need a test credential for the api session")
        payload = km.build_session(SID, NOW)
        evs = self._todo_events(payload)
        self.assertEqual(len(evs), 1)
        self.assertEqual(len(evs[0]["tasks"]), 1)
        self.assertEqual(len(evs[0]["userTodos"]), 1)

    def test_a_card_without_user_todos_keeps_its_pre_existing_shape(self):
        # the everyday card (agent tasks, no open todos) serializes exactly as before this seam
        # existed: no `userTodos` key at all — an empty list would be a new byte in every payload
        km._read_task_store = lambda fsid, fold=None: [
            {"id": "1", "subject": "Build the fixtures", "activeForm": None, "status": "pending"}]
        payload = km.build_session(SID, NOW)
        evs = self._todo_events(payload)
        self.assertEqual(len(evs), 1)
        self.assertEqual(set(evs[0]), {"kind", "tasks"})

    def test_an_unreadable_task_store_still_carries_the_rows(self):
        # FAIL LOUDLY on the task store, but the waiting-on-you rows come from a DIFFERENT store:
        # the error card carries them too, so an unreadable ~/.claude/tasks never hides an ask
        km._read_task_store = lambda fsid, fold=None: None
        km._fold_tasks = lambda session: [{"id": "1", "subject": "Build the fixtures",
                                           "activeForm": None, "status": "pending"}]
        km._add_user_todo(SID, "Need the staging port")
        payload = km.build_session(SID, NOW)
        evs = self._todo_events(payload)
        self.assertEqual(len(evs), 1)
        self.assertTrue(evs[0]["error"])
        self.assertEqual(evs[0]["tasks"], [])
        self.assertEqual(len(evs[0]["userTodos"]), 1)
        # …and the error card WITHOUT open todos keeps its pre-existing shape
        km._user_todos_cache.clear()
        (jd.STATE / "user-todos.json").write_text("{}")
        evs = self._todo_events(km.build_session(SID, NOW))
        self.assertEqual(set(evs[0]), {"kind", "tasks", "error"})

    def test_resolved_todos_ship_nowhere(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "dismissed")
        payload = km.build_session(SID, NOW)
        self.assertEqual(payload["userTodos"], [])
        self.assertEqual(self._todo_events(payload), [])

    def test_the_field_is_clock_invariant(self):
        # _send_client dedups by the serialized payload (the firstSeen lesson): the field must
        # serialize identically across builds when nothing changed
        km._add_user_todo(SID, "Need the auth-scheme decision")
        a = km.build_session(SID, NOW)
        b = km.build_session(SID, NOW + 600)
        self.assertEqual(json.dumps(a["userTodos"]), json.dumps(b["userTodos"]))

    def test_an_ended_session_hides_its_todos_without_clearing_them(self):
        km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        payload = km.build_session(SID, NOW)
        self.assertEqual(payload["userTodos"], [], "ended (registry alive:false) → hidden everywhere")
        self.assertEqual(self._todo_events(payload), [])
        self.assertEqual(len(km._open_user_todos(SID)), 1, "hidden, not cleared — revive returns them")
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": True}))
        self.assertEqual(len(km.build_session(SID, NOW)["userTodos"]), 1,
                         "a dormant session (alive:true, no thread) still shows its todos")

    def test_a_dead_tmux_session_hides_its_todos_too(self):
        # _thread_reg is {} for tmux, so the registry gate alone left a dead tmux session's todos
        # rendered with a live Reply — the gate must also read the durable death record
        # (STATE/gone, corroborated at write time), never a raw listing miss
        km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps({"t": NOW - 50, "by": "gone"}))
        km._parse_cache.clear()
        payload = km.build_session(SID, NOW)
        self.assertEqual(payload["userTodos"], [], "dead tmux session → hidden everywhere")
        self.assertEqual(self._todo_events(payload), [])
        self.assertEqual(len(km._open_user_todos(SID)), 1, "hidden, not cleared")
        # a REVIVAL supersedes the marker (newer states evidence) without deleting it
        (jd.STATE / "states").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "states" / (SID + ".jsonl")).write_text(
            json.dumps({"t": NOW - 10, "state": "idle"}) + "\n")
        km._parse_cache.clear()
        self.assertEqual(len(km.build_session(SID, NOW)["userTodos"]), 1,
                         "revived → the todos return with the session")

    def test_a_muted_session_still_ships_its_todos_to_the_tab(self):
        # THE DESIGNED ASYMMETRY (review call, 2026-08-22): hideFromFeed quiets the feed and every
        # aggregate built from it, because mute means "stop interrupting me about this session".
        # The CHAT payload still carries the open todos: the session's own tab remains truthful
        # about what it holds.
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        (jd.STATE / "session-flags.json").write_text(json.dumps({SID: {"hideFromFeed": True}}))
        km._flags_cache.clear()
        payload = km.build_session(SID, NOW)
        self.assertTrue(payload["hideFromFeed"])
        self.assertEqual(len(payload["userTodos"]), 1, "muted ≠ hidden on the session's own tab")
        self.assertEqual(len(self._todo_events(payload)), 1, "the split card renders too")

    def test_a_row_carries_detail_iff_the_ask_has_one(self):
        # The row's "more behind this" hint (render.ts renderTodo) keys on the PRESENCE of `detail`
        # on the payload row — that presence is the has-detail flag (no separate boolean: the row
        # already carries the text, and a second field could drift from it). So it must track the
        # store exactly: present, with the text, when the ask carries a non-blank detail; ABSENT
        # (not empty, not null) for a bare one-line ask — and a blank or whitespace-only detail
        # written straight into the store is no detail either, so the seam (_open_user_todos), not
        # just the register route, is what drops it.
        (jd.STATE / "user-todos.json").write_text(json.dumps({SID: [
            {"id": "ut-aaaaaaaa", "text": "Need the auth-scheme decision to wire login",
             "createdT": NOW - 40, "detail": "OAuth vs cookie — either unblocks login"},
            {"id": "ut-bbbbbbbb", "text": "Need a test credential for the api session", "createdT": NOW - 30},
            {"id": "ut-cccccccc", "text": "Need your pick of the two route layouts",
             "createdT": NOW - 20, "detail": "  \n\t "},
            {"id": "ut-dddddddd", "text": "Need the staging port", "createdT": NOW - 10, "detail": ""}]}))
        km._user_todos_cache.clear()
        payload = km.build_session(SID, NOW)
        rows = {t["id"]: t for t in payload["userTodos"]}
        self.assertEqual(set(rows), {"ut-aaaaaaaa", "ut-bbbbbbbb", "ut-cccccccc", "ut-dddddddd"})
        self.assertEqual(rows["ut-aaaaaaaa"]["detail"], "OAuth vs cookie — either unblocks login")
        self.assertNotIn("detail", rows["ut-bbbbbbbb"], "a bare ask ships no detail key at all")
        self.assertNotIn("detail", rows["ut-cccccccc"], "whitespace-only detail is no detail")
        self.assertNotIn("detail", rows["ut-dddddddd"], "an empty detail is no detail")
        ev_rows = {t["id"]: t for t in self._todo_events(payload)[0]["userTodos"]}
        self.assertEqual({k: ("detail" in v) for k, v in ev_rows.items()},
                         {k: ("detail" in v) for k, v in rows.items()},
                         "the split-card event rows carry the same has-detail truth as the field")

    def test_the_chat_tail_delta_carries_the_user_todos_field(self):
        # the chat wire's steady state is chatTail deltas: a caught-up client that only merged
        # full session frames kept a stale top-level field (the tab glyph's read, a later slice)
        rows = [{"id": "ut-aaaaaaaa", "text": "Need the auth-scheme decision", "createdT": NOW}]
        evs = [{"uuid": "u1", "kind": "user", "text": "wire the login routes"},
               {"uuid": "a1", "kind": "todo", "tasks": [], "userTodos": rows}]
        m = {"type": "session", "id": SID, "events": evs, "status": {"state": "idle"},
             "userTodos": rows}
        got = []
        c = {"send": lambda s: got.append(json.loads(s)), "sent": {},
             "echat": {SID: ("u1", 0)}}                # caught up from event 0 → the delta path
        km._send_chat(c, m, None, 1, False)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["type"], "chatTail", "the caught-up client got the delta")
        self.assertEqual(got[0]["userTodos"], rows,
                         "the field rides the delta — byte-stable store values, dedup-safe")

    def test_the_chat_tail_delta_of_a_todo_less_session_carries_an_empty_field(self):
        # riding EVERY delta (like status) is what keeps the field honest after the last todo
        # clears: a changed-only attach would need per-client prev tracking to send the []
        m = {"type": "session", "id": SID, "userTodos": [],
             "events": [{"uuid": "u1", "kind": "user", "text": "wire the login routes"},
                        {"uuid": "a1", "kind": "assistant", "text": "starting"}],
             "status": {"state": "idle"}}
        got = []
        c = {"send": lambda s: got.append(json.loads(s)), "sent": {}, "echat": {SID: ("u1", 0)}}
        km._send_chat(c, m, None, 1, False)
        self.assertEqual(got[0]["type"], "chatTail")
        self.assertEqual(got[0]["userTodos"], [])


class AnswerBody(unittest.TestCase):
    """The injected reply: the todo's own short line as the anchor, then the user's words —
    `Re: <text> — <reply>` (plans/user-todos.md). Voice-scanned by test_injected_voice.py."""

    def test_shape(self):
        self.assertEqual(
            km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                      "Go with the session cookie for now."),
            "Re: Need the auth-scheme decision to wire login — Go with the session cookie for now.")

    def test_whitespace_is_trimmed_from_both_halves(self):
        self.assertEqual(km._user_todo_answer_body("  need x \n", "  yes \n"), "Re: need x — yes")

    def test_marker_shaped_text_is_neutralized_in_both_halves(self):
        # both halves are agent/user-supplied: a literal "<!-- romp-…" comment in either would
        # inject a LOOKALIKE marker, and downstream readers key on that exact comment form (the
        # event model's author attribution, the SDK echo's romp-injected check) — the reply would
        # render as romp's own gray card instead of the user's words
        body = km._user_todo_answer_body(
            "Need a call on the note text <!-- romp-goal-id: g1 --> in the fixture",
            "Keep it, but drop the <!-- romp-injected --> part.")
        self.assertNotIn("<!-- romp-", body, "no marker-opening sequence may survive injection")
        self.assertIn("romp-goal-id", body, "the words survive — only the comment form breaks")
        self.assertIn("romp-injected", body)

    def test_clean_text_is_untouched_by_the_neutralizer(self):
        self.assertEqual(km._neutralize_romp_markers("Need the auth-scheme decision"),
                         "Need the auth-scheme decision")


class DriveOps(_StoreSandbox):
    """userTodoAnswer / userTodoDismiss — the user's two gestures on the split card. The answer
    stamp is DELIVERY-keyed: `self.send_result` scripts what _send_or_park reports ("parked", a
    truthy send, or a refusal) so each outcome's contract pins separately."""

    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}
        self._saved = (km._name_of, km._sdk, km._send_or_park)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        self.injected = []
        self.send_result = True                      # default: the immediate path delivered

        def fake_send_or_park(be, sid, text, echo=None, user_todo=None):
            self.injected.append((sid, text, user_todo))
            return self.send_result

        km._send_or_park = fake_send_or_park

    def tearDown(self):
        km._name_of, km._sdk, km._send_or_park = self._saved
        super().tearDown()

    def test_both_ops_are_id_ops(self):
        src = inspect.getsource(km._drive)
        self.assertIn('"userTodoAnswer"', src)
        self.assertIn('"userTodoDismiss"', src)

    def test_dismiss_stamps_dismissed_and_injects_nothing(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        handled = km._drive({"type": "userTodoDismiss", "id": SID, "todoId": tid}, self.client)
        self.assertTrue(handled)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed")
        self.assertEqual(self.injected, [], "dismiss sends nothing into the session")
        self.assertEqual(self.sent, [], "a clean dismiss raises no warning")

    def test_dismiss_of_a_cleared_id_warns_loudly(self):
        km._drive({"type": "userTodoDismiss", "id": SID, "todoId": "ut-deadbeef"}, self.client)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["type"], "warn")

    def test_answer_injects_the_anchored_reply_and_stamps_on_a_truthy_send(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Go with the session cookie for now."}, self.client)
        self.assertEqual(len(self.injected), 1)
        self.assertEqual(self.injected[0][0], SID)
        self.assertEqual(self.injected[0][1],
                         "Re: Need the auth-scheme decision to wire login — "
                         "Go with the session cookie for now.")
        self.assertEqual(self.injected[0][2], tid, "the todo id rides the send for the park path")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "delivered now → stamped now — the user's gesture, never a judgment")

    def test_a_parked_answer_does_not_stamp_yet(self):
        # the park is still recallable (the queued bubble's ✕) — the stamp waits for the drain
        self.send_result = "parked"
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Session cookie."}, self.client)
        self.assertEqual(len(self.injected), 1, "the answer went to the FIFO")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "parked ≠ delivered: stamping here loses the answer to a later recall")
        self.assertEqual(self.sent, [], "a park is normal flow, not an error")

    def test_a_refused_send_warns_and_leaves_the_todo_open(self):
        # the backend said no (an unrevivable SDK session): be loud, the ask still stands
        self.send_result = False
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Session cookie."}, self.client)
        self.assertNotIn("resolved", km._user_todos()[SID][0])
        self.assertEqual(self.sent[0]["type"], "warn")

    def test_a_tmux_nonce_return_is_threaded_into_the_stamp(self):
        # a tmux send answers with the send's NONCE (a str, truthy); the handler must hand exactly
        # that value to the stamp, so the stand-down is bound to THIS send's refusal verdict
        self.send_result = "0123456789abcdef0123456789abcdef"
        seen = []
        real = km._stamp_user_todo_answered

        def spy(sid, tid, text, nonce=None):
            seen.append(nonce)
            return real(sid, tid, text, nonce=nonce)
        km._stamp_user_todo_answered = spy
        self.addCleanup(setattr, km, "_stamp_user_todo_answered", real)
        tid = km._add_user_todo(SID, "Need the staging port")
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "8443."}, self.client)
        self.assertEqual(seen, [self.send_result])
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_answer_to_an_ended_sdk_session_is_refused_loudly(self):
        # sending into a dead session loses the answer while the stamp reads 'answered' — refuse
        # BEFORE the send, keep the todo open, tell the user how to make it answerable (revive)
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Session cookie."}, self.client)
        self.assertEqual(self.injected, [], "nothing may be sent into the void")
        self.assertEqual(self.sent[0]["type"], "warn")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the ask still stands")

    def test_answer_to_a_dead_tmux_session_is_refused_loudly(self):
        # _thread_reg is {} for tmux: the gate must also read the durable death record, or the
        # fire-and-forget tmux send "succeeds" into a nonexistent pane and the stamp fires
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps({"t": NOW, "by": "gone"}))
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Session cookie."}, self.client)
        self.assertEqual(self.injected, [], "nothing may be sent into the void")
        self.assertEqual(self.sent[0]["type"], "warn")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the ask still stands")

    def test_a_dormant_sdk_session_still_takes_the_answer(self):
        # dormant (alive:true, no thread) is addressable — the send path auto-revives it
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": True}))
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Session cookie."}, self.client)
        self.assertEqual(len(self.injected), 1)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_answer_to_a_cleared_id_sends_nothing_and_warns(self):
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": "ut-deadbeef",
                   "text": "too late"}, self.client)
        self.assertEqual(self.injected, [])
        self.assertEqual(self.sent[0]["type"], "warn")

    def test_an_empty_answer_is_not_a_drive_op(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        self.assertFalse(km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                                    "text": "   "}, self.client))
        self.assertEqual(km._open_user_todos(SID)[0]["id"], tid, "nothing was stamped")

    def test_the_warnings_speak_to_the_person_not_the_machinery(self):
        # the toasts are read by the person at the dashboard: they name what happened to the
        # answer and what to do next, never a store, a stamp or a queue
        for text in (km._USER_TODO_SETTLED_WARN, km._USER_TODO_ENDED_WARN,
                     km._USER_TODO_UNDELIVERED_WARN):
            low = text.lower()
            for noun in ("store", "stamp", "queue", "todo", "nonce", "mark"):
                self.assertNotIn(noun, low, "%r names machinery: %s" % (text, noun))


class _TodoStr(str):
    """The queue-entry contract the kernel reads back: a plain str for every consumer, with the
    todo id it answers riding as a `todo` attribute (getattr(entry, "todo", "") — duck-typed, so
    this local double pins the CONTRACT, not the SDK's own class)."""

    def __new__(cls, text, todo):
        o = str.__new__(cls, text)
        o.todo = todo
        return o


class _FakeBackend:
    """A forwards_sends backend double for the park/drain/recall pipeline: send() records and
    reports what the test scripts; pending_queued/unqueue model the SDK's recallable queue —
    including the todo id riding ON the queue entry (queue_carries_todos): the entry itself, not
    any kernel-side table, is what a recall reads the id back off."""

    queue_carries_todos = True

    def __init__(self, send_ok=True):
        self.sent = []
        self.send_ok = send_ok
        self.queue = []

    def forwards_sends(self):
        return True

    def send(self, sid, text, user_todo=None):
        if not self.send_ok:
            return False
        if user_todo:
            text = _TodoStr(text, user_todo)
        self.sent.append((sid, text))
        self.queue.append(text)
        return True

    def pending_queued(self, sid):
        return list(self.queue)

    def unqueue(self, sid, idx, expect=None):
        if 0 <= idx < len(self.queue) and (expect is None or self.queue[idx] == expect):
            return self.queue.pop(idx)
        return None


class DeliveryKeyedStamp(_StoreSandbox):
    """The answer stamp keys on DELIVERY (docs/adr/0001's fatal class), end to end through the
    real park machinery: a parked answer carries its todo id, stamps only when the park drains
    into a truthy send, and every recall/drop path leaves (or returns) the todo OPEN — the user
    changed their mind about the ANSWER; the ask still stands."""

    def setUp(self):
        super().setUp()
        self._saved = (km._name_of, km._sdk, km._compacting_now, dict(km._pending_ops))
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        km._pending_ops.clear()                       # a hermetic FIFO: the drain walks EVERY sid
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}

    def tearDown(self):
        km._name_of, km._sdk, km._compacting_now = self._saved[:3]
        km._pending_ops.clear()
        km._pending_ops.update(self._saved[3])
        super().tearDown()

    def _park_an_answer(self):
        km._compacting_now = lambda sid: sid == SID
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        handled = km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                             "text": "Go with the session cookie."}, self.client)
        self.assertTrue(handled)
        ops = km._pending_ops.get(SID) or []
        self.assertTrue(ops and ops[0][0] == "send", "the answer parked (compaction)")
        self.assertEqual(ops[0][3], tid, "the parked op carries the todo id for the drain stamp")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "no stamp at park time")
        return tid, ops

    def test_cancelling_the_parked_answer_leaves_the_todo_open(self):
        # park, then the user clicks ✕ on the queued bubble — the answer is recalled before it
        # ever reached the agent, so the ask must still stand
        tid, ops = self._park_an_answer()
        err = km._cancel_parked(SID, 0, km._parked_md(ops[0]))
        self.assertIsNone(err, "the cancel succeeds")
        self.assertFalse(km._pending_ops.get(SID), "the answer will never be delivered")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "recalled ≠ answered: the row returns, nothing is silently lost")

    def test_the_drain_delivers_and_stamps(self):
        tid, _ = self._park_an_answer()
        km._compacting_now = lambda sid, **k: False        # compaction ended — the FIFO may drain
        be = _FakeBackend()
        saved = km.Sessions.backend_for
        km.Sessions.backend_for = staticmethod(lambda sid: be)
        try:
            km._apply_pending_ops()
        finally:
            km.Sessions.backend_for = saved
        self.assertEqual(len(be.sent), 1, "the parked answer drained into a real send")
        self.assertIn("Re: Need the auth-scheme decision", be.sent[0][1])
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "THE delivery event — the drain — is where the stamp fires")

    def test_a_dropped_dead_session_queue_leaves_the_todo_open(self):
        tid, _ = self._park_an_answer()
        km._compacting_now = lambda sid, **k: False
        saved = km.Sessions.backend_for
        km.Sessions.backend_for = staticmethod(
            lambda sid: (_ for _ in ()).throw(RuntimeError("session is gone")))
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                km._apply_pending_ops()
        finally:
            km.Sessions.backend_for = saved
        self.assertFalse(km._pending_ops.get(SID), "the dead session's queue was dropped")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "dropped ≠ delivered: the ask survives the session")

    def test_a_refused_drain_send_stamps_nothing(self):
        # the drain's send answered falsy (an SDK session that cannot be revived): the op is
        # consumed, nothing was delivered, and the ask still stands
        be = _FakeBackend(send_ok=False)
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        km._deliver_send_batch(be, SID, [("send", body, None, tid)])
        self.assertEqual(be.sent, [])
        self.assertNotIn("resolved", km._user_todos()[SID][0], "a falsy send stamps nothing")

    def test_an_unqueued_answer_reopens_the_todo(self):
        # the immediate SDK path: send() enqueues backend-side (truthy → stamped), but the queued
        # bubble's ✕ can still recall it before it forwards — the recall must re-open the todo,
        # reading the id off the entry it removed (never a kernel-side table)
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        body = km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                         "Go with the session cookie.")
        be = _FakeBackend()
        self.assertTrue(km._backend_send(be, SID, body, user_todo=tid))   # the delivered-now path…
        km._stamp_user_todo_answered(SID, tid, body)                      # …stamps at the truthy send
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err, "the unqueue succeeds")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "recalled before it forwarded → the ask stands again")

    def test_reopen_never_lifts_a_dismiss_or_withdraw(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "dismissed")
        self.assertFalse(km._reopen_user_todo(SID, tid),
                         "only an 'answered' stamp — a failed delivery — may be lifted")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed")


class RecallRidesTheEntry(_StoreSandbox):
    """Two failure modes with one root (2026-08-22): a kernel-side recall map would be IN-MEMORY
    while the SDK queue it tracks is PERSISTED (reg mirror, reseeded at boot) — so a post-restart
    recall would reopen nothing, and any global FIFO cap on the map could evict a live entry. The
    id travels
    WITH the queued message instead (the entry itself carries it; the recall reads it back off the
    entry it removes), so there is nothing kernel-side to lose, restart away, or evict."""

    def _answered_via_backend(self, be=None):
        be = be or _FakeBackend()
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        body = km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                         "Go with the session cookie.")
        self.assertTrue(km._backend_send(be, SID, body, user_todo=tid))
        km._stamp_user_todo_answered(SID, tid, body)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")
        return be, tid, body

    def test_a_post_restart_recall_still_reopens(self):
        # the queue survives a kernel restart (reg mirror); an in-memory map would not — so the
        # recall must work with NO in-kernel memory of the send. The fresh kernel's
        # _cancel_backend_queued sees only the entry, and the entry knows its todo.
        be, tid, body = self._answered_via_backend()
        # "kernel restart": there is deliberately no kernel-side record left to clear — the
        # structural pin below proves the side table is gone, so this cancel IS the fresh kernel
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err, "the post-restart unqueue succeeds (the queue was persisted)")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "the recall reopens the ask — never a false permanent 'answered'")

    def test_the_recall_side_table_is_gone(self):
        # the whole eviction class (a FIFO cap evicting a live entry) dies with the table
        for name in ("_user_todo_recalls", "_USER_TODO_RECALLS_CAP", "_record_user_todo_recall"):
            self.assertFalse(hasattr(km, name),
                             "%s must not come back — the id rides the queue entry" % name)

    def test_many_later_answers_cannot_evict_the_recall(self):
        # 64+ later stamps could evict a live map entry; the id rides the entry now, so no volume
        # of unrelated answers can disarm a recall
        be, tid, body = self._answered_via_backend()
        for i in range(65):
            t2 = km._add_user_todo("00000000-0000-4000-8000-%012d" % i, "todo %d" % i)
            km._stamp_user_todo_answered("00000000-0000-4000-8000-%012d" % i, t2, "body %d" % i)
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err)
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "the recall survives any number of later answers")

    def test_a_lookalike_recall_reopens_nothing(self):
        # the answer was DELIVERED (its entry consumed); a later byte-identical NORMAL send
        # carries no todo id, so recalling that one reopens nothing
        be, tid, body = self._answered_via_backend()
        be.queue.pop(0)                               # the input generator forwards it: delivered
        be.send(SID, body)                            # a plain send, byte-identical, no user_todo
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "the delivered answer stands — nothing rode the lookalike entry")

    def test_a_recalled_entry_never_lifts_a_dismiss(self):
        # end to end: parked answer (no stamp), user dismisses, the drain delivers anyway (the
        # entry carries the id), then the user recalls the queued message — the reopen's
        # answered-only guard keeps the dismiss
        be = _FakeBackend()
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        self.assertTrue(km._resolve_user_todo(SID, tid, "dismissed"))
        km._deliver_send_batch(be, SID, [("send", body, None, tid)])
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed",
                         "the drain's stamp attempt must not overwrite the dismiss")
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed",
                         "reopen must never lift a dismiss — answered-only")

    def test_a_recall_that_finds_no_answered_row_is_loud(self):
        # the entry carries an id whose row is no longer 'answered' (cleared meanwhile, or capped
        # out of the history): the recall itself succeeds, the no-op reopen is SAID
        be = _FakeBackend()
        body = "Re: Need the staging port — 8443."
        self.assertTrue(km._backend_send(be, SID, body, user_todo="ut-00000000"))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIsNone(km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1]))
        self.assertIn("nothing reopened", err.getvalue())
        self.assertIn("ut-00000000", err.getvalue())

    def test_the_drain_hands_the_id_to_the_backend_entry(self):
        # the park path feeds the same root: a drained answer's queue entry carries the id
        # exactly like an immediate send's, so its recall reopens the same way
        be = _FakeBackend()
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        body = km._user_todo_answer_body("Need the auth-scheme decision", "Cookie.")
        km._deliver_send_batch(be, SID, [("send", body, None, tid)])
        self.assertEqual(getattr(be.queue[0], "todo", ""), tid,
                         "the drained entry carries the todo id end to end")

    def test_a_backend_without_the_capability_takes_the_plain_send(self):
        # older fakes and plain backends: neither capability flag → _backend_send hands over the
        # bare text, the call it always took
        class _Plain:
            def __init__(self):
                self.sent = []

            def send(self, sid, text):
                self.sent.append((sid, text))
                return True

        be = _Plain()
        self.assertTrue(km._backend_send(be, SID, "hello", user_todo="ut-12345678"))
        self.assertEqual(be.sent, [(SID, "hello")])


class LostAnswerReopens(_StoreSandbox):
    """A kernel death in the fed-but-unlanded window strands a stamped answer — the dropped-echo
    machinery detects the loss but could not tie it back to the ask. The echo now carries the todo
    id, the backend hands it to _user_todo_answer_lost, and the ask visibly returns to the open
    rows — UNLESS the transcript proves the text actually landed (then the agent has the answer
    and the stamp is true; a landed-but-unpruned echo at kernel death is common, so reopening
    blindly would flap answered asks open on every restart)."""

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
        km._stamp_user_todo_answered(SID, tid, body)
        return tid, body

    def _land(self, text):
        self.turns = [{"atoms": [{"type": "user", "author": "human", "uuid": "u1",
                                  "message": {"role": "user",
                                              "content": [{"type": "text", "text": text}]}}]}]

    def test_a_lost_answer_reopens_the_ask(self):
        tid, body = self._stamped()
        with contextlib.redirect_stderr(io.StringIO()):
            km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "the answer died with its holder — the ask visibly returns")

    def test_a_landed_answer_keeps_its_stamp(self):
        tid, body = self._stamped()
        self._land(body)
        with contextlib.redirect_stderr(io.StringIO()):
            km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "the transcript has the answer — delivered, not lost")

    def test_a_landed_text_block_inside_a_bundle_counts(self):
        # romp bundles injected messages into one user record; per-block matching (the
        # _atom_user_texts contract) must recognize the landed answer inside it
        tid, body = self._stamped()
        self.turns = [{"atoms": [{"type": "user", "author": "human", "uuid": "u1",
                                  "message": {"role": "user", "content": [
                                      {"type": "text", "text": "a restart notice"},
                                      {"type": "text", "text": body}]}}]}]
        with contextlib.redirect_stderr(io.StringIO()):
            km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_an_edge_whitespace_answer_reads_as_landed(self):
        # the CLI records user text verbatim, edge whitespace included, and _atom_user_texts yields
        # it stripped. A match set built from the raw text would never meet such a record, so a
        # delivered answer whose send carried a trailing newline would reopen at every boot: the
        # landed check's forms start from the stripped text — one key on both sides
        tid, body = self._stamped()
        self._land(body + "\n")
        with contextlib.redirect_stderr(io.StringIO()):
            km._user_todo_answer_lost(SID, tid, body + "\n", wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "one key on both sides — delivered, the stamp stands")

    def test_the_landed_match_is_exact_never_substring(self):
        # a record that merely QUOTES the answer is somebody else's message, not this delivery
        tid, body = self._stamped()
        self._land("Quoting what I never received: " + body)
        with contextlib.redirect_stderr(io.StringIO()):
            km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertNotIn("resolved", km._user_todos()[SID][0], "an embedded match is not a delivery")

    def test_the_loss_path_never_lifts_a_dismiss(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "dismissed")
        with contextlib.redirect_stderr(io.StringIO()):
            km._user_todo_answer_lost(SID, tid, "Re: Need the staging port — 8443.", wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed")

    def test_an_unparsable_transcript_fails_toward_the_visible_ask(self):
        # fail loudly, never degrade silently: a broken landed-check reopens (a wrongly-open ask
        # is visible and dismissable; a wrongly-'answered' one is the silent loss the ADR names)
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
        # the inline (wait=True) run REPORTS its verdict — what the tmux mark callers key on
        tid, body = self._stamped()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_answer_lost(SID, tid, body, wait=True), "reopened")
            self.assertEqual(km._user_todo_answer_lost(SID, tid, body, wait=True), "open",
                             "the row is open already — nothing to lift")
            km._resolve_user_todo(SID, tid, "dismissed")
            self.assertEqual(km._user_todo_answer_lost(SID, tid, body, wait=True), "stale")
            tid2, body2 = self._stamped()
            self._land(body2)
            self.assertEqual(km._user_todo_answer_lost(SID, tid2, body2, wait=True), "landed")
        self.assertIsNone(km._user_todo_answer_lost(SID, tid2, body2),
                          "the threaded default answers nothing — the verdict lands on its thread")

    def test_the_backend_wire_is_connected(self):
        # the callback must ride CONSTRUCTION (the boot reseed fires drop marks from __init__,
        # before any post-construction attribute assignment could arm it)
        src = inspect.getsource(km._sdk_locked)
        self.assertIn("todo_lost=_user_todo_answer_lost", src)

    def test_a_sid_outside_the_48h_window_still_gets_the_landed_check(self):
        # the check resolves its session via _sessions(now) — discover's DEFAULT 48h window — so
        # a >48h-idle transcript would skip it silently and a genuinely-landed answer's ask would
        # reopen (a card move with no new information). The check falls back to discover's cached
        # wide walk (the _alive_sessions / DEATH_BACKFILL_WINDOW idiom): it runs whenever the
        # transcript exists at all.
        tid, body = self._stamped()
        self._land(body)
        km._sessions = self._saved[0]        # the REAL _sessions: the window miss must come from
        saved = km.jd.discover               # discover itself, not from the class stub
        try:
            km.jd.discover = (lambda now, window=None, forks=True:
                              [] if window is None else [(SID, "/dev/null", SID, "web")])
            with contextlib.redirect_stderr(io.StringIO()):
                km._user_todo_answer_lost(SID, tid, body, wait=True)
        finally:
            km.jd.discover = saved
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "the transcript exists (wide walk) and holds the answer — delivered, "
                         "the stamp stands")

    def test_no_transcript_anywhere_reopens_and_logs_the_skipped_check(self):
        # fail toward the VISIBLE ask, but never silently: when the landed check cannot run at
        # all (no transcript even in the wide walk), the skip itself is logged before reopening
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
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "no transcript to check → reopen anyway (fail toward visible)")
        self.assertIn("cannot run", err.getvalue(), "…but the skipped check is SAID, not silent")
        self.assertIn(tid, err.getvalue())

    def test_a_reopen_that_finds_no_answered_row_is_loud(self):
        # a capped-out/cleared row means the answer never landed AND no row remains to show the
        # ask — this log line is the only record left
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._user_todo_answer_lost(SID, "ut-00000000", "Re: Need the staging port — 8443.",
                                      wait=True)
        self.assertIn("nothing reopened", err.getvalue())
        self.assertIn("ut-00000000", err.getvalue())


class LossBootPass(_StoreSandbox):
    """_mark_dropped_echoes persists an echo's drop mark IMMEDIATELY and fires the loss seam
    exactly once — for the not-yet-marked echo — while the reopen itself runs on a fire-and-forget
    daemon thread that at boot waits out _sdk_lock through the whole staggered reconcile. A kernel
    death in that window leaves the mark persisted with the reopen undone, and the next boot's
    one-shot marking skips the already-marked echo: the ask would stay falsely 'answered' forever.
    _user_todo_loss_boot_pass is the durability backstop: every boot re-derives the pending set
    from the PERSISTED world alone (an echo drop-marked AND carrying a todo id AND whose store row
    still reads 'answered') and re-offers each to the same landed-check-then-reopen seam —
    idempotent by the seam's own checks, and covering every historical mark."""

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
        km._stamp_user_todo_answered(SID, tid, body)
        return tid, body

    def test_a_marked_then_died_loss_reopens_on_the_next_boot(self):
        # the two-boot shape: boot 1 marked the echo (persisted) and died before its reopen
        # thread ran; boot 2's pass must re-offer the loss or the ask is 'answered' forever
        tid, body = self._stamped()
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": True, "todo": tid}])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 1)
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "the mark survived the death; the boot pass re-offered it and the ask "
                         "visibly returned")

    def test_a_landed_answer_keeps_its_stamp_through_the_pass(self):
        # idempotence half 1: the seam's transcript check still guards the stamp, so the pass
        # can re-offer the same landed echo on every boot without flapping the ask open
        tid, body = self._stamped()
        self.turns = [{"atoms": [{"type": "user", "author": "human", "uuid": "u1",
                                  "message": {"role": "user",
                                              "content": [{"type": "text", "text": body}]}}]}]
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": True, "todo": tid}])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 1)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "landed = delivered; the stamp stands however many boots re-check it")

    def test_rows_not_reading_answered_are_not_offered(self):
        # idempotence half 2: an already-reopened row (open) and a dismissed row fail the
        # answered filter — the pass goes quiet once the reopen has landed
        tid, body = self._stamped()
        km._reopen_user_todo(SID, tid)                       # boot N-1's reopen already landed
        tid2 = km._add_user_todo(SID, "Need the auth-scheme decision")
        km._resolve_user_todo(SID, tid2, "dismissed")        # a dismiss has no delivery to fail
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": True, "todo": tid},
                   {"t": 2, "text": "Re: auth — cookie.", "author": "human", "dropped": True,
                    "todo": tid2}])
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0)
        self.assertNotIn("resolved", km._user_todos()[SID][0])
        self.assertEqual(km._user_todos()[SID][1]["resolved"]["kind"], "dismissed")

    def test_unmarked_or_idless_echoes_are_not_offered(self):
        # an echo still in flight (not drop-marked) belongs to the live path; a plain echo
        # (no id) has nothing to reopen
        tid, body = self._stamped()
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": False, "todo": tid},
                   {"t": 2, "text": "an ordinary lost send", "author": "human", "dropped": True}])
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_one_offer_per_ask_however_many_echoes_carry_it(self):
        # two drop-marked echoes for the same answer (a re-send that also died) are ONE loss
        tid, body = self._stamped()
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": True, "todo": tid},
                   {"t": 2, "text": body, "author": "human", "dropped": True, "todo": tid}])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 1)

    def test_a_missing_or_junk_reg_dir_is_a_quiet_zero(self):
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0, "no sdk/ dir at all")
        (jd.STATE / "sdk").mkdir(parents=True)
        (jd.STATE / "sdk" / "junk.json").write_text("not json{")
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0, "unreadable regs are skipped")

    def test_the_pass_is_wired_into_main_before_any_backend_construction(self):
        # the ordering IS the correctness: the pass must read the regs as the dead kernel left
        # them, before this boot's reseed re-persists new drop marks — that split (pre-existing
        # marks → the pass; new marks → the live path) is what keeps the two from double-firing
        src = inspect.getsource(km.main)
        i = src.index("_user_todo_loss_boot_pass")
        self.assertLess(i, src.index("_boot_warm()"),
                        "_boot_warm's _alive_sessions constructs the backend — the pass runs first")
        self.assertLess(i, src.index("target=_sdk"))


class _FakeTmuxPane:
    """The raw-tmux primitives _tmux_send's paste sequence drives (capture / pane_in_mode /
    send_keys / set_buffer / paste_buffer, plus their checked variants), over a modelled input
    box — test_kernel_pane_clear.py's fake, reduced to what these tests read. `honors_kill` off
    is the clear-guard's refusal shape: a box no Ctrl+U will empty, where the guard REFUSES the
    paste rather than concatenate. `fail` is the dead-server shape: the named checked steps
    ("set_buffer" / "paste_buffer" / "enter") answer False WITHOUT acting — what a real tmux
    whose server died after the clear does (exit 1, and the command reached no pane)."""

    RULE = "─" * 40

    def __init__(self, box_lines=("",), honors_kill=True, fail=()):
        self.box_lines = list(box_lines)
        self.honors_kill = honors_kill
        self.fail = set(fail)
        self.keys_sent = []
        self.buffers = []
        self.pastes = []

    def capture(self, name, join=False, colour=False, t=2.5):
        first, rest = (self.box_lines[0], self.box_lines[1:]) if self.box_lines else ("", [])
        lines = ["  an earlier reply", self.RULE, km.PROMPT_GLYPH + " " + first]
        lines.extend("  " + line for line in rest)
        lines.append(self.RULE)
        return "\n".join(lines)

    def pane_in_mode(self, name, t=2):
        return False

    def send_keys(self, name, *keys, t=3):
        self.keys_sent.append(keys)
        if not self.honors_kill or keys != ("C-u",) or not self.box_lines:
            return
        if self.box_lines[-1]:
            self.box_lines[-1] = ""                 # the CLI kills the line's TEXT first…
        else:
            self.box_lines.pop()                    # …then the emptied line itself

    def set_buffer(self, text):
        self.buffers.append(text)

    def paste_buffer(self, name):
        self.pastes.append(name)

    def set_buffer_checked(self, text):
        if "set_buffer" in self.fail:
            return False
        self.set_buffer(text)
        return True

    def paste_buffer_checked(self, name):
        if "paste_buffer" in self.fail:
            return False
        self.paste_buffer(name)
        return True

    def send_keys_checked(self, name, *keys, t=3):
        if "enter" in self.fail:
            return False
        self.send_keys(name, *keys, t=t)
        return True


class TmuxPasteRefusalReopens(_StoreSandbox):
    """The clear-guard (PR-741) taught _tmux_send's paste thread to REFUSE when the pane's input
    box will not empty — correct for the pane, fatal for a delivery-keyed stamp that keys on the
    truthy send. TmuxBackend.send stays truthy (fire-and-forget), so the answer stamps 'answered'
    at the truthy send, and the refused paste never reaches the agent: with no loss seam on the
    tmux side that is docs/adr/0001's silent-loss class verbatim (before the guard the paste was
    unconditional, so the truthy send really was the delivery). The refusal EVENT now reopens the
    ask: the send carries the todo id, and the paste thread's refuse branch — or a death before
    Enter — hands it to _user_todo_answer_lost, the same reopen the SDK loss path uses, keyed at
    the refusal point itself so BOTH stamping callers (the drive handler's immediate send, the
    park drain's merged batch) are covered by one seam."""

    def setUp(self):
        super().setUp()
        self._saved = (km._TMUX, km._sessions, km._parse, km._compacting_now,
                       dict(km._pending_ops))
        self.be = km._TMUX                 # the REAL backend: send → _tmux_send → the fake pane
        # the LostAnswerReopens stubs: a transcript exists and holds nothing — a refused paste
        # never lands, so the seam's landed check must find no delivery and reopen
        km._sessions = lambda now, window=None, forks=True: [{"sid": SID, "path": "/dev/null"}]
        km._parse = lambda path, sid, now: {"turns": []}
        km._compacting_now = lambda sid, **k: False
        km._pending_ops.clear()
        km._pane_io_locks.clear()
        self._err = contextlib.redirect_stderr(io.StringIO())   # the seam's verdict lines are loud by design
        self._err.__enter__()

    def tearDown(self):
        self._err.__exit__(None, None, None)
        km._TMUX, km._sessions, km._parse, km._compacting_now = self._saved[:4]
        km._pending_ops.clear()
        km._pending_ops.update(self._saved[4])
        km._pane_io_locks.clear()
        super().tearDown()

    def _await(self, pred, timeout=10.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if pred():
                return True
            time.sleep(0.02)
        return pred()

    def _rows(self):
        return km._user_todos().get(SID) or []

    def test_a_refused_paste_reopens_the_stamped_answer(self):
        # end to end through the immediate path (_send_or_park → _backend_send → the real
        # TmuxBackend.send → the real clear against an unclearable pane): truthy send → stamp;
        # the paste thread then refuses; the ask must visibly return
        km._TMUX = _FakeTmuxPane(["a draft typed straight into the terminal"], honors_kill=False)
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        body = km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                         "Go with the session cookie.")
        got = km._send_or_park(self.be, SID, body, user_todo=tid)   # the drive handler's call…
        self.assertTrue(got, "fire-and-forget: the tmux send is truthy before any paste "
                             "(the truthy value is the send's nonce)")
        km._stamp_user_todo_answered(SID, tid, body, nonce=got)     # …and its stamp at the truthy send
        self.assertTrue(self._await(lambda: "resolved" not in self._rows()[0]),
                        "the clear-guard refusal is a loss event — the ask visibly returns")
        self.assertEqual(km._TMUX.pastes, [], "nothing was pasted onto the leftover (the guard held)")
        self.assertNotIn(("Enter",), km._TMUX.keys_sent, "and nothing was submitted")

    def test_a_clean_paste_keeps_the_stamp(self):
        # cards move on NEW information only: a send whose clear succeeded delivers, and the
        # reopen must never fire — the seam is armed by the refusal event, not by the send
        km._TMUX = _FakeTmuxPane(["an interrupt-restored prompt"])
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        body = km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                         "Go with the session cookie.")
        got = km._send_or_park(self.be, SID, body, user_todo=tid)
        self.assertTrue(got)
        km._stamp_user_todo_answered(SID, tid, body, nonce=got)
        self.assertTrue(self._await(lambda: ("Enter",) in km._TMUX.keys_sent),
                        "the paste completed and submitted")
        time.sleep(0.3)                              # a beat for any (wrong) reopen thread to land
        self.assertEqual(km._TMUX.buffers, [body])
        self.assertEqual(self._rows()[0]["resolved"]["kind"], "answered",
                         "delivered — the stamp stands")

    def test_a_plain_tmux_send_keeps_its_old_shape(self):
        # no id → no mark, no hooks armed, the same True it always returned
        km._TMUX = _FakeTmuxPane()
        self.assertIs(self.be.send(SID, "plain words"), True)
        self.assertTrue(self._await(lambda: ("Enter",) in km._TMUX.keys_sent))
        self.assertFalse((jd.STATE / "tmux-paste").exists(), "a plain send writes no mark")

    def test_a_refused_drain_reopens_every_answer_in_the_merged_batch(self):
        # the OTHER stamping caller (_deliver_send_batch): tmux merges a parked run into ONE
        # paste and stamps each answer on the truthy send — one refusal loses them all, so it
        # must reopen them all. The clear is gated so the test proves the ORDER the defect had:
        # stamps first, the refusal event later, and the reopen corrects the stamps.
        km._TMUX = _FakeTmuxPane()
        gate = threading.Event()
        saved_clear = km._clear_pane_input
        km._clear_pane_input = lambda name: bool(gate.wait(10)) and False
        self.addCleanup(setattr, km, "_clear_pane_input", saved_clear)
        tid1 = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        tid2 = km._add_user_todo(SID, "Need the staging port")
        b1 = km._user_todo_answer_body("Need the auth-scheme decision to wire login", "Cookie.")
        b2 = km._user_todo_answer_body("Need the staging port", "8443.")
        km._deliver_send_batch(self.be, SID, [("send", b1, None, tid1), ("send", b2, None, tid2)])
        self.assertEqual([r["resolved"]["kind"] for r in self._rows()], ["answered", "answered"],
                         "the drain stamped both at the truthy merged send")
        gate.set()                                   # NOW the clear-guard refuses the paste
        self.assertTrue(self._await(lambda: all("resolved" not in r for r in self._rows())),
                        "one refused paste = every answer it carried was lost — both asks return")
        self.assertEqual(km._TMUX.pastes, [])

    def test_a_death_between_clear_and_Enter_is_a_loss_event_too(self):
        # not just the refuse branch: any exception before Enter means the message never reached
        # the CLI — the hook fires on the way out, and the exception itself stays loud
        pane = _FakeTmuxPane()                       # empty box: the clear succeeds at once
        km._TMUX = pane

        def boom(text):
            raise RuntimeError("tmux died mid-send")

        pane.set_buffer = boom
        fired = []
        with self.assertRaises(RuntimeError):
            km._tmux_send("web", "the composer message", _async=False,
                          on_refused=lambda: fired.append(True))
        self.assertEqual(fired, [True])
        self.assertNotIn(("Enter",), pane.keys_sent)

    def test_the_hook_stays_quiet_when_the_paste_lands(self):
        pane = _FakeTmuxPane()
        km._TMUX = pane
        fired = []
        km._tmux_send("web", "the composer message", _async=False,
                      on_refused=lambda: fired.append(True))
        self.assertEqual(fired, [], "Enter landed — there is no loss to report")
        self.assertIn(("Enter",), pane.keys_sent)

    def test_backend_send_hands_the_id_to_a_refusal_reporting_backend(self):
        # the _forwards_sends-style capability probe: tmux has no queue entry to carry the id,
        # but its send watches for the refusal — the id must reach it. (A fake with NEITHER
        # capability still takes the plain two-argument send: RecallRidesTheEntry pins that.)
        seen = []

        class _RefusalBackend:
            send_reports_refusal = True

            def send(self, sid, text, user_todo=None):
                seen.append((sid, text, user_todo))
                return True

        km._backend_send(_RefusalBackend(), SID, "Re: Need the staging port — 8443.",
                         user_todo="ut-11111111")
        self.assertEqual(seen, [(SID, "Re: Need the staging port — 8443.", "ut-11111111")])

    # ── delivered means DELIVERED ──
    # The forgiving primitives swallow exec errors and ignore exit codes, so a tmux server that
    # died AFTER a successful clear makes set-buffer/paste-buffer/Enter silent no-ops; the three
    # steps that are the delivery read tmux's own exit code (dead server → 1 "no server running")
    # and any failure is a refusal like the clear-guard's — so the stamp cannot stand on a
    # message nothing received.

    def _stamped_send(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        body = km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                         "Go with the session cookie.")
        got = km._send_or_park(self.be, SID, body, user_todo=tid)
        self.assertTrue(got)
        km._stamp_user_todo_answered(SID, tid, body, nonce=got)
        return tid, body

    def test_a_dead_server_at_set_buffer_is_a_refusal_not_a_delivery(self):
        km._TMUX = _FakeTmuxPane(fail=("set_buffer",))       # empty box: the clear itself succeeds
        self._stamped_send()
        self.assertTrue(self._await(lambda: "resolved" not in self._rows()[0]),
                        "a failed set-buffer is NOT a delivery — the ask visibly returns")
        self.assertEqual(km._TMUX.buffers, [], "the dead server staged nothing")
        self.assertEqual(km._TMUX.pastes, [], "…and pasted nothing")

    def test_a_dead_server_at_paste_buffer_is_a_refusal_too(self):
        km._TMUX = _FakeTmuxPane(fail=("paste_buffer",))
        tid, body = self._stamped_send()
        self.assertTrue(self._await(lambda: "resolved" not in self._rows()[0]))
        self.assertEqual(km._TMUX.buffers, [body], "staged — but the paste never landed")
        self.assertNotIn(("Enter",), km._TMUX.keys_sent, "and nothing was submitted")

    def test_a_failed_submitting_Enter_is_a_refusal_even_after_a_clean_paste(self):
        # the latest possible silent no-op: staged AND pasted, but the Enter that would submit
        # exits nonzero — the message sits in a dead pane's input, which is not a delivery
        km._TMUX = _FakeTmuxPane(fail=("enter",))
        tid, body = self._stamped_send()
        self.assertTrue(self._await(lambda: "resolved" not in self._rows()[0]),
                        "pasted-but-never-submitted is a loss — the ask visibly returns")
        self.assertEqual(km._TMUX.buffers, [body])
        self.assertNotIn(("Enter",), km._TMUX.keys_sent)

    # ── the hook-exception contract ──

    def test_the_noop_early_return_arm_guards_a_throwing_hook(self):
        # the empty-name/empty-text arm fires on_refused SYNCHRONOUSLY on the caller's thread —
        # unguarded, a throwing hook would propagate into the caller, contradicting the
        # documented contract (stderr-logged, never raised). Unreachable with today's callers,
        # guarded anyway so the trap cannot arm.
        def boom():
            raise ValueError("hook boom")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._tmux_send("", "the composer message", _async=False, on_refused=boom)
            km._tmux_send("web", "", _async=False, on_refused=boom)
        self.assertEqual(err.getvalue().count("refusal hook failed"), 2,
                         "both empty arms log the hook's failure instead of raising it")

    def test_a_throwing_refusal_hook_is_logged_never_raised(self):
        # go()'s guarantee, pinned — the clear-guard refuses, the hook throws, and nothing
        # propagates (run sync so a raise would surface right here); the failure is SAID
        km._TMUX = _FakeTmuxPane(["a draft typed straight into the terminal"], honors_kill=False)

        def boom():
            raise ValueError("hook boom")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._tmux_send("web", "the composer message", _async=False, on_refused=boom)
        self.assertIn("refusal hook failed", err.getvalue())

    def test_a_throwing_hook_never_masks_the_pastes_own_exception(self):
        # the ORIGINAL death (set-buffer raising mid-send) stays the loud one — the hook's own
        # failure is logged, never swapped in for what propagates
        pane = _FakeTmuxPane()
        km._TMUX = pane

        def die(text):
            raise RuntimeError("tmux died mid-send")

        pane.set_buffer = die                        # the checked variant delegates → still raises

        def boom():
            raise ValueError("hook boom")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(RuntimeError):
                km._tmux_send("web", "the composer message", _async=False, on_refused=boom)
        self.assertIn("refusal hook failed", err.getvalue())

    def test_a_throwing_delivered_hook_is_logged_never_raised(self):
        # the verdict's other half keeps the same guard: a throwing on_delivered (the mark
        # clear) must never turn a delivered paste into a raise on the paste thread
        pane = _FakeTmuxPane(["an interrupt-restored prompt"])
        km._TMUX = pane

        def boom():
            raise ValueError("hook boom")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._tmux_send("web", "the composer message", _async=False, on_delivered=boom)
        self.assertIn("delivered hook failed", err.getvalue())
        self.assertIn(("Enter",), pane.keys_sent, "the paste itself completed")


class _TmuxPasteHarness(_StoreSandbox):
    """Shared rig for the pending-paste mark suites: the REAL TmuxBackend over a fake pane, the
    LostAnswerReopens transcript stubs (self.turns feeds the seam's landed check), and the
    mark-store readers/writers the assertions speak in. The seam's verdict lines are loud by
    design, so stderr is captured for the whole test."""

    def setUp(self):
        super().setUp()
        self._saved = (km._TMUX, km._sessions, km._parse, km._compacting_now,
                       dict(km._pending_ops))
        self.be = km._TMUX                 # the REAL backend: send → _tmux_send → the fake pane
        self.turns = []
        km._sessions = lambda now, window=None, forks=True: [{"sid": SID, "path": "/dev/null"}]
        km._parse = lambda path, sid, now: {"turns": self.turns}
        km._compacting_now = lambda sid, **k: False
        km._pending_ops.clear()
        km._pane_io_locks.clear()
        self.err = io.StringIO()
        self._err = contextlib.redirect_stderr(self.err)
        self._err.__enter__()

    def tearDown(self):
        self._err.__exit__(None, None, None)
        km._TMUX, km._sessions, km._parse, km._compacting_now = self._saved[:4]
        km._pending_ops.clear()
        km._pending_ops.update(self._saved[4])
        km._pane_io_locks.clear()
        super().tearDown()

    def _await(self, pred, timeout=10.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if pred():
                return True
            time.sleep(0.02)
        return pred()

    def _rows(self):
        return km._user_todos().get(SID) or []

    def _marks(self, sid=SID):
        return [(e["todo"], e["text"]) for e in self._raw_marks(sid)]

    def _raw_marks(self, sid=SID):
        try:
            d = json.loads((jd.STATE / "tmux-paste" / (sid + ".json")).read_text())
        except OSError:
            return []
        return list(d["pending"])

    def _mark_file(self, pending, sid=SID):
        d = jd.STATE / "tmux-paste"
        d.mkdir(parents=True, exist_ok=True)
        (d / (sid + ".json")).write_text(json.dumps({"sid": sid, "pending": pending}))

    def _stamped(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        km._stamp_user_todo_answered(SID, tid, body)
        return tid, body

    def _gate_clear(self, verdict):
        """Park the paste thread at the clear, so the test can look at the world while the
        verdict is pending; gate.set() releases it into `verdict` (True = clean, False = refuse)."""
        gate = threading.Event()
        saved = km._clear_pane_input
        km._clear_pane_input = lambda name: bool(gate.wait(10)) and verdict
        self.addCleanup(setattr, km, "_clear_pane_input", saved)
        return gate


class TmuxPendingPasteMarks(_TmuxPasteHarness):
    """The tmux refusal seam alone is process-lifetime-only. TmuxBackend.send returns truthy while
    the paste runs on a daemon thread, so a kernel death in the stamp→verdict window (0.3–4s)
    kills the thread pre-Enter: no refusal fires, and nothing persisted even RECORDS the attempt —
    the false 'answered' survives the restart, docs/adr/0001's silent-loss class, the exact window
    the SDK closes with persisted drop marks + _user_todo_loss_boot_pass. These pin the tmux twin:
    a pending-paste mark persists BEFORE the truthy send returns, the paste thread clears it on its
    verdict (delivered → clear; refused → the verdict is recorded on the store, THEN the clear),
    and _tmux_paste_loss_boot_pass re-offers any mark a dead kernel left to the same
    landed-check-then-reopen seam."""

    def test_the_mark_is_persisted_before_the_truthy_send_returns(self):
        # THE window: kernel death between the truthy send (whose caller stamps 'answered') and
        # the paste thread's verdict. The mark must already be on disk when send() returns —
        # written on the caller's thread, never the daemon's.
        km._TMUX = _FakeTmuxPane()
        gate = self._gate_clear(True)
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        got = self.be.send(SID, body, user_todo=tid)
        self.assertTrue(got, "truthy = accepted for delivery")
        self.assertEqual(got, self._raw_marks()[0].get("nonce"),
                         "…and the truthy value NAMES the send: it is the mark's nonce, for "
                         "the caller to thread into its stamp")
        self.assertEqual(self._marks(), [(tid, body)],
                         "the mark is on disk WHILE the verdict is pending — a kernel death "
                         "here leaves a record, not a silent false stamp")
        gate.set()
        self.assertTrue(self._await(lambda: self._marks() == []),
                        "a delivered paste clears its mark — the verdict's other half")

    def test_a_refusal_reopens_then_clears_the_mark(self):
        km._TMUX = _FakeTmuxPane(["a draft typed straight into the terminal"], honors_kill=False)
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        got = self.be.send(SID, body, user_todo=tid)
        self.assertTrue(got)
        km._stamp_user_todo_answered(SID, tid, body, nonce=got)
        self.assertTrue(self._await(lambda: "resolved" not in self._rows()[0]),
                        "the refusal reopened the ask")
        self.assertTrue(self._await(lambda: self._marks() == []),
                        "…and the mark cleared AFTER the reopen landed, not before")

    def test_the_drained_batch_marks_every_answer_with_the_merged_text(self):
        # one paste carries every answer in the run, so each mark keys on the MERGED text — the
        # text the paste delivers is what the boot pass's landed check must find in a transcript
        km._TMUX = _FakeTmuxPane()
        gate = self._gate_clear(False)
        tid1 = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        tid2 = km._add_user_todo(SID, "Need the staging port")
        b1 = km._user_todo_answer_body("Need the auth-scheme decision to wire login", "Cookie.")
        b2 = km._user_todo_answer_body("Need the staging port", "8443.")
        km._deliver_send_batch(self.be, SID, [("send", b1, None, tid1), ("send", b2, None, tid2)])
        merged = b1 + "\n\n" + b2
        self.assertEqual(self._marks(), [(tid1, merged), (tid2, merged)],
                         "both marks persisted before the truthy merged send, on the merged text")
        gate.set()                                   # NOW the clear-guard refuses the paste
        self.assertTrue(self._await(lambda: all("resolved" not in r for r in self._rows())),
                        "one refusal reopened every answer the paste carried")
        self.assertTrue(self._await(lambda: self._marks() == []),
                        "…and cleared every mark after the reopens landed")

    def test_a_stale_mark_at_boot_reopens_the_ask(self):
        # the two-boot shape: the send stamped 'answered', the kernel died before the paste's
        # verdict — nothing fired. The next boot's pass must treat the orphaned mark as a loss.
        tid, body = self._stamped()
        self._mark_file([{"todo": tid, "text": body, "t": 1}])
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 1)
        self.assertNotIn("resolved", self._rows()[0],
                         "the mark survived the death; the pass re-offered it and the ask "
                         "visibly returned")
        self.assertEqual(self._marks(), [], "consumed — but only after the seam ruled")

    def test_a_landed_answer_keeps_its_stamp_through_the_pass(self):
        # the benign shape: the kernel died between Enter and the mark's clear. The seam's
        # transcript check proves the delivery, so the stamp stands and only the mark goes.
        tid, body = self._stamped()
        self.turns = [{"atoms": [{"type": "user", "author": "human", "uuid": "u1",
                                  "message": {"role": "user",
                                              "content": [{"type": "text", "text": body}]}}]}]
        self._mark_file([{"todo": tid, "text": body, "t": 1}])
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 1)
        self.assertEqual(self._rows()[0]["resolved"]["kind"], "answered",
                         "landed = delivered; the stamp stands however many boots re-check it")
        self.assertEqual(self._marks(), [])

    def test_a_mark_whose_stamp_never_landed_is_swept_quietly(self):
        # the death beat the caller's stamp: the ask is still open, so there is nothing to
        # reopen — the pass offers nothing and consumes the stale mark
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        self._mark_file([{"todo": tid, "text": body, "t": 1}])
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0)
        self.assertNotIn("resolved", self._rows()[0], "still open — nothing to reopen")
        self.assertFalse((jd.STATE / "tmux-paste" / (SID + ".json")).exists(),
                         "…and the stale mark is swept")

    def test_a_missing_or_junk_marks_dir_is_a_quiet_zero(self):
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0, "no tmux-paste/ dir at all")
        (jd.STATE / "tmux-paste").mkdir(parents=True)
        (jd.STATE / "tmux-paste" / "junk.json").write_text("not json{")
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0)
        self.assertFalse((jd.STATE / "tmux-paste" / "junk.json").exists(),
                         "an unreadable mark file is consumed, not re-read every boot")

    def test_a_failed_mark_write_is_loud_never_silent(self):
        # without the mark the live seam still covers the common case, but a kernel death before
        # this paste's verdict would re-lose the answer — the failure must be SAID
        saved = km._atomic_write

        def refuse(path, text, mode=None):
            raise OSError("disk full")
        km._atomic_write = refuse
        self.addCleanup(setattr, km, "_atomic_write", saved)
        km._tmux_paste_mark(SID, [("ut-11111111", "Re: x — y", "1111aaaa")])
        self.assertIn("failed to persist", self.err.getvalue())
        self.assertIn("ut-11111111", self.err.getvalue())

    def test_the_pass_is_wired_into_main_before_any_backend_construction(self):
        # same ordering claim as the SDK sibling's: the marks must be read as the dead kernel
        # left them, before any of this boot's sends can write new ones
        src = inspect.getsource(km.main)
        i = src.index("_tmux_paste_loss_boot_pass")
        self.assertLess(i, src.index("_boot_warm()"),
                        "_boot_warm's _alive_sessions constructs the backend — the pass runs first")
        self.assertLess(i, src.index("target=_sdk"))

    # ── the landed check accepts the CLI's image rewrite ──
    # Claude Code reads each pasted image PATH and rewrites it in the input to "[Image #N]"
    # before submit — the very rewrite _tmux_send's pre-Enter wait exists for — so a DELIVERED
    # image-carrying answer appears in the transcript in the rewritten form. A landed check
    # keyed on the raw bytes alone would falsely reopen such an answer at every boot.

    def _turn_with(self, text):
        return [{"atoms": [{"type": "user", "author": "human", "uuid": "u1",
                            "message": {"role": "user",
                                        "content": [{"type": "text", "text": text}]}}]}]

    def test_a_delivered_image_paste_keeps_its_stamp_at_boot(self):
        ask = "Need the failing form state"
        tid = km._add_user_todo(SID, ask)
        body = km._user_todo_answer_body(ask, "See /tmp/staging-form.png — the port field is blank.")
        km._stamp_user_todo_answered(SID, tid, body)
        self.turns = self._turn_with(body.replace("/tmp/staging-form.png", "[Image #1]"))
        self._mark_file([{"todo": tid, "text": body, "t": 1}])
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 1)
        self.assertEqual(self._rows()[0]["resolved"]["kind"], "answered",
                         "the rewritten form IS the delivery — the stamp stands")
        self.assertEqual(self._marks(), [])

    def test_the_rewrite_numbers_every_image_in_order(self):
        ask = "Need the failing form state"
        tid = km._add_user_todo(SID, ask)
        body = km._user_todo_answer_body(ask, "Before: /tmp/form-empty.png after: /tmp/form-filled.png done.")
        km._stamp_user_todo_answered(SID, tid, body)
        rew = body.replace("/tmp/form-empty.png", "[Image #1]").replace("/tmp/form-filled.png",
                                                                        "[Image #2]")
        self.turns = self._turn_with(rew)
        self._mark_file([{"todo": tid, "text": body, "t": 1}])
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 1)
        self.assertEqual(self._rows()[0]["resolved"]["kind"], "answered")

    def test_the_rewritten_match_stays_exact_never_substring(self):
        # the check's own contract holds for the new form too: the rewritten text EMBEDDED in a
        # longer message is somebody quoting it, not this paste's delivery — the ask reopens
        ask = "Need the failing form state"
        tid = km._add_user_todo(SID, ask)
        body = km._user_todo_answer_body(ask, "See /tmp/staging-form.png — the port field is blank.")
        km._stamp_user_todo_answered(SID, tid, body)
        rew = body.replace("/tmp/staging-form.png", "[Image #1]")
        self.turns = self._turn_with("Quoting what I never received: " + rew)
        self._mark_file([{"todo": tid, "text": body, "t": 1}])
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 1)
        self.assertNotIn("resolved", self._rows()[0], "an embedded match is not a delivery")

    def test_the_landed_forms_are_the_raw_and_rewritten_texts_only(self):
        forms = km._paste_landed_texts("See /tmp/a.png then /tmp/b.png\n")
        self.assertEqual(forms, {"See /tmp/a.png then /tmp/b.png",
                                 "See [Image #1] then [Image #2]"})
        self.assertEqual(km._paste_landed_texts("  plain words  "), {"plain words"})

    # ── the boot pass consumes what it DISCOVERED ──
    # Discovery is by glob, but a consume that re-derived the path from the EMBEDDED sid field
    # would let a file whose two identities disagree be re-read (and possibly re-acted-on) every
    # boot, forever — and a directory named *.json survive silently just as long.

    def test_a_mark_whose_embedded_sid_disagrees_is_consumed_loudly(self):
        d = jd.STATE / "tmux-paste"
        d.mkdir(parents=True, exist_ok=True)
        p = d / (SID + ".json")
        p.write_text(json.dumps({"sid": SID2,
                                 "pending": [{"todo": "ut-11111111", "text": "Re: x — y", "t": 1}]}))
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0,
                         "a mark whose identities disagree is never acted on")
        self.assertFalse(p.exists(),
                         "consumed by the path it was DISCOVERED at — never re-read next boot")
        self.assertNotEqual(self.err.getvalue(), "", "…and refused loudly, never silently")

    def test_a_directory_in_the_marks_store_is_loud_never_silent(self):
        d = jd.STATE / "tmux-paste"
        (d / "not-a-mark.json").mkdir(parents=True)
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0)
        self.assertNotEqual(self.err.getvalue(), "",
                            "a directory named *.json is announced, not skipped silently")
        self.assertTrue((d / "not-a-mark.json").is_dir(), "…and left for a human, never rmtree'd")

    def test_an_unconsumable_mark_is_loud_never_silent(self):
        if os.geteuid() == 0:
            self.skipTest("root ignores directory write bits — the unlink cannot be made to fail")
        d = jd.STATE / "tmux-paste"
        d.mkdir(parents=True)
        (d / (SID + ".json")).write_text("not json{")
        os.chmod(d, 0o555)                           # the unlink now fails: EACCES on the dir
        try:
            self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0)
            self.assertNotEqual(self.err.getvalue(), "",
                                "an unlinkable mark is announced — it WILL be re-read next boot")
        finally:
            os.chmod(d, 0o755)


class TmuxStampStandDown(_TmuxPasteHarness):
    """One defect, two lenses: the refusal can OUTRUN the caller's 'answered' stamp (a dead tmux
    server fails the clear-guard's first capture in milliseconds while the stamp queues on
    _user_todos_lock), and a refusal hook that unconditionally unmarked would forfeit the healing
    record — the seam's reopen no-ops (no 'answered' row yet), the mark is consumed anyway, and
    the late stamp stands forever, unhealable even at boot. The fix is the repo's own doctrine at
    the write moment: the stamp's evidence is the truthy send; the refusal verdict is NEWER
    information; the stamp yields. Mechanism: the seam reports its verdict, an open-row refusal
    flips the mark to refused (never consumes it), and _stamp_user_todo_answered checks the mark
    store under the same lock before stamping — a refused mark stands the stamp down, records the
    loss, and consumes the mark itself. Ordering is proven by gating the stamp on the refusal
    verdict being RECORDED — an event, never a sleep."""

    def _verdict_recorded(self):
        # the refusal's verdict has reached the store: the mark was consumed (the old,
        # record-forfeiting shape) or flagged refused (the healing record)
        raw = self._raw_marks()
        return raw == [] or all(e.get("refused") for e in raw)

    def test_a_refusal_that_outruns_the_stamp_stands_it_down(self):
        km._TMUX = _FakeTmuxPane(["a draft typed straight into the terminal"], honors_kill=False)
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        got = self.be.send(SID, body, user_todo=tid)         # truthy return = this send's nonce
        self.assertTrue(got)
        self.assertTrue(self._await(self._verdict_recorded),
                        "the refusal ruled first — provably, before the stamp below lands")
        km._stamp_user_todo_answered(SID, tid, body, nonce=got)   # the late stamp lands…
        self.assertNotIn("resolved", self._rows()[0],
                         "…and stands down: the refusal verdict is newer information than the "
                         "truthy send the stamp is acting on")
        self.assertEqual(self._marks(), [], "the stand-down consumed the refused mark itself")
        self.assertIn("stand", self.err.getvalue(), "a stood-down stamp is said out loud")
        # healed for good, not parked for a boot: the next pass has nothing to re-offer and the
        # ask is still visibly waiting on the user
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0)
        self.assertNotIn("resolved", self._rows()[0])

    def test_a_refusal_that_outruns_the_batch_stamps_stands_them_all_down(self):
        # the other stamping caller: _deliver_send_batch stamps every answer after the truthy
        # merged send — the descheduled-caller interleaving, made deterministic by gating each
        # stamp on the batch refusal's verdict being recorded
        km._TMUX = _FakeTmuxPane(["a draft typed straight into the terminal"], honors_kill=False)
        real = km._stamp_user_todo_answered

        def gated(sid, tid, text, *a, **kw):
            self.assertTrue(self._await(self._verdict_recorded),
                            "the batch refusal ruled before this stamp")
            return real(sid, tid, text, *a, **kw)
        km._stamp_user_todo_answered = gated
        self.addCleanup(setattr, km, "_stamp_user_todo_answered", real)
        tid1 = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        tid2 = km._add_user_todo(SID, "Need the staging port")
        b1 = km._user_todo_answer_body("Need the auth-scheme decision to wire login", "Cookie.")
        b2 = km._user_todo_answer_body("Need the staging port", "8443.")
        km._deliver_send_batch(self.be, SID, [("send", b1, None, tid1),
                                              ("send", b2, None, tid2)])
        self.assertTrue(all("resolved" not in r for r in self._rows()),
                        "every late stamp stood down — both asks still wait on the user")
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0)
        self.assertTrue(all("resolved" not in r for r in self._rows()))

    def test_a_refused_flag_that_never_met_its_stamp_is_swept_quietly_at_boot(self):
        # the kernel died between the flip and the stamp: the row is OPEN (nothing was ever
        # stamped) and the refused mark has nothing left to heal — consumed, no re-offer
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        self._mark_file([{"todo": tid, "text": body, "t": 1, "refused": True}])
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0)
        self.assertNotIn("resolved", self._rows()[0], "still open — exactly as the refusal left it")
        self.assertFalse((jd.STATE / "tmux-paste" / (SID + ".json")).exists())

    def test_a_refused_flag_beside_an_answered_row_reopens_at_boot(self):
        # defense in depth: a stamp that somehow landed anyway (a version-skewed kernel, a
        # by-hand store edit) reads exactly like a stale mark — the seam rules, the ask reopens
        tid, body = self._stamped()
        self._mark_file([{"todo": tid, "text": body, "t": 1, "refused": True}])
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 1)
        self.assertNotIn("resolved", self._rows()[0])
        self.assertEqual(self._marks(), [])

    def test_check_and_stamp_are_one_critical_section(self):
        # the stand-down read and the stamp must not straddle a lock release: a refusal that
        # lands in the gap would be orphaned until the next boot. Pinned structurally — the
        # consume runs inside the `with _user_todos_lock:` block that decides the stamp.
        src = inspect.getsource(km._stamp_user_todo_answered)
        body = src[src.index("with _user_todos_lock:"):]
        block = body.split("\n")
        indent = len(block[1]) - len(block[1].lstrip())
        inside = []
        for line in block[1:]:
            if line.strip() and (len(line) - len(line.lstrip())) < indent:
                break
            inside.append(line)
        inside = "\n".join(inside)
        self.assertIn("_tmux_paste_consume_refused(", inside)
        self.assertIn('_resolve_user_todo(sid, tid, "answered")', inside)


class SeamOrderPins(_TmuxPasteHarness):
    """The load-bearing orderings — a refusal's clear follows its verdict; the boot pass consumes
    only after the seam rules — would be asserted only via end states that are identical under
    inverted order, so swapping the calls would pass the suite. The unmark is data-DEPENDENT on
    the seam's verdict (structural enforcement); these pin the observed sequence itself, for all
    three callers."""

    def _recorded(self):
        calls = []
        real_lost = km._user_todo_answer_lost
        real_unmark = km._tmux_paste_unmark

        def lost(sid, tid, text, wait=False, nonce=None):
            got = real_lost(sid, tid, text, wait=wait, nonce=nonce)
            calls.append(("ruled", tid))             # appended AFTER the seam returns…
            return got

        def unmark(sid, entries, path=None):
            if entries:                              # an empty call is the no-op sweep, no verdict rides it
                calls.append(("unmark", tuple(t for t, _ in entries)))   # …and BEFORE any consume
            return real_unmark(sid, entries, path=path)
        km._user_todo_answer_lost = lost
        km._tmux_paste_unmark = unmark
        self.addCleanup(setattr, km, "_user_todo_answer_lost", real_lost)
        self.addCleanup(setattr, km, "_tmux_paste_unmark", real_unmark)
        return calls

    def test_the_single_send_hook_rules_before_it_consumes(self):
        calls = self._recorded()
        km._TMUX = _FakeTmuxPane(["a draft typed straight into the terminal"], honors_kill=False)
        tid, body = self._stamped()                  # stamped FIRST: the refusal finds the row
        self.assertTrue(self.be.send(SID, body, user_todo=tid))
        self.assertTrue(self._await(lambda: self._marks() == []))
        self.assertEqual(calls, [("ruled", tid), ("unmark", (tid,))],
                         "the seam ruled to completion before the mark was touched")

    def test_the_batch_hook_rules_every_answer_before_it_consumes(self):
        calls = self._recorded()
        km._TMUX = _FakeTmuxPane()
        gate = self._gate_clear(False)
        tid1 = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        tid2 = km._add_user_todo(SID, "Need the staging port")
        b1 = km._user_todo_answer_body("Need the auth-scheme decision to wire login", "Cookie.")
        b2 = km._user_todo_answer_body("Need the staging port", "8443.")
        km._deliver_send_batch(self.be, SID, [("send", b1, None, tid1), ("send", b2, None, tid2)])
        gate.set()                                   # stamps are in; NOW the clear-guard refuses
        self.assertTrue(self._await(lambda: self._marks() == []))
        self.assertEqual(calls, [("ruled", tid1), ("ruled", tid2), ("unmark", (tid1, tid2))],
                         "every answer was ruled on before the batch's marks were consumed")

    def test_the_boot_pass_rules_before_it_consumes(self):
        calls = self._recorded()
        tid, body = self._stamped()
        self._mark_file([{"todo": tid, "text": body, "t": 1}])
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 1)
        self.assertEqual(calls, [("ruled", tid), ("unmark", (tid,))],
                         "the seam ruled first; the discovered mark was consumed after")


class TmuxBatchDuplicateAnswers(_TmuxPasteHarness):
    """A drained batch can carry TWO parked answers for the SAME todo — the stamp is
    delivery-keyed, so the row stays open until the drain, and a second dashboard's answer (or a
    re-answer) legitimately parks a second op for the same id. The merged paste is ONE delivery
    event per todo; accounting that ran PER OP failed in both orderings:
    - refusal outruns the stamps: the seam's 'open' verdict flips BOTH mark entries refused, the
      first stamp's stand-down consumes them ALL, and the second stamp lands a permanent false
      'answered' with the mark store empty — nothing for boot to heal (the ADR fatal class);
    - stamps land first: the seam rules the same tid twice ('reopened', then 'open' on the
      just-reopened row), flips the surviving entry refused, and the single-instance unmark
      strands it on disk — where it falsely stands down the NEXT delivered answer's stamp.
    The fix, two coordinated pieces: (1) unique-tid accounting through the batch seam — one
    mark, one seam ruling, one stamp per unique todo, while every parked body still rides the
    merged paste; (2) every mark carries a send NONCE, the refusal verdict flips by it, and the
    stamp's stand-down consumes only the mark OF THE SEND IT PRESENTED — a stale flag from any
    earlier send can never eat a delivered answer's stamp, and dies at the boot split instead."""

    ASK = "Need the staging port"

    def _dup_run(self):
        tid = km._add_user_todo(SID, self.ASK)
        body = km._user_todo_answer_body(self.ASK, "8443.")
        return tid, body, [("send", body, None, tid), ("send", body, None, tid)]

    def test_a_refusal_that_outruns_a_duplicate_answer_batch_never_stamps_answered(self):
        # ordering 1: the clear-guard refuses on the paste thread while both stamps are still
        # pending — deterministic via gating each stamp on the refusal verdict being RECORDED in
        # the mark store (an event, never a sleep)
        km._TMUX = _FakeTmuxPane(["a draft typed straight into the terminal"], honors_kill=False)

        def _verdict_recorded():
            raw = self._raw_marks()
            return raw == [] or all(e.get("refused") for e in raw)
        real = km._stamp_user_todo_answered

        def gated(sid, tid, text, *a, **kw):
            self.assertTrue(self._await(_verdict_recorded),
                            "the batch refusal ruled before this stamp — the outrun ordering")
            return real(sid, tid, text, *a, **kw)
        km._stamp_user_todo_answered = gated
        self.addCleanup(setattr, km, "_stamp_user_todo_answered", real)
        tid, body, run = self._dup_run()
        km._deliver_send_batch(self.be, SID, run)
        self.assertNotIn("resolved", self._rows()[0],
                         "one delivery event, one stamp, stood down on the refusal — a "
                         "duplicate op must never land a second, false 'answered'")
        self.assertEqual(self._marks(), [], "the stand-down consumed its own send's mark")
        self.assertIn("stand", self.err.getvalue(), "the stood-down stamp is said out loud")
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0)
        self.assertNotIn("resolved", self._rows()[0], "healed for good — not parked for a boot")

    def test_a_refusal_after_duplicate_stamps_strands_no_flag(self):
        # ordering 2: stamps land first, the refusal rules after — the seam must rule the tid
        # ONCE, unmark its one mark, and leave nothing refused on disk
        km._TMUX = _FakeTmuxPane()
        gate = self._gate_clear(False)
        tid, body, run = self._dup_run()
        km._deliver_send_batch(self.be, SID, run)
        merged = body + "\n\n" + body
        self.assertEqual(self._marks(), [(tid, merged)],
                         "one delivery event per todo = ONE mark, on the merged text")
        self.assertEqual(self._rows()[0]["resolved"]["kind"], "answered",
                         "the stamps landed first — the normal ordering")
        gate.set()                                   # NOW the clear-guard refuses the paste
        self.assertTrue(self._await(lambda: self._raw_marks() == []
                                    and "resolved" not in self._rows()[0]),
                        "the refusal reopened the ask and consumed the one mark — a "
                        "stranded refused entry would stand down the NEXT delivered answer")
        # the user re-answers the reopened ask; this time the paste delivers, and the stamp
        # (presenting its own send's nonce — or none: nothing refused remains either way) LANDS
        body2 = km._user_todo_answer_body(self.ASK, "8444 actually.")
        km._stamp_user_todo_answered(SID, tid, body2)
        self.assertEqual((self._rows()[0].get("resolved") or {}).get("kind"), "answered",
                         "the delivered re-answer's stamp lands — nothing stale stands it down")

    def test_a_delivered_duplicate_batch_carries_both_bodies_and_stamps_once(self):
        # delivery semantics unchanged by the unique-tid accounting: BOTH parked bodies still
        # ride the one merged paste; the one stamp records them as one answer
        km._TMUX = _FakeTmuxPane()
        gate = self._gate_clear(True)
        tid = km._add_user_todo(SID, self.ASK)
        b1 = km._user_todo_answer_body(self.ASK, "8443.")
        b2 = km._user_todo_answer_body(self.ASK, "8444 actually — checked twice.")
        km._deliver_send_batch(self.be, SID, [("send", b1, None, tid),
                                              ("send", b2, None, tid)])
        merged = b1 + "\n\n" + b2
        self.assertEqual(self._marks(), [(tid, merged)],
                         "one mark per unique todo, keyed on the merged text")
        self.assertEqual(self._rows()[0]["resolved"]["kind"], "answered")
        gate.set()                                   # the paste delivers
        self.assertTrue(self._await(lambda: km._TMUX.buffers == [merged]),
                        "never drop a parked body: both answers rode the one paste")
        self.assertTrue(self._await(lambda: self._marks() == []),
                        "…and the delivered verdict cleared the one mark")

    def test_the_refusal_flips_only_its_own_sends_mark(self):
        # piece 2's write half: the verdict names the paste it ruled on — a sibling send's
        # pending mark for the same todo keeps its own verdict open
        tid = km._add_user_todo(SID, self.ASK)
        body = km._user_todo_answer_body(self.ASK, "8443.")
        self._mark_file([{"todo": tid, "text": body, "t": 1, "nonce": "1111aaaa"},
                         {"todo": tid, "text": body, "t": 2, "nonce": "2222bbbb"}])
        km._tmux_paste_flag_refused(SID, tid, nonce="1111aaaa")
        self.assertEqual([bool(e.get("refused")) for e in self._raw_marks()], [True, False])

    def test_a_stale_flag_from_an_earlier_send_never_stands_down_a_delivered_stamp(self):
        # piece 2's read half, pinned directly: a refused flag stranded by an EARLIER send
        # cannot eat a later delivered answer's stamp — the stamp presents its own nonce, the
        # flag names a different send, the stamp lands, and the leftover dies at the boot split
        tid = km._add_user_todo(SID, self.ASK)
        old = km._user_todo_answer_body(self.ASK, "8443.")
        self._mark_file([{"todo": tid, "text": old, "t": 1, "refused": True,
                          "nonce": "1111aaaa"}])
        body2 = km._user_todo_answer_body(self.ASK, "8444 actually.")
        km._stamp_user_todo_answered(SID, tid, body2, nonce="2222bbbb")
        self.assertEqual(self._rows()[0]["resolved"]["kind"], "answered",
                         "the flag rode an earlier send — this delivered stamp lands")
        self.assertEqual(len(self._raw_marks()), 1,
                         "…and the stale flag stays for the boot split, unconsumed")
        # the boot split still rules with nonces riding the entries: refused beside an
        # 'answered' row → the seam rules (nothing landed) → reopen, mark consumed
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 1)
        self.assertNotIn("resolved", self._rows()[0])
        self.assertEqual(self._marks(), [])

    def test_a_nonceless_stamp_still_yields_to_any_refusal_on_its_todo(self):
        # fail toward the visible ask: a stamp that cannot name its send (no nonce) yields to
        # ANY refusal recorded for the todo — the conservative default
        tid = km._add_user_todo(SID, self.ASK)
        body = km._user_todo_answer_body(self.ASK, "8443.")
        self._mark_file([{"todo": tid, "text": body, "t": 1, "refused": True,
                          "nonce": "1111aaaa"}])
        km._stamp_user_todo_answered(SID, tid, body)
        self.assertNotIn("resolved", self._rows()[0])
        self.assertEqual(self._marks(), [], "the stand-down consumed the refused entry")

    def test_a_row_reopened_between_the_boot_check_and_the_offer_strands_no_usable_flag(self):
        # the boot pass's threaded-offer variant (wait=False): the row can flip answered→open
        # between the loop's answered filter and the offer thread's seam run, whose 'open'
        # verdict then flags the mark refused and leaves it (correctly) unconsumed.
        # Deterministic stand-in for the interleaving: lift the stamp just before the seam
        # rules. The flag carries ITS send's nonce, so a later delivered answer still stamps.
        tid, body = self._stamped()
        self._mark_file([{"todo": tid, "text": body, "t": 1, "nonce": "1111aaaa"}])
        real = km._user_todo_answer_lost

        def raced(sid, t, text, *a, **kw):
            km._reopen_user_todo(sid, t)             # the interleaved writer wins the gap
            return real(sid, t, text, *a, **kw)
        km._user_todo_answer_lost = raced
        self.addCleanup(setattr, km, "_user_todo_answer_lost", real)
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 1)
        self.assertEqual([(e["todo"], bool(e.get("refused")), e.get("nonce"))
                          for e in self._raw_marks()],
                         [(tid, True, "1111aaaa")],
                         "the 'open' verdict flagged the mark it ruled on, nonce intact")
        body2 = km._user_todo_answer_body("Need the staging port", "8444 actually.")
        km._stamp_user_todo_answered(SID, tid, body2, nonce="2222bbbb")
        self.assertEqual((self._rows()[0].get("resolved") or {}).get("kind"), "answered",
                         "the stranded flag names the dead send — the delivered stamp lands")


class MarkerNeutralizerVariants(unittest.TestCase):
    """Every downstream matcher tolerates arbitrary whitespace after the comment opener
    (\"<!--\\s*romp-\"), so the neutralizer must break that same CLASS, not the one literal
    one-space spelling — a no-space \"<!--romp-injected-->\" in todo text would sail through and
    the user's own answer would render as romp's system card. tests/test_marker_neutralizer.py
    holds the generic probes; these cover the answer body's two halves, against the VERBATIM
    downstream regexes, imported, never copied."""

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
            self.assertTrue(rex.search(raw),
                            "sanity: %r must be marker-shaped for /%s/" % (raw, rex.pattern))
            body = km._user_todo_answer_body("Need a call on %s in the fixture" % raw,
                                             "Keep it, but drop the %s part." % raw)
            self.assertFalse(rex.search(body),
                             "an answer body carrying %r still matches /%s/" % (raw, rex.pattern))

    def test_the_bare_goal_id_form_breaks_in_both_todo_bodies(self):
        # the bare "romp-goal-id:" form needs no comment opener, and per the follow-up contract
        # it would REOPEN the named goal — todo text and replies are agent/user-supplied, so a
        # quoted id in either half must not fire the judge's FOLLOWUP_RE or the kernel's twin
        raw = "wrap up romp-goal-id: g-12 first"
        for rex in (km.jd.FOLLOWUP_RE, km._FOLLOWUP_GOAL_RE):
            self.assertTrue(rex.search(raw),
                            "sanity: %r must be marker-shaped for /%s/" % (raw, rex.pattern))
            body = km._user_todo_answer_body("Need a call on %s" % raw, "Do %s after." % raw)
            self.assertFalse(rex.search(body),
                             "an answer body carrying %r still matches /%s/" % (raw, rex.pattern))


class NoJudgeWritesTheStore(unittest.TestCase):
    """The authority tier, grep-provable (docs/adr/0001): nothing in judge.py names the store or
    its helpers — every eraser in the three holes acts by inference, and this object exists to
    survive inference. The token list is DERIVED from the kernel source (every module-level def
    whose name says user_todo — writers and readers alike), so a helper added tomorrow is
    covered the day it is written; the literal floor below keeps the derivation honest against
    a pattern drift that would quietly match nothing."""

    # every store writer that exists today — the derivation must still see each of these,
    # or the regex broke and the pin is scanning an empty list
    _KNOWN_WRITERS = ("_add_user_todo", "_resolve_user_todo", "_reopen_user_todo",
                      "_stamp_user_todo_answered", "_user_todo_answer_lost",
                      "_user_todo_loss_boot_pass", "_write_user_todos")

    def test_judge_py_never_touches_user_todos(self):
        kdir = Path(HERE).parent / "kernel"
        src = (kdir / "judge.py").read_text()
        tokens = set(re.findall(r"^def (\w*user_todo\w*)\(",
                                (kdir / "kernel.py").read_text(), re.M))
        for w in self._KNOWN_WRITERS:
            self.assertIn(w, tokens, "the derivation no longer sees %s — fix the pattern, "
                                     "never the floor" % w)
        # the store file itself, plus the bare prefix that covers the reader/cache/lock names
        tokens |= {"user-todos.json", "_user_todos"}
        for token in sorted(tokens):
            self.assertNotIn(token, src)


if __name__ == "__main__":
    unittest.main()
