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

    @staticmethod
    def _flag_writing_routes(source):
        """The kernel's routes that write a session flag, DERIVED from the source (fork PR #897, round 3, the reviewer's
        ruling on section D: the witness pins the population as a set, so a new route turns it red). Returns (writers,
        references). A WRITER is a function holding a call of a write door one of whose arguments, or whose receiver,
        carries the flags path ("<module>" for a call outside every function). The doors: a call named
        _write_state_json, _atomic_write, open, replace, rename, write_text or write_bytes, by bare name or as a method
        whatever its receiver (Path.open, os.open and io.open alike, and so a method named _atomic_write or a replace
        imported from os). An expression CARRIES the flags path when it holds the constant "session-flags.json"; a name
        bound to the path; or a call, by bare name or as a method, of a PATH FUNCTION: a function one of whose own
        return statements returns an expression that carries the path. A name is BOUND to the path by an assignment
        (plain, annotated, or augmented as in p /= "session-flags.json") to a plain name whose value carries the path,
        in any order. A binding outside every function (at module level or in a class body, inside an if or a try there
        included) counts everywhere. A binding in a function counts throughout the outermost function around it, and so
        in every function nested in that one at any depth (a closure reading its enclosing function's name, the function
        around a nested one that binds it, and a function beside the binding inside that outermost function), and
        nowhere outside it, in another function or outside every function. Path functions and module-level names are
        derived together to a FIXPOINT (round 4 of fork PR #897, the reviewer's ruling on its round-3 refuters' finding,
        the thirty-sixth commit), since a path function's call can bind a module-level name that another function
        returns, and so on: a function returning a module-level name bound to the constant (the kernel's own idiom of a
        _X_FILE name beside an _x_path() function), a path function calling another at any depth, and a module-level
        name bound to such a call are all found. Until that commit a path function was one whose return statement held
        the constant itself, and open was a door by bare name alone, so a writer through any of those three shapes,
        through a path function returning a name bound in it, or through p.open, os.open or io.open was missed; the
        plant of each in test_the_flag_route_census_finds_a_new_route_and_a_writer_of_each_shape is red under the census
        as it stood at the round-3 head. The refuter drove two of these through the real WebSocket arm, a path function
        returning a module-level name and a write through p.open: each arm wrote the key while the set pin passed. The
        door list and the binding rule err wide (a read through open, a str.replace on the path, or a name a nested
        function binds, read outside it with no nonlocal statement, counts too), so a miss is what they guard against
        and a surplus fails the pin loudly. A REFERENCE is every other mention of a writer's name in the file, a call or
        not, in a function, in a class body or outside both, as (the dotted name of the classes and functions around it,
        "<module>" outside all of them; the selectors; the writer). The SELECTORS are, outermost first, the string
        constants among the operands of each comparison whose operators are all == (either side, every operand of a
        chain), anywhere in the test (every operand of an and, an or or a not, nested ones included), of each if
        statement whose body, not its else, holds the mention, between the mention and the function around it (up to the
        module for a mention outside every function). The route's own selector leads: POST /flag's path in
        _state_write_route, the WebSocket op's type in Handler._dispatch_ws.
        A text census cannot be complete, and this one covers the shapes above and no other. Each of those shapes has a
        plant in that test that a census dropping or changing it turns red, each door name by bare name and as a method
        included, and so does each rule that narrows one, under a census widening it: a function's OWN return statements
        count, not a nested function's; a binding in a function counts nowhere outside the outermost function around it,
        in another function or outside every function; a binding is an assignment of the three kinds above to a plain
        name; a selector is a string constant in a comparison whose operators are all ==, each of the nine other
        comparison operators planted; and selectors come from if statements alone (a while, a conditional expression and
        a match's case give none), from those whose body holds the mention, and from those inside the function around
        it. A plant may carry several shapes, as the test's first two do. The thirty-seventh commit said each had a
        plant of its own while a census could drop, change or widen six of them and pass every plant in that test: a
        path function with a return that does not carry the path beside one that does, a mention of a writer through an
        attribute, a selector on the left of its comparison, the selectors of nested ifs outermost first, a name bound
        in another function not counting, and a binding being an assignment to a plain name (the fourth and fifth turned
        only the real kernel's set pin red, the others nothing). The thirty-eighth commit planted each, and made each
        door name a door by bare name and as a method alike: until then two were doors by bare name alone and four as
        methods alone (open was a door both ways), so a write through a method named _atomic_write or through a replace
        imported from os was missed, and the plant of each is red under the census as it stood at the thirty-seventh
        commit. That commit left without a plant four of the fourteen door cells (_write_state_json as a method, rename,
        write_text and write_bytes by bare name), a mention outside every function, five rules of the selectors (no !=
        and no is, no while, no if outside the function around the mention, every comparison of a test) and three kinds
        of binding (an augmented assignment, a with statement's as, a comprehension's target), and it said a name counts
        in the function that binds it and not in another function while its census counted a nested function's binding
        in the function around it and read no enclosing function's binding in a nested one. The thirty-ninth commit
        plants each door cell and each of the rest and states the binding rule above, and the census now reads a binding
        in an augmented assignment and throughout the outermost function around it, so a write through a name an
        augmented assignment binds, a closure's write through its enclosing function's name, a write in a function
        beside the binding in one outermost function, and a write through a path function returning its enclosing
        function's name are found; the plant of each is red under the census as it stood at the thirty-eighth commit.
        Among what it does not see, each planted there and asserted NOT found, so this text moves if the census ever
        reaches one: a path built by string concatenation (no constant equals the name), a write through a library
        function outside the doors (shutil.copy), a write by another process (a subprocess), a path handed as an
        argument to a function that writes its parameter (the census follows no argument into its callee), a name bound
        other than by such an assignment (planted as unpacking into a tuple, an assignment to an attribute, a for loop's
        target, a comprehension's target, a with statement's as, an assignment expression and a parameter's default), a
        path held in an attribute and written in another method (self.p), and a name bound in another outermost function
        through a global statement."""
        import ast
        flags = "session-flags.json"
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
        writers = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if (getattr(f, "id", None) or getattr(f, "attr", None)) not in (
                    "_write_state_json", "_atomic_write", "open", "replace", "rename", "write_text", "write_bytes"):
                continue
            fn = function_of(node)
            parts = list(node.args) + [k.value for k in node.keywords] + ([f.value] if isinstance(f, ast.Attribute) else [])
            if any(carries(p, names_in(fn)) for p in parts):
                writers.add("<module>" if fn is None else fn.name)
        refs = []
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
        return writers, sorted(refs)

    def test_the_flag_route_census_finds_a_new_route_and_a_writer_of_each_shape(self):
        """The census the witness below pins (fork PR #897, round 3), run against what it must catch, on planted
        sources: a third WebSocket arm calling the setter; writers through a module-level path name, through a function
        that returns the path and through a local name bound to that call, reached by a new POST route directly and
        through a helper; and a write at module level. Each lands in the population, so the witness's set equality turns
        red on it. Since round 4 (the thirty-sixth commit, the census derived to a fixpoint) four more plants, each of
        shapes the census missed before that commit, each in its own subtest: a path function returning a module-level
        name bound to the constant, reached by a new WebSocket arm; a path function calling another, two levels, beside
        a module-level name bound to a call of a path function that returns a module-level name; open called as a
        method, on a Path, on os and on io; and a module-level name bound inside a try beside a name bound to one the
        walk reaches later (a branch's body). The thirty-seventh commit added a plant in its own subtest for ten shapes
        and narrowing rules the census docstring lists (a census dropping any one of them passed every plant before): a
        path function called as a method, a module-level name bound by an annotated assignment, the path in a door's
        keyword argument, a path function returning a name bound in it, the rename and write_bytes doors, a module-level
        name bound inside an if, a mention of a writer that is not a call, a selector as a string constant compared for
        equality alone, and a nested function's return being its own. It said that left none of them unplanted, and six
        were; the thirty-eighth commit planted those, five here, each in its own subtest: a path function with a return
        that does not carry the path beside one that does, a mention of a writer through an attribute, a selector on the
        left of its comparison, the selectors of nested ifs outermost first, and a name bound in another function not
        counting (the sixth, a binding being an assignment to a plain name, is planted with what the census does not
        see, below); and the two door forms that commit added, a door name called as a method and one called by bare
        name. The thirty-ninth commit replaced those two with a plant for each of the fourteen door cells, each door
        name by bare name and as a method, the docstring's list of doors asserted equal to the list planted; and added,
        each in its own subtest: a name bound in a function not counting outside every function; a mention of a writer
        outside every function, one in a class body, and the selectors of a mention outside every function; every
        comparison of a test, under an or, an and and a not; a comparison whose operators are not all ==, and each of
        the nine other comparison operators; an if outside the function around the mention; a while, a conditional
        expression and a match's case, none giving a selector; a name bound by an augmented assignment; and four writes
        through the binding rule the census now follows, a closure's through a name its enclosing function binds, one
        through a name a nested function binds through a nonlocal statement, one in a function beside the binding in one
        outermost function, and one through a path function returning a name its enclosing function binds. Then what the
        census does NOT see, one plant of each class its docstring names, each asserted not found, so the docstring
        moves if the census ever reaches one: a path built by concatenation, shutil.copy, a subprocess, a path handed to
        a helper that writes its parameter, a name bound by unpacking into a tuple, by an assignment to an attribute, by
        a for loop's target, by a comprehension's target, by a with statement's as, by an assignment expression and by a
        parameter's default, a path held in an attribute and written in another method, and a name bound in another
        outermost function through a global statement."""
        census = self._flag_writing_routes
        third_arm = ('def _set_session_flag(sid, flag, value):\n'
                     '    _write_state_json(jd.STATE / "session-flags.json", "{}")\n'
                     'class Handler:\n'
                     '    def _dispatch_ws(self, msg, client):\n'
                     '        if msg.get("type") == "setSessionFlag":\n'
                     '            _set_session_flag(msg["id"], msg["flag"], True)\n'
                     '        elif msg.get("type") == "setSessionFlagAny":\n'
                     '            _set_session_flag(msg["id"], msg["flag"], True)\n')
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
                  ("a selector is a string constant compared for equality, and no other",
                   setter + 'def _route(path, b):\n'
                            '    if path == "/flag" and "id" in b and len(b) == 2:\n'
                            '        _set_flag(b["id"])\n',
                   ({"_set_flag"}, [("_route", ("/flag",), "_set_flag")])),
                  ("a nested function's return is its own",
                   'def _outer(cur):\n'
                   '    def _inner():\n'
                   '        return jd.STATE / "session-flags.json"\n'
                   '    return cur\n'
                   'def _by_outer(cur):\n'
                   '    _atomic_write(_outer(cur), cur)\n',
                   (set(), [])),
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
                  ("a name bound in another outermost function does not count",
                   'def _where():\n'
                   '    p = jd.STATE / "session-flags.json"\n'
                   '    log(p)\n'
                   'def _by_parameter(p, cur):\n'
                   '    p.write_text(cur)\n',
                   (set(), [])),
                  ("a name bound in a function does not count outside every function",
                   'def _where():\n'
                   '    p = jd.STATE / "session-flags.json"\n'
                   '    log(p)\n'
                   'p.write_text("{}")\n',
                   (set(), [])),
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
                  ("a comparison whose operators are not all ==",
                   setter + 'def _route(path, b):\n'
                            '    if "/flag" == path != "/other":\n'
                            '        _set_flag(b["id"])\n',
                   ({"_set_flag"}, [("_route", (), "_set_flag")])),
                  ("an if outside the function around the mention",
                   setter + 'if MODE == "legacy":\n'
                            '    def _route(b):\n'
                            '        _set_flag(b["id"])\n',
                   ({"_set_flag"}, [("_route", (), "_set_flag")])),
                  ("a while gives no selector",
                   setter + 'def _route(op, b):\n'
                            '    while op == "retry":\n'
                            '        _set_flag(b["id"])\n',
                   ({"_set_flag"}, [("_route", (), "_set_flag")])),
                  ("a conditional expression gives no selector",
                   setter + 'def _route(path, b):\n'
                            '    return _set_flag(b["id"]) if path == "/flag" else None\n',
                   ({"_set_flag"}, [("_route", (), "_set_flag")])),
                  ("a match's case gives no selector",
                   setter + 'def _route(path, b):\n'
                            '    match path:\n'
                            '        case "/flag":\n'
                            '            _set_flag(b["id"])\n',
                   ({"_set_flag"}, [("_route", (), "_set_flag")])),
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
                   ({"_by_closure_path"}, [])))
        listed += tuple(("the comparison operator %s gives no selector" % op,
                         setter + 'def _route(path, b):\n'
                                  '    if path %s "/other":\n'
                                  '        _set_flag(b["id"])\n' % op,
                         ({"_set_flag"}, [("_route", (), "_set_flag")]))
                        for op in ("!=", "<", "<=", ">", ">=", "is", "is not", "in", "not in"))
        for label, src, expected in listed:
            with self.subTest(listed=label):
                self.assertEqual(census(src), expected,
                                 "EVERY SHAPE AND NARROWING RULE THE CENSUS DOCSTRING LISTS HAS A PLANT (round 4 of fork "
                                 "PR #897, the thirty-seventh to thirty-ninth commits): %s. A census that drops or changes "
                                 "the shape, or widens the rule, turns this plant red" % label)
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
        unseen = (("a path built by string concatenation",
                   'def _by_concatenation(cur):\n'
                   '    _atomic_write(jd.STATE / ("session-" + "flags.json"), cur)\n'),
                  ("a library function outside the doors, shutil.copy",
                   'def _by_library(tmp):\n'
                   '    shutil.copy(tmp, jd.STATE / "session-flags.json")\n'),
                  ("another process, a subprocess",
                   'def _by_subprocess(tmp):\n'
                   '    subprocess.run(["cp", tmp, str(jd.STATE / "session-flags.json")], check=True)\n'),
                  ("a path handed to a helper that writes its parameter",
                   'def _save(p, cur):\n'
                   '    _atomic_write(p, cur)\n'
                   'def _by_argument(cur):\n'
                   '    _save(jd.STATE / "session-flags.json", cur)\n'),
                  ("a name bound by unpacking into a tuple",
                   'def _by_unpacking(cur):\n'
                   '    base, p = jd.STATE, jd.STATE / "session-flags.json"\n'
                   '    p.write_text(cur)\n'),
                  ("a name bound by a for loop's target",
                   'def _by_loop(cur):\n'
                   '    for p in (jd.STATE / "session-flags.json",):\n'
                   '        p.write_text(cur)\n'),
                  ("a name bound by an assignment expression",
                   'def _by_walrus(cur):\n'
                   '    if (p := jd.STATE / "session-flags.json"):\n'
                   '        p.write_text(cur)\n'),
                  ("a name bound by a parameter's default",
                   'def _by_default(cur, p=jd.STATE / "session-flags.json"):\n'
                   '    p.write_text(cur)\n'),
                  ("a name bound by a comprehension's target",
                   'def _by_comprehension(cur):\n'
                   '    [p.write_text(cur) for p in (jd.STATE / "session-flags.json",)]\n'),
                  ("a name bound by a with statement's as",
                   'def _by_with(cur):\n'
                   '    with _held(jd.STATE / "session-flags.json") as p:\n'
                   '        p.write_text(cur)\n'),
                  ("a name bound by an assignment to an attribute",
                   'def _by_attribute_target(cur):\n'
                   '    store.p = jd.STATE / "session-flags.json"\n'
                   '    store.p.write_text(cur)\n'),
                  ("a path held in an attribute and written in another method",
                   'class Store:\n'
                   '    def __init__(self):\n'
                   '        self.p = jd.STATE / "session-flags.json"\n'
                   '    def _by_attribute(self, cur):\n'
                   '        self.p.write_text(cur)\n'),
                  ("a name bound in another outermost function through a global statement",
                   'def _init():\n'
                   '    global FLAGS_PATH\n'
                   '    FLAGS_PATH = jd.STATE / "session-flags.json"\n'
                   'def _by_global(cur):\n'
                   '    _atomic_write(FLAGS_PATH, cur)\n'))
        for label, src in unseen:
            with self.subTest(unseen=label):
                self.assertEqual(census(src), (set(), []),
                                 "WHAT THE CENSUS DOES NOT SEE, as its docstring discloses: %s writes the flags file and is not "
                                 "found. A census that reaches it turns this red, and the docstring's disclosure moves with it"
                                 % label)

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
        by the census above (_flag_writing_routes), are exactly POST /flag and the WebSocket arm, so a new route fails the
        set pin. Executed over the real handlers: the listing with thread rows has the thread and the roster omits it; a
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
            writers, refs = self._flag_writing_routes(f.read())
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
