#!/usr/bin/env python3
"""A subagents tree is validated at most once per pusher cycle and once per jobs pass (2026-09-19).

The walk memo (tests/test_subagent_tree_memo.py) made a read of a session's subagents tree cost one lstat per known
directory instead of a listing. But the agent-file lookup's memo (_subagent_file) re-validates a hit by stat-ing every
directory its walk read, which for a nested or missing agent's file is the whole tree, and _awaiting_nest resolves
every awaiting agent's file once per _session_awaiting call; so one call over A such agents paid (A + 1) x D directory
stats with nothing changed (when there are two or more such agents, or a command row whose owner is read from their
transcripts; a single agent with no command row is excluded from its own owner lookup and paid D alone), and the
pusher makes up to five such calls per session per cycle (the chat, feed and timeline builds and the chips), the jobs
pass one more. On one deployed kernel _dir_stamp's one os.stat was the top self frame of a 20 s py-spy profile, 28
percent of the samples by that profile's reading, and another's memo counters showed 24.5 million validation lstats in
6.8 hours over 1,294 directories (2026-09-19; the user 2026-09-05, who wanted the one-core kernel investigated).

The fix keys the validation on the event a time window would have stood in for: the cycle and the pass. Each opens a
thread-confined scope (_subagent_scope_open in _pusher_cycle and _jobs_cycle, closed in their finally blocks); the
first reader of a tree in the cycle validates or walks it and holds the (directories, stats) pair and each directory's
stamp; every later reader of the tree on that thread in the cycle is served it with no stat, the agent-file lookup's
re-check of its directories included (what the re-check's other stamps cost: the cost home, _subagent_tree_memo_report's
docstring); and the agents' launch folds are held for the cycle too (_awaiting_nest). A change on disk after the
validation is seen by the NEXT cycle's first reader, one cycle later at most. Nothing failed is held for the cycle; a
launch fold that did not read the file is held for the CALL that observed the fault alone (two lifetimes; round 1 of #882
found that returned without any hold it was folded once per owner lookup, A x (A - 1) times per read where the parent's
call-local memo folded A).

Pinned here, through the REAL cycle functions so the clearing point tested is the wired one: (1) the bound: one pusher
cycle and one jobs pass with three _session_awaiting calls each cost D os.lstat on the tree's directories (the one
validation), 0 os.stat on them, dirStats plus D - 1, one hit, served moved by the asks the scope answered (the premise
that every read reached the memo is asserted per read and by shape, the first ask validated and every later one served,
never by a count of asks per read; round 1 of #882's extra8-1) and A agent-file stats (one fold per agent), where before the scope
each call paid A x D os.stat, D lstats and A file stats, and the scope's reads moved no counter; with an agent row whose
file is nowhere the miss walk runs once per cycle and its dependency notes to the chat build cost no stat on the tree's
directories (round 1 of #882's correctness-1:
the own tree's note was a fresh stat, one per walk), and two such rows share the project directory's one stamp stat, an own
stat _dir_stamp holds in the scope keyed by directory under root None (dirStats moves by (D - 1) + 1 at one row and at two,
where the cost term as stated before the owner's pass before round 2 of #882, per agent, predicted (D - 1) + G; the term's
one home is _subagent_tree_memo_report's docstring); the scope is closed after the cycle; the bound's counts are backed by a
census, by call class, of the filesystem calls under the tree made through the classes the spy wraps (os.stat, os.lstat,
os.scandir, os.listdir, os.access, os.readlink, os.open, os.walk, io.open, io.FileIO, and every call given a dir_fd as its
own entry; a class outside that set, os.statvfs say, is outside the census, the roads it leaves open stated in _Spy's
docstring and witnessed in (8)) pinned by equality, {lstat: D, stat: A} over the cycle and {} on each
served path (the tree read, the stamp, the agent-file hit), so a read through a wrapped class the counts do not see fails by
name (the owner's pass before round 2 of #882: a guarded listing on the served path left the module green); and a read
outside any cycle (a handler thread's) still pays per call, with dirStats now counting the stats of both validators;
(2) per cycle, not sticky: a directory and a fourth agent landing between two cycles are seen by the second cycle's
first read (a re-walk; the listing equals os.walk's and the sidecar reaches the map) while its later reads that cycle
cost nothing, a launch appended to an agent's transcript between two cycles is folded by the second cycle's first read
(A folds, the launch folds being the cycle's) and nests its command there, and, the contract, a directory created after a
cycle's validation waits for the next cycle; and the stamps' release at the cycle's end pinned on its own: a second cycle
over the miss-path world re-takes the project directory's own stat (dirStats D, where a stamps map carried across cycles
serves the stale stamp and pays D - 1); (3) two
threads: a pusher cycle and a jobs pass running at once each validate once with their own scope object, never served
by the other's; (4) the guards, each against the input it refuses and the input it accepts: a forget that evicts the
root makes the next read in the same scope walk again while a forget that evicts nothing leaves the scope serving; a
stamp stat that raises is answered (dir, None) and not held while one that succeeds is held; a walk with a failed
listing is not held while a clean one is, and a walk that stored a racy stamp (the real window, one directory written at
the walk) is held for the cycle like a clean one, its pair and its stamps, and walked again by the next cycle's first read
(round 1 of #882: every case closed the window, so the hold had no executed pin and the opposite policy stayed green); a
launch fold that did not read the file is folded once per read (the call-local
hold) and again by the next read (not held for the cycle) while one that read it is held for the cycle, with the fault's
producer driven for real (the reader's fail path, a raising fold, a readable file); the generation is read before each disk
read, the pair's two hold sites (the validated hit's and the clean walk's, both in _subagent_tree) under the one read before
the root's lstat, so an eviction landing inside the root's lstat (the walk's hold), inside a validation lstat after the hit
was read (the hit's hold), inside an own stat or inside a launch fold's resolution leaves that hold outdated and the next
lookup validates, walks, stats or folds it once more (D lstats, D lstats, 1 stat, 1 fold) instead of serving it; a root gone mid-cycle whose entry stood
moves the gen and records its own eviction, and a sibling tree the scope held is still served (the eviction is that root's,
not the sibling's), while one with no entry moves nothing; the two pop paths, each found by a thread with no hold on the
root while another thread's scope holds it (the tree removed, and the tree replaced by a regular file; round 1 of #882,
where the replaced-root record had no case and its deletion left the module green): the pop moves the gen by one and names
the root in the table, the holder's next read drops its pair and answers the pop's shape at one lstat of the root, its
other held tree is still served, and a second read with no entry standing moves nothing; and the held-root lag,
characterized: a root removed while the same thread's scope holds it is served, pair and stamps, at no stat until that
scope ends (the served call precedes the root's lstat, so no pop runs and the gen stands), and the next scope's first read
finds it gone; and the served counter at every edge of these, asserted: a served read of a held root, removed or not,
lands in served, and a stale hold dropped at the lookup, a missing-root pop and a replaced-root pop move it by nothing (a
stale hold dropped after the forget reads (hit, miss, served, evict) == (0, 1, 0, 1)), so hit + miss + served is the reads
answered a tree; (5) the invalidation is scoped to what became stale (since 2026-09-21,
round 1 of #882's ruling): an eviction of a root drops from every open scope that root's pair, the stamps indexed from it and the launch folds
keyed on it (the transcript's own subagents root, whatever tree the agent's file resolved under: the rule and its bound
are stated once, in _subagent_scope's docstring), and nothing else, so a held tree, a held stamp and held launch folds survive
the eviction of a root they are not under (0 lstats, 0 stats, 0 folds on the next read), a cached agent-file path is not
answered after another thread found its tree gone (the stamps of the removed tree are dropped, whether indexed from the held
tree or taken as own stats by a lookup that preceded any tree read), a stamp the scope took itself, vouched by no root, is
re-taken after any eviction (1 stat) where a tree-indexed one is served (0), held launch folds are
re-read when their own root leaves the memo (the attribution changes), a fold of a file found under a sibling's tree (the
/clear-fork shape) survives the sibling's eviction (0 folds, the attribution served, the sibling's pair dropped) and is
dropped by the own root's (A + 1 folds), and once the sibling's tree is gone and popped by another thread the fold from the
gone file is served until the cycle ends and re-read by the next cycle's first read (the command top-level there: the
bound's edge), and the table of evicted roots at its cap is
cleared with every held entry dropped once, each map by execution (the pair D lstats, an indexed stamp 1 stat, the launch
folds A folds), not through the shared predicate alone. Before 2026-09-21 one process-wide generation emptied every scope's three maps on
any root's eviction: every held tree paid its D lstats again, every held stamp its stat, every awaiting agent its fold.
(6) The dependency key (since 2026-09-21, round 1 of #882's ruling): the key a chat build records for a subagents tree the agent-file miss walk looked
through is the served read's (mtime, size) per directory, so a file landing after the hold under a directory the served
listing lacked leaves the recorded key behind the next signature's re-stat and the tab is rebuilt, whether the landing moved
the root's stamp or a listed child's; a fresh stat taken after the served listing recorded the post-landing key, equal to
every later re-stat, and the tab that showed the file missing was never rebuilt; a build whose lookup the agent-file memo
answers in a later cycle, or the held launch fold answers after a reader with no record open walked, records the same keys,
replayed from the walk's notes (round 2 of #882, group B: before it such a build recorded nothing for the sibling's tree);
a path one build reported under two keys, a held fold's replayed key behind a fresh walk's among them, is recorded under a
key no re-stat equals, so that tab is rebuilt too, where a record keeping the first key kept the walk's and never rebuilt
it; and a sibling session directory appearing after a build moves no key it recorded on any of the three roads, the
residual, witnessed. An agent's own place holding what the walk refuses (a symlinked agent file, or a symlinked
subagents/ whose target holds the file) is in no record, so the tab its walk built is served with no rebuild, a write to
the link's target included, beside the control of an absent place recorded None (round 3 of #882, group B: every build
replayed the walk's (place, None), which the re-stat through the link never equals, and the tab was rebuilt every
cycle); and a symlinked subagents/ replaced by a real directory holding the file moves no recorded key, the second
residual, witnessed. (7) The sum over roots: three alive
sessions with trees of unequal size and unequal agent counts, read in one pusher cycle and in one jobs pass with the reads
interleaved, cost the sum over their roots of D_r lstats (each root its own D_r), 0 stats and one fold per agent (the sum
over the sessions of A_s), so the total directories decide the cycle's cost and not their split over roots (the derived
cost sentence's pin in the tree; a lab lifted from this world measured the same at more sizes outside the repo). (8) The
census's own roads (round 2 of #882, extra6-2), executed on the tree under the spy: each road the spy closes (a
non-normalized or relative spelling of the root, a call given a dir_fd, io.FileIO) is counted, and each road it leaves
open (a DirEntry from a listing of the root's parent, a path outside the tree, an os class outside CLASSES, a bare
descriptor, a symlinked spelling, pathlib on 3.10) has an executed witness whose census is {}. (9) The eviction table's
lock (round 2 of #882, group E): the clear straddle, the wiped record and one root's out-of-order stores, each driven
with real threads, answer vouched False under the lock where the unlocked table answered True, and the out-of-order
store driven through the real forget, walk and pop serves no pair of a removed tree (the unlocked table served its 2
directories), beside a control with no race. (10) The miss path's roads beside the bound, each a term of the cost home,
_subagent_tree_memo_report's docstring (round 2 of #882, group D): an absent sibling root costs one failed os.stat per
lookup of each agent whose file is nowhere, G x K x (1 + M) per cycle, cold or steady, and moves no counter (a boundary
pin, red under a kernel that holds absence for the cycle); a sibling tree the walk reads is read once per cycle and
costs a candidate lstat per directory per walk, and on a steady cycle one own stat per directory, shared (both in
MissPathRoads, with a command row whose owner is read from the agents' transcripts before the tree is read, which
re-stats the tree's D directories once per cycle); each walk lists the project directory once and stats its E entries,
G listings and G x E stats over the cycle (_miss_walk_cycle); a walk's calls under the tree are {lstat: D, scandir: D} (Guards' stale-hold case); an
unreadable session directory resolves every agent again on every read, {lstat: CALLS x (3A + 1), stat: CALLS x A x
(D + 2)} under the tree, with no counter moved but the project directory's one stamp stat (Guards); and the chat
signature of a tab whose build walked S sibling trees re-stats its D + 1 + S x D + K recorded paths every cycle, and a
directory created under any sibling directory rebuilds the tab (DependencyKey).

Every count is derived in the test from the world's sizes (D and A, and where a case adds them G, K, S, M, E and the
interpreter's own realpath count, taken by running it), never written out. The cycle's jobs that read the tree through
mechanisms of their own (the fold checkpoint writer's realpath per checkpointed file, the spend guard's window-file
walk) are stubbed to nothing here, so what the spy counts is this memo's path alone. Synthetic fixtures only: a
private placeholder sid, invented agent ids and descriptions, a temp state root with session hosts off.
"""
import builtins
import contextlib
import errno
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import threading
import time
import traceback
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from romp_load import load_source
from tests.thread_ends import join_started

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the load (the tests/test_subagent_tree_memo.py preamble): the kernel resolves its state root
# at import, and only pytest runs conftest's floor. The root minted here is outside conftest's belt, so session hosts
# are switched off in it too (a state root with no `session-hosts` file starts a real host for any session it
# connects; none is connected here, and the file makes that so whatever a later test in this module does).
_ROOT = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = _ROOT
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.makedirs(os.path.join(_ROOT, "romp"), exist_ok=True)
with open(os.path.join(_ROOT, "romp", "session-hosts"), "w") as _fh:
    _fh.write("off")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_subagent_tree_stamps_per_cycle", os.path.join(BIN, "romp-kernel"))
jd = km.jd
RACY_NS_REAL = km._SUBAGENT_DIR_RACY_NS   # the kernel's racy window, read at import BEFORE _World.setUp closes it: the racy-hold guard runs with it

D = 8              # directories in the tree: the subagents root, workflows/, and D - 2 workflow directories under it
A = 3              # awaiting workflow agents, one nested in each of the first A workflow directories
CALLS = 3          # _session_awaiting calls the stubbed job makes per cycle: the chat, feed and timeline builds' share
SID = "11111111-2222-3333-4444-7c7c7c7c7c7c"   # a PRIVATE placeholder sid (the goal-store fixture rule; this module mints no goals)
OTHER_SID = "11111111-2222-3333-4444-7c7c7c7c7c7d"   # a second private placeholder: the session whose tree vanishes mid-cycle (Guards)
NOW = 1781100000
AGED_NS = 10_000_000_000                       # ten seconds: past the racy window, as tests/test_subagent_tree_memo.py ages
STAT_KEYS = ("hit", "miss", "served", "evict", "dirStats")   # served: the reads the scope answered from a held pair (since 2026-09-21)

# The kernel names this module replaces for a test and puts back at cleanup: the liveness and awaiting sources (stubbed
# as tests/test_awaiting_rows.py stubs them), the tick jobs a test stands in for, and the two jobs that read the tree
# through mechanisms of their own (the module docstring).
_KM_SAVED = ("NAMES", "_sdk", "_bg_live_norm", "_bg_pending", "_states_awaiting_overlay", "_owned_yield_why",
             "_session_stamp_full", "_session_delegated_why", "_session_delegated_identities", "_watches", "_pr_watches",
             "_turn_notify_tick", "_auto_nudge_tick", "_persist_checkpoints", "_converge_checkpoints", "_spend_guard_tick")


def _age(root):
    """Every directory under `root` stamped ten seconds ago, so the walk memo may vouch for it."""
    t = time.time_ns() - AGED_NS
    for r, _ds, _fs in os.walk(str(root)):
        os.utime(r, ns=(t, t))


def _scope():
    """This thread's open cycle scope, or None: outside a cycle, or on a kernel without the scope."""
    return getattr(km, "_subagent_scope", lambda: None)()


class _Spy:
    """os.stat and os.lstat counted per calling thread by what the path is: one of the tree's directories (`dir_stat`,
    `dir_lstat`), a file under the tree (`file_stat`: the agent files and sidecars), or elsewhere (uncounted); and beside
    those counts a CENSUS, by call class, of the filesystem calls under the tree made through the classes it wraps
    (`tree_calls`, CLASSES): os.stat, os.lstat, os.scandir, os.listdir, os.access, os.readlink, os.open, os.walk, io.open
    (builtins.open is the same function and is patched too) and io.FileIO, keyed by the class's name, for every path that
    is the root or lies under it, directories and files alike. The counts key on what the bound derives (D lstats, A file
    stats); the census is pinned by EQUALITY where the bound's cases and the served paths run (_assert_bound, the
    served-paths case), so a read of the tree through a wrapped class the counts do not see, a listing, an access, an
    open, a file's lstat, fails closed by the class's name (the owner's pass before round 2 of #882: the spy saw os.stat
    and os.lstat alone, and a guarded os.scandir on the served tree path left the module green). The patch is the os
    module's attribute (io's for io.open and io.FileIO), which is what the kernel, os.path and the pathlib of 3.12 and
    3.14 look up at call time; the kernel runs on 3.12.

    Which spellings the census places (round 2 of #882, extra6-2: a reviewer's reads planted on the served paths through a
    `//` or `/./` spelling of the root, a dir_fd, io.FileIO and a DirEntry of the root's parent each left both modules
    green): a path is normalized lexically before the test, os.path.abspath (a relative
    path joined to the working directory, then os.path.normpath), so `<sid>//subagents`, `<sid>/./subagents` and a
    relative spelling are the root; never os.path.realpath, which would call the patched os.lstat and count itself. A call
    given a dir_fd is its own census entry, `<class>(dir_fd)`, wherever its path points, since a path relative to a
    descriptor cannot be placed without reading the descriptor: such a call is counted on the safe side. Each of those
    roads, and io.FileIO, has a red control in SpyRoads asserting that the census counts it (test_closed_road_...), and a
    read through one of them on a served path fails that path's {} pin by its entry's name (the served-paths case in
    BoundPerCycleAndPerPass, and _assert_bound's equality over a cycle).

    Not in the census, stated, each with an executed witness in SpyRoads that makes the call under the spy on the
    fixture's tree and pins tree_calls() == {}, so a spy change that closes or widens the road turns it red: a DirEntry's
    stat or is_dir taken from a listing of the root's parent (the session directory, outside the tree; a listing of the
    root or below is counted, by the directory listed, and what is done with its entries is not),
    test_open_road_a_direntry_from_a_listing_of_the_roots_parent; any call on a path outside the tree, the project
    directory and the transcript, test_open_road_a_path_outside_the_tree; an os call class not in CLASSES, os.statvfs,
    os.listxattr, os.pathconf, test_open_road_an_os_call_class_outside_the_wrapped_set; a bare descriptor, os.stat(fd),
    os.listdir(fd), os.scandir(fd), on a descriptor opened outside the window (an os.open of a path under the tree is
    counted when it runs), test_open_road_a_bare_descriptor; a symlinked spelling, a path through a link to the session
    directory (normalization is lexical), test_open_road_a_symlinked_spelling_of_the_root; and pathlib on 3.10, which
    calls the os functions it bound at import (the pathlib of 3.12 and 3.14 looks them up at call time and is counted),
    test_open_road_pathlib_on_3_10. The owner's pass before round 2 of #882 had planted os.statvfs on the served tree read
    and the module stayed green, where os.listdir, os.readlink and os.path.exists planted there each red by the class's
    name."""
    KEYS = ("dir_stat", "dir_lstat", "file_stat")
    CLASSES = ("stat", "lstat", "scandir", "listdir", "access", "readlink", "open", "walk")   # the os functions wrapped; io.open and io.FileIO beside them

    def __init__(self, dirset, root):
        tree = os.path.normpath(str(root))
        self.dirset, self.tree, self.root, self.by, self.census = dirset, tree, tree + os.sep, {}, {}

    def _c(self):
        return self.by.setdefault(threading.get_ident(), dict.fromkeys(self.KEYS, 0))

    def _seen(self, cls, p, dir_fd=None):
        """One call of class `cls` on `p`, counted in this thread's census when `p`, normalized lexically (os.path.abspath),
        is the root or lies under it; a call given a dir_fd, wherever `p` points, under `<cls>(dir_fd)`. A bare descriptor
        is not a path and is not counted (the class docstring)."""
        if dir_fd is not None:
            c = self.census.setdefault(threading.get_ident(), {})
            c[cls + "(dir_fd)"] = c.get(cls + "(dir_fd)", 0) + 1
            return
        if p is None or isinstance(p, int):
            return
        try:
            s = os.fsdecode(p)
        except TypeError:
            s = str(p)
        s = os.path.abspath(s)
        if s == self.tree or s.startswith(self.root):
            c = self.census.setdefault(threading.get_ident(), {})
            c[cls] = c.get(cls, 0) + 1

    def _wrapped(self, cls, real):
        spy = self

        def w(*a, **k):
            spy._seen(cls, a[0] if a else k.get("path", k.get("top")), k.get("dir_fd"))
            return real(*a, **k)
        return w

    def __enter__(self):
        real_stat, real_lstat, real_open, real_fileio, spy = os.stat, os.lstat, io.open, io.FileIO, self

        def st(p, *a, **k):
            s = str(p)
            if s in spy.dirset:
                spy._c()["dir_stat"] += 1
            elif s.startswith(spy.root):
                spy._c()["file_stat"] += 1
            spy._seen("stat", p, k.get("dir_fd"))
            return real_stat(p, *a, **k)

        def lst(p, *a, **k):
            if str(p) in spy.dirset:
                spy._c()["dir_lstat"] += 1
            spy._seen("lstat", p, k.get("dir_fd"))
            return real_lstat(p, *a, **k)

        def opn(f, *a, **k):
            spy._seen("io.open", f)
            return real_open(f, *a, **k)

        class FileIO(real_fileio):                        # a subclass: io.FileIO stays a class inside the window
            def __init__(self, file, *a, **k):
                spy._seen("io.FileIO", file)
                super().__init__(file, *a, **k)
        self._patches = [mock.patch.object(os, "stat", st), mock.patch.object(os, "lstat", lst)]
        self._patches += [mock.patch.object(os, cls, self._wrapped(cls, getattr(os, cls))) for cls in self.CLASSES[2:]]
        self._patches += [mock.patch.object(io, "open", opn), mock.patch.object(builtins, "open", opn),
                          mock.patch.object(io, "FileIO", FileIO)]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.stop()
        return False

    def total(self):
        out = dict.fromkeys(self.KEYS, 0)
        for c in list(self.by.values()):
            for k in out:
                out[k] += c[k]
        return out

    def thread(self, ident):
        return dict(self.by.get(ident) or dict.fromkeys(self.KEYS, 0))

    def tree_calls(self, ident=None):
        """The census: {call class: count} over the filesystem calls under the tree the spy saw through the classes it wraps, summed over threads (one
        thread's when `ident` is given); {} when it saw none. Compared by equality, so a class absent from the expectation
        fails by its name."""
        out = {}
        for i, c in list(self.census.items()):
            if ident is None or i == ident:
                for cls, n in c.items():
                    out[cls] = out.get(cls, 0) + n
        return dict(sorted(out.items()))


class _PathCalls:
    """os.stat and os.lstat calls counted by the exact path they name (os.fspath of the argument; the kernel spells each
    path one way), summed over threads, and the ones made inside _subagent_file_walk counted apart (`walk`), so a count
    can key on the agent-file walk's own calls and not on another reader's stat of the same path in the cycle (the
    cycle stats the transcript and the project directory for reasons of its own). Beside _Spy, which counts the tree's
    directories and files: this one counts any path, the project directory's entries and the sibling roots included. The
    listings too, os.listdir and os.scandir by the directory they list (Path.iterdir lists through os.listdir through
    3.12 and os.scandir from 3.13), so the walk's listing of the project directory is counted on every interpreter. On
    3.10 pathlib stats and lists through the accessor it bound at import (the kernel's counting wrapper, which holds the
    builtin), so the accessor is patched too and Path.iterdir, and any pathlib stat, is counted on every interpreter the
    suite runs; the walk reads each project-directory entry's type by os.stat itself, counted as such everywhere."""

    def __init__(self):
        self.all, self.walk = {}, {}
        self._tl = threading.local()

    def __enter__(self):
        pc, real_walk = self, km._subagent_file_walk

        def counted(cls, real, default=None):
            def f(p=default, *a, **k):
                if p is None:
                    return real(*a, **k)
                if not isinstance(p, int):
                    key = (cls, os.fspath(p))
                    pc.all[key] = pc.all.get(key, 0) + 1
                    if getattr(pc._tl, "depth", 0):
                        pc.walk[key] = pc.walk.get(key, 0) + 1
                return real(p, *a, **k)
            return f

        def walk(*a, **k):
            pc._tl.depth = getattr(pc._tl, "depth", 0) + 1
            try:
                return real_walk(*a, **k)
            finally:
                pc._tl.depth -= 1
        self._patches = [mock.patch.object(os, "stat", counted("stat", os.stat)),
                         mock.patch.object(os, "lstat", counted("lstat", os.lstat)),
                         mock.patch.object(os, "listdir", counted("listdir", os.listdir)),
                         mock.patch.object(os, "scandir", counted("scandir", os.scandir)),
                         mock.patch.object(km, "_subagent_file_walk", walk)]
        acc = getattr(sys.modules.get("pathlib"), "_NormalAccessor", None)   # 3.10 alone
        if acc is not None:
            self._patches += [mock.patch.object(acc, "stat", staticmethod(counted("stat", acc.stat))),
                              mock.patch.object(acc, "lstat", staticmethod(counted("lstat", acc.lstat))),
                              mock.patch.object(acc, "listdir", staticmethod(counted("listdir", acc.listdir))),
                              mock.patch.object(acc, "scandir", staticmethod(counted("scandir", acc.scandir)))]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.stop()
        return False

    def count(self, cls, paths, walk=False):
        """Calls of class `cls` ("stat", "lstat", "listdir" or "scandir") on the given paths, inside the walk alone when
        `walk`."""
        src = self.walk if walk else self.all
        return sum(src.get((cls, str(p)), 0) for p in paths)

    def listings(self, d, walk=True):
        """Listings of the directory `d`, by os.listdir or os.scandir, inside the walk alone by default."""
        return self.count("listdir", [d], walk) + self.count("scandir", [d], walk)

    def entries(self, cls, parent, walk=True):
        """Calls of class `cls` on the entries of the directory `parent` (a path whose dirname is `parent`), inside the walk
        alone by default: the agent-file walk's os.stat per project-directory entry."""
        src = self.walk if walk else self.all
        return sum(n for (c, p), n in src.items() if c == cls and os.path.dirname(p) == str(parent))


