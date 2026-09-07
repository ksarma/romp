#!/usr/bin/env python3
"""T233 (the user 2026-09-03): the chat's close confirmation is an EVENT, not the next pusher cycle.

The false "Couldn't close X — romp still has it open" toast: the endSession WS op killed the session and
recorded the death within the same second, yet the client toasted, because the ONLY confirmation it accepts
is a tabOrder push that no longer lists the id — and until now the only sender of that was the pusher's
periodic tabs-first send, whose cycle on a loaded box runs 20-40s, past the client's 15s backstop. Now the
endSession handler sends a FRESH tab set to every ready chat client in the same handler, off-cycle, right after
the kill — same shape as the pusher's tabs-first frame, through the same per-client dedup slot.

Deterministic: the SDK backend, the liveness read, the collapse guard, the tab builder and the pusher wake
are stubbed; the frames each client receives are recorded in send order. The fresh liveness read goes
through `_tab_list_tmux` like the pusher's tabs-first send: every tabOrder frame passes the collapse guard,
since an omitted id is an authoritative teardown on the client. Synthetic ids only, hermetic state.
"""
import json
import os
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = load_source("romp_kernel_t233", os.path.join(BIN, "romp-kernel"))

ENDED = "7a7a7a7a-1111-4222-8333-000000000233"   # the session the user ends
KEPT = "7a7a7a7a-1111-4222-8333-000000000234"    # a session that stays


class FakeBackend:
    def __init__(self):
        self.calls = []
        self._owned = {ENDED, KEPT}
        self.alive = {ENDED, KEPT}

    def owns(self, sid):
        return sid in self._owned

    def kill(self, sid):
        self.calls.append(("kill", sid)); self.alive.discard(sid); return True

    def live_sessions(self):
        return {s: {"state": "idle", "since": "100", "model": "m", "effort": "", "mode": "acceptEdits"} for s in self.alive}


def _chat_client(app="chat"):
    frames = []
    c = {"app": app, "alive": True, "send": lambda s: frames.append(json.loads(s))}
    return c, frames


