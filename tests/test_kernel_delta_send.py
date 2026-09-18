"""Diff-based delta-send for the chat (the user 2026-06-25, who wanted to stop re-sending what didn't change).

The chat pusher used to send the FULL events array on every change (~8MB for a big transcript). Now the
whole transcript stays resident in the browser (instant scrollback), but a caught-up client receives only
the CHANGED SUFFIX as {type:"chatTail", from, events}. The suffix is found by DIFFING the freshly-built
events against the previous build — robust to _hydrate_postal turning one event into several cards mid-array,
which a fixed window would mishandle. A fresh connect / fork / behind-the-change client still gets the full
{type:"session"} so it always renders from a correct base. Source-level + behavioural pins.
"""
import io
import json
import os
import sys
import time
import unittest
from romp_load import load_source
from unittest import mock
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))


def _client():
    sent = []
    return {"send": sent.append, "sent": {}}, sent


def _last(sent):
    return json.loads(sent[-1])


class ChatDiffTest(unittest.TestCase):
    def test_diff_finds_the_exact_changed_suffix(self):
        a = [{"uuid": "1", "x": 1}, {"uuid": "2", "x": 2}]
        self.assertEqual(km._chat_diff([], a), 0, "no prior build → full (from 0)")
        self.assertEqual(km._chat_diff(a, a + [{"uuid": "3"}]), 2, "append → from = old length")
        # a tool output filling an EARLIER card changes that card in place → from = its index
        filled = [{"uuid": "1", "x": 1}, {"uuid": "2", "x": 2, "output": "done"}, {"uuid": "3"}]
        self.assertEqual(km._chat_diff(a + [{"uuid": "3"}], filled), 1, "in-place fill → from = that index")
        self.assertEqual(km._chat_diff(a, list(a)), len(a), "no change → from = length (empty suffix)")

    def test_the_same_list_object_is_answered_without_a_walk(self):
        """The served-tab case: _push re-stores the same events list as the baseline (the cache hit keeps the
        payload, and the non-connect push writes m["events"] back into _prev_chat_events), so the next cycle's
        diff receives ONE object as both arguments. The answer is fixed (len, the empty suffix) and the walk
        that found it visited every event of every served tab per cycle (the design's stage 1 exact return,
        2026-09-18). A list that counts its reads proves the walk is gone: zero reads, where the loop read
        both sides of every index."""
        class Counting(list):
            reads = 0

            def __getitem__(self, i):
                Counting.reads += 1
                return list.__getitem__(self, i)
        same = Counting({"uuid": str(i), "x": i} for i in range(50))
        self.assertEqual(km._chat_diff(same, same), 50, "the empty suffix: from = the length")
        self.assertEqual(Counting.reads, 0, "the same object on both sides is answered without reading an event")
        # the walk stands for everything else: an equal copy is read (identity fails, values compare), and the
        # answer is unchanged
        copy = Counting(same)
        Counting.reads = 0
        self.assertEqual(km._chat_diff(same, copy), 50)
        self.assertEqual(Counting.reads, 100, "a distinct list is still walked, both sides of every index")
        empty = Counting()
        self.assertEqual(km._chat_diff(empty, empty), 0, "no prior build: a full send, as before")


