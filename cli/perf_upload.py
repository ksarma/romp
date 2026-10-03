#!/usr/bin/env python3
"""romp-perf-upload: send one paste-safe export (`romp perf export --public`) to a receiver. `romp perf upload FILE`.

    romp perf upload FILE [--yes] [--receiver URL]

The export verb writes a file and stops; this verb sends that file, and nothing else, to the receiver the
operator configured. It is opt-in per invocation and keeps no state: there is no switch to forget and no
default that sends anything. Stage two of the usage-data plan (2026-09-18).

The receiver's address comes from `--receiver`, else the ROMP_PERF_RECEIVER environment variable, else the
file ~/.config/romp/perf-receiver (one line, the `romp default-dir` pattern); with none set the verb refuses
naming the three settings, exit 2, so an installation nobody configured sends nowhere. The address must be an
https URL in printable ASCII with a host and no userinfo, query or fragment (http is allowed for 127.0.0.1 and
localhost alone, for tests); it may carry a path, the base the route is appended to; anything else, a setting
file that is not UTF-8 text or that is there but cannot be read among it, is refused without echoing the value, exit 2
(only an ABSENT file, or one holding no non-empty line, is no receiver). The receiver is
unauthenticated: no credential exists for it, and the verb reads no token from anywhere and sends none.

The file must exist, be a regular file of at most 1 MiB, parse as strict JSON (no NaN or Infinity, as a literal or as
a number written past the double's range, 1e999, or as an integer past about 1.8e308, which a double reader makes an
infinity of, refused by _bounded_int before int() runs for a literal over 309 digits and by float() at the edge; no
key repeated within one object at any depth: the receiver's contract refuses one, and a reader that kept one copy
would silently choose which value is checked and sent) with the top-level `schema` line `romp-perf-export/1`, nest at most MAX_DEPTH levels (32; a fresh
export is about 7 deep; a deeper file is refused in one line that names the bound, before any check walks it and never with a
traceback: the checks recurse one frame per level, and this is the one road that reads a file a person names),
and pass the export's own check again as the file stands, since the user may have edited it: the scan for the
strings only this machine knows, the paste-safety walk and the denylist walk of cli/perf_public.py, through
perf_export.check_document, so a problem is reported by its kind and key path and never by the key or the value (a
listed private string by the line of the list its entry is on as well, with the remedy, editing that line or the value); then,
as a belt under the three, the document's top level must be exactly what the export writes (TOP_LEVEL: schema,
exported_at and perf, with kernel_commit and usage optional, no other key, exported_at and kernel_commit in the shapes
the export spells) and each folded block, perf and usage, must equal its own fold, perf_public.fold, at the block root;
a document that is not is refused naming the top-level key alone (a name the checks just passed). Any of these refuses
with exit 1. The rule the re-check holds the file to is the export's (its third review round, 2026-09-18): the public
form is PASTE-SAFE, not unlinkable. The export removes identifiers, paths, free text, machine strings and every absolute
clock stamp and coarsens the uptime and the memory-fraction bounds; durations, counts and per-process measurements stay,
so two exports from one kernel remain linkable through them by design. The re-check refuses what the export would have
dropped, folded or coarsened, and of clock stamps it judges a FLOAT-VALUED one (a `t` put back on a split row, a string
value the export would have folded to `other`, a key it would have replaced, one ending in a newline among them, an uptime
typed to the second, a bound typed to the byte, a float inside a clock stamp's epoch window, 1.5e9 to 2.0e9 seconds or
1.5e12 to 2.0e12 milliseconds, under any key but a duration key) and passes what it keeps (an integer a double can hold is a byte
total or a count, whatever its size, which a long-lived kernel's totals carry into the window within hours, one a double cannot
hold being refused at the parse above; a float outside both windows is a measurement,
the allocator's arena on a long-lived kernel among them; a float inside a window under a duration key, a name carrying
the token `ms` such as `cycle_cpu_ms_sum` or `wallMs`, is a millisecond total, which the kernel's sums carry through
the seconds window in weeks), so a fresh export passes whole.

WHAT IS SENT IS WHAT WAS CHECKED. Every check and the fold belt read the PARSED document, and the body post() sends
is that document written out again by the export's own writer (perf_export.document_text: one space of indent, sorted
keys, a trailing newline), never the file's raw bytes. Until the fourth review round (2026-09-19) the verb sent the
file's bytes while its checks read the parse, and whatever the parser discards travelled unread by any check: a number
literal's spelling (digits past a float's precision, a digit run the denylist walk had refused respelled with an
exponent, a listed private string that is a digit run respelled inside a numeric leaf), inter-token whitespace, key
order; the repeated-key refusal closed one instance of that divergence and left the class open. The re-serialisation
closes the class by construction: the artifact the checks bind is the document they read, and the bytes on the wire
are a function of that document alone, pinned by the key-reversed upload in tests/test_perf_upload.py (the closing check
of 2026-09-19 found sort_keys=True in perf_export.document_text was the one thing keeping a file's key order off the
wire, since no check reads key order, and nothing then pinned it: with it removed every test in the repo passed while
the body was the input file byte for byte). A file as the export wrote it re-serialises to itself byte for byte (the
same function wrote it; pinned), so an unedited export goes out as the file. And the checks read the spelling that goes
out: the identifier scan (perf_public.identifier_hits) searches every number by its wire spelling, json.dumps, the same
spelling document_text writes, and, when that spelling carries an exponent, by its plain decimal expansion as well
(perf_public.number_spellings: 1.234567e+16 is also scanned as 12345670000000000, 1.5e-05 as 0.000015, the value a
reader recovers from the wire; never by the double's exact integer, binary noise nobody wrote), so a listed private
string with seven or more digits in some spelling of it (perf_public.NUMERIC_PROBE_MIN_DIGITS, the floor by digit count
over the whole spelling, so a listed 1234.5678 has eight and a listed 1.5e-05 reaches it as 0.000015) is refused in a
numeric leaf however the file spelled it (4242424242, 4242424242.0, -4242424242, 0.4242424242, or 4.242424242e9, which
canonicalises to 4242424242.0 and so once put the run on the wire from a file that never spelled it; 1.234567e+16 for a
listed 12345670000000000, which until the closing check of 2026-09-19 was refused as an integer and sent in exponent
form; and, by its whole-token run, 12345678 for a listed (12345678), as the base did and as the closing delta's first
cut did not), where until the fourth round a number was a measurement to every check and the run travelled as the number
they passed; the paste walk and the denylist walk judge a number by its value, as before. A spelling that carries no
listed entry travels: 4242424242e-3 is 4242424.242 on the wire and no spelling of that value carries the listed run. The
same scan serves the export and restart-metrics, so a counter that spells a listed string refuses those too, naming the
kind, the path and the line of the list the entry is on, the cost the docs already accept for a listed word that is romp
vocabulary; the remedy, which the refusal states, is editing that line or the value. Since 2026-09-19 the scan applies a
listed entry to a number only through a spelling of it, the entry as written or the plain decimal spelling of an entry
written with an exponent, that carries at least perf_public.NUMERIC_PROBE_MIN_DIGITS digits (seven; the comment there
has the measured collision chances); an entry that could match a number, by its spelling or by its digit groups
(perf_public.number_matchable), whose every spelling has fewer is checked in keys
and string values and not in numbers, said once on stderr naming such entries by their list lines (never their text,
never the list's path), and a listed entry of fewer digits protects no number.

Before sending, the verb prints the path, the byte size of the body it will send (the file's own size for a file as
the export wrote it) and the URL it will dial (the address as configured
with the route appended, so a path in the setting is seen at the prompt), then asks for a yes on a terminal
(stdin is a tty). Off a terminal it refuses, exit 2, unless `--yes` is passed: that flag is the form
an agent uses, and its presence in the command is the visible record of the confirmation. No configuration
file or environment variable stands in for it, so nothing sends from a cron by default.

The send is ONE POST to <receiver>/v1/upload, the checked document re-serialised as the body, under six headers: the verb sets
`Content-Type: application/json`, `Content-Length` and a fixed `User-Agent: romp-perf-upload/1` (no version
detail, no hostname); the HTTP client adds `Host` (the receiver's own name), `Accept-Encoding: identity` and
`Connection: close`. A 30 s DEADLINE over the whole exchange (TIMEOUT_S): the connect and, for https, the handshake
are bounded by the connection's own timeout, and from the moment the connection is up a timer shuts its socket down
when the time left runs out, so the send, the status line, the headers and the body together take at most the rest,
and a receiver that answers in pieces each under the limit cannot hold an unattended --yes run open (a per-operation
timeout alone let it, round 2, 2026-09-18); the refusal is the same fixed line whatever phase the deadline cut. Stdlib
urllib through an opener that refuses redirects (a 3xx is an
unexpected answer, never a second request, and its Location is never parsed), reads no proxy variables, and
carries no cookies. The one answer accepted is status 201 with a body of at most 64 KiB that is exactly the JSON
shape {"receipt": <uuid4 string>, "retention_days": <integer>, "av": "ok"|"skipped"}; the verb then prints
`uploaded: receipt <uuid> (kept <N> days; delete by sending the receipt to the project)`, exit 0. Any other
status, a body that is not JSON, an extra, missing or repeated key, a value outside that shape, a connection
error, a timeout or any other error the client raises is a refusal with a fixed message carrying only the status
code or the error's class name: never the body, never the URL, never an exception's message, exit 1.
"""
import argparse
import http.client
import json
import math
import os
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))   # cli/, whether run through the bin/ symlink or loaded by path
import perf_export as pe  # noqa: E402
import perf_public as pp  # noqa: E402  the fold the re-check holds every block to

