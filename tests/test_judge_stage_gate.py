#!/usr/bin/env python3
"""The judge tiers' EVIDENCE GATE (P1b of the judge perf plan, 2026-09-07): the planner and closer skip a
session's per-pass run when nothing their decision path reads has changed since the run that last judged
it to completion. P2 (the same day) put the four store-only tiers on the same gate: the unblocker (the
parse pair and the store trio), the grouper and consolidator (the store trio and cleared.jsonl, no parse),
the distiller (the store trio, the states file and this sid's stall records, no parse); the StoreTiers,
StoreReArms, StoreOwnWrites, StoreCompleteness, UnblockerHazard and DrainStaysUngated classes and the four
FsCompleteness checks below are its tests. J6 of the round-4 perf plan (the same day) put the courier's
per-session scan on the gate: the pinned parse pair, the store trio and the episode log, with the scan
marked incomplete when it produced pending rows or its link repair reached another session's store; the
CourierGate class and the courier's FsCompleteness check are its tests.

Why: every pass ran every discovered session in full (a parse, a store load, the unit walk, the closed-turn
walk, a rollup, an unconditional save), with about two of thirty-three sessions holding anything new per
pass on the live kernel; the planner and closer were two thirds of an idle pass's CPU.

What exact means here, and what every test below protects (CLAUDE.md, cards move on new information):
the gate never withholds a verdict the ungated pass would have filed from NEW evidence. A run is skipped
only when every input the tier reads is identical by identity to what it last judged to completion:
the parse pair pinned with the parse BEFORE it is read (_frame_parse_key, so judged content can be newer
than the stamp, never older), the store trio (store, override journal, archive), the tier's side files
(captions, episodes, the death marker, the sdk reg's spawnedAt value, cleared.jsonl, this sid's stall
records, the LEAF stem's task store), and the one clock input (a background launch's deadline). A stage
that deferred, was paused, failed a call, had a reply rejected without a write, raised, or was cut sets
the completeness bit and leaves no stamp. The probes the design review ran, each a test here: a poke
mid-pass (a turn ending after the pass's first touch), an unpoked background task, a rewind and a cut, a
journal gesture, a nudge block, two concurrent writers, a restart (fresh process state), the death drain,
the archive path.

Accepted lag, recorded here as the design asks: under an open frame every parsed_session caller sees the
pass-start world (a cache hit too), so the six pusher tick jobs that read the judge parse
(_interrupt_block_tick, _closer_pending, _awaiting_wake_outcomes, _deferral_sweep_tick,
_auto_nudge_session, _clear_done_working_notes) see a world up to one pass old for every session, and a
turn that ends after a pass's first touch is judged next pass, whole. That is the frame's design
(2026-07-21); the gate adds no lag beyond the producer's 3 s backstop for the clock input.

PRIVATE synthetic sids (goal-minting fixtures never share the placeholder sid: its override journal is
replayed on every load), invented text, a notes-api with web/api sessions; the journals are removed in
tearDown."""
import builtins
import contextlib
import errno
import io
import json
import os
import pathlib
import re
import shutil
import tempfile
import time
import unittest
from datetime import datetime, timezone
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
jd = load_source("romp_judge_stage_gate", os.path.join(BIN, "romp-judge"))
em = jd.em

SID = "aaaaaaaa-1111-2222-3333-444444444444"      # private synthetic sids, never the shared placeholder
SID2 = "bbbbbbbb-1111-2222-3333-444444444444"
T0 = 1781100000
NOW = T0 + 5000
MINT = '{"ops":[{"why":"x","do":"mint","text":"Goal"}]}'
EMPTY_CLOSE = '{"done": [], "block": []}'
HOLD_ALL = '{"verdicts":[]}'
LIFT_ONE = '{"verdicts":[{"n":1,"do":"lift","why":"the port was named two messages later"}]}'
MIRROR_WHY = "declared in the agent's own to-do list"          # the mirror top's mint reason (_title_mirror_tops)
STORE_TIERS = ("unblock", "group", "consolidate", "distill")
TRIAGE_TIERS = ("plan", "close", "unblock", "courier", "group", "consolidate", "distill")   # run_triage's order
ALL_TIERS = TRIAGE_TIERS + ("index",)          # plus the index tier (run_index, on its own thread beside run_triage
#                                                live; a test pass runs it after the triage tiers)
DELEGATE_REPLY = '{"verdict": "delegating", "goal": 0, "text": "Wire up the export button"}'
MID = "1781100000.11111_22222.TESTHOST"                         # a delivered peer message's id (synthetic)
MID2 = "1781100000.33333_44444.TESTHOST"


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def uline(t, text, uuid, parent=None, ps="typed"):
    return {"type": "user", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "promptSource": ps, "message": {"role": "user", "content": text}}


def aline(t, text, uuid, parent=None, stop="end_turn"):
    return {"type": "assistant", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}],
                        "stop_reason": stop}}


def tool_use_line(t, uuid, parent, tool_id, name, inp):
    return {"type": "assistant", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "stop_reason": "tool_use",
                        "content": [{"type": "tool_use", "id": tool_id, "name": name, "input": inp}]}}


def tool_result_line(t, uuid, parent, tool_id, text):
    return {"type": "user", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": text}]}}


def boundary(t, uuid, parent):
    """A compaction boundary record: the event model opens a trigger-less turn on it."""
    return {"type": "system", "subtype": "compact_boundary", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent}


TWO_TURNS = [uline(T0, "task A", "u1"), aline(T0 + 30, "did A", "a1", "u1"),
             uline(T0 + 100, "task B", "u2", "a1"), aline(T0 + 130, "did B", "a2", "u2")]


TRIAGE_JUDGES = ("planner", "closer", "unblocker", "courier", "grouper", "consolidator", "distiller")   # the tiers' row names


@contextlib.contextmanager
def _store_read_fault(path):
    """A goals store that exists and cannot be READ (an EACCES: nothing on disk moves, so no signature re-arms
    by itself). Both readers of the file fault for exactly this path: the writer's loader's Path.read_text
    (load_goals through _read_store_json) and the fd readers' jd._disk_read (load_goals_shared, the save
    path's _disk_rev and _disk_entry), so no tier reads it by another route. Bytes that do not parse are the
    other case, and not a fault: load_goals quarantines them aside and answers the fresh store (upstream
    #1019, steer 1 of the 2026-09-08 fold, which replaced the fork's fallback store and its stand-downs)."""
    real_read_text, real_disk_read = Path.read_text, jd._disk_read
    target = str(path)

    def read_text(p, *a, **k):
        if str(p) == target:
            raise OSError(errno.EACCES, "Permission denied", target)
        return real_read_text(p, *a, **k)

    def disk_read(fd, path_s):
        if path_s == target:
            raise OSError(errno.EACCES, "Permission denied", target)
        return real_disk_read(fd, path_s)
    Path.read_text, jd._disk_read = read_text, disk_read
    try:
        yield
    finally:
        Path.read_text, jd._disk_read = real_read_text, real_disk_read


def _fresh_store_text(sid):
    """A published fresh store's bytes: the file exists and parses, so a read fault injected on it is the only
    thing between a tier and its content."""
    return json.dumps({k: v for k, v in jd._fresh_store(sid).items() if not k.startswith("_")})


class _Gate(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        jd._rebind_state(self.td)                    # clears the stamps, the value memos and the counters
        jd.end_pass_frame(True)                      # belt: never inherit a frame a crashed test left open
        for c in (jd._PARSE_CACHE, jd._CHAIN_MEMO, jd._BG_SCAN_CACHE, jd._RECON_MEMO, jd._gone_memo):
            c.clear()
        jd._postal_from_memo[0] = (None, ({}, []))   # the ledger memo keys on (mtime, size), not the path: never
        #                                              serve another root's rows under this one
        self.cdir = self.td / "launchdir"; self.cdir.mkdir()
        self.proj = self.td / "projects"
        self.pdir = self.proj / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(self.cdir)))
        self.pdir.mkdir(parents=True)
        jd.NAMES.mkdir(parents=True, exist_ok=True)
        self.claude = self.td / "claude-config"; (self.claude / "tasks").mkdir(parents=True)
        self._env = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.claude)   # the task store, resolved at call time
        self._saved = (jd.PROJECTS, jd.plan_llm, jd.closer_llm, jd.group_llm, jd.opener_llm, jd._PENDING_CUT_FN,
                       jd._judge_run_impl, jd._rewound_away, jd._judge_run, jd._fileset_key, jd._close_turn,
                       jd._STAGE_STAMP_MAX)
        jd.PROJECTS = self.proj
        self.plan_calls, self.close_calls = [], []
        jd.plan_llm = lambda text, menu, human=False, **kw: (self.plan_calls.append(text) or MINT)
        jd.opener_llm = lambda text, menu, **kw: (self.plan_calls.append(text) or MINT)
        jd.closer_llm = lambda tt, mt, *a, **k: (self.close_calls.append(tt) or EMPTY_CLOSE)
        jd.group_llm = lambda menu, judge="grouper": '{"ops":[]}'
        jd._PENDING_CUT_FN = None
        # the store tiers' helpers (P2): hold every block, land every distill, title every mirror top; and a
        # belt under all of them, since no test here may reach the real model call
        self._saved_store = (jd.unblock_llm, jd.distill_llm, jd.brief_llm, jd.stall_llm, jd.mirror_title_llm,
                             jd.parsed_session, jd.courier_llm, jd._courier_scan, jd._segs, jd._session_settled,
                             jd.rollup_status)
        self.unblock_calls, self.distill_calls, self.title_calls, self.courier_calls = [], [], [], []
        # the courier (J6): a delegating verdict with no sender link, so a filed row plants the sender's
        # tracker and files the recipient quiet (the chain walk finds no link to root the mint on)
        jd.courier_llm = lambda text, menu, declared="": (self.courier_calls.append(text) or DELEGATE_REPLY)
        jd.unblock_llm = lambda blocks, since, completed="": (self.unblock_calls.append(blocks) or HOLD_ALL)
        jd.distill_llm = lambda text, work, why, **kw: (self.distill_calls.append(text) or "Shipped the search endpoint.")
        jd.brief_llm = lambda text, work, owed, **kw: (self.distill_calls.append(text) or "Pick the port the api binds.")
        jd.stall_llm = lambda text, work, holding: (self.distill_calls.append(text) or "The build has not finished.")
        jd.mirror_title_llm = lambda subject, frame=None, user_ask=None: (self.title_calls.append(subject) or "Write the api tests")

        # the index tier (J7): a caption for every unit, a gist for every prompt, a record for every archive
        self._saved_index = (jd.caption_llm, jd.gist_llm, jd.archive_llm, jd._index_caption_tasks, jd._index_arch_task,
                             jd.session_turn_captions, jd.ARCH_BUDGET)
        self.caption_calls, self.archive_calls = [], []
        jd.caption_llm = lambda text: (self.caption_calls.append(text) or "Wired the export button.")
        jd.gist_llm = lambda text, judge="gister": (self.caption_calls.append(text) or "Wire the export button")
        jd.archive_llm = lambda log: (self.archive_calls.append(log) or
                                      {"headline": "The notes api", "abstract": "Built the export button."})

        def no_model(*a, **k):
            raise AssertionError("a stage reached the real model call; patch the helper above the belt")
        jd._judge_run_impl = no_model
        jd._judge_ctx.paused, jd._judge_ctx.last_call_fail, jd._judge_ctx.stage_incomplete = False, None, False

    def tearDown(self):
        jd.end_pass_frame(True)
        (jd.caption_llm, jd.gist_llm, jd.archive_llm, jd._index_caption_tasks, jd._index_arch_task,
         jd.session_turn_captions, jd.ARCH_BUDGET) = self._saved_index
        (jd.PROJECTS, jd.plan_llm, jd.closer_llm, jd.group_llm, jd.opener_llm, jd._PENDING_CUT_FN,
         jd._judge_run_impl, jd._rewound_away, jd._judge_run, jd._fileset_key, jd._close_turn,
         jd._STAGE_STAMP_MAX) = self._saved
        (jd.unblock_llm, jd.distill_llm, jd.brief_llm, jd.stall_llm, jd.mirror_title_llm,
         jd.parsed_session, jd.courier_llm, jd._courier_scan, jd._segs, jd._session_settled,
         jd.rollup_status) = self._saved_store
        if self._env is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = self._env
        for sid in (SID, SID2):
            try:
                (jd._overrides_dir() / (sid + ".jsonl")).unlink()   # a sid's journal never outlives its test
            except OSError:
                pass
        jd._judge_ctx.paused, jd._judge_ctx.last_call_fail, jd._judge_ctx.stage_incomplete = False, None, False
        shutil.rmtree(self.td, ignore_errors=True)

    # ── fixture helpers ──
    def _session(self, sid, recs=None, name="web"):
        path = self.pdir / (sid + ".jsonl")
        path.write_text("\n".join(json.dumps(r) for r in (TWO_TURNS if recs is None else recs)) + "\n")
        (jd.NAMES / sid).write_text("%s\t%s\t#abcdef\n" % (name, str(self.cdir)))
        return path

    def _append(self, path, *recs):
        with open(path, "a") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")

    def _states_row(self, sid, t, state):
        jd.STATESDIR.mkdir(parents=True, exist_ok=True)
        with open(jd.STATESDIR / (sid + ".jsonl"), "a") as f:
            f.write(json.dumps({"t": t, "state": state}) + "\n")

    def _peer_line(self, t, uuid, mid, kind="delegate", body="DELEGATE: wire up the export button", parent=None):
        """A delivered peer (postal) message as the transcript records it: the body, then the id and kind
        markers the postal bus appends. The sender is resolved through the ledger row (_ledger_row)."""
        text = "%s\n<!-- romp-msg-id: %s -->" % (body, mid)
        if kind:
            text += "\n<!-- romp-msg-kind: %s -->" % kind
        return uline(t, text, uuid, parent, ps="sdk")

    def _ledger_row(self, mid, from_id, to_id, kind="delegate", body="DELEGATE: wire up the export button", t=T0 + 190, **extra):
        """The postal ledger's "sent" row for a delivered message: the authoritative sender record the parse's
        postal index (author.peer) and the courier's _postal_row read."""
        jd.MESSAGES.parent.mkdir(parents=True, exist_ok=True)
        row = {"t": t, "ev": "sent", "id": mid, "from": "web", "from_id": from_id, "to_id": to_id,
               "kind": kind, "body": body}
        row.update(extra)
        with open(jd.MESSAGES, "a") as f:
            f.write(json.dumps(row) + "\n")

    def _peer_session(self, sid, sender, mid=MID, kind="delegate", t=T0 + 200, replied=True):
        """A recipient session whose third turn is a delivered peer message from `sender` (ledger row
        included), answered when `replied`; the sender session is a plain two-turn one. Returns the path."""
        recs = list(TWO_TURNS) + [self._peer_line(t, "p1", mid, kind=kind, parent="a2")]
        if replied:
            recs.append(aline(t + 30, "On it.", "a3", "p1"))
        self._ledger_row(mid, sender, sid, kind=kind or "delegate", t=t - 10)
        path = self._session(sid, recs)
        self._session(sender, name="api")
        return path

    def _peer_seg_id(self, sid, path):
        """The segment id of the session's peer-triggered segment, as the courier files it."""
        store = jd.load_goals(sid)
        segs = [sg for turn in jd.parsed_session(sid, [str(path)], NOW)["turns"] for sg in jd._segs(turn, store)]
        return next(sg["id"] for sg in segs if jd._seg_peer(sg))

    def _scan_log(self):
        """Wrap _courier_scan to record the sids it ran for; returns the list (cleared by the caller)."""
        real, seen = self._saved_store[7], []

        def scan(fsid, path, now):
            seen.append(fsid)
            return real(fsid, path, now)
        jd._courier_scan = scan
        return seen

    def _pass(self, now=NOW, tiers=("plan", "close")):
        """One gated pass over the fixture: the named tiers in run_triage's order under one frame."""
        jd._discover_cache.clear()                   # discover's list is cached behind a dir fingerprint, not `now`
        runners = {"plan": jd.run_plan, "close": jd.run_close, "unblock": jd.run_unblock, "courier": jd.run_courier,
                   "group": jd.run_group, "consolidate": jd.run_consolidate, "distill": jd.run_distill,
                   "index": jd.run_index}
        own = jd.begin_pass_frame()
        try:
            for t in ALL_TIERS:
                if t in tiers:
                    runners[t](now=now)
        finally:
            jd.end_pass_frame(own)

    def _converge(self, now=NOW, limit=6, tiers=ALL_TIERS):
        """Passes over `tiers` until every one skips: the working pass, the follow-on run that finds nothing
        to write (the tier's own publish re-armed it once), then the skip. Leaves the counters zeroed."""
        for _ in range(limit):
            self._reset()
            self._pass(now, tiers=tiers)
            if all(self._st(t)["ran"] == 0 for t in tiers):
                self._reset()
                return
        self.fail("the fixture did not converge in %d passes" % limit)

    def _st4(self, key="ran"):
        """The four store tiers' `key` counters, in STORE_TIERS order."""
        return tuple(self._st(t)[key] for t in STORE_TIERS)

    def _block(self, sid, nid, t, why="Which port should the api bind?"):
        """A kernel-side nudge block on `nid` at `t`: the journal row plus a publish through save_goals."""
        store = jd.load_goals(sid)
        jd.append_block(sid, nid, "nudge", why, t)
        jd.record_verdict(store, store["nodes"][nid], "nudge", "block", t, why=why)
        jd.rollup_status(store, False)
        jd.save_goals(sid, store)

    def _mirror_top(self, sid, text, n=90):
        """An untitled to-do MIRROR top (the agent's own TaskCreate subject, verbatim): the one node shape
        that makes _title_mirror_tops call the model before the distiller's todo is built."""
        store = jd.load_goals(sid)
        nid = "%s:g%d" % (sid, n)
        store["nodes"][nid] = {"id": nid, "text": text, "parentId": None, "why": MIRROR_WHY, "t": T0 + 300,
                               "mt": T0 + 300, "log": [], "trail": [], "nodeComplete": False, "cleared": False}
        store["status"][nid] = "working"
        jd.save_goals(sid, store)
        return nid

    def _st(self, tier):
        return dict(jd._TIER_STATS[tier])

    def _rows(self, err):
        """The judge-errors rows with `err`, in file order; none when no row has been written yet."""
        if not jd.ERRORS.exists():
            return []
        return [r for r in (json.loads(l) for l in open(jd.ERRORS) if l.strip()) if r.get("err") == err]

    def _reset(self):
        for d in jd._TIER_STATS.values():
            for k in d:
                d[k] = 0

    def _stamp(self, tier, sid=SID):
        return jd._STAGE_STAMP.get((tier, sid))

    def _tops(self, sid=SID):
        store = jd.load_goals(sid)
        return sorted((nd for nd in store["nodes"].values() if nd["parentId"] is None), key=lambda nd: nd["t"])


class Convergence(_Gate):
    def test_two_idle_passes_run_once_then_skip_with_no_store_io(self):
        # the working pass places and sweeps; the tier's own publish re-arms it once (the stamp holds the
        # pre-run identity); the follow-on run makes no call and writes nothing; the third pass skips both
        # tiers, loads and saves nothing for the sid, and still stamps pass_done (a skip is a completed
        # no-op pass: the kernel's wedged-reviver bound reads that watermark)
        self._session(SID)
        self._pass()
        self.assertEqual(len(self.plan_calls), 2, "two ended turns: two work units placed")
        self.assertEqual(len(self.close_calls), 2, "and two turns swept")
        self.assertEqual((self._st("plan")["ran"], self._st("close")["ran"]), (1, 1))
        self.assertEqual((self._st("plan")["stamped"], self._st("close")["stamped"]), (1, 1),
                         "complete runs stamp what they judged")
        self._reset()
        self._pass()                                                    # the idle follow-on: runs, no calls, no write
        self.assertEqual((len(self.plan_calls), len(self.close_calls)), (2, 2), "no model call")
        self.assertEqual((self._st("plan")["ran"], self._st("close")["ran"]), (1, 1),
                         "the tiers' own publishes re-armed them once")
        self._reset()
        wm = jd.pass_watermark("plan", SID), jd.pass_watermark("close", SID)
        io0 = jd.goal_io_stats()
        time.sleep(0.002)
        self._pass()                                                    # the skip
        io1 = jd.goal_io_stats()
        self.assertEqual((self._st("plan")["ran"], self._st("close")["ran"]), (0, 0))
        self.assertEqual((self._st("plan")["skipped"], self._st("close")["skipped"]), (1, 1))
        self.assertEqual((io1["loads"] - io0["loads"], io1["saves"] - io0["saves"]), (0, 0),
                         "a skipped session costs no store load and no save")
        self.assertGreater(jd.pass_watermark("plan", SID), wm[0], "a skip stamps pass_done")
        self.assertGreater(jd.pass_watermark("close", SID), wm[1])
        self.assertEqual((len(self.plan_calls), len(self.close_calls)), (2, 2))

    def test_a_restart_is_a_full_walk(self):
        # the stamps are process state: a kernel restart mid-pass loses them and the first pass after boot
        # judges every session, as before the gate
        self._session(SID)
        self._converge()
        jd._STAGE_STAMP.clear()                                         # what a restart does
        self._pass()
        self.assertEqual((self._st("plan")["ran"], self._st("close")["ran"]), (1, 1))
        self.assertEqual((len(self.plan_calls), len(self.close_calls)), (2, 2), "nothing new: no call either way")

    def test_counters_add_up(self):
        self._session(SID)
        self._pass(); self._pass(); self._pass()
        for t in ("plan", "close"):
            s = self._st(t)
            self.assertEqual(s["ran"], s["stamped"] + s["bypassed"] + s["incomplete"], t)
        ts = jd.tier_stats()
        self.assertEqual(set(ts), set(jd.GATED_TIERS) | {"stamps"})
        self.assertEqual(ts["stamps"], 2, "one stamp per (tier, sid)")


