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
import threading
import time
import unittest
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
# a test that mints its own state root pins hosts off (2026-09-11): the real handler's target resolution scans the live
# roster over this root, and a root with no toggle would start a session host for any session a case connected
_ROOT = Path(os.environ["XDG_STATE_HOME"], "romp")
_ROOT.mkdir(parents=True, exist_ok=True)
(_ROOT / "session-hosts").write_text("off")
km = load_source("romp_kernel_billing_route", os.path.join(BIN, "romp-kernel"))
sb = load_source("romp_sdk_backend_billing_route", os.path.join(BIN, "romp_sdk_backend.py"))

SID = "11111111-2222-3333-4444-555555555555"
FAR_SID = "11111111-2222-3333-4444-666666666666"
FAR = {"host": "TESTHOST", "local_port": 1, "token": "t"}
# the synthetic stored-login id, ASSEMBLED at run time from parts too short for any scanner rule (round 2 of the review,
# 2026-09-18; the rule tests/gitleaks-config.bats states): a 12-hex literal beside `auth` or `login:` reads as a key to
# gitleaks' generic-api-key rule, and two such lines made the pre-push hook refuse the branch. Named with no scanner
# keyword in the name either (an `AUTH_`- or `KEY_`-named constant re-creates the hit)
LID = "".join(("0123", "4567", "89ab"))
MACHINE_LABEL = "dev@example.com"   # the machine login's display name, as the kernel's account probe would read it
PREDATES_FAR = ("the kernel on TESTHOST predates romp billing's routes (GET and POST /billing): run `romp update TESTHOST` from "
                "here, or update romp there and restart it")


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
                 labels=None, inflight=None, unwritten=None, explicit_pick=None, outlooks=None, failed=None, staggered=False):
        self.calls = []
        self._busy = busy
        self.failed = list(failed or [])       # the walk's followers whose step raised (the per-session try, 2026-09-18)
        self.staggered = staggered             # whether an asked relaunch waits for its spawn slot (auth_relaunch_staggered)
        # a turn in flight is NOT the same as busy: busy is also true for a queued or an untaken text with no turn open
        # (SdkBackend.busy's three readings), and only an open turn is something --now can cut (round 1 of the review).
        # None follows busy, for the cases that do not care
        self._inflight = busy if inflight is None else inflight
        self.unwritten = list(unwritten or [])
        self.why = why
        self.outlook = outlook
        self.view = view
        self.default, self.explicit, self.default_login, self.labels = default, explicit, default_login, labels or {}
        # the explicit default AS SET (a pick value): by default the resolution itself, so the two agree; a case that
        # models the fall (this box cannot bill the explicit default) hands in the pick the user set (round 2 of the review)
        self.explicit_pick = explicit_pick
        self.outlooks = outlooks if outlooks is not None else {"web": "now", "tests": "none"}

    # the machine default as a follower bills it (the backend's resolution, not the picker's preselection)
    def fallback_auth(self):
        return self.default

    def explicit_default_auth(self):
        return self.default if self.explicit else ""

    def explicit_default_login(self):
        return self.default_login

    def explicit_default_pick(self):
        if self.explicit_pick is not None:
            return self.explicit_pick
        if not self.explicit:
            return ""
        return ("login:" + self.default_login) if self.default == "login" and self.default_login else self.default

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

    def turn_open(self, sid):
        return self._inflight

    def auth_unavailable_why(self, side, login_id=""):
        return self.why

    def auth_apply_outlook(self, sid):
        return self.outlook

    def auth_relaunch_staggered(self, sid):
        return self.staggered                  # a bare read, as auth_apply_outlook is: not a recorded call

    def follow_default_auth(self, sid):
        self.calls.append(("follow_default_auth", sid))
        return True

    def set_auth_followers(self, value):
        self.calls.append(("set_auth_followers", value))
        if self.why:
            return None
        return {"moved": ["web", "tests"], "skipped": ["api"], "unwritten": list(self.unwritten), "failed": list(self.failed),
                "movedSids": [SID, FAR_SID], "outlook": dict(self.outlooks)}

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

    def _post(self, body, token=True):
        """POST /billing with the serve token (True), none (False) or the string given (a wrong one)."""
        import urllib.request, urllib.error
        headers = {"Content-Type": "application/json"}
        if token is True:
            headers["X-Romp-Token"] = km.TOKEN
        elif token:
            headers["X-Romp-Token"] = token
        req = urllib.request.Request("http://127.0.0.1:%d/billing" % self.port, method="POST",
                                     data=json.dumps(body).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            text = e.read().decode()
            try:
                return e.code, json.loads(text or "{}")
            except ValueError:
                return e.code, {"text": text}      # the preamble's 403 carries no JSON body

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

    def _local(self, fake, **more):
        """The local arms: the fake owns SID, nothing parks, the machine login's label is a fixed read, and the park
        reason's own reads (finding 4 of round 1) are quiet unless a case sets one."""
        stubs = {
            "_gate_or_park": lambda sid, op: False,
            "_claude_account_label": lambda: MACHINE_LABEL,
            "_compacting_now": lambda sid, **kw: False,
            "_limit_hold": lambda sid, usage=None: None,
        }
        stubs.update(more)
        return mock.patch.multiple(km, **stubs), mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake))


class PerSessionPick(_RouteServer):
    """POST /billing {target, pick[, now]}: the dashboard's per-session setAuth as a route."""

    def test_a_pick_on_a_quiet_session_is_recorded_and_reconnects_now(self):
        fake = _FakeBackend(outlook="now")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login"})
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp, {"ok": True, "session": "web", "sid": SID, "pick": "login", "reconnect": "now",
                                "cut": False, "queued": False, "superseded": 0})
        self.assertEqual(fake.calls, [("set_auth", SID, "login", True)], "the dashboard's path: set_auth with its chip")

    def test_a_pick_mid_turn_reconnects_at_the_end_of_the_open_turn_and_cuts_nothing_without_now(self):
        fake = _FakeBackend(busy=True, outlook="deferred")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": SID, "pick": "key"})
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp["reconnect"], "at the end of the open turn")
        self.assertIs(resp["cut"], False)
        self.assertEqual([c[0] for c in fake.calls], ["set_auth"], "no interrupt unless asked")

    def test_now_with_a_text_waiting_and_no_open_turn_cuts_nothing_and_says_the_next_quiet_moment(self):
        # round 1 of the review (finding 1): busy() is true for a queued or an untaken text with no turn in flight (a
        # session mid-reconnect with a message queued, say), and the cut used to fire on it: the interrupt ladder then
        # SIGINTed a CLI being launched, and the verb printed "the in-flight turn was cut" with no turn in flight. The
        # outlook names that state apart ("queued") and the cut asks the backend for an OPEN turn, never for busy
        fake = _FakeBackend(busy=True, inflight=False, outlook="queued")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login", "now": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual([c[0] for c in fake.calls], ["set_auth"], "nothing in flight, nothing to cut")
        self.assertEqual((resp["reconnect"], resp["cut"], resp["queued"]), ("at the next quiet moment", False, False))

    def test_now_records_the_pick_first_and_then_cuts_the_turn(self):
        # the order is the mechanism: set_auth writes the pending and the request, the interrupt ends the turn, and
        # the aborted turn's settle arms the reconnect the pick asked for; the interrupt first would settle a turn
        # with nothing pending and the pick would wait for the next one
        fake = _FakeBackend(busy=True, inflight=True, outlook="deferred")
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
        fake = _FakeBackend(busy=True, inflight=True, outlook="held")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login", "now": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual([c[0] for c in fake.calls], ["set_auth", "interrupt"])
        self.assertEqual((resp["reconnect"], resp["cut"]), ("held for live work", True))

    def test_now_under_live_work_with_no_open_turn_cuts_nothing(self):
        # live work (a background task) holds the pick while the session sits idle between turns: there is no turn to
        # cut, and an interrupt would only latch "interrupting" on a session with no settle to clear it
        fake = _FakeBackend(busy=True, inflight=False, outlook="held")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login", "now": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual([c[0] for c in fake.calls], ["set_auth"])
        self.assertEqual((resp["reconnect"], resp["cut"]), ("held for live work", False))

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

    def test_a_pick_the_gate_parks_is_queued_and_applies_at_the_end_of_the_open_turn(self):
        # the dashboard's op mid-turn: parked in the /model FIFO, applied when the session is quiet; the answer names the
        # reason the pick waits (the open turn, read as _ops_gate reads it: the backend's busy)
        fake = _FakeBackend(busy=True, outlook="deferred")
        parked = []
        a, b = self._local(fake, _gate_or_park=lambda sid, op: parked.append(op) or True)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login"})
        self.assertEqual(code, 200, resp)
        self.assertEqual((resp["reconnect"], resp["queued"], resp["cut"], resp["parked"]),
                         ("at the end of the open turn", True, False, "turn"))
        self.assertEqual(parked, [("auth", "login")], "the FIFO's own op shape, so the replay applies it")
        self.assertEqual(fake.calls, [], "the FIFO applies it; nothing is cut")

    def test_a_parked_pick_names_the_reason_it_waits_for(self):
        # round 1 of the review (finding 4): _ops_gate parks for five reasons and every park used to answer "at the next
        # quiet moment": a quiet session under a usage-limit hold was promised a quiet moment while the pick waited for
        # the hold to lift, and a move in flight got the same words. The auth pick is NOT exempted from the hold: the hold
        # is the kernel's FIFO gate on every drive op, and the pick queues behind it like any other; the words say which
        # Round 2 of the review: "turn" was answered from busy alone, which is also true for a queued or an untaken text
        # with no turn in flight, so the verb offered --now for a park a cut could not end, and the re-run with --now cut
        # nothing and answered "a message waits to run first" against the line it had just acted on. "waiting" names that
        # state with the unparked road's words (no --now offer); a backend that does not run the sid (turn_open None)
        # keeps "turn", since _working_now then parked on the cached transcript parse, where the open turn is real
        class _NoTurnOpen(_FakeBackend):
            def turn_open(self, sid):
                return None
        cases = [
            ("limit", {"_limit_hold": lambda sid, usage=None: {"reason": "x"}}, _FakeBackend(outlook="deferred"), "limit",
             "when the usage hold lifts"),
            ("compaction", {"_compacting_now": lambda sid, **kw: True}, _FakeBackend(outlook="deferred"), "compaction",
             "after the compaction"),
            ("move", {}, _FakeBackend(outlook="deferred"), "move", "after the move finishes"),
            ("turn", {}, _FakeBackend(busy=True, inflight=True, outlook="deferred"), "turn", "at the end of the open turn"),
            ("waiting", {}, _FakeBackend(busy=True, inflight=False, outlook="queued"), "waiting", "at the next quiet moment"),
            ("turn-unknown", {}, _NoTurnOpen(busy=True, outlook="deferred"), "turn", "at the end of the open turn"),
            ("queue", {}, _FakeBackend(outlook="deferred"), "queue", "after the work queued ahead of it"),
        ]
        for case, stubs, fake, reason, words in cases:
            a, b = self._local(fake, _gate_or_park=lambda sid, op: True, **stubs)
            if case == "move":
                km._moving.add(SID)
            if case == "queue":
                km._pending_ops[SID] = [("auth", "login")]
            try:
                with a, b:
                    code, resp = self._post({"target": "web", "pick": "login"})
            finally:
                km._moving.discard(SID)
                km._pending_ops.pop(SID, None)
            self.assertEqual(code, 200, (case, resp))
            self.assertEqual((resp["queued"], resp["parked"], resp["reconnect"]), (True, reason, words), case)
            self.assertEqual(fake.calls, [], case)

    def test_now_or_default_during_a_move_is_refused_not_cut(self):
        # round 2 of the review (route-2): _ops_gate parks every drive op while `_moving` holds the sid, so nothing reaches
        # the CLI while be.move() waits on its set_cwd answer; the --now road and the `default` road (never parked, with or
        # without --now) reached set_auth's request, whose arm on a quiet session tore the client down under that request,
        # so the move failed or landed on a replaced process while the verb answered a clean apply
        for body in ({"target": "web", "pick": "login", "now": True}, {"target": "web", "pick": "default"},
                     {"target": "web", "pick": "default", "now": True}):
            fake = _FakeBackend(outlook="now")
            a, b = self._local(fake)
            km._moving.add(SID)
            try:
                with a, b:
                    code, resp = self._post(body)
            finally:
                km._moving.discard(SID)
            self.assertEqual(code, 409, (body, resp))
            self.assertIs(resp["ok"], False)
            self.assertIn("moving", resp["error"], body)
            self.assertEqual(fake.calls, [], (body, "nothing reaches the backend mid-move"))
        # the plain road still parks behind the move, as before, and names it
        fake = _FakeBackend(outlook="now")
        a, b = self._local(fake, _gate_or_park=lambda sid, op: True)
        km._moving.add(SID)
        try:
            with a, b:
                code, resp = self._post({"target": "web", "pick": "login"})
        finally:
            km._moving.discard(SID)
        self.assertEqual((code, resp["parked"]), (200, "move"))

    def _parked(self, *ops):
        """SID's FIFO seeded through the kernel's own park (the mirror written, the wake made), cleaned after the test."""
        km._pending_ops.pop(SID, None)
        km._inflight_ops.pop(SID, None)
        for op in ops:
            km._park_op(SID, op)
        self.addCleanup(lambda: (km._pending_ops.pop(SID, None), km._inflight_ops.pop(SID, None), km._save_pending_ops()))

    def test_now_and_default_drop_the_sids_parked_auth_picks(self):
        # round 2 of the review (route-1, the high): the `now` and `default` roads bypass the FIFO, and a pick parked seconds
        # earlier (the dashboard's mid-turn, or `romp billing web login` without --now, whose parked line invites the --now
        # re-run) fired at the drain's next quiet cycle OVER the pick just applied: the session ended on the OLDER pick
        # although the verb answered that it bills the newer one from now, and a parked ("auth", "key") after `default` gave
        # the session a pick again. Dropped now, counted in the answer; a parked send keeps its place
        import io
        from contextlib import redirect_stderr
        fake = _FakeBackend(outlook="now")
        self._parked(("send", "a message parked ahead", "", "q1"), ("auth", "login"))
        a, b = self._local(fake)
        err = io.StringIO()
        with a, b, redirect_stderr(err):
            code, resp = self._post({"target": "web", "pick": "login:" + LID, "now": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp["superseded"], 1, "the earlier queued pick was dropped, and the answer says so")
        self.assertEqual([op[0] for op in km._pending_ops.get(SID) or []], ["send"], "only auth ops go; the send keeps its place")
        self.assertIn("parked-op cancel: %s auth (1 superseded by the --now pick)" % SID, err.getvalue())
        self.assertEqual(fake.calls, [("set_auth", SID, "login:" + LID, True)], "the --now pick alone reaches the backend")
        # the default road, with and without --now (it never parks in either form)
        for body in ({"target": "web", "pick": "default"}, {"target": "web", "pick": "default", "now": True}):
            fake = _FakeBackend(outlook="now")
            self._parked(("auth", "key"), ("auth", "login"))
            a, b = self._local(fake)
            with a, b:
                code, resp = self._post(body)
            self.assertEqual(code, 200, (body, resp))
            self.assertEqual(resp["superseded"], 2, body)
            self.assertNotIn(SID, km._pending_ops, "an emptied queue leaves no entry (and no drain hold) behind")
            self.assertNotIn(SID, km._drain_hold)
            self.assertEqual(fake.calls, [("follow_default_auth", SID)], (body, "nothing re-picks the session after the clear"))
        # the plain road parks behind the queue and drops nothing: two auth ops fire in press order, the last wins
        fake = _FakeBackend(outlook="now")
        self._parked(("auth", "key"))
        a, b = self._local(fake, _gate_or_park=km._gate_or_park)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login"})
        self.assertEqual((code, resp["queued"], resp["superseded"]), (200, True, 0), resp)
        self.assertEqual([op for op in km._pending_ops[SID]], [("auth", "key"), ("auth", "login")])

    def test_the_op_the_drain_is_handing_over_is_not_dropped(self):
        # the op at _inflight_slot is with the backend this instant and cannot be unsaid: it stays (the ✕ path's rule), and
        # the race left is the drain's call landing after the --now pick, which the answer's count does not claim
        fake = _FakeBackend(outlook="now")
        self._parked(("auth", "key"), ("auth", "login"))
        km._inflight_ops[SID] = km._pending_ops[SID][0]
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login:" + LID, "now": True})
        self.assertEqual((code, resp["superseded"]), (200, 1), resp)
        self.assertEqual(km._pending_ops[SID], [("auth", "key")], "the in-flight head stays; the parked one behind it went")

    def test_a_refused_now_pick_leaves_the_parked_pick_in_the_queue(self):
        # the refusal comes FIRST (round 2 of the review): a --now pick this box cannot bill (a stored login gone) must not
        # also discard the user's valid earlier queued pick
        fake = _FakeBackend(why="that login's record is missing")
        self._parked(("auth", "login"))
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login:" + LID, "now": True})
        self.assertEqual(code, 409, resp)
        self.assertEqual(resp["error"], "that login's record is missing")
        self.assertEqual(km._pending_ops[SID], [("auth", "login")], "the queue is untouched by a refused --now pick")
        self.assertEqual(fake.calls, [], "refused before set_auth: the backend's own reason, asked once")

    def test_a_pending_left_to_the_landing_is_answered_as_such_and_never_cut(self):
        # round 2 of the review: a pending written on a session no landing of this kernel has stamped, with no request
        # standing (the never-landed rule), answered "now", and the verb printed "the session is reconnecting to apply it"
        # while nothing was asked to reconnect; the word names the landing, and --now cuts nothing for it
        for pick in ("login", "default"):
            fake = _FakeBackend(busy=True, inflight=True, outlook="landing")
            a, b = self._local(fake)
            with a, b:
                code, resp = self._post({"target": "web", "pick": pick, "now": True})
            self.assertEqual(code, 200, (pick, resp))
            self.assertEqual((resp["reconnect"], resp["cut"], resp["queued"]), ("when its connect lands", False, False), pick)
            self.assertEqual([c[0] for c in fake.calls], ["set_auth" if pick == "login" else "follow_default_auth"],
                             "no interrupt: nothing is armed for a cut turn's settle to fire")

    def test_a_pending_left_to_the_clis_first_report_is_answered_as_such_and_never_cut(self):
        # the rebase follow-up (2026-09-18): the reviewer's cannot-tell class lands an attach that stamps no side, so the
        # pending parks for the CLI's first init, not for a landing that has passed; the word names the report, and --now
        # cuts nothing for it (nothing is armed for a cut turn's settle to fire)
        fake = _FakeBackend(busy=True, inflight=True, outlook="report")
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login", "now": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual((resp["reconnect"], resp["cut"], resp["queued"]), ("when its CLI first reports its billing", False, False))
        self.assertEqual([c[0] for c in fake.calls], ["set_auth"])

    def test_now_on_a_bounded_default_answers_the_stagger_after_the_cut(self):
        # the rebase follow-up (2026-09-18): `default` takes the follower walk's step, which flags its relaunch for the spawn
        # stagger, and since the reviewer's round 1 the arm waits for that slot with the CLI still serving; after the cut
        # the route answered "now" for a reconnect that fires at its turn. The backend's stagger read decides the word
        fake = _FakeBackend(busy=True, inflight=True, outlook="deferred", staggered=True)
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "default", "now": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual((resp["reconnect"], resp["cut"]), ("at its turn in the spawn stagger", True))
        self.assertEqual([c[0] for c in fake.calls], ["follow_default_auth", "interrupt"])
        fake = _FakeBackend(busy=True, inflight=True, outlook="deferred", staggered=False)
        a, b = self._local(fake)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "key", "now": True})
        self.assertEqual((resp["reconnect"], resp["cut"]), ("now", True), "a plain pick draws no slot: the cut turn's settle arms at once")

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
            code, resp = self._post({"target": "web", "pick": "login:" + LID})
        self.assertEqual(code, 409, resp)
        self.assertEqual(seen[-1], ("login", LID))
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
                                "cut": False, "queued": False, "default": "key", "superseded": 0},
                         "the default it follows now, for the caller's line")

    def test_default_with_now_cuts_the_turn_after_the_clear(self):
        fake = _FakeBackend(busy=True, inflight=True, outlook="deferred")
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
        self.assertEqual((resp["reconnect"], resp["queued"], resp["cut"]), ("at the end of the open turn", False, False))