PROG = "romp perf upload"
SCHEMA = pe.SCHEMA
RECEIVER_VAR = "ROMP_PERF_RECEIVER"
RECEIVER_FILE = "~/.config/romp/perf-receiver"
RECEIVER_FILE_MAX = 4096             # the setting file is one line of printable ASCII; past this it is not an address (fresh-5)
ROUTE = "/v1/upload"
MAX_BYTES = 1 << 20                  # the receiver's cap on Content-Length and on the bytes it reads
# The DEPTH BOUND (the fork review of the second round, 2026-09-18; its stated reason corrected in the fourth, 2026-09-19;
# the reach of every component re-measured at the closing check, 2026-09-19, which found the fourth round's text wrong
# about the writer). This verb is the one road in romp that hands a document a PERSON named to the shared walks
# (perf_public's identifier scan, paste walk, denylist walk and fold, through perf_export.check_document) and to the
# export's writer (perf_export.document_text), and every one of those recurses one frame per level: past the
# interpreter's reach they raise RecursionError. THE MEASURED REACH OF EACH, the deepest chain that passes, bisected in a
# fresh child per probe with one frame on the stack at entry, over a dict chain and a list chain, on the local builds
# (3.10.20, 3.11.15, 3.12.3, 3.13.14, 3.14.6 and the free-threaded 3.14.6t); the CI runner's 3.14t parser figure is the
# check's, every other figure this box's:
#
#   component                    3.10        3.11        3.12          3.13          3.14                    3.14t
#   the walks (check_document)   989         989         992           992           992                     992
#   the fold, dict chain         995         995         997           997           997                     997
#   the fold, list chain         497         497         997           997           997                     997
#   the parser (strict_loads)    992 to 994  992 to 994  9,994-9,997   9,995-9,998   40,101 to 40,129 here   37,235 to 37,253 here;
#                                                                                                            past 100,000 on CI's runner
#   the writer (document_text)   992 to 993  993         994           9,997         37,241 dict chain,      28,971 dict chain,
#                                                                                    past 40,000 list chain  past 40,000 list chain
#
# The walks and the fold stay under 1,000 on every build, at least fifteen times this bound (the fold's list reach halves
# on 3.10 and 3.11, where the list comprehension it recurses through, perf_public.fold, is a frame of its own before 3.12
# inlined comprehensions). The parser's reach differs by ORDERS OF MAGNITUDE between builds, and so does the writer's
# from 3.13 on; on 3.14 and 3.14t both figures moved between runs of the same probe. On every build the walks overflow at
# a shallower depth than the writer, and CI's 3.14t cell alone admitted the 100,000-level test document that every other
# cell's parser refused as not strict JSON (both local 3.14 builds refuse it too), and handed it to the walks, which
# overflowed there at 992 as everywhere. A file's nesting is therefore bounded here, before any walk runs, by a fixed
# number the refusal names, so that no build's parser can hand the walks a document they cannot take. A bound derived
# from the interpreter's limit would sit within a few frames of the walks' reach and would have to follow the fold's list
# reach on 3.10 and 3.11, so it would move with the build; this one is a fixed number well inside every build.
# The measurement the bound rests on: a fresh `romp perf export --public --usage` on 2026-09-18 was 116,063 bytes with a
# maximum nesting depth of 7 by nesting_depth's count (the deepest leaf perf/jobs/stageRing/#/stages/jobs.autoNudge/bytes),
# the reviewer measured 6 on a 129,435-byte document, and the receiver's own contract refuses more than about eight
# levels. The bound is 32, about four times the measured depth: a block the kernel adds later with a few more levels
# passes, and no document within it comes near any build's stack. The walks stay recursive (their traversal order decides
# which of two equally shallow findings a refusal names), which is safe on every other road because the document is
# bounded by construction (the export folds a snapshot the kernel built; restart-metrics reads its own state), and safe
# here only because of this bound: a future road that reads untrusted input owes a bound of its own.
MAX_DEPTH = 32                       # the deepest nesting read_export admits, by nesting_depth's count (the comment above)
# The document's TOP LEVEL, exactly what perf_export.export_document writes (the upload's third review round, 2026-09-18):
# the envelope, schema (checked first, by value), exported_at (the export's strftime("%Y-%m-%dT%H:%MZ")) and an optional
# kernel_commit (perf_export.kernel_commit: the first twelve characters, lower-cased, of a 7-to-64 hex sha, so 7 to 12
# lowercase hex), and the folded blocks, perf and an optional usage, each a dict equal to its own fold at the block root.
# Any other key is refused naming it. Before this allowlist a block nobody thought about at the root passed the three
# checks and the fold belt and was sent: a `judge` block whose denied path is anchored under perf and so not denied at
# the root, a `now` integer, kernel_commit as a dict carrying a token, each folded to itself because fold's rules are
# anchored at the block root and a foreign block has none there. The whole root is NOT folded as one dict for the same
# reason: moving the fold up moves the anchors, and a real export fails it.
TOP_LEVEL = {"schema": True, "exported_at": True, "perf": True, "kernel_commit": False, "usage": False}   # key: required
FOLDED = ("perf", "usage")                                       # the blocks, each held to its own fold at the block root
EXPORTED_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$")     # the export's UTC minute
KERNEL_COMMIT = re.compile(r"^[0-9a-f]{7,12}$")                   # kernel_commit()'s abbreviation of a sha
TIMEOUT_S = 30                       # a deadline over the whole exchange (_Deadline), not a per-operation timeout
USER_AGENT = "romp-perf-upload/1"
ANSWER_MAX = 64 * 1024               # a receipt is under 200 bytes; a longer 201 body is not the shape
LOOPBACK = frozenset({"127.0.0.1", "localhost"})
HOST = re.compile(r"^[A-Za-z0-9.-]+$")
ADDRESS = re.compile(r"[\x21-\x7e]+")     # printable ASCII, no space: what http.client can put on the wire, and nothing urlsplit strips (fullmatch: $ would pass a trailing newline)
UUID4 = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
AV = ("ok", "skipped")
ANSWER_KEYS = frozenset({"receipt", "retention_days", "av"})
NOT_THE_SHAPE = "refused: the receiver answered 201 without the receipt shape this verb accepts (receipt, retention_days, av); no receipt"
NO_ANSWER = "refused: no answer from the receiver (%s); no receipt"     # the error's class name, or TimeoutError when the deadline cut it


