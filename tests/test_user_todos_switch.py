#!/usr/bin/env python3
"""The Requests switch (plans/user-todos.md): requests from sessions are switchable, OFF by default, per
install. STATE/user-todos-enabled.json = {"enabled": bool, "gt": ms}, the thinking-summaries idiom
(gesture-clock stand-down, settingStale reply, atomic write, a loud write failure told on the socket).
NOT user-todos.json: that file is the request STORE (sid to records), and a settings blob written there
would replace the store on the next register, so the store guards its own shape.

Pinned here, kernel side:
- the reader: absent reads OFF silently; only a literal true turns it on; a string, null, 0, a list or
  unparsable text reads OFF and is said once per file version; the read is memoized on (mtime_ns, size),
  so an unchanged file costs one stat and no read; reading never creates the file;
- the setter: a stamped flip applies, an equal stamp with the stored value is a silent echo, an older
  stamp stands down with the settingStale record, a refused write is told through the refused-gesture
  record with the kept value, an unstamped flip applies with the clock;
- the WS op setUserTodos, /version's top-level `userTodos` (not in the mesh dict), _GT_STORES and the
  stamp report, _setting_kept_value and _setting_stored_gt;
- what OFF does on each kernel surface, each loud: the routes answer 409 and write nothing; the drive ops
  warn and stamp nothing; the payloads ship no rows and the chatTail frame no key; the boot notice counts
  the rows stored behind an off switch;
- the register forward keeps the remote's status (a remote 409 names the host; 0, 404, another status or
  a 200 without an id are 502s with the cause), and _remote_forward_status's contract;
- the store-shape guard on every surface, and the bus's wording of the kernel's statuses (BusWording).

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
import tempfile
import types
import unittest
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
km = load_source("romp_kernel_utswitch", os.path.join(BIN, "romp-kernel"))
jd = km.jd

# this module's private synthetic sids
SID = "5b5b5b5b-1111-4222-8333-944444444401"
SID2 = "5b5b5b5b-1111-4222-8333-944444444402"
NOW = 1781200000
T_OLD, T_NEW = 1_700_000_000_000, 1_700_000_060_000


class _Sandbox(unittest.TestCase):
    """Per-test STATE sandbox with the caches reset, session hosts off, km._reply captured, and the switch
    file ABSENT at the start of every test: the shipped default, OFF."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = Path(self.td.name)
        Path(self.td.name, "session-hosts").write_text("off")
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._user_todos_switch_cache.clear()
        km._user_todos_switch_bad.clear()
        km._stale_seen.last = None
        km._stale_seen.refused = None
        self.replies = []
        self._saved_reply = km._reply
        km._reply = lambda client, m: self.replies.append(m)

    def tearDown(self):
        km._reply = self._saved_reply
        jd.STATE = self.saved
        self.td.cleanup()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._user_todos_switch_cache.clear()
        km._user_todos_switch_bad.clear()

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


_ROMP_WORDS = None


def _romp_words():
    """The veil's vocabulary, ROMP_WORDS in tests/test_injected_voice.py, read out of that file as a literal."""
    global _ROMP_WORDS
    if _ROMP_WORDS is None:
        tree = ast.parse(Path(HERE, "test_injected_voice.py").read_text())
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "ROMP_WORDS" for t in node.targets):
                _ROMP_WORDS = [word for word, _why in ast.literal_eval(node.value)]
                break
        else:
            raise AssertionError("ROMP_WORDS not found in tests/test_injected_voice.py")
    return _ROMP_WORDS


_PM = None


def _bus():
    """The postal bus, loaded once."""
    global _PM
    if _PM is None:
        _PM = load_source("romp_postal_utswitch", os.path.join(BIN, "romp-postal-service"))
    return _PM


