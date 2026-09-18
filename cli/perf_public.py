#!/usr/bin/env python3
"""perf_public: the public shape of a romp performance document, shared by `romp perf export --public`
(cli/perf_export.py), `romp restart-metrics --json --public` (cli/restart_metrics.py) and the served-snapshot
invariant test (tests/test_perf_stats.py, ServedSnapshotIsPasteSafe). No bin/ entry: it is imported, never run.

A GET /perf snapshot and a restart-metrics document are diagnosis a user may want to paste in public (an issue,
a chat). What must not travel with them is anything that names the machine or its sessions (a home path, a
session id, a hostname, a username, a pid, a glossary term, a client's own text) or fixes them in time (an
absolute clock stamp). THE RULE (the export's third review round, 2026-09-18): the public form is PASTE-SAFE,
not unlinkable. It removes identifiers, paths, free text, machine strings and every ABSOLUTE CLOCK STAMP;
durations stay; per-process and per-machine MEASUREMENTS stay by design (the boot's stage split under
pusher.firstCycle and jobs.firstPass, whole; the lifetime maxima; every counter), because they are the data a
reader wants, so two exports from one kernel life, or from one machine, REMAIN LINKABLE through them. Two rules
make a copy safe by construction and two kinds of value are kept coarsened, so a block added to the kernel later
costs nothing here:

1. The SHAPE rule, over the whole document. Numbers, booleans and null pass. Every dict key and every string
   value must fullmatch the browser's `ident` grammar, `^[A-Za-z0-9_.:-]{1,32}$` (ui/webview/perf-telemetry.ts),
   or it folds to the literal `other`: a key folded to `other` merges with any sibling already there (numbers
   summed, dicts merged, lists joined), a value folded to `other` is the word. Two blocks join fixed
   identifiers with characters outside that grammar and are judged by their own grammars instead: `http`,
   whose keys are `METHOD /path` over the kernel's checked-in route register (HTTP_ROUTES, a copy of the
   kernel's _PERF_HTTP_ROUTES that tests/test_perf_export.py, RouteRegisterCopy, holds equal to it; a key
   outside the register folds to `other`), and the JOINED_KEY_BLOCKS, the byte tables whose keys are
   `kind<-caller` and `stage:kind<-caller` (a stage mark, a reader kind and a function name, never text).
2. The DENYLIST, dropped before the shape rule can turn them into `other` rows: the read table by path
   (`checkpoints.readByPath`, absolute transcript paths), the judges' child's first failure (an exception
   message), the thread stacks, a process id under any spelling (PID_KEY), every ABSOLUTE CLOCK STAMP under any
   spelling the two documents use (`now`, `since`, `until`, `started`, `generatedAt`, `t` at any depth, and the
   restart document's `auditT`, `firstServe`, `reconcileDone`, `restartT` and `prevCutT`; a duration beside one
   stays: `outageS`, `settleS`, `waitedS`, `uptime_s`). GET /perf writes `t` on every split row (the boot's first
   cycle under `pusher.firstCycle`, the first pass under `jobs.firstPass`, each `stageRing` row) as the wall
   clock at the cycle's CLOSE, so the first cycle's is the kernel's start plus that cycle's length (under a
   second on a quick boot, up to the ten seconds the kernel flags as slow), constant for the life of the process,
   and on the judge child's report; no `t` in the snapshot is a counter. The restart document carried the same
   stamps under other names while `t` alone was denied: a quiet window's `restartT` is the released restart's `t`
   verbatim, and `firstServe` minus the kept `outageS` is the cut's. Its `buckets[].start` and `end` are the one
   absolute stamp KEPT: day or week boundaries in the chosen zone, coarse, the window a bucket's counts cover
   (they do reveal the zone's UTC offset). `live.kernel.port` goes too: no reader needs it, and a kernel on a
   non-default ROMP_KERNEL_PORT made it a per-install constant. Then a sid in any spelling, the restart
   document's free-text fields (an event row's `text`, the prose of a session problem; a cut row's `drainError`
   and `reasonError`, exception messages), which a one-token message would otherwise carry through the grammar
   verbatim, and every key that names an identity or a place (a session or unit name, a scope, a label, a path,
   a working directory, a host, a user, a command line) where its value can carry text. The same key over a
   plain number is a COUNTER and stays: the chat build's per-label miss counts (`builds.chat.bg_miss.names`,
   `.host`, `.cwd`) and the sessions listing's miss reasons (`memos.sessionsListing.missBy.names`) are integers
   under identity-shaped keys. DENY_PATHS are anchored at the document's root; DENY_KEYS, PID_KEY and
   IDENTITY_KEYS apply wherever a dict key appears (`denied` is the one test).
3. The UPTIME ROUNDING: `uptime_s` (and the restart document's `uptimeS`) is not denied, since it is the span the
   lifetime totals cover, which a reader needs, but it is rounded DOWN to whole minutes (UPTIME_KEYS,
   public_uptime) before the envelope is written: to the second, beside the export's UTC minute (a stamp with no
   seconds), it placed the kernel's start within a minute, the same start the denied `t` carries and as constant
   for the life of the process (the receiving side's review, 2026-09-18).
4. The BOUND COARSENING: the memory-fraction bounds (BOUND_KEYS: `capBytes`, `budgetBytes`, `cap`, `bound`,
   `stageRingMax`, wherever the key appears) are kept and rounded UP to a power of two (public_bound), the key
   kept and the occupancy beside it untouched, so a bound that binds stays visible next to its `bytes` or
   `entries`. Each is a fixed fraction of the machine's MemTotal (`recordCache.budgetBytes` is half of it,
   `heap.hydrated.capBytes` a thirty-second, `checkpoints.docMemo.capBytes` and `asmCheckpoint.asmDocMemo.capBytes`
   a five-hundred-twelfth, `asmIndex.cap` the memory over 32 KiB, `pusher.stageRingMax` one per 256 MiB,
   `builds.feed.memo.bound` and `memos.spendTree.bound` a sixty-fourth, `memos.notices.bound` and
   `memos.summaryAnchor.bound` a two-hundred-fifty-sixth; the judge child's copies of its tables carry the same
   keys), so every export from one machine shared all ten exactly and one of them gave the machine's RAM to the
   kilobyte: a value derived from a machine fact is a machine string in a number's clothing (the third review
   round, 2026-09-18). A constant that happens to sit under one of the keys is coarsened too, at no cost.

The walk (paste_problems) is the invariant test's: every key against its block's grammar (`ident` for a plain
block; membership in the register's image for `http`, http_key_ok; the stack sample's `<ident> <kind>` for
`stacks`, a block the export drops and the served snapshot carries under its switch; JOINED_KEY for the joined
tables), every key and string against a uuid, a 32-hex token, a 40-hex token (a checkpoint document's name),
an absolute path and any planted text, and every string value against free text (whitespace: an exception
message, a URL, a bare host name), except a stack frame, "function (file:line)", which has its own grammar. It
reports each finding as a Problem (the kind of finding, whether a key or a value, the key path, the offending
string), formatted by the caller: the export runs it over its own output as a self-check and refuses to write
on a problem naming the kind and the path alone, while the invariant tests print the whole line (str(problem))
so a failure says what leaked. The identifier scan (machine_probes, identifier_hits) is the last backstop: strings only this machine knows (its hostname, user and home directory; the session ids and
working directories the state directory's sdk registry holds) are searched for in every key and string value of
the finished document, case-insensitively, and a hit refuses the write naming the key path and the kind of
string, never the value. A hostname or a login is a WORD and is matched as a run of whole tokens (a key or
value split on everything outside letters and digits): romp's own vocabulary contains common ones as
substrings (a user named mark and `intrMarks`, a machine named work or arch and `cpu_ms_workers`, `archive`),
and a substring match would refuse every export on such a machine for good. An id or a directory is matched
anywhere: hex and slashes spell no word, and a sid prefix glued to letters is still the sid. Session NAMES are
not probes on purpose: a session named after one of romp's own identifiers (`chat`, `feed`) would refuse every
export for the lifetime of that session, and the names never reach either document as keys or values (the
kernel keys its tables by sid or rank and the denylist drops every name field), so the probe would only ever
produce that false refusal. A hostname or login that IS one of romp's identifiers (a user named root and the
`POST /walk-root` route) still refuses; that is rare, and the refusal names the kind of string and the key
path."""
import collections
import glob
import json
import math
import os
import re
import socket

