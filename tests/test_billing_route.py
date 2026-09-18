#!/usr/bin/env python3
"""`romp billing` (the user 2026-09-18, who wanted a CLI door for a session's billing: until this only the dashboard
could change it): the kernel routes behind the verb and the backend helpers they call, against a fake backend and a
real backend with no CLI. The end-to-end run of the real `bin/romp` against a lab kernel is tests/test_cli_billing_kernel.py,
which needs the SDK venv; everything here runs anywhere.

POST /billing mirrors the WS setAuth arm: the target resolves through _control_target (a name, a sid, an attached
host's session forwards over its tunnel and the far kernel's answer is the answer, the /end precedent), the pick
is validated by parse_pick, a per-session pick goes through the same park-or-apply gate the dashboard's op takes,
and a refusal names its reason (auth_unavailable_why) with a 4xx. `now` cuts the in-flight turn AFTER the pick is
recorded, so the aborted turn's settle arms the reconnect the pick asked for (no new arm path). `default` is the
one pick with no dashboard value: it clears the session's own pick so it follows the machine default again
(follow_default_auth). `allFollowing` writes a pick on every live follower through the walk set_auth_default's
followers take (set_auth_followers), with no /auth chip. GET /billing?target= reads the launched side, the pick
and the machine default, for a dormant session from its reg.

Real Handler on loopback (tests/test_kernel_headless_ops.py's pattern); the backend is a fake that records calls.
SYNTHETIC fixtures only: the notes-api demo world (web, api, tests), host TESTHOST, placeholder sids.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_billing_route", os.path.join(BIN, "romp-kernel"))
sb = load_source("romp_sdk_backend_billing_route", os.path.join(BIN, "romp_sdk_backend.py"))

SID = "11111111-2222-3333-4444-555555555555"
FAR_SID = "11111111-2222-3333-4444-666666666666"
FAR = {"host": "TESTHOST", "local_port": 1, "token": "t"}
MACHINE_LABEL = "dev@example.com"   # the machine login's display name, as the kernel's account probe would read it


def _register(sid, name):
    """A session the kernel knows by id AND by name: the names registry line, and an SDK registry entry that says alive,
    which is what the client doors' by-name lookup admits (a live generation of the name; a bare names line alone is a
    dormant session, addressed by id and 404 by name, _resolve_sid's rule)."""
    km.NAMES.mkdir(parents=True, exist_ok=True)
    (km.NAMES / sid).write_text("%s\t\n" % name)
    sdk = km.jd.STATE / "sdk"
    sdk.mkdir(parents=True, exist_ok=True)
    (sdk / (sid + ".json")).write_text(json.dumps({"sid": sid, "name": name, "alive": True}))


class _FakeBackend:
    """A backend that records the calls the routes make, in order, and answers what the test tells it to."""

    def __init__(self, busy=False, why="", outlook="now", view=None, default="key", explicit=False, default_login="",
                 labels=None):
        self.calls = []
        self._busy = busy
        self.why = why
        self.outlook = outlook
        self.view = view
        self.default, self.explicit, self.default_login, self.labels = default, explicit, default_login, labels or {}

    # the machine default as a follower bills it (the backend's resolution, not the picker's preselection)
    def fallback_auth(self):
        return self.default

    def explicit_default_auth(self):
        return self.default if self.explicit else ""

    def explicit_default_login(self):
        return self.default_login

    def login_display(self, login_id):
        return self.labels.get(login_id, "") if login_id else ""

    def set_auth(self, sid, value, chip=True):
        self.calls.append(("set_auth", sid, value, chip))
        return not self.why

    def interrupt(self, sid):
        self.calls.append(("interrupt", sid))
        return True

    def busy(self, sid):
        return self._busy

    def auth_unavailable_why(self, side, login_id=""):
        return self.why

    def auth_apply_outlook(self, sid):
        return self.outlook

    def follow_default_auth(self, sid):
        self.calls.append(("follow_default_auth", sid))
        return True

    def set_auth_followers(self, value):
        self.calls.append(("set_auth_followers", value))
        if self.why:
            return None
        return {"moved": ["web", "tests"], "skipped": ["api"]}

    def billing_view(self, sid):
        self.calls.append(("billing_view", sid))
        return self.view


