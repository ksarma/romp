#!/usr/bin/env python3
"""Postal isolation (the user 2026-06-23): a session with the timeline lane's mailbox toggled off
(postalServiceOff — legacy postalOff — in the kernel's session-flags.json) is invisible to list_agents, can't send, and can't receive —
for working privately. These pin the flag reader + the read_box RECEIVE gate at the unit level; the
end-to-end /send + /agents enforcement is in tests/romp-postal.bats.

Synthetic only — placeholder UUIDs, hermetic temp state dir, no real session data.
"""
import json
import sys
import os
import shutil
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()      # hermetic; constants resolve under here at import
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
pm = load_source("romp_postal", os.path.join(BIN, "romp-postal-service"))
# The kernel, under a private name, for the one witness that writes a session flag through the kernel's own routes
# (ThreadOwnSendRefused, fork PR #897): the key the bus's thread gate reads, written by the kernel's WebSocket arm.
km = load_source("romp_kernel_isolation", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"
# The mailbox case drains a box of its OWN (2026-09-10). Every postal test module loads
# bin/romp-postal-service under the one name `romp_postal`, and load_source re-executes into the same
# module object, so under pytest they all share one MAILROOT, and most of them address the placeholder
# sid above. A sibling's case that leaves mail in that sid's new/ on purpose (the restore cases in
# tests/test_postal_deferred_push_identity.py put a message back) is drained by the sibling's later
# cases in serial order, but xdist hands cases to workers one at a time, so this case ran right after
# the leftover on one worker and read two bodies. Same rule as the goal-store fixtures (CLAUDE.md,
# Testing): a case that asserts the exact contents of a shared store uses a private synthetic sid. The
# flag cases keep SID: they read the flags file only, and clear it in tearDown.
BOX_SID = "12121212-3434-5656-7878-9a9a9a9a9a9a"


def _set_flag(sid, postal_off):
    pm.SESSION_FLAGS.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(pm.SESSION_FLAGS.read_text()) if pm.SESSION_FLAGS.exists() else {}
    if postal_off:
        data[sid] = {"postalOff": True}     # legacy key on purpose: pins back-compat (reader honours old + new)
    else:
        data.pop(sid, None)
    pm.SESSION_FLAGS.write_text(json.dumps(data))


class PostalOff(unittest.TestCase):
    def tearDown(self):
        try:
            pm.SESSION_FLAGS.unlink()
        except OSError:
            pass

    def test_default_not_isolated(self):
        self.assertFalse(pm._postal_off(SID), "no flags file → on the Romp Postal Service")
        self.assertFalse(pm._postal_off(""), "empty sid → not isolated")

    def test_flag_toggles_isolation(self):
        _set_flag(SID, True)
        self.assertTrue(pm._postal_off(SID))
        _set_flag(SID, False)
        self.assertFalse(pm._postal_off(SID), "clearing the flag rejoins the Romp Postal Service")

    def test_other_flags_do_not_isolate(self):
        pm.SESSION_FLAGS.parent.mkdir(parents=True, exist_ok=True)
        pm.SESSION_FLAGS.write_text(json.dumps({SID: {"hideFromFeed": True}}))   # muted from feed, NOT postal
        self.assertFalse(pm._postal_off(SID), "hideFromFeed alone must not isolate from postal")

    def test_malformed_flags_file_closes_cold_and_keeps_the_last_known_answer(self):
        # the flags dir is made HERE, not inherited from an earlier test: under pytest-xdist the
        # class's tests split across workers, and this one landed on a worker where no sibling had
        # created the dir yet (surfaced 2026-09-04 when the suite's test count shifted the split).
        # Until 2026-09-14 this pinned fail-open (a corrupt file read as no flags); the repo's rule is that an
        # unavailable source surfaces a fault, so a corrupt file with no flags known yet HOLDS mail (closed,
        # "unreadable", said once), and after a clean read the last known flags stand while it cannot be read
        pm.SESSION_FLAGS.parent.mkdir(parents=True, exist_ok=True)
        pm._FLAGS_LAST[0] = None; pm._FLAGS_FAULT_SAID[0] = False
        pm.SESSION_FLAGS.write_text("{not valid json")
        self.assertTrue(pm._postal_off(SID), "a corrupt flags file with nothing known: mail held, never a quiet on")
        self.assertEqual(pm._mail_off_why(SID), "flags", "the settings file's own word (the UI: mail held, the settings file cannot be read)")
        pm.SESSION_FLAGS.write_text(json.dumps({SID: {"hideFromFeed": True}}))
        self.assertFalse(pm._postal_off(SID), "a clean read: on")
        pm.SESSION_FLAGS.write_text("{not valid json")
        self.assertFalse(pm._postal_off(SID), "corrupt again: the last known flags stand (on)")

    def test_read_box_holds_mail_while_isolated(self):
        box = pm.MAILROOT / BOX_SID / "new"
        shutil.rmtree(box.parent, ignore_errors=True)               # nothing of an earlier run in it
        self.addCleanup(shutil.rmtree, box.parent, ignore_errors=True)
        box.mkdir(parents=True, exist_ok=True)
        (box / "msg1").write_text("From: peer\nFrom-Id: x\nDate: now\n\nhello\n")
        _set_flag(BOX_SID, True)
        self.assertEqual(pm.read_box(BOX_SID, consume=True), [],
                         "isolated → a drain delivers nothing")
        self.assertTrue((box / "msg1").exists(),
                        "the message stays in new/ (not consumed) until the session reconnects")
        _set_flag(BOX_SID, False)
        got = pm.read_box(BOX_SID, consume=True)
        self.assertEqual([m["body"] for m in got], ["hello"],
                         "reconnecting delivers the held mail")


class WiringAcrossSurfaces(unittest.TestCase):
    """The postalServiceOff flag spans three files (kernel boot exposure → timeline render/toggle → postal
    enforcement). Pin the cross-surface wiring by name so a rename can't silently disconnect a surface."""

    def test_kernel_boot_exposes_postaloff(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn('"postalServiceOff": _postal_isolated(sid)', src,
                      "the kernel must publish postalServiceOff in the session boot so the timeline can render it: the EFFECTIVE "
                      "state (the mailbox flag with its legacy twin, and a comment thread's mail-off default, T356)")

    def test_timeline_view_draws_and_toggles_the_mailbox(self):
        # Since 2026-07-28 the mailbox lives in the lane GEAR's drop-down (LANE_TOGGLES) rather than as
        # its own lane icon — the row still draws the mailboxIcon and toggles postalServiceOff through
        # the same _setSessionFlag persistence.
        src = open(os.path.join(os.path.dirname(BIN), "ui", "romp-timeline-view.js")).read()
        self.assertIn("mailboxIcon", src, "the gear menu draws the (monochrome) mailbox icon")
        self.assertIn("flag: 'postalServiceOff', label: 'Postal service', icon: mailboxIcon", src,
                      "the gear menu row toggles the postalServiceOff flag")
        self.assertIn("this._setSessionFlag(s, t.flag, next);", src, "menu rows persist via _setSessionFlag")



# ── a comment thread's mail is OFF until the user breaks it out (T356) ──────────────────────────────────

PARENT = "22222222-3333-4444-5555-666666666666"
THREAD = "66666666-7777-8888-9999-aaaaaaaaaaaa"
SENDER = "77777777-8888-9999-aaaa-bbbbbbbbbbbb"


def _reg(sid, **fields):
    d = pm.SESSION_FLAGS.parent / "sdk"
    d.mkdir(parents=True, exist_ok=True)
    (d / (sid + ".json")).write_text(json.dumps({"sid": sid, "alive": True, **fields}))


def _flags(data):
    pm.SESSION_FLAGS.parent.mkdir(parents=True, exist_ok=True)
    pm.SESSION_FLAGS.write_text(json.dumps(data))


class ThreadMailOff(unittest.TestCase):
    """The bus derives a thread's mail-off default from the kernel's durable reg (threadOf) beside the flags file:
    a thread on disk with NO flag reads OFF (the user 2026-09-11: a manager's comment thread received the manager's
    mail, mailed two workers and merged a pull request as if it were the manager); the fresh key `threadMail` at the
    literal True is the one way on short of a break-out; a break-out (threadOf gone) returns the ordinary rule."""

    def tearDown(self):
        for f in (pm.SESSION_FLAGS, pm.SESSION_FLAGS.parent / "sdk" / (THREAD + ".json"), pm.SESSION_FLAGS.parent / "sdk" / (SENDER + ".json")):
            try:
                f.unlink()
            except OSError:
                pass

    def test_a_thread_with_no_flag_reads_off_and_says_why(self):
        _reg(THREAD, threadOf=PARENT)
        self.assertEqual(pm._mail_off_why(THREAD), "thread"); self.assertTrue(pm._postal_off(THREAD))
        self.assertEqual(pm._mail_off_why(PARENT), "", "the session it belongs to is untouched")
        self.assertEqual(pm._thread_of(THREAD), PARENT); self.assertEqual(pm._thread_of(PARENT), "", "no reg: an ordinary session")

    def test_the_fresh_key_at_the_literal_true_turns_it_on_and_nothing_else_does(self):
        _reg(THREAD, threadOf=PARENT)
        _flags({THREAD: {"threadMail": True}})
        self.assertEqual(pm._mail_off_why(THREAD), "")
        for v in ("true", 1, "on"):
            _flags({THREAD: {"threadMail": v}})
            self.assertEqual(pm._mail_off_why(THREAD), "thread", repr(v))
        _flags({THREAD: {"postalServiceOff": False}})
        self.assertEqual(pm._mail_off_why(THREAD), "thread", "the mailbox flag at False is no way on for a thread")
        _flags({THREAD: {"threadMail": True, "postalServiceOff": True}})
        self.assertEqual(pm._mail_off_why(THREAD), "isolation", "mail on for the thread, then the user's own isolation holds")
        _flags("{not json")
        self.assertEqual(pm._mail_off_why(THREAD), "isolation", "a corrupt flags file keeps the LAST KNOWN flags (the rule since "
                         "2026-09-14: an unavailable source is never a quiet fresh answer), so the user's isolation still holds")
        pm._FLAGS_LAST[0] = None; pm._FLAGS_FAULT_SAID[0] = False
        self.assertEqual(pm._mail_off_why(THREAD), "thread", "a corrupt flags file with nothing known cannot turn a thread's mail on")

    def test_breaking_out_returns_the_ordinary_rule(self):
        _reg(THREAD, threadOf=PARENT)
        self.assertTrue(pm._postal_off(THREAD))
        _reg(THREAD)                                   # promotion pops threadOf from the reg
        self.assertEqual(pm._mail_off_why(THREAD), ""); self.assertFalse(pm._postal_off(THREAD))
        _flags({THREAD: {"postalOff": True}})
        self.assertEqual(pm._mail_off_why(THREAD), "isolation")

    def test_the_receive_gate_holds_a_threads_mail_in_its_box(self):
        _reg(THREAD, threadOf=PARENT)
        box = pm.MAILROOT / THREAD / "new"
        box.mkdir(parents=True, exist_ok=True)
        (box / "msg1").write_text("From: peer\nFrom-Id: x\nDate: now\n\nhello\n")
        self.assertEqual(pm.read_box(THREAD, consume=True), [], "held, not delivered")
        self.assertTrue((box / "msg1").exists(), "…and kept for the day the thread is broken out")

    def test_a_thread_is_invisible_to_peers_and_a_send_to_it_is_refused_with_the_thread_reason(self):
        _reg(THREAD, threadOf=PARENT)
        rows = [{"id": PARENT, "name": "web"}, {"id": THREAD, "name": "web-comment-1", "thread": True, "parent": PARENT},
                {"id": SENDER, "name": "api"}]
        saved = pm._kernel_sessions_checked
        pm._kernel_sessions_checked = lambda threads=False: ([r for r in rows if threads or not r.get("thread")], True)
        try:
            visible = [a["id"] for a in pm.all_agents(threads=True) if not pm._postal_off(a["id"])]   # the /agents filter
            self.assertNotIn(THREAD, visible); self.assertIn(PARENT, visible)
            res = pm.resolve_recipient("web-comment-1", SENDER)
            self.assertEqual((res["kind"], res["status"]), ("error", 403))
            self.assertIn("COMMENT THREAD", res["error"]); self.assertIn("breaks it out", res["error"]); self.assertIn("final", res["error"])
            _flags({THREAD: {"threadMail": True}})
            res = pm.resolve_recipient("web-comment-1", SENDER)
            self.assertEqual(res["kind"], "direct", "with mail on, the thread is a recipient like any other")
        finally:
            pm._kernel_sessions_checked = saved


class ThreadOwnSendRefused(unittest.TestCase):
    """The thread's OWN send, over the real handler: 403 whose text says the thread's mail is off until it is
    broken out (final; the isolation refusal a peer must not route around). The gate is also the witness the
    deadness mirror's disclosure rests on (fork PR #897, round 3): the mirror's roster omits comment threads, and
    the road to a false presumed-closed for a live thread runs only through a thread's mail crossing a host, which
    this gate refuses before the relay unless the `threadMail` flag is set. One road writes that key today: the
    kernel's WebSocket setSessionFlag arm, which accepts any flag name a client sends, while POST /flag, the one other
    kernel route that writes a session flag, applies the _LANE_FLAGS whitelist and refuses it; a separate fix-tier PR
    makes the WebSocket arm apply the same whitelist."""

    KERNEL_SRC = os.path.realpath(os.path.join(BIN, "romp-kernel"))   # the file km was loaded from (kernel/kernel.py)
    FLAG_WRITERS = {"_set_session_flag", "_set_notify_session"}
    FLAG_ROUTES = {("_state_write_route", "/flag"), ("Handler._dispatch_ws", "setSessionFlag")}
    # The net's exemption rows (round 4 of fork PR #897, the reviewer's ruling on section G): each function the net refuses
    # in kernel/kernel.py, with the reason the refusal is false. A row naming a function the net does not refuse raises.
    NET_EXEMPT = {
        "_state_quarantine": "moves an unparseable state file aside to a .corrupt name, and compares its name with the store's to "
                             "word its log line; it sets no flag",
        "_edit_tag": "its parameter rename holds a tag's new name; it holds no door call",
        "_set_notify_card": "writes notify-cards.json (its one door call names that file) and reads the session's flags through "
                            "_session_flags_proved",
        "_comments_frame": "holds no door call; builds a comment thread's frame from _thread_events and _mail_off_why_k",
        "_thread_rows": "holds no door call; spreads _mail_off_fields into each thread's row",
        "_push_subagents": "holds no door call; pushes the frame _subagent_frame_cached returns",
        "_chat_push_scopes_open": "holds no door call; keeps the signature _chat_sig_shared returns on the push scope",
        "_chat_build_sig": "holds no door call; reads that signature, or _chat_sig_shared's, into the chat's own",
        "build_feed": "holds no door call; keys each card's cache on _feed_session_key",
        "build_timeline": "holds no door call; puts each lane's flag values and _dead_lane_key's cache key in the timeline",
        "_history_pages": "holds no door call; collects the pages _chat_history_page returns",
        "_warm_history_pages": "holds no door call; warms the pages _chat_history_page returns and their _page_sig signatures",
        "_push": "holds no door call; pushes the rows build_session, _provisional_row and _mail_off_fields return",
        "_push_session_now": "holds no door call; pushes the row build_session returns",
        "_fleet_view_sig": "holds no door call; stats the store among the files whose change busts the view cache",
        "Handler.do_POST": "the HTTP POST handler: its one door call is a str.replace on an error message, and it hands a POST "
                           "to _state_write_route, a route in the set pin, and answers with the pair that returns",
        "Handler._dispatch_ws": "the WebSocket dispatcher: its door calls append to card-opens.jsonl and locate-audit.jsonl, and "
                                "it sends the readers' values to its clients; it writes a flag through _set_session_flag and "
                                "_set_notify_session, the references in the set pin",
    }

    @staticmethod
    def _flag_writing_routes(source, exempt=None, refusals=False):
        """The kernel's routes that write a session flag, DERIVED from the source, behind a NET that refuses by name
        what the derivation leaves unclassified (fork PR #897, each under the reviewer's ruling on section G: derived in
        round 3, to a fixpoint at round 4's thirty-sixth commit, the net at its forty-first). Returns (writers,
        references), and raises, naming each function the net refuses, unless `exempt` maps it to the reason the refusal
        is false; with refusals=True it returns the refused rows as a third element instead. Each rule below names its
        plant, a subtest of test_the_flag_route_census_finds_a_new_route_and_a_writer_of_each_shape (the derivation) or
        of test_the_net_refuses_what_the_derivation_leaves_unclassified (the net), by its label.
        THE DERIVATION. A WRITER is a function holding a call of a door one of whose arguments, positional or keyword,
        or whose receiver, carries the flags path ("the path in a door's keyword argument", "open called as a method"),
        named "<module>" for a call outside every function, a class body included ("each writer shape", "a door call in
        a class body is the writer <module>"). The doors: a call named _write_state_json, _atomic_write, open, replace,
        rename, write_text or write_bytes, by bare name or as a method whatever its receiver (each door planted in both
        forms, this list asserted equal to the list planted). An expression CARRIES the path when it holds the constant
        "session-flags.json", a name bound to the path, or a call, by bare name or as a method, of a PATH FUNCTION: a
        function one of whose own return statements returns an expression that carries the path ("a path function called
        as a method", "a path function with a return that does not carry the path beside one that does", "a path
        function returning a name bound in it"). A name is BOUND to the path by an assignment, plain, annotated or
        augmented, to a plain name whose value carries the path, in any order ("a module-level name bound by an
        annotated assignment", "a name bound by an augmented assignment", "a module-level name bound inside a try, and a
        name bound to one the walk reaches later"). A binding outside every function counts everywhere, inside an if or
        a try there included ("a module-level name bound inside an if"); a binding in a function counts throughout the
        outermost function around it, in every function nested in it at any depth ("a closure's write through a name its
        enclosing function binds", "a write through a name a nested function binds through a nonlocal statement", "a
        write in a function beside the binding in one outermost function", "a path function returning a name its
        enclosing function binds", and the two plants four functions deep). Path functions and module-level names grow
        together to a FIXPOINT ("a path function returning a module-level name", "a two-level chain of path functions,
        and a module-level name bound to a path function's call"). A REFERENCE is every other mention of a writer's name
        in the file, a call or not ("a mention of a writer that is not a call", "a mention of a writer through an
        attribute", "a mention of a writer outside every function", "a mention of a writer in a class body"), as (the
        dotted name of the classes and functions around it, outermost first, "<module>" outside all of them ("a mention
        of a writer inside a nested function", "a mention of a writer in a method of a class defined in a function");
        the selectors; the writer). The SELECTORS are, outermost first ("the selectors of nested ifs, outermost first"),
        the string constants among the operands of each comparison whose operators are all ==, either side and every
        operand of a chain ("a selector is a string constant compared for equality", "a selector on the left of its
        comparison", the two chain plants), every such comparison the test holds at any depth ("every comparison of a
        test, under an or, an and and a not", "a comparison inside a call in the test"), of each if statement whose body
        holds the mention, between the mention and the function around it, up to the module outside every function ("the
        selectors of a mention outside every function"). Widenings are not planted: the census's precision is pinned
        only by the exact set pin on the real kernel.py, where a census that finds more fails loudly.
        THE NET. A pre-scan of every name the source holds (every identifier field of every node of its tree: a
        variable, an attribute, the name of a def, a class or a parameter, a keyword's label, an import, a global
        statement's names; checked against Python's tokenizer, so a name token the scan does not read raises) and every
        string it holds (a constant, bytes, a piece of an f-string), keyed on the derivation's own sets, so the two
        agree by construction. Five clauses, each refusing a function (by its dotted name, "<module>" outside every
        function) with the token and its line: THE STORE'S NAME, a string holding "session-flags.json" (each plant of
        what the derivation does not see, below); A MODULE-LEVEL NAME of the fixpoint's, as a name or as a string equal
        to it, a name reached through globals(), getattr or a table ("a module-level name handed on by unpacking", "a
        module-level name reached through globals()"); A PATH FUNCTION of the fixpoint's, the same two ways ("a path
        function's call handed on by unpacking", "a path function reached through getattr and a string"); A DOOR's name,
        as a name alone, since the kernel uses open, replace and rename as words ("a door handed on as a value", "a door
        imported under another name"); and A WRITER's name, as a name or a string ("a writer imported under another name
        in a route", "a writer reached through getattr and a string in a route"). A mention is FOLDED, and counts for no
        clause, when it is the name of a def or a class, or a keyword's label ("a def named like a door, and a keyword
        labelled like one"; a parameter's name is not: "a parameter named like a door"); a door's name, when it names a
        call the derivation reads as a door ("each writer shape"); a string, when it is a whole statement, as a
        docstring is ("a docstring naming the store"); a path function's call or a module-level name, when its truth
        alone decides the test of an if, a while or a conditional expression, through and, or and not ("a path
        function's call and a module-level name whose truth alone decides a test"; a comparison hands the value on, and
        so does a call: "a module-level name compared in a test", "a path function's call handed to a call in a test").
        The derivation CLASSIFIES the rest, function by function: a writer's name in a function holding a reference ("a
        mention of a writer that is not a call"); the store's name, a module-level name or a path function in a writer,
        and in a function holding no door call the derivation reads when it is a path function or holds a binding whose
        outermost function holds a writer or a path function ("a path function that also writes the path through
        unpacking", "a name bound in another outermost function", "a name bound in a function, written outside every
        function", "a name bound in another method of the same class", "a name bound in another outermost function
        through a global statement"), and outside every function when a binding is there, its name then a module-level
        name, every mention of which the net reads ("a module-level name bound inside an if"). A door's name it does not
        read as a call it classifies nowhere ("a writer that also hands a door on as a value"). A function the net
        refuses on the real kernel.py is named in NET_EXEMPT with its reason, and a row naming a function the net does
        not refuse raises, so the rows stay exact ("an exemption row names a refused function", "an exemption row that
        names no refused function"). What the derivation does not see, each planted, asserted not found and refused:
        shutil.copy, a subprocess, a path handed to a helper that writes its parameter, a door reached through getattr
        and a string, and a name bound by unpacking into a tuple, by a for loop's target, by an assignment expression,
        by a parameter's default, by a comprehension's target, by a with statement's as, by an assignment to an
        attribute, in an attribute and written in another method, or through a global statement.
        THE NET'S LIMITS, each with a witness asserted neither found nor refused. The net folds every door call the
        derivation reads, whatever it writes, so a write the derivation misses is refused only through a path token, in
        its own function or in the function the path comes from: (a) a path built at run time, so that no string holds
        the store's name and no derived name carries it ("a path built by string concatenation"); (b) the net is
        function-level, so a function the derivation classifies is refused for none of its mentions, and a path such a
        function writes through a door reached by a string, or hands on through a channel the derivation does not follow
        to a function whose door call the derivation reads, passes both ("a path function writing its path through
        getattr and a string", "a path function handing its path to a helper that writes its parameter")."""
        import ast
        import io
        import keyword
        import tokenize
        from collections import Counter
        flags = "session-flags.json"
        doors = ("_write_state_json", "_atomic_write", "open", "replace", "rename", "write_text", "write_bytes")
        tree = ast.parse(source)
        parent = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
        defs = (ast.FunctionDef, ast.AsyncFunctionDef)

        def up(node):                                  # the ancestors, innermost first
            while node in parent:
                node = parent[node]
                yield node

        def function_of(node):
            return next((n for n in up(node) if isinstance(n, defs)), None)

        def unit(fn):                                  # the outermost function around fn, fn included (None outside every function)
            return next((n for n in reversed([fn, *up(fn)]) if isinstance(n, defs)), None) if fn is not None else None

        def names_in(fn):                              # the names bound to the path that count in fn: every binding in its unit,
            u = unit(fn)                               # the functions nested in it at any depth included, and the module's
            if u not in scoped:
                scoped[u] = bound_in(ast.walk(u), module_names)
            return scoped[u]

        path_funcs = set()                             # grown to the fixpoint below

        def carries(expr, names):
            for n in ast.walk(expr):
                if isinstance(n, ast.Constant) and n.value == flags or isinstance(n, ast.Name) and n.id in names:
                    return True
                if isinstance(n, ast.Call) and (getattr(n.func, "id", None) or getattr(n.func, "attr", None)) in path_funcs:
                    return True
            return False

        def bound_in(nodes, names):                    # the names an assignment among `nodes` binds to the flags path, to a
            names = set(names)                         # fixpoint, so a name bound to one bound later in the walk counts too
            assigns = [n for n in nodes if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and n.value is not None]
            while True:
                grown = {t.id for n in assigns if carries(n.value, names)
                         for t in (n.targets if isinstance(n, ast.Assign) else [n.target]) if isinstance(t, ast.Name)} - names
                if not grown:
                    return names
                names |= grown

        def door_call(node):                           # a call the derivation reads as a door: named a door, bare or as a method
            return isinstance(node, ast.Call) and (getattr(node.func, "id", None) or getattr(node.func, "attr", None)) in doors

        outside = [n for n in ast.walk(tree) if function_of(n) is None]   # every node outside every function
        functions = [n for n in ast.walk(tree) if isinstance(n, defs)]
        returns = {fn: [n.value for n in ast.walk(fn) if isinstance(n, ast.Return) and n.value is not None and function_of(n) is fn]
                   for fn in functions}              # each function's OWN return values (a nested function's are its own)
        while True:                                    # THE FIXPOINT: module-level names and path functions grow together
            module_names = bound_in(outside, ())
            scoped = {None: module_names}              # names_in() per unit, recomputed on each pass with its path functions
            grown = {fn.name for fn in functions if fn.name not in path_funcs and any(carries(r, names_in(fn)) for r in returns[fn])}
            if not grown:
                break
            path_funcs |= grown
        writers, writing = set(), set()                # the writers' names, and the functions holding a write (None outside all)
        for node in ast.walk(tree):
            if not door_call(node):
                continue
            f = node.func
            fn = function_of(node)
            parts = list(node.args) + [k.value for k in node.keywords] + ([f.value] if isinstance(f, ast.Attribute) else [])
            if any(carries(p, names_in(fn)) for p in parts):
                writers.add("<module>" if fn is None else fn.name)
                writing.add(fn)
        refs, referring = [], set()                    # the references, and the functions holding one
        for node in ast.walk(tree):
            name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
            if name not in writers:
                continue
            fn, selectors, child = function_of(node), [], node
            for n in up(node):
                if n is fn:
                    break
                if isinstance(n, ast.If) and any(child is b for b in n.body):
                    selectors[:0] = [x.value for c in ast.walk(n.test) if isinstance(c, ast.Compare) and all(isinstance(o, ast.Eq) for o in c.ops)
                                     for x in [c.left] + c.comparators if isinstance(x, ast.Constant) and isinstance(x.value, str)]
                child = n
            where = ".".join(reversed([n.name for n in up(node) if isinstance(n, defs + (ast.ClassDef,))])) or "<module>"
            refs.append((where, tuple(selectors), name))
            referring.add(fn)

        # THE NET, keyed on the derivation's own sets (the docstring's second part)
        def deciding(node):                            # its truth alone decides the test of an if, a while or a conditional
            while (isinstance(parent.get(node), ast.BoolOp)                        # expression, through and, or and not
                   or isinstance(parent.get(node), ast.UnaryOp) and isinstance(parent[node].op, ast.Not)):
                node = parent[node]
            return isinstance(parent.get(node), (ast.If, ast.While, ast.IfExp)) and parent[node].test is node

        def folded(clause, node, field):
            if isinstance(node, defs + (ast.ClassDef,)) and field == "name" or isinstance(node, ast.keyword):
                return True                            # the name of a def or a class, a keyword's label
            call = parent[node] if isinstance(parent.get(node), ast.Call) and parent[node].func is node else None
            if clause == "a door":
                return call is not None and door_call(call)
            if clause == "a path function":
                return call is not None and deciding(call)
            if clause == "a module-level name":
                return isinstance(node, ast.Name) and deciding(node)
            return False

        keyed = {"a module-level name": module_names, "a path function": path_funcs, "a door": set(doors), "a writer": writers}
        mentions, scanned = [], Counter()              # (function, clause, key, line) unfolded; every name the scan reads
        for node in ast.walk(tree):
            line = getattr(node, "lineno", None) or next((n.lineno for n in up(node) if getattr(n, "lineno", None)), 0)
            if isinstance(node, ast.Constant):
                v = node.value
                if not isinstance(parent.get(node), ast.Expr):                     # a whole statement, as a docstring is
                    if isinstance(v, str) and flags in v or isinstance(v, bytes) and flags.encode() in v:
                        mentions.append((function_of(node), "the store's name", flags, line))
                    mentions += [(function_of(node), clause, v, line)           # a name reached through a string
                                 for clause in ("a module-level name", "a path function", "a writer")
                                 if isinstance(v, str) and v in keyed[clause]]
                continue
            for field, value in ast.iter_fields(node):
                for word in [value] if isinstance(value, str) else value if isinstance(value, list) else ():
                    for key in word.split(".") if isinstance(word, str) else ():
                        scanned[key] += 1
                        mentions += [(function_of(node), clause, key, line) for clause, keys in keyed.items()
                                     if key in keys and not folded(clause, node, field)]
        kinds, tokens, previous = set(keyword.kwlist) | set(getattr(keyword, "softkwlist", ())), Counter(), None
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.NAME and tok.string not in kinds and getattr(previous, "string", None) != "!":
                tokens[tok.string] += 1                # (a name after "!" is an f-string's conversion, which no node holds)
            if tok.type not in (tokenize.NL, tokenize.COMMENT):
                previous = tok
        missed = tokens - scanned                      # raised, never asserted: python -O strips an assert, and the net with it
        if missed:
            raise AssertionError("THE NET'S SCAN READS EVERY NAME TOKEN: the tokenizer reads %s, which the scan does not"
                                 % sorted(missed))
        door_holders = {function_of(n) for n in ast.walk(tree) if door_call(n)}
        path_nodes = {fn for fn in functions if any(carries(r, names_in(fn)) for r in returns[fn])}
        binding = {function_of(n) for n in ast.walk(tree)                  # the functions holding a binding the derivation reads
                   if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and n.value is not None
                   and any(isinstance(t, ast.Name) for t in (n.targets if isinstance(n, ast.Assign) else [n.target]))
                   and carries(n.value, names_in(function_of(n)))}

        def reaching(fn):                              # the outermost function around fn holds a writer or a path function
            u = unit(fn)
            return any(r is not None and (r is u or u in set(up(r))) for r in writing | path_nodes)

        def classified(fn, clause):                    # the derivation accounts for the clause's mentions in fn
            if clause == "a door":
                return False                           # a door's name it does not read as a call: a door it does not follow
            if clause == "a writer":
                return fn in referring
            return fn in writing or fn not in door_holders and (fn in path_nodes or fn in binding and (fn is None or reaching(fn)))

        def dotted(fn):
            around = [n.name for n in [fn, *up(fn)] if isinstance(n, defs + (ast.ClassDef,))] if fn is not None else []
            return ".".join(reversed(around)) or "<module>"

        refused = sorted({(dotted(fn), clause, key, line) for fn, clause, key, line in mentions if not classified(fn, clause)},
                         key=lambda r: (r[3], r[0], r[1], r[2]))
        exempt = dict(exempt or {})
        stale = sorted(set(exempt) - {r[0] for r in refused})
        if stale:
            raise AssertionError("THE NET'S EXEMPTION ROWS NAME ONLY WHAT IT REFUSES: %s is refused by nothing" % stale)
        refused = [r for r in refused if r[0] not in exempt]
        if refusals:
            return writers, sorted(refs), refused
        if refused:
            raise AssertionError("THE NET REFUSES a function that mentions a name the census derives and that the derivation "
                                 "leaves unclassified (fork PR #897, round 4, the reviewer's ruling on section G): %s. Classify "
                                 "it by a rule of the derivation, or name it in an exemption row with its reason"
                                 % "; ".join("%s mentions %s %r at line %d" % r for r in refused))
        return writers, sorted(refs)

    def test_the_flag_route_census_finds_a_new_route_and_a_writer_of_each_shape(self):
        """The census the witness below pins (fork PR #897, rounds 3 and 4), run against what its derivation must find, on
        planted sources, each plant in a subtest whose label the census's docstring names beside the rule it pins: a third
        WebSocket arm calling the setter; each writer shape and a helper between a route and a writer; the fixpoint's
        shapes; open called as a method; the bindings in a try and in walk order; one plant for each shape and rule the
        docstring lists; and each door name, by bare name and as a method. Each lands in the population, so the witness's
        set equality turns red on it. A plant here pins what the census finds; widenings are not planted."""
        census = self._flag_writing_routes
        third_arm = ('def _set_session_flag(sid, flag, value):\n'
                     '    _write_state_json(jd.STATE / "session-flags.json", "{}")\n'
                     'class Handler:\n'
                     '    def _dispatch_ws(self, msg, client):\n'
                     '        if msg.get("type") == "setSessionFlag":\n'
                     '            _set_session_flag(msg["id"], msg["flag"], True)\n'
                     '        elif msg.get("type") == "setSessionFlagAny":\n'
                     '            _set_session_flag(msg["id"], msg["flag"], True)\n')
        with self.subTest(shape="a third WebSocket arm"):
            self.assertEqual(census(third_arm), ({"_set_session_flag"},
                                                 [("Handler._dispatch_ws", ("setSessionFlag",), "_set_session_flag"),
                                                  ("Handler._dispatch_ws", ("setSessionFlagAny",), "_set_session_flag")]),
                             "a third WebSocket arm is a route of its own")
        shapes = ('FLAGS_PATH = STATE / "session-flags.json"\n'
                  'def _flags_path():\n'
                  '    return STATE / "session-flags.json"\n'
                  'def _by_name(cur):\n'
                  '    _atomic_write(FLAGS_PATH, cur)\n'
                  'def _by_function(cur):\n'
                  '    _flags_path().write_text(cur)\n'
                  'def _by_local(tmp):\n'
                  '    p = _flags_path()\n'
                  '    os.replace(tmp, p)\n'
                  'def _helper(b):\n'
                  '    _by_function(b)\n'
                  'def _route(path, b):\n'
                  '    if path == "/mute":\n'
                  '        _by_name(b)\n'
                  '        _helper(b)\n'
                  '        _by_local(b)\n'
                  'open(STATE / "session-flags.json", "w").write("{}")\n')
        with self.subTest(shape="each writer shape"):
            self.assertEqual(census(shapes), ({"_by_name", "_by_function", "_by_local", "<module>"},
                                              [("_helper", (), "_by_function"), ("_route", ("/mute",), "_by_local"),
                                               ("_route", ("/mute",), "_by_name")]),
                             "each writer shape is found, and a helper between a route and a writer is a reference of its own")
        by_module_name = ('_FLAGS_FILE = "session-flags.json"\n'
                          'def _flags_file():\n'
                          '    return jd.STATE / _FLAGS_FILE\n'
                          'def _set_any_flag(sid, flag, value):\n'
                          '    _write_state_json(_flags_file(), "{}")\n'
                          'class Handler:\n'
                          '    def _dispatch_ws(self, msg, client):\n'
                          '        if msg.get("type") == "setAnyFlag":\n'
                          '            _set_any_flag(msg["id"], msg["flag"], True)\n')
        with self.subTest(shape="a path function returning a module-level name"):
            self.assertEqual(census(by_module_name), ({"_set_any_flag"}, [("Handler._dispatch_ws", ("setAnyFlag",), "_set_any_flag")]),
                             "A PATH FUNCTION RETURNING A MODULE-LEVEL NAME bound to the constant (the kernel's _X_FILE and _x_path() "
                             "idiom) is a path function, so its caller's write is found and the new WebSocket arm is a route: until "
                             "the thirty-sixth commit a path function was one whose return held the constant itself, and this arm "
                             "wrote any flag while the witness stayed green")
        chained = ('_FLAGS_FILE = "session-flags.json"\n'
                   'def _base():\n'
                   '    return jd.STATE / "session-flags.json"\n'
                   'def _flags_file():\n'
                   '    return _base()\n'
                   'def _by_chain(cur):\n'
                   '    _atomic_write(_flags_file(), cur)\n'
                   'def _flags_path():\n'
                   '    return jd.STATE / _FLAGS_FILE\n'
                   'FLAGS_PATH = _flags_path()\n'
                   'def _by_bound_call(tmp):\n'
                   '    os.replace(tmp, FLAGS_PATH)\n')
        with self.subTest(shape="a two-level chain of path functions, and a module-level name bound to a path function's call"):
            self.assertEqual(census(chained), ({"_by_chain", "_by_bound_call"}, []),
                             "THE FIXPOINT: a path function calling another (two levels) is a path function, and a module-level "
                             "name bound to a call of a path function that returns a module-level name is bound to the path, so "
                             "both writers are found (a census that derives path functions once, from the constant, misses both; "
                             "one that iterates path functions alone, with the module-level names derived once before them, misses "
                             "the second)")
        attr_open = ('def _by_path_open(cur):\n'
                     '    p = jd.STATE / "session-flags.json"\n'
                     '    with p.open("w") as f:\n'
                     '        f.write(cur)\n'
                     'def _by_os_open(cur):\n'
                     '    fd = os.open(jd.STATE / "session-flags.json", os.O_WRONLY | os.O_CREAT)\n'
                     '    os.write(fd, cur)\n'
                     'def _by_io_open(cur):\n'
                     '    with io.open(jd.STATE / "session-flags.json", "w") as f:\n'
                     '        f.write(cur)\n')
        with self.subTest(shape="open called as a method"):
            self.assertEqual(census(attr_open), ({"_by_path_open", "_by_os_open", "_by_io_open"}, []),
                             "OPEN CALLED AS A METHOD is a door whatever its receiver, a Path, os or io: until the thirty-sixth "
                             "commit open was a door by bare name alone, and a writer through p.open wrote any flag while the "
                             "witness stayed green")
        scopes = ('try:\n'
                  '    FLAGS_PATH = jd.STATE / "session-flags.json"\n'
                  'except Exception:\n'
                  '    FLAGS_PATH = None\n'
                  'def _by_name_in_a_try(cur):\n'
                  '    _atomic_write(FLAGS_PATH, cur)\n'
                  'def _by_name_bound_later_in_the_walk(cur, alt):\n'
                  '    if alt:\n'
                  '        base = jd.STATE / "session-flags.json"\n'
                  '    p = base\n'
                  '    p.write_text(cur)\n')
        with self.subTest(shape="a module-level name bound inside a try, and a name bound to one the walk reaches later"):
            self.assertEqual(census(scopes), ({"_by_name_in_a_try", "_by_name_bound_later_in_the_walk"}, []),
                             "THE BINDINGS: a name bound outside every function counts inside a try there, and a name bound to "
                             "another bound name counts whatever order the walk meets the two assignments in (the walk reaches a "
                             "branch's body after the statement below the branch), so both writers are found (a census reading "
                             "module-level names from the module's top statements alone misses the first; one binding names in a "
                             "single pass misses the second)")
        setter = ('def _set_flag(sid):\n'
                  '    _write_state_json(jd.STATE / "session-flags.json", "{}")\n')
        listed = (("a path function called as a method",
                   'class Store:\n'
                   '    def _flags_path(self):\n'
                   '        return jd.STATE / "session-flags.json"\n'
                   '    def _by_method_call(self, cur):\n'
                   '        _atomic_write(self._flags_path(), cur)\n',
                   ({"_by_method_call"}, [])),
                  ("a module-level name bound by an annotated assignment",
                   '_FLAGS_FILE: str = "session-flags.json"\n'
                   'def _by_annotated_name(cur):\n'
                   '    _atomic_write(jd.STATE / _FLAGS_FILE, cur)\n',
                   ({"_by_annotated_name"}, [])),
                  ("the path in a door's keyword argument",
                   'def _by_keyword(cur):\n'
                   '    with open(file=jd.STATE / "session-flags.json", mode="w") as f:\n'
                   '        f.write(cur)\n',
                   ({"_by_keyword"}, [])),
                  ("a path function returning a name bound in it",
                   'def _flags_path():\n'
                   '    p = jd.STATE / "session-flags.json"\n'
                   '    return p\n'
                   'def _by_local_in_the_path_function(cur):\n'
                   '    _atomic_write(_flags_path(), cur)\n',
                   ({"_by_local_in_the_path_function"}, [])),
                  ("the rename door",
                   'def _by_rename(tmp):\n'
                   '    os.rename(tmp, jd.STATE / "session-flags.json")\n',
                   ({"_by_rename"}, [])),
                  ("the write_bytes door",
                   'def _by_write_bytes(cur):\n'
                   '    (jd.STATE / "session-flags.json").write_bytes(cur)\n',
                   ({"_by_write_bytes"}, [])),
                  ("a module-level name bound inside an if",
                   'if jd.STATE:\n'
                   '    FLAGS_PATH = jd.STATE / "session-flags.json"\n'
                   'def _by_name_in_an_if(cur):\n'
                   '    _atomic_write(FLAGS_PATH, cur)\n',
                   ({"_by_name_in_an_if"}, [])),
                  ("a mention of a writer that is not a call",
                   setter + 'class Handler:\n'
                            '    def _dispatch_ws(self, msg, client):\n'
                            '        if msg.get("type") == "setFlagLater":\n'
                            '            client["then"] = _set_flag\n',
                   ({"_set_flag"}, [("Handler._dispatch_ws", ("setFlagLater",), "_set_flag")])),
                  ("a selector is a string constant compared for equality",
                   setter + 'def _route(path, b):\n'
                            '    if path == "/flag" and "id" in b and len(b) == 2:\n'
                            '        _set_flag(b["id"])\n',
                   ({"_set_flag"}, [("_route", ("/flag",), "_set_flag")])),
                  ("a path function with a return that does not carry the path beside one that does",
                   'def _flags_path():\n'
                   '    if jd.STATE is None:\n'
                   '        return None\n'
                   '    return jd.STATE / "session-flags.json"\n'
                   'def _by_early_return(cur):\n'
                   '    _atomic_write(_flags_path(), cur)\n',
                   ({"_by_early_return"}, [])),
                  ("a mention of a writer through an attribute",
                   'class Handler:\n'
                   '    def _set_flag(self, sid):\n'
                   '        _write_state_json(jd.STATE / "session-flags.json", "{}")\n'
                   '    def _dispatch_ws(self, msg, client):\n'
                   '        if msg.get("type") == "setFlagSelf":\n'
                   '            self._set_flag(msg["id"])\n',
                   ({"_set_flag"}, [("Handler._dispatch_ws", ("setFlagSelf",), "_set_flag")])),
                  ("a selector on the left of its comparison",
                   setter + 'def _route(path, b):\n'
                            '    if "/flag" == path:\n'
                            '        _set_flag(b["id"])\n',
                   ({"_set_flag"}, [("_route", ("/flag",), "_set_flag")])),
                  ("the selectors of nested ifs, outermost first",
                   setter + 'def _route(path, b):\n'
                            '    if path == "/flag":\n'
                            '        if b.get("op") == "set":\n'
                            '            _set_flag(b["id"])\n',
                   ({"_set_flag"}, [("_route", ("/flag", "set"), "_set_flag")])),
                  ("a mention of a writer outside every function",
                   setter + '_WS_OPS = {"setAnyFlag": _set_flag}\n',
                   ({"_set_flag"}, [("<module>", (), "_set_flag")])),
                  ("a mention of a writer in a class body",
                   setter + 'class Handler:\n'
                            '    OPS = {"setAnyFlag": _set_flag}\n',
                   ({"_set_flag"}, [("Handler", (), "_set_flag")])),
                  ("the selectors of a mention outside every function",
                   setter + 'if MODE == "legacy":\n'
                            '    _WS_OPS = {"setAnyFlag": _set_flag}\n',
                   ({"_set_flag"}, [("<module>", ("legacy",), "_set_flag")])),
                  ("every comparison of a test, under an or, an and and a not",
                   setter + 'def _route(path, b):\n'
                            '    if path == "/flag" or (b.get("op") == "set" and not b.get("dry") == "yes"):\n'
                            '        _set_flag(b["id"])\n',
                   ({"_set_flag"}, [("_route", ("/flag", "set", "yes"), "_set_flag")])),
                  ("a name bound by an augmented assignment",
                   'def _by_augmented(cur):\n'
                   '    p = jd.STATE\n'
                   '    p /= "session-flags.json"\n'
                   '    p.write_text(cur)\n',
                   ({"_by_augmented"}, [])),
                  ("a closure's write through a name its enclosing function binds",
                   'def _outer(cur):\n'
                   '    p = jd.STATE / "session-flags.json"\n'
                   '    def _inner():\n'
                   '        p.write_text(cur)\n'
                   '    _locked(_inner)\n',
                   ({"_inner"}, [("_outer", (), "_inner")])),
                  ("a write through a name a nested function binds through a nonlocal statement",
                   'def _by_nonlocal(cur):\n'
                   '    p = None\n'
                   '    def _bind():\n'
                   '        nonlocal p\n'
                   '        p = jd.STATE / "session-flags.json"\n'
                   '    _bind()\n'
                   '    p.write_text(cur)\n',
                   ({"_by_nonlocal"}, [])),
                  ("a write in a function beside the binding in one outermost function",
                   'def _outer(cur):\n'
                   '    def _bind():\n'
                   '        p = jd.STATE / "session-flags.json"\n'
                   '    def _save():\n'
                   '        p.write_text(cur)\n'
                   '    _locked(_save)\n',
                   ({"_save"}, [("_outer", (), "_save")])),
                  ("a path function returning a name its enclosing function binds",
                   'def _by_closure_path(cur):\n'
                   '    p = jd.STATE / "session-flags.json"\n'
                   '    def _path():\n'
                   '        return p\n'
                   '    _atomic_write(_path(), cur)\n',
                   ({"_by_closure_path"}, [])),
                  ("every operand of a chain of ==, the left one included",
                   setter + 'def _route(path, b):\n'
                            '    if "/flag" == path == "/flags":\n'
                            '        _set_flag(b["id"])\n',
                   ({"_set_flag"}, [("_route", ("/flag", "/flags"), "_set_flag")])),
                  ("every operand of a chain of == four operands long",
                   setter + 'def _route(path, route, b):\n'
                            '    if path == "/flag" == route == "/flags":\n'
                            '        _set_flag(b["id"])\n',
                   ({"_set_flag"}, [("_route", ("/flag", "/flags"), "_set_flag")])),
                  ("a comparison inside a call in the test",
                   setter + 'def _route(path, b):\n'
                            '    if any((path == "/flag", path == "/flags")):\n'
                            '        _set_flag(b["id"])\n',
                   ({"_set_flag"}, [("_route", ("/flag", "/flags"), "_set_flag")])),
                  ("a write four functions deep through a name the outermost function binds",
                   'def _outer(cur):\n'
                   '    p = jd.STATE / "session-flags.json"\n'
                   '    def _a():\n'
                   '        def _b():\n'
                   '            def _c():\n'
                   '                p.write_text(cur)\n'
                   '            _locked(_c)\n'
                   '        _b()\n'
                   '    _a()\n',
                   ({"_c"}, [("_outer._a._b", (), "_c")])),
                  ("a write in the outermost function through a name bound four functions deep",
                   'def _by_deep_nonlocal(cur):\n'
                   '    p = None\n'
                   '    def _a():\n'
                   '        def _b():\n'
                   '            def _c():\n'
                   '                nonlocal p\n'
                   '                p = jd.STATE / "session-flags.json"\n'
                   '            _c()\n'
                   '        _b()\n'
                   '    _a()\n'
                   '    p.write_text(cur)\n',
                   ({"_by_deep_nonlocal"}, [])),
                  ("a mention of a writer inside a nested function",
                   setter + 'def _route(b):\n'
                            '    def _later():\n'
                            '        _set_flag(b["id"])\n'
                            '    return _later\n',
                   ({"_set_flag"}, [("_route._later", (), "_set_flag")])),
                  ("a mention of a writer in a method of a class defined in a function",
                   setter + 'def _make():\n'
                            '    class Handler:\n'
                            '        def _dispatch_ws(self, msg, client):\n'
                            '            if msg.get("type") == "setFlagMade":\n'
                            '                _set_flag(msg["id"])\n'
                            '    return Handler\n',
                   ({"_set_flag"}, [("_make.Handler._dispatch_ws", ("setFlagMade",), "_set_flag")])),
                  ("a door call in a class body is the writer <module>",
                   'class Boot:\n'
                   '    open(jd.STATE / "session-flags.json", "w").write("{}")\n',
                   ({"<module>"}, [])))
        for label, src, expected in listed:
            with self.subTest(listed=label):
                self.assertEqual(census(src), expected,
                                 "EACH SHAPE AND RULE THE CENSUS DOCSTRING LISTS HAS A PLANT (round 4 of fork PR #897): %s. "
                                 "A census that drops or changes the shape turns this plant red" % label)
        import re
        doors = ("_write_state_json", "_atomic_write", "open", "replace", "rename", "write_text", "write_bytes")
        named = re.search(r"The doors: a call named (.+?), by bare name or as a method", " ".join((census.__doc__ or "").split()))
        self.assertEqual(tuple(re.split(r", | or ", named.group(1))) if named else None, doors,
                         "the doors the census docstring names are the doors planted below, each in both forms")
        for door in doors:
            for form, call in (("bare", door), ("method", "store." + door)):
                writer = "_by_%s_%s" % (form, door.strip("_"))
                with self.subTest(door=door, form=form):
                    self.assertEqual(census('def %s(cur):\n    %s(jd.STATE / "session-flags.json", cur)\n' % (writer, call)),
                                     ({writer}, []),
                                     "EVERY DOOR NAME IS A DOOR BY BARE NAME AND AS A METHOD (round 4 of fork PR #897, the "
                                     "thirty-ninth commit): %s called %s. A census that drops this cell turns it red"
                                     % (door, "by bare name" if form == "bare" else "as a method"))

    def test_the_net_refuses_what_the_derivation_leaves_unclassified(self):
        """THE NET behind the census (round 4 of fork PR #897, the reviewer's ruling on section G): a pre-scan of every
        name and string the source holds, keyed on the derivation's own sets, refusing by name, with the token and its
        line, a function that mentions one and that the derivation leaves unclassified. Planted, each in a subtest whose
        label the census's docstring names beside the rule it pins: a refusal by each of the five clauses; each fold and
        where it stops; what the derivation accounts for; the exemption rows, applied and exact; each shape the derivation
        does not see, not found and refused; and a witness of each of the net's two limits, neither found nor refused."""
        census = self._flag_writing_routes
        setter = ('def _set_flag(sid):\n'
                  '    _write_state_json(jd.STATE / "session-flags.json", "{}")\n')
        name = "the store's name"
        planted = (("a module-level name handed on by unpacking",
                    'FLAGS_PATH = jd.STATE / "session-flags.json"\n'
                    'def _by_module_unpacking(cur):\n'
                    '    base, p = jd.STATE, FLAGS_PATH\n'
                    '    p.write_text(cur)\n',
                    (set(), [], [("_by_module_unpacking", "a module-level name", "FLAGS_PATH", 3)])),
                   ("a path function's call handed on by unpacking",
                    'def _flags_path():\n'
                    '    return jd.STATE / "session-flags.json"\n'
                    'def _by_call_unpacking(cur):\n'
                    '    base, p = jd.STATE, _flags_path()\n'
                    '    p.write_text(cur)\n',
                    (set(), [], [("_by_call_unpacking", "a path function", "_flags_path", 4)])),
                   ("a door handed on as a value",
                    'def _save(write, cur):\n'
                    '    write(cur)\n'
                    'def _by_door_value(p, cur):\n'
                    '    _save(p.write_text, cur)\n',
                    (set(), [], [("_by_door_value", "a door", "write_text", 4)])),
                   ("a writer that also hands a door on as a value",
                    'def _by_writer_and_door(cur):\n'
                    '    _atomic_write(jd.STATE / "session-flags.json", cur)\n'
                    '    _later(open)\n',
                    ({"_by_writer_and_door"}, [], [("_by_writer_and_door", "a door", "open", 3)])),
                   ("a door imported under another name",
                    'from os import replace as _move\n'
                    'def _by_imported_door(tmp):\n'
                    '    _move(tmp, jd.STATE / "session-flags.json")\n',
                    (set(), [], [("<module>", "a door", "replace", 1), ("_by_imported_door", name, "session-flags.json", 3)])),
                   ("a module-level name reached through globals()",
                    'FLAGS_PATH = jd.STATE / "session-flags.json"\n'
                    'def _by_globals(cur):\n'
                    '    globals()["FLAGS_PATH"].write_text(cur)\n',
                    (set(), [], [("_by_globals", "a module-level name", "FLAGS_PATH", 3)])),
                   ("a path function reached through getattr and a string",
                    'def _flags_path():\n'
                    '    return jd.STATE / "session-flags.json"\n'
                    'def _by_path_by_string(cur):\n'
                    '    getattr(sys.modules[__name__], "_flags_path")().write_text(cur)\n',
                    (set(), [], [("_by_path_by_string", "a path function", "_flags_path", 4)])),
                   ("a writer reached through getattr and a string in a route",
                    'class Handler:\n'
                    '    def _set_flag(self, sid):\n'
                    '        _write_state_json(jd.STATE / "session-flags.json", "{}")\n'
                    '    def _dispatch_ws(self, msg, client):\n'
                    '        if msg.get("type") == "setFlagByName":\n'
                    '            getattr(self, "_set_flag")(msg["id"])\n',
                    ({"_set_flag"}, [], [("Handler._dispatch_ws", "a writer", "_set_flag", 6)])),
                   ("a writer imported under another name in a route",
                    setter + 'def _route(b):\n'
                             '    from kernel import _set_flag as set_flag\n'
                             '    set_flag(b["id"])\n',
                    ({"_set_flag"}, [], [("_route", "a writer", "_set_flag", 4)])),
                   ("a def named like a door, and a keyword labelled like one",
                    'class Store:\n'
                    '    def rename(self, sid, name):\n'
                    '        return self.edit(sid, rename=name)\n',
                    (set(), [], [])),
                   ("a parameter named like a door",
                    'def _edit(rename=None):\n'
                    '    return str(rename)\n',
                    (set(), [], [("_edit", "a door", "rename", 1), ("_edit", "a door", "rename", 2)])),
                   ("a docstring naming the store",
                    'def _retire(side):\n'
                    '    """Renames a session-flags.json.corrupt sidecar aside."""\n'
                    '    os.replace(side, side.with_name("retired"))\n',
                    (set(), [], [])),
                   ("a path function's call and a module-level name whose truth alone decides a test",
                    'FLAGS_PATH = jd.STATE / "session-flags.json"\n'
                    'def _flags_path():\n'
                    '    return FLAGS_PATH\n'
                    'def _gate(sid, out):\n'
                    '    if not (_flags_path() and FLAGS_PATH):\n'
                    '        return None\n'
                    '    while FLAGS_PATH or _flags_path():\n'
                    '        out.append(1 if _flags_path() else 0)\n'
                    '        break\n'
                    '    return sid\n',
                    (set(), [], [])),
                   ("a module-level name compared in a test",
                    'FLAGS_PATH = jd.STATE / "session-flags.json"\n'
                    'def _gate(p):\n'
                    '    if p == FLAGS_PATH:\n'
                    '        return None\n'
                    '    return p\n',
                    (set(), [], [("_gate", "a module-level name", "FLAGS_PATH", 3)])),
                   ("a path function's call handed to a call in a test",
                    'def _flags_path():\n'
                    '    return jd.STATE / "session-flags.json"\n'
                    'def _gate(sid):\n'
                    '    if _seen(_flags_path()):\n'
                    '        return None\n'
                    '    return sid\n',
                    (set(), [], [("_gate", "a path function", "_flags_path", 4)])),
                   ("a path function that also writes the path through unpacking",
                    'def _flags_path():\n'
                    '    base, p = jd.STATE, jd.STATE / "session-flags.json"\n'
                    '    p.write_text("{}")\n'
                    '    return jd.STATE / "session-flags.json"\n',
                    (set(), [], [("_flags_path", name, "session-flags.json", 2), ("_flags_path", name, "session-flags.json", 4)])),
                   ("a name bound in another outermost function",
                    'def _where():\n'
                    '    p = jd.STATE / "session-flags.json"\n'
                    '    log(p)\n'
                    'def _by_parameter(p, cur):\n'
                    '    p.write_text(cur)\n',
                    (set(), [], [("_where", name, "session-flags.json", 2)])),
                   ("a name bound in a function, written outside every function",
                    'def _where():\n'
                    '    p = jd.STATE / "session-flags.json"\n'
                    '    log(p)\n'
                    'p.write_text("{}")\n',
                    (set(), [], [("_where", name, "session-flags.json", 2)])),
                   ("a name bound in another method of the same class",
                    'class Store:\n'
                    '    def _where(self):\n'
                    '        p = jd.STATE / "session-flags.json"\n'
                    '        log(p)\n'
                    '    def _by_sibling_method(self, p, cur):\n'
                    '        p.write_text(cur)\n',
                    (set(), [], [("Store._where", name, "session-flags.json", 3)])),
                   ("a name bound in another outermost function through a global statement",
                    'def _init():\n'
                    '    global FLAGS_PATH\n'
                    '    FLAGS_PATH = jd.STATE / "session-flags.json"\n'
                    'def _by_global(cur):\n'
                    '    _atomic_write(FLAGS_PATH, cur)\n',
                    (set(), [], [("_init", name, "session-flags.json", 3)])),
                   ("shutil.copy",
                    'def _by_library(tmp):\n'
                    '    shutil.copy(tmp, jd.STATE / "session-flags.json")\n',
                    (set(), [], [("_by_library", name, "session-flags.json", 2)])),
                   ("a subprocess",
                    'def _by_subprocess(tmp):\n'
                    '    subprocess.run(["cp", tmp, str(jd.STATE / "session-flags.json")], check=True)\n',
                    (set(), [], [("_by_subprocess", name, "session-flags.json", 2)])),
                   ("a path handed to a helper that writes its parameter",
                    'def _save(p, cur):\n'
                    '    _atomic_write(p, cur)\n'
                    'def _by_argument(cur):\n'
                    '    _save(jd.STATE / "session-flags.json", cur)\n',
                    (set(), [], [("_by_argument", name, "session-flags.json", 4)])),
                   ("a door reached through getattr and a string",
                    'def _by_getattr(cur):\n'
                    '    getattr(jd.STATE / "session-flags.json", "write_text")(cur)\n',
                    (set(), [], [("_by_getattr", name, "session-flags.json", 2)])),
                   ("a name bound by unpacking into a tuple",
                    'def _by_unpacking(cur):\n'
                    '    base, p = jd.STATE, jd.STATE / "session-flags.json"\n'
                    '    p.write_text(cur)\n',
                    (set(), [], [("_by_unpacking", name, "session-flags.json", 2)])),
                   ("a name bound by a for loop's target",
                    'def _by_loop(cur):\n'
                    '    for p in (jd.STATE / "session-flags.json",):\n'
                    '        p.write_text(cur)\n',
                    (set(), [], [("_by_loop", name, "session-flags.json", 2)])),
                   ("a name bound by an assignment expression",
                    'def _by_walrus(cur):\n'
                    '    if (p := jd.STATE / "session-flags.json"):\n'
                    '        p.write_text(cur)\n',
                    (set(), [], [("_by_walrus", name, "session-flags.json", 2)])),
                   ("a name bound by a parameter's default",
                    'def _by_default(cur, p=jd.STATE / "session-flags.json"):\n'
                    '    p.write_text(cur)\n',
                    (set(), [], [("_by_default", name, "session-flags.json", 1)])),
                   ("a name bound by a comprehension's target",
                    'def _by_comprehension(cur):\n'
                    '    [p.write_text(cur) for p in (jd.STATE / "session-flags.json",)]\n',
                    (set(), [], [("_by_comprehension", name, "session-flags.json", 2)])),
                   ("a name bound by a with statement's as",
                    'def _by_with(cur):\n'
                    '    with _held(jd.STATE / "session-flags.json") as p:\n'
                    '        p.write_text(cur)\n',
                    (set(), [], [("_by_with", name, "session-flags.json", 2)])),
                   ("a name bound by an assignment to an attribute",
                    'def _by_attribute_target(cur):\n'
                    '    store.p = jd.STATE / "session-flags.json"\n'
                    '    store.p.write_text(cur)\n',
                    (set(), [], [("_by_attribute_target", name, "session-flags.json", 2)])),
                   ("a path held in an attribute and written in another method",
                    'class Store:\n'
                    '    def __init__(self):\n'
                    '        self.p = jd.STATE / "session-flags.json"\n'
                    '    def _by_attribute(self, cur):\n'
                    '        self.p.write_text(cur)\n',
                    (set(), [], [("Store.__init__", name, "session-flags.json", 3)])),
                   ("a path built by string concatenation",
                    'def _by_concatenation(cur):\n'
                    '    _atomic_write(jd.STATE / ("session-" + "flags.json"), cur)\n',
                    (set(), [], [])),
                   ("a path function writing its path through getattr and a string",
                    'def _flags_path():\n'
                    '    p = jd.STATE / "session-flags.json"\n'
                    '    getattr(p, "write_text")("{}")\n'
                    '    return p\n',
                    (set(), [], [])),
                   ("a path function handing its path to a helper that writes its parameter",
                    'def _flags_path():\n'
                    '    p = jd.STATE / "session-flags.json"\n'
                    '    _keep(p)\n'
                    '    return p\n'
                    'def _keep(q):\n'
                    '    q.write_text("{}")\n',
                    (set(), [], [])))
        for label, src, expected in planted:
            with self.subTest(net=label):
                self.assertEqual(census(src, refusals=True), expected,
                                 "THE NET (round 4 of fork PR #897, the reviewer's ruling on section G): %s. The census's "
                                 "docstring names this plant beside the rule it pins; the third element is what the net "
                                 "refuses, each as (function, clause, token, line)" % label)
        shutil_src = planted[[p[0] for p in planted].index("shutil.copy")][1]
        with self.subTest(net="an exemption row names a refused function"):
            self.assertEqual(census(shutil_src, exempt={"_by_library": "a planted reason"}), (set(), []),
                             "an exemption row lifts the net's refusal of the function it names")
            with self.assertRaises(AssertionError) as refusal:
                census(shutil_src)
            self.assertIn("_by_library mentions the store's name 'session-flags.json' at line 2", str(refusal.exception),
                          "with no row, the census raises, naming the function, the clause, the token and its line")
        with self.subTest(net="an exemption row that names no refused function"):
            with self.assertRaises(AssertionError) as stale:
                census(setter, exempt={"_set_flag": "a planted reason"})
            self.assertIn("THE NET'S EXEMPTION ROWS NAME ONLY WHAT IT REFUSES: ['_set_flag']", str(stale.exception),
                          "a row naming a function the net does not refuse raises, so the rows stay exact")

    @classmethod
    def setUpClass(cls):
        import threading
        from http.server import ThreadingHTTPServer
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), pm.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()

    def setUp(self):
        _reg(THREAD, threadOf=PARENT)
        self._saved = pm._kernel_sessions_checked
        rows = [{"id": PARENT, "name": "web"}, {"id": THREAD, "name": "web-comment-1", "thread": True, "parent": PARENT}]
        pm._kernel_sessions_checked = lambda threads=False: ([r for r in rows if threads or not r.get("thread")], True)
        pm.STATE.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        pm._kernel_sessions_checked = self._saved
        for f in (pm.SESSION_FLAGS, pm.SESSION_FLAGS.parent / "sdk" / (THREAD + ".json")):
            try:
                f.unlink()
            except OSError:
                pass

    def _send(self, frm_id, frm, to):
        import urllib.error
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:%d/send" % self.port, method="POST",
                                     data=json.dumps({"to": to, "from": frm, "from_id": frm_id, "body": "a note", "kind": "coordinate"}).encode("utf-8"),
                                     headers={"Content-Type": "application/json", "X-Romp-Token": pm.SERVE_TOKEN})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_the_threads_own_send_is_refused_until_broken_out(self):
        status, body = self._send(THREAD, "web-comment-1", "web")
        self.assertEqual(status, 403, body)
        self.assertTrue(body["error"].startswith("isolation:"), "the isolation refusal a peer treats as final")
        self.assertIn("COMMENT THREAD", body["error"]); self.assertIn("breaks it out", body["error"]); self.assertIn("Nothing was sent", body["error"])
        self.assertFalse((pm.MAILROOT / PARENT / "new").exists() and any((pm.MAILROOT / PARENT / "new").iterdir()), "nothing landed")
        _reg(THREAD)                                       # broken out: the reg has no threadOf
        status, body = self._send(THREAD, "web-2", "web")
        self.assertNotEqual(status, 403, "a promoted session sends like any other: %r" % (body,))

    def test_a_threads_send_to_a_peer_host_is_refused_before_the_relay_and_its_sid_is_in_no_roster(self):
        """Fork PR #897, round 3 (the reviewer's ruling on its refuters' narrowing of the comment-thread finding): the deadness
        mirror's roster is built from the presence producer, which reads the default listing (the 2026-08-22 rule: thread
        rows ride only when asked), so a live thread's sid is in no roster a peer's mirror holds, and a peer whose host
        vouches for absence would presume a thread that mailed it closed (rule 5). The road is closed here: a thread's own
        send is refused with 403 before resolve_recipient and any relay, so no thread's mail crosses a host; the one way
        through is `threadMail` at the literal True in session-flags.json. ONE road writes that key today: the kernel's
        WebSocket setSessionFlag arm (Handler._dispatch_ws), which accepts ANY flag name from an authenticated dashboard
        client, while POST /flag (_state_write_route) applies the _LANE_FLAGS whitelist and refuses it (no control of the
        UI sends the key; a hand edit of the file writes the same bytes). The consequence, in one sentence: a client that
        sets threadMail on a comment thread lets that thread's mail relay while every roster still omits its sid, so a far
        host's mirror can presume the live thread closed, a false rule 5 that a user reaches only by hand-crafting a
        WebSocket message (or by editing the file). The fix is a separate fix-tier PR that makes the WebSocket arm apply
        the same whitelist as POST /flag (the seventeenth commit said no route writes the key and the eighteenth named the
        arm; the reviewer's ruling of round 3 asked for this text and the set below).
        This pins the current truth as a set. The kernel's routes that write a session flag, derived from kernel/kernel.py
        by the census above (_flag_writing_routes, behind its net and NET_EXEMPT's rows), are exactly POST /flag and the
        WebSocket arm, so a new route fails the set pin, and a function the net refuses there fails it by name. Executed over the real handlers: the listing with thread rows has the thread and the roster omits it; a
        send to a session on a peer host, a relay destination for any session whose mail is on, is refused and nothing is
        parked in the peer's outbox; POST /flag refuses the key and the send is still refused; the key written through
        the kernel's real WebSocket arm, into the file the bus reads, lets the same send be parked (the disclosed road,
        whose shape, if thread mail is ever re-enabled, is a separate exchange field carrying the mirror-relevant thread
        sids, never the roster with thread rows). The fix PR flips exactly the WebSocket half: its pin here turns red and
        moves with the fix, never silently. A gate that let a thread's send through fails the 403 pin here."""
        far_host, far = "TESTHOST-far", "88888888-9999-aaaa-bbbb-cccccccccccc"
        self.assertTrue(pm.peers_on(), "peer mode: a name on a peer host is a relay destination")
        pm.PEER_STATE[far_host] = {"presence": [{"id": far, "name": "far"}], "epoch": 1, "holds": [],
                                   "seenAt": int(pm.time.time()), "presenceAnswered": True}
        pm.PEERS[far_host] = {"port": 50002, "up": True, "at": 0, "token": "", "trust": "trusted"}   # up: the park needs no redial
        self.addCleanup(pm.PEER_STATE.pop, far_host, None); self.addCleanup(pm.PEERS.pop, far_host, None)
        outbox = pm.OUTBOX / far_host
        shutil.rmtree(outbox, ignore_errors=True); self.addCleanup(shutil.rmtree, outbox, ignore_errors=True)
        self.assertIn(THREAD, [a["id"] for a in pm.local_agents_checked(threads=True)[0]], "the listing with thread rows has the thread")
        roster, answered = pm.presence_payload("")
        self.assertEqual(([a.get("id") for a in roster], answered), ([PARENT, far], True),
                         "THE ROSTER OMITS COMMENT THREADS: the presence producer reads the default listing, so the thread's sid is in "
                         "no roster a peer's mirror holds (its parent and the gossiped far session are)")
        self.assertEqual(pm.resolve_recipient("far", PARENT)["kind"], "relay", "the far session is a relay destination")
        status, body = self._send(THREAD, "web-comment-1", "far")
        self.assertEqual(status, 403, body)
        self.assertIn("COMMENT THREAD", body["error"]); self.assertIn("Nothing was sent", body["error"])
        self.assertFalse(outbox.exists() and any(outbox.iterdir()),
                         "REFUSED BEFORE THE RELAY: nothing is parked for the peer, so the thread's sid never reaches a far host as a "
                         "sender (a gate that opened parks the message here)")
        with open(self.KERNEL_SRC, encoding="utf-8") as f:
            writers, refs = self._flag_writing_routes(f.read(), exempt=self.NET_EXEMPT)
        self.assertEqual(writers, self.FLAG_WRITERS, "the kernel functions that write session-flags.json")
        self.assertEqual({(where, selectors[0] if selectors else "") for where, selectors, _ in refs}, self.FLAG_ROUTES,
                         "THE ROUTES THAT WRITE A SESSION FLAG, as a set: POST /flag and the WebSocket setSessionFlag arm, both "
                         "driven below through the real handlers (a new route fails here: drive it below and say what it does "
                         "with threadMail)")
        self.assertEqual(refs, [("Handler._dispatch_ws", ("setSessionFlag",), "_set_session_flag"),
                                ("Handler._dispatch_ws", ("setSessionFlag", "notify"), "_set_notify_session"),
                                ("_state_write_route", ("/flag",), "_set_session_flag"),
                                ("_state_write_route", ("/flag", "notify"), "_set_notify_session")],
                         "every mention of a flag writer in the kernel: the two routes' four calls and nothing else")
        saved_state = km.jd.STATE                             # the kernel writes the flags file the bus reads: one root, as in
        km.jd._rebind_state(pm.SESSION_FLAGS.parent)          # production (the kernel's STATE is the bus's STATE.parent)
        self.addCleanup(km.jd._rebind_state, saved_state)
        km._flags_cache.clear(); self.addCleanup(km._flags_cache.clear)
        dirty = km._mark_views_dirty
        km._mark_views_dirty = lambda: None                   # the pusher's wake is not under test
        self.addCleanup(setattr, km, "_mark_views_dirty", dirty)
        pm.SESSION_FLAGS.unlink(missing_ok=True)              # no flags yet: what the file carries below is the kernel's write alone
        code, resp = km._state_write_route("/flag", {"id": THREAD, "flag": "threadMail", "value": True})
        self.assertEqual((code, resp.get("ok")), (400, False), resp)
        self.assertIn('"threadMail"', resp.get("error", ""), "POST /flag holds the name to _LANE_FLAGS and refuses the key")
        self.assertFalse(pm.SESSION_FLAGS.exists(), "the refused route wrote nothing")
        status, body = self._send(THREAD, "web-comment-1", "far")
        self.assertEqual(status, 403, "the route refused the key, so the gate is still closed: %r" % (body,))
        sent = []
        client = {"app": "timeline", "wid": "w1", "alive": True, "send": lambda raw: sent.append(json.loads(raw))}
        km.Handler._dispatch_ws(None, {"type": "setSessionFlag", "id": THREAD, "flag": "threadMail", "value": True}, client)
        flags = json.loads(pm.SESSION_FLAGS.read_text()) if pm.SESSION_FLAGS.exists() else None
        self.assertEqual((sent, flags), ([], {THREAD: {"threadMail": True}}),
                         "THE KERNEL'S WEBSOCKET ARM writes the key, unrefused, into the file the bus reads: it applies no whitelist "
                         "(a hand edit of the file writes the same bytes; the separate fix-tier PR makes the arm apply _LANE_FLAGS, "
                         "which writes nothing, so this pin turns red and moves with that fix)")
        status, body = self._send(THREAD, "web-comment-1", "far")
        self.assertEqual(status, 200, body)
        self.assertTrue(outbox.exists() and any(outbox.iterdir()),
                        "with the key written through the kernel's WebSocket arm the same send is parked for the peer while the "
                        "roster still omits the thread: the disclosed road, open to a client message")