class ATurnEndingMidPass(_Gate):
    def test_a_turn_ending_after_the_first_touch_is_judged_next_pass_whole(self):
        # the review's hazard: a tick job (or the index tier) touches the session while its last turn is
        # OPEN; the turn's final record and the idle row land; the gated planner and closer run. Their
        # stamps must hold the PRE-append pair (the world they judged), so the next pass runs both stages
        # over the ended turn. A stamp stat'd at the stage's own moment would record the post-append key
        # and skip the ended turn until an unrelated write. Without P1a's key pin this test fails.
        path = self._session(SID, [uline(T0, "task A", "u1"), aline(T0 + 30, "did A", "a1", "u1"),
                                   uline(T0 + 100, "task B", "u2", "a1"),
                                   aline(T0 + 110, "starting on B", "a2", "u2", stop="tool_use")])
        self._converge()
        own = jd.begin_pass_frame()
        try:
            jd.parsed_session(SID, [str(path)], NOW)                    # the tick job's first touch, turn open
            pre = jd._frame["keys"][("parse", SID)]
            self._append(path, aline(T0 + 140, "did B", "a3", "a2"))
            self._states_row(SID, T0 + 141, "idle")
            jd.run_plan(now=NOW)
            jd.run_close(now=NOW)
        finally:
            jd.end_pass_frame(own)
        for t in ("plan", "close"):
            st = self._stamp(t)
            self.assertIsNotNone(st, "%s: the pass completed and stamped" % t)
            self.assertEqual(st[0][0][1], jd._pair_key(pre), "%s: the stamp holds the PRE-append pair" % t)
        self._reset()
        self._pass()
        self.assertEqual((self._st("plan")["ran"], self._st("close")["ran"]), (1, 1),
                         "the next pass runs both stages: the live pair differs from the stamped one")
        self.assertIn("did B", " ".join(self.plan_calls), "the planner judged the ended turn's work")
        turns = jd.parsed_session(SID, [str(path)], NOW)["turns"]
        self.assertTrue(turns[-1]["ended"])
        self.assertIn(turns[-1]["id"], jd.load_goals(SID).get("closedTurns") or [], "the closer swept it")


class TheCut(_Gate):
    def test_a_cut_arming_between_the_pin_and_the_parse_withholds_the_stamp(self):
        # the user's cut rule (2026-09-07): the parse runs under the LIVE cut, and a cut that arms after
        # the gate pinned makes the served pair differ from the pinned one, so the run is not stamped
        # (bypassed) and the sid stays due. Then: with the cut standing, the cut world converges and is
        # stamped under the cut; the cut clearing with no file change re-arms both tiers, and the
        # previously cut turn is judged. The invariant: no verdict the ungated pass would file is lost.
        path = self._session(SID)
        self._converge()
        self._append(path, uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))
        before = self._stamp("plan")
        own = jd.begin_pass_frame()
        try:
            pinned, _cut, _fr = jd._frame_parse_key(SID, [str(path)])   # the gate's pin (also run_plan's)
            self.assertEqual(pinned[1], "")
            jd._PENDING_CUT_FN = lambda fsid: "a2"                       # a bare rollback arms: u3/a3 abandoned
            jd.run_plan(now=NOW)
            jd.run_close(now=NOW)
        finally:
            jd.end_pass_frame(own)
        self.assertEqual(self._st("plan")["ran"], 1, "the transcript grew: the planner ran")
        self.assertEqual(self._st("plan")["bypassed"], 1, "but the served cut differs from the pinned one: no stamp")
        self.assertEqual(self._stamp("plan"), before, "the old stamp stands (it describes the last COMPLETE run)")
        self.assertNotIn("task C", " ".join(self.plan_calls), "the planner judged the cut world: the tail is not planned")
        self._reset()
        self._pass()                                                    # the cut world, pinned and parsed alike
        self.assertEqual(self._st("plan")["stamped"], 1, "a pin and a parse under the same cut stamp")
        self.assertEqual(self._stamp("plan")[0][0][1][1], "a2", "the stamp holds the cut")
        self._reset()
        self._pass()
        self.assertEqual((self._st("plan")["skipped"], self._st("close")["skipped"]), (1, 1))
        jd._PENDING_CUT_FN = None                                        # the rollback dissolves: no file change
        self._reset()
        self._pass()
        self.assertEqual((self._st("plan")["ran"], self._st("close")["ran"]), (1, 1),
                         "the cut clearing re-arms both tiers with no file change")
        self.assertIn("task C", " ".join(self.plan_calls), "and the un-cut tail is judged")

    def test_a_rewind_pending_defers_without_a_stamp_and_a_durable_rewind_retires(self):
        path = self._session(SID)
        self._converge()
        self._append(path, uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))
        jd._rewound_away = lambda fsid, p, uuid: "pending"
        self._pass()
        self.assertIsNone(self._stamp("plan") if self._st("plan")["stamped"] else None)
        self.assertEqual(self._st("plan")["incomplete"], 1, "a pending rewind defers the unit: no stamp")
        self._reset()
        self._pass()
        self.assertEqual(self._st("plan")["ran"], 1, "still due")
        self.assertEqual(self._st("plan")["incomplete"], 1)
        calls = []

        def durable_then_live(fsid, p, uuid):
            calls.append(uuid)
            return "durable" if len(calls) == 1 else False              # the unit's check; the plan-sync's is live
        jd._rewound_away = durable_then_live
        self._reset()
        self._pass()
        self.assertEqual(self._st("plan")["stamped"], 1, "a durable rewind retires the unit: a complete run")
        store = jd.load_goals(SID)
        retired = [k for k, v in store["placements"].items() if v is None]
        self.assertTrue(retired, "the unit is retired, not planned")
        self.assertNotIn("task C", " ".join(self.plan_calls))


class ARollbackArmingDuringTheCall(_Gate):
    def test_the_apply_time_pending_leg_leaves_no_stamp(self):
        # the review's second finding (2026-09-07): a bare rollback arming DURING the planner's model call
        # reaches apply_plan_guarded's pending leg past the unit loop's own check; the leg defers the unit
        # with no write, so the run must mark itself incomplete or the stamp holds the deferred unit until
        # an unrelated re-arm. The latest segment is trigger-less (a compaction boundary) so the plan-sync
        # stand-down, the other pending mark, cannot fire: the mark seen here is the apply leg's own.
        path = self._session(SID, TWO_TURNS + [boundary(T0 + 300, "cb1", "a2")])
        self._converge()
        store = jd.load_goals(SID)
        segs = [s for t in jd.parsed_session(SID, [str(path)], NOW)["turns"] for s in jd._segs(t, store)]
        self.assertIsNone(max(segs, key=lambda s: s.get("t") or 0).get("trigger"), "fixture: the latest segment has no trigger")
        seg2 = next(s for s in segs if s.get("trigger") == "u2")
        self.assertIn(seg2["id"], store["placements"], "fixture: turn 2's unit was placed")
        del store["placements"][seg2["id"]]                            # turn 2's unit falls due again
        jd.save_goals(SID, store)
        real = jd.plan_llm

        def arm_during_call(text, menu, human=False, **kw):
            jd._PENDING_CUT_FN = lambda fsid: "a1"                        # the rollback arms while the model thinks
            return real(text, menu, human=human, **kw)
        jd.plan_llm = arm_during_call
        self._reset()
        self._pass(tiers=("plan",))
        jd.plan_llm = real
        s = self._st("plan")
        self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0), "deferred at apply time: no stamp")
        rows = [json.loads(l) for l in open(jd.ERRORS) if l.strip()]
        self.assertEqual([r["err"] for r in rows if "rewind" in str(r.get("err"))], ["rewind-stand-down-pending"],
                         "the apply leg's own row, and no other stand-down")
        self.assertNotIn(seg2["id"], jd.load_goals(SID)["placements"], "deferred: no write, the key stays absent")
        jd._PENDING_CUT_FN = None                                       # the rollback dissolves: no file change
        self._reset()
        self._pass(tiers=("plan",))
        self.assertEqual(self._st("plan")["ran"], 1, "still due: the deferred run left no stamp")
        self.assertIn(seg2["id"], jd.load_goals(SID)["placements"], "and the unit is placed")
        self.assertEqual(self._st("plan")["stamped"], 1)


class ReArms(_Gate):
    """Each input re-arms exactly its tiers and only its sid."""

    def _rearms(self, plan, close, msg):
        self._reset()
        self._pass()
        self.assertEqual((self._st("plan")["ran"], self._st("close")["ran"]), (plan, close), msg)

    def test_transcript_and_states_re_arm_both(self):
        path = self._session(SID)
        self._converge()
        self._append(path, uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))
        self._rearms(1, 1, "a transcript append")
        self._converge()
        self._states_row(SID, T0 + 300, "idle")
        self._rearms(1, 1, "a states row (the states file is in the parse key)")

    def test_store_journal_and_archive_re_arm_both(self):
        self._session(SID)
        self._converge()
        store = jd.load_goals(SID)
        top = self._tops()[0]
        store["nodes"][top["id"]]["text"] = "Renamed by a kernel-side writer"
        jd.save_goals(SID, store)
        self._rearms(1, 1, "a save_goals publish (a rename: new identity)")
        self._converge()
        jd.append_override(SID, top["id"], "resolve", NOW + 1)          # the user's gesture: the journal only
        self._rearms(1, 1, "a journal append with no store write")
        self.assertEqual(jd.load_goals(SID)["status"].get(top["id"]), "completed", "the replayed resolve took")
        self._converge()
        jd.save_goal_archive(SID, {"rompUuid": SID, "nodes": {}, "status": {}})
        self._rearms(1, 1, "an archive write")

    def test_a_nudge_block_re_arms_both(self):
        # the kernel's nudge block: a journal row plus a publish through save_goals
        self._session(SID)
        self._converge()
        top = self._tops()[0]
        store = jd.load_goals(SID)
        jd.append_block(SID, top["id"], "nudge", "Which port should the api bind?", NOW + 2)
        jd.record_verdict(store, store["nodes"][top["id"]], "nudge", "block", NOW + 2, why="Which port should the api bind?")
        jd.rollup_status(store, False)
        jd.save_goals(SID, store)
        self._rearms(1, 1, "a nudge block")
        self.assertEqual(jd.load_goals(SID)["status"].get(top["id"]), "blocked")

    def test_captions_and_episodes_re_arm_the_planner_only(self):
        self._session(SID)
        self._converge()
        jd.CAPDIR.mkdir(parents=True, exist_ok=True)
        with open(jd.CAPDIR / (SID + ".jsonl"), "a") as f:
            f.write(json.dumps({"id": "seg-x#p", "caption": "Ship the notes-api search"}) + "\n")
        self._rearms(1, 0, "a captions append")
        self._converge()
        jd.EPIDIR.mkdir(parents=True, exist_ok=True)
        with open(jd.EPIDIR / (SID + ".jsonl"), "a") as f:
            f.write(json.dumps({"head": "u1", "fsid": SID, "t": T0}) + "\n")
        self._rearms(1, 0, "an episodes row")

    def test_the_death_marker_and_spawned_at_re_arm_both_and_a_reg_rewrite_re_arms_nothing(self):
        self._session(SID)
        self._converge()
        jd._write_death_marker(SID, {"t": T0 + 500, "by": "probe", "endedAt": T0 + 500})   # finalized: no epilogue
        self._rearms(1, 1, "a death marker")
        self._converge()
        reg = jd.STATE / "sdk" / (SID + ".json")
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text(json.dumps({"spawnedAt": T0 + 600, "model": "sonnet"}))
        self._rearms(1, 1, "a spawnedAt change (a revival)")
        self._converge()
        reg.write_text(json.dumps({"spawnedAt": T0 + 600, "model": "opus", "pushNote": "x"}))
        self._rearms(0, 0, "a reg rewrite that keeps spawnedAt (a model pick, a push note)")
        reg.write_text(json.dumps({"spawnedAt": T0 + 700, "model": "opus"}))
        self._rearms(1, 1, "the next revival")

    def test_a_reg_appearing_or_vanishing_re_arms_both_through_sdk_owned(self):
        # _sdk_owned (the reg's existence) is its own input: the parse authors the composer's input as the
        # human only for an SDK session, so a reg with no spawnedAt still re-arms when it appears or goes
        self._session(SID)
        self._converge()
        reg = jd.STATE / "sdk" / (SID + ".json")
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text(json.dumps({"model": "sonnet"}))                 # no spawnedAt: only the existence changes
        self.assertIsNone(jd._reg_spawned_at(SID), "premise: the value memo reads None either way")
        self._rearms(1, 1, "a reg appearing")
        self._converge()
        reg.unlink()
        self._rearms(1, 1, "a reg vanishing")

    def test_the_task_store_re_arms_the_planner_under_the_leaf_stem(self):
        # a to-do item created, then flipped in place, under the LEAF stem (what _sync_declared_plan reads:
        # a /clear fork lane's leaf is not the romp sid); a dir under the romp sid on a fork lane is not read
        path = self._session(SID)
        self._converge()
        d = self.claude / "tasks" / SID                                  # stem == sid here: the plain lane
        plan0, close0 = jd._stage_sig("plan", SID, str(path)), jd._stage_sig("close", SID, str(path))
        d.mkdir()
        (d / "1.json").write_text(json.dumps({"id": "1", "subject": "write the api tests", "status": "pending"}))
        plan1 = jd._stage_sig("plan", SID, str(path))
        self.assertNotEqual(plan1, plan0, "a to-do item created moves the planner's signature")
        self.assertEqual(jd._stage_sig("close", SID, str(path)), close0, "the closer does not read the task store")
        self._reset()
        self._pass()
        self.assertEqual(self._st("plan")["ran"], 1, "the planner runs (and mirrors the open item, which re-arms the closer)")
        self.assertTrue(any(nd.get("agentTask") for nd in jd.load_goals(SID)["nodes"].values()), "the mirror landed")
        self._converge()
        plan2 = jd._stage_sig("plan", SID, str(path))
        (d / "1.json").write_text(json.dumps({"id": "1", "subject": "write the api tests", "status": "completed"}))
        os.utime(d / "1.json", ns=(time.time_ns() + 5_000_000, time.time_ns() + 5_000_000))
        self.assertNotEqual(jd._stage_sig("plan", SID, str(path)), plan2, "an item flipped in place moves it too")
        self._reset()
        self._pass()
        self.assertEqual(self._st("plan")["ran"], 1)
        # the leaf-stem rule at the signature level, on a fork-lane path whose stem is not the sid
        fork = self.pdir / "cccccccc-1111-2222-3333-444444444444.jsonl"
        fork.write_text(json.dumps(uline(T0 + 900, "after the clear", "u9")) + "\n")
        s1 = jd._stage_sig("plan", SID, str(fork))
        (self.claude / "tasks" / fork.stem).mkdir()
        (self.claude / "tasks" / fork.stem / "1.json").write_text(json.dumps({"id": "1", "subject": "x", "status": "pending"}))
        s2 = jd._stage_sig("plan", SID, str(fork))
        self.assertNotEqual(s1, s2, "the LEAF stem's task store is in the planner's signature")
        (d / "2.json").write_text(json.dumps({"id": "2", "subject": "y", "status": "pending"}))
        self.assertEqual(jd._stage_sig("plan", SID, str(fork)), s2, "the romp sid's dir is not read on a fork lane")

    def test_cleared_rows_re_arm_both_and_a_second_sid_stays_stamped(self):
        self._session(SID)
        self._session(SID2, name="api")
        self._converge()
        with open(jd.STATE / "cleared.jsonl", "a") as f:
            f.write(json.dumps({"id": SID2 + ":g1", "op": "clear", "t": NOW}) + "\n")
        self._rearms(2, 2, "a cleared.jsonl row re-arms every session's planner and closer (whole-file identity)")
        self._converge()
        self._append(self.pdir / (SID2 + ".jsonl"), uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))
        self._rearms(1, 1, "the second sid's append")
        self.assertIsNotNone(self._stamp("plan", SID))
        self.assertEqual(self._st("plan")["skipped"], 1, "the first sid skipped")

    def test_value_inputs_are_read_by_value_not_by_file_identity(self):
        # the reg's spawnedAt and this sid's stall records are VALUE inputs: a rewrite in place that keeps
        # the file's (inode, mtime_ns, size) must still be seen. The kernel publishes both files by rename,
        # so identity moves there; a test fixture (or another writer) rewriting in place within one
        # mtime tick does not, and an identity memo served the previous content (17 distiller tests went
        # red under xdist for it, 2026-09-07)
        self._session(SID)
        an = jd.STATE / "auto-nudge.json"
        an.write_text(json.dumps({"enabled": False, "deferred": {SID2 + ":g1": {"at": NOW, "why": "waiting on the closer", "sid": SID2}}}))
        st = os.stat(an)
        self.assertEqual(jd._stall_slice(SID), ())
        body = json.dumps({"enabled": False, "deferred": {SID + ":g1": {"at": NOW, "why": "waiting on the closer", "sid": SID}}})
        self.assertEqual(len(body), st.st_size, "fixture: the rewrite keeps the size (the sids have one length)")
        an.write_text(body)
        os.utime(an, ns=(st.st_atime_ns, st.st_mtime_ns))              # ...and the mtime: identity unchanged
        self.assertEqual(os.stat(an).st_ino, st.st_ino, "fixture: written in place")
        self.assertEqual(jd._stall_slice(SID), ((SID + ":g1", "waiting on the closer", NOW),),
                         "the slice follows the content, not the identity")
        reg = jd.STATE / "sdk" / (SID + ".json")
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text(json.dumps({"spawnedAt": 1781100600}))
        st = os.stat(reg)
        self.assertEqual(jd._reg_spawned_at(SID), 1781100600)
        reg.write_text(json.dumps({"spawnedAt": 1781100700}))          # same length, a revival
        os.utime(reg, ns=(st.st_atime_ns, st.st_mtime_ns))
        self.assertEqual(jd._reg_spawned_at(SID), 1781100700, "the value follows the content, not the identity")

    def test_a_stall_record_for_this_sid_re_arms_and_another_sids_does_not(self):
        self._session(SID)
        self._converge()
        top = self._tops()[0]
        an = jd.STATE / "auto-nudge.json"
        an.write_text(json.dumps({"enabled": False, "deferred": {SID2 + ":g1": {"at": NOW, "why": "the closer has not settled the turn", "sid": SID2}}}))
        self._rearms(0, 0, "another sid's stall record")
        an.write_text(json.dumps({"enabled": False, "deferred": {top["id"]: {"at": NOW, "why": "the closer has not settled the turn", "sid": SID}}}))
        self._rearms(1, 1, "this sid's stall record (rollup_status reads it to retire a stall warn)")


class ConcurrentWriters(_Gate):
    def test_a_kernel_side_publish_during_the_stage_is_never_skipped_over(self):
        # a second writer publishes while the planner holds its store across a model call: the planner's
        # stamp holds the pre-run identity, so the next pass re-reads the store (the other writer's work
        # rebased in) and stamps only when nothing moves
        path = self._session(SID)
        self._converge()
        self._append(path, uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))
        real = jd.plan_llm

        def plan_and_race(text, menu, human=False, **kw):
            side = jd.load_goals(SID)                                   # the nudge tick, on its own thread
            side["nodes"][SID + ":side"] = {"id": SID + ":side", "text": "Answer the port question", "parentId": None,
                                            "nodeComplete": False, "blocked": True, "cleared": False, "trail": [],
                                            "t": NOW, "log": []}
            jd.save_goals(SID, side)
            return real(text, menu, human=human, **kw)
        jd.plan_llm = plan_and_race
        self._pass()
        jd.plan_llm = real
        self.assertIn(SID + ":side", jd.load_goals(SID)["nodes"], "the racing publish survived the planner's save")
        self._reset()
        self._pass()
        self.assertEqual(self._st("plan")["ran"], 1, "the identity moved under the stamp: the planner runs again")
        self._reset()
        self._pass()
        self.assertEqual((self._st("plan")["skipped"], self._st("close")["skipped"]), (1, 1))


