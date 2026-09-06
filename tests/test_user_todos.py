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
- the DELIVERY-KEYED answer stamp (docs/adr/0001's fatal class): sent now → stamped on a truthy
  backend send; parked → the op carries the todo id and stamps at the drain; recalled (parked ✕
  or backend unqueue) or dropped (dead-session queue) → the todo stays/returns OPEN;
- the POST routes (/usertodo, /usertodo/withdraw) incl. route auth, driven over the fake-socket
  harness (the auth-hardening idiom: ask the real dispatcher, don't pin source positions), and
  the ack-fast contract: the reply never waits behind a synchronous every-session build;
- build_session's `userTodos` field + the split-card `todo` event that carries the rows (the
  chatTail wire re-sends changed EVENTS only, so the rows must ride the event), clock-invariant
  per the serialized-payload dedup rule — and _send_chat's chatTail frame carrying the field;
- the ended gate for BOTH backends (SDK registry alive:false; a reg-less tmux sid's durable
  death record, superseded by newer states evidence — never a raw listing miss) — hidden, not
  cleared, and the answer op refuses loudly instead of sending into the void;
- the per-sid chat-build-sig fold (a todo write busts the owning session's cache only);
- the two drive ops (userTodoAnswer / userTodoDismiss), the injected answer body's shape, and
  its marker hygiene (a "<!-- romp-…" lookalike in either half is neutralized);
- the round-2 wave (2026-08-22): the recall reads the todo id off the QUEUE ENTRY itself (no
  kernel-side table to restart away or evict — RecallRidesTheEntry), a restart-lost answer's
  drop-marked echo reopens its ask through _user_todo_answer_lost unless the transcript proves
  it landed (LostAnswerReopens), the neutralizer breaks the whole "<!--\\s*romp-" class the
  downstream matchers accept (MarkerNeutralizerVariants, verbatim regex imports), and resolved
  rows are size-capped per sid while open rows never are (ResolvedRowsAreBounded);
- the round-3 wave (2026-08-22): a mark-then-die kernel death no longer strands the ask —
  every boot re-derives pending losses from the persisted regs and re-offers them to the same
  seam (LossBootPass); the landed check resolves its transcript through discover's cached WIDE
  walk, so a >48h-idle session no longer skips it silently, and a genuinely transcript-less
  check logs the skip before reopening (in LostAnswerReopens); and a loss-path reopen that
  finds no 'answered' row is loud, matching the recall path (in LostAnswerReopens);
- SLICE 2 (ambient visibility and the endgame): build_feed's sid-keyed open-count map behind
  the ended/muted gates + the feed-cache sig watch (FeedSeamUserTodos); the idle-escalation floor's
  arming predicate with the no-flap pin (EscalationFloorPredicate) and its perm_top-family
  wiring incl. the goal-less placeholder (EscalationFloorWiring); the widened app badge and its
  no-double-count rule (BadgeArithmetic); the auto-nudge stand-down (NudgeStandsDownForOpenTodos).
  The tab glyph / feed marker pins live in the node suites (tab-usertodo.test.ts,
  feed-user-todos.test.ts);
- the slice-2 review wave (2026-08-22): the nudge stand-down is scoped to the STATUS-NUDGE
  branch alone — the awaiting wake and the debt machinery flow past it
  (NudgeStandsDownForOpenTodos); the floor's predicate gains the peer-wait input (waiting on a
  live peer is deliberately not needs-you; in EscalationFloorPredicate); the floored card's OS
  push is deduplicated on the floored todo SET, never re-fired by the card's own designed
  Working dips (FloorNotificationDedup); one session shows ONE interrupt story — the goal-less
  placeholder yields to any floored/blocked card and the todo-floored card suppresses the
  provisional Working placeholder (OneInterruptStory); the badge counts per-ITEM decision
  classes (quarantine, parked handoffs) per card (in BadgeArithmetic); the focus-chain miss
  falls back to a still-working top (in OneInterruptStory); and the muted-session asymmetry —
  tab glyph shows, feed aggregates quiet — is pinned as designed (in BuildSessionSeam);
- the round-2 verification wave (2026-08-22), all in the classes above: the notification
  baseline SEEDS the floor-push latch from the already-floored world, so a restart's first
  dip+re-entry is not news; a LOST answer's reopen clears its id from the latch (the re-floor
  is the one signal the answer never arrived) while the user's own ✕ recall stays silent; the
  floored todo-set diff runs independent of the column transition, so an id joining with no
  observed dip still pushes (FloorNotificationDedup); the focus walk and the working-top
  fallback both skip done-CONFIRMING tops — the settle gate's cards, flooring them flaps
  (OneInterruptStory); and the peer-wait gate's local-host-only scope is pinned as a documented
  limitation shared with the waitingOn chip (PeerWaitScopeIsLocalOnly);
- SLICE 3 (memory across context loss): the rendered context block — nothing at zero todos,
  newest-first with the capped "…and N more" tail, marker hygiene, the deliberate absence of a
  liveness re-check (ContextBlock) — and its read-only, token-gated POST /usertodo/context leg
  (ContextRoute). The hook that carries it into a session is bats-covered
  (romp-usertodo-context.bats); the words themselves are voice-scanned in test_injected_voice.py.

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
from unittest import mock
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
em = SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_SERVE_TOKEN"] = "testtok"
km = SourceFileLoader("romp_kernel_ut", os.path.join(BIN, "romp-kernel")).load_module()
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
        km._user_todos_bad.clear()
        km._set_user_todos(True)                     # the feature switch is OFF by default (2026-09-03);
        #                                              these suites pin the ON behavior — the OFF side
        #                                              lives in test_user_todos_switch.py

    def tearDown(self):
        jd.STATE = self.saved
        self.td.cleanup()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()


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
            # the lock is re-entrant since the stamp stand-down (round 3, 2026-08-27), and an
            # RLock has no .locked() on 3.12 — _is_owned() is the sharper predicate anyway:
            # every mutation publishes on the thread that took the lock, so "the CALLING thread
            # holds it" is exactly the claim, where .locked() would settle for "someone does"
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
        # the R1 shape, bounded: two threads (two postal buses' route threads) register in
        # parallel; every row postal confirmed must be in the file afterwards
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
        # the R2 shape, bounded: whatever the schedule, exactly ONE clearing event wins and the
        # surviving stamp is the winner's — the loser is told loudly (False)
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


