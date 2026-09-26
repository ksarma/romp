#!/usr/bin/env python3
"""The kernel notices a dead dashboard pane (2026-09-03).

The keepalive was one-way: the kernel sent a small frame every KEEPALIVE_S and expected nothing back. A
peer whose forwarder kept the devbox-side socket open after the browser pane was gone — VS Code's port
forwarder does exactly that — therefore stayed a "live dashboard" forever, and the pusher kept building
and streaming every full payload to it. Measured live: 84 client connections on one kernel, 73 silent for
over five minutes, all phantoms sharing one multiplexed channel with three real panes.

Now every beat is also a WebSocket PING (RFC 6455), which every conforming peer answers with a PONG
without application code; a peer that has not answered the oldest outstanding ping within WS_DEAD_S is
dropped — the missing pong is the event. Any inbound message counts as life too. Real TCP loopback
pairs, matching the kernel's transport. Synthetic only.
"""
import json
import os
import socket
import struct
import tempfile
import threading
import time
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
open(os.path.join(os.environ["XDG_STATE_HOME"], "romp", "session-hosts"), "w").write("off\n")   # a root this module mints: no session host from it (T348)
km = load_source("romp_kernel_wslive", os.path.join(BIN, "romp-kernel"))


def _mask(payload):
    """A client-side (masked) frame body for `payload` with a fixed mask — what a browser's pong looks like."""
    mask = b"\x11\x22\x33\x44"
    return mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))


def _client_frame(opcode, payload):
    n = len(payload)
    hdr = bytes([0x80 | opcode, 0x80 | n]) if n < 126 else bytes([0x80 | opcode, 0x80 | 126]) + struct.pack(">H", n)
    return hdr + _mask(payload)


class _Peer(threading.Thread):
    """The far end of a pane's socket. `pongs=True` behaves like a browser (answers every ping with a pong
    echoing its payload); `pongs=False` is the phantom: it reads what arrives and never answers."""

    def __init__(self, sock, pongs):
        super().__init__(daemon=True)
        self.sock, self.pongs, self.pings, self.texts, self.stop = sock, pongs, [], [], False

    def run(self):
        rf = self.sock.makefile("rb")
        while not self.stop:
            try:
                op, payload, fin = km._ws_recv(rf)  # server frames are unmasked; the reader tolerates that
            except OSError:
                return                              # the kernel side shut the pair down under us (teardown)
            if op is None:
                return
            if op == 0x9:
                self.pings.append(payload)
                if self.pongs:
                    try:
                        self.sock.sendall(_client_frame(0xA, payload))
                    except OSError:
                        return
            elif op == 0x1:
                self.texts.append(payload)


class _Handler(threading.Thread):
    """The kernel side's read loop, as the connection handler runs it: pongs and messages stamp liveness."""

    def __init__(self, client, sock):
        super().__init__(daemon=True)
        self.client, self.sock, self.msgs = client, sock, []

    def run(self):
        rf = self.sock.makefile("rb")
        while self.client["alive"]:
            op, payload = km._ws_recv_message(rf, lambda p: None, on_pong=lambda p: km._note_ws_inbound(self.client))
            if op is None:
                break
            km._note_ws_inbound(self.client)
            self.msgs.append(payload)
        self.client["alive"] = False


