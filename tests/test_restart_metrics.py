#!/usr/bin/env python3
"""T304: `romp restart-metrics` (cli/restart_metrics.py), the read-only reader of what kernel restarts do to
the sessions. Hermetic: synthetic ledgers under a private state directory (placeholder uuids, TESTHOST, no
live reads), every row kind the reader parses, the window arithmetic, the summary text, the live helpers on
synthetic cgroup files and ps lines, and the JSON document's shape. Nothing here touches a kernel, and no test
reads the machine's own hostname, login or home: every `--public` run replaces machine_probes with SYNTHETIC_PROBES
or a probe list of its own."""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
rm = load_source("romp_restart_metrics", os.path.join(BIN, "romp-restart-metrics"))
pp = rm.perf_public          # the public shape the --public flag applies (cli/perf_public.py)

SID = "11111111-2222-4333-8444-000000000304"
SID2 = "22222222-3333-4444-8555-000000000304"
TZ = "UTC"
# What the identifier scan learns in a `--public` run here, instead of this machine's strings: a run that read the
# real hostname would refuse the print on any machine whose name is a token of the document (round 2 of the export's
# review found two tests doing so)
SYNTHETIC_PROBES = [("hostname", "testhost"), ("username", "tester"), ("home directory", "/home/tester")]


def _keys_named(doc, name):
    """The key paths of every dict holding a key named `name`, at any depth of `doc`; empty when none does."""
    out = []

    def walk(node, where):
        if isinstance(node, dict):
            if name in node:
                out.append("/".join(str(p) for p in where))
            for k, v in node.items():
                walk(v, where + (k,))
        elif isinstance(node, (list, tuple)):
            for i, v in enumerate(node):
                walk(v, where + (i,))
    walk(doc, ())
    return out


# A clock stamp is a number inside a PLAUSIBLE EPOCH WINDOW: the seconds from 2017 to 2033, or the same span in
# milliseconds; every stamp the fixture writes (2026) sits in the first, and no count or duration of the fixture reaches
# either. The same windows as tests/test_perf_export.py, worded there over a floor of 1.5e9 until the served kernel's
# glibc allocator figures passed it on CI's runner (round 5 of the export's review, 2026-09-18): a large number outside
# the windows is a measurement the public form keeps on purpose, not a stamp.
EPOCH_WINDOWS = ((1.5e9, 2.0e9), (1.5e12, 2.0e12))


def _numbers(doc):
    """[(path, value)] for every numeric leaf of `doc` (a bool is not a number)."""
    out = []

    def walk(node, where):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, where + (k,))
        elif isinstance(node, (list, tuple)):
            for i, v in enumerate(node):
                walk(v, where + (i,))
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            out.append(("/".join(str(p) for p in where), node))
    walk(doc, ())
    return out


def _stamps(doc):
    """The numeric leaves of `doc` that read as an absolute clock stamp: inside one of the EPOCH_WINDOWS."""
    return [(p, v) for p, v in _numbers(doc) if any(lo <= v <= hi for lo, hi in EPOCH_WINDOWS)]
D0 = rm.day_start("2026-09-10", TZ)          # the anchor day, midnight UTC


def _write(state: Path, name: str, rows):
    (state / name).parent.mkdir(parents=True, exist_ok=True)
    with open(state / name, "w") as f:
        for r in rows:
            f.write((json.dumps(r) if isinstance(r, dict) else r) + "\n")


def _fixture(state: Path):
    """A synthetic week: two restarts on day 0 (one quiet-window deploy, one backstop cut), a crash-only
    boot on day 2, events, turns (one a redo turn), a state log, spend."""
    t1 = D0 + 3600            # day 0, 01:00: a quiet-window deploy that cut two turns
    t2 = D0 + 7200            # day 0, 02:00: a backstop-cut restart, one turn
    t3 = D0 + 2 * 86400 + 60  # day 2: a boot with no cut row (a crash)
    _write(state, "restart-cuts.jsonl", [
        {"t": t1, "pid": 100, "cutTurns": [{"sid": SID, "name": "web"}, {"sid": SID2, "name": "api"}],
         "stopped": 5, "unjoined": 1, "reaped": 1, "watchesArmed": 3, "reason": "manager-sigterm: restart-all", "auditT": t1 - 2,
         "rssKb": 4 * 1024 * 1024, "cpuS": 900.5},
        {"t": t1 + 2, "pid": 101, "bootSettled": True, "firstServe": t1 + 2.5, "reconcileDone": t1 + 2.7,
         "settleS": 0.2, "prevCutT": t1, "outageS": 2.5, "rssKb": 300 * 1024, "cpuS": 1.5},
        "this line is not json",
        {"t": t2, "pid": 101, "cutTurns": [{"sid": SID, "name": "web"}], "stopped": 5, "unjoined": 0, "reaped": 0,
         "watchesArmed": 3, "reason": "p2p-update", "rssKb": 2 * 1024 * 1024, "cpuS": 300.0},
        {"t": t2 + 4, "pid": 102, "bootSettled": True, "firstServe": t2 + 4.0, "reconcileDone": t2 + 4.3,
         "settleS": 0.3, "prevCutT": t2, "outageS": 4.0},
        {"t": t3, "pid": 103, "bootSettled": True, "firstServe": t3 + 0.5, "reconcileDone": t3 + 0.6, "settleS": 0.1},
    ])
    _write(state, "restart-audit.jsonl", [
        {"t": t1 - 300, "action": "p2p-update", "reason": "deploy", "when": "quiet"},
        {"t": t1 - 3, "action": "quiet-window", "since": t1 - 300, "waitedS": 297, "reason": "quiet", "backstop": False,
         "coalesced": 2, "mode": "all", "lastInflight": 0, "misses": 0, "drainRefusedCount": 0, "drainArmedCount": 3},
        {"t": t1 - 2, "action": "manager-sigterm", "kernel": "main", "pid": 100, "reason": "restart", "trigger": "restart-all"},
        {"t": t2 - 1, "action": "quiet-window", "since": t2 - 901, "waitedS": 900, "reason": "backstop cap", "backstop": True,
         "coalesced": 1, "mode": "all", "lastInflight": 2, "misses": 0, "drainRefusedCount": 0, "drainArmedCount": 300},
        {"t": t2 - 1, "action": "manager-sigterm", "kernel": "main", "pid": 101, "reason": "restart", "trigger": "restart-all"},
        {"t": t3 + 5, "action": "signal", "reason": "signal, not requested through the manager"},
    ])
    _write(state, "session-events.jsonl", [
        {"t": t1 - 1, "pid": 100, "kind": "drain.unjoined", "sid": SID, "name": "web", "inflight": 1, "reaped": True},
        {"t": t1 + 3, "pid": 101, "kind": "reconcile.duplicate-cli", "sid": SID, "name": "web", "fsid": SID, "pids": "7,8", "n": 2},
        {"t": t1 + 3, "pid": 101, "kind": "reconcile.orphan-reaped", "sid": SID, "name": "web", "cliPid": 7},
        {"t": t1 + 3, "pid": 101, "kind": "reconcile.scope-stopped", "unit": "romp-session-11111111-7-1.scope", "sid8": "11111111"},
        {"t": t1 + 3, "pid": 101, "kind": "reconcile.boot", "sessions": 5, "resumed": 2, "restored": 0, "notified": 0,
         "reaped": 1, "scopesStopped": 1, "toStart": 2, "durationS": 0.2},
        {"t": t1 + 4, "pid": 101, "kind": "host.attached", "sid": SID, "name": "web", "boot": True, "hostPid": 20, "cliPid": 21, "replayFrom": 3},
        {"t": t1 + 4, "pid": 101, "kind": "host.attached", "sid": SID2, "name": "api", "boot": True, "hostPid": 22, "cliPid": 23},
        {"t": t2 + 100, "pid": 102, "kind": "host.attached", "sid": SID, "name": "web", "boot": False, "hostPid": 20, "cliPid": 21},
        {"t": t2 + 5, "pid": 102, "kind": "reconcile.boot", "sessions": 5, "resumed": 1, "reaped": 0, "scopesStopped": 0},
        {"t": t2 + 900, "pid": 102, "kind": "crash.heal", "sid": SID2, "name": "api", "attempt": 1},
        {"t": t2 + 960, "pid": 102, "kind": "crash.loop", "sid": SID2, "name": "api", "attempt": 2},
        {"t": t3 + 1, "pid": 103, "kind": "reconcile.boot", "sessions": 5, "resumed": 0, "reaped": 0, "scopesStopped": 0},
        {"t": t3 + 2, "pid": 103, "kind": "lease.stale-heartbeat", "sid": SID, "name": "web", "leasePid": 9},
        {"kind": "no-stamp"},
    ])
    _write(state, "turns.jsonl", [
        {"t": t1 + 40, "sid": SID, "name": "web", "fedT": t1 + 3, "firstOutT": t1 + 5.5, "resultT": t1 + 40.0,
         "durationMs": 37000, "apiMs": 30000, "numTurns": 4, "usd": 0.5, "tokIn": 100, "tokOut": 200, "tokCacheR": 3000,
         "tokCacheW": 400, "opener": "injected", "resumeNotice": True, "fedTexts": 1},
        {"t": t1 + 100, "sid": SID2, "name": "api", "fedT": t1 + 90, "firstOutT": t1 + 91.0, "resultT": t1 + 100.0,
         "durationMs": 10000, "apiMs": 8000, "usd": 0.1, "opener": "human", "resumeNotice": False, "fedTexts": 1},
        {"t": t2 + 50, "sid": SID2, "name": "api", "fedT": 0, "resultT": t2 + 50.0, "opener": "", "resumeNotice": False},
        # a turn the CLI opened itself at 02:01, written by a kernel before the 2026-09-10 writer fix: nothing fed
        # (fedTexts 0), and the stamps still in memory were the 01:00 turn's (its fedT and firstOutT)
        {"t": t2 + 60, "sid": SID, "name": "web", "fedT": t1 + 3, "firstOutT": t1 + 5.5, "resultT": t2 + 60.0,
         "opener": "injected", "resumeNotice": False, "fedTexts": 0},
    ])
    _write(state, "states/%s.jsonl" % SID, [
        {"t": int(t1 - 100), "state": "working"}, {"t": int(t1 - 70), "state": "waiting"},
        {"t": t1 - 0.5, "machineCut": "restart"},
        {"t": int(t1 + 3), "state": "working"}, {"t": int(t1 + 3), "awaiting": False}, {"t": int(t1 + 40), "state": "waiting"},
        {"t": int(t1 + 200), "state": "working"}, {"t": int(t1 + 210), "state": "waiting", "by": "interrupt"},
        {"t": int(t2 + 10), "state": "working"}, {"t": int(t2 + 20), "state": "idle"},
        {"t": t2 + 899.5, "machineCut": "crash"},
    ])
    (state / "spend.json").write_text(json.dumps({"days": {"2026-09-10": {"usd": 12.5, "turns": 30},
                                                            "2026-09-12": {"usd": 3.0, "turns": 4}}, "hours": {}}))
    return t1, t2, t3


