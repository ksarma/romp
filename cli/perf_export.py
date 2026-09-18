#!/usr/bin/env python3
"""romp-perf-export: write one paste-safe copy of the kernel's performance counters. `romp perf export --public`.

    romp perf export --public [--from SNAPSHOT.json] [--usage] [--out PATH]

Reads GET /perf from the running kernel the way `romp perf` does (the serve token from ROMP_SERVE_TOKEN or the
state directory's serve-token file, the port from ROMP_KERNEL_PORT or 29855, a ten-second timeout, a dead
kernel and a refused token each said plainly), or takes a snapshot `romp perf --json` saved earlier (--from),
and writes the PUBLIC form of it: the shape rule and the denylist of cli/perf_public.py applied to the whole
snapshot, under a top-level `schema` line (`romp-perf-export/1`), the UTC minute of the export (no seconds) and,
when the snapshot carries the kernel's commit, its twelve-character abbreviation. No hostname, path, pid,
session id or username is written; the finished document is walked once more (perf_public.paste_problems) and
searched for the strings only this machine knows (perf_public.identifier_hits), and either finding refuses the
write naming the key path, never the value. `--usage` adds a `usage` block, off by default: the session counts,
the feature counts (the user's own actions and the panes opened, from the http table's route counts) and the
kernel's uptime bucket, all from keys the snapshot already carries and folded the same way.

The file lands under the state directory as `perf-exports/perf-export-<YYYYMMDDTHHMM>.json`, mode 0600, or at
--out; the path and the byte size are printed, exit 0. Nothing leaves the machine: the user reads the file and
posts it by hand. The flag is required and the verb has no other mode, so a raw snapshot is never written by
habit: without --public it refuses with one line and exit 2. A reader for the terminal, never a kernel module.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))   # cli/, whether run through the bin/ symlink or loaded by path
import perf_public as pp  # noqa: E402

PROG = "romp perf export"
SCHEMA = "romp-perf-export/1"
TIMEOUT_S = 10          # `romp perf`'s curl -m
DEFAULT_PORT = 29855
EXPORT_DIR = "perf-exports"
COMMIT_KEYS = ("kernel_sha", "kernel_commit", "commit", "sha")
COMMIT = re.compile(r"[0-9a-fA-F]{7,64}")
# The http routes that count as the user's own actions (POST) and the panes they opened (GET), as feature names.
ACTION_SKIP = frozenset({"/tick", "/perf", "/push/ack", "/push/dropped", "/push/landed", "/push/superseded",
                         "/checkin", "/checkin/stop", "/working", "/notice", "/postal-notice", "/deliver"})
VIEW_ROUTES = ("/chat", "/feed", "/timeline", "/fleet", "/waiting", "/analytics", "/files", "/file", "/usage",
               "/usage/fleet", "/spend/detail", "/session-events", "/handoff", "/views", "/tunnels")
UPTIME_BUCKETS = ((3600, "lt1h"), (86400, "1h-24h"), (7 * 86400, "1d-7d"), (float("inf"), "gt7d"))


def state_dir() -> Path:
    return Path(os.environ.get("ROMP_STATE_DIR")
                or Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local/state")) / "romp")


def _token(state: Path) -> str:
    env = os.environ.get("ROMP_SERVE_TOKEN")
    if env:
        return env
    try:
        return (state / "serve-token").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _port() -> int:
    env = os.environ.get("ROMP_KERNEL_PORT")
    return int(env) if env and env.isdigit() else DEFAULT_PORT


class ReadError(Exception):
    pass


def read_kernel(state: Path) -> dict:
    """One GET /perf, the token on the header (never argv), `romp perf`'s wording for what can go wrong."""
    port = _port()
    url = "http://127.0.0.1:%d/perf" % port
    tok = _token(state)
    req = urllib.request.Request(url, headers={"X-Romp-Token": tok} if tok else {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ReadError("the kernel on :%d refused the serve token (HTTP %d); is ROMP_KERNEL_PORT pointing at another kernel?"
                            % (port, e.code))
        raise ReadError("the kernel on :%d answered HTTP %d" % (port, e.code))
    except (urllib.error.URLError, OSError, TimeoutError):
        raise ReadError("kernel not reachable on :%d (is romp running?)" % port)
    try:
        snap = json.loads(raw)
    except ValueError:
        raise ReadError("the kernel on :%d did not answer JSON on GET /perf" % port)
    if not isinstance(snap, dict):
        raise ReadError("the kernel on :%d answered GET /perf with something other than an object" % port)
    return snap


def read_file(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            snap = json.load(fh)
    except FileNotFoundError:
        raise ReadError("%s does not exist" % path)
    except OSError as e:
        raise ReadError("%s: %s" % (path, e.__class__.__name__))
    except ValueError:
        raise ReadError("%s is not JSON" % path)
    if not isinstance(snap, dict):
        raise ReadError("%s is not a JSON object (a `romp perf --json` snapshot)" % path)
    return snap


def kernel_commit(snap: dict):
    """The snapshot's kernel commit, abbreviated to twelve hex characters, or None when it carries none. /perf
    carries none today; a later kernel may add one, and a saved snapshot may have had one written beside it."""
    for k in COMMIT_KEYS:
        v = snap.get(k)
        if isinstance(v, str) and COMMIT.fullmatch(v):
            return v[:12].lower()
    return None


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _feature_name(path: str) -> str:
    return path.strip("/").replace("/", ".") or "root"


def usage_block(snap: dict) -> dict:
    """Usage counts from keys the snapshot already carries. Sessions: the sessions the kernel parsed
    (`parses.perSession.sessions`, or the size of an older kernel's per-sid table), the sessions with a chat
    build (`builds.chat.bySession`), the sessions stamped (`caches.session_stamp.entries`). Features: each
    POST route's count as an action (the kernel's own housekeeping posts left out) and each pane route's GET
    count as a view. Lifetime: the kernel's own uptime bucket. Per-session lifetimes are not in /perf (they are
    the sessions listing's), so the block has none."""
    out = {"sessions": {}, "actions": {}, "views": {}}
    parses = snap.get("parses") if isinstance(snap.get("parses"), dict) else {}
    per = parses.get("perSession")
    if isinstance(per, dict) and _num(per.get("sessions")) is not None:
        out["sessions"]["parsed"] = per["sessions"]
    elif isinstance(parses.get("bySid"), dict):
        out["sessions"]["parsed"] = len(parses["bySid"])
    builds = snap.get("builds") if isinstance(snap.get("builds"), dict) else {}
    chat = builds.get("chat") if isinstance(builds.get("chat"), dict) else {}
    if isinstance(chat.get("bySession"), list):
        out["sessions"]["chatBuilt"] = len(chat["bySession"])
    caches = snap.get("caches") if isinstance(snap.get("caches"), dict) else {}
    stamp = caches.get("session_stamp") if isinstance(caches.get("session_stamp"), dict) else {}
    if _num(stamp.get("entries")) is not None:
        out["sessions"]["stamped"] = stamp["entries"]
    http = snap.get("http") if isinstance(snap.get("http"), dict) else {}
    for key, row in http.items():
        if not (isinstance(key, str) and isinstance(row, dict) and pp.http_key_ok(key)) or key == pp.OTHER:
            continue
        count = _num(row.get("count"))
        if count is None:
            continue
        method, _, path = key.partition(" ")
        if method == "POST" and path in pp.HTTP_ROUTES["POST"] and path not in ACTION_SKIP:
            out["actions"][_feature_name(path)] = count
        elif method == "GET" and path in VIEW_ROUTES:
            out["views"][_feature_name(path)] = count
    up = _num(snap.get("uptime_s"))
    if up is not None:
        out["kernelUptime"] = next(name for bound, name in UPTIME_BUCKETS if up < bound)
    return out


def export_document(snap: dict, usage=False, now=None) -> dict:
    """The document the file holds: the envelope and the folded snapshot (and usage block). The envelope is
    added AFTER the fold, so the schema line's slash is the one string outside the grammar, by design."""
    now = now or datetime.now(timezone.utc)
    doc = {"schema": SCHEMA, "exported_at": now.strftime("%Y-%m-%dT%H:%MZ")}
    commit = kernel_commit(snap)
    if commit:
        doc["kernel_commit"] = commit
    doc["perf"] = pp.fold(snap)
    for k in COMMIT_KEYS:
        doc["perf"].pop(k, None)          # lifted into the envelope above, abbreviated; not a counter
    if usage:
        doc["usage"] = pp.fold(usage_block(snap))
    return doc


def check_document(doc: dict, state: Path):
    """None when the finished document may be written; else the one-line reason (a key path, never a value)."""
    problems = pp.paste_problems(doc, skip=("schema",), under=("perf",))
    if problems:
        return "the public form still fails the walk (%s); nothing written" % problems[0].split(" at ", 1)[-1]
    hits = pp.identifier_hits(doc, pp.machine_probes(state), skip=("schema",))
    if hits:
        kind, where = hits[0]
        return "a string this machine knows (%s) survives as %s; nothing written" % (kind, where)
    return None


def default_path(state: Path, now=None) -> Path:
    now = now or datetime.now(timezone.utc)
    return state / EXPORT_DIR / ("perf-export-%s.json" % now.strftime("%Y%m%dT%H%M"))


def write_file(path: Path, text: str) -> int:
    """Create or replace `path` as a regular file readable by the owner alone; the byte count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(path), flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, data)
    finally:
        os.close(fd)
    return len(data)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog=PROG, description=__doc__.split("\n\n")[0],
                                 usage="%(prog)s --public [--from SNAPSHOT.json] [--usage] [--out PATH]")
    ap.add_argument("--public", action="store_true", help="write the public form (required; there is no raw mode)")
    ap.add_argument("--from", dest="src", metavar="SNAPSHOT.json", help="a saved `romp perf --json` snapshot instead of the running kernel")
    ap.add_argument("--usage", action="store_true", help="add the usage block (session counts, actions, views, uptime bucket)")
    ap.add_argument("--out", metavar="PATH", help="write here instead of <state>/%s/perf-export-<YYYYMMDDTHHMM>.json" % EXPORT_DIR)
    a = ap.parse_args(argv)
    if not a.public:
        sys.stderr.write("%s: refused: this verb writes only the public form of the snapshot; pass --public (there is no raw mode)\n" % PROG)
        return 2
    state = state_dir()
    try:
        snap = read_file(a.src) if a.src else read_kernel(state)
    except ReadError as e:
        sys.stderr.write("%s: %s\n" % (PROG, e))
        return 1
    now = datetime.now(timezone.utc)
    doc = export_document(snap, usage=a.usage, now=now)
    reason = check_document(doc, state)
    if reason:
        sys.stderr.write("%s: refused: %s\n" % (PROG, reason))
        return 1
    path = Path(a.out) if a.out else default_path(state, now)
    try:
        n = write_file(path, json.dumps(doc, indent=1, sort_keys=True) + "\n")
    except OSError as e:
        sys.stderr.write("%s: cannot write %s (%s)\n" % (PROG, path, e.__class__.__name__))
        return 1
    print("%s (%d bytes)" % (path, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
