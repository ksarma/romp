#!/usr/bin/env python3
"""The housekeeping jobs run on their own thread (2026-09-13). The pusher's cycle used to run every tick job after its push, on
one thread, so at boot the reminder walk and the interrupt tick (a cold read of every session's transcript: 24 s and 6 s on the
11:55 AM boot that decided this) held every browser frame behind a 30 to 60 s first cycle, and all day a slow job delayed the
next refresh. The user asked why the reminder walk had to finish before the UI showed at all. Now `_pusher_cycle_jobs` keeps what
feeds a frame or shares the cycle's checkpoint byte budget, `_jobs_pass` runs the rest in the order it always had on the jobs
thread (`_jobs_loop`, one pass per JOBS_PASS_S) with its own liveness snapshot, /perf keeps the two loops' splits apart (`pusher`
and `jobs`), and the boot-health row carries both firsts (`firstCycleS`, the browser's wait; `jobsFirstPassS`, the housekeeping's)."""
import inspect
import io
import json
import os
import re
import sys
import threading
import time
import types
import unittest
from unittest import mock
HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
from test_asm_checkpoint import kernel_module   # noqa: E402

JOB_NAME_RE = r"_job_stage\(['\"](\w+)['\"]"
WALK_SID = "33333333-4444-5555-6666-777777777777"   # the walk test's own synthetic session: no other module keys a memo under it

PUSHER_JOBS = ("beginCheckpointCycle", "sessionsListing", "applyPendingOps", "turnNotify", "persistCheckpoints", "convergeCheckpoints",
               "bootRowBackstop", "kernelSample", "apiHealth")
HOUSEKEEPING = ("stateRootMode",   # the state root's mode re-check (2026-09-20), first: the premise of every write in the pass
                "liftSpentAwaiting", "deathSweep", "endOnIdle", "deferralSweep",
                "unreadableStores",   # this fork's unreadable-store warn, a stage of the jobs pass since the 2026-09-15 pull-in (the rulings' item 9)
                "autoNudge", "interruptBlock",
                "persistTickSeen", "persistIntrMarks", "persistSpendTrees", "autoPauseOnLimit", "usagePoll", "autoPauseOnSpend",
                "spendGuard", "autoResumeRetry", "autoResumeSession", "autoRetry", "idleQueueDrive", "clearDoneNotes")
QUIET = ("_lift_spent_awaiting", "_death_sweep_tick", "_end_on_idle_sweep", "_deferral_sweep_tick", "_unreadable_store_warns", "_interrupt_block_tick",
         "_persist_tick_seen", "_persist_intr_marks", "_persist_spend_trees", "_auto_pause_on_limit", "_usage_poll_tick",
         "_auto_pause_on_spend_limit", "_spend_guard_tick", "_auto_resume_retry", "_auto_resume_session_retry",
         "_auto_retry_tick", "_idle_queue_drive_tick", "_clear_done_working_notes", "_turn_notify_tick", "_apply_pending_ops",
         "_persist_checkpoints", "_converge_checkpoints", "_kernel_sample_tick", "_api_health_push")


