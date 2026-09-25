#!/usr/bin/env python3
"""A finished agent's parsed transcript leaves the record cache at the agent's end (2026-09-24).

The kernel folds a running agent's transcript within seconds of each append (the awaiting rows attribute a background
command through it, the agent head steps it), so the quiescent drop, which pops only at a fold that steps records over a
file unchanged for 120 s, never fires for it; after the agent ends every fold is a hit, which never pops, and the whole
entry stayed until the count cap evicted it. On a long-lived kernel those entries were most of the cache's non-leaf held
bytes. The SDK backend knows the end exactly: the agent leaves its session's live set on SubagentStop, its own task's end
or a turn-end report that lists its Task row as ended, its workflow slot's done or error state, a re-minted slot, the run's
end, the CLI's reconnect teardown, or the CLI's end (a kill, a crash; not a detach, where the CLI lives on under its host),
and, for a CLI that died with an earlier kernel, the boot reconcile or a comment thread's wake over the reg's mirror
(SdkBackend.note_agent_live's docstring states the roads in full, with the agents no end is queued for). Each of those ends
queues the agent, the agent's own end events even on a session object that never saw it start (the object that reattaches
after a kernel restart under a session host); the pusher drains the queue at its next cycle's start and releases the
agent's entry, writing the file's checkpoint document first when it lacks what the cache holds, so a later fold whose
cursor the document records restores a zero-weight tail instead of reading the file whole; an end seen before any fold
holds the file is remembered and the file is released at the first cycle after a read holds it. A file no fold holds a
recordable cursor for is released without a document and read whole at its next fold; a file that no longer exists is
released with nothing written.

Synthetic data only: a notes-api project under a temp root, placeholder ids, a private sid, hostname TESTHOST.
"""
import ast
import asyncio
import contextlib
import io
import json
import os
import shutil
import tempfile
import threading
import unittest
from collections import Counter
from pathlib import Path
from romp_load import load_source
if __package__:                                   # under pytest tests/ is a package: the one parse cache every census shares
    from . import parse_cache as PC
