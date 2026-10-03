#!/usr/bin/env python3
"""T289: a comment CREATE is idempotent on its own identity.

A create parked for transcript lag is retried by BOTH the kernel (the pusher's _retry_parked_creates) and
the client (its frame-keyed re-post), and a create whose ack was lost is sent again by the popover; before
this the second copy either collided on its explicit name and was refused with the create toast the user
saw, or, with the name now left to the kernel, would have minted a SECOND thread for one comment. The
kernel remembers each create it completed and answers a repeat with the SAME thread's ack; a lag-parked
create is parked once.

The identity is the client's createId when the frame carries one: the popover mints it at the send gesture
and every re-post of that gesture carries the same one, so a repeat is exactly a frame with an id the kernel
has seen. Keyed on the words instead (parent sid, anchor uuid, passage, text), the memo also swallowed a
DELIBERATE second comment in the same words on the same passage: one thread, two acks, the second name
nowhere on disk (review of the memo, 2026-09-09). A frame without a createId still keys on the words.
SYNTHETIC fixtures."""
import contextlib
import io
import json
import os
import shutil
import tempfile
import time
import unittest
from datetime import datetime, timezone
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
jd = load_source("romp_judge", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))

PARENT = "aaaaaaaa-1111-2222-3333-444444444444"


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat().replace("+00:00", "Z")


def uline(t, text, uuid, parent=None):
    return {"type": "user", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent, "promptSource": "typed",
            "message": {"role": "user", "content": text}}


