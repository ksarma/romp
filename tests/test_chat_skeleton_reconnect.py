#!/usr/bin/env python3
"""Reconnect skeletons — the kernel half (the user 2026-09-07, whose panes redialed after a long freeze and
pulled every session whole for the one tab on screen).

When a pane's socket died while its browser tab was away (a long freeze, a laptop sleep, a network change),
the redial used to be served as a client that holds nothing: a full {type:"session"} for EVERY tab — 17 frames,
~9 MB on the measured board — for one tab on screen. The page still holds every session it had; it only needs
the one it shows. Now a redial after the bundle's ready declares itself (?reconnect=1, test_pane_shim_return.py) and
the kernel sends THAT client the tab strip with a `skeleton` list (every listed tab but the active one, cheapest
transcript first), the active tab's full session, and a small status frame per skeleton tab so its chip stays
honest. A skeleton tab loads on the user's click (activeTab / needFull), on the client's idle prefetch
(needFull), or on any full the kernel sends for another reason; `ready` (a renderer that just evaluated, so it
holds nothing) clears the whole set. A client that declares no reconnect gets today's frames, byte for byte.

Drives the REAL _push / _push_session_now / _confirm_close_now / Handler._dispatch_ws / Handler._ws over fake
clients (the test_tab_meta_push.py pattern), with build_session stubbed to synthetic payloads and real temp
transcript files of distinct sizes (the size is the kernel's cost proxy). Synthetic only: the notes-api demo
world (web/api/tests/docs), placeholder UUIDs, TESTHOST.
"""
import contextlib
import inspect
import io
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_skeleton", os.path.join(BIN, "romp-kernel"))

S1 = "11111111-2222-3333-4444-555555555551"   # web   — the tab the page is looking at (mid-size transcript)
S2 = "11111111-2222-3333-4444-555555555552"   # api   — the BIGGEST transcript
S3 = "11111111-2222-3333-4444-555555555553"   # tests — the smallest transcript
S4 = "11111111-2222-3333-4444-555555555554"   # docs  — just created: no transcript on disk yet
GONE = "11111111-2222-3333-4444-555555555559"  # an ended session, listed nowhere
NAMES = {S1: "web", S2: "api", S3: "tests", S4: "docs"}
TAB_ORDER = [S2, S1, S3, S4]                  # big, mid, small — the tab order is NOT the size order
SIZES = {S2: 3000, S1: 2000, S3: 1000}        # transcript bytes; S4 has none
# the journal of a tap that parked on the named road and was landed by the redial's first strip (item 12)
REDIAL_TRAIL = r"\[reveal\] %s sid=\S+ wid=W1: parked[\s\S]*\[reveal\] sid=\S+ wid=W1: consumed \S+ the pane's redial"
# the record the parked-reveal preference files when it applies (pass 5, the author's label, taking the reviewer's round-4 finding kernel-2): the session served whole, the page's hint, its fate
PREFERRED_LINE = r"\[reveal\] sid=%s wid=W1: preferred at the set's resolve, the one full in place of the page's hint %s \(%s\)"


def _sess(sid, n, state):
    """A synthetic build_session payload: n events (well under WIRE_TAIL, so a full send is the whole thing)."""
    return {"type": "session", "id": sid, "name": NAMES[sid],
            "events": [{"kind": "assistant", "uuid": "u%d" % i, "md": "m%d" % i} for i in range(n)],
            "status": {"state": state, "sinceEpoch": None}, "ledger": None}


class _Self:
    """The handler's `self` for _dispatch_ws: only _push_one is reached by the frames driven here. Records
    the call; runs `push_one` when given one (the real body is _push([client], connect=True))."""
    def __init__(self, push_one=None):
        self.calls = []
        self._po = push_one

    def _push_one(self, client):
        self.calls.append(client)
        if self._po:
            self._po(client)


def _fake_self(path):
    """A connect handler with a peer that closes at once (the test_view_deltas.py HandlerWiring shape)."""
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


class _DepthLock:
    """Stands in for a client's slot RLock (`dlock`, what _client_lock returns) and records what a lock pin needs by
    execution: `holds`, how many times it was taken, and `depth`, how deep it is held right now, so a spy inside the
    hold can read whether the lock came first (test_11f)."""

    def __init__(self):
        self.holds = 0
        self.depth = 0

    def __enter__(self):
        self.holds += 1
        self.depth += 1
        return self

    def __exit__(self, *exc):
        self.depth -= 1
        return False


