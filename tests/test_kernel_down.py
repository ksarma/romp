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
from pathlib import Path
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

    def test_the_refusal_states_the_fact_and_hands_over_no_command(self):
        # `romp new` inside a session prints a 4xx body's error verbatim, so the reader can be an
        # AGENT; told to run `romp up` it would, and undo a stop the user made on purpose (review
        # find, 2026-09-06). The text says what is happening and instructs nobody.
        text = km.GOING_DOWN_REFUSAL
        self.assertIn("on purpose", text)
        self.assertIn("cannot start", text)
        for cmd in ("romp up", "romp down", "romp-service", "systemctl", "launchctl", "start it"):
            self.assertNotIn(cmd, text, "no command for the reader to run: %r" % cmd)
        self.assertNotIn("\u2014", text, "no em dashes in text a session can read")
        self.assertNotIn("fleet", text)

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


class QuiesceLease(unittest.TestCase):
    """The quiesce on the REAL SdkBackend, where the route's fake above cannot reach: the lease's wake
    timer, and the resume notice a turn cut by `romp down` gets at the next start."""

    @classmethod
    def setUpClass(cls):
        cls.sb = SourceFileLoader("romp_sdk_backend_down", os.path.join(BIN, "romp_sdk_backend.py")).load_module()

    def _backend(self, d=None):
        return self.sb.SdkBackend(d or tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)

    def test_a_deploy_poll_inside_a_quiesce_keeps_a_wake_at_the_quiesce_lapse(self):
        # refresh_drain_hold extended the hold (max) but re-armed the wake timer at its own 12.5s,
        # so the only wake fired under a still-held lease and nothing fired when the longer quiesce
        # lapsed: with no stop following (the CLI died between /down and the service call) held
        # fresh turns waited for an unrelated event (review find, 2026-09-06)
        be = self._backend()
        be.DRAIN_HOLD_TTL = 0.2
        wakes = []
        t0 = time.monotonic()
        be._wake_all_inputs = lambda: wakes.append(round(time.monotonic() - t0, 2))
        be.quiesce(1.0)
        be.refresh_drain_hold()                      # the parked poll lands inside the quiesce
        self.assertGreater(be._drain_hold_until, time.time() + 0.8, "the hold is still the quiesce's")
        self.assertGreater(be._drain_wake_timer.interval, 1.0,
                           "the re-armed wake covers the hold it just extended, not the 0.7s lease")
        time.sleep(1.8)
        self.assertFalse(be.drain_holding(), "the quiesce lapsed on its own")
        self.assertTrue(any(w >= 1.0 for w in wakes), "a wake fired at or after the lapse: %r" % (wakes,))

    def test_a_plain_deploy_poll_still_wakes_after_its_own_lease(self):
        be = self._backend()
        be.DRAIN_HOLD_TTL = 0.2
        be.refresh_drain_hold()
        self.assertAlmostEqual(be._drain_wake_timer.interval, 0.7, places=1,
                               msg="no quiesce: the wake is the lease TTL plus the half-second, as before")
        be._drain_wake_timer.cancel()

    # ── the resume notice after `romp down` + a later start ──────────────────
    def _cut_session(self, d, sid, working_t):
        sb = self.sb
        sb.write_reg(Path(d), sid, {"sid": sid, "name": "web", "cwd": "/tmp", "alive": True, "lastSid": sid})
        sb.append_state(Path(d), sid, "working", t=working_t)

    def _audit(self, d, t, action, **extra):
        row = {"t": t, "action": action}
        row.update(extra)
        with open(os.path.join(d, "restart-audit.jsonl"), "a") as f:
            f.write(json.dumps(row) + "\n")

    def _reconcile(self, d, be, sid):
        from unittest import mock
        be._ensure = lambda sid, on_boot_settled=None: on_boot_settled and on_boot_settled()
        with mock.patch.object(self.sb.subprocess, "run", return_value=mock.Mock(stdout="")):
            be._boot_reconcile([self.sb.read_reg(Path(d), sid)])
        return self.sb.read_reg(Path(d), sid).get("queue")

    def test_a_turn_romp_down_cut_hears_the_stop_and_the_gap(self):
        # `romp down` files {t, action: down} on restart-audit.jsonl before the stop; at the next
        # start the turn it cut is resumed with the stop and start times, not a bare "restarted"
        # that reads as a gap of seconds (review find, 2026-09-06)
        sb = self.sb
        d = tempfile.mkdtemp()
        sid = "11111111-2222-3333-4444-000000000001"
        now = int(time.time())
        self._cut_session(d, sid, working_t=now - 4 * 3600 - 240)     # the turn began before the stop
        self._audit(d, now - 4 * 3600, "down", cmd="romp down")
        q = self._reconcile(d, self._backend(d), sid)
        self.assertEqual(len(q), 1)
        self.assertTrue(q[0].startswith(sb._RESUME_NUDGE_LEAD), "the lead sentence is the restart notice's")
        self.assertIn("The stop was on purpose: romp down at ", q[0])
        self.assertIn("started again at ", q[0])
        self.assertIn("(4 h later)", q[0])
        self.assertIn("before relying on it", q[0])
        self.assertTrue(q[0].endswith(sb._RESUME_NUDGE_REST), "the disarm and the continue instruction follow")
        self.assertTrue(sb.is_resume_nudge(q[0]))
        self.assertNotIn("\u2014", q[0])
        self.assertTrue(q[0].startswith("<!-- romp-injected --><!-- romp-system -->[romp] "),
                        "a [romp] notice, the sanctioned family")

    def test_a_down_older_than_the_cut_turn_is_someone_elses_stop(self):
        # `romp down` Friday, `romp up` Monday (that boot said so), then a crash respawn: the newest
        # audit row is still the Friday `down`, but the turn it would explain began after it
        d = tempfile.mkdtemp()
        sid = "11111111-2222-3333-4444-000000000002"
        now = int(time.time())
        self._audit(d, now - 3 * 86400, "down", cmd="romp down")
        self._cut_session(d, sid, working_t=now - 600)
        q = self._reconcile(d, self._backend(d), sid)
        self.assertEqual(q, [self.sb.BOOT_RESUME_NUDGE], "the plain restart notice: this cut was not the down")

    def test_a_refresh_or_no_row_keeps_the_plain_notice(self):
        d = tempfile.mkdtemp()
        sid = "11111111-2222-3333-4444-000000000003"
        now = int(time.time())
        self._cut_session(d, sid, working_t=now - 100)
        self.assertEqual(self._reconcile(d, self._backend(d), sid), [self.sb.BOOT_RESUME_NUDGE],
                         "no audit row (a crash respawn): the notice as before")
        d2 = tempfile.mkdtemp()
        self._cut_session(d2, sid, working_t=now - 100)
        self._audit(d2, now - 3600, "down", cmd="romp down")
        self._audit(d2, now - 50, "refresh")               # the newest row is the refresh that cut this
        self.assertEqual(self._reconcile(d2, self._backend(d2), sid), [self.sb.BOOT_RESUME_NUDGE])

    def test_the_down_notice_names_dates_across_days_and_the_constant_is_unchanged(self):
        sb = self.sb
        stop = int(time.mktime((2026, 9, 4, 17, 12, 0, 0, 0, -1)))
        start = int(time.mktime((2026, 9, 7, 9, 3, 0, 0, 0, -1)))
        text = sb.down_resume_nudge(stop, start)
        self.assertIn("romp down at 2026-09-04 17:12, started again at 2026-09-07 09:03 (2 d 15 h later)", text)
        same = sb.down_resume_nudge(stop, stop + 3 * 3600 + 38 * 60)
        self.assertIn("romp down at 17:12, started again at 20:50 (3 h 38 min later)", same)
        self.assertIn("(under a minute later)", sb.down_resume_nudge(stop, stop + 5))
        self.assertIn("(12 min later)", sb.down_resume_nudge(stop, stop + 12 * 60 + 3))
        # the plain constant is byte-identical to its pre-split text (the fixtures and the popover
        # match on it), and the kernel's restart signature is a substring of both variants
        self.assertEqual(sb.BOOT_RESUME_NUDGE, (
            "<!-- romp-injected --><!-- romp-system -->[romp] The romp kernel restarted and cut this session's "
            "in-flight turn; the session has been resumed with its history intact. If the conversation tail "
            "shows '[Request interrupted by user]', that record came from this cut, not from the user: nobody "
            "asked you to stop. Re-read the tail of the conversation and pick the work back up where it "
            "stopped, without asking whether to continue. Any messages queued before the restart follow "
            "this one."))
        self.assertIn(km.INTR_RESTART_SIG, text)
        self.assertTrue(sb.is_resume_nudge(sb.BOOT_RESUME_NUDGE) and sb.is_resume_nudge(text)
                        and sb.is_resume_nudge(sb.CRASH_RESUME_NUDGE))
        self.assertFalse(sb.is_resume_nudge("a user's own message") or sb.is_resume_nudge(None))

    def test_newest_down_stop_reads_the_last_row_only(self):
        sb = self.sb
        d = tempfile.mkdtemp()
        self.assertIsNone(sb.newest_down_stop(Path(d)), "no file")
        self._audit(d, 1000, "down")
        self.assertEqual(sb.newest_down_stop(Path(d)), 1000)
        self._audit(d, 2000, "p2p-update", reason="from TESTHOST")
        self.assertIsNone(sb.newest_down_stop(Path(d)), "a later restart of another kind hides the down")
        with open(os.path.join(d, "restart-audit.jsonl"), "a") as f:
            f.write("not json\n")
        self.assertIsNone(sb.newest_down_stop(Path(d)), "a corrupt tail is nothing, never a raise")

    def test_the_thread_popover_and_the_wake_reorder_match_every_nudge(self):
        # two readers compared the queue head / the transcript text to BOOT_RESUME_NUDGE by
        # equality; the down variant must be treated the same, so both go through is_resume_nudge
        ksrc = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")).read()
        self.assertIn('getattr(sys.modules.get("romp_sdk_backend"), "is_resume_nudge", None)', ksrc)
        self.assertNotIn('"BOOT_RESUME_NUDGE", None)', ksrc, "no exact-text lookup remains in the kernel")
        ssrc = open(os.path.join(os.path.dirname(HERE), "kernel", "sdk_backend.py")).read()
        self.assertIn("head = rest[:1] if rest and is_resume_nudge(rest[0]) else []", ssrc)


if __name__ == "__main__":
    unittest.main()
