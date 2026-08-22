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
  its marker hygiene (a "<!-- romp-…" lookalike in either half is neutralized).

SYNTHETIC fixtures only: placeholder UUIDs, the notes-api demo world.
"""
import inspect
import io
import json
import os
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
            seen.append(km._user_todos_lock.locked())
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
        km._user_todo_recalls.clear()

    def tearDown(self):
        km._name_of, km._sdk, km._send_or_park = self._saved
        km._user_todo_recalls.clear()
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


class _FakeBackend:
    """A forwards_sends backend double for the park/drain/recall pipeline: send() records and
    reports what the test scripts; pending_queued/unqueue model the SDK's recallable queue."""

    def __init__(self, send_ok=True):
        self.sent = []
        self.send_ok = send_ok
        self.queue = []

    def forwards_sends(self):
        return True

    def send(self, sid, text):
        if not self.send_ok:
            return False
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
        km._user_todo_recalls.clear()
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}

    def tearDown(self):
        km._name_of, km._sdk, km._compacting_now = self._saved[:3]
        km._pending_ops.clear()
        km._pending_ops.update(self._saved[3])
        km._user_todo_recalls.clear()
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
        # bubble's ✕ can still recall it before it forwards — the recall must re-open the todo
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        body = km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                         "Go with the session cookie.")
        be = _FakeBackend()
        be.send(SID, body)                            # the delivered-now path…
        km._stamp_user_todo_answered(SID, tid, body)  # …stamps and records the recall key
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err, "the unqueue succeeds")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "recalled before it forwarded → the ask stands again")
        self.assertEqual(km._user_todo_recalls, {}, "the recall key is spent")

    def test_reopen_never_lifts_a_dismiss_or_withdraw(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "dismissed")
        self.assertFalse(km._reopen_user_todo(SID, tid),
                         "only an 'answered' stamp — a failed delivery — may be lifted")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed")


class NoJudgeWritesTheStore(unittest.TestCase):
    """The authority tier, grep-provable (docs/adr/0001): nothing in judge.py names the store or
    its writers — every eraser in the three holes acts by inference, and this object exists to
    survive inference."""

    def test_judge_py_never_touches_user_todos(self):
        src = (Path(HERE).parent / "kernel" / "judge.py").read_text()
        for token in ("user-todos.json", "_user_todos", "_add_user_todo", "_resolve_user_todo"):
            self.assertNotIn(token, src)


if __name__ == "__main__":
    unittest.main()
