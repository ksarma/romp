#!/usr/bin/env python3
"""`romp perf upload FILE [--yes] [--receiver URL]` (cli/perf_upload.py, bin/romp-perf-upload), 2026-09-18: the
export's companion, which sends one paste-safe export to the receiver the operator configured and nothing else.

What is pinned here, each by execution against the verb's own file run as a child (bin/romp-perf-upload under
a pinned hostname) or, for the request itself, through bin/romp: the receiver address comes from --receiver,
else ROMP_PERF_RECEIVER, else ~/.config/romp/perf-receiver (a regular file: a fifo there is refused at once as an
address the grammar refuses, where an open of it once hung the verb, and so is a path that is there but cannot be opened,
a socket or an unreadable file, never reported as no receiver set; only an absent or blank file is), and with none set the verb
refuses naming all three; the address must be https with a host and no userinfo, query or fragment (http for 127.0.0.1 and
localhost alone), and a refused address is never echoed; the file must exist, be at most 1 MiB, parse as strict
JSON (no NaN or Infinity, spelled as a literal or reached by a number written past the double's range, 1e999, which the
parser refuses since the closing re-run of 2026-09-19, where before it the fold belt alone kept the infinity off the wire;
no repeated key at any depth; a RecursionError out of the parser is the strict-JSON refusal,
pinned by mocking json.loads) nested at most MAX_DEPTH levels (32, about four times a fresh export's 7; a deeper file is
refused in one line naming the bound before any check walks it, check_document stubbed and never called; a 100,000-level
file meets whichever of the parser and the bound its build reaches first, and that case asserts the properties owed, exit
1, one of the two fixed lines, no traceback, nothing printed, nothing sent, never which line, since that is the
interpreter's stack and not the verb's) to an object with the schema
line and pass the export's own scan, walk and denylist walk as it stands (what the export dropped, folded or coarsened is
refused: a key it drops, a string value or a key the fold would have written as `other`, a key ending in a newline among
them, an uptime off whole minutes, a bound off a power of two, a float inside a clock stamp's epoch window, seconds or
milliseconds, under any key but a duration key; an integer, a float outside both windows and a float under a duration key
are measurements and pass, so an export from a long-lived kernel is sent whole; and, as a belt under the three, the top
level must be exactly what the export writes, schema, exported_at and perf with kernel_commit and usage optional and no
other key, each envelope line in the export's own spelling, and the perf and usage blocks must equal their own folds,
FoldBelt), an
edited file refused by kind and key path and never by value; the line before the prompt names the URL the verb will dial, a path in the address included; the send needs a yes on a terminal or --yes, off a terminal
without the flag it refuses before dialling, and no environment variable stands in for the flag (an AST census
of the module's environment reads, plus an executed check with tempting names set); TLS is urllib's default verified
context, pinned by an AST census over the module (no ssl import, no context keyword, no loosening attribute) and by
execution (the connection the handshake used is recorded and its context's verify_mode and check_hostname read); the one
answer accepted is
201 with exactly {receipt: uuid4, retention_days: int, av: ok|skipped} in a body of at most 64 KiB, every other status
(a redirect among them, never followed, its Location never parsed), body or error refused with a fixed line carrying
the status code or the error class and nothing of the body or of any exception's message; the thirty seconds are a
deadline over the whole exchange, so a receiver answering in pieces each under the limit is cut at the total (a
raw-socket drip receiver pins it) and the connection's own timeout is cut to the time the deadline has left (a unit pin);
and an enumeration of the request a recording receiver saw: the request line, every header
and the body bytes, which are the checked document written out by the export's own writer (perf_export.document_text),
so they equal the file's for a file as the export wrote it and, for a file edited since, carry the parsed document's
canonical spelling and never the file's own (WHAT IS SENT IS WHAT WAS CHECKED, the fourth review round, 2026-09-19).

Nothing here reads a live kernel, a real state directory or a real setting: the child's HOME is synthetic or a
temp directory under the test's own tree, USER and LOGNAME are `tester`, socket.gethostname is pinned to
TESTHOST.example in the child, every id is a placeholder, and the only receiver any case dials is a handler this
module starts on 127.0.0.1 (or a loopback port nothing listens on). No request leaves the machine."""
import ast
import collections.abc
import contextlib
import io
import json
import os
import re
import shutil
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
UPLOAD = os.path.join(BIN, "romp-perf-upload")
EXPORT = os.path.join(BIN, "romp-perf-export")
ROMP = os.path.join(BIN, "romp")

# Hermetic state BEFORE the load: the verb's module chain resolves its state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run would otherwise touch REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
pu = load_source("romp_perf_upload", UPLOAD)
pp = pu.pe.pp

SID = "11111111-2222-3333-4444-555555555555"
HOME = "/home/tester"                                       # a synthetic home; never this machine's
TERM = "Quarterly Roadmap"
APP = "<b>%s</b> %s" % (SID, HOME)
HOSTNAME = "TESTHOST.example"                                # the child's hostname; never this machine's
PLANTED = (SID, SID[:8], HOME, "tester", "TESTHOST", TERM, APP, "-home-tester-code-notes-api")
MARKER = "RECEIVER-BODY-MARKER-4242"                         # planted in every answer body that must not be echoed
RECEIPT = "3f2a9c1e-7b4d-4e6a-9c1f-2d3e4f5a6b7c"           # version nibble 4, variant nibble 9
SUCCESS = "uploaded: receipt %s (kept %d days; delete by sending the receipt to the project)\n"
CHILD = ("import runpy, socket, sys; socket.gethostname = lambda: %r; sys.argv = sys.argv[1:]; "
         "runpy.run_path(sys.argv[0], run_name='__main__')" % HOSTNAME)


def planted_snapshot():
    """A GET /perf snapshot in an old kernel's shape carrying the five plants the enumeration names (a home path,
    a session id, a hostname, a glossary term, a client's app string) in every place the export must fold or drop
    them, plus counters so the export is not empty."""
    return {
        "now": 1000.5, "since": 900.0, "uptime_s": 100.5, "log": True,
        "process": {"rss_kb": 409600, "threads": 40, "cpu_s": 60.0, "pid": 4242, "cwd": HOME},
        "pusher": {"cycles": 100, "cycle_ms_p50": 180.0,
                   "connectPush": {"count": 3, "byApp": {"chat": {"count": 1}, APP: {"count": 2}}}},
        "stages_ms": {"jobs": 5000.0, "push.chat": 15000.0, HOME + "/notes": 2.0},
        "builds": {"chat": {"cached": 80, "built": 20, "ms": 800.0, "bySession": [{"sid": SID, "n": 3, "max": 12.0}]}},
        "http": {"GET /perf": {"count": 5, "ms": 2.5}, "POST /send": {"count": 7, "ms": 7.0},
                 "GET /glossary/" + TERM: {"count": 1, "ms": 1.0}, "GET /remote/TESTHOST/sessions": {"count": 1, "ms": 1.0},
                 "GET " + HOME: {"count": 3, "ms": 1.0}},
        "parses": {"kernel": 12, "hits": 30, "bySid": {SID: 3}},
        "checkpoints": {"restored": 2, "readByPath": {HOME + "/.claude/projects/-home-tester-code-notes-api/%s.jsonl" % SID: 4096}},
        "heap": {"tracing": False, "host": "TESTHOST up"},
    }


def _env(state, home=HOME, extra=None):
    """A child's environment: the suite's minus every ROMP_* variable and the session id, a private state root, a
    synthetic HOME (so ~/.config/romp/perf-receiver resolves nowhere unless a case writes one under a temp HOME),
    USER and LOGNAME `tester`, no live kernel port."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("ROMP_") and k not in ("CLAUDE_CODE_SESSION_ID", "XDG_CONFIG_HOME")}
    env.update({"XDG_STATE_HOME": os.path.dirname(state), "HOME": home, "USER": "tester", "LOGNAME": "tester", "ROMP_KERNEL_PORT": "1"})
    # no XDG_CONFIG_HOME: the child resolves the private-strings list and the setting file under HOME, never this machine's
    env.update(extra or {})
    return env


def _run(args, state, home=HOME, extra=None, stdin=subprocess.DEVNULL, address_space=None):
    """bin/romp-perf-upload as a child under the pinned hostname (CHILD), stdin /dev/null (not a terminal) unless given.
    `address_space`, in bytes, caps the child's virtual address space (RLIMIT_AS) for a refusable input that could allocate
    without bound, set by the CHILD ITSELF in its prelude before the verb's code runs and never through preexec_fn: this
    parent runs the loopback Receiver's server thread, a fork hook in a threaded parent is the documented deadlock hazard,
    and the cap lands on the same process either way (the export module's _run takes the same shape)."""
    child = CHILD if address_space is None else "import resource; resource.setrlimit(resource.RLIMIT_AS, (%d, %d)); " % (address_space, address_space) + CHILD
    return subprocess.run([sys.executable, "-c", child, UPLOAD] + list(args), capture_output=True, text=True, timeout=60,
                          env=_env(state, home, extra), stdin=stdin)


def _run_tty(args, state, answer, home=HOME, extra=None):
    """The child with a pseudo-terminal on stdin and `answer` typed at it; stdout and stderr are pipes."""
    master, slave = os.openpty()
    try:
        p = subprocess.Popen([sys.executable, "-c", CHILD, UPLOAD] + list(args), stdin=slave, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, env=_env(state, home, extra))
        os.close(slave)
        slave = None
        os.write(master, answer.encode("utf-8"))
        out, err = p.communicate(timeout=60)
    finally:
        if slave is not None:
            os.close(slave)
        os.close(master)
    return subprocess.CompletedProcess(p.args, p.returncode, out, err)


def _state_root():
    """A state root the child resolves as <XDG>/romp, session hosts off; returns (xdg, state)."""
    xdg = tempfile.mkdtemp()
    state = os.path.join(xdg, "romp")
    os.makedirs(state)
    with open(os.path.join(state, "session-hosts"), "w") as fh:
        fh.write("off\n")
    return xdg, state


def _export(xdg, state, usage=False, commit=None, snap=None, name="export.json"):
    """An export the export verb wrote from the planted snapshot (or `snap`), under the same synthetic machine strings
    the upload child will scan with; returns its path (<xdg>/<name>). `usage` passes --usage; `commit` puts a kernel_sha
    on the snapshot, which the export lifts into the envelope as kernel_commit."""
    src = os.path.join(xdg, "snap.json")
    out = os.path.join(xdg, name)
    snap = planted_snapshot() if snap is None else snap
    if commit:
        snap["kernel_sha"] = commit
    with open(src, "w") as fh:
        json.dump(snap, fh)
    r = subprocess.run([sys.executable, "-c", CHILD, EXPORT, "--public", "--from", src, "--out", out] + (["--usage"] if usage else []),
                       capture_output=True, text=True, timeout=60, env=_env(state))
    assert r.returncode == 0, r.stderr
    return out


def _nested(depth):
    """An export-shaped document text whose nesting is exactly `depth` by the verb's count (nesting_depth: the root is 1,
    `perf` 2, and each `{"a": ` one more): the envelope the belt requires (the schema line and an exported_at minute), an
    uptime on the grain, and a chain of single-key objects under perf/x ending in the number 1, so every check passes and
    the depth alone decides the outcome."""
    n = depth - 2
    return ('{"schema": "romp-perf-export/1", "exported_at": "2026-09-18T12:00Z", "perf": {"uptime_s": 60, "x": '
            + '{"a": ' * n + "1" + "}" * n + "}}")


def _keys_named(doc, name):
    """The key paths (`a/b/0`) of every dict holding a key named `name`, at any depth of `doc`; empty when none does."""
    out = []

    def walk(node, where):
        if isinstance(node, dict):
            if name in node:
                out.append("/".join(str(p) for p in where))
            for k, v in node.items():
                walk(v, where + (k,))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, where + (i,))
    walk(doc, ())
    return out


def _wire(doc):
    """The bytes the verb sends for a document it accepts: the export's own writer over the parsed document
    (perf_export.document_text), which is the file's bytes when the file is as the export wrote it and the canonical
    spelling of the parse otherwise (a compact json.dump differs from it in whitespace alone)."""
    return pu.pe.document_text(doc).encode("utf-8")


class _RecordingEnv(collections.abc.MutableMapping):
    """A stand-in for os.environ that records every read (a membership test, an item, get, keys, items, iteration,
    len) in `touched` and holds nothing: what the consent decision must never consult, whatever the syntax."""

    def __init__(self, touched):
        self._d = {}
        self.touched = touched

    def __getitem__(self, k):
        self.touched.append(("getitem", k))
        return self._d[k]

    def __setitem__(self, k, v):
        self._d[k] = v

    def __delitem__(self, k):
        del self._d[k]

    def __iter__(self):
        self.touched.append(("iter", None))
        return iter(self._d)

    def __len__(self):
        self.touched.append(("len", None))
        return len(self._d)

    def __contains__(self, k):
        self.touched.append(("in", k))
        return k in self._d

    def get(self, k, default=None):
        self.touched.append(("get", k))
        return self._d.get(k, default)

    def keys(self):
        self.touched.append(("keys", None))
        return self._d.keys()

    def items(self):
        self.touched.append(("items", None))
        return self._d.items()


def _free_port():
    """A loopback port nothing listens on (bound and released; the kernel does not hand it out again at once)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Receiver:
    """A recording fake on 127.0.0.1: every request's line, headers and body are kept; the answer is whatever
    the test set (status, extra headers, body), a delay before it, or a close with no answer."""

    def __init__(self):
        self.requests = []
        self.answer = (201, {}, json.dumps({"receipt": RECEIPT, "retention_days": 180, "av": "ok"}))
        self.delay = 0.0
        self.hang_up = False
        fake = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(n)
                fake.requests.append((self.requestline, list(self.headers.items()), body))
                if fake.delay:
                    time.sleep(fake.delay)
                if fake.hang_up:
                    self.close_connection = True
                    return
                status, extra, text = fake.answer
                data = text.encode("utf-8")
                self.send_response(status)
                for k, v in extra.items():
                    self.send_header(k, v)
                self.send_header("Content-Type", "application/json" if text.startswith(("{", "[")) else "text/html")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST

            def log_message(self, *a):
                pass
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.srv.server_address[1]
        self.url = "http://127.0.0.1:%d" % self.port
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def reset(self):
        self.requests.clear()
        self.answer = (201, {}, json.dumps({"receipt": RECEIPT, "retention_days": 180, "av": "ok"}))
        self.delay = 0.0
        self.hang_up = False

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()


class DripReceiver:
    """A raw-socket receiver on 127.0.0.1 for one POST: it reads the request head to the blank line and Content-Length
    bytes of body, then writes its answer in `pieces`, sleeping `gap` seconds before each, so the answer arrives slowly by
    parts with every gap under a per-operation timeout and the whole over it: the shape a socket timeout cannot see and a
    deadline over the exchange must."""

    def __init__(self, pieces, gap):
        self.pieces, self.gap = pieces, gap
        self.requests = []
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(1)
        self.port = self.srv.getsockname()[1]
        self.url = "http://127.0.0.1:%d" % self.port
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        try:
            conn, _peer = self.srv.accept()
        except OSError:
            return
        try:
            conn.settimeout(10)
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = conn.recv(65536)
                if not chunk:
                    return
                head += chunk
            head, _sep, body = head.partition(b"\r\n\r\n")
            n = int(re.search(rb"(?i)content-length:\s*(\d+)", head).group(1))
            while len(body) < n:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                body += chunk
            self.requests.append((head, body))
            for piece in self.pieces:
                time.sleep(self.gap)
                conn.sendall(piece)
            time.sleep(0.2)                 # let the client read the tail before the close
        except OSError:
            pass                            # the client shut the socket down: the deadline fired
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def stop(self):
        self.srv.close()
        self.thread.join(5)


class ReceiverSetting(unittest.TestCase):
    """receiver_setting: the flag, then the variable, then the file's first non-empty line; none is (None, None)."""

    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)

    def _file(self, text):
        d = os.path.join(self.home, ".config", "romp")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "perf-receiver"), "w") as fh:
            fh.write(text)

    def test_the_order_is_flag_variable_file(self):
        with mock.patch.dict(os.environ, {"HOME": self.home}):
            self.assertEqual(pu.receiver_setting(None, env={}), (None, None))
            self._file("\n  \nhttps://file.example/\nhttps://second.example/\n")
            self.assertEqual(pu.receiver_setting(None, env={}), ("https://file.example/", "~/.config/romp/perf-receiver"))
            self.assertEqual(pu.receiver_setting(None, env={"ROMP_PERF_RECEIVER": "https://env.example"}), ("https://env.example", "ROMP_PERF_RECEIVER"))
            self.assertEqual(pu.receiver_setting(None, env={"ROMP_PERF_RECEIVER": ""}), ("https://file.example/", "~/.config/romp/perf-receiver"),
                             "an empty variable is unset")
            self.assertEqual(pu.receiver_setting("https://flag.example", env={"ROMP_PERF_RECEIVER": "https://env.example"}),
                             ("https://flag.example", "--receiver"))
            self._file("   \n\n")
            self.assertEqual(pu.receiver_setting(None, env={}), (None, None), "a blank file is unset")

    def test_a_file_that_is_not_utf8_text_is_an_address_the_grammar_refuses_with_the_file_as_its_source(self):
        d = os.path.join(self.home, ".config", "romp")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "perf-receiver"), "wb") as fh:
            fh.write(b"https://receiver.example/\xff\xfe\n")
        with mock.patch.dict(os.environ, {"HOME": self.home}):
            text, source = pu.receiver_setting(None, env={})
        self.assertEqual(source, "~/.config/romp/perf-receiver", "the file is named as the source, so the refusal points at it")
        self.assertIsNone(pu.receiver_url(text), "and what it holds is refused as an address, never decoded by halves")
        self.assertNotIn("receiver.example", text or "")


    def test_a_setting_file_over_the_bound_is_an_address_the_grammar_refuses_naming_the_file_and_never_its_bytes(self):
        """The setting file is read with a bound (RECEIVER_FILE_MAX + 1 bytes), never whole: a large REGULAR file put there
        by mistake costs that much memory and no more, and one over the bound is not truncated to its first line (which
        would send to whatever address that line spelled) but returned as the empty string with the file as its source,
        the non-UTF-8 road, so the caller refuses naming the file and nothing of its bytes. A stat would not do for the
        bound: it reports 0 for a device node or a fifo, so the bound is on the read. A fifo or a device node never reaches
        the read: pp.open_regular refuses anything that is not a regular file before it, on the fstat (the fifo case below
        pins that road; a device node this process can open takes the same S_ISREG branch; a socket, whose open is ENXIO
        whatever its mode, and a block device the account cannot open fail at the open itself and take receiver_setting's
        OSError road instead, which since the fourth review round reaches the same result, the file named, pinned by the
        socket and block-device cases below). Fails before: the address on the first line was returned."""
        self.assertEqual(pu.RECEIVER_FILE_MAX, 4096)
        first = "https://r.example\n"
        self._file(first + "x" * (pu.RECEIVER_FILE_MAX + 1 - len(first)))          # one byte over the bound, the address first
        with mock.patch.dict(os.environ, {"HOME": self.home}):
            text, source = pu.receiver_setting(None, env={})
        self.assertEqual((text, source), ("", "~/.config/romp/perf-receiver"), "over the bound: refused as an address, the file named")
        self.assertIsNone(pu.receiver_url(text))
        self._file(first + "x" * (pu.RECEIVER_FILE_MAX - len(first)))              # exactly the bound: read, and the first line is the address
        with mock.patch.dict(os.environ, {"HOME": self.home}):
            self.assertEqual(pu.receiver_setting(None, env={}), ("https://r.example", "~/.config/romp/perf-receiver"))

    def test_a_fifo_at_the_setting_path_is_refused_at_once_naming_the_file_and_nothing_of_it_is_read(self):
        """The setting file must be a REGULAR file (pp.open_regular: opened O_NONBLOCK, fstat'ed, S_ISREG required). A fifo at
        ~/.config/romp/perf-receiver hung the verb indefinitely: a plain open of a fifo blocks until a writer arrives, before
        any read the bound on the read could cover, so the bound the comment credited for the case never ran (the upload's
        second review round, 2026-09-18). Now the fifo is an address the grammar refuses with the file as its source, the
        refusal names the file, and the child exits 2 at once. THE CHILD IS RUN UNDER A TIMEOUT AND HARD-KILLED WHEN IT
        EXPIRES, AND IT RUNS BEFORE THE UNIT CALL: the defect is a hang, so a plain wait, or the unit call first, would take
        the runner with it; subprocess.run kills the child on TimeoutExpired and the case fails instead. Do not simplify
        this back into _run's sixty-second wait or move the unit call above the child."""
        d = os.path.join(self.home, ".config", "romp")
        os.makedirs(d, exist_ok=True)
        os.mkfifo(os.path.join(d, "perf-receiver"))
        xdg, state = _state_root()
        self.addCleanup(shutil.rmtree, xdg, True)
        try:
            r = subprocess.run([sys.executable, "-c", CHILD, UPLOAD, os.path.join(xdg, "no-such.json"), "--yes"], capture_output=True,
                               text=True, timeout=8, env=_env(state, self.home), stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            self.fail("the upload child hung on the fifo at the setting path (killed after 8 s)")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "romp perf upload: refused: the receiver address from ~/.config/romp/perf-receiver is not an https URL with a "
                                   "host and no userinfo, query or fragment (http is allowed for 127.0.0.1 and localhost only); nothing sent\n")
        self.assertEqual(r.stdout, "")
        with mock.patch.dict(os.environ, {"HOME": self.home}):           # the unit, after the child proved the open returns
            self.assertEqual(pu.receiver_setting(None, env={}), ("", "~/.config/romp/perf-receiver"),
                             "a fifo is refused as an address, the file named as its source, and nothing of it is read")


    def test_the_setting_file_is_read_to_the_bound_plus_one_byte_and_never_whole(self):
        """The read bound on the setting file, pinned where it is decided (tests-2, the third review round: replacing
        read(RECEIVER_FILE_MAX + 1) with read() left every case green, since every case asserted post-read behaviour, which
        is the same whether the bound or the whole file was read). pp.open_regular is replaced by a recording file whose
        payload is far past the bound; the one read asked for is RECEIVER_FILE_MAX + 1 bytes, and the outcome is the
        over-the-bound refusal, the file named and the address on its first line never returned. The mutant reads the
        whole payload and records -1 here."""
        asked = []

        class Recording:
            payload = b"https://r.example\n" + b"x" * (pu.RECEIVER_FILE_MAX * 8)

            def read(self, n=-1):
                asked.append(n)
                return self.payload if n is None or n < 0 else self.payload[:n]

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        with mock.patch.object(pu.pp, "open_regular", return_value=Recording()), mock.patch.dict(os.environ, {"HOME": self.home}):
            self.assertEqual(pu.receiver_setting(None, env={}), ("", "~/.config/romp/perf-receiver"), "over the bound: the file named, the address never returned")
        self.assertEqual(asked, [pu.RECEIVER_FILE_MAX + 1], "one bounded read, never an unbounded one")

    def test_a_socket_a_block_device_and_an_unreadable_file_at_the_setting_path_are_refused_naming_the_file_never_as_no_receiver(self):
        """receiver_setting swallowed every OSError from the open into (None, None), so a path that EXISTED but could not be
        opened (a unix socket, ENXIO whatever its mode; a regular file the account cannot read, EACCES; a block device outside
        the account's group, EACCES) had the verb report that no receiver was set and name the three settings, for a file
        that held a real address (correctness-2 and tests-3, the third review round). The open's failure is now split on
        errno: absent (FileNotFoundError, a missing path or a dangling link) is still no receiver, and any other OSError is
        an address the grammar refuses with the file as its source, the result a fifo or a device node reaches through the
        fstat, so the refusal names the file and never its bytes. Each case as a unit and as a hard-killed child (the setting
        path is user-named, where a hang was once possible). The block-device case links the setting path to a device the
        machine has and skips where it has none; whichever of the open (EACCES) and the fstat (S_ISBLK) finds it, the result
        is the same. The mode-000 case skips under root, which reads the file anyway. Fails before: the socket and the
        unreadable file returned (None, None) and the child printed that no receiver was set."""
        d = os.path.join(self.home, ".config", "romp")
        os.makedirs(d)
        setting = os.path.join(d, "perf-receiver")
        xdg, state = _state_root()
        self.addCleanup(shutil.rmtree, xdg, True)
        named = ("", "~/.config/romp/perf-receiver")
        refusal = ("romp perf upload: refused: the receiver address from ~/.config/romp/perf-receiver is not an https URL with a host and no "
                   "userinfo, query or fragment (http is allowed for 127.0.0.1 and localhost only); nothing sent\n")

        def unit():
            with mock.patch.dict(os.environ, {"HOME": self.home}):
                return pu.receiver_setting(None, env={})

        def child(what):
            try:
                r = subprocess.run([sys.executable, "-c", CHILD, UPLOAD, os.path.join(xdg, "no-such.json"), "--yes"], capture_output=True,
                                   text=True, timeout=8, env=_env(state, self.home), stdin=subprocess.DEVNULL)
            except subprocess.TimeoutExpired:
                self.fail("the upload child hung on %s at the setting path (killed after 8 s)" % what)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (2, "", refusal), what)
            self.assertNotIn("no receiver is set", r.stderr, what)
            return r

        sock = socket.socket(socket.AF_UNIX)
        self.addCleanup(sock.close)
        try:
            sock.bind(setting)
        except OSError:                                   # the path is too long for a socket address: bind short and link to it
            # The short dir goes under the system temp dir the tests package recorded (ROMP_TESTS_SYSTEM_TMPDIR), outside
            # the run's private root, so the AF_UNIX path fits sun_path under xdist nesting; a literal system path here
            # would bypass the redirect, which tests/test_tempdir_hygiene.py refuses. Outside the root is outside the
            # exit sweep's scope, so the dir is removed here, when its test is (the shape is tests/test_host_transport.py's
            # two socket dirs, TransportOverSocket._path and BackendHostRules._be).
            short = tempfile.mkdtemp(dir=os.environ.get("ROMP_TESTS_SYSTEM_TMPDIR") or None)
            self.addCleanup(shutil.rmtree, short, ignore_errors=True)
            sock.bind(os.path.join(short, "s"))
            os.symlink(os.path.join(short, "s"), setting)
        self.assertEqual(unit(), named, "a socket: the open itself fails (ENXIO) and the file is named")
        child("a socket")
        os.unlink(setting)
        if os.geteuid() != 0:
            with open(setting, "w") as fh:
                fh.write("https://receiver.example/\n")
            os.chmod(setting, 0)
            self.assertEqual(unit(), named, "a file the account cannot read: present and not an address, the file named")
            r = child("an unreadable file")
            self.assertNotIn("receiver.example", r.stdout + r.stderr, "and nothing of what it holds")
            os.chmod(setting, 0o600)
            os.unlink(setting)
        devices = [p for p in ("/dev/loop0", "/dev/sda", "/dev/nvme0n1", "/dev/vda", "/dev/xvda")
                   if os.path.exists(p) and stat.S_ISBLK(os.stat(p).st_mode)]
        if devices:
            os.symlink(devices[0], setting)
            self.assertEqual(unit(), named, "a block device: by the open (EACCES) or by the fstat (S_ISBLK), the file named either way")
            child("a block device")
            os.unlink(setting)
        os.symlink(os.path.join(self.home, "nowhere"), setting)
        self.assertEqual(unit(), (None, None), "a dangling link is absent: no receiver, like a blank file, and never the refusal")


