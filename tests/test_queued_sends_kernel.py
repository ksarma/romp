#!/usr/bin/env python3
"""The kernel's user-todo slot on a parked send, the ws park arm's look into the backend queue by the copy's id,
and the cancel paths that carry no copy id, driven through the functions (2026-09-08; re-aimed 2026-09-15 with
the upstream pull-in): a parked ANSWER carries its todo id as the op's fifth slot (the fourth is the copy's
press-time id, or None when only a todo rides: _op_qid, _op_todo), the drain hands only a real todo id to the
backend and stamps only the real answers, a park cancel whose id names no parked op looks in the backend queue by
that id before answering the miss (4e Q4: a fork-only arm riding the fork-only feed hold), an id-less cancel keeps
the index/body reading in the ws park arm and in SdkSession.unqueue, a feed-button follow-up parks bare, and the
one-time mirror migration in _load_pending_ops carries a pending-ops file written by the kernel before the fourth
slot took the copy's id (the K2 audit's shapes).

The copy's own identity is the id the client mints at the press (upstream's #1224 with #1260, #1261 and #1273):
its kernel half is tests/test_queued_copy_press_id.py and its SdkBackend half tests/test_queued_copy_identity.py.
This module's earlier identity cases (the fork's fifth-slot send id, the id on the wire, the kernel's landed-ids
map, the mirror's id field) retired with that identity under the pull-in's 4e Q1 and Q5; each retired case is
named with its twin in the class docstring or the module comment that replaces it, and in the pull-in's log.

The neighbours pin the same surfaces by source text (tests/test_kernel_send_park.py, tests/test_kernel.py); this
module drives the functions. Loader and isolation as in tests/test_kernel_send_park.py: hermetic state BEFORE the
loads, the account and prompt holds off.
SYNTHETIC fixtures only: this module's own placeholder sid, hostname TESTHOST, invented texts.
"""
import json
import os
import tempfile
import unittest
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
# tests/test_kernel_parked_ops_liveness.py): off here, as in tests/test_kernel_send_park.py. The stub takes the
# chat build's `usage=` keyword too, so a build path reaching the limit branch never trips on it.
km._limit_hold = lambda sid, usage=None: None
km._TMUX_PROMPT_HOLD_S = 0.0

SID = "11111111-2222-3333-4444-bbbbbbbbbb22"        # this module's own synthetic sid
QID = "echo:" + "a" * 32                            # a copy id in the kernel's own echo form (_CLIENT_QID_RE)
QID_B = "echo:" + "b" * 32                          # another copy's id: a same-words neighbour in a queue
QID_C = "echo:" + "c" * 32


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


class _TodoKeepingBackend:
    """An SDK-shaped backend for the drain: forwards its own sends and keeps a todo id on the queue entry
    (queue_carries_todos, the capability flag _backend_send reads). Its send takes no `qid`, so a press-minted
    copy id is left off (_takes_qid) and the keywords it records are the todo's alone."""
    queue_carries_todos = True

    def __init__(self):
        self.calls = []

    def forwards_sends(self):
        return True

    def send(self, sid, text, **kw):
        self.calls.append((text, kw))
        return True