else:                                             # a direct run has tests/ on sys.path
    import parse_cache as PC

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
NOTHING_RELEASED = {"agentEnded": {"count": 0, "bytes": 0}}   # recordCache.released before any release: the reason
#                                                                  reported at zero, so an export carries the key from the first read


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
        getattr(km, "_AGENT_ENDED_UNHELD", {}).clear()
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

    def _session_gone(self, sess=None, **flags):
        sess = self.s if sess is None else sess
        for k, v in flags.items():
            setattr(sess, k, v)
        with contextlib.redirect_stderr(io.StringIO()):
            self.be._on_session_gone(sess)

    def test_an_agent_is_released_when_its_session_is_killed(self):
        self._released_at_the_end(AID, self.agent, lambda: self._session_gone(ended=True))   # a kill or a shutdown ends it

    def test_an_agent_is_released_when_its_cli_dies_while_idle(self):
        self._released_at_the_end(AID, self.agent, lambda: self._session_gone())   # neither ended nor detached: a crash

    def test_an_agent_is_released_when_its_cli_is_cut_mid_turn(self):
        heals = []
        real = self.be._heal_cut_session
        self.be._heal_cut_session = lambda sess, oom: (heals.append(sess), real(sess, oom))
        self.be._oom_killed_scope = lambda sess: None                      # no scope read
        self.be._ensure = lambda sid, on_boot_settled=None: None           # the heal's resume does not start a CLI
        self._released_at_the_end(AID, self.agent, lambda: self._session_gone(inflight=1))   # died mid-turn: a cut
        self.assertEqual(heals, [self.s], "the cut road ran: the heal was called once for this session")

    def test_a_detached_session_ends_no_agent(self):
        size = self._fold_while_running(AID, self.agent)
        km._begin_checkpoint_cycle()                                     # drains the agent's start
        self._session_gone(detached=True)                                # the CLI lives on under its host
        self.assertIn(AID, self.s._subagents, "the agent stays in the live set")
        self.assertEqual(self.be.drain_agent_live_events(), ([], 0), "no end was queued")
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the agent keeps its records")
        self.assertEqual(self._stat("released"), NOTHING_RELEASED)

    # ---- an object that reattached after a kernel restart never saw the start, and still queues the end ----

    def _reattached(self, aid, path):
        """The agent runs across a kernel restart under a session host: the object that saw its start is dropped at the
        detach, and the one that reattaches to the surviving CLI starts with an empty live set (no subagent mirror exists).
        This module's state root has session hosts off (setUp): no host is started."""
        size = self._fold_while_running(aid, path)
        km._begin_checkpoint_cycle()                                     # drains the start
        self._session_gone(detached=True)
        self.assertEqual(self.be.drain_agent_live_events(), ([], 0), "precondition: the detach queued no end")
        again = sb.SdkSession(self.be, {"sid": SID, "name": "api", "cwd": self.root})
        self.assertNotIn(aid, again._subagents, "precondition: the new object never saw the start")
        return again, size

    def _queued_then_released(self, aid, path, size):
        self.assertEqual(list(self.be._agent_live_q), [(SID, aid, False)], "the end was queued, once")
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(path), "released at the next cycle")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}})

    def test_a_reattached_object_queues_the_end_at_the_agents_stop_hook(self):
        again, size = self._reattached(AID, self.agent)
        asyncio.run(again._subagent_stop_hook({"agent_id": AID}, None, None))
        self._queued_then_released(AID, self.agent, size)

    def test_a_reattached_object_queues_the_end_at_the_agents_task_end_and_not_a_shells(self):
        again, size = self._reattached(AID, self.agent)
        shell = "b0000000000000001"
        again._seed_live_work_from_reg({"bgTasks": [                     # the reg's mirror, seeded at the attach
            {"taskId": AID, "type": "local_agent", "desc": "check the notes-api routes", "since": 100},
            {"taskId": shell, "type": "local_bash", "desc": "run the notes-api tests", "since": 100}]})
        again._on_task_event("task_notification", {"task_id": shell, "status": "completed"})
        self.assertEqual(list(self.be._agent_live_q), [], "a shell's end queues nothing")
        again._on_task_event("task_notification", {"task_id": AID, "status": "completed"})
        self._queued_then_released(AID, self.agent, size)

    def test_a_reattached_object_queues_the_end_at_the_agents_workflow_slot_once(self):
        again, size = self._reattached(WF_AID, self.wf_agent)
        for _ in range(2):                                               # the run re-sends its whole list on every change
            again._on_task_event("task_progress", {"task_id": WF_TID, "workflow_progress": [_wf(1, WF_AID, "done")]})
        again._on_task_event("task_notification", {"task_id": WF_TID, "status": "completed"})   # and the run ends
        self.assertNotIn(WF_TID, again._wf_ended, "the run's record of the ends it queued goes with the run")
        self._queued_then_released(WF_AID, self.wf_agent, size)

    def test_the_teardown_forgets_the_ends_a_run_queued(self):
        self.s._on_task_event("task_progress", {"task_id": WF_TID, "workflow_progress": [_wf(1, WF_AID, "done")]})
        self.assertEqual(self.s._wf_ended, {WF_TID: {WF_AID}}, "precondition: the run's end queued is recorded")
        self.s._drop_live_work("reconnect")
        self.assertEqual(self.s._wf_ended, {}, "the teardown forgets it with the run's roster")

    # ---- the CLI's end on a reattached object: the agents it knows only through a row or a roster (PR 913 round 1) ----
    # The object that reattaches to a surviving CLI after a kernel restart never saw the starts of the agents already
    # running, so its _subagents lacks them; it knows a Task agent through the row seeded from the reg's mirror (or adopted
    # from a turn-end report) and a Workflow run's agent through the roster a progress frame named. Each road below ends such
    # an agent with no end event of the agent's own, and each queues its end and releases its records at the next cycle.
    # The premise is the one the live object's teardown already rests on: the CLI's end, or its reconnect teardown, ends
    # every agent inside it.

    def _seed_agent_row(self, sess, shell=True):
        rows = [{"taskId": AID, "type": "local_agent", "desc": "check the notes-api routes", "since": 100}]
        if shell:
            rows.append({"taskId": "b0000000000000001", "type": "local_bash", "desc": "run the notes-api tests", "since": 100})
        self.assertEqual(sess._seed_live_work_from_reg({"bgTasks": rows}), len(rows), "precondition: the mirror's rows seeded")

    def _roster(self, sess):
        sess._on_task_event("task_progress", {"task_id": WF_TID, "workflow_progress": [_wf(1, WF_AID, "progress")]})
        self.assertEqual(sess._wf_agents, {WF_TID: {WF_AID}}, "precondition: a progress frame named the run's agent")
        self.assertEqual(list(self.be._agent_live_q), [], "precondition: a progress frame ends nothing")

    def _no_wake(self):
        self.be._ensure = lambda sid, on_boot_settled=None: None    # a death notice's wake and a cut's heal start no CLI
        self.be._oom_killed_scope = lambda sess: None               # the cut road reads no scope

    def _released_at_the_next_cycle(self, aid, path, size):
        queued = list(self.be._agent_live_q)
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(path), "the finished agent's records are released at the next cycle (held: %s of %d "
                          "bytes; the ends queued: %r)" % (self._weight(path), size, queued))
        self.assertEqual(queued, [(SID, aid, False)], "the end was queued, once")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}})

    def test_a_reattached_objects_seeded_agent_row_ends_when_its_cli_dies_while_idle(self):
        again, size = self._reattached(AID, self.agent)
        self._seed_agent_row(again)
        self._no_wake()
        self._session_gone(again)                                        # neither ended nor detached: a crash
        self._released_at_the_next_cycle(AID, self.agent, size)

    def test_a_reattached_objects_seeded_agent_row_ends_when_its_session_is_killed(self):
        again, size = self._reattached(AID, self.agent)
        self._seed_agent_row(again)
        self._no_wake()
        self._session_gone(again, ended=True)                            # a kill or a shutdown
        self._released_at_the_next_cycle(AID, self.agent, size)

    def test_a_reattached_objects_seeded_agent_row_ends_when_its_cli_is_cut_mid_turn(self):
        again, size = self._reattached(AID, self.agent)
        self._seed_agent_row(again)
        self._no_wake()
        heals = []
        real = self.be._heal_cut_session
        self.be._heal_cut_session = lambda sess, oom: (heals.append(sess), real(sess, oom))
        self._session_gone(again, inflight=1)                            # died mid-turn: a cut
        self.assertEqual(heals, [again], "the cut road ran: the heal was called once for this object")
        self._released_at_the_next_cycle(AID, self.agent, size)

    def test_a_reattached_objects_roster_agent_ends_when_its_cli_dies(self):
        again, size = self._reattached(WF_AID, self.wf_agent)
        self._roster(again)
        self._no_wake()
        self._session_gone(again)
        self._released_at_the_next_cycle(WF_AID, self.wf_agent, size)

    def test_a_reattached_objects_seeded_agent_row_ends_when_its_cli_is_torn_down(self):
        again, size = self._reattached(AID, self.agent)
        self._seed_agent_row(again)
        again._drop_live_work("reconnect")
        self._released_at_the_next_cycle(AID, self.agent, size)

    def test_a_reattached_objects_roster_agent_ends_when_its_cli_is_torn_down(self):
        again, size = self._reattached(WF_AID, self.wf_agent)
        self._roster(again)
        again._drop_live_work("reconnect")
        self._released_at_the_next_cycle(WF_AID, self.wf_agent, size)

    def test_a_reattached_objects_seeded_agent_row_ends_when_the_report_lists_it_ended(self):
        """The report road: the agent's end frame never reached this kernel (acknowledged but not processed when the old
        kernel ended, a journal gap, or a mirror row left stale), no SubagentStop came, and the CLI's turn-end report lists
        the seeded row as ended. An agent that ends while no kernel is attached is not this road: the host replays its end
        frame at the attach, ahead of the first report."""
        again, size = self._reattached(AID, self.agent)
        self._seed_agent_row(again, shell=False)
        again._reconcile_seeded_with_report([{"id": AID, "status": "completed", "type": "subagent"}])
        self.assertNotIn(AID, again._bg_tasks, "precondition: the report retired the row")
        self._released_at_the_next_cycle(AID, self.agent, size)

    def test_an_adopted_agent_row_ends_when_a_later_report_lists_it_ended(self):
        again, size = self._reattached(AID, self.agent)
        again._reconcile_seeded_with_report([{"id": AID, "status": "running", "type": "subagent",
                                              "description": "check the notes-api routes"}])
        self.assertEqual(again._bg_tasks[AID]["type"], "local_agent", "precondition: adopted as a Task agent's row")
        self.assertEqual(list(self.be._agent_live_q), [], "precondition: an adoption ends nothing")
        again._reconcile_seeded_with_report([{"id": AID, "status": "completed", "type": "subagent"}])
        self._released_at_the_next_cycle(AID, self.agent, size)

    def test_residual_a_task_agent_row_of_a_type_never_learned_queues_no_end(self):
        """THE WITNESS of a residual SdkBackend.note_agent_live states (PR 913 round 1, the coordinator's decision 6): the
        reattached object's mirror lacked the agent's row, so the row is minted from the agent's first progress frame, which
        carries no type, and its end queues nothing. Queuing it was measured first (2026-09-25): the kernel would resolve
        the id at the drain, and on a miss that walks every sibling session's subagents tree in the project directory: on
        the largest project directory measured, 101 to 134 ms at the first walk (thirteen runs), and a median of 84 to 89 ms
        at each later cycle's walk once the jobs pass had dropped the sibling trees no alive session owns
        (_subagent_trees_forget; three runs of ten walks), both over the 50 ms bound set for one cycle's resolution; a
        further new id in the same cycle, with the trees still held, cost a median of 19 to 34 ms (thirteen runs). Green
        while the residual stands; queuing the end turns it red, and the texts that name the residual must change with it."""
        again, size = self._reattached(AID, self.agent)
        again._on_task_event("task_progress", {"task_id": AID, "description": "check the notes-api routes"})
        self.assertEqual(again._bg_tasks[AID]["type"], "", "precondition: a row of a type never learned")
        again._on_task_event("task_notification", {"task_id": AID, "status": "completed"})
        self.assertEqual(list(self.be._agent_live_q), [], "no end is queued for the row")
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the finished agent's records stay whole, left to the quiescent drop, "
                         "the count cap or the byte budget")

    # ---- the reg's mirror names the Task agents of a CLI that died with the old kernel ----

    def _dead_mirror_reg(self, **extra):
        reg = {"sid": SID, "alive": True, "name": "api", "cwd": self.root, "bgTasks": [
            {"taskId": AID, "type": "local_agent", "desc": "check the notes-api routes", "since": 100},
            {"taskId": "b0000000000000001", "type": "local_bash", "desc": "run the notes-api tests", "since": 100}], **extra}
        sb.write_reg(self.state, SID, reg)
        return reg

    def test_a_dead_mirrors_agent_row_at_boot_is_released_after_a_read_holds_its_file(self):
        """The boot reconcile with no surviving CLI: the mirror's Task agent died with the old kernel's CLI. Nothing is held at
        boot, so the end finds nothing to release; the kernel remembers it, and a read that holds the file afterwards is
        released at the next cycle."""
        reg = self._dead_mirror_reg()
        self.be._ensure = lambda sid, on_boot_settled=None: None         # the resume starts no CLI
        self.be._start_test_root_sweep = lambda: None                    # nor any sweep of this box's test roots
        with contextlib.redirect_stderr(io.StringIO()):
            self.be._boot_reconcile([reg])
        self.assertIn("cut off", json.dumps(sb.read_reg(self.state, SID).get("queue")), "precondition: the notice was queued")
        queued = list(self.be._agent_live_q)
        km._begin_checkpoint_cycle()                                     # the end finds nothing held
        km._agent_launch_ids(self.agent)                                 # a build reads the finished agent's file
        size = os.path.getsize(self.agent)
        self.assertEqual(self._weight(self.agent), size, "precondition: the read holds the whole file")
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "released at the cycle after the read (held: %s of %d bytes; the ends "
                          "queued at boot: %r)" % (self._weight(self.agent), size, queued))
        self.assertEqual(queued, [(SID, AID, False)], "the Task agent's end was queued at boot, and not the shell's")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}})

    def test_a_threads_wake_over_a_dead_mirrors_agent_row_releases_its_held_file(self):
        size = self._fold_while_running(AID, self.agent)                 # the file is held
        km._begin_checkpoint_cycle()                                     # drains the start
        self._dead_mirror_reg(threadOf="11111111-2222-3333-4444-000000000000")   # a dormant comment thread, its CLI dead

        class _NoCli:                                                    # the woken thread's object starts no CLI
            def __init__(self, backend, reg):
                self.thread = threading.Thread(target=lambda: None)
                self.on_boot_settled = None

            def start(self):
                pass
        real = sb.SdkSession
        sb.SdkSession = _NoCli
        try:
            self.be._ensure(SID)
        finally:
            sb.SdkSession = real
        self.assertIn("cut off", json.dumps(sb.read_reg(self.state, SID).get("queue")), "precondition: the notice was queued")
        self._released_at_the_next_cycle(AID, self.agent, size)

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
        # only the first whole read after the release counts (PR 913 round 1, group E): the file rewritten in place at the
        # same size, with a later mtime, is read whole past the cache, and that second whole read is not counted
        with open(self.agent, "r+b") as f:
            data = bytearray(f.read())
            i = data.rindex(b"schema")
            data[i:i + 6] = b"SCHEMA"
            f.seek(0); f.write(bytes(data))
        later = os.stat(self.agent).st_mtime + 5
        os.utime(self.agent, (later, later))
        w0 = self._whole_reads()
        em._read_jsonl_incremental(self.agent)
        self.assertEqual(self._whole_reads(), w0 + 1, "precondition: a second whole read of the file")
        self.assertEqual(self._stat("releasedReread")["count"], 1, "only the first whole read after the release is counted")
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

    def test_re_releasing_a_marked_path_refreshes_its_mark(self):
        """The release moves a path's mark to the newest (PR 913 round 1, group E; decision 11 implemented the refresh once,
        at the move in release_entry, the release's own pop keeping the mark). A path released, resumed, and released again
        from a restored tail that grew holds the newest mark, so a later release past the marks' bound drops the other path's
        mark, not this one's. Red under the move made a setdefault, which leaves the mark where the first release put it."""
        self._fold_while_running(AID, self.agent)
        self._fold_while_running(WF_AID, self.wf_agent)
        self._stop(AID); self._stop(WF_AID)
        km._begin_checkpoint_cycle()
        self.assertEqual(list(em._RELEASED_MARKS), [self.agent, self.wf_agent], "precondition: both released, in end order")
        self._start(AID)                                                 # resumed: a false end
        km._begin_checkpoint_cycle()
        km._agent_launch_ids(self.agent)                                 # its fold restores a tail (the insert keeps the mark)
        _append(self.agent, _agent_lines(AID, 45, 3))
        km._awaiting_live_rows(SID, self.leaf, self.s.snapshot())       # and the tail grows
        ent = self._ent(self.agent)
        self.assertTrue(ent is not None and ent[5] > 0 and em._entry_weight(ent) > 0, "precondition: a tail holding records")
        self.assertEqual(list(em._RELEASED_MARKS), [self.agent, self.wf_agent], "precondition: the mark kept, not taken")
        self._stop(AID)
        km._begin_checkpoint_cycle()                                     # released again
        self.assertEqual(self._stat("released")["agentEnded"]["count"], 3, "precondition: the second release was taken")
        agent3 = os.path.join(os.path.dirname(self.agent), "agent-%s.jsonl" % AID3)
        _append(agent3, _agent_lines(AID3, 0, 40))
        em._read_jsonl_incremental(agent3)
        saved = em._JSONL_CACHE_MAX
        em._JSONL_CACHE_MAX = 2                                          # the marks share the cache's count cap
        self.addCleanup(setattr, em, "_JSONL_CACHE_MAX", saved)
        self.assertEqual(em.release_entry(agent3, "agentEnded"), "released", "precondition: a third path released")
        self.assertEqual(list(em._RELEASED_MARKS), [self.agent, agent3],
                         "the re-released path's mark is the newer one kept; the other path's is dropped")

    def test_a_resumed_agent_is_a_false_end_and_appends_to_its_tail(self):
        """And that tail's release is charged at the tail's weight, not the file's size (PR 913 round 1, group F)."""
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
        tailw, held = em._entry_weight(ent), self._stat("bytes")
        self._stop(AID)
        km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 2, "bytes": size + tailw}}, "the tail at its weight")
        self.assertEqual(self._stat("bytes"), held - tailw, "the held bytes fell by the tail's weight")

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
        self.assertEqual((self._stat("released", {}), self._stat("falseEnds", 0)), (NOTHING_RELEASED, 0))

    # ---- an end the kernel saw before it held the file (PR 913 round 1, group H) ----
    # The end finds nothing to release (release_entry answers "absent"), and a read inside the quiescent drop's 120 s window
    # then holds the finished agent's file whole with every later fold a hit. The kernel remembers such an end and releases
    # the file at the first cycle after a read holds it; a start for the agent forgets the end.

    def _end_before_any_read(self):
        """The agent starts and ends with no read of its file in between: the end finds nothing held, and is remembered."""
        self._start(AID)
        km._begin_checkpoint_cycle()                                     # drains the start
        _append(self.agent, _agent_lines(AID, 40, 5))
        self._stop(AID)
        km._begin_checkpoint_cycle()                                     # the end finds nothing held
        self.assertIsNone(self._ent(self.agent), "precondition: nothing held at the end")
        self.assertEqual(self._stat("released"), NOTHING_RELEASED, "precondition: nothing released at the end")

    def test_an_end_before_any_read_holds_the_file_is_released_at_the_cycle_after_a_read(self):
        self._end_before_any_read()
        ids = set(km._agent_launch_ids(self.agent))                      # a build folds the finished agent inside the window
        size = os.path.getsize(self.agent)
        self.assertEqual(self._weight(self.agent), size, "precondition: the read holds the whole file")
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "released at the first cycle after the read (held: %s of %d bytes)"
                          % (self._weight(self.agent), size))
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}}, "counted as an agent's end")
        self.assertNotIn((SID, AID), km._AGENT_ENDED_UNHELD, "the end is no longer remembered")
        self.assertEqual(set(km._agent_launch_ids(self.agent)), ids, "the next fold answers as before")
        ent = self._ent(self.agent)
        self.assertTrue(ent is not None and ent[5] > 0 and em._entry_weight(ent) == 0, "a restored tail weighing nothing")
        self._start(AID)
        km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("falseEnds"), 1, "the release was recorded as taken: a start after it is a false end")

    def test_an_owed_release_paid_as_absent_is_released_at_the_cycle_after_a_read(self):
        size = self._owed()
        with em._JSONL_CACHE_LOCK:
            em._cache_pop_locked(self.agent)                             # an eviction between the deferral and the pay
        km._begin_checkpoint_cycle()                                     # the owed release finds nothing held
        self.assertEqual(self._stat("released"), NOTHING_RELEASED, "precondition: nothing released at the pay")
        km._agent_launch_ids(self.agent)                                 # a build reads the file whole again
        self.assertEqual(self._weight(self.agent), size, "precondition: the read holds the whole file")
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "released at the first cycle after the read (held: %s of %d bytes)"
                          % (self._weight(self.agent), size))
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}})

    def test_a_start_after_an_unheld_end_keeps_the_records(self):
        """The guard: the agent starts again after an end that found nothing held, and its file is read whole while it runs.
        The start forgets the end in its own cycle; the running agent keeps its records then and at the cycle after. A
        start that did not forget it would be caught at the cycle after the start's: in the start's own cycle the batch
        speaks for the agent, and the remembered end is not paid then either way."""
        self._end_before_any_read()
        self.assertIn((SID, AID), km._AGENT_ENDED_UNHELD, "precondition: the end is remembered")
        self._start(AID)                                                 # resumed
        km._agent_launch_ids(self.agent)                                 # and read whole while it runs
        size = os.path.getsize(self.agent)
        km._begin_checkpoint_cycle()                                     # the start's cycle
        self.assertEqual(self._weight(self.agent), size, "the running agent keeps its records in the start's cycle")
        remembered = (SID, AID) in km._AGENT_ENDED_UNHELD
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "and at the cycle after")
        self.assertEqual((self._stat("released"), self._stat("falseEnds")), (NOTHING_RELEASED, 0))
        self.assertFalse(remembered, "the start forgot the end in its own cycle")

    def test_an_unheld_end_whose_release_the_budget_refuses_is_owed(self):
        self._end_before_any_read()
        km._agent_launch_ids(self.agent)
        size = os.path.getsize(self.agent)
        km.CKPT_CONVERGE_BYTES = 1                                       # no room for the document
        km._begin_checkpoint_cycle()
        self.assertEqual((self._weight(self.agent), self._stat("releaseDeferred")), (size, 1), "deferred: the entry stays")
        self.assertNotIn((SID, AID), km._AGENT_ENDED_UNHELD, "the remembered end is carried by the owed release now")
        self.assertEqual(km._AGENT_RELEASED.get((SID, AID)), [self.agent, False], "recorded as owed")
        km.CKPT_CONVERGE_BYTES = 8 * 1024 * 1024
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "the owed release is paid at the next cycle")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}})

    def test_an_unheld_end_whose_release_is_lost_or_raises_is_given_up(self):
        self._end_before_any_read()
        km._agent_launch_ids(self.agent)
        size = os.path.getsize(self.agent)
        km.CKPT_CONVERGE_MS = 0                                          # the drop writes off: the release is lost
        with contextlib.redirect_stderr(io.StringIO()):
            km._begin_checkpoint_cycle()
        self.assertEqual((self._weight(self.agent), self._stat("releaseLost")), (size, 1), "lost: the entry stays")
        self.assertNotIn((SID, AID), km._AGENT_ENDED_UNHELD, "given up, not remembered")
        km.CKPT_CONVERGE_MS = 150.0
        km._AGENT_ENDED_UNHELD[(SID, AID)] = self.agent                  # remembered again, and its release raises
        agent3 = os.path.join(os.path.dirname(self.agent), "agent-%s.jsonl" % AID3)
        _append(agent3, _agent_lines(AID3, 0, 40))
        em._read_jsonl_incremental(agent3)
        self._start(AID3); self._stop(AID3)                              # a batch end in the same cycle
        real = em.release_entry

        def release(key, reason):
            if key == self.agent:
                raise RuntimeError("synthetic")
            return real(key, reason)
        em.release_entry = release
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                km._begin_checkpoint_cycle()
        finally:
            em.release_entry = real
        self.assertNotIn((SID, AID), km._AGENT_ENDED_UNHELD, "a raise gives the remembered end up")
        self.assertEqual(self._stat("releaseLost"), 2, "counted as a release given up")
        self._assert_raise_line(err.getvalue(), (SID, AID, self.agent))   # written like the batch's raise (group G)
        self.assertIsNone(self._weight(agent3), "the batch's end in the same cycle was still released")

    def test_the_unheld_ends_past_their_bound_forget_the_oldest_and_count_nothing(self):
        saved = km._AGENT_RELEASED_MAX
        km._AGENT_RELEASED_MAX = 2                                       # the table's bound, shared with _AGENT_RELEASED
        self.addCleanup(setattr, km, "_AGENT_RELEASED_MAX", saved)
        agent3 = os.path.join(os.path.dirname(self.agent), "agent-%s.jsonl" % AID3)
        _append(agent3, _agent_lines(AID3, 0, 40))
        for aid in (AID, WF_AID, AID3):
            self._start(aid); self._stop(aid)                            # three ends, none of whose files is held
        km._begin_checkpoint_cycle()
        self.assertEqual(list(km._AGENT_ENDED_UNHELD), [(SID, WF_AID), (SID, AID3)], "the two newest, oldest first")
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (0, NOTHING_RELEASED),
                         "the end forgotten past the bound counts nothing: it held nothing when it was last paid")

    def test_an_owed_release_taken_for_a_path_forgets_its_unheld_ends(self):
        """An owed release taken for a remembered end's path forgets that end. The owed pay's road is reached when another
        end of the same file was owed while this one found nothing held (a concurrent pop in between), so the pay is stubbed
        to report that release taken."""
        km._AGENT_ENDED_UNHELD[(OTHER_SID, AID)] = self.agent            # an end remembered for the file
        real = em.checkpoint_pay_owed_releases
        em.checkpoint_pay_owed_releases = lambda: {self.agent: "released"}
        try:
            km._begin_checkpoint_cycle()
        finally:
            em.checkpoint_pay_owed_releases = real
        self.assertNotIn((OTHER_SID, AID), km._AGENT_ENDED_UNHELD, "the path's release forgot the remembered end")

    def test_a_remembered_release_that_pops_a_path_forgets_the_other_ends_remembered_for_it(self):
        """The remembered releases' road of the rule that a release popping a path forgets every end remembered for that path
        (kernel._forget_unheld_paths over the paths popped in the cycle): two ends remembered for one file, a whole read, one
        cycle. The first remembered end's release pops the file; the second's then finds nothing held and would stay
        remembered, and the popped path forgets it. A batch end's release adds its path to the popped paths too, and that is
        reached only when the remembered releases before it did not pop the path. Red when the popped paths forget nothing:
        the second end stays remembered."""
        km._AGENT_ENDED_UNHELD[(SID, WF_AID)] = self.agent               # two ends remembered for one file
        km._AGENT_ENDED_UNHELD[(OTHER_SID, AID)] = self.agent
        em._read_jsonl_incremental(self.agent)                           # a whole read holds it
        size = os.path.getsize(self.agent)
        self.assertEqual(self._weight(self.agent), size, "precondition: the read holds the whole file")
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "released at the cycle after the read")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}}, "by one release")
        self.assertEqual(km._AGENT_ENDED_UNHELD, {}, "the popped path forgot both remembered ends")

    # ---- an agent's later end after its earlier release was taken (PR 913 round 1, the texts' account of two ends) ----
    # An agent reports two ends (its stop and its task's end, or its workflow slot's done state), and the second can reach a
    # later cycle than the first's taken release. A re-read holding the file at that end is released by it; an end that finds
    # nothing held is remembered like any end seen while nothing was held, so the first whole re-read after it is released
    # at the next cycle. The whole re-reads after that release stay held (the residual event_model states beside
    # RECORD_CACHE_BUDGET_FLOOR_BYTES).

    def _stop_released_and_taken(self):
        self.s._on_task_event("task_started", {"task_id": AID, "task_type": "local_agent"})
        size = self._fold_while_running(AID, self.agent)
        km._begin_checkpoint_cycle()                                     # drains the start
        self._stop(AID)
        km._begin_checkpoint_cycle()                                     # the stop's release
        self.assertEqual(km._AGENT_RELEASED.get((SID, AID)), [self.agent, True], "precondition: the release was taken")
        return size

    def _task_end(self):
        self.s._on_task_event("task_notification", {"task_id": AID, "status": "completed"})
        self.assertEqual(list(self.be._agent_live_q), [(SID, AID, False)], "precondition: the task's end is queued")

    def test_a_later_end_after_a_taken_release_is_remembered_and_the_next_whole_re_read_released_once(self):
        size = self._stop_released_and_taken()
        self._task_end()
        km._begin_checkpoint_cycle()                                     # a cycle after the release: nothing held
        self.assertEqual(km._AGENT_ENDED_UNHELD.get((SID, AID)), self.agent, "the later end found nothing held: remembered")
        em._read_jsonl_incremental(self.agent)                           # a whole reader (the agent viewer) re-reads it
        self.assertEqual(self._weight(self.agent), size, "precondition: the re-read holds the whole file")
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "the first whole re-read after the later end is released at the next "
                          "cycle (held: %s of %d bytes)" % (self._weight(self.agent), size))
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 2, "bytes": 2 * size}})
        self.assertNotIn((SID, AID), km._AGENT_ENDED_UNHELD, "that release forgot the end")
        em._read_jsonl_incremental(self.agent)                           # read whole again, with no later end of the agent
        for _ in range(2):
            km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "a whole re-read after that release stays whole over two cycles")
        self.assertEqual(self._stat("released")["agentEnded"]["count"], 2, "and is not released")

    def test_a_later_end_after_a_taken_release_releases_a_re_read_that_holds_the_file(self):
        size = self._stop_released_and_taken()
        em._read_jsonl_incremental(self.agent)                           # a whole re-read before the later end
        self.assertEqual(self._weight(self.agent), size, "precondition: the re-read holds the whole file")
        self._task_end()
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "the later end released the re-read (held: %s of %d bytes)"
                          % (self._weight(self.agent), size))
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 2, "bytes": 2 * size}})
        self.assertNotIn((SID, AID), km._AGENT_ENDED_UNHELD, "nothing remembered")

    def test_a_later_end_in_the_cycle_whose_owed_pay_takes_the_release_is_remembered(self):
        self.s._on_task_event("task_started", {"task_id": AID, "task_type": "local_agent"})
        size = self._fold_while_running(AID, self.agent)
        km._begin_checkpoint_cycle()
        km.CKPT_CONVERGE_BYTES = 1                                       # no room for the document
        self._stop(AID)
        km._begin_checkpoint_cycle()
        self.assertEqual(em.owed_release_paths(), {self.agent}, "precondition: the stop's release is owed")
        self._task_end()
        km.CKPT_CONVERGE_BYTES = 8 * 1024 * 1024
        km._begin_checkpoint_cycle()                                     # the owed pay takes it, then the batch's end
        self.assertIsNone(self._weight(self.agent), "precondition: the owed release was paid")
        self.assertEqual(km._AGENT_RELEASED.get((SID, AID)), [self.agent, True], "recorded as taken")
        self.assertEqual(km._AGENT_ENDED_UNHELD.get((SID, AID)), self.agent, "the later end found nothing held: remembered")
        em._read_jsonl_incremental(self.agent)                           # a whole re-read
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "the re-read is released at the next cycle (held: %s of %d bytes)"
                          % (self._weight(self.agent), size))
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 2, "bytes": 2 * size}})

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
        self.assertEqual(self._stat("released", {}), NOTHING_RELEASED, "nothing was released")

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
        self.assertEqual((self._stat("releaseDeferred"), self._stat("releaseLost"), self._stat("released")), (1, 0, NOTHING_RELEASED),
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
        self.assertEqual((self._stat("releaseDeferred"), self._stat("released")), (1, NOTHING_RELEASED), "the release is owed, not taken")
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

    # ---- the cycle start's order (PR 913 round 1, group D) ----
    # The owed quiescent drops and the owed releases take their writes from the same budget as the batch's new ends, each
    # in one step, so whichever runs first gets the room when one document fits: each owed kind is paid before a new end.

    def _est(self, path):
        """_drop_write's estimate for a file with no document yet: half the room its write takes from the cycle's budget."""
        self.assertFalse(em._ckpt_file(path).exists(), "precondition: no document yet for %s" % os.path.basename(path))
        return max(4096, os.path.getsize(path) // 8)

    def test_an_owed_drop_is_paid_before_a_new_end_when_one_document_fits(self):
        """Red when _begin_checkpoint_cycle pays the ends (_release_ended_agents) before the owed drops: the release takes the
        room and the owed drop is deferred again."""
        self._fold_while_running(WF_AID, self.wf_agent)
        size = self._fold_while_running(AID, self.agent)
        km._begin_checkpoint_cycle()                                     # drains the two starts
        saved = em._DROP_AFTER_QUIESCENT_S
        em._DROP_AFTER_QUIESCENT_S = 0                                   # every file is quiescent: a fold that steps drops
        self.addCleanup(setattr, em, "_DROP_AFTER_QUIESCENT_S", saved)
        em.checkpoint_cycle_begin(1)                                     # no room: the workflow agent's drop is owed
        _append(self.wf_agent, _agent_lines(WF_AID, 45, 2))
        km._agent_launch_ids(self.wf_agent)                              # a quiescent fold that steps the appended records
        wf_size = os.path.getsize(self.wf_agent)
        self.assertEqual((self.wf_agent in em._DROP_OWED, self._weight(self.wf_agent)), (True, wf_size),
                         "precondition: the drop is owed, the entry whole")
        self._stop(AID)                                                  # an end new to the next cycle
        km.CKPT_CONVERGE_BYTES = max(2 * self._est(self.wf_agent), 2 * self._est(self.agent)) + 64   # one document fits
        w0 = em.checkpoint_stats()["converge"]["dropWrites"]
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.wf_agent), "the owed drop is paid (held: %s of %d bytes)"
                          % (self._weight(self.wf_agent), wf_size))
        self.assertNotIn(self.wf_agent, em._DROP_OWED, "and no longer owed")
        self.assertEqual(em.checkpoint_stats()["converge"]["dropWrites"], w0 + 1, "its document written")
        self.assertEqual(self._weight(self.agent), size, "the new end's release is deferred: the entry whole")
        self.assertEqual((self._stat("released"), self._stat("releaseDeferred")), (NOTHING_RELEASED, 1))

    def test_an_owed_release_is_paid_before_a_new_end_when_one_document_fits(self):
        """Red when _release_ended_agents pays the owed releases after the batch's ends: the new end takes the room and the
        owed release is deferred again."""
        size = self._fold_while_running(AID, self.agent)
        wf_size = self._fold_while_running(WF_AID, self.wf_agent)
        km._begin_checkpoint_cycle()                                     # drains the two starts
        km.CKPT_CONVERGE_BYTES = 1
        self._stop(AID)
        km._begin_checkpoint_cycle()                                     # no room: the release is owed
        self.assertEqual(em.owed_release_paths(), {self.agent}, "precondition: owed")
        self._stop(WF_AID)                                               # an end new to the next cycle
        km.CKPT_CONVERGE_BYTES = max(2 * self._est(self.agent), 2 * self._est(self.wf_agent)) + 64   # one document fits
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "the owed release is paid")
        self.assertEqual(self._weight(self.wf_agent), wf_size, "the new end's release is deferred: the entry whole")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}})
        self.assertEqual((self._stat("releaseDeferred"), em.owed_release_paths()), (2, {self.wf_agent}))

    def test_an_owed_release_is_cancelled_when_the_agent_starts_again(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        km.CKPT_CONVERGE_BYTES = 1                                       # the budget refuses the document: the release is owed
        km._begin_checkpoint_cycle()
        km.CKPT_CONVERGE_BYTES = 8 * 1024 * 1024
        self._start(AID)                                                 # resumed before the cycle that would pay it
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the running agent keeps its records")
        self.assertEqual((self._stat("released"), self._stat("falseEnds"), self._stat("releaseDeferred")), (NOTHING_RELEASED, 0, 1),
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

    # ---- a release only owed, never taken, counts no false end ----

    def _owed(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        km.CKPT_CONVERGE_BYTES = 1                                       # the budget refuses the document: the release is owed
        km._begin_checkpoint_cycle()
        km.CKPT_CONVERGE_BYTES = 8 * 1024 * 1024
        self.assertEqual((list(em._RELEASE_OWED), self._weight(self.agent)), ([self.agent], size), "precondition: owed")
        return size

    def test_an_owed_release_paid_as_absent_then_a_start_is_no_false_end(self):
        self._owed()
        with em._JSONL_CACHE_LOCK:
            em._cache_pop_locked(self.agent)                             # an eviction between the deferral and the pay
        km._begin_checkpoint_cycle()                                     # the owed release finds no entry
        held = (SID, AID) in km._AGENT_RELEASED
        self._start(AID)
        km._begin_checkpoint_cycle()
        self.assertEqual((self._stat("falseEnds"), self._stat("released")), (0, NOTHING_RELEASED), "no release taken, no false end")
        self.assertFalse(held, "the end whose release was not taken was forgotten at the pay")

    def test_an_owed_release_paid_as_lost_then_a_start_is_no_false_end(self):
        size = self._owed()
        km.CKPT_CONVERGE_MS = 0                                          # the drop writes off when the owed release is paid
        with contextlib.redirect_stderr(io.StringIO()):
            km._begin_checkpoint_cycle()
        self.assertEqual((self._stat("releaseLost"), self._weight(self.agent)), (1, size), "precondition: given up, entry kept")
        self._start(AID)
        km._begin_checkpoint_cycle()
        self.assertEqual((self._stat("falseEnds"), self._stat("released")), (0, NOTHING_RELEASED), "no release taken, no false end")

    def test_an_owed_release_forgotten_at_a_rebind_then_a_start_is_no_false_end(self):
        size = self._owed()
        em.set_checkpoint_dir(lambda: Path(os.path.join(self.root, "checkpoints-rebound")))
        self._start(AID)                                                 # a start in the batch of the next cycle
        km._begin_checkpoint_cycle()
        self.assertEqual((self._stat("falseEnds"), self._stat("released")), (0, NOTHING_RELEASED), "no release taken, no false end")
        self.assertEqual(self._weight(self.agent), size, "the entry is whole")

    def test_an_owed_release_given_up_at_its_bound_then_a_start_is_no_false_end(self):
        self._owed()
        saved = em._DROP_OWED_MAX
        em._DROP_OWED_MAX = 1
        self.addCleanup(setattr, em, "_DROP_OWED_MAX", saved)
        with contextlib.redirect_stderr(io.StringIO()):
            em._owe_release(os.path.join(self.root, "owed-other.jsonl"), "agentEnded")   # the agent's owed release is the oldest
        self.assertEqual(list(em._RELEASE_OWED), [os.path.join(self.root, "owed-other.jsonl")], "precondition: given up")
        self._start(AID)
        km._begin_checkpoint_cycle()
        self.assertEqual((self._stat("falseEnds"), self._stat("released")), (0, NOTHING_RELEASED), "no release taken, no false end")

    def test_the_pay_reports_the_outcome_of_every_owed_release(self):
        keys = [os.path.join(self.root, "owed-%d.jsonl" % i) for i in range(2)]
        for k in keys:
            em._owe_release(k, "agentEnded")
        real = em.release_entry

        def release(key, reason):
            if key == keys[0]:
                raise RuntimeError("synthetic")
            return real(key, reason)
        em.release_entry = release
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                paid = em.checkpoint_pay_owed_releases()
        finally:
            em.release_entry = real
        self.assertEqual(paid, {keys[0]: "raised", keys[1]: "absent"}, "one outcome per owed release, a raise included")

    def test_a_start_whose_session_path_no_longer_resolves_still_cancels_its_owed_release(self):
        size = self._owed()
        km._path_of = lambda sid, now=None: None                         # the session's transcript is not known at the start
        self._start(AID)
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the running agent keeps its records")
        self.assertEqual((em._RELEASE_OWED, self._stat("released"), self._stat("falseEnds")), ({}, NOTHING_RELEASED, 0),
                         "the release owed under the agent's path is cancelled, none taken, no false end")

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
        self._assert_raise_line(err.getvalue(), ("the owed release of " + self.agent,))   # PR 913 round 1, group G

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
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (2, NOTHING_RELEASED))

    def test_with_no_checkpoint_directory_the_release_keeps_the_entry_and_says_why(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        em.set_checkpoint_dir(lambda: None)                              # no checkpoint directory (tearDown binds one again)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the entry is kept")
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (1, NOTHING_RELEASED))
        self.assertIn("no checkpoint directory", err.getvalue(), "said under the writes-off cause, which names a missing "
                      "directory: %r" % err.getvalue())

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
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (1, NOTHING_RELEASED))
        self.assertIn("recordCache.releaseLost", err.getvalue())

    def test_a_write_that_fails_on_disk_keeps_the_entry(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        with open(self.ckdir, "w") as f:                                 # the checkpoint directory's path is a file: the
            f.write("not a directory\n")                                 #  document's write raises OSError
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the entry is kept")
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (1, NOTHING_RELEASED))
        self.assertIn("the file's checkpoint document could not be written", err.getvalue())

    def test_a_directory_unbound_after_the_release_checked_it_keeps_the_entry(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        real = em._path_needs_write

        def unbinding(*a, **k):                                          # the checkpoint directory is unbound after the release
            out = real(*a, **k)                                          #  checked it and before the write
            em.set_checkpoint_dir(lambda: None)
            return out
        em._path_needs_write = unbinding
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                km._begin_checkpoint_cycle()
        finally:
            em._path_needs_write = real
        self.assertEqual(self._weight(self.agent), size, "the entry is kept")
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (1, NOTHING_RELEASED))
        self.assertIn("the file's checkpoint document could not be written", err.getvalue())

    def test_a_release_whose_entry_is_evicted_before_its_write_is_absent_not_lost(self):
        self._fold_while_running(AID, self.agent)
        self._stop(AID)
        real = em.checkpoint_write

        def evicting_write(path, *a, **k):                               # a concurrent eviction takes the entry after the
            if str(path) == self.agent:                                  #  release read it and before its write does
                with em._JSONL_CACHE_LOCK:
                    em._cache_pop_locked(self.agent)
            return real(path, *a, **k)
        em.checkpoint_write = evicting_write
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                km._begin_checkpoint_cycle()
        finally:
            em.checkpoint_write = real
        self.assertIsNone(self._ent(self.agent), "precondition: the eviction took the entry")
        self.assertEqual((self._stat("releaseLost"), self._stat("releaseDeferred"), self._stat("released")), (0, 0, NOTHING_RELEASED),
                         "nothing given up, nothing owed, nothing released")
        self.assertEqual(err.getvalue(), "", "nothing said on stderr")
        self.assertEqual(km._AGENT_RELEASED, {}, "no release taken or owed for the end")

    def _evicted_after_the_write(self):
        """Stub the document write so that, once it has written, an eviction pops the agent's entry, the way another path's
        insert does between the release's write and its pop. Returns the list the stub fills with each write's result."""
        real, fired = em.checkpoint_write, []

        def write_then_evict(path, *a, **k):
            out = real(path, *a, **k)
            if str(path) == self.agent:
                fired.append(out)
                with em._JSONL_CACHE_LOCK:
                    em._cache_pop_locked(self.agent)
            return out
        em.checkpoint_write = write_then_evict
        self.addCleanup(setattr, em, "checkpoint_write", real)
        return fired

    def test_a_release_whose_entry_is_evicted_after_its_write_is_absent_not_owed(self):
        """PR 913 round 1, group B: a concurrent pop after the document write and before the release's pop leaves nothing
        held, so nothing is deferred or owed; the end is remembered as one that found nothing held (group H)."""
        self._fold_while_running(AID, self.agent)
        self._stop(AID)
        fired = self._evicted_after_the_write()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual(fired, [True], "precondition: the release wrote the document")
        self.assertIsNone(self._ent(self.agent), "precondition: the eviction took the entry")
        self.assertEqual((self._stat("releaseDeferred"), self._stat("releaseLost"), self._stat("released")),
                         (0, 0, NOTHING_RELEASED), "nothing deferred, lost or released")
        self.assertEqual((em.owed_release_paths(), km._AGENT_RELEASED), (set(), {}), "nothing owed, no release recorded")
        self.assertEqual(km._AGENT_ENDED_UNHELD.get((SID, AID)), self.agent, "remembered as an end that found nothing held")
        self.assertEqual(err.getvalue(), "", "nothing said on stderr")

    def test_an_owed_release_whose_entry_is_evicted_after_its_write_is_absent_and_remembered(self):
        """Group B on the owed releases' pay: the same pop after the write answers "absent" there too, so the release is not
        owed again, and the end is remembered (group H's owed road)."""
        self._owed()
        fired = self._evicted_after_the_write()
        with contextlib.redirect_stderr(io.StringIO()):
            km._begin_checkpoint_cycle()                                 # the pay writes the document, and the entry goes
        self.assertEqual(fired, [True], "precondition: the pay wrote the document")
        self.assertEqual((self._stat("releaseDeferred"), em.owed_release_paths()), (1, set()),
                         "the one deferral before the pay, and nothing owed after it")
        self.assertNotIn((SID, AID), km._AGENT_RELEASED, "no release taken or owed for the end")
        self.assertEqual(km._AGENT_ENDED_UNHELD.get((SID, AID)), self.agent, "remembered as an end that found nothing held")

    def test_a_failed_write_after_a_read_replaced_the_entry_is_owed_not_lost(self):
        self._fold_while_running(AID, self.agent)
        self._stop(AID)
        real = em.checkpoint_write

        def replaced_then_failed(path, *a, **k):                         # a read of the grown file replaces the entry, and the
            if str(path) == self.agent:                                  #  write fails
                _append(self.agent, _agent_lines(AID, 45, 2))
                em._read_jsonl_incremental(self.agent)
                return False
            return real(path, *a, **k)
        em.checkpoint_write = replaced_then_failed
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                km._begin_checkpoint_cycle()
        finally:
            em.checkpoint_write = real
        grown = os.path.getsize(self.agent)
        self.assertEqual(self._weight(self.agent), grown, "the newer entry stands")
        self.assertEqual((self._stat("releaseDeferred"), self._stat("releaseLost"), self._stat("released")), (1, 0, NOTHING_RELEASED),
                         "owed, not lost")
        self.assertEqual(err.getvalue(), "", "nothing said on stderr")
        km._begin_checkpoint_cycle()                                     # the next cycle pays it
        self.assertIsNone(self._weight(self.agent), "released at the next cycle")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": grown}})

    def _dirty_at_an_older_read(self, budget):
        """The folds stepped the file (the path is dirty), then an eviction and a whole read (the agent viewer) left an entry of
        a new generation with no fold's cursor at it; the agent ends and a cycle with `budget` bytes runs."""
        self._fold_while_running(AID, self.agent)
        self.assertIn(self.agent, em.checkpoint_dirty(), "precondition: the path is dirty")
        with em._JSONL_CACHE_LOCK:
            em._cache_pop_locked(self.agent)
        em._read_jsonl_incremental(self.agent)
        size = os.path.getsize(self.agent)
        self.assertEqual(self._weight(self.agent), size, "precondition: a whole entry")
        self._stop(AID)
        km.CKPT_CONVERGE_BYTES = budget
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "released")
        self.assertEqual((self._stat("releaseLost"), self._stat("releaseDeferred"), self._stat("released")),
                         (0, 0, {"agentEnded": {"count": 1, "bytes": size}}), "released in this cycle, nothing given up or owed")
        self.assertFalse(em._ckpt_file(self.agent).exists(), "no document: nothing held here was recordable")
        self.assertEqual(err.getvalue(), "", "nothing said on stderr")

    def test_a_dirty_file_whose_folds_stand_at_an_older_read_is_released_without_a_document(self):
        self._dirty_at_an_older_read(8 * 1024 * 1024)

    def test_a_dirty_file_whose_folds_stand_at_an_older_read_waits_on_no_budget(self):
        self._dirty_at_an_older_read(1)                                  # no room for a document, and none is needed

    def test_a_write_that_finds_nothing_to_record_is_released_without_a_document(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        real = em.checkpoint_write

        def nothing(path, force=False, why=None):                        # the write finds no fold's cursor to record (one moved
            if why is not None:                                          #  after the check, say)
                why.append("nothingRecordable")
            return False
        em.checkpoint_write = nothing
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                km._begin_checkpoint_cycle()
        finally:
            em.checkpoint_write = real
        self.assertIsNone(self._weight(self.agent), "released")
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (0, {"agentEnded": {"count": 1, "bytes": size}}))
        self.assertEqual(err.getvalue(), "", "nothing said on stderr")

    def test_a_write_whose_cut_cannot_be_moved_keeps_the_entry(self):
        self._fold_while_running(AID, self.agent)                        # every fold's cursor at the entry's last record
        _append(self.agent, _agent_lines(AID, 45, 2))
        em._read_jsonl_incremental(self.agent)                           # the whole reader appends: every fold lags the entry
        size = os.path.getsize(self.agent)
        with open(self.agent, "r+b") as f:                               # the file's last bytes are rewritten in place, same
            data = bytearray(f.read())                                   #  size: the entry's own guard no longer matches, so
            i = data.rindex(b"schema")                                   #  the lagging folds' cut cannot be moved
            data[i:i + 6] = b"SCHEMA"
            f.seek(0); f.write(bytes(data))
        self._stop(AID)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the entry is kept")
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (1, NOTHING_RELEASED))
        self.assertIn("the file's checkpoint document could not be written", err.getvalue())

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
        self.assertEqual((self._stat("releaseLost"), self._stat("released")), (1, NOTHING_RELEASED))
        self.assertIn("the document check raised RuntimeError (counted as recordCache.releaseLost", err.getvalue())
        self._assert_raise_line(err.getvalue(), ("the document check of " + self.agent,))   # PR 913 round 1, group G

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

    def test_an_owed_release_whose_file_is_gone_is_released_with_the_drop_writes_off(self):
        size = self._fold_while_running(AID, self.agent)
        self._stop(AID)
        km.CKPT_CONVERGE_BYTES = 1                                       # deferred for the budget, the drop writes still on
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "precondition: the release is owed")
        os.unlink(self.agent)
        km.CKPT_CONVERGE_BYTES = 8 * 1024 * 1024
        km.CKPT_CONVERGE_MS = 0                                          # the drop writes off only when the owed release is paid
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "released: nothing to write, everything to release")
        self.assertEqual((self._stat("released"), self._stat("releaseLost")), ({"agentEnded": {"count": 1, "bytes": size}}, 0))

    def test_an_end_dropped_past_the_queue_bound_is_released_at_the_drain(self):
        """PR 913 round 1, decision 4: a dropped end is kept as its (sid, agent id) pair and released at the drain like a
        batch end, not counted lost."""
        size = self._fold_while_running(AID, self.agent)
        km._begin_checkpoint_cycle()                                     # drains the start
        self.be._AGENT_LIVE_MAX = 2                                      # this backend's bound, for the test
        # the queue holds two, so stop(WF_AID) drops stop(AID): the batch holds no later event for AID
        self._stop(AID); self._start(WF_AID); self._stop(WF_AID)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("releaseLost"), 0, "the end dropped past the queue's bound is not a release given up")
        self.assertIsNone(self._weight(self.agent), "released at the drain (held: %s of %d bytes)" % (self._weight(self.agent), size))
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}})
        self.assertNotIn("recordCache.releaseLost", err.getvalue())
        self.assertEqual(self.be.drain_agent_live_events(), ([], 0), "the drain took the dropped end with the batch")

    def test_a_dropped_end_whose_agent_the_batch_speaks_for_later_is_not_released_by_the_drop(self):
        """A dropped end is released at the drain only when the batch holds no later event for its agent: a later start keeps
        the agent's records (a later end releasing is pinned by test_a_dropped_stop_whose_task_end_releases_counts_nothing_lost)."""
        size = self._fold_while_running(AID, self.agent)
        km._begin_checkpoint_cycle()
        self.be._AGENT_LIVE_MAX = 2
        self._stop(AID); self._start(AID); self._start(WF_AID)            # start(WF_AID) drops stop(AID); the start stays
        self.assertEqual(self.be._agent_live_dropped, {(SID, AID): True}, "precondition: the dropped end is kept")
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the agent started again after the dropped end: its records stay")
        self.assertEqual((self._stat("released"), self._stat("releaseLost"), self._stat("falseEnds")), (NOTHING_RELEASED, 0, 0))

    def test_a_start_dropped_after_its_agents_dropped_end_forgets_that_end(self):
        size = self._fold_while_running(AID, self.agent)
        km._begin_checkpoint_cycle()
        self.be._AGENT_LIVE_MAX = 2
        self._stop(AID); self._start(AID); self._start(WF_AID); self._stop(WF_AID)   # both of AID's events dropped, the start last
        self.assertEqual(self.be._agent_live_dropped, {}, "the dropped start forgot the pair's dropped end")
        km._begin_checkpoint_cycle()
        self.assertEqual(self._weight(self.agent), size, "the running agent keeps its records")
        self.assertEqual(self._stat("releaseLost"), 0)

    def test_starts_dropped_past_the_queue_bound_are_not_releases_given_up(self):
        self.be._AGENT_LIVE_MAX = 2
        # stop(AID) drops start(AID) and stop(WF_AID) drops start(WF_AID): both events dropped are starts
        self._start(AID); self._start(WF_AID); self._stop(AID); self._stop(WF_AID)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("releaseLost"), 0, "the two events dropped past the bound were starts: none is counted")
        self.assertNotIn("recordCache.releaseLost", err.getvalue())

    def test_the_ends_dropped_past_the_bound_of_the_kept_pairs_are_counted_lost(self):
        """Decision 4: releaseLost counts only the dropped ends given up past the bound of the pairs the backend keeps (the
        queue's bound, _AGENT_LIVE_MAX). The oldest pair is the one given up: its entry stays; the pairs kept are released."""
        agent3 = os.path.join(os.path.dirname(self.agent), "agent-%s.jsonl" % AID3)
        _append(agent3, _agent_lines(AID3, 0, 40))
        em._read_jsonl_incremental(self.agent); em._read_jsonl_incremental(agent3)   # whole entries for the releases to take
        size, size3 = os.path.getsize(self.agent), os.path.getsize(agent3)
        self.be._AGENT_LIVE_MAX = 2
        # stop(AID3) drops stop(AID), stop(WF_AID2) drops stop(WF_AID), and the next end drops stop(AID3): three pairs kept
        # past a bound of two, so the oldest, AID's, is given up
        for aid in (AID, WF_AID, AID3, WF_AID2, "a5555555555555555"):
            self._stop(aid)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("releaseLost"), 1, "the one pair past the bound is the one release given up")
        self.assertIn("recordCache.releaseLost", err.getvalue())
        self.assertEqual(self._weight(self.agent), size, "the given-up agent's entry stays")
        self.assertIsNone(self._weight(agent3), "a kept pair is released at the drain")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size3}})
        km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("releaseLost"), 1, "a later cycle adds nothing")

    # ---- the release counters count releases, not ends (PR 913 round 1, group C) ----
    # An agent reports two ends (its stop and its task's end, or a workflow slot's done state), and a cycle's owed pay and
    # its batch can each try the same path: releaseDeferred and releaseLost count a path once per cycle.

    def _two_ends_under_a_refused_budget(self, aid, path, second_end):
        km.CKPT_CONVERGE_BYTES = 1                                       # no room for the document, every cycle below
        self._stop(aid)
        km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("releaseDeferred"), 1, "the stop's release is deferred once")
        second_end()
        self.assertEqual(list(self.be._agent_live_q), [(SID, aid, False)], "precondition: the second end is queued")
        km._begin_checkpoint_cycle()                                     # the owed pay, then the batch's end, try the one path
        self.assertEqual(self._stat("releaseDeferred"), 2, "one per refused cycle: the second end in that cycle adds nothing")
        self.assertEqual((self._weight(path), em.owed_release_paths()), (os.path.getsize(path), {path}), "still whole, owed")

    def test_a_workflow_agents_stop_then_slot_done_count_one_deferral_per_cycle(self):
        self.s._on_task_event("task_started", {"task_id": WF_TID, "task_type": "local_workflow"})
        self._fold_while_running(WF_AID, self.wf_agent)
        self.s._on_task_event("task_progress", {"task_id": WF_TID, "workflow_progress": [_wf(1, WF_AID, "progress")]})
        km._begin_checkpoint_cycle()                                     # drains the start
        self._two_ends_under_a_refused_budget(WF_AID, self.wf_agent, lambda: self.s._on_task_event(
            "task_progress", {"task_id": WF_TID, "workflow_progress": [_wf(1, WF_AID, "done")]}))

    def test_a_task_agents_stop_then_task_end_count_one_deferral_per_cycle(self):
        self.s._on_task_event("task_started", {"task_id": AID, "task_type": "local_agent"})
        self._fold_while_running(AID, self.agent)
        km._begin_checkpoint_cycle()
        self._two_ends_under_a_refused_budget(AID, self.agent, lambda: self.s._on_task_event(
            "task_notification", {"task_id": AID, "status": "completed"}))

    def test_a_dropped_stop_whose_task_end_releases_counts_nothing_lost(self):
        self.s._on_task_event("task_started", {"task_id": AID, "task_type": "local_agent"})
        size = self._fold_while_running(AID, self.agent)
        km._begin_checkpoint_cycle()
        self.be._AGENT_LIVE_MAX = 2
        self._stop(AID)
        self.s._on_task_event("task_notification", {"task_id": AID, "status": "completed"})
        self._start(WF_AID)                                              # drops the stop; the task's end survives
        self.assertEqual(list(self.be._agent_live_q), [(SID, AID, False), (SID, WF_AID, True)],
                         "precondition: the stop was dropped, the task's end kept")
        with contextlib.redirect_stderr(io.StringIO()):
            km._begin_checkpoint_cycle()
        self.assertEqual((self._stat("released"), self._stat("releaseLost")), ({"agentEnded": {"count": 1, "bytes": size}}, 0),
                         "one release, and nothing given up")

    def test_an_owed_release_lost_at_the_pay_and_a_second_end_in_that_cycle_count_one_loss(self):
        self.s._on_task_event("task_started", {"task_id": AID, "task_type": "local_agent"})
        size = self._fold_while_running(AID, self.agent)
        km._begin_checkpoint_cycle()
        km.CKPT_CONVERGE_BYTES = 1
        self._stop(AID)
        km._begin_checkpoint_cycle()                                     # the stop's release is owed
        self.assertEqual(em.owed_release_paths(), {self.agent}, "precondition: owed")
        self.s._on_task_event("task_notification", {"task_id": AID, "status": "completed"})   # the second end
        km.CKPT_CONVERGE_BYTES = 8 * 1024 * 1024
        km.CKPT_CONVERGE_MS = 0                                          # the drop writes off: the pay and the end are each lost
        with contextlib.redirect_stderr(io.StringIO()):
            km._begin_checkpoint_cycle()
        self.assertEqual((self._stat("releaseLost"), self._weight(self.agent)), (1, size), "one release given up, the entry kept")

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
        self._assert_raise_line(err.getvalue(), (OTHER_SID, WF_AID2, "its file not resolved"))   # PR 913 round 1, group G
        asyncio.run(other._subagent_start_hook({"agent_id": WF_AID2, "agent_type": "general-purpose"}, None, None))
        asyncio.run(other._subagent_stop_hook({"agent_id": WF_AID2}, None, None))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("releaseLost"), 2, "counted again")
        self._assert_raise_line(err.getvalue(), (OTHER_SID, WF_AID2))
        self.assertNotIn("recordCache.releaseLost; said once", err.getvalue(), "the cause's summary line is said once")

    def _assert_raise_line(self, out, names):
        """A release that raised wrote its own line: the names given, the exception's text and a traceback."""
        line = [ln for ln in out.splitlines() if ln.startswith("record cache: ") and " raised; the release is given up" in ln]
        self.assertEqual(len(line), 1, "one line for the raise: %r" % out)
        for n in names:
            self.assertIn(n, line[0], "the line names %s: %r" % (n, line[0]))
        self.assertIn("Traceback (most recent call last)", out, "with the traceback: %r" % out)
        self.assertIn("RuntimeError: synthetic", out, "and the exception's text: %r" % out)

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
        self.assertEqual(self._stat("released"), NOTHING_RELEASED, "nothing released")
        self.assertEqual(self._weight(self.agent), size, "the entry is whole")
        for d in (self.ckdir, other):
            self.assertEqual([f for _r, _d, fs in os.walk(d) for f in fs], [], "no document in %s" % os.path.basename(d))
        self._start(AID)                                                 # the agent starts again after the forgotten release
        km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("falseEnds"), 0, "a release forgotten, never taken, counts no false end")

    def test_a_cycle_over_a_backend_without_the_queue_does_nothing(self):
        for be in (None, False, object()):                               # not built, unavailable, a double without the queue
            km._sdk_backend = be
            km._begin_checkpoint_cycle()
        self.assertEqual(self._stat("released"), NOTHING_RELEASED)

    # ---- /perf ----

    def test_perf_carries_the_release_counters_and_the_maximum(self):
        st = em.record_cache_stats()
        self.assertEqual(sorted(st), sorted(["entries", "bytes", "bytesMax", "budgetBytes", "countCap", "inserts", "evictions",
                                             "evictedBytes", "budgetEvictions", "dropped", "droppedBytes", "wholeReads",
                                             "wholeReadsByStage", "released", "releaseDeferred", "releaseLost", "falseEnds",
                                             "releasedReread"]))
        self.assertEqual((st["released"], st["releasedReread"]), (NOTHING_RELEASED, {"count": 0, "bytes": 0}), "tables, even when zeroed")
        self.assertEqual(jd._SERVE_GAUGES["recordCache"], ("entries", "bytes", "bytesMax", "budgetBytes", "countCap"),
                         "bytesMax is the one new gauge")