class TheSwitch(_Sandbox):
    def test_the_file_is_not_the_store(self):
        self.assertEqual(km.USER_TODOS_SWITCH_FILE, "user-todos-enabled.json")
        self.assertNotEqual(km.USER_TODOS_SWITCH_FILE, "user-todos.json",
                            "user-todos.json is the request STORE: a setting written there corrupts it")

    def test_absent_is_off_the_shipped_default(self):
        self.assertFalse(self.switch.exists())
        self.assertFalse(km._user_todos_on())
        self.assertFalse(self.switch.exists(), "reading never creates the file")

    def _read(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            on = km._user_todos_on()
        return on, err.getvalue()

    def test_only_a_literal_true_turns_it_on(self):
        self.assertEqual(self._read(), (False, ""), "absent: the shipped default, silently")
        self.switch.write_text(json.dumps({"enabled": True, "gt": 6}))
        self.assertEqual(self._read(), (True, ""))
        self.switch.write_text(json.dumps({"enabled": False, "gt": 5}))
        self.assertEqual(self._read(), (False, ""), "a real false is not an error")
        for bad in ('{"enabled": "false"}', '{"enabled": "true"}', '{"enabled": null}', '{"enabled": 1}',
                    '{"gt": 3}', json.dumps(["enabled"]), "not json"):
            with self.subTest(bad=bad):
                self.switch.write_text(bad)
                on, err = self._read()
                self.assertFalse(on, "anything but a boolean true reads OFF")
                self.assertEqual(err.count("\n"), 1, err)
                self.assertIn("is not a switch file", err)
                self.assertIn("reading it as OFF", err)
                self.assertIn(str(self.switch), err, "names the file")
                self.assertEqual(self._read(), (False, ""), "the same file version is said once")

    def test_the_read_is_memoized_on_the_files_stat(self):
        self.switch.write_text(json.dumps({"enabled": True, "gt": 6}))
        self.assertTrue(km._user_todos_on())
        stats, reads = [], []
        real_stat, real_read = Path.stat, Path.read_text

        def stat(self, *a, **k):
            stats.append(str(self))
            return real_stat(self, *a, **k)

        def read(self, *a, **k):
            reads.append(str(self))
            return real_read(self, *a, **k)
        with mock.patch.object(Path, "stat", stat), mock.patch.object(Path, "read_text", read):
            self.assertTrue(km._user_todos_on())
        self.assertEqual(len(stats), 1, "one stat per call")
        self.assertEqual(reads, [], "an unchanged file is never read")
        self.switch.write_text(json.dumps({"enabled": False, "gt": 7}))
        os.utime(self.switch, ns=(1, 1))               # a new version: the key moves whatever the clock did
        with mock.patch.object(Path, "read_text", read):
            self.assertFalse(km._user_todos_on())
        self.assertEqual(len(reads), 1, "a moved key is read once")
        self.switch.unlink()
        self.assertFalse(km._user_todos_on(), "absent reads off and drops the memo")
        self.switch.write_text(json.dumps({"enabled": True, "gt": 8}))
        self.assertTrue(km._user_todos_on())

    def test_a_bad_version_is_memoized_as_off(self):
        self.switch.write_text("not json")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(km._user_todos_on())
        reads = []
        real_read = Path.read_text
        with mock.patch.object(Path, "read_text", lambda p, *a, **k: reads.append(1) or real_read(p, *a, **k)):
            self.assertFalse(km._user_todos_on())
        self.assertEqual(reads, [], "the OFF verdict is cached under the bad version's key")

    def test_a_stat_that_fails_for_another_reason_reads_off_and_is_said_once(self):
        # a present file the kernel cannot stat (a permission denied, never a missing file): OFF, said once per
        # failure, not on every gated read and not never (the failure has no version to be said once by)
        self.switch.write_text(json.dumps({"enabled": True, "gt": 6}))
        real_stat = Path.stat

        def stat(p, *a, **k):
            if str(p) == str(self.switch):
                raise PermissionError(errno.EACCES, "Permission denied", str(p))
            return real_stat(p, *a, **k)
        with mock.patch.object(Path, "stat", stat):
            on, err = self._read()
            self.assertFalse(on, "a file the kernel cannot stat reads OFF")
            self.assertEqual(err.count("\n"), 1, err)
            self.assertIn("stat failed", err)
            self.assertIn("reading it as OFF", err)
            self.assertIn(str(self.switch), err, "names the file")
            self.assertEqual(self._read(), (False, ""), "the same failure is said once")
            self.assertEqual(self._read(), (False, ""))
        self.assertEqual(self._read(), (True, ""), "the stat back, the file is read as it is")

    def test_the_setter_writes_value_and_stamp_and_the_reader_sees_it(self):
        self.assertEqual(km._set_user_todos(True, gt=T_OLD), T_OLD)
        self.assertEqual(json.loads(self.switch.read_text()), {"enabled": True, "gt": T_OLD})
        self.assertTrue(km._user_todos_on())
        self.assertEqual(km._set_user_todos(False, gt=T_NEW), T_NEW)
        self.assertFalse(km._user_todos_on(), "the setter pops the memo: its own flip is never missed")

    def test_a_stale_gesture_stands_down_loudly_and_keeps_the_stored_value(self):
        km._set_user_todos(True, gt=T_NEW)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIsNone(km._set_user_todos(False, gt=T_OLD))
        self.assertTrue(km._user_todos_on(), "the newer choice survives the stale flush")
        self.assertIn("user-todos", err.getvalue())
        self.assertIn("stale gesture stood down", err.getvalue())
        self.assertEqual(km._pop_stale_notice(), {"setting": "user-todos", "storedGt": T_NEW, "gt": T_OLD})

    def test_equal_stamps_keep_the_stored_value(self):
        km._set_user_todos(True, gt=T_NEW)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(km._set_user_todos(False, gt=T_NEW))
        self.assertTrue(km._user_todos_on())

    def test_an_equal_stamp_with_the_same_value_is_a_silent_echo(self):
        km._set_user_todos(True, gt=T_NEW)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIsNone(km._set_user_todos(True, gt=T_NEW))
        self.assertEqual(err.getvalue(), "", "the gesture's own echo: nothing to apply, nothing to say")
        self.assertIsNone(km._pop_stale_notice())

    def test_an_unstamped_apply_arms_the_store_against_stale_flushes(self):
        stamp = km._set_user_todos(True)
        self.assertIsInstance(stamp, int)
        self.assertGreater(stamp, T_NEW)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(km._set_user_todos(False, gt=T_OLD), "an old flush cannot walk it back")
        self.assertTrue(km._user_todos_on())

    def test_a_file_without_the_field_reads_as_gt_zero(self):
        self.switch.write_text(json.dumps({"enabled": True}))
        self.assertEqual(km._set_user_todos(False, gt=1), 1, "any stamped gesture applies over it")
        self.assertFalse(km._user_todos_on())

    def test_a_refused_write_is_told_and_applies_nothing(self):
        km._set_user_todos(True, gt=T_OLD)
        self.switch.unlink()
        self.switch.mkdir()                          # a directory in the file's place: the write is refused
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIsNone(km._set_user_todos(False, gt=T_NEW))
        self.assertIn("setting user-todos: write failed", err.getvalue())
        self.assertIsNone(km._pop_stale_notice(), "an OSError is not a stand-down")
        refused = km._pop_refused_notice()
        self.assertEqual((refused["setting"], refused["refused"], refused["write"], refused["known"]),
                         ("user-todos", "off", True, True))
        self.assertIn("write failed", refused["why"])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(km._user_todos_on(), "a directory is not a switch file: off, said")

    def test_the_stale_reply_words_the_kept_value(self):
        self.assertIs(km._setting_kept_value("user-todos"), False)
        km._set_user_todos(True)
        self.assertIs(km._setting_kept_value("user-todos"), True)

    def test_the_stamp_report_carries_the_store_like_its_siblings(self):
        self.assertIn("user-todos", km._GT_STORES)
        self.assertEqual(km._setting_stored_gt("user-todos"), 0, "absent reads 0")
        km._set_user_todos(True, gt=T_OLD)
        self.assertEqual(km._setting_stored_gt("user-todos"), T_OLD)
        self.assertEqual(km._version_info()["settingsGt"]["user-todos"], T_OLD)
        self.switch.write_text(json.dumps({"enabled": True}))
        self.assertEqual(km._setting_stored_gt("user-todos"), 0, "a file without the field reads 0")
        self.switch.write_text("garbled")
        self.assertEqual(km._setting_stored_gt("user-todos"), 0)


class TheWsOpAndVersion(_Sandbox):
    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s)), "alive": True}
        self._dirty = (km._mark_views_dirty, km._push_soon)
        self.dirtied, self.pushed = [], []
        km._mark_views_dirty = lambda: self.dirtied.append(True)
        km._push_soon = lambda: self.pushed.append(True)

    def tearDown(self):
        km._mark_views_dirty, km._push_soon = self._dirty
        super().tearDown()

    def dispatch(self, msg):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km.Handler._dispatch_ws(types.SimpleNamespace(), msg, self.client)
        return err.getvalue()

    def test_setUserTodos_applies_marks_the_views_dirty_and_wakes_the_push(self):
        self.dispatch({"type": "setUserTodos", "enabled": True, "gt": T_OLD})
        self.assertTrue(km._user_todos_on(), "the memo is dropped: the next read sees the flip")
        self.assertEqual(json.loads(self.switch.read_text())["gt"], T_OLD)
        self.assertEqual(self.dirtied, [True], "a flip changes the card with no store write: repaint now")
        self.assertEqual(self.pushed, [True])
        self.assertEqual(self.sent, [], "a clean apply sends nothing back")

    def test_a_non_boolean_enabled_is_refused(self):
        err = self.dispatch({"type": "setUserTodos", "enabled": "true", "gt": T_OLD})
        self.assertFalse(self.switch.exists(), "nothing applied")
        self.assertIn("refused setUserTodos", err)
        self.assertEqual(self.dirtied, [])
        warns = [m for m in self.replies if m.get("type") == "warn"]
        self.assertEqual(len(warns), 1)
        self.assertIn("'enabled' must be true or false", warns[0]["text"])

    def test_a_stale_setUserTodos_answers_the_delivering_socket_with_settingStale(self):
        self.dispatch({"type": "setUserTodos", "enabled": True, "gt": T_NEW})
        self.dispatch({"type": "setUserTodos", "enabled": False, "gt": T_OLD})
        self.assertTrue(km._user_todos_on())
        stale = [m for m in self.replies if m.get("type") == "settingStale"]
        self.assertEqual(stale, [{"type": "settingStale", "setting": "user-todos", "storedGt": T_NEW,
                                  "gt": T_OLD, "kept": True,
                                  "gesture": {"type": "setUserTodos", "enabled": False}}])
        self.assertEqual(len(self.dirtied), 1, "a stood-down gesture repaints nothing")

    def test_a_refused_write_does_not_tear_the_ws_down_and_is_told(self):
        self.switch.mkdir()
        try:
            err = self.dispatch({"type": "setUserTodos", "enabled": True, "gt": T_NEW})
        except OSError:
            self.fail("an OSError escaped _dispatch_ws: the reader loop reads it as a socket failure")
        self.assertIn("user-todos", err)
        self.assertTrue(self.client["alive"])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(km._user_todos_on())
        self.assertEqual(self.dirtied, [], "nothing applied, nothing to repaint")
        told = [m for m in self.replies if m.get("type") == "settingStale"]
        self.assertEqual(len(told), 1, "the refusal reaches the socket that made the gesture")
        self.assertEqual(told[0]["setting"], "user-todos")
        self.assertIn("write failed", told[0].get("why", ""))

    def test_a_valueless_op_is_ignored(self):
        self.dispatch({"type": "setUserTodos"})
        self.assertFalse(self.switch.exists())

    def test_version_reports_the_switch_top_level_and_not_in_the_mesh_dict(self):
        for want in (False, True):
            km._set_user_todos(want)
            v = km._version_info()
            self.assertIs(v["userTodos"], want)
            self.assertIn("thinkingSummaries", v)
        self.assertNotIn("userTodos", v["settings"], "per-install: never a mixed mark, never proposed")
        self.assertNotIn("user-todos", v["settingsPinned"])

    def test_per_install_no_propagation_table_names_it(self):
        self.assertNotIn("user-todos", km._SETTINGS_STORES)
        self.assertNotIn("user-todos", km._SETTINGS_LABELS)
        self.assertNotIn("user-todos", [s for _k, s, _f in km._MESH_ADOPTED_SETTINGS])
        src = inspect.getsource(km)
        self.assertNotIn('"userTodos", _set_user_todos', src, "the /judge-settings propagation shape")
        self.assertNotIn("_propagate_judge_settings(\"user-todos\"", src)
        self.assertNotIn("_pinned_stand_down(\"user-todos\"", src, "a per-install store is never pinned")


