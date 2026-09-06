#!/usr/bin/env python3
"""tools/perf-bench.py against a SYNTHETIC state directory (invented sessions in the notes-api demo
domain, placeholder uuids, no real data): it runs end to end and emits the JSON shape, it refuses the
live default state directory without the flag and mirrors it with the flag, and --compare prints
deltas. The tool is driven as a subprocess with the same env recipe a person would use, so nothing
here loads romp code in-process."""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
TOOL = os.path.join(ROOT, "tools", "perf-bench.py")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

SID_WEB = "11111111-2222-3333-4444-555555555555"
SID_API = "22222222-3333-4444-5555-666666666666"
SID_TESTS = "33333333-4444-5555-6666-777777777777"
MANAGER_VARS = ("ROMP_MANAGER_PORT", "ROMP_SERVE_PORT", "ROMP_MANAGER_PID", "ROMP_SUPERVISED")


def _iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat().replace("+00:00", "Z")


def _transcript(path, sid, cwd, n_turns, t0):
    """A synthetic Claude Code transcript: n_turns of prompt, one tool round, reply."""
    n = [0]
    parent = [None]
    t = [t0]

    def rec(typ, message, **extra):
        n[0] += 1
        t[0] += 3
        u = "aaaaaaaa-0000-0000-0000-%012d" % n[0]
        r = {"type": typ, "timestamp": _iso(t[0]), "uuid": u, "parentUuid": parent[0], "sessionId": sid,
             "cwd": cwd, "version": "2.1.0", "gitBranch": "main", "message": message}
        r.update(extra)
        parent[0] = u
        return r

    with open(path, "w") as f:
        for i in range(n_turns):
            tid = "toolu_%06d" % i
            rows = [
                rec("user", {"role": "user", "content": "step %d: tighten the search index and rerun the suite" % i},
                    promptSource="typed"),
                rec("assistant", {"role": "assistant", "model": "claude-sonnet-4", "stop_reason": "tool_use",
                                  "content": [{"type": "text", "text": "Round %d: adjusting `search.py`." % i},
                                              {"type": "tool_use", "id": tid, "name": "Bash",
                                               "input": {"command": "uv run pytest -q tests/test_search.py"}}]}),
                rec("user", {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "content": "ok\n"}]},
                    toolUseResult={"stdout": "ok"}),
                rec("assistant", {"role": "assistant", "model": "claude-sonnet-4", "stop_reason": "end_turn",
                                  "content": [{"type": "text", "text": "Step %d done: the suite passes." % i}]}),
            ]
            for r in rows:
                f.write(json.dumps(r) + "\n")


def build_synthetic(root):
    """A state directory at root/romp (named `romp` so XDG_STATE_HOME=root resolves it as the default)
    plus a Claude config dir at root/claude holding the transcripts. Returns (state, claude_dir)."""
    root = Path(root)
    state = root / "romp"
    cwd = root / "notes-api"
    cwd.mkdir(parents=True)
    for d in ("names", "sdk", "states", "goals"):
        (state / d).mkdir(parents=True)
    claude = root / "claude"
    proj = claude / "projects" / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cwd)))
    proj.mkdir(parents=True)
    now = int(time.time())
    for sid, name, color, alive, turns in ((SID_WEB, "web", "#4a7bd0", True, 12),
                                           (SID_API, "api", "#d07b4a", True, 3),
                                           (SID_TESTS, "tests", "#4ad07b", False, 1)):
        (state / "names" / sid).write_text("%s\t%s\t%s\t#ffffff\n" % (name, cwd, color))
        (state / "sdk" / (sid + ".json")).write_text(json.dumps(
            {"sid": sid, "name": name, "cwd": str(cwd), "mode": "acceptEdits", "effort": "medium",
             "lastSid": "", "alive": alive}))
        with open(state / "states" / (sid + ".jsonl"), "w") as f:
            f.write(json.dumps({"t": now - 3600, "state": "waiting"}) + "\n")
            f.write(json.dumps({"t": now - 60, "state": "working" if name == "web" else "waiting"}) + "\n")
        _transcript(proj / (sid + ".jsonl"), sid, str(cwd), turns, now - 3000)
    (state / "goals" / (SID_WEB + ".json")).write_text(json.dumps(
        {"rompUuid": SID_WEB, "seq": 1, "rev": 1, "placementsV": 11,
         "nodes": {"g1": {"parentId": None, "t": now - 500, "text": "wire the notes search index"}},
         "status": {"g1": "working"}, "lastNode": "g1", "placements": {}}))
    return str(state), str(claude)


def run_tool(args, env_extra=None, timeout=240):
    env = {k: v for k, v in os.environ.items() if k not in MANAGER_VARS}
    env.update(env_extra or {})
    return subprocess.run([sys.executable, TOOL] + list(args), capture_output=True, text=True, env=env, timeout=timeout)