class PruneSweep(_StoreSandbox):
    """The sweep keys on the rows' own corroborated evidence — resolved AND a durable death
    record — NEVER on a display/known-set: the tab-GC's set drops alive-but-idle tmux sessions
    during list-collapse cycles and 48h transcript ageouts, and the first cut deleted a LIVE
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

    def test_the_sweep_still_rides_the_tab_session_pass_but_not_its_known_set(self):
        # wired where the old sweep was — one call per pusher pass — but keyed on its own
        # corroborated evidence, never the display set the tab-GC prunes by
        src = inspect.getsource(km._chat_tab_sessions)
        self.assertIn("_prune_user_todos()", src)


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
        self.assertEqual(self._post("/usertodo", {"text": "no sid"})[0], 400)
        code, _ = _serve_post("/usertodo", b"not json", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400)

    def test_withdraw_requires_the_serve_token(self):
        code, _ = self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-deadbeef"}, token=False)
        self.assertEqual(code, 403)

    def test_withdraw_stamps_withdrawn(self):
        _, res = self._post("/usertodo", {"id": SID, "text": "Need the fixture format pick"})
        code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        self.assertEqual(code, 200)
        self.assertTrue(out["ok"])
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "withdrawn")

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


class ContextBlock(_StoreSandbox):
    """SLICE 3 (memory across context loss, plans/user-todos.md): _user_todo_context_block renders
    a session's OPEN todos as the agent's OWN outstanding notes to the person it works for — the
    passive block the SessionStart hook (hooks/romp-usertodo-context.sh) injects on the resume and
    compact sources, so an agent whose working memory was wiped remembers what it asked for and
    can withdraw the moot ones. Voice-scanned by test_injected_voice.py."""

    def _seed(self, rows, sid=SID):
        (jd.STATE / "user-todos.json").write_text(json.dumps({sid: rows}))
        km._user_todos_cache.clear()

    def test_no_open_todos_mean_no_block_at_all(self):
        # a zero-todo session gets NOTHING — no noise (the spec's no-noise rule)
        self.assertEqual(km._user_todo_context_block(SID), "")
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "withdrawn")
        self.assertEqual(km._user_todo_context_block(SID), "", "resolved rows render nothing")

    def test_the_block_carries_text_id_and_opened_date(self):
        self._seed([{"id": "ut-11111111", "createdT": NOW - 86400,
                     "text": "Need the auth-scheme decision to wire login"}])
        block = km._user_todo_context_block(SID)
        day = km.time.strftime("%Y-%m-%d", km.time.localtime(NOW - 86400))
        self.assertIn("Notes you still have open with the person you work for", block)
        self.assertIn("- Need the auth-scheme decision to wire login (ut-11111111, opened %s)" % day,
                      block)
        self.assertIn("withdraw it (withdraw_user_todo)", block,
                      "the withdraw instruction names the tool by its real name — the agent holds it")

    def test_detail_stays_behind_the_short_line(self):
        # the block carries the one short line only; the longer context lives on the split card
        self._seed([{"id": "ut-11111111", "createdT": NOW, "text": "Need the auth-scheme decision",
                     "detail": "OAuth vs cookie — either unblocks login"}])
        self.assertNotIn("OAuth vs cookie", km._user_todo_context_block(SID))

    def test_newest_first_and_capped_with_a_more_tail(self):
        cap = km._USER_TODO_CONTEXT_CAP
        self._seed([{"id": "ut-%08d" % i, "createdT": NOW + i, "text": "Need decision %d" % i}
                    for i in range(cap + 3)])
        block = km._user_todo_context_block(SID)
        bullets = [ln for ln in block.splitlines() if ln.startswith("- ")]
        self.assertEqual(len(bullets), cap + 1, "cap bullets plus the tail")
        self.assertIn("Need decision %d" % (cap + 2), bullets[0], "the newest ask leads")
        self.assertEqual(bullets[-1], "- …and 3 more from earlier")
        self.assertNotIn("Need decision 0", block, "the oldest beyond the cap fold into the tail")

    def test_exactly_cap_todos_carry_no_tail(self):
        cap = km._USER_TODO_CONTEXT_CAP
        self._seed([{"id": "ut-%08d" % i, "createdT": NOW + i, "text": "Need decision %d" % i}
                    for i in range(cap)])
        self.assertNotIn("more from earlier", km._user_todo_context_block(SID))

    def test_marker_shaped_text_is_neutralized(self):
        # todo text is agent-supplied: a literal "<!--romp-…" in it would inject a lookalike
        # marker into the session's context — same hygiene as the answer body
        self._seed([{"id": "ut-11111111", "createdT": NOW,
                     "text": "Need a call on the note text <!--romp-injected--> in the fixture"}])
        block = km._user_todo_context_block(SID)
        self.assertIsNone(km._ROMP_MARKER_OPEN_RE.search(block),
                          "no marker-opening sequence may survive into the block")
        self.assertIn("romp-injected", block, "the words survive — only the comment form breaks")

    def test_no_liveness_gate_the_session_start_event_is_the_evidence(self):
        # DELIBERATE (slice 3): the block renders even when a death marker / alive:false reg
        # exists. The only caller is a SessionStart fired from INSIDE the session — an ended
        # session fires none — and re-checking the marker here would race the revival's own
        # states row (tmux-status.sh writes it from the SAME SessionStart) and eat the exact
        # block the revival came for. The event outranks the stale record.
        self._seed([{"id": "ut-11111111", "createdT": NOW, "text": "Need the auth-scheme decision"}])
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps({"t": NOW - 50, "by": "gone"}))
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        self.assertIn("ut-11111111", km._user_todo_context_block(SID))


class ContextRoute(_StoreSandbox):
    """POST /usertodo/context — the read leg the SessionStart hook stands on. Token-gated like its
    siblings; READ-ONLY: it must neither write the store nor wake the pusher (nothing changed)."""

    def setUp(self):
        super().setUp()
        self._push = (km._push_all, km._push_soon)
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synchronous _push_all on the context read"))
        km._push_soon = lambda: (_ for _ in ()).throw(
            AssertionError("_push_soon on a read-only route — nothing changed"))

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

    def test_refuses_a_bodyless_or_idless_ask(self):
        self.assertEqual(self._post("/usertodo/context", {})[0], 400)
        code, _ = _serve_post("/usertodo/context", b"not json", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400)

    def test_returns_the_rendered_block_for_open_todos(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        code, res = self._post("/usertodo/context", {"id": SID})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        self.assertEqual(res["block"], km._user_todo_context_block(SID))
        self.assertIn("Notes you still have open", res["block"])

    def test_an_unknown_sid_answers_an_empty_block_not_an_error(self):
        # the hook fires for every romp session that resumes/compacts; "nothing to say" is the
        # common case and must be a clean empty answer, never a loud one
        code, res = self._post("/usertodo/context", {"id": SID2})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        self.assertEqual(res["block"], "")

    def test_the_read_never_writes_the_store(self):
        km._add_user_todo(SID, "Need the auth-scheme decision")
        p = jd.STATE / "user-todos.json"
        before = p.read_text()
        self._post("/usertodo/context", {"id": SID})
        self.assertEqual(p.read_text(), before)


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


class BuildSessionSeam(unittest.TestCase):
    """The chat payload: the top-level `userTodos` field (the upsert merge seam) AND the split-card
    `todo` event that carries the same rows — the chatTail wire re-sends changed EVENTS only, so a
    row change must be an event change or a caught-up client never hears of it."""

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
                      km._read_task_store, km._tmux_sessions, km._GLOBAL_CLAUDE_MD)
        jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATE = names, proj, td / "goals", td
        km.NAMES = names
        km._GLOBAL_CLAUDE_MD = td / "no-global.md"
        km._read_task_store = lambda fsid, fold=None: []
        km._tmux_sessions = lambda: {SID: {"state": "idle", "since": NOW - 100, "model": "", "effort": "",
                                           "context": None, "compactPct": None, "color": None}}
        jd.GOALDIR.mkdir(parents=True)
        km._parse_cache.clear()
        km._user_todos_cache.clear()
        km._set_user_todos(True)                     # switch ON (default OFF since 2026-09-03) — see _StoreSandbox
        rows = [
            {"type": "user", "uuid": "u1", "timestamp": jd.iso(NOW - 90) if hasattr(jd, "iso") else "2026-06-01T00:00:00Z",
             "sessionId": SID, "message": {"role": "user", "content": "wire the login routes"}},
            {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "timestamp": "2026-06-01T00:00:05Z",
             "sessionId": SID,
             "message": {"role": "assistant", "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": "starting on the open routes"}]}},
        ]
        self.tpath.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def tearDown(self):
        (jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATE, km.NAMES,
         km._read_task_store, km._tmux_sessions, km._GLOBAL_CLAUDE_MD) = self.saved
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
        # THE DESIGNED ASYMMETRY (review call, 2026-08-22 — do not "fix"): hideFromFeed quiets
        # the feed and every aggregate built from it — the card marker, the escalation floor,
        # the badge (FeedSeamUserTodos pins that side) — because mute means "stop interrupting
        # me about this session". The CHAT payload, the tab glyph's source, still carries the
        # open todos: the tab remains truthful about what its session holds.
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        (jd.STATE / "session-flags.json").write_text(json.dumps({SID: {"hideFromFeed": True}}))
        km._flags_cache.clear()
        payload = km.build_session(SID, NOW)
        self.assertEqual(len(payload["userTodos"]), 1, "muted ≠ hidden on the session's own tab")
        self.assertEqual(len(self._todo_events(payload)), 1, "the split card renders too")

    def test_a_row_carries_detail_iff_the_ask_has_one(self):
        # The row's "more behind this" hint (render.ts renderTodo → user-todo-hint.ts) keys on the
        # PRESENCE of `detail` on the payload row — that presence is the has-detail flag (no
        # separate boolean: the row already carries the text, and a second field could drift from
        # it). So it must track the store exactly: present, with the text, when the ask carries a
        # non-blank detail; ABSENT (not empty, not null) for a bare one-line ask — and a blank or
        # whitespace-only detail written straight into the store is no detail either, so the seam
        # (_open_user_todos), not just the register route, is what drops it.
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

    def test_a_todo_write_busts_the_chat_build_cache(self):
        # _chat_build_sig is (transcript, states, …) — a todo write changes NEITHER, so without the
        # store in the signature a background tab's cached chat never showed the new row
        sess = {"path": str(self.tpath), "sid": SID, "anchor": ""}
        saved_sdk = km._sdk
        km._sdk = lambda: None
        try:
            before = km._chat_build_sig(sess)
            km._add_user_todo(SID, "Need the auth-scheme decision")
            after = km._chat_build_sig(sess)
        finally:
            km._sdk = saved_sdk
        self.assertNotEqual(before, after)

    def test_another_sessions_todo_write_busts_no_one_elses_cache(self):
        # the fold is PER-SID (_user_todo_fp): a shared-file stat here made every session's write
        # rebuild every tab's chat once — extra load a hot route's caller then waited behind
        sess = {"path": str(self.tpath), "sid": SID, "anchor": ""}
        saved_sdk = km._sdk
        km._sdk = lambda: None
        try:
            before = km._chat_build_sig(sess)
            km._add_user_todo(SID2, "api: need the auth decision")
            after = km._chat_build_sig(sess)
        finally:
            km._sdk = saved_sdk
        self.assertEqual(before, after, "another session's row is not this tab's repaint")

    def test_the_chat_tail_delta_carries_the_user_todos_field(self):
        # the chat wire's steady state is chatTail deltas: a caught-up client that only merged
        # full session frames kept a stale top-level field (the tab glyph's read, next slice)
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
        # the R3 repro shape: park, then the user clicks ✕ on the queued bubble — the answer is
        # recalled before it ever reached the agent, so the ask must still stand
        tid, ops = self._park_an_answer()
        err = km._cancel_parked(SID, 0, km._parked_md(ops[0]))
        self.assertIsNone(err, "the cancel succeeds")
        self.assertFalse(km._pending_ops.get(SID), "the answer will never be delivered")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "recalled ≠ answered: the row returns, nothing is silently lost")

    def test_the_drain_delivers_and_stamps(self):
        tid, _ = self._park_an_answer()
        km._compacting_now = lambda sid: False        # compaction ended — the FIFO may drain
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
        km._compacting_now = lambda sid: False
        saved = km.Sessions.backend_for
        km.Sessions.backend_for = staticmethod(
            lambda sid: (_ for _ in ()).throw(RuntimeError("session is gone")))
        try:
            km._apply_pending_ops()
        finally:
            km.Sessions.backend_for = saved
        self.assertFalse(km._pending_ops.get(SID), "the dead session's queue was dropped")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "dropped ≠ delivered: the ask survives the session")

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
    """Round-2 findings 1+3, one root: the old recall bookkeeping was an IN-MEMORY map while the
    SDK queue it tracked is PERSISTED (reg mirror, reseeded at boot) — so a post-restart recall
    reopened nothing, and the map's global FIFO cap could evict a live entry. The id now travels
    WITH the queued message (the entry itself carries it; the recall reads it back off the entry
    it removes), so there is nothing kernel-side to lose, restart away, or evict."""

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
        # the round-2 test_A shape: the queue survives a kernel restart (reg mirror), the old map
        # did not — so the recall must work with NO in-kernel memory of the send. The fresh
        # kernel's _cancel_backend_queued sees only the entry, and the entry knows its todo.
        be, tid, body = self._answered_via_backend()
        # "kernel restart": there is deliberately no kernel-side record left to clear — the
        # structural pin below proves the side table is gone, so this cancel IS the fresh kernel
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err, "the post-restart unqueue succeeds (the queue was persisted)")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "the recall reopens the ask — never a false permanent 'answered'")

    def test_the_recall_side_table_is_gone(self):
        # finding 3's entire class (a FIFO cap evicting a live entry) dies with the table
        for name in ("_user_todo_recalls", "_USER_TODO_RECALLS_CAP", "_record_user_todo_recall"):
            self.assertFalse(hasattr(km, name),
                             "%s must not come back — the id rides the queue entry" % name)

    def test_many_later_answers_cannot_evict_the_recall(self):
        # the round-2 test_D shape: 64+ later stamps used to evict the live map entry; the id
        # rides the entry now, so no volume of unrelated answers can disarm a recall
        be, tid, body = self._answered_via_backend()
        for i in range(65):
            t2 = km._add_user_todo("00000000-0000-4000-8000-%012d" % i, "todo %d" % i)
            km._stamp_user_todo_answered("00000000-0000-4000-8000-%012d" % i, t2, "body %d" % i)
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err)
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "the recall survives any number of later answers")

    def test_a_lookalike_recall_reopens_nothing(self):
        # the round-2 test_C residual, closed by the same root: the answer was DELIVERED (its
        # entry consumed); a later byte-identical NORMAL send carries no todo id, so recalling
        # that one reopens nothing
        be, tid, body = self._answered_via_backend()
        be.queue.pop(0)                               # the input generator forwards it: delivered
        be.send(SID, body)                            # a plain send, byte-identical, no user_todo
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "the delivered answer stands — nothing rode the lookalike entry")

    def test_a_recalled_entry_never_lifts_a_dismiss(self):
        # the round-2 test_B shape, end to end: parked answer (no stamp), user dismisses, the
        # drain delivers anyway (the entry carries the id), then the user recalls the queued
        # message — the reopen's answered-only guard keeps the dismiss
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
        # tmux and older fakes: no queue_carries_todos → _backend_send hands over the bare text
        # (tmux delivers immediately; there is no queue entry to carry an id on)
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
    """Round-2 finding 2: a kernel death in the fed-but-unlanded window strands a stamped answer —
    the dropped-echo machinery detects the loss but could not tie it back to the ask. The echo now
    carries the todo id, the backend hands it to _user_todo_answer_lost, and the ask visibly
    returns to \"Waiting on you\" — UNLESS the transcript proves the text actually landed (then the
    agent has the answer and the stamp is true; a landed-but-unpruned echo at kernel death is
    common, so reopening blindly would flap answered asks open on every restart)."""

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
        km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "the answer died with its holder — the ask visibly returns")

    def test_a_landed_answer_keeps_its_stamp(self):
        tid, body = self._stamped()
        self._land(body)
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
        km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_an_edge_whitespace_answer_reads_as_landed(self):
        # the CLI records user text verbatim, edge whitespace included, and _atom_user_texts keys it
        # under echo_text_key (strip). A match set built from the raw text never met such a key, so a
        # delivered answer whose send carried a trailing newline was reopened at every boot
        # (2026-09-06 review, round 4): the landed check's forms start from the same key
        tid, body = self._stamped()
        self._land(body + "\n")
        km._user_todo_answer_lost(SID, tid, body + "\n", wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "one key on both sides — delivered, the stamp stands")

    def test_the_loss_path_never_lifts_a_dismiss(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "dismissed")
        km._user_todo_answer_lost(SID, tid, "Re: Need the staging port — 8443.", wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed")

    def test_an_unparsable_transcript_fails_toward_the_visible_ask(self):
        # fail loudly, never degrade silently: a broken landed-check reopens (a wrongly-open ask
        # is visible and dismissable; a wrongly-'answered' one is the silent loss the ADR names)
        tid, body = self._stamped()

        def boom(path, sid, now):
            raise RuntimeError("corrupt transcript")

        km._parse = boom
        km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertNotIn("resolved", km._user_todos()[SID][0])

    def test_the_backend_wire_is_connected(self):
        # the callback must ride CONSTRUCTION (the boot reseed fires drop marks from __init__,
        # before any post-construction attribute assignment could arm it)
        src = inspect.getsource(km._sdk_locked)
        self.assertIn("todo_lost=_user_todo_answer_lost", src)

    def test_a_sid_outside_the_48h_window_still_gets_the_landed_check(self):
        # round 3: the check resolved its session via _sessions(now) — discover's DEFAULT 48h
        # window — so a >48h-idle transcript skipped it silently and a genuinely-landed answer's
        # ask reopened (a card move with no new information). The check now falls back to
        # discover's cached wide walk (the _alive_sessions / DEATH_BACKFILL_WINDOW idiom): it
        # runs whenever the transcript exists at all.
        tid, body = self._stamped()
        self._land(body)
        km._sessions = self._saved[0]        # the REAL _sessions: the window miss must come from
        saved = km.jd.discover               # discover itself, not from the class stub
        try:
            km.jd.discover = (lambda now, window=None, forks=True:
                              [] if window is None else [(SID, "/dev/null", SID, "web")])
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
        # round 3: the recall path already logged a no-op reopen; the loss path swallowed it. A
        # capped-out/cleared row means the answer never landed AND no row remains to show the
        # ask — this log line is the only record left.
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._user_todo_answer_lost(SID, "ut-00000000", "Re: Need the staging port — 8443.",
                                      wait=True)
        self.assertIn("nothing reopened", err.getvalue())
        self.assertIn("ut-00000000", err.getvalue())


class LossBootPass(_StoreSandbox):
    """Round-3 finding 1 (2026-08-22): _mark_dropped_echoes persists an echo's drop mark
    IMMEDIATELY and fires the loss seam exactly once — for the not-yet-marked echo — while the
    reopen itself runs on a fire-and-forget daemon thread that at boot waits out _sdk_lock
    through the whole staggered reconcile. A kernel death in that window left the mark persisted
    with the reopen undone, and the next boot's one-shot marking skipped the already-marked
    echo: the ask stayed falsely 'answered' forever. _user_todo_loss_boot_pass is the durability
    backstop: every boot re-derives the pending set from the PERSISTED world alone (an echo
    drop-marked AND carrying a todo id AND whose store row still reads 'answered') and re-offers
    each to the same landed-check-then-reopen seam — idempotent by the seam's own checks, and
    covering every historical mark, including ones from before the pass existed."""

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
    paste rather than concatenate. `fail` is the dead-server shape (adversarial verify,
    2026-08-27): the named checked steps ("set_buffer" / "paste_buffer" / "enter") answer False
    WITHOUT acting — what a real tmux whose server died after the clear does (exit 1, and the
    command reached no pane)."""

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
    """Merge wave 2026-08-27: the clear-guard (PR-741) taught _tmux_send's paste thread to REFUSE
    when the pane's input box will not empty — correct for the pane, fatal for the delivery-keyed
    stamp it landed under. TmuxBackend.send stays truthy (fire-and-forget), so the answer stamps
    'answered' at the truthy send, and the refused paste never reaches the agent: with no loss
    seam on the tmux side that is docs/adr/0001's silent-loss class verbatim (before the guard
    the paste was unconditional, so the truthy send really was the delivery). The refusal EVENT
    now reopens the ask: the send carries the todo id, and the paste thread's refuse branch — or
    a death before Enter — hands it to _user_todo_answer_lost, the same reopen the SDK loss path
    uses, keyed at the refusal point itself so BOTH stamping callers (the drive handler's
    immediate send, the park drain's merged batch) are covered by one seam."""

    def setUp(self):
        super().setUp()
        self._saved = (km._TMUX, km._sessions, km._parse, km._compacting_now,
                       dict(km._pending_ops))
        self.be = km._TMUX                 # the REAL backend: send → _tmux_send → the fake pane
        # the LostAnswerReopens stubs: a transcript exists and holds nothing — a refused paste
        # never lands, so the seam's landed check must find no delivery and reopen
        km._sessions = lambda now, window=None, forks=True: [{"sid": SID, "path": "/dev/null"}]
        km._parse = lambda path, sid, now: {"turns": []}
        km._compacting_now = lambda sid: False
        km._pending_ops.clear()
        km._pane_io_locks.clear()

    def tearDown(self):
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
        # THE defect the merge minted, end to end through the immediate path (_send_or_park →
        # _backend_send → the real TmuxBackend.send → the real clear against an unclearable
        # pane): truthy send → stamp; the paste thread then refuses; the ask must visibly return
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

    # ── delivered means DELIVERED (findings 2+3, adversarial verify 2026-08-27) ──
    # The forgiving primitives swallow exec errors and ignore exit codes, so a tmux server that
    # died AFTER a successful clear made set-buffer/paste-buffer/Enter silent no-ops while
    # paste() answered True: the stamp stood, nothing was delivered, and no refusal fired. The
    # three steps that are the delivery now read tmux's own exit code (verified on tmux 3.4:
    # dead server → 1 "no server running") and any failure is a refusal like the clear-guard's.

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

    # ── the hook-exception contract (findings 4+5, adversarial verify 2026-08-27) ──

    def test_the_noop_early_return_arm_guards_a_throwing_hook(self):
        # finding 4: the empty-name/empty-text arm fires on_refused SYNCHRONOUSLY on the
        # caller's thread — unguarded, a throwing hook propagated into the caller, contradicting
        # the documented contract (stderr-logged, never raised). Unreachable with today's
        # callers, guarded anyway so the trap cannot arm.
        def boom():
            raise ValueError("hook boom")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._tmux_send("", "the composer message", _async=False, on_refused=boom)
            km._tmux_send("web", "", _async=False, on_refused=boom)
        self.assertEqual(err.getvalue().count("refusal hook failed"), 2,
                         "both empty arms log the hook's failure instead of raising it")

    def test_a_throwing_refusal_hook_is_logged_never_raised(self):
        # finding 5a: go()'s guarantee, pinned — the clear-guard refuses, the hook throws, and
        # nothing propagates (run sync so a raise would surface right here); the failure is SAID
        km._TMUX = _FakeTmuxPane(["a draft typed straight into the terminal"], honors_kill=False)

        def boom():
            raise ValueError("hook boom")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._tmux_send("web", "the composer message", _async=False, on_refused=boom)
        self.assertIn("refusal hook failed", err.getvalue())

    def test_a_throwing_hook_never_masks_the_pastes_own_exception(self):
        # finding 5b: the ORIGINAL death (set-buffer raising mid-send) stays the loud one — the
        # hook's own failure is logged, never swapped in for what propagates
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
    mark-store readers/writers the assertions speak in."""

    def setUp(self):
        super().setUp()
        self._saved = (km._TMUX, km._sessions, km._parse, km._compacting_now,
                       dict(km._pending_ops))
        self.be = km._TMUX                 # the REAL backend: send → _tmux_send → the fake pane
        self.turns = []
        km._sessions = lambda now, window=None, forks=True: [{"sid": SID, "path": "/dev/null"}]
        km._parse = lambda path, sid, now: {"turns": self.turns}
        km._compacting_now = lambda sid: False
        km._pending_ops.clear()
        km._pane_io_locks.clear()

    def tearDown(self):
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
    """Finding 1 (adversarial verify, 2026-08-27): the tmux refusal seam was process-lifetime-
    only. TmuxBackend.send returns truthy while the paste runs on a daemon thread, so a kernel
    death in the stamp→verdict window (0.3–4s) killed the thread pre-Enter: no refusal fired,
    and nothing persisted even RECORDED the attempt — the false 'answered' survived the restart,
    docs/adr/0001's silent-loss class, the exact window the SDK closed with persisted drop marks
    + _user_todo_loss_boot_pass. These pin the tmux twin: a pending-paste mark persists BEFORE
    the truthy send returns, the paste thread clears it on its verdict (delivered → clear;
    refused → the verdict is recorded on the store, THEN the clear), and
    _tmux_paste_loss_boot_pass re-offers any mark a dead kernel left to the same
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
                         "the caller to thread into its stamp (round 4, 2026-08-27)")
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

    def test_the_pass_is_wired_into_main_before_any_backend_construction(self):
        # same ordering claim as the SDK sibling's: the marks must be read as the dead kernel
        # left them, before any of this boot's sends can write new ones
        src = inspect.getsource(km.main)
        i = src.index("_tmux_paste_loss_boot_pass")
        self.assertLess(i, src.index("_boot_warm()"),
                        "_boot_warm's _alive_sessions constructs the backend — the pass runs first")
        self.assertLess(i, src.index("target=_sdk"))

    # ── the landed check accepts the CLI's image rewrite (finding 2, round 3 2026-08-27) ──
    # Claude Code reads each pasted image PATH and rewrites it in the input to "[Image #N]"
    # before submit — the very rewrite _tmux_send's pre-Enter wait exists for — so a DELIVERED
    # image-carrying answer appears in the transcript in the rewritten form. A landed check
    # keyed on the raw bytes alone falsely reopened such an answer at every boot.

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

    # ── the boot pass consumes what it DISCOVERED (finding 3, round 3 2026-08-27) ──
    # Discovery is by glob, but consumption re-derived the path from the EMBEDDED sid field: a
    # file whose two identities disagree was re-read (and possibly re-acted-on) every boot,
    # forever — and a directory named *.json survived silently just as long.

    def test_a_mark_whose_embedded_sid_disagrees_is_consumed_loudly(self):
        d = jd.STATE / "tmux-paste"
        d.mkdir(parents=True, exist_ok=True)
        p = d / (SID + ".json")
        p.write_text(json.dumps({"sid": SID2,
                                 "pending": [{"todo": "ut-11111111", "text": "Re: x — y", "t": 1}]}))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0,
                             "a mark whose identities disagree is never acted on")
        self.assertFalse(p.exists(),
                         "consumed by the path it was DISCOVERED at — never re-read next boot")
        self.assertNotEqual(err.getvalue(), "", "…and refused loudly, never silently")

    def test_a_directory_in_the_marks_store_is_loud_never_silent(self):
        d = jd.STATE / "tmux-paste"
        (d / "not-a-mark.json").mkdir(parents=True)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0)
        self.assertNotEqual(err.getvalue(), "",
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
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0)
            self.assertNotEqual(err.getvalue(), "",
                                "an unlinkable mark is announced — it WILL be re-read next boot")
        finally:
            os.chmod(d, 0o755)


