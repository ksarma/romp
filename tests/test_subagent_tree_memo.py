#!/usr/bin/env python3
"""The subagents directory walk memo (2026-09-16): one root-keyed memo of a session's subagents tree, validated by one
lstat per known directory, shared by every reader of the tree.

Before it, _subagent_dirs ran os.walk over the tree on every call (up to ~330 directories and ~3,600 files on the
measured box), and it was called several times per session per build: by _subagent_meta_map from the feed, timeline
and chat builds and the nudge walk, and by _find_agent_file; the feed key alone memoized the walk, for itself. A pusher
stack sample put a tenth of its push-stage samples inside that walk. The memo (_SUBAGENT_TREES) holds, per root, the
directories in walk order and each one's identity (ino, mtime_ns, size, ctime_ns), taken BEFORE its listing; a call
re-takes one lstat per known directory and lists nothing while every identity stands, because a directory entry's
creation, removal or renaming moves its PARENT's mtime and ctime and every parent is a known directory.

Pinned here, red-first on the first: (1) an unchanged tree is not listed on the second call, by _subagent_dirs and by
_subagent_meta_map; (2) a directory added two levels down is seen on the next call, in os.walk's sorted top-down order,
and a sidecar landing in a nested directory reaches the map; (3) a nested directory removed is seen and the hit path
does not raise over its missing stat; (4) a removed root returns [] and forgets its entry, and its absence is noted to a
running chat build as None; (5) a symlinked root is [] and lists nothing, and is noted under the key the chat signature
re-evaluates (None for a missing or dangling root, nothing for a live link, as before the memo); (6) eviction drops a
root no alive session owns and keeps the owned ones: from the jobs pass (_interrupt_block_tick, its home, with no feed
frame built at all), from the helper, and from the tracking-off frame, where a failed alive read evicts nothing; (7)
/perf's memos.subagentTree reports the hits and misses; (8) a tree written within the racy window is re-listed until it
has been quiet; (9) a listing that failed (EMFILE) or a child whose lstat failed (EIO) is never vouched: the next call
re-lists and recovers the whole tree; (10) a root whose own lstat fails for a reason other than absence (an EIO by mock, a
real EACCES from its parent) is a read that did not happen, not an absent tree: nothing is popped, no eviction is
recorded, nothing is noted absent, no counter moves, each reader answers its standing entry unheld or an unreadable
marker, and the next call after the fault clears validates the standing entry; (11) such a fault excludes its own tree
from the agent-file walk and nothing else: a file under a readable sibling's tree is found, memoized and answered with no
fault passed to the caller while the own tree, a sibling sorted before it or an entry whose type cannot be read faults,
and with the file nowhere the lookup answers None with the fault and memoizes nothing. Red-first on (1), the jobs-pass
half of (6), (9), (10) and (11). Synthetic fixtures only: placeholder ids, invented text, a temp directory."""
import contextlib
import errno
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the load (the tests/test_perf_heap_block.py preamble): the kernel resolves its state root at import,
# and only pytest runs conftest's floor. The root minted here is outside conftest's belt, so session hosts are switched off
# in it too (a state root with no `session-hosts` file starts a real host for any session it connects; none is connected
# here, and the file makes that so whatever a later test in this module does).
_ROOT = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = _ROOT
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.makedirs(os.path.join(_ROOT, "romp"), exist_ok=True)
with open(os.path.join(_ROOT, "romp", "session-hosts"), "w") as _fh:
    _fh.write("off")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_subagent_tree_memo", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"       # the placeholder session
SID_B = "11111111-2222-3333-4444-666666666666"     # a second, for ownership
AID = "a1111111111111111"                          # a top-level agent
AID_WF = "a2222222222222222"                       # a workflow agent, one level down
TU, TU_WF = "toolu_tree_0001", "toolu_tree_0002"
AID_FORK = "a3333333333333333"                     # an agent whose file sits under a sibling session's tree (a /clear fork's)
SID_BEFORE = "11111111-2222-3333-4444-000000000001"   # a sibling session sorted before the holder in the project directory
SID_HOLD = "11111111-2222-3333-4444-000000000002"     # the sibling session whose subagents tree holds AID_FORK's file
SID_AFTER = "11111111-2222-3333-4444-000000000003"    # a sibling session sorted after the holder
AGED_NS = 10_000_000_000                           # ten seconds: past the racy window, as tests/test_token_usage.py ages
RACY_NS = km._SUBAGENT_DIR_RACY_NS                 # the real window, reopened by the two tests that pin it


def _age(root):
    """Every directory under `root` stamped ten seconds ago, so the memo may vouch for it (the racy mask never serves a
    directory written within _SUBAGENT_DIR_RACY_NS of the walk)."""
    t = time.time_ns() - AGED_NS
    for r, _ds, _fs in os.walk(root):
        os.utime(r, ns=(t, t))


class _Listings:
    """Counts every directory listing the os module performs (scandir, walk, listdir) inside the block: os.walk binds
    `scandir` from the os module's globals, so patching os.scandir counts its listings too."""

    def __init__(self):
        self.n = 0

    def __enter__(self):
        self._real = {k: getattr(os, k) for k in ("scandir", "walk", "listdir")}

        def wrap(real):
            def f(*a, **k):
                self.n += 1
                return real(*a, **k)
            return f
        for k, real in self._real.items():
            setattr(os, k, wrap(real))
        return self

    def __exit__(self, *exc):
        for k, real in self._real.items():
            setattr(os, k, real)
        return False