class AllFollowing(_RouteServer):
    """POST /billing {pick, allFollowing}: the walk over this kernel's live followers."""

    def test_the_walk_answers_the_names_moved_and_skipped(self):
        fake = _FakeBackend()
        with mock.patch.object(km, "_sdk", lambda: fake):
            code, resp = self._post({"pick": "key", "allFollowing": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp, {"ok": True, "pick": "key", "moved": 2, "skipped": 1, "unwritten": 0, "failed": 0,
                                "sessions": ["web", "tests"], "skippedSessions": ["api"], "unwrittenSessions": [], "failedSessions": [],
                                "outlooks": {"web": "now", "tests": "none needed"}, "superseded": 0},
                         "each moved session's outlook rides the answer in the reconnect words (round 2 of the review)")
        self.assertEqual(fake.calls, [("set_auth_followers", "key")])

    def test_a_follower_whose_step_failed_is_answered_apart(self):
        # the rebase follow-up (2026-09-18): the walk survives one follower's fault (the reviewer's per-session rule) and
        # names it apart from the moved, the skipped and the unwritten, so the verb can say it was left following the default
        fake = _FakeBackend(failed=["notes"])
        with mock.patch.object(km, "_sdk", lambda: fake):
            code, resp = self._post({"pick": "key", "allFollowing": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual((resp["failed"], resp["failedSessions"], resp["sessions"]), (1, ["notes"], ["web", "tests"]))

    def test_a_follower_whose_record_would_not_read_is_answered_apart_from_the_skipped(self):
        # round 1 of the review (findings 8 and 12): the walk filed an unreadable record under skipped, and the verb told
        # the user that session "has its own pick" while nothing was written and it has none
        fake = _FakeBackend(unwritten=["docs"])
        with mock.patch.object(km, "_sdk", lambda: fake):
            code, resp = self._post({"pick": "key", "allFollowing": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual((resp["unwritten"], resp["unwrittenSessions"], resp["skippedSessions"]), (1, ["docs"], ["api"]))

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

    def test_the_walk_drops_each_moved_sessions_parked_auth_picks(self):
        # round 2 of the review (route-1's third part): a follower with a dashboard pick parked mid-turn reads as a follower
        # (its auth still ""), takes the walk's pick, and the parked op fired over it at the next quiet cycle; the kernel
        # drops the parked auth picks of every sid the walk moved, and the answer counts them
        fake = _FakeBackend()
        km._pending_ops.pop(SID, None)
        km._pending_ops.pop(FAR_SID, None)
        km._park_op(SID, ("auth", "login"))
        km._park_op(FAR_SID, ("send", "a parked text", "", "q2"))
        km._park_op(FAR_SID, ("auth", "login"))
        self.addCleanup(lambda: (km._pending_ops.pop(SID, None), km._pending_ops.pop(FAR_SID, None), km._save_pending_ops()))
        with mock.patch.object(km, "_sdk", lambda: fake):
            code, resp = self._post({"pick": "key", "allFollowing": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp["superseded"], 2)
        self.assertNotIn(SID, km._pending_ops)
        self.assertEqual([op[0] for op in km._pending_ops[FAR_SID]], ["send"], "the parked send keeps its place")


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
                                "default": {"auth": "key", "login": "", "explicit": False, "label": "", "explicitPick": "",
                                            "explicitWhy": ""}})
        self.assertEqual(fake.calls, [("billing_view", SID)])

    def test_a_stored_login_default_carries_its_label(self):
        fake = _FakeBackend(view=dict(self.VIEW), default="login", explicit=True, default_login=LID,
                            labels={LID: "work"})
        a, b = self._local(fake)
        with a, b:
            code, resp = self._get(SID)
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp["default"], {"auth": "login", "login": LID, "explicit": True, "label": "work",
                                           "explicitPick": "login:" + LID, "explicitWhy": ""})

    def test_the_machine_login_default_carries_the_machines_label(self):
        fake = _FakeBackend(view=dict(self.VIEW), default="login", explicit=True)
        a, b = self._local(fake)
        with a, b:
            code, resp = self._get(SID)
        self.assertEqual(resp["default"], {"auth": "login", "login": "", "explicit": True, "label": MACHINE_LABEL,
                                           "explicitPick": "login", "explicitWhy": ""})

    def test_the_default_is_what_a_follower_bills_not_the_pickers_preselection(self):
        # a remembered per-session pick seeds the picker's preselected choice (_auth_avail's `default`) while no explicit
        # default is set; a follower does not bill it, so the read must not say it does
        fake = _FakeBackend(view=dict(self.VIEW), default="key", explicit=False)
        with mock.patch.multiple(km, **{"_gate_or_park": lambda sid, op: False, "_claude_account_label": lambda: MACHINE_LABEL,
                                        "_auth_avail_status": lambda: {"default": "login", "defaultExplicit": False}}), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)):
            code, resp = self._get(SID)
        self.assertEqual(resp["default"], {"auth": "key", "login": "", "explicit": False, "label": "", "explicitPick": "",
                                           "explicitWhy": ""})

    def test_an_explicit_default_this_box_cannot_bill_is_named_beside_the_side_a_follower_bills(self):
        # round 2 of the review (verb-3): `explicit` is the raw flag and `auth` the billable resolution, which falls to the
        # other side when this box cannot bill the explicit default, so the verb printed "API key (set explicitly)" for a
        # default the user set to login. The raw pick rides beside the resolution with the box's reason
        fake = _FakeBackend(view=dict(self.VIEW), default="key", explicit=True, explicit_pick="login", why=sb._cred.WHY_NO_LOGIN)
        a, b = self._local(fake)
        with a, b:
            code, resp = self._get(SID)
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp["default"], {"auth": "key", "login": "", "explicit": True, "label": "",
                                           "explicitPick": "login", "explicitWhy": sb._cred.WHY_NO_LOGIN})

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

    def test_the_post_is_token_gated_and_reaches_no_backend(self):
        # round 1 of the review (finding 26): only the GET's gate was pinned; a POST arm moved ahead of the handler's
        # preamble would have passed the census
        fake = _FakeBackend()
        a, b = self._local(fake)
        with a, b:
            self.assertEqual(self._post({"target": "web", "pick": "login"}, token=False)[0], 403)
            self.assertEqual(self._post({"target": "web", "pick": "login"}, token="not-the-token")[0], 403)
            self.assertEqual(self._post({"pick": "login", "allFollowing": True}, token=False)[0], 403)
        self.assertEqual(fake.calls, [], "a refused token reaches no backend call")