class Refusal(Exception):
    """One line for stderr and the exit code: 2 before anything is read or sent for a reason the user fixes in
    the command (no receiver, a bad address, no terminal and no --yes, an answer that was not yes); 1 for a
    file that fails a check or a send that did not end in a receipt."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


# ── the receiver ─────────────────────────────────────────────────────────────────────────────────────────
def receiver_setting(flag, env=None):
    """(text, source): the address as configured and which setting supplied it, in order --receiver, the
    environment variable, the file's first non-empty line; (None, None) when none is set: no flag, the variable unset
    or empty, and the file ABSENT (FileNotFoundError: no such path, or a dangling link) or there and holding no
    non-empty line (a blank file is unset). The file is read under HOME,
    the way `romp default-dir` reads its own. It must be a REGULAR file (pp.open_regular: opened O_NONBLOCK and
    fstat'ed before any read, since a plain open of a fifo blocks until a writer arrives, before any read a bound could
    cover, and a fifo at this path hung the verb indefinitely, the upload's second review round, 2026-09-18), and it is
    read with a bound: at most RECEIVER_FILE_MAX + 1 bytes are taken, so a large file put there by mistake costs that
    much memory and no more. A file that is THERE and is not a readable regular file returns the empty string with the
    file as its source, an address the grammar refuses, so the caller's refusal names the file and nothing of its bytes
    and never says no receiver is set for a path that exists: one that is not regular (a fifo, a device node, by the
    fstat); one whose open or read itself fails (a socket, ENXIO whatever its mode; a file the account cannot read; a
    parent that is a file; a block device outside the account's group); one over the bound (not truncated to its first
    line, which would send to whatever address that line spelled); and one that is not UTF-8 text. Until the fourth
    review round (2026-09-19) every OSError from the open read as absent, and a socket or an unreadable file holding a
    real address had the verb report that no receiver was set. A size check alone would not do (stat reports 0 for a
    device node or a fifo), so the bound is on the read and the kind on the fstat."""
    if flag is not None:
        return flag, "--receiver"
    env = os.environ if env is None else env
    value = env.get(RECEIVER_VAR)
    if value:
        return value, RECEIVER_VAR
    try:
        fh = pp.open_regular(os.path.expanduser(RECEIVER_FILE))
    except FileNotFoundError:
        return None, None                # absent: the one road that is no receiver
    except OSError:                      # there and not openable: a socket, an unreadable file, a parent that is a file
        return "", RECEIVER_FILE
    if fh is None:
        return "", RECEIVER_FILE
    try:
        with fh:
            raw = fh.read(RECEIVER_FILE_MAX + 1)
    except OSError:
        return "", RECEIVER_FILE
    if len(raw) > RECEIVER_FILE_MAX:
        return "", RECEIVER_FILE
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return "", RECEIVER_FILE
    for line in text.splitlines():
        if line.strip():
            return line.strip(), RECEIVER_FILE
    return None, None


def receiver_url(text):
    """The address split, or None: it must be printable ASCII (spaces around it dropped; urlsplit would silently
    strip a tab or a newline, and http.client cannot encode a character outside ASCII), https (http for 127.0.0.1
    and localhost alone), carry a host of letters, digits, dots and dashes with a numeric port at most, no
    userinfo, no query, no fragment, and a path starting with a slash (the base the route is appended to). None
    says nothing about which rule failed on purpose: the caller's refusal never echoes the value, which may be
    anything the user typed."""
    if not isinstance(text, str) or not ADDRESS.fullmatch(text.strip(" ")):
        return None
    try:
        u = urllib.parse.urlsplit(text.strip(" "))
        u.port
    except ValueError:
        return None
    if u.scheme not in ("https", "http") or not u.hostname or not HOST.match(u.hostname):
        return None
    if u.username is not None or u.password is not None or u.query or u.fragment:
        return None
    if u.scheme == "http" and u.hostname not in LOOPBACK:
        return None
    if u.path and not u.path.startswith("/"):
        return None
    return u


def upload_url(u):
    """<receiver>/v1/upload: the configured base (a trailing slash dropped) and the route."""
    return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path.rstrip("/") + ROUTE, "", ""))


# ── strict JSON ──────────────────────────────────────────────────────────────────────────────────────────
class RepeatedKey(ValueError):
    """An object spells the same key twice: json.loads would keep the last copy and drop the rest, and this reader
    must not silently choose which copy is checked and sent (the receiver's contract refuses a repeated key too). The
    key itself is not carried: it may be anything."""


class NonFinite(ValueError):
    """A number is written past the double's range and parses to an infinity, or would in any double reader: a float
    spelling (1e999, -1e999, 1E400, _finite_float) or, since the closing check of 2026-09-19, an INTEGER literal
    float() cannot hold (_bounded_int: 2**1024 - 2**970 and above, 309 digits or more; json parses it exactly, and
    every double reader, a browser's JSON.parse or the receiver, makes an infinity of it, so to the wire the two
    spellings are the same number). Valid JSON to every editor and validator (RFC 8259 leaves range to the
    implementation), so the verb's refusal names the reason, as it does for a repeated key, or an operator whose hand
    edit produced it is told nothing they can act on (the closing re-run's verification, 2026-09-19). The number
    itself is not carried."""


def _no_constant(name):
    raise ValueError("not strict JSON: " + name)


def _finite_float(text):
    """The float `text` spells, or NonFinite (a ValueError) when it is not finite: json's parser hands every number
    with a fraction or an exponent here, and a number written past the double's range (1e999, -1e999, 1E400) parses to
    an infinity that parse_constant never sees, since no literal spelled it. An underflow (1e-999) is 0.0 and a
    measurement."""
    v = float(text)
    if not math.isfinite(v):
        raise NonFinite("not strict JSON: a number outside the finite range")
    return v


# The digit count of the largest double, 309 (len(str(int(sys.float_info.max)))): an integer literal of more digits is
# past every double, and _bounded_int refuses it by its length BEFORE int() runs, so the outcome is this verb's rule and
# not the interpreter's int() digit limit (4300 by default, sys.get_int_max_str_digits; a 5001-digit literal is that
# limit's ValueError, the bare "is not strict JSON" line, without the pre-check). At 309 digits the count decides nothing:
# 10**308 converts, 2**1024 - 2**970 does not, and float() is asked.
DOUBLE_DIGITS = len(str(int(sys.float_info.max)))


def _bounded_int(text):
    """The int `text` spells, or NonFinite (a ValueError) when no double can hold it: json's scanner hands every
    integer literal here as its TEXT (verified on 3.12: a 5001-digit literal arrives whole, before any int()), so a
    literal over DOUBLE_DIGITS digits, the sign not counted, is refused by its length and never converted, and one
    within it is converted and asked of float(), which raises OverflowError at 2**1024 - 2**970 and above (309 digits;
    int(sys.float_info.max) + 1 and everything below the edge round to the largest double and pass). THE CHOKE POINT of
    the closing check's HIGH 2 (2026-09-19): the checks downstream apply float-domain functions to the parsed value
    (public_uptime and public_bound over a raw file value in pp.denylist_problems, math.isfinite before that day), and
    json hands them unbounded ints; refusing here, with the line the overflowing float already has, means no site on
    this road, present or future, can see one. The threshold is behavioural (does float() hold it), not a digit
    count; the pre-check exists to stay clear of the interpreter's int() limit, so that a 5001-digit literal is this
    verb's one line and not the interpreter's."""
    digits = text[1:] if text.startswith("-") else text
    if len(digits) > DOUBLE_DIGITS:
        raise NonFinite("not strict JSON: a number outside the finite range")
    v = int(text)
    try:
        float(v)
    except OverflowError:
        raise NonFinite("not strict JSON: a number outside the finite range")
    return v


def _no_repeat(pairs):
    if len({k for k, _v in pairs}) != len(pairs):
        raise RepeatedKey("not strict JSON: a key repeats")
    return dict(pairs)


def strict_loads(data):
    """The document `data` (bytes) spells, or a ValueError: UTF-8, no NaN or Infinity whether spelled as a literal
    (parse_constant) or reached by an overflowing number (parse_float, _finite_float: 1e999 parses to inf and is
    refused here as NonFinite, a ValueError, so read_export can name the reason; 1e-999 underflows to 0.0 and is a
    measurement) or by an integer literal no double can hold (parse_int, _bounded_int: 2**1024 - 2**970 and above,
    the same NonFinite, a literal over 309 digits refused by its length before int() runs, so the outcome is this
    verb's line and never the interpreter's int() digit limit), no key repeated within one object at any depth
    (RepeatedKey, a ValueError), and nesting within the parser's reach (json raises RecursionError past it; here that
    is a ValueError like any other unparseable input, never a traceback). The parser's reach is not the verb's depth
    rule: read_export holds the parsed document to MAX_DEPTH, a far smaller number, before any check walks it. Before
    the overflow was refused here, the fold belt (read_export's FOLDED comparison, which nulls a non-finite number and
    so refuses the document as differing from its fold) was the only thing keeping an infinity off the wire, a purpose
    it was not written for and did not know it held (the closing re-run of 2026-09-19), so a later relaxation of the
    belt would have reopened it silently; the refusal now lives with the other strict-JSON rules."""
    try:
        return json.loads(data.decode("utf-8"), parse_constant=_no_constant, parse_float=_finite_float, parse_int=_bounded_int,
                          object_pairs_hook=_no_repeat)
    except RecursionError:
        raise ValueError("not strict JSON: nested past the parser")


def nesting_depth(node):
    """How deep `node` nests: the objects and arrays around its deepest value, the root counting one, so a leaf's depth
    is the number of components in its key path (a fresh export's deepest leaf, perf/jobs/stageRing/#/stages/jobs.autoNudge/
    bytes, sits at 7; an empty object at the root is 1; a scalar alone is 0). An explicit stack and no recursion: this runs
    before the walks so that a document deeper than their frames reach never gets to them, and a measure that shared their
    limit would overflow on the very document it is there to refuse."""
    depth = 0
    stack = [(node, 1)] if isinstance(node, (dict, list, tuple)) else []
    while stack:
        n, d = stack.pop()
        if d > depth:
            depth = d
        for v in (n.values() if isinstance(n, dict) else n):
            if isinstance(v, (dict, list, tuple)):
                stack.append((v, d + 1))
    return depth


# ── the file ─────────────────────────────────────────────────────────────────────────────────────────────

def read_export(path, state):
    """The checked document's bytes, re-serialised by the export's own writer (pe.document_text), once every check
    passes; never the file's raw bytes (the module docstring, WHAT IS SENT IS WHAT WAS CHECKED). The checks: the file
    exists and is a regular file (pp.open_regular: opened O_NONBLOCK and fstat'ed, the one look the verb takes at the
    path, so a fifo there is refused at once and never opened blocking; a stat followed by a blocking open left a window
    in which a fifo appearing between the two hung the verb forever, the fourth review round, 2026-09-19), it is at most
    MAX_BYTES (the size from that fstat; MAX_BYTES + 1 bytes are read as the belt for a file that grew after it), it
    parses as strict JSON (strict_loads: a repeated key is named as the reason, since the file may be one the
    user edited by hand and an editor calls it valid) to an object with the schema line, it nests at most MAX_DEPTH
    levels (nesting_depth), and it passes
    perf_export.check_document (the machine-string scan, the paste-safety walk and the denylist walk, which holds
    the file to the export's own rule, paste-safe, not unlinkable: what the export dropped, folded or coarsened is
    refused and the measurements it keeps pass; the shallowest finding named) as it stands, and then the belt under the
    three checks: the top level is exactly what the export writes (TOP_LEVEL: no key the export does not write, none it
    always writes missing, exported_at and kernel_commit in the export's own spellings) and each folded block, perf and
    usage (FOLDED), is a dict equal to its own fold (pp.fold) at the block root. The checks name a finding by its kind
    and key path; the allowlist turns a top-level key nobody thought about from accepted into refused, and the fold
    comparison catches whatever shape a later fold rule would fold that no check yet names, both at the price of naming
    the top-level key alone. A Refusal
    otherwise, naming the file path the user passed and, for a walk or scan finding, the kind and the key path,
    never the value (a listed private string's also the line of the list its entry is on and the remedy, editing that
    line or the value); for the belt, the top-level key, which the checks passed. The depth rule runs before the checks and
    is this verb's own: the checks and the fold recurse one frame per level, the parser admits documents far deeper than
    their frames reach on some builds, and this is the one road that hands them a file a person named, so a document
    nested deeper than MAX_DEPTH is refused in one line naming the bound and the file's depth (the receiver's depth rule,
    about eight levels, is the receiver's and is not enforced here). A RecursionError out of the checks, the fold or the
    writer is caught behind the bound as a belt, the same one-line refusal naming the error's class, never a traceback;
    with the bound in front no file reaches it."""
    try:
        fh = pp.open_regular(path)
    except FileNotFoundError:
        raise Refusal("refused: %s does not exist; nothing sent" % path, 1)
    except OSError as e:
        raise Refusal("refused: %s cannot be read (%s); nothing sent" % (path, e.__class__.__name__), 1)
    if fh is None:
        raise Refusal("refused: %s is not a regular file; nothing sent" % path, 1)
    try:
        with fh:
            size = os.fstat(fh.fileno()).st_size
            if size > MAX_BYTES:
                raise Refusal("refused: %s is %d bytes and the receiver takes at most %d (1 MiB); nothing sent" % (path, size, MAX_BYTES), 1)
            data = fh.read(MAX_BYTES + 1)
    except OSError as e:
        raise Refusal("refused: %s cannot be read (%s); nothing sent" % (path, e.__class__.__name__), 1)
    if len(data) > MAX_BYTES:    # grew between the fstat and the read
        raise Refusal("refused: %s is %d bytes and the receiver takes at most %d (1 MiB); nothing sent" % (path, len(data), MAX_BYTES), 1)
    try:
        doc = strict_loads(data)
    except RepeatedKey:
        raise Refusal("refused: %s is not strict JSON (a key repeats); nothing sent" % path, 1)
    except NonFinite:            # valid JSON to a hand editor, like the repeated key: the reason is named
        raise Refusal("refused: %s is not strict JSON (a number is outside the finite range); nothing sent" % path, 1)
    except ValueError:           # UnicodeDecodeError and JSONDecodeError are both ValueErrors
        raise Refusal("refused: %s is not strict JSON; nothing sent" % path, 1)
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise Refusal("refused: %s is not a romp perf export (no top-level schema %s); nothing sent" % (path, SCHEMA), 1)
    depth = nesting_depth(doc)
    if depth > MAX_DEPTH:            # the depth bound, before any walk runs (the comment at MAX_DEPTH)
        raise Refusal("refused: %s is nested %d levels deep and this verb takes at most %d; nothing sent" % (path, depth, MAX_DEPTH), 1)
    try:
        reason = pe.check_document(doc, state, tail="nothing sent")
        if reason:
            raise Refusal("refused: " + reason, 1)
        # the belt, after the checks so that a top-level key is safe to print (they passed over it: it fits the identifier
        # grammar whole and spells no machine string). First the allowlist (TOP_LEVEL): a key the export does not write, a
        # key it always writes missing, an envelope line not in the export's own spelling. Then the fold: a fold is a fixed
        # point of its own output (pinned over every fixture and a served export; fold is idempotent even on the summed-floats
        # case pp._merge names, which the denylist walk above refuses first), so a block that differs from its fold was
        # changed after the export in a way the checks above do not name. The belt no longer holds the non-finite case
        # alone: strict_loads refuses an overflowing number (1e999) or an integer a double cannot hold (2**1024 - 2**970 and
        # above, which the fold nulls) first, so a block carrying either never reaches this line
        for k in doc:
            if k not in TOP_LEVEL:
                raise Refusal("refused: %s is not the export's own shape (a top-level %s block the export does not write); nothing sent" % (path, k), 1)
        for k, required in TOP_LEVEL.items():
            if required and k not in doc:
                raise Refusal("refused: %s is not the export's own shape (no top-level %s); nothing sent" % (path, k), 1)
        for k, shape in (("exported_at", EXPORTED_AT), ("kernel_commit", KERNEL_COMMIT)):
            if k in doc and not (isinstance(doc[k], str) and shape.match(doc[k])):
                raise Refusal("refused: %s is not the export's own shape (the %s line is not what the export writes); nothing sent" % (path, k), 1)
        for k in FOLDED:
            if k in doc and not isinstance(doc[k], dict):
                raise Refusal("refused: %s is not the export's own shape (the %s block is not what the export writes); nothing sent" % (path, k), 1)
            if k in doc and pp.fold(doc[k]) != doc[k]:
                raise Refusal("refused: %s is not the export's own public form (the %s block differs from its fold); nothing sent" % (path, k), 1)
        text = pe.document_text(doc)      # the document the checks read, spelled as the export spells it
    except RecursionError:
        # the belt behind the depth bound: the walks, the fold and the writer recurse one frame per level, and MAX_DEPTH
        # keeps every file this verb reads far inside any build's stack, so nothing reaches this line by nesting alone; it
        # stands so that whatever the interpreter's stack looks like, the verb answers with one line and never a traceback.
        # The writer is inside it on purpose: json's encoder recurses one frame per level too, and a raise out of it past a
        # belt that ended at the fold would have been a traceback (the fourth review round, 2026-09-19). Measured at the
        # closing check with the bound lifted, the checks overflow before the writer on every build (the table at MAX_DEPTH),
        # so only a planted raise reaches this line from the writer; the belt holds it all the same
        raise Refusal("refused: %s could not be checked (RecursionError); nothing sent" % path, 1)
    return text.encode("utf-8")


# ── the confirmation ─────────────────────────────────────────────────────────────────────────────────────
def confirmed(yes, stdin=None, stdout=None):
    """True when the send may go: --yes was passed, or stdin is a terminal and the line typed at the prompt is
    y or yes. Off a terminal without --yes, a Refusal (exit 2) that names the flag; a terminal's other answer,
    a Refusal that says nothing was sent. Nothing but the flag and the typed line decide this."""
    if yes:
        return True
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    if stdin is None or not stdin.isatty():
        raise Refusal("refused: not on a terminal, so there is no prompt to answer; pass --yes to send without one "
                      "(the form an agent uses; no setting or variable stands in for it); nothing sent", 2)
    stdout.write("send it? [y/N] ")
    stdout.flush()
    answer = stdin.readline().strip().lower()
    if answer in ("y", "yes"):
        return True
    raise Refusal("nothing sent", 2)


# ── the send ─────────────────────────────────────────────────────────────────────────────────────────────
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A 3xx answer is an error to the caller, refused by its code like any other status, and its Location is
    never read: the parent's http_error_30x parse the target (urlparse raises a ValueError quoting a bracketed
    host, receiver text) before they ask redirect_request, so each is overridden to return None, which leaves
    the status to HTTPDefaultErrorHandler, an HTTPError with the 3xx code and no second request. Standing in
    for the default handler is what keeps build_opener from adding the parent."""

    def _refuse(self, req, fp, code, msg, headers):
        return None

    http_error_301 = http_error_302 = http_error_303 = http_error_307 = http_error_308 = _refuse

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _Deadline:
    """The budget over the whole exchange: TIMEOUT_S from post()'s start, held by a timer. A socket timeout is
    per operation (each read waits up to the limit and a receiver answering in pieces each under it is never late),
    and the header phase runs inside urllib where a caller cannot budget it, so the bound is a timer instead: armed on
    the connection's socket once the connection is up (_DeadlineConnection.connect), it shuts the socket down in both
    directions when the time left runs out, so whatever phase the exchange is in, the send, the status line, the
    headers or the body, the blocked read returns end of stream or the write fails at once, and `fired` says the
    deadline was the cause. The shutdown reaches the socket itself, whichever object holds it (the connection, or the
    response's file after urllib drops the connection's reference), and touches no private attribute; a socket the
    exchange already closed has nothing to shut, and that error is ignored. The timer thread is a daemon, and post()
    cancels it once the exchange ends, so a quick answer leaves nothing running. Preferred over re-arming the socket
    timeout before every read, which reaches two private attributes and cannot see the header phase (round 2,
    2026-09-18)."""

    def __init__(self, seconds):
        self.end = time.monotonic() + seconds
        self.fired = False
        self._timer = None

    def remaining(self):
        return max(0.0, self.end - time.monotonic())

    def arm(self, sock):
        self.cancel()
        timer = threading.Timer(self.remaining(), self._fire, (sock,))
        timer.daemon = True
        self._timer = timer
        timer.start()

    def _fire(self, sock):
        self.fired = True                    # set before the shutdown, so the thread it wakes reads the cause
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def cancel(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None


class _DeadlineConnection:
    """Mixed into the two connection classes: the connection's own timeout is cut to the time the deadline has left
    (it bounds the connect and, for https, the handshake, the phases before a socket exists to arm), and once the
    connection is up the deadline is armed on its socket."""

    def __init__(self, *args, deadline=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._deadline = deadline

    def connect(self):
        if self._deadline is not None and isinstance(self.timeout, (int, float)):
            self.timeout = max(min(self.timeout, self._deadline.remaining()), 0.001)    # a zero would make the socket non-blocking
        super().connect()
        if self._deadline is not None:
            self._deadline.arm(self.sock)


class _DeadlineHTTPConnection(_DeadlineConnection, http.client.HTTPConnection):
    pass


class _DeadlineHTTPSConnection(_DeadlineConnection, http.client.HTTPSConnection):
    pass


class _DeadlineHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, deadline):
        super().__init__()
        self._deadline = deadline

    def http_open(self, req):
        return self.do_open(_DeadlineHTTPConnection, req, deadline=self._deadline)


class _DeadlineHTTPSHandler(urllib.request.HTTPSHandler):
    """The default handler's https_open with the deadline connection in place of http.client's, and NO context
    argument: HTTPSConnection builds urllib's default verified context itself when none is passed, so certificate
    verification is the library's own and this module holds no context object at all (the census in
    tests/test_perf_upload.py forbids one here)."""

    def __init__(self, deadline):
        super().__init__()
        self._deadline = deadline

    def https_open(self, req):
        return self.do_open(_DeadlineHTTPSConnection, req, deadline=self._deadline)


def post(url, data, timeout=None):
    """One POST of `data` to `url`: (status, body) for any HTTP answer (the body read only on 201, capped at
    ANSWER_MAX + 1 so a long one is judged by its length, empty for every other status), or a Refusal naming the
    error's class alone when no answer came or the client raised anything else (the last clause is the belt:
    whatever the class, its message is never printed). `timeout` (TIMEOUT_S) is a DEADLINE over the whole exchange
    (_Deadline): when it fires, the refusal names TimeoutError whatever the client made of the socket that ended
    under it (an OSError, a RemoteDisconnected, an IncompleteRead, a ValueError, a truncated body or headers that
    parsed short), which every clause below and the success path check first. The verb sets its three headers
    itself, Content-Type, Content-Length (the body's own length, so the attribution the docs make is true by
    construction, and a body that is not bytes fails at the call instead of going out chunked) and User-Agent; the
    client adds Host, Accept-Encoding and Connection. The opener has no proxy (ProxyHandler({}) reads no *_proxy
    variable: the address configured is the address dialled), no cookie jar, and refuses redirects; TLS is urllib's
    default context, which verifies the certificate against the system store."""
    timeout = TIMEOUT_S if timeout is None else timeout
    deadline = _Deadline(timeout)
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(data)), "User-Agent": USER_AGENT})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect(),
                                         _DeadlineHTTPHandler(deadline), _DeadlineHTTPSHandler(deadline))

    def name_of(e):
        return "TimeoutError" if deadline.fired else e.__class__.__name__
    try:
        with opener.open(req, timeout=timeout) as r:
            status = r.status
            body = r.read(ANSWER_MAX + 1) if status == 201 else b""
    except urllib.error.HTTPError as e:
        e.close()
        status, body = e.code, b""
    except urllib.error.URLError as e:
        reason = e.reason
        raise Refusal(NO_ANSWER % name_of(reason if isinstance(reason, BaseException) else e), 1)
    except (OSError, http.client.HTTPException) as e:
        raise Refusal(NO_ANSWER % name_of(e), 1)
    except Exception as e:       # a ValueError from a header or URL the client could not handle, say
        raise Refusal(NO_ANSWER % name_of(e), 1)
    finally:
        deadline.cancel()
    if deadline.fired:           # the socket ended under the deadline and the client made a status or a short body of it
        raise Refusal(NO_ANSWER % "TimeoutError", 1)
    return status, body


