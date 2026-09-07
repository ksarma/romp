#!/usr/bin/env python3
"""A `closed` frame is broadcast ONLY when a session actually ended (2026-08-18).

Every chat client obeys `closed` with a full dismissSession — no suppression, no undo (render.ts).
So a `closed` for a session the kernel KEEPS LISTING is a lie with a permanent cost: the next push
re-lists the id, the client re-draws it with no session behind it, and the tab is the dead swirling
placeholder until a browser reload. The emitters that could lie:

  - closeTab: deliberately declines to kill a live sid (a stale client's hide ask) yet broadcast
    `closed` anyway — and the ✕'s End-session confirm posts endSession+closeTab TOGETHER, so this
    companion post raced every slow or failed kill on every other connected window.
  - endSession (the WS drive op) and the /end route: TmuxBackend.kill is fire-and-forget (a
    kill-session timeout is swallowed and kill() returns True regardless), so a failed kill still
    broadcast `closed` and recorded a death that had not happened.
  - cancelCreate's teardown (_end_pending_sid): a kill THROW was caught and logged — and then
    `closed` was broadcast anyway (covered in test_kernel_cancel_create.py).

The rule: corroborate with the liveness owner AFTER the kill; a session still listed gets a warn
(endSession) or a silent refusal (closeTab — endSession owns the warn, a double toast helps nobody),
never a dismissal. Death records and comment-thread teardown ride the corroborated branch only.

…and the corroboration itself must not inherit the collapse it distrusts (2026-08-18, round two):
`sid in _tmux_sessions()` reads through list_lines, whose exec error/timeout→[] collapse made every
live sid read dead-confirmed during a tmux stall — the exact moment the fire-and-forget kill also
fails, so the gates certified a FALSE death (durable gone marker, live comment threads killed, the
dishonest closed broadcast) precisely when they mattered. All four gates now ask _confirmed_ended:
death is certified only by an AFFIRMATIVE answer (still-listed → refuse; SDK reg partition; headless
zero; alive_sids answering without the sid) — a probe failure (alive_sids None) STANDS DOWN into the
warn/ok:false branch, while an authoritative zero (set()) still proves the death.

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
    """A backend whose kill visibly lands (removes the sid from the shared live map) — or doesn't,
    when the test breaks it, mirroring tmux's silent fire-and-forget failure mode."""

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
        patch("_push_all", lambda tmux=None: None)
        patch("_tmux_sessions", lambda: self.live)
        patch("_record_death", lambda sid, t, kind: self.deaths.append((sid, kind)))
        patch("_comment_kill_all", lambda sid, be: self.comment_kills.append(sid))
        patch("_kernel_knows", lambda sid: True)
        patch("_name_of", lambda sid: "web")
        self._saved_bf = km.Sessions.backend_for
        km.Sessions.backend_for = staticmethod(lambda sid: self.be)
        # The corroboration's second leg (_confirmed_ended): the probe mirrors the shared live map by
        # default, so a kill that lands reads as the authoritative zero and a survivor stays listed.
        # Stall tests override alive_sids/available per-case. Instance attrs shadow the class methods;
        # tearDown deletes them so the real TmuxBackend is untouched for other suites.
        km._TMUX.available = lambda: True
        km._TMUX.alive_sids = lambda t=3: set(self.live)
        self.client = {"send": lambda s: self.client_frames.append(json.loads(s))}

    def tearDown(self):
        for nm, v in self._saved.items():
            setattr(km, nm, v)
        km.Sessions.backend_for = self._saved_bf
        for nm in ("available", "alive_sids"):
            km._TMUX.__dict__.pop(nm, None)

    def closed_broadcasts(self):
        return [m for _a, m in self.sent if m.get("type") == "closed"]

    def client_warns(self):
        return [f for f in self.client_frames if f.get("type") == "warn"]

    def client_end_faileds(self):
        # endSession's refusal is TYPED and sid-bearing (2026-08-18) so the closer can release its
        # own close-suppression and restore the tab the user is told to retry on (render.ts)
        return [f for f in self.client_frames if f.get("type") == "endFailed"]


