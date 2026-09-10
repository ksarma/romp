#!/usr/bin/env python3
"""A drive op naming a session this kernel doesn't have must FAIL LOUDLY, never degrade into a no-op.

The user 2026-07-29: on a board merging two kernels, a reply addressed to the wrong one reached a kernel
that owns no such session. Sessions.backend_for() falls through to tmux for any unrecognized sid, and
TmuxBackend.send then types at a pane named after the sid — with no such pane, the keystrokes evaporate
with nothing raised and nothing logged, so typed messages simply ceased to exist. Per the repo's
fail-loudly rule, an op we cannot deliver has to say so: a modal in the pane that fired it, the text kept
verbatim on disk so nothing typed is lost, and a line in the kernel log.
"""
import json
import os
import unittest
from unittest import mock
from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_foreign", os.path.join(BIN, "romp-kernel"))

OURS = "11111111-2222-3333-4444-555555555555"
THEIRS = "99999999-8888-7777-6666-555555555555"   # lives on another machine's kernel


class KernelKnows(unittest.TestCase):
    """The names registry is the authority, and it OUTLIVES the session — so 'we don't have it' means
    never created here, not merely 'not running'."""

    def setUp(self):
        self._name_of, self._sdk = km._name_of, km._sdk
        km._name_of = lambda sid: "web" if sid == OURS else None
        km._sdk = lambda: None

    def tearDown(self):
        km._name_of, km._sdk = self._name_of, self._sdk

    def test_a_named_session_is_ours_even_when_long_dead(self):
        # the registry entry survives the session, so a send that REVIVES a dormant tab still goes through
        self.assertTrue(km._kernel_knows(OURS))

    def test_a_foreign_sid_is_not_ours(self):
        self.assertFalse(km._kernel_knows(THEIRS))

    def test_empty_is_not_ours(self):
        self.assertFalse(km._kernel_knows(""))
        self.assertFalse(km._kernel_knows(None))

    def test_a_session_mid_launch_is_ours_via_the_sdk(self):
        # spawned but not yet written to the registry — never call that foreign
        km._name_of = lambda sid: None
        km._sdk = lambda: type("B", (), {"owns": staticmethod(lambda s: s == OURS)})()
        self.assertTrue(km._kernel_knows(OURS))
        self.assertFalse(km._kernel_knows(THEIRS))


class _ForeignDriveFixture(unittest.TestCase):
    """The refusing gate: a names registry that knows OURS alone, no SDK backend, and a backend_for that records
    what reaches it. No tests of its own, so a class that needs the fixture inherits it and not another class's
    tests."""

    def setUp(self):
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}
        self._name_of, self._sdk = km._name_of, km._sdk
        km._name_of = lambda sid: "web" if sid == OURS else None
        km._sdk = lambda: None
        self._backend_for = km.Sessions.backend_for
        self.reached = []
        km.Sessions.backend_for = staticmethod(
            lambda sid: type("B", (), {"send": lambda _s, s, t: self.reached.append((s, t))})())

    def tearDown(self):
        km._name_of, km._sdk = self._name_of, self._sdk
        km.Sessions.backend_for = staticmethod(self._backend_for)