class RemoteForwarding(_RouteServer):
    """A session an attached host runs: the request forwards over its tunnel and the far answer is the answer
    (the /end precedent, tests/test_kernel_remote_end_interrupt.py)."""

    def _forward(self, method, body, far_reply, target=FAR_SID, far_status=200, far_text=None):
        """`far_reply` None is a dead tunnel; else the far kernel answers `far_status` with the JSON body (or `far_text`
        when the far body is not JSON: an old kernel's catch-all 404)."""
        crossed = []

        def rec(r, p, b, method="POST"):
            crossed.append((r, p, b, method))
            if far_reply is None and far_text is None:
                return (0, None, "")
            return (far_status, far_reply, far_text if far_text is not None else json.dumps(far_reply))

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

    def test_a_far_non_200_rides_back_with_its_status_and_the_host_named(self):
        # round 1 of the review (finding 25): the relay of a far status (_billing_far_answer through _remote_refusal) had no
        # pin; the commit message names the case (an old far kernel's 404)
        code, resp, _ = self._forward("POST", {"target": FAR_SID, "pick": "key"},
                                      {"ok": False, "error": "no live session named far-web"}, far_status=404)
        self.assertEqual(code, 404)
        self.assertEqual(resp, {"ok": False, "error": "no live session named far-web (the kernel on TESTHOST)"})
        # a far text/plain 404 is the far catch-all, a kernel from before these routes: named with the remedy (round 2 of
        # the review; the bare relay "HTTP 404: not found" told the user neither), still 404 with a JSON body so the verb
        # prints the sentence as it prints every kernel refusal
        code, resp, _ = self._forward("POST", {"target": FAR_SID, "pick": "key"}, None, far_status=404, far_text="not found")
        self.assertEqual(code, 404)
        self.assertEqual(resp, {"ok": False, "error": PREDATES_FAR})
        code, resp, _ = self._forward("GET", None, {"ok": False, "error": "no live session named far-web"}, far_status=404)
        self.assertEqual((code, resp), (404, {"ok": False, "error": "no live session named far-web (the kernel on TESTHOST)"}))
        code, resp, _ = self._forward("GET", None, None, far_status=404, far_text="not found")
        self.assertEqual((code, resp), (404, {"ok": False, "error": PREDATES_FAR}))
        # a far JSON 404 with no error field is the same skew shape, not a resolver's refusal
        code, resp, _ = self._forward("GET", None, {"ok": False}, far_status=404)
        self.assertEqual((code, resp), (404, {"ok": False, "error": PREDATES_FAR}))
        # any other far status keeps the verbatim relay
        code, resp, _ = self._forward("POST", {"target": FAR_SID, "pick": "key"}, None, far_status=503, far_text="busy")
        self.assertEqual((code, resp), (503, {"ok": False, "error": "the remote kernel for TESTHOST answered HTTP 503: busy"}))

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
        # a follower whose connect in progress already launches the pick (its arm came first): set_auth's already-applying
        # branch records the pending and asks no reconnect, so no relaunch slot is drawn (round 1 of the review, finding 7:
        # the walk flagged the slot ahead of set_auth and left it standing, and the session's NEXT reconnect, an effort
        # pick days later, waited on a spawn-stagger slot it was never meant to draw)
        mid = self._sess("api2", launched=None)
        self._queue_loop(mid)
        mid._launching = dict(self.be._launch_shape(mid), auth="key", login="")
        out = self.be.set_auth_followers("key")
        self.assertEqual(out, {"moved": ["api2", "docs", "tests", "web"], "skipped": ["api"], "unwritten": [],
                               "movedSids": [mid.sid, docs.sid, tests.sid, web.sid],
                               "failed": [],
                               # each moved session's outlook (round 2 of the review): web's request stands and its bounded
                               # relaunch waits for a spawn slot with the CLI serving (staggered, since the reviewer's round 1
                               # drew the slot at the arm), tests already runs the side (none), docs has no loop (next-launch),
                               # and api2's pending is the connect in progress's to serve, with no request standing (landing)
                               "outlook": {"web": "staggered", "tests": "none", "docs": "next-launch", "api2": "landing"}},
                         "names sorted: the roster's order is not a contract; the sids in the names' order")
        self.assertEqual((self._reg(mid.sid)["auth"], mid._auth_pending, mid._relaunch_bounded), ("key", "key", False),
                         "already applying: the pick and the pending, no request, so no slot")
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

    def test_set_auth_followers_files_a_record_that_would_not_read_apart(self):
        # round 1 of the review (findings 8 and 12): filed under skipped, the log said the session had a pick of its own
        web = self._sess("web", launched="login")
        docs = self._sess("docs", launched="login")
        sb._reg_path(Path(self.d), docs.sid).write_text("{not a record")
        out = self.be.set_auth_followers("key")
        self.assertEqual(out, {"moved": ["web"], "skipped": [], "unwritten": ["docs"], "failed": [], "movedSids": [web.sid],
                               "outlook": {"web": "next-launch"}})
        self.assertIs(docs._relaunch_bounded, False, "nothing written, nothing asked, no slot")
        self.assertTrue(any("1 record would not read (docs)" in m for m in self.logs), self.logs[-2:])
        self.assertFalse(any("skipped with a pick of their own (docs)" in m for m in self.logs), self.logs[-2:])

    def test_set_auth_draws_a_relaunch_slot_only_when_asked_to_and_only_on_a_request(self):
        # the `bounded` keyword (round 1 of the review, finding 7): the flag is set where the request is made, never ahead
        web = self._sess("web", launched="login")
        self._queue_loop(web)
        self.assertTrue(self.be.set_auth(web.sid, "key", chip=False))
        self.assertIs(web._relaunch_bounded, False, "a plain pick draws no slot")
        api = self._sess("api", launched="login")
        self._queue_loop(api)
        self.assertTrue(self.be.set_auth(api.sid, "key", chip=False, bounded=True))
        self.assertIs(api._relaunch_bounded, True, "asked to, and a reconnect was requested")
        tests = self._sess("tests", launched="key")
        self._queue_loop(tests)
        self.assertTrue(self.be.set_auth(tests.sid, "key", chip=False, bounded=True))
        self.assertIs(tests._relaunch_bounded, False, "asked to, but the side it runs: no request, no slot")
        # a plain pick that takes over a follower's STANDING ask spends the walk's flag (round 2 of the review): a stored
        # login picked over the walk's machine-login pending goes through the pending branch (the pairs differ), which
        # only ever SET the flag, so the pick's own relaunch drew a boot slot and could wait the backstop behind boot's
        rec = {"id": sb._logins.mint_id(), "label": "Work", "tokenCmd": "token-read 'romp login Work'",
               "addedAt": int(time.time()) - 86400}
        sb._logins.write_record(self.d, rec)
        docs = self._sess("docs", launched="key")
        docs.auth_live = "key"
        dq = self._queue_loop(docs)
        self.assertTrue(self.be.set_auth_default("login"))
        self.assertEqual((docs._auth_pending, docs._relaunch_bounded, len(dq)), ("login", True, 1), "the walk's ask, flagged")
        self.assertTrue(self.be.set_auth(docs.sid, "login:" + rec["id"], chip=False))
        self.assertEqual((docs.auth, docs.auth_login, docs._auth_pending), ("login", rec["id"], "login"))
        self.assertFalse(any("already applying" in m for m in self.logs[-2:]), self.logs[-2:])
        self.assertIs(docs._relaunch_bounded, False, "a plain pick that takes over a follower's ask spends the walk's flag")

    def _never_landed_follower(self, name, reports, composed):
        """A follower whose reg carries its CLI's report (auth_live restored at construction: the CLI bills `reports`), no
        landing of this kernel stamped (_launched_auth None), a boot re-attach in flight composed from `composed`
        (_launching, _connecting, the host's attach road) and a recording loop: the never-landed shape after a restart."""
        s = self._sess(name)
        self.be._update_reg(s.sid, apiKeyAuth=(reports == "key"))
        s.auth_live = reports
        s._launching = dict(self.be._launch_shape(s), auth=composed, login="")
        s._connecting = True
        s._host_is_attach = True
        return s, self._queue_loop(s)

    def test_set_auth_on_a_never_landed_follower_leaves_the_pick_to_its_landing(self):
        # round 2 of the review (concurrency-2, regression-1): the walk routes every follower through set_auth, whose guards
        # read the launched stamp and never the report, so for a follower whose CLI no landing had stamped (a boot
        # re-attach in flight after a restart) two things went wrong. (a) A pick of the side the survivor already bills
        # took the pending branch and requested a reconnect; the request's arm retired the report, the attach landed with
        # none, stamped the composed side, and relaunched a CLI already on the pick through a boot slot. (b) A pick of the
        # side the attach COMPOSED took the already-applying guard, which asked nothing; the attach then stamped the
        # report (the other side), and the pending stood unserved with no arm coming: a pick the verb reported moved that
        # never applied. Now set_auth writes the pick for the landing to decide (no request, no slot), and the landing
        # that finds the pick unserved with no arm standing makes the request with the stamps truthful
        web, wq = self._never_landed_follower("web", reports="login", composed="key")
        out = self.be.set_auth_followers("login")
        self.assertEqual((out["moved"], out["outlook"]), (["web"], {"web": "landing"}))
        self.assertEqual((web.auth, web._auth_pending, self._reg(web.sid)["auth"], self._reg(web.sid)["authPending"]),
                         ("login", "login", "login", True), "the pick and its pending, for the landing")
        self.assertEqual(len(wq), 0, "no request: the landing decides")
        self.assertIs(web._relaunch_bounded, False, "no slot")
        self.assertEqual((web.auth_live, self._reg(web.sid)["apiKeyAuth"]), ("login", False), "the report stands: it describes the CLI that runs")
        self.assertTrue(any("its landing decides" in m and "set to login" in m for m in self.logs), self.logs[-2:])
        web._connect_landed()
        self.assertEqual((web._launched_auth, web._auth_pending, self._reg(web.sid)["authPending"]), ("login", "", False),
                         "the attach stamped the report; the pick is served, and nothing relaunches a CLI already on it")
        self.assertEqual(len(wq), 0)
        api, aq = self._never_landed_follower("api", reports="login", composed="key")
        out = self.be.set_auth_followers("key")
        self.assertEqual(out["moved"], ["api"], "web carries its own pick now and is skipped")
        self.assertEqual((api.auth, api._auth_pending, len(aq), api._relaunch_bounded), ("key", "key", 0, False),
                         "the composed side is no evidence for an attach: written for the landing, not already applying")
        api._connect_landed()
        self.assertEqual((api._launched_auth, api._auth_pending), ("login", "key"), "the attach stamped the report; the pick stands unserved")
        self.assertEqual(len(aq), 1, "the landing found no arm standing for the pick and made the request")
        self.assertIs(api._relaunch_bounded, True, "the walk's pick: its relaunch draws a slot, from the memo")
        self.assertTrue(any("left to this landing, so it is asked now" in m for m in self.logs), self.logs[-2:])
        # the dashboard's pick through the same shape: the landing's request draws no slot
        docs, dq = self._never_landed_follower("docs", reports="login", composed="key")
        self.assertTrue(self.be.set_auth(docs.sid, "key"))
        self.assertEqual((docs._auth_pending, len(dq)), ("key", 0))
        docs._connect_landed()
        self.assertEqual((len(dq), docs._relaunch_bounded), (1, False))
        # a LAUNCH (hosts off: the report is retired at the handshake, the landing stamps the composed side): a pick of the
        # other side is asked at the landing too, once
        tests, tq = self._never_landed_follower("tests", reports="login", composed="key")
        tests._host_is_attach = False
        self.assertTrue(self.be.set_auth(tests.sid, "login", chip=False))
        self.assertEqual(len(tq), 0)
        tests.auth_live = ""                                   # _stamp_launch_login at the handshake
        tests._connect_landed()
        self.assertEqual((tests._launched_auth, tests._auth_pending, len(tq)), ("key", "login", 1))
        # a pick made during the spawn of the OTHER side on a LANDED session keeps its own request's arm (the base's rule):
        # the landing asks nothing more for it
        notes = self._sess("notes", launched="key")
        nq = self._queue_loop(notes)
        notes._launching = dict(self.be._launch_shape(notes), auth="key", login="")
        notes._connecting = True
        self.assertTrue(self.be.set_auth(notes.sid, "login", chip=False))
        self.assertEqual(len(nq), 1, "a landed session's pick requests as before")
        notes._connect_landed()
        self.assertEqual((notes._launched_auth, notes._auth_pending, len(nq)), ("key", "login", 1), "its own request stands; no second ask")

    def test_follow_default_auth_whose_report_is_retired_in_the_gap_hands_the_session_to_the_unlanded_step(self):
        # round 2 of the review (concurrency-1): follow_default_auth's bare read found a report and dispatched to
        # _follow_default, which re-read the running side and returned silently when it was empty, and between the two
        # reads _stamp_launch_login (the handshake for a kernel child, the hello for a hosted spawn, before the landing
        # stamps) retires the report. The verb then had no step: nothing pending, no request, and the connect in flight,
        # composed from the old pick, landed with nothing to decide, so the session billed the pick's side for the process
        # lifetime while the reg said it followed the default. With `because` set the empty read hands the session to the
        # unlanded step, which judges the connect in flight. The report is the KEY: since round 1 of the reviewer's review
        # (its kernel-4) a launch retires the report only when the side it composed differs from it, and the relaunch in
        # flight here composes the pick, the login (the rebase follow-up, 2026-09-18)
        s = self._sess("web", auth="login")
        self.be._update_reg(s.sid, apiKeyAuth=True)
        s.auth_live = "key"                                # the report restored; no landing stamped
        s._launching = dict(self.be._launch_shape(s))      # the connect in flight, composed from the pick; the default is the key
        queued = self._queue_loop(s)
        real, fired = sb.SdkBackend._follow_default, []

        def stamp_first(be, sess, *a, **kw):
            if not fired:
                fired.append(1)
                be._stamp_launch_login(sess)               # the handshake's stamp lands in the gap: the report is retired
                self.assertEqual((sess.auth_live, sess._launched_auth), ("", None))
            return real(be, sess, *a, **kw)
        with mock.patch.object(sb.SdkBackend, "_follow_default", stamp_first):
            self.assertTrue(self.be.follow_default_auth(s.sid))
        self.assertEqual(fired, [1])
        self.assertEqual((s._auth_pending, len(queued), self._reg(s.sid)["authPending"], s._relaunch_bounded), ("key", 1, True, True),
                         "the unlanded step asked: the connect in flight launches the login, the default is the key")
        self.assertTrue(any("connect in flight launches the login" in m for m in self.logs), self.logs[-3:])
        s._connect_landed()
        self.assertEqual((s._launched_auth, s._auth_pending), ("login", "key"), "the landing stamps the login; the ask to the key stands")

    def test_two_picks_on_one_session_from_two_threads_leave_the_session_and_the_reg_on_one_side(self):
        # round 2 of the review (concurrency-4): several threads call set_auth on one session (a WS handler per dashboard,
        # POST /billing's handler, the drain). Each wrote s.auth bare and mirrored `auth` as ITS literal after the hold, so
        # two picks that straddled at the mirror left s.auth on one side and the reg's auth on the other: the next compose
        # reads s.auth, a restart reads the reg. The pair is written under the hold beside the pending now and mirrored
        # from the live fields, so the last RMW records the in-memory truth whichever thread wrote last. Two threads,
        # parked at their reg write and released in the reverse order of their arrival
        web = self._sess("web", launched="login")
        self._queue_loop(web)
        real = sb.SdkBackend._update_reg
        names = ("pick-key", "pick-login")
        arrived = {n: threading.Event() for n in names}
        gates = {n: threading.Event() for n in names}

        def parked(be, sid, live_fields=None, **kw):
            me = threading.current_thread().name
            if sid == web.sid and me in gates and not arrived[me].is_set():
                arrived[me].set()
                gates[me].wait(10)
            return real(be, sid, live_fields=live_fields, **kw)
        with mock.patch.object(sb.SdkBackend, "_update_reg", parked):
            t1 = threading.Thread(target=self.be.set_auth, args=(web.sid, "key", False), name="pick-key")
            t1.start()
            self.assertTrue(arrived["pick-key"].wait(10), "the first pick reached its reg write")
            t2 = threading.Thread(target=self.be.set_auth, args=(web.sid, "login", False), name="pick-login")
            t2.start()
            self.assertTrue(arrived["pick-login"].wait(10), "the second pick reached its reg write")
            gates["pick-login"].set()
            t2.join(10)
            gates["pick-key"].set()
            t1.join(10)
        self.assertFalse(t1.is_alive() or t2.is_alive())
        reg = self._reg(web.sid)
        self.assertEqual((web.auth, reg["auth"]), ("login", "login"), "the session and the reg name the same side: the last pick's")
        self.assertEqual((web._auth_pending, reg["authPending"]), ("", False), "the second pick reverted the first's pending")

    def test_follow_default_auth_logs_and_pokes_only_with_the_hold_released(self):
        # round 2 of the review (tests-1): the three-roads test below pins the pending under the hold and the reg write with
        # it released, and nothing pinned the rest of round 3's rule for the unlanded step, no log line and no poke under
        # the hold (a planted line inside the hold left the module green). The sink records whether any of the three
        # sessions' hold locks was held at each line and each poke; single-threaded, so the caller is the only holder
        web = self._sess("web", auth="login")
        web._auth_pending = "login"; self.be._update_reg(web.sid, authPending=True)
        web._launching = dict(self.be._launch_shape(web))
        self._queue_loop(web)
        api = self._sess("api", auth="key")
        api._auth_pending = "key"; self.be._update_reg(api.sid, authPending=True)
        api._launching = dict(self.be._launch_shape(api))
        self._queue_loop(api)
        docs = self._sess("docs", auth="login")
        docs._auth_pending = "login"; self.be._update_reg(docs.sid, authPending=True)
        self._queue_loop(docs)
        sessions = (web, api, docs)
        lines, pokes = [], []
        self.be._log_cb = lambda m: lines.append((m, any(s._hold_lock.locked() for s in sessions)))
        self.be._poke_cb = lambda: pokes.append(any(s._hold_lock.locked() for s in sessions))
        for s in sessions:
            self.assertTrue(self.be.follow_default_auth(s.sid))
        self.assertEqual([m for m, under in lines if under], [], "a log line ran under the hold")
        self.assertEqual([p for p in pokes if p], [], "a poke ran under the hold")
        self.assertGreaterEqual(len(lines), 6, "the clear's line and the step's line per road: the pin is live")
        self.assertEqual(len(pokes), 3, "one poke per road")

    def test_auth_apply_outlook_answers_landing_for_a_pending_no_request_stands_for(self):
        # round 2 of the review (concurrency-3, route-3, regression-2): the roads that write a pending for the landing to
        # decide make no request, and the outlook read pending-and-quiet as "now", so the verb printed "the session is
        # reconnecting to apply it" for a reconnect nothing had asked. Keyed on the object (no landing stamped) AND on the
        # absence of an ask, so a request made on such an object still answers "now"
        s = self._sess("api", auth="login")                 # never landed, with a report; the default is the key
        s.auth_live = "login"
        q = self._queue_loop(s)
        self.assertTrue(self.be.follow_default_auth(s.sid))
        self.assertEqual((s._auth_pending, len(q)), ("key", 0))
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "landing")
        s._launching = dict(self.be._launch_shape(s))       # with the connect composed too
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "landing")
        s._pending = ["a queued text"]
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "landing", "before the queue read: nothing is armed for that turn's settle")
        # the retarget road (no report, no connect composed): the first connect decides, nothing asked
        t = self._sess("web", auth="login")
        t._auth_pending = "login"
        tq = self._queue_loop(t)
        self.assertTrue(self.be.follow_default_auth(t.sid))
        self.assertEqual((t._auth_pending, len(tq)), ("key", 0))
        self.assertEqual(self.be.auth_apply_outlook(t.sid), "landing")
        # the counter-pin: a never-landed object WITH a request standing (the unlanded step's ask for a connect in flight
        # composed from the old pick) answers "now": the read is keyed on the ask, not on the object's shape alone
        u = self._sess("tests", auth="login")
        u._launching = dict(self.be._launch_shape(u))
        uq = self._queue_loop(u)
        self.assertTrue(self.be.follow_default_auth(u.sid))
        self.assertEqual(len(uq), 1)
        # the follower step's request is bounded (its relaunch waits for a spawn slot with the CLI serving, the reviewer's
        # round 1), so the word is the stagger's; with no spawn budget it is "now"
        self.assertEqual(self.be.auth_apply_outlook(u.sid), "staggered")
        with mock.patch.object(self.be, "_spawn_sem", None):
            self.assertEqual(self.be.auth_apply_outlook(u.sid), "now")
        # a landed session's pick keeps "now"
        v = self._sess("docs", launched="login")
        self._queue_loop(v)
        self.assertTrue(self.be.set_auth(v.sid, "key", chip=False))
        self.assertEqual(self.be.auth_apply_outlook(v.sid), "now")

    def test_billing_default_names_the_explicit_pick_beside_the_resolution(self):
        # round 2 of the review (verb-3): the route's default took `explicit` from the raw flag and the side from the
        # billable resolution, which falls to the other side when this box cannot bill the explicit default
        sb.write_sdk_default(Path(self.d), auth="login", authLogin="", authExplicit=True)
        self.be.login_ok = lambda: False                    # no login signed in; a helper is configured
        d = km._billing_default(self.be)
        self.assertEqual((d["auth"], d["value"], d["explicit"], d["explicitPick"], d["explicitWhy"]),
                         ("key", "key", True, "login", sb._cred.WHY_NO_LOGIN), "a follower bills the key; login was set")
        self.be.login_ok = lambda: True
        sb.write_sdk_default(Path(self.d), auth="login", authLogin=LID, authExplicit=True)   # a stored login whose record is gone
        with mock.patch.object(km, "_claude_account_label", lambda: MACHINE_LABEL):
            d = km._billing_default(self.be)
        self.assertEqual((d["auth"], d["login"], d["label"], d["explicitPick"]), ("login", "", MACHINE_LABEL, "login:" + LID),
                         "the machine's own login, the same side word; compared as pick values")
        self.assertEqual(d["explicitWhy"], "no stored login with that id")
        sb.write_sdk_default(Path(self.d), auth="key", authLogin="", authExplicit=True)
        d = km._billing_default(self.be)
        self.assertEqual((d["explicitPick"], d["explicitWhy"]), ("key", ""), "agreeing: no reason")
        self.assertEqual(self.be.explicit_default_pick(), "key")

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

    def test_follow_default_auth_during_a_connect_composed_from_the_old_pick_retargets_the_ask(self):
        # round 1 of the review (finding 3): `romp billing web key` on a quiet session arms a reconnect composed with the
        # key; `romp billing web default` a second later, while that connect is in flight (no report, no landed stamp),
        # returned before any request, the landing then found the pick's pending equal to the side it launched and
        # cleared it as served, and the session ran the key for the process lifetime while every reader said it
        # followed the default (the login here). The launching pick is compared to the default's target instead
        s = self._sess("web", auth="login")               # picked onto the login; the default here is the key (helper rule)
        s._auth_pending = "login"
        self.be._update_reg(s.sid, authPending=True)
        s._launching = dict(self.be._launch_shape(s))      # the connect in flight launches the pick
        self.assertEqual(s._launching["auth"], "login")
        queued = self._queue_loop(s)
        self.assertTrue(self.be.follow_default_auth(s.sid))
        reg = self._reg(s.sid)
        self.assertEqual((reg["auth"], s.auth, s._auth_pending, reg["authPending"]), ("", "", "key", True),
                         "the ask is retargeted to the default the connect in flight does not launch")
        self.assertEqual(len(queued), 1, "a reconnect is requested; its arm rides after the connect lands")
        self.assertIs(s._relaunch_bounded, True)
        self.assertTrue(any("connect in flight launches the login" in m and "the key" in m for m in self.logs), self.logs[-2:])
        # the connect in flight already launches what the default resolves to: the pick's pending is stale, cleared
        t = self._sess("api", auth="key")
        t._auth_pending = "key"
        self.be._update_reg(t.sid, authPending=True)
        t._launching = dict(self.be._launch_shape(t))
        self.assertEqual(t._launching["auth"], "key")
        tq = self._queue_loop(t)
        self.assertTrue(self.be.follow_default_auth(t.sid))
        self.assertEqual((t._auth_pending, self._reg(t.sid)["authPending"], len(tq)), ("", False, 0),
                         "the connect lands the default: nothing pending, nothing asked")

    def test_follow_default_auth_on_a_session_that_never_landed_retargets_a_standing_pending_to_the_default(self):
        # round 1 of the review (finding 6): the pick's pending ("login") survived the clear on a session with no running
        # side and no connect composed; the first connect then landed the default ("key"), the landing's follower
        # comparison failed ("login" != "key"), the dots stayed on, and a later re-pick of the login read as "already
        # applying" against that stale pending, so it never applied. Retargeted to what the default resolves to, the
        # landing clears it
        s = self._sess("web", auth="login")
        s._auth_pending = "login"
        self.be._update_reg(s.sid, authPending=True)
        queued = self._queue_loop(s)
        self.assertTrue(self.be.follow_default_auth(s.sid))
        self.assertEqual((s.auth, s._auth_pending, self._reg(s.sid)["authPending"]), ("", "key", True),
                         "the pending now names the default; the reg keeps the dots until the landing")
        self.assertEqual(len(queued), 0, "no request: the first connect composes from the default (_decide_auth)")
        s._launching = dict(self.be._launch_shape(s))       # the connect lands the default
        s._connect_landed()
        self.assertEqual((s._auth_pending, self._reg(s.sid)["authPending"]), ("", False), "served by the landing")
        # a later pick of the login is a real change again, not "already applying"
        self.assertTrue(self.be.set_auth(s.sid, "login", chip=False))
        self.assertEqual((s.auth, s._auth_pending), ("login", "login"))
        self.assertEqual(len(queued), 1, "…and its reconnect is requested")

    def test_follow_default_auth_on_a_dormant_session_clears_the_reg(self):
        self.n += 1
        sid = "11111111-2222-3333-4444-%012d" % self.n
        sb.write_reg(Path(self.d), sid, {"sid": sid, "name": "docs", "cwd": self.d, "alive": True, "auth": "login",
                                          "authLogin": "", "authPending": True})
        self.assertTrue(self.be.follow_default_auth(sid))
        reg = self._reg(sid)
        self.assertEqual((reg["auth"], reg["authLogin"], reg["authPending"]), ("", "", False),
                         "no report of the side its CLI ran: nothing says it runs the other side, so no ask")
        # a dormant session that already follows the default, with an ask but no report: the ask is derived from the
        # report alone (round 1 of the review, finding 5), and with none there is nothing to ask; the constructor and
        # the landing would have cleared it at the first connect anyway (a launch of the default clears the pending)
        self.n += 1
        fsid = "11111111-2222-3333-4444-%012d" % self.n
        sb.write_reg(Path(self.d), fsid, {"sid": fsid, "name": "tests", "cwd": self.d, "alive": True, "authPending": True})
        self.assertTrue(self.be.follow_default_auth(fsid))
        self.assertEqual((self._reg(fsid).get("auth"), self._reg(fsid)["authPending"]), ("", False))
        self.assertFalse(self.be.follow_default_auth("11111111-2222-3333-4444-999999999999"), "no record: refused")

    def test_follow_default_auth_on_a_dormant_session_derives_the_ask_from_its_report(self):
        # round 1 of the review (finding 5): a session with no object can have a live CLI (stood down under its host, or
        # the kernel mid-boot), and its next "launch" is an ATTACH, which asks a follower to move only while authPending
        # stands. The old branch forced it False for a picked session, so a session picked onto the login and running it
        # kept billing the login after `default` while every reader said it followed the default (the key here)
        self.n += 1
        sid = "11111111-2222-3333-4444-%012d" % self.n
        sb.write_reg(Path(self.d), sid, {"sid": sid, "name": "docs", "cwd": self.d, "alive": True, "auth": "login",
                                          "authLogin": "", "apiKeyAuth": False})
        self.assertTrue(self.be.follow_default_auth(sid))
        reg = self._reg(sid)
        self.assertEqual((reg["auth"], reg["authPending"]), ("", True), "its CLI reported the login; the default is the key: an ask")
        self.assertTrue(any("its CLI last reported the login" in m and "asked to move when it next attaches" in m
                            for m in self.logs), self.logs[-2:])
        s = sb.SdkSession(self.be, dict(reg))
        self.assertEqual(s._auth_pending, "key", "the constructor carries it as a follower's ask")
        # a report of the side the default resolves to: nothing to ask
        self.n += 1
        ksid = "11111111-2222-3333-4444-%012d" % self.n
        sb.write_reg(Path(self.d), ksid, {"sid": ksid, "name": "web", "cwd": self.d, "alive": True, "auth": "login",
                                          "authPending": True, "apiKeyAuth": True})
        self.assertTrue(self.be.follow_default_auth(ksid))
        self.assertIs(self._reg(ksid)["authPending"], False)

    @staticmethod
    def _hold_checked(s):
        """`s` records every write of its pending target with whether its hold lock was held at the write (round 3 of the
        default billing's review, 2026-09-18: every writer takes the hold for the in-memory write alone). A data
        descriptor on a subclass wins over the instance attribute, so the swap intercepts the plain assignment the code
        makes; the value moves to a private slot of the dict. One test's helper, the lock read by the writer's own thread."""
        writes = []

        class _Checked(sb.SdkSession):
            @property
            def _auth_pending(self_):
                return self_.__dict__.get("_auth_pending_v", "")

            @_auth_pending.setter
            def _auth_pending(self_, v):
                writes.append((v, self_._hold_lock.locked()))
                self_.__dict__["_auth_pending_v"] = v
        s.__dict__["_auth_pending_v"] = s.__dict__.pop("_auth_pending", "")
        s.__class__ = _Checked
        return writes

    def test_follow_default_auth_writes_the_pending_under_the_hold_and_mirrors_the_reg_with_it_released(self):
        # round 3 of the default billing's review (2026-09-18) made every writer of a session's pending target take the
        # hold for the in-memory write alone and mirror the reg flag after it from the live value (_mirror_auth_pending):
        # the landing's clear compares the live pending against its snapshot under that lock, so a bare write between its
        # compare and its clear is wiped, and a literal flag lands over the landing's. The verb's step for a session with
        # no running side (_follow_default_unlanded) wrote the pending bare and the flag as a literal on all three of its
        # roads, and its clear left the ask's slot flag standing (the rebase follow-up, 2026-09-18). A recording
        # _update_reg sees the hold released at every reg write and the flag arriving through live_fields, never literal
        real = sb.SdkBackend._update_reg
        reg_writes = []

        def recording(be, sid, live_fields=None, **kw):
            s = be.sessions.get(sid)
            reg_writes.append((s.name if s else sid, s is not None and s._hold_lock.locked(), "authPending" in kw,
                               live_fields is not None))
            return real(be, sid, live_fields=live_fields, **kw)
        web = self._sess("web", auth="login")               # the retarget road: a connect in flight launching the pick
        web._auth_pending = "login"; self.be._update_reg(web.sid, authPending=True)
        web._launching = dict(self.be._launch_shape(web))
        wq = self._queue_loop(web)
        api = self._sess("api", auth="key")                 # the clear road: the connect in flight launches the default
        api._auth_pending = "key"; self.be._update_reg(api.sid, authPending=True)
        api._launching = dict(self.be._launch_shape(api))
        api._relaunch_bounded = True                        # a walk's pick set the slot flag (set_auth's bounded)
        aq = self._queue_loop(api)
        docs = self._sess("docs", auth="login")             # the no-connect road: a standing pending retargeted
        docs._auth_pending = "login"; self.be._update_reg(docs.sid, authPending=True)
        dq = self._queue_loop(docs)
        held = {s.name: self._hold_checked(s) for s in (web, api, docs)}
        with mock.patch.object(sb.SdkBackend, "_update_reg", recording):
            for s in (web, api, docs):
                self.assertTrue(self.be.follow_default_auth(s.sid))
        self.assertEqual((web._auth_pending, api._auth_pending, docs._auth_pending), ("key", "", "key"))
        self.assertEqual((self._reg(web.sid)["authPending"], self._reg(api.sid)["authPending"], self._reg(docs.sid)["authPending"]),
                         (True, False, True), "the reg flag mirrors the live pending on every road")
        self.assertEqual((len(wq), len(aq), len(dq)), (1, 0, 0), "one request, on the retarget road")
        for name, writes in held.items():
            self.assertTrue(writes, "%s: no pending written" % name)
            self.assertEqual([v for v, under in writes if not under], [],
                             "%s: a pending written with the hold released: %r" % (name, writes))
        flagged = [w for w in reg_writes if w[0] in held]
        self.assertEqual([w for w in flagged if w[1]], [], "a reg write ran under the hold lock: %r" % (flagged,))
        self.assertEqual([w for w in flagged if w[2]], [], "a literal authPending: %r" % (flagged,))
        for name in held:
            self.assertTrue(any(w[3] for w in flagged if w[0] == name), "%s: the flag was not mirrored: %r" % (name, flagged))
        self.assertIs(api._relaunch_bounded, False, "the slot flag goes with the ask the clear withdrew")

    def test_follow_default_auth_whose_connect_lands_in_the_gap_runs_the_step_from_a_fresh_read(self):
        # round 3's rule for a step that reads the connect window and then writes: the write goes under the hold against a
        # re-read of the stamp, and a stamp found means the landing ran between the read and the write, so the step runs
        # once more from a fresh read. The verb's dispatch read the stamp bare and the unlanded step read _launching bare
        # after it, so a landing in between (the pick's connect lands, served, its pending cleared) left the step on the
        # no-connect road with nothing pending: no ask, and the session ran the pick's side while every reader said it
        # followed the default (the rebase follow-up, 2026-09-18). The landing is driven from the step's file read
        # (_launch_shape), which sits in that gap
        s = self._sess("web", auth="login")                # picked onto the login; the default here is the key
        s._auth_pending = "login"; self.be._update_reg(s.sid, authPending=True)
        s._launching = dict(self.be._launch_shape(s))      # the pick's connect in flight, composed with the login
        queued = self._queue_loop(s)
        real, fired = sb.SdkBackend._launch_shape, []

        def landing_in_the_gap(be, sess, *a, **kw):
            if not fired:
                fired.append(1)
                sess._connect_landed()                     # the pick's connect lands: stamped login, its pending served
                self.assertEqual((sess._launched_auth, sess._launching, sess._auth_pending), ("login", None, ""))
            return real(be, sess, *a, **kw)
        with mock.patch.object(sb.SdkBackend, "_launch_shape", landing_in_the_gap):
            self.assertTrue(self.be.follow_default_auth(s.sid))
        self.assertEqual(fired, [1])
        self.assertEqual((s.auth, s._auth_pending, self._reg(s.sid)["authPending"]), ("", "key", True),
                         "run again from a fresh read: the landed process runs the login and the default is the key, so it asks")
        self.assertEqual(len(queued), 1, "the reconnect is requested")
        self.assertTrue(any("follows the machine default again" in m and "runs on the login" in m for m in self.logs),
                        self.logs[-3:])

    def test_follow_default_auth_leaves_a_session_whose_report_arrives_in_the_gap_to_its_landing(self):
        # round 3's never-landed rule: an object no landing of this kernel has stamped (_launched_auth None) with a report
        # (auth_live) is left to its landing, with no request and no slot, because a request's arm clears the report and
        # the landing then stamps the composed side over what the CLI bills. The verb's dispatch read the report bare and
        # sent a session without one down the unlanded step, which requests a reconnect for a connect in flight composed
        # from the old pick; a report arriving between that read and the write (the CLI's init frame) made that request
        # the one the rule forbids (the rebase follow-up, 2026-09-18)
        s = self._sess("web", auth="login")
        s._auth_pending = "login"; self.be._update_reg(s.sid, authPending=True)
        s._launching = dict(self.be._launch_shape(s))
        queued = self._queue_loop(s)
        real, fired = sb.SdkBackend._launch_shape, []

        def report_in_the_gap(be, sess, *a, **kw):
            if not fired:
                fired.append(1)
                sess.auth_live = "login"                   # the CLI's init frame: it bills the login; nothing has stamped it
            return real(be, sess, *a, **kw)
        with mock.patch.object(sb.SdkBackend, "_launch_shape", report_in_the_gap):
            self.assertTrue(self.be.follow_default_auth(s.sid))
        self.assertEqual((s._auth_pending, self._reg(s.sid)["authPending"]), ("key", True), "the ask stands for the landing to decide")
        self.assertEqual(len(queued), 0, "no request: the landing decides for an object that never landed")
        self.assertIs(s._relaunch_bounded, False, "and no slot")
        self.assertTrue(any("follows the machine default again" in m and "its landing decides" in m for m in self.logs),
                        self.logs[-3:])

    def test_follow_default_auth_keeps_its_words_when_the_step_reruns_after_a_landing(self):
        # the step's re-run from a fresh read (round 3) is a recursive call; the verb's head (`because`) rides it (the
        # rebase's resolution of the two sides, 2026-09-18), so the re-run's line still says the session follows the
        # default again, not that the machine default changed. Green on the rebased tree: a pin of the resolution
        s = self._sess("api", auth="login")                # never landed, with a report: the never-landed branch
        s.auth_live = "login"
        queued = self._queue_loop(s)
        real, fired = sb.SdkBackend._launch_shape, []

        def stamp_in_the_gap(be, sess, *a, **kw):
            if not fired:
                fired.append(1)
                sess._launched_auth = "login"              # the landing stamps between the window's read and the hold's write
            return real(be, sess, *a, **kw)
        with mock.patch.object(sb.SdkBackend, "_launch_shape", stamp_in_the_gap):
            self.assertTrue(self.be.follow_default_auth(s.sid))
        self.assertEqual((s._auth_pending, len(queued)), ("key", 1))
        heads = [m for m in self.logs if "follows the machine default again: automatic (the key on this box); this session "
                 "follows the default but runs on the login" in m]
        self.assertEqual(len(heads), 1, self.logs[-3:])
        self.assertFalse(any("the machine default is now" in m for m in self.logs), "the re-run kept the verb's head")

    def test_default_label_names_the_billable_resolution(self):
        # round 1 of the review (finding 9): the label read the raw explicit default, so a stored-login default whose record
        # had gone was named in the log while the relaunch composed the machine's own login (the fall fallback_auth takes)
        self.assertEqual(self.be._default_label(), "automatic", "no explicit default")
        sb.write_sdk_default(Path(self.d), auth="login", authLogin=LID, authExplicit=True)
        self.assertEqual(self.be.fallback_auth(), "login", "the stored login's record is missing: the machine's own login")
        self.assertEqual(self.be._default_label(), "login")
        s = self._sess("api", auth="key", launched="key")
        s.auth_live = "key"
        self._queue_loop(s)
        self.assertTrue(self.be.follow_default_auth(s.sid))
        self.assertTrue(any("follows the machine default again: login;" in m for m in self.logs), self.logs[-2:])
        self.assertFalse(any("record missing" in m for m in self.logs), "the label never names an account the session will not bill")

    def test_auth_apply_outlook_names_the_schedule(self):
        self.assertEqual(self.be.auth_apply_outlook("11111111-2222-3333-4444-999999999999"), "next-launch")
        s = self._sess("web", launched="login")
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "none", "nothing pending")
        self.be.set_auth(s.sid, "key", chip=False)
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "next-launch", "pending, and no process to reconnect")
        s.loop = object()                    # a live session: the loop's presence is what request_reconnect reads
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "now")
        # a text waiting with no turn open is busy, but not a turn --now can cut (round 1 of the review, finding 1)
        s._pending = ["a queued text"]
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "queued")
        self.assertIs(self.be.turn_open(s.sid), False)
        s._pending = []
        s._untaken = {"text": "fed, not yet taken"}
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "queued")
        s._untaken = None
        s.inflight = 1
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "deferred")
        self.assertIs(self.be.turn_open(s.sid), True)
        self.assertIsNone(self.be.turn_open("11111111-2222-3333-4444-999999999999"), "not ours")
        with s._hold_write():
            s._reconnect_surfaces.add("auth")
            s._reconnect_held_for_work = True
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "held")

    def test_billing_view_reads_a_live_session_and_a_dormant_reg(self):
        s = self._sess("web", auth="login", launched="key")
        s.auth_live = "key"
        s._auth_pending = "login"
        s.client = object()                  # a client is up: the stamp describes a running process
        self.assertEqual(self.be.billing_view(s.sid), {
            "launched": "key", "launchedLogin": "", "launchedLabel": "", "live": "key", "cannotTell": False,
            "pick": {"auth": "login", "login": "", "label": "", "explicit": True}, "pending": True, "held": False})
        self.n += 1
        sid = "11111111-2222-3333-4444-%012d" % self.n
        sb.write_reg(Path(self.d), sid, {"sid": sid, "name": "docs", "cwd": self.d, "alive": True, "apiKeyAuth": False})
        self.assertEqual(self.be.billing_view(sid), {
            "launched": None, "launchedLogin": "", "launchedLabel": "", "live": "login", "cannotTell": False,
            "pick": {"auth": "key", "login": "", "label": "", "explicit": False}, "pending": False, "held": False},
            "a dormant follower: no process, the last init's side, the default it follows (the helper rule: the key)")
        self.assertIsNone(self.be.billing_view("11111111-2222-3333-4444-999999999999"))

    def test_billing_view_reports_no_launched_side_while_no_process_runs(self):
        # round 1 of the review (finding 10): the launched stamp is written at the landing and reset nowhere, so between a
        # reconnect's teardown and its landing, or after a crash, the read said "launched: login" for a process that no
        # longer existed. No client, or a connect composed and not landed, reads as no process
        s = self._sess("web", launched="login")
        self.assertIsNone(self.be.billing_view(s.sid)["launched"], "no client: no process runs")
        s.client = object()
        self.assertEqual(self.be.billing_view(s.sid)["launched"], "login")
        s._connecting = True
        self.assertIsNone(self.be.billing_view(s.sid)["launched"], "a connect composed and not landed: the old process is gone")

    # ---- the rebase onto round 1 of the reviewer's review of the auth-default fix (2026-09-18): the verb follows its
    # invariants (the pending's login beside it, the slot flag in the pending's hold, the cannot-tell class, the walk's
    # per-session try, the stagger in the words). Each test was red on the rebased tree before the follow-up

    STAGGER = ', staggered: the relaunch waits for a spawn slot and the CLI serves until its turn'

    @staticmethod
    def _flag_checked(s):
        """`s` records every write of its relaunch slot flag with whether its hold lock was held at the write (the reviewer's
        regression-3: the ask's flag is written in the pending's hold). The _hold_checked idiom, for the flag."""
        writes = []

        class _Flagged(sb.SdkSession):
            @property
            def _relaunch_bounded(self_):
                return self_.__dict__.get("_relaunch_bounded_v", False)

            @_relaunch_bounded.setter
            def _relaunch_bounded(self_, v):
                writes.append((v, self_._hold_lock.locked()))
                self_.__dict__["_relaunch_bounded_v"] = v
        s.__dict__["_relaunch_bounded_v"] = s.__dict__.pop("_relaunch_bounded", False)
        s.__class__ = _Flagged
        return writes

    def _stored_login(self, label="Work"):
        rec = {"id": sb._logins.mint_id(), "label": label, "tokenCmd": "token-read 'romp login %s'" % label,
               "addedAt": int(time.time()) - 86400}
        sb._logins.write_record(self.d, rec)
        return rec

    def _leased_unreported_follower(self, name, composed, auth=""):
        """The reviewer's cannot-tell class as set_auth meets it: no report on record (the previous kernel relaunched the CLI
        onto a new side and it never turned since, so no init has streamed), no landing of this kernel stamped, a LIVE
        host lease holding its CLI (the backend's lease read answers True for it), a boot re-attach in flight composed
        from `composed`, and a recording loop."""
        s = self._sess(name, auth=auth)
        s._launching = dict(self.be._launch_shape(s), auth=composed, login="")
        s._connecting = True
        s._host_is_attach = True
        leased = self.__dict__.setdefault("_leased", set())
        leased.add(s.sid)
        self.be._host_lease_live = lambda sess: sess.sid in leased
        return s, self._queue_loop(s)

    def test_set_auth_never_landed_branch_writes_the_pendings_login_beside_it(self):
        # the pending carries the stored login it targets (the reviewer's regression-2 and correctness-3): set_auth's
        # never-landed branch wrote the side word alone, so a stored-login pick parked for the landing read as the
        # machine's own login to every pair compare (the landing's served clear, the outlook's, a later pick's guard)
        rec = self._stored_login()
        web, wq = self._never_landed_follower("web", reports="key", composed="key")
        self.assertTrue(self.be.set_auth(web.sid, "login:" + rec["id"], chip=False))
        self.assertEqual(web._auth_pending_target(), ("login", rec["id"]), "the pair, not the side word alone")
        self.assertEqual((web.auth, web.auth_login, len(wq)), ("login", rec["id"], 0))
        web._connect_landed()                                    # the attach stamps the report (the key): the pick stands unserved
        self.assertEqual((web._launched_auth, web._auth_pending_target(), len(wq)), ("key", ("login", rec["id"]), 1))

    def test_set_auth_writes_the_walks_slot_flag_in_the_pendings_hold(self):
        # the reviewer's regression-3: the ask's slot flag is written in the same hold as the pending it belongs to, so the
        # landing's guarded clear cannot run between the two writes and leave the flag standing with no ask behind it.
        # set_auth's request branch wrote the walk's flag bare, after the hold and the mirror
        web = self._sess("web", launched="login")
        self._queue_loop(web)
        writes = self._flag_checked(web)
        self.assertTrue(self.be.set_auth(web.sid, "key", chip=False, bounded=True))
        self.assertEqual(writes, [(True, True)], "one write of the flag, under the hold")
        api = self._sess("api", launched="login")
        self._queue_loop(api)
        writes = self._flag_checked(api)
        self.assertTrue(self.be.set_auth(api.sid, "key", chip=False))
        self.assertEqual(writes, [(False, True)], "a plain pick writes the flag off, in the same hold")

    def test_follow_default_unlanded_writes_the_pair_and_the_slot_flag_in_the_asks_hold(self):
        # the verb's unlanded step wrote the pending's side word alone on both of its writing roads and the slot flag bare
        # after the hold (its own comment said so), and its clear left the pending's login standing
        rec = self._stored_login()
        self.assertTrue(self.be.set_auth_default("login:" + rec["id"]))
        web = self._sess("web", auth="key")                      # the connect in flight, composed from the old pick
        web._launching = dict(self.be._launch_shape(web))
        wq = self._queue_loop(web)
        writes = self._flag_checked(web)
        self.assertTrue(self.be.follow_default_auth(web.sid))
        self.assertEqual((web._auth_pending_target(), len(wq)), (("login", rec["id"]), 1), "the ask names the stored login")
        self.assertEqual(writes, [(True, True)], "the flag, once, under the hold")
        docs = self._sess("docs", auth="key")                    # no connect composed: the standing pending is retargeted
        docs._auth_pending = "key"
        self._queue_loop(docs)
        self.assertTrue(self.be.follow_default_auth(docs.sid))
        self.assertEqual(docs._auth_pending_target(), ("login", rec["id"]))
        api = self._sess("api", auth="login")                    # the connect in flight already launches the default: cleared
        api.auth_login = rec["id"]
        api._auth_pending, api._auth_pending_login = "login", rec["id"]
        api._launching = dict(self.be._launch_shape(api), auth="login", login=rec["id"])
        aq = self._queue_loop(api)
        self.assertTrue(self.be.follow_default_auth(api.sid))
        self.assertEqual((api._auth_pending, api._auth_pending_login, len(aq)), ("", "", 0), "the pair clears together")

    def test_set_auth_on_a_leased_follower_with_no_report_parks_the_pick_for_the_clis_first_init(self):
        # the reviewer's correctness-1, carried into the pick: the never-landed class was keyed on a REPORT, so a follower
        # whose surviving CLI had streamed no init (a live host lease, no report) went through set_auth's ordinary guards.
        # A pick of the side the re-attach composed took the already-applying guard; the cannot-tell attach then stamped
        # None and the picked block cleared the pick as served, so a survivor billing the other side kept the pick on
        # paper and never moved. A pick of the other side made a request whose arm tore down a CLI that may have billed
        # the pick already. Now the pick parks (no request, no slot), the attach leaves it, and the CLI's first init
        # decides it: served when the report is the pick, asked (with the walk's slot memo) when it is not
        web, wq = self._leased_unreported_follower("web", composed="key")
        out = self.be.set_auth_followers("login")
        self.assertEqual((out["moved"], out["outlook"]), (["web"], {"web": "landing"}))
        self.assertEqual((web.auth, web._auth_pending_target(), len(wq), web._relaunch_bounded, web._landing_ask_bounded),
                         ("login", ("login", ""), 0, False, True), "parked for the landing: the pair, no request, the memo")
        self.assertTrue(any("has not reported which side it bills" in m and "set to login" in m for m in self.logs), self.logs[-2:])
        web._connect_landed()                                    # the attach, no report: cannot-tell
        self.assertIsNone(web._launched_auth)
        self.assertIsNotNone(web._launched_effort, "a landing happened")
        self.assertEqual((web._auth_pending, self._reg(web.sid)["authPending"], len(wq)), ("login", True, 0),
                         "not cleared as served: the landing could not tell, and asked nothing")
        self.assertTrue(any("the CLI's first init decides it" in m for m in self.logs), self.logs[-2:])
        self.assertEqual(self.be.auth_apply_outlook(web.sid), "report")
        del self.logs[:]
        self.be._note_auth_source(web, "ANTHROPIC_API_KEY")   # the CLI's first init: it bills the key, the pick is the login
        self.assertEqual((web._launched_auth, len(wq), web._relaunch_bounded, web._landing_ask_bounded), ("key", 1, True, False),
                         "the report is the stamp; the pick differs, so it is asked now, with the walk's slot")
        line = [m for m in self.logs if "left to this report, so it is asked now" in m]
        self.assertEqual(len(line), 1, self.logs)
        self.assertTrue(line[0].endswith(self.STAGGER), line[0])
        # the served twin, through the dashboard's own pick: the report names the pick, so nothing relaunches
        api, aq = self._leased_unreported_follower("api", composed="login")
        self.assertTrue(self.be.set_auth(api.sid, "key"))
        self.assertEqual((api._auth_pending_target(), len(aq)), (("key", ""), 0))
        api._connect_landed()
        self.assertEqual((api._launched_auth, api._auth_pending), (None, "key"))
        self.be._note_auth_source(api, "ANTHROPIC_API_KEY")
        self.assertEqual((api._launched_auth, api._auth_pending, self._reg(api.sid)["authPending"], len(aq), api._relaunch_bounded),
                         ("key", "", False, 0, False), "served by the report: cleared, mirrored, no request")
        self.assertTrue(any("the pick is served, no reconnect" in m for m in self.logs), self.logs[-2:])
        # a follower with neither a report nor a lease keeps set_auth's ordinary schedule (its first connect is a launch)
        docs = self._sess("docs")
        docs._launching = dict(self.be._launch_shape(docs), auth="login", login="")
        dq = self._queue_loop(docs)
        self.assertTrue(self.be.set_auth(docs.sid, "key", chip=False))
        self.assertEqual(len(dq), 1, "no lease, no report: the request branch, as before")

    def test_follow_default_auth_on_a_leased_follower_with_no_report_parks_the_ask_with_no_request(self):
        # the dispatch keyed on the report and the stamp alone, so a picked session with a live host lease and no report
        # (the reviewer's cannot-tell class) went to the unlanded step, which read the re-attach in flight as a connect
        # composed from the old pick and REQUESTED a reconnect: its arm relaunched a survivor that may already bill the
        # default. The follower step parks the ask as the pair with no request and lets the attach, or the CLI's first
        # init, decide (the default is the key; the pick, and the re-attach's compose, the login)
        s, q = self._leased_unreported_follower("web", composed="login", auth="login")
        self.assertTrue(self.be.follow_default_auth(s.sid))
        self.assertEqual((s.auth, s._auth_pending_target(), len(q), s._relaunch_bounded), ("", ("key", ""), 0, False),
                         "the ask is parked as the pair: no request, no slot")
        self.assertTrue(any("has not reported which side it bills: its first init decides" in m for m in self.logs), self.logs[-2:])
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "landing")
        s._connect_landed()                                      # the cannot-tell attach: the ask stands, nothing asked
        self.assertEqual((s._launched_auth, s._auth_pending, len(q)), (None, "key", 0))
        self.be._note_auth_source(s, "none")                      # the CLI bills the login: the follower step asks
        self.assertEqual((s._launched_auth, s._auth_pending, len(q)), ("login", "key", 1))

    def test_auth_apply_outlook_says_staggered_for_a_bounded_request_on_a_quiet_session(self):
        # since the reviewer's round 1 the bounded relaunch draws its spawn slot at the ARM, with the CLI still serving, and
        # reconnects at the grant; "now" promised the moment the stagger delays. The word follows the flag, the wait in
        # flight and the held slot (the three hand over on the loop thread), and falls back to "now" with no spawn budget
        web = self._sess("web", launched="login")
        self._queue_loop(web)
        self.assertTrue(self.be.set_auth(web.sid, "key", chip=False, bounded=True))
        self.assertEqual(self.be.auth_apply_outlook(web.sid), "staggered")
        self.assertIs(self.be.auth_relaunch_staggered(web.sid), True)
        web._relaunch_bounded = False
        web._slot_wait = True
        self.assertEqual(self.be.auth_apply_outlook(web.sid), "staggered", "the wait in flight")
        web._slot_wait = False
        web._relaunch_slot = lambda: None
        self.assertEqual(self.be.auth_apply_outlook(web.sid), "staggered", "the granted slot, held for the relaunch")
        web._relaunch_slot = None
        self.assertEqual(self.be.auth_apply_outlook(web.sid), "now", "the slot fired: the relaunch is in flight")
        api = self._sess("api", launched="login")
        self._queue_loop(api)
        self.assertTrue(self.be.set_auth(api.sid, "key", chip=False))
        self.assertEqual(self.be.auth_apply_outlook(api.sid), "now", "a plain pick draws no slot")
        self.assertIs(self.be.auth_relaunch_staggered(api.sid), False)
        docs = self._sess("docs", launched="login")
        self._queue_loop(docs)
        self.assertTrue(self.be.set_auth(docs.sid, "key", chip=False, bounded=True))
        with mock.patch.object(self.be, "_spawn_sem", None):
            self.assertEqual(self.be.auth_apply_outlook(docs.sid), "now", "no spawn budget: the arm fires at once")
        docs.inflight = 1
        self.assertEqual(self.be.auth_apply_outlook(docs.sid), "deferred", "a turn in flight outranks the stagger: the settle arms")
        self.assertIs(self.be.auth_relaunch_staggered("11111111-2222-3333-4444-999999999999"), False)

    def test_auth_apply_outlook_says_report_after_a_cannot_tell_attach_landed(self):
        # "landing" named an event that had passed: after an attach that stamped the effort but no side (the reviewer's
        # cannot-tell class) the CLI's first init decides the parked pending, and the word says so
        s = self._sess("web", auth="login")
        s._auth_pending = "login"
        s._launching = dict(self.be._launch_shape(s))
        s._host_is_attach = True
        self._queue_loop(s)
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "landing", "before the landing")
        s._connect_landed()
        self.assertEqual((s._launched_auth, s._auth_pending), (None, "login"))
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "report")

    def test_billing_view_names_a_surviving_cli_attached_with_no_report(self):
        # the read said "no CLI is up under this kernel" for a live object whose landing attached a surviving CLI with no
        # report on record (launched None with a client up): a process runs, and its first init says what it bills
        s = self._sess("web", auth="login")
        s._launching = dict(self.be._launch_shape(s))
        s._host_is_attach = True
        s._connect_landed()
        s.client = object()
        view = self.be.billing_view(s.sid)
        self.assertEqual((view["launched"], view["live"], view["cannotTell"]), (None, "", True))
        s._connecting = True
        self.assertIs(self.be.billing_view(s.sid)["cannotTell"], False, "a connect composed and not landed is not this")
        t = self._sess("api", launched="login")
        t.client = object()
        self.assertIs(self.be.billing_view(t.sid)["cannotTell"], False)

    def test_set_auth_followers_survives_one_followers_fault_and_leaves_it_a_follower(self):
        # the reviewer's regression-4 and kernel-2, the default walk's rule carried into the verb's walk: one follower's reg
        # write refused mid-step raised out of set_auth_followers, so the followers after it were never written, the route
        # read the raise as the whole request failing, and the failed one was left half-picked (auth written in memory,
        # a pending with no arm). The walk goes on, the failed session is a follower again with no ask, and one problem
        # row names it; the answer files it apart
        web, api, tests = self._sess("web", launched="login"), self._sess("api", launched="login"), self._sess("tests", launched="login")
        for s in (web, api, tests):
            self._queue_loop(s)
        real_write = sb.write_reg

        def refused(state_dir, sid, reg):
            if sid == api.sid and reg.get("auth") == "key":
                raise PermissionError(13, "Permission denied", str(sb._reg_path(state_dir, sid)))
            return real_write(state_dir, sid, reg)
        with mock.patch.object(sb, "write_reg", refused):
            out = self.be.set_auth_followers("key")
        self.assertEqual((out["moved"], out["failed"], out["unwritten"], sorted(out["outlook"])), (["tests", "web"], ["api"], [], ["tests", "web"]))
        for s in (web, tests):
            self.assertEqual((s.auth, s._auth_pending, self._reg(s.sid)["auth"]), ("key", "key", "key"), s.name)
        self.assertEqual((api.auth, api.auth_login, api._auth_pending, api._auth_pending_login, api._relaunch_bounded, api._landing_ask_bounded),
                         ("", "", "", "", False, False), "the failed follower is a follower again, with no ask")
        self.assertEqual((self._reg(api.sid).get("auth", ""), self._reg(api.sid).get("authPending", False)), ("", False), "the mirror retried")
        rows = [p["text"] for p in self.be.problems(10) if "step failed" in p["text"]]
        self.assertEqual(len(rows), 1, self.be.problems(10))
        self.assertIn("auth (api): the pick key was asked of this session, but its step failed (PermissionError", rows[0])
        self.assertIn("it keeps following the machine default and stays on the login", rows[0])
        self.assertTrue(any("1 step failed (api), left following the default with no ask standing" in m for m in self.logs), self.logs[-1:])

    def test_the_verbs_ask_lines_end_with_the_stagger_clause(self):
        # the walk's lines end with the stagger clause since the reviewer's round 1 (the relaunch waits for a spawn slot
        # with the CLI still serving); the verb's four ask lines promised the moment the stagger delays
        web = self._sess("web", launched="login")
        self._queue_loop(web)
        self.assertTrue(self.be.set_auth(web.sid, "key", chip=False, bounded=True))
        self.assertTrue(self.logs[-1].startswith("auth (web): set to key; reconnecting to apply") and self.logs[-1].endswith(self.STAGGER), self.logs[-1])
        api = self._sess("api", launched="login")
        self._queue_loop(api)
        self.assertTrue(self.be.set_auth(api.sid, "key", chip=False))
        self.assertEqual(self.logs[-1], "auth (api): set to key; reconnecting to apply", "a plain pick draws no slot: no clause")
        one, two = self._sess("one", launched="key"), self._sess("two", launched="key")   # two followers, the walk's head
        self._queue_loop(one); self._queue_loop(two)
        out = self.be.set_auth_followers("login")
        self.assertEqual(out["outlook"], {"one": "staggered", "two": "staggered"})
        head = [m for m in self.logs if m.startswith("auth: 2 sessions following the default now carry the pick login (one, two)")]
        self.assertEqual(len(head), 1, self.logs[-3:])
        self.assertIn("2 asked to reconnect (one, two), staggered: each relaunch waits for a spawn slot and its CLI serves until its turn", head[0])
        docs = self._sess("docs", auth="login")                  # the unlanded step's ask, for a connect in flight
        docs._launching = dict(self.be._launch_shape(docs))
        self._queue_loop(docs)
        self.assertTrue(self.be.follow_default_auth(docs.sid))
        line = [m for m in self.logs if "connect in flight launches the login" in m]
        self.assertEqual(len(line), 1, self.logs[-2:])
        self.assertTrue(line[0].endswith(self.STAGGER), line[0])
        notes, nq = self._never_landed_follower("notes", reports="login", composed="key")   # the landing's re-ask, from the memo
        self.assertIn("notes", self.be.set_auth_followers("key")["moved"])   # docs, a follower again since its `default`, moves too
        notes._connect_landed()
        line = [m for m in self.logs if "left to this landing, so it is asked now" in m]
        self.assertEqual((len(line), len(nq)), (1, 1), self.logs[-2:])
        self.assertTrue(line[0].endswith(self.STAGGER), line[0])
        tests, tq = self._never_landed_follower("tests", reports="login", composed="key")    # the dashboard's pick: no memo, no clause
        self.assertTrue(self.be.set_auth(tests.sid, "key"))
        tests._connect_landed()
        line = [m for m in self.logs if "auth (tests)" in m and "left to this landing, so it is asked now" in m]
        self.assertEqual(len(line), 1, self.logs[-2:])
        self.assertFalse(line[0].endswith(self.STAGGER), line[0])