class _World(unittest.TestCase):
    """The shared world (tests/test_kernel_pusher_snapshot.py's _CycleFixture, one session): a hermetic state root, the
    session's transcript, name and live row on disk, the awaiting sources stubbed, and beside the transcript a subagents
    tree of D directories with A nested workflow agents, aged past the racy window with the window itself closed (an aged
    fixture's ctime is now, and nothing back-dates ctime: the memo module's precedent). setUp warms the memos with one
    _session_awaiting OUTSIDE any scope, so every cycle a test runs measures the hit paths: the tree memo's validation and
    the agent-file memo's stamp re-check. Every replaced name is put back and every scope slot cleared by cleanups, so a
    failing test cannot leak a cycle's memo into the next on this thread."""

    def setUp(self):
        self.addCleanup(self._restore)                    # registered first: a raise below still restores (cleanups run whatever setUp did)
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        self.saved = {n: getattr(km, n) for n in _KM_SAVED}
        self.saved_jd = {n: getattr(jd, n) for n in ("NAMES", "PROJECTS", "CAPDIR", "ARCHDIR", "GOALDIR", "STATE")}
        self.saved_live = km.Sessions.live
        self.saved_clients = list(km._clients)
        names = td / "names"; names.mkdir()
        proj = td / "projects"; proj.mkdir()
        jd.NAMES, jd.PROJECTS = names, proj
        jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR = td / "captions", td / "archive", td / "goals"
        for d in (jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR):
            d.mkdir()
        jd.STATE = td
        km.NAMES = names
        km._sdk = lambda: None
        cdir = td / "work"; cdir.mkdir()
        pdir = proj / jd.re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
        pdir.mkdir(parents=True)
        rec = {"type": "user", "timestamp": "2026-06-11T00:00:00.000Z", "uuid": "u1", "parentUuid": None,
               "promptSource": "typed", "message": {"role": "user", "content": "hello there"}}
        self.tpath = pdir / (SID + ".jsonl")
        self.tpath.write_text(json.dumps(rec) + "\n")
        self.path = str(self.tpath)
        (names / SID).write_text("web\t%s\t#abcdef\n" % str(cdir))
        # the tree: the root, workflows/, D - 2 workflow directories, the first A each holding one agent's file and sidecar
        self.sub = km._subagents_dir(self.tpath)
        self.wfroot = self.sub / "workflows"
        self.wfroot.mkdir(parents=True)
        self.dirs = [str(self.sub), str(self.wfroot)]
        self.aids = ["a%016x" % (0x7c00 + i) for i in range(A)]
        for i in range(D - 2):
            wf = self.wfroot / ("wf_%016x" % i)
            wf.mkdir()
            self.dirs.append(str(wf))
            if i < A:
                self._add_agent(wf, i, self.aids[i])
        self.assertEqual(len(self.dirs), D)
        self.dirset = set(self.dirs)                      # the spy reads this live set, so a directory a test adds is counted too
        _age(self.sub)
        self.live_aids = list(self.aids)
        km.Sessions.live = lambda: {SID: self._row()}
        km._bg_live_norm = lambda sid, path, live=None: []
        km._bg_pending = lambda sid, path, tasks: tasks
        km._states_awaiting_overlay = lambda sid: None
        km._owned_yield_why = lambda sid, path: None
        km._session_stamp_full = lambda sid: (None, 0, None, None, ())
        km._session_delegated_why = lambda sid: None
        km._session_delegated_identities = lambda sid: []
        km._watches, km._pr_watches = [], []
        km._persist_checkpoints = lambda now: 0            # the checkpoint writer's realpath per checkpointed agent file, and
        km._converge_checkpoints = lambda now: None        #  the spend guard's own walk of the tree (memos.spendTree): separate
        km._spend_guard_tick = lambda now, live_map, **kw: None   # mechanisms, not this memo's path (the module docstring)
        with km._clients_lock:
            km._clients[:] = []                           # no client: the push leg is not the subject, the stubbed job is
        self._files_stat_reset()
        # a steady-state jobs pass, never the boot's first (the _CycleFixture pin: the roster must not depend on what ran before)
        passes = mock.patch.dict(km._PERF_STATS.jobs, {"passes": max(km._PERF_STATS.jobs.get("passes", 0), 1)})
        passes.start()
        self.addCleanup(passes.stop)
        racy = mock.patch.object(km, "_SUBAGENT_DIR_RACY_NS", 0)
        racy.start()
        self.addCleanup(racy.stop)
        self._forget_memos()
        # warm OUTSIDE any scope: the tree memo holds the root and the agent-file memo each agent's nested file
        aw = km._session_awaiting(SID, self.path, True)
        self.assertEqual((aw or {}).get("count"), A, "the warm read sees the A agents: %r" % (aw,))
        self.assertEqual(len(km._SUBAGENT_TREES[str(self.sub)][0]), D, "the walk memo holds the D directories")
        for aid in self.aids:
            self.assertIsNotNone(km._SUBAGENT_FILE_CACHE.get((self.path, aid), (None, None))[1], "each agent's file resolved")

    def _restore(self):
        for n, f in self.saved.items():
            setattr(km, n, f)
        km.Sessions.live = self.saved_live
        for n, v in self.saved_jd.items():
            setattr(jd, n, v)
        with km._clients_lock:
            km._clients[:] = self.saved_clients
        for slot in ("snapshot", "sessions", "paths", "names", "files_stat", "files_dirty", "subtrees"):
            setattr(km._live_scope, slot, None)          # every scope slot, the tree scope included
        self._files_stat_reset()
        km._compact_clicked.clear()
        self._forget_memos()
        self.td.cleanup()

    def _files_stat_reset(self):
        """The ten-file key's standing snapshot, dirty set and observers back to a boot's (the _CycleFixture idiom)."""
        getattr(km, "_FILES_STAT_STANDING", {}).clear()
        getattr(km, "_FILES_STAT_DIRTY", {}).update({"sids": set(), "all": True})
        getattr(km, "_FILES_STAT_OBSERVED", {}).update({"postal": None, "rows": {}, "jdAll": None, "jdBy": {}, "sig": None, "sigMsgs": None})
        km._live_scope.files_dirty = None

    def _forget_memos(self):
        """This session's entries out of the process-wide memos, so no test inherits another's."""
        km._SUBAGENT_TREES.pop(str(self.sub), None)
        km._SUBAGENT_META_CACHE.pop(str(self.sub), None)
        for k in [k for k in list(km._SUBAGENT_FILE_CACHE) if k[0] == self.path]:
            km._SUBAGENT_FILE_CACHE.pop(k, None)
        for k in [k for k in list(km._AGENT_LAUNCH_IDS_CACHE) if str(k).startswith(str(self.sub))]:
            km._AGENT_LAUNCH_IDS_CACHE.pop(k, None)

    def _row(self):
        return {"state": "waiting", "since": NOW - 5, "model": "", "effort": "", "context": None, "compactPct": None,
                "color": None, "mode": "", "backend": "sdk",
                "subagents": [{"type": "Workflow", "since": 100, "agentId": a} for a in self.live_aids]}

    @staticmethod
    def _add_agent(wf, i, aid):
        """A workflow agent's empty transcript and its sidecar (toolUseId, no parentAgentId: the owner is read from the
        other agents' launch folds, so every agent's file is resolved on each _session_awaiting call) in `wf`."""
        (wf / ("agent-%s.meta.json" % aid)).write_text(json.dumps(
            {"agentType": "Workflow", "description": "tidy note %d" % i, "spawnDepth": 1, "toolUseId": "toolu_stamps_%04d" % i}))
        (wf / ("agent-%s.jsonl" % aid)).write_text("")

    def _grow_to(self, n):
        """The world grown to `n` awaiting agents (n at most D - 2): an agent's file and sidecar in each empty workflow
        directory up to n, the tree aged, the live row extended, the memos forgotten and re-warmed OUTSIDE any scope (setUp's
        idiom), so a read over the grown world measures the hit paths as setUp's world does."""
        self.assertLessEqual(n, D - 2)
        for i in range(len(self.aids), n):
            aid = "a%016x" % (0x7c00 + i)
            self._add_agent(self.wfroot / ("wf_%016x" % i), i, aid)
            self.aids.append(aid); self.live_aids.append(aid)
        _age(self.sub)
        self._forget_memos()
        aw = km._session_awaiting(SID, self.path, True)
        self.assertEqual((aw or {}).get("count"), n, "the re-warm sees the %d agents: %r" % (n, aw))
        for aid in self.aids:
            self.assertIsNotNone(km._SUBAGENT_FILE_CACHE.get((self.path, aid), (None, None))[1], "each agent's file resolved")

    def _spy(self):
        return _Spy(self.dirset, self.sub)

    def _open(self):
        """This thread's cycle scope opened directly (the Guards and ScopedInvalidation cases; the clearing point itself is
        pinned through the real cycles), closed by cleanup."""
        km._subagent_scope_open()
        self.addCleanup(km._subagent_scope_close)
        return km._subagent_scope()

    def _read_on_a_thread_with_no_scope(self, root):
        """`root` read once on a helper thread that holds no scope (_live_scope is thread-local): the read a thread holding
        the root never makes inside its cycle, since its served call precedes the root's lstat. Returns what the helper
        saw: its scope (None), _subagent_tree's answer, and the generation right after."""
        errs, seen = [], {}

        def helper():
            try:
                seen["scope"] = _scope()
                seen["answer"] = km._subagent_tree(str(root))
                seen["gen"] = km._SUBAGENT_TREES_GEN[0]
            except Exception:
                errs.append(traceback.format_exc())
        th = threading.Thread(target=helper, name="stamps-popper")
        th.start()
        th.join(30)
        self.assertFalse(th.is_alive(), "the helper returned")
        self.assertEqual(errs, [])
        self.assertIsNone(seen.get("scope"), "the helper thread holds no scope")
        return seen

    @staticmethod
    def _counting_fold(folded):
        """The REAL _agent_launch_ids behind a wrapper that records each file folded, by basename."""
        real_fold = km._agent_launch_ids

        def counting(agent_path, *a, **k):
            folded.append(os.path.basename(str(agent_path)))
            return real_fold(agent_path, *a, **k)
        return mock.patch.object(km, "_agent_launch_ids", counting)

    @staticmethod
    def _stats():
        return dict(km._SUBAGENT_TREE_STATS)

    @staticmethod
    def _delta(before):
        # .get: on a kernel without a counter the delta reads 0 and the pin on it fails with its own message, not a KeyError here
        return {k: km._SUBAGENT_TREE_STATS.get(k, 0) - before.get(k, 0) for k in STAT_KEYS}

    def _awaiting_job(self, rec, spy=None, probe=False):
        """A tick job's stand-in (the pusher's _turn_notify_tick, the pass's _auto_nudge_tick): CALLS _session_awaiting
        reads of the session, as the chat, feed and timeline builds make in one cycle. Records into `rec` rather than
        asserting: the cycle runs each job under a try that writes a raise to stderr and goes on. `spy` given, the
        spy's totals after each call; `probe`, the listing and the sidecar map as read inside the cycle. `asked` records,
        one list per _session_awaiting read, per _subagent_tree call on the session's root that read made, whether the
        scope already held the pair and answered with it ("served") or the call validated or walked ("validated"): the
        premise the bound rests on, that every read reached the memo, is asserted per read, so a read that never asked
        cannot satisfy the bound for nothing; the lists are per read so the assertion can key on the shape (the first ask
        validated, every later one served) and not on how many asks one read makes (round 1 of #882's extra8-1: the flat
        exact list also fixed that number, so a new in-call reader turned the bound cases red over a bound it had not
        touched, with a message that blamed a re-validation)."""
        def job(now, live_map, **kw):
            rec["scope"] = _scope()
            rec["counts"], rec["per_call"], rec["asked"] = [], [], []
            real, root = km._subagent_tree, str(self.sub)

            def asking(d, *a, **k):
                sc = _scope()
                held = (sc["trees"].get(str(d)) if sc is not None else None)   # (the (dirs, stats) pair, the gen it was held under)
                out = real(d, *a, **k)
                if str(d) == root:
                    rec["asked"][-1].append("served" if held is not None and out is held[0] else "validated")
                return out
            with mock.patch.object(km, "_subagent_tree", asking):   # what _subagent_dirs, _subagent_meta_map and the file walk look up
                for _ in range(CALLS):
                    rec["asked"].append([])
                    aw = km._session_awaiting(SID, self.path, True)
                    rec["counts"].append((aw or {}).get("count"))
                    if spy is not None:
                        rec["per_call"].append(spy.total())
            if probe:
                rec["dirs"] = list(km._subagent_dirs(str(self.sub)))
                rec["meta"] = set(km._subagent_meta_map(self.path))
        return job

    def _assert_asks(self, what, asks, d, reads):
        """The premise the bound rests on, keyed on the property and not on a count of asks per read (round 1 of #882's
        extra8-1): `asks` is one list per driven read; every one of the `reads` reads asked the tree memo at least once, and
        flattened, the first ask validated and every later one was served the held pair, however many asks a read makes (a
        new in-call reader adds served asks and leaves this green; a later read that validated again, or one that never
        asked, reds it). Then the counter: memos.subagentTree served moved by exactly the asks the scope answered."""
        flat = [a for bucket in asks for a in bucket]
        self.assertEqual(len(asks), reads, "one list of asks per driven read in one %s: %r" % (what, asks))
        self.assertTrue(all(asks), "every read in one %s reached the tree memo at least once (a bound met because a read never asked is "
                                   "no bound): %r" % (what, asks))
        self.assertEqual(flat, ["validated"] + ["served"] * (len(flat) - 1),
                         "the asks on the root over one %s, flattened: %r; keyed on the shape, the first ask validating and every later "
                         "one served the held pair, not on their number (a later ask that validated again is the per-reader cost the "
                         "scope removes)" % (what, asks))
        self.assertEqual(d["served"], flat.count("served"),
                         "memos.subagentTree served over one %s: %d; keyed on the asks the scope answered from its held pair, %d "
                         "(_subagent_tree's early return alone moves it, so hit + miss + served is the reads of the root; before "
                         "2026-09-21 those reads moved no counter)" % (what, d["served"], flat.count("served")))
        return flat

    def _assert_bound(self, what, sp, d, rec):
        """The per-cycle bound, derived from D and A: the counts one pusher cycle or one jobs pass pays on the tree, read from
        the spy `sp`. The counts first, so a red names the cost, then the census of every call class under the tree by
        equality (so a class the counts do not see fails by name), then the scope's presence inside the cycle and its
        absence after."""
        t, c = sp.total(), sp.tree_calls()
        self.assertEqual(rec.get("counts"), [A] * CALLS, "the stubbed job made its %d reads and each saw the A agents: %r" % (CALLS, rec))
        self._assert_asks(what, rec.get("asked") or [], d, CALLS)
        self.assertEqual(t["dir_stat"], 0,
                         "os.stat on the tree's %d directories over one %s: %d; keyed on 0, the count alone: no agent-file hit's stamp "
                         "re-check (_dir_stamps) reached os.stat (that the tree read was answered the held pair is _assert_asks's identity "
                         "pin, and a re-check through another call class is the census pin below); before the scope it was "
                         "CALLS x A x D = %d, one re-stat of every directory per agent per _session_awaiting call"
                         % (D, what, t["dir_stat"], CALLS * A * D))
        self.assertEqual(t["dir_lstat"], D,
                         "os.lstat on the tree's directories over one %s: %d; the bound is D = %d, the one validation (the root's "
                         "lstat plus one per known directory) held for the cycle by _subagent_scope_hold; before the scope it was "
                         "CALLS x D = %d, one validation per _session_awaiting call" % (what, t["dir_lstat"], D, CALLS * D))
        self.assertEqual((d["hit"], d["miss"], d["evict"]), (1, 0, 0),
                         "memos.subagentTree over one %s: hit %d, miss %d, evict %d; expected one validated hit (was CALLS = %d), "
                         "no walk and nothing evicted (the pass's forget keeps the alive session's root)"
                         % (what, d["hit"], d["miss"], d["evict"], CALLS))
        self.assertEqual(d["dirStats"], D - 1,
                         "memos.subagentTree dirStats over one %s: %d; expected D - 1 = %d, the one validation's lstats, the stamp "
                         "re-checks paying no stat; before the scope it was CALLS x (D - 1) = %d, and the A x D re-check stats were "
                         "not counted at all" % (what, d["dirStats"], D - 1, CALLS * (D - 1)))
        self.assertEqual(t["file_stat"], A,
                         "os.stat on the agent files over one %s: %d; expected A = %d, one launch fold per agent per cycle "
                         "(_awaiting_nest's launches held in the scope); before it was CALLS x A = %d" % (what, t["file_stat"], A, CALLS * A))
        self.assertEqual(c, {"lstat": D, "stat": A},
                         "filesystem calls under the tree over one %s, by call class (the census wraps os.%s, io.open and io.FileIO on "
                         "every path that is the root or under it, and counts every call given a dir_fd): %r; keyed on equality with "
                         "{lstat: D = %d, stat: A = %d}, the one validation's lstats and the A agent-file stats and nothing else, "
                         "so a read of the tree through any other class, or one more of these, fails here by the class's name (a "
                         "guarded listing, an access or an open on a served path moves none of the counts above)" % (what, ", ".join(_Spy.CLASSES), c, D, A))
        self.assertIsNotNone(rec.get("scope"), "the %s opened the subagents-tree scope on its thread (_subagent_scope_open)" % what)
        self.assertTrue(getattr(km._live_scope, "subtrees", None) is None,
                        "the scope ends with the %s (_subagent_scope_close in its finally): the slot still holds a scope" % what)


    def _miss_walk_cycle(self, G):
        """One pusher cycle over the world plus G live agent rows whose file exists nowhere, under the own tree or a
        sibling's (the ghosts), with the miss path's costs that are each row's own asserted here, derived from D, A and G:
        each row's first owner lookup walks once (the walk misses and the scope's launches map holds set() for it, so the
        rest of the cycle is served), the walk's dependency notes to the running chat build (the absent own place, every
        directory of each tree it looked through) come from the pair the lookup was answered, the served tree, so they cost
        no stat on the tree's directories (0 os.stat; round 1 of #882's correctness-1: the own tree's note was a fresh
        _chat_stat_key stat, 1 per walk), and each walk pays W lstats of the own root, its two symlink checks (os.path.islink,
        and os.path.realpath's lstat per component), counted by running those two calls, and one os.lstat per candidate
        file, the flat place and one per served directory (D + 1, the flat place being the own root's candidate, so its
        path is read twice), counted by path inside the walk (_PathCalls), with no os.stat of any file under the tree but
        the A folds'. The walk's own ask on the root is among the first read's and is
        served, not a second validation: the asks are asserted by shape, and served by the asks the scope answered
        (_assert_asks). And each walk lists the project directory once and stats each of its E entries once (os.stat, its
        type, files included), G listings and G x E stats over the cycle, counted inside the walk (_PathCalls) and paid per walk,
        not shared: the cost home's miss-walk term (_subagent_tree_memo_report's docstring; round 2 of #882, fresh-2, and
        the listing since the pass applying its rulings), the stats red under a kernel that holds the entries' types for
        the cycle (E at G = 2) and the listings under one that lists the directory twice per walk (2G). What the rows SHARE, the project directory's one stamp stat in dirStats,
        the caller asserts: one row and two rows pay the same. Returns (the spy's totals, the counters' delta, the job's
        record, the ghosts)."""
        ghosts = ["a%016x" % (0x7cf1 + i) for i in range(G)]
        self.live_aids.extend(ghosts)                         # in the live row; no sidecar and no file anywhere
        own = str(self.sub)
        with self._spy() as sp0:
            os.path.islink(own); os.path.realpath(own)
        W = sp0.total()["dir_lstat"]
        proj = Path(self.path).parent
        E = len(list(proj.iterdir()))                         # the project directory's entries: the transcript and the session directory
        rec = {}
        km._turn_notify_tick = self._awaiting_job(rec)
        b = self._stats()
        with self._spy() as sp, _PathCalls() as pc:
            km._pusher_cycle()
        t, d = sp.total(), self._delta(b)
        self.assertEqual(pc.entries("stat", proj), G * E,
                         "os.stat on the project directory's entries inside the agent-file walk over one pusher cycle: %d; keyed on "
                         "G x E = %d x %d, each walk's os.stat per entry (its type), paid per walk and held nowhere (a kernel that shares the "
                         "entries' types across the cycle's walks pays E)" % (pc.entries("stat", proj), G, E))
        self.assertEqual(pc.listings(proj), G,
                         "listings of the project directory inside the agent-file walk over one pusher cycle: %d; keyed on G = %d, "
                         "each walk's one Path.iterdir, paid per walk, held nowhere and counted by no counter (a walk that lists it "
                         "twice pays 2G)" % (pc.listings(proj), G))
        what = "pusher cycle with the miss walk" if G == 1 else "pusher cycle with %d miss walks" % G
        self.assertEqual(rec.get("counts"), [A + G] * CALLS, "each of the %d reads saw the A agents and the %d rows nobody owns: %r" % (CALLS, G, rec))
        flat = self._assert_asks(what, rec.get("asked") or [], d, CALLS)
        self.assertGreater(len(flat), CALLS, "the asks on the root: %r; the miss walk asked the tree too, beyond the %d reads' own asks "
                                             "(and was served: the shape above)" % (rec.get("asked"), CALLS))
        self.assertEqual(t["dir_stat"], 0,
                         "os.stat on the tree's %d directories over one %s: %d; keyed on 0, the count alone: neither the walk's notes "
                         "to the chat build nor the stamp re-checks reached os.stat (which object answered them is _assert_asks's identity "
                         "pin for the tree read, not this count; round 1 of #882: the own tree's note was a fresh stat, 1 per walk)"
                         % (D, what, t["dir_stat"]))
        self.assertEqual(t["dir_lstat"], D + G * W,
                         "os.lstat on the tree's directories: %d; expected D + G x W = %d + %d x %d, the one validation plus each walk's "
                         "symlink checks of the own root" % (t["dir_lstat"], D, G, W))
        self.assertEqual(t["file_stat"], A,
                         "os.stat on files under the tree: %d; expected A = %d, one fold per agent with a file and nothing else: the walk "
                         "reads its candidates by os.lstat (until round 3 of #882, group A, by os.path.isfile, an os.stat each, A + G x "
                         "(D + 1) = %d)" % (t["file_stat"], A, A + G * (D + 1)))
        cand_lstats = sum(pc.count("lstat", [os.path.join(x, "agent-%s.jsonl" % gh) for x in self.dirs], walk=True) for gh in ghosts)
        self.assertEqual(cand_lstats, G * (D + 1),
                         "os.lstat on the ghosts' candidate files inside the agent-file walk: %d; expected G x (D + 1) = %d x (%d + 1), each "
                         "walk's flat place and one candidate per served directory, the own root's candidate being the flat place's path "
                         "read a second time" % (cand_lstats, G, D))
        self.assertEqual((d["hit"], d["miss"], d["evict"]), (1, 0, 0), "one validated hit, no walk of the tree, nothing evicted: %r" % (d,))
        for ghost in ghosts:
            self.assertIsNone(km._SUBAGENT_FILE_CACHE.get((self.path, ghost), (None, "unset"))[1], "the miss is memoized: the file is nowhere")
        return t, d, rec, ghosts


class BoundPerCycleAndPerPass(_World):
    """(1) The bound: a tree is validated once per pusher cycle and once per jobs pass, however many readers."""

    def test_one_pusher_cycle_validates_the_tree_once_however_many_readers(self):
        rec = {}
        km._turn_notify_tick = self._awaiting_job(rec)    # a _job_stage job of _pusher_cycle_jobs, after the push leg
        b = self._stats()
        with self._spy() as sp:
            km._pusher_cycle()
        self._assert_bound("pusher cycle", sp, self._delta(b), rec)

    def test_one_jobs_pass_validates_the_tree_once_however_many_readers(self):
        rec = {}
        km._auto_nudge_tick = self._awaiting_job(rec)     # where the real pass reaches _session_awaiting (the nudge look)
        b = self._stats()
        with self._spy() as sp:
            km._jobs_cycle()
        self._assert_bound("jobs pass", sp, self._delta(b), rec)
        self.assertIn(str(self.sub), km._SUBAGENT_TREES, "the interrupt tick's forget kept the alive session's root")

    def test_one_pusher_cycle_with_an_agent_whose_file_is_nowhere_walks_once_and_its_notes_cost_no_stat(self):
        """The miss path inside the bound (fresh-4 of the round-1 review: no case entered it): one live agent row whose file
        exists nowhere. Its own costs are _miss_walk_cycle's assertions; here, the project directory's one stamp stat, in
        dirStats and outside the tree (the two-row case beside this one pins that it is shared)."""
        t, d, rec, ghosts = self._miss_walk_cycle(1)
        self.assertEqual(d["dirStats"], D,
                         "dirStats %d; expected (D - 1) + 1 = %d: the validation's lstats plus the project directory's one stamp stat, "
                         "the walk's, held for the cycle under no root" % (d["dirStats"], D))

    def test_two_agents_whose_files_are_nowhere_share_the_project_directorys_one_stamp_stat(self):
        """The project directory's stamp stat, one term of the miss walk in the cost home, is once per cycle, SHARED by
        every agent whose file is nowhere or under a sibling's tree, not once per such agent (the owner's pass before round
        2 of #882: the term's homes read per agent, G such rows paying G project-directory stats where the code pays 1; the
        home is _subagent_tree_memo_report's docstring). Two such rows: each walks once and pays its own candidate lstats and symlink
        checks (G x, _miss_walk_cycle), but the project directory's stamp stat is an own stat _dir_stamp holds in the scope
        keyed by directory under root None, so the first walk pays it and the second walk, and every re-check of either row
        in the cycle, is served it: dirStats moves by (D - 1) + 1, not (D - 1) + G, and the scope's stamps map holds the
        directory once, under root None. Own stats keyed per (agent, directory) leave the one-row case green and turn this
        one red (dirStats D + 1), which is why the bound has a two-row case."""
        G = 2
        t, d, rec, ghosts = self._miss_walk_cycle(G)
        self.assertEqual(d["dirStats"], D,
                         "dirStats %d; expected (D - 1) + 1 = %d, not (D - 1) + G = %d: the project directory's one stamp stat, an own stat "
                         "keyed by directory under root None, paid by the first of the %d walks and served to the other and to every "
                         "re-check in the cycle (once per cycle, shared, whatever the number of agents whose file is nowhere)"
                         % (d["dirStats"], D, (D - 1) + G, G))
        stamps = (rec.get("scope") or {}).get("stamps") or {}
        proj = str(Path(self.path).parent)
        held = stamps.get(proj)
        self.assertIsNotNone(held, "the scope's stamps map holds the project directory under its path (the served entry both walks and "
                                   "every re-check keyed on): %r" % (sorted(str(k) for k in stamps),))
        self.assertIsNone(held[1], "the project directory's stamp is an own stat, vouched by no root (root None): %r" % (held,))
        self.assertEqual([k for k in stamps if str(k).startswith(proj) and k not in self.dirset and not str(k).startswith(str(self.sub))], [proj],
                         "the project directory is held once, keyed by directory alone and not per agent: %r" % (sorted(str(k) for k in stamps),))

    def test_the_served_tree_read_the_served_stamp_and_the_agent_file_hit_make_no_filesystem_call_of_any_class_the_census_wraps_under_the_tree(self):
        """The premise the bound's zeros rest on, by census rather than by two counts (the owner's pass before round 2 of
        #882: the count pins saw os.stat and os.lstat alone, so a guarded os.scandir, an os.access or an os.open on the
        served tree path, and a listing on _dir_stamp's served path, left the module green). Inside one scope, after the
        hold, each of the three served paths runs under the spy's census on its own: the tree read _subagent_tree answers
        from the held pair, the stamp _dir_stamp answers from the held stamps, and the agent-file hit _subagent_file answers
        from its memo with its stamp re-check served. Each makes no filesystem call of any class the census wraps on any
        path that is the root or under it and no call given a dir_fd, keyed on the census == {} per path, so a new call
        class on a served path fails here by its name and by the path it ran on."""
        root, aid, sd = str(self.sub), self.aids[0], self.dirs[3]
        sc = self._open()
        km._subagent_tree(root)                              # the hold: the cycle's one validation, its stamps indexed
        self.assertIn(root, sc["trees"], "premise: the pair is held")
        self.assertIn(sd, sc["stamps"], "premise: the directory's stamp is held, indexed from the tree")
        self.assertIsNotNone(km._SUBAGENT_FILE_CACHE.get((self.path, aid), (None, None))[1], "premise: the agent's file is memoized (setUp's warm read)")
        classes = "os.%s, io.open and io.FileIO on the root or under it, or any call given a dir_fd" % ", ".join(_Spy.CLASSES)
        b = self._stats()
        with self._spy() as sp:
            pair = km._subagent_tree(root)
        self.assertIs(pair, sc["trees"][root][0], "premise: the tree read was answered the held pair")
        self.assertEqual(self._delta(b)["served"], 1, "premise: the read moved served")
        self.assertEqual(sp.tree_calls(), {},
                         "filesystem calls under the tree on the served tree read, by class: %r; keyed on {} (no call the census counts: "
                         "%s); a listing, an access or an open on this path shows here by name"
                         % (sp.tree_calls(), classes))
        with self._spy() as sp:
            st = km._dir_stamp(sd)
        self.assertEqual(st, sc["stamps"][sd][0], "premise: the stamp was answered the held one")
        self.assertEqual(sp.tree_calls(), {},
                         "filesystem calls under the tree on the served stamp, by class: %r; keyed on {} (%s); a listing of the directory or "
                         "its parent on this path shows here by name" % (sp.tree_calls(), classes))
        with self._spy() as sp:
            ap = km._subagent_file(self.path, aid)
        self.assertEqual(ap, km._SUBAGENT_FILE_CACHE[(self.path, aid)][1], "premise: the hit was answered the memo's resolution")
        self.assertEqual(sp.tree_calls(), {},
                         "filesystem calls under the tree on the agent-file hit, by class: %r; keyed on {} (%s): the stamp re-check served "
                         "from the scope and nothing read of the file itself; an lstat of the cached file or a listing shows here by name"
                         % (sp.tree_calls(), classes))

    def test_outside_a_cycle_every_reader_validates_for_itself_and_dirstats_counts_both_validators(self):
        """A handler thread's read (a WS or HTTP build, the act-now nudge pass) holds no scope and pays what it paid: the
        tree's validation and, per agent, the file memo's re-check of every directory its walk read. That cost is now
        VISIBLE: dirStats counts both validators' directory stats (the lstat half alone before this change, so the field
        figure across the deploy is not one series)."""
        self.assertIsNone(_scope(), "no scope is open on this thread outside a cycle")
        b = self._stats()
        with self._spy() as sp:
            aw = km._session_awaiting(SID, self.path, True)
        t, d = sp.total(), self._delta(b)
        self.assertEqual(aw["count"], A)
        self.assertEqual(t["dir_stat"], A * D, "each agent's file hit re-stats the D directories its walk read: A x D = %d, unchanged "
                                               "outside a cycle by design" % (A * D))
        self.assertEqual(t["dir_lstat"], D, "the tree's one validation for this call")
        self.assertEqual(t["file_stat"], A, "one launch fold per agent")
        self.assertEqual((d["hit"], d["miss"]), (1, 0))
        self.assertEqual(d["served"], 0, "memos.subagentTree served over a read outside any cycle: %d; keyed on 0, no scope held a pair "
                                         "to answer from (the counter moves on _subagent_tree's scope early return alone, never on a "
                                         "validated hit)" % d["served"])
        self.assertEqual(d["dirStats"], (D - 1) + A * D,
                         "dirStats %d; expected (D - 1) + A x D = %d: the validation's lstats AND the stamp re-checks' stats, both "
                         "counted since 2026-09-19 (_dir_stamp counts each os.stat it takes); the lstat half alone, D - 1 = %d, "
                         "was the count before" % (d["dirStats"], (D - 1) + A * D, D - 1))


class MissPathRoads(_World):
    """(10) The agent-file lookup's roads the cost home names beside the bound, each derived here from the world's sizes
    and pinned through the real _pusher_cycle (round 2 of #882, group D: extra6-1, correctness-2, fresh-2; the home is
    _subagent_tree_memo_report's docstring, and each of its entries names the case that pins it): an absent sibling
    root, a sibling tree the agent-file walk reads, and a command row whose owner is read from the agents' transcripts
    before the tree is read. G live rows name an agent whose file exists nowhere (the ghosts); each cycle makes CALLS
    _session_awaiting reads and then looks each ghost up M more times, as the chat build's Agent head (_stamp_agents) and
    an open viewer (_subagent_frame_cached, build_subagent) look an agent up. A ghost's first cycle is cold (its walk
    runs, memoizing the miss), the next steady (each lookup a memo hit re-checking the walk's stamps). Every count is
    derived in the case from D, A, CALLS, G, K, S, M and the interpreter's realpath, which is counted by running it."""

    M = 2   # a ghost's lookups per cycle beyond the one _awaiting_nest makes (its held launch fold answers the rest)

    def _absent_roots(self, k):
        """K session directories with no subagents/ in the project directory (a tool-results directory alone, the shape
        most session directories have): places the walk stamps and never finds a tree at. Returns those places."""
        proj = Path(self.path).parent
        out = []
        for i in range(k):
            d = proj / ("11111111-2222-3333-4444-7c7c7c7c%04x" % (0xa000 + i))
            (d / "tool-results").mkdir(parents=True)
            out.append(str(d / "subagents"))
        return out

    def _sibling_trees(self, s, dsib):
        """S sibling sessions in the project directory, each a transcript and a subagents tree of dsib directories (the
        root, workflows/ and dsib - 2 workflow directories), aged and not in the walk memo. Returns {root: its directories}."""
        proj = Path(self.path).parent
        out = {}
        for i in range(s):
            sid = "11111111-2222-3333-4444-7c7c7c7c%04x" % (0xb000 + i)
            (proj / (sid + ".jsonl")).write_text("")
            root = proj / sid / "subagents"
            (root / "workflows").mkdir(parents=True)
            dirs = [str(root), str(root / "workflows")]
            for j in range(dsib - 2):
                wf = root / "workflows" / ("wf_%016x" % (0x7c00 + j))
                wf.mkdir()
                dirs.append(str(wf))
            _age(root)
            self.addCleanup(km._SUBAGENT_TREES.pop, str(root), None)
            self.addCleanup(km._SUBAGENT_META_CACHE.pop, str(root), None)
            out[str(root)] = dirs
        return out

    def _ghosts(self, g, base):
        """G ghost ids from `base`, the live row set to the A agents and them (a ghost from another G is not looked up)."""
        ghosts = ["a%016x" % (base + i) for i in range(g)]
        self.live_aids[:] = list(self.aids) + ghosts
        for gh in ghosts:
            self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, (self.path, gh), None)
        return ghosts

    def _cycle(self, ghosts, what):
        """One pusher cycle: CALLS _session_awaiting reads, then M lookups of each ghost. Returns (the path calls, the
        counters' delta)."""
        rec = {}

        def job(now, live_map, **kw):
            rec["counts"] = [(km._session_awaiting(SID, self.path, True) or {}).get("count") for _ in range(CALLS)]
            rec["extra"] = [km._subagent_file(self.path, gh) for gh in ghosts for _ in range(self.M)]
        km._turn_notify_tick = job
        b = self._stats()
        with _PathCalls() as pc:
            km._pusher_cycle()
        self.assertEqual(rec.get("counts"), [A + len(ghosts)] * CALLS, "%s: each read saw the A agents and the ghosts: %r" % (what, rec))
        self.assertEqual(rec.get("extra"), [None] * (len(ghosts) * self.M), "%s: each extra lookup found the ghost's file nowhere" % what)
        return pc, self._delta(b)

    def test_each_absent_sibling_root_costs_one_failed_stat_per_lookup_of_each_agent_whose_file_is_nowhere_and_moves_no_counter(self):
        """The absent-sibling-root term: a directory in the project directory with no subagents/ under it (K of them)
        costs one os.stat of its subagents place per agent-file lookup of each agent whose file is nowhere, the walk's own
        and every memo hit's re-check of the stamps the walk took, which hold (place, None): G x K x (1 + M) per cycle,
        cold or steady. The stat raises, and a stat that raises is never held (_dir_stamp) and counts in no counter, so
        dirStats stays at (D - 1) + 1, the validation and the project directory's stamp, whatever G and K. The cold walk
        also lstats each place twice over, _subagent_tree's root lstat (answered ((), ()), not held) and _find_agent_file's
        realpath (its lstat count on the place taken by running it, W_abs): G x K x (1 + W_abs), none in the steady
        cycle. A boundary pin, green by design at the head round 2 of #882 reviewed (the per-lookup stat was already paid
        there; the round found the home omitting it, not the code paying it) and red under a kernel that holds an absent
        stamp for the cycle, which pays K per cycle whatever G and M."""
        K = 2
        absent = self._absent_roots(K)
        with _PathCalls() as pc0:
            os.path.realpath(absent[0])
        w_abs = pc0.count("lstat", absent[:1])
        for G in (1, 2, 3):
            with self.subTest(G=G):
                ghosts = self._ghosts(G, 0x7d00 + 0x10 * G)
                for phase in ("cold", "steady"):
                    what = "the %s cycle at G = %d, K = %d, M = %d" % (phase, G, K, self.M)
                    pc, d = self._cycle(ghosts, what)
                    got = pc.count("stat", absent)
                    self.assertEqual(got, G * K * (1 + self.M),
                                     "os.stat on the absent sibling subagents places over %s: %d; keyed on G x K x (1 + M) = %d, one "
                                     "failed stat per lookup per agent whose file is nowhere, never held; a kernel that holds the "
                                     "absent stamp for the cycle pays K = %d" % (what, got, G * K * (1 + self.M), K))
                    lst = pc.count("lstat", absent)
                    self.assertEqual(lst, G * K * (1 + w_abs) if phase == "cold" else 0,
                                     "os.lstat on the absent places over %s: %d; keyed on G x K x (1 + W_abs) = %d x %d x (1 + %d) in "
                                     "the cold cycle (each walk's root lstat and realpath) and 0 in the steady one (no walk)"
                                     % (what, lst, G, K, w_abs))
                    self.assertEqual((d["dirStats"], d["hit"], d["miss"], d["evict"]), (D, 1, 0, 0),
                                     "(dirStats, hit, miss, evict) over %s: %r; keyed on ((D - 1) + 1, 1, 0, 0): the validation and "
                                     "the project directory's one stamp stat, the failed stats counted nowhere"
                                     % (what, (d["dirStats"], d["hit"], d["miss"], d["evict"])))

    def test_a_sibling_tree_the_walk_reads_is_read_once_per_cycle_and_costs_a_candidate_lstat_per_directory_per_walk(self):
        """The sibling-tree term: S sibling sessions with subagents trees of DSIB directories each, G agents whose file is
        nowhere. The cold cycle (the ghosts' walks): each sibling's tree read once, a walk (miss S; its listings and lstats
        are the walk term's, pinned in Guards), shared by the G walks, every later walk served it; each sibling root's stamp
        taken once as an own stat before its tree is read (dirStats + S), then served from the tree's index; and per walk,
        per sibling tree, one lstat of the root by _find_agent_file's realpath (W_sib, counted by running it) and one os.lstat
        per candidate place, one per directory: G x S x DSIB candidate lstats and S x DSIB + G x S x W_sib lstats on the
        sibling directories. The steady cycle (the ghosts' memo hits): no sibling tree is read, and each lookup's re-check
        of the walk's stamps pays one own stat per sibling directory, taken by the first lookup and held under root None,
        so S x DSIB stats per cycle whatever G and M, all in dirStats. Red in the cold cycle under a kernel that reads a
        sibling's tree again for every walk (miss G x S) and under one that holds no own stat (each lookup's re-check paying
        its own stats, dirStats past (D - 1) + 1 + S)."""
        S, DSIB, G = 2, 4, 2
        sibs = self._sibling_trees(S, DSIB)
        roots = list(sibs)
        sdirs = [x for r in roots for x in sibs[r]]
        with _PathCalls() as pc0:
            os.path.realpath(roots[0])
        w_sib = pc0.count("lstat", roots[:1])
        ghosts = self._ghosts(G, 0x7e00)
        cands = [os.path.join(x, "agent-%s.jsonl" % gh) for x in sdirs for gh in ghosts]
        pc, d = self._cycle(ghosts, "the cold cycle")
        got = (d["miss"], pc.count("lstat", sdirs), pc.count("lstat", cands), pc.count("stat", cands), pc.count("stat", sdirs),
               d["dirStats"])
        want = (S, S * DSIB + G * S * w_sib, G * S * DSIB, 0, S, (D - 1) + 1 + S)
        self.assertEqual(got, want,
                         "the cold cycle at S = %d, DSIB = %d, G = %d, W_sib = %d: (miss, lstats on the sibling directories, candidate "
                         "lstats, candidate stats, stats on the sibling directories, dirStats) = %r; keyed on (S, S x DSIB + G x S x "
                         "W_sib, G x S x DSIB, 0, S, (D - 1) + 1 + S) = %r: each sibling tree walked once for all the walks, each walk's "
                         "realpath of each root and its candidate lstat per directory (an os.stat each, by os.path.isfile, until round "
                         "3 of #882, group A), each root's stamp once before its tree was read"
                         % (S, DSIB, G, w_sib, got, want))
        pc, d = self._cycle(ghosts, "the steady cycle")
        got = (d["miss"], pc.count("lstat", sdirs), pc.count("lstat", cands), pc.count("stat", cands), pc.count("stat", sdirs),
               d["dirStats"])
        want = (0, 0, 0, 0, S * DSIB, (D - 1) + 1 + S * DSIB)
        self.assertEqual(got, want,
                         "the steady cycle: (miss, lstats on the sibling directories, candidate lstats, candidate stats, stats on the "
                         "sibling directories, dirStats) = %r; keyed on (0, 0, 0, 0, S x DSIB, (D - 1) + 1 + S x DSIB) = %r: no sibling "
                         "tree read and no walk, and one own stat per sibling directory, held and shared by the G x (1 + M) re-checks"
                         % (got, want))

    def test_a_command_rows_owner_lookup_before_the_tree_is_read_re_stats_its_directories_once_per_cycle(self):
        """The own stats a command row adds: a background command whose owner is read from the agents' transcripts (no
        launch-ledger owner) makes _awaiting_nest consult every agent's launches before the tree is read in the read that
        makes it, so the first agent's memo hit re-checks the tree's D directories as own stats (held under root None,
        every later re-check served), and the validation after it re-indexes them: D os.stat on the tree's directories and
        dirStats (D - 1) + D per cycle, where a cycle with no command row pays 0 and D - 1 (the bound's cases)."""
        cmd = {"tid": "toolu_stamps_cmd4", "desc": "run the api tests", "t": 130, "type": "local_bash"}
        km._bg_live_norm = lambda sid, path, live=None: [cmd]
        rec = {}
        km._turn_notify_tick = self._awaiting_job(rec)
        b = self._stats()
        with self._spy() as sp:
            km._pusher_cycle()
        t, d = sp.total(), self._delta(b)
        self.assertEqual(rec.get("counts"), [A + 1] * CALLS, "each read saw the A agents and the command row: %r" % (rec,))
        got = (t["dir_stat"], t["dir_lstat"], d["dirStats"], d["hit"], d["miss"])
        self.assertEqual(got, (D, D, (D - 1) + D, 1, 0),
                         "(os.stat and os.lstat on the tree's directories, dirStats, hit, miss) over one pusher cycle with a command "
                         "row: %r; keyed on (D, D, (D - 1) + D, 1, 0) = %r: the owner lookup's re-check of the D stamps before the "
                         "tree's read, once per cycle, then the one validation" % (got, (D, D, (D - 1) + D, 1, 0)))