class ParkedAnswerCarriesItsTodo(_ParkFixture):
    """_send_or_park parks an ANSWER with its todo id as the op's fifth slot, behind the copy's press-time id or
    None (4e Q2 REFINED); the drain hands only a real todo id to the backend and stamps only the real answers.
    This class's copy-id cases retired 2026-09-15 with the fork's send-id identity (4e Q1; R1, R5), each with its
    twin in tests/test_queued_copy_press_id.py::ParkedSendCarriesItsPressId:
    the id half of test_the_parked_op_carries_the_id_as_its_fifth_slot_and_bare_shapes_stay_bare ->
    test_two_same_text_parks_carry_their_ids_in_press_order_and_a_park_without_one_stays_three_slot;
    test_the_fifth_slot_survives_the_disk_mirror -> test_the_slot_survives_the_disk_mirror;
    test_deliver_send_batch_alone_forwards_the_fifth_slot and the id half of
    test_the_drain_hands_the_backend_the_id_and_only_a_real_todo_id -> test_the_drain_hands_each_parked_send_its_own_id.
    The two todo halves stay below, re-aimed onto the resolved op shape."""

    def test_a_parked_answer_carries_its_todo_as_the_fifth_slot_and_a_plain_send_stays_three_slot(self):
        km._compacting_now = lambda sid: True
        be = _TodoKeepingBackend()
        self.assertEqual(km._send_or_park(be, SID, "an answer alone", echo="human", user_todo="ut-2"), "parked")
        self.assertEqual(km._send_or_park(be, SID, "Re: the ask, yes", echo="human", qid=QID, user_todo="ut-1"),
                         "parked")
        self.assertEqual(km._send_or_park(be, SID, "a plain send", echo="human"), "parked")
        self.assertEqual(km._pending_ops[SID],
                         [("send", "an answer alone", "human", None, "ut-2"),
                          ("send", "Re: the ask, yes", "human", QID, "ut-1"),
                          ("send", "a plain send", "human")],
                         "the todo id is the 5th slot behind the copy's id or None; a plain send keeps the 3-slot shape")
        self.assertEqual(be.calls, [], "parked, not sent")
        self.assertEqual(self.echoes, [], "a parked send stamps no echo until it fires")

    def test_the_drain_hands_the_backend_only_a_real_todo_id(self):
        be = _TodoKeepingBackend()
        km.Sessions.backend_for = lambda sid: be
        km._pending_ops[SID] = [("send", "a", "human"),
                                ("send", "Re: the ask, yes", "human", None, "ut-9"),
                                ("send", "an answer alone", "human", None, "ut-3"),
                                ("send", "c", "human")]
        km._apply_pending_ops()
        self.assertEqual(be.calls, [("a", {}),
                                    ("Re: the ask, yes", {"user_todo": "ut-9"}),
                                    ("an answer alone", {"user_todo": "ut-3"}),
                                    ("c", {})],
                         "a real 5th slot rides as user_todo; a 3-slot send passes nothing")
        self.assertEqual(self.stamps, [("ut-9", "Re: the ask, yes"), ("ut-3", "an answer alone")],
                         "only the two real answers stamp their todo")
        self.assertNotIn(SID, km._pending_ops, "the whole run drained")


class TheMirrorMigrationInLoadPendingOps(unittest.TestCase):
    """_load_pending_ops's one-time layout migration (4e Q3; the shapes the K2 audit named): a pending-ops file
    written by the kernel before the fourth slot took the copy's press-time id put a send's user-todo id fourth and
    the client's send id fifth. A record with a todo loads as ('send', text, echo, None, todo); one with an EMPTY
    todo (the common parked record: a composer send that answered no todo) loads as the bare ('send', text, echo);
    the old fifth slot is dropped either way, so no reader takes a retired send id for a todo id. A record already
    in the current layout (an id in the echo form fourth, or None fourth with the todo fifth) loads byte for byte."""

    def setUp(self):
        km._pending_ops.clear()
        km._PENDING_OPS_FILE.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        km._pending_ops.clear()
        km._save_pending_ops()                        # an empty mirror behind us, matching the in-memory queue

    def _load(self, records):
        km._PENDING_OPS_FILE.write_text(json.dumps({SID: records}))
        return km._load_pending_ops().get(SID)

    def test_an_old_record_with_a_todo_moves_the_todo_to_the_fifth_slot_behind_none(self):
        self.assertEqual(self._load([["send", "Re", "human", "ut-1", "s-2"]]),
                         [("send", "Re", "human", None, "ut-1")],
                         "the todo id leaves the 4th slot for the 5th; the old client send id is dropped")
        self.assertEqual(self._load([["send", "an answer alone", "human", "ut-3"]]),
                         [("send", "an answer alone", "human", None, "ut-3")],
                         "the old four-slot answer (a todo and no send id) migrates the same way")

    def test_an_old_record_with_an_empty_todo_loads_as_the_bare_three_slot_send(self):
        self.assertEqual(self._load([["send", "go ahead", "human", "", "s-1"]]),
                         [("send", "go ahead", "human")],
                         "the common parked record: no todo, and the retired send id is dropped, never read as one")
        self.assertEqual(self._load([["send", "a", "human", "", "s-1"], ["command", "/compact", "human"],
                                     ["model", "opus"]]),
                         [("send", "a", "human"), ("command", "/compact", "human"), ("model", "opus")],
                         "only a send's fourth slot is read; the other kinds load as written")

    def test_a_record_in_the_current_layout_loads_byte_for_byte(self):
        qid = "echo:" + "a" * 16
        self.assertEqual(self._load([["send", "a", "human", qid]]), [("send", "a", "human", qid)],
                         "an id in the echo form fourth is the current layout: nothing moves")
        current = [("send", "an answer alone", "human", None, "ut-2"), ("send", "Re", "human", QID, "ut-1"),
                   ("command", "/compact", "human", QID), ("send", "plain", "human")]
        km._pending_ops[SID] = list(current)
        km._save_pending_ops()
        self.assertEqual(km._load_pending_ops().get(SID), current,
                         "a todo behind None or behind the copy's id, a command's id and a plain send round-trip")