class Partition(unittest.TestCase):
    """Which job runs where, pinned by exact membership: a job added to either list must be placed on purpose."""

    def setUp(self):
        self.km = kernel_module()

    def test_the_two_lists_partition_the_jobs_census_in_the_old_order(self):
        km = self.km
        pusher = re.findall(JOB_NAME_RE, inspect.getsource(km._pusher_cycle_jobs))
        jobs = re.findall(JOB_NAME_RE, inspect.getsource(km._jobs_pass))
        self.assertEqual(tuple(pusher), PUSHER_JOBS, "the pusher keeps what feeds a frame or shares the checkpoint budget")
        self.assertEqual(tuple(jobs), HOUSEKEEPING, "the housekeeping, in the order it always ran")
        self.assertFalse(set(pusher) & set(jobs), "no job on both threads")
        self.assertEqual(set(pusher) | set(jobs), set(km._PerfStats.JOBS), "together they are the JOBS census")
        # the collector keeps the two lists by thread since 2026-09-18 (stage attribution: the pusher's nine are seeded under
        # pusher.cycleJobsMs, the jobs thread's nineteen as flat `jobs.<job>` rows), so each must be the source's, in order
        self.assertEqual(km._PerfStats.CYCLE_JOBS, PUSHER_JOBS, "CYCLE_JOBS is _pusher_cycle_jobs's list")
        self.assertEqual(km._PerfStats.PASS_JOBS, HOUSEKEEPING, "PASS_JOBS is _jobs_pass's list")
        self.assertEqual(km._PerfStats.JOBS, PUSHER_JOBS + HOUSEKEEPING, "JOBS is the census as CYCLE_JOBS + PASS_JOBS")

    def test_the_jobs_pass_keeps_its_ordering_reasons(self):
        src = inspect.getsource(self.km._jobs_pass)
        order = [src.index(s) for s in ("_lift_spent_awaiting(now, live_map)", "_deferral_sweep_tick(now)",
                                        "_auto_nudge_tick(now, live_map)", "_interrupt_block_tick(now, live_map)",
                                        "_persist_tick_seen()", "_auto_pause_on_spend_limit(now, live_map)",
                                        "_spend_guard_tick(now, live_map)", "_auto_resume_retry(now, live_map)")]
        self.assertEqual(order, sorted(order), "lift before the walk before the interrupt tick before the memo persist; "
                                               "the deferral sweep before the walk; the pause before the guard before the resume")
        self.assertIn('_PERF_STATS.jobs.get("passes", 0) >= 1', src, "the guard skips the boot's first PASS, its own loop's first")
        self.assertNotIn("_push_all", src, "the jobs thread never builds a frame")
        self.assertIn('_PERF_STATS.stage("jobsPass"', src, "the pass is its own container stage")

    def test_main_starts_the_jobs_thread_and_the_docs_list_the_kind(self):
        km = self.km
        src = inspect.getsource(km.main)
        self.assertIn('threading.Thread(target=_jobs_loop, daemon=True, name="jobs").start()', src)
        self.assertLess(src.index("_JOBS_THREAD_STARTED[0] = True"), src.index("target=_jobs_loop"),
                        "the boot row learns of the thread before its first pass can report")
        doc = open(os.path.join(os.path.dirname(HERE), "docs", "reference.md"), encoding="utf-8").read()
        self.assertIn("`jobs` (the housekeeping loop split off the pusher)", doc, "the thread kind is documented")
        self.assertIn("`jobsFirstPassS`", doc, "the boot row's second first is documented")

    def test_the_two_persisted_memos_stage_under_a_per_thread_tmp_name(self):
        km = self.km
        for fn in (km._persist_tick_seen, km._persist_spend_trees):
            src = inspect.getsource(fn)
            self.assertIn('".tmp.%d.%x" % (os.getpid(), threading.get_ident())', src,
                          "%s: the exit's force write runs beside the jobs thread's; two writers under one tmp name unlink "
                          "each other's" % fn.__name__)


class _LabCycles(unittest.TestCase):
    """A hermetic kernel module, every job quiet unless a test speaks for it, the boot row captured, the two loops' first
    marks re-armed as a fresh boot's."""

    def setUp(self):
        self.km = km = kernel_module()
        self.saved = (km.NAMES, km._live_map, km._push_all, km._append_restart_cut, km._BOOT_HEALTH_DONE[0],
                      km._JOBS_THREAD_STARTED[0], dict(km._BOOT_FIRST), km._BOOT_FIRST_CLOSED_MONO[0])
        self.saved_jobs = {nm: getattr(km, nm) for nm in QUIET}
        for nm in QUIET:
            setattr(km, nm, lambda *a, **k: None)
        km.NAMES = {}
        km._live_map = lambda: {}
        km._push_all = lambda live_map=None: None
        self.rows = []
        km._append_restart_cut = lambda row: self.rows.append(row)
        km._BOOT_HEALTH_DONE[0] = False
        km._JOBS_THREAD_STARTED[0] = False
        km._BOOT_FIRST.update({"pusher": None, "jobs": None})
        km._BOOT_FIRST_CLOSED_MONO[0] = None
        self.saved_samplers = (dict(km._FIRST_CYCLE_SAMPLER), dict(km._FIRST_PASS_SAMPLER))
        for slot in (km._FIRST_CYCLE_SAMPLER, km._FIRST_PASS_SAMPLER):
            slot.update({"started": False, "stop": threading.Event(), "rows": [], "thread": None, "failed": 0})
        km._PERF_STATS.reset()

    def tearDown(self):
        km = self.km
        (km.NAMES, km._live_map, km._push_all, km._append_restart_cut, km._BOOT_HEALTH_DONE[0],
         km._JOBS_THREAD_STARTED[0], first, km._BOOT_FIRST_CLOSED_MONO[0]) = self.saved
        km._BOOT_FIRST.update(first)
        for nm, fn in self.saved_jobs.items():
            setattr(km, nm, fn)
        for slot, saved in zip((km._FIRST_CYCLE_SAMPLER, km._FIRST_PASS_SAMPLER), self.saved_samplers):
            slot.clear(); slot.update(saved)
        km._PERF_STATS.reset()


