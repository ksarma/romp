#!/usr/bin/env python3
"""File comments (plans/file-review.md, Slice 1) — the kernel side.

Two WebSocket ops beside saveFile: `fileComments` runs ONE sidecar verb through the node host script
(tools/file-comments-host.mjs) on the owning kernel's disk, and `fileCommentsSend` hands a file's
unsent comments to the owning session as one message in the person's voice, optionally answering
the user todo the file was opened from. saveFile appends a direct edit to the comments log before
its ack. The kernel is the door — path resolution, the file-editing consent BEFORE any content
check, the node probe, a bounded subprocess with the request on stdin and argv as a list — so the
host script here is a STUB written under the test's temp dir that records what it was handed and
answers as told (canned JSON, a non-zero exit, garbage, or a stall). The real host script has its
own node tests; the contract between the two is the request JSON pinned here.

Synthetic only: the notes-api demo world, a placeholder sid, temp dirs (tests/test_savefile.py's
hermetic pattern).
"""
import contextlib
import inspect
import io
import json
import os
import re
import shutil
import tempfile
import threading
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel_filecomments", os.path.join(BIN, "romp-kernel")).load_module()
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
NODE = shutil.which("node")

# The stub host script: records the request it read from stdin, whether TRACKCHANGES_ROOT reached its
# environment, and its argv tail, then answers as configured. ESM (.mjs) like the real script.
_STUB = """import fs from 'node:fs';
const CFG = %s;
let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (d) => { raw += d; });
process.stdin.on('end', () => {
  let request = null;
  try { request = JSON.parse(raw); } catch (e) { request = { parseError: String(e), raw }; }
  fs.writeFileSync(CFG.seen, JSON.stringify({ request,
    hasRoot: Object.prototype.hasOwnProperty.call(process.env, 'TRACKCHANGES_ROOT'),
    argv: process.argv.slice(2) }));
  if (CFG.write !== null && request && request.path) fs.writeFileSync(request.path, CFG.write);   // the host wrote the file…
  const finish = () => {
    if (CFG.stderr) process.stderr.write(CFG.stderr);
    if (CFG.stdout !== null) process.stdout.write(CFG.stdout);
    else process.stdout.write(JSON.stringify(CFG.reply));
    process.exit(CFG.exit);
  };
  const tick = () => { if (fs.existsSync(CFG.waitFor)) finish(); else setTimeout(tick, 20); };
  if (CFG.sleep) setTimeout(finish, CFG.sleep * 1000); else if (CFG.waitFor) tick(); else finish();
});
"""


@unittest.skipUnless(NODE, "node not installed on this machine")
class _Harness(unittest.TestCase):
    """A notes-api tree with a .trackchanges/ at its root, the consent on, and the kernel pointed at a
    stub host script under the temp dir."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "notes-api")
        os.makedirs(os.path.join(self.root, ".trackchanges"))
        os.makedirs(os.path.join(self.root, "docs"))
        self.fp = os.path.join(self.root, "docs", "report.md")
        with open(self.fp, "w") as f:
            f.write("# Findings\n\nThe api session cut p95 latency by 40%.\n")
        self.ns = os.stat(self.fp).st_mtime_ns
        self.seen_path = os.path.join(self.tmp, "seen.json")
        self.stub_path = os.path.join(self.tmp, "stub-host.mjs")
        self._saved = (km._FILE_COMMENTS_HOST, km._FILE_COMMENTS_TIMEOUT)
        km._FILE_COMMENTS_HOST = Path(self.stub_path)
        km._set_file_editing(True)
        self.stub()

    def tearDown(self):
        km._FILE_COMMENTS_HOST, km._FILE_COMMENTS_TIMEOUT = self._saved
        km._set_file_editing(False)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def stub(self, reply=None, exit=0, stderr="", stdout=None, sleep=0, wait_for=None, write=None):
        """(Re)write the stub host script: answer `reply` as JSON (or raw `stdout`), exit `exit`. `sleep`
        stalls the answer for that many seconds; `wait_for` holds it until that path exists (a gate the
        test opens, so a test about the wait itself needs no clock). `write` makes the stub rewrite the
        request's file with that text before it answers — the host that landed its writes and then died."""
        if reply is None:
            reply = {"ok": True, "verb": "status", "root": self.root, "storePath": None, "trackedBy": None,
                     "agentTooling": "absent", "fileMtimeNs": str(self.ns), "storeMtimeNs": None,
                     "configMtimeNs": None, "store": None, "hunks": [],
                     "unsent": {"comments": [], "replies": [], "accepted": 0, "rejected": 0, "watermark": None},
                     "log": [], "logTruncated": False}
        cfg = {"seen": self.seen_path, "reply": reply, "exit": exit, "stderr": stderr, "stdout": stdout,
               "sleep": sleep, "waitFor": wait_for, "write": write}
        with open(self.stub_path, "w") as f:
            f.write(_STUB % json.dumps(cfg))
        try:
            os.unlink(self.seen_path)
        except OSError:
            pass

    def seen(self):
        """What the stub was handed, or None when it never ran."""
        try:
            with open(self.seen_path) as f:
                return json.load(f)
        except OSError:
            return None


class _Wire(_Harness):
    """The real dispatcher with a fake client whose send() records the reply and wakes the test — the
    file-comments ops answer from their own thread, so the test waits for the reply instead of indexing
    sent[-1]. `dispatch` is what the recv loop does per frame and returns whenever the dispatcher does;
    `answered`/`wait_for` read the replies by reqId, so a test can hold an op open and look at what the
    dispatcher did meanwhile."""

    def setUp(self):
        super().setUp()
        self.sent, self.got, self.cv = [], threading.Event(), threading.Condition()

        def _send(s):
            with self.cv:
                self.sent.append(json.loads(s))
                self.got.set()
                self.cv.notify_all()
        self.client = {"app": "feed", "alive": True, "send": _send}
        self.handler = object.__new__(km.Handler)

    def dispatch(self, msg):
        """One frame through the dispatcher, no waiting — what the recv loop does per frame."""
        km.Handler._dispatch_ws(self.handler, msg, self.client)

    def send(self, msg, wait=True):
        self.got.clear()
        self.dispatch(msg)
        if wait:
            self.assertTrue(self.got.wait(20), "the op never answered")
        return self.sent[-1] if self.sent else None

    def answered(self, req_id):
        """Has a reply carrying this reqId reached the client yet?"""
        with self.cv:
            return any(r.get("reqId") == req_id for r in self.sent)

    def wait_for(self, req_id, timeout=20):
        """The reply carrying this reqId, waited for."""
        with self.cv:
            self.assertTrue(self.cv.wait_for(lambda: any(r.get("reqId") == req_id for r in self.sent), timeout),
                            "reqId %r never answered" % (req_id,))
            return next(r for r in self.sent if r.get("reqId") == req_id)


