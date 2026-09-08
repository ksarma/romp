#!/usr/bin/env python3
"""The kernel's half of the send id (2026-09-08): a composer send's client-minted id rides a PARKED op as
its 5th slot, the drain hands it to the backend, build_session stamps it on the queued chip (a backend
queue entry's or a parked op's), on the send's echo event and on the record that landed it
(_note_send_landings), and a ✕ that names its send cancels EXACTLY that entry; an id no queue holds is
the honest miss, never a relocation onto a neighbour wearing the same words (review round 1). The
landed-ids map is bounded and its walk is guarded against a concurrent build of the same session. Round 2
(2026-09-08): a goal-cited follow-up carries its bubble's id into the park or the queue entry, and the park
arm of cancelQueued looks in the backend queue by id before answering a miss (a parked run drains there and
dwells behind the feed hold).

The neighbours pin the same surfaces by source text (tests/test_kernel_send_park.py,
tests/test_kernel.py); this module drives the functions. Loader and isolation as in
tests/test_kernel_send_park.py: hermetic state BEFORE the loads, the account and prompt holds off.
SYNTHETIC fixtures only: this module's own placeholder sid, hostname TESTHOST, invented texts.
"""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()    # the transcripts the backend's landing scan reads
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_queuedsends", os.path.join(BIN, "romp-kernel"))
sbk = load_source("romp_sdk_backend_queuedsends", os.path.join(BIN, "romp_sdk_backend.py"))

# The ACCOUNT gate and the tmux PROMPT HOLD are separate axes (tests/test_kernel_limit_queue.py,
# tests/test_kernel_parked_ops_liveness.py): off here, as in tests/test_kernel_send_park.py.
km._limit_hold = lambda sid: None
km._TMUX_PROMPT_HOLD_S = 0.0

SID = "11111111-2222-3333-4444-bbbbbbbbbb22"        # this module's own synthetic sid
MISS = "too late to cancel — the message already reached the session, and will be answered in the current turn"


def _iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _q(text, send_id="", todo=""):
    """A backend queue entry carrying a client send id: the SDK's _QueueText, the class build_session and
    the cancel path read `send_id` off."""
    return sbk._QueueText(text, todo, send_id)


class _ParkFixture(unittest.TestCase):
    """The park helpers' collaborators, stubbed the way tests/test_kernel_send_park.py stubs them."""

    def setUp(self):
        self.echoes = []
        self.stamps = []
        self._saved = (km._compacting_now, km.Sessions.backend_for, km._push_all, km._optimistic_echo,
                       km._working_now, km._stamp_user_todo_answered)
        km._push_all = lambda: None
        km._optimistic_echo = lambda sid, text, author="human": self.echoes.append((text, author))
        km._stamp_user_todo_answered = lambda sid, tid, text, nonce=None: self.stamps.append((tid, text))
        km._working_now = lambda sid: False
        km._compacting_now = lambda sid: False
        km._pending_ops.clear()
        km._inflight_ops.pop(SID, None)

    def tearDown(self):
        (km._compacting_now, km.Sessions.backend_for, km._push_all, km._optimistic_echo,
         km._working_now, km._stamp_user_todo_answered) = self._saved
        km._pending_ops.clear()
        km._inflight_ops.pop(SID, None)


class _IdKeepingBackend:
    """An SDK-shaped backend for the drain: forwards its own sends and keeps a todo id and a send id on
    the queue entry (the two capability flags _backend_send reads)."""
    queue_carries_todos = True
    queue_carries_send_ids = True

    def __init__(self):
        self.calls = []

    def forwards_sends(self):
        return True

    def send(self, sid, text, **kw):
        self.calls.append((text, kw))
        return True