# ---- the census of the places an agent leaves what a session knows (PR 913 round 1, group A; tests-2) ----

ROOT = os.path.dirname(HERE)
CENSUS_FILES = ("kernel/sdk_backend.py", "kernel/kernel.py")
CENSUS_STRUCTS = frozenset(("_subagents", "_bg_tasks", "_seeded_tasks", "_reported_tasks", "_wf_agents", "_wf_slots", "_wf_ended"))
CENSUS_REMOVES = frozenset(("_subagents", "_bg_tasks", "_wf_agents", "_wf_slots"))   # a QUEUES site over these needs the call AFTER it
CENSUS_METHODS = frozenset(("pop", "clear", "popitem", "discard", "remove", "difference_update", "intersection_update",
                            "symmetric_difference_update"))
CENSUS_ALIAS_FROM = frozenset(("get", "setdefault"))   # a local bound from one of these (or a subscript) of a structure is its alias
CENSUS_QUEUE_CALLS = {"_note_live_agents": 1, "note_agent_live": 2}   # the call that queues, and the index of its `live` argument
MIRROR, SESSIONS = "bgTasks mirror", "sessions"
Q, X, ADD, DROP = "QUEUES", "EXEMPT", "ADD", "DROP"
SB = "kernel/sdk_backend.py"
_MARKER = "a marker set over _bg_tasks rows"
_TASK_EVENT_MARKER = _MARKER + ": the row stays (a start or progress frame) or leaves at the task end's _bg_tasks pop"
_REPORT_MARKER = (_MARKER + ": a retired row leaves at one of this function's _bg_tasks pops, and every other row stays in "
                  "_bg_tasks")