class TheDiskOp(_Harness):
    def op(self, **kw):
        msg = {"type": "fileComments", "reqId": 7, "sid": SID, "path": self.fp, "verb": "status"}
        msg.update(kw)
        return km._file_comments_op(msg)

    def test_a_verb_runs_the_host_with_the_request_on_stdin_and_echoes_reqid_and_verb(self):
        r = self.op()
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertEqual((r["reqId"], r["verb"]), (7, "status"))
        self.assertEqual(r["root"], self.root, "every host success field rides the reply")
        self.assertEqual(r["hunks"], [])
        self.assertNotIn("ok", r, "the host's ok flag is the kernel's, not the client's")
        s = self.seen()
        self.assertEqual(s["request"], {"verb": "status", "path": self.fp, "args": {}, "fence": None},
                         "one JSON request on stdin: the resolved path, the verb, empty args, no fence")
        self.assertEqual(s["argv"], [], "argv is the list [node, script] — nothing of the request in it")

    def test_args_and_fence_pass_through_untouched(self):
        self.stub(reply={"ok": True, "verb": "set-tracked", "trackedBy": {"kind": "file", "entry": "docs/report.md"}})
        r = self.op(verb="set-tracked", args={"on": True, "scope": "file"},
                    fence={"storeMtimeNs": "", "configMtimeNs": ""})
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertEqual(r["trackedBy"], {"kind": "file", "entry": "docs/report.md"})
        req = self.seen()["request"]
        self.assertEqual(req["args"], {"on": True, "scope": "file"})
        self.assertEqual(req["fence"], {"storeMtimeNs": "", "configMtimeNs": ""})

    def test_a_relative_path_resolves_against_the_sessions_cwd(self):
        real = km._cwd_of
        km._cwd_of = lambda sid: self.root if sid == SID else None
        try:
            r = self.op(path="docs/report.md")
        finally:
            km._cwd_of = real
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertEqual(self.seen()["request"]["path"], self.fp, "the host sees the absolute path only")

    def test_an_unresolvable_path_is_unreadable_and_never_reaches_the_host(self):
        for msg in ({"path": "docs/report.md", "sid": None}, {"path": ""}, {"path": None}):
            r = self.op(**msg)
            self.assertEqual(r["type"], "fileCommentsFailed", msg)
            self.assertEqual(r["code"], "unreadable", msg)
            self.assertEqual((r["reqId"], r["verb"]), (7, "status"))
        self.assertIsNone(self.seen(), "path resolution failed: nothing was run")

    def test_mutating_verbs_are_refused_while_editing_is_off_before_any_content_check(self):
        km._set_file_editing(False)
        gone = os.path.join(self.root, "docs", "missing.md")       # no such file: a content check would say so
        for verb in ("set-tracked", "comment", "reply", "resolve", "log-edit", "log-send", "accept", ""):
            r = self.op(verb=verb, path=gone)
            self.assertEqual(r["type"], "fileCommentsFailed", verb)
            self.assertEqual(r["code"], "editing-off", verb)
            self.assertIn("file editing is off", r["error"], "the phrase the viewer's regex matches")
            self.assertIn("missing.md", r["error"], "the refusal names the path")
            self.assertEqual(r["verb"], verb)
        self.assertIsNone(self.seen(), "the consent wall stands before the host ever runs")

    def test_status_is_the_one_verb_allowed_while_editing_is_off(self):
        km._set_file_editing(False)
        r = self.op(verb="status")
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertEqual(self.seen()["request"]["verb"], "status")

    def test_no_node_refuses_every_verb_quietly(self):
        real = km.shutil.which
        km.shutil.which = lambda name, *a, **k: None
        try:
            for verb in ("status", "comment"):
                r = self.op(verb=verb)
                self.assertEqual(r["type"], "fileCommentsFailed", verb)
                self.assertEqual(r["code"], "no-node", verb)
                self.assertIn("node", r["error"])
        finally:
            km.shutil.which = real
        self.assertIsNone(self.seen())

    def test_a_host_refusal_rides_back_with_its_own_code_and_error(self):
        self.stub(reply={"ok": False, "code": "store-moved",
                         "error": "the comments for ~/notes-api/docs/report.md changed on disk"})
        r = self.op(verb="comment", args={"note": "Which cache?"})
        self.assertEqual(r["type"], "fileCommentsFailed")
        self.assertEqual(r["code"], "store-moved")
        self.assertEqual(r["error"], "the comments for ~/notes-api/docs/report.md changed on disk")
        self.assertEqual((r["reqId"], r["verb"]), (7, "comment"))

    def test_a_crash_is_a_host_error_carrying_the_stderr_tail(self):
        self.stub(exit=3, stderr="x" * 2000 + "\nTypeError: boom at store-io.mjs:12\n")
        r = self.op()
        self.assertEqual(r["type"], "fileCommentsFailed")
        self.assertEqual(r["code"], "host-error")
        self.assertIn("exit 3", r["error"])
        self.assertIn("TypeError: boom", r["error"], "the tail of stderr rides the error")
        self.assertLess(len(r["error"]), 700, "…bounded, never the whole trace")

    def test_bad_stdout_is_a_host_error(self):
        for out in ("not json at all", "[1, 2]", ""):
            self.stub(stdout=out, stderr="warn: something")
            r = self.op()
            self.assertEqual(r["type"], "fileCommentsFailed", out)
            self.assertEqual(r["code"], "host-error", out)
            self.assertIn("JSON", r["error"])

    def test_the_deadline_is_a_host_error(self):
        km._FILE_COMMENTS_TIMEOUT = 1
        self.stub(sleep=6)
        r = self.op()
        self.assertEqual(r["type"], "fileCommentsFailed")
        self.assertEqual(r["code"], "host-error")
        self.assertIn("did not answer within 1 s", r["error"])

    def test_trackchanges_root_never_reaches_the_host(self):
        # TRACKCHANGES_ROOT overrides every file's root for the CLIs (survey item A8): a kernel that
        # inherited it would write every project's comments into one folder. Stripped from the child
        # env even when the parent carries it.
        os.environ["TRACKCHANGES_ROOT"] = os.path.join(self.tmp, "elsewhere")
        try:
            r = self.op()
        finally:
            del os.environ["TRACKCHANGES_ROOT"]
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertIs(self.seen()["hasRoot"], False)


class TheDiskOpOnTheWire(_Wire):
    def test_the_op_answers_the_sending_socket_with_the_request_id(self):
        r = self.send({"type": "fileComments", "reqId": 41, "sid": SID, "path": self.fp, "verb": "status"})
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertEqual((r["reqId"], r["verb"]), (41, "status"))

    def test_a_host_that_has_not_answered_holds_the_ops_thread_not_the_dispatcher(self):
        # The plan's reason for the thread (plans/file-review.md, Kernel: the receive loop never blocks
        # on the host script), end to end: the real op, a real node host that answers only once a gate
        # file exists. The reply cannot land before the gate opens, so a dispatcher that is back
        # BEFORE it opens was never waiting on the host — no clock in the assertion. A dispatcher that
        # ran the op inline would sit here until the host's 10 s deadline and come back with the
        # host-error already delivered.
        gate = os.path.join(self.tmp, "release")
        self.stub(wait_for=gate)
        try:
            self.dispatch({"type": "fileComments", "reqId": 43, "sid": SID, "path": self.fp, "verb": "status"})
            self.assertFalse(self.answered(43), "the dispatcher is back while the host is still running")
        finally:
            Path(gate).touch()
        r = self.wait_for(43)
        self.assertEqual((r["type"], r["reqId"], r["verb"]), ("fileCommentsResult", 43, "status"))
        self.assertEqual(self.seen()["request"]["verb"], "status", "the host ran and answered once released")


class TheOpsAnswerOffTheRecvLoop(_Wire):
    """Both frame types answer from their own thread, the fileGitLink shape (the contract sheet, C2; the
    plan: the host script is a subprocess with a deadline and the receive loop never waits on it).
    Pinned by BEHAVIOUR, not by the source text: a rewrite that ran the op before starting the thread,
    the thread only sending the reply, keeps every line a source pin looks for and every reply a
    waiting harness accepts, and holds the socket's recv loop for the full deadline on every verb (the
    review, 2026-09-06). So the op is swapped for one that cannot finish until the test lets it: the
    dispatcher must be back while the op is held, a second frame dispatched meanwhile must be answered
    while the first is still held, and the held one must still answer once released. Faked at the op,
    so the send frame needs no session world: what is under test is the reply helper's threading, the
    same for both frame types."""

    def frames(self):
        """(op attribute on km, success type, failure type, frame) for both frame types."""
        yield ("_file_comments_op", "fileCommentsResult", "fileCommentsFailed",
               {"type": "fileComments", "sid": SID, "path": self.fp, "verb": "status"})
        yield ("_file_comments_send_op", "fileCommentsSent", "fileCommentsSendFailed",
               {"type": "fileCommentsSend", "sid": SID, "path": self.fp, "tracked": True, "comments": ONE,
                "accepted": 0, "rejected": 0, "watermark": None, "todoId": None})

    def test_the_dispatcher_is_back_while_the_op_is_still_held(self):
        for attr, ok_type, _, frame in self.frames():
            with self.subTest(attr):
                self.sent.clear()
                release = threading.Event()
                real = getattr(km, attr)

                def held(m, ok_type=ok_type, release=release):
                    if m.get("reqId") == 1:
                        # A dispatcher that ran the op inline would wait here forever; the bound turns
                        # that hang into a failure (the reply is already in when dispatch returns).
                        release.wait(20)
                    return {"type": ok_type, "reqId": m.get("reqId"), "verb": "status"}
                setattr(km, attr, held)
                try:
                    self.dispatch(dict(frame, reqId=1))
                    self.assertFalse(self.answered(1), "%s: the dispatcher returned before the op finished" % attr)
                    self.dispatch(dict(frame, reqId=2))
                    r2 = self.wait_for(2)
                    self.assertFalse(self.answered(1), "%s: a later frame is served while the op is held" % attr)
                    release.set()
                    r1 = self.wait_for(1)
                finally:
                    release.set()
                    setattr(km, attr, real)
                self.assertEqual((r1["type"], r1["reqId"]), (ok_type, 1), "the held op still answers once released")
                self.assertEqual((r2["type"], r2["reqId"]), (ok_type, 2))

    def test_an_exception_inside_the_op_still_answers(self):
        # the saveFile lesson: a handler that raises sends nothing and the client hangs forever — for
        # both frame types, each with its own failure type
        for attr, _, fail_type, frame in self.frames():
            with self.subTest(attr):
                real = getattr(km, attr)

                def boom(m):
                    raise RuntimeError("kernel bug")
                setattr(km, attr, boom)
                try:
                    r = self.send(dict(frame, reqId=42))
                finally:
                    setattr(km, attr, real)
                self.assertEqual(r["type"], fail_type)
                self.assertEqual((r["reqId"], r["code"]), (42, "host-error"))
                self.assertIn("kernel bug", r["error"])


