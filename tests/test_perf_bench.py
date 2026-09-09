#!/usr/bin/env python3
"""tools/perf-bench.py against a SYNTHETIC state directory (invented sessions in the notes-api demo
domain, placeholder uuids, no real data): it runs end to end and emits the JSON shape, its cold
build_session row is a real cold parse, it leaves the copy byte-identical (every write the kernel
aims at it lands in the tool's shadow, and the census says so on the error path too), it finds
transcripts older than the discovery window through the backfill, --cwd-map resolves a redacted copy's
registry cwds, it refuses the live default state directory without the flag and mirrors it with the
flag, and --compare prints deltas. The sessions' directory is a real git
checkout with a fabricated GitHub origin, as every real state's is: the chat build's git queries —
the path-link ones and the session-repo `remote get-url` — reach the tripwire's allow list, which a
plain directory never exercised (the tripwire refused the repo query and a real run aborted at its
first chat build while this suite stayed green, 2026-09-06). The tool is driven as a subprocess with
the same env recipe a person would use, so nothing here loads romp code in-process; the tool module
itself is loaded for direct checks of its fake client's frame labelling and of the tripwire's allow
rule (its import pulls in only the standard library)."""
import atexit
import copy
import hashlib
import json
import os
import re
import shutil
from romp_load import load_source
from types import SimpleNamespace
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

# Two effects. For the CHILD (the tool runs as a subprocess and sets its own state root before it loads
# the kernel) this points the default state root at a temp dir, so the refusal tests' XDG_STATE_HOME /
# ROMP_STATE_DIR overrides are the only "live" candidates the tool can see. It is also the ratchet's
# preamble for the one in-process load below, the tool module, which loads no romp code at import. It
# replaces conftest's suite-wide floor with another temp dir for the modules collected after this one,
# which changes nothing for them. Every temp dir this module makes is removed when it is done with it
# (this one at interpreter exit): a suite that leaves its directories behind fills /tmp over time.
_XDG_TMP = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = _XDG_TMP
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
atexit.register(shutil.rmtree, _XDG_TMP, ignore_errors=True)

SID_WEB = "11111111-2222-3333-4444-555555555555"
SID_API = "22222222-3333-4444-5555-666666666666"
SID_TESTS = "33333333-4444-5555-6666-777777777777"
MANAGER_VARS = ("ROMP_MANAGER_PORT", "ROMP_SERVE_PORT", "ROMP_MANAGER_PID", "ROMP_SUPERVISED")
WEB_TURNS = 400       # large enough that a cold build (parse + fold) measurably outlasts a warm one
EXPECTED_NEUTRALIZED = {
    "km._refresh_remote_prices", "km._warm_fleet_bg", "km._system_notify", "km._push_notify", "km._push_forward",
    "km._badge_push", "romp_kernel_perf_bench.subprocess", "romp_judge.subprocess", "romp_sdk_backend.subprocess",
    "km._atomic_write (shadowed)", "km._read_state_json (shadow overlay)", "km._order_audit_path (shadowed)",
    "pwd.getpwnam (counted)", "pwd.getpwuid (counted)"}
# The caches the tool empties before each cold build_session sample, as this kernel has them. The tool
# skips a name a revision lacks, so a rename here would silently leave that cache warm: this pins the
# HEAD set, and a kernel change that renames or adds one must change it deliberately.
EXPECTED_COLD_CACHES = {
    "kernel": {"_parse_cache", "_built_chat", "_prev_chat_events", "_prev_chat_ledger", "_arch_tops_cache",
               "_PATH_LINK_CACHE", "_states_notes_cache", "_state_ev_cache", "_bgtasks_cache", "_bgall_cache",
               "_queued_parse_cache", "_wake_tail_cache", "_session_meta_cache", "_session_tok_cache",
               "_machine_cut_cache", "_chat_fold", "_caps_memo", "_thread_reg_memo", "_states_overlay_cache",
                "_lanes_memo"},
    "event_model": {"_JSONL_CACHE", "_ASM_CACHE", "_TRAILING_CACHE"}}
# What the kernel aims at the copy on a normal run, every one of which the tool's shadow takes: the
# import-time repo-root marker, the tab-order audit and the session order the push maintains. The copy
# itself changes by nothing (the tree hash below). A new write path in a builder must change this set
# deliberately, and one that reaches the copy fails the hash.
EXPECTED_SHADOWED = {"order-audit.jsonl", "repo-root", "session-order.json"}
REDACTED_PREFIX = "/XXXX/XXXXXX"     # what a redaction tool leaves where a home path stood


