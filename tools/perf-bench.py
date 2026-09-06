#!/usr/bin/env python3
"""perf-bench — offline timing of the romp kernel's payload builders against a COPY of a state directory.

The live kernel's pusher thread spends most of a core rebuilding payloads: build_session (chat),
build_feed, build_timeline (kernel/kernel.py) and jd.load_goals (kernel/judge.py). This tool imports a
checkout's kernel IN-PROCESS, points it at a state directory copy, reconstructs the pusher's liveness
snapshot from that copy's registry files, and times each builder on real-sized data — with no live
kernel, no restart, no process spawned, no network, no WebSocket. Two checkouts (HEAD and a candidate)
run against the same copy and `--compare` prints the per-benchmark deltas.

Usage (every path below is an example; the copy lives OUTSIDE any repo):

    # 1. copy the state directory, leaving out the SDK venv (hundreds of MB, not data)
    rsync -a --exclude sdkvenv ~/.local/state/romp/ /tmp/romp-state-copy/

    # 2. bench this checkout, then a candidate checkout, against the same copy
    tools/perf-bench.py --state /tmp/romp-state-copy --profile --json /tmp/bench-head.json
    tools/perf-bench.py --state /tmp/romp-state-copy --repo ../romp-candidate --json /tmp/bench-cand.json

    # 3. deltas, A -> B
    tools/perf-bench.py --compare /tmp/bench-head.json /tmp/bench-cand.json

The tool REFUSES the live default state directory ($ROMP_STATE_DIR, $XDG_STATE_HOME/romp, or
~/.local/state/romp) unless `--i-know-this-is-live` is passed — and even then it never runs the
kernel against that directory: it mirrors the directory to a fresh temp copy (sdkvenv excluded) and
benches the mirror, so the live directory is only ever read.

What is measured (each after one warm-up call, then `--iters` timed calls; ms min/median/max):
  liveness_snapshot      Sessions.live() — the pusher cycle's one liveness read (tmux backend off)
  names_snapshot         _names_snapshot() — the cycle's names-registry read
  discover_cold/warm     jd.discover(now) with and without its fingerprint cache
  warm_all_parses        one _parse() per live session from an empty parse cache (total, once)
  build_session_cold:S   build_session for each of the K largest live transcripts, parse + fold
                         caches cleared before every call (the boot / first-paint shape)
  build_session_warm:S   the same call again with everything cached (an unchanged tab's push)
  build_feed             build_feed with every live session's parse cached (the steady state)
  build_feed_noparse     build_feed with the parse cache empty (the cards-first boot shape)
  build_timeline_bars    build_timeline(with_bars=True)
  build_timeline_skel    build_timeline(with_bars=False) — the lanes skeleton the push sends first
  load_goals:S           jd.load_goals for each of the K largest goal stores
  push_connect           _push over fake clients with empty dedup state (a fresh page's first push)
  push_steady            _push again, N times (the periodic pusher's steady state)
The push benchmarks also report bytes handed to each fake client per slot.

How the liveness snapshot is reconstructed, and what is approximated:
  * The SDK backend object is built WITHOUT its constructor (no boot heal, no reconcile thread, no
    key claim, no scope probe): a subclass allocated with __new__ and given only the attributes the
    read-side methods use. Its live_sessions() reads sdk/<sid>.json exactly as the real backend does
    for a session with no running thread (_live_row), so every reg with alive=true is a live row.
  * The state of each row is the last STATE record of states/<sid>.jsonl, verbatim, and the row is
    marked connected — what a running session would report — instead of the dormant mapping that
    turns an in-flight state into "waiting". `--dormant-rows` keeps the dormant mapping instead.
    A running session's snapshot also carries live-only fields (subagents, bgTasks, ctxTokens from
    the last turn); those read empty here. `--all-regs-live` also lists regs with alive=false.
  * The tmux backend is switched off (ROMP_TMUX_AVAILABLE=0, the kernel's own seam) and TMUX_TMPDIR
    points at an empty private directory, so no `tmux` is ever run and tmux-backed sessions are not
    represented. Comment threads (threadOf regs) are skipped, as the real live_sessions skips them.
  * The SDK backend's manager key is pinned empty (dormant rows read auth=login).
  * Transcripts are read from Claude Code's own directory ($CLAUDE_CONFIG_DIR or ~/.claude), which
    the registry references; `--claude-dir` points at a copy or a synthetic one. Discovery windows
    are keyed to the real clock, so bench a fresh copy: a session idle for two days drops out.

Side-effect guards (all reported in the output):
  * The manager control-port variables are removed or poisoned before the import (ROMP_MANAGER_PORT
    is set to a dead port rather than unset — an ABSENT value maps to the default, live, port in
    one consumer; see tests/conftest.py), so nothing this process does can reach the live manager.
  * ROMP_MODEL_CATALOG=off, ROMP_CLI_SCOPE=0, ROMP_CLAUDE_BIN=/bin/false, the service env file
    pointed at a missing path, every ANTHROPIC_* variable removed.
  * Functions that would start a network fetch, a background parse thread, a desktop notification,
    a Web Push or a badge push are replaced with recorders (they are not builders; the push path
    reaches them from _cached_feed and the pricing table).
  * `subprocess` in every loaded romp module is replaced with a tripwire that raises on any spawn —
    except the chat build's own read-only local git queries (`git rev-parse`, `git ls-files`, which
    place path links and are cached on the repo's mtimes), which run and are counted; `--no-git`
    answers those as failures instead, for a strict zero-exec run.
  * Every kernel _atomic_write is checked to land under the state copy; the copy's files are
    fingerprinted before and after so the output lists exactly what the run wrote.

Verification: run once under `strace -f -e trace=execve,connect`: with `--no-git` the only execve is
the interpreter itself; without it the extra execves are the counted git queries; there is never a
connect.

Not a test (pytest collects test_*.py); tests/test_perf_bench.py drives it against a synthetic state
directory."""
import argparse
import cProfile
import gc
import json
import os
import pstats
import shutil
import statistics
import subprocess as _real_subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1
DEFAULT_CLIENTS = "chat,feed,timeline"
PROFILE_TOP = 25


