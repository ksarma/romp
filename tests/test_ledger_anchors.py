"""The ledger TOC and the feed cards must deep-link a goal node to the SAME chat turn BY UUID, not by the
old nearest-time heuristic (the user 2026-06-19). Both build_session (the ledger) and build_feed (the cards)
resolve a node's (promptAnchorUuid, anchorUuid) through the ONE shared helper km._node_anchor_uuids, so they
cannot drift apart. This pins the helper's resolution and the shared-call anti-drift property."""
import json
import os
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path
from romp_load import load_source
import tempfile

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
jd = km.jd                              # the kernel's judge: the one object build_feed reads stores through


class NodeAnchorResolution(unittest.TestCase):
    # seg id -> the .turn[data-uuid] anchors (prompt = the segment's trigger / user message; work = its reply)
    SEG_TRIG = {"s1": "u-aaa", "s2": "u-bbb", "s3": "u-ccc"}
    SEG_WORK = {"s1": "a-aaa", "s2": "a-bbb", "s3": "a-ccc"}

    def test_every_node_work_anchors_to_its_NEWEST_trail_segment(self):
        # the work anchor is trail[-1] for EVERY node (2026-07-20): the resolve turn for done/blocked
        # nodes, the latest activity for open ones — "where it stands", never "where it was born". (Open
        # nodes anchored their MINT before; a long-lived open sub's click then said nothing useful.)
        nd = {"trail": ["s1", "s2", "s3"]}
        prompt, work = km._node_anchor_uuids(nd, self.SEG_TRIG, self.SEG_WORK)
        self.assertEqual(prompt, "u-aaa")        # trail[0] trigger (the minting message) — unchanged
        self.assertEqual(work, "a-ccc")          # trail[-1] work (the newest event)

    def test_single_segment_trail(self):
        nd = {"trail": ["s2"]}
        self.assertEqual(km._node_anchor_uuids(nd, self.SEG_TRIG, self.SEG_WORK), ("u-bbb", "a-bbb"))

    def test_empty_trail_yields_no_anchors(self):
        # no filed segments → no uuid to land on → (None, None); the render then falls back to nearest-time.
        self.assertEqual(km._node_anchor_uuids({"trail": []}, self.SEG_TRIG, self.SEG_WORK), (None, None))
        self.assertEqual(km._node_anchor_uuids({}, self.SEG_TRIG, self.SEG_WORK), (None, None))

    def test_segment_missing_from_the_map_degrades_to_None(self):
        # a trail segment the chat parse didn't surface (rewound / orphaned) → None for that anchor, not a throw.
        nd = {"trail": ["sX", "sY"]}
        self.assertEqual(km._node_anchor_uuids(nd, self.SEG_TRIG, self.SEG_WORK), (None, None))

    def test_a_junk_mint_quote_ships_no_prompt_anchor(self):
        # the read-side junk guard (jd.junk_quote): a node minted off a bare "retry" must not deep-link
        # its title to that stub (the user 2026-07-20, romp_docs g242) — existing stores heal, no migration.
        nd = {"trail": ["s1", "s2"], "promptUuid": "u-stored", "quote": "retry"}
        prompt, work = km._node_anchor_uuids(nd, self.SEG_TRIG, self.SEG_WORK)
        self.assertIsNone(prompt)
        self.assertEqual(work, "a-bbb")