class _StampClearForcing:
    """Forces the late order of two writers of client["pingAt"] that the kernel leaves free to land either way
    (2026-09-20): the sender thread's stamp of a ping as it reaches the socket (_ws_sender) and a clear on the
    handler's thread (_note_ws_inbound: a pong, a message, or the return from a dispatch). Each write is atomic under
    the client's qlock, only their ORDER is open, and both orders are valid kernel states (test_c3c's docstring says
    why the kernel is unchanged). The `ping`th ping is held before its stamp until the first clear after arm() has
    landed, and that clear returns only once the stamp point has passed. It wraps the two module functions the harness
    threads look up by name, so the REAL sender runs, over a queue proxy (the hold, before the stamp) and a socket-lock
    proxy (the stamp point: the sender takes that lock right after the stamp). Every hold is bounded by hold_s and
    recorded in `holds`, one record per hold in return order, read by the cases: (name, fired, exited), `fired` the
    wait's own return (True the event, False the bound expired) and `exited` whether __exit__ had run when the wait
    returned, so a release by the exit reads as fired with exited True, a release by the event as fired with exited
    False, and an expiry as not fired. A wait that discards its result cannot tell its release from its expiry, and a
    test over it passes green when the bound runs out (the round 1 review, 2026-09-21). `forced` is True only when
    every hold was released by its event, so a test that means to force asserts it. __exit__ sets both events on
    every path, so a test that raises inside the block strands no sender thread in a hold (test_c3h)."""
    HOLD_S = 1.0

    def __init__(self, module, ping=2, hold_s=HOLD_S):
        self.km, self.ping, self.hold_s = module, ping, hold_s
        self.cleared, self.stamped = threading.Event(), threading.Event()
        self.armed, self.holds, self.exited = False, [], False

    @property
    def forced(self):
        return bool(self.holds) and all(fired and not exited for _, fired, exited in self.holds)

    def arm(self):
        """The next _note_ws_inbound call is the forced clear (an earlier call would spend the events)."""
        self.armed = True

    def _wait(self, name, ev):
        fired = ev.wait(self.hold_s)
        self.holds.append((name, fired, self.exited))    # the wait's own answer, and whether the exit had run by then

    def __enter__(self):
        f = self
        real_sender, real_clear = self.km._ws_sender, self.km._note_ws_inbound
        self._saved = real_sender, real_clear

        class Q:                                    # the sender's queue: the hold sits before the stamp
            def __init__(s, q):
                s.q, s.n, s.at_stamp_point = q, 0, False

            def get(s):
                item = s.q.get()
                if isinstance(item, bytes) and item[:1] == b"\x89":
                    s.n += 1
                    if s.n == f.ping:
                        s.at_stamp_point = True
                        f._wait("the stamp held for the clear", f.cleared)
                return item

        class L:                                    # the socket lock: the sender takes it right after the stamp
            def __init__(s, lock, q):
                s.lock, s.q = lock, q

            def __enter__(s):
                if s.q.at_stamp_point:
                    s.q.at_stamp_point = False
                    f.stamped.set()
                return s.lock.__enter__()

            def __exit__(s, *a):
                return s.lock.__exit__(*a)

        def sender(q, sock, lock, client):
            qp = Q(q)
            return real_sender(qp, sock, L(lock, qp), client)

        def clear(client, now=None):
            if not f.armed:
                return real_clear(client, now)
            f.armed = False
            r = real_clear(client, now)
            f.cleared.set()
            f._wait("the clear's return held for the stamp", f.stamped)
            return r

        self.km._ws_sender, self.km._note_ws_inbound = sender, clear
        return self

    def __exit__(self, *a):
        self.exited = True                          # first, since a hold reads it as its wait returns: the exit's release, not the event's
        self.cleared.set(); self.stamped.set()      # then both holds released, whatever the path: a raise inside the block strands no sender
        self.km._ws_sender, self.km._note_ws_inbound = self._saved


