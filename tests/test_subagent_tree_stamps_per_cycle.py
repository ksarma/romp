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
did not read the file is held for the CALL that observed the fault alone (two lifetimes, round 2 of #882: returned without
any hold it was folded once per owner lookup, A x (A - 1) times per read where the parent's call-local memo folded A).

Pinned here, through the REAL cycle functions so the clearing point tested is the wired one: (1) the bound: one pusher
cycle and one jobs pass with three _session_awaiting calls each cost D os.lstat on the tree's directories (the one
validation), 0 os.stat on them, dirStats plus D - 1, one hit and A agent-file stats (one fold per agent), where before
the scope each call paid A x D os.stat, D lstats and A file stats; the scope is closed after the cycle; and a read
outside any cycle (a handler thread's) still pays per call, with dirStats now counting the stats of both validators;
(2) per cycle, not sticky: a directory and a fourth agent landing between two cycles are seen by the second cycle's
first read (a re-walk; the listing equals os.walk's and the sidecar reaches the map) while its later reads that cycle
cost nothing, and, the contract, a directory created after a cycle's validation waits for the next cycle; (3) two
threads: a pusher cycle and a jobs pass running at once each validate once with their own scope object, never served
by the other's; (4) the guards, each against the input it refuses and the input it accepts: a forget that evicts the
root makes the next read in the same scope walk again while a forget that evicts nothing leaves the scope serving; a
stamp stat that raises is answered (dir, None) and not held while one that succeeds is held; a walk with a failed
listing is not held while a clean one is; a launch fold that did not read the file is folded once per read (the call-local
hold) and again by the next read (not held for the cycle) while one that read it is held for the cycle, with the fault's
producer driven for real (the reader's fail path, a raising fold, a readable file); a root gone mid-cycle whose entry stood
moves the gen, so a sibling tree the scope held is validated again, while one with no entry moves nothing and leaves it
served.

Every count is derived from D and A in the test, never written out. The cycle's jobs that read the tree through
mechanisms of their own (the fold checkpoint writer's realpath per checkpointed file, the spend guard's window-file
walk) are stubbed to nothing here, so what the spy counts is this memo's path alone. Synthetic fixtures only: a
private placeholder sid, invented agent ids and descriptions, a temp state root with session hosts off.
"""
import errno
import json
import os
import shutil
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

D = 8              # directories in the tree: the subagents root, workflows/, and D - 2 workflow directories under it
A = 3              # awaiting workflow agents, one nested in each of the first A workflow directories
CALLS = 3          # _session_awaiting calls the stubbed job makes per cycle: the chat, feed and timeline builds' share
SID = "11111111-2222-3333-4444-7c7c7c7c7c7c"   # a PRIVATE placeholder sid (the goal-store fixture rule; this module mints no goals)
OTHER_SID = "11111111-2222-3333-4444-7c7c7c7c7c7d"   # a second private placeholder: the session whose tree vanishes mid-cycle (Guards)
NOW = 1781100000
AGED_NS = 10_000_000_000                       # ten seconds: past the racy window, as tests/test_subagent_tree_memo.py ages
STAT_KEYS = ("hit", "miss", "evict", "dirStats")

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
    `dir_lstat`), a file under the tree (`file_stat`: the agent files and sidecars), or elsewhere (uncounted). The patch
    is the os module's attribute, which is what the kernel and os.path look up at call time (pathlib on 3.10 binds the os
    functions at import; every path counted here is stat'd through os.stat, os.lstat or os.path)."""
    KEYS = ("dir_stat", "dir_lstat", "file_stat")

    def __init__(self, dirset, root):
        self.dirset, self.root, self.by = dirset, str(root) + os.sep, {}

    def _c(self):
        return self.by.setdefault(threading.get_ident(), dict.fromkeys(self.KEYS, 0))

    def __enter__(self):
        real_stat, real_lstat, spy = os.stat, os.lstat, self

        def st(p, *a, **k):
            s = str(p)
            if s in spy.dirset:
                spy._c()["dir_stat"] += 1
            elif s.startswith(spy.root):
                spy._c()["file_stat"] += 1
            return real_stat(p, *a, **k)

        def lst(p, *a, **k):
            if str(p) in spy.dirset:
                spy._c()["dir_lstat"] += 1
            return real_lstat(p, *a, **k)
        self._patches = [mock.patch.object(os, "stat", st), mock.patch.object(os, "lstat", lst)]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self._patches:
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

    @staticmethod
    def _stats():
        return dict(km._SUBAGENT_TREE_STATS)

    @staticmethod
    def _delta(before):
        return {k: km._SUBAGENT_TREE_STATS[k] - before[k] for k in STAT_KEYS}

    def _awaiting_job(self, rec, spy=None, probe=False):
        """A tick job's stand-in (the pusher's _turn_notify_tick, the pass's _auto_nudge_tick): CALLS _session_awaiting
        reads of the session, as the chat, feed and timeline builds make in one cycle. Records into `rec` rather than
        asserting: the cycle runs each job under a try that writes a raise to stderr and goes on. `spy` given, the
        spy's totals after each call; `probe`, the listing and the sidecar map as read inside the cycle. `asked` records,
        per _subagent_tree call on the session's root made by those reads, whether the scope already held the pair and
        answered with it ("served") or the call validated or walked ("validated"): the premise the bound rests on, that
        every read reached the memo, is asserted, so a read that never asked cannot satisfy the bound for nothing."""
        def job(now, live_map, **kw):
            rec["scope"] = _scope()
            rec["counts"], rec["per_call"], rec["asked"] = [], [], []
            real, root = km._subagent_tree, str(self.sub)

            def asking(d):
                sc = _scope()
                held = (sc["trees"].get(str(d)) if sc is not None else None)
                out = real(d)
                if str(d) == root:
                    rec["asked"].append("served" if held is not None and out is held else "validated")
                return out
            with mock.patch.object(km, "_subagent_tree", asking):   # what _subagent_dirs, _subagent_meta_map and the file walk look up
                for _ in range(CALLS):
                    aw = km._session_awaiting(SID, self.path, True)
                    rec["counts"].append((aw or {}).get("count"))
                    if spy is not None:
                        rec["per_call"].append(spy.total())
            if probe:
                rec["dirs"] = list(km._subagent_dirs(str(self.sub)))
                rec["meta"] = set(km._subagent_meta_map(self.path))
        return job

    def _assert_bound(self, what, t, d, rec):
        """The per-cycle bound, derived from D and A: the counts one pusher cycle or one jobs pass pays on the tree. The
        counts first, so a red names the cost, then the scope's presence inside the cycle and its absence after."""
        self.assertEqual(rec.get("counts"), [A] * CALLS, "the stubbed job made its %d reads and each saw the A agents: %r" % (CALLS, rec))
        self.assertEqual(rec.get("asked"), ["validated"] + ["served"] * (CALLS - 1),
                         "each of the %d reads in one %s reached the tree memo, the first validating and every later one served the held "
                         "pair: %r (a bound met because a later read never asked is no bound; a later read that validated again is the "
                         "per-reader cost the scope removes)" % (CALLS, what, rec.get("asked")))
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
        self._assert_bound("pusher cycle", sp.total(), self._delta(b), rec)

    def test_one_jobs_pass_validates_the_tree_once_however_many_readers(self):
        rec = {}
        km._auto_nudge_tick = self._awaiting_job(rec)     # where the real pass reaches _session_awaiting (the nudge look)
        b = self._stats()
        with self._spy() as sp:
            km._jobs_cycle()
        self._assert_bound("jobs pass", sp.total(), self._delta(b), rec)
        self.assertIn(str(self.sub), km._SUBAGENT_TREES, "the interrupt tick's forget kept the alive session's root")

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

    def _open(self):
        km._subagent_scope_open()
        self.addCleanup(km._subagent_scope_close)
        return km._subagent_scope()

    def test_a_forget_that_evicts_the_root_makes_the_next_read_walk_again_while_one_that_evicts_nothing_leaves_it_served(self):
        self._open()
        b = self._stats()
        with self._spy() as sp:
            km._subagent_tree(str(self.sub)); km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], D, "two reads in one scope cost one validation")
        # accept: a forget over a live set that owns the root evicts nothing, moves no gen, and the scope keeps serving
        km._subagent_trees_forget([{"path": self.path}])
        self.assertEqual(self._delta(b)["evict"], 0)
        with self._spy() as sp:
            km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], 0, "served: nothing was evicted, the held pair stands")
        # refuse: nobody alive evicts the root; the next read in the SAME scope walks again instead of being served the evicted pair
        km._subagent_trees_forget([])
        self.assertEqual(self._delta(b)["evict"], 1)
        self.assertNotIn(str(self.sub), km._SUBAGENT_TREES)
        with self._spy() as sp:
            dirs, _stats = km._subagent_tree(str(self.sub))
        d = self._delta(b)
        self.assertEqual(d["miss"], 1, "the read after the forget walked (a miss), not the held pair: _subagent_trees_forget moves "
                                       "_SUBAGENT_TREES_GEN and _subagent_scope empties a scope opened under the older value")
        self.assertEqual(sp.total()["dir_lstat"], D, "a walk: the root and each child by lstat, D = %d" % D)
        self.assertEqual(len(dirs), D)

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
        self.assertEqual(sc["stamps"].get(target), r3)

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

    def test_a_faulted_launch_fold_is_folded_once_per_call_and_not_held_across_calls(self):
        """Two lifetimes for a launch fold whose reader took its fail path (_awaiting_nest's `faulted`, round 2 of #882): the
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

    def test_a_root_gone_mid_cycle_with_an_entry_moves_the_gen_and_revalidates_the_held_tree_while_one_without_leaves_it_served(self):
        """_subagent_tree's missing-root pop path (a session's tree removed while the walk memo held it): a pop that removed
        an entry moves _SUBAGENT_TREES_GEN, so a scope opened before it empties itself and a sibling tree it held is validated
        once more in that cycle (the eviction cost the reference names); a missing root with no entry answers (), () and
        moves nothing, so the held tree stays served."""
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
        # refuse: the entry stood, so the pop is an eviction: the gen moves and the held sibling is validated again
        self.assertEqual(km._subagent_tree(str(other)), ((), ()), "nothing at the root: (), () as ever")
        self.assertNotIn(str(other), km._SUBAGENT_TREES)
        self.assertEqual(km._SUBAGENT_TREES_GEN[0] - g0, 1, "the missing-root pop that removed an entry moved _SUBAGENT_TREES_GEN")
        with self._spy() as sp:
            dirs, _stats = km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], D, "the sibling tree held before the eviction is validated once more (D = %d lstats), "
                                                     "not served the pair from before it" % D)
        self.assertEqual(len(dirs), D)
        # accept: no entry stands now, so the same call moves nothing and the re-validated tree stays served
        g1 = km._SUBAGENT_TREES_GEN[0]
        self.assertEqual(km._subagent_tree(str(other)), ((), ()))
        self.assertEqual(km._SUBAGENT_TREES_GEN[0], g1, "a missing root with no entry moves no gen")
        with self._spy() as sp:
            km._subagent_tree(str(self.sub))
        self.assertEqual(sp.total()["dir_lstat"], 0, "served: nothing was evicted")
        self.assertEqual((self._delta(b)["hit"], self._delta(b)["miss"]), (2, 0), "two validated hits in the scope: before and after the eviction")


if __name__ == "__main__":
    unittest.main()