def receipt(status, body):
    """(receipt, retention_days, av) of the one answer accepted: status 201 and a body of at most ANSWER_MAX bytes
    that is one strict JSON object (strict_loads: a repeated key is not the shape either, a retention_days of 1e999
    is refused by the parser as an overflow before the integer check below would have refused it, and since the
    closing check of 2026-09-19 so is a retention_days no double can hold, 2**1024 - 2**970 and above, NonFinite through
    parse_int and NOT_THE_SHAPE here, where before it a 401-digit one passed the integer check and was printed in the
    success line, 401 digits wide) with exactly the keys receipt (a uuid4 string), retention_days (a non-negative
    integer, not a bool) and av (ok or skipped). Anything else is a Refusal whose text carries the status code and
    nothing of the body."""
    if status != 201:
        raise Refusal("refused: the receiver answered HTTP %d where the 201 receipt was expected; no receipt" % status, 1)
    if len(body) > ANSWER_MAX:
        raise Refusal(NOT_THE_SHAPE, 1)
    try:
        answer = strict_loads(body)
    except ValueError:
        raise Refusal(NOT_THE_SHAPE, 1)
    if not isinstance(answer, dict) or set(answer) != ANSWER_KEYS:
        raise Refusal(NOT_THE_SHAPE, 1)
    rid, days, av = answer["receipt"], answer["retention_days"], answer["av"]
    if not (isinstance(rid, str) and UUID4.match(rid)):
        raise Refusal(NOT_THE_SHAPE, 1)
    if not isinstance(days, int) or isinstance(days, bool) or days < 0:
        raise Refusal(NOT_THE_SHAPE, 1)
    if av not in AV:
        raise Refusal(NOT_THE_SHAPE, 1)
    return rid, days, av