class _Tree(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.proj = Path(self.td) / "projects" / "-tmp-notes-api"
        self.proj.mkdir(parents=True)
        self.tpath, self.subdir, self.wf = self._make_tree(SID)
        self.roots = [str(self.subdir)]
        km._SUBAGENT_META_CACHE.clear()
        km._chat_dep_scope.deps = None
        # The fixtures age directories with os.utime, which back-dates mtime but sets ctime to NOW, and nothing can back-date
        # ctime; with the racy mask on both stamps (the adversarial review's finding) an aged fixture could not vouch for two
        # seconds. The served-path tests run with the window closed; the two window tests reopen the real constant (RACY_NS).
        self._racy = mock.patch.object(km, "_SUBAGENT_DIR_RACY_NS", 0)
        self._racy.start()

    def tearDown(self):
        self._racy.stop()
        km._chat_dep_scope.deps = None
        for r in self.roots:
            km._SUBAGENT_TREES.pop(r, None)
        km._SUBAGENT_META_CACHE.clear()
        shutil.rmtree(self.td, ignore_errors=True)

    def _make_tree(self, sid, aged=True):
        """A session's transcript path with a subagents tree beside it: one agent pair at the top, one workflow agent's
        pair under workflows/wf_<id>/; aged past the racy window unless told otherwise."""
        tpath = self.proj / (sid + ".jsonl")
        tpath.write_text("")
        sub = tpath.with_suffix("") / "subagents"
        wf = sub / "workflows" / ("wf_%016x" % (int(sid[-4:], 16)))
        wf.mkdir(parents=True)
        (sub / ("agent-%s.meta.json" % AID)).write_text(json.dumps(
            {"agentType": "general-purpose", "description": "check the api tests", "spawnDepth": 1, "toolUseId": TU}))
        (sub / ("agent-%s.jsonl" % AID)).write_text("")
        (wf / ("agent-%s.meta.json" % AID_WF)).write_text(json.dumps(
            {"agentType": "Workflow", "description": "tidy the readme", "spawnDepth": 1, "toolUseId": TU_WF}))
        (wf / ("agent-%s.jsonl" % AID_WF)).write_text("")
        if aged:
            _age(str(sub))
        if hasattr(self, "roots"):
            self.roots.append(str(sub))
        return tpath, sub, wf

    @staticmethod
    def _reference_walk(d):
        out = []
        for r, ds, _fs in os.walk(d):
            ds.sort()
            out.append(r)
        return out


class ServedWhileStanding(_Tree):
    def test_an_unchanged_tree_is_not_listed_on_the_second_call(self):
        """RED FIRST: before the memo _subagent_dirs ran os.walk on every call (three listings on this tree) and
        _subagent_meta_map walked before consulting its own cache."""
        first = km._subagent_dirs(str(self.subdir))
        self.assertEqual(first, [str(self.subdir), str(self.subdir / "workflows"), str(self.wf)])
        with _Listings() as n:
            self.assertEqual(km._subagent_dirs(str(self.subdir)), first)
        self.assertEqual(n.n, 0, "a standing tree: one lstat per known directory, nothing listed")
        m = km._subagent_meta_map(str(self.tpath))
        self.assertEqual((m[TU]["agentId"], m[TU_WF]["agentId"]), (AID, AID_WF))
        with _Listings() as n:
            self.assertIs(km._subagent_meta_map(str(self.tpath)), m, "an unchanged tree serves the cached map")
        self.assertEqual(n.n, 0, "the map from its cache, its directories from the tree memo: no listing at all")

    def test_a_tree_written_within_the_racy_window_is_relisted_until_quiet(self):
        """The racy mask (git's rule, as _subagent_transcripts applies it): a directory stamped within
        _SUBAGENT_DIR_RACY_NS of the walk is stored with identity None and never serves, so an entry created in the same
        coarse filesystem tick right after its parent was stat'd cannot stay unseen."""
        _tp, sub, _wf = self._make_tree(SID_B, aged=False)
        with mock.patch.object(km, "_SUBAGENT_DIR_RACY_NS", RACY_NS):
            first = km._subagent_dirs(str(sub))
            with _Listings() as n:
                self.assertEqual(km._subagent_dirs(str(sub)), first)
        self.assertGreaterEqual(n.n, 1, "a fresh tree is listed again")
        self.assertIn(None, km._SUBAGENT_TREES[str(sub)][1], "its fresh directories are stored unvouched")


class MovedTrees(_Tree):
    def test_a_directory_added_two_levels_down_is_seen_on_the_next_call(self):
        km._subagent_dirs(str(self.subdir))                         # served once
        new = self.subdir / "workflows" / "wf_00000000000000ee"
        new.mkdir()
        (new / "deeper").mkdir()
        dirs = km._subagent_dirs(str(self.subdir))
        self.assertIn(str(new), dirs)
        self.assertIn(str(new / "deeper"), dirs)
        self.assertEqual(dirs, self._reference_walk(str(self.subdir)), "os.walk's top-down sorted order, on a readable tree")
        # a sidecar landing in a nested directory moves that directory alone, and the map re-reads
        (self.wf / "agent-a3333333333333333.meta.json").write_text(json.dumps({"toolUseId": "toolu_tree_0003", "agentType": "Explore"}))
        self.assertEqual(km._subagent_meta_map(str(self.tpath))["toolu_tree_0003"]["agentId"], "a3333333333333333")

    def test_a_removed_nested_directory_is_seen_and_the_hit_path_does_not_raise(self):
        first = km._subagent_dirs(str(self.subdir))
        self.assertIn(str(self.wf), first)
        self.assertEqual(set(km._subagent_meta_map(str(self.tpath))), {TU, TU_WF})
        shutil.rmtree(self.wf)                                      # the workflow directory goes: its stat is None on the hit path
        dirs = km._subagent_dirs(str(self.subdir))
        self.assertEqual(dirs, [str(self.subdir), str(self.subdir / "workflows")])
        self.assertEqual(set(km._subagent_meta_map(str(self.tpath))), {TU}, "its sidecar left the map with it")
        self.assertIsNone(km._stat_ident(None), "a missing directory's identity is None, a miss against any stored tuple")

    def test_a_removed_root_returns_empty_and_forgets_the_entry(self):
        km._subagent_dirs(str(self.subdir))
        self.assertIn(str(self.subdir), km._SUBAGENT_TREES)
        shutil.rmtree(self.subdir)
        self.assertEqual(km._subagent_dirs(str(self.subdir)), [])
        self.assertNotIn(str(self.subdir), km._SUBAGENT_TREES, "a removed root: [] and forgotten")
        deps = {"task_outs": []}
        km._chat_dep_scope.deps = deps                              # a running chat build's dependency record
        try:
            self.assertEqual(km._subagent_meta_map(str(self.tpath)), {})
        finally:
            km._chat_dep_scope.deps = None
        self.assertEqual(deps["task_outs"], [(str(self.subdir), None)], "the absence is a dependency, as before")
        self.assertEqual(km._subagent_dirs_ident(SID, str(self.subdir)), ((str(self.subdir),), (None,)),
                         "the feed key's component for a missing root: the tree (d,) with identity None")
        # the root comes back: listed again on the next call
        self.subdir.mkdir()
        (self.subdir / ("agent-%s.meta.json" % AID)).write_text(json.dumps({"toolUseId": TU, "agentType": "x"}))
        self.assertEqual(km._subagent_dirs(str(self.subdir)), [str(self.subdir)])
        self.assertEqual(set(km._subagent_meta_map(str(self.tpath))), {TU})

    def test_a_symlinked_root_is_empty_lists_nothing_and_is_noted_under_the_key_the_signature_re_stats(self):
        outside = Path(self.td) / "elsewhere" / "subagents"
        outside.mkdir(parents=True)
        (outside / ("agent-%s.meta.json" % AID)).write_text(json.dumps({"toolUseId": TU, "agentType": "x"}))
        km._subagent_dirs(str(self.subdir))                         # the real tree, memoized
        shutil.rmtree(self.subdir)
        os.symlink(str(outside), str(self.subdir))                  # a live link in its place: not this session's tree
        self.assertEqual(km._subagent_dirs(str(self.subdir)), [])
        self.assertNotIn(str(self.subdir), km._SUBAGENT_TREES, "a root that is not a directory holds no entry")
        with _Listings() as n:
            self.assertEqual(km._subagent_dirs(str(self.subdir)), [])
            self.assertEqual(km._subagent_meta_map(str(self.tpath)), {})
        self.assertEqual(n.n, 0, "one lstat, nothing listed")
        # The chat build's dependency record for a LIVE link: no note, as before the memo (os.stat succeeded on it and only
        # its failure noted). A None note would mismatch _chat_sig_deps' re-stat (the target's (mtime, size)) every cycle and
        # rebuild the tab for good; the target's key would rebuild it on changes the map ({} regardless) never shows.
        deps = {"task_outs": []}
        km._chat_dep_scope.deps = deps
        try:
            km._subagent_meta_map(str(self.tpath))
        finally:
            km._chat_dep_scope.deps = None
        self.assertEqual(deps["task_outs"], [], "a live link records no dependency, as before")
        dirs, idents = km._subagent_dirs_ident(SID, str(self.subdir))
        self.assertEqual(dirs, (str(self.subdir),))
        self.assertEqual(len(idents), 1)
        self.assertIsNotNone(idents[0], "the feed key folds the link's own lstat identity")
        self.assertEqual(idents[0][0], os.lstat(str(self.subdir)).st_ino, "the link's inode, not the target's")
        # a DANGLING link notes None, as a missing root does (today's os.stat failure recorded the same note)
        os.unlink(str(self.subdir))
        os.symlink(str(Path(self.td) / "nowhere"), str(self.subdir))
        deps = {"task_outs": []}
        km._chat_dep_scope.deps = deps
        try:
            self.assertEqual(km._subagent_meta_map(str(self.tpath)), {})
        finally:
            km._chat_dep_scope.deps = None
        self.assertEqual(deps["task_outs"], [(str(self.subdir), None)])


class TransientFailures(_Tree):
    def test_a_failed_listing_is_not_vouched_and_the_next_call_relists_the_whole_tree(self):
        """RED FIRST against the memo's first cut, which stored a truncated list under vouched identities after a transient
        scandir failure and served it as a hit until an entry landed in that directory."""
        real_scandir, failed = os.scandir, []

        def flaky(p, *a, **k):
            if str(p) == str(self.subdir / "workflows") and not failed:
                failed.append(p)
                raise OSError(errno.EMFILE, "too many open files")
            return real_scandir(p, *a, **k)
        with mock.patch.object(os, "scandir", flaky):
            first = km._subagent_dirs(str(self.subdir))
        self.assertEqual(first, [str(self.subdir), str(self.subdir / "workflows")], "the failed listing truncates this call, as os.walk did")
        self.assertIsNone(km._SUBAGENT_TREES[str(self.subdir)][1][1], "the directory whose listing failed is stored unvouched")
        with _Listings() as n:
            second = km._subagent_dirs(str(self.subdir))
        self.assertGreaterEqual(n.n, 1, "the next call re-lists")
        self.assertEqual(second, self._reference_walk(str(self.subdir)), "...and recovers the whole tree in os.walk's order")
        self.assertEqual(set(km._subagent_meta_map(str(self.tpath))), {TU, TU_WF}, "the nested sidecar is seen")
        with _Listings() as n:
            km._subagent_dirs(str(self.subdir))
        self.assertEqual(n.n, 0, "a clean listing is vouched: served from here")
        # a child's lstat failing (EIO) likewise leaves its parent unvouched
        km._SUBAGENT_TREES.pop(str(self.subdir), None)
        real_lstat, failed = os.lstat, []

        def flaky_lstat(p, *a, **k):
            if str(p) == str(self.wf) and not failed:
                failed.append(p)
                raise OSError(errno.EIO, "input/output error")
            return real_lstat(p, *a, **k)
        with mock.patch.object(os, "lstat", flaky_lstat):
            first = km._subagent_dirs(str(self.subdir))
        self.assertNotIn(str(self.wf), first)
        self.assertIsNone(km._SUBAGENT_TREES[str(self.subdir)][1][1], "the parent whose child could not be stat'd is unvouched")
        self.assertEqual(km._subagent_dirs(str(self.subdir)), self._reference_walk(str(self.subdir)))

    def test_an_unvouched_entry_never_validates_so_a_directory_vanishing_mid_check_is_a_miss_not_a_hit_with_a_hole(self):
        """RED FIRST against the fold's first cut, which validated an entry carrying an unvouched directory: that directory,
        removed between its parent's lstat and its own, matched the stored None and the tree was served as a hit with a None
        among the stats, which the meta map indexes (AttributeError, one build dropped). Such an entry re-walks instead."""
        real_scandir, failed = os.scandir, []

        def flaky(p, *a, **k):
            if str(p) == str(self.subdir / "workflows") and not failed:
                failed.append(p)
                raise OSError(errno.EMFILE, "too many open files")
            return real_scandir(p, *a, **k)
        with mock.patch.object(os, "scandir", flaky):
            km._subagent_dirs(str(self.subdir))
        self.assertIsNone(km._SUBAGENT_TREES[str(self.subdir)][1][1], "the workflows directory is stored unvouched")
        real_lstat, gone = os.lstat, []

        def vanishing(p, *a, **k):
            # the race, made deterministic: the unvouched directory goes the instant the check reaches it, after its parent's stat
            if str(p) == str(self.subdir / "workflows") and not gone:
                gone.append(p)
                shutil.rmtree(self.subdir / "workflows")
            return real_lstat(p, *a, **k)
        before = dict(km._SUBAGENT_TREE_STATS)
        with mock.patch.object(os, "lstat", vanishing):
            meta = km._subagent_meta_map(str(self.tpath))     # must not raise on a None among the stats
        self.assertEqual(set(meta), {TU}, "the top-level sidecar alone: the nested one went with its directory")
        self.assertEqual(km._SUBAGENT_TREE_STATS["hit"], before["hit"], "an entry with an unvouched directory is never served as a hit")
        self.assertEqual(km._subagent_dirs(str(self.subdir)), self._reference_walk(str(self.subdir)), "the re-walk sees the tree as it is")

    def test_the_racy_mask_covers_the_ctime_stamp_too(self):
        """A directory whose ctime alone is within the window (a chmod, a utime) is stored unvouched: the ctime component is
        the one that catches a back-dated mtime, and a ctime inside the racy tick could be equalled by a later change."""
        km._subagent_dirs(str(self.subdir))                     # vouched under the closed window (setUp)
        t = time.time_ns() - AGED_NS
        os.utime(str(self.wf), ns=(t, t))                       # mtime stays aged; ctime moves to now
        with mock.patch.object(km, "_SUBAGENT_DIR_RACY_NS", RACY_NS):
            dirs = km._subagent_dirs(str(self.subdir))
        idents = km._SUBAGENT_TREES[str(self.subdir)][1]
        self.assertTrue(all(os.lstat(d).st_mtime_ns < time.time_ns() - RACY_NS for d in dirs), "every mtime is aged: mtime alone would have vouched")
        self.assertTrue(all(i is None for i in idents), "ctime within the window: unvouched, all of them (setUp's aging set their ctime too)")


class Ownership(_Tree):
    def test_the_jobs_pass_evicts_a_root_no_alive_session_owns_with_no_feed_frame_built(self):
        """RED FIRST against the memo's first cut, whose bound rode the feed frame alone: a headless or timeline-only kernel
        (no feed audience) inserted roots from the jobs thread and the chat and timeline builds and never evicted one.
        _interrupt_block_tick holds the cycle's alive rows every jobs pass, whether or not a client is connected."""
        tpath_b, sub_b, _wf = self._make_tree(SID_B)
        km._subagent_meta_map(str(self.tpath))                  # inserted by a reader, no feed frame built
        km._subagent_meta_map(str(tpath_b))
        self.assertLessEqual({str(self.subdir), str(sub_b)}, set(km._SUBAGENT_TREES))
        rows = [{"sid": SID, "name": "web", "anchor": SID, "path": str(self.tpath), "mtime": 0.0}]
        # the tick's per-row body is skipped through the hideFromFeed flag (its own early return); the pass's forgets run after
        # the loop regardless, which is what this pins
        with mock.patch.object(km, "_alive_sessions", lambda now, live_map: rows), \
                mock.patch.object(km, "_session_flag", lambda sid, flag: flag == "hideFromFeed"):
            km._interrupt_block_tick(time.time(), {SID: {"state": "idle"}})
        self.assertIn(str(self.subdir), km._SUBAGENT_TREES, "the alive session's root stays")
        self.assertNotIn(str(sub_b), km._SUBAGENT_TREES, "the departed session's root left on the jobs pass")

    def test_eviction_drops_a_root_no_alive_session_owns_and_keeps_owned_ones(self):
        tpath_b, sub_b, _wf = self._make_tree(SID_B)
        km._subagent_dirs(str(self.subdir))
        km._subagent_dirs(str(sub_b))
        self.assertLessEqual({str(self.subdir), str(sub_b)}, set(km._SUBAGENT_TREES))
        before = km._SUBAGENT_TREE_STATS["evict"]
        km._subagent_trees_forget([{"sid": SID, "path": str(self.tpath)}, {"sid": "no-path"}])
        self.assertIn(str(self.subdir), km._SUBAGENT_TREES, "an alive session's root stays")
        self.assertNotIn(str(sub_b), km._SUBAGENT_TREES, "a root nobody alive owns leaves")
        self.assertEqual(km._SUBAGENT_TREE_STATS["evict"] - before, 1)
        with _Listings() as n:
            self.assertEqual(len(km._subagent_dirs(str(sub_b))), 3)
        self.assertGreaterEqual(n.n, 1, "walked again on the next ask, then served")
        with _Listings() as n:
            km._subagent_dirs(str(sub_b))
        self.assertEqual(n.n, 0)

    def test_the_tracking_off_frame_evicts_a_departed_root_and_keeps_a_live_one(self):
        """With Task tracking off build_feed never runs, so the bound rides the off frame too; a FAILED alive read evicts
        nothing, since an empty set from a failure is not an owner list."""
        _tpath_b, sub_b, _wf = self._make_tree(SID_B)
        km._subagent_dirs(str(self.subdir))
        km._subagent_dirs(str(sub_b))
        rows = [{"sid": SID, "name": "web", "anchor": SID, "path": str(self.tpath), "mtime": 0.0}]
        with mock.patch.object(km, "_alive_sessions", lambda now, live_map: rows):
            f = km._feed_off_frame(time.time(), {SID: {}})
        self.assertTrue(f["off"])
        self.assertIn(str(self.subdir), km._SUBAGENT_TREES)
        self.assertNotIn(str(sub_b), km._SUBAGENT_TREES, "the departed session's root left with the off frame")
        km._subagent_dirs(str(sub_b))
        with mock.patch.object(km, "_alive_sessions", side_effect=RuntimeError("registry unreadable")):
            f = km._feed_off_frame(time.time(), {SID: {}})
        self.assertTrue(f["off"])
        self.assertLessEqual({str(self.subdir), str(sub_b)}, set(km._SUBAGENT_TREES), "a failed read evicts nothing")


class Reported(_Tree):
    def test_the_perf_block_reports_hits_and_misses(self):
        base = dict(km._SUBAGENT_TREE_STATS)
        km._subagent_dirs(str(self.subdir))                         # a miss: the walk
        km._subagent_dirs(str(self.subdir))                         # a hit: one lstat per known directory
        rep = km._PERF_STATS.snapshot()["memos"]["subagentTree"]
        self.assertEqual(set(rep), {"hit", "miss", "served", "evict", "dirStats", "walkMs", "validateMs", "roots", "dirs"},
                         "the report's keys; served (reads a cycle scope answered from its held pair) since 2026-09-21 (round 1 of "
                         "#882's fresh-3 asked for the absorbed reads to be counted), its moving edge pinned in "
                         "tests/test_subagent_tree_stamps_per_cycle.py")
        self.assertEqual((rep["miss"] - base["miss"], rep["hit"] - base["hit"]), (1, 1))
        self.assertGreaterEqual(rep["dirStats"] - base["dirStats"], 2, "the hit paid a stat per directory beyond the root")
        self.assertGreaterEqual(rep["roots"], 1)
        self.assertGreaterEqual(rep["dirs"], 3)
        self.assertGreaterEqual(rep["walkMs"], 0.0)
        self.assertGreaterEqual(rep["validateMs"], 0.0)
        self.assertEqual(rep, km._subagent_tree_memo_report())
        json.dumps(rep)
        (self.wf / "wf_inner").mkdir()                              # the tree moved: the call validates, mismatches and walks
        km._subagent_dirs(str(self.subdir))
        after = km._subagent_tree_memo_report()
        self.assertEqual((after["miss"] - rep["miss"], after["hit"] - rep["hit"]), (1, 0))
        self.assertGreaterEqual(after["walkMs"], rep["walkMs"])
        self.assertGreaterEqual(after["validateMs"], rep["validateMs"])


class UnreadableRoot(_Tree):
    """A root whose own lstat fails for a reason other than absence (EACCES from a parent without search permission, EIO)
    is a read that did not happen, not an absent tree: nothing is popped, no eviction is recorded, nothing is noted absent,
    no counter moves, each reader answers its standing entry unheld, and the next call after the fault clears reads the
    disk again and finds the entry standing (a validation, never a walk). RED FIRST: until 2026-09-21 the root's
    `except OSError` took every errno for absence, so an EIO popped the entry, moved the generation, answered (), () and
    noted the tree absent to the chat build, which showed no subagents until the fault cleared; the module's own cases
    drove only ENOENT there. Two faults: an EIO by mock on os.lstat of the root alone (every other path reads) and a REAL
    EACCES from the parent directory without search permission (nothing under it reads either; skipped as root, whom
    permission bits do not bind). The scope is open under the fault, so "nothing held" is executed, not implied, and it is
    the WHOLE scope that is compared, its three maps (trees, stamps, launches) each empty after the tree reads: a pin over
    one map is narrower than "no scope entry", and a stamps entry recorded on the raise left the trees-only pin green (the
    owner's pass before round 2 of #882, its fixes-by-execution lens). After the agent-file lookup under the real EACCES
    the whole scope is compared again, by equality, to the one entry the walk holds: the project directory's stamp, since
    a fault excludes its own tree from the walk and nothing else, so the walk goes on to list the project directory (round
    2 of #882, group A; FaultExcludesItsOwnTree below executes the exclusion)."""

    EMPTY = {"trees": {}, "stamps": {}, "launches": {}}   # the scope as _subagent_scope_open mints it: nothing held in any of its three maps

    def _standing(self):
        """The memo entry and the cached sidecar map, standing before the fault; the workflow agent's resolution cold."""
        root = str(self.subdir)
        km._subagent_dirs(root)
        m = km._subagent_meta_map(str(self.tpath))
        self.assertEqual(set(m), {TU, TU_WF})
        self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, (str(self.tpath), AID_WF), None)
        km._SUBAGENT_FILE_CACHE.pop((str(self.tpath), AID_WF), None)
        return root, km._SUBAGENT_TREES[root], m

    def _open_scope(self):
        """A cycle's scope, opened after every pre-fault read so nothing is held: the fault must be observed by the lstat, not
        served from a hold (a served read never reaches the disk); what the fault must leave empty."""
        km._subagent_scope_open()
        self.addCleanup(km._subagent_scope_close)
        self.assertEqual(km._subagent_scope(), self.EMPTY,
                         "premise: nothing held before the fault, in any of the scope's three maps (trees, stamps, launches)")

    def _fault_holds(self, root, entry, m, errno_expected):
        """Under the fault: the sidecar map first (the reader the chat build asks), then the memo, the feed key, the lookup."""
        g0, evicted, before = km._SUBAGENT_TREES_GEN[0], dict(km._SUBAGENT_ROOT_EVICTED), dict(km._SUBAGENT_TREE_STATS)
        deps = {"task_outs": [], "postal_any": False}
        km._chat_dep_scope.deps = deps
        try:
            meta = km._subagent_meta_map(str(self.tpath))
        finally:
            km._chat_dep_scope.deps = None
        self.assertIn(root, km._SUBAGENT_TREES, "the entry stands: a read that did not happen pops nothing")
        self.assertIs(km._SUBAGENT_TREES[root], entry, "the same entry, untouched")
        self.assertEqual(km._SUBAGENT_TREES_GEN[0], g0, "no eviction is recorded: the generation did not move")
        self.assertEqual(km._SUBAGENT_ROOT_EVICTED, evicted, "and no root gained an eviction record")
        self.assertNotIn((root, None), deps["task_outs"], "the tree is not noted absent to the chat build")
        self.assertEqual(deps["task_outs"], [(root, km._TREE_UNREADABLE)],
                         "it is noted unreadable, under a key no stat equals, so the tab is rebuilt next cycle and reads again")
        self.assertIs(meta, m, "the standing map is answered, unheld (its cache entry neither popped nor re-keyed)")
        self.assertEqual({k: km._SUBAGENT_TREE_STATS[k] - before[k] for k in ("hit", "miss", "served", "evict", "dirStats")},
                         {"hit": 0, "miss": 0, "served": 0, "evict": 0, "dirStats": 0}, "no counter moves: the read answered no tree")
        self.assertEqual(km._subagent_scope(), self.EMPTY,
                         "nothing is held in the cycle scope, in any of its three maps (trees, stamps, launches): the fail-closed read "
                         "records no scope entry, so the next call retries (keyed on the whole scope by equality; a pin over the trees "
                         "map alone stayed green with a stamps entry recorded on the raise)")
        with self.assertRaises(km._SubagentTreeUnreadable) as cm:
            km._subagent_tree(root)
        self.assertEqual(cm.exception.error.errno, errno_expected, "the raise carries the lstat's own error")
        self.assertIs(cm.exception.entry, entry, "and the standing entry")
        with self.assertRaises(km._SubagentTreeUnreadable):
            km._subagent_dirs(root)                             # never [], which is absence
        self.assertIs(km._subagent_dirs_ident(SID, root), entry,
                      "the feed key's component is the standing entry, not the missing root's (d,), (None,)")
        self.assertEqual(km._subagent_scope(), self.EMPTY,
                         "still nothing held after the direct reads, in any of the three maps (trees, stamps, launches)")

    def _fold_has_the_calls_lifetime(self):
        """The awaiting fold over a resolution that could not be made is held for the call alone, never the cycle."""
        row = km._awaiting_item("agents", TU_WF, "Workflow", None, agent_id=AID_WF)
        cmd = km._awaiting_item("commands", "toolu_tree_cmd1", "run the api tests", None)
        agents, commands = km._awaiting_nest([row], [cmd], {}, str(self.tpath))
        self.assertEqual((len(agents), len(commands)), (1, 1), "nothing attributed this call")
        self.assertEqual(km._subagent_scope()["launches"], {},
                         "the fold of a resolution that could not be made is held for the call alone, not the cycle")
        return row, cmd

    def _the_next_call_reads_again(self, root, m, row, cmd):
        """After the fault clears: a validation of the standing entry (nothing listed), the standing map, the lookup made."""
        before = dict(km._SUBAGENT_TREE_STATS)
        with _Listings() as n:
            dirs = km._subagent_dirs(root)
        self.assertEqual(dirs, self._reference_walk(root), "the next call reads the disk again")
        self.assertEqual(n.n, 0, "as a validation of the standing entry, nothing listed: the entry was never popped")
        self.assertEqual((km._SUBAGENT_TREE_STATS["hit"] - before["hit"], km._SUBAGENT_TREE_STATS["miss"] - before["miss"]), (1, 0),
                         "one validation, no walk")
        self.assertIs(km._subagent_meta_map(str(self.tpath)), m, "the map's cache stood too")
        wf_file = self.wf / ("agent-%s.jsonl" % AID_WF)
        self.assertEqual(km._subagent_file(str(self.tpath), AID_WF), wf_file, "the lookup is made")
        self.assertEqual(km._SUBAGENT_FILE_CACHE[(str(self.tpath), AID_WF)][1], wf_file, "and memoized now that it was")
        km._awaiting_nest([row], [cmd], {}, str(self.tpath))
        self.assertIn((str(self.tpath), AID_WF), km._subagent_scope()["launches"],
                      "the next call in the cycle resolves the file and holds its fold")

    def test_an_eio_on_the_roots_own_lstat_pops_records_and_notes_nothing_and_the_next_call_reads_the_disk_again(self):
        root, entry, m = self._standing()
        real = os.lstat

        def eio(p, *a, **k):
            if str(p) == root:
                raise OSError(errno.EIO, "input/output error")
            return real(p, *a, **k)
        self._open_scope()
        with mock.patch.object(os, "lstat", eio):
            self._fault_holds(root, entry, m, errno.EIO)
            faults = []
            self.assertIsNone(km._subagent_file(str(self.tpath), AID_WF, faults),
                              "the nested agent's lookup needs the tree: with no standing resolution, nothing is known")
            self.assertEqual(faults, ["OSError"], "and the caller is told the lookup could not be made")
            self.assertNotIn((str(self.tpath), AID_WF), km._SUBAGENT_FILE_CACHE, "a lookup that could not be made memoizes no miss")
            row, cmd = self._fold_has_the_calls_lifetime()
        self._the_next_call_reads_again(root, m, row, cmd)

    def test_a_real_eacces_at_the_root_from_a_parent_without_search_permission_is_not_absence(self):
        if os.geteuid() == 0:
            self.skipTest("permission bits do not bind root: no EACCES to drive")
        root, entry, m = self._standing()
        wf_file = self.wf / ("agent-%s.jsonl" % AID_WF)
        self.assertEqual(km._subagent_file(str(self.tpath), AID_WF), wf_file)   # a standing resolution this time
        standing = km._SUBAGENT_FILE_CACHE[(str(self.tpath), AID_WF)]
        self._open_scope()
        parent = self.subdir.parent
        self.addCleanup(lambda: os.path.isdir(parent) and os.chmod(parent, 0o755))   # a belt: tearDown removes the tree first
        os.chmod(parent, 0o000)
        try:
            with self.assertRaises(PermissionError) as cm:
                os.lstat(root)
            self.assertEqual(cm.exception.errno, errno.EACCES, "the real fault this case drives")
            self._fault_holds(root, entry, m, errno.EACCES)
            g, proj = km._SUBAGENT_TREES_GEN[0], str(self.proj)
            faults = []
            self.assertEqual(km._subagent_file(str(self.tpath), AID_WF, faults), wf_file,
                             "the standing resolution is answered, unheld")
            self.assertEqual(faults, ["PermissionError"], "and the caller is told the lookup could not be made")
            self.assertIs(km._SUBAGENT_FILE_CACHE[(str(self.tpath), AID_WF)], standing, "its memo entry is untouched")
            row, cmd = self._fold_has_the_calls_lifetime()
            self.assertEqual(km._subagent_scope(),
                             {"trees": {}, "stamps": {proj: ((proj, os.stat(proj).st_mtime_ns), None, g)}, "launches": {}},
                             "at the fault's end the scope holds the project directory's stamp and nothing else, compared whole: the "
                             "agent-file walk excludes the own tree it could not read and goes on to list the project directory, "
                             "whose stamp it takes as an own stat (round 2 of #882, group A); under the parent at mode 000 every "
                             "stat of the lookup's re-check fails, and a stat that raises is never held")
        finally:
            os.chmod(parent, 0o755)
        self._the_next_call_reads_again(root, m, row, cmd)


