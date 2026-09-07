#!/usr/bin/env python3
"""File comments (plans/file-review.md, Slice 1) — the kernel-side fixes from the slice's review.

Four findings (2026-09-06), each pinned beside the seam it changed in kernel/kernel.py:

- A host refusal that says `logged: true` — log-edit and log-send append their entry BEFORE the sidecar
  read that can refuse — is reported as an entry that landed, never as "not written to the comments
  log". The kernel reads `logged` off the refusal (_file_comments_call hands the host's whole answer
  back beside the code) and words the warning after what failed.
- The two command lines in the sent message carry the path as ONE shell word (shlex.quote's rule,
  _sh_word), so a space no longer truncates --file's value and a metacharacter no longer runs in the
  session's shell. An ordinary path still reads exactly as the plan's template writes it.
- saveFile reads nothing the save refuses: the text the comments log needs comes out of _save_file's
  own read, through its `prior` argument, after the consent gate, the text-name check, the on-disk
  size cap and the mtime fence; _edit_log_before is path predicates only.
- The log verbs are the kernel's own: a client's log-edit or log-send is refused `kernel-only`, and a
  send's watermark is checked (shape and clock) before the message goes, so no send entry can hide
  later comments from the unsent derivation.

Stubbed like tests/test_file_comments.py (a node host script under the temp dir that answers as told);
the ...WithTheRealHost classes run tools/file-comments-host.mjs over the vendored store layer on a corrupt
sidecar, the case a stub cannot vouch for. Synthetic only: the notes-api demo world, placeholder ids,
temp dirs.
"""
import builtins
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(HERE)
BIN = os.path.join(REPO, "bin")
HOST = os.path.join(REPO, "tools", "file-comments-host.mjs")
CORRUPT = os.path.join(HERE, "fixtures", "file_comments", "sidecar-corrupt.txt")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the load — the kernel resolves its state root at import time, and only pytest
# runs conftest's floor (a bare unittest run would otherwise write REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_filecomments_hardening", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
NODE = shutil.which("node")
BASH = shutil.which("bash")
TEXT = "# Findings\n\nThe api session cut p95 latency by 40%.\n"
EDITED = "# Findings\n\nThe api session cut p95 latency by 45%.\n"
ONE = [{"id": "1781100000000-0", "desc": 'on "shipping the cache in v1.2"', "body": "Which cache? Say which."}]
REPORT = "/TESTDIR/notes-api/docs/report.md"
NO_STORE = {"storeMtimeNs": "", "configMtimeNs": ""}

# The stub host script (tests/test_file_comments.py's): records the request it read from stdin, then
# answers as configured.
_STUB = """import fs from 'node:fs';
const CFG = %s;
let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (d) => { raw += d; });
process.stdin.on('end', () => {
  let request = null;
  try { request = JSON.parse(raw); } catch (e) { request = { parseError: String(e), raw }; }
  fs.writeFileSync(CFG.seen, JSON.stringify({ request, argv: process.argv.slice(2) }));
  if (CFG.stderr) process.stderr.write(CFG.stderr);
  if (CFG.stdout !== null) process.stdout.write(CFG.stdout);
  else process.stdout.write(JSON.stringify(CFG.reply));
  process.exit(CFG.exit);
});
"""


