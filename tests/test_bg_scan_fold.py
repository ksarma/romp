#!/usr/bin/env python3
"""The background-task pairing, the timeline's state intervals and postal connectors, and the
last-state readers stop re-walking whole files (2026-09-03). Profiled live with ~10 sessions, the
kernel's push loop held a full core, a third of it json-decoding bytes it had already decoded: the
bg-scan caches (kernel ×2, judge ×1) re-paired a working session's ENTIRE transcript on every appended
record (one was 180 MB), `_state_intervals` re-read and re-parsed every states log twice per 2 s
timeline rebuild, `_postal_messages` re-parsed the whole message log per rebuild, and `last_state`
read a whole log to find its last line. The scan is now a fold over em.fold_records (moved from the
kernel so the judge shares it); the running-only view forgets terminal tasks behind a tombstone; the
last-state readers read the tail backwards. Contract: every answer equals the old from-scratch walk.
Synthetic fixtures only: placeholder ids, invented text."""
import json
import os
import tempfile
import time
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
em = SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
jd = SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
km = SourceFileLoader("romp_kernel_bgfold", os.path.join(BIN, "romp-kernel")).load_module()
sb = SourceFileLoader("romp_sdk_backend_bgfold", os.path.join(BIN, "..", "kernel", "sdk_backend.py")).load_module()

SID = "11111111-2222-3333-4444-555555555555"
PEER = "11111111-2222-3333-4444-666666666666"


def _bump(path):
    """Make the next write land under a DIFFERENT mtime even on a coarse-clock filesystem."""
    st = os.stat(path)
    os.utime(path, (st.st_atime, st.st_mtime + 2))


def _append(path, *recs):
    with open(path, "a") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    _bump(path)


def _user(text, **kw):
    r = {"type": "user", "uuid": kw.pop("uuid", "u"), "timestamp": kw.pop("ts", "2026-09-02T10:00:00.000Z"),
         "message": {"role": "user", "content": text}}
    r.update(kw)
    return r


def _assistant(blocks, **kw):
    r = {"type": "assistant", "uuid": kw.pop("uuid", "a"), "timestamp": kw.pop("ts", "2026-09-02T10:00:01.000Z"),
         "message": {"role": "assistant", "content": blocks}}
    r.update(kw)
    return r


def _launch(tid, desc):
    return _assistant([{"type": "tool_use", "id": tid, "name": "Bash",
                        "input": {"command": "sleep 1", "run_in_background": True, "description": desc}}])


def _result(tid, status="completed"):
    note = ("<task-notification>\n<task-id>%s</task-id>\n<tool-use-id>%s</tool-use-id>\n"
            "<status>%s</status>\n<summary>%s</summary>\n</task-notification>" % ("b1", tid, status, status))
    return _user(note, ts="2026-09-02T10:00:05.000Z")