class TheBrowserNeverWaitsOnTheHousekeeping(_LabCycles):
    def test_a_slow_housekeeping_job_lengthens_the_jobs_pass_and_not_the_pusher_cycle(self):
        """The change itself: the reminder walk sleeping 0.4 s costs the jobs pass 0.4 s and the pusher's cycle nothing. At
        the base the walk ran inside the pusher's cycle, so the cycle carried the sleep."""
        km = self.km
        calls = []
        self.addCleanup(setattr, km, "_auto_nudge_tick", km._auto_nudge_tick)   # the real tick, captured BEFORE the stub: the lab
        #                                                                        kernel is one object for the process, and a cleanup that
        #                                                                        read the attribute after the assignment restored the stub
        km._auto_nudge_tick = lambda now, live_map: (calls.append(1), time.sleep(0.4))
        t0 = time.monotonic(); km._pusher_cycle(); cycle = time.monotonic() - t0
        self.assertEqual(calls, [], "the pusher's cycle ran no walk")
        self.assertLess(cycle, 0.3, "and did not carry its sleep: %.3f s" % cycle)
        t0 = time.monotonic(); km._jobs_cycle(); pas = time.monotonic() - t0
        self.assertEqual(calls, [1], "the jobs pass ran it once")
        self.assertGreaterEqual(pas, 0.4)
        snap = km._PERF_STATS.snapshot()
        self.assertEqual(snap["jobs"]["passes"], 1, "counted under /perf jobs, not pusher")
        self.assertEqual(snap["pusher"]["cycles"], 1)
        self.assertGreaterEqual(snap["stages_ms"]["jobs.autoNudge"], 400.0)
        self.assertLess(snap["pusher"]["cycle_ms_max"], 300.0, "the pusher's own ring never saw the sleep")

    def test_the_jobs_pass_has_its_own_split_and_scope(self):
        km = self.km
        reads = []

        def fake(who):                                    # a thread clock that advances one ms of user, half a ms of sys per read
            reads.append(who)
            return types.SimpleNamespace(ru_utime=0.001 * len(reads), ru_stime=0.0005 * len(reads), ru_maxrss=0)
        with mock.patch.object(km, "_RUSAGE_THREAD", 11), mock.patch.object(km.resource, "getrusage", fake):
            km._jobs_cycle()
            snap = km._PERF_STATS.snapshot()
        # the pass container's thread CPU (stages_cpu_ms; 2026-09-18 review, medium 8): its open and close reads apart
        cpu = snap["stages_cpu_ms"]["jobsPass"]
        self.assertGreaterEqual(cpu["user"], 1.0 - 1e-6, "the pass's CPU row moved: at least its own read pair apart")
        self.assertAlmostEqual(cpu["sys"], cpu["user"] / 2.0, places=6, msg="the fake's ratio survives the fold")
        first = snap["jobs"]["firstPass"]
        self.assertIsNotNone(first, "the boot's first pass's split is kept under jobs.firstPass")
        self.assertIn("jobsPass", first["stages"], sorted(first["stages"]))
        self.assertIn("jobs.prelude", first["stages"])
        self.assertTrue(any(k.startswith("jobs.") and k != "jobs.prelude" for k in first["stages"]), "the jobs as sub-stages")
        self.assertIsNone(snap["pusher"]["firstCycle"], "the pusher's split is untouched by the jobs thread's pass")
        self.assertEqual(snap["jobs"]["stageRingLen"], 1)
        for k in ("pass_ms_p50", "pass_ms_p90", "pass_ms_ring_max", "passFailed", "splitFailed"):
            self.assertIn(k, snap["jobs"], k)
        self.assertIn("jobsPass", snap["stages_ms"]); self.assertIn("jobs.prelude", snap["stages_ms"])
        self.assertIsNone(km._live_scope.snapshot, "the pass closes its scope")
        self.assertIsNone(km._live_scope.names)

    def test_the_nudge_walk_names_its_parts_on_the_pass_split(self):
        """plans/nudge-walk-events.md, the measurement's first step: the walk's key stats, its snapshot reads and its looks are
        sub-stages of jobs.autoNudge on the pass's split, so a pass that spikes names what it paid; the parts sum to at most
        the job."""
        km = self.km
        # the pass body directly, under the job's own stage: a test earlier in this module leaves a pass in flight on a blocked
        # thread, and the tick's single-flight guard would stand this walk down
        now = int(time.time())
        km._PERF_STATS.cycle_begin("jobs")                 # this thread stands for the jobs thread: a `jobs.` stage is the flat row's
        #                                                    by its writer's owner (2026-09-18), and a thread owning no loop
        #                                                    would count under stagesForeign instead
        km._job_stage("autoNudge", lambda: km._auto_nudge_pass(now, km._live_map(), False))
        snap = km._PERF_STATS.snapshot()
        st = snap["stages_ms"]
        have = sorted(k for k in st if k.startswith("jobs.autoNudge"))
        self.assertEqual(have, ["jobs.autoNudge", "jobs.autoNudge.key", "jobs.autoNudge.looks", "jobs.autoNudge.snapshot"], have)
        parts = sum(st[k] for k in st if k.startswith("jobs.autoNudge."))
        self.assertLessEqual(parts, st["jobs.autoNudge"] + 1.0, "the parts sum to at most the job")
        self.assertEqual(snap["stagesForeign"], {}, "the walk ran as the jobs owner: nothing foreign")

    def test_the_dashboards_act_now_pass_is_the_writer_of_stages_foreign(self):
        """The one writer of stagesForeign on a running kernel (2026-09-18 review): the dashboard's setAutoNudge and
        setCompactSuggest arms run the nudge pass on the WS handler thread (_ws_act_now_tick), which owns neither loop, so
        the pass's parts are counted there under their stage names and move neither the flat jobs.autoNudge rows (the jobs
        thread's) nor pusher.cycleJobsMs (the pusher's). The reference and the collector's docstring name this writer; an
        earlier reading had the block empty on a running kernel."""
        km = self.km
        before = km._PERF_STATS.snapshot()
        done = threading.Event()

        def handler_thread():                                  # a WS handler's: no cycle_begin on it
            try:
                km._ws_act_now_tick()
            finally:
                done.set()
        # single-flight against nothing here: the tick stands down when a pass is in flight, and a module sharing this lab
        # kernel can leave one on a blocked thread; the guard itself is pinned in tests/test_dead_wait_block.py
        with mock.patch.object(km, "_AUTO_NUDGE_TICK_LOCK", threading.Lock()):
            th = threading.Thread(target=handler_thread); th.start(); th.join(30)
        self.assertTrue(done.is_set(), "the act-now pass ran")
        snap = km._PERF_STATS.snapshot()
        self.assertEqual(sorted(snap["stagesForeign"]), ["jobs.autoNudge.key", "jobs.autoNudge.looks", "jobs.autoNudge.snapshot"],
                         "the pass's parts, from a thread owning neither loop (no session alive, so no parse)")
        self.assertEqual(snap["stages_ms"]["jobs.autoNudge"], before["stages_ms"]["jobs.autoNudge"], "the flat row is the jobs thread's")
        self.assertFalse([k for k in snap["stages_ms"] if k.startswith("jobs.autoNudge.")], "no part reached a flat row")
        self.assertEqual(snap["pusher"]["cycleJobsMs"], before["pusher"]["cycleJobsMs"], "nor the pusher's block")
        self.assertEqual((snap["jobs"]["passes"], snap["pusher"]["cycles"]), (0, 0), "no cycle opened: the handler's own thread")

    def test_the_looks_mark_excludes_the_parses_for_a_writer_owning_no_loop(self):
        """jobs.autoNudge.looks is the loop's wall outside the parses for every writer (2026-09-18 review). The pass read the
        parses' wall off the FLAT jobs.autoNudge.parse row before and after the loop, and that row moves for the jobs owner
        alone since the routing, so the act-now pass on the WS handler thread (stagesForeign) and a pusher-owner walk got a
        zero delta and a looks mark that carried every parse a second time. The walk now tallies its parses on the walking
        thread (_NUDGE_HORIZON.parse_s). Driven here with no owner and one session whose parse sleeps: the four parts
        partition the job in the writer's block."""
        km = self.km
        now = int(time.time())
        row = {"sid": WALK_SID, "path": "/nonexistent/transcript.jsonl", "name": "web", "mtime": now}

        def slow_parse(sid, paths, now_):
            time.sleep(0.05)
            return {"turns": []}                                 # the look returns at the parse: nothing else to walk

        def forget_memo():                                       # the look records its memo under the sid; the lab keeps none
            with km._TICK_SEEN_LOCK:
                for key in [k for k in km._TICK_SEEN if isinstance(k, tuple) and WALK_SID in k]:
                    km._TICK_SEEN.pop(key, None)
        self.addCleanup(forget_memo)
        out = {}

        def walker():                                            # a thread owning neither loop
            try:
                km._job_stage("autoNudge", lambda: km._auto_nudge_pass(now, {}, False))
            except BaseException as e:                           # noqa: BLE001
                out["err"] = e
        with mock.patch.multiple(km, _alive_sessions=lambda now, live_map: [row], _session_flag=lambda sid, flag: False,
                                 _compacting_now=lambda *a, **k: False, _api_error=lambda path: False), \
             mock.patch.object(km.jd, "parsed_session", side_effect=slow_parse):
            th = threading.Thread(target=walker); th.start(); th.join(30)
        self.assertFalse(th.is_alive(), "the walk returned")
        self.assertNotIn("err", out, repr(out.get("err")))
        fx = km._PERF_STATS.snapshot()["stagesForeign"]
        self.assertEqual(sorted(fx), ["jobs.autoNudge", "jobs.autoNudge.key", "jobs.autoNudge.looks", "jobs.autoNudge.parse",
                                      "jobs.autoNudge.snapshot"], fx)
        self.assertGreaterEqual(fx["jobs.autoNudge.parse"], 50.0, "the session paid the parse: %r" % fx)
        parts = sum(v for k, v in fx.items() if k.startswith("jobs.autoNudge."))
        self.assertLessEqual(parts, fx["jobs.autoNudge"] + 1.0, "the parts partition the job, the parse counted once: %r" % fx)

    def test_a_loop_body_on_a_thread_owning_the_other_loops_cycle_takes_the_owner_over(self):
        """The guard at the top of each loop body (2026-09-18 review): a thread that owns the OTHER loop's cycle flips to this
        loop's, so the body's jobs are credited to this loop. Before, the guard opened a cycle only for a thread owning none,
        so a test driving both bodies on one thread kept the first owner through the second body and the nine cycle jobs
        landed in the flat jobs.<job> rows, the merge stage()'s routing exists to end. The running kernel's two loop threads
        never meet this: each loop function opens its own cycle before its body."""
        km = self.km
        now = int(time.time())
        km._jobs_pass(now, {})                                   # this thread is the jobs owner
        self.assertEqual(km._PERF_STATS._mine(), "jobs")
        km._pusher_cycle_jobs(now, {}, False)                    # the pusher's body: the thread flips to its owner
        self.assertEqual(km._PERF_STATS._mine(), "pusher")
        snap = km._PERF_STATS.snapshot()
        st, cyc = snap["stages_ms"], snap["pusher"]["cycleJobsMs"]
        self.assertFalse({"jobs." + j for j in PUSHER_JOBS} & set(st),
                         "no cycle job's row in stages_ms: %r" % sorted(k for k in st if k.startswith("jobs.")))
        self.assertEqual(sorted(cyc), sorted(PUSHER_JOBS))
        self.assertGreater(sum(cyc.values()), 0.0, "the nine were credited to the pusher's block")
        for j in HOUSEKEEPING:
            self.assertIn("jobs." + j, st, j)
        self.assertEqual(snap["stagesForeign"], {})
        km._jobs_pass(now, {})                                   # and back: the jobs' body takes the owner from the pusher
        self.assertEqual(km._PERF_STATS._mine(), "jobs")
        snap = km._PERF_STATS.snapshot()
        self.assertEqual(snap["pusher"]["cycleJobsMs"], cyc, "the second pass added nothing to the pusher's block")
        self.assertGreater(snap["stages_ms"]["jobsPass"], st["jobsPass"], "and its pass went to the flat rows")

    def test_a_run_of_both_loops_keeps_each_threads_job_rows_apart(self):
        """The real _pusher_cycle and _jobs_cycle, every job quiet: the nine cycle jobs' walls land under pusher.cycleJobsMs
        and sum to at most the pusher's `jobs` container, the nineteen housekeeping jobs' land in the flat `jobs.<job>` rows
        and sum to at most `jobsPass`, no cycle job's key is in stages_ms, and nothing is foreign. Each sum is a set of
        disjoint intervals inside its container's, so the bound is exact, not a ratio (the ratio tests here were coin
        tosses under load)."""
        km = self.km
        km._pusher_cycle(); km._jobs_cycle()
        snap = km._PERF_STATS.snapshot()
        st, cyc = snap["stages_ms"], snap["pusher"]["cycleJobsMs"]
        self.assertEqual(sorted(cyc), sorted(PUSHER_JOBS), "exactly the nine, whether or not a job took measurable time")
        self.assertFalse({"jobs." + j for j in PUSHER_JOBS} & set(st), "no cycle job's row in stages_ms")
        for j in HOUSEKEEPING:
            self.assertIn("jobs." + j, st, j)
        self.assertLessEqual(sum(cyc.values()), st["jobs"] + 1e-6, "the cycle jobs against the pusher's jobs container")
        self.assertLessEqual(sum(st["jobs." + j] for j in HOUSEKEEPING), st["jobsPass"] + 1e-6, "the housekeeping against the pass")
        self.assertGreater(st["jobsPass"], 0.0); self.assertGreater(st["jobs"], 0.0)
        self.assertEqual(snap["stagesForeign"], {})
        self.assertEqual(snap["jobs"]["passes"], 1); self.assertEqual(snap["pusher"]["cycles"], 1)

    def test_the_stats_keep_two_owners_apart(self):
        """A stage closed on the jobs thread lands in the jobs split and never in the pusher's, and the other way round. The
        cumulative rows are each writer's own since 2026-09-18 (a flat `jobs.` row the jobs thread's, a flat push row the
        pusher's, a connect push's push.chat under pusher.connectPush.stagesMs and not in the flat row), where they took
        every writer's before: the flat push.chat read 30 ms under the fold, the pusher's 10 and the connect thread's 20."""
        km = self.km
        ps = km._PerfStats()
        ps.cycle_begin()                                              # this thread is the pusher
        ps.stage("push.chat", 0.010); ps.stage("push", 0.010)
        done = threading.Event()
        def jobs_thread():
            ps.cycle_begin("jobs")
            ps.stage("jobs.autoNudge", 0.020); ps.stage("jobsPass", 0.020)
            ps.jobs_pass(0.021)
            done.set()
        th = threading.Thread(target=jobs_thread); th.start(); th.join(5)
        self.assertTrue(done.is_set())
        connected = threading.Event()
        def connect_thread():                                         # a fresh client's handler thread: no cycle, _push's "connect" mark
            km._stage_marked("connect")(lambda: ps.stage("push.chat", 0.020))()
            connected.set()
        th = threading.Thread(target=connect_thread); th.start(); th.join(5)
        self.assertTrue(connected.is_set())
        ps.stage("jobs.apiHealth", 0.001); ps.stage("jobs", 0.001)
        ps.cycle(0.012)
        snap = ps.snapshot()
        self.assertEqual(sorted(snap["pusher"]["firstCycle"]["stages"]), ["jobs", "jobs.apiHealth", "push", "push.chat"])
        self.assertEqual(sorted(snap["jobs"]["firstPass"]["stages"]), ["jobs.autoNudge", "jobsPass"])
        self.assertAlmostEqual(snap["jobs"]["firstPass"]["stages"]["jobsPass"]["ms"], 20.0)
        self.assertAlmostEqual(snap["stages_ms"]["jobs.autoNudge"], 20.0, msg="the flat row takes the jobs thread's job")
        # the pusher's `jobs.apiHealth` (2026-09-18): its split row as before, its cumulative wall under pusher.cycleJobsMs
        # and not in stages_ms, which holds no cycle job's key since the change
        self.assertAlmostEqual(snap["pusher"]["firstCycle"]["stages"]["jobs.apiHealth"]["ms"], 1.0)
        self.assertAlmostEqual(snap["pusher"]["cycleJobsMs"]["apiHealth"], 1.0)
        self.assertNotIn("jobs.apiHealth", snap["stages_ms"])
        # the pusher's push stages (2026-09-18): the flat rows are its own by its ownership of the cycle, exact
        self.assertAlmostEqual(snap["stages_ms"]["push.chat"], 10.0, msg="the pusher's push.chat, the flat row (30.0 under the fold)")
        self.assertAlmostEqual(snap["stages_ms"]["push"], 10.0)
        self.assertEqual(snap["pusher"]["connectPush"]["stagesMs"], {"push.chat": 20.0}, "the connect thread's, apart")
        self.assertEqual(snap["stagesForeign"], {}, "every writer had an owner or a purpose")
        self.assertEqual(ps._mine(), "pusher")
        self.assertEqual(snap["jobs"]["passes"], 1)
        self.assertEqual(snap["pusher"]["cycles"], 1)


