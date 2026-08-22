#!/usr/bin/env python3
"""User todos (plans/user-todos.md; docs/adr/0001): a need an agent registers with the person it
works for — a decision, input, or action only they can provide — held open while the agent keeps
working. Exactly three events clear one: the user answers, the user dismisses, or the agent
withdraws. Nothing that reasons by inference may write the store (the authority tier).

Covered here, kernel-side:
- the store (user-todos.json under STATE): round-trip, stamps-not-deletes, sid-keying, id
  stability, the loud unknown-id refusal, the mtime-cache, the prune sweep;
- the POST routes (/usertodo, /usertodo/withdraw) incl. route auth, driven over the fake-socket
  harness (the auth-hardening idiom: ask the real dispatcher, don't pin source positions);
- build_session's `userTodos` field + the split-card `todo` event that carries the rows (the
  chatTail wire re-sends changed EVENTS only, so the rows must ride the event), clock-invariant
  per the serialized-payload dedup rule;
- the ended gate (registry alive:false hides, revive returns them — hidden, not cleared);
- the two drive ops (userTodoAnswer / userTodoDismiss) and the injected answer body's shape.

SYNTHETIC fixtures only: placeholder UUIDs, the notes-api demo world.
"""
import inspect
import io
import json
import os
import tempfile
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


class PruneSweep(_StoreSandbox):
    def test_gone_sids_leave_and_known_sids_stay(self):
        km._add_user_todo(SID, "keep me")
        km._add_user_todo(SID2, "drop me")
        km._prune_user_todos({SID})
        self.assertEqual(set(km._user_todos()), {SID})

    def test_resolved_records_ride_with_their_session(self):
        tid = km._add_user_todo(SID, "answered but kept")
        km._resolve_user_todo(SID, tid, "answered")
        km._prune_user_todos({SID})
        self.assertEqual(len(km._user_todos()[SID]), 1)

    def test_a_noop_prune_never_writes(self):
        km._add_user_todo(SID, "still here")
        p = jd.STATE / "user-todos.json"
        before = p.stat().st_mtime_ns
        km._prune_user_todos({SID})
        self.assertEqual(p.stat().st_mtime_ns, before, "nothing gone → no write (no hot-path churn)")

    def test_the_sweep_rides_the_tab_session_gc(self):
        # the same known-set _gc_session_order cleans by — GONE means neither alive nor in the
        # discover window, so a dead-but-revivable session keeps its todos
        src = inspect.getsource(km._chat_tab_sessions)
        self.assertIn("_prune_user_todos", src)


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
        self._push_all = km._push_all
        km._push_all = lambda *a, **k: None            # route handlers push; tests don't build views

    def tearDown(self):
        km._push_all = self._push_all
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


class DriveOps(_StoreSandbox):
    """userTodoAnswer / userTodoDismiss — the user's two gestures on the split card."""

    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}
        self._saved = (km._name_of, km._sdk, km._send_or_park)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        self.injected = []
        km._send_or_park = lambda be, sid, text, echo=None: self.injected.append((sid, text))

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

    def test_answer_injects_the_anchored_reply_and_stamps_at_the_send(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Go with the session cookie for now."}, self.client)
        self.assertEqual(len(self.injected), 1)
        self.assertEqual(self.injected[0][0], SID)
        self.assertEqual(self.injected[0][1],
                         "Re: Need the auth-scheme decision to wire login — "
                         "Go with the session cookie for now.")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "stamped at the send — the user's gesture, never a judgment")

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
