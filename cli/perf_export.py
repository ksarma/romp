#!/usr/bin/env python3
"""romp-perf-export: write one paste-safe copy of the kernel's performance counters. `romp perf export --public`.

    romp perf export --public [--from SNAPSHOT.json] [--usage] [--out PATH]

Reads GET /perf from the running kernel the way `romp perf` does (the serve token from ROMP_SERVE_TOKEN or the
state directory's serve-token file, the port from ROMP_KERNEL_PORT or 29855, a ten-second timeout, a dead
kernel, a refused token and a ROMP_KERNEL_PORT that is not a port number each said plainly, never replaced by
the default), or takes a snapshot `romp perf --json` saved earlier (--from); either must carry GET /perf's fixed
top-level blocks (SNAPSHOT_KEYS), so a registry row or a sessions listing handed to --from is refused at the
read rather than folded and labelled an export. From a running kernel the verb also reads GET /version on the
same port (auth-exempt) for the kernel's commit, `kernel_sha` (git's short sha, `-dirty` appended when the
checkout has uncommitted edits), and sets it on the snapshot; a /version that does not answer, or answers no
hex sha, leaves the snapshot as it was. It writes the PUBLIC form of the snapshot: the shape rule and the
denylist of cli/perf_public.py applied to the whole snapshot, under a top-level `schema` line
(`romp-perf-export/1`), the UTC minute of the export (no seconds) and, when the snapshot carries the kernel's
commit (from /version, or written beside a saved snapshot), its abbreviation to at most twelve hex characters,
the `-dirty` suffix stripped. The public form is PASTE-SAFE, not unlinkable (the rule of the third review
round, 2026-09-18): it removes identifiers, paths, free text, machine strings and every absolute clock stamp
(every `t`, the wall clock at a cycle's close; the snapshot's `now` and `since`), rounds the kernel's uptime
down to whole minutes and the ten memory-fraction bounds up to a power of two (each a fixed fraction of the
machine's MemTotal, one of them half of it); durations stay, and per-process and per-machine MEASUREMENTS stay
by design (the boot's stage split under pusher.firstCycle and jobs.firstPass, whole; the lifetime maxima; every
counter), because they are the data a reader wants, so two exports from one kernel life, or from one machine,
remain linkable through them. No hostname, path, pid, session id, username or clock stamp is written; the finished document
is searched for the strings only this machine knows (perf_public.identifier_hits), walked once more
(perf_public.paste_problems) and walked for the denylist (perf_public.denylist_problems: a key the fold drops, an
uptime not on whole minutes, a bound not on a power of two, a number the size of a clock stamp under any other key; a
fold's own output carries none of the four, so here it is a belt, and for `romp perf upload`, which runs the same
check over a file the user may have edited, it is the check that what the export dropped or coarsened does not
travel, while the measurements it keeps pass, the export's own rule: paste-safe, not unlinkable); any finding refuses
the write, and the SHALLOWEST finding across the three is
the one named (check_document), so a walk problem beneath a machine-named key is reported as the machine string, not
as a path spelling the key, and a machine string beneath a key the walk refuses (a 32-hex token) is reported as
that key's rule and its dict, not as a path spelling the token. The refusal is built from the finding's fields
(the kind of string or rule, and the key path: a value's own path, or the path of the dict holding a key), never
from a line that carries the flagged text, so a key or value containing " at " cannot put a fragment of itself
into the refusal. `--usage` adds a `usage` block, off by default: the session counts, the feature counts (the
user's own actions and the panes opened, from the http table's route counts) and the kernel's uptime bucket, all
from keys the snapshot already carries and folded the same way.

The file lands under the state directory as `perf-exports/perf-export-<YYYYMMDDTHHMM>.json`, mode 0600, or at
--out (a write that fails partway removes the file rather than leave a truncated one); the path and the byte
size are printed, exit 0. Nothing leaves the machine: the user reads the file and
posts it by hand. The flag is required and the verb has no other mode, so a raw snapshot is never written by
habit: without --public it refuses with one line and exit 2. A reader for the terminal, never a kernel module.
"""
import argparse
import http.client
import json
import math
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
# GET /perf's fixed top-level blocks, present in every kernel since the verb (2026-09-06): what makes an object a
# snapshot. Any other JSON object (a registry row, a listing) would pass the grammar with keys the denylist
# never heard of.
SNAPSHOT_KEYS = ("uptime_s", "process", "pusher", "http")
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


class ReadError(Exception):
    pass