class TheBootRowCarriesBothFirsts(_LabCycles):
    def test_with_the_jobs_thread_started_the_row_waits_for_the_later_first(self):
        km = self.km
        km._JOBS_THREAD_STARTED[0] = True
        km._pusher_cycle()
        self.assertEqual(self.rows, [], "the pusher's first cycle alone writes no row: the jobs pass is still open")
        self.assertFalse(km._BOOT_HEALTH_DONE[0])
        self.addCleanup(setattr, km, "_auto_nudge_tick", km._auto_nudge_tick)   # captured before the stub (see the slow-job test)
        km._auto_nudge_tick = lambda now, live_map: time.sleep(0.05)
        km._jobs_cycle()
        self.assertEqual(len(self.rows), 1, "the jobs thread's first pass, the later of the two, wrote it")
        row = self.rows[0]
        self.assertTrue(row["bootHealth"])
        self.assertIn("firstCycleS", row); self.assertIn("slow", row)
        self.assertIn("jobsFirstPassS", row); self.assertIn("jobsSlow", row)
        self.assertGreaterEqual(row["jobsFirstPassS"], 0.05)
        self.assertIn("prelude", row["stages"], "the pusher's split rides the row")
        self.assertIn("jobsPass", row["stages"], "and the jobs thread's")
        self.assertIn("jobs.autoNudge", row["stages"])
        self.assertIsInstance(row["firstCycleStacks"], list)
        self.assertIsInstance(row["firstPassStacks"], list, "the jobs thread's first pass was sampled too")
        self.assertNotIn("jobsFirstPassPending", row)
        self.assertTrue(km._BOOT_HEALTH_DONE[0])
        self.assertEqual(km._BOOT_FIRST, {"pusher": None, "jobs": None}, "the firsts are cleared once the row is written")
        km._pusher_cycle(); km._jobs_cycle()
        self.assertEqual(len(self.rows), 1, "later cycles and passes write nothing")

    def test_whichever_loop_finishes_its_first_last_writes_the_row(self):
        km = self.km
        km._JOBS_THREAD_STARTED[0] = True
        km._jobs_cycle()
        self.assertEqual(self.rows, [], "the jobs pass first: the row waits for the pusher")
        km._pusher_cycle()
        self.assertEqual(len(self.rows), 1)
        self.assertIn("jobsFirstPassS", self.rows[0]); self.assertIn("firstCycleS", self.rows[0])

    def test_without_a_jobs_thread_the_pushers_first_cycle_writes_the_row_at_once(self):
        """A test driving one cycle, or a kernel whose main never started the thread: the old contract holds."""
        km = self.km
        km._pusher_cycle()
        self.assertEqual(len(self.rows), 1)
        self.assertIn("firstCycleS", self.rows[0])
        self.assertNotIn("jobsFirstPassS", self.rows[0])
        self.assertNotIn("firstPassStacks", self.rows[0], "no jobs thread, no second sample list")
        self.assertIsNone(km._boot_health_first_cycle(0.1), "the second cycle is not the boot's first")

    def test_a_jobs_pass_that_never_ends_still_leaves_a_row_by_the_backstop(self):
        km = self.km
        km._JOBS_THREAD_STARTED[0] = True
        km._pusher_cycle()
        self.assertEqual(self.rows, [])
        self.assertIsNone(km._boot_health_row_backstop(time.monotonic()), "well inside the bound: nothing yet")
        with mock.patch.object(km, "BOOT_JOBS_PASS_ROW_BACKSTOP_S", 0.0):
            km._pusher_cycle()                                        # a later cycle runs the backstop
        self.assertEqual(len(self.rows), 1, "the row without the jobs pass")
        row = self.rows[0]
        self.assertTrue(row.get("jobsFirstPassPending"))
        self.assertIn("firstCycleS", row); self.assertNotIn("jobsFirstPassS", row)
        self.assertTrue(km._BOOT_HEALTH_DONE[0])
        km._jobs_cycle()
        self.assertEqual(len(self.rows), 1, "the late pass writes no second row")

    def test_the_slow_lines_name_their_thread(self):
        km = self.km
        km._JOBS_THREAD_STARTED[0] = True
        err = io.StringIO()
        with mock.patch.object(km, "BOOT_FIRST_CYCLE_BOUND_S", 0.0), mock.patch.object(km.sys, "stderr", err):
            km._pusher_cycle(); km._jobs_cycle()
        self.assertIn("the first pusher cycle took", err.getvalue())
        self.assertIn("the first housekeeping pass took", err.getvalue())
        self.assertIn("the browser did not wait on it", err.getvalue())