class ParkedPickRefusedAtTheDrain(unittest.TestCase):
    """A pick the FIFO parked can be refused when it FIRES (a stored login removed between the park and the settle, a
    record that will not read): round 1 of the review (finding 2) found the drain's auth arm discarding set_auth's
    verdict while the effort and fast arms beside it write the stderr line and the settingRefused frame. The verb had
    answered exit 0 with a promised apply, so a silent drop here is the fail-loudly rule broken twice. Synthetic only."""

    def setUp(self):
        self.frames = []
        km._pending_ops.pop(SID, None)
        km._moving.discard(SID)
        km._inflight_ops.pop(SID, None)
        km._drain_hold.pop(SID, None)
        self.addCleanup(lambda: (km._pending_ops.pop(SID, None), km._save_pending_ops()))

    def _drain(self, fake):
        import io
        from contextlib import redirect_stderr
        km._park_op(SID, ("auth", "login:" + LID))
        err = io.StringIO()
        with mock.patch.multiple(km, **{
                "_compacting_now": lambda sid, **k: False, "_working_now": lambda sid: False,
                "_limit_hold": lambda sid, usage=None: None, "_name_of": lambda sid: "web",
                "_send_to_app": lambda app, m: self.frames.append((app, m))}), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), redirect_stderr(err):
            km._apply_pending_ops()
        self.assertNotIn(SID, km._pending_ops, "popped: a refused pick is never replayed forever")
        return err.getvalue()

    def test_a_parked_pick_the_backend_refuses_at_the_drain_is_said_to_the_chat_and_on_stderr(self):
        fake = _FakeBackend(why="that login's record is missing")
        err = self._drain(fake)
        self.assertEqual(fake.calls, [("set_auth", SID, "login:" + LID, True)], "fired once, at the drain, refused there")
        self.assertEqual(self.frames, [("chat", {"type": "settingRefused", "gesture": "command", "sid": SID, "flag": "auth",
                                                 "text": "that login's record is missing"})],
                         "the chat hears the refusal on the frame the live setEffort and setFast ops answer with")
        self.assertIn("pending ops apply: _FakeBackend refused '/auth login:%s' for %s" % (LID, SID[:8]), err)

    def test_a_record_that_would_not_read_is_named_as_the_reason(self):
        class _Unreadable(_FakeBackend):
            def set_auth(self, sid, value, chip=True):
                self.calls.append(("set_auth", sid, value, chip))
                return False
        fake = _Unreadable()
        self._drain(fake)
        self.assertEqual(len(self.frames), 1)
        self.assertIn("web's record would not read", self.frames[0][1]["text"])

    def test_a_parked_pick_the_backend_takes_says_nothing(self):
        fake = _FakeBackend()
        err = self._drain(fake)
        self.assertEqual([c[0] for c in fake.calls], ["set_auth"])
        self.assertEqual((self.frames, err), ([], ""), "nothing to say: the pick landed")


