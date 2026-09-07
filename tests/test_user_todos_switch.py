#!/usr/bin/env python3
"""The USER TODOS feature switch (the user 2026-09-03): "Waiting on you" is switchable, DEFAULT OFF,
per install — STATE/user-todos-enabled.json = {"enabled": bool, "gt": ms}, the file-editing /
thinking-summaries idiom exactly (gesture-clock stand-down, settingStale reply, atomic write, loud
write failure). NOT user-todos.json: that file is the todo STORE (sid → records), and a settings
blob written there once destroyed a live ledger — so the store now guards its own shape.

Pinned here, kernel side:
- the helpers: absent / garbled / false all read OFF, the setter writes value + stamp, a stale
  gesture stands down loudly and keeps the stored value, an unstamped apply arms the store, a
  failed write is loud and applies nothing, and _setting_kept_value words the stale reply;
- the WS op setUserTodos (beside setThinkingSummaries), /version's top-level `userTodos`, and the
  PER-INSTALL contract: no propagation table names it (federation's KERNEL_SETTING is pinned on the
  node side, user-todos-switch.test.ts);
- what OFF does on each kernel surface, each loud: POST /usertodo and /usertodo/withdraw answer
  409 with a one-line reason and write nothing; /usertodo/context answers enabled:false with an
  empty block; userTodoAnswer / userTodoDismiss warn and inject / stamp nothing; and the payloads
  every UI surface reads ship EMPTY — build_session's field + split-card event, build_feed's map —
  because _open_user_todos is the one gated read (the nudge stand-down and the escalation floor
  read it too). The store keeps every row; ON shows them again;
- the sig folds: a flip busts the owning session's chat cache and the feed cache with no store write;
- the boot notice: N open rows stored while OFF → one stderr line; ON, or zero rows → silence;
- the store-shape guard: a user-todos.json that is not sid → list (a settings blob, a JSON list,
  unparsable text) reads as EMPTY, says so once per file version, and every writer REFUSES to
  overwrite that version (fail loudly, never silently replace) until the file is fixed or removed.

SYNTHETIC fixtures only: placeholder UUIDs, the notes-api demo world.
"""
import contextlib
import inspect
import io
import json
import os
import tempfile
import types
import unittest
from romp_load import load_source
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model_utsw", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge_utsw", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_SERVE_TOKEN"] = "testtok"
km = load_source("romp_kernel_utsw", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
SID2 = "22222222-3333-4444-5555-666666666666"
NOW = 1781200000
T_OLD, T_NEW = 1_700_000_000_000, 1_700_000_060_000


class _Sandbox(unittest.TestCase):
    """Per-test STATE sandbox + cache reset — the _StoreSandbox idiom of test_user_todos.py. The
    switch file is ABSENT at the start of every test: that is the shipped default, OFF."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = Path(self.td.name)
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()

    def tearDown(self):
        jd.STATE = self.saved
        self.td.cleanup()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()

    @property
    def switch(self):
        return jd.STATE / km.USER_TODOS_SWITCH_FILE


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


def _post(path, body):
    code, out = _serve_post(path, body, {"X-Romp-Token": km.TOKEN})
    try:
        return code, json.loads(out.decode() or "{}")
    except ValueError:
        return code, {}


class TheSwitch(_Sandbox):
    def test_the_file_is_not_the_store(self):
        self.assertEqual(km.USER_TODOS_SWITCH_FILE, "user-todos-enabled.json")
        self.assertNotEqual(km.USER_TODOS_SWITCH_FILE, "user-todos.json",
                            "user-todos.json is the todo STORE — a setting written there corrupts it")

    def test_absent_is_off_the_shipped_default(self):
        self.assertFalse(self.switch.exists())
        self.assertFalse(km._user_todos_on())
        self.assertFalse(self.switch.exists(), "reading never creates the file")

    def test_garbled_or_false_reads_off(self):
        self.switch.write_text("not json")
        self.assertFalse(km._user_todos_on())
        self.switch.write_text(json.dumps(["enabled"]))
        self.assertFalse(km._user_todos_on())
        self.switch.write_text(json.dumps({"enabled": False, "gt": 5}))
        self.assertFalse(km._user_todos_on())

    def test_the_setter_writes_value_and_stamp_and_the_reader_sees_it(self):
        self.assertEqual(km._set_user_todos(True, gt=T_OLD), T_OLD)
        self.assertEqual(json.loads(self.switch.read_text()), {"enabled": True, "gt": T_OLD})
        self.assertTrue(km._user_todos_on())
        self.assertEqual(km._set_user_todos(False, gt=T_NEW), T_NEW)
        self.assertFalse(km._user_todos_on())

    def test_a_stale_gesture_stands_down_loudly_and_keeps_the_stored_value(self):
        km._set_user_todos(True, gt=T_NEW)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIsNone(km._set_user_todos(False, gt=T_OLD))
        self.assertTrue(km._user_todos_on(), "the newer choice survives the stale flush")
        self.assertIn("user-todos", err.getvalue())
        self.assertIn("stale gesture stood down", err.getvalue())
        self.assertEqual(km._pop_stale_notice(), {"setting": "user-todos", "storedGt": T_NEW},
                         "the stand-down is recorded for the settingStale reply")

    def test_equal_stamps_keep_the_stored_value(self):
        km._set_user_todos(True, gt=T_NEW)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(km._set_user_todos(False, gt=T_NEW))
        self.assertTrue(km._user_todos_on())

    def test_an_unstamped_apply_arms_the_store_against_stale_flushes(self):
        stamp = km._set_user_todos(True)
        self.assertIsInstance(stamp, int)
        self.assertGreater(stamp, T_NEW, "an unstamped set records its arrival time")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(km._set_user_todos(False, gt=T_OLD), "an old flush cannot walk it back")
        self.assertTrue(km._user_todos_on())

    def test_a_file_without_the_field_reads_as_gt_zero(self):
        self.switch.write_text(json.dumps({"enabled": True}))
        self.assertEqual(km._set_user_todos(False, gt=1), 1, "any stamped gesture applies over it")
        self.assertFalse(km._user_todos_on())

    def test_a_failed_write_is_loud_none_and_applies_nothing(self):
        km._set_user_todos(True, gt=T_OLD)
        err = io.StringIO()
        with mock.patch.object(km, "_atomic_write", side_effect=OSError("disk full")), \
                contextlib.redirect_stderr(err):
            self.assertIsNone(km._set_user_todos(False, gt=T_NEW))
        self.assertIn("setting user-todos: write failed", err.getvalue())
        self.assertTrue(km._user_todos_on(), "the stored choice survives the failed write")
        self.assertIsNone(km._pop_stale_notice(), "an OSError is not a stand-down: no stale frame")

    def test_the_stale_reply_words_the_kept_value(self):
        self.assertIs(km._setting_kept_value("user-todos"), False)
        km._set_user_todos(True)
        self.assertIs(km._setting_kept_value("user-todos"), True)


class TheWsOpAndVersion(_Sandbox):
    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s)), "alive": True}
        self._dirty = km._mark_views_dirty
        self.dirtied = []
        km._mark_views_dirty = lambda: self.dirtied.append(True)

    def tearDown(self):
        km._mark_views_dirty = self._dirty
        super().tearDown()

    def dispatch(self, msg):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km.Handler._dispatch_ws(types.SimpleNamespace(), msg, self.client)
        return err.getvalue()

    def test_setUserTodos_applies_and_repaints(self):
        self.dispatch({"type": "setUserTodos", "enabled": True, "gt": T_OLD})
        self.assertTrue(km._user_todos_on())
        self.assertEqual(json.loads(self.switch.read_text())["gt"], T_OLD, "the gesture stamp lands")
        self.assertEqual(self.dirtied, [True], "a flip changes every payload with no store write: repaint now")
        self.assertEqual(self.sent, [], "a clean apply sends nothing back")

    def test_a_stale_setUserTodos_answers_the_delivering_socket_with_settingStale(self):
        self.dispatch({"type": "setUserTodos", "enabled": True, "gt": T_NEW})
        self.dispatch({"type": "setUserTodos", "enabled": False, "gt": T_OLD})
        self.assertTrue(km._user_todos_on())
        stale = [m for m in self.sent if m.get("type") == "settingStale"]
        self.assertEqual(stale, [{"type": "settingStale", "setting": "user-todos", "storedGt": T_NEW, "kept": True}])
        self.assertEqual(len(self.dirtied), 1, "a stood-down gesture repaints nothing — no new information")

    def test_a_full_disk_toggle_does_not_tear_the_ws_down(self):
        with mock.patch.object(km, "_atomic_write", side_effect=OSError("disk full")):
            try:
                err = self.dispatch({"type": "setUserTodos", "enabled": True, "gt": T_NEW})
            except OSError:
                self.fail("an OSError escaped _dispatch_ws — the reader loop reads it as a socket failure")
        self.assertIn("user-todos", err)
        self.assertTrue(self.client["alive"])
        self.assertFalse(km._user_todos_on())

    def test_a_valueless_op_is_ignored(self):
        self.dispatch({"type": "setUserTodos"})
        self.assertFalse(self.switch.exists())

    def test_version_reports_the_switch_top_level_beside_thinking_summaries(self):
        for want in (False, True):
            km._set_user_todos(want)
            v = km._version_info()
            self.assertIs(v["userTodos"], want)
            self.assertIn("thinkingSummaries", v)
        self.assertNotIn("userTodos", v["settings"],
                         "per-install like thinkingSummaries: not in the mesh-comparison dict (never a 'mixed' mark)")

    def test_per_install_no_propagation_table_names_it(self):
        src = inspect.getsource(km)
        self.assertNotIn('"userTodos", _set_user_todos', src, "the /judge-settings propagation shape")
        self.assertNotIn("_propagate_judge_settings(\"user-todos\"", src)
        # the dispatcher says so where the op is handled
        at = src.index('msg.get("type") == "setUserTodos"')
        self.assertIn("NOT in federation.ts's KERNEL_SETTING", src[at:at + 900])


class OffOnTheRoutes(_Sandbox):
    """POST /usertodo and /usertodo/withdraw refuse with a 409 + one-line reason while OFF; the store
    is untouched; /usertodo/context says enabled:false with an empty block. ON: as before."""

    def setUp(self):
        super().setUp()
        self._push = (km._push_all, km._push_soon)
        self.pushed = []
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(AssertionError("synchronous _push_all"))
        km._push_soon = lambda: self.pushed.append(True)

    def tearDown(self):
        km._push_all, km._push_soon = self._push
        super().tearDown()

    def test_register_is_refused_409_and_writes_nothing(self):
        code, res = _post("/usertodo", {"id": SID, "text": "Need the auth-scheme decision"})
        self.assertEqual(code, 409)
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "user todos are turned off on this machine")
        self.assertFalse((jd.STATE / "user-todos.json").exists(), "nothing written")
        self.assertEqual(self.pushed, [], "nothing changed, nothing to push")

    def test_shape_errors_still_come_first(self):
        self.assertEqual(_post("/usertodo", {"id": SID})[0], 400)
        self.assertEqual(_post("/usertodo/withdraw", {"id": SID})[0], 400)

    def test_withdraw_is_refused_409_and_the_row_stays_open(self):
        km._set_user_todos(True)
        _, res = _post("/usertodo", {"id": SID, "text": "Need the staging port"})
        tid = res["todoId"]
        km._set_user_todos(False)
        code, out = _post("/usertodo/withdraw", {"id": SID, "todoId": tid})
        self.assertEqual(code, 409)
        self.assertFalse(out["ok"])
        self.assertIn("turned off on this machine", out["error"])
        row = km._user_todos()[SID][0]
        self.assertNotIn("resolved", row, "the ask still stands in the store")

    def test_context_answers_enabled_false_and_an_empty_block_despite_open_rows(self):
        km._set_user_todos(True)
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        code, res = _post("/usertodo/context", {"id": SID})
        self.assertEqual((code, res["enabled"]), (200, True))
        self.assertIn("Notes you still have open", res["block"])
        km._set_user_todos(False)
        code, res = _post("/usertodo/context", {"id": SID})
        self.assertEqual(code, 200, "a read: OFF is an honest 200, not an error")
        self.assertIs(res["enabled"], False)
        self.assertEqual(res["block"], "", "the hook injects nothing")

    def test_turning_it_back_on_shows_the_stored_rows_again(self):
        km._set_user_todos(True)
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        km._set_user_todos(False)
        self.assertEqual(km._open_user_todos(SID), [])
        km._set_user_todos(True)
        self.assertEqual([t["id"] for t in km._open_user_todos(SID)], [tid], "kept on disk the whole time")

    def test_on_the_routes_work_as_before(self):
        km._set_user_todos(True)
        code, res = _post("/usertodo", {"id": SID, "text": "Need the fixture format pick"})
        self.assertEqual((code, res["ok"]), (200, True))
        code, out = _post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        self.assertEqual((code, out["ok"]), (200, True))


class OffOnTheDriveOps(_Sandbox):
    """userTodoAnswer / userTodoDismiss warn (the op's typed failure) and touch nothing while OFF —
    a dashboard can still show a row it was handed before the switch flipped."""

    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}
        self._saved = (km._name_of, km._sdk, km._send_or_park, km._push_soon)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        self.injected = []
        km._send_or_park = lambda be, sid, text, echo=None, user_todo=None: self.injected.append((sid, text)) or True
        km._push_soon = lambda: None
        km._set_user_todos(True)
        self.tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._set_user_todos(False)

    def tearDown(self):
        km._name_of, km._sdk, km._send_or_park, km._push_soon = self._saved
        super().tearDown()

    def _warns(self):
        return [m for m in self.sent if m.get("type") == "warn"]

    def test_answer_warns_and_injects_nothing(self):
        handled = km._drive({"type": "userTodoAnswer", "id": SID, "todoId": self.tid, "text": "OAuth"}, self.client)
        self.assertTrue(handled)
        self.assertEqual(self.injected, [])
        self.assertEqual(len(self._warns()), 1)
        self.assertIn("turned off on this machine", self._warns()[0]["text"])
        self.assertNotIn("already settled", self._warns()[0]["text"],
                         "the switch is named — not the stale-row story the gated read would suggest")
        self.assertNotIn("resolved", km._user_todos()[SID][0])

    def test_dismiss_warns_and_stamps_nothing(self):
        km._drive({"type": "userTodoDismiss", "id": SID, "todoId": self.tid}, self.client)
        self.assertEqual(len(self._warns()), 1)
        self.assertIn("turned off on this machine", self._warns()[0]["text"])
        self.assertNotIn("resolved", km._user_todos()[SID][0])

    def test_on_again_the_same_gestures_land(self):
        km._set_user_todos(True)
        km._drive({"type": "userTodoDismiss", "id": SID, "todoId": self.tid}, self.client)
        self.assertEqual(self._warns(), [])
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed")


class OffOnThePayloads(unittest.TestCase):
    """The kernel ships NO rows while OFF, so the client needs no logic of its own: build_session's
    `userTodos` field is [] and no split-card event carries rows; build_feed's map is {}. ON: the
    same store fills both. _open_user_todos is the one gated read."""

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
        km._user_todos_bad.clear()
        rows = [
            {"type": "user", "uuid": "u1", "timestamp": "2026-06-01T00:00:00Z",
             "sessionId": SID, "message": {"role": "user", "content": "wire the login routes"}},
            {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "timestamp": "2026-06-01T00:00:05Z",
             "sessionId": SID,
             "message": {"role": "assistant", "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": "starting on the open routes"}]}},
        ]
        self.tpath.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        km._set_user_todos(True)
        self.tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", "OAuth vs cookie")
        km._set_user_todos(False)

    def tearDown(self):
        (jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATE, km.NAMES,
         km._read_task_store, km._tmux_sessions, km._GLOBAL_CLAUDE_MD) = self.saved
        km._parse_cache.clear()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        self.td.cleanup()

    def _todo_events(self, payload):
        return [e for e in payload["events"] if e.get("kind") == "todo"]

    def test_build_session_ships_an_empty_field_and_no_rows_while_off(self):
        payload = km.build_session(SID, NOW)
        self.assertEqual(payload["userTodos"], [])
        self.assertEqual(self._todo_events(payload), [], "no split card either: the section has nothing to show")
        self.assertEqual(len(km._user_todos()[SID]), 1, "…while the store still holds the row")

    def test_the_same_build_shows_the_row_once_on(self):
        km._set_user_todos(True)
        km._parse_cache.clear()
        payload = km.build_session(SID, NOW)
        self.assertEqual([t["id"] for t in payload["userTodos"]], [self.tid])
        self.assertEqual(self._todo_events(payload)[0]["userTodos"], payload["userTodos"])

    def test_a_flip_busts_the_owning_sessions_chat_cache(self):
        # the chat sig folds this sid's rows (_user_todo_fp); a flip changes the card with no store
        # write, so the fold must change too — or a background tab keeps painting the stale card
        off = km._user_todo_fp(SID)
        km._set_user_todos(True)
        on = km._user_todo_fp(SID)
        self.assertNotEqual(off, on)
        self.assertEqual(on, km._user_todo_fp(SID), "byte-stable while the switch holds")
        self.assertIsNone(km._user_todo_fp(SID2), "a sid with no rows is untouched by the switch")

    def test_build_feed_ships_an_empty_map_while_off_and_the_counts_once_on(self):
        sessions = [{"sid": SID, "name": "web", "path": "/nonexistent/%s.jsonl" % SID, "anchor": 0, "mtime": 0}]
        with mock.patch.object(km, "_alive_sessions", lambda now, tmux: list(sessions)), \
                mock.patch.object(km, "_warm_fleet_bg", lambda now: None):
            self.assertEqual(km.build_feed(NOW, {}).get("userTodos"), {})
            km._set_user_todos(True)
            self.assertEqual(km.build_feed(NOW, {}).get("userTodos"), {SID: 1})

    def test_the_feed_sig_watches_the_switch_file(self):
        with mock.patch.object(km, "_alive_sessions", lambda now, tmux: []), \
                mock.patch.object(km, "_warm_fleet_bg", lambda now: None):
            before = km._fleet_view_sig(NOW, {})
            km._set_user_todos(True)
            after = km._fleet_view_sig(NOW, {})
        self.assertNotEqual(before, after)

    def test_open_user_todos_is_the_one_gated_read(self):
        src = inspect.getsource(km._open_user_todos)
        self.assertIn("if not _user_todos_on():\n        return []", src)
        self.assertEqual(km._open_user_todos(SID), [])
        # the nudge stand-down and the escalation floor read it (grep-provable wiring)
        ksrc = inspect.getsource(km)
        self.assertIn("_todo_standdown = bool(_open_user_todos(sid))", ksrc)
        self.assertIn("_ut_open = _open_user_todos(fsid)", ksrc)


class BootNotice(_Sandbox):
    def _notice(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            n = km._user_todos_off_boot_notice()
        return n, err.getvalue()

    def test_open_rows_behind_an_off_switch_are_announced_once(self):
        km._set_user_todos(True)
        km._add_user_todo(SID, "Need the auth-scheme decision")
        km._add_user_todo(SID2, "Need the staging port")
        tid = km._add_user_todo(SID2, "Need your pick of the two layouts")
        km._resolve_user_todo(SID2, tid, "withdrawn")
        km._set_user_todos(False)
        n, err = self._notice()
        self.assertEqual(n, 2, "open rows only")
        self.assertIn("2 user todo(s) are stored but the feature is off", err)
        self.assertIn("Turn it on in the gear", err)

    def test_silent_when_on_or_when_nothing_is_stored(self):
        self.assertEqual(self._notice(), (0, ""))
        km._set_user_todos(True)
        km._add_user_todo(SID, "Need the auth-scheme decision")
        self.assertEqual(self._notice(), (0, ""), "ON: the rows are visible, nothing to announce")

    def test_wired_into_main_after_the_loss_boot_pass(self):
        src = inspect.getsource(km.main)
        self.assertIn("_user_todos_off_boot_notice()", src)
        self.assertLess(src.index("_user_todo_loss_boot_pass"), src.index("_user_todos_off_boot_notice"),
                        "the loss pass may reopen rows first; the count then reflects them")
        self.assertLess(src.index("_user_todos_off_boot_notice"), src.index("_boot_warm()"))


class StoreShapeGuard(_Sandbox):
    """user-todos.json is the STORE. A file there that is not sid → list reads as empty, loudly,
    and no writer may overwrite that version: the incident was the switch's settings blob written
    into the store by hand, and the next register would have replaced the whole ledger."""

    def setUp(self):
        super().setUp()
        km._set_user_todos(True)
        self.store = jd.STATE / "user-todos.json"

    def _read(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            d = km._user_todos()
        return d, err.getvalue()

    def test_a_settings_blob_in_the_store_reads_empty_and_loud_once_per_version(self):
        self.store.write_text(json.dumps({"enabled": True, "gt": 1}))
        d, err = self._read()
        self.assertEqual(d, {})
        self.assertIn("is not a todo store", err)
        self.assertIn("enabled, gt", err, "names what it found")
        self.assertIn("user-todos-enabled.json", err, "…and where the switch actually lives")
        self.assertIn("refusing to overwrite", err)
        km._user_todos_cache.clear()
        self.assertEqual(self._read(), ({}, ""), "the same file version is not re-announced")

    def test_every_writer_refuses_to_overwrite_the_flagged_version(self):
        self.store.write_text(json.dumps({"enabled": True, "gt": 1}))
        before = self.store.read_text()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(RuntimeError):
                km._add_user_todo(SID, "Need the auth-scheme decision")
            with self.assertRaises(RuntimeError):
                km._resolve_user_todo(SID, "ut-deadbeef", "dismissed") or km._write_user_todos({SID: []})
        self.assertEqual(self.store.read_text(), before, "the unreadable ledger is intact")

    def test_the_register_route_fails_loudly_never_a_200(self):
        self.store.write_text(json.dumps({"enabled": True, "gt": 1}))
        before = self.store.read_text()
        saved = (km._push_all, km._push_soon)
        km._push_all = km._push_soon = lambda *a, **k: None
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                code, _ = _post("/usertodo", {"id": SID, "text": "Need the auth-scheme decision"})
        finally:
            km._push_all, km._push_soon = saved
        self.assertNotEqual(code, 200, "the bus must not echo 'saved' back to the agent")
        self.assertEqual(self.store.read_text(), before)

    def test_unparsable_text_and_a_json_list_are_guarded_the_same_way(self):
        for junk in ("not json", json.dumps([{"id": "ut-1"}]), json.dumps({SID: {"id": "ut-1"}})):
            km._user_todos_cache.clear(); km._user_todos_bad.clear()
            self.store.write_text(junk)
            d, err = self._read()
            self.assertEqual(d, {}, junk)
            self.assertIn("is not a todo store", err, junk)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(RuntimeError):
                km._write_user_todos({})

    def test_a_shaped_store_is_never_flagged(self):
        self.store.write_text(json.dumps({SID: [{"id": "ut-1", "text": "x", "createdT": 1}], SID2: []}))
        d, err = self._read()
        self.assertEqual(err, "")
        self.assertEqual(set(d), {SID, SID2})
        self.assertEqual(km._user_todos_bad, {})
        km._add_user_todo(SID, "Need the staging port")           # writes go through
        self.assertEqual(len(km._user_todos()[SID]), 2)

    def test_the_empty_store_and_a_missing_file_are_shaped(self):
        self.assertTrue(km._user_todo_store_shaped({}))
        self.assertEqual(self._read(), ({}, ""))
        km._add_user_todo(SID, "Need the staging port")
        self.assertEqual(len(km._user_todos()[SID]), 1)

    def test_fixing_or_removing_the_file_lets_writes_through_again(self):
        self.store.write_text(json.dumps({"enabled": True, "gt": 1}))
        with contextlib.redirect_stderr(io.StringIO()):
            self._read()
            with self.assertRaises(RuntimeError):
                km._add_user_todo(SID, "x")
            self.store.unlink()                                  # removed: nothing left to protect
            tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        self.assertEqual(km._user_todos()[SID][0]["id"], tid)
        self.assertEqual(km._user_todos_bad, {}, "a shaped read clears the flag")

    def test_the_boot_notice_and_the_gated_read_survive_a_corrupt_store(self):
        self.store.write_text(json.dumps({"enabled": True, "gt": 1}))
        km._set_user_todos(False)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todos_off_boot_notice(), 0)
            self.assertEqual(km._open_user_todos(SID), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
