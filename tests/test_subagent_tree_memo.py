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
re-evaluates (None for a missing or dangling root, nothing for a live link, as before the memo), and its reads move none
of hit, miss and scoped; (6) eviction drops a
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
and with the file nowhere the lookup answers None with the fault and memoizes nothing; (12) the fail-closed answers
beside the own root's (FailClosedRoads): a sibling's tree that cannot be read and a project directory that cannot be
listed each reach the caller as a fault, memoize nothing and tell a running chat build the read is unreadable, whose
recorded key the next signature's re-stat differs from once the fault clears, when the lookup recovers; the feed key's
component for an unreadable root with no entry standing is the unreadable marker; and ENOTDIR at a root is absence (a
boundary guard); (13) what a reader that passes no faults list shows while the tree the agent's file lies under cannot
be read, with no resolution standing (ViewerUnderAnUnreadableTree): the viewer's missing-transcript frame, equal to a
removed tree's and keyed as it is, and an Agent head with no steps, both gone once the fault clears: the lookup then
resolves the file, the head carries its step, and the frame cache's key moves, so the frame cached under the fault is
rebuilt (a characterization, the witness of the texts that state it); (14) a lookup that could not be made answers the memo's standing resolution
only when that path lies under what the walk could not read (StandingResolutionUnderAFault): a standing path under a
tree the walk read in full, a sibling's or the own tree before a listing that faults, is not answered, and one under
the tree that faults, or under a sibling the listing could not name, is; (15) a place below a tree's root that cannot
be read, its root reading (FaultBelowTheRoot): a workflows/ or workflow directory whose listing fails, a workflow
directory whose own lstat fails and an entry whose type cannot be read each exclude that place from the agent-file
walk, so with the file under it the lookup answers None with the fault, memoizes nothing and walks again at the next
lookup, the chat build's record re-arms once the fault clears, the lookup then finds the file, and a standing
resolution under the place is answered and left standing; (16) the agent-file walk's own reads of a place
read the error (FaultOnTheWalksOwnRead): a candidate file whose lstat fails for a reason other than ENOENT and ENOTDIR
(in a directory that can be listed but not searched, or an EIO), in a workflow directory and at the flat place, and a
project-directory entry whose os.stat fails outside _REG_MISSING_ERRNOS, each with the file there alone, answer None
with the fault, memoize nothing, walk again at each lookup and note the place unreadable, and once the fault clears the
lookup finds the file; a standing resolution beside a faulted candidate is not answered; a file found past such a
fault is answered as before, and absent candidates, links at a candidate and links as an entry read as absence or not
a directory, with no fault. Red-first on (1), the jobs-pass half of (6), (9), (10), (11), (14), (15) and (16) (its
entry pin on 3.14t alone); (12) is red under a mutant per road; (13) is green before its change by design and red
under the follow-up that has the viewer state the fault.
Synthetic fixtures only: placeholder ids, invented text, a temp directory."""
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


SLOTS = ("subagent_trees", "subagent_stamps", "subagent_launches")   # the tree scope's slots on _live_scope (upstream's held
#   samples and the stamp index and launch folds derived from them), which every cycle opens together and clears together


def _scope_open():
    """Open the tree scope's three slots on this thread, as _pusher_cycle's try opens them."""
    for slot in SLOTS:
        setattr(km._live_scope, slot, {})


def _scope_close():
    """Clear them, as _pusher_cycle's finally does."""
    for slot in SLOTS:
        setattr(km._live_scope, slot, None)


def _scope():
    """This thread's open tree scope as {"trees", "stamps", "launches"}, the three slots' own objects, or None when no tree
    scope is open."""
    trees = getattr(km._live_scope, "subagent_trees", None)
    if trees is None:
        return None
    return {"trees": trees, "stamps": getattr(km._live_scope, "subagent_stamps", None),
            "launches": getattr(km._live_scope, "subagent_launches", None)}


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
        km._subagent_dirs(str(self.subdir))                         # the real tree, memoized (a miss, before the snapshot)
        counters = ("hit", "miss", "scoped")
        before = {k: km._SUBAGENT_TREE_STATS[k] for k in counters}
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
        # The counter rule (kernel/kernel.py, the comment at _SUBAGENT_TREE_STATS): a read answered no tree moves none of hit, miss
        # and scoped, and a symlink in the root's place, live or dangling, is such a read (round 2 of #882, extra6-3).
        moved = tuple(km._SUBAGENT_TREE_STATS[k] - before[k] for k in counters)
        self.assertEqual(moved, (0, 0, 0),
                         "memos.subagentTree (hit, miss, scoped) over every read of the root while a live and then a dangling link "
                         "stood in its place: %r; keyed on (0, 0, 0), since a read answered no tree lands in none of the three" % (moved,))


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
        self.assertEqual(set(rep), {"hit", "miss", "scoped", "evict", "dirStats", "walkMs", "validateMs", "roots", "dirs"})
        self.assertEqual((rep["miss"] - base["miss"], rep["hit"] - base["hit"]), (1, 1))
        self.assertGreaterEqual(rep["dirStats"] - base["dirStats"], 2, "the hit paid a stat per directory beyond the root")
        self.assertGreaterEqual(rep["roots"], 1)
        self.assertGreaterEqual(rep["dirs"], 3)
        self.assertGreaterEqual(rep["walkMs"], 0.0)
        self.assertGreaterEqual(rep["validateMs"], 0.0)
        self.assertEqual(rep, km._subagent_tree_memo_report())
        json.dumps(rep)
        # under an open cycle scope (2026-09-18) the first call is the cycle's sample (a hit: one lstat per known directory)
        # and the second is served from it: `scoped` moves, `dirStats` does not
        km._live_scope.subagent_trees = {}
        try:
            km._subagent_dirs(str(self.subdir))
            mid = km._subagent_tree_memo_report()
            self.assertEqual((mid["hit"] - rep["hit"], mid["dirStats"] - rep["dirStats"]), (1, 2), "the sample: a validation")
            km._subagent_dirs(str(self.subdir))
            served = km._subagent_tree_memo_report()
            self.assertEqual(served["scoped"] - mid["scoped"], 1, "served from the cycle's sample")
            self.assertEqual(served["dirStats"] - mid["dirStats"], 0, "...with no stat at all")
            self.assertEqual((served["hit"], served["miss"]), (mid["hit"], mid["miss"]))
        finally:
            km._live_scope.subagent_trees = None
        rep = km._subagent_tree_memo_report()
        (self.wf / "wf_inner").mkdir()                              # the tree moved: the call validates, mismatches and walks
        km._subagent_dirs(str(self.subdir))
        after = km._subagent_tree_memo_report()
        self.assertEqual((after["miss"] - rep["miss"], after["hit"] - rep["hit"]), (1, 0))
        self.assertGreaterEqual(after["walkMs"], rep["walkMs"])
        self.assertGreaterEqual(after["validateMs"], rep["validateMs"])