def _tree_hash(root):
    """Every directory, file and symlink under root, keyed by relative path: a directory as "dir", a
    symlink as its target, a file as the sha256 of its bytes. Two equal maps mean a byte-identical tree
    (mtimes aside, which a read may not touch either — the mirror test checks those)."""
    out = {}
    for dp, dns, fns in os.walk(root):
        for d in dns:
            out[os.path.relpath(os.path.join(dp, d), root) + "/"] = "dir"
        for f in fns:
            p = os.path.join(dp, f)
            if os.path.islink(p):
                out[os.path.relpath(p, root)] = "link:" + os.readlink(p)
            else:
                with open(p, "rb") as fh:
                    out[os.path.relpath(p, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def _age_transcripts(claude, days):
    """Set every transcript's mtime `days` back: a copy taken from a machine whose sessions last wrote
    that long ago, outside discovery's 48 h window and inside the 365-day backfill."""
    t = time.time() - days * 86400
    for p in Path(claude, "projects").rglob("*.jsonl"):
        os.utime(p, (t, t))


def _redact_cwds(state, root):
    """Rewrite every registry cwd (names/ and sdk/) so the fixture's root reads as REDACTED_PREFIX, the
    way a redaction tool replaces a home path, while the projects/ directory keeps its original name."""
    for f in Path(state, "names").iterdir():
        f.write_text(f.read_text().replace(str(root), REDACTED_PREFIX))
    for f in Path(state, "sdk").glob("*.json"):
        reg = json.loads(f.read_text())
        reg["cwd"] = reg["cwd"].replace(str(root), REDACTED_PREFIX)
        f.write_text(json.dumps(reg))


def _iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat().replace("+00:00", "Z")


def _transcript(path, sid, cwd, n_turns, t0):
    """A synthetic Claude Code transcript: n_turns of prompt, one tool round, reply. One reply carries a
    `~someone/...` path token, which the chat build's path-link pass hands to os.path.expanduser."""
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
            reply = "Step %d done: the suite passes." % i
            if i == 1:
                reply += " Notes are in `~someone/notes/index.md` for later."
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
                                  "content": [{"type": "text", "text": reply}]}),
            ]
            for r in rows:
                f.write(json.dumps(r) + "\n")


ORIGIN = "https://github.com/example-org/notes-api.git"   # fabricated; `remote get-url` reads config, no network


def _git(*args, cwd):
    """A fixture git call that reads no global or system config (a developer's commit signing or
    url.insteadOf must not bend the fixture) and commits as a synthetic author."""
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    subprocess.run(["git", "-c", "user.email=t@TESTHOST", "-c", "user.name=t", "-c", "commit.gpgsign=false"] + list(args),
                   cwd=str(cwd), check=True, capture_output=True, env=env)


def build_synthetic(root, web_turns=WEB_TURNS):
    """A state directory at root/romp (named `romp` so XDG_STATE_HOME=root resolves it as the default)
    plus a Claude config dir at root/claude holding the transcripts. Returns (state, claude_dir). The
    state carries the two credential-shaped files a real one has (synthetic contents), which the mirror
    must leave behind. The sessions' cwd is a one-commit checkout with a GitHub origin, so the kernel's
    read-only git queries run for real and the tripwire's allow list is exercised."""
    root = Path(root)
    state = root / "romp"
    cwd = root / "notes-api"
    cwd.mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=cwd)
    (cwd / "README.md").write_text("# notes-api\n")
    _git("add", "README.md", cwd=cwd)
    _git("commit", "-q", "-m", "seed", cwd=cwd)
    _git("remote", "add", "origin", ORIGIN, cwd=cwd)
    for d in ("names", "sdk", "states", "goals"):
        (state / d).mkdir(parents=True)
    (state / "serve-token").write_text("synthetic-serve-token-not-real\n")
    (state / "push-vapid.json").write_text(json.dumps({"synthetic": True}))
    claude = root / "claude"
    proj = claude / "projects" / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cwd)))
    proj.mkdir(parents=True)
    now = int(time.time())
    for sid, name, color, alive, turns in ((SID_WEB, "web", "#4a7bd0", True, web_turns),
                                           (SID_API, "api", "#d07b4a", True, 3),
                                           (SID_TESTS, "tests", "#4ad07b", False, 1)):
        (state / "names" / sid).write_text("%s\t%s\t%s\t#ffffff\n" % (name, cwd, color))
        (state / "sdk" / (sid + ".json")).write_text(json.dumps(
            {"sid": sid, "name": name, "cwd": str(cwd), "mode": "acceptEdits", "effort": "medium",
             "lastSid": "", "alive": alive}))
        with open(state / "states" / (sid + ".jsonl"), "w") as f:
            f.write(json.dumps({"t": now - 3600, "state": "waiting"}) + "\n")
            f.write(json.dumps({"t": now - 60, "state": "working" if name == "web" else "waiting"}) + "\n")
        _transcript(proj / (sid + ".jsonl"), sid, str(cwd), turns, now - 3 * turns * 4 - 60)
    (state / "goals" / (SID_WEB + ".json")).write_text(json.dumps(
        {"rompUuid": SID_WEB, "seq": 1, "rev": 1, "placementsV": 11,
         "nodes": {"g1": {"parentId": None, "t": now - 500, "text": "wire the notes search index"}},
         "status": {"g1": "working"}, "lastNode": "g1", "placements": {}}))
    return str(state), str(claude)


