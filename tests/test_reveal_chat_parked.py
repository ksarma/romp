#!/usr/bin/env python3
"""A wid-targeted chat focus parks when its window's chat pane cannot hear it (review round 1, 2026-09-18).

_reveal_chat_for sent the focus through _send_to_view, which hands a frame to the READY same-wid chat clients
and otherwise to nobody, parking nothing. On the phone that was every session tap made from the feed,
Sessions, Outline or the Log after a return on a non-chat tab: the chat pane is parked (no socket) until the
Chat tab is shown, or the kernel still holds the previous socket, dead without a close for up to WS_DEAD_S.
The shell reveal still went out, so the Chat tab opened, but on the pane's stored session instead of the
tapped one, and a dead session's revive prompt never appeared.

The focus now takes _reveal_request's road: sent to the ready same-wid chat clients; a copy kept in the
window's _PENDING_REVEAL entry, tagged with the targets, while every taker is unproven (a ping on the wire
nobody answered); parked alone when no ready target took it. The redial's first tab strip and the ready
handler consume the park as they do a push tap's.

Review round 2 (2026-09-18): the slot is keyed by window (a click in one window overwrote a push tap parked
for another); a window's entry goes with its last client; a copy is kept only when EVERY taker is unproven
(a proven pane displayed the focus, so a copy for the unproven one replayed hours later); a copy tagged only
with a socket the reaper dropped is retired at the reap, unless the window's redialed chat pane is already
connected, whose first strip lands it.

Synthetic clients only; the one socket-shaped fixture is a stub with a shutdown method. Placeholder uuids.
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
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_reveal_parked", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"
SID_B = "22222222-3333-4444-5555-666666666666"
W = "W-phone"


def _fake_self(path):
    """A connect handler with a peer that closes at once (tests/test_chat_skeleton_reconnect.py's shape): the real
    Handler._ws runs its handshake, reads the close, and its finally removes the client, the one road the kernel's
    disconnect bookkeeping runs on."""
    class FakeSelf:
        headers = {"Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ=="}
        rfile = io.BytesIO(); wfile = io.BytesIO()
        connection = type("FakeSock", (), {"sendall": lambda self, b: None, "shutdown": lambda self, how: None})()
        close_connection = False
        def send_response(self, *a): pass
        def send_header(self, *a): pass
        def end_headers(self): pass
    FakeSelf.path = path
    return FakeSelf()


def _fake_ws_client(app, wid):
    """Just enough of a _clients row for the reveal paths: send() records the parsed JSON. `ready` is the
    handshake's stamp (every kernel-served socket carries one); a test that wants a socket whose bundle is
    still loading flips it off."""
    got = []
    return {"app": app, "wid": wid, "alive": True, "ready": True,
            "send": lambda s: got.append(json.loads(s))}, got


class FocusParks(unittest.TestCase):
    def setUp(self):
        km._PENDING_REVEAL.clear()
        self._added = []

    def tearDown(self):
        with km._clients_lock:
            for c in self._added:
                if c in km._clients:
                    km._clients.remove(c)
        km._PENDING_REVEAL.clear()

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
        self.assertEqual(km._PENDING_REVEAL.get(W), {"sid": SID, "wid": W}, "the focus waits for the window's chat pane")
        # the pane shows, redials, and its first tab strip consumes (its sender's call); another window's pane
        # and a non-chat pane of this window take nothing, as for a push tap
        km._consume_pending_reveal(other)
        self.assertEqual(other_got, [])
        km._consume_pending_reveal(feed)
        self.assertIsNotNone(km._PENDING_REVEAL.get(W))
        mine, mine_got = _fake_ws_client("chat", W)
        with mock.patch.object(km, "_live_map", return_value={SID: {}}):
            km._consume_pending_reveal(mine, why="the pane's redial")
        self.assertEqual(mine_got, [{"type": "focus", "id": SID, "live": True, "own": True}])
        self.assertEqual(km._PENDING_REVEAL, {})

    def test_a_dead_sessions_revive_prompt_parks_too_and_is_reminted_on_the_consume(self):
        # a tap on a dead session's card: _reveal_or_confirm routes confirmRevive through the same door, and the
        # consume re-mints the prompt from the sid (the session is still dead when the pane arrives)
        feed, _ = self._register("feed", W)
        with mock.patch.object(km, "_live_map", return_value={}), \
             mock.patch.object(km, "_name_of", return_value="web"):
            km._reveal_or_confirm(SID, {"type": "focus", "id": SID}, client=feed)
            self.assertEqual(km._PENDING_REVEAL.get(W), {"sid": SID, "wid": W})
            mine, mine_got = _fake_ws_client("chat", W)
            km._consume_pending_reveal(mine)
        self.assertEqual(mine_got, [{"type": "confirmRevive", "id": SID, "name": "web", "own": True}])
        self.assertEqual(km._PENDING_REVEAL, {})

    def test_a_focus_to_an_unproven_held_socket_is_sent_and_a_copy_waits_for_the_redial(self):
        # (b) the phone's dominant shape: the kernel still holds the chat socket from before the suspend. It posted
        # ready in its day, so it IS a target; a ping is on the wire nobody has answered (pingAt set), so nothing
        # proves it alive. The focus goes out (the socket may be live) AND a copy stays, tagged with who got it.
        held, held_got = self._register("chat", W)
        held["pingAt"] = 100.0
        feed, _ = self._register("feed", W)
        km._reveal_chat_for(feed, {"type": "focus", "id": SID})
        self.assertEqual(held_got, [{"type": "focus", "id": SID}], "sent as before")
        parked = km._PENDING_REVEAL.get(W)
        self.assertIsNotNone(parked, "…and kept until the socket proves itself")
        self.assertEqual((parked["sid"], parked["wid"], parked.get("sent")), (SID, W, [held]))
        # the dead socket never pongs; the pane redials and the redial's first strip consumes the copy. The consumed
        # frame is re-minted from the sid: session and liveness, no anchor or cite (the slot's follow-on).
        fresh, fresh_got = _fake_ws_client("chat", W)
        with mock.patch.object(km, "_live_map", return_value={SID: {}}):
            km._consume_pending_reveal(fresh, why="the pane's redial")
        self.assertEqual(fresh_got, [{"type": "focus", "id": SID, "live": True, "own": True}])
        self.assertEqual(km._PENDING_REVEAL, {})

    def test_the_targets_pong_retires_the_copy_and_a_proven_socket_parks_nothing(self):
        # the live half of the same shape: a desktop pane mid-heartbeat. The pong that proves it retires the copy
        # (the focus frame is ordered ahead of the pong), and a socket with no ping outstanding parks nothing, so a
        # click on a healthy dashboard never leaves a slot behind for a later ready to replay.
        c, got = self._register("chat", W)
        c["pingAt"] = 100.0
        feed, _ = self._register("feed", W)
        km._reveal_chat_for(feed, {"type": "focus", "id": SID})
        self.assertIsNotNone(km._PENDING_REVEAL.get(W))
        other, _ = self._register("chat", "W-desktop")
        other["pingAt"] = 100.0
        km._note_ws_inbound(other, now=101.0)
        self.assertIsNotNone(km._PENDING_REVEAL.get(W), "another window's pong is not this target's")
        km._note_ws_inbound(c, now=101.0)
        self.assertEqual(km._PENDING_REVEAL, {})
        got.clear()
        km._reveal_chat_for(feed, {"type": "focus", "id": SID, "anchor": "u1"})
        self.assertEqual(got, [{"type": "focus", "id": SID, "anchor": "u1"}])
        self.assertEqual(km._PENDING_REVEAL, {}, "a proven socket: delivered, nothing parked")

    def test_a_same_wid_socket_that_has_not_said_ready_is_no_target_and_its_ready_consumes(self):
        # a chat socket exists from its handshake, but until its bundle posts ready it has no listener: a frame
        # sent to it vanishes. No target, so the park stands; the ready handler stamps it and consumes.
        booting, heard = self._register("chat", W)
        booting["ready"] = False
        feed, _ = self._register("feed", W)
        km._reveal_chat_for(feed, {"type": "focus", "id": SID})
        self.assertEqual(heard, [], "nothing is sent to a pane that cannot listen")
        self.assertEqual(km._PENDING_REVEAL.get(W), {"sid": SID, "wid": W})
        booting["ready"] = True
        with mock.patch.object(km, "_live_map", return_value={SID: {}}):
            km._consume_pending_reveal(booting)
        self.assertEqual(heard, [{"type": "focus", "id": SID, "live": True, "own": True}])
        self.assertEqual(km._PENDING_REVEAL, {})

    def test_no_wid_keeps_the_broadcast_and_parks_nothing(self):
        # a client that reports no wid (an older build) keeps today's behaviour: every chat hears it, nothing parks
        a, a_got = self._register("chat", "W-a")
        b, b_got = self._register("chat", "W-b")
        km._reveal_chat_for(None, {"type": "focus", "id": SID})
        self.assertEqual(a_got, [{"type": "focus", "id": SID}])
        self.assertEqual(b_got, [{"type": "focus", "id": SID}])
        self.assertEqual(km._PENDING_REVEAL, {})

    def test_a_proven_taker_beside_an_unproven_one_displays_the_focus_and_no_copy_is_kept(self):
        # review round 2 (2026-09-18): two ready chat clients wear the window's wid, A with a ping outstanding and B proven
        # (no ping on the wire). B displays the focus the moment it lands, so a copy kept for A alone would replay at the
        # window's next redial, hours later, as a session switch or a revive prompt nobody asked for. Every taker unproven
        # keeps a copy; one proven taker means no copy. A alone (the phone's dead-held socket) still parks its rescue.
        a, a_got = self._register("chat", W)
        a["pingAt"] = 100.0
        b, b_got = self._register("chat", W)
        feed, _ = self._register("feed", W)
        km._reveal_chat_for(feed, {"type": "focus", "id": SID})
        self.assertEqual(a_got, [{"type": "focus", "id": SID}])
        self.assertEqual(b_got, [{"type": "focus", "id": SID}], "both takers get the frame")
        self.assertEqual(km._PENDING_REVEAL, {}, "a proven taker displayed it: no copy waits to replay")
        with km._clients_lock:
            km._clients.remove(b)
        a_got.clear()
        km._reveal_chat_for(feed, {"type": "focus", "id": SID})
        self.assertEqual(a_got, [{"type": "focus", "id": SID}])
        self.assertEqual((km._PENDING_REVEAL.get(W) or {}).get("sent"), [a], "A alone, unproven: the copy is kept for its redial")

    def test_a_copy_tagged_only_with_a_socket_the_reaper_dropped_is_retired(self):
        # review round 2 (2026-09-18): the copy for an unproven taker waited on its pong, and nothing retired it when the
        # keepalive judged the socket dead (WS_DEAD_S with no pong), so it stood for the pane's next redial, minutes or
        # hours later. The reaper's drop retires it, through the real beat: a socket-shaped client with a ping older than
        # WS_DEAD_S and no other chat pane in the window.
        a, a_got = self._register("chat", W)
        a["pingAt"] = 100.0
        a["sock"] = type("Sock", (), {"shutdown": lambda self, how: None})()   # judged (has a socket), no fileno: no outq read
        feed, _ = self._register("feed", W)
        km._reveal_chat_for(feed, {"type": "focus", "id": SID})
        self.assertEqual((km._PENDING_REVEAL.get(W) or {}).get("sent"), [a])
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            km._keepalive_all(now=100.0 + km.WS_DEAD_S)
        self.assertIs(a["alive"], False, "the beat judged the socket dead")
        self.assertEqual(km._PENDING_REVEAL, {}, "the copy went with its only target")
        self.assertIn("[reveal] sid=11111111 wid=W-phone: copy retired, its target was reaped", buf.getvalue())
        # a copy with another target left keeps waiting on that one
        km._PENDING_REVEAL.clear()
        a2, _ = self._register("chat", W)
        a2["pingAt"] = 100.0
        km._PENDING_REVEAL[W] = {"sid": SID, "wid": W, "sent": [a, a2]}
        km._retire_reveal_copy_at_reap(a)
        self.assertEqual(km._PENDING_REVEAL.get(W), {"sid": SID, "wid": W, "sent": [a2]})

    def test_the_reap_of_a_twin_keeps_the_park_for_the_redial_that_superseded_it(self):
        # the phone's tap, in the racy order: the focus reached the dead-held socket A (copy kept), the shell reveal showed
        # the chat pane, its redial registered as A's twin (same iid) and A was dropped with the successor already in
        # _clients. If the beat now judges A before the redial's first strip consumes, the copy must NOT go: it stands as a
        # plain park for the successor, whose first strip lands it (kernel.py _retire_reveal_copy_at_reap).
        a, _ = self._register("chat", W)
        a["pingAt"] = 100.0
        a["iid"] = "page-1"
        a["sock"] = type("Sock", (), {"shutdown": lambda self, how: None})()
        feed, _ = self._register("feed", W)
        km._reveal_chat_for(feed, {"type": "focus", "id": SID})
        self.assertEqual((km._PENDING_REVEAL.get(W) or {}).get("sent"), [a])
        fresh, fresh_got = _fake_ws_client("chat", W)
        fresh["iid"] = "page-1"; fresh["ready"] = False   # a redial carries no ready until its first strip stamps it
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            km._register_ws_client(fresh)                # the twin rule drops A
            self._added.append(fresh)
            self.assertIs(a["alive"], False)
            km._keepalive_all(now=100.0 + km.WS_DEAD_S)   # the beat over the dropped A, before the successor's strip
        self.assertEqual(km._PENDING_REVEAL.get(W), {"sid": SID, "wid": W}, "a plain park now, for the successor")
        self.assertIn("the park stands for the window's other chat pane", buf.getvalue())
        with mock.patch.object(km, "_live_map", return_value={SID: {}}):
            km._consume_pending_reveal(fresh, why="the pane's redial")
        self.assertEqual([m for m in fresh_got if m["type"] != "ka"],   # the beat's ka reached the successor too
                         [{"type": "focus", "id": SID, "live": True, "own": True}])
        self.assertEqual(km._PENDING_REVEAL, {})

    def test_a_click_in_one_window_does_not_overwrite_another_windows_parked_push_tap(self):
        # review round 2 (2026-09-18): the slot was one for every window. A push tap parked for a booting window B (its
        # shell POSTed /reveal, its chat pane not up yet) was overwritten by a session click in window A whose chat pane
        # was unproven, or had no ready chat pane, and B's tap was lost. Each window's park is its own entry now.
        shell_b, _ = self._register("shell", "W-B")
        with mock.patch.object(km, "_live_map", return_value={}), mock.patch.object(km, "_name_of", return_value="web"):
            self.assertFalse(km._reveal_request(SID_B, "W-B", boot=True, via="link"))
        self.assertEqual(km._PENDING_REVEAL.get("W-B"), {"sid": SID_B, "wid": "W-B"})
        a, _ = self._register("chat", "W-A")
        a["pingAt"] = 100.0
        feed_a, _ = self._register("feed", "W-A")
        km._reveal_chat_for(feed_a, {"type": "focus", "id": SID})      # the unproven-taker click
        self.assertEqual((km._PENDING_REVEAL.get("W-A") or {}).get("sent"), [a])
        self.assertEqual(km._PENDING_REVEAL.get("W-B"), {"sid": SID_B, "wid": "W-B"}, "B's tap stands beside A's copy")
        km._note_ws_inbound(a, now=101.0)                               # A's pong retires A's copy alone
        self.assertIsNone(km._PENDING_REVEAL.get("W-A"))
        self.assertEqual(km._PENDING_REVEAL.get("W-B"), {"sid": SID_B, "wid": "W-B"})
        with km._clients_lock:
            km._clients.remove(a)
        km._reveal_chat_for(feed_a, {"type": "focus", "id": SID})      # the no-ready-chat click parks under A
        self.assertEqual(km._PENDING_REVEAL.get("W-A"), {"sid": SID, "wid": "W-A"})
        self.assertEqual(km._PENDING_REVEAL.get("W-B"), {"sid": SID_B, "wid": "W-B"})
        chat_b, b_got = _fake_ws_client("chat", "W-B")
        with mock.patch.object(km, "_live_map", return_value={}), mock.patch.object(km, "_name_of", return_value="web"):
            km._consume_pending_reveal(chat_b)
        self.assertEqual(b_got, [{"type": "confirmRevive", "id": SID_B, "name": "web", "own": True}], "B's tap lands on B's pane")
        self.assertEqual(km._PENDING_REVEAL.get("W-A"), {"sid": SID, "wid": "W-A"}, "A's park is untouched by B's consume")

    def test_a_windows_park_goes_with_its_last_client_and_stays_while_another_pane_is_up(self):
        # review round 2 (2026-09-18): nothing cleared a park on a disconnect, so a boot reveal whose page died before its
        # chat pane came up sat in the slot until the next tap overwrote it (and, keyed, would sit for the kernel's life).
        # The window's last client takes its park with it; a window with another pane up keeps it (the phone's shell and
        # feed while its chat pane is parked). The no-wid entry names no window and stays.
        shell_b, _ = self._register("shell", "W-B")
        feed_b, _ = self._register("feed", "W-B")
        with mock.patch.object(km, "_live_map", return_value={SID_B: {}}):
            km._reveal_request(SID_B, "W-B", boot=True, via="link")
        with km._clients_lock:
            km._clients.remove(shell_b)
            km._forget_pending_reveal_if_last(shell_b)
        self.assertEqual(km._PENDING_REVEAL.get("W-B"), {"sid": SID_B, "wid": "W-B"}, "the feed still holds the window")
        buf = io.StringIO()
        with km._clients_lock, contextlib.redirect_stderr(buf):
            km._clients.remove(feed_b)
            km._forget_pending_reveal_if_last(feed_b)
        self.assertEqual(km._PENDING_REVEAL, {}, "the window is gone, and so is its park")
        self.assertIn("[reveal] sid=22222222 wid=W-B: dropped, its window's last client left", buf.getvalue())
        with mock.patch.object(km, "_live_map", return_value={SID: {}}):
            km._reveal_request(SID, "")
        nowid, _ = self._register("feed", "")
        with km._clients_lock:
            km._clients.remove(nowid)
            km._forget_pending_reveal_if_last(nowid)
        self.assertEqual(km._PENDING_REVEAL.get(""), {"sid": SID, "wid": ""}, "a park with no wid waits for the first chat pane, as before")

    def test_the_handlers_close_drops_the_window_park_with_its_last_client(self):
        # the same rule through the real handler: Handler._ws registers the client, reads the peer's close at once, and
        # its finally removes the client and runs the disconnect bookkeeping (beside T347's active-chat drop).
        with mock.patch.object(km, "_live_map", return_value={SID: {}}):
            km._reveal_request(SID, "W-C", via="sw")
        self.assertEqual(km._PENDING_REVEAL.get("W-C"), {"sid": SID, "wid": "W-C"})
        real_recv = km._ws_recv
        km._ws_recv = lambda rfile: (0x8, b"", True)     # the peer closes at once
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                km.Handler._ws(_fake_self("/ws?app=shell&wid=W-C"))
        finally:
            km._ws_recv = real_recv
        self.assertFalse(any((c.get("wid") or "") == "W-C" for c in km._clients), "the handler's finally removed the client")
        self.assertEqual(km._PENDING_REVEAL, {}, "and the window's park went with it")

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