def aline(t, text, uuid, parent=None):
    return {"type": "assistant", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": text}]}}


class FakeBackend:
    def __init__(self):
        self.calls = []

    def fork(self, name, parent_sid, cut_uuid="", bg="", fg="", sid=None, thread_of="", model="", effort="", fast=""):
        self.calls.append(("fork", name)); return sid

    def connect(self, sid):
        return True

    def send(self, sid, text):
        return True

    def kill(self, sid):
        return True

    def rename(self, sid, name):
        self.calls.append(("rename", name)); return True

    def promote_thread(self, sid, name, bg="", fg=""):
        self.calls.append(("promote", name)); return True


class CreateIsIdempotent(unittest.TestCase):
    def setUp(self):
        self._saved = jd.STATE
        self._saved_proj = jd.PROJECTS
        self._td = tempfile.mkdtemp()
        jd._rebind_state(Path(self._td))
        jd.PROJECTS = Path(self._td) / "projects"
        jd._discover_cache.clear()
        jd._PARSE_CACHE.clear(); jd._CHAIN_MEMO.clear()
        km._thread_msgs_cache.clear()
        # the create memos start empty as well (review, 2026-09-09): the tests reuse the same create ids
        # under one parent sid, so an id a previous test noted would name a thread id this test's fresh
        # store can hold too, and a fresh gesture here would be answered as a repeat; random thread ids
        # keep that from happening by chance today, and the clears make the order not matter. The noted
        # creates are the memo a passing test leaves behind; the in-flight set and the parked list are
        # empty at the end of every passing test, so their clears keep a test that failed part-way from
        # failing the next one too. Under the lock every writer of the three memos takes.
        with km._create_lock:
            km._recent_creates.clear(); km._inflight_creates.clear(); km._parked_creates.clear()
        self.now = int(time.time())
        cdir = str(Path(self._td) / "work")
        self.proj = jd._proj_dir(cdir)
        self.proj.mkdir(parents=True, exist_ok=True)
        jd.NAMES.mkdir(parents=True, exist_ok=True)
        jd.SDKDIR.mkdir(parents=True, exist_ok=True)
        (jd.NAMES / PARENT).write_text("web\t%s\t\t\n" % cdir)   # the names row: the refusal names the parent by it
        self.be = FakeBackend()
        self._saved_fns = (km._sdk, km.Sessions.backend_for, km._sdk_ready, km._sessions, km._reveal_chat_for,
                           km._push_session_now, km._live_map, km._kernel_knows)
        km._sdk = lambda: None
        km._kernel_knows = lambda sid: sid == PARENT     # the dispatcher's ownership guard is not under test
        self._saved_km_names = km.NAMES
        km.NAMES = jd.NAMES                              # the kernel's own binding of the names dir follows the rebind
        km.Sessions.backend_for = staticmethod(lambda sid: self.be)
        km._sdk_ready = lambda: True
        km._live_map = lambda: {}
        t = self.now - 600
        p = self.proj / (PARENT + ".jsonl")
        p.write_text("\n".join(json.dumps(r) for r in [
            uline(t, "how should the notes-api retry loop back off?", "u1"),
            aline(t + 5, "Use exponential backoff with a jitter of ten percent.", "a1", parent="u1")]) + "\n")
        km._sessions = lambda now, window=None, forks=True: [
            {"sid": PARENT, "name": "web", "path": str(p), "mtime": self.now}]
        km._reveal_chat_for = lambda client, msg: None
        km._push_session_now = lambda sid: None
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s)), "app": "chat"}

    def tearDown(self):
        (km._sdk, km.Sessions.backend_for, km._sdk_ready, km._sessions, km._reveal_chat_for,
         km._push_session_now, km._live_map, km._kernel_knows) = self._saved_fns
        km.NAMES = self._saved_km_names
        jd._rebind_state(self._saved)
        jd.PROJECTS = self._saved_proj
        shutil.rmtree(self._td, ignore_errors=True)

    def _drive(self, msg):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            handled = km._drive(msg, self.client)
        return handled, buf.getvalue()

    def _warns(self):
        return [f["text"] for f in self.sent if f.get("type") == "warn"]

    def _create(self, text="Why jitter at all?", uuid="a1", name="", create_id=None):
        msg = {"type": "commentCreate", "id": PARENT, "uuid": uuid, "exact": "exponential backoff",
               "text": text, "name": name}
        if create_id is not None:
            msg["createId"] = create_id                 # the client's per-gesture stamp (absent from an older client)
        return self._drive(msg)

    def _rows(self):
        return km._load_comments(PARENT).get("threads") or []

    def _acks(self):
        return [f for f in self.sent if f.get("type") == "commentCreated"]

    def test_the_same_create_twice_yields_one_thread_and_two_acks_naming_it(self):
        self._create(); self._create()
        self.assertEqual(len(self._rows()), 1, "one comment, one thread")
        acks = self._acks()
        self.assertEqual(len(acks), 2, "the repeat is answered, so the popover adopts the thread")
        self.assertEqual(acks[0]["tid"], acks[1]["tid"])
        self.assertEqual(self._warns(), [])

    def test_a_different_comment_on_the_same_passage_is_a_second_thread(self):
        self._create("Why jitter at all?"); self._create("And the cap?")
        self.assertEqual(len(self._rows()), 2)
        self.assertEqual(len({a["tid"] for a in self._acks()}), 2)

    def test_a_lag_parked_create_is_parked_once(self):
        # the anchor is not in the transcript yet: the create parks, the client hears a transient nack and
        # re-posts on the next frame — the park must not double
        km._parked_creates.clear()
        self._create(uuid="a9"); self._create(uuid="a9")
        nacks = [f for f in self.sent if f.get("type") == "commentCreateFailed"]
        self.assertEqual(len(nacks), 2)
        self.assertTrue(all(n["transient"] for n in nacks))
        self.assertEqual(len(km._parked_creates), 1, "one parked copy for one create")
        km._parked_creates.clear()

    def test_a_parked_create_that_landed_answers_the_clients_repost_with_the_same_thread(self):
        km._parked_creates.clear()
        self._create(uuid="a9")
        self.assertEqual(len(km._parked_creates), 1)
        # the transcript catches up: the pusher's retry lands the thread
        p = Path(km._sessions(0)[0]["path"])
        with p.open("a") as fh:
            fh.write(json.dumps(aline(self.now - 300, "Add a jitter to the backoff.", "a9", parent="a1")) + "\n")
        km._retry_parked_creates()
        self.assertEqual(km._parked_creates, [])
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        # the client's own re-post of the same create arrives a beat later: the same thread, no second one
        self._create(uuid="a9")
        self.assertEqual(len(self._rows()), 1, "the repeat is the same comment")
        acks = self._acks()
        self.assertTrue(acks and acks[-1]["tid"] == rows[0]["tid"], acks)
        self.assertEqual(self._warns(), [])

    def test_a_repost_arriving_while_the_pushers_retry_creates_is_not_a_second_thread(self):
        # THE RACE (review, 2026-09-09): the pusher sends the chat frame before it retries parked creates,
        # the client re-posts the create on that frame, and the re-post lands on a WS thread while the
        # pusher's own create is in flight — neither copy is noted yet, so both minted. The identity must
        # be reserved before the create runs, on both doors, and the pusher must consult the memo.
        import threading
        km._parked_creates.clear()
        self._create(uuid="a9")                       # lag-parked (the anchor is not on disk yet)
        self.assertEqual(len(km._parked_creates), 1)
        p = Path(km._sessions(0)[0]["path"])
        with p.open("a") as fh:
            fh.write(json.dumps(aline(self.now - 300, "Add a jitter to the backoff.", "a9", parent="a1")) + "\n")
        real = km._comment_create
        seen = {"n": 0, "nested": None}

        def racing(*a, **k):
            seen["n"] += 1
            if seen["n"] == 1:
                # the pusher's create is in flight: the client's re-post arrives on another thread NOW
                before = len(self.sent)
                t = threading.Thread(target=lambda: self._create(uuid="a9"))
                t.start(); t.join(10)
                seen["nested"] = self.sent[before:]
            return real(*a, **k)
        km._comment_create = racing
        try:
            km._retry_parked_creates()
        finally:
            km._comment_create = real
        self.assertEqual(seen["n"], 1, "the re-post never reached a second create: %r" % (seen["nested"],))
        self.assertEqual(len(self._rows()), 1, "one comment, one thread")
        kinds = [f.get("type") for f in (seen["nested"] or [])]
        self.assertTrue("commentCreateFailed" in kinds or "commentCreated" in kinds,
                        "the re-post is answered while the pusher's copy is in flight (a typed transient nack, or the ack): %r" % kinds)
        self.assertEqual(km._parked_creates, [])
        self.assertEqual(self._warns(), [])

    def test_a_repeat_after_the_thread_was_resolved_is_a_new_comment_not_a_dropped_one(self):
        # a resolved (or merged, or promoted) thread cannot take a message: answering a same-worded comment
        # with its ack would drop the user's words silently (review, 2026-09-09)
        self._create()
        tid = self._acks()[0]["tid"]
        self.assertIsNone(km._comment_resolve(PARENT, tid))
        self._create()
        rows = self._rows()
        self.assertEqual(len(rows), 2, "a second, open thread for the re-asked comment")
        self.assertEqual(self._warns(), [])

    def test_a_fresh_gesture_in_the_same_words_on_the_same_passage_is_a_second_thread(self):
        # the user posts a comment, takes the ack, and posts the SAME words on the same passage again under
        # another name: two gestures, two comments. Keyed on the words alone the memo answered the second
        # with the first thread's ack, and the second name was nowhere on disk (review, 2026-09-09).
        self._create(name="first-look", create_id="g-1111")
        first = self._acks()[-1]["tid"]
        self._create(name="second-look", create_id="g-2222")
        rows = self._rows()
        self.assertEqual(len(rows), 2, "two gestures are two comments, whatever their words")
        self.assertEqual(sorted(r["name"] for r in rows), ["first-look", "second-look"], "both names on disk")
        acks = self._acks()
        self.assertEqual(len(acks), 2)
        self.assertNotEqual(acks[1]["tid"], first, "the second ack names the second thread")
        self.assertEqual(self._warns(), [])

    def test_a_retried_frame_with_the_same_create_id_is_one_thread_answered_twice(self):
        # the re-post side of the same rule: a frame the client sends again (a lost ack, a lag retry) carries
        # the id it minted at the gesture, and the kernel answers it with the thread that gesture made
        self._create(create_id="g-1111"); self._create(create_id="g-1111")
        self.assertEqual(len(self._rows()), 1, "one gesture, one thread")
        acks = self._acks()
        self.assertEqual(len(acks), 2, "the repeat is answered, so the popover adopts the thread")
        self.assertEqual(acks[0]["tid"], acks[1]["tid"])
        self.assertEqual(self._warns(), [])

    def test_a_fresh_gesture_after_a_parked_create_landed_is_a_second_thread_and_its_repost_is_not(self):
        # the parked copy carries the gesture's id through the pusher's retry: the client's re-post of THAT
        # gesture is the same comment, and a new gesture in the same words a moment later is a new one
        km._parked_creates.clear()
        self._create(uuid="a9", create_id="g-1111")
        self.assertEqual(len(km._parked_creates), 1)
        p = Path(km._sessions(0)[0]["path"])
        with p.open("a") as fh:
            fh.write(json.dumps(aline(self.now - 300, "Add a jitter to the backoff.", "a9", parent="a1")) + "\n")
        km._retry_parked_creates()
        self.assertEqual(km._parked_creates, [])
        landed = self._rows()
        self.assertEqual(len(landed), 1)
        self._create(uuid="a9", create_id="g-1111")   # the client's own re-post of the parked gesture
        self.assertEqual(len(self._rows()), 1, "the re-post is the same comment")
        self.assertEqual(self._acks()[-1]["tid"], landed[0]["tid"])
        self._create(uuid="a9", create_id="g-2222")   # a new gesture, same words, same passage
        rows = self._rows()
        self.assertEqual(len(rows), 2, "a fresh gesture is a second thread")
        self.assertNotEqual(self._acks()[-1]["tid"], landed[0]["tid"])
        self.assertEqual(self._warns(), [])

    def test_two_gestures_in_the_same_words_are_both_parked_while_the_anchor_lags(self):
        # two comments posted before the anchor reached the transcript park separately and land as two
        # threads; the same gesture posted twice still parks once
        km._parked_creates.clear()
        self._create(uuid="a9", create_id="g-1111"); self._create(uuid="a9", create_id="g-1111")
        self.assertEqual(len(km._parked_creates), 1, "one parked copy for one gesture")
        self._create(uuid="a9", create_id="g-2222")
        self.assertEqual(len(km._parked_creates), 2, "a second gesture is its own parked create")
        nacks = [f for f in self.sent if f.get("type") == "commentCreateFailed"]
        self.assertEqual(len(nacks), 3)
        self.assertTrue(all(n["transient"] for n in nacks))
        p = Path(km._sessions(0)[0]["path"])
        with p.open("a") as fh:
            fh.write(json.dumps(aline(self.now - 300, "Add a jitter to the backoff.", "a9", parent="a1")) + "\n")
        km._retry_parked_creates()
        self.assertEqual(km._parked_creates, [])
        self.assertEqual(len(self._rows()), 2, "both gestures landed as threads")
        self.assertEqual(self._warns(), [])

    def test_a_frame_without_a_create_id_still_keys_on_the_words(self):
        # an older client sends no id: the words identity stands for it, and a stamped frame in the same
        # words is not answered from the words memo (nor the other way round)
        self._create(); self._create()
        self.assertEqual(len(self._rows()), 1)
        self._create(create_id="g-1111")
        self.assertEqual(len(self._rows()), 2, "a stamped gesture is not a repeat of an unstamped one")
        self._create()
        self.assertEqual(len(self._rows()), 2, "and the unstamped repeat still answers from its own memo")
        self.assertEqual(self._warns(), [])

    def test_a_repost_of_a_parked_gesture_is_refused_at_the_door_before_the_create_runs(self):
        # the busy nack for a re-post of a parked gesture comes from the reservation, which finds the parked
        # copy by the gesture's id, so the create never runs a second time (compared by its words instead, a
        # stamped re-post would go free, re-run the create into the lag and rely on the park-once check)
        km._parked_creates.clear()
        self._create(uuid="a9", create_id="g-1111")
        self.assertEqual(len(km._parked_creates), 1)
        real = km._comment_create
        calls = []

        def counting(*a, **k):
            calls.append(a)
            return real(*a, **k)
        km._comment_create = counting
        try:
            self._create(uuid="a9", create_id="g-1111")
        finally:
            km._comment_create = real
        self.assertEqual(calls, [], "the re-post is busy at the door; no second create")
        nacks = [f for f in self.sent if f.get("type") == "commentCreateFailed"]
        self.assertEqual(len(nacks), 2)
        self.assertTrue(all(n["transient"] for n in nacks))
        self.assertEqual(len(km._parked_creates), 1)
        km._parked_creates.clear()

    def test_a_repost_landing_between_the_doors_release_and_its_park_is_parked_once(self):
        # the door releases its reservation before it parks, and the park-once check covers that window: a
        # re-post of the same gesture on another server thread lands in it, runs the create into the lag and
        # parks first; this door then finds that parked copy by the gesture's id and parks no twin (the other
        # door runs whole inside the window here, in place of a second thread, so the order is exact)
        km._parked_creates.clear()
        real = km._release_create
        raced = []

        def release_then_race(key):
            real(key)
            if not raced:
                raced.append(key)
                self._create(uuid="a9", create_id="g-1111")
        km._release_create = release_then_race
        try:
            self._create(uuid="a9", create_id="g-1111")
        finally:
            km._release_create = real
        self.assertEqual(len(raced), 1)
        self.assertEqual(len(km._parked_creates), 1, "one parked copy for one gesture, whichever door parked it")
        nacks = [f for f in self.sent if f.get("type") == "commentCreateFailed"]
        self.assertEqual(len(nacks), 2)
        self.assertTrue(all(n["transient"] for n in nacks))
        km._parked_creates.clear()

    def test_an_answered_repeat_is_said_in_the_kernel_log(self):
        self._create()
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            km._drive({"type": "commentCreate", "id": PARENT, "uuid": "a1", "exact": "exponential backoff",
                       "text": "Why jitter at all?", "name": ""}, self.client)
        self.assertIn("comment create repeated", buf.getvalue(), "a collapse is visible, never silent")

    # ── every answer names the gesture it answers (the chat popover's same-message create collision) ─────
    # The popover holds each create by the id its send gesture minted. Two creates on one message share the
    # anchor uuid, so an answer that named only the uuid settled whichever of them the popover held under it:
    # the second send's hold overwrote the first's, the first's ack retired the second's, and the ack adopted
    # the thread into whatever create dialog was open. Every door that answers a create echoes the id.
    def _answers(self):
        return [(f["type"], f.get("createId"), f.get("transient")) for f in self.sent
                if f.get("type") in ("commentCreated", "commentCreateFailed")]

    def test_every_answer_to_a_stamped_create_echoes_its_create_id(self):
        self._create(create_id="g-1111")                                   # created
        self._create(create_id="g-1111")                                   # a re-post: the same thread, answered again
        taken = self._rows()[0]["name"]
        self._create(text="And the cap?", name=taken, create_id="g-2222")  # refused: the name is taken
        self._create(uuid="a9", create_id="g-3333")                        # the anchor lags: parked, transient
        self._create(uuid="a9", create_id="g-3333")                        # a re-post while parked: busy, transient
        self.assertEqual(self._answers(), [
            ("commentCreated", "g-1111", None), ("commentCreated", "g-1111", None),
            ("commentCreateFailed", "g-2222", False),
            ("commentCreateFailed", "g-3333", True), ("commentCreateFailed", "g-3333", True)],
            "the success, the repeat, the refusal, the lag nack and the busy nack each name the gesture they answer")
        p = Path(km._sessions(0)[0]["path"])
        with p.open("a") as fh:
            fh.write(json.dumps(aline(self.now - 300, "Add a jitter to the backoff.", "a9", parent="a1")) + "\n")
        with km._clients_lock:
            km._clients.append(self.client)
        try:
            km._retry_parked_creates()                                     # the pusher lands the parked create
        finally:
            with km._clients_lock:
                km._clients[:] = [c for c in km._clients if c is not self.client]
        self.assertEqual(self._answers()[-1], ("commentCreated", "g-3333", None),
                         "the pusher's ack for a parked create names the gesture it was parked under")
        self.assertEqual(km._parked_creates, [])

    def test_an_unstamped_create_is_answered_with_an_empty_create_id(self):
        # a create that carries no id (a page from before the id) is answered with "". A page routes an answer whose
        # id names a create it minted in echo mode to its echo-mode handling, which settles that create. Every other
        # answer goes to its handling of a kernel without the echo, by the message's uuid: "" and an id the page did
        # not mint in echo mode settle none of its echo-mode creates and show it the echo; an answer with no createId
        # key (a kernel older than the echo) shows it no echo, and first hands its echo-mode creates still out on that
        # host back to the person, with no re-post
        self._create()
        taken = self._rows()[0]["name"]
        self._create(text="And the cap?", name=taken)
        self._create(uuid="a9")
        self.assertEqual(self._answers(), [("commentCreated", "", None), ("commentCreateFailed", "", False),
                                           ("commentCreateFailed", "", True)])
        km._parked_creates.clear()

    def test_a_create_refused_at_the_drive_gate_is_answered_as_a_refusal_naming_its_gesture(self):
        # a create addressed to a session this kernel does not have is refused at the drive gate (the modal, the
        # row in undelivered.jsonl); it is also answered as the create door answers a refusal, so a page that sent
        # it from an echo-mode dialog hands that dialog back with its words instead of leaving it busy until it is
        # closed; a main-mode dialog stays busy until closed, as on main (main hands back only on a warn, and the
        # gate sends the modal, not a warn)
        foreign = "bbbbbbbb-1111-2222-3333-444444444444"
        handled, _ = self._drive({"type": "commentCreate", "id": foreign, "uuid": "a1", "exact": "exponential backoff",
                                  "text": "Why jitter at all?", "name": "", "createId": "g-4444"})
        self.assertTrue(handled, "the gate consumed the create")
        self.assertEqual([f["type"] for f in self.sent], ["err", "commentCreateFailed"],
                         "the modal, then the typed refusal the popover settles its create by")
        failed = self.sent[-1]
        self.assertEqual((failed.get("id"), failed.get("uuid"), failed.get("transient"), failed.get("createId")),
                         (foreign, "a1", False, "g-4444"), "a real refusal, naming the gesture it refuses")
        self._drive({"type": "commentCreate", "id": foreign, "uuid": "a1", "exact": "exponential backoff",
                     "text": "And the cap?", "name": ""})
        self.assertEqual(self.sent[-1].get("createId"), "", "an unstamped create refused at the gate is answered with an empty id")
        self.assertEqual(self._rows(), [], "nothing was created")

    def test_the_kernel_announces_that_its_create_answers_echo_the_create_id(self):
        # the caps frame (in reply to a page's ready) and /version carry commentCreateId: a page opens a comment dialog
        # in echo mode (its create settled by the answer that names it) only for a session whose kernel is last known to
        # echo it (the createIdEcho marker on its connection's connect push, this cap, or the key on a create answer), and
        # in main mode, main's handling, otherwise
        self.assertIn("commentCreateId", km.KERNEL_WS_CAPS)
        self.assertIn("commentCreateId", km._version_info()["caps"])