class ReceiverAddress(unittest.TestCase):
    """receiver_url and upload_url: the address grammar and the route appended to it."""

    def test_accepted_addresses(self):
        for text, target in (("https://r.example", "https://r.example/v1/upload"),
                             ("https://r.example/", "https://r.example/v1/upload"),
                             ("https://r.example:8443/base/", "https://r.example:8443/base/v1/upload"),
                             ("  https://receiver-abc123-uc.a.b.example  ", "https://receiver-abc123-uc.a.b.example/v1/upload"),
                             ("http://127.0.0.1:8080", "http://127.0.0.1:8080/v1/upload"),
                             ("https://r.example/base%20one/", "https://r.example/base%20one/v1/upload"),
                             ("http://localhost:1/", "http://localhost:1/v1/upload")):
            u = pu.receiver_url(text)
            self.assertIsNotNone(u, text)
            self.assertEqual(pu.upload_url(u), target)

    def test_refused_addresses(self):
        for text in ("http://r.example", "http://r.example.localhost", "http://127.0.0.2/", "https://user@r.example", "https://user:pw@r.example",
                     "https://r.example/?x=1", "https://r.example/#frag", "https://", "https:///v1", "ftp://r.example", "r.example",
                     "https://r.example:abc", "https://ex ample.com", "https://r.example/a b", "https://[::1]/",
                     "https://r.example/\u00e9", "https://r.example/caf\u00e9/", "https://r.example/a\u00a0b", "https://r.example/\x7f",
                     "https://r.\u00e9xample/", "https://r.example/\u200b", "https://r.example/\n",
                     "", "   ", "https://r.exa\tmple", None, 42):
            self.assertIsNone(pu.receiver_url(text), repr(text))