@unittest.skipUnless(NODE, "node not installed on this machine")
class _Harness(unittest.TestCase):
    """A notes-api tree with a .trackchanges/ at its root, the consent on, the kernel pointed at a stub
    host script under the temp dir."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "notes-api")
        os.makedirs(os.path.join(self.root, ".trackchanges"))
        os.makedirs(os.path.join(self.root, "docs"))
        self.fp = os.path.join(self.root, "docs", "report.md")
        with open(self.fp, "w") as f:
            f.write(TEXT)
        self.ns = os.stat(self.fp).st_mtime_ns
        self.seen_path = os.path.join(self.tmp, "seen.json")
        self.stub_path = os.path.join(self.tmp, "stub-host.mjs")
        self._saved_host = (km._FILE_COMMENTS_HOST, km._FILE_COMMENTS_TIMEOUT)
        km._FILE_COMMENTS_HOST = Path(self.stub_path)
        km._set_file_editing(True)
        self.stub()

    def tearDown(self):
        km._FILE_COMMENTS_HOST, km._FILE_COMMENTS_TIMEOUT = self._saved_host
        km._set_file_editing(False)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def stub(self, reply=None, exit=0, stderr="", stdout=None):
        if reply is None:
            reply = {"ok": True, "verb": "status", "root": self.root, "storePath": None, "trackedBy": None,
                     "agentTooling": "absent", "fileMtimeNs": str(self.ns), "storeMtimeNs": None,
                     "configMtimeNs": None, "store": None, "hunks": [],
                     "unsent": {"comments": [], "replies": [], "accepted": 0, "rejected": 0, "watermark": None},
                     "log": [], "logTruncated": False}
        cfg = {"seen": self.seen_path, "reply": reply, "exit": exit, "stderr": stderr, "stdout": stdout}
        with open(self.stub_path, "w") as f:
            f.write(_STUB % json.dumps(cfg))
        try:
            os.unlink(self.seen_path)
        except OSError:
            pass

    def seen(self):
        try:
            with open(self.seen_path) as f:
                return json.load(f)
        except OSError:
            return None

    def real_host(self):
        """Run the REAL host script over the vendored store layer instead of the stub."""
        km._FILE_COMMENTS_HOST = Path(HOST)

    def sidecar(self):
        return os.path.join(self.root, ".trackchanges", "docs%2Freport.md.json")

    def log_lines(self):
        p = os.path.join(self.root, ".trackchanges", "docs%2Freport.md.comments-log.jsonl")
        if not os.path.exists(p):
            return []
        with open(p) as f:
            return [json.loads(l) for l in f.read().splitlines() if l.strip()]


class _Wire(_Harness):
    """The real dispatcher with a fake client whose send() flips an Event."""

    def setUp(self):
        super().setUp()
        self.sent, self.got = [], threading.Event()

        def _send(s):
            self.sent.append(json.loads(s))
            self.got.set()
        self.client = {"app": "feed", "alive": True, "send": _send}
        self.handler = object.__new__(km.Handler)

    def send(self, msg, wait=True):
        self.got.clear()
        km.Handler._dispatch_ws(self.handler, msg, self.client)
        if wait:
            self.assertTrue(self.got.wait(20), "the op never answered")
        return self.sent[-1] if self.sent else None

    def save(self, path=None, content=EDITED, ns=None, rid=3):
        return self.send({"type": "saveFile", "path": path or self.fp, "content": content,
                          "baseMtimeNs": str(self.ns if ns is None else ns), "reqId": rid}, wait=False)


class _World(_Wire):
    """…plus the send op's world: a STATE sandbox with user todos ON, a known session (`web`), and
    _send_or_park scripted — tests/test_file_comments.py's _SendWorld."""

    def setUp(self):
        super().setUp()
        self.td = tempfile.TemporaryDirectory()
        self.saved_state = jd.STATE
        jd.STATE = Path(self.td.name)
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._set_user_todos(True)
        km._set_file_editing(True)                    # the state root moved: re-open the consent there
        self._saved_world = (km._name_of, km._sdk, km._send_or_park)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        self.injected = []

        def fake_send_or_park(be, sid, text, echo=None, user_todo=None):
            self.injected.append({"sid": sid, "text": text, "user_todo": user_todo})
            return True
        km._send_or_park = fake_send_or_park
        self.tid = km._add_user_todo(SID, "Need a look at the findings report", self.fp)
        self.stub(reply={"ok": True, "verb": "log-send", "logged": True})

    def tearDown(self):
        km._name_of, km._sdk, km._send_or_park = self._saved_world
        jd.STATE = self.saved_state
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        self.td.cleanup()
        super().tearDown()

    def send_op(self, **kw):
        msg = {"type": "fileCommentsSend", "reqId": 9, "sid": SID, "path": self.fp, "tracked": True,
               "comments": ONE, "accepted": 0, "rejected": 0, "watermark": 1781100000000, "todoId": self.tid}
        msg.update(kw)
        return km._file_comments_send_op(msg)

    def todo(self):
        return km._user_todos()[SID][0]


CORRUPT_REFUSAL = {"ok": False, "code": "corrupt",
                   "error": "the comments for ~/notes-api/docs/report.md could not be read: the sidecar is not "
                            "valid JSON in the expected shape; nothing was changed"}