class BackgroundTasks(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.td.name, SID + ".jsonl")
        for c in (km._bgtasks_cache, km._bgall_cache, jd._BG_SCAN_CACHE):
            c.clear()

    def tearDown(self):
        self.td.cleanup()

    def _steps(self, cache):
        """Records folded so far, per the fold_records entry (n, last record, state)."""
        return cache[self.p][0]

    def test_caches_fold_appends_and_keep_their_two_views_apart(self):
        _append(self.p, _launch("toolu_1", "first job"))
        self.assertEqual([t["id"] for t in km._bg_scan_cached(self.p)], ["toolu_1"])
        self.assertEqual([t["status"] for t in km._bg_scan_all_cached(self.p)], ["running"])
        _append(self.p, _launch("toolu_2", "second job"), _result("toolu_1"))
        self.assertEqual([t["id"] for t in km._bg_scan_cached(self.p)], ["toolu_2"],
                         "toolu_1 returned → only toolu_2 still runs")
        every = km._bg_scan_all_cached(self.p)
        self.assertEqual([(t["id"], t["status"]) for t in every],
                         [("toolu_1", "completed"), ("toolu_2", "running")])
        self.assertTrue(every[0].get("endT"), "the return's moment rides the row")
        self.assertEqual(self._steps(km._bgtasks_cache), 3)
        self.assertEqual(self._steps(km._bgall_cache), 3)

    def test_only_the_appended_records_are_stepped(self):
        _append(self.p, _launch("toolu_1", "a"), _launch("toolu_2", "b"))
        km._bg_scan_cached(self.p)
        seen = []
        real = em._bg_step

        def spy(state, o):
            seen.append(o.get("uuid"))
            return real(state, o)
        em._bg_step = spy
        try:
            _append(self.p, _result("toolu_2"))
            self.assertEqual([t["id"] for t in km._bg_scan_cached(self.p)], ["toolu_1"])
        finally:
            em._bg_step = real
        self.assertEqual(seen, ["u"], "one appended record → one step; the prefix was not re-paired")

    def test_answers_are_snapshots_of_the_fold_state(self):
        _append(self.p, _launch("toolu_1", "a"))
        row = km._bg_scan_all_cached(self.p)[0]
        row["status"] = "tampered"                   # a caller scribbling on its answer...
        _append(self.p, _launch("toolu_2", "b"))
        self.assertEqual([t["status"] for t in km._bg_scan_all_cached(self.p)], ["running", "running"],
                         "...never reaches the fold state the next incremental answer is built from")

    def test_running_only_state_forgets_terminal_tasks_and_dead_dispatches(self):
        _append(self.p, _launch("toolu_1", "a"),
                _assistant([{"type": "tool_use", "id": "toolu_sync", "name": "Agent",
                             "input": {"description": "sync agent", "prompt": "x" * 500}}]),
                _user([{"type": "tool_result", "tool_use_id": "toolu_sync", "content": "done"}]),
                _result("toolu_1"))
        self.assertEqual(km._bg_scan_cached(self.p), [])
        st = km._bgtasks_cache[self.p][2]
        self.assertEqual((st["tasks"], st["order"], st["dispatch"], st["done"]), ({}, [], {}, {"toolu_1"}),
                         "a returned task leaves a tombstone, not a row; a synchronously-acked dispatch leaves nothing")
        every = km._bg_scan_all_cached(self.p)
        self.assertEqual([(t["id"], t["status"]) for t in every], [("toolu_1", "completed")],
                         "the history view keeps the returned task")
        self.assertEqual(km._bgall_cache[self.p][2]["dispatch"], {})

    def test_a_replayed_ack_after_the_terminal_does_not_resurrect_the_task(self):
        # a real transcript shape: launch → async ack → terminal notification → the SAME ack again
        launch = _assistant([{"type": "tool_use", "id": "toolu_ag", "name": "Agent",
                              "input": {"description": "explore", "prompt": "look around"}}])
        ack = _user([{"type": "tool_result", "tool_use_id": "toolu_ag", "content": "launched"}],
                    toolUseResult={"isAsync": True, "status": "async_launched", "description": "explore",
                                   "taskType": "local_agent"}, uuid="ack-1")
        _append(self.p, launch, ack)
        self.assertEqual([t["id"] for t in km._bg_scan_cached(self.p)], ["toolu_ag"])
        _append(self.p, _result("toolu_ag"))
        self.assertEqual(km._bg_scan_cached(self.p), [])
        _append(self.p, ack)                          # the replay lands AFTER the row was dropped
        self.assertEqual(km._bg_scan_cached(self.p), [], "a tombstoned id cannot come back as running")
        self.assertEqual(km._bg_scan_cached(self.p), em._scan_bg_tasks(self.p),
                         "…and the incremental answer still equals the full walk")
        self.assertEqual([(t["id"], t["status"]) for t in km._bg_scan_all_cached(self.p)],
                         [("toolu_ag", "completed")])
        _append(self.p, launch)                       # a replayed LAUNCH record is ignored the same way
        self.assertEqual(km._bg_scan_cached(self.p), [])
        for cache in (km._bgtasks_cache, km._bgall_cache):
            self.assertEqual(cache[self.p][2]["dispatch"], {},
                             "neither replay left a dispatch entry behind in either view's state")

    def test_uncached_scan_and_cached_scans_agree(self):
        _append(self.p, _launch("toolu_1", "a"), _launch("toolu_2", "b"), _result("toolu_2", "failed"))
        self.assertEqual(em._scan_bg_tasks(self.p), km._bg_scan_cached(self.p))
        self.assertEqual(em._scan_bg_tasks(self.p, want_all=True), km._bg_scan_all_cached(self.p))
        self.assertEqual(em._scan_bg_tasks(self.p), em.scan_bg_tasks_cached(self.p, jd._BG_SCAN_CACHE))
        self.assertEqual(jd._bg_unresolved(self.p), em._scan_bg_tasks(self.p), "the judge's gate reads the same fold")

    def test_rewrite_refolds_from_the_top(self):
        _append(self.p, _launch("toolu_1", "a"), _launch("toolu_2", "b"))
        self.assertEqual(len(km._bg_scan_cached(self.p)), 2)
        with open(self.p, "w") as f:
            f.write(json.dumps(_launch("toolu_9", "z")) + "\n")
        _bump(self.p)
        self.assertEqual([t["id"] for t in km._bg_scan_cached(self.p)], ["toolu_9"])

    def test_missing_file(self):
        self.assertEqual(km._bg_scan_cached("/no/such/transcript.jsonl"), [])
        self.assertEqual(km._bg_scan_all_cached("/no/such/transcript.jsonl"), [])

    def test_a_final_record_without_its_newline_still_counts(self):
        # the old whole-file walk saw a complete final line with no "\n"; the incremental reader leaves it
        # unconsumed (torn-write safety), so the fold applies it provisionally — and permanently once the
        # newline lands, exactly once
        _append(self.p, _launch("toolu_1", "a"))
        self.assertEqual([t["id"] for t in km._bg_scan_cached(self.p)], ["toolu_1"])
        with open(self.p, "a") as f:
            f.write(json.dumps(_result("toolu_1")))   # complete record, no newline yet
        _bump(self.p)
        self.assertEqual(km._bg_scan_cached(self.p), [], "the terminal record counts even without its newline")
        self.assertEqual(km._bg_scan_cached(self.p), em._scan_bg_tasks(self.p))
        self.assertEqual(km._bgtasks_cache[self.p][0], 1, "…but it is not in the cached fold yet")
        with open(self.p, "a") as f:
            f.write("\n")
        _bump(self.p)
        self.assertEqual(km._bg_scan_cached(self.p), [])
        self.assertEqual(km._bgtasks_cache[self.p][0], 2, "the newline lands → folded for good, once")
        self.assertEqual([(t["id"], t["status"]) for t in km._bg_scan_all_cached(self.p)], [("toolu_1", "completed")])

    def test_a_torn_final_record_is_ignored_until_complete(self):
        _append(self.p, _launch("toolu_1", "a"))
        km._bg_scan_cached(self.p)
        with open(self.p, "a") as f:
            f.write(json.dumps(_result("toolu_1"))[:-20])   # a writer caught mid-append
        _bump(self.p)
        self.assertEqual([t["id"] for t in km._bg_scan_cached(self.p)], ["toolu_1"])