def _port() -> int:
    """ROMP_KERNEL_PORT as a port number, or the default when it is unset or empty. A value that is not a port is a
    ReadError: bin/romp's perf verb dials what it was given and fails on it, and this reader must not dial the
    default instead and export whatever kernel answers there."""
    env = os.environ.get("ROMP_KERNEL_PORT")
    if env is None or env == "":
        return DEFAULT_PORT
    if not env.isdigit() or not 0 < int(env) < 65536:
        raise ReadError("ROMP_KERNEL_PORT is set but is not a port number (1-65535); not read")
    return int(env)


def _snapshot(snap, what: str) -> dict:
    """`snap` when it is a GET /perf snapshot (an object with SNAPSHOT_KEYS); else a ReadError naming `what` and the
    missing blocks, never the contents."""
    if not isinstance(snap, dict):
        raise ReadError("%s is not a JSON object (a `romp perf --json` snapshot)" % what)
    missing = [k for k in SNAPSHOT_KEYS if k not in snap]
    if missing:
        raise ReadError("%s is not a GET /perf snapshot (no %s)" % (what, ", ".join(missing)))
    return snap


def _commit_text(v):
    """`v` as a commit: a string of 7 to 64 hex characters, a trailing `-dirty` (what the kernel's _kernel_sha
    appends when the checkout has uncommitted edits) removed first; None for anything else."""
    if not isinstance(v, str):
        return None
    v = v[:-len("-dirty")] if v.endswith("-dirty") else v
    return v if COMMIT.fullmatch(v) else None


def read_kernel(state: Path) -> dict:
    """One GET /perf, the token on the header (never argv), `romp perf`'s wording for what can go wrong; then one
    GET /version on the same port for the kernel's commit (`kernel_sha`), set on the snapshot when it answers a
    JSON object carrying a hex sha, the snapshot left as it was when it does not (a failure to answer, another
    shape). GET /perf has no commit key of its own, so without this read an export from a running kernel would
    never carry a kernel identity (the export's review, 2026-09-18)."""
    port = _port()
    tok = _token(state)
    headers = {"X-Romp-Token": tok} if tok else {}

    # What a read can raise: HTTPError (an answer with an error status), URLError (a connection that failed, an
    # OSError wrapped), OSError and TimeoutError (the socket), and http.client.HTTPException (an answer that is not
    # HTTP: a status line that is not one, a body shorter than its Content-Length, a header line past the reader's
    # limit); the last is not an OSError and was a traceback until round 2. Not str(e) in any line: BadStatusLine's
    # text is the served line, and a refusal must carry nothing the socket served.
    NOT_HTTP = (urllib.error.URLError, OSError, TimeoutError, http.client.HTTPException)

    def get(route):
        """The body as bytes: decoded where it is parsed (json.loads reads bytes), so bytes that are not UTF-8 are
        the did-not-answer-JSON refusal there, not a UnicodeDecodeError here."""
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, route), headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            return r.read()
    try:
        raw = get("/perf")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ReadError("the kernel on :%d refused the serve token (HTTP %d); is ROMP_KERNEL_PORT pointing at another kernel?"
                            % (port, e.code))
        raise ReadError("the kernel on :%d answered HTTP %d" % (port, e.code))
    except NOT_HTTP:
        raise ReadError("kernel not reachable on :%d (is romp running?)" % port)
    try:
        snap = json.loads(raw)
    except ValueError:      # not JSON, or not UTF-8 (a UnicodeDecodeError is a ValueError)
        raise ReadError("the kernel on :%d did not answer JSON on GET /perf" % port)
    snap = _snapshot(snap, "the kernel's answer on :%d" % port)
    try:
        version = json.loads(get("/version"))
    except NOT_HTTP + (ValueError,):   # HTTPError is a URLError; a /version that does not answer leaves the snapshot as it was
        return snap
    if isinstance(version, dict) and _commit_text(version.get("kernel_sha")):
        snap["kernel_sha"] = version["kernel_sha"]
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
    return _snapshot(snap, path)


def kernel_commit(snap: dict):
    """The snapshot's kernel commit, abbreviated to at most twelve hex characters (a short sha is shorter), or
    None when it carries none. /perf carries none of its own; read_kernel sets GET /version's `kernel_sha` on the
    snapshot (git's short sha, `-dirty` appended for a checkout with uncommitted edits: stripped here), and a
    saved snapshot may have had one written beside it."""
    for k in COMMIT_KEYS:
        v = _commit_text(snap.get(k))
        if v:
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
    if up is not None and math.isfinite(up):   # a NaN or an infinite uptime (json.load accepts both literals) fits no
        out["kernelUptime"] = next(name for bound, name in UPTIME_BUCKETS if up < bound)   # bucket: the key is left out
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