class CloseConfirmRidesTheKill(unittest.TestCase):
    def setUp(self):
        self.be = FakeBackend()
        self.saved = (km._sdk, km._send_to_app, km._push_soon, km._chat_tab_sessions, km._tmux_sessions,
                      km._comment_kill_all, km._record_death, list(km._clients), km._tab_list_tmux)
        km._sdk = lambda: self.be
        self.guarded = []                                  # what the collapse guard was handed, in order
        km._tab_list_tmux = lambda tmux: (self.guarded.append(tmux), tmux)[1]   # a healthy read: adopted as-is
        self.events = []                                   # every side effect, in order
        km._send_to_app = lambda app, msg: self.events.append(("app", app, msg))
        km._push_soon = lambda: self.events.append(("push_soon",))
        km._comment_kill_all = lambda sid, be: None
        km._record_death = lambda sid, ts, why: self.events.append(("death", sid, why))
        # the tab builder reads the backend's CURRENT liveness — so after the kill it lists only the survivor
        km._tmux_sessions = lambda: {s: {} for s in self.be.alive}
        km._chat_tab_sessions = lambda now, tmux: [{"sid": s, "name": "web" if s == KEPT else "api", "path": "/nonexistent"}
                                                   for s in (KEPT, ENDED) if s in tmux]
        del km._clients[:]

    def tearDown(self):
        (km._sdk, km._send_to_app, km._push_soon, km._chat_tab_sessions, km._tmux_sessions,
         km._comment_kill_all, km._record_death, clients, km._tab_list_tmux) = self.saved
        del km._clients[:]
        km._clients.extend(clients)

    def test_endSession_confirms_with_a_fresh_tab_set_in_the_same_handler(self):
        chat, frames = _chat_client("chat")
        feed, feed_frames = _chat_client("feed")
        km._clients.extend([chat, feed])
        # the frames land through the same recording send, so interleave them into the event log
        chat["send"] = lambda s: (frames.append(json.loads(s)), self.events.append(("frame", json.loads(s)["type"])))
        self.assertTrue(km._drive({"type": "endSession", "id": ENDED}, {"send": lambda s: None}))
        self.assertIn(("kill", ENDED), self.be.calls)
        kinds = [e[0] if e[0] != "frame" else "frame:" + e[1] for e in self.events]
        self.assertEqual(kinds, ["death", "app", "frame:tabOrder", "push_soon"],
                         "kill recorded → closed fan-out → the FRESH tabOrder → then the pusher wake; no cycle in between")
        tab = frames[-1]
        self.assertEqual(tab["type"], "tabOrder")
        self.assertNotIn(ENDED, tab["order"], "the ended session is gone from the confirmation")
        self.assertEqual(tab["order"], [KEPT])
        self.assertEqual([t["id"] for t in tab["tabs"]], [KEPT], "tabs meta rides along, same shape as the pusher's")
        self.assertIn("views", tab)
        self.assertEqual(feed_frames, [], "only chat clients render the tab strip")

    def test_the_confirmation_uses_the_pusher_dedup_slot_so_the_next_cycle_is_a_noop(self):
        chat, frames = _chat_client()
        km._clients.append(chat)
        self.be.alive.discard(ENDED)
        self.assertTrue(km._confirm_close_now(ENDED))
        self.assertEqual(len(frames), 1)
        self.assertIn(("taborder",), chat["sent"], "recorded under the pusher's own slot")
        self.assertTrue(km._confirm_close_now(ENDED), "idempotent")
        self.assertEqual(len(frames), 1, "an identical frame is deduped, exactly as the pusher's would be")

    def test_an_end_that_did_not_take_still_sends_the_honest_order_and_says_so(self):
        # the backend still lists the session → the fresh order still carries it. That frame is sent anyway
        # (it is the kernel's true word), and the client's own 15s backstop is what turns it into the toast.
        chat, frames = _chat_client()
        km._clients.append(chat)
        self.assertFalse(km._confirm_close_now(ENDED))
        self.assertIn(ENDED, frames[-1]["order"])

    def test_a_failing_builder_never_breaks_the_handler(self):
        chat, frames = _chat_client()
        km._clients.append(chat)
        km._chat_tab_sessions = lambda now, tmux: (_ for _ in ()).throw(RuntimeError("boom"))
        self.assertFalse(km._confirm_close_now(ENDED))
        self.assertEqual(frames, [])

    def test_the_fresh_liveness_read_goes_through_the_collapse_guard(self):
        # the guard's answer, not the raw read, is what the frame is built from: here the raw read still
        # lists the ended session (the backend has not dropped it yet) and the guard's map does not
        chat, frames = _chat_client()
        km._clients.append(chat)
        km._tab_list_tmux = lambda tmux: (self.guarded.append(tmux), {KEPT: {}})[1]
        self.assertTrue(km._confirm_close_now(ENDED))
        self.assertEqual(self.guarded, [{ENDED: {}, KEPT: {}}], "the guard was handed the raw fresh read")
        self.assertEqual(frames[-1]["order"], [KEPT], "…and the frame carries the guard's map")

    def test_a_guard_with_nothing_trustworthy_sends_no_frame(self):
        # a boot-time collapse with no carry: the pusher skips its tabOrder for the cycle rather than assert an
        # empty board, and so does the confirmation — an omitting frame is the mass teardown the guard refuses
        chat, frames = _chat_client()
        km._clients.append(chat)
        km._tab_list_tmux = lambda tmux: None
        self.assertFalse(km._confirm_close_now(ENDED), "unconfirmed: the client's own backstop says so")
        self.assertEqual(frames, [], "no frame at all — never one that omits every tmux tab")
        self.assertNotIn("sent", chat)

    def test_a_chat_page_behind_the_ready_gate_or_dead_gets_no_frame_and_a_ready_one_does(self):
        # READY_GATE_CAP: a page that announced the cap is held until its bundle says `ready`; the pusher
        # (_push) and _push_session_now filter their tabOrder sends on _client_ready and alive. This sender
        # sent to every chat client, so a page still behind the gate received a frame before its bundle
        # had asked for one, and a client already marked dead was written to
        held, held_frames = _chat_client(); held["ready"] = False
        dead, dead_frames = _chat_client(); dead["alive"] = False
        ready, ready_frames = _chat_client()
        km._clients.extend([held, dead, ready])
        self.be.alive.discard(ENDED)
        self.assertTrue(km._confirm_close_now(ENDED))
        self.assertEqual(held_frames, [], "a page whose bundle has not said `ready` is held, as every other tabOrder sender holds it")
        self.assertNotIn("sent", held, "…and nothing is recorded under its dedup slot, so its first real frame is not deduped away")
        self.assertEqual(dead_frames, [], "a dead client is skipped, as _push_session_now skips it")
        self.assertEqual(len(ready_frames), 1, "the ready client gets the confirmation")
        self.assertEqual(ready_frames[0]["type"], "tabOrder")
        self.assertEqual(ready_frames[0]["order"], [KEPT])

    def test_the_call_site_comment_no_longer_claims_recently_died_tabs(self):
        src = open(os.path.join(BIN, "romp-kernel")).read() if not os.path.islink(os.path.join(BIN, "romp-kernel")) \
            else open(os.path.realpath(os.path.join(BIN, "romp-kernel"))).read()
        self.assertNotIn("living + recently-died-while-shown, minus ×-hidden", src)
        self.assertIn("live + explicitly kept-open (read-only reopened dead) — nothing else", src)
        self.assertIn("_confirm_close_now(sid)      # the kill IS the event", src)


if __name__ == "__main__":
    unittest.main()