class OffOnTheRoutes(_Sandbox):
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
        self.assertEqual(res["error"], km._USER_TODOS_OFF_ERR)
        self.assertFalse((jd.STATE / "user-todos.json").exists(), "nothing written")
        self.assertEqual(self.pushed, [])

    def test_shape_errors_still_come_first(self):
        self.assertEqual(_post("/usertodo", {"id": SID})[0], 400)
        self.assertEqual(_post("/usertodo", {"id": "web/" + SID, "text": "x"})[0], 400)
        self.assertEqual(_post("/usertodo", {"id": SID, "text": "x", "blocking": "no"})[0], 400)
        self.assertEqual(_post("/usertodo/withdraw", {"id": SID})[0], 400)

    def test_the_refusal_comes_before_any_remote_forward(self):
        with mock.patch.object(km, "_host_for_sid", lambda sid: {"host": "TESTHOST"}), \
                mock.patch.object(km, "_remote_forward", side_effect=AssertionError("forwarded while off")), \
                mock.patch.object(km, "_remote_forward_status", side_effect=AssertionError("forwarded while off")):
            self.assertEqual(_post("/usertodo", {"id": SID, "text": "Need the staging port"})[0], 409)
            self.assertEqual(_post("/usertodo/withdraw", {"id": SID, "todoId": "ut-9f2c1a34"})[0], 409)

    def test_withdraw_is_refused_409_and_the_row_stays_open(self):
        km._set_user_todos(True)
        _, res = _post("/usertodo", {"id": SID, "text": "Need the staging port"})
        km._set_user_todos(False)
        code, out = _post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        self.assertEqual(code, 409)
        self.assertEqual(out["error"], km._USER_TODOS_OFF_ERR)
        self.assertNotIn("resolved", km._user_todos()[SID][0])

    def test_turning_it_back_on_shows_the_stored_rows_again(self):
        km._set_user_todos(True)
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        km._set_user_todos(False)
        self.assertEqual(km._open_user_todos(SID), [])
        km._set_user_todos(True)
        self.assertEqual([t["id"] for t in km._open_user_todos(SID)], [tid], "kept on disk the whole time")

    def test_context_answers_enabled_false_and_an_empty_block_despite_open_rows(self):
        # the SessionStart hook's read (segment C): a read, so OFF is an honest 200 carrying the switch's value
        # and an empty block, never a 409; the hook stays silent on `enabled: false` whatever else rides along
        km._set_user_todos(True)
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        code, res = _post("/usertodo/context", {"id": SID})
        self.assertEqual((code, res["enabled"]), (200, True))
        self.assertIn("Notes you still have open", res["block"])
        km._set_user_todos(False)
        code, res = _post("/usertodo/context", {"id": SID})
        self.assertEqual(code, 200, "a read: off is an honest 200, not an error")
        self.assertIs(res["enabled"], False)
        self.assertEqual(res["block"], "", "the hook injects nothing")
        self.assertEqual(self.pushed, [], "a read wakes nothing, on or off")