class ParkedSendCarriesItsId(_ParkFixture):
    """_send_or_park parks a send WITH its client id as the op's 5th slot; the slot survives the disk
    mirror; the drain hands the id (and only a real todo id) to the backend."""

    def test_the_parked_op_carries_the_id_as_its_fifth_slot_and_bare_shapes_stay_bare(self):
        km._compacting_now = lambda sid: True
        be = _IdKeepingBackend()
        self.assertEqual(km._send_or_park(be, SID, "go ahead", echo="human", send_id="s-1"), "parked")
        self.assertEqual(km._send_or_park(be, SID, "Re: the ask — yes", echo="human", user_todo="ut-1", send_id="s-2"),
                         "parked")
        self.assertEqual(km._send_or_park(be, SID, "an answer alone", echo="human", user_todo="ut-2"), "parked")
        self.assertEqual(km._send_or_park(be, SID, "a plain send", echo="human"), "parked")
        self.assertEqual(km._pending_ops[SID],
                         [("send", "go ahead", "human", "", "s-1"),
                          ("send", "Re: the ask — yes", "human", "ut-1", "s-2"),
                          ("send", "an answer alone", "human", "ut-2"),
                          ("send", "a plain send", "human")],
                         "the id is the 5th slot, present only when set; the 3- and 4-slot shapes are unchanged")
        self.assertEqual(be.calls, [], "parked, not sent")
        self.assertEqual(self.echoes, [], "a parked send stamps no echo until it fires")

    def test_the_fifth_slot_survives_the_disk_mirror(self):
        km._compacting_now = lambda sid: True
        km._send_or_park(_IdKeepingBackend(), SID, "go ahead", echo="human", send_id="s-1")
        self.assertEqual(km._load_pending_ops().get(SID), [("send", "go ahead", "human", "", "s-1")],
                         "a kernel restart restores the parked send with its id (the chip keeps its ✕-by-id)")

    def test_the_drain_hands_the_backend_the_id_and_only_a_real_todo_id(self):
        be = _IdKeepingBackend()
        km.Sessions.backend_for = lambda sid: be
        km._pending_ops[SID] = [("send", "a", "human", "", "s-1"),
                                ("send", "Re: the ask — yes", "human", "ut-9", "s-2"),
                                ("send", "an answer alone", "human", "ut-3"),
                                ("send", "c", "human")]
        km._apply_pending_ops()
        self.assertEqual(be.calls, [("a", {"send_id": "s-1"}),
                                    ("Re: the ask — yes", {"user_todo": "ut-9", "send_id": "s-2"}),
                                    ("an answer alone", {"user_todo": "ut-3"}),
                                    ("c", {})],
                         "op[4] rides as send_id; an EMPTY 4th slot is no todo id (nothing stamped, nothing passed)")
        self.assertEqual(self.stamps, [("ut-9", "Re: the ask — yes"), ("ut-3", "an answer alone")],
                         "only the two real answers stamp their todo")
        self.assertNotIn(SID, km._pending_ops, "the whole run drained")

    def test_deliver_send_batch_alone_forwards_the_fifth_slot(self):
        be = _IdKeepingBackend()
        km._deliver_send_batch(be, SID, [("send", "one", None, "", "s-7"), ("send", "two", None)])
        self.assertEqual(be.calls, [("one", {"send_id": "s-7"}), ("two", {})])
        self.assertEqual(self.stamps, [], "an empty 4th slot never stamps")


class CancelParkedById(_ParkFixture):
    """The ✕ on a parked send that names its send: exact by id; an id no parked op carries is the miss and
    removes nothing; only an id-less cancel keeps the index/body fallback."""

    OP1 = ("send", "go ahead", "human", "", "s-1")
    OP2 = ("send", "go ahead", "human", "", "s-2")

    def test_removes_exactly_the_op_carrying_the_id_of_two_wearing_the_same_words(self):
        km._pending_ops[SID] = [self.OP1, self.OP2]
        self.assertIsNone(km._cancel_parked(SID, 0, "go ahead", send_id="s-2"),
                          "a stale index and the shared words: the id wins")
        self.assertEqual(km._pending_ops[SID], [self.OP1], "the other send stays parked")

    def test_an_id_no_parked_op_carries_is_the_miss_and_removes_nothing(self):
        # the first send drained between the push that drew its bubble and the click: its twin is still parked
        km._pending_ops[SID] = [self.OP2]
        self.assertEqual(km._cancel_parked(SID, 0, "go ahead", send_id="s-1"), MISS,
                         "the named send is gone: say so, never pop the neighbour wearing its words")
        self.assertEqual(km._pending_ops[SID], [self.OP2], "the twin survives")
        # the optimistic arm (no park index yet) resolves the same way
        self.assertEqual(km._cancel_parked(SID, -1, "go ahead", send_id="s-1"), MISS)
        self.assertEqual(km._pending_ops[SID], [self.OP2])

    def test_the_in_flight_head_is_never_the_ids_target(self):
        km._pending_ops[SID] = [self.OP1, self.OP2]
        km._inflight_ops[SID] = km._pending_ops[SID][0]          # the drain is handing s-1 to the backend now
        self.assertEqual(km._cancel_parked(SID, 0, "go ahead", send_id="s-1"), MISS,
                         "the backend has it: too late, and never a wrong-op removal")
        self.assertEqual(km._pending_ops[SID], [self.OP1, self.OP2])
        self.assertIsNone(km._cancel_parked(SID, 1, "go ahead", send_id="s-2"), "the second chip still cancels")
        self.assertEqual(km._pending_ops[SID], [self.OP1])

    def test_an_id_less_cancel_keeps_the_index_and_body_fallback(self):
        km._pending_ops[SID] = [("send", "first", "human"), ("send", "second", "human")]
        self.assertIsNone(km._cancel_parked(SID, 0, "second"), "an older client's ✕: the body relocates")
        self.assertEqual(km._pending_ops[SID], [("send", "first", "human")])
        km._pending_ops[SID] = [self.OP1, self.OP2]
        self.assertIsNone(km._cancel_parked(SID, 1, "go ahead"), "and it may name an id-carrying op by index")
        self.assertEqual(km._pending_ops[SID], [self.OP1])