class PerCycleNotSticky(_World):
    """(2) The memo is the cycle's, never longer: what lands between cycles is seen by the next; what lands after a
    cycle's validation waits for the next, one cycle at most."""

    def test_a_directory_and_an_agent_landing_between_cycles_are_seen_by_the_next_cycle(self):
        rec1 = {}
        km._turn_notify_tick = self._awaiting_job(rec1)
        km._pusher_cycle()                                # cycle one: the tree held for the cycle, released with it
        self.assertEqual(rec1["counts"], [A] * CALLS)
        # between the cycles: a new workflow directory with a fourth agent's file and sidecar; the agent joins the live row
        new_aid = "a%016x" % 0x7cff
        wf_new = self.wfroot / ("wf_%016x" % 0x7cff)
        wf_new.mkdir()
        self._add_agent(wf_new, 99, new_aid)
        _age(self.sub)
        self.dirs.append(str(wf_new)); self.dirset.add(str(wf_new)); self.live_aids.append(new_aid)
        rec2 = {}
        sp = self._spy()
        km._turn_notify_tick = self._awaiting_job(rec2, spy=sp, probe=True)
        b = self._stats()
        with sp:
            km._pusher_cycle()                            # cycle two: its first read walks again, its later reads are served
        t, d = sp.total(), self._delta(b)
        ref = sorted(r for r, _ds, _fs in os.walk(str(self.sub)))
        self.assertEqual(sorted(rec2.get("dirs") or []), ref,
                         "cycle two's listing is the disk's, the new directory included: the memo is per cycle, not sticky")
        self.assertIn("toolu_stamps_0099", rec2.get("meta") or set(), "the new sidecar reached the map in cycle two")
        self.assertEqual(rec2.get("counts"), [A + 1] * CALLS, "every read in cycle two saw the fourth agent: %r" % (rec2,))
        self.assertEqual(d["miss"], 1, "cycle two's first read walked the tree again (workflows/ changed): one miss, not one per reader")
        self.assertEqual(t["dir_stat"], 0, "os.stat on the tree's %d directories over cycle two: %d; keyed on 0, the count alone: no "
                                           "agent-file re-check reached os.stat after the cycle's walk (before the scope each later read alone "
                                           "paid (A + 1) x D = %d)"
                         % (D + 1, t["dir_stat"], (A + 1) * (D + 1)))
        per = rec2.get("per_call") or []
        self.assertEqual(len(per), CALLS)
        later = [(c["dir_lstat"] - per[i - 1]["dir_lstat"], c["dir_stat"] - per[i - 1]["dir_stat"]) for i, c in enumerate(per) if i]
        self.assertEqual(later, [(0, 0)] * (CALLS - 1),
                         "the later reads in cycle two cost no directory stat at all (lstat, stat per call): %r; each paid D = %d "
                         "lstats and (A + 1) x D stats before the scope" % (later, D + 1))
        self.assertGreaterEqual(per[0]["dir_lstat"], D + 1, "the first read paid the walk (the root and each child by lstat)")

    def test_a_launch_appended_between_cycles_is_folded_by_the_next_cycle_and_nests_its_command_there(self):
        """The launch half of the rule, the contract _awaiting_nest states (a launch appended mid-cycle nests on the next
        cycle): the launch folds are the cycle's, released with the scope, so a launch appended to agent 0's transcript
        between two cycles is folded by the second cycle's first read (one fold per agent, A) and the command it names nests
        under agent 0 there. Keys on the folds in cycle two and on the nesting: a launches map carried from one cycle to the
        next folds nothing in cycle two (0) and leaves the command top-level for as long as it is carried. Until this case no
        case counted folds in a second cycle, so the release edge at the cycle's end had no pin of its own."""
        cmd = {"tid": "toolu_stamps_cmd2", "desc": "run the parser test chunk", "t": 130, "type": "local_bash"}
        km._bg_live_norm = lambda sid, path, live=None: [cmd]
        names = sorted("agent-%s.jsonl" % a for a in self.aids)
        rec1, rec2, folded = {}, {}, []
        km._turn_notify_tick = lambda now, live_map, **kw: rec1.setdefault("aw", km._session_awaiting(SID, self.path, True))
        with self._counting_fold(folded):
            km._pusher_cycle()                            # cycle one: the folds held, the command attributed to nobody
        self.assertEqual(((rec1.get("aw") or {}).get("count"), sorted(folded)), (A + 1, names),
                         "cycle one: the A agents and the command, top-level, one fold per agent: %r" % (rec1.get("aw"),))
        ap = self.wfroot / ("wf_%016x" % 0) / ("agent-%s.jsonl" % self.aids[0])
        ap.write_text(json.dumps({"type": "assistant", "timestamp": "2026-09-10T10:00:00.000Z", "message": {"content": [
            {"type": "tool_use", "id": cmd["tid"], "name": "Bash",
             "input": {"run_in_background": True, "command": "uv run pytest tests/test_parser.py -q", "description": cmd["desc"]}}]}}) + "\n")
        del folded[:]
        km._turn_notify_tick = lambda now, live_map, **kw: rec2.setdefault("aw", km._session_awaiting(SID, self.path, True))
        with self._counting_fold(folded):
            km._pusher_cycle()                            # cycle two: every fold redone, agent 0's names the launch
        aw2 = rec2.get("aw") or {}
        self.assertEqual(sorted(folded), names,
                         "folds in cycle two: %r; keyed on every agent's fold redone (A = %d, one each), since the launch folds are the "
                         "cycle's and the next cycle's first read folds again; a launches map carried across cycles folds nothing (0) and "
                         "the launch appended between the cycles is never seen" % (sorted(folded), A))
        self.assertEqual(aw2.get("count"), A, "cycle two: the command nests under agent 0, whose fresh fold names its launch: %r" % (aw2,))
        agent0 = [it for it in aw2.get("items", []) if it.get("agentId") == self.aids[0]]
        self.assertEqual([w["id"] for w in (agent0[0].get("waits", []) if agent0 else [])], [cmd["tid"]],
                         "the command row nested under agent 0 in cycle two: %r" % (agent0,))

    def test_the_stamps_held_for_a_cycle_are_released_at_its_end_so_the_next_cycle_re_takes_the_project_directorys_stamp(self):
        """The stamps memo's release at the cycle's end, pinned on its own (the owner's pass before round 2 of #882: a stamps
        map carried across cycles on this thread, the trees and launches released as today, reddened one case in the module,
        at a dependency-key outcome whose message named neither the stamps memo nor the cycle's end). Cycle one is the
        miss-path bound case, one row whose file is nowhere (_miss_walk_cycle asserts its costs): its walk stats the project
        directory once, an own stat _dir_stamp holds under root None. Cycle two over the same world, unchanged: the tree's one
        validation (D - 1 lstats into dirStats) and the row's memoized miss re-checked, whose project-directory stamp the new
        scope does not hold, so it is re-taken (+1). Three pins, each keyed on what it names (the owner's pass before round 2
        of #882, its fixes-by-execution lens: the count alone reds identically under a carried LAUNCHES map, whose served fold
        makes no lookup in cycle two, so no project-directory stat is owed, and the count's message blamed the stamps map):
        the lookup was made in cycle two, keyed on cycle two's scope holding the project directory's stamp under root None (a
        carried launches map reds here); the stamps map was released, keyed on cycle two's stamps map and its entry being
        objects other than cycle one's (a carried stamps map reds here, by identity); and then the count, cycle two's dirStats
        == (D - 1) + 1 = D, keyed on the count alone. Keyed on dirStats, the memo's own counter, and not on a raw count of
        os.stat on the project directory, which the cycle stats once more for reasons of its own (_discover_fingerprint)."""
        proj = str(Path(self.path).parent)
        t1, d1, rec1, ghosts = self._miss_walk_cycle(1)
        self.assertIsNone(getattr(km._live_scope, "subtrees", None), "premise: cycle one's scope is closed (its finally ran)")
        stamps1 = (rec1.get("scope") or {}).get("stamps")
        self.assertIsNotNone(stamps1, "premise: cycle one's job recorded its scope")
        self.assertIn(proj, stamps1, "premise: cycle one's walk held the project directory's own stat (the entry a carried map would serve on): %r"
                      % (sorted(str(k) for k in stamps1),))
        rec = {}
        km._turn_notify_tick = self._awaiting_job(rec)
        b = self._stats()
        with self._spy() as sp:
            km._pusher_cycle()
        d = self._delta(b)
        self.assertEqual(rec.get("counts"), [A + 1] * CALLS, "cycle two's %d reads each saw the A agents and the one row nobody owns: %r" % (CALLS, rec))
        stamps2 = (rec.get("scope") or {}).get("stamps")
        self.assertIsNotNone(stamps2, "cycle two's job recorded its scope")
        held = stamps2.get(proj)
        self.assertIsNotNone(held,
                             "cycle two's scope holds the project directory's stamp: the lookup was made in cycle two (the row's memoized miss "
                             "re-checked, _dir_stamp's own stat of the project directory taken and held); a launches map carried across cycles "
                             "serves the row's fold, makes no lookup and lands no entry here: %r" % (sorted(str(k) for k in stamps2),))
        self.assertIsNone(held[1], "the project directory's stamp is an own stat, vouched by no root (root None): %r" % (held,))
        self.assertIsNot(stamps2, stamps1,
                         "cycle two's stamps map is not cycle one's object: the map is released at the cycle's end (_subagent_scope_close) "
                         "and the next cycle's scope mints its own; a stamps map carried across cycles is the same object")
        self.assertIsNot(held, stamps1[proj],
                         "and the project directory's entry is cycle two's own, re-taken, not cycle one's held tuple served on")
        self.assertEqual(d["dirStats"], D,
                         "memos.subagentTree dirStats over cycle two, the world unchanged since cycle one: %d; keyed on (D - 1) + 1 = %d, the "
                         "count alone: the validation's lstats plus one stamp stat (that the lookup was made is the presence pin above, and "
                         "that the stat was re-taken rather than served from a carried map is the identity pin above)" % (d["dirStats"], D))
        self.assertEqual((d["hit"], d["miss"], d["evict"]), (1, 0, 0), "cycle two's one validated hit, no walk, nothing evicted: %r" % (d,))
        self.assertEqual(sp.total()["dir_stat"], 0, "no os.stat on the tree's directories in cycle two either: the tree is read before the re-checks")
        self.assertIsNone(getattr(km._live_scope, "subtrees", None), "cycle two's scope is closed too")

    def test_a_directory_created_after_a_cycles_validation_is_listed_by_the_next_cycle_not_this_one(self):
        """The contract the fix accepts, stated as a pin: within one cycle the first reader's validation stands, so a
        workflow directory created after it is not listed by a later read in the same cycle; the next cycle's first read
        lists it. One cycle of lag at most, where a cycle is the pusher's wake or its 0.5 s backstop."""
        late = self.wfroot / ("wf_%016x" % 0x7cfe)
        rec = {}

        def job(now, live_map, **kw):
            km._session_awaiting(SID, self.path, True)   # this cycle's validation of the tree
            late.mkdir()                                  # a workflow directory lands after it
            rec["same"] = str(late) in km._subagent_dirs(str(self.sub))
        km._turn_notify_tick = job
        km._pusher_cycle()
        self.dirs.append(str(late)); self.dirset.add(str(late))
        rec2 = {}
        km._turn_notify_tick = lambda now, live_map, **kw: rec2.setdefault("next", str(late) in km._subagent_dirs(str(self.sub)))
        km._pusher_cycle()
        self.assertIn("same", rec); self.assertIn("next", rec2)
        self.assertFalse(rec["same"], "a later read in the same cycle is served the cycle's validated listing (the lag the fix "
                                      "accepts: a change after the validation waits for the next cycle)")
        self.assertTrue(rec2["next"], "the next cycle's first read validates against the disk, walks and lists it: one cycle later at most")


class TwoThreadsEachValidateOnce(_World):
    """(3) The scope is thread-confined (_live_scope): a pusher cycle and a jobs pass at once each validate once and
    hold their own pair; neither is served the other's."""

    def test_a_pusher_cycle_and_a_jobs_pass_at_once_each_validate_once_with_their_own_scope(self):
        gate = threading.Barrier(2, timeout=30)           # both scopes open before either reads
        first = threading.Event()                         # the pusher reads first, so a memo shared across threads would serve the jobs thread
        rec = {"P": {}, "J": {}}

        def job_for(who, after_first):
            def job(now, live_map, **kw):
                r = rec[who]
                r["ident"], r["scope"] = threading.get_ident(), _scope()
                gate.wait()
                if after_first:
                    first.wait(30)
                r["counts"] = [(km._session_awaiting(SID, self.path, True) or {}).get("count") for _ in range(CALLS)]
                if not after_first:
                    first.set()
            return job
        km._turn_notify_tick = job_for("P", False)
        km._auto_nudge_tick = job_for("J", True)
        errs = []

        def run(fn):
            try:
                fn()
            except Exception:
                errs.append(traceback.format_exc())
        b = self._stats()
        with self._spy() as sp:
            tp = threading.Thread(target=run, args=(km._pusher_cycle,), name="stamps-pusher")
            tj = threading.Thread(target=run, args=(km._jobs_cycle,), name="stamps-jobs")
            tp.start(); tj.start()
            tp.join(90); tj.join(90)
        self.assertEqual(errs, [])
        self.assertFalse(tp.is_alive() or tj.is_alive(), "both loops' bodies returned")
        for who, what in (("P", "pusher cycle"), ("J", "jobs pass")):
            r = rec[who]
            self.assertEqual(r.get("counts"), [A] * CALLS, "the %s's stubbed job made its reads: %r" % (what, r))
            c = sp.thread(r["ident"])
            self.assertEqual(c["dir_lstat"], D, "the %s's thread validated the tree once itself: %d lstats, expected D = %d (a memo "
                                                "shared across threads would have served the second thread for 0; before the scope "
                                                "each thread paid CALLS x D = %d)" % (what, c["dir_lstat"], D, CALLS * D))
            self.assertEqual(c["dir_stat"], 0, "the %s's thread paid no stamp re-check stat: %d (before the scope CALLS x A x D = %d)"
                             % (what, c["dir_stat"], CALLS * A * D))
        self.assertIsNotNone(rec["P"]["scope"]); self.assertIsNotNone(rec["J"]["scope"])
        self.assertIsNot(rec["P"]["scope"], rec["J"]["scope"],
                         "each thread's scope is its own (_live_scope.subtrees is thread-local): a module-level memo would be one object")
        d = self._delta(b)
        self.assertEqual((d["hit"], d["miss"]), (2, 0), "one validated hit per thread (was CALLS per thread = %d)" % (2 * CALLS))


