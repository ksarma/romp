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
import ast
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
    dormant session, addressed by id and 404 by name, _resolve_sid's rule). Returns the two paths it wrote, for the
    caller to take back when it is done: the reg lands in the state root of the SHARED judge module (kernel.py loads
    judge.py under the one name romp_judge, whatever name the kernel itself was loaded under), the SDKDIR every other
    test module's kernel in the process reads, where a leftover reads as an SDK-owned session (2026-09-19)."""
    km.NAMES.mkdir(parents=True, exist_ok=True)
    (km.NAMES / sid).write_text("%s\t\n" % name)
    sdk = km.jd.STATE / "sdk"
    sdk.mkdir(parents=True, exist_ok=True)
    (sdk / (sid + ".json")).write_text(json.dumps({"sid": sid, "name": name, "alive": True}))
    return [km.NAMES / sid, sdk / (sid + ".json")]


class _FakeBackend:
    """A backend that records the calls the routes make, in order, and answers what the test tells it to."""

    def __init__(self, busy=False, why="", outlook="now", view=None, default="key", explicit=False, default_login="",
                 labels=None, inflight=None, unwritten=None, explicit_pick=None, outlooks=None, failed=None, staggered=False,
                 reads=True, follow_ok=True, set_ok=None):
        self.calls = []
        self._busy = busy
        self.reads = reads                     # record_reads: the record reads as an object (round 1 of the review, 2026-09-19)
        self.follow_ok = follow_ok             # follow_default_auth's verdict once the record read
        self.set_ok = set_ok                   # set_auth's verdict when not None (else: refused only for a `why`)
        self.parked = []                       # the sids the walk's park hook took (a move in flight)
        self.dropped = []                      # the sids the walk's after_write hook ran for, in order
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
        return (not self.why) if self.set_ok is None else self.set_ok

    def record_reads(self, sid):
        return self.reads                      # a bare read, as auth_unavailable_why is: not a recorded call

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
        return self.follow_ok

    def set_auth_followers(self, value, park=None, after_write=None):
        """The walk's shape with the kernel's two hooks (round 1 of the review, 2026-09-19): `park` is asked per follower
        and a True answer files the follower as parked with nothing written; `after_write` runs right after each moved
        follower's write and its count rides the answer as `superseded`."""
        self.calls.append(("set_auth_followers", value))
        if self.why:
            return None
        moved, sids, superseded = [], [], 0
        for name, sid in (("web", SID), ("tests", FAR_SID)):
            if park is not None and park(sid):
                self.parked.append(sid)
                continue
            moved.append(name)
            sids.append(sid)
            if after_write is not None:
                self.dropped.append(sid)
                superseded += int(after_write(sid) or 0)
        parked = [n for n, s in (("web", SID), ("tests", FAR_SID)) if s in self.parked]
        return {"moved": moved, "skipped": ["api"], "unwritten": list(self.unwritten), "failed": list(self.failed),
                "parked": parked, "movedSids": sids, "outlook": {n: w for n, w in self.outlooks.items() if n in moved},
                "superseded": superseded}

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
        cls._registered = _register(SID, "web")

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        for path in cls._registered:      # the shared registry is left as it was found (RouteServerLeavesTheSharedRegistryClean)
            path.unlink(missing_ok=True)

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
            # the sentence follows the PICK (round 1 of the review, 2026-09-19; its correctness-5): `default --now` was answered
            # with the --now sentence, whose advice (run it again without --now) the very next branch refuses, a circle
            if body["pick"] == "default":
                self.assertIn("`default` never queues, so run it again after the move finishes", resp["error"], body)
                self.assertNotIn("without --now", resp["error"], body)
            else:
                self.assertIn("run it again without --now to queue the pick behind the move", resp["error"], body)
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

    def test_now_during_a_compaction_tells_a_default_pick_it_never_queues(self):
        # round 1 of the review (correctness-4, narrowed by both refuters to the words; the compaction half of tests-1 refuted):
        # `default` never parks, and mid-compaction it applies at once with its reconnect deferred by request_reconnect's own
        # quiet test to the compaction turn's settle, so the refusal's advice to re-run it "to queue the pick behind the
        # compaction" promised a wait the re-run does not take; the plain pick's re-run does park, and keeps its sentence.
        # The gate itself is unchanged: `default` without --now is not refused during a compaction (the refuted half)
        fake = _FakeBackend(busy=True, outlook="deferred")
        a, b = self._local(fake, _compacting_now=lambda sid, **kw: True)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "default", "now": True})
        self.assertEqual(code, 409, resp)
        self.assertEqual(resp["error"], "web is compacting, and a compaction is not cut for a billing change; run it again without "
                                        "--now: `default` never queues, it applies at once and the session reconnects when the "
                                        "compaction ends")
        self.assertEqual(fake.calls, [])
        a, b = self._local(fake, _compacting_now=lambda sid, **kw: True)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login", "now": True})
        self.assertEqual(code, 409, resp)
        self.assertIn("run it again without --now to queue the pick behind the compaction, or wait for it to end", resp["error"])
        a, b = self._local(fake, _compacting_now=lambda sid, **kw: True)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "default"})
        self.assertEqual((code, resp["reconnect"]), (200, "at the end of the open turn"), "no behaviour change: applied now, deferred")
        self.assertEqual(fake.calls, [("follow_default_auth", SID)])

    def test_a_pick_this_box_cannot_bill_is_refused_before_the_park_on_the_plain_road(self):
        # round 1 of the review (kernel-1 with correctness-3): the plain road parked a pick the box already knew it could not
        # bill and answered ok with a moment, so the refusal came at the drain, visible only as a chat frame and kernel
        # stderr, while the --now road and the walk asked auth_unavailable_why first. Asked before the park now, in --now's
        # order: the queue is untouched. The read is live, so a transient unavailability (a login signing in) can refuse a
        # pick that would have applied at the drain: the cheaper error, visible at once and one keystroke to retry, against
        # a doomed parked op that answers ok and fails where nobody looks; the drain's refusal-reporting arm stays for the
        # state that changes between the check and the fire (ParkedPickRefusedAtTheDrain)
        fake = _FakeBackend(busy=True, why="that login's record is missing")
        parked = []
        a, b = self._local(fake, _gate_or_park=lambda sid, op: parked.append(op) or True)
        with a, b:
            code, resp = self._post({"target": "web", "pick": "login:" + LID})
        self.assertEqual(code, 409, resp)
        self.assertEqual(resp["error"], "that login's record is missing")
        self.assertEqual(parked, [], "nothing parked: the refusal came before the queue")
        self.assertEqual(fake.calls, [], "the box's reason, asked once, before the helper")

    def test_default_and_now_probe_the_record_before_dropping_the_parked_picks(self):
        # round 1 of the review (regression-2 with kernel-2, extra7-1 and extra8-1): both gate-off roads dropped the sid's
        # parked auth picks and THEN met the backend's second refusal reason, a record that would not read, and answered
        # "nothing was changed" over an emptied queue. Both refuters rejected the fix as filed (drop only after a successful
        # write: the drain can fire a stale parked pick between the write and the drop, the race round 2 closed) and took
        # a read-only probe ahead of the drop, through a backend predicate (record_reads, the read the two writes make),
        # keeping drop-before-write on the success path
        for body, call in (({"target": "web", "pick": "default"}, "follow_default_auth"),
                           ({"target": "web", "pick": "login:" + LID, "now": True}, "set_auth")):
            fake = _FakeBackend(reads=False)
            self._parked(("send", "a message parked ahead", "", "q1"), ("auth", "login"))
            a, b = self._local(fake)
            with a, b:
                code, resp = self._post(body)
            self.assertEqual(code, 409, (body, resp))
            self.assertEqual(resp["error"], "web's record would not read, so nothing was changed", body)
            self.assertEqual([op[0] for op in km._pending_ops.get(SID) or []], ["send", "auth"], (body, "the queue is untouched"))
            self.assertNotIn("superseded", resp, body)
            self.assertEqual([c[0] for c in fake.calls], [], (body, "%s is not reached: the probe came first" % call))
        # the residual window (the record goes unreadable between the probe and the write) is said, never "nothing was changed"
        for body, fake in (({"target": "web", "pick": "default"}, _FakeBackend(follow_ok=False)),
                           ({"target": "web", "pick": "login:" + LID, "now": True}, _FakeBackend(set_ok=False))):
            self._parked(("auth", "login"))
            a, b = self._local(fake)
            with a, b:
                code, resp = self._post(body)
            self.assertEqual(code, 409, (body, resp))
            self.assertEqual(resp["error"], "web's record would not read, so the pick was not applied; 1 earlier queued pick was "
                                            "dropped before the refusal", body)
            self.assertEqual(resp["superseded"], 1, body)
            self.assertNotIn(SID, km._pending_ops, body)

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

    def test_a_default_whose_clear_will_not_write_answers_409_in_the_writes_own_words_with_no_traceback(self):
        # round 1 of the billing verb's review (2026-09-19, the 17:14Z takes; fresh-2, the DISCLOSURE half, both refuters): follow_default_auth's
        # bare mirror raised out of POST /billing into do_POST's catch-all, an HTTP 500 whose body was traceback.format_exc()
        # with this box's absolute paths, on a kernel reachable over the tailnet. A REAL backend behind the real handler, a
        # live picked session, and the fault on the clear's own mirror (the write carrying the cleared pair, not gated on
        # authPending): the answer is a 409 in the write's own sentence, the live object and its record keep the pick, and
        # the body carries no traceback and no absolute path. A pick parked earlier rides the case: the road drops it before
        # the write (kept ahead of the write: a drop after it reopens the drain race round 2 closed on every successful
        # clear), so the sentence names the drop, as the record-unreadable refusal does
        d = tempfile.mkdtemp()
        Path(d, "session-hosts").write_text("off")   # a test that mints its own state root pins hosts off (2026-09-11)
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda m: None)
        be.login_ok = lambda: True
        be.key_state = lambda: "ok"
        reg = {"sid": SID, "name": "web", "cwd": d, "alive": True, "lastSid": SID, "auth": "login"}
        sb.write_reg(Path(d), SID, reg)
        s = sb.SdkSession(be, dict(reg))
        s._launched_auth = "login"
        s.auth_live = "login"
        be.sessions[SID] = s
        km._pending_ops.pop(SID, None)
        km._inflight_ops.pop(SID, None)
        km._park_op(SID, ("auth", "key"))   # PerSessionPick._parked's seed, with its cleanup
        self.addCleanup(lambda: (km._pending_ops.pop(SID, None), km._inflight_ops.pop(SID, None), km._save_pending_ops()))
        real_write = sb.write_reg

        def refused(state_dir, sid, reg):
            if sid == SID and reg.get("auth") == "":
                raise PermissionError(13, "Permission denied", str(sb._reg_path(state_dir, sid)))
            return real_write(state_dir, sid, reg)
        a, b = self._local(be)
        with a, b, mock.patch.object(sb, "write_reg", refused):
            code, resp = self._post({"target": "web", "pick": "default"})
        text = json.dumps(resp)
        self.assertEqual(code, 409, (code, text[:400]))
        self.assertEqual(resp, {"ok": False, "superseded": 1,
                                "error": "web's pick was not cleared: its record would not write (PermissionError), so it keeps its "
                                         "own pick; 1 earlier queued pick was dropped before the refusal"})
        self.assertNotIn("Traceback", text)
        self.assertNotRegex(text, r"/[A-Za-z0-9_.-]+/", "no absolute path reaches the caller")
        self.assertEqual((s.auth, s.auth_login, s.effective_auth()), ("login", "", "login"), "the live object keeps its pick")
        self.assertEqual(sb.read_reg(Path(d), SID)["auth"], "login", "the record is as it was")
        self.assertNotIn(SID, km._pending_ops, "the parked pick went before the write, and the sentence said so")

    def test_a_default_refused_for_its_record_answers_the_records_sentence_never_a_stale_one_an_earlier_refusal_left(self):
        # the owner's second pass over round 1's takes (2026-09-19): the fresh-2 sentence is popped by the route call that refused, so a later
        # refusal of another kind on the same sid must never read it. Pinned on the one road that reaches _auth_refusal's
        # pop with nothing of its own: a sentence left in the slot by a clear nobody read (follow_default_auth called by
        # something other than the route and refused), then the route's `default` whose record reads at the probe and is
        # gone at the backend's read (the check-then-act window the road accepts). The answer is the record's sentence in
        # the route's own words, and the slot is empty after it; until the entry clear the stale write sentence answered,
        # visible and false
        d = tempfile.mkdtemp()
        Path(d, "session-hosts").write_text("off")   # a test that mints its own state root pins hosts off (2026-09-11)
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda m: None)
        be.login_ok = lambda: True
        be.key_state = lambda: "ok"
        reg = {"sid": SID, "name": "web", "cwd": d, "alive": True, "lastSid": SID, "auth": "login"}
        sb.write_reg(Path(d), SID, reg)
        s = sb.SdkSession(be, dict(reg))
        s._launched_auth = "login"
        s.auth_live = "login"
        be.sessions[SID] = s
        km._pending_ops.pop(SID, None)
        km._inflight_ops.pop(SID, None)
        self.addCleanup(lambda: (km._pending_ops.pop(SID, None), km._inflight_ops.pop(SID, None), km._save_pending_ops()))
        real_write, real_read = sb.write_reg, sb.read_reg

        def refused(state_dir, sid, reg):
            if sid == SID and reg.get("auth") == "":
                raise PermissionError(13, "Permission denied", str(sb._reg_path(state_dir, sid)))
            return real_write(state_dir, sid, reg)
        with mock.patch.object(sb, "write_reg", refused):
            self.assertFalse(be.follow_default_auth(SID))       # a caller that is not the route: the sentence stays in the slot
        self.assertIn(SID, be._auth_refusals)
        be.record_reads = lambda sid: True                      # the route's probe read the record...
        a, b = self._local(be)
        with a, b, mock.patch.object(sb, "read_reg", lambda state_dir, sid: None if sid == SID else real_read(state_dir, sid)):
            code, resp = self._post({"target": "web", "pick": "default"})   # ...and the backend's own read found it gone
        self.assertEqual((code, resp), (409, {"ok": False, "error": "web's record would not read, so nothing was changed"}))
        self.assertEqual(be.pop_auth_refusal(SID), "", "the slot is empty: the stale sentence went at entry")
        self.assertEqual((s.auth, s.auth_login), ("login", ""), "the live object keeps its pick")