_ROW_ADDED = "a _bg_tasks row added, guarded by the id's absence"
_ENDS_QUEUED = ("the record of ends already queued: it names no live agent, and a repeated end is harmless (in the cycle of "
                "an earlier attempt it counts nothing; with the drop writes off a repeat in a later cycle counts again)")
_GONE_ROAD = ("SdkBackend._on_session_gone, which queues every agent the dropped object knows when it is not detached, after "
              "this drop, as the object's thread ends")
# (file, enclosing function, structure, operation) -> one (verdict, the executed road test that proves it, or the reason) per
# site, in source order. QUEUES: the site's function calls _note_live_agents(..., False) or note_agent_live(..., False)
# after a removal of a _subagents entry, a _bg_tasks row or a roster, and anywhere for a mirror write; ADD: a call with
# True after it; EXEMPT and DROP: the reason.
RELEASE_CENSUS = {
    (SB, "SdkSession._subagent_start_hook", "_subagents", "setitem"): [
        (ADD, "test_a_resumed_agent_is_a_false_end_and_appends_to_its_tail")],
    (SB, "SdkSession._subagent_stop_hook", "_subagents", "pop"): [
        (Q, "test_an_agent_folded_while_it_ran_is_released_at_its_stop_hook")],
    (SB, "SdkSession._drop_live_work", "_subagents", "clear"): [(Q, "test_an_agent_is_released_when_its_cli_is_torn_down")],
    (SB, "SdkSession._drop_live_work", "_wf_agents", "clear"): [
        (Q, "test_a_reattached_objects_roster_agent_ends_when_its_cli_is_torn_down")],
    (SB, "SdkSession._drop_live_work", "_wf_slots", "clear"): [
        (Q, "test_a_reattached_objects_roster_agent_ends_when_its_cli_is_torn_down")],
    (SB, "SdkSession._drop_live_work", "_wf_ended", "clear"): [(X, _ENDS_QUEUED)],
    (SB, "SdkSession._drop_live_work", "_bg_tasks", "clear"): [
        (Q, "test_a_reattached_objects_seeded_agent_row_ends_when_its_cli_is_torn_down")],
    (SB, "SdkSession._drop_live_work", "_seeded_tasks", "clear"): [(X, _MARKER + ", cleared with the rows (the _bg_tasks clear)")],
    (SB, "SdkSession._drop_live_work", "_reported_tasks", "clear"): [(X, _MARKER + ", cleared with the rows (the _bg_tasks clear)")],
    (SB, "SdkSession._drop_live_work", MIRROR, "_update_reg"): [
        (Q, "test_a_reattached_objects_seeded_agent_row_ends_when_its_cli_is_torn_down")],
    (SB, "SdkSession._reconcile_workflow_agents", "_wf_slots", "setitem (alias)"): [
        (Q, "test_a_workflow_agent_is_released_when_its_slot_is_re_minted")],
    (SB, "SdkSession._reconcile_workflow_agents", "_wf_agents", "pop"): [(Q, "test_a_workflow_agent_is_released_at_its_run_end")],
    (SB, "SdkSession._reconcile_workflow_agents", "_wf_slots", "pop"): [(Q, "test_a_workflow_agent_is_released_at_its_run_end")],
    (SB, "SdkSession._reconcile_workflow_agents", "_wf_ended", "pop"): [(X, _ENDS_QUEUED)],
    (SB, "SdkSession._reconcile_workflow_agents", "_subagents", "pop"): [
        (Q, "test_a_workflow_agent_is_released_when_its_slot_reports_done")],
    (SB, "SdkSession._on_task_event", "_seeded_tasks", "discard"): [(X, _TASK_EVENT_MARKER)],
    (SB, "SdkSession._on_task_event", "_reported_tasks", "discard"): [(X, _TASK_EVENT_MARKER)],
    (SB, "SdkSession._on_task_event", "_bg_tasks", "setitem"): [(X, _ROW_ADDED)],
    (SB, "SdkSession._on_task_event", "_bg_tasks", "setitem (alias)"): [(X, "a field of a standing row")] * 4,
    (SB, "SdkSession._on_task_event", "_bg_tasks", "pop"): [
        (Q, "test_a_reattached_object_queues_the_end_at_the_agents_task_end_and_not_a_shells")],
    (SB, "SdkSession._on_task_event", "_subagents", "pop"): [
        (Q, "test_an_agent_folded_while_it_ran_is_released_at_its_own_task_end")],
    (SB, "SdkSession._on_task_event", MIRROR, "_update_reg"): [
        (Q, "test_a_reattached_object_queues_the_end_at_the_agents_task_end_and_not_a_shells")],
    (SB, "SdkSession._seed_live_work_from_reg", "_bg_tasks", "setitem"): [(X, _ROW_ADDED)],
    (SB, "SdkSession._reconcile_seeded_with_report", "_bg_tasks", "setitem"): [(X, _ROW_ADDED)],
    (SB, "SdkSession._reconcile_seeded_with_report", "_bg_tasks", "pop"): [
        (Q, "test_a_reattached_objects_seeded_agent_row_ends_when_the_report_lists_it_ended"),
        (X, "a row the report omits: only a shell reaches it (report_absence_decides), and a shell names no agent; the type "
            "test runs over both retired lists, so this stays right if the predicate widens")],
    (SB, "SdkSession._reconcile_seeded_with_report", "_seeded_tasks", "clear"): [(X, _REPORT_MARKER)],
    (SB, "SdkSession._reconcile_seeded_with_report", "_reported_tasks", "difference_update"): [(X, _REPORT_MARKER)],
    (SB, "SdkSession._reconcile_seeded_with_report", MIRROR, "_update_reg"): [
        (Q, "test_an_adopted_agent_row_ends_when_a_later_report_lists_it_ended")],
    (SB, "SdkBackend._boot_reconcile", MIRROR, "setitem"): [
        (Q, "test_a_dead_mirrors_agent_row_at_boot_is_released_after_a_read_holds_its_file")],
    (SB, "SdkBackend._ensure", MIRROR, "setitem"): [
        (Q, "test_a_threads_wake_over_a_dead_mirrors_agent_row_releases_its_held_file")] * 2,
    (SB, "SdkBackend._ensure", SESSIONS, "setitem"): [
        (DROP, "replaces an object whose thread has ended (a live one is returned instead); that thread's end ran "
               "SdkBackend._on_session_gone")],
    (SB, "SdkBackend.kill", SESSIONS, "pop"): [(DROP, "ends the session's thread, whose end runs " + _GONE_ROAD)],
    (SB, "SdkBackend.conserve_close", SESSIONS, "pop"): [(DROP, "ends the session's thread, whose end runs " + _GONE_ROAD)],
    (SB, "SdkBackend._on_session_gone", SESSIONS, "pop"): [(DROP, "inside " + _GONE_ROAD)],
    (SB, "SdkBackend._on_session_gone", "_subagents", "clear"): [
        (Q, "test_a_reattached_objects_seeded_agent_row_ends_when_its_cli_dies_while_idle")],
    (SB, "SdkBackend._on_session_gone", MIRROR, "setitem"): [
        (Q, "test_a_reattached_objects_seeded_agent_row_ends_when_its_cli_dies_while_idle")],
    (SB, "SdkBackend._heal_cut_session", SESSIONS, "pop"): [(DROP, "called by and inside " + _GONE_ROAD)] * 2,
}
CENSUS_NOT_COVERAGE = (
    "The census proves classification, not coverage: that a queue call follows a site cannot show that the call queues what "
    "the site removed (the rosters and rows _drop_live_work clears sit in a function whose _subagents queue call already "
    "follows them). What proves each QUEUES site is the executed road test named beside it.")