class _RouteServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import threading
        from http.server import ThreadingHTTPServer
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        _register(SID, "web")

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def _post(self, body):
        import urllib.request, urllib.error
        req = urllib.request.Request("http://127.0.0.1:%d/billing" % self.port, method="POST",
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "X-Romp-Token": km.TOKEN})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")

    def _get(self, target, token=True):
        import urllib.request, urllib.error, urllib.parse
        req = urllib.request.Request("http://127.0.0.1:%d/billing?target=%s" % (self.port, urllib.parse.quote(target, safe="")),
                                     headers={"X-Romp-Token": km.TOKEN} if token else {})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                return e.code, json.loads(body or "{}")
            except ValueError:
                return e.code, {"text": body}

    def _local(self, fake):
        """The local arms: the fake owns SID, nothing parks, the machine login's label is a fixed read."""
        return mock.patch.multiple(km, **{
            "_gate_or_park": lambda sid, op: False,
            "_claude_account_label": lambda: MACHINE_LABEL,
        }), mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake))


class PerSessionPick(_RouteServer):
    """POST /billing {target, pick[, now]}: the dashboard's per-session setAuth as a route."""

    def test_a_pick_on_a_quiet_session_is_recorded_and_reconnects_now(self):
        fake = _FakeBackend(outlook="now")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login"})
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp, {"ok": True, "session": "web", "sid": SID, "pick": "login", "reconnect": "now",
                                "cut": False, "queued": False})
        self.assertEqual(fake.calls, [("set_auth", SID, "login", True)], "the dashboard's path: set_auth with its chip")

    def test_a_pick_mid_turn_reconnects_at_the_next_quiet_moment_and_cuts_nothing_without_now(self):
        fake = _FakeBackend(busy=True, outlook="deferred")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": SID, "pick": "key"})
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp["reconnect"], "at the next quiet moment")
        self.assertIs(resp["cut"], False)
        self.assertEqual([c[0] for c in fake.calls], ["set_auth"], "no interrupt unless asked")

    def test_now_records_the_pick_first_and_then_cuts_the_turn(self):
        # the order is the mechanism: set_auth writes the pending and the request, the interrupt ends the turn, and
        # the aborted turn's settle arms the reconnect the pick asked for; the interrupt first would settle a turn
        # with nothing pending and the pick would wait for the next one
        fake = _FakeBackend(busy=True, outlook="deferred")
        # the FIFO park the dashboard's op takes mid-turn is bypassed: parked, the pick would apply only when the pusher's
        # sweep found the session quiet, not at the cut turn's settle, and the interrupt would cut a turn with nothing pending
        with mock.patch.multiple(km, **{"_gate_or_park": lambda sid, op: self.fail("--now never parks"),
                                        "_claude_account_label": lambda: MACHINE_LABEL}), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)):
            code, resp = self._post({"target": "web", "pick": "login", "now": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual(fake.calls, [("set_auth", SID, "login", True), ("interrupt", SID)])
        self.assertEqual((resp["reconnect"], resp["cut"], resp["queued"]), ("now", True, False))
        self.assertIn(SID, km._interrupt_clicked, "the chip reads interrupting, as the /interrupt route's stop does")

    def test_now_on_a_quiet_session_cuts_nothing(self):
        fake = _FakeBackend(busy=False, outlook="now")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login", "now": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual([c[0] for c in fake.calls], ["set_auth"])
        self.assertEqual((resp["reconnect"], resp["cut"]), ("now", False))

    def test_now_under_live_work_cuts_the_turn_and_says_the_pick_is_held(self):
        fake = _FakeBackend(busy=True, outlook="held")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login", "now": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual([c[0] for c in fake.calls], ["set_auth", "interrupt"])
        self.assertEqual((resp["reconnect"], resp["cut"]), ("held for live work", True))

    def test_a_dormant_session_applies_at_its_next_launch(self):
        fake = _FakeBackend(outlook="next-launch")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login", "now": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp["reconnect"], "at its next launch")
        self.assertEqual([c[0] for c in fake.calls], ["set_auth"], "nothing runs, nothing to cut")

    def test_an_unchanged_pick_needs_no_reconnect(self):
        fake = _FakeBackend(outlook="none")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "key"})
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp["reconnect"], "none needed")

    def test_a_pick_the_gate_parks_is_queued_and_applies_at_the_next_quiet_moment(self):
        # the dashboard's op mid-turn or mid-compaction: parked in the /model FIFO, applied when the session is quiet
        fake = _FakeBackend(busy=True, outlook="deferred")
        parked = []
        with mock.patch.multiple(km, **{"_gate_or_park": lambda sid, op: parked.append(op) or True,
                                        "_claude_account_label": lambda: MACHINE_LABEL}), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)):
            code, resp = self._post({"target": "web", "pick": "login"})
        self.assertEqual(code, 200, resp)
        self.assertEqual((resp["reconnect"], resp["queued"], resp["cut"]), ("at the next quiet moment", True, False))
        self.assertEqual(parked, [("auth", "login")], "the FIFO's own op shape, so the replay applies it")
        self.assertEqual(fake.calls, [], "the FIFO applies it; nothing is cut")

    def test_now_during_a_compaction_is_refused_not_cut(self):
        fake = _FakeBackend(busy=True, outlook="deferred")
        with mock.patch.multiple(km, **{"_compacting_now": lambda sid, **kw: True, "_claude_account_label": lambda: MACHINE_LABEL}), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)):
            code, resp = self._post({"target": "web", "pick": "login", "now": True})
        self.assertEqual(code, 409, resp)
        self.assertIs(resp["ok"], False)
        self.assertIn("compacting", resp["error"])
        self.assertEqual(fake.calls, [], "a compaction is never cut for a billing pick; without --now the pick queues behind it")

    def test_a_refused_side_answers_409_with_the_backends_reason(self):
        fake = _FakeBackend(why=sb._cred.WHY_NO_LOGIN)
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login"})
        self.assertEqual(code, 409, resp)
        self.assertEqual(resp, {"ok": False, "error": sb._cred.WHY_NO_LOGIN})

    def test_a_stored_login_refusal_names_that_login_reason(self):
        # the WS arm asks auth_unavailable_why with the whole pick value, which a "login:<id>" answers "" to; the route
        # parses the pick and asks with the side and the id, so a stored login's own reason reaches the caller
        seen = []

        class _Why(_FakeBackend):
            def auth_unavailable_why(self, side, login_id=""):
                seen.append((side, login_id))
                return "that login's record is missing"
        fake = _Why()
        fake.why = "x"   # set_auth refuses
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login:0123456789ab"})
        self.assertEqual(code, 409, resp)
        self.assertEqual(seen[-1], ("login", "0123456789ab"))
        self.assertEqual(resp["error"], "that login's record is missing")

    def test_a_junk_pick_is_400_naming_the_choices(self):
        fake = _FakeBackend()
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "auto"})
        self.assertEqual(code, 400, resp)
        self.assertIs(resp["ok"], False)
        for word in ("key", "login", "login:<id>", "default"):
            self.assertIn(word, resp["error"])
        self.assertEqual(fake.calls, [])

    def test_a_missing_target_or_pick_is_400(self):
        fake = _FakeBackend()
        a, b = self._local(fake)
        with a, b:
            self.assertEqual(self._post({"pick": "login"})[0], 400)
            self.assertEqual(self._post({"target": "web"})[0], 400)
        self.assertEqual(fake.calls, [])

    def test_an_unknown_session_is_the_resolvers_404(self):
        fake = _FakeBackend()
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "nosuch", "pick": "login"})
        self.assertEqual(code, 404, resp)
        self.assertIs(resp["ok"], False)
        self.assertIn("nosuch", resp["error"])
        self.assertEqual(fake.calls, [], "a phantom sid never reaches the backend")

    def test_a_backend_without_a_billing_pick_is_refused_by_name(self):
        class _Codexish:
            def set_auth(self, sid, value):
                return False

            def auth_unavailable_why(self, *a):
                return ""
        with mock.patch.multiple(km, **{"_gate_or_park": lambda sid, op: False, "_claude_account_label": lambda: MACHINE_LABEL}), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: _Codexish())):
            code, resp = self._post({"target": "web", "pick": "login"})
        self.assertEqual(code, 409, resp)
        self.assertIs(resp["ok"], False)
        self.assertIn("Claude Code session", resp["error"])
        with mock.patch.multiple(km, **{"_gate_or_park": lambda sid, op: False}), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: _Codexish())):
            code, resp = self._post({"target": "web", "pick": "default"})
        self.assertEqual(code, 409, resp)
        self.assertIn("Claude Code session", resp["error"])