OTHER = "other"

# The browser's `ident` grammar (ui/webview/perf-telemetry.ts): letters, digits, `_ . : -`, at most 32 chars.
IDENT = re.compile(r"^[A-Za-z0-9_.:-]{1,32}$")

# ── the http block: METHOD /path over the kernel's own route register ────────────────────────────────────
# A checked-in COPY of kernel/kernel.py's _PERF_HTTP_ROUTES and _PERF_HTTP_FAMILIES (tests/test_perf_export.py,
# RouteRegisterCopy, holds the two equal, so a route added there without a line here fails that test). Copied
# rather than imported: loading the kernel module from a terminal tool runs its import-time state binding
# against the live state directory, which the cli/ readers never do.
HTTP_ROUTES = {
    "GET": (
        "/", "/analytics", "/api-health", "/api-health/frame", "/busy", "/chat", "/classify",
        "/commands", "/defaults", "/diag/sendvis", "/emoji", "/feed", "/feed.json", "/file", "/files",
        "/fleet", "/followup-preview", "/handoff", "/healthz", "/logins", "/manifest.webmanifest",
        "/mcp", "/models", "/notify-all", "/notify-turns", "/palette", "/perf", "/push/pending",
        "/push/vapid-key", "/session-events", "/sessions", "/sessions/by-fsid", "/settings",
        "/spend/detail", "/ssh-hosts", "/sw.js", "/timeline", "/tunnels", "/tunnels/of",
        "/tunnels/pairs", "/update-check", "/usage", "/usage/fleet", "/version", "/views", "/waiting",
        "/watches", "/ws",
    ),
    "HEAD": (
        "/file",
    ),
    "POST": (
        "/checkin", "/checkin/stop", "/color", "/compact", "/deliver", "/down", "/emoji", "/end",
        "/flag", "/fleet-restart", "/fork", "/fork-comment", "/fork-promote", "/group", "/interrupt",
        "/judge-settings", "/logins", "/mesh-settings", "/move", "/new", "/notice", "/notify-all",
        "/notify-turns", "/order", "/perf", "/pinnote", "/postal-notice", "/push/ack", "/push/dropped",
        "/push/landed", "/push/relay", "/push/subscribe", "/push/superseded", "/push/test",
        "/push/unsubscribe", "/redial", "/rename", "/restart", "/reveal", "/send", "/tag", "/tick",
        "/tunnels", "/tunnels/askpull", "/tunnels/autoupdate", "/tunnels/checkin", "/tunnels/detach",
        "/tunnels/forget", "/tunnels/pull", "/tunnels/start", "/tunnels/trust", "/tunnels/trust-mirror",
        "/tunnels/trust-remote", "/tunnels/update", "/unpinnote", "/update", "/update-dismiss",
        "/usertodo", "/usertodo/context", "/usertodo/withdraw", "/views", "/walk-root", "/watch",
        "/watch-pr", "/working",
    ),
}
HTTP_ROUTES["OPTIONS"] = tuple(sorted(set(HTTP_ROUTES["GET"]) | set(HTTP_ROUTES["HEAD"]) | set(HTTP_ROUTES["POST"])))
HTTP_FAMILIES = ("/dist/*", "/media/*", "/glossary/*", "/remote/*")
_ROUTE_SETS = {m: frozenset(v) for m, v in HTTP_ROUTES.items()}