class _DriveFixture(_ParkFixture):
    """_drive's collaborators for a session this kernel HAS (tests/test_kernel_card_predict.py's shape): the
    name registry answers, the backend is ours, the feed fan-out and the goal store are stubbed, and the
    client records every frame the handler answers with."""

    def setUp(self):
        super().setUp()
        self._saved_drive = (km._name_of, km._send_to_app, km.jd.optimistic_followup)
        km._name_of = lambda sid: "web"
        km._send_to_app = lambda app, m: None
        km.jd.optimistic_followup = lambda *a, **k: False
        self.frames = []
        self.client = {"send": lambda raw: self.frames.append(json.loads(raw))}

    def tearDown(self):
        km._name_of, km._send_to_app, km.jd.optimistic_followup = self._saved_drive
        super().tearDown()


class AFollowUpCarriesTheBubblesId(_DriveFixture):
    """A chat-typed citation follow-up (askFollowUp with the composer's sendId): the kernel wraps the text in
    the goal body and the id rides the parked op or the backend queue entry like a plain send's, so the
    bubble's ✕ finds exactly that entry. Before, the handler passed no id while the bubble wore one: the ✕
    missed by id and toasted 'too late' with the follow-up still queued (review round 2)."""

    FU = {"type": "askFollowUp", "itemId": SID + ":g1", "text": "and the tests?", "sid": SID}

    def test_a_parked_follow_up_carries_the_id_as_its_fifth_slot_and_its_cancel_finds_it(self):
        km._compacting_now = lambda sid: True
        be = _IdKeepingBackend()
        km.Sessions.backend_for = lambda sid: be
        self.assertTrue(km._drive({**self.FU, "sendId": "s-fu"}, self.client))
        ops = km._pending_ops.get(SID) or []
        self.assertEqual(len(ops), 1, ops)
        self.assertEqual(ops[0][0], "send")
        self.assertTrue(ops[0][1].startswith("and the tests?"), "the typed words lead the wrapped body")
        self.assertIn("<!-- romp-goal-id: %s:g1 -->" % SID, ops[0][1], "the goal marker rides along")
        self.assertEqual(ops[0][4], "s-fu", "the bubble's id is the op's 5th slot")
        self.assertEqual(be.calls, [], "parked, not sent")
        self.assertIsNone(km._cancel_parked(SID, -1, "and the tests?", send_id="s-fu"),
                          "the bubble's ✕ names its send and finds the parked follow-up")
        self.assertNotIn(SID, km._pending_ops)

    def test_a_delivered_follow_up_hands_the_backend_the_id(self):
        be = _IdKeepingBackend()
        km.Sessions.backend_for = lambda sid: be
        self.assertTrue(km._drive({**self.FU, "sendId": "s-fu2"}, self.client))
        self.assertEqual(len(be.calls), 1, be.calls)
        text, kw = be.calls[0]
        self.assertTrue(text.startswith("and the tests?"))
        self.assertEqual(kw.get("send_id"), "s-fu2", "the queue entry, echo and landing name the bubble")

    def test_a_feed_button_follow_up_posts_no_id_and_stays_bare(self):
        be = _IdKeepingBackend()
        km.Sessions.backend_for = lambda sid: be
        self.assertTrue(km._drive({**self.FU, "nudge": True}, self.client))
        self.assertEqual(len(be.calls), 1, be.calls)
        self.assertEqual(be.calls[0][1], {}, "no id was posted, none is invented")
        km._compacting_now = lambda sid: True
        self.assertTrue(km._drive(self.FU, self.client))
        self.assertEqual(len(km._pending_ops[SID][0]), 3, "a bare follow-up parks in the 3-slot shape")