class Parsers(unittest.TestCase):
    def setUp(self):
        self.state = Path(tempfile.mkdtemp())
        self.t1, self.t2, self.t3 = _fixture(self.state)

    def test_restarts_join_cuts_to_boots(self):
        rows, note = rm._read_jsonl(self.state / "restart-cuts.jsonl")
        self.assertEqual(note["unparseable"], 1)
        rs = rm.parse_restarts(rows)
        self.assertEqual([r["t"] for r in rs], [int(self.t1), int(self.t2), int(self.t3)])
        a, b, c = rs
        self.assertEqual((a["cutTurns"], a["cutSessions"], a["unjoined"], a["reaped"]), (2, ["web", "api"], 1, 1))
        self.assertEqual(a["boot"]["outageS"], 2.5)
        self.assertEqual(a["boot"]["settleS"], 0.2)
        self.assertEqual(a["reason"], "manager-sigterm: restart-all")
        self.assertEqual((b["cutTurns"], b["boot"]["outageS"]), (1, 4.0))
        self.assertTrue(c["noCutRow"], "a boot with no cut before it is a crash respawn; its boot row still counts")
        self.assertEqual(c["cutTurns"], 0)

    def test_quiet_windows_join_the_restart_they_released(self):
        cuts, _ = rm._read_jsonl(self.state / "restart-cuts.jsonl")
        audit, _ = rm._read_jsonl(self.state / "restart-audit.jsonl")
        rs = rm.parse_restarts(cuts)
        q = rm.parse_quiet_windows(audit, rs)
        self.assertEqual([(x["waitedS"], x["backstop"], x["restartT"], x["cutTurns"]) for x in q],
                         [(297, False, int(self.t1), 2), (900, True, int(self.t2), 1)])
        counts = rm.audit_counts(audit)
        self.assertEqual(counts["byAction"]["quiet-window"], 2)
        self.assertEqual(counts["sigtermTriggers"], {"restart-all": 2})

    def test_events_turns_and_state_log(self):
        ev, _ = rm._read_jsonl(self.state / "session-events.jsonl")
        events = rm.parse_events(ev)
        self.assertEqual(len(events), 13, "the stamp-less row is dropped (the three host.attached rows count)")
        tu, _ = rm._read_jsonl(self.state / "turns.jsonl")
        turns = rm.parse_turns(tu)
        self.assertEqual(turns[0]["feedToResultS"], 37.0)
        self.assertEqual(turns[0]["feedToFirstOutS"], 2.5)
        self.assertNotIn("feedToResultS", turns[2], "fedT 0 (no feed stamp) → no interval, never a bogus one")
        # the self-opened turn (fedTexts 0) carries the previous fed turn's stamps: an hour of feed-to-result and
        # a duplicated first-output interval if read; it counts as a turn and measures nothing
        self.assertEqual(turns[3]["fedTexts"], 0)
        self.assertNotIn("feedToResultS", turns[3], "nothing fed: the stamps are another turn's, never an interval")
        self.assertNotIn("feedToFirstOutS", turns[3])
        lines = (self.state / "states" / (SID + ".jsonl")).read_text().splitlines()
        sl, cuts = rm.state_log_turns(lines)
        self.assertEqual([x["feedToResultS"] for x in sl], [30.0, 37.0],
                         "working→waiting pairs; an interrupt's by-marked settle and an idle close are not turns")
        self.assertEqual(cuts, {"restart": 1, "crash": 1})
        self.assertEqual(rm.spend_by_day(json.loads((self.state / "spend.json").read_text())), {"2026-09-10": 12.5, "2026-09-12": 3.0})

    def test_parse_turns_gates_on_a_zero_count_alone(self):
        """The fedTexts gate keys on the count 0 and nothing else: a row without the key is read by its stamps
        (a writer that never wrote the key), and a bool is not a count. Direct rows, so the fixture's turn
        count and buckets stay as they are."""
        stamped = {"t": 100, "sid": SID, "fedT": 10, "firstOutT": 12.0, "resultT": 15.0}
        rows = [dict(stamped), dict(stamped, fedTexts=0), dict(stamped, fedTexts=False), dict(stamped, fedTexts=1)]
        got = [(r.get("feedToResultS"), r.get("feedToFirstOutS")) for r in rm.parse_turns(rows)]
        self.assertEqual(got, [(5.0, 2.0), (None, None), (5.0, 2.0), (5.0, 2.0)],
                         "no key: read by its stamps; the count 0: unmeasured; a bool: not a count; a count: measured")

    def test_state_log_pair_breaks_at_a_machine_cut(self):
        """Review find (2026-09-10): a cut turn's `working` row was closed by the RESUMED turn's `waiting`, so
        the interval spanned the outage and the redo. A machineCut row ends the open pair unmeasured."""
        lines = [json.dumps(r) for r in (
            {"t": 1000, "state": "working"}, {"t": 1300.5, "machineCut": "restart"},
            {"t": 1400, "state": "working"}, {"t": 1410, "state": "waiting"})]
        sl, cuts = rm.state_log_turns(lines)
        self.assertEqual([(x["fedT"], x["feedToResultS"]) for x in sl], [(1400, 10.0)])
        self.assertEqual(cuts, {"restart": 1})


class BootJoin(unittest.TestCase):
    def test_a_cut_without_a_boot_row_does_not_take_the_next_restarts_boot(self):
        rows = [{"t": 1000, "cutTurns": [], "stopped": 1},                       # a legacy cut: no boot row ever followed
                {"t": 2000, "cutTurns": [{"sid": SID, "name": "web"}], "stopped": 1},
                {"t": 2003, "bootSettled": True, "firstServe": 2003.5, "reconcileDone": 2003.6, "settleS": 0.1},   # legacy boot: no prevCutT
                {"t": 3000, "cutTurns": [], "stopped": 1},
                {"t": 3002, "bootSettled": True, "firstServe": 3002.5, "reconcileDone": 3002.6, "settleS": 0.1,
                 "prevCutT": 3000, "outageS": 2.5}]
        rs = rm.parse_restarts(rows)
        self.assertEqual([(r["t"], (r.get("boot") or {}).get("t")) for r in rs], [(1000, None), (2000, 2003), (3000, 3002)])
        self.assertEqual(rs[1]["boot"]["outageS"], 3.5, "computed from firstServe when the boot row has no outageS")

    def test_rotated_predecessor_is_read_first(self):
        state = Path(tempfile.mkdtemp())
        _write(state, "turns.jsonl.1", [{"t": 1, "sid": SID}])
        _write(state, "turns.jsonl", [{"t": 2, "sid": SID}])
        rows, note = rm._read_jsonl(state / "turns.jsonl")
        self.assertEqual([r["t"] for r in rows], [1, 2])
        self.assertEqual(note["rows"], 2)


