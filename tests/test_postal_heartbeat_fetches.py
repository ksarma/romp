#!/usr/bin/env python3
"""The postal heartbeat's cost to the kernel: GET /sessions per beat and per tool call (2026-09-06).

Each MCP heartbeat used to resolve this session's identity twice (my_id, then my_name — one GET /sessions
each) and the bus's handler fetched a third time, so about 30 local sessions beating every 30 s were
3 requests per second against a kernel already at one core, for a beat the bus ignores (local sids are
already in its listing). Now: one resolution per beat and per tool call (_self_identity), and the loop
ends the first time the bus confirms this session local from its own answered listing. A remote
(client-only box) session never hears "local" from the hub's bus and keeps beating exactly as before.

The kernel is the ROMP_SESSIONS_FILE seam; fetches are counted at _kernel_sessions_checked, the one
function every listing read goes through. Synthetic only: placeholder UUIDs, the notes-api demo sessions."""
import json
import os
import tempfile
import threading
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

WEB = "11111111-2222-3333-4444-555555555555"
API = "11111111-2222-3333-4444-666666666666"
THREAD = "11111111-2222-3333-4444-777777777777"
FORK = "99999999-8888-7777-6666-555555555555"

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
_SESS = os.path.join(os.environ["XDG_STATE_HOME"], "sessions.json")
Path(_SESS).write_text(json.dumps([
    {"id": WEB, "name": "web", "dir": "", "state": "working", "working": "", "lastSid": FORK},
    {"id": API, "name": "api", "dir": "", "state": "idle", "working": "", "lastSid": ""},
    {"id": THREAD, "name": "web-t1", "dir": "", "state": "working", "working": "", "lastSid": "",
     "thread": True, "parent": WEB}]))
os.environ["ROMP_SESSIONS_FILE"] = _SESS
pm = SourceFileLoader("romp_postal_hb_fetches", os.path.join(BIN, "romp-postal-service")).load_module()