class OffOnTheDriveOps(_Sandbox):
    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}
        self._saved = (km._name_of, km._sdk, km._send_or_park, km._push_soon)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        self.injected = []
        km._send_or_park = lambda be, sid, text, **kw: self.injected.append((sid, text)) or False
        km._push_soon = lambda: None
        km._set_user_todos(True)
        self.tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._set_user_todos(False)

    def tearDown(self):
        km._name_of, km._sdk, km._send_or_park, km._push_soon = self._saved
        super().tearDown()

    def _warns(self):
        return [m["text"] for m in self.sent if m.get("type") == "warn"]

    def test_answer_warns_and_sends_nothing(self):
        handled = km._drive({"type": "userTodoAnswer", "id": SID, "todoId": self.tid, "text": "OAuth"}, self.client)
        self.assertTrue(handled)
        self.assertEqual(self.injected, [])
        self.assertEqual(self._warns(), [km._USER_TODOS_OFF_WARN])
        self.assertNotIn("already settled", self._warns()[0])
        self.assertNotIn("resolved", km._user_todos()[SID][0])

    def test_dismiss_warns_and_stamps_nothing(self):
        km._drive({"type": "userTodoDismiss", "id": SID, "todoId": self.tid}, self.client)
        self.assertEqual(self._warns(), [km._USER_TODOS_OFF_WARN])
        self.assertNotIn("resolved", km._user_todos()[SID][0])

    def test_the_warning_names_the_switch_and_what_did_not_happen(self):
        self.assertIn("nothing was sent", km._USER_TODOS_OFF_WARN)
        self.assertIn("nothing changed", km._USER_TODOS_OFF_WARN)
        self.assertIn("Settings, Sessions, Requests", km._USER_TODOS_OFF_WARN)

    def test_on_again_the_same_gestures_land(self):
        km._set_user_todos(True)
        km._drive({"type": "userTodoDismiss", "id": SID, "todoId": self.tid}, self.client)
        self.assertEqual(self._warns(), [])
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed")


class _PayloadSandbox(unittest.TestCase):
    """A build_session fixture (one named session, a two-row transcript) with one row stored and the switch
    left OFF."""

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
        Path(state, "session-hosts").write_text("off")
        self.saved = (jd.STATE, jd.PROJECTS, km.NAMES, km.WORKING_DIR, km._GLOBAL_CLAUDE_MD, km._live_map, km._sdk,
                      os.environ.get("CLAUDE_CONFIG_DIR"), km._read_task_store)
        jd._rebind_state(state)
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
        km._built_chat.clear()
        km._parse_cache.clear()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._user_todos_switch_cache.clear()
        km._user_todos_switch_bad.clear()
        km._set_user_todos(True)
        self.tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", "OAuth vs cookie")
        km._set_user_todos(False)

    def tearDown(self):
        (state, proj, names, wdir, gmd, live_fn, sdk, cfg, rts) = self.saved
        jd._rebind_state(state)
        jd.PROJECTS = proj
        km.NAMES, km.WORKING_DIR, km._GLOBAL_CLAUDE_MD, km._live_map, km._sdk = names, wdir, gmd, live_fn, sdk
        km._read_task_store = rts
        if cfg is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = cfg
        km._built_chat.clear()
        km._parse_cache.clear()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._user_todos_switch_cache.clear()
        km._user_todos_switch_bad.clear()
        self.td.cleanup()

    def build(self):
        km._parse_cache.clear()
        return km.build_session(SID, NOW, live_map=self.live_map)

    def _todo_events(self, payload):
        return [e for e in payload["events"] if e.get("kind") == "todo"]


class OffOnThePayloads(_PayloadSandbox):
    def test_build_session_ships_an_empty_field_and_no_rows_while_off(self):
        payload = self.build()
        self.assertEqual(payload["userTodos"], [])
        self.assertEqual(self._todo_events(payload), [])
        self.assertEqual(len(km._user_todos()[SID]), 1, "while the store still holds the row")

    def test_the_everyday_card_is_byte_identical_while_off(self):
        km._read_task_store = lambda fsid, fold=None: [
            {"id": "1", "subject": "Build the fixtures", "activeForm": None, "status": "pending"}]
        payload = self.build()
        evs = self._todo_events(payload)
        self.assertEqual(len(evs), 1)
        self.assertEqual(set(evs[0]) - {"uuid"}, {"kind", "tasks"}, "no userTodos key, no error key: today's card")
        self.assertEqual(payload["userTodos"], [])

    def test_the_same_build_shows_the_row_once_on(self):
        km._set_user_todos(True)
        payload = self.build()
        self.assertEqual([t["id"] for t in payload["userTodos"]], [self.tid])
        self.assertEqual(self._todo_events(payload)[0]["userTodos"], payload["userTodos"])

    def test_a_flip_busts_the_owning_sessions_chat_cache(self):
        off = km._user_todo_fp(SID)
        km._set_user_todos(True)
        on = km._user_todo_fp(SID)
        self.assertNotEqual(off, on)
        self.assertEqual(on, km._user_todo_fp(SID), "byte-stable while the switch holds")
        self.assertIsNone(km._user_todo_fp(SID2), "a sid with no rows is untouched by the switch")

    def test_the_chat_tail_frame_carries_no_key_while_off_and_the_list_while_on(self):
        m = {"type": "session", "id": SID, "userTodos": [],
             "events": [{"uuid": "u1", "kind": "user", "text": "wire the login routes"},
                        {"uuid": "a1", "kind": "assistant", "text": "starting"}],
             "status": {"state": "idle"}}
        sent = []
        c = {"send": lambda s: sent.append(json.loads(s)), "sent": {}, "echat": {SID: ("u1", 0)}}
        km._send_chat(c, m, None, 1, False)
        self.assertEqual(sent[0]["type"], "chatTail")
        self.assertNotIn("userTodos", sent[0])
        km._set_user_todos(True)
        sent = []
        c = {"send": lambda s: sent.append(json.loads(s)), "sent": {}, "echat": {SID: ("u1", 0)}}
        km._send_chat(c, m, None, 1, False)
        self.assertEqual(sent[0]["userTodos"], [])

    def test_open_user_todos_is_the_one_gated_read(self):
        src = inspect.getsource(km._open_user_todos)
        self.assertRegex(src, r"if not _user_todos_on\(\):\s+return \[\]")
        self.assertEqual(km._open_user_todos(SID), [])