class _QueueBackend:
    """A backend that owns its queue (exposes unqueue) and keeps send ids on its entries, mirroring
    SdkBackend.unqueue's contract for the kernel's decision: records every pop it is asked for."""

    def __init__(self, pending):
        self._p = list(pending)
        self.unqueued = []

    def pending_queued(self, sid):
        return list(self._p)

    def unqueue(self, sid, idx, expect=None, send_id=None):
        self.unqueued.append((idx, str(expect) if expect is not None else None, send_id))
        if send_id:
            hit = next((i for i, q in enumerate(self._p) if getattr(q, "send_id", "") == send_id), -1)
            if hit >= 0:
                idx, expect = hit, None
        if expect is not None and not (0 <= idx < len(self._p) and self._p[idx] == expect):
            idx = next((i for i, q in enumerate(self._p) if q == expect), -1)
        return self._p.pop(idx) if 0 <= idx < len(self._p) else None


class _QueueBackendWithoutTheIdParameter(_QueueBackend):
    def unqueue(self, sid, idx, expect=None):
        return _QueueBackend.unqueue(self, sid, idx, expect)


class CancelBackendQueuedById(unittest.TestCase):
    """The ✕ on a backend-queue entry that names its send (the same rule as the parked arm)."""

    def test_the_id_wins_over_a_stale_index_and_the_shared_words(self):
        be = _QueueBackend([_q("go ahead", "s-1"), _q("go ahead", "s-2")])
        self.assertIsNone(km._cancel_backend_queued(be, SID, 0, "go ahead", send_id="s-2"))
        self.assertEqual(be.unqueued, [(1, "go ahead", "s-2")], "located by id, and the backend is told the id")
        self.assertEqual([q.send_id for q in be._p], ["s-1"], "the other entry stays")

    def test_an_id_the_queue_does_not_hold_misses_and_touches_nothing(self):
        # s-1 was fed into the CLI between the push and the click; s-2 wears the same words
        be = _QueueBackend([_q("go ahead", "s-2")])
        self.assertEqual(km._cancel_backend_queued(be, SID, 0, "go ahead", send_id="s-1"), MISS)
        self.assertEqual(km._cancel_backend_queued(be, SID, -1, "go ahead", send_id="s-1"), MISS,
                         "the optimistic arm (no index yet) is the same miss")
        self.assertEqual(be.unqueued, [], "no pop was even attempted")
        self.assertEqual([q.send_id for q in be._p], ["s-2"], "the twin survives")

    def test_an_id_less_cancel_keeps_the_body_relocation_and_the_raw_index(self):
        be = _QueueBackend(["alpha", "beta"])
        self.assertIsNone(km._cancel_backend_queued(be, SID, 2, "beta"), "a stale index relocates by body")
        self.assertEqual(be.unqueued, [(1, "beta", None)])
        be = _QueueBackend([_q("go ahead", "s-1"), _q("go ahead", "s-2")])
        self.assertIsNone(km._cancel_backend_queued(be, SID, 1, "go ahead"),
                          "an older client may still name an id-carrying entry by index and body")
        self.assertEqual([q.send_id for q in be._p], ["s-1"])

    def test_a_backend_without_the_id_parameter_still_gets_the_pop(self):
        be = _QueueBackendWithoutTheIdParameter([_q("go ahead", "s-1")])
        self.assertIsNone(km._cancel_backend_queued(be, SID, 0, "go ahead", send_id="s-1"))
        self.assertEqual(be.unqueued, [(0, "go ahead", None)], "the id located it; the pop fell back to the 3-arg form")
        self.assertEqual(be._p, [])