class BenchError(Exception):
    pass


# ── argument parsing ────────────────────────────────────────────────────────────────────────────
def parse_args(argv):
    ap = argparse.ArgumentParser(prog="perf-bench", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", help="a COPY of a romp state directory (see the module docstring)")
    ap.add_argument("--repo", help="the checkout whose kernel to bench (default: the one this script lives in)")
    ap.add_argument("--claude-dir", help="CLAUDE_CONFIG_DIR for the run: where transcripts (projects/) live")
    ap.add_argument("--iters", type=int, default=5, help="timed calls per benchmark after one warm-up (default 5)")
    ap.add_argument("--sessions", type=int, default=5, help="how many of the largest transcripts / goal stores to bench (default 5)")
    ap.add_argument("--clients", default=DEFAULT_CLIENTS,
                    help="fake client apps for the push benchmarks, comma-separated (default %s); empty skips them" % DEFAULT_CLIENTS)
    ap.add_argument("--profile", action="store_true", help="cProfile one call per builder; print the top %d by cumulative and by tottime" % PROFILE_TOP)
    ap.add_argument("--json", help="write the machine-readable result here")
    ap.add_argument("--compare", nargs=2, metavar=("A.json", "B.json"), help="print per-benchmark deltas A -> B and exit")
    ap.add_argument("--no-git", action="store_true",
                    help="answer the chat build's read-only git queries (rev-parse, ls-files) as failures instead of running git")
    ap.add_argument("--dormant-rows", action="store_true", help="liveness rows exactly as a restarted kernel reports dormant sessions")
    ap.add_argument("--all-regs-live", action="store_true", help="treat regs with alive=false as live too")
    ap.add_argument("--i-know-this-is-live", action="store_true",
                    help="allow --state to name the live default state directory; it is mirrored to a temp copy first")
    return ap.parse_args(argv)


# ── live-directory refusal ──────────────────────────────────────────────────────────────────────
def live_state_dirs(env):
    """Every path the CALLER's environment would resolve as the live state directory."""
    out = set()
    if env.get("ROMP_STATE_DIR"):
        out.add(os.path.realpath(os.path.expanduser(env["ROMP_STATE_DIR"])))
    xdg = env.get("XDG_STATE_HOME") or "~/.local/state"
    out.add(os.path.realpath(os.path.join(os.path.expanduser(xdg), "romp")))
    out.add(os.path.realpath(os.path.expanduser("~/.local/state/romp")))
    return out


def mirror_state(src):
    """Copy `src` (sdkvenv excluded) into a fresh temp directory and return the copy's path."""
    root = tempfile.mkdtemp(prefix="romp-perf-live-mirror-")
    dst = os.path.join(root, "romp")
    shutil.copytree(src, dst, symlinks=True, ignore=shutil.ignore_patterns("sdkvenv"))
    return dst


# ── environment for the in-process kernel ───────────────────────────────────────────────────────
def prepare_env(state, claude_dir, private_dir):
    """Rewrite os.environ for the kernel import. Returns the list of applied changes (for the report)."""
    changes = []
    for k in ("ROMP_SERVE_PORT", "ROMP_MANAGER_PID", "ROMP_SUPERVISED", "TMUX", "TMUX_PANE",
              "ROMP_SID", "ROMP_SESSION_NAME", "ROMP_STATE_DIR"):
        if k in os.environ:
            os.environ.pop(k)
            changes.append("unset " + k)
    for k in [k for k in os.environ if k.startswith("ANTHROPIC_")]:
        os.environ.pop(k)
        changes.append("unset " + k)
    tmux_dir = os.path.join(private_dir, "tmux")
    os.makedirs(tmux_dir, exist_ok=True)          # tmux falls back to the default socket dir when this is missing
    no_env = os.path.join(private_dir, "no-such-service.env")
    sets = {
        "ROMP_MANAGER_PORT": "1",                 # a dead port: absent maps to the default (live) port in _run_main_update
        "ROMP_KERNEL_NO_OPEN": "1",
        "ROMP_MODEL_CATALOG": "off",
        "ROMP_CLI_SCOPE": "0",
        "ROMP_CLAUDE_BIN": "/bin/false",
        "ROMP_TMUX_AVAILABLE": "0",
        "TMUX_TMPDIR": tmux_dir,
        "ROMP_SERVE_TOKEN": "perf-bench-token-not-for-use",
        "ROMP_SERVICE_ENV_FILE": no_env,
        "ROMP_SERVICE_ENV": no_env,
        "ROMP_STATE_DIR": state,
        "XDG_STATE_HOME": os.path.dirname(state),
    }
    if claude_dir:
        sets["CLAUDE_CONFIG_DIR"] = claude_dir
    for k, v in sets.items():
        os.environ[k] = v
        changes.append("set %s" % k)
    return changes


# ── side-effect tripwires ───────────────────────────────────────────────────────────────────────
class SubprocessTripwire:
    """Stands in for the `subprocess` module inside the loaded romp modules: constants and helpers pass
    through; every spawn raises, except the kernel's own read-only local git queries (`git rev-parse`,
    `git ls-files`), which the chat build runs to place path links (cached on the repo's index and tree
    mtimes, so a cold build pays them once per session cwd). Those are counted and reported. With
    no_git they are answered as failures (the "no git on this box" shape) instead of run, so a strict
    zero-exec run is possible without replacing any kernel function."""
    _SPAWN = ("Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput")
    _GIT_READ_ONLY = ("rev-parse", "ls-files")

    def __init__(self, real, log, no_git=False):
        self._real, self._log, self._no_git = real, log, no_git
        self.git_calls = {}

    @classmethod
    def _git_subcommand(cls, argv):
        if not (isinstance(argv, (list, tuple)) and argv and argv[0] == "git"):
            return None
        i = 1
        while i < len(argv) and argv[i] == "-C":
            i += 2
        return argv[i] if i < len(argv) else None

    def __getattr__(self, name):
        if name in self._SPAWN:
            def refuse(*a, **k):
                import traceback
                argv = a[0] if a else k.get("args")
                sub = self._git_subcommand(argv)
                if name == "run" and sub in self._GIT_READ_ONLY:
                    self.git_calls[sub] = self.git_calls.get(sub, 0) + 1
                    if self._no_git:
                        return self._real.CompletedProcess(argv, 1, "" if k.get("text") else b"", "" if k.get("text") else b"")
                    return self._real.run(*a, **k)
                where = [fr for fr in traceback.extract_stack()[:-1] if "perf-bench" not in fr.filename][-4:]
                via = " <- ".join("%s:%d %s" % (os.path.basename(fr.filename), fr.lineno, fr.name) for fr in reversed(where))
                self._log.append("subprocess.%s %r via %s" % (name, argv, via))
                raise BenchError("perf-bench tripwire: subprocess.%s called (argv %r) via %s" % (name, argv, via))
            return refuse
        return getattr(self._real, name)


def install_guards(km, sbmod, no_git=False):
    """Neutralize the non-builder side effects the push path can reach; return (names, recorder)."""
    rec = {"spawns": [], "notifications": [], "atomic_writes": [], "tripwires": []}
    names = []

    def stub(mod, attr, fn):
        if hasattr(mod, attr):
            setattr(mod, attr, fn)
            names.append("%s.%s" % ("km" if mod is km else "jd", attr))

    stub(km, "_refresh_remote_prices", lambda now=None: None)          # network fetch thread
    stub(km, "_warm_fleet_bg", lambda now=None: None)                  # background parse thread
    stub(km, "_system_notify", lambda t, b: rec["notifications"].append(("system", t)))
    stub(km, "_push_notify", lambda t, b, sid="", badge=None: rec["notifications"].append(("push", t)))
    stub(km, "_push_forward", lambda evs: rec["notifications"].append(("forward", len(evs))))
    stub(km, "_badge_push", lambda n: rec["notifications"].append(("badge", n)))
    for mod in (km, getattr(km, "jd", None), getattr(km, "em", None), sbmod):
        if mod is not None and getattr(mod, "subprocess", None) is not None:
            tw = SubprocessTripwire(_real_subprocess, rec["spawns"], no_git=no_git)
            mod.subprocess = tw
            rec["tripwires"].append(tw)
            names.append("%s.subprocess%s" % (getattr(mod, "__name__", "?"), " (git answers as failure)" if no_git else ""))
    state = Path(km.jd.STATE).resolve()
    real_aw = getattr(km, "_atomic_write", None)
    if real_aw is not None:
        def guarded(path, text, mode=None):
            p = Path(path).resolve()
            if state not in p.parents and p != state:
                raise BenchError("perf-bench: _atomic_write outside the state copy: %s" % p)
            rec["atomic_writes"].append(str(p.relative_to(state)))
            return real_aw(path, text, mode) if mode is not None else real_aw(path, text)
        km._atomic_write = guarded
        names.append("km._atomic_write (checked)")
    return names, rec


# ── the constructor-free SDK backend ────────────────────────────────────────────────────────────
def make_backend(sbmod, state, dormant_rows, all_regs):
    class BenchSdkBackend(sbmod.SdkBackend):
        def __getattr__(self, name):          # only reached for attributes the constructor would have set
            raise BenchError("perf-bench: the bench backend lacks attribute %r (a code path this tool "
                             "did not anticipate reached it — add it to make_backend)" % name)

        def live_sessions(self):
            out = {}
            for reg in sbmod.list_regs(self.state_dir):
                if reg.get("threadOf"):
                    continue
                if not reg.get("alive") and not self._bench_all_regs:
                    continue
                sid = reg.get("sid")
                if not sid:
                    continue
                row = self._live_row(reg, sid)                 # the real dormant-row derivation
                if not self._bench_dormant:
                    st = ""
                    lsv = getattr(sbmod, "last_state_value", None)
                    if lsv is not None:
                        st = lsv(self.state_dir, sid)
                    else:
                        st = (sbmod.last_state(self.state_dir, sid) or {}).get("state") or ""
                    if st:
                        row["state"] = st
                    row["connected"] = True
                out[sid] = row
            return out

    be = BenchSdkBackend.__new__(BenchSdkBackend)
    be.__dict__.update({
        "state_dir": Path(state), "claude_bin": "/bin/false", "sessions": {},
        "_lock": threading.Lock(), "_reg_lock": threading.Lock(), "_pending_ask": {}, "_live": {},
        "_fork_children_memo": None, "_work_key_pin": "", "work_key": "",   # a property with a pin at
        #   HEAD (the pin wins), a plain attribute in older revisions (the instance value wins)
        "_problems": [], "_problem_seq": 0,
        "_problem_lock": threading.Lock(), "_sdk_missing": False, "_turn_seq": {}, "_drive_marks": {},
        "_drive_inflight": set(), "_heal_attempts": {}, "_notify": None, "_poke_cb": None,
        "_push_cb": None, "_push_session_cb": None, "_todo_lost_cb": None, "_log_cb": None,
        "mcp_config": None, "append_prompt_path": None, "cli_scope": False, "thread_wake_model": None,
        "_bench_dormant": bool(dormant_rows), "_bench_all_regs": bool(all_regs),
    })
    return be


# ── loading ─────────────────────────────────────────────────────────────────────────────────────
def load_kernel(repo):
    from importlib.machinery import SourceFileLoader
    kpath = os.path.join(repo, "kernel", "kernel.py")
    if not os.path.isfile(kpath):
        raise BenchError("no kernel at %s" % kpath)
    km = SourceFileLoader("romp_kernel_perf_bench", kpath).load_module()
    sbmod = sys.modules.get("romp_sdk_backend")
    if sbmod is None:
        sbmod = SourceFileLoader("romp_sdk_backend", os.path.join(repo, "kernel", "sdk_backend.py")).load_module()
    for sym in ("_live_scope", "Sessions", "build_session", "build_feed", "build_timeline", "_push",
                "_names_snapshot", "_sessions", "_parse", "_parse_cache", "_tmux_sessions"):
        if not hasattr(km, sym):
            raise BenchError("this kernel lacks %s; the harness does not know how to drive it" % sym)
    return km, sbmod


def git_head(repo):
    """The checkout's HEAD sha (12 chars) read from the git files directly — no `git` process, so a
    strace of this tool shows only the kernel's own spawns. None when it cannot be read."""
    try:
        dotgit = os.path.join(repo, ".git")
        gitdir = dotgit
        if os.path.isfile(dotgit):                       # a worktree: one line, gitdir: <private dir>
            with open(dotgit) as f:
                line = f.readline().strip()
            if not line.startswith("gitdir:"):
                return None
            gitdir = line[len("gitdir:"):].strip()
            if not os.path.isabs(gitdir):
                gitdir = os.path.normpath(os.path.join(repo, gitdir))
        with open(os.path.join(gitdir, "HEAD")) as f:
            head = f.read().strip()
        if not head.startswith("ref:"):
            return head[:12]
        ref = head[4:].strip()
        common = gitdir
        cf = os.path.join(gitdir, "commondir")           # a worktree's refs live in the main repo's dir
        if os.path.isfile(cf):
            with open(cf) as f:
                common = os.path.normpath(os.path.join(gitdir, f.read().strip()))
        rp = os.path.join(common, ref)
        if os.path.isfile(rp):
            with open(rp) as f:
                return f.read().strip()[:12]
        with open(os.path.join(common, "packed-refs")) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 2 and parts[1] == ref:
                    return parts[0][:12]
    except OSError:
        return None
    return None


# ── timing ──────────────────────────────────────────────────────────────────────────────────────
def ms_stats(samples):
    return {"n": len(samples), "min": round(min(samples), 2), "median": round(statistics.median(samples), 2),
            "max": round(max(samples), 2), "mean": round(statistics.fmean(samples), 2)}


def timed(fn, iters, before=None, warmup=1):
    """Call `before` (untimed) then `fn` (timed), `warmup` times discarded, then `iters` times kept."""
    last = None
    for _ in range(warmup):
        if before:
            before()
        last = fn()
    samples = []
    for _ in range(iters):
        if before:
            before()
        t0 = time.perf_counter()
        last = fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return ms_stats(samples), last


def profile_once(fn, before=None):
    if before:
        before()
    pr = cProfile.Profile()
    pr.enable()
    t0 = time.perf_counter()
    fn()
    ms = (time.perf_counter() - t0) * 1000.0
    pr.disable()
    return pr, ms


def profile_rows(pr, key, top, repo):
    st = pstats.Stats(pr)
    idx = 3 if key == "cumulative" else 2
    rows = []
    for (fn, line, name), (cc, nc, tt, ct, _callers) in st.stats.items():
        rows.append((ct if idx == 3 else tt, fn, line, name, nc, cc, tt, ct))
    rows.sort(key=lambda r: r[0], reverse=True)
    out = []
    repo_p = os.path.realpath(repo) + os.sep
    for _k, fn, line, name, nc, cc, tt, ct in rows[:top]:
        f = fn
        if f.startswith(repo_p):
            f = f[len(repo_p):]
        elif f.startswith("<") or f.startswith("~"):
            pass
        else:
            f = os.path.basename(f)
        out.append({"func": name, "file": f, "line": line, "ncalls": nc if nc == cc else "%d/%d" % (nc, cc),
                    "tottime_ms": round(tt * 1000, 2), "cumtime_ms": round(ct * 1000, 2)})
    return out


def fmt_profile(title, rows):
    lines = ["  %s" % title, "  %10s %12s %12s  %s" % ("ncalls", "tottime ms", "cumtime ms", "function")]
    for r in rows:
        lines.append("  %10s %12.2f %12.2f  %s:%s(%s)" % (r["ncalls"], r["tottime_ms"], r["cumtime_ms"],
                                                        r["file"], r["line"], r["func"]))
    return "\n".join(lines)


# ── state fingerprint (what did the run write) ──────────────────────────────────────────────────
def fingerprint(state):
    out = {}
    for root, dirs, files in os.walk(state):
        dirs[:] = [d for d in dirs if d != "sdkvenv"]
        for f in files:
            p = os.path.join(root, f)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            out[os.path.relpath(p, state)] = (st.st_mtime_ns, st.st_size)
    return out


def fingerprint_diff(before, after):
    changed = sorted(k for k in after if k in before and after[k] != before[k])
    new = sorted(k for k in after if k not in before)
    gone = sorted(k for k in before if k not in after)
    return {"changed": len(changed), "new": len(new), "removed": len(gone),
            "sample": (["~ " + k for k in changed] + ["+ " + k for k in new] + ["- " + k for k in gone])[:40]}


# ── fake WebSocket clients ──────────────────────────────────────────────────────────────────────
def fake_client(km, app, active=None):
    c = {"app": app, "wid": "perf-bench-" + app, "alive": True, "ready": True, "sock": None,
         "dlock": threading.RLock(), "qlock": threading.Lock(), "sent": {}, "echat": {},
         "delta": True, "caps": set(), "bytes": {}, "frames": 0}
    for cap in ("FEED_DELTA_CAP", "READY_GATE_CAP"):
        if hasattr(km, cap):
            c["caps"].add(getattr(km, cap))
    if active:
        c["active"] = active

    def send(s):
        key = c.get("curSlot")
        label = km._perf_slot(key) if hasattr(km, "_perf_slot") else str(key)
        c["bytes"][label] = c["bytes"].get(label, 0) + len(s)
        c["frames"] += 1
    c["send"] = send
    return c


def reset_client_bytes(clients):
    for c in clients:
        c["bytes"] = {}
        c["frames"] = 0


def client_bytes(clients):
    return {c["app"]: {"frames": c["frames"], "slots": dict(sorted(c["bytes"].items()))} for c in clients}


# ── the run ─────────────────────────────────────────────────────────────────────────────────────
def run(args, state, mirror_of, out):
    private = tempfile.mkdtemp(prefix="romp-perf-private-")
    repo = os.path.realpath(args.repo) if args.repo else os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
    out["repo"], out["repo_head"], out["state"], out["state_mirror_of"] = repo, git_head(repo), state, mirror_of
    out["env_changes"] = prepare_env(state, args.claude_dir, private)
    fp_before = fingerprint(state)
    threads_before = {t.name for t in threading.enumerate()}

    km, sbmod = load_kernel(repo)
    jd = km.jd
    be = make_backend(sbmod, state, args.dormant_rows, args.all_regs_live)
    km._sdk_backend = be                       # _sdk() returns this without constructing the real one
    if hasattr(km, "_codex_backend"):
        km._codex_backend = False              # "module unavailable": _codex() returns None, loads nothing
    out["neutralized"], rec = install_guards(km, sbmod, no_git=args.no_git)
    bench = out["benchmarks"] = {}
    profiles = out["profiles"] = {}
    iters = max(1, args.iters)

    def now():
        return int(time.time())

    def scope(tmux):
        km._live_scope.snapshot = tmux
        km._live_scope.paths = {}
        km._live_scope.names = km._names_snapshot()

    def unscope():
        km._live_scope.snapshot = None
        km._live_scope.names = None
        km._live_scope.paths = None

    def clear_chat_caches():
        km._parse_cache.clear()
        if hasattr(km, "_chat_fold_lock"):
            with km._chat_fold_lock:
                km._chat_fold.clear()
        elif hasattr(km, "_chat_fold"):
            km._chat_fold.clear()
        for name in ("_built_chat", "_prev_chat_events", "_prev_chat_ledger", "_arch_tops_cache"):
            d = getattr(km, name, None)
            if isinstance(d, dict):
                d.clear()
        gc.collect()

    # liveness + names snapshots (the pusher cycle's per-cycle reads)
    bench["liveness_snapshot"], tmux = timed(lambda: km.Sessions.live(), iters)
    bench["names_snapshot"], _ = timed(lambda: km._names_snapshot(), iters)
    regs = sbmod.list_regs(state)
    expected = sum(1 for r in regs if not r.get("threadOf") and (r.get("alive") or args.all_regs_live))
    if len(tmux) != expected:
        # Sessions.live() catches and logs a failing backend merge and carries on with whatever rows it
        # has, so a bench backend that a kernel revision drives differently would otherwise be timed
        # against an empty or partial world and report success. Exact by construction: every counted reg
        # must produce exactly one row.
        raise BenchError("liveness snapshot has %d rows but %d registry entries qualify — the backend merge "
                         "failed inside the kernel (its traceback is on stderr); the bench backend needs "
                         "adjusting for this revision" % (len(tmux), expected))
    out["liveness"] = {"live": len(tmux), "alive_regs": sum(1 for r in regs if r.get("alive") and not r.get("threadOf")),
                       "closed_regs": sum(1 for r in regs if not r.get("alive") and not r.get("threadOf")),
                       "thread_regs": sum(1 for r in regs if r.get("threadOf")),
                       "rows": "dormant" if args.dormant_rows else "states-file"}
    scope(tmux)
    try:
        # discovery
        def cold_discover():
            cache = getattr(jd, "_discover_cache", None)
            if isinstance(cache, dict):
                cache.clear()
        bench["discover_cold"], _ = timed(lambda: jd.discover(now()), iters, before=cold_discover)
        bench["discover_warm"], _ = timed(lambda: jd.discover(now()), iters)

        # the live sessions discovery knows about, largest transcripts first
        sessions = [s for s in km._sessions(now()) if s["sid"] in tmux]
        for s in sessions:
            try:
                s["bytes"] = os.path.getsize(s["path"])
            except OSError:
                s["bytes"] = 0
        sessions.sort(key=lambda s: s["bytes"], reverse=True)
        picked = sessions[:max(0, args.sessions)]
        out["live_transcripts"] = {"count": len(sessions), "bytes": sum(s["bytes"] for s in sessions)}

        # warm every live parse once from empty (the boot-time cost), keep it warm for the feed/timeline
        km._parse_cache.clear()
        t0 = time.perf_counter()
        for s in sessions:
            km._parse(s["path"], s["sid"], now())
        bench["warm_all_parses"] = {"n": 1, "min": None, "median": round((time.perf_counter() - t0) * 1000, 2),
                                    "max": None, "mean": None, "sessions": len(sessions)}

        # build_session, cold then warm, per picked transcript
        out["benched_sessions"] = []
        for s in picked:
            sid, tag = s["sid"], s["sid"][:8]
            km._live_scope.paths = {}
            st_cold, m = timed(lambda: km.build_session(sid, now(), tmux), iters, before=clear_chat_caches)
            st_warm, m2 = timed(lambda: km.build_session(sid, now(), tmux), iters)
            bench["build_session_cold:" + tag] = st_cold
            bench["build_session_warm:" + tag] = st_warm
            out["benched_sessions"].append({"sid8": tag, "name": s.get("name", ""), "bytes": s["bytes"],
                                            "events": len((m or {}).get("events") or [])})
            if args.profile:
                pr, ms = profile_once(lambda: km.build_session(sid, now(), tmux), before=clear_chat_caches)
                profiles["build_session_cold:" + tag] = {"ms": round(ms, 2),
                                                         "cumulative": profile_rows(pr, "cumulative", PROFILE_TOP, repo),
                                                         "tottime": profile_rows(pr, "tottime", PROFILE_TOP, repo)}
                pr, ms = profile_once(lambda: km.build_session(sid, now(), tmux))
                profiles["build_session_warm:" + tag] = {"ms": round(ms, 2),
                                                         "cumulative": profile_rows(pr, "cumulative", PROFILE_TOP, repo),
                                                         "tottime": profile_rows(pr, "tottime", PROFILE_TOP, repo)}
        # re-warm every parse (the cold builds emptied the cache) so the feed/timeline see the steady state
        for s in sessions:
            km._parse(s["path"], s["sid"], now())

        # feed + timeline in the steady state
        bench["build_feed"], feed = timed(lambda: km.build_feed(now(), tmux), iters)
        bench["build_feed"]["cards"] = {k: len(feed.get(k) or []) for k in ("asks", "working", "awaiting") if isinstance(feed, dict)}
        bench["build_timeline_bars"], tl = timed(lambda: km.build_timeline(now(), tmux, with_bars=True), iters)
        bench["build_timeline_bars"]["lanes"] = len((tl or {}).get("sessions") or [])
        bench["build_timeline_skel"], _ = timed(lambda: km.build_timeline(now(), tmux, with_bars=False), iters)
        if args.profile:
            for label, fn in (("build_feed", lambda: km.build_feed(now(), tmux)),
                              ("build_timeline_bars", lambda: km.build_timeline(now(), tmux, with_bars=True))):
                pr, ms = profile_once(fn)
                profiles[label] = {"ms": round(ms, 2), "cumulative": profile_rows(pr, "cumulative", PROFILE_TOP, repo),
                                   "tottime": profile_rows(pr, "tottime", PROFILE_TOP, repo)}
        # the feed with nothing parsed (cards-first boot)
        bench["build_feed_noparse"], _ = timed(lambda: km.build_feed(now(), tmux), iters, before=km._parse_cache.clear)
        for s in sessions:
            km._parse(s["path"], s["sid"], now())

        # goal stores, largest first
        gdir = Path(jd.GOALDIR)
        stores = []
        if gdir.is_dir():
            for p in gdir.glob("*.json"):
                try:
                    stores.append((p.stat().st_size, p.stem))
                except OSError:
                    pass
        stores.sort(reverse=True)
        out["goal_stores"] = []
        for size, fsid in stores[:max(0, args.sessions)]:
            tag = fsid[:8]
            bench["load_goals:" + tag], store = timed(lambda: jd.load_goals(fsid), iters)
            out["goal_stores"].append({"fsid8": tag, "bytes": size, "nodes": len((store or {}).get("nodes") or {})})
            if args.profile and not any(k.startswith("load_goals:") for k in profiles):
                pr, ms = profile_once(lambda: jd.load_goals(fsid))
                profiles["load_goals:" + tag] = {"ms": round(ms, 2), "cumulative": profile_rows(pr, "cumulative", PROFILE_TOP, repo),
                                                 "tottime": profile_rows(pr, "tottime", PROFILE_TOP, repo)}

        # the push over fake clients
        apps = [a.strip() for a in (args.clients or "").split(",") if a.strip()]
        if apps:
            active = picked[0]["sid"] if picked else None
            clients = [fake_client(km, a, active if a == "chat" else None) for a in apps]
            clear_chat_caches()
            for name in ("_built_feed", "_built_timeline"):
                e = getattr(km, name, None)
                if isinstance(e, list) and len(e) >= 2:
                    e[1] = None
            for name in ("_feed_wire", "_bars_wire"):
                if hasattr(km, name):
                    setattr(km, name, None)
            unscope()
            scope(tmux)
            t0 = time.perf_counter()
            km._push(clients, tmux=tmux)
            bench["push_connect"] = {"n": 1, "min": None, "median": round((time.perf_counter() - t0) * 1000, 2),
                                     "max": None, "mean": None, "bytes": client_bytes(clients)}
            reset_client_bytes(clients)

            def one_push():
                km._live_scope.paths = {}
                km._push(clients, tmux=tmux)
            st, _ = timed(one_push, iters, warmup=0)
            st["bytes"] = client_bytes(clients)
            st["clients"] = apps
            bench["push_steady"] = st
            if args.profile:
                pr, ms = profile_once(one_push)
                profiles["push_steady"] = {"ms": round(ms, 2), "cumulative": profile_rows(pr, "cumulative", PROFILE_TOP, repo),
                                           "tottime": profile_rows(pr, "tottime", PROFILE_TOP, repo)}
    finally:
        unscope()

    out["writes"] = fingerprint_diff(fp_before, fingerprint(state))
    out["writes"]["atomic_writes"] = sorted(set(rec["atomic_writes"]))
    out["notifications_suppressed"] = len(rec["notifications"])
    out["spawn_attempts"] = rec["spawns"]
    git = {}
    for tw in rec["tripwires"]:
        for sub, n in tw.git_calls.items():
            git[sub] = git.get(sub, 0) + n
    out["git_queries"] = {"answered_as_failure": bool(args.no_git), "calls": git}
    out["threads_new"] = sorted({t.name for t in threading.enumerate()} - threads_before)
    return out


# ── reporting ───────────────────────────────────────────────────────────────────────────────────
def fmt_ms(v):
    return "%9.2f" % v if isinstance(v, (int, float)) else "%9s" % "-"


def render_text(out, profile):
    L = []
    L.append("perf-bench  repo=%s (%s)  state=%s%s" % (out["repo"], out.get("repo_head") or "no git",
                                                     out["state"], ("  [mirror of %s]" % out["state_mirror_of"]) if out.get("state_mirror_of") else ""))
    lv = out.get("liveness", {})
    L.append("liveness: %d live rows (%d alive regs, %d closed, %d threads skipped; rows from %s); "
             "%d live transcripts discovered, %.1f MB total" % (lv.get("live", 0), lv.get("alive_regs", 0), lv.get("closed_regs", 0),
                                                              lv.get("thread_regs", 0), lv.get("rows", "?"),
                                                              out.get("live_transcripts", {}).get("count", 0),
                                                              out.get("live_transcripts", {}).get("bytes", 0) / 1e6))
    if out.get("benched_sessions"):
        L.append("transcripts benched: " + ", ".join("%s (%.1f MB, %d events)" % (s["sid8"], s["bytes"] / 1e6, s["events"])
                                                    for s in out["benched_sessions"]))
    if out.get("goal_stores"):
        L.append("goal stores benched: " + ", ".join("%s (%.0f KB, %d nodes)" % (g["fsid8"], g["bytes"] / 1e3, g["nodes"])
                                                     for g in out["goal_stores"]))
    L.append("")
    L.append("%-34s %4s %9s %9s %9s" % ("benchmark", "n", "min ms", "median", "max"))
    for name, st in out["benchmarks"].items():
        L.append("%-34s %4d %s %s %s" % (name, st.get("n", 0), fmt_ms(st.get("min")), fmt_ms(st.get("median")), fmt_ms(st.get("max"))))
    for name in ("push_connect", "push_steady"):
        st = out["benchmarks"].get(name)
        if st and st.get("bytes"):
            L.append("")
            L.append("%s bytes per client slot:" % name)
            for app, d in st["bytes"].items():
                slots = ", ".join("%s=%d" % (k, v) for k, v in d["slots"].items()) or "nothing sent"
                L.append("  %-9s %4d frames  %s" % (app, d["frames"], slots))
    L.append("")
    w = out.get("writes", {})
    L.append("writes into the state copy: %d changed, %d new, %d removed" % (w.get("changed", 0), w.get("new", 0), w.get("removed", 0)))
    for s in w.get("sample", []):
        L.append("  " + s)
    L.append("neutralized: " + ", ".join(out.get("neutralized", [])))
    g = out.get("git_queries", {})
    L.append("git read-only queries %s: %s" % ("answered as failures (--no-git)" if g.get("answered_as_failure") else "run",
                                             ", ".join("%s=%d" % kv for kv in sorted(g.get("calls", {}).items())) or "none"))
    L.append("notifications suppressed: %d; refused spawns: %d; new threads: %s"
             % (out.get("notifications_suppressed", 0), len(out.get("spawn_attempts", [])), out.get("threads_new") or "none"))
    if profile and out.get("profiles"):
        for name, p in out["profiles"].items():
            L.append("")
            L.append("profile %s (%.1f ms under cProfile)" % (name, p["ms"]))
            L.append(fmt_profile("top %d by cumulative time" % PROFILE_TOP, p["cumulative"]))
            L.append(fmt_profile("top %d by own time" % PROFILE_TOP, p["tottime"]))
    return "\n".join(L)


def compare(a_path, b_path):
    with open(a_path) as f:
        a = json.load(f)
    with open(b_path) as f:
        b = json.load(f)
    L = ["perf-bench compare  A=%s (%s)  B=%s (%s)" % (a_path, a.get("repo_head") or "?", b_path, b.get("repo_head") or "?")]
    L.append("%-34s %9s %9s %10s %8s" % ("benchmark", "A median", "B median", "delta ms", "delta %"))
    ab, bb = a.get("benchmarks", {}), b.get("benchmarks", {})
    for name in ab:
        if name not in bb:
            continue
        ma, mb = ab[name].get("median"), bb[name].get("median")
        if not isinstance(ma, (int, float)) or not isinstance(mb, (int, float)):
            continue
        d = mb - ma
        pct = (d / ma * 100.0) if ma else float("inf")
        L.append("%-34s %9.2f %9.2f %+10.2f %+7.1f%%" % (name, ma, mb, d, pct))
    only_a = sorted(set(ab) - set(bb))
    only_b = sorted(set(bb) - set(ab))
    if only_a:
        L.append("only in A: " + ", ".join(only_a))
    if only_b:
        L.append("only in B: " + ", ".join(only_b))
    for name in ("push_connect", "push_steady"):
        ba, bbb = (ab.get(name) or {}).get("bytes"), (bb.get(name) or {}).get("bytes")
        if ba and bbb:
            for app in ba:
                if app in bbb:
                    ta = sum(ba[app]["slots"].values())
                    tb = sum(bbb[app]["slots"].values())
                    L.append("%s bytes %-9s A=%d B=%d delta=%+d" % (name, app, ta, tb, tb - ta))
    return "\n".join(L)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.compare:
        print(compare(*args.compare))
        return 0
    if not args.state:
        sys.stderr.write("perf-bench: --state DIR is required (or --compare A B)\n")
        return 2
    state = os.path.realpath(os.path.expanduser(args.state))
    if not os.path.isdir(state):
        sys.stderr.write("perf-bench: %s is not a directory\n" % state)
        return 2
    for sub in ("sdk", "names"):
        if not os.path.isdir(os.path.join(state, sub)):
            sys.stderr.write("perf-bench: %s has no %s/ — not a romp state directory?\n" % (state, sub))
            return 2
    mirror_of = None
    if state in live_state_dirs(os.environ):
        if not args.i_know_this_is_live:
            sys.stderr.write("perf-bench: %s is the LIVE state directory. Bench a copy (see --help), or pass "
                             "--i-know-this-is-live to have it mirrored to a temp directory first.\n" % state)
            return 2
        mirror_of, state = state, mirror_state(state)
        sys.stderr.write("perf-bench: mirrored the live directory to %s (sdkvenv excluded); benching the mirror\n" % state)
    out = {"schema": SCHEMA, "tool": "perf-bench", "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "python": sys.version.split()[0], "iters": args.iters, "sessions_requested": args.sessions}
    run(args, state, mirror_of, out)
    print(render_text(out, args.profile))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(out, f, indent=1, sort_keys=True)
        print("\njson written to %s" % args.json)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BenchError as e:
        sys.stderr.write("perf-bench: %s\n" % e)
        sys.exit(1)
