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
    """Orders two writers of client["pingAt"] that the kernel leaves free to land either way (2026-09-20): the
    sender thread's stamp of a ping as it reaches the socket (_ws_sender) and a clear on the handler's thread
    (_note_ws_inbound: a pong, a message, or the return from a dispatch). Each write is atomic under the client's
    qlock; only their ORDER is open, and both orders are valid kernel states, because a ping that leaves after the
    clear is a new outstanding ping stamped at its leave time. Suppressing the late stamp would leave a ping on the
    wire never judged, so the obvious kernel fix introduces a real defect where the test fix introduces none.
    The instrument fixes the order of the `ping`th ping's stamp against the first clear after arm(): `late` holds
    that ping before its stamp until the clear has landed, and lets the clear return only once the stamp point has
    passed; `early` is the converse, the clear waits for the stamp point first. It wraps the two module functions
    the harness threads look up by name, so the REAL sender runs, over a queue proxy (the hold, before the stamp)
    and a socket-lock proxy (the stamp point: the sender takes that lock right after the stamp). Every wait is
    bounded by hold_s and `holds` records whether the event or the bound released each one; `forced` is True only
    when every hold was released by its event, so a test that means to force asserts it. `at` carries
    perf_counter_ns stamps of the clear and of the stamp point for a trace. That record is the distinction a
    bounded wait owes: a wait that discards its result cannot tell its release from its expiry, and a test over it
    passes green when the bound runs out (the round 1 review, 2026-09-21). Leaving the block releases both holds
    whatever the path, since __exit__ sets the two events before it restores the functions, so a test that raises
    inside the block strands no sender thread in a hold; a wait released that way is recorded as not by the event.
    Two more events and two more stamps let a test read that release as an event rather than infer it from a
    bound: `parked` is set as a hold begins its wait, `released` as a hold's wait returns, whatever released it,
    after the record of that hold is complete; `at["exit"]` is stamped in __exit__ before the two sets, and
    `at["hold_returned"]` as a hold returns unreleased by its event, the two releases that stamp tells apart (the
    exit's, within milliseconds of `at["exit"]`; the bound's, about hold_s later). A hold released by its event
    leaves `at` with the two write stamps alone, which test_c3g's keyset assertion reads. The release on exit
    is exercised by test_c3h at a bound that can show a parked sender; its docstring carries the recipe and the
    counts."""
    HOLD_S = 1.0

    def __init__(self, module, order, ping=2, hold_s=HOLD_S):
        assert order in ("late", "early"), order
        self.km, self.order, self.ping, self.hold_s = module, order, ping, hold_s
        self.cleared, self.stamped = threading.Event(), threading.Event()
        self.parked, self.released = threading.Event(), threading.Event()   # a hold began its wait; a hold's wait returned
        self.armed, self.holds, self.at, self.exited = False, [], {}, False

    @property
    def forced(self):
        return bool(self.holds) and all(ok for _, ok in self.holds)

    def arm(self):
        """The next _note_ws_inbound call is the forced clear (an earlier call would spend the events)."""
        self.armed = True

    def _wait(self, name, ev):
        self.parked.set()                                # the thread is at the hold (a test that releases a parked thread waits for this first)
        ok = ev.wait(self.hold_s) and not self.exited    # a release from __exit__ is not the event's
        if not ok:
            self.at["hold_returned"] = time.perf_counter_ns()   # unreleased by its event: against at["exit"], the exit's release or the bound's expiry
        self.holds.append((name, ok))
        self.released.set()                              # after the record, so a reader this wakes finds the hold recorded
        return ok

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
                        if f.order == "late":
                            f._wait("the stamp held for the clear", f.cleared)
                return item

        class L:                                    # the socket lock: the sender takes it right after the stamp
            def __init__(s, lock, q):
                s.lock, s.q = lock, q

            def __enter__(s):
                if s.q.at_stamp_point:
                    s.q.at_stamp_point = False
                    f.at["stamp"] = time.perf_counter_ns()
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
            if f.order == "early":
                f._wait("the clear held for the stamp", f.stamped)
            r = real_clear(client, now)
            f.at["clear"] = time.perf_counter_ns()
            if f.order == "late":
                f.cleared.set()
                f._wait("the clear's return held for the stamp", f.stamped)
            return r

        self.km._ws_sender, self.km._note_ws_inbound = sender, clear
        return self

    def __exit__(self, *a):
        self.exited = True                          # then release both holds, whatever the path: a test that raises
        self.at["exit"] = time.perf_counter_ns()    # inside the block must not strand a sender thread in a hold
        self.cleared.set(); self.stamped.set()      # (test_c3h reads this stamp against the hold's return)
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
        before = set(threading.enumerate())
        client, q, lock = km._new_ws_client(app, "w1", kern)
        # The factory starts the client's sender (ws-send) inside the kernel, and a thread is in the enumeration once
        # start() has returned. Recorded so that tearDown's outlived-thread assertion covers it as it covers the peer
        # and the handler (the round 1 review, 2026-09-21); read from the enumeration rather than started by hand
        # (start_sender=False, as test_c2 does) so the kernel's own start path stays in place for every test that
        # connects this way.
        senders = [t for t in set(threading.enumerate()) - before if t.name == "ws-send"]
        self.assertEqual(len(senders), 1, "the factory started one sender thread: %r" % (senders,))
        km._clients.append(client); self.queues.append(q)
        peer = _Peer(peer_sock, pongs); peer.start()
        handler = _Handler(client, kern); handler.start()
        self.threads += [senders[0], peer, handler]
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
        right after the clear raced the stamp (red once on CPython 3.14t in CI, 2026-09-20: traced unforced, the
        stamp landed 68 to 158 microseconds after the clear in the diagnosis and 80 to 196 in this change's re-trace,
        while this thread was past the assertion within 51 at most, so the red needs one preemption of this thread
        in that gap. Not observed in 320 unforced runs on the free-threaded 3.14t build on a 60-core box, nor in 10
        on 3.12: under the GIL the woken sender gets the CPU only on a switch-interval drop request or a blocking
        call by the holder, and the free-threaded build needs neither. The free-threaded CI cell, two vCPUs running
        four threads, did preempt this thread there once, the red this wait answers). Suppressing the late
        stamp would leave a ping on the wire never judged, so the obvious kernel fix introduces a real defect where
        the test fix introduces none. This is the ordinary-path case: the body, _a_dispatch_return_gets_a_fresh_window,
        runs unforced here, in whatever order the scheduler gives the threads, and is shared with the two cases that
        run it under _StampClearForcing. The wait line in that helper, `self.assertTrue(self._settle(lambda:
        len(peer.pings) == 2), ...)`, the line before the clear, is guarded by test_c3f and not by this case: deleting
        it reds test_c3f and leaves this case green, since unforced the stamp lands about a hundred microseconds after
        this thread has passed the assertion. test_c3g is the early order's committed selection; test_c3c runs the
        late order on purpose."""
        self._a_dispatch_return_gets_a_fresh_window()

    def _a_dispatch_return_gets_a_fresh_window(self):
        """The body of test_c3, one method shared with test_c3f and test_c3g (the forcing-guarded cases) so that a
        change to the wait before the clear reaches all three. The round 1 review showed by execution that a case
        carrying its own copy of this body stays green when the wait is deleted from test_c3 alone, since the copy is
        untouched; a shared body is what makes the deletion red in test_c3f."""
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
        introduces a real defect where the test fix introduces none. Deterministic through _StampClearForcing
        (`late`), and it asserts the forcing took, so it never passes by the scheduler's grace.
        Mutation recipe for the one hold: in a scratch copy of kernel/kernel.py, have _note_ws_inbound set a flag on
        the client under its qlock after the clear, and have _ws_sender skip the ping stamp once while the flag is set.
        This test then fails at its pingAt assertion (None where the leave time is due) and test_c3 fails at its wait
        for the third ping's stamp; executed 2026-09-20, 3 of 3 on CPython 3.12 and on 3.14t (free-threaded)."""
        with _StampClearForcing(km, "late") as forcing:
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

    def test_c3f_the_wait_for_the_second_ping_is_what_keeps_the_clear_ahead_of_its_stamp(self):
        """The guard of test_c3's wait for the second ping (2026-09-21): the shared body runs under _StampClearForcing
        (`late`), which holds that ping before its stamp until the clear has landed. The fixed body clears only after
        the ping has reached the peer, which is after its stamp point, so the clear cannot release the hold: the hold
        expires at its bound (HOLD_S, 1.0 s, inside _settle's 3.0 s), the clear's return then finds the stamp point
        already passed, and the late order is unreachable from the fixed body. The assertions read that from the
        instrument's record, hold by hold, so the pass is the expiry the fixed body makes certain, about a second long.
        Two halves, two kinds of assertion. The helper's `self.assertIsNone(client["pingAt"])` is the product
        assertion: it establishes that the outcome was right, no ping outstanding after the clear, the value CI saw
        absent. This case's two assertIn over forcing.holds are the instrument's assertions: they establish that the
        forcing happened as the fixed body dictates, the stamp hold expired at its bound because the clear came after
        the stamp point, and the clear's return was released by the stamp point, not by its bound. A red in the first
        is the flake back; a red in the second is the instrument not having forced what this case claims it forced.
        Mutation recipe: in _a_dispatch_return_gets_a_fresh_window delete the wait,
        `self.assertTrue(self._settle(lambda: len(peer.pings) == 2), ...)`, the line before the clear. The clear then
        runs while the second ping is still held, releases the hold, the stamp lands after the clear, and the shared
        body's assertIsNone reds here with CI's text, `AssertionError: 1800000090.0 is not None`. test_c3 stays green
        through the same body (unforced, the stamp lands about a hundred microseconds after this thread has passed
        the assertion: the reason the guard is a separate case over a shared body), and test_c3g stays green (its
        hold waits for the stamp point, which the unfixed order still reaches). Executed 2026-09-21 in a scratch copy
        on CPython 3.12 and on 3.14t (free-threaded): this case red 3 of 3 on each, test_c3 green 3 of 3 on each,
        and the module once on each with this case the only red (1 failed, 13 passed; once more per interpreter in
        the round's follow-up, with test_c3h present: 1 failed, 14 passed); as shipped, the module green 5 of 5 on
        each and this case 3 of 3 alone on each."""
        with _StampClearForcing(km, "late") as forcing:
            forcing.arm()                                           # the body's first _note_ws_inbound call is the clear: the peer sends no pong
            self._a_dispatch_return_gets_a_fresh_window()
            self.assertIn(("the stamp held for the clear", False), forcing.holds,
                          "the hold on the stamp expired at its bound, unreleased by the clear: %r" % (forcing.holds,))
            self.assertIn(("the clear's return held for the stamp", True), forcing.holds,
                          "the stamp point, not the bound, released the clear's return: %r" % (forcing.holds,))

    def test_c3g_the_stamp_before_the_clear_is_the_order_the_fixed_body_produces(self):
        """The committed selection of the instrument's `early` order (2026-09-21), so the both-directions evidence the
        review asked for is reproducible from the tree: under `early` the fixed body passes with the forcing satisfied
        (this case); under `late` it passes with the stamp hold expired at its bound (test_c3f); test_c3c runs the
        late order on purpose with the forcing satisfied. Here the clear's hold finds the stamp point already passed,
        because the wait for the second ping ordered the stamp before the clear, and the trace shows that order. This
        is NOT a guard of the wait: with the wait deleted the clear's hold waits for the stamp point instead, the
        forcing is satisfied, and the case stays green under the wait-deletion mutation (executed 2026-09-21 in
        scratch copies of test_c3f's recipe, once per interpreter in the round and once more per interpreter in its
        follow-up: green 2 of 2 on CPython 3.12 and 2 of 2 on 3.14t (free-threaded), inside the module runs that red
        test_c3f alone)."""
        with _StampClearForcing(km, "early") as forcing:
            forcing.arm()
            self._a_dispatch_return_gets_a_fresh_window()
            self.assertTrue(forcing.forced, "the events, not the bound, ordered the two writes: %r" % (forcing.holds,))
            self.assertEqual(set(forcing.at), {"stamp", "clear"}, "both moments were traced: %r" % (forcing.at,))
            self.assertLess(forcing.at["stamp"], forcing.at["clear"], "the stamp point passed before the clear: %r" % (forcing.at,))

    def test_c3h_a_test_that_raises_inside_the_forcing_leaves_no_sender_parked(self):
        """The instrument's release on exit, exercised at a bound that can show a parked sender (2026-09-21, the round
        1 review's follow-up). __exit__ sets the two events before it restores the functions, so a test that raises
        inside the block strands no sender thread in a hold. At the shipped bound that release could never show: a
        1.0 s hold expires before tearDown's 3.0 s join finds the thread, so a parked sender looks released whether
        the exit freed it or the bound ran out. This case raises the bound to 10 s, so the release is the only thing
        that lets the thread go inside the test's time. Under the late order the real sender parks in the queue proxy
        before the second ping's stamp, waiting for a clear that never comes: the case raises a test-local exception
        before any clear, and asserts on the EVENT rather than on a wait that cannot tell its release from its expiry
        (the defect the whole change is about): `released`, with a 30 s bound behind it, three times the hold, whose
        red says the sender was never released; then the hold's return within half the hold of `at["exit"]`, whose red
        says the bound expired and the exit released nothing. Half, not the whole hold, because the hold begins before
        the exit, so the bound's expiry lands within microseconds of hold_s after the exit, on either side of it; the
        exit's release lands within milliseconds; half the hold separates the two by seconds. The record must also read as the
        exit's release: `exited` True and the stamp hold recorded as not released by its event. The peer then receives
        the second ping, a bounded wait accepted only because the release is already proven by the event above.
        Mutation recipe: in a scratch copy of the module, remove the two .set() calls from __exit__. The case then reds
        at the elapsed assertion, `released AFTER the bound expired, not by the exit`, about 10 s in, the 10 s hold
        expiring with the exit having released nothing; tearDown is green there, since by the time it joins the
        expired hold has already freed the sender (a parked sender shows at the join only when a case leaves the
        block with hold time left, which this case does not, as it waits for the return first). Executed 2026-09-21
        in a scratch copy over an archive of the head, kernel byte-identical: red once on CPython 3.12 and once on
        3.14t (free-threaded) at that assertion, the hold returned 10.000052 s and 10.000175 s after the exit (52 and
        175 microseconds past the whole hold, which is why the threshold is half of it), the other 14 cases green and
        no error at teardown. As shipped, green 3 of 3 alone per interpreter, well under a second each (the hold
        returned 92 and 23 microseconds after the exit in one traced run per interpreter), and inside the module's
        5 of 5 per interpreter."""
        class Deliberate(Exception):
            """The test-local failure inside the block; assertRaises names it so no other error passes as it."""
        with self.assertRaises(Deliberate):
            with _StampClearForcing(km, "late", hold_s=10.0) as forcing:
                client, peer, handler = self._connect(pongs=False)
                t0 = self.clock[0]
                client["inRead"] = False
                km._keepalive_all(now=t0)
                self.assertTrue(self._settle(lambda: client["pingAt"] == t0))
                self.clock[0] = t0 + 3 * km.WS_DEAD_S
                km._keepalive_all(now=self.clock[0])                # the second ping is queued; the real sender parks before its stamp
                self.assertTrue(forcing.parked.wait(3.0), "the sender never reached the hold, so there was nothing to release: %r" % (forcing.holds,))
                forcing.arm()                                       # where test_c3c stands before its clear; here the block ends instead
                raise Deliberate("the test fails inside the block, before any clear")
        ok = forcing.released.wait(30.0)
        self.assertTrue(ok, "the parked sender was NEVER released: 30 s passed with the hold still parked (the exit did not release it and the 10 s bound did not expire either)")
        elapsed = (forcing.at["hold_returned"] - forcing.at["exit"]) / 1e9
        self.assertLess(elapsed, forcing.hold_s / 2, "the hold returned %.3f s after the exit, past half its %.1f s bound: released AFTER the bound expired, not by the exit" % (elapsed, forcing.hold_s))
        self.assertTrue(forcing.exited)
        self.assertIn(("the stamp held for the clear", False), forcing.holds, "the hold was released by the exit, not by its event: %r" % (forcing.holds,))
        # The product-side consequence: the released sender goes on to send the held ping. A bounded wait is acceptable
        # here ONLY because the release itself is already proven above by the event and the elapsed time; this line
        # adds what the release led to, not whether it happened.
        self.assertTrue(self._settle(lambda: len(peer.pings) == 2), "the released sender never delivered the second ping")

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