class RefusedRecordWrites(_RouteServer):
    """Round 2 of the billing verb's review (2026-09-20, the reviewer's 02:25Z rulings; its kernel-1, ruled HIGH, both
    refuters): a refused registry write answers as a REFUSAL REPLY on every road of POST /billing. The guard round 1's
    fresh-2 put on the `default` road stopped there: on the `--now` and plain roads set_auth's raise at its record mirror
    went up through do_POST's catch-all, an HTTP 500 whose body was traceback.format_exc() with this box's absolute state
    paths, the live object moved onto the new pick while the record read the old one with no arm behind it, and on `--now`
    the user's parked pick already dropped. A REAL backend behind the real handler on each road, each fault the ruling
    names injected in turn: the record write refused as EACCES, EROFS and ENOSPC; a record that reads at the route's probe
    and not at the backend's own read; a record that does not parse. The answer is a 409 in the failure's own words, no
    traceback and no absolute path in the body, the live object's pick pair and pending equal to the record's afterwards,
    the parked pick where the road's contract puts it (dropped before the write and named on `default` and `--now`, whose
    probe read the record; untouched on the plain road and wherever the probe refused first), and one problem row for a
    refused write. Red on the round-2 head for the `--now` and plain write faults: `500 != 409`, the body a traceback."""

    ROADS = (("default", {"target": "web", "pick": "default"}),
             ("now", {"target": "web", "pick": "key", "now": True}),
             ("plain", {"target": "web", "pick": "key"}))
    WRITE_FAULTS = (("EACCES", PermissionError(13, "Permission denied")), ("EROFS", OSError(30, "Read-only file system")),
                    ("ENOSPC", OSError(28, "No space left on device")))
    NOT_WRITTEN = {"default": "web's pick was not cleared: its record would not write (%s), so it keeps its own pick",
                   "now": "web's pick key was not applied: its record would not write (%s), so the session bills as it did",
                   "plain": "web's pick key was not applied: its record would not write (%s), so the session bills as it did"}
    DROPPED = "; 1 earlier queued pick was dropped before the refusal"
    ROW = {"default": "auth (web): its own pick was NOT cleared: the record write failed (%s: ",
           "now": "auth (web): the pick key was asked of this session, but its step failed (%s: ",
           "plain": "auth (web): the pick key was asked of this session, but its step failed (%s: "}

    def _picked(self):
        """A live session picked onto the login, its CLI running it, one earlier pick parked in its FIFO; a real backend over
        its own state root (hosts off), owning SID for the handler."""
        d = tempfile.mkdtemp()
        Path(d, "session-hosts").write_text("off")   # a test that mints its own state root pins hosts off (2026-09-11)
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda m: None)
        be.login_ok = lambda: True
        be.key_state = lambda: "ok"
        reg = {"sid": SID, "name": "web", "cwd": d, "alive": True, "lastSid": SID, "auth": "login"}
        sb.write_reg(Path(d), SID, reg)
        s = sb.SdkSession(be, dict(reg))
        s._launched_auth = "login"
        s.auth_live = "login"
        be.sessions[SID] = s
        km._pending_ops.pop(SID, None)
        km._inflight_ops.pop(SID, None)
        km._park_op(SID, ("auth", "login"))
        self.addCleanup(lambda: (km._pending_ops.pop(SID, None), km._inflight_ops.pop(SID, None), km._save_pending_ops()))
        return be, s, Path(d)

    def _reply_is_a_refusal(self, road, code, resp, s):
        text = json.dumps(resp)
        self.assertEqual(code, 409, (road, code, text[:400]))
        self.assertNotIn("Traceback", text)
        self.assertNotRegex(text, r"/[A-Za-z0-9_.-]+/", "no absolute path reaches the caller")
        self.assertEqual((s.auth, s.auth_login, bool(s._auth_pending)), ("login", "", False), "%s: the live object is as it was" % road)

    def test_a_refused_record_write_answers_409_in_its_own_words_on_every_road_and_leaves_the_live_pair_as_the_record(self):
        for road, body in self.ROADS:
            for label, err in self.WRITE_FAULTS:
                with self.subTest(road=road, fault=label):
                    be, s, d = self._picked()
                    real_write = sb.write_reg

                    def refused(state_dir, sid, reg, err=err):
                        if sid == SID:   # every write of this record from here on, the guard's retry included
                            raise type(err)(err.errno, err.strerror, str(sb._reg_path(state_dir, sid)))
                        return real_write(state_dir, sid, reg)
                    seq0 = be._problem_seq
                    a, b = self._local(be)
                    with a, b, mock.patch.object(sb, "write_reg", refused):
                        code, resp = self._post(body)
                    self._reply_is_a_refusal(road, code, resp, s)
                    cls = type(err).__name__
                    want = self.NOT_WRITTEN[road] % cls + (self.DROPPED if road != "plain" else "")
                    self.assertEqual(resp, dict({"ok": False, "error": want}, **({"superseded": 1} if road != "plain" else {})), road)
                    reg = sb.read_reg(d, SID)
                    self.assertEqual((s.auth, s.auth_login, bool(s._auth_pending)),
                                     (reg["auth"], reg.get("authLogin", ""), bool(reg.get("authPending"))),
                                     "%s: the live object and the record agree" % road)
                    self.assertEqual(km._pending_ops.get(SID, []), [] if road != "plain" else [("auth", "login")],
                                     "%s: dropped before the write on the probing roads and named; untouched on the plain road" % road)
                    rows = [p["text"] for p in be.problems(10) if p["seq"] > seq0]
                    self.assertEqual(len(rows), 1, (road, rows))
                    self.assertTrue(rows[0].startswith(self.ROW[road] % cls), (road, rows[0]))
                    self.assertEqual(be.pop_auth_refusal(SID), "", "the sentence was popped by the answer: nothing stale is left")

    def test_a_record_that_will_not_read_answers_409_in_the_records_words_on_every_road(self):
        real_read = sb.read_reg
        for road, body in self.ROADS:
            with self.subTest(road=road, fault="unreadable at the backend's read"):
                # the route's probe read it (the check-then-act window the roads accept), the backend's own read finds it gone
                be, s, d = self._picked()
                be.record_reads = lambda sid: True
                a, b = self._local(be)
                with a, b, mock.patch.object(sb, "read_reg", lambda state_dir, sid: None if sid == SID else real_read(state_dir, sid)):
                    code, resp = self._post(body)
                self._reply_is_a_refusal(road, code, resp, s)
                if road == "plain":
                    self.assertEqual(resp, {"ok": False, "error": "web's record would not read, so nothing was changed"})
                    self.assertEqual(km._pending_ops.get(SID), [("auth", "login")], "no probe, no drop: the queue is untouched")
                else:
                    self.assertEqual(resp, {"ok": False, "superseded": 1,
                                            "error": "web's record would not read, so the pick was not applied" + self.DROPPED})
                    self.assertNotIn(SID, km._pending_ops, "the probe passed, so the drop ran before the refusal, and the sentence says so")
                self.assertEqual(sb.read_reg(d, SID)["auth"], "login", "the record itself is as it was")
            with self.subTest(road=road, fault="unparseable"):
                be, s, d = self._picked()
                sb._reg_path(d, SID).write_text("{not a record")
                a, b = self._local(be)
                with a, b:
                    code, resp = self._post(body)
                self._reply_is_a_refusal(road, code, resp, s)
                self.assertEqual(resp, {"ok": False, "error": "web's record would not read, so nothing was changed"}, road)
                self.assertEqual(km._pending_ops.get(SID), [("auth", "login")], "%s: refused ahead of the drop, the queue untouched" % road)
                self.assertEqual(sb._reg_path(d, SID).read_text(), "{not a record", "nothing wrote over it")

    def test_a_dead_stderr_never_turns_an_answer_into_a_500_on_any_road(self):
        # kernel-2 of the same round (2026-09-20; both refuters of tests-1 and kernel-2): _drop_parked_auth's cancel line and
        # _park_op_locked's park line were bare sys.stderr.write calls, the one raise road left inside the three roads once
        # the record writes were guarded: a dead stderr (a reset journal stream, a closed tty, a full log disk) raised out of
        # the drop on `default` and `--now`, out of the park on the plain road, and out of the walk's after_write hook, and
        # do_POST's catch-all answered the traceback. Both lines go through _exit_log now, the kernel's best-effort writer,
        # and the two writers return normally under a stderr whose write raises
        class _Dead:
            def write(self, text):
                raise OSError(9, "Bad file descriptor")

            def flush(self):
                pass
        fake = _FakeBackend(outlooks={"web": "now", "tests": "now"})
        parks = lambda sid, op: km._park_op(sid, op) is None      # the plain road's park, through the real _park_op and its line
        cases = (("default", {"target": "web", "pick": "default"}, {}),
                 ("now", {"target": "web", "pick": "key", "now": True}, {}),
                 ("plain, parked", {"target": "web", "pick": "key"}, {"_gate_or_park": parks}),
                 ("all-following", {"pick": "key", "allFollowing": True}, {}))
        self.addCleanup(lambda: (km._pending_ops.pop(SID, None), km._pending_ops.pop(FAR_SID, None), km._save_pending_ops()))
        for label, body, stubs in cases:
            with self.subTest(road=label):
                km._pending_ops.pop(SID, None)
                km._pending_ops.pop(FAR_SID, None)
                km._park_op(SID, ("auth", "login"))       # the drop's line runs only with something to drop
                km._park_op(FAR_SID, ("auth", "login"))
                a, b = self._local(fake, **stubs)
                with a, b, mock.patch.object(km, "_sdk", lambda: fake), mock.patch.object(km.sys, "stderr", _Dead()):
                    code, resp = self._post(body)
                self.assertEqual(code, 200, (label, code, json.dumps(resp)[:400]))
        km._pending_ops.pop(SID, None)
        with mock.patch.object(km.sys, "stderr", _Dead()):
            km._park_op(SID, ("auth", "login"))            # returns: the line is best-effort
            self.assertEqual(km._pending_ops[SID], [("auth", "login")], "parked all the same")
            self.assertEqual(km._drop_parked_auth(SID, "the test"), 1, "dropped all the same, and counted")
        self.assertNotIn(SID, km._pending_ops)


