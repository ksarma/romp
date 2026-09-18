#!/usr/bin/env python3
"""`romp perf upload FILE [--yes] [--receiver URL]` (cli/perf_upload.py, bin/romp-perf-upload), 2026-09-18: the
export's companion, which sends one paste-safe export to the receiver the operator configured and nothing else.

What is pinned here, each by execution against the verb's own file run as a child (bin/romp-perf-upload under
a pinned hostname) or, for the request itself, through bin/romp: the receiver address comes from --receiver,
else ROMP_PERF_RECEIVER, else ~/.config/romp/perf-receiver, and with none set the verb refuses naming all
three; the address must be https with a host and no userinfo, query or fragment (http for 127.0.0.1 and
localhost alone), and a refused address is never echoed; the file must exist, be at most 1 MiB, parse as strict
JSON to an object with the schema line and pass the export's own scan and walk as it stands, an edited file
refused by kind and key path and never by value; the send needs a yes on a terminal or --yes, off a terminal
without the flag it refuses before dialling, and no environment variable stands in for the flag (an AST census
of the module's environment reads, plus an executed check with tempting names set); the one answer accepted is
201 with exactly {receipt: uuid4, retention_days: int, av: ok|skipped}, every other status (a redirect among
them, never followed), body or error refused with a fixed line carrying the status code or the error class and
nothing of the body; and an enumeration of the request a recording receiver saw: the request line, every header
and the body bytes, which equal the file's.

Nothing here reads a live kernel, a real state directory or a real setting: the child's HOME is synthetic or a
temp directory under the test's own tree, USER and LOGNAME are `tester`, socket.gethostname is pinned to
TESTHOST.example in the child, every id is a placeholder, and the only receiver any case dials is a handler this
module starts on 127.0.0.1 (or a loopback port nothing listens on). No request leaves the machine."""
import ast
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
    env = {k: v for k, v in os.environ.items() if not k.startswith("ROMP_") and k != "CLAUDE_CODE_SESSION_ID"}
    env.update({"XDG_STATE_HOME": os.path.dirname(state), "HOME": home, "USER": "tester", "LOGNAME": "tester", "ROMP_KERNEL_PORT": "1"})
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


class ReceiverAddress(unittest.TestCase):
    """receiver_url and upload_url: the address grammar and the route appended to it."""

    def test_accepted_addresses(self):
        for text, target in (("https://r.example", "https://r.example/v1/upload"),
                             ("https://r.example/", "https://r.example/v1/upload"),
                             ("https://r.example:8443/base/", "https://r.example:8443/base/v1/upload"),
                             ("  https://receiver-abc123-uc.a.b.example  ", "https://receiver-abc123-uc.a.b.example/v1/upload"),
                             ("http://127.0.0.1:8080", "http://127.0.0.1:8080/v1/upload"),
                             ("http://localhost:1/", "http://localhost:1/v1/upload")):
            u = pu.receiver_url(text)
            self.assertIsNotNone(u, text)
            self.assertEqual(pu.upload_url(u), target)

    def test_refused_addresses(self):
        for text in ("http://r.example", "http://r.example.localhost", "http://127.0.0.2/", "https://user@r.example", "https://user:pw@r.example",
                     "https://r.example/?x=1", "https://r.example/#frag", "https://", "https:///v1", "ftp://r.example", "r.example",
                     "https://r.example:abc", "https://ex ample.com", "https://r.example/a b", "https://[::1]/",
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

    def test_the_three_settings_in_order_flag_variable_file(self):
        dead = "http://127.0.0.1:%d" % _free_port()
        os.makedirs(os.path.join(self.home, ".config", "romp"))
        with open(os.path.join(self.home, ".config", "romp", "perf-receiver"), "w") as fh:
            fh.write(self.fake.url + "\n")
        r = _run([self.file, "--yes"], self.state, home=self.home)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to 127.0.0.1\n" % (self.file, len(self.data)) + SUCCESS % (RECEIPT, 180))
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

    def test_off_a_terminal_without_yes_the_verb_refuses_after_the_summary_line_and_dials_nothing(self):
        r = self._refused(_run([self.file, "--receiver", self.fake.url], self.state), 2, "refused: not on a terminal", "pass --yes",
                          "the form an agent uses", "no setting or variable stands in for it", "nothing sent")
        self.assertEqual(r.stdout, "%s (%d bytes) to 127.0.0.1\n" % (self.file, len(self.data)))
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

    def test_on_a_terminal_the_prompt_is_asked_and_y_or_yes_sends_while_anything_else_does_not(self):
        summary = "%s (%d bytes) to 127.0.0.1\n" % (self.file, len(self.data))
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

    def test_success_prints_the_receipt_and_the_retention_and_exits_0(self):
        self.fake.answer = (201, {}, json.dumps({"av": "skipped", "retention_days": 7, "receipt": RECEIPT.upper()}))
        r = _run([self.file, "--yes", "--receiver", self.fake.url], self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes) to 127.0.0.1\n" % (self.file, len(self.data)) + SUCCESS % (RECEIPT.upper(), 7))
        self.assertEqual(r.stderr, "")
        self.assertEqual(len(self.fake.requests), 1)
        self.assertEqual(self.fake.requests[0][2], self.data, "the body is the file's bytes")


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
        cls.summary = "%s (%d bytes) to 127.0.0.1\n" % (cls.file, len(cls.data))

    @classmethod
    def tearDownClass(cls):
        cls.fake.stop()
        shutil.rmtree(cls.xdg, True)

    def setUp(self):
        self.fake.reset()

    def _refused(self, line, url=None):
        r = _run([self.file, "--yes", "--receiver", url or self.fake.url], self.state)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stdout, self.summary)
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
                  json.dumps(ok) + json.dumps(ok), json.dumps(ok)[:-1], json.dumps({**ok, "note": "x" * (64 * 1024)})]
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
        self.assertEqual(r.stdout, "%s (%d bytes) to 127.0.0.1\n" % (out, len(data)) + SUCCESS % (RECEIPT, 180))
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