class Completeness(_Gate):
    """A stage that did not finish leaves no stamp, so the sid stays due."""

    def test_an_empty_or_whitespace_reply_keeps_the_planner_due_without_a_parse_fail(self):
        # the stripped-reply case patches _judge_run_impl, not plan_llm: plan_llm strips the reply, so a
        # whitespace reply reaches the stage as "" and the belt in _judge_run marks the stage incomplete
        path = self._session(SID)
        self._converge()
        self._append(path, uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))
        jd.plan_llm = self._saved[1]                                    # the real planner helper, over the belt
        for reply in ("", "   "):
            jd._judge_run_impl = lambda *a, **k: reply
            self._reset()
            self._pass(tiers=("plan",))
            self.assertEqual(self._st("plan")["ran"], 1)
            self.assertEqual(self._st("plan")["incomplete"], 1, "reply %r: the call failed, the stage is incomplete" % reply)
            self.assertEqual(self._st("plan")["stamped"], 0)
            self.assertFalse(jd.load_goals(SID).get("parseFails"), "no parse try burned on a failed call")
        self.assertIsNotNone(self._stamp("plan"), "the earlier complete run's stamp stands")

    def test_a_failed_closer_call_and_a_rejected_reply_keep_the_closer_due(self):
        path = self._session(SID)
        self._converge()
        self._append(path, uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))
        jd.closer_llm = lambda *a, **k: ""                              # a cut: the call failed
        self._pass()
        self.assertEqual((self._st("close")["ran"], self._st("close")["incomplete"]), (1, 1))
        self._reset()
        jd.closer_llm = lambda *a, **k: "not a verdict at all"          # a parse reject under the cap
        self._pass()
        self.assertEqual((self._st("close")["ran"], self._st("close")["incomplete"]), (1, 1))
        self._reset()
        jd.closer_llm = lambda tt, mt, *a, **k: EMPTY_CLOSE             # a served reply
        self._pass()
        self.assertEqual(self._st("close")["stamped"], 1)

    def test_a_raising_stage_stamps_nothing(self):
        path = self._session(SID)
        self._converge()
        self._append(path, uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))
        before = self._stamp("close")

        def boom(*a, **k):
            raise RuntimeError("closer down")
        jd._close_turn = boom
        self._reset()
        self._pass()
        self.assertEqual(self._stamp("close"), before, "no stamp from a raised run")
        rows = [json.loads(l) for l in open(jd.ERRORS) if l.strip()]
        self.assertTrue(any(r.get("err") == "pass-crash" for r in rows), "the crash is logged, as before")
        s = self._st("close")
        self.assertEqual((s["ran"], s["incomplete"]), (1, 1), "a raised run counts as incomplete")
        self.assertEqual(s["ran"], s["stamped"] + s["bypassed"] + s["incomplete"], "the identity romp perf reads holds through a crash")

    def test_a_vanished_candidate_runs_the_stage_and_stamps_nothing(self):
        path = self._session(SID)
        self._converge()
        self._append(path, uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))
        before = self._stamp("plan")

        def vanished(files):
            raise OSError("a candidate vanished between the exists() and the stat")
        jd._fileset_key = vanished
        self._pass(tiers=("plan",))
        self.assertEqual((self._st("plan")["ran"], self._st("plan")["bypassed"]), (1, 1))
        self.assertEqual(self._stamp("plan"), before)
        self.assertIn("task C", " ".join(self.plan_calls), "the stage ran over the live world")


class TheClock(_Gate):
    def _monitor_fixture(self):
        # turn 1: a non-persistent Monitor launched with a 60 s timeout_ms, its ack, then the turn ends: the
        # launch is running with a deadline (its t + 60); the closer stamps the wait on that turn's top.
        # turn 2: task A, done by the closer; its top is the last placement, so it is the FOCUS whose settle
        # waits on the hold (rollup_status: settled = not the focus, or the session settled).
        launch_t = T0 + 100
        recs = [uline(T0 + 90, "watch the deploy log", "u1"),
                tool_use_line(launch_t, "a1", "u1", "toolu_m1", "Monitor", {"command": "tail -f deploy.log", "timeout_ms": 60000}),
                tool_result_line(launch_t + 1, "r1", "a1", "toolu_m1", "Monitor started"),
                aline(launch_t + 5, "Watching the deploy log in the background.", "a2", "r1"),
                uline(T0 + 200, "task A", "u3", "a2"), aline(T0 + 230, "did A", "a3", "u3")]
        path = self._session(SID, recs)

        def closer(tt, mt, *a, **k):
            self.close_calls.append(tt)
            if "did A" in tt:
                return '{"done": [{"goal": 1, "why": "task A shipped"}], "block": []}'
            return '{"done": [], "block": [], "awaiting": [{"goal": 1, "why": "the deploy log is still being watched"}]}'
        jd.closer_llm = closer
        return path, launch_t + 60.0 + 120.0                            # the expiry: deadline + grace

    def test_the_stamp_carries_the_next_expiry_and_the_run_is_due_once_the_clock_passes_it(self):
        path, expiry = self._monitor_fixture()
        now0 = int(expiry) - 100
        self._converge(now0)
        watch, g1 = self._tops()                                        # the monitor's top, then task A's
        store = jd.load_goals(SID)
        self.assertTrue(store["nodes"][g1["id"]]["nodeComplete"], "premise: the closer filed task A done")
        self.assertTrue(store["nodes"][watch["id"]].get("awaitingWhy"), "premise: the closer stamped the wait")
        self.assertIn(g1["id"], store.get("confirming") or [], "the settle is held: the monitor is awaited")
        self.assertEqual(self._stamp("plan")[1], expiry, "the planner's stamp carries the launch's expiry")
        self.assertEqual(self._stamp("close")[1], expiry)
        self._reset()
        self._pass(int(expiry))                                         # at the instant: not yet expired
        self.assertEqual((self._st("plan")["skipped"], self._st("close")["skipped"]), (1, 1),
                         "skipped at the expiry instant (em._bg_expired reads now > expiry)")
        self._reset()
        self._pass(int(expiry) + 1)
        self.assertEqual(self._st("plan")["due_clock"], 1, "past the expiry the planner runs on the clock alone")
        self.assertEqual(self._st("plan")["ran"], 1)
        store = jd.load_goals(SID)
        self.assertEqual(store["status"].get(g1["id"]), "completed", "the expired wait released the settle")
        self.assertIsNone(self._stamp("plan")[1], "no future expiry left: the stamp's not-before is None")

    def test_a_complete_run_at_the_expiry_instant_keeps_the_clock(self):
        # the review's boundary case (2026-09-07): run_triage's now is int(time.time()) and transcript
        # timestamps are whole seconds, so a pass lands in the expiry's own second routinely. At that
        # instant the launch has not expired (em._bg_expired is strict), the run holds the settle, and the
        # stamp must still carry the expiry: a stamp with no clock would skip every later pass while the
        # ungated pass at now > expiry releases the hold and completes the top.
        path, expiry = self._monitor_fixture()
        self.assertEqual(expiry, int(expiry), "fixture: an integral expiry (launch t + timeout + grace)")
        self._converge(int(expiry) - 100)
        watch, g1 = self._tops()
        with open(jd.STATE / "cleared.jsonl", "a") as f:               # an unrelated re-arm in the expiry's second
            f.write(json.dumps({"id": "cccccccc-1111-2222-3333-444444444444:g7", "op": "clear", "t": int(expiry)}) + "\n")
        self._reset()
        self._pass(int(expiry))
        self.assertEqual(self._st("plan")["ran"], 1, "re-armed: the planner ran at the instant")
        self.assertEqual(self._st("plan")["stamped"], 1, "a complete run")
        self.assertIn(g1["id"], jd.load_goals(SID).get("confirming") or [], "at the instant the wait still holds")
        self.assertEqual(self._stamp("plan")[1], expiry, "the stamp keeps the expiry that equals now")
        self.assertEqual(self._stamp("close")[1], expiry)
        self._reset()
        self._pass(int(expiry) + 1)
        self.assertEqual((self._st("plan")["ran"], self._st("plan")["due_clock"]), (1, 1), "past it: run on the clock")
        self.assertEqual(jd.load_goals(SID)["status"].get(g1["id"]), "completed", "the released settle completes the top")
        self.assertIsNone(self._stamp("plan")[1])

    def test_the_expiry_helper_and_the_predicate_agree(self):
        self.assertEqual(em._bg_expiry_t({"deadline": 1000.0}), 1120.0)
        self.assertEqual(em._bg_expiry_t({"deadline": 1000.0, "deadlineSrc": "hook"}), 1005.0, "hook grace 5")
        self.assertIsNone(em._bg_expiry_t({"id": "x"}), "no deadline: never expires by the clock")
        for t in ({"deadline": 1000.0}, {"deadline": 1000.0, "deadlineSrc": "hook"}):
            x = em._bg_expiry_t(t)
            self.assertFalse(em._bg_expired(t, x), "at the instant: not expired")
            self.assertTrue(em._bg_expired(t, x + 0.001), "past it: expired")
        self.assertFalse(em._bg_expired({"id": "x"}, 1e12))

    def test_not_before_is_the_earliest_future_non_ghost_expiry(self):
        path, expiry = self._monitor_fixture()
        self.assertEqual(jd._settle_not_before(SID, str(path), expiry - 10), expiry)
        self.assertEqual(jd._settle_not_before(SID, str(path), expiry), expiry,
                         "at the instant the launch has not expired yet (em._bg_expired is strict), so it stays on the stamp")
        self.assertIsNone(jd._settle_not_before(SID, str(path), expiry + 1), "past it nothing lies ahead")
        reg = jd.STATE / "sdk" / (SID + ".json")
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text(json.dumps({"spawnedAt": T0 + 400}))            # a CLI spawned after the launch: a ghost
        self.assertIsNone(jd._settle_not_before(SID, str(path), expiry - 10),
                          "a ghost launch's expiry can change no verdict, so it arms no clock")


class DeathDrain(_Gate):
    def _dead(self):
        # a session outside the discover window with a pending death marker: run_close reaches it only
        # through the death drain
        path = self._session(SID)
        self._converge()
        later = int(time.time()) + 49 * 3600                            # the transcript falls out of the 48 h window
        jd._discover_cache.clear()                                      # (the list is cached behind a dir fingerprint)
        self.assertFalse([s for s in jd.discover(later) if s[0] == SID], "premise: not discovered")
        jd._discover_cache.clear()
        return path, later

    def test_a_pending_marker_finalizes_on_the_first_drain_run_and_the_sid_then_skips(self):
        path, later = self._dead()
        jd._write_death_marker(SID, {"t": T0 + 1000, "by": "probe"})
        self._reset()
        self._pass(later, tiers=("close",))
        self.assertEqual(self._st("close")["ran"], 1, "the drain's sid runs through the gate")
        m = json.loads((jd.GONEDIR / (SID + ".json")).read_text())
        self.assertIn("endedAt", m, "the settled dead store finalized its marker")
        self.assertIsNotNone(self._stamp("close"), "a complete drain run stamps")
        self._reset()
        self._pass(later + 1, tiers=("close",))
        self.assertEqual((self._st("close")["ran"], self._st("close")["skipped"]), (0, 0),
                         "a finalized marker leaves the drain: the sid is not listed at all")
        self.assertIsNone(self._stamp("close"), "...and its stamp is evicted with it")

    def test_a_marker_superseded_by_a_newer_states_row_retires(self):
        path, later = self._dead()
        jd._write_death_marker(SID, {"t": T0 + 1000, "by": "probe"})
        self._states_row(SID, T0 + 2000, "idle")                        # a revival's row, newer than the marker
        self._pass(later, tiers=("close",))
        m = json.loads((jd.GONEDIR / (SID + ".json")).read_text())
        self.assertTrue(m.get("superseded"))

    def test_a_cut_walk_leaves_the_marker_pending_and_the_sid_due(self):
        path, later = self._dead()
        self._append(path, uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))

        def dead_call(*a, **k):
            jd._judge_ctx.last_call_fail = {"note": "the model CLI died with no output (exit -14)",
                                            "model": "sonnet", "kill": True}
            return ""
        jd.closer_llm = dead_call
        self._pass()                                                    # the planner places task C; the closer's call dies
        self.assertEqual(self._st("close")["incomplete"], 1, "premise: the cut walk is incomplete while alive too")
        jd._write_death_marker(SID, {"t": T0 + 1000, "by": "probe"})
        self._reset()
        self._pass(later, tiers=("close",))
        self.assertEqual((self._st("close")["ran"], self._st("close")["incomplete"]), (1, 1))
        m = json.loads((jd.GONEDIR / (SID + ".json")).read_text())
        self.assertNotIn("endedAt", m, "a cut walk never finalizes the marker")
        self._reset()
        self._pass(later + 1, tiers=("close",))
        self.assertEqual(self._st("close")["ran"], 1, "still due: the cut run stamped nothing, so there is no stamp to match")


class Bounds(_Gate):
    def test_rebind_empties_the_stamps_and_eviction_follows_discover(self):
        self._session(SID)
        self._session(SID2, name="api")
        self._converge()
        self.assertEqual(len(jd._STAGE_STAMP), len(ALL_TIERS) * 2, "one stamp per gated tier per sid")
        (jd.NAMES / SID2).unlink()                                      # the session leaves discover
        jd._namefp_memo.clear()
        self._pass(tiers=ALL_TIERS)
        self.assertEqual({k for k in jd._STAGE_STAMP}, {(t, SID) for t in ALL_TIERS}, "the gone sid's stamps evicted")
        jd._rebind_state(self.td)
        self.assertEqual(jd._STAGE_STAMP, {}, "a new root is a new world")

    def test_the_cap_clears(self):
        self._session(SID)
        self._session(SID2, name="api")
        jd._STAGE_STAMP_MAX = 1
        self._pass()
        self.assertEqual(len(jd._STAGE_STAMP), 1, "a wholesale clear at the cap: one full walk next pass")


class FsCompleteness(_Gate):
    """The loud guard for a missing input: wrap the filesystem for one idle run of each stage over a
    two-session fixture (a task store, captions, episodes, a finalized death marker and an sdk reg present)
    and hold every path touched under the state root, the transcript directory and the task store against
    the tier's signature file set plus a fixed allowlist. A stage that starts reading a file the signature
    does not carry fails here."""

    ALLOW_NAMES = {"usage.json", "retry-paused.json", "judge-errors.jsonl", "session-flags.json"}

    def _touched(self, fn):
        seen = set()

        def note(p):
            if isinstance(p, (str, bytes, os.PathLike)):
                seen.add(os.path.abspath(os.fsdecode(p)))
        reals = {(os, "stat"): os.stat, (os, "lstat"): os.lstat, (os, "open"): os.open, (os, "scandir"): os.scandir,
                 (os, "listdir"): os.listdir, (builtins, "open"): builtins.open, (io, "open"): io.open}

        def wrap(real):
            def w(p, *a, **k):
                note(p)
                return real(p, *a, **k)
            return w
        for (mod, name), real in reals.items():
            setattr(mod, name, wrap(real))
        try:
            fn()
        finally:
            for (mod, name), real in reals.items():
                setattr(mod, name, real)
        return seen

    def _fixture(self):
        self._session(SID)
        self._session(SID2, name="api")
        jd.CAPDIR.mkdir(parents=True, exist_ok=True)
        (jd.CAPDIR / (SID + ".jsonl")).write_text(json.dumps({"id": "seg#p", "caption": "Ship the search"}) + "\n")
        jd.EPIDIR.mkdir(parents=True, exist_ok=True)
        (jd.EPIDIR / (SID + ".jsonl")).write_text(json.dumps({"head": "u1", "fsid": SID, "t": T0}) + "\n")
        jd._write_death_marker(SID2, {"t": T0 + 500, "by": "probe", "endedAt": T0 + 500})
        reg = jd.STATE / "sdk" / (SID + ".json"); reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text(json.dumps({"spawnedAt": T0 - 10}))
        d = self.claude / "tasks" / SID; d.mkdir()
        (d / "1.json").write_text(json.dumps({"id": "1", "subject": "write the api tests", "status": "pending"}))
        self._states_row(SID, T0 + 131, "idle")
        (jd.STATE / "cleared.jsonl").write_text("")
        (jd.STATE / "auto-nudge.json").write_text(json.dumps({"enabled": False, "deferred": {}}))
        self._converge()

    def _allowed(self, tier, sid, path):
        ident, value = jd._sig_inputs(tier, sid, str(path))
        allowed = {os.path.abspath(str(p)) for p in ident + value}
        if tier in jd.PARSE_TIERS:
            cands, states, key_files = jd._parse_key_files(sid, [str(path)])
            allowed |= {os.path.abspath(str(p)) for p in key_files + [states, jd.MESSAGES]}
        # the grouper, consolidator and distiller carry NO parse pair, so a transcript read on their idle
        # path is exactly what this test must catch: the transcript stays out of their allowed set
        allowed |= {os.path.abspath(str(jd.STATE / n)) for n in self.ALLOW_NAMES}
        return allowed

    def _check(self, tier, stage, prep=None):
        self._fixture()
        if prep is not None:
            prep()
            self._converge()
        for sid in (SID, SID2):
            path = self.pdir / (sid + ".jsonl")
            own = jd.begin_pass_frame()                                 # a fresh frame: the parse hits the filesystem
            try:
                touched = self._touched(lambda: stage(sid, str(path), NOW))
            finally:
                jd.end_pass_frame(own)
            allowed = self._allowed(tier, sid, path)
            roots = (str(jd.STATE), str(self.pdir), str(self.claude / "tasks"))
            scratch = (str(jd.JUDGE_SCRATCH), str(jd.NAMES), str(self.claude / "tasks" / Path(path).stem))
            stray = sorted(p for p in touched
                           if p.startswith(roots) and p not in allowed and not os.path.isdir(p)
                           and not p.startswith(scratch))
            self.assertEqual(stray, [], "%s read files its signature does not carry for %s" % (tier, sid))

    def test_the_planners_idle_reads_are_all_in_its_signature(self):
        self._check("plan", jd._plan_session)

    def test_the_closers_idle_reads_are_all_in_its_signature(self):
        self._check("close", jd._close_session)

    def test_the_unblockers_idle_reads_are_all_in_its_signature(self):
        # with a blocked candidate whose examine is current (the block postdates every ended turn), so the
        # run reaches the parse and stops at `due` empty: the parse and the store, nothing else
        self._check("unblock", jd._unblock_session,
                    prep=lambda: self._block(SID, self._tops()[0]["id"], T0 + 150))

    def test_the_couriers_idle_reads_are_all_in_its_signature(self):
        # the courier's idle scan: the pinned parse (the key files, the states file and the ledger the postal
        # index reads, allowed for every parse tier), the store trio and the episode log, nothing else
        self._check("courier", jd._courier_scan)

    def test_the_index_tiers_idle_reads_are_all_in_its_signature(self):
        # the index tier's idle path over a WARM unit cache (the fixture converged, so every session's cache is
        # current and the captioner's body takes the hit path): the pinned parse's key files, the captions file,
        # the archive record and the unit cache. The signature carries NO goal store (decision 7 of the round-4
        # plan), so the store is outside the allowed set and a store read on this path is exactly what this
        # test must catch
        self._check("index", lambda sid, path, now: (jd._index_caption_tasks(sid, path, sid, now),
                                                     jd._index_arch_task(sid)))
        for sid in (SID, SID2):
            self.assertEqual(json.loads((jd.PCACHE / (sid + ".json")).read_text())["key"],
                             json.loads(json.dumps(list(jd._frame_parse_key(sid, [str(self.pdir / (sid + ".jsonl"))])[0]))),
                             "the cache is warm under the live pair: the check ran the hit path")

    def test_the_groupers_idle_reads_are_all_in_its_signature(self):
        self._check("group", jd._group_session)

    def test_the_consolidators_idle_reads_are_all_in_its_signature(self):
        self._check("consolidate", jd._consolidate_session)

    def test_the_distillers_idle_reads_are_all_in_its_signature(self):
        # the distiller's idle run, as the review defines it: no untitled mirror top and an empty todo; a
        # transcript or peer-store read here would be a signature hole
        self._check("distill", jd._distill_session)


class StoreTiers(_Gate):
    """The four store-only tiers on the gate (P2): two idle passes run once, then skip with no store I/O."""

    def test_two_idle_passes_run_once_then_skip_with_no_store_io(self):
        self._session(SID)
        self._pass(tiers=("plan", "close"))                            # the planner mints two tops, the closer sweeps
        self._reset()
        self._pass(tiers=STORE_TIERS)
        self.assertEqual(self._st4("ran"), (1, 1, 1, 1), "first pass: every store tier runs")
        self.assertEqual(self._st4("stamped"), (1, 1, 1, 1), "each ran to completion")
        self.assertEqual(self._st4("skipped"), (0, 0, 0, 0))
        # the grouper and the consolidator each recorded their signature on first sight (groupedSig,
        # consolidatedSig: a store-level write, no relink): those publishes moved the store identity after
        # the unblocker's stamp and their own, and before the distiller's, which keyed on the final identity
        self._reset()
        self._pass(tiers=STORE_TIERS)
        self.assertEqual(self._st4("ran"), (1, 1, 1, 0), "the publishes re-armed the tiers stamped before them, once")
        self.assertEqual(self._st4("skipped"), (0, 0, 0, 1))
        self._reset()
        wm = [jd.pass_watermark(t, SID) for t in STORE_TIERS]
        io0 = jd.goal_io_stats()
        time.sleep(0.002)
        self._pass(tiers=STORE_TIERS)
        io1 = jd.goal_io_stats()
        self.assertEqual(self._st4("ran"), (0, 0, 0, 0), "the third pass skips every store tier")
        self.assertEqual(self._st4("skipped"), (1, 1, 1, 1))
        self.assertEqual((io1["loads"] - io0["loads"], io1["saves"] - io0["saves"]), (0, 0),
                         "a skipped session costs no store load and no save")
        for t, w in zip(STORE_TIERS, wm):
            self.assertGreater(jd.pass_watermark(t, SID), w, "%s: a skip stamps pass_done" % t)
        self.assertEqual(self.unblock_calls, [], "no blocked goal, no unblocker call")

    def test_counters_add_up_over_the_store_tiers(self):
        self._session(SID)
        self._converge()
        for t in STORE_TIERS:
            self.assertIsNotNone(self._stamp(t), t)
        stats = jd.tier_stats()
        for t in STORE_TIERS:
            s = stats[t]
            self.assertEqual(s["ran"], s["stamped"] + s["bypassed"] + s["incomplete"], t)
        self.assertGreaterEqual(stats["stamps"], 6, "one stamp per tier for the sid")


