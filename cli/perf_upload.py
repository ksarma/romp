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
file that is not UTF-8 text among it, is refused without echoing the value, exit 2. The receiver is
unauthenticated: no credential exists for it, and the verb reads no token from anywhere and sends none.

The file must exist, be a regular file of at most 1 MiB, parse as strict JSON (no NaN or Infinity literals, no
key repeated within one object at any depth, since json.loads would keep the last copy while the bytes sent
carry every copy, and nesting within the parser's reach) with the top-level `schema` line `romp-perf-export/1`,
and pass the export's own check again as the file stands, since the user may have edited it: the scan for the
strings only this machine knows, the paste-safety walk and the denylist walk of cli/perf_public.py, through
perf_export.check_document, so a problem is reported by its kind and key path and never by the key or the value. Any
of these refuses with exit 1. The rule the re-check holds the file to is the export's (its third review round,
2026-09-18): the public form is PASTE-SAFE, not unlinkable. It removes identifiers, paths, free text, machine
strings and every absolute clock stamp and coarsens the uptime and the memory-fraction bounds; durations, counts and
per-process measurements stay, so two exports from one kernel remain linkable through them by design. The re-check
refuses what the export would have dropped or coarsened (a `t` put back on a split row, an uptime typed to the
second, a bound typed to the byte, a float inside a clock stamp's epoch window, 1.5e9 to 2.0e9 seconds or 1.5e12 to
2.0e12 milliseconds, under any key but a duration key) and passes what it keeps (an integer is a byte total or a count,
which a long-lived kernel's totals carry into the window within hours; a float outside both windows is a measurement,
the allocator's arena on a long-lived kernel among them; a float inside a window under a duration key, a name carrying
the token `ms` such as `cycle_cpu_ms_sum` or `wallMs`, is a millisecond total, which the kernel's sums carry through
the seconds window in weeks), so a fresh export passes whole.

Before sending, the verb prints the path, the byte size and the URL it will dial (the address as configured
with the route appended, so a path in the setting is seen at the prompt), then asks for a yes on a terminal
(stdin is a tty). Off a terminal it refuses, exit 2, unless `--yes` is passed: that flag is the form
an agent uses, and its presence in the command is the visible record of the confirmation. No configuration
file or environment variable stands in for it, so nothing sends from a cron by default.

The send is ONE POST to <receiver>/v1/upload, the file's bytes as the body, under six headers: the verb sets
`Content-Type: application/json`, `Content-Length` and a fixed `User-Agent: romp-perf-upload/1` (no version
detail, no hostname); the HTTP client adds `Host` (the receiver's own name), `Accept-Encoding: identity` and
`Connection: close`. A 30 s timeout, stdlib urllib through an opener that refuses redirects (a 3xx is an
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
import os
import re
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))   # cli/, whether run through the bin/ symlink or loaded by path
import perf_export as pe  # noqa: E402

