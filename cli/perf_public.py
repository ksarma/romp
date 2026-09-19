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

1. The SHAPE rule, over the whole document. Numbers, booleans and null pass; a number no double can hold (a NaN, an
   infinity, and since 2026-09-19 an integer at or past 2**1024 - 2**970, 309 digits, which every double reader, a
   browser's JSON.parse or the receiver, would make an infinity of) is written null, finite_number, and so is the result
   of a coarsening or a merged sum that passes the edge from inputs within it (held_number: a bound rounded up to
   2**1024, two measurements summed past the largest double). Every dict key and every string
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
and plainly absent on a clone that never set one up, which adds nothing, in silence; every other road to no list, a path
that is there but is not a regular file, one that cannot be read, a symbolic link whose target is gone, a
ROMP_PRIVATE_STRINGS naming a file that is not there, is said on stderr at the moment it happens, LIST_UNREADABLE, naming
the path and the reason, since a check that turns itself off must say so) are searched for in every key, string value and NUMBER of
the finished document, case-insensitively (a number by its wire spelling, json.dumps, the spelling the export's writer
puts in the file and the upload puts on the wire, and, when that spelling carries an exponent, by its plain decimal
expansion too, number_spellings, so a listed digit run inside a numeric leaf is found however the file spelled it, the
fourth review round and the closing delta, 2026-09-19; an expansion is taken only for an exponent within
EXPANSION_EXPONENT_MAX, 324 in magnitude, which every double's spelling is within, so a listed 1e-1000000000 keeps its one
spelling and machine_probes says so once, LIST_EXPANSION_SKIPPED, where the unbounded expansion took the export and the upload
down with a MemoryError, the closing re-run of 2026-09-19; a bool and null are not scanned; a listed string is applied to a
NUMBER only when some spelling of it, the entry as listed or the plain decimal expansion of an entry written with an
exponent, carries at least NUMERIC_PROBE_MIN_DIGITS digits, seven, counted across the whole spelling (numeric_probe:
1234.5678 has eight, (12345678) has eight and is applied by its token run; never the longest run, never the character
length, and never the alphabet: an entry carrying other characters is applied too, since the base matched it to a number
by its token run and dropping that sent three refused documents), the floor the comment at that constant derives from
measured collision chances, since 2026-09-19, and a listed entry that could match a number (number_matchable: spelled in
the number alphabet, or a run of digit-only tokens such as (123456) or _123456, which the token-run arm would apply at
seven digits) whose every spelling has fewer digits is checked in every key and string value and in no number, which
machine_probes says once on stderr, LIST_UNDER_NUMERIC_FLOOR, naming the counted entries by their list lines (never their
text, never the list's path) and what does protect a number; an entry outside the number alphabet with a letter in a
token (zz424242, abc12) is not counted, the one letter a number spells being an exponent's e, which the alphabet arm reads,
so a listed 1e5 or 1.5e-04 is counted by its spelling, and the line reports the digit-count side only, so its silence is not
a claim that an entry it does not count matches some number), and a
hit refuses the write naming
the key path and the kind of string, never the value; for a listed string the refusal also names the LINE of the list
the entry is on (Hit.line, carried from the Probe, never the text) and the remedy, editing that line or the value.
A hostname or a login is a WORD and is matched as a run of whole tokens
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
neither the hostname nor the login, so no other probe knows it; the upload verb, 2026-09-18, is a road where a
document leaves the machine without a human reading it, which is what made the gap consequential), so a
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
from decimal import Decimal, InvalidOperation

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
    reason in UPTIME_KEYS's comment; anything that is not a number, or is a float that is not finite (a bool, null, a
    string, a NaN the fold has nulled) is returned as it is. TOTAL over ints, whatever their size: an int takes the
    exact arm (value - value % 60), a float the floor of its quotient. Until 2026-09-19 the guard was math.isfinite(value)
    over either type and the quotient was taken for both, and each raises OverflowError for an int float() cannot hold
    (10**400: "int too large to convert to float", "integer division result too large for a float"); denylist_problems
    applies this function to a RAW file value on the upload road, and the verb answered a 401-digit uptime with a
    thirty-line traceback where it promises one refusal line (the closing check's HIGH 2). The parse now refuses such
    an int before any check (cli/perf_upload.py, _bounded_int) and finite_number nulls it in any fold; this arm is
    the belt behind both, so no caller can raise here whatever it hands in."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (isinstance(value, float) and not math.isfinite(value)):
        return value
    if isinstance(value, int):
        return value - value % UPTIME_GRAIN_S
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
    a reader cannot tell from a rounded one. Anything that is not a positive number, or is a float that is not finite (a
    bool, null, a string, zero, a negative, a NaN the fold has nulled) is returned as it is. TOTAL over ints, whatever
    their size: the finiteness test is asked of a float alone, and the body is exact for an int (math.ceil of an int is
    the int, bit_length is exact), so public_bound(10**400) is 1 << 1329. Until 2026-09-19 the guard was
    math.isfinite(value) over either type, which raises OverflowError for an int float() cannot hold, and
    denylist_problems applies this function to a RAW file value on the upload road (the closing check's HIGH 2; the
    same belt as public_uptime's)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (isinstance(value, float) and not math.isfinite(value)) or value <= 0:
        return value
    return 1 << (math.ceil(value) - 1).bit_length()


# The memory-fraction bounds by PATH below the snapshot root, the ten the BOUND_KEYS comment lists, and the one constant
# that sits under a BOUND_KEYS name (memos.judgingBand.bound, the kernel's _JUDGING_ROW_CAP, a literal count of rows,
# coarsened at no cost). The judge child's copies of its tables carry the same keys under ("judge", "child"). The
# disclosure paragraph's "ten memory-fraction bounds" is pinned against these two sets by tests/test_perf_stats.py
# (Disclosed): every bound-keyed leaf on the wire, the ("judge", "child") prefix stripped, is classified against them,
# and a leaf in neither is red there, so a constant added under one of the keys does not read as an eleventh fraction
# and a fraction dropped does not pass as a constant (the closing check's finding 4, 2026-09-19: the pin's set-aside
# had the two labels swapped, pusher.stageRingMax as a ring length and memos.judgingBand.bound as a fraction, where the
# kernel's _stage_ring_len scales the ring one per 256 MiB of MemTotal and _JUDGING_ROW_CAP is the literal 20000).
MEMORY_FRACTION_BOUNDS = frozenset({
    ("recordCache", "budgetBytes"), ("heap", "hydrated", "capBytes"), ("checkpoints", "docMemo", "capBytes"),
    ("asmCheckpoint", "asmDocMemo", "capBytes"), ("asmIndex", "cap"), ("pusher", "stageRingMax"),
    ("builds", "feed", "memo", "bound"), ("memos", "notices", "bound"), ("memos", "spendTree", "bound"),
    ("memos", "summaryAnchor", "bound"),
})
CONSTANT_BOUNDS = frozenset({("memos", "judgingBand", "bound")})


def finite_number(x):
    """`x` when a double can hold it, else None: a bool passes; an int passes when float(x) does not raise OverflowError
    (2**1024 - 2**970, 309 digits, is the first int that raises; int(sys.float_info.max) + 1 and everything below the
    edge round to the largest double and pass); a float passes when math.isfinite. THE RULE is "representable as a
    finite double", the same rule that nulls a NaN or an infinity: every double reader, a browser's JSON.parse or the
    receiver, makes an infinity of an integer past the double, so it is not a value the public form can carry and is
    written null the way a NaN is. Until 2026-09-19 (_finite, the name kept below as an alias) an int of any size was
    kept, so fold({"rss_kb": 10**400}) wrote 401 digits and the export road put them in the file (the closing check's
    HIGH 2). The fold's leaf case and the coarsenings' None identity in _merge rest on this."""
    if isinstance(x, bool):
        return x
    if isinstance(x, int):
        try:
            float(x)
        except OverflowError:
            return None
        return x
    return x if math.isfinite(x) else None


_finite = finite_number      # the name before 2026-09-19


def held_number(x):
    """`x` unless it is a number no double holds, then None: finite_number over the RESULT of a coarsening or a sum, which
    can pass the edge from inputs that did not. public_bound rounds a bound at or past 2**1023 up to 2**1024, which no
    double holds (int(sys.float_info.max) under capBytes); public_uptime's int arm steps a negative uptime just inside the
    edge past it (-(2**1024 - 2**970 - 1) has a residue of 49); _merge sums two ints or two floats near the largest double
    past it, the float sum an infinity. The closing check at the re-run's head (2026-09-19) drove the first two through the
    export child: the file carried 2**1024 and 2 * fmax, numbers the fold's own docstring said it never writes, and the
    upload refused the export's own output as not strict JSON. So every such result is held to the same rule as a parsed
    leaf, and a fold's output is its own fold on these inputs (pinned in tests/test_perf_export.py, FoldInvariant).
    Anything that is not a number (None, a string, a bool) is returned as it is, so a coarsening that returned its input
    unchanged is not judged twice."""
    return finite_number(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else x


def _merge(a, b):
    """Two values whose keys folded to the same name: numbers add, dicts merge, lists join; anything else that
    disagrees is `other`. None is the identity: a non-finite number is nulled by finite_number before it gets here, and
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
    decision. The sum's RESULT is held to finite_number's rule (held_number): two ints or two floats a double holds can sum
    past the largest double (the float sum is an infinity), and until 2026-09-19 the fold wrote the sum as it stood, 2 *
    int(sys.float_info.max) under a merged key, the closing check at the re-run's head; null now, like a parsed number no
    double holds, and the re-coarsened bound the same way."""
    if a is None or b is None:
        return b if a is None else a
    if isinstance(a, bool) or isinstance(b, bool):
        return a if a == b else OTHER
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return held_number(a + b)                 # two measurements near the largest double sum past it: null, as a parsed one is
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = _merge(out[k], v) if k in out else v
            if k in BOUND_KEYS and k in a:
                out[k] = held_number(public_bound(out[k]))     # the sum of two coarsened bounds is not a power of two: coarsen again
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
    non-finite numbers null (finite_number: a NaN, an infinity, and since 2026-09-19 an integer a double cannot hold,
    2**1024 - 2**970 and above, which every double reader, a browser's JSON.parse or the receiver, would make an
    infinity of), the kernel's uptime rounded down to whole minutes (UPTIME_KEYS), every memory-fraction
    bound rounded up to a power of two (BOUND_KEYS). `where` is the path of ORIGINAL keys, which the denylist and the
    block grammars are keyed on. The RESULTS of the two coarsenings and of _merge's sums are held to the same rule as a
    parsed leaf (held_number): a bound at or past 2**1023 rounds up to 2**1024, which no double holds, and two summed
    measurements can pass the largest double, so each is written null too, and the output carries no number a double
    cannot hold whatever the input carried (the closing check at the re-run's head, 2026-09-19, found the export writing
    2**1024 under capBytes for int(sys.float_info.max) and the upload refusing that file). Returns a new document; the
    input is not touched. The output is a fixed point of the denylist walk (denylist_problems) except for the float case
    _merge names, and on the constructed inputs above it is its own fold (fold(fold(x)) == fold(x), pinned)."""
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
                fv = held_number(public_uptime(fv))     # kept coarsened: whole minutes (UPTIME_KEYS); the result held by a double
            elif k in BOUND_KEYS:
                fv = held_number(public_bound(fv))      # kept coarsened: the next power of two (BOUND_KEYS); null past 2**1023
            out[nk] = _merge(out[nk], fv) if nk in out else fv
        return out
    if isinstance(node, (list, tuple)):
        return [fold(v, where + (i,)) for i, v in enumerate(node)]
    if isinstance(node, str):
        return node if IDENT.fullmatch(node) else OTHER
    if isinstance(node, bool) or node is None:
        return node
    if isinstance(node, (int, float)):
        return finite_number(node)     # a NaN, an infinity or an int a double cannot hold is null
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


class Hit(collections.namedtuple("Hit", "kind is_key path depth line", defaults=(None,))):
    """One finding of the identifier scan (identifier_hits), shaped like Problem: `kind` the probe's kind (hostname,
    username, home directory, session id, session directory, private string), `is_key`, `path` and `depth` as
    Problem's, and `line`, the one-based line of the private list the matching entry is on (the Probe's; None for a
    machine string or a probe built without one), which the refusal names in place of the entry. The string that
    matched is not carried (a number's is its wire spelling): a key IS the string, and the scan's callers print the
    finding in a refusal."""
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
    integer a double can hold passes whatever its size; one it cannot hold (2**1024 - 2**970 and above) is null in any
    fold's output and refused at the upload's parse (cli/perf_upload.py, _bounded_int), so it reaches this walk on no
    road, and the two coarsenings this walk applies to a raw value, public_uptime and public_bound, are total over ints
    since 2026-09-19 so that even a caller that hands one in gets a finding and never an OverflowError (the closing
    check's HIGH 2 drove a 401-digit uptime through this walk to a traceback); a float outside both windows tells no
    time and is a measurement the export keeps, the
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
            # a float alone, inside one of the epoch windows, and never with a duration key on its path: an integer a double can
            # hold is a total whatever its size (one it cannot hold reaches no walk: the parse refuses it, the fold nulls it), a
            # float outside both windows is a measurement, and so is a float under a key that names a
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
DIGITS = frozenset("0123456789")               # the decimal digits, the explicit ASCII set (str.isdigit accepts other scripts' digits too)
# NUMBER_CHARS is an ALPHABET test, not a grammar: every character json.dumps emits for a finite int or float (400k values
# sampled, 2026-09-19). It admits arrangements no number spells (10.0.0.1, 2026-09, +424242, 1e5e5), accepted because the
# alphabet decides nothing alone: it is one arm of number_matchable, which decides only whether the stderr line COUNTS an
# under-floor entry (machine_probes), never whether an entry is applied to a number (numeric_probe, by digit count alone).
# The other arm is a run of digit-only tokens, so a parenthesised, underscored, slashed or space-split run under the floor
# ((123456), _123456, 123456/, 1 23456) IS counted, an IP address under the floor is counted too, and an entry outside the
# alphabet with a letter in a token (zz424242, abc12) is not: the one letter a number spells is an exponent's e, which the
# alphabet arm reads (a listed 1e5 or 1.5e-04 is counted by its spelling; TOKEN splits 1.5e-05 into 1, 5e and 05), and a
# token carrying e outside the alphabet (_1.5e-05_) is the one run the token-run arm could apply at seven digits that the
# count leaves out, by the ruling's rule of no letters (the closing re-run's verification, 2026-09-19, found the first
# wording here, that no number's token carries a letter, false by that example). The closing delta's cut had counted the
# alphabet alone and justified that by saying an entry outside it was matched by no number, so the line's remedy could not
# reach it; execution at the closing re-run of 2026-09-19 falsified that: (1234567), _1234567 and 1234567/ each refuse the
# leaf 1234567 through the token-run arm, so the remedy, listing more of the value's digits, reaches exactly those entries,
# and the operator whose private value is an underscored six-digit id is unprotected in numbers and is now told so.
NUMBER_CHARS = frozenset("+-.0123456789e")
# THE NUMERIC FLOOR (2026-09-19; its predicate corrected by the closing delta the same day). identifier_hits scans a number by
# its wire spelling (json.dumps) and, when that spelling carries an exponent, by its plain decimal expansion too
# (number_spellings), and applies a listed private string to those spellings only through a SPELLING OF THE ENTRY that carries
# at least NUMERIC_PROBE_MIN_DIGITS digits counted across the whole spelling (numeric_probe: 1234.5678 has eight, 1234.56 six,
# 4242424 seven, 1.5e-05 four as listed and seven as its plain expansion 0.000015, which is the spelling armed); a listed entry
# that could match a number (number_matchable: spelled in the number alphabet, or a run of digit-only tokens) whose every
# spelling has fewer digits is checked in every key and string value as before and in no number, and machine_probes says so
# once on stderr (LIST_UNDER_NUMERIC_FLOOR, naming those entries by their list lines, list_lines_phrase, and saying what does
# protect a number). The floor is by DIGIT COUNT and by nothing else: an
# entry carrying characters outside NUMBER_CHARS ((12345678), _12345678, 12345678/, 1234 5678, zz4242424) is armed by the
# same count and is applied by its token run
# (probe_in), which matches a number whose digit groups split the same way, as the base at 5d1de45dc did; the closing delta's
# first cut gated the arm on the alphabet and turned three refusals into sends ((12345678), _12345678 and 12345678/ against
# the leaf 12345678, refused at the base and at cd3b4cfab, exported and POSTed under that cut), so the alphabet decides nothing
# about the arm, and the stderr count is by number_matchable: a run of digit-only tokens under the floor ((123456), _123456,
# 123456/, 1 23456) is counted beside the alphabet-spelled entries, since the token-run arm would apply it at seven digits, and
# an entry outside the alphabet with a letter in a token is not, the exponent's e being the one letter a number spells and
# read by the alphabet arm (the closing delta's cut had counted the alphabet alone, saying the remedy could not
# reach an entry outside it, which the closing re-run of 2026-09-19 falsified by execution: (1234567), _1234567 and 1234567/
# each refuse the leaf 1234567). The floor is where a match becomes EVIDENCE, not a tolerated rate of false refusals. Measured on a real export of
# 2026-09-19 (3,770 numbers, 2,684 of
# them integers, none negative or exponent-spelled): a listed run of k digits collides by substring with some number of that
# one export with probability about 0.26 at k=4 (2,558 distinct 4-digit windows over the 10,000 possible), 0.023 at k=5,
# 0.0019 at k=6, 0.00015 at k=7, 0.000012 at k=8 and under one in a million at k=9; over the day's nine real exports together,
# 0.81, 0.13, 0.011, 0.00095 and 0.000076 for k=4 to 8. Those nine exports are not on disk; the one real export this box keeps
# (3,658 numbers, 2,595 of them integers, none negative or exponent-spelled) re-derives the per-export row within its stated
# precision (0.23, 0.021, 0.0018, 0.00015, 0.000012) and is the corpus of the shape rates below. At four digits a match is a
# coin toss on coincidence alone, so a refusal there says nothing about whether the private value is present, and a check that
# refuses at random trains its reader to clear the refusal without looking; at seven the coincidence is about 0.015 percent
# per export, so a match is overwhelmingly the listed value itself. That is why an entry under the floor is not checked in
# numbers at all rather than checked with a known error rate: below the floor the check carries no information.
# WHY THE DIGIT COUNT, and not the longest digit run or the character length. The chance that a listed value of some shape
# collides is the count of distinct windows of that shape over the export's spellings divided by ten to the power of its
# DIGITS: the denominator is set by the digit count alone, and the numerator is bounded by the spellings whatever the shape (a
# float's spelling holds one point, so a pointed shape has at most one window per float), so each digit divides the chance by
# about ten and moving the point does not multiply it back. The first floor (a086ced5a) gated on the LONGEST RUN and so
# excluded a listed 1234.5678 (eight digits, longest run four) while it kept a bare 4242424: the value with the stronger
# evidence was dropped (the dddd.dddd window is bounded by one per float, 1.09e-5 on the comment's export against the 1.5e-4
# of the seven-run it kept, fourteen times; measured 7.2e-7 on the export on disk, two hundred times), the base at 5d1de45dc
# had refused that value on both roads while a086ced5a sent it, and the stderr line then advised listing more consecutive
# digits, which silenced the line and protected nothing, since that number's spelling carries no eight consecutive digits. A
# CHARACTER-LENGTH gate over the number alphabet admits 1234.56 (seven characters, six digits), a value drawn from a million:
# the verifier measured its window at 8.75e-4 on a corpus of the comment's shape, 2.6 times the bare seven-run's; on the
# export on disk the six-digit pointed shapes collide between 5.2e-5 (ddddd.d) and 1.7e-4 (d.ddddd, 1.2 times the bare
# seven-run) with dddd.dd at 7.6e-5, every seven-digit pointed shape is under 1.8e-5 and every eight-digit one under 1.8e-6
# (the closing delta's floor-measurement script over the export on disk, counts only). A digit-count gate admits 1234.5678
# and excludes 1234.56 and 424242, which is the order the chances have. THE ONE EXCEPTION TO "EACH DIGIT DIVIDES BY TEN": the
# leading zeros of a fraction count as digits and add no evidence. A listed 0.000015 counts seven and is armed, but a float
# spelled 1.5xe-05 for any digit x expands to 0.000015x and carries it, so the entry collides with every float in
# [1.5e-05, 1.6e-05), about one in a hundred of the floats in that decade, the rate of its TWO significant digits and not of
# seven (the closing delta's verifier measured 5 of 800 random exponent-spelled floats; the same holds with no exponent for a
# listed 0.001234 against [0.001234, 0.001235)). Such an entry is armed at the collision rate of its significant digits; no
# real export's float sits in those ranges today (none is exponent-spelled), and the count is not corrected for it because a
# significant-digit floor would drop 0.000015 and 1.5e-05 from the numeric arm, a design change the ruling did not make.
# The list this was measured beside holds eleven entries, none spelled like a number or as a run of digit-only tokens, so
# none is counted by the line, and none carries seven digits, so none is applied to a number (at cd3b4cfab the line's longest-run trigger counted five of
# them, entries carrying a letter, and fired on every run here, which the closing check caught); the floor is a guard for a
# list that later holds a numeric value.
# What the floor leaves as it was. A hostname or a login (WORD_KINDS) is matched as a run of whole tokens, so over a number
# it matches a whole digit group only (an all-digit hostname or login of PROBE_MIN or more characters; rare, the cost
# identifier_hits' docstring names), and it stays applied to numbers at any length. Every other probe is a substring match
# and takes the floor, which changes nothing for the machine's own strings: a home directory and a working directory carry a
# slash, which no number spells; a whole session id carries dashes inside it, which a number spells only in front; and its
# eight-character prefix, the shortest id probe, is an eight-digit run when it is all digits, above the floor, and with a
# hex letter in it matches no number spelling (json spells `e` only after one digit or a pointed mantissa and before a
# signed exponent, and never a, b, c, d or f). So the floor's one effect is on the private list.
# WHAT THE LINE DOES NOT SAY. The line reports the digit-count side only; an entry it does not count is not thereby matchable
# in a number: a listed 192.168.100.200 carries twelve digits and is armed, and its four digit groups spell no json number, so
# it matches none, while 10.0.0.1 beside it is counted (five digits). An entry can be above the floor and match nothing, and
# the line is silent about it; its silence is not a claim (the closing re-run of 2026-09-19, finding 9).
NUMERIC_PROBE_MIN_DIGITS = 7
# THE EXPANSION BOUND (the closing re-run of 2026-09-19). number_spellings spells an exponent-written number out in plain
# decimal with format(Decimal(text), 'f'), which writes about as many digits as the exponent, so that work is exponential in
# an ENTRY'S LENGTH while PRIVATE_STRINGS_MAX bounds only the FILE: a 13-character entry, 1e-1000000000, asks for a billion
# digits (measured at the closing re-run: 1e-400 is 402 characters, 1e-100000 is 100002, 1e-10000000 is 10000002, and
# 1e-1000000000 a MemoryError that took `romp perf export --public` and `romp perf upload` down with a traceback, where
# cd3b4cfab exported the same list with rc 0). The bound is stated against the thing that grows, the exponent, and is derived
# from the double: the smallest positive double is 5e-324 and the largest 1.7976931348623157e+308 (sys.float_info.max), so
# every finite leaf's repr, which is what json.dumps writes, has its leading digit's exponent (Decimal(text).adjusted()) in
# [-324, 308]. A listed entry outside that range is the spelling of no leaf, and its plain expansion is longer than any leaf's
# spelling (the longest leaf expansion is 5e-324 at 326 characters), so no leaf spelling holds it as a substring and no leaf's
# digit groups equal its token run: skipping its expansion loses no protection, and the expansion's length is then at most
# 325 characters plus the mantissa's own digits, linear in the entry's length. The bound is symmetric, 324 in magnitude, so its positive
# side admits exponents 309 to 324 that no double reaches; those expand to at most 325 digits, harmless, and a one-sided bound
# would buy nothing. The bound is asked before any expansion
# (expansion_bounded, in number_spellings itself; Decimal construction is instant for any exponent the decimal module
# accepts, and only format expands), so
# identifier_hits, which expands every probe and every leaf, never formats an unbounded entry either; machine_probes says
# once which listed entries kept their one spelling for this reason (LIST_EXPANSION_SKIPPED, by list line). THE GUARD'S OWN
# LIMIT: the decimal module refuses to construct a number whose exponent is past decimal.MAX_EMAX (999999999999999999, about
# 1e18, the same on 3.10 through 3.14t) and raises InvalidOperation before adjusted() can run, while json reads the same
# text as the finite float 0.0, so a 22-character entry such as 1e-9999999999999999999 reached the guard and killed all
# three verbs with that traceback at the closing re-run's verification (2026-09-19), one exponent longer than the pinned
# input; expansion_bounded reads the refusal as beyond the bound, which it is by construction, and such an entry takes the
# same skip line. An entry that
# overflows to infinity (1e400; _number_value None) keeps the older silent road: it was never expanded, and nothing is said.
EXPANSION_EXPONENT_MAX = 324
# The machine-local list of strings that must never be published: the file the repository's pre-push hook reads
# (.githooks/pre-push, scan_identifiers), one string per line, a `#` starting a comment, surrounding whitespace
# dropped, blanks skipped, resolved as the hook resolves it (private_strings_path). Plainly absent on a clone that never
# set one up (nothing at the derived path), and then it adds nothing, in silence: that is the normal case. EVERY OTHER
# ROAD TO NO LIST IS SAID: a path that is there but is not a regular file (a directory, a fifo, a device node, a socket),
# one that cannot be opened or read (a permission, a parent that is not a directory), a symbolic link whose target is
# gone (a list set up once and now pointing at nothing; the open reports the target absent, and the link is told apart
# by lstat), a ROMP_PRIVATE_STRINGS that names a file that is not there (a typo in the one setting the operator wrote),
# each writes LIST_UNREADABLE to stderr at the moment it happens, naming the path and the reason, and the caller goes on
# with no list. The list is a protection, and a protection that turns itself off
# must say so when it does, not when someone wonders: the upload's third review round (2026-09-18) found the two loud
# lines below written for the over-the-bound case and for a case the reader cannot produce, while the one road that
# disabled the whole list, a fifo or a directory or an unreadable file at the path, sent a document carrying a listed
# string with nothing on stderr. A line that is not UTF-8 is not an entry and is counted once in LIST_NOT_UTF8 the same
# way, where a replaced byte once made it a probe that matched nothing while the list read as in force.
# Read with a bound: a list is a few lines, and a file put there by mistake costs
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
# The count, the list's length, the skipped entries' LIST LINES (list_lines_phrase) and the bound (EXPANSION_EXPONENT_MAX):
# written once, BEFORE LIST_UNDER_NUMERIC_FLOOR, since the skip explains why such an entry has one spelling, which the floor
# line then judges (a listed 1e-400 is skipped and then counted under the floor, two lines in that order). Never the text.
LIST_EXPANSION_SKIPPED = ("romp: %d of %d private-strings entries (%s) are written with an exponent beyond %d, further than any number in an "
                          "export reaches, so each is checked by its own text and not by its plain decimal expansion")
# The count, the list's length, the counted entries' LIST LINES (list_lines_phrase), the floor twice. The line names the
# entries it counts by the line of the list each is on and never by its text (the text is what the list exists to keep off
# every output, stderr included; a refusal names its entry the same way, Hit.line), and it does not name the list's path:
# there is one list location, the docs name it, and a home path on stderr every run is noise (the review of 2026-09-19).
# The enumeration is capped: the first LIST_LINES_NAMED lines in file order, then `and N more` for the rest, so the line
# stays one line at a realistic entry count (an advisory that wraps is one nobody reads).
LIST_UNDER_NUMERIC_FLOOR = ("romp: %d of %d private-strings entries (%s) could match a number, by their spelling or by their digit groups, but "
                            "carry fewer than %d digits, so they are "
                            "checked in keys and string values and not in numbers; a number is checked against a listed entry only when the entry, "
                            "or the plain decimal spelling of an entry written with an exponent, carries %d or more digits, and the match is against "
                            "the number's own spelling: a listed 1234.5678 protects the number 1234.5678, a listed 12345678 does not, and a listed "
                            "entry of fewer digits protects no number")
LIST_UNREADABLE = "romp: no private-strings list was read from %s (%s); no listed string is checked"   # the path and the reason
LIST_NOT_UTF8 = "romp: %d line(s) of the private-strings list at %s are not UTF-8 and are not checked"


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


def _file_kind(path):
    """For LIST_UNREADABLE: the kind of thing at `path` when it is not a regular file (a directory, a fifo, a socket, a
    character device, a block device), by a stat of its own for the message alone, whether open_regular's fstat found
    it (None returned) or the open itself failed on it (a socket is ENXIO at the open, a block device EACCES for an
    account outside its group); None for a regular file, or a path that cannot be stat'ed, and the caller says what
    it knows instead (the error's class, or "not a regular file")."""
    try:
        mode = os.stat(path).st_mode
    except OSError:
        return None
    for test, kind in ((stat.S_ISDIR, "a directory"), (stat.S_ISFIFO, "a fifo"), (stat.S_ISSOCK, "a socket"),
                       (stat.S_ISCHR, "a character device"), (stat.S_ISBLK, "a block device")):
        if test(mode):
            return kind
    return None


def private_entries(env):
    """[(line, str)]: the private list's entries with the ONE-BASED LINE of the file each is on (comment and blank lines
    count, so the number is the one an editor shows; a refusal names it in place of the entry's text), a `#` comment and
    surrounding whitespace stripped from each line and blanks
    dropped, read line by line as UTF-8 from a REGULAR file (open_regular) of at most PRIVATE_STRINGS_MAX bytes:
    PRIVATE_STRINGS_MAX + 1 are read, and a file over the bound is cut back to the last complete line inside it, so no
    fragment of an entry becomes a probe, with LIST_OVER_BOUND said once on stderr, since the entries from the cut on
    are not checked; a file exactly at the bound is read whole and nothing is said. A line that is not UTF-8 is not an
    entry, and how many were dropped is said once (LIST_NOT_UTF8), never a traceback. [] when there is no list to read,
    and in SILENCE for exactly two of those roads: no path at all (no HOME and no variable), and the derived default
    path PLAINLY absent, nothing at the path (os.path.islink False), a clone that never set a list up. Every other road
    to [] is said once on stderr (LIST_UNREADABLE, the path and the reason): a symbolic link at either path whose target
    is gone (a list set up once and now pointing at nothing, the protection turning itself off, not a clone without a
    list: os.open follows the link and reports the target absent, so the link is told apart by lstat), a
    ROMP_PRIVATE_STRINGS that names a file that is not there (absent), a path that is not a regular file (a directory,
    a fifo, a device node, a socket, by kind through _file_kind, whether the fstat or the open itself found it), and
    one that cannot be opened or read (the error's class). The comment at PRIVATE_STRINGS_VAR says why silence is the
    wrong signal here."""
    path = private_strings_path(env)
    if not path:
        return []
    try:
        fh = open_regular(path)
    except FileNotFoundError:
        if os.path.islink(path):                 # a link whose target is gone: a list set up once, now pointing at nothing
            sys.stderr.write(LIST_UNREADABLE % (path, "a symbolic link whose target is absent") + "\n")
        elif env.get(PRIVATE_STRINGS_VAR):       # named by the operator and not there; the derived default's plain absence is the normal case
            sys.stderr.write(LIST_UNREADABLE % (path, "absent") + "\n")
        return []
    except OSError as e:                          # a socket (ENXIO), a device the account cannot open, a permission, a parent that is a file
        sys.stderr.write(LIST_UNREADABLE % (path, _file_kind(path) or e.__class__.__name__) + "\n")
        return []
    if fh is None:
        sys.stderr.write(LIST_UNREADABLE % (path, _file_kind(path) or "not a regular file") + "\n")
        return []
    try:
        with fh:
            raw = fh.read(PRIVATE_STRINGS_MAX + 1)
    except OSError as e:
        sys.stderr.write(LIST_UNREADABLE % (path, e.__class__.__name__) + "\n")
        return []
    if len(raw) > PRIVATE_STRINGS_MAX:
        raw = raw[:PRIVATE_STRINGS_MAX]
        raw = raw[:raw.rfind(b"\n") + 1]        # back to the last complete line; empty when the bound cut the first one
        sys.stderr.write(LIST_OVER_BOUND + "\n")
    out, undecodable = [], 0
    for number, line in enumerate(raw.split(b"\n"), 1):
        try:
            text = line.decode("utf-8")
        except UnicodeDecodeError:
            undecodable += 1
            continue
        text = text.split("#", 1)[0].strip()
        if text:
            out.append((number, text))
    if undecodable:
        sys.stderr.write(LIST_NOT_UTF8 % (undecodable, path) + "\n")
    return out


def private_strings(env):
    """[str]: the texts of private_entries, in file order, without the line numbers: the reader's view for a caller that
    names no line (the pre-push hook reads the same texts). Every road to no list, and every loud line, is
    private_entries'."""
    return [text for _, text in private_entries(env)]


def digit_count(s):
    """How many characters of `s` are decimal digits (DIGITS, the ASCII set), counted across the whole string: what
    NUMERIC_PROBE_MIN_DIGITS is measured against (`1234.5678` is 8, `1234.56` is 6, `424242` is 6, `4242424` is 7,
    `1.5e-05` is 4, `12345670000000000` is 17, `0.000015` is 7, `abc12` is 2, `abc` and the empty string are 0). Never
    the longest run: the first floor (a086ced5a) measured that and excluded 1234.5678 while it kept 4242424, the comment
    at NUMERIC_PROBE_MIN_DIGITS."""
    return sum(1 for c in s if c in DIGITS)


def number_shaped(s):
    """Is `s` spelled like a number: at least one digit, and every character in NUMBER_CHARS, the alphabet json.dumps
    spells a finite number with (`1234.5678`, `-4242424`, `1.5e-05`, `.5678` and `4242424` are; `abc12`, `zz4242424`, a
    lone `e` and the empty string are not). Read by number_matchable alone, as one of its two arms, to decide whether an
    entry under the floor is COUNTED by the stderr line (machine_probes); the alphabet decides nothing alone, and a
    string outside it can still be counted through the other arm, a run of digit-only tokens ((123456)), or be left
    uncounted by a letter in a token (abc12: at cd3b4cfab the line counted any digit run under the floor, letters or
    not, and fired on every run on this box for entries carrying a letter). It decides nothing about whether an entry is
    APPLIED to a number (numeric_probe, by digit count alone): an entry outside the alphabet can match a number by its
    token run, and the base did. An alphabet test, not a grammar: 10.0.0.1 and 2026-09 are shaped (the comment at
    NUMBER_CHARS). On the entry's stripped lower-cased text, the normalisation machine_probes applies (a listed `1.5E-05`
    is `1.5e-05`)."""
    return any(c in DIGITS for c in s) and all(c in NUMBER_CHARS for c in s)


def number_matchable(s):
    """Could some spelling of `s` match a number: `s` is spelled in the number alphabet (number_shaped), or it is a run of
    one or more digit-only tokens (TOKEN over it, every character of every token in DIGITS), which probe_in matches
    against a number whose digit groups split the same way ((1234567), _1234567 and 1234567/ each refuse the leaf 1234567
    through the token-run arm, executed at the closing re-run of 2026-09-19; (123456), _123456, 123456/ and 1 23456 are
    matchable and under the floor). An entry outside the alphabet carrying a letter in a token (zz424242, abc12) is not, and
    neither is a lone `e` (no digit): the one letter a number spells is an exponent's e, and an entry in the alphabet that
    carries it (1e5, 1.5e-04; TOKEN splits 1.5e-05 into 1, 5e and 05) is matchable through number_shaped, while a token
    carrying e outside the alphabet (_1.5e-05_) is the one run the token-run arm could apply at seven digits that this
    leaves out (the closing re-run's verification found the first wording, that no number's token carries a letter, false
    by that example); nor is a string with no token (the empty string, `()`, `_`). Read by machine_probes
    alone, to decide whether an entry under the floor is COUNTED by LIST_UNDER_NUMERIC_FLOOR: the operator whose private
    value is an underscored six-digit id is unprotected in numbers and is told so, where the closing delta's cut,
    counting the alphabet alone, told them nothing (over-counting costs an operator one unnecessary edit; under-counting
    leaves them believing a protection they do not have). Decides nothing about whether an entry is APPLIED to a number
    (numeric_probe, by digit count alone). On the entry's stripped lower-cased text, as number_shaped."""
    tokens = TOKEN.findall(s)
    return number_shaped(s) or (bool(tokens) and all(all(c in DIGITS for c in t) for t in tokens))


def numeric_probe(s):
    """Is the spelling `s` of a listed entry applied to NUMBERS by identifier_hits: it carries at least
    NUMERIC_PROBE_MIN_DIGITS digits (digit_count), the floor the comment at that constant derives, and nothing else is
    asked of it (`1234.5678`, `4242424`, `-4242424`, `12345678e-4`, `0.000015`, `zz4242424`, `(12345678)` and `1234 5678`
    are; `424242`, `1234.56`, `1.5e-05` and `abc12` are not). Not the alphabet: an entry carrying other characters is
    applied by its token run (probe_in), which matches a number whose digit groups split the same way, as the base did;
    the closing delta's first cut required number_shaped here and turned three refusals into sends. Decided per
    SPELLING, so an entry written with an exponent is armed through its plain expansion when that carries the digits
    (identifier_hits applies numeric_probe to each of number_spellings' results; a listed 1.5e-05 is armed as 0.000015
    and not as itself, a listed 1e+16 as 10000000000000000)."""
    return digit_count(s) >= NUMERIC_PROBE_MIN_DIGITS


# How many list lines LIST_UNDER_NUMERIC_FLOOR names before it counts the rest (list_lines_phrase): an advisory that wraps is
# one nobody reads, so at a realistic entry count the line stays one line, the first six lines in file order and `and N more`.
LIST_LINES_NAMED = 6


def list_lines_phrase(lines):
    """`list line 4`, `list lines 3 and 6`, `list lines 3, 6 and 9`, and past LIST_LINES_NAMED lines `list lines 2, 5, 9, 12,
    15, 18 and 3 more`: the ONE-BASED LINES of the private list (private_entries, the number an editor shows) that
    LIST_UNDER_NUMERIC_FLOOR names for the entries it counts, in file order, one phrase inside the one line. The line points
    at each counted entry this way so that it spells no entry's text (the list exists to keep those off every output, stderr
    included; a refusal names its entry by line for the same reason, Hit.line) and names no path (there is one list
    location, the docs name it, and a home path on stderr every run is noise; the review of 2026-09-19). The enumeration is
    CAPPED: at most LIST_LINES_NAMED lines are named, the first in file order, and the rest are counted (`and N more`, N the
    counted entries past the cap), since an advisory that wraps is one nobody reads; at or under the cap the phrase is the
    plain list, `and` before the last line. `lines` is never empty: the line is written only when something is counted."""
    lines = [str(n) for n in lines]
    if len(lines) == 1:
        return "list line " + lines[0]
    if len(lines) > LIST_LINES_NAMED:
        return "list lines %s and %d more" % (", ".join(lines[:LIST_LINES_NAMED]), len(lines) - LIST_LINES_NAMED)
    return "list lines %s and %s" % (", ".join(lines[:-1]), lines[-1])


def _number_value(text):
    """The int or finite float `text` parses to as a JSON number, else None: what number_spellings expands a listed
    entry through. A fragment (`.5678`, `1234567.`), an overflow (`1e400`, which parses to infinity), a plus sign or a
    leading zero parses to no finite number and keeps its one spelling."""
    try:
        value = json.loads(text)
    except ValueError:                                     # not a JSON number; also the interpreter's digit limit on a huge int
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if isinstance(value, int) or math.isfinite(value) else None


def expansion_bounded(text):
    """Is the exponent of the number `text` spells within EXPANSION_EXPONENT_MAX, so that its plain decimal expansion
    (number_spellings) is bounded in length: the exponent of its leading digit, Decimal(text).adjusted(), has magnitude at
    most 324 (`5e-324`, -324, and `1.7976931348623157e+308`, 308, the two ends of the double, are within; `1e-325`, -325,
    `1000000e-400`, -394, `1e+325` and `1e-1000000000` are not; the bound is symmetric, so `1e+309` to `1e+324` are within
    it too, past any double and harmless at up to 325 digits). Decimal construction is instant for any exponent the decimal
    module accepts; only format expands, and this is asked before it (the comment at the constant). Past the module's own
    limit, an exponent whose magnitude exceeds decimal.MAX_EMAX (about 1e18: `1e-9999999999999999999`, `1e-` followed by
    sixty thousand nines), the constructor raises InvalidOperation, and that refusal is read as False here: such an entry
    is beyond the bound by construction, and reading it any other way killed all three verbs with the traceback at the
    closing re-run's verification (2026-09-19). A context with the trap off would hand back a non-finite or a clamped
    Decimal instead, so the finite check stands beside the exponent's. `text` is a spelling json reads as a finite number:
    number_spellings asks this only after _number_value or the leaf itself has said so."""
    try:
        d = Decimal(text)
    except InvalidOperation:                                # an exponent past decimal.MAX_EMAX: beyond the bound by construction
        return False
    return d.is_finite() and abs(d.adjusted()) <= EXPANSION_EXPONENT_MAX


def number_spellings(text, value=None):
    """Every spelling a reader recovers a number's value from, distinct, `text` first: the spellings identifier_hits scans
    a number leaf by and applies an armed listed entry as. `text` is the wire spelling (json.dumps(node) for a leaf; the
    entry as listed for a probe) and `value` the number it spells (the leaf itself; _number_value(text) for a probe).
    When `value` is a finite float and `text` carries an exponent (repr spells a float at or above 1e16 or under 1e-4 in
    magnitude with a point after the first digit and an exponent after the mantissa), the plain decimal expansion of the
    TEXT, format(Decimal(text), 'f') (`1.234567e+16` is `12345670000000000`, `1.5e-05` is `0.000015`, `1.234567e-05` is
    `0.00001234567`, `-1.5e-05` is `-0.000015`, `1e+16` is `10000000000000000`, `1e+23` is `100000000000000000000000`).
    Two spellings at most, and never a third: the exact integer the double holds, str(int(value)), differs from the
    expansion above 2**53 (int(1e+23) is 99999999999999991611392) and spells digits neither the file nor a person wrote,
    binary noise that a listed 9999999 would then match; the closing delta's first cut scanned it and the verifier
    dropped it (the ruling named the plain expansion alone). Decimal of the TEXT, never of the value: Decimal(value) is
    the double's exact binary expansion, not a spelling a reader recovers (Decimal(1e+23) is 99999999999999991611392 and
    never 100000000000000000000000). A number whose repr carries no exponent has the one spelling (5000.0, 0.037,
    1234.5678, 409600, every int), so a real export's numbers gain none: the export the floor was measured on had no
    exponent-spelled number. The closing check of 2026-09-19: a listed 12345670000000000 was refused when the leaf
    spelled the integer and travelled when the same value's canonical spelling was 1.234567e+16; the hole was as old as
    the numeric scan (431db9a60), and this module claimed a listed run was found however the file spelled it. A listed
    entry is expanded the same way and the floor is decided PER SPELLING (identifier_hits applies numeric_probe to each):
    a listed 1.5e-05 is armed as its expansion 0.000015 and not as itself, a listed 1e+16 as 10000000000000000, and an
    expansion that carries fewer digits than the entry is not armed (a listed 1.0000000e+2 is armed as itself and as
    100.00000, both harmless, and never as 100). An entry whose leading exponent is outside EXPANSION_EXPONENT_MAX
    (1000000e-400, adjusted -394; 1e-1000000000, which asked for a billion digits and took two verbs down with a
    MemoryError at the closing re-run of 2026-09-19) keeps its one spelling, and never a `0` (the exact zero it underflows
    to is the first cut's int() road, dropped), and machine_probes says so (LIST_EXPANSION_SKIPPED); within the bound the
    expansion is at most 326 characters (5e-324), so the work here is linear in the text's length (the comment at
    EXPANSION_EXPONENT_MAX: the head before the re-run formatted any exponent, and PRIVATE_STRINGS_MAX bounded the file
    while the work was exponential in an entry's length)."""
    out = [text]
    if isinstance(value, float) and math.isfinite(value) and "e" in text and expansion_bounded(text):
        plain = format(Decimal(text), "f")
        if plain not in out:
            out.append(plain)
    return tuple(out)


class Probe(collections.namedtuple("Probe", "kind text")):
    """A probe as machine_probes builds it: the (kind, text) pair probe_in and identifier_hits read, and BESIDE the pair,
    never in it, `line`, the one-based line of the private list a listed entry is on (None for a machine string), which
    identifier_hits carries into the Hit so that a refusal can name the line and never the text. A plain (kind, text)
    tuple is a probe too, with no line (the tests build them); it compares equal to a Probe of the same kind and text, so a
    repeated entry is one probe, the first line's."""

    def __new__(cls, kind, text, line=None):
        self = super().__new__(cls, kind, text)
        self.line = line
        return self


def machine_probes(state_dir=None, env=None):
    """[(kind, string)]: what only this machine knows. The hostname and its first label, the login name and
    the home directory (with its last component, which is usually the login name), every string on the
    machine-local private list (private_entries, kind PRIVATE_KIND, `private string`: the maintainer's own list of
    what must never be published, absent on a clone that never set one up, matched as a substring or a token run,
    probe_in, each probe carrying the LINE of the list its entry is on, Probe, for the refusal to name), and, when
    `state_dir` holds an sdk registry, every session id (whole and its first eight characters,
    the spelling the scope units and the ledgers use), every conversation id and every working directory.
    Lower-cased; strings shorter than PROBE_MIN are left out, EXCEPT a listed private string: the list is the
    maintainer's explicit choice and not the heuristic the floor exists for, and the floor dropped a three-character
    entry silently while a document carrying it was sent (the upload's second review round, 2026-09-18); an empty
    entry is never a probe (an empty substring is in every string). When a listed entry did not become a probe (the
    reader returns no blank today, so only a filter a later change adds could drop one), LIST_NOT_IN_FORCE says how
    many of how many on stderr: a list silently not in force is the wrong signal. When at least one listed entry could
    match a number (number_matchable, on its stripped lower-cased text: spelled in the number alphabet, or a run of
    digit-only tokens) and NO spelling of it (number_spellings:
    the text, and the plain decimal expansion of an entry written with an exponent) carries NUMERIC_PROBE_MIN_DIGITS
    digits (numeric_probe, the arm's own test, so the two sides partition the number-matchable entries),
    LIST_UNDER_NUMERIC_FLOOR says once how many of how many are checked in keys and string values and not in numbers,
    WHICH by the list line each is on (list_lines_phrase, in file order: never an entry's text, which the list exists to
    keep off every output, and never the list's path, which the docs name and which would put a home path on stderr
    every run; the review of 2026-09-19; at most LIST_LINES_NAMED lines named and the rest counted, `and N more`, so the
    line stays one line however long the list)
    (the comment at the floor: below it a match in a number is coincidence, so identifier_hits does not apply such an
    entry to a number) and what does protect a number: a listed entry of seven or more digits, in its own spelling or
    its plain expansion, matched against the number's own spelling, since a listed bare run protects only a number
    whose spelling carries that run (the first line advised listing more of the value's digits, which for a pointed
    value such as 1234.5678 silenced the line and protected nothing; the closing delta of 2026-09-19). A listed 1e+16 or
    1.5e-05 is not counted: its plain expansion (10000000000000000, 0.000015) carries the digits and is what the arm
    applies. An entry carrying a run of digit-only tokens with other characters around or between them ((123456),
    _123456, 123456/, 1 23456) IS counted: the token-run arm would apply it at seven digits, so the operator whose
    private value is an underscored six-digit id is unprotected in numbers and is told so (the closing delta's cut
    counted the alphabet alone and said the remedy could not reach such an entry, which the closing re-run of
    2026-09-19 falsified by execution: (1234567), _1234567 and 1234567/ each refuse the leaf 1234567). An entry with no
    digit, or outside the alphabet with a letter in a token (zz424242, abc12), is not counted: the one letter a number
    spells is an exponent's e, which the alphabet arm reads, so a listed 1e5 or 1.5e-04 is counted by its spelling (at
    cd3b4cfab the trigger counted any digit run under the floor, letters or not, and the line fired on every run on
    this box for entries carrying a letter); an entry of seven or more digits (zz4242424, (12345678)) is armed and is
    not what the line is about. The line reports the digit-count side only: an entry it does not count is not thereby
    matchable in a number (a listed 192.168.100.200 carries twelve digits and is armed, and its four digit groups spell
    no json number, so it matches none, while 10.0.0.1 beside it is counted); its silence is not a claim (the closing
    re-run of 2026-09-19, finding 9). Both numbers in the line run over listed
    LINES, so a repeated entry is counted once per line while the probes dedupe it to one (a list of 1234.56, 1234.56
    and 424242 says 3 of 3, list lines 1, 2 and 3). BEFORE that line, when a listed entry is written with an exponent
    beyond EXPANSION_EXPONENT_MAX (1e-1000000000: further than any number in an export reaches, and an expansion that
    asked for a billion digits and took this reader's two verbs down with a MemoryError, the closing re-run of
    2026-09-19), LIST_EXPANSION_SKIPPED says once how many of how many kept their one spelling for that reason, by list
    line, never the text and never the path; the skip explains why such an entry has one spelling, which the floor line
    then judges (a listed 1e-400 is skipped and then counted under the floor, two lines in that order; a listed
    1e-1000000000 carries eleven digits as written, so it is armed as itself and only the skip line is written; an entry
    whose exponent the decimal module itself refuses to construct, past decimal.MAX_EMAX at about 1e18, such as
    1e-9999999999999999999, is beyond the bound by construction and takes the same skip line, where at the closing re-run's
    verification the guard's own InvalidOperation killed the three verbs). An
    entry that overflows (1e400, infinity) was never expanded and nothing is said of it, as before. See the module
    docstring for why session names are not probes, and why a listed string that is also romp vocabulary refuses on
    purpose."""
    env = os.environ if env is None else env
    out = []

    def add(kind, s, line=None):
        s = str(s or "").strip().lower()
        if s and (kind == PRIVATE_KIND or len(s) >= PROBE_MIN) and (kind, s) not in out:
            out.append(Probe(kind, s, line))
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
    listed = private_entries(env)
    for line, s in listed:
        add(PRIVATE_KIND, s, line)
    dropped = sum(1 for _, s in listed if (PRIVATE_KIND, str(s).strip().lower()) not in out)
    if dropped:
        sys.stderr.write(LIST_NOT_IN_FORCE % (dropped, len(listed)) + "\n")
    texts = [(line, str(s or "").strip().lower()) for line, s in listed]
    skipped = [line for line, t in texts                                    # exponent-written, finite, and beyond the bound: one spelling, said first
               if isinstance(_number_value(t), float) and "e" in t and not expansion_bounded(t)]
    if skipped:
        sys.stderr.write(LIST_EXPANSION_SKIPPED % (len(skipped), len(listed), list_lines_phrase(skipped), EXPANSION_EXPONENT_MAX) + "\n")
    under = [line for line, t in texts                                      # could match a number, and armed by no spelling: the arm's other side
             if number_matchable(t) and not any(numeric_probe(s) for s in number_spellings(t, _number_value(t)))]
    if under:                                                               # the counted entries by their list lines, never their text or the path
        sys.stderr.write(LIST_UNDER_NUMERIC_FLOOR % (len(under), len(listed), list_lines_phrase(under), NUMERIC_PROBE_MIN_DIGITS,
                                                     NUMERIC_PROBE_MIN_DIGITS) + "\n")
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
    """[Hit] for every key, string value or NUMBER of `doc` that carries a probe (probe_in), case-insensitively, one
    per string (the first probe that matches), in walk order. A Hit is structured like the walk's Problem (the kind,
    key or value, the key path, its depth, and the list line of a listed entry, Probe.line, when the probe carries
    one) and the caller formats it (place), so the string itself is never in the
    report (a key IS the string, so its own path is not named, and its dict's is). `skip` names top-level keys
    whose string value is not searched. A number is scanned by its WIRE SPELLING, json.dumps(node), which is the
    spelling perf_export.document_text puts in the file and `romp perf upload` puts on the wire (json.dumps spells a
    number the same way whatever the indent, and the upload sends the checked document re-serialised by that writer),
    so the spelling scanned is the spelling sent: the private list may hold a digit run, and a listed run written as
    a number (4242424242, 4242424242.0, -4242424242, 0.4242424242, or 4.242424242e9, which canonicalises to
    4242424242.0 and so put the run on the wire from a file that never spelled it) travelled unread while the same run
    in quotes was refused (the upload's fourth review round, 2026-09-19, the round's lens over the final artifact);
    AND, when that spelling carries an exponent (a float at or above 1e16 or under 1e-4 in magnitude: repr puts a
    point after the first digit and an exponent after the mantissa), by every other spelling a reader recovers the
    value from (number_spellings): its plain decimal expansion (1.234567e+16 is 12345670000000000, 1.5e-05 is
    0.000015; never the exact integer of the double, binary noise above 2**53 that nobody spelled), since a listed
    12345670000000000 was refused when the leaf spelled the integer and travelled when the same value's canonical
    spelling was 1.234567e+16, the point after the first digit breaking the substring (the closing check of
    2026-09-19; the hole was as old as the numeric scan, 431db9a60, and the claim that a listed run is found however
    the file spelled it was false until the expansion). A number yields at most ONE Hit, at the first spelling and
    probe that match, and the Hit never carries a spelling. A bool and null are not scanned (they spell no probe).
    A KEY and a STRING VALUE are scanned by EVERY spelling of a listed entry, its text and its plain expansion
    (number_spellings), with no floor, as the entry's own text always was: a listed 1.5e-05 refuses the string 0.000015
    and the key zz0.000015, a listed 1e+16 the seventeen-digit string, a listed 1.0000000e+2 the string 100.00000, and a
    listed 1e5 the string 100000 (six digits, under the floor: applied to no number, and to a string on the same terms as
    a listed 100000). The ENTRY is expanded and never the document's string: a listed 0.000015 refuses the number 1.5e-05,
    whose leaf is expanded, and not a string value spelled 1.5e-05 nor a key zz1.5e-05, since reading a number out of
    every string a document carries is a change no document promises and this scan does not make
    (the closing re-run of 2026-09-19 found the expansion applied to numbers alone, so a listed value written with an
    exponent protected the number and not the same digits in a key or a string, while docs/reference.md already
    promised that a listed 1.5e-05 reaches the floor as 0.000015; the cost is what a listed entry's own text already
    costs there, the key and string scan having no floor, and on the machine's own list no entry gains a spelling, 0 of
    11 by derived count). Each spelling is a Probe carrying the entry's line, so the refusal names the line whichever
    spelling was found.
    What this costs: a number spells no path, no uuid, no hostname and no login (a hex id's eight-character prefix
    can be all digits, rarely, and a login can be, and then a counter carrying it is refused naming the kind and the
    path, like a listed word that is romp vocabulary), so the scan over numbers finds a probe that is a digit run
    alone, which is what the private list is for. THE NUMERIC FLOOR (2026-09-19, the comment at
    NUMERIC_PROBE_MIN_DIGITS): a probe that is not a word is applied to a number only through a spelling of it that
    carries at least NUMERIC_PROBE_MIN_DIGITS digits counted across the whole spelling (numeric_probe: 1234.5678 has
    eight and is applied, 1234.56 has six and is not; never the longest run, which excluded 1234.5678 and dropped a
    protection the base had, and never the character length, which admits 1234.56), since a shorter listed value
    collides with some number of an export by coincidence too often for a match to say anything (measured: about one
    export in four at four digits, about one in 7,000 at seven); a listed entry under the floor is checked in every
    key and string value and in no number, and a word probe (WORD_KINDS, a token-run match) is applied to numbers as
    before. The alphabet is NOT asked: a listed entry carrying characters no number spells ((12345678), _12345678,
    12345678/, 1234 5678) is armed by the same digit count and is applied by its token run (probe_in), which matches a
    number whose digit groups split the same way (a listed (12345678) refuses the leaf 12345678, a listed 1234 5678 the
    leaf 1234.5678), as the base at 5d1de45dc did; the closing delta's first cut required number_shaped here and
    turned three refusals into sends. A listed signed number is applied without its sign the same way (a listed
    -12345670000000000 refuses the leaf 12345670000000000: the token run strips the sign). An armed listed entry is
    applied by every spelling of number_spellings that carries the digits (a listed 1.234567e+16 as 12345670000000000
    and as itself, a listed 12345678e-4 as 1234.5678 and as itself, a listed 1.5e-05 as 0.000015 alone, its own text
    being four digits), each a Probe carrying the entry's line. The floor is decided per spelling; the numbers
    themselves are all scanned, by every spelling; the floor selects the probes."""
    hits = []
    numeric = []                  # the probes applied to a number: a word probe as itself, a listed entry by each spelling at the floor
    spelled = []                  # the probes applied to a key or a string value: a word probe as itself, a listed entry by every spelling, no floor
    for p in probes:
        kind, text = p
        if kind in WORD_KINDS:
            numeric.append(p)
            spelled.append(p)
        else:
            for s in number_spellings(text, _number_value(text)):
                q = Probe(kind, s, getattr(p, "line", None))
                spelled.append(q)
                if numeric_probe(s):
                    numeric.append(q)

    def scan(s, where, key, applicable=spelled):
        for p in applicable:
            kind, probe = p
            if probe_in(kind, probe, s):
                hits.append(Hit(kind, key, "/".join(str(p) for p in where), len(where), getattr(p, "line", None)))
                return True
        return False

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
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            for spelling in number_spellings(json.dumps(node), node):  # as the export writes it and the upload sends it, then its plain expansion
                if scan(spelling, where, False, numeric):              # one Hit per number: the first spelling a floor probe is found in
                    break

    walk(doc, ())
    return hits