class _TraceWorld(_Wire):
    """The wire harness with the trace ARMED and every door to the session spied on. TheDiskOp's world
    cannot tell whether a verb traces: its state root has no names registry, so a trace added to the
    op finds no live tree containing the file, returns quietly, and the suite stays green. Here one
    live session's recorded cwd is the notes-api root (so _edit_trace_sid resolves the file to it),
    the backend's send and _send_or_park are both recorded, _edit_trace and _reject_trace are each
    counted, and `order` writes down whether the client's reply or a backend send came first. Through
    the wire rather than the op alone: saveFile's trace sits in _dispatch_ws after its reply, so a
    trace could land beside the op, in the reply thread, or in the dispatcher, and the op's thread is
    joined after the answer so a trace fired after the reply is still counted."""

    def setUp(self):
        super().setUp()
        self._saved3 = (km._tmux_sessions, km._cwd_of, km.Sessions.__dict__["backend_for"],
                        km._send_or_park, km._edit_trace, km._reject_trace)
        km._tmux_sessions = lambda: {SID: {}}
        km._cwd_of = lambda s: self.root if s == SID else ""
        self.reached, self.parked, self.traced, self.reject_traced, self.order = [], [], [], [], []
        world = self
        client_send = self.client["send"]

        def ordered_send(s):
            world.order.append("reply")
            client_send(s)
        self.client["send"] = ordered_send

        class _FakeBE:
            def send(self, sid, text, *a, **k):
                world.order.append("trace")
                world.reached.append((sid, text))
                return True
        km.Sessions.backend_for = staticmethod(lambda sid: _FakeBE())

        def fake_send_or_park(be, sid, text, echo=None, user_todo=None):
            self.parked.append((sid, text))
            return True
        km._send_or_park = fake_send_or_park
        real_trace, real_reject_trace = self._saved3[4], self._saved3[5]

        def counted_trace(path, sid):
            self.traced.append((path, sid))
            return real_trace(path, sid)
        km._edit_trace = counted_trace

        def counted_reject_trace(path, sid, n):
            self.reject_traced.append((path, sid, n))
            return real_reject_trace(path, sid, n)
        km._reject_trace = counted_reject_trace

    def tearDown(self):
        km._tmux_sessions, km._cwd_of, bf, km._send_or_park, km._edit_trace, km._reject_trace = self._saved3
        km.Sessions.backend_for = bf
        super().tearDown()

    def verb(self, verb, args, reply=None, fence=None, exit=0, write=None):
        """One fileComments verb through the dispatcher, the stub answering ok — `reply` adds to or
        overrides that answer, the way the real host's carries `accepted`/`rejected` or a refusal; `exit`
        and `write` are the stub's (a host that died, a host that wrote the file first). The op answers
        from its own thread and may run on past the reply, so that thread is joined before the asserts."""
        rep = {"ok": True, "verb": verb}
        rep.update(reply or {})
        self.stub(reply=rep, exit=exit, write=write)
        if fence is None and verb != "status":
            fence = {"storeMtimeNs": ""}
        before = set(threading.enumerate())
        r = self.send({"type": "fileComments", "reqId": 11, "sid": SID, "path": self.fp, "verb": verb,
                       "args": args, "fence": fence})
        for t in set(threading.enumerate()) - before:
            t.join(20)
        return r


class SidecarOnlyVerbsTellTheSessionNothing(_TraceWorld):
    """Consent, trace, routing (plans/file-review.md; decision 7): a verb that touches only the
    sidecar or the config — set-tracked, comment, reply, resolve, and Slice 2's accept — sends the
    owning session NOTHING. The sent message is the notification; a trace hooked onto every
    mutating verb would announce each comment the moment it landed. The two log verbs are the
    kernel's own (log-edit after a save, log-send after a send): from a client they are refused
    `kernel-only` before the host runs, and that refusal tells the session nothing either — the
    kernel's own log-edit runs inside saveFile, whose one trace the control test counts. The world
    proves its arming with a direct edit through the same dispatcher (a save IS told to the session,
    as today), then runs the sidecar-only verbs and asserts that nothing reached the session by
    either door. Reject, the verb that DOES change the file, is RejectTellsTheSession's."""

    def test_a_direct_edit_is_told_to_the_session_in_this_world(self):
        # the control: same world, same file, same dispatcher — the spies see a save's trace, so the
        # silence in the next test is the policy, not a spy that never armed
        self.stub(reply={"ok": True, "verb": "log-edit", "logged": True})
        r = self.send({"type": "saveFile", "sid": SID, "path": self.fp, "reqId": 3, "baseMtimeNs": str(self.ns),
                       "content": "# Findings\n\nThe api session cut p95 latency by 45%.\n"}, wait=False)
        self.assertEqual(r["type"], "fileSaved")
        self.assertEqual(self.traced, [(self.fp, SID)])
        self.assertEqual([sid for sid, _ in self.reached], [SID])
        self.assertIn("I just edited", self.reached[0][1])
        self.assertEqual(self.parked, [], "the trace goes straight to the backend, never through the todo helper")

    def test_the_sidecar_only_verbs_send_nothing_by_either_door(self):
        self.assertEqual(km._edit_trace_sid(self.fp, SID), SID, "armed: a trace from here WOULD reach the session")
        verbs = [
            ("status", {}),
            ("set-tracked", {"on": True, "scope": "file"}),
            ("comment", {"anchor": "shipping the cache in v1.2", "note": "Which cache? Say which."}),
            ("comment", {"note": "Add a summary table at the top."}),
            ("reply", {"commentId": "1781100000000-0", "note": "Still the wrong cache."}),
            ("resolve", {"commentId": "1781100000000-0", "on": True}),
            # Slice 2's accept keeps the new text and drops the record: sidecar-only, so it belongs here
            # (reject changes file bytes and WILL trace — that half of the pair lands with Slice 2). The
            # kernel is verb-agnostic, so the policy is pinned before the verb exists.
            ("accept", {"ids": ["1781100000000-1"]}),
            ("accept-all", {}),
            ("set-tracked", {"on": False, "scope": "file"}),
        ]
        for verb, args in verbs:
            r = self.verb(verb, args)
            self.assertEqual(r["type"], "fileCommentsResult", verb)
            self.assertEqual(self.seen()["request"]["verb"], verb, "the verb ran: the silence is not a refusal")
        # The kernel's own log verbs, asked for by a client: refused `kernel-only` (the kernel appends those
        # entries itself; tests/test_kernel_file_comments_hardening.py ClientVerbsStopAtTheKernel), the host
        # never runs, and the refusal is as silent toward the session as a verb that ran.
        kernel_only = [
            ("log-edit", {"summary": {"mtimeBeforeNs": str(self.ns), "mtimeAfterNs": str(self.ns), "bytesBefore": 47,
                                      "bytesAfter": 47, "diff": "", "truncated": False}}),
            ("log-send", {"sid": SID, "comments": ONE, "accepted": 0, "rejected": 0, "queued": False,
                          "watermark": 1781100000000}),
        ]
        for verb, args in kernel_only:
            r = self.verb(verb, args)
            self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "kernel-only"), verb)
            self.assertIsNone(self.seen(), "%s from a client: the host never ran" % verb)
        self.assertEqual(self.traced, [], "no edit trace after a sidecar-only verb (decision 7)")
        self.assertEqual(self.reached, [], "nothing reached the session's backend")
        self.assertEqual(self.parked, [], "and nothing went through the todo-reply delivery helper")