def http_key_ok(key):
    """Is `key` a "METHOD /path" the kernel's register can produce: a fixed route of that method, a collapsed
    family, or a remote route (`/remote/*` alone or `/remote/*/<route of the same method>`), or `other`. This is
    the image of the kernel's _perf_http_key over the register (tests/test_perf_stats.py enumerates it from the
    kernel's own copy, 457 keys on the register of 2026-09-18, and holds every member to this test), and the
    check the invariant walk applies to the http block: a character grammar stood there first and admitted any
    path-shaped key (the served-leak review, 2026-09-18)."""
    if key == OTHER:
        return True
    if not isinstance(key, str) or " " not in key:
        return False
    method, _, path = key.partition(" ")
    routes = _ROUTE_SETS.get(method)
    if routes is None:
        return False
    if path in routes or path in HTTP_FAMILIES:
        return True
    return path.startswith("/remote/*/") and path[len("/remote/*"):] in routes


def http_public_key(key):
    """The public form of one http key: the kernel's own collapse of the high-cardinality families (a bundle name
    under /dist/ or /media/, a glossary TERM, an attached HOST under /remote/), the way _perf_http_key spells them,
    then the register; anything else is `other`. A kernel from before the served-leak fixes counted the raw paths,
    so a saved snapshot of its /perf carries them; a current kernel's keys pass through unchanged."""
    if not isinstance(key, str) or key == OTHER:
        return OTHER
    method, sep, path = key.partition(" ")
    if not sep or not path.startswith("/"):
        return OTHER
    if path.startswith("/dist/"):
        path = "/dist/*"
    elif path.startswith("/media/"):
        path = "/media/*"
    elif path.startswith("/glossary/"):
        path = "/glossary/*"
    elif path.startswith("/remote/") and not path.startswith("/remote/*"):
        rest = path[len("/remote/"):]
        i = rest.find("/")
        path = "/remote/*" + (rest[i:] if i >= 0 else "")
    key = method + " " + path
    return key if http_key_ok(key) else OTHER