class StoreReArms(_Gate):
    """Each input re-arms exactly the store tiers that read it (the runs, in STORE_TIERS order)."""

    def _rearms(self, expect, msg):
        self._reset()
        self._pass(tiers=STORE_TIERS)
        self.assertEqual(self._st4("ran"), expect, msg)

    def test_a_store_publish_a_journal_append_and_an_archive_write_re_arm_all_four(self):
        self._session(SID)
        self._converge()
        store = jd.load_goals(SID)
        top = self._tops()[0]
        store["nodes"][top["id"]]["text"] = "Renamed by a kernel-side writer"
        jd.save_goals(SID, store)
        self._rearms((1, 1, 1, 1), "a save_goals publish (a rename: new identity)")
        self._converge()
        jd.append_override(SID, top["id"], "resolve", NOW + 1)           # the user's gesture: the journal only
        self._rearms((1, 1, 1, 1), "a journal append with no store write")
        self.assertEqual(jd.load_goals(SID)["status"].get(top["id"]), "completed", "the replayed resolve took")
        self._converge()
        jd.save_goal_archive(SID, {"rompUuid": SID, "nodes": {}, "status": {}})
        self._rearms((1, 1, 1, 1), "an archive write: in the grouper's and consolidator's signatures too "
                                   "(compaction rewrites it with no journal row)")

    def test_a_cleared_row_re_arms_the_grouper_and_consolidator_only(self):
        self._session(SID)
        self._converge()
        with open(jd.STATE / "cleared.jsonl", "a") as f:
            f.write(json.dumps({"id": SID2 + ":g1", "op": "clear", "t": NOW}) + "\n")
        self._rearms((0, 1, 1, 0), "a cleared.jsonl row (whole-file identity): the two tiers whose candidate "
                                   "forests read the view-cleared set")

    def test_a_transcript_append_re_arms_the_unblocker_only(self):
        path = self._session(SID)
        self._converge()
        self._append(path, uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))
        self._rearms((1, 0, 0, 0), "a transcript append: the parse pair is the unblocker's key and no one else's")
        self.assertEqual(self.unblock_calls, [], "no blocked goal: the re-armed run made no call")

    def test_a_states_row_re_arms_the_distiller_and_the_unblocker_not_the_grouper_or_consolidator(self):
        self._session(SID)
        self._converge()
        self._states_row(SID, T0 + 300, "picker")
        self._rearms((1, 0, 0, 1), "a states row entering picker: the distiller reads the states file, and the "
                                   "unblocker's parse key names it")

    def test_a_stall_record_for_this_sid_re_arms_the_distiller_and_another_sids_does_not(self):
        self._session(SID)
        self._converge()
        top = self._tops()[0]
        an = jd.STATE / "auto-nudge.json"
        an.write_text(json.dumps({"enabled": False, "deferred": {SID2 + ":g1": {"at": NOW, "why": "the closer has not settled the turn", "sid": SID2}}}))
        self._rearms((0, 0, 0, 0), "another sid's stall record")
        an.write_text(json.dumps({"enabled": False, "deferred": {top["id"]: {"at": NOW, "why": "the closer has not settled the turn", "sid": SID}}}))
        self._rearms((0, 0, 0, 1), "this sid's stall record: the staller owes the card a note")
        self.assertIsNotNone(jd.load_goals(SID)["nodes"][top["id"]].get("stallSummary"), "and wrote it")


class StoreOwnWrites(_Gate):
    """A tier's own publish re-arms it once (the stamp holds the pre-run identity); the follow-on run finds
    nothing to write and stamps; the third pass skips."""

    def test_the_unblockers_lift_re_arms_it_once_then_it_skips(self):
        path = self._session(SID)
        self._converge()
        top = self._tops()[0]
        self._block(SID, top["id"], T0 + 150)
        self._append(path, uline(T0 + 200, "the api binds 8080", "u3", "a2"), aline(T0 + 230, "noted", "a3", "u3"))
        jd.unblock_llm = lambda blocks, since, completed="": (self.unblock_calls.append(blocks) or LIFT_ONE)
        self._reset()
        self._pass(tiers=("unblock",))
        self.assertEqual(len(self.unblock_calls), 1, "one examine over the new turn")
        self.assertNotEqual(jd.load_goals(SID)["status"].get(top["id"]), "blocked", "the lift filed")
        self.assertEqual((self._st("unblock")["ran"], self._st("unblock")["stamped"]), (1, 1))
        self._reset()
        self._pass(tiers=("unblock",))
        self.assertEqual((self._st("unblock")["ran"], self._st("unblock")["stamped"]), (1, 1),
                         "the own publish re-armed it once; the follow-on run found nothing due")
        self.assertEqual(len(self.unblock_calls), 1, "and made no call")
        self._reset()
        self._pass(tiers=("unblock",))
        self.assertEqual((self._st("unblock")["ran"], self._st("unblock")["skipped"]), (0, 1))

    def test_a_titling_re_arms_the_distiller_once_and_the_third_pass_skips(self):
        # the review's cross-tier convergence probe: _title_mirror_tops titles a mirror top and the caller
        # saves, so the distiller's own publish re-arms it once; the follow-on run reads no transcript,
        # writes nothing and stamps; the third pass skips
        self._session(SID)
        self._converge()
        nid = self._mirror_top(SID, "add tests+docs for the search endpoint")
        parses = []
        real = self._saved_store[5]
        jd.parsed_session = lambda *a, **k: (parses.append(a[0]) or real(*a, **k))
        self._reset()
        self._pass(tiers=("distill",))
        self.assertEqual(self.title_calls, ["add tests+docs for the search endpoint"])
        nd = jd.load_goals(SID)["nodes"][nid]
        self.assertEqual((nd.get("text"), nd.get("declaredSubject")), ("Write the api tests", "add tests+docs for the search endpoint"))
        self.assertTrue(nd.get("titledT"))
        self.assertEqual((self._st("distill")["ran"], self._st("distill")["stamped"]), (1, 1), "the titling run completed")
        self._reset()
        io0 = jd.goal_io_stats()
        parses.clear()
        self._pass(tiers=("distill",))
        io1 = jd.goal_io_stats()
        self.assertEqual((self._st("distill")["ran"], self._st("distill")["stamped"]), (1, 1),
                         "the own publish re-armed it once; the follow-on run stamps")
        self.assertEqual(parses, [], "no transcript read on the idle path")
        self.assertEqual(io1["saves"] - io0["saves"], 0, "nothing written")
        self.assertEqual(len(self.title_calls), 1, "titled once, never re-derived")
        self._reset()
        self._pass(tiers=("distill",))
        self.assertEqual((self._st("distill")["ran"], self._st("distill")["skipped"]), (0, 1))


class StoreCompleteness(_Gate):
    """A store-tier run that did not finish leaves no stamp, so the sid stays due."""

    def _blocked_with_a_new_turn(self):
        path = self._session(SID)
        self._converge()
        top = self._tops()[0]
        self._block(SID, top["id"], T0 + 150)
        self._append(path, uline(T0 + 200, "the api binds 8080", "u3", "a2"), aline(T0 + 230, "noted", "a3", "u3"))
        return top

    def test_a_stripped_unblocker_reply_keeps_the_sid_due_without_a_strike(self):
        # patches _judge_run_impl, not unblock_llm: the helper strips its reply, so "   " reaches the stage as
        # "" and takes the no-write return (a truthy raw would take the parse-strike path instead)
        top = self._blocked_with_a_new_turn()
        jd.unblock_llm = self._saved_store[0]                            # the real helper, over the belt
        for reply in ("", "   "):
            jd._judge_run_impl = lambda *a, **k: reply
            self._reset()
            io0 = jd.goal_io_stats()
            self._pass(tiers=("unblock",))
            s = self._st("unblock")
            self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0), "reply %r" % reply)
            self.assertEqual(jd.goal_io_stats()["saves"] - io0["saves"], 0, "no save")
            self.assertFalse(jd.load_goals(SID).get("unblockFails"), "no strike burned on a failed call")
        jd._judge_run_impl = lambda *a, **k: LIFT_ONE
        self._reset()
        self._pass(tiers=("unblock",))
        self.assertEqual(self._st("unblock")["stamped"], 1, "a served reply completes the run")
        self.assertNotEqual(jd.load_goals(SID)["status"].get(top["id"]), "blocked")

    def test_a_stripped_grouper_or_consolidator_reply_keeps_the_sid_due_without_a_strike(self):
        self._session(SID)
        self._pass(tiers=("plan", "close"))                            # two open tops: the grouper has a menu
        store = jd.load_goals(SID)
        store.pop("groupedSig", None)                                    # the planner groups inline after each placement
        jd.save_goals(SID, store)                                        # and recorded the set already: re-open the gate
        jd.group_llm = self._saved[3]                                    # the real helper, over the belt
        for reply in ("", "   "):
            jd._judge_run_impl = lambda *a, **k: reply
            self._reset()
            io0 = jd.goal_io_stats()
            self._pass(tiers=("group",))
            s = self._st("group")
            self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0), "grouper, reply %r" % reply)
            self.assertEqual(jd.goal_io_stats()["saves"] - io0["saves"], 0, "no save")
            self.assertFalse(jd.load_goals(SID).get("groupFails"), "no strike")
        jd._judge_run_impl = lambda *a, **k: '{"ops":[]}'
        self._reset()
        self._pass(tiers=("group",))
        self.assertEqual(self._st("group")["stamped"], 1, "a served reply completes the run (groupedSig written)")
        # the consolidator: two COMPLETED tops (resolved, and the focus top's pending settle forced through:
        # a done verdict on the last node exports as confirming until the session settles, and the
        # consolidator's menu is the completed status alone), then the same probe over that menu
        for top in self._tops():
            jd.append_override(SID, top["id"], "resolve", NOW + 1)
        store = jd.load_goals(SID)
        for top in self._tops():
            store["status"][top["id"]] = "completed"
        store["confirming"] = []
        jd.save_goals(SID, store)
        self.assertEqual(len(jd._consolidate_tops(jd.load_goals(SID))), 2, "fixture: the consolidator has a menu")
        for reply in ("", "   "):
            jd._judge_run_impl = lambda *a, **k: reply
            self._reset()
            io0 = jd.goal_io_stats()
            self._pass(tiers=("consolidate",))
            s = self._st("consolidate")
            self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0), "consolidator, reply %r" % reply)
            self.assertEqual(jd.goal_io_stats()["saves"] - io0["saves"], 0, "no save")
            self.assertFalse(jd.load_goals(SID).get("consolidateFails"), "no strike")
        jd._judge_run_impl = lambda *a, **k: '{"ops":[]}'
        self._reset()
        self._pass(tiers=("consolidate",))
        self.assertEqual(self._st("consolidate")["stamped"], 1)

    def test_a_paused_title_call_keeps_the_distiller_due(self):
        self._session(SID)
        self._converge()
        nid = self._mirror_top(SID, "add tests+docs for the search endpoint")
        jd.mirror_title_llm = self._saved_store[4]                       # the real helper, over the belt

        def paused(*a, **k):
            jd._judge_ctx.paused = True                                  # what the real call does under retry-paused.json
            return ""
        jd._judge_run_impl = paused
        self._reset()
        io0 = jd.goal_io_stats()
        self._pass(tiers=("distill",))
        s = self._st("distill")
        self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0), "a pause-skipped titling leaves the sid due")
        self.assertEqual(jd.goal_io_stats()["saves"] - io0["saves"], 0)
        self.assertFalse(jd.load_goals(SID)["nodes"][nid].get("titledT"), "not stamped: the next pass retries")

        def served(*a, **k):
            jd._judge_ctx.paused = False
            return "Write the api tests"
        jd._judge_run_impl = served
        self._reset()
        self._pass(tiers=("distill",))
        self.assertEqual(self._st("distill")["stamped"], 1)
        self.assertEqual(jd.load_goals(SID)["nodes"][nid].get("text"), "Write the api tests")

    def test_a_paused_distill_call_keeps_the_sid_due_and_a_failed_one_writes_the_strike(self):
        self._session(SID)
        self._converge()
        top = self._tops()[0]
        jd.append_override(SID, top["id"], "resolve", NOW + 1)           # completed: a summary is owed

        def paused(*a, **k):
            jd._judge_ctx.paused = True
            return ""
        jd.distill_llm = paused
        self._reset()
        self._pass(tiers=("distill",))
        s = self._st("distill")
        self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0), "the paused continue marks the run")
        nd = jd.load_goals(SID)["nodes"][top["id"]]
        self.assertIsNone(nd.get("summary"))
        self.assertFalse(nd.get("distillFails"), "a pause-skip is not a strike")
        jd._judge_ctx.paused = False
        jd.distill_llm = lambda *a, **k: ""                              # a real failure, past the belt
        self._reset()
        self._pass(tiers=("distill",))
        self.assertEqual(jd.load_goals(SID)["nodes"][top["id"]].get("distillFails"), 1, "the strike is written")
        self.assertEqual(self._st("distill")["ran"], 1)
        self._reset()
        self._pass(tiers=("distill",))
        self.assertEqual(self._st("distill")["ran"], 1, "the strike's publish re-armed the tier by identity")
        self.assertEqual(jd.load_goals(SID)["nodes"][top["id"]].get("distillFails"), 2, "and it retried")
        jd.distill_llm = lambda *a, **k: "Shipped the search endpoint."
        self._reset()
        self._pass(tiers=("distill",))
        self.assertEqual(jd.load_goals(SID)["nodes"][top["id"]].get("summary"), "Shipped the search endpoint.")
        self._converge(tiers=("distill",))

    def test_a_store_read_fault_never_stamps(self):
        # Upstream #1019 (steer 1 of the 2026-09-08 fold) replaced the fork's fallback store: a goals file that
        # exists and cannot be READ raises out of load_goals, so every triage tier's run ends there. The pool
        # tiers raise through _gated, which counts the run incomplete, and their runner files the pass-crash
        # row; the courier's scan catches its own load, marks the run and files the same row with its "store"
        # note. No tier writes (the file is byte-identical), no tier stamps (the sid stays due), and the
        # boundary's store-unreadable row is not a triage pass's (load_goals_or_fault is the kernel's and the
        # index tier's miss path; the index skips here on its hit path). Readable again with nothing on disk
        # moved, every tier runs to completion and stamps. A read fault never moves the file, so the store is
        # touched once to re-arm the tiers; bytes that do not parse are the next test's case.
        self._session(SID)
        self._converge()
        gp = jd.GOALDIR / (SID + ".json")
        good = gp.read_bytes()
        st = gp.stat()
        os.utime(gp, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))   # re-arm: every triage signature carries the store
        with _store_read_fault(gp):
            for i in (1, 2):
                self._reset()
                self._pass(tiers=ALL_TIERS)
                for t in TRIAGE_TIERS:                                   # the index tier's signature carries no store:
                    s = self._st(t)                                      #  it skips (IndexGate holds its miss path)
                    self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0),
                                     "%s: a store that does not read ends the run incomplete, so the sid stays due" % t)
                self.assertEqual(self._st("index")["skipped"], 1, "the index reads no store on its hit path: it skips")
                crash = self._rows("pass-crash")
                self.assertEqual(len(crash), 7 * i, "one pass-crash row per triage tier per pass")
                self.assertEqual(sorted(r["judge"] for r in crash[-7:]), sorted(TRIAGE_JUDGES))
                self.assertTrue(all(r["fsid"] == SID and "Permission denied" in r["note"] for r in crash),
                                "every row names the session and the fault")
                self.assertTrue(all(r["note"].startswith("store: ") for r in crash if r["judge"] == "courier"),
                                "the courier's scan files the store note every pass wrapper uses")
        self.assertEqual(gp.read_bytes(), good, "no tier wrote")
        self.assertEqual(len(self._rows("store-unreadable")), 0, "the boundary row is not a triage pass's to file")
        self.assertEqual(len(self._rows("store-quarantined")), 0, "a read fault is never mistaken for bytes that do not parse")
        self._reset()                                                    # the fault lifted: nothing on disk moved
        self._pass(tiers=ALL_TIERS)
        self.assertEqual(tuple(self._st(t)["stamped"] for t in TRIAGE_TIERS), (1,) * len(TRIAGE_TIERS),
                         "readable again: every tier runs to completion and stamps")
        self.assertEqual(len(self._rows("pass-crash")), 14, "no row for a pass that read")

    def test_a_store_that_does_not_parse_is_quarantined_once_and_every_tier_stamps_on_the_fresh_store(self):
        # Bytes that do not parse are no longer a stand-down (upstream #1019, steer 1 of the 2026-09-08 fold;
        # the fork's fallback store held every tier back until the file read): load_goals moves the file aside
        # (one sidecar, one store-quarantined row, one stderr line) and answers the fresh store, every tier runs
        # to completion on it, and the planner re-mints and republishes, so the fixture converges as a fresh
        # session does. Bounded: the path reads as absent after the move, so the quarantine fires once, never
        # once per tier or per pass; no tier crashes and the boundary row is never filed.
        self._session(SID)
        self._converge()
        gp = jd.GOALDIR / (SID + ".json")
        gp.write_text("{ not the store")                                 # exists, and is not a store: re-arms every tier
        with contextlib.redirect_stderr(io.StringIO()):
            self._converge(tiers=ALL_TIERS)
        self.assertEqual(len(list(jd.GOALDIR.glob(SID + ".json.corrupt-*"))), 1, "the evidence is preserved aside, once")
        rows = self._rows("store-quarantined")
        self.assertEqual([r["fsid"] for r in rows], [SID], "one row, load_goals' own")
        self.assertIn("could not be parsed", rows[0]["note"])
        self.assertEqual(len(self._rows("pass-crash")), 0, "no tier stood down or crashed on the fresh store")
        self.assertEqual(len(self._rows("store-unreadable")), 0)
        self.assertTrue(gp.exists() and json.loads(gp.read_text())["nodes"], "the fresh store was judged and republished")
        self.assertTrue(all(self._stamp(t) is not None for t in ALL_TIERS), "every tier converged to a stamp on it")

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode-000 file")
    def test_an_unreadable_journal_never_stamps(self):
        self._session(SID)
        self._converge()
        top = self._tops()[0]
        jd.append_override(SID, top["id"], "resolve", NOW + 1)
        self._converge()
        jp = jd._overrides_dir() / (SID + ".jsonl")
        os.chmod(jp, 0)
        try:
            os.utime(jp, ns=(os.stat(jp).st_atime_ns, os.stat(jp).st_mtime_ns + 1_000_000_000))   # re-arm: chmod moves ctime only
            self._reset()
            self._pass(tiers=STORE_TIERS)
            self.assertEqual(self._st4("ran"), (1, 1, 1, 1))
            self.assertEqual(self._st4("incomplete"), (1, 1, 1, 1), "_replay_overrides' unreadable branch marks the run")
            self.assertEqual(self._st4("stamped"), (0, 0, 0, 0))
            rows = [json.loads(l) for l in open(jd.ERRORS) if l.strip()]
            self.assertTrue(any(r.get("err") == "history-unreadable" for r in rows), "the loud row stays per pass")
        finally:
            os.chmod(jp, 0o644)
        self._reset()
        self._pass(tiers=STORE_TIERS)
        self.assertEqual(self._st4("stamped"), (1, 1, 1, 1), "readable again: complete runs stamp")

    def _focus(self):
        store = jd.load_goals(SID)
        f = store.get("lastNode")
        while f and store["nodes"][f].get("parentId") is not None:
            f = store["nodes"][f]["parentId"]
        return store["nodes"][f]

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode-000 file")
    def test_an_unreadable_states_file_never_stamps(self):
        # the review's reproduction: the gate stats the states file into the distiller's signature, then the
        # stage's open fails. Before the fix the run answered "no live prompt", completed and stamped, and
        # the brief owed to the parked session waited until the file moved for an unrelated reason
        self._session(SID)
        self._converge()
        self._states_row(SID, T0 + 300, "picker")
        sp = jd.STATESDIR / (SID + ".jsonl")
        os.chmod(sp, 0)
        try:
            self._reset()
            self._pass(tiers=("distill",))
            s = self._st("distill")
            self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0),
                             "a states read that fails after a good stat marks the run incomplete")
            self.assertEqual(len(self._rows("states-unreadable")), 1, "one loud row")
            self._reset()
            self._pass(tiers=("distill",))
            self.assertEqual((self._st("distill")["ran"], self._st("distill")["incomplete"]), (1, 1), "still due")
            self.assertEqual(len(self._rows("states-unreadable")), 1, "one row per failure episode, not per pass")
        finally:
            os.chmod(sp, 0o644)
        self._reset()
        self._pass(tiers=("distill",))
        s = self._st("distill")
        self.assertEqual((s["ran"], s["stamped"]), (1, 1), "readable again, nothing on disk moved: the run happens and stamps")
        self.assertTrue(self._focus().get("blockSummary"), "the parked session's brief landed")

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode-000 file")
    def test_an_unreadable_cleared_file_never_stamps(self):
        self._session(SID)
        self._converge()
        cp = jd.STATE / "cleared.jsonl"
        with open(cp, "a") as f:                                         # a row: the grouper re-arms and reads it
            f.write(json.dumps({"id": SID2 + ":g1", "op": "clear", "t": NOW}) + "\n")
        os.chmod(cp, 0)
        try:
            self._reset()
            self._pass(tiers=("group",))
            s = self._st("group")
            self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0),
                             "a cleared.jsonl read that fails after a good stat marks the run incomplete")
            self.assertEqual(len(self._rows("cleared-unreadable")), 1)
        finally:
            os.chmod(cp, 0o644)
        self._reset()
        self._pass(tiers=("group",))
        self.assertEqual((self._st("group")["ran"], self._st("group")["stamped"]), (1, 1), "readable again: the run stamps")

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode-000 file")
    def test_an_unreadable_stall_file_never_stamps(self):
        # the by-value input: the signature's own read fails too, and an empty slice would EQUAL the last
        # good one whenever the records were empty, so the gate would skip a session over a file it cannot
        # see. The signature read is strict (raises), so the gate runs the stage without a stamp (bypassed);
        # the stage's own failed read marks the run; one row per failure episode either way
        self._session(SID)
        self._converge()
        an = jd.STATE / "auto-nudge.json"
        rec = {"enabled": False, "deferred": {SID + ":g999": {"why": "the build has not finished", "at": T0 + 10}}}
        an.write_text(json.dumps(rec))                 # a record for this sid moves the slice: the distiller is due
        os.chmod(an, 0)
        try:
            for _ in range(2):
                self._reset()
                self._pass(tiers=("distill",))
                s = self._st("distill")
                self.assertEqual((s["ran"], s["bypassed"], s["stamped"]), (1, 1, 0),
                                 "the stage ran (no skip over an unreadable input) and did not stamp")
                self.assertEqual(len(self._rows("stall-unreadable")), 1, "one row per failure episode, not per pass")
        finally:
            os.chmod(an, 0o644)
        self._reset()
        self._pass(tiers=("distill",))
        self.assertEqual((self._st("distill")["ran"], self._st("distill")["stamped"]), (1, 1), "readable again: the run stamps")
        an.write_text("{ not a document")              # exists, unparseable: the same shape, a new episode
        self._reset()
        self._pass(tiers=("distill",))
        s = self._st("distill")
        self.assertEqual((s["ran"], s["bypassed"], s["stamped"]), (1, 1, 0), "an unparseable file is not a real state")
        self.assertEqual(len(self._rows("stall-unreadable")), 2, "a new failure episode: a second row")
        an.write_text(json.dumps(rec))                 # the same records again: nothing the last complete run did not judge
        self._reset()
        self._pass(tiers=("distill",))
        self.assertEqual((self._st("distill")["ran"], self._st("distill")["skipped"]), (0, 1), "the stamp survived the episode")

    # ── the stage-site marks, one test per site, each forcing the early return past the _judge_run belt ──
    def test_the_unblockers_failed_call_site_marks_the_run(self):
        self._blocked_with_a_new_turn()
        jd.unblock_llm = lambda blocks, since, completed="": ""        # the helper, not the belt: the site alone marks
        self._reset()
        io0 = jd.goal_io_stats()
        self._pass(tiers=("unblock",))
        s = self._st("unblock")
        self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0))
        self.assertEqual(jd.goal_io_stats()["saves"] - io0["saves"], 0)

    def test_the_groupers_failed_call_site_marks_the_run(self):
        self._session(SID)
        self._pass(tiers=("plan", "close"))
        store = jd.load_goals(SID)
        store.pop("groupedSig", None)
        jd.save_goals(SID, store)
        jd.group_llm = lambda menu, judge="grouper": ""
        self._reset()
        io0 = jd.goal_io_stats()
        self._pass(tiers=("group",))
        s = self._st("group")
        self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0))
        self.assertEqual(jd.goal_io_stats()["saves"] - io0["saves"], 0)
        self.assertFalse(jd.load_goals(SID).get("groupFails"))

    def test_the_consolidators_failed_call_site_marks_the_run(self):
        self._session(SID)
        self._converge()
        store = jd.load_goals(SID)
        for top in self._tops():
            store["status"][top["id"]] = "completed"
        store["confirming"] = []
        jd.save_goals(SID, store)
        jd.group_llm = lambda menu, judge="grouper": ""
        self._reset()
        io0 = jd.goal_io_stats()
        self._pass(tiers=("consolidate",))
        s = self._st("consolidate")
        self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0))
        self.assertEqual(jd.goal_io_stats()["saves"] - io0["saves"], 0)
        self.assertFalse(jd.load_goals(SID).get("consolidateFails"))

    def test_the_titlers_paused_site_marks_the_run(self):
        self._session(SID)
        self._converge()
        nid = self._mirror_top(SID, "add tests+docs for the search endpoint")

        def paused_title(subject, frame=None, user_ask=None):
            jd._judge_ctx.paused = True
            return ""
        jd.mirror_title_llm = paused_title
        self._reset()
        io0 = jd.goal_io_stats()
        self._pass(tiers=("distill",))
        s = self._st("distill")
        self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0))
        self.assertEqual(jd.goal_io_stats()["saves"] - io0["saves"], 0)
        self.assertFalse(jd.load_goals(SID)["nodes"][nid].get("titledT"))

    def test_the_stallers_paused_site_marks_the_run(self):
        self._session(SID)
        self._converge()
        top = self._tops()[0]
        (jd.STATE / "auto-nudge.json").write_text(json.dumps(
            {"deferred": {top["id"]: {"why": "the build has not finished", "at": T0 + 100}}}))

        def paused_stall(text, work, holding):
            jd._judge_ctx.paused = True
            return ""
        jd.stall_llm = paused_stall
        self._reset()
        io0 = jd.goal_io_stats()
        self._pass(tiers=("distill",))
        s = self._st("distill")
        self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0))
        self.assertEqual(jd.goal_io_stats()["saves"] - io0["saves"], 0)
        self.assertIsNone(jd.load_goals(SID)["nodes"][top["id"]].get("stallSummary"))

    def test_the_briefers_paused_shortfall_retry_marks_the_run(self):
        self._session(SID)
        self._converge()
        top = self._tops()[0]
        store = jd.load_goals(SID)
        kid = "%s:g%d" % (SID, 91)                                        # a sub-goal: two blocked nodes make owed a list
        store["nodes"][kid] = {"id": kid, "text": "pick the test database", "parentId": top["id"], "t": T0 + 120,
                               "mt": T0 + 120, "log": [], "trail": [], "nodeComplete": False, "cleared": False}
        store["status"][kid] = "working"
        jd.save_goals(SID, store)
        self._block(SID, top["id"], T0 + 150, why="Which port should the api bind?")
        self._block(SID, kid, T0 + 160, why="Which database should the tests use?")
        calls = []

        def brief(text, work, owed, frame=None, user_ask=None, shortfall=None):
            calls.append(shortfall)
            if shortfall:                                                # the retry is skipped under the pause
                jd._judge_ctx.paused = True
                return ""
            return "One paragraph for two owed decisions."
        jd.brief_llm = brief
        self._reset()
        self._pass(tiers=("distill",))
        s = self._st("distill")
        self.assertEqual(calls, [None, (1, 2)], "two owed decisions, one paragraph: the corrective retry ran")
        self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0))
        self.assertIsNone(jd.load_goals(SID)["nodes"][top["id"]].get("blockSummary"), "the brief is still owed")