class Guards(_World):
    """(4) What the scope refuses to hold, each beside what it accepts. These open the scope directly (the clearing
    point is pinned through the real cycles above)."""

    def test_a_forget_that_evicts_the_root_makes_the_next_read_walk_again_while_one_that_evicts_nothing_leaves_it_served(self):
        sc = self._open()
        b = self._stats()
        with self._spy() as sp:
            km._subagent_tree(str(self.sub)); km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], D, "two reads in one scope cost one validation")
        self.assertEqual((self._delta(b)["hit"], self._delta(b)["served"]), (1, 1),
                         "the first read validated and the second was served the held pair: %r" % (self._delta(b),))
        # accept: a forget over a live set that owns the root evicts nothing, moves no gen, and the scope keeps serving
        km._subagent_trees_forget([{"path": self.path}])
        self.assertEqual(self._delta(b)["evict"], 0)
        held = sc["trees"][str(self.sub)]                 # the pair the scope holds, read before the call it should answer
        with self._spy() as sp:
            out = km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], 0, "os.lstat on the tree's directories on the read after the forget that evicted nothing: "
                                                     "%d; keyed on 0 (the read reached no disk)" % sp.total()["dir_lstat"])
        self.assertIs(out, held[0], "that read was answered the pair the scope held before it (served), keyed on identity")
        served_before_eviction = self._delta(b)["served"]
        self.assertEqual(served_before_eviction, 2, "memos.subagentTree served so far: %d; keyed on 2, the first pair's second read and "
                                                    "the read after the forget that evicted nothing, both answered the held pair" % served_before_eviction)
        # refuse: nobody alive evicts the root; the next read in the SAME scope walks again instead of being served the evicted pair
        km._subagent_trees_forget([])
        self.assertEqual(self._delta(b)["evict"], 1)
        self.assertNotIn(str(self.sub), km._SUBAGENT_TREES)
        with self._spy() as sp:
            dirs, _stats = km._subagent_tree(str(self.sub))
        d = self._delta(b)
        self.assertEqual(d["miss"], 1, "the read after the forget walked (a miss), not the held pair: _subagent_trees_forget moved "
                                       "_SUBAGENT_TREES_GEN and recorded the root's eviction, so the hold was dropped at this lookup "
                                       "(_subagent_vouched against the root's record) and the disk read")
        self.assertEqual(d["served"], served_before_eviction,
                         "memos.subagentTree served after the read that dropped the stale hold and walked: %d; keyed on the %d served reads "
                         "before the eviction alone (the early return is the one site that moves served; a hold dropped at the lookup lands "
                         "in miss, or in hit when the entry still stands, never in served)" % (d["served"], served_before_eviction))
        self.assertEqual(sp.total()["dir_lstat"], D, "a walk: the root and each child by lstat, D = %d" % D)
        self.assertEqual(len(dirs), D)

    def test_a_stale_hold_dropped_at_the_lookup_lands_in_miss_and_moves_served_by_nothing(self):
        """The rule that a read answered a tree lands in exactly one of hit, miss and served, at the stale-hold edge (the
        owner's pass before round 2 of #882: a kernel counting served on the dropped hold left the module green, the counter
        being pinned only where reads are served). The scope holds the root; the forget evicts it (nobody alive); the next
        read finds its hold stale at the lookup, drops it and reads the disk (the forget popped the entry, so a walk). Keys
        on the (hit, miss, served, evict) delta over the forget and that read == (0, 1, 0, 1): the early return alone moves
        served, so a hold dropped at the lookup is a validation or a walk and lands in hit or miss, here miss."""
        root = str(self.sub)
        sc = self._open()
        km._subagent_tree(root)
        self.assertIn(root, sc["trees"], "premise: the root is held")
        b = self._stats()
        km._subagent_trees_forget(set())
        with self._spy() as sp:
            out = km._subagent_tree(root)
        d = self._delta(b)
        got = (d["hit"], d["miss"], d["served"], d["evict"])
        self.assertEqual(got, (0, 1, 0, 1),
                         "(hit, miss, served, evict) over the forget and the read that dropped the stale hold: %r; keyed on (0, 1, 0, 1): one "
                         "eviction, the read landing in miss alone (the entry left with the eviction, so it walked) and served moved by "
                         "nothing (the early return alone moves it; a kernel that counts the dropped hold reads (0, 1, 1, 1))" % (got,))
        self.assertEqual((len(out[0]), sp.total()["dir_lstat"]), (D, D), "the walk: D directories at D lstats")
        self.assertEqual(sp.tree_calls(), {"lstat": D, "scandir": D},
                         "filesystem calls under the tree on the walk, by class: %r; keyed on {lstat: D, scandir: D} = D = %d each, the "
                         "root's lstat and one per child directory, and one listing per directory (an entry's type comes from the "
                         "listing): the cost home's walk term (_subagent_tree_memo_report's docstring)" % (sp.tree_calls(), D))
        self.assertIn(root, sc["trees"], "the walk re-holds the root")

    def test_a_stamp_stat_that_raises_is_answered_and_not_held_while_one_that_succeeds_is_held(self):
        sc = self._open()
        target = self.dirs[3]
        real_stat = os.stat
        calls = [0]

        def failing(p, *a, **k):
            if str(p) == target:
                calls[0] += 1
                raise OSError(errno.EIO, "synthetic EIO")
            return real_stat(p, *a, **k)
        with mock.patch.object(os, "stat", failing):
            r1 = km._dir_stamp(target); r2 = km._dir_stamp(target)
        self.assertEqual((r1, r2), ((target, None), (target, None)), "a faulted stat is answered (dir, None), as before the scope")
        self.assertEqual(calls[0], 2, "refused: the fault is not held, so the second call stats again (a held (dir, None) would be served)")
        self.assertNotIn(target, sc["stamps"])
        # accept: once it stats, the stamp is held and the second call is served
        n = [0]

        def counting(p, *a, **k):
            if str(p) == target:
                n[0] += 1
            return real_stat(p, *a, **k)
        with mock.patch.object(os, "stat", counting):
            r3 = km._dir_stamp(target); r4 = km._dir_stamp(target)
        self.assertEqual(n[0], 1, "accepted: one stat, the second call served from the scope's stamps")
        self.assertEqual(r3, r4)
        self.assertIsNotNone(r3[1])
        held = sc["stamps"].get(target)
        self.assertIsNotNone(held, "the stamp that stat'd is held")
        self.assertEqual(held[0], r3, "held as the stamp _dir_stamp answers (the entry is (stamp, the root it depends on, the generation held under))")
        self.assertIsNone(held[1], "an own stat: no root the scope can name, so vouched by no root")

    def test_a_walk_with_a_failed_listing_is_not_held_while_a_clean_walk_is(self):
        km._SUBAGENT_TREES.pop(str(self.sub), None)     # the next read walks
        sc = self._open()
        real_scandir = os.scandir
        fails = [1]

        def failing(p, *a, **k):
            if fails[0] and str(p) == self.dirs[1]:      # workflows/: its listing fails once
                fails[0] -= 1
                raise OSError(errno.EMFILE, "synthetic EMFILE")
            return real_scandir(p, *a, **k)
        b = self._stats()
        with mock.patch.object(os, "scandir", failing):
            dirs1, _s1 = km._subagent_tree(str(self.sub))
        self.assertEqual(self._delta(b)["miss"], 1)
        self.assertLess(len(dirs1), D, "the failed listing lost the directories under workflows/")
        self.assertNotIn(str(self.sub), sc["trees"], "refused: a walk whose listing failed is not held for the cycle")
        dirs2, _s2 = km._subagent_tree(str(self.sub))     # the next call this cycle walks again (an unvouched entry never hits)
        self.assertEqual(self._delta(b)["miss"], 2, "the next call re-walked instead of being served the unclean pair")
        self.assertEqual(len(dirs2), D)
        self.assertIn(str(self.sub), sc["trees"], "accepted: the clean walk is held")
        held = sc["trees"][str(self.sub)]
        with self._spy() as sp:
            out3 = km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], 0, "os.lstat on the tree's directories on the read after the held clean walk: %d; keyed on 0"
                         % sp.total()["dir_lstat"])
        self.assertIs(out3, held[0], "that read was answered the pair the clean walk left in the scope (served), keyed on identity")
        self.assertEqual(self._delta(b)["miss"], 2)
        self.assertEqual(out3[0], dirs2)

    def test_a_racy_tree_is_held_for_the_cycle_it_was_walked_in_and_walked_again_next_cycle(self):
        """The racy hold with the REAL window (regression-1 and tests-3 of the round-1 review: setUp closes the window for
        every case, so no walk in the module stored a racy stamp and the opposite policy, a scope holding vouched walks
        alone, stayed green through it). A directory whose mtime or ctime is within _SUBAGENT_DIR_RACY_NS of the walk is
        stored in the cross-cycle memo with identity None (git's racy-stamp rule), so that memo never vouches for the tree
        and the next cycle's first read walks it again; the cycle scope holds the walk like any clean one, its pair and its
        stamps, since a racy stamp is the clock's coarseness and no failure, and a tree under active write is the one the
        pusher reads most. Keys, in order: the premise (the walk stored None for the directory written at the walk; a walk
        that ran late, past the window, is a visible red here, never a pass for the wrong reason), the hold (the second read
        in the scope and the written directory's _dir_stamp cost 0 lstats and 0 stats and neither validate nor walk) and the
        release (a new scope's first read walks: one miss, D lstats). The opposite policy leaves the second read walking: D
        lstats and a miss where 0 are owed, once per read for every tree under active write."""
        root, touched = str(self.sub), self.dirs[3]       # one workflow directory, written at the walk: within the real window
        with mock.patch.object(km, "_SUBAGENT_DIR_RACY_NS", RACY_NS_REAL):
            self.assertGreater(km._SUBAGENT_DIR_RACY_NS, 0, "the window is the kernel's own, read at import before setUp closed it")
            km._SUBAGENT_TREES.pop(root, None)             # no entry stands: the first read walks
            sc = self._open()
            b = self._stats()
            now = time.time_ns()
            os.utime(touched, ns=(now, now))              # mtime now; the utime itself moves ctime to now as well
            with self._spy() as sp:
                dirs1, stats1 = km._subagent_tree(root)
            t1, d1 = sp.total(), self._delta(b)
            self.assertEqual((len(dirs1), d1["miss"], t1["dir_lstat"]), (D, 1, D), "read 1 walked the tree: D directories, one miss, D lstats")
            at = dirs1.index(touched)
            self.assertIsNone(km._SUBAGENT_TREES[root][1][at],
                              "premise: the walk stored identity None for the directory written at the walk, its stamp within "
                              "_SUBAGENT_DIR_RACY_NS = %d ns of the clock; a stored identity means the walk saw no racy stamp (it ran past "
                              "the window on a slow box) and this case cannot pin the hold" % RACY_NS_REAL)
            with self._spy() as sp:
                dirs2, _stats2 = km._subagent_tree(root)
                stamp2 = km._dir_stamp(touched)
            t2, d2 = sp.total(), self._delta(b)
            cost2 = (t2["dir_lstat"], t2["dir_stat"], d2["hit"] - d1["hit"], d2["miss"] - d1["miss"])
            self.assertEqual(cost2, (0, 0, 0, 0),
                             "(os.lstat on the tree's directories, os.stat on them, validated hits, walks) on the second read in the scope "
                             "and the written directory's stamp: %r; keyed on the racy walk being held for the cycle like a clean one, the "
                             "pair and the stamps served (0, 0, 0, 0); a scope holding vouched walks alone walks again, D = %d lstats, a "
                             "stat for the stamp and a miss, on every read of a tree under active write" % (cost2, D))
            self.assertIs(dirs2, dirs1, "the second read is answered the first read's listing")
            self.assertEqual(stamp2, (touched, stats1[at].st_mtime_ns), "the stamp served is the one the walk took")
            self.assertIn(root, sc["trees"], "held: the racy walk's pair stands in the scope")
            km._subagent_scope_close()                     # the cycle ends
            self._open()                                   # the next cycle
            with self._spy() as sp:
                dirs3, _stats3 = km._subagent_tree(root)
            t3, d3 = sp.total(), self._delta(b)
            cost3 = (d3["miss"] - d2["miss"], d3["hit"] - d2["hit"], t3["dir_lstat"], len(dirs3))
            self.assertEqual(cost3, (1, 0, D, D),
                             "the next scope's first read: (walks, validated hits, lstats, directories) %r; keyed on a walk (1, 0, D, D): "
                             "the racy entry is unvouched across cycles, so the cross-cycle memo never hits on it, and the hold ended with "
                             "the scope, so the new cycle reads the disk (a hold that outlived the scope would serve the pair for 0)"
                             % (cost3,))

    def test_an_eviction_landing_inside_the_roots_read_outdates_the_pair_so_the_next_read_validates_again(self):
        """The generation is read BEFORE the disk read at every hold site: the pair's two, both in _subagent_tree under the one
        read before the root's lstat (_subagent_scope_hold after a clean walk, the site this case drives, since the forget
        inside the root's lstat pops the entry and the read walks; and after a validated hit, the twin case below, which the
        owner's pass before round 2 of #882 found unpinned), the own stat's before its stat and the launch fold's before its
        file's resolution (the two cases after the twin), so an eviction that lands inside the read leaves the hold outdated
        and the next lookup validates, walks, stats or folds once more instead of serving an entry under a value that already
        counts the eviction: the safe side, one re-validation, as the ledger and the docstrings state. Fires the own root's
        eviction (nobody alive owns it: _subagent_trees_forget) from inside os.lstat of the root, the read's first call, so the
        read's walk re-inserts the root and the hold is under the generation from before the eviction. Keys on the second
        read costing D lstats (a validation): a generation read after the root's lstat counts the eviction and serves the
        pair (0)."""
        root = str(self.sub)
        sc = self._open()
        real_lstat, fired = os.lstat, [0]

        def racing(p, *a, **k):
            st = real_lstat(p, *a, **k)
            if str(p) == root and not fired[0]:
                fired[0] = 1
                km._subagent_trees_forget([])              # the eviction, inside the read
            return st
        with mock.patch.object(os, "lstat", racing):
            dirs1, _s1 = km._subagent_tree(root)
        self.assertEqual((fired[0], len(dirs1)), (1, D), "premise: the eviction ran inside the read and the read answered the tree")
        self.assertIn(root, km._SUBAGENT_TREES, "the read re-inserted the root (its walk, after the forget popped the entry)")
        with self._spy() as sp:
            dirs2, _s2 = km._subagent_tree(root)
        self.assertEqual((sp.total()["dir_lstat"], len(dirs2)), (D, D),
                         "(os.lstat on the tree's directories, directories) on the read after one whose generation was read before an "
                         "eviction inside it: %r; keyed on (D = %d, D): the hold is outdated by that eviction, so this read validates again; "
                         "a generation read after the root's lstat counts the eviction and serves the pair (0, D)"
                         % ((sp.total()["dir_lstat"], len(dirs2)), D))
        held = sc["trees"][root]                          # the pair the second read's validation held, under the generation after the eviction
        with self._spy() as sp:
            out = km._subagent_tree(root)
        self.assertEqual(sp.total()["dir_lstat"], 0, "os.lstat on the tree's directories on the third read: %d; keyed on 0 (held again, under a "
                                                     "generation that counts the eviction)" % sp.total()["dir_lstat"])
        self.assertIs(out, held[0], "the third read was answered the pair the scope held before it (served), keyed on identity")

    def test_an_eviction_landing_inside_a_validation_lstat_after_the_hit_was_read_outdates_the_hit_paths_hold_too(self):
        """The pair's other hold site, the validated hit's (the case above drives the clean walk's). _subagent_tree holds the
        pair from two sites under the one generation read before the root's lstat, _subagent_scope_hold after a validated hit
        and after a clean walk; a hit's hold under a generation read after the validation would count an eviction that landed
        inside the validation and serve the pair past it (the owner's pass before round 2 of #882: that variant left the module
        green, every ordering case popping the entry inside the root's lstat and so driving the walk). Fires the forget inside
        os.lstat of the SECOND directory, a validation lstat after `hit` was read at the memo: the forget pops the entry, the
        validation goes on and the pair is held through the hit path, under the older generation. Premise: the read took the
        hit path (hit +1, miss 0) with the one eviction inside it, and the entry the forget popped was not re-inserted (a hit
        stores nothing). Keys on the next read costing D lstats with miss +1, a walk: the hold is outdated by the eviction
        inside its validation and the entry is gone; a hit-path hold under a generation read after the validation serves the
        pair (0 lstats, served +1)."""
        root, second = str(self.sub), self.dirs[1]
        sc = self._open()
        real_lstat, fired = os.lstat, [0]

        def racing(p, *a, **k):
            st = real_lstat(p, *a, **k)
            if str(p) == second and not fired[0]:
                fired[0] = 1
                km._subagent_trees_forget([])              # the eviction, inside a validation lstat (hit already read at the memo)
            return st
        b = self._stats()
        with mock.patch.object(os, "lstat", racing):
            dirs1, _s1 = km._subagent_tree(root)
        d1 = self._delta(b)
        self.assertEqual((fired[0], len(dirs1)), (1, D), "premise: the eviction ran inside the read and the read answered the tree")
        self.assertEqual((d1["hit"], d1["miss"], d1["evict"]), (1, 0, 1),
                         "premise: the read took the HIT path (validated, no walk) with the one eviction inside its validation: %r" % (d1,))
        self.assertNotIn(root, km._SUBAGENT_TREES, "premise: the entry the forget popped was not re-inserted (the hit path stores nothing)")
        self.assertIn(root, sc["trees"], "premise: the hit path held the pair")
        with self._spy() as sp:
            dirs2, _s2 = km._subagent_tree(root)
        d2 = self._delta(b)
        self.assertEqual((sp.total()["dir_lstat"], len(dirs2)), (D, D),
                         "(os.lstat on the tree's directories, directories) on the read after a HIT-path hold whose generation was read "
                         "before an eviction inside its validation: %r; keyed on (D = %d, D): the hold is outdated, so this read reads the "
                         "disk again (a walk, the entry being gone); a hit-path hold under a generation read after the validation counts "
                         "the eviction and serves the pair (0, D)" % ((sp.total()["dir_lstat"], len(dirs2)), D))
        self.assertEqual((d2["miss"] - d1["miss"], d2["served"] - d1["served"]), (1, 0),
                         "that read is a walk and not a served read: (miss, served) moved %r; keyed on (1, 0)" % ((d2["miss"] - d1["miss"], d2["served"] - d1["served"]),))
        self.assertIn(root, km._SUBAGENT_TREES, "the walk re-inserted the root")
        held = sc["trees"][root]                          # the pair the second read's walk held, under the generation after the eviction
        with self._spy() as sp:
            out = km._subagent_tree(root)
        self.assertEqual(sp.total()["dir_lstat"], 0, "os.lstat on the tree's directories on the third read: %d; keyed on 0 (held again, under a "
                                                     "generation that counts the eviction)" % sp.total()["dir_lstat"])
        self.assertIs(out, held[0], "the third read was answered the pair the scope held before it (served), keyed on identity")

    def test_an_eviction_landing_inside_an_own_stat_outdates_the_stamp_so_it_is_re_taken(self):
        """The own stat's site of the rule above: the eviction fires inside os.stat of the directory (no tree read this cycle,
        so the stamp is an own stat, root None), and the next _dir_stamp re-takes it. Keys on 1 stat: a generation read after
        the stat serves it (0)."""
        sc = self._open()
        target = self.dirs[3]
        real_stat, fired = os.stat, [0]

        def racing(p, *a, **k):
            st = real_stat(p, *a, **k)
            if str(p) == target and not fired[0]:
                fired[0] = 1
                km._subagent_trees_forget([])
            return st
        with mock.patch.object(os, "stat", racing):
            r1 = km._dir_stamp(target)
        self.assertEqual(fired[0], 1, "premise: the eviction ran inside the stat")
        self.assertIsNotNone(r1[1])
        self.assertIsNone(sc["stamps"][target][1], "premise: an own stat, root None")
        with self._spy() as sp:
            r2 = km._dir_stamp(target)
        self.assertEqual(sp.total()["dir_stat"], 1,
                         "os.stat for an own stamp on the read after one whose generation was read before an eviction inside the stat: %d; "
                         "keyed on 1 (the hold is outdated, the stamp re-taken); a generation read after the stat serves it (0)"
                         % sp.total()["dir_stat"])
        self.assertEqual(r1, r2)
        held = sc["stamps"][target]                       # the stamp the re-take held, read before the call it should answer
        with self._spy() as sp:
            r3 = km._dir_stamp(target)
        self.assertEqual(sp.total()["dir_stat"], 0, "os.stat for the directory's stamp on the third call: %d; keyed on 0 (held again)"
                         % sp.total()["dir_stat"])
        self.assertIs(r3, held[0], "the third call was answered the stamp the scope held before it (served), keyed on identity")

    def test_an_eviction_landing_inside_a_launch_folds_resolution_outdates_the_fold_so_it_is_redone(self):
        """The launch fold's site of the rule above: the own root leaves the memo inside the FIRST fold's resolution of its
        file (_subagent_file called from _awaiting_nest's launches(); the sidecar reader's earlier call for the same agent is
        not the one), so that fold is held under the generation from before the eviction and the other A - 1 under the one
        after. Keys on the read's folds: one per agent plus that one fold redone at its next lookup in the same read (a later
        agent's owner lookup consults it again and finds its hold outdated), A + 1; and on the next read folding nothing,
        every hold now under a generation that counts the eviction. A generation read after the resolution counts the
        eviction at once and never redoes the fold (A folds in the read)."""
        self._open()
        real_file, real_fold, fired, folded = km._subagent_file, km._agent_launch_ids, [], []
        names = sorted("agent-%s.jsonl" % a for a in self.aids)

        def racing(path, aid, *a, **k):                      # `faults` passes through: the fold's fault plumbing under the stub
            ap = real_file(path, aid, *a, **k)
            if not fired and sys._getframe(1).f_code.co_name == "launches":
                fired.append("agent-%s.jsonl" % aid)
                km._subagent_trees_forget([])              # the own root leaves the memo inside the resolution
            return ap

        def counting(agent_path, *a, **k):
            folded.append(os.path.basename(str(agent_path)))
            return real_fold(agent_path, *a, **k)
        with mock.patch.object(km, "_subagent_file", racing), mock.patch.object(km, "_agent_launch_ids", counting):
            aw1 = km._session_awaiting(SID, self.path, True)
        self.assertEqual(((aw1 or {}).get("count"), len(fired)), (A, 1),
                         "premise: the read saw the A agents and the eviction fired inside one launches() resolution: %r" % (((aw1 or {}).get("count"), fired),))
        self.assertEqual(sorted(folded), sorted(names + fired),
                         "folds in the read whose first fold's resolution had the own root's eviction land inside it: %r; keyed on one fold "
                         "per agent plus that fold, %r, redone at its next lookup in the same read (its generation was read before the "
                         "eviction, so its hold is outdated once the eviction lands; the other A - 1 = %d were read after it and are held), "
                         "A + 1 = %d folds; a generation read after the resolution counts the eviction at once and never redoes it (A = %d)"
                         % (sorted(folded), fired, A - 1, A + 1, A))
        del folded[:]
        with mock.patch.object(km, "_agent_launch_ids", counting):
            aw2 = km._session_awaiting(SID, self.path, True)
        self.assertEqual(((aw2 or {}).get("count"), folded), (A, []),
                         "the next read: every fold held under a generation that counts the eviction, served (0 folds): %r" % (folded,))

    def test_a_faulted_launch_fold_is_folded_once_per_call_and_not_held_across_calls(self):
        """Two lifetimes for a launch fold whose reader took its fail path (_awaiting_nest's `faulted`; round 1 of #882's extra9-2): the
        fault is held for the CALL that observed it, so the owner lookups of one _session_awaiting read fold each agent's file
        once (each of the A lookups consults every other agent's launches, A x (A - 1) lookups per read), and not beyond that
        call, so the next read in the same cycle folds again and a file that became readable is seen at that read; a fold that
        read the file is held for the cycle. Drives the REAL _agent_launch_ids through a counting wrapper, with the fault
        produced where the reader produces it: os.stat raising EIO on every agent transcript (event_model's reader reports a
        non-ENOENT stat through on_fail, fold_records' "fail" road). Keys on the folds per read, one per agent, at A = 3
        (setUp's world) and A = 6 (the world grown): a fault returned without a call-local hold folded A x (A - 1) per read
        (6 and 30); a fault held for the cycle would fold 0 on the second read and attribute nothing to those agents all cycle."""
        real_fold, real_stat = km._agent_launch_ids, os.stat
        folded, fault, under = [], [True], str(self.sub) + os.sep

        def counting(agent_path, *a, **k):
            folded.append(os.path.basename(str(agent_path)))
            return real_fold(agent_path, *a, **k)

        def failing(p, *a, **k):
            s = str(p)
            if fault[0] and s.startswith(under) and os.path.basename(s).startswith("agent-") and s.endswith(".jsonl"):
                raise OSError(errno.EIO, "synthetic EIO")
            return real_stat(p, *a, **k)

        def read():
            del folded[:]
            aw = km._session_awaiting(SID, self.path, True)
            return (aw or {}).get("count"), sorted(folded)

        for n in (A, D - 2):
            with self.subTest(A=n):
                if n != len(self.aids):
                    self._grow_to(n)
                names = sorted("agent-%s.jsonl" % a for a in self.aids)
                sc = self._open()
                try:
                    fault[0] = True
                    with mock.patch.object(km, "_agent_launch_ids", counting), mock.patch.object(os, "stat", failing):
                        c1, f1 = read()
                        self.assertEqual(c1, n, "the read saw the %d agents" % n)
                        self.assertEqual(f1, names, "read 1 under the fault: %d folds; each of the A = %d agents' files is folded ONCE per "
                                                    "read (the call-local hold of the fault), not once per owner lookup that consulted it, "
                                                    "A x (A - 1) = %d (a fault returned without a hold)" % (len(f1), n, n * (n - 1)))
                        self.assertEqual([k for k in sc["launches"] if k[0] == self.path], [],
                                         "refused: a fold that did not read the file is held in no cycle scope")
                        c2, f2 = read()
                        self.assertEqual(c2, n)
                        self.assertEqual(f2, names, "read 2, the fault persisting: %d folds; folded again, A = %d, since the fault is not "
                                                    "held across calls (a fault held for the cycle would fold 0 here)" % (len(f2), n))
                        self.assertEqual([k for k in sc["launches"] if k[0] == self.path], [], "still nothing held")
                        fault[0] = False
                        c3, f3 = read()
                        self.assertEqual(c3, n)
                        self.assertEqual(f3, names, "read 3, the fault lifted: %d folds; the files that became readable are folded at this "
                                                    "read, A = %d, one each" % (len(f3), n))
                        self.assertEqual({k[1] for k in sc["launches"] if k[0] == self.path}, set(self.aids),
                                         "accepted: every fold that read its file is held for the cycle")
                        c4, f4 = read()
                        self.assertEqual(c4, n)
                        self.assertEqual(f4, [], "read 4: every agent's launches served from the scope, 0 folds: %r" % (f4,))
                finally:
                    km._subagent_scope_close()

    def test_the_fault_producer_names_the_readers_fail_path_and_a_raising_fold_and_stays_empty_on_a_read(self):
        """_agent_launch_ids's `faults` producer, driven directly (the case above sees only its effect through the memo): a
        readable file folds with faults == []; the reader's fail path (os.stat raising EIO on a file that exists, which
        event_model reports through on_fail) answers (set(), ["fail"]); a fold_records that raises answers (set(), [the
        exception's type name]), so a wrong stub shape (a TypeError) cannot pass for the reader's fault. Keys on the exact
        list: a producer with the `on` callback's append deleted answers [] for the fail path, one with the except branch's
        append deleted answers [] for the raise."""
        ap = self.wfroot / ("wf_%016x" % 0) / ("agent-%s.jsonl" % self.aids[0])
        self.assertTrue(ap.is_file())
        faults = []
        self.assertEqual(km._agent_launch_ids(ap, faults), set())
        self.assertEqual(faults, [], "a readable file: the fold read it and recorded no fault")
        real_stat = os.stat

        def failing(p, *a, **k):
            if str(p) == str(ap):
                raise OSError(errno.EIO, "synthetic EIO")
            return real_stat(p, *a, **k)
        faults = []
        with mock.patch.object(os, "stat", failing):
            ids = km._agent_launch_ids(ap, faults)
        self.assertEqual((ids, faults), (set(), ["fail"]),
                         "the reader's fail path (its stat raised on a file that exists): set() and the `on` callback's 'fail', once")
        faults = []
        with mock.patch.object(km.em, "fold_records", side_effect=OSError(errno.EIO, "synthetic EIO")):
            ids = km._agent_launch_ids(ap, faults)
        self.assertEqual((ids, faults), (set(), ["OSError"]), "a fold that raised: set() and the exception's type name from the except branch")
        self.assertEqual(km._agent_launch_ids(ap), set(), "no list handed: the producer is optional and the answer stands")

    def test_an_unreadable_session_directory_resolves_every_agent_again_on_every_read_and_its_failed_calls_move_no_counter(self):
        """The unreadable-tree term of the cost home (_subagent_tree_memo_report's docstring; round 2 of #882, extra5-4),
        as group A leaves the walk: the session directory at mode 000, a real EACCES on every path under it (skipped as
        root, whom permission bits do not bind), the A agents' resolutions standing from setUp's warm read. Nothing under
        the tree is held (a read that did not happen is never held), so every read pays again, derived from the code per
        read: _subagent_meta_map's root lstat (1 lstat), and per agent, whose launches the call consults once (the fault
        holds its fold for the call alone): the memo hit's re-check of its D stamps (D stats), the walk's own-root stamp
        (1 stat), the flat place's lstat and islink's (2 lstats; the flat place was an os.stat, by os.path.isfile, until
        round 3 of #882, group A), _subagent_tree's root lstat (1 lstat, the raise), and the fold of the standing
        resolution's file (1 stat). So the census under the tree over one pusher cycle of CALLS reads is
        {lstat: CALLS x (3A + 1), stat: CALLS x A x (D + 2)}, every call failing. None of them moves a counter: hit, miss,
        served and evict stay at 0. dirStats moves by 1, and that 1 is one os.stat: _dir_stamp's stat of the project
        directory (the transcript's parent) in _subagent_file_walk, which the walk now reaches since a fault excludes its own
        tree and nothing else. The project directory lies outside the mode-000 tree, so that stat succeeds where every stamp
        stat under the tree fails, and _dir_stamp counts only a stat that succeeds; the tree validation's lstats, dirStats's
        other half, never run, the root's lstat raising first. The cycle's first walk takes the stat and the scope holds it
        as an own stat, which the later walks are served. The cost home derives this 1 in its unreadable-tree
        entry, as each walk's project-directory part, a pointer to the project-directory stamp of its entry for the miss
        walk over the own tree (an own stat, once per cycle, shared). The walk's listing and per-entry stats of the project
        directory are outside the tree too, that same entry's, and move no counter."""
        if os.geteuid() == 0:
            self.skipTest("permission bits do not bind root: no EACCES to drive")
        sess = self.sub.parent
        rec = {}
        km._turn_notify_tick = self._awaiting_job(rec)
        b = self._stats()
        os.chmod(sess, 0o000)
        try:
            with self.assertRaises(PermissionError, msg="premise: the real fault this case drives"):
                os.lstat(str(self.sub))
            with self._spy() as sp:
                km._pusher_cycle()
        finally:
            os.chmod(sess, 0o755)
        c, d = sp.tree_calls(), self._delta(b)
        self.assertEqual(rec.get("counts"), [A] * CALLS, "each read still listed the A agents (the live row names them): %r" % (rec,))
        want = {"lstat": CALLS * (3 * A + 1), "stat": CALLS * A * (D + 2)}
        self.assertEqual(c, want,
                         "filesystem calls under the unreadable tree over one pusher cycle, by class: %r; keyed on {lstat: CALLS x (3A + "
                         "1), stat: CALLS x A x (D + 2)} = %r, every agent resolved again on every read and nothing held"
                         % (c, want))
        got = tuple(d[k] for k in STAT_KEYS)
        self.assertEqual(got, (0, 0, 0, 0, 1),
                         "(hit, miss, served, evict, dirStats) over the cycle: %r; keyed on (0, 0, 0, 0, 1): the failed calls under the "
                         "tree move no counter, and dirStats moves by _dir_stamp's one os.stat of the project directory alone (the "
                         "cost home's unreadable-tree entry, its project-directory part)" % (got,))

    def test_a_root_gone_mid_cycle_with_an_entry_moves_the_gen_and_records_its_eviction_while_a_held_sibling_stays_served(self):
        """_subagent_tree's missing-root pop path (a session's tree removed while the walk memo held it): a pop that removed
        an entry moves _SUBAGENT_TREES_GEN and records the root's eviction at the value it moved to, so what an open scope
        holds for THAT root is dropped at its next lookup; a sibling tree the scope holds is still served (before 2026-09-21
        one process-wide generation emptied every scope and the sibling paid its D lstats again); a missing root
        with no entry answers (), () and moves nothing."""
        other_t = Path(self.td.name) / "other" / (OTHER_SID + ".jsonl")   # a second session's transcript, its tree beside it
        other_t.parent.mkdir()
        other_t.write_text("")
        other = km._subagents_dir(other_t)
        (other / "workflows").mkdir(parents=True)
        _age(other)
        self.addCleanup(km._SUBAGENT_TREES.pop, str(other), None)
        km._subagent_tree(str(other))                     # walked into the cross-cycle memo: an entry stands
        self.assertIn(str(other), km._SUBAGENT_TREES)
        sc = self._open()
        b = self._stats()
        with self._spy() as sp:
            first = km._subagent_tree(str(self.sub))
            held = sc["trees"][str(self.sub)]
            second = km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], D, "os.lstat on the tree's directories over two reads in the scope: %d; keyed on D = %d, one "
                                                     "validation (the second read reached no disk)" % (sp.total()["dir_lstat"], D))
        self.assertIs(first, held[0], "the first read's validated pair is what the scope holds")
        self.assertIs(second, held[0], "and the second read was answered it (served), keyed on identity")
        self.assertIn(str(self.sub), sc["trees"])
        shutil.rmtree(other)
        g0 = km._SUBAGENT_TREES_GEN[0]
        # refuse: the entry stood, so the pop is an eviction: the gen moves, the root's eviction is recorded at the new value, and
        # the held sibling is still served (its root did not leave the memo)
        self.assertEqual(km._subagent_tree(str(other)), ((), ()), "nothing at the root: (), () as ever")
        self.assertNotIn(str(other), km._SUBAGENT_TREES)
        self.assertEqual(km._SUBAGENT_TREES_GEN[0] - g0, 1, "the missing-root pop that removed an entry moved _SUBAGENT_TREES_GEN")
        with self._spy() as sp:
            out = km._subagent_tree(str(self.sub))
        dirs = out[0]
        self.assertEqual(sp.total()["dir_lstat"], 0, "os.lstat on the held sibling's directories after the pop: %d; keyed on 0, since the "
                                                     "eviction was the other root's and its pair is as fresh as before; one process-wide "
                                                     "generation emptied the scope and cost D = %d lstats again"
                         % (sp.total()["dir_lstat"], D))
        self.assertIs(out, held[0], "and the read was answered the pair held before the pop (served), keyed on identity")
        self.assertEqual(len(dirs), D)
        self.assertEqual(km._SUBAGENT_ROOT_EVICTED.get(str(other)), km._SUBAGENT_TREES_GEN[0],
                         "the pop recorded the removed root's eviction at the value the gen moved to: what a scope holds for it is dropped")
        # accept: no entry stands now, so the same call moves nothing and the held tree stays served
        g1 = km._SUBAGENT_TREES_GEN[0]
        self.assertEqual(km._subagent_tree(str(other)), ((), ()))
        self.assertEqual(km._SUBAGENT_TREES_GEN[0], g1, "a missing root with no entry moves no gen")
        held = sc["trees"][str(self.sub)]
        with self._spy() as sp:
            out = km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], 0, "os.lstat on the held tree's directories after the second missing-root read: %d; keyed on 0 "
                                                     "(nothing was evicted this time)" % sp.total()["dir_lstat"])
        self.assertIs(out, held[0], "and the read was answered the held pair (served), keyed on identity")
        self.assertEqual((self._delta(b)["hit"], self._delta(b)["miss"]), (1, 0), "one validated hit in the scope, before the eviction; "
                                                                                   "none after (the sibling was served)")

    def _sibling_tree(self, tag="other"):
        """A second session's transcript under `tag` and beside it a subagents tree of D directories (the root, workflows/
        and D - 2 workflow directories, no agents), aged and walked into the cross-cycle memo outside any scope, owned by
        nobody alive: (the root, its directories in walk order)."""
        other_t = Path(self.td.name) / tag / (OTHER_SID + ".jsonl")
        other_t.parent.mkdir()
        other_t.write_text("")
        other = km._subagents_dir(other_t)
        wfroot = other / "workflows"
        wfroot.mkdir(parents=True)
        dirs = [str(other), str(wfroot)] + [str(wfroot / ("wf_%016x" % i)) for i in range(D - 2)]
        for p in dirs[2:]:
            os.mkdir(p)
        _age(other)
        self.addCleanup(km._SUBAGENT_TREES.pop, str(other), None)
        got, _stats = km._subagent_tree(str(other))
        self.assertEqual(list(got), dirs, "the sibling's tree walked into the cross-cycle memo: its D = %d directories in walk order" % D)
        return other, dirs

    def _assert_not_a_tree(self, answer, shape, what):
        """What _subagent_tree answers for a root that is not a tree: (), () when nothing is at the path ("missing"); (), (its
        lstat,) with a regular file's mode when a file stands in its place ("replaced"). Keys on dirs == () and the stat
        count and mode, not on tuple equality of stat results (two lstats of one file are two objects)."""
        self.assertIsNotNone(answer, "%s: no answer" % what)
        dirs, stats = answer
        self.assertEqual(dirs, (), "%s: directories %r; keyed on () (what is at the root is no tree)" % (what, dirs))
        if shape == "missing":
            self.assertEqual(stats, (), "%s: stats %r; keyed on () (nothing at the root)" % (what, stats))
        else:
            self.assertEqual(len(stats), 1, "%s: %d stats; keyed on one, the root's own lstat" % (what, len(stats)))
            self.assertTrue(stat.S_ISREG(stats[0].st_mode), "%s: the one stat is the regular file's standing in the tree's place" % what)

    def _holder_drops_its_pair_after_another_threads_pop(self, other, other_dirs, shape):
        """The body the two pop-path guards share. This thread's scope holds the sibling's tree (D directories) and this
        session's; the sibling is removed on disk ("missing") or removed and a regular file written in its place
        ("replaced"); a thread with no scope reads it, the pop. Keys, in order: the pop's answer; the eviction record (the
        gen moved by exactly one, the table naming the root at that value); the holder's next read of the sibling, which
        drops its pair at the lookup and answers the pop's shape at one lstat of the root (a pop that recorded no eviction
        leaves the D directories served at 0 lstats for the rest of the cycle); this session's tree still served, 0
        lstats, since the eviction is the sibling's; and the accept side, a second read of the same root with no entry
        standing, which moves no gen and records nothing new."""
        oset = set(other_dirs)
        sc = self._open()
        b = self._stats()
        with self._spy() as sp, _Spy(oset, other) as osp:
            km._subagent_tree(str(other)); km._subagent_tree(str(self.sub))
        self.assertEqual((osp.total()["dir_lstat"], sp.total()["dir_lstat"]), (D, D), "the holds: each tree validated once, D lstats each")
        self.assertEqual((self._delta(b)["hit"], self._delta(b)["served"]), (2, 0), "the two holds are validated hits, not served reads")
        self.assertIn(str(other), sc["trees"]); self.assertIn(str(self.sub), sc["trees"])
        shutil.rmtree(other)
        if shape == "replaced":
            Path(other).write_text("")                    # a regular file where the tree was
        g0 = km._SUBAGENT_TREES_GEN[0]
        s_pop = self._stats()
        seen = self._read_on_a_thread_with_no_scope(other)
        self._assert_not_a_tree(seen.get("answer"), shape, "the helper's read, the %s-root pop" % shape)
        self.assertNotIn(str(other), km._SUBAGENT_TREES, "the pop removed the cross-cycle entry")
        self.assertEqual(self._delta(s_pop)["served"], 0,
                         "memos.subagentTree served over the %s-root pop on the thread with no hold: %d; keyed on 0 (a pop answers no tree "
                         "and moves none of hit, miss and served; the early return alone moves served)" % (shape, self._delta(s_pop)["served"]))
        s_drop = self._stats()
        with _Spy(oset, other) as osp:
            got = km._subagent_tree(str(other))
        moved, answered, lstats = km._SUBAGENT_TREES_GEN[0] - g0, len(got[0]), osp.total()["dir_lstat"]
        self.assertEqual((moved, answered, lstats), (1, 0, 1),
                         "(_SUBAGENT_TREES_GEN's move on the %s-root pop, directories the holding thread is answered for that root on its "
                         "next read, its os.lstat of the root) %r; keyed on (1, 0, 1): one eviction event recorded (_subagent_root_evicted), "
                         "the holder's pair dropped at the lookup since the vouch fails on that record, and the root's own lstat paid; a "
                         "pop that recorded nothing is (0, D = %d, 0), the held pair served stale for the rest of the cycle"
                         % (shape, (moved, answered, lstats), D))
        # The served count over the same read, asserted after the key above and not before it (round 2 of #882, tests-2): a pop
        # that recorded no eviction leaves the pair held and served, which moves served too, and a red on this message, which
        # presents the read as one that dropped its pair, would name the opposite of that defect; the key above names it.
        self.assertEqual(self._delta(s_drop)["served"], 0,
                         "memos.subagentTree served over the holder's read that dropped its stale pair and lstat'd the %s root: %d; keyed on 0 "
                         "(a hold dropped at the lookup is not a served read, and what the lstat found is no tree)" % (shape, self._delta(s_drop)["served"]))
        self.assertEqual(km._SUBAGENT_ROOT_EVICTED.get(str(other)), seen.get("gen"),
                         "the table names the %s root at the value the gen moved to: %r against %r; keyed on equality (the record that "
                         "outdates every scope's hold on this root)" % (shape, km._SUBAGENT_ROOT_EVICTED.get(str(other)), seen.get("gen")))
        self._assert_not_a_tree(got, shape, "the holder's read after the pop")
        self.assertNotIn(str(other), sc["trees"], "the holder's scope no longer holds the popped root")
        served_reads = 0                                  # this session's held tree, read twice below and answered the held pair each time
        held = sc["trees"][str(self.sub)]
        with self._spy() as sp:
            out = km._subagent_tree(str(self.sub))
        dirs = out[0]
        served_reads += 1
        self.assertEqual((sp.total()["dir_lstat"], len(dirs)), (0, D),
                         "this session's held tree on the read after the sibling's pop: (lstats, directories) %r; keyed on (0, D = %d), "
                         "since the eviction recorded is the sibling's; one process-wide generation emptied this hold too"
                         % ((sp.total()["dir_lstat"], len(dirs)), D))
        self.assertIs(out, held[0], "and the read was answered the pair held before the pop (served), keyed on identity")
        # accept: no entry stands, so a second read of the same root pops nothing, moves no gen and records nothing new
        g1, rec1 = km._SUBAGENT_TREES_GEN[0], km._SUBAGENT_ROOT_EVICTED.get(str(other))
        with _Spy(oset, other) as osp:
            again = km._subagent_tree(str(other))
        self._assert_not_a_tree(again, shape, "a second read with no entry standing")
        self.assertEqual(osp.total()["dir_lstat"], 1, "the second read costs the root's lstat alone")
        self.assertEqual((km._SUBAGENT_TREES_GEN[0], km._SUBAGENT_ROOT_EVICTED.get(str(other))), (g1, rec1),
                         "a %s root with no entry standing moves no gen and records nothing new: (gen, record) %r against %r"
                         % (shape, (km._SUBAGENT_TREES_GEN[0], km._SUBAGENT_ROOT_EVICTED.get(str(other))), (g1, rec1)))
        held = sc["trees"][str(self.sub)]
        with self._spy() as sp:
            out = km._subagent_tree(str(self.sub))
        served_reads += 1
        self.assertEqual(sp.total()["dir_lstat"], 0, "os.lstat on this session's held tree after the second %s-root read: %d; keyed on 0"
                         % (shape, sp.total()["dir_lstat"]))
        self.assertIs(out, held[0], "this session's read was answered the pair the scope held before it (served), keyed on identity")
        d = self._delta(b)
        self.assertEqual((d["hit"], d["miss"], d["served"]), (2, 0, served_reads),
                         "memos.subagentTree over the case: (hit, miss, served) %r; keyed on the two holds' validated hits, no walk, and served "
                         "moved by the %d reads of this session's held tree the scope answered alone (the %s-root pop, the holder's drop and "
                         "the second read with no entry standing count as none of the three)" % ((d["hit"], d["miss"], d["served"]), served_reads, shape))

    def test_a_root_replaced_by_a_file_mid_cycle_is_popped_by_a_thread_with_no_hold_and_the_holder_drops_its_pair(self):
        """_subagent_tree's replaced-root pop path (correctness-2, tests-2, kernel-1, extra7-2, extra9-1 and extra10-1 of the
        round-1 review: the one eviction record in the change with no case arming it, so a kernel whose replaced-root pop
        recorded nothing left the module green and a held tree served for the rest of the cycle). A regular file where the
        sibling's subagents tree was, found by a thread with no scope while this thread's scope holds the tree (a
        same-thread read of a held root is served before the root's lstat and never pops: the lag case below). The pop
        answers (), (the file's lstat,), moves the gen by one and names the root in the table; the holder's next read drops
        its pair and answers the same at one lstat; the holder's other tree is still served; a second read moves nothing."""
        other, dirs = self._sibling_tree()
        self._holder_drops_its_pair_after_another_threads_pop(other, dirs, "replaced")

    def test_a_root_removed_mid_cycle_is_popped_by_a_thread_with_no_hold_and_the_holder_drops_its_pair(self):
        """The missing-root twin of the case above, the same shape through the other pop path, so the two records are told
        apart: a kernel whose missing-root pop records nothing reds this case and leaves the replaced one green, and a
        kernel whose replaced-root pop records nothing does the reverse. The pop answers (), ()."""
        other, dirs = self._sibling_tree()
        self._holder_drops_its_pair_after_another_threads_pop(other, dirs, "missing")

    def test_a_root_removed_while_this_thread_holds_it_is_served_until_its_scope_ends_and_found_gone_by_the_next(self):
        """The held-root lag, characterized (fresh-1 of the round-1 review, as its refuters narrowed it: the contract the
        change states, not a defect). The served call precedes the root's lstat, so a root this thread's scope holds is
        served after its removal on disk, its pair and its stamps, at no stat and with no pop (the cross-cycle entry stands,
        the gen does not move), until the scope ends; the next scope's first read lstats the root, pops the entry, records
        the eviction and answers (), (). Keys on (D directories, 0 lstats, 0 stats) served after the removal, and on the next
        scope's pop (one lstat, the gen moved by one, the table naming this root). A read that checked the root on disk
        before serving the hold, the option the review measured and declined for its per-read cost, answers () at one
        lstat per read there."""
        root = str(self.sub)
        sc = self._open()
        b = self._stats()
        with self._spy() as sp:
            km._subagent_tree(root)
        self.assertEqual(sp.total()["dir_lstat"], D, "the hold: the cycle's one validation")
        held_stamp = km._dir_stamp(self.dirs[3])
        self.assertIsNotNone(held_stamp[1])
        held_pair = sc["trees"][root]
        self.assertIs(held_stamp, sc["stamps"][self.dirs[3]][0], "premise: the stamp answered before the removal is the one the scope holds")
        shutil.rmtree(self.sub)
        g0 = km._SUBAGENT_TREES_GEN[0]
        with self._spy() as sp:
            out = km._subagent_tree(root)
            stamp = km._dir_stamp(self.dirs[3])
        dirs = out[0]
        t = sp.total()
        self.assertEqual((len(dirs), t["dir_lstat"], t["dir_stat"]), (D, 0, 0),
                         "(directories answered, os.lstat, os.stat) on this thread's read of a held root after its removal on disk: %r; "
                         "keyed on (D = %d, 0, 0): the reads reached no disk (the served call precedes the root's lstat: the lag the "
                         "design states, one cycle at most); a read that lstats the root before serving answers () at one lstat"
                         % ((len(dirs), t["dir_lstat"], t["dir_stat"]), D))
        self.assertIs(out, held_pair[0], "the read after the removal was answered the pair held before it (served), keyed on identity")
        self.assertIs(stamp, held_stamp, "and the removed directory's stamp call the stamp held before it (served), keyed on identity: %r"
                      % (stamp,))
        self.assertEqual(km._SUBAGENT_TREES_GEN[0], g0, "no pop ran on the served read: the gen stands")
        self.assertIn(root, km._SUBAGENT_TREES, "the cross-cycle entry stands: nothing has found the root gone")
        self.assertIn(root, sc["trees"], "the scope still holds the pair")
        d = self._delta(b)
        self.assertEqual((d["hit"], d["miss"], d["served"]), (1, 0, 1),
                         "memos.subagentTree over the hold and the read after the removal: (hit, miss, served) %r; keyed on (1, 0, 1), the hold's "
                         "validated hit and the one read the scope answered from the held pair (a served read of a removed held root lands in "
                         "served: the lag is visible there), the served stamp moving none of the three" % ((d["hit"], d["miss"], d["served"]),))
        km._subagent_scope_close()                        # the cycle ends
        self._open()                                      # the next cycle
        with self._spy() as sp:
            got = km._subagent_tree(root)
        self.assertEqual(got, ((), ()), "the next scope's first read finds nothing at the root: %r" % (got,))
        self.assertEqual(sp.total()["dir_lstat"], 1, "one lstat, the root's (which raised); no held pair in the new scope")
        self.assertEqual(km._SUBAGENT_TREES_GEN[0] - g0, 1,
                         "_SUBAGENT_TREES_GEN moved by %d on the next scope's read; keyed on exactly one, the missing-root pop of the standing "
                         "entry" % (km._SUBAGENT_TREES_GEN[0] - g0))
        self.assertEqual(km._SUBAGENT_ROOT_EVICTED.get(root), km._SUBAGENT_TREES_GEN[0], "the table names this root at that value")
        self.assertNotIn(root, km._SUBAGENT_TREES, "the entry left the cross-cycle memo")
        d2 = self._delta(b)
        self.assertEqual((d2["hit"], d2["miss"], d2["served"]), (d["hit"], d["miss"], d["served"]),
                         "(hit, miss, served) after the next scope's pop: %r against %r before it; keyed on equality, the missing-root pop "
                         "moving none of the three (it answered no tree)" % ((d2["hit"], d2["miss"], d2["served"]), (d["hit"], d["miss"], d["served"])))