PROG = "romp perf upload"
SCHEMA = pe.SCHEMA
RECEIVER_VAR = "ROMP_PERF_RECEIVER"
RECEIVER_FILE = "~/.config/romp/perf-receiver"
RECEIVER_FILE_MAX = 4096             # the setting file is one line of printable ASCII; past this it is not an address (fresh-5)
ROUTE = "/v1/upload"
MAX_BYTES = 1 << 20                  # the receiver's cap on Content-Length and on the bytes it reads
TIMEOUT_S = 30
USER_AGENT = "romp-perf-upload/1"
ANSWER_MAX = 64 * 1024               # a receipt is under 200 bytes; a longer 201 body is not the shape
LOOPBACK = frozenset({"127.0.0.1", "localhost"})
HOST = re.compile(r"^[A-Za-z0-9.-]+$")
ADDRESS = re.compile(r"[\x21-\x7e]+")     # printable ASCII, no space: what http.client can put on the wire, and nothing urlsplit strips (fullmatch: $ would pass a trailing newline)
UUID4 = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
AV = ("ok", "skipped")
ANSWER_KEYS = frozenset({"receipt", "retention_days", "av"})
NOT_THE_SHAPE = "refused: the receiver answered 201 without the receipt shape this verb accepts (receipt, retention_days, av); no receipt"


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
    environment variable, the file's first non-empty line; (None, None) when none is set. An empty variable
    is unset. The file is read under HOME, the way `romp default-dir` reads its own, and read with a bound: at most
    RECEIVER_FILE_MAX + 1 bytes are taken, so a file that is not a setting (a device node, a fifo, a large file put
    there by mistake) costs that much memory and no more, and one over the bound is not truncated to its first line
    but returned as the empty string with the file as its source, the same road a file that is not UTF-8 text takes:
    an address the grammar refuses, so the caller's refusal names the file and nothing of its bytes. A size check
    would not do (stat reports 0 for a device node or a fifo), so the bound is on the read itself."""
    if flag is not None:
        return flag, "--receiver"
    env = os.environ if env is None else env
    value = env.get(RECEIVER_VAR)
    if value:
        return value, RECEIVER_VAR
    try:
        with open(os.path.expanduser(RECEIVER_FILE), "rb") as fh:
            raw = fh.read(RECEIVER_FILE_MAX + 1)
    except OSError:
        return None, None
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
    """An object spells the same key twice: json.loads would keep the last copy and drop the rest, so the
    document checked and the bytes sent would differ. The key itself is not carried: it may be anything."""


def _no_constant(name):
    raise ValueError("not strict JSON: " + name)


def _no_repeat(pairs):
    if len({k for k, _v in pairs}) != len(pairs):
        raise RepeatedKey("not strict JSON: a key repeats")
    return dict(pairs)


def strict_loads(data):
    """The document `data` (bytes) spells, or a ValueError: UTF-8, no NaN or Infinity, no key repeated within
    one object at any depth (RepeatedKey, a ValueError), and nesting within the parser's reach (json raises
    RecursionError past it; here that is a ValueError like any other unparseable input, never a traceback)."""
    try:
        return json.loads(data.decode("utf-8"), parse_constant=_no_constant, object_pairs_hook=_no_repeat)
    except RecursionError:
        raise ValueError("not strict JSON: nested past the parser")


# ── the file ─────────────────────────────────────────────────────────────────────────────────────────────

def read_export(path, state):
    """The file's bytes, once every check passes: it exists and is a regular file, it is at most MAX_BYTES, it
    parses as strict JSON (strict_loads: a repeated key is named as the reason, since the file may be one the
    user edited by hand and an editor calls it valid) to an object with the schema line, and it passes
    perf_export.check_document (the machine-string scan, the paste-safety walk and the denylist walk, which holds
    the file to the export's own rule, paste-safe, not unlinkable: what the export dropped or coarsened is refused
    and the measurements it keeps pass; the shallowest finding named) as it stands. A Refusal
    otherwise, naming the file path the user passed and, for a walk or scan finding, the kind and the key path,
    never the value."""
    p = Path(path)
    try:
        st = p.stat()
    except FileNotFoundError:
        raise Refusal("refused: %s does not exist; nothing sent" % path, 1)
    except OSError as e:
        raise Refusal("refused: %s cannot be read (%s); nothing sent" % (path, e.__class__.__name__), 1)
    if not stat.S_ISREG(st.st_mode):
        raise Refusal("refused: %s is not a regular file; nothing sent" % path, 1)
    if st.st_size > MAX_BYTES:
        raise Refusal("refused: %s is %d bytes and the receiver takes at most %d (1 MiB); nothing sent" % (path, st.st_size, MAX_BYTES), 1)
    try:
        data = p.read_bytes()
    except OSError as e:
        raise Refusal("refused: %s cannot be read (%s); nothing sent" % (path, e.__class__.__name__), 1)
    if len(data) > MAX_BYTES:    # grew between the stat and the read
        raise Refusal("refused: %s is %d bytes and the receiver takes at most %d (1 MiB); nothing sent" % (path, len(data), MAX_BYTES), 1)
    try:
        doc = strict_loads(data)
    except RepeatedKey:
        raise Refusal("refused: %s is not strict JSON (a key repeats); nothing sent" % path, 1)
    except ValueError:           # UnicodeDecodeError and JSONDecodeError are both ValueErrors
        raise Refusal("refused: %s is not strict JSON; nothing sent" % path, 1)
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise Refusal("refused: %s is not a romp perf export (no top-level schema %s); nothing sent" % (path, SCHEMA), 1)
    reason = pe.check_document(doc, state, tail="nothing sent")
    if reason:
        raise Refusal("refused: " + reason, 1)
    return data


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


def post(url, data, timeout=None):
    """One POST of `data` to `url`: (status, body) for any HTTP answer (the body read only on 201, capped at
    ANSWER_MAX + 1 so a long one is judged by its length, empty for every other status), or a Refusal naming the
    error's class alone when no answer came or the client raised anything else (the last clause is the belt:
    whatever the class, its message is never printed). The verb sets its three headers itself, Content-Type,
    Content-Length (the body's own length, so the attribution the docs make is true by construction, and a body that
    is not bytes fails at the call instead of going out chunked) and User-Agent; the client adds Host, Accept-Encoding
    and Connection. The opener has no proxy (ProxyHandler({}) reads no *_proxy variable: the address configured is the
    address dialled), no cookie jar, and refuses redirects; TLS is urllib's default context, which verifies the
    certificate against the system store."""
    timeout = TIMEOUT_S if timeout is None else timeout
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(data)), "User-Agent": USER_AGENT})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as r:
            status = r.status
            body = r.read(ANSWER_MAX + 1) if status == 201 else b""
            return status, body
    except urllib.error.HTTPError as e:
        e.close()
        return e.code, b""
    except urllib.error.URLError as e:
        reason = e.reason
        name = reason.__class__.__name__ if isinstance(reason, BaseException) else e.__class__.__name__
        raise Refusal("refused: no answer from the receiver (%s); no receipt" % name, 1)
    except (OSError, http.client.HTTPException) as e:
        raise Refusal("refused: no answer from the receiver (%s); no receipt" % e.__class__.__name__, 1)
    except Exception as e:       # a ValueError from a header or URL the client could not handle, say
        raise Refusal("refused: no answer from the receiver (%s); no receipt" % e.__class__.__name__, 1)


def receipt(status, body):
    """(receipt, retention_days, av) of the one answer accepted: status 201 and a body of at most ANSWER_MAX bytes
    that is one strict JSON object (strict_loads: a repeated key is not the shape either) with exactly the keys
    receipt (a uuid4 string), retention_days (a non-negative integer, not a bool) and av (ok or skipped).
    Anything else is a Refusal whose text carries the status code and nothing of the body."""
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
                         "a clock stamp, a bound to the byte) is refused and the measurements it keeps pass")
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
        print("%s (%d bytes) to %s" % (a.file, len(data), url))     # the URL dialled, so a path in the setting is seen before the yes
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