# Retired 2026-09-15 with the fork's send-id identity (4e Q1; R1, R5), the twins in tests/test_queued_copy_press_id.py:
# class CancelParkedById (the parked-FIFO cancel by id) -> press_id's CancelParkedById, the same four names
#   (test_removes_exactly_the_op_carrying_the_id_of_two_wearing_the_same_words,
#   test_an_id_no_parked_op_carries_is_the_miss_and_removes_nothing, test_the_in_flight_head_is_never_the_ids_target,
#   test_an_id_less_cancel_keeps_the_index_and_body_fallback).
# class CancelBackendQueuedById (the backend-queue cancel by id) -> press_id's CancelBackendQueuedById:
#   test_the_id_wins_over_a_stale_index_and_the_shared_words, test_an_id_the_queue_does_not_hold_misses_and_touches_nothing
#   and test_an_id_less_cancel_keeps_the_body_relocation_and_the_raw_index under the same names;
#   test_a_backend_without_the_id_parameter_still_gets_the_pop ->
#   test_a_backend_whose_unqueue_takes_no_id_takes_the_index_and_body_path_never_a_refusal.
# The _QueueBackendWithoutTheIdParameter fixture that class alone used went with it.


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


class AFollowUpWithoutAnId(_DriveFixture):
    """A feed-button follow-up (askFollowUp with `nudge`) posts no copy id and stays bare: the kernel invents none,
    and parked it keeps the 3-slot shape. The chat-typed follow-up's identity cases retired 2026-09-15 with the
    fork's send-id identity (4e Q1; R1, R5), each with its twin in tests/test_queued_copy_press_id.py:
    test_a_parked_follow_up_carries_the_id_as_its_fifth_slot_and_its_cancel_finds_it ->
    TheWireCarriesTheId::test_a_follow_up_parks_its_wrapped_body_under_the_id and
    TheWireCarriesTheId::test_a_cancel_that_names_the_id_removes_that_copy_whatever_index_the_click_carried;
    test_a_delivered_follow_up_hands_the_backend_the_id ->
    ParkedSendCarriesItsPressId::test_handed_over_now_the_id_reaches_a_backend_that_identifies_its_copies_and_not_one_that_does_not."""

    FU = {"type": "askFollowUp", "itemId": SID + ":g1", "text": "and the tests?", "sid": SID}

    def test_a_feed_button_follow_up_posts_no_id_and_stays_bare(self):
        be = _TodoKeepingBackend()
        km.Sessions.backend_for = lambda sid: be
        self.assertTrue(km._drive({**self.FU, "nudge": True}, self.client))
        self.assertEqual(len(be.calls), 1, be.calls)
        self.assertEqual(be.calls[0][1], {}, "no id was posted, none is invented")
        km._compacting_now = lambda sid: True
        self.assertTrue(km._drive(self.FU, self.client))
        self.assertEqual(len(km._pending_ops[SID][0]), 3, "a bare follow-up parks in the 3-slot shape")