class ALoggedRefusalIsAnEntryThatLanded(_World):
    """The host's log verbs append first and read the sidecar second; when the read refuses they say
    `logged: true` beside the code. Before the fix the kernel reduced every refusal to (code, error) and
    told the person the log was not written while the entry sat on disk."""

    def test_the_call_hands_the_refusal_back_beside_the_error(self):
        self.stub(reply=dict(CORRUPT_REFUSAL, logged=True))
        out, err = km._file_comments_call(self.fp, "log-edit", {"summary": {}})
        self.assertEqual(err, ("corrupt", CORRUPT_REFUSAL["error"]))
        self.assertIs(out["logged"], True, "the host's whole answer rides back, `logged` included")
        self.stub(exit=1, stderr="Error: boom")
        out, err = km._file_comments_call(self.fp, "log-edit", {"summary": {}})
        self.assertIsNone(out, "a kernel-side failure has no host answer to hand back")
        self.assertEqual(err[0], "host-error")

    def test_a_save_whose_entry_landed_reports_logged_true_and_names_what_failed(self):
        self.stub(reply=dict(CORRUPT_REFUSAL, logged=True))
        r = self.save()
        self.assertEqual(r["type"], "fileSaved")
        self.assertIs(r["logged"], True, "the entry is on disk: the panel's Log is current")
        self.assertIn("written to the comments log", r["logWarning"])
        self.assertIn("could not be read back", r["logWarning"])
        self.assertIn("not valid JSON", r["logWarning"], "the host's reason rides along")
        self.assertNotIn("not written", r["logWarning"])
        self.assertEqual(self.seen()["request"]["verb"], "log-edit")

    def test_a_refusal_with_no_entry_is_still_not_written(self):
        for reply, content in ((dict(CORRUPT_REFUSAL, logged=False), EDITED), (CORRUPT_REFUSAL, TEXT)):
            self.stub(reply=reply)
            r = self.save(content=content, ns=os.stat(self.fp).st_mtime_ns)
            self.assertEqual(r["type"], "fileSaved")
            self.assertIs(r["logged"], False)
            self.assertIn("not written to the comments log", r["logWarning"])
            self.assertIn("not valid JSON", r["logWarning"])

    def test_a_send_whose_entry_landed_says_the_log_was_updated(self):
        self.stub(reply=dict(CORRUPT_REFUSAL, logged=True))
        r = self.send_op()
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIn("comments log", r["logWarning"])
        self.assertIn("was updated", r["logWarning"])
        self.assertIn("could not be read", r["logWarning"])
        self.assertNotIn("was not updated", r["logWarning"], "the panel shows this row: it must not invite a second send")
        self.assertEqual(len(self.injected), 1)
        self.assertEqual(self.todo()["resolved"]["kind"], "answered")

    def test_a_send_whose_entry_did_not_land_still_says_not_updated(self):
        self.stub(reply=CORRUPT_REFUSAL)
        r = self.send_op()
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIn("was not updated", r["logWarning"])


class ACorruptSidecarWithTheRealHost(_World):
    """The plan's own Risks case (a sidecar left with conflict markers after a rebase), through the real
    host script: the edit and send entries land, and the kernel says so."""

    def setUp(self):
        super().setUp()
        self.real_host()
        shutil.copyfile(CORRUPT, self.sidecar())

    def test_the_sidecar_reads_as_corrupt_for_the_panel(self):
        r = self.send({"type": "fileComments", "reqId": 5, "sid": SID, "path": self.fp, "verb": "status"})
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "corrupt"))
        # the fence names the sidecar that IS there (the "" fence would refuse store-moved before any read)
        fence = {"storeMtimeNs": str(os.stat(self.sidecar()).st_mtime_ns), "configMtimeNs": ""}
        r = self.send({"type": "fileComments", "reqId": 6, "sid": SID, "path": self.fp, "verb": "comment",
                       "args": {"note": "x"}, "fence": fence})
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "corrupt"))
        self.assertEqual(self.log_lines(), [], "a refused verb appends nothing")

    def test_a_direct_edit_is_logged_and_the_ack_says_so(self):
        r = self.save()
        self.assertEqual(r["type"], "fileSaved")
        self.assertIs(r["logged"], True)
        self.assertIn("written to the comments log", r["logWarning"])
        self.assertIn("could not be read back", r["logWarning"])
        self.assertNotIn("not written", r["logWarning"])
        entries = self.log_lines()
        self.assertEqual([e["kind"] for e in entries], ["edit"])
        self.assertEqual(entries[0]["bytesBefore"], len(TEXT.encode()))
        self.assertEqual(entries[0]["mtimeBeforeNs"], str(self.ns))
        self.assertIn("+The api session cut p95 latency by 45%.", entries[0]["diff"])
        with open(self.fp) as f:
            self.assertEqual(f.read(), EDITED)
        with open(self.sidecar()) as f, open(CORRUPT) as g:
            self.assertEqual(f.read(), g.read(), "the corrupt sidecar is never replaced")

    def test_a_send_is_logged_with_its_watermark_and_the_reply_says_updated(self):
        r = self.send_op(watermark=1781100000000)
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIn("was updated", r["logWarning"])
        self.assertNotIn("was not updated", r["logWarning"])
        entries = self.log_lines()
        self.assertEqual([e["kind"] for e in entries], ["send"])
        self.assertEqual((entries[0]["sid"], entries[0]["sessionName"], entries[0]["watermark"]),
                         (SID, "web", 1781100000000))
        self.assertEqual(len(self.injected), 1)