class ColdBeatWorkAnchorFallback(unittest.TestCase):
    """The feed reads the parse CACHE-ONLY, and every transcript write invalidates it — so an actively
    working session's pushes arrive with EMPTY seg maps most beats, and every node's work anchor went out
    null: the modal's ⏸ mark dispatched anchorUuid null and the click could only toast "couldn't locate"
    (the user 2026-07-20, three dead clicks on the romp_docs blocked sub in one cold beat). A warm resolve
    is REMEMBERED per node id and served through the cold beats; a node never seen warm this kernel run
    falls to its stored summaryAnchor (the distiller's validated citation); only a node with neither still
    honest-fails."""

    SEG_TRIG = {"s1": "u-aaa"}
    SEG_WORK = {"s1": "a-aaa"}
    COLD = {}                     # what build_feed's maps look like on a cold beat

    def setUp(self):
        km._node_anchor_last.clear()

    def tearDown(self):
        km._node_anchor_last.clear()

    def test_a_warm_resolve_is_remembered_and_served_through_a_cold_beat(self):
        nd = {"id": "S:g1", "trail": ["s1"], "promptUuid": "u-stored"}
        warm = km._node_anchor_uuids(nd, self.SEG_TRIG, self.SEG_WORK)
        self.assertEqual(warm, ("u-stored", "a-aaa"))
        cold = km._node_anchor_uuids(nd, self.COLD, self.COLD)
        self.assertEqual(cold, warm, "the cold beat serves the remembered warm anchors, not null")

    def test_never_seen_warm_falls_to_the_stored_distiller_citation(self):
        nd = {"id": "S:g2", "trail": ["sX"], "promptUuid": "u-stored", "summaryAnchor": "a-cited"}
        self.assertEqual(km._node_anchor_uuids(nd, self.COLD, self.COLD), ("u-stored", "a-cited"))

    def test_a_node_with_neither_still_honest_fails(self):
        # no warm memory, no stored citation → None work anchor: the render's honest-fail toast is correct
        nd = {"id": "S:g3", "trail": ["sX"]}
        self.assertEqual(km._node_anchor_uuids(nd, self.COLD, self.COLD), (None, None))

    def test_the_memory_is_per_node_never_a_neighbors(self):
        km._node_anchor_uuids({"id": "S:g4", "trail": ["s1"]}, self.SEG_TRIG, self.SEG_WORK)
        nd = {"id": "S:g5", "trail": ["sX"]}
        self.assertEqual(km._node_anchor_uuids(nd, self.COLD, self.COLD), (None, None),
                         "g4's warm anchors never bleed onto g5")

    def test_a_warm_miss_prefers_the_memory_over_the_stored_citation(self):
        # warm maps that MISS this node's seg (drift / rewound off-path) behave like a cold beat: the last
        # good anchor (exact) outranks the stored citation (older)
        nd = {"id": "S:g6", "trail": ["s1"], "summaryAnchor": "a-cited"}
        km._node_anchor_uuids(nd, self.SEG_TRIG, self.SEG_WORK)
        got = km._node_anchor_uuids({**nd, "trail": ["sX"]}, self.SEG_TRIG, self.SEG_WORK)
        self.assertEqual(got[1], "a-aaa", "the remembered warm anchor wins over the stored citation")