def check_document(doc: dict, state: Path, under=("perf",), tail="nothing written"):
    """None when the finished document may be written; else the one-line reason, built from the finding's fields:
    the kind of string or rule and the key path (a value's own path; for a key, the path of the dict holding it),
    never the key or the value itself. All three mechanisms run, the identifier scan, the walk and the denylist
    walk (pp.denylist_problems: a key the fold drops, an uptime not on whole minutes, a bound not on a power of two,
    or a float the size of a clock stamp with no duration key on its path; an integer that large is a byte total or
    a count, and a float under a duration key, a name carrying the token `ms`, its own or any key above it, is a
    millisecond total, both of which a long-lived kernel's totals reach, so both pass; none of the four a fold's own
    output carries, so for
    this verb it is a
    belt; for `romp perf upload`, over a file as it stands, it is what refuses a `t` the user put back, an uptime
    typed to the second, a bound typed to the byte or a stamp under a new key, and passes every measurement the
    export keeps: paste-safe, not unlinkable, the fold's own rule), and the SHALLOWEST finding is the one named:
    the fewest path components, a key finding counting the depth of the dict holding it and a value finding its
    own, the scan's wording when the depths tie, then the walk's.

    The rule this keeps: the refusal never prints a path component that the walk would refuse to write, nor one
    that spells a string this machine knows, nor one the denylist drops. Every component of a printed path is a key
    of a dict above the finding, and a key any mechanism flags is a finding of its own at a strictly shallower
    depth, so the shallowest finding cannot sit beneath one. Naming the scan's finding first whatever its depth
    (round 1) printed a 32-hex token, the class of key the walk refuses, when a hostname sat beneath it; naming the
    walk's first (the version before) printed a key spelling the hostname when free text sat beneath that.

    `under` is the key path the document's blocks sit below (the export's `perf`; the root for the restart
    document, whose blocks are its top-level keys) and `tail` what the refusal says was not done (this verb's write;
    `romp perf upload`, which runs the same check over a file as it stands, passes "nothing sent"). `romp
    restart-metrics --json --public` runs this same function over its document (`under=()`, "nothing printed"): it
    ran the scan alone and printed a 32-hex token planted in an event row's nested field, the one place raw ledger
    rows pass through, where this verb refused the same document (the export's closing check, 2026-09-18)."""
    findings = [(h.depth, 0, "a string this machine knows (%s) survives as %s" % (h.kind, pp.place(h)))
                for h in pp.identifier_hits(doc, pp.machine_probes(state), skip=("schema",))]
    findings += [(p.depth, 1, "the public form still fails the walk (%s, %s)" % (p.kind, pp.place(p)))
                 for p in pp.paste_problems(doc, skip=("schema",), under=under)]
    findings += [(p.depth, 2, "the public form still fails the denylist (%s, %s)" % (p.kind, pp.place(p)))
                 for p in pp.denylist_problems(doc, under=under)]
    if not findings:
        return None
    return "%s; %s" % (min(findings, key=lambda f: f[:2])[2], tail)    # min is stable: walk order among equals


def default_path(state: Path, now=None) -> Path:
    now = now or datetime.now(timezone.utc)
    return state / EXPORT_DIR / ("perf-export-%s.json" % now.strftime("%Y%m%dT%H%M"))


def write_file(path: Path, text: str) -> int:
    """Create or replace `path` as a regular file readable by the owner alone; the byte count written, which is
    every byte of `text`: os.write may write fewer than asked (a full disk, a size limit, an interruption), so the
    write loops over what is left and a write that makes no progress is an OSError, never a truncated file
    reported as a success (the export's review, 2026-09-18). A write that fails once the file is open (the loop,
    the mode, the close) removes the file before the error propagates: the open truncated whatever was there, so
    nothing is lost by removing it, and a truncated 0600 file must not be left looking like an export (round 2).
    Not a temporary file moved over the target: a replace would swap out a symlink at --out, which O_NOFOLLOW
    refuses to follow."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(path), flags, 0o600)
    try:
        try:
            os.fchmod(fd, 0o600)
            view = memoryview(data)
            written = 0
            while written < len(data):
                n = os.write(fd, view[written:])
                if n <= 0:
                    raise OSError("short write: %d of %d bytes" % (written, len(data)))
                written += n
        finally:
            os.close(fd)
    except OSError:
        try:
            os.unlink(str(path))
        except OSError:
            pass
        raise
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog=PROG, description=__doc__.split("\n\n")[0],
                                 usage="%(prog)s --public [--from SNAPSHOT.json] [--usage] [--out PATH]")
    ap.add_argument("--public", action="store_true",
                    help="write the public form (required; there is no raw mode): paste-safe, not unlinkable. Identifiers, paths, "
                         "free text, machine strings and every absolute clock stamp go, the uptime is rounded to whole minutes and "
                         "the memory-fraction bounds up to a power of two; durations and per-process measurements (the boot's stage "
                         "split, the lifetime maxima) stay, so two exports from one kernel remain linkable through them")
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