class TheCommandLinesCarryThePathAsOneWord(unittest.TestCase):
    """The session runs the two command lines as written. A path is one shell word on them (shlex.quote's
    rule), so a space no longer splits --file's value and a metacharacter never runs; the prose keeps the
    plain path. The webview's preview builder must port _sh_word byte for byte."""

    def lines(self, path, tracked=True, is_text=True):
        body = km._file_comments_message(path, ONE, 0, 0, tracked, is_text)
        cmd = [l for l in body.splitlines() if "track-reply.mjs" in l or "track-edit.mjs" in l]
        return body, cmd

    def file_arg(self, line):
        """What a POSIX shell hands the CLI as --file's value."""
        words = shlex.split(line[line.index("node "):].replace("<id>", "ID"))
        return words[words.index("--file") + 1]

    def test_an_ordinary_path_reads_as_the_plans_template(self):
        body, cmd = self.lines(REPORT)
        self.assertEqual(len(cmd), 2)
        for l in cmd:
            self.assertIn("--file %s --thread <id>" % REPORT, l, "no quotes on a path that needs none")
            self.assertEqual(self.file_arg(l), REPORT)
        self.assertNotIn("'", body)

    def test_a_space_in_the_name_stays_one_word(self):
        path = "/TESTDIR/vault/Meeting notes.md"
        body, cmd = self.lines(path)
        self.assertTrue(body.startswith("[obsidian-diff] I left 1 comment on %s.\n" % path), "prose: the plain path")
        self.assertEqual(len(cmd), 2)
        for l in cmd:
            self.assertIn("--file '/TESTDIR/vault/Meeting notes.md' --thread <id>", l)
            self.assertEqual(self.file_arg(l), path, "the CLI sees the whole name, not …/Meeting plus a stray word")

    def test_metacharacters_are_inert(self):
        names = ["notes; touch PWNED #.md", "a$(touch PWNED2).md", "b`touch PWNED3`.md", "it's here.md",
                 'say "hi".md', "x && touch PWNED4.md", "y | tee PWNED5.md", "z > PWNED6.md", "w\\v.md"]
        for name in names:
            path = "/TESTDIR/vault/" + name
            body, cmd = self.lines(path)
            self.assertEqual(len(cmd), 2, name)
            for l in cmd:
                self.assertEqual(self.file_arg(l), path, name)

    @unittest.skipUnless(BASH, "bash not installed on this machine")
    def test_a_real_shell_agrees_and_runs_nothing_else(self):
        scratch = tempfile.mkdtemp()
        try:
            for name in ["notes; touch PWNED #.md", "a$(touch PWNED2).md", "b`touch PWNED3`.md", "Meeting notes.md",
                         "it's here.md", "x && touch PWNED4.md"]:
                path = "/TESTDIR/vault/" + name
                _, cmd = self.lines(path)
                for l in cmd:
                    # the line as the session would run it, with the CLI swapped for printf so each argv
                    # element prints on its own line, and the <id> placeholder filled
                    tail = l.split(".mjs ", 1)[1].replace("<id>", "ID")
                    r = subprocess.run([BASH, "-c", "printf '%s\\n' " + tail], cwd=scratch, capture_output=True,
                                       text=True, timeout=20)
                    self.assertEqual(r.returncode, 0, (name, r.stderr))
                    argv = r.stdout.split("\n")
                    self.assertEqual(argv[argv.index("--file") + 1], path, name)
            self.assertEqual(os.listdir(scratch), [], "nothing in a file name ran")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def test_neutralization_comes_first_then_the_quoting(self):
        path = "/TESTDIR/<!-- romp-x -->/a.md"
        body, cmd = self.lines(path)
        self.assertNotIn("<!-- romp-", body)
        self.assertIn("I left 1 comment on /TESTDIR/<!- - romp-x -->/a.md.", body)
        for l in cmd:
            self.assertIn("--file '/TESTDIR/<!- - romp-x -->/a.md' --thread <id>", l)
            self.assertEqual(self.file_arg(l), "/TESTDIR/<!- - romp-x -->/a.md")

    def test_the_other_bullets_are_untouched(self):
        for tracked, is_text, want in ((False, True, "edit the file normally"), (True, False, "regenerate the file")):
            body, cmd = self.lines("/TESTDIR/vault/Meeting notes.md", tracked, is_text)
            self.assertEqual(len(cmd), 1, "only the reply line carries the path")
            self.assertIn(want, body)
            self.assertIn("--file '/TESTDIR/vault/Meeting notes.md' --thread <id>", cmd[0])

    def test_the_rule_is_shlex_quote(self):
        # the spec the webview's port follows: empty → '', the safe set passes, everything else is
        # single-quoted with an embedded quote written as '"'"'
        self.assertEqual(km._sh_word(""), "''")
        self.assertEqual(km._sh_word("/a/b_c-d.e:f@g%h+i=j,k"), "/a/b_c-d.e:f@g%h+i=j,k")
        self.assertEqual(km._sh_word("a b"), "'a b'")
        self.assertEqual(km._sh_word("it's"), "'it'\"'\"'s'")
        self.assertEqual(km._sh_word("é.md"), "'é.md'", "non-ASCII is outside the safe set")
        for s in ("", "a b", "it's", "$(x)", "`y`", "é.md", "a;b"):
            self.assertEqual(shlex.split(km._sh_word(s)) if s else [""], [s] if s else [""])


