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
released with nothing written. An end whose file lookup could not be made (a place the walk needed could not be read)
releases nothing and is remembered, and the lookup is made again at the first cycle at which one of the places the walk
could not read reads again or the walk no longer reaches it, each read once per cycle until then with no walk, one read
for all the ends of a session waiting on it (the reads: kernel._unread_place_reads' docstring); a cycle makes one such
lookup, oldest first, so when more ends are due the rest are looked up at the next cycles.

Synthetic data only: a notes-api project under a temp root, placeholder ids, a private sid, hostname TESTHOST.
"""
import ast
import asyncio
import contextlib
import errno
import io
import json
import os
import shutil
import stat
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
SIB_SID = "11111111-2222-3333-4444-a9e7e1d0c0e1"      # a sibling session directory in the project, holding the third agent's file
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
        getattr(km, "_AGENT_ENDED_FAULTED", {}).clear()
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

    # ---- a row whose type was never learned (PR 913 round 1, the coordinator's decision 6) ----
    # The reattached object's mirror lacked the agent's row, so the object mints it from the agent's first progress frame,
    # which carries no type, and a mirror written from that row carries it untyped. Such a row counts as a Task agent's on
    # every road that queues an end from a row (sdk_backend._bg_row_may_be_agent, whose docstring states the measured cost
    # of resolving its id at the drain); one pin per place the predicate is read.

    def _untyped_row(self, sess, aid=AID):
        before = list(self.be._agent_live_q)
        sess._on_task_event("task_progress", {"task_id": aid, "description": "check the notes-api routes"})
        self.assertEqual(sess._bg_tasks[aid]["type"], "", "precondition: a row of a type never learned")
        self.assertEqual(list(self.be._agent_live_q), before, "precondition: a progress frame ends nothing")

    def test_a_reattached_objects_untyped_agent_row_ends_at_its_task_end(self):
        """The row's own end frame queues the agent's end by (sid, agent id), and the drain resolves the agent's file as it
        resolves every end (_path_of, _subagent_file) and releases it at the next cycle. Before decision 6 was built the end
        queued nothing and the finished agent's records stayed whole."""
        again, size = self._reattached(AID, self.agent)
        self._untyped_row(again)
        again._on_task_event("task_notification", {"task_id": AID, "status": "completed"})
        self._released_at_the_next_cycle(AID, self.agent, size)

    def test_a_reattached_objects_untyped_agent_row_ends_when_its_cli_dies(self):
        again, size = self._reattached(AID, self.agent)
        self._untyped_row(again)
        self._no_wake()
        self._session_gone(again)                                        # neither ended nor detached: a crash
        self._released_at_the_next_cycle(AID, self.agent, size)

    def test_a_reattached_objects_seeded_untyped_agent_row_ends_when_the_report_lists_it_ended(self):
        again, size = self._reattached(AID, self.agent)
        self.assertEqual(again._seed_live_work_from_reg({"bgTasks": [      # a mirror written from an untyped row
            {"taskId": AID, "type": "", "desc": "check the notes-api routes", "since": 100}]}), 1, "precondition: seeded")
        again._reconcile_seeded_with_report([{"id": AID, "status": "completed", "type": "subagent"}])
        self.assertNotIn(AID, again._bg_tasks, "precondition: the report retired the row")
        self._released_at_the_next_cycle(AID, self.agent, size)

    def test_an_untyped_row_whose_id_names_no_agent_file_releases_and_counts_nothing(self):
        """The guard: an untyped row need not be an agent's. Its end is queued, and the drain resolves it to nothing and
        counts nothing: an id not in an agent id's shape with no walk (it never enters _subagent_file's memo), an
        agent-shaped id whose file exists nowhere after the walk. The running agent's records are untouched."""
        size = self._fold_while_running(AID, self.agent)
        km._begin_checkpoint_cycle()                                     # drains the start
        monitor, orphan = "m0000000000000001", "a4444444444444444"
        for tid in (monitor, orphan):
            self._untyped_row(self.s, tid)
            self.s._on_task_event("task_notification", {"task_id": tid, "status": "completed"})
        self.assertEqual(list(self.be._agent_live_q), [(SID, monitor, False), (SID, orphan, False)], "both ends queued")
        km._begin_checkpoint_cycle()
        self.assertNotIn((self.leaf, monitor), km._SUBAGENT_FILE_CACHE, "an id not in an agent id's shape is not resolved")
        self.assertIsNone(km._SUBAGENT_FILE_CACHE[(self.leaf, orphan)][1], "the agent-shaped id resolved to nothing")
        self.assertEqual(self._weight(self.agent), size, "the running agent keeps its records")
        self.assertEqual((self._stat("released"), self._stat("releaseDeferred"), self._stat("releaseLost")),
                         (NOTHING_RELEASED, 0, 0), "nothing released and nothing counted")
        self.assertEqual((km._AGENT_RELEASED, km._AGENT_ENDED_UNHELD), ({}, {}), "nothing recorded or remembered")

    # ---- the reg's mirror names the Task agents of a CLI that died with the old kernel ----

    def _dead_mirror_reg(self, agent_type="local_agent", **extra):
        reg = {"sid": SID, "alive": True, "name": "api", "cwd": self.root, "bgTasks": [
            {"taskId": AID, "type": agent_type, "desc": "check the notes-api routes", "since": 100},
            {"taskId": "b0000000000000001", "type": "local_bash", "desc": "run the notes-api tests", "since": 100}], **extra}
        sb.write_reg(self.state, SID, reg)
        return reg

    def test_a_dead_mirrors_agent_row_at_boot_is_released_after_a_read_holds_its_file(self):
        """The boot reconcile with no surviving CLI: the mirror's Task agent died with the old kernel's CLI. Nothing is held at
        boot, so the end finds nothing to release; the kernel remembers it, and a read that holds the file afterwards is
        released at the next cycle."""
        self._boot_over_a_dead_mirror("local_agent")

    def test_a_dead_mirrors_untyped_agent_row_at_boot_is_released_after_a_read_holds_its_file(self):
        self._boot_over_a_dead_mirror("")                                # a mirror written from an untyped row

    def _boot_over_a_dead_mirror(self, agent_type):
        reg = self._dead_mirror_reg(agent_type)
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
        self._wake_over_a_dead_mirror("local_agent")

    def test_a_threads_wake_over_a_dead_mirrors_untyped_agent_row_releases_its_held_file(self):
        self._wake_over_a_dead_mirror("")                                # a mirror written from an untyped row

    def _wake_over_a_dead_mirror(self, agent_type):
        size = self._fold_while_running(AID, self.agent)                 # the file is held
        km._begin_checkpoint_cycle()                                     # drains the start
        self._dead_mirror_reg(agent_type, threadOf="11111111-2222-3333-4444-000000000000")   # a dormant thread, its CLI dead

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
    # the file at the first cycle after a read holds it; a start of the agent that a cycle drains forgets the end (a start
    # queued after the drain of the cycle that releases the file, or dropped past the queue's bound, does not).

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
        remembered, and the popped path forgets it. A batch end's release adds its path to the popped paths too, pinned by
        test_a_batch_end_release_that_pops_a_path_forgets_the_other_ends_remembered_for_it. Red when the popped paths forget
        nothing: the second end stays remembered."""
        km._AGENT_ENDED_UNHELD[(SID, WF_AID)] = self.agent               # two ends remembered for one file
        km._AGENT_ENDED_UNHELD[(OTHER_SID, AID)] = self.agent
        em._read_jsonl_incremental(self.agent)                           # a whole read holds it
        size = os.path.getsize(self.agent)
        self.assertEqual(self._weight(self.agent), size, "precondition: the read holds the whole file")
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "released at the cycle after the read")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}}, "by one release")
        self.assertEqual(km._AGENT_ENDED_UNHELD, {}, "the popped path forgot both remembered ends")

    def test_a_batch_end_release_that_pops_a_path_forgets_the_other_ends_remembered_for_it(self):
        """The batch ends' road of the same rule: two ends in one batch whose (session, agent) pairs resolve to one file
        (_subagent_file stubbed, since no real road maps two agent ids to one transcript), a whole read, one cycle. The
        first end's release pops the file, and the second's then finds nothing held. Red when a taken batch end's release
        adds nothing to the popped paths: the second end stays remembered."""
        real = km._subagent_file
        km._subagent_file = lambda path, aid, faults=None, unread=None: (   # the release's lookup passes both lists
            Path(self.agent) if aid in (AID, WF_AID) else real(path, aid, faults, unread=unread))
        self.addCleanup(setattr, km, "_subagent_file", real)
        em._read_jsonl_incremental(self.agent)                           # a whole read holds it
        size = os.path.getsize(self.agent)
        self.assertEqual(self._weight(self.agent), size, "precondition: the read holds the whole file")
        self.be.note_agent_live(SID, AID, False)                         # two ends in one batch, both for that file
        self.be.note_agent_live(SID, WF_AID, False)
        km._begin_checkpoint_cycle()
        self.assertIsNone(self._weight(self.agent), "released at the batch's cycle")
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}}, "by one release")
        self.assertEqual(km._AGENT_RELEASED, {(SID, AID): [self.agent, True]}, "only the first end's release was taken")
        self.assertEqual(km._AGENT_ENDED_UNHELD, {}, "the popped path forgot the second end")

    # ---- an end whose file lookup could not be made (fork PR 882 round 5, the callers of _subagent_file's bare None) ----
    # The release resolves an ended agent's file with a faults list (kernel._release_end). A lookup that could not be made
    # (a place the walk needed could not be read, for a reason other than absence) is not "no file for the agent": nothing
    # is released, the end is remembered with the places the walk could not read (_AGENT_ENDED_FAULTED), and it is looked up
    # again at the first cycle at which one of them reads again by the read the walk makes of it, one per place per cycle
    # (the reads: _unread_place_reads' docstring; the cases below that say a place is read as the walk reads it), or at a
    # later one when more such ends are due (one lookup a cycle), and no walk until then. The code before the change passed
    # no faults list: with no resolution standing it read the bare None as no file and gave the end up, counted nowhere and
    # not looked up again after the fault cleared; with one standing it released under the fault, where em.release_entry's
    # os.path.exists read the fault as the file gone and popped the records without their checkpoint document. Each fault is
    # a real EACCES (skipped as root, whom permission bits do not bind), restored inside the case, since a cleanup runs
    # after tearDown removed the tree.

    @contextlib.contextmanager
    def _unreadable(self, *dirs, mode=0o000):
        """Each of `dirs` at `mode` (000 unless given) for the block, its mode restored at the block's end whatever the
        block raised."""
        if os.geteuid() == 0:
            self.skipTest("permission bits do not bind root: no EACCES to drive")
        modes = [(d, stat.S_IMODE(os.stat(d).st_mode)) for d in dirs]
        try:
            for d in dirs:
                os.chmod(d, mode)
            yield
        finally:
            for d, m in reversed(modes):
                os.chmod(d, m)

    def _ended_with_its_file_resolved(self, aid, path, standing):
        """The agent runs and its file is folded (_fold_while_running), a cycle drains its start, and it ends: its end is
        queued for the next cycle. With `standing` False the lookup's memo entry is dropped (as the memo's 1024-key clear
        drops it), so no resolution stands for the end's lookup; with it True the resolution the folds made stands."""
        size = self._fold_while_running(aid, path)
        km._begin_checkpoint_cycle()                                     # drains the start
        if standing:
            self.assertEqual(str(km._subagent_file(self.leaf, aid)), path, "precondition: a resolution stands")
        else:
            km._SUBAGENT_FILE_CACHE.pop((self.leaf, aid), None)
        self._stop(aid)
        return size

    def _lookup_faults(self, aid, standing):
        faults = []
        got = km._subagent_file(self.leaf, aid, faults)
        self.assertEqual((got is None, faults), (not standing, ["PermissionError"]),
                         "precondition: the lookup could not be made (%r, %r)" % (got, faults))

    def _released_with_its_document(self, path, size):
        w = self._weight(path)
        self.assertTrue(w is None or w == 0, "the end's release happens once the lookup is made (weight %r of %d)" % (w, size))
        self.assertEqual(self._stat("released"), {"agentEnded": {"count": 1, "bytes": size}}, "one release, counted")
        self.assertTrue(em._ckpt_file(path).exists(), "with its checkpoint document")
        self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {}, "and the faulted end is forgotten")

    def _held_unwritten_nothing(self, path, size, when):
        self.assertEqual((self._weight(path), self._stat("released"), self._stat("releaseLost"), em._ckpt_file(path).exists()),
                         (size, NOTHING_RELEASED, 0, False),
                         "%s: not yet, so the records stay, nothing is released or given up, and nothing is popped "
                         "unwritten" % when)

    @contextlib.contextmanager
    def _recording(self):
        """This thread's os.lstat, os.stat and os.scandir calls on a path under the project directory, by class, and the
        agent-file walks (_subagent_file_walk calls), for the block."""
        me, proj = threading.get_ident(), os.path.dirname(self.leaf)
        got = {"lstat": [], "stat": [], "scandir": [], "walks": 0}
        real = {n: getattr(os, n) for n in ("lstat", "stat", "scandir")}

        def wrap(n):
            def call(p=".", *a, **k):
                if threading.get_ident() == me and isinstance(p, (str, os.PathLike)) and (
                        str(p) == proj or str(p).startswith(proj + os.sep)):
                    got[n].append(str(p))
                return real[n](p, *a, **k)
            return call
        real_walk = km._subagent_file_walk

        def walk(*a, **k):
            got["walks"] += 1
            return real_walk(*a, **k)
        try:
            for n in real:
                setattr(os, n, wrap(n))
            km._subagent_file_walk = walk
            yield got
        finally:
            for n, f in real.items():
                setattr(os, n, f)
            km._subagent_file_walk = real_walk

    def _cycle_in_the_pushers_slots(self):
        """One _begin_checkpoint_cycle inside the three tree slots, as _pusher_cycle opens them around its jobs stage."""
        slots = ("subagent_trees", "subagent_stamps", "subagent_launches")
        for s in slots:
            setattr(km._live_scope, s, {})
        try:
            km._begin_checkpoint_cycle()
        finally:
            for s in slots:
                setattr(km._live_scope, s, None)

    def test_an_end_whose_file_lookup_faults_is_released_at_the_first_cycle_after_the_fault_clears(self):
        """R1: no resolution standing, the session directory at mode 000. In the end's cycle under the fault nothing is
        released or counted; at the first cycle after the fault clears, with no new event, the release happens with its
        checkpoint document. Red under a mutant that reads the fault as no file again: the end's cycle gives the end up,
        and after the clear the records stay whole (weight equal to the file's size). The code before this change cannot
        run the case (its _subagent_file takes no `faults` argument, so the precondition's lookup raises TypeError), which
        is no red for the reason."""
        size = self._ended_with_its_file_resolved(AID, self.agent, standing=False)
        with self._unreadable(os.path.dirname(os.path.dirname(self.agent))):
            self._lookup_faults(AID, standing=False)
            km._begin_checkpoint_cycle()                                 # the end's cycle, under the fault
            self._held_unwritten_nothing(self.agent, size, "in the end's cycle under the fault")
        km._begin_checkpoint_cycle()                                     # the fault cleared; no new event
        self._released_with_its_document(self.agent, size)

    def test_a_start_after_a_faulted_end_cancels_its_retry(self):
        """R2: the agent is live again before its faulted end is looked up again. The start's cycle forgets the faulted end,
        and the running agent keeps its records then and at the cycle after. Red under a mutant that drops the drained
        start's forgetting of the faulted end: the table still holds the end after the start's cycle, and at the next cycle
        its lookup would release the running agent's records. Before the change there was no faulted end to forget, and
        the premise fails."""
        size = self._ended_with_its_file_resolved(AID, self.agent, standing=False)
        with self._unreadable(os.path.dirname(os.path.dirname(self.agent))):
            km._begin_checkpoint_cycle()
            self.assertIn((SID, AID), getattr(km, "_AGENT_ENDED_FAULTED", {}), "precondition: the end is remembered as faulted")
        self._start(AID)                                                 # live again; the fault has cleared
        km._begin_checkpoint_cycle()                                     # the start's cycle
        self.assertEqual(km._AGENT_ENDED_FAULTED, {}, "the drained start forgot the faulted end")
        self.assertEqual(self._weight(self.agent), size, "a live agent's records are not released")
        km._begin_checkpoint_cycle()
        self.assertEqual((self._weight(self.agent), self._stat("released")), (size, NOTHING_RELEASED), "nor at the cycle after")

    def test_an_end_whose_standing_resolution_lies_under_the_fault_is_deferred_and_released_with_its_document_after_it(self):
        """R3: a resolution stands, and the lookup answers it with the fault, since it lies under the place the walk could
        not read. The end is not released under the fault, so nothing pops its records unwritten, and it is released with
        its checkpoint document at the first cycle after the fault clears. Red under a mutant that defers only a lookup
        with no resolution, and under one that reads the fault as no file again: the release under the fault takes the
        standing path, em.release_entry's os.path.exists answers False under the EACCES, and the records are popped with
        no document (the next fold reads the file whole). The code before this change cannot run the case (its
        _subagent_file takes no `faults` argument, so the precondition's lookup raises TypeError), which is no red for the
        reason."""
        size = self._ended_with_its_file_resolved(AID, self.agent, standing=True)
        with self._unreadable(os.path.dirname(os.path.dirname(self.agent))):
            self._lookup_faults(AID, standing=True)
            km._begin_checkpoint_cycle()
            self._held_unwritten_nothing(self.agent, size, "under the fault")
        km._begin_checkpoint_cycle()
        self._released_with_its_document(self.agent, size)

    def test_a_faulted_end_costs_one_lstat_of_its_unread_place_per_cycle_and_is_looked_up_only_once_that_place_reads(self):
        """The retry is keyed on the event that the place reads again, not on the cycle. R1's world: the session directory
        at mode 000 leaves one place the walk could not read, the own subagents directory (its lstat, and the tree's read
        of it, each excluded it). Inside the pusher cycle's three slots, each cycle under the fault reads that place by one
        os.lstat and makes no os.stat, no listing and no walk; the first cycle after the clear walks once and releases.
        Red under a mutant that looks every faulted end up at every cycle (a walk per faulted cycle). Before the change no
        end was remembered, and the premise fails."""
        own = os.path.dirname(self.agent)
        size = self._ended_with_its_file_resolved(AID, self.agent, standing=False)
        with self._unreadable(os.path.dirname(own)):
            self._cycle_in_the_pushers_slots()                           # the end's cycle: the lookup walks and faults
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, AID): ((own, "tree"),)},
                             "precondition: remembered with its one place, a place in a subagents tree")
            for n in (1, 2):
                with self._recording() as got:
                    self._cycle_in_the_pushers_slots()
                self.assertEqual(got, {"lstat": [own], "stat": [], "scandir": [], "walks": 0},
                                 "faulted cycle %d: one lstat of the place and no walk" % n)
            self._held_unwritten_nothing(self.agent, size, "over the two faulted cycles")
        with self._recording() as got:
            self._cycle_in_the_pushers_slots()                           # the fault cleared: the place reads
        self.assertEqual(got["walks"], 1, "looked up again, one walk, once the place reads")
        self._released_with_its_document(self.agent, size)

    def test_the_ends_waiting_on_one_place_read_it_once_per_cycle_however_many_they_are(self):
        """The waiting reads are memoized for the cycle on the place, its kind and the session (_release_ended_agents),
        so the wait costs one read per place per cycle, not one per end. R1's world: the own end remembered with its one
        place, the own subagents directory under the session directory at mode 000, and 49 more ends of the session
        waiting on that place. Each cycle under the fault reads it by one os.lstat and makes no walk. Red under a read
        per end: 50 lstats a cycle."""
        own = os.path.dirname(self.agent)
        size = self._ended_with_its_file_resolved(AID, self.agent, standing=False)
        with self._unreadable(os.path.dirname(own)):
            km._begin_checkpoint_cycle()                                 # the end's cycle: the lookup walks and faults
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, AID): ((own, "tree"),)},
                             "precondition: remembered with its one place")
            for i in range(1, 50):
                km._remember_faulted_end((SID, "a%016x" % i), ((own, "tree"),))
            for n in (1, 2):
                with self._recording() as got:
                    km._begin_checkpoint_cycle()
                self.assertEqual(got, {"lstat": [own], "stat": [], "scandir": [], "walks": 0},
                                 "faulted cycle %d: one lstat of the place for the 50 ends, and no walk" % n)
            self.assertEqual(len(km._AGENT_ENDED_FAULTED), 50, "every end still waits")
            self._held_unwritten_nothing(self.agent, size, "under the fault")

    def test_an_end_of_another_session_waiting_on_the_same_place_is_read_for_its_own_session(self):
        """The memo's key holds the session, since a place whose read fails is lasting or not by where the session's
        transcript lies (_unread_place_reads). The own end, remembered with the own subagents directory under the
        session directory at mode 000, is lasting; an end of a second session waiting on the same place, whose
        transcript lies in another project directory, is not, since its walk lists that directory. The cycle reads the
        place once for each session and looks the second end up, one walk, which finds no file and forgets it. Red under
        a memo keyed on the place and its kind alone: the second end is served the first's answer and waits while the
        place stays unreadable."""
        own = os.path.dirname(self.agent)
        other = os.path.join(self.root, "projects", "-home-TESTHOST-notes-web", OTHER_SID + ".jsonl")
        os.makedirs(os.path.dirname(other))
        _append(other, [{"type": "user", "uuid": "11111111-2222-3333-4444-000000000005", "sessionId": OTHER_SID,
                         "timestamp": "2026-09-24T10:30:00.000Z",
                         "message": {"role": "user", "content": "Review the notes-web client."}}])
        km._path_of = lambda sid, now=None: {SID: self.leaf, OTHER_SID: other}.get(sid)   # restored by tearDown
        size = self._ended_with_its_file_resolved(AID, self.agent, standing=False)
        with self._unreadable(os.path.dirname(own)):
            km._begin_checkpoint_cycle()                                 # the end's cycle: the lookup walks and faults
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, AID): ((own, "tree"),)},
                             "precondition: remembered with its one place")
            km._remember_faulted_end((OTHER_SID, AID3), ((own, "tree"),))
            with self._recording() as got:
                km._begin_checkpoint_cycle()
            self.assertEqual((got["lstat"], got["walks"], km._AGENT_ENDED_FAULTED),
                             ([own, own], 1, {(SID, AID): ((own, "tree"),)}),
                             "the place read once per session, and the second session's end looked up and forgotten")
            self._held_unwritten_nothing(self.agent, size, "under the fault")

    def test_a_path_waited_on_as_an_entry_and_as_a_tree_place_is_read_once_for_each_kind(self):
        """The memo's key holds the kind of read, since one path read as a project-directory entry (its os.stat, through a
        link) and as a place in a subagents tree (its os.lstat and listing) can answer differently. No lookup records a
        path under two kinds, so the table is injected: two ends of the session wait on a sibling session directory with
        no tree, the older as an entry and the newer as a tree place, and the directory's os.stat fails (an EIO by mock)
        while its lstat and listing answer. The older end's read fails, and the entry lies in the project directory the
        walk lists, so that end waits; the newer end's read answers, so it is looked up, one walk (which faults on the
        same os.stat and remembers the end again, with the place as the entry it is). The older end comes first in the
        table so that the cap (one lookup a cycle) does not end the cycle before the newer end is read. Red under a memo
        keyed on the place and the session alone: the newer end is served the older end's answer and waits, no walk."""
        p = os.path.join(os.path.dirname(self.leaf), SIB_SID)
        os.makedirs(p)
        km._remember_faulted_end((SID, AID), ((p, "entry"),))
        km._remember_faulted_end((SID, AID3), ((p, "tree"),))
        real = os.stat

        def st(q, *a, **k):
            if isinstance(q, (str, os.PathLike)) and os.fspath(q) == p:
                raise OSError(errno.EIO, "the lookup answered EIO", p)
            return real(q, *a, **k)
        os.stat = st
        try:
            with self._recording() as got:
                km._begin_checkpoint_cycle()
        finally:
            os.stat = real
        self.assertEqual((got["walks"], km._AGENT_ENDED_FAULTED),
                         (1, {(SID, AID): ((p, "entry"),), (SID, AID3): ((p, "entry"),)}),
                         "the entry-kind end waits; the tree-kind end is looked up, one walk, and remembered again")

    def test_the_ends_whose_place_reads_again_are_looked_up_one_per_cycle_oldest_first(self):
        """The count cap on the faulted ends looked up per cycle (_AGENT_FAULTED_LOOKUPS_MAX, one): the own agent and the
        workflow agent end in one batch under R1's fault, each remembered with the own subagents directory, the own
        agent's first. At the first cycle after the fault clears the oldest end alone is looked up and released with its
        document, the other left in the table; the next cycle looks the other up and releases it. Red under a mutant with
        no cap: the first cycle walks twice."""
        own = os.path.dirname(self.agent)
        size = self._fold_while_running(AID, self.agent)
        wf_size = self._fold_while_running(WF_AID, self.wf_agent)
        km._begin_checkpoint_cycle()                                     # drains both starts
        for aid in (AID, WF_AID):
            km._SUBAGENT_FILE_CACHE.pop((self.leaf, aid), None)          # no resolution stands for either lookup
        self._stop(AID)
        self._stop(WF_AID)
        with self._unreadable(os.path.dirname(own)):
            km._begin_checkpoint_cycle()                                 # the ends' cycle: each lookup walks and faults
            self.assertEqual(list(getattr(km, "_AGENT_ENDED_FAULTED", {}).items()),
                             [((SID, AID), ((own, "tree"),)), ((SID, WF_AID), ((own, "tree"),))],
                             "precondition: both remembered with the own subagents directory, the own agent's first")
        with self._recording() as got:
            km._begin_checkpoint_cycle()                                 # the fault cleared: the oldest end alone
        self.assertEqual((got["walks"], list(km._AGENT_ENDED_FAULTED)), (1, [(SID, WF_AID)]),
                         "one lookup, the oldest end's; the other waits for the next cycle")
        self.assertEqual((self._weight(self.agent) in (None, 0), em._ckpt_file(self.agent).exists(),
                          self._weight(self.wf_agent)), (True, True, wf_size),
                         "the own agent released with its document, the workflow agent's records still held")
        with self._recording() as got:
            km._begin_checkpoint_cycle()
        self.assertEqual((got["walks"], km._AGENT_ENDED_FAULTED), (1, {}), "the next cycle looks the other up")
        self.assertEqual((self._weight(self.wf_agent) in (None, 0), em._ckpt_file(self.wf_agent).exists(),
                          self._stat("released")), (True, True, {"agentEnded": {"count": 2, "bytes": size + wf_size}}),
                         "and releases it with its document")

    def test_the_ends_due_take_turns_when_the_oldest_ones_lookup_faults_again_at_each_cycle(self):
        """The ends due take turns under the cap: a lookup that faults again remembers its end as the newest
        (_remember_faulted_end), so an end whose lookup faults at every cycle does not hold the cycle's one lookup. The
        older end is the workflow agent's, whose lookup faults at every cycle on residual 2's root form (the strict
        os.path.realpath of the own subagents directory fails, an EIO by mock, while its lstat and listing answer), as
        in the root-form witness
        test_residual_a_resolution_of_a_trees_root_that_fails_where_its_lstat_answers_has_its_end_looked_up_at_each_cycle.
        The younger is the third agent's, whose file lies in a sibling session's tree; both end in one batch while that
        tree's root fails its resolution too (by the same mock), so both lookups fault and both ends are remembered, the
        workflow agent's first. Then the sibling's root resolves again, and both ends' places read at each cycle, so
        both are due: the first cycle looks the older up, which faults again and goes behind the younger; the second
        looks the younger up and releases its records with their document; the third looks the older up again. Red
        under a mutant that keeps a re-remembered end in its old place: the older end is looked up at every cycle and
        the younger never is."""
        own = os.path.dirname(self.agent)
        sib = os.path.join(os.path.dirname(self.leaf), SIB_SID, "subagents")
        path3 = os.path.join(sib, "agent-%s.jsonl" % AID3)
        os.makedirs(sib)
        _append(path3, _agent_lines(AID3, 0, 40))
        wf_size = self._fold_while_running(WF_AID, self.wf_agent)
        size3 = self._fold_while_running(AID3, path3)
        km._begin_checkpoint_cycle()                                     # drains both starts
        for aid in (WF_AID, AID3):
            km._SUBAGENT_FILE_CACHE.pop((self.leaf, aid), None)          # no resolution stands for either lookup
        failing = {own, sib}
        real = os.path.realpath

        def resolve(p, *a, **k):
            if k.get("strict") and os.fspath(p) in failing:
                raise OSError(errno.EIO, "the resolution failed", os.fspath(p))
            return real(p, *a, **k)
        os.path.realpath = resolve
        try:
            self._stop(WF_AID)
            self._stop(AID3)
            km._begin_checkpoint_cycle()                                 # the ends' cycle: each lookup faults on both roots
            both = ((own, "tree"), (sib, "tree"))
            self.assertEqual(list(km._AGENT_ENDED_FAULTED.items()), [((SID, WF_AID), both), ((SID, AID3), both)],
                             "precondition: both remembered with the two roots, the workflow agent's end the older")
            failing.discard(sib)                                         # the sibling's root resolves again; the own root's not
            rows, self.maxDiff = [], None                                # the whole rows in a red's message
            for n in (1, 2, 3):
                with self._recording() as got:
                    km._begin_checkpoint_cycle()
                rows.append((n, got["walks"], list(km._AGENT_ENDED_FAULTED), self._weight(path3) in (None, 0)))
            self.assertEqual(rows, [(1, 1, [(SID, AID3), (SID, WF_AID)], False),
                                    (2, 1, [(SID, WF_AID)], True),
                                    (3, 1, [(SID, WF_AID)], True)],
                             "(cycle, walks, the faulted ends oldest first, the third agent's records released): the "
                             "older end's lookup faults again and it goes behind the younger, looked up and released at "
                             "the second cycle")
            self.assertEqual((em._ckpt_file(path3).exists(), self._weight(self.wf_agent), self._stat("releaseLost")),
                             (True, wf_size, 0), "the younger end's records released with their document, the older "
                             "end's still held while its lookup faults, nothing given up")
        finally:
            os.path.realpath = real
        km._begin_checkpoint_cycle()                                     # the own root resolves again
        self.assertEqual((self._weight(self.wf_agent) in (None, 0), em._ckpt_file(self.wf_agent).exists(),
                          self._stat("released"), km._AGENT_ENDED_FAULTED),
                         (True, True, {"agentEnded": {"count": 2, "bytes": size3 + wf_size}}, {}),
                         "the older end looked up and released with its document at the first cycle after its fault")

    def test_an_end_that_waited_keeps_its_place_and_is_looked_up_first_once_its_place_reads(self):
        """Oldest first holds for an end that waited too: a cycle in which an end waits leaves it where it is in the table,
        so once its place reads it is looked up before the younger ends due. The own agent's end, the oldest, waits on a
        place whose read fails (by a wrapper of _unread_place_reads, since the order is under test and not the read); the
        workflow agent's and the third agent's ends, younger, are remembered with the own subagents directory, which
        reads, so both are due. The first cycle looks the workflow agent's end up; then the oldest end's place reads, and
        the second cycle looks it up before the third agent's. Red under a mutant that moves a waiting end behind the
        others at each cycle it waits: the first cycle leaves the table as [the third agent's, the own agent's], and the
        second looks the third agent's end up while the oldest waits another cycle."""
        own = os.path.dirname(self.agent)
        _append(os.path.join(own, "agent-%s.jsonl" % AID3), _agent_lines(AID3, 0, 40))
        blocked = os.path.join(os.path.dirname(self.leaf), "a-place-that-fails")
        km._remember_faulted_end((SID, AID), ((blocked, "tree"),))      # the oldest, waiting
        km._remember_faulted_end((SID, WF_AID), ((own, "tree"),))       # two younger ends, due
        km._remember_faulted_end((SID, AID3), ((own, "tree"),))
        real, fails = km._unread_place_reads, [True]
        km._unread_place_reads = lambda p, kind, sid: (not fails[0]) if p == blocked else real(p, kind, sid)
        try:
            rows, self.maxDiff = [], None
            for n in (1, 2, 3):
                with self._recording() as got:
                    km._begin_checkpoint_cycle()
                rows.append((n, got["walks"], [aid for _sid, aid in km._AGENT_ENDED_FAULTED]))
                fails[0] = False                                         # the oldest end's place reads after the first
        finally:
            km._unread_place_reads = real
        self.assertEqual(rows, [(1, 1, [AID, AID3]), (2, 1, [AID3]), (3, 1, [])],
                         "(cycle, walks, the faulted ends left, oldest first): the waiting end keeps its place and is "
                         "looked up at the first cycle after its place reads, ahead of the younger end due")

    def test_a_directory_whose_listing_is_refused_is_read_by_its_listing_so_its_end_is_not_walked_while_it_stays_refused(self):
        """The own subagents directory at mode 000: its lstat succeeds (its parent can be searched) while its listing and
        the lstat of the file in it are refused. The walk excludes the directory for its listing and the file for its
        lstat, and each cycle under the fault reads the directory by its lstat and its listing's first entry and the file
        by its lstat, then, that read failing, the tree's root on the walk's way to the file by one more lstat (the
        directory itself, a real one, so the walk reaches the file), with no walk; the first cycle after the clear walks
        once and releases. Red under a mutant that reads a directory by its lstat alone: the directory reads at every
        faulted cycle, and the end is walked at each."""
        own = os.path.dirname(self.agent)
        size = self._ended_with_its_file_resolved(AID, self.agent, standing=False)
        with self._unreadable(own):
            os.lstat(own)                                                # the premise: the place's own lstat reads
            with self.assertRaises(PermissionError, msg="precondition: its listing is refused"):
                os.scandir(own).close()
            km._begin_checkpoint_cycle()
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, AID): ((own, "tree"), (self.agent, "tree"))},
                             "precondition: remembered with the directory and the file in it")
            for n in (1, 2):
                with self._recording() as got:
                    km._begin_checkpoint_cycle()
                self.assertEqual(got, {"lstat": [own, self.agent, own], "stat": [], "scandir": [own], "walks": 0},
                                 "faulted cycle %d: each place read once, the root on the way to the file, and no walk" % n)
            self._held_unwritten_nothing(self.agent, size, "under the fault")
        with self._recording() as got:
            km._begin_checkpoint_cycle()
        self.assertEqual(got["walks"], 1, "looked up again once the listing reads")
        self._released_with_its_document(self.agent, size)

    def test_a_project_directory_entry_is_read_through_its_link_so_its_end_is_not_walked_while_the_target_is_unreadable(self):
        """A sibling session directory reached through a link, the agent's file under its tree, the link's target in a
        directory at mode 000: the walk reads the entry by os.stat, which follows the link and fails, and excludes the
        entry. Each cycle under the fault reads the entry by one os.stat, as the walk does, and no lstat and no walk; the
        first cycle after the clear walks once and releases. Red under a mutant that reads the entry by its lstat: the link
        itself reads at every faulted cycle, and the end is walked at each."""
        proj = os.path.dirname(self.leaf)
        away = os.path.join(self.root, "elsewhere")
        target = os.path.join(away, SIB_SID)
        os.makedirs(os.path.join(target, "subagents"))
        link = os.path.join(proj, SIB_SID)
        os.symlink(target, link)
        path = os.path.join(link, "subagents", "agent-%s.jsonl" % AID3)
        _append(path, _agent_lines(AID3, 0, 40))
        size = self._ended_with_its_file_resolved(AID3, path, standing=False)
        with self._unreadable(away):
            km._begin_checkpoint_cycle()
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, AID3): ((link, "entry"),)},
                             "precondition: remembered with the entry, a project-directory entry")
            for n in (1, 2):
                with self._recording() as got:
                    km._begin_checkpoint_cycle()
                self.assertEqual(got, {"lstat": [], "stat": [link], "scandir": [], "walks": 0},
                                 "faulted cycle %d: the entry read once through its link and no walk" % n)
            self._held_unwritten_nothing(path, size, "under the fault")
        with self._recording() as got:
            km._begin_checkpoint_cycle()
        self.assertEqual(got["walks"], 1, "looked up again once the entry reads")
        self._released_with_its_document(path, size)

    def test_a_project_directory_entry_replaced_by_a_looping_link_answers_its_own_read_so_its_end_is_looked_up(self):
        """A sibling session directory reached through a link whose target lies in a directory at mode 000: the walk's
        os.stat of the entry fails and the end is remembered with the entry. The link is then replaced by a link to itself:
        the entry's os.stat reads ELOOP, which the walk takes for not a directory and the place read answers the same
        way, so the next cycle looks the end up, and the walk, finding no file, releases nothing. Red under a mutant that
        drops the entry's _REG_MISSING_ERRNOS answer: the read falls through to the transcript, whose project directory
        holds the entry, so the place stays lasting and no walk is made."""
        proj = os.path.dirname(self.leaf)
        away = os.path.join(self.root, "elsewhere")
        target = os.path.join(away, SIB_SID)
        os.makedirs(os.path.join(target, "subagents"))
        link = os.path.join(proj, SIB_SID)
        os.symlink(target, link)
        path = os.path.join(link, "subagents", "agent-%s.jsonl" % AID3)
        _append(path, _agent_lines(AID3, 0, 40))
        size = self._ended_with_its_file_resolved(AID3, path, standing=False)
        with self._unreadable(away):
            km._begin_checkpoint_cycle()
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, AID3): ((link, "entry"),)},
                             "precondition: remembered with the entry")
            os.unlink(link)
            os.symlink(link, link)
            with self.assertRaises(OSError, msg="precondition: the entry's os.stat fails") as cm:
                os.stat(link)
            self.assertEqual(cm.exception.errno, errno.ELOOP, "precondition: the entry's os.stat reads ELOOP")
            faults, excluded = [], []
            self.assertEqual((km._subagent_file_walk(self.leaf, AID3, [], faults, [], excluded), faults, excluded),
                             (None, [], []), "precondition: the walk takes the looping entry for not a directory")
            with self._recording() as got:
                km._begin_checkpoint_cycle()
            self.assertEqual((got["walks"], getattr(km, "_AGENT_ENDED_FAULTED", {})), (1, {}),
                             "the next cycle looks the end up, one walk, and forgets it")
            self.assertEqual((self._weight(path), self._stat("released"), self._stat("releaseLost")),
                             (size, NOTHING_RELEASED, 0), "nothing released or given up: the walk found no file")

    def _sibling_agent(self, proj):
        """The third agent's file under a sibling session directory's tree in `proj`, where only the walk's project
        listing reaches it: its path."""
        path = os.path.join(proj, SIB_SID, "subagents", "agent-%s.jsonl" % AID3)
        os.makedirs(os.path.dirname(path))
        _append(path, _agent_lines(AID3, 0, 40))
        return path

    def _project_listing_refused(self, proj, refused):
        """The third agent, its file under a sibling's tree, ends while `refused` (the project directory, or the directory
        a link in its place points at) is at mode 300: searchable, so the own tree and every entry's stat read, and not
        listable, so the walk excludes the project directory for its listing. Each cycle under the fault reads the project
        directory by one os.stat and its listing, with no lstat and no walk; the first cycle after the clear walks once
        and releases."""
        path = self._sibling_agent(proj)                                 # the path the walk resolves, through a link if one
        size = self._ended_with_its_file_resolved(AID3, path, standing=False)
        with self._unreadable(refused, mode=0o300):
            with self.assertRaises(PermissionError, msg="precondition: the project directory's listing is refused"):
                os.listdir(proj)
            km._begin_checkpoint_cycle()
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, AID3): ((proj, "project"),)},
                             "precondition: remembered with the project directory")
            for n in (1, 2):
                with self._recording() as got:
                    km._begin_checkpoint_cycle()
                self.assertEqual(got, {"lstat": [], "stat": [proj], "scandir": [proj], "walks": 0},
                                 "faulted cycle %d: the project directory read once, stat and listing, and no walk" % n)
            self._held_unwritten_nothing(path, size, "under the fault")
        with self._recording() as got:
            km._begin_checkpoint_cycle()
        self.assertEqual(got["walks"], 1, "looked up again once the listing reads")
        self._released_with_its_document(path, size)

    def test_a_project_directory_whose_listing_is_refused_is_read_by_its_listing_so_its_end_is_not_walked_meanwhile(self):
        """The project directory at mode 300 (_project_listing_refused). Red under a mutant that reads the project
        directory by its stat alone: it reads at every faulted cycle, and the end is walked at each."""
        self._project_listing_refused(os.path.dirname(self.leaf), os.path.dirname(self.leaf))

    def test_a_project_directory_reached_through_a_link_is_read_through_it_so_its_end_is_not_walked_meanwhile(self):
        """The same with the project directory a link to a directory at mode 300: the walk stats and lists it through the
        link. Red under a mutant that reads the project directory as a place in a tree (its lstat, which answers the link
        itself, and a listing only for a directory there): the link reads at every faulted cycle, and the end is walked
        at each."""
        real = os.path.join(self.root, "projects-real", "-home-TESTHOST-notes-api-linked")
        link = os.path.join(self.root, "projects", "-home-TESTHOST-notes-api-linked")
        os.makedirs(os.path.join(real, SID, "subagents"))
        os.symlink(real, link)
        self.leaf = os.path.join(link, SID + ".jsonl")                 # the session's transcript, reached through the link
        _append(self.leaf, [{"type": "user", "uuid": "11111111-2222-3333-4444-000000000002", "sessionId": SID,
                             "timestamp": "2026-09-24T09:59:00.000Z",
                             "message": {"role": "user", "content": "Run the notes-api tests in the background."}}])
        km._path_of = lambda sid, now=None: self.leaf if sid == SID else None   # restored by tearDown
        self._project_listing_refused(link, real)

    def test_a_faulted_end_is_looked_up_again_when_any_of_its_places_reads_while_another_still_cannot(self):
        """Two places the walk could not read: the own session directory at mode 000 (the own subagents directory
        excluded) and a sibling session directory at mode 000 whose tree holds the agent's file (its subagents root
        excluded). When the sibling alone is restored the end is looked up again at the next cycle and released, the own
        tree still unreadable: every place the walk could not read is read at each cycle, the first to read ending the
        wait. Red under a mutant that reads the first place alone: the release waits until the own tree reads."""
        proj = os.path.dirname(self.leaf)
        sess, sib = os.path.dirname(os.path.dirname(self.agent)), os.path.join(proj, SIB_SID)
        path = os.path.join(sib, "subagents", "agent-%s.jsonl" % AID3)
        os.makedirs(os.path.dirname(path))
        _append(path, _agent_lines(AID3, 0, 40))
        size = self._ended_with_its_file_resolved(AID3, path, standing=False)
        with self._unreadable(sess):
            with self._unreadable(sib):
                km._begin_checkpoint_cycle()
                self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}),
                                 {(SID, AID3): ((os.path.join(sess, "subagents"), "tree"),
                                                (os.path.join(sib, "subagents"), "tree"))},
                                 "precondition: remembered with both places, the own tree's first")
                km._begin_checkpoint_cycle()
                self._held_unwritten_nothing(path, size, "while both places are unreadable")
            with self.assertRaises(PermissionError, msg="precondition: the own tree still cannot be read"):
                os.lstat(os.path.join(sess, "subagents"))
            km._begin_checkpoint_cycle()                                 # the sibling reads; the own tree does not
            self._released_with_its_document(path, size)

    def test_a_faulted_end_whose_lookup_faults_again_waits_on_the_places_of_that_lookup(self):
        """A faulted end looked up again whose lookup faults again is remembered with the places that lookup could not
        read, not the earlier set (_remember_faulted_end). The own agent ends with the own session directory and an empty
        sibling session directory both at mode 000, so it is remembered with both subagents places, the own first. The
        sibling is restored: its subagents place reads (nothing there), so the next cycle looks the end up, and that
        lookup faults again on the own tree alone and remembers the end with it. The two cycles after that make no walk,
        and the first cycle after the own tree reads releases the records with their document. Red under a mutant that
        keeps the earlier set: the sibling's place still reads at every cycle, so every cycle walks and faults again."""
        proj = os.path.dirname(self.leaf)
        sess, own = os.path.dirname(os.path.dirname(self.agent)), os.path.dirname(self.agent)
        sib = os.path.join(proj, SIB_SID)
        os.makedirs(sib)                                                 # a sibling session directory with no tree
        size = self._ended_with_its_file_resolved(AID, self.agent, standing=False)
        with self._unreadable(sess):
            with self._unreadable(sib):
                km._begin_checkpoint_cycle()                             # the end's cycle: the lookup walks and faults
                self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}),
                                 {(SID, AID): ((own, "tree"), (os.path.join(sib, "subagents"), "tree"))},
                                 "precondition: remembered with both places, the own tree's first")
            walks = []
            for n in range(3):
                with self._recording() as got:
                    km._begin_checkpoint_cycle()
                walks.append(got["walks"])
                if n == 0:
                    self.assertEqual(km._AGENT_ENDED_FAULTED, {(SID, AID): ((own, "tree"),)},
                                     "the lookup faulted again and remembered the end with its own place alone")
            self.assertEqual(walks, [1, 0, 0], "looked up once, when the sibling's place read; then no walk")
            self._held_unwritten_nothing(self.agent, size, "while the own tree cannot be read")
        km._begin_checkpoint_cycle()
        self._released_with_its_document(self.agent, size)

    # A place whose read fails is lasting only where the walk the lookup makes now reaches it (fork PR 882's focused
    # re-check, condition 1: every error the place read takes as lasting is one the walk faults on). The walk lists the
    # project directory of the session's transcript and no other, so a project directory, an entry or a place in a tree
    # outside that one is not reached. Inside it, the walk enters a sibling session directory only when its os.stat reads
    # a directory (_REG_MISSING_ERRNOS read as not one), and goes below a tree's root only through real directories, never
    # a link, while an os.lstat of the place follows a link at every component but the last. Each case below changes what
    # lies on the way to a place the end's walk could not read, or where the session's transcript lies, so that the walk
    # no longer reaches the place and answers, while the place's own read still fails. Under a read that takes every
    # failed place as lasting (no transcript read, no read of the way), the end stays until the table's bound gives it up
    # and is counted in releaseLost: each case whose name says a place is read as the walk reads it is red there at its
    # last step (no walk, the end kept), and the control holds there too. The unit pin
    # test_a_failed_place_answers_where_the_transcript_lies_in_another_project_and_waits_with_no_transcript_or_a_raise is
    # red there at each kind's first other-project answer.

    def _read_fails(self, p, kind="tree"):
        """Whether the place's own read fails for a reason other than absence: the read _unread_place_reads makes first,
        for a place in a tree an os.lstat and the first entry of its listing for a directory there, for the project
        directory an os.stat and the first entry of its listing, and for an entry of it an os.stat, _REG_MISSING_ERRNOS
        read as not a directory."""
        try:
            if stat.S_ISDIR((os.lstat if kind == "tree" else os.stat)(p).st_mode) and kind != "entry":
                with os.scandir(p) as it:
                    next(it, None)
        except (FileNotFoundError, NotADirectoryError):
            return False
        except OSError as e:
            return not (kind == "entry" and e.errno in (errno.EBADF, errno.ELOOP))
        return False

    def _looked_up_at_the_next_cycle(self, aid, places, path, size, kind="tree"):
        """Each of the end's places (of `kind`) still fails its own read, the walk the lookup makes now answers (no file,
        no fault), and the next cycle looks the end up: one walk, the end forgotten, nothing released or given up, and
        the records still held, since the walk found no file to release."""
        self.assertEqual([self._read_fails(p, kind) for p in places], [True] * len(places),
                         "precondition: each place's own read still fails")
        faults, excluded = [], []
        self.assertEqual((km._subagent_file_walk(self.leaf, aid, [], faults, [], excluded), faults, excluded),
                         (None, [], []), "precondition: the walk the lookup makes now answers, with no file and no fault")
        with self._recording() as got:
            km._begin_checkpoint_cycle()
        self.assertEqual((got["walks"], getattr(km, "_AGENT_ENDED_FAULTED", {})), (1, {}),
                         "the next cycle looks the end up, one walk, and forgets it")
        self.assertEqual((self._weight(path), self._stat("released"), self._stat("releaseLost")),
                         (size, NOTHING_RELEASED, 0), "nothing released or given up: the walk found no file")

    def _sibling_entry_no_longer_a_directory(self, replace):
        """A sibling session directory reached through a link, the agent's file under its tree, the link's target at mode
        000: the walk reads the entry by os.stat, a directory, and excludes the tree, whose root's lstat fails, so the end
        is remembered with that root, a place in a subagents tree. `replace(link)` then leaves the entry something the
        walk's os.stat takes for not a directory, and the walk enters nothing there."""
        proj = os.path.dirname(self.leaf)
        target = os.path.join(self.root, "elsewhere", SIB_SID)
        os.makedirs(os.path.join(target, "subagents"))
        link = os.path.join(proj, SIB_SID)
        os.symlink(target, link)
        path = os.path.join(link, "subagents", "agent-%s.jsonl" % AID3)
        _append(path, _agent_lines(AID3, 0, 40))
        size = self._ended_with_its_file_resolved(AID3, path, standing=False)
        place = os.path.join(link, "subagents")
        with self._unreadable(target):
            km._begin_checkpoint_cycle()
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, AID3): ((place, "tree"),)},
                             "precondition: remembered with the sibling's tree root")
            with self._recording() as got:
                km._begin_checkpoint_cycle()
            self.assertEqual(got, {"lstat": [place], "stat": [], "scandir": [], "walks": 0},
                             "precondition: a cycle under the fault reads the root once (EACCES, no read on the way to a "
                             "root, and no os.stat of the entry for that errno) and makes no walk")
            replace(link)
            self._looked_up_at_the_next_cycle(AID3, (place,), path, size)

    def test_a_sibling_session_directory_replaced_by_a_looping_link_is_read_as_the_walk_reads_it_so_its_end_is_looked_up(self):
        """Road 1 (ELOOP): the link replaced by a link to itself. The walk's os.stat of the entry reads ELOOP, which it
        takes for not a directory, while the lstat of the place reads the same ELOOP through the entry."""
        def loop(link):
            os.unlink(link)
            os.symlink(link, link)
        self._sibling_entry_no_longer_a_directory(loop)

    def test_a_sibling_session_directory_whose_stat_reads_ebadf_is_read_as_the_walk_reads_it_so_its_end_is_looked_up(self):
        """Road 1 (EBADF, by mock: a FUSE filesystem can answer a lookup so, a local one does not): every os.stat and
        os.lstat that resolves the entry reads EBADF, which the walk's os.stat of the entry takes for not a directory."""
        real = {n: getattr(os, n) for n in ("stat", "lstat")}

        def ebadf(link):
            def call(n):
                def f(p, *a, **k):
                    s = os.fspath(p) if isinstance(p, (str, os.PathLike)) else None
                    if s is not None and (s == link and n == "stat" or s.startswith(link + os.sep)):
                        raise OSError(errno.EBADF, "the lookup answered EBADF", s)
                    return real[n](p, *a, **k)
                return f
            for n in real:
                setattr(os, n, call(n))
        try:
            self._sibling_entry_no_longer_a_directory(ebadf)
        finally:
            for n, f in real.items():
                setattr(os, n, f)

    # The next two cases drive the sibling stat's other two answers by mock: a filesystem that answers two lookups of one
    # path differently (a FUSE one can; on a local one an entry that is a file makes an lstat below it read ENOTDIR, an
    # absence, and an entry whose own os.stat fails fails the same way for an lstat that resolves it). Every os.lstat
    # below the entry reads ELOOP, so the sibling stat is made, and the entry's os.stat answers otherwise.

    def _entry_answers_while_below_it_loops(self, answer):
        """(install, real): install(link), the `replace` of _sibling_entry_no_longer_a_directory or a case's own step,
        makes every os.lstat below the link read ELOOP and the link's os.stat answer `answer(path)`; the case restores
        os.stat and os.lstat from `real`."""
        real = {n: getattr(os, n) for n in ("stat", "lstat")}

        def install(link):
            def st(p, *a, **k):
                if isinstance(p, (str, os.PathLike)) and os.fspath(p) == link:
                    return answer(p)
                return real["stat"](p, *a, **k)

            def lst(p, *a, **k):
                if isinstance(p, (str, os.PathLike)) and os.fspath(p).startswith(link + os.sep):
                    raise OSError(errno.ELOOP, "the lookup answered ELOOP", os.fspath(p))
                return real["lstat"](p, *a, **k)
            os.stat, os.lstat = st, lst
        return install, real

    def test_a_sibling_session_directory_whose_stat_reads_a_file_while_below_it_loops_is_read_as_the_walk_reads_it(self):
        """The entry's os.stat reads a regular file: the walk takes it for not a directory and enters nothing, and the
        place read answers the same, so the end is looked up. Red under a mutant that reads that non-directory as the
        fault lasting: the end waits with no walk."""
        file_st = os.stat(self.leaf)
        install, real = self._entry_answers_while_below_it_loops(lambda p: file_st)
        try:
            self._sibling_entry_no_longer_a_directory(install)
        finally:
            for n, f in real.items():
                setattr(os, n, f)

    def test_a_sibling_session_directory_whose_stat_fails_otherwise_while_below_it_loops_keeps_the_fault_with_no_walk(self):
        """The entry's os.stat reads EIO: the walk's os.stat of the entry fails there too, a fault, so the place stays
        unreadable and the end waits with no walk; once the mock is gone and the target reads, the next cycle releases
        the records with their document. Red under a mutant that answers every error of that stat: each cycle walks."""
        proj = os.path.dirname(self.leaf)
        target = os.path.join(self.root, "elsewhere", SIB_SID)
        os.makedirs(os.path.join(target, "subagents"))
        link = os.path.join(proj, SIB_SID)
        os.symlink(target, link)
        path = os.path.join(link, "subagents", "agent-%s.jsonl" % AID3)
        _append(path, _agent_lines(AID3, 0, 40))
        size = self._ended_with_its_file_resolved(AID3, path, standing=False)
        place = os.path.join(link, "subagents")

        def eio(p):
            raise OSError(errno.EIO, "the lookup answered EIO", os.fspath(p))
        install, real = self._entry_answers_while_below_it_loops(eio)
        with self._unreadable(target):
            km._begin_checkpoint_cycle()                                 # the end's cycle: the root's lstat reads EACCES
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, AID3): ((place, "tree"),)},
                             "precondition: remembered with the sibling's tree root")
            install(link)
            try:
                for n in (1, 2):
                    with self._recording() as got:
                        km._begin_checkpoint_cycle()
                    self.assertEqual((got["stat"], got["walks"], km._AGENT_ENDED_FAULTED),
                                     ([link], 0, {(SID, AID3): ((place, "tree"),)}),
                                     "cycle %d: the entry's os.stat fails, so the place stays unreadable, and no walk" % n)
            finally:
                for n, f in real.items():
                    setattr(os, n, f)
            self._held_unwritten_nothing(path, size, "while the entry's os.stat fails")
        km._begin_checkpoint_cycle()
        self._released_with_its_document(path, size)

    def test_an_own_session_directory_left_looping_by_a_clear_is_read_as_the_walk_reads_it_so_its_end_is_looked_up(self):
        """Road 1 through a /clear: the session directory replaced by a link to itself before the end, so the walk's lstat
        of the own subagents directory reads ELOOP, a fault, and the end is remembered with that place. While the session's
        transcript stays the same the place is lasting and no walk is made. A /clear then moves the session to a new
        transcript in the same project: the old session directory is a sibling to the walk from it, read by os.stat, whose
        ELOOP it takes for not a directory. Red under a mutant that answers ELOOP for the own session directory too: the
        cycles before the /clear walk at each."""
        proj = os.path.dirname(self.leaf)
        sess = os.path.join(proj, SID)
        own = os.path.join(sess, "subagents")
        size = self._ended_with_its_file_resolved(AID, self.agent, standing=False)
        os.rename(sess, os.path.join(self.root, "moved-session"))
        os.symlink(sess, sess)                                           # the session directory a link to itself
        km._begin_checkpoint_cycle()                                     # the end's cycle: the own lstat reads ELOOP
        self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, AID): ((own, "tree"),)},
                         "precondition: remembered with the own subagents directory")
        for n in (1, 2):
            with self._recording() as got:
                km._begin_checkpoint_cycle()
            self.assertEqual(got, {"lstat": [own], "stat": [], "scandir": [], "walks": 0},
                             "cycle %d before the /clear: the own place is lasting (its session directory the own one, "
                             "not read by os.stat), and no walk" % n)
        self.leaf = os.path.join(proj, "11111111-2222-3333-4444-a9e7e1d0c0e2.jsonl")   # the transcript after the /clear,
        _append(self.leaf, [{"type": "user", "uuid": "11111111-2222-3333-4444-000000000003", "sessionId": SID,   # which
                             "timestamp": "2026-09-24T10:30:00.000Z",                   # setUp's _path_of stub answers
                             "message": {"role": "user", "content": "Start the notes-api migration review."}}])
        self._looked_up_at_the_next_cycle(AID, (own,), self.agent, size)

    def _nested_place_behind_a_link(self, replace):
        """The workflow agent's directory (workflows/wf_notesapi01) at mode 000: the walk excludes it for its listing and
        the agent's file in it for its lstat, and the end is remembered with both. Two cycles under the fault read both as
        lasting and make no walk, the directories on the way to them being real. `replace(own, moved)` then moves a
        directory on the way out of the tree (to `moved`) and leaves a link in its place, which the walk never goes
        through, while an lstat of each place follows it (or, by mock, makes that directory read as absent while an
        lstat of each place still resolves it)."""
        if os.geteuid() == 0:
            self.skipTest("permission bits do not bind root: no EACCES to drive")
        own = os.path.dirname(self.agent)
        wf = os.path.dirname(self.wf_agent)
        size = self._ended_with_its_file_resolved(WF_AID, self.wf_agent, standing=False)
        moved = os.path.join(self.root, "moved")
        os.chmod(wf, 0o000)
        try:
            km._begin_checkpoint_cycle()
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, WF_AID): ((wf, "tree"), (self.wf_agent, "tree"))},
                             "precondition: remembered with the workflow directory and the file in it")
            for n in (1, 2):
                with self._recording() as got:
                    km._begin_checkpoint_cycle()
                self.assertEqual(got["walks"], 0, "precondition: faulted cycle %d makes no walk" % n)
            replace(own, moved)
            self._looked_up_at_the_next_cycle(WF_AID, (wf, self.wf_agent), self.wf_agent, size)
        finally:                                                         # wherever the workflow directory is now
            for d in (wf, os.path.join(moved, "wf_notesapi01"), os.path.join(moved, "workflows", "wf_notesapi01")):
                with contextlib.suppress(OSError):
                    os.chmod(d, 0o755)

    def test_a_directory_below_a_trees_root_replaced_by_a_looping_link_is_read_as_the_walk_reads_it_so_its_end_is_looked_up(self):
        """Road 2: the workflows directory moved out and a link to itself left in its place."""
        def loop(own, moved):
            os.rename(os.path.join(own, "workflows"), moved)
            os.symlink(os.path.join(own, "workflows"), os.path.join(own, "workflows"))
        self._nested_place_behind_a_link(loop)

    def test_a_directory_below_a_trees_root_replaced_by_a_link_to_it_is_read_as_the_walk_reads_it_so_its_end_is_looked_up(self):
        """Road 2: the workflows directory moved out and a link to it left in its place, so the workflow directory's lstat
        answers through the link and its listing is still refused, and the file's lstat still reads EACCES."""
        def link(own, moved):
            os.rename(os.path.join(own, "workflows"), moved)
            os.symlink(moved, os.path.join(own, "workflows"))
        self._nested_place_behind_a_link(link)

    def test_a_directory_on_the_way_that_reads_as_absent_while_the_place_resolves_is_read_as_the_walk_reads_it(self):
        """Road 2 with nothing on the way (by mock: a filesystem that answers two lookups of one path differently; on a
        local one a directory missing on the way makes the place's own lstat read ENOENT, an absence): the workflows
        directory's os.lstat reads ENOENT while the workflow directory's lstat, which resolves it, still answers and its
        listing is refused. The walk's tree read takes the workflows directory for gone and goes no deeper, and the place
        read answers the same, so the end is looked up. Red under a mutant that reads a way directory's absence as the
        fault lasting: the end waits with no walk."""
        real = os.lstat

        def absent(own, moved):
            gone = os.path.join(own, "workflows")

            def lst(p, *a, **k):
                if isinstance(p, (str, os.PathLike)) and os.fspath(p) == gone:
                    raise FileNotFoundError(errno.ENOENT, "the lookup answered ENOENT", gone)
                return real(p, *a, **k)
            os.lstat = lst
        try:
            self._nested_place_behind_a_link(absent)
        finally:
            os.lstat = real

    def _transcript_in_another_project(self):
        """The session's transcript now lies in another project directory, which holds nothing else: the walk the lookup
        makes lists that directory and no other."""
        other = os.path.join(self.root, "projects", "-home-TESTHOST-notes-web")
        os.makedirs(other)
        self.leaf = os.path.join(other, SID + ".jsonl")                  # which setUp's _path_of stub answers
        _append(self.leaf, [{"type": "user", "uuid": "11111111-2222-3333-4444-000000000004", "sessionId": SID,
                             "timestamp": "2026-09-24T10:30:00.000Z",
                             "message": {"role": "user", "content": "Continue the notes-api review from the web checkout."}}])

    def test_a_project_directory_the_session_no_longer_lists_is_read_as_the_walk_reads_it_so_its_end_is_looked_up(self):
        """The project directory at mode 300, so the walk excludes it for its listing, and the third agent's end, its file
        under a sibling's tree, is remembered with it; a cycle under the fault reads it by its os.stat and its listing and
        makes no walk. The session's transcript then lies in another project directory, the one the walk lists now, so the
        next cycle looks the end up. Red under a mutant that reads the transcript for a place in a tree alone, and under
        one that keeps a project directory lasting whatever the transcript."""
        proj = os.path.dirname(self.leaf)
        path = self._sibling_agent(proj)
        size = self._ended_with_its_file_resolved(AID3, path, standing=False)
        with self._unreadable(proj, mode=0o300):
            km._begin_checkpoint_cycle()
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, AID3): ((proj, "project"),)},
                             "precondition: remembered with the project directory")
            with self._recording() as got:
                km._begin_checkpoint_cycle()
            self.assertEqual(got, {"lstat": [], "stat": [proj], "scandir": [proj], "walks": 0},
                             "precondition: a cycle under the fault reads the project directory once and makes no walk")
            self._transcript_in_another_project()
            self._looked_up_at_the_next_cycle(AID3, (proj,), path, size, kind="project")

    def test_a_project_directory_entry_the_session_no_longer_lists_is_read_as_the_walk_reads_it_so_its_end_is_looked_up(self):
        """A sibling session directory reached through a link whose target lies in a directory at mode 000, so the walk's
        os.stat of the entry fails and excludes it, and the third agent's end, its file under that sibling's tree, is
        remembered with the entry; a cycle under the fault reads the entry by one os.stat and makes no walk. The session's
        transcript then lies in another project directory, whose entries are the ones the walk reads now, so the next
        cycle looks the end up. Red under a mutant that reads the transcript for a place in a tree alone, and under one
        that keeps an entry lasting whatever the transcript."""
        proj = os.path.dirname(self.leaf)
        away = os.path.join(self.root, "elsewhere")
        target = os.path.join(away, SIB_SID)
        os.makedirs(os.path.join(target, "subagents"))
        link = os.path.join(proj, SIB_SID)
        os.symlink(target, link)
        path = os.path.join(link, "subagents", "agent-%s.jsonl" % AID3)
        _append(path, _agent_lines(AID3, 0, 40))
        size = self._ended_with_its_file_resolved(AID3, path, standing=False)
        with self._unreadable(away):
            km._begin_checkpoint_cycle()
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, AID3): ((link, "entry"),)},
                             "precondition: remembered with the entry, a project-directory entry")
            with self._recording() as got:
                km._begin_checkpoint_cycle()
            self.assertEqual(got, {"lstat": [], "stat": [link], "scandir": [], "walks": 0},
                             "precondition: a cycle under the fault reads the entry once and makes no walk")
            self._transcript_in_another_project()
            self._looked_up_at_the_next_cycle(AID3, (link,), path, size, kind="entry")

    def test_a_directory_on_the_way_to_a_place_whose_read_fails_there_keeps_the_place_unreadable_with_no_walk(self):
        """The control of road 2: the workflow directory at mode 000, the end remembered with it and the file in it, then
        the session directory at mode 000 as well, so each place's read fails and so does the lstat of the tree's root on
        the walk's way to it (EACCES), a fault the walk's own lstat of that root meets too. Each cycle keeps both places
        unreadable and makes no walk. Red under a mutant that takes a failed read on the way for a way the walk does not
        go: the first such cycle walks."""
        wf = os.path.dirname(self.wf_agent)
        own = os.path.dirname(self.agent)
        size = self._ended_with_its_file_resolved(WF_AID, self.wf_agent, standing=False)
        with self._unreadable(wf):
            km._begin_checkpoint_cycle()
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, WF_AID): ((wf, "tree"), (self.wf_agent, "tree"))},
                             "precondition: remembered with the workflow directory and the file in it")
            with self._unreadable(os.path.dirname(own)):
                for n in (1, 2):
                    with self._recording() as got:
                        km._begin_checkpoint_cycle()
                    self.assertEqual(got["walks"], 0, "cycle %d: each place's read fails, and the root's on the way to it, "
                                                      "so no walk" % n)
                self._held_unwritten_nothing(self.wf_agent, size, "under the fault")

    def test_a_failed_place_answers_where_the_transcript_lies_in_another_project_and_waits_with_no_transcript_or_a_raise(self):
        """The answers made before the way to a place is read, for each kind of place, each place's read failing (EACCES):
        the project directory at mode 300 (its listing refused), an entry of it (the own session directory) under the
        project directory at mode 600 (its os.stat refused), and the own subagents directory under the session directory
        at mode 000 (its os.lstat refused). Each is lasting from the session's own transcript; each answers when the
        transcript lies in another project directory, since the walk lists that one, and one of the two other directories
        has a name the session's own extends (-home-TESTHOST-notes, against the own -home-TESTHOST-notes-api); and each
        stays lasting when the session has no transcript or its resolution raises, neither of which says where the walk
        goes (a lookup made then would give the end up while the place still cannot be read). Red under a mutant that
        answers either of those two, under one that reads the transcript for a place in a tree alone, and under one that
        takes a place in a tree as inside the project directory by its name without the separator (p.startswith(project)):
        the tree's subcase for -home-TESTHOST-notes, whose path is a prefix of the place's."""
        proj = os.path.dirname(self.leaf)
        sess = os.path.join(proj, SID)
        own = os.path.join(sess, "subagents")
        elsewhere = os.path.join(self.root, "projects", "-home-TESTHOST-notes-web", SID + ".jsonl")
        prefix = os.path.join(self.root, "projects", "-home-TESTHOST-notes", SID + ".jsonl")   # a name the own extends
        own_transcript = km._path_of

        def raises(sid, now=None):
            raise RuntimeError("the session registry could not be read")
        for p, kind, refused, mode in ((proj, "project", proj, 0o300), (sess, "entry", proj, 0o600),
                                       (own, "tree", sess, 0o000)):
            with self.subTest(kind=kind), self._unreadable(refused, mode=mode):
                km._path_of = own_transcript                             # restored by tearDown
                self.assertTrue(self._read_fails(p, kind), "precondition: the place's own read fails")
                self.assertFalse(km._unread_place_reads(p, kind, SID), "control: lasting from the session's own transcript")
                for other in (elsewhere, prefix):
                    km._path_of = lambda sid, now=None, other=other: other
                    self.assertTrue(km._unread_place_reads(p, kind, SID), "another project directory (%s): the walk lists "
                                    "that one" % os.path.basename(os.path.dirname(other)))
                for why, stub in (("no transcript", lambda sid, now=None: None), ("a resolution that raises", raises)):
                    km._path_of = stub
                    self.assertFalse(km._unread_place_reads(p, kind, SID), "%s: the fault lasts" % why)

    def test_a_failed_tree_place_in_the_project_directory_outside_its_subagents_trees_stays_unreadable(self):
        """The tree kind's answer for a place inside the transcript's project directory that lies in no subagents tree:
        the own session directory read as a tree place, and a path below it outside its subagents directory, each whose
        os.lstat fails (an EIO by mock). Neither is on a way the walk takes, so the place's own read decides, and it
        failed: the fault lasts. No lookup records such a place (every tree place the walk records lies at or below a
        subagents directory), so this pins the branch by a direct call. Red under a mutant that answers it."""
        proj = os.path.dirname(self.leaf)
        sess = os.path.join(proj, SID)
        real = os.lstat
        for p in (sess, os.path.join(sess, "notes")):
            def lst(q, *a, p=p, **k):
                if isinstance(q, (str, os.PathLike)) and os.fspath(q) == p:
                    raise OSError(errno.EIO, "the lookup answered EIO", p)
                return real(q, *a, **k)
            with self.subTest(place=os.path.relpath(p, proj)):
                os.lstat = lst
                try:
                    self.assertTrue(self._read_fails(p), "precondition: the place's own read fails")
                    self.assertFalse(km._unread_place_reads(p, "tree", SID), "the place's own failed read decides")
                finally:
                    os.lstat = real

    def test_a_trees_root_replaced_by_a_link_to_it_is_read_as_the_walk_reads_it_so_its_end_is_looked_up(self):
        """Road 2 at the root: the own subagents directory moved out and a link to it left in its place. The walk takes
        a linked subagents directory for no tree and searches nothing under it. Red under a mutant that reads the
        directories on the way from below the root."""
        def link(own, moved):
            os.rename(own, moved)
            os.symlink(moved, own)
        self._nested_place_behind_a_link(link)

    def test_a_faulted_end_forgets_its_unheld_end_so_nothing_pops_the_records_unwritten_under_the_fault(self):
        """An end remembered as unheld, then a read that holds the file, then the agent's second end in a batch whose
        lookup faults. The faulted end carries the agent from then on and the unheld end is forgotten, so the remembered
        releases, which release their path with no lookup, do not pop the records under the fault; the first cycle after
        the clear releases them with their document. Red before the change, and under a mutant that keeps the unheld end:
        the next cycle under the fault pays it, em.release_entry's os.path.exists answers False, and the records are popped
        with no document."""
        self._end_before_any_read()
        self.assertIn((SID, AID), km._AGENT_ENDED_UNHELD, "precondition: the end is remembered as unheld")
        km._agent_steps(self.agent)                                      # a read holds the file after the end
        size = os.path.getsize(self.agent)
        self.assertEqual(self._weight(self.agent), size, "precondition: the read holds the whole file")
        km._SUBAGENT_FILE_CACHE.pop((self.leaf, AID), None)
        self.be.note_agent_live(SID, AID, False)                         # the agent's second end
        with self._unreadable(os.path.dirname(os.path.dirname(self.agent))):
            km._begin_checkpoint_cycle()                                 # the second end's cycle: its lookup faults
            km._begin_checkpoint_cycle()                                 # a cycle with no event under the fault
            self._held_unwritten_nothing(self.agent, size, "under the fault")
            self.assertEqual((SID, AID) in km._AGENT_ENDED_UNHELD, False, "the faulted end forgot the unheld end")
        km._begin_checkpoint_cycle()
        self._released_with_its_document(self.agent, size)

    def test_the_faulted_ends_past_their_bound_give_up_the_oldest_and_count_it_lost(self):
        """The table's bound, shared with _AGENT_RELEASED: past it the oldest faulted end is given up, and counted in
        releaseLost with its cause said once on stderr, since its records stay held. Red under a mutant that forgets it
        silently."""
        saved = km._AGENT_RELEASED_MAX
        km._AGENT_RELEASED_MAX = 2
        self.addCleanup(setattr, km, "_AGENT_RELEASED_MAX", saved)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            for aid in (AID, WF_AID, AID3):
                km._remember_faulted_end((SID, aid), ((os.path.dirname(self.agent), "tree"),))
        self.assertEqual(list(km._AGENT_ENDED_FAULTED), [(SID, WF_AID), (SID, AID3)], "the two newest, oldest first")
        self.assertEqual(self._stat("releaseLost"), 1, "the end given up is counted")
        self.assertEqual(err.getvalue().count("recordCache.releaseLost"), 1, "said once on stderr: %r" % err.getvalue())

    # Two roads release a path with no lookup, so the deferral above does not reach them: the remembered unheld releases of
    # an agent with no faulted end (a faulted end forgets the agent's unheld end, the case above) and the owed releases'
    # pay (em.checkpoint_pay_owed_releases). Each calls em.release_entry on the path, whose own os.path.exists answers
    # False under a fault as it does for a file that is gone, and pops the records with no document (fork PR 913's code,
    # pre-existing). The pay also remembers an owed release it finds absent as unheld while the agent's faulted end waits,
    # which under one lookup a cycle can last cycles after the fault clears, one for each end due ahead of it, so the
    # unheld release reaches that agent too; its last step is the first case below. The two residual cases below are the
    # named witnesses of that residual as it stands; the held follow-up (only ENOENT and ENOTDIR read as gone, any other
    # error deferring the release) turns them red and replaces them. A release either road takes there with the file
    # present forgets the agent's faulted end too, since it covered the agent's file, and one that is the residual's pop
    # with no document keeps it, so the end's lookup after the fault remembers the agent as unheld (the cases after
    # them). The file present is a second read after the release's own, and a fault's edge between the two is a residual
    # _release_ended_agents' docstring states, with no case here.

    def test_residual_an_unheld_end_paid_under_an_unreadable_tree_pops_the_records_without_their_document(self):
        self._end_before_any_read()
        km._agent_steps(self.agent)                                      # a read holds the file after the end
        size = os.path.getsize(self.agent)
        with self._unreadable(os.path.dirname(os.path.dirname(self.agent))):
            km._begin_checkpoint_cycle()                                 # the remembered release, under the fault
            self.assertEqual((self._weight(self.agent), self._stat("released"), em._ckpt_file(self.agent).exists()),
                             (None, {"agentEnded": {"count": 1, "bytes": size}}, False),
                             "the residual: popped under the fault with no checkpoint document")

    def test_residual_a_listing_that_fails_past_its_first_entry_has_its_end_looked_up_at_each_cycle_while_it_lasts(self):
        """The residual witness of one of the two faults the place read cannot see (_unread_place_reads): the own
        subagents directory's listing yields its first entry and then fails (an EIO by mock; the tree memo's entry
        dropped, so the tree's read lists it), and the workflow agent's file lies one level down, where that listing
        would lead. The walk excludes the directory; each cycle's read of it gets the first entry and answers, so the
        end is looked up, one walk, at each cycle while the fault lasts, and released with its document at the first
        cycle after it. A fix that reads what the walk's listing reads turns this red and replaces it."""
        own = os.path.dirname(self.agent)
        size = self._ended_with_its_file_resolved(WF_AID, self.wf_agent, standing=False)
        km._SUBAGENT_TREES.pop(own, None)
        real = os.scandir

        class FailsPastTheFirstEntry:
            def __init__(self, it):
                self.it, self.given = it, False

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.it.close()

            def close(self):
                self.it.close()

            def __iter__(self):
                return self

            def __next__(self):
                if not self.given:
                    self.given = True
                    for e in self.it:                                    # a file first, so the walk learns no directory
                        if not e.is_dir(follow_symlinks=False):
                            return e
                raise OSError(errno.EIO, "the listing failed past its first entry")

        os.scandir = lambda p=".", *a, **k: (FailsPastTheFirstEntry(real(p, *a, **k)) if str(p) == own
                                             else real(p, *a, **k))
        try:
            km._begin_checkpoint_cycle()                                 # the end's cycle: the lookup walks and faults
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, WF_AID): ((own, "tree"),)},
                             "precondition: remembered with the directory whose listing failed")
            for n in (1, 2):
                with self._recording() as got:
                    km._begin_checkpoint_cycle()
                own_listings = [d for d in got["scandir"] if d == own]  # the walk's project listing is an os.scandir
                #                                                         too from 3.13 (Path.iterdir): own's alone count
                self.assertEqual((own_listings, got["walks"]), ([own, own], 1),
                                 "faulted cycle %d: the read answers, so the end is walked, and faults again" % n)
            self._held_unwritten_nothing(self.wf_agent, size, "while the listing fails")
        finally:
            os.scandir = real
        km._begin_checkpoint_cycle()
        self._released_with_its_document(self.wf_agent, size)

    def test_residual_a_resolution_that_fails_where_its_places_lstat_answers_has_its_end_looked_up_at_each_cycle_while_it_lasts(self):
        """The residual witness of the other fault the place read cannot see (_unread_place_reads): the workflow agent's
        file, one level down, whose strict os.path.realpath in _find_agent_file fails (an EIO by mock, the failure a
        readlink of a link above the file makes there) while the file's own lstat answers. The walk excludes the
        candidate; each cycle's read of it, one lstat, answers, so the end is looked up, one walk, at each cycle while
        the fault lasts, and released with its document at the first cycle after it. On Linux a lasting form needs a
        failure the kernel's own resolution of the path does not meet, since an lstat of the whole path reads every
        component the realpath reads; a race (a link replaced during the call) lasts one cycle. A fix that reads what the
        walk's resolution reads turns this red and replaces it."""
        size = self._ended_with_its_file_resolved(WF_AID, self.wf_agent, standing=False)
        real = os.path.realpath

        def failing(p, *a, **k):
            if k.get("strict") and os.fspath(p) == self.wf_agent:
                raise OSError(errno.EIO, "the resolution failed", os.fspath(p))
            return real(p, *a, **k)
        os.path.realpath = failing
        try:
            km._begin_checkpoint_cycle()                                 # the end's cycle: the lookup walks and faults
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, WF_AID): ((self.wf_agent, "tree"),)},
                             "precondition: remembered with the candidate whose resolution failed")
            for n in (1, 2):
                with self._recording() as got:
                    km._begin_checkpoint_cycle()
                self.assertEqual((self.wf_agent in got["lstat"], got["walks"]), (True, 1),
                                 "faulted cycle %d: the candidate's lstat answers, so the end is walked, and faults again" % n)
            self._held_unwritten_nothing(self.wf_agent, size, "while the resolution fails")
        finally:
            os.path.realpath = real
        km._begin_checkpoint_cycle()
        self._released_with_its_document(self.wf_agent, size)

    def test_residual_a_resolution_of_a_trees_root_that_fails_where_its_lstat_answers_has_its_end_looked_up_at_each_cycle(self):
        """The root form of the witness above: the strict os.path.realpath of the own subagents directory in
        _find_agent_file fails (an EIO by mock) while that directory's lstat and the first entry of its listing answer.
        The walk excludes the tree, so the workflow agent's file in it (one level down, where no flat lookup reaches) is
        found nowhere and the end is remembered with the directory; each cycle's read of it answers, so the end is
        looked up, one walk, at each cycle while the fault lasts, and remembered again with the same place, and it is
        released with its document at the first cycle after the fault. A fix that reads what the walk's resolution reads
        turns this red and replaces it."""
        own = os.path.dirname(self.agent)
        size = self._ended_with_its_file_resolved(WF_AID, self.wf_agent, standing=False)
        real = os.path.realpath

        def failing(p, *a, **k):
            if k.get("strict") and os.fspath(p) == own:
                raise OSError(errno.EIO, "the resolution failed", os.fspath(p))
            return real(p, *a, **k)
        os.path.realpath = failing
        try:
            km._begin_checkpoint_cycle()                                 # the end's cycle: the lookup walks and faults
            self.assertEqual(getattr(km, "_AGENT_ENDED_FAULTED", {}), {(SID, WF_AID): ((own, "tree"),)},
                             "precondition: remembered with the tree whose resolution failed")
            for n in (1, 2):
                with self._recording() as got:
                    km._begin_checkpoint_cycle()
                self.assertEqual((own in got["lstat"], got["walks"], km._AGENT_ENDED_FAULTED),
                                 (True, 1, {(SID, WF_AID): ((own, "tree"),)}),
                                 "faulted cycle %d: the root's lstat answers, so the end is walked, and faults again" % n)
            self._held_unwritten_nothing(self.wf_agent, size, "while the resolution fails")
        finally:
            os.path.realpath = real
        km._begin_checkpoint_cycle()
        self._released_with_its_document(self.wf_agent, size)

    def test_residual_an_owed_release_paid_under_an_unreadable_tree_pops_the_records_without_their_document(self):
        size = self._owed()
        with self._unreadable(os.path.dirname(os.path.dirname(self.agent))):
            km._begin_checkpoint_cycle()                                 # the owed release's pay, under the fault
            self.assertEqual((self._weight(self.agent), self._stat("released"), em._ckpt_file(self.agent).exists()),
                             (None, {"agentEnded": {"count": 1, "bytes": size}}, False),
                             "the residual: popped under the fault with no checkpoint document")

    def test_an_unheld_release_taken_while_the_agents_faulted_end_waits_forgets_that_end_too(self):
        """The unheld road's release covers the agent's file for its faulted end too (_release_ended_agents). The state an
        owed release paid as absent leaves beside a faulted end (the residual above) is seeded, as fork PR 882's round-5
        closing check seeded it: the workflow agent's faulted end and then the own agent's, each remembered with the own
        subagents directory, which reads (the fault has cleared), and the own agent remembered as unheld too, its file
        held by a whole read. Under the cap (one lookup a cycle) the first cycle looks the workflow agent's end up (one
        walk; nothing is held for its file, so it is remembered as unheld), and the unheld road releases the own agent's
        file with its document; that release forgets the own agent's faulted end too, and only that end. Red when it does
        not: the faulted end waits its turn, and its lookup at the second cycle finds nothing held and remembers the own
        agent as unheld again, so the unheld road, and with it the residual that reads a fault on the path as the file
        gone, outlives the wait (the rows then: (1, 1, False, True, False, True, 1), (2, 1, False, False, True, True, 1),
        (3, 0, False, False, True, True, 1)). Red too when the release forgets another agent's faulted end (every
        faulted end, the session's, or the oldest): the workflow agent's end is then dropped with no lookup, so the first
        cycle does not remember it as unheld."""
        own = os.path.dirname(self.agent)
        km._remember_faulted_end((SID, WF_AID), ((own, "tree"),))       # an end due ahead of the own agent's
        km._remember_faulted_end((SID, AID), ((own, "tree"),))          # the own agent's faulted end
        km._remember_unheld_end((SID, AID), self.agent)                 # and its unheld end beside it
        km._agent_steps(self.agent)                                      # a read holds the file whole, a fold with it
        size = os.path.getsize(self.agent)
        self.assertEqual(self._weight(self.agent), size, "precondition: the read holds the whole file")
        rows, self.maxDiff = [], None                                    # the whole rows in a red's message
        for n in (1, 2, 3):
            with self._recording() as got:
                km._begin_checkpoint_cycle()
            rows.append((n, got["walks"], (SID, WF_AID) in km._AGENT_ENDED_FAULTED, (SID, AID) in km._AGENT_ENDED_FAULTED,
                         (SID, AID) in km._AGENT_ENDED_UNHELD, (SID, WF_AID) in km._AGENT_ENDED_UNHELD,
                         self._stat("released")["agentEnded"]["count"]))
        self.assertEqual(rows, [(1, 1, False, False, False, True, 1), (2, 0, False, False, False, True, 1),
                                (3, 0, False, False, False, True, 1)],
                         "(cycle, walks, the workflow agent's end faulted, the own agent's end faulted, the own agent's "
                         "end unheld, the workflow agent's end unheld, releases): the first cycle looks the workflow "
                         "agent's end up, and the release forgets the own agent's faulted end alone")
        self.assertEqual((self._weight(self.agent) in (None, 0), em._ckpt_file(self.agent).exists()), (True, True),
                         "the own agent's file released with its document")

    def test_an_owed_release_taken_while_the_agents_faulted_end_waits_forgets_that_end_too(self):
        """The owed releases' pay covers the agent's file for its faulted end too, as the unheld road's release does (the
        case above, whose state this seeds with a third agent's end due ahead as well). The budget refuses the document
        at the first cycle, so the unheld road's release of the own agent's file is deferred, owed, and the own agent's
        faulted end is kept, since a deferral covers nothing yet, while the workflow agent's end, the oldest, is looked
        up. At the second cycle, the budget back, the pay takes the release with its document and forgets the own
        agent's faulted end, and only that end: the third agent's end is looked up (nothing is held for its file, so it
        is remembered as unheld). Red when the pay leaves the own agent's end: it is still in the table after the second
        cycle, and its lookup at the third finds nothing held and remembers the own agent as unheld again (the rows
        then: (1, 1, [AID3, AID], False, False, 0, 'owed'), (2, 1, [AID], False, True, 1, 'taken'), (3, 1, [], True,
        True, 1, 'taken')). Red when a deferred release forgets the faulted end: the first row's table reads [AID3]. Red
        when the pay forgets another agent's end (every faulted end, the session's, or the oldest): the third agent's
        end is dropped with no lookup, so the second cycle does not remember it as unheld."""
        own = os.path.dirname(self.agent)
        _append(os.path.join(own, "agent-%s.jsonl" % AID3), _agent_lines(AID3, 0, 40))
        km._remember_faulted_end((SID, WF_AID), ((own, "tree"),))       # two ends due ahead of the own agent's
        km._remember_faulted_end((SID, AID3), ((own, "tree"),))
        km._remember_faulted_end((SID, AID), ((own, "tree"),))          # the own agent's faulted end
        km._remember_unheld_end((SID, AID), self.agent)                 # and its unheld end beside it
        km._agent_steps(self.agent)                                      # a read holds the file whole, a fold with it
        size = os.path.getsize(self.agent)
        self.assertEqual(self._weight(self.agent), size, "precondition: the read holds the whole file")
        rows, self.maxDiff = [], None
        for n in (1, 2, 3):
            km.CKPT_CONVERGE_BYTES = 1 if n == 1 else 8 * 1024 * 1024   # the first cycle's budget refuses the document
            with self._recording() as got:
                km._begin_checkpoint_cycle()                             # the second pays the owed release
            rec = km._AGENT_RELEASED.get((SID, AID))
            rows.append((n, got["walks"], [aid for _sid, aid in km._AGENT_ENDED_FAULTED],
                         (SID, AID) in km._AGENT_ENDED_UNHELD, (SID, AID3) in km._AGENT_ENDED_UNHELD,
                         self._stat("released")["agentEnded"]["count"], None if rec is None else "taken" if rec[1] else "owed"))
        self.assertEqual(rows, [(1, 1, [AID3, AID], False, False, 0, "owed"), (2, 1, [], False, True, 1, "taken"),
                                (3, 0, [], False, True, 1, "taken")],
                         "(cycle, walks, the faulted ends left, oldest first, the own agent's end unheld, the third "
                         "agent's end unheld, releases, the own agent's release): the deferral keeps the own agent's "
                         "faulted end, and the pay's release forgets it alone")
        self.assertEqual((self._weight(self.agent) in (None, 0), em._ckpt_file(self.agent).exists()), (True, True),
                         "the own agent's file released with its document")

    def _released_under_a_fault_then_at_the_whole_read_after_it(self, size):
        """The rows of a release that pops the own agent's records under R1's fault on its own subagents directory (mode
        000 for a cycle: its lstat answers, its listing and the file's stat are refused) while the agent's faulted end
        waits on that directory: (cycle, the end faulted, the end unheld, releases, weight, document), over the cycle
        under the fault, the cycle after it, the next fold's whole read, and the cycle after that read."""
        own = os.path.dirname(self.agent)
        rows, self.maxDiff = [], None

        def row(n):
            rows.append((n, (SID, AID) in km._AGENT_ENDED_FAULTED, (SID, AID) in km._AGENT_ENDED_UNHELD,
                         self._stat("released")["agentEnded"]["count"], self._weight(self.agent),
                         em._ckpt_file(self.agent).exists()))
        with self._unreadable(own):
            km._begin_checkpoint_cycle()                                 # the release, under the fault
            row(1)
        km._begin_checkpoint_cycle()                                     # the fault cleared: the faulted end looked up
        row(2)
        km._agent_steps(self.agent)                                      # the next fold reads the file whole
        row("read")
        km._begin_checkpoint_cycle()
        row(3)
        self.assertEqual(rows, [(1, True, False, 1, None, False), (2, False, True, 1, None, False),
                                ("read", False, True, 1, size, False), (3, False, False, 2, None, True)],
                         "the release under the fault pops the records with no document and keeps the faulted end; "
                         "its lookup after the fault remembers the agent as unheld, so the whole read is released "
                         "with its document at the cycle after it")

    def test_an_unheld_release_that_pops_the_records_under_a_fault_keeps_the_agents_faulted_end(self):
        """A release that did not see the file did not cover it, so it keeps the agent's faulted end. The own agent is
        remembered as faulted, with the own subagents directory, and as unheld, its file held by a whole read; then the
        directory is at mode 000 for a cycle. The unheld road's release is the residual's own pop with no document
        (em.release_entry's os.path.exists reads the refused stat as the file gone), and the faulted end, kept, waits on
        the directory's listing. At the cycle after the fault it is looked up, finds nothing held, and remembers the
        agent as unheld, so the next fold's whole read of the file, with no document to restore from, is released with
        its document at the cycle after it. Red when the pop forgets the faulted end whatever the release saw: nothing
        remembers the agent after the fault, and the whole read stays held (the rows then: (1, False, False, 1, None,
        False), (2, False, False, 1, None, False), ('read', False, False, 1, <size>, False), (3, False, False, 1,
        <size>, False))."""
        own = os.path.dirname(self.agent)
        km._remember_faulted_end((SID, AID), ((own, "tree"),))
        km._remember_unheld_end((SID, AID), self.agent)
        km._agent_steps(self.agent)                                      # a read holds the file whole
        size = os.path.getsize(self.agent)
        self.assertEqual(self._weight(self.agent), size, "precondition: the read holds the whole file")
        self._released_under_a_fault_then_at_the_whole_read_after_it(size)

    def test_an_owed_release_that_pops_the_records_under_a_fault_keeps_the_agents_faulted_end(self):
        """The pay's form of the case above: the own agent's release owed (the budget refused its document) and its end
        remembered as faulted, with the own subagents directory; then the directory at mode 000 for a cycle. The pay's
        release is the residual's pop with no document and keeps the faulted end; after the fault its lookup remembers
        the agent as unheld, and the next fold's whole read is released with its document at the cycle after it. Red
        when the pay's release forgets the faulted end whatever the release saw (the rows then as the case above's)."""
        own = os.path.dirname(self.agent)
        size = self._owed()
        km._remember_faulted_end((SID, AID), ((own, "tree"),))
        self._released_under_a_fault_then_at_the_whole_read_after_it(size)

    def test_an_unheld_release_that_finds_nothing_held_keeps_the_agents_faulted_end(self):
        """Only a release taken with the file there forgets the agent's faulted end: one that finds nothing held keeps
        it, and the faulted end goes on carrying the agent's release. The workflow agent is remembered as faulted, with
        the own subagents directory, and as unheld, nothing held for its file, while that directory's strict
        os.path.realpath fails (residual 2's root form, an EIO by mock) and its lstat and listing answer. The first
        cycle's unheld release finds nothing held; the faulted end is looked up, one walk, faults again, and forgets the
        unheld end (_release_end). Then the mock is off, a fold holds the file whole, and the directory is at mode 000
        for a cycle: the faulted end waits on its listing and no road releases the file under the fault, so the records
        stay; at the cycle after the fault the lookup releases them with their document. Red when the faulted end is
        forgotten before the release is known: the unheld end stays remembered, and the cycle under the fault pops the
        records with no document."""
        own = os.path.dirname(self.agent)
        km._remember_faulted_end((SID, WF_AID), ((own, "tree"),))
        km._remember_unheld_end((SID, WF_AID), self.wf_agent)
        real = os.path.realpath

        def failing(p, *a, **k):
            if k.get("strict") and os.fspath(p) == own:
                raise OSError(errno.EIO, "the resolution failed", os.fspath(p))
            return real(p, *a, **k)
        os.path.realpath = failing
        try:
            with self._recording() as got:
                km._begin_checkpoint_cycle()                             # absent; the lookup faults again
            self.assertEqual(((SID, WF_AID) in km._AGENT_ENDED_FAULTED, (SID, WF_AID) in km._AGENT_ENDED_UNHELD,
                              got["walks"], self._stat("released")["agentEnded"]["count"]),
                             (True, False, 1, 0), "(faulted, unheld, walks, releases): the release found nothing held, "
                             "so the faulted end is kept, looked up, and remembered again, its unheld end forgotten")
        finally:
            os.path.realpath = real
        km._agent_steps(self.wf_agent)                                   # a fold holds the file whole
        size = os.path.getsize(self.wf_agent)
        self.assertEqual(self._weight(self.wf_agent), size, "precondition: the read holds the whole file")
        with self._unreadable(own):
            km._begin_checkpoint_cycle()
            self._held_unwritten_nothing(self.wf_agent, size, "under the fault")
        km._begin_checkpoint_cycle()
        self._released_with_its_document(self.wf_agent, size)

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

    # ---- a batch end for a remembered pair: its own outcome governs (PR 913 round 2, tests-1) ----
    # The agent's stop finds nothing held and is remembered, a whole read then holds its file, and its task's end reaches a
    # later batch, which speaks for the pair: the remembered loop skips it, and the batch end's release decides. When that
    # release is lost or raises, the pair is forgotten and the release given up, not retried at a later cycle.

    def _remembered_then_task_end(self):
        """The task-end road to a batch end for a remembered pair; returns the file's size, which the whole read holds."""
        self.s._on_task_event("task_started", {"task_id": AID, "task_type": "local_agent"})
        self._end_before_any_read()
        self.assertEqual(km._AGENT_ENDED_UNHELD.get((SID, AID)), self.agent, "precondition: the stop is remembered")
        em._read_jsonl_incremental(self.agent)                           # a whole reader holds the finished agent's file
        size = os.path.getsize(self.agent)
        self.assertEqual(self._weight(self.agent), size, "precondition: the read holds the whole file")
        self._task_end()
        return size

    def _given_up_not_retried(self, size):
        """After the cycle that gave the batch end's release up: that cycle forgot the pair, and the next cycle, with the
        writes on, releases nothing."""
        self.assertEqual((self._weight(self.agent), self._stat("releaseLost")), (size, 1),
                         "precondition: the release was given up and the entry stayed")
        remembered = (SID, AID) in km._AGENT_ENDED_UNHELD
        km._begin_checkpoint_cycle()                                     # the next cycle, the drop writes on
        self.assertEqual(self._weight(self.agent), size, "the next cycle, with the writes on, leaves the given-up file held "
                         "(held: %s of %d bytes)" % (self._weight(self.agent), size))
        self.assertEqual(self._stat("released"), NOTHING_RELEASED, "nothing released")
        self.assertFalse(remembered, "the batch end's outcome forgot the remembered pair")

    def test_a_batch_end_for_a_remembered_pair_whose_release_is_lost_is_given_up(self):
        """Red when a lost batch end leaves the pair remembered: the next cycle releases the file."""
        size = self._remembered_then_task_end()
        km.CKPT_CONVERGE_MS = 0                                          # the drop writes off: the batch end's release is lost
        with contextlib.redirect_stderr(io.StringIO()):
            km._begin_checkpoint_cycle()
        km.CKPT_CONVERGE_MS = 150.0
        self._given_up_not_retried(size)

    def test_a_batch_end_for_a_remembered_pair_whose_release_raises_is_given_up(self):
        """Red when a batch end that raises leaves the pair remembered: the next cycle releases the file."""
        size = self._remembered_then_task_end()
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
        self._assert_raise_line(err.getvalue(), (SID, AID, self.agent))
        self._given_up_not_retried(size)

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
    # kernel/kernel.py holds no session structure. Its one site is upstream's _chat_row_sig, which met this census at fold
    # 3's merge of fork main at batch 921: the mirror predicate, keyed on the key name "bgTasks" alone, whatever the
    # receiver, reads its write into its own dict as a mirror write.
    ("kernel/kernel.py", "_chat_row_sig", MIRROR, "setitem"): [
        (X, "a key of the chat-build signature's own copy of a liveness row (`out`, a dict comprehension over the row, "
            "which it leaves as it was): it writes neither the reg's bgTasks mirror nor any structure a session knows its "
            "agents by")],
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
    a subscript assignment to "bgTasks"; that predicate is keyed on the key name alone, whatever the receiver, so a write of
    the key into a function's own dict is a site too, which the table records EXEMPT with its reason); and every drop of a
    session object from `sessions` (those methods, a del, a subscript assignment). Returns ([(file, function, structure,
    operation, line)], {(file, function): [(line, live)]}), the second the queue calls of each function (`live` the literal,
    or None when it is not one)."""
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
    the census's (CENSUS_NOT_COVERAGE, which the failure message carries). kernel/kernel.py holds no session structure:
    the one site the census finds there, _chat_row_sig's write of "bgTasks" into its own copy of a liveness row, is
    recorded EXEMPT, and test_kernel_py_holds_no_session_structure holds every site found there to an EXEMPT row of its
    own, so a real mirror write planted in kernel/kernel.py fails it.
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
        by_key = {}
        for s in sorted(sites, key=lambda s: s[4]):                      # source order, the table's order per key
            by_key.setdefault(s[:4], []).append(s)
        unexempt = [s for k, found in by_key.items() for i, s in enumerate(found)
                    if [v for v, _why in RELEASE_CENSUS.get(k, [])][i:i + 1] != [X]]   # each site needs an EXEMPT row of its own
        self.assertEqual(unexempt, [], "kernel/kernel.py holds no session structure: every site the census finds there is "
                                       "recorded EXEMPT, one row per site")

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
