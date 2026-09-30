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
real EACCES from its parent) is a read that did not happen, not an absent tree: nothing is popped, nothing is noted
absent, no counter moves, the sidecar map answers its standing map unheld, the feed key's component is the
unreadable marker whatever entry stands, and the next call after the fault clears validates the standing entry;
(11) such a fault excludes its own tree
from the agent-file walk and nothing else: a file under a readable sibling's tree is found, memoized and answered with no
fault passed to the caller while the own tree, a sibling sorted before it or an entry whose type cannot be read faults,
and with the file nowhere the lookup answers None with the fault and memoizes nothing; (12) the fail-closed answers
beside the own root's (FailClosedRoads): a sibling's tree that cannot be read and a project directory that cannot be
listed each reach the caller as a fault, memoize nothing and tell a running chat build the read is unreadable, whose
recorded key the next signature's re-stat differs from once the fault clears, when the lookup recovers; the feed key's
component for an unreadable root is the unreadable marker with no entry standing and with one holding an unvouched
identity (a lone root's entry or one that lists more), as it is with a vouched entry standing in (10); and ENOTDIR
at a root is absence (a
boundary guard); (13) what a reader that passes no faults list shows while the tree the agent's file lies under cannot
be read, with no resolution standing (ViewerUnderAnUnreadableTree): the viewer's missing-transcript frame, equal to a
removed tree's and keyed as it is, and an Agent head with no steps, both gone once the fault clears: the lookup then
resolves the file, the head carries its step, and the frame cache's key moves, so the frame cached under the fault is
rebuilt (a characterization, the witness of the texts that state it); (14) a lookup that could not be made answers the memo's standing resolution
only when that path lies under what the walk could not read (StandingResolutionUnderAFault): a standing path under a
tree the walk read in full, a sibling's or the own tree before a listing that faults or beside an own session directory
entry that cannot be typed, is not answered, and one under
the tree that faults, or under a sibling the listing could not name, is; (15) a place below a tree's root that cannot
be read, its root reading (FaultBelowTheRoot): a workflows/ or workflow directory whose listing fails, a workflow
directory whose own lstat fails and an entry whose type cannot be read each exclude that place from the agent-file
walk, so with the file under it the lookup answers None with the fault, memoizes nothing and walks again at the next
lookup, the chat build's record re-arms once the fault clears, the lookup then finds the file, and a standing
resolution under the place is answered and left standing; (16) the agent-file walk's reads that decide whether a
place holds the file read the error (FaultOnTheWalksOwnRead): a candidate file whose lstat fails for a reason other
than ENOENT and ENOTDIR (in a directory that can be listed but not searched, or an EIO), in a workflow directory and at
the flat place, and a project-directory entry whose os.stat fails outside _REG_MISSING_ERRNOS, each with the file there
alone, answer None with the fault, memoize nothing, walk again at each lookup and note the place unreadable, and once
the fault clears the lookup finds the file; a standing resolution beside a faulted candidate is not answered; a file
found past such a fault is answered as before, and absent candidates, links at a candidate and links as an entry read
as absence or not a directory, with no fault; a candidate faulted in a sibling's tree is excluded as one in the own
tree is, and the search goes on through a tree's other candidates past a faulted one; and a fault on the lstat of a
symlinked subagents/ itself (by mock) excludes the own root, so the file behind the link is not taken, and after the
fault clears the lookup is a miss, memoized, as a symlinked subagents/ always is; and on a tree held earlier in the
scope, under a real EACCES, the root's strict realpath is the read that meets the fault and no candidate path is
resolved; (17) _find_agent_file's two os.path.realpath calls read a failed resolution as the walk's own fault, one
behaviour on every interpreter (RealpathFailureIsAFault): a sibling root's failure excludes that sibling and the
holder's file is found past it, the own root's and a candidate's each answer None with the fault and memoize nothing, a
place with no tree stays a miss with no fault, and a path gone between two reads is a fault where it was found, a miss
at the next lookup (a candidate removed between its lstat and its resolution, and a root removed on disk while a scope
holds its pair, in that scope); (18) a None the walk notes for a place whose stamp it took as real (a live link whose
note's stat or identity lstat failed, or which changed between them) is never memoized, so the tab is rebuilt at most
once (DowngradedNoneIsNotMemoized); (19) a witness of a stated residual, not a fix: under a filesystem clock coarser
than an entry change, the memo's hit replays keys the walk took before a change made in its stamp's tick
(CoarseClockTick).
Red-first on (1), the jobs-pass half of (6), (9) and (10); (11), (14) and (15) are red under the mutants their classes
name, and (16) red first under a kernel whose walk reads a candidate through os.path.isfile (its entry pin on 3.14t
alone), its (8) control on the root's strict raise under a root realpath that is unstrict (its class's M4); (12) is red
under a mutant per road, its unvouched-entry marker cases under two; (13) is green before its change by design and red
under the follow-up that has the viewer state the fault; (17) is red under its class's M0 (both calls as the code before
this change made them) on every interpreter except its sibling case, red there on 3.10 to 3.12 alone, and its two
absence boundaries, green by design; (18) is red under the mutant its class names; (19) is green by design and red
under the follow-up that would close the residual.
Synthetic fixtures only: placeholder ids, invented text, a temp directory."""
import contextlib
import errno
import json
import os
import shutil
import stat
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
RACY_NS = km._SUBAGENT_DIR_RACY_NS                 # the real window, reopened by the tests that need it


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
        # seconds. The served-path tests run with the window closed; the tests that need the window reopen the real constant
        # (RACY_NS): the window's own tests and the feed key's marker case for an entry stored within it.
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
        # and scoped, and a symlink in the root's place, live or dangling, is such a read.
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
    is a read that did not happen, not an absent tree: nothing is popped, nothing is noted absent, no counter moves, the
    sidecar map answers its standing map unheld, the feed key's component is the unreadable marker and never the
    standing entry (so a feed entry derived under the fault is never served after it clears:
    tests/test_feed_session_memo.py FeedEntryDerivedUnderARootFault), and the next call after the fault clears reads
    the disk again and finds the
    entry standing (a validation, never a walk). This is the second of the two rules in which the tree read here
    differs from upstream's: #1822's _subagent_tree_sample takes every OSError on the root's lstat for absence and pops,
    and that sample's `except` applied at this head as a mutant reds both cases on the entry popped under the fault.
    Red at the code before this change (fork main with romp-on/romp PR #1822 and fork PR #910), whose
    _subagent_tree_sample takes every OSError on the root's lstat for absence: an EIO pops the entry, answers (), () and
    notes the tree absent to the chat build, which shows no subagents until the fault clears; the module's cases there
    drive only ENOENT at the root. Two faults:
    an EIO by mock on os.lstat of the root alone (every other path reads) and a REAL
    EACCES from the parent directory without search permission (nothing under it reads either; skipped as root, whom
    permission bits do not bind). The scope is open under the fault, so "nothing held" is executed, not implied, and it is
    the WHOLE scope that is compared, its three slots (subagent_trees, subagent_stamps, subagent_launches) each empty
    after the tree reads: a pin over one slot is narrower than "no scope entry", and a stamps entry recorded on the raise
    left a trees-only pin green. After the
    agent-file lookup under the real EACCES
    the whole scope is compared again, by equality, to the one entry the walk holds: the project directory's stamp, since
    a fault excludes its own tree from the walk and nothing else, so the walk goes on to list the project directory
    (FaultExcludesItsOwnTree below executes the exclusion)."""

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
        self.assertEqual(km._subagent_dirs_ident(SID, root), ((root,), (km._TREE_UNREADABLE,)),
                         "the feed key's component is the unreadable marker, never the standing entry (a feed entry derived under "
                         "the fault would be served after it clears) and never the missing root's (d,), (None,)")
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
                             "whose stamp it takes as an own stamp; under the parent at mode 000 every "
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
    """A fault excludes the tree that raised it and nothing else. An agent's file under a readable sibling session's tree
    (a /clear fork's fsid) is found, memoized and answered with no fault passed to the caller while another tree the walk
    looks through cannot be read: the own subagents tree, a sibling's sorted before the holder, or a project-directory
    entry sorted before the holder whose type cannot be read (its os.stat raising). The code before this change takes
    every such fault for absence and the walk goes on, and it cannot run these cases, since its _subagent_file takes no
    `faults` argument. Each found-past case is red under a mutant whose _subagent_file gate discards a found file
    whenever any fault occurred (`if failed:` for `if failed and found is None:`), which answers None with the fault and
    memoizes nothing (the viewer would say the transcript is missing, the awaiting box attribute no launches, the Agent
    card show no steps) for as long as the unrelated tree stays unreadable. Each road is driven under a real EACCES (a
    directory at mode 000; skipped as root, whom permission bits do not bind) and under an EIO by mock. The walk reads an
    entry's type by os.stat on every interpreter (the code before this change reads it with Path.is_dir, whose raise
    depends on the interpreter, so the entry cases would have no raise to drive on some), and each entry case asserts
    first that the entry's os.stat raises with an errno outside _REG_MISSING_ERRNOS (_entry_stat_premise). Two
    controls, green by design: an unreadable sibling sorted after the holder is never reached, and with the file nowhere (no holder) the lookup answers None with the fault, memoizes nothing and tells the
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
                  "that could not be read")

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
                        "the file under the readable sibling after it is found (a walk that took the raise for the "
                        "listing's fault would answer None)")

    def test_an_entry_whose_type_cannot_be_read_sorted_before_the_holder_eio_leaves_its_file_found_and_memoized(self):
        self._untyped_entry_before_holder("eio")

    def test_an_entry_whose_type_cannot_be_read_sorted_before_the_holder_eacces_leaves_its_file_found_and_memoized(self):
        self._untyped_entry_before_holder("eacces")

    # ── controls, green by design ────────────────────────────────────────────────────────────────────────────────────
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
    """The fail-closed answers beside UnreadableRoot's: the agent-file walk's fault on
    a sibling's tree, the project directory's listing that could not be made, the walk's _TREE_UNREADABLE note to a running
    chat build on both of those roads, _subagent_dirs_ident's marker for an unreadable root (its answer whatever entry
    stands), driven here with no memo entry standing and with one holding an unvouched identity, and ENOTDIR at a root,
    which is absence. UnreadableRoot above reaches the own root alone, with its entries standing, and pins the marker
    with a vouched entry standing. None of these fault answers exists in the code before this change, and it
    cannot run the cases that drive them (its _subagent_file takes no `faults` argument and it has no _TREE_UNREADABLE),
    which is no red for the reason; the ENOTDIR guard is green there by design. Each case is red under a mutant that
    takes its road's fault for absence or drops its
    answer: the sibling's fault not recorded, the listing's fault not recorded, the walk's note not made, the marker
    answered as the missing root's (None,) (red on the three marker cases), the standing entry answered whatever
    identities it holds (red on both unvouched-entry cases), only the lone root's unvouched entry answered the marker
    (red on the multi-directory case), ENOTDIR moved to the unreadable side. A standing entry answered when it holds no
    unvouched identity reds none of the three marker cases; its reds are UnreadableRoot's two cases and
    tests/test_feed_session_memo.py FeedEntryDerivedUnderARootFault.
    The sibling and listing cases each assert, under the fault, the caller's faults, no memo entry and the note under
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
        (UnreadableRoot drives it with a vouched entry standing): (d,) with identity _TREE_UNREADABLE, never the missing
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

    def test_the_feed_keys_component_for_an_unreadable_root_whose_entry_holds_an_unvouched_identity_is_the_unreadable_marker(self):
        """_subagent_dirs_ident for a root whose lstat fails for a reason other than absence while its memo entry holds an
        unvouched (None) identity: a lone subagents root created now and read once is stored ((d,), (None,)) by the racy
        mask (the real window reopened), which is also the key a missing root answers. Under an EIO by mock on the root's
        lstat the component is (d,) with identity _TREE_UNREADABLE, never that entry, so an unreadable tree is not keyed
        as an absent one. The marker is the answer for every fault, whatever entry stands; red under a mutant that
        answers a standing entry whatever identities it holds."""
        root = str(self.proj / SID_AFTER / "subagents")
        os.makedirs(root)
        self.roots.append(root)
        with mock.patch.object(km, "_SUBAGENT_DIR_RACY_NS", RACY_NS):
            km._subagent_dirs(root)
        missing = str(self.proj / SID_BEFORE / "subagents")
        self.assertEqual((km._SUBAGENT_TREES.get(root), km._subagent_dirs_ident(SID, missing)),
                         (((root,), (None,)), ((missing,), (None,))),
                         "premise: the lone root's entry, stored within the racy window, is ((d,), (None,)), the shape of a missing "
                         "root's component")
        with self._unreadable(root, "eio"):
            got = km._subagent_dirs_ident(SID, root)
        self.assertEqual(km._SUBAGENT_TREES.get(root), ((root,), (None,)), "premise: the entry stood under the fault")
        self.assertEqual(got, ((root,), (km._TREE_UNREADABLE,)),
                         "the feed key's component for an unreadable root whose entry holds an unvouched identity: %r; keyed on the "
                         "unreadable marker, not the entry, which equals the missing root's ((d,), (None,))" % (got,))

    def test_the_feed_keys_component_for_an_unreadable_root_whose_multi_directory_entry_holds_an_unvouched_identity_is_the_unreadable_marker(self):
        """The same rule for an entry that lists more than the root: a subagents root and its workflows/ created now and
        read once are stored with unvouched (None) identities by the racy mask (the real window reopened), an entry that
        is not the missing root's key. Under an EIO by mock on the root's lstat the entry still stands and the component
        is (d,) with identity _TREE_UNREADABLE, never that entry: _subagent_tree_sample never serves an entry holding an
        unvouched identity as a hit, and neither does the feed key's answer under a fault, which is the marker whatever
        entry stands. Red under a mutant that answers the marker for the lone root's such entry alone and every other
        standing entry as it stands (`e.entry != ((d,), (None,))` the condition for answering the entry)."""
        root = str(self.proj / SID_AFTER / "subagents")
        child = os.path.join(root, "workflows")
        os.makedirs(child)
        self.roots.append(root)
        with mock.patch.object(km, "_SUBAGENT_DIR_RACY_NS", RACY_NS):
            km._subagent_dirs(root)
        entry = km._SUBAGENT_TREES.get(root)
        self.assertEqual((entry and entry[0], entry is not None and None in entry[1], entry != ((root,), (None,))),
                         ((root, child), True, True),
                         "premise: the entry lists the root and workflows/, holds an unvouched identity, and is not the lone "
                         "root's ((d,), (None,)): %r" % (entry,))
        with self._unreadable(root, "eio"):
            got = km._subagent_dirs_ident(SID, root)
        self.assertIs(km._SUBAGENT_TREES.get(root), entry, "premise: the entry stood under the fault")
        self.assertEqual(got, ((root,), (km._TREE_UNREADABLE,)),
                         "the feed key's component for an unreadable root whose multi-directory entry holds an unvouched identity: "
                         "%r; keyed on the unreadable marker, not the entry" % (got,))

    def test_enotdir_at_the_root_is_absence_answered_empty_with_the_entry_popped_a_boundary_guard(self):
        """A boundary guard, green by design: ENOTDIR on the root's own lstat (a regular file where the session
        directory above the root should be) is absence, answered ((), ()) with the memo entry popped, as ENOENT is
        (upstream's pop, which drops nothing an open scope holds). ENOTDIR is absence in the code before this change and
        here, so this case cannot fail at the code before this change; it turns red if ENOTDIR moves to the unreadable
        side (a raise, the entry kept)."""
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
    the walk read in full is disproven by that read, and the answer is None with the fault. RED under a mutant whose
    _subagent_file answers the standing path whenever the lookup faulted (the _subagent_walk_excluded test dropped from
    its gate): AID_FORK's file, memoized under the holder sibling's tree and since moved into another sibling's tree
    that cannot be read, is answered at its old path, which no longer exists, because the other tree faulted; and a
    file memoized under the own tree and gone from it is answered at its old path while the project directory cannot
    be listed, although the listing excludes only the siblings it could not name and the walk reads the own tree
    before it. Controls, green by design: a standing path under the very tree that faults, or under a sibling while the
    listing faults, is answered with the fault, since the walk could not look there. A standing path under the own tree is
    not answered when the own session directory's entry cannot be typed (its os.stat raising EIO by mock), since the
    entry's exclusion keeps the own tree as the listing's does; red when that exclusion keeps nothing (a kernel that
    drops `kept=str(own)` there), which answers the stale path with the fault. Each fault is driven under a real
    EACCES (skipped as root, whom permission bits do not bind) and under an EIO by mock (the listing's EIO variant
    skipped on 3.10, whose pathlib lists through the os.listdir it bound at import)."""

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

    def test_a_standing_path_under_the_own_tree_is_not_answered_when_the_own_session_directorys_entry_cannot_be_typed_eio(self):
        """AID's file found at the own flat place and memoized, then moved out of the project directory (the own
        subagents directory's stamp moves, so the next lookup walks), and the own session directory's os.stat, the read
        the walk types that project-directory entry by, raising EIO by mock (an EIO or ESTALE on the directory's own
        attributes; an EACCES there would come from the project directory's search permission and fail the own tree's
        read as well). The walk reads
        the own tree in full before the listing and the file is not there, so the standing path is disproven: None with
        the fault, the stale path not answered, nothing memoized. RED when the entry's exclusion keeps nothing (a kernel
        whose entry exclusion drops `kept=str(own)`): it excludes the own tree the walk has just read, and the lookup
        answers the stale path with the fault. Once the fault clears the lookup is a real
        miss, memoized, with no fault."""
        key = (str(self.tpath), AID)
        km._SUBAGENT_FILE_CACHE.pop(key, None)
        self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, key, None)
        own_file = self.subdir / ("agent-%s.jsonl" % AID)
        self.assertEqual(km._subagent_file(str(self.tpath), AID), own_file, "premise: found at the own flat place and memoized")
        entry = km._SUBAGENT_FILE_CACHE[key]
        os.rename(str(own_file), os.path.join(self.td, own_file.name))      # the file leaves the own tree and the project
        sess = str(self.subdir.parent)
        real = os.stat

        def eio(p, *a, **k):
            if not isinstance(p, int) and os.fsdecode(p) == sess:
                raise OSError(errno.EIO, "input/output error")
            return real(p, *a, **k)
        with mock.patch.object(os, "stat", eio):
            with self.assertRaises(OSError, msg="premise: the own session directory's os.stat raises under the mock") as cm:
                os.stat(sess)
            self.assertNotIn(cm.exception.errno, km._REG_MISSING_ERRNOS,
                             "premise: a fault, not an absence-shaped errno (%r)" % (cm.exception,))
            faults = []
            got = km._subagent_file(str(self.tpath), AID, faults)
        seen = (got and os.path.relpath(str(got), self.td), faults, km._SUBAGENT_FILE_CACHE.get(key) is entry)
        self.assertEqual(seen, (None, ["OSError"], True),
                         "(the answer, faults, the memo entry untouched) = %r; keyed on (None, ['OSError'], True): the walk read "
                         "the own tree in full and the file is not there, so the standing path under it is disproven whatever the "
                         "own session directory's entry stat answered (an entry exclusion that keeps nothing excludes the own tree "
                         "and answers the stale path, which no longer exists)" % (seen,))
        after_faults = []
        got = km._subagent_file(str(self.tpath), AID, after_faults)
        self.assertEqual((got, after_faults, km._SUBAGENT_FILE_CACHE[key][1]), (None, [], None),
                         "the fault cleared: the file is nowhere, a real miss with no fault, memoized")

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
    differs from the next signature's re-stat (the tab is rebuilt) and the lookup finds the file. RED under a kernel
    whose tree read tells no reader of a failed listing below the root, as in the code before this change: the walk
    finds no file, takes that for a miss and memoizes it on stamps a chmod or a transient EIO does not move, and every
    lookup after the fault clears is answered the memoized miss until a stamped directory changes. The tree read's two
    other shapes have their cases: the workflow directory whose own lstat fails (workflows/ at 0o644
    for a real EACCES, an EIO by mock on its lstat) and the workflow directory's entry whose type cannot be read (an EIO
    on is_dir by a wrapped os.scandir), each asserting None, the fault, nothing memoized, the (place, _TREE_UNREADABLE)
    note by equality on the workflow directory and the file found once the fault clears; red under a kernel that drops
    that shape's report (the EACCES variant on the place's equality,
    since the candidate's lstat in the unsearchable workflows/ faults too and is noted instead). The chat record for the
    place holds the disagreement of two reports (_chat_build_deps): the walk noted it unreadable, and the tree read noted
    it under its own key, which a chmod or a cleared EIO does not move. A lookup alone re-arms under a record that keeps
    the first key as well, since the walk's _TREE_UNREADABLE is reported before the replayed tree note; a chat build that
    reads the sidecar map before its lookup (_stamp_agents) reports the tree read's key first, and its case re-arms only
    through the disagreement. A standing resolution under the place that faults is answered with
    the fault and left standing; that case stays green under the kernel above, since the candidate's own lstat in the
    unsearchable workflow directory faults and excludes it, and is red under a kernel whose _subagent_file memoizes the
    walk's miss whatever faulted (its fault gate removed), which replaces the resolution in the memo. A control, green
    by design: a file under a readable sibling is found past the fault below the own root, memoized and answered
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

    # ── the tree read's two other shapes ──────────────────────────────────────────────────────────────────────────────
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

    def test_a_chat_build_that_reads_the_sidecar_map_before_its_lookup_rebuilds_its_tab_through_the_disagreement_eio(self):
        """The live road of _chat_build_deps' two-key rule. A chat build reads the sidecar map before it looks an agent up
        (_stamp_agents, as build_session does). Under an EIO by mock on workflows/'s listing, the map's tree read notes
        workflows/ under the stat key of its read; the lookup's walk excludes that place and notes it under
        _TREE_UNREADABLE. Premise, from the build's reports for workflows/ in order: the first is a stat key and
        _TREE_UNREADABLE is among the later ones. Once the fault clears, the key the build
        recorded for workflows/ differs from the next signature's re-stat, so the tab is rebuilt, and the lookup finds the
        file. Red under a record that keeps a path's first key: it records the tree read's stat key, which the EIO did not
        move, and the re-stat equals it."""
        km._SUBAGENT_TREES.pop(str(self.subdir), None)             # no standing tree entry: the fault is met by a walk
        ev = {"name": "Agent", "agentId": AID_WF}                   # a foreground launch's Agent head
        deps = {"task_outs": [], "postal_any": False}
        with self._below("eio-workflows") as place:
            km._chat_dep_scope.deps = deps
            try:
                km._stamp_agents({TU_WF: ev}, str(self.tpath), None, None)
            finally:
                km._chat_dep_scope.deps = None
        reports = [k for p, k in deps["task_outs"] if p == place]
        self.assertTrue(reports and isinstance(reports[0], tuple) and km._TREE_UNREADABLE in reports[1:],
                        "premise: the build's reports for workflows/, in order, are the sidecar map's stat key first and the walk's "
                        "_TREE_UNREADABLE after it: %r" % (reports,))
        self.assertNotIn(self.wf_key, km._SUBAGENT_FILE_CACHE, "premise: the lookup under the fault memoized nothing")
        km._chat_dep_scope.deps = {"task_outs": list(deps["task_outs"]), "postal_any": False}
        try:
            rec = km._chat_build_deps(SID, {"events": []})
        finally:
            km._chat_dep_scope.deps = None
        recorded = dict(rec["task_outs"]).get(place, "unrecorded")
        restat = dict(km._chat_sig_deps(SID, rec)[0]).get(place, "unrecorded")
        self.assertNotEqual(recorded, restat,
                            "the fault cleared: the key the build recorded for workflows/, %r, against the next signature's re-stat, "
                            "%r; keyed on a difference, so the tab is rebuilt (a record that keeps the first key holds the sidecar "
                            "map's stat key, which the EIO did not move, and equals the re-stat)" % (recorded, restat))
        got, faults, _notes = self._lookup_wf()
        self.assertEqual((got, faults), (self.target, []), "the fault cleared: the next lookup finds the file, with no fault")

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
    """The agent-file walk's reads that decide whether a place holds the file read the error, never a boolean helper that
    answers a fault as False. A candidate file, the own place included,
    is read by os.lstat: ENOENT and ENOTDIR are absence, any other errno a fault that excludes the candidate path. A
    project-directory entry's type is read by os.stat: _REG_MISSING_ERRNOS reads as not a directory, any other errno a
    fault that excludes the entry. The own subagents directory's type is read by os.lstat before the flat check: a
    symlink there is a symlinked subagents/, through which nothing is taken; ENOENT and ENOTDIR are no link; any other
    errno is a fault that excludes the own root, and nothing at the own place is taken or noted (case (5)).
    Cases (1) to (3), RED FIRST under a kernel whose walk reads a candidate through os.path.isfile, which answers False
    on EACCES and EIO on every interpreter, and an entry through Path.is_dir, which answers False on any error from 3.14
    (3.10 to 3.13 raise, and the entry is excluded already), with the `faults` argument this change gives
    _subagent_file: the fault is taken for absence, the miss memoized on stamps a chmod or a cleared EIO never moves,
    and the lookup after the fault clears is answered the memoized miss. The real shape: a directory that can be listed but not searched (read without execute) holding only
    files, whose listing succeeds and types its entries with no child to lstat, so the tree read reports no fault, while
    the candidate's lstat raises EACCES. Each of those pins asserts, under the fault, None, the fault passed to the
    caller, nothing memoized, a walk per lookup and the (place, _TREE_UNREADABLE) note by equality on the place, and
    after the fault clears, the memo entry absent before the next lookup and the file found. The EIO pins mock os.stat
    and os.lstat both for the candidate alone, as a real EIO fails every stat of the path: a mock of the lstat alone is
    never seen by os.path.isfile, and the red would be for another reason. The entry pin is red under that kernel on
    3.14t alone; on 3.10 its EIO variant fails there too, but only because 3.10's pathlib stats through the os.stat it
    bound at import and never sees the mock, which is not the defect; elsewhere it is green under that kernel and
    here, the control that the new partition keeps what pathlib did before 3.14. Case (5)'s pin and its control state
    their own red and green. Case (6) drives the candidate's fault at the sibling tree's call of _find_agent_file, as
    (1) and (2) drive it at the own tree's, through the same assertions, red under the os.path.isfile kernel (the miss
    memoized). The controls and boundaries at the end are green here by design, each saying so, and all but the (8)
    control are green under that kernel too; the two (7) controls find the file in a later directory of the same tree
    past a faulted candidate, and the (8) control drives the containment check's claim on a tree held earlier in the
    scope under a real EACCES (_subagent_file_walk's docstring states the claim): the root's strict realpath is the read
    that meets the fault, and no candidate path is resolved. Its assertion on that raise is red under a root realpath
    that is unstrict, as the code before this change made it (M4 below). The EACCES cases skip as root, whom permission
    bits do not bind.

    Named mutants, each applied alone to kernel/kernel.py and red on the case named (each run recorded outside the repo
    with its command, interpreter and head):
    - M1, the own subagents directory's type read by os.path.islink(own) again, which answers False on a fault: case
      (5)'s pin, on the file taken through the link;
    - M2, a no-op exclude (`lambda w, e: None`) at the sibling tree's call of _find_agent_file: case (6), both
      variants, on the miss memoized under the fault and served after it cleared (omitting the keyword-only `exclude`
      there raises TypeError, which the existing sibling cases catch, so a no-op or wrong handler is the mutant);
    - M3, `return None` in place of the `continue` after a faulted candidate's exclusion in _find_agent_file: both (7)
      controls, on the file answered None with the fault;
    - M4, the root's realpath in _find_agent_file unstrict (strict=True dropped there): the (8) control, on the root's
      realpath raising nothing; and M4 with each candidate resolved by an unstrict realpath before its lstat: the (8)
      control on a realpath taken of a candidate path through the faulted place."""

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
        path is disproven: None with the fault, the standing entry left as it was. Red under a kernel that reads the
        candidate through os.path.isfile, which swallows the EIO (no fault, the miss memoized), and under one that excludes the candidate's
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

    # ── (5) the own subagents directory's type, read for its error ──────────────────────────────────────────────────
    def _symlinked_subagents(self):
        """subagents/ replaced by a symlink to a directory elsewhere holding what it held, AID's flat file among them:
        (the link's path, the flat place through it)."""
        target = Path(self.td) / "linked-subagents"
        os.rename(str(self.subdir), str(target))
        self.subdir.symlink_to(target)
        _age(str(target))
        own, ap = str(self.subdir), str(self.subdir / ("agent-%s.jsonl" % AID))
        self.assertTrue(os.path.islink(own) and os.path.isfile(ap),
                        "premise: subagents/ is a symlink to a directory holding AID's flat file")
        return own, ap

    def _after_the_fault(self, what):
        """AID's lookup once the fault has cleared: None with no fault and the miss memoized, since a file behind a
        symlinked subagents/ is never taken."""
        got, faults, _notes = self._looked_up(AID)
        self.assertEqual((got, faults), (None, []), "%s cleared: a file behind a symlinked subagents/ is never taken, so the "
                                                    "lookup is a miss with no fault" % what)
        self.assertIsNone(km._SUBAGENT_FILE_CACHE.get(self.flat_key, (None, "unset"))[1], "%s cleared: the miss is memoized" % what)

    def test_a_fault_on_the_own_subagents_directorys_lstat_under_a_symlinked_subagents_directory_excludes_the_own_root_and_takes_nothing(self):
        """subagents/ a symlink to a directory holding AID's flat file, and os.lstat raising EIO for the own
        subagents directory's path alone (by mock: a non-root test cannot drive a fault on that lstat alone for real,
        since a real fault there, an EACCES from a parent, also fails the flat place's lstat and the own tree's read,
        which the control below drives). The walk reads the own subagents directory's type from that lstat, so the fault
        excludes the own root: None, faults ['OSError'], nothing memoized, and the running chat build told that the own
        root is unreadable, the place by equality; once the fault clears, None with no fault and the miss memoized. RED
        when the own subagents directory's type is read by os.path.islink(own) (M1), which answers False on the fault,
        so the flat check takes the file through the link with no fault, memoizes it and serves it after the fault
        clears."""
        own, ap = self._symlinked_subagents()
        real = os.lstat

        def eio(p, *a, **k):
            if not isinstance(p, int) and os.fsdecode(p) == own:
                raise OSError(errno.EIO, "input/output error")
            return real(p, *a, **k)
        with mock.patch.object(os, "lstat", eio):
            with self.assertRaises(OSError, msg="premise: the own subagents directory's lstat raises under the mock"):
                os.lstat(own)
            self.assertTrue(stat.S_ISREG(os.lstat(ap).st_mode),
                            "premise: the flat place's lstat, through the link, still finds a regular file: the mock reaches "
                            "the own subagents directory's path alone")
            got, faults, notes = self._looked_up(AID)
            memo = km._SUBAGENT_FILE_CACHE.get(self.flat_key)
        after, after_faults, _notes = self._looked_up(AID)
        rel = lambda p: p and os.path.relpath(str(p), self.td)
        seen = (rel(got), faults, memo and ("a memo entry answering", rel(memo[1])), rel(after), after_faults)
        self.assertEqual(seen, (None, ["OSError"], None, None, []),
                         "(the answer, faults and memo entry under the fault on the own subagents directory's lstat, then the answer "
                         "and faults once it cleared) = %r; keyed on (None, ['OSError'], None, None, []): the fault excludes the own "
                         "root, so nothing at the own place is taken or memoized, and a file behind a symlinked subagents/ is never "
                         "taken (a boolean read of that type, os.path.islink, answered False on the fault, so the flat check took the "
                         "file through the link, memoized it and served it after the fault cleared)" % (seen,))
        self.assertEqual([p for p, k in notes if k == km._TREE_UNREADABLE], [own],
                         "the running chat build is told the own root is unreadable, the place by equality: %r" % (notes,))
        self.assertIsNone(km._SUBAGENT_FILE_CACHE.get(self.flat_key, (None, "unset"))[1],
                          "the fault cleared: the miss is memoized")

    def test_control_a_real_eacces_on_the_own_subagents_directory_under_a_symlinked_subagents_directory_excludes_the_own_root_first(self):
        """The control, green by design whether the own subagents directory's type is read by os.path.islink or by an
        lstat whose error is read: the same world with the session directory at mode
        000 (a real EACCES from a parent; skipped as root, whom permission bits do not bind), which fails the own
        subagents directory's lstat, the flat place's and the own tree's read alike: None, faults ['PermissionError'],
        nothing memoized, the running chat build told that the own root is unreadable, and the walk's first exclusion the
        own root; once the mode is restored, None with no fault and the miss memoized."""
        if os.geteuid() == 0:
            self.skipTest("permission bits do not bind root: no EACCES to drive")
        own, ap = self._symlinked_subagents()
        sess = str(self.subdir.parent)
        os.chmod(sess, 0o000)                                     # restored in the finally, before tearDown removes the tree
        try:
            for p in (own, ap):
                with self.assertRaises(PermissionError, msg="premise: the real fault fails the lstat of %s" % os.path.relpath(p, self.td)):
                    os.lstat(p)
            got, faults, notes = self._looked_up(AID)
            memo = km._SUBAGENT_FILE_CACHE.get(self.flat_key)
            excluded = []
            km._subagent_file_walk(str(self.tpath), AID, excluded=excluded)
        finally:
            os.chmod(sess, 0o755)
        self.assertEqual((got, faults, memo), (None, ["PermissionError"], None),
                         "under the real EACCES: (answer, faults, memo entry); keyed on (None, ['PermissionError'], None)")
        self.assertEqual([p for p, k in notes if k == km._TREE_UNREADABLE], [own],
                         "the running chat build is told the own root is unreadable, the place by equality: %r" % (notes,))
        self.assertEqual(excluded[:1], [(own, None)], "the walk's first exclusion is the own root: %r" % (excluded,))
        self._after_the_fault("the mode is restored and the fault")

    # ── (6) a candidate in a sibling's tree ─────────────────────────────────────────────────────────────────────────
    @contextlib.contextmanager
    def _sibling_listable_unsearchable(self, hold, cand):
        """The holder sibling's subagents root `hold` at mode 0o644 inside the block (read without search: a real fault),
        its three premises asserted against that root: the listing succeeds and names the agent's file, the sibling tree's
        read reports no fault (its memo entry dropped after, so the lookup reads it), and the candidate's lstat raises
        PermissionError. The root must hold only files: a child directory (its workflows/) would fault on the tree read's
        lstat of it and be excluded through the walk's loop over the tree's own faults, another road."""
        if os.geteuid() == 0:
            self.skipTest("permission bits do not bind root: no EACCES to drive")
        os.chmod(hold, 0o644)
        try:
            self.assertIn(os.path.basename(cand), os.listdir(hold), "premise: the sibling root's listing succeeds and names the file")
            below = []
            km._subagent_tree(hold, faults=below)
            km._SUBAGENT_TREES.pop(hold, None)
            self.assertEqual(below, [], "premise: the sibling tree's read reports no fault, so it excludes nothing")
            with self.assertRaises(PermissionError, msg="premise: the candidate's lstat raises"):
                os.lstat(cand)
            yield
        finally:
            os.chmod(hold, 0o755)

    def _sibling_candidate(self, how):
        """AID_FORK's file at the top of the holder sibling's tree, and that candidate faulted: under the EIO by mock on
        both its stats, or (EACCES) with the sibling's workflows/ removed and its subagents/ at mode 0o644."""
        hold, holder_file = self._sibling(SID_HOLD, holder=True)
        cand = str(holder_file)
        if how == "eacces":
            shutil.rmtree(os.path.join(hold, "workflows"))
            _age(str(self.proj / SID_HOLD))
            fault = self._sibling_listable_unsearchable(hold, cand)
        else:
            fault = self._eio_on(cand)
        self._unmade_then_found(AID_FORK, fault, cand, self.ERR[how], holder_file)

    def test_a_candidate_in_a_siblings_tree_whose_every_stat_raises_eio_is_a_fault_with_nothing_memoized(self):
        """The candidate-fault exclusion at the sibling tree's call of _find_agent_file, which cases (1) and (2) drive
        only at the own tree's call. Red under M2, and under a kernel whose _find_agent_file reads the candidate with
        os.path.isfile: the miss memoized under the fault and served after it clears. Omitting the keyword-only
        `exclude` at that call raises TypeError, which the existing sibling cases
        catch, so the mutant is a no-op or wrong handler there."""
        self._sibling_candidate("eio")

    def test_a_candidate_in_a_siblings_tree_that_can_be_listed_but_not_searched_is_a_fault_with_nothing_memoized_eacces(self):
        """The real shape of the case above: the holder sibling's subagents/ at mode 0o644 holding only the file. Red
        under M2 and under the os.path.isfile kernel, as above."""
        self._sibling_candidate("eacces")

    # ── controls and boundaries, green here and under the os.path.isfile kernel by design ───────────────────────────
    def _found_past(self, fault):
        _hold, holder_file = self._sibling(SID_HOLD, holder=True)
        with fault:
            got, faults, notes = self._looked_up(AID_FORK)
        self.assertEqual((got, faults), (holder_file, []), "found under the readable sibling past the faulted candidate, no fault passed on")
        self.assertEqual(km._SUBAGENT_FILE_CACHE[self.fork_key][1], holder_file, "and memoized")
        self.assertNotIn(km._TREE_UNREADABLE, [k for _p, k in notes], "and nothing noted unreadable")

    def test_control_found_elsewhere_past_a_candidate_in_a_workflow_directory_that_cannot_be_searched_eacces(self):
        """Green by design, here and under a kernel that reads the candidate through os.path.isfile (which takes it for
        absent, and the walk goes on): a file found past a fault is answered the same."""
        cand = str(self.wf / ("agent-%s.jsonl" % AID_FORK))
        self._found_past(self._listable_unsearchable(str(self.wf), cand, False))

    def test_control_found_elsewhere_past_the_flat_place_in_a_subagents_directory_that_cannot_be_searched_eacces(self):
        """Green by design, here and under the os.path.isfile kernel, as the case above."""
        self._flat_only_files()
        ap = str(self.subdir / ("agent-%s.jsonl" % AID_FORK))
        self._found_past(self._listable_unsearchable(str(self.subdir), ap, False))

    def test_control_found_elsewhere_past_a_candidate_whose_every_stat_raises_eio(self):
        """Green by design, here and under the os.path.isfile kernel, as the cases above, in the nested and the flat place."""
        for cand in (str(self.wf / ("agent-%s.jsonl" % AID_FORK)), str(self.subdir / ("agent-%s.jsonl" % AID_FORK))):
            with self.subTest(cand=os.path.relpath(cand, self.td)):
                km._SUBAGENT_FILE_CACHE.pop(self.fork_key, None)
                shutil.rmtree(str(self.proj / SID_HOLD), ignore_errors=True)
                self._found_past(self._eio_on(cand))

    def _found_past_in_the_same_tree(self, fault):
        """AID_WF's lookup under `fault`, its file left in the own workflow directory, a later directory of the own tree
        than the faulted candidate: found, memoized, no fault passed on and nothing noted unreadable."""
        target = self.wf / ("agent-%s.jsonl" % AID_WF)
        with fault:
            got, faults, notes = self._looked_up(AID_WF)
        memo = km._SUBAGENT_FILE_CACHE.get(self.wf_key)
        rel = lambda p: p and os.path.relpath(str(p), self.td)
        seen = (rel(got), faults, memo and ("a memo entry answering", rel(memo[1])), [p for p, k in notes if k == km._TREE_UNREADABLE])
        self.assertEqual(seen, (rel(target), [], ("a memo entry answering", rel(target)), []),
                         "(the answer, faults, the memo entry, the places noted unreadable) = %r; keyed on the file found, no fault, "
                         "the file memoized and nothing noted: the search goes on through the tree's other candidates past a faulted "
                         "one (a search that stops at the faulted candidate answers None with the fault)" % (seen,))

    def test_control_found_in_a_later_directory_of_the_same_tree_past_the_flat_place_whose_every_stat_raises_eio(self):
        """(7) The search goes on through the same tree's other candidates after a faulted one: case (4)'s fixture
        without the move, the EIO by mock on both stats of the flat place
        subagents/agent-<AID_WF>.jsonl and the file left in the own workflow directory. The own root is the first of the
        tree's directories, so the faulted candidate comes first with no ordering premise. Green under a kernel that reads
        the candidate through os.path.isfile (which swallows the fault, and the loop goes on) and here by design; red
        under M3."""
        self._found_past_in_the_same_tree(self._eio_on(str(self.subdir / ("agent-%s.jsonl" % AID_WF))))

    def test_control_found_in_a_later_directory_of_the_same_tree_past_a_workflow_directory_that_cannot_be_searched_eacces(self):
        """(7), the real shape: a workflow directory at mode 0o644 holding only files, sorted before the one holding the
        file, its ordering premise asserted (the faulted directory before the holder in _subagent_tree's directories).
        Green under the os.path.isfile kernel and here by design; red under M3."""
        early = self.subdir / "workflows" / "wf_0000000000000001"
        early.mkdir()
        (early / "agent-a4444444444444444.jsonl").write_text("")          # another agent's file: the directory holds only files
        _age(str(self.subdir))
        cand = str(early / ("agent-%s.jsonl" % AID_WF))

        @contextlib.contextmanager
        def fault():
            with self._listable_unsearchable(str(early), cand, False):
                dirs, _stats = km._subagent_tree(str(self.subdir))
                km._SUBAGENT_TREES.pop(str(self.subdir), None)
                self.assertLess(list(dirs).index(str(early)), list(dirs).index(str(self.wf)),
                                "premise: the faulted directory comes before the holder in the tree's directories: %r"
                                % ([os.path.relpath(d, self.td) for d in dirs],))
                yield
        self._found_past_in_the_same_tree(fault())

    # ── (8) a tree held earlier in the scope, then a real EACCES from its parent ────────────────────────────────────
    def test_control_a_tree_held_earlier_in_the_scope_then_a_real_eacces_from_its_parent_resolves_no_candidate_path(self):
        """(8) The containment check's claim on the held-tree road (_subagent_file_walk's docstring), under a real
        EACCES: the own tree is read inside a cycle scope, so the scope holds its pair, and then the session directory
        goes to mode 000, so every read under it fails. The lookup's tree read is served the held pair and reads
        nothing, so _find_agent_file's realpath of the root does read through the faulted place; strict, it raises, and
        the tree is excluded. A candidate's realpath runs only after that candidate's lstat found a regular file, which a
        fault on the traversal prevents, so no realpath is taken of a candidate path. Keyed, by equality, on (None, the
        fault, nothing memoized, no realpath of a candidate path) and on the root's realpath raising PermissionError.
        The mode is restored and the scope closed inside the case, before tearDown removes the tree. Its first assertion
        is green by design; its second, the root's strict raise, is red under M4, a root realpath that is unstrict, as the
        code before this change made it (it answers the path unresolved and raises nothing, on every interpreter here,
        while the first assertion holds), and so under RealpathFailureIsAFault's M0. The case is also red under M4 with
        each candidate resolved before its lstat, on the first assertion (a realpath of a candidate path), and under
        RealpathFailureIsAFault's M1 (the root's raise unread, out of the lookup). Skipped as root, whom permission bits do
        not bind."""
        if os.geteuid() == 0:
            self.skipTest("permission bits do not bind root: no EACCES to drive")
        sess, root = str(self.tpath.with_suffix("")), str(self.subdir)
        real_rp = os.path.realpath
        calls = []

        def spied(p, *a, **k):
            try:
                out = real_rp(p, *a, **k)
            except OSError as e:
                calls.append((os.fsdecode(p), type(e).__name__))
                raise
            calls.append((os.fsdecode(p), None))
            return out
        _scope_open()
        try:
            km._subagent_tree(root)                             # a reader earlier in the scope: the own tree's pair held
            self.assertIn(root, km._live_scope.subagent_trees, "premise: the scope holds the own tree's pair")
            os.chmod(sess, 0o000)
            try:
                with self.assertRaises(PermissionError, msg="premise: the real fault, every read under the session directory"):
                    os.lstat(root)
                with mock.patch.object(os.path, "realpath", spied):
                    got, faults, _notes = self._looked_up(AID_WF)
            finally:
                os.chmod(sess, 0o755)
        finally:
            _scope_close()
        cands = [c for c in calls if c[0].endswith(".jsonl")]
        seen = (got, faults, self.wf_key in km._SUBAGENT_FILE_CACHE, cands)
        self.assertEqual(seen, (None, ["PermissionError"], False, []),
                         "(the answer, faults, memoized, the realpath calls on a candidate path) = %r; keyed on (None, the fault, "
                         "nothing memoized, none): the fault is met before any candidate is resolved (a kernel that resolves a "
                         "candidate before its lstat reads a path through the faulted place here)" % (seen,))
        self.assertEqual([c for c in calls if c[0] == root], [(root, "PermissionError")],
                         "the root's realpath calls, (path, the error it raised): %r; keyed on one, raising PermissionError: the "
                         "held pair spared the tree read, so the root's realpath is the read that meets the fault, and strict, it "
                         "raises (unstrict, it answers the path unresolved and the claim would rest on the candidates' lstats)"
                         % ([(os.path.relpath(p, self.td), e) for p, e in calls],))

    def _plain_miss(self, what):
        got, faults, notes = self._looked_up(AID_FORK)
        self.assertEqual((got, faults), (None, []), "%s: a miss, with no fault" % what)
        self.assertIsNone(km._SUBAGENT_FILE_CACHE.get(self.fork_key, (None, "unset"))[1], "%s: and the miss is memoized" % what)
        self.assertNotIn(km._TREE_UNREADABLE, [k for _p, k in notes], "%s: and nothing noted unreadable" % what)

    def test_boundary_an_absent_candidate_is_a_miss_memoized_with_no_fault(self):
        """The absence side, green here and under the os.path.isfile kernel by design: ENOENT on every candidate (no
        file anywhere) is an ordinary
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
        """Green here and under the os.path.isfile kernel by design: the walk never takes a symlink, and its lstat of
        one succeeds, so a looping, a
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
        """Green here and under a kernel that reads the entry through Path.is_dir, by design: an entry's type is read
        through a link, and ELOOP (a looping link) and ENOENT (a dangling one) are in _REG_MISSING_ERRNOS, so the entry
        is not a directory, never a fault, as Path.is_dir answers it in the code before this change. Red under a kernel
        that drops ELOOP from the entry's partition."""
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
    """What a reader that passes no faults list shows while the tree the agent's file lies under cannot be read.
    _subagent_file answers such a caller a bare None when
    the file is found under no tree the walk could read while one could not be read, and the caller reads it as absence:
    the viewer (build_subagent) says the agent's transcript is missing, the frame equal to the one a removed tree gives
    and _subagent_frame_cached keyed as it is, and the chat's Agent head (_stamp_agents) carries no steps. A caller that
    passes a faults list is told the reason (_awaiting_nest, and the release at an agent's end, _release_ended_agents,
    whose cases are in tests/test_record_cache_agent_end.py AgentEnd); these are not. Transient: nothing is memoized
    under the fault, so the first lookup after it clears resolves the file and the head carries its steps again, and
    _subagent_frame_cached's key moves with the resolved file, so the frame it cached under the fault is rebuilt rather
    than served (asserted without clearing the frame cache). This case is the
    named witness of the texts that state it (_subagent_tree's and _SubagentTreeUnreadable's docstrings and
    docs/reference.md's memos paragraph). Green before the change too, by design: it characterizes what the code does
    (the base kernel showed the same frame, and memoized the miss as well). The follow-up fix that has the viewer state
    the fault turns it red and replaces it. Driven with the workflow agent's file one level down and no standing resolution, under a real
    EACCES (the session directory at mode 000; skipped as root, whom permission bits do not bind) and under an EIO by
    mock on the root's own lstat."""

    ERR = {"eio": "OSError", "eacces": "PermissionError"}   # the type name the walk passes to a caller's faults
    MISSING = "The transcript file for agent %s is missing"   # the opening of build_subagent's absent sentence

    def setUp(self):
        super().setUp()
        self.wf_key = (str(self.tpath), AID_WF)
        km._SUBAGENT_FILE_CACHE.pop(self.wf_key, None)       # no standing resolution
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



def _in_realpath_of_an_agent_file():
    """Whether the caller of the caller runs inside an os.path.realpath call whose argument is an agent file (a *.jsonl
    path): _find_agent_file's candidate resolution, told apart from the root's by its argument."""
    f = sys._getframe(2)
    while f is not None:
        if f.f_code.co_name == "realpath":
            fn = f.f_locals.get("filename")
            return fn is not None and os.fsdecode(fn).endswith(".jsonl")
        f = f.f_back
    return False


class RealpathFailureIsAFault(_Walk):
    """(17) _find_agent_file's real-path check reads its error, with one behaviour on every supported interpreter: its
    two os.path.realpath calls are strict, so a readlink or an lstat either one makes that fails raises, and the raise is
    the walk's own fault, the root's call excluding the tree and a candidate's excluding that candidate; the root's call
    is made only when the tree read found a directory, so a place with no tree stays an ordinary miss. The code before
    this change called both unstrict, whose answer differs by interpreter: 3.10 to 3.12 raise when a readlink the call
    makes fails, a raise the walk did not read, and 3.13 and later answer the path unresolved. Each world fails one
    link's readlink by mock (a real failure needs the link replaced during the call):
    - a symlinked sibling session directory sorted before the holder, its readlink raising ENOENT: the holder's file, no
      fault, and again after the mock lifts. Red under M0 on 3.10 to 3.12 alone (the raise taken by the project
      listing's ENOENT clause for no project directory: None, no fault, the miss memoized and answered after the lift);
      green under M0 on 3.13 and later, where the check answers the unresolved sibling root and its candidates are
      absent;
    - the own tree reached through a symlinked project directory, its readlink raising EIO for every resolution: None
      with the fault, the own root noted unreadable by equality on the place, nothing memoized, and the file after the
      lift. Red under M0 on every interpreter: 3.10 to 3.12 raise OSError out of _subagent_file, and 3.13 and later
      answer the file, the check comparing two unresolved paths, which is not the one answer the rule gives everywhere;
    - the candidate half, the same world with the candidate's resolution alone failing and the root's reading: None with
      the fault, the candidate noted unreadable, nothing memoized, and the file after the lift. Red under M0 on every
      interpreter: 3.10 to 3.12 raise OSError out of _subagent_file, and 3.13 and later reject the unresolved candidate
      with no fault and memoize the miss, answered after the mock lifts although the file is there;
    - the boundaries, green under M0 and here by design: an absent own root, and a sibling session directory with no
      subagents/, each a miss memoized with no fault, and the holder's file found past that sibling with no fault;
    - the boundaries where a path goes away between two reads: a candidate removed between its lstat and its
      resolution is a fault, nothing memoized, and the next lookup a miss (red under M0 and M3: the gone file answered
      and memoized); a root removed on disk while the scope holds its pair answers the fault in that scope, nothing
      memoized, and a miss in the next (red under M0 and M4: a miss memoized in the removal's scope, on the held
      stamps, which the next scope's re-check finds moved).

    Named mutants, each applied alone to kernel/kernel.py and red on the case named (each run on 3.10, 3.11, 3.12, 3.13
    and 3.14t and recorded outside the repo with its command, interpreter and head):
    - M0, both calls as the code before this change made them, unstrict with their raise unread (both tries removed and
      strict=True dropped at each): the sibling case on 3.10 to 3.12 alone; the own-tree case, the candidate case, both
      boundaries where a path goes away, FaultOnTheWalksOwnRead's (8) control and tests/test_record_cache_agent_end.py
      AgentEnd's resolution residual, on every interpreter;
    - M1, the root's try removed: the own-tree case (OSError out of _subagent_file) and the sibling case (None with no
      fault: the project listing's ENOENT clause takes the raise), the held-root boundary and FaultOnTheWalksOwnRead's
      (8) control (each a raise out of _subagent_file), on every interpreter;
    - M2, the candidate's try removed: the candidate case and the removed-candidate boundary (each a raise out of
      _subagent_file), and AgentEnd's resolution residual, on every interpreter;
    - M3, the candidate's call unstrict again: the removed-candidate boundary (the gone file answered and memoized) and
      AgentEnd's resolution residual, on every interpreter, and the candidate case on 3.13 and later (the miss
      memoized; on 3.10 to 3.12 the try reads the unstrict raise, and that case is green);
    - M4, the root's call unstrict again: the held-root boundary (a miss memoized in the removal's scope) and
      FaultOnTheWalksOwnRead's (8) control (the root's realpath raising nothing), on every interpreter, and the own-tree
      case on 3.13 and later, where the fault is then the candidate's and the place noted is not the root;
    - M5, the return for a tree with no directory removed: both absence boundaries (the strict call's FileNotFoundError
      on the absent root read as a fault where a miss is due), the held-root boundary on its next scope's miss (the same
      raise), ViewerUnderAnUnreadableTree's two cases on their removed-tree premise, and the absent-place cases
      tests/test_subagent_tree_stamps_per_cycle.py's list of named mutants names, on every interpreter."""

    @staticmethod
    def _readlink_failing(link, err, candidate_only=False):
        """os.readlink of `link` raising `err` (FileNotFoundError for ENOENT, else OSError), every other readlink reading;
        with `candidate_only`, only inside a realpath of an agent file, so the root's resolution reads. Returns (the patch,
        the list of raises)."""
        real, raised = os.readlink, []

        def rl(p, *a, **k):
            if not isinstance(p, int) and os.fsdecode(p) == link and (not candidate_only or _in_realpath_of_an_agent_file()):
                raised.append(1)
                if err == errno.ENOENT:
                    raise FileNotFoundError(err, os.strerror(err), link)
                raise OSError(err, os.strerror(err), link)
            return real(p, *a, **k)
        return mock.patch.object(os, "readlink", rl), raised

    def _look_at(self, tpath, aid):
        """`aid`'s lookup beside the transcript `tpath` under a running chat build's dependency scope: (answer, the
        caller's faults, the build's notes), a raise out of _subagent_file failing the case with the interpreter named."""
        faults, deps = [], {"task_outs": [], "postal_any": False}
        km._chat_dep_scope.deps = deps
        try:
            got = km._subagent_file(str(tpath), aid, faults)
        except OSError as e:
            self.fail("the lookup raised %r out of _subagent_file (sys.version %s)" % (e, sys.version.split()[0]))
        finally:
            km._chat_dep_scope.deps = None
        return got, faults, deps["task_outs"]

    def _linked_project(self, name):
        """The project directory reached through a symlink `name` beside it: (the transcript's path through the link, the
        link, the own subagents root through it), the workflow agent's memo key forgotten around the case."""
        linkproj = Path(self.td) / "projects" / name
        linkproj.symlink_to(self.proj)
        tpath = linkproj / (SID + ".jsonl")
        own = tpath.with_suffix("") / "subagents"
        self.roots.append(str(own))
        key = (str(tpath), AID_WF)
        km._SUBAGENT_FILE_CACHE.pop(key, None)
        self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, key, None)
        return tpath, str(linkproj), own

    def _unmade_under_the_link(self, tpath, link, place, candidate_only):
        """Under the failing readlink, the workflow agent's lookup through the link: None with the fault, `place` noted
        unreadable by equality, nothing memoized; after the mock lifts, the file, memoized."""
        key = (str(tpath), AID_WF)
        patch, raised = self._readlink_failing(link, errno.EIO, candidate_only)
        with patch:
            got, faults, notes = self._look_at(tpath, AID_WF)
        py = sys.version.split()[0]
        self.assertTrue(raised, "premise: the resolution reached the failing readlink (sys.version %s)" % py)
        memo = km._SUBAGENT_FILE_CACHE.get(key)
        self.assertEqual((got, faults, memo), (None, ["OSError"], None),
                         "(answer, faults, memo entry) under the failed resolution, sys.version %s: %r; keyed on (None, "
                         "['OSError'], None): the resolution's failure read as the walk's own fault on every interpreter, the "
                         "lookup not made, nothing memoized" % (py, (got, faults, memo)))
        self.assertEqual([p for p, k in notes if k == km._TREE_UNREADABLE], [str(place)],
                         "the running chat build is told the place whose resolution failed is unreadable, by equality on the "
                         "place (sys.version %s): %r" % (py, notes))
        f = tpath.with_suffix("") / "subagents" / "workflows" / self.wf.name / ("agent-%s.jsonl" % AID_WF)
        self.assertEqual(self._look_at(tpath, AID_WF)[:2], (f, []), "the mock lifted: the next lookup finds the file")
        self.assertEqual(km._SUBAGENT_FILE_CACHE[key][1], f, "and memoizes it")

    def test_a_readlink_enoent_under_a_symlinked_sibling_does_not_hide_the_holders_file(self):
        real_dir = Path(self.td) / "elsewhere-before"
        (real_dir / "subagents" / "workflows").mkdir(parents=True)
        link = self.proj / SID_BEFORE
        link.symlink_to(real_dir)
        _age(str(real_dir))
        self.roots.append(str(link / "subagents"))
        _root, f = self._sibling(SID_HOLD, holder=True)
        _age(str(self.proj))
        self._premise_order(SID_BEFORE, SID_HOLD)
        patch, raised = self._readlink_failing(str(link), errno.ENOENT)
        with patch:
            got, faults, _notes = self._look_at(self.tpath, AID_FORK)
        py = sys.version.split()[0]
        self.assertTrue(raised, "premise: the sibling root's resolution reached the failing readlink (sys.version %s)" % py)
        self.assertEqual((got, faults), (f, []), "the holder's file, no fault: the sibling excluded and the search gone on "
                                                 "(sys.version %s)" % py)
        self.assertEqual(km._subagent_file(str(self.tpath), AID_FORK), f, "and after the mock lifts")

    def test_a_failed_resolution_of_the_own_trees_root_answers_none_with_the_fault_on_every_interpreter(self):
        tpath, link, own = self._linked_project("-tmp-notes-api-link")
        self._unmade_under_the_link(tpath, link, own, candidate_only=False)

    def test_a_failed_resolution_of_a_candidate_alone_answers_none_with_the_fault_and_memoizes_no_miss(self):
        tpath, link, own = self._linked_project("-tmp-notes-api-link2")
        cand = own / "workflows" / self.wf.name / ("agent-%s.jsonl" % AID_WF)
        self._unmade_under_the_link(tpath, link, cand, candidate_only=True)

    def test_boundary_an_absent_own_root_is_a_miss_memoized_with_no_fault(self):
        shutil.rmtree(str(self.subdir))
        _age(str(self.tpath.with_suffix("")))
        _age(str(self.proj))
        got, faults, _notes = self._lookup()
        self.assertEqual((got, faults, self.fork_key in km._SUBAGENT_FILE_CACHE), (None, [], True),
                         "an absent own root: a miss, memoized, no fault (no realpath is taken for a place with no tree)")

    def test_boundary_a_sibling_session_directory_with_no_subagents_is_a_miss_and_the_holder_is_found_past_it(self):
        (self.proj / SID_BEFORE).mkdir()
        _age(str(self.proj / SID_BEFORE))
        _age(str(self.proj))
        got, faults, _notes = self._lookup()
        self.assertEqual((got, faults, self.fork_key in km._SUBAGENT_FILE_CACHE), (None, [], True),
                         "a sibling with no subagents/: a miss, memoized, no fault")
        km._SUBAGENT_FILE_CACHE.pop(self.fork_key, None)
        _root, f = self._sibling(SID_HOLD, holder=True)
        _age(str(self.proj))
        self._premise_order(SID_BEFORE, SID_HOLD)
        got, faults, _notes = self._lookup()
        self.assertEqual((got, faults), (f, []), "the holder's file found past the sibling with no subagents/, no fault")

    def test_boundary_a_candidate_removed_between_its_lstat_and_its_resolution_is_a_fault_and_the_next_lookup_a_miss(self):
        """The workflow agent's file removed right after the walk's lstat of it found a regular file (by a wrapper of
        os.lstat that unlinks it once): the candidate's strict resolution raises FileNotFoundError, read as the walk's
        fault, so the lookup answers None with the fault and memoizes nothing, and the next lookup is a miss, memoized
        with no fault. Red on its first assertion under M0 and M3 (the unstrict call answers the removed path, the
        containment check passes, and the gone file is answered and memoized), and under M2 at the lookup (the strict
        call's raise unread, out of it), on every interpreter."""
        key = (str(self.tpath), AID_WF)
        km._SUBAGENT_FILE_CACHE.pop(key, None)
        self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, key, None)
        f = str(self.wf / ("agent-%s.jsonl" % AID_WF))
        real, done = os.lstat, []

        def lstat(p, *a, **k):
            st = real(p, *a, **k)
            if not done and not isinstance(p, int) and os.fsdecode(p) == f and sys._getframe(1).f_code.co_name == "_find_agent_file":
                done.append(1)
                os.unlink(f)
            return st
        faults = []
        with mock.patch.object(os, "lstat", lstat):
            got = km._subagent_file(str(self.tpath), AID_WF, faults)
        self.assertEqual(done, [1], "premise: the file was removed right after the walk's lstat of it")
        self.assertEqual((got, faults, key in km._SUBAGENT_FILE_CACHE), (None, ["FileNotFoundError"], False),
                         "the removed candidate's strict resolution read as the walk's fault, nothing memoized (sys.version %s)"
                         % sys.version.split()[0])
        faults = []
        got = km._subagent_file(str(self.tpath), AID_WF, faults)
        self.assertEqual((got, faults, key in km._SUBAGENT_FILE_CACHE), (None, [], True),
                         "the next lookup reads the place again: a miss, memoized with no fault")

    def test_boundary_a_held_root_removed_on_disk_answers_the_fault_in_its_scope_and_a_miss_in_the_next(self):
        """The held-root lag meets the strict call: inside a scope that holds the own tree's pair, the root removed on
        disk, the pair still lists its directories, so the root's resolution is made and raises FileNotFoundError: that
        scope's lookup answers None with the fault and memoizes nothing (the code before this change resolved it unstrict
        and memoized a miss on the held stamps); the next scope reads the absence, a miss memoized with no fault. Red on
        its first assertion under M0 and M4, the miss memoized in the removal's scope, under M1 at the lookup (the
        strict call's raise unread, out of it), and under M5 on its second (the next scope's absent root read as a
        fault), on every interpreter."""
        key = (str(self.tpath), AID_WF)
        km._SUBAGENT_FILE_CACHE.pop(key, None)
        self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, key, None)
        _scope_open()
        try:
            held = km._subagent_tree(str(self.subdir))
            self.assertTrue(held[0], "premise: the scope holds the own tree's pair, with its directories")
            shutil.rmtree(str(self.subdir))
            _age(str(self.proj))
            faults = []
            got = km._subagent_file(str(self.tpath), AID_WF, faults)
            self.assertEqual((got, faults, key in km._SUBAGENT_FILE_CACHE), (None, ["FileNotFoundError"], False),
                             "in the removal's scope: the held pair's root resolved strictly, its absence read as the walk's "
                             "fault, nothing memoized")
        finally:
            _scope_close()
        _scope_open()
        try:
            faults = []
            got = km._subagent_file(str(self.tpath), AID_WF, faults)
            self.assertEqual((got, faults, key in km._SUBAGENT_FILE_CACHE), (None, [], True),
                             "in the next scope: the tree read finds no root, a miss memoized with no fault")
        finally:
            _scope_close()


