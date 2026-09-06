#!/usr/bin/env python3
"""POST /down — the quiesce `romp down` asks for before it stops the kernel (2026-09-06).

The kernel never exits from this route: under the manager a kernel exit is a crash to respawn,
so the stop comes top-down through the supervisor. The route only makes the moment quiet — it
arms the going-down hold (new turn starts and session creates held), blocks until the in-flight
count reaches 0 or `wait` runs out, and answers what a stop right now would cut. Pinned here:
the explicit-token gate (a WRITE that holds every session's turn starts, so the ambient cookie is
not enough — the /busy?drain=1 rule), the wait-for-quiet loop against a fake backend whose count
falls mid-wait, the bounded give-up with the in-flight names, the cancel arm, both create doors
refusing while the hold is in force, and the no-backend case (nothing to hold: quiet at once).
Synthetic only: the real Handler on an ephemeral loopback port, a fake backend, invented token.
"""
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
# a dead manager port, never popped: absent is the one unsafe state (see tests/conftest.py)
os.environ["ROMP_MANAGER_PORT"] = "1"
km = SourceFileLoader("romp_kernel_down", os.path.join(BIN, "romp-kernel")).load_module()


class _FakeBackend:
    """What the route needs of SdkBackend: the in-flight count, the names behind it, and the
    quiesce trio. Records every call so the tests can assert the hold's TTL and the cancel."""

    def __init__(self, busy=0, names=()):
        self.busy = busy
        self.names = list(names)
        self.quiesced = []      # the TTLs each quiesce() call armed
        self.canceled = 0
        self._until = 0.0

    def busy_count(self):
        return self.busy

    def inflight_names(self):
        return list(self.names[: self.busy])

    def quiesce(self, ttl):
        self.quiesced.append(ttl)
        self._until = time.time() + ttl

    def quiescing(self):
        return self._until > time.time()

    def cancel_quiesce(self):
        self.canceled += 1
        self._until = 0.0