class Windows(unittest.TestCase):
    def test_week_bounds_follow_local_midnight_across_a_daylight_saving_change(self):
        """Review find (2026-09-10): seven times 86400 seconds from the anchor drifted an hour off local
        midnight after a clock change; weeks are counted in local dates."""
        la = "America/Los_Angeles"          # clocks fall back on 2026-11-01
        s, e = rm.bucket_bounds("week of 2026-10-29", "week", la)
        self.assertEqual(e - s, 7 * 86400 + 3600, "the week holds the extra hour and still ends at local midnight")
        self.assertEqual(rm.local_date(e, la), "2026-11-05")
        self.assertEqual(rm.bucket_key(rm.day_start("2026-11-04", la) + 12 * 3600, "week", "2026-10-29", la), "week of 2026-10-29")
        self.assertEqual(rm.bucket_key(rm.day_start("2026-11-05", la) + 60, "week", "2026-10-29", la), "week of 2026-11-05")

    def test_bucket_keys_days_and_weeks(self):
        self.assertEqual(rm.bucket_key(D0 + 10, "day", "2026-09-10", TZ), "2026-09-10")
        self.assertEqual(rm.bucket_key(D0 + 86400 * 6 + 10, "week", "2026-09-10", TZ), "week of 2026-09-10")
        self.assertEqual(rm.bucket_key(D0 + 86400 * 7, "week", "2026-09-10", TZ), "week of 2026-09-17")
        self.assertEqual(rm.bucket_key(D0 - 10, "week", "2026-09-10", TZ), "week of 2026-09-03", "before the anchor buckets backwards")
        s, e = rm.bucket_bounds("week of 2026-09-10", "week", TZ)
        self.assertEqual((s, e), (D0, D0 + 7 * 86400))
        s, e = rm.bucket_bounds("2026-09-10", "day", TZ)
        self.assertEqual((s, e), (D0, D0 + 86400))

    def test_sample_cap_strides_evenly(self):
        self.assertEqual(rm._cap(list(range(10)), cap=5), [0.0, 2.0, 4.0, 6.0, 8.0])
        self.assertEqual(rm._cap([1, 2], cap=5), [1.0, 2.0])

    def test_stats(self):
        self.assertEqual(rm.stats([]), {"n": 0})
        st = rm.stats([1, 2, 3, 4, 10])
        self.assertEqual((st["n"], st["p50"], st["p90"], st["max"], st["mean"]), (5, 3.0, 10.0, 10.0, 4.0))
        self.assertEqual(rm.stats([True, "x", 2])["n"], 1, "only numbers, never bools or strings")