def _census_scopes(tree):
    """[(qualified name, the nodes it owns)] for the module and every function: a nested def owns its own body, a class only
    prefixes its methods' names, and a lambda's body belongs to the function around it. Reads the tree only."""
    mod = []
    out = [("<module>", mod)]

    def visit(node, qual, own):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = (qual + "." if qual else "") + child.name
                mine = []
                out.append((q, mine))
                visit(child, q, mine)
            elif isinstance(child, ast.ClassDef):
                visit(child, (qual + "." if qual else "") + child.name, own)
            else:
                own.append(child)
                visit(child, qual, own)
    visit(tree, "", mod)
    return out


def _census_targets(t):
    if isinstance(t, (ast.Tuple, ast.List)):
        for e in t.elts:
            yield from _census_targets(e)
    elif isinstance(t, ast.Starred):
        yield from _census_targets(t.value)
    else:
        yield t


def _census_struct(node):
    return node.attr if isinstance(node, ast.Attribute) and node.attr in CENSUS_STRUCTS else None


def release_census(trees):
    """Every site in `trees` ([(file, tree)]) at which an entry leaves, or is written into, what a session knows of its
    agents: a pop, clear, popitem, discard, remove or set update, a del of a subscript, a `-=` or `&=`, a rebinding outside
    __init__, and a subscript assignment (directly, or through a local alias bound from a structure's get, setdefault or
    subscript), on any receiver, over CENSUS_STRUCTS; every write of the reg's bgTasks mirror (_update_reg's bgTasks keyword,
    a subscript assignment to "bgTasks"); and every drop of a session object from `sessions` (those methods, a del, a
    subscript assignment). Returns ([(file, function, structure, operation, line)], {(file, function): [(line, live)]}), the
    second the queue calls of each function (`live` the literal, or None when it is not one)."""
    sites, queues = [], {}
    for rel, tree in trees:
        for qual, nodes in _census_scopes(tree):
            alias = {}
            for n in nodes:
                binds = ([(t, n.value) for t in n.targets] if isinstance(n, ast.Assign)
                         else [(n.target, n.value)] if isinstance(n, ast.NamedExpr) else [])
                for t, v in binds:
                    src = None
                    if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr in CENSUS_ALIAS_FROM:
                        src = _census_struct(v.func.value)
                    elif isinstance(v, ast.Subscript):
                        src = _census_struct(v.value)
                    if src and isinstance(t, ast.Name):
                        alias[t.id] = src

            def recv(node):
                st = _census_struct(node)
                if st:
                    return st, ""
                if isinstance(node, ast.Name) and node.id in alias:
                    return alias[node.id], " (alias)"
                return None, ""

            def is_sessions(node):
                return isinstance(node, ast.Attribute) and node.attr == SESSIONS
            calls = []
            fn = qual.rsplit(".", 1)[-1]
            for n in nodes:
                ln = getattr(n, "lineno", 0)
                if isinstance(n, ast.Call) and isinstance(n.func, (ast.Attribute, ast.Name)):
                    name = n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id
                    if name in CENSUS_QUEUE_CALLS:
                        i = CENSUS_QUEUE_CALLS[name]
                        arg = n.args[i] if len(n.args) > i else next((k.value for k in n.keywords if k.arg == "live"), None)
                        calls.append((ln, arg.value if isinstance(arg, ast.Constant) else None))
                    if isinstance(n.func, ast.Attribute) and n.func.attr in CENSUS_METHODS:
                        st, how = recv(n.func.value)
                        if st:
                            sites.append((rel, qual, st, n.func.attr + how, ln))
                        elif is_sessions(n.func.value):
                            sites.append((rel, qual, SESSIONS, n.func.attr, ln))
                    if name == "_update_reg" and any(k.arg == "bgTasks" for k in n.keywords):
                        sites.append((rel, qual, MIRROR, "_update_reg", ln))
                elif isinstance(n, ast.Delete):
                    for x in (x for t in n.targets for x in _census_targets(t)):
                        if isinstance(x, ast.Subscript):
                            st, how = recv(x.value)
                            if st:
                                sites.append((rel, qual, st, "del" + how, ln))
                            elif is_sessions(x.value):
                                sites.append((rel, qual, SESSIONS, "del", ln))
                elif isinstance(n, ast.AugAssign):
                    st = _census_struct(n.target)
                    if st and isinstance(n.op, (ast.Sub, ast.BitAnd)):
                        sites.append((rel, qual, st, "-=" if isinstance(n.op, ast.Sub) else "&=", ln))
                    elif isinstance(n.target, ast.Subscript):
                        st, how = recv(n.target.value)
                        if st:
                            sites.append((rel, qual, st, "setitem" + how, ln))
                elif isinstance(n, (ast.Assign, ast.AnnAssign)):
                    for x in (x for t in (n.targets if isinstance(n, ast.Assign) else [n.target]) for x in _census_targets(t)):
                        if _census_struct(x):
                            if fn != "__init__":
                                sites.append((rel, qual, x.attr, "rebind", ln))
                        elif isinstance(x, ast.Subscript):
                            st, how = recv(x.value)
                            if st:
                                sites.append((rel, qual, st, "setitem" + how, ln))
                            elif isinstance(x.slice, ast.Constant) and x.slice.value == "bgTasks":
                                sites.append((rel, qual, MIRROR, "setitem", ln))
                            elif is_sessions(x.value):
                                sites.append((rel, qual, SESSIONS, "setitem", ln))
            queues[(rel, qual)] = calls
    return sites, queues