class RejectTellsTheSession(_TraceWorld):
    """Consent, trace, routing (plans/file-review.md; the Slice 2 contract, D3): reject and reject-all
    change the FILE's bytes — the host writes the reverse edits into it and drops the records from the
    sidecar — so, like a save, they are told to the session whose tree holds the file: ONE trace, in the
    person's voice, AFTER the reply (saveFile's order: the client's button is released, then the
    backend send). Whether to trace and the count both come from the host's reply — `rejected`, the ids
    it actually resolved — never from the request: the ids a client asked for may have coalesced,
    landed already, or been refused by id. The stub plays the host; the real verbs are the host's own
    node tests' concern."""

    IDS = ["1781100000000-1", "1781100000000-2"]

    def fence(self):
        return {"storeMtimeNs": "1781100000000000000", "configMtimeNs": "", "fileMtimeNs": str(self.ns)}

    def test_a_reject_is_told_once_after_the_reply_with_the_count_and_the_path(self):
        r = self.verb("reject", {"ids": self.IDS}, reply={"rejected": self.IDS, "fileMtimeNs": str(self.ns)},
                      fence=self.fence())
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertEqual(r["rejected"], self.IDS, "the host's list rides back to the client untouched")
        real = os.path.realpath(self.fp)
        self.assertEqual(self.reject_traced, [(real, SID, 2)], "one trace, on the real path the sidecar keys on")
        self.assertEqual([sid for sid, _ in self.reached], [SID], "exactly one send, to the owning session")
        body = self.reached[0][1]
        self.assertEqual(body, km._reject_trace_body(real, 2))
        self.assertIn("I rejected 2 of your tracked changes in %s while reading it; the file and its sidecar both "
                      "changed, so re-read it before writing." % km._tilde(real), body)
        self.assertIn("romp-injected", body, "the trace renders as an injected (gray) message")
        self.assertEqual(self.order, ["reply", "trace"], "the fileCommentsResult is on the wire before the trace goes")
        self.assertEqual(self.traced, [], "the edit trace is a save's; a reject has its own")
        self.assertEqual(self.parked, [], "straight to the backend, never through the todo-reply helper")

    def test_reject_all_is_told_the_same_way(self):
        ids = self.IDS + ["1781100000000-3"]
        r = self.verb("reject-all", {}, reply={"rejected": ids, "fileMtimeNs": str(self.ns)}, fence=self.fence())
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertEqual(self.reject_traced, [(os.path.realpath(self.fp), SID, 3)])
        self.assertEqual(len(self.reached), 1)
        self.assertIn("I rejected 3 of your tracked changes in", self.reached[0][1])
        self.assertEqual(self.order, ["reply", "trace"])

    def test_a_reject_that_resolved_nothing_is_not_told(self):
        # the host answered ok with an empty list: nothing left the sidecar and the file did not change
        r = self.verb("reject", {"ids": self.IDS}, reply={"rejected": []}, fence=self.fence())
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertEqual(self.reject_traced, [])
        self.assertEqual(self.reached, [])

    def test_a_refused_reject_is_not_told(self):
        for code in ("file-moved", "store-moved", "too-large", "no-change"):
            r = self.verb("reject", {"ids": self.IDS},
                          reply={"ok": False, "code": code, "error": "cannot reject the changes in ~/x: " + code},
                          fence=self.fence())
            self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", code))
        self.assertEqual(self.reject_traced, [])
        self.assertEqual(self.reached, [], "a refusal changed nothing, so there is nothing to tell")

    def test_accept_and_comment_are_not_told_even_with_ids_resolved(self):
        # accept keeps the new text and drops the record: the file's bytes are unchanged, and the sent
        # message carries the decision; a comment is the plan's own listed non-trace
        self.verb("accept", {"ids": self.IDS}, reply={"accepted": self.IDS})
        self.verb("accept-all", {}, reply={"accepted": self.IDS + ["1781100000000-3"], "store": None, "hunks": []})
        self.verb("comment", {"anchor": "shipping the cache in v1.2", "note": "Which cache? Say which."})
        self.verb("comment", {"suggestionId": self.IDS[0], "note": "Keep the old word."})
        self.assertEqual(self.reject_traced, [])
        self.assertEqual(self.reached, [])
        self.assertEqual(self.parked, [])

    def test_a_successful_reject_without_the_list_is_loud_and_tells_nothing(self):
        # a contract break between the host and the kernel: the file may have changed, but the kernel
        # will not guess a count to tell the session — it says so on stderr instead (no silent fallback)
        for reply in ({}, {"rejected": 2}, {"rejected": "1781100000000-1"}):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                r = self.verb("reject", {"ids": self.IDS}, reply=reply, fence=self.fence())
            self.assertEqual(r["type"], "fileCommentsResult", reply)
            self.assertIn("without a `rejected` list", err.getvalue(), reply)
        self.assertEqual(self.reject_traced, [])
        self.assertEqual(self.reached, [])

    def test_a_host_that_wrote_the_file_and_then_died_still_tells_the_session_without_a_count(self):
        # the host landed the sidecar and the file, then died before its reply (killed after the rename, or
        # failing inside the status it builds after the writes): the kernel answers host-error, and the file
        # on disk is not what the session last wrote — the never-lose-the-thread rule says tell it
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            r = self.verb("reject", {"ids": self.IDS}, fence=self.fence(), exit=1, write="# Report\n\nreverted text\n")
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "host-error"))
        self.assertIs(r["fileChanged"], True, "the failure says the file moved under it")
        self.assertIn("The file itself changed on disk during the request", r["error"])
        real = os.path.realpath(self.fp)
        self.assertEqual(self.reject_traced, [(real, SID, None)], "one trace, with no count to claim")
        self.assertEqual([sid for sid, _ in self.reached], [SID])
        body = self.reached[0][1]
        self.assertEqual(body, km._reject_trace_body(real, None))
        self.assertIn("I rejected some of your tracked changes in %s while reading it; the file and its sidecar both "
                      "changed, so re-read it before writing." % km._tilde(real), body)
        self.assertNotIn(" 0 of ", body, "never a number the kernel would have to guess")
        self.assertEqual(self.order, ["reply", "trace"], "the failure is on the wire before the trace goes")

    def test_a_host_that_died_without_writing_tells_nothing_and_a_refusal_after_a_write_is_someone_elses(self):
        r = self.verb("reject", {"ids": self.IDS}, fence=self.fence(), exit=1)
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "host-error"))
        self.assertNotIn("fileChanged", r, "the file is as it was: nothing to report beyond the failure")
        self.assertNotIn("changed on disk", r["error"])
        # the host's own refusal writes nothing, so a file that moved under it was moved by someone else —
        # the session's own write, which it knows about; and a sidecar-only verb never stats the file at all
        self.verb("reject", {"ids": self.IDS}, reply={"ok": False, "code": "file-moved", "error": "~/x changed"},
                  fence=self.fence(), write="# Report\n\nthe session's own write\n")
        self.verb("accept", {"ids": self.IDS}, exit=1, write="# Report\n\nanother write\n")
        self.assertEqual(self.reject_traced, [])
        self.assertEqual(self.reached, [])

    def test_a_file_outside_every_live_tree_is_nobodys_to_tell(self):
        km._cwd_of = lambda s: os.path.join(self.tmp, "elsewhere")      # the one live session works somewhere else
        self.verb("reject", {"ids": self.IDS}, reply={"rejected": self.IDS}, fence=self.fence())
        self.assertEqual(len(self.reject_traced), 1, "the trace ran")
        self.assertEqual(self.reached, [], "and found no session whose tree holds the file")

    def test_the_trace_runs_after_the_reply_even_when_it_raises(self):
        # a backend that fails does not cost the client its answer, and says so on stderr
        class _Broken:
            def send(self, sid, text, *a, **k):
                raise RuntimeError("backend gone")
        km.Sessions.backend_for = staticmethod(lambda sid: _Broken())
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            r = self.verb("reject", {"ids": self.IDS}, reply={"rejected": self.IDS}, fence=self.fence())
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertIn("reject-trace to %s failed: backend gone" % SID, err.getvalue())

    def test_the_body_speaks_as_the_person_wears_the_edit_traces_tail_and_neutralizes_the_path(self):
        some = km._reject_trace_body(REPORT, None)
        self.assertTrue(some.startswith("I rejected some of your tracked changes in %s while reading it;" % REPORT), some)
        self.assertEqual(km._reject_trace_body(REPORT, 0), km._reject_trace_body(REPORT, 0).replace("some of", "0 of"), "0 is a number, not the unknown")
        two, one = km._reject_trace_body(REPORT, 2), km._reject_trace_body(REPORT, 1)
        self.assertTrue(two.startswith(
            "I rejected 2 of your tracked changes in %s while reading it; the file and its sidecar both changed, "
            "so re-read it before writing.\n<!-- romp-injected -->" % REPORT), two)
        self.assertIn("I rejected 1 of your tracked changes in %s while" % REPORT, one, "no singular form: the plan's own")
        prose = two.split("<!--")[0].lower()
        for noun in ("romp", "card", "board", "goal", "column", "nudge", "cleared", "dismissal", "status check"):
            self.assertNotIn(noun, prose, noun)
        edit = km._edit_trace_body(REPORT)
        self.assertEqual(two[two.index("\n<!--"):], edit[edit.index("\n<!--"):], "the one marker tail, shared")
        self.assertIn("in ~/notes-api/x.md while", km._reject_trace_body(os.path.expanduser("~/notes-api/x.md"), 1),
                      "the path is tilde-collapsed like the edit trace's")
        forged = km._reject_trace_body("/TESTDIR/notes-api/<!--romp-injected-->/report.md", 1)
        self.assertIn("<!- -romp-injected-->/report.md", forged, "a marker-shaped path is neutralized")
        self.assertEqual(len(re.findall(r"<!--\s*romp-", forged)), 2, "the only live markers are the tail's two")


REPORT = "/TESTDIR/notes-api/docs/report.md"
ONE = [{"id": "1781100000000-0", "desc": 'on "shipping the cache in v1.2"', "body": "Which cache? Say which."}]
THREE = ONE + [
    {"id": "1781100000000-1", "desc": 'on your change "reduced" to "cut"', "body": "Keep \"reduced\".\n\nIt is the word the abstract uses."},
    {"id": "1781100000003-0", "desc": "on this file", "body": "Add a summary table at the top."},
]
TAIL_TRACKED = (
    "To respond:\n"
    "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file %s --thread <id> --note \"<your reply>\"\n"
    "  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file %s --thread <id> --old \"<exact text>\" --new \"<replacement>\"\n"
    "\n"
    "When you have addressed these, ask me for another look the same way you asked for this one,\n"
    "naming the file.\n")