class UnreadableStoreOnThePayload(_PayloadSandbox):
    def _corrupt(self):
        (jd.STATE / "user-todos.json").write_text(json.dumps({"enabled": True, "gt": 1}))

    def test_build_session_carries_the_error_on_the_todo_event(self):
        km._set_user_todos(True)
        self._corrupt()
        with contextlib.redirect_stderr(io.StringIO()):
            payload = self.build()
        self.assertEqual(payload["userTodos"], [])
        evs = self._todo_events(payload)
        self.assertEqual(len(evs), 1, "the card says why instead of showing nothing")
        self.assertEqual(evs[0]["userTodosError"], km._USER_TODOS_UNREADABLE_CARD
                         % str(jd.STATE / "user-todos.json").replace(str(Path.home()), "~", 1))
        self.assertNotIn(str(Path.home()), evs[0]["userTodosError"])
        self.assertEqual(evs[0]["tasks"], [])
        self.assertNotIn("error", evs[0], "the task store's key is not borrowed")

    def test_the_request_store_error_rides_its_own_key_beside_the_checklist(self):
        km._set_user_todos(True)
        km._read_task_store = lambda fsid, fold=None: [
            {"id": "1", "subject": "Build the fixtures", "activeForm": None, "status": "pending"}]
        self._corrupt()
        with contextlib.redirect_stderr(io.StringIO()):
            evs = self._todo_events(self.build())
        self.assertEqual(len(evs), 1)
        self.assertEqual(len(evs[0]["tasks"]), 1, "the checklist stays")
        self.assertNotIn("error", evs[0])
        self.assertIn("Can't read romp's request store", evs[0]["userTodosError"])

    def test_the_error_is_quiet_while_off_and_gone_once_the_file_is_fixed(self):
        self._corrupt()
        with contextlib.redirect_stderr(io.StringIO()):
            payload = self.build()
        self.assertEqual(self._todo_events(payload), [])
        km._set_user_todos(True)
        (jd.STATE / "user-todos.json").write_text(json.dumps({SID: [
            {"id": self.tid, "text": "Need the auth-scheme decision to wire login",
             "detail": "OAuth vs cookie", "createdT": NOW}]}))
        payload = self.build()
        self.assertNotIn("userTodosError", self._todo_events(payload)[0])
        self.assertEqual([t["id"] for t in payload["userTodos"]], [self.tid])

    def test_the_chat_sig_sees_the_store_go_bad_with_no_rows_of_its_own(self):
        km._set_user_todos(True)
        self.assertIsNone(km._user_todo_fp(SID2))
        self._corrupt()
        with contextlib.redirect_stderr(io.StringIO()):
            bad = km._user_todo_fp(SID2)
            self.assertEqual(bad, "unreadable")
            self.assertEqual(bad, km._user_todo_fp(SID2), "byte-stable while the file stands")
            km._set_user_todos(False)
            self.assertIsNone(km._user_todo_fp(SID2))


class OffOnTheBadge(_Sandbox):
    """The badge (_needs_you_count) reads no switch: with requests OFF the store reader returns [] for every sid, so no
    request-floored card can be built and the number is the per-card rule's, unchanged from before requests existed; with
    the switch ON a floored card contributes its blocking count. The same feed dict yields the same number either way,
    because the switch decides which cards EXIST, not how they count."""

    FLOORED = {"asks": [{"itemId": "g1", "sid": SID, "column": "needs_input", "board": "feed", "category": "needs_input",
                         "blocked": {"state": "userTodos", "count": 3, "open": 3, "what": "stopped"}}]}
    HARD = {"asks": [{"itemId": "g1", "sid": SID, "column": "needs_input", "board": "feed", "category": "needs_input",
                      "blocked": {"state": "permission", "what": "stopped"}}]}

    def test_the_count_has_no_switch_read(self):
        self.assertNotIn("_user_todos_on", inspect.getsource(km._needs_you_count))
        self.assertNotIn('feed.get("userTodos")', inspect.getsource(km._needs_you_count),
                         "the frame's marker map is not the badge's source: the floored card is")

    def test_off_no_floored_card_can_exist_so_the_number_is_the_per_card_rule(self):
        # a blocking row stored behind the off switch: the reader hides it, so nothing floors and nothing counts it
        km._set_user_todos(True)
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", blocking=True)
        km._set_user_todos(False)
        self.assertEqual(km._open_user_todos(SID), [], "off: the floor's reader sees no blocking request")
        self.assertEqual(km._blocking_user_todos(SID), [])
        self.assertEqual(km._needs_you_count(self.HARD), 1, "a hard stop counts once, as ever")

    def test_on_a_floored_card_contributes_its_blocking_count(self):
        km._set_user_todos(True)
        self.assertEqual(km._needs_you_count(self.FLOORED), 3)
        km._set_user_todos(False)
        self.assertEqual(km._needs_you_count(self.FLOORED), 3, "the same dict, the same number: the switch decides which cards exist")