class TheSaveReadsNothingItWouldRefuse(_Wire):
    """saveFile's edit-log read used to run BEFORE _save_file — ahead of the consent gate, the text-name
    check, the size cap and the mtime fence — on any file under a tree holding a .trackchanges/. Now the
    only read is _save_file's own, after every gate, and it hands the old text out through `prior`."""

    def setUp(self):
        super().setUp()
        self.opened = []
        real = builtins.open

        def spy(file, *a, **k):
            self.opened.append(os.path.realpath(file) if not isinstance(file, int) else file)
            return real(file, *a, **k)
        km.open = spy                                   # shadows the builtin for every function in the module

    def tearDown(self):
        try:
            del km.open
        except AttributeError:
            pass
        super().tearDown()

    def never_opened(self, path):
        self.assertNotIn(os.path.realpath(path), self.opened, "the save read a file it refused")

    def test_with_editing_off_a_blob_under_a_tracked_tree_is_never_opened(self):
        km._set_file_editing(False)
        blob = os.path.join(self.root, "docs", "big.iso")
        with open(blob, "wb") as f:
            f.write(b"\0" * 64)
        self.opened.clear()
        self.assertTrue(km._trackchanges_above(blob), "the precondition the finding names")
        r = self.save(path=blob, content="", ns=0)
        self.assertEqual(r["type"], "fileSaveFailed")
        self.assertIn("file editing is off", r["error"])
        self.never_opened(blob)
        self.assertIsNone(self.seen(), "no host call either")

    def test_a_non_text_name_is_refused_before_any_read(self):
        blob = os.path.join(self.root, "docs", "big.iso")
        with open(blob, "wb") as f:
            f.write(b"\0" * 64)
        self.opened.clear()
        r = self.save(path=blob, content="", ns=os.stat(blob).st_mtime_ns)
        self.assertEqual(r["type"], "fileSaveFailed")
        self.assertIn("not a text file", r["error"])
        self.never_opened(blob)

    def test_a_stale_anchor_is_refused_before_any_read(self):
        r = self.save(ns=self.ns - 10)
        self.assertEqual(r["type"], "fileSaveFailed")
        self.assertIn("changed on disk", r["error"])
        self.never_opened(self.fp)
        self.assertIsNone(self.seen())

    def test_a_text_file_past_the_cap_on_disk_is_refused_on_the_stat(self):
        big = os.path.join(self.root, "docs", "big.md")
        with open(big, "wb") as f:
            f.truncate(km._TEXT_MAX_BYTES + 1)          # sparse: the size without the bytes
        self.opened.clear()
        r = self.save(path=big, content="small\n", ns=os.stat(big).st_mtime_ns)
        self.assertEqual(r["type"], "fileSaveFailed")
        self.assertIn("past the 2.0 MB text cap", r["error"])
        self.assertIn("big.md", r["error"])
        self.never_opened(big)
        with open(big, "rb") as f:
            self.assertEqual(len(f.read()), km._TEXT_MAX_BYTES + 1, "untouched")
        # exactly the cap is still a file the viewer loads
        with open(big, "wb") as f:
            f.write(b"a" * km._TEXT_MAX_BYTES)
        r = self.save(path=big, content="small\n", ns=os.stat(big).st_mtime_ns)
        self.assertEqual(r["type"], "fileSaved")

    def test_a_fifo_under_a_tracked_tree_is_refused_not_read(self):
        fifo = os.path.join(self.root, "docs", "pipe.md")
        os.mkfifo(fifo)
        self.opened.clear()
        done = threading.Event()
        box = {}

        def run():
            box["r"] = self.save(path=fifo, content="x\n", ns=os.stat(fifo).st_mtime_ns)
            done.set()
        t = threading.Thread(target=run, daemon=True)
        t.start()
        answered = done.wait(10)
        if not answered:
            # release a reader stuck in open(): a writer end makes its open return and its read see EOF
            try:
                os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
            except OSError:
                pass
        self.assertTrue(answered, "the recv loop blocked on a FIFO")
        self.assertEqual(box["r"]["type"], "fileSaveFailed")
        self.assertIn("no such file", box["r"]["error"])
        self.never_opened(fifo)

    def test_a_good_save_reads_the_file_once_and_the_log_gets_that_text(self):
        self.stub(reply={"ok": True, "verb": "log-edit", "logged": True})
        self.opened.clear()
        r = self.save()
        self.assertEqual(r["type"], "fileSaved")
        self.assertIs(r["logged"], True)
        self.assertNotIn("logWarning", r)
        self.assertEqual(self.opened.count(os.path.realpath(self.fp)), 1, "one read: _save_file's own")
        s = self.seen()["request"]["args"]["summary"]
        self.assertEqual((s["bytesBefore"], s["mtimeBeforeNs"]), (len(TEXT.encode()), str(self.ns)))
        self.assertEqual(s["bytesAfter"], len(EDITED.encode()))
        self.assertIn("-The api session cut p95 latency by 40%.\n", s["diff"])
        self.assertIn("+The api session cut p95 latency by 45%.\n", s["diff"])

    def test_the_helpers(self):
        # _edit_log_before: path predicates only, nothing opened
        self.opened.clear()
        self.assertEqual(km._edit_log_before(self.fp, None), {"path": self.fp})
        self.assertIsNone(km._edit_log_before(os.path.join(self.root, ".trackchanges", "config.json"), None))
        loose = os.path.join(self.tmp, "loose.md")
        with open(loose, "w") as f:
            f.write("a\n")
        self.opened.clear()
        self.assertIsNone(km._edit_log_before(loose, None))
        self.assertEqual(self.opened, [])
        # _save_file fills `prior` once every gate has passed, and only then
        d = {}
        km._set_file_editing(False)
        self.assertIsNotNone(km._save_file(self.fp, None, EDITED, self.ns, prior=d)[1])
        self.assertEqual(d, {}, "a refused save hands nothing out")
        km._set_file_editing(True)
        self.assertIn("changed on disk", km._save_file(self.fp, None, EDITED, self.ns - 1, prior=d)[1])
        self.assertEqual(d, {})
        mt, err = km._save_file(self.fp, None, EDITED, self.ns, prior=d)
        self.assertIsNone(err)
        self.assertEqual(d, {"bytes": TEXT.encode(), "ns": self.ns})
        # the 4-argument call every other caller makes is unchanged
        mt2, err2 = km._save_file(self.fp, None, TEXT, mt)
        self.assertIsNone(err2)
        self.assertIsInstance(mt2, int)
        # _edit_log_after without the read it needs says so instead of logging a wrong diff
        logged, warn = km._edit_log_after({"path": self.fp}, {}, EDITED, mt2)
        self.assertIs(logged, False)
        self.assertIn("was not read before the save", warn)
        self.assertEqual(km._edit_log_after(None, None, EDITED, mt2), (False, None))