class TmuxStampStandDown(_TmuxPasteHarness):
    """Findings 1+4 (round 3, 2026-08-27) — one defect, two lenses: the refusal can OUTRUN the
    caller's 'answered' stamp (a dead tmux server fails the clear-guard's first capture in
    milliseconds while the stamp queues on _user_todos_lock), and the refusal hook's
    unconditional unmark then forfeited the healing record — the seam's reopen no-oped (no
    'answered' row yet), the mark was consumed anyway, and the late stamp stood forever,
    unhealable even at boot. The fix is the repo's own doctrine at the write moment: the stamp's
    evidence is the truthy send; the refusal verdict is NEWER information; the stamp yields.
    Mechanism: the seam reports its verdict, an open-row refusal flips the mark to refused
    (never consumes it), and _stamp_user_todo_answered checks the mark store under the same lock
    before stamping — a refused mark stands the stamp down, records the loss, and consumes the
    mark itself. Ordering is proven by gating the stamp on the refusal verdict being RECORDED —
    an event, never a sleep."""

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
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._stamp_user_todo_answered(SID, tid, body, nonce=got)   # the late stamp lands…
        self.assertNotIn("resolved", self._rows()[0],
                         "…and stands down: the refusal verdict is newer information than the "
                         "truthy send the stamp is acting on")
        self.assertEqual(self._marks(), [], "the stand-down consumed the refused mark itself")
        self.assertIn("stand", err.getvalue(), "a stood-down stamp is said out loud")
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
        with contextlib.redirect_stderr(io.StringIO()):
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