class RefusesForeignDriveOps(_ForeignDriveFixture):
    def test_a_send_to_a_foreign_session_never_reaches_a_backend(self):
        handled = km._drive({"type": "sendMessage", "id": THEIRS, "text": "did you get this?"}, self.client)
        self.assertTrue(handled, "the op is CONSUMED — refused, not passed on to be silently retried")
        self.assertEqual(self.reached, [], "nothing was handed to a backend")

    def test_the_refusal_reaches_the_pane_that_fired_it_as_an_err_not_a_warn(self):
        km._drive({"type": "sendMessage", "id": THEIRS, "text": "did you get this?"}, self.client)
        self.assertEqual(len(self.sent), 1)
        msg = self.sent[0]
        # `err` (a modal you must dismiss), NOT `warn` (a toast that fades in 12s and can be missed)
        self.assertEqual(msg["type"], "err")
        self.assertIn("not delivered", msg["title"])
        self.assertIn("Nothing was sent", msg["text"])
        self.assertIn(THEIRS, msg["text"], "names the session it could not find, so the cause is diagnosable")
        # the typed text rides back so the user can recover it — the composer cleared it on Enter
        self.assertEqual(msg["copy"], "did you get this?")
        # …and the sid rides along, so the shell's error-center entry says WHICH session it was meant for
        self.assertEqual(msg["sid"], THEIRS)
        # …and the REQUEST it answers (review find, 2026-09-08): the feed latches a button on the click (Retry →
        # "Retrying…", Continue → "Sent") and re-arms it on the kernel's reply for THAT post, never every latch
        # the session holds, and never on a clock, so the reply names the op and the card it was for
        self.assertEqual((msg["op"], msg["itemId"]), ("sendMessage", ""))

    def test_a_card_reply_is_refused_the_same_way(self):
        # the exact shape that lost real messages: askFollowUp derives its sid from the itemId
        km._drive({"type": "askFollowUp", "itemId": THEIRS + ":g4", "text": "and the fix?"}, self.client)
        self.assertEqual(self.reached, [])
        self.assertEqual(self.sent[0]["type"], "err")
        self.assertEqual(self.sent[0]["copy"], "and the fix?")
        self.assertIn("reply", self.sent[0]["title"])
        self.assertEqual((self.sent[0]["op"], self.sent[0]["itemId"]), ("askFollowUp", THEIRS + ":g4"),
                         "the card's own latch is the one this refusal releases")

    def test_our_own_session_is_untouched(self):
        km._drive({"type": "sendMessage", "id": OURS, "text": "hello"}, self.client)
        self.assertEqual(self.reached, [(OURS, "hello")], "a session we own still gets its message")
        self.assertEqual(self.sent, [], "and no error is raised for it")

    def test_a_non_drive_op_still_falls_through_untouched(self):
        # UI/nav ops carry no session to own — they must keep reaching _dispatch_ws
        self.assertFalse(km._drive({"type": "setColormap", "name": "viridis"}, self.client))
        self.assertEqual(self.sent, [])

    def test_the_text_is_kept_verbatim_on_disk_so_nothing_typed_is_lost(self):
        import tempfile
        import pathlib
        with tempfile.TemporaryDirectory() as d:
            saved = km.jd.STATE
            km.jd.STATE = pathlib.Path(d)
            try:
                km._drive({"type": "sendMessage", "id": THEIRS, "text": "a paragraph I do not want to retype"},
                          self.client)
                rows = [json.loads(x) for x in (pathlib.Path(d) / "undelivered.jsonl").read_text().splitlines()]
            finally:
                km.jd.STATE = saved
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], "a paragraph I do not want to retype")
        self.assertEqual(rows[0]["sid"], THEIRS)
        self.assertEqual(rows[0]["op"], "sendMessage")

    def test_a_refused_text_less_gesture_files_a_row_with_no_text(self):
        # the Continue button (askFollowUp with cont:true and no text), interrupt and endSession carry no text,
        # and the records writer appends their undelivered.jsonl row all the same: a durable record of op, sid
        # and item that the stderr line does not keep across a log rotation. The error center's tooltip said a
        # refused card gesture writes nothing there, which is true only of the goals-file gesture refusals
        # (clear, drop, undo); it now says a refused reply, interrupt or end files a row with no text, and the
        # modal promises the verbatim text only when there is one (review round 7, 2026-09-09).
        import pathlib
        with tempfile.TemporaryDirectory() as d:
            saved = km.jd.STATE
            km.jd.STATE = pathlib.Path(d)
            try:
                for msg in ({"type": "askFollowUp", "itemId": THEIRS + ":g4", "cont": True},
                            {"type": "interrupt", "id": THEIRS}, {"type": "endSession", "id": THEIRS}):
                    self.assertTrue(km._drive(msg, self.client), msg)
                rows = [json.loads(x) for x in (pathlib.Path(d) / "undelivered.jsonl").read_text().splitlines()]
            finally:
                km.jd.STATE = saved
        self.assertEqual([(r["op"], r["sid"], r["what"], r["itemId"], r["text"]) for r in rows],
                         [("askFollowUp", THEIRS, "reply", THEIRS + ":g4", ""), ("interrupt", THEIRS, "interrupt", "", ""),
                          ("endSession", THEIRS, "end", "", "")], "one row per refused gesture, with no text")
        self.assertEqual(self.reached, [])
        self.assertEqual(len(self.sent), 3)
        for msg in self.sent:
            self.assertEqual(msg["type"], "err")
            self.assertIn("Nothing was sent", msg["text"])
            self.assertIn("The refusal is recorded in undelivered.jsonl", msg["text"])
            self.assertNotIn("Your text is saved verbatim", msg["text"], "no text was typed, so none is promised")
            self.assertEqual(msg["copy"], "")

    def test_a_compact_or_command_refused_by_name_keeps_the_session_name_out_of_the_text(self):
        # compact and sendCommand address their session by NAME (the timeline keys them so), and the records
        # writer read ("text", "cmd", "name") for the text to keep, so a compact refused by name filed a row whose
        # text was the session name, the modal promised "Your text is saved verbatim" and Copy my text copied the
        # name, under "That action was not delivered" (the verb table knew compactSession, not compact). The name
        # is typed text for the ops in _TYPED_NAME_OPS (renameSession, forkSession, commentPromote, commentCreate);
        # for compact and sendCommand it is the target, kept in the row under its own key so the row still says
        # which session was addressed, and
        # a sendCommand's text stays its cmd (review round 8, 2026-09-09). tmux is off, the comment threads' store
        # empty and the roster clear, so the name resolves to nothing and the unknown refusal answers.
        import pathlib
        with tempfile.TemporaryDirectory() as d:
            saved = km.jd.STATE
            km.jd.STATE = pathlib.Path(d)
            try:
                with mock.patch.object(km._TMUX, "available", lambda: False), \
                     mock.patch.object(km, "_thread_names", lambda: {}), \
                     mock.patch.dict(km._remotes, {}, clear=True):
                    for msg in ({"type": "compact", "name": "web-2"},
                                {"type": "sendCommand", "name": "web-2", "cmd": "/model opus"},
                                {"type": "renameSession", "id": THEIRS, "name": "a title I typed"}):
                        self.assertTrue(km._drive(msg, self.client), msg)
                rows = [json.loads(x) for x in (pathlib.Path(d) / "undelivered.jsonl").read_text().splitlines()]
            finally:
                km.jd.STATE = saved
        self.assertEqual(self.reached, [])
        compact, command, rename = self.sent
        self.assertEqual(compact["copy"], "", "no text was typed, so none is offered back")
        self.assertEqual(compact["title"], "That compact was not delivered")
        self.assertEqual([(r["op"], r["sid"], r["what"], r["text"], r["target"]) for r in rows],
                         [("compact", "web-2", "compact", "", "web-2"),
                          ("sendCommand", "web-2", "command", "/model opus", "web-2"),
                          ("renameSession", THEIRS, "rename", "a title I typed", "")],
                         "the name is the target for compact and sendCommand, the text for a rename")
        self.assertIn("The refusal is recorded in undelivered.jsonl", compact["text"])
        self.assertNotIn("Your text is saved verbatim", compact["text"])
        self.assertIn("has no session with id web-2", compact["text"])
        self.assertEqual(compact["sid"], "web-2")
        self.assertEqual(command["title"], "That command was not delivered")
        self.assertEqual(command["copy"], "/model opus", "the cmd is the typed text")
        self.assertIn("Your text is saved verbatim", command["text"])
        self.assertEqual(rename["title"], "That rename was not delivered")
        self.assertEqual(rename["copy"], "a title I typed", "a rename's name is typed text, kept as before")
        self.assertIn("Your text is saved verbatim", rename["text"])

    def test_a_fork_promote_or_thread_refused_at_the_gate_keeps_the_typed_name_as_its_text(self):
        # the op-aware fold (the test above) was pinned for renameSession alone, so a _TYPED_NAME_OPS that dropped
        # forkSession or commentPromote left every test green while a refused fork filed a row with no text and
        # offered nothing back. The other three members, each refused at the gate for a foreign sid: the typed
        # name is the row's text and the modal's copy, and the target is empty (the name addresses no session).
        # commentCreate's handler requires text, which the fold reads first, so its entry reaches the fold only
        # for a text-less create refused at the gate, which is what is driven here; with text the text wins.
        # None of the three is in the verb table, so the modal wears the generic title; pinned as it stands
        # (review round 9, 2026-09-09).
        import pathlib
        typed = {"forkSession": "a fork title I typed", "commentPromote": "a promote title I typed",
                 "commentCreate": "a thread title I typed"}
        msgs = ({"type": "forkSession", "id": THEIRS, "uuid": "u1", "name": typed["forkSession"]},
                {"type": "commentPromote", "id": THEIRS, "tid": "t1", "name": typed["commentPromote"]},
                {"type": "commentCreate", "id": THEIRS, "uuid": "u1", "exact": "the quoted span",
                 "name": typed["commentCreate"]},
                {"type": "commentCreate", "id": THEIRS, "uuid": "u2", "exact": "the quoted span",
                 "text": "the comment I typed", "name": "a thread title the text outranks"})
        with tempfile.TemporaryDirectory() as d:
            saved = km.jd.STATE
            km.jd.STATE = pathlib.Path(d)
            try:
                with mock.patch.object(km._TMUX, "available", lambda: False):
                    for msg in msgs:
                        self.assertTrue(km._drive(msg, self.client), msg)
                rows = [json.loads(x) for x in (pathlib.Path(d) / "undelivered.jsonl").read_text().splitlines()]
            finally:
                km.jd.STATE = saved
        self.assertEqual(self.reached, [], "nothing was handed to a backend")
        self.assertEqual([(r["op"], r["sid"], r["text"], r["target"]) for r in rows],
                         [("forkSession", THEIRS, typed["forkSession"], ""),
                          ("commentPromote", THEIRS, typed["commentPromote"], ""),
                          ("commentCreate", THEIRS, typed["commentCreate"], ""),
                          ("commentCreate", THEIRS, "the comment I typed", "")],
                         "the typed name is the row's text and never its target; a create's text outranks its title")
        self.assertEqual([m["copy"] for m in self.sent],
                         [typed["forkSession"], typed["commentPromote"], typed["commentCreate"], "the comment I typed"],
                         "the typed name is offered back")
        for m in self.sent:
            self.assertEqual(m["type"], "err")
            self.assertEqual(m["sid"], THEIRS)
            self.assertIn("Your text is saved verbatim", m["text"])
            self.assertEqual(m["title"], "That action was not delivered", "no verb in the table for these three")

    def test_a_record_that_will_not_read_refuses_the_typed_text_into_the_same_three_records(self):
        # _session_gate's unreadable verdict (a session the SDK backend is not running whose SDK registry entry
        # exists but will not read) refuses through _refuse_drive_unreadable, the sibling of the unknown refusal
        # above, and the two
        # write through one records writer: the same modal with the text offered back, the same undelivered.jsonl
        # row with the text verbatim, the same stderr line, with the cause naming the record. Pinned with typed
        # text: the two-doors table drives interrupt, which carries none, so a refusal that kept the modal and
        # dropped the row and the line passed every test (review round 6, 2026-09-09).
        import contextlib
        import io
        import pathlib
        sid = "77777777-6666-5555-4444-333333333333"
        typed = "a paragraph I typed for a session whose record broke"
        with tempfile.TemporaryDirectory() as d:
            saved = km.jd.STATE
            km.jd.STATE = pathlib.Path(d)
            reg = pathlib.Path(d) / "sdk" / (sid + ".json")
            reg.parent.mkdir()
            reg.write_bytes(b"{not json")
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()
            err = io.StringIO()
            try:
                with mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), contextlib.redirect_stderr(err):
                    handled = km._drive({"type": "sendMessage", "id": sid, "text": typed}, self.client)
                rows = [json.loads(x) for x in (pathlib.Path(d) / "undelivered.jsonl").read_text().splitlines()]
            finally:
                km.jd.STATE = saved
                km._thread_reg_memo.clear()
                km._thread_reg_failed.clear()
        self.assertTrue(handled, "the op is CONSUMED: refused, not passed on")
        self.assertEqual(self.reached, [], "nothing was handed to a backend")
        self.assertEqual([(r["op"], r["sid"], r["what"], r["text"]) for r in rows],
                         [("sendMessage", sid, "message", typed)], "the typed text survives the refusal on disk")
        self.assertIn("undeliverable sendMessage: the record for session %s will not read; %r" % (sid, typed),
                      err.getvalue(), "the kernel log names the cause")
        self.assertEqual(len(self.sent), 1)
        msg = self.sent[0]
        self.assertEqual(msg["type"], "err")
        self.assertEqual(msg["copy"], typed, "the typed text rides back to the pane")
        self.assertIn("could not read the record", msg["text"].lower())
        self.assertIn("Nothing was sent", msg["text"])
        self.assertNotIn("no session with id", msg["text"], "a record that will not read is never called foreign")
        self.assertEqual((msg["sid"], msg["op"]), (sid, "sendMessage"))