class DefaultPick(_RouteServer):
    """`default`: the pick with no dashboard value. It clears the session's own pick (follow_default_auth)."""

    def test_default_clears_the_sessions_own_pick(self):
        fake = _FakeBackend(outlook="now")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "default"})
        self.assertEqual(code, 200, resp)
        self.assertEqual(fake.calls, [("follow_default_auth", SID)], "not set_auth: there is no value that clears")
        self.assertEqual(resp, {"ok": True, "session": "web", "sid": SID, "pick": "default", "reconnect": "now",
                                "cut": False, "queued": False, "default": "key"}, "the default it follows now, for the caller's line")

    def test_default_with_now_cuts_the_turn_after_the_clear(self):
        fake = _FakeBackend(busy=True, outlook="deferred")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "default", "now": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual(fake.calls, [("follow_default_auth", SID), ("interrupt", SID)])
        self.assertEqual((resp["reconnect"], resp["cut"]), ("now", True))

    def test_default_is_never_parked_as_a_pick_value(self):
        # the FIFO's ("auth", value) replay calls set_auth, which refuses "default"; the clear takes the follower walk's
        # own road instead (the fix's mechanism: request_reconnect's arm rule defers to the settle that finds the
        # session quiet), so mid-turn it is applied now and reconnects at the next quiet moment
        fake = _FakeBackend(busy=True, outlook="deferred")
        with mock.patch.multiple(km, **{"_gate_or_park": lambda sid, op: self.fail("default is never parked"),
                                        "_claude_account_label": lambda: MACHINE_LABEL}), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)):
            code, resp = self._post({"target": "web", "pick": "default"})
        self.assertEqual(code, 200, resp)
        self.assertEqual(fake.calls, [("follow_default_auth", SID)])
        self.assertEqual((resp["reconnect"], resp["queued"], resp["cut"]), ("at the next quiet moment", False, False))