class DowngradedNoneIsNotMemoized(_Walk):
    """(18) A None the agent-file walk notes for a place whose stamp it took as real is never memoized. The walk notes a
    live link at a sibling's subagents place under _chat_stat_key taken through the link, downgraded to None when that
    stat or the identity lstat after it raises, or when the place changed between the two (_subagent_walk_dep_note),
    while its stamp of the place (_dir_stamp, through the link) is real. Memoized, that None would be replayed by every
    memo hit while the stamp stands, and since no re-stat of a live link equals None, the tab would be rebuilt every cycle
    with nothing changed on disk, where the code before this change cost one rebuild. So _subagent_file memoizes nothing for
    such a walk, and the next lookup walks again. Three variants, the world a live link at the holder's subagents place
    and AID_FORK's file nowhere: one EIO on the identity lstat, one EIO on the note's stat, and no fault at all (the link
    re-created to the same target between the note's stat and its identity lstat); each asserts the downgraded None in
    the first build's record, nothing memoized, and the tab rebuilt at most once and then served; a no-fault control is
    noted under a real key, memoized, and served every cycle. Red under the mutant that drops _subagent_file's
    memoize-nothing rule for a downgraded None, each variant on every interpreter (rebuilt at every cycle, the memo
    replaying the None)."""

    def _world(self):
        target = Path(self.td) / "elsewhere"
        (target / "workflows").mkdir(parents=True)
        _age(str(target))
        hold = self.proj / SID_HOLD
        hold.mkdir()
        (hold / "subagents").symlink_to(target)
        _age(str(hold))
        sd = str(hold / "subagents")
        self.roots.append(sd)
        return target, sd

    def _build(self):
        km._chat_dep_scope.deps = {"task_outs": [], "postal_any": False}
        try:
            got = km._subagent_file(str(self.tpath), AID_FORK)
            return got, km._chat_build_deps(SID, {"events": []})
        finally:
            km._chat_dep_scope.deps = None

    def _cycles(self, first_cm, sd, n=5):
        """The first build under `first_cm` inside a scope, then n - 1 cycles, each rebuilding when the recorded keys no
        longer equal the signature's re-stat. Returns (the key the first record holds for `sd`, whether the first build
        memoized, the verdicts)."""
        _scope_open()
        try:
            with first_cm:
                _got, rec = self._build()
        finally:
            _scope_close()
        first = dict(rec["task_outs"]).get(sd, "unnoted")
        memoized = self.fork_key in km._SUBAGENT_FILE_CACHE
        verdicts = []
        for _c in range(2, n + 1):
            rebuilt = km._chat_sig_deps(SID, rec)[0] != tuple(rec["task_outs"])
            verdicts.append("rebuilt" if rebuilt else "served")
            if rebuilt:
                _scope_open()
                try:
                    _got, rec = self._build()
                finally:
                    _scope_close()
        return first, memoized, verdicts

    def _assert_settles(self, got):
        first, memoized, verdicts = got
        self.assertIsNone(first, "premise: the first build's record notes the live link's place under the downgraded None")
        self.assertIn(verdicts, (["served"] * 4, ["rebuilt"] + ["served"] * 3),
                      "the tab is rebuilt at most once and served after (a downgraded None is never replayed): %r" % (verdicts,))
        self.assertFalse(memoized, "the walk that noted the downgraded None memoized nothing")

    def test_control_no_fault_is_noted_under_a_real_key_memoized_and_served(self):
        _t, sd = self._world()
        first, memoized, verdicts = self._cycles(contextlib.nullcontext(), sd)
        self.assertEqual((first is not None, memoized, verdicts), (True, True, ["served"] * 4),
                         "the place noted under a real key, the walk memoized, the tab served every cycle: %r"
                         % ((first, memoized, verdicts),))

    def test_one_eio_on_the_identity_lstat(self):
        _t, sd = self._world()
        real, calls = os.lstat, []

        def lst(p, *a, **k):
            if not isinstance(p, int) and os.fsdecode(p) == sd:
                calls.append(sys._getframe(1).f_code.co_name)
                if calls[-1] == "_lstat_or_none" and calls.count("_lstat_or_none") == 1:
                    raise OSError(errno.EIO, "transient")
            return real(p, *a, **k)
        self._assert_settles(self._cycles(mock.patch.object(os, "lstat", lst), sd))
        self.assertIn("_lstat_or_none", calls, "premise: the identity lstat ran")

    def test_one_eio_on_the_notes_stat(self):
        _t, sd = self._world()
        real, calls = os.stat, []

        def st(p, *a, **k):
            if not isinstance(p, int) and os.fsdecode(p) == sd:
                calls.append(sys._getframe(1).f_code.co_name)
                if calls[-1] == "_chat_stat_key" and calls.count("_chat_stat_key") == 1:
                    raise OSError(errno.EIO, "transient")
            return real(p, *a, **k)
        self._assert_settles(self._cycles(mock.patch.object(os, "stat", st), sd))
        self.assertIn("_chat_stat_key", calls, "premise: the note's stat ran")

    def test_no_fault_the_link_re_created_to_the_same_target_between_the_notes_stat_and_its_identity_lstat(self):
        target, sd = self._world()
        real, done = km._chat_stat_key, []

        def csk(p):
            out = real(p)
            if p == sd and not done:
                done.append(1)
                os.unlink(sd)
                os.symlink(str(target), sd)
            return out
        self._assert_settles(self._cycles(mock.patch.object(km, "_chat_stat_key", csk), sd))
        self.assertEqual(done, [1], "premise: the link was re-created")