class SkeletonReconnect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.paths = {}
        for sid, n in SIZES.items():          # real files: os.path.getsize is the kernel's ranking, so it must stat
            p = os.path.join(self.tmp, sid + ".jsonl")
            with open(p, "w") as f:
                f.write("x" * n)              # content is irrelevant to the kernel here; the SIZE is the cost proxy
            self.paths[sid] = p
        self.paths[S4] = os.path.join(self.tmp, S4 + ".jsonl")   # never written: the transcript-less session
        self.SESS = {S1: _sess(S1, 5, "working"), S2: _sess(S2, 7, "working"),
                     S3: _sess(S3, 3, "waiting"), S4: _sess(S4, 0, "waiting")}
        self._saved = (km._chat_tab_sessions, km._live_map, km._cached_feed, km.build_session,
                       km._comments_frame, km._push_subagents, km.NAMES, km.jd.STATE, list(km._clients))
        km._chat_tab_sessions = lambda now, live_map: [
            {"sid": sid, "name": NAMES[sid], "path": self.paths[sid], "anchor": sid} for sid in TAB_ORDER]
        km._live_map = lambda: {}
        km._cached_feed = lambda *a, **k: None          # no feed build — the chat frames are what is pinned
        self.built = []

        def build(sid, now, live_map=None, **kw):
            self.built.append(sid)
            return json.loads(json.dumps(self.SESS[sid]))   # a fresh copy per build, as the real builder returns
        km.build_session = build
        km._comments_frame = lambda sid, live_map: None
        km._push_subagents = lambda clients, now, live_map: None
        km.NAMES = Path(self.tmp) / "names"
        km.NAMES.mkdir()
        km.jd.STATE = Path(self.tmp) / "state"
        km.jd.STATE.mkdir(parents=True, exist_ok=True)
        km._built_chat.clear()
        km._prev_chat_events.clear()
        km._prev_chat_ledger.clear()
        del km._clients[:]
        km._pusher_wake.clear()

    def tearDown(self):
        (km._chat_tab_sessions, km._live_map, km._cached_feed, km.build_session,
         km._comments_frame, km._push_subagents, km.NAMES, km.jd.STATE, clients) = self._saved
        del km._clients[:]
        km._clients.extend(clients)
        km._built_chat.clear()
        km._prev_chat_events.clear()
        km._prev_chat_ledger.clear()

    # ── helpers ──
    def _client(self, **kw):
        frames = []
        c = {"app": "chat", "alive": True, "sent": {}, "send": lambda s: frames.append(json.loads(s)),
             "_frames": frames}
        c.update(kw)
        return c

    @staticmethod
    def _frames(c, typ=None):
        return [f for f in c["_frames"] if typ is None or f["type"] == typ]

    def _sessions(self, c):
        return [f["id"] for f in self._frames(c, "session")]

    def _statuses(self, c):
        return [(f["id"], f["status"]) for f in self._frames(c, "status")]

    def _tab_orders(self, c):
        return self._frames(c, "tabOrder")

    @staticmethod
    def _names(ids):
        """Tab names for a list of sids (the four synthetic tabs), so a red reads as tabs and not as ids the box's log
        redactor masks (an unknown id is kept as it is)."""
        return [NAMES.get(i, i) for i in ids]

    # ── §4.1 item 1 ──
    def test_00a_a_sid_already_held_whole_is_never_listed_when_the_set_resolves(self):
        # a full that won the race (a create's _push_session_now landing between the flag's pop and the set's write)
        # used to be re-listed as skeleton and then starved of tails (review find 2026-09-07): the resolve is atomic
        # under the client lock now, and a sid echat already holds is excluded outright
        import inspect
        c = self._client(active=S1, reconnect=True)
        c.setdefault("echat", {})[S3] = ("11111111-2222-3333-4444-555555555553", 0)
        km._push([c])
        self.assertEqual(self._tab_orders(c)[0]["skeleton"], [S2], "S3 is held whole → not a skeleton")
        self.assertEqual(c["skeleton"], {S2})
        self.assertTrue(c["skeleton"].isdisjoint(c["echat"]), "the two stores never both hold a sid")
        src = inspect.getsource(km._resolve_reconnect)
        self.assertLess(src.index("with _client_lock(c):"), src.index('c.pop("reconnect"'), "flag, stats and write: one locked step")

    def test_00b_a_skeleton_sid_whose_session_left_the_strip_leaves_the_set_and_its_status_slot(self):
        c = self._client(active=S1, reconnect=True)
        km._push([c])
        self.assertEqual(c["skeleton"], {S2, S3})
        orig = km._chat_tab_sessions
        km._chat_tab_sessions = lambda now, live_map: [s for s in orig(now, live_map) if s["sid"] != S3]   # S3 ended
        try:
            km._push([c])
        finally:
            km._chat_tab_sessions = orig
        self.assertEqual(c["skeleton"], {S2}, "a session the strip no longer lists is not a skeleton (review find 2026-09-07)")
        self.assertEqual(self._tab_orders(c)[-1]["skeleton"], [S2], "…and no strip names a sid its order lacks")
        self.assertNotIn(("status", S3), c["sent"], "its status slot went with it")

    def test_01_a_reconnecting_client_gets_the_strip_with_skeleton_and_one_full(self):
        c = self._client(active=S1, reconnect=True)
        km._push([c])
        self.assertEqual(self._sessions(c), [S1, S4],
                         "one full for the tab on screen — plus the transcript-less one, which is never a skeleton")
        to = self._tab_orders(c)
        self.assertEqual(len(to), 1)
        self.assertEqual(to[0]["order"], TAB_ORDER)
        self.assertEqual(to[0]["skeleton"], [S3, S2],
                         "ascending transcript size (small, big) — NOT tab order (big, small), and never the active")
        self.assertEqual(sorted(self._statuses(c)),
                         sorted([(S2, self.SESS[S2]["status"]), (S3, self.SESS[S3]["status"])]),
                         "one status frame per skeleton sid, carrying that session's status")
        self.assertEqual(c["skeleton"], {S2, S3})
        self.assertEqual(c["skeletonOrder"], [S3, S2])
        self.assertEqual(set(c["echat"]), {S1, S4}, "echat knows only the tabs that were sent whole")
        for sid in (S2, S3):
            self.assertNotIn(("chat", sid), c["sent"], "a skeleton sid never took the chat slot")
            self.assertIn(("status", sid), c["sent"], "…it rode its own status slot")
        self.assertIsNone(c.get("reconnect"), "one-shot: the first strip sender consumed it")
        types = [f["type"] for f in c["_frames"]]
        self.assertNotIn("chatTail", types)
        self.assertLess(types.index("tabOrder"), types.index("session"), "strip first")
        first_sess = self._frames(c, "session")[0]
        self.assertEqual(first_sess["id"], S1, "the active tab's full is the first session frame")
        self.assertLess(c["_frames"].index(first_sess), c["_frames"].index(self._frames(c, "status")[0]),
                        "the status frames trail the active full")

    # ── item 2 ──
    def test_02_the_next_cycle_sends_no_skeleton_sid_and_its_status_dedups(self):
        c = self._client(active=S1, reconnect=True)
        km._push([c])
        c["_frames"].clear()
        km._push([c])
        self.assertEqual([f for f in c["_frames"] if f["type"] in ("session", "chatTail") and f["id"] in (S2, S3)],
                         [], "no chat of any shape for a skeleton sid")
        self.assertEqual(self._statuses(c), [], "an unchanged status is deduped on its slot")
        for sid in (S2, S3):
            self.assertIsNone(km._built_chat[sid][2],
                              "the lazy full serialization was never materialized for a skeleton sid")
        self.assertIsNotNone(km._built_chat[S1][2], "…while the active tab's full send did materialize it")
        # a real transition: the status changes WITH the transcript, as it does live (the build cache keys on the
        # file stat) → exactly one status frame, for that sid, and still no full
        self.SESS[S2]["status"]["state"] = "waiting"
        with open(self.paths[S2], "a") as f:
            f.write("y")
        c["_frames"].clear()
        km._push([c])
        self.assertEqual(self._statuses(c), [(S2, {"state": "waiting", "sinceEpoch": None})])
        self.assertEqual(self._sessions(c), [], "still no full for a skeleton sid")
        self.assertEqual(c["skeleton"], {S2, S3}, "a status change releases nothing")

    # ── item 3 ──
    def test_03_activetab_releases_exactly_one_and_wakes_the_pusher(self):
        c = self._client(active=S1, reconnect=True)
        km._push([c])
        c["_frames"].clear()
        km._pusher_wake.clear()
        km.Handler._dispatch_ws(_Self(), {"type": "activeTab", "id": S2}, c)
        self.assertEqual(c["skeleton"], {S3}, "only the clicked tab left the set")
        self.assertEqual(c["active"], S2)
        self.assertTrue(km._pusher_wake.is_set(), "the click is the event the next cycle rides")
        self.assertNotIn(("status", S2), c["sent"], "its status slot went with it")
        km._push([c])
        self.assertEqual(self._sessions(c), [S2], "the released tab's full — and no S3")
        to = self._tab_orders(c)
        self.assertEqual(len(to), 1, "the strip is re-sent: its skeleton list changed, so its sig changed")
        self.assertEqual(to[0]["skeleton"], [S3])
        self.assertEqual(self._statuses(c), [], "S3's status is unchanged → deduped")

    def test_03b_activetab_naming_a_remote_or_unknown_id_releases_nothing(self):
        c = self._client(active=S1, reconnect=True)
        km._push([c])
        km.Handler._dispatch_ws(_Self(), {"type": "activeTab", "id": "gpu1:" + S2}, c)
        self.assertEqual(c["skeleton"], {S2, S3})
        km.Handler._dispatch_ws(_Self(), {"type": "activeTab", "id": None}, c)
        self.assertEqual(c["skeleton"], {S2, S3})

    # ── item 4 ──
    def test_04_needfull_releases_exactly_one_and_repairs_now(self):
        c = self._client(active=S1, reconnect=True)
        km._push([c])
        km.Handler._dispatch_ws(_Self(), {"type": "activeTab", "id": S2}, c)   # S2 loads on its click…
        km._push([c])
        c["_frames"].clear()
        h = _Self()                                                             # …S3 on the idle prefetch's ask
        km.Handler._dispatch_ws(h, {"type": "needFull", "id": S3, "why": "prefetch"}, c)   # `why` is the client's diagnostic; ignored here
        self.assertEqual(c["skeleton"], set(), "the set emptied")
        self.assertNotIn(("status", S3), c["sent"], "_client_reset_chat_sid popped the status slot with the release")
        self.assertEqual(h.calls, [c], "the repair push ran on the handler thread, not on the next tick")
        km._push([c], connect=True)                                             # what that _push_one does
        self.assertEqual(self._sessions(c), [S3])
        to = self._tab_orders(c)
        self.assertEqual(len(to), 1, "the strip changed (no set) → re-sent")
        self.assertEqual(to[0].get("skeleton"), [], "an empty set is SAID as [] once a set has existed: the federated merge keeps a host's last list on an absent key")

    # ── item 5 ──
    def test_05_a_push_session_now_full_releases(self):
        c = self._client(active=S1, reconnect=True)
        km._push([c])
        c["_frames"].clear()
        km._clients.append(c)
        km._push_session_now(S3)                       # a create / handshake for a tab the page holds as skeleton
        self.assertEqual(self._sessions(c), [S3], "the full went (change_from 0 → always the full form)")
        self.assertEqual(c["skeleton"], {S2}, "…and released S3 through _send_chat_locked")
        self.assertIn(("chat", S3), c["sent"])
        self.assertNotIn(("status", S3), c["sent"])
        self.assertEqual(self._tab_orders(c), [], "its strip was identical to the one already held → deduped")
        c["_frames"].clear()
        km._push([c])
        self.assertEqual(self._tab_orders(c)[0]["skeleton"], [S2], "the next cycle's strip says so")
        self.assertEqual(self._sessions(c), [], "S3 is now an ordinary held tab: no re-send")

    # ── item 6 ──
    def test_06_a_fresh_client_is_unchanged(self):
        c = self._client(active=S1)
        km._push([c])
        self.assertEqual(sorted(self._sessions(c)), sorted(TAB_ORDER), "every full, as today")
        self.assertEqual(self._statuses(c), [], "no status frames for a client that declared no reconnect")
        to = self._tab_orders(c)
        self.assertEqual(len(to), 1)
        self.assertEqual(set(to[0]), {"type", "order", "tabs", "views", "live", "selfHost"},
                         "today's frame, key for key (T258's `live` rides every strip; `selfHost` names the viewing "
                         "kernel since 2026-09-06): no new key for a client that did not declare a reconnect")
        for sid in TAB_ORDER:
            self.assertIn(("chat", sid), c["sent"])
        self.assertNotIn("skeleton", c)
        self.assertNotIn("skeletonOrder", c)
        self.assertFalse([k for k in c["sent"] if k[0] == "status"])

    def test_06b_ready_pops_the_set_and_the_repush_is_every_full(self):
        c = self._client(active=S1, reconnect=True)
        km._push([c])
        self.assertEqual(c["skeleton"], {S2, S3})
        c["_frames"].clear()
        c["reconnect"] = True                          # whatever the flag's state, the reset pops it before its push
        h = _Self(lambda cl: km._push([cl], connect=True))   # the real _push_one body
        km.Handler._dispatch_ws(h, {"type": "ready"}, c)
        for k in ("skeleton", "skeletonOrder", "reconnect"):
            self.assertNotIn(k, c, k)
        self.assertFalse([k for k in c["sent"] if k[0] == "status"], "every status slot went with the set")
        self.assertEqual(h.calls, [c])
        self.assertEqual(sorted(self._sessions(c)), sorted(TAB_ORDER), "the following push sends every full")
        self.assertNotIn("skeleton", self._tab_orders(c)[0], "no set → no key")

    # ── item 7 ──
    def test_07_no_active_hint_means_no_skeleton(self):
        c = self._client(reconnect=True)
        km._push([c])
        self.assertEqual(sorted(self._sessions(c)), sorted(TAB_ORDER), "the kernel cannot know what the page shows → everything")
        self.assertNotIn("skeleton", self._tab_orders(c)[0])
        self.assertNotIn("skeleton", c)
        self.assertIsNone(c.get("reconnect"), "consumed all the same")

    # ── item 8 ──
    def test_08_dedup_slots_flip_from_status_to_chat_on_release(self):
        c = self._client(active=S1, reconnect=True)
        km._push([c])
        self.assertIn(("status", S2), c["sent"])
        self.assertNotIn(("chat", S2), c["sent"])
        km.Handler._dispatch_ws(_Self(), {"type": "activeTab", "id": S2}, c)
        self.assertNotIn(("status", S2), c["sent"], "the release drops the status slot at once")
        km._push([c])
        self.assertIn(("chat", S2), c["sent"])
        self.assertNotIn(("status", S2), c["sent"])

    # ── item 9 ──
    def test_09_the_handshake_records_the_flag_and_wakes_the_pusher(self):
        # the third dial is a later chat column's FIRST (the split, 2026-09-11): skeleton=1 arms `reconnect` like a redial
        # AND `skeletonOnReady`, the flag the ready arm's reset spares (test_11_a runs the cycle). The fourth is that
        # column's REDIAL (the shim reads skeleton=1 off the address on every dial, reconnect=1 once its gate passes):
        # `reconnect` alone — its page said ready on an earlier socket, so no arm would ever pop the flag, and armed it
        # left the client unstamped for the page's life (review find 2026-09-11; test_11_c runs the cycle)
        for path, expect, view, flag, diet in (("/ws?app=chat&delta=1&iid=page-9&active=%s&reconnect=1" % S1, True, False, False, False),
                                         ("/ws?app=chat&delta=1&iid=page-9&active=%s" % S1, False, False, False, False),
                                         ("/ws?app=chat&delta=1&iid=page-9&active=%s&col=2&skeleton=1" % S1, True, True, True, True),
                                         ("/ws?app=chat&delta=1&iid=page-9&active=%s&col=2&reconnect=1&skeleton=1" % S1, True, True, False, True),
                                         ("/ws?app=feed&delta=1&iid=page-9&active=%s&skeleton=1" % S1, False, False, False, False)):   # a non-chat socket carrying the term arms nothing (PR 1661 round two; the follow-up's executed row)
            got = []
            real_reg, real_recv = km._register_ws_client, km._ws_recv
            km._register_ws_client = lambda c: (got.append(c), km._clients.append(c))
            km._ws_recv = lambda rfile: (0x8, b"", True)              # the peer closes at once
            km._pusher_wake.clear()
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    km.Handler._ws(_fake_self(path))
            finally:
                km._register_ws_client, km._ws_recv = real_reg, real_recv
                for c in got:
                    if c in km._clients:
                        km._clients.remove(c)
            self.assertEqual(len(got), 1, path)
            c = got[0]
            self.assertEqual(c.get("active"), S1)
            self.assertEqual(c.get("iid"), "page-9")
            self.assertTrue(c.get("delta"))
            if expect:
                self.assertIs(c.get("reconnect"), True, path)
                self.assertTrue(km._pusher_wake.is_set(), "the reconnect is the event; no backstop wait")
            else:
                self.assertIsNone(c.get("reconnect"), path)
                self.assertFalse(km._pusher_wake.is_set(), "a fresh page wakes nothing new")
            if view:
                self.assertEqual(c.get("col"), "2")
            if flag:
                self.assertIs(c.get("skeletonOnReady"), True, "a later chat column's first dial: the flag that survives the ready arm's reset")
            else:
                self.assertNotIn("skeletonOnReady", c, path + ": a redial (or no skeleton) arms no flag no arm would pop")
            if diet:
                self.assertIs(c.get("dietSkeleton"), True, path + ": a skeleton=1 chat dial marks the client dieted (durable), so a no-active resolve skeletons ALL its tabs")
            else:
                self.assertNotIn("dietSkeleton", c, path + ": no skeleton=1 (or a non-chat socket) marks no diet")

    # ── item 10 ──
    def test_10_source_pins_every_strip_sender_resolves_and_uses_the_one_builder(self):
        src = inspect.getsource(km)
        self.assertEqual(src.count('{"type": "tabOrder"'), 1,
                         "exactly one tabOrder literal in the kernel — inside _tab_order_frame, the builder that "
                         "carries the skeleton list; a hand-built frame would erase the set on the client")
        self.assertIn('{"type": "tabOrder"', inspect.getsource(km._tab_order_frame))
        # the three senders each hand the builder the cycle's liveness map (live_map; the fork's per-sender
        # collapse-guarded maps left with the tmux backend 2026-09-11): the prefix and the map are pinned per sender
        for fn in (km._push, km._push_session_now, km._confirm_close_now):
            s = inspect.getsource(fn)
            self.assertIn("_resolve_reconnect(c, chat_list)", s, fn.__name__)
            self.assertIn("_send_tab_order(c, tab_order, tab_meta, live_map)", s, fn.__name__)
            self.assertLess(s.index("_resolve_reconnect(c, chat_list)"), s.index("_send_tab_order(c, tab_order, tab_meta, live_map)"),
                            fn.__name__ + ": resolve BEFORE the strip")
            self.assertIn("_consume_pending_reveal(c", s, fn.__name__ + ": a redial's first strip consumes a parked reveal")
            self.assertLess(s.index("_send_tab_order(c, tab_order, tab_meta, live_map)"), s.index("_consume_pending_reveal(c"),
                            fn.__name__ + ": the strip BEFORE the focus it names a tab of")
        i = src.find('msg.get("type") == "ready"')
        body = src[i:i + 2600]
        self.assertNotIn("_send_tab_order(client", body,
                         "the ready arm sends no strip of its own: its connect push (_push_one) resolves the flag and sends the strip")
        self.assertNotIn('client["send"](json.dumps({"type": "tabOrder"', src, "no strip bypasses the builder")
        i = src.find('msg.get("type") == "activeTab"')
        body = src[i:i + 700]
        self.assertIn('_release_skeleton(client, str(msg["id"]))', body)
        self.assertLess(body.index("_release_skeleton("), body.index("_pusher_wake.set()"),
                        "release, THEN wake — the woken cycle must see the released sid")
        s = inspect.getsource(km._send_chat_locked)
        self.assertIn("_release_skeleton_locked(c, sid)", s)
        self.assertLess(s.index("head_from = max(0, total - WIRE_TAIL)"), s.index("_release_skeleton_locked(c, sid)"),
                        "in the FULL branch — after the tail branch has returned")
        self.assertIn("_release_skeleton_locked(client, sid)", inspect.getsource(km._client_reset_chat_sid))
        s = inspect.getsource(km._client_reset_chat_base)
        for k in ('client.pop("skeleton", None)', 'client.pop("skeletonOrder", None)',
                  'client.pop("reconnect", None)', 'k[0] in ("chat", "status", "taborder", "activeChat")'):
            self.assertIn(k, s)
        s = inspect.getsource(km._push)
        self.assertIn("_send_chat_or_status(c, m, ms, change_from, led_changed)", s)
        self.assertNotIn("= _send_chat(c, m, ms, change_from, led_changed)", s,
                         "the pusher's per-client send goes through the skeleton-aware twin")
        self.assertIn('+((everConnected&&bundleReady&&readyAcked&&!readyQueued)?"&reconnect=1&proto="+readyProto:"")', km._shim("chat", 1),
                      "the shim declares the redial once the kernel's caps frame has answered its bundle's ready")
        self.assertIn('if(msg&&msg.type==="caps")readyAcked=true;', km._shim("chat", 1),
                      "the latch is the caps frame, the ready arm's reply (_send_caps)")
        s = inspect.getsource(km.Handler._ws)
        self.assertIn('reconnect = (q.get("reconnect") or [""])[0] == "1"', s)
        self.assertIn('client["reconnect"] = True', s)
        self.assertLess(s.index("_register_ws_client(client)"),
                        s.index('if client.get("reconnect"):\n            _pusher_wake.set()'),
                        "registered first, then woken — the pusher must find the client in _clients")

    def test_10b_a_close_confirmation_as_the_first_strip_already_carries_the_set(self):
        # the behavioral twin: the ≤1-cycle gap between the handshake and the pusher's first pass, filled by an
        # off-cycle strip — it must not paint the page's stale sessions as loaded tabs
        c = self._client(active=S1, reconnect=True)
        km._clients.append(c)
        self.assertTrue(km._confirm_close_now(GONE))
        to = self._tab_orders(c)
        self.assertEqual(len(to), 1)
        self.assertEqual(to[0]["skeleton"], [S3, S2])
        self.assertEqual(c["skeleton"], {S2, S3})
        self.assertIsNone(c.get("reconnect"), "consumed by the confirmation, so the pusher's pass resolves nothing new")
        c["_frames"].clear()
        km._push([c])
        self.assertEqual(self._tab_orders(c), [], "the pusher's identical strip dedups")
        self.assertEqual(self._sessions(c), [S1, S4], "…and its fulls are exactly the reconnect set's complement")

    def test_10c_skeleton_for_ranks_by_size_skips_the_active_and_the_transcript_less(self):
        rows = km._chat_tab_sessions(0, {})
        self.assertEqual(km._skeleton_for({}, S1, rows), [S3, S2])
        self.assertEqual(km._skeleton_for({}, S3, rows), [S1, S2])
        self.assertEqual(km._skeleton_for({}, "gpu1:" + S1, rows), [S3, S1, S2],
                         "a remote/viewer/closed hint matches nothing: every local transcript is skeleton")
        self.assertEqual(km._skeleton_for({}, S1, rows + [{"sid": GONE, "path": None}]), [S3, S2],
                         "a path-less row is skipped, not a crash")

    # ── item 11 ──
    def test_11_every_touch_of_the_set_is_under_the_clients_slot_lock(self):
        src = inspect.getsource(km)
        lines = src.splitlines()

        def owners(token):
            """The defs whose bodies mention `token` (their own def line excluded)."""
            cur, found = None, set()
            for ln in lines:
                m = re.match(r"^\s*def (\w+)\(", ln)
                if m:
                    cur = m.group(1)
                    continue
                if token in ln:
                    found.add(cur)
            return found

        self.assertEqual(owners('"skeleton"') | owners('"skeletonOrder"'),
                         {"_client_reset_chat_base", "_release_skeleton_locked", "_resolve_reconnect",
                          "_skeleton_held_here",        # the cold-tab gate's reader (2026-09-14): the per-client predicate, read under
                          #                               its callers' hold (_held_as_skeleton_by_all per tab, _skeleton_census once per
                          #                               push for the warm-tab census, 2026-09-18)
                          "_send_light_status",         # ...and its status send, membership re-checked under the lock (round three)
                          "_tab_order_frame", "_send_chat_or_status", "_send_tab_order",
                          # the two READERS of the connect query's skeleton=1 term (a later chat column's dial,
                          # 2026-09-11): _ws sets the client's `reconnect` and `skeletonOnReady` flags from it, and
                          # _shim writes the term; neither touches the client's set
                          "_ws", "_shim"},
                         "the set is touched only in its helpers — a new site must join this list AND take the lock")
        for name in ("_client_reset_chat_base", "_resolve_reconnect", "_send_chat_or_status", "_send_tab_order"):
            s = inspect.getsource(getattr(km, name))
            self.assertLess(s.index("with _client_lock("), s.index('"skeleton"'), name + ": the lock comes first")
        # the three lock-free helpers (_release_skeleton_locked, _tab_order_frame, _skeleton_held_here) are reached only from
        # bodies that hold the lock
        self.assertEqual(owners("_release_skeleton_locked("),
                         {"_release_skeleton", "_send_chat_locked", "_send_chat_proto2", "_client_reset_chat_sid"})   # _send_chat_proto2: reached from _send_chat_locked alone (T323 stage 4b)
        self.assertEqual(owners("_tab_order_frame("), {"_send_tab_order"})
        for name in ("_release_skeleton", "_client_reset_chat_sid", "_send_tab_order"):
            s = inspect.getsource(getattr(km, name))
            self.assertLess(s.index("with _client_lock("), s.index("_release_skeleton_locked(" if name != "_send_tab_order" else "_tab_order_frame("), name)
        # the per-client skeleton predicate reads the set lock-free; its two callers, the cold gate's walk and the warm-tab
        # census, each take the client's slot lock first (2026-09-19 review, correctness-4: the predicate had no caller check).
        # That the two callers DO take the lock, and take it before the read, is pinned by execution in test_11f below: the
        # text pin that stood here (`with _client_lock(` in each caller's inspect.getsource, and its index before the
        # predicate's) was satisfied by a comment carrying the literal with the real lock gone (round two, 2026-09-19, tests-3)
        self.assertEqual(owners("_skeleton_held_here("), {"_held_as_skeleton_by_all", "_skeleton_census"},
                         "a new caller of the lock-free predicate must join this set AND pass test_11f's hold count")
        self.assertEqual(owners("_send_chat_locked("), {"_send_chat", "_send_chat_or_status"},
                         "_send_chat_locked has no lock-free caller")
        for name in ("_send_chat", "_send_chat_or_status"):
            s = inspect.getsource(getattr(km, name))
            self.assertLess(s.index("with _client_lock("), s.index("_send_chat_locked("), name)

    def test_11f_the_lock_free_predicates_two_callers_take_each_clients_slot_lock_first_by_execution(self):
        """_skeleton_held_here reads a client's skeleton set lock-free, so its two callers, the cold gate's walk
        (_held_as_skeleton_by_all) and the warm-tab census (_skeleton_census), must hold the client's slot lock across
        the call. Pinned by EXECUTION: every client's `dlock` is a _DepthLock (one hold counted per `with`, the nesting
        depth kept live) and a spy on the predicate records the depth of that client's lock at call time. The 2026-09-19
        round-2 review (tests-3) found the pin that stood in test_11, `with _client_lock(` in the caller's
        inspect.getsource text and its index before the predicate's, satisfied by a COMMENT carrying the literal with the
        real lock gone, the fifth source pin met by a comment; this test reds on that mutation (holds 0) and on the lock
        taken after the read (depth 0 at the call). test_11's owners() set-equality stays the gate a third caller must
        join; this is what it must then pass. Three clients in the shapes the census reads: a set holder, a reconnecting
        page whose set is not resolved yet (a watched tab and a tail believed held), and a relay diet page with no
        watched tab; S3 is the one tab all three hold."""
        clients = [self._client(skeleton={S1, S2, S3}, dlock=_DepthLock()),
                   self._client(reconnect=True, active=S1, echat={S2: 1}, dlock=_DepthLock()),
                   self._client(reconnect=True, dietSkeleton=True, kind="relay", dlock=_DepthLock())]
        calls = []
        real = km._skeleton_held_here

        def spy(c, sid):
            calls.append((clients.index(c), sid, c["dlock"].depth))
            return real(c, sid)

        def reset():
            for c in clients:
                c["dlock"].holds = c["dlock"].depth = 0
            del calls[:]

        def check(where):
            self.assertTrue(calls, where + ": the predicate ran")
            self.assertEqual([d for _i, _s, d in calls], [1] * len(calls),
                             where + ": every predicate call ran at depth 1 of its client's slot lock (the lock comes first)")
            for i, c in enumerate(clients):
                asked = sum(1 for j, _s, _d in calls if j == i)
                self.assertEqual(c["dlock"].holds, 1 if asked else 0,
                                 "%s: client %d held exactly once when asked (%d asks), never otherwise" % (where, i, asked))
        with mock.patch.object(km, "_skeleton_held_here", spy):
            # the gate's walk over the tab every client holds: one hold per client, the predicate under each
            self.assertTrue(km._held_as_skeleton_by_all(S3, clients))
            self.assertEqual([c["dlock"].holds for c in clients], [1, 1, 1], "_held_as_skeleton_by_all: one hold per client")
            check("_held_as_skeleton_by_all(S3)")
            reset()
            # over a tab the second client does not hold: the walk stops there, each client it reached held once and the
            # third never asked (a walk that asks every client and folds the answers reds here: the round-3 review)
            self.assertFalse(km._held_as_skeleton_by_all(S1, clients))
            check("_held_as_skeleton_by_all(S1)")
            self.assertEqual([c["dlock"].holds for c in clients], [1, 1, 0], "_held_as_skeleton_by_all(S1): the walk stopped at the second client")
            self.assertNotIn(2, [i for i, _s, _d in calls], "_held_as_skeleton_by_all(S1): the third client was never asked")
            reset()
            # the census over any number of tabs: one hold per client per call, every question under that hold
            for sids in ([S3], [S1, S2, S3], ["%08d-1111-2222-3333-444444444444" % i for i in range(38)] + [S3]):
                self.assertEqual(km._skeleton_census(sids, clients), {S3})
                self.assertEqual([c["dlock"].holds for c in clients], [1, 1, 1],
                                 "_skeleton_census over %d tabs: one hold per client per call, whatever the tab count" % len(sids))
                check("_skeleton_census over %d tabs" % len(sids))
                reset()

    # ── a later chat column: a skeleton client from its FIRST dial (the split, 2026-09-11) ──
    def test_11_a_skeleton_dial_survives_the_ready_reset(self):
        # The shell opens a later chat column as /chat?col=N&skeleton=1 with the column's state blob naming the session
        # it opens on, so the page's FIRST dial carries active=<sid>&skeleton=1 and _ws arms both flags (test_09). A
        # pusher cycle before the bundle's ready serves the strip (with the skeleton list) and the statuses into a
        # document that cannot hear it yet, and WITHHOLDS the session frames (review find 2026-09-11: the one full crossed
        # the wire twice per open); the ready arm's _client_reset_chat_base pops the set and `reconnect`, and the survivor
        # (`skeletonOnReady`) re-arms the flag for the connect push the page CAN hear — the same view, and THAT push's one
        # full is the only one. Until that ready the client is not stamped and a parked reveal stands: the arm's own stamp
        # and consume land it, as for any fresh page.
        km._PENDING_REVEAL.clear()
        km._live_map = lambda: {S1: {}}       # the tapped session is live, so the reveal is a focus, not a revive
        try:
            trail = io.StringIO()
            with contextlib.redirect_stderr(trail):
                self.assertFalse(km._reveal_request(S1, "W1", via="sw"), "a tap for the window parks: no ready pane yet")
            c = self._client(active=S1, reconnect=True, skeletonOnReady=True, wid="W1")
            # 1. the pusher's cycle BEFORE the ready: the set, the strip, a status per other tab — no session frame (the
            #    document cannot hear it, and the ready arm re-sends the one full anyway), no stamp, no consume
            with contextlib.redirect_stderr(trail):
                km._push([c])
            self.assertEqual(c["skeleton"], {S2, S3})
            to = self._tab_orders(c)
            self.assertEqual(len(to), 1)
            self.assertEqual(to[0]["skeleton"], [S3, S2], "the strip carries the set, as a redial's does")
            self.assertEqual(self._sessions(c), [], "no session frame before the ready: the connect push the arm makes is the one full")
            self.assertEqual(sorted(s for s, _ in self._statuses(c)), sorted([S2, S3]), "a status per other tab")
            self.assertEqual(c.get("echat") or {}, {}, "…and nothing is believed held: the arm's push sends the full, not a delta")
            self.assertNotIn("ready", c, "a pre-ready pop stamps nothing: the page has no listener yet")
            self.assertEqual(km._PENDING_REVEAL.get("W1"), {"sid": S1, "wid": "W1"}, "…and consumes nothing: the park stands for the ready arm")
            self.assertEqual(self._frames(c, "focus"), [])
            self.assertIsNone(c.get("reconnect"), "the pop consumed the handshake's flag")
            self.assertIs(c.get("skeletonOnReady"), True, "the survivor is untouched by the pop")
            self.assertNotIn("the pane's redial", trail.getvalue(), "no strip stood in for a ready: this page posts one")
            # 2. the ready arm: the reset pops the set and the flag, the survivor re-arms it, the connect push serves the
            #    same view again, the arm stamps the client and the park lands behind the strip
            c["_frames"].clear()
            h = _Self(lambda cl: km._push([cl], connect=True))   # the real _push_one body
            with contextlib.redirect_stderr(trail):
                km.Handler._dispatch_ws(h, {"type": "ready"}, c)
            self.assertEqual(h.calls, [c])
            self.assertNotIn("skeletonOnReady", c, "popped once, by the arm")
            self.assertIsNone(c.get("reconnect"), "re-armed past the reset and consumed by the connect push's resolve")
            self.assertEqual(c["skeleton"], {S2, S3}, "the set is back: the connect push served the view, not the board")
            to = self._tab_orders(c)
            self.assertEqual(len(to), 1, "the reset cleared the strip's slot, so the strip went again")
            self.assertEqual(to[0]["skeleton"], [S3, S2])
            self.assertEqual(self._sessions(c), [S1, S4], "the one full (+ the transcript-less), from this push alone")
            self.assertEqual(sorted(s for s, _ in self._statuses(c)), sorted([S2, S3]))
            self.assertIs(c.get("ready"), True)
            self.assertEqual(km._PENDING_REVEAL, {}, "the park was consumed at the ready")
            types = [f["type"] for f in c["_frames"]]
            self.assertEqual(types.count("focus"), 1, "one focus")
            self.assertLess(types.index("tabOrder"), types.index("focus"), "behind the strip that names its tab")
            self.assertEqual([(f["id"], f["live"]) for f in self._frames(c, "focus")], [(S1, True)])
            self.assertRegex(trail.getvalue(), r"\[reveal\] sw sid=\S+ wid=W1: parked[\s\S]*\[reveal\] sid=\S+ wid=W1: consumed")
            # 3. the next cycle: an ordinary skeleton client from here (test_02's regime), nothing parked
            c["_frames"].clear()
            with contextlib.redirect_stderr(trail):
                km._push([c])
            self.assertEqual(self._sessions(c), [], "no full for a skeleton sid, and the active is held")
            self.assertEqual(self._frames(c, "focus"), [])
        finally:
            km._PENDING_REVEAL.clear()

    def test_11_d_a_pusher_iteration_landing_in_the_ready_arms_gap_sends_no_full(self):
        # THE SECOND FULL ON A NEW COLUMN'S SOCKET (a slow runner, 2026-09-12; reproduced at the wire: 18 of 27 opens carried
        # full frames for sessions the column does not hold, up to six per open, and the page asked for none). The pusher
        # cycle the handshake woke is still in its per-session loop when the ready arm runs. The arm's reset pops the set
        # and `reconnect`, the survivor re-arms `reconnect`, and the arm's connect push rebuilds the set only at its own
        # _resolve_reconnect, past a liveness sweep and the tab list. In that gap the client had no set and no
        # `skeletonOnReady`, and _send_chat_or_status read nothing else: every session the pusher's loop visited fell
        # through to _send_chat_locked, a full for a tab the column holds as a skeleton, an echat entry, and the arm's
        # strip dropped the sid from its skeleton list as held whole. The guard reads `reconnect` too now (a client with
        # the flag armed has no set yet; the strip sender that pops it sends the active tab's full itself), and the reset
        # pops the survivor and re-arms under its own lock, so no instant exists with neither flag set.
        def in_the_gap(cl, sid):
            """The pusher's per-session iteration for `sid`, landing on the handler thread's _push_one: the instant after
            the arm's reset and re-arm, before its push's _resolve_reconnect."""
            self.assertNotIn("skeleton", cl, "the reset popped the set")
            self.assertNotIn("skeletonOnReady", cl, "…and the survivor")
            self.assertIs(cl.get("reconnect"), True, "…and re-armed the flag for the connect push")
            m = json.loads(json.dumps(self.SESS[sid]))
            km._send_chat_or_status(cl, m, None, len(m["events"]), False)
        # 1. the loop reaches a session the column does NOT hold (the wire shape: every extra full was another tab's)
        c = self._client(active=S1, reconnect=True, skeletonOnReady=True)
        km._push([c])                                 # the pre-ready cycle: the set, the strip, a status per other tab
        self.assertEqual(self._sessions(c), [])
        c["_frames"].clear()
        h = _Self(lambda cl: (in_the_gap(cl, S2), km._push([cl], connect=True)))
        with contextlib.redirect_stderr(io.StringIO()):
            km.Handler._dispatch_ws(h, {"type": "ready"}, c)
        self.assertEqual(h.calls, [c])
        self.assertEqual(self._sessions(c), [S1, S4], "the one full (+ the transcript-less): the pusher's iteration for S2 in the gap sent none")
        self.assertEqual(sorted(s for s, _ in self._statuses(c)), sorted([S2, S3]), "S2 is a status, as every other tab")
        to = self._tab_orders(c)
        self.assertEqual(len(to), 1)
        self.assertEqual(to[0]["skeleton"], [S3, S2], "S2 is still on the strip's skeleton list: no full won a race against the set")
        self.assertEqual(c["skeleton"], {S2, S3})
        self.assertEqual(sorted(c["echat"]), sorted([S1, S4]), "believed held: the active tab and the transcript-less, nothing else")
        types = [f["type"] for f in c["_frames"]]
        self.assertLess(types.index("tabOrder"), types.index("session"), "the strip is ahead of every full: the set's invariant")
        # 2. the loop reaches the ACTIVE session in the gap: its full crosses once, from the arm's push, behind the strip
        c = self._client(active=S1, reconnect=True, skeletonOnReady=True)
        km._push([c])
        c["_frames"].clear()
        h = _Self(lambda cl: (in_the_gap(cl, S1), km._push([cl], connect=True)))
        with contextlib.redirect_stderr(io.StringIO()):
            km.Handler._dispatch_ws(h, {"type": "ready"}, c)
        self.assertEqual([f["type"] for f in c["_frames"] if f.get("id") == S1 and f["type"] in ("session", "chatTail")], ["session"],
                         "one full for the active tab and no tail behind it: the iteration in the gap neither sent it nor left a base")
        self.assertEqual(self._sessions(c), [S1, S4])
        self.assertEqual(self._tab_orders(c)[0]["skeleton"], [S3, S2])
        types = [f["type"] for f in c["_frames"]]
        self.assertLess(types.index("tabOrder"), types.index("session"))
        # the source: the iteration reads `reconnect` beside `skeletonOnReady`; the reset re-arms under its lock, right
        # behind the pop, and the arm no longer pops or re-arms on its own (two statements outside the lock were the instant)
        so = inspect.getsource(km._send_chat_or_status)
        self.assertIn('if c.get("skeletonOnReady") or c.get("reconnect"):', so)
        rs = inspect.getsource(km._client_reset_chat_base)
        self.assertLess(rs.index("with _client_lock(client):"), rs.index('client.pop("reconnect", None)'))
        self.assertLess(rs.index('client.pop("reconnect", None)'),
                        rs.index('if client.pop("skeletonOnReady", False):\n            client["reconnect"] = True'))
        arm = inspect.getsource(km.Handler)
        body = arm[arm.index('msg.get("type") == "ready"'):][:3500]
        self.assertNotIn('client.pop("skeletonOnReady"', body)

    def test_11_c_a_later_columns_redial_is_stamped_by_its_first_strip_and_lands_a_parked_reveal(self):
        # The shim reads skeleton=1 off the address on EVERY dial of a later column, so its redial after a kernel restart
        # or a laptop sleep carries reconnect=1 AND skeleton=1. Armed with `skeletonOnReady`, that client was never stamped:
        # its page said ready on an earlier socket, no arm ever popped the flag, and _resolve_reconnect's fresh guard held
        # for the page's life — no reveal aimed at it, a parked one never consumed (review find 2026-09-11). _ws arms
        # `reconnect` alone for it (test_09's fourth dial), and the redial is served like any redial (test_12): the first
        # strip stamps the client, still carries the skeleton list, and the park lands behind it.
        km._PENDING_REVEAL.clear()
        km._live_map = lambda: {S1: {}}       # the tapped session is live, so the reveal is a focus, not a revive
        got = []
        real_reg, real_recv = km._register_ws_client, km._ws_recv
        km._register_ws_client = lambda cl: got.append(cl)
        km._ws_recv = lambda rfile: (0x8, b"", True)              # the peer closes at once
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                km.Handler._ws(_fake_self("/ws?app=chat&delta=1&iid=page-11c&wid=W1&active=%s&col=2&reconnect=1&skeleton=1" % S1))
        finally:
            km._register_ws_client, km._ws_recv = real_reg, real_recv
        self.assertEqual(len(got), 1)
        armed = {k: got[0][k] for k in ("reconnect", "skeletonOnReady") if k in got[0]}   # exactly what the real handshake armed
        self.assertEqual(armed, {"reconnect": True}, "a redial of a later column: the redial flag alone")
        try:
            trail = io.StringIO()
            with contextlib.redirect_stderr(trail):
                self.assertFalse(km._reveal_request(S1, "W1", via="sw"), "no stamped pane for the window: parked")
            c = self._client(active=S1, wid="W1", **armed)
            with contextlib.redirect_stderr(trail):
                km._push([c])
            self.assertIs(c.get("ready"), True, "the redial's first strip stamps the client, as for any redial")
            self.assertEqual(km._PENDING_REVEAL, {}, "the park was consumed")
            self.assertIsNone(c.get("reconnect"))
            self.assertNotIn("skeletonOnReady", c)
            types = [f["type"] for f in c["_frames"]]
            self.assertEqual(types.count("focus"), 1, "one focus: the parked tap")
            self.assertLess(types.index("tabOrder"), types.index("focus"), "behind the strip that names its tab")
            self.assertEqual([(f["id"], f["live"]) for f in self._frames(c, "focus")], [(S1, True)])
            self.assertEqual(self._tab_orders(c)[0]["skeleton"], [S3, S2], "still a skeleton client of the session it opened on")
            self.assertEqual(self._sessions(c), [S1, S4], "one full (+ the transcript-less): the diet, not the board, and not withheld — this page listens")
            self.assertRegex(trail.getvalue(), REDIAL_TRAIL % "sw", "the journal says the redial landed the park")
            # …and a tap that arrives now is aimed at it directly (stamped), never parked
            km._clients.append(c)
            c["_frames"].clear()
            with contextlib.redirect_stderr(trail):
                self.assertTrue(km._reveal_request(S1, "W1", via="sw"), "a stamped client for the window takes the tap")
            self.assertEqual([f["type"] for f in c["_frames"]], ["focus"])
            self.assertEqual(km._PENDING_REVEAL, {})
        finally:
            km._PENDING_REVEAL.clear()

    def test_11_b_a_relay_skeleton_dial_with_no_active_diets_all_its_tabs_through_the_cycle_and_ready(self):
        # LOW (2026-09-15, the federated dial), the full flow that pins the ready arm's reset ORDER: a RELAY fresh
        # skeleton dial (kind relay, skeletonOnReady) with NO active hint diets every transcript-bearing tab. Before
        # the ready the strip lists all of them as skeletons with a status each and NO full (the pre-ready gate holds
        # the fulls for the arm's push); at the ready _client_reset_chat_base pops the set and re-arms from
        # skeletonOnReady, the durable dietSkeleton survives, and the connect push rebuilds the SAME all-tabs set, so a
        # skeletoned tab is never sent full. A LOCAL page in the same state keeps the whole push (test_11_e).
        c = self._client(kind="relay", reconnect=True, skeletonOnReady=True, dietSkeleton=True)   # no active
        km._push([c])
        self.assertEqual(self._sessions(c), [], "no full before the ready (the arm's push serves the diet)")
        self.assertEqual(self._tab_orders(c)[0].get("skeleton"), [S3, S1, S2], "the strip lists every transcript-bearing tab as a skeleton")
        self.assertEqual(sorted(c.get("skeleton") or []), sorted([S1, S2, S3]))
        self.assertNotIn("ready", c, "a pre-ready pop stamps nothing")
        self.assertIsNone(c.get("reconnect"))
        c["_frames"].clear()
        h = _Self(lambda cl: km._push([cl], connect=True))
        with contextlib.redirect_stderr(io.StringIO()):
            km.Handler._dispatch_ws(h, {"type": "ready"}, c)
        self.assertNotIn("skeletonOnReady", c)
        self.assertEqual(sorted(c.get("skeleton") or []), sorted([S1, S2, S3]), "the all-tabs set survives the ready reset")
        for sid in (S1, S2, S3):
            self.assertNotIn(sid, self._sessions(c), "a skeletoned tab is never sent full, even at the ready")
        self.assertIs(c.get("ready"), True)

    def test_11_e_the_no_active_diet_is_scoped_to_relay_clients(self):
        # the resolve's no-active diet builds the all-tabs set ONLY for a RELAY client (the hub pane through the
        # splice); a LOCAL page (kind page) that dialed the diet with no active, and a plain reconnect, both keep the
        # fail-safe whole push; a local page's page-side recovery is not browser-proven yet (the follow-up).
        rows = km._chat_tab_sessions(0, {})
        relay = {"app": "chat", "kind": "relay", "reconnect": True, "dietSkeleton": True}
        self.assertTrue(km._resolve_reconnect(relay, rows))
        self.assertEqual(relay.get("skeletonOrder"), [S3, S1, S2], "every transcript-bearing tab a skeleton, cheapest first")
        self.assertNotIn(S4, relay.get("skeleton") or set(), "the transcript-less tab is built whole")
        local = {"app": "chat", "kind": "page", "reconnect": True, "dietSkeleton": True}
        self.assertTrue(km._resolve_reconnect(local, rows))
        self.assertIsNone(local.get("skeleton"), "a LOCAL diet page with no active is served whole (pending the follow-up)")
        plain = {"app": "chat", "kind": "relay", "reconnect": True}   # relay but did NOT diet
        self.assertTrue(km._resolve_reconnect(plain, rows))
        self.assertIsNone(plain.get("skeleton"), "a non-diet reconnect with no active is served whole")
        # FOLD 2, the cold-tab gate on an UNRESOLVED diet client (reconnect armed, no set yet): a relay diet client
        # with no active is read as holding EVERY tab as a skeleton, so the per-session route builds none it will
        # skeleton (cost only); a local diet page holds nothing (whole push).
        relay_unresolved = {"app": "chat", "kind": "relay", "reconnect": True, "dietSkeleton": True}
        self.assertTrue(km._held_as_skeleton_by_all(S1, [relay_unresolved]), "an unresolved relay diet client with no active holds every tab as a skeleton")
        local_unresolved = {"app": "chat", "kind": "page", "reconnect": True, "dietSkeleton": True}
        self.assertFalse(km._held_as_skeleton_by_all(S1, [local_unresolved]), "a local unresolved diet page holds nothing")

    # ── item 12 ──
    def test_12_a_reveal_parked_while_the_page_had_no_socket_lands_behind_the_redials_first_strip(self):
        # A push tap (or a deep link, or a vanished notification) reached the kernel while the page's socket was
        # dead: /reveal found no ready chat pane for the window and parked. The page redials with ?reconnect=1 and
        # its bundle, which posted ready once, never posts another, so no ready arm runs for the new socket. The
        # pusher's first strip for the redial is the event that stands in: it stamps the client, sends the strip,
        # then delivers the parked focus, so the focus names a tab the strip has already listed.
        km._PENDING_REVEAL.clear()
        km._live_map = lambda: {S1: {}}       # the tapped session is live, so the reveal is a focus, not a revive
        try:
            trail = io.StringIO()
            with contextlib.redirect_stderr(trail):
                self.assertFalse(km._reveal_request(S1, "W1", via="vanish"), "no socket for the window: parked")
                self.assertEqual(km._PENDING_REVEAL.get("W1"), {"sid": S1, "wid": "W1"})
                c = self._client(active=S1, reconnect=True, wid="W1")
                km._push([c])
            self.assertIs(c.get("ready"), True, "the redial's first strip stamps the client as the ready arm would")
            self.assertEqual(km._PENDING_REVEAL, {}, "the park was consumed")
            types = [f["type"] for f in c["_frames"]]
            self.assertIn("focus", types, "the parked focus landed on the redialed socket")
            self.assertLess(types.index("tabOrder"), types.index("focus"), "behind the strip that names its tab")
            self.assertLess(types.index("focus"), types.index("session"), "and ahead of the cycle's session frames")
            focus = self._frames(c, "focus")
            self.assertEqual(len(focus), 1)
            self.assertEqual((focus[0]["id"], focus[0]["live"]), (S1, True))
            self.assertEqual(self._tab_orders(c)[0]["skeleton"], [S3, S2], "the redial is still served as a skeleton set")
            self.assertRegex(trail.getvalue(), REDIAL_TRAIL % "vanish", "the journal says which event landed the park")
            # the next cycle consumes nothing: the flag is gone, and there is nothing parked
            c["_frames"].clear()
            with contextlib.redirect_stderr(io.StringIO()):
                km._push([c])
            self.assertEqual(self._frames(c, "focus"), [])
            # a fresh page (no redial) with a park for its window is left to its own ready, as before
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(km._reveal_request(S1, "W2", via="sw"))
                fresh = self._client(active=S1, wid="W2")
                km._push([fresh])
            self.assertEqual(self._frames(fresh, "focus"), [], "no redial: the strip consumes nothing")
            self.assertNotIn("ready", fresh)
            self.assertEqual(km._PENDING_REVEAL.get("W2"), {"sid": S1, "wid": "W2"}, "the park stands for the ready arm")
        finally:
            km._PENDING_REVEAL.clear()

    def _park_for_a_redialing_page(self, via):
        """A tap parked while the window had no socket, then the page's redial registered at its handshake:
        the client is in _clients with the flag and no stamp, exactly as _ws leaves it before any strip."""
        km._PENDING_REVEAL.clear()
        km._live_map = lambda: {S1: {}}       # the tapped session is live, so the reveal is a focus, not a revive
        trail = io.StringIO()
        with contextlib.redirect_stderr(trail):
            self.assertFalse(km._reveal_request(S1, "W1", via=via), "no socket for the window: parked")
        c = self._client(active=S1, reconnect=True, wid="W1")
        km._clients.append(c)
        return c, trail

    def _assert_landed_behind_the_first_strip(self, c, trail, via):
        self.assertIs(c.get("ready"), True, "stamped by the strip sender that popped the flag")
        self.assertIsNone(c.get("reconnect"))
        self.assertEqual(km._PENDING_REVEAL, {}, "the park was consumed")
        types = [f["type"] for f in c["_frames"]]
        self.assertIn("focus", types)
        self.assertLess(types.index("tabOrder"), types.index("focus"), "behind the strip that names its tab")
        self.assertEqual([(f["id"], f["live"]) for f in self._frames(c, "focus")], [(S1, True)])
        self.assertEqual(self._tab_orders(c)[0]["skeleton"], [S3, S2], "the strip is still the redial's skeleton strip")
        self.assertRegex(trail.getvalue(), REDIAL_TRAIL % via)

    def test_12b_a_close_confirmation_as_the_redials_first_strip_lands_the_park_too(self):
        # the off-cycle sender that can be the FIRST strip a redialing page sees (test_10b): it stamps and consumes
        # like the pusher's pass does, so a park does not wait for the next cycle
        c, trail = self._park_for_a_redialing_page("sw")
        try:
            with contextlib.redirect_stderr(trail):
                self.assertTrue(km._confirm_close_now(GONE))
            self._assert_landed_behind_the_first_strip(c, trail, "sw")
        finally:
            km._PENDING_REVEAL.clear()

    def test_12c_a_session_push_as_the_redials_first_strip_lands_the_park_too(self):
        # the other off-cycle sender (a create or a handshake for one tab, test_05), as the redial's first strip
        c, trail = self._park_for_a_redialing_page("link")
        try:
            with contextlib.redirect_stderr(trail):
                km._push_session_now(S3)
            self._assert_landed_behind_the_first_strip(c, trail, "link")
            self.assertEqual(self._sessions(c), [S3], "the push's own full still follows")
        finally:
            km._PENDING_REVEAL.clear()

    def test_12d_the_ready_arm_over_a_still_flagged_client_lands_the_park_once_as_the_ready(self):
        # the arm's path and the strip's cannot both land one park: _client_reset_chat_base pops the flag before the
        # connect push, so that push's strip resolves nothing, and the arm's own consume (after the push) is the one;
        # the journal names the ready, not the redial, and there is one focus (green before and after the change)
        c, trail = self._park_for_a_redialing_page("sw")
        try:
            h = _Self(lambda cl: km._push([cl], connect=True))   # the real _push_one body
            with contextlib.redirect_stderr(trail):
                km.Handler._dispatch_ws(h, {"type": "ready"}, c)
            self.assertEqual(h.calls, [c])
            self.assertIs(c.get("ready"), True)
            self.assertEqual(km._PENDING_REVEAL, {})
            for k in ("skeleton", "skeletonOrder", "reconnect"):
                self.assertNotIn(k, c, k)
            types = [f["type"] for f in c["_frames"]]
            self.assertEqual(types.count("focus"), 1, "one focus: the arm's")
            self.assertLess(types.index("tabOrder"), types.index("focus"))
            self.assertEqual(sorted(self._sessions(c)), sorted(TAB_ORDER), "the arm's push is every full, no set")
            self.assertRegex(trail.getvalue(), r"consumed \S+ the pane's ready")
            self.assertNotIn("the pane's redial", trail.getvalue(), "the strip inside the arm's push resolved no flag")
        finally:
            km._PENDING_REVEAL.clear()

    # ── pass 4b, the author's label (2026-09-20, taking the reviewer's round-3 addendum: fresh-1 / regression-4, the round-3 fixlist's extra9-1) ──
    def test_12e_a_reveal_parked_for_the_window_makes_the_parked_session_the_redials_one_full_when_the_kernel_lists_it(self):
        # The phone's first dial takes the skeleton diet with the LAST-SHOWN tab as its hint. A notification tap whose /reveal
        # beat the chat pane's socket (the ack and vanish roads land at boot; sw when the browser opens the installed app on
        # its own start URL) sits parked for the window; before this the one full went to the hint and the notified session
        # came as a skeleton, one skeleton-click round trip before it showed. _resolve_reconnect prefers the parked sid when
        # the tab list carries it: the full is the parked session's, the stored tab is a skeleton, and the consume behind the
        # strip lands the focus on a tab already whole. A parked sid the list lacks leaves the hint as before (two legs below).
        km._PENDING_REVEAL.clear()
        km._live_map = lambda: {S2: {}}       # the tapped session is live, so the reveal is a focus, not a revive
        try:
            trail = io.StringIO()
            with contextlib.redirect_stderr(trail):
                self.assertFalse(km._reveal_request(S2, "W1", via="ack"), "no socket for the window: parked")
                c = self._client(active=S1, reconnect=True, wid="W1")   # the dial's hint is the last-shown tab, web
                km._push([c])
            self.assertTrue(self._sessions(c), "the cycle sent session frames (a derived expectation over nothing is no witness)")
            self.assertTrue(self._tab_orders(c), "the cycle sent a strip")
            self.assertEqual(sorted(self._names(self._sessions(c))), ["api", "docs"], "the one full is the PARKED session's (api), plus the transcript-less docs (whole as ever; build_order ranks it first)")
            self.assertEqual(self._names(self._tab_orders(c)[0]["skeleton"]), ["tests", "web"], "the stored tab is a skeleton now, ascending size")
            self.assertEqual(c["skeleton"], {S1, S3})
            types = [f["type"] for f in c["_frames"]]
            self.assertEqual([(f["id"], f["live"]) for f in self._frames(c, "focus")], [(S2, True)], "one focus, the parked tap's")
            self.assertLess(types.index("tabOrder"), types.index("focus"), "behind the strip that names its tab")
            self.assertEqual(km._PENDING_REVEAL, {}, "the park was consumed")
            self.assertRegex(trail.getvalue(), REDIAL_TRAIL % "ack", "the journal says the redial landed the park")
            # pass 5, the author's label, taking the reviewer's round-4 finding kernel-2: the one place the kernel overrides the page's hint files a record, printed once the set is built
            # and named by the event (the set's resolve; the branch runs on the redial and on the ready arm alike), the hint's fate read off
            # the resolved set (web has a transcript: a skeleton)
            self.assertRegex(trail.getvalue(), PREFERRED_LINE % (S2[:8], S1[:8], "a skeleton"), "the preference is recorded, naming the session served whole and the hint's fate")
            self.assertEqual(len(re.findall(r"preferred at the set's resolve", trail.getvalue())), 1, "once")
            # the fallback: a parked sid this kernel does not list (an ended session) leaves the hint's set as before, and the
            # consume still lands its revive prompt
            gone_trail = io.StringIO()
            with contextlib.redirect_stderr(gone_trail):
                self.assertFalse(km._reveal_request(GONE, "W1", via="ack"))
                c2 = self._client(active=S1, reconnect=True, wid="W1")
                km._push([c2])
            self.assertTrue(self._sessions(c2))
            self.assertEqual(sorted(self._names(self._sessions(c2))), ["docs", "web"], "the hint's full, as before")
            self.assertNotIn("preferred at the set's resolve", gone_trail.getvalue(), "not applied, so no record claims it (pass 5, the reviewer's round-4 kernel-2)")
            self.assertEqual(self._names(self._tab_orders(c2)[0]["skeleton"]), ["tests", "api"])
            self.assertEqual([f["type"] for f in c2["_frames"] if f["type"] in ("focus", "confirmRevive")], ["confirmRevive"],
                             "the ended session's park lands the revive prompt")
            self.assertEqual(km._PENDING_REVEAL, {})
            # ...and a host-prefixed sid (another host's session, admitted by the reveal's shape) matches no local row: the set
            # is unchanged and the focus carries the id as-is (the page routes it)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(km._reveal_request("gpu1:" + S2, "W1", via="sw"))
                c3 = self._client(active=S1, reconnect=True, wid="W1")
                km._push([c3])
            self.assertTrue(self._sessions(c3))
            self.assertEqual(sorted(self._names(self._sessions(c3))), ["docs", "web"])
            self.assertEqual(self._names(self._tab_orders(c3)[0]["skeleton"]), ["tests", "api"])
            self.assertEqual([(f["id"], f["live"]) for f in self._frames(c3, "focus")], [("gpu1:" + S2, True)])
            # THE SPLIT (pass 5, the author's label, taking the reviewer's round-4 finding correctness-1: the regression pass 4b introduced by taking the reviewer's round-3 addendum). Two chat columns under one wid, each
            # with its own active hint, and a park for api. The kernel cannot name the column that will SHOW the tapped session
            # (the consume focuses the first chat client of the wid and the page hands a session another column holds to that
            # column), so the preference is for a window with ONE chat column, keyed on the `col` each column declares at its
            # handshake: here each column's own active stays whole and out of its own skeleton list, the parent's behaviour. At
            # the pass-4b head the column that resolved first was served api's full and its own visible tab as a skeleton.
            del km._clients[:]
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(km._reveal_request(S2, "W1", via="ack"), "parked: neither column has said ready")
                cA = self._client(active=S1, reconnect=True, wid="W1", col="")     # the first column (the page's ?col= is empty for it)
                cB = self._client(active=S3, reconnect=True, wid="W1", col="2")    # the second column, its own active hint
                km._clients.extend([cA, cB])                                        # both registered, as the handshake registers them
                km._push([cA, cB])
            self.assertTrue(self._sessions(cA) and self._sessions(cB), "both columns were sent session frames")
            self.assertNotIn("web", self._names(cA["skeleton"]), "the first column's own active hint stays out of its own skeleton list")
            self.assertNotIn("tests", self._names(cB["skeleton"]), "the second column's own active hint stays out of its own skeleton list (at the pass-4b head: a skeleton, api's full in its place)")
            self.assertEqual(sorted(self._names(self._sessions(cA))), ["docs", "web"], "the first column's one full is its own hint's")
            self.assertEqual(sorted(self._names(self._sessions(cB))), ["docs", "tests"], "the second column's one full is its own hint's")
            self.assertEqual(self._names(self._tab_orders(cB)[0]["skeleton"]), ["web", "api"], "api is a skeleton for the second column, ascending size (the page's focus handler asks for it, one round trip: the parent's road)")
            self.assertEqual(km._PENDING_REVEAL, {}, "the park was consumed by the strip behind which the page routes the focus")
            self.assertEqual([f["id"] for c_ in (cA, cB) for f in self._frames(c_, "focus")], [S2], "one focus for the window, the parked tap's (own=True; the page hands it to the owning column)")
            # THE STALE TWIN on the boot road (vote 1's executed shape): the previous page's chat socket of the SAME column is still
            # registered (sessionStorage keeps the wid across a reload and the ping timeout has up to WS_DEAD_S to reap it). A count
            # of same-wid chat clients would read it as a second column and drop the preference on the road the clause exists for;
            # keyed on the column, the twin is the same column and the parked session's full still lands.
            del km._clients[:]
            with contextlib.redirect_stderr(io.StringIO()):
                twin = self._client(active=S1, wid="W1", col="")                    # the dead page's socket: never said ready (no target), same column
                twin["alive"] = False
                c4 = self._client(active=S1, reconnect=True, wid="W1", col="")
                km._clients.extend([twin, c4])
                self.assertFalse(km._reveal_request(S2, "W1", via="ack"), "parked: the twin never said ready, the redial carries no ready")
                km._push([c4])
            self.assertTrue(self._sessions(c4))
            self.assertEqual(sorted(self._names(self._sessions(c4))), ["api", "docs"], "the stale twin of the same column does not cost the preference: the parked session's full lands (a same-wid count would have served the hint's)")
            self.assertEqual(self._names(self._tab_orders(c4)[0]["skeleton"]), ["tests", "web"])
            self.assertEqual(km._PENDING_REVEAL, {})
            self.assertEqual(self._sessions(twin), [], "the dead twin was pushed nothing")
            # THE FRESH POP (the guard's `not fresh` term): a skeleton client's pre-ready pop consumes no park (the page cannot hear
            # a focus yet; the ready arm re-resolves and consumes), so the preference waits for the pop that does. Pre-ready the set
            # is the hint's (api a skeleton, the park standing); the arm's connect push, not fresh, serves api's full and the focus.
            del km._clients[:]
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(km._reveal_request(S2, "W1", via="sw"))
                c5 = self._client(active=S1, reconnect=True, skeletonOnReady=True, wid="W1")
                km._clients.append(c5)
                km._push([c5])
            self.assertEqual(self._names(self._tab_orders(c5)[0]["skeleton"]), ["tests", "api"], "the pre-ready pop keeps the hint's set: no preference before a pop that consumes")
            self.assertEqual(self._sessions(c5), [], "no session frame before the ready")
            self.assertEqual(km._PENDING_REVEAL.get("W1"), {"sid": S2, "wid": "W1"}, "the park stands for the ready arm")
            c5["_frames"].clear()
            h = _Self(lambda cl: km._push([cl], connect=True))   # the real _push_one body
            with contextlib.redirect_stderr(io.StringIO()):
                km.Handler._dispatch_ws(h, {"type": "ready"}, c5)
            self.assertEqual(sorted(self._names(self._sessions(c5))), ["api", "docs"], "the ready arm's connect push, not fresh: the parked session's full")
            self.assertEqual(self._names(self._tab_orders(c5)[0]["skeleton"]), ["tests", "web"], "the stored tab a skeleton")
            self.assertEqual([f["id"] for f in self._frames(c5, "focus")], [S2], "the arm consumed the park")
            self.assertEqual(km._PENDING_REVEAL, {})
            # THE DECLARATION (the author's pass-5 verify, correctness-1's residual). The sockets read above is ONE column's at the first column's
            # resolve when a split page's columns redial one after another (the second's handshake has not registered its col yet), so
            # at the pass-5 head the first column was served the parked session's full and its own shown tab as a skeleton in that
            # window. The shell now declares its chat column count with the tap (_LANDING_REVEAL_JS cols, the /reveal body) and the park
            # carries it: a park declaring two columns declines the preference for the first column to resolve, alone in _clients, and
            # its own hint stays whole; the park is consumed all the same (the page routes the focus to the owning column).
            del km._clients[:]
            trail2 = io.StringIO()
            with contextlib.redirect_stderr(trail2):
                self.assertFalse(km._reveal_request(S2, "W1", via="ack", cols=2), "parked, with the declaration")
                self.assertEqual(km._PENDING_REVEAL.get("W1"), {"sid": S2, "wid": "W1", "cols": 2}, "the park carries the shell's column count")
                cA2 = self._client(active=S1, reconnect=True, wid="W1", col="")
                km._clients.append(cA2)                                            # the first column's handshake registered it; the second's has not yet
                km._push([cA2])
            self.assertTrue(self._sessions(cA2))
            self.assertEqual(sorted(self._names(self._sessions(cA2))), ["docs", "web"], "the first column to redial, alone in _clients: the declared two columns decline the preference, so its one full is its own hint's (at the pass-5 head: api's full, web a skeleton)")
            self.assertEqual(self._names(self._tab_orders(cA2)[0]["skeleton"]), ["tests", "api"])
            self.assertEqual([f["id"] for f in self._frames(cA2, "focus")], [S2], "the park is consumed behind the strip all the same (the page hands the focus to the owning column)")
            self.assertEqual(km._PENDING_REVEAL, {})
            self.assertRegex(trail2.getvalue(), r"\[reveal\] ack sid=\S+ wid=W1: parked cols=2", "the park's journal line records the declaration")
            with contextlib.redirect_stderr(io.StringIO()):
                cB2 = self._client(active=S3, reconnect=True, wid="W1", col="2")   # the second column's redial lands after the first resolved
                km._clients.append(cB2)
                km._push([cB2])
            self.assertEqual(sorted(self._names(self._sessions(cB2))), ["docs", "tests"], "the second column: its own hint's full")
            # ...a declared ONE-column window takes the preference (the phone's shape, and a desktop with one column)...
            del km._clients[:]
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(km._reveal_request(S2, "W1", via="ack", cols=1))
                c6 = self._client(active=S1, reconnect=True, wid="W1", col="")
                km._clients.append(c6)
                km._push([c6])
            self.assertEqual(sorted(self._names(self._sessions(c6))), ["api", "docs"], "one declared column: the parked session's full")
            self.assertEqual(self._names(self._tab_orders(c6)[0]["skeleton"]), ["tests", "web"])
            # ...unless a second column's socket is registered already (a column split off after the tap): the sockets read is the belt
            del km._clients[:]
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(km._reveal_request(S2, "W1", via="ack", cols=1))
                c7 = self._client(active=S1, reconnect=True, wid="W1", col="")
                c8 = self._client(active=S3, reconnect=True, wid="W1", col="2")
                km._clients.extend([c7, c8])
                km._push([c7])
            self.assertEqual(sorted(self._names(self._sessions(c7))), ["docs", "web"], "one declared but a second column registered (split off after the tap): the sockets read declines the preference")
            # THE UNDECLARED PARK (a focus _send_focus_to_view parked; a shell of a build before the field): the sockets read alone, so on
            # a split page the first column to redial, alone in _clients, takes the preference. The residual the PR body discloses,
            # pinned so the disclosure and the code say the same thing.
            del km._clients[:]
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(km._reveal_request(S2, "W1", via="ack"))
                self.assertEqual(km._PENDING_REVEAL.get("W1"), {"sid": S2, "wid": "W1"}, "no declaration: the two-key entry as before")
                c9 = self._client(active=S1, reconnect=True, wid="W1", col="")
                km._clients.append(c9)
                km._push([c9])
            self.assertEqual(sorted(self._names(self._sessions(c9))), ["api", "docs"], "no declaration and one socket registered: the preference applies (the disclosed residual: a split page's staggered redial over a park with no declaration)")
        finally:
            km._PENDING_REVEAL.clear()

    def test_12f_the_preference_records_the_served_session_where_the_push_reads_the_watched_tab(self):
        # pass 7 (the author's label, 2026-09-20, taking the reviewer's round-5 finding kernel-1). The preference reassigned only the
        # local `act`: _push's active set, build_order, _all_active and the cold-tab gate still named the page's stale hint, so on
        # the boot road the hint was ranked first and handed a cold full build the gate would otherwise have skipped (every connected
        # page holds it as a skeleton and its live row can state a status), and the notified session's full was built after it. The
        # served session is recorded on the client (`preferred`, under the slot lock the resolve holds) and _watched_tab reads it in
        # the hint's place for those four readers; `active` stays the page's own declaration (the client-diag skeleton row,
        # _watched_sids and the live-wake exemption read it), and the page's next activeTab, its own word, drops the record.
        km._PENDING_REVEAL.clear()
        row = {"state": "working", "since": 1781100000, "model": "", "effort": "", "mode": "", "backend": "sdk"}
        km._live_map = lambda: {S2: dict(row), S1: dict(row)}   # the tapped session live (a focus, not a revive); the hint's row states its status
        skip0 = km._VIEW_STATS.get("chatSkipCold", 0)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(km._reveal_request(S2, "W1", via="ack", cols=1), "no socket for the window: parked, one column declared")
                c = self._client(active=S1, reconnect=True, wid="W1", col="")   # the dial's hint is the last-shown tab, web
                km._clients.append(c)                                          # the gate asks every CONNECTED chat client
                km._push([c])
            self.assertEqual(sorted(self._names(self._sessions(c))), ["api", "docs"], "the one full is the parked session's (test_12e's leg)")
            self.assertEqual(self._names(self.built), ["api", "docs", "tests"],
                             "the served session is built FIRST (it is the watched tab now), the transcript-less docs with it, then the skeleton "
                             "tests (no live row: the gate builds it as before); the hint web is not built at all: %r" % (self._names(self.built),))
            self.assertNotIn(S1, self.built, "the hint, a skeleton on every connected page with a live row to state its status, gets no cold build")
            self.assertEqual(km._VIEW_STATS["chatSkipCold"] - skip0, 1, "the gate skipped the hint's cold build, once")
            self.assertIn(S1, {f["id"] for f in self._frames(c, "status")}, "the skipped tab's status still goes, from its live row")
            self.assertEqual(c["active"], S1, "the page's own declaration is never overwritten")
            self.assertEqual(c.get("preferred"), S2, "the served session is recorded on the client")
            self.assertEqual(km._watched_tab(c), S2, "the readers' view: the served session in the hint's place")
            self.assertEqual(km._PENDING_REVEAL, {}, "the park was consumed")
            # the page's own tab switch supersedes the record: from here `active` is the page's word again
            c["_frames"].clear()
            with contextlib.redirect_stderr(io.StringIO()):
                km.Handler._dispatch_ws(_Self(), {"type": "activeTab", "id": S1}, c)
            self.assertNotIn("preferred", c, "the page's activeTab drops the record")
            self.assertEqual((c["active"], km._watched_tab(c)), (S1, S1))
            # a redial whose park the preference declines (two columns declared) records nothing
            del km._clients[:]
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(km._reveal_request(S2, "W1", via="ack", cols=2))
                c2 = self._client(active=S1, reconnect=True, wid="W1", col="")
                km._clients.append(c2)
                km._push([c2])
            self.assertEqual(sorted(self._names(self._sessions(c2))), ["docs", "web"], "declined: the hint's full")
            self.assertNotIn("preferred", c2, "no preference applied, no record")
            self.assertEqual(km._watched_tab(c2), S1)
        finally:
            km._PENDING_REVEAL.clear()

    def test_12g_a_second_ready_re_bases_the_record_with_the_set_it_belongs_to(self):
        # pass 8 (the author's label, 2026-09-21, taking the reviewer's round-6 finding kernel-2). `preferred` joined the family of
        # per-renderer beliefs (echat, skeleton, skeletonOrder, reconnect) and had not joined the reset that clears them: on the
        # second-ready re-base road (Handler._dispatch_ws runs _client_reset_chat_base on EVERY ready, readySeen or not) the stale
        # record outlived its set, and _watched_tab demoted the page's own declared tab out of _push's active-first batch. By reading,
        # no client of this tree posts a second ready on one socket (render.ts once at evaluation, the shim's re-post on a new socket
        # alone, federation.ts once per remote socket, the extension's pipe once per up): the arm's own re-base branch is the road, and
        # this drives it. Red before: the record stood through the reset and the build order was ['docs', 'web', 'tests'].
        km._PENDING_REVEAL.clear()
        row = {"state": "working", "since": 1781100000, "model": "", "effort": "", "mode": "", "backend": "sdk"}
        km._live_map = lambda: {S2: dict(row), S1: dict(row)}
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(km._reveal_request(S2, "W1", via="ack", cols=1), "parked, one column declared")
                c = self._client(active=S1, reconnect=True, wid="W1", col="")
                km._clients.append(c)
                km._push([c])
            self.assertEqual(c.get("preferred"), S2, "test_12f's state: the record stands after the resolve")
            del self.built[:]
            c["_frames"].clear()
            with contextlib.redirect_stderr(io.StringIO()):
                km.Handler._dispatch_ws(_Self(lambda cl: km._push([cl], connect=True)), {"type": "ready", "proto": 2}, c)   # the re-base: the reset, then the connect push
            self.assertEqual(self._names(self.built), ["web", "docs", "api", "tests"],
                             "the re-based renderer's active-first batch is the page's declared tab (web), the transcript-less docs with it, "
                             "then the rest in strip order; before the reset dropped the record, api (the stale record) was built first and "
                             "web third: %r" % (self._names(self.built),))
            self.assertNotIn("preferred", c, "the reset forgets the record with the set it belongs to")
            self.assertEqual(km._watched_tab(c), S1, "the readers see the page's own declared tab again")
            self.assertEqual(c["active"], S1, "the page's declaration was never overwritten")
            # the family rule both ways: a DECLARED redial keeps its beliefs through a ready, the record among them (the reset's guard)
            r = self._client(active=S1, redial=True, reconnect=True, skeleton={S3}, skeletonOrder=[S3], preferred=S2, echat={})
            km._client_reset_chat_base(r)
            self.assertEqual((r.get("preferred"), r.get("skeleton"), r.get("reconnect")), (S2, {S3}, True),
                             "a declared redial keeps its state for _resolve_reconnect to fill, the record with it")
        finally:
            km._PENDING_REVEAL.clear()

    def test_12h_the_resolve_pop_of_the_record_is_defensive_no_road_reaches_it_with_a_record(self):
        # pass 8 (the author's label, 2026-09-21, taking the reviewer's round-6 findings tests-2 and extra9-3). The `c.pop("preferred", None)`
        # in _resolve_reconnect's `act and not fresh` branch finds nothing on any road at this head, because a socket enters that branch
        # at most once: `skeletonOnReady` alone re-arms `reconnect` on a live client (the reset, once, at the bundle's one ready), and
        # the two other writers arm it at the handshake. Driven, each with a park the preference takes so a record is WRITTEN after the
        # pop, then a second strip sender (_push_session_now) and a second push, neither of which may re-enter: road A (a redial), road B
        # (a skeleton column: the pre-ready pop skips the branch under `fresh`, the ready-time re-arm enters once), road C (a redial of a
        # skeleton column). The spy counts the branch's pops of `preferred` by caller and what each found. Red under a kernel whose
        # resolve reads the flag without consuming it (every sender re-enters: two pops, the second finding the record).
        class _PopSpy(dict):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                self.pops = []

            def pop(self, key, *default):
                if key == "preferred":
                    self.pops.append((sys._getframe(1).f_code.co_name, dict.get(self, key)))
                return dict.pop(self, key, *default)

        row = {"state": "working", "since": 1781100000, "model": "", "effort": "", "mode": "", "backend": "sdk"}
        km._live_map = lambda: {S2: dict(row), S1: dict(row)}
        roads = [("A, a redial", dict(active=S1, reconnect=True, redial=True, wid="W1", col="")),
                 ("B, a skeleton column", dict(active=S1, reconnect=True, skeletonOnReady=True, dietSkeleton=True, wid="W1", col="")),
                 ("C, a redial of a skeleton column", dict(active=S1, reconnect=True, redial=True, dietSkeleton=True, wid="W1", col=""))]
        for name, kw in roads:
            with self.subTest(road=name):
                del km._clients[:]
                km._PENDING_REVEAL.clear()
                km._built_chat.clear()
                del self.built[:]
                try:
                    with contextlib.redirect_stderr(io.StringIO()):
                        self.assertFalse(km._reveal_request(S2, "W1", via="ack", cols=1), "parked, one column declared")
                        c = _PopSpy(self._client(**kw))
                        km._clients.append(c)
                        km._push([c])                                    # the first strip sender (road B: the pre-ready pop, under fresh)
                        if kw.get("skeletonOnReady"):
                            km.Handler._dispatch_ws(_Self(lambda cl: km._push([cl], connect=True)), {"type": "ready", "proto": 2}, c)   # the one ready: the reset re-arms, the connect push resolves
                        km._push_session_now(S3)                         # a second strip sender: the flag is consumed, the branch is not re-entered
                        km._push([c])                                    # and the pusher's next cycle
                    resolve_pops = [(f, v) for f, v in c.pops if f == "_resolve_reconnect"]
                    self.assertEqual(len(resolve_pops), 1, "the branch is entered once per socket on this road: %r" % (c.pops,))
                    self.assertIsNone(resolve_pops[0][1], "the pop finds no record on this road: it is defensive: %r" % (c.pops,))
                    self.assertEqual(c.get("preferred"), S2, "the record is written after the pop, once, and stands until a release")
                finally:
                    km._PENDING_REVEAL.clear()