class EndSessionCorroborates(ClosedHonestyBase):
    def test_a_kill_that_lands_broadcasts_closed_and_records_the_death(self):
        self.live[SID] = {}
        km._drive({"type": "endSession", "id": SID}, self.client)
        self.assertEqual(self.be.killed, [SID])
        self.assertEqual([m.get("id") for m in self.closed_broadcasts()], [SID],
                         "the session genuinely ended → every client is told to prune it")
        self.assertEqual(self.deaths, [(SID, "kill")])
        self.assertEqual(self.comment_kills, [SID])
        self.assertEqual(self.client_warns(), [], "an ordinary end says nothing extra")

    def test_a_kill_that_silently_fails_sends_end_failed_and_does_not_dismiss(self):
        # tmux's kill_by_name is _fire (best-effort): a timeout is swallowed and kill() returns True
        # while the session keeps running and keeps being LISTED — the exact closed-lie seam.
        self.live[SID] = {}
        self.be.kill = lambda sid: self.be.killed.append(sid)     # runs, but the session survives
        km._drive({"type": "endSession", "id": SID}, self.client)
        self.assertEqual(self.closed_broadcasts(), [],
                         "still live-and-listed: a closed broadcast would dismiss it on every client "
                         "while the next push re-lists it — the permanent dead-swirl seam")
        fails = self.client_end_faileds()
        self.assertEqual(len(fails), 1, "the honest signal is the typed failure, not a dismissal")
        self.assertEqual(fails[0].get("id"), SID,
                         "sid-bearing, so the closer releases its own close-suppression — the bare "
                         "warn left the tab hidden for 15s and bought a second backstop toast")
        self.assertIn("still running", fails[0]["text"])
        self.assertEqual(self.deaths, [], "no death record for a session that did not die")
        self.assertEqual(self.comment_kills, [], "its comment threads are still that live session's")

    def test_a_dead_sessions_end_still_prunes(self):
        # endSession for an already-dead sid (a dead read-only tab): kill no-ops on the backend, the
        # corroboration reads it dead, and the prune broadcast goes out exactly as before.
        km._drive({"type": "endSession", "id": SID}, self.client)
        self.assertEqual([m.get("id") for m in self.closed_broadcasts()], [SID])
        self.assertEqual(self.client_warns() + self.client_end_faileds(), [])


class CloseTabRefusalIsHonest(ClosedHonestyBase):
    def _close_tab(self, sid):
        km.Handler._dispatch_ws(types.SimpleNamespace(), {"type": "closeTab", "id": sid}, self.client)

    def test_a_live_sid_gets_no_closed_broadcast(self):
        # The refusal already existed ("a stale client's hide ask for a live sid is ignored") — but it
        # still broadcast `closed`, dismissing the live session on EVERY chat client with no suppression
        # anywhere (closingTabs only guards the closer). Refuse honestly: nothing closed, say nothing.
        self.live[SID] = {}
        km._kept_open.add(SID)
        try:
            self._close_tab(SID)
            self.assertEqual(self.closed_broadcasts(), [],
                             "no closed broadcast when nothing closed")
            self.assertNotIn(SID, km._kept_open, "the read-only-keep bookkeeping still clears")
            self.assertEqual(self.client_warns(), [],
                             "no warn either — the ✕'s companion endSession owns the kill-fail warn, "
                             "and a stale hide ask self-reports through the client's own ack backstop")
        finally:
            km._kept_open.discard(SID)

    def test_a_dead_sid_still_broadcasts_closed(self):
        # the handler's real job: closing a DEAD read-only tab — the prune must keep working, and it
        # also covers the everyday ✕ flow (endSession killed the sid, so by this companion post the
        # liveness owner already reads it dead → the fast-path prune goes out as before)
        km._kept_open.add(SID)
        try:
            self._close_tab(SID)
            self.assertEqual([m.get("id") for m in self.closed_broadcasts()], [SID],
                             "a genuinely-ended session's tab prunes everywhere, fast")
            self.assertNotIn(SID, km._kept_open)
        finally:
            km._kept_open.discard(SID)


