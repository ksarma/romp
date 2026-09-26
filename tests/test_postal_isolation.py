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
    # in kernel/kernel.py, with the reason the refusal is false and each refusal it lifts there, as (clause, token, what the
    # value is handed to after its one hop), at its count. A row lifts only what it lists: a mention beyond it, or handed
    # elsewhere, is refused, and an entry the net does not refuse at its count raises.
    NET_EXEMPT = {
        "_state_quarantine": ("moves an unparseable state file aside to a .corrupt name, and compares its name with the "
                              "store's to word its log line; it sets no flag",
                              {("the store's name", "session-flags.json", "Compare"): 2}),
        "_edit_tag": ("its parameter rename holds a tag's new name, compared, and turned into a string that is sliced "
                      "(Subscript); it holds no door call",
                      {("a door", "rename", "arg"): 1, ("a door", "rename", "Compare"): 1, ("a door", "rename", "Subscript"): 1}),
        "_session_flags_proved": ("the mutation snapshot's reader: hands the store's path, as a string, to the display cache's "
                                  "lookup (.get), and hands it to _read_state_json (which moves torn bytes aside), the "
                                  "quarantine check, the refusal it raises and its exit text; it writes no flag",
                                  {("a name bound to the path", "p", ".get"): 1,
                                   ("a name bound to the path", "p", "_read_state_json"): 1,
                                   ("a name bound to the path", "p", "_flags_quarantined"): 1,
                                   ("a name bound to the path", "p", "_StateUnreadable"): 1,
                                   ("a name bound to the path", "p", "_flags_exit_text"): 1}),
        "_session_flags": ("the display reader: hands the store's path, as a string, to the display cache's lookup (.get) and "
                           "store (Subscript), and hands it to its stat, the quarantine check, the fault notices "
                           "(_StateUnreadable, _clear_state_fault), _read_state_json (which moves torn bytes aside) and "
                           "_retire_flags_quarantine, which renames the quarantine sidecars beside the store; it writes no flag",
                           {("a name bound to the path", "p", ".get"): 1, ("a name bound to the path", "p", "Subscript"): 1,
                            ("a name bound to the path", "p", ".stat"): 1,
                            ("a name bound to the path", "p", "_flags_quarantined"): 1,
                            ("a name bound to the path", "p", "_StateUnreadable"): 3,
                            ("a name bound to the path", "p", "_clear_state_fault"): 3,
                            ("a name bound to the path", "p", "_read_state_json"): 1,
                            ("a name bound to the path", "p", "_retire_flags_quarantine"): 1}),
        "_thread_rows_key": ("stats the store for the thread rows' cache key",
                             {("the store's name", "session-flags.json", ".stat"): 1}),
        "_flags_unknown_cold": ("binds the store's path, as a string, to p (Assign), and looks p up among the noted read "
                                "faults (Compare) and in the display cache (.get)",
                                {("the store's name", "session-flags.json", "Assign"): 1,
                                 ("a name bound to the path", "p", "Compare"): 1, ("a name bound to the path", "p", ".get"): 1}),
        "_chat_sig_shared": ("hands the store's path to _chat_ident, which stats it for the chat-build signature",
                             {("the store's name", "session-flags.json", "_chat_ident"): 1}),
        "_dead_lane_key": ("hands the store's path to _stat_key, which stats it for a dead lane's cache key",
                           {("the store's name", "session-flags.json", "_stat_key"): 1}),
        "_fleet_view_sig": ("stats the store among the files whose change busts the view cache: the loop (For) unpacks each "
                            "path and its key into p, which it stats, and k, the signature's key",
                            {("the store's name", "session-flags.json", "For"): 1,
                             ("a name bound to the path", "p", ".stat"): 1, ("a name bound to the path", "k", "Subscript"): 1}),
    }

    @staticmethod
    def _flag_writing_routes(source, exempt=None, refusals=False):
        """The kernel's routes that write a session flag, DERIVED from the source, behind a NET that refuses by name
        each mention of a derived name that the derivation does not follow (fork PR #897, each under the reviewer's
        ruling on section G: derived in round 3, to a fixpoint at round 4's thirty-sixth commit, the net at its
        forty-first, the net per mention at its forty-second, its folds, rows and limit at its forty-third, its one
        hop, the class body and the folds restored at its forty-fourth). Returns (writers, references), and raises,
        naming each mention the net refuses by its function, clause, token, line and what its value is handed to,
        unless a row of `exempt` lifts it; with refusals=True it returns the refused mentions as a third element
        instead, each as (function, clause, token, line). Each rule below names its plant, a subtest of
        test_the_flag_route_census_finds_a_new_route_and_a_writer_of_each_shape (the derivation) or of
        test_the_net_refuses_what_the_derivation_leaves_unclassified (the net), by its label.
        THE DERIVATION. A WRITER is a function holding a call of a door one of whose arguments, positional or keyword,
        or whose receiver, carries the flags path ("the path in a door's keyword argument", "open called as a method"),
        named "<module>" for a call outside every function, a class body included ("each writer shape", "a door call in
        a class body is the writer <module>"). The doors: a call named _write_state_json, _atomic_write, open, replace,
        rename, write_text or write_bytes, by bare name or as a method whatever its receiver (each door planted in both
        forms, this list asserted equal to the list planted). An expression CARRIES the path when it is the constant
        "session-flags.json", a name bound to the path or a call, by bare name or as a method, of a PATH FUNCTION, or a
        division either of whose operands carries ("each writer shape"); a path inside any other expression is not
        carried, and the net refuses it ("a path in a door's argument through str()", "a reader of the store"). A path
        function is a function one of whose own return statements returns an expression that carries the path ("a path
        function called as a method", "a path function with a return that does not carry the path beside one that does",
        "a path function returning a name bound in it"). A name is BOUND to the path by an assignment, plain, annotated
        or augmented, to a plain name whose value carries the path, in any order ("a module-level name bound by an
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
        variable, an attribute, the name of a def, a class or a parameter, a keyword's label, an import, a global or
        nonlocal statement's names; checked against Python's tokenizer, so a name token the scan does not read raises)
        and every string it holds (a constant, bytes, a piece of an f-string), keyed on the derivation's own sets and on
        the nodes it reads, so the two agree by construction. Seven clauses, each
        refusing a mention (its function by dotted name, "<module>" outside every function, with the token, its line and
        what its value is handed to): THE STORE'S NAME, a string holding
        "session-flags.json" anywhere in it ("an f-string holding the store's name in a longer piece", "a string joined
        to the store's name", "the store's name in bytes"); A MODULE-LEVEL NAME of the fixpoint's, as a name or as a
        word of a string ("a module-level name handed on by unpacking", "a module-level name reached through
        globals()"); A PATH FUNCTION of the fixpoint's, the same two ways ("a path function's call handed on by
        unpacking", "a path function reached through getattr and a string", "a path function called in a string handed
        to eval", "a path function called in a bytes string handed to eval"); A NAME BOUND TO THE PATH in a function, in
        the functions of its outermost function, as any name the scan reads there, an attribute included, or as a word
        of a string ("a name bound to the path handed to a helper", "a name bound to the path in a class body, read as
        the class's attribute", "a class's attribute bound to the path, read through self in a method", "a name bound
        to the path reached through locals() and a string"), and a name a refused mention's value lands in (THE ONE
        HOP, below); A
        DOOR's name, as a name alone, since the kernel uses open, replace and rename as words ("a door handed on as a
        value", "a door imported under another name"); A WRITER's name, as a name or as a word of a string ("a writer
        imported under another name in a route", "a writer reached through getattr and a string in a route"); and A
        METHOD THE LANGUAGE CALLS UNNAMED, a division's (__truediv__, __rtruediv__ or __itruediv__, since the derivation
        follows a division) or a path function's whose name begins and ends with two underscores, as a name, a def's and
        a name being bound included, or as a word of a string ("a class defining a division", "a class defining a
        division by assignment", "a path function the language calls unnamed").
        THE ONE HOP: the net follows a keyed value exactly ONE hop, to its consumer or to the name it lands in. A value
        that leaves the function through a return, a container, an attribute or a store, and is read back elsewhere, is
        inside the stated limit, with witnesses. The hop climbs from the mention (from a path function's call, for its
        name) each step that hands the value on as it is: a division, a keyword argument, a conversion (a call named str,
        bytes, fspath, fsencode, fsdecode, Path, PurePath, abspath, realpath, normpath, expanduser, resolve, absolute or
        as_posix, by bare name or as a method, the value an argument or the receiver; each planted in the three forms,
        this list asserted equal to the list planted), a tuple, a list, a set or a dict display, a starred item, a
        comprehension's element, an operand of and or or, a conditional expression's branch, and an assignment
        expression, whose target the value lands in on its way ("a refused mention's value lands in a name through each
        step"). Its CONSUMER is the node holding it at the end of the hop (the rows' key, below). The names it LANDS IN
        are the names that node binds: among the targets of an assignment, plain, chained, annotated or augmented,
        unpacked, a starred or a list target included, or of a for loop or a comprehension, and the parameter whose
        default it is; an attribute or a subscript is none, holding the value outside the function's names ("a lifted
        mention's value landing in a name, written through it", "a refused mention's value lands in a name by each kind
        of target", "a name bound by unpacking into a tuple", "a name bound by a for loop's target", "a name bound by an
        assignment expression", "a name bound by a parameter's default", "a name bound by a comprehension's target"). A
        name the value of a mention the net refuses, before any row lifts it, lands in is keyed as a name bound to the
        path throughout the outermost function around it ("a name a value landed in, read by a nested function"), a
        name the module binds everywhere ("a name the module binds, a value landed in, read in a function"), and its own
        refused uses land in turn, to a fixpoint ("a use of a name a value landed in, landing in another").
        A mention is FOLDED, and counts for no clause, when it is the name of a def or a class, or a keyword's label ("a
        def named like a door, and a keyword labelled like one"; a parameter's name is not: "a parameter named like a
        door"), except the name of a def with a decorator, which is handed the function: that name is keyed, but for a
        door's ("a writer's own def, decorated", "a path function's own def, decorated"); a door's name, when it names a call
        the derivation reads as a door ("each writer shape"); a string, when it is a whole statement, as a docstring is
        (a witness of the limit: "a docstring holding the store's name, read back through __doc__ and inspect.getdoc");
        a path function's call, a module-level name or a bound name, when its truth alone decides the test of an
        if, a while or a conditional expression, through and, or and not (not as a conditional expression's body, nor as
        an operand of and or or whose value is handed on: "a name bound to the path in a conditional expression's body,
        handed to a helper", "a name bound to the path under an and, handed to a helper"), or when it is an operand of a
        comparison whose operators are all is or is not ("a path function's call and a module-level name whose truth
        alone decides a test", "a name bound to the
        path compared by identity, and one whose truth alone decides a test"; a comparison by == hands the value on, and
        so does a call: "a module-level name compared in a test", "a path function's call handed to a call in a test");
        a name being bound or deleted ("a path function returning a name bound in it"), and a parameter's name for the
        bound clause ("a name bound by a parameter's default"); and a nonlocal statement's name
        that the derivation counts in the function around it ("a write through a name a nested function binds through a
        nonlocal statement"; a global statement's is not: "a name bound in another outermost function through a global
        statement", "a nested function's global statement naming a name its enclosing function binds").
        The derivation CLASSIFIES a mention, one by one: a writer's name where it records a reference, a name or an
        attribute ("a mention of a writer that is not a call"; a string or an import is none, a reference beside it in
        the same function notwithstanding: "a writer's name as a string beside a reference in a route", "a writer
        imported under another name beside a reference in a route"); every other mention in a writer but a door's name;
        and, in a function holding no door call it reads (one that does is refused whole: "a path function that also
        writes the path through unpacking"), a mention it reads (the constant, a bound name, a path function's call)
        whose value reaches, through divisions alone, the value of one of the function's own return statements, the
        function being a path function, or of an assignment all of whose targets are names it binds ("a path function
        returning a name bound in it"), outside a class body: a binding in a class body, at any depth of it, it does
        not follow, so the mention there is refused where it stands ("a name bound to the path in a class body, read
        as the class's attribute", "a class's attribute bound to the path, the class returned and read in another
        function", "a class's attribute bound to the path inside an if in its body"). Handed anywhere else, the
        mention is refused: to a helper ("a name bound to the path handed to a helper", "a path function handing its
        path to a helper that writes its parameter", "a route returning a path function's call that hands the path to
        a helper"), to getattr ("a path function writing its path through getattr and a string"), or on from a binding
        whose name the derivation reads nowhere else ("a name bound in another outermost function", "a name bound in a
        function, written outside every function", "a name bound in another method of the same class"). A door's name
        it does not read as a call, and a method the language calls unnamed, it classifies nowhere ("a writer that
        also hands a door on as a value").
        THE ROWS. A mention the net refuses on the real kernel.py is lifted by a row of NET_EXEMPT: the function, the
        reason the refusal is false, and each refusal it lifts there as (clause, token, what the value is handed to), at
        its count. What a value is handed to is its consumer, read at the end of its one hop: the function a call names,
        as .name for a method, or Call for a function with no name; the attribute read on it, as .name; or else the kind
        of node holding it (Compare, Subscript, Assign, For, Return); and for the name of a def, a parameter, an import
        or a global statement, its own kind (the real kernel.py's rows, and the plants of "a row lifts a refused
        mention"); so a lifted str() handed on to another call no longer matches its row ("a lifted mention handed on
        through a conversion to another call is refused"), and an edit that keeps each consumer keeps its row ("a lifted
        mention edited with its consumer unchanged stays lifted", "a use of a landed name by the consumer its row lists
        stays lifted"). A row lifts only its refusals, each at its count; one beyond its
        count, or one the row does not list, the same clause and token handed to something else among them, is refused
        at every line of it, the function's row notwithstanding ("a mention beyond its row is refused", "a lifted
        mention handed elsewhere is refused"); a refusal the net makes fewer times than its row lists raises, so a lifted
        mention edited to hand the path elsewhere raises, as does a row that is not a reason and its refusals so keyed
        ("a row entry the net refuses fewer times"); and when the function has become a writer, the entry being of a
        clause the writer rule classifies, the message says so and names the writers ("a row of a function that has
        become a writer").
        What the derivation does not see, each planted, asserted not found and refused: shutil.copy, a subprocess, a
        path handed to a helper that writes its parameter, a door reached through getattr and a string, and a name bound
        by unpacking into a tuple, by a for loop's target, by an assignment expression, by a parameter's default, by a
        comprehension's target, by a with statement's as, by an assignment to an attribute, by an assignment to a name
        and to an attribute at once ("a path bound to a name and to an attribute in one assignment"), in an attribute
        and written in another method, or through a global statement.
        THE NET'S LIMIT, with its witnesses asserted neither found nor refused: the net reads the text of
        kernel/kernel.py alone, and the net follows a keyed value exactly ONE hop, to its consumer or to the name it
        lands in. A value that leaves the function through a return, a container, an attribute or a store, and is read
        back elsewhere, is inside the stated limit, with witnesses. Those witnesses, each source's refusal lifted by a
        row as on the real kernel.py: "a path returned as a string and written by the caller", "a path appended to a
        module-level list and written from it", "a path held in an attribute as a string and written in another
        method" and "a path stored as a cache's key and read back elsewhere". Inside it too, a path or a name reached
        at run time rather than written: a path built at run time, so that no string holds the store's name and no
        derived name carries it ("a path built by string concatenation"); a local read back by reflection without its
        name, a caller's through its frame or a function's own through locals() ("a caller's local read through its
        frame", "a local read back through locals() without its name"); a name read back at run time through
        reflection (a docstring through __doc__ or inspect, a def's or class's __name__, a keyword label made a key)
        ("a docstring holding the store's name, read back through __doc__ and inspect.getdoc", "the store's name cut
        from a docstring's words, read back through __doc__", "a def named like a writer, read back through __name__",
        "a class named like a writer, read back through __name__", "a def named like a path function that is not one",
        "a keyword labelled like a writer, read back as a key", "a keyword labelled like a name bound to the path,
        read back through eval", "a writer picked by its parameters' names through __code__"); and a path or a writer
        defined in a module the kernel loads, as judge.py is loaded as jd ("a writer defined in a module the kernel
        loads")."""
        import ast
        import io
        import keyword
        import re
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

        def reads(n, names):                           # the one node carries() reads as the path (the net reads it too)
            return (isinstance(n, ast.Constant) and n.value == flags or isinstance(n, ast.Name) and n.id in names
                    or isinstance(n, ast.Call) and (getattr(n.func, "id", None) or getattr(n.func, "attr", None)) in path_funcs)

        def carries(expr, names):                      # the expression's value is the path: a node reads() reads, or a division
            return reads(expr, names) or (isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div)   # either operand of
                                          and (carries(expr.left, names) or carries(expr.right, names)))  # which carries

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
        refs, ref_nodes = [], set()                    # the references, and the nodes the net reads as one
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
            ref_nodes.add(node)

        # THE NET, keyed on the derivation's own sets and on the nodes it reads (the docstring's second part)
        def deciding(node):                            # its truth alone decides the test of an if, a while or a conditional
            while (isinstance(parent.get(node), ast.BoolOp)                        # expression, through and, or and not
                   or isinstance(parent.get(node), ast.UnaryOp) and isinstance(parent[node].op, ast.Not)):
                node = parent[node]
            return isinstance(parent.get(node), (ast.If, ast.While, ast.IfExp)) and parent[node].test is node

        def identity(node):                            # an operand of a comparison whose operators are all is or is not
            return isinstance(parent.get(node), ast.Compare) and all(isinstance(o, (ast.Is, ast.IsNot)) for o in parent[node].ops)

        def folded(clause, node, field, key):
            if clause == unnamed:
                return False                           # folded nowhere, a def's name included
            if isinstance(node, defs + (ast.ClassDef,)) and field == "name" or isinstance(node, ast.keyword):
                return clause == "a door" or not (isinstance(node, defs) and node.decorator_list)   # the name of a def or a
                #                                        class, or a keyword's label; a decorated def's is handed to its decorator
            call = parent[node] if isinstance(parent.get(node), ast.Call) and parent[node].func is node else None
            if clause == "a door":
                return call is not None and door_call(call)
            value = call if clause == "a path function" else node if isinstance(node, ast.Name) else None
            if value is not None and (deciding(value) or identity(value)):
                return True                            # its truth alone decides a test, or an identity comparison reads it
            if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load) or isinstance(node, ast.arg) and clause == bound:
                return True                            # a name being bound or deleted, and a parameter's for the bound clause
            if isinstance(node, ast.Nonlocal):         # a binding the derivation counts in the function around this one
                outer = function_of(function_of(node))
                return outer is not None and key in names_in(outer)
            return False

        def used(clause, node, fn):                    # the derivation follows the mention: it reads the node, and the value
            n = parent.get(node) if clause == "a path function" else node          # it carries through divisions alone
            if clause == "a path function" and not (isinstance(n, ast.Call) and n.func is node) or not reads(n, names_in(fn)):
                return False
            while isinstance(parent.get(n), ast.BinOp) and isinstance(parent[n].op, ast.Div):
                n = parent[n]
            stmt = parent.get(n)
            if isinstance(stmt, ast.Return) and stmt.value is n:
                return fn is not None and fn.name in path_funcs                    # the value that makes fn a path function
            if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and stmt.value is n:
                return (not isinstance(next(a for a in up(stmt) if isinstance(a, defs + (ast.ClassDef, ast.Module))), ast.ClassDef)
                        and all(isinstance(t, ast.Name) and t.id in names_in(fn)   # a binding of names the derivation binds,
                                for t in (stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target])))   # not in a class body
            return False

        bound, unnamed = "a name bound to the path", "a method the language calls unnamed"
        keyed = {"a module-level name": module_names, "a path function": path_funcs, "a door": set(doors), "a writer": writers,
                 unnamed: {"__truediv__", "__rtruediv__", "__itruediv__"} | {f for f in path_funcs if f[:2] == f[-2:] == "__"}}
        local_names = set().union(*(names_in(fn) for fn in functions)) - module_names   # a name bound in some function
        mentions, scanned, spots = [], Counter(), {}   # (function, clause, key, line, node) unfolded; every name the scan reads;
        for node in ast.walk(tree):                    # and where each name and each word of a string stands, as (node, field, line)
            line = getattr(node, "lineno", None) or next((n.lineno for n in up(node) if getattr(n, "lineno", None)), 0)
            if isinstance(node, ast.Constant):
                if isinstance(parent.get(node), ast.Expr):
                    continue                           # a whole statement, as a docstring is
                v = node.value
                if isinstance(v, str) and flags in v or isinstance(v, bytes) and flags.encode() in v:
                    mentions.append((function_of(node), "the store's name", flags, line, node))
                words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", v if isinstance(v, str) else v.decode("latin-1")
                                   if isinstance(v, bytes) else "")                    # a name reached through a string
                mentions += [(function_of(node), clause, w, line, node) for w in words
                             for clause in ("a module-level name", "a path function", "a writer", unnamed) if w in keyed[clause]]
                for w in words:
                    spots.setdefault(w, []).append((node, None, line))
                continue
            for field, value in ast.iter_fields(node):
                for word in [value] if isinstance(value, str) else value if isinstance(value, list) else ():
                    for key in word.split(".") if isinstance(word, str) else ():
                        scanned[key] += 1
                        mentions += [(function_of(node), clause, key, line, node) for clause, keys in keyed.items()
                                     if key in keys and not folded(clause, node, field, key)]
                        spots.setdefault(key, []).append((node, field, line))
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

        def classified(fn, clause, node):              # the derivation accounts for this one mention
            if clause in ("a door", unnamed):
                return False                           # a door's name it does not read as a call, and a method called unnamed
            if clause == "a writer":
                return node in ref_nodes               # a reference it records; a string, an import or a parameter it does not
            return fn in writing or fn not in door_holders and used(clause, node, fn)

        def dotted(fn):
            around = [n.name for n in [fn, *up(fn)] if isinstance(n, defs + (ast.ClassDef,))] if fn is not None else []
            return ".".join(reversed(around)) or "<module>"

        conversions = ("str", "bytes", "fspath", "fsencode", "fsdecode", "Path", "PurePath", "abspath", "realpath", "normpath",
                       "expanduser", "resolve", "absolute", "as_posix")

        def hop(clause, node):                         # ONE hop: the value climbed through the steps that hand it on as it is (the
            call = parent.get(node)                    # docstring's pass-through), to the node holding it, with the names an
            n = call if clause == "a path function" and isinstance(call, ast.Call) and call.func is node else node   # assignment
            names = set()                                                                                            # expression binds
            while True:
                h = parent.get(n)
                if isinstance(h, ast.Attribute) and h.attr in conversions and isinstance(parent.get(h), ast.Call) and parent[h].func is h:
                    n = parent[h]                      # a conversion called on the value, as a method
                elif (isinstance(h, ast.BinOp) and isinstance(h.op, ast.Div)
                      or isinstance(h, (ast.keyword, ast.Tuple, ast.List, ast.Set, ast.Dict, ast.Starred, ast.BoolOp))
                      or isinstance(h, (ast.ListComp, ast.SetComp, ast.GeneratorExp)) and h.elt is n
                      or isinstance(h, ast.DictComp) and n in (h.key, h.value) or isinstance(h, ast.IfExp) and h.test is not n
                      or isinstance(h, ast.Call) and h.func is not n and (getattr(h.func, "id", None) or getattr(h.func, "attr", None))
                      in conversions):
                    n = h                              # a division, a keyword argument, a container, an and or an or, a
                elif isinstance(h, ast.NamedExpr) and h.value is n:   # conditional expression's branch, a conversion it is
                    names.add(h.target.id)             # handed to; an assignment expression, whose value goes on
                    n = h
                else:
                    return n, h, names

        def consumer(clause, node):                    # what the mention's value is handed to after its hop (the rows' key)
            if not isinstance(node, (ast.expr, ast.keyword)):
                return type(node).__name__             # a def, a parameter, an import or a global statement: its own kind
            n, holder, _ = hop(clause, node)
            if isinstance(holder, ast.Call) and holder.func is not n:  # a call: the function it names, else Call
                f = holder.func
                return getattr(f, "id", None) or ("." + f.attr if isinstance(f, ast.Attribute) else "Call")
            return "." + holder.attr if isinstance(holder, ast.Attribute) else type(holder).__name__   # an attribute; else its holder

        def lands(clause, node):                       # the names the mention's value lands in at the end of its hop
            if not isinstance(node, ast.expr):
                return set()                           # a def, a parameter, an import, a global statement, a keyword's label
            n, h, names = hop(clause, node)
            if isinstance(h, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and h.value is n:
                targets = h.targets if isinstance(h, ast.Assign) else [h.target]
            elif isinstance(h, (ast.For, ast.AsyncFor, ast.comprehension)) and h.iter is n:
                targets = [h.target]
            elif isinstance(h, ast.arguments):         # a parameter's default lands in the parameter
                positional = h.posonlyargs + h.args
                return names | {a.arg for a, d in list(zip(positional[len(positional) - len(h.defaults):], h.defaults))
                                + list(zip(h.kwonlyargs, h.kw_defaults)) if d is n}
            else:
                targets = []
            while any(isinstance(t, (ast.Tuple, ast.List, ast.Starred)) for t in targets):   # unpacked, a starred target included;
                targets = [e for t in targets for e in (t.elts if isinstance(t, (ast.Tuple, ast.List))   # an attribute or a subscript
                                                        else [t.value] if isinstance(t, ast.Starred) else [t])]   # holds it outside
            return names | {t.id for t in targets if isinstance(t, ast.Name)}               # the function's names: the limit

        landed = {}                                    # the unit (None: the module) -> the names a refused mention's value lands in

        def keyed_bound(fn):                           # the names the bound clause keys in fn
            return (names_in(fn) - module_names if fn is not None else set()) | landed.get(unit(fn), set()) | landed.get(None, set())

        while True:                                    # to a fixpoint: a refused use of a name a value landed in can land in another
            bound_mentions = [(function_of(node), bound, key, line, node)
                              for key in local_names.union(*landed.values()) for node, field, line in spots.get(key, ())
                              if key in keyed_bound(function_of(node)) and (field is None or not folded(bound, node, field, key))]
            grown = {(unit(fn), name) for fn, clause, key, line, node in mentions + bound_mentions if not classified(fn, clause, node)
                     for name in lands(clause, node) - keyed_bound(fn) - module_names}
            if not grown:
                break
            for u, name in grown:
                landed.setdefault(u, set()).add(name)
        mentions += bound_mentions
        refused = sorted(((dotted(fn), clause, key, consumer(clause, node), line) for fn, clause, key, line, node in mentions
                          if not classified(fn, clause, node)), key=lambda r: (r[4], r[0], r[1], r[2], r[3]))
        # THE ROWS: each names a function, the reason its refusal is false, and each refusal it lifts as (clause, token, what the
        # value is handed to), at its count
        exempt, counts = dict(exempt or {}), Counter(r[:4] for r in refused)
        malformed = sorted(fn for fn, row in exempt.items()
                           if not (isinstance(row, tuple) and len(row) == 2 and isinstance(row[0], str) and row[0]
                                   and isinstance(row[1], dict) and row[1]
                                   and all(isinstance(k, tuple) and len(k) == 3 for k in row[1])
                                   and all(isinstance(n, int) and n > 0 for n in row[1].values())))
        if malformed:
            raise AssertionError("THE NET'S EXEMPTION ROWS ARE (reason, {(clause, token, handed to): count}), a reason and one "
                                 "refusal at least, each at a count above 0: %s is not" % malformed)
        lifts = {(fn, clause, key, to): n for fn, (reason, lifted) in exempt.items() for (clause, key, to), n in lifted.items()}
        writing_names = {dotted(fn) for fn in writing}
        stale = ["%s lists %s %r handed to %s %d time(s), and the net refuses it %d time(s)%s" % (
                     fn, clause, key, to, n, counts[(fn, clause, key, to)],
                     " (%s is now a WRITER the derivation finds, so every mention in it is classified; the writers are %s: a "
                     "new writer is a new route for the set pin, not a row to delete)" % (fn, sorted(writers))
                     if fn in writing_names and clause not in ("a writer", "a door", unnamed) else "")
                 for (fn, clause, key, to), n in sorted(lifts.items()) if counts[(fn, clause, key, to)] < n]
        if stale:
            raise AssertionError("THE NET'S EXEMPTION ROWS LIFT ONLY WHAT IT REFUSES, EACH AT ITS COUNT: %s" % "; ".join(stale))
        refused = [r for r in refused if counts[r[:4]] > lifts.get(r[:4], 0)]     # beyond its row's count: every line of it
        if refusals:
            return writers, sorted(refs), [(fn, clause, key, line) for fn, clause, key, to, line in refused]
        if refused:
            raise AssertionError("THE NET REFUSES a function that mentions a name the census derives, in a place the derivation "
                                 "does not follow (fork PR #897, round 4, the reviewer's ruling on section G): %s. Classify it "
                                 "by a rule of the derivation, or name the function, the clause, the token, what it is handed "
                                 "to and its count in an exemption row with its reason" % "; ".join(
                                     "%s mentions %s %r at line %d, handed to %s" % (r[0], r[1], r[2], r[4], r[3])
                                     + (" (its exemption row lifts %d of %d)" % (lifts[r[:4]], counts[r[:4]]) if r[:4] in lifts else "")
                                     for r in refused))
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
        name and string the source holds, keyed on the derivation's own sets and on the nodes it reads, refusing by name,
        with the token and its line, each mention the derivation does not follow. Planted, each in a subtest whose label
        the census's docstring names beside the rule it pins: a refusal by each of the seven clauses; each fold and where
        it stops; what the derivation accounts for, a class body's binding not among it; the one hop, each step and each
        kind of target; the exemption rows, each refusal keyed by what its value is handed to after its hop, at its
        count, with the controls an edit keeping each consumer passes; each shape the derivation does not see, not found
        and refused; and the witnesses of the net's limit, neither found nor refused."""
        census = self._flag_writing_routes
        setter = ('def _set_flag(sid):\n'
                  '    _write_state_json(jd.STATE / "session-flags.json", "{}")\n')
        save = ('def _save(q, cur):\n'
                '    _atomic_write(q, cur)\n')
        name, bound, unnamed = "the store's name", "a name bound to the path", "a method the language calls unnamed"
        planted = (("a module-level name handed on by unpacking",
                    'FLAGS_PATH = jd.STATE / "session-flags.json"\n'
                    'def _by_module_unpacking(cur):\n'
                    '    base, p = jd.STATE, FLAGS_PATH\n'
                    '    p.write_text(cur)\n',
                    (set(), [], [("_by_module_unpacking", "a module-level name", "FLAGS_PATH", 3), ("_by_module_unpacking", bound, "p", 4)])),
                   ("a path function's call handed on by unpacking",
                    'def _flags_path():\n'
                    '    return jd.STATE / "session-flags.json"\n'
                    'def _by_call_unpacking(cur):\n'
                    '    base, p = jd.STATE, _flags_path()\n'
                    '    p.write_text(cur)\n',
                    (set(), [], [("_by_call_unpacking", "a path function", "_flags_path", 4), ("_by_call_unpacking", bound, "p", 5)])),
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
                   ("a path function called in a string handed to eval",
                    'def _flags_path():\n'
                    '    return jd.STATE / "session-flags.json"\n'
                    'def _by_eval(cur):\n'
                    '    eval("_flags_path()").write_text(cur)\n',
                    (set(), [], [("_by_eval", "a path function", "_flags_path", 4)])),
                   ("a path function called in a bytes string handed to eval",
                    'def _flags_path():\n'
                    '    return jd.STATE / "session-flags.json"\n'
                    'def _by_eval_bytes(cur):\n'
                    '    eval(b"_flags_path()").write_text(cur)\n',
                    (set(), [], [("_by_eval_bytes", "a path function", "_flags_path", 4)])),
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
                   ("a writer's name as a string beside a reference in a route",
                    'class Handler:\n'
                    '    def _set_flag(self, sid):\n'
                    '        _write_state_json(jd.STATE / "session-flags.json", "{}")\n'
                    '    def _dispatch_ws(self, msg, client):\n'
                    '        if msg.get("type") == "setFlag":\n'
                    '            self._set_flag(msg["id"])\n'
                    '        elif msg.get("type") == "setFlagByName":\n'
                    '            getattr(self, "_set_flag")(msg["id"])\n',
                    ({"_set_flag"}, [("Handler._dispatch_ws", ("setFlag",), "_set_flag")],
                     [("Handler._dispatch_ws", "a writer", "_set_flag", 8)])),
                   ("a writer imported under another name beside a reference in a route",
                    setter + 'def _route(b):\n'
                             '    _set_flag(b["id"])\n'
                             '    from kernel import _set_flag as set_flag\n'
                             '    set_flag(b["other"])\n',
                    ({"_set_flag"}, [("_route", (), "_set_flag")], [("_route", "a writer", "_set_flag", 5)])),
                   ("a def named like a door, and a keyword labelled like one",
                    'class Store:\n'
                    '    def rename(self, sid, name):\n'
                    '        return self.edit(sid, rename=name)\n',
                    (set(), [], [])),
                   ("a parameter named like a door",
                    'def _edit(rename=None):\n'
                    '    return str(rename)\n',
                    (set(), [], [("_edit", "a door", "rename", 1), ("_edit", "a door", "rename", 2)])),
                   ("a writer's own def, decorated",
                    '_OPS = {}\n'
                    'def _register(f):\n'
                    '    _OPS[f.__name__] = f\n'
                    '    return f\n'
                    '@_register\n'
                    'def _set_flag(sid):\n'
                    '    _write_state_json(jd.STATE / "session-flags.json", "{}")\n'
                    'def _route(b):\n'
                    '    _OPS[b["op"]](b["id"])\n',
                    ({"_set_flag"}, [], [("<module>", "a writer", "_set_flag", 6)])),
                   ("a path function's own def, decorated",
                    'def _on_boot(f):\n'
                    '    _atomic_write(f(), "{}")\n'
                    '    return f\n'
                    '@_on_boot\n'
                    'def _flags_path():\n'
                    '    return jd.STATE / "session-flags.json"\n',
                    (set(), [], [("<module>", "a path function", "_flags_path", 5)])),
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
                   ("a name bound to the path compared by identity, and one whose truth alone decides a test",
                    'def _flags_path():\n'
                    '    p = jd.STATE / "session-flags.json"\n'
                    '    if p is None or not p:\n'
                    '        return None\n'
                    '    return p\n',
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
                   ("a name bound to the path in a conditional expression's body, handed to a helper",
                    save + 'def _by_conditional(cur, c):\n'
                           '    p = jd.STATE / "session-flags.json"\n'
                           '    _save(p if c else None, cur)\n',
                    (set(), [], [("_by_conditional", bound, "p", 5)])),
                   ("a name bound to the path under an and, handed to a helper",
                    save + 'def _by_and(cur):\n'
                           '    p = jd.STATE / "session-flags.json"\n'
                           '    _save(jd.STATE and p, cur)\n',
                    (set(), [], [("_by_and", bound, "p", 5)])),
                   ("a path function that also writes the path through unpacking",
                    'def _flags_path():\n'
                    '    base, p = jd.STATE, jd.STATE / "session-flags.json"\n'
                    '    p.write_text("{}")\n'
                    '    return jd.STATE / "session-flags.json"\n',
                    (set(), [], [("_flags_path", name, "session-flags.json", 2), ("_flags_path", bound, "p", 3),
                                 ("_flags_path", name, "session-flags.json", 4)])),
                   ("a name bound to the path handed to a helper",
                    save + 'def _by_bound_name(cur):\n'
                           '    p = jd.STATE / "session-flags.json"\n'
                           '    _save(p, cur)\n',
                    (set(), [], [("_by_bound_name", bound, "p", 5)])),
                   ("a name bound to the path reached through locals() and a string",
                    save + 'def _by_local_string(cur):\n'
                           '    p = jd.STATE / "session-flags.json"\n'
                           '    _save(locals()["p"], cur)\n',
                    (set(), [], [("_by_local_string", bound, "p", 5)])),
                   ("a name bound to the path in a class body, read as the class's attribute",
                    save + 'def _by_class_attribute(cur):\n'
                           '    class _Where:\n'
                           '        p = jd.STATE / "session-flags.json"\n'
                           '    _save(_Where.p, cur)\n',
                    (set(), [], [("_by_class_attribute", name, "session-flags.json", 5), ("_by_class_attribute", bound, "p", 6)])),
                   ("a class's attribute bound to the path, the class returned and read in another function",
                    save + 'def _make():\n'
                           '    class _Where:\n'
                           '        p = jd.STATE / "session-flags.json"\n'
                           '    return _Where\n'
                           'def _by_returned_class(cur):\n'
                           '    _save(_make().p, cur)\n',
                    (set(), [], [("_make", name, "session-flags.json", 5)])),
                   ("a class's attribute bound to the path inside an if in its body",
                    save + 'def _make(c):\n'
                           '    class _Where:\n'
                           '        if c:\n'
                           '            p = jd.STATE / "session-flags.json"\n'
                           '    return _Where\n'
                           'def _by_returned_class(cur):\n'
                           '    _save(_make(1).p, cur)\n',
                    (set(), [], [("_make", name, "session-flags.json", 6)])),
                   ("a class's attribute bound to the path, read through self in a method",
                    save + 'def _by_method_attr(cur):\n'
                           '    class _Where:\n'
                           '        p = jd.STATE / "session-flags.json"\n'
                           '        def go(self):\n'
                           '            _save(self.p, cur)\n'
                           '    _Where().go()\n',
                    (set(), [], [("_by_method_attr", name, "session-flags.json", 5), ("_by_method_attr._Where.go", bound, "p", 7)])),
                   ("a name bound in another outermost function",
                    'def _where():\n'
                    '    p = jd.STATE / "session-flags.json"\n'
                    '    log(p)\n'
                    'def _by_parameter(p, cur):\n'
                    '    p.write_text(cur)\n',
                    (set(), [], [("_where", bound, "p", 3)])),
                   ("a name bound in a function, written outside every function",
                    'def _where():\n'
                    '    p = jd.STATE / "session-flags.json"\n'
                    '    log(p)\n'
                    'p.write_text("{}")\n',
                    (set(), [], [("_where", bound, "p", 3)])),
                   ("a name bound in another method of the same class",
                    'class Store:\n'
                    '    def _where(self):\n'
                    '        p = jd.STATE / "session-flags.json"\n'
                    '        log(p)\n'
                    '    def _by_sibling_method(self, p, cur):\n'
                    '        p.write_text(cur)\n',
                    (set(), [], [("Store._where", bound, "p", 4)])),
                   ("a name bound in another outermost function through a global statement",
                    'def _init():\n'
                    '    global FLAGS_PATH\n'
                    '    FLAGS_PATH = jd.STATE / "session-flags.json"\n'
                    'def _by_global(cur):\n'
                    '    _atomic_write(FLAGS_PATH, cur)\n',
                    (set(), [], [("_init", bound, "FLAGS_PATH", 2)])),
                   ("a nested function's global statement naming a name its enclosing function binds",
                    'def _flags_path():\n'
                    '    p = jd.STATE / "session-flags.json"\n'
                    '    def _publish():\n'
                    '        global p\n'
                    '        p = jd.STATE / "session-flags.json"\n'
                    '    _publish()\n'
                    '    return p\n'
                    'def _by_global_nested(cur):\n'
                    '    _atomic_write(p, cur)\n',
                    (set(), [], [("_flags_path._publish", bound, "p", 4)])),
                   ("an f-string holding the store's name in a longer piece",
                    'def _by_fstring(cur):\n'
                    '    with open(f"{jd.STATE}/session-flags.json", "w") as f:\n'
                    '        f.write(cur)\n',
                    (set(), [], [("_by_fstring", name, "session-flags.json", 2)])),
                   ("a string joined to the store's name",
                    'def _by_join(cur):\n'
                    '    _atomic_write(str(jd.STATE) + "/session-flags.json", cur)\n',
                    (set(), [], [("_by_join", name, "session-flags.json", 2)])),
                   ("the store's name in bytes",
                    'def _by_bytes(cur):\n'
                    '    with open(os.path.join(os.fsencode(str(jd.STATE)), b"session-flags.json"), "wb") as f:\n'
                    '        f.write(cur)\n',
                    (set(), [], [("_by_bytes", name, "session-flags.json", 2)])),
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
                    (set(), [], [("_by_unpacking", name, "session-flags.json", 2), ("_by_unpacking", bound, "p", 3)])),
                   ("a name bound by a for loop's target",
                    'def _by_loop(cur):\n'
                    '    for p in (jd.STATE / "session-flags.json",):\n'
                    '        p.write_text(cur)\n',
                    (set(), [], [("_by_loop", name, "session-flags.json", 2), ("_by_loop", bound, "p", 3)])),
                   ("a name bound by an assignment expression",
                    'def _by_walrus(cur):\n'
                    '    if (p := jd.STATE / "session-flags.json"):\n'
                    '        p.write_text(cur)\n',
                    (set(), [], [("_by_walrus", name, "session-flags.json", 2), ("_by_walrus", bound, "p", 3)])),
                   ("a name bound by a parameter's default",
                    'def _by_default(cur, p=jd.STATE / "session-flags.json"):\n'
                    '    p.write_text(cur)\n',
                    (set(), [], [("_by_default", name, "session-flags.json", 1), ("_by_default", bound, "p", 2)])),
                   ("a name bound by a comprehension's target",
                    'def _by_comprehension(cur):\n'
                    '    [p.write_text(cur) for p in (jd.STATE / "session-flags.json",)]\n',
                    (set(), [], [("_by_comprehension", bound, "p", 2), ("_by_comprehension", name, "session-flags.json", 2)])),
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
                   ("a path bound to a name and to an attribute in one assignment",
                    'def _flags_path():\n'
                    '    p = store.p = jd.STATE / "session-flags.json"\n'
                    '    return p\n',
                    (set(), [], [("_flags_path", bound, "p", 2), ("_flags_path", name, "session-flags.json", 2)])),
                   ("a path held in an attribute and written in another method",
                    'class Store:\n'
                    '    def __init__(self):\n'
                    '        self.p = jd.STATE / "session-flags.json"\n'
                    '    def _by_attribute(self, cur):\n'
                    '        self.p.write_text(cur)\n',
                    (set(), [], [("Store.__init__", name, "session-flags.json", 3)])),
                   ("a path in a door's argument through str()",
                    'def _by_str(cur):\n'
                    '    with open(str(jd.STATE / "session-flags.json"), "w") as f:\n'
                    '        f.write(cur)\n',
                    (set(), [], [("_by_str", name, "session-flags.json", 2)])),
                   ("a reader of the store",
                    'def _flags():\n'
                    '    return json.loads((jd.STATE / "session-flags.json").read_text())\n',
                    (set(), [], [("_flags", name, "session-flags.json", 2)])),
                   ("a path function writing its path through getattr and a string",
                    'def _flags_path():\n'
                    '    p = jd.STATE / "session-flags.json"\n'
                    '    getattr(p, "write_text")("{}")\n'
                    '    return p\n',
                    (set(), [], [("_flags_path", bound, "p", 3)])),
                   ("a path function handing its path to a helper that writes its parameter",
                    'def _flags_path():\n'
                    '    p = jd.STATE / "session-flags.json"\n'
                    '    _keep(p)\n'
                    '    return p\n'
                    'def _keep(q):\n'
                    '    q.write_text("{}")\n',
                    (set(), [], [("_flags_path", bound, "p", 3)])),
                   ("a route returning a path function's call that hands the path to a helper",
                    'def _flags_path():\n'
                    '    return jd.STATE / "session-flags.json"\n'
                    'def _save(p, data):\n'
                    '    _write_state_json(p, data)\n'
                    'def _route(path, b):\n'
                    '    if path == "/flagraw":\n'
                    '        _save(_flags_path(), b["data"])\n'
                    '        return 200\n'
                    '    return _flags_path()\n',
                    (set(), [], [("_route", "a path function", "_flags_path", 7)])),
                   ("a class defining a division",
                    'class _Joiner:\n'
                    '    def __truediv__(self, name):\n'
                    '        _atomic_write(jd.STATE / name, "{}")\n'
                    'def _by_division(cur):\n'
                    '    p = _Joiner() / "session-flags.json"\n',
                    (set(), [], [("<module>", unnamed, "__truediv__", 2)])),
                   ("a class defining a division by assignment",
                    'def _join(self, name):\n'
                    '    _atomic_write(jd.STATE / name, "{}")\n'
                    'class _Joiner:\n'
                    '    __truediv__ = _join\n'
                    'def _by_division(cur):\n'
                    '    p = _Joiner() / "session-flags.json"\n',
                    (set(), [], [("<module>", unnamed, "__truediv__", 4)])),
                   ("a path function the language calls unnamed",
                    'class _Store:\n'
                    '    def __fspath__(self):\n'
                    '        return jd.STATE / "session-flags.json"\n'
                    'def _by_fspath(cur):\n'
                    '    with open(_Store(), "w") as f:\n'
                    '        f.write(cur)\n',
                    (set(), [], [("<module>", unnamed, "__fspath__", 2)])),
                   ("a path built by string concatenation",
                    'def _by_concatenation(cur):\n'
                    '    _atomic_write(jd.STATE / ("session-" + "flags.json"), cur)\n',
                    (set(), [], [])),
                   ("a caller's local read through its frame",
                    'def _flags_path():\n'
                    '    p = jd.STATE / "session-flags.json"\n'
                    '    _peek()\n'
                    '    return p\n'
                    'def _peek():\n'
                    '    _atomic_write(sys._getframe(1).f_locals["p"], "{}")\n',
                    (set(), [], [])),
                   ("a local read back through locals() without its name",
                    save + 'def _by_locals_values(cur):\n'
                           '    p = jd.STATE / "session-flags.json"\n'
                           '    _save(list(locals().values())[-1], cur)\n',
                    (set(), [], [])),
                   ("a docstring holding the store's name, read back through __doc__ and inspect.getdoc",
                    'def _store():\n'
                    '    """session-flags.json"""\n'
                    'def _note():\n'
                    '    """The flags live in session-flags.json, beside the views."""\n'
                    'def _by_doc(cur):\n'
                    '    _atomic_write(jd.STATE / _store.__doc__, cur)\n'
                    '    _atomic_write(jd.STATE / inspect.getdoc(_note).split()[4].rstrip(","), cur)\n',
                    (set(), [], [])),
                   ("the store's name cut from a docstring's words, read back through __doc__",
                    'def _retire():\n'
                    '    """Renames the sidecars beside session-flags.json and moves them aside."""\n'
                    'def _by_doc_word(cur):\n'
                    '    _atomic_write(jd.STATE / next(w for w in _retire.__doc__.split() if w.endswith(".json")), cur)\n',
                    (set(), [], [])),
                   ("a def named like a writer, read back through __name__",
                    setter + 'class _Ops:\n'
                             '    def _set_flag(self):\n'
                             '        pass\n'
                             'def _route(b):\n'
                             '    for f in vars(_Ops).values():\n'
                             '        if callable(f):\n'
                             '            globals()[f.__name__](b["id"])\n',
                    ({"_set_flag"}, [], [])),
                   ("a class named like a writer, read back through __name__",
                    setter + 'class _Ops:\n'
                             '    class _set_flag:\n'
                             '        pass\n'
                             'def _route(b):\n'
                             '    for c in vars(_Ops).values():\n'
                             '        if isinstance(c, type):\n'
                             '            globals()[c.__name__](b["id"])\n',
                    ({"_set_flag"}, [], [])),
                   ("a def named like a path function that is not one",
                    'def _flags_path():\n'
                    '    return jd.STATE / "session-flags.json"\n'
                    'class _Names:\n'
                    '    def _flags_path(self):\n'
                    '        return None\n'
                    'def _by_def_name(cur):\n'
                    '    for f in vars(_Names).values():\n'
                    '        if callable(f):\n'
                    '            _atomic_write(globals()[f.__name__](), cur)\n',
                    (set(), [], [])),
                   ("a keyword labelled like a writer, read back as a key",
                    setter + 'def _route(b):\n'
                             '    globals()[next(iter(dict(_set_flag=0)))](b["id"])\n',
                    ({"_set_flag"}, [], [])),
                   ("a keyword labelled like a name bound to the path, read back through eval",
                    save + 'def _by_label(cur):\n'
                           '    p = jd.STATE / "session-flags.json"\n'
                           '    _save(eval(next(iter(dict(p=0)))), cur)\n',
                    (set(), [], [])),
                   ("a writer picked by its parameters' names through __code__",
                    'def _set_flag(sid, flag, value):\n'
                    '    _write_state_json(jd.STATE / "session-flags.json", "{}")\n'
                    'def _route(b):\n'
                    '    fn = next(f for f in list(globals().values())\n'
                    '              if getattr(getattr(f, "__code__", None), "co_varnames", ())[:3] == ("sid", "flag", "value"))\n'
                    '    fn(b["id"], b["flag"], True)\n',
                    ({"_set_flag"}, [], [])),
                   ("a writer defined in a module the kernel loads",
                    'class Handler:\n'
                    '    def _dispatch_ws(self, msg, client):\n'
                    '        if msg.get("type") == "setFlagElsewhere":\n'
                    '            jd._set_flag_elsewhere(msg["id"], msg["flag"])\n',
                    (set(), [], [])))
        for label, src, expected in planted:
            with self.subTest(net=label):
                self.assertEqual(census(src, refusals=True), expected,
                                 "THE NET (round 4 of fork PR #897, the reviewer's ruling on section G): %s. The census's "
                                 "docstring names this plant beside the rule it pins; the third element is what the net "
                                 "refuses, each as (function, clause, token, line)" % label)
        # THE ONE HOP (the census docstring's rule): a refused mention's value, followed through the steps that hand it on as
        # it is, lands in the name it is bound to, which the net then keys as a name bound to the path
        import re
        value, path = 'str(jd.STATE / "session-flags.json")', 'jd.STATE / "session-flags.json"'
        conversions = ("str", "bytes", "fspath", "fsencode", "fsdecode", "Path", "PurePath", "abspath", "realpath", "normpath",
                       "expanduser", "resolve", "absolute", "as_posix")
        listed = re.search(r"a conversion \(a call named (.+?), by bare name or as a method", " ".join((census.__doc__ or "").split()))
        self.assertEqual(tuple(re.split(r", | or ", listed.group(1))) if listed else None, conversions,
                         "the conversions the census docstring names are the conversions planted below, each in three forms")
        steps = [(label % c, form % ((c, path) if "%s(%s)" in form else (path, c))) for c in conversions
                 for label, form in (("the conversion %s by bare name", "%s(%s)"), ("the conversion %s as a method", "store.%s(%s)"),
                                     ("the conversion %s called on the value", "(%s).%s()"))]
        steps += [("a keyword argument of a conversion", "str(object=%s)" % path), ("a tuple", "(0, %s)" % value),
                  ("a list", "[0, %s]" % value), ("a set", "{0, %s}" % value), ("a dict's value", "{0: %s}" % value),
                  ("a dict's key", "{%s: 0}" % value), ("a starred item", "(*(%s,),)" % value),
                  ("a list comprehension's element", "[%s for _ in (0,)]" % value),
                  ("a set comprehension's element", "{%s for _ in (0,)}" % value),
                  ("a generator's element", "(%s for _ in (0,))" % value),
                  ("a dict comprehension's key", "{%s: 0 for _ in (0,)}" % value),
                  ("a dict comprehension's value", "{0: %s for _ in (0,)}" % value),
                  ("an operand of or", "cur or %s" % value), ("an operand of and", "cur and %s" % value),
                  ("a conditional expression's body", "%s if cur else None" % value),
                  ("a conditional expression's orelse", "None if cur else %s" % value),
                  ("an assignment expression on the way", "(r := %s)" % value)]
        for label, expr in steps:
            with self.subTest(net="a refused mention's value lands in a name through each step", step=label):
                self.assertEqual(census(save + 'def _by_step(cur):\n    q = %s\n    _save(q, cur)\n' % expr, refusals=True),
                                 (set(), [], [("_by_step", name, "session-flags.json", 4), ("_by_step", bound, "q", 5)]),
                                 "THE ONE HOP (round 4 of fork PR #897, the reviewer's ruling on the pass-through): the store's "
                                 "name reaches q through %s, so q is keyed as a name bound to the path and its use is refused; a "
                                 "net that stops at this step lets q hand the path on unrefused" % label)
        targets = (("a chained assignment", 'def _by_target(cur):\n    q = r = %s\n    _save(q, cur)\n', 4, 5),
                   ("an annotated assignment", 'def _by_target(cur):\n    q: str = %s\n    _save(q, cur)\n', 4, 5),
                   ("an augmented assignment", 'def _by_target(cur):\n    q = ""; q += %s\n    _save(q, cur)\n', 4, 5),
                   ("a starred target", 'def _by_target(cur):\n    first, *q = 0, %s\n    _save(q, cur)\n', 4, 5),
                   ("a list target", 'def _by_target(cur):\n    [q] = [%s]\n    _save(q, cur)\n', 4, 5),
                   ("an async for loop's target", 'async def _by_target(cur):\n    async for q in (%s,):\n        _save(q, cur)\n', 4, 5),
                   ("a keyword-only parameter's default", 'def _by_target(cur, *, q=%s):\n    _save(q, cur)\n', 3, 4),
                   ("a positional-only parameter's default", 'def _by_target(q=%s, /):\n    _save(q, None)\n', 3, 4))
        for label, body, at, use in targets:
            with self.subTest(net="a refused mention's value lands in a name by each kind of target", target=label):
                self.assertEqual(census(save + body % value, refusals=True),
                                 (set(), [], [("_by_target", name, "session-flags.json", at), ("_by_target", bound, "q", use)]),
                                 "THE ONE HOP: the store's name lands in q, %s, so q's use is refused" % label)
        with self.subTest(net="a use of a name a value landed in, landing in another"):
            self.assertEqual(census(save + 'def _by_two(cur):\n    p = %s\n    q = p\n    _save(q, cur)\n' % value, refusals=True),
                             (set(), [], [("_by_two", name, "session-flags.json", 4), ("_by_two", bound, "p", 5),
                                          ("_by_two", bound, "q", 6)]),
                             "to a fixpoint: p's refused use lands in q, which is keyed in its turn")
        with self.subTest(net="a name a value landed in, read by a nested function"):
            self.assertEqual(census(save + 'def _by_closure(cur):\n    p = %s\n    def _later():\n        _save(p, cur)\n'
                                           '    _locked(_later)\n' % value, refusals=True),
                             (set(), [], [("_by_closure", name, "session-flags.json", 4), ("_by_closure._later", bound, "p", 6)]),
                             "a landed name is keyed throughout the outermost function around it, a nested function included")
        with self.subTest(net="a name the module binds, a value landed in, read in a function"):
            self.assertEqual(census(save + 'P = %s\ndef _by_module_landed(cur):\n    _save(P, cur)\n' % value, refusals=True),
                             (set(), [], [("<module>", name, "session-flags.json", 3), ("_by_module_landed", bound, "P", 5)]),
                             "a name the module binds, a value landed in, is keyed everywhere")
        cold = 'def _cold():\n    p = str(jd.STATE / "session-flags.json")\n    return p in SEEN and CACHE.get(p) is None\n'
        cold_row = {"_cold": ("a planted reason", {(name, "session-flags.json", "Assign"): 1, (bound, "p", "Compare"): 1,
                                                    (bound, "p", ".get"): 1})}
        sig = ('def _sig(sig):\n    for p, k in ((jd.STATE / "colormap", "__cmap__"), (jd.STATE / "session-flags.json", "__flags__")):\n'
               '        sig[k] = os.stat(p).st_mtime\n')
        sig_row = {"_sig": ("a planted reason", {(name, "session-flags.json", "For"): 1, (bound, "p", ".stat"): 1,
                                                  (bound, "k", "Subscript"): 1})}
        with self.subTest(net="a lifted mention's value landing in a name, written through it"):
            self.assertEqual(census(cold, exempt=cold_row), (set(), []), "the row lifts the store's name, bound as a string to p, "
                             "and p's two uses, each by its consumer (the shape of the real kernel.py's _flags_unknown_cold)")
            self.assertEqual(census(sig, exempt=sig_row), (set(), []), "the row lifts the store's name, unpacked by the loop into "
                             "p and k, and their two uses, each by its consumer (the shape of the real kernel.py's view-cache signature)")
            for shape, src, row, said in (
                    ("C1, a write through p", cold.replace("    return", '    if PENDING:\n        _write_state_json(p, "{}")\n    return'),
                     cold_row, "_cold mentions a name bound to the path 'p' at line 4, handed to _write_state_json"),
                    ("C1h, p handed to a helper that writes its parameter",
                     'def _flush(q):\n    _write_state_json(q, "{}")\n' + cold.replace("    return", "    _flush(p)\n    return"),
                     cold_row, "_cold mentions a name bound to the path 'p' at line 5, handed to _flush"),
                    ("C2, a write through the loop's p",
                     sig.replace("        sig[k]", '        if k == "__flags__":\n            _write_state_json(p, "{}")\n        sig[k]'),
                     sig_row, "_sig mentions a name bound to the path 'p' at line 4, handed to _write_state_json")):
                with self.assertRaises(AssertionError) as landed:
                    census(src, exempt=row)
                self.assertIn(said, str(landed.exception),
                              "THE NAME A LIFTED MENTION'S VALUE LANDS IN IS KEYED (the verifier's %s, driven through the real "
                              "kernel in round 4 of fork PR #897): the row still lifts the mention at its consumer, and the new "
                              "use of the name it landed in is refused" % shape)
        with self.subTest(net="a use of a landed name by the consumer its row lists stays lifted"):
            edited = cold.replace("return p in SEEN and CACHE.get(p) is None", "return CACHE.get(p, None) is None and (\n        p in SEEN)")
            self.assertEqual(census(edited, exempt=cold_row), (set(), []),
                             "the CONTROL: p's uses edited, each still handed to the consumer its row lists, stay lifted")
        with self.subTest(net="a lifted mention handed on through a conversion to another call is refused"):
            hit = 'def _hit():\n    p = jd.STATE / "session-flags.json"\n    return CACHE.get(str(p))\n'
            hit_row = {"_hit": ("a planted reason", {(bound, "p", ".get"): 1})}
            self.assertEqual(census(hit, exempt=hit_row), (set(), []),
                             "the row lifts p handed, as a string, to the display cache's lookup: its consumer is read past str")
            with self.assertRaises(AssertionError) as onward:
                census(hit.replace("CACHE.get(str(p))", "_rv_write(str(p))"), exempt=hit_row)
            self.assertIn("_hit lists a name bound to the path 'p' handed to .get 1 time(s), and the net refuses it 0 time(s)",
                          str(onward.exception), "THE CONSUMER IS READ AFTER THE HOP: the same str(p) handed to a helper that "
                          "writes the store leaves its row unmatched, which raises (a key read at str would still match)")
        for label, src, row in (
                ("a path returned as a string and written by the caller",
                 save + 'def _key():\n    return str(jd.STATE / "session-flags.json")\ndef _by_return(cur):\n    _save(_key(), cur)\n',
                 {"_key": ("a planted reason", {(name, "session-flags.json", "Return"): 1})}),
                ("a path appended to a module-level list and written from it",
                 save + '_SEEN = []\ndef _note():\n    _SEEN.append(str(jd.STATE / "session-flags.json"))\n'
                        'def _by_container(cur):\n    _save(_SEEN[0], cur)\n',
                 {"_note": ("a planted reason", {(name, "session-flags.json", ".append"): 1})}),
                ("a path held in an attribute as a string and written in another method",
                 save + 'class Store:\n    def __init__(self):\n        self.where = str(jd.STATE / "session-flags.json")\n'
                        '    def _by_attribute(self, cur):\n        _save(self.where, cur)\n',
                 {"Store.__init__": ("a planted reason", {(name, "session-flags.json", "Assign"): 1})}),
                ("a path stored as a cache's key and read back elsewhere",
                 '_cache = {}\ndef _read():\n    p = jd.STATE / "session-flags.json"\n    _cache[str(p)] = p.read_text()\n'
                 'def _by_cache_key(cur):\n    _atomic_write(next(k for k in _cache if k.endswith("-flags.json")), cur)\n',
                 {"_read": ("a planted reason", {(bound, "p", "Subscript"): 1, (bound, "p", ".read_text"): 1})})):
            with self.subTest(net=label):
                self.assertEqual(census(src, exempt=row), (set(), []),
                                 "THE ONE-HOP LIMIT'S WITNESS (round 4 of fork PR #897, the reviewer's ruling): the value leaves "
                                 "the function beyond its one hop, and the writer that reads it back is neither found nor "
                                 "refused, its source's refusal lifted by a row as on the real kernel.py: %s" % label)
        shutil_src = planted[[p[0] for p in planted].index("shutil.copy")][1]
        row = {"_by_library": ("a planted reason", {(name, "session-flags.json", ".copy"): 1})}
        with self.subTest(net="a row lifts a refused mention"):
            self.assertEqual(census(shutil_src, exempt=row), (set(), []),
                             "an exemption row lifts the refusal it lists, (clause, token, what the value is handed to), at its "
                             "count, in the function it names")
            with self.assertRaises(AssertionError) as refusal:
                census(shutil_src)
            self.assertIn("_by_library mentions the store's name 'session-flags.json' at line 2, handed to .copy",
                          str(refusal.exception), "with no row, the census raises, naming the function, the clause, the token, "
                          "its line and what its value is handed to")
            self.assertEqual(census('def _key():\n    return _stat(path=jd.STATE / "session-flags.json")\n',
                                    exempt={"_key": ("a planted reason", {(name, "session-flags.json", "_stat"): 1})}), (set(), []),
                             "a value handed on as a keyword argument is handed to the call that takes it")
            self.assertEqual(census('def _key(ops):\n    return ops["stat"](jd.STATE / "session-flags.json")\n',
                                    exempt={"_key": ("a planted reason", {(name, "session-flags.json", "Call"): 1})}), (set(), []),
                             "a value handed to a call of a function with no name is handed to Call")
            self.assertEqual(census('def _flags_path():\n    return jd.STATE / "session-flags.json"\n'
                                    'def _key():\n    return _stat(_flags_path())\n',
                                    exempt={"_key": ("a planted reason", {("a path function", "_flags_path", "_stat"): 1})}),
                             (set(), []), "a path function's call is what is handed on, so the row names what takes the call")
        with self.subTest(net="a mention beyond its row is refused"):
            twice = shutil_src + '    shutil.copy(tmp, jd.STATE / "session-flags.json")\n'
            with self.assertRaises(AssertionError) as beyond:
                census(twice, exempt=row)
            self.assertIn("_by_library mentions the store's name 'session-flags.json' at line 3, handed to .copy (its exemption "
                          "row lifts 1 of 2)", str(beyond.exception),
                          "a refusal the net makes more times than its row lists is refused at every line")
            other = shutil_src + '    p = jd.STATE / "session-flags.json"\n    _save(p)\n'
            self.assertEqual(census(other, exempt=row, refusals=True), (set(), [], [("_by_library", bound, "p", 4)]),
                             "a refusal the row does not list is refused though the row names the function: a row lifts its "
                             "refusals, never the function (the verifier's plant, a new arm inside an exempt dispatcher)")
        with self.subTest(net="a lifted mention handed elsewhere is refused"):
            stat_row = {"_key": ("a planted reason", {(name, "session-flags.json", ".stat"): 1})}
            self.assertEqual(census('def _key():\n    return (jd.STATE / "session-flags.json").stat()\n', exempt=stat_row),
                             (set(), []), "the row lifts the store's name handed to its stat")
            edited = 'def _key():\n    return _stat(jd.STATE / "session-flags.json")\n'
            with self.assertRaises(AssertionError) as moved:
                census(edited, exempt=stat_row)
            self.assertIn("_key lists the store's name 'session-flags.json' handed to .stat 1 time(s), and the net refuses it 0 "
                          "time(s)", str(moved.exception),
                          "THE SAME MENTION EDITED TO HAND THE PATH ELSEWHERE (the verifier's plant: a stat turned into a "
                          "helper that writes the store) leaves its row unmatched, which raises")
            beside = ('def _key():\n    (jd.STATE / "session-flags.json").stat()\n'
                      '    return _stat(jd.STATE / "session-flags.json")\n')
            with self.assertRaises(AssertionError) as elsewhere:
                census(beside, exempt=stat_row)
            self.assertIn("_key mentions the store's name 'session-flags.json' at line 3, handed to _stat", str(elsewhere.exception),
                          "the same clause and token handed to something the row does not list is refused, the row's own "
                          "refusal beside it notwithstanding")
        with self.subTest(net="a lifted mention edited with its consumer unchanged stays lifted"):
            self.assertEqual(census('def _key():\n    return (jd.STATE /\n            "session-flags.json").stat(\n        follow_symlinks=True)\n',
                                    exempt=stat_row), (set(), []),
                             "the CONTROL: the lifted stat split across lines and given a keyword argument keeps its consumer, "
                             "so its row still lifts it")
        with self.subTest(net="a row entry the net refuses fewer times"):
            with self.assertRaises(AssertionError) as stale:
                census(shutil_src, exempt={"_by_library": ("a planted reason", {(name, "session-flags.json", ".copy"): 2})})
            self.assertIn("THE NET'S EXEMPTION ROWS LIFT ONLY WHAT IT REFUSES, EACH AT ITS COUNT: _by_library lists the store's "
                          "name 'session-flags.json' handed to .copy 2 time(s), and the net refuses it 1 time(s)",
                          str(stale.exception), "a row entry the net refuses fewer times than it lists raises, so the rows "
                          "stay exact")
            for bad in ("a planted reason", ("a planted reason", {(name, "session-flags.json"): 1})):
                with self.assertRaises(AssertionError) as malformed:
                    census(shutil_src, exempt={"_by_library": bad})
                self.assertIn("THE NET'S EXEMPTION ROWS ARE (reason, {(clause, token, handed to): count})", str(malformed.exception),
                              "a row that is not a reason and its refusals, each keyed by what the value is handed to, raises")
        with self.subTest(net="a row of a function that has become a writer"):
            with self.assertRaises(AssertionError) as writer:
                census(setter, exempt={"_set_flag": ("a planted reason", {(name, "session-flags.json", "_write_state_json"): 1})})
            self.assertIn("_set_flag lists the store's name 'session-flags.json' handed to _write_state_json 1 time(s), and the "
                          "net refuses it 0 time(s) (_set_flag is now a WRITER the derivation finds", str(writer.exception),
                          "a row gone stale because its function became a writer says so and names the writers, so the red "
                          "points at the set pin and not at the row")
            two = ('def _set_flag(sid):\n    log("not _set_other")\n    _write_state_json(jd.STATE / "session-flags.json", "{}")\n'
                   'def _set_other(sid):\n    _write_state_json(jd.STATE / "session-flags.json", "{}")\n')
            self.assertEqual(census(two, exempt={"_set_flag": ("a planted reason", {("a writer", "_set_other", "log"): 1})}),
                             ({"_set_flag", "_set_other"}, []), "a row in a writer lifts a writer's name in a string")
            with self.assertRaises(AssertionError) as named:
                census(two, exempt={"_set_flag": ("a planted reason", {("a writer", "_set_other", "log"): 2})})
            self.assertIn("_set_flag lists a writer '_set_other' handed to log 2 time(s), and the net refuses it 1 time(s)",
                          str(named.exception), "the row entry the net refuses fewer times raises")
            self.assertNotIn("is now a WRITER", str(named.exception),
                             "a stale entry of a clause the writer rule does not classify (a writer's name in a string) carries "
                             "no writer note: the function did not become a writer, it was one")

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
        WebSocket arm, so a new route fails the set pin, and a mention the net refuses there fails it by name, but for the
        net's stated limit: the net follows a keyed value one hop, to its consumer or to the name it lands in, so a value
        that leaves the function through a return, a container, an attribute or a store and is read back elsewhere passes
        it, as do a path built at run time, a local or a name read back at run time through reflection, and a path or a
        writer in a module the kernel loads. Executed over the real handlers: the listing with thread rows has the thread and the roster omits it; a
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