# ── every connection's connect push carries the marker ──────────────────────────────────────────────────────────
# A page re-posts an echo-mode comment create still held from an earlier connection only on a connection whose first
# strip carries createIdEcho (the frame every chat connection is sent ahead of its sessions, _tab_order_frame), and a
# connection whose first strip lacks it makes the page hand those creates back to the person, with no re-post
# (render.ts noteConnectPush, handBackEchoCreates). So the marker must ride the first strip of EVERY connection, whichever sender
# serves it: the ready arm's connect push for a fresh page and for a relay's first dial, the pusher's cycle for a
# redial (a page's or a relay's), and the two off-cycle senders, either of which can be a redial's first strip.
MARK_SIDS = ("cccccccc-1111-2222-3333-444444444441", "cccccccc-1111-2222-3333-444444444442")


class _ReadySelf:
    """The handler's `self` for _dispatch_ws: the ready arm reaches only _push_one, whose real body is
    _push([client], connect=True)."""
    def _push_one(self, client):
        km._push([client], connect=True)


class ConnectPushMarker(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.mkdtemp()
        # the ready arm reaches km._sdk() under the sandboxed jd.STATE below, which builds the kernel's backend singleton
        # over this directory: kept here and put back in tearDown before the directory goes
        self._sdk_backend = km._sdk_backend
        self._saved = (km._chat_tab_sessions, km._live_map, km._cached_feed, km.build_session, km._comments_frame,
                       km._push_subagents, km.NAMES, km.jd.STATE, list(km._clients))
        km._chat_tab_sessions = lambda now, live_map: [
            {"sid": sid, "name": "web", "path": os.path.join(self._td, sid + ".jsonl"), "anchor": sid} for sid in MARK_SIDS]
        km._live_map = lambda: {}
        km._cached_feed = lambda *a, **k: None
        km.build_session = lambda sid, now, live_map=None, **kw: {
            "type": "session", "id": sid, "name": "web", "events": [], "status": {"state": "idle", "sinceEpoch": None}, "ledger": None}
        km._comments_frame = lambda sid, live_map=None: None
        km._push_subagents = lambda clients, now, live_map: None
        km.NAMES = Path(self._td) / "names"
        km.NAMES.mkdir()
        km.jd.STATE = Path(self._td) / "state"
        km.jd.STATE.mkdir(parents=True, exist_ok=True)
        km._built_chat.clear()
        km._prev_chat_events.clear()
        km._prev_chat_ledger.clear()
        del km._clients[:]

    def tearDown(self):
        (km._chat_tab_sessions, km._live_map, km._cached_feed, km.build_session, km._comments_frame,
         km._push_subagents, km.NAMES, km.jd.STATE, clients) = self._saved
        del km._clients[:]
        km._clients.extend(clients)
        km._built_chat.clear()
        km._prev_chat_events.clear()
        km._prev_chat_ledger.clear()
        km._sdk_backend = self._sdk_backend
        shutil.rmtree(self._td, ignore_errors=True)

    @staticmethod
    def _client(**kw):
        frames = []
        c = {"app": "chat", "alive": True, "sent": {}, "send": lambda s: frames.append(json.loads(s)), "_frames": frames}
        c.update(kw)
        return c

    def _first_strip(self, c):
        """The client's frames up to and including its first strip: the strip must come before any session frame and
        before the caps frame, and it must carry the marker."""
        types = [f["type"] for f in c["_frames"]]
        self.assertIn("tabOrder", types, "the connection got a strip")
        at = types.index("tabOrder")
        self.assertNotIn("session", types[:at], "no session frame ahead of the connection's first strip")
        self.assertNotIn("caps", types[:at], "and no caps frame ahead of it")
        return c["_frames"][at]

    def test_a_fresh_pages_connect_push_carries_the_marker_on_its_first_strip(self):
        c = self._client(caps={km.READY_GATE_CAP}, ready=False)        # a kernel-served pane, held until its bundle's ready
        km.Handler._dispatch_ws(_ReadySelf(), {"type": "ready", "proto": 2}, c)
        self.assertIs(self._first_strip(c).get("createIdEcho"), True)
        self.assertEqual([f["type"] for f in c["_frames"]][-1], "caps", "the caps frame still comes last, after the pushes")

    def test_a_relays_first_dial_carries_the_marker_on_its_first_strip(self):
        c = self._client(kind="relay")                                  # federation's dial through the splice: ready from accept
        km.Handler._dispatch_ws(_ReadySelf(), {"type": "ready", "proto": 2}, c)   # federation posts the page's ready on a first dial
        self.assertIs(self._first_strip(c).get("createIdEcho"), True)

    def test_a_redial_served_by_the_pushers_cycle_carries_the_marker_on_its_first_strip(self):
        for kw in ({"reconnect": True, "redial": True, "active": MARK_SIDS[0]},                       # a pane's redial
                   {"reconnect": True, "redial": True, "kind": "relay", "dietSkeleton": True}):     # a relay's
            c = self._client(**kw)
            km._push([c])                                               # the cycle the redial's handshake woke
            self.assertIs(self._first_strip(c).get("createIdEcho"), True, kw)

    def test_the_off_cycle_strips_carry_the_marker_too_since_either_can_be_a_redials_first(self):
        c = self._client(reconnect=True, redial=True, active=MARK_SIDS[0])
        km._clients.append(c)
        self.assertTrue(km._confirm_close_now("cccccccc-1111-2222-3333-444444444449"))   # a close confirmation, first
        self.assertIs(self._first_strip(c).get("createIdEcho"), True, "the close confirmation's strip")
        c2 = self._client(reconnect=True, redial=True, active=MARK_SIDS[0])
        km._clients[:] = [c2]
        km._push_session_now(MARK_SIDS[1])                             # an off-cycle session push, first
        self.assertIs(self._first_strip(c2).get("createIdEcho"), True, "the off-cycle session push's strip")

    def test_every_strip_the_builder_makes_carries_the_marker(self):
        # the one builder: no sender can send a strip without it, a client's frame and the bare shape alike
        self.assertIs(km._tab_order_frame(list(MARK_SIDS), [], set(MARK_SIDS)).get("createIdEcho"), True)
        self.assertIs(km._tab_order_frame(list(MARK_SIDS), [], set(), self._client(skeletonOrder=[], skeleton=set())).get("createIdEcho"), True)


if __name__ == "__main__":
    unittest.main()