class _QueueBackend:
    """A backend that owns its queue (exposes unqueue) and identifies its copies the way SdkBackend does since the
    pull-in (pending_queued_meta; its unqueue takes the copy's id, so _takes_qid reads True, and locates by it the
    way SdkSession.unqueue does under its own lock): the queue keeps (text, id) pairs, a bare text carries None.
    Records every unqueue it is asked for as (index, expected body, id) and pops by id when one is named, else by
    the index re-located onto the body (SdkBackend.unqueue's drift guard)."""

    def __init__(self, pending):
        self.q = [x if isinstance(x, tuple) else (x, None) for x in pending]
        self.unqueued = []

    def pending_queued(self, sid):
        return [t for t, _ in self.q]

    def pending_queued_meta(self, sid):
        return [{"md": t, "qid": q, "qts": None} for t, q in self.q]

    def unqueue(self, sid, idx, expect=None, qid=None):
        self.unqueued.append((idx, str(expect) if expect is not None else None, qid))
        if qid:
            idx = next((i for i, (_, q) in enumerate(self.q) if q == qid), -1)
        elif expect is not None and not (0 <= idx < len(self.q) and self.q[idx][0] == expect):
            idx = next((i for i, (t, _) in enumerate(self.q) if t == expect), -1)
        return self.q.pop(idx)[0] if 0 <= idx < len(self.q) else None


class TheParkArmLooksInTheBackendQueueById(_DriveFixture):
    """The cancel on a bubble drawn as PARKED (park + qid) after the run drained: the op left the kernel FIFO for
    the backend's queue, where it dwells behind the fork's feed hold until the CLI takes the text ahead of it,
    still recallable. For an id no parked op carries, the park arm looks in the backend queue by that id before
    answering the miss, as the md-only arm does (review round 2). A fork-only arm riding the fork-only hold,
    kept and re-expressed on the copy's press-time id at the 2026-09-15 pull-in (4e Q4, whose ruling re-pins
    these four cases on qid; upstream's park arm is the single _cancel_parked call). By id only: an id-less park
    cancel keeps the single look, since a body could relocate onto a same-words neighbour there. The arm's source
    pin is tests/test_kernel_send_park.py::QueuedBubble::test_drive_routes_park_cancels."""

    def _cancel(self, be, **fields):
        km.Sessions.backend_for = lambda sid: be
        self.frames.clear()
        self.assertTrue(km._drive({"type": "cancelQueued", "id": SID, **fields}, self.client))
        res = [f for f in self.frames if f.get("type") == "cancelResult"]
        self.assertEqual(len(res), 1, self.frames)
        return res[0]

    def test_a_drained_parked_send_is_still_cancelled_from_its_park_bubble_by_id(self):
        be = _QueueBackend([("go ahead", QID)])                # the FIFO is empty: the run drained
        r = self._cancel(be, park=0, md="go ahead", qid=QID)
        self.assertTrue(r["ok"], r)
        self.assertEqual(be.unqueued, [(-1, None, QID)],
                         "found in the backend queue by id and popped there: asked by the id alone, no index, no body")
        self.assertEqual(be.q, [])

    def test_an_id_neither_queue_holds_is_the_miss_and_touches_nothing(self):
        be = _QueueBackend([("go ahead", QID_B)])              # a same-words neighbour, another send's
        r = self._cancel(be, park=0, md="go ahead", qid=QID)
        self.assertFalse(r["ok"])
        self.assertEqual(r["text"], km._cancel_miss_text("go ahead"), "the honest too-late answer")
        self.assertEqual(be.unqueued, [(-1, None, QID)], "asked by id alone; nothing popped")
        self.assertEqual(be.q, [("go ahead", QID_B)], "the neighbour survives: never a relocation onto the same words")

    def test_an_id_less_park_cancel_keeps_the_single_look(self):
        be = _QueueBackend(["go ahead"])
        r = self._cancel(be, park=0, md="go ahead")
        self.assertFalse(r["ok"], "the parked op is gone and no id names the send: the honest miss")
        self.assertEqual(be.unqueued, [], "the backend queue is not searched by body from this arm")
        self.assertEqual(be.pending_queued(SID), ["go ahead"])

    def test_a_parked_op_that_is_still_there_wins_without_consulting_the_backend(self):
        km._pending_ops[SID] = [("send", "go ahead", "human", QID)]
        be = _QueueBackend([("go ahead", QID_C)])
        r = self._cancel(be, park=0, md="go ahead", qid=QID)
        self.assertTrue(r["ok"])
        self.assertNotIn(SID, km._pending_ops)
        self.assertEqual(be.unqueued, [], "the parked FIFO is read first; the backend is not consulted")