class UnblockerHazard(_Gate):
    def test_a_turn_ending_after_the_first_touch_is_judged_next_pass_by_the_unblocker(self):
        # the review's hazard, on the unblocker: a tick job touches the session while its last turn is OPEN
        # and a top is blocked; the turn's final record and the idle row land; the gated unblocker runs and
        # finds nothing due under the pinned parse. Its stamp must hold the PRE-append pair, so the next
        # pass runs it over the ended turn and the lift files. Without P1a's key pin this test fails.
        path = self._session(SID)
        self._converge(tiers=("plan", "close"))
        top = self._tops()[0]
        self._block(SID, top["id"], T0 + 150)                            # after both ended turns
        self._append(path, uline(T0 + 200, "use port 8080 for the api", "u3", "a2"),
                     aline(T0 + 210, "starting on it", "a3", "u3", stop="tool_use"))
        jd.unblock_llm = lambda blocks, since, completed="": (self.unblock_calls.append(since) or LIFT_ONE)
        own = jd.begin_pass_frame()
        try:
            jd.parsed_session(SID, [str(path)], NOW)                     # the tick job's first touch, turn open
            pre = jd._frame["keys"][("parse", SID)]
            self._append(path, aline(T0 + 240, "bound to 8080", "a4", "a3"))
            self._states_row(SID, T0 + 241, "idle")
            jd.run_unblock(now=NOW)
        finally:
            jd.end_pass_frame(own)
        self.assertEqual(self.unblock_calls, [], "under the pinned parse the turn is open: nothing due, no call")
        st = self._stamp("unblock")
        self.assertIsNotNone(st, "the run completed and stamped")
        self.assertEqual(st[0][0][1], jd._pair_key(pre), "the stamp holds the PRE-append pair")
        self._reset()
        self._pass(tiers=("unblock",))
        self.assertEqual(self._st("unblock")["ran"], 1, "the live pair differs from the stamped one: the tier runs")
        self.assertEqual(len(self.unblock_calls), 1, "and examines the ended turn")
        self.assertIn("bound to 8080", self.unblock_calls[0])
        self.assertNotEqual(jd.load_goals(SID)["status"].get(top["id"]), "blocked", "the lift filed")


class DrainStaysUngated(_Gate):
    def test_the_drain_distills_an_absent_stuck_store_regardless_of_stamps(self):
        # a store no discovered session owns (no transcript for SID2) holding a completed top with a null
        # summary: _drain_undiscovered reaches it on every distill pass; it never holds a stamp to skip on
        self._session(SID)
        self._converge()
        nid = SID2 + ":g1"
        store = jd.load_goals(SID2)
        store["nodes"][nid] = {"id": nid, "text": "Ship the search", "parentId": None, "nodeComplete": True,
                               "cleared": False, "t": T0, "mt": T0 + 60, "trail": [],
                               "log": [{"kind": "done", "ev_t": T0 + 60, "at": T0 + 60, "src": "closer", "why": "landed"}]}
        store["status"][nid] = "completed"
        jd.save_goals(SID2, store)
        self._reset()
        self._pass(tiers=("distill",))
        self.assertEqual(jd.load_goals(SID2)["nodes"][nid].get("summary"), "",
                         "no transcript, no work: the sentinel, written by the ungated drain")
        self.assertIsNone(self._stamp("distill", SID2), "the drain leaves no stamp")
        self.assertEqual(self._st("distill")["ran"], 0, "the discovered sid skipped; the drain is not a gated run")