class RegisterForward(_Sandbox):
    """POST /usertodo for a sid another kernel owns: the forward keeps the remote's status."""

    def setUp(self):
        super().setUp()
        km._set_user_todos(True)
        self._saved = (km._host_for_sid, km._remote_forward_status, km._push_all, km._push_soon)
        km._host_for_sid = lambda sid: {"host": "TESTHOST", "local_port": 1, "token": ""}
        km._push_all = km._push_soon = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("nothing changed locally, nothing to push"))
        self.calls = []

    def tearDown(self):
        km._host_for_sid, km._remote_forward_status, km._push_all, km._push_soon = self._saved
        super().tearDown()

    def _forward(self, st, res, **extra):
        km._remote_forward_status = lambda r, path, body: (self.calls.append((path, body)) or (st, res))
        with contextlib.redirect_stderr(io.StringIO()):
            return _post("/usertodo", dict({"id": SID, "text": "Need the staging port", "detail": "8443?"}, **extra))

    def test_a_minted_id_is_relayed_and_blocking_rides_the_forwarded_body(self):
        code, res = self._forward(200, {"ok": True, "todoId": "ut-9f2c1a34"}, blocking=True)
        self.assertEqual((code, res), (200, {"ok": True, "todoId": "ut-9f2c1a34"}))
        self.assertEqual(self.calls, [("/usertodo", {"id": SID, "text": "Need the staging port", "detail": "8443?",
                                                     "blocking": True})])

    def test_a_remote_switch_that_is_off_is_a_409_naming_the_host(self):
        code, res = self._forward(409, None)
        self.assertEqual(code, 409)
        self.assertFalse(res["ok"])
        self.assertIn("turned off", res["error"])
        self.assertIn("TESTHOST", res["error"])
        self.assertEqual(res["host"], "TESTHOST")

    def test_a_dead_tunnel_an_old_kernel_and_an_unreadable_answer_are_502_with_the_cause(self):
        for st, res_in, why in ((0, None, "not answering"), (404, None, "predates"), (500, None, "HTTP 500"),
                                (200, None, "without a request id"), (200, {"ok": False}, "without a request id")):
            with self.subTest(status=st, body=res_in):
                code, res = self._forward(st, res_in)
                self.assertEqual(code, 502)
                self.assertFalse(res["ok"])
                self.assertIn(why, res["error"])
                self.assertEqual(res["host"], "TESTHOST")
        self.assertEqual(km._user_todos(), {}, "the local store is never written for a remote sid")


class RemoteForwardStatusPin(unittest.TestCase):
    """_remote_forward_status: (status, parsed JSON on a 200 else None); 0 and a redial for a dead tunnel;
    (200, None) with NO redial for a 200 whose body is not JSON. _remote_forward reads its answer off it."""

    _R = {"host": "TESTHOST", "local_port": 1, "token": ""}

    @staticmethod
    def _conn(status=200, body=b"", raise_on_request=None):
        class _Resp:
            def read(self):
                return body
        _Resp.status = status

        class _Conn:
            def __init__(self, *a, **k):
                pass

            def request(self, *a, **k):
                if raise_on_request is not None:
                    raise raise_on_request

            def getresponse(self):
                return _Resp()

            def close(self):
                pass
        return _Conn

    def test_a_non_json_200_is_200_none_with_no_redial(self):
        redials = []
        with mock.patch.object(km.http.client, "HTTPConnection", self._conn(200, b"<html>not json</html>")), \
                mock.patch.object(km, "_demand_redial", lambda host, why: redials.append((host, why))):
            self.assertEqual(km._remote_forward_status(self._R, "/usertodo", {"id": SID}), (200, None))
            self.assertIsNone(km._remote_forward(self._R, "/usertodo", {"id": SID}))
        self.assertEqual(redials, [], "a malformed body still proves the far side spoke")

    def test_a_200_body_is_parsed_and_handed_to_both_readers(self):
        with mock.patch.object(km.http.client, "HTTPConnection", self._conn(200, b'{"ok": true, "todoId": "ut-1"}')):
            self.assertEqual(km._remote_forward_status(self._R, "/usertodo", {}), (200, {"ok": True, "todoId": "ut-1"}))
            self.assertEqual(km._remote_forward(self._R, "/usertodo", {}), {"ok": True, "todoId": "ut-1"})

    def test_a_non_200_keeps_its_status_and_a_refused_connection_is_0_with_the_redial(self):
        redials = []
        with mock.patch.object(km.http.client, "HTTPConnection", self._conn(404, b"")), \
                mock.patch.object(km, "_demand_redial", lambda host, why: redials.append((host, why))):
            self.assertEqual(km._remote_forward_status(self._R, "/usertodo", {}), (404, None))
            self.assertIsNone(km._remote_forward(self._R, "/usertodo", {}))
        self.assertEqual(redials, [])
        with mock.patch.object(km.http.client, "HTTPConnection", self._conn(raise_on_request=ConnectionRefusedError())), \
                mock.patch.object(km, "_demand_redial", lambda host, why: redials.append((host, why))):
            self.assertEqual(km._remote_forward_status(self._R, "/usertodo", {}), (0, None))
        self.assertEqual(redials, [("TESTHOST", "refused")], "a dead tunnel is user demand for a redial")