class AllFollowing(_RouteServer):
    """POST /billing {pick, allFollowing}: the walk over this kernel's live followers."""

    def test_the_walk_answers_the_names_moved_and_skipped(self):
        fake = _FakeBackend()
        with mock.patch.object(km, "_sdk", lambda: fake):
            code, resp = self._post({"pick": "key", "allFollowing": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp, {"ok": True, "pick": "key", "moved": 2, "skipped": 1,
                                "sessions": ["web", "tests"], "skippedSessions": ["api"]})
        self.assertEqual(fake.calls, [("set_auth_followers", "key")])

    def test_the_walk_takes_the_sdk_backend_not_a_target(self):
        fake = _FakeBackend()
        with mock.patch.object(km, "_sdk", lambda: fake), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: self.fail("no target to resolve"))):
            code, resp = self._post({"pick": "login", "allFollowing": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual(fake.calls, [("set_auth_followers", "login")])

    def test_a_refused_side_is_409_with_the_reason_and_moves_nothing(self):
        fake = _FakeBackend(why=sb._cred.WHY_NO_HELPER)
        with mock.patch.object(km, "_sdk", lambda: fake):
            code, resp = self._post({"pick": "key", "allFollowing": True})
        self.assertEqual(code, 409, resp)
        self.assertEqual(resp, {"ok": False, "error": sb._cred.WHY_NO_HELPER})

    def test_default_is_not_a_pick_for_the_walk(self):
        # the followers already follow the default: there is nothing to write
        fake = _FakeBackend()
        with mock.patch.object(km, "_sdk", lambda: fake):
            code, resp = self._post({"pick": "default", "allFollowing": True})
        self.assertEqual(code, 400, resp)
        self.assertEqual(fake.calls, [])

    def test_no_sdk_backend_is_a_loud_refusal(self):
        with mock.patch.object(km, "_sdk", lambda: None):
            code, resp = self._post({"pick": "key", "allFollowing": True})
        self.assertEqual(code, 409, resp)
        self.assertIs(resp["ok"], False)


class Read(_RouteServer):
    """GET /billing?target=: the launched side, the pick and the machine default."""

    VIEW = {"launched": "key", "launchedLogin": "", "launchedLabel": "", "live": "key",
            "pick": {"auth": "key", "login": "", "label": "", "explicit": False}, "pending": False, "held": False}

    def test_the_read_composes_the_session_view_with_the_machine_default(self):
        fake = _FakeBackend(view=dict(self.VIEW))
        a, b = self._local(fake)
        with a, b:
            code, resp = self._get("web")
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp, {"ok": True, "session": "web", "sid": SID, **self.VIEW,
                                "default": {"auth": "key", "login": "", "explicit": False, "label": ""}})
        self.assertEqual(fake.calls, [("billing_view", SID)])

    def test_a_stored_login_default_carries_its_label(self):
        fake = _FakeBackend(view=dict(self.VIEW), default="login", explicit=True, default_login="0123456789ab",
                            labels={"0123456789ab": "work"})
        a, b = self._local(fake)
        with a, b:
            code, resp = self._get(SID)
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp["default"], {"auth": "login", "login": "0123456789ab", "explicit": True, "label": "work"})

    def test_the_machine_login_default_carries_the_machines_label(self):
        fake = _FakeBackend(view=dict(self.VIEW), default="login", explicit=True)
        a, b = self._local(fake)
        with a, b:
            code, resp = self._get(SID)
        self.assertEqual(resp["default"], {"auth": "login", "login": "", "explicit": True, "label": MACHINE_LABEL})

    def test_the_default_is_what_a_follower_bills_not_the_pickers_preselection(self):
        # a remembered per-session pick seeds the picker's preselected choice (_auth_avail's `default`) while no explicit
        # default is set; a follower does not bill it, so the read must not say it does
        fake = _FakeBackend(view=dict(self.VIEW), default="key", explicit=False)
        with mock.patch.multiple(km, **{"_gate_or_park": lambda sid, op: False, "_claude_account_label": lambda: MACHINE_LABEL,
                                        "_auth_avail_status": lambda: {"default": "login", "defaultExplicit": False}}), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)):
            code, resp = self._get(SID)
        self.assertEqual(resp["default"], {"auth": "key", "login": "", "explicit": False, "label": ""})

    def test_a_session_whose_record_will_not_read_is_refused(self):
        fake = _FakeBackend(view=None)
        a, b = self._local(fake)
        with a, b:
            code, resp = self._get("web")
        self.assertEqual(code, 409, resp)
        self.assertIs(resp["ok"], False)

    def test_an_unknown_session_is_404_and_a_missing_target_400(self):
        fake = _FakeBackend(view=dict(self.VIEW))
        a, b = self._local(fake)
        with a, b:
            code, resp = self._get("nosuch")
            self.assertEqual(code, 404, resp)
            self.assertIn("nosuch", resp["error"])
            code, resp = self._get("")
            self.assertEqual(code, 400, resp)
        self.assertEqual(fake.calls, [])

    def test_the_read_is_token_gated_like_every_route(self):
        code, _ = self._get("web", token=False)
        self.assertEqual(code, 403)