class ClientVerbsStopAtTheKernel(_Harness):
    """log-edit and log-send are what the kernel appends after a save and a send. The host takes them
    from anyone, and one client-minted send entry with a far-future watermark would hide every later
    comment for the rest of the file's life — so the kernel refuses them from a client."""

    def op(self, verb, **kw):
        msg = {"type": "fileComments", "reqId": 7, "sid": SID, "path": self.fp, "verb": verb}
        msg.update(kw)
        return km._file_comments_op(msg)

    def test_the_log_verbs_are_refused_kernel_only_and_never_reach_the_host(self):
        for verb, args in (("log-send", {"sid": SID, "comments": [], "accepted": 0, "rejected": 0, "queued": False,
                                         "watermark": 9007199254740000}),
                           ("log-edit", {"summary": {"diff": "-forged\n+arbitrary text\n"}})):
            r = self.op(verb, args=args)
            self.assertEqual(r["type"], "fileCommentsFailed", verb)
            self.assertEqual(r["code"], "kernel-only", verb)
            self.assertIn(verb, r["error"])
            self.assertIn("report.md", r["error"], "the refusal names the path")
            self.assertNotIn("file editing is off", r["error"], "not the phrase the viewer's consent regex matches")
            self.assertEqual((r["reqId"], r["verb"]), (7, verb))
        self.assertIsNone(self.seen(), "the host never ran")
        self.assertEqual(km._FILE_COMMENTS_KERNEL_VERBS, frozenset(("log-edit", "log-send")))

    def test_the_consent_wall_still_stands_first(self):
        km._set_file_editing(False)
        for verb in ("log-edit", "log-send"):
            r = self.op(verb)
            self.assertEqual(r["code"], "editing-off", verb)
        self.assertIsNone(self.seen())

    def test_every_other_verb_still_reaches_the_host(self):
        for verb in ("status", "set-tracked", "comment", "reply", "resolve", "accept", "accept-all"):
            self.stub(reply={"ok": True, "verb": verb})
            r = self.op(verb, args={})
            self.assertEqual(r["type"], "fileCommentsResult", verb)
            self.assertEqual(self.seen()["request"]["verb"], verb, "the host decides the verbs it knows")

    def test_the_kernels_own_log_send_is_not_a_client_op(self):
        # the send op reaches the host through _file_comments_call directly, not through the client op
        import inspect
        src = inspect.getsource(km._file_comments_send_op)
        self.assertIn('_file_comments_call(p, "log-send", entry)', src)
        self.assertNotIn("_file_comments_op(", src)


