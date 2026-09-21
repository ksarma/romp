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
stamp; every later reader on that thread in the cycle, the agent-file lookup's stamp re-check included, pays no stat;
and the agents' launch folds are held for the cycle too (_awaiting_nest). A change on disk after the validation is
seen by the NEXT cycle's first reader, one cycle later at most. Nothing failed is held for the cycle; a launch fold that
did not read the file is held for the CALL that observed the fault alone (two lifetimes; round 1 of #882 found that returned without
any hold it was folded once per owner lookup, A x (A - 1) times per read where the parent's call-local memo folded A).

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
census of every filesystem call class under the tree (os.stat, os.lstat, os.scandir, os.listdir, os.access, os.readlink,
os.open, os.walk, io.open) pinned by equality, {lstat: D, stat: A} over the cycle and {} on each served path (the tree read,
the stamp, the agent-file hit), so a read through a class the counts do not see fails by name (the owner's pass before round 2
of #882: a guarded listing on the served path left the module green); and a read
outside any cycle (a handler thread's) still pays per call, with dirStats now counting the stats of both validators;
(2) per cycle, not sticky: a directory and a fourth agent landing between two cycles are seen by the second cycle's
first read (a re-walk; the listing equals os.walk's and the sidecar reaches the map) while its later reads that cycle
cost nothing, a launch appended to an agent's transcript between two cycles is folded by the second cycle's first read
(A folds, the launch folds being the cycle's) and nests its command there, and, the contract, a directory created after a
cycle's validation waits for the next cycle; (3) two
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
read, so an eviction landing inside the root's lstat, an own stat or a launch fold's resolution leaves that hold outdated
and the next lookup validates, stats or folds it once more (D lstats, 1 stat, 1 fold) instead of serving it; a root gone mid-cycle whose entry stood
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
every later re-stat, and the tab that showed the file missing was never rebuilt. (7) The sum over roots: three alive
sessions with trees of unequal size and unequal agent counts, read in one pusher cycle and in one jobs pass with the reads
interleaved, cost the sum over their roots of D_r lstats (each root its own D_r), 0 stats and one fold per agent (the sum
over the sessions of A_s), so the total directories decide the cycle's cost and not their split over roots (the derived
cost sentence's pin in the tree; a lab lifted from this world measured the same at more sizes outside the repo).

Every count is derived from D and A in the test, never written out. The cycle's jobs that read the tree through
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
from unittest import mock
from romp_load import load_source

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
    those counts a CENSUS of every filesystem call under the tree by call class (`tree_calls`): os.stat, os.lstat,
    os.scandir, os.listdir, os.access, os.readlink, os.open, os.walk and io.open (builtins.open is the same function and
    is patched too), keyed by the class's name, for every path that is the root or lies under it, directories and files
    alike. The counts key on what the bound derives (D lstats, A file stats); the census is pinned by EQUALITY where the
    bound's cases and the served paths run (_assert_bound, the served-paths case), so a read of the tree through a class
    the counts do not see, a listing, an access, an open, a file's lstat, fails closed by the class's name (the owner's
    pass before round 2 of #882: the spy saw os.stat and os.lstat alone, and a guarded os.scandir on the served tree path
    left the module green). The patch is the os module's attribute, which is what the kernel, os.path and, from 3.12,
    pathlib look up at call time (pathlib on 3.10 binds the os functions at import, outside the census; the kernel runs
    on 3.12). Not in the census, stated: a DirEntry's stat or is_dir, reached only from a scandir the census counts by
    the directory listed (a listing on a served path is seen; what is done with its entries is not), and any call on a
    path outside the tree (the project directory)."""
    KEYS = ("dir_stat", "dir_lstat", "file_stat")
    CLASSES = ("stat", "lstat", "scandir", "listdir", "access", "readlink", "open", "walk")   # the os functions wrapped; io.open beside them

    def __init__(self, dirset, root):
        self.dirset, self.tree, self.root, self.by, self.census = dirset, str(root), str(root) + os.sep, {}, {}

    def _c(self):
        return self.by.setdefault(threading.get_ident(), dict.fromkeys(self.KEYS, 0))

    def _seen(self, cls, p):
        """One call of class `cls` on `p`: counted in this thread's census when `p` is a path (not a descriptor) that is the
        root or lies under it."""
        if p is None or isinstance(p, int):
            return
        try:
            s = os.fsdecode(p)
        except TypeError:
            s = str(p)
        if s == self.tree or s.startswith(self.root):
            c = self.census.setdefault(threading.get_ident(), {})
            c[cls] = c.get(cls, 0) + 1

    def _wrapped(self, cls, real):
        spy = self

        def w(*a, **k):
            spy._seen(cls, a[0] if a else k.get("path", k.get("top")))
            return real(*a, **k)
        return w

    def __enter__(self):
        real_stat, real_lstat, real_open, spy = os.stat, os.lstat, io.open, self

        def st(p, *a, **k):
            s = str(p)
            if s in spy.dirset:
                spy._c()["dir_stat"] += 1
            elif s.startswith(spy.root):
                spy._c()["file_stat"] += 1
            spy._seen("stat", p)
            return real_stat(p, *a, **k)

        def lst(p, *a, **k):
            if str(p) in spy.dirset:
                spy._c()["dir_lstat"] += 1
            spy._seen("lstat", p)
            return real_lstat(p, *a, **k)

        def opn(f, *a, **k):
            spy._seen("io.open", f)
            return real_open(f, *a, **k)
        self._patches = [mock.patch.object(os, "stat", st), mock.patch.object(os, "lstat", lst)]
        self._patches += [mock.patch.object(os, cls, self._wrapped(cls, getattr(os, cls))) for cls in self.CLASSES[2:]]
        self._patches += [mock.patch.object(io, "open", opn), mock.patch.object(builtins, "open", opn)]
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
        """The census: {call class: count} over every filesystem call under the tree the spy saw, summed over threads (one
        thread's when `ident` is given); {} when it saw none. Compared by equality, so a class absent from the expectation
        fails by its name."""
        out = {}
        for i, c in list(self.census.items()):
            if ident is None or i == ident:
                for cls, n in c.items():
                    out[cls] = out.get(cls, 0) + n
        return dict(sorted(out.items()))


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

            def asking(d):
                sc = _scope()
                held = (sc["trees"].get(str(d)) if sc is not None else None)   # (the (dirs, stats) pair, the gen it was held under)
                out = real(d)
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
                         "os.stat on the tree's %d directories over one %s: %d; the bound is 0, every agent-file hit's stamp re-check "
                         "(_dir_stamps) served from the scope _subagent_tree filled at the cycle's one validation; before the scope "
                         "it was CALLS x A x D = %d, one re-stat of every directory per agent per _session_awaiting call"
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
                         "filesystem calls under the tree over one %s, by call class (the census wraps os.%s and io.open, on every "
                         "path that is the root or under it): %r; keyed on equality with {lstat: D = %d, stat: A = %d}, the one "
                         "validation's lstats and the A agent-file stats and nothing else, so a read of the tree through any other "
                         "class, or one more of these, fails here by the class's name (a guarded listing, an access or an open on a "
                         "served path moves none of the counts above)" % (what, ", ".join(_Spy.CLASSES), c, D, A))
        self.assertIsNotNone(rec.get("scope"), "the %s opened the subagents-tree scope on its thread (_subagent_scope_open)" % what)
        self.assertTrue(getattr(km._live_scope, "subtrees", None) is None,
                        "the scope ends with the %s (_subagent_scope_close in its finally): the slot still holds a scope" % what)


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

    def _miss_walk_cycle(self, G):
        """One pusher cycle over the world plus G live agent rows whose file exists nowhere, under the own tree or a
        sibling's (the ghosts), with the miss path's costs that are each row's own asserted here, derived from D, A and G:
        each row's first owner lookup walks once (the walk misses and the scope's launches map holds set() for it, so the
        rest of the cycle is served), the walk's dependency notes to the running chat build (the absent own place, every
        directory of each tree it looked through) come from the pair the lookup was answered, the served tree, so they cost
        no stat on the tree's directories (0 os.stat; round 1 of #882's correctness-1: the own tree's note was a fresh
        _chat_stat_key stat, 1 per walk), and each walk pays W lstats of the own root, its two symlink checks (os.path.islink,
        and os.path.realpath's lstat per component), counted by running those two calls, and one os.stat per candidate file,
        the flat place and one per served directory (D + 1). The walk's own ask on the root is among the first read's and is
        served, not a second validation: the asks are asserted by shape, and served by the asks the scope answered
        (_assert_asks). What the rows SHARE, the project directory's one stamp stat in dirStats, the caller asserts: one row
        and two rows pay the same. Returns (the spy's totals, the counters' delta, the job's record, the ghosts)."""
        ghosts = ["a%016x" % (0x7cf1 + i) for i in range(G)]
        self.live_aids.extend(ghosts)                         # in the live row; no sidecar and no file anywhere
        own = str(self.sub)
        with self._spy() as sp0:
            os.path.islink(own); os.path.realpath(own)
        W = sp0.total()["dir_lstat"]
        rec = {}
        km._turn_notify_tick = self._awaiting_job(rec)
        b = self._stats()
        with self._spy() as sp:
            km._pusher_cycle()
        t, d = sp.total(), self._delta(b)
        what = "pusher cycle with the miss walk" if G == 1 else "pusher cycle with %d miss walks" % G
        self.assertEqual(rec.get("counts"), [A + G] * CALLS, "each of the %d reads saw the A agents and the %d rows nobody owns: %r" % (CALLS, G, rec))
        flat = self._assert_asks(what, rec.get("asked") or [], d, CALLS)
        self.assertGreater(len(flat), CALLS, "the asks on the root: %r; the miss walk asked the tree too, beyond the %d reads' own asks "
                                             "(and was served: the shape above)" % (rec.get("asked"), CALLS))
        self.assertEqual(t["dir_stat"], 0,
                         "os.stat on the tree's %d directories over one %s: %d; keyed on 0, the walk's notes "
                         "to the chat build taken from the served pair and the stamp re-checks served as in the bound (round 1 of #882: "
                         "the own tree's note was a fresh stat, 1 per walk)" % (D, what, t["dir_stat"]))
        self.assertEqual(t["dir_lstat"], D + G * W,
                         "os.lstat on the tree's directories: %d; expected D + G x W = %d + %d x %d, the one validation plus each walk's "
                         "symlink checks of the own root" % (t["dir_lstat"], D, G, W))
        self.assertEqual(t["file_stat"], A + G * (D + 1),
                         "os.stat on files under the tree: %d; expected A + G x (D + 1) = %d, one fold per agent with a file plus each "
                         "walk's candidate stats, the flat place and one per served directory" % (t["file_stat"], A + G * (D + 1)))
        self.assertEqual((d["hit"], d["miss"], d["evict"]), (1, 0, 0), "one validated hit, no walk of the tree, nothing evicted: %r" % (d,))
        for ghost in ghosts:
            self.assertIsNone(km._SUBAGENT_FILE_CACHE.get((self.path, ghost), ("unset",))[-1], "the miss is memoized: the file is nowhere")
        return t, d, rec, ghosts

    def test_one_pusher_cycle_with_an_agent_whose_file_is_nowhere_walks_once_and_its_notes_cost_no_stat(self):
        """The miss path inside the bound (fresh-4 of the round-1 review: no case entered it): one live agent row whose file
        exists nowhere. Its own costs are _miss_walk_cycle's assertions; here, the project directory's one stamp stat, in
        dirStats and outside the tree (the two-row case beside this one pins that it is shared)."""
        t, d, rec, ghosts = self._miss_walk_cycle(1)
        self.assertEqual(d["dirStats"], D,
                         "dirStats %d; expected (D - 1) + 1 = %d: the validation's lstats plus the project directory's one stamp stat, "
                         "the walk's, held for the cycle under no root" % (d["dirStats"], D))

    def test_two_agents_whose_files_are_nowhere_share_the_project_directorys_one_stamp_stat(self):
        """The miss path's term of the cost expression is once per cycle, SHARED by every agent whose file is nowhere or
        under a sibling's tree, not once per such agent (the owner's pass before round 2 of #882: the term's homes read per
        agent, G such rows paying G project-directory stats where the code pays 1; the expression's one home is
        _subagent_tree_memo_report's docstring). Two such rows: each walks once and pays its own candidate stats and symlink
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

    def test_the_served_tree_read_the_served_stamp_and_the_agent_file_hit_make_no_filesystem_call_of_any_class_under_the_tree(self):
        """The premise the bound's zeros rest on, by census rather than by two counts (the owner's pass before round 2 of
        #882: the count pins saw os.stat and os.lstat alone, so a guarded os.scandir, an os.access or an os.open on the
        served tree path, and a listing on _dir_stamp's served path, left the module green). Inside one scope, after the
        hold, each of the three served paths runs under the spy's census on its own: the tree read _subagent_tree answers
        from the held pair, the stamp _dir_stamp answers from the held stamps, and the agent-file hit _subagent_file answers
        from its memo with its stamp re-check served. Each makes no filesystem call of any class the census wraps on any
        path that is the root or under it, keyed on the census == {} per path, so a new call class on a served path fails
        here by its name and by the path it ran on."""
        root, aid, sd = str(self.sub), self.aids[0], self.dirs[3]
        sc = self._open()
        km._subagent_tree(root)                              # the hold: the cycle's one validation, its stamps indexed
        self.assertIn(root, sc["trees"], "premise: the pair is held")
        self.assertIn(sd, sc["stamps"], "premise: the directory's stamp is held, indexed from the tree")
        self.assertIsNotNone(km._SUBAGENT_FILE_CACHE.get((self.path, aid), (None, None))[1], "premise: the agent's file is memoized (setUp's warm read)")
        classes = "os.%s and io.open" % ", ".join(_Spy.CLASSES)
        b = self._stats()
        with self._spy() as sp:
            pair = km._subagent_tree(root)
        self.assertIs(pair, sc["trees"][root][0], "premise: the tree read was answered the held pair")
        self.assertEqual(self._delta(b)["served"], 1, "premise: the read moved served")
        self.assertEqual(sp.tree_calls(), {},
                         "filesystem calls under the tree on the served tree read, by class: %r; keyed on {} (no call of any class the "
                         "census wraps, %s, on the root or under it); a listing, an access or an open on this path shows here by name"
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
        self.assertEqual(t["dir_stat"], 0, "no reader in cycle two re-stat'd the %d directories: the walk's pair served every "
                                           "agent-file re-check (before the scope each later read alone paid (A + 1) x D = %d)"
                         % (D + 1, (A + 1) * (D + 1)))
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
        self._open()
        b = self._stats()
        with self._spy() as sp:
            km._subagent_tree(str(self.sub)); km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], D, "two reads in one scope cost one validation")
        self.assertEqual((self._delta(b)["hit"], self._delta(b)["served"]), (1, 1),
                         "the first read validated and the second was served the held pair: %r" % (self._delta(b),))
        # accept: a forget over a live set that owns the root evicts nothing, moves no gen, and the scope keeps serving
        km._subagent_trees_forget([{"path": self.path}])
        self.assertEqual(self._delta(b)["evict"], 0)
        with self._spy() as sp:
            km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], 0, "served: nothing was evicted, the held pair stands")
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
        with self._spy() as sp:
            dirs3, _s3 = km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], 0, "served from the scope")
        self.assertEqual(self._delta(b)["miss"], 2)
        self.assertEqual(dirs3, dirs2)

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
        """The generation is read BEFORE the disk read at each of the three hold sites (the pair's before the root's lstat,
        here; the own stat's before its stat and the launch fold's before its file's resolution, the two cases below), so an
        eviction that lands inside the read leaves the hold outdated and the next lookup validates, stats or folds once more
        instead of serving an entry under a value that already counts the eviction: the safe side, one re-validation, as the
        ledger and the docstrings state. Fires the own root's eviction (nobody alive owns it: _subagent_trees_forget) from
        inside os.lstat of the root, the read's first call, so the read's walk re-inserts the root and the hold is under the
        generation from before the eviction. Keys on the second read costing D lstats (a validation): a generation read after
        the root's lstat counts the eviction and serves the pair (0)."""
        root = str(self.sub)
        self._open()
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
        with self._spy() as sp:
            km._subagent_tree(root)
        self.assertEqual(sp.total()["dir_lstat"], 0, "held again, under a generation that counts the eviction: served")

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
        with self._spy() as sp:
            km._dir_stamp(target)
        self.assertEqual(sp.total()["dir_stat"], 0, "held again: served")

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
            km._subagent_tree(str(self.sub)); km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], D, "the held tree: one validation, then served")
        self.assertIn(str(self.sub), sc["trees"])
        shutil.rmtree(other)
        g0 = km._SUBAGENT_TREES_GEN[0]
        # refuse: the entry stood, so the pop is an eviction: the gen moves, the root's eviction is recorded at the new value, and
        # the held sibling is still served (its root did not leave the memo)
        self.assertEqual(km._subagent_tree(str(other)), ((), ()), "nothing at the root: (), () as ever")
        self.assertNotIn(str(other), km._SUBAGENT_TREES)
        self.assertEqual(km._SUBAGENT_TREES_GEN[0] - g0, 1, "the missing-root pop that removed an entry moved _SUBAGENT_TREES_GEN")
        with self._spy() as sp:
            dirs, _stats = km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], 0, "os.lstat on the held sibling's directories after the pop: %d; keyed on the sibling being "
                                                     "served (0), since the eviction was the other root's and its pair is as fresh as before; "
                                                     "one process-wide generation emptied the scope and cost D = %d lstats again"
                         % (sp.total()["dir_lstat"], D))
        self.assertEqual(len(dirs), D)
        self.assertEqual(km._SUBAGENT_ROOT_EVICTED.get(str(other)), km._SUBAGENT_TREES_GEN[0],
                         "the pop recorded the removed root's eviction at the value the gen moved to: what a scope holds for it is dropped")
        # accept: no entry stands now, so the same call moves nothing and the held tree stays served
        g1 = km._SUBAGENT_TREES_GEN[0]
        self.assertEqual(km._subagent_tree(str(other)), ((), ()))
        self.assertEqual(km._SUBAGENT_TREES_GEN[0], g1, "a missing root with no entry moves no gen")
        with self._spy() as sp:
            km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], 0, "served: nothing was evicted")
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
        self.assertEqual(self._delta(s_drop)["served"], 0,
                         "memos.subagentTree served over the holder's read that dropped its stale pair and lstat'd the %s root: %d; keyed on 0 "
                         "(a hold dropped at the lookup is not a served read, and what the lstat found is no tree)" % (shape, self._delta(s_drop)["served"]))
        moved, answered, lstats = km._SUBAGENT_TREES_GEN[0] - g0, len(got[0]), osp.total()["dir_lstat"]
        self.assertEqual((moved, answered, lstats), (1, 0, 1),
                         "(_SUBAGENT_TREES_GEN's move on the %s-root pop, directories the holding thread is answered for that root on its "
                         "next read, its os.lstat of the root) %r; keyed on (1, 0, 1): one eviction event recorded (_subagent_root_evicted), "
                         "the holder's pair dropped at the lookup since the vouch fails on that record, and the root's own lstat paid; a "
                         "pop that recorded nothing is (0, D = %d, 0), the held pair served stale for the rest of the cycle"
                         % (shape, (moved, answered, lstats), D))
        self.assertEqual(km._SUBAGENT_ROOT_EVICTED.get(str(other)), seen.get("gen"),
                         "the table names the %s root at the value the gen moved to: %r against %r; keyed on equality (the record that "
                         "outdates every scope's hold on this root)" % (shape, km._SUBAGENT_ROOT_EVICTED.get(str(other)), seen.get("gen")))
        self._assert_not_a_tree(got, shape, "the holder's read after the pop")
        self.assertNotIn(str(other), sc["trees"], "the holder's scope no longer holds the popped root")
        served_reads = 0                                  # this session's held tree, read twice below and answered the held pair each time
        with self._spy() as sp:
            dirs, _stats = km._subagent_tree(str(self.sub))
        served_reads += 1
        self.assertEqual((sp.total()["dir_lstat"], len(dirs)), (0, D),
                         "this session's held tree on the read after the sibling's pop: (lstats, directories) %r; keyed on (0, D = %d), "
                         "served, since the eviction recorded is the sibling's; one process-wide generation emptied this hold too"
                         % ((sp.total()["dir_lstat"], len(dirs)), D))
        # accept: no entry stands, so a second read of the same root pops nothing, moves no gen and records nothing new
        g1, rec1 = km._SUBAGENT_TREES_GEN[0], km._SUBAGENT_ROOT_EVICTED.get(str(other))
        with _Spy(oset, other) as osp:
            again = km._subagent_tree(str(other))
        self._assert_not_a_tree(again, shape, "a second read with no entry standing")
        self.assertEqual(osp.total()["dir_lstat"], 1, "the second read costs the root's lstat alone")
        self.assertEqual((km._SUBAGENT_TREES_GEN[0], km._SUBAGENT_ROOT_EVICTED.get(str(other))), (g1, rec1),
                         "a %s root with no entry standing moves no gen and records nothing new: (gen, record) %r against %r"
                         % (shape, (km._SUBAGENT_TREES_GEN[0], km._SUBAGENT_ROOT_EVICTED.get(str(other))), (g1, rec1)))
        with self._spy() as sp:
            km._subagent_tree(str(self.sub))
        served_reads += 1
        self.assertEqual(sp.total()["dir_lstat"], 0, "this session's tree still served")
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
        apart: a kernel whose missing-root pop records nothing reds this case (and the same-thread guard above, and the
        cached-agent-file case) and leaves the replaced one green, and a kernel whose replaced-root pop records nothing does
        the reverse. The pop answers (), ()."""
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
        shutil.rmtree(self.sub)
        g0 = km._SUBAGENT_TREES_GEN[0]
        with self._spy() as sp:
            dirs, _stats = km._subagent_tree(root)
            stamp = km._dir_stamp(self.dirs[3])
        t = sp.total()
        self.assertEqual((len(dirs), t["dir_lstat"], t["dir_stat"]), (D, 0, 0),
                         "(directories answered, os.lstat, os.stat) on this thread's read of a held root after its removal on disk: %r; "
                         "keyed on (D = %d, 0, 0), the served pair and stamp (the served call precedes the root's lstat: the lag the "
                         "design states, one cycle at most); a read that lstats the root before serving answers () at one lstat"
                         % ((len(dirs), t["dir_lstat"], t["dir_stat"]), D))
        self.assertEqual(stamp, held_stamp, "the removed directory's stamp is served from the hold too: %r against the held %r" % (stamp, held_stamp))
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
        self._open()
        b = self._stats()
        with self._spy() as sp:
            km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], D, "the hold: the cycle's one validation")
        self._evict([other], [])
        with self._spy() as sp:
            dirs, _stats = km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], 0,
                         "os.lstat on the held tree's directories on the read after an unrelated root's eviction: %d; keyed on the held pair "
                         "being served (0), since another root leaving the memo leaves this pair as fresh as it was; one process-wide "
                         "generation emptied the scope and cost D = %d lstats again, once per forget" % (sp.total()["dir_lstat"], D))
        self.assertEqual(len(dirs), D)
        self.assertEqual((self._delta(b)["hit"], self._delta(b)["miss"]), (1, 0), "one validation in the scope, none after the eviction")

    def test_a_held_stamp_survives_the_eviction_of_a_root_its_directory_is_not_under(self):
        _op, other = self._other_root()
        self._open()
        km._subagent_tree(str(self.sub))                  # the D directories' stamps indexed from the held tree
        target = self.dirs[3]
        with self._spy() as sp:
            r1 = km._dir_stamp(target)
        self.assertEqual(sp.total()["dir_stat"], 0, "served from the held tree's index before the eviction")
        self._evict([other], [])
        with self._spy() as sp:
            r2 = km._dir_stamp(target)
        self.assertEqual(sp.total()["dir_stat"], 0,
                         "os.stat for a held stamp on the read after an unrelated root's eviction: %d; keyed on the stamp being served (0), "
                         "since it was indexed from a tree that did not leave the memo; one process-wide generation emptied the scope's "
                         "stamps and cost one stat per held stamp" % sp.total()["dir_stat"])
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
        self.assertEqual(sp.total()["dir_stat"], 0, "the hit's stamp re-check served from the scope")
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
        stamps0, p0 = km._SUBAGENT_FILE_CACHE[(self.path, aid)]
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
        with self._spy() as sp:
            km._dir_stamp(target)
        self.assertEqual(sp.total()["dir_stat"], 0, "held within the cycle: served")
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
        with self._spy() as sp:
            r3 = km._dir_stamp(target)
        self.assertEqual(sp.total()["dir_stat"], 0,
                         "os.stat for the same directory's stamp, indexed from the held tree, after another unrelated eviction: %d; keyed "
                         "on 0 (served: its root did not leave the memo), the contrast with the own stat's 1" % sp.total()["dir_stat"])
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
        (one re-validation, the safe side: never a stale serve) and entries held after it are vouched by the table again.
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
            self._open()
            with self._spy() as sp:
                km._subagent_tree(str(self.sub))
            self.assertEqual(sp.total()["dir_lstat"], D, "the hold")
            folded = []
            with self._counting_fold(folded), self._spy() as sp:
                aw = km._session_awaiting(SID, self.path, True)   # the launch folds held, the stamps served from the held tree
            self.assertEqual(((aw or {}).get("count"), sorted(folded), sp.total()["dir_lstat"], sp.total()["dir_stat"]), (A, names, 0, 0),
                             "the hold, launches half: one fold per agent, the tree and its stamps served: %r" % ((aw or {}).get("count"),))
            for i in range(cap):                          # cap evictions of distinct roots fill the table; the held pair survives each
                self._evict([others[i][1]], [p for p, _r in others[i + 1:]])
                with self._spy() as sp:
                    km._subagent_tree(str(self.sub))
                self.assertEqual(sp.total()["dir_lstat"], 0, "eviction %d of %d distinct roots: the held pair still served" % (i + 1, cap))
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
            with self._spy() as sp:
                km._subagent_tree(str(self.sub)); km._dir_stamp(target)
            self.assertEqual((sp.total()["dir_lstat"], sp.total()["dir_stat"]), (0, 0), "held again under the new generation: served, pair and stamp")


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
    the landing moved the root's stamp or a listed child's. Driven through the real _pusher_cycle, with the build's record
    shape (build_session's literal) open around the real _session_awaiting."""

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
            rec["found"] = km._SUBAGENT_FILE_CACHE.get((self.path, aid), ("unset",))[-1]
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

        def asking(d):
            sc = _scope()
            held = (sc["trees"].get(str(d)) if sc is not None else None)
            out = real(d)
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


if __name__ == "__main__":
    unittest.main()
