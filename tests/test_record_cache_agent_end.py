#!/usr/bin/env python3
"""A finished agent's parsed transcript leaves the record cache at the agent's end (2026-09-24).

The kernel folds a running agent's transcript within seconds of each append (the awaiting rows attribute a background
command through it, the agent head steps it), so the quiescent drop, which pops only at a fold that steps records over a
file unchanged for 120 s, never fires for it; after the agent ends every fold is a hit, which never pops, and the whole
entry stayed until the count cap evicted it. On a long-lived kernel those entries were most of the cache's non-leaf held
bytes. The SDK backend knows the end exactly: the agent leaves its session's live set on SubagentStop, its own task's end,
its workflow slot's done or error state, a re-minted slot, the run's end, the CLI's reconnect teardown, or the CLI's end (a
kill, a crash; not a detach, where the CLI lives on under its host). Each of those removals
queues the agent; the pusher drains the queue at its next cycle's start and releases the agent's entry after writing the
file's checkpoint document, so a later fold restores a zero-weight tail instead of reading the file whole.

Synthetic data only: a notes-api project under a temp root, placeholder ids, a private sid, hostname TESTHOST.
"""
import asyncio
import contextlib
import io
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp(prefix="agent-end-state-")   # hermetic state BEFORE the load
os.environ.pop("ROMP_STATE_DIR", None)
km = load_source("romp_kernel_agent_end", os.path.join(BIN, "romp-kernel"))
em, jd = km.em, km.jd
sb = load_source("romp_sdk_backend_agent_end", os.path.join(BIN, "romp_sdk_backend.py"))
jd.STATE.mkdir(parents=True, exist_ok=True)
(jd.STATE / "session-hosts").write_text("off\n")   # this module mints its own state root: no per-session host

SID = "11111111-2222-3333-4444-a9e7e1d0c0de"          # a private synthetic sid
OTHER_SID = "11111111-2222-3333-4444-a9e7e1d0c0df"    # a second one, for an event whose resolution raises
AID = "a0123456789abcdef"                              # an agent id in the hook's shape (a + 16 hex)
WF_AID = "afedcba9876543210"                           # a workflow agent
WF_AID2 = "a2222222222222222"                          # the slot's retried attempt
WF_TID = "w0000000000000001"                           # the workflow run's task id
AID3 = "a3333333333333333"                             # a third agent, for a cycle that must still drain its end
LAUNCH = "toolu_notesapi_bg_tests"                     # the agent's run_in_background Bash: the pending command the rows attribute


