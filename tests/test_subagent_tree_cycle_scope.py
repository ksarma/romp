#!/usr/bin/env python3
"""One sample of a session's subagents tree per pusher cycle, however many readers ask (2026-09-18).

The walk memo (_SUBAGENT_TREES, 2026-09-16) made an unchanged tree cost one lstat per known directory instead of a
listing, but every reader still paid that validation itself: within ONE pusher cycle the chat build's sidecar-map reads
(_stamp_agents, then _awaiting_items_payload -> _session_background_items -> _awaiting_live_rows, then _awaiting_nest for
the agent row it minted), the feed key's _subagent_dirs_ident, the feed derivation's _session_awaiting and a viewer
frame's agent-file re-walk on a cache miss (its first open, or after a file landed in a directory the walk read; the
frame's hit-path re-stats are a separate route) each re-validated the same root. Live on the measured kernel that was
63,473 validations, 5.2 M lstats and 346 s of validation wall over 3,867 cycles; the ~39,500 outside the feed key are the
candidates, an estimated 30-50% of all validations re-samples of a root another reader had taken in the same cycle, and
the `scoped` tally measures the realized share. The fix is the _live_scope idiom the liveness map, the names registry,
the discover rows and the billing
availability already use: _pusher_cycle (and _jobs_cycle, and a connect push's chat loop on a handler thread through
_chat_push_scopes_open) opens `subagent_trees`, the first reader of a root validates or walks, every later reader of the
cycle is served that sample with no lstat, and the slot is cleared with the cycle.

Pinned here, red-first on the count: (1) one cycle with a chat client validates or walks the root exactly once and serves
the rest from the sample (on stock the chat build alone reads the map three times before the feed key, so the count is
more than one, and `scoped` is not a key of the stats); (2) outside a scope every call samples afresh (the handler-thread
contract); (3) a directory change landing after a cycle's sample is seen by the next cycle, whose one sample is then a
miss; (4) the jobs pass opens and closes the slot like the pusher; (5) a connect push on a handler thread shares one
sample across its chat loop and closes its own scope with it; (6) an EMPTY answer (no root, or not a directory) is never
scoped, so a tree appearing under an open scope is found by _subagent_file rather than memoized as a miss under a stamp
newer than the listing it read (the refuter's amendment); (7) the dependency key the agent-file lookup's miss walk records
for each tree it looked through, a sibling fsid's or its own, comes from the read that answered the lookup, every
directory of that tree under the (st_mtime, st_size) of the read's own stat, so a file landing after the cycle's sample
leaves the recorded key behind the next signature's re-stat (2026-09-24; red on the fresh root stat the walk noted
before); (8) a live link or a file at a sibling's or the own subagents path (never listed) is noted under that path's
own stat key, as the walk noted it before, so a tree replacing it moves the key, and a path that changed between the
read and that stat is noted None, which no re-stat of a directory, a live link or a file equals, on the own path as on a
sibling's; one path that holds a live link, then a file, then a dangling link, each replaced by a tree before the next
cycle, rebuilds the tab after every swap; (9) an absent subagents path whose fsid directory exists is noted None from
the read, so a tree appearing after the read moves the key, and the identity lstat that detects a change follows the
stat, so a path that changes after that lstat keeps the key the stat took and a tree placed there after it is never
recorded under its own key. Synthetic fixtures only: placeholder ids, the notes-api demo world (sessions web and api), a
temp directory."""
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads (the tests/test_kernel_pusher_snapshot.py preamble): the kernel and the judge resolve
# their state root at import, and only pytest runs conftest's floor. The root minted here is outside conftest's belt, so
# session hosts are switched off in it too (a state root with no `session-hosts` file starts a real host for any session
# it connects).
_ROOT = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = _ROOT
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.makedirs(os.path.join(_ROOT, "romp"), exist_ok=True)
with open(os.path.join(_ROOT, "romp", "session-hosts"), "w") as _fh:
    _fh.write("off")
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_subagent_tree_cycle_scope", os.path.join(BIN, "romp-kernel"))
jd = km.jd

NOW = 1781100000
SID = "11111111-2222-3333-4444-555555555555"       # web: the session with a subagents tree and an Agent in flight
SID2 = "11111111-2222-3333-4444-565656565656"      # api: a plain session, no subagents directory
AID = "a1111111111111111"                          # the top-level agent
AID_WF = "a2222222222222222"                       # a workflow agent, one level down
AID_NEW = "a3333333333333333"                      # the agent whose directory lands mid-test
AID_GHOST = "a4444444444444444"                    # the agent the dependency-key cases look up: its file lands under a sibling
SIB = "11111111-2222-3333-4444-575757575757"       # a sibling fsid in web's and api's project directory (a /clear fork's)
TU, TU_WF, TU_NEW = "toolu_tree_0001", "toolu_tree_0002", "toolu_tree_0003"
AGED_NS = 10_000_000_000                           # ten seconds: past the racy window, as tests/test_subagent_tree_memo.py ages


def _age(root):
    """Every directory under `root` stamped ten seconds ago, so the memo may vouch for it."""
    t = time.time_ns() - AGED_NS
    for r, _ds, _fs in os.walk(root):
        os.utime(r, ns=(t, t))