# ── the joined-identifier tables ─────────────────────────────────────────────────────────────────────────
# A fixed name, a stage mark, a reason code, or a code object's name as the interpreter spells it (<lambda>,
# <genexpr>): a caller read through a lambda.
NAME = r"(?:[A-Za-z0-9_.?-]+|<[a-z]+>)"
JOINED_KEY = re.compile(r"^%s(?::%s)?(?:<-%s)?$" % (NAME, NAME, NAME))
# The blocks whose keys join identifiers: the record cache's whole reads as kind<-caller and stage:kind<-caller,
# the assembly checkpoints' hydrations as caller and stage:caller, its parse counters as phase:reason, its
# removals as fallback:reason, the lazy index's materializations as caller and stage:caller; the judge child's
# copies of the first two tables under judge.child.
JOINED = frozenset({("recordCache", "wholeReads"), ("recordCache", "wholeReadsByStage"),
                    ("asmCheckpoint", "hydratedBy"), ("asmCheckpoint", "hydratedByStage"),
                    ("asmCheckpoint", "parse"), ("asmCheckpoint", "removed"),
                    ("asmIndex", "materializedBy"), ("asmIndex", "materializedByStage")})
JOINED_KEY_BLOCKS = JOINED | frozenset(("judge", "child") + b for b in JOINED if b[0] in ("recordCache", "asmCheckpoint"))

# ── the denylist ─────────────────────────────────────────────────────────────────────────────────────────
# Anchored at the root: the read table by path, the child's first failure (an exception message; the count
# beside it stays) and /perf's `now` (uptime_s, a duration, stays: rounded, see UPTIME_KEYS). The child's report
# stamp, once listed here by path, is denied by its key (`t`, DENY_KEYS) since 2026-09-18, and `since` moved to
# DENY_KEYS in the third review round: a quiet window's parked stamp sits at depth under that name.
DENY_PATHS = frozenset({("checkpoints", "readByPath"), ("judge", "child", "failures", "first"), ("now",)})
# Dropped wherever they appear as a dict key, whatever the value: by-identity tables, thread stacks and the perf
# log switch, session ids in every spelling this repository uses, every ABSOLUTE CLOCK STAMP under the spellings
# the two documents use (the rule of the third review round, 2026-09-18: a stamp fixes a process or an event in
# time and is the same value in every document from that machine, so all of them go and durations stay). `t`:
# GET /perf writes it on every split row (the boot's first cycle under pusher.firstCycle, the first pass under
# jobs.firstPass and each stageRing row) as the wall clock at the cycle's close, the first cycle's the kernel's
# start plus that cycle's length and constant for the life of the process, and on the judge child's report; no
# `t` in the snapshot is a counter, checked against the kernel's snapshot builders. The restart document's `t` is
# the second of each restart, boot, quiet window, kernel-series point and event, and the same stamps ride its rows
# under other names: auditT (the audit row a cut consumed), firstServe and reconcileDone (the boot's marks;
# firstServe minus the kept outageS is the denied cut's t), a quiet window's since (parked; since plus waitedS is
# its t) and restartT (the released restart's t verbatim), prevCutT (the ledger's own join key), and the range's
# since and until (user-typed day bounds the buckets already carry as start and end, the one stamp kept). `port`
# is live.kernel.port: no reader needs it, and a kernel on a non-default ROMP_KERNEL_PORT made it a per-install
# constant. Then the restart document's free-text fields: a session-events row's `text` (problem_row's prose)
# and a cut row's `drainError` and `reasonError` (exception messages). None of the three is ever a counter, and a
# message that happens to be one token of at most 32 characters would pass the grammar verbatim (the export's
# review, 2026-09-18).
DENY_KEYS = frozenset({
    "bySid", "byPath", "readByPath", "stacks", "log",
    "sid", "sids", "sid8", "fsid", "lastSid", "sessionId",
    "kernelSha", "bootId", "started", "generatedAt", "t", "since", "until",
    "auditT", "firstServe", "reconcileDone", "restartT", "prevCutT", "port",
    "text", "drainError", "reasonError",
})
# A process id under any spelling the ledgers write (pid, ppid, pids, cliPid, hostPid, managerPid, hub_pid,
# boundary_pids) and the next one: `pid`, `ppid` or `pids` in any case as the whole key or after `_`, or `Pid`/`Pids`
# after a letter or digit. `rapid` and `cupid` are words, not pids (the camel-case form is case-sensitive for that).
PID_KEY = re.compile(r"(?:^|_)(?i:p?pids?)$|[A-Za-z0-9]Pids?$")
# Dropped where the value can carry text (a string, a list, a dict): a key naming an identity or a place. Over a
# number, a bool or null the same key is a counter or a flag and stays (see the module docstring).
IDENTITY_KEYS = frozenset({
    "name", "names", "cutSessions", "label", "scope", "unit",
    "path", "paths", "cwd", "home", "dir",
    "host", "hosts", "hostname", "user", "username", "login",
    "cmd", "command", "argv",
})