class CourierGate(_Gate):
    """The courier's per-session scan on the gate (J6, 2026-09-07). The invariant: the gate never withholds a
    courier action the ungated pass would have taken from new evidence. A scan is skipped only when the
    pinned parse pair, the store trio and the episode log are identical to the last scan that completed
    with no pending row and no backref; a scan that produced rows, reached another session's store, stood
    down on a fallback store or raised leaves no stamp, so the session is scanned again next pass."""

    def _ran(self, tier="courier"):
        s = self._st(tier)
        return (s["ran"], s["skipped"], s["stamped"], s["incomplete"])

    def test_two_idle_passes_scan_once_then_skip_with_no_store_io(self):
        self._session(SID)
        self._session(SID2, name="api")
        seen = self._scan_log()
        self._pass(tiers=("courier",))
        self.assertEqual(sorted(seen), sorted([SID, SID2]), "first pass: every discovered session is scanned")
        self.assertEqual(self._ran(), (2, 0, 2, 0), "two complete scans, both stamped")
        self.assertIsNotNone(self._stamp("courier", SID))
        self.assertIsNotNone(self._stamp("courier", SID2))
        wm = jd.pass_watermark("courier", SID)
        self.assertIsNotNone(wm, "a completed scan stamps pass_done")
        seen.clear()
        segs = []
        real_segs = self._saved_store[8]
        jd._segs = lambda turn, store: (segs.append(1) or real_segs(turn, store))
        self._reset()
        io0 = jd.goal_io_stats()
        time.sleep(0.002)
        self._pass(tiers=("courier",))
        io1 = jd.goal_io_stats()
        self.assertEqual(seen, [], "second pass: no scan")
        self.assertEqual(segs, [], "no segment walk")
        self.assertEqual(self._ran(), (0, 2, 0, 0))
        self.assertEqual((io1["loads"] - io0["loads"], io1["saves"] - io0["saves"]), (0, 0),
                         "a skipped session costs no store load and no save")
        self.assertGreater(jd.pass_watermark("courier", SID), wm, "a skip stamps pass_done too")
        self.assertEqual(self.courier_calls, [], "no peer mail, no model call, in either pass")

    def test_each_input_re_arms_the_courier_for_its_sid_only(self):
        path = self._session(SID)
        self._session(SID2, name="api")
        self._converge()                                                # every tier, so the planner's tops exist
        seen = self._scan_log()

        def rearms(expect, msg="the follow-on pass: nothing new, both skip"):
            seen.clear()
            self._reset()
            self._pass(tiers=("courier",))
            self.assertEqual(seen, expect, msg)
            self.assertEqual(self._st("courier")["skipped"], 2 - len(expect), msg)
        self._append(path, uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))
        rearms([SID], "a transcript append (the parse pair)")
        rearms([], "nothing new: the re-armed scan wrote nothing and stamped")
        self._states_row(SID, T0 + 300, "idle")
        rearms([SID], "a states row (in the parse key)")
        rearms([])
        store = jd.load_goals(SID)
        top = self._tops()[0]
        store["nodes"][top["id"]]["text"] = "Renamed by a kernel-side writer"
        jd.save_goals(SID, store)
        rearms([SID], "a save_goals publish (a rename: new identity)")
        rearms([])
        jd.append_override(SID, top["id"], "resolve", NOW + 1)          # the user's gesture: the journal only
        rearms([SID], "a journal append with no store write")
        rearms([])
        jd.save_goal_archive(SID, {"rompUuid": SID, "nodes": {}, "status": {}})
        rearms([SID], "an archive write")
        rearms([])
        jd.EPIDIR.mkdir(parents=True, exist_ok=True)
        with open(jd.EPIDIR / (SID + ".jsonl"), "a") as f:
            f.write(json.dumps({"head": "u1", "fsid": SID, "t": T0}) + "\n")
        rearms([SID], "an episodes row (episode_floor is the courier's pre-episode guard)")
        rearms([])
        # not courier inputs: captions, cleared.jsonl, the sdk reg, a stall record, the ledger alone
        jd.CAPDIR.mkdir(parents=True, exist_ok=True)
        with open(jd.CAPDIR / (SID + ".jsonl"), "a") as f:
            f.write(json.dumps({"id": "seg-x#p", "caption": "Ship the notes-api search"}) + "\n")
        rearms([], "a captions append re-arms nothing")
        with open(jd.STATE / "cleared.jsonl", "a") as f:
            f.write(json.dumps({"id": SID2 + ":g1", "op": "clear", "t": NOW}) + "\n")
        rearms([], "a cleared.jsonl row re-arms nothing")
        reg = jd.STATE / "sdk" / (SID + ".json")
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text(json.dumps({"spawnedAt": T0 + 600}))
        rearms([], "an sdk reg appearing re-arms nothing (the scan reads only peer authors)")
        (jd.STATE / "auto-nudge.json").write_text(json.dumps(
            {"enabled": False, "deferred": {top["id"]: {"at": NOW, "why": "waiting on the closer", "sid": SID}}}))
        rearms([], "a stall record re-arms nothing (the courier rolls up only at its write sites)")
        self._ledger_row(MID2, SID2, SID, t=NOW)
        rearms([], "a ledger row alone re-arms nothing: the sent row precedes the transcript atom that carries it")

    def test_a_session_with_a_pending_row_is_scanned_every_pass_and_never_stamped(self):
        # Exercised for the contract, not because it occurs live: the state copy the round was measured on
        # holds zero sessions with an unfiled peer row (they are filed on the pass that finds them). A row the
        # write loop could not consume (an empty courier reply: the account is usage-limited) keeps the session
        # due; once a reply files it, the store's own move re-arms the scan once more, and then it skips.
        path = self._peer_session(SID, SID2)
        seg_id = self._peer_seg_id(SID, path)
        jd.courier_llm = lambda text, menu, declared="": (self.courier_calls.append(text) or "")
        seen = self._scan_log()
        for i in range(3):
            seen.clear()
            self._reset()
            self._pass(tiers=("courier",))
            self.assertIn(SID, seen, "pass %d: the session with a row is scanned" % i)
            self.assertEqual(self._st("courier")["incomplete"], 1, "pass %d: the row marks the run incomplete" % i)
            self.assertIsNone(self._stamp("courier", SID), "pass %d: never stamped" % i)
        store = jd.load_goals(SID)
        self.assertNotIn(seg_id, store["placements"], "an empty reply never places the segment")
        self.assertIn(seg_id, store.get("courierDeferred") or {}, "the deferral is recorded (once, a write)")
        self.assertEqual(len(self.courier_calls), 3, "one call per pass: the row is retried every pass")
        self.assertIsNotNone(self._stamp("courier", SID2), "the sender, with no row, stamped on its first scan")
        jd.courier_llm = lambda text, menu, declared="": (self.courier_calls.append(text) or DELEGATE_REPLY)
        seen.clear()
        self._reset()
        self._pass(tiers=("courier",))
        store = jd.load_goals(SID)
        self.assertEqual(store["placements"].get(seg_id), "fyi", "filed quiet: no link to root a recipient top on")
        self.assertNotIn(seg_id, store.get("courierDeferred") or {}, "a landed reply clears the deferral")
        trackers = [nd for nd in jd.load_goals(SID2)["nodes"].values()
                    if isinstance(nd.get("handoff"), dict) and nd["handoff"].get("msgId") == MID]
        self.assertEqual(len(trackers), 1, "the sender's tracking node planted")
        self.assertIsNone(self._stamp("courier", SID), "the filing pass produced the row: no stamp yet")
        seen.clear()
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual(sorted(seen), sorted([SID, SID2]), "both stores moved: both re-armed once")
        self.assertEqual(self._ran(), (2, 0, 2, 0), "the placed segment scans clean: both stamp")
        seen.clear()
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual((seen, self._st("courier")["skipped"]), ([], 2), "then both skip")
        self.assertEqual(len(self.courier_calls), 4)

    def _placed_delegate(self, sender_discovered=True, from_host=""):
        """A recipient whose peer delegate segment was PLACED by another writer under a node with no courier
        link (the link-repair shape). Returns (seg_id, nid)."""
        recs = list(TWO_TURNS) + [self._peer_line(T0 + 200, "p1", MID, parent="a2"), aline(T0 + 230, "On it.", "a3", "p1")]
        extra = {"from_host": from_host} if from_host else {}
        self._ledger_row(MID, SID2, SID, t=T0 + 190, **extra)
        path = self._session(SID, recs)
        if sender_discovered:
            self._session(SID2, name="api")
        seg_id = self._peer_seg_id(SID, path)
        store = jd.load_goals(SID)
        nid = SID + ":g7"
        store["nodes"][nid] = {"id": nid, "text": "Wire up the export button", "parentId": None, "t": T0 + 200,
                               "mt": T0 + 200, "log": [], "trail": [], "nodeComplete": False, "cleared": False}
        store["status"][nid] = "working"
        store["placements"][seg_id] = nid
        jd.save_goals(SID, store)
        return seg_id, nid

    def _tracker(self, complete):
        snd = jd.load_goals(SID2)
        tid = SID2 + ":g1"
        snd["nodes"][tid] = {"id": tid, "text": "delegated to web: wire up the export button", "parentId": None,
                             "t": T0 + 190, "mt": T0 + 190, "log": [], "trail": [], "nodeComplete": complete,
                             "cleared": False, "handoff": {"peer": SID, "msgId": MID}}
        snd["status"][tid] = "completed" if complete else "working"
        jd.save_goals(SID2, snd)
        return tid

    def test_a_placed_delegate_with_no_sender_tracker_stamps_after_one_scan(self):
        # the review's nit (2026-09-07): the repair found no tracker in any discovered store, and nothing can
        # plant one later for a placed local segment (the two planters plant for unplaced rows and for remote
        # recipients), so marking the run kept the session hot forever at N+1 store loads per pass. It stamps.
        seg_id, nid = self._placed_delegate()
        seen = self._scan_log()
        self._pass(tiers=("courier",))
        self.assertEqual(sorted(seen), sorted([SID, SID2]))
        self.assertEqual(self._ran(), (2, 0, 2, 0), "no tracker anywhere: the scan is complete and stamps")
        self.assertNotIn("links", jd.load_goals(SID)["nodes"][nid])
        self.assertEqual(self.courier_calls, [], "a placed segment is never re-judged")
        seen.clear()
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual((seen, self._st("courier")["skipped"]), ([], 2), "and skips")

    def test_a_completed_sender_tracker_keeps_the_scan_due_until_a_reopen_links_it(self):
        # the one shape in which a later pass can attach the link with none of this session's inputs moving:
        # the sender's tracker exists and is complete (never linked); a user reopening it moves the SENDER's
        # store, so the recipient's run stays incomplete until the reopened tracker is linked
        seg_id, nid = self._placed_delegate()
        tid = self._tracker(complete=True)
        seen = self._scan_log()
        for i in range(2):
            seen.clear()
            self._reset()
            self._pass(tiers=("courier",))
            self.assertIn(SID, seen, "pass %d: scanned" % i)
            self.assertIsNone(self._stamp("courier", SID), "pass %d: a completed tracker keeps the run incomplete" % i)
            self.assertNotIn("links", jd.load_goals(SID)["nodes"][nid], "a completed tracker is never linked")
        self.assertIsNotNone(self._stamp("courier", SID2), "the sender, with nothing pending, stamped")
        snd = jd.load_goals(SID2)                                        # the user reopens the tracker
        self.assertTrue(jd.record_verdict(snd, snd["nodes"][tid], "user", "reopen", NOW + 1, why="reopened by the user"))
        jd.rollup_status(snd, False)
        jd.save_goals(SID2, snd)
        self.assertFalse(jd.load_goals(SID2)["nodes"][tid].get("nodeComplete"), "premise: the tracker is open again")
        seen.clear()
        self._reset()
        self._pass(tiers=("courier",))
        self.assertIn(SID, seen, "still due: the reopened tracker is found")
        links = jd.load_goals(SID)["nodes"][nid].get("links") or []
        self.assertEqual(links, [{"peer": SID2, "goalId": tid, "msgId": MID}], "the link attached")
        self.assertIsNotNone(self._stamp("courier", SID), "the attaching run is complete (its save re-arms it once)")
        seen.clear()
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual(seen, [SID], "the link's save moved the recipient's store: one more scan (the sender's "
                                      "reopen save preceded the linking pass, so its scan there already stamped it)")
        self.assertEqual(self._ran(), (1, 1, 1, 0), "the link is in the store: the repair stops before the lookup")
        seen.clear()
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual((seen, self._st("courier")["skipped"]), ([], 2), "then both skip")

    def test_a_local_sender_outside_the_discover_window_keeps_the_scan_due_and_a_remote_one_does_not(self):
        # no tracker is visible because the sender's store was not READ (the sender is a local session outside
        # the discover window): its return makes an open tracker visible with nothing of the recipient's moving,
        # so the run stays incomplete; once the sender is discovered and holds no tracker, the scan stamps.
        # A sender on another kernel (the ledger row's from_host) keeps its tracker there: stamp at once.
        seg_id, nid = self._placed_delegate(sender_discovered=False)
        seen = self._scan_log()
        for i in range(2):
            seen.clear()
            self._reset()
            self._pass(tiers=("courier",))
            self.assertEqual(seen, [SID], "pass %d: the recipient is scanned" % i)
            self.assertEqual(self._ran(), (1, 0, 0, 1), "pass %d: a local sender outside the window: incomplete" % i)
        self._session(SID2, name="api")                                  # the sender returns, with no tracker
        seen.clear()
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual(sorted(seen), sorted([SID, SID2]))
        self.assertEqual(self._ran(), (2, 0, 2, 0), "discovered and trackerless: nothing can appear later, both stamp")
        # the remote sender, from a clean root
        jd._rebind_state(self.td); jd._STAGE_STAMP.clear()
        for c in (jd._PARSE_CACHE, jd._discover_cache):
            c.clear()
        shutil.rmtree(jd.GOALDIR, ignore_errors=True); shutil.rmtree(jd.NAMES, ignore_errors=True)
        jd.NAMES.mkdir(parents=True)
        jd.MESSAGES.unlink()
        seg_id, nid = self._placed_delegate(sender_discovered=False, from_host="TESTHOST-B")
        seen.clear()
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual(seen, [SID])
        self.assertEqual(self._ran(), (1, 0, 1, 0), "a remote sender's tracker is never local: stamp")

    def test_the_settle_is_read_once_per_written_session_and_never_on_the_idle_path(self):
        # two peer rows in one session, both filed without a model call (a declared coordinate and a declared
        # question file fyi): _session_settled runs once for that session, from the store being written, and
        # every rollup at the write sites gets that value; the idle sender is never settled at all
        recs = list(TWO_TURNS) + [self._peer_line(T0 + 200, "p1", MID, kind="coordinate", body="COORDINATE: the api is on 8080", parent="a2"),
                                  aline(T0 + 230, "Noted.", "a3", "p1"),
                                  self._peer_line(T0 + 300, "p2", MID2, kind="question", body="QUESTION: which port do the tests use?", parent="a3"),
                                  aline(T0 + 330, "The tests use 8081.", "a4", "p2")]
        self._ledger_row(MID, SID2, SID, kind="coordinate", t=T0 + 190)
        self._ledger_row(MID2, SID2, SID, kind="question", t=T0 + 290)
        self._session(SID, recs)
        self._session(SID2, name="api")
        settled, rolled = [], []
        real_settled, real_rollup = self._saved_store[9], self._saved_store[10]

        def ss(fsid, path, session, store, now=None):
            v = real_settled(fsid, path, session, store, now)
            settled.append((fsid, v))
            return v

        def ru(store, session_closed, now=None):
            rolled.append((store.get("rompUuid"), session_closed))
            return real_rollup(store, session_closed, now=now)
        jd._session_settled, jd.rollup_status = ss, ru
        self._pass(tiers=("courier",))
        store = jd.load_goals(SID)
        peer_segs = [k for k, v in store["placements"].items() if v == "fyi"]
        self.assertEqual(len(peer_segs), 2, "both declared non-delegations filed fyi with no model call")
        self.assertEqual(self.courier_calls, [])
        self.assertEqual([f for f, v in settled], [SID], "settled once, for the written session only")
        value = settled[0][1]
        self.assertTrue(value, "premise: the turn ended and nothing is awaited, so the session is settled")
        writes = [v for sid, v in rolled if sid == SID]
        self.assertEqual(writes, [value, value], "each write site's rollup got the one settled value")
        self.assertEqual(self._ran(), (2, 0, 1, 1), "the sender stamped; the written session produced rows")

    def test_the_settle_guard_logs_and_the_write_still_lands_when_the_parse_raises(self):
        # outside a frame (romp-judge --courier, tests) the settle's parse can raise on a transcript that moved
        # and no longer parses; the guard logs a pass-crash row and reads not-settled, and the write loop goes
        # on. Under the pass frame the settle's parse is the pinned one, so the guard never fires there.
        path = self._peer_session(SID, SID2, kind="coordinate")
        seg_id = self._peer_seg_id(SID, path)
        real = self._saved_store[5]
        calls = []

        def second_call_raises(fsid, files, now):
            calls.append(fsid)
            if fsid == SID and calls.count(SID) == 2:
                raise RuntimeError("the transcript moved under the write loop")
            return real(fsid, files, now)
        jd.parsed_session = second_call_raises
        jd._discover_cache.clear()
        jd.run_courier(now=NOW)                                         # no frame: the settle parses on its own
        self.assertEqual(jd.load_goals(SID)["placements"].get(seg_id), "fyi", "the write landed with settled=False")
        rows = [json.loads(l) for l in open(jd.ERRORS) if l.strip()]
        notes = [r.get("note") or "" for r in rows if r.get("err") == "pass-crash" and r.get("fsid") == SID]
        self.assertEqual(len(notes), 1, rows)
        self.assertTrue(notes[0].startswith("settle: "), notes[0])

    def test_a_peer_message_landing_after_the_first_touch_is_filed_next_pass(self):
        # the frame hazard, on the courier: a tick job touches the session while nothing is pending; the
        # peer message and the agent's reply land mid-pass; the gated courier judges the pinned (pre-append)
        # world and stamps THAT pair, so the next pass runs the scan over the new turn and files the row.
        # A stamp stat'd at the courier's own moment would record the post-append pair and skip the message
        # until an unrelated write. Without P1a's key pin this test fails.
        path = self._session(SID)
        self._session(SID2, name="api")
        self._converge(tiers=("courier",))
        jd.save_goal_archive(SID, {"rompUuid": SID, "nodes": {}, "status": {}})   # re-arm: the run below is a run
        own = jd.begin_pass_frame()
        try:
            jd.parsed_session(SID, [str(path)], NOW)                    # the tick job's first touch
            pre = jd._frame["keys"][("parse", SID)]
            self._ledger_row(MID, SID2, SID, t=T0 + 190)
            self._append(path, self._peer_line(T0 + 200, "p1", MID, parent="a2"), aline(T0 + 230, "On it.", "a3", "p1"))
            jd.run_courier(now=NOW)
        finally:
            jd.end_pass_frame(own)
        self.assertEqual(self.courier_calls, [], "under the pinned parse there is no peer segment: nothing filed")
        self.assertEqual((self._st("courier")["ran"], self._st("courier")["stamped"]), (1, 1), "a run, complete")
        st = self._stamp("courier", SID)
        self.assertIsNotNone(st, "the run completed and stamped")
        self.assertEqual(st[0][0][1], jd._pair_key(pre), "the stamp holds the PRE-append pair")
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual(self._st("courier")["ran"], 1, "the live pair differs from the stamped one: the scan runs")
        self.assertEqual(len(self.courier_calls), 1, "and the message is judged")
        self.assertIn("wire up the export button", self.courier_calls[0])
        seg_id = self._peer_seg_id(SID, path)
        self.assertEqual(jd.load_goals(SID)["placements"].get(seg_id), "fyi", "filed (quiet: no rooted link)")

    def test_a_cut_arming_between_the_pin_and_the_parse_withholds_the_couriers_stamp(self):
        path = self._session(SID)
        self._converge(tiers=("courier",))
        self._append(path, uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))
        before = self._stamp("courier")
        own = jd.begin_pass_frame()
        try:
            jd._frame_parse_key(SID, [str(path)])                        # the pin, under no cut
            jd._PENDING_CUT_FN = lambda fsid: "a2"                       # a bare rollback arms before the parse
            jd.run_courier(now=NOW)
        finally:
            jd.end_pass_frame(own)
        s = self._st("courier")
        self.assertEqual((s["ran"], s["bypassed"], s["stamped"]), (1, 1, 0), "served under another cut: no stamp")
        self.assertEqual(self._stamp("courier"), before, "the old stamp stands")
        jd._PENDING_CUT_FN = None
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual(self._st("courier")["stamped"], 1, "pin and parse under one cut: a stamp")

    def test_a_late_ledger_row_is_filed_once_the_transcript_moves(self):
        # the ledger is not in the signature (the sent row precedes the transcript atom, so the atom's append
        # re-arms the scan with the row already in place). The residual: a marker whose row the ledger lacks
        # when the parse ran is sender-less (author.peer None), which the scan skips and the planner places as
        # plain work in the same pass. Here only the courier runs, so the segment stays unplaced: the row
        # appended alone changes nothing the pinned parse saw (the ungated courier served the same cached
        # parse), and the agent's reply, the transcript's own next append, re-parses with the row in the
        # index and files the message. No pass files anything the ungated pass would have filed.
        recs = list(TWO_TURNS) + [self._peer_line(T0 + 200, "p1", MID, parent="a2")]
        path = self._session(SID, recs)                                 # no ledger row yet
        self._session(SID2, name="api")
        seen = self._scan_log()
        self._pass(tiers=("courier",))
        self.assertEqual(self.courier_calls, [], "sender-less: not the courier's to file")
        self.assertIsNotNone(self._stamp("courier", SID), "a complete scan with no row stamps")
        self._ledger_row(MID, SID2, SID, t=T0 + 190)                    # the row lands late, alone
        seen.clear()
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual((seen, self._st("courier")["skipped"]), ([], 2), "nothing in the signature moved")
        self._append(path, aline(T0 + 230, "On it.", "a3", "p1"))        # the agent replies: the pair moves
        seen.clear()
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual(seen, [SID])
        self.assertEqual(len(self.courier_calls), 1, "re-parsed with the row in the index: filed")
        seg_id = self._peer_seg_id(SID, path)
        self.assertEqual(jd.load_goals(SID)["placements"].get(seg_id), "fyi")

    def test_a_crashed_scan_logs_a_scan_row_stamps_nothing_and_the_pass_goes_on(self):
        # a parse that raises, then a segment walk that raises: each is caught per session as a pass-crash row
        # labelled "scan:", the run counts incomplete with no stamp, the other session is still scanned and
        # stamped, and run_courier returns (before the gate a _segs crash aborted the triage pass at the courier)
        self._session(SID)
        self._session(SID2, name="api")
        real = self._saved_store[5]

        def poisoned(fsid, files, now):
            if fsid == SID:
                raise ValueError("not a transcript")
            return real(fsid, files, now)
        jd.parsed_session = poisoned
        self._pass(tiers=("courier",))
        self.assertEqual(self._ran(), (2, 0, 1, 1), "the crash counts incomplete; the other session stamped")
        self.assertIsNone(self._stamp("courier", SID))
        self.assertIsNotNone(self._stamp("courier", SID2))
        rows = [json.loads(l) for l in open(jd.ERRORS) if l.strip()]
        notes = [r["note"] for r in rows if r.get("err") == "pass-crash" and r.get("fsid") == SID]
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0].startswith("scan: ValueError"), notes[0])
        jd.parsed_session = real
        real_segs = self._saved_store[8]

        def walk_crashes(turn, store):
            if store.get("rompUuid") == SID:
                raise RuntimeError("a seam without a segment")
            return real_segs(turn, store)
        jd._segs = walk_crashes
        self._reset()
        self._pass(tiers=("courier",))                                  # returns: the crash is per session
        self.assertEqual(self._ran(), (1, 1, 0, 1), "the walk crash: incomplete, no stamp; the other sid skipped")
        rows = [json.loads(l) for l in open(jd.ERRORS) if l.strip()]
        notes = [r["note"] for r in rows if r.get("err") == "pass-crash" and r.get("fsid") == SID]
        self.assertEqual(len(notes), 2)
        self.assertTrue(notes[1].startswith("scan: RuntimeError"), notes[1])
        jd._segs = real_segs
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual(self._ran(), (1, 1, 1, 0), "healed: the crashed sid runs and stamps")

    def _ledger_reads(self, fn):
        """Run fn counting the opens of the ledger file (Path.read_text and the event model's incremental
        reader both open it); returns the count."""
        n, target = [0], os.path.abspath(str(jd.MESSAGES))
        reals = {(builtins, "open"): builtins.open, (io, "open"): io.open}
        # Python 3.10: Path.open calls pathlib._NormalAccessor.open, a class attribute bound to io.open when
        # pathlib was imported, so a patched io.open never sees Path.read_text (3.11 removed the accessor and
        # Path.open calls io.open directly). Patch that slot too, as a staticmethod so the path stays the
        # first argument, the way the unbound builtin behaved.
        acc = getattr(pathlib, "_NormalAccessor", None)
        if acc is not None:
            reals[(acc, "open")] = acc.open

        def wrap(real):
            def w(p, *a, **k):
                if isinstance(p, (str, bytes, os.PathLike)) and os.path.abspath(os.fsdecode(p)) == target:
                    n[0] += 1
                return real(p, *a, **k)
            return w
        for (mod, name), real in reals.items():
            setattr(mod, name, staticmethod(wrap(real)) if isinstance(mod, type) else wrap(real))
        try:
            fn()
        finally:
            for (mod, name), real in reals.items():
                setattr(mod, name, real)
        return n[0]

    def _trackers(self, sid):
        return [nd for nd in jd.load_goals(sid)["nodes"].values() if isinstance(nd.get("handoff"), dict)]

    def test_the_ledger_is_parsed_once_per_version_for_the_cross_host_plant(self):
        # the xrows arm reads its candidate rows from the postal memo (_postal_ledger): across two passes with
        # an unchanged ledger the file is opened once (by the first pass), the plant is idempotent, and the
        # memo slot is the same object; an appended row refills it once and plants once
        self._session(SID)
        self._session(SID2, name="api")
        self._converge(tiers=("courier",))
        self._ledger_row("px-1.mail.TESTHOST-A", SID, "peer:TESTHOST-B", t=NOW - 100, toName="TESTHOST-B:web",
                         body="DELEGATE: run the exporter on the far box")
        jd._postal_from_memo[0] = (None, {})                            # what five suites do: a stale, 2-slot reset
        reads = self._ledger_reads(lambda: self._pass(tiers=("courier",)))
        self.assertGreaterEqual(reads, 1, "the first pass parses the ledger once for the memo")
        self.assertEqual(len(self._trackers(SID)), 1, "the cross-host delegate planted the sender's tracker")
        ent = jd._postal_from_memo[0]
        self.assertEqual(len(ent[1][1]), 1, "one candidate row in the memo")
        reads = self._ledger_reads(lambda: self._pass(tiers=("courier",)))
        self.assertEqual(reads, 0, "an unchanged ledger is not opened again")
        self.assertIs(jd._postal_from_memo[0], ent, "the memo slot is the same object")
        self.assertEqual(len(self._trackers(SID)), 1, "idempotent by msgId")
        self._ledger_row("px-2.mail.TESTHOST-A", SID, "peer:TESTHOST-B", t=NOW - 50, toName="TESTHOST-B:web",
                         body="DELEGATE: and the importer")
        reads = self._ledger_reads(lambda: self._pass(tiers=("courier",)))
        self.assertEqual(reads, 1, "an appended row: one refill")
        self.assertEqual(len(self._trackers(SID)), 2, "and the new row planted")

    def test_the_sender_and_horizon_filters_run_per_pass_on_the_memoized_rows(self):
        # the memo holds the ledger's rows under the ledger's identity; who is discovered and what is inside
        # the retry horizon are this pass's questions. A candidate whose sender is not discovered at pass 1
        # and past the horizon at pass 2 plants at neither, and plants at pass 3 when both hold, with the
        # memo never refilled between them (no clock predicate is frozen in it)
        self._session(SID)
        self._ledger_row("px-3.mail.TESTHOST-A", SID2, "peer:TESTHOST-B", t=NOW - jd.COURIER_RETRY_HORIZON + 50,
                         toName="TESTHOST-B:web", body="DELEGATE: run the exporter on the far box")
        self._pass(tiers=("courier",))                                  # SID2 not discovered: no plant
        ent = jd._postal_from_memo[0]
        self.assertEqual(len(ent[1][1]), 1, "the row is a candidate in the memo")
        self.assertEqual(self._trackers(SID2), [], "its sender is not among this pass's discovered sessions")
        self._session(SID2, name="api")                                 # now discovered
        self._pass(now=NOW + 100, tiers=("courier",))                   # but the row is past the horizon at this now
        self.assertEqual(self._trackers(SID2), [], "past the horizon at the pass's now: never backfilled")
        self.assertIs(jd._postal_from_memo[0], ent, "the memo did not refill: the filters ran on its rows")
        self._pass(now=NOW, tiers=("courier",))                         # within the horizon again, sender discovered
        self.assertEqual(len(self._trackers(SID2)), 1, "both filters hold: planted")
        self.assertIs(jd._postal_from_memo[0], ent)

    def test_a_link_repair_that_raises_marks_the_run_and_the_pass_goes_on(self):
        # the placed branch's own guard: a repair that raises is logged as before ("link-attach: ...") and, so
        # the repair is retried rather than skipped over, marks the run incomplete; the other session stamps
        path = self._peer_session(SID, SID2)
        seg_id = self._peer_seg_id(SID, path)
        store = jd.load_goals(SID)
        nid = SID + ":g7"
        store["nodes"][nid] = {"id": nid, "text": "Wire up the export button", "parentId": None, "t": T0 + 200,
                               "mt": T0 + 200, "log": [], "trail": [], "nodeComplete": False, "cleared": False}
        store["status"][nid] = "working"
        store["placements"][seg_id] = nid
        jd.save_goals(SID, store)
        real = jd._seg_peer_kind

        def kind_crashes(seg):
            if jd._seg_peer(seg):
                raise RuntimeError("a marker the kind reader cannot parse")
            return real(seg)
        jd._seg_peer_kind = kind_crashes
        try:
            self._pass(tiers=("courier",))
        finally:
            jd._seg_peer_kind = real
        self.assertEqual(self._ran(), (2, 0, 1, 1), "the crashed repair: incomplete; the sender stamped")
        self.assertIsNone(self._stamp("courier", SID))
        rows = [json.loads(l) for l in open(jd.ERRORS) if l.strip()]
        notes = [r["note"] for r in rows if r.get("err") == "pass-crash" and r.get("fsid") == SID]
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0].startswith("link-attach: RuntimeError"), notes[0])

    def test_a_placed_row_whose_t_drifted_is_placed_for_the_scan_too(self):
        # the review's nit 3: the write loop dedups a placed row drift-safely (_placed_key), but the scan's
        # placed check was exact-key, so a row whose parse t drifted after its placement was returned every
        # pass, marked the run incomplete every pass, and was then deduped by the write loop: the gate was
        # defeated for that session forever. The scan now asks the same helper: no row, a complete run, a stamp.
        path = self._peer_session(SID, SID2)
        seg_id = self._peer_seg_id(SID, path)
        parts = seg_id.split(":")
        drifted = ":".join(parts[:-2] + [str(int(parts[-2]) + 7), parts[-1]])   # the same segment, its t moved
        self.assertNotEqual(drifted, seg_id)
        store = jd.load_goals(SID)
        store["placements"][drifted] = "fyi"                            # as the courier filed it, under the old t
        jd.save_goals(SID, store)
        self.assertTrue(jd._placed_key(store["placements"], seg_id), "premise: the write loop would dedup it")
        self.assertNotIn(seg_id, store["placements"], "premise: the exact check misses it")
        seen = self._scan_log()
        self._pass(tiers=("courier",))
        self.assertEqual(sorted(seen), sorted([SID, SID2]))
        self.assertEqual(self.courier_calls, [], "no row returned, no call")
        self.assertEqual(self._ran(), (2, 0, 2, 0), "the scan is complete and stamps")
        seen.clear()
        self._reset()
        self._pass(tiers=("courier",))
        self.assertEqual((seen, self._st("courier")["skipped"]), ([], 2), "and skips")

    def test_counters_add_up_over_the_courier(self):
        path = self._peer_session(SID, SID2)
        self._pass(tiers=("courier",))
        self._append(path, uline(T0 + 400, "task D", "u4", "a3"), aline(T0 + 430, "did D", "a4", "u4"))
        self._pass(tiers=("courier",))
        self._pass(tiers=("courier",))
        s = self._st("courier")
        self.assertEqual(s["ran"], s["stamped"] + s["bypassed"] + s["incomplete"])
        self.assertGreater(s["skipped"], 0)
        ts = jd.tier_stats()
        self.assertIn("courier", ts)
        self.assertEqual(set(ts), set(jd.GATED_TIERS) | {"stamps"})