class TheParkArmLooksInTheBackendQueueById(_DriveFixture):
    """The ✕ on a bubble drawn as PARKED (park + sendId) after the run drained: the op left the kernel FIFO
    for the backend's queue, where it dwells behind the feed hold until the CLI takes the text ahead of it,
    still recallable. The park arm used to answer the miss at once; now, for an id no parked op carries, it
    looks in the backend queue by that id, as the md-only arm does (review round 2). By id only: an id-less
    park cancel keeps the single look, since a body could relocate onto a same-words neighbour there."""

    def _cancel(self, be, **fields):
        km.Sessions.backend_for = lambda sid: be
        self.frames.clear()
        self.assertTrue(km._drive({"type": "cancelQueued", "id": SID, **fields}, self.client))
        res = [f for f in self.frames if f.get("type") == "cancelResult"]
        self.assertEqual(len(res), 1, self.frames)
        return res[0]

    def test_a_drained_parked_send_is_still_cancelled_from_its_park_bubble_by_id(self):
        be = _QueueBackend([_q("go ahead", "s-1")])           # the FIFO is empty: the run drained
        r = self._cancel(be, park=0, md="go ahead", sendId="s-1")
        self.assertTrue(r["ok"], r)
        self.assertEqual(be.unqueued, [(0, "go ahead", "s-1")], "found in the backend queue by id, popped there")
        self.assertEqual(be._p, [])

    def test_an_id_neither_queue_holds_is_the_miss_and_touches_nothing(self):
        be = _QueueBackend([_q("go ahead", "s-2")])           # a same-words neighbour, another send's
        r = self._cancel(be, park=0, md="go ahead", sendId="s-1")
        self.assertFalse(r["ok"])
        self.assertEqual(r["text"], MISS)
        self.assertEqual(be.unqueued, [], "no pop attempted")
        self.assertEqual([q.send_id for q in be._p], ["s-2"], "the neighbour survives")

    def test_an_id_less_park_cancel_keeps_the_single_look(self):
        be = _QueueBackend(["go ahead"])
        r = self._cancel(be, park=0, md="go ahead")
        self.assertFalse(r["ok"], "the parked op is gone and no id names the send: the honest miss")
        self.assertEqual(be.unqueued, [], "the backend queue is not searched by body from this arm")
        self.assertEqual(be._p, ["go ahead"])

    def test_a_parked_op_that_is_still_there_wins_without_consulting_the_backend(self):
        km._pending_ops[SID] = [("send", "go ahead", "human", "", "s-1")]
        be = _QueueBackend([_q("go ahead", "s-9")])
        r = self._cancel(be, park=0, md="go ahead", sendId="s-1")
        self.assertTrue(r["ok"])
        self.assertNotIn(SID, km._pending_ops)
        self.assertEqual(be.unqueued, [])


class TheBackendUnqueueHonoursTheSameRule(unittest.TestCase):
    """SdkSession.unqueue is the pop the kernel's cancel reaches, re-located UNDER the backend's lock: an id
    it is given and does not hold must be the miss there too, or the window between the kernel's snapshot
    and the pop (the feeder taking the named entry) still pops the same-words neighbour. An id-less pop
    keeps its text re-location."""

    def setUp(self):
        self.state = tempfile.mkdtemp()
        reg = {"sid": SID, "name": "web", "mode": "acceptEdits", "alive": True,
               "cwd": os.path.join(self.state, "proj")}
        sbk.write_reg(self.state, SID, dict(reg))
        self.be = sbk.SdkBackend(self.state, "/bin/true", lambda *a, **k: None, log=lambda m, **k: None)
        self.s = sbk.SdkSession(self.be, dict(reg))          # never started: unqueue needs only the lock and the list

    def tearDown(self):
        self.s.shutdown()

    def test_an_id_the_session_does_not_hold_pops_nothing(self):
        self.s._pending = [_q("go ahead", "s-2")]
        self.assertIsNone(self.s.unqueue(0, "go ahead", send_id="s-1"),
                          "the named entry left the queue: a miss, never the neighbour wearing its words")
        self.assertEqual([q.send_id for q in self.s._pending], ["s-2"], "the twin survives")
        got = self.s.unqueue(0, "go ahead", send_id="s-2")
        self.assertEqual(getattr(got, "send_id", ""), "s-2", "the id it does hold pops exactly that entry")
        self.assertEqual(self.s._pending, [])

    def test_an_id_less_pop_keeps_the_text_relocation(self):
        self.s._pending = ["alpha", "beta"]
        self.assertEqual(self.s.unqueue(2, "beta"), "beta", "a stale index relocates by text")
        self.assertEqual(self.s._pending, ["alpha"])