class ScopedInvalidation(_World):
    """(5) An eviction drops from every open scope what became stale and nothing else (since 2026-09-21): the evicted
    root's pair, the stamps indexed from that tree and the launch folds keyed on it (a fold's root is the transcript's own
    subagents root whatever tree the agent's file resolved under; the rule, its bound and the case here that executes both
    are stated once, in _subagent_scope's docstring). Every other root's pair, stamps and launch folds are still served. Before 2026-09-21 one process-wide generation
    (_SUBAGENT_TREES_GEN alone) emptied every scope's three maps on any root's eviction, so an ownership eviction of an
    unrelated root (most often an unowned sibling a miss scan inserted, forgotten by the next jobs pass) cost every held
    tree its D lstats again, every held stamp its stat and every awaiting agent its fold, once per forget rather than once
    per cycle, and re-folded launches that neither read nor depend on that root. The eviction here comes from the forget
    (nobody alive owns the other root) or, for the removed tree, from another thread's missing-root pop (a same-thread
    read of a held root is served before its lstat, so it never pops)."""

    def _other_root(self, tag="other"):
        """A second session's transcript and its tree beside it, walked into the cross-cycle memo and owned by nobody
        alive: (the transcript's path, the root)."""
        other_t = Path(self.td.name) / tag / (OTHER_SID + ".jsonl")
        other_t.parent.mkdir()
        other_t.write_text("")
        other = km._subagents_dir(other_t)
        (other / "workflows").mkdir(parents=True)
        _age(other)
        self.addCleanup(km._SUBAGENT_TREES.pop, str(other), None)
        km._subagent_tree(str(other))                     # walked into the cross-cycle memo: an entry stands
        self.assertIn(str(other), km._SUBAGENT_TREES)
        return str(other_t), other

    def _evict(self, roots, alive_paths):
        """The forget over the alive set (self.sub's session and `alive_paths`): the roots in `roots` leave the memo and
        nothing else does."""
        e0 = km._SUBAGENT_TREE_STATS["evict"]
        km._subagent_trees_forget([{"path": p} for p in [self.path] + list(alive_paths)])
        self.assertEqual(km._SUBAGENT_TREE_STATS["evict"] - e0, len(roots), "the forget evicted the unowned roots and only them")
        for r in roots:
            self.assertNotIn(str(r), km._SUBAGENT_TREES)
        self.assertIn(str(self.sub), km._SUBAGENT_TREES, "the alive session's root stays")

    def test_a_held_tree_survives_the_eviction_of_a_root_it_is_not(self):
        _op, other = self._other_root()
        sc = self._open()
        b = self._stats()
        with self._spy() as sp:
            km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], D, "the hold: the cycle's one validation")
        self._evict([other], [])
        held = sc["trees"][str(self.sub)]
        with self._spy() as sp:
            out = km._subagent_tree(str(self.sub))
        dirs = out[0]
        self.assertEqual(sp.total()["dir_lstat"], 0,
                         "os.lstat on the held tree's directories on the read after an unrelated root's eviction: %d; keyed on 0, since "
                         "another root leaving the memo leaves this pair as fresh as it was; one process-wide generation emptied the scope "
                         "and cost D = %d lstats again, once per forget" % (sp.total()["dir_lstat"], D))
        self.assertIs(out, held[0], "and the read was answered the pair held before the eviction (served), keyed on identity")
        self.assertEqual(len(dirs), D)
        self.assertEqual((self._delta(b)["hit"], self._delta(b)["miss"]), (1, 0), "one validation in the scope, none after the eviction")

    def test_a_held_stamp_survives_the_eviction_of_a_root_its_directory_is_not_under(self):
        _op, other = self._other_root()
        sc = self._open()
        km._subagent_tree(str(self.sub))                  # the D directories' stamps indexed from the held tree
        target = self.dirs[3]
        held = sc["stamps"][target]
        with self._spy() as sp:
            r1 = km._dir_stamp(target)
        self.assertEqual(sp.total()["dir_stat"], 0, "os.stat for the directory's stamp before the eviction: %d; keyed on 0" % sp.total()["dir_stat"])
        self.assertIs(r1, held[0], "the call was answered the stamp indexed from the held tree (served), keyed on identity")
        self._evict([other], [])
        with self._spy() as sp:
            r2 = km._dir_stamp(target)
        self.assertEqual(sp.total()["dir_stat"], 0,
                         "os.stat for a held stamp on the read after an unrelated root's eviction: %d; keyed on 0, since the stamp was "
                         "indexed from a tree that did not leave the memo; one process-wide generation emptied the scope's stamps and "
                         "cost one stat per held stamp" % sp.total()["dir_stat"])
        self.assertIs(r2, held[0], "and the read after the eviction was answered the same held stamp (served), keyed on identity")
        self.assertEqual(r1, r2)
        self.assertIsNotNone(r2[1])

    def test_held_launch_folds_survive_the_eviction_of_a_root_their_files_are_not_under(self):
        _op, other = self._other_root()
        self._open()
        folded = []
        with self._counting_fold(folded), self._spy() as sp:
            aw1 = km._session_awaiting(SID, self.path, True)
        self.assertEqual((aw1 or {}).get("count"), A)
        self.assertEqual((len(folded), sp.total()["file_stat"]), (A, A), "the hold: one fold and one file stat per agent")
        self._evict([other], [])
        del folded[:]
        with self._counting_fold(folded), self._spy() as sp:
            aw2 = km._session_awaiting(SID, self.path, True)
        t = sp.total()
        self.assertEqual((aw2 or {}).get("count"), A)
        self.assertEqual((len(folded), t["file_stat"], t["dir_lstat"], t["dir_stat"]), (0, 0, 0, 0),
                         "(folds, agent-file stats, tree lstats, stamp stats) on the read after an unrelated root's eviction: %r; keyed on "
                         "every held launch fold being served (0 folds, 0 file stats), since the transcript's own root, the root every "
                         "fold is keyed on, did not leave the memo, and on the tree and its stamps beside them (0, 0); one process-wide generation emptied "
                         "the launches map with the rest, re-folded A = %d files and re-validated the tree (D = %d lstats)"
                         % ((len(folded), t["file_stat"], t["dir_lstat"], t["dir_stat"]), A, D))

    def test_a_cached_agent_file_is_not_answered_after_another_thread_found_its_tree_gone(self):
        """The stamps half, behavioural (fresh-2 of the round-1 review): a scope holds the tree and has resolved an agent's
        file through _subagent_file (the memo's cached path, its stamp re-check served from the scope); the tree is removed
        on disk and a thread with no scope (the jobs thread to the pusher's, say) reads the root, the missing-root pop. The
        holding thread's next _subagent_file answers None: the removed tree's stamps are dropped at their lookup, the
        re-check stats and mismatches, the walk finds nothing. Keys on None against the cached path: a scope whose stamps
        survived their root's eviction (not vouched by their root, or vouched by another) answers the path of a file that
        is gone, which build_subagent shows as an error pane."""
        sc = self._open()
        aid = self.aids[0]
        km._subagent_tree(str(self.sub))                  # held: its D stamps indexed under this root
        with self._spy() as sp:
            p1 = km._subagent_file(self.path, aid)
        self.assertIsNotNone(p1)
        self.assertTrue(Path(p1).is_file())
        self.assertEqual(sp.total()["dir_stat"], 0, "os.stat on the tree's directories for the hit's stamp re-check: %d; keyed on 0 (the re-check "
                                                    "reached no disk: the stamps are indexed from the held tree)" % sp.total()["dir_stat"])
        shutil.rmtree(self.sub)
        errs, seen = [], {}

        def helper():                                     # no scope on this thread (_live_scope is thread-local)
            try:
                seen["scope"] = _scope()
                seen["pop"] = km._subagent_tree(str(self.sub))
                seen["gen"] = km._SUBAGENT_TREES_GEN[0]
            except Exception:
                errs.append(traceback.format_exc())
        th = threading.Thread(target=helper, name="stamps-helper")
        th.start()
        th.join(30)
        self.assertFalse(th.is_alive(), "the helper returned")
        self.assertEqual(errs, [])
        self.assertIsNone(seen.get("scope"), "the helper thread holds no scope")
        self.assertEqual(seen.get("pop"), ((), ()), "the missing-root pop answered (), ()")
        self.assertNotIn(str(self.sub), km._SUBAGENT_TREES)
        p2 = km._subagent_file(self.path, aid)
        self.assertIsNone(p2, "the agent file answered by the holding thread after another thread found the tree gone: %r; keyed on None "
                              "(the removed tree's held stamps are dropped at their lookup, the re-check stats and mismatches, the walk "
                              "finds nothing); a scope whose stamps survived their root's eviction answered the cached path %r to a "
                              "removed file" % (p2, p1))
        self.assertEqual(km._SUBAGENT_ROOT_EVICTED.get(str(self.sub)), seen.get("gen"),
                         "the pop recorded this root's eviction at the value the gen moved to")
        self.assertNotIn(str(self.sub), sc["trees"], "the removed tree's held pair left the scope at its lookup")

    def test_own_stat_stamps_are_dropped_by_any_eviction_so_a_cached_agent_file_is_not_answered_after_its_tree_went(self):
        """The stamps _dir_stamp took itself, vouched by no root: the owner-lookup-first order (a _subagent_file hit inside the
        scope BEFORE any tree read this cycle, as a command row's owner lookup makes it) re-stats every directory the agent's
        walk read and holds each as an own stat under root None, since no tree the scope could name was read. Held within the
        cycle (a second lookup is served, 0 stats) and released at ANY eviction: the tree is removed on disk and popped by a
        thread with no scope, and the holding thread's next _subagent_file answers None, the own stats dropped at their lookup
        (the re-check stats and mismatches, the walk finds nothing). Keys on None against the cached path: a vouch that answers
        True for root None serves the own stats past the tree's removal and answers the path of a file that is gone, which
        build_subagent shows as an error pane; the case above pins the same for stamps indexed from a held tree, this one the
        population that has no root to key on."""
        sc = self._open()
        aid = self.aids[0]
        stamps0, p0 = km._SUBAGENT_FILE_CACHE[(self.path, aid)][:2]   # (stamps, resolution, the walk's noted keys)
        dirs_read = [sd for sd, _m in stamps0 if sd in self.dirset]
        self.assertTrue(dirs_read, "premise: the agent's walk read directories of the tree")
        with self._spy() as sp:
            p1 = km._subagent_file(self.path, aid)         # the hit's re-check, no tree read this cycle: own stats
        self.assertEqual(p1, p0)
        self.assertEqual(sp.total()["dir_stat"], len(dirs_read), "premise: the hit re-stat'd every directory its walk read, nothing served")
        self.assertNotIn(str(self.sub), sc["trees"], "premise: no tree read this cycle")
        held = [sc["stamps"].get(sd) for sd in dirs_read]
        self.assertTrue(all(h is not None and h[1] is None for h in held),
                        "premise: each re-checked directory's stamp is held as an own stat, vouched by no root: %r" % (held[:2],))
        with self._spy() as sp:
            p1b = km._subagent_file(self.path, aid)
        self.assertEqual((p1b, sp.total()["dir_stat"]), (p0, 0), "held within the cycle: the second lookup is served the own stats, 0 stats")
        shutil.rmtree(self.sub)
        seen = self._read_on_a_thread_with_no_scope(self.sub)
        self.assertEqual(seen.get("answer"), ((), ()), "the missing-root pop on the thread with no scope")
        self.assertEqual(km._SUBAGENT_ROOT_EVICTED.get(str(self.sub)), seen.get("gen"), "the pop recorded this root's eviction")
        with self._spy() as sp:
            p2 = km._subagent_file(self.path, aid)
        self.assertIsNone(p2, "the agent file answered after another thread found its tree gone, the stamps held as own stats: %r; keyed "
                              "on None (an own stat is vouched by no root, so any eviction drops it at its lookup: the re-check stats and "
                              "mismatches, the walk finds nothing); a vouch that answers True for root None serves the own stats and answers "
                              "the cached path %r to a removed file" % (p2, p0))
        self.assertGreater(sp.total()["dir_stat"], 0, "the own stats were dropped and re-taken (stat attempts on the removed directories), not served")
        for sd in dirs_read:
            self.assertNotIn(sd, sc["stamps"], "the dropped own stat left the scope at its lookup (a failed stat is never held)")

    def test_an_own_stat_stamp_is_re_taken_after_an_unrelated_roots_eviction_where_a_tree_indexed_stamp_is_served(self):
        """The cost face of the same rule, the one the reference and the ledger state per eviction event: an own stat (root
        None) costs one stat after ANY eviction, an unrelated root's included, where a stamp indexed from a held tree costs 0
        across the same eviction (the survival case above). Keys on 1 stat after the unrelated eviction while held as an own
        stat, then 0 after the next such eviction once the tree's hold has re-indexed the same directory under its root: a
        vouch that answers True for root None serves the own stat (0 where 1 is owed) and, by the same answer, serves it past
        its own tree's removal (the case above)."""
        _op, other = self._other_root()
        sc = self._open()
        target = self.dirs[3]
        with self._spy() as sp:
            r1 = km._dir_stamp(target)                    # no tree read this cycle: an own stat
        self.assertEqual(sp.total()["dir_stat"], 1)
        self.assertIsNotNone(r1[1])
        self.assertIsNone(sc["stamps"][target][1], "premise: held as an own stat, root None")
        held = sc["stamps"][target]
        with self._spy() as sp:
            r1b = km._dir_stamp(target)
        self.assertEqual(sp.total()["dir_stat"], 0, "os.stat for the own stat's directory on the second call in the cycle: %d; keyed on 0"
                         % sp.total()["dir_stat"])
        self.assertIs(r1b, held[0], "the second call was answered the own stat the scope held (served), keyed on identity")
        self._evict([other], [])
        with self._spy() as sp:
            r2 = km._dir_stamp(target)
        self.assertEqual(sp.total()["dir_stat"], 1,
                         "os.stat for an own stamp on the read after an UNRELATED root's eviction: %d; keyed on 1, re-taken (vouched by no "
                         "root, so any eviction drops it: the one stat per own stamp per eviction event the reference states); a vouch that "
                         "answers True for root None serves it (0) and serves it past its own tree's removal too" % sp.total()["dir_stat"])
        self.assertEqual(r1, r2)
        km._subagent_tree(str(self.sub))                  # the tree's hold re-indexes the same directory under its root
        self.assertEqual(sc["stamps"][target][1], str(self.sub), "premise: now indexed from the held tree, vouched by its root")
        _op2, other2 = self._other_root("other2")
        self._evict([other2], [])
        held = sc["stamps"][target]
        with self._spy() as sp:
            r3 = km._dir_stamp(target)
        self.assertEqual(sp.total()["dir_stat"], 0,
                         "os.stat for the same directory's stamp, indexed from the held tree, after another unrelated eviction: %d; keyed "
                         "on 0 (its root did not leave the memo), the contrast with the own stat's 1" % sp.total()["dir_stat"])
        self.assertIs(r3, held[0], "and the call was answered the stamp indexed from the held tree (served), keyed on identity")
        self.assertEqual(r3, r1)

    def test_held_launch_folds_are_dropped_when_their_own_root_leaves_the_memo(self):
        """The launches half, behavioural (extra7-1's refuters: a launch fold is keyed on the session's own subagents root,
        the rule _subagent_scope's docstring states, so it is stale when THAT root leaves the memo and fresh across any other
        root's eviction; a fold that survived its own root's eviction served a mixed-vintage attribution). A command row
        the ledger does not attribute; agent 0's transcript gains its launch mid-cycle, and the held folds keep the
        command top-level for the rest of the cycle (the lag the scope accepts). Then the own root leaves the memo (nobody
        alive owns it): the folds keyed on it are dropped, the read after re-folds every agent's file and the command
        nests under agent 0. Keys on the folds (A) and the nesting: a launches map not vouched by its own root served the
        held folds (0 folds, the command still top-level)."""
        cmd = {"tid": "toolu_stamps_cmd1", "desc": "run the parser test chunk", "t": 130, "type": "local_bash"}
        km._bg_live_norm = lambda sid, path, live=None: [cmd]
        names = sorted("agent-%s.jsonl" % a for a in self.aids)
        self._open()
        folded = []
        with self._counting_fold(folded):
            aw1 = km._session_awaiting(SID, self.path, True)
        self.assertEqual((aw1 or {}).get("count"), A + 1, "the A agents and the command, attributed to nobody, all top-level: %r" % (aw1,))
        self.assertEqual(sorted(folded), names, "the hold: one fold per agent")
        ap = self.wfroot / ("wf_%016x" % 0) / ("agent-%s.jsonl" % self.aids[0])
        ap.write_text(json.dumps({"type": "assistant", "timestamp": "2026-09-10T10:00:00.000Z", "message": {"content": [
            {"type": "tool_use", "id": cmd["tid"], "name": "Bash",
             "input": {"run_in_background": True, "command": "uv run pytest tests/test_parser.py -q", "description": cmd["desc"]}}]}}) + "\n")
        del folded[:]
        with self._counting_fold(folded):
            aw2 = km._session_awaiting(SID, self.path, True)
        self.assertEqual(((aw2 or {}).get("count"), folded), (A + 1, []),
                         "held for the cycle: no fold, and the command stays top-level until the next cycle (the lag the scope accepts)")
        b = self._stats()
        km._subagent_trees_forget([])                     # nobody alive: the own root leaves the memo
        self.assertEqual(self._delta(b)["evict"], 1)
        del folded[:]
        with self._counting_fold(folded):
            aw3 = km._session_awaiting(SID, self.path, True)
        self.assertEqual(sorted(folded), names,
                         "folds on the read after the own root's eviction: %r; keyed on every agent's fold being redone (A = %d, one each), "
                         "since the root that left the memo is the transcript's own, the root every fold is keyed on; a launches map not vouched by its own root "
                         "served the held folds (0)" % (sorted(folded), A))
        self.assertEqual((aw3 or {}).get("count"), A, "the command nests under agent 0, whose re-read fold names its launch: %r" % (aw3,))
        agent0 = [it for it in (aw3 or {}).get("items", []) if it.get("agentId") == self.aids[0]]
        self.assertEqual([w["id"] for w in (agent0[0].get("waits", []) if agent0 else [])], [cmd["tid"]],
                         "the command row nested under agent 0: %r" % (agent0,))

    def _sibling_resolved_agent(self):
        """The /clear-fork shape, S = 2 transcripts in one project directory: a second transcript beside this session's and,
        under ITS subagents tree (D_sib = 3 directories: the root, workflows/ and one workflow directory), a fourth awaiting
        agent of THIS session whose transcript names one background command's launch. Warmed outside any scope (the
        premise: the miss scan resolves the file under the sibling's tree and inserts the sibling root into the walk memo),
        then the agent-file memo's entry for the agent is dropped, so the cycle's first read resolves it through the miss
        walk again, which reads the sibling's tree into the scope (R = 2 roots held). Returns (the sibling transcript's
        path, the sibling root, its directories, the agent's file, the agent id, the command)."""
        pdir = self.tpath.parent
        sib_t = pdir / (OTHER_SID + ".jsonl")
        sib_t.write_text("")
        sib = km._subagents_dir(sib_t)
        wf = sib / "workflows" / ("wf_%016x" % 0x7c40)
        wf.mkdir(parents=True)
        aid = "a%016x" % 0x7c40
        cmd = {"tid": "toolu_stamps_sibcmd", "desc": "run the tests", "t": 130, "type": "local_bash"}
        (wf / ("agent-%s.meta.json" % aid)).write_text(json.dumps(
            {"agentType": "Workflow", "description": "sort the notes", "spawnDepth": 1, "toolUseId": "toolu_stamps_sib0"}))
        ap = wf / ("agent-%s.jsonl" % aid)
        ap.write_text(json.dumps({"type": "assistant", "timestamp": "2026-09-10T10:00:00.000Z", "message": {"content": [
            {"type": "tool_use", "id": cmd["tid"], "name": "Bash",
             "input": {"run_in_background": True, "command": "uv run pytest -q", "description": cmd["desc"]}}]}}) + "\n")
        _age(sib)
        sibdirs = [str(sib), str(sib / "workflows"), str(wf)]
        self.live_aids.append(aid)
        km._bg_live_norm = lambda sid, path, live=None: [cmd]
        self.addCleanup(km._SUBAGENT_TREES.pop, str(sib), None)
        self.addCleanup(km._SUBAGENT_META_CACHE.pop, str(sib), None)
        self.addCleanup(lambda: [km._AGENT_LAUNCH_IDS_CACHE.pop(k, None) for k in list(km._AGENT_LAUNCH_IDS_CACHE)
                                 if str(k).startswith(str(sib))])
        aw = km._session_awaiting(SID, self.path, True)
        self.assertEqual((aw or {}).get("count"), A + 1, "premise: A + 1 agents, the command nested under the fourth: %r" % (aw,))
        self.assertEqual(km._SUBAGENT_FILE_CACHE.get((self.path, aid), (None, None))[1], ap,
                         "premise: the fourth agent's file resolved under the SIBLING root")
        self.assertIn(str(sib), km._SUBAGENT_TREES, "premise: the miss scan inserted the sibling root into the walk memo")
        km._SUBAGENT_FILE_CACHE.pop((self.path, aid), None)   # no entry: the cycle's first read walks and reads the sibling's tree
        return str(sib_t), str(sib), sibdirs, ap, aid, cmd

    @staticmethod
    def _nested_under(aw, aid):
        """The ids of the rows nested under agent `aid` in an awaiting answer ([] when none, or no such row)."""
        rows = [it for it in (aw or {}).get("items", []) if it.get("agentId") == aid]
        return [w["id"] for w in (rows[0].get("waits", []) if rows else [])]

    def test_a_fold_resolved_under_a_siblings_tree_is_keyed_on_the_own_root_and_served_past_the_siblings_removal_until_the_cycle_ends(self):
        """The fold's root, executed at both edges (the rule and its bound are stated once, in _subagent_scope's docstring).
        A launch fold is keyed on the transcript's OWN subagents root whatever tree the agent's file resolved under, so the
        sibling root's eviction drops none of this session's folds (0 folds, the attribution still served) while it does
        drop the sibling's held pair (its next read walks), and the own root's eviction drops all of them (A + 1 folds, the
        agent whose file lies under the sibling's tree included). The bound: with the sibling's tree gone on disk and
        popped by a thread with no hold on it, the fold from the gone file is served until the cycle ends (the command
        still nests under an agent whose file no longer exists), and the next cycle's first read resolves the file again,
        to nothing, so the command is top-level there and the own agents fold once more. S = 2 transcripts in one project
        directory, A = 3 + 1 agents, R = 2 roots read, D = 8, D_sib = 3. A fold keyed on the root the file resolved under
        re-folds the agent at the sibling's eviction (1 fold where 0); a launches map carried across cycles serves the gone
        file's attribution in cycle two (the command still nested, 0 folds where A)."""
        sib_t, sib, sibdirs, ap, aid, cmd = self._sibling_resolved_agent()
        names = sorted("agent-%s.jsonl" % a for a in self.aids + [aid])
        own_names = sorted("agent-%s.jsonl" % a for a in self.aids)
        sc = self._open()
        folded = []
        with self._counting_fold(folded):
            aw1 = km._session_awaiting(SID, self.path, True)
        self.assertEqual(((aw1 or {}).get("count"), sorted(folded), self._nested_under(aw1, aid)), (A + 1, names, [cmd["tid"]]),
                         "the hold: one fold per agent, the command nested under the sibling-resolved agent: %r" % (aw1,))
        self.assertIn(sib, sc["trees"], "premise: the miss walk read the sibling's tree into the scope (R = 2)")
        held = sc["launches"].get((self.path, aid))
        self.assertIsNotNone(held, "premise: the sibling-resolved agent's fold is held")
        b = self._stats()
        km._subagent_trees_forget([{"path": self.path}])   # this session alive, the sibling's root owned by nobody: the sibling leaves
        self.assertEqual(self._delta(b)["evict"], 1)
        self.assertNotIn(sib, km._SUBAGENT_TREES)
        self.assertIn(str(self.sub), km._SUBAGENT_TREES)
        del folded[:]
        with self._counting_fold(folded), self._spy() as sp:
            aw2 = km._session_awaiting(SID, self.path, True)
        got = (len(folded), self._nested_under(aw2, aid), sp.total()["file_stat"])
        self.assertEqual(got, (0, [cmd["tid"]], 0),
                         "(folds, the command's nesting, agent-file stats) on the read after the SIBLING root's eviction: %r; keyed on 0 "
                         "folds with the attribution still served, since every fold of this session is keyed on the transcript's own root, "
                         "which did not leave the memo, the agent whose file lies under the sibling's tree included; a fold keyed on the root "
                         "its file resolved under is dropped here and folded again (1)" % (got,))
        self.assertTrue(km._subagent_vouched(held[1], held[2]), "the held fold is still vouched after the sibling's eviction")
        b = self._stats()
        with _Spy(set(sibdirs), sib) as ssp:
            dirs, _stats = km._subagent_tree(sib)
        d = self._delta(b)
        got = (len(dirs), ssp.total()["dir_lstat"], d["served"], d["miss"])
        self.assertEqual(got, (len(sibdirs), len(sibdirs), 0, 1),
                         "(directories, os.lstat on the sibling's directories, served, miss) on the sibling tree's read after its eviction: "
                         "%r; keyed on its held pair being dropped at the lookup and the read walking (D_sib = %d lstats, one miss, nothing "
                         "served): what the sibling's eviction drops is the sibling's pair, not this session's folds" % (got, len(sibdirs)))
        b = self._stats()
        km._subagent_trees_forget([{"path": sib_t}])      # the sibling's session alive, this session's root owned by nobody: the own root leaves
        self.assertEqual(self._delta(b)["evict"], 1)
        self.assertNotIn(str(self.sub), km._SUBAGENT_TREES)
        self.assertIn(sib, km._SUBAGENT_TREES)
        del folded[:]
        with self._counting_fold(folded):
            aw3 = km._session_awaiting(SID, self.path, True)
        got = (sorted(folded), self._nested_under(aw3, aid))
        self.assertEqual(got, (names, [cmd["tid"]]),
                         "(folds, the command's nesting) on the read after the OWN root's eviction: %r; keyed on every fold of the session "
                         "being redone (A + 1 = %d, the agent whose file lies under the sibling's tree included, since its fold too is keyed "
                         "on the own root) and the command nesting again under the fresh fold; a fold keyed on the root its file resolved "
                         "under survives the own root's eviction here (A folds, not A + 1)" % (got, A + 1))
        held3 = sc["launches"].get((self.path, aid))
        self.assertIsNotNone(held3, "premise: the fold re-held after the own root's eviction")
        shutil.rmtree(sib)                                # the bound's edge: the sibling's tree gone on disk...
        seen = self._read_on_a_thread_with_no_scope(sib)  # ...and popped by a thread with no hold on it
        self.assertEqual(seen.get("answer"), ((), ()), "the missing-root pop on the thread with no scope")
        self.assertEqual(km._SUBAGENT_ROOT_EVICTED.get(sib), seen.get("gen"), "the pop recorded the sibling's eviction")
        self.assertFalse(ap.exists(), "premise: the agent's file is gone with the sibling's tree")
        del folded[:]
        with self._counting_fold(folded):
            aw4 = km._session_awaiting(SID, self.path, True)
        got = (len(folded), self._nested_under(aw4, aid), (aw4 or {}).get("count"))
        self.assertEqual(got, (0, [cmd["tid"]], A + 1),
                         "(folds, the command's nesting, count) on the same cycle's read after the sibling's tree went and another thread "
                         "popped it: %r; keyed on the fold from the gone file being served (0 folds, the command still nested under the agent "
                         "whose file no longer exists): the bound the design accepts, a fold keyed on the own root stands until the cycle "
                         "ends whatever became of the sibling's tree" % (got,))
        self.assertTrue(km._subagent_vouched(held3[1], held3[2]), "the fold, keyed on the own root, is still vouched after the sibling's pop")
        km._subagent_scope_close()                        # the cycle ends
        self._open()                                      # the next cycle
        del folded[:]
        with self._counting_fold(folded):
            aw5 = km._session_awaiting(SID, self.path, True)
        got = (sorted(folded), self._nested_under(aw5, aid), (aw5 or {}).get("count"))
        self.assertEqual(got, (own_names, [], A + 2),
                         "(folds, the command's nesting, count) on the next cycle's first read: %r; keyed on the bound's edge, the fold "
                         "re-read by the next cycle (the gone file resolves to nothing, so no fold for it and the command is top-level: "
                         "A + 2 = %d rows) and the own agents folded once more (A = %d); a launches map carried across cycles serves the "
                         "gone file's attribution in cycle two (0 folds, the command still nested)" % (got, A + 2, A))

    def test_the_table_of_evicted_roots_at_its_cap_is_cleared_and_every_held_entry_dropped_once(self):
        """The table is bounded: an eviction of a root not in it while it holds _SUBAGENT_ROOT_EVICTED_MAX roots clears it
        and records the clear's generation, so every entry held under an older generation is dropped at its next lookup
        (one re-validation) and entries held after it are vouched by the table again. Single-threaded: it shows the clear's
        edge on one thread; that a clear serves nothing stale while evictions and vouches run on other threads is
        EvictionTableLock's (the clear-straddle and wiped-record cases).
        Keys on each of the three maps at the clear edge, by execution and not through the shared predicate alone: the held
        pair costs D lstats once on the read after the clearing eviction (0 before it and after that), a stamp indexed from
        the held tree costs 1 stat once, and the held launch folds are redone once (A folds), where a clear that recorded no
        generation would leave every one of them vouched (0 where D, 1 and A are owed), a stamp or launch lookup blind to the
        clear (a vouch inlined without the cleared-generation check) finds no eviction record for the root, which never left
        the memo, and serves what was held before the clear (0), and a table that never cleared would grow by one entry per
        root ever evicted."""
        cap = 4
        target = self.dirs[3]
        names = sorted("agent-%s.jsonl" % a for a in self.aids)
        with mock.patch.object(km, "_SUBAGENT_ROOT_EVICTED_MAX", cap), mock.patch.dict(km._SUBAGENT_ROOT_EVICTED, {}, clear=True), \
                mock.patch.object(km, "_SUBAGENT_ROOTS_CLEARED_GEN", [0]):
            others = [self._other_root("other%d" % i) for i in range(cap + 1)]   # cap + 1 unowned roots, one transcript each
            sc = self._open()
            with self._spy() as sp:
                km._subagent_tree(str(self.sub))
            self.assertEqual(sp.total()["dir_lstat"], D, "the hold")
            folded = []
            with self._counting_fold(folded), self._spy() as sp:
                aw = km._session_awaiting(SID, self.path, True)   # the launch folds held, the stamps served from the held tree
            self.assertEqual(((aw or {}).get("count"), sorted(folded), sp.total()["dir_lstat"], sp.total()["dir_stat"]), (A, names, 0, 0),
                             "(count, folds, tree lstats, stamp stats) on the read after the hold: %r; keyed on (A = %d, one fold per agent, "
                             "0, 0): the read reached the disk for the folds alone"
                             % (((aw or {}).get("count"), sorted(folded), sp.total()["dir_lstat"], sp.total()["dir_stat"]), A))
            for i in range(cap):                          # cap evictions of distinct roots fill the table; the held pair survives each
                self._evict([others[i][1]], [p for p, _r in others[i + 1:]])
                held = sc["trees"][str(self.sub)]
                with self._spy() as sp:
                    out = km._subagent_tree(str(self.sub))
                self.assertEqual(sp.total()["dir_lstat"], 0, "os.lstat on the held tree's directories after eviction %d of %d distinct roots: %d; "
                                                             "keyed on 0" % (i + 1, cap, sp.total()["dir_lstat"]))
                self.assertIs(out, held[0], "and the read after eviction %d was answered the held pair (served), keyed on identity" % (i + 1,))
            self.assertEqual(len(km._SUBAGENT_ROOT_EVICTED), cap, "the table holds one entry per evicted root, at its cap")
            self._evict([others[cap][1]], [])             # one more distinct root: the table is cleared
            self.assertEqual(sorted(km._SUBAGENT_ROOT_EVICTED), [str(others[cap][1])], "cleared, then the clearing root recorded")
            self.assertEqual(km._SUBAGENT_ROOTS_CLEARED_GEN[0], km._SUBAGENT_TREES_GEN[0], "the clear recorded the generation it happened at")
            self.assertNotIn(str(self.sub), km._SUBAGENT_ROOT_EVICTED, "premise: the held tree's root has no eviction record (it never left the memo)")
            with self._spy() as sp:
                km._dir_stamp(target)                     # BEFORE the tree's re-read, which would re-index it under the new generation
            self.assertEqual(sp.total()["dir_stat"], 1,
                             "os.stat for a stamp indexed from the held tree on the read after the clearing eviction: %d; keyed on 1, dropped "
                             "once by the clear (the cleared generation outranks the hold's); a stamp lookup blind to the clear finds no "
                             "eviction record for its root and serves what was held before the clear (0)" % sp.total()["dir_stat"])
            with self._spy() as sp:
                dirs, _stats = km._subagent_tree(str(self.sub))
            self.assertEqual(sp.total()["dir_lstat"], D,
                             "os.lstat on the held tree's directories on the read after the clearing eviction: %d; keyed on the held pair being "
                             "dropped once (D = %d, a validation), since a cleared table can no longer vouch for what was held before the "
                             "clear; a clear that recorded no generation leaves it served (0)" % (sp.total()["dir_lstat"], D))
            self.assertEqual(len(dirs), D)
            del folded[:]
            with self._counting_fold(folded), self._spy() as sp:
                aw = km._session_awaiting(SID, self.path, True)
            self.assertEqual(sorted(folded), names,
                             "folds on the read after the clearing eviction: %r; keyed on every held launch fold redone once (A = %d), since the "
                             "folds were held before the clear; a launch lookup blind to the clear finds no eviction record for the own root "
                             "and serves the folds held before it (0)" % (sorted(folded), A))
            self.assertEqual(((aw or {}).get("count"), sp.total()["dir_lstat"], sp.total()["dir_stat"]), (A, 0, 0),
                             "the read after the clear costs the tree nothing more: re-held by the read above, its stamps re-indexed")
            held_pair, held_stamp = sc["trees"][str(self.sub)], sc["stamps"][target]
            with self._spy() as sp:
                out, r = km._subagent_tree(str(self.sub)), km._dir_stamp(target)
            self.assertEqual((sp.total()["dir_lstat"], sp.total()["dir_stat"]), (0, 0),
                             "(tree lstats, stamp stats) on the reads after the re-hold: %r; keyed on (0, 0), held again under the new generation"
                             % ((sp.total()["dir_lstat"], sp.total()["dir_stat"]),))
            self.assertIs(out, held_pair[0], "the tree read was answered the re-held pair (served), keyed on identity")
            self.assertIs(r, held_stamp[0], "and the stamp call the re-indexed stamp (served), keyed on identity")