class TheBackendUnqueueWithoutAnId(unittest.TestCase):
    """SdkSession.unqueue is the pop the kernel's cancel reaches, re-located UNDER the backend's lock: an id-less
    pop keeps its text re-location. The by-id case, test_an_id_the_session_does_not_hold_pops_nothing, retired
    2026-09-15 with the fork's send-id identity (4e Q1; R1, R5); its twin is
    tests/test_queued_copy_identity.py::TheSdkQueueTakesTheClientsId::test_unqueue_by_id_pops_the_named_copy_and_its_echo_leaving_the_same_text_other."""

    def setUp(self):
        self.state = tempfile.mkdtemp()
        reg = {"sid": SID, "name": "web", "mode": "acceptEdits", "alive": True,
               "cwd": os.path.join(self.state, "proj")}
        sbk.write_reg(self.state, SID, dict(reg))
        self.be = sbk.SdkBackend(self.state, "/bin/true", lambda *a, **k: None, log=lambda m, **k: None)
        self.s = sbk.SdkSession(self.be, dict(reg))          # never started: unqueue needs only the lock and the list

    def tearDown(self):
        self.s.shutdown()

    def test_an_id_less_pop_keeps_the_text_relocation(self):
        self.s._pending = ["alpha", "beta"]
        self.assertEqual(self.s.unqueue(2, "beta"), "beta", "a stale index relocates by text")
        self.assertEqual(self.s._pending, ["alpha"])


# Retired 2026-09-15 with the fork's send-id identity (4e Q1 and Q5; R1, R5): the kernel's landed-ids map (its cap
# and its landing note) is gone with upstream's stampBase (#1273) and the per-build pairing of the fed ledger, the
# chip and user-event fields are `qid`, and the mirror carries `qid`. The twins, all in tests/test_queued_copy_identity.py:
# class BuildSessionStampsTheIds -> TheChatCarriesTheIds:
#   test_the_queued_chips_carry_the_id_of_the_entry_or_the_parked_op_they_stand_for ->
#   test_the_queued_group_and_the_landed_atom_share_the_copys_id and
#   test_a_parked_copy_carries_the_id_it_was_pressed_with_and_a_kernel_parked_one_none_until_the_backend;
#   the in-flight echo's user-event test (its name spells the retired identifier; the pull-in log names it) ->
#   test_an_intermediate_build_between_the_feed_and_the_landing_keeps_the_pairing and
#   test_ids_ride_only_when_each_one_sits_beside_its_own_text;
#   test_the_record_that_landed_the_send_carries_its_id_and_a_folded_record_every_id ->
#   test_a_two_block_record_carries_both_copies_ids and test_the_queued_group_and_the_landed_atom_share_the_copys_id.
# class LandedIdsMap (test_the_cap_trims_the_oldest_landing_first, test_two_builds_of_one_session_never_break_each_others_walk):
#   the map has no successor; the landing pairs per build from the fed ledger (TheChatCarriesTheIds's tests above).
# class TheIdSurvivesTheRestartMirror (test_the_reseeded_echo_and_the_re_queued_entry_carry_the_id) ->
#   IdentitySurvivesTheKernelsDeath::test_the_restored_queue_and_the_reseeded_echo_keep_the_copys_id_and_the_landing_pairs_with_it.
# The _ChatBackend, _echo, _urec, _arec, _iso and _landing fixtures those classes alone used went with them.


if __name__ == "__main__":
    unittest.main()