class PerfBench(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="perf-bench-test-")
        cls.state, cls.claude = build_synthetic(cls.root)
        cls.json_path = os.path.join(cls.root, "out.json")
        cls.transcript = os.path.join(cls.claude, "projects",
                                      re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(os.path.join(cls.root, "notes-api"))),
                                      SID_WEB + ".jsonl")
        cls.transcript_mtime = os.stat(cls.transcript).st_mtime_ns
        cls.main = run_tool(["--state", cls.state, "--claude-dir", cls.claude, "--repo", ROOT, "--iters", "1",
                             "--sessions", "2", "--profile", "--json", cls.json_path])

    def _ok(self, r):
        self.assertEqual(r.returncode, 0, "rc=%d\nstdout:\n%s\nstderr:\n%s" % (r.returncode, r.stdout[-4000:], r.stderr[-4000:]))

    def test_runs_and_reports_every_builder(self):
        self._ok(self.main)
        with open(self.json_path) as f:
            out = json.load(f)
        self.assertEqual(out["schema"], 1)
        self.assertEqual(os.path.realpath(out["state"]), os.path.realpath(self.state))
        b = out["benchmarks"]
        for name in ("liveness_snapshot", "names_snapshot", "discover_cold", "discover_warm", "build_feed",
                     "build_feed_noparse", "build_timeline_bars", "build_timeline_skel",
                     "build_session_cold:11111111", "build_session_warm:11111111",
                     "build_session_cold:22222222", "load_goals:11111111", "push_connect", "push_steady"):
            self.assertIn(name, b, "missing benchmark %s in %s" % (name, sorted(b)))
            self.assertIsInstance(b[name]["median"], (int, float), name)
        self.assertNotIn("build_session_cold:33333333", b, "a closed reg (alive=false) is not a live session")
        self.assertEqual(out["liveness"]["live"], 2)
        self.assertEqual(out["liveness"]["closed_regs"], 1)
        web = next(s for s in out["benched_sessions"] if s["sid8"] == "11111111")
        self.assertGreater(web["events"], 0, "the chat build saw the synthetic transcript's events")
        self.assertEqual(out["benched_sessions"][0]["sid8"], "11111111", "largest transcript first")
        self.assertEqual(out["goal_stores"][0]["nodes"], 1)
        chat = b["push_connect"]["bytes"]["chat"]["slots"]
        self.assertIn("chat:11111111", chat, "the fake chat client received the active tab's session frame")
        self.assertGreater(chat["chat:11111111"], 0)
        self.assertIn("feed", b["push_connect"]["bytes"]["feed"]["slots"])
        self.assertEqual(out["spawn_attempts"], [], "no builder spawned a process")
        self.assertEqual(out["threads_new"], [], "no builder left a thread running")
        self.assertIn("km._refresh_remote_prices", out["neutralized"])
        self.assertIn("km._warm_fleet_bg", out["neutralized"])
        self.assertEqual(os.stat(self.transcript).st_mtime_ns, self.transcript_mtime, "transcripts are read-only")
        prof = out["profiles"]
        for name in ("build_feed", "build_timeline_bars", "build_session_cold:11111111", "load_goals:11111111", "push_steady"):
            self.assertIn(name, prof)
            self.assertLessEqual(len(prof[name]["cumulative"]), 25)
            self.assertLessEqual(len(prof[name]["tottime"]), 25)
            self.assertEqual(set(prof[name]["cumulative"][0]), {"func", "file", "line", "ncalls", "tottime_ms", "cumtime_ms"})
        self.assertIn("build_feed", self.main.stdout)
        self.assertIn("top 25 by cumulative time", self.main.stdout)

    def test_refuses_the_live_default_dir_without_the_flag(self):
        root = tempfile.mkdtemp(prefix="perf-bench-live-")
        state, claude = build_synthetic(root)
        r = run_tool(["--state", state, "--claude-dir", claude, "--repo", ROOT, "--iters", "1"],
                     env_extra={"XDG_STATE_HOME": root})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("--i-know-this-is-live", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(state, "repo-root")), "the kernel was never imported against it")
        r = run_tool(["--state", state, "--claude-dir", claude, "--repo", ROOT, "--iters", "1"],
                     env_extra={"ROMP_STATE_DIR": state})
        self.assertEqual(r.returncode, 2, "ROMP_STATE_DIR names the live dir too")

    def test_live_flag_benches_a_mirror_and_leaves_the_original_alone(self):
        root = tempfile.mkdtemp(prefix="perf-bench-live-")
        state, claude = build_synthetic(root)
        before = {p: os.stat(p).st_mtime_ns for p in Path(state).rglob("*") if p.is_file()}
        out_json = os.path.join(root, "out.json")
        r = run_tool(["--state", state, "--claude-dir", claude, "--repo", ROOT, "--iters", "1", "--sessions", "1",
                      "--clients", "", "--i-know-this-is-live", "--json", out_json], env_extra={"XDG_STATE_HOME": root})
        self._ok(r)
        self.assertIn("mirrored", r.stderr)
        after = {p: os.stat(p).st_mtime_ns for p in Path(state).rglob("*") if p.is_file()}
        self.assertEqual(before, after, "the live directory is only read")
        with open(out_json) as f:
            out = json.load(f)
        self.assertEqual(os.path.realpath(out["state_mirror_of"]), os.path.realpath(state))
        self.assertNotEqual(os.path.realpath(out["state"]), os.path.realpath(state))
        self.assertIn("build_feed", out["benchmarks"])
        self.assertNotIn("push_steady", out["benchmarks"], "--clients '' skips the push benchmarks")

    def test_compare_prints_per_benchmark_deltas(self):
        self._ok(self.main)
        r = run_tool(["--compare", self.json_path, self.json_path])
        self._ok(r)
        self.assertIn("build_feed", r.stdout)
        self.assertIn("+0.00", r.stdout)
        self.assertIn("push_connect bytes", r.stdout)

    def test_requires_a_state_dir(self):
        r = run_tool([])
        self.assertEqual(r.returncode, 2)
        r = run_tool(["--state", os.path.join(self.root, "not-a-state-dir")])
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
