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

SYNTHETIC fixtures only: placeholder UUIDs, invented names, hermetic temp STATE.
"""
import json
import os
import tempfile
import types
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel_closedhonesty", os.path.join(BIN, "romp-kernel")).load_module()

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
        self.client = {"send": lambda s: self.client_frames.append(json.loads(s))}

    def tearDown(self):
        for nm, v in self._saved.items():
            setattr(km, nm, v)
        km.Sessions.backend_for = self._saved_bf

    def closed_broadcasts(self):
        return [m for _a, m in self.sent if m.get("type") == "closed"]

    def client_warns(self):
        return [f for f in self.client_frames if f.get("type") == "warn"]


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

    def test_a_kill_that_silently_fails_warns_and_does_not_dismiss(self):
        # tmux's kill_by_name is _fire (best-effort): a timeout is swallowed and kill() returns True
        # while the session keeps running and keeps being LISTED — the exact closed-lie seam.
        self.live[SID] = {}
        self.be.kill = lambda sid: self.be.killed.append(sid)     # runs, but the session survives
        km._drive({"type": "endSession", "id": SID}, self.client)
        self.assertEqual(self.closed_broadcasts(), [],
                         "still live-and-listed: a closed broadcast would dismiss it on every client "
                         "while the next push re-lists it — the permanent dead-swirl seam")
        self.assertEqual(len(self.client_warns()), 1, "the honest signal is a warn, not a dismissal")
        self.assertEqual(self.deaths, [], "no death record for a session that did not die")
        self.assertEqual(self.comment_kills, [], "its comment threads are still that live session's")

    def test_a_dead_sessions_end_still_prunes(self):
        # endSession for an already-dead sid (a dead read-only tab): kill no-ops on the backend, the
        # corroboration reads it dead, and the prune broadcast goes out exactly as before.
        km._drive({"type": "endSession", "id": SID}, self.client)
        self.assertEqual([m.get("id") for m in self.closed_broadcasts()], [SID])
        self.assertEqual(self.client_warns(), [])


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


if __name__ == "__main__":
    unittest.main()