class AllFollowing(_RouteServer):

    """POST /billing {pick, allFollowing}: the walk over this kernel's live followers."""

    def test_the_walk_answers_the_names_moved_and_skipped(self):
        fake = _FakeBackend()
        with mock.patch.object(km, "_sdk", lambda: fake):
            code, resp = self._post({"pick": "key", "allFollowing": True})
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp, {"ok": True, "pick": "key", "moved": 2, "skipped": 1, "unwritten": 0, "failed": 0, "parked": 0,
                                "sessions": ["web", "tests"], "skippedSessions": ["api"], "unwrittenSessions": [], "failedSessions": [],
                                "parkedSessions": [], "parkedReconnect": "after the move finishes",
                                "outlooks": {"web": "now", "tests": "none needed"}, "superseded": 0},
                         "each moved session's outlook rides the answer in the reconnect words (round 2 of the review); the "
                         "parked bucket and its word since round 1 of the review, 2026-09-19")
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
        self.assertEqual(resp["superseded"], 2, "the count rides the walk's answer, summed by the walk from its hook")
        self.assertNotIn(SID, km._pending_ops)
        self.assertEqual([op[0] for op in km._pending_ops[FAR_SID]], ["send"], "the parked send keeps its place")
        # PER FOLLOWER, through the walk's after_write hook (round 1 of the review, 2026-09-19; its correctness-2): dropped
        # after the whole walk, a drain cycle inside the walk fired an earlier follower's parked pick over the walk's write
        # while the answer said none was superseded. The route hands the drop to the walk, which runs it right after each
        # follower's write (set_auth_followers pins the interleaving on the real backend)
        self.assertEqual(fake.dropped, [SID, FAR_SID], "the kernel's drop ran through the hook, once per moved follower")

    def test_a_follower_mid_move_has_the_pick_parked_behind_its_move_and_is_not_written(self):
        # round 1 of the review (tests-1's move half with extra8-2, both refuters): the walk was the third road to bypass the
        # FIFO and the only one with no move guard, so a follower whose queue `_moving` holds (be.move() waiting on its
        # set_cwd answer, a quiet session) was written and asked, and the arm tore its client down under the move. Both
        # refuters took PARK over skip: the plain road's park in its own words (_BILLING_PARK_WORDS["move"]), applied by
        # the drain when the move ends, where a skipped follower stays on the default with nothing to retry. The walk's
        # `park` hook is the kernel's: it parks the pick in the follower's FIFO and the follower is filed apart; it never
        # reaches the walk's after_write hook (the `continue` after the park), so its own parked picks are not dropped. The
        # compaction half was refuted (a compacting session is
        # never quiet, so the walk's request defers to the compaction's settle on its own) and has no gate
        fake = _FakeBackend(outlooks={"web": "now", "tests": "now"})
        km._pending_ops.pop(SID, None)
        km._pending_ops.pop(FAR_SID, None)
        km._park_op(SID, ("auth", "login"))                      # the moving follower's earlier parked pick: kept, the walk's queues behind it
        self.addCleanup(lambda: (km._pending_ops.pop(SID, None), km._pending_ops.pop(FAR_SID, None), km._save_pending_ops()))
        km._moving.add(SID)
        try:
            with mock.patch.object(km, "_sdk", lambda: fake):
                code, resp = self._post({"pick": "key", "allFollowing": True})
        finally:
            km._moving.discard(SID)
        self.assertEqual(code, 200, resp)
        self.assertEqual((resp["parked"], resp["parkedSessions"], resp["parkedReconnect"]), (1, ["web"], "after the move finishes"))
        self.assertEqual((resp["moved"], resp["sessions"], resp["outlooks"]), (1, ["tests"], {"tests": "now"}))
        self.assertEqual(km._pending_ops[SID], [("auth", "login"), ("auth", "key")],
                         "parked behind the move, after the pick already queued: the FIFO's press order, the last wins")
        self.assertEqual(fake.parked, [SID], "the hook answered True for the moving follower alone")
        self.assertEqual(fake.dropped, [FAR_SID], "the drop ran for the moved follower alone: a parked follower keeps its queue")
        self.assertEqual(resp["superseded"], 0)


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
                               "failed": [], "parked": [], "superseded": 0,   # the kernel's two hooks, None here (round 1 of the review)
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
        # THE RECORD-READ GATE OF THE WALK'S DROP (round 2 of the billing verb's review, 2026-09-20; its extra8-1, both
        # refuters): the after_write hook, the kernel's drop of a follower's parked picks, runs only after a write that
        # LANDED, so a follower whose record would not read keeps its queued pick; the spy's call list is the pin, since a
        # hook returning 0 would leave `superseded` at 0 under the mutation that moves the hook above the `written` guard
        seen = []
        out = self.be.set_auth_followers("key", after_write=lambda sid: seen.append(sid) or 1)
        self.assertEqual(out, {"moved": ["web"], "skipped": [], "unwritten": ["docs"], "failed": [], "parked": [], "movedSids": [web.sid],
                               "outlook": {"web": "next-launch"}, "superseded": 1})
        self.assertEqual(seen, [web.sid], "the hook ran for the written follower alone: nothing landed for docs, so nothing is dropped")
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
        # the road's word (round 1 of the review, 2026-09-19; its tests-5): the attach leg says "attached to this session's
        # surviving CLI"; the launch leg below says "launched this session's new CLI". Collapsing the two to "attach" left
        # every module green; only the launch leg's assertion discriminates that mutation, this one pins the reverse
        self.assertTrue(any("auth (api): attached to this session's surviving CLI, which runs on the login while its pick is the key"
                            in m for m in self.logs), self.logs[-2:])
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
        self.assertTrue(any("auth (tests): launched this session's new CLI, which runs on the key while its pick is the login"
                            in m for m in self.logs), self.logs[-2:])   # the launch leg's word (tests-5, the discriminating half)
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
    # per-session try, the stagger in the words). THE RED-BEFORE RECORD OF THIS BLOCK, RE-DERIVED BY RUNNING (round 2 of
    # the billing verb's review, 2026-09-20; its extra6-2 with tests-2 and extra7-1): this file, as committed, run on a
    # detached checkout of the rebase follow-up's parent, the tree the follow-up's tests were written against; the block
    # holds 19 tests from four commits, the follow-up's ten, the rebase onto the reviewer's round 2's three, and the six the
    # two later commits appended (their own header below). RED there, at an assertion of its own, 12: the follow-up's
    # never-landed login, slot-flag-in-the-hold, unlanded pair, leased-follower pick, leased-follower ask, staggered outlook,
    # report outlook and stagger-clause tests; the rebase onto round 2's census pin (the_follower_step_is_reached_only...);
    # and three of the appended six (the_init_closes_a_pick..., after_the_close_the_door_refuses...,
    # a_raise_in_the_closers_compose_read...). ERROR BEFORE ITS ASSERTION, 6, which says nothing about the defect each
    # pins: billing_view_names_a_surviving_cli... (KeyError: the read had no cannotTell field yet) and
    # set_auth_followers_survives_one_followers_fault... (TypeError on this round's after_write spy; without the spy the
    # PermissionError the follow-up's per-session try now contains); the rebase onto round 2's two guard tests and two of
    # the appended six (a_refusal_sentence_a_caller_left_unread..., follow_default_auth_whose_clear_will_not_write...), all
    # four a PermissionError escaping the call the guard now contains. GREEN there, 1: request_reconnect_runs_on_the_loop...,
    # green by design (the ordering it pins shipped before this PR; red with _call_on_loop running its callable inline)

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
        # the ask's line is 787's since the rebase folded the verb's closer into _recover_picked_pending_at_init (one method,
        # one line), so the pin reads 787's wording, not the verb's old one
        line = [m for m in self.logs if "left to this report and nothing was armed for it, so it is asked now" in m]
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
        seen = []   # the after_write hook's call list (extra8-1, 2026-09-20): a follower whose step RAISED is not written, so no drop
        with mock.patch.object(sb, "write_reg", refused):
            out = self.be.set_auth_followers("key", after_write=lambda sid: seen.append(sid) or 1)
        self.assertEqual((out["moved"], out["failed"], out["unwritten"], sorted(out["outlook"])), (["tests", "web"], ["api"], [], ["tests", "web"]))
        self.assertEqual((seen, out["superseded"]), ([web.sid, tests.sid], 2), "the hook ran for the two written followers, never for the failed one")
        for s in (web, tests):
            self.assertEqual((s.auth, s._auth_pending, self._reg(s.sid)["auth"]), ("key", "key", "key"), s.name)
        self.assertEqual((api.auth, api.auth_login, api._auth_pending, api._auth_pending_login, api._relaunch_bounded, api._landing_ask_bounded),
                         ("", "", "", "", False, False), "the failed follower is a follower again, with no ask")
        self.assertEqual((self._reg(api.sid).get("auth", ""), self._reg(api.sid).get("authPending", False)), ("", False),
                         "the reg names no pick and no ask (the fault here is the mirror itself; the retry's own pin is "
                         "test_a_walk_step_that_raises_after_its_mirror_has_the_reg_rolled_back_with_the_pair)")
        rows = [p["text"] for p in self.be.problems(10) if "step failed" in p["text"]]
        self.assertEqual(len(rows), 1, self.be.problems(10))
        self.assertIn("auth (api): the pick key was asked of this session, but its step failed (PermissionError", rows[0])
        self.assertIn("it keeps following the machine default and stays on the login", rows[0])
        self.assertTrue(any("1 step failed (api), left following the default as the step found it" in m for m in self.logs), self.logs[-1:])

    def test_set_auth_followers_fault_leaves_a_followers_standing_ask_as_the_step_found_it(self):
        # the reviewer's round 2 (2026-09-19; its kernel-1) replaced the walk's round-1 handler, which wiped the failed
        # follower to a fixed clean state, with one guard that restores what stood when the step began, COMPARED before the
        # write: an ask the step did not write is not the step's to wipe. The verb's walk kept a copy of the round-1 handler
        # through its rebase, so a follower carrying the default walk's parked ask (a CLI reporting the login, no landing of
        # this kernel stamped, the default moved to the login: the ask waits for the landing) lost that ask when its own
        # set_auth step raised at the reg mirror. Through the guard the follower is a follower again with its ask standing
        # for its landing, the retry mirrors the pair and the flag, and the row says which ask stands
        web, api = self._sess("web", launched="login"), self._sess("api")
        for s in (web, api):
            self._queue_loop(s)
        api.auth_live = "login"                             # the report restored from the reg; no landing has stamped
        api._auth_pending, api._auth_pending_login = "login", ""
        self.be._update_reg(api.sid, apiKeyAuth=False, authPending=True)
        real_write = sb.write_reg

        def refused(state_dir, sid, reg):
            if sid == api.sid and reg.get("auth") == "key":
                raise PermissionError(13, "Permission denied", str(sb._reg_path(state_dir, sid)))
            return real_write(state_dir, sid, reg)
        with mock.patch.object(sb, "write_reg", refused):
            out = self.be.set_auth_followers("key")
        self.assertEqual((out["moved"], out["failed"]), (["web"], ["api"]))
        self.assertEqual((api.auth, api.auth_login, api._auth_pending, api._auth_pending_login, api._relaunch_bounded, api._landing_ask_bounded),
                         ("", "", "login", "", False, False), "as the step found it: a follower, its standing ask kept, no slot memo")
        reg = self._reg(api.sid)
        self.assertEqual((reg.get("auth", ""), reg.get("authPending")), ("", True),
                         "the reg names no pick and the standing ask (the fault here is the mirror itself, so this case cannot see "
                         "the retry; its pin is the after-the-mirror test beside it)")
        self.assertFalse(api._reconnect or api._reconnect_when_idle, "no request: the ask waits for its landing as it did")
        rows = [p["text"] for p in self.be.problems(10) if "step failed" in p["text"]]
        self.assertEqual(len(rows), 1, self.be.problems(10))
        self.assertIn("auth (api): the pick key was asked of this session, but its step failed (PermissionError", rows[0])
        self.assertIn("it keeps following the machine default and stays on the login until its next connect or the next default "
                      "write, with the login ask it already carried standing for that event", rows[0])
        self.assertTrue(any("1 step failed (api), left following the default as the step found it" in m for m in self.logs), self.logs[-1:])

    def test_follow_default_auth_runs_both_hops_through_the_one_guard_and_a_refused_mirror_leaves_the_session_as_found(self):
        # the reviewer's round 2 (2026-09-19; its kernel-1): one guarded entry point for every follower step, so a raise
        # inside it (the ask's reg mirror on a full or read-only state directory) is contained the same way on every road.
        # The verb's `default` road called _follow_default and _follow_default_unlanded bare, so the raise went up through
        # POST /billing with the pending written in memory and no arm behind it: the dots on, and a later pick of that side
        # read as already applying. Both hops now run under the guard: the landed step (a session running the login while
        # the default is the key) and the unlanded step (no running side, a connect in flight composed from the old pick)
        web = self._sess("web", auth="login", launched="login")
        web.auth_live = "login"
        self.be._update_reg(web.sid, apiKeyAuth=False)
        wq = self._queue_loop(web)
        api = self._sess("api", auth="login")
        api._launching = dict(self.be._launch_shape(api))   # composed from the pick, the login; the default is the key
        aq = self._queue_loop(api)
        real_write = sb.write_reg

        def refused(state_dir, sid, reg):
            if sid in (web.sid, api.sid) and reg.get("authPending"):
                raise PermissionError(13, "Permission denied", str(sb._reg_path(state_dir, sid)))
            return real_write(state_dir, sid, reg)
        with mock.patch.object(sb, "write_reg", refused):
            self.assertTrue(self.be.follow_default_auth(web.sid), "the pick is cleared, which is what happened; the fault is a row")
            self.assertTrue(self.be.follow_default_auth(api.sid))
        for s, q in ((web, wq), (api, aq)):
            self.assertEqual((s.auth, s.auth_login), ("", ""), "%s: the verb's own clear stands" % s.name)
            self.assertEqual((s._auth_pending, s._auth_pending_login, s._relaunch_bounded), ("", "", False),
                             "%s: left as the step found it, no half-written ask" % s.name)
            self.assertEqual(len(q), 0, "%s: no request behind a restored pending" % s.name)
            reg = self._reg(s.sid)
            self.assertEqual((reg["auth"], reg.get("authPending", False)), ("", False), "%s: the retry mirrored the clear" % s.name)
        rows = [p["text"] for p in self.be.problems(10) if "step failed" in p["text"]]
        self.assertEqual(len(rows), 2, self.be.problems(10))
        self.assertIn("auth (web): follows the machine default again: automatic, but this session's step failed (PermissionError", rows[0])
        self.assertIn("; it stays on the login until its next connect or the next default write, with no ask standing", rows[0])
        self.assertIn("auth (api): follows the machine default again: automatic, but this session's step failed (PermissionError", rows[1])
        self.assertIn("; it stays on the side it is on until its next connect or the next default write, with no ask standing", rows[1])

    def _box_with_nothing_to_fall_to(self):
        """The box the closer's refused-pair gate lives on: no key to fall to (Claude Code's settings cannot be read) and the
        same unreadable read for the machine login's fall. Returns the lease set the backend's lease read answers from."""
        self.be.key_state = lambda: "unknown"
        self.be._helper_source_read = lambda: (None, False)
        leased = self.__dict__.setdefault("_leased", set())
        self.be._host_lease_live = lambda sess: sess.sid in leased
        return leased

    def _picked_survivor_on(self, name, launched, pick, leased):
        """The object the CLI's first init finds, built through real code with no hand-set stamps (round 1 of the billing
        verb's review, 2026-09-19, the 17:14Z takes; extra5-1, and the owner's second pass over those takes): a survivor the previous kernel launched on the stored
        login `launched` (the reg's launchedLogin), a live host lease and no report (the cannot-tell class), the user's
        pick of the stored login `pick` parked on it before the boot re-attach composes (set_auth's never-landed branch),
        the real compose and the cannot-tell attach landing, the pending standing. Returns the session and its recording
        loop."""
        self.n += 1
        sid = "11111111-2222-3333-4444-%012d" % self.n
        reg = {"sid": sid, "name": name, "cwd": self.d, "alive": True, "lastSid": sid,
               "auth": "login", "authLogin": launched["id"], "launchedLogin": launched["id"]}
        sb.write_reg(Path(self.d), sid, reg)
        s = sb.SdkSession(self.be, dict(reg))
        s._launched_auth = None
        s.inflight = 0
        self.be.sessions[sid] = s
        q = self._queue_loop(s)
        leased.add(sid)
        self.assertEqual(s._launched_login, launched["id"], "the reg restored the launched login")
        self.assertTrue(self.be.set_auth(sid, "login:" + pick["id"], chip=False))
        self.assertEqual((s._auth_pending_target(), len(q)), (("login", pick["id"]), 0), "%s: parked for the landing" % name)
        fell, side, lid = self.be._decide_auth(s)
        self.be._stamp_compose(s, side, lid)                 # the real compose's stamps
        s._host_is_attach = True
        s._connect_landed()                                   # the cannot-tell attach lands: the pending stands
        self.assertEqual((s._launched_auth, s._auth_pending_target()), (None, ("login", pick["id"])), name)
        return s, q

    # ---- round 1 of the billing verb's review, the reviewer's 17:14Z takes, and the owner's second pass over them (2026-09-19):
    # the six tests the two commits that took them appended here (extra6-2, 2026-09-20: recorded apart from the follow-up's
    # block they sit in). At their own parent, the round-1 addendum's head, with this file copied in: RED at an assertion of
    # its own, 3 (the_init_closes_a_pick..., after_the_close_the_door_refuses..., a_raise_in_the_closers_compose_read...);
    # ERROR BEFORE ITS ASSERTION, 2 (a_refusal_sentence_a_caller_left_unread... and follow_default_auth_whose_clear_will_not_
    # write...: the PermissionError fresh-2's guard now contains escaped the call); GREEN by design, 1
    # (request_reconnect_runs_on_the_loop...). The_follower_step_is_reached_only... and the_verbs_ask_lines... after them
    # belong to the block above

    def test_the_init_closes_a_pick_whose_relaunch_would_carry_the_token_this_report_refused_and_asks_one_of_another_login(self):
        # round 1 of the billing verb's review (2026-09-19, the 17:14Z takes; extra5-1, in both refuters' narrowed form). The full chain through
        # real code, no hand-set stamps: a survivor launched by the previous kernel on stored login A (the reg's launchedLogin),
        # a live host lease and no report (the cannot-tell class), the user's pick parked on it before the boot re-attach
        # composes (set_auth's never-landed branch), the real compose, the cannot-tell attach landing, then the CLI's first
        # init reporting a KEY word: A's token was not used. The wrong-landing branch marks A refused and, with nothing to
        # fall to on this box (no helper readable, no machine login to fall to), DECLINES a relaunch; the closer then ran
        # its ask on the reconnect flags alone and re-armed the very relaunch just declined, which composed A again (the
        # compose reads the pick, and the refusal leaves it nothing to fall to), carried the same token, landed the same
        # way and served the pending on the shape word: a false served on a session billing the wrong account, the CLI and
        # its work torn down for nothing. Gated on what the relaunch would compose: the same refused pair is CLOSED with a
        # row that says the pick cannot be applied on this box and what bills instead (never served, never silent, never
        # retargeted: the pick stands); a pick of ANOTHER stored login than the refused launch is still asked, since that
        # relaunch composes B and is right
        a, b = self._stored_login("Alpha"), self._stored_login("Beta")
        leased = self._box_with_nothing_to_fall_to()
        for name, pick, asked in (("web", a, False), ("api", b, True)):
            s, q = self._picked_survivor_on(name, a, pick, leased)   # launched on A; the pick: A again, or B
            sid = s.sid
            del self.logs[:]
            seq0 = self.be._problem_seq
            self.be._note_auth_source(s, "apiKeyHelper")          # the CLI's first init: a key word, A's token was not used
            rows = [p["text"] for p in self.be.problems(20) if p["seq"] > seq0]
            self.assertTrue(any("nothing to fall to on this box, so the session stays where it landed" in r for r in rows),
                            (name, rows))                         # the wrong-landing branch declined a relaunch
            self.assertEqual((s._launched_auth, s._launched_login), ("key", ""), "%s: the report is the stamp; A is not what runs" % name)
            self.assertTrue(sb._logins.record_state(self.d, a["id"]).get("refused"), "A is marked refused")
            closed = [r for r in rows if "so the pick cannot be applied on this box" in r]
            if asked:
                self.assertEqual((s._auth_pending_target(), len(q)), (("login", b["id"]), 1),
                                 "api: a pick of ANOTHER stored login than the refused launch is asked; its relaunch composes B")
                self.assertEqual(len([m for m in self.logs if "so it is asked now" in m]), 1, self.logs)
                self.assertEqual(closed, [], "nothing closed: the relaunch is right")
                continue
            self.assertEqual((s._auth_pending, s._auth_pending_login, self._reg(sid)["authPending"], len(q), s._reconnect),
                             ("", "", False, 0, False), "web: the pending is closed with no ask and no arm; the dots go")
            self.assertEqual((s.auth, s.auth_login, self._reg(sid)["auth"], sb.SdkBackend.reg_login(self._reg(sid))),
                             ("login", a["id"], "login", a["id"]), "the pick stands: no retarget, no served clear")
            self.assertEqual([m for m in self.logs if "asked now" in m or "the pick is served" in m], [], "neither asked nor served")
            self.assertEqual(len(closed), 1, rows)
            self.assertEqual(closed[0], "auth (web): this session's surviving CLI reported its billing, the key, while its pick is the "
                                        "Alpha login, whose token this same report refused; a relaunch would carry that token again and "
                                        "land the same way, so the pick cannot be applied on this box: it stands unapplied, nothing is "
                                        "asked, and the session keeps billing the key")
            # the compose the gate read is the arm's own: it would still name A, with nothing to fall to
            shape = self.be._launch_shape(s)
            self.assertEqual((shape["auth"], shape["login"]), ("login", a["id"]))

    def test_after_the_close_the_door_refuses_the_refused_login_and_no_later_report_relaunch_or_restart_re_asks(self):
        # the owner's second pass over round 1's takes (2026-09-19), two claims the lens left unpinned on the close above. ONE ROW PER KERNEL
        # LIFE: the close row is filed unkeyed (no repeat suffix), so a second firing in one life would be a second ring
        # row, and none is reachable: the pick's only way back is set_auth, whose door refuses a refused stored login
        # (auth_unavailable_why through logins.why_unavailable, the record the wrong-landing branch marked), and a later
        # report in the same life finds the side stamped and no pending, so the closer is not entered. NOTHING AFTER THE
        # CLOSE RE-ASKS: a second report from the surviving CLI; a same-life relaunch (any other pick's) that composes the
        # standing pick, with nothing to fall to still names A, carries the refused token again, lands as a launch and
        # reports the key once more (the wrong-landing branch declines once more; the closer's entry gate, a stamped side,
        # is shut); and a kernel restart over the reg the close left (the pick standing, authPending False, launchedLogin
        # cleared by the evidence persist, the report persisted), whose boot re-attach reads the report and stamps it. The
        # restart after the relaunch and the restart right after the close read the same reg fields, asserted below
        a = self._stored_login("Alpha")
        leased = self._box_with_nothing_to_fall_to()
        s, q = self._picked_survivor_on("web", a, a, leased)
        sid = s.sid
        self.be._note_auth_source(s, "apiKeyHelper")            # the close (the test above)

        def closes():
            return [p["text"] for p in self.be.problems(50) if "so the pick cannot be applied on this box" in p["text"]]

        def asks():
            return [m for m in self.logs if "so it is asked now" in m]
        self.assertEqual((len(closes()), s._auth_pending, len(q), asks()), (1, "", 0, []), "the close: one row, no ask")
        # the door: the refused login cannot be picked again in this life, so no second pending forms for the pair
        self.assertFalse(self.be.set_auth(sid, "login:" + a["id"], chip=False))
        self.assertEqual(self.be.last_auth_refusal, "the Alpha login was refused: the token was not used and the CLI signed in "
                                                    "with the CLI's apiKeyHelper credential instead")
        self.assertEqual((s._auth_pending, len(q), len(closes())), ("", 0, 1))
        # a second report from the same CLI: the side is stamped and no pending stands, so the closer is not entered
        self.be._note_auth_source(s, "apiKeyHelper")
        self.assertEqual((s._auth_pending, len(q), len(closes()), asks()), ("", 0, 1, []))
        # a same-life relaunch: the compose names the standing pick (nothing to fall to), the launch lands, the CLI reports
        # the key again; the branch declines again and the closer is not entered (a stamped side, no pending)
        fell, side, lid = self.be._decide_auth(s)
        self.assertEqual((side, lid), ("login", a["id"]), "the relaunch would carry the refused token again")
        self.be._stamp_compose(s, side, lid)
        s._host_is_attach = False
        self.be._stamp_launch_login(s)
        s._connect_landed()
        self.assertEqual((s._launched_auth, s._launched_login), ("login", a["id"]))
        seq1 = self.be._problem_seq
        self.be._note_auth_source(s, "apiKeyHelper")
        rows = [p["text"] for p in self.be.problems(50) if p["seq"] > seq1]
        self.assertTrue(any("nothing to fall to on this box, so the session stays where it landed" in r for r in rows), rows)
        self.assertEqual((s._auth_pending, len(q), len(closes()), asks(), s._launched_login), ("", 0, 1, [], ""))
        # a kernel restart: the reg the close left (the same fields a restart right after the close reads)
        reg = self._reg(sid)
        self.assertEqual((reg["auth"], sb.SdkBackend.reg_login(reg), reg["authPending"], reg.get("launchedLogin", ""), reg["apiKeyAuth"]),
                         ("login", a["id"], False, "", True))
        s2 = sb.SdkSession(self.be, dict(reg))
        s2._launched_auth = None
        s2.inflight = 0
        self.be.sessions[sid] = s2
        q2 = self._queue_loop(s2)
        self.assertEqual((s2.auth, s2.auth_login, s2._auth_pending, s2._launched_login, s2.auth_live),
                         ("login", a["id"], "", "", "key"), "the pick stands across the restart with no pending; the report is restored")
        fell, side, lid = self.be._decide_auth(s2)
        self.be._stamp_compose(s2, side, lid)
        s2._host_is_attach = True
        s2._connect_landed()
        self.assertEqual(s2._launched_auth, "key", "the boot re-attach reads the report the init persisted")
        del self.logs[:]
        self.be._note_auth_source(s2, "apiKeyHelper")
        self.assertEqual((s2._launched_auth, s2._auth_pending, len(q2), len(closes()), asks()), ("key", "", 0, 1, []))

    def test_a_raise_in_the_closers_compose_read_is_contained_by_the_guard_and_the_pending_stands_for_the_next_pick(self):
        # the owner's second pass over round 1's takes (2026-09-19): the closer's gate reads what the relaunch would compose
        # (_launch_shape) inside the guarded step, so a raise there is the guard's to contain (_follow_default_guarded: the
        # pending pair restored to what stood, the mirror retried, one row naming the pick's next deciding event) and the
        # init handler's tail still runs. Round 5 pinned that for the served branch's mirror; this pins it for the new read:
        # the pending stands for the next pick, nothing is asked, nothing is closed. A REQUIREMENT PIN, not a
        # characterisation (round 2 of the billing verb's review, 2026-09-20; its correctness-1 and the refuted extra6-1,
        # both refuters of the latter): the read has a production road. The settings read decodes the operator's Claude Code
        # settings file as UTF-8 inside credentials._read_settings, whose guards convert OSError and json's ValueError to
        # CredentialError and let UnicodeDecodeError through, so a settings file that is not UTF-8 (a torn rewrite of one
        # holding a non-ASCII byte included) raises out of _launch_shape with nothing patched, through key_state and
        # _helper_source_read, which catch CredentialError alone; the login records' read catches its own faults
        # (OSError, ValueError). The OSError injected here stands in for that class at the same site: the row formats the
        # exception's class name, which is what the assertion below pins
        a = self._stored_login("Alpha")
        leased = self._box_with_nothing_to_fall_to()
        s, q = self._picked_survivor_on("web", a, a, leased)
        del self.logs[:]
        seq0 = self.be._problem_seq
        with mock.patch.object(self.be, "_launch_shape", side_effect=OSError(28, "No space left on device")):
            self.be._note_auth_source(s, "apiKeyHelper")        # returns: the raise never leaves the handler
        rows = [p["text"] for p in self.be.problems(20) if p["seq"] > seq0]
        self.assertTrue(any("nothing to fall to on this box, so the session stays where it landed" in r for r in rows), rows)
        failed = [r for r in rows if "but the pick's step failed" in r]
        self.assertEqual(len(failed), 1, rows)
        self.assertEqual(failed[0], "auth (web): this session's CLI reported its billing, but the pick's step failed (OSError: [Errno 28] "
                                    "No space left on device); the connect goes on with the CLI it has, and it stays on the key until "
                                    "its next connect or the next pick, with the login ask it already carried standing for that event")
        self.assertEqual((s._auth_pending_target(), self._reg(s.sid)["authPending"]), (("login", a["id"]), True),
                         "the pending stands, restored and mirrored, for the next pick")
        self.assertEqual((len(q), s._reconnect, [m for m in self.logs if "asked now" in m or "the pick is served" in m]), (0, False, []),
                         "neither asked nor served: the step did not finish")
        self.assertEqual([r for r in rows if "so the pick cannot be applied on this box" in r], [], "not closed either")
        self.assertEqual((s._launched_auth, s.api_key_auth, self._reg(s.sid)["apiKeyAuth"]), ("key", True, True),
                         "the report is the stamp and the init's tail ran")

    def test_request_reconnect_runs_on_the_loop_after_its_caller_returns_never_inline(self):
        # the owner's second pass over round 1's takes (2026-09-19): the ordering the enumeration's loop double models (OneAskPerInit._Loop
        # queues each callback and runs it when the handler that scheduled it has returned). request_reconnect reaches
        # _do_request_reconnect only through _call_on_loop's call_soon_threadsafe, so a request made inside a loop callback
        # (the init handler's wrong-landing branch; the closer's ask a few lines later) runs after that callback returns,
        # never inside it, and the flags it sets are not yet set when the caller reads them. Pinned against a REAL loop on
        # the session object the enumeration drives (no CLI: the arm composes a shape and sets the flag)
        import asyncio
        s = self._sess("web", launched="login")
        s.inflight = 0
        seen = {}

        async def handler():
            s.request_reconnect()
            seen["at return"] = s._reconnect
            await asyncio.sleep(0)                          # the loop's next iteration: the queued callback runs
            seen["after a yield"] = s._reconnect
            ran = []
            self.assertTrue(sb._call_on_loop(loop, ran.append, 1))
            seen["helper at return"] = list(ran)
            await asyncio.sleep(0)
            seen["helper after a yield"] = list(ran)
        loop = asyncio.new_event_loop()
        try:
            s.loop = loop
            loop.run_until_complete(handler())
        finally:
            loop.close()
        self.assertEqual(seen, {"at return": False, "after a yield": True, "helper at return": [], "helper after a yield": [1]})

    def test_a_refusal_sentence_a_caller_left_unread_is_gone_at_the_next_clear_so_no_later_refusal_reads_it_stale(self):
        # the owner's second pass over round 1's takes (2026-09-19): pop_auth_refusal's promise (a caller never reads a refusal another call
        # left) rested on the route being follow_default_auth's one caller and popping on every refusal. The door no longer
        # rests on that: follow_default_auth clears the sid's slot at entry, before its reg read, so what a caller pops after
        # a False is this call's own sentence or nothing. A sentence left by a refused clear nobody read is gone at the next
        # clear on the sid, whichever way that clear ends: refused for the other reason (its record gone), or done
        web = self._sess("web", auth="login", launched="login")
        web.auth_live = "login"
        self._queue_loop(web)
        real_write, real_read = sb.write_reg, sb.read_reg

        def refused(state_dir, sid, reg):
            if sid == web.sid and reg.get("auth") == "":
                raise PermissionError(13, "Permission denied", str(sb._reg_path(state_dir, sid)))
            return real_write(state_dir, sid, reg)
        with mock.patch.object(sb, "write_reg", refused):
            self.assertFalse(self.be.follow_default_auth(web.sid))
        self.assertIn(web.sid, self.be._auth_refusals, "left unread: this caller did not pop")
        with mock.patch.object(sb, "read_reg", lambda state_dir, sid: None if sid == web.sid else real_read(state_dir, sid)):
            self.assertFalse(self.be.follow_default_auth(web.sid), "the other reason: a record that would not read")
        self.assertEqual(self.be.pop_auth_refusal(web.sid), "", "the stale sentence went at entry, and this refusal left none")
        self.be._auth_refusals[web.sid] = "a sentence nobody read"
        self.assertTrue(self.be.follow_default_auth(web.sid))
        self.assertEqual(self.be.pop_auth_refusal(web.sid), "", "a clear that succeeds leaves nothing to pop")
        # the caller fact the promise used to rest on, kept as a census: the route's `default` road is the one caller
        calls = {}
        for path in (os.path.join(BIN, "romp-kernel"), os.path.join(BIN, "romp_sdk_backend.py")):
            def walk(node, fn):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        fn = child.name
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) and child.func.attr == "follow_default_auth":
                        calls[fn] = calls.get(fn, 0) + 1
                    walk(child, fn)
            walk(ast.parse(Path(path).read_text()), None)
        self.assertEqual(calls, {"_billing_request": 1})

    def test_follow_default_auth_whose_clear_will_not_write_restores_the_pick_and_refuses_in_its_own_words(self):
        # round 1 of the billing verb's review (2026-09-19, the 17:14Z takes; fresh-2, the STATE half, both refuters): the clear of the pick pair
        # ran under the hold and its reg mirror ran bare, OUTSIDE the one-guard rule the step below it takes, so a reg write
        # that failed (a full or read-only state directory) left the live object following the machine default, the status
        # rows and the verb's read with it, while the reg and a kernel restart still carried the pick: the caller was told
        # it failed and the change had happened, the inverse of round 1's regression-2. The clear and its mirror are one
        # unit now: the pair is restored on a raise, the record is untouched, a row is filed, and the caller gets False with
        # a sentence of this failure's own (never the 409's "record would not read, so nothing was changed", which
        # misdescribes a refused write). The fault is injected on the CLEAR's own mirror, the write that carries the
        # cleared pair, whatever authPending says: the guard test above exempts exactly this write with its authPending
        # predicate, so it stayed green over the bare mirror
        web = self._sess("web", auth="login", launched="login")
        web.auth_live = "login"
        wq = self._queue_loop(web)
        real_write = sb.write_reg

        def refused(state_dir, sid, reg):
            if sid == web.sid and reg.get("auth") == "":
                raise PermissionError(13, "Permission denied", str(sb._reg_path(state_dir, sid)))
            return real_write(state_dir, sid, reg)
        seq0 = self.be._problem_seq
        with mock.patch.object(sb, "write_reg", refused):
            self.assertFalse(self.be.follow_default_auth(web.sid), "the write was refused: the caller is told the pick stands")
        self.assertEqual((web.auth, web.auth_login), ("login", ""), "the live object keeps its pick (restored from the snapshot)")
        self.assertEqual((web.effective_auth(), self.be.billing_view(web.sid)["pick"]["explicit"]), ("login", True),
                         "the status rows and the verb's read see the pick, not the default")
        reg = self._reg(web.sid)
        self.assertEqual((reg["auth"], reg.get("authPending", False)), ("login", False), "the record is as it was")
        self.assertEqual((len(wq), web._auth_pending), (0, ""), "no step ran: nothing asked, nothing pending")
        self.assertEqual(self.be.pop_auth_refusal(web.sid),
                         "web's pick was not cleared: its record would not write (PermissionError), so it keeps its own pick")
        self.assertEqual(self.be.pop_auth_refusal(web.sid), "", "popped once: a later refusal never reads this one")
        rows = [p["text"] for p in self.be.problems(10) if p["seq"] > seq0]
        self.assertEqual(len(rows), 1, rows)
        self.assertTrue(rows[0].startswith("auth (web): its own pick was NOT cleared: the record write failed (PermissionError: "), rows[0])
        self.assertIn("; the pick stands and the session bills as it did", rows[0])
        # the dormant road (no object; the reg write is the whole change) is wrapped the same way
        self.n += 1
        dsid = "11111111-2222-3333-4444-%012d" % self.n
        sb.write_reg(Path(self.d), dsid, {"sid": dsid, "name": "docs", "cwd": self.d, "alive": True, "lastSid": dsid,
                                          "auth": "login", "apiKeyAuth": False})

        def refused_dormant(state_dir, sid, reg):
            if sid == dsid:
                raise OSError(28, "No space left on device", str(sb._reg_path(state_dir, sid)))
            return real_write(state_dir, sid, reg)
        with mock.patch.object(sb, "write_reg", refused_dormant):
            self.assertFalse(self.be.follow_default_auth(dsid))
        self.assertEqual(self._reg(dsid)["auth"], "login", "the record is as it was")
        self.assertEqual(self.be.pop_auth_refusal(dsid),
                         "docs's pick was not cleared: its record would not write (OSError), so it keeps its own pick")

    def test_the_follower_step_is_reached_only_through_the_guard_and_its_own_hand_offs(self):
        # CENSUS PIN (the verb's rebase onto the reviewer's round 2, 2026-09-19): every caller of the follower's step runs
        # it through _follow_default_guarded, so the only bare calls of _follow_default and _follow_default_unlanded are the
        # guard's and the two steps' hand-offs to each other. A new caller lands here first
        src = Path(os.path.join(BIN, "romp_sdk_backend.py")).read_text()
        calls = {}

        def walk(node, fn):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fn = child.name
                if (isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                        and child.func.attr in ("_follow_default", "_follow_default_unlanded")):
                    calls.setdefault(fn, []).append(child.func.attr)
                walk(child, fn)
        walk(ast.parse(src), None)
        self.assertEqual(calls, {"_follow_default_guarded": ["_follow_default"],
                                 "_follow_default": ["_follow_default_unlanded", "_follow_default"],   # the `because` hand-off,
                                 #                                                                        then the landed-in-the-gap re-run
                                 "_follow_default_unlanded": ["_follow_default"]})                     # the landed hop back

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


    # ---- round 1 of the billing verb's review (2026-09-19, the rulings of 13:45Z): the high, the gap cases, the reachable
    # injectors, the walk's hooks, the memo's life and the quiet tail. THE RED-BEFORE RECORD, RE-DERIVED BY RUNNING (round 2
    # of the review, 2026-09-20; its tests-2, extra6-2 and extra7-1): this file, as committed, run on a detached checkout of
    # the round-1 commit's parent (the rebased twin of 1100d3f0f), ten tests. RED there, at an assertion of its own, 2:
    # the_walks_slot_memo_dies... and the_asks_tail_and_the_served_line... (a CHARACTERISATION PIN whose first leg was red
    # all the same: its label speaks for its injector's missing production road, not for a green base). GREEN there, 4: the
    # two gap cases (a_launch_that_lands_in_the_gap... and a_landing_in_the_gap_that_matches...: coverage of code already
    # right, each red under its own mutation of the branch, the re-check and the fresh read after the gap) and the two other
    # labelled pins (a_walk_step_that_raises_after_its_mirror..., billing_view_names_the_stored_login...). ERROR BEFORE ITS
    # ASSERTION, 4, an EMPTY red that says nothing about the defect: the high's two tests (AttributeError: _stamp_compose
    # lands with the fix, so the committed form cannot run at the parent), the_walk_drops_each_followers_parked_picks...
    # (TypeError: the after_write hook lands with the fix) and record_reads_is_the_records_own_read... (AttributeError:
    # record_reads lands with the fix). THE HIGH'S RED IS ESTABLISHED TWO WAYS (extra7-1, both refuters): by the MUTATION
    # at the fixed head, _connect_landed's picked-branch guard reverted to its pre-fix spelling
    # `(self._launched_auth is None and not attach) or self._launched_unkeyed_pick`, which reds the high's two tests,
    # OneAskPerInit and the quiet-tail pin (its landing leg rides the same road) and nothing else: on the round-2 head 4
    # failed, 127 passed against a 131-passed control, and on this commit the same four against the module's own count (the
    # PR body's round-2 section pastes both); and by a PRE-FIX RED THAT REACHES ITS ASSERTION: the parent with a copy of
    # _options's compose block standing in for _stamp_compose (the helper lands with the fix) reds the three committed
    # tests on the defect itself, (('', ''), False, 0) != (('login', ''), True, 0) (the pending cleared as served across the
    # cannot-tell attach), (('', ''), 0, False) != (('key', ''), 1, True) (nothing asked at the landing that could tell), and
    # the enumeration's wrong-silent set 12 states over the pinned residual. The defect's pre-existence is the enumeration
    # at 1100d3f0f in the body's round-1 section

    def _composed(self, s):
        """The compose's stamps as _options writes them (_decide_auth, then _stamp_compose: the shape, _launching,
        _connecting, the fast ask, _launched_keyed, _options_login and _launched_unkeyed_pick), so a test's window is the
        REAL compose's and the unkeyed-pick flag is derived from it, never hand-set (round 1 of the review, 2026-09-19;
        its regression-1, both refuters: a flag set beside a shape the compose cannot produce pins a state the code cannot
        reach). Returns (side, shape)."""
        fell, side, lid = self.be._decide_auth(s)
        shape, _ = self.be._stamp_compose(s, side, lid)
        return side, shape

    def _unkeyed_key_survivor(self, name, cls, report=""):
        """The high's class (round 1 of the review, 2026-09-19; regression-1): a session PICKED onto the key on a box whose
        Claude Code settings cannot be read (key_state "unknown": the compose cannot bill the key as the key, _launch_shape
        names the login for it, and the compose flags the pick unkeyed), its CLI a survivor of a kernel restart under a
        live host lease, the boot re-attach composed and not landed. `cls` "lease": no report on record, the cannot-tell
        attach; "report": the CLI's report restored from the reg (`report`, the side it bills), an attach that can tell.
        The compose's own derivation is asserted, so a fixture that stopped producing the flag would say so here."""
        self.be.key_state = lambda: "unknown"
        s = self._sess(name, auth="key")
        if cls == "report":
            self.be._update_reg(s.sid, apiKeyAuth=(report == "key"))
            s.auth_live = report
        leased = self.__dict__.setdefault("_leased", set())
        leased.add(s.sid)
        self.be._host_lease_live = lambda sess: sess.sid in leased
        q = self._queue_loop(s)
        side, shape = self._composed(s)
        self.assertEqual((side, shape["auth"], s._launched_unkeyed_pick, s._launched_keyed), ("key", "login", True, False),
                         "reachability: the compose itself flags an explicit key pick this box cannot bill as the key")
        s._host_is_attach = True
        return s, q

    def test_a_pick_parked_across_a_cannot_tell_attach_of_an_unkeyed_key_compose_stands_for_the_clis_first_init(self):
        # THE HIGH (round 1 of the review, 2026-09-19; regression-1, both refuters): the never-landed park (this PR) writes a
        # pick on the object with no request, and _connect_landed's picked branch served a pending on `_launched_unkeyed_pick`
        # with no attach guard, so on a cannot-tell attach the parked pick was cleared as SERVED, the closer found no
        # pending at the CLI's first init, and the session kept billing the old account with no reconnect, no dots and no
        # problem row (the per-init mismatch check is silenced by the same flag). At 787's head the plain login pick
        # ended in the same silence through the already-applying branch, while a stored-login pick was relaunched by the
        # request branch, so the regression is the stored-login pick on this road (the body says which). The flag is
        # the compose's own here (_unkeyed_key_survivor); both clauses now end in `and not attach`, the pending stands
        # across the attach, and the CLI's first init decides it: served when the CLI bills the pick, asked when it does not
        rec = self._stored_login()
        cases = (("web", "login", "apiKeyHelper", "asked"), ("api", "login:" + rec["id"], "apiKeyHelper", "asked"),
                 ("tests", "key", "none", "asked"), ("docs", "key", "apiKeyHelper", "served"))
        for name, pick, init, expect in cases:
            s, q = self._unkeyed_key_survivor(name, "lease")
            self.assertTrue(self.be.set_auth(s.sid, pick, chip=False))
            want = sb._logins.parse_pick(pick)
            self.assertEqual((s._auth_pending_target(), len(q)), (want, 0), "%s: parked for the landing, no request" % name)
            del self.logs[:]
            s._connect_landed()                                   # the cannot-tell attach lands
            self.assertIsNone(s._launched_auth, name)
            self.assertEqual((s._auth_pending_target(), self._reg(s.sid)["authPending"], len(q)), (want, True, 0),
                             "%s: the pending stands across the attach; the unkeyed flag serves nothing on the attach road" % name)
            self.assertTrue(any("auth (%s): attached to this session's surviving CLI, which has not reported which side it bills"
                                % name in m and "the CLI's first init decides it" in m for m in self.logs), (name, self.logs))
            del self.logs[:]
            self.be._note_auth_source(s, init)                    # the CLI's first init, the closing event
            self.assertEqual(s._launched_auth, "key" if init == "apiKeyHelper" else "login", name)
            if expect == "asked":
                self.assertEqual((s._auth_pending_target(), len(q), self._reg(s.sid)["authPending"]), (want, 1, True),
                                 "%s: asked at the init, the relaunch composes the pick" % name)
                self.assertTrue(any("left to this report and nothing was armed for it, so it is asked now" in m for m in self.logs),
                                (name, self.logs))
            else:
                self.assertEqual((s._auth_pending, len(q), self._reg(s.sid)["authPending"]), ("", 0, False),
                                 "%s: served by the report, no relaunch" % name)
                self.assertTrue(any("the pick is served, no reconnect" in m for m in self.logs), (name, self.logs))
        # the silence that made this the worst outcome available: a login pick on a survivor billing the key rings no
        # mismatch row (the compose meant the key, and the CLI reports the key), so nothing but the closer could say
        self.assertEqual([p["text"] for p in self.be.problems(20) if "auth (web)" in p["text"]], [])

    def test_a_pick_parked_across_an_attach_that_can_tell_with_an_unkeyed_key_compose_is_asked_at_the_landing(self):
        # the worse of the two roads (round 1 of the review, 2026-09-19; regression-1, both refuters): with the CLI's report
        # on record the attach stamps it and CAN tell, so _note_auth_source's init step never runs (its gate is a stamp of
        # None) and the landing is the only closing event there is. The unkeyed clause cleared the parked pick as served
        # at that landing while the survivor billed the other account, and nothing could ever ask it. Guarded, the landing
        # finds the pending unserved and asks it (_ask_parked_pick's attach road), once; the init asks nothing more
        rec = self._stored_login()
        for name, report, pick in (("web", "login", "key"), ("api", "key", "login:" + rec["id"]), ("tests", "key", "login")):
            s, q = self._unkeyed_key_survivor(name, "report", report)
            self.assertTrue(self.be.set_auth(s.sid, pick, chip=False))
            want = sb._logins.parse_pick(pick)
            self.assertEqual((s._auth_pending_target(), len(q)), (want, 0), "%s: parked for the landing (the report is on record)" % name)
            del self.logs[:]
            s._connect_landed()                                   # the attach stamps the report: it can tell
            self.assertEqual(s._launched_auth, report, name)
            self.assertEqual((s._auth_pending_target(), len(q), self._reg(s.sid)["authPending"]), (want, 1, True),
                             "%s: unserved and asked at the landing" % name)
            runs = "the %s" % report   # the survivors here launched on the machine login or the key: no stored login (tests-4, 2026-09-20)
            self.assertTrue(any("auth (%s): attached to this session's surviving CLI, which runs on %s while its pick is" % (name, runs) in m
                                and "left to this landing, so it is asked now" in m for m in self.logs), (name, self.logs))
            with mock.patch.object(s, "_recover_picked_pending_at_init", wraps=s._recover_picked_pending_at_init) as closer:
                self.be._note_auth_source(s, "apiKeyHelper" if report == "key" else "none")
            self.assertEqual((closer.call_count, len(q)), (0, 1), "%s: the init step is not entered with a stamp on record; no second ask" % name)

    def test_a_launch_that_lands_in_the_gap_of_the_never_landed_branch_is_read_afresh(self):
        # round 1 of the review (tests-2, both refuters; the refuters' own probe, moved into this class): the landed-in-the-gap
        # half of set_auth's never-landed branch (the re-check under the hold, the fresh read_picks after it) had no test,
        # and either mutation left every module green. A follower with no report and a LIVE host lease, a launch in flight
        # composed from the key; the pick is the login. The launch LANDS between the picks read and the never-landed hold
        # (the lease read is the file I/O in that gap), stamping the key. Read afresh, the guards see a landed object on
        # the key with a login pick and REQUEST the reconnect; read from the stale snapshot, the pick is written for a
        # landing that has passed. And the refuter's addition: deleting the branch outright DROPS the pick (nothing
        # written, nothing pending), worse than leaving it pending, so the reg's pick is pinned too
        s = self._sess("web")
        s._launching = dict(self.be._launch_shape(s), auth="key", login="")
        s._connecting = True
        s._host_is_attach = False
        q = self._queue_loop(s)
        fired = []

        def lease_lands(sess):
            if not fired:
                fired.append(1)
                sess._connect_landed()
                self.assertEqual(sess._launched_auth, "key")
            return True
        self.be._host_lease_live = lease_lands
        self.assertTrue(self.be.set_auth(s.sid, "login", chip=False))
        self.assertEqual(fired, [1], "the seam ran")
        self.assertEqual((s.auth, s._auth_pending, self._reg(s.sid)["auth"]), ("login", "login", "login"), "the pick is written, not dropped")
        self.assertEqual(len(q), 1, "the landing has passed: the pick must make its own request, not wait for a landing")
        self.assertEqual(self.be.auth_apply_outlook(s.sid), "now")

    def test_a_landing_in_the_gap_that_matches_the_pick_is_not_already_applying(self):
        # tests-2's second case (the refuters' probe): the same gap, with the connect in flight composing the SIDE THE PICK
        # NAMES. Read afresh the landed stamp equals the pick and nothing is owed; read from the stale snapshot (launched
        # None, launching == the pick) the already-applying guard writes a pending for a landing that has passed, and the
        # dots never clear
        s = self._sess("api", auth="login")
        s._launching = dict(self.be._launch_shape(s), auth="login", login="")
        s._connecting = True
        s._host_is_attach = False
        q = self._queue_loop(s)
        fired = []

        def lease_lands(sess):
            if not fired:
                fired.append(1)
                sess._connect_landed()
                self.assertEqual(sess._launched_auth, "login")
            return True
        self.be._host_lease_live = lease_lands
        self.assertTrue(self.be.set_auth(s.sid, "login", chip=False))
        self.assertEqual(fired, [1], "the seam ran")
        self.assertEqual((s.auth, s._auth_pending, self._reg(s.sid)["auth"]), ("login", "", "login"),
                         "the landed process already runs the pick: nothing pending, the pick kept")
        self.assertEqual(len(q), 0, self.logs[-2:])
        self.assertIs(bool(self._reg(s.sid).get("authPending")), False)

    def test_a_walk_step_that_raises_after_its_mirror_has_the_reg_rolled_back_with_the_pair(self):
        # CHARACTERISATION PIN (round 1 of the review, tests-3, both refuters; relabelled by the round's addendum after its
        # injector lens, 2026-09-19): the guard's step road retries the mirror of the PAIR (_mirror_auth), not the flag alone
        # (_mirror_auth_pending), and nothing pinned it: the two tests above inject their fault AT the reg write that would
        # have put the pick there, so a retry that mirrored the flag alone, or no retry at all, left them green. The fault
        # here lands AFTER set_auth's mirror, on the step's own tail line, and it is one NO PRODUCTION ROAD MAKES AT THIS
        # HEAD: the ruling offered two injectors, a raising log callback (_log_quietly's closed-stderr case) and a raising
        # _note_reconnect_ask, and neither raises with the kernel's wiring. The kernel's only log callback is kernel.py's
        # _backend_log, which writes through _exit_log's try/except (since 2026-09-10), and everything else the request
        # branch runs after its mirror cannot raise: _note_reconnect_ask takes locks and formats a string, request_reconnect
        # goes through _call_on_loop (never raises), _poke swallows, and the walk passes chip=False so no chip is written.
        # What this pins is the guard's containment against an arbitrary post-mirror raise, the shape of fork PR #787's own
        # pin (tests/test_sdk_backend.py, the step that fails after its mirror write, which patches _note_reconnect_ask to
        # raise): the retry writes the pair back, and the mutation that mirrors the flag alone reds it. The callback raises
        # once, on that line alone: a callback that kept raising would take the guard's own row down too (a bare _log in
        # its handler, fork PR #787's, not this round's)
        web, api = self._sess("web", launched="login"), self._sess("api", launched="login")
        for s in (web, api):
            self._queue_loop(s)
        real_cb = self.be._log_cb
        raised = []

        def closed_stderr(m):
            if str(m).startswith("auth (api): set to key;") and not raised:
                raised.append(str(m))
                raise OSError(9, "Bad file descriptor")
            return real_cb(m)
        self.be._log_cb = closed_stderr
        out = self.be.set_auth_followers("key")
        self.be._log_cb = real_cb
        self.assertEqual(len(raised), 1, "the fault fired on the step's own tail line, after the mirror")
        self.assertEqual((out["moved"], out["failed"]), (["web"], ["api"]))
        self.assertEqual((api.auth, api.auth_login, api._auth_pending, api._relaunch_bounded, api._landing_ask_bounded),
                         ("", "", "", False, False), "the object is a follower again, as the step found it")
        reg = self._reg(api.sid)
        self.assertEqual((reg.get("auth", ""), reg.get("authPending", False)), ("", False),
                         "the retry mirrored the PAIR: the reg names no pick and no ask, so a restart does not launch the key "
                         "the row said was rolled back")
        rows = [p["text"] for p in self.be.problems(10) if "step failed" in p["text"]]
        self.assertEqual(len(rows), 1, self.be.problems(10))
        self.assertIn("auth (api): the pick key was asked of this session, but its step failed (OSError", rows[0])

    def test_the_walk_drops_each_followers_parked_picks_right_after_its_own_write_and_parks_a_mover(self):
        # round 1 of the review (correctness-2, both refuters): the kernel dropped every moved follower's parked picks after
        # the WHOLE walk, so a drain cycle inside the walk fired an earlier follower's parked pick over the walk's write
        # while the answer said none was superseded; a drop before the write (the finding's other option) loses a
        # still-parked pick for a follower the walk skips or fails. Per follower, after its successful write, through the
        # kernel's hook, with the count riding the callback's returns: the mutation that must fail is moving the drop back
        # after the loop, which this spy sees as the other follower's pick already written at the first drop
        web, api = self._sess("web", launched="login"), self._sess("api", launched="login")
        for s in (web, api):
            self._queue_loop(s)
        seen = []

        def after_write(sid):
            other = api if sid == web.sid else web
            seen.append((self.be.sessions[sid].name, other.auth))   # what the OTHER follower's pick reads at this drop
            return 1 if sid == web.sid else 2
        out = self.be.set_auth_followers("key", after_write=after_write)
        self.assertEqual(out["moved"], ["api", "web"])
        self.assertEqual(seen, [("web", ""), ("api", "key")],
                         "web's drop ran before api's write and api's after it: per follower, in the roster's order")
        self.assertEqual(out["superseded"], 3, "the count rides through the callback, never summed afterwards")
        # the park hook (tests-1's move half with extra8-2): a follower the kernel parks is written nothing and asked nothing,
        # filed apart, and never reaches the after_write hook (the `continue` after the park), so its own parked picks are
        # not dropped
        docs, tests = self._sess("docs", launched="login"), self._sess("tests", launched="login")
        dq, tq = self._queue_loop(docs), self._queue_loop(tests)
        dropped = []
        out = self.be.set_auth_followers("key", park=lambda sid: sid == docs.sid, after_write=lambda sid: dropped.append(sid) or 0)
        self.assertEqual((out["moved"], out["parked"], out["movedSids"], out["skipped"]), (["tests"], ["docs"], [tests.sid], ["api", "web"]))
        self.assertEqual((docs.auth, docs._auth_pending, len(dq), docs._relaunch_bounded, docs._landing_ask_bounded), ("", "", 0, False, False),
                         "parked by the kernel: nothing written or asked for it")
        self.assertNotIn("auth", self._reg(docs.sid))
        self.assertEqual((tests.auth, len(tq), dropped), ("key", 1, [tests.sid]))
        self.assertTrue(any("1 parked behind a move in flight (docs), the pick applies when the move finishes" in m for m in self.logs), self.logs[-1:])

    def test_the_walks_slot_memo_dies_with_the_pick_it_belongs_to(self):
        # round 1 of the review (correctness-6 with kernel-3; extra5-2 and extra6-3 the same family): the walk's slot memo
        # (_landing_ask_bounded) was spent only where the parked pick was ASKED (_ask_parked_pick), so a pick SERVED at the
        # CLI's first init, or withdrawn, or reverted, left it standing, and the next landing that asked an ordinary pick
        # drew the walk's spawn-stagger slot from it and told the user so. The refuters corrected the proposed fix (clear it
        # at the ask's stand-down: that spends it while its ask still stands and loses a correct stagger on a re-ask) to the
        # invariant: the memo goes with the pick it belongs to, cleared at every disposal of the pending and written with
        # every pending set_auth's request branch writes. Every disposal site is driven here; the last case drives the
        # consequence on the one road that reaches _ask_parked_pick again inside one kernel life
        self.be.key_state = lambda: "unknown"    # the consequence's road needs a key pick and a login pick to compose alike
        # (1) SERVED at the CLI's first init (extra6-3's walk-driven served twin)
        web, wq = self._leased_unreported_follower("web", composed="login")
        self.assertEqual(self.be.set_auth_followers("login")["moved"], ["web"])
        self.assertIs(web._landing_ask_bounded, True, "the walk's memo, written with the parked pick")
        web._connect_landed()
        self.be._note_auth_source(web, "none")                    # the CLI bills the login the pick names: served
        self.assertEqual((web._auth_pending, web._relaunch_bounded, web._landing_ask_bounded, len(wq)), ("", False, False, 0), "served: the memo is gone")
        # (2) the served check's withdrawal (_served_by_connect, the running process already runs it)
        api, aq = self._leased_unreported_follower("api", composed="login")
        self.assertEqual(self.be.set_auth_followers("login")["moved"], ["api"])
        api._connect_landed()
        self.be._note_auth_source(api, "none")
        self.assertIs(api._landing_ask_bounded, False)
        api._auth_pending, api._auth_pending_login, api._landing_ask_bounded = "login", "", True   # a walk's pending the running process serves
        self.assertTrue(api._served_by_connect("request", pick="auth"))
        self.assertEqual((api._auth_pending, api._landing_ask_bounded), ("", False), "withdrawn as served: the memo with it")
        # (3) set_auth's revert branch (a re-pick of the side the CLI runs withdraws the pending)
        docs, dq = self._leased_unreported_follower("docs", composed="key")
        self.assertEqual(self.be.set_auth_followers("login")["moved"], ["docs"])
        self.assertIs(docs._landing_ask_bounded, True)
        docs._connect_landed()
        self.be._note_auth_source(docs, "apiKeyHelper")            # the CLI bills the key: the login pick is asked (the memo spent)
        self.assertEqual((docs._auth_pending, docs._landing_ask_bounded, len(dq)), ("login", False, 1))
        tests, tq = self._leased_unreported_follower("tests", composed="key")
        self.assertEqual(self.be.set_auth_followers("login")["moved"], ["tests"])
        tests._connect_landed()
        tests._launched_auth = "key"                                # the landing that could tell (the report on record) would stamp this
        self.assertTrue(self.be.set_auth(tests.sid, "key", chip=False))   # the revert: the side the CLI runs, the pending withdrawn
        self.assertEqual((tests._auth_pending, tests._relaunch_bounded, tests._landing_ask_bounded), ("", False, False), "reverted: the memo with it")
        # (4) the unchanged branch's clear, (5) the follower step's withdrawal, (6) the unlanded step's clear of a moot pending
        one = self._sess("one", launched="key")
        self._queue_loop(one)
        one._auth_pending, one._landing_ask_bounded = "key", True    # a stale pending of the side the CLI runs, the memo left from a walk
        self.assertTrue(self.be.set_auth(one.sid, "key", chip=False))
        self.assertEqual((one._auth_pending, one._landing_ask_bounded), ("", False), "the unchanged branch's clear")
        two = self._sess("two", auth="login", launched="login")
        two.auth_live = "login"
        two._auth_pending, two._landing_ask_bounded = "login", True
        self._queue_loop(two)
        self.assertTrue(self.be.follow_default_auth(two.sid))      # the default is the login here (no helper readable): already runs it
        self.assertEqual((two._auth_pending, two._landing_ask_bounded), ("", False), "the follower step's withdrawal")
        three = self._sess("three", auth="login")
        three._auth_pending, three._landing_ask_bounded = "login", True
        three._launching = dict(self.be._launch_shape(three), auth="login", login="")   # the connect in flight launches the default
        self._queue_loop(three)
        self.assertTrue(self.be.follow_default_auth(three.sid))
        self.assertEqual((three._auth_pending, three._landing_ask_bounded), ("", False), "the unlanded step's clear of a moot pending")
        # (7) the request branch writes the memo with the pending, from the same `bounded` as its slot flag
        four = self._sess("four", launched="login")
        self._queue_loop(four)
        four._landing_ask_bounded = True                              # a stale memo, were one ever left
        self.assertTrue(self.be.set_auth(four.sid, "key", chip=False))
        self.assertEqual((four._relaunch_bounded, four._landing_ask_bounded), (False, False), "a plain pick's pending inherits no memo")
        # (8) _follow_default's SECOND withdrawal (the mutation pass's Q8, 2026-09-19): a CLI that reports the key while romp's
        # own launch meant the login, on a box whose settings carry no apiKeyHelper (key_state "missing": a credential in
        # the CLI's own environment), has any standing ask withdrawn in one line, and the memo goes with it. The pending
        # must not be the default's own pair, or the no-new-ask guard returns first, so it is a moot key pick's
        self.be.key_state = lambda: "missing"
        five = self._sess("five", auth="key", launched="login")
        five.auth_live = "key"
        five._auth_pending, five._landing_ask_bounded = "key", True
        self._queue_loop(five)
        self.assertTrue(self.be.follow_default_auth(five.sid))
        self.assertEqual((five._auth_pending, five._relaunch_bounded, five._landing_ask_bounded), ("", False, False), "the key-report withdrawal")
        self.assertTrue(any("bills a key romp does not control" in m and "the pending key reconnect is withdrawn" in m for m in self.logs),
                        self.logs[-3:])
        self.be.key_state = lambda: "unknown"
        # THE CONSEQUENCE, on the one road that asks a landed session's pick again inside one kernel life: a key pick whose
        # own request the connect in progress served (on this box a key pick and a login pick compose the same shape) and
        # whose landing then finds it unserved asks it through _ask_parked_pick, which draws the memo. Served at (1), web's
        # memo is gone, so the ask draws no slot and the line carries no stagger clause; leaked, it drew the walk's slot for
        # a pick the user made alone
        self.assertEqual((web.auth, web._launched_auth), ("login", "login"))
        side, shape = self._composed(web)                          # a reconnect in progress composed from the login pick
        self.assertEqual((side, shape["auth"]), ("login", "login"))
        self.assertTrue(self.be.set_auth(web.sid, "key", chip=False))   # the key pick: its request is made...
        self.assertEqual(len(wq), 1)
        for cb, a in wq:                                              # ...and run by the loop: served by the connect in progress
            cb(*a)
        self.assertTrue(any("the connect in progress launches what the pending auth pick asks for" in m for m in self.logs), self.logs[-3:])
        web._host_is_attach = False
        del self.logs[:]
        web._connect_landed()                                         # the launch lands the login: the key pick is unserved, asked
        line = [m for m in self.logs if "auth (web): launched this session's new CLI" in m and "so it is asked now" in m]
        self.assertEqual(len(line), 1, self.logs)
        self.assertFalse(line[0].endswith(self.STAGGER), "no memo: a pick the user made alone draws no spawn-stagger slot")
        self.assertIs(web._relaunch_bounded, False)

    def test_the_asks_tail_and_the_served_line_are_filed_quietly_so_a_raising_log_callback_cannot_undo_a_decision(self):
        # CHARACTERISATION PIN (round 1 of the review, regression-5, narrowed by its refuter; relabelled by the round's
        # addendum after its injector lens, 2026-09-19). The refuter's narrowing said the one raise reachable after the
        # closer's decision is the kernel's log callback (a closed stderr under a service restart, _log_quietly's case). It
        # is not: the kernel wires _backend_log, which writes through _exit_log's try/except (kernel.py, since 2026-09-10),
        # so with the kernel's callback no raise reaches the guard after the decision, at 1100d3f0f as here, and the
        # routing through _log_quietly is defensive. What this pins is the routing itself, for any callback a constructor
        # passes: filed bare, the ask's tail line raised into the guard, which restored the slot flag and the memo as found
        # (a made ask, its flag spent) and filed a "step failed" row for an ask that stood; the served branch's line put a
        # served pick's pending back; and the landing road's tail (the third leg, the mutation pass's L2) raised out of
        # _connect_landed, which runs it bare on the loop thread, after the ask was made. Each leg reds under the mutation
        # that files its line bare
        web, wq = self._leased_unreported_follower("web", composed="key")
        self.assertEqual(self.be.set_auth_followers("login")["moved"], ["web"])
        web._connect_landed()
        real_cb = self.be._log_cb

        def closed_on(needle):
            def cb(m):
                if needle in str(m):
                    raise OSError(9, "Bad file descriptor")
                return real_cb(m)
            return cb
        self.be._log_cb = closed_on("so it is asked now")
        self.be._note_auth_source(web, "ANTHROPIC_API_KEY")      # the CLI bills the key, the pick is the login: asked
        self.be._log_cb = real_cb
        self.assertEqual((len(wq), web._relaunch_bounded, web._landing_ask_bounded, web._auth_pending), (1, True, False, "login"),
                         "the ask stands as made: the flag set, the memo spent")
        self.assertEqual([p["text"] for p in self.be.problems(10) if "step failed" in p["text"]], [], "no guard row for a line")
        api, aq = self._leased_unreported_follower("api", composed="login")
        self.assertTrue(self.be.set_auth(api.sid, "key"))
        api._connect_landed()
        self.be._log_cb = closed_on("the pick is served, no reconnect")
        self.be._note_auth_source(api, "ANTHROPIC_API_KEY")      # the CLI bills the key it picked: served
        self.be._log_cb = real_cb
        self.assertEqual((api._auth_pending, self._reg(api.sid)["authPending"], len(aq)), ("", False, 0), "served stays served")
        self.assertEqual([p["text"] for p in self.be.problems(10) if "step failed" in p["text"]], [])
        # the third leg, the landing road's tail: the high's report-on-record road, asked at the landing through
        # _ask_parked_pick's attach branch, which _connect_landed runs bare on the loop thread
        docs, dq = self._unkeyed_key_survivor("docs", "report", "key")
        self.assertTrue(self.be.set_auth(docs.sid, "login", chip=False))
        self.assertEqual((docs._auth_pending_target(), len(dq)), (("login", ""), 0), "parked for the landing")
        self.be._log_cb = closed_on("left to this landing, so it is asked now")
        try:
            docs._connect_landed()                                # the attach can tell: the pick is asked, its tail filed quietly
        finally:
            self.be._log_cb = real_cb
        self.assertEqual((len(dq), docs._auth_pending, docs._relaunch_bounded, self._reg(docs.sid)["authPending"]), (1, "login", False, True),
                         "the landing returned with its ask standing as made")

    def test_billing_view_names_the_stored_login_the_running_cli_launched_on(self):
        # CHARACTERISATION PIN (round 1 of the review, 2026-09-19; tests-4): `launchedLogin` and `launchedLabel` were only ever
        # exercised empty, so the one line that says WHICH stored login the running CLI launched on was untested end to end;
        # green on 1100d3f0f, red under the mutation that blanks the id
        rec = self._stored_login()
        s = self._sess("web", auth="login", launched="login")
        s.auth_login = rec["id"]
        s._launched_login = rec["id"]
        s.auth_live = "login"
        s.client = object()
        view = self.be.billing_view(s.sid)
        self.assertEqual((view["launched"], view["launchedLogin"], view["launchedLabel"]), ("login", rec["id"], "Work"))
        t = self._sess("api", auth="key", launched="key")
        t._launched_login = rec["id"]                             # a stale launch-login stamp beside a key launch: not this launch's
        t.client = object()
        view = self.be.billing_view(t.sid)
        self.assertEqual((view["launched"], view["launchedLogin"], view["launchedLabel"]), ("key", "", ""), "the key branch names no login")

    def test_record_reads_is_the_records_own_read_as_an_object(self):
        # the mutation pass (2026-09-19; its P3): every pin of the route's probe ran through the route tests' fake backend,
        # so the real predicate (`bool(read_reg(...))`) was unpinned and `return True` left the module green. The route asks
        # it on a real state directory before every `default` and `--now` drop (kernel.py's two gate-off roads), so its
        # inputs are the records that directory holds: a written record; a body that is not JSON (a torn or hand-edited
        # file: romp's own writer is atomic, so such a body comes from outside it); JSON that is not an object; and a record
        # gone since the resolver named it. read_reg's one handler takes OSError and ValueError alike, so the absent file's
        # ENOENT and an EACCES read answer the same None (no mode case here: a root runner reads a mode-000 file anyway, and
        # a pin that skips is worse than none). Red under `return True`
        s = self._sess("web")
        p = sb._reg_path(Path(self.d), s.sid)
        self.assertIs(self.be.record_reads(s.sid), True, "a written record reads as an object")
        p.write_text("{not a record")
        self.assertIs(self.be.record_reads(s.sid), False, "a body that is not JSON does not read")
        p.write_text("[]")
        self.assertIs(self.be.record_reads(s.sid), False, "JSON that is not an object does not read (read_reg's rule)")
        p.write_text(json.dumps({"sid": s.sid, "name": "web"}))
        self.assertIs(self.be.record_reads(s.sid), True, "healed, it reads again")
        self.assertIs(self.be.record_reads("11111111-2222-3333-4444-999999999999"), False, "no record at all: the absent file")

    # ---- round 2 of the billing verb's review (2026-09-20, the reviewer's 02:25Z rulings): the walk's hooks inside its
    # containment. Red on the round-2 head 676054c2f (the raise escaped set_auth_followers)

    def test_a_raising_after_write_or_park_hook_never_aborts_the_walk_and_each_follower_keeps_its_true_outcome(self):
        # CHARACTERISATION PIN at this commit (the injector census, 2026-09-20): the kernel's hooks had ONE raise road on the
        # round-2 head, the bare sys.stderr.write in _drop_parked_auth and _park_op_locked, and kernel-2's half of this fix
        # routes it through _exit_log, so with the kernel's wiring no hook raises here now; what this pins is the walk's own
        # containment against any hook a caller passes, red on the round-2 head where the road was real.
        # tests-1 with kernel-2 (both refuters): the two kernel hooks ran OUTSIDE the per-follower containment the loop states
        # two lines above them, so a raise from either (the kernel's after_write, _drop_parked_auth, had one: its bare
        # sys.stderr.write) aborted the walk mid-roster: the followers after it were never written, the summary Log line was
        # never filed, and the raise escaped POST /billing as a 500. Both hooks run inside the loop's own containment now,
        # and each follower is filed by what HAPPENED, never as `failed` (the guard's rollback bucket, which tells the user
        # the pick was not written): a follower whose after_write raised HAS the pick (its write succeeded), so it stays in
        # moved with a problem row saying its parked picks may still fire; a follower whose park hook raised has the pick
        # QUEUED already (the kernel's hook appends and mirrors before the line that raises), so it is filed under parked
        # with a row and never falls through to set_auth, which would apply the pick twice, once now and once at the drain
        web, api, tests = self._sess("web", launched="login"), self._sess("api", launched="login"), self._sess("tests", launched="login")
        for s in (web, api, tests):
            self._queue_loop(s)
        seen = []

        def after_write(sid):
            seen.append(sid)
            if sid == web.sid:
                raise OSError(9, "Bad file descriptor")
            return 1
        seq0 = self.be._problem_seq
        out = self.be.set_auth_followers("key", after_write=after_write)
        self.assertEqual((out["moved"], out["failed"], out["parked"], out["unwritten"], out["superseded"]), (["api", "tests", "web"], [], [], [], 2),
                         "the raise on the first follower's hook: the rest written and counted, nobody filed as failed")
        self.assertEqual(seen, [web.sid, api.sid, tests.sid], "the hook ran for every written follower, the raising one included")
        for s in (web, api, tests):
            self.assertEqual((s.auth, s._auth_pending, self._reg(s.sid)["auth"]), ("key", "key", "key"), s.name)
        rows = [p["text"] for p in self.be.problems(10) if p["seq"] > seq0]
        self.assertEqual(rows, ["auth (web): the pick key is written, but the hook that drops this session's parked picks failed (OSError: "
                                "[Errno 9] Bad file descriptor); a pick parked earlier for it may still fire at its next quiet moment"])
        self.assertTrue(any("3 sessions following the default now carry the pick key (api, tests, web)" in m for m in self.logs), self.logs[-1:])
        # the park hook: the raise on the first follower, the two after it written, the raiser parked and not written
        docs, notes, more = self._sess("docs", launched="login"), self._sess("notes", launched="login"), self._sess("more", launched="login")
        for s in (docs, notes, more):
            self._queue_loop(s)

        def park(sid):
            if sid == docs.sid:
                raise OSError(9, "Bad file descriptor")
            return False
        seq0 = self.be._problem_seq
        dropped = []
        out = self.be.set_auth_followers("key", park=park, after_write=lambda sid: dropped.append(sid) or 0)
        self.assertEqual((out["moved"], out["parked"], out["failed"], out["unwritten"]), (["more", "notes"], ["docs"], [], []))
        self.assertEqual((docs.auth, docs._auth_pending, docs._relaunch_bounded, docs._landing_ask_bounded), ("", "", False, False),
                         "filed as parked: nothing written or asked for it, so the queued pick is not applied twice")
        self.assertNotIn("auth", self._reg(docs.sid))
        self.assertEqual((notes.auth, more.auth, dropped), ("key", "key", [notes.sid, more.sid]))
        rows = [p["text"] for p in self.be.problems(10) if p["seq"] > seq0]
        self.assertEqual(rows, ["auth (docs): the walk's park hook failed (OSError: [Errno 9] Bad file descriptor) after the kernel queued the "
                                "pick behind this session's move, so it is filed as parked and nothing is written here, which would apply the "
                                "pick twice"])
        self.assertTrue(any("2 sessions following the default now carry the pick key (more, notes)" in m
                            and "1 parked behind a move in flight (docs), the pick applies when the move finishes" in m for m in self.logs), self.logs[-1:])


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

    def test_the_walk_whose_every_reached_follower_failed_does_not_deny_the_followers(self):
        # round 1 of the billing verb's review (2026-09-19, the 17:14Z takes; extra7-2, both refuters): with nothing moved and every reached follower's step
        # failed, the head said "no running session follows the machine default" while the tail named the two followers the
        # walk reached and could not move; the head's guard was widened for `unwritten` in round 2 and `failed` was added
        # after it. The whole line, since only the head changes
        out = self._romp("--all-following", "key", reply=(200, {"ok": True, "pick": "key", "moved": 0, "skipped": 0, "unwritten": 0,
                                                                 "failed": 2, "sessions": [], "skippedSessions": [], "unwrittenSessions": [],
                                                                 "failedSessions": ["api", "notes"], "outlooks": {}}))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "romp billing: no follower moved to the API key; 0 skipped; "
                                             "2 failed (api, notes): they keep following the default unchanged, the kernel's Log names the fault")

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
        # follow-up, 2026-09-18): "no CLI is up" was false for it, and its first report decides which side it bills (the clause
        # completed in round 1 of the billing verb's review, 2026-09-19 (the 17:14Z takes), its fresh-3: it ended mid-sentence, and this pin held it so)
        view.update(live="", cannotTell=True)
        self.assertEqual(self._romp("web", reply=(200, view)).stdout.splitlines()[0],
                         "launched: a surviving CLI is attached that has not reported which side it bills; its first report decides which side it bills")

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


    def test_the_walk_says_the_followers_parked_behind_a_move(self):
        # round 1 of the review (tests-1's move half): a follower whose queue a move holds is parked behind the move by the
        # kernel and filed apart; the verb says so in the plain road's words (parkedReconnect, kernel.py's
        # _BILLING_PARK_WORDS["move"]), and a walk that parked its only follower does not deny that any follows
        reply = {"ok": True, "pick": "key", "moved": 1, "skipped": 0, "unwritten": 0, "failed": 0, "parked": 1, "skippedSessions": [],
                 "unwrittenSessions": [], "failedSessions": [], "parkedSessions": ["docs"], "parkedReconnect": "after the move finishes",
                 "sessions": ["web"], "outlooks": {"web": "now"}}
        out = self._romp("--all-following", "key", reply=(200, reply))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(),
                         "romp billing: 1 session following the default now carries its own pick, the API key (web); "
                         "it reconnects at its next quiet moment; 0 skipped; "
                         "1 parked (docs): it is mid-move, so the pick applies after the move finishes")
        reply.update(sessions=[], moved=0, outlooks={}, parkedSessions=["api", "docs"], parked=2)
        out = self._romp("--all-following", "key", reply=(200, reply))
        self.assertEqual(out.stdout.strip(),
                         "romp billing: no follower moved to the API key; 0 skipped; "
                         "2 parked (api, docs): they are mid-move, so the pick applies after the move finishes")
        # CHARACTERISATION PIN (the mutation pass's V3, 2026-09-19): the printer's own word when the answer carries
        # parkedSessions and no parkedReconnect. No kernel at this head answers that shape (the two keys were added together),
        # so this pins the literal's agreement with the kernel's word, not a road; red under the mutation that changes it
        del reply["parkedReconnect"]
        out = self._romp("--all-following", "key", reply=(200, reply))
        self.assertEqual(out.stdout.strip(),
                         "romp billing: no follower moved to the API key; 0 skipped; "
                         "2 parked (api, docs): they are mid-move, so the pick applies %s" % km._BILLING_PARK_WORDS["move"])

    def test_the_read_names_the_stored_login_the_cli_launched_on(self):
        # CHARACTERISATION PIN (round 1 of the review, 2026-09-19; tests-4): the launched line with a stored login's id, with
        # the kernel's label and without one (a record deleted since the launch: the id stands in). Green on 1100d3f0f
        view = {"ok": True, "session": "web", "launched": "login", "launchedLogin": LID, "launchedLabel": "Work", "live": "login",
                "pick": {"auth": "login", "login": LID, "label": "Work", "explicit": True}, "pending": False, "held": False,
                "default": {"auth": "key", "login": "", "explicit": False, "label": ""}}
        out = self._romp("web", reply=(200, view))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.splitlines()[0], 'launched: login "Work"; the CLI reports: login')
        view["launchedLabel"] = ""
        self.assertEqual(self._romp("web", reply=(200, view)).stdout.splitlines()[0], 'launched: login "%s"; the CLI reports: login' % LID)

    def test_the_help_and_the_reference_say_default_never_queues_behind_a_compaction(self):
        # round 1 of the review (correctness-4): the verb's --help and docs/reference.md told the user to re-run without --now
        # "to queue the pick behind the compaction", which `default` never does (it applies at once and the session
        # reconnects when the compaction ends); the refusal sentence is pinned on the route (PerSessionPick)
        out = self._romp("--help")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("(default never queues: during a compaction it applies at once and the session reconnects when the compaction "
                      "ends; during a move it is refused)", " ".join(l.strip() for l in out.stdout.splitlines()))
        doc = " ".join(Path(os.path.dirname(HERE), "docs", "reference.md").read_text().split())   # the section is hard-wrapped
        self.assertEqual(doc.count("`default` never queues: during a compaction it applies at once and the session reconnects when the "
                                   "compaction ends"), 2, "the command table's row and the per-session billing section")
        self.assertNotIn("(`default` never queues, so it is refused during a move too)", doc)


