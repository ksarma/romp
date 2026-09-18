#!/usr/bin/env python3
"""T386 stage 2 (plans/chat-history-regions.md Part B, the kernel): every history reply names its TURN SPAN so the page can place
it among its regions; a gap's page is asked by span (loadTurns) and served exactly; and the per-client base is TAIL-ONLY: a reply
moves the client's base only when its span reaches the tail run, so the kernel never withholds a delta from a reader in older
history (no client is ever detached). Over the render-floor fixture (a restored parse whose pre-cut turns are lazy) the pages
before the floor and the floor'd list equal the whole build, so a span's events are checked against the whole. Synthetic
transcripts only (the stage 4a served fixture's builder)."""
import contextlib
import datetime
import inspect
import io
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from test_chat_pages import NOW, SID, Harness, _client, _strip, em, km, transcript


def _iso(t):
    """A transcript timestamp, the builder's own form."""
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class WindowSpans(Harness):
    def _boot(self):
        recs = transcript(NOW - 86400, turns=120, compact_every=25)
        self.write(recs)
        whole = self.whole()
        self.document()
        m = self.restored()
        c, sent = _client()
        km._send_chat_locked(c, m, None, 0, False)
        frame = sent[-1]
        return whole, m, frame, c

    def test_the_full_frame_names_the_tail_runs_first_turn_and_the_page_size(self):
        whole, m, frame, _ = self._boot()
        self.assertIn("tailLo", frame, "the full frame names where the tail run starts, so the page can lay a gap before it")
        self.assertGreater(frame["tailLo"], 0, "a restored parse's tail does not start at the head")
        self.assertEqual(frame["pageTurns"], km.PAGE_TURNS, "the page the gaps ask by")
        turns = km._parse(self.leaf, SID, NOW)["turns"]
        self.assertLessEqual(frame["tailLo"], len(turns))
        # the tail run's first event is the first event of turn tailLo
        first_tail = next(a["uuid"] for a in turns[frame["tailLo"]]["atoms"] if a.get("uuid"))
        resident = [e["uuid"] for e in _strip(frame["events"])]
        self.assertEqual(resident[0], first_tail, "the run the page holds starts at the named turn")

    def test_the_full_frame_starts_at_the_turn_boundary_when_the_cut_falls_inside_a_long_last_turn(self):
        """A LAST turn longer than WIRE_TAIL (a long agentic turn: hundreds of tool calls). The full frame ships the last
        WIRE_TAIL events and names the tail run's first turn (tailLo); the page lays a gap over the turns before it and asks
        those by whole turn (loadTurns), and holds the run from tailLo on. Until 2026-09-15 the frame's first event was the cut
        itself, inside that turn, so the turn's events before the cut belonged to neither the run (the page believed it held
        the turn from its start) nor the gap (whole turns before tailLo): unreachable by any ask. The frame now begins at the
        turn's first event, as every window and page does (review find J), and the coverage law holds: the head pages plus
        the frame are the whole build."""
        recs = transcript(NOW - 86400, turns=40, compact_every=25)
        t, parent = NOW - 3600, recs[-1]["uuid"]
        recs.append({"type": "user", "uuid": "uL", "parentUuid": parent, "timestamp": _iso(t), "promptSource": "typed", "cwd": "/w/notes-api",
                     "message": {"role": "user", "content": "run the whole sweep and report 0"}})
        recs.append({"type": "assistant", "uuid": "aL0", "parentUuid": "uL", "timestamp": _iso(t + 5), "cwd": "/w/notes-api",
                     "message": {"role": "assistant", "content": [{"type": "text", "text": "Starting the sweep; the figures land as each stage finishes."}], "stop_reason": "tool_use"}})
        parent = "aL0"
        for i in range(km.WIRE_TAIL + 50):
            tu, tr = "tL%d" % i, "rL%d" % i
            recs.append({"type": "assistant", "uuid": tu, "parentUuid": parent, "timestamp": _iso(t + 10 + 2 * i), "cwd": "/w/notes-api",
                         "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "tuL%d" % i, "name": "Bash", "input": {"command": "uv run python stage.py %d" % i}}], "stop_reason": "tool_use"}})
            recs.append({"type": "user", "uuid": tr, "parentUuid": tu, "timestamp": _iso(t + 11 + 2 * i),
                         "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tuL%d" % i, "content": "ok %d" % i}]}})
            parent = tr
        recs.append({"type": "assistant", "uuid": "aL1", "parentUuid": parent, "timestamp": _iso(t + 20 + 2 * (km.WIRE_TAIL + 50)), "cwd": "/w/notes-api",
                     "message": {"role": "assistant", "content": [{"type": "text", "text": "Sweep done; every stage reported."}], "stop_reason": "end_turn"}})
        self.write(recs)
        whole = self.whole()                                   # the whole build's events (a proto-1 client's, floor 0)
        m = km.build_session(SID, NOW, {}, floor=0)            # the frame a proto-2 client is sent from
        turns = km._parse(self.leaf, SID, NOW)["turns"]
        last = len(turns) - 1
        self.assertGreater(len(whole), km.WIRE_TAIL, "the fixture's last turn alone outgrows the wire tail")
        c, sent = _client()
        km._send_chat_locked(c, m, None, 0, False)
        frame = sent[-1]
        self.assertEqual(frame.get("proto"), 2)
        self.assertEqual(frame["tailLo"], last, "the cut falls inside the last turn, so the tail run starts there")
        resident = [e["uuid"] for e in _strip(frame["events"]) if e.get("uuid")]
        first_of_turn = next(a["uuid"] for a in turns[last]["atoms"] if a.get("uuid"))
        self.assertEqual(resident[0], first_of_turn, "the run the page holds starts at the named turn's FIRST event, not at the cut")
        self.assertIn("aL0", resident, "the turn's opening reply, before the cut, is in the run")
        self.assertGreaterEqual(len(resident), km.WIRE_TAIL, "the frame still carries at least the wire tail")
        # the coverage law: the pages the gap asks by whole turn (loadTurns, PAGE_TURNS at a time, the page's own ask), plus
        # the run, are the whole build; no event is in neither
        pages = []
        for lo in range(0, last, km.PAGE_TURNS):
            r = km._chat_history_reply(SID, {"type": "loadTurns", "id": SID, "lo": lo, "hi": min(lo + km.PAGE_TURNS, last)}, NOW)
            pages += [e["uuid"] for e in _strip(r["events"]) if e.get("uuid") and not str(e["uuid"]).startswith("system:")]   # transcript events; the head page's cards aside
        whole_uuids = [e["uuid"] for e in whole if e.get("uuid") and not str(e["uuid"]).startswith("system:")]
        self.assertEqual(pages + resident, whole_uuids, "every event is reachable: in a head page (turns before tailLo) or in the run")

    def test_load_around_carries_its_span_and_no_connected_verdict(self):
        whole, m, frame, c = self._boot()
        turns = km._parse(self.leaf, SID, NOW)["turns"]
        anchor = whole[len(whole) // 4]["uuid"]
        w = km._chat_history_reply(SID, {"type": "loadAround", "id": SID, "uuid": anchor}, NOW, base=c["echat"][SID])
        self.assertNotIn("missing", w)
        self.assertEqual(len(w["span"]), 2, "a window names [lo, hi) in the kernel's turn numbering")
        lo, hi = w["span"]
        self.assertLess(lo, hi); self.assertLessEqual(hi, len(turns))
        self.assertIn(anchor, [e["uuid"] for e in w["events"]], "the anchor is inside its window")
        self.assertEqual([e["uuid"] for e in w["events"]], [e["uuid"] for e in km._chat_history_page(SID, lo, hi, NOW)], "the window IS the span's page")
        self.assertNotIn("connected", w, "no detached verdict: the tail run is always resident on the page")
        head = km._chat_history_reply(SID, {"type": "loadAround", "id": SID, "uuid": whole[0]["uuid"]}, NOW, base=c["echat"][SID])
        self.assertEqual(head["span"][0], 0, "a window reaching the head spans from turn 0, whatever the head cards' own index: %r" % head["span"])
        self.assertEqual([e["uuid"] for e in head["events"][:len(self.head_cards)]], [e["uuid"] for e in self.head_cards], "…and carries the head cards")
        self.assertNotIn("_base", {k: v for k, v in w.items() if v is not None}, "a window short of the tail moves no base") if hi < frame["tailLo"] else None

    def test_load_older_carries_its_span_and_the_tail_only_base(self):
        whole, m, frame, c = self._boot()
        base = c["echat"][SID]
        oldest = _strip(frame["events"])[0]["uuid"]
        r = km._chat_history_reply(SID, {"type": "loadOlder", "id": SID, "before": oldest}, NOW, base=base)
        self.assertNotIn("missing", r)
        self.assertEqual(r["span"][1], frame["tailLo"], "the chunk before the tail ends where the tail run starts")
        lo, hi = r["span"]
        self.assertLess(lo, hi)
        self.assertEqual([e["uuid"] for e in r["events"][len(self.head_cards) if lo == 0 else 0:]], [e["uuid"] for e in km._chat_history_page(SID, lo, hi, NOW)], "the span is honest: its events are exactly the turns it names")
        self.assertTrue(r.get("_base") and r["_base"].get("first"), "a page joining the tail run moves the client's base to its first event: the tail-only base")
        self.assertEqual(r["_base"]["first"], km._event_key(r["events"][len(self.head_cards) if lo == 0 else 0]), "…its first TRANSCRIPT event (the head cards ride a chunk that reaches the head, and are no base)")
        # a page deep in history, not touching the tail, moves nothing
        if lo > 0:
            deep = km._chat_history_reply(SID, {"type": "loadOlder", "id": SID, "before": r["events"][0]["uuid"]}, NOW, base=base)
            self.assertNotIn("missing", deep)
            self.assertEqual(deep["span"][1], lo, "the chunks tile: each ends where the next begins")
            self.assertFalse(deep.get("_base"), "a chunk short of the tail moves no base (the reader is not detached, the tail's deltas keep flowing)")

    def test_load_turns_serves_exactly_the_span_asked_with_the_head_cards_at_the_head(self):
        whole, m, frame, c = self._boot()
        turns = km._parse(self.leaf, SID, NOW)["turns"]
        for lo, hi in ((0, 16), (16, 48), (20, 37), (frame["tailLo"] - 5, frame["tailLo"])):
            with self.subTest(lo=lo, hi=hi):
                n = km._chat_history_reply(SID, {"type": "loadTurns", "id": SID, "lo": lo, "hi": hi}, NOW, base=c["echat"][SID])
                self.assertNotIn("missing", n)
                self.assertEqual(n["span"], [lo, hi], "the span comes back as asked (alignment is the page's rule, chat-regions.ts pagesToAsk)")
                self.assertEqual(n["head"], lo == 0)
                body = n["events"][len(self.head_cards):] if lo == 0 else n["events"]
                if lo == 0:
                    self.assertEqual([e["uuid"] for e in n["events"][:len(self.head_cards)]], [e["uuid"] for e in self.head_cards], "the head cards ride the head page")
                self.assertEqual([e["uuid"] for e in body], [e["uuid"] for e in km._chat_history_page(SID, lo, hi, NOW)])
                if hi >= frame["tailLo"]:
                    self.assertTrue(n.get("_base") and n["_base"].get("first"), "a span reaching the tail moves the base to its first event")
                else:
                    self.assertFalse(n.get("_base"), "a span short of the tail moves no base")
        empty = km._chat_history_reply(SID, {"type": "loadTurns", "id": SID, "lo": 40, "hi": 40}, NOW)
        self.assertTrue(empty["missing"], "an empty span is missing, never a silent empty run")
        past = km._chat_history_reply(SID, {"type": "loadTurns", "id": SID, "lo": len(turns) + 5, "hi": len(turns) + 9}, NOW)
        self.assertTrue(past["missing"], "a span past the transcript is missing")
        self.assertEqual(past["span"], [len(turns) + 5, len(turns) + 9], "…and echoes the ASKED span, not the clamp, so the page's gapLoading key clears (T386 stage 2, low 3)")

    def test_load_turns_head_page_carries_the_head_cards_at_floor_zero(self):
        # round seven, medium 2: with no render floor the head cards are IN the floor'd list (turn index -1, above turn 0) and the
        # reply's head_cards field is empty, so the head page must start at the list's first event or the system context and the
        # /clear card never reach a reader who scrolls to the top (the reply says head, so nothing asks again)
        recs = transcript(NOW - 86400, turns=40)                           # no compaction: the whole build stands at floor 0
        self.write(recs)
        # the floor-0 build itself, cards and all (the harness's whole() strips them), from a fresh process with no document, as whole()
        # builds it: a build over the module's shared state left a stale lazy index behind for the next module (CI, round seven)
        self.fresh(); saved = em._CKPT_DIR_FN; em._CKPT_DIR_FN = None
        try:
            m0 = km.build_session(SID, NOW, {}, floor=0)
        finally:
            em._CKPT_DIR_FN = saved
        whole = m0["events"]
        self.assertEqual(int(m0.get("floor") or 0), 0, "the build stands at floor 0: %r" % m0.get("floor"))
        turns = km._parse(self.leaf, SID, NOW)["turns"]
        tix = km._turn_index_of_events(whole, turns)
        self.assertEqual(tix[0], -1, "the fixture fact: a head card leads the floor-0 list: %r" % whole[0].get("kind"))
        first_turn0 = next(i for i, ti in enumerate(tix) if ti >= 0)
        self.assertGreater(first_turn0, 0, "…at least one card above turn 0")
        n = km._chat_history_reply(SID, {"type": "loadTurns", "id": SID, "lo": 0, "hi": 16}, NOW)
        self.assertNotIn("missing", n); self.assertTrue(n["head"]); self.assertEqual(n["span"], [0, 16])
        end = next((i for i, ti in enumerate(tix) if ti >= 16), len(whole))
        self.assertEqual([e["uuid"] for e in n["events"]], [e["uuid"] for e in whole[:end]],
                         "the head page at floor 0 starts at the list's first event, the head cards riding along, through turn 15")
        self.assertEqual(n["events"][0]["uuid"], whole[0]["uuid"], "the first event served is the first card")

    def test_a_socket_before_its_ready_gets_no_chat_frame_and_its_ready_brings_the_declared_wire(self):
        # round eleven: the kernel used to serve INDEX frames to a socket that had not yet sent `ready` (the pusher fires from the socket's
        # open, the bundle evaluates later), so a proto-2 page whose ready lost that race held an index frame at its reload restore and
        # landed through the older wire (the mid-run reload red on CI: a reload-restore write, then loadOlder, loadAround 0)
        whole, m, frame, c = self._boot()
        fresh = {"send": (lambda s: sent.append(json.loads(s))), "echat": {}, "handshake": False}   # a real socket before its ready, as the accept marks it
        sent = []
        rows = []
        from unittest import mock
        with mock.patch.object(km, "_client_diag_append", lambda fp, line: rows.append((fp.name, json.loads(line)))):
            km._send_chat_locked(fresh, m, None, 0, False)
            km._send_chat_locked(fresh, m, None, 0, False)                          # a second push while the handshake is still out
            self.assertEqual(rows, [], "the routine pre-ready race files nothing while the socket is open (the tidy after PR 1642, low 1): %r" % rows)
            self.assertEqual(fresh["withheld"], 2, "…the withheld frames are counted on the record")
            # the permanent case: the socket closes without its handshake: ONE row, with the count, at the close
            gone = dict(fresh, sock=None, t0=km._ws_clock() - 30.0)
            self.assertTrue(km._note_chat_withheld_at_close(gone), "a socket closing unhandshaken with frames withheld files the row")
            self.assertEqual([(n, r["what"], r["surface"], r["data"]["frames"]) for n, r in rows], [("client-diag.jsonl", "chatWithheld", "kernel", 2)], "one row, the frames counted: %r" % rows)
            self.assertGreaterEqual(rows[0][1]["data"]["ageS"], 29.0, "…and the socket's age: %r" % rows[0][1]["data"])
            # the routine case at its close: the handshake came, so nothing is filed however many frames were withheld before it
            self.assertFalse(km._note_chat_withheld_at_close(dict(fresh, handshake=True)), "a socket whose handshake came files no row at its close")
            self.assertEqual(len(rows), 1)
        self.assertEqual(sent, [], "a socket before its ready gets no chat frame: %r" % [f.get("type") for f in sent])
        self.assertNotIn(SID, fresh["echat"], "…and the kernel believes it holds nothing")
        fresh["proto"] = 2; fresh["handshake"] = True                               # the handshake declares the uuid wire
        km._send_chat_locked(fresh, m, None, 0, False)
        self.assertEqual([f.get("type") for f in sent], ["session"], "the first frame after the handshake is the session")
        self.assertEqual(sent[0].get("proto"), 2, "…in the wire the handshake declared: %r" % {k: sent[0].get(k) for k in ("proto", "tailLo", "headFrom")})
        self.assertIsInstance(sent[0].get("tailLo"), int, "a proto-2 frame names the tail run's first turn")

    def test_an_older_vintage_sockets_first_frame_stands_as_a_proto1_handshake_and_a_silent_socket_stays_withheld(self):
        """2026-09-18: an older hub's relay socket (no proto term, no ready ever: its page sent the ready to its local socket alone) and
        an older shim's redial (reconnect=1 with no proto term, its page's one ready acked long ago) were held silent for the socket's
        life by the round-eleven gate above; the first client frame from such a socket now stands as a proto-1 handshake
        (_implicit_handshake) and the socket is served the index wire from there. The rule reads the client's VINTAGE, never the
        frame's kind (review round 1, 2026-09-18): a current page's relay (a namespaced iid), the VS Code extension host's pipe
        (client=ext) and a non-chat socket are never taken, whatever they send first, and neither `delta` nor `reconnect` is read,
        since the older shim's redial carries both. The decision table, then the wire it brings, then the real ready that
        re-declares the wire; the silent socket's withhold and its chatWithheld row are pinned by the test above and stand."""
        whole, m, frame, c = self._boot()
        sent, rows = [], []
        real_append = km._client_diag_append
        km._client_diag_append = lambda fp, line: rows.append(json.loads(line))
        self.addCleanup(setattr, km, "_client_diag_append", real_append)
        relay = {"send": (lambda s: sent.append(json.loads(s))), "echat": {}, "handshake": False, "ready": True, "kind": "relay", "app": "chat", "wid": "w1"}
        km._send_chat_locked(relay, m, None, 0, False)                                  # a pusher cycle before any frame from the peer
        self.assertEqual(sent, [], "withheld before the first frame"); self.assertEqual(relay["withheld"], 1)
        ask = {"type": "needFull", "id": SID}
        BARE_IID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"      # the shim mints a uuid per page load; a current hub's relay namespaces it: "<wid>:<uuid>"

        def declined(client, msg, why):
            """A cell that is not taken: the record untouched, nothing said, no row filed, the pusher not woken."""
            before, nrows = dict(client), len(rows)
            km._pusher_wake.clear()
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertFalse(km._implicit_handshake(client, msg), why)
            self.assertEqual(client, before, why + ": the record is untouched")
            self.assertEqual(err.getvalue(), "", why + ": nothing said")
            self.assertEqual(len(rows), nrows, why + ": no row filed")
            self.assertFalse(km._pusher_wake.is_set(), why + ": the pusher is not woken")

        def taken(client, msg, why, stood_in):
            """A cell that is taken: proto 1, the frame on the record, said once, the pusher woken (a settings post wakes nothing itself)."""
            km._pusher_wake.clear()
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertTrue(km._implicit_handshake(client, msg), why)
            self.assertEqual((client["handshake"], client["proto"], client["implicitHandshake"]), (True, 1, stood_in), why)
            self.assertEqual(err.getvalue().count("stands as a proto-1 handshake"), 1, why + ": " + err.getvalue())
            self.assertTrue(km._pusher_wake.is_set(), why + ": the pusher wakes on the event")
            return err.getvalue()

        # not taken: a ready (the arm declares the wire itself); an undecodable frame; a decodable frame that is not an object; a socket
        # held under READY_GATE_CAP (a kernel-served pane before its bundle's ready, whose shim flushes queued clientDiag rows at its
        # open); a socket already handshaken; a record without the mark (a test's dict modelling a socket past its handshake)
        declined(relay, {"type": "ready", "proto": 2}, "a ready")
        declined(relay, None, "an undecodable frame")
        for odd in (["needFull"], "needFull", 3):
            declined(relay, odd, "a decodable frame that is not an object: %r" % (odd,))
        declined(dict(relay, ready=False, kind="page"), {"type": "clientDiag", "surface": "pane-shim", "what": "wsclose", "data": {"app": "chat"}}, "a held page's flushed row")
        declined(dict(relay, handshake=True, proto=2), ask, "a socket already handshaken")
        declined({"send": relay["send"], "echat": {}}, ask, "a record without the mark")
        # ...nor, whatever it sends first, a socket of CURRENT vintage or one that carries no chat wire (review round 1):
        # a feed relay (no chat frame is ever sent to it, so there is no wire to declare and nothing to say); a current page's relay,
        # told by the namespaced iid federation.ts has dialled since 8fe70da07 (its held setting used to pin a proto-2 page to proto 1
        # and serve it an index frame before its ready); the VS Code extension host's pipe (client=ext at accept: it forwards its
        # webview's own ready, and a replayed intent on its reconnect must not stand in for it)
        declined(dict(relay, app="feed"), {"type": "setAutoNudge", "value": True}, "a feed relay")
        declined(dict(relay, app="fleet"), ask, "an Outline relay")
        declined(dict(relay, iid="hubwid:" + BARE_IID, delta=True), {"type": "setAutoNudge", "value": True}, "a current page's relay, a held setting first")
        declined(dict(relay, iid="hubwid:" + BARE_IID, delta=True), {"type": "activeTab", "id": SID}, "a current page's relay, its active tab first")
        declined(dict(relay, iid="hubwid:" + BARE_IID, delta=True), ask, "a current page's relay, an ask first")
        declined(dict(relay, kind="page", ext=True, delta=True), {"type": "sendMessage", "id": SID, "text": "a replayed intent"}, "the extension host's pipe")
        declined(dict(relay, kind="page", ext=True, delta=True), {"type": "closeTab", "id": SID}, "the extension host's pipe, a non-drive intent")
        # taken: the first frame of an older-vintage chat socket that is ready from accept, said once on stderr and filed once as a
        # kernel-surface row beside the socket's wsopen row; the second frame changes nothing
        said = taken(relay, ask, "the older hub's bare relay", "needFull")
        self.assertIn("a relay socket (app chat) declared no chat wire; its first frame (needFull) stands as a proto-1 handshake, 1 chat frame(s) withheld before it", said)
        self.assertEqual([(r["surface"], r["what"], r["wid"], r["data"]) for r in rows],
                         [("kernel", "implicitHandshake", "w1", {"app": "chat", "kind": "relay", "frame": "needFull", "withheld": 1, "proto": 1})], rows)
        self.assertIsInstance(rows[0]["t"], int)
        self.assertLessEqual(set(rows[0]["data"]), km.CLIENT_DIAG_KEYS["kernel"], "the kernel surface's allowlist entry names the row's keys")
        declined(relay, {"type": "activeTab", "id": SID}, "once: the mark has lifted")
        # ...and the wire it brings is the index wire, the one every older producer speaks
        km._send_chat_locked(relay, m, None, 0, False)
        self.assertEqual([f.get("type") for f in sent], ["session"], "the next push serves the session")
        f = sent[0]
        self.assertNotEqual(f.get("proto"), 2, "the index wire, not the uuid wire: %r" % {k: f.get(k) for k in ("proto", "firstUuid", "tailLo", "headFrom")})
        self.assertNotIn("firstUuid", f); self.assertNotIn("lastUuid", f)
        self.assertIsInstance(relay["echat"][SID], tuple, "the index base (head uuid, headFrom), never a proto-2 dict: %r" % (relay["echat"][SID],))
        self.assertTrue(km._chat_floor0_of([relay]), "an index client: the floor drops to 0 for it, as for a ready that names no proto")
        self.assertFalse(km._note_chat_withheld_at_close(relay), "served: the frames withheld before its first frame file no row at its close")
        # a real ready after the implicit handshake re-declares the wire (proto 2), resets the base (_client_reset_chat_base) and pops
        # the implicit mark from the record: the next push serves the uuid wire over a dict base, as for any ready
        class _Self:
            def _push_one(self, client): pass
        del sent[:]
        with contextlib.redirect_stderr(io.StringIO()):
            km.Handler._dispatch_ws(_Self(), {"type": "ready", "proto": 2}, relay)
        self.assertEqual((relay["handshake"], relay["proto"], relay.get("ready")), (True, 2, True), "the ready arm re-declares the wire")
        self.assertNotIn("implicitHandshake", relay, "the stand-in is popped: the socket has declared its wire")
        self.assertEqual(relay["echat"], {}, "the base is reset by the arm")
        km._send_chat_locked(relay, m, None, 0, False)
        sessions = [f for f in sent if f.get("type") == "session"]
        self.assertEqual(len(sessions), 1, [f.get("type") for f in sent])
        self.assertEqual(sessions[0].get("proto"), 2, "the uuid wire from here")
        self.assertIn("firstUuid", sessions[0])
        self.assertIsInstance(relay["echat"][SID], dict, "a proto-2 base: %r" % (relay["echat"][SID],))
        self.assertEqual([r["what"] for r in rows], ["implicitHandshake"], "the durable record of the event stands in the file")
        # the older shim's redial after this kernel restarted: reconnect=1 and no proto term (stamped ready at accept), delta=1 and a BARE
        # uuid iid like every shim's dial, and the wsclose row the shim flushes at the redial's open is its first frame; the same road.
        # Neither delta nor reconnect may key the decline: this socket carries both (reconnect is popped by the first pusher cycle)
        redial = {"send": (lambda s: None), "echat": {}, "handshake": False, "ready": True, "reconnect": True, "redial": True, "delta": True,
                  "caps": {"readyGate"}, "iid": BARE_IID, "kind": "page", "app": "chat", "wid": "w2"}   # ready: the hold it announced, lifted by reconnect=1
        taken(redial, {"type": "clientDiag", "surface": "pane-shim", "what": "wsclose", "data": {"app": "chat"}}, "the older shim's redial", "clientDiag")
        taken(dict(redial, handshake=False, reconnect=False), ask, "the same redial once the first cycle popped reconnect", "needFull")
        # the branches the first cut left unpinned (review round 1): a frame with no type stands in as `other` (review round 2; "?" before
        # the vocabulary below); a record with the mark and no ready key reads as ready from accept (the accept path stamps every socket,
        # so the default is never read live)
        taken(dict(relay, handshake=False, proto=None, echat={}), {"id": SID}, "a frame with no type", "other")
        taken({"send": relay["send"], "echat": {}, "handshake": False, "kind": "relay", "app": "chat"}, ask, "a record with no ready key", "needFull")
        # a first frame's type is CLIENT TEXT until it matches an op the kernel accepts (review round 2, the privacy check): the record,
        # the stderr line and the row quote a word from WS_OPS or `other`, never the type itself, so free text, a sid-shaped string and
        # the content of a dict or list type never reach client-diag.jsonl or the kernel log; the socket is taken all the same
        PLANTED = "PLANTED-FREE-TEXT-7c1d"
        for odd_type, why in ((PLANTED + " path=/srv/notes/private.md", "a free-text type"),
                              ("11111111-2222-3333-4444-000000000001", "a sid-shaped type"),
                              ({"leak": PLANTED}, "a dict type"),
                              ([PLANTED, "11111111-2222-3333-4444-000000000001"], "a list type"),
                              (7, "a number type")):
            nrows = len(rows)
            said = taken(dict(relay, handshake=False, proto=None, echat={}), {"type": odd_type, "id": SID}, why, "other")
            self.assertEqual(len(rows), nrows + 1, why + ": one row filed")
            self.assertEqual(rows[-1]["data"], {"app": "chat", "kind": "relay", "frame": "other", "withheld": 1, "proto": 1}, why + ": the row reads the word")
            self.assertIn("its first frame (other) stands as a proto-1 handshake", said, why)
            for text in (PLANTED, "11111111-2222", "/srv/notes", "leak"):
                self.assertNotIn(text, json.dumps(rows[-1]) + said, why + ": planted text on the row or stderr: %r" % text)
        # a file failure never touches the socket: the row is a courtesy to the reader of the file
        def refuse(fp, line):
            raise OSError("the state directory is unwritable")
        nrows = len(rows)
        km._client_diag_append = refuse
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(km._implicit_handshake(dict(relay, handshake=False, echat={}), ask), "taken with the row refused")
        self.assertEqual(len(rows), nrows, "the refused row is not in the file: %r" % [r["what"] for r in rows])

    def test_the_word_a_kernel_record_quotes_a_frame_type_from_is_the_dispatchs_own_vocabulary(self):
        """WS_OPS (review round 2) is the set of op names _dispatch_ws's arms, _drive's ID_OPS and _TARGET_NAME_OPS test a client
        frame's type against, and _ws_op_word maps a type to its member or to `other`. Pinned equal to the literals in the source, so
        an arm added without its name fails here instead of reading as `other` in the implicitHandshake row for good."""
        disp = inspect.getsource(km.Handler._dispatch_ws)
        ops = set()
        for m in re.finditer(r'msg(?:\.get\("type"\)|\["type"\]) (?:==|in) (\("[^)]*"\)|"\w+")', disp):
            ops.update(re.findall(r'"(\w+)"', m.group(1)))
        self.assertGreater(len(ops), 90, "the dispatch's arms were found in its source")
        drive = inspect.getsource(km._drive)
        ops.update(re.findall(r'"(\w+)"', re.search(r"ID_OPS = \((.*?)\)\n", drive, re.S).group(1)))
        ops.update(re.findall(r't == "(\w+)"', drive))
        ops.update(km._TARGET_NAME_OPS)
        self.assertEqual(set(km.WS_OPS), ops, "WS_OPS is exactly what the dispatch and the drive accept; missing %r, extra %r"
                         % (sorted(ops - km.WS_OPS), sorted(km.WS_OPS - ops)))
        self.assertNotIn("other", km.WS_OPS, "the placeholder is no op")
        for w in km.WS_OPS:
            self.assertRegex(w, r"^[A-Za-z]+$", "a word: %r" % (w,))
        for t, want in (("needFull", "needFull"), ("ready", "ready"), ("sendMessage", "sendMessage"), ("NEEDFULL", "other"), ("needFull ", "other"),
                        ("", "other"), (None, "other"), ({"type": "needFull"}, "other"), (["needFull"], "other"), (7, "other"), (True, "other")):
            self.assertEqual(km._ws_op_word(t), want, repr(t))

    def test_load_newer_is_retired(self):
        self._boot()
        r = km._chat_history_reply(SID, {"type": "loadNewer", "id": SID, "after": "11111111-2222-3333-4444-000000000001"}, NOW)
        self.assertTrue(r.get("missing") and r.get("retired"), "the walk toward the tail is gone: the tail run is always resident (T386 stage 2): %r" % r)


if __name__ == "__main__":
    unittest.main()