class IndexReaders(_Gate):
    """The index tier's readers are strict about files that EXIST (J7, 2026-09-07; the round-3 and round-4
    reviews' recurring finding). Absent stays a real state (no caption rows, no archive record, a unit-cache
    miss) and marks nothing; a failure on a file that exists reads as that same empty answer for the call,
    marks the running stage incomplete and logs one judge-errors row per failure episode, so the gate never
    stamps a decision made without an input its signature says the stage saw. Before, every one of these
    readers swallowed the failure as the empty answer and nothing recorded it."""

    def _tasks(self, path, now=NOW):
        return jd.tasks_for(SID, str(path), [str(path)], now)

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode-000 file")
    def test_the_caption_readers_read_absent_as_empty_and_an_unreadable_file_marks_and_logs_once(self):
        self.assertEqual((jd.captioned_ids(SID), jd._live_natoms(SID), jd.session_turn_captions(SID)), (set(), {}, []))
        self.assertFalse(jd._judge_ctx.stage_incomplete, "absent is a state, not a failure")
        self.assertEqual(self._rows("captions-unreadable"), [])
        jd.append_caption(SID, "seg1", "segment", T0 + 30, "Did A")
        jd.append_caption(SID, "t1", "turn", T0 + 30, "Did A")
        jd.append_caption(SID, "seg2", "segment", T0 + 200, "Working on B", live=True, natoms=9)
        with open(jd.CAPDIR / (SID + ".jsonl"), "a") as f:
            f.write("{ not a row\n")                                    # content, not a read failure
        self.assertEqual(jd.captioned_ids(SID), {"seg1", "t1"}, "live rows are not done; a bad line is skipped")
        self.assertEqual(jd._live_natoms(SID), {"seg2": 9})
        self.assertEqual(jd.session_turn_captions(SID), ["Did A"])
        self.assertFalse(jd._judge_ctx.stage_incomplete)
        rows = jd._caption_rows(SID)
        self.assertEqual((jd.captioned_ids(SID, rows), jd._live_natoms(SID, rows)), ({"seg1", "t1"}, {"seg2": 9}),
                         "the captioner's one read per session derives both answers from the same rows")
        cp = jd.CAPDIR / (SID + ".jsonl")
        os.chmod(cp, 0)
        try:
            for fn, empty in ((jd.captioned_ids, set()), (jd._live_natoms, {}), (jd.session_turn_captions, [])):
                jd._judge_ctx.stage_incomplete = False
                self.assertEqual(fn(SID), empty, fn.__name__)
                self.assertTrue(jd._judge_ctx.stage_incomplete,
                                "%s: a read that fails on a file that exists marks the stage" % fn.__name__)
            self.assertEqual(len(self._rows("captions-unreadable")), 1, "one row per failure episode, not per read")
            self.assertEqual(self._rows("captions-unreadable")[0]["fsid"], SID)
            self.assertIsNone(jd._caption_rows(SID), "the row reader answers None for a failed read (the bodies stand down on it)")
        finally:
            os.chmod(cp, 0o644)
        self.assertEqual(jd._caption_rows(SID2), [], "and [] for an absent file")
        jd._judge_ctx.stage_incomplete = False
        self.assertEqual(jd.captioned_ids(SID), {"seg1", "t1"}, "readable again")
        self.assertFalse(jd._judge_ctx.stage_incomplete)
        os.chmod(cp, 0)
        try:
            jd.session_turn_captions(SID)
            self.assertEqual(len(self._rows("captions-unreadable")), 2, "a good read ended the episode: the next failure logs again")
        finally:
            os.chmod(cp, 0o644)

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode-000 file")
    def test_the_archive_reader_reads_absent_as_none_and_a_bad_file_marks_and_logs_once(self):
        self.assertIsNone(jd.load_archive(SID))
        self.assertFalse(jd._judge_ctx.stage_incomplete, "absent is a state")
        jd.write_archive(SID, {"headline": "Ship the search", "abstract": "Built it.", "turns": 2})
        self.assertEqual(jd.load_archive(SID)["turns"], 2)
        ap = jd.ARCHDIR / (SID + ".json")
        self.assertEqual(jd._read_archive(SID2), (None, False), "absent: no record, no failure")
        os.chmod(ap, 0)
        try:
            jd._judge_ctx.stage_incomplete = False
            self.assertIsNone(jd.load_archive(SID))
            self.assertTrue(jd._judge_ctx.stage_incomplete, "a read that fails on a file that exists marks the stage")
            self.assertEqual(jd._read_archive(SID), (None, True), "the archiver's twin says the file failed")
            jd.load_archive(SID)
            self.assertEqual(len(self._rows("session-archive-unreadable")), 1, "one row per failure episode")
        finally:
            os.chmod(ap, 0o644)
        jd._judge_ctx.stage_incomplete = False
        self.assertEqual(jd.load_archive(SID)["turns"], 2, "readable again")
        self.assertFalse(jd._judge_ctx.stage_incomplete)
        # a file that READS but is not a record is content, not a read failure (review should-fix): the
        # answer is an absent record's, so the archiver rebuilds it; the row is still written, once per
        # episode, and the stage is not marked (it decided with the input)
        ap.write_text("[1, 2]")                                          # decodes, but is not a record
        self.assertEqual(jd._read_archive(SID), (None, False))
        self.assertIsNone(jd.load_archive(SID))
        self.assertFalse(jd._judge_ctx.stage_incomplete, "content: the stage is not marked")
        self.assertEqual(len(self._rows("session-archive-unreadable")), 2, "but the corruption is logged once")
        ap.write_text("{ not json")
        self.assertEqual(jd._read_archive(SID), (None, False))
        self.assertEqual(len(self._rows("session-archive-unreadable")), 2, "the same episode: no second row")
        self.assertEqual(self._rows("archive-unreadable"), [], "the goals archive's row name is not borrowed")

    def test_the_unit_cache_read_is_strict_and_a_stale_or_absent_cache_is_a_plain_miss(self):
        path = self._session(SID)
        tasks = self._tasks(path)
        self.assertTrue(tasks, "two ended turns: caption tasks")
        cf = jd.PCACHE / (SID + ".json")
        self.assertTrue(cf.exists(), "the miss path published the cache")
        self.assertFalse(jd._judge_ctx.stage_incomplete)
        cf.write_text("{ not the cache")                                 # exists, does not decode
        jd._judge_ctx.stage_incomplete = False
        self.assertEqual(self._tasks(path), tasks, "the miss path regenerated the same tasks")
        self.assertTrue(jd._judge_ctx.stage_incomplete, "a cache that exists and does not read marks the stage")
        self.assertEqual(len(self._rows("units-cache-unreadable")), 1)
        self.assertEqual(json.loads(cf.read_text())["tasks"], tasks, "and the publish repaired the file")
        jd._judge_ctx.stage_incomplete = False
        self.assertEqual(self._tasks(path), tasks)                       # the hit
        self.assertFalse(jd._judge_ctx.stage_incomplete, "a good read marks nothing")
        cf.write_text(json.dumps({"key": [[["stale", 1]], ""], "v": 6, "tasks": []}))   # the current version (v6, T252d): only the key is stale
        self.assertEqual(self._tasks(path), tasks, "a stale key is a plain miss")
        self.assertFalse(jd._judge_ctx.stage_incomplete)
        cf.unlink()
        self.assertEqual(self._tasks(path), tasks, "an absent cache is a plain miss")
        self.assertFalse(jd._judge_ctx.stage_incomplete)
        self.assertEqual(len(self._rows("units-cache-unreadable")), 1, "neither miss is a failure")

    def test_a_failed_unit_cache_publish_keeps_the_tasks_marks_the_run_and_logs_once_per_episode(self):
        path = self._session(SID)
        jd.PCACHE.parent.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(jd.PCACHE, ignore_errors=True)
        jd.PCACHE.write_text("")                                         # a file where the cache dir goes: mkdir fails
        jd._judge_ctx.stage_incomplete = False
        tasks = self._tasks(path)
        self.assertTrue(tasks, "the decision stands for this pass")
        self.assertTrue(jd._judge_ctx.stage_incomplete, "but the next pass cannot read it back: the run is incomplete")
        self.assertEqual(len(self._rows("units-cache-write-failed")), 1)
        self.assertEqual(self._rows("units-cache-unreadable"), [], "a cache under a path that is not a directory is absent")
        self._tasks(path)
        self.assertEqual(len(self._rows("units-cache-write-failed")), 1, "one row per failure episode, not per pass")
        jd.PCACHE.unlink()
        jd._judge_ctx.stage_incomplete = False
        self.assertEqual(self._tasks(path), tasks)
        self.assertFalse(jd._judge_ctx.stage_incomplete, "the publish landed")
        self.assertTrue((jd.PCACHE / (SID + ".json")).exists())
        shutil.rmtree(jd.PCACHE)
        jd.PCACHE.write_text("")
        self._tasks(path)
        self.assertEqual(len(self._rows("units-cache-write-failed")), 2, "a good publish ended the episode: the next failure logs again")

    def test_a_store_read_fault_stands_the_captioner_down_and_memoizes_nothing(self):
        # the seams _ready_tasks applies are the store's: a task list built without the store is not the
        # session's (a seamed turn's first segment would be captioned as the whole turn), so tasks_for reads it
        # through load_goals_or_fault (upstream #1019, steer 1 of the 2026-09-08 fold; before it the fork's
        # fallback store stood the stage down) and on a fault stands down: no tasks, the run marked incomplete,
        # no cache published (so the next pass reads the store again rather than serving a list made without it
        # until the transcript moves), and the boundary's one store-unreadable row per fault episode. Bytes that
        # do not parse are not a fault: load_goals quarantines them and the tasks are built on the fresh store.
        path = self._session(SID)
        gp = jd.GOALDIR / (SID + ".json")
        gp.parent.mkdir(parents=True, exist_ok=True)
        gp.write_text(_fresh_store_text(SID))                            # exists and parses: only the read faults
        with _store_read_fault(gp):
            jd._judge_ctx.stage_incomplete = False
            self.assertEqual(self._tasks(path), [], "no task list without the store")
            self.assertTrue(jd._judge_ctx.stage_incomplete, "the boundary's fault marked the stage")
            self.assertFalse((jd.PCACHE / (SID + ".json")).exists(), "nothing memoized")
            self.assertEqual(len(self._rows("store-unreadable")), 1)
            jd._judge_ctx.stage_incomplete = False
            self.assertEqual(self._tasks(path), [], "still faulting: still stood down")
            self.assertTrue(jd._judge_ctx.stage_incomplete)
            self.assertEqual(len(self._rows("store-unreadable")), 1, "one row per fault episode, not per call")
        jd._judge_ctx.stage_incomplete = False
        self.assertTrue(self._tasks(path), "the store reads again: the tasks are built and published")
        self.assertFalse(jd._judge_ctx.stage_incomplete)
        self.assertTrue((jd.PCACHE / (SID + ".json")).exists())
        self.assertEqual(len(self._rows("store-unreadable")), 1, "the episode ended on the read")
        (jd.PCACHE / (SID + ".json")).unlink()                           # a miss: the store is read again
        gp.write_text("{ not the store")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(self._tasks(path), "bytes that do not parse: quarantined, the tasks built on the fresh store")
        self.assertFalse(jd._judge_ctx.stage_incomplete, "a quarantine is not a stand-down")
        self.assertFalse(gp.exists())
        self.assertEqual(len(self._rows("store-quarantined")), 1)
        self.assertTrue((jd.PCACHE / (SID + ".json")).exists(), "the fresh store's task list is the session's: published")