class Cli(unittest.TestCase):
    """The verb as a child over an export the export verb wrote: the settings, the address refusals, the file
    checks, the confirmation and the success line; the fake receiver records what, if anything, was dialled."""

    @classmethod
    def setUpClass(cls):
        cls.fake = Receiver()

    @classmethod
    def tearDownClass(cls):
        cls.fake.stop()

    def setUp(self):
        self.fake.reset()
        self.xdg, self.state = _state_root()
        self.addCleanup(shutil.rmtree, self.xdg, True)
        self.file = _export(self.xdg, self.state)
        with open(self.file, "rb") as fh:
            self.data = fh.read()
        self.home = os.path.join(self.xdg, "home")      # a real, empty HOME for the cases that write the setting file
        os.makedirs(self.home)

    def _refused(self, r, code, *phrases):
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)
        self.assertTrue(r.stderr.startswith("romp perf upload: "), r.stderr)
        for phrase in phrases:
            self.assertIn(phrase, r.stderr)
        return r

    def test_with_no_receiver_set_the_verb_refuses_naming_the_three_settings_before_it_reads_the_file(self):
        r = self._refused(_run([os.path.join(self.xdg, "no-such.json"), "--yes"], self.state), 2, "refused: no receiver is set",
                          "--receiver URL", "ROMP_PERF_RECEIVER", "~/.config/romp/perf-receiver", "nothing sent")
        self.assertEqual(r.stdout, "")
        self.assertNotIn("does not exist", r.stderr)
        self.assertEqual(self.fake.requests, [])

    def test_the_guide_says_no_receiver_ships_and_the_code_carries_none(self):
        """docs/guide.md says the upload is something the user runs, what it sends, and that the receiver is one the user
        configures, none shipping, so nothing can be sent until one is set (fresh-2, 2026-09-18; the guide ranks the upload
        against nothing else: its receiver sentence is pinned present, and since the closing check at the re-run's head the
        ranking phrases the second round's sentence carried, "the one exception" to the guide's local-only clause and "the
        only other traffic", are pinned ABSENT from the guide and from the reference's upload section, since a rewrite that
        restored them stayed green before). The
        sentence is pinned flattened, so a rewrap survives, and cross-checked against the code by execution and by text:
        with no flag, no variable and an empty HOME the setting resolves to nothing (the verb then refuses naming the three
        settings, the case above), and no string constant in the module, docstrings included, spells a URL, so no default
        address can be hiding in the text."""
        with open(os.path.join(ROOT, "docs", "guide.md"), encoding="utf-8") as fh:
            guide = " ".join(fh.read().split())
        self.assertIn("to a receiver you configure yourself (none ships, so nothing can be sent until you set one), "
                      "and only after you confirm it", guide)
        with open(os.path.join(ROOT, "docs", "reference.md"), encoding="utf-8") as fh:
            reference = " ".join(fh.read().split())
        section = reference[reference.index("`romp perf upload <file>` sends one such export"):
                            reference.index("An operator writing a receiver implements this contract")]   # the reference uses
        for words in ("the one exception", "the only other traffic"):     # "the one exception" of an unrelated leaf elsewhere
            self.assertFalse(words in guide, "the guide ranks the upload against other traffic again: %r" % words)         # by boolean:
            self.assertFalse(words in section, "the reference's upload section ranks the upload against other traffic: %r" % words)   # never the page
        with mock.patch.dict(os.environ, {"HOME": self.home}):
            self.assertEqual(pu.receiver_setting(None, env={}), (None, None), "nothing configured resolves to no receiver")
        with open(os.path.join(ROOT, "cli", "perf_upload.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        urls = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and re.search(r"https?://", n.value)]
        self.assertEqual(urls, [], "no URL in any string constant of the module")

    def test_the_three_settings_in_order_flag_variable_file(self):
        dead = "http://127.0.0.1:%d" % _free_port()
        os.makedirs(os.path.join(self.home, ".config", "romp"))
        with open(os.path.join(self.home, ".config", "romp", "perf-receiver"), "w") as fh:
            fh.write(self.fake.url + "\n")
        r = _run([self.file, "--yes"], self.state, home=self.home)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (self.file, len(self.data), self.fake.url) + SUCCESS % (RECEIPT, 180))
        self.assertEqual(len(self.fake.requests), 1, "the file supplied the address")
        with open(os.path.join(self.home, ".config", "romp", "perf-receiver"), "w") as fh:
            fh.write(dead + "\n")
        r = _run([self.file, "--yes"], self.state, home=self.home, extra={"ROMP_PERF_RECEIVER": self.fake.url})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.fake.requests), 2, "the variable outranks the file")
        r = _run([self.file, "--yes", "--receiver", self.fake.url], self.state, home=self.home, extra={"ROMP_PERF_RECEIVER": dead})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.fake.requests), 3, "the flag outranks the variable")
        self.assertEqual(r.stderr, "")

    def test_a_refused_address_names_its_source_and_never_its_value(self):
        secret = "https://user:PASSWORD-MARKER-77@receiver.example/"
        for args, extra, home, source in (([self.file, "--yes", "--receiver", secret], None, HOME, "--receiver"),
                                          ([self.file, "--yes"], {"ROMP_PERF_RECEIVER": secret}, HOME, "ROMP_PERF_RECEIVER"),
                                          ([self.file, "--yes"], None, self.home, "~/.config/romp/perf-receiver")):
            if home == self.home:
                os.makedirs(os.path.join(self.home, ".config", "romp"), exist_ok=True)
                with open(os.path.join(self.home, ".config", "romp", "perf-receiver"), "w") as fh:
                    fh.write(secret + "\n")
            r = self._refused(_run(args, self.state, home=home, extra=extra), 2, "refused: the receiver address from %s is not an https URL" % source,
                              "no userinfo, query or fragment", "127.0.0.1 and localhost only", "nothing sent")
            self.assertEqual(r.stdout, "")
            self.assertNotIn("PASSWORD-MARKER", r.stdout + r.stderr)
            self.assertNotIn("receiver.example", r.stdout + r.stderr)
        for text in ("http://receiver.example/", "https://receiver.example/?x=1", "ftp://receiver.example"):
            self._refused(_run([self.file, "--yes", "--receiver", text], self.state), 2, "is not an https URL")
        self.assertEqual(self.fake.requests, [])

    def test_the_file_must_exist_and_be_a_regular_file_of_at_most_one_mib(self):
        base = [self.fake.url]
        missing = os.path.join(self.xdg, "missing.json")
        self._refused(_run([missing, "--yes", "--receiver"] + base, self.state), 1, "refused: %s does not exist; nothing sent" % missing)
        self._refused(_run([self.xdg, "--yes", "--receiver"] + base, self.state), 1, "refused: %s is not a regular file; nothing sent" % self.xdg)
        big = os.path.join(self.xdg, "big.json")
        with open(big, "wb") as fh:
            fh.write(b"{" + b" " * (1 << 20))                      # 1 MiB + 1: over the cap
        self._refused(_run([big, "--yes", "--receiver"] + base, self.state), 1,
                      "refused: %s is %d bytes and the receiver takes at most %d (1 MiB); nothing sent" % (big, (1 << 20) + 1, 1 << 20))
        with open(big, "wb") as fh:
            fh.write(b"{" + b" " * ((1 << 20) - 1))                # exactly 1 MiB: through the size gate, stopped by the parse
        self._refused(_run([big, "--yes", "--receiver"] + base, self.state), 1, "refused: %s is not strict JSON; nothing sent" % big)
        self.assertEqual(self.fake.requests, [])

    def test_a_fifo_at_the_file_path_is_refused_at_once_and_the_file_is_looked_at_once_through_open_regular(self):
        """read_export decided the FILE's kind with a stat and then read it with a blocking open, so a fifo appearing at the
        path between the two hung the verb forever with no timeout (correctness-1, the third review round; the code closed
        the same window for SIZE and not for KIND). pp.open_regular (O_NONBLOCK, fstat, S_ISREG) closes it atomically, as it
        already did for the setting file. Three pins. A fifo at the path is refused at once as not a regular file, the child
        hard-killed on a timeout since the defect is a hang. A child whose Path.stat swaps the regular file for a fifo the
        moment it is asked about that path, the race made deterministic, sends the file and leaves it a regular file: the
        verb never asks Path.stat about the file now, the open is its one look; before, the swap ran between the stat and
        the read and the read blocked forever (killed after 8 s: the fails-before). And an AST census that read_export
        reaches the file through pp.open_regular and never through a stat or read_bytes attribute."""
        base = ["--yes", "--receiver", self.fake.url]
        fifo = os.path.join(self.xdg, "export.fifo")
        os.mkfifo(fifo)
        try:
            r = subprocess.run([sys.executable, "-c", CHILD, UPLOAD, fifo] + base, capture_output=True, text=True, timeout=8,
                               env=_env(self.state), stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            self.fail("the upload child hung on a fifo at the file path (killed after 8 s)")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "romp perf upload: refused: %s is not a regular file; nothing sent\n" % fifo)
        self.assertEqual(self.fake.requests, [])
        swap = ("import os, pathlib, runpy, socket, stat, sys\n"
                "socket.gethostname = lambda: %r\n"
                "target, sys.argv = sys.argv[1], sys.argv[2:]\n"
                "real = pathlib.Path.stat\n"
                "def swapping(self, *a, **k):\n"
                "    r = real(self, *a, **k)\n"
                "    if str(self) == target and stat.S_ISREG(r.st_mode):\n"
                "        os.unlink(target)\n"
                "        os.mkfifo(target)\n"
                "    return r\n"
                "pathlib.Path.stat = swapping\n"
                "runpy.run_path(sys.argv[0], run_name='__main__')\n") % HOSTNAME
        copy = os.path.join(self.xdg, "copy.json")
        shutil.copyfile(self.file, copy)
        try:
            r = subprocess.run([sys.executable, "-c", swap, copy, UPLOAD, copy] + base, capture_output=True, text=True, timeout=8,
                               env=_env(self.state), stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            self.fail("the upload child hung: it stat'ed the file, the swap put a fifo there, and the blocking read waited on it (killed after 8 s)")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(self.fake.requests), 1)
        self.assertEqual(self.fake.requests[0][2], self.data)
        self.assertTrue(os.path.isfile(copy) and not stat.S_ISFIFO(os.stat(copy).st_mode), "Path.stat was never asked about the file, so the swap never ran")
        with open(os.path.join(ROOT, "cli", "perf_upload.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "read_export")
        self.assertIn("pp.open_regular", [ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)], "the FILE road goes through open_regular")
        self.assertFalse({n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)} & {"stat", "read_bytes", "read_text", "open"},
                         "and never through a stat followed by an open")

    def test_the_file_is_read_to_the_bound_plus_one_byte_and_never_whole(self):
        """The read bound on the FILE argument, pinned where it is decided, the way the third round pinned the setting file's
        and the private list's (tests-2): read_export promises MAX_BYTES + 1 bytes read as the belt for a file that grew after
        the fstat, and replacing read(MAX_BYTES + 1) with read() left every case green, since every case reads a file whose
        size the fstat had already judged (the fourth round's verifier). pp.open_regular is replaced by a recording file whose
        fileno is a real two-byte file's, so the fstat reports a size inside the bound, and whose payload is far past it; the
        one read asked for is MAX_BYTES + 1 bytes, and the outcome is the over-the-bound refusal naming the bytes read,
        MAX_BYTES + 1, never the payload's length. The mutant reads the whole payload, records -1 and names its full length."""
        asked = []
        small = os.path.join(self.xdg, "small.json")
        with open(small, "wb") as fh:
            fh.write(b"{}")
        real = open(small, "rb")
        self.addCleanup(real.close)

        class Recording:
            payload = b"{" + b" " * (pu.MAX_BYTES * 3) + b"}"

            def fileno(self):
                return real.fileno()

            def read(self, n=-1):
                asked.append(n)
                return self.payload if n is None or n < 0 else self.payload[:n]

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        with mock.patch.object(pu.pp, "open_regular", return_value=Recording()):
            with self.assertRaises(pu.Refusal) as cm:
                pu.read_export(self.file, pu.pe.Path(self.state))
        self.assertEqual(asked, [pu.MAX_BYTES + 1], "one bounded read, never an unbounded one")
        self.assertEqual(str(cm.exception), "refused: %s is %d bytes and the receiver takes at most %d (1 MiB); nothing sent"
                         % (self.file, pu.MAX_BYTES + 1, pu.MAX_BYTES), "the belt's refusal names the bytes read, the bound plus one")
        self.assertEqual(cm.exception.code, 1)

    def test_the_file_must_be_strict_json_with_the_schema_line(self):
        base = ["--yes", "--receiver", self.fake.url]
        bad = os.path.join(self.xdg, "bad.json")
        for text, phrase in (("not json", "is not strict JSON"), (b"\xff\xfe".decode("latin-1"), "is not strict JSON"),
                             ('{"schema": "romp-perf-export/1", "perf": {"uptime_s": NaN}}', "is not strict JSON"),
                             ('{"schema": "romp-perf-export/1", "perf": {"x": Infinity}}', "is not strict JSON"),
                             # an overflowing number is the parser's refusal, not the fold belt's ("the perf block differs from its fold", which
                             # is what this document met before the parser refused it; the envelope line is there so nothing earlier refuses)
                             ('{"schema": "romp-perf-export/1", "exported_at": "2026-09-18T12:00Z", "perf": {"uptime_s": 60, "x": 1e999}}',
                              "is not strict JSON (a number is outside the finite range)"),
                             ('{"schema": "romp-perf-export/1", "exported_at": "2026-09-18T12:00Z", "perf": {"uptime_s": 60, "x": -1e999}}',
                              "is not strict JSON (a number is outside the finite range)"),
                             ('{"schema": "romp-perf-export/1", "exported_at": "2026-09-18T12:00Z", "perf": {"uptime_s": 60, "x": 1E400}}',
                              "is not strict JSON (a number is outside the finite range)"),
                             ('["romp-perf-export/1"]', "is not a romp perf export (no top-level schema romp-perf-export/1)"),
                             ('{"perf": {}}', "is not a romp perf export"),
                             ('{"schema": "romp-perf-export/2", "perf": {}}', "is not a romp perf export"),
                             ('{"schema": 1, "perf": {}}', "is not a romp perf export")):
            with open(bad, "w", encoding="latin-1") as fh:
                fh.write(text)
            r = self._refused(_run([bad] + base, self.state), 1, "refused: %s %s" % (bad, phrase), "nothing sent")
            self.assertEqual(r.stdout, "")
        self.assertEqual(self.fake.requests, [])

    def test_an_edited_file_is_refused_by_kind_and_key_path_never_by_value(self):
        base = ["--yes", "--receiver", self.fake.url]
        doc = json.loads(self.data)
        edited = os.path.join(self.xdg, "edited.json")

        def write(d):
            with open(edited, "w") as fh:
                json.dump(d, fh)
        doc["perf"]["note"] = "/home/someone/code/notes-api/scratch.jsonl"          # a value: an absolute path
        write(doc)
        r = self._refused(_run([edited] + base, self.state), 1,
                          "refused: the public form still fails the walk (an absolute path, the value at perf/note); nothing sent")
        self.assertNotIn("someone", r.stdout + r.stderr)
        doc = json.loads(self.data)
        doc["perf"]["stages_ms"]["/home/someone/code/notes-api"] = 2.0                  # a key: outside the grammar and a path
        write(doc)
        r = self._refused(_run([edited] + base, self.state), 1, "still fails the walk (", "a key under perf/stages_ms); nothing sent")
        self.assertNotIn("someone", r.stdout + r.stderr)
        doc = json.loads(self.data)
        doc["perf"]["pusher"]["client"] = "TESTHOST.example"                          # the machine's own hostname (pinned in the child)
        write(doc)
        r = self._refused(_run([edited] + base, self.state), 1,
                          "refused: a string this machine knows (hostname) survives as the value at perf/pusher/client; nothing sent")
        self.assertNotIn("TESTHOST", r.stdout + r.stderr)
        os.makedirs(os.path.join(self.state, "sdk"))
        with open(os.path.join(self.state, "sdk", "web.json"), "w") as fh:            # the registry's session id
            json.dump({"sid": SID, "cwd": "/home/tester/code/notes-api"}, fh)
        doc = json.loads(self.data)
        doc["perf"]["builds"]["chat"][SID[:8]] = 1
        write(doc)
        r = self._refused(_run([edited] + base, self.state), 1,
                          "refused: a string this machine knows (session id) survives as a key under perf/builds/chat; nothing sent")
        self.assertNotIn(SID[:8], r.stdout + r.stderr)
        self.assertEqual(self.fake.requests, [], "no edited file was sent")
        r = _run([self.file] + base, self.state)
        self.assertEqual(r.returncode, 0, "the file as the export wrote it passes the same check")
        self.assertEqual(len(self.fake.requests), 1)

    def test_a_string_on_the_machine_local_private_list_is_refused_by_the_scan_and_never_sent(self):
        """The shared probe set covers the hostname, the login, the home path and the registry's ids, and not a coined
        project nickname, which fits the identifier grammar: a file carrying one passed all three checks and was POSTed
        (7 of 9 such tokens on the box that found it). The machine-local list the repository's pre-push hook reads
        (~/.config/romp/private-strings.txt) is exactly the list of those strings, so it feeds the scan (perf_public
        machine_probes, kind `private string`), resolved under the child's HOME; the refusal names the kind and the
        path and never the string. This widens the shared check, not only the upload. Fails before: exit 0, one request.
        A listed string is matched as a substring OR a whole-token run (the union, the third review round, 2026-09-18):
        the hook matches each entry as a plain substring, so the token glued to letters, as a key (zzcoinedzzChat) or a
        value (chatZzcoinedzz), is a hit here too, refused by the kind and the path, the token in no output, nothing sent.
        Fails before: a whole-token match passed both glued forms and the child POSTed them."""
        base = ["--yes", "--receiver", self.fake.url]
        token = "zzcoinedzz"
        self.assertTrue(pp.IDENT.fullmatch(token), "the token fits the grammar: only the list knows it")
        os.makedirs(os.path.join(self.home, ".config", "romp"))
        with open(os.path.join(self.home, ".config", "romp", "private-strings.txt"), "w", encoding="utf-8") as fh:
            fh.write("# strings that must never be published\n%s\n" % token)
        edited = os.path.join(self.xdg, "edited.json")
        for plant, line, what in (({"leak": token}, "the value at perf/leak", "value"),
                                  ({token + "Chat": 1}, "a key under perf", "key"),                    # the token glued to letters, as a key
                                  ({"leak": "chat" + token.capitalize()}, "the value at perf/leak", "value")):    # and as a value, in another case
            doc = json.loads(self.data)
            doc["perf"].update(plant)
            with open(edited, "w") as fh:
                json.dump(doc, fh)
            r = self._refused(_run([edited] + base, self.state, home=self.home), 1,
                              "refused: a string this machine knows (private string) survives as %s; "
                              "edit line 2 of the private-strings list or that %s; nothing sent" % (line, what))    # line 2: the comment is line 1
            self.assertNotIn(token, (r.stdout + r.stderr).lower(), line)
            self.assertEqual(r.stdout, "", "refused before the summary line")
        self.assertEqual(self.fake.requests, [], "nothing was sent")
        r = _run([edited] + base, self.state)             # the synthetic HOME has no list: the token is a grammar-fitting word and passes
        self.assertEqual(r.returncode, 0, r.stderr + " (without the list, no probe knows the token)")
        r = _run([self.file] + base, self.state, home=self.home)
        self.assertEqual(r.returncode, 0, r.stderr + " (a fresh export passes with the list loaded)")
        self.assertEqual(len(self.fake.requests), 2)

    def test_a_list_path_that_yields_no_list_is_said_on_stderr_and_the_document_is_sent_where_a_readable_list_refuses_it(self):
        """The list turning itself off is said where it happens (pp.LIST_UNREADABLE, the fourth review round, 2026-09-19):
        with a fifo or a directory at ROMP_PRIVATE_STRINGS the upload child sends a document carrying a listed string, as
        before, and now says so in one stderr line naming the path and the reason, where the third round left stderr empty
        and the listed string travelled unannounced (extra4-1); with a readable list at the derived path the same document
        is refused by the scan. The children are run under a timeout and hard-killed, since a fifo at a user-named path is
        where a hang was possible (the second round's defect). Fails before: rc 0, one request, stderr empty."""
        base = ["--yes", "--receiver", self.fake.url]
        token = "zzcoinedzz"
        edited = os.path.join(self.xdg, "edited.json")
        doc = json.loads(self.data)
        doc["perf"]["leak"] = token
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        for make, kind in ((os.mkfifo, "a fifo"), (os.mkdir, "a directory")):
            path = os.path.join(self.xdg, "list-" + kind.split()[-1])
            make(path)
            self.fake.reset()
            try:
                r = subprocess.run([sys.executable, "-c", CHILD, UPLOAD, edited] + base, capture_output=True, text=True, timeout=8,
                                   env=_env(self.state, extra={"ROMP_PRIVATE_STRINGS": path}), stdin=subprocess.DEVNULL)
            except subprocess.TimeoutExpired:
                self.fail("the upload child hung on %s at the private-strings path (killed after 8 s)" % kind)
            self.assertEqual(r.returncode, 0, r.stderr + " (%s: no list, so no probe knows the token)" % kind)
            self.assertEqual(r.stderr, "romp: no private-strings list was read from %s (%s); no listed string is checked\n" % (path, kind),
                             "the list turning itself off is said, naming the path and the reason")
            self.assertEqual(len(self.fake.requests), 1, kind)
            self.assertIn(token.encode(), self.fake.requests[0][2], "the listed string travelled, and the line above is what says the check was off")
        os.makedirs(os.path.join(self.home, ".config", "romp"))
        with open(os.path.join(self.home, ".config", "romp", "private-strings.txt"), "w", encoding="utf-8") as fh:
            fh.write(token + "\n")
        self.fake.reset()
        r = self._refused(_run([edited] + base, self.state, home=self.home), 1,
                          "refused: a string this machine knows (private string) survives as the value at perf/leak; "
                          "edit line 1 of the private-strings list or that value; nothing sent")
        self.assertEqual(self.fake.requests, [], "a readable list refuses the same document, as before")

    def test_an_edited_file_carrying_a_split_row_stamp_is_refused_by_the_denylist_naming_the_row_and_never_the_key(self):
        """`t` is denied at any depth (perf_public.DENY_KEYS, 2026-09-18): the export drops it from every split row, so a
        file that carries one was edited after the export. The walk alone passes it (`t` fits the identifier grammar);
        the denylist walk refuses it, and the refusal names the dict holding the key, never the key or its value."""
        base = ["--yes", "--receiver", self.fake.url]
        doc = json.loads(self.data)
        self.assertEqual(_keys_named(doc, "t"), [], "the export wrote no key named t at any depth")
        doc["perf"]["pusher"]["firstCycle"] = {"s": 0.5, "t": 900.5}          # a split row with its wall-clock stamp put back
        edited = os.path.join(self.xdg, "edited.json")
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = self._refused(_run([edited] + base, self.state), 1,
                          "refused: the public form still fails the denylist (a key the denylist drops, a key under perf/pusher/firstCycle); nothing sent")
        self.assertNotIn("900", r.stdout + r.stderr)
        self.assertEqual(r.stdout, "", "refused before the summary line")
        self.assertEqual(self.fake.requests, [], "nothing was sent")

    def test_an_edited_file_with_the_uptime_to_the_second_is_refused_naming_the_value_path_and_never_the_number(self):
        """The export rounds `uptime_s` down to whole minutes (perf_public.public_uptime, 2026-09-18); a file carrying
        one to the second was edited after the export. A number passes the walk; the denylist walk refuses it, naming
        the value's path and not the number."""
        base = ["--yes", "--receiver", self.fake.url]
        doc = json.loads(self.data)
        self.assertEqual(doc["perf"]["uptime_s"], 60, "the planted snapshot's 100.5 s left the export as one whole minute")
        doc["perf"]["uptime_s"] = 3725
        edited = os.path.join(self.xdg, "edited.json")
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = self._refused(_run([edited] + base, self.state), 1,
                          "refused: the public form still fails the denylist (an uptime not rounded to whole minutes, the value at perf/uptime_s); nothing sent")
        self.assertNotIn("3725", r.stdout + r.stderr)
        self.assertEqual(r.stdout, "", "refused before the summary line")
        self.assertEqual(self.fake.requests, [], "nothing was sent")
        doc["perf"]["uptime_s"] = 3720                                            # on the grain: what the export would have written
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = _run([edited] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.fake.requests), 1, "a whole-minute uptime passes the same check")

    def test_an_edited_file_with_a_bound_off_a_power_of_two_is_refused_naming_the_value_path_and_never_the_number(self):
        """The export rounds every memory-fraction bound (perf_public.BOUND_KEYS) UP to a power of two (public_bound; round 3
        of the export's review, 2026-09-18: each is a fixed fraction of the machine's MemTotal); a file carrying one off a
        power of two was edited after the export. A number passes the walk; the denylist walk refuses it, naming the value's
        path and not the number. The same bound at a power of two passes, however large: a coarsened bound is the export's
        own (and no power of two lies in a stamp window)."""
        base = ["--yes", "--receiver", self.fake.url]
        doc = json.loads(self.data)
        self.assertNotIn("hydrated", doc["perf"]["heap"], "the planted snapshot carries no bound; the case plants one")
        doc["perf"]["heap"]["hydrated"] = {"entries": 12, "bytes": 5000, "capBytes": 4_210_310_144}   # MemTotal / 32 of a 125.5 GiB machine, exact
        edited = os.path.join(self.xdg, "edited.json")
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = self._refused(_run([edited] + base, self.state), 1,
                          "refused: the public form still fails the denylist (a bound not rounded to a power of two, the value at perf/heap/hydrated/capBytes); nothing sent")
        self.assertNotIn("4210310144", r.stdout + r.stderr)
        self.assertEqual(r.stdout, "", "refused before the summary line")
        self.assertEqual(self.fake.requests, [], "nothing was sent")
        doc["perf"]["heap"]["hydrated"]["capBytes"] = 1 << 32                         # what the export would have written: the next power of two
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = _run([edited] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.fake.requests), 1, "a bound at a power of two passes the same check, however large")

    def test_an_edited_file_with_a_number_the_size_of_a_clock_stamp_is_refused_naming_the_value_path_and_never_the_number(self):
        """The export writes no absolute clock stamp: every one the snapshot carries is denied by key, and round 3's property
        test pins that none survives the fold under any key. So a FLOAT leaf inside one of perf_public.STAMP_WINDOWS (1.5e9 to
        2.0e9, an epoch second from 2017 to 2033; 1.5e12 to 2.0e12, the same span in milliseconds) anywhere outside a
        coarsened bound or a duration key (test_an_export_whose_millisecond_totals_reached_the_stamp_window_is_sent_since_a_
        float_under_a_duration_key_is_a_total) was typed in after the export, whatever other key it sits under (a time.time()
        value is a float, and JSON keeps the distinction: a number written with a point or an exponent loads as one); the
        denylist walk refuses it, naming the value's path and not the number. An integer is a count or a byte total and
        passes whatever its size (the next case), and so does a float outside both windows (the allocator case). A fresh
        export passes."""
        base = ["--yes", "--receiver", self.fake.url]
        edited = os.path.join(self.xdg, "edited.json")
        self.assertEqual(pp.STAMP_WINDOWS, ((1.5e9, 2.0e9), (1.5e12, 2.0e12)))
        doc = json.loads(self.data)
        doc["perf"]["pusher"]["startedAt"] = 1.6e9                                    # a stamp under a key the denylist does not know
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = self._refused(_run([edited] + base, self.state), 1,
                          "refused: the public form still fails the denylist (a number the size of a clock stamp, the value at perf/pusher/startedAt); nothing sent")
        self.assertNotIn("1600000000", r.stdout + r.stderr)
        self.assertNotIn("1.6e", r.stdout + r.stderr)
        self.assertEqual(r.stdout, "", "refused before the summary line")
        doc = json.loads(self.data)
        doc["perf"]["pusher"]["marks"] = [1, 1600000000.5]                           # a float, in a list: the path carries the index
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = self._refused(_run([edited] + base, self.state), 1, "(a number the size of a clock stamp, the value at perf/pusher/marks/1); nothing sent")
        self.assertNotIn("1600000000", r.stdout + r.stderr)
        doc = json.loads(self.data)
        doc["perf"]["pusher"]["bootAt"] = 1.6e12                                      # a millisecond stamp under a key the denylist does not know
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = self._refused(_run([edited] + base, self.state), 1, "(a number the size of a clock stamp, the value at perf/pusher/bootAt); nothing sent")
        self.assertNotIn("1600000000000", r.stdout + r.stderr)
        self.assertNotIn("1.6e", r.stdout + r.stderr)
        self.assertEqual(self.fake.requests, [], "nothing was sent")
        doc = json.loads(self.data)
        doc["perf"]["pusher"]["cycles"] = 1_499_999_999                               # below the seconds window: a count, and it passes
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = _run([edited] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = _run([self.file] + base, self.state)
        self.assertEqual(r.returncode, 0, "a fresh export from the export verb passes the same check")
        self.assertEqual(len(self.fake.requests), 2)

    def test_an_export_whose_byte_totals_reached_the_stamp_window_is_sent_since_an_integer_that_large_is_a_total_not_a_stamp(self):
        """The kernel's cumulative byte and count totals are integers, and on a busy kernel the wire totals (pusher.clients
        byKind and byApp `bytes`, `parses.bytes`) pass 1.5e9 within hours, so an export from a long-lived kernel carries
        integers the size of a clock stamp under keys the denylist does not know by name. The re-check exempts an integer
        whatever its size (a time.time() value is a float) and the file is sent whole, the totals in the body; the same
        total written as a float, at the seconds window's ceiling, is the stamp finding, so the type decides and never the
        key. Fails before: the export was refused by its own belt, naming perf/parses/bytes (the shallowest of the four),
        and nothing was sent."""
        base = ["--yes", "--receiver", self.fake.url]
        doc = json.loads(self.data)
        self.assertNotIn("clients", doc["perf"]["pusher"], "the planted snapshot carries no wire table; the case plants one")
        doc["perf"]["pusher"]["clients"] = {
            "byKind": {"chrome": {"frames": 400_000, "bytes": 2_000_000_000, "sendMs": 12345.5, "sendMax": 250.5, "sends": 400_000}},
            "byApp": {"chat": {"frames": 400_000, "bytes": 2_000_000_000}}}
        doc["perf"]["parses"]["bytes"] = 2_000_000_000
        doc["perf"]["pusher"]["startedAt"] = 2_000_000_000                             # an integer under a key the denylist does not know
        edited = os.path.join(self.xdg, "edited.json")
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        with open(edited, "rb") as fh:
            data = fh.read()
        self.assertEqual(data.count(b"2000000000"), 4, "four integers past the floor, written without a point")
        wire = _wire(doc)
        self.assertEqual(wire.count(b"2000000000"), 4, "and the same four in the body the verb sends")
        r = _run([edited] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (edited, len(wire), self.fake.url) + SUCCESS % (RECEIPT, 180))
        self.assertEqual(len(self.fake.requests), 1, "the export with byte totals inside the seconds window was sent")
        self.assertEqual(self.fake.requests[0][2], wire, "the body is the checked document re-serialised, totals included")
        doc["perf"]["pusher"]["clients"]["byKind"]["chrome"]["bytes"] = 2_000_000_000.0   # the same total as a float: a stamp
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = self._refused(_run([edited] + base, self.state), 1,
                          "refused: the public form still fails the denylist (a number the size of a clock stamp, the value at perf/pusher/clients/byKind/chrome/bytes); nothing sent")
        self.assertNotIn("2000000000", r.stdout + r.stderr)
        self.assertEqual(len(self.fake.requests), 1, "nothing more was sent")

    def test_an_export_whose_millisecond_totals_reached_the_stamp_window_is_sent_since_a_float_under_a_duration_key_is_a_total(self):
        """The kernel's millisecond totals are FLOATS and cumulative (pusher.cycle_cpu_ms_sum read 1,779,484.0 after one
        hour on a busy kernel, about 35 days to 1.5e9 and twelve more across the seconds window; the wire tables' sendMs
        behind it), so an export from a long-lived kernel carries floats the size of a clock stamp under duration keys,
        every one of them inside the seconds window for those twelve days. The re-check exempts a float under a
        duration key (perf_public.duration_key: a name whose tokens carry `ms`), its own or any key above it (stages_ms,
        the lifetime sum per stage, whose leaf keys are stage names), and the file is sent whole, the sums in the body;
        the same value under a key whose path carries no `ms` token (sendMax) is the stamp finding, so the key decides
        with the type. Fails before: the export was refused by its own belt, naming perf/pusher/cycle_cpu_ms_sum, and
        nothing was sent; with the leaf-only reading, perf/stages_ms/push at 2.0e9 was refused the same way."""
        base = ["--yes", "--receiver", self.fake.url]
        doc = json.loads(self.data)
        self.assertNotIn("cycle_cpu_ms_sum", doc["perf"]["pusher"], "the planted snapshot carries no cpu sum; the case plants one")
        doc["perf"]["pusher"]["cycle_cpu_ms_sum"] = 2.0e9
        doc["perf"]["stages_ms"]["push"] = 2.0e9            # a stage's lifetime sum: the parent key carries the token, the leaf names the stage
        doc["perf"]["pusher"]["clients"] = {
            "byKind": {"chrome": {"frames": 400_000, "bytes": 2_000_000_000, "sendMs": 1.6e9, "sendMax": 250.5, "sends": 400_000}}}
        edited = os.path.join(self.xdg, "edited.json")
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        with open(edited, "rb") as fh:
            data = fh.read()
        self.assertIn(b"2000000000.0", data, "the sum is written as a float, with a point")
        self.assertIn(b'"push": 2000000000.0', data)
        self.assertIn(b"1600000000.0", data)
        wire = _wire(doc)
        self.assertIn(b'"push": 2000000000.0', wire, "the sums are in the body the verb sends, as floats")
        r = _run([edited] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (edited, len(wire), self.fake.url) + SUCCESS % (RECEIPT, 180))
        self.assertEqual(len(self.fake.requests), 1, "the export with millisecond totals inside the seconds window was sent")
        self.assertEqual(self.fake.requests[0][2], wire, "the body is the checked document re-serialised, sums included")
        doc["perf"]["pusher"]["clients"]["byKind"]["chrome"]["sendMax"] = 1.6e9     # no `ms` token in the name: a stamp
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = self._refused(_run([edited] + base, self.state), 1,
                          "refused: the public form still fails the denylist (a number the size of a clock stamp, the value at perf/pusher/clients/byKind/chrome/sendMax); nothing sent")
        self.assertNotIn("1600000000", r.stdout + r.stderr)
        self.assertEqual(len(self.fake.requests), 1, "nothing more was sent")

    def test_an_export_whose_allocator_figures_passed_the_stamp_window_is_sent_since_a_float_outside_both_windows_is_a_measurement(self):
        """A clock stamp lands in an epoch window (perf_public.STAMP_WINDOWS: 1.5e9 to 2.0e9 seconds, 1.5e12 to 2.0e12
        milliseconds); a float outside both tells no time and is a measurement the export keeps on purpose (the export's
        fifth review round, 2026-09-18: glibc's allocator figures on a long-lived kernel, process.malloc.arena 2931437568
        and uordblks 2731423520, exceeded a floor at 1.5e9 in the served export's property test, and the re-check's own
        floor refused a file carrying them as floats). The re-check passes a float above the seconds window, one between
        the windows and one above the milliseconds window, under keys the denylist does not know and in a list, and the
        file is sent whole, the figures in the body; the same arena figure moved into the seconds window is the stamp
        finding, so the size decides with the type and the key. Fails before: refused by its own belt naming
        perf/process/malloc/arena, nothing sent."""
        base = ["--yes", "--receiver", self.fake.url]
        doc = json.loads(self.data)
        self.assertNotIn("malloc", doc["perf"]["process"], "the planted snapshot carries no allocator block; the case plants one")
        doc["perf"]["process"]["malloc"] = {"arena": 2931437568.0, "hblkhd": 0.0, "uordblks": 2731423520.0, "fordblks": 200014048.0}
        doc["perf"]["pusher"]["marks"] = [2.9e9, 1.0e12, 2.5e12]
        edited = os.path.join(self.xdg, "edited.json")
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        with open(edited, "rb") as fh:
            data = fh.read()
        self.assertIn(b'"arena": 2931437568.0', data, "the figure is written as a float, with a point")
        self.assertIn(b"2731423520.0", data)
        self.assertIn(b"2500000000000.0", data)
        wire = _wire(doc)
        self.assertIn(b'"arena": 2931437568.0', wire, "the figures are in the body the verb sends, as floats")
        r = _run([edited] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (edited, len(wire), self.fake.url) + SUCCESS % (RECEIPT, 180))
        self.assertEqual(len(self.fake.requests), 1, "the export with allocator figures above the seconds window was sent")
        self.assertEqual(self.fake.requests[0][2], wire, "the body is the checked document re-serialised, figures included")
        doc["perf"]["process"]["malloc"]["arena"] = 1_931_437_568.0                  # the same kind of figure inside the seconds window: a stamp
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = self._refused(_run([edited] + base, self.state), 1,
                          "refused: the public form still fails the denylist (a number the size of a clock stamp, the value at perf/process/malloc/arena); nothing sent")
        self.assertNotIn("1931437568", r.stdout + r.stderr)
        self.assertEqual(len(self.fake.requests), 1, "nothing more was sent")

    def test_the_line_before_the_prompt_names_the_url_dialled_with_a_path_and_port_in_the_address_included(self):
        base = self.fake.url + "/u/" + SID                # an address whose path carries an identifier: it is dialled, so it is shown
        r = _run([self.file, "--yes", "--receiver", base + "/"], self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (self.file, len(self.data), base) + SUCCESS % (RECEIPT, 180))
        self.assertEqual(self.fake.requests[0][0], "POST /u/%s/v1/upload HTTP/1.1" % SID, "what was shown is what was dialled")
        r = self._refused(_run([self.file, "--receiver", base], self.state), 2, "pass --yes")
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (self.file, len(self.data), base), "shown before the prompt, so a refusal to answer is informed")
        self.assertEqual(len(self.fake.requests), 1)

    def test_an_integer_a_double_cannot_hold_is_refused_at_the_parse_under_every_key_class_in_one_line_and_never_a_traceback(self):
        """HIGH 2 of the closing check (2026-09-19): json hands the checks unbounded ints, and every float-domain function
        downstream is a raise waiting for one. Driven then on this road: a 401-digit uptime_s answered with a thirty-line
        traceback out of pp.public_uptime (math.isfinite over an int float() cannot hold), reached through pe.check_document
        and pp.denylist_problems, where the verb promises one refusal line; the same digits under a BOUND_KEYS name raised in
        pp.public_bound; under an ordinary counter they passed every check and REACHED THE POST, 401 digits wide. The class,
        a float-domain function meeting an integer json handed on unbounded, is closed at the parse: strict_loads' parse_int
        (pu._bounded_int) refuses every integer literal no double can hold with the line the overflowing float already has, so
        no site on this road, present or future, sees one. Pinned over the verb as a child for each of 10**400, -10**400 and
        10**5000 (the last past the interpreter's int() digit limit, 4300 by default, so without the length pre-check its
        refusal would be the interpreter's bare strict-JSON line and not the verb's reason) at every site class the audit
        named: uptime_s (the first raise then), each BOUND_KEYS name (capBytes at heap/hydrated, the path a real export carries
        it at, and budgetBytes, cap, bound and stageRingMax under a planted block), an ordinary counter (process/rss_kb, the one that
        was sent), an http row's count, a list element, a usage leaf in a --usage export, and a bound inside a subtree whose
        key the fold merges (perf/'a b'/bound, where pp._merge coarsens again after the sum). The file TEXT is written with
        the literal spliced in, since json.dump cannot write a 5001-digit int under the limit. Each: exit 1, exactly the
        NonFinite refusal line naming the file, nothing on stdout, nothing dialled, no traceback and no run of forty zeros
        anywhere in the output. The positive controls draw the edge where float() draws it and not at a digit count:
        int(sys.float_info.max) (309 digits), 2**1024 - 2**970 - 1 (309 digits) and 10**307 are sent, the digits in the body
        the recorder saw; 2**1024 - 2**970 (309 digits, the first int float() refuses) and its negative are refused. Fails
        without parse_int=_bounded_int (the uptime and bound plants meet the denylist lines, since the two coarsenings are
        total over ints; the counter, http-count, list and usage plants meet the fold belt, since the fold nulls the value;
        the 5001-digit plants meet the bare strict-JSON line), fails with the length pre-check dropped (the 10**5000 plants
        get the bare line) and fails with the pre-check at 100 digits (the 309-digit controls are refused)."""
        base = ["--yes", "--receiver", self.fake.url]
        with open(_export(self.xdg, self.state, usage=True, name="usage-export.json"), "rb") as fh:
            usage_data = fh.read()
        self.assertEqual(json.loads(usage_data)["usage"]["actions"], {"send": 7}, "the usage leaf the case plants over")
        mark = "@@INTEGER-LITERAL@@"
        edited = os.path.join(self.xdg, "edited.json")

        def probe(d, **leaf):
            d["perf"]["probe"] = leaf

        sites = (
            ("perf/uptime_s", self.data, lambda d: d["perf"].__setitem__("uptime_s", mark)),
            ("perf/heap/hydrated/capBytes", self.data, lambda d: d["perf"]["heap"].__setitem__("hydrated", {"entries": 12, "bytes": 5000, "capBytes": mark})),
            ("perf/probe/budgetBytes", self.data, lambda d: probe(d, budgetBytes=mark)),
            ("perf/probe/cap", self.data, lambda d: probe(d, cap=mark)),
            ("perf/probe/bound", self.data, lambda d: probe(d, bound=mark)),
            ("perf/probe/stageRingMax", self.data, lambda d: probe(d, stageRingMax=mark)),
            ("perf/process/rss_kb", self.data, lambda d: d["perf"]["process"].__setitem__("rss_kb", mark)),
            ("perf/http/GET /feed/count", self.data, lambda d: d["perf"]["http"].__setitem__("GET /feed", {"count": mark, "ms": 1.0})),
            ("perf/probe/ring/0", self.data, lambda d: probe(d, ring=[mark])),
            ("usage/actions/send", usage_data, lambda d: d["usage"]["actions"].__setitem__("send", mark)),
            ("perf/a b/bound", self.data, lambda d: d["perf"].__setitem__("a b", {"bound": mark})),
        )
        self.assertEqual({s[0].split("/")[-1] for s in sites[1:6]}, set(pp.BOUND_KEYS), "every BOUND_KEYS name is a site")

        def write(data, plant, literal):
            doc = json.loads(data)
            plant(doc)
            text = json.dumps(doc)
            self.assertEqual(text.count(json.dumps(mark)), 1)
            with open(edited, "w") as fh:
                fh.write(text.replace(json.dumps(mark), literal))

        refusal = "romp perf upload: refused: %s is not strict JSON (a number is outside the finite range); nothing sent\n" % edited
        literals = (("10**400", "1" + "0" * 400), ("-10**400", "-1" + "0" * 400), ("10**5000", "1" + "0" * 5000))
        for where, data, plant in sites:
            for name, literal in literals:
                write(data, plant, literal)
                r = _run([edited] + base, self.state)
                label = "%s at %s" % (name, where)
                self.assertEqual(r.returncode, 1, label + "\n" + r.stderr[-800:])
                self.assertEqual(r.stderr, refusal, label)
                self.assertEqual(r.stdout, "", label)
                self.assertNotIn("Traceback", r.stdout + r.stderr, label)
                self.assertNotRegex(r.stdout + r.stderr, r"0{40}", label)
        self.assertEqual(self.fake.requests, [], "no plant was sent")
        # the positive controls, each under the ordinary counter: the edge is float()'s, not a digit count
        fmax, edge = int(sys.float_info.max), 2 ** 1024 - 2 ** 970
        self.assertEqual((len(str(fmax)), len(str(edge)), len(str(edge - 1))), (309, 309, 309))
        counter = sites[6][2]
        for name, value, sent in (("int(sys.float_info.max)", fmax, True), ("2**1024 - 2**970 - 1", edge - 1, True), ("10**307", 10 ** 307, True),
                                  ("2**1024 - 2**970", edge, False), ("-(2**1024 - 2**970)", -edge, False)):
            write(self.data, counter, str(value))
            r = _run([edited] + base, self.state)
            if sent:
                self.assertEqual(r.returncode, 0, name + "\n" + r.stderr[-800:])
                self.assertEqual(r.stderr, "", name)
                self.assertEqual(len(self.fake.requests), 1, name)
                body = self.fake.requests[0][2]
                self.assertEqual(json.loads(body)["perf"]["process"]["rss_kb"], value, name)
                self.assertIn(str(value).encode("utf-8"), body, name + ": the digits are in the body")
                self.fake.requests.clear()
            else:
                self.assertEqual(r.returncode, 1, name + "\n" + r.stderr[-800:])
                self.assertEqual(r.stderr, refusal, name)
                self.assertEqual(r.stdout, "", name)
                self.assertEqual(self.fake.requests, [], name)

    def test_the_exports_own_output_for_a_bound_at_the_largest_double_is_sent_since_the_fold_nulls_what_its_coarsening_made(self):
        """The fold's rule over what it MAKES (the closing check at the re-run's head, its verification, 2026-09-19): a saved
        snapshot carrying int(sys.float_info.max), a number a double holds, under heap.hydrated.capBytes made the export child
        write 2**1024 (public_bound rounds up), and two such values under keys the fold merges made it write 2 * fmax; each is
        a number no double holds, and this verb refused the export's own file as not strict JSON. Driven on the road: the
        export child writes the file from that snapshot, the two leaves are null in it (pp.held_number over each coarsening's
        and each sum's result), and the upload child sends it, exit 0, one request, the nulls in the body and no run of forty
        zeros anywhere. Fails with held_number dropped from fold or from _merge (the export writes 2**1024 and 2 * fmax and
        the upload refuses the file)."""
        fmax = int(sys.float_info.max)
        snap = planted_snapshot()
        snap["heap"]["hydrated"] = {"entries": 12, "bytes": 5000, "capBytes": fmax}
        snap["a b"] = {"n": fmax}
        snap["a c"] = {"n": fmax}
        path = _export(self.xdg, self.state, snap=snap, name="held.json")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotRegex(text, r"0{40}", "the export wrote no number no double holds")
        self.assertNotIn("Infinity", text)
        doc = json.loads(text)
        self.assertIsNone(doc["perf"]["heap"]["hydrated"]["capBytes"])
        self.assertEqual(doc["perf"]["heap"]["hydrated"]["bytes"], 5000, "the occupancy beside the null bound")
        self.assertIsNone(doc["perf"]["other"]["n"], "the merged sum")
        r = _run([path, "--yes", "--receiver", self.fake.url], self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "")
        self.assertEqual(len(self.fake.requests), 1, "the export's own output is sent")
        body = json.loads(self.fake.requests[0][2])
        self.assertIsNone(body["perf"]["heap"]["hydrated"]["capBytes"])
        self.assertIsNone(body["perf"]["other"]["n"])
        self.assertNotRegex(self.fake.requests[0][2].decode("utf-8"), r"0{40}")

    def test_a_plain_export_sends_the_http_table_with_a_count_and_ms_per_route_served_and_no_usage_block_which_is_those_counts_relabelled(self):
        """HIGH 1 of the closing check (2026-09-19): the disclosure paragraph conditioned the 53 action counts and the 15 pane
        counts on --usage, and every one of them is on the wire in a plain export's perf.http table, identical: the usage
        block's actions and views are the http counts relabelled, its session counts copies of leaves that travel, its uptime
        bucket a bucket of an uptime that travels. The paragraph is what a user reads before typing yes, so a clause saying
        data travels only with a flag when it always travels misinforms them in the dangerous direction; the fix names the
        http table as travelling in every export and reduces the --usage clause to the packaging it does. The conditioning is
        pinned here on the ROAD, as documents: the export child writes a plain export from a snapshot that served action and
        pane routes and the upload child sends it, and the body the recorder saw has no top-level usage key and carries, for
        every route the snapshot served, one http row with exactly the keys count and ms (the glossary and remote families
        collapsed to one row each as the kernel collapses them, the off-register key as `other`, the counts summed under the
        collapsed key); the same snapshot exported with --usage and sent carries the usage block, whose actions and views
        equal the http rows' counts under the feature names, whose one session count is the length of a list the plain body
        carries and whose uptime bucket is the bucket of the uptime it carries, so the block adds no number the plain body
        lacks. This planted snapshot is the OLD shape (parses.bySid and no perSession, what a kernel before 2026-09-18 saved),
        so the block has no parsed count: the per-sid table is one the plain export drops, and a count of it was the one
        number the flag added that no leaf of the plain body gave (the verification of the closing check at the re-run's head
        drove it; usage_block no longer counts that table). The whole block's derivation, leaf by leaf, over both snapshot
        shapes, is pinned in tests/test_perf_stats.py (Disclosed); this is the wire's side of it, and the reference's wording
        is pinned in Docs below. Since the second closing check (2026-09-19) the absence is STATED on the wire: the older
        shape's block carries `sessions.parsedUnavailable`, the fixed string `predates-parses.perSession`, in place of the
        count, so a reader of two uploads can tell a count the export could not read from a kernel that parsed nothing; the
        upload's three walks and its fold belt pass the leaf (one token of the ident grammar, as `kernelUptime`'s bucket is)
        and the recording receiver sees it. The same snapshot with a perSession block whose sessions is a digit string, the
        MALFORMED shape (the ruling of 2026-09-19 on the leaf), sent the same way: the leaf carries its own reason,
        `perSession.sessions-not-a-number`, never the predates reason, since the block is there, and the digit string travels
        under perf as the fold leaves it. Fails with export_document writing usage unconditionally (the plain body carries
        the block), with usage_block counting the per-sid table again (a parsed count no plain leaf gives), with the absence
        leaf dropped or either reason reworded (the leaf is read at the receiver by name and value), with the malformed
        shape given the predates reason."""
        base = ["--yes", "--receiver", self.fake.url]
        snap = planted_snapshot()
        snap["http"].update({"GET /feed": {"count": 3, "ms": 30.0}, "GET /timeline": {"count": 2, "ms": 1.0},
                             "POST /new": {"count": 2, "ms": 4.0}, "GET /dist/render.js": {"count": 9, "ms": 1.0}})
        served = {}
        for key, row in snap["http"].items():
            public = pp.http_public_key(key)
            served[public] = served.get(public, 0) + row["count"]
        self.assertEqual(set(served), {"GET /perf", "POST /send", "POST /new", "GET /feed", "GET /timeline", "GET /glossary/*",
                                       "GET /remote/*/sessions", "GET /dist/*", "other"}, "the routes the snapshot served, as the kernel keys them")
        bodies, raw = {}, {}
        for usage in (False, True):
            path = _export(self.xdg, self.state, usage=usage, snap=snap, name="road-%s.json" % ("usage" if usage else "plain"))
            r = _run([path] + base, self.state)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(len(self.fake.requests), 1)
            raw[usage] = self.fake.requests[0][2]
            bodies[usage] = json.loads(raw[usage])
            self.fake.requests.clear()
        plain, withu = bodies[False], bodies[True]
        self.assertNotIn("usage", plain, "a plain export sends no usage block")
        self.assertEqual(set(plain), {"schema", "exported_at", "perf"})
        self.assertEqual(set(withu), {"schema", "exported_at", "perf", "usage"})
        http = plain["perf"]["http"]
        self.assertEqual(set(http), set(served), "one row per route served, whatever made the requests")
        for key, row in http.items():
            self.assertEqual(set(row), {"count", "ms"}, key)
            self.assertEqual(row["count"], served[key], key)
            self.assertIsInstance(row["ms"], float, key)
        self.assertEqual(withu["perf"], plain["perf"], "the perf block is the same with and without the flag")
        actions = {pu.pe._feature_name(k.partition(" ")[2]): row["count"] for k, row in http.items()
                   if k.startswith("POST ") and k.partition(" ")[2] not in pu.pe.ACTION_SKIP}
        views = {pu.pe._feature_name(k.partition(" ")[2]): row["count"] for k, row in http.items()
                 if k.startswith("GET ") and k.partition(" ")[2] in pu.pe.VIEW_ROUTES}
        self.assertEqual((actions, views), ({"send": 7, "new": 2}, {"feed": 3, "timeline": 2}))
        self.assertEqual(withu["usage"]["actions"], actions, "an action count is the http row's count under the route's name")
        self.assertEqual(withu["usage"]["views"], views, "a view count is the http row's count under the route's name")
        # the rest of the block, each leaf from a leaf of the plain body: the old-shape snapshot's per-sid table is dropped
        # from the plain body and gives no parsed count, the absence is stated in the count's place (the plain body has no
        # perSession either, which is the fact the leaf states), and the block's leaves are exactly the four the paragraph names
        self.assertFalse("bySid" in plain["perf"]["parses"], "the per-sid table is one the plain export drops: %s" % sorted(plain["perf"]["parses"]))
        self.assertFalse("perSession" in plain["perf"]["parses"], "the older shape carries no perSession for the count to be copied from")
        self.assertEqual(withu["usage"]["sessions"], {"chatBuilt": len(plain["perf"]["builds"]["chat"]["bySession"]),
                                                      "parsedUnavailable": "predates-parses.perSession"},
                         "a count of a list the plain body carries, no parsed count from the dropped table, and the absence stated")
        self.assertEqual(withu["usage"]["sessions"], {"chatBuilt": 1, "parsedUnavailable": "predates-parses.perSession"})
        self.assertIn(b'"parsedUnavailable": "predates-parses.perSession"', raw[True], "the line at the receiver, by name and value")
        self.assertNotIn(b"parsedUnavailable", raw[False], "a plain export carries no usage block and so no absence leaf")
        self.assertEqual(withu["usage"]["kernelUptime"], next(name for bound, name in pu.pe.UPTIME_BUCKETS if plain["perf"]["uptime_s"] < bound))
        self.assertEqual(set(withu["usage"]), {"actions", "views", "sessions", "kernelUptime"}, "every leaf of the block accounted for")
        # the malformed shape on the wire: the per-sid table replaced by a perSession block whose count is a digit string
        bad = dict(snap, parses=dict({k: v for k, v in snap["parses"].items() if k != "bySid"}, perSession={"sessions": "1", "max": 3}))
        path = _export(self.xdg, self.state, usage=True, snap=bad, name="road-malformed.json")
        r = _run([path] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.fake.requests), 1)
        raw_bad = self.fake.requests[0][2]
        self.fake.requests.clear()
        sent = json.loads(raw_bad)
        self.assertEqual(sent["perf"]["parses"]["perSession"], {"sessions": "1", "max": 3}, "the garbage travels as the fold leaves it")
        self.assertEqual(sent["usage"]["sessions"], {"chatBuilt": 1, "parsedUnavailable": "perSession.sessions-not-a-number"},
                         "the block is there and carries no number: its own reason, never that the snapshot is old")
        self.assertIn(b'"parsedUnavailable": "perSession.sessions-not-a-number"', raw_bad, "the line at the receiver, by name and value")
        self.assertNotIn(b"predates-parses.perSession", raw_bad)

    def test_a_file_that_repeats_a_key_is_refused_before_the_scan_since_the_reader_must_not_choose_a_copy(self):
        """A key spelled twice in one object is refused as not strict JSON, at any depth and whatever the values. The reason
        since the fourth review round (2026-09-19): the body sent is the parsed document re-serialised, so the bytes and
        the parse no longer differ, but a reader that kept one copy (json.loads keeps the last) would silently choose which
        value is checked and sent, and the receiver's contract refuses a repeated key; the refusal stays and names no key."""
        base = ["--yes", "--receiver", self.fake.url]
        dup = os.path.join(self.xdg, "dup.json")
        plants = '"note": "TESTHOST.example", "cwd": "/home/someone/secret-project"'       # the hostname pinned in the child, and a path
        for text in ('{"schema": "romp-perf-export/1", "perf": {%s}, "perf": {"uptime_s": 1}}' % plants,               # at the top
                     '{"schema": "romp-perf-export/1", "perf": {"uptime_s": 1, "pusher": {%s}, "pusher": {"cycles": 1}}}' % plants,   # nested
                     '{"schema": "romp-perf-export/1", "perf": {"uptime_s": 1, "builds": [{%s, "note": "x"}]}}' % plants,   # in a list
                     '{"schema": "romp-perf-export/1", "schema": "romp-perf-export/1", "perf": {"uptime_s": 1}}'):        # the same value twice
            with open(dup, "w") as fh:
                fh.write(text)
            r = self._refused(_run([dup] + base, self.state), 1, "refused: %s is not strict JSON (a key repeats); nothing sent" % dup)
            self.assertEqual(r.stdout, "")
            self.assertNotIn("TESTHOST", r.stdout + r.stderr)
            self.assertNotIn("someone", r.stdout + r.stderr)
        self.assertEqual(self.fake.requests, [], "json.loads alone would keep the last copy and this verb would have chosen it in silence")

    def test_the_body_is_the_checked_document_re_serialised_so_a_spelling_no_check_read_never_travels(self):
        """WHAT IS SENT IS WHAT WAS CHECKED (the upload's fourth review round, 2026-09-19). Every check and the fold belt
        read the parsed document; until this round post() sent the file's raw bytes, so whatever the parser discards
        travelled unread by any check. Three spellings from the round, each planted in a fresh export by editing its TEXT
        (not by json.dump, which would canonicalise them): a number literal with more digits than a float holds
        (0.30000000000000004441 parses to 0.30000000000000004); a digit run the denylist walk refuses as a float inside the
        stamp window (1700000000.5) respelled with an exponent to a value outside it (1700000000e-9 is 1.7); and a listed
        private string that is a digit run (4242424242) respelled inside a numeric leaf (4242424242e-3 is 4242424.242).
        For each, the body the recording receiver saw is the parsed document written out by the export's own writer
        (perf_export.document_text), the file's spelling is nowhere in it, it differs from the file's bytes, and
        Content-Length and the summary line follow the body. A fresh export re-serialises to itself byte for byte (the
        same function wrote it), so a file as the export wrote it goes out as the file. Fails before: the three bodies
        were the files' bytes, each digit run in them. AND THE SCAN READS THE SPELLING THAT GOES OUT (the same round, its
        lens over the final artifact): perf_public.identifier_hits searches every number by its wire spelling, json.dumps,
        the writer's own, so the listed run written as a number in any spelling whose canonical form carries it (a plain
        integer, a float, a negative, embedded in a longer run, a fraction, two exponent forms that canonicalise to
        4242424242.0 and so put the run on the wire from a file that never spelled it, a listed float-shaped entry
        1234.5678 and its exponent respelling 12345678e-4, an element of a list, a leaf under usage) is refused by the scan
        naming the kind and the path, the run in no output, nothing sent; 4242424242e-3 still travels, as 4242424.242, a
        spelling that carries no listed run. Fails before: every numeric spelling was sent, the run on the wire as the
        number every check passed, where the quoted spelling alone was the scan's refusal. The float-shaped entry is the
        base's (5d1de45dc): the first floor (a086ced5a) measured an entry by its LONGEST digit run and so dropped 1234.5678
        (eight digits, longest run four) from the numeric arm while it kept a bare 4242424, and this test was moved to
        1234567.8 with it; the closing check (2026-09-19) found that input refused at the base and sent at head, rc 0, the
        value on the wire. The floor now counts digits across the whole entry (perf_public.numeric_probe), and this case is
        the upload half of the restored assertion. AND EVERY SPELLING A READER RECOVERS THE VALUE FROM IS SCANNED (the same
        closing check): json spells a float at or above 1e16, or under 1e-4, in exponent form with a point after the first
        digit, so a listed 12345670000000000 was refused when the leaf spelled the integer and the same value travelled as
        1.234567e+16, and a listed 0.000015 travelled as 1.5e-05; perf_public.number_spellings scans an exponent-spelled
        leaf by its plain decimal expansion too, so the int 12345670000000000, the float 1.234567e+16, its negative, and
        1.5e-05 in three spellings are each refused naming the entry's line, and the refusal is the only stderr line (every
        entry is at or above the floor). Fails before the fix: 1.234567e+16, -1.234567e+16, 1.5e-05, 0.000015 and 15e-6
        were sent, rc 0, the exponent spelling on the wire. AND KEY ORDER IS A CHANNEL NO CHECK READS (the closing check,
        2026-09-19): strict_loads' repeated-key rule, the three walks, TOP_LEVEL and the fold belt are all order-blind
        (dict equality ignores order), so a fresh export rewritten with every object's keys reversed passes every check;
        sort_keys=True in perf_export.document_text is what keeps the file's own order off the wire, and this case is the
        only pin that reds without it: the reordered file, uploaded with no list, goes out as the export's own canonical
        bytes, not the file's, with the top level in sorted order. The closing check removed sort_keys and 268 tests
        passed; a consistent indent change (indent=2) is not this pin's claim, since it is a writer-and-reader agreement
        and the body still equals the export the same writer wrote."""
        base = ["--yes", "--receiver", self.fake.url]
        text = self.data.decode("utf-8")
        anchor = '"uptime_s": 60'
        self.assertEqual(text.count(anchor), 1, "the fresh export's one uptime line is where the leaf is planted")
        self.assertEqual(_wire(pu.strict_loads(self.data)), self.data, "a fresh export re-serialises to itself: the writer is the same function")

        def _reversed(node):
            """`node` with every object rebuilt in reversed key order, lists recursed, scalars as they are: the same
            document under another layout."""
            if isinstance(node, dict):
                return {k: _reversed(node[k]) for k in reversed(list(node))}
            if isinstance(node, list):
                return [_reversed(v) for v in node]
            return node
        reordered = os.path.join(self.xdg, "reordered.json")
        with open(reordered, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(_reversed(pu.strict_loads(self.data)), indent=1) + "\n")    # the writer's indent, NO sort_keys
        with open(reordered, "rb") as fh:
            raw = fh.read()
        self.assertNotEqual(raw, self.data, "the reordered file differs from the export in layout")
        self.assertEqual(json.loads(raw), json.loads(self.data), "and is the same document")
        self.fake.reset()
        r = _run([reordered] + base, self.state)                                             # the synthetic HOME has no list
        self.assertEqual(r.returncode, 0, r.stderr + " (key order is read by no check)")
        self.assertEqual(len(self.fake.requests), 1)
        body = self.fake.requests[0][2]
        self.assertEqual(body, self.data, "the body is the canonical bytes: the file's own key order is not on the wire (sort_keys)")
        self.assertNotEqual(body, raw, "and not the reordered file's bytes")
        self.assertEqual(list(json.loads(body)), ["exported_at", "perf", "schema"], "the top level in sorted order")
        os.makedirs(os.path.join(self.home, ".config", "romp"))
        entries = {1: "4242424242",                # a bare digit run
                   2: "1234.5678",                 # float-shaped: eight digits across the entry, a longest run of four (the base's entry)
                   3: "12345670000000000",         # an integer whose canonical float spelling is exponent form, 1.234567e+16
                   4: "0.000015"}                  # seven digits; the plain spelling of 1.5e-05, which is how json spells the value
        with open(os.path.join(self.home, ".config", "romp", "private-strings.txt"), "w", encoding="utf-8") as fh:
            fh.write("".join(entries[n] + "\n" for n in sorted(entries)))
        for entry in list(entries.values()) + ["1.234567e+16", "1.5e-05"]:
            self.assertNotIn(entry.encode(), self.data, "the fresh export carries no listed entry in any spelling")
        edited = os.path.join(self.xdg, "edited.json")
        for literal, canonical, digits in (("0.30000000000000004441", "0.30000000000000004", b"4441"),
                                           ("1700000000e-9", "1.7", b"1700000000"),
                                           ("4242424242e-3", "4242424.242", b"4242424242")):
            with open(edited, "w", encoding="utf-8") as fh:
                fh.write(text.replace(anchor, anchor + ', "zzratio": ' + literal))
            with open(edited, "rb") as fh:
                raw = fh.read()
            self.assertIn(digits, raw, literal)
            self.fake.reset()
            r = _run([edited] + base, self.state, home=self.home)
            self.assertEqual(r.returncode, 0, r.stderr + " (%s: the checks read %s, a measurement)" % (literal, canonical))
            self.assertEqual(len(self.fake.requests), 1, literal)
            line, headers, body = self.fake.requests[0]
            self.assertEqual(body, _wire(pu.strict_loads(raw)), "the body is the parsed document written by the export's writer: " + literal)
            self.assertNotEqual(body, raw, "and not the file's bytes: " + literal)
            self.assertIn(('"zzratio": ' + canonical).encode(), body, literal)
            self.assertNotIn(digits, body, "the spelling no check read is not on the wire: " + literal)
            self.assertEqual(int(dict(headers)["Content-Length"]), len(body), "Content-Length follows the body sent")
            self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (edited, len(body), self.fake.url) + SUCCESS % (RECEIPT, 180),
                             "the summary line names the body's size, not the file's")
        with open(edited, "w", encoding="utf-8") as fh:
            fh.write(text.replace(anchor, anchor + ', "zzratio": "4242424242"'))          # the listed digit run as a string: the scan reads it
        self.fake.reset()
        r = self._refused(_run([edited] + base, self.state, home=self.home), 1,
                          "refused: a string this machine knows (private string) survives as the value at perf/zzratio; "
                          "edit line 1 of the private-strings list or that value; nothing sent")
        self.assertNotIn("4242424242", r.stdout + r.stderr)
        self.assertEqual(self.fake.requests, [])
        refusal = ("refused: a string this machine knows (private string) survives as the value at %s; "
                   "edit line %d of the private-strings list or that value; nothing sent")
        for literal in ("4242424242", "4242424242.0", "4242424242.5", "-4242424242", "14242424242", "0.4242424242",
                        "4.242424242e9", "4242424242e0",                    # line 1, by the wire spelling
                        "1234.5678", "12345678e-4",                         # line 2: the float-shaped entry, and its exponent respelling
                        "1.234567e+16", "12345670000000000", "-1.234567e+16",   # line 3: the int, and the float json spells with an exponent
                        "1.5e-05", "0.000015", "15e-6"):                    # line 4: a small float json spells with an exponent, three ways
            with open(edited, "w", encoding="utf-8") as fh:
                fh.write(text.replace(anchor, anchor + ', "zzratio": ' + literal))
            value = json.loads(literal)
            spellings = pp.number_spellings(json.dumps(value), value)      # the wire spelling, then its plain expansion when it has an exponent
            lines = [n for n, entry in entries.items() if any(entry in s for s in spellings)]
            self.assertEqual(len(lines), 1, "%s: exactly one listed entry is carried by a spelling of the value %r" % (literal, spellings))
            listed_line = lines[0]                                         # the refusal names the entry's line, never the entry
            r = _run([edited] + base, self.state, home=self.home)
            self.assertEqual(r.returncode, 1, "%s as a number was not refused (listed entry on line %d): %s" % (literal, listed_line, r.stdout + r.stderr))
            self._refused(r, 1, refusal % ("perf/zzratio", listed_line))
            for run in list(entries.values()) + ["12345678", "1.234567e+16", "1.5e-05"]:
                self.assertNotIn(run, r.stdout + r.stderr, literal)
            self.assertEqual(r.stdout, "", literal)
            self.assertEqual(r.stderr.count("\n"), 1, literal + ": the refusal alone; every listed entry is at or above the floor, so no advisory")
        with open(edited, "w", encoding="utf-8") as fh:
            fh.write(text.replace(anchor, anchor + ', "zzlist": [4242424242, 1]'))            # an element of a list
        self._refused(_run([edited] + base, self.state, home=self.home), 1, refusal % ("perf/zzlist/0", 1))
        xdg, state = _state_root()
        self.addCleanup(shutil.rmtree, xdg, True)
        with open(_export(xdg, state, usage=True), encoding="utf-8") as fh:
            usage = fh.read()
        self.assertEqual(usage.count('"send": 7'), 1, "the usage block's one action count is where the leaf is planted")
        with open(edited, "w", encoding="utf-8") as fh:
            fh.write(usage.replace('"send": 7', '"send": 7, "zzratio": 4242424242'))       # a leaf under usage, walked like perf
        self._refused(_run([edited] + base, state, home=self.home), 1, refusal % ("usage/actions/zzratio", 1))
        self.assertEqual(self.fake.requests, [], "no numeric spelling whose canonical form carries a listed run was sent")
        with open(edited, "w", encoding="utf-8") as fh:
            fh.write(text.replace(anchor, anchor + ', "zzratio": 4242424242'))
        r = _run([edited] + base, self.state)                                              # the synthetic HOME has no list: a number like any other
        self.assertEqual(r.returncode, 0, r.stderr + " (without the list, no probe is a digit run and the number passes)")
        self.assertIn(b'"zzratio": 4242424242', self.fake.requests[0][2])

    def test_a_listed_six_digit_run_in_a_number_travels_with_the_stderr_line_and_a_seven_digit_run_is_refused_naming_the_list_line(self):
        """The floor by the upload child (2026-09-19, the comment at pp.NUMERIC_PROBE_MIN_DIGITS). With a list of a comment, a
        word, a blank and a six-digit run (line 4) under the child's HOME, an export edited to carry the run as a NUMBER in
        five spellings (whole, inside a byte total, a float, a negative, an exponent form) is sent, exit 0, the number on
        the wire, and stderr is exactly the one line saying 1 of 2 entries (list line 4: the entry by the line it is on, never
        its text or the list's path) could match a number, by their spelling or by their digit groups, but carry fewer than 7
        digits and so are checked in keys and string values and not in numbers, and what does and does not protect a number
        (the text is perf_public.LIST_UNDER_NUMERIC_FLOOR, pasted here whole: the closing check of 2026-09-19 found the old
        line's remedy, list more of the digits, a trap, since a listed eight-digit run protected the number 1234.5678 in no
        spelling while it silenced the line; the count is by number_matchable entries under the floor since the closing
        re-run, an entry spelled like a number or a run of digit-only tokens such as (123456) or _123456, since the arm
        applies those to a number by their digit groups and an operator holding one is unprotected in numbers too, so the
        word entry is not counted and an entry carrying a letter such as abc12 would not be either); the same run in QUOTES
        is refused as before,
        naming line 4 and the remedy, the loud line before the refusal. With the run lengthened to seven digits on the same
        line, five numeric spellings are each refused in one
        stderr line naming the kind, the value's path and line 4 of the list, the run in no output, nothing sent. The
        boundary is by execution with literals: 424242 travels, 4242424 does not. Fails before: every six-digit spelling was
        refused and no refusal named a line."""
        base = ["--yes", "--receiver", self.fake.url]
        text = self.data.decode("utf-8")
        anchor = '"uptime_s": 60'
        self.assertEqual(text.count(anchor), 1)
        self.assertNotIn("424242", text, "the fresh export carries neither run")
        edited = os.path.join(self.xdg, "edited.json")
        os.makedirs(os.path.join(self.home, ".config", "romp"))
        listed = os.path.join(self.home, ".config", "romp", "private-strings.txt")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("# strings that must never be published\nzzcoinedzz\n\n424242\n")
        loud = ("romp: 1 of 2 private-strings entries (list line 4) could match a number, by their spelling or by their digit groups, but carry "
                "fewer than 7 digits, so they are checked in keys and string values and not in numbers; a number is checked against a listed "
                "entry only when the entry, or the plain "
                "decimal spelling of an entry written with an exponent, carries 7 or more digits, and the match is against the number's own "
                "spelling: a listed 1234.5678 protects the number 1234.5678, a listed 12345678 does not, and a listed entry of fewer digits "
                "protects no number\n")
        self.assertEqual(loud, pp.LIST_UNDER_NUMERIC_FLOOR % (1, 2, pp.list_lines_phrase([4]), 7, 7) + "\n",
                         "the literal here is the module's line with its four numbers and the counted entry's list line")
        self.assertNotIn(listed, loud, "the list's path is not in the line")
        for literal in ("424242", "9424242", "424242.0", "-424242", "4.24242e5"):
            with open(edited, "w", encoding="utf-8") as fh:
                fh.write(text.replace(anchor, anchor + ', "zzratio": ' + literal))
            self.fake.reset()
            r = _run([edited] + base, self.state, home=self.home)
            self.assertEqual(r.returncode, 0, literal + ": " + r.stdout + r.stderr)
            self.assertEqual(r.stderr, loud, literal)
            self.assertEqual(len(self.fake.requests), 1, literal)
            self.assertIn(('"zzratio": ' + json.dumps(json.loads(literal))).encode(), self.fake.requests[0][2], "the number travelled: " + literal)
        with open(edited, "w", encoding="utf-8") as fh:
            fh.write(text.replace(anchor, anchor + ', "zzratio": "424242"'))
        self.fake.reset()
        r = _run([edited] + base, self.state, home=self.home)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stderr, loud + "romp perf upload: refused: a string this machine knows (private string) survives as the value at "
                                          "perf/zzratio; edit line 4 of the private-strings list or that value; nothing sent\n")
        self.assertEqual(self.fake.requests, [], "the quoted run is refused as before")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("# strings that must never be published\nzzcoinedzz\n\n4242424\n")
        for literal in ("4242424", "94242424", "4242424.0", "-4242424", "4.242424e6"):
            with open(edited, "w", encoding="utf-8") as fh:
                fh.write(text.replace(anchor, anchor + ', "zzratio": ' + literal))
            r = self._refused(_run([edited] + base, self.state, home=self.home), 1,
                              "refused: a string this machine knows (private string) survives as the value at perf/zzratio; "
                              "edit line 4 of the private-strings list or that value; nothing sent")
            self.assertNotIn("4242424", r.stdout + r.stderr, literal)
            self.assertEqual(r.stdout, "", literal)
        self.assertEqual(self.fake.requests, [], "no seven-digit spelling was sent")

    def test_a_listed_entry_with_an_exponent_beyond_the_doubles_range_is_checked_by_its_own_text_in_one_line_and_never_a_traceback(self):
        """The refusable input of the closing re-run's finding 5 (2026-09-19), on the upload road, under an address-space
        cap. A list of exactly one entry, 1e-1000000000, gave the head before the fix an uncaught MemoryError out of
        format(Decimal(text), "f"): the plain expansion of an exponent-spelled entry has as many digits as the exponent, so
        PRIVATE_STRINGS_MAX bounded the FILE and not the WORK, which grows with an entry's exponent. With the bound
        (perf_public.EXPANSION_EXPONENT_MAX, 324: the smallest double is 5e-324 and the largest about 1.8e+308, so no number
        an export carries is written further out) the entry keeps its own text as its one spelling, a fresh export is sent,
        rc 0, one request whose body is the export's bytes, stdout the summary and the receipt line, and stderr EXACTLY the
        one advisory line, perf_public.LIST_EXPANSION_SKIPPED with the count, the list's length and the entries' list lines
        (never their text), pasted here whole so the module and the road agree; Traceback, MemoryError and InvalidOperation in
        no stream. The list's second line is 1e-10000000000000000000, whose exponent (10**19) the decimal module refuses to
        construct (past decimal.MAX_EMAX, about 1e18): the bound's first cut asked Decimal(text).adjusted() bare and this verb
        died on it with an uncaught InvalidOperation (the re-run's verification, rc 1, zero requests), so the line reads 2 of
        2, list lines 1 and 2. The child runs under RLIMIT_AS of 1.5 GiB on Linux, set in its own prelude and not through a
        fork hook (_run: the parent runs the loopback Receiver's server thread, and a preexec_fn in a threaded parent is the
        documented deadlock hazard); 1.5 GiB is the export module's ADDRESS_SPACE_CAP for its measured reasons (the
        free-threaded 3.14t interpreter maps about 1 GiB before any code runs and died importing hashlib under 768 MiB, and
        under 2 GiB the billion-digit expansion completes and the mutated child grinds to the timeout; under 1.5 GiB it raises
        MemoryError in under a second), so the mutation, the bound removed, fails fast with the MemoryError the re-run saw
        instead of filling the box; elsewhere the case still pins the one line and no traceback. This case is run inside a
        memory-capped scope by the sweep's own rule for a refusable input that could allocate without bound."""
        base = ["--yes", "--receiver", self.fake.url]
        os.makedirs(os.path.join(self.home, ".config", "romp"))
        with open(os.path.join(self.home, ".config", "romp", "private-strings.txt"), "w", encoding="utf-8") as fh:
            fh.write("1e-1000000000\n1e-10000000000000000000\n")
        line = ("romp: 2 of 2 private-strings entries (list lines 1 and 2) are written with an exponent beyond 324, further than any number in an "
                "export reaches, so each is checked by its own text and not by its plain decimal expansion\n")
        self.assertEqual(line, pp.LIST_EXPANSION_SKIPPED % (2, 2, pp.list_lines_phrase([1, 2]), pp.EXPANSION_EXPONENT_MAX) + "\n",
                         "the literal here is the module's line with its numbers and the entries' list lines")
        self.assertEqual(pp.EXPANSION_EXPONENT_MAX, 324)
        cap = 1536 * 1024 * 1024 if sys.platform.startswith("linux") else None   # the export module's ADDRESS_SPACE_CAP, and why
        r = _run([self.file] + base, self.state, home=self.home, address_space=cap)
        for word in ("Traceback", "MemoryError", "InvalidOperation", "1e-1000000000", "1e-10000000000000000000"):
            self.assertNotIn(word, r.stdout + r.stderr, word)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stderr, line, "the one advisory line and nothing else: each entry is at the floor by its own digits as written")
        self.assertEqual(len(self.fake.requests), 1)
        self.assertEqual(self.fake.requests[0][2], self.data, "the export's bytes: neither entry's own text is in any number of a fresh export")
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (self.file, len(self.data), self.fake.url) + SUCCESS % (RECEIPT, 180))

    def test_a_listed_entry_written_with_an_exponent_is_applied_by_its_plain_spelling_to_keys_and_string_values_too(self):
        """The closing re-run's finding 1 (2026-09-19), on the upload road: identifier_hits expanded an exponent-spelled entry
        for the NUMBER arm alone, so a listed 1.5e-05 refused the number 1.5e-05 and SENT the string "0.000015" and the key
        zz0.000015 (the re-run executed the four sending cases below at rc 0, the digits in the body; not a regression, the
        base did the same), while docs/reference.md told the operator the entry reaches the floor as 0.000015 with no
        sentence scoping that to numbers. Every spelling of a non-word probe is now a probe for keys and string values as
        well (perf_public.identifier_hits, its spelled list): with the list 1.5e-05 the string "0.000015" as a value and the
        key zz0.000015 are each refused naming the kind, the place and line 1 of the list, the digits in no output, nothing
        sent; with the list 1e+16 the string "10000000000000000" is refused the same way; and the control, the list 0.000015
        against the same string, refuses as the base did. stderr is exactly the refusal each time: no entry is under the
        floor and none is written with an exponent beyond the bound, so no advisory. Fails before: rc 0 and one POST for
        each of the first three, the digits on the wire."""
        base = ["--yes", "--receiver", self.fake.url]
        text = self.data.decode("utf-8")
        anchor = '"uptime_s": 60'
        self.assertEqual(text.count(anchor), 1)
        for digits in ("0.000015", "10000000000000000"):
            self.assertNotIn(digits, text, "the fresh export carries neither spelling")
        edited = os.path.join(self.xdg, "edited.json")
        os.makedirs(os.path.join(self.home, ".config", "romp"))
        listed = os.path.join(self.home, ".config", "romp", "private-strings.txt")
        refusal = ("romp perf upload: refused: a string this machine knows (private string) survives as %s; "
                   "edit line 1 of the private-strings list or that %s; nothing sent\n")
        for entry, plant, place, what, digits in (
                ("1.5e-05", ', "zzn": "0.000015"', "the value at perf/zzn", "value", "0.000015"),
                ("1.5e-05", ', "zz0.000015": 1', "a key under perf", "key", "0.000015"),
                ("1e+16", ', "zzn": "10000000000000000"', "the value at perf/zzn", "value", "10000000000000000"),
                ("0.000015", ', "zzn": "0.000015"', "the value at perf/zzn", "value", "0.000015")):     # the control: the base's behaviour
            with open(listed, "w", encoding="utf-8") as fh:
                fh.write(entry + "\n")
            with open(edited, "w", encoding="utf-8") as fh:
                fh.write(text.replace(anchor, anchor + plant))
            self.fake.reset()
            r = _run([edited] + base, self.state, home=self.home)
            self.assertEqual(r.returncode, 1, "listed %s against %s was not refused: %s" % (entry, plant, r.stdout + r.stderr))
            self.assertEqual(r.stderr, refusal % (place, what), entry + " against " + plant)
            self.assertEqual(r.stdout, "", entry)
            self.assertNotIn(digits, r.stdout + r.stderr, entry)
            self.assertNotIn(entry, r.stdout + r.stderr, entry)
            self.assertEqual(self.fake.requests, [], "nothing sent: listed %s against %s" % (entry, plant))

    def test_a_listed_entry_carrying_other_characters_is_applied_to_a_number_by_its_token_run_and_refused_before_any_request(self):
        """The alphabet is not asked of the numeric arm (the closing delta, 2026-09-19). A listed (12345678), eight digits inside
        characters no number spells, is applied to a number by its whole-token run (perf_public.probe_in), so an export edited
        to carry the integer 12345678 is refused naming the kind, the path and line 1 of the list, the run in no output, rc 1
        and NO request at the receiver, as the base at 5d1de45dc did; the delta's first cut required a listed entry to be
        spelled like a number before it reached the arm, and the closing check's Refuted section measured that cut as three
        refusals turned into POSTs ((12345678), _12345678 and 12345678/ against the leaf 12345678, on this road and the
        export's). The token-run match is by digit GROUPS: the same list lets the pointed 1234.5678 travel, rc 0 and one
        request carrying the value, since its groups 1234 and 5678 are not the entry's one group, and stderr is empty, the
        entry being at the floor by its eight digits and not something the advisory counts. Fails under the first cut: rc 0
        and one POST carrying 12345678."""
        base = ["--yes", "--receiver", self.fake.url]
        text = self.data.decode("utf-8")
        anchor = '"uptime_s": 60'
        self.assertEqual(text.count(anchor), 1)
        self.assertNotIn("12345678", text, "the fresh export carries no eight-digit run")
        edited = os.path.join(self.xdg, "edited.json")
        os.makedirs(os.path.join(self.home, ".config", "romp"))
        with open(os.path.join(self.home, ".config", "romp", "private-strings.txt"), "w", encoding="utf-8") as fh:
            fh.write("(12345678)\n")
        with open(edited, "w", encoding="utf-8") as fh:
            fh.write(text.replace(anchor, anchor + ', "zzratio": 12345678'))
        r = _run([edited] + base, self.state, home=self.home)
        self._refused(r, 1, "refused: a string this machine knows (private string) survives as the value at perf/zzratio; "
                            "edit line 1 of the private-strings list or that value; nothing sent")
        self.assertNotIn("12345678", r.stdout + r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(self.fake.requests, [], "refused before any request: nothing was dialled")
        with open(edited, "w", encoding="utf-8") as fh:
            fh.write(text.replace(anchor, anchor + ', "zzratio": 1234.5678'))
        r = _run([edited] + base, self.state, home=self.home)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "", "an eight-digit entry is at the floor: nothing is under it to be said")
        self.assertEqual(len(self.fake.requests), 1)
        self.assertIn(b'"zzratio": 1234.5678', self.fake.requests[0][2], "the groups split unlike the entry's: the value travels")

    def test_an_edited_file_the_fold_would_have_changed_is_refused_by_kind_and_key_path_and_never_sent(self):
        """The re-check holds the file to the export's FOLD, not to the walk's shapes alone (the upload's second review
        round, 2026-09-18). Three edits the walk passed and the fold would have written differently, each POSTed at the
        previous head: a 41-character token with no whitespace, hex run or path as a string value (the fold writes `other`),
        a key with a trailing newline after a good name (the walk's `$`-anchored match admits it, the fold's fullmatch does
        not), and a top-level block the envelope does not name whose value carries the token. Each exits 1 with one stderr
        line naming the kind and the key path (a key's the dict holding it), the token in no output, nothing sent; a fresh
        export and a 20-deep file, inside the depth bound, still exit 0."""
        base = ["--yes", "--receiver", self.fake.url]
        token = "zz-planted-token-past-thirty-two-chars-zz"
        edited = os.path.join(self.xdg, "edited.json")
        for edit, line in (({"perf": {"leak": token}}, "a string the fold would have folded, the value at perf/leak"),
                           ({"perf": {"cycles\n": 1}}, "a key the fold would have folded, a key under perf"),
                           ({"extra": {"note": token}}, "a string the fold would have folded, the value at extra/note")):
            doc = json.loads(self.data)
            for k, v in edit.items():
                doc.setdefault(k, {}).update(v)
            with open(edited, "w") as fh:
                json.dump(doc, fh)
            r = self._refused(_run([edited] + base, self.state), 1, "refused: the public form still fails the denylist (%s); nothing sent" % line)
            self.assertNotIn(token, r.stdout + r.stderr, line)
            self.assertNotIn("cycles", r.stdout + r.stderr, line)
            self.assertEqual(r.stdout, "", "refused before the summary line")
        self.assertEqual(self.fake.requests, [], "none of the three was sent")
        r = _run([self.file] + base, self.state)
        self.assertEqual(r.returncode, 0, "a fresh export is its own fold and passes")
        deep = os.path.join(self.xdg, "deep.json")
        with open(deep, "w") as fh:
            fh.write(_nested(20))
        r = _run([deep] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.fake.requests), 2)

    def test_a_top_level_key_the_export_does_not_write_is_refused_naming_the_key_and_never_sent(self):
        """The re-check holds the file's TOP LEVEL to exactly what the export writes (pu.TOP_LEVEL: schema, exported_at and
        perf, kernel_commit and usage optional, no other key, each envelope line in the export's spelling), the upload's
        third review round, 2026-09-18. Before the allowlist a block nobody thought about at the root passed the three
        checks and the fold belt and was POSTed: fold's rules are anchored at the block root, so a `judge` block at the root
        is not the denied perf/judge/child/failures/first, a `now` integer at the root is not the denied perf/now, and a
        kernel_commit spelled as a dict folds to itself. Each is refused, exit 1, one stderr line naming the top-level key
        (printable: the three checks passed over it) and never the value, the token in no output, nothing sent; the same
        judge value under perf is the denylist's finding as before; a missing exported_at or perf is refused naming the
        missing line; a fresh export passes with and without kernel_commit and with and without usage."""
        base = ["--yes", "--receiver", self.fake.url]
        token = "zz-ident-token-the-root-knew"
        self.assertTrue(pp.IDENT.fullmatch(token), "the token fits the grammar: no check names it")
        edited = os.path.join(self.xdg, "edited.json")
        for plant, line in ((("judge", {"child": {"failures": {"first": token}}}), "a top-level judge block the export does not write"),
                            (("now", 1700000000), "a top-level now block the export does not write"),
                            (("kernel_commit", {"sha": token}), "the kernel_commit line is not what the export writes"),
                            (("kernel_commit", "ABCDEF0123"), "the kernel_commit line is not what the export writes"),
                            (("exported_at", "2026-09-18T12:00:00Z"), "the exported_at line is not what the export writes"),
                            (("usage", [token]), "the usage block is not what the export writes")):
            doc = json.loads(self.data)
            doc[plant[0]] = plant[1]
            with open(edited, "w") as fh:
                json.dump(doc, fh)
            r = self._refused(_run([edited] + base, self.state), 1, "refused: %s is not the export's own shape (%s); nothing sent" % (edited, line))
            self.assertNotIn(token, r.stdout + r.stderr, line)
            self.assertNotIn("1700000000", r.stdout + r.stderr, line)
            self.assertNotIn("ABCDEF", r.stdout + r.stderr, line)
            self.assertEqual(r.stdout, "", "refused before the summary line")
        for missing in ("exported_at", "perf"):
            doc = json.loads(self.data)
            del doc[missing]
            with open(edited, "w") as fh:
                json.dump(doc, fh)
            self._refused(_run([edited] + base, self.state), 1, "refused: %s is not the export's own shape (no top-level %s); nothing sent" % (edited, missing))
        doc = json.loads(self.data)
        doc["perf"]["judge"] = {"child": {"failures": {"first": token}}}      # the same value under perf: the denylist's finding, as before
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = self._refused(_run([edited] + base, self.state), 1,
                          "refused: the public form still fails the denylist (a key the denylist drops, a key under perf/judge/child/failures); nothing sent")
        self.assertNotIn(token, r.stdout + r.stderr)
        self.assertEqual(self.fake.requests, [], "none of the edited files was sent")
        for usage in (False, True):
            for commit in (None, "0123456789abcdef0123456789abcdef01234567"):
                xdg, state = _state_root()
                self.addCleanup(shutil.rmtree, xdg, True)
                fresh = _export(xdg, state, usage=usage, commit=commit)
                with open(fresh, "rb") as fh:
                    doc = json.loads(fh.read())
                self.assertEqual(sorted(doc), sorted(["schema", "exported_at", "perf"] + (["usage"] if usage else []) + (["kernel_commit"] if commit else [])))
                r = _run([fresh] + base, state)
                self.assertEqual(r.returncode, 0, r.stderr + " (a fresh export, usage=%r, commit=%r, is the export's own shape)" % (usage, bool(commit)))
        self.assertEqual(len(self.fake.requests), 4)

    def test_a_hundred_thousand_level_file_is_refused_by_the_parser_or_the_depth_bound_and_one_within_the_bound_takes_the_ordinary_path(self):
        """Which refusal the 100000-level document meets depends on whether the build's parser admits it: a parser that
        gives up on it refuses it as not strict JSON; one that admits it (CI's free-threaded 3.14t cell does) hands it to
        the depth bound, which refuses it as nested 100001 levels deep. Which of the two fires is a property of the
        interpreter's stack, not of the verb (the case once pinned the strict-JSON line alone and was red on that cell
        while green on every other), so the case asserts the properties the verb owes and nothing about which line: exit
        1, stderr equal to one of the two fixed lines, no Recursion and no Traceback in it, empty stdout, no request sent.
        The strict-JSON road itself is pinned as a unit in DepthBound by making the parser raise."""
        base = ["--yes", "--receiver", self.fake.url]
        deep = os.path.join(self.xdg, "deep.json")
        with open(deep, "w") as fh:
            fh.write('{"schema": "romp-perf-export/1", "perf": ' + "[" * 100000 + "]" * 100000 + "}")        # 200 KB, under the size cap
        r = self._refused(_run([deep] + base, self.state), 1, "refused: %s is " % deep, "; nothing sent")
        self.assertIn(r.stderr, ("romp perf upload: refused: %s is not strict JSON; nothing sent\n" % deep,
                                 "romp perf upload: refused: %s is nested 100001 levels deep and this verb takes at most 32; nothing sent\n" % deep),
                      r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertNotIn("Recursion", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.fake.requests, [])
        with open(deep, "w") as fh:
            fh.write(_nested(20))
        r = _run([deep] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr + " (20 levels is inside the bound and every build's walks admit it; the verb parses, walks and sends)")
        self.assertEqual(len(self.fake.requests), 1)

    def test_a_file_nested_past_the_depth_bound_is_refused_in_one_line_naming_the_bound_with_no_traceback_and_nothing_sent(self):
        """The depth rule is the verb's own (the fork review of the second round, 2026-09-18): a file nested deeper than
        MAX_DEPTH (32) is refused before any check walks it, in one stderr line that names the file's depth and the bound,
        exit 1, nothing sent, on every Python. Before the bound the verb let the walks decide by running out of stack. The
        reach of each component, the deepest chain that passes with one frame on the stack at entry, bisected at the closing
        check (2026-09-19) over a dict chain and a list chain on the local builds: the walks (check_document) 989 on 3.10 and
        3.11 and 992 on 3.12 to 3.14t; the fold 995 and 997 over a dict chain, and over a LIST chain 497 on 3.10 and 3.11,
        where it spends two frames per level, and 997 from 3.12; the parser 992 to 994 on 3.10 and 3.11, 9,994 to 9,998 on
        3.12 and 3.13, about 40,100 on this box's 3.14.6 and about 37,240 on its 3.14.6t (both moving between runs), and past
        100,000 on CI's 3.14t runner; the writer 992 to 994 on 3.10 to 3.12, 9,997 on 3.13, and on 3.14 and 3.14t 28,971 to
        37,241 over a dict chain and past 40,000 over a list chain. The parser's reach differs by orders of magnitude between
        builds, and the writer's from 3.13 on; the walks and the fold stay under 1,000 everywhere, at least fifteen times the
        bound, and CI's 3.14t cell alone admitted a 100,000-level document every other cell's parser refused as not strict
        JSON, so the walks overflowed there and nowhere else (the comment at MAX_DEPTH carries the table). A bound derived
        from the interpreter's limit would sit within a few frames of the walks' reach and would have to follow the fold's
        list reach on 3.10 and 3.11, so it would move with the build; the bound is a fixed number well inside every build.
        The three documents
        here are fixed: 33 levels, one past the bound, refused; 32, at the bound,
        sent; and the 100000-level file in the case beside this one meets whichever refusal its build's parser leaves it:
        a parser that gives up on the document refuses it as not strict JSON, one that admits it hands it to the depth
        bound, and both are refusals by kind."""
        base = ["--yes", "--receiver", self.fake.url]
        deep = os.path.join(self.xdg, "deep.json")
        with open(deep, "w") as fh:
            fh.write(_nested(33))                    # the literals, not MAX_DEPTH: a change to the bound is made here on purpose
        r = self._refused(_run([deep] + base, self.state), 1, "refused: %s is nested 33 levels deep and this verb takes at most 32; nothing sent" % deep)
        self.assertEqual(r.stderr, "romp perf upload: refused: %s is nested 33 levels deep and this verb takes at most 32; nothing sent\n" % deep)
        self.assertNotIn("Recursion", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.stdout, "", "refused before the summary line")
        self.assertEqual(self.fake.requests, [])
        with open(deep, "rb") as fh:
            doc = pu.strict_loads(fh.read())
        self.assertIsInstance(doc, dict, "the parser admits it: the depth rule, not the parser, refused it")
        self.assertEqual(pu.nesting_depth(doc), 33, "one past the bound, by the verb's own count")
        self.assertEqual(pu.MAX_DEPTH, 32)
        with open(deep, "w") as fh:
            fh.write(_nested(32))
        r = _run([deep] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr + " (at the bound the file takes the ordinary path)")
        self.assertEqual(len(self.fake.requests), 1)

    def test_a_setting_file_that_is_not_utf8_text_is_refused_naming_the_file_and_never_its_bytes(self):
        os.makedirs(os.path.join(self.home, ".config", "romp"))
        with open(os.path.join(self.home, ".config", "romp", "perf-receiver"), "wb") as fh:
            fh.write(b"https://receiver.example/\xff\xfe\n")
        r = self._refused(_run([self.file, "--yes"], self.state, home=self.home), 2,
                          "refused: the receiver address from ~/.config/romp/perf-receiver is not an https URL", "nothing sent")
        self.assertEqual(r.stdout, "")
        self.assertNotIn("receiver.example", r.stderr)
        self.assertNotIn("codec", r.stderr)
        self.assertEqual(self.fake.requests, [])

    def test_off_a_terminal_without_yes_the_verb_refuses_after_the_summary_line_and_dials_nothing(self):
        r = self._refused(_run([self.file, "--receiver", self.fake.url], self.state), 2, "refused: not on a terminal", "pass --yes",
                          "the form an agent uses", "no setting or variable stands in for it", "nothing sent")
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (self.file, len(self.data), self.fake.url))
        self.assertEqual(self.fake.requests, [])

    def test_no_environment_variable_stands_in_for_yes(self):
        tempting = {k: "1" for k in ("ROMP_PERF_UPLOAD_YES", "ROMP_PERF_YES", "ROMP_YES", "ROMP_UPLOAD", "ROMP_PERF_UPLOAD", "YES",
                                    "ASSUME_YES", "CI", "NONINTERACTIVE", "ROMP_PERF_RECEIVER_YES", "ROMP_NO_PROMPT")}
        r = self._refused(_run([self.file, "--receiver", self.fake.url], self.state, extra=tempting), 2, "pass --yes")
        self.assertEqual(self.fake.requests, [])
        # the census: the module's own environment reads name one variable, the receiver's address
        with open(os.path.join(ROOT, "cli", "perf_upload.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        constants = {t.id: node.value.value for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                     for t in node.targets if isinstance(t, ast.Name)}          # the module's own UPPER_CASE names

        def literal(node):
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.Name) and node.id in constants:
                return constants[node.id]
            return "<dynamic>"
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("get", "getenv", "pop", "setdefault"):
                base = node.func.value
                if (isinstance(base, ast.Attribute) and base.attr == "environ") or (isinstance(base, ast.Name) and base.id in ("env", "environ", "os")):
                    names.add(literal(node.args[0]) if node.args else "<dynamic>")
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "environ":
                names.add(literal(node.slice))
        self.assertEqual(names, {"ROMP_PERF_RECEIVER"})
        self.assertEqual({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == "getenv"}, set())
        # the environ-node walk, ADDED to the name census (which alone reads four call shapes: a membership test, `"X" in
        # os.environ`, has no call and passed it): every reference to `environ` in the module, an attribute or a bare
        # name, paired with the function holding it, is the one read in receiver_setting (by function name and count,
        # no line number: the function's body moves)
        refs = []

        def visit(node, fn):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn = node.name
            if (isinstance(node, ast.Attribute) and node.attr == "environ") or (isinstance(node, ast.Name) and node.id == "environ"):
                refs.append(fn)
            for child in ast.iter_child_nodes(node):
                visit(child, fn)
        visit(tree, "<module>")
        self.assertEqual(refs, ["receiver_setting"], "one environ reference, the receiver's address; confirmed holds none")
        # the executed check, whatever the syntax (a getattr, a future access form): the environment replaced by a mapping
        # that records every read, and confirmed off a terminal without --yes refuses having touched none of it
        touched = []
        with mock.patch.object(pu.os, "environ", _RecordingEnv(touched)):
            with self.assertRaises(pu.Refusal) as cm:
                pu.confirmed(False, stdin=io.StringIO(), stdout=io.StringIO())
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("pass --yes", str(cm.exception))
        self.assertEqual(touched, [], "the decision read nothing from the environment under any access form")

    def test_on_a_terminal_the_prompt_is_asked_and_y_or_yes_sends_while_anything_else_does_not(self):
        summary = "%s (%d bytes) to %s/v1/upload\n" % (self.file, len(self.data), self.fake.url)
        r = _run_tty([self.file, "--receiver", self.fake.url], self.state, "y\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, summary + "send it? [y/N] " + SUCCESS % (RECEIPT, 180))
        self.assertEqual(r.stderr, "")
        self.assertEqual(len(self.fake.requests), 1)
        r = _run_tty([self.file, "--receiver", self.fake.url], self.state, "YES\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.fake.requests), 2)
        for answer in ("n\n", "\n", "yes please\n", "y e s\n"):
            r = _run_tty([self.file, "--receiver", self.fake.url], self.state, answer)
            self.assertEqual(r.returncode, 2, answer)
            self.assertEqual(r.stdout, summary + "send it? [y/N] ", answer)
            self.assertEqual(r.stderr, "romp perf upload: nothing sent\n", answer)
        self.assertEqual(len(self.fake.requests), 2, "no other answer sent")
        r = _run_tty([self.file, "--yes", "--receiver", self.fake.url], self.state, "n\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("send it?", r.stdout, "--yes asks nothing, on a terminal too")
        self.assertEqual(len(self.fake.requests), 3)

    def test_no_proxy_variable_diverts_the_request(self):
        dead = "http://127.0.0.1:%d" % _free_port()
        proxies = {k: dead for k in ("http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")}
        proxies["no_proxy"] = proxies["NO_PROXY"] = ""
        r = _run([self.file, "--yes", "--receiver", self.fake.url], self.state, extra=proxies)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.fake.requests), 1, "the configured address was dialled, not the proxy")
        self.assertEqual(self.fake.requests[0][0], "POST /v1/upload HTTP/1.1", "origin form, not the absolute form a proxy is sent")

    def test_an_https_address_at_a_plaintext_receiver_is_refused_by_its_ssl_error_class_with_no_cleartext_retry(self):
        """An https address is dialled as https and nothing else. Against a receiver that speaks plain HTTP the TLS
        handshake fails and the verb refuses by the error's class alone: an SSLError, or the SSLEOFError a server that
        closes first leaves behind, so the class is pinned by its shape and not its exact name (the suite runs on five
        interpreters and two platforms). The fake's log is the substance: a retry in the clear would leave one plaintext
        request there whose body is the export, and there must be none. This case alone cannot see verification turned
        off (with it off and no retry the same dial still ends in an SSL error); the census beside it does."""
        r = _run([self.file, "--yes", "--receiver", "https://127.0.0.1:%d" % self.fake.port], self.state)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertRegex(r.stderr, r"^romp perf upload: refused: no answer from the receiver \((SSL[A-Za-z]*Error)\); no receipt\n$")
        self.assertEqual(r.stdout, "%s (%d bytes) to https://127.0.0.1:%d/v1/upload\n" % (self.file, len(self.data), self.fake.port))
        self.assertEqual(self.fake.requests, [], "no cleartext request reached the receiver: an https address is never retried as http")

    def test_the_module_uses_urllibs_default_tls_context_and_nothing_weakens_it(self):
        """Two pins on the same property, beside the https case above. The CENSUS over the transport module's text: disabling
        certificate verification needs a context object from somewhere, and the module has none. No import of ssl, no
        `context=` keyword at any call (the default HTTPSHandler and HTTPSConnection build the verified context themselves
        when none is passed, so the deadline handlers pass none), no attribute that would loosen one, no bare name ssl. The
        consent census (test_no_environment_variable_stands_in_for_yes) already collects every environ subscript, a
        PYTHONHTTPSVERIFY write among them. Then the EXECUTED pin (the upload's third review round, 2026-09-18): a census
        cannot catch a weakening spelled in a way it does not enumerate, and three mutants, a context built through a
        computed attribute name, a sibling module's helper passing a loosened context through **kwargs, and a setattr on
        the connection's own context with no context keyword anywhere, each left the whole suite green while accepting a
        self-signed and a plaintext receiver. So the connection the handshake actually uses is recorded, and its context
        is read: verification required and the hostname checked. The plaintext receiver suffices, since the context is
        built when the connection is, before any peer is spoken to."""
        with open(os.path.join(ROOT, "cli", "perf_upload.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        imported = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        imported += [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertEqual([m for m in imported if m == "ssl" or m.startswith("ssl.")], [], imported)
        self.assertNotIn("context", {kw.arg for n in ast.walk(tree) if isinstance(n, ast.Call) for kw in n.keywords})
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertEqual(attrs & {"check_hostname", "verify_mode", "_create_unverified_context", "_create_default_https_context",
                                  "load_verify_locations", "wrap_socket", "SSLContext", "set_ciphers", "minimum_version"}, set())
        self.assertEqual({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == "ssl"}, set())
        # the executed pin: record the HTTPS connection at handshake time and read the context it verifies with
        recorded = []
        original = pu._DeadlineHTTPSConnection.connect

        def record(conn):
            recorded.append(conn)
            return original(conn)
        with mock.patch.object(pu._DeadlineHTTPSConnection, "connect", record):
            with self.assertRaises(pu.Refusal):                 # the plaintext receiver: the handshake fails by its SSL error class
                pu.post("https://127.0.0.1:%d/v1/upload" % self.fake.port, b"{}")
        self.assertEqual(len(recorded), 1, "one https connection was made")
        # _context is a PRIVATE http.client attribute (HTTPSConnection.__init__ stores the context it will wrap the socket
        # with, the library's default verified one when none was passed), confirmed stable across 3.10 to 3.14; it is read
        # here because the executed property is worth more than the guarantee of a public name
        self.assertEqual(recorded[0]._context.verify_mode, ssl.CERT_REQUIRED, "certificate verification is required")
        self.assertIs(recorded[0]._context.check_hostname, True, "and the hostname is checked")
        self.assertEqual(self.fake.requests, [], "nothing reached the receiver in the clear")

    def test_a_refused_run_a_failed_send_and_a_successful_send_leave_no_file_behind_and_change_none(self):
        """The verb keeps no state: it writes nothing under the state root or HOME and touches no file beside the export,
        whatever the run's outcome (refused by the checks, a send that found no receiver, a 201 receipt), and the receipt
        is printed once and kept nowhere. Pinned by execution: a snapshot of every regular file under the test's tree (the
        state root, HOME and the export's own directory all live under it) is taken before the runs and compared whole
        after each, names and bytes, so a new entry, a removed one or a line appended to an existing file (a receipt log,
        a remembered receiver address) is caught. Nothing under the tree is excluded; the child's __pycache__ lands in
        cli/, outside it. Fails before: it is a pin; a mutant that appends one line per run under the state directory
        turns it red."""
        base = ["--yes", "--receiver", self.fake.url]
        edited = os.path.join(self.xdg, "edited.json")
        doc = json.loads(self.data)
        doc["perf"]["note"] = "/home/someone/code/notes-api/scratch.jsonl"           # refused by the walk: an absolute path
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        trees = list(dict.fromkeys((self.xdg, os.path.dirname(self.file))))           # the export's directory is the tree's root here

        def snapshot():
            out = {}
            for tree in trees:
                for root, _dirs, files in os.walk(tree):
                    for name in files:
                        path = os.path.join(root, name)
                        if os.path.isfile(path) and not os.path.islink(path):
                            with open(path, "rb") as fh:
                                out[os.path.relpath(path, self.xdg)] = fh.read()
            return out
        before = snapshot()
        self.assertIn(os.path.relpath(self.file, self.xdg), before)
        self.assertIn(os.path.join("romp", "session-hosts"), before)
        r = _run([edited] + base, self.state, home=self.home)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertEqual(snapshot(), before, "a refused run left nothing behind and changed nothing")
        r = _run([self.file, "--yes", "--receiver", "http://127.0.0.1:%d" % _free_port()], self.state, home=self.home)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("(ConnectionRefusedError)", r.stderr)
        self.assertEqual(snapshot(), before, "a send that found no receiver left nothing behind and changed nothing")
        r = _run([self.file] + base, self.state, home=self.home)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.fake.requests), 1)
        self.assertIn("receipt " + RECEIPT, r.stdout)
        self.assertEqual(snapshot(), before, "a successful send left nothing behind and changed nothing: the receipt is printed once and kept nowhere")

    def test_success_prints_the_receipt_and_the_retention_and_exits_0(self):
        self.fake.answer = (201, {}, json.dumps({"av": "skipped", "retention_days": 7, "receipt": RECEIPT.upper()}))
        r = _run([self.file, "--yes", "--receiver", self.fake.url], self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (self.file, len(self.data), self.fake.url) + SUCCESS % (RECEIPT.upper(), 7))
        self.assertEqual(r.stderr, "")
        self.assertEqual(len(self.fake.requests), 1)
        self.assertEqual(self.fake.requests[0][2], self.data, "the body is the file's bytes: a file as the export wrote it re-serialises to itself")


class StrictLoads(unittest.TestCase):
    """strict_loads as a unit (the closing re-run of 2026-09-19, its finding 6): the docstring promised no NaN or Infinity and
    the parser refused the two LITERALS alone, while a number written past the double's range (1e999) parsed to an infinity
    that passed the scan, the paste walk and the denylist walk, and only the fold belt in read_export, which nulls a
    non-finite number and so finds the block differing from its fold, kept it off the wire: a belt load-bearing beyond
    its stated purpose, which a later relaxation would not have known. The refusal now lives in the parser (parse_float,
    _finite_float), where the other strict-JSON rules are. The closing check (2026-09-19, HIGH 2) found the integer side of
    the same range open: parse_int was not hooked, so 10**400 parsed exactly and met math.isfinite in pp.public_uptime with a
    traceback; parse_int (pu._bounded_int) now refuses every integer literal no double can hold with the same NonFinite."""

    def test_an_integer_no_double_can_hold_is_not_strict_json_by_the_verbs_own_rule_whatever_its_length(self):
        """pu.strict_loads refuses an integer literal float() cannot hold as pu.NonFinite with the fixed text: 401 digits,
        its negative, the edge 2**1024 - 2**970 (309 digits, the first int float() refuses) and its negative, and 5001 digits,
        which is past the interpreter's int() digit limit (4300 by default) and would be the interpreter's ValueError, with
        its own text naming the limit, without pu._bounded_int's length pre-check, which refuses a literal over
        pu.DOUBLE_DIGITS digits (309, the digit count of the largest double, derived from sys.float_info) before int() runs.
        The refusal is the hook's, not json's: json.loads alone parses the 401-digit literal to 10**400. Within the double
        an int parses as before: 1 followed by 308 zeros, 2**1024 - 2**970 - 1 and int(sys.float_info.max), all 309 digits,
        so the edge is float()'s and not a digit count. Fails without parse_int (10**400 returned), without the pre-check
        (the 5001-digit case raises the interpreter's ValueError, not NonFinite), and with the pre-check at 100 digits (the
        309-digit values are refused)."""
        fmax, edge = int(sys.float_info.max), 2 ** 1024 - 2 ** 970
        for text, label in ((b'{"a": 1' + b"0" * 400 + b"}", "401 digits"), (b'{"a": -1' + b"0" * 400 + b"}", "-401 digits"),
                            (('{"a": %d}' % edge).encode(), "the edge"), (('{"a": %d}' % -edge).encode(), "the negative edge"),
                            (b'{"a": 1' + b"0" * 5000 + b"}", "5001 digits, past the interpreter's int() limit"),
                            (b'{"a": [1, {"b": 1' + b"0" * 400 + b"}]}", "nested")):
            with self.assertRaises(ValueError, msg=label) as cm:
                pu.strict_loads(text)
            self.assertIsInstance(cm.exception, pu.NonFinite, label)
            self.assertEqual(str(cm.exception), "not strict JSON: a number outside the finite range", label)
        self.assertEqual(pu.strict_loads(b'{"a": 1' + b"0" * 308 + b"}"), {"a": 10 ** 308}, "309 digits within the double: an int")
        self.assertEqual(pu.strict_loads(('{"a": %d}' % (edge - 1)).encode()), {"a": edge - 1})
        self.assertEqual(pu.strict_loads(('{"a": %d}' % fmax).encode()), {"a": fmax})
        self.assertEqual(pu.strict_loads(('{"a": %d}' % (fmax + 1)).encode()), {"a": fmax + 1}, "rounds to the largest double: held")
        self.assertEqual(pu.strict_loads(b'{"a": -12, "b": 0}'), {"a": -12, "b": 0})
        self.assertEqual(json.loads('{"a": 1' + "0" * 400 + "}")["a"], 10 ** 400, "json.loads alone parses it: the refusal is the hook's")
        self.assertEqual(pu.DOUBLE_DIGITS, 309)
        self.assertEqual(pu.DOUBLE_DIGITS, len(str(fmax)))
        self.assertEqual(pu._bounded_int("-7"), -7)
        with self.assertRaises(pu.NonFinite):
            pu._bounded_int("1" + "0" * 5000)          # by length, before int(): the interpreter's limit is never asked
        if sys.get_int_max_str_digits():                 # the outcome the pre-check preempts, under the interpreter's default limit
            with self.assertRaises(ValueError) as cm:
                json.loads('{"a": 1' + "0" * 5000 + "}")
            self.assertNotIsInstance(cm.exception, pu.NonFinite)

    def test_a_number_written_past_the_finite_range_is_not_strict_json_and_an_underflow_is_a_measurement(self):
        """1e999, -1e999 and 1E400 each raise pu.NonFinite, a ValueError, with the fixed text (no traceback out of the
        parser, nothing of the document in it; the class is what lets read_export name the reason in its refusal, as it does
        for a repeated key: a hand editor's validator calls 1e999 valid JSON, so the bare line told them nothing to act on);
        1e-999 parses to 0.0 (an underflow is a value, not an overflow); 1.5 and 1e5 parse as before; the literal NaN and
        Infinity still raise through parse_constant. Fails without parse_float: 1e999 returns inf; with a plain ValueError
        raised instead of NonFinite, the road rows get the bare strict-JSON line."""
        for text in (b'{"a": 1e999}', b'{"a": -1e999}', b'{"a": 1E400}'):
            with self.assertRaises(ValueError, msg=text) as cm:
                pu.strict_loads(text)
            self.assertIsInstance(cm.exception, pu.NonFinite, text)
            self.assertEqual(str(cm.exception), "not strict JSON: a number outside the finite range", text)
        self.assertEqual(pu.strict_loads(b'{"a": 1e-999}')["a"], 0.0, "an underflow is a measurement")
        self.assertEqual(pu.strict_loads(b'{"a": 1.5}'), {"a": 1.5})
        self.assertEqual(pu.strict_loads(b'{"a": 1e5}'), {"a": 100000.0})
        self.assertEqual(pu.strict_loads(b'{"a": 12}'), {"a": 12})
        for text, name in ((b'{"a": NaN}', "NaN"), (b'{"a": Infinity}', "Infinity"), (b'{"a": -Infinity}', "-Infinity")):
            with self.assertRaises(ValueError, msg=text) as cm:
                pu.strict_loads(text)
            self.assertEqual(str(cm.exception), "not strict JSON: " + name)


class DepthBound(unittest.TestCase):
    """The depth rule as a unit: nesting_depth's count (the root is 1, a leaf's depth its key path's length, a scalar 0),
    without recursion, so it measures a document the walks could not; the bound is 32, about four times the depth of a
    fresh export, which this module's export from the planted snapshot stays under with the same margin; and the
    RecursionError belt behind the bound refuses in one line naming the error's class, since no file reaches it by nesting
    alone, out of the checks and out of the writer alike. Two more: a RecursionError out of the PARSER is the strict-JSON
    refusal (strict_loads turns it into a ValueError with a fixed text), and the bound refuses BEFORE any check walks the
    document (check_document stubbed, never called)."""

    def test_nesting_depth_counts_containers_around_the_deepest_value_without_recursion(self):
        for doc, depth in (({}, 1), ([], 1), (1, 0), ("s", 0), ({"a": []}, 2), ({"a": [{"b": 1}]}, 3), ({"a": {"b": {}}, "c": 1}, 3),
                           ([[[]]], 3), ({"a": 1, "b": {"c": [1, {"d": None}]}}, 4)):
            self.assertEqual(pu.nesting_depth(doc), depth, repr(doc))
        for depth in (2, 20, 32, 33):
            self.assertEqual(pu.nesting_depth(pu.strict_loads(_nested(depth).encode("utf-8"))), depth)
        deep = 1
        for _ in range(5000):           # built as an object, not parsed: the parser's own reach differs by build and is not the point
            deep = [deep]
        self.assertEqual(pu.nesting_depth(deep), 5000, "an explicit stack, so a document the walks could not take is measured")
        self.assertEqual(pu.MAX_DEPTH, 32)

    def test_the_export_from_the_planted_snapshot_sits_inside_a_quarter_of_the_bound(self):
        xdg, state = _state_root()
        self.addCleanup(shutil.rmtree, xdg, True)
        with open(_export(xdg, state), "rb") as fh:
            depth = pu.nesting_depth(pu.strict_loads(fh.read()))
        self.assertGreaterEqual(depth, 3)
        self.assertLessEqual(depth, pu.MAX_DEPTH // 4, "a fresh export measured 7 on 2026-09-18; the bound is about four times that")

    def test_a_recursion_error_out_of_the_checks_is_the_one_line_belt_behind_the_bound(self):
        xdg, state = _state_root()
        self.addCleanup(shutil.rmtree, xdg, True)
        file = _export(xdg, state)
        with mock.patch.object(pu.pe, "check_document", side_effect=RecursionError("planted")):
            with self.assertRaises(pu.Refusal) as cm:
                pu.read_export(file, pu.pe.Path(state))
        self.assertEqual(str(cm.exception), "refused: %s could not be checked (RecursionError); nothing sent" % file)
        self.assertEqual(cm.exception.code, 1)
        self.assertNotIn("planted", str(cm.exception))

    def test_a_recursion_error_out_of_the_writer_is_the_same_one_line_belt(self):
        """The writer (pe.document_text, json's encoder) recurses one frame per level like the walks and the fold, and it ran
        after the belt's try, so a RecursionError out of it would have escaped read_export as a traceback; the belt's own
        comment promises one line whatever the stack looks like, so the writer runs inside the belt (the fourth review round,
        2026-09-19). What this case shows is that the belt catches a raise from the writer, demonstrated by a PLANTED raise: no
        document reaches that line by nesting. Measured at the closing check (2026-09-19) with MAX_DEPTH lifted, over dict and
        list chains under perf (one and two keys or elements per level) at every depth from 400 to 1,100 on 3.10 and 3.11 and
        to the parser's reach on 3.12 and 3.13, every RecursionError was raised inside the belt by the checks (or by the fold
        over list nesting on 3.10 and 3.11, whose reach there is 497), none by the writer and none escaped; the writer's own
        reach (992 to 994 on 3.10 to 3.12, 9,997 on 3.13, past 28,000 on 3.14 and 3.14t) is at or past the checks' (989 to
        992) on every build, so the fourth round's account of the writer overflowing first with the bound lifted did not
        reproduce. Fails before: RecursionError out of read_export, the writer outside the try."""
        xdg, state = _state_root()
        self.addCleanup(shutil.rmtree, xdg, True)
        file = _export(xdg, state)
        with mock.patch.object(pu.pe, "document_text", side_effect=RecursionError("planted")):
            with self.assertRaises(pu.Refusal) as cm:
                pu.read_export(file, pu.pe.Path(state))
        self.assertEqual(str(cm.exception), "refused: %s could not be checked (RecursionError); nothing sent" % file)
        self.assertEqual(cm.exception.code, 1)
        self.assertNotIn("planted", str(cm.exception))

    def test_a_recursion_error_out_of_the_parser_is_not_strict_json_and_never_a_traceback(self):
        """json raises RecursionError on a document nested past the parser's reach, on the builds where the C scanner gives up
        before the depth bound sees the document; strict_loads turns it into a ValueError with a fixed text, and read_export
        into the strict-JSON refusal, so the verb answers with one line and never a traceback whatever the build. Pinned by
        making json.loads raise: sys.setrecursionlimit is NOT the mechanism, because on 3.12 and later the C JSON scanner's
        reach is bounded by the thread's stack size and not by the recursion limit, so lowering the limit does not make the
        parser give up on any document (both refuters of the third review round, 2026-09-18)."""
        xdg, state = _state_root()
        self.addCleanup(shutil.rmtree, xdg, True)
        file = _export(xdg, state)
        with mock.patch.object(pu.json, "loads", side_effect=RecursionError("planted")):
            with self.assertRaises(ValueError) as cm:
                pu.strict_loads(b"{}")
            self.assertEqual(str(cm.exception), "not strict JSON: nested past the parser")
            self.assertNotIn("planted", str(cm.exception))
            self.assertNotIsInstance(cm.exception, RecursionError)
            with self.assertRaises(pu.Refusal) as cm:
                pu.read_export(file, pu.pe.Path(state))
        self.assertEqual(str(cm.exception), "refused: %s is not strict JSON; nothing sent" % file)
        self.assertEqual(cm.exception.code, 1)
        self.assertNotIn("planted", str(cm.exception))
        self.assertNotIn("Recursion", str(cm.exception))

    def test_the_depth_bound_refuses_before_any_check_walks_the_document(self):
        """The bound's whole point is ordering: the checks recurse one frame per level, so a document past the bound must be
        refused before any of them runs. Pinned by stubbing check_document, which every check runs through, and asserting
        it was never called for a 33-level file; the refusal names the file's depth and the bound. A pin on the refusal text
        alone would stay green if the gate moved below the checks (every existing case did, refuter-confirmed)."""
        xdg, state = _state_root()
        self.addCleanup(shutil.rmtree, xdg, True)
        deep = os.path.join(xdg, "deep.json")
        with open(deep, "w") as fh:
            fh.write(_nested(33))
        with mock.patch.object(pu.pe, "check_document", return_value=None) as stub, mock.patch.object(pu.pp, "fold") as fold:
            with self.assertRaises(pu.Refusal) as cm:
                pu.read_export(deep, pu.pe.Path(state))
        self.assertEqual(stub.call_count, 0, "no check walked the document: the bound refused first")
        self.assertEqual(fold.call_count, 0, "and the fold belt did not run either")
        self.assertEqual(str(cm.exception), "refused: %s is nested 33 levels deep and this verb takes at most 32; nothing sent" % deep)
        self.assertEqual(cm.exception.code, 1)


class FoldBelt(unittest.TestCase):
    """read_export's last step, as a unit: with the three checks stubbed to pass, the top level must be exactly what the
    export writes (TOP_LEVEL: an unlisted top-level block is refused naming it, a required key missing naming it, an envelope
    line off the export's spelling naming it, a block that is not a dict naming it) and the perf and usage blocks must equal
    their own folds (a block that differs is refused naming it); an export as written passes, with and without kernel_commit
    and usage. The value is never in the refusal."""

    def setUp(self):
        self.xdg, self.state = _state_root()
        self.addCleanup(shutil.rmtree, self.xdg, True)
        self.file = _export(self.xdg, self.state, usage=True, commit="0123456789abcdef0123456789abcdef01234567")
        with open(self.file, "rb") as fh:
            self.data = fh.read()
        self.edited = os.path.join(self.xdg, "edited.json")
        self.token = "zz-planted-token-past-thirty-two-chars-zz"

    def _write(self, doc):
        with open(self.edited, "w") as fh:
            json.dump(doc, fh)
        return self.edited

    def _refused(self, doc, line):
        with mock.patch.object(pu.pe, "check_document", return_value=None) as stub:
            with self.assertRaises(pu.Refusal) as cm:
                pu.read_export(self._write(doc), pu.pe.Path(self.state))
        self.assertEqual(stub.call_count, 1, "the checks ran first and passed (stubbed); the belt is what refused")
        self.assertEqual(str(cm.exception), "refused: %s %s; nothing sent" % (self.edited, line))
        self.assertEqual(cm.exception.code, 1)
        self.assertNotIn(self.token, str(cm.exception))
        return cm.exception

    def test_the_fold_belt_refuses_a_block_the_checks_passed(self):
        doc = json.loads(self.data)
        doc["usage"]["note"] = self.token                                   # a listed block that is not its own fold
        self._refused(doc, "is not the export's own public form (the usage block differs from its fold)")
        doc = json.loads(self.data)
        doc["perf"]["heap"]["note"] = self.token
        self._refused(doc, "is not the export's own public form (the perf block differs from its fold)")
        with mock.patch.object(pu.pe, "check_document", return_value=None):
            self.assertEqual(pu.read_export(self.file, pu.pe.Path(self.state)), self.data, "the export as written is its own fold")
            doc = json.loads(self.data)
            doc["usage"]["note"] = "fits-the-grammar"                        # a block the fold leaves as it is passes the belt
            self.assertEqual(json.loads(pu.read_export(self._write(doc), pu.pe.Path(self.state)))["usage"], doc["usage"])

    def test_the_top_level_is_exactly_what_the_export_writes(self):
        """The allowlist (the upload's third review round, 2026-09-18). Before it, a top-level block the export does not write
        passed the belt whenever it was its own fold, which a foreign block at the root is (fold's rules are anchored at
        the block root): the clause that said a block the fold leaves as it is passes now says an unlisted block is refused
        naming it. The export's envelope pin in tests/test_perf_export.py is unchanged by this."""
        self.assertEqual(pu.TOP_LEVEL, {"schema": True, "exported_at": True, "perf": True, "kernel_commit": False, "usage": False})
        self.assertEqual(pu.FOLDED, ("perf", "usage"))
        self.assertEqual(pu.pe.ENVELOPE_KEYS, ("schema", "exported_at", "kernel_commit"))
        doc = json.loads(self.data)
        self.assertEqual(sorted(doc), ["exported_at", "kernel_commit", "perf", "schema", "usage"], "a fresh export with every optional key")
        doc["extra"] = {"note": "fits-the-grammar", "count": 1}              # its own fold, and refused all the same
        self.assertEqual(pu.pp.fold(doc["extra"]), doc["extra"])
        self._refused(doc, "is not the export's own shape (a top-level extra block the export does not write)")
        doc = json.loads(self.data)
        doc["judge"] = {"child": {"failures": {"first": self.token}}}         # denied under perf, not at the root: a fold of itself
        self._refused(doc, "is not the export's own shape (a top-level judge block the export does not write)")
        for missing in ("exported_at", "perf"):
            doc = json.loads(self.data)
            del doc[missing]
            self._refused(doc, "is not the export's own shape (no top-level %s)" % missing)
        for value in ("2026-09-18T12:00:00Z", "2026-09-18 12:00Z", "2026-09-18T12:00", 1700000000, None, ["2026-09-18T12:00Z"]):
            doc = json.loads(self.data)
            doc["exported_at"] = value
            self._refused(doc, "is not the export's own shape (the exported_at line is not what the export writes)")
        for value in ("ABCDEF0123", "abcdef", "0123456789abc", "0123456789abcdef0123456789abcdef01234567", {"sha": "0123456789ab"}, 1234567, ""):
            doc = json.loads(self.data)
            doc["kernel_commit"] = value
            self._refused(doc, "is not the export's own shape (the kernel_commit line is not what the export writes)")
        for block, value in (("perf", [1]), ("perf", "perf"), ("usage", [self.token]), ("usage", 1)):
            doc = json.loads(self.data)
            doc[block] = value
            self._refused(doc, "is not the export's own shape (the %s block is not what the export writes)" % block)
        with mock.patch.object(pu.pe, "check_document", return_value=None):
            for value in ("0123456", "0123456789ab", "abcdef0"):            # 7 to 12 lowercase hex: what kernel_commit() writes
                doc = json.loads(self.data)
                doc["kernel_commit"] = value
                self.assertEqual(json.loads(pu.read_export(self._write(doc), pu.pe.Path(self.state)))["kernel_commit"], value)
            for drop in ((), ("kernel_commit",), ("usage",), ("kernel_commit", "usage")):
                doc = json.loads(self.data)
                for k in drop:
                    del doc[k]
                self.assertEqual(sorted(json.loads(pu.read_export(self._write(doc), pu.pe.Path(self.state)))), sorted(doc),
                                 "the optional keys are optional: %r" % (drop,))


class Answers(unittest.TestCase):
    """Every answer but the one accepted is a refusal with a fixed line: the status code alone for a status other
    than 201 (a redirect among them, never followed), the shape line alone for a 201 whose body is not exactly the
    receipt, the error class alone when no answer came. The fake plants a marker in every body; it never appears."""

    @classmethod
    def setUpClass(cls):
        cls.fake = Receiver()
        cls.xdg, cls.state = _state_root()
        cls.file = _export(cls.xdg, cls.state)
        with open(cls.file, "rb") as fh:
            cls.data = fh.read()
        cls.summary = "%s (%d bytes) to %s/v1/upload\n" % (cls.file, len(cls.data), cls.fake.url)

    @classmethod
    def tearDownClass(cls):
        cls.fake.stop()
        shutil.rmtree(cls.xdg, True)

    def setUp(self):
        self.fake.reset()

    def _refused(self, line, url=None):
        r = _run([self.file, "--yes", "--receiver", url or self.fake.url], self.state)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (self.file, len(self.data), url or self.fake.url))
        self.assertEqual(r.stderr, "romp perf upload: %s\n" % line)
        self.assertNotIn(MARKER, r.stdout + r.stderr)
        return r

    def test_a_status_other_than_201_is_refused_by_its_code_alone(self):
        good = json.dumps({"receipt": RECEIPT, "retention_days": 180, "av": "ok"})
        for status, body in ((200, good), (202, good), (204, ""), (400, MARKER), (413, "<html>%s</html>" % MARKER), (422, json.dumps({"error": MARKER})),
                             (429, MARKER), (500, "<html><body>%s</body></html>" % MARKER), (503, MARKER)):
            self.fake.answer = (status, {}, body)
            self._refused("refused: the receiver answered HTTP %d where the 201 receipt was expected; no receipt" % status)
            self.assertEqual(len(self.fake.requests), 1, status)
            self.fake.requests.clear()

    def test_a_redirect_is_refused_by_its_code_and_never_followed(self):
        for status in (301, 302, 303, 307, 308):
            self.fake.answer = (status, {"Location": self.fake.url + "/elsewhere"}, MARKER)
            self._refused("refused: the receiver answered HTTP %d where the 201 receipt was expected; no receipt" % status)
            self.assertEqual([line for line, _h, _b in self.fake.requests], ["POST /v1/upload HTTP/1.1"], "one request, the redirect target never dialled")
            self.fake.requests.clear()

    def test_a_redirect_whose_location_urllib_cannot_parse_is_refused_by_its_code_alone_and_the_text_never_shown(self):
        # HTTPRedirectHandler.http_error_30x parse the Location before they ask redirect_request; a bracketed host makes
        # urlsplit raise a ValueError quoting the receiver's text, so the handler must never reach that parse
        for location in ("http://[%s your export leaked see pastebin.example]/x" % MARKER, "http://[x", "http://[::1]:99999/", "http://[::1]/" + MARKER):
            for status in (301, 302, 303, 307, 308):
                self.fake.answer = (status, {"Location": location}, MARKER)
                r = self._refused("refused: the receiver answered HTTP %d where the 201 receipt was expected; no receipt" % status)
                self.assertNotIn("Traceback", r.stderr)
                self.assertNotIn("pastebin", r.stderr)
                self.assertEqual([line for line, _h, _b in self.fake.requests], ["POST /v1/upload HTTP/1.1"], (location, status))
                self.fake.requests.clear()

    def test_a_201_body_nested_past_the_parser_is_refused_by_the_shape_line_alone(self):
        self.fake.answer = (201, {}, "[" * 30000 + "]" * 30000)            # 60,000 bytes: under the cap, past the parser's reach
        r = self._refused(pu.NOT_THE_SHAPE)
        self.assertNotIn("Recursion", r.stderr)
        with self.assertRaises(pu.Refusal) as cm:
            pu.receipt(201, b"[" * 30000 + b"]" * 30000)
        self.assertEqual(str(cm.exception), pu.NOT_THE_SHAPE)

    def test_a_201_body_over_the_cap_is_refused_and_one_under_it_is_read_whole(self):
        ok = json.dumps({"receipt": RECEIPT, "retention_days": 180, "av": "ok"})
        self.fake.answer = (201, {}, ok + " " * (64 * 1024))               # the receipt, then padding past the cap: not the shape
        self._refused(pu.NOT_THE_SHAPE)
        self.fake.answer = (201, {}, ok + " " * 100)                       # the receipt, then padding under the cap: the receipt
        r = _run([self.file, "--yes", "--receiver", self.fake.url], self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, self.summary + SUCCESS % (RECEIPT, 180))
        body = ok.encode()
        self.assertEqual(pu.receipt(201, body + b" " * (pu.ANSWER_MAX - len(body))), (RECEIPT, 180, "ok"), "exactly the cap is read whole")
        with self.assertRaises(pu.Refusal) as cm:
            pu.receipt(201, body + b" " * (pu.ANSWER_MAX - len(body) + 1))
        self.assertEqual(str(cm.exception), pu.NOT_THE_SHAPE)
        self.assertEqual(pu.ANSWER_MAX, 64 * 1024)

    def test_post_reads_at_most_the_cap_plus_one_byte_of_a_201_body_however_long_the_receiver_makes_it(self):
        # the resource bound under the shape rule: a 201 body is read to ANSWER_MAX + 1 and no further, so a receiver
        # answering with megabytes costs that much memory and no more; the extra byte is what marks it over the cap
        asked = []

        class Response:
            status = 201

            def read(self, n=-1):
                asked.append(n)
                return b" " * (n if n is not None and n >= 0 else 8 * 1024 * 1024)

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        with mock.patch.object(urllib.request.OpenerDirector, "open", return_value=Response()):
            status, body = pu.post(self.fake.url + "/v1/upload", b"{}")
        self.assertEqual((status, len(body)), (201, pu.ANSWER_MAX + 1))
        self.assertEqual(asked, [pu.ANSWER_MAX + 1], "one bounded read, never an unbounded one")
        Response.status = 500
        with mock.patch.object(urllib.request.OpenerDirector, "open", return_value=Response()):
            status, body = pu.post(self.fake.url + "/v1/upload", b"{}")
        self.assertEqual((status, body), (500, b""), "another status is not read at all")
        self.assertEqual(asked, [pu.ANSWER_MAX + 1])

    def test_the_verb_sets_content_type_content_length_and_user_agent_and_the_client_adds_the_rest(self):
        """The attribution the module docstring and the reference make (three headers from the verb, three from the HTTP
        client) is pinned where it is decided, at the Request's construction, not on the wire: the wire shows six headers
        whichever side supplied Content-Length (the enumeration test already sees it there). With the verb passing the
        body's own length, a body that is not bytes fails at the call instead of going out chunked with no length.
        Fails before: the verb passed two headers and left Content-Length to the client."""
        real, constructed = urllib.request.Request, []

        def recording(*a, **kw):
            constructed.append(kw)
            return real(*a, **kw)
        with mock.patch.object(pu.urllib.request, "Request", new=recording):
            status, body = pu.post(self.fake.url + "/v1/upload", b"{}")
        self.assertEqual(status, 201)
        self.assertEqual([kw.get("headers") for kw in constructed],
                         [{"Content-Type": "application/json", "Content-Length": "2", "User-Agent": pu.USER_AGENT}])
        self.assertEqual(len(self.fake.requests), 1)
        line, headers, wire_body = self.fake.requests[0]
        self.assertEqual(wire_body, b"{}")
        self.assertEqual(sorted(dict(headers)), sorted(Enumeration.FIXED_HEADERS), "six headers on the wire, as before")
        self.assertEqual(dict(headers)["Content-Length"], "2")

    def test_an_error_of_any_other_class_while_dialling_is_refused_by_its_class_alone(self):
        # the belt under the specific clauses: whatever else the client raises, the class and never the message
        with mock.patch.object(urllib.request.OpenerDirector, "open", side_effect=ValueError(MARKER)):
            with self.assertRaises(pu.Refusal) as cm:
                pu.post(self.fake.url + "/v1/upload", b"{}")
        self.assertEqual(str(cm.exception), "refused: no answer from the receiver (ValueError); no receipt")
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(self.fake.requests, [])

    def test_a_201_whose_body_is_not_exactly_the_receipt_is_refused_by_the_shape_line_alone(self):
        ok = {"receipt": RECEIPT, "retention_days": 180, "av": "ok"}
        bodies = [MARKER, "<html>%s</html>" % MARKER, "", json.dumps([ok]), json.dumps(RECEIPT), json.dumps(None),
                  json.dumps({**ok, "note": MARKER}), json.dumps({**ok, "url": "https://receiver.example/" + MARKER}),
                  json.dumps({k: v for k, v in ok.items() if k != "av"}), json.dumps({k: v for k, v in ok.items() if k != "receipt"}),
                  json.dumps({k: v for k, v in ok.items() if k != "retention_days"}), json.dumps({}),
                  json.dumps({**ok, "receipt": 42}), json.dumps({**ok, "receipt": None}), json.dumps({**ok, "receipt": MARKER}),
                  json.dumps({**ok, "receipt": "3f2a9c1e-7b4d-1e6a-9c1f-2d3e4f5a6b7c"}),        # version 1
                  json.dumps({**ok, "receipt": "3f2a9c1e-7b4d-4e6a-1c1f-2d3e4f5a6b7c"}),        # a wrong variant nibble
                  json.dumps({**ok, "receipt": RECEIPT + "x"}), json.dumps({**ok, "receipt": RECEIPT[:-1]}),
                  json.dumps({**ok, "receipt": "urn:uuid:" + RECEIPT}), json.dumps({**ok, "receipt": RECEIPT.replace("-", "")}),
                  json.dumps({**ok, "retention_days": True}), json.dumps({**ok, "retention_days": 180.0}), json.dumps({**ok, "retention_days": "180"}),
                  json.dumps({**ok, "retention_days": -1}), json.dumps({**ok, "retention_days": None}),
                  json.dumps({**ok, "av": "other"}), json.dumps({**ok, "av": "OK"}), json.dumps({**ok, "av": 1}), json.dumps({**ok, "av": None}),
                  json.dumps({**ok, "av": ["ok"]}),
                  '{"receipt": "%s", "retention_days": NaN, "av": "ok"}' % RECEIPT,
                  '{"receipt": "%s", "retention_days": 1e999, "av": "ok"}' % RECEIPT,        # an overflow: the parser refuses it before the int check
                  # an integer no double can hold, 401 digits, and one past the interpreter's int() limit, 5001: NonFinite through
                  # parse_int (pu._bounded_int), the shape line here; before 2026-09-19 the 401-digit one passed the int check and
                  # the success line printed it 401 digits wide (the closing check's HIGH 2 audit, receipt())
                  '{"receipt": "%s", "retention_days": 1%s, "av": "ok"}' % (RECEIPT, "0" * 400),
                  '{"receipt": "%s", "retention_days": 1%s, "av": "ok"}' % (RECEIPT, "0" * 5000),
                  json.dumps(ok) + json.dumps(ok), json.dumps(ok)[:-1], json.dumps({**ok, "note": "x" * (64 * 1024)}),
                  '{"receipt": "%s", "receipt": "%s", "retention_days": 180, "av": "ok"}' % (MARKER, RECEIPT),      # a repeated key
                  '{"receipt": "%s", "retention_days": 1, "retention_days": 180, "av": "ok"}' % RECEIPT]
        for body in bodies:
            self.fake.answer = (201, {}, body)
            self._refused(pu.NOT_THE_SHAPE)
            self.assertEqual(len(self.fake.requests), 1, body[:60])
            self.fake.requests.clear()
        self.fake.answer = (201, {}, json.dumps(ok))
        r = _run([self.file, "--yes", "--receiver", self.fake.url], self.state)
        self.assertEqual(r.returncode, 0, "the exact shape, in any key order, is the one accepted")
        self.fake.answer = (201, {}, json.dumps({"av": "skipped", "retention_days": 0, "receipt": RECEIPT}))
        r = _run([self.file, "--yes", "--receiver", self.fake.url], self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, self.summary + SUCCESS % (RECEIPT, 0))

    def test_the_shape_test_as_a_unit(self):
        ok = {"receipt": RECEIPT, "retention_days": 180, "av": "skipped"}
        self.assertEqual(pu.receipt(201, json.dumps(ok).encode()), (RECEIPT, 180, "skipped"))
        with self.assertRaises(pu.Refusal) as cm:
            pu.receipt(200, json.dumps(ok).encode())
        self.assertEqual(str(cm.exception), "refused: the receiver answered HTTP 200 where the 201 receipt was expected; no receipt")
        self.assertEqual(cm.exception.code, 1)
        for body in (b"", b"\xff", b"{", json.dumps({**ok, "x": 1}).encode(), b"x" * (pu.ANSWER_MAX + 1)):
            with self.assertRaises(pu.Refusal) as cm:
                pu.receipt(201, body)
            self.assertEqual(str(cm.exception), pu.NOT_THE_SHAPE, body[:20])
            self.assertEqual(cm.exception.code, 1)

    def test_no_answer_is_refused_by_the_error_class_alone(self):
        self._refused("refused: no answer from the receiver (ConnectionRefusedError); no receipt", url="http://127.0.0.1:%d" % _free_port())
        self.assertEqual(self.fake.requests, [])
        self.fake.hang_up = True
        r = self._refused("refused: no answer from the receiver (RemoteDisconnected); no receipt")
        self.assertNotIn("Remote end closed", r.stderr, "the class, never the message")
        self.assertEqual(len(self.fake.requests), 1)

    def test_the_timeout_is_a_deadline_over_the_whole_exchange_and_a_receiver_answering_in_pieces_cannot_hold_it_open(self):
        """The documented thirty seconds was a per-operation socket timeout: every read waited up to the limit and started
        over, so a receiver answering in pieces each under it held an unattended --yes run open for as long as it liked
        (the refuter measured 60 s and a 201 at the real value). The bound is now a deadline over the whole exchange, a
        timer that shuts the connection's socket down when the budget runs out, so it covers the header phase inside
        urllib, which a budgeted read after open() cannot, as well as the body. Two legs against a raw-socket receiver
        with TIMEOUT_S at 1.0 and every gap 0.6 s, the total over the budget in both: the status line and headers at
        once and the receipt body in two pieces; the status line, the headers and the body in three pieces (the header
        phase alone). Each ends in the fixed TimeoutError line, code 1, after at least the budget and under about twice
        it, whatever the client made of the shut socket (a truncated body, a short header set). The control leg, the same
        drip with the total under the budget, is accepted as 201 with the receipt body whole. Fails before: both legs
        returned 201 after the total elapsed."""
        ok = json.dumps({"receipt": RECEIPT, "retention_days": 180, "av": "ok"}).encode()
        head = b"HTTP/1.1 201 Created\r\n"
        headers = b"Content-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % len(ok)
        body_legs = ([head + headers + ok[:20], ok[20:]],                 # the body in two pieces
                     [head, headers, ok])                               # the status line, the headers, the body
        for pieces in body_legs:
            fake = DripReceiver(pieces, gap=0.6)
            self.addCleanup(fake.stop)
            started = time.monotonic()
            with mock.patch.object(pu, "TIMEOUT_S", 1.0):
                with self.assertRaises(pu.Refusal) as cm:
                    pu.post(fake.url + "/v1/upload", b"{}")
            elapsed = time.monotonic() - started
            self.assertEqual(str(cm.exception), "refused: no answer from the receiver (TimeoutError); no receipt", pieces[0][:12])
            self.assertEqual(cm.exception.code, 1)
            self.assertGreaterEqual(elapsed, 1.0, "not before the budget")
            self.assertLess(elapsed, 2.0, "and not long after it: %.2f s for %d pieces at 0.6 s gaps (%.1f s total)" % (elapsed, len(pieces), 0.6 * len(pieces)))
            self.assertEqual(len(fake.requests), 1, "the one request reached the receiver whole")
            self.assertEqual(fake.requests[0][1], b"{}")
        fake = DripReceiver([head, headers, ok[:20], ok[20:]], gap=0.15)      # the same drip, the total under the budget
        self.addCleanup(fake.stop)
        with mock.patch.object(pu, "TIMEOUT_S", 1.0):
            self.assertEqual(pu.post(fake.url + "/v1/upload", b"{}"), (201, ok), "a slow but timely receiver is accepted, the body whole")
        self.assertEqual(pu.receipt(201, ok), (RECEIPT, 180, "ok"))

    def test_the_connections_own_timeout_is_cut_to_the_time_the_deadline_has_left(self):
        """_DeadlineConnection.connect cuts the connection's timeout, which bounds the connect and the handshake, the phases
        before a socket exists to arm the deadline on, to the time the deadline has left; a unit pin, since an `if False:`
        over the two cut lines left every other case green (the upload's third review round, 2026-09-18). A listening
        loopback socket, a 30 s connection timeout and a deadline half a second away: after connect() the timeout is the
        remaining half second at most, and above zero (a zero would make the socket non-blocking)."""
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        self.addCleanup(srv.close)
        deadline = pu._Deadline(0.5)
        self.addCleanup(deadline.cancel)                    # nothing fires after the assertions
        conn = pu._DeadlineHTTPConnection("127.0.0.1", srv.getsockname()[1], timeout=30, deadline=deadline)
        self.addCleanup(conn.close)
        conn.connect()
        self.assertGreater(conn.timeout, 0)
        self.assertLessEqual(conn.timeout, 0.5, "the connection's own timeout is the time the deadline has left, not the 30 s it was given")
        self.assertIsNotNone(deadline._timer, "and the deadline is armed on the socket once the connection is up")

    def test_a_timeout_is_refused_by_its_class_alone_after_the_fixed_wait(self):
        self.fake.delay = 1.5
        err, out = io.StringIO(), io.StringIO()
        probes = [("hostname", "testhost"), ("username", "tester"), ("home directory", HOME)]
        with mock.patch.object(pu, "TIMEOUT_S", 0.3), mock.patch.object(pp, "machine_probes", return_value=probes), \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            code = pu.main([self.file, "--yes", "--receiver", self.fake.url], stdin=io.StringIO())
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), self.summary)
        self.assertEqual(err.getvalue(), "romp perf upload: refused: no answer from the receiver (TimeoutError); no receipt\n")
        self.assertEqual(pu.TIMEOUT_S, 30, "the verb's own timeout is thirty seconds")
        time.sleep(1.5)                               # let the handler finish before the fake is reset