class UnreadableRoot(_Tree):
    """A root whose own lstat fails for a reason other than absence (EACCES from a parent without search permission, EIO)
    is a read that did not happen, not an absent tree: nothing is popped, nothing is noted absent, no counter moves, each
    reader answers its standing entry unheld, and the next call after the fault clears reads the disk again and finds the
    entry standing (a validation, never a walk). This is the second of the two rules in which this branch's tree read
    differs from upstream's: #1822's _subagent_tree_sample takes every OSError on the root's lstat for absence and pops.
    RED FIRST: until 2026-09-21 the root's `except OSError` took every errno for absence, so an EIO popped the entry,
    answered (), () and noted the tree absent to the chat build, which showed no subagents until the fault cleared; the
    module's own cases
    drove only ENOENT there. Two faults: an EIO by mock on os.lstat of the root alone (every other path reads) and a REAL
    EACCES from the parent directory without search permission (nothing under it reads either; skipped as root, whom
    permission bits do not bind). The scope is open under the fault, so "nothing held" is executed, not implied, and it is
    the WHOLE scope that is compared, its three slots (subagent_trees, subagent_stamps, subagent_launches) each empty
    after the tree reads: a pin over one slot is narrower than "no scope entry", and a stamps entry recorded on the raise
    left a trees-only pin green (the owner's pass before round 2 of #882, its fixes-by-execution lens). After the
    agent-file lookup under the real EACCES
    the whole scope is compared again, by equality, to the one entry the walk holds: the project directory's stamp, since
    a fault excludes its own tree from the walk and nothing else, so the walk goes on to list the project directory (round
    2 of #882, group A; FaultExcludesItsOwnTree below executes the exclusion)."""

    EMPTY = {"trees": {}, "stamps": {}, "launches": {}}   # the tree scope as a cycle opens it: nothing held in any of its three slots

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
        _scope_open()
        self.addCleanup(_scope_close)
        self.assertEqual(_scope(), self.EMPTY,
                         "premise: nothing held before the fault, in any of the scope's three slots (trees, stamps, launches)")

    def _fault_holds(self, root, entry, m, errno_expected):
        """Under the fault: the sidecar map first (the reader the chat build asks), then the memo, the feed key, the lookup."""
        before = dict(km._SUBAGENT_TREE_STATS)
        deps = {"task_outs": [], "postal_any": False}
        km._chat_dep_scope.deps = deps
        try:
            meta = km._subagent_meta_map(str(self.tpath))
        finally:
            km._chat_dep_scope.deps = None
        self.assertIn(root, km._SUBAGENT_TREES, "the entry stands: a read that did not happen pops nothing")
        self.assertIs(km._SUBAGENT_TREES[root], entry, "the same entry, untouched")
        self.assertNotIn((root, None), deps["task_outs"], "the tree is not noted absent to the chat build")
        self.assertEqual(deps["task_outs"], [(root, km._TREE_UNREADABLE)],
                         "it is noted unreadable, under a key no stat equals, so the tab is rebuilt next cycle and reads again")
        self.assertIs(meta, m, "the standing map is answered, unheld (its cache entry neither popped nor re-keyed)")
        self.assertEqual({k: km._SUBAGENT_TREE_STATS[k] - before[k] for k in ("hit", "miss", "scoped", "evict", "dirStats")},
                         {"hit": 0, "miss": 0, "scoped": 0, "evict": 0, "dirStats": 0}, "no counter moves: the read answered no tree")
        self.assertEqual(_scope(), self.EMPTY,
                         "nothing is held in the cycle scope, in any of its three slots (trees, stamps, launches): the fail-closed read "
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
        self.assertEqual(_scope(), self.EMPTY,
                         "still nothing held after the direct reads, in any of the three slots (trees, stamps, launches)")

    def _fold_has_the_calls_lifetime(self):
        """The awaiting fold over a resolution that could not be made is held for the call alone, never the cycle."""
        row = km._awaiting_item("agents", TU_WF, "Workflow", None, agent_id=AID_WF)
        cmd = km._awaiting_item("commands", "toolu_tree_cmd1", "run the api tests", None)
        agents, commands = km._awaiting_nest([row], [cmd], {}, str(self.tpath))
        self.assertEqual((len(agents), len(commands)), (1, 1), "nothing attributed this call")
        self.assertEqual(_scope()["launches"], {},
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
        self.assertIn((str(self.tpath), AID_WF), _scope()["launches"],
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
            proj = str(self.proj)
            faults = []
            self.assertEqual(km._subagent_file(str(self.tpath), AID_WF, faults), wf_file,
                             "the standing resolution is answered, unheld")
            self.assertEqual(faults, ["PermissionError"], "and the caller is told the lookup could not be made")
            self.assertIs(km._SUBAGENT_FILE_CACHE[(str(self.tpath), AID_WF)], standing, "its memo entry is untouched")
            row, cmd = self._fold_has_the_calls_lifetime()
            self.assertEqual(_scope(),
                             {"trees": {}, "stamps": {proj: (proj, os.stat(proj).st_mtime_ns)}, "launches": {}},
                             "at the fault's end the scope holds the project directory's stamp and nothing else, compared whole: the "
                             "agent-file walk excludes the own tree it could not read and goes on to list the project directory, "
                             "whose stamp it takes as an own stamp (round 2 of #882, group A); under the parent at mode 000 every "
                             "stat of the lookup's re-check fails, and a stat that raises is never held")
        finally:
            os.chmod(parent, 0o755)
        self._the_next_call_reads_again(root, m, row, cmd)


class _Walk(_Tree):
    """The agent-file walk's fixture (no cases of its own): AID_FORK's lookup key forgotten around each case, a sibling
    session's subagents tree in the project directory, a fault on one tree or on the project directory's listing, and
    the lookup under a running chat build's dependency scope. Every class below it in this module derives from it."""

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
    def _unlistable(self, how):
        """The project directory cannot be listed inside the block while every path under it still reads. "eacces": the
        directory at mode 0311 (search and write, no read: a real fault; lstat and stat under it still work); "eio": os.listdir
        and os.scandir of that directory raising EIO by mock, every other call reading. Path.iterdir lists through os.listdir
        (3.11, 3.12) or os.scandir (3.13 on); 3.10's pathlib lists through the os.listdir it bound at import, which the mock
        does not reach, so the EIO variant asserts that first and is skipped there."""
        proj = str(self.proj)
        if how == "eacces":
            if os.geteuid() == 0:
                self.skipTest("permission bits do not bind root: no EACCES to drive")
            os.chmod(proj, 0o311)
            try:
                with self.assertRaises(PermissionError, msg="premise: the real fault this case drives, on the listing alone"):
                    list(self.proj.iterdir())
                os.lstat(str(self.subdir))                          # premise: a path under the directory still reads
                yield
            finally:
                os.chmod(proj, 0o755)
            return

        def eio(real):
            def f(p=".", *a, **k):
                if not isinstance(p, int) and os.fsdecode(p) == proj:
                    raise OSError(errno.EIO, "input/output error")
                return real(p, *a, **k)
            return f
        with mock.patch.object(os, "listdir", eio(os.listdir)), mock.patch.object(os, "scandir", eio(os.scandir)):
            try:
                list(self.proj.iterdir())
                seen = False
            except OSError:
                seen = True
            if not seen:
                self.assertLess(sys.version_info, (3, 11), "premise: Path.iterdir reaches the mocked os.listdir or os.scandir "
                                                           "on every interpreter but 3.10")
                self.skipTest("3.10's pathlib lists through the os.listdir it bound at import: the EIO mock is not seen")
            yield

    @contextlib.contextmanager
    def _untyped_entry(self, how, holder=False):
        """A project-directory entry sorted before the holder whose type cannot be read, yielded, with AID_FORK's file under
        it when `holder` (reached through the entry: the entry's subagents/ at its top). "eacces": a symlink into a
        directory at mode 000 (a real fault: the stat through the link fails with EACCES); "eio": a sibling session's
        directory whose os.stat raises EIO by mock, every other call reading."""
        entry = self.proj / SID_BEFORE
        if how == "eacces":
            if os.geteuid() == 0:
                self.skipTest("permission bits do not bind root: no EACCES to drive")
            locked = Path(self.td) / "locked"
            (locked / "tree" / "subagents").mkdir(parents=True)
            if holder:
                (locked / "tree" / "subagents" / ("agent-%s.jsonl" % AID_FORK)).write_text("")
            entry.symlink_to(locked / "tree")
            self.roots.append(str(entry / "subagents"))
            os.chmod(locked, 0o000)
            try:
                yield entry
            finally:
                os.chmod(locked, 0o755)
            return
        self._sibling(SID_BEFORE, holder=holder)
        real = os.stat

        def eio(p, *a, **k):
            if str(p) == str(entry):
                raise OSError(errno.EIO, "input/output error")
            return real(p, *a, **k)
        with mock.patch.object(os, "stat", eio):
            yield entry

    def _entry_stat_premise(self, entry, how):
        """The entry's os.stat raises a fault under the `how` fault, on every interpreter: the read the walk takes a
        project-directory entry's type from (os.stat, looked up at call time, so the EIO mock is seen on 3.10 too, where
        pathlib stats through the os.stat it bound at import). Under the EACCES the stat through the link into the directory
        at mode 000 fails; under the EIO the mock raises. An errno in _REG_MISSING_ERRNOS would read as not a directory,
        so the premise is that it is outside that set."""
        with self.assertRaises(OSError, msg="premise: the entry's os.stat raises under the %s fault" % how) as cm:
            os.stat(entry)
        self.assertNotIn(cm.exception.errno, km._REG_MISSING_ERRNOS,
                         "premise: the entry's os.stat raises a fault, not an absence-shaped errno (%r)" % (cm.exception,))

    def _lookup(self):
        """AID_FORK's lookup under a running chat build's dependency scope: (answer, the caller's faults, the build's notes)."""
        faults, deps = [], {"task_outs": [], "postal_any": False}
        km._chat_dep_scope.deps = deps
        try:
            got = km._subagent_file(str(self.tpath), AID_FORK, faults)
        finally:
            km._chat_dep_scope.deps = None
        return got, faults, deps["task_outs"]

    def _looked_up(self, aid):
        """`aid`'s lookup under a running chat build's dependency scope: (answer, the caller's faults, the build's notes)."""
        faults, deps = [], {"task_outs": [], "postal_any": False}
        km._chat_dep_scope.deps = deps
        try:
            got = km._subagent_file(str(self.tpath), aid, faults)
        finally:
            km._chat_dep_scope.deps = None
        return got, faults, deps["task_outs"]

    def _unmade_then_found(self, aid, fault, place, err, found):
        """Under `fault` (a context manager), two lookups of `aid`, observed; after the fault's block, asserted first so
        that the memo serving the miss after the fault clears is the red: no memo entry before the next lookup, which
        finds `found` with no fault and memoizes it. Then what each lookup under the fault answered: None with the fault
        `err` passed to the caller, nothing memoized, a walk each and the one (place, _TREE_UNREADABLE) note by equality
        on the place."""
        key = (str(self.tpath), aid)
        walks, real_walk, seen = [], km._subagent_file_walk, []

        def counting(*a, **k):
            walks.append(1)
            return real_walk(*a, **k)
        with fault, mock.patch.object(km, "_subagent_file_walk", counting):
            for call in ("first", "second"):
                got, faults, notes = self._looked_up(aid)
                seen.append((call, got, faults, notes, km._SUBAGENT_FILE_CACHE.get(key)))
        walked = len(walks)
        before = km._SUBAGENT_FILE_CACHE.get(key)
        memo = None if before is None else ("a memo entry answering", before[1])
        got, faults, _notes = self._looked_up(aid)
        self.assertEqual((memo, got, faults), (None, found, []),
                         "the fault cleared: (the memo entry before the next lookup, its answer, its faults) = %r; keyed on (None, the "
                         "file, []): a lookup under the fault memoized nothing, so this one walks and finds the file (a miss memoized "
                         "under the fault stands, since a chmod or a cleared EIO moves no stamp, and is answered here: the readable "
                         "file reported missing)" % ((memo, got, faults),))
        self.assertEqual(km._SUBAGENT_FILE_CACHE[key][1], found, "and memoizes it")
        for call, got, faults, notes, memo in seen:
            self.assertIsNone(got, "%s lookup under the fault: the file lies at the place the walk could not read" % call)
            self.assertIsNone(memo, "%s lookup under the fault: nothing memoized (%r)" % (call, memo))
            self.assertEqual(faults, [err], "%s lookup under the fault: the caller is told the lookup could not be made" % call)
            self.assertEqual([p for p, k in notes if k == km._TREE_UNREADABLE], [place],
                             "%s lookup under the fault: the running chat build is told the place is unreadable, the place by "
                             "equality: %r" % (call, notes))
        self.assertEqual(walked, 2, "two lookups under the fault, two walks: nothing memoized, so each lookup walks again")


class FaultExcludesItsOwnTree(_Walk):
    """A fault excludes the tree that raised it and nothing else (round 2 of #882, group A: correctness-1, regression-1,
    extra5-1). An agent's file under a readable sibling session's tree (a /clear fork's fsid) is found, memoized and answered
    with no fault passed to the caller while another tree the walk looks through cannot be read: the own subagents tree, a
    sibling's sorted before the holder, or a project-directory entry sorted before the holder whose type cannot be read
    (its os.stat raising). RED FIRST: from the fail-closed change of 2026-09-21 until this one the agent-file walk
    answered through _subagent_walk_unreadable at the first such tree, before it looked through the trees sorted after it,
    so the lookup answered None with the fault and memoized nothing (the viewer said the transcript was missing, the
    awaiting box attributed no launches, the Agent card showed no steps) for as long as the unrelated tree stayed
    unreadable, where the walk before the fail-closed change found and memoized the file; and _subagent_file's gate
    discarded a found file whenever any fault occurred, so a fix to the walk alone did not reach the caller. Each road is
    driven under a real EACCES (a directory at mode 000; skipped as root, whom permission bits do not bind) and under an EIO
    by mock. The walk reads an entry's type by os.stat on every interpreter (round 3 of #882, group A; until then by
    Path.is_dir, whose raise depended on the interpreter, so the entry cases had no raise to drive on some), and each entry
    case asserts first that the entry's os.stat raises with an errno outside _REG_MISSING_ERRNOS (_entry_stat_premise).
    Two controls hold at both heads: an unreadable sibling sorted after the holder is never reached, and with the file nowhere (no holder) the lookup answers None with the fault, memoizes nothing and tells the
    running chat build the tree is unreadable, on every call while the fault lasts: the fail-closed rule's cost, which
    _subagent_tree's docstring states with the no-holder cases as its witness."""

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
            _scope_open()
            try:
                row = km._awaiting_item("agents", "toolu_tree_0003", "Workflow", None, agent_id=AID_FORK)
                cmd = km._awaiting_item("commands", "toolu_tree_cmd2", "run the api tests", None)
                km._awaiting_nest([row], [cmd], {}, str(self.tpath))
                self.assertIn(self.fork_key, _scope()["launches"],
                              "the fold over the found file is held for the cycle in the launch-fold slot "
                              "(_live_scope.subagent_launches): no fault reached _awaiting_nest")
            finally:
                _scope_close()
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
            self._entry_stat_premise(entry, how)
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


class FailClosedRoads(_Walk):
    """The fail-closed answers that no case executed until round 2 of #882 (group C, tests-1): the agent-file walk's fault on
    a sibling's tree, the project directory's listing that could not be made, the walk's _TREE_UNREADABLE note to a running
    chat build on both of those roads, _subagent_dirs_ident's marker for an unreadable root with no memo entry standing, and
    ENOTDIR at a root, which is absence. UnreadableRoot above reaches the own root alone, with its entries standing. Not red
    first: each answer was in the kernel before these cases. Each case is red, at the head that added it, under a mutant
    that takes its road's fault for absence or drops its answer: the sibling's fault not recorded, the listing's fault not
    recorded, the walk's note not made, the marker answered as the missing root's (None,), ENOTDIR moved to the unreadable
    side. The sibling and listing cases each assert, under the fault, the caller's faults, no memo entry and the note under
    an open chat dependency scope; then, after the fault clears, that the key the build recorded differs from the next
    signature's re-stat (_chat_sig_deps, the chat cache's own evaluation: the tab is rebuilt) and the recovery (the file
    found and memoized with no fault, and the rebuilt record equal to the next re-stat, so the tab settles). The file found
    after the fault clears would not pin the sibling road alone: under a real EACCES the stamp stat of the unreadable root
    fails too, so a walk that took the fault for absence would memoize its miss under (root, None), which no later stamp
    equals, and the memo would walk again and find the file on its own; under the EIO mock only the lstat faults, and that
    walk's miss would stand. Each road is driven under a real EACCES (skipped as root, whom permission bits do not bind)
    and under an EIO by mock."""

    ERR = {"eio": "OSError", "eacces": "PermissionError"}   # the type name the walk passes to the caller's faults

    def _rebuilt_then_settles(self, notes, where, holder_file):
        """After the fault clears. The key the build recorded for `where` is _TREE_UNREADABLE, and the next signature's
        re-stat of the same record differs from it, so the chat tab is rebuilt; the rebuilt tab's lookup finds the file, with
        no fault, memoizes it, and records keys equal to the next re-stat, so the tab is not rebuilt again."""
        rec = {"task_outs": list(notes), "pl_pending": [], "postal_any": False}
        restat = km._chat_sig_deps(SID, rec)[0]
        i = list(notes).index((where, km._TREE_UNREADABLE))
        self.assertEqual(restat[i][0], where, "premise: the re-stat evaluates the record's own entries, in order")
        self.assertIsNotNone(restat[i][1], "premise: %s stats again once the fault cleared" % where)
        self.assertNotEqual(restat[i], notes[i],
                            "the next signature's re-stat of %r differs from the key the build recorded for it (_TREE_UNREADABLE), "
                            "so the signature moves and the tab that showed the file missing is rebuilt" % where)
        got, faults, notes2 = self._lookup()
        self.assertEqual(got, holder_file, "recovery: the rebuilt tab's lookup finds the file once the fault cleared")
        self.assertEqual(faults, [], "with no fault passed to the caller")
        self.assertEqual(km._SUBAGENT_FILE_CACHE[self.fork_key][1], holder_file, "and memoizes it")
        rec2 = {"task_outs": list(notes2), "pl_pending": [], "postal_any": False}
        self.assertEqual(km._chat_sig_deps(SID, rec2)[0], tuple(notes2),
                         "the rebuilt tab's record equals the next signature's re-stat: the tab settles, rebuilt once")

    # ── the sibling road: the agent's file under the one tree that cannot be read ─────────────────────────────────────
    def _sibling_road(self, how):
        hold, holder_file = self._sibling(SID_HOLD, holder=True)
        with self._unreadable(hold, how):
            got, faults, notes = self._lookup()
            self.assertIsNone(got, "the file lies under the one tree the walk could not read: nothing found")
            self.assertEqual(faults, [self.ERR[how]],
                             "the sibling's fault reaches the caller: the lookup could not be made, which is not a miss (a walk "
                             "that took the fault for absence passes no fault and memoizes the miss)")
            self.assertNotIn(self.fork_key, km._SUBAGENT_FILE_CACHE,
                             "nothing memoized under the sibling's fault, so the next lookup walks again")
            self.assertIn((hold, km._TREE_UNREADABLE), notes,
                          "the running chat build is told the sibling's tree is unreadable, under a key no stat equals, so the tab "
                          "is rebuilt next cycle: %r" % (notes,))
        self._rebuilt_then_settles(notes, hold, holder_file)

    def test_a_siblings_tree_that_cannot_be_read_is_a_fault_with_no_memo_and_an_unreadable_note_and_re_arms_the_tab_eio(self):
        self._sibling_road("eio")

    def test_a_siblings_tree_that_cannot_be_read_is_a_fault_with_no_memo_and_an_unreadable_note_and_re_arms_the_tab_eacces(self):
        self._sibling_road("eacces")

    # ── the listing road: the project directory cannot be listed, the file under a readable sibling ────────────────────
    def _listing_road(self, how):
        _hold, holder_file = self._sibling(SID_HOLD, holder=True)
        proj = str(self.proj)
        with self._unlistable(how):
            got, faults, notes = self._lookup()
            self.assertIsNone(got, "the file lies under a sibling the walk reaches only through the listing: nothing found")
            self.assertEqual(faults, [self.ERR[how]],
                             "the listing's fault reaches the caller: a listing that could not be made is not a project "
                             "directory with no siblings (a walk that took it for absence passes no fault and memoizes the miss)")
            self.assertNotIn(self.fork_key, km._SUBAGENT_FILE_CACHE,
                             "nothing memoized under the listing's fault, so the next lookup walks again")
            self.assertIn((proj, km._TREE_UNREADABLE), notes,
                          "the running chat build is told the project directory could not be listed, under a key no stat "
                          "equals, so the tab is rebuilt next cycle: %r" % (notes,))
        self._rebuilt_then_settles(notes, proj, holder_file)

    def test_a_project_directory_that_cannot_be_listed_is_a_fault_with_no_memo_and_an_unreadable_note_and_re_arms_the_tab_eio(self):
        self._listing_road("eio")

    def test_a_project_directory_that_cannot_be_listed_is_a_fault_with_no_memo_and_an_unreadable_note_and_re_arms_the_tab_eacces(self):
        self._listing_road("eacces")

    # ── _subagent_dirs_ident's marker and ENOTDIR at the root ───────────────────────────────────────────────────────────
    def test_the_feed_keys_component_for_an_unreadable_root_with_no_entry_standing_is_the_unreadable_marker(self):
        """_subagent_dirs_ident for a root whose lstat fails for a reason other than absence, its memo entry popped first
        (UnreadableRoot answers this reader from the standing entry): (d,) with identity _TREE_UNREADABLE, never the missing
        root's (d,), (None,), so an unreadable tree is not keyed as an absent one, and the component moves once the root
        reads."""
        root = str(self.subdir)
        km._subagent_dirs(root)
        self.assertIsNotNone(km._SUBAGENT_TREES.pop(root, None), "premise: an entry stood, and is popped")
        with self._unreadable(root, "eio"):
            got = km._subagent_dirs_ident(SID, root)
        self.assertEqual(got, ((root,), (km._TREE_UNREADABLE,)),
                         "the feed key's component for an unreadable root with no entry standing is the unreadable marker, not "
                         "the missing root's ((d,), (None,)): %r" % (got,))
        self.assertNotEqual(km._subagent_dirs_ident(SID, root), got, "and the component moves once the root reads")

    def test_enotdir_at_the_root_is_absence_answered_empty_with_the_entry_popped_a_boundary_guard(self):
        """A boundary guard, green before the fail-closed change and since, by design: ENOTDIR on the root's own lstat (a
        regular file where the session directory above the root should be) is absence, answered ((), ()) with the memo entry
        popped, as ENOENT is (upstream's pop, with no eviction record under the one-cycle lag). The fail-closed change of
        2026-09-21 kept ENOTDIR on the absence side,
        and the `except OSError` before it read ENOTDIR as absence too, so this case cannot fail before that change; it turns
        red if a later change moves ENOTDIR to the unreadable side (a raise, the entry kept)."""
        root = str(self.subdir)
        km._subagent_dirs(root)
        self.assertIn(root, km._SUBAGENT_TREES, "premise: the entry stands")
        sess = self.subdir.parent
        shutil.rmtree(str(sess))
        sess.write_text("")                                         # a regular file where the session directory was
        with self.assertRaises(NotADirectoryError, msg="premise: the root's lstat fails with ENOTDIR"):
            os.lstat(root)
        try:
            got = km._subagent_tree(root)
        except km._SubagentTreeUnreadable as e:
            self.fail("ENOTDIR at the root was answered as a root that could not be read (%s); it is absence, nothing at the "
                      "root" % (e,))
        self.assertEqual(got, ((), ()), "ENOTDIR at the root is absence: ((), ())")
        self.assertNotIn(root, km._SUBAGENT_TREES, "and the entry is popped, as for a missing root")


class StandingResolutionUnderAFault(_Walk):
    """A lookup that could not be made (the file found nowhere while a tree, an entry or the listing faulted) answers the
    memo's standing resolution only when that path lies under what the walk could not read; a standing path under a tree
    the walk read in full is disproven by that read, and the answer is None with the fault (the pass applying round 2 of
    #882's rulings found the fault applied wider than its subject). RED before this change, at the round-2 head and after
    group A: _subagent_file answered the standing path whenever the lookup faulted, so AID_FORK's file, memoized under the
    holder sibling's tree and since moved into another sibling's tree that cannot be read, was answered at its old path,
    which no longer exists, because the other tree faulted; and a file memoized under the own tree and gone from it was
    answered at its old path while the project directory could not be listed, although the listing excludes only the
    siblings it could not name and the walk reads the own tree before it. Controls, green before the change and after
    it: a standing path under the very tree that faults, or under a sibling while the listing faults, is answered with
    the fault, since the walk could not look there. Each fault is driven under a real EACCES (skipped as root, whom
    permission bits do not bind) and under an EIO by mock (the listing's EIO variant skipped on 3.10, whose pathlib lists
    through the os.listdir it bound at import)."""

    ERR = {"eio": "OSError", "eacces": "PermissionError"}   # the type name the walk passes to the caller's faults

    def _memoized_under_the_holder(self):
        """AID_FORK found under the holder sibling's tree and memoized: (the holder's root, the file, the memo entry)."""
        hold, holder_file = self._sibling(SID_HOLD, holder=True)
        got, faults, _notes = self._lookup()
        self.assertEqual((got, faults), (holder_file, []), "premise: found under the holder sibling's tree")
        entry = km._SUBAGENT_FILE_CACHE[self.fork_key]
        self.assertEqual(entry[1], holder_file, "premise: memoized, the standing resolution")
        return hold, holder_file, entry

    def _moved_into_a_faulting_tree(self, how, after):
        other, _ = self._sibling(SID_AFTER if after else SID_BEFORE)
        hold, holder_file, entry = self._memoized_under_the_holder()
        if after:
            self._premise_order(SID_HOLD, SID_AFTER)
        else:
            self._premise_order(SID_BEFORE, SID_HOLD)
        os.rename(str(holder_file), os.path.join(other, holder_file.name))   # the file leaves the holder for the other tree
        with self._unreadable(other, how):
            got, faults, _notes = self._lookup()
        self.assertEqual(faults, [self.ERR[how]], "premise: the lookup could not be made, and the caller is told")
        self.assertIsNone(got,
                          "the walk read the holder's tree in full and the file is not there, so the standing path under it is "
                          "disproven; answered %r (exists: %s): a fault on another tree decided the answer for a tree the walk read"
                          % (got and os.path.relpath(str(got), self.td), bool(got) and os.path.exists(str(got))))
        self.assertIs(km._SUBAGENT_FILE_CACHE.get(self.fork_key), entry,
                      "and the lookup memoized nothing: the standing entry is untouched, so the next call walks again")

    def test_a_standing_path_under_a_tree_the_walk_read_is_not_answered_when_a_tree_sorted_after_it_faults_eio(self):
        self._moved_into_a_faulting_tree("eio", after=True)

    def test_a_standing_path_under_a_tree_the_walk_read_is_not_answered_when_a_tree_sorted_after_it_faults_eacces(self):
        self._moved_into_a_faulting_tree("eacces", after=True)

    def test_a_standing_path_under_a_tree_the_walk_read_is_not_answered_when_a_tree_sorted_before_it_faults_eio(self):
        self._moved_into_a_faulting_tree("eio", after=False)

    def test_a_standing_path_under_a_tree_the_walk_read_is_not_answered_when_a_tree_sorted_before_it_faults_eacces(self):
        self._moved_into_a_faulting_tree("eacces", after=False)

    def _own_file_gone_and_the_listing_faults(self, how):
        key = (str(self.tpath), AID_WF)
        self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, key, None)
        own_file = self.wf / ("agent-%s.jsonl" % AID_WF)
        self.assertEqual(km._subagent_file(str(self.tpath), AID_WF), own_file, "premise: found under the own tree and memoized")
        os.rename(str(own_file), os.path.join(self.td, own_file.name))      # the file leaves the own tree and the project
        with self._unlistable(how):
            faults = []
            got = km._subagent_file(str(self.tpath), AID_WF, faults)
        self.assertEqual(faults, [self.ERR[how]], "premise: the listing could not be made, and the caller is told")
        self.assertIsNone(got,
                          "the walk read the own tree in full before the listing faulted and the file is not there, so the "
                          "standing path under it is disproven; answered %r: the listing's fault excludes the siblings it could "
                          "not name, not the own tree" % (got and os.path.relpath(str(got), self.td),))

    def test_a_standing_path_under_the_own_tree_is_not_answered_when_the_project_directory_cannot_be_listed_eio(self):
        self._own_file_gone_and_the_listing_faults("eio")

    def test_a_standing_path_under_the_own_tree_is_not_answered_when_the_project_directory_cannot_be_listed_eacces(self):
        self._own_file_gone_and_the_listing_faults("eacces")

    # ── controls: a standing path where the walk could not look is answered, with the fault ────────────────────────────
    def _under_the_faulting_tree(self, how):
        hold, holder_file, _entry = self._memoized_under_the_holder()
        (self.proj / "notes.txt").write_text("")                  # a new entry: the project directory's stamp moves, so the
        with self._unreadable(hold, how):                          #  memo's re-check misses and the lookup walks
            got, faults, _notes = self._lookup()
        self.assertEqual((got, faults), (holder_file, [self.ERR[how]]),
                         "the standing path lies under the tree that could not be read: answered, with the fault")

    def test_control_a_standing_path_under_the_tree_that_faults_is_answered_eio(self):
        self._under_the_faulting_tree("eio")

    def test_control_a_standing_path_under_the_tree_that_faults_is_answered_eacces(self):
        self._under_the_faulting_tree("eacces")

    def _under_a_sibling_while_the_listing_faults(self, how):
        hold, holder_file, _entry = self._memoized_under_the_holder()
        (self.proj / "notes.txt").write_text("")                  # the project directory's stamp moves: the lookup walks
        with self._unlistable(how):
            got, faults, _notes = self._lookup()
        self.assertEqual((got, faults), (holder_file, [self.ERR[how]]),
                         "the standing path lies under a sibling the listing could not name: answered, with the fault")

    def test_control_a_standing_path_under_a_sibling_is_answered_while_the_project_directory_cannot_be_listed_eio(self):
        self._under_a_sibling_while_the_listing_faults("eio")

    def test_control_a_standing_path_under_a_sibling_is_answered_while_the_project_directory_cannot_be_listed_eacces(self):
        self._under_a_sibling_while_the_listing_faults("eacces")


class FaultBelowTheRoot(_Walk):
    """A place below a tree's root that the tree read could not read, the root itself reading: workflows/ whose listing
    fails (a real EACCES, the directory at mode 000; an EIO by mock on its os.scandir) or the workflow directory that holds
    the agent's file at mode 000, in the own tree and in a sibling's. The agent-file walk excludes that place as it
    excludes a tree whose root could not be read,
    so with the file under it the lookup answers None with the fault, memoizes nothing and walks again at the next
    lookup, and the running chat build is told the place is unreadable; once the fault clears, the key the build recorded
    differs from the next signature's re-stat (the tab is rebuilt) and the lookup finds the file. RED at the round-2 head
    and before this change (the pass applying round 2 of #882's rulings; the base behaved the same): _subagent_tree told no
    reader of a failed listing below the root, so the walk found no file, took that for a miss and memoized it on stamps
    a chmod or a transient EIO does not move, and every lookup after the fault cleared was answered the memoized miss
    until a stamped directory changed. The tree read's two other shapes have their cases since round 3 of #882 (tests-1:
    removing either report left both modules green): the workflow directory whose own lstat fails (workflows/ at 0o644
    for a real EACCES, an EIO by mock on its lstat) and the workflow directory's entry whose type cannot be read (an EIO
    on is_dir by a wrapped os.scandir), each asserting None, the fault, nothing memoized, the (place, _TREE_UNREADABLE)
    note by equality on the workflow directory and the file found once the fault clears; red at the round-2 head for
    the same reason, and under a kernel that drops that shape's report (the EACCES variant on the place's equality,
    since the candidate's lstat in the unsearchable workflows/ faults too and is noted instead). The chat record's re-arm composes two rules: the tree read noted the place under
    its own key, which a chmod does not move, and the walk noted it unreadable, and a path reported under two keys is
    recorded as their disagreement (_chat_build_deps). A standing resolution under the place that faults is answered with
    the fault and left standing, red before too, when the walk's miss replaced it in the memo. A control, green before the
    change and after it: a file under a readable sibling is found past the fault below the own root, memoized and answered
    with no fault. The EACCES cases skip as root, whom permission bits do not bind."""

    ERR = {"eacces-workflows": "PermissionError", "eio-workflows": "OSError", "eacces-wf": "PermissionError"}

    def setUp(self):
        super().setUp()
        self.wf_key = (str(self.tpath), AID_WF)
        km._SUBAGENT_FILE_CACHE.pop(self.wf_key, None)
        self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, self.wf_key, None)
        self.target = self.wf / ("agent-%s.jsonl" % AID_WF)

    @contextlib.contextmanager
    def _below(self, how):
        """The place below the own root that cannot be read inside the block, yielded; the root and every other path read."""
        place = str(self.subdir / "workflows") if how.endswith("workflows") else str(self.wf)
        if how.startswith("eacces"):
            if os.geteuid() == 0:
                self.skipTest("permission bits do not bind root: no EACCES to drive")
            os.chmod(place, 0o000)
            try:
                with self.assertRaises(PermissionError, msg="premise: the real fault this case drives, the place's listing"):
                    os.listdir(place)
                os.lstat(str(self.subdir))                          # premise: the root itself still reads
                yield place
            finally:
                os.chmod(place, 0o755)
            return
        real = os.scandir

        def eio(p=".", *a, **k):
            if not isinstance(p, int) and os.fsdecode(p) == place:
                raise OSError(errno.EIO, "input/output error")
            return real(p, *a, **k)
        with mock.patch.object(os, "scandir", eio):
            yield place

    def _lookup_wf(self):
        """AID_WF's lookup under a running chat build's dependency scope: (answer, the caller's faults, the build's notes)."""
        faults, deps = [], {"task_outs": [], "postal_any": False}
        km._chat_dep_scope.deps = deps
        try:
            got = km._subagent_file(str(self.tpath), AID_WF, faults)
        finally:
            km._chat_dep_scope.deps = None
        return got, faults, deps["task_outs"]

    def _fault_below(self, how):
        km._SUBAGENT_TREES.pop(str(self.subdir), None)             # no standing tree entry: the fault is met by a walk
        walks, real_walk = [], km._subagent_file_walk

        def counting(*a, **k):
            walks.append(1)
            return real_walk(*a, **k)
        with self._below(how) as place, mock.patch.object(km, "_subagent_file_walk", counting):
            for call in ("first", "second"):
                got, faults, notes = self._lookup_wf()
                self.assertIsNone(got, "%s lookup: the file lies under the place the tree read could not read" % call)
                self.assertNotIn(self.wf_key, km._SUBAGENT_FILE_CACHE,
                                 "%s lookup: the walk could not read the place the file lies under, so its miss is not a miss and "
                                 "is not memoized (a memoized miss is served after the fault clears, since a chmod or an EIO moves "
                                 "no stamp): %r" % (call, km._SUBAGENT_FILE_CACHE.get(self.wf_key)))
                self.assertEqual(faults, [self.ERR[how]], "%s lookup: the caller is told the lookup could not be made" % call)
                self.assertIn((place, km._TREE_UNREADABLE), notes,
                              "%s lookup: the running chat build is told the place is unreadable: %r" % (call, notes))
            self.assertEqual(len(walks), 2, "two lookups under the fault, two walks: nothing memoized, so each lookup walks again")
        km._chat_dep_scope.deps = {"task_outs": list(notes), "postal_any": False}
        try:
            rec = km._chat_build_deps(SID, {"events": []})
        finally:
            km._chat_dep_scope.deps = None
        restat = km._chat_sig_deps(SID, rec)[0]
        self.assertNotEqual(dict(rec["task_outs"]).get(place), dict(restat).get(place),
                            "the fault cleared: the key the build recorded for the place differs from the next signature's re-stat, "
                            "so the tab that showed the file missing is rebuilt (recorded %r, re-stat %r)"
                            % (dict(rec["task_outs"]).get(place), dict(restat).get(place)))
        got, faults, _notes = self._lookup_wf()
        self.assertEqual((got, faults), (self.target, []), "the fault cleared: the next lookup finds the file, with no fault")
        self.assertEqual(km._SUBAGENT_FILE_CACHE[self.wf_key][1], self.target, "and memoizes it")

    def test_a_workflows_directory_that_cannot_be_listed_eacces_is_a_fault_with_nothing_memoized(self):
        self._fault_below("eacces-workflows")

    def test_a_workflows_directory_that_cannot_be_listed_eio_is_a_fault_with_nothing_memoized(self):
        self._fault_below("eio-workflows")

    def test_a_workflow_directory_that_cannot_be_listed_eacces_is_a_fault_with_nothing_memoized(self):
        self._fault_below("eacces-wf")

    def _sibling_fault_below(self, how):
        """The same road in a sibling's tree: AID_FORK's file in a workflow directory of the holder sibling's tree, that
        directory at mode 000 (its listing and the candidate stat under it fail), or the sibling's workflows/ listing
        failing by an EIO by mock on its os.scandir, so the workflow directory is never found (an EIO on the workflow
        directory's own listing would leave the candidate stat of the file inside it reading, and the file found)."""
        hold, _ = self._sibling(SID_HOLD)
        wf = Path(hold) / "workflows" / "wf_00000000000000f2"
        wf.mkdir()
        holder_file = wf / ("agent-%s.jsonl" % AID_FORK)
        holder_file.write_text("")
        _age(str(self.proj / SID_HOLD))
        place = str(wf) if how == "eacces" else str(wf.parent)
        if how == "eacces":
            if os.geteuid() == 0:
                self.skipTest("permission bits do not bind root: no EACCES to drive")
            os.chmod(str(wf), 0o000)
            fault = contextlib.nullcontext()
        else:
            real = os.scandir

            def eio(p=".", *a, **k):
                if not isinstance(p, int) and os.fsdecode(p) == place:
                    raise OSError(errno.EIO, "input/output error")
                return real(p, *a, **k)
            fault = mock.patch.object(os, "scandir", eio)
        try:
            with fault:
                got, faults, notes = self._lookup()
        finally:
            os.chmod(str(wf), 0o755)
        self.assertIsNone(got, "the file lies under the sibling's place its tree read could not read")
        self.assertNotIn(self.fork_key, km._SUBAGENT_FILE_CACHE,
                         "the walk could not read the place the file lies under, so its miss is not memoized: %r"
                         % (km._SUBAGENT_FILE_CACHE.get(self.fork_key),))
        self.assertEqual(faults, ["PermissionError" if how == "eacces" else "OSError"], "the caller is told")
        self.assertIn((place, km._TREE_UNREADABLE), notes, "the running chat build is told the place is unreadable")
        got, faults, _notes = self._lookup()
        self.assertEqual((got, faults), (holder_file, []), "the fault cleared: the next lookup finds the file, with no fault")

    def test_a_workflow_directory_under_a_siblings_tree_that_cannot_be_listed_eacces_is_a_fault_with_nothing_memoized(self):
        self._sibling_fault_below("eacces")

    def test_a_workflows_directory_under_a_siblings_tree_that_cannot_be_listed_eio_is_a_fault_with_nothing_memoized(self):
        self._sibling_fault_below("eio")

    # ── the tree read's two other shapes (round 3 of #882, tests-1) ───────────────────────────────────────────────────
    @contextlib.contextmanager
    def _child_lstat_fails(self, how):
        """workflows/ listed and its entry typed while the workflow directory's own lstat fails inside the block.
        "eacces": workflows/ at mode 0o644 (read without search: a real fault), its premises asserted: the listing
        succeeds and names the workflow directory, the entry's is_dir(follow_symlinks=False) from the listing succeeds,
        and the child's lstat raises PermissionError; "eio": os.lstat of the workflow directory alone raising EIO by
        mock, every other call reading."""
        wfs, wf = str(self.subdir / "workflows"), str(self.wf)
        if how == "eacces":
            if os.geteuid() == 0:
                self.skipTest("permission bits do not bind root: no EACCES to drive")
            os.chmod(wfs, 0o644)
            try:
                with os.scandir(wfs) as it:
                    ents = {e.name: e for e in it}
                    self.assertIn(self.wf.name, ents, "premise: workflows/'s listing succeeds and names the workflow directory")
                    self.assertTrue(ents[self.wf.name].is_dir(follow_symlinks=False),
                                    "premise: the entry's type, from the listing, reads as a directory")
                with self.assertRaises(PermissionError, msg="premise: the child's lstat raises"):
                    os.lstat(wf)
                yield
            finally:
                os.chmod(wfs, 0o755)
            return
        real = os.lstat

        def eio(p, *a, **k):
            if not isinstance(p, int) and os.fsdecode(p) == wf:
                raise OSError(errno.EIO, "input/output error")
            return real(p, *a, **k)
        with mock.patch.object(os, "lstat", eio):
            yield

    @contextlib.contextmanager
    def _entry_type_fails(self):
        """workflows/ listed through a wrapped os.scandir whose every entry's is_dir(follow_symlinks=False) raises EIO
        inside the block, every other listing and call reading; the premise asserted: the wrapped entry's type raises."""
        wfs, real = str(self.subdir / "workflows"), os.scandir

        class Entry:
            def __init__(self, e):
                self._e = e

            def __getattr__(self, name):
                return getattr(self._e, name)

            def is_dir(self, *, follow_symlinks=True):
                if not follow_symlinks:
                    raise OSError(errno.EIO, "input/output error")
                return self._e.is_dir()

        class Listing:
            def __init__(self, it):
                self._it = it

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self._it.close()
                return False

            def __iter__(self):
                return (Entry(e) for e in self._it)

        def scandir(p=".", *a, **k):
            it = real(p, *a, **k)
            return Listing(it) if not isinstance(p, int) and os.fsdecode(p) == wfs else it
        with mock.patch.object(os, "scandir", scandir):
            with os.scandir(wfs) as it:
                ents = list(it)
            self.assertEqual([e.name for e in ents], [self.wf.name], "premise: the wrapped listing names the workflow directory")
            with self.assertRaises(OSError, msg="premise: the entry's type raises"):
                ents[0].is_dir(follow_symlinks=False)
            yield

    def test_a_workflow_directory_whose_lstat_fails_eacces_is_a_fault_with_nothing_memoized_and_the_place_noted(self):
        """The child-lstat shape under a real EACCES (workflows/ at 0o644). The place noted is the workflow directory, the
        child whose lstat failed, by equality: A's candidate road faults here too (workflows/ cannot be searched, so the
        candidate's lstat in it raises) and would note the candidate, so with the child's report removed the case still
        sees a fault and reds on the place alone."""
        km._SUBAGENT_TREES.pop(str(self.subdir), None)             # no standing tree entry: the fault is met by a walk
        self._unmade_then_found(AID_WF, self._child_lstat_fails("eacces"), str(self.wf), "PermissionError", self.target)

    def test_a_workflow_directory_whose_lstat_fails_eio_is_a_fault_with_nothing_memoized_and_the_place_noted(self):
        """The child-lstat shape under an EIO by mock on the workflow directory's lstat alone."""
        km._SUBAGENT_TREES.pop(str(self.subdir), None)
        self._unmade_then_found(AID_WF, self._child_lstat_fails("eio"), str(self.wf), "OSError", self.target)

    def test_an_entry_whose_type_cannot_be_read_eio_is_a_fault_with_nothing_memoized_and_the_entry_noted(self):
        """The entry-type shape: workflows/'s listing succeeds and the workflow directory's entry cannot be typed (EIO on
        is_dir(follow_symlinks=False) by a wrapped os.scandir). The place noted is the entry, the workflow directory
        (os.path.join of the directory listed and the entry's name), not workflows/."""
        km._SUBAGENT_TREES.pop(str(self.subdir), None)
        self._unmade_then_found(AID_WF, self._entry_type_fails(), str(self.wf), "OSError", self.target)

    # ── controls, green before the change and after it ─────────────────────────────────────────────────────────────────
    def test_control_a_file_under_a_readable_sibling_is_found_past_a_fault_below_the_own_root(self):
        _hold, holder_file = self._sibling(SID_HOLD, holder=True)
        km._SUBAGENT_TREES.pop(str(self.subdir), None)
        with self._below("eio-workflows"):
            got, faults, _notes = self._lookup()
        self.assertEqual((got, faults), (holder_file, []), "found past the fault below the own root, with no fault passed on")
        self.assertEqual(km._SUBAGENT_FILE_CACHE[self.fork_key][1], holder_file, "and memoized")

    def test_a_standing_resolution_under_the_place_that_faults_is_answered_with_the_fault_and_left_standing(self):
        self.assertEqual(km._subagent_file(str(self.tpath), AID_WF), self.target, "premise: found and memoized")
        entry = km._SUBAGENT_FILE_CACHE[self.wf_key]
        (self.subdir / "notes.txt").write_text("")                 # the own root's stamp moves: the memo re-check misses, the lookup walks
        with self._below("eacces-wf"):
            faults = []
            got = km._subagent_file(str(self.tpath), AID_WF, faults)
        self.assertIs(km._SUBAGENT_FILE_CACHE.get(self.wf_key), entry,
                      "the standing entry is left as it was: the walk could not read the place the file lies under, so its miss "
                      "does not replace the resolution (%r)" % (km._SUBAGENT_FILE_CACHE.get(self.wf_key),))
        self.assertEqual((got, faults), (self.target, ["PermissionError"]),
                         "the standing resolution lies under the place the walk could not read: answered, with the fault")

    def test_a_child_gone_since_its_parent_was_listed_is_absence_and_its_miss_is_memoized_a_boundary_guard(self):
        """A boundary guard on the absence side, green before this change by design (the walk then memoized every miss
        below the root): a child whose lstat raises ENOENT is a place gone since its parent was listed, whose removal
        moved the parent's stamp, so it is absence, not a place the walk could not read: no fault reaches the caller and
        the miss is memoized, as for a root that is not there. Driven by an ENOENT by mock on the workflow directory's
        lstat, every other call reading; red if a change moves ENOENT to the fault side."""
        km._SUBAGENT_TREES.pop(str(self.subdir), None)
        real, gone = os.lstat, str(self.wf)

        def enoent(p, *a, **k):
            if not isinstance(p, int) and os.fsdecode(p) == gone:
                raise FileNotFoundError(errno.ENOENT, "no such file or directory")
            return real(p, *a, **k)
        with mock.patch.object(os, "lstat", enoent):
            got, faults, notes = self._lookup_wf()
        self.assertEqual((got, faults), (None, []), "a child gone since its parent was listed is absence: a miss, with no fault")
        self.assertIsNone(km._SUBAGENT_FILE_CACHE.get(self.wf_key, (None, "unset"))[1], "and the miss is memoized")
        self.assertNotIn(km._TREE_UNREADABLE, [k for _p, k in notes], "and no place is noted unreadable to the chat build")


class FaultOnTheWalksOwnRead(_Walk):
    """The agent-file walk's own reads of a place read the error, never a boolean helper that answers a fault as False
    (round 3 of #882, group A: correctness-1, extra5-1, kernel-1, extra8-1). A candidate file, the own place included, is
    read by os.lstat: ENOENT and ENOTDIR are absence, any other errno a fault that excludes the candidate path. A
    project-directory entry's type is read by os.stat: _REG_MISSING_ERRNOS reads as not a directory, any other errno a
    fault that excludes the entry. RED FIRST at the round-3 head: the walk read a candidate through os.path.isfile, which
    answers False on EACCES and EIO on every interpreter, and an entry through Path.is_dir, which answers False on any
    error from 3.14 (3.10 to 3.13 raised, and the entry was excluded already), so the fault was taken for absence, the
    miss memoized on stamps a chmod or a cleared EIO never moves, and the lookup after the fault cleared was answered
    the memoized miss. The real shape: a directory that can be listed but not searched (read without execute) holding
    only files, whose listing succeeds and types its entries with no child to lstat, so the tree read reports no fault,
    while the candidate's lstat raises EACCES. Each pin asserts, under the fault, None, the fault passed to the caller,
    nothing memoized, a walk per lookup and the (place, _TREE_UNREADABLE) note by equality on the place, and after the
    fault clears, the memo entry absent before the next lookup and the file found. The EIO pins mock os.stat and
    os.lstat both for the candidate alone, as a real EIO fails every stat of the path: a mock of the lstat alone is
    never seen by os.path.isfile, and the red would be for another reason. The entry pin is red at the round-3 head on
    3.14t alone; on 3.10 its EIO variant fails there too, but only because 3.10's pathlib stats through the os.stat it
    bound at import and never sees the mock, which is not the defect; elsewhere it is green at both heads, the control
    that the new partition keeps what pathlib did before 3.14. The controls and boundaries at the end are green at both
    heads by design, each saying so. The EACCES cases skip as root, whom permission bits do not bind."""

    ERR = {"eacces": "PermissionError", "eio": "OSError"}   # the type name the walk passes to the caller's faults

    def setUp(self):
        super().setUp()
        self.wf_key, self.flat_key = (str(self.tpath), AID_WF), (str(self.tpath), AID)
        for k in (self.wf_key, self.flat_key):
            km._SUBAGENT_FILE_CACHE.pop(k, None)
            self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, k, None)

    # ── the faults ──────────────────────────────────────────────────────────────────────────────────────────────────
    @contextlib.contextmanager
    def _listable_unsearchable(self, d, cand, name_listed):
        """The directory `d` at mode 0o644 inside the block (read without search: a real fault), its premises asserted:
        the listing succeeds (naming the agent's file when `name_listed`), the own tree's read reports no fault (its
        listings succeed, each entry typed from the listing, no child to lstat; the read's memo entry dropped after, so the
        lookup walks), and the candidate's lstat raises PermissionError."""
        if os.geteuid() == 0:
            self.skipTest("permission bits do not bind root: no EACCES to drive")
        os.chmod(d, 0o644)
        try:
            names = os.listdir(d)
            if name_listed:
                self.assertIn(os.path.basename(cand), names, "premise: the directory's listing succeeds and names the agent's file")
            below = []
            km._subagent_tree(str(self.subdir), faults=below)
            km._SUBAGENT_TREES.pop(str(self.subdir), None)
            self.assertEqual(below, [], "premise: the own tree's read reports no fault, so it excludes nothing")
            with self.assertRaises(PermissionError, msg="premise: the candidate's lstat raises"):
                os.lstat(cand)
            yield
        finally:
            os.chmod(d, 0o755)

    @contextlib.contextmanager
    def _eio_on(self, target):
        """os.stat and os.lstat both raising EIO for the path `target` alone, every other path reading."""
        def raising(real):
            def f(p, *a, **k):
                if not isinstance(p, int) and os.fsdecode(p) == target:
                    raise OSError(errno.EIO, "input/output error")
                return real(p, *a, **k)
            return f
        with mock.patch.object(os, "stat", raising(os.stat)), mock.patch.object(os, "lstat", raising(os.lstat)):
            yield

    def _flat_only_files(self):
        """The own subagents/ holding only files (workflows/ removed): the flat layout's real shape."""
        shutil.rmtree(str(self.subdir / "workflows"))
        return str(self.subdir / ("agent-%s.jsonl" % AID))

    # ── (1) the candidate under a real EACCES ───────────────────────────────────────────────────────────────────────
    def test_a_candidate_in_a_workflow_directory_that_can_be_listed_but_not_searched_is_a_fault_with_nothing_memoized_eacces(self):
        cand = str(self.wf / ("agent-%s.jsonl" % AID_WF))
        self._unmade_then_found(AID_WF, self._listable_unsearchable(str(self.wf), cand, True), cand, self.ERR["eacces"],
                                Path(cand))

    def test_the_flat_place_in_a_subagents_directory_that_can_be_listed_but_not_searched_is_a_fault_with_nothing_memoized_eacces(self):
        ap = self._flat_only_files()
        self._unmade_then_found(AID, self._listable_unsearchable(str(self.subdir), ap, True), ap, self.ERR["eacces"], Path(ap))

    # ── (2) the candidate under an EIO on every stat of its path ────────────────────────────────────────────────────
    def test_a_candidate_in_a_workflow_directory_whose_every_stat_raises_eio_is_a_fault_with_nothing_memoized(self):
        cand = str(self.wf / ("agent-%s.jsonl" % AID_WF))
        self._unmade_then_found(AID_WF, self._eio_on(cand), cand, self.ERR["eio"], Path(cand))

    def test_the_flat_place_whose_every_stat_raises_eio_is_a_fault_with_nothing_memoized(self):
        ap = str(self.subdir / ("agent-%s.jsonl" % AID))
        self._unmade_then_found(AID, self._eio_on(ap), ap, self.ERR["eio"], Path(ap))

    # ── (3) a project-directory entry whose type cannot be read, the file under it alone ────────────────────────────
    def _entry_holding_the_file(self, how):
        entry = self.proj / SID_BEFORE
        found = entry / "subagents" / ("agent-%s.jsonl" % AID_FORK)

        @contextlib.contextmanager
        def fault():
            with self._untyped_entry(how, holder=True) as e:
                self._entry_stat_premise(e, how)
                yield
        self._unmade_then_found(AID_FORK, fault(), str(entry), self.ERR[how], found)

    def test_an_entry_whose_type_cannot_be_read_holding_the_file_is_a_fault_with_nothing_memoized_eacces(self):
        self._entry_holding_the_file("eacces")

    def test_an_entry_whose_type_cannot_be_read_holding_the_file_is_a_fault_with_nothing_memoized_eio(self):
        self._entry_holding_the_file("eio")

    # ── (4) a standing resolution beside a faulted candidate ─────────────────────────────────────────────────────────
    def test_a_standing_resolution_under_a_readable_subdirectory_of_a_faulted_candidates_directory_is_not_answered(self):
        """AID_WF's file found under its workflow directory and memoized, then moved out of the project directory (its
        directory's stamp moves, so the next lookup walks), and the flat place, the own root's candidate, faulted by the
        EIO mock on both calls. The walk reads the workflow directory in full and the file is not there, so the standing
        path is disproven: None with the fault, the standing entry left as it was. Red at the round-3 head, where
        os.path.isfile swallowed the EIO (no fault, the miss memoized), and under a kernel that excludes the candidate's
        directory rather than the candidate (the own subagents directory, everything under it: the standing path
        answered). The file has left the project directory, so after the fault clears the lookup is a real miss:
        memoized, with no fault."""
        target = self.wf / ("agent-%s.jsonl" % AID_WF)
        self.assertEqual(km._subagent_file(str(self.tpath), AID_WF), target, "premise: found under the workflow directory")
        entry = km._SUBAGENT_FILE_CACHE[self.wf_key]
        self.assertEqual(entry[1], target, "premise: memoized, the standing resolution")
        os.rename(str(target), os.path.join(self.td, target.name))
        ap = str(self.subdir / ("agent-%s.jsonl" % AID_WF))
        with self._eio_on(ap):
            got, faults, notes = self._looked_up(AID_WF)
        self.assertEqual(faults, [self.ERR["eio"]], "the lookup could not be made: the flat place's EIO is a fault, passed on")
        self.assertIsNone(got, "the walk read the workflow directory in full and the file is not there, so the standing path is "
                               "disproven; answered %r: the fault excluded more than the candidate that raised it"
                               % (got and os.path.relpath(str(got), self.td),))
        self.assertIs(km._SUBAGENT_FILE_CACHE.get(self.wf_key), entry, "and the lookup memoized nothing: the standing entry is untouched")
        self.assertEqual([p for p, k in notes if k == km._TREE_UNREADABLE], [ap], "the running chat build is told the place is unreadable")
        got, faults, _notes = self._looked_up(AID_WF)
        self.assertEqual((got, faults), (None, []), "the fault cleared: the file is nowhere, a real miss, with no fault")
        self.assertIsNone(km._SUBAGENT_FILE_CACHE[self.wf_key][1], "and the miss is memoized")

    # ── controls and boundaries, green at both heads by design ──────────────────────────────────────────────────────
    def _found_past(self, fault):
        _hold, holder_file = self._sibling(SID_HOLD, holder=True)
        with fault:
            got, faults, notes = self._looked_up(AID_FORK)
        self.assertEqual((got, faults), (holder_file, []), "found under the readable sibling past the faulted candidate, no fault passed on")
        self.assertEqual(km._SUBAGENT_FILE_CACHE[self.fork_key][1], holder_file, "and memoized")
        self.assertNotIn(km._TREE_UNREADABLE, [k for _p, k in notes], "and nothing noted unreadable")

    def test_control_found_elsewhere_past_a_candidate_in_a_workflow_directory_that_cannot_be_searched_eacces(self):
        """Green at both heads by design: a file found past a fault was answered the same before (os.path.isfile took
        the candidate for absent and the walk went on)."""
        cand = str(self.wf / ("agent-%s.jsonl" % AID_FORK))
        self._found_past(self._listable_unsearchable(str(self.wf), cand, False))

    def test_control_found_elsewhere_past_the_flat_place_in_a_subagents_directory_that_cannot_be_searched_eacces(self):
        """Green at both heads by design, as the case above."""
        self._flat_only_files()
        ap = str(self.subdir / ("agent-%s.jsonl" % AID_FORK))
        self._found_past(self._listable_unsearchable(str(self.subdir), ap, False))

    def test_control_found_elsewhere_past_a_candidate_whose_every_stat_raises_eio(self):
        """Green at both heads by design, as the cases above, in the nested and the flat place."""
        for cand in (str(self.wf / ("agent-%s.jsonl" % AID_FORK)), str(self.subdir / ("agent-%s.jsonl" % AID_FORK))):
            with self.subTest(cand=os.path.relpath(cand, self.td)):
                km._SUBAGENT_FILE_CACHE.pop(self.fork_key, None)
                shutil.rmtree(str(self.proj / SID_HOLD), ignore_errors=True)
                self._found_past(self._eio_on(cand))

    def _plain_miss(self, what):
        got, faults, notes = self._looked_up(AID_FORK)
        self.assertEqual((got, faults), (None, []), "%s: a miss, with no fault" % what)
        self.assertIsNone(km._SUBAGENT_FILE_CACHE.get(self.fork_key, (None, "unset"))[1], "%s: and the miss is memoized" % what)
        self.assertNotIn(km._TREE_UNREADABLE, [k for _p, k in notes], "%s: and nothing noted unreadable" % what)

    def test_boundary_an_absent_candidate_is_a_miss_memoized_with_no_fault(self):
        """The absence side, green at both heads by design: ENOENT on every candidate (no file anywhere) is an ordinary
        miss, memoized; and ENOTDIR by mock on both stats of a candidate (a file where a directory on its path was) is
        absence too. Red under a kernel that moves either errno to the fault side."""
        self._plain_miss("ENOENT on every candidate")
        km._SUBAGENT_FILE_CACHE.pop(self.fork_key, None)
        target = str(self.wf / ("agent-%s.jsonl" % AID_FORK))

        def enotdir(real):
            def f(p, *a, **k):
                if not isinstance(p, int) and os.fsdecode(p) == target:
                    raise NotADirectoryError(errno.ENOTDIR, "not a directory")
                return real(p, *a, **k)
            return f
        with mock.patch.object(os, "stat", enotdir(os.stat)), mock.patch.object(os, "lstat", enotdir(os.lstat)):
            self._plain_miss("ENOTDIR on a candidate")

    def test_boundary_a_looping_dangling_or_live_symlink_as_the_candidate_is_a_miss_memoized_with_no_fault(self):
        """Green at both heads by design: the walk never takes a symlink, and its lstat of one succeeds, so a looping, a
        dangling or a live link at a candidate is a candidate that is not a regular file, a miss with no fault. Red under a
        kernel that reads the candidate by os.stat with ENOENT and ENOTDIR alone as absence (a looping link then raises
        ELOOP through it, a fault in a place the walk never takes, and a permanent one)."""
        real = Path(self.td) / "elsewhere.jsonl"
        real.write_text("")
        for where in (self.wf, self.subdir):
            for kind in ("looping", "dangling", "live"):
                with self.subTest(where=os.path.relpath(str(where), self.td), kind=kind):
                    km._SUBAGENT_FILE_CACHE.pop(self.fork_key, None)
                    link = where / ("agent-%s.jsonl" % AID_FORK)
                    link.symlink_to({"looping": link.name, "dangling": "gone.jsonl", "live": str(real)}[kind])
                    try:
                        self._plain_miss("a %s link at %s" % (kind, link.name))
                    finally:
                        link.unlink()

    def test_boundary_a_looping_or_dangling_symlink_as_a_project_directory_entry_is_not_a_directory_and_no_fault(self):
        """Green at both heads by design: an entry's type is read through a link, and ELOOP (a looping link) and ENOENT (a
        dangling one) are in _REG_MISSING_ERRNOS, so the entry is not a directory, never a fault, as Path.is_dir answered
        it before. Red under a kernel that drops ELOOP from the entry's partition."""
        for kind in ("looping", "dangling"):
            with self.subTest(kind=kind):
                km._SUBAGENT_FILE_CACHE.pop(self.fork_key, None)
                link = self.proj / SID_BEFORE
                link.symlink_to(SID_BEFORE if kind == "looping" else "gone")
                try:
                    with self.assertRaises(OSError, msg="premise: the entry's os.stat raises") as cm:
                        os.stat(link)
                    self.assertIn(cm.exception.errno, km._REG_MISSING_ERRNOS, "premise: an absence-shaped errno (%r)" % (cm.exception,))
                    self._plain_miss("a %s link as a project-directory entry" % kind)
                finally:
                    link.unlink()