class _ChatBackend:
    """An SDK-shaped backend double for build_session: owns the sid, serves a fixed queue and a fixed live
    tail, exposes unqueue (so the queued chips are cancelable and the tmux echo fold stands down)."""

    def __init__(self, queued=(), live=()):
        self._q = list(queued)
        self._live = list(live)
        self.pruned = []

    def owns(self, sid):
        return True

    def pending_queued(self, sid):
        return list(self._q)

    def unqueue(self, sid, idx, expect=None, send_id=None):
        return None

    def live_atoms(self, sid):
        return list(self._live)

    def prune_live(self, sid, tx_uuids, tx_text_t, human_floor):
        self.pruned.append((set(tx_uuids), dict(tx_text_t)))

    def busy(self, sid):
        return None


def _echo(text, send_id, t, n):
    atom = {"type": "user", "uuid": "echo:%d" % n, "session_id": SID, "t": t, "parentUuid": None,
            "author": "human", "_echo_text": text,
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}}
    if send_id:
        atom["_send_id"] = send_id
    return atom


def _urec(uuid, t, content, parent=None):
    """A transcript user record, the CLI's shape: the parser keeps a user record only with its thread
    fields (parentUuid, cwd) present."""
    return {"type": "user", "uuid": uuid, "parentUuid": parent, "timestamp": _iso(t), "sessionId": SID,
            "cwd": "/work/notes-api", "message": {"role": "user", "content": content}}