class BootNotice(_Sandbox):
    def _notice(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            n = km._user_todos_off_boot_notice()
        return n, err.getvalue()

    def test_open_rows_behind_an_off_switch_are_announced_once_in_request_wording(self):
        km._set_user_todos(True)
        km._add_user_todo(SID, "Need the auth-scheme decision")
        km._add_user_todo(SID2, "Need the staging port")
        tid = km._add_user_todo(SID2, "Need your pick of the two layouts")
        km._resolve_user_todo(SID2, tid, "withdrawn")
        km._set_user_todos(False)
        n, err = self._notice()
        self.assertEqual(n, 2, "open rows only")
        self.assertIn("2 request(s) from sessions are stored but the switch is off", err)
        self.assertIn("Settings, Sessions, Requests", err)
        self.assertNotIn("todo", err.lower())

    def test_silent_when_on_or_when_nothing_is_stored(self):
        self.assertEqual(self._notice(), (0, ""))
        km._set_user_todos(True)
        km._add_user_todo(SID, "Need the auth-scheme decision")
        self.assertEqual(self._notice(), (0, ""), "on: the rows are visible, nothing to announce")


class StoreShapeGuard(_Sandbox):
    """user-todos.json is the store. A file there that is not sid to list reads as empty, loudly, and no
    writer may overwrite that version; every surface says the store is unreadable rather than answering a
    definite state off the guard's empty read."""

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
        self.assertIn("is not a request store", err)
        self.assertIn("enabled, gt", err, "names what it found")
        self.assertIn("user-todos-enabled.json", err, "and where the switch lives")
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
                km._write_user_todos({SID: []})
            self.assertFalse(km._resolve_user_todo(SID, "ut-deadbeef", "dismissed"))
            self.assertFalse(km._reopen_user_todo(SID, "ut-deadbeef"))
        self.assertEqual(self.store.read_text(), before, "the unreadable store is intact")

    def test_unparsable_text_and_a_json_list_are_guarded_the_same_way(self):
        for junk in ("not json", json.dumps([{"id": "ut-1"}]), json.dumps({SID: {"id": "ut-1"}})):
            km._user_todos_cache.clear(); km._user_todos_bad.clear()
            self.store.write_text(junk)
            d, err = self._read()
            self.assertEqual(d, {}, junk)
            self.assertIn("is not a request store", err, junk)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(RuntimeError):
                km._write_user_todos({})

    def test_a_key_that_is_not_a_session_id_is_not_a_store_either(self):
        for bad in ({"../x": []}, {".hidden": []}, {"": []}):
            self.assertFalse(km._user_todo_store_shaped(bad), bad)
        self.assertTrue(km._user_todo_store_shaped({}))
        self.assertTrue(km._user_todo_store_shaped({SID: [], SID2: [{"id": "ut-1"}]}))

    _BAD_SIDS = ("TESTHOST:" + SID, "web/" + SID, "." + SID, "a" * 129)

    def test_the_writer_refuses_a_sid_the_reader_would_reject(self):
        for bad in self._BAD_SIDS:
            with self.assertRaises(ValueError, msg=bad):
                km._add_user_todo(bad, "Need the staging port")
        self.assertFalse(self.store.exists(), "nothing written for a refused key")
        km._add_user_todo(SID, "Need the staging port")
        d, err = self._read()
        self.assertEqual(err, "", "the store never became unreadable")
        self.assertEqual(set(d), {SID})
        self.assertEqual(km._user_todos_bad, {})

    def test_the_register_route_answers_400_for_a_malformed_id_and_leaves_a_stored_row_readable(self):
        good = km._add_user_todo(SID, "Need the auth-scheme decision")
        before = self.store.read_text()
        saved = (km._push_all, km._push_soon)
        km._push_all = km._push_soon = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("nothing changed, nothing to push"))
        try:
            for bad in self._BAD_SIDS:
                code, res = _post("/usertodo", {"id": bad, "text": "Need the staging port"})
                self.assertEqual((code, res), (400, {"ok": False, "error": "id must be a session id"}), bad)
        finally:
            km._push_all, km._push_soon = saved
        self.assertEqual(self.store.read_text(), before, "the route wrote nothing")
        km._user_todos_cache.clear()
        d, err = self._read()
        self.assertEqual(err, "")
        self.assertEqual([t["id"] for t in d[SID]], [good], "the stored row still reads")

    def test_fixing_or_removing_the_file_lets_writes_through_again(self):
        self.store.write_text(json.dumps({"enabled": True, "gt": 1}))
        with contextlib.redirect_stderr(io.StringIO()):
            self._read()
            with self.assertRaises(RuntimeError):
                km._add_user_todo(SID, "x")
            self.store.unlink()
            tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        self.assertEqual(km._user_todos()[SID][0]["id"], tid)
        self.assertEqual(km._user_todos_bad, {}, "a shaped read clears the flag")

    def test_the_boot_notice_and_the_gated_read_survive_a_corrupt_store(self):
        self.store.write_text(json.dumps({"enabled": True, "gt": 1}))
        km._set_user_todos(False)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._user_todos_off_boot_notice(), 0)
            self.assertEqual(km._open_user_todos(SID), [])

    def _corrupt(self):
        self.store.write_text(json.dumps({"enabled": True, "gt": 1}))
        with contextlib.redirect_stderr(io.StringIO()):
            km._user_todos_cache.clear()
            km._user_todos()

    def test_unreadable_tracks_the_flagged_file_version(self):
        self.assertFalse(km._user_todos_unreadable(), "no file: an empty store, not an unreadable one")
        tid = km._add_user_todo(SID, "Need the staging port")
        self.assertFalse(km._user_todos_unreadable())
        self.store.write_text(json.dumps({"enabled": True, "gt": 1}))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(km._user_todos_unreadable(), "the read that flags is the read this makes")
            self.assertTrue(km._user_todos_unreadable())
        self.store.write_text(json.dumps({SID: [{"id": tid, "text": "Need the staging port", "createdT": 1}]}))
        self.assertFalse(km._user_todos_unreadable(), "a fixed file reads again")
        self.store.unlink()
        self.assertFalse(km._user_todos_unreadable(), "a removed file is the empty store")

    def test_the_drive_ops_warn_unreadable_not_settled(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        self._corrupt()
        sent, injected = [], []
        client = {"send": lambda s: sent.append(json.loads(s))}
        with mock.patch.object(km, "_name_of", lambda sid: "web"), \
                mock.patch.object(km, "_sdk", lambda: None), \
                mock.patch.object(km, "_send_or_park", lambda be, sid, text, **kw: injected.append(text) or False), \
                mock.patch.object(km, "_push_soon", lambda: None), \
                contextlib.redirect_stderr(io.StringIO()):
            km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "OAuth"}, client)
            km._drive({"type": "userTodoDismiss", "id": SID, "todoId": tid}, client)
        warns = [m["text"] for m in sent if m.get("type") == "warn"]
        self.assertEqual(warns, [km._USER_TODOS_UNREADABLE_WARN, km._USER_TODOS_UNREADABLE_WARN])
        self.assertEqual(injected, [], "nothing reaches the session")
        self.assertEqual(self.store.read_text(), json.dumps({"enabled": True, "gt": 1}))