class Document(unittest.TestCase):
    def setUp(self):
        self.state = Path(tempfile.mkdtemp())
        self.t1, self.t2, self.t3 = _fixture(self.state)

    def test_week_buckets_carry_every_metric(self):
        doc = rm.collect(self.state, kind="week", anchor="2026-09-10", tz=TZ, live=False)
        self.assertEqual(doc["schema"], 1)
        self.assertEqual(doc["window"], {"kind": "week", "anchor": "2026-09-10", "tz": TZ})
        self.assertTrue(doc["live"]["skipped"])
        (b,) = doc["buckets"]
        self.assertEqual(b["key"], "week of 2026-09-10")
        self.assertEqual((b["restarts"], b["cutTurns"], b["cleanRestarts"], b["restartsWithoutCutRow"]), (3, 3, 0, 1))
        self.assertEqual(b["measuredRestarts"], 2, "a boot with no cut row cut an unknown number of turns, not zero")
        self.assertEqual(b["cutTurnsPerRestart"], 1.5, "3 cut turns over the 2 MEASURED restarts (review find)")
        self.assertEqual(b["cutSessions"], {"web": 2, "api": 1})
        self.assertEqual(b["reasons"], {"manager-sigterm": 1, "p2p-update": 1, "(no cut row)": 1})
        self.assertEqual((b["outageS"]["n"], b["outageS"]["max"]), (2, 4.0))
        self.assertEqual((b["settleS"]["n"], b["settleS"]["max"]), (3, 0.3))
        self.assertEqual((b["quietWindows"], b["backstopFires"], b["quietWaitS"]["p50"], b["quietWaitS"]["max"]), (2, 1, 297.0, 900.0))
        self.assertEqual((b["boots"], b["resumedTurns"]), (3, 3))
        self.assertEqual((b["orphansReaped"], b["scopesStopped"], b["duplicateClis"], b["crashHeals"], b["crashLoops"],
                          b["drainLeftClosing"], b["leaseProblems"]), (1, 1, 1, 1, 1, 1, 1))
        self.assertEqual((b["drainUnjoinedCount"], b["drainReapedCount"]), (1, 1))
        self.assertEqual((b["attachedAtBoot"], b["attachedLater"]), (2, 1),
                         "host.attached rows (T315): the sessions a restart kept running under their hosts, and the later attaches")
        self.assertEqual(doc["events"]["byKind"]["host.attached"], 3)
        self.assertEqual(b["redo"], {"turns": 1, "usd": 0.5, "tokens": 3700})
        self.assertEqual(b["turns"], 4, "the self-opened turn counts as a turn; only its latency is unmeasured")
        self.assertEqual((b["latency"]["feedToResultS"]["n"], b["latency"]["feedToResultS"]["max"]), (2, 37.0))
        self.assertEqual(b["latency"]["feedToFirstOutS"]["p50"], 1.0)
        self.assertEqual(b["latency"]["apiS"]["max"], 30.0)
        self.assertEqual((b["stateLogTurns"], b["stateLogLatencyS"]["max"]), (2, 37.0))
        self.assertEqual(b["machineCuts"], {"restart": 1, "crash": 1})
        self.assertEqual(b["spendUsd"], 15.5)
        self.assertEqual(b["samples"]["feedToResultS"], [37.0, 10.0])
        self.assertEqual((b["kernelAtExit"]["rssMb"]["n"], b["kernelAtExit"]["rssMb"]["max"], b["kernelAtExit"]["cpuS"]["max"]),
                         (2, 4096.0, 900.5), "the crash boot has no cut row and so no exit sample")
        self.assertEqual([(k["kind"], k["rssMb"]) for k in doc["kernelSeries"]],
                         [("exit", 4096.0), ("boot", 300.0), ("exit", 2048.0)])
        self.assertEqual(b["samples"]["stateLogS"], [30.0, 37.0])
        self.assertEqual(doc["events"]["byKind"]["reconcile.boot"], 3)
        self.assertEqual(doc["sources"]["stateLogs"], 1)
        self.assertEqual(doc["sources"]["restartCuts"]["rows"], 5)

    def test_day_buckets_and_range(self):
        doc = rm.collect(self.state, kind="day", tz=TZ, live=False, since=D0, until=D0 + 86400)
        self.assertEqual([b["key"] for b in doc["buckets"]], ["2026-09-10"])
        b = doc["buckets"][0]
        self.assertEqual((b["restarts"], b["cutTurns"], b["spendUsd"]), (2, 3, 12.5))
        self.assertEqual(doc["window"]["anchor"], "2026-09-10", "the default anchor is the first restart's day in range")
        full = rm.collect(self.state, kind="day", tz=TZ, live=False)
        self.assertEqual([b["key"] for b in full["buckets"]], ["2026-09-10", "2026-09-12"])
        self.assertEqual(full["buckets"][1]["restartsWithoutCutRow"], 1)

    def test_summary_text_names_the_numbers(self):
        doc = rm.collect(self.state, kind="week", anchor="2026-09-10", tz=TZ, live=False)
        doc["label"] = "TESTHOST"
        text = rm.summary(doc)
        self.assertIn("restart metrics: TESTHOST, week windows", text)
        self.assertIn("week of 2026-09-10", text)
        self.assertIn("restarts 3 · turns cut 3 (1.5 per measured restart) · clean restarts 0 · boots with no cut row 1", text)
        self.assertIn("dates in UTC time", text)
        self.assertIn("quiet windows 2 · wait n=2 p50 297 s p90 900 s max 900 s · backstop fired 1", text)
        self.assertIn("orphans reaped 1 · scopes stopped 1 · duplicate CLIs 1 · crash heals 1 · crash loops 1 · drain left closing 1", text)
        self.assertIn("hosts attached: at boot 2 · later 1", text)
        self.assertIn("continuation notices 3 · redo turns 1 · redo cost $0.50 of $15.50 in the window · redo tokens 3,700", text)
        self.assertIn("feed to result n=2 p50 10.0 s p90 37.0 s", text)
        self.assertIn("machine cuts crash 1, restart 1", text)
        self.assertIn("kernel process at its exits: resident n=2 p50 2048 MB p90 4096 MB max 4096 MB · cpu n=2 p50 300 s", text)
        self.assertIn("live: skipped", text)
        self.assertIn("note: Redo cost", text)
        self.assertNotIn("MISSING", text)

    def test_default_label_is_this_machine_and_nothing_the_user_reads_carries_an_em_dash(self):
        """Two of the user's standing rules for anything they read (the manager's fold, 2026-09-10): the
        hostname is a personal identifier, so the default header names 'this machine' and the hostname
        appears nowhere unless --label passes it; and no em-dash anywhere in the summary."""
        import socket
        # the hostname is pinned to a synthetic one for the read AND for the collect and the summary, so the test reads
        # no real machine string (the module docstring's promise) and cannot fail on a machine named after a token of
        # the document (round 3 of the export's review: a first label of `web` failed it, the fixture's session name)
        with mock.patch.object(socket, "gethostname", return_value="TESTHOST.example"):
            host = (socket.gethostname() or "").split(".")[0]
            doc = rm.collect(self.state, kind="week", anchor="2026-09-10", tz=TZ, live=False)
            text = rm.summary(doc)
            labelled = rm.collect(self.state, kind="week", anchor="2026-09-10", tz=TZ, live=False, label="web box")
            labelled_text = rm.summary(labelled)
        self.assertEqual(host, "TESTHOST")
        self.assertEqual(doc["label"], "this machine")
        self.assertNotIn("host", doc, "no host field at all: the document names itself by label only")
        self.assertIn("restart metrics: this machine, week windows", text)
        self.assertNotIn(host, text)
        self.assertNotIn(host, json.dumps(doc))
        self.assertNotIn("\u2014", text)
        self.assertNotIn("\u2014", json.dumps(doc))
        self.assertIn("restart metrics: web box,", labelled_text)

    def test_no_em_dash_in_any_string_of_the_reader_or_the_report(self):
        """Every string literal of the two modules, docstrings included (--help prints the module docstring's
        first paragraph), is free of em-dashes, by AST, so a new label cannot bring one back."""
        import ast
        for path in (os.path.join(BIN, "romp-restart-metrics"), os.path.join(os.path.dirname(HERE), "scripts", "restart_metrics_report.py")):
            tree = ast.parse(open(path, encoding="utf-8").read())
            offenders = [(n.lineno, n.value[:60]) for n in ast.walk(tree)
                         if isinstance(n, ast.Constant) and isinstance(n.value, str) and "\u2014" in n.value]
            self.assertEqual(offenders, [], "%s carries an em-dash in a string" % os.path.basename(path))
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            rm.main(["--help"])
        self.assertNotIn("\u2014", out.getvalue())

    def test_summary_dates_follow_the_documents_zone(self):
        """Review find (2026-09-10): the window bounds were rendered in the machine's zone, ignoring --tz. A
        zone fourteen hours ahead of UTC puts the anchor's local midnight on the previous UTC day."""
        far = "Pacific/Kiritimati"
        doc = rm.collect(self.state, kind="day", tz=far, live=False, since=rm.day_start("2026-09-10", far),
                         until=rm.day_start("2026-09-11", far))
        text = rm.summary(doc)
        self.assertIn("2026-09-10  (2026-09-10 to 2026-09-10)", text, "the machine's UTC clock would have said 2026-09-09")

    def test_bad_anchor_is_refused_like_the_other_dates(self):
        self.assertEqual(rm.main(["--anchor", "yesterday", "--no-live", "--state", str(self.state)]), 2)

    def test_missing_ledgers_are_said(self):
        empty = Path(tempfile.mkdtemp())
        doc = rm.collect(empty, kind="day", tz=TZ, live=False)
        self.assertEqual(doc["buckets"], [])
        self.assertFalse(doc["sources"]["restartCuts"]["present"])
        text = rm.summary(doc)
        self.assertIn("MISSING ledgers", text)
        self.assertIn("restart-cuts.jsonl", text)
        self.assertIn("no rows in range", text)

    def test_main_json_and_text(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = rm.main(["--json", "--window", "week", "--anchor", "2026-09-10", "--tz", TZ, "--no-live", "--state", str(self.state)])
        self.assertEqual(rc, 0)
        doc = json.loads(out.getvalue())
        self.assertEqual(doc["buckets"][0]["restarts"], 3)
        out = io.StringIO()
        with redirect_stdout(out):
            rc = rm.main(["--no-live", "--state", str(self.state), "--tz", TZ])
        self.assertEqual(rc, 0)
        self.assertIn("restart metrics", out.getvalue())
        self.assertEqual(rm.main(["--since", "not-a-date", "--no-live", "--state", str(self.state)]), 2)


def _plant_free_text(state: Path):
    """The restart document's free-text fields on the fixture's rows, as ONE-TOKEN values: a cut row's drainError
    and reasonError (exception messages) and an event row's text (problem_row's prose). A longer message folds to
    `other` by the grammar alone; a one-token message of at most 32 characters passes it, so only the denylist
    keeps the fields out (the export's review, 2026-09-18). Planted on the second cut row and the drain event, so
    no count the other cases assert moves."""
    for name, match, fields in (("restart-cuts.jsonl", ("reason", "p2p-update"), {"drainError": "TESTHOST", "reasonError": "boom42"}),
                                ("session-events.jsonl", ("kind", "drain.unjoined"), {"text": "TESTHOST"})):
        rows = (state / name).read_text().splitlines()
        out = []
        for ln in rows:
            try:
                r = json.loads(ln)
            except ValueError:
                out.append(ln)
                continue
            if isinstance(r, dict) and r.get(match[0]) == match[1]:
                r.update(fields)
            out.append(json.dumps(r))
        (state / name).write_text("\n".join(out) + "\n")


# The three opaque ids of the user's conversation objects a host fault row relays: kernel/session_host.py's
# hook-self-answered line carries them, sdk_backend forwards the line through problem_row into session-events.jsonl,
# and events.recent is those rows raw. Each fits the ident grammar, the tool use's id at its 32-character limit,
# so only the denylist keeps them out (the fourth review round, 2026-09-18).
HOST_FAULT_IDS = {"requestId": "req_7_c0ffee", "callbackId": "hook_3", "toolUseId": "toolu_01Ab3dEf5gHi7jKl9mNo1pQr3s"}


def _plant_host_fault_row(state: Path, t):
    """One host.hook-self-answered row in the relay's shape (append_session_event: t, pid, kind, sid, name, the prose
    under text, then the host line's own fields), appended to the fixture so no count the other cases assert moves."""
    row = {"t": t, "pid": 102, "kind": "host.hook-self-answered", "sid": SID, "name": "web",
           "text": "the host answered a PreToolUse hook for web itself after 4.5 s with no kernel attached",
           "event": "PreToolUse", "parkedS": 4.5}
    row.update(HOST_FAULT_IDS)
    with open(state / "session-events.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")


class PublicForm(unittest.TestCase):
    """`--json --public` (2026-09-18): the document's paste-safe form through cli/perf_public.py, the shape `romp perf
    export --public` writes. The fixture's session names (web, api) ride the cut rows' cutSessions lists and the
    buckets' cutSessions counts, the sids and pids ride the events, the label is free text, and a cut row's
    drainError and reasonError and an event row's text are planted as one-token messages (_plant_free_text), and one
    case appends a host fault row carrying the three opaque conversation ids (_plant_host_fault_row); none may
    survive, while the counts they stood beside do. Before the flag, argparse refused `--public`. Since 2026-09-18
    every ABSOLUTE clock stamp goes too, whatever its key (`t`, the second of each restart, boot, quiet window,
    kernel-series point and event, and the same stamps under other names: auditT, firstServe, reconcileDone, a quiet
    window's since and restartT, the range's since and until), the live block's port goes, and the kernel's uptime is
    rounded down to whole minutes; the bucket bounds (start, end: day or week boundaries in the chosen zone) are the one
    stamp kept. The rule (round 3): the public form is paste-safe, not unlinkable. Durations (outageS, settleS, waitedS)
    and every count and distribution stay, so two documents from one machine remain linkable through them by design."""

    def setUp(self):
        self.state = Path(tempfile.mkdtemp())
        _fixture(self.state)
        _plant_free_text(self.state)

    def _public(self, *extra):
        out = io.StringIO()
        with redirect_stdout(out), mock.patch.object(pp, "machine_probes", return_value=SYNTHETIC_PROBES):
            rc = rm.main(["--json", "--public", "--anchor", "2026-09-10", "--tz", TZ, "--no-live", "--state", str(self.state)] + list(extra))
        self.assertEqual(rc, 0)
        return json.loads(out.getvalue())

    def test_no_session_name_id_pid_scope_or_label_survives_and_the_counts_do(self):
        doc = self._public("--label", "TESTHOST")
        text = json.dumps(doc)
        for planted in ('"web"', '"api"', SID, SID2, SID[:8], "TESTHOST", "this machine", "cutSessions", '"label"', '"pids"', '"sid"', '"name"',
                        "boom42", "drainError", "reasonError", '"text"'):
            self.assertNotIn(planted, text, planted)     # the names as JSON tokens: `api` is a substring of the apiS latency key
        self.assertIs(doc["public"], True)
        self.assertEqual(doc["schema"], 1)
        self.assertNotIn("generatedAt", doc)
        first = doc["restarts"][0]
        self.assertEqual((first["cutTurns"], first["stopped"], first["reason"]), (2, 5, "other"), "the count stays, the names go, free text folds")
        self.assertNotIn("pid", first)
        self.assertEqual(doc["restarts"][1]["reason"], "p2p-update", "a reason that is an identifier stays")
        self.assertEqual(sorted(k for k in doc["restarts"][1] if k in ("drainError", "reasonError", "stopped")), ["stopped"],
                         "the two exception-message fields go whatever their value; the count beside them stays")
        drains = [e for e in doc["events"]["recent"] if e.get("kind") == "drain.unjoined"]
        self.assertEqual(drains, [{"kind": "drain.unjoined", "inflight": 1, "reaped": True}],
                         "the event row's prose and its stamp go, its flat counters stay")
        self.assertEqual(_keys_named(doc, "t"), [], "no row keeps its wall-clock second")
        self.assertEqual(len(doc["restarts"]), 3, "the rows themselves stay, in order")
        self.assertEqual(doc["restarts"][0]["boot"]["settleS"], 0.2)
        self.assertEqual(rm.public_form({"restarts": [{"drainError": "boom", "reasonError": "TESTHOST", "stopped": 1}],
                                         "events": {"recent": [{"kind": "crash.heal", "text": "boom", "attempt": 1}]}}),
                         {"restarts": [{"stopped": 1}], "events": {"recent": [{"kind": "crash.heal", "attempt": 1}]}, "public": True})
        b = [x for x in doc["buckets"] if x["key"] == "2026-09-10"][0]
        self.assertEqual((b["restarts"], b["cutTurns"], b["cleanRestarts"]), (2, 3, 0))
        self.assertEqual(b["reasons"], {"manager-sigterm": 1, "p2p-update": 1})
        self.assertEqual(doc["window"], {"kind": "day", "anchor": "2026-09-10", "tz": TZ})
        self.assertEqual(sorted(doc["sources"]["turns"]), ["present", "rows"], "the file NAME is a path key and goes")
        recent = doc["events"]["recent"]
        self.assertTrue(recent and all("sid" not in e and "name" not in e and "pids" not in e for e in recent), recent)
        # the host.attached rows carry hostPid and cliPid, the stale-heartbeat row a leasePid: a pid under any spelling
        # goes wherever it sits (a substring test over the JSON, so a nested one is caught too)
        for spelled in ("hostPid", "cliPid", "leasePid", '"pid"', '"ppid"', "managerPid"):
            self.assertNotIn(spelled, text, spelled)
        attached = [e for e in recent if e.get("kind") == "host.attached"]
        self.assertEqual(len(attached), 3, "the rows stay, their pids go")
        self.assertEqual(attached[0], {"kind": "host.attached", "boot": True, "replayFrom": 3}, "the row's second goes with its pids")
        self.assertEqual(doc["events"]["byKind"]["reconcile.duplicate-cli"], 1)
        self.assertEqual(doc["notes"], ["other", "other"], "prose is not an identifier")
        problems = pp.paste_problems(doc, planted=(SID, SID2, "TESTHOST", "this machine", "boom42"))   # the walk's probes are substrings
        self.assertEqual(problems, [], "%d leak(s):\n  %s" % (len(problems), "\n  ".join(map(str, problems))))

    def test_no_absolute_clock_stamp_survives_except_the_bucket_bounds(self):
        """The rule (round 3, 2026-09-18): the public form removes every ABSOLUTE clock stamp under whatever key. Denying
        `t` alone left the same stamps under other names: a quiet window's restartT was the released restart's t
        verbatim, its since the parked stamp (since plus waitedS is the row's t), a restart's auditT, a boot's firstServe
        and reconcileDone (firstServe minus outageS is the denied cut's t), the range's since and until. Pinned as the
        PROPERTY, not as key names: a walk over the printed document finds no numeric leaf inside an epoch window
        (EPOCH_WINDOWS) outside buckets[].start and buckets[].end, the day or week bounds in the chosen zone, coarse and
        documented (they do reveal the zone's UTC offset). Durations stay, and so does a large number outside the
        windows, a measurement. Fails before: fifteen leaves survived."""
        doc = self._public("--since", "2026-09-10", "--until", "2026-09-13")
        bounds = sorted("buckets/%d/%s" % (i, k) for i in range(len(doc["buckets"])) for k in ("start", "end"))
        self.assertTrue(bounds, "the fixture fills buckets")
        survivors = _stamps(doc)
        self.assertEqual(sorted(p for p, _ in survivors), bounds,
                         "an absolute stamp survives outside the bucket bounds (a large number outside the epoch windows is a "
                         "measurement the public form keeps on purpose and is not listed here):\n  %s"
                         % "\n  ".join("%s = %r" % s for s in survivors))
        for i, b in enumerate(doc["buckets"]):
            self.assertEqual((b["end"] - b["start"]) % 86400, 0, "a bound pair spans whole days")
        # the raw document's stamps (every number inside an epoch window off the bucket bounds) equal no number the public form keeps
        out = io.StringIO()
        with redirect_stdout(out):
            rm.main(["--json", "--anchor", "2026-09-10", "--tz", TZ, "--no-live", "--state", str(self.state),
                     "--since", "2026-09-10", "--until", "2026-09-13"])
        raw = json.loads(out.getvalue())
        raw_stamps = {v for p, v in _stamps(raw) if p not in bounds}
        self.assertGreaterEqual(len(raw_stamps), 15, "the raw document carries the stamps the public form must not")
        kept = {v for p, v in _numbers(doc) if p not in bounds}
        self.assertEqual(raw_stamps & kept, set(), "a raw stamp survives under some key")
        # durations and counts stay: they are the data, and two documents from one machine stay linkable through them
        self.assertEqual(doc["restarts"][0]["boot"]["outageS"], 2.5)
        self.assertEqual(doc["restarts"][0]["boot"]["settleS"], 0.2)
        self.assertEqual([q["waitedS"] for q in doc["quietWindows"]], [297, 900])
        self.assertEqual([q["cutTurns"] for q in doc["quietWindows"]], [2, 1], "the joined restart's count stays, its stamp goes")
        self.assertEqual(doc["range"], {}, "since and until are user-typed day bounds the buckets already carry")
        self.assertEqual(doc["buckets"][0]["start"], D0, "the bucket bounds are the documented exception")
        for key in ("auditT", "firstServe", "reconcileDone", "restartT", "prevCutT", "since", "until"):
            self.assertIn(key, pp.DENY_KEYS, key)
        self.assertNotIn(("since",), pp.DENY_PATHS, "since is denied by key now, at any depth")

    def test_week_buckets_keep_distinct_keys(self):
        # the raw key is "week of YYYY-MM-DD", which the ident grammar folds to `other`, so every week would collapse
        # into one unreadable bucket; the public form spells it week-of-YYYY-MM-DD before the fold
        doc = self._public("--window", "week")
        keys = [b["key"] for b in doc["buckets"]]
        self.assertTrue(keys and all(re.fullmatch(r"week-of-\d{4}-\d{2}-\d{2}", k) for k in keys), keys)
        self.assertEqual(len(set(keys)), len(keys))
        self.assertEqual(doc["buckets"][0]["restarts"], 3)
        self.assertEqual(doc["window"]["kind"], "week")

    def test_the_generation_second_goes_with_generated_at(self):
        # live.t is generatedAt under another key, to the second, and goes with every other `t` (the denylist's key);
        # the kernel's uptime (a duration the counters are read against) stays, rounded down to whole minutes (to the
        # second, beside the paste time, it placed the boot within a minute, a stamp constant for the life of the
        # process), its start stamp and pid go; the port goes too (a kernel on a non-default ROMP_KERNEL_PORT made it a
        # per-install constant no reader needs; round 3)
        out = rm.public_form({"schema": 1, "generatedAt": 1757500000, "label": "TESTHOST",
                              "live": {"t": 1757500000, "platform": "Linux", "sessionsCounted": 2,
                                       "kernel": {"port": 29855, "pid": 4242, "started": 1757400000.0, "uptimeS": 100000.0,
                                                  "kernelSha": "0123456789abcdef0123456789abcdef01234567", "bootId": "b1"}}})
        self.assertEqual(out, {"schema": 1, "public": True,
                               "live": {"platform": "Linux", "sessionsCounted": 2, "kernel": {"uptimeS": 99960}}})
        self.assertIn("port", pp.DENY_KEYS)
        self.assertEqual(rm.public_form({"live": {"skipped": True}})["live"], {"skipped": True})

    def test_the_raw_document_still_carries_the_names_so_the_flag_is_what_removes_them(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = rm.main(["--json", "--anchor", "2026-09-10", "--tz", TZ, "--no-live", "--state", str(self.state)])
        self.assertEqual(rc, 0)
        doc = json.loads(out.getvalue())
        self.assertEqual(doc["restarts"][0]["cutSessions"], ["web", "api"])
        self.assertEqual((doc["restarts"][1]["drainError"], doc["restarts"][1]["reasonError"]), ("TESTHOST", "boom42"))
        self.assertEqual([e["text"] for e in doc["events"]["recent"] if e.get("kind") == "drain.unjoined"], ["TESTHOST"])
        self.assertNotIn("public", doc)

    def test_the_opaque_ids_a_host_fault_row_relays_go_and_its_event_and_wait_stay(self):
        """A session host's hook-self-answered line carries requestId, callbackId and toolUseId, opaque ids of the
        user's conversation objects (a hook request, a hook callback, a tool use); the kernel relays the line into
        session-events.jsonl through problem_row, and events.recent is those rows raw. Each id is one token of at
        most 32 characters, so the grammar keeps it and only the denylist removes it (the fourth review round,
        2026-09-18: a pre-existing pass-through this verb owns). Fails before: the three keys and their values were
        printed verbatim in the public form. The row itself stays, with its hook event and its wait."""
        for key, value in HOST_FAULT_IDS.items():
            self.assertTrue(pp.IDENT.fullmatch(value), "%s fits the grammar, so only the denylist can keep it out" % key)
        self.assertEqual(len(HOST_FAULT_IDS["toolUseId"]), 32, "a tool use's id sits at the grammar's length limit")
        _plant_host_fault_row(self.state, D0 + 7200 + 120)
        doc = self._public()
        text = json.dumps(doc)
        for key, value in HOST_FAULT_IDS.items():
            self.assertNotIn('"%s"' % key, text, key)
            self.assertNotIn(value, text, key)
        rows = [e for e in doc["events"]["recent"] if e.get("kind") == "host.hook-self-answered"]
        self.assertEqual(rows, [{"kind": "host.hook-self-answered", "event": "PreToolUse", "parkedS": 4.5}],
                         "the row stays with its hook event and its wait; the ids, the prose, the pid and the stamp go")
        self.assertEqual(doc["events"]["byKind"]["host.hook-self-answered"], 1)
        for key, value in HOST_FAULT_IDS.items():
            self.assertTrue(pp.denied(key, value), key)
            self.assertIn(key, pp.DENY_KEYS, key)
        # the raw document carries all three, so the flag is what removes them
        out = io.StringIO()
        with redirect_stdout(out):
            rm.main(["--json", "--anchor", "2026-09-10", "--tz", TZ, "--no-live", "--state", str(self.state)])
        raw = [e for e in json.loads(out.getvalue())["events"]["recent"] if e.get("kind") == "host.hook-self-answered"]
        self.assertEqual([(e["requestId"], e["callbackId"], e["toolUseId"]) for e in raw],
                         [(HOST_FAULT_IDS["requestId"], HOST_FAULT_IDS["callbackId"], HOST_FAULT_IDS["toolUseId"])])

    def test_a_32_hex_token_on_an_event_row_refuses_the_print_the_way_the_export_refuses_the_write(self):
        """events.recent is the one place raw ledger rows pass through, and a 32-hex token fits the identifier grammar,
        so the fold keeps it as a key and as a value; the identifier scan does not know it. `romp perf export` refuses
        such a document through check_document, whose three sources are the identifier scan, the paste walk and the
        denylist walk (which refuses what the fold would have dropped, folded or coarsened as "the public form still
        fails the denylist"); this verb ran the scan alone
        and PRINTED the token (the export PR's closing check, 2026-09-18). Both verbs now run
        check_document: the print is refused, exit 1, nothing on stdout, and the refusal names the kind and the key
        path of the shallowest finding (a value's own path; a key's the dict holding it) and never the token. Fails
        before: the public run returned 0 with both tokens in its document. No writer today carries a nested object or
        such a token on a session-events row; the fixture is the defensive case the check exists for."""
        key_token, value_token = "d" * 32, "e" * 32
        for token in (key_token, value_token):
            self.assertTrue(pp.IDENT.fullmatch(token), "the token fits the grammar, so the fold keeps it")
        self.assertEqual(pp.fold({"detail": {key_token: 1, "token": value_token}}), {"detail": {key_token: 1, "token": value_token}})

        def plant(detail, t):
            row = {"t": t, "pid": 102, "kind": "host.hook-self-answered", "sid": SID, "name": "web",
                   "event": "PreToolUse", "parkedS": 1.0, "detail": detail}
            with open(self.state / "session-events.jsonl", "a") as f:
                f.write(json.dumps(row) + "\n")

        def run(*flags):
            err, out = io.StringIO(), io.StringIO()
            with mock.patch("sys.stderr", err), redirect_stdout(out), \
                    mock.patch.object(pp, "machine_probes", return_value=SYNTHETIC_PROBES):
                rc = rm.main(["--json"] + list(flags) + ["--anchor", "2026-09-10", "--tz", TZ, "--no-live", "--state", str(self.state)])
            return rc, out.getvalue(), err.getvalue()

        def planted_rows(raw_text):
            return [i for i, e in enumerate(json.loads(raw_text)["events"]["recent"]) if "detail" in e]

        # the value alone: named by its own path
        plant({"token": value_token}, D0 + 7200 + 130)
        rc, raw, err = run()
        self.assertEqual((rc, err), (0, ""), "the raw document is not checked")
        self.assertIn(value_token, raw, "the raw run carries the value, so the flag is what refuses it")
        (i,) = planted_rows(raw)
        rc, out, err = run("--public")
        self.assertEqual(rc, 1)
        self.assertEqual(out, "", "nothing printed")
        self.assertEqual(err, "romp restart-metrics: refused: the public form still fails the walk (a 32-hex token, "
                              "the value at events/recent/%d/detail/token); nothing printed\n" % i)
        # a second row with the token as a key: the dict holding it is one component shallower than the first row's
        # value, so the key finding is the one named, whichever row came first
        plant({key_token: 1, "token": value_token}, D0 + 7200 + 140)
        rc, raw, err = run()
        self.assertEqual(rc, 0)
        i, j = planted_rows(raw)
        self.assertIn('"%s": 1' % key_token, raw, "the raw run carries the key")
        rc, out, err = run("--public")
        self.assertEqual(rc, 1)
        self.assertEqual(out, "", "nothing printed")
        self.assertEqual(err, "romp restart-metrics: refused: the public form still fails the walk (a 32-hex token, "
                              "a key under events/recent/%d/detail); nothing printed\n" % j)
        for token in (key_token, value_token):
            self.assertNotIn(token, out + err, "the token never reaches stdout or stderr")

    def test_a_fifo_at_the_private_strings_path_is_no_list_said_on_stderr_and_the_public_print_returns_at_once(self):
        """The third of the three callers of the shared list reader (perf_public.private_strings): with a fifo at
        ROMP_PRIVATE_STRINGS the public print goes out with no list, as before, and now says so in one stderr line naming the
        path and the reason (pp.LIST_UNREADABLE, the fourth review round, 2026-09-19), where the list turned itself off in
        silence (extra4-1). The verb runs as a child under a pinned hostname, a synthetic HOME and login and no kernel, and
        THE CHILD IS RUN UNDER A TIMEOUT AND HARD-KILLED WHEN IT EXPIRES: a fifo at a user-named path is where a plain open
        hung this verb (the second round), so a plain wait would take the runner with it. Fails before: stderr was empty."""
        fifo = str(self.state / "private-strings.fifo")
        os.mkfifo(fifo)
        xdg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, xdg, True)
        env = {k: v for k, v in os.environ.items() if not k.startswith("ROMP_") and k not in ("CLAUDE_CODE_SESSION_ID", "XDG_CONFIG_HOME")}
        env.update({"XDG_STATE_HOME": xdg, "HOME": "/home/tester", "USER": "tester", "LOGNAME": "tester", "ROMP_KERNEL_PORT": "1",
                    "ROMP_PRIVATE_STRINGS": fifo})
        child = ("import runpy, socket, sys; socket.gethostname = lambda: 'TESTHOST.example'; sys.argv = sys.argv[1:]; "
                 "runpy.run_path(sys.argv[0], run_name='__main__')")
        try:
            r = subprocess.run([sys.executable, "-c", child, os.path.join(BIN, "romp-restart-metrics"), "--json", "--public", "--anchor", "2026-09-10",
                                "--tz", TZ, "--no-live", "--state", str(self.state)], capture_output=True, text=True, timeout=8, env=env)
        except subprocess.TimeoutExpired:
            self.fail("the restart-metrics child hung on the fifo at the private-strings path (killed after 8 s)")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "romp: no private-strings list was read from %s (a fifo); no listed string is checked\n" % fifo,
                         "the list turning itself off is said, naming the path and the reason")
        self.assertIs(json.loads(r.stdout)["public"], True, "and the public document was printed")

    def test_a_listed_pointed_value_a_spend_bucket_spells_refuses_the_public_print_naming_the_path_and_the_list_line(self):
        """The third road of the numeric floor (the comment at pp.NUMERIC_PROBE_MIN_DIGITS; the closing delta of 2026-09-19).
        spend.json's usd for a day is a float that reaches the public document as buckets/N/spendUsd (spend_by_day, then
        round(x, 4)), so a listed private string that is a pointed value of eight digits, 1234.5678, refuses the print as the
        export and the upload refuse it: rc 1, the one stderr line naming the kind, the value's path and line 1 of the list
        with the remedy, the digits in no output, nothing printed; the same document with no list prints, the value in its
        bucket. The child runs under a pinned hostname, a synthetic HOME and login and no kernel, as the fifo case does, and
        under a timeout. The export and upload roads pin this value in their own modules; this road shares check_document
        and passed by inheritance at the closing delta, unpinned, so a road-specific change here would have gone unseen.
        Fails at a086ced5a, whose longest-run floor did not apply an entry of this shape to any number: rc 0, the value
        printed."""
        (self.state / "spend.json").write_text(json.dumps({"days": {"2026-09-10": {"usd": 1234.5678, "turns": 30}}, "hours": {}}))
        xdg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, xdg, True)
        listed = os.path.join(xdg, "private-strings.txt")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("1234.5678\n")
        env = {k: v for k, v in os.environ.items() if not k.startswith("ROMP_") and k not in ("CLAUDE_CODE_SESSION_ID", "XDG_CONFIG_HOME")}
        env.update({"XDG_STATE_HOME": xdg, "HOME": "/home/tester", "USER": "tester", "LOGNAME": "tester", "ROMP_KERNEL_PORT": "1"})
        child = ("import runpy, socket, sys; socket.gethostname = lambda: 'TESTHOST.example'; sys.argv = sys.argv[1:]; "
                 "runpy.run_path(sys.argv[0], run_name='__main__')")
        argv = [sys.executable, "-c", child, os.path.join(BIN, "romp-restart-metrics"), "--json", "--public", "--anchor", "2026-09-10",
                "--tz", TZ, "--no-live", "--state", str(self.state)]
        r = subprocess.run(argv, capture_output=True, text=True, timeout=20, env=dict(env, ROMP_PRIVATE_STRINGS=listed))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "romp restart-metrics: refused: a string this machine knows (private string) survives as the value at "
                                   "buckets/0/spendUsd; edit line 1 of the private-strings list or that value; nothing printed\n")
        self.assertEqual(r.stdout, "", "nothing printed")
        for digits in ("1234.5678", "12345678", "1234"):
            self.assertNotIn(digits, r.stdout + r.stderr, "the value is never printed")
        r = subprocess.run(argv, capture_output=True, text=True, timeout=20, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "", "no list, nothing said")
        self.assertEqual(json.loads(r.stdout)["buckets"][0]["spendUsd"], 1234.5678, "without the list the value is a measurement like any other")

    def test_a_listed_entry_with_an_exponent_beyond_any_double_prints_under_a_finite_address_space_with_one_line_and_no_traceback(self):
        """The refusable input of the closing re-run (2026-09-19, finding 5) through the third caller of the shared list reader:
        ROMP_PRIVATE_STRINGS naming a list of 1e-1000000000 alone, the entry whose plain decimal expansion asked for a billion
        digits (format(Decimal(text), 'f') writes about as many digits as the exponent, so the work was exponential in an
        entry's length while PRIVATE_STRINGS_MAX bounded only the file) and took `romp perf export --public` and `romp perf
        upload` down with an uncaught MemoryError at b3df460d5; this verb shares machine_probes and died the same way. The
        list's second line is 1e-10000000000000000000, whose exponent (10**19) the decimal module refuses to construct (past
        decimal.MAX_EMAX, about 1e18): the bound's first cut asked Decimal(text).adjusted() bare and this verb died on it with
        an uncaught InvalidOperation too (the re-run's verification, rc 1). Now, over the ordinary fixture: rc 0, stdout
        parses as JSON and is the public document, stderr exactly the one skip line (pp.LIST_EXPANSION_SKIPPED: 2 of 2, list
        lines 1 and 2, the bound 324) and Traceback, MemoryError and InvalidOperation in neither stream. THE CHILD RUNS UNDER A
        FINITE ADDRESS-SPACE CAP (RLIMIT_AS, 1.5 GiB, set by the child itself in its prelude before the verb's code runs; the
        report's reproduction used 768 MiB, ulimit -v 786432, which the free-threaded 3.14t interpreter maps past before any
        code runs, and 2 GiB lets the billion-digit expansion complete, so the export module's cap and this one are 1.5 GiB
        on every interpreter, the reasons measured at the export module's ADDRESS_SPACE_CAP), so with the bound removed the
        input fails fast under the cap with a MemoryError rather than allocating without bound. The export road pins the same
        list in its own module;
        the upload road in its. Dropping `and expansion_bounded(text)` from number_spellings' guard reds this with rc 1 and
        the traceback; the try/except removed from expansion_bounded reds it with rc 1 and InvalidOperation in stderr."""
        xdg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, xdg, True)
        listed = os.path.join(xdg, "private-strings.txt")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("1e-1000000000\n1e-10000000000000000000\n")
        env = {k: v for k, v in os.environ.items() if not k.startswith("ROMP_") and k not in ("CLAUDE_CODE_SESSION_ID", "XDG_CONFIG_HOME")}
        env.update({"XDG_STATE_HOME": xdg, "HOME": "/home/tester", "USER": "tester", "LOGNAME": "tester", "ROMP_KERNEL_PORT": "1",
                    "ROMP_PRIVATE_STRINGS": listed})
        cap = 1536 * 1024 * 1024                                            # the export module's ADDRESS_SPACE_CAP, and why
        child = ("import resource, runpy, socket, sys; resource.setrlimit(resource.RLIMIT_AS, (%d, %d)); "
                 "socket.gethostname = lambda: 'TESTHOST.example'; sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')" % (cap, cap))
        argv = [sys.executable, "-c", child, os.path.join(BIN, "romp-restart-metrics"), "--json", "--public", "--anchor", "2026-09-10",
                "--tz", TZ, "--no-live", "--state", str(self.state)]
        r = subprocess.run(argv, capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r.returncode, 0, r.stdout[-500:] + r.stderr)
        self.assertEqual(r.stderr, pp.LIST_EXPANSION_SKIPPED % (2, 2, "list lines 1 and 2", 324) + "\n", "the skip line and nothing else")
        for word in ("Traceback", "MemoryError", "InvalidOperation", "1e-1000000000", "1e-10000000000000000000"):
            self.assertNotIn(word, r.stdout + r.stderr, word)
        self.assertIs(json.loads(r.stdout)["public"], True, "and the public document was printed")

    def test_a_listed_exponent_written_entry_refuses_the_public_print_when_its_plain_digits_sit_in_a_key_or_a_string(self):
        """The third road of the key and string fix (the closing re-run of 2026-09-19, finding 1; its verification found this
        road unpinned, where the export and upload roads pin theirs and the precedent above says a road that passes by
        inheritance lets a road-specific change go unseen). An event row whose kind is zz0.000015 survives the fold as the
        key events/byKind/zz0.000015 (and as the string events/recent/N/kind), and a list of 1.5e-05 alone refuses the print
        through the entry's plain expansion: rc 1, stdout empty, stderr exactly the refusal naming the kind, a key under
        events/byKind and line 1 of the list with the remedy, the digits and the entry's text in no output; the control, the
        same state with the list 1e+16, prints (rc 0, the public document, the key in it). On a second fixture state (the
        check names one finding, so the string road is not asked beside the key), a cut row whose reason is 0.000015 survives
        as the string restarts/2/reason (the fixture's two cut rows before it) and is refused the same way naming the value.
        The child runs as the pointed value case does: a pinned hostname, a synthetic HOME and login, no kernel, under a
        timeout. Fails before the fix: rc 0 with the key printed (the expansion was applied to numbers alone)."""
        t1 = D0 + 3600
        with open(self.state / "session-events.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": t1 + 6, "pid": 101, "kind": "zz0.000015", "sid": SID, "name": "web"}) + "\n")
        xdg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, xdg, True)
        listed = os.path.join(xdg, "private-strings.txt")
        env = {k: v for k, v in os.environ.items() if not k.startswith("ROMP_") and k not in ("CLAUDE_CODE_SESSION_ID", "XDG_CONFIG_HOME")}
        env.update({"XDG_STATE_HOME": xdg, "HOME": "/home/tester", "USER": "tester", "LOGNAME": "tester", "ROMP_KERNEL_PORT": "1",
                    "ROMP_PRIVATE_STRINGS": listed})
        child = ("import runpy, socket, sys; socket.gethostname = lambda: 'TESTHOST.example'; sys.argv = sys.argv[1:]; "
                 "runpy.run_path(sys.argv[0], run_name='__main__')")
        argv = [sys.executable, "-c", child, os.path.join(BIN, "romp-restart-metrics"), "--json", "--public", "--anchor", "2026-09-10",
                "--tz", TZ, "--no-live", "--state", str(self.state)]
        refusal = ("romp restart-metrics: refused: a string this machine knows (private string) survives as %s; "
                   "edit line 1 of the private-strings list or that %s; nothing printed\n")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("1.5e-05\n")
        r = subprocess.run(argv, capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r.returncode, 1, r.stdout[-500:] + r.stderr)
        self.assertEqual(r.stderr, refusal % ("a key under events/byKind", "key"), "the key, by the entry's plain expansion")
        self.assertEqual(r.stdout, "", "nothing printed")
        for text in ("0.000015", "1.5e-05"):
            self.assertNotIn(text, r.stdout + r.stderr, "the digits and the entry's text reach no output")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("1e+16\n")
        r = subprocess.run(argv, capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r.returncode, 0, r.stdout[-500:] + r.stderr)
        self.assertEqual(r.stderr, "", "the control: an unrelated exponent entry says nothing")
        doc = json.loads(r.stdout)
        self.assertIs(doc["public"], True, "and the public document was printed")
        self.assertIn("zz0.000015", doc["events"]["byKind"], "with the key in it")
        other = Path(tempfile.mkdtemp())                                    # the string road on its own fixture: one finding is named
        self.addCleanup(shutil.rmtree, other, True)
        t2 = D0 + 7200
        _fixture(other)
        with open(other / "restart-cuts.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": t2 + 3000, "pid": 102, "cutTurns": [], "stopped": 1, "unjoined": 0, "reaped": 0,
                                 "watchesArmed": 1, "reason": "0.000015"}) + "\n")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("1.5e-05\n")
        r = subprocess.run(argv[:-1] + [str(other)], capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r.returncode, 1, r.stdout[-500:] + r.stderr)
        self.assertEqual(r.stderr, refusal % ("the value at restarts/2/reason", "value"), "the string value, by the same expansion")
        self.assertEqual(r.stdout, "", "nothing printed")

    def test_an_uptime_no_double_can_hold_from_the_kernels_version_answer_is_null_in_the_public_form_and_raises_nothing(self):
        """The third road of the closing check's HIGH 2 (2026-09-19): live.kernel.uptimeS is GET /version's uptime_s
        (kernel_live), public_form folds it through pp.public_uptime, and that function raised OverflowError on an int float()
        cannot hold (math.isfinite, then the quotient). The shared fold now nulls such an int (pp.finite_number, the rule that
        nulls a NaN) and the coarsening is total over ints, so the public form carries null and no traceback for 10**400,
        -10**400 and 10**5000 (an int already, so the interpreter's digit limit on str-to-int is not in play), an int a double
        holds is rounded exactly, and the folded document is the check's fixed point: perf_export.check_document over it at
        the root, as the verb runs it before the print, finds nothing. This reader's other float-domain sites (float() over
        ledger rows and the /version answer, the MB helpers) take the kernel's own ledgers and answer, never a file a person
        names, and are listed in the closing check's audit with no fix beyond this shared one. Fails with finite_number's int
        arm reverted (10**400 - 40 where None is asserted)."""
        for label, v in (("10**400", 10 ** 400), ("-10**400", -(10 ** 400)), ("10**5000", 10 ** 5000), ("the edge", 2 ** 1024 - 2 ** 970)):
            public = rm.public_form({"live": {"platform": "Linux", "kernel": {"uptimeS": v, "cpuS": 1.5}}})
            self.assertIsNone(public["live"]["kernel"]["uptimeS"], label)
            self.assertEqual(public["live"]["kernel"]["cpuS"], 1.5, label)
            self.assertIs(public["public"], True, label)
            with mock.patch.object(pp, "machine_probes", return_value=SYNTHETIC_PROBES):
                self.assertIsNone(rm.perf_export.check_document(public, Path(tempfile.mkdtemp()), under=(), tail="nothing printed"), label)
        fmax = int(sys.float_info.max)
        held = rm.public_form({"live": {"kernel": {"uptimeS": fmax}}})["live"]["kernel"]["uptimeS"]
        self.assertEqual(held, fmax - fmax % 60, "an int a double holds is rounded down to the minute, exactly")
        self.assertEqual(rm.public_form({"live": {"kernel": {"uptimeS": 3725}}})["live"]["kernel"]["uptimeS"], 3720)

    def test_public_without_json_is_refused(self):
        err = io.StringIO()
        with mock.patch("sys.stderr", err):
            rc = rm.main(["--public", "--no-live", "--state", str(self.state)])
        self.assertEqual(rc, 2)
        self.assertIn("--json --public", err.getvalue())

    def test_a_machine_string_that_survives_the_fold_refuses_the_print(self):
        # a real document has no machine string left after the fold (the label is dropped by the denylist before the
        # scan), so the refusal leg is reached by patching public_form to plant a hostname-shaped key past the fold;
        # the first leg pins that the label alone does not refuse, the third that a value the fold keeps (the
        # window's tz, an identifier) is scanned too, through identifier_hits' value branch
        probes = [("hostname", "testhost")]
        with mock.patch.object(pp, "machine_probes", return_value=probes):
            err, out = io.StringIO(), io.StringIO()
            with mock.patch("sys.stderr", err), redirect_stdout(out):
                rc = rm.main(["--json", "--public", "--anchor", "2026-09-10", "--tz", TZ, "--no-live", "--state", str(self.state),
                              "--label", "TESTHOST"])
            self.assertEqual(rc, 0, "the label is dropped by the denylist before the scan: nothing to refuse")
            self.assertNotIn("TESTHOST", out.getvalue())
            err, out = io.StringIO(), io.StringIO()
            with mock.patch("sys.stderr", err), redirect_stdout(out), \
                    mock.patch.object(rm, "public_form", side_effect=lambda d: dict(rm.perf_public.fold(d), TESTHOST=1)):
                rc = rm.main(["--json", "--public", "--no-live", "--state", str(self.state)])
            self.assertEqual(rc, 1)
            self.assertEqual(out.getvalue(), "", "nothing printed")
            self.assertIn("hostname", err.getvalue())
            self.assertIn("a key under the root", err.getvalue())
            self.assertNotIn("TESTHOST", err.getvalue(), "never the value")
        # a value the fold keeps: the window's tz is an identifier, and a machine named like it is found there
        with mock.patch.object(pp, "machine_probes", return_value=[("hostname", TZ.lower())]):
            err, out = io.StringIO(), io.StringIO()
            with mock.patch("sys.stderr", err), redirect_stdout(out):
                rc = rm.main(["--json", "--public", "--anchor", "2026-09-10", "--tz", TZ, "--no-live", "--state", str(self.state)])
        self.assertEqual(rc, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("(hostname) survives as the value at window/tz; nothing printed", err.getvalue())
        self.assertNotIn(TZ, err.getvalue(), "the value is never printed")


class LiveHelpers(unittest.TestCase):
    """The live reads, on synthetic files and listings: no cgroup, no ps, no kernel is touched."""

    def test_scope_stats_from_synthetic_cgroup_files(self):
        d = Path(tempfile.mkdtemp()) / "romp-session-11111111-4242-1757374800.scope"
        d.mkdir()
        (d / "memory.current").write_text("104857600\n")
        (d / "memory.peak").write_text("209715200\n")
        (d / "cpu.stat").write_text("usage_usec 12500000\nuser_usec 1\nsystem_usec 2\n")
        (d / "cgroup.procs").write_text("4242\n4300\n4301\n")
        s = rm.scope_stats(str(d))
        self.assertEqual((s["sid8"], s["cliPid"], s["memBytes"], s["memPeakBytes"], s["cpuS"], s["procs"]),
                         ("11111111", 4242, 104857600, 209715200, 12.5, 3))
        self.assertEqual(rm.cgroup_scope_dirs(str(d.parent)), [str(d)])

    def test_ps_parsing_trees_and_duplicates(self):
        lines = ["  100     1  1000  0.5 /x/claude --output-format stream-json --resume %s --input-format stream-json" % SID,
                 "  101   100   500  1.0 bash -c tool",
                 "  102   101   250  0.0 sleep 3",
                 "  200     1  2000  2.0 /x/claude --output-format stream-json --resume=%s --input-format stream-json" % SID,
                 "  300     1   900  0.0 /x/claude --output-format stream-json --resume %s --input-format stream-json" % SID2,
                 "  400     1   100  0.0 claude --resume %s" % SID,   # a terminal CLI: no stream-json mark, never romp's
                 "garbage"]
        procs = rm.parse_ps(lines)
        self.assertEqual(len(procs), 6)
        regs = {SID: {"name": "web", "lastSid": SID, "alive": True}, SID2: {"name": "api", "lastSid": SID2, "alive": True}}
        trees = sorted(rm.ps_session_trees(procs, regs), key=lambda t: t["cliPid"])
        self.assertEqual([(t["name"], t["cliPid"], t["procs"], t["memBytes"], t["cpuPct"]) for t in trees],
                         [("web", 100, 3, 1750 * 1024, 1.5), ("web", 200, 1, 2000 * 1024, 2.0), ("api", 300, 1, 900 * 1024, 0.0)])
        self.assertEqual(rm.duplicate_clis(procs, [SID, SID2]), {SID: [100, 200]}, "a terminal CLI (no stream-json mark: someone's own claude, never romp's) never counts")

    def test_kernel_live_unreachable_is_said(self):
        state = Path(tempfile.mkdtemp())
        (state / "serve-port").write_text("1\n")          # nothing listens on port 1
        with mock.patch.dict(os.environ):                 # the suite's dead-port floor comes back after (review find)
            os.environ.pop("ROMP_KERNEL_PORT", None)
            k = rm.kernel_live(state)
        self.assertEqual(k["port"], 1)
        self.assertIn("not reachable", k["error"])


if __name__ == "__main__":
    unittest.main()