class _World(unittest.TestCase):
    """The tests/test_kernel_pusher_snapshot.py cycle world, extended with a subagents tree: a hermetic state root, two
    sessions on disk (web with a transcript whose last record is an Agent tool_use without its result, so the turn is
    open, and a subagents tree beside it; api with a user record alone), web's live row carrying the Agent launch in its
    bgTasks set without a taskId (so _bg_live_norm yields an agent row with no agentId, and _awaiting_live_rows reads
    the sidecar map for it, then _awaiting_nest reads it again for the row it minted), the pusher's ticks stubbed, the
    racy window closed as the memo tests close it, and every scope slot cleared after each test."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        self.saved = (jd.NAMES, jd.PROJECTS, jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR, jd.STATE,
                      km.NAMES, km.Sessions.live, km._sdk,
                      km._auto_nudge_tick, km._clear_done_working_notes,
                      km._turn_notify_tick, km._api_health_frame, km._api_health_push, km._lift_spent_awaiting)
        names = td / "names"; names.mkdir()
        proj = td / "projects"; proj.mkdir()
        jd.NAMES, jd.PROJECTS = names, proj
        jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR = td / "captions", td / "archive", td / "goals"
        for d in (jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR):
            d.mkdir()
        jd.STATE = td
        km.NAMES = names
        km._sdk = lambda: None
        cdir = td / "notes-api"; cdir.mkdir()
        pdir = proj / jd.re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
        pdir.mkdir(parents=True)
        user = {"type": "user", "timestamp": "2026-06-11T00:00:00.000Z", "uuid": "u1",
                "parentUuid": None, "promptSource": "typed",
                "message": {"role": "user", "content": "check the api tests"}}
        launch = {"type": "assistant", "timestamp": "2026-06-11T00:00:05.000Z", "uuid": "a1", "parentUuid": "u1",
                  "message": {"role": "assistant", "content": [
                      {"type": "tool_use", "id": TU, "name": "Agent",
                       "input": {"description": "check the api tests", "prompt": "look at the failing test"}}]}}
        self.paths = {}
        for sid, name, recs in ((SID, "web", (user, launch)), (SID2, "api", (user,))):
            self.paths[sid] = str(pdir / (sid + ".jsonl"))
            (pdir / (sid + ".jsonl")).write_text("".join(json.dumps(r) + "\n" for r in recs))
            (names / sid).write_text("%s\t%s\t#abcdef\n" % (name, str(cdir)))
        # web's subagents tree, the tests/test_subagent_tree_memo.py shape: one agent pair at the top, one workflow
        # agent's pair under workflows/wf_<id>/
        self.subdir = pdir / SID / "subagents"
        self.wf = self.subdir / "workflows" / ("wf_%016x" % (int(SID[-4:], 16)))
        self.wf.mkdir(parents=True)
        (self.subdir / ("agent-%s.meta.json" % AID)).write_text(json.dumps(
            {"agentType": "general-purpose", "description": "check the api tests", "spawnDepth": 1, "toolUseId": TU}))
        (self.subdir / ("agent-%s.jsonl" % AID)).write_text("")
        (self.wf / ("agent-%s.meta.json" % AID_WF)).write_text(json.dumps(
            {"agentType": "Workflow", "description": "tidy the readme", "spawnDepth": 1, "toolUseId": TU_WF}))
        (self.wf / ("agent-%s.jsonl" % AID_WF)).write_text("")
        _age(str(self.subdir))
        self.roots = [str(self.subdir), str(km._subagents_dir(self.paths[SID2]))]
        meta = {"state": "waiting", "since": NOW - 5, "model": "", "effort": "", "context": None,
                "compactPct": None, "color": None, "mode": "", "backend": "sdk"}
        self.row = {SID: dict(meta, bgTasks=[{"toolUseId": TU, "desc": "check the api tests", "since": NOW - 3,
                                              "type": "local_agent"}]),
                    SID2: dict(meta)}
        km.Sessions.live = lambda: dict(self.row)
        # the pusher's ticks and the jobs pass's, stubbed: none of them is a reader of the tree, and none is under test
        km._turn_notify_tick = lambda now, live_map: None
        km._api_health_frame = lambda now, live_map: None
        km._api_health_push = lambda frame: None
        km._lift_spent_awaiting = lambda now, live_map: None
        km._clear_done_working_notes = lambda now, live_map: None
        self.saved_clients = list(km._clients)
        # os.utime back-dates mtime but sets ctime to now, and the racy mask covers both stamps: the window is closed so
        # the memo can vouch for the aged fixture (the tests/test_subagent_tree_memo.py _Tree rule)
        self._racy = mock.patch.object(km, "_SUBAGENT_DIR_RACY_NS", 0)
        self._racy.start()
        self._forget()

    def _forget(self):
        for r in self.roots:
            km._SUBAGENT_TREES.pop(r, None)
        km._SUBAGENT_META_CACHE.clear()
        km._SUBAGENT_FILE_CACHE.clear()
        km._built_chat.clear()
        km._built_feed[:] = [None, None, 0.0, 0.0]

    def tearDown(self):
        self._racy.stop()
        (jd.NAMES, jd.PROJECTS, jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR, jd.STATE,
         km.NAMES, km.Sessions.live, km._sdk,
         km._auto_nudge_tick, km._clear_done_working_notes,
         km._turn_notify_tick, km._api_health_frame, km._api_health_push, km._lift_spent_awaiting) = self.saved
        with km._clients_lock:
            km._clients[:] = self.saved_clients
        # every scope slot, so a failing test cannot leak a cycle's memo into the next on this thread
        for k in ("snapshot", "sessions", "paths", "names", "auth", "msgsum", "files_stat", "files_dirty",
                  "subagent_trees", "chat_shared", "chat_push_owned"):
            setattr(km._live_scope, k, None)
        km._chat_dep_scope.deps = None
        self._forget()
        self.td.cleanup()

    def _chat_client(self):
        """A connected chat client, so the push leg builds the tabs for real; returns the list its sends land in."""
        sent = []
        with km._clients_lock:
            km._clients[:] = [{"app": "chat", "alive": True, "wid": "", "qbytes": 0, "send": sent.append}]
        return sent

    @staticmethod
    def _validations(before, after):
        """How many times the memo validated or walked: hit + miss moved."""
        return (after["hit"] + after["miss"]) - (before["hit"] + before["miss"])


class OneSampleOfEachRootPerCycle(_World):
    def test_one_pusher_cycle_samples_a_subagents_root_once_however_many_readers(self):
        """RED FIRST. In this fixture the chat build is the cycle's first reader and reads the sidecar map three times
        (_stamp_agents; _awaiting_items_payload -> _session_background_items -> _awaiting_live_rows, since the Agent
        tool_use has no result, so the turn is open and _session_awaiting answers None before reading, in build_session
        and in _feed_session_entry alike; then _awaiting_nest for the agent row it minted), and the feed key's
        _subagent_dirs_ident reads the tree once more: on stock each is a validation of its own, so the count is more
        than one, and `scoped` is not a key of the stats. With the cycle scope the first read is the cycle's one sample
        and the rest are served from it."""
        sent = self._chat_client()
        before = dict(km._SUBAGENT_TREE_STATS)
        km._pusher_cycle()
        after = dict(km._SUBAGENT_TREE_STATS)
        self.assertTrue(any('"type": "session"' in s for s in sent), "the push leg really built the session")
        self.assertEqual(self._validations(before, after), 1,
                         "one validation or walk of the root per cycle: the chat build's sidecar-map reads and the feed key "
                         "read one sample")
        self.assertGreaterEqual(after["scoped"] - before.get("scoped", 0), 2, "the later readers were served the sample")
        self.assertIsNone(getattr(km._live_scope, "subagent_trees", None), "the scope ends with the cycle")

    def test_outside_a_cycle_every_call_samples_afresh(self):
        """The handler-thread contract (a WS viewer frame, GET /feed.json): no scope open, every call validates."""
        km._live_scope.subagent_trees = None
        root = str(self.subdir)
        before = dict(km._SUBAGENT_TREE_STATS)
        km._subagent_tree(root)
        km._subagent_tree(root)
        after = dict(km._SUBAGENT_TREE_STATS)
        self.assertEqual(self._validations(before, after), 2, "no scope, no memo: two calls are two samples")
        self.assertEqual(after["scoped"], before["scoped"], "nothing was served from a scope")

    def test_a_change_after_the_cycles_sample_is_seen_by_the_next_cycle(self):
        """The exactness claim: once per cycle, never stale past the cycle. A workflow directory and its sidecar land
        after cycle one's sample; cycle two's one sample is a miss (the tree changed), the memo holds the new directory,
        and the feed key's subagents component moved for the session. The chat tab is cycle two's first reader here too:
        its taskout dependency on the workflows directory rebuilds it. The feed is forced to rebuild with a dirty mark
        (the refuter's amendment): within REBUILD_MIN_S _feed_servable would otherwise serve cycle one's build and the
        key would never be re-taken."""
        self._chat_client()
        km._pusher_cycle()
        root = str(self.subdir)
        self.assertIn(root, km._SUBAGENT_TREES, "cycle one sampled the root")
        new = self.subdir / "workflows" / ("wf_%016x" % 0xee)
        new.mkdir()
        (new / ("agent-%s.meta.json" % AID_NEW)).write_text(json.dumps(
            {"agentType": "Workflow", "description": "check the readme links", "spawnDepth": 1, "toolUseId": TU_NEW}))
        (new / ("agent-%s.jsonl" % AID_NEW)).write_text("")
        feed_before = km._feed_memo_report()["miss_by"].get("subagents", 0)
        before = dict(km._SUBAGENT_TREE_STATS)
        km._mark_views_dirty()
        km._pusher_cycle()
        after = dict(km._SUBAGENT_TREE_STATS)
        self.assertIn(str(new), km._SUBAGENT_TREES[root][0], "the next cycle's sample holds the new directory")
        self.assertEqual(self._validations(before, after), 1, "again exactly one sample of the root")
        self.assertEqual(after["miss"] - before["miss"], 1, "...and it was a miss: the tree changed")
        self.assertEqual(km._feed_memo_report()["miss_by"].get("subagents", 0) - feed_before, 1,
                         "the feed key's subagents component moved for the session")
        self.assertIsNone(getattr(km._live_scope, "subagent_trees", None))

    def test_the_jobs_pass_opens_and_closes_the_scope(self):
        """The housekeeping pass's twin (the reminder walk's _session_awaiting readers share one sample per root per pass;
        precedent: the snapshot test's jobs twin). RED FIRST: on stock the slot never exists."""
        got = {}
        km._auto_nudge_tick = lambda now, live_map, **kw: got.setdefault(
            "open", isinstance(getattr(km._live_scope, "subagent_trees", None), dict))
        km._jobs_cycle()
        self.assertIs(got.get("open"), True, "the pass opened the scope before its jobs ran")
        self.assertIsNone(getattr(km._live_scope, "subagent_trees", None), "the scope ends with the pass")

    def test_a_connect_push_on_a_handler_thread_shares_one_sample_across_its_chat_loop(self):
        """A push outside any cycle (a fresh client on its handler thread) opens the slot for its chat loop through
        _chat_push_scopes_open, as it opens the caption-map slot and the names snapshot there, and closes exactly what
        it opened (the ownership rule tests/test_chat_build_sig_inputs.py pins for names and msgsum). The feed is warmed
        by a cycle first, so the connect serves it and never rebuilds; the tab is dropped from _built_chat so the
        connect rebuilds it. RED FIRST: on stock the rebuilt tab validates three times."""
        self._chat_client()
        km._pusher_cycle()                                     # warms the feed: the connect serves it, no feed key read
        km._built_chat.clear()                                 # the tab rebuilds on the connect
        km._live_scope.subagent_trees = None                   # no cycle scope on this thread
        sent = []
        client = {"app": "chat", "alive": True, "wid": "", "qbytes": 0, "send": sent.append}
        before = dict(km._SUBAGENT_TREE_STATS)
        km._push([client], connect=True)
        after = dict(km._SUBAGENT_TREE_STATS)
        self.assertTrue(any('"type": "session"' in s for s in sent), "the connect push built the tab")
        self.assertEqual(self._validations(before, after), 1, "the push's chat loop shared one sample of the root")
        self.assertIsNone(getattr(km._live_scope, "subagent_trees", None), "the push's own scope closes with its chat loop")
        self.assertIsNone(getattr(km._live_scope, "chat_push_owned", None), "the owned slot list was consumed by the close")

    def test_an_empty_answer_is_never_scoped_so_a_tree_appearing_under_an_open_scope_is_found(self):
        """The refuter's amendment: _subagent_file_walk stamps the root itself with a fresh _dir_stamp and hands
        _find_agent_file the tree it read with _subagent_tree; served an older EMPTY sample it would memoize a nested
        agent's miss under a stamp newer than the listing it read, a stale miss that outlives the cycle because
        _subagent_file's hit path re-stats and never re-walks. So a zero-directory answer (no root, or not a directory)
        is never stored in the scope, and every caller re-lstats such a root as today. On the spec's storage rule as
        written this returned None twice."""
        tpath = self.paths[SID2]                               # api: no subagents directory yet
        own = km._subagents_dir(tpath)
        self.assertFalse(own.exists())
        km._live_scope.subagent_trees = {}
        try:
            self.assertEqual(km._subagent_tree(str(own)), ((), ()))
            self.assertNotIn(str(own), km._live_scope.subagent_trees, "an empty answer carries no stamp: not scoped")
            wf = own / "workflows" / ("wf_%016x" % 0xab)
            wf.mkdir(parents=True)
            (wf / ("agent-%s.meta.json" % AID_NEW)).write_text(json.dumps({"agentType": "Workflow", "toolUseId": TU_NEW}))
            (wf / ("agent-%s.jsonl" % AID_NEW)).write_text("")
            self.assertEqual(km._subagent_file(tpath, AID_NEW), wf / ("agent-%s.jsonl" % AID_NEW),
                             "found inside the scope: the empty sample did not stand in for the tree")
            self.assertIn(str(own), km._live_scope.subagent_trees, "the walked tree, with its stamps, is the scoped sample")
        finally:
            km._live_scope.subagent_trees = None
        self.assertEqual(km._subagent_file(tpath, AID_NEW), wf / ("agent-%s.jsonl" % AID_NEW),
                         "and after the scope: the memo holds the path, not a None")


class DependencyKeyFromTheHeldRead(_World):
    """The key a chat build records for a subagents tree that the agent-file lookup's miss walk looked through
    (_subagent_file_walk), a sibling fsid's or its own, comes from the read that answered the lookup, never from a stat
    taken after it (2026-09-24). Inside a cycle scope _find_agent_file is answered the cycle's held pair for a root
    another reader sampled earlier; a note taken from a fresh _chat_stat_key stat after that post-dates the listing, so a file
    landing after the sample under a directory the listing lacked is recorded under its own post-landing key, which every
    later re-stat equals, and the tab that showed the file missing is never rebuilt. And every directory of the tree is
    noted, not the root alone, since a landing under a listed child (workflows/) moves that child and not the root.
    The world: api's transcript looks up AID_GHOST, whose file is nowhere until it lands, after the tree's sample, under
    the sibling fsid SIB's tree (api has no tree of its own there) or under api's own tree (the own-tree case), each
    tree aged into the past so the landing moves a stamp."""

    def setUp(self):
        super().setUp()
        self.tpath = self.paths[SID2]
        self.sib = Path(self.tpath).parent / SIB / "subagents"
        self.root = str(self.sib)
        self.landed = self.sib / "workflows" / "wf_1" / ("agent-%s.jsonl" % AID_GHOST)
        self.addCleanup(km._SUBAGENT_TREES.pop, self.root, None)

    def _land(self):
        """The agent's file created with its parents under the sibling's tree."""
        self.landed.parent.mkdir(parents=True, exist_ok=True)
        self.landed.write_text("")

    def _lookup_recorded(self):
        """The lookup under a chat build's record: (the answer, {path: key} as _chat_build_deps records it)."""
        km._chat_dep_scope.deps = {"task_outs": [], "postal_any": False}
        try:
            got = km._subagent_file(self.tpath, AID_GHOST)
            rec = dict(km._chat_build_deps(SID2, {"events": []})["task_outs"])
        finally:
            km._chat_dep_scope.deps = None
        return got, rec

    def _next_scope_lookup(self):
        """The next scope's lookup of the same agent, opened and closed as a cycle opens and closes the slot."""
        km._live_scope.subagent_trees = {}
        try:
            return km._subagent_file(self.tpath, AID_GHOST)
        finally:
            km._live_scope.subagent_trees = None

    @staticmethod
    def _pair(st):
        return (st.st_mtime, st.st_size)

    def test_a_held_sibling_roots_key_is_the_held_stats_pair_not_a_re_stat_after_the_landing_moved_it(self):
        """D2a. The sibling's tree is its root alone. Red before the fix on (2): the walk noted the root under a fresh
        _chat_stat_key taken after the landing, later than the held sample it then looked the tree up through: the
        post-landing pair, equal to the re-stat."""
        self.sib.mkdir(parents=True)
        _age(self.root)
        km._live_scope.subagent_trees = {}
        try:
            held = km._subagent_tree(self.root)
            self.assertEqual(held[0], (self.root,), "premise: the sampled tree is the root alone")
            self.assertIs(km._live_scope.subagent_trees.get(self.root), held, "premise: the scope holds the sample")
            held_pair = self._pair(held[1][0])
            self._land()
            restat = km._chat_stat_key(self.root)
            self.assertNotEqual(restat, held_pair, "premise: the root's re-stat after the landing differs from the held "
                                "stat's pair (re-stat %r, held %r)" % (restat, held_pair))
            got, rec = self._lookup_recorded()
        finally:
            km._live_scope.subagent_trees = None
        self.assertIsNone(got, "(1) the lookup inside the scope answers None (the held listing lacks workflows/)")
        restat = km._chat_stat_key(self.root)
        self.assertEqual(rec.get(self.root), held_pair,
                         "(2) the key recorded for the sibling root equals the held stat's (st_mtime, st_size) "
                         "(recorded %r, held %r, re-stat %r)" % (rec.get(self.root), held_pair, restat))
        self.assertNotEqual(rec.get(self.root), restat,
                            "(2) the key recorded for the sibling root differs from its re-stat "
                            "(recorded %r, re-stat %r)" % (rec.get(self.root), restat))
        self.assertEqual(self._next_scope_lookup(), self.landed, "(3) the next scope's lookup answers the landed file")

    def test_a_held_sibling_trees_listed_child_is_recorded_under_its_held_stats_pair(self):
        """D2b. The sibling's tree is its root and an empty workflows/, so the landing moves workflows/ and not the root.
        Red before the fix: the walk recorded no key for workflows/, and the root's recorded key equalled its re-stat."""
        wf = self.sib / "workflows"
        wf.mkdir(parents=True)
        _age(self.root)
        km._live_scope.subagent_trees = {}
        try:
            held = km._subagent_tree(self.root)
            self.assertEqual(held[0], (self.root, str(wf)), "premise: the sampled tree is the root and workflows/")
            self.assertIs(km._live_scope.subagent_trees.get(self.root), held, "premise: the scope holds the sample")
            root_pair, wf_pair = self._pair(held[1][0]), self._pair(held[1][1])
            self._land()
            wf_restat, root_restat = km._chat_stat_key(str(wf)), km._chat_stat_key(self.root)
            self.assertNotEqual(wf_restat, wf_pair, "premise: workflows/'s re-stat after the landing differs from its "
                                "held stat's pair (re-stat %r, held %r)" % (wf_restat, wf_pair))
            self.assertEqual(root_restat, root_pair, "premise: the root's re-stat after the landing equals its held "
                             "stat's pair (re-stat %r, held %r)" % (root_restat, root_pair))
            got, rec = self._lookup_recorded()
        finally:
            km._live_scope.subagent_trees = None
        self.assertIsNone(got, "the lookup inside the scope answers None (the held listing lacks workflows/wf_1/)")
        wf_restat = km._chat_stat_key(str(wf))
        self.assertEqual(rec.get(str(wf)), wf_pair,
                         "the key recorded for workflows/ equals its held stat's (st_mtime, st_size) (recorded %r, held "
                         "%r, re-stat %r; recorded for the root %r, the root's re-stat %r)"
                         % (rec.get(str(wf)), wf_pair, wf_restat, rec.get(self.root), km._chat_stat_key(self.root)))
        self.assertNotEqual(rec.get(str(wf)), wf_restat, "the key recorded for workflows/ differs from its re-stat "
                            "(recorded %r, re-stat %r)" % (rec.get(str(wf)), wf_restat))
        self.assertEqual(self._next_scope_lookup(), self.landed, "the next scope's lookup answers the landed file")

    def test_the_own_trees_listed_child_is_recorded_under_its_held_stats_pair(self):
        """The same rule on the walk's own tree, which it reads once and notes when the project directory's listing
        reaches it: api's own tree is its root and an empty workflows/, sampled first in the scope, and the file lands
        under workflows/. Red before the fix: the own root was noted under a fresh _chat_stat_key stat (equal to its held
        pair, since the landing did not move it) and workflows/ not at all."""
        own = km._subagents_dir(self.tpath)
        wf = own / "workflows"
        wf.mkdir(parents=True)
        _age(str(own))
        landed = wf / "wf_1" / ("agent-%s.jsonl" % AID_GHOST)
        self.addCleanup(km._SUBAGENT_TREES.pop, str(own), None)
        km._live_scope.subagent_trees = {}
        try:
            held = km._subagent_tree(str(own))
            self.assertEqual(held[0], (str(own), str(wf)), "premise: the sampled tree is the own root and workflows/")
            self.assertIs(km._live_scope.subagent_trees.get(str(own)), held, "premise: the scope holds the sample")
            wf_pair = self._pair(held[1][1])
            landed.parent.mkdir()
            landed.write_text("")
            wf_restat = km._chat_stat_key(str(wf))
            self.assertNotEqual(wf_restat, wf_pair, "premise: workflows/'s re-stat after the landing differs from its "
                                "held stat's pair (re-stat %r, held %r)" % (wf_restat, wf_pair))
            got, rec = self._lookup_recorded()
        finally:
            km._live_scope.subagent_trees = None
        self.assertIsNone(got, "the lookup inside the scope answers None (the held listing lacks workflows/wf_1/)")
        wf_restat = km._chat_stat_key(str(wf))
        self.assertEqual(rec.get(str(wf)), wf_pair,
                         "the key recorded for the own workflows/ equals its held stat's (st_mtime, st_size) (recorded "
                         "%r, held %r, re-stat %r; recorded for the own root %r, its re-stat %r)"
                         % (rec.get(str(wf)), wf_pair, wf_restat, rec.get(str(own)), km._chat_stat_key(str(own))))
        self.assertNotEqual(rec.get(str(wf)), wf_restat, "the key recorded for the own workflows/ differs from its "
                            "re-stat (recorded %r, re-stat %r)" % (rec.get(str(wf)), wf_restat))
        self.assertEqual(self._next_scope_lookup(), landed, "the next scope's lookup answers the landed file")

    def test_with_no_scope_open_the_same_sequence_finds_the_file(self):
        """The control: D2a's sequence with no scope open. The lookup samples the sibling's tree afresh after the landing
        and answers the file, so the None inside a scope is the held sample's one-cycle lag."""
        self.sib.mkdir(parents=True)
        _age(self.root)
        self.assertIsNone(getattr(km._live_scope, "subagent_trees", None), "premise: no scope is open")
        self.assertEqual(km._subagent_tree(self.root)[0], (self.root,), "premise: the sampled tree is the root alone")
        self._land()
        got, _rec = self._lookup_recorded()
        self.assertEqual(got, self.landed, "with no scope open the lookup answers the landed file")


class WalkNoteForAPathThatHoldsNoTree(_World):
    """The miss walk's note for a subagents path, a sibling fsid's or its own, that holds no tree (2026-09-24). The rule
    over the paths this class covers: a live link or a file at the path (never listed, never scoped) is noted under the
    path's _chat_stat_key, as the walk noted every such path before its note moved to the tree read (the link target's
    (st_mtime, st_size), or the file's), so a real tree replacing the link or the file, holding the agent's file under
    workflows/wf_1/, moves the key against the next signature's re-stat and the tab that showed the file missing is
    rebuilt; an absent path (its fsid directory present) or a dangling link is noted None; a path that changed between
    the read and that stat is noted None; and the identity lstat that detects such a change is taken after the stat. The
    read-then-replace cases, at a sibling's path and at the own path, pin the None noted for a path changed after the
    read; the absent-path cases pin the None an absent path is noted from the read; and the cases that place a tree
    right after the note's identity lstat pin the order of that lstat and the stat.

    The first form of the read-keyed note recorded nothing for a live link or a file, as _subagent_meta_map records
    nothing for one, and nothing then moved when the tree replaced it. Under that form the cases that place a live link
    or a file once, at a sibling's path and at the own path, and both read-then-replace cases are red on the key's
    presence; the sequence cases are red on the rebuild assertion in their link and file subtests, and their dangling
    subtests pass (that form notes a dangling link None too). Every other case of the class names its own red in its
    own docstring, except the dangling-link control, which says why it stays green. The world: api's transcript looks
    up AID_GHOST, whose file is nowhere; the link's target and the file are aged into the past, so the tree that
    replaces them differs in mtime from what the note recorded."""

    def setUp(self):
        super().setUp()
        self.tpath = self.paths[SID2]
        self.target = Path(self.tpath).parent.parent / "elsewhere"   # outside the project directory: no fsid of its own

    def _lookup_recorded(self):
        """The lookup under a chat build's record: (the answer, {path: key} as _chat_build_deps records it)."""
        km._chat_dep_scope.deps = {"task_outs": [], "postal_any": False}
        try:
            got = km._subagent_file(self.tpath, AID_GHOST)
            rec = dict(km._chat_build_deps(SID2, {"events": []})["task_outs"])
        finally:
            km._chat_dep_scope.deps = None
        return got, rec

    def _place(self, p, kind):
        """A live link to an aged directory, a dangling link, or an aged file at `p`, its fsid directory created."""
        p.parent.mkdir(parents=True, exist_ok=True)
        if kind == "file":
            p.write_text("x")
            t = time.time_ns() - AGED_NS
            os.utime(str(p), ns=(t, t))
        elif kind == "link":
            self.target.mkdir()
            _age(str(self.target))
            os.symlink(str(self.target), str(p))
        else:
            os.symlink(str(self.target), str(p))                    # the target is never created: a dangling link
        self.assertEqual(km._subagent_tree(str(p))[0], (), "premise: the read at %s answers no directory" % kind)

    @staticmethod
    def _replace_with_tree(p):
        """The link or file at `p` replaced by a real subagents tree holding the agent's file one workflow down."""
        os.unlink(str(p))
        landed = p / "workflows" / "wf_1" / ("agent-%s.jsonl" % AID_GHOST)
        landed.parent.mkdir(parents=True)
        landed.write_text("")
        return landed

    def _check(self, p, kind):
        self._place(p, kind)
        before = km._chat_stat_key(str(p))
        got, rec = self._lookup_recorded()
        self.assertIsNone(got, "the lookup answers None: nothing is read through a %s" % kind)
        self.assertIn(str(p), rec, "a key is recorded for the %s at the subagents path (recorded paths %r)"
                      % (kind, sorted(rec)))
        self.assertEqual(rec[str(p)], before, "the key recorded for the %s is the path's _chat_stat_key (recorded %r, "
                         "stat key %r)" % (kind, rec[str(p)], before))
        landed = self._replace_with_tree(p)
        restat = km._chat_stat_key(str(p))
        self.assertNotEqual(rec[str(p)], restat, "the key recorded for the %s differs from the path's re-stat once a "
                            "tree replaced it (recorded %r, re-stat %r)" % (kind, rec[str(p)], restat))
        self.assertEqual(km._subagent_file(self.tpath, AID_GHOST), landed, "the next lookup answers the landed file")

    def test_a_live_link_at_a_sibling_path_is_noted_under_the_targets_stat_key(self):
        self._check(Path(self.tpath).parent / SIB / "subagents", "link")

    def test_a_file_at_a_sibling_path_is_noted_under_its_stat_key(self):
        self._check(Path(self.tpath).parent / SIB / "subagents", "file")

    def test_a_live_link_at_the_own_path_is_noted_under_the_targets_stat_key(self):
        self._check(km._subagents_dir(self.tpath), "link")

    def test_a_file_at_the_own_path_is_noted_under_its_stat_key(self):
        self._check(km._subagents_dir(self.tpath), "file")

    def test_a_dangling_link_at_a_sibling_path_is_noted_none(self):
        """The control, green before and after the read-keyed note: a dangling link notes None, what its re-stat
        answers until something real is placed there."""
        p = Path(self.tpath).parent / SIB / "subagents"
        self._place(p, "dangling")
        got, rec = self._lookup_recorded()
        self.assertIsNone(got, "the lookup answers None")
        self.assertIn(str(p), rec, "a key is recorded for the dangling link (recorded paths %r)" % sorted(rec))
        self.assertIsNone(rec[str(p)], "the key recorded for the dangling link is None (recorded %r)" % (rec[str(p)],))

    def _replaced_between_the_read_and_the_note(self, p, where):
        """A live link at `p`, replaced by a tree holding the agent's file under workflows/wf_1/ right after the walk's
        read of `p` returns. The premise is one read of `p` and then the replacement; the lookup answers None, a key is
        recorded for `p`, that key differs from the path's re-stat after the replacement, and the next lookup answers
        the landed file."""
        self._place(p, "link")
        real = km._subagent_tree
        swapped = []

        def read_then_swap(d):
            out = real(d)
            if str(d) == str(p) and not swapped:
                swapped.append(self._replace_with_tree(p))
            return out
        with mock.patch.object(km, "_subagent_tree", read_then_swap):
            got, rec = self._lookup_recorded()
        self.assertEqual(len(swapped), 1, "premise: the %s was read once and then replaced" % where)
        self.assertIsNone(got, "the lookup answers None: the read saw the link")
        self.assertIn(str(p), rec, "a key is recorded for the %s (recorded paths %r)" % (where, sorted(rec)))
        restat = km._chat_stat_key(str(p))
        self.assertNotEqual(rec[str(p)], restat, "the key recorded for the %s differs from its re-stat after the "
                            "replacement (recorded %r, re-stat %r)" % (where, rec[str(p)], restat))
        self.assertEqual(km._subagent_file(self.tpath, AID_GHOST), swapped[0],
                         "the next lookup answers the landed file")

    def test_a_link_replaced_by_a_tree_between_the_read_and_the_note_leaves_a_key_the_re_stat_differs_from(self):
        """The note's stat is taken after the read. When a tree replaces the link in between (injected right after the
        read of the sibling's path returns), the recorded key must still differ from the path's re-stat, so the tab
        that showed the file missing is rebuilt; a bare stat after the read would record the replacing tree's own key,
        equal to every later re-stat."""
        self._replaced_between_the_read_and_the_note(Path(self.tpath).parent / SIB / "subagents", "sibling's path")

    def test_the_own_path_link_replaced_by_a_tree_between_the_read_and_the_note_leaves_a_key_the_re_stat_differs_from(self):
        """The own-path twin of the case above: the live link is at the transcript's own subagents path, and the tree
        replaces it right after the read of that path returns. Red with the identity check removed, on the recorded key
        equal to the re-stat: the stat taken after the read answers the replacing tree's own key. Among its other reds
        are the fork's merge of romp-on/romp PR #1822, whose own-path stat came after the read, and the own path's note
        taken from a second read of the path in place of the one that answered the lookup; the red log that fork PR
        #910's build record names has the rest."""
        self._replaced_between_the_read_and_the_note(km._subagents_dir(self.tpath), "own path")

    def _placed_after_the_notes_identity_lstat(self, p):
        """A live link at `p`. While the walk's note runs for `p`, and only then, a tree holding the agent's file under
        workflows/wf_1/ replaces the link right after the note's identity lstat of `p` returns. The premises are one
        identity lstat of `p` inside the note and one swap; the lookup answers None, a key is recorded for `p`, that key
        differs from the path's re-stat after the swap, and the next lookup answers the landed file. With the identity
        lstat taken before the stat key the tree placed between the two passes the identity check, the stat answers the
        tree's own key and the walk records it, equal to the re-stat. These cases cannot run at the fork's merge of
        romp-on/romp PR #1822 or under the read-keyed note's first form, which have no _subagent_walk_dep_note (an
        AttributeError, not a red); with the identity check removed they fail on the premise of one identity lstat,
        which is not their red either."""
        self._place(p, "link")
        real_lstat, real_note = km._lstat_or_none, km._subagent_walk_dep_note
        inside, swapped, calls = [], [], []

        def note(d, tree):
            inside.append(str(d))
            try:
                return real_note(d, tree)
            finally:
                inside.pop()

        def lstat(q):
            out = real_lstat(q)
            if inside and inside[-1] == str(p) and str(q) == str(p):
                calls.append(str(q))
                if not swapped:
                    swapped.append(self._replace_with_tree(p))
            return out
        with mock.patch.object(km, "_subagent_walk_dep_note", note), mock.patch.object(km, "_lstat_or_none", lstat):
            got, rec = self._lookup_recorded()
        self.assertEqual(len(calls), 1, "premise: the note took one identity lstat of the path")
        self.assertEqual(len(swapped), 1, "premise: a tree replaced the link right after that lstat")
        self.assertIsNone(got, "the lookup answers None: the read saw the link")
        self.assertIn(str(p), rec, "a key is recorded for the path (recorded paths %r)" % sorted(rec))
        restat = km._chat_stat_key(str(p))
        self.assertNotEqual(rec[str(p)], restat, "the key recorded for the path differs from its re-stat after a tree "
                            "replaced the link right after the note's identity lstat (recorded %r, re-stat %r)"
                            % (rec[str(p)], restat))
        self.assertEqual(km._subagent_file(self.tpath, AID_GHOST), swapped[0], "the next lookup answers the landed file")

    def test_a_tree_placed_at_a_sibling_path_after_the_notes_identity_lstat_leaves_a_key_the_re_stat_differs_from(self):
        """At a sibling fsid's subagents path. Red with the note's identity lstat taken before its stat key, on the
        recorded key equal to the re-stat (the helper says where the case cannot run)."""
        self._placed_after_the_notes_identity_lstat(Path(self.tpath).parent / SIB / "subagents")

    def test_a_tree_placed_at_the_own_path_after_the_notes_identity_lstat_leaves_a_key_the_re_stat_differs_from(self):
        """At the transcript's own subagents path. Red with the note's identity lstat taken before its stat key, on the
        recorded key equal to the re-stat (the helper says where the case cannot run)."""
        self._placed_after_the_notes_identity_lstat(km._subagents_dir(self.tpath))

    def _tree_appears_after_the_read_of_an_absent_path(self, p):
        """Nothing at `p`, its fsid directory present; a tree holding the agent's file under workflows/wf_1/ is created
        right after the walk's read of `p` returns. The build runs in an open cycle scope under a chat build's record,
        and the later cycle evaluates the tab's trailing signature components over that record (_chat_sig_deps) and
        looks the agent up again. The premises are one read of `p`, answered ((), ()). Then, in this order: the lookup
        answers None; no recorded path but `p` moved (a premise); the tab rebuilds (the later components differ from the
        record's at_build); `p`'s recorded key is present and None, the read's answer; the rebuild's lookup answers the
        landed file. With `p` noted under a _chat_stat_key taken after the read, which answers the tree's own key, the
        later components equal at_build and the rebuild assertion is red."""
        p.parent.mkdir(parents=True, exist_ok=True)
        self.assertFalse(os.path.lexists(str(p)), "premise: nothing at the path")
        self.addCleanup(km._SUBAGENT_TREES.pop, str(p), None)
        real = km._subagent_tree
        made, reads = [], []

        def read_then_create(d):
            out = real(d)
            if str(d) == str(p) and not made:
                reads.append(out)
                landed = p / "workflows" / "wf_1" / ("agent-%s.jsonl" % AID_GHOST)
                landed.parent.mkdir(parents=True)
                landed.write_text("")
                made.append(landed)
            return out
        km._live_scope.subagent_trees = {}               # the cycle whose build shows the file missing
        km._chat_dep_scope.deps = {"task_outs": [], "postal_any": False}
        try:
            with mock.patch.object(km, "_subagent_tree", read_then_create):
                got = km._subagent_file(self.tpath, AID_GHOST)
            deps = km._chat_build_deps(SID2, {"events": []})
        finally:
            km._chat_dep_scope.deps = None
            km._live_scope.subagent_trees = None
        km._live_scope.subagent_trees = {}               # the later cycle: the tab's signature, then its rebuild
        try:
            later = km._chat_sig_deps(SID2, deps)
            again = km._subagent_file(self.tpath, AID_GHOST)
        finally:
            km._live_scope.subagent_trees = None
        rec, now = dict(deps["task_outs"]), dict(later[0])
        restat = km._chat_stat_key(str(p))
        shown = repr(rec[str(p)]) if str(p) in rec else "nothing"
        self.assertEqual(len(made), 1, "premise: the path was read once, then a tree appeared")
        self.assertEqual(reads, [((), ())], "premise: the read found nothing at the path")
        self.assertIsNone(got, "the lookup answers None: the read found nothing")
        self.assertEqual({k: v for k, v in now.items() if k != str(p)}, {k: v for k, v in rec.items() if k != str(p)},
                         "premise: no recorded path but the subagents path moved")
        self.assertNotEqual(later, deps["at_build"], "the tab rebuilds in the cycle after the tree appeared: its "
                            "trailing signature components differ from the build's (recorded for the path %s, its "
                            "re-stat %r)" % (shown, restat))
        self.assertIn(str(p), rec, "a key is recorded for the absent path")
        self.assertIsNone(rec[str(p)], "the absent path is noted None, the read's answer (recorded %s)" % shown)
        self.assertEqual(again, made[0], "the rebuild's lookup answers the landed file")

    def test_an_absent_sibling_path_is_noted_none_from_the_read_so_a_tree_appearing_after_it_rebuilds_the_tab(self):
        """At a sibling fsid's subagents path. Red with an absent path noted under a stat taken after the read, on the
        rebuild assertion (the later components equal at_build). Green at the fork's merge of romp-on/romp PR #1822,
        where the sibling's stat came before its read, so this case guards a regression that merge did not have."""
        self._tree_appears_after_the_read_of_an_absent_path(Path(self.tpath).parent / SIB / "subagents")

    def test_an_absent_own_path_is_noted_none_from_the_read_so_a_tree_appearing_after_it_rebuilds_the_tab(self):
        """At the transcript's own subagents path. Red with an absent path noted under a stat taken after the read, on
        the rebuild assertion (the later components equal at_build). Red at the fork's merge of romp-on/romp PR #1822
        too, but only in a build with no earlier _subagent_meta_map read of the path, as here: in a chat build
        _stamp_agents reads the map on the same path first, which notes the path None, and the build keeps the first
        key it records per path."""
        self._tree_appears_after_the_read_of_an_absent_path(km._subagents_dir(self.tpath))

    def _rebuilds_after_each_swap(self, p):
        """One path `p` holds a live link, then a file, then a dangling link, and after each shape a real tree holding
        the agent's file replaces it before the next cycle. Each shape's cycle builds the tab under a chat build's
        record (the lookup misses and the walk notes `p`); the later cycle evaluates the tab's trailing signature
        components over that record (_chat_sig_deps, the components _chat_build_sig appends after the static ones),
        which must differ from the ones the build embedded (the record's at_build), so the tab rebuilds, and the
        rebuild's lookup answers the landed file. No other recorded path moves across a swap (a premise), so the
        rebuild is `p`'s key. Each shape is its own subtest, so a red names every shape that left the tab stale."""
        self.addCleanup(km._SUBAGENT_TREES.pop, str(p), None)
        for kind in ("link", "file", "dangling"):
            with self.subTest(shape=kind):
                if p.is_symlink() or p.is_file():            # the previous shape's leftover, or its tree, off `p`
                    p.unlink()
                elif p.is_dir():
                    shutil.rmtree(str(p))
                if kind == "dangling" and self.target.exists():
                    shutil.rmtree(str(self.target))          # the link's target, gone: the new link dangles
                self._place(p, kind)
                before = km._chat_stat_key(str(p))
                km._live_scope.subagent_trees = {}           # this shape's cycle: the build that shows the file missing
                km._chat_dep_scope.deps = {"task_outs": [], "postal_any": False}
                try:
                    got = km._subagent_file(self.tpath, AID_GHOST)
                    deps = km._chat_build_deps(SID2, {"events": []})
                finally:
                    km._chat_dep_scope.deps = None
                    km._live_scope.subagent_trees = None
                landed = self._replace_with_tree(p)          # between the cycles: a real tree replaces the shape
                km._live_scope.subagent_trees = {}           # the later cycle: the tab's signature, then its rebuild
                try:
                    later = km._chat_sig_deps(SID2, deps)
                    again = km._subagent_file(self.tpath, AID_GHOST)
                finally:
                    km._live_scope.subagent_trees = None
                rec, now = dict(deps["task_outs"]), dict(later[0])
                restat = km._chat_stat_key(str(p))
                shown = repr(rec[str(p)]) if str(p) in rec else "nothing"
                self.assertIsNone(got, "the lookup through the %s answers None" % kind)
                self.assertEqual({k: v for k, v in now.items() if k != str(p)},
                                 {k: v for k, v in rec.items() if k != str(p)},
                                 "premise: no recorded path but the %s's moved across the swap" % kind)
                self.assertNotEqual(later, deps["at_build"], "the tab rebuilds in the cycle after a tree replaced the "
                                    "%s: its trailing signature components differ from the build's (recorded for the "
                                    "path %s, its re-stat %r)" % (kind, shown, restat))
                self.assertIn(str(p), rec, "a key is recorded for the %s at the path" % kind)
                self.assertEqual(rec[str(p)], before, "the key recorded for the %s is the path's _chat_stat_key before "
                                 "the swap (recorded %s, stat key %r)" % (kind, shown, before))
                self.assertEqual(again, landed, "the rebuild's lookup answers the landed file")

    def test_a_sibling_path_that_is_a_link_then_a_file_then_a_dangling_link_rebuilds_the_tab_after_each_swap(self):
        """The sequence at a sibling fsid's subagents path. Red with the walk's note sent back through
        _subagent_tree_dep_note (the read-keyed note's first form): it records nothing for the link or the file, so no
        recorded key moves when the tree replaces either and the tab stays stale. The dangling link is noted None
        there too, and its swap rebuilds the tab on either form."""
        self._rebuilds_after_each_swap(Path(self.tpath).parent / SIB / "subagents")

    def test_the_own_path_that_is_a_link_then_a_file_then_a_dangling_link_rebuilds_the_tab_after_each_swap(self):
        """The same sequence at the transcript's own subagents path, the walk's other road."""
        self._rebuilds_after_each_swap(km._subagents_dir(self.tpath))


if __name__ == "__main__":
    unittest.main()