class RouteServerLeavesTheSharedRegistryClean(unittest.TestCase):
    """_register writes the placeholder sid's names line and SDK reg into the state root of the SHARED judge module
    (kernel.py loads judge.py under the one name romp_judge, so every test module's kernel in a process reads the same
    SDKDIR, whatever name the kernel itself was loaded under). A reg a _RouteServer class left behind made
    tests/test_kernel.py's ViewBuilder lane read 'sdk' for a names-only session whenever one of these classes had run on
    the same xdist worker first (a full-suite sweep, 2026-09-19). The fixture takes back exactly what it wrote."""

    def test_the_fixture_takes_back_what_it_registered(self):
        class _Probe(_RouteServer):
            pass
        reg, line = km.jd.STATE / "sdk" / (SID + ".json"), km.NAMES / SID
        _Probe.setUpClass()
        try:
            self.assertTrue(reg.exists(), "the fixture registers the session while the class runs")
            self.assertTrue(line.exists())
        finally:
            _Probe.tearDownClass()
        self.assertFalse(reg.exists(), "a reg left in the shared registry reads as an SDK-owned session to every other "
                                       "module's kernel")
        self.assertFalse(line.exists())
        with mock.patch.object(km, "_sdk", lambda: None), mock.patch.object(km, "_codex", lambda: None):
            self.assertEqual(km._session_backend(SID, {"state": "idle"}), "",
                             "a names-only session reads '' once the class is done, the label ViewBuilder pins on the lane")