def denied(key, value):
    """Is the dict entry `key: value` dropped by the denylist, wherever it sits: an always-denied key, a pid under any
    spelling, or an identity key whose value can carry text."""
    if key in DENY_KEYS or PID_KEY.search(key):
        return True
    return key in IDENTITY_KEYS and not (value is None or isinstance(value, (bool, int, float)))


# The kernel's uptime, kept and COARSENED: GET /perf's `uptime_s` and the restart document's `uptimeS` (GET /version's,
# under live.kernel). It is the span the lifetime totals cover, which a reader needs; to the second, beside the export
# minute (a stamp with no seconds) or the paste time, it placed the kernel's start within a minute, the same start as
# the denied `t` carries and as constant for the life of the process, so it is rounded DOWN to whole minutes before the
# envelope is written (the receiving side's review, 2026-09-18). The export's usage block buckets the RAW value; its
# bounds are whole minutes, so the bucket agrees with the rounded one (tests/test_perf_export.py, UptimeRounding, pins
# both).
UPTIME_KEYS = frozenset({"uptime_s", "uptimeS"})
UPTIME_GRAIN_S = 60


def public_uptime(value):
    """`value` rounded down to a whole number of minutes, as an int (3725 -> 3720; 100.5 -> 60; 59.9 -> 0), the
    reason in UPTIME_KEYS's comment; anything that is not a finite number (a bool, null, a string, a NaN the fold
    has nulled) is returned as it is."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return value
    return int(math.floor(value / UPTIME_GRAIN_S)) * UPTIME_GRAIN_S


# The memory-fraction BOUNDS, kept and COARSENED (the third review round, 2026-09-18): each of the ten GET /perf serves
# (heap.hydrated.capBytes, checkpoints.docMemo.capBytes, asmCheckpoint.asmDocMemo.capBytes, asmIndex.cap,
# recordCache.budgetBytes, pusher.stageRingMax, builds.feed.memo.bound, memos.notices.bound, memos.spendTree.bound,
# memos.summaryAnchor.bound; the judge child's copies of its tables carry the same keys) is a fixed fraction of the
# machine's MemTotal, so every export from one machine shared all ten exactly and recordCache.budgetBytes, half of
# MemTotal, gave the machine's RAM to the kilobyte: a value derived from a machine fact. Rounded UP to a power of two
# (public_bound), the key kept and the occupancy beside it untouched, so a bound that binds stays visible next to its
# bytes or entries. Keyed on the name at any depth, like UPTIME_KEYS; a constant under one of the keys
# (memos.judgingBand.bound, 20000 entries) is coarsened too, at no cost.
BOUND_KEYS = frozenset({"capBytes", "budgetBytes", "cap", "bound", "stageRingMax"})


def public_bound(value):
    """`value` rounded UP to a power of two, as an int (3 -> 4; 4 -> 4; 2.5 -> 4; 501 -> 512), the machine-fact reason
    in BOUND_KEYS's comment; a bound that already is a power of two (a floor on a small machine) reads the same, which
    a reader cannot tell from a rounded one. Anything that is not a finite positive number (a bool, null, a string,
    zero, a NaN the fold has nulled) is returned as it is."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        return value
    return 1 << (math.ceil(value) - 1).bit_length()


