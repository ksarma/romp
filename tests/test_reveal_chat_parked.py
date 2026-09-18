#!/usr/bin/env python3
"""A wid-targeted chat focus parks when its window's chat pane cannot hear it (review round 1, 2026-09-18).

_reveal_chat_for sent the focus through _send_to_view, which hands a frame to the READY same-wid chat clients
and otherwise to nobody, parking nothing. On the phone that was every session tap made from the feed,
Sessions, Outline or the Log after a return on a non-chat tab: the chat pane is parked (no socket) until the
Chat tab is shown, or the kernel still holds the previous socket, dead without a close for up to WS_DEAD_S.
The shell reveal still went out, so the Chat tab opened, but on the pane's stored session instead of the
tapped one, and a dead session's revive prompt never appeared.

The focus now takes _reveal_request's road: sent to the ready same-wid chat clients; a copy kept in
_PENDING_REVEAL, tagged with the targets, while any of them is unproven (a ping on the wire nobody
answered); parked alone when no ready target took it. The redial's first tab strip and the ready handler
consume the park as they do a push tap's.

Synthetic clients only; no sockets. The sid is a placeholder uuid.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
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
km = load_source("romp_kernel_reveal_parked", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"
W = "W-phone"


def _fake_ws_client(app, wid):
    """Just enough of a _clients row for the reveal paths: send() records the parsed JSON. `ready` is the
    handshake's stamp (every kernel-served socket carries one); a test that wants a socket whose bundle is
    still loading flips it off."""
    got = []
    return {"app": app, "wid": wid, "alive": True, "ready": True,
            "send": lambda s: got.append(json.loads(s))}, got


class FocusParks(unittest.TestCase):
    def setUp(self):
        km._PENDING_REVEAL[0] = None
        self._added = []

    def tearDown(self):
        with km._clients_lock:
            for c in self._added:
                if c in km._clients:
                    km._clients.remove(c)
        km._PENDING_REVEAL[0] = None

    def _register(self, app, wid):
        c, got = _fake_ws_client(app, wid)
        with km._clients_lock:
            km._clients.append(c)
        self._added.append(c)
        return c, got

    def test_no_chat_client_for_the_window_parks_the_focus_and_the_panes_redial_lands_it(self):
        # (a) the phone after a return on a non-chat tab: the chat pane is parked, so the window has a shell and
        # a feed socket and no chat socket at all. Another window's chat must not be moved by the tap (2026-07-29).
        shell, shell_got = self._register("shell", W)
        feed, _ = self._register("feed", W)
        other, other_got = self._register("chat", "W-desktop")
        km._reveal_chat_for(feed, {"type": "focus", "id": SID})
        self.assertEqual(shell_got, [{"type": "reveal", "pane": "chat"}], "the shell is still told to come forward: that is what unparks the pane")
        self.assertEqual(other_got, [])
        self.assertEqual(km._PENDING_REVEAL[0], {"sid": SID, "wid": W}, "the focus waits for the window's chat pane")
        # the pane shows, redials, and its first tab strip consumes (its sender's call); another window's pane
        # and a non-chat pane of this window take nothing, as for a push tap
        km._consume_pending_reveal(other)
        self.assertEqual(other_got, [])
        km._consume_pending_reveal(feed)
        self.assertIsNotNone(km._PENDING_REVEAL[0])
        mine, mine_got = _fake_ws_client("chat", W)
        with mock.patch.object(km, "_live_map", return_value={SID: {}}):
            km._consume_pending_reveal(mine, why="the pane's redial")
        self.assertEqual(mine_got, [{"type": "focus", "id": SID, "live": True, "own": True}])
        self.assertIsNone(km._PENDING_REVEAL[0])

    def test_a_dead_sessions_revive_prompt_parks_too_and_is_reminted_on_the_consume(self):
        # a tap on a dead session's card: _reveal_or_confirm routes confirmRevive through the same door, and the
        # consume re-mints the prompt from the sid (the session is still dead when the pane arrives)
        feed, _ = self._register("feed", W)
        with mock.patch.object(km, "_live_map", return_value={}), \
             mock.patch.object(km, "_name_of", return_value="web"):
            km._reveal_or_confirm(SID, {"type": "focus", "id": SID}, client=feed)
            self.assertEqual(km._PENDING_REVEAL[0], {"sid": SID, "wid": W})
            mine, mine_got = _fake_ws_client("chat", W)
            km._consume_pending_reveal(mine)
        self.assertEqual(mine_got, [{"type": "confirmRevive", "id": SID, "name": "web", "own": True}])
        self.assertIsNone(km._PENDING_REVEAL[0])

    def test_a_focus_to_an_unproven_held_socket_is_sent_and_a_copy_waits_for_the_redial(self):
        # (b) the phone's dominant shape: the kernel still holds the chat socket from before the suspend. It posted
        # ready in its day, so it IS a target; a ping is on the wire nobody has answered (pingAt set), so nothing
        # proves it alive. The focus goes out (the socket may be live) AND a copy stays, tagged with who got it.
        held, held_got = self._register("chat", W)
        held["pingAt"] = 100.0
        feed, _ = self._register("feed", W)
        km._reveal_chat_for(feed, {"type": "focus", "id": SID})
        self.assertEqual(held_got, [{"type": "focus", "id": SID}], "sent as before")
        parked = km._PENDING_REVEAL[0]
        self.assertIsNotNone(parked, "…and kept until the socket proves itself")
        self.assertEqual((parked["sid"], parked["wid"], parked.get("sent")), (SID, W, [held]))
        # the dead socket never pongs; the pane redials and the redial's first strip consumes the copy. The consumed
        # frame is re-minted from the sid: session and liveness, no anchor or cite (the slot's follow-on).
        fresh, fresh_got = _fake_ws_client("chat", W)
        with mock.patch.object(km, "_live_map", return_value={SID: {}}):
            km._consume_pending_reveal(fresh, why="the pane's redial")
        self.assertEqual(fresh_got, [{"type": "focus", "id": SID, "live": True, "own": True}])
        self.assertIsNone(km._PENDING_REVEAL[0])

    def test_the_targets_pong_retires_the_copy_and_a_proven_socket_parks_nothing(self):
        # the live half of the same shape: a desktop pane mid-heartbeat. The pong that proves it retires the copy
        # (the focus frame is ordered ahead of the pong), and a socket with no ping outstanding parks nothing, so a
        # click on a healthy dashboard never leaves a slot behind for a later ready to replay.
        c, got = self._register("chat", W)
        c["pingAt"] = 100.0
        feed, _ = self._register("feed", W)
        km._reveal_chat_for(feed, {"type": "focus", "id": SID})
        self.assertIsNotNone(km._PENDING_REVEAL[0])
        other, _ = self._register("chat", "W-desktop")
        other["pingAt"] = 100.0
        km._note_ws_inbound(other, now=101.0)
        self.assertIsNotNone(km._PENDING_REVEAL[0], "another window's pong is not this target's")
        km._note_ws_inbound(c, now=101.0)
        self.assertIsNone(km._PENDING_REVEAL[0])
        got.clear()
        km._reveal_chat_for(feed, {"type": "focus", "id": SID, "anchor": "u1"})
        self.assertEqual(got, [{"type": "focus", "id": SID, "anchor": "u1"}])
        self.assertIsNone(km._PENDING_REVEAL[0], "a proven socket: delivered, nothing parked")

    def test_a_same_wid_socket_that_has_not_said_ready_is_no_target_and_its_ready_consumes(self):
        # a chat socket exists from its handshake, but until its bundle posts ready it has no listener: a frame
        # sent to it vanishes. No target, so the park stands; the ready handler stamps it and consumes.
        booting, heard = self._register("chat", W)
        booting["ready"] = False
        feed, _ = self._register("feed", W)
        km._reveal_chat_for(feed, {"type": "focus", "id": SID})
        self.assertEqual(heard, [], "nothing is sent to a pane that cannot listen")
        self.assertEqual(km._PENDING_REVEAL[0], {"sid": SID, "wid": W})
        booting["ready"] = True
        with mock.patch.object(km, "_live_map", return_value={SID: {}}):
            km._consume_pending_reveal(booting)
        self.assertEqual(heard, [{"type": "focus", "id": SID, "live": True, "own": True}])
        self.assertIsNone(km._PENDING_REVEAL[0])

    def test_no_wid_keeps_the_broadcast_and_parks_nothing(self):
        # a client that reports no wid (an older build) keeps today's behaviour: every chat hears it, nothing parks
        a, a_got = self._register("chat", "W-a")
        b, b_got = self._register("chat", "W-b")
        km._reveal_chat_for(None, {"type": "focus", "id": SID})
        self.assertEqual(a_got, [{"type": "focus", "id": SID}])
        self.assertEqual(b_got, [{"type": "focus", "id": SID}])
        self.assertIsNone(km._PENDING_REVEAL[0])

    def test_the_journal_pairs_the_park_with_its_consume(self):
        # one stderr line when a focus parks or keeps a copy, none for a plain delivery (a desktop click is not a
        # journal event), so a report that a tap did nothing reads: parked, then consumed or never
        feed, _ = self._register("feed", W)
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            km._reveal_chat_for(feed, {"type": "focus", "id": SID})
            mine, _ = _fake_ws_client("chat", W)
            with mock.patch.object(km, "_live_map", return_value={SID: {}}):
                km._consume_pending_reveal(mine, why="the pane's redial")
            proven, _ = self._register("chat", "W-desktop")
            km._reveal_chat_for(proven, {"type": "focus", "id": SID})
        lines = [l for l in buf.getvalue().splitlines() if l.startswith("[reveal]")]
        self.assertEqual(lines, ["[reveal] focus sid=11111111 wid=W-phone: parked",
                                 "[reveal] sid=11111111 wid=W-phone: consumed — the pane's redial"])


if __name__ == "__main__":
    unittest.main()