class SendChatTest(unittest.TestCase):
    def _m(self, sid, events):
        return {"type": "session", "id": sid, "name": sid, "events": events,
                "status": {"state": "working"}, "ledger": None, "color": None}

    def test_new_client_gets_the_full_session_then_appends_arrive_as_a_tail(self):
        a = [{"uuid": "1"}, {"uuid": "2"}]
        c, sent = _client()
        km._send_chat(c, self._m("S", a), None, 0, False)             # first send → full
        self.assertEqual(_last(sent)["type"], "session")
        b = a + [{"uuid": "3"}]
        km._send_chat(c, self._m("S", b), None, 2, False)             # caught up, appended → tail from 2
        tail = _last(sent)
        self.assertEqual(tail["type"], "chatTail")
        self.assertEqual(tail["from"], 2)
        self.assertEqual([e["uuid"] for e in tail["events"]], ["3"])
        self.assertEqual(tail["total"], 3)
        self.assertIn("status", tail)                          # the chip rides along on the delta

    def test_a_tool_fill_re_sends_from_that_cards_index(self):
        b = [{"uuid": "1"}, {"uuid": "2"}, {"uuid": "3"}]
        c, sent = _client()
        km._send_chat(c, self._m("S", b), None, 0, False)             # full
        filled = [{"uuid": "1"}, {"uuid": "2", "output": "done"}, {"uuid": "3"}]
        km._send_chat(c, self._m("S", filled), None, 1, False)        # card #2 filled → tail FROM 1
        tail = _last(sent)
        self.assertEqual(tail["type"], "chatTail")
        self.assertEqual(tail["from"], 1)
        self.assertEqual([e.get("output") for e in tail["events"]], ["done", None])

    def test_a_flag_only_change_rides_an_empty_tail_carrying_the_flags(self):
        # the user 2026-09-11: a bell flipped in one split column reached the other only with its next FULL frame.
        # Unchanged events diff to len(prev) → an empty suffix; the flags ride it as the status does
        c, sent = _client()
        a = [{"uuid": "1"}, {"uuid": "2"}]
        km._send_chat(c, self._m("S", a), None, 0, False)             # full
        m2 = dict(self._m("S", a), notify=True, hideFromFeed=False, postalServiceOff=True)
        km._send_chat(c, m2, None, km._chat_diff(a, a), False)
        t = _last(sent)
        self.assertEqual((t["type"], t["from"], t["events"]), ("chatTail", 2, []), "an empty suffix: nothing in the events changed")
        self.assertEqual((t["notify"], t["hideFromFeed"], t["postalServiceOff"]), (True, False, True), "the flags ride the tail")
        n = len(sent)
        km._send_chat(c, dict(m2, notify=False), None, km._chat_diff(a, a), False)
        self.assertEqual((len(sent), _last(sent)["notify"]), (n + 1, False), "the flip alone is a new frame: the dedup signature reads the flags")

    def test_a_flag_only_change_reaches_an_index_client_on_its_uuid_anchored_tail_too(self):
        # the shell's pages speak the uuid-anchored wire (proto 2, T323): the same flip has to ride THAT delta, or another
        # window on the same kernel learns a bell only with the session's next full frame (2026-09-13, found by the served
        # split story's second window)
        c, sent = _client(); c["proto"] = 2
        a = [{"uuid": "1"}, {"uuid": "2"}]
        km._send_chat(c, self._m("S", a), None, 0, False)             # the full frame: the client's base is {first, last}
        self.assertEqual((_last(sent)["type"], _last(sent)["proto"]), ("session", 2))
        m2 = dict(self._m("S", a), notify=True, hideFromFeed=False, postalServiceOff=True)
        km._send_chat(c, m2, None, km._chat_diff(a, a), False)
        t = _last(sent)
        self.assertEqual((t["type"], t["afterUuid"], t["events"]), ("chatTail", "2", []), "an empty suffix after the newest held event")
        self.assertEqual((t["notify"], t["hideFromFeed"], t["postalServiceOff"]), (True, False, True), "the flags ride the uuid-anchored tail")
        n = len(sent)
        km._send_chat(c, dict(m2, notify=False), None, km._chat_diff(a, a), False)
        self.assertEqual((len(sent), _last(sent)["notify"]), (n + 1, False), "the flip alone is a new frame here too")

    def test_a_fork_new_head_uuid_forces_a_full_resend(self):
        c, sent = _client()
        km._send_chat(c, self._m("S", [{"uuid": "1"}, {"uuid": "2"}]), None, 0, False)   # full
        # the tab re-pointed onto a NEW transcript (a /clear-style fork) → first event uuid changes
        km._send_chat(c, self._m("S", [{"uuid": "9"}, {"uuid": "10"}]), None, 0, False)
        self.assertEqual(_last(sent)["type"], "session", "a fork must full-resend, never a tail onto a wrong base")

    def test_a_change_below_the_clients_loaded_tail_forces_a_full(self):
        # the client holds a TAIL starting at headFrom=2 (echat = (tail_head_uuid, headFrom)). A change at
        # index 1 is BELOW its loaded tail → it lacks [1,2) → must full-resend, not tail.
        c, sent = _client()
        evs = [{"uuid": "1"}, {"uuid": "2"}, {"uuid": "3"}, {"uuid": "4"}]
        c["echat"] = {"S": ("3", 2)}                           # holds the tail [2,4): head '3' at index 2
        km._send_chat(c, self._m("S", evs), None, 1, False)           # change_from 1 < headFrom 2 → full
        self.assertEqual(_last(sent)["type"], "session")

    def test_a_big_session_full_send_is_trimmed_to_the_tail_with_an_offset(self):
        evs = [{"uuid": str(i)} for i in range(km.WIRE_TAIL + 50)]    # bigger than the wire tail
        c, sent = _client()
        km._send_chat(c, self._m("S", evs), None, 0, False)
        full = _last(sent)
        self.assertEqual(full["type"], "session")
        self.assertEqual(len(full["events"]), km.WIRE_TAIL, "ship only the last WIRE_TAIL events")
        self.assertEqual(full["headFrom"], 50, "offset = total - WIRE_TAIL (older history lives before it)")
        self.assertEqual(full["headTotal"], km.WIRE_TAIL + 50)
        self.assertEqual(full["events"][0]["uuid"], "50", "the tail starts at headFrom")
        # echat now tracks (tail_head_uuid, headFrom) → a later append delta uses the GLOBAL index
        evs2 = evs + [{"uuid": "NEW"}]
        km._send_chat(c, self._m("S", evs2), None, len(evs), False)   # appended at global index = old total
        tail = _last(sent)
        self.assertEqual(tail["type"], "chatTail")
        self.assertEqual(tail["from"], len(evs), "the tail's `from` is the GLOBAL index, mapped by the browser")
        self.assertEqual([e["uuid"] for e in tail["events"]], ["NEW"])

    def test_the_top_level_git_branch_survives_the_tail_trim(self):
        # Regression (the user 2026-06-30): the status-bar branch + tab tooltip read a TOP-LEVEL gitBranch field,
        # never the head system event. The system event lives at events[0]; a >WIRE_TAIL session ships only the
        # last WIRE_TAIL events, so that head event (and its branch) fell off the wire → the branch vanished on
        # every long session. A top-level field is not part of the windowed events, so it must always ride along.
        evs = [{"uuid": str(i)} for i in range(km.WIRE_TAIL + 50)]    # bigger than the wire tail
        m = self._m("S", evs); m["gitBranch"] = "main"
        c, sent = _client()
        km._send_chat(c, m, None, 0, False)
        full = _last(sent)
        self.assertEqual(len(full["events"]), km.WIRE_TAIL, "events are still trimmed to the tail")
        self.assertEqual(full.get("gitBranch"), "main", "the top-level branch rides along even when trimmed")

    def test_a_small_session_under_the_tail_is_sent_whole(self):
        evs = [{"uuid": "1"}, {"uuid": "2"}]
        c, sent = _client()
        km._send_chat(c, self._m("S", evs), None, 0, False)
        full = _last(sent)
        self.assertEqual(full["type"], "session")
        self.assertNotIn("headFrom", full, "a session that fits under WIRE_TAIL is sent whole, no offset")

    def test_the_ledger_rides_the_tail_only_when_it_changed(self):
        # the ledger (goal tree, tens of KB) only changes on a judge pass, so it must NOT ride every 0.5s delta
        a = [{"uuid": "1"}, {"uuid": "2"}]
        c, sent = _client()
        km._send_chat(c, self._m("S", a), None, 0, False)                  # full → carries the ledger
        km._send_chat(c, self._m("S", a + [{"uuid": "3"}]), None, 2, False)   # only an event appended
        self.assertEqual(_last(sent)["type"], "chatTail")
        self.assertNotIn("ledger", _last(sent), "an unchanged ledger does NOT ride every delta")
        km._send_chat(c, self._m("S", a + [{"uuid": "3"}, {"uuid": "4"}]), None, 3, True)   # judge pass
        self.assertIn("ledger", _last(sent), "a changed ledger DOES ride the delta")