class SeamOrderPins(_TmuxPasteHarness):
    """Finding 5 (round 3, 2026-08-27): the load-bearing orderings — a refusal's clear follows
    its verdict; the boot pass consumes only after the seam rules — were asserted only via end
    states that are identical under inverted order, so swapping the calls passed the suite.
    The fix makes the unmark data-DEPENDENT on the seam's verdict (structural enforcement);
    these pin the observed sequence itself, for all three callers."""

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
    """Round 4 (2026-08-27): a drained batch can carry TWO parked answers for the SAME todo —
    the stamp is delivery-keyed, so the row stays open until the drain, and a second dashboard's
    answer (or a re-answer) legitimately parks a second op for the same id. The merged paste is
    ONE delivery event per todo, but the batch's accounting ran PER OP, in both orderings:
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
        # finding A (probe ordering 1): the clear-guard refuses on the paste thread while both
        # stamps are still pending — deterministic via gating each stamp on the refusal verdict
        # being RECORDED in the mark store (an event, never a sleep)
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
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._deliver_send_batch(self.be, SID, run)
        self.assertNotIn("resolved", self._rows()[0],
                         "one delivery event, one stamp, stood down on the refusal — a "
                         "duplicate op must never land a second, false 'answered'")
        self.assertEqual(self._marks(), [], "the stand-down consumed its own send's mark")
        self.assertIn("stand", err.getvalue(), "the stood-down stamp is said out loud")
        self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 0)
        self.assertNotIn("resolved", self._rows()[0], "healed for good — not parked for a boot")

    def test_a_refusal_after_duplicate_stamps_strands_no_flag(self):
        # finding B (probe ordering 2): stamps land first, the refusal rules after — the seam
        # must rule the tid ONCE, unmark its one mark, and leave nothing refused on disk
        km._TMUX = _FakeTmuxPane()
        gate = self._gate_clear(False)
        tid, body, run = self._dup_run()
        km._deliver_send_batch(self.be, SID, run)
        merged = body + "\n\n" + body
        self.assertEqual(self._marks(), [(tid, merged)],
                         "one delivery event per todo = ONE mark, on the merged text")
        self.assertEqual(self._rows()[0]["resolved"]["kind"], "answered",
                         "the stamps landed first — the normal ordering")
        with contextlib.redirect_stderr(io.StringIO()):
            gate.set()                               # NOW the clear-guard refuses the paste
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
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._tmux_paste_loss_boot_pass(wait=True), 1)
        self.assertNotIn("resolved", self._rows()[0])
        self.assertEqual(self._marks(), [])

    def test_a_nonceless_stamp_still_yields_to_any_refusal_on_its_todo(self):
        # fail toward the visible ask: a stamp that cannot name its send (no nonce) yields to
        # ANY refusal recorded for the todo — the legacy read, kept as the conservative default
        tid = km._add_user_todo(SID, self.ASK)
        body = km._user_todo_answer_body(self.ASK, "8443.")
        self._mark_file([{"todo": tid, "text": body, "t": 1, "refused": True,
                          "nonce": "1111aaaa"}])
        with contextlib.redirect_stderr(io.StringIO()):
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
        with contextlib.redirect_stderr(io.StringIO()):
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
    """Round-2 finding 4: every downstream matcher tolerates arbitrary whitespace after the
    comment opener (\"<!--\\s*romp-\"), so the neutralizer must break that same CLASS, not the one
    literal one-space spelling — a no-space \"<!--romp-injected-->\" in todo text sailed through
    and the user's own answer rendered as romp's system card. Verified against the VERBATIM
    downstream regexes, imported, never copied."""

    WS = ("", " ", "   ", "\n", "\t ", " \n ")

    def _cases(self):
        for ws in self.WS:
            yield "<!--%sromp-injected -->" % ws, em.ROMP_INJECT_RE, "romp-injected"
            yield "<!--%sromp-injected -->" % ws, km.jd.NUDGE_MARKER_RE, "romp-injected"
            yield "<!--%sromp-msg-id: m-3f2c -->" % ws, em.POSTAL_RE, "romp-msg-id"
            yield "<!--%sromp-tag: build-1 -->" % ws, em.MSG_TAG_RE, "romp-tag"

    def test_every_whitespace_variant_breaks_for_every_downstream_matcher(self):
        for raw, rex, words in self._cases():
            self.assertTrue(rex.search(raw),
                            "sanity: %r must be marker-shaped for /%s/" % (raw, rex.pattern))
            out = km._neutralize_romp_markers("note %s kept" % raw)
            self.assertFalse(rex.search(out),
                             "neutralized %r still matches /%s/" % (out, rex.pattern))
            self.assertIn(words, out, "the words survive — only the comment form breaks")

    def test_the_answer_body_gets_the_same_tolerance_on_both_halves(self):
        for raw, rex, _ in self._cases():
            body = km._user_todo_answer_body("Need a call on %s in the fixture" % raw,
                                             "Keep it, but drop the %s part." % raw)
            self.assertFalse(rex.search(body),
                             "an answer body carrying %r still matches /%s/" % (raw, rex.pattern))

    def test_the_edit_trace_path_gets_the_same_neutralization(self):
        # the edit trace embeds the request-supplied file PATH in an injected body — a marker-shaped
        # filename must not become a live marker downstream readers key on (same rule as the answer
        # body's two halves). The body's own designed tail IS a real marker, so only the prose half
        # before it is asserted marker-free.
        for raw, rex, _ in self._cases():
            body = km._edit_trace_body("/TESTDIR/notes-api/drafts/%s.md" % raw)
            head, sep, _tail = body.rpartition("<!-- romp-injected -->")
            self.assertTrue(sep, "the designed marker tail must still ride the body")
            self.assertFalse(rex.search(head),
                             "the path half carrying %r still matches /%s/" % (raw, rex.pattern))

    def test_the_escape_is_the_same_visible_one(self):
        self.assertEqual(km._neutralize_romp_markers("<!-- romp-injected -->"),
                         "<!- - romp-injected -->")
        self.assertEqual(km._neutralize_romp_markers("<!--romp-injected-->"),
                         "<!- -romp-injected-->")

    def test_the_bare_goal_id_form_breaks_in_both_todo_bodies(self):
        # The CANONICAL neutralizer (the one def these callers actually reach — see
        # tests/test_marker_neutralizer.py's single-def pin) also breaks the bare "romp-goal-id:"
        # form: it needs no comment opener, and per the follow-up contract it would REOPEN the
        # named goal — todo text and replies are agent/user-supplied, so a quoted id in either
        # half must not fire the judge's FOLLOWUP_RE or the kernel's twin.
        raw = "wrap up romp-goal-id: g-12 first"
        for rex in (km.jd.FOLLOWUP_RE, km._FOLLOWUP_GOAL_RE):
            self.assertTrue(rex.search(raw),
                            "sanity: %r must be marker-shaped for /%s/" % (raw, rex.pattern))
            body = km._user_todo_answer_body("Need a call on %s" % raw, "Do %s after." % raw)
            self.assertFalse(rex.search(body),
                             "an answer body carrying %r still matches /%s/" % (raw, rex.pattern))
            self.assertNotIn("romp-goal-id:", km._neutralize_romp_markers(raw))
        self.assertIn("romp-goal-id;", km._neutralize_romp_markers(raw),
                      "the visible escape: the colon becomes a semicolon")

    def test_a_non_romp_comment_is_untouched(self):
        self.assertEqual(km._neutralize_romp_markers("code sample: <!-- not ours -->"),
                         "code sample: <!-- not ours -->")


class ResolvedRowsAreBounded(_StoreSandbox):
    """Round-2 finding 5: a never-dying session's resolved rows accumulated without bound (the
    prune clears them only at session death — right for history, wrong as an invariant on a
    self-hosted box whose sessions live for weeks), and _user_todo_fp re-serializes every row on
    every chat build. A per-sid SIZE cap on RESOLVED rows only: the newest _USER_TODO_RESOLVED_KEEP
    stay, the oldest leave. OPEN rows are NEVER capped — the ADR's authority tier: an open ask
    leaves the store by answer/dismiss/withdraw alone, never by volume."""

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


# ────────────────────────────── slice 2: ambient visibility and the endgame ──────────────────────────


def _feed_env(test, sids):
    """Patch build_feed's session inputs to a synthetic alive set — the map/floor seams need no
    parse (ps None keeps every parse-derived path dark, exactly the cold-start shape)."""
    sessions = [{"sid": s, "name": n, "path": "/nonexistent/%s.jsonl" % s, "anchor": 0, "mtime": 0}
                for s, n in sids]
    ps = [
        mock.patch.object(km, "_alive_sessions", lambda now, tmux: list(sessions)),
        mock.patch.object(km, "_warm_fleet_bg", lambda now: None),
    ]
    for p in ps:
        p.start()
        test.addCleanup(p.stop)


class FeedSeamUserTodos(_StoreSandbox):
    """build_feed's return grows a top-level sid-keyed OPEN-COUNT map (plans/user-todos.md, data
    seams) — the feed-card marker's ride, the same way working[]/bgServices ride the payload. The
    ended gate is build_session's exact gate; a muted (hideFromFeed) session contributes nothing,
    like every other feed surface."""

    def test_the_map_carries_open_counts_per_sid(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._add_user_todo(SID, "Need a staging credential for the tests")
        tid = km._add_user_todo(SID2, "Need your pick of the two route layouts")
        km._resolve_user_todo(SID2, tid, "withdrawn")
        _feed_env(self, [(SID, "web"), (SID2, "api")])
        feed = km.build_feed(NOW, {})
        self.assertEqual(feed.get("userTodos"), {SID: 2}, "open rows only; a resolved-only sid is absent")

    def test_an_ended_sessions_todos_are_hidden_from_the_map(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps({"t": NOW, "by": "gone"}))
        _feed_env(self, [(SID, "web")])
        feed = km.build_feed(NOW, {})
        self.assertEqual(feed.get("userTodos"), {}, "hidden, not cleared — they return with a revive")
        self.assertTrue(km._open_user_todos(SID), "the store still holds the open ask")

    def test_a_muted_session_contributes_nothing(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        (jd.STATE / "session-flags.json").write_text(json.dumps({SID: {"hideFromFeed": True}}))
        km._flags_cache.clear()
        _feed_env(self, [(SID, "web")])
        feed = km.build_feed(NOW, {})
        self.assertEqual(feed.get("userTodos"), {}, "muted from the feed → no marker data either")

    def test_the_map_serializes_stably_across_builds(self):
        # the feed payload is dedup-compared serialized (_send_client) — same store, same bytes
        km._add_user_todo(SID2, "api: need the auth decision")
        km._add_user_todo(SID, "web: need the staging port")
        _feed_env(self, [(SID, "web"), (SID2, "api")])
        a = json.dumps(km.build_feed(NOW, {}).get("userTodos"))
        b = json.dumps(km.build_feed(NOW, {}).get("userTodos"))
        self.assertEqual(a, b)
        self.assertEqual(json.loads(a), {SID: 1, SID2: 1})

    def test_the_view_sig_watches_the_store(self):
        # the marker/badge/floor all read this store from build_feed, so a todo write must bust
        # the FEED cache the way it already busts the owning session's chat cache — without this
        # the new row waited on an unrelated rebuild
        before = km._fleet_view_sig(NOW, {})
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        after = km._fleet_view_sig(NOW, {})
        self.assertNotEqual(before, after)


class EscalationFloorPredicate(_StoreSandbox):
    """The idle-escalation floor's ARMING read (_user_todo_idle): true only when the session has
    SETTLED idle — no open turn, nothing dispatched, no queued intent, no live prompt — the exact
    idle the auto-nudge tick requires. Event-keyed both ways, and NEVER armed by a transient
    turn-boundary lull (the cards-move-on-new-information rule; WHY_UNBLOCK_UNSETTLED is the
    repo's own card-flap history)."""

    PS = {"turns": [{"id": "t1", "t": NOW - 60, "end": NOW - 30, "atoms": []}]}

    def _idle(self, sid=SID, ps=None, who_working=False, awaiting=None, perm_state=None, aerr=None,
              last_state=("waiting", NOW - 20), queued=False, rewind=False, compacting=False,
              interrupted=False, pending_ops=None, peer_wait=None):
        patches = [
            mock.patch.object(km, "_last_state", lambda s: last_state),
            mock.patch.object(km, "_backend_queued", lambda s: queued),
            mock.patch.object(km, "_backend_rewind_pending", lambda s: rewind),
            mock.patch.object(km, "_compacting_now", lambda s: compacting),
            mock.patch.object(km, "_interrupt_suppresses_nudge", lambda turns, s="", **k: interrupted),
            mock.patch.dict(km._pending_ops, pending_ops or {}, clear=True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return km._user_todo_idle(sid, self.PS if ps is None else ps, who_working, awaiting,
                                  perm_state, aerr, peer_wait)

    def test_a_settled_idle_session_arms_the_floor(self):
        self.assertTrue(self._idle())

    def test_an_open_turn_never_arms_it(self):
        self.assertFalse(self._idle(who_working=True))

    def test_dispatched_background_work_never_arms_it(self):
        self.assertFalse(self._idle(awaiting="waiting on 2 agents"))

    def test_a_live_prompt_or_compaction_never_arms_it(self):
        self.assertFalse(self._idle(perm_state="permission"))
        self.assertFalse(self._idle(perm_state="picker"))
        self.assertFalse(self._idle(perm_state="compacting"))
        self.assertFalse(self._idle(compacting=True))

    def test_an_api_error_story_wins(self):
        self.assertFalse(self._idle(aerr={"status": 529, "text": "overloaded"}))

    def test_queued_intent_means_the_session_is_about_to_wake(self):
        # a message arrived — the de-escalation event; the floor must not claim idle over it
        self.assertFalse(self._idle(queued=True))
        self.assertFalse(self._idle(pending_ops={SID: [("send", "hi")]}))
        self.assertFalse(self._idle(rewind=True))

    def test_a_user_interrupt_means_the_user_acted(self):
        self.assertFalse(self._idle(interrupted=True))

    def test_waiting_on_a_live_peer_never_floors(self):
        # the notes-api shape (review 2026-08-22): api sent web a question and web is alive —
        # api's idle with an open todo is explained by the PEER it awaits (_wait_for_graph's
        # edge, the same event the waitingOn chip and the nudge tick's skip read), and waiting
        # on a peer is deliberately NOT needs-you (interrupt only when the human is the
        # bottleneck). The floor must not fire while a live peer owes this session a reply.
        edge = {"peerSid": SID2, "name": "web", "color": None, "inCycle": False,
                "since": NOW - 900, "kind": "question"}
        self.assertFalse(self._idle(peer_wait=edge))

    def test_the_peer_wait_lifts_with_the_edge(self):
        # the peer's reply (any message back) drops the edge — a real postal event, and the
        # floor may then claim the idle it explains
        self.assertTrue(self._idle(peer_wait=None))

    def test_no_parse_or_no_turns_reads_unknown_never_idle(self):
        self.assertFalse(self._idle(ps={}))
        self.assertFalse(self._idle(ps={"turns": []}))
        self.assertFalse(km._user_todo_idle(SID, None, False, None, None, None))

    def test_no_flap_a_mid_turn_lull_never_arms_the_floor(self):
        # THE PIN (the card-flap history): the event model reads "no open turn" during transient
        # mid-turn lulls, so keying the floor on that alone would strobe the card at every turn
        # boundary. The authoritative state log saying PROGRESSING at/after the parsed turn end
        # means the stop is not real — the same genuine-stop discriminator the auto-nudge uses,
        # two real-event timestamps, no time window.
        self.assertFalse(self._idle(last_state=("working", NOW - 10)),
                         "state log progressing AFTER the turn end → a lull, not a stop")
        self.assertFalse(self._idle(last_state=("working", NOW - 30)),
                         "progressing AT the turn end → still the open turn")

    def test_a_stale_progressing_record_from_before_the_turn_end_does_not_wedge(self):
        # the post-turn 'waiting' write can be LOST (kernel restart) — a progressing record OLDER
        # than the turn end must not pin the floor off forever (the bugsdk2 nudge lesson)
        self.assertTrue(self._idle(last_state=("working", NOW - 40)))

    def test_the_deciding_events_re_derive_it_cleanly(self):
        # escalate at the settle; stand down the build after a new turn opens — each a real event
        self.assertTrue(self._idle())
        self.assertFalse(self._idle(who_working=True), "a new turn opening stands the floor down")


class EscalationFloorWiring(_StoreSandbox):
    """The floor lives in build_feed's perm_top family (source pins — the same convention as
    test_kernel_distill_state: a full feed build's inputs are heavy). A verdict-shaped write is
    exactly what the ADR forbids; the floor re-derives from the store read each build."""

    def test_the_floor_yields_to_every_live_interrupt(self):
        src = inspect.getsource(km.build_feed)
        self.assertIn("_user_todo_idle(", src)
        self.assertIn("if _todo_idle and api_top is None and perm_top is None and jauth_top is None:",
                      src, "one interrupt at a time — the present event first")

    def test_the_floor_files_the_focus_card_under_needs_input(self):
        src = inspect.getsource(km.build_feed)
        self.assertIn('_todo_block = bool(nid == todo_top and col == "working")', src,
                      "floors a plain-working focus card only — never displaces awaiting/blocked/"
                      "recheck moves, which are their own designed latches")
        self.assertIn("or _todo_block", src.split("column = (")[1].split(")\n")[0],
                      "the column expression carries the floor")

    def test_the_escalated_card_carries_the_story(self):
        src = inspect.getsource(km.build_feed)
        self.assertIn('{"state": "userTodos"', src)
        self.assertIn("if _todo_block", src)

    def test_the_ended_gate_is_build_sessions_exact_gate(self):
        src = inspect.getsource(km.build_feed)
        self.assertIn("_user_todo_session_ended(fsid)", src)

    def test_a_goal_less_session_gets_the_needs_input_placeholder(self):
        src = inspect.getsource(km.build_feed)
        self.assertIn("elif _todo_idle and _ut_open and todo_top is None and not had_needs_input:",
                      src, "…and only when NOTHING else floored/blocked the session — one "
                           "interrupt story at a time (review 2026-08-22; OneInterruptStory "
                           "carries the behavioral repro)")
        self.assertIn("_user_todo_placeholder(", src)

    def test_the_floor_reads_the_peer_wait_edge(self):
        # review 2026-08-22: the predicate's peer-wait input comes from the SAME wait-for graph
        # the nudge tick and the waitingOn chip consult — never a second derivation
        src = inspect.getsource(km.build_feed)
        self.assertIn("aerr, wmap.get(fsid),", src)   # the edge, then the badge read (P2 S2)

    def test_the_provisional_chain_treats_a_floored_card_as_working(self):
        # review 2026-08-22: a todo-floored focus card reports needs_input, so without this the
        # judge-latency window painted a provisional Working "Analyzing:" placeholder BESIDE the
        # floored card — the exact duplicate the perm floor's guard already prevents; mirror it
        src = inspect.getsource(km.build_feed)
        self.assertIn("if not had_working and perm_top is None and todo_top is None and ps:", src)

    def test_the_placeholder_is_a_presentation_not_a_countable_card(self):
        # provisional, like the goal-less permission placeholder — the badge counts the TODOS
        # (the map), never this presentation of them (the no-double-count rule)
        ph = km._user_todo_placeholder(
            {"sid": SID, "path": "/nonexistent"}, "web", None, SID, True, NOW,
            [{"id": "ut-11111111", "text": "Need the auth-scheme decision", "createdT": NOW - 300},
             {"id": "ut-22222222", "text": "Need a staging credential", "createdT": NOW - 100}])
        self.assertTrue(ph["provisional"])
        self.assertEqual(ph["column"], "needs_input")
        self.assertEqual(ph["blocked"]["state"], "userTodos")
        self.assertEqual(ph["blocked"]["count"], 2)
        self.assertEqual(ph["itemId"], "usertodo:" + SID)
        self.assertIn("Need the auth-scheme decision", ph["text"], "the oldest open ask titles it")
        self.assertIn("+1 more", ph["text"])
        self.assertEqual(ph["t"], NOW - 100, "the newest ask is the card's current-state time")

    def test_the_floor_is_not_a_judge_verdict(self):
        # read-side only: build_feed never writes the goal store or the diary for this move
        src = inspect.getsource(km.build_feed)
        self.assertNotIn("save_goals", src)


class PeerWaitScopeIsLocalOnly(_StoreSandbox):
    """The peer-wait stand-down is LOCAL-HOST only — a DOCUMENTED limitation, pinned (round-2
    verification, 2026-08-22): _wait_for_graph keeps an edge only when the awaited peer is in
    THIS kernel's alive set, so an unanswered ask to a FEDERATED peer (a relay-addressed row)
    makes no edge and the idle floor still fires needs-you over an idle a remote peer actually
    explains. The scope is shared with the waitingOn chip and the nudge tick's skip — all three
    read the same graph, deliberately: cross-host wait tracking belongs in _wait_for_graph,
    where widening it lifts every surface at once; a floor-only special case would fork the
    wait derivation (plans/user-todos.md, escalation). If these tests start failing because the
    graph learned federated edges, flip the floor's expectation CONSCIOUSLY alongside the
    chip's."""

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

    def _write_rows(self, rows):
        self.mfile.parent.mkdir(parents=True, exist_ok=True)
        self.mfile.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        km._POSTAL_WAIT_CACHE[:] = [None, None]

    def test_a_local_alive_peer_makes_the_edge(self):
        # the control (keeps the negatives below non-vacuous): the same unanswered question to
        # a LOCAL alive peer builds the edge the floor stands down on
        self._write_rows([{"from_id": SID, "to_id": SID2, "t": NOW - 300,
                           "kind": "question", "body": "Which port does staging use?"}])
        wmap = km._wait_for_graph(NOW, {SID, SID2})
        self.assertIn(SID, wmap)
        self.assertEqual(wmap[SID]["peerSid"], SID2)

    def test_a_relay_addressed_ask_makes_no_edge_so_the_floor_still_fires(self):
        # the federated shape: the row is addressed to the relay and the remote never spoke, so
        # the alias cannot resolve and the pair keys on the named recipient — never in the local
        # alive set, so the graph drops the edge and the floor's peer_wait input (wmap.get(sid))
        # is None: a session idle on a cross-host reply still floors as needs-you. KNOWN
        # limitation, kept consciously — see the class docstring.
        self._write_rows([{"from_id": SID, "to_id": "peer:TESTHOST", "toName": "TESTHOST:api",
                           "t": NOW - 300, "kind": "question",
                           "body": "Which port does staging use?"}])
        wmap = km._wait_for_graph(NOW, {SID})
        self.assertNotIn(SID, wmap, "no edge to a federated peer — wmap is local-host scope")

    def test_even_a_resolved_remote_sid_makes_no_edge(self):
        # the stronger claim: the alias CAN resolve the remote's real sid (it sent a row once),
        # and the edge is still dropped — the gate is the local alive set, not addressability
        self._write_rows([
            {"from_id": SID2, "from": "api", "from_host": "TESTHOST", "to_id": SID,
             "t": NOW - 900, "kind": "coordinate", "body": "Staging is rebuilt nightly."},
            {"from_id": SID, "to_id": "peer:TESTHOST", "toName": "TESTHOST:api",
             "t": NOW - 300, "kind": "question", "body": "Which port does staging use?"},
        ])
        wmap = km._wait_for_graph(NOW, {SID})
        self.assertNotIn(SID, wmap, "a resolvable but non-local peer still makes no edge")


class OneInterruptStory(_StoreSandbox):
    """Review 2026-08-22, the guard-conflict roots: a session shows ONE interrupt presentation
    at a time. (a) The goal-less userTodos placeholder fired BESIDE a jauth-floored focus card
    (todo_top None conflated 'no live goal' with 'yielded to jauth_top'); (b) the provisional
    Working chain painted an 'Analyzing:' placeholder beside a todo-floored card during judge
    latency; and the focus-chain miss: a completed lastNode top with another top still working
    escalated NOTHING (the walk dead-ended, had_working suppressed the placeholder). Behavioral,
    over a real build_feed with the repro's own harness — SYNTHETIC data only."""

    TURNS = [{"id": "t1", "t": NOW - 60, "end": NOW - 30, "ended": True, "atoms": []}]

    def _env(self, store, jauth=False, extra=None):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        sessions = [{"sid": SID, "name": "web", "path": "/nonexistent/%s.jsonl" % SID,
                     "anchor": 0, "mtime": 0}]
        turns = list(self.TURNS)
        patches = [
            mock.patch.object(jd, "_auth_down_map",
                              lambda: ({SID: {"mode": "key", "since": NOW - 100}} if jauth else {})),
            mock.patch.object(km, "_alive_sessions", lambda now, tmux: list(sessions)),
            mock.patch.object(km, "_warm_fleet_bg", lambda now: None),
            mock.patch.object(km, "_parse_cached", lambda path: {"turns": list(turns)}),
            mock.patch.object(km, "_merge_live_atoms", lambda ps, sid: ps),
            mock.patch.object(km, "_feed_goals", lambda sid: dict(store)),
            # the predicate is pinned separately (EscalationFloorPredicate); force-arm it here
            # so these shapes exercise the GUARDS, not the arming gates — arity-proof on purpose
            mock.patch.object(km, "_user_todo_idle", lambda *a, **k: True),
        ] + (extra or [])
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _needs_input(self, feed):
        return [a for a in feed["asks"]
                if str(a.get("sid")) == SID and a.get("column") == "needs_input"]

    def test_the_jauth_floor_stands_alone(self):
        # the reviewer repro: jauth latched + open todos + a live goal → the jauth story is the
        # one interrupt; the goal-less todo placeholder must not fire beside it
        self._env({"nodes": {"g1": {"parentId": None, "t": NOW - 500, "text": "wire the login flow"}},
                   "status": {"g1": "working"}, "lastNode": "g1", "placements": {}}, jauth=True)
        ni = self._needs_input(km.build_feed(NOW, {}))
        self.assertEqual(len(ni), 1,
                         "ONE needs-input presentation, got %d (%s)"
                         % (len(ni), sorted(str((a.get("blocked") or {}).get("state")) for a in ni)))
        self.assertNotIn("usertodo:" + SID, [a["itemId"] for a in ni],
                         "the placeholder yielded — jauth won")

    def test_a_todo_floored_card_gets_no_working_placeholder(self):
        # (b): during judge latency _provisional_card can return a Working 'Analyzing:' card;
        # a todo-floored focus card already tells the session's one story, so the provisional
        # chain must treat it as had-working-equivalent (the perm floor's own handling)
        dummy = {"itemId": "provisional:" + SID, "sid": SID, "name": "web", "color": None,
                 "text": "Analyzing: wire the login flow", "t": NOW, "live": True,
                 "trgb": [0, 0, 0], "turnId": None, "origin": None, "followupPending": None,
                 "summary": None, "blockSummary": None, "background": None,
                 "blocked": None, "column": "working", "provisional": True, "tree": []}
        self._env({"nodes": {"g1": {"parentId": None, "t": NOW - 500, "text": "wire the login flow"}},
                   "status": {"g1": "working"}, "lastNode": "g1", "placements": {}},
                  extra=[mock.patch.object(km, "_provisional_card", lambda *a, **k: dict(dummy))])
        feed = km.build_feed(NOW, {})
        ni = self._needs_input(feed)
        self.assertEqual([str((a.get("blocked") or {}).get("state")) for a in ni], ["userTodos"],
                         "the floored focus card carries the story")
        self.assertNotIn("provisional:" + SID, [a["itemId"] for a in feed["asks"]],
                         "no Working placeholder beside the floored card")

    def test_a_completed_focus_falls_back_to_the_working_top(self):
        # the focus-chain miss: lastNode's top completed, another top still working → the todo
        # IS the frontier of this IDLE session regardless of which top holds focus
        self._env({"nodes": {"g1": {"parentId": None, "t": NOW - 900, "text": "ship the fixtures"},
                             "g2": {"parentId": None, "t": NOW - 500, "text": "wire the login flow"}},
                   "status": {"g1": "completed", "g2": "working"}, "lastNode": "g1",
                   "placements": {}})
        feed = km.build_feed(NOW, {})
        ni = self._needs_input(feed)
        self.assertEqual([a["itemId"] for a in ni], ["g2"],
                         "the still-working top takes the floor when the focus walk dead-ends")
        self.assertEqual((ni[0].get("blocked") or {}).get("state"), "userTodos")
        self.assertNotIn("usertodo:" + SID, [a["itemId"] for a in feed["asks"]],
                         "a floored card means no placeholder")

    def test_the_fallback_still_yields_to_jauth(self):
        # keep every yield rule: with the jauth floor latched on a live focus goal, the
        # fallback never floors a second card for the same session
        self._env({"nodes": {"g1": {"parentId": None, "t": NOW - 900, "text": "ship the fixtures"},
                             "g2": {"parentId": None, "t": NOW - 500, "text": "wire the login flow"}},
                   "status": {"g1": "working", "g2": "working"}, "lastNode": "g1",
                   "placements": {}}, jauth=True)
        ni = self._needs_input(km.build_feed(NOW, {}))
        self.assertEqual(len(ni), 1, "one interrupt story — jauth floors the focus, todos wait")
        self.assertNotEqual((ni[0].get("blocked") or {}).get("state"), "userTodos")

    def test_a_done_confirming_focus_is_never_floored(self):
        # round-2 verification: a top in the rollup's `confirming` export (done verdict filed,
        # settle pending) still reads col 'working' — flooring it fights the settle gate and
        # flaps working→needs-you→completed with no new information. The focus walk skips it;
        # the fallback floors the genuinely working top instead.
        self._env({"nodes": {"g1": {"parentId": None, "t": NOW - 900, "text": "ship the fixtures"},
                             "g2": {"parentId": None, "t": NOW - 500, "text": "wire the login flow"}},
                   "status": {"g1": "working", "g2": "working"}, "lastNode": "g1",
                   "confirming": ["g1"], "placements": {}})
        feed = km.build_feed(NOW, {})
        ni = self._needs_input(feed)
        self.assertEqual([a["itemId"] for a in ni], ["g2"],
                         "the confirming focus belongs to the settle gate, not the floor")
        g1 = next(a for a in feed["asks"] if a["itemId"] == "g1")
        self.assertTrue(g1.get("doneConfirming"), "the skipped focus keeps its steady cue")

    def test_the_fallback_skips_a_confirming_top_too(self):
        # …and the working-top fallback honors the same set: with the one candidate confirming,
        # nothing floors this build — its completion is moments away (the settle), and a floor
        # now would be un-floored by the very next verdict
        self._env({"nodes": {"g1": {"parentId": None, "t": NOW - 900, "text": "ship the fixtures"},
                             "g2": {"parentId": None, "t": NOW - 500, "text": "wire the login flow"}},
                   "status": {"g1": "completed", "g2": "working"}, "lastNode": "g1",
                   "confirming": ["g2"], "placements": {}})
        feed = km.build_feed(NOW, {})
        self.assertEqual(self._needs_input(feed), [],
                         "no floor while the only candidate is done-confirming")
        g2 = next(a for a in feed["asks"] if a["itemId"] == "g2")
        self.assertEqual(g2["column"], "working")
        self.assertTrue(g2.get("doneConfirming"))


class FloorNotificationDedup(_StoreSandbox):
    """Review 2026-08-22: the floor stands down for every turn the session takes and re-arms at
    the settle — the DESIGNED card move — but _feed_notifications read each re-entry as news,
    an OS push per exchange and per monitor wake-cycle for the SAME deferred todo. The interrupt
    is deduplicated at the notification layer, event-keyed on the FLOORED TODO SET: it fires on
    first arm or when a todo id joins the set; an identical set re-entering is not news. The
    latch is _NOTIFY_PREV's own in-memory idiom, kept beside it, so it survives the card's
    Working dips. The CARD move stays exactly as built — only the push is deduplicated."""

    def setUp(self):
        super().setUp()
        km._NOTIFY_PREV[0] = None
        getattr(km, "_NOTIFY_UT_FIRED", [{}])[0].clear()
        patches = [
            mock.patch.object(km, "_notify_card_effective", lambda cards, iid, sid: True),
            mock.patch.object(km, "_prune_notify_cards", lambda live: None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        km._NOTIFY_PREV[0] = None
        getattr(km, "_NOTIFY_UT_FIRED", [{}])[0].clear()
        super().tearDown()

    def _card(self, floored, state="userTodos"):
        blocked = ({"state": state, "count": len(km._open_user_todos(SID)),
                    "what": "waiting on you"} if floored else None)
        return {"asks": [{"itemId": SID + ":g1", "sid": SID, "name": "web",
                          "text": "wire the login flow",
                          "column": "needs_input" if floored else "working",
                          "blocked": blocked}]}

    def test_a_dip_and_re_entry_with_the_same_todo_set_is_not_news(self):
        # the monitor-cycle shape: settle→floor (push), check-in turn→working, settle→floor,
        # …repeated. Exactly ONE notification for the one deferred todo.
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._feed_notifications(self._card(floored=False))          # baseline build
        fired = len(km._feed_notifications(self._card(floored=True)))   # first arm → the one push
        self.assertEqual(fired, 1)
        for _cycle in range(3):                                    # three monitor wake-cycles
            self.assertEqual(km._feed_notifications(self._card(floored=False)), [])
            fired += len(km._feed_notifications(self._card(floored=True)))
        self.assertEqual(fired, 1, "re-entry with an identical todo set is not news")

    def test_a_new_todo_re_arms_the_push(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1)
        km._feed_notifications(self._card(floored=False))          # the session took a turn
        km._add_user_todo(SID, "Need a staging credential for the tests")
        out = km._feed_notifications(self._card(floored=True))
        self.assertEqual(len(out), 1, "a todo id joining the floored set IS news")

    def test_the_dedup_is_scoped_to_the_floor(self):
        # a permission stop that re-enters after an answer is a NEW block — unchanged contract
        # (test_notify_bells.py::test_reblocking_after_an_answer_notifies_again is the master pin)
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(True, state="permission"))), 1)
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(True, state="permission"))), 1,
                         "non-todo cards keep the column-diff contract exactly as before")

    def test_a_restart_baseline_seeds_the_latch_from_the_floored_world(self):
        # round-2 verification (repro test_A): the latch is in-memory and the baseline build
        # returned BEFORE seeding it, so the first dip+re-entry after every kernel restart
        # re-pushed the SAME already-notified todo — one spurious interrupt per floored session
        # per deploy on a self-hosting box. The floored set IS the already-notified state (the
        # card either fired before the restart or was status the baseline declined to push), so
        # the baseline seeds the latch from exactly the cards already floored — event-derived,
        # no persistence file.
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1)
        # KERNEL RESTART: both in-memory latches re-baseline together
        km._NOTIFY_PREV[0] = None
        km._NOTIFY_UT_FIRED[0].clear()
        self.assertEqual(km._feed_notifications(self._card(floored=True)), [],
                         "the boot baseline stays silent — existing state is status, not news")
        self.assertEqual(km._feed_notifications(self._card(floored=False)), [])
        self.assertEqual(km._feed_notifications(self._card(floored=True)), [],
                         "the routine dip+re-entry after a restart is NOT news — the baseline "
                         "seeded the latch from the already-floored card")

    def test_the_baseline_seed_suppresses_only_what_was_already_floored(self):
        # the seed must not oversuppress: a todo the baseline never saw is still news
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        self.assertEqual(km._feed_notifications(self._card(floored=True)), [],
                         "floored at boot — the baseline is silent and seeds the latch")
        km._add_user_todo(SID, "Need a staging credential for the tests")
        self.assertEqual(km._feed_notifications(self._card(floored=False)), [])
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1,
                         "the id that joined AFTER the baseline is news")

    def test_a_new_id_joining_while_floored_pushes_with_no_observed_dip(self):
        # round-2 verification (repro test_C): a second todo registers in a turn too quick for
        # any build to observe the dip — the card is floored in BOTH adjacent builds, so hanging
        # the latch off the column diff short-circuited it and the join never pushed. The
        # todo-set diff is the news test, independent of the column transition.
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1)
        km._add_user_todo(SID, "Need a staging credential for the tests")
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1,
                         "a joining id is news even when no build observed a dip")
        self.assertEqual(km._feed_notifications(self._card(floored=True)), [],
                         "…and exactly once: the steadily floored card stays quiet after it")

    def test_a_lost_answer_reopen_re_arms_the_push(self):
        # round-2 verification (repro test_B): the loss seam reopens the SAME id, so the set
        # dedup ate the re-floor's push forever — but that push is the ONE signal telling the
        # user their answer never arrived (the loss seam's never-quiet doctrine). The loss
        # EVENT clears the id from the latch, so the next floor treats it as news.
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1)
        # the user answers → stamp lands, the card unfloors
        self.assertTrue(km._resolve_user_todo(SID, tid, "answered"))
        self.assertEqual(km._feed_notifications(self._card(floored=False)), [])
        # the answer's holder dies; the loss seam reopens the same id (no transcript → reopen)
        with mock.patch.object(km, "_sessions",
                               lambda now, window=None, forks=True: [{"sid": SID,
                                                                      "path": "/dev/null"}]), \
             mock.patch.object(km, "_parse", lambda path, sid, now: {"turns": []}), \
             contextlib.redirect_stderr(io.StringIO()):
            km._user_todo_answer_lost(SID, tid, "Re: Need the auth-scheme decision — cookie.",
                                      wait=True)
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the loss reopened the ask")
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1,
                         "the re-floor after a LOST answer pushes — never quiet")

    def test_the_users_own_recall_stays_silent(self):
        # the ✕ recall (_cancel_backend_queued) reopens the same id too — but the user pulled
        # the answer back THEMSELVES; an interrupt telling them what they just did is noise.
        # The unlatch keys on the LOSS event alone, so the recall's re-floor stays deduplicated.
        be = _FakeBackend()
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1)
        body = km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                         "Go with the session cookie.")
        self.assertTrue(km._backend_send(be, SID, body, user_todo=tid))
        km._stamp_user_todo_answered(SID, tid, body)
        self.assertEqual(km._feed_notifications(self._card(floored=False)), [])
        self.assertIsNone(km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1]))
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the recall reopened the ask")
        self.assertEqual(km._feed_notifications(self._card(floored=True)), [],
                         "the user's own ✕ needs no interrupt saying what they just did")

    def test_the_latch_writers_share_one_lock(self):
        # the loss seam's unlatch runs THREADED beside the build's read-modify-write; every
        # writer holds _NOTIFY_UT_LOCK, or a stale fire could overwrite a concurrent unlatch
        # (a lost update that re-arms or re-silences the wrong sid)
        for fn in (km._feed_notifications, km._notify_ut_unlatch):
            self.assertIn("with _NOTIFY_UT_LOCK", inspect.getsource(fn),
                          "%s must hold the latch lock around its read-modify-write" % fn.__name__)


