#!/usr/bin/env python3
"""The /end route for a REMOTE sid relays the owning kernel's answer (fork PR 433, E1; 2026-08-18).

Until the tmux backend's removal (upstream #1401, folded 2026-09-15) this module also pinned the fork's
death corroboration: every `closed` emitter (endSession, closeTab, /end, cancelCreate's teardown) asked
the liveness owner AFTER the kill (_confirmed_ended, _end_and_record) because TmuxBackend.kill was
fire-and-forget and `sid in _tmux_sessions()` collapsed to [] on a tmux stall. Those classes
(EndSessionCorroborates, CloseTabRefusalIsHonest, CorroborationNeverInheritsTheCollapse,
EndRouteCorroborates) retired with the family: the SDK and Codex kills are authoritative, so upstream's
kill path records the death and broadcasts `closed` on be.kill's return (tests/test_kernel_session_death.py
and tests/test_sdk_registry_blind.py cover the per-backend stand-down); closeTab broadcasts `closed`
unconditionally again and POST /end answers ok:true on the kill's return.

What stays is the relay: /end for a sid another kernel owns must hand the caller THAT kernel's answer
(its refusal in its words, its ok:true, or an honest failure when it does not answer), never a
manufactured ok:true; bin/romp printed 'ok' and exited 0 on a dropped remote refusal once.

SYNTHETIC fixtures only: placeholder UUIDs, invented names, hermetic temp STATE.
"""
import io
import json
import os
import tempfile
import types
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_closedhonesty", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"


class FakeBackend:
    """A backend whose kill visibly lands (removes the sid from the shared live map)."""

    def __init__(self, live):
        self.killed = []
        self.live = live

    def kill(self, sid):
        self.killed.append(sid)
        self.live.pop(sid, None)


class ClosedHonestyBase(unittest.TestCase):
    def setUp(self):
        self.live = {}                # the liveness owner's answer; never reassigned, only mutated
        self.be = FakeBackend(self.live)
        self.sent = []                # (app, msg) broadcasts
        self.client_frames = []       # frames sent to THIS client only
        self.deaths = []
        self.comment_kills = []
        self._saved = {}

        def patch(nm, fn):
            self._saved[nm] = getattr(km, nm)
            setattr(km, nm, fn)

        patch("_send_to_app", lambda app, m: self.sent.append((app, m)))
        patch("_push_soon", lambda: None)
        patch("_push_all", lambda live_map=None: None)
        patch("_live_map", lambda: self.live)
        patch("_record_death", lambda sid, t, kind: self.deaths.append((sid, kind)))
        patch("_comment_kill_all", lambda sid, be: self.comment_kills.append(sid))
        patch("_kernel_knows", lambda sid, live=None: True)   # the HTTP gate passes the map it read
        patch("_name_of", lambda sid: "web")
        self._saved_bf = km.Sessions.backend_for
        km.Sessions.backend_for = staticmethod(lambda sid: self.be)
        self.client = {"send": lambda s: self.client_frames.append(json.loads(s))}

    def tearDown(self):
        for nm, v in self._saved.items():
            setattr(km, nm, v)
        km.Sessions.backend_for = self._saved_bf

    def closed_broadcasts(self):
        return [m for _a, m in self.sent if m.get("type") == "closed"]

    def client_warns(self):
        return [f for f in self.client_frames if f.get("type") == "warn"]


class FakePost(km.Handler):
    """Just enough of the HTTP handler for do_POST's /end branch: path + body in, (code, json) out.
    A real Handler (no socket, no __init__ of its own base) rather than a bare duck type: since the
    2026-09-08 fold of upstream's request-bodies change, do_POST reads the body through
    Handler._read_post_body (authorize first, then a bounded read), and a fake without that method
    raised into the catch-all, whose traceback 500 this _send could not parse, so no response was
    recorded at all. _authorize is stubbed open: the gate under test is the kill corroboration, not auth."""

    def __init__(self, path, body=b"{}"):
        self.path = path
        self.headers = {"Content-Length": str(len(body))}
        self.rfile = io.BytesIO(body)
        self.client_address = ("127.0.0.1", 0)
        self.close_connection = False                    # keep-alive until the body read says otherwise
        self.responses = []

    def _origin_ok(self):
        return False

    def _authorize(self, q):
        return True, None, ""

    def _send(self, code, body, ctype="text/plain", headers=None):
        # `headers` is what a body refusal passes (Connection: close); recording it keeps such a refusal
        # legible as a wrong status code rather than a swallowed TypeError and an empty response list
        self.responses.append((code, json.loads(body)))


class RemoteEndRelaysTheRefusal(ClosedHonestyBase):
    """/end for a REMOTE sid must relay the owning kernel's answer, not manufacture ok:true: the
    remote's new corroborated refusal ("the kill didn't take") arrives as parsed JSON from
    _remote_forward and used to be dropped on the floor — bin/romp printed 'ok' and exited 0 while
    the runaway session kept running and billing. The /send twin already had this honesty."""

    def setUp(self):
        super().setUp()
        self._saved["_host_for_sid"] = km._host_for_sid
        km._host_for_sid = lambda sid: {"host": "gpu1", "local_port": 1, "token": ""}
        self.forwarded = []

    def _post_end(self):
        import contextlib
        fake = FakePost("/end", json.dumps({"id": SID}).encode())
        with contextlib.redirect_stderr(io.StringIO()):
            km.Handler.do_POST(fake)
        self.assertEqual(len(fake.responses), 1)
        return fake.responses[0]

    def test_the_remote_refusal_reaches_the_caller_verbatim(self):
        refusal = {"ok": False, "error": "the session is still running — the kill didn't take"}
        # the arm reads the far answer with its body (_remote_forward_answer), so that is the seam stubbed
        self._saved["_remote_forward_answer"] = km._remote_forward_answer
        km._remote_forward_answer = lambda r, path, body, method="POST": (self.forwarded.append((path, body)) or (200, refusal, json.dumps(refusal)))
        code, resp = self._post_end()
        self.assertEqual((code, resp), (200, refusal),
                         "the owning kernel said the kill didn't take — the caller must hear it")
        self.assertEqual(self.forwarded, [("/end", {"id": SID})])
        self.assertEqual(self.deaths, [], "the remote owns the death record, never the relay")

    def test_a_remote_success_still_relays_ok_true(self):
        self._saved["_remote_forward_answer"] = km._remote_forward_answer
        km._remote_forward_answer = lambda r, path, body, method="POST": (200, {"ok": True}, "")
        code, resp = self._post_end()
        self.assertEqual((code, resp), (200, {"ok": True}))

    def test_a_dead_far_kernel_is_an_honest_failure(self):
        self._saved["_remote_forward_answer"] = km._remote_forward_answer
        km._remote_forward_answer = lambda r, path, body, method="POST": (0, None, "")
        code, resp = self._post_end()
        self.assertEqual(code, 200)
        self.assertFalse(resp["ok"])
        self.assertIn("isn't answering", resp["error"])
        self.assertIn("gpu1", resp["error"])


if __name__ == "__main__":
    unittest.main()