def _finite(x):
    return x if (isinstance(x, (int, bool)) or math.isfinite(x)) else None


def _merge(a, b):
    """Two values whose keys folded to the same name: numbers add, dicts merge, lists join; anything else that
    disagrees is `other`. None is the identity: a non-finite number is nulled by _finite before it gets here, and
    a counter beside it must stay a number (and a bool a bool), not become the word `other`; a null beside a null
    is null."""
    if a is None or b is None:
        return b if a is None else a
    if isinstance(a, bool) or isinstance(b, bool):
        return a if a == b else OTHER
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + b
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = _merge(out[k], v) if k in out else v
        return out
    if isinstance(a, list) and isinstance(b, list):
        return a + b
    return a if a == b else OTHER


def _public_key(key, where):
    """The key as the public form spells it: the http block through the register (families collapsed), the joined
    tables through their grammar, everything else through the ident grammar; `other` when it fails."""
    if where == ("http",):
        return http_public_key(key)
    if where in JOINED_KEY_BLOCKS:
        return key if (JOINED_KEY.fullmatch(key) and len(key) <= 96) else OTHER
    return key if IDENT.fullmatch(key) else OTHER


def fold(node, where=()):
    """The public form of `node`: the denylist dropped, every key and string outside its grammar folded to
    `other` (colliding keys merged), non-finite numbers null, the kernel's uptime rounded down to whole minutes
    (UPTIME_KEYS), every memory-fraction bound rounded up to a power of two (BOUND_KEYS). `where` is the path of
    ORIGINAL keys, which the denylist and the block grammars are keyed on. Returns a new document; the input is not
    touched."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            k = k if isinstance(k, str) else str(k)
            here = where + (k,)
            if denied(k, v) or here in DENY_PATHS:
                continue
            nk = _public_key(k, where)
            fv = fold(v, here)
            if k in UPTIME_KEYS:
                fv = public_uptime(fv)          # kept coarsened: whole minutes (UPTIME_KEYS)
            elif k in BOUND_KEYS:
                fv = public_bound(fv)           # kept coarsened: the next power of two (BOUND_KEYS)
            out[nk] = _merge(out[nk], fv) if nk in out else fv
        return out
    if isinstance(node, (list, tuple)):
        return [fold(v, where + (i,)) for i, v in enumerate(node)]
    if isinstance(node, str):
        return node if IDENT.fullmatch(node) else OTHER
    if isinstance(node, bool) or node is None:
        return node
    if isinstance(node, (int, float)):
        return _finite(node)
    return OTHER


# ── the invariant walk ───────────────────────────────────────────────────────────────────────────────────
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
HEX32 = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{32}(?![0-9a-fA-F])")
HEX40 = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{40}(?![0-9a-fA-F])")   # a sha1: a checkpoint document's name, a commit
ABS_PATH = re.compile(r"(?:^|[\s\"'=(:,])/(?:[^/\s]+/)+[^/\s]*")   # a slash-rooted path of two or more segments
WHITESPACE = re.compile(r"\s")                                       # free text: an exception message, a URL, a bare host name
# The stack sample (GET /perf?stacks=1, ROMP_PERF_STACKS; the kernel's _thread_stacks): a row per thread keyed
# "<ident> <kind>", the kind a word from the kernel's register of its own thread kinds (_THREAD_KIND_WORDS, a
# judge pool's worker composing judge-<word>) or `other`, never a name. The export drops the block (DENY_KEYS)
# and so needs no copy of that register; this module's grammar is the character grammar, one kind token or `?`
# (what a kernel before the register spelled for a thread gone between its two enumerations), which admits a
# served snapshot from any tree, and the served walk (tests/test_perf_stats.py, ServedSnapshotIsPasteSafe) passes
# the register's own grammar through paste_problems's stacks_key.
STACKS_KEY = re.compile(r"^[0-9]+ (?:[A-Za-z0-9_.-]+|\?)$")
# A frame string, "function (file:line)": a code object's name and its file's BASENAME, the interpreter's <lambda>
# and <frozen ...> forms included; never a directory.
FRAME = re.compile(r"^(?:[A-Za-z0-9_]+|<[a-z]+>) \(<?[A-Za-z0-9_. -]+>?:[0-9]+\)$")


def _frame_value(block):
    """Is a value at `block` (a key path below `under`) one of the stack sample's frame strings: stacks/<row>/frames/<i>."""
    return block is not None and len(block) > 2 and block[0] == "stacks" and block[2] == "frames"