class BadgeArithmetic(unittest.TestCase):
    """_needs_you_count widens to 'things only the user can move' (plans/user-todos.md, (d)):
    open user todos of non-ended sessions PLUS hard-stopped needs-input sessions — counted per
    SESSION ('counts once as itself'), with the escalation floor adding nothing (a presentation
    of todos the count already includes). Ended sessions are excluded upstream: the map is built
    behind the ended gate (FeedSeamUserTodos)."""

    def test_todos_plus_hard_stopped_sessions(self):
        feed = {"asks": [{"itemId": "a", "sid": "S1", "column": "needs_input"}],
                "userTodos": {"S2": 2}}
        self.assertEqual(km._needs_you_count(feed), 3)

    def test_the_escalation_floor_adds_nothing_extra(self):
        # an idle session escalated BY its todos: the card is a presentation of the two todos
        # already in the count — never a third thing
        feed = {"asks": [{"itemId": "a", "sid": "S2", "column": "needs_input",
                          "blocked": {"state": "userTodos", "count": 2}}],
                "userTodos": {"S2": 2}}
        self.assertEqual(km._needs_you_count(feed), 2)

    def test_a_hard_stopped_session_with_todos_counts_once_as_itself(self):
        # the spec's dedup rule: the permission stop is its own thing (1) beside the session's
        # own todo (1) — the session's hard stop never counts twice
        feed = {"asks": [{"itemId": "a", "sid": "S1", "column": "needs_input",
                          "blocked": {"state": "permission", "what": "stopped"}}],
                "userTodos": {"S1": 1}}
        self.assertEqual(km._needs_you_count(feed), 2)

    def test_hard_stops_count_per_session_not_per_card(self):
        feed = {"asks": [{"itemId": "a", "sid": "S1", "column": "needs_input"},
                         {"itemId": "b", "sid": "S1", "column": "needs_input"}]}
        self.assertEqual(km._needs_you_count(feed), 1)

    def test_provisional_and_non_blocked_cards_stay_out(self):
        feed = {"asks": [
            {"itemId": "a", "sid": "S1", "column": "needs_input", "provisional": True},
            {"itemId": "b", "sid": "S2", "column": "working"},
            {"itemId": "c", "sid": "S3", "column": "completed"},
        ]}
        self.assertEqual(km._needs_you_count(feed), 0)

    def test_a_sid_less_card_still_counts(self):
        # nothing to dedup it against — dropping it would hide a real needs-you
        feed = {"asks": [{"itemId": "q1", "column": "needs_input"},
                         {"itemId": "q2", "column": "needs_input"}]}
        self.assertEqual(km._needs_you_count(feed), 2)

    def test_held_mail_counts_per_message_beside_a_session_stop(self):
        # review 2026-08-22: quarantine cards are independent user DECISIONS (approve/deny/edit
        # per message), not a state of their session — the per-session dedup absorbed them, so a
        # permission stop + 2 held mails for the same session read badge 1. Three decisions = 3.
        feed = {"asks": [
            {"itemId": "S1:g1", "sid": "S1", "column": "needs_input",
             "blocked": {"state": "permission", "what": "stopped"}},
            {"itemId": "quarantine:m-01", "sid": "S1", "column": "needs_input",
             "blocked": {"state": "quarantine", "mid": "m-01"}},
            {"itemId": "quarantine:m-02", "sid": "S1", "column": "needs_input",
             "blocked": {"state": "quarantine", "mid": "m-02"}},
        ]}
        self.assertEqual(km._needs_you_count(feed), 3)

    def test_parked_handoffs_count_per_send(self):
        # two handoffs parked for the same offline recipient are two deliver-or-dismiss calls
        feed = {"asks": [
            {"itemId": "parked:m-01", "sid": "S9", "column": "needs_input",
             "blocked": {"state": "parkedHandoff", "toSid": "S9"}},
            {"itemId": "parked:m-02", "sid": "S9", "column": "needs_input",
             "blocked": {"state": "parkedHandoff", "toSid": "S9"}},
        ]}
        self.assertEqual(km._needs_you_count(feed), 2)

    def test_the_per_item_classes_are_the_feeds_own(self):
        # the class list is enumerated from build_feed's needs-input constructors — goal cards
        # and the provisional placeholders are session-state; these two are the per-item ones.
        # A constructor whose state leaves this list dedups by sid, so drift shows up here.
        self.assertEqual(set(km._NEEDS_YOU_PER_ITEM), {"quarantine", "parkedHandoff"})
        src = inspect.getsource(km.build_feed) + inspect.getsource(km._quarantine_cards)
        for st in km._NEEDS_YOU_PER_ITEM:
            self.assertIn('"state": "%s"' % st, src, "the class must name a real constructor")

    def test_an_empty_feed_is_zero(self):
        self.assertEqual(km._needs_you_count({"asks": []}), 0)
        self.assertEqual(km._needs_you_count({}), 0)


