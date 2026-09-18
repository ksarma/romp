#!/usr/bin/env python3
"""`romp perf upload FILE [--yes] [--receiver URL]` (cli/perf_upload.py, bin/romp-perf-upload), 2026-09-18: the
export's companion, which sends one paste-safe export to the receiver the operator configured and nothing else.

What is pinned here, each by execution against the verb's own file run as a child (bin/romp-perf-upload under
a pinned hostname) or, for the request itself, through bin/romp: the receiver address comes from --receiver,
else ROMP_PERF_RECEIVER, else ~/.config/romp/perf-receiver, and with none set the verb refuses naming all
three; the address must be https with a host and no userinfo, query or fragment (http for 127.0.0.1 and
localhost alone), and a refused address is never echoed; the file must exist, be at most 1 MiB, parse as strict
JSON (no NaN or Infinity, no repeated key at any depth, nesting within the checks' reach, about a thousand levels, past
which the verb refuses in one line) to an object with the schema
line and pass the export's own scan, walk and denylist walk as it stands (what the export dropped or coarsened is refused:
a key it drops, an uptime off whole minutes, a bound off a power of two, a float inside a clock stamp's epoch window, seconds
or milliseconds, under any key but a duration key; an integer, a float outside both windows and a float under a duration key
are measurements and pass, so an export from a long-lived kernel is sent whole), an
edited file refused by kind and key path and never by value; the line before the prompt names the URL the verb will dial, a path in the address included; the send needs a yes on a terminal or --yes, off a terminal
without the flag it refuses before dialling, and no environment variable stands in for the flag (an AST census
of the module's environment reads, plus an executed check with tempting names set); the one answer accepted is
201 with exactly {receipt: uuid4, retention_days: int, av: ok|skipped} in a body of at most 64 KiB, every other status
(a redirect among them, never followed, its Location never parsed), body or error refused with a fixed line carrying
the status code or the error class and nothing of the body or of any exception's message; the thirty seconds are a
deadline over the whole exchange, so a receiver answering in pieces each under the limit is cut at the total (a
raw-socket drip receiver pins it); and an enumeration of the request a recording receiver saw: the request line, every header
and the body bytes, which equal the file's.

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


def _run(args, state, home=HOME, extra=None, stdin=subprocess.DEVNULL):
    """bin/romp-perf-upload as a child under the pinned hostname (CHILD), stdin /dev/null (not a terminal) unless given."""
    return subprocess.run([sys.executable, "-c", CHILD, UPLOAD] + list(args), capture_output=True, text=True, timeout=60,
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


def _export(xdg, state):
    """An export the export verb wrote from the planted snapshot, under the same synthetic machine strings the
    upload child will scan with; returns its path."""
    src = os.path.join(xdg, "snap.json")
    out = os.path.join(xdg, "export.json")
    with open(src, "w") as fh:
        json.dump(planted_snapshot(), fh)
    r = subprocess.run([sys.executable, "-c", CHILD, EXPORT, "--public", "--from", src, "--out", out],
                       capture_output=True, text=True, timeout=60, env=_env(state))
    assert r.returncode == 0, r.stderr
    return out


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
        """The setting file is read with a bound (RECEIVER_FILE_MAX + 1 bytes), never whole: a device node, a fifo or a
        large file at that path costs that much memory and no more, and one over the bound is not truncated to its
        first line (which would send to whatever address that line spelled) but returned as the empty string with the
        file as its source, the non-UTF-8 road, so the caller refuses naming the file and nothing of its bytes. A stat
        would not do: it reports 0 for a device node or a fifo. Fails before: the address on the first line was returned.
        No device node in the suite: a regression there would exhaust the runner rather than fail a test."""
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
        """docs/guide.md names the upload as the one user-initiated exception to the local-only promise and says the receiver
        is one the user configures, none shipping, so nothing can be sent until one is set (fresh-2, 2026-09-18). The
        sentence is pinned flattened, so a rewrap survives, and cross-checked against the code by execution and by text:
        with no flag, no variable and an empty HOME the setting resolves to nothing (the verb then refuses naming the three
        settings, the case above), and no string constant in the module, docstrings included, spells a URL, so no default
        address can be hiding in the text."""
        with open(os.path.join(ROOT, "docs", "guide.md"), encoding="utf-8") as fh:
            guide = " ".join(fh.read().split())
        self.assertIn("to a receiver you configure yourself (none ships, so nothing can be sent until you set one), "
                      "and only after you confirm it", guide)
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

    def test_the_file_must_be_strict_json_with_the_schema_line(self):
        base = ["--yes", "--receiver", self.fake.url]
        bad = os.path.join(self.xdg, "bad.json")
        for text, phrase in (("not json", "is not strict JSON"), (b"\xff\xfe".decode("latin-1"), "is not strict JSON"),
                             ('{"schema": "romp-perf-export/1", "perf": {"uptime_s": NaN}}', "is not strict JSON"),
                             ('{"schema": "romp-perf-export/1", "perf": {"x": Infinity}}', "is not strict JSON"),
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
        path and never the string. This widens the shared check, not only the upload. Fails before: exit 0, one request."""
        base = ["--yes", "--receiver", self.fake.url]
        token = "zzcoinedzz"
        self.assertTrue(pp.IDENT.fullmatch(token), "the token fits the grammar: only the list knows it")
        os.makedirs(os.path.join(self.home, ".config", "romp"))
        with open(os.path.join(self.home, ".config", "romp", "private-strings.txt"), "w", encoding="utf-8") as fh:
            fh.write("# strings that must never be published\n%s\n" % token)
        doc = json.loads(self.data)
        doc["perf"]["leak"] = token
        edited = os.path.join(self.xdg, "edited.json")
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        r = self._refused(_run([edited] + base, self.state, home=self.home), 1,
                          "refused: a string this machine knows (private string) survives as the value at perf/leak; nothing sent")
        self.assertNotIn(token, r.stdout + r.stderr)
        self.assertEqual(r.stdout, "", "refused before the summary line")
        self.assertEqual(self.fake.requests, [], "nothing was sent")
        r = _run([edited] + base, self.state)             # the synthetic HOME has no list: the token is a grammar-fitting word and passes
        self.assertEqual(r.returncode, 0, r.stderr + " (without the list, no probe knows the token)")
        r = _run([self.file] + base, self.state, home=self.home)
        self.assertEqual(r.returncode, 0, r.stderr + " (a fresh export passes with the list loaded)")
        self.assertEqual(len(self.fake.requests), 2)

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
        r = _run([edited] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (edited, len(data), self.fake.url) + SUCCESS % (RECEIPT, 180))
        self.assertEqual(len(self.fake.requests), 1, "the export with byte totals inside the seconds window was sent")
        self.assertEqual(self.fake.requests[0][2], data, "the body is the file's bytes, totals included")
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
        r = _run([edited] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (edited, len(data), self.fake.url) + SUCCESS % (RECEIPT, 180))
        self.assertEqual(len(self.fake.requests), 1, "the export with millisecond totals inside the seconds window was sent")
        self.assertEqual(self.fake.requests[0][2], data, "the body is the file's bytes, sums included")
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
        r = _run([edited] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to %s/v1/upload\n" % (edited, len(data), self.fake.url) + SUCCESS % (RECEIPT, 180))
        self.assertEqual(len(self.fake.requests), 1, "the export with allocator figures above the seconds window was sent")
        self.assertEqual(self.fake.requests[0][2], data, "the body is the file's bytes, figures included")
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

    def test_a_file_that_repeats_a_key_is_refused_before_the_scan_since_the_bytes_and_the_parse_would_differ(self):
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
        self.assertEqual(self.fake.requests, [], "json.loads alone would keep the last copy, pass the scan, and send the bytes with both")

    def test_an_edited_file_the_fold_would_have_changed_is_refused_by_kind_and_key_path_and_never_sent(self):
        """The re-check holds the file to the export's FOLD, not to the walk's shapes alone (the upload's second review
        round, 2026-09-18). Three edits the walk passed and the fold would have written differently, each POSTed at the
        previous head: a 41-character token with no whitespace, hex run or path as a string value (the fold writes `other`),
        a key with a trailing newline after a good name (the walk's `$`-anchored match admits it, the fold's fullmatch does
        not), and a top-level block the envelope does not name whose value carries the token. Each exits 1 with one stderr
        line naming the kind and the key path (a key's the dict holding it), the token in no output, nothing sent; a fresh
        export and the 900-deep file the ordinary path admits still exit 0."""
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
            fh.write('{"schema": "romp-perf-export/1", "perf": {"uptime_s": 60, "x": ' + '{"a": ' * 900 + "1" + "}" * 900 + "}}")
        r = _run([deep] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.fake.requests), 2)

    def test_a_file_nested_past_the_parser_is_refused_as_not_strict_json_and_one_within_its_reach_takes_the_ordinary_path(self):
        base = ["--yes", "--receiver", self.fake.url]
        deep = os.path.join(self.xdg, "deep.json")
        with open(deep, "w") as fh:
            fh.write('{"schema": "romp-perf-export/1", "perf": ' + "[" * 100000 + "]" * 100000 + "}")        # 200 KB, under the size cap
        r = self._refused(_run([deep] + base, self.state), 1, "refused: %s is not strict JSON; nothing sent" % deep)
        self.assertEqual(r.stdout, "")
        self.assertNotIn("Recursion", r.stderr)
        self.assertEqual(self.fake.requests, [])
        with open(deep, "w") as fh:
            fh.write('{"schema": "romp-perf-export/1", "perf": {"uptime_s": 60, "x": ' + '{"a": ' * 900 + "1" + "}" * 900 + "}}")
        r = _run([deep] + base, self.state)
        self.assertEqual(r.returncode, 0, r.stderr + " (the receiver's depth rule is the receiver's; the verb parses, walks and sends)")
        self.assertEqual(len(self.fake.requests), 1)

    def test_a_file_nested_past_the_checks_reach_is_refused_in_one_line_with_no_traceback_and_nothing_sent(self):
        """The parser reaches about ten thousand levels and the three checks and the fold about a thousand (one frame per
        level under the interpreter's recursion limit), so a document the parser admits can overflow the checks: at the
        previous head that was a multi-page RecursionError traceback on stderr. Now it is the documented one-line refusal,
        nothing sent. The depth is derived from the recursion limit (the child inherits the interpreter's default, which is
        what this process reads too) and is not a depth rule of the verb's own: the receiver's depth rule is the receiver's,
        and the 900-deep case beside this one still takes the ordinary path."""
        base = ["--yes", "--receiver", self.fake.url]
        depth = sys.getrecursionlimit() + 5
        deep = os.path.join(self.xdg, "deep.json")
        with open(deep, "w") as fh:
            fh.write('{"schema": "romp-perf-export/1", "perf": {"uptime_s": 60, "x": ' + '{"a": ' * depth + "1" + "}" * depth + "}}")
        with open(deep, "rb") as fh:
            self.assertIsInstance(pu.strict_loads(fh.read()), dict, "the parser admits it")
        r = self._refused(_run([deep] + base, self.state), 1, "refused: %s is nested past the checks; nothing sent" % deep)
        self.assertEqual(r.stderr, "romp perf upload: refused: %s is nested past the checks; nothing sent\n" % deep)
        self.assertNotIn("Recursion", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(self.fake.requests, [])

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
        """The census over the transport module's text, load-bearing beside the https case above: disabling certificate
        verification needs a context object from somewhere, and the module has none. No import of ssl, no `context=`
        keyword at any call (the default HTTPSHandler and HTTPSConnection build the verified context themselves when
        none is passed, so the deadline handlers pass none), no attribute that would loosen one, no bare name ssl. The
        consent census (test_no_environment_variable_stands_in_for_yes) already collects every environ subscript, a
        PYTHONHTTPSVERIFY write among them."""
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
        self.assertEqual(self.fake.requests[0][2], self.data, "the body is the file's bytes")


class FoldBelt(unittest.TestCase):
    """read_export's last step, as a unit: with the three checks stubbed to pass, a top-level block that differs from its
    own fold is refused naming the block alone, and an export as written passes."""

    def test_the_fold_belt_refuses_a_block_the_checks_passed(self):
        xdg, state = _state_root()
        self.addCleanup(shutil.rmtree, xdg, True)
        file = _export(xdg, state)
        with open(file, "rb") as fh:
            data = fh.read()
        token = "zz-planted-token-past-thirty-two-chars-zz"
        doc = json.loads(data)
        doc["extra"] = {"note": token, "count": 1}
        edited = os.path.join(xdg, "edited.json")
        with open(edited, "w") as fh:
            json.dump(doc, fh)
        with mock.patch.object(pu.pe, "check_document", return_value=None) as stub:
            with self.assertRaises(pu.Refusal) as cm:
                pu.read_export(edited, pu.pe.Path(state))
            self.assertEqual(stub.call_count, 1, "the checks ran first and passed (stubbed); the belt is what refused")
            self.assertEqual(str(cm.exception), "refused: %s is not the export's own public form (the extra block differs from its fold); nothing sent" % edited)
            self.assertEqual(cm.exception.code, 1)
            self.assertNotIn(token, str(cm.exception))
            self.assertEqual(pu.read_export(file, pu.pe.Path(state)), data, "the export as written is its own fold")
            doc = json.loads(data)
            doc["extra"] = {"note": "fits-the-grammar", "count": 1}      # a block the fold leaves as it is passes the belt
            with open(edited, "w") as fh:
                json.dump(doc, fh)
            self.assertEqual(json.loads(pu.read_export(edited, pu.pe.Path(state)))["extra"], doc["extra"])
        self.assertEqual(pu.pe.ENVELOPE_KEYS, ("schema", "exported_at", "kernel_commit"))


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
    against the file's. Both runs are hermetic: an empty HOME under the test's tree, USER and LOGNAME `tester`,
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
        self.assertEqual(body, data, "the body is the file's bytes, unchanged")
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


if __name__ == "__main__":
    unittest.main()