class Enumeration(unittest.TestCase):
    """Exactly what the verb sends, read from a recording receiver and not from the code. The export is written
    through bin/romp from the planted snapshot (a home path, a session id, a hostname, a glossary term and a
    client's app string in every place the export folds or drops them), the upload runs through bin/romp against
    it with --yes, and the one request the receiver saw is compared whole: the request line, the header set
    (exactly six: Host, User-Agent, Accept-Encoding, Content-Type, Content-Length, Connection), the body bytes
    against the file's, which a fresh export's re-serialisation equals. Both runs are hermetic: an empty HOME under the test's tree, USER and LOGNAME `tester`,
    no ROMP_* variable, a dead kernel port; the machine strings the two scans read are the same for both."""
    FIXED_HEADERS = ("Host", "User-Agent", "Accept-Encoding", "Content-Type", "Content-Length", "Connection")

    def test_the_one_request_is_the_file_under_six_fixed_headers_and_names_nothing_of_the_machine(self):
        fake = Receiver()
        self.addCleanup(fake.stop)
        xdg, state = _state_root()
        self.addCleanup(shutil.rmtree, xdg, True)
        home = os.path.join(xdg, "home")
        os.makedirs(home)
        src, out = os.path.join(xdg, "snap.json"), os.path.join(xdg, "export.json")
        with open(src, "w") as fh:
            json.dump(planted_snapshot(), fh)
        env = _env(state, home=home)
        r = subprocess.run([ROMP, "perf", "export", "--public", "--from", src, "--out", out], capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, "rb") as fh:
            data = fh.read()
        doc = json.loads(data)
        self.assertEqual(doc["schema"], "romp-perf-export/1")
        self.assertEqual(pp.paste_problems(doc, planted=PLANTED, skip=("schema",), under=("perf",)), [], "the export carries no plant")
        self.assertEqual(doc["perf"]["pusher"]["cycles"], 100, "and keeps the counters")

        r = subprocess.run([ROMP, "perf", "upload", out, "--yes", "--receiver", fake.url], capture_output=True, text=True, timeout=60,
                           env=env, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (out, len(data), fake.url) + SUCCESS % (RECEIPT, 180))
        self.assertEqual(r.stderr, "")

        self.assertEqual(len(fake.requests), 1, "one POST, no other request")
        line, headers, body = fake.requests[0]
        self.assertEqual(line, "POST /v1/upload HTTP/1.1")
        self.assertEqual(len(headers), len(self.FIXED_HEADERS), headers)
        self.assertEqual(dict(headers), {"Host": "127.0.0.1:%d" % fake.port, "User-Agent": "romp-perf-upload/1", "Accept-Encoding": "identity",
                                         "Content-Type": "application/json", "Content-Length": str(len(data)), "Connection": "close"})
        self.assertEqual(body, data, "the body is the file's bytes: a file as the export wrote it re-serialises to itself")
        self.assertEqual(body, _wire(doc), "and is the checked document written by the export's own writer, the same function that wrote the file")
        self.assertEqual(len(body), int(dict(headers)["Content-Length"]))
        # nothing of the machine or the file in the request line or a header: the plants, the real hostname, user and home
        # of the machine running the suite, the temp tree, the file's name, a path, a uuid, a hex token
        text = line + "\n" + "\n".join("%s: %s" % h for h in headers)
        for s in PLANTED + (socket.gethostname(), os.environ.get("USER") or "-", os.environ.get("HOME") or "-", xdg, os.path.basename(out)):
            self.assertNotIn(s, text, s)
        for name, value in headers:
            self.assertNotIn(name, ("Cookie", "Authorization", "X-Romp-Token", "Referer", "Origin"))
            self.assertIsNone(pp.ABS_PATH.search(value), (name, value))
            self.assertIsNone(pp.UUID.search(value), (name, value))
            self.assertIsNone(pp.HEX32.search(value), (name, value))
            self.assertNotIn(" ", value.strip(), (name, value))
        with open(out, "rb") as fh:
            self.assertEqual(fh.read(), data, "the verb did not touch the file")