class DownRoute(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self._saved_be = km._sdk_backend
        self._saved_tmux = km._tmux_sessions
        km._tmux_sessions = lambda *a, **k: {}     # no tmux server in a test
        self.be = _FakeBackend()
        km._sdk_backend = self.be

    def tearDown(self):
        km._sdk_backend = self._saved_be
        km._tmux_sessions = self._saved_tmux
        self.srv.shutdown()
        self.srv.server_close()

    def _post(self, path, body=None, headers=None, raw=None):
        data = raw if raw is not None else json.dumps(body if body is not None else {}).encode()
        h = {"Content-Type": "application/json"}
        h.update(headers or {})
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), data=data,
                                     headers=h, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raw_body = e.read()
            try:
                return e.code, json.loads(raw_body)
            except Exception:
                return e.code, {"raw": raw_body.decode("utf-8", "replace")}

    def _down(self, body=None, **kw):
        return self._post("/down", body, headers={"X-Romp-Token": km.TOKEN}, **kw)

    # ── the gate ────────────────────────────────────────────────────────────
    def test_no_credential_is_refused_and_arms_nothing(self):
        status, _ = self._post("/down", {"wait": 0})
        self.assertEqual(status, 403)
        self.assertEqual(self.be.quiesced, [], "an unauthenticated POST holds nobody's turns")

    def test_the_ambient_cookie_alone_is_refused(self):
        # the preamble's _authorize takes the cookie; the route demands the EXPLICIT token on top
        status, body = self._post("/down", {"wait": 0}, headers={"Cookie": "romp_token=" + km.TOKEN})
        self.assertEqual(status, 403)
        self.assertIn("serve token", body.get("error", ""))
        self.assertEqual(self.be.quiesced, [])

    def test_a_query_token_is_accepted_like_the_header(self):
        status, body = self._post("/down?token=" + km.TOKEN, {"wait": 0})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(len(self.be.quiesced), 1)

    # ── the quiesce ─────────────────────────────────────────────────────────
    def test_a_quiet_kernel_answers_at_once_and_holds_for_wait_plus_grace(self):
        status, body = self._down({"wait": 5})
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True, "quiet": True, "busy": 0, "inflight": [], "waited": 0.0})
        self.assertEqual(self.be.quiesced, [5 + km.DOWN_HOLD_GRACE_S],
                         "the hold outlives the wait by the grace, so the stop that follows lands "
                         "on a still-quiet kernel")

    def test_the_wait_ends_on_the_event_the_count_reaches_zero(self):
        self.be.busy = 2
        self.be.names = ["web", "api"]

        def finish_turns():
            time.sleep(0.4)
            self.be.busy = 0

        threading.Thread(target=finish_turns, daemon=True).start()
        t0 = time.monotonic()
        status, body = self._down({"wait": 5})
        took = time.monotonic() - t0
        self.assertEqual(status, 200)
        self.assertTrue(body["quiet"])
        self.assertEqual(body["busy"], 0)
        self.assertEqual(body["inflight"], [])
        self.assertGreaterEqual(took, 0.35, "it waited for the turns to end")
        self.assertLess(took, 3, "…and returned on that event, not at the deadline")
        self.assertEqual(self.be.quiesced, [5 + km.DOWN_HOLD_GRACE_S], "the hold was armed BEFORE the wait")

    def test_a_kernel_still_busy_at_the_deadline_names_what_a_stop_cuts(self):
        self.be.busy = 1
        self.be.names = ["web"]
        t0 = time.monotonic()
        status, body = self._down({"wait": 0.3})
        took = time.monotonic() - t0
        self.assertEqual(status, 200)
        self.assertFalse(body["quiet"])
        self.assertEqual(body["busy"], 1)
        self.assertEqual(body["inflight"], ["web"], "the CLI says which sessions the stop cuts")
        self.assertGreaterEqual(took, 0.25)
        self.assertLess(took, 3, "the wait is bounded by `wait`, not by the turn")
        self.assertGreaterEqual(body["waited"], 0.2)

    def test_wait_zero_is_a_probe_that_still_arms_the_hold(self):
        # `--now` skips the route entirely; a caller that wants the hold with no wait sends 0
        self.be.busy = 1
        status, body = self._down({"wait": 0})
        self.assertEqual(status, 200)
        self.assertFalse(body["quiet"])
        self.assertEqual(self.be.quiesced, [km.DOWN_HOLD_GRACE_S])

    def test_the_default_wait_applies_when_the_body_names_none(self):
        status, _ = self._down({})
        self.assertEqual(status, 200)
        self.assertEqual(self.be.quiesced, [km.DOWN_WAIT_DEFAULT_S + km.DOWN_HOLD_GRACE_S])

    # ── the create doors refuse while the hold is in force ───────────────────
    def test_post_new_is_refused_while_quiescing(self):
        self._down({"wait": 0})
        self.assertTrue(self.be.quiescing())
        status, body = self._post("/new", {"name": "web", "dir": tempfile.mkdtemp(), "backend": "sdk"},
                                  headers={"X-Romp-Token": km.TOKEN})
        self.assertEqual(status, 503, "a session born now would die with the kernel — refuse, loudly")
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], km.GOING_DOWN_REFUSAL)

    def test_the_ws_create_op_is_refused_with_the_same_words(self):
        self._down({"wait": 0})
        sent = []
        client = {"send": lambda s: sent.append(json.loads(s)), "app": "chat"}
        km.Handler._dispatch_ws(None, {"type": "createSession", "name": "web", "dir": tempfile.mkdtemp(),
                                       "backend": "sdk"}, client)
        warns = [m for m in sent if m.get("type") == "warn"]
        self.assertEqual(len(warns), 1, sent)
        self.assertEqual(warns[0]["text"], km.GOING_DOWN_REFUSAL)

    def test_cancel_releases_the_hold_and_reopens_the_doors(self):
        self._down({"wait": 0})
        self.assertTrue(self.be.quiescing())
        status, body = self._down({"cancel": True})
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True, "canceled": True})
        self.assertEqual(self.be.canceled, 1)
        self.assertFalse(self.be.quiescing())
        status, _ = self._post("/new", {"name": "web", "dir": tempfile.mkdtemp(), "backend": "sdk"},
                               headers={"X-Romp-Token": km.TOKEN})
        self.assertNotEqual(status, 503, "after the cancel the door is whatever it was before")

    def test_going_down_reads_the_global_and_never_builds_a_backend(self):
        km._sdk_backend = None
        self.assertFalse(km._going_down())
        km._sdk_backend = False            # "unavailable" — the other non-backend value
        self.assertFalse(km._going_down())

    # ── malformed asks and the no-backend case ───────────────────────────────
    def test_a_bad_body_or_wait_is_a_400_and_arms_nothing(self):
        for raw, why in ((b"[]", "a list"), (b"nonsense", "not JSON")):
            status, body = self._down(raw=raw)
            self.assertEqual(status, 400, why)
            self.assertFalse(body["ok"])
        for w in ("5", True, -1, km.DOWN_WAIT_MAX_S + 1):
            status, _ = self._down({"wait": w})
            self.assertEqual(status, 400, repr(w))
        self.assertEqual(self.be.quiesced, [], "no malformed request holds anyone's turns")

    def test_no_sdk_backend_means_nothing_to_hold(self):
        km._sdk_backend = None
        status, body = self._down({"wait": 5})
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True, "quiet": True, "busy": 0, "inflight": [], "waited": 0})
        # the cancel arm is a no-op with the same answer
        status, body = self._down({"cancel": True})
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True, "canceled": True})


if __name__ == "__main__":
    unittest.main()