class TheWatermarkIsCheckedBeforeTheMessageGoes(_World):
    """The log's unsent derivation takes the maximum watermark over every send entry, forever. The send
    op therefore refuses a watermark no comment could carry — the wrong shape, or later than this
    machine's clock plus the skew allowance — BEFORE delivering, so neither the message nor the entry
    goes out on a value the host would refuse or the derivation would be poisoned by."""

    def now_ms(self):
        return int(time.time() * 1000)

    def test_a_future_watermark_refuses_and_nothing_moves(self):
        for wm in (9007199254740000, self.now_ms() + km._SEND_WATERMARK_SKEW_MS + 60 * 1000):
            r = self.send_op(watermark=wm)
            self.assertEqual(r["type"], "fileCommentsSendFailed", wm)
            self.assertIn("watermark", r["error"])
            self.assertIn(str(wm), r["error"], "the refusal names the value")
            self.assertIn("nothing was sent", r["error"])
        self.assertEqual(self.injected, [], "the message never went")
        self.assertIsNone(self.seen(), "and no entry was appended")
        self.assertNotIn("resolved", self.todo(), "the todo stays open")

    def test_the_shape_is_checked(self):
        for wm in (True, False, "abc", "12abc", "", 1.5, float("nan"), float("inf"), -1, -1.0, [1], {"a": 1}):
            r = self.send_op(watermark=wm)
            self.assertEqual(r["type"], "fileCommentsSendFailed", repr(wm))
            self.assertIn("watermark", r["error"])
        self.assertEqual(self.injected, [])
        self.assertIsNone(self.seen())

    def test_a_comments_timestamp_goes_through_as_a_number(self):
        cases = ((1781100000000, 1781100000000), ("1781100000000", 1781100000000), (1781100000000.0, 1781100000000),
                 (None, None), (0, 0))
        for given, want in cases:
            self.stub(reply={"ok": True, "verb": "log-send", "logged": True})
            r = self.send_op(watermark=given, todoId=None)
            self.assertEqual(r["type"], "fileCommentsSent", repr(given))
            got = self.seen()["request"]["args"]["watermark"]
            self.assertEqual(got, want, repr(given))
            self.assertIs(type(got), type(want), "the host takes number|null, never a string")
        self.assertEqual(len(self.injected), len(cases))

    def test_the_bound_is_this_clock_plus_the_skew(self):
        inside = self.now_ms() + km._SEND_WATERMARK_SKEW_MS - 30 * 1000
        r = self.send_op(watermark=inside, todoId=None)
        self.assertEqual(r["type"], "fileCommentsSent", "a sidecar committed from a clock that ran ahead still sends")
        self.assertEqual(self.seen()["request"]["args"]["watermark"], inside)
        self.assertEqual(km._SEND_WATERMARK_SKEW_MS, 60 * 60 * 1000)
        self.assertEqual(km._send_watermark(None), (None, None))
        self.assertEqual(km._send_watermark("  42 "), (42, None))
        self.assertIsNotNone(km._send_watermark(self.now_ms() + km._SEND_WATERMARK_SKEW_MS + 1000)[1])