class _PausingTable(dict):
    """The eviction table (_SUBAGENT_ROOT_EVICTED) with one pause point, armed per case for one named thread: "store"
    pauses that thread's store of `key` before it lands (its value already computed), "clear before" pauses its clear()
    before the table is emptied, "clear after" once it has been. At the pause the thread sets `reached` and waits for
    `go`; every other thread, and the armed thread after its one pause, runs through. The hook calls nothing of the
    kernel's, so the thread paused in it, which holds _SUBAGENT_EVICT_LOCK at that point, never asks for the lock again
    (the notes-dir probe's hooks called the kernel from inside the clear and the store on the same thread, which a lock
    that admits no call under it cannot serve)."""

    def __init__(self):
        super().__init__()
        self.phase = self.key = self.thread = None
        self.reached, self.go = threading.Event(), threading.Event()

    def arm(self, phase, thread, key=None):
        self.phase, self.thread, self.key = phase, thread, key

    def _at(self, phase, key=None):
        if self.phase != phase or threading.current_thread().name != self.thread or (phase == "store" and key != self.key):
            return
        self.phase = None
        self.reached.set()
        if not self.go.wait(30):
            raise AssertionError("the thread paused at %r was never released" % phase)

    def __setitem__(self, k, v):
        self._at("store", k)
        super().__setitem__(k, v)

    def clear(self):
        self._at("clear before")
        super().clear()
        self._at("clear after")


class _QueueWatch:
    """_SUBAGENT_EVICT_LOCK behind a wrapper that marks the moment a thread finds the lock held by another thread and is
    about to wait for it (its non-blocking try failed): it sets the thread's Event in `events` (keyed by thread name) and
    records (thread, holder) in `queued`. A case waits on that Event, which the thread also sets when it ends, before it
    releases the paused holder, so it knows the second thread has reached the lock, where a kernel with no lock runs the
    same thread to its end, with no time window."""

    def __init__(self, real, events):
        self.real, self.events, self.holder, self.queued = real, events, None, []

    def acquire(self, blocking=True, timeout=-1):
        me = threading.current_thread().name
        if self.real.acquire(False):
            self.holder = me
            return True
        if not blocking:
            return False
        self.queued.append((me, self.holder))
        ev = self.events.get(me)
        if ev is not None:
            ev.set()
        if not self.real.acquire(True, timeout):
            return False
        self.holder = me
        return True

    def release(self):
        self.holder = None
        self.real.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()
        return False


class EvictionTableLock(_World):
    """(9) The eviction table's writes and the vouch's reads under one lock (round 2 of #882, group E; the lock's lifetime
    and what it guards are stated once, at _SUBAGENT_EVICT_LOCK). Until then _subagent_root_evicted wrote the gen, the
    table and the cleared generation unlocked and _subagent_vouched read them unlocked, which left three windows in which
    a vouch answered True for an entry held before its root's latest eviction. Each window case drives its window with
    real threads: the writing thread is paused inside the table (_PausingTable) at the window's line, the other thread
    runs until it queues behind the lock (_QueueWatch) or, on a kernel with no lock, to its end, and then the paused
    thread is released. Each window's vouch answers True with no lock and False with it; the end-to-end case drives the
    out-of-order store through the real forget, walk and pop until a removed tree's pair is served (2 directories with no
    lock, 0 with it), beside its control with no race (0 on both). Every wait is bounded at 30 s, so a lost wake fails
    instead of hanging, and nothing waits on a time window."""

    def _roots(self):
        """Three root strings under the test's temp directory (the table cases never touch the disk)."""
        return tuple(os.path.join(self.td.name, n, "subagents") for n in ("r", "s1", "s2"))

    def _eviction_world(self, table, cap=None):
        """The table swapped for `table`, the cleared generation for a fresh [0], the cap for `cap` when given and the lock,
        on a kernel that has one, for a _QueueWatch over it; each put back by cleanup. The table's `go` is kept as the gate
        _run's cleanups set: every thread a case starts goes through _run after this call, so its cleanup, registered later,
        runs first (unittest runs cleanups last in, first out) and no paused thread writes into the restored globals.
        Returns the watch (None on a kernel with no lock)."""
        self.events, self.gate = {}, table.go
        real = getattr(km, "_SUBAGENT_EVICT_LOCK", None)
        watch = _QueueWatch(real, self.events) if real is not None else None
        patches = [mock.patch.object(km, "_SUBAGENT_ROOT_EVICTED", table), mock.patch.object(km, "_SUBAGENT_ROOTS_CLEARED_GEN", [0])]
        if cap is not None:
            patches.append(mock.patch.object(km, "_SUBAGENT_ROOT_EVICTED_MAX", cap))
        if watch is not None:
            patches.append(mock.patch.object(km, "_SUBAGENT_EVICT_LOCK", watch))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return watch

    def _run(self, name, fn):
        """`fn` on a new thread named `name`: its thread, its result, its errors and the Event set when it queues behind
        the lock or ends. The thread's stop is registered as a cleanup before its start (tests/thread_ends.py's
        join_started: it sets the gate a paused thread waits on, then joins the thread if it started, bounded at 30 s; a
        thread whose start never ran is skipped, not joined, which lets the registration come first), so a failed
        assertion anywhere in the case still releases and joins it before the patches of _eviction_world stop."""
        run = SimpleNamespace(out={}, errs=[], ev=self.events.setdefault(name, threading.Event()))

        def body():
            try:
                run.out["value"] = fn()
            except Exception:
                run.errs.append(traceback.format_exc())
            finally:
                run.ev.set()
        run.thread = threading.Thread(target=body, name=name, daemon=True)
        self.addCleanup(join_started, self.gate, [run.thread], 30)
        run.thread.start()
        return run

    def _wait(self, ev, what):
        self.assertTrue(ev.wait(30), "%s, within 30 s" % what)

    def _joined(self, run):
        run.thread.join(30)
        self.assertFalse(run.thread.is_alive(), "%s returned" % run.thread.name)
        self.assertEqual(run.errs, [], "%s raised" % run.thread.name)
        return run.out.get("value")

    def test_a_vouch_made_while_another_thread_clears_the_table_answers_false_for_a_root_evicted_after_its_hold(self):
        """The clear straddle. An entry for root r is held under g0, then r is evicted (its record g0 + 1, and the vouch
        answers False); the table fills to its cap (2), and a third root's eviction clears it. A vouch of (r, g0) made on
        another thread while the clearing thread stands after the clear and before the cleared generation's write read,
        with no lock, an empty table and the old cleared generation: True, an entry held before r's eviction vouched.
        Under the lock the vouch waits for the whole eviction and reads the cleared generation it wrote: False. Keys on
        that one answer, with the premise (False before the clear) and the answer after the clear asserted beside it. Red
        under the vouch's reads taken outside the lock and under the clear taken outside it."""
        table = _PausingTable()
        watch = self._eviction_world(table, cap=2)
        r, s1, s2 = self._roots()
        g0 = km._SUBAGENT_TREES_GEN[0]                    # an entry for r held under g0
        km._subagent_root_evicted(r)                      # r leaves the memo after the hold
        self.assertIs(km._subagent_vouched(r, g0), False, "premise: r's eviction outdates the hold")
        km._subagent_root_evicted(s1)                     # the table at its cap
        table.arm("clear after", "stamps-clearer")
        clearer = self._run("stamps-clearer", lambda: km._subagent_root_evicted(s2))   # a root not in the full table: the clear
        self._wait(table.reached, "the clearing thread reached the point after its clear")
        reader = self._run("stamps-reader", lambda: km._subagent_vouched(r, g0))
        self._wait(reader.ev, "the vouching thread queued behind the lock or returned")
        table.go.set()
        answer = self._joined(reader)
        self._joined(clearer)
        self.assertIs(answer, False,
                      "_subagent_vouched(r, g0) on another thread while the clearing thread stood between its clear and its "
                      "cleared generation's write: %r; keyed on False, r having been evicted after the hold (a vouch sees an "
                      "eviction whole or not at all); True is the straddle, the table read after the clear and the cleared "
                      "generation before its write" % (answer,))
        self.assertEqual(km._SUBAGENT_ROOTS_CLEARED_GEN[0], km._SUBAGENT_TREES_GEN[0], "the clear recorded the generation it happened at")
        self.assertIs(km._subagent_vouched(r, g0), False, "and a vouch after the clear answers False")
        if watch is not None:
            self.assertIn(("stamps-reader", "stamps-clearer"), watch.queued, "the vouch waited behind the clearing thread")

    def test_an_eviction_recorded_while_another_thread_clears_the_table_is_not_wiped_by_that_clear(self):
        """The wiped record. r is in the table (evicted once before) and the table is at its cap (2); a third root's
        eviction passes the cap check and is paused before its clear. An entry for r is then held under the gen that
        eviction made (g0: a read after its increment), and another thread evicts r again (g0 + 1, after the hold). With
        no lock that record landed before the paused clear, which wiped it, and the cleared generation written was the
        clearing thread's own g0, so no value above g0 named r's second eviction: vouched(r, g0) True, for as long as the
        hold lasts. Under the lock the second eviction waits for the whole clearing eviction and is recorded after the
        clear: False, the table holding both roots. Keys on that answer and on the table. Red under the clear taken outside
        the lock; the vouch here runs after both threads end, so the vouch's own lock is not this case's subject."""
        table = _PausingTable()
        self._eviction_world(table, cap=2)
        r, s1, s2 = self._roots()
        km._subagent_root_evicted(r)                      # r evicted once before
        km._subagent_root_evicted(s1)                     # the table at its cap
        table.arm("clear before", "stamps-clearer")
        clearer = self._run("stamps-clearer", lambda: km._subagent_root_evicted(s2))
        self._wait(table.reached, "the clearing thread passed the cap check and reached its clear")
        g0 = km._SUBAGENT_TREES_GEN[0]                    # an entry for r held under the clearing eviction's value
        evictor = self._run("stamps-evictor", lambda: km._subagent_root_evicted(r))   # r leaves the memo again, after the hold
        self._wait(evictor.ev, "the evicting thread queued behind the lock or returned")
        table.go.set()
        self._joined(evictor)
        self._joined(clearer)
        answer = km._subagent_vouched(r, g0)
        self.assertIs(answer, False,
                      "_subagent_vouched(r, g0) after r's second eviction (g0 + 1) ran while the clearing eviction (g0) stood "
                      "between its cap check and its clear: %r; keyed on False; True is the wiped record: the clear erased r's "
                      "g0 + 1 and the cleared generation written was g0; table %r, cleared generation %d, g0 %d"
                      % (answer, dict(table), km._SUBAGENT_ROOTS_CLEARED_GEN[0], g0))
        self.assertEqual(dict(table), {s2: g0, r: g0 + 1}, "the clearing root at g0 and r's second eviction at g0 + 1, recorded after the clear")

    def test_two_evictions_of_one_root_leave_its_record_at_the_later_one(self):
        """The out-of-order stores. A first eviction of r makes its increment (g0) and is paused before its store lands; an
        entry for r is then held under g0 (a read after the first eviction's pop, which re-inserted r), and a second
        eviction of r (g0 + 1, after the hold) runs on another thread. With no lock the second store landed first and the
        first one's late store moved r's record back to g0: vouched(r, g0) True, an entry held before r's latest eviction
        vouched. Under the lock the second eviction waits for the first to finish, so its store lands last: r's record
        g0 + 1, and False. Keys on that answer and on the record.

        The mutants, each applied alone to the locked kernel: the store taken outside the lock reds this case and the
        end-to-end case below (the paused store's value was computed before the pause, so the earlier value overwrites the
        later one, with max or without). The store without max, which round 2 of #882's group E listed among the mutants,
        is equivalent under the one lock and cannot fail a case: the increment and the store run in one critical section,
        _subagent_root_evicted is the table's one writer and holds the gen's one increment, so each store's g exceeds every
        value stored before it and max(existing, g) is g on every call. So the out-of-order window is pinned by the store
        taken outside the lock, not by the store without max; max stays in the kernel as ruled."""
        table = _PausingTable()
        watch = self._eviction_world(table)
        r, _s1, _s2 = self._roots()
        table.arm("store", "stamps-first", key=r)
        first = self._run("stamps-first", lambda: km._subagent_root_evicted(r))
        self._wait(table.reached, "the first eviction made its increment and reached its store")
        g0 = km._SUBAGENT_TREES_GEN[0]                    # an entry for r held under the first eviction's value
        second = self._run("stamps-second", lambda: km._subagent_root_evicted(r))   # r leaves the memo again, after the hold
        self._wait(second.ev, "the second eviction queued behind the lock or returned")
        table.go.set()
        self._joined(second)
        self._joined(first)
        answer = km._subagent_vouched(r, g0)
        self.assertIs(answer, False,
                      "_subagent_vouched(r, g0) after a second eviction of r ran while the first eviction's store (g0) was "
                      "paused: %r; keyed on False; True is the out-of-order store, r's record %r where g0 + 1 = %d is owed"
                      % (answer, table.get(r), g0 + 1))
        self.assertEqual(table.get(r), g0 + 1, "r's record is its later eviction's value")
        if watch is not None:
            self.assertIn(("stamps-second", "stamps-first"), watch.queued, "the second eviction waited behind the first")

    def _two_directory_root(self, tag):
        """A second session's transcript and beside it a subagents tree of two directories (the root and workflows/), aged
        and walked into the cross-cycle memo outside any scope, owned by nobody alive: its root as a string."""
        other_t = Path(self.td.name) / tag / (OTHER_SID + ".jsonl")
        other_t.parent.mkdir()
        other_t.write_text("")
        other = km._subagents_dir(other_t)
        (other / "workflows").mkdir(parents=True)
        _age(other)
        self.addCleanup(km._SUBAGENT_TREES.pop, str(other), None)
        got, _st = km._subagent_tree(str(other))
        self.assertEqual(len(got), 2, "the tree walked into the cross-cycle memo: its 2 directories")
        return str(other)

    def _end_to_end(self, race):
        """The out-of-order store through the real functions (the round-2 review's end-to-end shape). A forget on a thread
        with no scope evicts the unowned root: it pops the entry and makes its increment, and with `race` its store is
        paused. This thread's scope then walks the root and holds its pair under the forget's value; the tree is removed
        on disk, and a thread with no scope reads the root: the missing-root pop, a second eviction. Then the forget is
        released. Returns what this thread's next read of the root answers: (directories, served moved, the root on
        disk)."""
        root = self._two_directory_root("e2e")
        table = _PausingTable()
        self._eviction_world(table)
        sc = self._open()
        if race:
            table.arm("store", "stamps-forget", key=root)
        forget = self._run("stamps-forget", lambda: km._subagent_trees_forget([{"path": self.path}]))
        if race:
            self._wait(table.reached, "the forget popped the root, made its increment and reached its store")
        else:
            self._joined(forget)
        dirs, _st = km._subagent_tree(root)
        self.assertEqual(len(dirs), 2, "this thread's scope walked the root again and holds its 2 directories")
        self.assertIn(root, sc["trees"], "the pair is held")
        shutil.rmtree(root)
        popper = self._run("stamps-popper", lambda: km._subagent_tree(root))
        self._wait(popper.ev, "the popping thread queued behind the lock or returned")
        table.go.set()
        self.assertEqual(self._joined(popper), ((), ()), "the pop found nothing at the root")
        self._joined(forget)
        b = self._stats()
        got = km._subagent_tree(root)
        return len(got[0]), self._delta(b)["served"], os.path.exists(root)

    def test_a_removed_trees_pair_is_not_served_after_a_late_store_of_an_earlier_eviction_end_to_end(self):
        """End to end: the forget's store paused, the walk and hold, the removal, the pop, then the forget's late store.
        With no lock the pop's record (g0 + 1) landed first and the forget's late store moved the root's record back to the
        hold's g0, so this thread's next read was served the removed tree's pair: 2 directories and served + 1. Under the
        lock the pop waits for the forget's eviction and its record lands last, so the read drops the hold and finds
        nothing at the root. Keys on (directories, served moved, on disk) == (0, 0, False); the control below runs the
        same sequence with no race. Red under the store taken outside the lock."""
        got = self._end_to_end(race=True)
        self.assertEqual(got, (0, 0, False),
                         "(directories, served moved, the root on disk) on this thread's read of a root it held under the forget's "
                         "value, after the tree was removed and a thread with no scope popped it while the forget's store was "
                         "paused: %r; keyed on (0, 0, False): the pop's eviction outdates the hold and the read finds nothing at "
                         "the root; (2, 1, False) is the removed tree's pair served, the forget's late store having moved the "
                         "root's record back to the hold's value" % (got,))

    def test_control_the_same_sequence_with_no_race_serves_no_pair_of_the_removed_tree(self):
        """The end-to-end case's control: the same forget, walk, removal and pop with the forget run to its end first.
        (0, 0, False) with and without the lock."""
        got = self._end_to_end(race=False)
        self.assertEqual(got, (0, 0, False), "(directories, served moved, the root on disk) with no race: %r; keyed on (0, 0, False)" % (got,))