class Counting(unittest.TestCase):
    """Every listing fetch is counted; the bus is stubbed at _http and answers what each test says."""

    def setUp(self):
        # os.environ is process-wide: other modules in the same pytest worker pop or repoint the seam
        # between tests, so pin both env halves here and put them back after (the self-identity test's idiom)
        self._env = (os.environ.get("CLAUDE_CODE_SESSION_ID"), os.environ.get("ROMP_SESSIONS_FILE"))
        os.environ["CLAUDE_CODE_SESSION_ID"] = WEB
        os.environ["ROMP_SESSIONS_FILE"] = _SESS
        self._saved = (pm._kernel_sessions_checked, pm._http, pm.ensure)
        self.fetches, self.posts = [], []
        real = self._saved[0]
        pm._kernel_sessions_checked = lambda threads=False: (self.fetches.append(threads),
                                                             real(threads=threads))[1]
        self.answer = {"ok": True, "local": True, "agents": []}
        pm._http = lambda method, path, payload=None: (self.posts.append((method, path, payload))
                                                      or dict(self.answer))
        pm.ensure = lambda: True

    def tearDown(self):
        pm._kernel_sessions_checked, pm._http, pm.ensure = self._saved
        for key, val in zip(("CLAUDE_CODE_SESSION_ID", "ROMP_SESSIONS_FILE"), self._env):
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val

    # ── one resolution ────────────────────────────────────────────────────────────────────────

    def test_self_identity_is_one_fetch_with_thread_rows(self):
        self.assertEqual(pm._self_identity(), (WEB, "web"))
        self.assertEqual(self.fetches, [True], "one GET /sessions?threads=1 for both halves")

    def test_self_identity_keeps_both_fallbacks(self):
        # the fork fsid resolves to the stable row (the 2026-07-27 rule) in the same single fetch
        os.environ["CLAUDE_CODE_SESSION_ID"] = FORK
        self.assertEqual(pm._self_identity(), (WEB, "web"))
        # no row anywhere: the env value passes through as the id, the names registry is the name
        os.environ["CLAUDE_CODE_SESSION_ID"] = "abcdef00-0000-0000-0000-000000000000"
        pm.NAMES_DIR.mkdir(parents=True, exist_ok=True)
        (pm.NAMES_DIR / "abcdef00-0000-0000-0000-000000000000").write_text("tests\t\t#111111\t#ffffff\n")
        self.assertEqual(pm._self_identity(), ("abcdef00-0000-0000-0000-000000000000", "tests"))
        os.environ.pop("CLAUDE_CODE_SESSION_ID")
        self.assertEqual(pm._self_identity(), (None, None), "not a romp session")
        self.assertEqual(pm.my_id(), None)
        self.assertEqual(pm.my_name(), None)

    def test_a_thread_row_heartbeats_under_its_row_name(self):
        # a comment thread withholds its names entry, so the name must come from the row and nothing else
        os.environ["CLAUDE_CODE_SESSION_ID"] = THREAD
        self.assertTrue(pm._heartbeat_once())
        self.assertEqual(self.posts, [("POST", "/heartbeat", {"id": THREAD, "name": "web-t1"})])
        self.assertEqual(self.fetches, [True])

    def test_one_heartbeat_iteration_is_one_fetch(self):
        pm._heartbeat_once()
        self.assertEqual(self.fetches, [True], "was two: my_id() then my_name()")
        self.assertEqual(self.posts, [("POST", "/heartbeat", {"id": WEB, "name": "web"})])

    def test_one_tool_call_is_one_fetch(self):
        for tool, args in (("list_agents", {}), ("check_inbox", {}),
                           ("send_message", {"to": "api", "body": "the staging port?", "kind": "question"})):
            self.fetches.clear(); self.posts.clear()
            pm._mcp_call(tool, args)
            self.assertEqual(self.fetches, [True], "%s: one GET /sessions per tool call (was two)" % tool)
            self.assertEqual(self.posts[0], ("POST", "/heartbeat", {"id": WEB, "name": "web"}),
                             "%s: the per-call beat still goes out" % tool)
        self.assertEqual(self.posts[1][2]["from_id"], WEB)
        self.assertEqual(self.posts[1][2]["from"], "web")

    def test_cli_agents_and_cli_send_are_one_fetch_each(self):
        import io, sys
        out, saved_out = io.StringIO(), sys.stdout
        sys.stdout = out
        try:
            self.assertEqual(pm.cli_agents(), 0)
            self.assertEqual(self.fetches, [True])
            self.assertEqual(self.posts[-1][1], "/agents?me=web")
            self.fetches.clear()
            self.assertEqual(pm.cli_send(["--kind", "coordinate", "api", "synthetic body"]), 0)
            self.assertEqual(self.fetches, [True])
            self.assertEqual(self.posts[-1][2]["from_id"], WEB)
        finally:
            sys.stdout = saved_out

    # ── the loop's exit ───────────────────────────────────────────────────────────────────────

    def test_heartbeat_once_reads_the_bus_verdict(self):
        self.answer = {"ok": True, "local": True}
        self.assertTrue(pm._heartbeat_once(), "the bus confirmed local from its own listing")
        self.answer = {"ok": True, "local": False}
        self.assertFalse(pm._heartbeat_once(), "remote, or the bus's listing was unanswered: keep beating")
        self.answer = {"ok": True}
        self.assertFalse(pm._heartbeat_once(), "an older bus without the bit: keep beating")
        pm._http = lambda *a, **k: (_ for _ in ()).throw(pm.BusError("down"))
        self.assertFalse(pm._heartbeat_once(), "no bus: keep beating")
        os.environ.pop("CLAUDE_CODE_SESSION_ID")
        self.assertFalse(pm._heartbeat_once(), "no identity: nothing to end")

    def test_loop_ends_on_the_first_local_answer_and_not_before(self):
        answers = [{"ok": True, "local": False}, {"ok": True}, {"ok": True, "local": True},
                   {"ok": True, "local": True}]
        pm._http = lambda method, path, payload=None: (self.posts.append(path) or answers.pop(0))
        t = threading.Thread(target=pm._heartbeat_loop, kwargs={"interval": 0.01}, daemon=True)
        t.start()
        t.join(5)
        self.assertFalse(t.is_alive(), "the loop ends once the bus says local")
        self.assertEqual(self.posts, ["/heartbeat"] * 3, "two non-local answers kept it beating")
        self.assertEqual(self.fetches, [True] * 3, "one listing fetch per beat")

    def test_repeated_non_local_answers_never_end_the_loop(self):
        # the remote-session shape: the hub's bus never lists this sid and answers local=false on every
        # beat, so each iteration is a full resolution plus a post, exactly as before this change
        self.answer = {"ok": True, "local": False}
        for _ in range(4):
            self.assertFalse(pm._heartbeat_once())
        self.assertEqual(len(self.posts), 4)
        self.assertEqual(self.fetches, [True] * 4, "no memo of the sid or the verdict between beats")
        # and the loop body is exactly that test: it returns on True and on nothing else
        import inspect
        src = inspect.getsource(pm._heartbeat_loop)
        self.assertIn("if _heartbeat_once():\n                return", src)
        self.assertEqual(src.count("return"), 1, "the loop has one exit and it is the bus's local answer")

    # ── the bus's retry pass ──────────────────────────────────────────────────────────────────

    def test_retry_pending_fetches_nothing_without_pending_mail(self):
        pm.MAILPENDING.mkdir(parents=True, exist_ok=True)
        for m in pm.MAILPENDING.iterdir():
            m.unlink()
        pm._retry_pending()
        self.assertEqual(self.fetches, [], "no marker files: no GET /sessions (was one every 5 s)")
        (pm.MAILPENDING / API).write_text("")                   # a stale marker: new/ is empty
        pm._retry_pending()
        self.assertEqual(self.fetches, [], "a stale marker is cleared without a fetch")
        self.assertFalse((pm.MAILPENDING / API).exists(), "the stale marker was reconciled away")

    def test_retry_pending_fetches_once_for_real_pending_mail(self):
        saved_push = pm._push
        pushed = []
        pm._push = lambda sid, row: pushed.append(sid)
        try:
            pm.deliver(API, "web", WEB, "synthetic body", kind="coordinate")
            pm.deliver(WEB, "api", API, "synthetic reply", kind="coordinate")
            self.fetches.clear()
            pm._retry_pending()
            self.assertEqual(self.fetches, [False], "one listing fetch for the whole pass, not one per marker")
            self.assertEqual(sorted(pushed), sorted([API, WEB]))
        finally:
            pm._push = saved_push
            for sid in (API, WEB):
                for f in (pm.MAILROOT / sid / "new").glob("*"):
                    f.unlink()
                pm._mark_pending(sid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