def release_census_problems(trees, table=None):
    """The census's findings against the recorded table (RELEASE_CENSUS), one line each; [] when they agree. Fails on: nothing
    found; a (file, function, structure, operation) the source has more or fewer times than the table; a QUEUES site whose
    function lacks the queue call its kind needs, and an ADD site with no start queued after it; a named road test that does
    not exist in this module."""
    table = RELEASE_CENSUS if table is None else table
    sites, queues = release_census(trees)
    if not sites:
        return ["the census found nothing in %s: a file moved, or every structure was renamed" % ", ".join(r for r, _t in trees)]
    probs = []
    found = Counter(s[:4] for s in sites)
    want = Counter({k: len(v) for k, v in table.items()})
    for k in sorted(set(found) | set(want)):
        if found[k] != want[k]:
            lines = [s[4] for s in sites if s[:4] == k]
            probs.append("%s %s: %s %s found %d time%s (lines %s), the table records %d" % (
                k[0], k[1], k[2], k[3], found[k], "" if found[k] == 1 else "s", lines or "none", want[k]))
    by_key = {}
    for s in sorted(sites, key=lambda s: (s[0], s[4])):
        by_key.setdefault(s[:4], []).append(s[4])
    for k, lines in by_key.items():
        for ln, (verdict, why) in zip(lines, table.get(k, [])):
            calls = queues.get((k[0], k[1]), [])
            if verdict == Q:
                after = k[2] in CENSUS_REMOVES
                if not any(live is False and (ln < cl or not after) for cl, live in calls):
                    probs.append("%s %s line %d: %s %s is recorded QUEUES (%s), and the function has no "
                                 "_note_live_agents(..., False) or note_agent_live(..., False) %s" % (
                                     k[0], k[1], ln, k[2], k[3], why, "after it" if after else "anywhere in it"))
            elif verdict == ADD and not any(live is True and ln < cl for cl, live in calls):
                probs.append("%s %s line %d: the add queues no start after it" % (k[0], k[1], ln))
    for rows in table.values():
        for verdict, why in rows:
            if verdict in (Q, ADD) and not callable(getattr(AgentEnd, why, None)):
                probs.append("the road test %s named in the table is not in this module" % why)
    return probs