class NudgeStandsDownForOpenTodos(_StoreSandbox):
    """The auto-nudge's open-todo gate is scoped to the STATUS NUDGE alone (plans/user-todos.md,
    escalation; review 2026-08-22): the todo says exactly what a status check would fish for, so
    none fires while one stands — but two unrelated ladders share this walk and must flow past
    it. The awaiting WAKE is the 6h LOST-WAKEUP backstop (suppressing it re-creates the
    2026-08-11 wedge: dispatched background work whose completion wakeup died, asleep in Awaiting
    for days), and the DEBT machinery is the ONE mechanism that unparks a PEER silently waiting
    on this session's answer — a todo names what THIS session needs from the user and says
    nothing about what a peer needs from it. The first cut returned at session level and
    silenced all three. SYNTHETIC fixtures (the notes-api world)."""

    S = {"sid": SID, "name": "web", "path": "/nonexistent/%s.jsonl" % SID, "anchor": 0, "mtime": 0}
    TURNS = [{"id": "t1", "t": NOW - 600, "end": NOW - 500, "ended": True, "atoms": []}]

    def setUp(self):
        super().setUp()
        self.saved_goaldir = jd.GOALDIR
        jd.GOALDIR = jd.STATE / "goals"
        jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        km._autonudge_cache.clear()
        km._SESSION_STAMP_CACHE.clear()
        km._flags_cache.clear()
        self.sent = []
        rec = self

        class _Backend:
            def send(self, sid, body):
                rec.sent.append((sid, body))
                return True

        self.saved_backend = km.Sessions.backend_for
        km.Sessions.backend_for = staticmethod(lambda sid: _Backend())
        patches = [
            mock.patch.object(km, "_api_error", lambda path: None),
            mock.patch.object(jd, "parsed_session",
                              lambda sid, paths, now: {"turns": list(self.TURNS)}),
            mock.patch.object(km, "_session_working", lambda turns: False),
            mock.patch.object(km, "_interrupt_suppresses_nudge", lambda turns, s="", **k: False),
            mock.patch.object(km, "_backend_queued", lambda s: False),
            mock.patch.object(km, "_backend_rewind_pending", lambda s: False),
            mock.patch.object(km, "_last_state", lambda s: ("waiting", 0)),
            mock.patch.object(km, "_session_awaiting",
                              lambda sid, path, idle, stamp=False: None),
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
            {"rompUuid": SID, "seq": 1, "placements": {}, "status": status or {},
             "nodes": nodes}))

    def _plain_top(self):
        return {"g1": {"id": "g1", "text": "wire the login flow", "parentId": None,
                       "t": NOW - 900, "mt": NOW - 900, "nodeComplete": False,
                       "blocked": False, "cleared": False, "trail": []}}

    def _stamped_top(self, at):
        nd = {"id": "g1", "text": "run the fixture sweep", "parentId": None,
              "t": NOW - 90000, "mt": NOW - 90000, "nodeComplete": False, "blocked": False,
              "cleared": False, "trail": [],
              "awaitingWhy": "the sweep it dispatched; reports when done", "awaitingAt": at,
              "log": [{"ev_t": at, "src": "closer", "kind": "awaiting",
                       "why": "the sweep it dispatched; reports when done", "at": at + 5}]}
        return {"g1": nd}

    def _run(self, alive_ids=None):
        km._autonudge_cache.clear()
        km._SESSION_STAMP_CACHE.clear()
        return km._auto_nudge_session(self.S, NOW, {SID: {"state": ""}}, {}, {},
                                      alive_ids=alive_ids)

    def test_the_status_nudge_stands_down_while_a_todo_is_open(self):
        self._seed_goals(self._plain_top(), status={"g1": "working"})
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        self.assertFalse(self._run())
        self.assertEqual(self.sent, [], "the todo already names what a status check would ask")
        self.assertEqual(km._auto_nudge_data().get("nudged", {}), {}, "no record armed either")

    def test_the_gate_lifts_the_moment_the_last_todo_clears(self):
        self._seed_goals(self._plain_top(), status={"g1": "working"})
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._resolve_user_todo(SID, tid, "dismissed")
        self.assertTrue(self._run(), "with no open todos the status nudge proceeds as before")
        self.assertEqual(len(self.sent), 1)

    def test_the_awaiting_wake_flows_past_an_open_todo(self):
        # the awaiting-wedge shape (2026-08-11): a stamped goal past the 6h backstop whose
        # completion wakeup died. The wake is a lost-wakeup CHECK, not a status ask — an open
        # todo must not put the session back to sleep for days.
        self._seed_goals(self._stamped_top(at=NOW - 7 * 3600), status={"g1": "working"})
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        self.assertTrue(self._run(), "the wake fired despite the open todo")
        self.assertEqual(len(self.sent), 1)
        self.assertTrue(km._auto_nudge_data()["nudged"]["g1"].get("wake"),
                        "…and it is the WAKE's episode record, not a status nudge's")

    def test_the_debt_machinery_flows_past_an_open_todo(self):
        # the peer-parked-forever shape: this idle session owes a live peer a reply ("Awaiting
        # us" on their card). The debt reminder is the one mechanism that unparks them; a todo
        # about the USER must not silence it.
        self._seed_goals({}, status={})
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        t_ask = NOW - 1800
        maps = ({(SID2, SID): t_ask},
                {(SID2, SID): (t_ask, "question", "Which port should the staging server use?")})
        patches = [
            mock.patch.object(km, "_postal_wait_maps", lambda: maps),
            mock.patch.object(km, "_name_of", lambda sid: {SID2: "api", SID: "web"}.get(sid)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.assertTrue(self._run(alive_ids={SID, SID2}), "the reminder fired despite the todo")
        self.assertEqual(len(self.sent), 1)
        self.assertIn("api asked you", self.sent[0][1])


if __name__ == "__main__":
    unittest.main()