class TheBootRowCarriesEachSplitsGcDelta(_LabCycles):
    """The row's `gc`: each first split's collector delta on its own, `firstCycle` and `firstPass`, never summed (the tallies
    are process-wide, so a collection inside both windows is in both deltas and a sum would count it twice), absent when
    neither split has one (review round)."""

    def _row_with(self, cyc, pas):
        km = self.km
        km._BOOT_FIRST.update({"pusher": 0.5, "jobs": 0.7})
        with mock.patch.object(km._PERF_STATS, "first_cycle_split", return_value=cyc), \
             mock.patch.object(km._PERF_STATS, "first_pass_split", return_value=pas):
            row = km._boot_health_row()
        self.assertEqual(self.rows, [row])
        return row

    def test_both_deltas_ride_the_row_unsummed(self):
        cyc_gc = {"n0": 3, "n1": 1, "n2": 1, "ms2": 12.5}            # one full collection inside the pusher's window...
        pas_gc = {"n0": 5, "n1": 1, "n2": 1, "ms2": 12.5}            # ...and inside the jobs pass's, which overlapped it
        cyc = {"s": 0.5, "t": 1.0, "gc": cyc_gc,
               "stages": {"push": {"ms": 400.0, "bytes": 0, "hydrated": 0}, "jobs.other": {"ms": 10.0, "bytes": 0, "hydrated": 0}}}
        pas = {"s": 0.7, "t": 1.2, "gc": pas_gc,
               "stages": {"jobsPass": {"ms": 700.0, "bytes": 0, "hydrated": 0}, "jobs.other": {"ms": 5.0, "bytes": 0, "hydrated": 0}}}
        row = self._row_with(cyc, pas)
        self.assertEqual(row["gc"], {"firstCycle": cyc_gc, "firstPass": pas_gc})
        self.assertEqual(row["gc"]["firstCycle"]["n2"] + row["gc"]["firstPass"]["n2"], 2,
                         "the same collection in both windows: a sum would have said two")
        self.assertEqual(row["stages"]["jobs.other"]["ms"], 15.0, "a stage key both own is still summed; the gc deltas are not")
        json.dumps(row)

    def test_a_split_without_a_delta_reads_null_beside_the_others(self):
        cyc = {"s": 0.5, "t": 1.0, "stages": {}, "gc": None}          # closed without an opening mark
        pas = {"s": 0.7, "t": 1.2, "stages": {}, "gc": {"n0": 2, "n1": 0, "n2": 0, "ms2": 0.0}}
        row = self._row_with(cyc, pas)
        self.assertEqual(row["gc"], {"firstCycle": None, "firstPass": {"n0": 2, "n1": 0, "n2": 0, "ms2": 0.0}})

    def test_no_delta_in_either_split_leaves_the_key_off(self):
        row = self._row_with({"s": 0.5, "t": 1.0, "stages": {}, "gc": None}, None)   # and no jobs pass at all
        self.assertNotIn("gc", row)
        self.assertNotIn("stages", row)

    def test_a_driven_boot_carries_the_deltas_from_the_real_splits(self):
        km = self.km
        km._JOBS_THREAD_STARTED[0] = True
        km._pusher_cycle(); km._jobs_cycle()
        row = self.rows[0]
        self.assertEqual(set(row["gc"]), {"firstCycle", "firstPass"})
        for k in ("firstCycle", "firstPass"):
            self.assertEqual(set(row["gc"][k]), {"n0", "n1", "n2", "ms2"}, k)


