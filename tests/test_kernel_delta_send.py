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
import types
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

    def _run(self, diff, perf=None, build=None, tolerate=(), between=None):
        """Six cycles; returns (the raw wire strings per client, whether the diff met one object on both sides per
        cycle, and with `perf` a _PerfStats each cycle's stage split, the cycle opened and closed on this thread).
        `build` replaces build_session's body (frame -> the session dict, or a raise); `tolerate` names stderr lines
        the run expects (a failed build's own report); `between`, when given, is called with the cycle's index before
        each cycle's push (the census tests move a client's skeleton set between cycles)."""
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
                mock.patch.object(km, "build_session", lambda sid, now, live_map=None, **kw: (build or dict)(world["frame"])), \
                mock.patch.object(km, "_cached_feed", lambda now, live_map, sig, connect=False: world["feed"]), \
                mock.patch.object(km, "_cached_timeline", lambda now, live_map, sig, connect=False: world["timeline"]), \
                mock.patch.object(km, "build_timeline", lambda now, live_map, with_bars=True, live_only=False: world["timeline"]), \
                mock.patch.object(km, "_fleet_view_sig", lambda now, live_map: ("sig",)), \
                mock.patch.object(km, "_DELTA_MAX_FRACTION", 10.0), \
                mock.patch.object(sys, "stderr", err):
            builds, rows = [], []
            for i, (frame, feed, timeline) in enumerate(self._script()):
                if between is not None:
                    between(i)
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
            if any(t in line for t in tolerate):
                continue
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

    def test_the_signature_counters_move_with_the_push_loop(self):
        """Stage 1 of the chat-signature design (2026-09-18): memos.chatSig counts what the push loop does. Six cycles over
        one tab, rebuilt and served alternately: pre = the six pre-build signatures = builds.chat cached + built, post = the
        three post-build signatures = built less nosig, no nosig, a compare on every cycle after the first (a cached entry
        to compare against), at least one stat per signature (the transcript's), and no census count with no chat client
        registered (the harness's clients are the push's targets, not connected clients)."""
        ps = km._PERF_STATS
        before, b0 = km._chat_sig_stats_report(), ps.snapshot()["builds"]["chat"]
        _wire, calls, _rows = self._run(km._chat_diff, perf=ps)
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        after, b1 = km._chat_sig_stats_report(), ps.snapshot()["builds"]["chat"]
        d = {k: after[k] - before[k] for k in after}
        cached, built = b1["cached"] - b0["cached"], b1["built"] - b0["built"]
        self.assertEqual((cached, built), (3, 3))
        self.assertEqual(d["pre"], cached + built, "one pre-build signature per tab per push")
        self.assertEqual(d["nosig"], 0)
        self.assertEqual(d["post"], built - d["nosig"], "one post-build signature per rebuild that had a signature")
        self.assertEqual(d["compares"], 5, "every cycle after the first meets the cached entry")
        self.assertGreaterEqual(d["compareIdentity"], 0)
        self.assertLessEqual(d["compareIdentity"], 5 * len(km._CHAT_SIG_LABELS))
        self.assertGreaterEqual(d["stats"], d["pre"] + d["post"], "every signature stats the transcript at least")
        self.assertEqual(d["waited"], 0)
        self.assertEqual((d["warmEligible"], d["warmBlockedByOutline"], d["heldBody"]), (0, 0, 0), "no connected chat client: no census")

    def test_the_warm_tab_census_counts_by_what_the_connected_clients_hold(self):
        """The census the warm-tab gate question needs (the design's dropped alternative, kept as a count): a cached tab
        every connected chat client holds as a skeleton and no client watches is warmEligible; the same tab with a plain
        Outline pane connected is warmBlockedByOutline; a tab a client holds as a body (the watched tab included) is
        heldBody. The first cycle builds the tab while the client still holds it whole (else the cold gate would skip it
        and it would never be warm); the client's skeleton set gains the sid before the second."""
        ps = km._PERF_STATS
        keys = ("warmEligible", "warmBlockedByOutline", "heldBody")

        def scenario(clients, between=None):
            before, c0 = km._chat_sig_stats_report(), ps.snapshot()["builds"]["chat"]["coldSkipped"]
            with mock.patch.object(km, "_clients", clients):
                _wire, calls, _rows = self._run(km._chat_diff, perf=ps, between=between)
            self.assertEqual(calls, [False, True, False, True, False, True], "the census changes no build: rebuilt, served, alternating")
            self.assertEqual(ps.snapshot()["builds"]["chat"]["coldSkipped"], c0, "no tab was cold-skipped")
            after = km._chat_sig_stats_report()
            return tuple(after[k] - before[k] for k in keys)

        def client(**kw):
            return dict({"app": "chat", "alive": True, "sent": {}, "skeleton": set(), "proto": 2, "ready": True, "handshake": True}, **kw)
        held = client()
        def skeleton_from_cycle_1(i):
            if i == 1:
                held["skeleton"] = {self.SID}
        self.assertEqual(scenario([held], skeleton_from_cycle_1), (5, 0, 1),
                         "warm from cycle 1 on and held as a skeleton: eligible five times; held as a body on cycle 0")
        held = client()
        self.assertEqual(scenario([held, {"app": "fleet", "alive": True, "sent": {}}], skeleton_from_cycle_1), (0, 5, 1),
                         "a plain Outline pane blocks the gate: the same five count under warmBlockedByOutline")
        self.assertEqual(scenario([client(active=self.SID)]), (0, 0, 6), "a watched tab is a body every cycle")

    def test_the_census_reads_each_clients_skeleton_set_once_per_push_not_once_per_tab(self):
        """The census's skeleton question is answered from one read of every connected chat client per push
        (_skeleton_census, before the tab loop), not by asking _held_as_skeleton_by_all per tab as the first cut did: over
        six pushes with one connected page the by-all walk runs once, for the cold gate on the first cycle (the tab not
        yet built), and the census helper once per push (2026-09-18 review, low 2)."""
        ps = km._PERF_STATS
        by_all, census = [], []
        real_by_all, real_census = km._held_as_skeleton_by_all, km._skeleton_census

        def spy_by_all(sid, clients):
            by_all.append(sid); return real_by_all(sid, clients)

        def spy_census(sids, clients):
            census.append(list(sids)); return real_census(sids, clients)
        held = {"app": "chat", "alive": True, "sent": {}, "skeleton": set(), "proto": 2, "ready": True, "handshake": True}

        def skeleton_from_cycle_1(i):
            if i == 1:
                held["skeleton"] = {self.SID}
        before = km._chat_sig_stats_report()
        with mock.patch.object(km, "_clients", [held]), mock.patch.object(km, "_held_as_skeleton_by_all", spy_by_all), \
                mock.patch.object(km, "_skeleton_census", spy_census):
            _wire, calls, _rows = self._run(km._chat_diff, perf=ps, between=skeleton_from_cycle_1)
        after = km._chat_sig_stats_report()
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        self.assertEqual(by_all, [self.SID], "the by-all walk ran once: the cold gate's, on the first cycle, before the tab was built")
        self.assertEqual(census, [[self.SID]] * 6, "the census helper ran once per push, over the push's tabs")
        self.assertEqual(tuple(after[k] - before[k] for k in ("warmEligible", "warmBlockedByOutline", "heldBody")), (5, 0, 1),
                         "...and the census reads the same as before the change")

    def test_reads_inside_a_signature_are_counted_and_the_same_reads_outside_one_are_not(self):
        """The read counters are gated to a signature (the thread-local scope _chat_build_sig opens): the names read in
        _sdk_transcript_path, the switch read in _user_todos_on and sdk_backend.read_reg count inside one and not
        outside, and regReads equals the read_reg calls the signature made (a dead tab's queue fallbacks included)."""
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        path = os.path.join(td.name, self.SID + ".jsonl")
        with open(path, "w") as f:
            f.write("{}\n")
        sess = {"sid": self.SID, "name": "web", "anchor": None, "path": path, "mtime": self.NOW}
        self.assertTrue(km._sdk(), "premise: the SDK backend module loads (its read_reg is the counted reader)")
        sb = sys.modules["romp_sdk_backend"]
        real_read_reg = sb.read_reg
        reg_calls = []

        def read_reg(state_dir, sid):
            reg_calls.append(sid); return real_read_reg(state_dir, sid)
        empty_stamp = ((None, None, None, None, ()), frozenset(), ())

        def stamp(sid):
            km._sdk_transcript_path(sid); return empty_stamp

        def todo_fp(sid):
            km._user_todos_on(); return None

        def launch(sid, be=None):
            sb.read_reg(km.jd.STATE, str(sid)); return None
        with mock.patch.object(sb, "read_reg", read_reg), mock.patch.object(km, "_session_stamp_read", stamp), \
                mock.patch.object(km, "_user_todo_fp", todo_fp), mock.patch.object(km, "_launch_error", launch), \
                mock.patch.object(km._live_scope, "names", {}, create=True):   # a names snapshot: _names_parts reads no file
            before = km._chat_sig_stats_report()
            km._sdk_transcript_path(self.SID); km._user_todos_on(); sb.read_reg(km.jd.STATE, self.SID); km._chat_ident(path)
            self.assertEqual(km._chat_sig_stats_report(), before, "outside a signature the readers count nothing")
            del reg_calls[:]
            sig = km._chat_build_sig(sess, None, self.NOW, live_map={})
            after = km._chat_sig_stats_report()
        self.assertIsNotNone(sig)
        d = {k: after[k] - before[k] for k in after}
        self.assertEqual(d["namesReads"], 1, "the stamp read's names read, and no other")
        self.assertEqual(d["switchReads"], 1)
        self.assertEqual(d["regReads"], len(reg_calls), "every read_reg the signature made: %r" % (reg_calls,))
        self.assertGreaterEqual(d["regReads"], 1)
        self.assertGreaterEqual(d["stats"], 5, "the transcript, the states file and the archive, episodes and gone identities at least")
        self.assertEqual((d["pre"], d["post"], d["compares"]), (0, 0, 0), "a signature outside the push loop is not a loop count")

    def test_the_frames_are_byte_identical_with_the_signature_counters_disabled(self):
        """The counters are measurement: with every counting site a no-op and the thread-CPU clock absent the six cycles
        produce the same wire strings for every client (the stage 1 invariant: no frame or read changes)."""
        live, calls_live, _ = self._run(km._chat_diff)
        noop = lambda *a, **k: None
        with mock.patch.object(km, "_chat_sig_count", noop), mock.patch.object(km, "_chat_sig_bump", noop), \
                mock.patch.object(km, "_chat_sig_note_pre", noop), mock.patch.object(km, "_thread_cpu", lambda: None):
            off, calls_off, _ = self._run(km._chat_diff)
        self.assertEqual(off, live, "the same wire strings, per client, with the counters off")
        self.assertEqual(calls_off, calls_live)

    def test_the_signature_seam_is_split_into_its_static_and_deps_sub_seams(self):
        """Stage 1 of the chat-signature design (2026-09-18): push.chat.sig is a container of push.chat.sig.static (the
        signature less its dependency tail) and push.chat.sig.deps (the tail _chat_sig_deps evaluates), in stages_ms, in
        stages_cpu_ms and in the cycle's split. Every pre-build signature records both (a cold tab's tail runs and answers
        empty); the post-build one, deps=False, records static alone: a served tab closes static once and deps once, a
        rebuilt tab static twice and deps once, and per row the two sum to the seam within rounding."""
        ps = km._PERF_STATS
        names = []
        real_stage = ps.stage

        def stage(name, dt, cpu=None):
            names.append(name); return real_stage(name, dt, cpu=cpu)
        before = ps.snapshot()
        with mock.patch.object(ps, "stage", stage):
            _wire, calls, rows = self._run(km._chat_diff, perf=ps)
        after = ps.snapshot()
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        for k in ("push.chat.sig.static", "push.chat.sig.deps"):
            self.assertIn(k, before["stages_ms"], "%s is listed at zero from the start" % k)
            self.assertGreater(after["stages_ms"][k], before["stages_ms"][k], "%s moved" % k)
            self.assertIn(k, after["stages_cpu_ms"] or {k: None}, "%s has a CPU row where the platform has the clock" % k)
        self.assertAlmostEqual(after["stages_ms"]["push.chat.sig"] - before["stages_ms"]["push.chat.sig"],
                               sum(after["stages_ms"][k] - before["stages_ms"][k] for k in ("push.chat.sig.static", "push.chat.sig.deps")),
                               places=6, msg="the two sub-seams are the seam, cumulatively")
        for i, row in enumerate(rows):
            self.assertIn("push.chat.sig.static", row, "cycle %d" % i); self.assertIn("push.chat.sig.deps", row, "cycle %d" % i)
            self.assertLessEqual(abs(row["push.chat.sig"]["ms"] - row["push.chat.sig.static"]["ms"] - row["push.chat.sig.deps"]["ms"]), 0.2,
                                 "cycle %d: the split's rows sum within their rounding (%r)" % (i, {k: v["ms"] for k, v in row.items() if k.startswith("push.chat.sig")}))
        # the closes per cycle, in the order the seam close records them
        cycles, cur = [], []
        for n in names:
            if n == "push.chat":
                cycles.append(cur); cur = []
            elif n.startswith("push.chat.sig"):
                cur.append(n)
        self.assertEqual(len(cycles), 6)
        for i, seen in enumerate(cycles):
            served = calls[i]
            self.assertEqual(seen.count("push.chat.sig.static"), 1 if served else 2, "cycle %d: %r" % (i, seen))
            self.assertEqual(seen.count("push.chat.sig.deps"), 1, "cycle %d: the tail runs once, in the pre-build signature: %r" % (i, seen))
            self.assertEqual(seen[:3], ["push.chat.sig.static", "push.chat.sig.deps", "push.chat.sig"], "cycle %d: the sub-seams close before the seam: %r" % (i, seen))

    def test_the_chat_seams_record_their_thread_cpu_from_a_bounded_number_of_rusage_reads(self):
        """Stage 1 of the chat-signature design (2026-09-18): the chat loop reads getrusage(RUSAGE_THREAD) at each seam's
        open and close and stages_cpu_ms carries the delta beside the wall. Under a fake clock that advances one ms of
        user and half a ms of system time per read: every signature seam moves the sig row by at least one read's worth,
        the send row moves too, the container's CPU covers its seams, and the reads per cycle stay within the stated
        bound (two per mark: the container, the signature and its deps sub-seam, the send; a rebuild adds the build seam
        and the post-build signature; the harness's own snapshot may add one)."""
        ps = km._PERF_STATS
        reads = []

        def fake(who):
            reads.append(who)
            return types.SimpleNamespace(ru_utime=0.001 * len(reads), ru_stime=0.0005 * len(reads), ru_maxrss=0)
        before = ps.snapshot()["stages_cpu_ms"]
        with mock.patch.object(km, "_RUSAGE_THREAD", 11), mock.patch.object(km.resource, "getrusage", fake):
            _wire, calls, rows = self._run(km._chat_diff, perf=ps)
            after = ps.snapshot()["stages_cpu_ms"]
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        self.assertEqual(reads, [11] * len(reads), "every read asked for the thread's rusage")
        self.assertLessEqual(len(reads), 6 * 16, "at most sixteen reads per cycle: %d over six" % len(reads))
        d = {k: {c: after[k][c] - before[k][c] for c in ("user", "sys")} for k in after if k in before}
        self.assertGreaterEqual(d["push.chat.sig"]["user"], 9 * 1.0 - 1e-6, "nine signatures, each at least one read apart")
        self.assertAlmostEqual(d["push.chat.sig"]["sys"], d["push.chat.sig"]["user"] / 2.0, msg="the fake's ratio survives the fold")
        self.assertGreater(d["push.chat.send"]["user"], 0.0)
        self.assertGreater(d["push.chat.build"]["user"], 0.0)
        self.assertGreaterEqual(d["push.chat"]["user"] + 1e-6, sum(d[k]["user"] for k in ("push.chat.sig", "push.chat.build", "push.chat.send")),
                                "the container's CPU covers its seams")
        for row in rows:
            self.assertEqual(set(row["push.chat.sig"]), {"ms", "bytes", "hydrated"}, "the split's rows carry no CPU column")

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

    def test_a_build_that_raises_records_its_build_seam_and_no_send(self):
        """A build_session that raises is build time too: the tab's per-build guard records push.chat.build before it
        skips the tab, beside the signature it took; no frame, so no send seam (2026-09-18 review, medium 6)."""
        ps = km._PERF_STATS
        saved = dict(km._chat_build_faults)
        self.addCleanup(lambda: (km._chat_build_faults.clear(), km._chat_build_faults.update(saved)))
        km._chat_build_faults.pop(self.SID, None)

        def build(frame):
            raise RuntimeError("synthetic build failure")
        before = ps.snapshot()["stages_ms"]
        wire, calls, rows = self._run(km._chat_diff, perf=ps, build=build, tolerate=("push build: chat ",))
        self.assertEqual(calls, [], "no build ever stored: the diff never ran")
        self.assertEqual(len(rows), 6)
        for i, row in enumerate(rows):
            chat = sorted(k for k in row if k.startswith("push.chat"))
            self.assertIn("push.chat.sig", chat, "cycle %d: the signature was taken (%r)" % (i, chat))
            self.assertIn("push.chat.build", chat, "cycle %d: the failed build's time is build time (%r)" % (i, chat))
            self.assertNotIn("push.chat.send", chat, "cycle %d: no frame, no send (%r)" % (i, chat))
            self.assertIn("push.chat", chat)
        after = ps.snapshot()["stages_ms"]
        self.assertGreater(after["push.chat.build"], before["push.chat.build"])
        types = [json.loads(s)["type"] for s in wire["chat"]]
        self.assertNotIn("session", types); self.assertNotIn("chatTail", types)

    def test_a_rebuild_closes_the_sig_seam_twice_and_a_served_tab_once(self):
        """The post-build signature (the check that the static components held across the build) is signature time
        too: a rebuilt tab closes push.chat.sig twice, before and after build_session, a served tab once
        (2026-09-18 review, medium 6: the seams test alone could not tell the two apart)."""
        ps = km._PERF_STATS
        names = []
        real_stage, real_begin = ps.stage, ps.cycle_begin

        def stage(name, dt, cpu=None):
            names.append(name); return real_stage(name, dt, cpu=cpu)   # cpu: the seams' thread-CPU delta (stages_cpu_ms, 2026-09-18)

        def begin(*a, **kw):
            names.append(None); return real_begin(*a, **kw)
        with mock.patch.object(ps, "stage", stage), mock.patch.object(ps, "cycle_begin", begin):
            _wire, calls, rows = self._run(km._chat_diff, perf=ps)
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        cycles, cur = [], None
        for n in names:
            if n is None:
                cur = []; cycles.append(cur)
            else:
                cur.append(n)
        self.assertEqual(len(cycles), 6)
        for i, seen in enumerate(cycles):
            served = calls[i]
            self.assertEqual(seen.count("push.chat.sig"), 1 if served else 2,
                             "cycle %d (%s): the pre-build signature, and the post-build one on a rebuild (%r)"
                             % (i, "served" if served else "rebuilt", seen))
            self.assertEqual(seen.count("push.chat.build"), 0 if served else 1)
            self.assertEqual(seen.count("push.chat.send"), 1)
            self.assertEqual(seen.count("push.chat"), 1)