class ReleaseCensus(unittest.TestCase):
    """EVERY PLACE AN AGENT LEAVES WHAT A SESSION KNOWS QUEUES ITS END, OR SAYS WHY NOT (PR 913 round 1, group A; tests-2).
    A session knows its agents through four structures: _subagents, the _bg_tasks rows (a Task agent's row is keyed by its
    agent's id), the Workflow rosters (_wf_agents, with _wf_slots) and the reg's bgTasks mirror, which a reattach seeds rows
    from. The census re-derives from the source, by AST over kernel/sdk_backend.py and kernel/kernel.py (release_census), the
    multiset of (file, enclosing function, structure, operation) sites over those structures and their markers
    (_seeded_tasks, _reported_tasks, _wf_ended), the mirror's writes, and the drops of a session object from `sessions`,
    and asserts it equals the table RELEASE_CENSUS in both directions. Each site is QUEUES, naming the executed road test of
    its road, or EXEMPT or DROP with its reason, or the one ADD (the start hook, which queues a start). A QUEUES site that
    removes a _subagents entry, a _bg_tasks row or a roster needs a queue call with live False after it in its function; a
    mirror write needs one anywhere in its function; an ADD needs one with live True after it; and each road test named
    must exist in this module. That the named test shows its road releasing the finished agent is the test's to show, not
    the census's (CENSUS_NOT_COVERAGE, which the failure message carries). kernel/kernel.py holds no session structure,
    and the census finds nothing there.
    Shown red before it was relied on (2026-09-25), and kept red by the test_the_census_reds_* tests below: a clear of
    _subagents in a new function of SdkSession with no queue call; a _bg_tasks clear planted in SdkBackend._on_session_gone,
    a function already listed, ahead of its queue call; the queue call removed from
    _reconcile_seeded_with_report, whose sites are recorded QUEUES; and a tree in which it finds nothing."""

    @classmethod
    def setUpClass(cls):
        cls.texts, cls.trees = {}, []
        for rel in CENSUS_FILES:
            text, tree = PC.source_and_tree(os.path.join(ROOT, rel), rel)
            cls.texts[rel] = text
            cls.trees.append((rel, tree))

    def _planted(self, old, new):
        text = self.texts[SB]
        self.assertEqual(text.count(old), 1, "precondition: the plant's anchor is in kernel/sdk_backend.py once")
        return [(SB, ast.parse(text.replace(old, new)))] + [t for t in self.trees if t[0] != SB]

    def test_every_site_is_recorded_and_every_queues_site_queues(self):
        probs = release_census_problems(self.trees)
        self.assertEqual(probs, [], "\n".join(probs) + "\n" + CENSUS_NOT_COVERAGE + " The table: " + "; ".join(
            "%s %s %s: %s" % (k[1], k[2], k[3], ", ".join("%s (%s)" % r for r in v)) for k, v in sorted(RELEASE_CENSUS.items())))

    def test_kernel_py_holds_no_session_structure(self):
        sites, _queues = release_census([t for t in self.trees if t[0] == "kernel/kernel.py"])
        self.assertEqual(sites, [])

    def test_the_census_reds_on_a_planted_site_in_a_new_function(self):
        probs = release_census_problems(self._planted(
            "    def _known_agents_locked(self) -> list:\n",
            "    def _forget_live_agents(self):\n"
            "        with self._sub_lock:\n"
            "            self._subagents.clear()\n\n"
            "    def _known_agents_locked(self) -> list:\n"))
        self.assertTrue(any("SdkSession._forget_live_agents: _subagents clear found 1 time" in p for p in probs), probs)

    def test_the_census_reds_on_a_planted_site_inside_a_listed_function(self):
        probs = release_census_problems(self._planted(
            "                gone_agents = sess._known_agents_locked()\n",
            "                gone_agents = sess._known_agents_locked()\n"
            "                sess._bg_tasks.clear()\n"))
        self.assertTrue(any("SdkBackend._on_session_gone: _bg_tasks clear found 1 time" in p for p in probs), probs)

    def test_the_census_reds_when_a_queues_site_loses_its_call(self):
        probs = release_census_problems(self._planted("            self._note_live_agents(retired_agents, False)\n", ""))
        self.assertTrue(any("_reconcile_seeded_with_report line" in p and "_bg_tasks pop is recorded QUEUES" in p
                            for p in probs), probs)
        self.assertTrue(any("_reconcile_seeded_with_report line" in p and "bgTasks mirror _update_reg is recorded QUEUES" in p
                            for p in probs), probs)

    def test_the_census_reds_when_it_finds_nothing(self):
        self.assertEqual(release_census_problems([(SB, ast.parse("x = 1\n"))]),
                         ["the census found nothing in kernel/sdk_backend.py: a file moved, or every structure was renamed"])


if __name__ == "__main__":
    unittest.main()