class TypedNameOpsClassifyEveryAcceptedOp(_ForeignDriveFixture):
    """The records writer folds `name` into a refusal's text for the ops in _TYPED_NAME_OPS and keeps it as the
    row's target for those in _TARGET_NAME_OPS; an op whose handler reads the message's name and sits in neither
    tuple is a refusal that drops a typed title or files a session name as text (round 8's compact). Round 9 pinned
    the tuples with a syntactic walk of _drive's dispatch chain for msg["name"] and msg.get("name"), which an alias,
    a hoisted local, msg.pop and a helper taking msg all passed. This pin is executed instead: every op the front
    door accepts is enumerated from the source (the one use of the AST, to LIST the ops, never to detect a read),
    each is classified HERE, by hand, as carrying a typed title, addressing its session by name, or carrying no
    name, and every op is driven through a refusing gate with a name and with a name and text, so the undelivered
    row and the modal are asserted against the classification. An op the door accepts that the table does not
    classify is reported by name, so a new op cannot land without saying what its name means to a refusal, and a
    tuple edit without a table edit is red (review round 10, 2026-09-09). An arm of the chain the listing cannot
    read is red too, by its source text, so an op cannot go unclassified because its arm was keyed on a shape
    the walk did not resolve (review round 11, 2026-09-10)."""

    NAME, TEXT = "title-I-typed", "a paragraph I typed"
    # `name` is a title the user typed: the row's text and the modal's copy when the op carries no text
    TYPED = {"renameSession": "the new name", "forkSession": "the fork's name",
             "commentPromote": "the promoted session's name", "commentCreate": "the thread's name (a text-less create)"}
    # `name` is the session ADDRESSED (the timeline keys these by session name): the row's target, never its text
    TARGET = {"compact": "the session to compact", "sendCommand": "the session the command goes to"}
    # every other op the front door accepts: `name` means nothing to its handler, and a refusal keeps none
    NAMELESS = ("sendMessage", "rewindSend", "rewindDelete", "interrupt", "compactSession", "dismissDialog", "answerAsk",
                "navAsk", "toggleAsk", "submitAsk", "addCustomAsk", "cancelAsk", "askText", "cancelQueued", "dismissEcho",
                "apiRetry", "setModel", "setEffort", "setMode", "setFast", "setAuth", "endSession", "moveSession",
                "stopTask", "rewindFiles", "mcpAction", "commentReply", "commentResolve", "commentDelete", "commentSeen",
                "userTodoAnswer", "userTodoDismiss", "unpinNote", "commentMerge", "askFollowUp")
    # what the front door needs beside `type` to read a message as a drive op: an id for the id ops, nothing for
    # the ops addressed by name, and the Continue shape for askFollowUp (itemId plus cont, which carries no text)
    FRONT_DOOR = {"askFollowUp": {"itemId": THEIRS + ":1", "cont": True}}

    def _accepted_ops(self):
        """Every op string _drive's front door accepts, read from its source: the ops named in the first if/elif
        chain that tests `t`, resolved through the function body's local tuple, list, set and dict assigns
        (ID_OPS), the kernel's module tuples (_TARGET_NAME_OPS) and inline tuple, list and set literals. A listing
        only: nothing here reads what an arm does with the message. An arm the listing cannot read is RED, never
        skipped: an arm of the chain that yields no op, or a `t in <name>` whose name resolves to nothing, is
        reported by its source text (round 11: an arm keyed on a local set or dict, a frozenset(...) call or a
        BinOp yielded an empty set silently and the pin stayed green with the op unclassified; round 9's walk
        did not catch this either, its unclassified list flagging only arms that also read msg["name"], so this
        is a stricter check, not a restoration)."""
        import ast
        import inspect
        import textwrap
        fn = ast.parse(textwrap.dedent(inspect.getsource(km._drive))).body[0]

        def literal_ops(node):
            # the op strings of a tuple, list or set literal, or a dict literal's keys; None for any other shape
            if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
                return tuple(e.value for e in node.elts if isinstance(e, ast.Constant))
            if isinstance(node, ast.Dict):
                return tuple(k.value for k in node.keys if isinstance(k, ast.Constant))
            return None
        local_ops = {}
        for stmt in fn.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                ops = literal_ops(stmt.value)
                if ops is not None:
                    local_ops[stmt.targets[0].id] = ops
        unreadable = []

        def ops_of(test):
            out = set()
            for n in ast.walk(test):
                if isinstance(n, ast.Compare) and isinstance(n.left, ast.Name) and n.left.id == "t":
                    for op, right in zip(n.ops, n.comparators):
                        if isinstance(op, ast.Eq) and isinstance(right, ast.Constant):
                            out.add(right.value)
                        elif isinstance(op, ast.In):
                            ops = literal_ops(right)
                            if ops is None and isinstance(right, ast.Name):
                                ops = local_ops.get(right.id)
                                if ops is None:
                                    held = getattr(km, right.id, None)
                                    ops = tuple(held) if isinstance(held, (tuple, list, set, frozenset, dict)) else None
                            if not ops:
                                unreadable.append(ast.unparse(right))
                            else:
                                out.update(ops)
            return out

        def mentions_t(node):
            return any(isinstance(n, ast.Name) and n.id == "t" for n in ast.walk(node))
        accepted = set()
        for stmt in fn.body:
            if isinstance(stmt, ast.If) and mentions_t(stmt.test):
                node = stmt
                while isinstance(node, ast.If):
                    ops = ops_of(node.test)
                    if not ops:
                        unreadable.append(ast.unparse(node.test))
                    accepted |= ops
                    node = node.orelse[0] if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If) else None
                break
        self.assertEqual(unreadable, [], "arms of _drive's front door, or names they test `t` against, that this listing "
                                         "cannot read: key the arm on a literal or a local or module tuple, list, set or "
                                         "dict, or teach the listing the shape, so the arm's ops are classified")
        return accepted

    def test_every_accepted_op_is_classified_and_its_refusal_keeps_the_name_as_classified(self):
        import pathlib
        accepted = self._accepted_ops()
        self.assertGreater(len(accepted), 30, "the front door's chain was found")
        classified = set(self.TYPED) | set(self.TARGET) | set(self.NAMELESS)
        self.assertEqual(sorted(accepted - classified), [],
                         "ops the drive door accepts that this pin does not classify: say whether the op's `name` is a "
                         "typed title (TYPED), the session it addresses (TARGET) or nothing (NAMELESS)")
        self.assertEqual(sorted(classified - accepted), [], "classified ops the drive door no longer accepts")
        self.assertEqual(set(km._TYPED_NAME_OPS), set(self.TYPED), "the typed-name tuple and this table disagree")
        self.assertEqual(set(km._TARGET_NAME_OPS), set(self.TARGET), "the target tuple and this table disagree")
        self.assertEqual(set(self.TYPED) & set(self.TARGET), set(), "an op is typed text or a target")
        with tempfile.TemporaryDirectory() as d:
            saved = km.jd.STATE
            km.jd.STATE = pathlib.Path(d)
            records = pathlib.Path(d) / "undelivered.jsonl"

            def rows():
                return [json.loads(x) for x in records.read_text().splitlines()] if records.exists() else []
            try:
                with mock.patch.object(km._TMUX, "available", lambda: False), \
                     mock.patch.object(km, "_thread_names", lambda: {}), \
                     mock.patch.dict(km._remotes, {}, clear=True):
                    for op in sorted(accepted):
                        door = self.FRONT_DOOR.get(op) or ({} if op in self.TARGET else {"id": THEIRS})
                        for text in (None, self.TEXT):
                            msg = dict(door, type=op, name=self.NAME)
                            if text is not None:
                                msg["text"] = text
                            del self.sent[:]
                            before = len(rows())
                            self.assertTrue(km._drive(msg, self.client),
                                            (op, "the op did not reach the gate: its front-door keys are missing from FRONT_DOOR"))
                            new = rows()[before:]
                            self.assertEqual(len(new), 1, (op, msg, "one refusal, one row"))
                            self.assertEqual(len(self.sent), 1, (op, msg, self.sent))
                            row, modal = new[0], self.sent[0]
                            expect_text = text if text is not None else (self.NAME if op in self.TYPED else "")
                            expect_target = self.NAME if op in self.TARGET else ""
                            self.assertEqual((row["op"], row["text"], row["target"]), (op, expect_text, expect_target),
                                             (op, msg, "the row keeps the name as the classification says"))
                            self.assertEqual((modal["type"], modal["op"], modal["copy"]), ("err", op, expect_text), (op, msg))
                            self.assertEqual(row["sid"], modal["sid"], op)
                            self.assertEqual(modal["sid"], self.NAME if op in self.TARGET else THEIRS, op)
                            if expect_text:
                                self.assertIn("Your text is saved verbatim", modal["text"], (op, msg))
                            else:
                                self.assertIn("The refusal is recorded in undelivered.jsonl", modal["text"], (op, msg))
                                self.assertNotIn("Your text is saved verbatim", modal["text"], (op, msg))
                self.assertEqual(self.reached, [], "nothing was handed to a backend")
            finally:
                km.jd.STATE = saved


if __name__ == "__main__":
    unittest.main()