class Docs(unittest.TestCase):
    """The user-facing sentences this verb's docs rest on, pinned flattened so a rewrap survives and cross-checked against
    the code where a count is involved."""

    @staticmethod
    def _flat(*parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return " ".join(fh.read().split())

    def test_the_reference_says_what_travels_and_makes_no_blanket_promise_about_the_machine(self):
        """The upload section of docs/reference.md said "Nothing about the machine travels: no hostname, account or filename,
        and no second file", which was false of the body the same section describes (per-machine measurements the export
        keeps by design: rss, cpu, the ten memory-fraction bounds coarsened to a power of two, the uptime and its bucket, the
        kernel commit) and contradicted by its own linkability clause a paragraph earlier (correctness-4 and extra4-3, the
        third review round): a false privacy promise in the paragraph a user decides on. The sentence now holds the standard
        the PR states everywhere else, paste-safe, not unlinkable: the negative is scoped to what NAMES the machine, what does
        travel is said in the same breath, and two uploads from one kernel remain linkable by design. The load-bearing words
        are pinned, and the blanket promise is pinned absent. Fails before: the old sentence was in the reference. The closing
        check found the enumeration incomplete (sent but unlisted: threads, hwm_kb, rss_anon_kb, gc_gen2, allocated_blocks, the
        malloc block and the fixed string process/source, and every leaf under heap and gc), so the sentence lists every leaf
        under process, heap and gc that a fresh Linux export of 2026-09-19 carried, plus the one leaf macOS adds (rss_peak_kb, the
        peak resident size, which the kernel writes on darwin alone and which reaches the wire like every other measurement;
        the closing check found the paragraph false on a Mac), says the four malloc leaves are null where the C library has
        no mallinfo2 (the closing re-run found the disclosure pin red wherever that is, glibc before 2.33, musl and macOS,
        with the leaves disclosed as travelling), and says the usage block is written only with --usage and adds no number a
        plain export lacks, the http table travelling in every export (the closing check of 2026-09-19, HIGH 1: the clause
        conditioned the 53 action counts and the 15 pane counts on the flag, and every one of them is in a plain export's
        perf.http table, identical, so the flag read as consent for data that always travels; the re-run before it found
        the paragraph naming one leaf of eleven there; the same rewrite dropped two provenance claims the code contradicts,
        the counts as the user's own actions and one count per pane opened, since a hook, a relaying kernel or a peer's poll
        posts the same routes). WHAT IS
        PINNED WHERE: this case pins the WORDING and the macOS clause's PLACEMENT (the process parenthetical is one needle
        and the clause is another that must follow it OUTSIDE the closing parenthesis, so the parenthetical the reader has
        already scanned is not silently widened); the LEAF POPULATION is pinned live in tests/test_perf_stats.py (Disclosed),
        over a real km._PerfStats().snapshot() through the public fold, the usage block from a snapshot that served every
        route the export counts, because a fixed list here cannot see an added leaf (this case holds the usage clause's
        PREFIX alone, up to the session counts; the route names are Disclosed's):
        the closing check added three leaves to a temp copy of the kernel one at a time and each travelled to a recording
        receiver over the real export-then-upload road while this case stayed at 2 passed; what went stale was the
        disclosure, not the protection: the recomputing paste-safety walk folded the probe gauge's path and uuid to `other`
        and no identifier reached the wire. The heap and gc enumerations that used to be needles here are therefore gone;
        the live pin holds them."""
        text = self._flat("docs", "reference.md")     # asserted by boolean, so a failure names the words and never dumps the page
        self.assertFalse("Nothing about the machine travels" in text, "the blanket promise is still in the reference")
        process = ("every leaf under `process` (`rss_kb`, `rss_anon_kb`, `hwm_kb`, `cpu_s`, `threads`, `gc_gen2`, `allocated_blocks`, "
                   "the `malloc` block's `arena`, `fordblks`, `hblkhd` and `uordblks`, null with no leaves under it where the C library "
                   "has no mallinfo2, glibc before 2.33, musl and macOS among them, and the fixed string `source`)")   # mallinfo2 unbackticked: not a key
        darwin = " plus, on macOS alone, `rss_peak_kb` (the peak resident size)"
        for words in ("The request carries nothing that names the machine beyond the file: no hostname, account or filename anywhere in it, "
                      "and no second file; the receiver names the stored object itself. What does travel is the file's content, and that is "
                      "paste-safe, not unlinkable:",
                      process, darwin, process + darwin,        # the clause follows the parenthetical, outside it
                      "the ten memory-fraction bounds coarsened to a power of two",
                      # HIGH 1 of the closing check: the http table is named as travelling in EVERY export, before the usage clause
                      "the uptime rounded down to the minute, the `http` table in every export, with or without `--usage`: one row per route "
                      "the kernel has served since it started",
                      # and the usage clause is packaging: its head says the block adds no number a plain export lacks (the clause's
                      # prefix; its population is Disclosed's)
                      "and, only when `--usage` was given, the `usage` block, which adds no number a plain export lacks: every leaf under "
                      "`usage` (the uptime's bucket `kernelUptime`, the `sessions` block's `parsed`, `chatBuilt` and `stamped`, each a copy or "
                      "a count of a leaf under perf that travels anyway",
                      # the second closing check (2026-09-19): the absence of the parsed count is stated in the document, by a leaf the
                      # paragraph names with its fixed value, and (the ruling of the same day on the leaf) one value per cause, each
                      # true of the shape that carries it; the wire's side is the road case above, the derivation is Disclosed's
                      "or, where the snapshot gives no parsed count, `parsedUnavailable` in place of `parsed` with one of two fixed "
                      "strings, predates-parses.perSession for a snapshot saved before the kernel counted parsed sessions (no perSession "
                      "block under parses) and perSession.sessions-not-a-number for a snapshot whose perSession block is there but "
                      "carries no number under sessions, so a count the export could not read is told from a kernel that parsed "
                      "nothing, and an old snapshot from a malformed one",
                      "the kernel commit",
                      "so two uploads from one kernel remain linkable by design",
                      # the closing re-run's finding 3, as its verification corrected it: the round's first replacement said an
                      # entry carrying a letter is not counted since no number spells one, and a listed 1e5 is counted (the
                      # exponent's e); the sentence now says which letter a number spells and that the alphabet decides
                      "and an entry outside the number alphabet that carries a letter in a digit group (abc12, zz424242) is not counted; the one "
                      "letter a number spells is an exponent's e, so an entry in the alphabet such as 1e5 is counted by its spelling",
                      # finding 9: the reference says the advisory's silence is not a claim (the module's copy is pinned in the export module)
                      "the line reports the digit count only, and an entry it does not count is not thereby matchable in a number",
                      # finding 6 of the re-run, widened by the closing check's HIGH 2: the upload section's strict-JSON parenthetical names
                      # both spellings the parser refuses, the overflowing float and the integer no double can hold
                      "parses as strict JSON (no `NaN` or `Infinity`, whether spelled as a literal or reached by a number written past the "
                      "double's range, such as 1e999 or an integer past about 1.8e308, which a double reader makes an infinity; no key "
                      "repeated within an object)"):
            self.assertTrue(words in text, "not in the reference: " + words)
        # the closing check's HIGH 1 and its finding 3: the old conditioning ("only when --usage was given, every leaf under usage",
        # which read as consent for counts a plain export sends identically) and the two provenance claims the code contradicts
        # (a hook, a relaying kernel and a peer's poll post the same routes) are pinned absent; asserted by boolean, as above
        for clause in ("the user's own actions", "one count per pane opened", "only when `--usage` was given, every leaf under `usage`"):
            self.assertFalse(clause in text, "the falsified usage clause is back in the reference: " + clause)
        # the closing re-run's finding 3: the clause saying an entry outside the number alphabet "is a substring of no number"
        # was false by execution ((1234567), _1234567 and 1234567/ each refuse the number 1234567 by its digit groups); deleted.
        # Asserted by boolean like the needles above: assertNotIn on failure prints the whole flattened page (about 400 KB)
        for clause in ("substring of no number", "since no number spells one", "since no number spells a letter"):
            self.assertFalse(clause in text, "the falsified alphabet clause is back in the reference: " + clause)

    def test_the_readme_rows_name_every_importer_of_the_public_shape_counted_from_the_code(self):
        """This PR added a fourth importer of cli/perf_public.py and left both README enumerations of who shares the public
        shape at three (regression-2, the third review round). The importers are counted from the code, not from the finding:
        every module under cli/ that imports perf_public (the three verbs), plus the served-snapshot invariant test, which
        loads it by path; four surfaces, and the bin README's perf_public parenthetical (by bin entry) and the cli README's
        perf_public row (by command) must name every one. Fails before: both rows named three."""
        cli_dir = os.path.join(ROOT, "cli")
        importers = []
        for name in sorted(os.listdir(cli_dir)):
            if name.endswith(".py") and name != "perf_public.py":
                with open(os.path.join(cli_dir, name), encoding="utf-8") as fh:
                    if re.search(r"^import perf_public\b", fh.read(), re.M):
                        importers.append(name)
        self.assertEqual(importers, ["perf_export.py", "perf_upload.py", "restart_metrics.py"], "the verbs that import the shape")
        with open(os.path.join(ROOT, "tests", "test_perf_stats.py"), encoding="utf-8") as fh:
            self.assertIn('"perf_public.py"', fh.read(), "the invariant test loads the shape by path: the fourth surface")
        self.assertEqual(len(importers) + 1, 4)
        bin_row = "imported by this, by `romp-perf-upload`, by `romp-restart-metrics --public` and by the served-snapshot invariant test"
        cli_row = ("The public shape shared by `romp perf export --public`, `romp perf upload`, `romp restart-metrics --json --public` "
                   "and the served-snapshot invariant test")
        self.assertTrue(bin_row in self._flat("bin", "README.md"), "bin/README.md's perf_public parenthetical does not name the four surfaces")
        self.assertTrue(cli_row in self._flat("cli", "README.md"), "cli/README.md's perf_public row does not name the four surfaces")


if __name__ == "__main__":
    unittest.main()