class PhantomPanesAreDropped(unittest.TestCase):
    def setUp(self):
        self.closeables, self.threads, self.queues = [], [], []
        self._saved_clients = list(km._clients)
        km._clients[:] = []
        self.clock = [1_800_000_000.0]
        self._saved_clock, self._saved_outq = km._ws_clock, km._ws_outq
        km._ws_clock = lambda: self.clock[0]
        km._ws_outq = lambda sock: 0                  # loopback drains instantly; the drain probe has its own test

    def tearDown(self):
        km._ws_clock, km._ws_outq = self._saved_clock, self._saved_outq
        km._clients[:] = self._saved_clients
        for q in self.queues:
            q.put(None)                               # end every sender thread the test started
        for s in self.closeables:
            try:
                s.shutdown(socket.SHUT_RDWR)          # a thread parked in a read returns EOF (close alone would
            except OSError:                           # not: the reader's file object keeps the descriptor)
                pass
            try:
                s.close()
            except OSError:
                pass
        for t in self.threads:
            t.join(3.0)
            self.assertFalse(t.is_alive(), "a test thread outlived its test: %r" % t)

    def _pair(self):
        srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0)); srv.listen(1)
        peer = socket.create_connection(srv.getsockname())
        kern, _ = srv.accept()
        srv.close()
        self.closeables += [peer, kern]
        return kern, peer

    def _connect(self, pongs, app="timeline"):
        kern, peer_sock = self._pair()
        client, q, lock = km._new_ws_client(app, "w1", kern)
        km._clients.append(client); self.queues.append(q)
        peer = _Peer(peer_sock, pongs); peer.start()
        handler = _Handler(client, kern); handler.start()
        self.threads += [peer, handler]
        return client, peer, handler

    def _settle(self, pred, timeout=3.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if pred():
                return True
            time.sleep(0.02)
        return pred()

    def test_a_the_beat_carries_a_ping_and_a_browser_answers_it(self):
        client, peer, _ = self._connect(pongs=True)
        t0 = 1_800_000_000.0
        km._keepalive_all(now=t0)
        self.assertTrue(self._settle(lambda: len(peer.pings) == 1 and len(peer.texts) == 1), "one ka text + one ping per beat")
        self.assertEqual(json.loads(peer.texts[0])["type"], "ka")
        self.assertEqual(peer.pings[0], str(int(t0)).encode(), "the ping carries the beat's stamp")
        self.assertTrue(self._settle(lambda: client["pingAt"] is None), "the pong cleared the outstanding ping")
        self.assertTrue(client["alive"])

    def test_b_a_peer_that_never_answers_is_dropped_after_the_window_and_only_then(self):
        client, peer, handler = self._connect(pongs=False)
        t0 = self.clock[0]
        km._keepalive_all(now=t0)
        self.assertTrue(self._settle(lambda: len(peer.pings) == 1))
        self.assertTrue(self._settle(lambda: client["pingAt"] == t0), "the clock runs from the first unanswered ping, stamped as it left")
        self.clock[0] = t0 + km.KEEPALIVE_S
        km._keepalive_all(now=self.clock[0])                        # second beat: still inside the window
        self.assertTrue(self._settle(lambda: len(peer.pings) == 2))
        self.assertTrue(client["alive"], "one missed pong is not death")
        self.assertEqual(client["pingAt"], t0, "…and the oldest unanswered ping keeps the clock")
        self.clock[0] = t0 + km.WS_DEAD_S
        km._keepalive_all(now=self.clock[0])                        # the window has run out
        self.assertFalse(client["alive"], "no pong within WS_DEAD_S → dropped")
        handler.join(3.0)
        self.assertFalse(handler.is_alive(), "the shutdown ended the handler's blocking read")
        self.assertTrue(self._settle(lambda: not peer.is_alive()), "…and the peer saw the close")

    def test_c_any_inbound_message_is_life(self):
        client, peer, handler = self._connect(pongs=False)          # never pongs, but talks
        t0 = self.clock[0]
        km._keepalive_all(now=t0)
        self.assertTrue(self._settle(lambda: len(peer.pings) == 1 and client["pingAt"] == t0))
        peer.sock.sendall(_client_frame(0x1, json.dumps({"type": "activeTab", "id": "x"}).encode()))
        self.assertTrue(self._settle(lambda: client["pingAt"] is None), "a message cleared the outstanding ping")
        self.clock[0] = t0 + km.WS_DEAD_S + 1
        km._keepalive_all(now=self.clock[0])
        self.assertTrue(client["alive"], "a talking peer is never dropped for a missing pong")

    def test_c2_the_clock_starts_when_the_ping_leaves_not_when_the_beat_queued_it(self):
        """A slow-but-alive peer with a backlog ahead of the ping must not be judged on time the ping spent in
        the queue — the diagnosis this change answers found a 300 KB/s tunnel client rightly kept alive."""
        kern, peer_sock = self._pair()
        client, q, lock = km._new_ws_client("timeline", "w1", kern, start_sender=False)   # sender held back = backlog
        km._clients.append(client)
        t0 = self.clock[0]
        km._keepalive_all(now=t0)
        self.assertIsNone(client["pingAt"], "queued, not on the wire → no clock yet")
        self.clock[0] = t0 + 10 * km.WS_DEAD_S                       # a long backlog later…
        km._keepalive_all(now=self.clock[0])
        self.assertTrue(client["alive"], "…still not judged: no ping has reached the peer")
        t = threading.Thread(target=km._ws_sender, args=(q, kern, lock, client), daemon=True); t.start()   # backlog drains
        self.threads.append(t); self.queues.append(q)
        self.assertTrue(self._settle(lambda: client["pingAt"] == self.clock[0]), "stamped as the first ping left")

    def test_c3_a_peer_is_never_judged_while_its_handler_is_inside_a_dispatch(self):
        """A `ready` runs the connect push on the handler thread, tens of seconds on a cold kernel, and the
        peer's pongs wait unread in the receive buffer meanwhile. Unread is not missing (review 2026-09-03).
        The wait before the clear keys the harness on the moment the second ping left rather than on the moment
        the clear landed: a ping that leaves after the clear is a new outstanding ping stamped at its leave time,
        so the sender's stamp and this thread's clear are two valid orders of one kernel state, and asserting None
        right after the clear raced the stamp (red once on CPython 3.14t in CI, 2026-09-20: unforced, the stamp lands
        about a hundred microseconds after the clear, so the red needs one preemption of this thread in that gap, which
        under the GIL takes a switch-interval drop request or a blocking call by the holder and on the free-threaded
        build takes neither; the traces and the unforced run counts are in the ledger entry,
        upstream/2026-09-20-ws-liveness-order.md). This is the ordinary-path case: the body,
        _a_dispatch_return_gets_a_fresh_window, runs unforced here, in whatever order the scheduler gives the threads,
        and is shared with test_c3f, which runs it under _StampClearForcing and guards the wait line in it: deleting that
        line reds test_c3f and leaves this case green, since unforced the stamp lands after this thread has passed the
        assertion. test_c3c runs the late order on purpose."""
        self._a_dispatch_return_gets_a_fresh_window()

    def _a_dispatch_return_gets_a_fresh_window(self):
        """The body of test_c3, one method shared with test_c3f (the forcing-guarded case) so that a change to the wait
        before the clear reaches both. The round 1 review showed by execution that a case carrying its own copy of this
        body stays green when the wait is deleted from test_c3 alone, since the copy is untouched; a shared body is what
        makes the deletion red in test_c3f."""
        client, peer, handler = self._connect(pongs=False)
        t0 = self.clock[0]
        client["inRead"] = False                                    # as the handler marks itself for a dispatch
        km._keepalive_all(now=t0)
        self.assertTrue(self._settle(lambda: client["pingAt"] == t0))
        self.clock[0] = t0 + 3 * km.WS_DEAD_S
        km._keepalive_all(now=self.clock[0])
        self.assertTrue(client["alive"], "silence during a dispatch is the kernel's, not the peer's")
        self.assertTrue(self._settle(lambda: len(peer.pings) == 2), "the second ping has left: no stamp of it is pending")
        km._note_ws_inbound(client); client["inRead"] = True        # the handler returns to its read: fresh clock
        self.assertIsNone(client["pingAt"])
        km._keepalive_all(now=self.clock[0])                        # a new ping…
        self.assertTrue(self._settle(lambda: client["pingAt"] == self.clock[0]))
        self.clock[0] += km.WS_DEAD_S
        km._keepalive_all(now=self.clock[0])                        # …judged on its own fresh window
        self.assertFalse(client["alive"], "back in the read and still silent for a whole window → dropped")

    def test_c3b_a_peer_the_kernel_declines_to_judge_still_gets_its_beat(self):
        """Not judging a client mid-dispatch must not also starve it: the ka is what the shim's own silence
        watchdog listens for, and a long build sends nothing else for tens of seconds (review 2026-09-03)."""
        client, peer, handler = self._connect(pongs=False)
        t0 = self.clock[0]
        client["inRead"] = False
        km._keepalive_all(now=t0)
        self.assertTrue(self._settle(lambda: len(peer.texts) >= 1 and client["pingAt"] == t0))
        self.clock[0] = t0 + 3 * km.WS_DEAD_S
        km._keepalive_all(now=self.clock[0])                        # ancient stamp, but the handler is busy
        self.assertTrue(client["alive"])
        self.assertTrue(self._settle(lambda: len(peer.texts) >= 2), "the beat still crossed to the peer")
        self.assertEqual(json.loads(peer.texts[-1])["type"], "ka")

    def test_c3c_a_ping_that_leaves_after_the_clear_is_a_new_outstanding_ping_stamped_as_it_left(self):
        """The order CI hit in test_c3, run on purpose (2026-09-20): the handler's clear lands first and the second
        beat's ping, already queued, leaves afterwards. The kernel treats it as what it is, a ping nobody has
        answered, stamped at its leave time and judged on its own window from there. This is why the kernel is not
        changed: suppressing the late stamp would leave a ping on the wire never judged, so the obvious kernel fix
        introduces a real defect where the test fix introduces none. Deterministic through _StampClearForcing, and it
        asserts the forcing took, so it never passes by the scheduler's grace.
        Mutation recipe for the one hold: in a scratch copy of kernel/kernel.py, have _note_ws_inbound set a flag on
        the client under its qlock after the clear, and have _ws_sender skip the ping stamp once while the flag is set.
        This test then fails at its pingAt assertion (None where the leave time is due), and test_c3 and test_c3f at the
        shared body's wait for the third ping's stamp, the stamp the flag makes the sender skip, so pingAt stays at the
        None the clear left (executed 2026-09-20; the counts are in the ledger entry)."""
        with _StampClearForcing(km) as forcing:
            client, peer, handler = self._connect(pongs=False)
            t0 = self.clock[0]
            client["inRead"] = False
            km._keepalive_all(now=t0)
            self.assertTrue(self._settle(lambda: client["pingAt"] == t0))
            self.clock[0] = t0 + 3 * km.WS_DEAD_S
            km._keepalive_all(now=self.clock[0])                    # the second ping is queued and held before its stamp
            forcing.arm()
            km._note_ws_inbound(client); client["inRead"] = True    # the clear lands, then the held ping leaves
            self.assertTrue(forcing.forced, "the events, not the bound, ordered the two writes: %r" % (forcing.holds,))
            self.assertEqual(client["pingAt"], self.clock[0], "the late ping is a new outstanding ping, stamped as it left")
            self.assertTrue(self._settle(lambda: len(peer.pings) == 2))
        self.clock[0] += km.WS_DEAD_S - 1
        km._keepalive_all(now=self.clock[0])
        self.assertTrue(client["alive"], "judged on its own window, from the leave time")
        self.clock[0] += 1
        km._keepalive_all(now=self.clock[0])
        self.assertFalse(client["alive"], "silent for that whole window: dropped")

    def test_c3f_the_wait_for_the_second_ping_is_what_keeps_its_stamp_ahead_of_the_clear(self):
        """The guard of test_c3's wait for the second ping (2026-09-21): the shared body runs under _StampClearForcing,
        which holds that ping before its stamp until the clear has landed. The fixed body clears only after the ping has
        reached the peer, which is after its stamp point, so the clear cannot release the hold: it expires at its bound
        (HOLD_S, 1.0 s, inside _settle's 3.0 s, the reason the pass takes about a second), the clear's return then finds
        the stamp point already passed, and the late order is unreachable from the fixed body. Two kinds of assertion:
        the helper's `self.assertIsNone(client["pingAt"])` is the product assertion (no ping outstanding after the
        clear, the value CI saw absent); this case's assertions over forcing.holds are the instrument's (the stamp hold
        expired at its bound, the clear's return was released by the stamp point, so not every hold was released by its
        event). A red in the first is the flake back; a red in the second is the instrument not having forced what this
        case claims. Mutation recipe: in _a_dispatch_return_gets_a_fresh_window delete the wait,
        `self.assertTrue(self._settle(lambda: len(peer.pings) == 2), ...)`, the line before the clear. The clear then
        runs while the second ping is still held, releases the hold, the stamp lands after the clear, and the shared
        body's assertIsNone reds here with CI's text, `AssertionError: 1800000090.0 is not None`; test_c3 stays green
        through the same body (unforced, the stamp lands after this thread has passed the assertion: the reason the
        guard is a separate case over a shared body). A second recipe, `all` to `any` in `forced`: the assertFalse
        below reds, the other cases stay green. The counts of both are in the ledger entry."""
        with _StampClearForcing(km) as forcing:
            forcing.arm()                                           # the body's first _note_ws_inbound call is the clear: the peer sends no pong
            self._a_dispatch_return_gets_a_fresh_window()
            self.assertIn(("the stamp held for the clear", False, False), forcing.holds,
                          "the hold on the stamp expired at its bound, unreleased by the clear: %r" % (forcing.holds,))
            self.assertIn(("the clear's return held for the stamp", True, False), forcing.holds,
                          "the stamp point, not the bound, released the clear's return: %r" % (forcing.holds,))
            self.assertFalse(forcing.forced, "one hold expired at its bound and the other was released by its event, so not every hold was forced: %r" % (forcing.holds,))

    def test_c3h_a_raise_inside_the_forcing_releases_the_held_sender_rather_than_leaving_it_to_its_bound(self):
        """The instrument's release on exit (2026-09-21, the round 1 review's follow-up), at a 10 s hold: the shipped
        1.0 s hold expires before tearDown's 3.0 s join, so at that bound a release could never be told from an expiry.
        The real sender enters the queue proxy's hold before the second ping's stamp, the block is left by a test-local
        raise before any clear, and __exit__ sets both events on every path. The claim is the hold's own record: the
        hold, entered before or after the exit, returned released with the exit already run, not expired; the case makes
        no claim that the thread was blocked in the wait or had reached the hold before the exit. The poll for the record
        is bounded at 30 s only so that the release mutant reds at the boolean rather than at the poll; no assertion
        rests on that bound against the hold. tearDown's outlived-thread backstop does not record the factory's sender
        thread and cannot cover this case, whose wait outlasts its hold. Mutation recipe: remove the two set() calls from
        __exit__. This case then reds at its `fired` assertion about 10 s in, when the bound expires; every other case
        green; tearDown green there, since by its join the expired hold has freed the sender. The counts are in the
        ledger entry."""
        class Deliberate(Exception):
            """The test-local failure inside the block; assertRaises names it so no other error passes as it."""
        with self.assertRaises(Deliberate):
            with _StampClearForcing(km, hold_s=10.0) as forcing:
                client, peer, handler = self._connect(pongs=False)
                t0 = self.clock[0]
                client["inRead"] = False
                km._keepalive_all(now=t0)
                self.assertTrue(self._settle(lambda: client["pingAt"] == t0))
                self.clock[0] = t0 + 3 * km.WS_DEAD_S
                km._keepalive_all(now=self.clock[0])                # the second ping is queued: the real sender holds before its stamp
                raise Deliberate("the test fails inside the block, before any clear")
        self.assertTrue(self._settle(lambda: forcing.holds, timeout=30.0), "the hold never returned within 30 s: neither the exit's release nor the bound's expiry was recorded")
        name, fired, exited = forcing.holds[0]
        self.assertTrue(fired, "the hold ran to its %.0f s bound unreleased: the exit set nothing: %r" % (forcing.hold_s, forcing.holds))
        self.assertTrue(exited, "the event was set before the exit, by something other than the exit (the case made no clear): %r" % (forcing.holds,))

    def test_c4_a_peer_still_draining_its_backlog_is_alive_and_one_that_stopped_acknowledging_is_not(self):
        client, peer, handler = self._connect(pongs=False)
        t0 = self.clock[0]
        outq = [3_000_000]
        km._ws_outq = lambda sock: outq[0]
        km._keepalive_all(now=t0)
        self.assertTrue(self._settle(lambda: client["pingAt"] == t0))
        self.clock[0] = t0 + km.WS_DEAD_S; outq[0] = 2_000_000       # the window passed, but bytes are leaving
        km._keepalive_all(now=self.clock[0])
        self.assertTrue(client["alive"], "unsent bytes fell since the last beat → a slow peer, not a dead one")
        self.clock[0] += km.KEEPALIVE_S; outq[0] = 1_000_000
        km._keepalive_all(now=self.clock[0])
        self.assertTrue(client["alive"])
        stuck_at = self.clock[0]                                    # from here the count never moves
        self.clock[0] += km.KEEPALIVE_S
        km._keepalive_all(now=self.clock[0])
        self.assertTrue(client["alive"], "unchanged once is not yet a verdict")
        self.clock[0] = stuck_at + km.KEEPALIVE_S + km.WS_DEAD_S
        km._keepalive_all(now=self.clock[0])
        self.assertFalse(client["alive"], "unsent bytes unmoved for a whole window → the peer stopped acknowledging")

    def test_c5_the_liveness_clock_is_monotonic(self):
        self.assertIs(self._saved_clock, time.monotonic, "a suspend or an NTP step must not read as silence")

    def test_c6_a_reconnect_of_the_same_page_retires_its_previous_socket_at_once(self):
        """The exact event behind the leak: a page reconnects (same app, same page-instance id) because its
        side of the old socket is dead, however open a forwarder keeps our side. The old socket goes now, not
        after a ping window. Keyed on the INSTANCE id, not the dashboard id: two sockets that share a
        dashboard id without an instance id (the VS Code extension's status pipe beside its feed panel), or
        with different instance ids (a duplicated browser tab, which inherits sessionStorage), are twins that
        must BOTH live — keyed on wid they retired each other every 1.5 s (review 2026-09-03)."""
        old, peer_old, h_old = self._connect(pongs=True); old["iid"] = "page-1"
        def pane(wid, iid):
            kern, _peer = self._pair()
            c, q, _ = km._new_ws_client("timeline", wid, kern); self.queues.append(q)
            if iid:
                c["iid"] = iid
            km._clients.append(c)
            return c
        dup_tab = pane("w1", "page-2")                                # same dashboard id, another page
        twin_pipe_a, twin_pipe_b = pane("w1", ""), pane("w1", "")      # the extension's shape: no instance id
        other_dash = pane("w2", "page-3")
        new_kern, _np = self._pair()
        new, nq, _ = km._new_ws_client("timeline", "w1", new_kern); self.queues.append(nq); new["iid"] = "page-1"
        km._register_ws_client(new)                                  # the same page again
        self.assertFalse(old["alive"], "the page's previous socket is retired on the reconnect itself")
        for c in (new, dup_tab, twin_pipe_a, twin_pipe_b, other_dash):
            self.assertTrue(c["alive"], "every other socket stands")
        self.assertIn(new, km._clients)
        h_old.join(3.0); self.assertFalse(h_old.is_alive(), "the old handler's read ended")
        # and the extension's shape from the other side: a second id-less socket retires nothing
        km._register_ws_client(pane("w1", ""))
        self.assertTrue(twin_pipe_a["alive"] and twin_pipe_b["alive"] and new["alive"])

    def test_d_the_ping_frame_is_well_formed(self):
        f = km._ws_ping_frame(b"1700000000")
        self.assertEqual(f[0], 0x89, "FIN + ping opcode")
        self.assertEqual(f[1], len(b"1700000000"))
        self.assertEqual(f[2:], b"1700000000")
        self.assertEqual(len(km._ws_ping_frame(b"x" * 300)), 2 + 125, "control payloads are capped at 125 bytes")

    def test_e_a_legacy_client_without_a_socket_is_never_judged(self):
        sent = []
        legacy = {"app": "feed", "wid": "", "alive": True, "send": sent.append}
        km._clients.append(legacy)
        km._keepalive_all(now=1_800_000_000.0)
        km._keepalive_all(now=1_800_000_000.0 + 10 * km.WS_DEAD_S)
        self.assertTrue(legacy["alive"])
        self.assertEqual(len(sent), 2, "it still gets the ka text and never a ping")


if __name__ == "__main__":
    unittest.main()