def _arec(uuid, t, parent, text="done."):
    return {"type": "assistant", "uuid": uuid, "parentUuid": parent, "timestamp": _iso(t), "sessionId": SID,
            "cwd": "/work/notes-api", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


class BuildSessionStampsTheIds(unittest.TestCase):
    """build_session: the queued chip carries `sendId` (a backend entry's or a parked op's), an echo's user
    event carries `sendIds`, and the record that landed an id-carrying send carries every id it landed."""

    U1 = "22222222-2222-3333-4444-bbbbbbbbbb01"
    U2 = "22222222-2222-3333-4444-bbbbbbbbbb02"
    U3 = "22222222-2222-3333-4444-bbbbbbbbbb03"
    A1 = "33333333-2222-3333-4444-bbbbbbbbbb01"

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.tx = os.path.join(self.dir, SID + ".jsonl")
        self.now = int(time.time())
        self.t0 = self.now - 600                     # the transcript's turn, ten minutes ago
        self.sess = [{"sid": SID, "name": "web", "path": self.tx, "mtime": self.now}]
        km._pending_ops.clear()
        km._landed_send_ids.pop(SID, None)

    def tearDown(self):
        km._pending_ops.clear()
        km._landed_send_ids.pop(SID, None)

    def _write(self, recs):
        with open(self.tx, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")

    def _build(self, be):
        with mock.patch.object(km, "_sessions", lambda now, **kw: list(self.sess)), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: be)), \
             mock.patch.object(km, "_captions", lambda sid: {}), \
             mock.patch.object(km, "_limit_hold", lambda sid: None):
            m = km.build_session(SID, self.now, tmux={})
        self.assertIsNotNone(m, "the session must build")
        return m["events"]

    def test_the_queued_chips_carry_the_id_of_the_entry_or_the_parked_op_they_stand_for(self):
        self._write([_urec(self.U1, self.t0, "status?"), _arec(self.A1, self.t0 + 30, self.U1)])
        be = _ChatBackend(queued=[_q("hello there", "s-q1"), "plain queued"])
        km._pending_ops[SID] = [("send", "parked words", "human", "", "s-p1"), ("send", "bare parked", "human"),
                                ("model", "opus")]
        evs = self._build(be)
        q = next((e for e in evs if e.get("kind") == "queued"), None)
        self.assertIsNotNone(q, "the queued indicator shows")
        chips = [(t["md"], t.get("idx"), t.get("park"), t.get("sendId")) for t in q["texts"]]
        self.assertEqual(chips, [("hello there", 0, None, "s-q1"), ("plain queued", 1, None, None),
                                 ("parked words", None, 0, "s-p1"), ("bare parked", None, 1, None),
                                 ("/model opus", None, 2, None)],
                         "an id-carrying entry or parked send names itself; a bare one carries no sendId key")
        self.assertTrue(all("sendId" not in t for t in q["texts"] if t.get("sendId") is None),
                        "no empty sendId key on a bare chip")

    def test_an_echo_still_in_flight_carries_its_send_id_on_its_user_event(self):
        self._write([_urec(self.U1, self.t0, "status?"), _arec(self.A1, self.t0 + 30, self.U1)])
        be = _ChatBackend(live=[_echo("not yet landed", "s-e1", self.now - 5, 1),
                                _echo("a bare echo", "", self.now - 4, 2)])
        evs = self._build(be)
        users = {e["md"]: e for e in evs if e.get("kind") == "user"}
        self.assertEqual(users["not yet landed"].get("sendIds"), ["s-e1"], "the echo names its send")
        self.assertNotIn("sendIds", users["a bare echo"], "a send with no client identity stamps nothing")
        self.assertNotIn("sendIds", users["status?"], "a record that landed no id-carrying send stamps nothing")

    def test_the_record_that_landed_the_send_carries_its_id_and_a_folded_record_every_id(self):
        # two same-worded sends land on two records in send order; one record wearing two sends' text
        # blocks (the CLI's fold) carries both ids; the echoes themselves are retired by the landing
        t_send = self.now - 30
        self._write([_urec(self.U1, t_send + 2, "ship it"),
                     _urec(self.U2, t_send + 4, "ship it", self.U1),
                     _urec(self.U3, t_send + 6, [{"type": "text", "text": "first words"},
                                                 {"type": "text", "text": "Re: the ask — the reply"}], self.U2),
                     _arec(self.A1, t_send + 8, self.U3)])
        be = _ChatBackend(live=[_echo("ship it", "s-1", t_send, 1), _echo("ship it", "s-2", t_send + 1, 2),
                                _echo("first words", "s-3", t_send + 1, 3),
                                _echo("Re: the ask — the reply", "s-4", t_send + 1, 4)])
        evs = self._build(be)
        by_uuid = {e["uuid"]: e for e in evs if e.get("kind") == "user"}
        self.assertEqual(by_uuid[self.U1].get("sendIds"), ["s-1"])
        self.assertEqual(by_uuid[self.U2].get("sendIds"), ["s-2"], "the second send's record, in order")
        self.assertEqual(by_uuid[self.U3].get("sendIds"), ["s-3", "s-4"], "a folded record carries every id")
        self.assertEqual([e["md"] for e in evs if e.get("kind") == "user" and e["uuid"].startswith("echo:")], [],
                         "the landed echoes are hidden behind their records")
        self.assertEqual(len(be.pruned), 1, "the prune ran once, after the landings were noted")
        # a second build (the pusher's next cycle) stamps the same ids: nothing doubles, nothing moves
        evs2 = self._build(be)
        self.assertEqual({e["uuid"]: e.get("sendIds") for e in evs2 if e.get("kind") == "user"},
                         {e["uuid"]: e.get("sendIds") for e in evs if e.get("kind") == "user"})


def _landing(n, t0=1_700_000_000):
    """One id-carrying echo and the record that lands it, both synthetic, for the map's bookkeeping."""
    text = "landing number %d" % n
    live = [{"_echo_text": text, "_send_id": "s-%d" % n, "t": t0 + n, "uuid": "echo:%d" % n}]
    turns = [{"atoms": [{"type": "user", "uuid": "rec-%d" % n, "t": t0 + n + 1,
                         "message": {"role": "user", "content": text}}]}]
    return live, turns, {text: t0 + n + 1}