class CorroborationNeverInheritsTheCollapse(ClosedHonestyBase):
    """The correlated failure the gates exist for: a wedged tmux server swallows the fire-and-forget
    kill AND times out the corroborating merged read in one gesture, so _tmux_sessions() collapses to
    {} while the session keeps running. Every fixture here holds that shape — live map empty, kill
    recorded but never landing — and varies only the alive_sids probe: None (a real probe failure)
    must STAND DOWN into the warn/refusal branch with no death record, no comment-thread teardown and
    no closed broadcast, for all four writers; set() (the authoritative zero) must still certify the
    death, so the dead-tab prune keeps working."""

    def setUp(self):
        super().setUp()
        self.be.kill = lambda sid: self.be.killed.append(sid)   # fires, but the session survives
        km._TMUX.alive_sids = lambda t=3: None                  # …and the probe fails with it

    def _end_session(self):
        import contextlib
        with contextlib.redirect_stderr(io.StringIO()) as err:
            km._drive({"type": "endSession", "id": SID}, self.client)
        return err.getvalue()

    def test_end_session_stands_down_on_a_probe_failure(self):
        err = self._end_session()
        self.assertEqual(self.closed_broadcasts(), [],
                         "silence is not a death: a collapsed read + failed probe must never dismiss "
                         "a session that may still be running on every client")
        self.assertEqual(self.deaths, [], "no durable false death record")
        self.assertEqual(self.comment_kills, [], "its comment threads stay untouched — they may be live")
        fails = self.client_end_faileds()
        self.assertEqual(len(fails), 1, "the asker is told, loudly")
        self.assertEqual(fails[0].get("id"), SID)
        self.assertIn("Couldn't confirm", fails[0]["text"],
                      "…with the honest ambiguity: unconfirmable, not definitely-running")
        self.assertIn("kill-corroborate", err, "…and the stand-down is logged (the fail-loudly rule)")

    def test_end_session_stands_down_when_the_probe_answers_alive(self):
        km._TMUX.alive_sids = lambda t=3: {SID}                 # the probe SEES the survivor
        self._end_session()
        self.assertEqual(self.closed_broadcasts(), [])
        self.assertEqual(self.deaths, [])
        fails = self.client_end_faileds()
        self.assertEqual(len(fails), 1)
        self.assertIn("still running", fails[0]["text"],
                      "an answering probe is definite: the copy says so")

    def test_end_session_still_certifies_death_on_the_authoritative_zero(self):
        km._TMUX.alive_sids = lambda t=3: set()                 # list-sessions answered: nothing alive
        self._end_session()
        self.assertEqual([m.get("id") for m in self.closed_broadcasts()], [SID],
                         "an ANSWERING probe without the sid is a real death — the prune must not stall")
        self.assertEqual(self.deaths, [(SID, "kill")])
        self.assertEqual(self.comment_kills, [SID])
        self.assertEqual(self.client_warns() + self.client_end_faileds(), [])

    def test_end_session_headless_box_still_certifies_the_sdk_death(self):
        # no tmux on the host: alive_sids returns None BOTH on probe failure and absence, so without
        # the available() gate an SDK session's end would report "still running" forever
        km._TMUX.available = lambda: False
        self._end_session()
        self.assertEqual([m.get("id") for m in self.closed_broadcasts()], [SID])
        self.assertEqual(self.deaths, [(SID, "kill")])
        self.assertEqual(self.client_warns() + self.client_end_faileds(), [])

    def test_close_tab_refuses_the_broadcast_on_a_probe_failure(self):
        import contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            km.Handler._dispatch_ws(types.SimpleNamespace(), {"type": "closeTab", "id": SID}, self.client)
        self.assertEqual(self.closed_broadcasts(), [],
                         "the ✕'s companion post lands mid-stall on every failed kill — a closed here "
                         "would dismiss the live session on every non-closer window")

    def test_close_tab_still_broadcasts_on_the_authoritative_zero(self):
        km._TMUX.alive_sids = lambda t=3: set()
        km.Handler._dispatch_ws(types.SimpleNamespace(), {"type": "closeTab", "id": SID}, self.client)
        self.assertEqual([m.get("id") for m in self.closed_broadcasts()], [SID])