def main(argv=None, stdin=None) -> int:
    ap = argparse.ArgumentParser(prog=PROG, description=__doc__.split("\n\n")[0],
                                 usage="%(prog)s FILE [--yes] [--receiver URL]")
    ap.add_argument("file", metavar="FILE",
                    help="an export written by `romp perf export --public`, checked again as it stands: the public form is "
                         "paste-safe, not unlinkable, so what the export dropped or coarsened (an identifier, a path, free text, "
                         "a float-valued clock stamp, a bound to the byte) is refused and the measurements it keeps pass")
    ap.add_argument("--yes", action="store_true",
                    help="send without the prompt: the form an agent uses; off a terminal the verb refuses without it, "
                         "and no setting or variable stands in for it")
    ap.add_argument("--receiver", metavar="URL",
                    help="the receiver's https address (else %s, else the file %s)" % (RECEIVER_VAR, RECEIVER_FILE))
    a = ap.parse_args(argv)
    try:
        text, source = receiver_setting(a.receiver)
        if text is None:
            raise Refusal("refused: no receiver is set; pass --receiver URL, set %s, or write the address to %s; nothing sent"
                          % (RECEIVER_VAR, RECEIVER_FILE), 2)
        u = receiver_url(text)
        if u is None:
            raise Refusal("refused: the receiver address from %s is not an https URL with a host and no userinfo, query or "
                          "fragment (http is allowed for 127.0.0.1 and localhost only); nothing sent" % source, 2)
        data = read_export(a.file, pe.state_dir())
        url = upload_url(u)
        print("%s (%d bytes) to %s" % (a.file, len(data), url))     # the body's size and the URL dialled, so a path in the setting is seen before the yes
        sys.stdout.flush()
        confirmed(a.yes, stdin=stdin)
        status, body = post(url, data)
        rid, days, _av = receipt(status, body)
    except Refusal as e:
        sys.stderr.write("%s: %s\n" % (PROG, e))
        return e.code
    print("uploaded: receipt %s (kept %d days; delete by sending the receipt to the project)" % (rid, days))
    return 0


if __name__ == "__main__":
    sys.exit(main())