def run_tool(args, env_extra=None, timeout=300):
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
        cls.state_before, cls.claude_before = _tree_hash(cls.state), _tree_hash(cls.claude)
        cls.main = run_tool(["--state", cls.state, "--claude-dir", cls.claude, "--repo", ROOT, "--iters", "2",
                             "--sessions", "2", "--profile", "--json", cls.json_path])
        cls.state_after, cls.claude_after = _tree_hash(cls.state), _tree_hash(cls.claude)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def _scratch_root(self, prefix):
        root = tempfile.mkdtemp(prefix=prefix)
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        return root

    def _ok(self, r):
        self.assertEqual(r.returncode, 0, "rc=%d\nstdout:\n%s\nstderr:\n%s" % (r.returncode, r.stdout[-4000:], r.stderr[-4000:]))

    def _out(self):
        self._ok(self.main)
        with open(self.json_path) as f:
            return json.load(f)

    def test_runs_and_reports_every_builder(self):
        out = self._out()
        self.assertEqual(out["schema"], 3)
        self.assertEqual(os.path.realpath(out["state"]), os.path.realpath(self.state))
        b = out["benchmarks"]
        for name in ("liveness_snapshot", "names_snapshot", "discover_cold", "discover_warm", "build_feed",
                     "build_feed_noparse", "build_timeline_bars", "build_timeline_skel",
                     "build_session_cold:11111111", "build_session_emwarm:11111111", "build_session_warm:11111111",
                     "build_session_cold:22222222", "load_goals:11111111", "push_cold_cycle", "push_steady",
                     "push_connect:chat", "push_connect:feed", "push_connect:timeline"):
            self.assertIn(name, b, "missing benchmark %s in %s" % (name, sorted(b)))
            self.assertIsInstance(b[name]["median"], (int, float), name)
        self.assertNotIn("build_session_cold:33333333", b, "a closed reg (alive=false) is not a live session")
        self.assertEqual(out["liveness"]["live"], 2)
        self.assertEqual(out["liveness"]["closed_regs"], 1)
        self.assertEqual(out["live_transcripts"]["count"], 2)
        self.assertEqual(out["live_transcripts"]["no_transcript"], [])
        web = next(s for s in out["benched_sessions"] if s["sid8"] == "11111111")
        self.assertGreater(web["events"], 0, "the chat build saw the synthetic transcript's events")
        self.assertEqual(out["benched_sessions"][0]["sid8"], "11111111", "largest transcript first")
        self.assertEqual(out["goal_stores"][0]["nodes"], 1)
        self.assertEqual(out["spawn_attempts"], [], "no builder spawned a process")
        self.assertEqual(out["threads_new"], [], "no builder left a thread running")
        self.assertEqual(set(out["neutralized"]), EXPECTED_NEUTRALIZED)
        self.assertEqual(os.stat(self.transcript).st_mtime_ns, self.transcript_mtime, "transcripts are read-only")
        self.assertEqual(set(out["writes"]["shadowed"]), EXPECTED_SHADOWED)
        self.assertEqual((out["writes"]["changed"], out["writes"]["new"], out["writes"]["removed"]), (0, 0, 0))
        self.assertEqual(out["live_transcripts"]["searched"], {"cwds": 1, "project_dirs": 1, "transcripts": 3})
        self.assertEqual(out["cwd_map"], [])
        prof = out["profiles"]
        for name in ("build_feed", "build_timeline_bars", "build_session_cold:11111111", "load_goals:11111111", "push_steady"):
            self.assertIn(name, prof)
            self.assertLessEqual(len(prof[name]["cumulative"]), 25)
            self.assertLessEqual(len(prof[name]["tottime"]), 25)
            self.assertEqual(set(prof[name]["cumulative"][0]), {"func", "file", "line", "ncalls", "tottime_ms", "cumtime_ms"})
        self.assertIn("build_feed", self.main.stdout)
        self.assertIn("top 25 by cumulative time", self.main.stdout)

    def test_cold_build_is_a_full_parse_and_slower_than_warm(self):
        b = self._out()["benchmarks"]
        cold, em, warm = b["build_session_cold:11111111"], b["build_session_emwarm:11111111"], b["build_session_warm:11111111"]
        self.assertEqual(cold["asm"].get("full", 0), cold["n"], "every kept cold sample ran exactly one full assembly")
        self.assertEqual(cold["asm"].get("serve", 0), 0, "a single-session transcript is assembled once per cold build")
        self.assertEqual(cold["asm"].get("fold", 0), 0, "nothing grows between reads in a static fixture")
        self.assertEqual(em["asm"].get("full", 0), 0, "the em-warm row never re-parses")
        self.assertGreater(cold["median"], warm["median"], "a %d-turn transcript's cold build outlasts its warm build (%s vs %s ms)"
                           % (WEB_TURNS, cold["median"], warm["median"]))
        self.assertGreater(cold["median"], em["median"], "the parse is part of the cold row, not the em-warm row")
        self.assertIn("git_per_build", cold)
        self.assertEqual({k: set(v) for k, v in self._out()["cold_caches"].items()}, EXPECTED_COLD_CACHES)

    def test_path_token_lookups_are_counted(self):
        out = self._out()
        self.assertGreaterEqual(out["nss_lookups"].get("getpwnam", 0), 1,
                                "the `~someone/...` token reached pwd.getpwnam through os.path.expanduser")

    def test_the_session_repo_query_passes_the_tripwire_and_is_counted(self):
        # the sessions' cwd is a checkout, so the chat build asks `git remote get-url origin` for the
        # session's GitHub repo; the tripwire admits exactly that pair and counts it (a refusal would
        # have aborted the run — spawn_attempts stays empty and every row is present)
        out = self._out()
        g = out["git_queries"]
        self.assertFalse(g["answered_as_failure"])
        self.assertGreaterEqual(g["calls"].get("remote get-url", 0), 1, g)
        self.assertGreaterEqual(g["calls"].get("rev-parse", 0), 1, "the toplevel query ran in the checkout too")
        self.assertEqual(out["spawn_attempts"], [])
        self.assertIn("remote get-url=", self.main.stdout, "the report names the query by its pair")

    def test_push_rows_report_bytes_and_rebuild_flags(self):
        b = self._out()["benchmarks"]
        chat = b["push_cold_cycle"]["bytes"]["chat"]["slots"]
        self.assertIn("chat:11111111", chat, "the fake chat client received the active tab's session frame")
        self.assertGreater(chat["chat:11111111"], 0)
        self.assertIn("feed", b["push_cold_cycle"]["bytes"]["feed"]["slots"])
        self.assertIn("chat:11111111", b["push_connect:chat"]["bytes"]["slots"], "a fresh chat client gets the full session")
        self.assertIn("feed", b["push_connect:feed"]["bytes"]["slots"])
        self.assertIn("timeline", b["push_connect:timeline"]["bytes"]["slots"])
        st = b["push_steady"]
        self.assertGreaterEqual(len(st["samples"]), st["n"])
        self.assertEqual(st["n"], 2, "the loop ran until two quiet samples existed")
        for s in st["samples"]:
            self.assertEqual(set(s), {"ms", "rebuilt_feed", "rebuilt_timeline", "bytes"})
        quiet = [s for s in st["samples"] if not (s["rebuilt_feed"] or s["rebuilt_timeline"])]
        self.assertEqual(len(quiet), st["n"])
        self.assertEqual(st["rebuild_samples"], len(st["samples"]) - len(quiet))
        for name, row in b.items():
            if name.startswith("push") and row.get("bytes"):
                self.assertNotIn("unknown", json.dumps(row["bytes"]), "%s: every frame the fake clients got was labelled" % name)

    def test_fake_client_labels_direct_delta_frames_by_their_slot(self):
        # the static fixture never changes between pushes, so no delta frame reaches a fake client in the
        # run above; this drives the client's send() directly with the three frame shapes it can see
        pb = load_source("perf_bench_under_test", TOOL)
        c = pb.fake_client(SimpleNamespace(), "timeline")      # no _perf_slot: a keyed label is str(key)
        delta = '{"type": "delta", "slot": "bars", "base": 3, "rev": 4, "coll": {}}'
        c["send"](delta)                                        # _send_slot_delta: send() directly, no curSlot
        c["curSlot"] = ("timeline",)                            # what _client_send sets around its call
        full = '{"type": "timeline", "sessions": []}'
        c["send"](full)
        del c["curSlot"]
        other = '{"type": "warn", "text": "not a slot frame"}'
        c["send"](other)
        self.assertEqual(c["bytes"], {"bars-delta": len(delta), "('timeline',)": len(full), "warn": len(other)})
        self.assertEqual(c["frames"], 3)

    def test_the_copy_is_byte_identical_after_a_run(self):
        # the three files the kernel aims at the copy (EXPECTED_SHADOWED) landed in the tool's shadow, so
        # the copy has the same directories, files and bytes it started with; before the shadow the run
        # created repo-root, session-order.json and order-audit.jsonl inside it
        self._ok(self.main)
        self.assertEqual(self.state_after, self.state_before, "the state copy is only read")
        self.assertEqual(self.claude_after, self.claude_before, "the transcripts are only read")
        self.assertIn("writes into the state copy: 0 changed, 0 new, 0 removed", self.main.stdout)
        self.assertIn("writes shadowed (landed in the private dir, not the copy): order-audit.jsonl, repo-root, session-order.json",
                      self.main.stdout)

    def test_the_census_runs_on_the_error_path_and_names_what_was_searched(self):
        # a claude dir with no projects/ at all: discovery finds nothing, the window and the backfill both
        # count zero, and the run stops with the counts it worked from. The census still runs and prints,
        # the JSON carries it beside the error, and the copy is untouched (the kernel WAS imported, so
        # without the shadow repo-root would be in it)
        root = self._scratch_root("perf-bench-nofind-")
        state, claude = build_synthetic(root, web_turns=3)
        empty_claude = os.path.join(root, "claude-empty")
        os.makedirs(empty_claude)
        before = _tree_hash(state)
        out_json = os.path.join(root, "out.json")
        r = run_tool(["--state", state, "--claude-dir", empty_claude, "--repo", ROOT, "--iters", "1", "--json", out_json])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("discovery found no transcript for any of the 2 live sessions: 0 in the 48 h window, "
                      "0 more in the 365-day backfill; their 1 registry cwd(s) resolve to 0 existing project "
                      "directories holding 0 transcript(s)", r.stderr)
        self.assertIn("--cwd-map", r.stderr, "the error points at the redacted-copy remedy")
        self.assertNotIn(root, r.stderr.split("perf-bench: discovery")[1], "the error names counts, not paths")
        self.assertIn("writes into the state copy: 0 changed, 0 new, 0 removed", r.stdout)
        self.assertIn("writes shadowed (landed in the private dir, not the copy): repo-root", r.stdout)
        self.assertEqual(_tree_hash(state), before, "an error run leaves the copy byte-identical too")
        with open(out_json) as f:
            out = json.load(f)
        self.assertIn("no transcript for any", out["error"])
        self.assertEqual((out["writes"]["changed"], out["writes"]["new"], out["writes"]["removed"]), (0, 0, 0))
        self.assertEqual(out["writes"]["shadowed"], ["repo-root"])
        self.assertIn("(partial: the run stopped on an error)", r.stdout)

    def test_transcripts_older_than_the_window_are_found_by_the_backfill(self):
        # every transcript is 3 days old: outside discovery's 48 h window, inside the 365-day backfill.
        # Before the fix the run raised "no transcript for any live session" before the backfill ran
        root = self._scratch_root("perf-bench-old-")
        state, claude = build_synthetic(root, web_turns=3)
        _age_transcripts(claude, days=3)
        out_json = os.path.join(root, "out.json")
        r = run_tool(["--state", state, "--claude-dir", claude, "--repo", ROOT, "--iters", "1", "--sessions", "2",
                      "--clients", "", "--json", out_json])
        self._ok(r)
        with open(out_json) as f:
            out = json.load(f)
        lt = out["live_transcripts"]
        self.assertEqual((lt["in_window"], lt["backfilled"], lt["count"], lt["no_transcript"]), (0, 2, 2, []))
        self.assertIn("build_session_cold:11111111", out["benchmarks"])
        self.assertIn("build_session_cold:22222222", out["benchmarks"])
        self.assertIn("2 live transcripts (0 in the discovery window, 2 backfilled, 0 without one)", r.stdout)

    def test_cwd_map_resolves_a_redacted_copy(self):
        # the registry cwds read /XXXX/XXXXXX/notes-api while the project directory is still named after
        # the real path: without a map discovery resolves the cwd to a directory that does not exist and
        # the run stops; with --cwd-map the same run finds both transcripts and reports the rule's hits
        root = self._scratch_root("perf-bench-redacted-")
        state, claude = build_synthetic(root, web_turns=3)
        _redact_cwds(state, root)
        before = _tree_hash(state)
        out_json = os.path.join(root, "out.json")
        base = ["--state", state, "--claude-dir", claude, "--repo", ROOT, "--iters", "1", "--sessions", "2",
                "--clients", "", "--json", out_json]
        r = run_tool(base)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("their 1 registry cwd(s) resolve to 0 existing project directories", r.stderr)
        r = run_tool(base + ["--cwd-map", "/nowhere/else=/nowhere", "--cwd-map", REDACTED_PREFIX + "=" + root])
        self._ok(r)
        with open(out_json) as f:
            out = json.load(f)
        self.assertEqual((out["live_transcripts"]["count"], out["live_transcripts"]["no_transcript"]), (2, []))
        self.assertEqual(out["live_transcripts"]["searched"], {"cwds": 1, "project_dirs": 1, "transcripts": 3})
        self.assertEqual([(m["from"], m["to"]) for m in out["cwd_map"]], [("/nowhere/else", "/nowhere"), (REDACTED_PREFIX, root)])
        self.assertEqual(out["cwd_map"][0]["hits"], 0)
        self.assertGreater(out["cwd_map"][1]["hits"], 0, "the matching rule counted its hits")
        self.assertIn("build_session_cold:11111111", out["benchmarks"])
        self.assertIn("cwd-map hits: rule 1=0, rule 2=", r.stdout)
        self.assertIn("jd._proj_dir (cwd-map)", out["neutralized"], "the report says the derivation is wrapped")
        self.assertEqual(_tree_hash(state), before, "the map rewrites nothing in the copy")
        self.assertEqual(out["spawn_attempts"], [], "the git queries against the redacted cwd failed quietly, no tripwire")

    def test_an_exception_out_of_the_candidate_kernel_still_prints_the_census(self):
        # a --repo whose kernel raises at import (the realistic error of a broken candidate checkout) is
        # not a BenchError: before the fix it propagated past main() and the census run() had taken was
        # dropped with it (no census line, no JSON, only the traceback). Now the census prints, the JSON
        # carries the error beside it, the copy is byte-identical, and the traceback still follows
        root = self._scratch_root("perf-bench-broken-")
        state, claude = build_synthetic(root, web_turns=3)
        repo = os.path.join(root, "broken-repo")
        os.makedirs(os.path.join(repo, "kernel"))
        shutil.copy(os.path.join(ROOT, "kernel", "loadsource.py"), os.path.join(repo, "kernel", "loadsource.py"))
        Path(repo, "kernel", "kernel.py").write_text("raise RuntimeError('synthetic import failure')\n")
        before = _tree_hash(state)
        out_json = os.path.join(root, "out.json")
        r = run_tool(["--state", state, "--claude-dir", claude, "--repo", repo, "--iters", "1", "--json", out_json])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("writes into the state copy: 0 changed, 0 new, 0 removed", r.stdout)
        self.assertIn("writes shadowed (landed in the private dir, not the copy): none", r.stdout)
        self.assertIn("(partial: the run stopped on an error)", r.stdout)
        self.assertIn("perf-bench: RuntimeError: synthetic import failure", r.stderr)
        self.assertIn("Traceback", r.stderr, "the exception still leaves main() with its traceback")
        self.assertEqual(_tree_hash(state), before)
        with open(out_json) as f:
            out = json.load(f)
        self.assertEqual(out["error"], "RuntimeError: synthetic import failure")
        self.assertEqual((out["writes"]["changed"], out["writes"]["new"], out["writes"]["removed"]), (0, 0, 0))
        self.assertEqual(out["writes"]["shadowed"], [])

    def test_fingerprint_sees_directories_and_symlink_targets(self):
        # the census fingerprints directories and link targets too: a directory the kernel creates (its
        # mkdir sites on STATE subdirectories) or a link it retargets is a write into the copy, and one
        # that records files only would report it as 0 changed, 0 new, 0 removed
        pb = load_source("perf_bench_fingerprint_under_test", TOOL)
        root = self._scratch_root("perf-bench-fp-")
        os.makedirs(os.path.join(root, "sdk"))
        Path(root, "sdk", "a.json").write_text("{}")
        os.symlink("sdk", os.path.join(root, "alias"))
        before = pb.fingerprint(root)
        self.assertEqual(before["sdk/"], "dir")
        self.assertEqual(before["alias/"], ("link", "sdk"))
        os.makedirs(os.path.join(root, "goals"))
        os.remove(os.path.join(root, "alias"))
        os.symlink("goals", os.path.join(root, "alias"))
        diff = pb.fingerprint_diff(before, pb.fingerprint(root))
        self.assertEqual((diff["changed"], diff["new"], diff["removed"]), (1, 1, 0))
        self.assertEqual(diff["sample"], ["~ alias/", "+ goals/"])

    def test_install_cwd_map_wraps_nothing_without_rules(self):
        # the default run pays no extra frame per _proj_dir call; with a rule the wrapper counts its hits
        pb = load_source("perf_bench_cwdmap_under_test", TOOL)
        real = lambda d: "proj:" + str(d)
        jd = SimpleNamespace(_proj_dir=real)
        self.assertEqual(pb.install_cwd_map(jd, []), [])
        self.assertIs(jd._proj_dir, real)
        hits = pb.install_cwd_map(jd, [("/XXXX/XXXXXX", "/repo")])
        self.assertIsNot(jd._proj_dir, real)
        self.assertEqual(jd._proj_dir("/XXXX/XXXXXX/notes-api"), "proj:/repo/notes-api")
        self.assertEqual(jd._proj_dir("/XXXX/XXXXXXX/other"), "proj:/XXXX/XXXXXXX/other", "whole-component match only")
        self.assertEqual(hits, [1])

    def test_cwd_map_refuses_a_malformed_rule(self):
        r = run_tool(["--state", self.state, "--claude-dir", self.claude, "--repo", ROOT, "--cwd-map", "no-equals-sign"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("expected FROM=TO", r.stderr)
        r = run_tool(["--state", self.state, "--claude-dir", self.claude, "--repo", ROOT, "--cwd-map", "=/somewhere"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("FROM is empty", r.stderr)

    def test_refuses_the_live_default_dir_without_the_flag(self):
        root = self._scratch_root("perf-bench-live-")
        state, claude = build_synthetic(root, web_turns=3)
        r = run_tool(["--state", state, "--claude-dir", claude, "--repo", ROOT, "--iters", "1"],
                     env_extra={"XDG_STATE_HOME": root})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("--i-know-this-is-live", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(state, "repo-root")), "the kernel was never imported against it")
        r = run_tool(["--state", state, "--claude-dir", claude, "--repo", ROOT, "--iters", "1"],
                     env_extra={"ROMP_STATE_DIR": state})
        self.assertEqual(r.returncode, 2, "ROMP_STATE_DIR names the live dir too")

    def test_live_flag_benches_a_mirror_and_leaves_the_original_alone(self):
        root = self._scratch_root("perf-bench-live-")
        state, claude = build_synthetic(root, web_turns=3)
        before = {p: os.stat(p).st_mtime_ns for p in Path(state).rglob("*") if p.is_file()}
        out_json = os.path.join(root, "out.json")
        r = run_tool(["--state", state, "--claude-dir", claude, "--repo", ROOT, "--iters", "1", "--sessions", "1",
                      "--clients", "", "--i-know-this-is-live", "--keep-mirror", "--json", out_json],
                     env_extra={"XDG_STATE_HOME": root})
        self._ok(r)
        self.assertIn("mirrored", r.stderr)
        self.assertIn("mirror kept at", r.stderr)
        after = {p: os.stat(p).st_mtime_ns for p in Path(state).rglob("*") if p.is_file()}
        self.assertEqual(before, after, "the live directory is only read")
        with open(out_json) as f:
            out = json.load(f)
        self.assertEqual(os.path.realpath(out["state_mirror_of"]), os.path.realpath(state))
        mirror = out["state"]
        self.assertNotEqual(os.path.realpath(mirror), os.path.realpath(state))
        self.assertTrue(os.path.isdir(os.path.join(mirror, "sdk")), "the mirror is a state directory")
        for name in ("serve-token", "push-vapid.json"):
            self.assertFalse(os.path.exists(os.path.join(mirror, name)), "%s is not copied into the mirror" % name)
        self.assertIn("build_feed", out["benchmarks"])
        self.assertNotIn("push_steady", out["benchmarks"], "--clients '' skips the push benchmarks")
        mirror_root = os.path.dirname(os.path.realpath(mirror))      # the tool's mkdtemp dir; the mirror is its romp/
        self.assertTrue(os.path.basename(mirror_root).startswith("romp-perf-live-mirror-"), mirror_root)
        shutil.rmtree(mirror_root, ignore_errors=True)                # kept for the assertions above, not beyond
        # without --keep-mirror the mirror is removed
        r = run_tool(["--state", state, "--claude-dir", claude, "--repo", ROOT, "--iters", "1", "--sessions", "1",
                      "--clients", "", "--i-know-this-is-live", "--json", out_json], env_extra={"XDG_STATE_HOME": root})
        self._ok(r)
        self.assertIn("mirror removed", r.stderr)
        with open(out_json) as f:
            self.assertFalse(os.path.exists(json.load(f)["state"]))

    def test_compare_prints_per_benchmark_deltas(self):
        out = self._out()
        b = copy.deepcopy(out)
        feed = out["benchmarks"]["build_feed"]["median"]
        b["benchmarks"]["build_feed"]["median"] = feed * 2
        del b["benchmarks"]["discover_warm"]
        b["benchmarks"]["invented_row"] = {"n": 1, "median": 1.0}
        b["iters"] = 9
        b_path = os.path.join(self.root, "b.json")
        with open(b_path, "w") as f:
            json.dump(b, f)
        r = run_tool(["--compare", self.json_path, b_path])
        self._ok(r)
        lines = r.stdout.splitlines()
        feed_line = next(l for l in lines if l.startswith("build_feed "))
        self.assertEqual(feed_line.split(), ["build_feed", "%.2f" % feed, "%.2f" % (feed * 2), "%+.2f" % feed, "+100.0%"])
        self.assertIn("only in A: discover_warm", r.stdout)
        self.assertIn("only in B: invented_row", r.stdout)
        self.assertIn("MISMATCH", r.stdout, "a differing iters count is flagged before the table")
        self.assertIn("push_cold_cycle bytes chat", r.stdout)
        r = run_tool(["--compare", self.json_path, self.json_path])
        self._ok(r)
        self.assertNotIn("MISMATCH", r.stdout)

    def test_requires_a_state_dir(self):
        r = run_tool([])
        self.assertEqual(r.returncode, 2)
        r = run_tool(["--state", os.path.join(self.root, "not-a-state-dir")])
        self.assertEqual(r.returncode, 2)


class Tripwire(unittest.TestCase):
    """The tripwire's allow rule, in-process: exactly the kernel's read-only git queries pass —
    `rev-parse`, `ls-files`, and the pair `remote get-url` — and everything else raises. `git remote`
    is not read-only as a whole (add / set-url / remove rewrite config), so only the get-url pair is
    admitted, by both words."""

    @classmethod
    def setUpClass(cls):
        cls.pb = load_source("perf_bench_tripwire_under_test", TOOL)
        cls.root = tempfile.mkdtemp(prefix="perf-bench-tripwire-")
        cls.repo = os.path.join(cls.root, "notes-api")
        os.makedirs(cls.repo)
        _git("init", "-q", "-b", "main", cwd=cls.repo)
        _git("remote", "add", "origin", ORIGIN, cwd=cls.repo)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def _tw(self, no_git=False):
        log = []
        return self.pb.SubprocessTripwire(subprocess, log, no_git=no_git), log

    def test_the_allow_rule_names_exactly_three_queries(self):
        q = self.pb.SubprocessTripwire._git_query
        self.assertEqual(q(["git", "-C", "/x", "rev-parse", "--show-toplevel"]), "rev-parse")
        self.assertEqual(q(["git", "ls-files", "-co", "--exclude-standard"]), "ls-files")
        self.assertEqual(q(["git", "-C", "/x", "remote", "get-url", "origin"]), "remote get-url")
        for argv in (["git", "-C", "/x", "remote", "set-url", "origin", "u"],
                     ["git", "-C", "/x", "remote", "add", "origin", "u"],
                     ["git", "-C", "/x", "remote", "remove", "origin"],
                     ["git", "-C", "/x", "remote"],
                     ["git", "-C", "/x", "fetch", "origin"],
                     ["git", "-C", "/x", "push"],
                     ["git"], ["gh", "pr", "view", "1"], "git rev-parse HEAD", None):
            self.assertIsNone(q(argv), argv)

    def test_the_repo_query_runs_and_is_counted_by_its_pair(self):
        tw, log = self._tw()
        r = tw.run(["git", "-C", self.repo, "remote", "get-url", "origin"], capture_output=True, text=True, timeout=5)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), ORIGIN)
        self.assertEqual(tw.git_calls, {"remote get-url": 1})
        self.assertEqual(log, [])

    def test_a_writing_remote_form_trips(self):
        tw, log = self._tw()
        with self.assertRaises(self.pb.BenchError):
            tw.run(["git", "-C", self.repo, "remote", "set-url", "origin", "https://github.com/other-org/x.git"],
                   capture_output=True, text=True)
        self.assertEqual(len(log), 1)
        self.assertIn("remote', 'set-url'", log[0])
        self.assertEqual(tw.git_calls, {})
        with self.assertRaises(self.pb.BenchError):
            tw.run(["git", "-C", self.repo, "remote"], capture_output=True, text=True)
        r = subprocess.run(["git", "-C", self.repo, "remote", "get-url", "origin"], capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), ORIGIN, "the refused set-url never ran")

    def test_no_git_answers_the_repo_query_as_a_failure(self):
        tw, log = self._tw(no_git=True)
        r = tw.run(["git", "-C", self.repo, "remote", "get-url", "origin"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertEqual(tw.git_calls, {"remote get-url": 1}, "counted even when answered as a failure")
        self.assertEqual(log, [])


if __name__ == "__main__":
    unittest.main()