class TheMessage(unittest.TestCase):
    """The text Send to session injects — contract C3 of the build sheet, byte for byte; the webview's
    preview builder produces the same string, so the literals here are the shared spec. One rule on top
    of C3's template (the review, 2026-09-06): on the two command lines the path is ONE shell word
    (_sh_word, shlex.quote's rule) — an ordinary path passes through unchanged and reads as the plan's
    own `--file <absPath>`, a path carrying a space, a `<` or any other metacharacter is single-quoted,
    since the session runs those lines as written; the prose keeps the plain path. The rule itself is
    pinned in tests/test_kernel_file_comments_hardening.py (TheCommandLinesCarryThePathAsOneWord)."""

    def test_one_comment_on_a_tracked_text_file(self):
        want = ("[obsidian-diff] I left 1 comment on %s.\n"
                "\n"
                "Comment 1781100000000-0 (on \"shipping the cache in v1.2\"):\n"
                "Which cache? Say which.\n"
                "\n" % REPORT) + TAIL_TRACKED % (REPORT, REPORT)
        self.assertEqual(km._file_comments_message(REPORT, ONE, 0, 0, True, True), want)

    def test_several_comments_are_separated_by_one_blank_line(self):
        want = ("[obsidian-diff] I left 3 comments on %s.\n"
                "\n"
                "Comment 1781100000000-0 (on \"shipping the cache in v1.2\"):\n"
                "Which cache? Say which.\n"
                "\n"
                "Comment 1781100000000-1 (on your change \"reduced\" to \"cut\"):\n"
                "Keep \"reduced\".\n"
                "\n"
                "It is the word the abstract uses.\n"
                "\n"
                "Comment 1781100000003-0 (on this file):\n"
                "Add a summary table at the top.\n"
                "\n" % REPORT) + TAIL_TRACKED % (REPORT, REPORT)
        self.assertEqual(km._file_comments_message(REPORT, THREE, 0, 0, True, True), want)

    def test_the_decisions_line_appears_only_when_there_was_a_decision(self):
        body = km._file_comments_message(REPORT, ONE, 4, 1, True, True)
        self.assertIn("Which cache? Say which.\n"
                      "\n"
                      "I accepted 4 of your changes and rejected 1.\n"
                      "\n"
                      "To respond:\n", body)
        self.assertNotIn("I accepted", km._file_comments_message(REPORT, ONE, 0, 0, True, True))
        self.assertIn("I accepted 0 of your changes and rejected 2.\n",
                      km._file_comments_message(REPORT, ONE, 0, 2, True, True))
        # Slice 2's Send: the accept-pending-changes checkbox adds N to accepted with nothing rejected —
        # A + R > 0, so the line renders, blank line after (contract C3 / D3). With no comments the send
        # wears the DECISIONS-ONLY shape (the review, 2026-09-06): it never says "I left 0 comments" over
        # two `--thread <id>` command lines with no thread to name. That shape is pinned byte for byte in
        # tests/test_kernel_file_comments_decisions_send.py; this checks the line and its blank lines
        body = km._file_comments_message(REPORT, [], 3, 0, True, True)
        self.assertIn("[obsidian-diff] I went over %s.\n"
                      "\n"
                      "I accepted 3 of your changes and rejected 0.\n"
                      "\n"
                      "No comments this time, so nothing needs a reply.\n" % REPORT, body)
        self.assertNotIn("0 comments", body)
        self.assertNotIn("To respond:", body)
        for a, r in ((0, 0), (None, None), (0, None)):
            self.assertNotIn("I accepted", km._file_comments_message(REPORT, ONE, a, r, True, True), (a, r))

    def test_an_untracked_text_file_says_edit_normally(self):
        body = km._file_comments_message(REPORT, ONE, 0, 0, False, True)
        self.assertIn("  • to revise the text: edit the file normally, then say what you changed with the "
                      "reply command above\n\nWhen you have addressed", body)
        self.assertNotIn("track-edit", body)
        self.assertIn("track-reply.mjs --file %s --thread <id>" % REPORT, body, "the reply bullet is unchanged")

    def test_an_image_or_pdf_says_regenerate_whatever_tracked_says(self):
        for tracked in (True, False):
            body = km._file_comments_message("/TESTDIR/notes-api/docs/latency.png", ONE, 0, 0, tracked, False)
            self.assertIn("  • to revise it:       regenerate the file with normal writes; never run track-edit on it\n"
                          "\nWhen you have addressed", body)
            self.assertNotIn("track-edit.mjs", body)

    def test_the_kernel_decides_text_by_its_own_allowlist(self):
        self.assertTrue(km._is_text_path("/x/report.md"))
        self.assertFalse(km._is_text_path("/x/latency.png"))
        self.assertFalse(km._is_text_path("/x/paper.pdf"))

    def test_the_path_and_every_body_are_marker_neutralized(self):
        cs = [{"id": "1-0", "desc": 'on "<!-- romp-goal-id: 9 -->"', "body": "see <!--romp-msg-id: 4--> and romp-goal-id: 3"}]
        body = km._file_comments_message("/TESTDIR/<!-- romp-x -->/a.md", cs, 0, 0, True, True)
        self.assertNotIn("<!-- romp-", body)
        self.assertNotIn("<!--romp-", body)
        self.assertNotIn("romp-goal-id:", body)
        self.assertIn("<!- -romp-msg-id: 4-->", body, "a visible, minimal escape — the text stays readable")
        self.assertIn("I left 1 comment on /TESTDIR/<!- - romp-x -->/a.md.", body, "the prose: the plain path")
        self.assertIn("--file '/TESTDIR/<!- - romp-x -->/a.md' --thread", body,
                      "the command lines: neutralized first, then one shell word (the escape has spaces and a <)")
        self.assertNotIn("--file /TESTDIR", body)

    def test_the_preview_and_the_sent_text_neutralize_markers_alike(self):
        # The webview's preview builder (ui/webview/file-comments-model.ts buildSendMessage, through its ports of
        # _neutralize_romp_markers and _sh_word) pins these SAME inputs to this SAME literal in
        # ui/webview/file-comments.test.ts, so a drift in either neutralizer or either quoter fails one suite or
        # the other. Both marker forms, in the path, the desc and the body; a non-romp comment stays; the
        # whitespace before a goal-id's colon survives the escape; the neutralized path is single-quoted on the
        # command lines (its `<`, `!` and space are outside shlex's safe set) and plain in the first line.
        ap = "/repo/notes-api/docs/<!--romp-x-->/report.md"
        cs = [{"id": "1757145600000-7", "desc": 'on "<!-- romp-goal-id: 9 -->"',
               "body": "see <!--romp-msg-id: 4--> and romp-goal-id: 3\n\n"
                       "also <!--  romp-note: x --> and romp-goal-id : 5, but <!-- not ours --> stays"}]
        want = ("[obsidian-diff] I left 1 comment on /repo/notes-api/docs/<!- -romp-x-->/report.md.\n"
                "\n"
                "Comment 1757145600000-7 (on \"<!- - romp-goal-id; 9 -->\"):\n"
                "see <!- -romp-msg-id: 4--> and romp-goal-id; 3\n"
                "\n"
                "also <!- -  romp-note: x --> and romp-goal-id ; 5, but <!-- not ours --> stays\n"
                "\n"
                "To respond:\n"
                "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file '/repo/notes-api/docs/<!- -romp-x-->/report.md' --thread <id> --note \"<your reply>\"\n"
                "  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file '/repo/notes-api/docs/<!- -romp-x-->/report.md' --thread <id> --old \"<exact text>\" --new \"<replacement>\"\n"
                "\n"
                "When you have addressed these, ask me for another look the same way you asked for this one,\n"
                "naming the file.\n")
        self.assertEqual(km._file_comments_message(ap, cs, 0, 0, True, True), want)

    def test_the_file_word_literals(self):
        # ui/webview/file-comments.test.ts ("the --file word ...") pins the webview's builder to these SAME three
        # texts: a path with a space (single-quoted on the command lines, plain in the prose), one with a quote
        # (the quote becomes '"'"' inside the single quotes), and an empty one (''). The kernel never sends an
        # empty path — _file_comments_send_op refuses first — but the builders must agree on every input the
        # type admits, or the preview shows text the session never receives.
        one = [{"id": "1757145600000-118", "desc": "on this file", "body": "Good."}]
        tail = ("\n"
                "When you have addressed these, ask me for another look the same way you asked for this one,\n"
                "naming the file.\n")
        self.assertEqual(km._file_comments_message("/repo/notes-api/vault/Meeting notes.md", one, 0, 0, True, True),
                         "[obsidian-diff] I left 1 comment on /repo/notes-api/vault/Meeting notes.md.\n"
                         "\n"
                         "Comment 1757145600000-118 (on this file):\n"
                         "Good.\n"
                         "\n"
                         "To respond:\n"
                         "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file '/repo/notes-api/vault/Meeting notes.md' --thread <id> --note \"<your reply>\"\n"
                         "  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file '/repo/notes-api/vault/Meeting notes.md' --thread <id> --old \"<exact text>\" --new \"<replacement>\"\n"
                         + tail)
        self.assertEqual(km._file_comments_message("/repo/notes-api/vault/it's here.md", one, 0, 0, False, True),
                         "[obsidian-diff] I left 1 comment on /repo/notes-api/vault/it's here.md.\n"
                         "\n"
                         "Comment 1757145600000-118 (on this file):\n"
                         "Good.\n"
                         "\n"
                         "To respond:\n"
                         "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file '/repo/notes-api/vault/it'\"'\"'s here.md' --thread <id> --note \"<your reply>\"\n"
                         "  • to revise the text: edit the file normally, then say what you changed with the reply command above\n"
                         + tail)
        self.assertIs(km._is_text_path(""), False, "no extension, no text-by-convention name: non-text, as the webview's isTextPath says")
        self.assertEqual(km._file_comments_message("", one, 0, 0, True, km._is_text_path("")),
                         "[obsidian-diff] I left 1 comment on .\n"
                         "\n"
                         "Comment 1757145600000-118 (on this file):\n"
                         "Good.\n"
                         "\n"
                         "To respond:\n"
                         "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file '' --thread <id> --note \"<your reply>\"\n"
                         "  • to revise it:       regenerate the file with normal writes; never run track-edit on it\n"
                         + tail)

    def test_the_text_ends_with_exactly_one_newline_and_names_no_machinery(self):
        body = km._file_comments_message(REPORT, THREE, 0, 0, True, True)
        self.assertTrue(body.endswith("naming the file.\n"))
        self.assertFalse(body.endswith("\n\n"))
        self.assertNotIn("<!--", body, "no marker tail: this is the person's own message, like a todo answer")
        for word in ("romp", "card", "board", "goal", "nudge"):
            self.assertNotIn(word, body.lower())