class _CountingLock:
    """Stands in for a client's slot RLock (`dlock`, what _client_lock returns): counts the holds."""

    def __init__(self):
        self.holds = 0

    def __enter__(self):
        self.holds += 1

    def __exit__(self, *a):
        return False


class ChatSigHelpers(unittest.TestCase):
    """memos.chatSig's pieces on their own (stage 1 of the chat-signature design): the warm-tab census's once-per-push
    skeleton read, the per-tab note's clauses, and a stat site's count. Synthetic ids only."""

    SIDS = ["11111111-2222-4333-8444-0000000009%02d" % i for i in range(6)]

    def _client(self, **kw):
        return dict({"app": "chat", "alive": True, "sent": {}, "dlock": _CountingLock()}, **kw)

    def test_the_skeleton_census_answers_the_by_all_question_per_tab_from_one_hold_per_client(self):
        """_skeleton_census(sids, clients) is {sid for which _held_as_skeleton_by_all(sid, clients)} over the same client
        shapes (a set holder, a reconnecting page with a watched tab, a relay diet page with none, a page whose echat
        already holds a tab), taking each client's slot lock ONCE for any number of tabs; None with no client, so the
        note can tell "no connected chat client" from "held by none"."""
        s = self.SIDS
        clients = [self._client(skeleton={s[0], s[1], s[2], s[3]}),
                   self._client(reconnect=True, active=s[0], echat={s[3]: 1}),          # holds every tab but its watched one and the one it has
                   self._client(skeletonOnReady=True, dietSkeleton=True, kind="relay")]  # a relay diet page with no watched tab: every tab
        expected = {x for x in s if km._held_as_skeleton_by_all(x, clients)}
        self.assertEqual(expected, {s[1], s[2]}, "premise: the by-all walk's own answer over these clients")
        for c in clients:
            c["dlock"].holds = 0
        self.assertEqual(km._skeleton_census(s, clients), expected)
        self.assertEqual([c["dlock"].holds for c in clients], [1, 1, 1], "one hold per client for six tabs")
        self.assertIsNone(km._skeleton_census(s, []), "no connected chat client: None, not an empty set")
        self.assertEqual(km._skeleton_census(s, [self._client()]), set(), "a page with no diet holds nothing as a skeleton")
        self.assertEqual(km._skeleton_census([], clients), set())

    def test_the_note_counts_a_cached_skeleton_tab_as_warm_only_while_its_transcript_exists(self):
        """The warm-tab gate's transcript clause: a cached tab every page holds as a skeleton counts under warmEligible
        when the signature's transcript component is a stat pair, and under neither warmEligible nor heldBody when it
        is None (the file is gone: the cold gate's os.path.exists clause, read off the signature instead of a second
        stat). A watched tab is a body whatever the set says; with no connected chat client the census counts nothing
        (2026-09-18 review, low 16)."""
        sid = self.SIDS[0]
        n = len(km._CHAT_SIG_LABELS)
        with_file = ((1.0, 3),) + (None,) * (n - 1)
        no_file = (None,) * n
        hit = (with_file, {"events": []}, None, None)
        keys = ("pre", "nosig", "compares", "warmEligible", "warmBlockedByOutline", "heldBody")

        def delta(sig, hit, watched, held, plain_outline=False):
            before = km._chat_sig_stats_report()
            km._chat_sig_note_pre(sid, sig, hit, watched, held, plain_outline)
            after = km._chat_sig_stats_report()
            return tuple(after[k] - before[k] for k in keys)
        self.assertEqual(delta(with_file, hit, False, {sid}), (1, 0, 1, 1, 0, 0), "cached, unwatched, held, with a transcript: warm")
        self.assertEqual(delta(no_file, hit, False, {sid}), (1, 0, 1, 0, 0, 0), "the transcript gone: neither warm nor a body")
        self.assertEqual(delta(with_file, hit, False, {sid}, True), (1, 0, 1, 0, 1, 0), "a plain Outline connected: blocked, not eligible")
        self.assertEqual(delta(with_file, hit, True, {sid}), (1, 0, 1, 0, 0, 1), "watched: a body, whatever the set says")
        self.assertEqual(delta(with_file, hit, False, set()), (1, 0, 1, 0, 0, 1), "held by none of the connected pages: a body")
        self.assertEqual(delta(with_file, hit, False, None), (1, 0, 1, 0, 0, 0), "no connected chat client: no census count")
        self.assertEqual(delta(with_file, None, False, {sid}), (1, 0, 0, 0, 0, 0), "no cached build: cold, not warm, and no compare")
        self.assertEqual(delta(None, hit, False, {sid}), (1, 1, 0, 0, 0, 0), "no signature: nosig, no compare, not warm")

    def test_the_repo_index_key_counts_exactly_the_stats_it_attempts(self):
        """_repo_index_key's share of memos.chatSig.stats is the stats it makes, each counted as it is attempted (the
        rule at every other counted site: a stat of a missing file is a syscall too): one per immediate subdirectory,
        one for the tree's own mtime, and one for the git index only when the tree has a git dir to hold one. The first
        cut counted the subdirectories plus two whatever `gi` said, a phantom stat per signature for a tree with no git
        dir (2026-09-18 review, low 4)."""
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        for d in ("a", "b"):
            os.mkdir(os.path.join(td.name, d))
        with open(os.path.join(td.name, "notes.txt"), "w") as f:
            f.write("x\n")

        def key_and_stats(head):
            with mock.patch.object(km, "_tree_of", lambda d: (td.name, "main")), \
                    mock.patch.object(km, "_git_head_file", lambda tree: head):
                before = km._chat_sig_stats_report()["stats"]
                with km._chat_sig_scope():
                    key = km._repo_index_key(td.name)
                return key, km._chat_sig_stats_report()["stats"] - before
        key, n = key_and_stats("")
        self.assertEqual(n, 3, "two subdirectory stats and the tree's mtime: no git dir, no index stat")
        self.assertIsNone(key[0]); self.assertEqual([s[0] for s in key[2]], ["a", "b"])
        gitdir = os.path.join(td.name, ".git")
        os.mkdir(gitdir)
        open(os.path.join(gitdir, "index"), "w").close()
        key, n = key_and_stats(os.path.join(gitdir, "HEAD"))
        self.assertEqual(n, 4, "...plus the index's mtime when the tree has a git dir (.git itself is not a counted subdirectory)")
        self.assertIsNotNone(key[0])
        before = km._chat_sig_stats_report()["stats"]
        with mock.patch.object(km, "_tree_of", lambda d: (td.name, "main")), mock.patch.object(km, "_git_head_file", lambda tree: ""), \
                mock.patch.object(km.os.path, "getmtime", mock.Mock(side_effect=OSError("synthetic"))):
            with km._chat_sig_scope():
                self.assertIsNone(km._repo_index_key(td.name), "a stat that raises: no key")
        self.assertEqual(km._chat_sig_stats_report()["stats"] - before, 3, "the raising stat was attempted, so it counts, like a missing file's")


if __name__ == "__main__":
    unittest.main()