class SharedHelperAntiDrift(unittest.TestCase):
    """The whole point of the helper: the feed and the ledger can't drift. Guard that BOTH build_feed and
    build_session resolve node anchors through km._node_anchor_uuids (not a private re-implementation). Since the
    Outline's provisional row (plans/outline-pane-provisional-row.md, 2026-09-15) the ledger's walk lives in the shared
    _goal_tree_walk, which build_session AND the provisional assembly call: the anchors are resolved there, through the
    one helper, so the pin follows the walk and holds both callers to it."""

    def test_both_builders_call_the_one_helper(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        # the helper is defined once
        self.assertEqual(len(re.findall(r"def _node_anchor_uuids\(", src)), 1, "helper defined exactly once")
        # both view-builders bodies reference it
        def body(fn):
            m = re.search(r"\ndef %s\(.*?(?=\ndef )" % fn, src, re.S)
            self.assertIsNotNone(m, "found %s" % fn)
            return m.group(0)
        self.assertIn("_node_anchor_uuids(", body("_goal_tree_walk"), "the ledger's shared walk resolves anchors via the helper")
        self.assertNotIn("_node_anchor_uuids(", body("build_session"), "build_session holds no private anchor resolution beside the walk")
        self.assertIn("_goal_tree_walk(sid, gstore, seg_trig, seg_work, anchors=True)", body("build_session"), "the ledger takes the shared walk, anchors on")
        self.assertIn("_goal_tree_walk(sid, gstore, anchors=False)", body("_provisional_ledger"), "the Outline's provisional row takes the same walk, anchors off (a cold tab has no landing)")
        self.assertEqual(len(re.findall(r"def _goal_tree_walk\(", src)), 1, "the walk defined exactly once")
        self.assertIn("_node_anchor_uuids(", body("_feed_session_entry"),   # T368: build_feed's per-session loop body
                      "the feed resolves anchors via the helper")


class GlowByIdRouting(unittest.TestCase):
    """The timeline->chat glow lights a hovered bar's segments BY ID (their atom uuids), not a +/-2s time
    window — the time heuristic the user banned (2026-06-19/20). Pin the kernel side. (The functional
    _segment_atom_uuids test lives with the session fixture in test_kernel.py's owner's suite; here we pin
    the helper's presence + the handler wiring without that fixture.)"""

    def test_segment_atom_uuids_helper_exists(self):
        self.assertTrue(hasattr(km, "_segment_atom_uuids"), "the seg->atom-uuid resolver exists")

    def test_timeline_hover_glows_by_uuid_not_time_range(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn("_segment_atom_uuids(hsid, seg_ids", src)         # the handler resolves segs -> atom uuids
        self.assertIn('"glowTurns", "groups": groups, "mids": []', src)
        self.assertIn('"uuids": uuids', src)                            # sent as uuids...
        self.assertNotIn('"ranges": [[t0, t1]]', src)                  # ...not the old +/-2s time window


class SegmentOfUuid(unittest.TestCase):
    """The inverse resolver behind the chat-dot hover: one hovered atom uuid -> (its segment id, ALL of that
    segment's atom uuids). Pins #2 (which feed card owns it) + #3 (which sibling rows light) to EXACT segment
    membership, never a time window. _sessions/_parse/em.segments are stubbed so no on-disk fixture is needed."""

    SEGS = [
        {"id": "s1", "atoms": [{"uuid": "u1"}, {"uuid": "a1"}]},
        {"id": "s2", "atoms": [{"uuid": "u2"}, {"uuid": "a2"}, {"uuid": "a3"}]},
    ]

    def setUp(self):
        self._orig = (km._sessions, km._parse, km.em.segments)
        km._sessions = lambda now: [{"sid": "S", "path": "P"}]
        km._parse = lambda path, sid, now: {"turns": [{"segs": self.SEGS}]}
        km.em.segments = lambda turn: turn["segs"]

    def tearDown(self):
        km._sessions, km._parse, km.em.segments = self._orig

    def test_any_atom_resolves_to_its_segment_and_ALL_its_uuids(self):
        # hovering the middle atom of s2 lights the whole segment (all 3 rows) and names s2 as the card owner
        self.assertEqual(km._segment_of_uuid("S", "a2", 0), ("s2", ["u2", "a2", "a3"]))

    def test_the_trigger_atom_resolves_the_same_as_any_other(self):
        self.assertEqual(km._segment_of_uuid("S", "u1", 0), ("s1", ["u1", "a1"]))

    def test_unknown_uuid_is_None_not_a_throw(self):
        self.assertEqual(km._segment_of_uuid("S", "nope", 0), (None, []))

    def test_empty_uuid_short_circuits(self):
        # the chat 'leave' event carries no uuid -> resolve to nothing -> the handler then clears both surfaces
        self.assertEqual(km._segment_of_uuid("S", "", 0), (None, []))

    def test_unknown_session_is_None(self):
        self.assertEqual(km._segment_of_uuid("MISSING", "a2", 0), (None, []))


class ChatAndFeedHoverRouting(unittest.TestCase):
    """The hover graph is now bidirectional and BY ID: a feed-card hover glows its chat rows (#1 feed->chat),
    and a chat-dot hover lights the owning feed card (#2) + every sibling row in its segment (#3). Pin the
    kernel wiring (the functional resolvers are pinned above + in the owner's fixture suite)."""

    SRC = open(os.path.join(BIN, "romp-kernel")).read()

    def test_inverse_resolver_exists(self):
        self.assertTrue(hasattr(km, "_segment_of_uuid"), "the uuid->segment resolver exists")

    def test_feed_card_hover_glows_chat_by_uuid(self):
        # #1: showAskPath resolves the goal's segments -> their atom uuids -> a chat glow (distinct var gsid)
        self.assertIn("_segment_atom_uuids(gsid, seg_ids", self.SRC)
        self.assertIn('_send_to_app("chat", {"type": "glowTurns"', self.SRC)

    def test_chat_dot_hover_lights_owning_feed_card(self):
        # #2: the dotHover branch maps the hovered atom's segment -> its top feed card(s)
        self.assertIn("_segment_of_uuid(hsid, huuid", self.SRC)
        self.assertIn("_cards_for_segments(hsid, [seg_id])", self.SRC)
        self.assertIn('_send_to_app("feed", {"type": "hoverCards"', self.SRC)

    def test_chat_dot_hover_glows_its_whole_segment(self):
        # #3: the same branch glows EVERY atom uuid in the hovered segment (the sibling dots), by id; the group is
        # built by _glow_groups, which adds each uuid's global index for the ruler's history strip (T318b)
        self.assertIn("_glow_groups(hsid, seg_uuids)", self.SRC)

    def test_ledger_bullet_hover_stays_timeline_only(self):
        # the feed/chat extension is gated to dotHover; a ledgerHover (TOC bullet) must not stomp the glow
        self.assertIn('if msg.get("type") == "dotHover":', self.SRC)


def _atom(uuid, blocks, typ="assistant", err=False):
    a = {"type": typ, "uuid": uuid, "message": {"content": blocks}}
    if err:
        a["isApiError"] = True
    return a


THINK = [{"type": "thinking", "thinking": "", "signature": "x"}]
TOOL = [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]
TEXT = [{"type": "text", "text": "Here are several recordings that would demonstrate it."}]


class SegJump(unittest.TestCase):
    """_seg_jump — the LANDABLE chat jump target (the user 2026-07-21): a card summary click on the
    romp_docs recording-suggestions card toasted "couldn't locate this in the transcript" because the
    newest segment's only assistant output at build time was a thinking block, and the `r or w` fallback
    handed the summary zone that thinking-only uuid — an atom the chat renders no .turn[data-uuid] for."""

    def test_thinking_only_segment_yields_none_never_the_thinking_uuid(self):
        self.assertIsNone(km._seg_jump([_atom("a-think", THINK)]),
                          "no landable atom yet: None → the client's ev_t time-nav, not an honest-fail toast")

    def test_readable_reply_wins(self):
        atoms = [_atom("a-think", THINK), _atom("a-tool", TOOL), _atom("a-text", TEXT)]
        self.assertEqual(km._seg_jump(atoms), "a-text")

    def test_tool_row_is_landable_when_there_is_no_prose_yet(self):
        atoms = [_atom("a-think", THINK), _atom("a-tool", TOOL)]
        self.assertEqual(km._seg_jump(atoms), "a-tool",
                         "a tool row renders a .turn[data-uuid] (collapsed groups expand on anchor)")

    def test_api_error_atoms_never_anchor(self):
        atoms = [_atom("a-err", TEXT, err=True)]
        self.assertIsNone(km._seg_jump(atoms))

    def test_the_deep_link_maps_use_the_landable_anchor(self):
        # both zone maps (ledger seg_work + feed seg_uuid) resolve through _seg_jump, not bare `r or w`
        import inspect
        src = inspect.getsource(km.build_session) + inspect.getsource(km._feed_session_entry)   # T368: the feed's loop body
        self.assertEqual(src.count('_seg_jump(seg["atoms"])'), 2)
        self.assertNotIn("= r or w", src)


class FeedWarmResolveBumpsTheLedgerRevision(unittest.TestCase):
    """The feed's WARM resolve of a node's anchors bumps _node_anchor_rev for the session it builds, through the
    `sid=fsid` argument on _feed_session_entry's _node_anchor_uuids call (2026-09-09). The 2026-09-15 upstream pull-in's
    merge dropped that argument once, the fixer round restored it, and no executed case failed without it (review round
    1, tests-1): the argument is the whole of what these cases pin. Three memo keys read the revision, each taken BEFORE
    its walk: build_session's ledger memo (`_lkey`'s third component), the chat build's signature
    (`sig.append(_node_anchor_rev.get(sid, 0))`) and the feed entry's own `anchors` component (_feed_session_key). A
    warm resolve that CHANGES the table's entry must move all three, or a memoized tree whose cold nodes read the older
    entry is served as current. Driven through the REAL build_feed over a hermetic two-session board (the notes-api demo
    world): `web`, whose parse is warm the way a chat build or _warm_fleet_bg leaves it, so the feed's cache-only read
    resolves its node's segment; `api`, whose parse is cold and whose node names a segment no parse holds, so every
    resolve of it is cold and writes nothing. Private synthetic sids (the goal-store fixture rule: load_goals replays the
    per-sid override journal, so a shared placeholder sid can be re-flagged by another module's rows); the state root,
    the memo, the anchor tables and the parse cache are restored in tearDown."""

    SIDS = ("7a6b5c4d-3e2f-4a1b-9c8d-7e6f5a4b3c01", "7a6b5c4d-3e2f-4a1b-9c8d-7e6f5a4b3c02")
    WEB, API = SIDS
    NAME_OF = {WEB: "web", API: "api"}
    COLOR_OF = {WEB: "#1EA1EB", API: "#E67E22"}
    GOAL_OF = {WEB: "wire the notes-api web client", API: "add the notes-api list endpoint"}
    NOW = 1781100000
    T0 = NOW - 3600

    @staticmethod
    def _iso(t):
        return datetime.fromtimestamp(t, timezone.utc).isoformat().replace("+00:00", "Z")

    def _transcript(self, sid):
        """One user message and its reply: the segment web's trail names (uuids u1 and a1)."""
        u = {"type": "user", "timestamp": self._iso(self.T0), "uuid": "u1", "parentUuid": None, "promptSource": "typed",
             "message": {"role": "user", "content": "start on: " + self.GOAL_OF[sid]}}
        a = {"type": "assistant", "timestamp": self._iso(self.T0 + 40), "uuid": "a1", "parentUuid": "u1",
             "message": {"role": "assistant", "content": [{"type": "text", "text": "On it."}], "stop_reason": "end_turn"}}
        return json.dumps(u) + "\n" + json.dumps(a) + "\n"

    def _mint(self, sid, seg_id, prompt_uuid):
        """One top-level goal minted the way the planner mints (apply_plan), rolled up and saved."""
        s = {"rompUuid": sid, "seq": 0, "placementsV": jd.PLACEMENTS_V, "nodes": {}, "placements": {}, "status": {}}
        jd.apply_plan(s, seg_id, self.T0, [{"do": "mint", "why": "the request that opened the session",
                                            "text": self.GOAL_OF[sid]}], [], prompt_uuid=prompt_uuid)
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(sid, s)

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        proj, names = td / "projects", td / "names"
        names.mkdir()
        self.tpath = {}
        for sid in self.SIDS:
            cdir = td / ("launch-" + self.NAME_OF[sid])
            cdir.mkdir()
            pdir = proj / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
            pdir.mkdir(parents=True)
            tp = pdir / (sid + ".jsonl")
            tp.write_text(self._transcript(sid))
            (names / sid).write_text("%s\t%s\t%s\n" % (self.NAME_OF[sid], cdir, self.COLOR_OF[sid]))
            self.tpath[sid] = tp
        self.saved = (jd.STATE, jd.PROJECTS, km.NAMES, km._GLOBAL_CLAUDE_MD)
        # The warm parse below reaches Sessions.backend_for and so km._sdk(), which builds the kernel's backend singleton
        # over jd.STATE as it stands when this class is the worker's first builder: saved here, before the rebind, and
        # put back in tearDown before the sandbox is removed (the suite's ratchet in tests/conftest.py names a class that
        # leaves it there).
        self.saved_sdk = km._sdk_backend
        with km._feed_memo_lock:
            self.saved_memo = (dict(km._feed_memo), json.loads(json.dumps(km._FEED_MEMO_STATS)))
            km._feed_memo.clear()                     # every case starts with the memo cold and its counters at zero
            for k in ("hit", "miss", "evict", "derived", "entries", "bytes"):
                km._FEED_MEMO_STATS[k] = 0
            for k in km._FEED_MEMO_STATS["miss_by"]:
                km._FEED_MEMO_STATS["miss_by"][k] = 0
        self.saved_anchors = (dict(km._node_anchor_last), dict(km._node_anchor_rev))
        km._node_anchor_last.clear()
        km._node_anchor_rev.clear()
        # The kernel's judge is one module object for every test module in the process: this board builds over ITS
        # root and nothing else (_rebind_state moves GOALDIR and every derived dir with it; test_feed_session_memo's idiom).
        jd._rebind_state(td)
        jd.PROJECTS = proj
        km.NAMES = jd.NAMES
        km._GLOBAL_CLAUDE_MD = td / "no-global-claude.md"
        km._live_scope.names = None
        km._live_scope.snapshot = None
        jd._discover_cache.clear()
        # api: a node whose trail names a segment no parse holds. web: the REAL segment id, read off the parse this call
        # warms (the same _parse a chat build and _warm_fleet_bg fill the cache through; the feed reads it cache-only).
        self._mint(self.API, "s1", None)
        ps = km._parse(str(self.tpath[self.WEB]), self.WEB, self.NOW)
        seg = next(sg for turn in ps["turns"] for sg in km.em.segments(turn) if sg.get("trigger") == "u1")
        self._mint(self.WEB, seg["id"], "u1")
        self.live = {sid: {"state": "idle", "since": self.NOW - 100, "model": "", "effort": "", "context": None,
                           "compactPct": None, "color": None} for sid in self.SIDS}

    def tearDown(self):
        with km._feed_memo_lock:
            km._feed_memo.clear()
            km._feed_memo.update(self.saved_memo[0])
            km._FEED_MEMO_STATS.clear()
            km._FEED_MEMO_STATS.update(self.saved_memo[1])
        km._node_anchor_last.clear()
        km._node_anchor_last.update(self.saved_anchors[0])
        km._node_anchor_rev.clear()
        km._node_anchor_rev.update(self.saved_anchors[1])
        for sid in self.SIDS:
            jd.parse_cache_drop(sid)
        jd._rebind_state(self.saved[0])
        km._sdk_backend = self.saved_sdk
        jd.PROJECTS, km.NAMES, km._GLOBAL_CLAUDE_MD = self.saved[1:]
        km._live_scope.names = None
        km._live_scope.snapshot = None
        jd._discover_cache.clear()
        self.td.cleanup()

    @staticmethod
    def _rows(feed):
        return {r["id"]: r for c in feed["asks"] for r in (c.get("tree") or [])}

    def test_a_warm_resolve_in_the_feed_bumps_the_revision_of_the_session_it_builds(self):
        self.assertIsNotNone(km._parse_cached(str(self.tpath[self.WEB])), "web's parse is warm: the feed's read finds it")
        self.assertEqual([km._node_anchor_rev.get(s, 0) for s in self.SIDS], [0, 0])
        rows = self._rows(km.build_feed(self.NOW, self.live))
        web, api = rows[self.WEB + ":g1"], rows[self.API + ":g1"]
        self.assertEqual((web["promptAnchorUuid"], web["anchorUuid"]), ("u1", "a1"),
                         "web's node resolved WARM through the feed: the table's entry changed")
        self.assertEqual(km._node_anchor_last.get(self.WEB + ":g1"), ("u1", "a1"))
        self.assertIsNone(api["anchorUuid"], "api's node resolved cold: nothing written for it")
        self.assertEqual(km._node_anchor_rev.get(self.WEB, 0), 1,
                         "the revision the ledger memo, the chat signature and the feed key read rose by one for web")
        self.assertEqual(km._node_anchor_rev.get(self.API, 0), 0, "and not for the peer, whose resolve wrote nothing")

    def test_the_feed_key_sees_the_bump_once_then_settles(self):
        # The key takes `anchors` BEFORE the derivation (stat-then-read), so the build that learns the anchor stores a
        # key one revision behind: the next build re-derives web once, attributed to `anchors`, and the one after hits.
        # The same one-build lag build_session's ledger memo and the chat signature document for their reads.
        km.build_feed(self.NOW, self.live)                         # web's rev 0 -> 1 during the derivation
        b = km._feed_memo_report()
        km.build_feed(self.NOW, self.live)
        a = km._feed_memo_report()
        self.assertEqual((a["derived"] - b["derived"], a["hit"] - b["hit"]), (1, 1), "web re-derives, api hits")
        self.assertEqual({k: a["miss_by"][k] - b["miss_by"].get(k, 0) for k in a["miss_by"]
                          if a["miss_by"][k] != b["miss_by"].get(k, 0)}, {"anchors": 1})
        km.build_feed(self.NOW, self.live)
        c = km._feed_memo_report()
        self.assertEqual((c["derived"] - a["derived"], c["hit"] - a["hit"]), (0, 2), "settled: the same anchors bump nothing")
        self.assertEqual(km._node_anchor_rev.get(self.WEB, 0), 1)

    def test_the_three_memo_keys_read_the_one_revision(self):
        # the readers the bump exists for, each keyed on _node_anchor_rev before its walk (upstream's text at the tip)
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn("_lkey = (_seams_sig, _ck, _node_anchor_rev.get(sid, 0))", src)   # build_session's ledger memo
        self.assertIn("sig.append(_node_anchor_rev.get(sid, 0))", src)                    # the chat build's signature
        self.assertIn("anchors = _node_anchor_rev.get(fsid, 0)", src)                      # the feed entry's key component


if __name__ == "__main__":
    unittest.main()