class _SendWorld(_Harness):
    """The send op's world: a STATE sandbox with user todos ON, a known session (`web`) owned by the
    tmux backend (no SDK), and _send_or_park scripted — the DriveOps idiom of tests/test_user_todos.py."""

    def setUp(self):
        super().setUp()
        self.td = tempfile.TemporaryDirectory()
        self.saved_state = jd.STATE
        jd.STATE = Path(self.td.name)
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._set_user_todos(True)
        km._set_file_editing(True)                    # the state root moved: re-open the consent there
        self._saved2 = (km._name_of, km._sdk, km._send_or_park)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        self.injected, self.send_result = [], True

        def fake_send_or_park(be, sid, text, echo=None, user_todo=None):
            self.injected.append({"sid": sid, "text": text, "echo": echo, "user_todo": user_todo, "be": be})
            return self.send_result
        km._send_or_park = fake_send_or_park
        self.tid = km._add_user_todo(SID, "Need a look at the findings report", self.fp)
        self.stub(reply={"ok": True, "verb": "log-send", "logged": True})

    def tearDown(self):
        km._name_of, km._sdk, km._send_or_park = self._saved2
        jd.STATE = self.saved_state
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        self.td.cleanup()
        super().tearDown()

    def send(self, **kw):
        msg = {"type": "fileCommentsSend", "reqId": 9, "sid": SID, "path": self.fp, "tracked": True,
               "comments": ONE, "accepted": 0, "rejected": 0, "watermark": 1781100000000, "todoId": self.tid}
        msg.update(kw)
        return km._file_comments_send_op(msg)

    def todo(self):
        return km._user_todos()[SID][0]


class TheSendOp(_SendWorld):
    def test_a_sent_message_is_the_contract_text_answers_the_todo_and_is_logged(self):
        r = self.send()
        self.assertEqual(r, {"type": "fileCommentsSent", "reqId": 9, "queued": False})
        self.assertEqual(len(self.injected), 1)
        inj = self.injected[0]
        self.assertEqual(inj["text"], km._file_comments_message(self.fp, ONE, 0, 0, True, True))
        self.assertTrue(inj["text"].startswith("[obsidian-diff] I left 1 comment on %s.\n" % self.fp))
        self.assertEqual(inj["user_todo"], self.tid, "the todo id rides the send for the park path")
        self.assertEqual(inj["echo"], "human", "a tmux-owned session gets the kernel-side echo, as the todo Reply does")
        self.assertEqual(self.todo()["resolved"]["kind"], "answered", "delivered now → stamped now")
        s = self.seen()
        self.assertEqual(s["request"]["verb"], "log-send")
        self.assertEqual(s["request"]["path"], self.fp)
        args = s["request"]["args"]
        self.assertEqual(args["sid"], SID)
        self.assertEqual(args["sessionName"], "web")
        self.assertEqual(args["comments"], ONE)
        self.assertEqual((args["accepted"], args["rejected"], args["queued"], args["watermark"]),
                         (0, 0, False, 1781100000000),
                         "the watermark reaches the log as the number the host's log-send takes (number|null)")

    def test_a_parked_send_is_queued_and_stamps_later(self):
        self.send_result = "parked"
        r = self.send()
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIs(r["queued"], True)
        self.assertEqual(self.injected[0]["user_todo"], self.tid, "the drain stamps from the op's 4th slot")
        self.assertNotIn("resolved", self.todo(), "parked ≠ delivered: the ✕ can still recall it")
        self.assertIs(self.seen()["request"]["args"]["queued"], True, "the log says it was queued")

    def test_a_refused_send_fails_the_op_and_logs_nothing(self):
        self.send_result = False
        r = self.send()
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertEqual(r["reqId"], 9)
        self.assertIn("didn't take it", r["error"])
        self.assertNotIn("resolved", self.todo())
        self.assertIsNone(self.seen(), "no send entry for a message that never went")

    def test_switch_off_sends_warns_and_stamps_nothing(self):
        # the todo Reply sends nothing here; Send to session sends — the comments are the point,
        # the stamp a convenience — and says why nothing was marked
        km._set_user_todos(False)
        r = self.send()
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIn("turned off", r["warning"])
        self.assertEqual(len(self.injected), 1, "the message went")
        self.assertIsNone(self.injected[0]["user_todo"], "no id rides a send that must not stamp")
        km._set_user_todos(True)
        km._user_todos_cache.clear()
        self.assertNotIn("resolved", self.todo())
        self.assertEqual(self.seen()["request"]["verb"], "log-send")

    def test_a_settled_todo_sends_warns_and_stamps_nothing(self):
        r = self.send(todoId="ut-deadbeef")
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIn("already settled", r["warning"])
        self.assertEqual(len(self.injected), 1)
        self.assertIsNone(self.injected[0]["user_todo"])
        self.assertNotIn("resolved", self.todo(), "the real open todo is untouched")

    def test_an_ended_session_refuses_with_the_revive_text_and_sends_nothing(self):
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        r = self.send()
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertIn("has ended", r["error"])
        self.assertIn("Revive the session", r["error"])
        self.assertEqual(self.injected, [], "nothing into the void")
        self.assertNotIn("resolved", self.todo())
        self.assertIsNone(self.seen())

    def test_an_ended_session_refuses_even_without_a_todo(self):
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps({"t": 1781200000, "by": "gone"}))
        r = self.send(todoId=None)
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertEqual(self.injected, [])

    def test_without_a_todo_the_message_goes_and_nothing_is_stamped(self):
        r = self.send(todoId=None)
        self.assertEqual(r, {"type": "fileCommentsSent", "reqId": 9, "queued": False})
        self.assertIsNone(self.injected[0]["user_todo"])
        self.assertNotIn("resolved", self.todo(), "the open todo stays open: this send did not answer it")

    def test_a_session_this_kernel_lacks_is_refused_before_anything_runs(self):
        r = self.send(sid="99999999-8888-7777-6666-555555555555")
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertIn("no session with id", r["error"])
        self.assertEqual(self.injected, [])
        self.assertIsNone(self.seen())

    def test_nothing_unsent_is_a_refusal_not_an_empty_message(self):
        r = self.send(comments=[], accepted=0, rejected=0)
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertIn("no unsent comments", r["error"])
        self.assertEqual(self.injected, [])

    def test_decisions_alone_are_worth_a_message(self):
        r = self.send(comments=[], accepted=2, rejected=1)
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIn("I accepted 2 of your changes and rejected 1.", self.injected[0]["text"])

    def test_tracked_and_the_file_kind_pick_the_second_bullet(self):
        self.send(tracked=False)
        self.assertIn("edit the file normally", self.injected[-1]["text"])
        png = os.path.join(self.root, "docs", "latency.png")
        self.send(path=png, tracked=True)
        self.assertIn("regenerate the file with normal writes", self.injected[-1]["text"])
        self.assertIn("--file %s --thread" % png, self.injected[-1]["text"])

    def test_a_failed_log_append_is_a_warning_never_a_failed_send(self):
        self.stub(exit=2, stderr="EACCES: permission denied, open '.comments-log.jsonl'")
        r = self.send()
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIs(r["queued"], False)
        self.assertIn("comments log", r["logWarning"])
        self.assertIn("EACCES", r["logWarning"])
        self.assertEqual(self.todo()["resolved"]["kind"], "answered", "the send and its stamp stand")

    def test_the_send_sits_behind_the_editing_consent(self):
        # The comments log is a file in the user's project: every write to disk stands behind the one
        # consent (decision 5), and the send IS a disk write — its `send` entry is the log's only record
        # of what went, and the unsent list is derived from that log. The first build sent the message
        # and skipped the append: the session got it, the todo was stamped, the log stayed empty, and
        # the next click sent the identical message again. So the gate is checked once, ahead of
        # delivery: nothing sent, nothing stamped, no host call. The refusal carries the phrase the
        # viewer's consent helper matches, so the panel re-offers the consent and retries. A person
        # cannot have comments to send without having consented earlier, so this only follows a
        # revocation (the review, 2026-09-06).
        km._set_file_editing(False)
        r = self.send()
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertEqual(r["code"], "editing-off")
        self.assertIn("file editing is off", r["error"])
        self.assertIn("nothing was sent", r["error"])
        self.assertEqual(self.injected, [], "no _send_or_park: the message did not go")
        self.assertNotIn("resolved", self.todo(), "nothing stamped")
        self.assertIsNone(self.seen(), "no host call without consent")

    def test_a_log_send_refusal_after_the_append_says_the_log_was_updated(self):
        # log-send appends FIRST, then reads the sidecar to fill the status fields; a corrupt sidecar
        # stops the read, not the append, and the host says so with `logged: true` beside its refusal.
        # The kernel used to drop the refusal's fields and report the entry as never written — and the
        # panel then offered the same comments again (the review, 2026-09-06).
        self.stub(reply={"ok": False, "code": "corrupt", "logged": True,
                         "error": "the comments for ~/notes-api/docs/report.md are unreadable JSON; the send was recorded in the comments log"})
        r = self.send()
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIn("comments log", r["logWarning"])
        self.assertIn("was updated", r["logWarning"])
        self.assertIn("unreadable JSON", r["logWarning"])
        self.assertNotIn("was not updated", r["logWarning"])
        self.assertEqual(self.todo()["resolved"]["kind"], "answered")

    def test_a_log_send_refusal_before_the_append_says_the_log_was_not_updated(self):
        # the other `logged` the real host answers: false, when the refusal came before the append
        self.stub(reply={"ok": False, "code": "unreadable", "logged": False,
                         "error": "cannot read ~/notes-api/docs/report.md: EACCES"})
        r = self.send()
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIn("was not updated", r["logWarning"])
        self.assertIn("EACCES", r["logWarning"])

    def test_no_node_still_sends_and_warns_about_the_log(self):
        real = km.shutil.which
        km.shutil.which = lambda name, *a, **k: None
        try:
            r = self.send()
        finally:
            km.shutil.which = real
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertIn("node", r["logWarning"])
        self.assertEqual(len(self.injected), 1)

    def test_malformed_comments_refuse(self):
        r = self.send(comments="not a list")
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        r = self.send(comments=[1, 2])
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertEqual(self.injected, [])