class LandedIdsMap(unittest.TestCase):
    """_landed_send_ids: bounded at _LANDED_SEND_IDS_CAP (oldest landing out first), and its walk is safe
    against a concurrent build of the same session."""

    def setUp(self):
        km._landed_send_ids.pop(SID, None)

    def tearDown(self):
        km._landed_send_ids.pop(SID, None)

    def test_the_cap_trims_the_oldest_landing_first(self):
        cap = km._LANDED_SEND_IDS_CAP
        for n in range(cap + 1):
            km._note_send_landings(SID, *_landing(n))
        ids = km._landed_send_ids[SID]
        self.assertEqual(len(ids), cap, "one over the cap: one trimmed")
        self.assertNotIn("rec-0", ids, "the oldest landing goes first")
        self.assertEqual(ids["rec-%d" % cap]["ids"], ["s-%d" % cap], "the newest stays")
        self.assertIn("rec-1", ids)

    def test_two_builds_of_one_session_never_break_each_others_walk(self):
        """A pusher cycle and an HTTP request's build run _note_send_landings for one sid at once: one
        inserts landings (and trims) while the other walks the map. Unguarded, the walk raised
        'dictionary changed size during iteration' out of the whole build (review round 1). The switch
        interval is dropped so the threads interleave at nearly every bytecode."""
        cap = km._LANDED_SEND_IDS_CAP
        for n in range(cap):
            km._note_send_landings(SID, *_landing(n))          # a full map: every walk is as long as it gets
        unlanded = ([{"_echo_text": "still in flight", "_send_id": "s-x", "t": 1_700_000_000, "uuid": "echo:x"}],
                    [], {})                                    # a build whose echo has not landed: walk only
        errors, rounds = [], 400
        gate = threading.Barrier(2)

        def lander():
            try:
                gate.wait()
                for n in range(cap, cap + rounds):
                    km._note_send_landings(SID, *_landing(n))
            except BaseException as e:                          # noqa: BLE001 (the test reports it)
                errors.append(("lander", repr(e)))

        def walker():
            try:
                gate.wait()
                for _ in range(rounds):
                    km._note_send_landings(SID, *unlanded)
            except BaseException as e:                          # noqa: BLE001
                errors.append(("walker", repr(e)))

        old = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)
        try:
            ts = [threading.Thread(target=lander), threading.Thread(target=walker)]
            for t in ts:
                t.start()
            for t in ts:
                t.join(30)
        finally:
            sys.setswitchinterval(old)
        self.assertFalse(any(t.is_alive() for t in ts), "both builds finished")
        self.assertEqual(errors, [], "neither build raised")
        self.assertEqual(len(km._landed_send_ids[SID]), cap, "the cap held throughout")


class TheIdSurvivesTheRestartMirror(unittest.TestCase):
    """The echo mirror round trip: an id-carrying echo persisted by one kernel is reseeded by the next
    with its id, and when its CLI died holding it the re-queued entry carries the id too, so the client's
    bubble still clears by id after the restart."""

    def setUp(self):
        self.state = tempfile.mkdtemp()
        self.cwd = os.path.join(self.state, "proj")
        os.makedirs(self.cwd)
        self.lines = []
        self.reg = {"sid": SID, "name": "web", "mode": "acceptEdits", "alive": True, "cwd": self.cwd}
        sbk.write_reg(self.state, SID, dict(self.reg))

    def _backend(self):
        return sbk.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                              log=lambda m, **k: self.lines.append(str(m)))

    def test_the_reseeded_echo_and_the_re_queued_entry_carry_the_id(self):
        be1 = self._backend()
        t = int(time.time()) - 10
        be1._stash_live(SID, "echo:1", _echo("carry me", "s-1", t, 1))
        be1._stash_live(SID, "echo:2", _echo("plain", "", t + 1, 2))
        be1._persist_echoes(SID)
        mirror = {e["text"]: e for e in (sbk.read_reg(self.state, SID) or {}).get("echoes", [])}
        self.assertEqual(mirror["carry me"].get("sendId"), "s-1", "the mirror keeps the id")
        self.assertNotIn("sendId", mirror["plain"])
        # the next kernel: a readable transcript with neither text landed, so the dead CLI provably
        # held both sends and the boot re-queues them
        path = sbk.transcript_path(self.cwd, SID)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()
        be2 = self._backend()
        be2._reseed_echoes([sbk.read_reg(self.state, SID)])
        live = {a["_echo_text"]: a for a in be2.live_atoms(SID) if a.get("_echo_text")}
        self.assertEqual(live["carry me"].get("_send_id"), "s-1", "the reseeded echo carries the id")
        self.assertNotIn("_send_id", live["plain"])
        queue = (sbk.read_reg(self.state, SID) or {}).get("queue")
        self.assertEqual(queue, [{"text": "carry me", "sendId": "s-1"}, "plain"],
                         "the re-queued entry carries the id; a bare send re-queues bare")
        self.assertEqual([getattr(q, "send_id", "") for q in sbk._queue_texts(queue)], ["s-1", ""],
                         "…and the seed reads it back onto the entry")


if __name__ == "__main__":
    unittest.main()