class RenderHandlesTheTail(unittest.TestCase):
    def _render(self):
        import pathlib
        return (pathlib.Path(BIN).parent / "ui" / "webview" / "render.ts").read_text()

    def test_render_truncates_to_from_appends_and_repaints_from_the_changed_point(self):
        r = self._render()
        self.assertIn('else if (m.type === "chatTail") chatTail(m);', r)       # dispatched
        self.assertIn("from = (msg.from | 0) - (s.headFrom || 0);", r)   # GLOBAL index → resident-tail local
        # The two rejection cases split on 2026-07-28. Below the loaded head → still a quiet return (the
        # resident tail is fine). A GAP (from past what we hold) → ask for a full session: "wait for the
        # next full" was a promise nothing kept, and the tab froze there until its socket dropped.
        self.assertIn("if (from < 0) return;", r)
        # the gap check runs in KERNEL coordinates — the client's injected optimistic tail is not part
        # of the kernel's index space, and counting it masked genuine gaps (the user 2026-08-09)
        self.assertIn("if (from > kernelLen) {", r)
        self.assertIn('requestFullSession(msg.id, "gap");', r)   # 2026-09-07: the ask names its reason (skeleton tabs)
        self.assertIn("s.events.length = from;", r)                            # truncate the superseded tail
        self.assertIn("for (const e of (msg.events || [])) s.events.push(e);", r)  # append the suffix
        self.assertIn("v.rendered = Math.min(v.rendered, from);", r)           # repaint from the exact change

    def test_render_handles_a_partial_session_and_streams_older_in(self):
        r = self._render()
        # upsert records the wire offset → s.events is the tail [headFrom, headTotal); an empty frame for a held
        # transcript keeps the resident window instead (T249b, frame-merge.ts)
        self.assertIn("headFrom: kept && prev ? prev.headFrom : (msg.headFrom ?? 0),", r)
        # scroll to the top of the resident tail with older on the server → request the previous chunk
        self.assertIn('vscodeApi?.postMessage({ type: "loadOlder", id: sid, before: s.proto === 2 ? s.firstUuid : s.headFrom });', r)
        # …only on an upward or unchanged move of the view (T366: a downward flick inside the estimate's top band never asks)
        self.assertIn("if (gesture) v.edgeUp = olderRequestAllowed(v.edgeTop, st);", r)
        self.assertIn("const upward = v.edgeUp !== false;", r)
        self.assertIn("if (moreOnServer && (v.winStart ?? 0) === 0 && st < topH + edgePx && upward) { requestOlder(", r)
        # chatHead PREPENDS the chunk + lowers headFrom + re-anchors
        self.assertIn('else if (m.type === "chatHead") chatHead(m);', r)
        self.assertIn("if (older.length) s.events = older.concat(s.events);", r)
        self.assertIn("s.headFrom = from;", r)