class Problem(collections.namedtuple("Problem", "kind is_key path text depth")):
    """One finding of the walk: `kind` is the rule that failed (a fixed phrase from the list in paste_problems),
    `is_key` whether the string is a dict key (True) or a string value, `path` the key path as `a/b/0/c` (a key's
    is the path of the dict holding it; the root is the empty string), `text` the offending string itself, `depth`
    the number of components in `path` (a key's is its dict's; the root is 0), counted at the finding because a key
    may itself contain the separator (an http route key, `GET /perf`), so it cannot be recovered from the string.
    Callers format it (place): the export's refusal prints the kind and the path and never `text` (the leak a
    refusal exists to prevent must not travel in the refusal); the invariant tests print str(problem), the whole
    line."""
    __slots__ = ()

    def __str__(self):
        return "%s: %s %r at %s" % (self.kind, "key" if self.is_key else "value", self.text, self.path)


class Hit(collections.namedtuple("Hit", "kind is_key path depth")):
    """One finding of the identifier scan (identifier_hits), shaped like Problem: `kind` the probe's kind (hostname,
    username, home directory, session id, session directory), `is_key`, `path` and `depth` as Problem's. The string
    that matched is not carried: a key IS the string, and the scan's callers print the finding in a refusal."""
    __slots__ = ()


def place(finding):
    """Where a Hit or a Problem sits, as a refusal spells it: "a key under <path of the dict>" or "the value at <path>",
    the root spelled `the root`; never the string itself."""
    return ("a key under %s" if finding.is_key else "the value at %s") % (finding.path or "the root")


def paste_problems(doc, planted=(), ident=IDENT, skip=(), under=(), stacks_key=STACKS_KEY):
    """Every way `doc` fails to be paste-safe, one Problem each (empty when it is): a key outside its block's
    grammar (`ident` for plain blocks, the register's image for `http` (http_key_ok), `stacks_key` for `stacks`
    (STACKS_KEY, the character grammar, unless the caller holds the kernel's register of thread kinds and passes
    its grammar, as the served-snapshot test does), JOINED_KEY for the joined tables), a key or string value
    carrying a uuid, a 32-hex or 40-hex token, an
    absolute path or any of the `planted` strings, a string value carrying whitespace (free text) anywhere but
    the stack sample's frames, and a frame outside FRAME. `skip` names top-level keys whose string value is not
    walked (an export's schema line); `under` is the key path the snapshot's blocks sit below (`("perf",)` in an
    export; the root in a served snapshot). A Problem is structured, not a line, so a caller that must not print
    the offending string (the export's refusal) cannot: a key or value that itself contains " at " used to hand a
    fragment of the flagged material to a caller splitting the line (the export's review, 2026-09-18)."""
    problems = []
    n = len(under)

    def block(where):
        return where[n:] if where[:n] == tuple(under) else None

    def found(kind, s, where, key):
        problems.append(Problem(kind, key, "/".join(str(p) for p in where), s, len(where)))

    def text(s, where, key):
        for probe in planted:
            if probe and probe in s:
                found("planted text survives", s, where, key)
                break
        if UUID.search(s):
            found("a uuid-shaped token", s, where, key)
        if HEX32.search(s):
            found("a 32-hex token", s, where, key)
        if HEX40.search(s):
            found("a 40-hex token", s, where, key)
        if not (key and block(where) == ("http",)) and ABS_PATH.search(s):   # a route key is a path by design;
            found("an absolute path", s, where, key)                          #  its membership is checked below
        if not key:
            if _frame_value(block(where)):
                if not FRAME.match(s):
                    found("outside the frame grammar", s, where, key)
            elif WHITESPACE.search(s):
                found("free text", s, where, key)

    def check_key(k, where):
        if not isinstance(k, str):
            found("a non-string key", str(k), where, True)
            return
        text(k, where, True)
        if block(where) == ("http",):
            if not http_key_ok(k):
                found("outside the image of the route register", k, where, True)
        elif block(where) == ("stacks",):
            if not stacks_key.match(k):
                found("outside the stack sample's key grammar", k, where, True)
        elif block(where) in JOINED_KEY_BLOCKS:
            if not JOINED_KEY.match(k):
                found("outside the joined-identifier grammar", k, where, True)
        elif not ident.match(k):
            found("outside the identifier grammar", k, where, True)

    def walk(node, where):
        if isinstance(node, dict):
            for k, v in node.items():
                check_key(k, where)
                if where == () and k in skip and isinstance(v, str):
                    continue
                walk(v, where + (k,))
        elif isinstance(node, (list, tuple)):
            for i, v in enumerate(node):
                walk(v, where + (i,))
        elif isinstance(node, str):
            text(node, where, False)

    walk(doc, ())
    return problems