class BusWording(unittest.TestCase):
    """What the two postal tools tell the agent. The bus reaches the kernel through _kernel_post, which
    answers None for an unreachable kernel and {ok: False, status, error} for a refusal, so the tool words
    each status the kernel returns and never mirrors the kernel's caps."""

    def setUp(self):
        self.pm = pm = _bus()
        self._saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        self.posts = []
        self.canned = None
        pm._kernel_post = lambda path, body, timeout=2: (self.posts.append((path, body)) or self.canned)
        pm._self_identity = lambda: (SID, "api")
        pm._heartbeat = lambda *a, **k: None
        pm._user_todos_switch_cache.clear()
        pm.USER_TODOS_SWITCH.parent.mkdir(parents=True, exist_ok=True)
        pm.USER_TODOS_SWITCH.write_text(json.dumps({"enabled": True, "gt": 1}))

    def tearDown(self):
        pm = self.pm
        pm._kernel_post, pm._self_identity, pm._heartbeat = self._saved
        pm.USER_TODOS_SWITCH.unlink(missing_ok=True)
        pm._user_todos_switch_cache.clear()

    def _no_machinery(self, text):
        for word in _romp_words() + ["kernel"]:
            self.assertNotIn(word, text.lower(), (word, text))

    @staticmethod
    def _refusal(status, error):
        # the shape _kernel_post returns for a 4xx/5xx: the status and a bounded slice of the body
        return {"ok": False, "status": status, "error": json.dumps({"ok": False, "error": error})}

    def test_a_409_relays_the_kernels_off_line(self):
        self.canned = self._refusal(409, "requests from sessions are turned off on this machine")
        text, is_err = self.pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(is_err)
        self.assertEqual(len(self.posts), 1)
        self.assertIn("Not saved", text)
        self.assertIn("turned off on this machine", text)
        self.assertNotIn("try again", text)
        self._no_machinery(text)

    def test_a_400_relays_the_caps_text_and_the_bus_mirrors_no_cap(self):
        why = "detail is 100000 characters, over the 4000-character cap: keep the request to one line and put the rest in your reply"
        self.canned = self._refusal(400, why)
        text, is_err = self.pm._mcp_call("add_user_todo", {"text": "Need the port", "detail": "x" * 100_000})
        self.assertTrue(is_err)
        self.assertEqual(len(self.posts), 1, "posted: the kernel enforces the caps once")
        self.assertIn("one line", text)
        self.assertIn("rest in your reply", text)
        self._no_machinery(text)
        src = Path(BIN).parent.joinpath("postal", "postal_service.py").read_text()
        self.assertNotIn("USER_TODO_TEXT_CAP", src)
        self.assertNotIn("USER_TODO_DETAIL_CAP", src)
        arm = src[src.index('if name == "add_user_todo":'):src.index('if name == "withdraw_user_todo":')]
        self.assertNotIn("len(text)", arm, "no length check precedes the post")
        self.assertNotIn("len(detail)", arm)

    def test_a_503_and_a_502_relay_the_cause(self):
        self.canned = self._refusal(503, "the request store is unreadable (see the kernel log)")
        text, is_err = self.pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(is_err)
        self.assertIn("unreadable", text)
        self.canned = self._refusal(502, "the tunnel to TESTHOST is not answering (re-dialing)")
        text, is_err = self.pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(is_err)
        self.assertIn("TESTHOST", text)
        self.assertIn("not answering", text)
        for t in (text,):
            self.assertNotIn("romp", t.lower())

    def test_a_plain_error_text_is_relayed_as_it_is(self):
        self.canned = {"ok": False, "status": 500, "error": "Internal Server Error"}
        text, is_err = self.pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(is_err)
        self.assertIn("Internal Server Error", text)

    def test_none_is_the_unreachable_line(self):
        self.canned = None
        text, is_err = self.pm._mcp_call("add_user_todo", {"text": "Need the port"})
        self.assertTrue(is_err)
        self.assertIn("will NOT see it", text)
        self.assertIn("try again", text)
        self._no_machinery(text)

    def test_withdraw_against_an_unreadable_store_says_so_not_no_request_of_yours(self):
        self.canned = {"ok": False, "state": "unknown", "at": None, "owner": None,
                       "error": "the request store is unreadable (see the kernel log)"}
        text, is_err = self.pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})
        self.assertTrue(is_err)
        self.assertNotIn("of yours", text)
        self.assertIn("ut-9f2c1a34", text)
        self.assertIn("Nothing changed", text)
        self.assertIn("read", text.lower())
        self._no_machinery(text)

    def test_the_bus_switch_reader_is_memoized_and_says_once(self):
        pm = self.pm
        pm._user_todos_switch_bad.clear()

        def read():
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                on = pm._user_todos_on()
            return on, err.getvalue()
        pm.USER_TODOS_SWITCH.unlink()
        self.assertEqual(read(), (False, ""), "absent is silent")
        pm.USER_TODOS_SWITCH.write_text("not json")
        on, err = read()
        self.assertEqual((on, err.count("\n")), (False, 1), err)
        self.assertIn("is not a switch file", err)
        self.assertEqual(read(), (False, ""), "once per file version")
        pm.USER_TODOS_SWITCH.write_text(json.dumps({"enabled": "true"}))
        self.assertEqual(read()[1].count("\n"), 1, "a string is not a boolean")
        pm.USER_TODOS_SWITCH.write_text(json.dumps({"enabled": False, "gt": 5}))
        self.assertEqual(read(), (False, ""))
        pm.USER_TODOS_SWITCH.write_text(json.dumps({"enabled": True, "gt": 6}))
        self.assertEqual(read(), (True, ""))
        reads = []
        real = Path.read_text
        with mock.patch.object(Path, "read_text", lambda p, *a, **k: reads.append(1) or real(p, *a, **k)):
            self.assertTrue(pm._user_todos_on())
        self.assertEqual(reads, [], "an unchanged file is stat'ed, never read")


if __name__ == "__main__":
    unittest.main(verbosity=2)