class AForgedWatermarkNeverLandsWithTheRealHost(_World):
    """End to end: a comment made through the real host, a forged send refused, the comment still
    unsent; then a real send, and the derivation moves exactly to that comment's ts."""

    def setUp(self):
        super().setUp()
        self.real_host()

    def fc(self, verb, args=None, fence=None, rid=20):
        msg = {"type": "fileComments", "reqId": rid, "sid": SID, "path": self.fp, "verb": verb}
        if args is not None:
            msg["args"] = args
        if fence is not None:
            msg["fence"] = fence
        return self.send(msg)

    def test_the_forged_send_is_refused_and_the_comment_stays_unsent(self):
        r = self.fc("comment", {"note": "Which cache?"}, NO_STORE)
        self.assertEqual(r["type"], "fileCommentsResult", r)
        cid = r["store"]["comments"][0]["id"]
        ts = r["store"]["comments"][0]["ts"]
        self.assertEqual(r["unsent"]["comments"], [cid])
        bad = self.send_op(comments=[{"id": cid, "desc": "on this file", "body": "Which cache?"}],
                           watermark=9007199254740000, todoId=None)
        self.assertEqual(bad["type"], "fileCommentsSendFailed")
        self.assertEqual(self.injected, [])
        s = self.fc("status")
        self.assertEqual(s["unsent"]["comments"], [cid], "still unsent: no send entry was written")
        self.assertIsNone(s["unsent"]["watermark"])
        self.assertEqual([e["kind"] for e in s["log"]], [])
        # a client's own log-send is refused at the kernel too
        forged = self.fc("log-send", {"sid": SID, "comments": [], "accepted": 0, "rejected": 0, "queued": False,
                                      "watermark": 9007199254740000}, NO_STORE)
        self.assertEqual((forged["type"], forged["code"]), ("fileCommentsFailed", "kernel-only"))
        # the real send moves the derivation to the comment's own ts
        good = self.send_op(comments=[{"id": cid, "desc": "on this file", "body": "Which cache?"}], watermark=ts,
                            todoId=None)
        self.assertEqual(good["type"], "fileCommentsSent", good)
        self.assertNotIn("logWarning", good)
        s2 = self.fc("status")
        self.assertEqual(s2["unsent"]["comments"], [])
        self.assertEqual(s2["unsent"]["watermark"], ts)
        self.assertEqual([e["kind"] for e in s2["log"]], ["send"])
        self.assertEqual(len(self.injected), 1)


if __name__ == "__main__":
    unittest.main()
