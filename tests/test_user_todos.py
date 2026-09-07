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
- resolved rows are size-capped per sid while open rows never are (ResolvedRowsAreBounded);
- the authority tier as a grep-provable pin: judge.py never names the store or its helpers
  (NoJudgeWritesTheStore).

SYNTHETIC fixtures only: placeholder UUIDs, the notes-api demo world.
"""
import inspect
import io
import json
import os
import re
import tempfile
import threading
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
                      "_write_user_todos")

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