class RemoteForwarding(_RouteServer):
    """A session an attached host runs: the request forwards over its tunnel and the far answer is the answer
    (the /end precedent, tests/test_kernel_remote_end_interrupt.py)."""

    def _forward(self, method, body, far_reply, target=FAR_SID):
        crossed = []

        def rec(r, p, b, method="POST"):
            crossed.append((r, p, b, method))
            return (200, far_reply, json.dumps(far_reply)) if far_reply is not None else (0, None, "")

        def no_local(sid):
            self.fail("a remote session's billing must not touch the local backend")

        with mock.patch.object(km, "_host_for_sid", lambda sid: dict(FAR) if sid == FAR_SID else None), \
             mock.patch.object(km, "_remote_forward_answer", rec), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(no_local)):
            code, resp = self._post(body) if method == "POST" else self._get(target)
        self.assertEqual(len(crossed), 1, "exactly one forward over the tunnel")
        return code, resp, crossed[0]

    def test_a_pick_crosses_the_wire_with_its_now_flag_by_far_sid(self):
        code, resp, (r, path, body, method) = self._forward("POST", {"target": FAR_SID, "pick": "login", "now": True}, {"ok": True, "reconnect": "now", "cut": True})
        self.assertEqual((r["host"], path, method), ("TESTHOST", "/billing", "POST"))
        self.assertEqual(body, {"target": FAR_SID, "pick": "login", "now": True},
                         "the validated fields only, the far kernel resolves the sid it lists")
        self.assertEqual((code, resp), (200, {"ok": True, "reconnect": "now", "cut": True}), "the far answer rides back as is")

    def test_a_dead_tunnel_is_not_an_ok(self):
        code, resp, _ = self._forward("POST", {"target": FAR_SID, "pick": "key"}, None)
        self.assertEqual(code, 200)
        self.assertIs(resp["ok"], False)
        self.assertIn("TESTHOST", resp["error"])
        self.assertIn("not changed", resp["error"])

    def test_a_far_refusal_rides_back_verbatim(self):
        refusal = {"ok": False, "error": "x"}
        code, resp, _ = self._forward("POST", {"target": FAR_SID, "pick": "key"}, dict(refusal))
        self.assertEqual((code, resp), (200, refusal))

    def test_the_read_forwards_as_a_get_with_the_far_sid(self):
        far = {"ok": True, "session": "far-web", "sid": FAR_SID, "launched": "login"}
        code, resp, (r, path, body, method) = self._forward("GET", None, far)
        self.assertEqual((r["host"], method, body), ("TESTHOST", "GET", None))
        self.assertEqual(path, "/billing?target=" + FAR_SID)
        self.assertEqual((code, resp), (200, far))