class TimelineReaders(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd._rebind_state(Path(self.td.name))
        (jd.STATE / "states").mkdir(parents=True)
        (jd.STATE / "timeline").mkdir(parents=True)
        km._state_ev_cache.clear()
        km._postal_log_cache.clear()

    def tearDown(self):
        jd._rebind_state(self.saved)
        self.td.cleanup()

    def test_state_intervals_fold_appended_transitions(self):
        now = 1_000_000
        p = jd.STATE / "states" / (SID + ".jsonl")
        _append(str(p), {"t": now - 300, "state": "working"}, {"t": now - 200, "state": "permission"})
        self.assertEqual(km._state_intervals(SID, "permission", now), [[now - 200, now]],
                         "an open awaiting interval runs to now")
        _append(str(p), {"t": now - 100, "state": "working"}, {"awaiting": False})
        self.assertEqual(km._state_intervals(SID, "permission", now), [[now - 200, now - 100]])
        self.assertEqual(km._state_intervals(SID, "compacting", now), [])
        self.assertEqual(km._state_ev_cache[str(p)][0], 4, "one fold serves every `want`")

    def test_state_transition_without_its_newline_still_counts(self):
        now = 1_000_000
        p = jd.STATE / "states" / (SID + ".jsonl")
        _append(str(p), {"t": now - 300, "state": "working"})
        with open(p, "a") as f:
            f.write(json.dumps({"t": now - 200, "state": "permission"}))
        _bump(str(p))
        self.assertEqual(km._state_intervals(SID, "permission", now), [[now - 200, now]])
        self.assertEqual(km._state_ev_cache[str(p)][0], 1, "provisional: not folded into the cache")

    def test_postal_event_without_its_newline_still_counts(self):
        now = int(time.time())
        log = jd.STATE / "timeline" / "messages.jsonl"
        _append(str(log), {"ev": "sent", "id": "m1", "from_id": SID, "to_id": PEER, "t": now - 60, "body": "ping"})
        with open(log, "a") as f:
            f.write(json.dumps({"ev": "exec", "id": "m1", "t": now - 30}))
        _bump(str(log))
        rows = km._postal_messages(now, {SID, PEER}, {SID: "web", PEER: "api"}, live_sids={SID, PEER})
        self.assertEqual([(r["id"], r["hasExec"]) for r in rows], [("m1", True)])

    def test_state_intervals_missing_file(self):
        self.assertEqual(km._state_intervals(SID, "permission", 5), [])

    def test_postal_connectors_fold_the_message_log(self):
        now = int(time.time())
        log = jd.STATE / "timeline" / "messages.jsonl"
        _append(str(log), {"ev": "sent", "id": "m1", "from_id": SID, "to_id": PEER, "t": now - 60, "body": "ping"})
        names = {SID: "web", PEER: "api"}
        rows = km._postal_messages(now, {SID, PEER}, names, live_sids={SID, PEER})
        self.assertEqual([(r["id"], r["hasExec"], r["pending"]) for r in rows], [("m1", False, True)])
        _append(str(log), {"ev": "exec", "id": "m1", "t": now - 30},
                {"ev": "sent", "id": "m2", "from_id": PEER, "to_id": SID, "t": now - 20, "body": "pong"},
                {"ev": "recall", "id": "m2", "t": now - 10})
        rows = km._postal_messages(now, {SID, PEER}, names, live_sids={SID, PEER})
        self.assertEqual([(r["id"], r["hasExec"], r["pending"]) for r in rows],
                         [("m1", True, False), ("m2", False, False)])
        self.assertEqual(km._postal_log_cache[str(log)][0], 4)

    def test_postal_connectors_missing_log(self):
        self.assertEqual(km._postal_messages(5, {SID}, {SID: "web"}), [])


class LastState(unittest.TestCase):
    """last_state / last_state_value read the file's TAIL backwards; they must answer exactly what the
    forward walk did, on every file shape — including lines longer than the read block."""
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        (Path(self.td.name) / "states").mkdir()
        self.p = Path(self.td.name) / "states" / (SID + ".jsonl")

    def tearDown(self):
        self.td.cleanup()

    @staticmethod
    def _forward_last(p):
        try:
            line = ""
            with open(p) as f:
                for line in f:
                    pass
            return json.loads(line) if line.strip() else {}
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _forward_value(p):
        val = ""
        try:
            with open(p) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(rec, dict) and "state" in rec:
                        val = str(rec["state"])
        except OSError:
            pass
        return val

    def _check(self, text):
        self.p.write_text(text)
        self.assertEqual(sb.last_state(self.td.name, SID), self._forward_last(self.p), repr(text[-40:]))
        self.assertEqual(sb.last_state_value(self.td.name, SID), self._forward_value(self.p), repr(text[-40:]))

    def test_shapes(self):
        a = json.dumps({"t": 1, "state": "working"})
        b = json.dumps({"t": 2, "state": "ready"})
        ov = json.dumps({"awaiting": False})
        for text in ("", "\n", a, a + "\n", a + "\n" + b, a + "\n" + b + "\n", a + "\n" + b + "\n\n",
                     a + "\n" + b + "\n" + ov + "\n", a + "\n" + ov + "\n" + ov + "\n",
                     a + "\n" + "not json\n", "\n\n" + a + "\n", a + "\r\n" + b + "\r\n"):
            self._check(text)

    def test_lines_longer_than_a_read_block(self):
        big = json.dumps({"t": 1, "state": "working", "pad": "x" * 200_000})
        self._check(big + "\n" + json.dumps({"awaiting": True}) + "\n")
        self._check(json.dumps({"awaiting": True}) + "\n" + big + "\n")
        self._check(big)

    def test_multibyte_text_across_a_block_boundary(self):
        rec = json.dumps({"t": 1, "state": "working", "pad": "é" * 70_000}, ensure_ascii=False)
        self._check(rec + "\n" + json.dumps({"awaiting": True}) + "\n")

    def test_missing_file(self):
        self.assertEqual(sb.last_state(self.td.name, "nope"), {})
        self.assertEqual(sb.last_state_value(self.td.name, "nope"), "")

    def test_reads_the_tail_only(self):
        many = "".join(json.dumps({"t": i, "state": "working", "pad": "y" * 100}) + "\n" for i in range(5000))
        self.p.write_text(many + json.dumps({"t": 5000, "state": "ready"}) + "\n")
        real_open = open
        sizes = []

        class Spy:
            def __init__(self, f):
                self.f = f

            def read(self, n=-1):
                sizes.append(n)
                return self.f.read(n)

            def __getattr__(self, k):
                return getattr(self.f, k)

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return self.f.__exit__(*a)

        sb.open = lambda *a, **k: Spy(real_open(*a, **k))
        try:
            self.assertEqual(sb.last_state(self.td.name, SID)["state"], "ready")
        finally:
            del sb.open
        self.assertLess(sum(sizes), self.p.stat().st_size // 4, "one block from the end, not the file")


if __name__ == "__main__":
    unittest.main()