class RestartDiet(unittest.TestCase):
    """The user's ruling (2026-09-14): after a reload the selected tab builds first, the strip's other tabs spread over later refreshes,
    hidden tabs not until shown; and restarts are invisible, so the one reload the reload core fires is the one the user accepts when a
    newer build is offered (2026-09-16), a fresh page on a kernel that has the build. The client half: the main chat pane's FIRST dial after any reload the core fired is a skeleton
    dial (the later column's shape), so the kernel's existing handshake serves the strip with the skeleton set, one full for the active
    tab and a status per other tab; a redial carries the diet through reconnect=1 as before. Pinned in the served shim's source: the
    reload core keeps the reason and the document's path in a durable record (announce() removes the announce record before a pane
    dials, and a pane inside the shell never announces); the chat shim alone reads it, removes it BEFORE parsing (a malformed record is
    consumed too), and dials skeleton=1 on its first socket when the record names the shell or a chat document; a column and a skeleton
    view leave the record alone; every other pane's shim carries the false alone; the kernel arms the term for a chat socket only."""

    def test_the_first_dial_after_a_restart_reload_is_a_skeleton_dial(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        fire = src[src.index("function fire(){"):src.index("var heldFor=null;")]
        self.assertIn("sessionStorage.setItem('romp:reloadReason',JSON.stringify({reason:owed.reason,path:location.pathname,t:Date.now()}))", fire,
                      "the reload core keeps the reason and the document's path durably when it fires (the announce record is consumed before the panes dial)")
        chat, feed = km._shim("chat"), km._shim("feed")
        self.assertIn("""var RESTART_DIET=false;if(!COL&&!SKEL){var rr=null;try{var raw=sessionStorage.getItem('romp:reloadReason');sessionStorage.removeItem('romp:reloadReason');rr=raw?JSON.parse(raw):null;}catch(e){}RESTART_DIET=!!(rr&&typeof rr==='object'&&typeof rr.reason==='string'&&(rr.path===undefined||rr.path==='/'||String(rr.path).indexOf('/chat')===0));}""", chat,
                      "the chat shim removes the record BEFORE parsing it and dials the diet on any reload the core fired for the shell or a chat document, only for an object with the fields (a scalar is consumed and diets nothing): a main pane, not a column, not a skeleton view")
        self.assertIn("sessionStorage.setItem('romp:reloadReason',JSON.stringify({reason:owed.reason,path:location.pathname,t:Date.now()}))", src,
                      "the reload core's record names the document that reloaded, so a standalone feed page's reload steers no chat dial")
        read = "sessionStorage.getItem('romp:reloadReason')"   # the READ; the reload core's write of the record rides every page's shim
        self.assertNotIn(read, feed, "a non-chat pane's shim never reads the record (round two, medium 2)")
        self.assertIn("var RESTART_DIET=false;", feed, "…it carries the false alone, so the shared dial line still compiles")
        for other in ("fleet", "files", "timeline", "settings"):
            self.assertNotIn(read, km._shim(other), other)
        self.assertIn('skeleton = (q.get("skeleton") or [""])[0] == "1" and app == "chat"', src, "the kernel arms the skeleton diet for a chat socket alone (round two, medium 2)")
        self.assertIn("""((SKEL||(RESTART_DIET&&!everConnected))?"&skeleton=1":"")""", src,
                      "the dial carries skeleton=1 for a column, or for the main pane's FIRST socket after a restart reload (a redial dials as before)")
        # the kernel side the dial lands on is unchanged and already pinned above: skeleton=1 without reconnect arms skeletonOnReady at the
        # handshake, and the ready arm serves the strip with the skeleton set, one full for the active tab, a status per other tab
        self.assertIn('client["skeletonOnReady"] = True', src)

if __name__ == "__main__":
    unittest.main()