class IndexGate(_Gate):
    """The index tier (the captioner and archiver) on the gate (J7 of the round-4 plan, 2026-09-07). The
    invariant: the gate never withholds a caption or an archive write the ungated pass would have made from
    new evidence. A session is skipped only when its pinned parse pair, captions file, archive record and
    unit cache are identical to the last run that found no work and voided no read; a session with a
    caption owed or an archive refresh due, a reader that failed on a file that exists, a failed cache
    publish, a store read fault on the miss path or a crash in a body leaves no stamp and runs again next
    pass. The signature carries no goal store (decision 7): the hit path reads none."""

    TURN_C = (uline(T0 + 200, "task C", "u3", "a2"), aline(T0 + 230, "did C", "a3", "u3"))

    def _ran(self):
        s = self._st("index")
        return (s["ran"], s["skipped"], s["stamped"], s["incomplete"])

    def _body_log(self):
        """Wrap the two per-session bodies to record the sids they ran for; returns (caption_sids, arch_sids)."""
        real_c, real_a = self._saved_index[3], self._saved_index[4]
        seen_c, seen_a = [], []

        def c(fsid, path, anchor, now):
            seen_c.append(fsid)
            return real_c(fsid, path, anchor, now)

        def a(fsid):
            seen_a.append(fsid)
            return real_a(fsid)
        jd._index_caption_tasks, jd._index_arch_task = c, a
        return seen_c, seen_a

    def _rearm_hit(self, sid):
        """Move the session's unit cache identity without changing its content: the next pass runs the
        session on its hit path and finds no work."""
        cf = jd.PCACHE / (sid + ".json")
        time.sleep(0.002)
        cf.write_text(cf.read_text())

    def _captioned(self, text):
        return any(text in c for c in self.caption_calls)

    def test_two_idle_passes_run_once_then_skip_with_no_reads(self):
        self._session(SID)
        self._session(SID2, name="api")
        seen_c, seen_a = self._body_log()
        self._pass(tiers=("index",))
        self.assertEqual((sorted(seen_c), sorted(seen_a)), (sorted([SID, SID2]),) * 2, "first pass: both bodies over every session")
        self.assertEqual(self._ran(), (2, 0, 0, 2), "the working pass: captions and an archive to write, so no stamp")
        n_caps = len(self.caption_calls)
        self.assertGreater(n_caps, 0)
        self.assertEqual(len(self.archive_calls), 2)
        self.assertTrue(jd.captioned_ids(SID))
        self.assertEqual(jd.load_archive(SID)["turns"], 2)
        self._reset()
        seen_c.clear(); seen_a.clear()
        self._pass(tiers=("index",))                                    # the follow-on: the cache publish re-armed each once
        self.assertEqual(self._ran(), (2, 0, 2, 0), "the follow-on run finds no work and stamps")
        self.assertEqual((len(self.caption_calls), len(self.archive_calls)), (n_caps, 2), "no model call")
        wm = jd.pass_watermark("index", SID)
        self.assertIsNotNone(wm, "a completed run stamps pass_done")
        self._reset()
        seen_c.clear(); seen_a.clear()
        io0 = jd.goal_io_stats()
        time.sleep(0.002)
        self._pass(tiers=("index",))                                    # the skip
        io1 = jd.goal_io_stats()
        self.assertEqual((seen_c, seen_a), ([], []), "third pass: neither body runs")
        self.assertEqual(self._ran(), (0, 2, 0, 0))
        self.assertEqual((io1["loads"] - io0["loads"], io1["saves"] - io0["saves"]), (0, 0),
                         "a skipped session costs no store load and no save")
        self.assertGreater(jd.pass_watermark("index", SID), wm, "a skip stamps pass_done too")
        self.assertEqual((len(self.caption_calls), len(self.archive_calls)), (n_caps, 2))

    def test_each_input_re_arms_the_index_for_its_sid_only_and_a_store_publish_does_not(self):
        path = self._session(SID)
        self._session(SID2, name="api")
        self._converge(tiers=("index",))
        seen_c, _ = self._body_log()
        # (a) a transcript append moves the pair: the new turn is captioned and the archive refreshed
        self._append(path, *self.TURN_C)
        n0, a0 = len(self.caption_calls), len(self.archive_calls)
        self._pass(tiers=("index",))
        self.assertEqual(seen_c, [SID], "the changed session ran; the other skipped")
        self.assertEqual(self._ran(), (1, 1, 0, 1), "work found: no stamp yet")
        self.assertTrue(self._captioned("did C"), "the new turn's caption was not withheld")
        self.assertEqual(len(self.archive_calls), a0 + 1)
        self.assertEqual(jd.load_archive(SID)["turns"], 3)
        self._converge(tiers=("index",))
        seen_c.clear()
        # (b) a caption row appended by another writer (a tombstone): one run, no work, a stamp
        jd.append_caption(SID, "orphan", "segment", T0 + 999, "")
        self._pass(tiers=("index",))
        self.assertEqual((seen_c, self._ran()), ([SID], (1, 1, 1, 0)))
        seen_c.clear()
        # (c) the archive record rewritten with a stale turn count: the run refreshes it, as the ungated pass would
        rec = jd.load_archive(SID)
        rec["turns"] = 1
        jd.write_archive(SID, rec)
        a1 = len(self.archive_calls)
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual((seen_c, self._ran()), ([SID], (1, 1, 0, 1)))
        self.assertEqual((len(self.archive_calls), jd.load_archive(SID)["turns"]), (a1 + 1, 3))
        self._converge(tiers=("index",))
        seen_c.clear()
        # (d) the unit cache rewritten (same content, a new identity): one run on the hit path, a stamp
        self._rearm_hit(SID)
        self._pass(tiers=("index",))
        self.assertEqual((seen_c, self._ran()), ([SID], (1, 1, 1, 0)))
        seen_c.clear()
        # (e) a states row moves the pair (the states file is in the fileset key): a miss, no new work
        self._states_row(SID, T0 + 300, "idle")
        n1 = len(self.caption_calls)
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(seen_c, [SID])
        self.assertEqual((self._st("index")["ran"], len(self.caption_calls)), (1, n1))
        self._converge(tiers=("index",))
        seen_c.clear()
        # (f) a store publish and a journal row re-arm NOTHING (decision 7): the hit path reads no store
        self._mirror_top(SID, "Write the api tests")
        jd.append_override(SID, SID + ":g90", "resolve", NOW + 1)
        time.sleep(0.002)
        self._pass(tiers=("index",))
        self.assertEqual(seen_c, [], "a store publish and a journal row re-arm nothing: the index reads no store on its hit path")
        self.assertEqual(self._ran(), (0, 2, 0, 0))

    def test_a_session_with_a_caption_owed_runs_every_pass_and_never_stamps_until_it_lands(self):
        path = self._session(SID)
        self._converge(tiers=("index",))
        self._append(path, *self.TURN_C)

        def paused(text, judge="gister"):                                # a pause skip: not a verdict, no strike
            jd._judge_ctx.paused = True
            return ""
        jd.caption_llm = jd.gist_llm = paused
        before = self._stamp("index")
        for _ in range(2):
            self._reset()
            self._pass(tiers=("index",))
            self.assertEqual(self._ran(), (1, 0, 0, 1), "a caption owed: the session runs and never stamps")
            self.assertEqual(self._stamp("index"), before, "the converged stamp stands (it no longer matches); no new one")
        self.assertFalse((jd.CAPDIR / (SID + ".fails.json")).exists(), "a pause skip is not a strike")
        jd.caption_llm, jd.gist_llm = self._saved_index[0], self._saved_index[1]
        jd.caption_llm = lambda text: (self.caption_calls.append(text) or "Wired the export button.")
        jd.gist_llm = lambda text, judge="gister": (self.caption_calls.append(text) or "Wire the export button")
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 0, 1), "the captions land: work this pass")
        self.assertTrue(self._captioned("did C"))
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 1, 0), "nothing owed: stamped")

    def test_the_caption_and_archive_caps_leave_a_deferred_session_due(self):
        # the caps take their share AFTER a session is counted as having work: a session whose task or
        # refresh was not selected this pass is never stamped, so the next pass offers it again
        self._session(SID)
        self._session(SID2, name="api")
        own = jd.begin_pass_frame()
        try:
            jd.run_index(now=NOW, budget=0)
        finally:
            jd.end_pass_frame(own)
        self.assertEqual(self.caption_calls, [], "a zero budget: nothing selected")
        self.assertEqual(self._ran(), (2, 0, 0, 2), "work found, none done: both stay due")
        jd.ARCH_BUDGET = 0
        self._reset()
        self._pass(tiers=("index",))
        self.assertGreater(len(self.caption_calls), 0, "the captions land")
        self.assertEqual(self.archive_calls, [], "the archive cap dropped both refreshes")
        self.assertEqual(self._ran(), (2, 0, 0, 2), "archives due but capped: no stamp")
        jd.ARCH_BUDGET = None
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(len(self.archive_calls), 2, "the deferred archives are written, not withheld")
        self.assertEqual(self._ran(), (2, 0, 0, 2))
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (2, 0, 2, 0))

    def test_a_crashed_caption_call_keeps_the_sid_due_without_a_strike(self):
        path = self._session(SID)
        self._converge(tiers=("index",))
        self._append(path, *self.TURN_C)

        def boom(text, judge="gister"):
            raise RuntimeError("the worker died")
        jd.caption_llm = jd.gist_llm = boom
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 0, 1), "a crashed worker is not the model's verdict: the caption stays owed")
        self.assertGreaterEqual(len([r for r in self._rows("pass-crash") if r["judge"] == "captioner"]), 1)
        self.assertFalse((jd.CAPDIR / (SID + ".fails.json")).exists(), "no strike for a crash")
        jd.caption_llm = lambda text: (self.caption_calls.append(text) or "Wired the export button.")
        jd.gist_llm = lambda text, judge="gister": (self.caption_calls.append(text) or "Wire the export button")
        self._reset()
        self._pass(tiers=("index",))
        self.assertTrue(self._captioned("did C"))
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 1, 0))

    def test_the_archivers_failure_ladder_re_arms_through_its_own_publish_and_the_give_up_stamps(self):
        # each failed archive call bumps the fail counter ON the record (a publish), which moves the archive
        # identity and re-arms the session once more, until the give-up gate holds the turn set: then the
        # session has no refresh due, stamps, and skips until a new turn caption changes the count
        self._session(SID)
        jd.archive_llm = lambda log: None                                # a call failure
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 0, 1), "captions landed; the archive attempt failed and wrote its counter")
        self.assertEqual(jd.load_archive(SID)["fails"], 1)
        for _ in range(jd.ARCH_FAIL_CAP - 1):
            self._reset()
            self._pass(tiers=("index",))
            self.assertEqual(self._ran(), (1, 0, 0, 1), "the counter publish re-armed the session: it retries")
        self.assertEqual(jd.load_archive(SID)["fails"], jd.ARCH_FAIL_CAP)
        self.assertEqual(len([r for r in self._rows("give-up") if r["judge"] == "archiver"]), 1)
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 1, 0), "the give-up gate holds this turn set: no refresh due, the run stamps")
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (0, 1, 0, 0), "and skips")
        jd.append_caption(SID, "t9", "turn", T0 + 900, "Did more")       # a new turn caption re-arms the ladder
        jd.archive_llm = lambda log: (self.archive_calls.append(log) or {"headline": "H", "abstract": "A."})
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 0, 1))
        self.assertEqual(jd.load_archive(SID)["turns"], 3, "the refresh landed")

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode-000 file")
    def test_an_unreadable_captions_file_leaves_no_stamp_and_the_due_archive_refreshes_once_it_reads(self):
        # plan test (a): a captions read that fails after the gate's stat. The body stands down (no caption is
        # minted against a done set it could not see, no archive is rebuilt from captions it could not read),
        # the run is incomplete, one row is written for the episode, and the refresh that was due lands on the
        # first pass after the file reads again
        self._session(SID)
        self._converge(tiers=("index",))
        jd.append_caption(SID, "t3", "turn", T0 + 300, "Did C")          # a third turn caption: the archive is due (3 != 2)
        cp = jd.CAPDIR / (SID + ".jsonl")
        n0, a0 = len(self.caption_calls), len(self.archive_calls)
        os.chmod(cp, 0)
        try:
            for i in range(2):
                self._reset()
                self._pass(tiers=("index",))
                s = self._st("index")
                self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0), "pass %d: due, no stamp" % i)
                self.assertEqual(len(self._rows("captions-unreadable")), 1, "one row per failure episode, not per pass")
            self.assertEqual((len(self.caption_calls), len(self.archive_calls)), (n0, a0), "stood down: no call either way")
        finally:
            os.chmod(cp, 0o644)
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 0, 1), "readable again: the refresh that was due is written")
        self.assertEqual((len(self.archive_calls), jd.load_archive(SID)["turns"]), (a0 + 1, 3))
        self.assertEqual(len(self.caption_calls), n0, "every unit was already captioned: no re-caption")
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 1, 0))

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode-000 file")
    def test_an_unreadable_archive_record_leaves_no_stamp_and_refreshes_once_it_reads(self):
        # plan test (b): the archiver stands down on a record it cannot read rather than rebuild over it
        self._session(SID)
        self._converge(tiers=("index",))
        jd.append_caption(SID, "t3", "turn", T0 + 300, "Did C")          # the archive is due
        ap = jd.ARCHDIR / (SID + ".json")
        a0 = len(self.archive_calls)
        os.chmod(ap, 0)
        try:
            self._reset()
            self._pass(tiers=("index",))
            s = self._st("index")
            self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0))
            self.assertEqual(len(self._rows("session-archive-unreadable")), 1)
            self.assertEqual(len(self.archive_calls), a0, "stood down: no rebuild over a record the pass could not read")
            self._reset()
            self._pass(tiers=("index",))
            self.assertEqual((self._st("index")["ran"], self._st("index")["incomplete"]), (1, 1), "still due")
            self.assertEqual(len(self._rows("session-archive-unreadable")), 1)
        finally:
            os.chmod(ap, 0o644)
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 0, 1), "readable again: the refresh lands")
        self.assertEqual((len(self.archive_calls), jd.load_archive(SID)["turns"]), (a0 + 1, 3))
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 1, 0))

    def test_a_corrupt_archive_record_is_rebuilt_once_and_an_unreadable_one_still_stands_down(self):
        # the review's should-fix: a record that reads but is not one (a truncated write, a non-record document)
        # is content, so the archiver rebuilds it on the next pass and the publish replaces the file; before, the
        # strict reader stood down on it too, and the session ran every pass forever with the record never rebuilt
        self._session(SID)
        self._converge(tiers=("index",))
        ap = jd.ARCHDIR / (SID + ".json")
        a0 = len(self.archive_calls)
        ap.write_text("{ not the record")
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 0, 1), "a refresh due (no readable record): work, no stamp")
        self.assertEqual(len(self.archive_calls), a0 + 1, "one archive call rebuilds it")
        self.assertEqual(jd.load_archive(SID)["turns"], 2, "a readable record after it")
        self.assertEqual(len(self._rows("session-archive-unreadable")), 1, "the corruption was logged once")
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 1, 0), "the publish re-armed once; the hit path stamps")
        ap.write_text("[1, 2]")                                          # decodes, is not a record: the base crashed on this shape
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual((self._ran(), len(self.archive_calls)), ((1, 0, 0, 1), a0 + 2), "rebuilt, not crashed")
        self.assertEqual(jd.load_archive(SID)["turns"], 2)
        if os.geteuid() != 0:
            self._converge(tiers=("index",))
            os.chmod(ap, 0)
            try:
                os.utime(ap, ns=(os.stat(ap).st_atime_ns, os.stat(ap).st_mtime_ns + 1_000_000_000))   # re-arm: chmod moves ctime only
                self._reset()
                self._pass(tiers=("index",))
                self.assertEqual((self._ran(), len(self.archive_calls)), ((1, 0, 0, 1), a0 + 2),
                                 "a record that cannot be READ still stands the archiver down: no rebuild over it")
            finally:
                os.chmod(ap, 0o644)

    def test_an_unreadable_unit_cache_leaves_no_stamp_and_the_miss_path_repairs_it(self):
        # plan test (b), the unit cache: a cache that exists and does not decode is a voided read (a row, no
        # stamp); the miss path regenerates and publishes it, which moves its identity, and the next pass hits
        path = self._session(SID)
        self._converge(tiers=("index",))
        cf = jd.PCACHE / (SID + ".json")
        cf.write_text("{ not the cache")
        n0 = len(self.caption_calls)
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 0, 1))
        self.assertEqual(len(self._rows("units-cache-unreadable")), 1)
        self.assertEqual(len(self.caption_calls), n0, "the regenerated tasks were all captioned already: no call")
        self.assertEqual(json.loads(cf.read_text())["v"], 6, "repaired by the publish")   # v6 since T252d (upstream 5d295734 moved the seg ids)
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 1, 0), "the repaired cache's identity re-armed once; the hit path stamps")
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (0, 1, 0, 0))

    def test_a_failed_unit_cache_publish_leaves_no_stamp_until_it_lands(self):
        # plan test (c): the parse ran and the tasks stand, but the next pass cannot read them back; a stamp
        # here would hold the cache's identity (absent) over a decision the next pass would have to remake
        path = self._session(SID)
        self._converge(tiers=("index",))
        shutil.rmtree(jd.PCACHE)
        jd.PCACHE.write_text("")                                         # a file where the cache dir goes: mkdir fails
        for i in range(2):
            self._reset()
            self._pass(tiers=("index",))
            self.assertEqual(self._ran(), (1, 0, 0, 1), "pass %d: the publish failed, the run is incomplete" % i)
            self.assertEqual(len(self._rows("units-cache-write-failed")), 1, "one row per failure episode")
        jd.PCACHE.unlink()
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 1, 0), "the publish lands: a complete run, stamped under the pre-run identity")
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 1, 0), "the new cache identity re-arms once")
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (0, 1, 0, 0))

    def test_a_store_read_fault_on_the_miss_path_voids_only_that_sessions_stamp(self):
        # plan test (d): the miss path loads the store for the seams; a goals file that exists and does not
        # READ stands the session down (upstream #1019, steer 1 of the 2026-09-08 fold: tasks_for reads it
        # through load_goals_or_fault, which files the boundary's row; before it the fork's fallback store stood
        # the stage down): no caption over a task list built without the store, no cache published, THAT run
        # marked; the other session, re-armed on its hit path in the same pass, stamps. Bytes that do not parse
        # are quarantined and the tasks built on the fresh store (IndexReaders).
        path = self._session(SID)
        self._session(SID2, name="api")
        self._converge(tiers=("index",))
        gp = jd.GOALDIR / (SID + ".json")
        gp.parent.mkdir(parents=True, exist_ok=True)
        gp.write_text(_fresh_store_text(SID))                            # exists and parses: only the read faults
        self._append(path, *self.TURN_C)                                 # SID misses its cache: the store is read
        self._rearm_hit(SID2)
        before, before2 = self._stamp("index", SID), self._stamp("index", SID2)
        self._reset()
        with _store_read_fault(gp):
            self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (2, 0, 1, 1))
        self.assertEqual(self._stamp("index", SID), before, "the fault voided this session's stamp: the stale one stands")
        self.assertNotEqual(self._stamp("index", SID2), before2, "and only this one: the other re-stamped")
        self.assertEqual(len(self._rows("store-unreadable")), 1)
        self.assertFalse(self._captioned("did C"), "stood down: no caption over a task list built without the store")
        self.assertNotEqual(json.loads((jd.PCACHE / (SID + ".json")).read_text())["key"],
                            json.loads(json.dumps(list(jd._frame_parse_key(SID, [str(path)])[0]))),
                            "nothing memoized under the fault: the cache still holds the pre-append key")
        self._reset()                                                    # the fault lifted: nothing on disk moved
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 1, 0, 1), "the store reads: the new turn is captioned")
        self.assertTrue(self._captioned("did C"))
        self.assertEqual(len(self._rows("store-unreadable")), 1, "the episode ended on the read")
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 1, 1, 0))

    def test_a_crash_in_either_body_logs_a_row_counts_incomplete_and_the_pass_goes_on(self):
        # before the gate, a crash anywhere in the captioner loop ended the index pass for every session after
        # it; now each body's crash is this session's pass-crash row, the run is incomplete with no stamp, and
        # the other session runs and stamps
        path = self._session(SID)
        self._session(SID2, name="api")
        self._converge(tiers=("index",))
        real = self._saved_store[5]

        def poisoned(fsid, files, now):
            if fsid == SID:
                raise ValueError("not a transcript")
            return real(fsid, files, now)
        jd.parsed_session = poisoned
        self._append(path, *self.TURN_C)                                 # SID misses its cache: the parse raises
        self._rearm_hit(SID2)
        before, before2 = self._stamp("index", SID), self._stamp("index", SID2)
        self._reset()
        self._pass(tiers=("index",))                                    # returns: the crash is per session
        self.assertEqual(self._ran(), (2, 0, 1, 1), "the crash counts incomplete; the other session stamped")
        self.assertEqual(self._stamp("index", SID), before, "no new stamp for the crashed session")
        self.assertNotEqual(self._stamp("index", SID2), before2)
        notes = [r["note"] for r in self._rows("pass-crash") if r["fsid"] == SID]
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0].startswith("tasks: ValueError"), notes[0])
        jd.parsed_session = real
        real_stc = self._saved_index[5]

        def stc_crashes(fsid, rows=None):
            if fsid == SID:
                raise RuntimeError("a row without a grain")
            return real_stc(fsid, rows)
        jd.session_turn_captions = stc_crashes
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 1, 0, 1), "the archiver body's crash: incomplete, no stamp; the other sid skipped")
        self.assertTrue(self._captioned("did C"), "the captioner's body ran first and its captions landed")
        notes = [r["note"] for r in self._rows("pass-crash") if r["fsid"] == SID]
        self.assertEqual(len(notes), 2)
        self.assertTrue(notes[1].startswith("archive: RuntimeError"), notes[1])
        jd.session_turn_captions = real_stc
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 1, 0, 1), "healed: the archive refresh the crash deferred is written")
        self.assertEqual(jd.load_archive(SID)["turns"], 3)
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 1, 1, 0))

    def test_a_cut_arming_between_the_pin_and_the_parse_withholds_the_stamp_and_memoizes_nothing(self):
        # the served-pair rule for the index: the parse the miss path ran was made under a cut the pinned pair
        # does not name, so the stamp is withheld; and the unit cache is NOT published under the pinned key
        # (before, the cut world's tasks were memoized under the uncut key, and a later pass pinning that key
        # hit them and never captioned the turn the cut hid)
        path = self._session(SID)
        self._converge(tiers=("index",))
        self._append(path, *self.TURN_C)
        before = self._stamp("index")
        cf = jd.PCACHE / (SID + ".json")
        cached = cf.read_text()
        own = jd.begin_pass_frame()
        try:
            jd._frame_parse_key(SID, [str(path)])                        # the pin, under no cut
            jd._PENDING_CUT_FN = lambda fsid: "a2"                       # a bare rollback arms before the parse
            jd.run_index(now=NOW)
        finally:
            jd.end_pass_frame(own)
        s = self._st("index")
        self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0),
                         "served under another cut: the skipped publish marks the run, no stamp")
        self.assertEqual(self._stamp("index"), before, "the old stamp stands")
        self.assertFalse(self._captioned("did C"), "the cut hid turn C from the parse")
        self.assertEqual(cf.read_text(), cached, "nothing memoized under the pinned key for a world parsed under the cut")
        jd._PENDING_CUT_FN = None
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 0, 1), "the cut cleared: the next pass re-parses and captions turn C")
        self.assertTrue(self._captioned("did C"))

    def test_a_cut_that_clears_between_the_parse_and_the_publish_still_memoizes_nothing(self):
        # the review's should-fix: the moved-cut check re-read the live cut a third time, so a cut that cleared
        # between the parse and that read compared equal to the pinned pair and the cut world's tasks were
        # memoized under the uncut key; the next pass hit them, stamped, and the hidden turn was never captioned
        # until the transcript moved. The check now compares the pair the parse was SERVED under (recorded when
        # it was pinned) against the pinned pair, and reads the cut no third time.
        path = self._session(SID)
        self._converge(tiers=("index",))
        self._append(path, *self.TURN_C)
        before = self._stamp("index")
        cf = jd.PCACHE / (SID + ".json")
        cached = cf.read_text()
        answers = []

        def cut_once(fsid):
            answers.append(fsid)
            return "a2" if len(answers) == 1 else ""                     # armed for the parse, cleared for anything after
        own = jd.begin_pass_frame()
        try:
            jd._frame_parse_key(SID, [str(path)])                        # the pin, under no cut
            jd._PENDING_CUT_FN = cut_once
            jd.run_index(now=NOW)
        finally:
            jd.end_pass_frame(own)
        self.assertEqual(len(answers), 1, "the cut is read once, by the parse; the publish check reads the served pair")
        s = self._st("index")
        self.assertEqual((s["ran"], s["incomplete"], s["stamped"]), (1, 1, 0), "no stamp")
        self.assertEqual(self._stamp("index"), before)
        self.assertEqual(cf.read_text(), cached, "no memo of the cut world under the uncut key")
        self.assertFalse(self._captioned("did C"))
        jd._PENDING_CUT_FN = None
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 0, 1), "the next pass re-parses and captions the turn the cut hid")
        self.assertTrue(self._captioned("did C"))

    def test_a_turn_ending_after_the_first_touch_is_captioned_next_pass_whole(self):
        # the frame hazard for the index: a tick job touches the session while its last turn is OPEN, the
        # turn's final record and the idle row land, then run_index runs. Its stamp holds the PRE-append pair
        # (the pinned key it read the unit cache under), so the next pass runs the session over the ended turn
        path = self._session(SID, [uline(T0, "task A", "u1"), aline(T0 + 30, "did A", "a1", "u1"),
                                   uline(T0 + 100, "task B", "u2", "a1"),
                                   aline(T0 + 110, "starting on B", "a2", "u2", stop="tool_use")])
        self._converge(tiers=("index",))
        own = jd.begin_pass_frame()
        try:
            jd.parsed_session(SID, [str(path)], NOW)                    # the tick job's first touch, turn open
            pre = jd._frame["keys"][("parse", SID)]
            self._append(path, aline(T0 + 140, "did B", "a3", "a2"))
            self._states_row(SID, T0 + 141, "idle")
            jd.run_index(now=NOW)
        finally:
            jd.end_pass_frame(own)
        st = self._stamp("index")
        self.assertIsNotNone(st, "the pass completed over the pinned world and stamped")
        self.assertEqual(st[0][0][1], jd._pair_key(pre), "the stamp holds the PRE-append pair")
        self.assertFalse(self._captioned("did B"))
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._st("index")["ran"], 1, "the next pass runs: the live pair differs from the stamped one")
        self.assertTrue(self._captioned("did B"), "the ended turn's work is captioned, whole")

    def test_eviction_follows_discover_and_a_restart_is_a_full_walk(self):
        self._session(SID)
        self._session(SID2, name="api")
        self._converge(tiers=("index",))
        self.assertEqual({k for k in jd._STAGE_STAMP if k[0] == "index"}, {("index", SID), ("index", SID2)})
        (jd.NAMES / SID2).unlink()                                      # the session leaves discover
        jd._namefp_memo.clear()
        self._pass(tiers=("index",))
        self.assertEqual({k for k in jd._STAGE_STAMP if k[0] == "index"}, {("index", SID)}, "the gone sid's stamp evicted")
        jd._STAGE_STAMP.clear()                                         # what a restart does
        self._reset()
        self._pass(tiers=("index",))
        self.assertEqual(self._ran(), (1, 0, 1, 0), "the first pass after boot runs the session, as before the gate")

    def test_counters_add_up_over_the_index(self):
        path = self._session(SID)
        self._pass(tiers=("index",))
        self._append(path, *self.TURN_C)
        self._pass(tiers=("index",))
        self._pass(tiers=("index",))
        self._pass(tiers=("index",))
        s = self._st("index")
        self.assertEqual(s["ran"], s["stamped"] + s["bypassed"] + s["incomplete"])
        self.assertGreater(s["skipped"], 0)
        ts = jd.tier_stats()
        self.assertIn("index", ts)
        self.assertEqual(set(ts), set(jd.GATED_TIERS) | {"stamps"})


if __name__ == "__main__":
    unittest.main()