class ThreadMailOffFollowUp(unittest.TestCase):
    """The review's lows on the thread rule: a reg that exists but cannot be read fails CLOSED; the CLI judges the
    caller's own identity before a --from label substitutes a synthetic one; a sender's stuck-mail line for a thread
    says HELD, never resend; an inbound cross-host bounce names the thread refusal."""

    def tearDown(self):
        for f in (pm.SESSION_FLAGS, pm.SESSION_FLAGS.parent / "sdk" / (THREAD + ".json"), pm.SESSION_FLAGS.parent / "sdk" / (SENDER + ".json")):
            try:
                f.unlink()
            except OSError:
                pass

    def test_an_unreadable_reg_fails_closed_and_no_reg_stays_open(self):
        d = pm.SESSION_FLAGS.parent / "sdk"; d.mkdir(parents=True, exist_ok=True)
        (d / (THREAD + ".json")).write_text("{not json")
        self.assertEqual(pm._thread_of(THREAD), pm.THREAD_REG_UNREADABLE)
        self.assertEqual(pm._mail_off_why(THREAD), "unreadable", "a record that exists but cannot be read: closed, under its own reason")
        self.assertTrue(pm._postal_off(THREAD))
        (d / (THREAD + ".json")).write_text(json.dumps(["not", "a", "dict"]))
        self.assertEqual(pm._mail_off_why(THREAD), "unreadable", "…whatever shape the corruption takes")
        (d / (THREAD + ".json")).unlink()
        self.assertEqual(pm._thread_of(THREAD), ""); self.assertEqual(pm._mail_off_why(THREAD), "", "no reg at all: an ordinary session")

    def test_the_cli_judges_the_callers_own_identity_before_any_from_label(self):
        _reg(THREAD, threadOf=PARENT)
        import io
        saved = (pm._self_identity, pm.ensure, pm._http)
        calls = []
        try:
            pm._self_identity = lambda: (THREAD, "web-comment-1")
            pm.ensure = lambda: True
            pm._http = lambda *a, **k: calls.append(a) or {}
            err = io.StringIO(); real = sys.stderr; sys.stderr = err
            try:
                rc1 = pm.cli_send(["web", "a note"])
                rc2 = pm.cli_send(["--from", "nightly", "web", "a note"])
            finally:
                sys.stderr = real
            self.assertEqual((rc1, rc2), (1, 1)); self.assertEqual(calls, [], "nothing reached the bus")
            self.assertEqual(err.getvalue().count("COMMENT THREAD"), 2); self.assertIn("breaks it out", err.getvalue())
            _reg(THREAD)                                   # broken out: the same calls go through to the bus
            rc3 = pm.cli_send(["--from", "nightly", "web", "a note"])
            self.assertEqual(rc3, 0); self.assertEqual(len(calls), 1); self.assertEqual(calls[0][2]["from_id"], "ext:nightly")
        finally:
            pm._self_identity, pm.ensure, pm._http = saved

    def test_a_directory_the_bus_cannot_stat_fails_closed_without_raising(self):
        # the review's medium: the stat sat outside the try, so EACCES on sdk/ raised out of every reader
        d = pm.SESSION_FLAGS.parent / "sdk"; d.mkdir(parents=True, exist_ok=True)
        (d / (THREAD + ".json")).write_text(json.dumps({"sid": THREAD, "threadOf": PARENT}))
        if os.geteuid() == 0:
            self.skipTest("root reads through chmod 000")
        os.chmod(d, 0)
        try:
            self.assertEqual(pm._thread_of(THREAD), pm.THREAD_REG_UNREADABLE)
            self.assertEqual(pm._mail_off_why(THREAD), "unreadable")
            self.assertEqual(pm.read_box(THREAD, consume=True), [], "the receive gate answers empty, it does not raise")
            self.assertTrue(pm._postal_off(THREAD))
        finally:
            os.chmod(d, 0o755)

    def test_an_unreadable_record_gets_its_own_words_never_the_thread_diagnosis(self):
        d = pm.SESSION_FLAGS.parent / "sdk"; d.mkdir(parents=True, exist_ok=True)
        (d / (SENDER + ".json")).write_text("{corrupt")
        self.assertNotIn("COMMENT THREAD", pm.UNREADABLE_REG_SENDER); self.assertIn("cannot be read", pm.UNREADABLE_REG_SENDER)
        held = pm._stuck_warn_text({"name": "api"}, SENDER, "hello")
        self.assertTrue(held.startswith("↩ HELD")); self.assertIn("cannot read", held); self.assertNotIn("COMMENT THREAD", held)
        self.assertIn("cannot read", pm._isolated_bounce_why([{"id": SENDER, "name": "api"}], "api"))
        import io
        saved = (pm._self_identity, pm.ensure, pm._http)
        try:
            pm._self_identity = lambda: (SENDER, "api"); pm.ensure = lambda: True; pm._http = lambda *a, **k: {}
            err = io.StringIO(); real = sys.stderr; sys.stderr = err
            try:
                rc = pm.cli_send(["web", "a note"])
            finally:
                sys.stderr = real
            self.assertEqual(rc, 1); self.assertIn("cannot be read", err.getvalue()); self.assertNotIn("COMMENT THREAD", err.getvalue())
        finally:
            pm._self_identity, pm.ensure, pm._http = saved

    def test_an_inbound_relay_to_a_thread_bounces_through_relay_in_itself(self):
        # the review's medium: _relay_in listed the DEFAULT rows (no threads), so the thread arm never ran and the relay retried forever
        _reg(THREAD, threadOf=PARENT)
        rows = [{"id": PARENT, "name": "web"}, {"id": THREAD, "name": "web-comment-1", "thread": True, "parent": PARENT}]
        saved = pm._kernel_sessions_checked
        pm._kernel_sessions_checked = lambda threads=False: ([r for r in rows if threads or not r.get("thread")], True)
        try:
            verdict, bounce = pm._relay_in("TESTHOST", {"mid": "relay-thread-0001", "to": "web-comment-1", "frm": "api", "frm_id": "id-api", "body": "a note", "kind": "coordinate"})
            self.assertEqual(verdict, "bounce", (verdict, bounce))
            self.assertIn("COMMENT THREAD", bounce["why"]); self.assertIn("breaks it out", bounce["why"])
        finally:
            pm._kernel_sessions_checked = saved

    def test_the_stuck_mail_line_says_held_for_a_thread_and_resend_for_a_session(self):
        _reg(THREAD, threadOf=PARENT)
        held = pm._stuck_warn_text({"name": "web-comment-1"}, THREAD, "please  look\nat this")
        self.assertTrue(held.startswith("↩ HELD")); self.assertIn("breaks it out", held); self.assertIn("Nothing to resend", held)
        self.assertIn("Original: please look at this", held)
        stuck = pm._stuck_warn_text({"name": "api"}, SENDER, "hello")
        self.assertTrue(stuck.startswith("↩ STILL UNDELIVERED")); self.assertIn("resend", stuck)

    def test_an_inbound_bounce_names_the_thread_refusal(self):
        _reg(THREAD, threadOf=PARENT)
        why = pm._isolated_bounce_why([{"id": THREAD, "name": "web-comment-1"}], "web-comment-1")
        self.assertIn("COMMENT THREAD", why); self.assertIn("breaks it out", why)
        _flags({SENDER: {"postalServiceOff": True}})
        self.assertEqual(pm._isolated_bounce_why([{"id": SENDER, "name": "api"}], "api"), "recipient 'api' has its mailbox off (postal isolation)")