class FakePost:
    """Just enough of the HTTP handler for do_POST's /end branch: path + body in, (code, json) out.
    _authorize is stubbed open — the gate under test is the kill corroboration, not auth."""

    def __init__(self, path, body=b"{}"):
        self.path = path
        self.headers = {"Content-Length": str(len(body))}
        self.rfile = io.BytesIO(body)
        self.client_address = ("127.0.0.1", 0)
        self.responses = []

    def _origin_ok(self):
        return False

    def _authorize(self, q):
        return True, None, ""

    def _send(self, code, body, ctype="text/plain"):
        self.responses.append((code, json.loads(body)))


class EndRouteCorroborates(ClosedHonestyBase):
    """POST /end mirrors the WS twin: ok:true + death record only on a corroborated end; a survivor
    or an unconfirmable one answers ok:false with no death record and no closed broadcast."""

    def _post_end(self):
        import contextlib
        fake = FakePost("/end", json.dumps({"id": SID}).encode())
        with contextlib.redirect_stderr(io.StringIO()):
            km.Handler.do_POST(fake)
        self.assertEqual(len(fake.responses), 1)
        return fake.responses[0]

    def test_a_corroborated_end_answers_ok_true(self):
        self.live[SID] = {}                                     # alive until the kill lands
        code, resp = self._post_end()
        self.assertEqual((code, resp), (200, {"ok": True}))
        self.assertEqual(self.deaths, [(SID, "kill")])
        self.assertEqual([m.get("id") for m in self.closed_broadcasts()], [SID])

    def test_a_surviving_session_answers_ok_false(self):
        self.live[SID] = {}
        self.be.kill = lambda sid: self.be.killed.append(sid)   # fires, never lands — still listed
        code, resp = self._post_end()
        self.assertEqual(code, 200)
        self.assertFalse(resp["ok"])
        self.assertIn("still running", resp["error"])
        self.assertEqual(self.deaths, [])
        self.assertEqual(self.closed_broadcasts(), [])

    def test_a_probe_failure_answers_ok_false_and_stands_down(self):
        # the collapse: merged read {} (self.live stays empty), probe None, kill never landing
        self.be.kill = lambda sid: self.be.killed.append(sid)
        km._TMUX.alive_sids = lambda t=3: None
        code, resp = self._post_end()
        self.assertEqual(code, 200)
        self.assertFalse(resp["ok"], "a headless caller told ok:true would abandon a runaway session")
        self.assertIn("couldn't confirm", resp["error"])
        self.assertEqual(self.deaths, [])
        self.assertEqual(self.closed_broadcasts(), [])

    def test_the_authoritative_zero_still_answers_ok_true(self):
        self.be.kill = lambda sid: self.be.killed.append(sid)
        km._TMUX.alive_sids = lambda t=3: set()
        code, resp = self._post_end()
        self.assertEqual((code, resp), (200, {"ok": True}))
        self.assertEqual(self.deaths, [(SID, "kill")])


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
        self._saved["_remote_forward"] = km._remote_forward
        km._remote_forward = lambda r, path, body: (self.forwarded.append((path, body)) or refusal)
        code, resp = self._post_end()
        self.assertEqual((code, resp), (200, refusal),
                         "the owning kernel said the kill didn't take — the caller must hear it")
        self.assertEqual(self.forwarded, [("/end", {"id": SID})])
        self.assertEqual(self.deaths, [], "the remote owns the death record, never the relay")

    def test_a_remote_success_still_relays_ok_true(self):
        self._saved["_remote_forward"] = km._remote_forward
        km._remote_forward = lambda r, path, body: {"ok": True}
        code, resp = self._post_end()
        self.assertEqual((code, resp), (200, {"ok": True}))

    def test_a_dead_far_kernel_is_an_honest_failure(self):
        self._saved["_remote_forward"] = km._remote_forward
        km._remote_forward = lambda r, path, body: None
        code, resp = self._post_end()
        self.assertEqual(code, 200)
        self.assertFalse(resp["ok"])
        self.assertIn("isn't answering", resp["error"])
        self.assertIn("gpu1", resp["error"])


if __name__ == "__main__":
    unittest.main()