# ── the identifier scan ──────────────────────────────────────────────────────────────────────────────────
PROBE_MIN = 4   # a shorter machine string matches romp's own vocabulary too often to be a probe
WORD_KINDS = frozenset({"hostname", "username"})   # probes that are words: matched as runs of whole tokens
TOKEN = re.compile(r"[a-z0-9]+")


def machine_probes(state_dir=None, env=None):
    """[(kind, string)]: what only this machine knows. The hostname and its first label, the login name and
    the home directory (with its last component, which is usually the login name), and, when `state_dir` holds
    an sdk registry, every session id (whole and its first eight characters, the spelling the scope units and
    the ledgers use), every conversation id and every working directory. Lower-cased; strings shorter than
    PROBE_MIN are left out (see the module docstring for why session names are not probes)."""
    env = os.environ if env is None else env
    out = []

    def add(kind, s):
        s = str(s or "").strip().lower()
        if len(s) >= PROBE_MIN and (kind, s) not in out:
            out.append((kind, s))
    try:
        host = socket.gethostname()
    except OSError:
        host = ""
    add("hostname", host)
    add("hostname", host.split(".", 1)[0])
    for var in ("USER", "LOGNAME"):
        add("username", env.get(var))
    home = env.get("HOME") or ""
    add("home directory", home)
    add("username", os.path.basename(home.rstrip("/")))
    if state_dir:
        for p in sorted(glob.glob(os.path.join(str(state_dir), "sdk", "*.json"))):
            try:
                with open(p, encoding="utf-8") as fh:
                    d = json.load(fh)
            except Exception:
                continue
            if not isinstance(d, dict):
                continue
            stem = os.path.splitext(os.path.basename(p))[0]
            for sid in (d.get("sid"), d.get("lastSid"), stem):
                if isinstance(sid, str) and len(sid) >= 8:
                    add("session id", sid)
                    add("session id", sid[:8])
            add("session directory", d.get("cwd"))
    return out


def probe_in(kind, probe, s):
    """Does the lower-cased `s` carry `probe`: a word probe (WORD_KINDS: a hostname, a login) as a contiguous run of
    whole tokens, split on everything outside letters and digits (`mark` is not in `intrMarks`, `tester` is in
    `tester-app` and `app_Tester`, `testhost.example` is in `chat.testhost.example` and not in `testhost` beside
    `example`); any other probe (an id, a directory) as a substring."""
    low = s.lower()
    if kind not in WORD_KINDS:
        return probe in low
    run, tokens = TOKEN.findall(probe), TOKEN.findall(low)
    n = len(run)
    return n > 0 and any(tokens[i:i + n] == run for i in range(len(tokens) - n + 1))


def identifier_hits(doc, probes, skip=()):
    """[Hit] for every key or string value of `doc` that carries a probe (probe_in), case-insensitively, one per
    string (the first probe that matches), in walk order. A Hit is structured like the walk's Problem (the kind,
    key or value, the key path, its depth) and the caller formats it (place), so the string itself is never in the
    report (a key IS the string, so its own path is not named, and its dict's is). `skip` names top-level keys
    whose string value is not searched."""
    hits = []

    def scan(s, where, key):
        for kind, probe in probes:
            if probe_in(kind, probe, s):
                hits.append(Hit(kind, key, "/".join(str(p) for p in where), len(where)))
                return

    def walk(node, where):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(k, str):
                    scan(k, where, True)
                if where == () and k in skip and isinstance(v, str):
                    continue
                walk(v, where + (k,))
        elif isinstance(node, (list, tuple)):
            for i, v in enumerate(node):
                walk(v, where + (i,))
        elif isinstance(node, str):
            scan(node, where, False)

    walk(doc, ())
    return hits