class BackendHelpers(unittest.TestCase):
    """The backend half on a REAL SdkBackend with sessions that have no CLI: what the routes call."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        Path(self.d, "session-hosts").write_text("off")   # a test that mints its own state root pins hosts off (2026-09-11)
        self.logs = []
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=self.logs.append)
        self.be.login_ok = lambda: True
        self.be.key_state = lambda: "ok"     # an apiKeyHelper is configured: both sides billable
        self.n = 0

    def _sess(self, name, auth="", launched=None, alive=True):
        self.n += 1
        sid = "11111111-2222-3333-4444-%012d" % self.n
        reg = {"sid": sid, "name": name, "cwd": self.d, "alive": alive, "lastSid": sid}
        if auth:
            reg["auth"] = auth
        sb.write_reg(Path(self.d), sid, reg)
        s = sb.SdkSession(self.be, dict(reg))
        s._launched_auth = launched
        self.be.sessions[sid] = s
        return s

    def _reg(self, sid):
        return sb.read_reg(Path(self.d), sid)

    @staticmethod
    def _queue_loop(s):
        """A loop double that records request_reconnect's callback without running it: the session reads as one whose
        request can arm (the walk's rule for the relaunch flag), and nothing composes a CLI."""
        queued = []
        s.loop = type("_Queue", (), {"call_soon_threadsafe": lambda self_, cb, *a: queued.append((cb, a))})()
        return queued

    def _gestures(self, sid):
        p = Path(self.d, "states", sid + ".jsonl")
        if not p.exists():
            return []
        return [json.loads(ln)["cmdGesture"] for ln in p.read_text().splitlines() if "cmdGesture" in ln]

    def test_set_auth_chip_false_writes_the_pick_without_the_auth_chip(self):
        s = self._sess("web", launched="login")
        self.assertTrue(self.be.set_auth(s.sid, "key", chip=False))
        self.assertEqual((self._reg(s.sid)["auth"], s.auth, s._auth_pending), ("key", "key", "key"))
        self.assertEqual(self._gestures(s.sid), [], "no /auth chip: the session made no pick")
        t = self._sess("api", launched="login")
        self.assertTrue(self.be.set_auth(t.sid, "key"))
        self.assertEqual(self._gestures(t.sid), ["/auth key"], "the dashboard's path is unchanged: one chip")

    def test_set_auth_followers_moves_the_followers_and_skips_the_picked(self):
        web = self._sess("web", launched="login")
        queued = self._queue_loop(web)               # a running follower: its request can arm
        api = self._sess("api", auth="login", launched="login")
        tests = self._sess("tests", launched="key")
        docs = self._sess("docs", launched="login")   # a follower with no loop yet: its first connect composes from the reg
        ended = self._sess("notes", launched="login")
        ended.ended = True
        out = self.be.set_auth_followers("key")
        self.assertEqual(out, {"moved": ["docs", "tests", "web"], "skipped": ["api"]}, "names sorted: the roster's order is not a contract")
        self.assertEqual((self._reg(web.sid)["auth"], web._auth_pending, web._relaunch_bounded), ("key", "key", True),
                         "a follower running the other side: the pick, a pending reconnect, and a bounded relaunch slot")
        self.assertEqual(len(queued), 1, "the reconnect was asked on its loop")
        self.assertEqual((self._reg(docs.sid)["auth"], docs._auth_pending, docs._relaunch_bounded), ("key", "key", False),
                         "no loop: the pick and the pending, but no slot (flagged only when the request can arm, the walk's rule)")
        self.assertEqual((self._reg(tests.sid)["auth"], tests._auth_pending, tests._relaunch_bounded), ("key", "", False),
                         "a follower already running the side: the pick written, no reconnect, no slot held")
        self.assertEqual(self._reg(api.sid)["auth"], "login", "the picked session keeps its own pick")
        self.assertNotIn("auth", self._reg(ended.sid), "an ended session is nothing to move")
        for s in (web, api, tests, docs):
            self.assertEqual(self._gestures(s.sid), [], "no /auth chip on the walk")

    def test_set_auth_followers_refuses_a_side_this_box_cannot_bill(self):
        web = self._sess("web", launched="key")
        self.be.login_ok = lambda: False
        self.assertIsNone(self.be.set_auth_followers("login"))
        self.assertEqual(self.be.last_auth_refusal, sb._cred.WHY_NO_LOGIN)
        self.assertNotIn("auth", self._reg(web.sid), "nothing moved")
        self.assertIsNone(self.be.set_auth_followers("auto"), "not a pick")

    def test_follow_default_auth_clears_the_pick_and_reconnects_when_the_default_is_the_other_side(self):
        # the default is the helper rule (a helper is configured: the key); a session picked onto the login and running it
        s = self._sess("api", auth="login", launched="login")
        s.auth_live = "login"
        self.be._update_reg(s.sid, apiKeyAuth=False)
        queued = self._queue_loop(s)
        self.assertTrue(self.be.follow_default_auth(s.sid))
        reg = self._reg(s.sid)
        self.assertEqual((reg["auth"], reg["authLogin"], s.auth, s.auth_login), ("", "", "", ""))
        self.assertEqual((s._auth_pending, reg["authPending"], s._relaunch_bounded), ("key", True, True),
                         "it follows the default now, runs the other side, so the walk's step asks the reconnect")
        self.assertEqual(len(queued), 1, "…on its loop")
        self.assertIs(reg["apiKeyAuth"], False, "the reg keeps the CLI's last report: it describes the process until the relaunch")
        self.assertEqual(self._gestures(s.sid), [], "no /auth chip: the session made no pick")
        self.assertTrue(any("follows the machine default again: automatic (the key on this box)" in m and "runs on the login" in m
                            for m in self.logs), self.logs[-3:])
        # the same clear on a session whose loop has not started: the pending rides the session and the reg, no slot
        t = self._sess("web", auth="login", launched="login")
        self.assertTrue(self.be.follow_default_auth(t.sid))
        self.assertEqual((t._auth_pending, self._reg(t.sid)["authPending"], t._relaunch_bounded), ("key", True, False))

    def test_follow_default_auth_on_a_session_already_running_the_default_reconnects_nothing(self):
        s = self._sess("api", auth="key", launched="key")
        self.assertTrue(self.be.follow_default_auth(s.sid))
        reg = self._reg(s.sid)
        self.assertEqual((reg["auth"], s.auth, s._auth_pending), ("", "", ""))
        self.assertFalse(reg.get("authPending"))

    def test_follow_default_auth_withdraws_a_pending_pick_the_default_makes_moot(self):
        # picked onto the login while running the key, the reconnect still pending; the default (the key) is what it runs
        s = self._sess("api", auth="login", launched="key")
        s._auth_pending = "login"
        self.be._update_reg(s.sid, authPending=True)
        self.assertTrue(self.be.follow_default_auth(s.sid))
        reg = self._reg(s.sid)
        self.assertEqual((reg["auth"], s._auth_pending, reg["authPending"]), ("", "", False))

    def test_follow_default_auth_on_a_dormant_session_clears_the_reg(self):
        self.n += 1
        sid = "11111111-2222-3333-4444-%012d" % self.n
        sb.write_reg(Path(self.d), sid, {"sid": sid, "name": "docs", "cwd": self.d, "alive": True, "auth": "login",
                                          "authLogin": "", "authPending": True})
        self.assertTrue(self.be.follow_default_auth(sid))
        reg = self._reg(sid)
        self.assertEqual((reg["auth"], reg["authLogin"], reg["authPending"]), ("", "", False),
                         "a picked session's pending described its pick's reconnect: moot once the pick is cleared")
        # a dormant session that already follows the default keeps its authPending: the ask a follower carries across a
        # kernel restart (round 1 of the walk's review); its next launch decides
        self.n += 1
        fsid = "11111111-2222-3333-4444-%012d" % self.n
        sb.write_reg(Path(self.d), fsid, {"sid": fsid, "name": "tests", "cwd": self.d, "alive": True, "authPending": True})
        self.assertTrue(self.be.follow_default_auth(fsid))
        self.assertEqual((self._reg(fsid).get("auth"), self._reg(fsid)["authPending"]), ("", True))
        self.assertFalse(self.be.follow_default_auth("11111111-2222-3333-4444-999999999999"), "no record: refused")

    def test_auth_apply_outlook_names_the_schedule(self):
        self.assertEqual(self.be.auth_apply_outlook("11111111-2222-3333-4444-999999999999"), "next-launch")
        s = self._sess("web", launched="login")
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "none", "nothing pending")
        self.be.set_auth(s.sid, "key", chip=False)
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "next-launch", "pending, and no process to reconnect")
        s.loop = object()                    # a live session: the loop's presence is what request_reconnect reads
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "now")
        s.inflight = 1
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "deferred")
        with s._hold_write():
            s._reconnect_surfaces.add("auth")
            s._reconnect_held_for_work = True
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "held")

    def test_billing_view_reads_a_live_session_and_a_dormant_reg(self):
        s = self._sess("web", auth="login", launched="key")
        s.auth_live = "key"
        s._auth_pending = "login"
        self.assertEqual(self.be.billing_view(s.sid), {
            "launched": "key", "launchedLogin": "", "launchedLabel": "", "live": "key",
            "pick": {"auth": "login", "login": "", "label": "", "explicit": True}, "pending": True, "held": False})
        self.n += 1
        sid = "11111111-2222-3333-4444-%012d" % self.n
        sb.write_reg(Path(self.d), sid, {"sid": sid, "name": "docs", "cwd": self.d, "alive": True, "apiKeyAuth": False})
        self.assertEqual(self.be.billing_view(sid), {
            "launched": None, "launchedLogin": "", "launchedLabel": "", "live": "login",
            "pick": {"auth": "key", "login": "", "label": "", "explicit": False}, "pending": False, "held": False},
            "a dormant follower: no process, the last init's side, the default it follows (the helper rule: the key)")
        self.assertIsNone(self.be.billing_view("11111111-2222-3333-4444-999999999999"))


if __name__ == "__main__":
    unittest.main()