class DependencyKey(_World):
    """(6) The key a chat build records for a subagents tree the agent-file miss walk looked through is the served read's
    stamp (since 2026-09-21, round 1 of #882's ruling). Two sessions share a project directory (a /clear fork's, the case the sibling scan exists for);
    an agent row of this session names a file that exists nowhere yet; earlier in the cycle a build read the sibling's tree,
    so the scope holds it; then the file lands under the sibling's root in a directory the held listing lacks; then this
    session's chat build resolves the agent, is answered the held listing, finds the file nowhere and shows it missing. The
    tab is cached under the dependencies the build recorded (_chat_build_deps) and rebuilt when the next cycle's signature
    re-stats one of them to a different key (_chat_sig_deps). Before 2026-09-21 the walk recorded the sibling's root under a
    FRESH os.stat taken after the served listing, the post-landing key, equal to every later re-stat, so the tab stayed
    stale until something else moved; and it recorded the root alone, which a landing under a listed child never moves. Now
    every directory of the tree is recorded under the (mtime, size) of the stat the served read was taken with (the shape
    _subagent_meta_map records: _subagent_tree_dep_note), so the key is behind the re-stat and the tab is rebuilt, whether
    the landing moved the root's stamp or a listed child's. The same keys reach a build whose lookup the walk did not run
    (round 2 of #882, group B): the agent-file memo's hit and _awaiting_nest's held launch fold replay the pairs the walk
    noted (_subagent_file_notes_replay), where before they recorded nothing for the sibling's tree; a replayed key that
    disagrees with a fresher key the same build reported for the path is recorded as the disagreement (_chat_build_deps),
    which no re-stat equals; the project directory stays out of every record, the residual two cases here witness, one
    for a build that found the file nowhere and one for a build that found it. An own place holding what the walk
    refuses is noted nothing, so a tab over it is served from its first build on (round 3 of #882, group B), and a
    symlinked subagents/ replaced by a real directory moves no recorded key, the second residual, witnessed. Driven
    through the real _pusher_cycle, with the
    build's record shape (build_session's literal) open around the real _session_awaiting."""

    def _sibling(self, workflows):
        """A second session's transcript beside this one's in the project directory and its subagents tree: the root alone,
        or the root and workflows/, aged; no entry in the walk memo yet. Returns the root."""
        other_t = Path(self.path).parent / (OTHER_SID + ".jsonl")
        other_t.write_text("")
        other = km._subagents_dir(other_t)
        ((other / "workflows") if workflows else other).mkdir(parents=True)
        _age(other)
        self.addCleanup(km._SUBAGENT_TREES.pop, str(other), None)
        self.addCleanup(km._SUBAGENT_META_CACHE.pop, str(other), None)
        self.addCleanup(setattr, km._chat_dep_scope, "deps", None)
        return other

    def _landing_probe(self, other, land_in):
        """One pusher cycle: a build reads the sibling's tree (held); the agent's file lands in a new workflow directory
        created under `land_in` (its parent's stamp moves; the held listing lacks the new directory); this session's build
        resolves the agent with the record open. Returns (the agent id, what the job saw: the served listing and its keys,
        every served directory's fresh key after the landing, the record, the resolution, the landed file)."""
        aid = "a%016x" % 0x7cf0
        self.live_aids.append(aid)
        rec = {}

        def job(now, live_map, **kw):
            dirs, stats = km._subagent_tree(str(other))            # a build earlier in the cycle: the sibling's tree, held
            rec["dirs"] = list(dirs)
            rec["served"] = {sd: (st.st_mtime, st.st_size) for sd, st in zip(dirs, stats)}
            wf = land_in / ("wf_%016x" % 0x7cf0)
            wf.mkdir(parents=True)                               # the landing, after the hold
            self._add_agent(wf, 240, aid)
            rec["fresh"] = {sd: km._chat_stat_key(sd) for sd in dirs}
            km._chat_dep_scope.deps = {"task_outs": [], "postal_any": False}   # build_session's record for this build
            try:
                aw = km._session_awaiting(SID, self.path, True)
                rec["deps"] = km._chat_build_deps(SID, {"events": []})
            finally:
                km._chat_dep_scope.deps = None
            rec["count"] = (aw or {}).get("count")
            rec["found"] = km._SUBAGENT_FILE_CACHE.get((self.path, aid), (None, "unset"))[1]
            rec["file"] = wf / ("agent-%s.jsonl" % aid)
        km._turn_notify_tick = job
        km._pusher_cycle()
        self.assertIn("deps", rec, "the job ran to its end: %r" % (rec,))
        self.assertEqual(rec["count"], A + 1)
        self.assertIsNone(rec["found"], "premise: the build's lookup, answered the held listing, found the file nowhere (the tab "
                                        "shows the agent's file missing): %r" % (rec["found"],))
        return aid, rec

    @staticmethod
    def _keys(rec, sd):
        """(the key the build recorded for `sd`, the served read's key for it, the next signature's re-stat of it)."""
        recorded = dict(rec["deps"]["task_outs"])
        touts = dict(km._chat_sig_deps(SID, rec["deps"])[0])
        return recorded.get(sd, "unrecorded"), rec["served"].get(sd), touts.get(sd, "unrecorded")

    def test_the_key_recorded_for_a_sibling_root_is_the_served_reads_so_a_landing_that_moved_the_root_re_arms_the_tab(self):
        other = self._sibling(workflows=False)                     # the held listing is the root alone
        aid, rec = self._landing_probe(other, other / "workflows")   # workflows/ is created by the landing: the ROOT's stamp moves
        root = str(other)
        self.assertEqual(rec["dirs"], [root], "premise: the held listing is the sibling's root alone")
        self.assertNotEqual(rec["fresh"][root], rec["served"][root], "premise: the landing moved the root's (mtime, size)")
        recorded, served, restat = self._keys(rec, root)
        self.assertEqual(recorded, served,
                         "the key the build recorded for the sibling's root: %r; keyed on the served read's %r, the stamp of the listing "
                         "the lookup was answered with; a fresh stat taken after that listing recorded the post-landing key %r"
                         % (recorded, served, rec["fresh"][root]))
        self.assertNotEqual(restat, recorded,
                         "the next signature's re-stat of the root, %r, against the recorded key %r: keyed on a difference (the taskout "
                         "component moves and the tab is rebuilt); equal means the tab that shows the file missing is served until "
                         "something else moves" % (restat, recorded))
        self.assertEqual(restat, rec["fresh"][root], "the re-stat is the post-landing key")
        # the rebuilt tab: the next cycle's lookup re-checks the miss's stamps, the sibling root's has moved, and the walk finds the file
        nxt = {}
        km._turn_notify_tick = lambda now, live_map, **kw: nxt.setdefault("found", km._subagent_file(self.path, aid))
        km._pusher_cycle()
        self.assertEqual(nxt.get("found"), rec["file"], "the next cycle's lookup finds the file the landing put under the sibling")

    def test_every_directory_of_a_served_sibling_tree_is_recorded_so_a_landing_under_a_listed_child_re_arms_the_tab(self):
        other = self._sibling(workflows=True)                      # the held listing: the root and workflows/
        aid, rec = self._landing_probe(other, other / "workflows")   # wf_<id>/ lands in workflows/: THAT stamp moves, the root's does not
        root, wfdir = str(other), str(other / "workflows")
        self.assertEqual(rec["dirs"], [root, wfdir], "premise: the held listing is the root and workflows/")
        self.assertEqual(rec["fresh"][root], rec["served"][root], "premise: the landing left the root's stamp where it was")
        self.assertNotEqual(rec["fresh"][wfdir], rec["served"][wfdir], "premise: the landing moved workflows/'s stamp")
        recorded, served, restat = self._keys(rec, wfdir)
        self.assertEqual(recorded, served,
                         "the key recorded for the served tree's child workflows/: %r; keyed on the served read's %r, since every directory "
                         "of a tree the lookup looked through is a dependency; a record of the root alone has none for it, and the root's "
                         "key %r cannot move for a landing under a child" % (recorded, served, rec["served"][root]))
        self.assertNotEqual(restat, recorded,
                         "the next signature's re-stat of workflows/, %r, against the recorded key %r: keyed on a difference (the tab is "
                         "rebuilt)" % (restat, recorded))
        r_root, s_root, rs_root = self._keys(rec, root)
        self.assertEqual((r_root, rs_root), (s_root, s_root),
                         "the root is recorded too, under its served key, and its re-stat holds: nothing landed in it")

    def _chat_build(self):
        """A chat build's share of a cycle: build_session's record open around the real _session_awaiting, then the record
        _chat_build_deps takes from it. Returns (what _session_awaiting answered, the record)."""
        km._chat_dep_scope.deps = {"task_outs": [], "postal_any": False}   # build_session's literal for this build
        try:
            aw = km._session_awaiting(SID, self.path, True)
            return aw, km._chat_build_deps(SID, {"events": []})
        finally:
            km._chat_dep_scope.deps = None

    @staticmethod
    def _counting(name, aid, calls):
        """`name` (a kernel function taking (path, agent id, ...)) behind a wrapper that records each call for `aid` and
        what it answered; the real function still runs."""
        real = getattr(km, name)

        def counting(p, a, *args, **kw):
            out = real(p, a, *args, **kw)
            if a == aid:
                calls.append(out)
            return out
        return mock.patch.object(km, name, counting)

    def test_a_lookup_the_agent_file_memo_answers_in_a_later_cycle_replays_the_walks_keys_so_a_landing_under_the_sibling_re_arms_the_tab(self):
        """Round 2 of #882, group B (fresh-1), the memo-hit road. Cycle 1: a chat build's lookup of an agent whose file is
        nowhere walks, records every directory of the sibling's tree under the served read's key (round 1's F) and the memo
        keeps the miss. Cycle 2: a build reads the sibling's tree (held), the agent's file lands under workflows/ after the
        hold, and a second chat build's lookup is answered by the agent-file memo (its stamps re-checked against the scope's
        held ones, equal), so that build shows the file missing too. Keys on that second build's record: every pair the walk
        noted under the sibling's tree, and the absent beside-path, is recorded under the walk's own key, replayed from the
        memo entry, so the next signature's re-stat of workflows/ differs and the tab is rebuilt. Before the replay the hit
        recorded nothing for the sibling's tree ("unrecorded" below) and the tab stayed stale until an unrelated change; a
        replay that re-stats records the post-landing key, equal to every later re-stat (round 1's post-dating defect)."""
        other = self._sibling(workflows=True)                      # the sibling's tree: the root and workflows/
        root, wfdir = str(other), str(other / "workflows")
        aid = "a%016x" % 0x7cf2
        beside = str(self.sub / ("agent-%s.jsonl" % aid))          # the agent's own place, absent
        self.live_aids.append(aid)
        rec = {}

        def walk_job(now, live_map, **kw):
            walks = []
            with self._counting("_subagent_file_walk", aid, walks):
                rec["aw1"], rec["deps1"] = self._chat_build()
            rec["walks1"] = walks
            rec["found1"] = km._SUBAGENT_FILE_CACHE.get((self.path, aid), (None, "unset"))[1]
        km._turn_notify_tick = walk_job
        km._pusher_cycle()
        self.assertIn("deps1", rec, "cycle 1's job ran to its end: %r" % (rec,))
        self.assertEqual(((rec["aw1"] or {}).get("count"), rec["walks1"][:1], rec["found1"]), (A + 1, [None], None),
                         "premise: build 1 saw the A agents and the new row, its lookup walked and missed, and the memo keeps the miss")
        walked = dict(rec["deps1"]["task_outs"])
        paths = {"root": root, "workflows/": wfdir, "beside-path": beside}   # labels in the messages, not the temp paths
        noted = {n: walked.get(p, "unrecorded") for n, p in paths.items()}
        self.assertNotIn("unrecorded", noted.values(),
                         "premise: build 1's walk recorded the sibling's root, workflows/ and the absent beside-path: %r" % (noted,))

        def hit_job(now, live_map, **kw):
            dirs, stats = km._subagent_tree(root)                  # a build earlier in cycle 2: the sibling's tree, held
            rec["served"] = {sd: (st.st_mtime, st.st_size) for sd, st in zip(dirs, stats)}
            wf = other / "workflows" / ("wf_%016x" % 0x7cf2)
            wf.mkdir()                                              # the landing, after the hold: workflows/'s stamp moves
            self._add_agent(wf, 241, aid)
            rec["file"] = wf / ("agent-%s.jsonl" % aid)
            rec["fresh"] = km._chat_stat_key(wfdir)
            walks, asked = [], []
            with self._counting("_subagent_file_walk", aid, walks), self._counting("_subagent_file", aid, asked):
                rec["aw2"], rec["deps2"] = self._chat_build()
            rec["walks2"], rec["asked2"] = walks, asked
        km._turn_notify_tick = hit_job
        km._pusher_cycle()
        self.assertIn("deps2", rec, "cycle 2's job ran to its end: %r" % (rec,))
        self.assertEqual(rec["served"].get(wfdir), noted["workflows/"], "premise: nothing moved between the cycles, so cycle 2's held "
                                                                        "read of workflows/ carries the key the walk recorded")
        self.assertNotEqual(rec["fresh"], noted["workflows/"], "premise: the landing moved workflows/'s (mtime, size)")
        self.assertEqual((rec["walks2"], bool(rec["asked2"]), set(rec["asked2"])), ([], True, {None}),
                         "premise: build 2's lookups were answered by the agent-file memo (no walk) with the memoized miss, so the tab "
                         "shows the file missing: walks %r, answers %r" % (rec["walks2"], rec["asked2"]))
        recorded = dict(rec["deps2"]["task_outs"])
        got = {n: recorded.get(p, "unrecorded") for n, p in paths.items()}
        self.assertEqual(got, noted,
                         "the keys build 2 recorded for the sibling's root, workflows/ and the absent beside-path: %r; keyed on equality "
                         "with the pairs the walk noted, %r, replayed from the memo entry by the hit; \"unrecorded\" is a hit that records "
                         "nothing for the trees its walk read (the tab never re-arms on the landing), and workflows/ at %r, the "
                         "post-landing key, is a replay that re-stat'd" % (got, noted, rec["fresh"]))
        restat = dict(km._chat_sig_deps(SID, rec["deps2"])[0]).get(wfdir, "unrecorded")
        self.assertNotEqual(restat, recorded.get(wfdir, "unrecorded"),
                            "the next signature's re-stat of workflows/, %r, against build 2's recorded key: keyed on a difference, the "
                            "taskout component moves and the tab is rebuilt" % (restat,))
        nxt = {}
        km._turn_notify_tick = lambda now, live_map, **kw: nxt.setdefault("found", km._subagent_file(self.path, aid))
        km._pusher_cycle()
        self.assertEqual(nxt.get("found"), rec["file"], "the rebuilt tab's lookup: the memo's stamps moved, the walk finds the file")

    def test_a_lookup_the_held_launch_fold_answers_after_a_non_chat_readers_walk_replays_the_walks_keys_so_a_landing_under_the_sibling_re_arms_the_tab(self):
        """Round 2 of #882, group B (fresh-1), the held-fold road, in one cycle. A reader with no chat record open (the feed's
        build) resolves an agent whose file is nowhere: its lookup walks, reads the sibling's tree (held), and _awaiting_nest
        holds the agent's launch fold for the cycle. The agent's file then lands under the sibling's root in workflows/, a
        directory the held listing lacks, and the chat build's _session_awaiting consults the agent's launches, which the held
        fold answers without calling _subagent_file (the only lookup a chat build makes for a Workflow agent with no Agent
        tool event). Keys on the chat build's record: the sibling's root under the key the walk noted, the served read's,
        replayed from the fold entry, so the next signature's re-stat differs and the tab is rebuilt. Before the replay the
        held fold recorded nothing for the sibling's tree ("unrecorded" below); a replay that re-stats records the
        post-landing key."""
        other = self._sibling(workflows=False)                     # the held listing will be the root alone
        root = str(other)
        aid = "a%016x" % 0x7cf3
        self.live_aids.append(aid)
        rec = {}

        def job(now, live_map, **kw):
            walks = []
            with self._counting("_subagent_file_walk", aid, walks):
                rec["aw0"] = km._session_awaiting(SID, self.path, True)   # a non-chat reader: no record open on this thread
            rec["walks0"] = walks
            sc = _scope()
            rec["held"] = sc is not None and (self.path, aid) in sc["launches"]
            dirs, stats = km._subagent_tree(root)                  # the pair the walk was answered, held: its keys
            rec["dirs"] = list(dirs)
            rec["served"] = {sd: (st.st_mtime, st.st_size) for sd, st in zip(dirs, stats)}
            wf = other / "workflows" / ("wf_%016x" % 0x7cf3)
            wf.mkdir(parents=True)                                  # the landing: workflows/ created, the root's stamp moves
            self._add_agent(wf, 242, aid)
            rec["fresh"] = km._chat_stat_key(root)
            asked = []
            with self._counting("_subagent_file", aid, asked):
                rec["aw"], rec["deps"] = self._chat_build()
            rec["asked"] = asked
        km._turn_notify_tick = job
        km._pusher_cycle()
        self.assertIn("deps", rec, "the job ran to its end: %r" % (rec,))
        self.assertEqual(((rec["aw0"] or {}).get("count"), rec["walks0"][:1], rec["held"]), (A + 1, [None], True),
                         "premise: the non-chat reader saw the A agents and the new row, its lookup walked and missed, and the agent's "
                         "launch fold is held for the cycle")
        self.assertEqual(rec["dirs"], [root], "premise: the held listing is the sibling's root alone")
        self.assertNotEqual(rec["fresh"], rec["served"][root], "premise: the landing moved the root's (mtime, size)")
        self.assertEqual(((rec["aw"] or {}).get("count"), rec["asked"]), (A + 1, []),
                         "premise: the chat build saw the A agents and the new row and never called _subagent_file for the agent: its "
                         "launches were answered by the held fold: %r" % (rec["asked"],))
        recorded = dict(rec["deps"]["task_outs"]).get(root, "unrecorded")
        self.assertEqual(recorded, rec["served"][root],
                         "the key the chat build recorded for the sibling's root: %r; keyed on the served read's %r, the key the walk "
                         "noted, replayed from the held fold's entry; \"unrecorded\" is a held fold that records nothing for the trees "
                         "its walk read, and %r, the post-landing key, is a replay that re-stat'd" % (recorded, rec["served"][root], rec["fresh"]))
        restat = dict(km._chat_sig_deps(SID, rec["deps"])[0]).get(root, "unrecorded")
        self.assertNotEqual(restat, recorded,
                            "the next signature's re-stat of the root, %r, against the recorded key %r: keyed on a difference, the tab "
                            "is rebuilt" % (restat, recorded))

    def test_a_held_folds_replayed_key_behind_a_fresh_walks_key_for_the_same_directory_re_arms_the_tab(self):
        """The held-fold road when a fresh walk in the same build reports the directory first (the pass applying round 2
        of #882's rulings found it; the case above has the fold report first). One cycle: a reader with no chat record open
        holds the launch fold of a Workflow agent K2 whose file is nowhere, its walk having read the sibling's tree, and
        looks up an agent K1 whose file lies at the sibling's root; the sibling's root is then evicted (owned by no alive
        session: the jobs pass's forget or the feed build's belt), and K2's file lands under the sibling's workflows/. The
        chat build then looks K1 up first (the Agent head: _stamp_agents runs before _session_awaiting in build_session):
        K1's memo re-check sees workflows/ moved, its walk reads the tree again and reports workflows/ under the key after
        the landing. The awaiting box's owner lookups then consult K2's launches, which the held fold answers from before
        the landing, replaying the walk's older key for workflows/. Keyed on the property: the build answered K2 with no
        file while K2's file exists, so its record for workflows/ must differ from the next signature's re-stat (the tab
        is rebuilt). RED before _chat_build_deps recorded a disagreement, when it kept the first key, the walk's, equal
        to every later re-stat, and dropped the fold's; red before group B too, when the held fold replayed nothing. Now
        the path reported under two keys is recorded under a key no re-stat equals."""
        other = self._sibling(workflows=True)                      # the sibling's tree: the root and workflows/
        root, wfdir = str(other), str(other / "workflows")
        k1, k2 = "a%016x" % 0x7cf6, "a%016x" % 0x7cf7
        k1_file = other / ("agent-%s.jsonl" % k1)                  # K1: its file at the sibling's root, the Agent head's lookup
        k1_file.write_text("")
        _age(other)
        self.live_aids.append(k2)                                  # K2: in the live row, its file nowhere yet
        for aid in (k1, k2):
            self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, (self.path, aid), None)
        rec = {}

        def job(now, live_map, **kw):
            rec["aw0"] = km._session_awaiting(SID, self.path, True)   # a reader with no record open: K2's fold held
            rec["held"] = (self.path, k2) in _scope()["launches"]
            rec["k1_0"] = km._subagent_file(self.path, k1)
            km._subagent_trees_forget([{"path": self.path}])        # the sibling's root, owned by no alive session, evicted
            rec["evicted"] = root in km._SUBAGENT_ROOT_EVICTED
            wf = other / "workflows" / ("wf_%016x" % 0x7cf7)
            wf.mkdir()                                              # K2's file lands: workflows/'s stamp moves
            self._add_agent(wf, 244, k2)
            rec["file"] = wf / ("agent-%s.jsonl" % k2)
            rec["fresh"] = km._chat_stat_key(wfdir)
            km._chat_dep_scope.deps = {"task_outs": [], "postal_any": False}   # build_session's record for the chat build
            try:
                asked = []
                rec["k1"] = km._subagent_file(self.path, k1)           # the Agent head's lookup first
                with self._counting("_subagent_file", k2, asked):
                    rec["aw"] = km._session_awaiting(SID, self.path, True)
                rec["asked"] = asked
                rec["reports"] = [k for p, k in km._chat_dep_scope.deps["task_outs"] if p == wfdir]
                rec["deps"] = km._chat_build_deps(SID, {"events": []})
            finally:
                km._chat_dep_scope.deps = None
        km._turn_notify_tick = job
        km._pusher_cycle()
        self.assertIn("deps", rec, "the job ran to its end: %r" % (rec,))
        self.assertEqual(((rec["aw0"] or {}).get("count"), rec["held"], rec["k1_0"], rec["evicted"]),
                         (A + 1, True, k1_file, True),
                         "premise: the first reader saw the A agents and K2, held K2's fold, found K1 at the sibling's root, and the "
                         "sibling's eviction is recorded")
        self.assertEqual((rec["k1"], (rec["aw"] or {}).get("count"), rec["asked"]), (k1_file, A + 1, []),
                         "premise: the chat build found K1 and saw K2, whose launches the held fold answered without calling "
                         "_subagent_file: %r" % (rec["asked"],))
        self.assertTrue(rec["file"].exists(), "premise: K2's file exists under the sibling's workflows/")
        self.assertEqual(rec["reports"][:1], [rec["fresh"]],
                         "premise: the build's first report of workflows/ is K1's walk, under the key after the landing: %r" % (rec["reports"],))
        recorded = dict(rec["deps"]["task_outs"]).get(wfdir, "unrecorded")
        restat = dict(km._chat_sig_deps(SID, rec["deps"])[0]).get(wfdir, "unrecorded")
        self.assertNotEqual(recorded, restat,
                            "the chat build answered K2 from the fold held before the landing (no file) while K2's file exists, so its "
                            "record for workflows/ must differ from the next signature's re-stat and the tab be rebuilt; recorded %r, "
                            "re-stat %r: equal, the tab keeps showing K2's file missing (the build's reports of workflows/: %r; a "
                            "record that keeps the first key drops the fold's older one)" % (recorded, restat, rec["reports"]))
        self.assertEqual(len(set(rec["reports"])), 2,
                         "and the fold replayed the walk's older key for workflows/ behind K1's: %r" % (rec["reports"],))
        nxt = {}
        km._turn_notify_tick = lambda now, live_map, **kw: nxt.setdefault("found", km._subagent_file(self.path, k2))
        km._pusher_cycle()
        self.assertEqual(nxt.get("found"), rec["file"], "the rebuilt tab's lookup of K2: the memo's stamps moved, the walk finds the file")

    def test_a_path_one_build_reported_under_two_keys_is_recorded_under_a_key_no_re_stat_equals_in_either_order(self):
        """_chat_build_deps' rule for a path reported more than once (the case above drives it through the real readers):
        under two different keys, in either order, the record's one entry for the path is a key the next signature's
        re-stat never equals, so the tab is rebuilt; reported twice under one key, the entry is that key and equals the
        re-stat, so a consistent build is not rebuilt for it. RED, in the order current key first and older key second,
        before the rule, when the record kept the first key; the other order and the one-key control were green then."""
        p = str(self.sub)
        now_key = km._chat_stat_key(p)
        older = (now_key[0] - 1.0, now_key[1])                     # the path's key before a change: an older read's
        for what, reports in (("the current key first", [(p, now_key), (p, older)]),
                              ("the older key first", [(p, older), (p, now_key)])):
            km._chat_dep_scope.deps = {"task_outs": list(reports), "postal_any": False}
            try:
                rec = km._chat_build_deps(SID, {"events": []})
            finally:
                km._chat_dep_scope.deps = None
            restat = km._chat_sig_deps(SID, rec)[0]
            self.assertEqual([q for q, _k in rec["task_outs"]], [p], "one entry for the path (%s)" % what)
            self.assertNotEqual(tuple(rec["task_outs"]), restat,
                                "a path reported under two keys, %s: the record %r equals the next re-stat %r, so the tab is not "
                                "rebuilt while the payload embeds a read under the other key" % (what, rec["task_outs"], restat))
        km._chat_dep_scope.deps = {"task_outs": [(p, now_key), (p, now_key)], "postal_any": False}
        try:
            rec = km._chat_build_deps(SID, {"events": []})
        finally:
            km._chat_dep_scope.deps = None
        self.assertEqual((rec["task_outs"], km._chat_sig_deps(SID, rec)[0]), ([(p, now_key)], ((p, now_key),)),
                         "control: a path reported twice under one key is recorded under it, equal to the re-stat (no rebuild)")

    def test_a_sibling_directory_appearing_after_a_build_moves_no_key_that_build_recorded_on_any_road(self):
        """The residual group B leaves (round 2 of #882), witnessed. The project directory the walk lists is stamped for the
        agent-file memo alone and is no build's dependency, whether the build's lookup walked or was answered by the memo or
        by the held launch fold, so a sibling session directory that appears in it after a build moves no key that build
        recorded: an agent whose file was nowhere when the build looked, landing under the NEW sibling's tree, leaves the
        tab showing it missing until another recorded key moves. Three chat builds in three cycles, one per road (the first
        walks; the second is answered by the agent-file memo; in the third a reader with no record open looks first, a memo
        hit that holds the launch fold, and the chat build is answered by that fold), then a sibling session's directory
        appears with the agent's file under its tree. Keys on each record's taskout component re-evaluated now equalling
        what the build recorded (the tab is not rebuilt), the project directory in no record, and the lookup itself finding
        the file (the memo's project-directory stamp moved). Green by design: a change that records the project directory,
        or a new sibling's tree, turns it red, and the residual's text in _subagent_file's docstring goes with it."""
        aid = "a%016x" % 0x7cf4
        self.live_aids.append(aid)
        rec = {}

        def build(road):
            def job(now, live_map, **kw):
                walks, asked = [], []
                if road == "fold":
                    km._session_awaiting(SID, self.path, True)   # a reader with no record open: its lookup holds the fold
                with self._counting("_subagent_file_walk", aid, walks), self._counting("_subagent_file", aid, asked):
                    rec[road] = self._chat_build()
                rec[road + "-calls"] = (len(walks), len(asked))
            return job
        for road in ("walk", "memo", "fold"):
            km._turn_notify_tick = build(road)
            km._pusher_cycle()
        got = tuple((road, rec.get(road + "-calls", ("unset",))[0], rec.get(road + "-calls", ("unset",))[-1] > 0)
                    for road in ("walk", "memo", "fold"))
        self.assertEqual(got, (("walk", 1, True), ("memo", 0, True), ("fold", 0, False)),
                         "premise, (road, walks, _subagent_file called) per chat build: the first walked, the second was answered by "
                         "the agent-file memo, the third never called _subagent_file (the held fold answered): %r" % (got,))
        self.assertIsNone(km._SUBAGENT_FILE_CACHE.get((self.path, aid), (None, "unset"))[1], "premise: the memo keeps the miss")
        other_t = Path(self.path).parent / (OTHER_SID + ".jsonl")
        other_t.write_text("")                                      # a sibling session appears after the three builds
        other = km._subagents_dir(other_t)
        self.addCleanup(km._SUBAGENT_TREES.pop, str(other), None)
        self.addCleanup(km._SUBAGENT_META_CACHE.pop, str(other), None)
        wf = other / "workflows" / ("wf_%016x" % 0x7cf4)
        wf.mkdir(parents=True)
        self._add_agent(wf, 243, aid)
        proj = str(Path(self.path).parent)
        beside = str(self.sub / ("agent-%s.jsonl" % aid))
        for road in ("walk", "memo", "fold"):
            deps = rec[road][1]
            recorded = dict(deps["task_outs"])
            self.assertIn(beside, recorded, "premise: the %s build recorded the walk's keys (the absent beside-path among them)" % road)
            self.assertNotIn(proj, recorded, "the project directory is no build's dependency (the %s build)" % road)
            now_keys = dict(km._chat_sig_deps(SID, deps)[0])
            moved = sorted(os.path.relpath(p, proj) for p in recorded if now_keys.get(p) != recorded[p])
            self.assertEqual(moved, [],
                             "keys the %s build recorded that the new sibling's appearance moved: %r; keyed on none, the residual: a "
                             "sibling session directory appearing after a build is outside its record, so the tab that shows the file "
                             "missing is not rebuilt for it (stated in _subagent_file's docstring)" % (road, moved))
        self.assertEqual(km._subagent_file(self.path, aid), wf / ("agent-%s.jsonl" % aid),
                         "the lookup itself recovers: the memo's stamp of the project directory moved, so it walks and finds the file")

    def test_a_sibling_directory_appearing_after_a_build_that_found_the_file_is_recorded_by_no_later_build_on_any_road(self):
        """The same residual where round 2 of #882's ruling on group B names it: a new sibling session directory that
        appears after a build that already FOUND the agent's file (the case above is its twin for a file found nowhere).
        The file lies under an existing sibling's tree (a /clear fork's), so the walk that found it listed the project
        directory and stamped it for the agent-file memo alone, and the memo holds the found file. Then a second sibling
        session's directory appears with a subagents tree of its own, sorted after the first, so a walk that finds the file
        under the first never reaches it. Keys on every key the found build recorded re-evaluating equal after the
        appearance (its tab is not rebuilt for it), and on three later chat builds in three cycles, one per road (the
        lookup walks again, the memo's stamp of the project directory having moved; the agent-file memo answers; a reader
        with no record open looks first and the held launch fold answers): each is answered the same file, and each
        records no path under the new sibling's directory and not the project directory. Green by design, and not a
        claim that the state is wanted: a kernel that records the project
        directory, or the new sibling's tree for a lookup that found the file elsewhere, closes the residual and turns
        this case red."""
        proj = Path(self.path).parent
        aid = "a%016x" % 0x7cf8
        self.live_aids.append(aid)
        other = self._sibling(workflows=True)                      # the first sibling's tree: the root and workflows/
        wf = other / "workflows" / ("wf_%016x" % 0x7cf8)
        wf.mkdir()
        self._add_agent(wf, 245, aid)                              # the agent's file, under the first sibling's tree
        found = wf / ("agent-%s.jsonl" % aid)
        _age(other)
        t = time.time_ns() - AGED_NS
        os.utime(str(proj), ns=(t, t))                             # the project directory back-dated too, so the new sibling's
        rec = {}                                                   #  appearance moves its stamp whatever the clock's grain

        def build(road):
            def job(now, live_map, **kw):
                walks, asked = [], []
                if road == "fold":
                    first = []
                    with self._counting("_subagent_file", aid, first):
                        km._session_awaiting(SID, self.path, True)   # a reader with no record open: its lookup holds the fold
                    rec["fold-first"] = first
                    rec["fold-held"] = (self.path, aid) in _scope()["launches"]
                with self._counting("_subagent_file_walk", aid, walks), self._counting("_subagent_file", aid, asked):
                    rec[road] = self._chat_build()
                rec[road + "-calls"] = (walks, asked)
            return job
        km._turn_notify_tick = build("found")
        km._pusher_cycle()
        walks, asked = rec.get("found-calls", ([], []))
        entry = km._SUBAGENT_FILE_CACHE.get((self.path, aid), ((), "unset"))
        self.assertEqual((len(walks), set(walks + asked), entry[1]), (1, {found}, found),
                         "premise: the found build's lookup walked once and found the file under the first sibling's tree, and the "
                         "memo holds it: walks %r, answers %r, memo %r" % (walks, asked, entry[1]))
        self.assertIn(str(proj), [d for d, _m in entry[0]], "premise: the memo is stamped on the project directory the walk listed")
        beside = str(self.sub / ("agent-%s.jsonl" % aid))
        walked = [beside, str(other), str(other / "workflows"), str(wf)]   # the absent beside-path and the sibling tree's directories
        recorded0 = dict(rec["found"][1]["task_outs"])
        self.assertEqual([p for p in walked if p not in recorded0], [],
                         "premise: the found build recorded the walk's keys, the absent beside-path and every directory of the sibling's tree")
        new_sid = "11111111-2222-3333-4444-7c7c7c7c7c7e"          # sorted after the first sibling's
        (proj / (new_sid + ".jsonl")).write_text("")
        new = km._subagents_dir(proj / (new_sid + ".jsonl"))
        (new / "workflows").mkdir(parents=True)                    # the new sibling session's directory and its tree appear
        self.addCleanup(km._SUBAGENT_TREES.pop, str(new), None)
        self.addCleanup(km._SUBAGENT_META_CACHE.pop, str(new), None)
        new_dir = str(new.parent)
        self.assertLess(str(other.parent), new_dir, "premise: the new sibling's directory sorts after the one holding the file")
        now0 = dict(km._chat_sig_deps(SID, rec["found"][1])[0])
        moved0 = sorted(os.path.relpath(p, str(proj)) for p in recorded0 if now0.get(p) != recorded0[p])
        self.assertEqual(moved0, [],
                         "keys the found build recorded that the new sibling's appearance moved: %r; keyed on none, the residual: the "
                         "project directory is no build's dependency, so a sibling session directory appearing after a build that "
                         "found the file does not rebuild its tab" % (moved0,))
        for road in ("walk", "memo", "fold"):
            km._turn_notify_tick = build(road)
            km._pusher_cycle()
        got = tuple((road, len(rec.get(road + "-calls", ([], []))[0]), bool(rec.get(road + "-calls", ([], []))[1]))
                    for road in ("walk", "memo", "fold"))
        self.assertEqual(got, (("walk", 1, True), ("memo", 0, True), ("fold", 0, False)),
                         "premise, (road, walks, _subagent_file called) per later chat build: the first walked again (the memo's stamp "
                         "of the project directory moved), the second was answered by the agent-file memo, the third never called "
                         "_subagent_file (the held fold answered): %r" % (got,))
        answers = {road: set(sum(rec[road + "-calls"], [])) for road in ("walk", "memo")}
        answers["fold"] = set(rec.get("fold-first", []))
        self.assertEqual((answers, rec.get("fold-held")), ({"walk": {found}, "memo": {found}, "fold": {found}}, True),
                         "premise: the walk and the memo answered the file where it was found, and the fold the chat build was served "
                         "is held from a lookup that answered it: %r" % (answers,))
        for road in ("walk", "memo", "fold"):
            recorded = dict(rec[road][1]["task_outs"])
            self.assertEqual([p for p in walked if p not in recorded], [],
                             "premise: the %s build recorded the walk's keys (the absent beside-path, the sibling tree's directories)" % road)
            self.assertNotIn(str(proj), recorded, "the project directory is no build's dependency (the %s build)" % road)
            under = sorted(os.path.relpath(p, str(proj)) for p in recorded if p == new_dir or p.startswith(new_dir + os.sep))
            self.assertEqual(under, [],
                             "paths under the new sibling's directory the %s build recorded: %r; keyed on none, the residual: a sibling "
                             "session directory that appears after a build that found the file, sorted after the tree holding it, is "
                             "recorded by no later build while the file stays where it was found" % (road, under))

    def test_the_chat_signature_re_stats_every_directory_the_walk_recorded_so_a_change_in_any_sibling_directory_rebuilds_the_tab(self):
        """The dependency-note signature term of the cost home (_subagent_tree_memo_report's docstring; round 2 of #882,
        regression-2), as group B leaves the record: a chat build whose lookup of an agent whose file is nowhere walks S
        sibling trees of D directories each, beside K session directories with no subagents/, records one key per path, and
        each later pusher cycle's signature of that cached tab (_chat_sig_deps, inside _chat_build_sig) re-stats every one,
        counted in memos.chatSig stats: D for the own tree (the sidecar map's note and the walk's, one key per directory),
        1 for the absent beside-path, S x D for the sibling trees and K for the absent sibling places, noted None. Keyed on
        the stats a signature scope counts over the record's evaluation, D + 1 + S x D + K; a kernel that records one key per
        sibling root (the base's form) records and re-stats D + 1 + S + K, and a landing under a sibling's workflow directory
        moves no key it recorded. The intended half, pinned beside the count: a directory created under any sibling
        directory moves that directory's re-stat against the recorded key, so the tab is rebuilt."""
        S, K = 2, 1
        proj = Path(self.path).parent
        sib_dirs = []
        for i in range(S):
            sid = "11111111-2222-3333-4444-7c7c7c7c%04x" % (0xc000 + i)
            (proj / (sid + ".jsonl")).write_text("")
            root = proj / sid / "subagents"
            (root / "workflows").mkdir(parents=True)
            dirs = [str(root), str(root / "workflows")]
            for j in range(D - 2):
                wf = root / "workflows" / ("wf_%016x" % (0x7c00 + j))
                wf.mkdir()
                dirs.append(str(wf))
            _age(root)
            self.addCleanup(km._SUBAGENT_TREES.pop, str(root), None)
            self.addCleanup(km._SUBAGENT_META_CACHE.pop, str(root), None)
            sib_dirs.append(dirs)
        for i in range(K):
            (proj / ("11111111-2222-3333-4444-7c7c7c7c%04x" % (0xc100 + i)) / "tool-results").mkdir(parents=True)
        aid = "a%016x" % 0x7cf5
        self.live_aids.append(aid)
        self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, (self.path, aid), None)
        self.addCleanup(setattr, km._chat_dep_scope, "deps", None)
        rec = {}

        def job(now, live_map, **kw):
            walks = []
            with self._counting("_subagent_file_walk", aid, walks):
                rec["aw"], rec["deps"] = self._chat_build()
            rec["walks"] = walks
        km._turn_notify_tick = job
        km._pusher_cycle()
        self.assertIn("deps", rec, "the job ran to its end: %r" % (rec,))
        self.assertEqual(((rec["aw"] or {}).get("count"), rec["walks"][:1]), (A + 1, [None]),
                         "premise: the chat build saw the A agents and the new row, and its lookup walked and missed")
        deps = rec["deps"]
        recorded = dict(deps["task_outs"])
        b = km._chat_sig_stats_report()["stats"]
        with km._chat_sig_scope():
            touts = km._chat_sig_deps(SID, deps)[0]
        n = km._chat_sig_stats_report()["stats"] - b
        want = D + 1 + S * D + K
        self.assertEqual((n, len(recorded)), (want, want),
                         "memos.chatSig stats over one evaluation of the tab's record, and the paths it recorded: %r; keyed on D + 1 + "
                         "S x D + K = %d + 1 + %d x %d + %d = %d each, one re-stat per recorded path every cycle; one key per sibling "
                         "root, the base's form, is D + 1 + S + K = %d" % ((n, len(recorded)), D, S, D, K, want, D + 1 + S + K))
        for dirs in sib_dirs:
            self.assertEqual([p for p in dirs if p not in recorded], [], "every directory of each sibling tree is among them")
        self.assertEqual(touts, tuple(deps["task_outs"]), "premise: nothing moved since the build, so the re-stat equals the record")
        wf = sib_dirs[-1][-1]
        os.mkdir(os.path.join(wf, "late"))                    # a directory created under a sibling's workflow directory
        moved = [os.path.relpath(p, str(proj)) for p, key in km._chat_sig_deps(SID, deps)[0] if recorded.get(p) != key]
        self.assertEqual(moved, [os.path.relpath(wf, str(proj))],
                         "the recorded keys the creation moved: %r; keyed on the sibling directory it landed in, whose re-stat now "
                         "differs, so the tab is rebuilt (a record of the sibling root alone moves nothing here)" % (moved,))

    def _agent_head_build(self, aid):
        """A chat build's share of a cycle for a transcript whose Agent tool event names `aid`: build_session's record open
        around the real Agent head (_stamp_agents, one foreground Agent event, which looks the agent's file up whether or
        not a sidecar names it) and then the real _session_awaiting, in build_session's order. Returns the record."""
        km._chat_dep_scope.deps = {"task_outs": [], "postal_any": False}   # build_session's literal for this build
        try:
            km._stamp_agents({"toolu_stamps_b": {"name": "Agent", "agentId": aid}}, self.path, None, {})
            km._session_awaiting(SID, self.path, True)
            return km._chat_build_deps(SID, {"events": []})
        finally:
            km._chat_dep_scope.deps = None

    def _tab_cycles(self, tab, n):
        """`n` pusher cycles of one cached chat tab under the chat-build cache's rule (_chat_build_sig: a tab is served
        while its signature holds): each cycle's job evaluates the three dependency components over the tab's latest
        record (_chat_sig_deps) and rebuilds the tab, one call of tab["build"], when they differ from what that build
        embedded (the record's at_build); a tab with no record builds at once. `tab` carries across calls: "builds", each
        build's record in order; "evals", per cycle that had a record, (that record's index, its taskout component then);
        "rebuilt", per cycle, True when the evaluation rebuilt the tab, False when it served it, None for a cold build."""
        for _ in range(n):
            ran = len(tab["rebuilt"])

            def job(now, live_map, **kw):
                deps = tab["builds"][-1] if tab["builds"] else None
                if deps is not None:
                    comps = km._chat_sig_deps(SID, deps)
                    tab["evals"].append((len(tab["builds"]) - 1, comps[0]))
                    if comps == deps["at_build"]:
                        tab["rebuilt"].append(False)
                        return
                tab["rebuilt"].append(None if deps is None else True)
                tab["builds"].append(tab["build"]())
            km._turn_notify_tick = job
            km._pusher_cycle()
            self.assertEqual(len(tab["rebuilt"]), ran + 1, "the cycle's job ran to its end: %r" % (tab["rebuilt"],))

    def _refused_place(self, shape):
        """Group B's world (round 3 of #882): an agent, named by an Agent tool event and in the live row, whose own place
        (subagents/agent-<id>.jsonl) holds what the walk refuses, the link's target holding the agent's file outside the
        project directory, so the walk finds it nowhere and the tab shows it missing. "file": the place a symlink to that
        file, in the real subagents tree; "subagents": subagents/ itself a symlink to a directory holding the file, which
        replaces the tree the setUp agents' files were in, the live row naming this agent alone; "absent", the control:
        nothing at the place. The link's target is aged. Returns (the agent id, its own place, the target's copy of its
        file or None, the tab: _tab_cycles' carrier, its build the Agent head's, _agent_head_build)."""
        aid = "a%016x" % 0x7cf9
        name = "agent-%s.jsonl" % aid
        elsewhere = Path(self.td.name) / "elsewhere"
        elsewhere.mkdir()
        ap = self.sub / name
        target = None
        if shape == "file":
            target = elsewhere / name
            target.write_text("")
            os.symlink(str(target), str(ap))
            _age(self.sub)
            self.live_aids.append(aid)
            self.assertTrue(os.path.islink(ap) and os.path.isfile(ap), "premise: the own place is a symlink to the agent's file")
        elif shape == "subagents":
            shutil.rmtree(str(self.sub))
            tdir = elsewhere / "subagents"
            tdir.mkdir()
            target = tdir / name
            target.write_text("")
            _age(tdir)
            os.symlink(str(tdir), str(self.sub))
            self._forget_memos()
            self.live_aids[:] = [aid]
            self.assertTrue(os.path.islink(self.sub) and os.path.isfile(ap),
                            "premise: subagents/ is a symlink to a directory holding the agent's file")
        else:
            self.live_aids.append(aid)
            self.assertFalse(os.path.lexists(ap), "premise: nothing at the own place")
        self.addCleanup(km._SUBAGENT_FILE_CACHE.pop, (self.path, aid), None)
        self.addCleanup(setattr, km._chat_dep_scope, "deps", None)
        tab = {"builds": [], "evals": [], "rebuilt": [], "build": lambda: self._agent_head_build(aid)}
        return aid, ap, target, tab

    def _walks_then_three_cycles(self, shape):
        """The walk's build (the tab's cold build: the agent's lookup walks and finds the file nowhere), then three pusher
        cycles of the tab (_tab_cycles). Returns _refused_place's four."""
        aid, ap, target, tab = self._refused_place(shape)
        walks = []
        with self._counting("_subagent_file_walk", aid, walks):
            self._tab_cycles(tab, 1)
        entry = km._SUBAGENT_FILE_CACHE.get((self.path, aid), ((), "unset"))
        self.assertEqual((tab["rebuilt"], walks, entry[1]), ([None], [None], None),
                         "premise: the walk's build was the tab's cold build, its lookup walked once and found the file nowhere, and "
                         "the memo keeps the miss: %r" % ((tab["rebuilt"], walks, entry[1]),))
        self._tab_cycles(tab, 3)
        return aid, ap, target, tab

    def _assert_each_build_equals_its_re_stat(self, tab, what):
        """Every build's whole record equals the next cycle's evaluation of it (its taskout component, re-stat'd)."""
        firsts = {}
        for i, touts in tab["evals"]:
            firsts.setdefault(i, touts)
        for i, deps in enumerate(tab["builds"]):
            self.assertIn(i, firsts, "premise: build %d was evaluated by a later cycle (%s)" % (i, what))
            self.assertEqual(firsts[i], tuple(deps["task_outs"]),
                             "build %d's record against the next signature's re-stat of it (%s): equal means the tab is served, "
                             "a difference rebuilds it" % (i, what))

    def _assert_refused_place_settles(self, shape):
        """Group B's pin (round 3 of #882, correctness-2), for `shape` (_refused_place). Keys on the rebuilds over the three
        cycles after the walk's build: 0, since the walk notes nothing for a place holding what it refuses, so every build's
        record equals its re-stat. Then a write to the link's target and one more cycle: 0 rebuilds, the record again equal
        to its re-stat. Last, the own place in no build's record, asserted after the write so that the rejected form below
        reds at the write. RED before the fix, and before round 2 of #882's replay too, differently: where the walk noted
        (place, None) unconditionally and every build replayed it (round 2's group B), the re-stat, which follows the link
        to the file, differed every cycle and the tab was rebuilt every cycle (3); before that replay only the walk's build
        recorded the note, a later build answered by the memo recorded nothing for the place, and the tab settled after one
        rebuild (1), also red here, on the walk's build, because the fix settles one cycle sooner than that head did. The
        write step reds the other form the ruling rejected, noting the place under a key taken through the link: its steady
        state holds, but a write to the target moves that key while no stamp the memo checks moves, so every build replays
        the stale key and the tab is rebuilt every cycle."""
        aid, ap, target, tab = self._walks_then_three_cycles(shape)
        rebuilds = tab["rebuilt"][1:].count(True)
        self.assertEqual(rebuilds, 0,
                         "rebuilds of the tab over the three cycles after the walk's build (%s): %d; keyed on 0, the place noting nothing "
                         "(the record equals its re-stat); a note (place, None) replayed by every build rebuilds it every cycle (3), and "
                         "one recorded by the walk's build alone rebuilds it once (1): %r" % (shape, rebuilds, tab["rebuilt"]))
        self._assert_each_build_equals_its_re_stat(tab, shape)
        before = km._chat_stat_key(str(ap))
        with open(str(target), "a") as fh:
            fh.write("\n")                                     # a write to the link's target: its key moves, no directory's does
        self.assertNotEqual(km._chat_stat_key(str(ap)), before, "premise: the write moved the key a re-stat of the place reads through the link")
        self._tab_cycles(tab, 1)
        self.assertEqual(tab["rebuilt"][-1], False,
                         "the cycle after a write to the link's target (%s): rebuilt %r; keyed on the tab served (False); a note of the "
                         "place under a key taken through the link is replayed stale by every build after the write, and the tab is "
                         "rebuilt every cycle" % (shape, tab["rebuilt"][-1]))
        self.assertEqual(tab["evals"][-1], (len(tab["builds"]) - 1, tuple(tab["builds"][-1]["task_outs"])),
                         "the latest record against its re-stat after the write to the target (%s)" % shape)
        noted = [i for i, deps in enumerate(tab["builds"]) if str(ap) in dict(deps["task_outs"])]
        self.assertEqual(noted, [], "builds whose record holds the own place, which holds what the walk refuses (%s): %r" % (shape, noted))

    def test_a_symlinked_agent_file_notes_nothing_for_its_place_so_the_tab_is_never_rebuilt_even_after_a_write_to_the_target(self):
        """Group B's pin for a symlinked agent file (_assert_refused_place_settles)."""
        self._assert_refused_place_settles("file")

    def test_a_symlinked_subagents_directory_holding_the_file_notes_nothing_for_the_place_so_the_tab_is_never_rebuilt_even_after_a_write_to_the_target(self):
        """Group B's pin for a symlinked subagents/ whose target holds the agent's file (_assert_refused_place_settles)."""
        self._assert_refused_place_settles("subagents")

    def test_control_an_absent_own_place_is_recorded_none_equal_to_its_re_stat_and_the_tab_is_never_rebuilt(self):
        """Group B's control (round 3 of #882), green at every head by design: nothing at the own place, so the walk notes
        (place, None), every build records it, and its re-stat answers None too, so the tab is served with no rebuild over
        the three cycles after the walk's build. A kernel that dropped the note for an absent place fails the record
        assertion here (the file appearing there would then move no recorded key)."""
        aid, ap, _target, tab = self._walks_then_three_cycles("absent")
        self.assertEqual(tab["rebuilt"][1:].count(True), 0, "rebuilds over the three cycles after the walk's build: %r" % (tab["rebuilt"],))
        self._assert_each_build_equals_its_re_stat(tab, "absent")
        got = [dict(deps["task_outs"]).get(str(ap), "unrecorded") for deps in tab["builds"]]
        self.assertEqual(got, [None] * len(tab["builds"]), "each build's key for the absent own place: %r" % (got,))

    def test_a_symlinked_subagents_directory_replaced_by_a_real_directory_holding_the_file_moves_no_key_a_build_recorded(self):
        """The residual group B leaves (round 3 of #882), witnessed; green by design, and not a claim that the state is
        wanted. The walk notes the own place only when nothing is there, and a symlinked subagents/ is no tree the readers
        record (a live link notes nothing), so once the link is replaced by a real directory holding the agent's file, no
        key the tab's build recorded moves and the tab keeps showing the file missing, while the lookup itself finds the
        file (the memo's stamp of the own place moved). Keys on no recorded key moving and the next cycle serving the tab.
        A kernel that keys the own place when it is a link closes the residual and turns this case red; the text in
        _subagent_file's docstring goes with it."""
        aid, ap, _target, tab = self._refused_place("subagents")
        self._tab_cycles(tab, 2)
        self.assertEqual(tab["rebuilt"], [None, False], "premise: the walk's build, then a cycle that served the tab: %r" % (tab["rebuilt"],))
        self.assertIsNone(km._SUBAGENT_FILE_CACHE.get((self.path, aid), ((), "unset"))[1], "premise: the memo keeps the miss")
        os.unlink(str(self.sub))
        self.sub.mkdir()                                            # the link replaced by a real directory holding the file
        ap.write_text("")
        self.assertTrue(not os.path.islink(self.sub) and os.path.isfile(ap), "premise: subagents/ is a real directory holding the file")
        deps = tab["builds"][-1]
        recorded = dict(deps["task_outs"])
        now_keys = dict(km._chat_sig_deps(SID, deps)[0])
        proj = str(Path(self.path).parent)
        moved = sorted(os.path.relpath(p, proj) for p in recorded if now_keys.get(p) != recorded[p])
        self.assertEqual(moved, [],
                         "keys the tab's build recorded that the replacement moved: %r; keyed on none, the residual (stated in "
                         "_subagent_file's docstring)" % (moved,))
        self._tab_cycles(tab, 1)
        self.assertEqual(tab["rebuilt"][-1], False, "the next cycle serves the tab, which shows the file missing: the residual")
        self.assertEqual(km._subagent_file(self.path, aid), ap,
                         "the lookup itself finds the file: the memo's stamp of the own place moved, so it walks")