class VerbWords(unittest.TestCase):
    """What the REAL bin/romp prints from a kernel's answer, against a stub that answers canned bodies on the two /billing
    arms (no kernel, no SDK venv). Round 1 of the review found four of the verb's own lines wrong (findings 12 to 15) and
    the old kernel's 404 read as a bare status (finding 13), none of which the lab pins: the lab's kernel is this change's
    own. Hermetic: a temp HOME, the stub's port, a fixed serve token."""

    @classmethod
    def setUpClass(cls):
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        cls.reply = (200, b"{}", "application/json")
        cls.seen = []

        class _Stub(BaseHTTPRequestHandler):
            def _answer(self, method):
                n = int(self.headers.get("Content-Length") or 0)
                cls.seen.append((method, self.path, self.rfile.read(n) if n else b""))
                st, body, ctype = cls.reply
                self.send_response(st)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                self._answer("GET")

            def do_POST(self):
                self._answer("POST")

            def log_message(self, *a):
                pass
        cls.srv = HTTPServer(("127.0.0.1", 0), _Stub)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.home = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def _romp(self, *args, reply=None):
        import subprocess
        if reply is not None:
            body = reply[1]
            type(self).reply = (reply[0], body if isinstance(body, bytes) else json.dumps(body).encode(),
                                reply[2] if len(reply) > 2 else "application/json")
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": self.home, "ROMP_KERNEL_PORT": str(self.port),
               "ROMP_SERVE_TOKEN": "stub-token", "XDG_STATE_HOME": os.path.join(self.home, "state"),
               "XDG_CONFIG_HOME": os.path.join(self.home, "config"),
               # the verb starts no kernel and no bus; the postal trio rides its environment all the same, so the static
               # census over every bin/romp spawn (tests/test_hermetic_kernel_postal.py) holds and no arm of the script
               # could ever ensure the machine's bus from a test
               "ROMP_POSTAL_PORT": "1", "ROMP_POSTAL_PEERS": "0", "ROMP_POSTAL_CLIENT_ONLY": "1"}
        return subprocess.run(["bash", os.path.join(BIN, "romp"), "billing", *args], env=env, capture_output=True,
                              text=True, timeout=60)

    def test_the_walk_says_it_wrote_the_pick_and_that_they_reconnect_and_names_the_unwritten_apart(self):
        # finding 14: "1 session now bill the login" misconjugated and claimed the sessions already bill it, while the
        # walk only writes the pick and asks a reconnect; finding 12: an unreadable record was called "its own pick"
        out = self._romp("--all-following", "login:abcdef012345",
                         reply=(200, {"ok": True, "pick": "login:abcdef012345", "moved": 1, "skipped": 1, "unwritten": 1,
                                      "sessions": ["web"], "skippedSessions": ["api"], "unwrittenSessions": ["docs"],
                                      "outlooks": {"web": "now"}}))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(),
                         'romp billing: 1 session following the default now carries its own pick, the login "abcdef012345" (web); '
                         'it reconnects at its next quiet moment; 1 skipped (api): it has its own pick; '
                         '1 not written (docs): its record would not read')
        out = self._romp("--all-following", "key",
                         reply=(200, {"ok": True, "pick": "key", "moved": 2, "skipped": 0, "unwritten": 2,
                                      "sessions": ["tests", "web"], "skippedSessions": [], "unwrittenSessions": ["api", "docs"],
                                      "outlooks": {"tests": "at the end of the open turn", "web": "now"}}))
        self.assertEqual(out.stdout.strip(),
                         "romp billing: 2 sessions following the default now carry their own pick, the API key (tests, web); "
                         "they reconnect at their next quiet moment; 0 skipped; "
                         "2 not written (api, docs): their records would not read")
        out = self._romp("--all-following", "key", reply=(200, {"ok": True, "pick": "key", "moved": 0, "skipped": 0,
                                                                 "sessions": [], "skippedSessions": []}))
        self.assertEqual(out.stdout.strip(),
                         "romp billing: no running session follows the machine default, so none moved to the API key; 0 skipped",
                         "an older kernel's answer without the third bucket prints as before")

    def test_the_walks_reconnect_clause_follows_each_sessions_outlook(self):
        # round 2 of the review (verb-1): the head said every moved session reconnects at its next quiet moment, while
        # set_auth's unchanged guard reconnects nothing for a follower already running the side and a session with no loop
        # applies the pick at its next connect; a walk onto the side every follower ran promised switching dots that never
        # came. The kernel's per-session outlook words the clause per bucket, with names when the buckets differ
        reply = {"ok": True, "pick": "key", "moved": 5, "skipped": 0, "unwritten": 0, "skippedSessions": [], "unwrittenSessions": [],
                 "sessions": ["api2", "docs", "notes", "tests", "web"],
                 "outlooks": {"web": "now", "tests": "none needed", "docs": "at its next launch", "api2": "when its connect lands",
                              "notes": "held for live work"}}
        out = self._romp("--all-following", "key", reply=(200, reply))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(),
                         "romp billing: 5 sessions following the default now carry their own pick, the API key (api2, docs, notes, tests, web); "
                         "web reconnects at its next quiet moment; tests already bills it, no reconnect; "
                         "docs applies it at its next launch; "
                         "api2 waits for its connect in progress to land, which decides whether to reconnect; "
                         "notes waits for live work to finish, then reconnects; 0 skipped")
        # every moved session already runs the side: no reconnect promised
        reply.update(sessions=["tests", "web"], moved=2, outlooks={"tests": "none needed", "web": "none needed"})
        out = self._romp("--all-following", "key", reply=(200, reply))
        self.assertEqual(out.stdout.strip(),
                         "romp billing: 2 sessions following the default now carry their own pick, the API key (tests, web); "
                         "they already bill it, no reconnect; 0 skipped")
        # two buckets, plural each
        reply.update(sessions=["api", "docs", "tests", "web"], moved=4,
                     outlooks={"api": "none needed", "docs": "at the next quiet moment", "tests": "none needed", "web": "now"})
        out = self._romp("--all-following", "key", reply=(200, reply))
        self.assertEqual(out.stdout.strip(),
                         "romp billing: 4 sessions following the default now carry their own pick, the API key (api, docs, tests, web); "
                         "docs, web reconnect at their next quiet moment; api, tests already bill it, no reconnect; 0 skipped")
        # an older kernel's answer without outlooks: the write alone, no moment promised
        reply.pop("outlooks")
        out = self._romp("--all-following", "key", reply=(200, reply))
        self.assertEqual(out.stdout.strip(),
                         "romp billing: 4 sessions following the default now carry their own pick, the API key (api, docs, tests, web); 0 skipped")
        # the parked picks the walk dropped (route-1) are said
        reply.update(outlooks={n: "now" for n in reply["sessions"]}, superseded=1)
        out = self._romp("--all-following", "key", reply=(200, reply))
        self.assertEqual(out.stdout.strip(),
                         "romp billing: 4 sessions following the default now carry their own pick, the API key (api, docs, tests, web); "
                         "they reconnect at their next quiet moment; 1 earlier queued pick was dropped; 0 skipped")

    def test_the_walk_says_the_stagger_the_first_report_and_the_failed(self):
        # the rebase follow-up (2026-09-18): an asked relaunch waits for its spawn slot with the CLI still serving (the
        # reviewer's round 1), so "at their next quiet moment" promised the moment the stagger delays; a cannot-tell attach
        # leaves the pending to the CLI's first report; and a follower whose step failed is said apart, left following
        # the default
        reply = {"ok": True, "pick": "key", "moved": 3, "skipped": 0, "unwritten": 0, "failed": 1, "skippedSessions": [],
                 "unwrittenSessions": [], "failedSessions": ["notes"], "sessions": ["api2", "docs", "web"],
                 "outlooks": {"web": "at its turn in the spawn stagger", "docs": "at its turn in the spawn stagger",
                              "api2": "when its CLI first reports its billing"}}
        out = self._romp("--all-following", "key", reply=(200, reply))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(),
                         "romp billing: 3 sessions following the default now carry their own pick, the API key (api2, docs, web); "
                         "api2 waits for its CLI's first report of which side it bills, which decides whether to reconnect; "
                         "docs, web reconnect at their turn in the spawn stagger, each CLI serving until then; "
                         "0 skipped; 1 failed (notes): it keeps following the default unchanged, the kernel's Log names the fault")
        reply.update(sessions=["web"], moved=1, outlooks={"web": "at its turn in the spawn stagger"}, failedSessions=["api", "notes"], failed=2)
        out = self._romp("--all-following", "key", reply=(200, reply))
        self.assertEqual(out.stdout.strip(),
                         "romp billing: 1 session following the default now carries its own pick, the API key (web); "
                         "it reconnects at its turn in the spawn stagger, its CLI serving until then; "
                         "0 skipped; 2 failed (api, notes): they keep following the default unchanged, the kernel's Log names the fault")

    def test_the_walk_with_nothing_moved_denies_followers_only_when_none_was_reached(self):
        # round 2 of the review (verb-5): with nothing moved and a record unwritten the head said "no running session follows
        # the machine default" while the tail named the follower the walk reached and could not write
        out = self._romp("--all-following", "key", reply=(200, {"ok": True, "pick": "key", "moved": 0, "skipped": 0, "unwritten": 1,
                                                                 "sessions": [], "skippedSessions": [], "unwrittenSessions": ["docs"],
                                                                 "outlooks": {}}))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "romp billing: no follower moved to the API key; 0 skipped; 1 not written (docs): its record would not read")
        out = self._romp("--all-following", "key", reply=(200, {"ok": True, "pick": "key", "moved": 0, "skipped": 1, "unwritten": 0,
                                                                 "sessions": [], "skippedSessions": ["api"], "unwrittenSessions": [],
                                                                 "outlooks": {}}))
        self.assertEqual(out.stdout.strip(), "romp billing: no running session follows the machine default, so none moved to the API key; "
                                             "1 skipped (api): it has its own pick", "a skipped session has its own pick and follows nothing")

    def test_an_empty_session_is_misuse_on_every_arm(self):
        # round 2 of the review (verb-6): `romp billing ""` passed the arity check as one argument and reached the kernel's
        # 400 (or "the kernel isn't running"), exit 1, against the verb's own header (misuse is the usage line, exit 2, before
        # any network), which `romp end ""` keeps
        before = len(type(self).seen)
        for args in (("",), ("", "login"), ("", "login", "--now")):
            out = self._romp(*args, reply=(400, {"ok": False, "error": "target required"}))
            self.assertEqual(out.returncode, 2, (args, out.stderr))
            self.assertTrue(out.stderr.startswith("usage: romp billing "), (args, out.stderr))
            self.assertEqual(out.stdout, "", args)
        self.assertEqual(len(type(self).seen), before, "no request reaches the kernel for an empty session")

    def test_the_read_names_the_explicit_default_the_box_cannot_bill_beside_what_a_follower_bills(self):
        # round 2 of the review (verb-3): "set explicitly" was printed of the RESOLVED side, so an explicit login default on a
        # machine with no login read as an explicit key; the line names what was set and why a follower bills the other side
        view = {"ok": True, "session": "web", "launched": "key", "launchedLogin": "", "launchedLabel": "", "live": "key",
                "pick": {"auth": "key", "login": "", "label": "", "explicit": False}, "pending": False, "held": False,
                "default": {"auth": "key", "login": "", "explicit": True, "label": "", "explicitPick": "login",
                            "explicitWhy": "no Claude login is signed in on this machine"}}
        out = self._romp("web", reply=(200, view))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.splitlines()[2],
                         "machine default: API key (login set explicitly, but no Claude login is signed in on this machine)")
        view["default"] = {"auth": "login", "login": "", "explicit": True, "label": MACHINE_LABEL, "explicitPick": "login:" + LID,
                           "explicitWhy": "no stored login with that id"}
        self.assertEqual(self._romp("web", reply=(200, view)).stdout.splitlines()[2],
                         'machine default: login "%s" (login "%s" set explicitly, but no stored login with that id)' % (MACHINE_LABEL, LID))
        view["default"] = {"auth": "key", "login": "", "explicit": True, "label": "", "explicitPick": "key", "explicitWhy": ""}
        self.assertEqual(self._romp("web", reply=(200, view)).stdout.splitlines()[2], "machine default: API key (set explicitly)")
        view["default"] = {"auth": "key", "login": "", "explicit": True, "label": ""}   # an older kernel: no explicitPick
        self.assertEqual(self._romp("web", reply=(200, view)).stdout.splitlines()[2], "machine default: API key (set explicitly)")

    def test_the_read_shows_the_machine_logins_label_when_the_kernel_supplies_one(self):
        # finding 15: the label rode the answer for a plain login default and words() dropped it without a stored-login id
        view = {"ok": True, "session": "web", "launched": "login", "launchedLogin": "", "launchedLabel": "", "live": "login",
                "pick": {"auth": "login", "login": "", "label": "", "explicit": False}, "pending": False, "held": False,
                "default": {"auth": "login", "login": "", "explicit": False, "label": MACHINE_LABEL}}
        out = self._romp("web", reply=(200, view))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.splitlines(), ["launched: login; the CLI reports: login", "pick: follows the machine default",
                                                   'machine default: login "%s" (the helper rule)' % MACHINE_LABEL])
        view["default"] = {"auth": "login", "login": "", "explicit": True, "label": ""}
        self.assertEqual(self._romp("web", reply=(200, view)).stdout.splitlines()[2], "machine default: login (set explicitly)")

    def test_the_read_says_when_the_cli_has_not_reported(self):
        # a launch retires the CLI's report (round 3 of the default billing's review, 2026-09-18: _stamp_launch_login), so
        # every fresh launch answers an empty `live` until the CLI's first init frame, which a resumed session streams at
        # its first turn; the read dropped the clause and "launched: login" stood alone, the launched side reading as a
        # report (the rebase follow-up, 2026-09-18)
        view = {"ok": True, "session": "web", "launched": "login", "launchedLogin": "", "launchedLabel": "", "live": "",
                "pick": {"auth": "login", "login": "", "label": "", "explicit": False}, "pending": False, "held": False,
                "default": {"auth": "login", "login": "", "explicit": False, "label": ""}}
        out = self._romp("web", reply=(200, view))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.splitlines()[0], "launched: login; the CLI has not reported yet")
        # no landed launch under this kernel (round 2 of the review, verb-4): "no CLI process running" claimed a fact the kernel
        # does not know (a dormant session's CLI can serve under its host; a connect in flight is a process) and dropped the
        # report the kernel kept, the reg's last apiKeyAuth; the head says what None means, and the report rides as "last"
        view["launched"] = None
        self.assertEqual(self._romp("web", reply=(200, view)).stdout.splitlines()[0], "launched: no CLI is up under this kernel",
                         "no landed launch, no report: the head alone")
        view["live"] = "key"
        self.assertEqual(self._romp("web", reply=(200, view)).stdout.splitlines()[0],
                         "launched: no CLI is up under this kernel; the CLI last reported: API key")
        # a client up whose landing attached a surviving CLI with no report (the reviewer's cannot-tell class; the rebase
        # follow-up, 2026-09-18): "no CLI is up" was false for it, and its first turn's report says what it bills
        view.update(live="", cannotTell=True)
        self.assertEqual(self._romp("web", reply=(200, view)).stdout.splitlines()[0],
                         "launched: a surviving CLI is attached that has not reported which side it bills; its first turn's report says")

    def test_an_old_kernels_404_names_the_cause_and_the_remedy_on_both_arms(self):
        # finding 13: a kernel from before this change answers its catch-all 404 (text, no JSON object) and the verb printed
        # "HTTP 404: not found" with no cause; the emoji verb's read arm names this case, and the two arms now do too. A
        # JSON 404 (the resolver's, an unknown session) still prints the kernel's reason
        for args in (("web",), ("web", "login")):
            out = self._romp(*args, reply=(404, b"not found", "text/plain"))
            self.assertEqual(out.returncode, 1, args)
            self.assertIn("predates", out.stderr, args)
            self.assertIn("restart romp so the kernel matches this command", out.stderr, args)
            self.assertEqual(out.stdout, "", args)
            out = self._romp(*args, reply=(404, {"ok": False, "error": "no live session named nosuch"}))
            self.assertEqual(out.returncode, 1, args)
            self.assertIn("no live session named nosuch", out.stderr, args)
            self.assertNotIn("predates", out.stderr, args)

    def test_every_reconnect_word_the_kernel_answers_has_a_line(self):
        # finding 1 (a text waiting, no turn open) and finding 4 (the park reasons): the verb words each, and offers --now
        # only where a turn is open to cut
        base = {"ok": True, "session": "web", "sid": SID, "pick": "key", "cut": False, "queued": False}
        cases = {
            "at the end of the open turn": ("web will bill the API key", "--now cuts the turn"),
            "at the next quiet moment": ("web will bill the API key", "a message waits to run first"),
            "after the compaction": ("web will bill the API key", "queued behind the compaction"),
            "after the work queued ahead of it": ("web will bill the API key", "queued behind the work ahead of it"),
            "after the move finishes": ("web will bill the API key", "move"),
            "when the usage hold lifts": ("web will bill the API key", "usage hold"),
            "held for live work": ("web will bill the API key", "live work"),
            "now": ("web bills the API key from now", "reconnecting"),
            "none needed": ("web bills the API key already", "no reconnect is needed"),
            "at its next launch": ("web will bill the API key", "next launch"),
            "when its connect lands": ("web will bill the API key", "no reconnect was asked"),
            # the rebase follow-up (2026-09-18): the reviewer's cannot-tell attach leaves the pending to the CLI's first
            # report, and a bounded relaunch waits for its spawn slot with the CLI still serving
            "when its CLI first reports its billing": ("web will bill the API key", "its first report decides"),
            "at its turn in the spawn stagger": ("web will bill the API key", "spawn stagger"),
        }
        # the census (round 2 of the review, tests-2): the cases are the kernel's two tables, so a word added there with no
        # line in bin/romp's tails fails here rather than printing the generic "the session reconnects <word>" with exit 0
        self.assertEqual(set(cases), set(km._BILLING_WORDS.values()) | set(km._BILLING_PARK_WORDS.values()),
                         "a kernel reconnect word without a verb line (or a verb line for no kernel word)")
        for when, (lead, tail) in cases.items():
            out = self._romp("web", "key", reply=(200, dict(base, reconnect=when)))
            self.assertEqual(out.returncode, 0, (when, out.stderr))
            self.assertTrue(out.stdout.startswith("romp billing: " + lead), (when, out.stdout))
            self.assertIn(tail, out.stdout, when)
            self.assertNotIn("the session reconnects %s" % when, out.stdout,
                             "the generic tail means bin/romp's tails has no line for this word: " + when)
            if when != "at the end of the open turn":
                self.assertNotIn("--now", out.stdout, "the cut is offered only where a turn is open: " + when)
        # the parked picks --now or default dropped (round 2 of the review, route-1) are said on the pick arm too
        out = self._romp("web", "key", "--now", reply=(200, dict(base, reconnect="now", cut=True, superseded=1)))
        self.assertEqual(out.stdout.strip(), "romp billing: the in-flight turn was cut; web bills the API key from now; "
                                             "the session is reconnecting to apply it; 1 earlier queued pick was dropped")
        out = self._romp("web", "default", reply=(200, dict(base, pick="default", default="key", reconnect="now", superseded=2)))
        self.assertEqual(out.stdout.strip(), "romp billing: web follows the machine default again (API key); "
                                             "the session is reconnecting to apply it; 2 earlier queued picks were dropped")


if __name__ == "__main__":
    unittest.main()