def _agent_lines(aid, start, n):
    out = []
    for i in range(start, start + n):
        ts = "2026-09-24T10:%02d:%02d.000Z" % (i // 60 % 60, i % 60)
        use = LAUNCH if i == 0 else "toolu_%s_%04d" % (aid[-4:], i)
        base = {"sessionId": SID, "agentId": aid, "isSidechain": True, "timestamp": ts, "cwd": "/home/TESTHOST/notes-api"}
        out.append(dict(base, type="assistant", uuid="11111111-2222-3333-4444-%012d" % (2 * i), message={
            "role": "assistant", "content": [
                {"type": "text", "text": "Checking the notes-api route for field %d before the migration runs." % i},
                {"type": "tool_use", "id": use, "name": "Bash",
                 "input": {"command": "pytest -q tests/test_notes_api.py", "run_in_background": use == LAUNCH}}]}))
        out.append(dict(base, type="user", uuid="11111111-2222-3333-4444-%012d" % (2 * i + 1), message={
            "role": "user", "content": [
                {"type": "tool_result", "tool_use_id": use, "content": "notes-api: 12 passed, schema unchanged. " * 8}]}))
    return out


def _append(path, recs):
    with open(path, "a", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")


def _wf(index, aid, state):
    return {"type": "workflow_agent", "index": index, "agentId": aid, "state": state}


class AgentEnd(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="agent-end-")
        proj = os.path.join(self.root, "projects", "-home-TESTHOST-notes-api")
        self.leaf = os.path.join(proj, SID + ".jsonl")
        sub = os.path.join(proj, SID, "subagents")
        self.agent = os.path.join(sub, "agent-%s.jsonl" % AID)
        self.wf_agent = os.path.join(sub, "workflows", "wf_notesapi01", "agent-%s.jsonl" % WF_AID)
        os.makedirs(os.path.dirname(self.wf_agent))
        _append(self.leaf, [{"type": "user", "uuid": "11111111-2222-3333-4444-000000000001", "sessionId": SID,
                             "timestamp": "2026-09-24T09:59:00.000Z",
                             "message": {"role": "user", "content": "Run the notes-api tests in the background."}}])
        _append(self.agent, _agent_lines(AID, 0, 40))
        _append(self.wf_agent, _agent_lines(WF_AID, 0, 40))
        self.ckdir = os.path.join(self.root, "checkpoints")
        em.set_checkpoint_dir(lambda: Path(self.ckdir))   # the harnesses' fresh-process setter: pending, dirty and owed tables clear
        em._JSONL_CACHE.clear(); em._JSONL_CACHE_BYTES[0] = 0
        for k in list(em._RECORD_CACHE_STATS):
            em._RECORD_CACHE_STATS[k] = 0
        getattr(em, "_JSONL_CACHE_BYTES_MAX", [0])[0] = 0
        getattr(em, "_RELEASED_MARKS", {}).clear()
        getattr(em, "_RELEASE_LOST_SAID", set()).clear()
        getattr(km, "_AGENT_RELEASED", {}).clear()
        km._AGENT_LAUNCH_IDS_CACHE.clear(); km._AGENT_GIST_CACHE.clear()
        self._saved = {n: getattr(km, n) for n in ("_bg_live_norm", "_bg_pending", "_path_of", "_sdk_backend",
                                                   "CKPT_CONVERGE_MS", "CKPT_CONVERGE_BYTES")}
        km._bg_live_norm = lambda sid, path, live=None: (
            [{"tid": LAUNCH, "desc": "run the notes-api tests", "t": 100, "type": "local_bash"}] if sid == SID else [])
        km._bg_pending = lambda sid, path, tasks: tasks
        km._path_of = lambda sid, now=None: self.leaf if sid == SID else None
        km.CKPT_CONVERGE_MS, km.CKPT_CONVERGE_BYTES = 150.0, 8 * 1024 * 1024
        self.state = os.path.join(self.root, "sdk-state")
        os.makedirs(self.state)
        with open(os.path.join(self.state, "session-hosts"), "w") as f:
            f.write("off\n")
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None)
        self.s = sb.SdkSession(self.be, {"sid": SID, "name": "api", "cwd": self.root})
        km._sdk_backend = self.be

    def tearDown(self):
        for n, v in self._saved.items():
            setattr(km, n, v)
        em.set_checkpoint_dir(lambda: jd.STATE / "checkpoints")
        em._JSONL_CACHE.clear(); em._JSONL_CACHE_BYTES[0] = 0
        shutil.rmtree(self.root, ignore_errors=True)

    # ---- helpers ----

    def _start(self, aid):
        asyncio.run(self.s._subagent_start_hook({"agent_id": aid, "agent_type": "general-purpose"}, None, None))

    def _stop(self, aid):
        asyncio.run(self.s._subagent_stop_hook({"agent_id": aid}, None, None))

    def _ent(self, path):
        with em._JSONL_CACHE_LOCK:
            return em._JSONL_CACHE.get(path)

    def _weight(self, path):
        ent = self._ent(path)
        return None if ent is None else em._entry_weight(ent)

    def _whole_reads(self):
        return sum(v["count"] for v in em.record_cache_stats()["wholeReads"].values())

    def _stat(self, key, default=None):
        return em.record_cache_stats().get(key, default)

    def _fold_while_running(self, aid, path):
        """The kernel folds the running agent's file the way it does in production: the snapshot lists the agent live, the
        rows attribute the pending background command through the agent's own launches (_awaiting_nest ->
        _agent_launch_ids), and the agent head steps it (_agent_steps). The agent appends between the two passes."""
        self._start(aid)
        km._awaiting_live_rows(SID, self.leaf, self.s.snapshot())
        _append(path, _agent_lines(aid, 40, 5))
        km._awaiting_live_rows(SID, self.leaf, self.s.snapshot())
        km._agent_steps(path)
        ent = self._ent(path)
        self.assertIsNotNone(ent, "precondition: the running agent's file is in the cache")
        self.assertEqual((ent[5], em._entry_weight(ent)), (0, os.path.getsize(path)), "precondition: whole, weighing its file")
        return os.path.getsize(path)

    def _released_at_the_end(self, aid, path, end):
        size = self._fold_while_running(aid, path)
        held = self._stat("bytes")
        end()
        self.assertNotIn(aid, self.s._subagents, "the agent left the live set")
        km._begin_checkpoint_cycle()                                     # the pusher's next cycle begins
        ent = self._ent(path)
        self.assertTrue(ent is None or em._entry_weight(ent) == 0,
                        "the finished agent's records left the cache (held: base %s, weight %s of %d)"
                        % (ent and ent[5], ent and em._entry_weight(ent), size))
        self.assertEqual(self._stat("bytes"), held - size, "the held bytes fell by the file's size")
        self.assertTrue(em._ckpt_file(path).exists(), "its checkpoint document was written")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}})
        return size

    # ---- the defect: every road out of the live set releases the entry ----

    def test_an_agent_folded_while_it_ran_is_released_at_its_stop_hook(self):
        self._released_at_the_end(AID, self.agent, lambda: self._stop(AID))

    def test_an_agent_folded_while_it_ran_is_released_at_its_own_task_end(self):
        self._released_at_the_end(AID, self.agent,
                                  lambda: self.s._on_task_event("task_notification", {"task_id": AID, "status": "completed"}))

    def test_a_workflow_agent_is_released_when_its_slot_reports_done(self):
        self.s._on_task_event("task_started", {"task_id": WF_TID, "task_type": "local_workflow"})
        self._released_at_the_end(WF_AID, self.wf_agent, lambda: self.s._on_task_event(
            "task_progress", {"task_id": WF_TID, "workflow_progress": [_wf(1, WF_AID, "done")]}))

    def test_a_workflow_agent_is_released_when_its_slot_is_re_minted(self):
        self.s._on_task_event("task_started", {"task_id": WF_TID, "task_type": "local_workflow"})
        self.s._on_task_event("task_progress", {"task_id": WF_TID, "workflow_progress": [_wf(1, WF_AID, "progress")]})
        self._released_at_the_end(WF_AID, self.wf_agent, lambda: self.s._on_task_event(
            "task_progress", {"task_id": WF_TID, "workflow_progress": [_wf(1, WF_AID2, "progress")]}))

    def test_a_workflow_agent_is_released_at_its_run_end(self):
        self.s._on_task_event("task_started", {"task_id": WF_TID, "task_type": "local_workflow"})
        self.s._on_task_event("task_progress", {"task_id": WF_TID, "workflow_progress": [_wf(1, WF_AID, "progress")]})
        self._released_at_the_end(WF_AID, self.wf_agent,
                                  lambda: self.s._on_task_event("task_notification", {"task_id": WF_TID, "status": "completed"}))

    def test_an_agent_is_released_when_its_cli_is_torn_down(self):
        self._released_at_the_end(AID, self.agent, lambda: self.s._drop_live_work("reconnect"))

    def _session_gone(self, **flags):
        for k, v in flags.items():
            setattr(self.s, k, v)
        with contextlib.redirect_stderr(io.StringIO()):
            self.be._on_session_gone(self.s)

    def test_an_agent_is_released_when_its_session_is_killed(self):
        self._released_at_the_end(AID, self.agent, lambda: self._session_gone(ended=True))   # a kill or a shutdown ends it

    def test_an_agent_is_released_when_its_cli_dies_while_idle(self):
        self._released_at_the_end(AID, self.agent, lambda: self._session_gone())   # neither ended nor detached: a crash

    def test_a_detached_session_ends_no_agent(self):
        size = self._fold_while_running(AID, self.agent)
        km._begin_checkpoint_cycle()                                     # drains the agent's start
        self._session_gone(detached=True)                                # the CLI lives on under its host
        self.assertIn(AID, self.s._subagents, "the agent stays in the live set")
        self.assertEqual(self.be.drain_agent_live_events(), ([], 0), "no end was queued")
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the agent keeps its records")
        self.assertEqual(self._stat("released"), {})

    # ---- after the release ----

    def test_a_released_agent_folds_from_its_document_without_a_whole_read(self):
        # the positive control first: in this setup a pop WITHOUT a document costs a whole read at the next fold, so the zero
        # below is the document's doing, not a counter that cannot see
        self._fold_while_running(WF_AID, self.wf_agent)
        with em._JSONL_CACHE_LOCK:
            em._cache_pop_locked(self.wf_agent)
        w0, r0 = self._whole_reads(), em._READ_BYTES.get(self.wf_agent, 0)
        km._agent_launch_ids(self.wf_agent)
        self.assertEqual(self._whole_reads(), w0 + 1, "control: a pop without a document reads the file whole at the next fold")
        self.assertGreaterEqual(em._READ_BYTES.get(self.wf_agent, 0) - r0, os.path.getsize(self.wf_agent))
        asyncio.run(self.s._subagent_stop_hook({"agent_id": WF_AID}, None, None))
        km._begin_checkpoint_cycle()

        size = self._fold_while_running(AID, self.agent)
        ids, steps = set(km._agent_launch_ids(self.agent)), json.dumps(km._agent_steps(self.agent), sort_keys=True)
        self._stop(AID)
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "released")
        w0, r0 = self._whole_reads(), em._READ_BYTES.get(self.agent, 0)
        for _ in range(3):                                               # three builds fold the finished agent again
            self.assertEqual(set(km._agent_launch_ids(self.agent)), ids, "the launch fold answers as before")
            self.assertEqual(json.dumps(km._agent_steps(self.agent), sort_keys=True), steps, "the agent head answers as before")
        self.assertEqual(self._whole_reads(), w0, "no whole read")
        self.assertLessEqual(em._READ_BYTES.get(self.agent, 0) - r0, 2 * em._JSONL_TAIL_GUARD,
                             "only guard bytes were read (a restore verifies and captures at most two guards)")
        ent = self._ent(self.agent)
        self.assertTrue(ent is not None and ent[5] > 0 and em._entry_weight(ent) == 0, "a restored tail weighing nothing")

    def test_a_whole_read_after_a_release_is_counted_and_one_after_another_pop_is_not(self):
        size = self._released_at_the_end(AID, self.agent, lambda: self._stop(AID))
        km._agent_launch_ids(self.agent)                                 # a fold restores the tail from the document
        ent = self._ent(self.agent)
        self.assertTrue(ent is not None and ent[5] > 0, "a restored tail")
        self.assertEqual(self._stat("releasedReread"), {"count": 0, "bytes": 0}, "a restore is not a whole read")
        em._read_jsonl_incremental(self.agent)                           # a whole reader (the agent viewer) upgrades it
        self.assertEqual(self._stat("releasedReread"), {"count": 1, "bytes": size}, "what the release cost: one whole read")
        em._read_jsonl_incremental(self.agent)
        self.assertEqual(self._stat("releasedReread")["count"], 1, "a hit afterwards costs nothing more")
        # control: a released path popped by something else before its whole read is that pop's, not the release's
        self._fold_while_running(WF_AID, self.wf_agent)
        asyncio.run(self.s._subagent_stop_hook({"agent_id": WF_AID}, None, None))
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.wf_agent), "the workflow agent was released too")
        km._agent_launch_ids(self.wf_agent)
        with em._JSONL_CACHE_LOCK:
            em._cache_pop_locked(self.wf_agent)                          # an eviction of the restored tail
        em._read_jsonl_incremental(self.wf_agent)
        self.assertEqual(self._stat("releasedReread")["count"], 1, "a whole read after another pop is not counted")

    def test_a_resumed_agent_is_a_false_end_and_appends_to_its_tail(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        km._begin_checkpoint_cycle()
        self._start(AID)                                                 # the agent is resumed after its end
        km._begin_checkpoint_cycle()
        before = os.path.getsize(self.agent)
        _append(self.agent, _agent_lines(AID, 45, 3))
        w0 = self._whole_reads()
        km._awaiting_live_rows(SID, self.leaf, self.s.snapshot())       # the running agent is folded again
        ent = self._ent(self.agent)
        self.assertTrue(ent is not None and ent[5] > 0, "the fold holds a tail, not the whole file")
        self.assertEqual(em._entry_weight(ent), os.path.getsize(self.agent) - before, "the tail holds the appended records alone")
        self.assertEqual(self._whole_reads(), w0, "no whole read")
        self.assertEqual(self._stat("falseEnds"), 1, "the released agent entered the live set again")
        self.assertEqual(self._stat("released")["agentEnded"]["bytes"], size)

    def test_a_second_end_over_a_restored_tail_leaves_it_alone(self):
        self._fold_while_running(AID, self.agent)
        self._stop(AID)
        km._begin_checkpoint_cycle()
        km._agent_launch_ids(self.agent)                                 # a fold restores a tail weighing nothing
        tail = self._ent(self.agent)
        self.assertTrue(tail is not None and tail[5] > 0 and em._entry_weight(tail) == 0, "a restored tail")
        self._start(AID); self._stop(AID)                                # resumed and ended again, nothing appended
        km._begin_checkpoint_cycle()
        self.assertIs(self._ent(self.agent), tail, "the same restored tail stays")
        self.assertEqual(self._stat("released")["agentEnded"]["count"], 1, "one release, not two")

    def test_an_end_and_a_start_in_one_cycle_release_nothing(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        self._start(AID)                                                 # resumed before the pusher's next cycle
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the running agent keeps its records")
        self.assertEqual((self._stat("released", {}), self._stat("falseEnds", 0)), ({}, 0))

    # ---- false ends: no liveness snapshot ends an agent ----

    def test_a_staler_snapshot_a_failed_row_and_a_dormant_one_release_nothing(self):
        stale = self.s.snapshot()                                        # taken before the agent started: subagents []
        size = self._fold_while_running(AID, self.agent)
        fresh = self.s.snapshot()
        sb.write_reg(self.state, SID, {"sid": SID, "alive": True, "name": "api", "cwd": self.root})
        self.be._live_row = lambda reg, sid: 1 / 0                       # one session's row raises: the listing's fallback row
        with contextlib.redirect_stderr(io.StringIO()):
            failed = self.be.live_sessions()[SID]
        self.assertEqual(failed["subagents"], [], "the backend's failure row lists no agent")
        self.assertEqual(stale["subagents"], [])
        for row in (stale, fresh, failed, fresh, None, fresh, stale):   # three threads' snapshots, out of order
            km._awaiting_live_rows(SID, self.leaf, row)
            km._begin_checkpoint_cycle()
            self.assertEqual(self._weight(self.agent), size, "the running agent keeps its records")
        self.assertEqual(self._stat("released", {}), {}, "nothing was released")

    # ---- the release's refusals ----

    def test_a_release_racing_a_read_is_owed_not_lost(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        real, fired = em.checkpoint_write, []

        def racing_write(path, *a, **k):                                 # between the document write and the pop, a read of the
            out = real(path, *a, **k)                                    #  grown file replaces the entry
            if str(path) == self.agent and not fired:
                fired.append(1)
                _append(self.agent, _agent_lines(AID, 45, 2))
                em._read_jsonl_incremental(self.agent)
            return out
        em.checkpoint_write = racing_write
        try:
            km._begin_checkpoint_cycle()
        finally:
            em.checkpoint_write = real
        self.assertTrue(fired, "the release wrote the agent's document")
        grown = os.path.getsize(self.agent)
        self.assertGreater(grown, size)
        self.assertEqual(self._weight(self.agent), grown, "the newer entry stands")
        self.assertEqual((self._stat("releaseDeferred"), self._stat("releaseLost"), self._stat("released")), (1, 0, {}),
                         "owed, not popped, not lost")
        km._begin_checkpoint_cycle()                                     # the next cycle pays it
        self.assertIsNone(self._weight(self.agent), "released at the next cycle")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": grown}})

    def test_a_read_in_flight_when_the_release_pops_is_owed_not_lost(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        _append(self.agent, _agent_lines(AID, 45, 3))                   # the agent's last lines, not read yet
        grown = os.path.getsize(self.agent)
        parked, go, box = threading.Event(), threading.Event(), {}
        real_scan, real_stripe = em._scan_jsonl_stream, em._read_stripe

        def scan(*a, **k):                                               # the reader waits inside its byte pull, holding the
            if threading.current_thread() is box.get("reader"):          #  path's stripe, before its insert
                parked.set()
                go.wait(10)
            return real_scan(*a, **k)

        def stripe(path):                                                # the release reaching for that stripe lets the reader
            if box.get("armed") and threading.current_thread() is not box.get("reader") and str(path) == self.agent:
                go.set()                                                 #  go on to its insert
            return real_stripe(path)
        box["reader"] = threading.Thread(target=em._read_jsonl_incremental, args=(self.agent,))
        em._scan_jsonl_stream, em._read_stripe = scan, stripe
        try:
            box["reader"].start()
            self.assertTrue(parked.wait(10), "precondition: the reader is inside its read")
            box["armed"] = True
            km._begin_checkpoint_cycle()                                 # the pusher releases the ended agent
            go.set()
            box["reader"].join(10)
        finally:
            em._scan_jsonl_stream, em._read_stripe = real_scan, real_stripe
        self.assertFalse(box["reader"].is_alive(), "precondition: the reader finished")
        self.assertGreater(grown, size)
        self.assertEqual(self._weight(self.agent), grown, "the read's entry stands, whole")
        self.assertEqual((self._stat("releaseDeferred"), self._stat("released")), (1, {}), "the release is owed, not taken")
        km._begin_checkpoint_cycle()                                     # the next cycle pays it
        self.assertIsNone(self._weight(self.agent), "released at the next cycle")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": grown}})

    def test_a_release_the_cycle_budget_refuses_waits_for_the_next_cycle(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        km.CKPT_CONVERGE_BYTES = 1                                       # no room for the document, two cycles running
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the entry stays this cycle")
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "and the next")
        self.assertEqual(self._stat("releaseDeferred"), 2, "each refused cycle counts one deferral")
        km.CKPT_CONVERGE_BYTES = 8 * 1024 * 1024
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "released at the next cycle with room")
        self.assertTrue(em._ckpt_file(self.agent).exists())
        self.assertEqual((self._stat("releaseDeferred"), self._stat("released")), (2, {"agentEnded": {"count": 1, "bytes": size}}))
        self._start(AID)
        km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("falseEnds"), 1, "the agent starting after its owed release was paid is a false end")

    def test_an_owed_release_is_cancelled_when_the_agent_starts_again(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        km.CKPT_CONVERGE_BYTES = 1                                       # the budget refuses the document: the release is owed
        km._begin_checkpoint_cycle()
        km.CKPT_CONVERGE_BYTES = 8 * 1024 * 1024
        self._start(AID)                                                 # resumed before the cycle that would pay it
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the running agent keeps its records")
        self.assertEqual((self._stat("released"), self._stat("falseEnds"), self._stat("releaseDeferred")), ({}, 0, 1),
                         "nothing released, no false end counted, one deferral")
        self.assertEqual(em._RELEASE_OWED, {}, "nothing is owed any more")

    def test_an_owed_release_then_a_start_and_an_end_releases_once(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        km.CKPT_CONVERGE_BYTES = 1
        km._begin_checkpoint_cycle()                                     # the release is owed
        km.CKPT_CONVERGE_BYTES = 8 * 1024 * 1024
        self._start(AID); self._stop(AID)                                # resumed and ended again before the next cycle
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "released in that cycle")
        self.assertEqual((self._stat("released"), self._stat("falseEnds")), ({"agentEnded": {"count": 1, "bytes": size}}, 0),
                         "one release, and no false end counted")
        self._start(AID)
        km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("falseEnds"), 1, "the agent starting after that release is a false end")

    def test_an_owed_release_that_raises_loses_neither_the_rest_nor_the_cycle(self):
        self._fold_while_running(AID, self.agent)
        self._stop(AID)
        self.s._on_task_event("task_started", {"task_id": WF_TID, "task_type": "local_workflow"})
        self._fold_while_running(WF_AID, self.wf_agent)
        self.s._on_task_event("task_progress", {"task_id": WF_TID, "workflow_progress": [_wf(1, WF_AID, "done")]})
        km.CKPT_CONVERGE_BYTES = 1
        km._begin_checkpoint_cycle()
        self.assertEqual(list(em._RELEASE_OWED), [self.agent, self.wf_agent], "precondition: two releases owed, in end order")
        agent3 = os.path.join(os.path.dirname(self.agent), "agent-%s.jsonl" % AID3)
        _append(agent3, _agent_lines(AID3, 0, 40))
        self._fold_while_running(AID3, agent3)
        self._stop(AID3)                                                 # an end queued for the cycle below
        real, calls = em._drop_write, []

        def raising(key, ent, *a, **k):
            calls.append(key)
            if len(calls) == 1:
                raise RuntimeError("synthetic")
            return real(key, ent, *a, **k)
        em._drop_write = raising
        km.CKPT_CONVERGE_BYTES = 8 * 1024 * 1024
        err, raised = io.StringIO(), None
        try:
            with contextlib.redirect_stderr(err):
                km._begin_checkpoint_cycle()
        except Exception as e:
            raised = e
        finally:
            em._drop_write = real
        self.assertIsNone(raised, "the cycle did not raise")
        self.assertEqual(calls[0], self.agent, "precondition: the first owed release is the one that raised")
        self.assertIsNone(self._weight(self.wf_agent), "the owed release after the one that raised was released")
        self.assertIsNone(self._weight(agent3), "the end queued for the same cycle was released in it")
        self.assertEqual(self._stat("releaseLost"), 1, "the raise is one release given up")
        self.assertIn("a release raised RuntimeError", err.getvalue())

    def test_with_the_drop_writes_off_the_release_keeps_the_entry_and_says_so_once(self):
        km.CKPT_CONVERGE_MS = 0                                          # the pass off: the cycle begins with no budget
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual(err.getvalue().count("recordCache.releaseLost"), 1, "said on stderr: %r" % err.getvalue())
        self.assertEqual(self._weight(self.agent), size, "the entry is kept")
        wf_size = self._fold_while_running(WF_AID, self.wf_agent)
        asyncio.run(self.s._subagent_stop_hook({"agent_id": WF_AID}, None, None))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual(err.getvalue(), "", "said once per process")
        self.assertEqual(self._weight(self.wf_agent), wf_size)
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (2, {}))

    def test_a_write_that_wrote_nothing_keeps_the_entry(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        real = em.checkpoint_write
        em.checkpoint_write = lambda path, *a, **k: False               # a write due that writes nothing
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                km._begin_checkpoint_cycle()
        finally:
            em.checkpoint_write = real
        self.assertEqual(self._weight(self.agent), size, "the entry is kept")
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (1, {}))
        self.assertIn("recordCache.releaseLost", err.getvalue())

    def test_a_document_check_that_raises_keeps_the_entry(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        real = em._path_needs_write

        def raising(*a, **k):
            raise RuntimeError("synthetic")
        em._path_needs_write = raising                                   # whether a write is due cannot be known
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                km._begin_checkpoint_cycle()
        finally:
            em._path_needs_write = real
        self.assertEqual(self._weight(self.agent), size, "the entry is kept")
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (1, {}))
        self.assertIn("the document check raised RuntimeError (counted as recordCache.releaseLost", err.getvalue())

    def test_an_owed_release_whose_file_is_gone_is_released(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        km.CKPT_CONVERGE_BYTES = 1                                       # deferred for the budget
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size)
        os.unlink(self.agent)                                            # the transcript is deleted before the next cycle
        km.CKPT_CONVERGE_BYTES = 8 * 1024 * 1024
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "the entry is released")
        self.assertFalse(em._ckpt_file(self.agent).exists(), "no document written for a file that is gone")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}})

    def test_events_past_the_queue_bound_are_releases_given_up(self):
        self.be._AGENT_LIVE_MAX = 2                                      # this backend's bound, for the test
        # the queue holds two, so start(WF_AID) drops start(AID) and stop(WF_AID) drops stop(AID): of the two events dropped,
        # the stop is a release and the start is not
        self._start(AID); self._stop(AID); self._start(WF_AID); self._stop(WF_AID)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("releaseLost"), 1, "of the two events dropped past the bound, the one end is counted")
        self.assertIn("recordCache.releaseLost", err.getvalue())
        km._begin_checkpoint_cycle(); km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("releaseLost"), 1, "two later cycles add nothing to releaseLost")

    def test_starts_dropped_past_the_queue_bound_are_not_releases_given_up(self):
        self.be._AGENT_LIVE_MAX = 2
        # stop(AID) drops start(AID) and stop(WF_AID) drops start(WF_AID): both events dropped are starts
        self._start(AID); self._start(WF_AID); self._stop(AID); self._stop(WF_AID)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("releaseLost"), 0, "the two events dropped past the bound were starts: none is counted")
        self.assertNotIn("recordCache.releaseLost", err.getvalue())

    def test_an_end_that_raises_does_not_lose_the_rest_of_the_batch(self):
        size = self._fold_while_running(AID, self.agent)
        other = sb.SdkSession(self.be, {"sid": OTHER_SID, "name": "web", "cwd": self.root})
        asyncio.run(other._subagent_start_hook({"agent_id": WF_AID2, "agent_type": "general-purpose"}, None, None))
        asyncio.run(other._subagent_stop_hook({"agent_id": WF_AID2}, None, None))   # queued BEFORE the good end below
        self._stop(AID)
        path_of = km._path_of

        def raising(sid, now=None):
            if sid == OTHER_SID:
                raise RuntimeError("synthetic")
            return path_of(sid, now)
        km._path_of = raising
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "the end queued after the one that raised was still released")
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (1, {"agentEnded": {"count": 1, "bytes": size}}))
        self.assertIn("a release raised RuntimeError", err.getvalue())
        asyncio.run(other._subagent_start_hook({"agent_id": WF_AID2, "agent_type": "general-purpose"}, None, None))
        asyncio.run(other._subagent_stop_hook({"agent_id": WF_AID2}, None, None))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual((err.getvalue(), self._stat("releaseLost")), ("", 2), "counted again, said once")

    # ---- the bounds, and a rebind ----

    def test_the_release_marks_keep_the_newest_up_to_the_count_cap(self):
        paths = []
        for i in range(3):
            p = os.path.join(self.root, "released-%d.jsonl" % i)
            _append(p, _agent_lines(AID, 0, 2))
            em._read_jsonl_incremental(p)                                # a whole entry, weighing its file
            paths.append(p)
        saved = em._JSONL_CACHE_MAX
        em._JSONL_CACHE_MAX = 2                                          # the marks share the cache's count cap, lowered once
        self.addCleanup(setattr, em, "_JSONL_CACHE_MAX", saved)          #  the three entries are in (a cap binds at an insert)
        em.checkpoint_cycle_begin(8 * 1024 * 1024)
        self.assertEqual([em.release_entry(p, "agentEnded") for p in paths], ["released"] * 3, "precondition: three releases")
        self.assertEqual(list(em._RELEASED_MARKS), paths[1:], "the two newest marks, oldest first")

    def test_the_owed_releases_past_their_bound_give_up_the_oldest(self):
        saved = em._DROP_OWED_MAX
        em._DROP_OWED_MAX = 2
        self.addCleanup(setattr, em, "_DROP_OWED_MAX", saved)
        keys = [os.path.join(self.root, "owed-%d.jsonl" % i) for i in range(3)]
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            for k in keys:
                em._owe_release(k, "agentEnded")
        self.assertEqual(list(em._RELEASE_OWED), keys[1:], "the oldest owed release is the one gone")
        self.assertEqual((self._stat("releaseLost"), self._stat("releaseDeferred")), (1, 3), "one given up, three deferrals")
        self.assertEqual(err.getvalue().count("recordCache.releaseLost"), 1, "said once on stderr: %r" % err.getvalue())

    def test_the_released_ends_past_their_bound_forget_the_oldest(self):
        saved = km._AGENT_RELEASED_MAX
        km._AGENT_RELEASED_MAX = 2
        self.addCleanup(setattr, km, "_AGENT_RELEASED_MAX", saved)
        agent3 = os.path.join(os.path.dirname(self.agent), "agent-%s.jsonl" % AID3)
        _append(agent3, _agent_lines(AID3, 0, 40))
        for aid, path in ((AID, self.agent), (WF_AID, self.wf_agent), (AID3, agent3)):
            em._read_jsonl_incremental(path)                             # a whole entry for the release to take
            self._start(aid); self._stop(aid)
        km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("released")["agentEnded"]["count"], 3, "precondition: three ends released")
        self.assertEqual(list(km._AGENT_RELEASED), [(SID, WF_AID), (SID, AID3)], "the first end is the one forgotten")

    def test_a_checkpoint_directory_rebind_forgets_an_owed_release(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        km.CKPT_CONVERGE_BYTES = 1
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "precondition: the release is owed")
        other = os.path.join(self.root, "checkpoints-rebound")
        em.set_checkpoint_dir(lambda: Path(other))                       # the state is rebound before the owed release is paid
        km.CKPT_CONVERGE_BYTES = 8 * 1024 * 1024
        km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("released"), {}, "nothing released")
        self.assertEqual(self._weight(self.agent), size, "the entry is whole")
        for d in (self.ckdir, other):
            self.assertEqual([f for _r, _d, fs in os.walk(d) for f in fs], [], "no document in %s" % os.path.basename(d))

    def test_a_cycle_over_a_backend_without_the_queue_does_nothing(self):
        for be in (None, False, object()):                               # not built, unavailable, a double without the queue
            km._sdk_backend = be
            km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("released"), {})

    # ---- /perf ----

    def test_perf_carries_the_release_counters_and_the_maximum(self):
        st = em.record_cache_stats()
        self.assertEqual(sorted(st), sorted(["entries", "bytes", "bytesMax", "budgetBytes", "countCap", "inserts", "evictions",
                                             "evictedBytes", "budgetEvictions", "dropped", "droppedBytes", "wholeReads",
                                             "wholeReadsByStage", "released", "releaseDeferred", "releaseLost", "falseEnds",
                                             "releasedReread"]))
        self.assertEqual((st["released"], st["releasedReread"]), ({}, {"count": 0, "bytes": 0}), "tables, even when zeroed")
        self.assertEqual(jd._SERVE_GAUGES["recordCache"], ("entries", "bytes", "bytesMax", "budgetBytes", "countCap"),
                         "bytesMax is the one new gauge")


if __name__ == "__main__":
    unittest.main()