class SumOverRoots(_World):
    """(7) The cost across sessions is the sum over the roots read of each root's own figure, whatever the split (the
    derived cost sentence in the comment block at _subagent_scope_open, docs/reference.md and the ledger entry; the lab
    that measured it at more sizes lives outside the repo, this is its pin in the tree). Three alive sessions in one
    project directory with trees of UNEQUAL size and UNEQUAL agent counts, setUp's (D, A) and EXTRA's, each read CALLS times
    in one pusher cycle and in one jobs pass, the reads interleaved across the sessions (S0, S1, S2, S0, ...) as the
    builds' are, so a scope that held one root at a time would validate on every read. Keys, per root: D_r os.lstat on its
    directories (its one validation), 0 os.stat on them, A_r os.stat on its agent files and A_r folds (one per agent, since
    every agent's owner is read from the other agents' launches when A_r >= 2); and over the cycle: the sum over the roots
    of D_r lstats, the sum over the sessions of A_s folds, R validated hits, no walk, nothing evicted, served moved by the
    asks the scope answered, and dirStats plus the sum of D_r - 1. Every figure is derived from the sessions' D_r and A_r in
    the test. Before the scope each session's N reads paid N x D_s lstats and N x A_s x D_s stats, the cost linear in the
    reads, the sessions, the agents and the directories at once."""

    EXTRA = ((5, 2), (12, 5))   # (D_r, A_r) of the two sessions built beside setUp's (D, A) = (8, 3): unequal, each A_r >= 2

    def _drop_memos(self, path, root):
        """A session's entries out of the process-wide memos (setUp's _forget_memos for a session built here)."""
        km._SUBAGENT_TREES.pop(root, None)
        km._SUBAGENT_META_CACHE.pop(root, None)
        for k in [k for k in list(km._SUBAGENT_FILE_CACHE) if k[0] == path]:
            km._SUBAGENT_FILE_CACHE.pop(k, None)
        for k in [k for k in list(km._AGENT_LAUNCH_IDS_CACHE) if str(k).startswith(root)]:
            km._AGENT_LAUNCH_IDS_CACHE.pop(k, None)

    def _sessions(self):
        """setUp's session and, for each (D_r, A_r) in EXTRA, one more beside it in the project directory: its transcript,
        name and live row, and a subagents tree of D_r directories (the root, workflows/, D_r - 2 workflow directories) with
        A_r nested agents, aged, its memos warmed OUTSIDE any scope (setUp's idiom) and popped at cleanup. Returns
        [(sid, transcript path, root, its directories, its agent ids)] in read order, the sizes asserted unequal."""
        out = [(SID, self.path, str(self.sub), list(self.dirs), list(self.aids))]
        rows = {SID: self._row()}
        cdir = Path(self.td.name) / "work"
        for s, (dr, ar) in enumerate(self.EXTRA, start=1):
            self.assertGreaterEqual(dr, ar + 2, "each agent has a workflow directory of its own")
            sid = "11111111-2222-3333-4444-7c7c7c7c7c%02x" % (0x80 + s)   # a PRIVATE placeholder sid per session
            tpath = self.tpath.parent / (sid + ".jsonl")
            tpath.write_text(self.tpath.read_text())
            (jd.NAMES / sid).write_text("web%d\t%s\t#abcdef\n" % (s, str(cdir)))
            sub = km._subagents_dir(tpath)
            wfroot = sub / "workflows"
            wfroot.mkdir(parents=True)
            dirs = [str(sub), str(wfroot)]
            aids = ["a%016x" % (0x7d00 + 0x100 * s + i) for i in range(ar)]
            for i in range(dr - 2):
                wf = wfroot / ("wf_%016x" % i)
                wf.mkdir()
                dirs.append(str(wf))
                if i < ar:
                    self._add_agent(wf, 100 * s + i, aids[i])
            self.assertEqual(len(dirs), dr)
            _age(sub)
            self.addCleanup(self._drop_memos, str(tpath), str(sub))
            rows[sid] = dict(self._row(), subagents=[{"type": "Workflow", "since": 100, "agentId": a} for a in aids])
            out.append((sid, str(tpath), str(sub), dirs, aids))
        km.Sessions.live = lambda: dict(rows)
        for sid, path, root, dirs, aids in out[1:]:
            aw = km._session_awaiting(sid, path, True)
            self.assertEqual((aw or {}).get("count"), len(aids), "the warm read of the session sees its %d agents: %r" % (len(aids), aw))
            self.assertEqual(len(km._SUBAGENT_TREES[root][0]), len(dirs), "the walk memo holds the session's %d directories" % len(dirs))
            for aid in aids:
                self.assertIsNotNone(km._SUBAGENT_FILE_CACHE.get((path, aid), (None, None))[1], "each agent's file resolved")
        self.assertEqual(len({len(d) for _s, _p, _r, d, _a in out}), len(out), "premise: the trees are of unequal size: %r" % [len(d) for _s, _p, _r, d, _a in out])
        self.assertEqual(len({len(a) for _s, _p, _r, _d, a in out}), len(out), "premise: the agent counts are unequal: %r" % [len(a) for _s, _p, _r, _d, a in out])
        return out

    def _cycle_over(self, what, run, tick):
        sess = self._sessions()
        by_root = {root: sid for sid, _p, root, _d, _a in sess}
        rec = {"counts": {sid: [] for sid, _p, _r, _d, _a in sess}, "asked": {sid: [] for sid, _p, _r, _d, _a in sess}}
        real = km._subagent_tree

        def asking(d, *a, **k):
            sc = _scope()
            held = (sc["trees"].get(str(d)) if sc is not None else None)
            out = real(d, *a, **k)
            sid = by_root.get(str(d))
            if sid is not None:
                rec["asked"][sid][-1].append("served" if held is not None and out is held[0] else "validated")
            return out

        def job(now, live_map, **kw):
            rec["scope"] = _scope()
            with mock.patch.object(km, "_subagent_tree", asking):
                for _ in range(CALLS):                    # interleaved: every session once, then again
                    for sid, path, _root, _dirs, _aids in sess:
                        rec["asked"][sid].append([])
                        aw = km._session_awaiting(sid, path, True)
                        rec["counts"][sid].append((aw or {}).get("count"))
        setattr(km, tick, job)
        folded = []
        b = self._stats()
        spies = {}
        with contextlib.ExitStack() as es:
            for _sid, _p, root, dirs, _a in sess:
                spies[root] = es.enter_context(_Spy(set(dirs), root))   # one spy per tree: disjoint directory sets
            es.enter_context(self._counting_fold(folded))
            run()
        d = self._delta(b)
        self.assertIsNotNone(rec.get("scope"), "the %s opened the subagents-tree scope on its thread" % what)
        self.assertTrue(getattr(km._live_scope, "subtrees", None) is None, "the scope ends with the %s" % what)
        sum_d = sum(len(dirs) for _s, _p, _r, dirs, _a in sess)
        sum_a = sum(len(aids) for _s, _p, _r, _d, aids in sess)
        lstats = sum(sp.total()["dir_lstat"] for sp in spies.values())
        self.assertEqual(lstats, sum_d,
                         "os.lstat over the R = %d trees in one %s: %d; keyed on the sum over the roots read of D_r, %r = %d, the total "
                         "directories whatever their split over roots (each root's one validation, however the sessions' reads "
                         "interleave); before the scope N x that = %d, and a scope holding one root at a time pays it again"
                         % (len(sess), what, lstats, [len(dirs) for _s, _p, _r, dirs, _a in sess], sum_d, CALLS * sum_d))
        self.assertEqual(len(folded), sum_a,
                         "launch folds over one %s: %d; keyed on the sum over the sessions of A_s, %r = %d, one per agent; before the "
                         "scope N x that = %d" % (what, len(folded), [len(aids) for _s, _p, _r, _d, aids in sess], sum_a, CALLS * sum_a))
        asks_total = 0
        for sid, _path, root, dirs, aids in sess:
            dr, ar = len(dirs), len(aids)
            self.assertEqual(rec["counts"][sid], [ar] * CALLS, "each of the %d reads of the session saw its %d agents: %r" % (CALLS, ar, rec["counts"][sid]))
            asks = rec["asked"][sid]
            flat = [a for bucket in asks for a in bucket]
            self.assertEqual(len(asks), CALLS)
            self.assertTrue(all(asks), "every read of the session reached the tree memo at least once: %r" % (asks,))
            self.assertEqual(flat, ["validated"] + ["served"] * (len(flat) - 1),
                             "the asks on the session's root over one %s, flattened: %r; keyed on the shape, the first validating and every "
                             "later one served the held pair, with the other sessions' reads in between (a scope holding one root at a time "
                             "validates again after each of them)" % (what, asks))
            asks_total += len(flat)
            t = spies[root].total()
            self.assertEqual((t["dir_lstat"], t["dir_stat"], t["file_stat"]), (dr, 0, ar),
                             "(os.lstat on the root's directories, os.stat on them, os.stat on its agent files) for the root of D_r = %d "
                             "directories and A_r = %d agents over one %s: %r; keyed on (D_r, 0, A_r): its one validation, no stamp "
                             "re-check stat, one fold per agent; before the scope its N = %d reads paid (N x D_r, N x A_r x D_r, N x A_r) = %r"
                             % (dr, ar, what, (t["dir_lstat"], t["dir_stat"], t["file_stat"]), CALLS, (CALLS * dr, CALLS * ar * dr, CALLS * ar)))
            names = sorted("agent-%s.jsonl" % a for a in aids)
            self.assertEqual(sorted(f for f in folded if f in set(names)), names, "one fold per agent of the session: %r" % (folded,))
        self.assertEqual((d["hit"], d["miss"], d["evict"]), (len(sess), 0, 0),
                         "memos.subagentTree over one %s: (hit, miss, evict) %r; keyed on (R = %d, 0, 0): one validated hit per root, no walk, "
                         "nothing evicted (every session is alive)" % (what, (d["hit"], d["miss"], d["evict"]), len(sess)))
        self.assertEqual(d["served"], asks_total - len(sess),
                         "memos.subagentTree served over one %s: %d; keyed on the asks the scopes answered from a held pair, %d (every ask "
                         "but each root's first)" % (what, d["served"], asks_total - len(sess)))
        self.assertEqual(d["dirStats"], sum(len(dirs) - 1 for _s, _p, _r, dirs, _a in sess),
                         "dirStats over one %s: %d; keyed on the sum over the roots of D_r - 1 = %d, the validations' lstats below each root and "
                         "no stamp re-check stat" % (what, d["dirStats"], sum(len(dirs) - 1 for _s, _p, _r, dirs, _a in sess)))

    def test_one_pusher_cycle_over_three_sessions_costs_the_sum_over_their_roots(self):
        self._cycle_over("pusher cycle", km._pusher_cycle, "_turn_notify_tick")

    def test_one_jobs_pass_over_three_sessions_costs_the_sum_over_their_roots(self):
        self._cycle_over("jobs pass", km._jobs_cycle, "_auto_nudge_tick")


class SpyRoads(_World):
    """The census's own roads (round 2 of #882, extra6-2), each executed on this world's tree under the spy, outside any
    kernel code: the roads the spy closes, each counted (a red control: a spy change that reopens one turns its case red),
    and the roads it leaves open, each an executed witness whose green is tree_calls() == {} (a spy change that closes or
    widens one turns its case red, and the _Spy docstring's list is corrected with it). _Spy's docstring names each case."""

    CLOSED = ("the census counts this road: a read through it on a served path fails that path's {} pin by the entry's name; "
              "a spy change that stops counting it reds here")
    OPEN = ("the road stays open, as _Spy's docstring states: the census does not see it; a spy change that closes or widens it "
            "reds here, and the docstring's list of roads it does not see is corrected with it")

    # ── roads the spy closes ──────────────────────────────────────────────────────────────────────────────────────────
    def test_closed_road_a_non_normalized_spelling_of_the_root(self):
        root = str(self.sub)
        parent, base = os.path.split(root)
        spellings = (parent + os.sep + os.sep + base, parent + os.sep + "." + os.sep + base,
                     root + os.sep + "workflows" + os.sep + "..")
        expect = sorted(os.listdir(root))
        with self._spy() as sp:
            got = [sorted(os.listdir(x)) for x in spellings]
        self.assertEqual(got, [expect] * len(spellings), "premise: each spelling names the root")
        self.assertEqual(sp.tree_calls(), {"listdir": len(spellings)},
                         "filesystem calls under the tree over %d listings of the root under spellings os.path.normpath maps to it "
                         "(%s), by class: %r; keyed on {listdir: %d}: %s"
                         % (len(spellings), ", ".join(("//", "/./", "workflows/..")), sp.tree_calls(), len(spellings), self.CLOSED))

    def test_closed_road_a_relative_spelling_of_the_root(self):
        rel = os.path.relpath(str(self.sub))
        self.assertFalse(os.path.isabs(rel), "premise: a relative spelling")
        with self._spy() as sp:
            os.listdir(rel)
        self.assertEqual(sp.tree_calls(), {"listdir": 1},
                         "filesystem calls under the tree over a listing of the root spelled relative to the working directory, by "
                         "class: %r; keyed on {listdir: 1}: %s" % (sp.tree_calls(), self.CLOSED))

    def test_closed_road_a_call_given_a_dir_fd(self):
        parent, base = os.path.split(str(self.sub))
        pfd = os.open(parent, os.O_RDONLY)                        # the session directory, outside the tree, opened outside the window
        self.addCleanup(os.close, pfd)
        with self._spy() as sp:
            st = os.stat(base, dir_fd=pfd, follow_symlinks=False)
            fd = os.open(base, os.O_RDONLY, dir_fd=pfd)
            os.close(fd)
        self.assertTrue(stat.S_ISDIR(st.st_mode), "premise: the descriptor-relative stat reached the root")
        self.assertEqual(sp.tree_calls(), {"open(dir_fd)": 1, "stat(dir_fd)": 1},
                         "filesystem calls over a stat and an open of the root relative to its parent's descriptor, by class: %r; keyed "
                         "on {open(dir_fd): 1, stat(dir_fd): 1}, each call given a dir_fd its own entry wherever it points: %s"
                         % (sp.tree_calls(), self.CLOSED))

    def test_closed_road_io_fileio(self):
        f = os.path.join(self.dirs[2], "agent-%s.jsonl" % self.aids[0])
        self.assertTrue(os.path.isfile(f), "premise: an agent file under the tree")
        with self._spy() as sp:
            io.FileIO(f).close()
        self.assertEqual(sp.tree_calls(), {"io.FileIO": 1},
                         "filesystem calls under the tree over an io.FileIO open of an agent file, by class: %r; keyed on "
                         "{io.FileIO: 1}: %s" % (sp.tree_calls(), self.CLOSED))

    # ── roads the spy leaves open, each witnessed ─────────────────────────────────────────────────────────────────────
    def test_open_road_a_direntry_from_a_listing_of_the_roots_parent(self):
        parent, base = os.path.split(str(self.sub))
        with self._spy() as sp:
            with os.scandir(parent) as it:
                ents = [e for e in it if e.name == base]
            self.assertEqual(len(ents), 1, "premise: the parent's listing holds the root's entry")
            self.assertTrue(stat.S_ISDIR(ents[0].stat(follow_symlinks=False).st_mode) and ents[0].is_dir(follow_symlinks=False),
                            "premise: the entry's stat and is_dir were taken")
        self.assertEqual(sp.tree_calls(), {}, "the root's DirEntry from a listing of its parent: %r; %s" % (sp.tree_calls(), self.OPEN))

    def test_open_road_a_path_outside_the_tree(self):
        proj = os.path.dirname(self.path)
        with self._spy() as sp:
            os.stat(proj)
            self.assertIn(os.path.basename(self.path), os.listdir(proj), "premise: the project directory was listed")
            with open(self.path) as fh:
                self.assertTrue(fh.read(), "premise: the transcript was read")
        self.assertEqual(sp.tree_calls(), {}, "a stat and a listing of the project directory and a read of the transcript: %r; %s"
                         % (sp.tree_calls(), self.OPEN))

    def test_open_road_an_os_call_class_outside_the_wrapped_set(self):
        root, ran = str(self.sub), []
        with self._spy() as sp:
            os.statvfs(root); ran.append("statvfs")
            os.pathconf(root, "PC_NAME_MAX"); ran.append("pathconf")
            if hasattr(os, "listxattr"):
                try:
                    os.listxattr(root)
                except OSError:                                 # a filesystem without extended attributes: the call still reached it
                    pass
                ran.append("listxattr")
        self.assertIn("statvfs", ran)
        self.assertEqual(sp.tree_calls(), {}, "%s of the root: %r; %s" % (", ".join("os." + r for r in ran), sp.tree_calls(), self.OPEN))

    def test_open_road_a_bare_descriptor(self):
        root = str(self.sub)
        fd = os.open(root, os.O_RDONLY)                           # opened outside the window: an os.open of the path inside it is counted
        self.addCleanup(os.close, fd)
        expect = sorted(os.listdir(root))
        with self._spy() as sp:
            st, names = os.stat(fd), sorted(os.listdir(fd))
            with os.scandir(fd) as it:
                list(it)
        self.assertTrue(stat.S_ISDIR(st.st_mode) and names == expect, "premise: the descriptor is the root, stat'd and listed")
        self.assertEqual(sp.tree_calls(), {}, "os.stat, os.listdir and os.scandir on a descriptor of the root: %r; %s"
                         % (sp.tree_calls(), self.OPEN))

    def test_open_road_a_symlinked_spelling_of_the_root(self):
        sess = os.path.dirname(str(self.sub))
        alias = os.path.join(self.td.name, "alias")
        os.symlink(sess, alias)
        via = os.path.join(alias, os.path.basename(str(self.sub)))
        self.assertEqual(os.path.realpath(via), os.path.realpath(str(self.sub)), "premise: the spelling names the root")
        with self._spy() as sp:
            os.listdir(via)
            os.stat(via)
        self.assertEqual(sp.tree_calls(), {}, "a listing and a stat of the root through a link to its session directory: %r; %s"
                         % (sp.tree_calls(), self.OPEN))

    def test_open_road_pathlib_on_3_10(self):
        root = Path(str(self.sub))
        with self._spy() as sp:
            self.assertTrue(stat.S_ISDIR(root.stat().st_mode), "premise: pathlib stat'd the root")
        if sys.version_info < (3, 11):
            self.assertEqual(sp.tree_calls(), {}, "Path.stat of the root on %s, whose pathlib calls the os.stat it bound at import: "
                             "%r; %s" % (sys.version.split()[0], sp.tree_calls(), self.OPEN))
        else:
            self.assertEqual(sp.tree_calls(), {"stat": 1}, "Path.stat of the root on %s, whose pathlib looks os.stat up at call time: "
                             "%r; keyed on {stat: 1}: this interpreter's pathlib is counted" % (sys.version.split()[0], sp.tree_calls()))


if __name__ == "__main__":
    unittest.main()