if __name__ == "__main__":
    unittest.main()


class ByteIdenticalFrames(unittest.TestCase):
    """The stage 1 exact return in _chat_diff (2026-09-18) may skip work only where the output is unchanged: this
    runs the same six pusher cycles twice, once with a verbatim copy of the walk it replaced and once with the
    kernel's own, and compares the raw wire strings every client received. Chat, feed and timeline clients
    together, so the feed's card order and columns are in the comparison too (the cards rule). Synthetic only:
    placeholder ids, the notes-api demo world, TESTHOST."""

    SID = "11111111-2222-4333-8444-000000000918"
    NOW = 1781400000

    @staticmethod
    def _chat_diff_reference(prev, cur):
        # the walk as it stood before the exact return, verbatim
        if not prev:
            return 0
        n = min(len(prev), len(cur))
        i = 0
        while i < n:
            a, b = prev[i], cur[i]
            if a is not b and a != b:
                break
            i += 1
        return i

    def _ev(self, i, output=None):
        e = {"kind": "assistant", "uuid": "11111111-2222-4333-8444-00000000b%03d" % i, "md": "reply %d" % i}
        if output is not None:
            e["output"] = output
        return e

    def _session(self, events):
        return {"type": "session", "id": self.SID, "name": "web", "color": None, "events": events,
                "status": {"state": "ready"}, "ledger": None}

    def _card(self, i, text=None):
        t = self.NOW - i * 60
        return {"itemId": "%s:g%d" % (self.SID, i), "sid": self.SID, "name": "web", "color": None,
                "text": text or "Synthetic goal %d on the notes-api board" % i, "t": t, "live": True,
                "trgb": [10, 20, 30], "column": "working", "summary": "s" * 40, "tree": []}

    def _feed(self, build_id, asks):
        return {"type": "feed", "asks": asks, "now": self.NOW, "buildId": build_id, "order": [self.SID],
                "working": ["web"], "awaiting": [], "sessions": [{"sid": self.SID, "name": "web", "color": None}],
                "userTodos": {}, "views": {}, "clearNotices": [], "syncNotices": [], "sdkNotices": [],
                "selfHost": "TESTHOST"}

    def _timeline(self, nbars, now):
        turns = {self.SID: [{"id": "b%d" % i, "t": i, "end": i + 1, "open": False} for i in range(nbars)]}
        return {"type": "timeline", "sessions": [{"id": self.SID, "name": "web"}], "turns": turns,
                "judging": {}, "messages": [], "now": now}

    def _script(self):
        """(build_session frame, feed, timeline) per cycle. The SAME session frame object twice in a row is the
        served tab: _push writes its events list back as the baseline, so the next diff sees one object on both
        sides (the exact return's case); a new list is a rebuild with an appended tail, then an in-place fill."""
        e1, e2, e3 = self._ev(1), self._ev(2), self._ev(3)
        a = self._session([e1, e2])
        b = self._session([e1, e2, e3])
        c = self._session([e1, self._ev(2, output="done"), e3])
        asks1 = [self._card(i) for i in range(4)]
        asks2 = [self._card(i, text="changed" if i == 2 else None) for i in range(4)]
        f1, f2 = self._feed(1, asks1), self._feed(2, asks2)
        t1, t2 = self._timeline(2, 1), self._timeline(3, 2)
        return [(a, f1, t1), (a, f1, t1), (b, f1, t1), (b, f1, t1), (c, f1, t1), (c, f2, t2)]

    def _run(self, diff, perf=None):
        """Six cycles; returns (the raw wire strings per client, whether the diff met one object on both sides per
        cycle, and with `perf` a _PerfStats each cycle's stage split, the cycle opened and closed on this thread)."""
        sid = self.SID
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        path = os.path.join(td.name, sid + ".jsonl")
        with open(path, "w") as f:
            f.write("{}\n")
        sess = {"sid": sid, "name": "web", "anchor": None, "path": path, "mtime": self.NOW}
        live = {sid: {"state": "waiting", "color": "#888888", "since": self.NOW - 60, "model": "", "effort": "",
                      "context": None, "backend": "sdk"}}
        wire = {"chat": [], "feed": [], "timeline": []}
        clients = [{"app": app, "alive": True, "sent": {}, "delta": app != "chat", "caps": set(),
                    "send": (lambda s, app=app: wire[app].append(s))} for app in ("chat", "feed", "timeline")]
        # the same cold module state for both runs
        for d in (km._prev_chat_events, km._prev_chat_ledger, km._built_chat):
            d.pop(sid, None)
        km._EMPTY_BUILD_NOTED.discard(sid)
        km._last_tab_order[:] = []
        saved = (km._feed_wire, km._bars_wire, km._skel_wire, dict(km._delta_parts_cache), dict(km._delta_split_memo),
                 km._feed_cards_memo, list(km._built_timeline))
        km._feed_wire = km._bars_wire = km._skel_wire = None
        km._delta_parts_cache.clear(); km._delta_split_memo.clear(); km._feed_cards_memo = None

        def restore():
            km._feed_wire, km._bars_wire, km._skel_wire = saved[:3]
            km._delta_parts_cache.clear(); km._delta_parts_cache.update(saved[3])
            km._delta_split_memo.clear(); km._delta_split_memo.update(saved[4])
            km._feed_cards_memo = saved[5]; km._built_timeline[:] = saved[6]
            for d in (km._prev_chat_events, km._prev_chat_ledger, km._built_chat):
                d.pop(sid, None)
        self.addCleanup(restore)
        same_object_calls = []

        def spy(prev, cur):
            same_object_calls.append(prev is not None and prev is cur)
            return diff(prev, cur)
        world = {}
        err = io.StringIO()
        with mock.patch.object(km, "_chat_diff", spy), \
                mock.patch.object(km, "_alive_sessions", lambda now, tm: [dict(sess)]), \
                mock.patch.object(km, "_chat_tab_sessions", lambda now, tm: [dict(sess)]), \
                mock.patch.object(km, "_warm_fleet_bg", lambda now: None), \
                mock.patch.object(km, "_live_map", lambda: dict(live)), \
                mock.patch.object(km, "build_session", lambda sid, now, live_map=None, **kw: dict(world["frame"])), \
                mock.patch.object(km, "_cached_feed", lambda now, live_map, sig, connect=False: world["feed"]), \
                mock.patch.object(km, "_cached_timeline", lambda now, live_map, sig, connect=False: world["timeline"]), \
                mock.patch.object(km, "build_timeline", lambda now, live_map, with_bars=True, live_only=False: world["timeline"]), \
                mock.patch.object(km, "_fleet_view_sig", lambda now, live_map: ("sig",)), \
                mock.patch.object(km, "_DELTA_MAX_FRACTION", 10.0), \
                mock.patch.object(sys, "stderr", err):
            builds, rows = [], []
            for frame, feed, timeline in self._script():
                if not builds or builds[-1] is not frame:      # a new frame is a rebuild: the transcript's stat moves,
                    builds.append(frame)                        # so the tab's signature misses and build_session runs;
                    os.utime(path, (self.NOW, self.NOW + len(builds)))   # a repeat is the served tab (the cache hit)
                world.update(frame=frame, feed=feed, timeline=timeline)
                km._built_timeline[:] = [None, timeline, time.time(), time.time()]
                if perf is not None:
                    perf.cycle_begin()
                t0 = time.monotonic()
                km._push(clients, live_map=live)
                if perf is not None:
                    perf.cycle(time.monotonic() - t0)
                    rows.append(perf.snapshot()["pusher"]["stageRing"][-1]["stages"])
        for line in err.getvalue().splitlines():
            self.assertNotIn("push build:", line, "a cycle raised: %s" % err.getvalue())
            self.assertNotIn("push send", line, "a send raised: %s" % err.getvalue())
        return wire, same_object_calls, rows

    def test_the_frames_every_client_receives_are_byte_identical_with_and_without_the_exact_return(self):
        before, calls_before, _ = self._run(self._chat_diff_reference)
        after, calls_after, _ = self._run(km._chat_diff)
        self.assertEqual(after, before, "the same wire strings, per client, across the six cycles")
        self.assertEqual(calls_after, calls_before, "the diff met the same arguments in the same order")
        self.assertEqual(calls_after, [False, True, False, True, False, True],
                         "the served-tab case (one list on both sides) on every repeat cycle, a walk on every rebuild")
        types = lambda strings: [json.loads(s)["type"] for s in strings]
        chat = types(after["chat"])
        self.assertEqual(chat.count("session"), 1, "the full session went once, to the fresh client: %r" % chat)
        tails = [json.loads(s) for s in after["chat"] if json.loads(s)["type"] == "chatTail"]
        self.assertEqual([(t["from"], len(t["events"])) for t in tails], [(2, 0), (2, 1), (3, 0), (1, 2), (3, 0)],
                         "the served tab's empty suffix after the full, the appended event, the served tab again, the "
                         "in-place fill's two, the served tab once more")
        self.assertIn("feed", types(after["feed"]))
        self.assertIn("delta", types(after["feed"]), "the changed card crossed as a delta, so the card path is in the comparison")
        self.assertIn("bars", types(after["timeline"]))
        self.assertIn("delta", types(after["timeline"]), "the appended bar crossed as a delta")
        feed_frames = [json.loads(s) for s in after["feed"]]
        first = [f for f in feed_frames if f["type"] == "feed"][0]
        self.assertEqual([a["column"] for a in first["asks"]], ["working"] * 4, "no card moved column")
        self.assertEqual([a["itemId"] for a in first["asks"]], ["%s:g%d" % (self.SID, i) for i in range(4)], "nor order")

    def test_the_chat_stage_is_split_into_its_seams(self):
        """Stage 1 of the incremental-push design (2026-09-18): push.chat is a container of three seams in stages_ms
        and in the cycle's split: sig (the tab's signature, every tab every cycle, the post-build one included),
        build (build_session, a rebuild only) and send (the diff and the per-client sends). A served tab records
        sig and send and no build."""
        ps = km._PERF_STATS
        seams = ("push.chat.sig", "push.chat.build", "push.chat.send")
        before = ps.snapshot()["stages_ms"]
        for k in seams:
            self.assertIn(k, before, "%s is listed at zero from the start" % k)
        _wire, calls, rows = self._run(km._chat_diff, perf=ps)
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, rebuilt, served, rebuilt, served")
        for i, row in enumerate(rows):
            chat = sorted(k for k in row if k.startswith("push.chat"))
            if calls[i]:
                self.assertNotIn("push.chat.build", chat, "cycle %d served the tab: no build seam (%r)" % (i, chat))
                self.assertIn("push.chat.sig", chat); self.assertIn("push.chat.send", chat)
            else:
                self.assertEqual([k for k in chat if k in seams], sorted(seams), "cycle %d rebuilt: every seam (%r)" % (i, chat))
            self.assertIn("push.chat", chat, "the container closes every cycle")
        after = ps.snapshot()["stages_ms"]
        for k in seams:
            self.assertGreater(after[k], before[k], "%s moved" % k)
        self.assertGreaterEqual(after["push.chat"] - before["push.chat"] + 1e-6, sum(after[k] - before[k] for k in seams),
                                "the seams sit inside the container's wall time")