class CliJudgesIsolationToo(unittest.TestCase):
    """`romp mail send --from <label>` judged the caller for the thread and unreadable doors only; a mailbox the user
    toggled OFF fell through (the review's low). Every closed door now stops the CLI before any label applies."""

    def tearDown(self):
        try:
            pm.SESSION_FLAGS.unlink()
        except OSError:
            pass

    def test_an_isolated_caller_is_stopped_with_the_isolation_words_with_and_without_from(self):
        _flags({SENDER: {"postalServiceOff": True}})
        import io
        saved = (pm._self_identity, pm.ensure, pm._http)
        calls = []
        try:
            pm._self_identity = lambda: (SENDER, "api"); pm.ensure = lambda: True; pm._http = lambda *a, **k: calls.append(a) or {}
            err = io.StringIO(); real = sys.stderr; sys.stderr = err
            try:
                rc1 = pm.cli_send(["web", "a note"]); rc2 = pm.cli_send(["--from", "nightly", "web", "a note"])
            finally:
                sys.stderr = real
            self.assertEqual((rc1, rc2), (1, 1)); self.assertEqual(calls, [], "nothing reached the bus")
            self.assertEqual(err.getvalue().count("YOUR OWN mailbox is OFF"), 2); self.assertNotIn("COMMENT THREAD", err.getvalue())
            self.assertEqual(pm.ISOLATION_SENDER, pm.ISOLATION_SENDER.strip()); self.assertIn("isolation:", pm.ISOLATION_SENDER)
        finally:
            pm._self_identity, pm.ensure, pm._http = saved

if __name__ == "__main__":
    unittest.main(verbosity=2)