class CoarseClockTick(_Walk):
    """(19) A WITNESS of a stated residual, not a fix: these cases assert the residual's behaviour as it stands and turn
    red when it is closed. The agent-file memo's hit is validated on each directory's mtime_ns as the walk stamped it and
    replays the keys the walk noted, so a filesystem clock coarser than an entry change (Linux before 6.13 stamps
    directories in jiffies, some filesystems in seconds) can leave a directory's mtime_ns equal across a change made in
    the tick its stamp was taken in, and the hit then replays keys taken before it (_subagent_file_notes_replay's
    docstring states the residual; no same-mtime_ns change was seen in 15,000 trials on ext4 and tmpfs under a Linux 7.0
    kernel). Emulated as that clock would leave it: the own subagents directory changed just now, the change made, and
    its mtime put back to the stamp's own value. With the racy window reopened, as a real kernel runs, so a fix that
    applies _subagent_tree's racy rule to this memo turns both red:
    - the agent's own file landing at its flat place in the stamp's tick: the lookup answers the memoized miss and the
      tab, replaying the place's (path, None), is rebuilt at every cycle while the directory's mtime stays (the miss
      predates this change; the rebuild every cycle is new with the replay); once the mtime moves, the lookup finds the
      file and the tab settles after one rebuild;
    - a sidecar landing in the stamp's tick where it moves the directory's size (tmpfs, btrfs and short-form xfs move a
      directory's size per entry; skipped where the size does not move within 400 entries): the tab is rebuilt at every
      cycle while the mtime stays, the hit replaying the pre-change (mtime, size) (new with the replay: the code before
      it rebuilt once); once the mtime moves, one rebuild and then served.
    Both are green here by design; red under the racy rule on this memo (memoizing nothing for a walk that read a
    directory changed within _SUBAGENT_DIR_RACY_NS of the clock), the follow-up that would close the residual."""

    GHOST = "a9999999999999999"

    def setUp(self):
        super().setUp()
        self.gkey = (str(self.tpath), self.GHOST)
        km._SUBAGENT_FILE_CACHE.pop(self.gkey, None)
        self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, self.gkey, None)
        racy = mock.patch.object(km, "_SUBAGENT_DIR_RACY_NS", RACY_NS)   # the real window, reopened
        racy.start()
        self.addCleanup(racy.stop)

    def _touch_now(self, d):
        p = os.path.join(d, ".tick")
        open(p, "w").close()
        os.unlink(p)
        return os.stat(d)

    def _same_tick(self, d, st, make):
        make()
        os.utime(d, ns=(st.st_atime_ns, st.st_mtime_ns))
        self.assertEqual(os.stat(d).st_mtime_ns, st.st_mtime_ns, "premise: the stamp's mtime_ns stands across the change")

    @staticmethod
    def _next_tick(d, st):
        """The directory's mtime moved one second past the stamp's, its entries unchanged: the next change a coarse clock
        does see."""
        os.utime(d, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))

    def _build(self):
        km._chat_dep_scope.deps = {"task_outs": [], "postal_any": False}
        try:
            got = km._subagent_file(str(self.tpath), self.GHOST)
            return got, km._chat_build_deps(SID, {"events": []})
        finally:
            km._chat_dep_scope.deps = None

    def _cycles(self, rec, n):
        """n cycles over the record `rec`, each rebuilding when the recorded keys no longer equal the signature's re-stat:
        (the verdicts, each rebuild's answer, the last record)."""
        verdicts, answers = [], []
        for _ in range(n):
            rebuilt = km._chat_sig_deps(SID, rec)[0] != tuple(rec["task_outs"])
            verdicts.append("rebuilt" if rebuilt else "served")
            if rebuilt:
                got, rec = self._build()
                answers.append(got)
        return verdicts, answers, rec

    def test_residual_the_agents_own_file_landing_in_its_stamps_tick_is_answered_the_memoized_miss_until_the_mtime_moves(self):
        sub = str(self.subdir)
        st = self._touch_now(sub)                                     # the own subagents directory changed just now
        got, rec = self._build()
        self.assertIsNone(got, "premise: the file is nowhere yet")
        f = self.subdir / ("agent-%s.jsonl" % self.GHOST)
        self._same_tick(sub, st, lambda: f.write_text(""))
        verdicts, answers, rec = self._cycles(rec, 3)
        self.assertEqual((verdicts, answers), (["rebuilt"] * 3, [None] * 3),
                         "the residual as it stands: while the directory's mtime stays, each rebuild's lookup answers the memoized "
                         "miss and the tab is rebuilt at every cycle, the hit replaying the place's (path, None): %r"
                         % ((verdicts, answers),))
        self._next_tick(sub, st)
        verdicts, answers, _rec = self._cycles(rec, 3)
        self.assertEqual((verdicts, answers), (["rebuilt", "served", "served"], [f]),
                         "its bound: once the mtime moves, the lookup walks and finds the file, and the tab settles after one "
                         "rebuild: %r" % ((verdicts, answers),))

    def test_residual_a_size_move_in_the_stamps_tick_rebuilds_the_tab_at_every_cycle_until_the_mtime_moves(self):
        sub = str(self.subdir)
        st = self._touch_now(sub)
        _got, rec = self._build()
        size0 = os.stat(sub).st_size

        def land():
            n = 0
            while os.stat(sub).st_size == size0 and n < 400:
                (self.subdir / ("agent-%016x.meta.json" % (0xb000 + n))).write_text("{}")
                n += 1
        self._same_tick(sub, st, land)
        if os.stat(sub).st_size == size0:
            self.skipTest("this filesystem's directory size did not move within 400 entries")
        verdicts, _answers, rec = self._cycles(rec, 4)
        self.assertEqual(verdicts, ["rebuilt"] * 4,
                         "the residual as it stands: while the directory's mtime stays, the hit replays the pre-change (mtime, "
                         "size) and the tab is rebuilt at every cycle: %r" % (verdicts,))
        self._next_tick(sub, st)
        verdicts, _answers, _rec = self._cycles(rec, 3)
        self.assertEqual(verdicts, ["rebuilt", "served", "served"],
                         "its bound: once the mtime moves, the lookup walks, notes the directory's current key and the tab "
                         "settles after one rebuild: %r" % (verdicts,))


if __name__ == "__main__":
    unittest.main()