class FaultExcludesItsOwnTree(_Tree):
    """A fault excludes the tree that raised it and nothing else (round 2 of #882, group A: correctness-1, regression-1,
    extra5-1). An agent's file under a readable sibling session's tree (a /clear fork's fsid) is found, memoized and answered
    with no fault passed to the caller while another tree the walk looks through cannot be read: the own subagents tree, a
    sibling's sorted before the holder, or a project-directory entry sorted before the holder whose type cannot be read
    (pathlib's is_dir raising). RED FIRST: from the fail-closed change of 2026-09-21 until this one the agent-file walk
    answered through _subagent_walk_unreadable at the first such tree, before it looked through the trees sorted after it,
    so the lookup answered None with the fault and memoized nothing (the viewer said the transcript was missing, the
    awaiting box attributed no launches, the Agent card showed no steps) for as long as the unrelated tree stayed
    unreadable, where the walk before the fail-closed change found and memoized the file; and _subagent_file's gate
    discarded a found file whenever any fault occurred, so a fix to the walk alone did not reach the caller. Each road is
    driven under a real EACCES (a directory at mode 000; skipped as root, whom permission bits do not bind) and under an EIO
    by mock. The is_dir road exists where pathlib's is_dir re-raises an errno other than ENOENT, ENOTDIR, EBADF and ELOOP,
    which is through 3.12, the kernel's interpreter; from 3.13 is_dir is os.path.isdir, which answers False on any OSError,
    and on 3.10 pathlib stats through the os.stat it bound at import, so the EIO mock is not seen there: each is_dir case
    asserts its interpreter's behaviour first, and where is_dir does not raise the entry is skipped at both heads. Two
    controls hold at both heads: an unreadable sibling sorted after the holder is never reached, and with the file nowhere
    (no holder) the lookup answers None with the fault, memoizes nothing and tells the running chat build the tree is
    unreadable, on every call while the fault lasts: the fail-closed rule's cost, which _subagent_tree's docstring states
    with the no-holder cases as its witness."""

    def setUp(self):
        super().setUp()
        self.fork_key = (str(self.tpath), AID_FORK)
        km._SUBAGENT_FILE_CACHE.pop(self.fork_key, None)
        self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, self.fork_key, None)

    def _sibling(self, sid, holder=False):
        """A sibling session's subagents tree in the project directory, aged, with AID_FORK's file at its top when `holder`:
        (the root, the agent file or None)."""
        sub = self.proj / sid / "subagents"
        (sub / "workflows").mkdir(parents=True)
        f = None
        if holder:
            f = sub / ("agent-%s.jsonl" % AID_FORK)
            f.write_text("")
        _age(str(self.proj / sid))
        self.roots.append(str(sub))
        return str(sub), f

    def _premise_order(self, first, second):
        names = [p.name for p in sorted(self.proj.iterdir())]      # the walk's own order (sorted(parent.iterdir()))
        self.assertLess(names.index(first), names.index(second), "premise: the walk lists %s before %s" % (first, second))

    @contextlib.contextmanager
    def _unreadable(self, root, how):
        """The subagents root `root` cannot be read inside the block. "eacces": its session directory at mode 000, a real
        fault, so every stat under that directory fails too (restored before the block exits, so tearDown can remove it);
        "eio": os.lstat of the root alone raising EIO by mock, every other call reading."""
        if how == "eacces":
            if os.geteuid() == 0:
                self.skipTest("permission bits do not bind root: no EACCES to drive")
            parent = os.path.dirname(root)
            os.chmod(parent, 0o000)
            try:
                with self.assertRaises(PermissionError, msg="premise: the real fault this case drives"):
                    os.lstat(root)
                yield
            finally:
                os.chmod(parent, 0o755)
            return
        real = os.lstat

        def eio(p, *a, **k):
            if str(p) == root:
                raise OSError(errno.EIO, "input/output error")
            return real(p, *a, **k)
        with mock.patch.object(os, "lstat", eio):
            yield

    @contextlib.contextmanager
    def _untyped_entry(self, how):
        """A project-directory entry sorted before the holder whose type cannot be read, yielded. "eacces": a symlink into a
        directory at mode 000 (a real fault: the stat through the link fails with EACCES); "eio": a sibling session's
        directory whose os.stat raises EIO by mock, every other call reading."""
        entry = self.proj / SID_BEFORE
        if how == "eacces":
            if os.geteuid() == 0:
                self.skipTest("permission bits do not bind root: no EACCES to drive")
            locked = Path(self.td) / "locked"
            (locked / "tree" / "subagents").mkdir(parents=True)
            entry.symlink_to(locked / "tree")
            os.chmod(locked, 0o000)
            try:
                yield entry
            finally:
                os.chmod(locked, 0o755)
            return
        self._sibling(SID_BEFORE)
        real = os.stat

        def eio(p, *a, **k):
            if str(p) == str(entry):
                raise OSError(errno.EIO, "input/output error")
            return real(p, *a, **k)
        with mock.patch.object(os, "stat", eio):
            yield entry

    def _is_dir_premise(self, entry, how):
        """This interpreter's is_dir on the entry under the fault: it raises through 3.12 (from 3.13 it is os.path.isdir,
        which answers False on any OSError), except that on 3.10 the EIO mock is not seen (pathlib bound os.stat at import,
        and the entry is a readable directory)."""
        try:
            entry.is_dir()
            raised = False
        except OSError:
            raised = True
        expect = sys.version_info < (3, 13) and (how == "eacces" or sys.version_info >= (3, 11))
        self.assertEqual(raised, expect, "premise: Path.is_dir %s on this interpreter under the %s fault"
                         % ("raises" if expect else "does not raise", how))

    def _lookup(self):
        """AID_FORK's lookup under a running chat build's dependency scope: (answer, the caller's faults, the build's notes)."""
        faults, deps = [], {"task_outs": [], "postal_any": False}
        km._chat_dep_scope.deps = deps
        try:
            got = km._subagent_file(str(self.tpath), AID_FORK, faults)
        finally:
            km._chat_dep_scope.deps = None
        return got, faults, deps["task_outs"]

    def _found(self, got, faults, notes, holder_file, why):
        self.assertEqual(got, holder_file, why)
        self.assertEqual(faults, [], "the lookup was made: the caller (_awaiting_nest) is told of no fault when a file was found")
        self.assertEqual(km._SUBAGENT_FILE_CACHE[self.fork_key][1], holder_file, "and the found file is memoized")
        self.assertNotIn(km._TREE_UNREADABLE, [k for _p, k in notes],
                         "the running chat build is told of no unreadable tree when the file was found: the answer is the file, "
                         "recorded when it is read, and the tab is not rebuilt every cycle for a tree the answer did not need")

    def _skipped_then_walked_again(self, root, holder_file):
        """Under a real EACCES the found file's memo stamps carry the skipped tree's (root, None), so the first lookup after
        the fault clears walks again (the root's stamp reads now) and still finds the file. Call after the fault's block."""
        self.assertEqual(km._subagent_file(str(self.tpath), AID_FORK), holder_file, "found again once the tree reads")
        self.assertIn((root, os.stat(root).st_mtime_ns), km._SUBAGENT_FILE_CACHE[self.fork_key][0],
                      "the lookup after the fault cleared walked again: the memo now carries the skipped root's stamp as read")

    FOUND_PAST = ("a fault excludes its own tree and nothing else: the file under the readable sibling is found past the tree "
                  "that could not be read (the walk used to answer None at the first tree it could not read)")

    # ── the unreadable own tree, the file under a readable sibling ─────────────────────────────────────────────────────
    def _own_tree_unreadable(self, how):
        root = str(self.subdir)
        _hold, holder_file = self._sibling(SID_HOLD, holder=True)
        with self._unreadable(root, how):
            got, faults, notes = self._lookup()
            self._found(got, faults, notes, holder_file, self.FOUND_PAST)
            if how == "eacces":
                self.assertIn((root, None), km._SUBAGENT_FILE_CACHE[self.fork_key][0],
                              "the memo's stamps carry the skipped own tree's root unread, so the memo walks again once it reads")
        if how == "eacces":
            self._skipped_then_walked_again(root, holder_file)

    def test_an_unreadable_own_tree_eio_leaves_the_file_under_a_readable_sibling_found_and_memoized(self):
        self._own_tree_unreadable("eio")

    def test_an_unreadable_own_tree_eacces_leaves_the_file_under_a_readable_sibling_found_and_memoized(self):
        self._own_tree_unreadable("eacces")

    # ── an unreadable sibling sorted before the holder ───────────────────────────────────────────────────────────────
    def _sibling_before_holder_unreadable(self, how):
        before, _ = self._sibling(SID_BEFORE)
        _hold, holder_file = self._sibling(SID_HOLD, holder=True)
        self._premise_order(SID_BEFORE, SID_HOLD)
        with self._unreadable(before, how):
            got, faults, notes = self._lookup()
            self._found(got, faults, notes, holder_file, self.FOUND_PAST)
            if how == "eacces":
                self.assertIn((before, None), km._SUBAGENT_FILE_CACHE[self.fork_key][0],
                              "the memo's stamps carry the skipped sibling's root unread, so the memo walks again once it reads")
            # The caller: _awaiting_nest's fold, whose own lookup walks under the fault, is held for the cycle, since
            # _subagent_file passes it no fault when a file was found (a fault holds the fold for the one call).
            km._SUBAGENT_FILE_CACHE.pop(self.fork_key, None)
            km._subagent_scope_open()
            try:
                row = km._awaiting_item("agents", "toolu_tree_0003", "Workflow", None, agent_id=AID_FORK)
                cmd = km._awaiting_item("commands", "toolu_tree_cmd2", "run the api tests", None)
                km._awaiting_nest([row], [cmd], {}, str(self.tpath))
                self.assertIn(self.fork_key, km._subagent_scope()["launches"],
                              "the fold over the found file is held for the cycle: no fault reached _awaiting_nest")
            finally:
                km._subagent_scope_close()
        if how == "eacces":
            self._skipped_then_walked_again(before, holder_file)

    def test_an_unreadable_sibling_sorted_before_the_holder_eio_leaves_its_file_found_memoized_and_the_fold_held(self):
        self._sibling_before_holder_unreadable("eio")

    def test_an_unreadable_sibling_sorted_before_the_holder_eacces_leaves_its_file_found_memoized_and_the_fold_held(self):
        self._sibling_before_holder_unreadable("eacces")

    # ── a project-directory entry sorted before the holder whose type cannot be read ──────────────────────────────────
    def _untyped_entry_before_holder(self, how):
        _hold, holder_file = self._sibling(SID_HOLD, holder=True)
        with self._untyped_entry(how) as entry:
            self._premise_order(SID_BEFORE, SID_HOLD)
            self._is_dir_premise(entry, how)
            got, faults, notes = self._lookup()
            self._found(got, faults, notes, holder_file,
                        "a fault excludes its own entry and nothing else: an entry whose type could not be read is skipped and "
                        "the file under the readable sibling after it is found (the walk used to take the raise for the "
                        "listing's fault and answer None)")

    def test_an_entry_whose_type_cannot_be_read_sorted_before_the_holder_eio_leaves_its_file_found_and_memoized(self):
        self._untyped_entry_before_holder("eio")

    def test_an_entry_whose_type_cannot_be_read_sorted_before_the_holder_eacces_leaves_its_file_found_and_memoized(self):
        self._untyped_entry_before_holder("eacces")

    # ── controls, green at both heads ────────────────────────────────────────────────────────────────────────────────
    def _sibling_after_holder_unreadable(self, how):
        after, _ = self._sibling(SID_AFTER)
        _hold, holder_file = self._sibling(SID_HOLD, holder=True)
        self._premise_order(SID_HOLD, SID_AFTER)
        with self._unreadable(after, how):
            got, faults, notes = self._lookup()
            self._found(got, faults, notes, holder_file, "the holder, sorted first, answers the walk")
            self.assertNotIn(after, [d for d, _m in km._SUBAGENT_FILE_CACHE[self.fork_key][0]],
                             "the unreadable sibling sorted after the holder is never reached")

    def test_control_an_unreadable_sibling_sorted_after_the_holder_is_never_reached_eio(self):
        self._sibling_after_holder_unreadable("eio")

    def test_control_an_unreadable_sibling_sorted_after_the_holder_is_never_reached_eacces(self):
        self._sibling_after_holder_unreadable("eacces")

    def _no_holder(self, layout, how):
        before, _ = self._sibling(SID_BEFORE)
        self._sibling(SID_HOLD)                                     # a readable sibling without the file
        root = str(self.subdir) if layout == "own" else before
        with self._unreadable(root, how):
            for call in ("first", "second"):
                got, faults, notes = self._lookup()
                self.assertIsNone(got, "%s call: the file is nowhere the walk could read" % call)
                self.assertEqual(faults, ["PermissionError" if how == "eacces" else "OSError"],
                                 "%s call: with the fault, since the file may be under the tree that could not be read" % call)
                self.assertNotIn(self.fork_key, km._SUBAGENT_FILE_CACHE,
                                 "%s call: nothing memoized, so the next call walks again (the fail-closed rule's cost)" % call)
                self.assertIn((root, km._TREE_UNREADABLE), notes,
                              "%s call: the running chat build is told the tree is unreadable, under a key no stat equals, so "
                              "its tab is rebuilt next cycle" % call)

    def test_control_no_holder_with_the_own_tree_unreadable_answers_none_with_the_fault_and_memoizes_nothing_eio(self):
        self._no_holder("own", "eio")

    def test_control_no_holder_with_the_own_tree_unreadable_answers_none_with_the_fault_and_memoizes_nothing_eacces(self):
        self._no_holder("own", "eacces")

    def test_control_no_holder_with_a_sibling_unreadable_answers_none_with_the_fault_and_memoizes_nothing_eio(self):
        self._no_holder("sibling", "eio")

    def test_control_no_holder_with_a_sibling_unreadable_answers_none_with_the_fault_and_memoizes_nothing_eacces(self):
        self._no_holder("sibling", "eacces")


if __name__ == "__main__":
    unittest.main()
