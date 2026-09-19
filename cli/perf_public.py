#!/usr/bin/env python3
"""perf_public: the public shape of a romp performance document, shared by `romp perf export --public`
(cli/perf_export.py), `romp restart-metrics --json --public` (cli/restart_metrics.py), `romp perf upload`
(cli/perf_upload.py, which holds a file to this shape as the file stands) and the served-snapshot invariant test
(tests/test_perf_stats.py, ServedSnapshotIsPasteSafe). No bin/ entry: it is imported, never run.

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
   restart document's `auditT`, `firstServe`, `reconcileDone` and `restartT`; a duration beside one stays:
   `outageS`, `settleS`, `waitedS`, `uptime_s`; `prevCutT`, the restart ledger's own join key, is on the list
   defensively: parse_restarts reads it to pair a boot with its cut and never serializes it, so the entry removes
   nothing from today's document and guards a future writer only), and the OPAQUE IDS OF CONVERSATION OBJECTS a
   host fault row relays into the restart document's `events.recent` (`requestId`, `callbackId`, `toolUseId`: a
   hook request's, a hook callback's and a tool use's id from the user's conversation, one token each, which the
   grammar would keep verbatim). GET /perf writes `t` on every split row (the boot's first
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
so a failure says what leaked. The denylist walk (denylist_problems) is the third mechanism, and it enforces the fold's own
rule over a document as it stands: it refuses what the fold would have dropped, folded or coarsened, six findings, a
key the denylist drops (a key finding at the dict holding it, its value not walked), a key the fold would have written
as `other` (the block's own grammar through _public_key, so a trailing newline the walk's anchored match admits and a
joined key past the cap count; the value still walked), a string value it would have written as `other`, an uptime
(UPTIME_KEYS) not on whole minutes, a bound (BOUND_KEYS) not on a power of two, and a float inside one of the
STAMP_WINDOWS with no duration key (duration_key) on its path. It runs through perf_export.check_document for that
function's three callers, `romp perf export --public` (cli/perf_export.py, over its own output, where it is a belt),
`romp restart-metrics --json --public` (cli/restart_metrics.py, over its document at the root) and `romp perf upload`
(cli/perf_upload.py, over a file as it stands, which is where an edit made after the export is caught), and not for
the served-snapshot invariant test, which runs paste_problems alone. A fold's own output is the walk's fixed point,
pinned over every fixture and a served export; the one stated exception is the summed-floats case _merge names, two
measurement floats under a merged `other` key landing inside a stamp window. The identifier scan (machine_probes,
identifier_hits) is the last of the three, the backstop: strings only this machine knows (its hostname, user and home directory; the session ids and
working directories the state directory's sdk registry holds; and the strings listed in the machine-local file
~/.config/romp/private-strings.txt, the same list the repository's pre-push hook reads, one string per line with
`#` comments, resolved the way the hook resolves it: ROMP_PRIVATE_STRINGS, else $XDG_CONFIG_HOME, else $HOME/.config,
and absent on a clone that never set one up, which adds nothing) are searched for in every key and string value of
the finished document, case-insensitively, and a hit refuses the write naming the key path and the kind of
string, never the value. A hostname or a login is a WORD and is matched as a run of whole tokens
(a key or value split on everything outside letters and digits): romp's own vocabulary contains common ones as
substrings (a user named mark and `intrMarks`, a machine named work or arch and `cpu_ms_workers`, `archive`),
and a substring match would refuse every export on such a machine for good. An id or a directory is matched
anywhere: hex and slashes spell no word, and a sid prefix glued to letters is still the sid. A listed string is
matched BOTH ways, as a substring or as a run of whole tokens (the union, the upload's third review round,
2026-09-18): the pre-push hook matches each entry as a plain substring, so a listed token glued to letters
(`zzcoinedzzChat`) must be a hit here too, and a dotted entry (`second.coined`) is still found under another join
(`second-coined`), which the hook's substring grep misses; the list is a few entries the maintainer chose, its
shortest included (PROBE_MIN does not apply to the kind), and a false refusal it causes has a stated remedy,
editing the list. Session NAMES are
not probes on purpose: a session named after one of romp's own identifiers (`chat`, `feed`) would refuse every
export for the lifetime of that session, and the names never reach either document as keys or values (the
kernel keys its tables by sid or rank and the denylist drops every name field), so the probe would only ever
produce that false refusal. The private list is different in kind: it is the maintainer's explicit choice of
what must never be published (a coined project nickname among them, which fits the identifier grammar and is
neither the hostname nor the login, so no other probe knows it; the upload verb, 2026-09-18, is the first road
where a document leaves the machine without a human reading it, which is what made the gap consequential), so a
listed word that is also romp vocabulary refuses every export on that machine, naming the kind (`private
string`) and the path, and the remedy is editing the list. A hostname or login that IS one of romp's identifiers
(a user named root and the `POST /walk-root` route) still refuses; that is rare, and the refusal names the kind
of string and the key path.

The three walks and the fold recurse one frame per level and stay recursive (their traversal order decides which of two
equally shallow findings check_document names), which is safe on every road but one because the document is bounded by
construction (the export folds a snapshot the kernel built, restart-metrics reads its own state, the invariant test its
fixtures), and on the one road that reads a file a person names, `romp perf upload`, only because that verb refuses a
document nested deeper than its MAX_DEPTH (32) before any walk runs; a future road that takes untrusted input owes a bound
of its own the same way."""
import collections
import glob
import json
import math
import os
import re
import socket
import stat
import sys

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
# its t) and restartT (the released restart's t verbatim), and the range's since and until (user-typed day bounds
# the buckets already carry as start and end, the one stamp kept). prevCutT is DEFENSIVE, not a field of the
# document: the restart ledger's join key, which parse_restarts reads to pair a boot with its cut and never
# serializes, so the entry removes nothing today and guards a writer that starts carrying it. `port` is
# live.kernel.port: no reader needs it, and a kernel on a non-default ROMP_KERNEL_PORT made it a per-install
# constant. Then the restart document's free-text fields: a session-events row's `text` (problem_row's prose)
# and a cut row's `drainError` and `reasonError` (exception messages). None of the three is ever a counter, and a
# message that happens to be one token of at most 32 characters would pass the grammar verbatim (the export's
# review, 2026-09-18). Then the opaque ids of the user's conversation objects a host fault row relays: the
# session host's hook-self-answered line carries requestId (the hook request's), callbackId (the hook callback's)
# and toolUseId (the tool use's), sdk_backend forwards them through problem_row into the session-events row, and
# events.recent is those rows raw; each is one token the grammar keeps verbatim, and no GET /perf key spells any
# of the three (the fourth review round, 2026-09-18).
DENY_KEYS = frozenset({
    "bySid", "byPath", "readByPath", "stacks", "log",
    "sid", "sids", "sid8", "fsid", "lastSid", "sessionId",
    "kernelSha", "bootId", "started", "generatedAt", "t", "since", "until",
    "auditT", "firstServe", "reconcileDone", "restartT", "prevCutT", "port",
    "text", "drainError", "reasonError",
    "requestId", "callbackId", "toolUseId",
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
    is null. Inside a merged dict a memory-fraction bound (BOUND_KEYS) is coarsened AGAIN after the sum: the two sides
    were each rounded up to a power of two by fold before the merge, and a sum of two powers of two is one only when
    they are equal (1024 + 2048 is 3072), so without this the fold's own output failed its denylist walk at every
    collision of two out-of-grammar sibling keys whose subtrees carry a bound (the upload's second review round,
    2026-09-18); the collision is always at an ANCESTOR key folded to `other` (two bound keys cannot collide in one
    dict, each is its own identifier), so the fold's coarsening at the leaf cannot see it and the merge must. An uptime
    (UPTIME_KEYS) needs no second pass: a sum of whole minutes is whole minutes. NOT closed here: two measurement
    FLOATS summed under a merged key can land inside a stamp window (STAMP_WINDOWS) and read as a clock stamp to the
    denylist walk; no coarsening is involved, so neither this pass nor a key-aware sum fixes it, and whether to exempt a
    value whose key folded to `other` from the stamp rule at the merge sites, or accept the hole, is a separate
    decision."""
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
            if k in BOUND_KEYS and k in a:
                out[k] = public_bound(out[k])     # the sum of two coarsened bounds is not a power of two: coarsen again
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
    `other` (colliding keys merged, a bound inside a merged subtree coarsened again after the sum, see _merge),
    non-finite numbers null, the kernel's uptime rounded down to whole minutes (UPTIME_KEYS), every memory-fraction
    bound rounded up to a power of two (BOUND_KEYS). `where` is the path of ORIGINAL keys, which the denylist and the
    block grammars are keyed on. Returns a new document; the input is not touched. The output is a fixed point of the
    denylist walk (denylist_problems) except for the float case _merge names."""
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


# The STAMP WINDOWS, the fourth finding of denylist_problems (2026-09-18, with the third review round's rules; windows in
# place of a floor since the export's fifth review round, the same day): every absolute clock stamp the two documents carry
# is denied by KEY (DENY_KEYS, DENY_PATHS), and the export's property test (tests/test_perf_export.py, no absolute clock
# stamp survives the export) pins that none survives the fold under any key. Over a FILE the upload verb re-checks, that
# property becomes a belt for a stamp under a key the denylist does not know. A clock stamp is a FLOAT (a time.time() value;
# JSON keeps the distinction, a number written with a point or an exponent loads as one) inside a plausible EPOCH WINDOW:
# 1.5e9 to 2.0e9 for seconds (2017 to 2033), or 1.5e12 to 2.0e12 for milliseconds (the same span; the kernel's clocks are
# seconds, a client's or an editor's could be milliseconds), both ends in. Everything else is a measurement the export keeps
# on purpose, whatever its size, because the kernel's lifetime figures reach and pass these numbers, and a rule over every
# number refused a fresh export from a long-lived kernel by its own belt, and the upload verb with it (the defects each rule
# below replaced, 2026-09-18). An INTEGER: the cumulative byte and count totals are integers, and on a busy kernel the wire
# totals (pusher.clients byKind and byApp `bytes`, hundreds of megabytes to one client within an hour; `parses.bytes`) pass
# 1.5e9 within hours. A float OUTSIDE both windows: the fifth review round ruled, after the served export's property test
# refused a kernel whose glibc allocator figures (process.malloc.arena 2931437568 and uordblks 2731423520) had grown past
# a floor at 1.5e9, that a clock stamp is a number inside a plausible epoch window and a large number outside them is a
# measurement the export keeps on purpose; a large number tells no time unless it lands where a clock reads, so above 2.0e9
# (and above 2.0e12) a float is never a finding here either. A float under a DURATION KEY (duration_key, below), its own or
# ANY key above it on its path: the
# millisecond totals are floats and cumulative too (pusher.cycle_cpu_ms_sum read 1,779,484.0 after one hour on a busy
# kernel, about 35 days to 1.5e9 and twelve more across the seconds window; the other ms sums climb behind it), so a float
# under a key that names a millisecond measure is never judged as a stamp; the key that names it may be the parent's
# (stages_ms is a dict of lifetime sums keyed by STAGE names, push, jobs, push.chat, so its leaves carry no ms token while
# the parent does, and they climb the same way), so every key on the leaf's path is read, and a float inside a window with
# no duration key anywhere on its path is the finding. A memory-fraction bound (BOUND_KEYS) is judged by the power-of-two
# rule alone and never as a stamp (one finding per leaf, the coarsening's; no power of two lies in either window besides,
# and recordCache.budgetBytes floors at 4 GiB on every machine). The fixed point holds over every fixture and a served
# export (ServedKernel). The duration-key exemption is read BY NAME over every ancestor at any depth, so any key carrying
# the token ms exempts every float beneath it, however deep; it is an accident belt for a stamp typed under a new key, not
# an adversarial control, and an editor who wants a stamp through can spell it as an integer or a quoted string under any
# key (the upload's third review round, 2026-09-18: a narrowing to the leaf's key or its parent would not close that road,
# nor the finding's own case, a float directly under an invented ms-named key, which is then the parent; a checked-in
# list of duration parents would bring back the false refusals the ancestor rule exists to avoid; so neither is taken.
# The kernel's own stages_ms is a flat dict of stage names, so its leaves stay exempt under either rule).
STAMP_WINDOWS = ((1.5e9, 2.0e9), (1.5e12, 2.0e12))   # (floor, ceiling) pairs, both ends in: epoch seconds, epoch milliseconds

# A DURATION KEY: a name that, split into tokens on underscores and camelCase boundaries, carries the token `ms` in any case.
# cycle_cpu_ms_sum, ms_sum, ms_max, wallMs, sendMs, restoreMs, held_ms and tierCpuMs are duration keys; sendMax, startedAt,
# bytes and sigMsgs are not (the token must be `ms` whole, so `msgs` is not it), and a float under one of those is judged
# against the windows whatever it measures: a per-write maximum cannot climb to 1.5e9 ms, and the totals that can all carry
# the token. The kernel spells its millisecond keys both ways, so both splits are read; a digit joins its letters, so the
# gc row's `ms2` (gen-2 time) is one token and not a duration under this rule. The rule is applied to the leaf's own key and
# to every dict key above it (a list index is not a key and is skipped), so a leaf named for what it counts under a parent
# named for the measure passes (stages_ms.push), and so does an element of a list under a duration key, which has no key
# of its own; a leaf with no duration key on its path is judged. The receiver applies the same split and token, and its
# sync test reads KEY_TOKEN_BOUNDARY and DURATION_TOKEN by name, so a change to either here is a change there.
KEY_TOKEN_BOUNDARY = re.compile(r"_+|(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")   # wallMs: wall, Ms; HTTPMs: HTTP, Ms
DURATION_TOKEN = "ms"


def key_tokens(key):
    """The tokens of a key name, the key split on KEY_TOKEN_BOUNDARY (a run of underscores, a lowercase letter or digit
    before an uppercase letter, an uppercase run before a capitalized word) with the empty pieces a leading or trailing
    underscore leaves dropped: `cycle_cpu_ms_sum` is cycle, cpu, ms, sum; `tierCpuMs` is tier, Cpu, Ms; `__msgs__` is msgs."""
    return [t for t in KEY_TOKEN_BOUNDARY.split(key) if t]


def duration_key(key):
    """True when `key` is a string one of whose tokens (key_tokens: the one split, so the eight tokenizer pins in
    tests/test_perf_export.py certify the split this rule runs) is DURATION_TOKEN lower-cased: a millisecond measure.
    denylist_problems reads it over a leaf's own key and every key above it on its path, and never judges a float with
    one there against STAMP_WINDOWS. None or a non-string key (a list element's) is never one; the isinstance guard runs
    before the call, since key_tokens takes a string."""
    return isinstance(key, str) and any(t.lower() == DURATION_TOKEN for t in key_tokens(key))


def denylist_problems(doc, under=(), skip=()):
    """Every entry of `doc` the fold would not have written as it stands, one Problem each; empty when the document is a
    fold's own output (the walk's FIXED POINT, pinned over every fixture and a served export), except for the float case
    _merge names: two measurement floats summed under a merged `other` key can land inside a stamp window and are refused
    here. THE RULE it enforces is the
    fold's (the export's third review round, 2026-09-18): the public form is PASTE-SAFE, not unlinkable, so what the fold
    drops, folds or coarsens is refused here and what it keeps (durations, counts, per-process measurements) passes. Six
    findings: a key the denylist drops (denied, wherever a dict key appears, and DENY_PATHS anchored at `under`, the key
    path the snapshot's blocks sit below, as paste_problems takes it), a KEY finding at the dict holding it, its value not
    walked; a KEY the fold would have replaced by `other` (_public_key over the block the key sits in: the identifier
    grammar's fullmatch for a plain block, the joined grammar's fullmatch and its 96-character cap for a joined table, the
    register's own collapse for `http`), a key finding at the dict holding it, its value still walked, which is what closes
    the class of key the walk's anchored `.match` admits and the fold does not (a trailing newline after an otherwise good
    name: `$` matches before it; a joined key past the cap), the upload's second review round, 2026-09-18; a STRING VALUE
    the fold would have replaced by `other` (the identifier grammar's fullmatch, which every string a fold writes passes by
    construction), a VALUE finding at its own path, in a dict or a list (the walk judges a value for a uuid, a hex token, a
    path and whitespace, so a 43-character token with none of them passed it), the same round; an uptime (UPTIME_KEYS)
    whose value is not what public_uptime would have written, a value finding at its own path; a memory-fraction bound
    (BOUND_KEYS) whose value is not what public_bound would have written, a value finding at its own path; and a FLOAT
    leaf inside one of the STAMP_WINDOWS (1.5e9 to 2.0e9, an epoch second; 1.5e12 to 2.0e12, an epoch millisecond; both
    ends in) with no duration key (duration_key) on its path, its own key or any dict key above it (a list index is not a
    key), in a dict or a list, a value finding at its own path (the fold's output carries no absolute clock stamp under any
    key, so one in a file was typed in after the export, whatever key it sits under; a time.time() value is a float, and an
    integer inside a window is a count or a byte total, which the kernel's lifetime totals reach within hours, so an
    integer passes whatever its size; a float outside both windows tells no time and is a measurement the export keeps, the
    allocator's arena on a long-lived kernel among them, so it passes whatever its size; a float under a duration key, a
    name whose tokens carry `ms`, its own or an ancestor's (stages_ms names the measure and its leaves the stages), is a
    millisecond total, which the kernel's sums carry through the seconds window in weeks, so it passes too; a bound is
    judged as a bound alone, never as a stamp). `skip` names top-level keys whose string value is not judged, as
    paste_problems and identifier_hits take it: the export's `schema` line carries a slash by design and check_document
    passes it, so the envelope is not the finding on every export.
    One finding per leaf: a string is judged by the grammar alone, a number by the coarsening the fold applies under its
    key first, else the stamp windows. The string or number itself is not carried in the kind,
    and a caller prints the kind and the path alone. The walk (paste_problems) is a shape rule and passes all six: `t`
    fits the identifier grammar, any number is a number, and its key and value rules are anchored matches and searches for
    named shapes, so a document that a fold produced passes here by
    construction, and one a user edited after the export (a `t` put back on a split row, an uptime typed to the second, a
    bound typed to the byte, a float stamp under a new key, a token or a key the fold would have written as `other`) is
    refused with the same wording the export's own check uses
    (`romp perf upload`, 2026-09-18)."""
    problems = []
    n = len(under)

    def value_problem(kind, v, here):
        problems.append(Problem(kind, False, "/".join(str(x) for x in here), str(v), len(here)))

    def leaf(key, v, here):
        if isinstance(v, str):
            # a string is judged by the grammar alone: the fold writes every string value as itself or as `other`, and
            # both fullmatch IDENT, so one that does not was put there after the fold (the coarsenings and the windows
            # judge numbers and a bound key over a string is a string still)
            if not IDENT.fullmatch(v):
                value_problem("a string the fold would have folded", v, here)
            return
        # one finding per leaf: the coarsening the fold applies under the key first, else the stamp windows
        if key in UPTIME_KEYS:
            rounded = public_uptime(v)
            if not (rounded is v or rounded == v):
                value_problem("an uptime not rounded to whole minutes", v, here)
                return
        elif key in BOUND_KEYS:
            rounded = public_bound(v)
            if not (rounded is v or rounded == v):
                value_problem("a bound not rounded to a power of two", v, here)
            return                          # a bound is judged as a bound alone, never as a stamp
        if isinstance(v, float) and any(lo <= v <= hi for lo, hi in STAMP_WINDOWS) and not any(duration_key(k) for k in here):
            # a float alone, inside one of the epoch windows, and never with a duration key on its path: an integer is a total
            # whatever its size, a float outside both windows is a measurement, and so is a float under a key that names a
            # millisecond measure, its own or any above it (STAMP_WINDOWS's comment); `here` ends in the leaf's own key, or in
            # its index when the leaf is a list element, and an index is never a duration key
            value_problem("a number the size of a clock stamp", v, here)

    def walk(node, where):
        if isinstance(node, dict):
            block = where[n:] if where[:n] == tuple(under) else None     # the dict's path below `under`: which grammar its keys take
            for k, v in node.items():
                key = k if isinstance(k, str) else str(k)
                here = where + (key,)
                anchored = here[n:] if here[:n] == tuple(under) else None
                if denied(key, v) or (anchored is not None and anchored in DENY_PATHS):
                    problems.append(Problem("a key the denylist drops", True, "/".join(str(x) for x in where), key, len(where)))
                    continue
                if _public_key(key, block) != key:
                    # the key the fold would have written is not this one: the walk's `.match` against a `$`-anchored grammar
                    # admits a trailing newline and the joined grammar has no length cap there; the fold's fullmatch and cap
                    # do not, and a key outside the register's image in `http` collapses. The value is walked all the same.
                    problems.append(Problem("a key the fold would have folded", True, "/".join(str(x) for x in where), key, len(where)))
                if where == () and key in skip and isinstance(v, str):
                    continue
                leaf(key, v, here)
                walk(v, here)
        elif isinstance(node, (list, tuple)):
            for i, v in enumerate(node):
                here = where + (i,)
                leaf(None, v, here)
                walk(v, here)

    walk(doc, ())
    return problems


# ── the identifier scan ──────────────────────────────────────────────────────────────────────────────────
PROBE_MIN = 4   # a shorter machine string matches romp's own vocabulary too often to be a probe; not applied to a listed private string (machine_probes)
WORD_KINDS = frozenset({"hostname", "username"})   # probes that are words: matched as runs of whole tokens alone (probe_in)
PRIVATE_KIND = "private string"                    # a listed string: matched as a substring OR a run of whole tokens (probe_in)
TOKEN = re.compile(r"[a-z0-9]+")
# The machine-local list of strings that must never be published: the file the repository's pre-push hook reads
# (.githooks/pre-push, scan_identifiers), one string per line, a `#` starting a comment, surrounding whitespace
# dropped, blanks skipped, resolved as the hook resolves it (private_strings_path). Absent on a clone that never set
# one up, and then it adds nothing. Read with a bound: a list is a few lines, and a file put there by mistake costs
# PRIVATE_STRINGS_MAX and no more. Past the bound the file is cut back to its last complete line and every entry from
# there on is not checked, said once on stderr (LIST_OVER_BOUND): a cut mid-line made a fragment of an entry a probe of
# its own, which falsely refused an unrelated document while the entry it was cut from travelled (the upload's second
# review round, 2026-09-18), so the tail is dropped whole, and dropping it silently would let a listed string go
# unchecked with nothing said. The hook and this re-check read the SAME list and match it DIFFERENTLY, knowingly: the
# hook matches each entry as a case-insensitive plain substring (grep -i -F) over the lines a push adds, its messages,
# the tip trees and the stamped address domains; the re-check matches a substring OR a whole-token run over every key
# and string value of the finished document (probe_in). The re-check was weaker than the hook in a different way in
# each of three findings of one round (a word match that missed a glued entry, the PROBE_MIN floor that dropped a short
# one, a tail cut that made a fragment one); one matcher both call is the honest fix and is not done in this PR.
PRIVATE_STRINGS_VAR = "ROMP_PRIVATE_STRINGS"
PRIVATE_STRINGS_FILE = os.path.join("romp", "private-strings.txt")
PRIVATE_STRINGS_MAX = 64 * 1024
LIST_OVER_BOUND = "romp: the private-strings list is over %d bytes; entries past the bound are not checked" % PRIVATE_STRINGS_MAX
LIST_NOT_IN_FORCE = "romp: %d of %d private-strings entries did not become probes and are not checked; the list is not fully in force"


def open_regular(path):
    """`path` open for reading bytes when it is a REGULAR file, else None; an OSError (absent, unreadable) propagates.
    Opened O_NONBLOCK and fstat'ed before any read: a plain open of a fifo blocks until a writer arrives, before any
    read a bound could cover, and a fifo at the private-strings path hung `romp perf export --public` and `romp
    restart-metrics --json --public`, one at the receiver setting hung `romp perf upload`, all indefinitely (the
    upload's second review round, 2026-09-18). Anything but a regular file (a fifo, a device node, a directory) is
    closed and None, so the caller takes its absent or refused road; the flag stays on the descriptor, which a regular
    file's reads never notice."""
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        regular = stat.S_ISREG(os.fstat(fd).st_mode)
    except OSError:
        os.close(fd)
        raise
    if not regular:
        os.close(fd)
        return None
    return os.fdopen(fd, "rb")


def private_strings_path(env):
    """The private list's path, the way .githooks/pre-push resolves it: ROMP_PRIVATE_STRINGS when set, else
    $XDG_CONFIG_HOME/romp/private-strings.txt when that variable is set, else $HOME/.config/romp/private-strings.txt;
    None when HOME is unset and neither variable names one."""
    explicit = env.get(PRIVATE_STRINGS_VAR)
    if explicit:
        return explicit
    config = env.get("XDG_CONFIG_HOME") or (os.path.join(env["HOME"], ".config") if env.get("HOME") else None)
    return os.path.join(config, PRIVATE_STRINGS_FILE) if config else None


def private_strings(env):
    """[str]: the private list's entries, a `#` comment and surrounding whitespace stripped from each line and blanks
    dropped, read as UTF-8 (a byte that is not is replaced, never a traceback) from a REGULAR file (open_regular) of at
    most PRIVATE_STRINGS_MAX bytes: PRIVATE_STRINGS_MAX + 1 are read, and a file over the bound is cut back to the last
    complete line inside it, so no fragment of an entry becomes a probe, with LIST_OVER_BOUND said once on stderr, since
    the entries from the cut on are not checked; a file exactly at the bound is read whole and nothing is said. [] when
    there is no file to read: absent, unreadable, no path at all, or not a regular file (a fifo, a device node)."""
    path = private_strings_path(env)
    if not path:
        return []
    try:
        fh = open_regular(path)
        if fh is None:
            return []
        with fh:
            raw = fh.read(PRIVATE_STRINGS_MAX + 1)
    except OSError:
        return []
    if len(raw) > PRIVATE_STRINGS_MAX:
        raw = raw[:PRIVATE_STRINGS_MAX]
        raw = raw[:raw.rfind(b"\n") + 1]        # back to the last complete line; empty when the bound cut the first one
        sys.stderr.write(LIST_OVER_BOUND + "\n")
    out = []
    for line in raw.decode("utf-8", "replace").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def machine_probes(state_dir=None, env=None):
    """[(kind, string)]: what only this machine knows. The hostname and its first label, the login name and
    the home directory (with its last component, which is usually the login name), every string on the
    machine-local private list (private_strings, kind PRIVATE_KIND, `private string`: the maintainer's own list of
    what must never be published, absent on a clone that never set one up, matched as a substring or a token run,
    probe_in), and, when `state_dir` holds an sdk registry, every session id (whole and its first eight characters,
    the spelling the scope units and the ledgers use), every conversation id and every working directory.
    Lower-cased; strings shorter than PROBE_MIN are left out, EXCEPT a listed private string: the list is the
    maintainer's explicit choice and not the heuristic the floor exists for, and the floor dropped a three-character
    entry silently while a document carrying it was sent (the upload's second review round, 2026-09-18); an empty
    entry is never a probe (an empty substring is in every string). When a listed entry did not become a probe (the
    reader returns no blank today, so only a filter a later change adds could drop one), LIST_NOT_IN_FORCE says how
    many of how many on stderr: a list silently not in force is the wrong signal. See the module docstring for why
    session names are not probes, and why a listed string that is also romp vocabulary refuses on purpose."""
    env = os.environ if env is None else env
    out = []

    def add(kind, s):
        s = str(s or "").strip().lower()
        if s and (kind == PRIVATE_KIND or len(s) >= PROBE_MIN) and (kind, s) not in out:
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
    listed = private_strings(env)
    for s in listed:
        add(PRIVATE_KIND, s)
    dropped = sum(1 for s in listed if (PRIVATE_KIND, str(s).strip().lower()) not in out)
    if dropped:
        sys.stderr.write(LIST_NOT_IN_FORCE % (dropped, len(listed)) + "\n")
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
    `example`); a listed private string (PRIVATE_KIND) as a substring OR as a token run, the union: the substring is
    what the pre-push hook matches (`zzcoinedzz` is in `zzcoinedzzChat` and in `zzcoinedzzs`), and the token run keeps
    a dotted entry found under another join (`second.coined` is in `second-coined` and `second_coined`, which the
    hook's substring grep misses); any other probe (an id, a directory) as a substring."""
    low = s.lower()
    if kind not in WORD_KINDS and kind != PRIVATE_KIND:
        return probe in low
    if kind == PRIVATE_KIND and probe in low:
        return True
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