class OneAskPerInit(unittest.TestCase):
    """THE CONVERGENCE GATE (romp-manager, 2026-09-19: round 6 of the auth-default fix, fork PR #787, and round 1 of this
    PR). Three mechanisms once decided a picked session's pending across a cannot-tell attach: fork PR #787's closer with its
    ask leg (_recover_picked_pending_at_init), this PR's landing roads (_connect_landed's picked branch through
    _ask_parked_pick's attach and launch branches) and the never-landed park's later init; the rebase folded them into one
    closer and one ask. That they never double, and never all stand down, is shown BY EXECUTION here, not by reading:
    every interleaving of the cannot-tell attach is enumerated as the product of the variables below, each state is
    driven through the real compose (_decide_auth, then _stamp_compose: the stamps _options writes, so the unkeyed-pick
    flag is the compose's own and never hand-set), the real landing and the real init, each handler's requests run when
    it has returned (_Loop, the loop's order), and the asks are counted per phase: the auth ask (request_reconnect with pick "auth", the one form every writer of a billing ask takes: set_auth,
    _ask_parked_pick, _follow_default and _follow_default_unlanded), the bare request the wrong-landing branch makes,
    and the ARMS (a transition of _reconnect from False to True, one relaunch each).

    The variables, each an independent fact of the session's state or of the CLI's word:
      * existing: the session's own pick when the kernel restarted ("" a follower; "login" the machine's own; "loginA" a
        stored login, which its CLI's launch carried; "key");
      * gesture: the pick made in the window ("login", "loginA", "key", or "default", the verb's clear);
      * box: "keyed" (an apiKeyHelper is configured, key_state ok) or "unkeyed" (Claude Code's settings cannot be read,
        key_state unknown: the compose flags an explicit key pick as unkeyed, the high's class);
      * timing: the gesture "before" the compose (the object built, the loop up, no connect composed: the window closed)
        or "after" it (the boot re-attach composed and not landed: the window open);
      * cls: what the object has when the connect lands: "lease" (a live host lease, no report on record: the cannot-tell
        attach), "report" (the CLI's report restored from the reg: an attach that can tell), "launch" (neither: the connect
        is a launch, the report retired at the handshake);
      * arm: another pick's reconnect standing at the init: "none"; "immediate" (a reconnect armed, fork PR #787's fixture for a
        relaunch already scheduled); "deferred" (an effort pick behind an open turn); "held" (an effort pick held for a
        background task);
      * report: what the CLI's first init says: "none" (the login: the machine's own, or the stored login the launch
        carried) or "key".
    Two facts are DERIVED, not varied, because varying them alone would build states the compose cannot produce: the
    unkeyed-pick flag (the compose's, from existing and box) and the stored login a login report names (the launch the
    CLI came from). No combination is pruned: each is reachable by construction (a wrong landing is the CLI's word, a
    stored login's refusal its record's).

    The gate: in every state the init asks at most once and at most one relaunch is armed over the whole sequence; for an
    explicit pick the sequence never ends WRONG-SILENT (the pending gone, nothing asked or armed, the CLI billing another
    account than the pick, and no problem row), except the residual named below, which is pinned as a set so it cannot
    grow unnoticed. Two request calls do occur, and are counted as such: a pick's own request the connect in progress
    served and the landing's re-ask, both withdrawn by the served check with no arm (a key pick on the unkeyed box, which
    composes as the login), and the follower road's re-ask at a launch landing (787's design: "asked again", the same
    arm). ROMP_ASK_TABLE=<path> writes one line per state, the record the review reads."""

    EXISTING = ("", "login", "loginA", "key")
    GESTURE = ("login", "loginA", "key", "default")
    BOX = ("keyed", "unkeyed")
    TIMING = ("before", "after")
    CLS = ("lease", "report", "launch")
    ARM = ("none", "immediate", "deferred", "held")
    REPORT = ("none", "key")
    # THE RESIDUAL, pre-existing at fork PR #787's head 934aa3cbf (the same enumeration there: 12 states, these four among them),
    # named in that PR's body as the unapplied-pick family and queued: a login pick made inside the window of a LAUNCH
    # composed for an explicit key pick this box cannot bill as the key (the compose's shape names the login for both
    # picks, so the already-applying branch rides the connect), the launch goes plain with the helper unsuppressed, the
    # CLI bills the key, the landing serves the login pending on the shape word, and the per-init check is silenced by the
    # compose's unkeyed-pick flag. Not this PR's to fix (its guard is the attach road's), pinned so the set cannot grow
    RESIDUAL = frozenset(("key", "login", "unkeyed", "after", "launch", arm, "key") for arm in ARM)

    class _Loop:
        """A loop double that QUEUES (tests/test_sdk_backend.py's _Queue idiom): request_reconnect's call_soon_threadsafe
        records the callback, and _drive runs the queue when the handler that scheduled it has returned, which is the
        loop's order: request_reconnect reaches _do_request_reconnect only through _call_on_loop's call_soon_threadsafe,
        never inline (BackendHelpers.test_request_reconnect_runs_on_the_loop_after_its_caller_returns_never_inline pins
        it against a real loop). Until the owner's second pass over round 1's takes (2026-09-19) this double ran each callback at once,
        inside the handler, where the loop never runs one: the wrong-landing branch's bare request then armed before the
        closer, a few lines later in the same init handler, read the flags, and the closer read armed where the loop has
        it ask (one init ask and one arm, the ask's request withdrawn by the served check as the fall's relaunch); the
        states that moved are named in the PR body's convergence paragraph."""
        def __init__(self):
            self.queued = []

        def call_soon_threadsafe(self, cb, *a):
            self.queued.append((cb, a))

        def flush(self):
            while self.queued:
                cb, a = self.queued.pop(0)
                cb(*a)

    NOFALL = "nofall"   # a box with NOTHING to fall to: no helper readable (key_state unknown) and no machine login the fall can read

    def _backend(self, box):
        d = tempfile.mkdtemp()
        Path(d, "session-hosts").write_text("off")
        logs = []
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=logs.append)
        be.login_ok = lambda: True
        be.key_state = (lambda: "ok") if box == "keyed" else (lambda: "unknown")
        if box == self.NOFALL:
            be._helper_source_read = lambda: (None, False)   # the read a refused stored login's fall asks (pick_fall): nothing to fall to
        leased = set()
        be._host_lease_live = lambda sess: sess.sid in leased
        return be, logs, leased

    def _drive(self, be, logs, leased, n, existing, gesture, box, timing, cls, arm, report):
        rec = {"id": sb._logins.mint_id(), "label": "Work%d" % n, "tokenCmd": "token-read 'romp login Work%d'" % n,
               "addedAt": int(time.time()) - 86400}
        sb._logins.write_record(be.state_dir, rec)               # a fresh stored login per state: a wrong landing marks it refused
        A = rec["id"]
        sid = "11111111-2222-3333-4444-%012d" % n
        reg = {"sid": sid, "name": "s%d" % n, "cwd": str(be.state_dir), "alive": True, "lastSid": sid}
        if existing == "key":
            reg["auth"] = "key"
        elif existing == "login":
            reg["auth"] = "login"
        elif existing == "loginA":
            reg.update(auth="login", authLogin=A, launchedLogin=A)
        if cls == "report":
            reg["apiKeyAuth"] = report == "key"
            if report == "none" and existing == "loginA":
                reg["authLoginLive"] = A
        sb.write_reg(Path(be.state_dir), sid, reg)
        s = sb.SdkSession(be, dict(reg))
        s._launched_auth = None
        s.inflight = 0
        loop = s.loop = self._Loop()
        be.sessions[sid] = s
        if cls == "lease":
            leased.add(sid)
        asks = {"pick": 0, "landing": 0, "init": 0}
        bare = {"pick": 0, "landing": 0, "init": 0}
        arms = {"pick": 0, "landing": 0, "init": 0}
        phase = ["pick"]
        real_rr, real_arm = s.request_reconnect, s._arm_reconnect

        def rr(*a, **k):
            (asks if k.get("pick") == "auth" else bare)[phase[0]] += 1
            return real_rr(*a, **k)

        def arm_wrap(*a, **k):
            was = s._reconnect
            out = real_arm(*a, **k)
            if not was and s._reconnect:
                arms[phase[0]] += 1
            return out
        s.request_reconnect, s._arm_reconnect = rr, arm_wrap
        value = {"login": "login", "loginA": "login:" + A, "key": "key"}.get(gesture)

        def gesture_now():
            if gesture == "default":
                be.follow_default_auth(sid)
            else:
                be.set_auth(sid, value, chip=False)
            loop.flush()                                         # the kernel thread's pick: its request runs on the loop next
        if timing == "before":
            gesture_now()
        fell, side, lid = be._decide_auth(s)
        be._stamp_compose(s, side, lid)                         # the real compose's stamps: the flag is derived here
        s._host_is_attach = cls != "launch"
        flag = bool(s._launched_unkeyed_pick)
        if arm == "immediate":
            s._reconnect = True
        elif arm == "deferred":
            s.inflight = 1
            be.set_effort(sid, "max" if s.effort != "max" else "high")
        elif arm == "held":
            s._on_task_event("task_started", {"task_id": "t-%d" % n, "task_type": "local_bash", "description": "a sweep"})
            be.set_effort(sid, "max" if s.effort != "max" else "high")
        loop.flush()                                             # the other pick's request, served before the landing
        if timing == "after":
            gesture_now()
        phase[0] = "landing"
        if cls == "launch":
            be._stamp_launch_login(s)                            # the handshake's stamp on the launch road
        s._connect_landed()
        loop.flush()                                             # the landing's requests run when its callback has returned
        phase[0] = "init"
        seq0 = be._problem_seq
        be._note_auth_source(s, "apiKeyHelper" if report == "key" else "none")
        loop.flush()                                             # the init's requests: the branch's bare one, the closer's ask
        rows = [p["text"] for p in be._problems if p["seq"] > seq0 and ("(%s)" % s.name) in p["text"]]
        with s._hold_lock:
            armed = bool(s._reconnect or (s._reconnect_when_idle and "auth" in s._reconnect_surfaces) or "auth" in s._pending_names())
        total = sum(asks.values())
        want = None if gesture == "default" else sb._logins.parse_pick(value)
        launched_login = getattr(s, "_launched_login", "") or ""
        bills = ("key" if report == "key" else "login", A if (report == "none" and launched_login == A) else "")
        pending = s._auth_pending_target() if s._auth_pending else None
        if want is None:
            outcome = "follower"
        elif total or armed:
            outcome = "asked" if total else "armed"
        elif pending:
            outcome = "standing-no-arm"
        elif bills == want:
            outcome = "served"
        elif rows:
            outcome = "wrong-with-row"
        else:
            outcome = "WRONG-SILENT"
        return {"asks": asks, "bare": bare, "arms": arms, "total": total, "armed": armed, "pending": pending, "flag": flag,
                "launched": s._launched_auth, "bills": bills, "rows": len(rows), "rowtexts": rows, "outcome": outcome}

    def test_exactly_one_ask_per_init_over_every_interleaving_of_the_cannot_tell_attach(self):
        import itertools
        bes = {box: self._backend(box) for box in self.BOX}
        lines, silent, n = [], set(), 0
        init_hist, arm_hist = {}, {}
        for state in itertools.product(self.EXISTING, self.GESTURE, self.BOX, self.TIMING, self.CLS, self.ARM, self.REPORT):
            existing, gesture, box, timing, cls, arm, report = state
            n += 1
            be, logs, leased = bes[box]
            r = self._drive(be, logs, leased, n, *state)
            a, ar = r["asks"], sum(r["arms"].values())
            key = "%s/%s/%s/%s/%s/%s/%s" % (existing or "follower", gesture, box, timing, cls, arm, report)
            lines.append("%-56s flag=%d asks pick=%d landing=%d init=%d bare-init=%d total=%d arms=%d armed=%d pending=%s launched=%s "
                         "bills=%s rows=%d %s" % (key, r["flag"], a["pick"], a["landing"], a["init"], r["bare"]["init"], r["total"],
                                                  ar, r["armed"], r["pending"], r["launched"], r["bills"], r["rows"], r["outcome"]))
            init_hist[a["init"]] = init_hist.get(a["init"], 0) + 1
            arm_hist[ar] = arm_hist.get(ar, 0) + 1
            with self.subTest(state=key):
                self.assertLessEqual(a["init"], 1, "the init asked twice: %s" % lines[-1])
                self.assertLessEqual(ar, 1, "two relaunches armed: %s" % lines[-1])
                if gesture != "default":
                    self.assertLessEqual(r["total"], 2, lines[-1])
                    if r["total"] == 2:
                        self.assertEqual(ar, 0, "two requests are two only when both were served with no arm: %s" % lines[-1])
                if r["outcome"] == "WRONG-SILENT":
                    silent.add(state)
        table = os.environ.get("ROMP_ASK_TABLE")
        if table:
            Path(table).write_text("\n".join(lines) + "\nINIT-ASKS %r\nARMS %r\n" % (sorted(init_hist.items()), sorted(arm_hist.items())))
        self.assertEqual(n, 1536, "the product: 4 existing x 4 gestures x 2 boxes x 2 timings x 3 classes x 4 arms x 2 reports")
        self.assertEqual(silent, set(self.RESIDUAL),
                         "the wrong-silent set is exactly the pre-existing residual: %r" % sorted(silent ^ set(self.RESIDUAL)))
        self.assertEqual(max(init_hist), 1)
        self.assertEqual(max(arm_hist), 1)

    def test_on_a_box_with_nothing_to_fall_to_the_init_closes_a_pick_whose_relaunch_would_land_wrong_again_with_a_row(self):
        # round 1 of fork PR #813's review (2026-09-19, the 17:14Z takes; its extra5-1, in both refuters' narrowed form). The closer's gate on what
        # the relaunch would compose never fires in the product above: that harness box always has a fall (login_ok True, the
        # operator's settings readable), so a wrong landing's branch REQUESTS the relaunch onto the fall (bare-init=1 in every
        # loginA/*/key state of its table) and the relaunch composes the fall, never the refused pair. The gate's own box is
        # this one, with nothing to fall to: that branch DECLINES a relaunch, and the closer's ask, reading the reconnect flags
        # alone, re-armed the very relaunch it declined, composing the refused login again (a false served at its landing on a
        # session billing the wrong account, the CLI and its work torn down for nothing). The stored-login states are driven
        # on this box through the same real compose, landing and init: the init still asks at most once and at most one
        # relaunch is armed; every state whose relaunch would compose the refused pair (the pick is the refused login, the
        # attach could not tell, the report a key word: 8 states) ends with the pending CLOSED, nothing asked at the init, no
        # bare request (the branch declined) and the row that says the pick cannot be applied on this box, whatever other
        # arm stands; no state ends wrong-silent. ROMP_ASK_TABLE=<path> writes this leg's lines to <path>.nofall
        import itertools
        be, logs, leased = self._backend(self.NOFALL)
        lines, closed, silent, n = [], set(), set(), 5000
        init_hist = {}
        for state in itertools.product(("loginA",), self.GESTURE, (self.NOFALL,), self.TIMING, self.CLS, self.ARM, self.REPORT):
            existing, gesture, box, timing, cls, arm, report = state
            n += 1
            r = self._drive(be, logs, leased, n, *state)
            a, ar = r["asks"], sum(r["arms"].values())
            key = "%s/%s/%s/%s/%s/%s/%s" % (existing, gesture, box, timing, cls, arm, report)
            lines.append("%-56s flag=%d asks pick=%d landing=%d init=%d bare-init=%d total=%d arms=%d armed=%d pending=%s launched=%s "
                         "bills=%s rows=%d %s" % (key, r["flag"], a["pick"], a["landing"], a["init"], r["bare"]["init"], r["total"],
                                                  ar, r["armed"], r["pending"], r["launched"], r["bills"], r["rows"], r["outcome"]))
            init_hist[a["init"]] = init_hist.get(a["init"], 0) + 1
            same_pair = gesture == "loginA" and cls == "lease" and report == "key"
            with self.subTest(state=key):
                self.assertLessEqual(a["init"], 1, "the init asked twice: %s" % lines[-1])
                self.assertLessEqual(ar, 1, "two relaunches armed: %s" % lines[-1])
                if same_pair:
                    self.assertEqual((a["init"], r["bare"]["init"], r["pending"]), (0, 0, None),
                                     "the relaunch would compose the refused pair: closed, not asked, and the wrong-landing branch declined: %s"
                                     % lines[-1])
                    self.assertTrue(any("so the pick cannot be applied on this box" in t for t in r["rowtexts"]), r["rowtexts"])
                    closed.add(state)
                if r["outcome"] == "WRONG-SILENT":
                    silent.add(state)
        table = os.environ.get("ROMP_ASK_TABLE")
        if table:
            Path(table + ".nofall").write_text("\n".join(lines) + "\nINIT-ASKS %r\n" % sorted(init_hist.items()))
        self.assertEqual(n - 5000, 192, "the product: 4 gestures x 2 timings x 3 classes x 4 arms x 2 reports on the one box")
        self.assertEqual(len(closed), 8)
        self.assertEqual(silent, set(), "no state ends wrong-silent on this box: %r" % sorted(silent))


if __name__ == "__main__":
    unittest.main()