class TheSendOpOnTheWire(_Wire, _SendWorld):
    def frame(self, req_id):
        return {"type": "fileCommentsSend", "reqId": req_id, "sid": SID, "path": self.fp, "tracked": True,
                "comments": ONE, "accepted": 0, "rejected": 0, "watermark": None, "todoId": self.tid}

    def test_the_send_op_answers_the_sending_socket_with_the_request_id(self):
        r = self.send(self.frame(51))
        self.assertEqual(r["type"], "fileCommentsSent")
        self.assertEqual(r["reqId"], 51)
        self.assertEqual(len(self.injected), 1)

    def test_the_log_append_holds_the_ops_thread_not_the_dispatcher(self):
        # The send op's own host call — log-send after the message went — is the wait the dispatcher's
        # comment names as the reason this frame is threaded. The real op, a real node host held by a
        # gate file: the dispatcher is back before the gate opens, and the send still completes.
        gate = os.path.join(self.tmp, "release")
        self.stub(reply={"ok": True, "verb": "log-send", "logged": True}, wait_for=gate)
        try:
            self.dispatch(self.frame(52))
            self.assertFalse(self.answered(52), "the dispatcher is back while the log append is still running")
        finally:
            Path(gate).touch()
        r = self.wait_for(52)
        self.assertEqual((r["type"], r["reqId"], r["queued"]), ("fileCommentsSent", 52, False))
        self.assertNotIn("logWarning", r, "the append completed once released")
        self.assertEqual(len(self.injected), 1)
        self.assertEqual(self.seen()["request"]["verb"], "log-send")


class TheTodoReplyIsUnchanged(_SendWorld):
    """The userTodoAnswer handler now goes through the shared helper in its STRICT mode; its own
    contract (tests/test_user_todos.py DriveOps) is pinned here beside the lenient one so a change to
    the helper cannot quietly relax the Reply."""

    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}

    def reply(self, tid=None, text="Go with the session cookie for now."):
        return km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid or self.tid, "text": text}, self.client)

    def test_the_handler_and_the_send_op_share_one_helper(self):
        self.assertIn("_deliver_todo_reply(be, sid, body, tid, must_stamp=True)", inspect.getsource(km._drive))
        self.assertIn("must_stamp=False", inspect.getsource(km._file_comments_send_op))
        self.assertIn('"userTodoAnswer"', inspect.getsource(km._drive), "still an ID op")

    def test_switch_off_sends_nothing_and_warns_with_the_switch_text(self):
        km._set_user_todos(False)
        self.assertTrue(self.reply())
        self.assertEqual(self.injected, [], "the todo Reply exists to stamp: no stamp, no send")
        self.assertEqual(self.sent, [{"type": "warn", "text": km._USER_TODOS_OFF_WARN}])

    def test_a_settled_todo_sends_nothing_and_warns(self):
        self.reply(tid="ut-deadbeef")
        self.assertEqual(self.injected, [])
        self.assertIn("already settled", self.sent[0]["text"])

    def test_an_ended_session_sends_nothing_and_warns(self):
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        self.reply()
        self.assertEqual(self.injected, [])
        self.assertIn("has ended", self.sent[0]["text"])
        self.assertNotIn("resolved", self.todo())

    def test_a_truthy_send_stamps_a_parked_one_waits_a_refused_one_warns(self):
        self.reply()
        self.assertEqual(self.injected[0]["text"], "Re: Need a look at the findings report — Go with the session cookie for now.")
        self.assertEqual(self.injected[0]["user_todo"], self.tid)
        self.assertEqual(self.todo()["resolved"]["kind"], "answered")
        self.assertEqual(self.sent, [])
        tid2 = km._add_user_todo(SID, "Need the staging port")
        self.send_result = "parked"
        self.reply(tid=tid2, text="8080")
        self.assertNotIn("resolved", km._user_todos()[SID][1])
        self.assertEqual(self.sent, [])
        self.send_result = False
        self.reply(tid=tid2, text="8080")
        self.assertNotIn("resolved", km._user_todos()[SID][1])
        self.assertIn("Couldn't deliver", self.sent[-1]["text"])


class TheSaveLogsTheEdit(_Wire):
    """saveFile: a direct edit is appended to the comments log through the host's log-edit verb after
    the save lands and BEFORE the ack, which carries `logged`."""

    def save(self, path=None, content="# Findings\n\nThe api session cut p95 latency by 45%.\n", ns=None, rid=3):
        return self.send({"type": "saveFile", "path": path or self.fp, "content": content,
                          "baseMtimeNs": str(self.ns if ns is None else ns), "reqId": rid}, wait=False)

    def test_a_save_asks_the_host_with_the_summary_and_reports_logged_true(self):
        self.stub(reply={"ok": True, "verb": "log-edit", "logged": True})
        old = open(self.fp, "rb").read()
        r = self.save()
        self.assertEqual(r["type"], "fileSaved")
        self.assertEqual(r["reqId"], 3)
        self.assertIsInstance(r["mtimeNs"], str)
        self.assertIs(r["logged"], True)
        self.assertNotIn("logWarning", r)
        req = self.seen()["request"]
        self.assertEqual(req["verb"], "log-edit")
        self.assertEqual(req["path"], self.fp)
        s = req["args"]["summary"]
        self.assertEqual(s["mtimeBeforeNs"], str(self.ns))
        self.assertEqual(s["mtimeAfterNs"], r["mtimeNs"], "the ack and the log agree on the new anchor")
        self.assertEqual(s["bytesBefore"], len(old))
        self.assertEqual(s["bytesAfter"], len("# Findings\n\nThe api session cut p95 latency by 45%.\n".encode()))
        self.assertIn("-The api session cut p95 latency by 40%.\n", s["diff"])
        self.assertIn("+The api session cut p95 latency by 45%.\n", s["diff"])
        self.assertNotIn("\n # Findings", s["diff"], "zero context: only the changed lines")
        self.assertIs(s["truncated"], False)
        self.assertEqual(open(self.fp).read(), "# Findings\n\nThe api session cut p95 latency by 45%.\n")

    def test_the_host_decides_logged_false(self):
        self.stub(reply={"ok": True, "verb": "log-edit", "logged": False})
        r = self.save()
        self.assertEqual(r["type"], "fileSaved")
        self.assertIs(r["logged"], False)
        self.assertNotIn("logWarning", r)
        self.assertEqual(self.seen()["request"]["verb"], "log-edit")

    def test_a_refused_save_never_asks_the_host(self):
        r = self.save(ns=self.ns - 10)
        self.assertEqual(r["type"], "fileSaveFailed")
        self.assertIn("changed on disk", r["error"])
        self.assertIsNone(self.seen())

    def test_a_path_inside_trackchanges_is_never_logged(self):
        cfg = os.path.join(self.root, ".trackchanges", "config.json")
        with open(cfg, "w") as f:
            f.write('{"v": 2, "tracked": []}\n')
        r = self.save(path=cfg, content='{"v": 2, "tracked": ["docs/"]}\n', ns=os.stat(cfg).st_mtime_ns)
        self.assertEqual(r["type"], "fileSaved")
        self.assertIs(r["logged"], False)
        self.assertNotIn("logWarning", r)
        self.assertIsNone(self.seen(), "the log never records an edit to itself or its siblings")

    def test_a_tree_with_no_trackchanges_above_never_spawns_node(self):
        loose = os.path.join(self.tmp, "loose.md")
        with open(loose, "w") as f:
            f.write("a\n")
        self.assertFalse(km._trackchanges_above(loose))
        r = self.save(path=loose, content="b\n", ns=os.stat(loose).st_mtime_ns)
        self.assertEqual(r["type"], "fileSaved")
        self.assertIs(r["logged"], False)
        self.assertNotIn("logWarning", r)
        self.assertIsNone(self.seen(), "no sidecar, log or config can exist for it: nothing to ask")

    def test_a_host_failure_is_reported_and_never_fails_the_save(self):
        self.stub(exit=1, stderr="Error: cannot append to the comments log")
        r = self.save()
        self.assertEqual(r["type"], "fileSaved", "the file was written; only the log is behind")
        self.assertIs(r["logged"], False)
        self.assertIn("comments log", r["logWarning"])
        self.assertIn("cannot append", r["logWarning"])
        self.assertEqual(open(self.fp).read(), "# Findings\n\nThe api session cut p95 latency by 45%.\n")

    def test_a_host_refusal_after_the_append_reports_logged_true_with_the_refusal(self):
        # what the real host answers on a corrupt sidecar: log-edit appends first, then the read that fills
        # the status fields refuses, so the refusal carries `logged: true` (tools/file-comments-host.mjs,
        # recordedDespite; pinned in its own tests). The kernel reads `logged` off the refusal instead of
        # inferring it from the code: the entry IS in the log, and the ack says so.
        self.stub(reply={"ok": False, "code": "corrupt", "logged": True,
                         "error": "the comments for ~/notes-api/docs/report.md are unreadable JSON; the edit was recorded in the comments log"})
        r = self.save()
        self.assertEqual(r["type"], "fileSaved")
        self.assertIs(r["logged"], True)
        self.assertIn("written to the comments log", r["logWarning"])
        self.assertIn("could not be read back", r["logWarning"])
        self.assertIn("unreadable JSON", r["logWarning"])

    def test_a_host_refusal_before_the_append_reports_logged_false(self):
        self.stub(reply={"ok": False, "code": "unreadable", "logged": False,
                         "error": "cannot read ~/notes-api/docs/report.md: EACCES"})
        r = self.save()
        self.assertEqual(r["type"], "fileSaved")
        self.assertIs(r["logged"], False)
        self.assertIn("not written to the comments log", r["logWarning"])
        self.assertIn("EACCES", r["logWarning"])

    def test_no_node_saves_and_reports_logged_false_quietly(self):
        real = km.shutil.which
        km.shutil.which = lambda name, *a, **k: None
        try:
            r = self.save()
        finally:
            km.shutil.which = real
        self.assertEqual(r["type"], "fileSaved")
        self.assertIs(r["logged"], False)
        self.assertNotIn("logWarning", r, "no node means no panel: nothing to warn about")
        self.assertIsNone(self.seen())

    def test_the_log_call_sits_between_the_save_and_the_ack_ahead_of_the_trace(self):
        src = inspect.getsource(km.Handler._dispatch_ws)
        i_pre, i_save = src.index("pre = _edit_log_before("), src.index("mt, err = _save_file(")
        i_after, i_ack, i_trace = (src.index("logged, lwarn = _edit_log_after("), src.index('"logged": logged}'),
                                   src.index("_edit_trace(msg.get(\"path\")"))
        self.assertLess(i_pre, i_save, "the prior bytes are read before the replace destroys them")
        self.assertLess(i_save, i_after)
        self.assertLess(i_after, i_ack, "the ack carries the verdict")
        self.assertLess(i_ack, i_trace, "the trace still fires after the reply, as before")

    def test_the_path_helpers(self):
        self.assertTrue(km._under_trackchanges("/x/notes-api/.trackchanges/docs%2Freport.md.json"))
        self.assertTrue(km._under_trackchanges("/x/notes-api/.trackchanges/config.json"))
        self.assertFalse(km._under_trackchanges("/x/notes-api/docs/.trackchanges.md"))
        self.assertFalse(km._under_trackchanges(self.fp))
        self.assertTrue(km._trackchanges_above(self.fp))
        self.assertTrue(km._trackchanges_above(os.path.join(self.root, "a.md")))