class TheJobsLoop(_LabCycles):
    def test_a_pass_that_raises_is_counted_and_the_loop_goes_on(self):
        km = self.km
        n = [0]
        def cycle():
            n[0] += 1
            if n[0] <= 2:
                raise RuntimeError("no thread slot")
            km._LOOPS_STOP.set()
        err = io.StringIO()
        saved_stop = km._LOOPS_STOP.is_set()
        with mock.patch.object(km, "_jobs_cycle", cycle), mock.patch.object(km, "_JOBS_FAILED_SAID", {}), \
             mock.patch.object(km.sys, "stderr", err), mock.patch.dict(km._PERF_STATS.jobs, {"passFailed": 0}), \
             mock.patch.object(km, "PUSHER_FAIL_BACKOFF_S", (0.01, 0.01, 0.01, 0.01)):
            try:
                km._jobs_loop()
                self.assertEqual(n[0], 3, "two raising passes were skipped and the third ran")
                self.assertEqual(km._PERF_STATS.jobs["passFailed"], 2)
            finally:
                if not saved_stop:
                    km._LOOPS_STOP.clear()
        self.assertEqual(err.getvalue().count("jobs: a pass raised RuntimeError"), 1, "said once per kind: %r" % err.getvalue())
        self.assertIn("passFailed", km._PERF_STATS.snapshot()["jobs"])

    def test_the_loop_paces_at_the_pushers_backstop_and_stops_with_the_loops(self):
        km = self.km
        self.assertEqual(km.JOBS_PASS_S, 0.5)
        n = [0]
        def cycle():
            n[0] += 1
            if n[0] == 2:
                km._LOOPS_STOP.set()
        saved_stop = km._LOOPS_STOP.is_set(); km._LOOPS_STOP.clear()
        t0 = time.monotonic()
        try:
            with mock.patch.object(km, "_jobs_cycle", cycle), mock.patch.object(km, "JOBS_PASS_S", 0.05):
                km._jobs_loop()
        finally:
            if saved_stop: km._LOOPS_STOP.set()
            else: km._LOOPS_STOP.clear()
        self.assertEqual(n[0], 2)
        self.assertGreaterEqual(time.monotonic() - t0, 0.05, "one pace between the two passes")


if __name__ == "__main__":
    unittest.main()