class ViewerUnderAnUnreadableTree(_Walk):
    """What a reader that passes no faults list shows while the tree the agent's file lies under cannot be read (round 2
    of #882, group F: kernel-2, extra5-3, decided as option (b)). _subagent_file answers such a caller a bare None when
    the file is found under no tree the walk could read while one could not be read, and the caller reads it as absence:
    the viewer (build_subagent) says the agent's transcript is missing, the frame equal to the one a removed tree gives
    and _subagent_frame_cached keyed as it is, and the chat's Agent head (_stamp_agents) carries no steps. A caller that
    passes a faults list (_awaiting_nest) is told the reason; these are not. Transient: nothing is memoized under the
    fault, so the first lookup after it clears resolves the file and the head carries its steps again, and
    _subagent_frame_cached's key moves with the resolved file, so the frame it cached under the fault is rebuilt rather
    than served (asserted without clearing the frame cache). This case is the
    named witness of the texts that state it (_subagent_tree's and _SubagentTreeUnreadable's docstrings and
    docs/reference.md's memos paragraph), which until this change said no reader answers an absent-shaped tree under a
    fault. Green before the change too, by design: it characterizes what the code does (the base kernel showed the same
    frame, and memoized the miss as well). The follow-up fix that has the viewer state the fault (option (a)) turns it red
    and replaces it. Driven in the notes-dir probe's shape, the workflow agent's file one level down with no standing
    resolution, under a real EACCES (the session directory at mode 000; skipped as root, whom permission bits do not
    bind) and under an EIO by mock on the root's own lstat."""

    ERR = {"eio": "OSError", "eacces": "PermissionError"}   # the type name the walk passes to a caller's faults
    MISSING = "The transcript file for agent %s is missing"   # the opening of build_subagent's absent sentence

    def setUp(self):
        super().setUp()
        self.wf_key = (str(self.tpath), AID_WF)
        km._SUBAGENT_FILE_CACHE.pop(self.wf_key, None)       # no standing resolution: the probe's shape
        self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, self.wf_key, None)
        self.addCleanup(km._SUBAGENT_FRAMES.pop, (SID, AID_WF), None)
        path = str(self.tpath)
        p = mock.patch.object(km, "_path_of", lambda sid, now=None: path if sid == SID else None)
        p.start()
        self.addCleanup(p.stop)
        self.agent_file = self.wf / ("agent-%s.jsonl" % AID_WF)   # one tool call, so a readable file gives the head a step
        self.agent_file.write_text(json.dumps({
            "type": "assistant", "timestamp": "2026-09-10T10:00:00.000Z", "uuid": "u-viewer-1",
            "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "toolu_viewer_0001", "name": "Read", "input": {"file_path": "README.md"}}]}}) + "\n")
        _age(str(self.subdir))

    def _head_steps(self):
        """Whether the chat's Agent head for AID_WF carries steps (_stamp_agents, a foreground launch)."""
        ev = {"name": "Agent", "agentId": AID_WF}
        km._stamp_agents({"toolu_viewer_head": ev}, str(self.tpath), None, None)
        return bool(ev.get("agentSteps"))

    def _views(self):
        """What the person sees for AID_WF now: the viewer frame build_subagent answers, the key and serialized frame
        _subagent_frame_cached holds for it, and whether the Agent head carries steps."""
        km._SUBAGENT_FRAMES.pop((SID, AID_WF), None)
        fr = km.build_subagent(SID, AID_WF, 0, live_map={})
        _fr, pre = km._subagent_frame_cached(SID, AID_WF, 0, live_map={})
        return fr, km._SUBAGENT_FRAMES[(SID, AID_WF)][0], pre, self._head_steps()

    def _viewer(self, how):
        root, path = str(self.subdir), str(self.tpath)
        with self._unreadable(root, how):
            faults = []
            self.assertIsNone(km._subagent_file(path, AID_WF, faults), "premise: the file is under the one tree the walk could not read")
            self.assertEqual(faults, [self.ERR[how]], "premise: a caller that passes a faults list is told the lookup could not be made")
            self.assertIsNone(km._subagent_file(path, AID_WF),
                              "a caller that passes no faults list is answered a bare None, the answer an absent file gets")
            fr, key, pre, steps = self._views()
            self.assertNotIn(self.wf_key, km._SUBAGENT_FILE_CACHE, "nothing is memoized under the fault, so the answer is transient")
        self.assertEqual(km._subagent_file(path, AID_WF), self.agent_file, "the fault cleared: the next lookup resolves the file")
        self.assertTrue(self._head_steps(), "and the Agent head carries the file's step again")
        _fr, pre_after = km._subagent_frame_cached(SID, AID_WF, 0, live_map={})   # no pop: the frame cached under the fault stands
        key_after = km._SUBAGENT_FRAMES[(SID, AID_WF)][0]
        self.assertNotEqual(key_after, key,
                            "the fault cleared: _subagent_frame_cached's key moves with the resolved file (its stat and its "
                            "sidecar), so the frame it cached under the fault is rebuilt, not served (%r, then %r)"
                            % (key[1:], key_after[1:]))
        self.assertNotIn(self.MISSING % AID_WF, pre_after,
                         "and the rebuilt viewer frame no longer says the transcript is missing")
        shutil.rmtree(str(self.subdir))                        # the tree removed: the absent answer the fault's views equal
        fr0, key0, pre0, steps0 = self._views()
        self.assertTrue(str(fr0.get("error", "")).startswith(self.MISSING % AID_WF),
                        "premise: the removed tree's viewer frame is the missing-transcript sentence: %r" % (fr0,))
        self.assertEqual(pre, pre0,
                         "the viewer frame under the unreadable tree, serialized, equals the removed tree's: it says the transcript "
                         "is missing (%r); the follow-up that has the viewer state the fault makes these differ" % (fr.get("error"),))
        self.assertEqual(json.dumps(fr), json.dumps(fr0), "build_subagent's frame, byte for byte")
        self.assertEqual(key, key0, "and _subagent_frame_cached keys it as it keys the removed tree's")
        self.assertEqual((steps, steps0), (False, False), "the Agent head carries no steps under the fault, as for the removed tree")

    def test_the_viewer_says_the_transcript_is_missing_and_the_agent_head_has_no_steps_while_the_tree_cannot_be_read_eio(self):
        self._viewer("eio")

    def test_the_viewer_says_the_transcript_is_missing_and_the_agent_head_has_no_steps_while_the_tree_cannot_be_read_eacces(self):
        self._viewer("eacces")


if __name__ == "__main__":
    unittest.main()