class TheEditDiff(unittest.TestCase):
    def test_zero_context_unified_diff(self):
        diff, truncated = km._edit_log_diff("a\nb\nc\n", "a\nB\nc\n", "x.md")
        self.assertEqual(diff, "--- a/x.md\n+++ b/x.md\n@@ -2 +2 @@\n-b\n+B\n")
        self.assertIs(truncated, False)

    def test_a_missing_final_newline_still_yields_whole_lines(self):
        diff, _ = km._edit_log_diff("a\nb", "a\nc", "x.md")
        self.assertTrue(diff.endswith("+c\n"))
        self.assertEqual(diff.count("\n"), len(diff.splitlines()))

    def test_the_line_cap(self):
        old = "".join("line %d\n" % i for i in range(300))
        new = "".join("LINE %d\n" % i for i in range(300))
        diff, truncated = km._edit_log_diff(old, new, "x.md")
        self.assertIs(truncated, True)
        self.assertLessEqual(len(diff.splitlines()), km._EDIT_DIFF_MAX_LINES)

    def test_the_byte_cap(self):
        old = "".join("%d %s\n" % (i, "x" * 500) for i in range(60))
        new = "".join("%d %s\n" % (i, "y" * 500) for i in range(60))
        diff, truncated = km._edit_log_diff(old, new, "x.md")
        self.assertIs(truncated, True)
        self.assertLessEqual(len(diff.encode("utf-8")), km._EDIT_DIFF_MAX_BYTES)

    def test_no_change_is_an_empty_diff(self):
        self.assertEqual(km._edit_log_diff("a\n", "a\n", "x.md"), ("", False))

    def test_the_log_diff_does_not_shadow_the_transcript_folds_diff(self):
        """kernel.py holds two diff helpers: the transcript fold's one-argument _edit_diff(inp), which
        renders an Edit/MultiEdit tool_use, and the comments log's _edit_log_diff(old, new, name).
        The log helper was first defined under the fold's name, further down the module, so the
        later def won and every fold of an Edit tool_use raised TypeError (77 tests across
        test_kernel, test_chat_fold and test_kernel_patch_rows). Both names must exist, as
        different functions, each answering its own call shape."""
        self.assertIsNot(km._edit_diff, km._edit_log_diff)
        self.assertEqual(km._edit_diff({"old_string": "a", "new_string": "b"}), "- a\n+ b")
        self.assertEqual(km._edit_log_diff("a\n", "b\n", "x.md")[0].splitlines()[-2:], ["-a", "+b"])


def _serve_get(path, headers=None):
    """Drive the REAL do_GET dispatcher over a fake socket → (status, body) — the auth-hardening harness."""
    h = km.Handler.__new__(km.Handler)
    h.client_address = ("127.0.0.1", 0)
    h.headers = dict(headers or {})
    h.path = path
    h.command = "GET"
    h.request_version = "HTTP/1.1"
    h.wfile = io.BytesIO()
    h.rfile = io.BytesIO()
    h.close_connection = True
    captured = {}
    h.send_response = lambda code, *a: captured.__setitem__("status", code)
    h.send_header = lambda k, v: None
    h.end_headers = lambda: None
    h.log_message = lambda *a: None
    h.do_GET()
    return captured.get("status"), h.wfile.getvalue().decode("utf-8", "replace")


class TheDefaultsVerdict(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._saved = (km.shutil.which, km._AGENT_TOOLING_PROBE)
        km._AGENT_TOOLING_PROBE = os.path.join(self.tmp, "hooks", "track-reply.mjs")

    def tearDown(self):
        km.shutil.which, km._AGENT_TOOLING_PROBE = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _link_tooling(self):
        os.makedirs(os.path.dirname(km._AGENT_TOOLING_PROBE))
        with open(km._AGENT_TOOLING_PROBE, "w") as f:
            f.write("// linked\n")

    def test_no_node_wins_over_everything(self):
        km.shutil.which = lambda name, *a, **k: None
        self._link_tooling()
        self.assertEqual(km._file_comments_verdict(), "no-node")

    def test_agent_tooling_absent_when_the_reply_cli_is_not_linked(self):
        km.shutil.which = lambda name, *a, **k: "/usr/bin/node"
        self.assertEqual(km._file_comments_verdict(), "agent-tooling-absent")

    def test_ok_when_node_and_the_tooling_are_both_there(self):
        km.shutil.which = lambda name, *a, **k: "/usr/bin/node"
        self._link_tooling()
        self.assertEqual(km._file_comments_verdict(), "ok")

    def test_the_verdict_rides_the_gated_defaults_route_not_version(self):
        km.shutil.which = lambda name, *a, **k: "/usr/bin/node"
        self._link_tooling()
        status, body = _serve_get("/defaults", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(status, 200)
        d = json.loads(body)
        self.assertEqual(d["fileComments"], "ok")
        self.assertIsInstance(d.get("defaultDir"), str, "the existing keys are untouched")
        self.assertIn("nativeDialogs", d)
        self.assertNotIn("fileComments", km._version_info(), "/version is served before authorization")
        status, _ = _serve_get("/defaults", {})
        self.assertEqual(status, 403)


class ThePromptTellsSessionsHowToAskForALook(unittest.TestCase):
    """claude/romp-session-prompt.md gains one sentence in Working style (plans/file-review.md,
    decision 35): sessions learn to name the file's absolute path in a user todo's detail, so the
    loop's first step exists. In the person's voice, conditional on the tool (it exists only while
    the User todos switch is on), and outside Housekeeping, which CLAUDE.md reserves for explaining
    romp's artifacts."""

    def test_the_sentence_is_there_in_working_style_and_names_the_tool(self):
        text = (Path(HERE).parent / "claude" / "romp-session-prompt.md").read_text()
        working, housekeeping = text.split("# Housekeeping", 1)
        self.assertIn("add_user_todo", working)
        self.assertIn("if you have\nthat tool", working, "conditional on the tool, which the switch gates")
        self.assertIn("absolute path in the detail", working)
        self.assertIn("comments come back to you as a message", working)
        self.assertNotIn("add_user_todo", housekeeping, "Housekeeping explains romp's artifacts only")
        for word in ("card", "board", "goal", "nudge", "viewer", "panel", "dashboard"):
            self.assertNotIn(word, working.lower(), "the sentence names only what the agent already sees")


if __name__ == "__main__":
    unittest.main()
