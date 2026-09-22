#!/usr/bin/env python3
"""The census of every thread a test starts and HOW its stop is reached, derived by AST over tests/*.py (T282, the stop
shape, 2026-09-21). A thread a test starts must be ended by a construct that runs on EVERY exit path of the test, so a
failed assertion in the body cannot leave it running. This module reads each start, decides what the thread would do
if nobody stopped it (its KIND), reads how the test stops it (its SHAPE), and holds that no thread that would run on
or wait on the test has its stop only on the body's tail.

WHY (the mechanism found on 2026-09-21, romp-manager's verification). tests/test_kernel_parked_ops_liveness.py starts
a REAL kernel judge loop (km._producer) and stopped it on its body's last lines: km._LOOPS_STOP.set(), gate.set(),
km._producer_wake.set(), producer.join(5). Its assertion at the head of the body ("a judge pass is in flight") began
failing when kernel commit 3421c94d0 (2026-09-11) put an 8 s boot hold (BOOT_JUDGE_HOLD_S, _wait_boot_attached) in
front of the producer's first pass, against a test written 2026-09-03 that polled 5 s for the pass. The defect is a
CONDITION, not a frequency: _BOOT_ATTACHED (kernel/kernel.py:30789, set at :30860) is a one-way, process-wide latch,
never cleared, and the test patches km._sdk to lambda: None, so it can never latch it itself; the test passes if and
only if something earlier in the same interpreter already latched it, and fails otherwise after the 8 s hold against its
5 s deadline. Alone serially: always red. The module serially: green (its alphabetically first test's km._pusher_cycle()
reaches _sdk() through _turn_notify_tick and _alive_sessions and builds a real SdkBackend whose boot reconcile latches
it as a side effect). The module under -n 9: red. A full -n 10 sweep: a prior latcher in the target's worker is likely
but not guaranteed: five full sweeps checked on 2026-09-21 did not fire it (those for 853, 862 twice and 887, and 781's
at c7e51ae47), one did (box 2's control at 65f1895f6). An isolated-level certainty and a sweep-level flake at the same
time, decided by which tests ran before it in that worker's process; never in CI (serial). The failed assertion skipped the stop on
the tail, the tearDown only CLEARED the stop flag when the producer was already dead and never SET it, so a live,
fully UNPATCHED judge loop (the with-block's eleven patches were undone on the way out while the producer was still in
its hold) ran for the rest of the worker's life. The T282 census in tearDown named the leftover thread (the "1 error"
beside the "1 failed") but could not stop it.

THE BLAST RADIUS, proven by romp-manager's probe, has TWO FIGURES with different meanings. REACH: the leaked loop runs
_compact_goal_stores() on its 3 s backstop (_producer_wake.wait(3)), globbing jd.GOALDIR and rewriting any store whose
mtime moved; km.jd is the ONE process-wide judge module (kernel/kernel.py:52, jd = load_source("romp_judge", ...): one
object per interpreter; tests/conftest.py's shared-judge note), and 141 test modules call jd._rebind_state(), so the
leaked loop follows jd.GOALDIR to wherever the LATEST rebind put it: any of those 141 scheduled after the failure in the
same worker (a store saved under a private sid with a cleared root was archived 7.5 s later by the leaked thread).
VISIBLE SET: 13 modules save stores with cleared roots and 18 assert on the archive; that is where a wrong result would
surface, a SPURIOUS PASS as well as a spurious failure in a module that did nothing wrong, and the spurious pass is the
dangerous direction. 13 is not the exposure; 141 is the reach. NOT DETERMINED, carried and not dropped: whether the
leaked loop produced flakes in earlier sweeps. The contamination disclosure is CONDITIONAL: a sweep carried the leaked
loop only if the target's failure line is in that sweep's pytest log. The SdkBackend
side-effect build is benign on its own (its orphan reap is gated on its own empty registry; sweep_dead_test_roots
removes only romp-tests-* roots whose marker names a dead pid).

THE START SITES. A `.start()` call whose receiver the walk resolves to a Thread or Timer construction: by name, through
an alias (`from threading import Thread as Th`; a module-level or local `Real = threading.Thread`), or of a Thread
SUBCLASS defined in the module or in the function (its run() is what the thread does); chained (`Thread(...).start()`),
through a name bound in the same function (an assignment, a for-target or a comprehension target over a list of such, a
list appended to, an element of a dict or a list assigned by subscript, a conditional expression, a tuple unpacked from
a helper's return), through an attribute bound on self or cls anywhere in the class or a base in the same file, through
a module name, or through a HELPER whose return is such a construction (a module function, a method of the class, a
function of the body, a lambda: the target is read where the construction sits). The binding in force at a start is the
last one at or before it (`[... for t in range(8)]` and then `for t in threads: t.start()` reads the for's). A receiver
bound to a known non-thread (a mock patcher, a regex match, tracemalloc, an object of a product or library module such
as sb.SdkSession(...), whose start() is its own) is not a thread start; a receiver the walk cannot resolve (a parameter,
a call it cannot classify, a method the class does not define, a product Thread subclass) is UNREADABLE and LISTED,
never passed in silence.

THE KIND of a thread, read from its target: what it does if the test never stops it.
  loop:    it runs until told: serve_forever / run_forever; a function of the test module whose body has a `while`
           (a `while` bounded by a clock reading, in its test or by an `if <clock>: break` in its body, is not one), or
           that iterates `iter(f, sentinel)`, or that calls a product function that has one (INDIRECT evidence the walk
           cannot weigh: the product loop may well return, so for the timed-join rule below such a thread is read as
           bounded); a product function (kernel/, postal/, cli/, the bin scripts) whose body has a `while` (km._producer,
           _pusher, _heartbeat, _jobs_loop, _ws_sender, _apply_pending_ops, pm._heartbeat_loop).
  waits:   it blocks until the test releases it: the target is an untimed Event.wait / Lock.acquire / Queue.get / join,
           or a function of the test module that calls one with no timeout (or reads a socket or a pipe).
  bounded: everything else: a function of the test module with no loop and only timed waits, a product function with
           no `while`, a Timer (it fires once). Such a thread ends on its own whatever the test does, within its own
           bound, so its join is a convenience of the body and not the stop; the shape rule BOUNDED excuses it, with
           this as the reason. What the walk does not read: a product function that blocks in a read (km._login_reader
           reads a pty until its fd is closed) or in a lock is classed bounded because it has no `while`; the runtime
           oracle, tests/conftest.py's thread_census and wait_for_census in a module's own teardown, is what catches
           those.

THE SHAPE of the stop, read in this order; the first match names it. The walk forward from a start reads the
statements that follow it (climbing out of the for, the comprehension or the with that did the starting) up to the
FIRST ASSERTION (self.assert*, self.fail, a bare assert, a raise): a statement that is not an assertion is taken not to
fail, and the shape this census forbids is a stop that stands BEHIND an assertion, the shape that leaked.
  finally: the start is inside a try body that has a finally, or the walk forward meets such a try before any assertion
    (start, then `try: ... finally: stop`, the contextmanager idiom).
  cleanup-before-start: a cleanup (addCleanup, addClassCleanup, addfinalizer, addModuleCleanup, or a registrar handed in
    as a parameter whose name says cleanup) that names a stop OF THIS THREAD: its text, or the body of the local
    function, the lambda or the method of the class it names, has a stop (an attribute or call of join / set / shutdown /
    stop / close / cancel / terminate / kill, the loops' seam _LOOPS_STOP, a name that says stop / end / close) AND
    mentions the thread: its receiver (and the attribute or holder behind `self.x` or `h[k]`), the list a for-target
    iterates, what its target waits on or polls, its target and the object the target runs on (srv for
    srv.serve_forever), the names handed to it through args= / kwargs= (an Event a product loop is given), the loops'
    seam for a loop outside the module, or the attribute on self that holds it. A cleanup that stops another thread
    excuses nothing about this one: setUp's addCleanup(self.srv.shutdown) covers the server's serve_forever thread and no
    other start in the class. Registered at or before the start in the same function or in the class's setUp. unittest
    runs cleanups after tearDown, LIFO, on every exit path.
  cleanup-before-first-assertion: such a cleanup registered by a statement the walk forward meets before any assertion
    (`Thread(target=srv.serve_forever).start()` then `self.addCleanup(srv.shutdown)`).
  stop-before-first-assertion: the walk meets the stop itself before any assertion, in the start's own statement first
    (`t.start(), t.join()` in one) and then forward: a join of the same receiver or the same list (`for t in ts:
    t.start()` then `for t in ts: t.join()`), a shutdown / stop / cancel of it or of the object the target runs on
    (srv.shutdown() for srv.serve_forever; loop.stop handed to call_soon_threadsafe), a set or release of what the thread
    waits on or polls (`go.set()`), or the loops' seam set for a loop outside the module (km._LOOPS_STOP.set() for
    km._producer). A TIMED join of a loop thread is a wait the loop may outlive, not its stop: alone it is passed over,
    and the walk goes on to a release, a shutdown or the seam; an untimed join counts (a loop that did not end would
    hang the test, loudly).
  class-hook: the thread, the object its target runs on (target=self.srv.serve_forever), a local receiver the body
    stores on self (self.loops.append(loop)), or the attribute a helper's result is assigned to (self.bus = _serve(...))
    is on self or cls, and a hook of the class or a base in the same file (tearDown, tearDownClass, a cleanup registered
    in setUp or setUpClass, tearDownModule) applies a stop verb to it, as a call or as a callback handed over
    (loop.call_soon_threadsafe(loop.stop)), or sets _LOOPS_STOP.
  object-owned: the start is in a method of a fake (a class that is not a TestCase), and the class has an end method
    (close, stop, shutdown, __exit__, end, drain, terminate, kill) that applies a stop verb: the fake owns its thread and
    ends it when the test ends the fake. The second hop, that every test ends the fake on every path, is not read here.
  allowlisted: an entry in ALLOW, one site each, with its reason; an entry that matches no tail-only site is STALE and
    fails the census, so the list cannot outlive the sites it excuses.
  tail-only: none of the above: the stop, if the body has one, stands behind an assertion. For a loop or a waits thread
    this set is asserted EMPTY.
A helper that starts a thread and is not itself a test (a `_start`, a `_pass`, a `_wire`) is classed in its own body
first; when its own body has no guarantee, each caller in the same class is classed at its call (a cleanup registered
before the call, the walk forward from the call, the attribute the call's result is stored on against the caller's
hooks), and the site is named at the caller.

WHAT THIS CENSUS DOES NOT SEE. The shape rules read constructs and not their meaning: a cleanup that names the
thread and a stop verb whose stop does not reach it (a set of an event the loop stopped reading), a finally that does
not join, a tearDown or a cleanup whose only stop of a loop thread is a timed join (the thread is waited for on every
exit path; whether the loop ended within the bound is the oracle's to say: the timed-join rule reads the body's forward
walk, not the hooks), an end method no test calls, are all classed as guaranteed here and caught only by the runtime
oracle. A thread started
by code outside tests/*.py (a kernel helper that spawns its own worker; a product object's own start(), as
sb.SdkSession(...).start()) is the product's to end. Run the module directly for the table (`--table`; `--tail` prints
only the tail-only and unreadable rows).
"""
import ast
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

THREAD_CTORS = ("Thread", "Timer")
STOP_VERBS = ("join", "set", "shutdown", "stop", "close", "cancel", "terminate", "kill", "server_close", "release")
STOP_SEAM = "_LOOPS_STOP"
STOP_WORDS = ("stop", "end", "close", "shutdown", "cancel", "join", "release")
CLEANUP_NAMES = ("addCleanup", "addClassCleanup", "addfinalizer", "addModuleCleanup")
HOOK_NAMES = ("setUp", "tearDown", "setUpClass", "tearDownClass", "setUpModule", "tearDownModule")
OWNER_ENDS = ("close", "stop", "shutdown", "__exit__", "end", "drain", "terminate", "kill")
BLOCKING = ("wait", "acquire", "join", "get")            # untimed when called with no arguments
BUILTIN_METHODS = ("append", "extend", "add", "update", "get", "put", "pop", "setdefault", "insert", "remove", "discard",
                   "clear", "copy", "keys", "items", "values", "sort", "reverse", "index", "count", "join", "split", "strip",
                   "format", "encode", "decode", "write", "read", "flush", "set", "wait", "acquire", "release", "is_set", "start")
ASSERTS = ("fail", "failIf", "failUnless", "skipTest")
READS = ("recv", "recv_into", "recvfrom", "accept", "readline", "read")
FOREVER = ("serve_forever", "run_forever")
CLOCK = re.compile(r"\btime\.|monotonic|perf_counter|deadline|thread_time")
PRODUCT_DIRS = ("kernel", "postal", "cli")
KINDS_PINNED = ("loop", "waits")
# Receivers whose start() is known not to be a thread of ours: a mock patcher (mock.patch, patch.object, patch.dict), a
# regex match (re.finditer / match / search), the tracemalloc module. Any other call the walk cannot read is UNREADABLE.
NON_THREAD_HEADS = ("re", "regex", "tracemalloc")
NON_THREAD_PARTS = ("patch",)
NON_THREAD_ATTRS = ("finditer", "match", "search", "fullmatch", "compile")

# Shapes that are not leaks, excused one site at a time. Key: (file, unit the shape was read in, the target's text);
# value: the reason. Every entry must match a site the walk classes tail-only at this head, or the entry is stale and
# the census is red.
ALLOW = {
}


def _callee_name(call):
    f = call.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def _names_thread_ctor(node):
    """The expression is threading.Thread / Timer by name: `threading.Thread`, `Thread`, `_real_threading.Timer`."""
    if isinstance(node, ast.Attribute):
        return node.attr in THREAD_CTORS
    if isinstance(node, ast.Name):
        return node.id in THREAD_CTORS
    return False


def _is_thread_ctor(node):
    """A Thread or Timer construction by NAME only (no aliases, no subclasses): the unit-aware check is _Unit.is_thread_ctor."""
    return isinstance(node, ast.Call) and _callee_name(node) in THREAD_CTORS


def _target_expr(call):
    """The callable a Thread or Timer runs: `target=` (or the first positional) for Thread, `function=` (or the second
    positional) for Timer."""
    if _callee_name(call) == "Timer":
        for kw in call.keywords:
            if kw.arg == "function":
                return kw.value
        return call.args[1] if len(call.args) > 1 else None
    for kw in call.keywords:
        if kw.arg == "target":
            return kw.value
    return call.args[0] if call.args else None


def _has_args(call):
    return any(kw.arg in ("args", "kwargs") for kw in call.keywords) or len(call.args) > 1


def _stop_shaped(node):
    """The node (a cleanup's argument, a local function, a lambda) names a stop: an attribute or call of a stop verb, the
    loops' stop seam, or a bare name that says stop."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute) and sub.attr in STOP_VERBS:
            return True
        if isinstance(sub, ast.Name) and (sub.id == STOP_SEAM or any(w in sub.id.lower() for w in STOP_WORDS)):
            return True
    return False


def _expr_children(stmt):
    """The expression nodes of one statement, not descending into the statements it holds."""
    for child in ast.iter_child_nodes(stmt):
        if isinstance(child, ast.stmt):
            continue
        yield from ast.walk(child)


def _run_nodes(stmt):
    """The nodes of a statement that run when it does: not the bodies of the functions, lambdas and classes it defines."""
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return                                          # a definition: nothing of its body runs here
    stack = [stmt]
    while stack:
        n = stack.pop()
        yield n
        for c in ast.iter_child_nodes(n):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            stack.append(c)


def _returns(fn):
    """The value of every `return` of the function's OWN body (not of the functions it defines)."""
    for s in fn.body:
        for n in _run_nodes(s):
            if isinstance(n, ast.Return) and n.value is not None:
                yield n.value


def _join_kinds(kinds):
    """One answer for a set of element answers: a thread among them makes the whole a thread; an unread element makes it
    unread; all read and none a thread is other; no elements is empty."""
    if "thread" in kinds:
        return "thread"
    if None in kinds:
        return None
    return "other" if kinds else "empty"


def _word_in(word, text):
    """`word` appears in `text` as a whole name (`producer` in `self.producer.join(10)`; not in `_producer_wake`)."""
    return re.search(r"(?<!\w)%s(?!\w)" % re.escape(word), text) is not None


def product_loops(root=ROOT):
    """The name of every function in the product sources whose body has a `while`: kernel/, postal/, cli/ and the bin
    scripts that are files of their own (the rest of bin/ are links into those directories)."""
    names = set()
    for tree in _product_trees(root):
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(isinstance(s, ast.While) for s in ast.walk(n)):
                names.add(n.name)
    return names


def product_thread_classes(root=ROOT):
    """The name of every class in the product sources whose bases name threading.Thread: a construction of one by a test
    (km.Worker(...).start()) is a thread the walk does not read the target of, so it is listed unreadable."""
    names = set()
    for tree in _product_trees(root):
        for n in ast.walk(tree):
            if isinstance(n, ast.ClassDef) and any(_names_thread_ctor(b) for b in n.bases):
                names.add(n.name)
    return names


def _product_trees(root):
    files = []
    for d in PRODUCT_DIRS:
        p = os.path.join(root, d)
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in os.listdir(p) if f.endswith(".py")]
    b = os.path.join(root, "bin")
    if os.path.isdir(b):
        for f in os.listdir(b):
            p = os.path.join(b, f)
            if os.path.isfile(p) and not os.path.islink(p):
                with open(p, "rb") as fh:
                    head = fh.readline()
                if head.startswith(b"#!") and b"python" in head:
                    files.append(p)
    for p in files:
        try:
            yield ast.parse(open(p, encoding="utf-8").read(), p)
        except (SyntaxError, UnicodeDecodeError):
            continue


class _Module:
    def __init__(self, path, loops, src=None, thread_classes=None):
        self.path = path
        self.loops = loops
        self.product_thread_classes = set() if thread_classes is None else thread_classes
        self.src = open(path, encoding="utf-8").read() if src is None else src
        self.tree = ast.parse(self.src, path)
        self.classes = {n.name: n for n in self.tree.body if isinstance(n, ast.ClassDef)}
        self.functions = {n.name: n for n in self.tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.globals, self.imports = {}, set()
        self.thread_aliases = set()          # names bound at module level to threading.Thread / Timer
        for n in ast.walk(self.tree):
            if isinstance(n, ast.Import):
                self.imports.update((a.asname or a.name).split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                self.imports.update(a.asname or a.name for a in n.names)
                if n.module == "threading":                          # from threading import Thread as Th
                    self.thread_aliases.update(a.asname or a.name for a in n.names if a.name in THREAD_CTORS)
        for n in self.tree.body:
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        self.globals[t.id] = n.value
        su = self.functions.get("setUpModule")
        if su is not None:                                   # setUpModule's `global x; x = ...` binds module names too
            declared = {nm for s in ast.walk(su) if isinstance(s, ast.Global) for nm in s.names}
            for s in ast.walk(su):
                if isinstance(s, ast.Assign):
                    for t in s.targets:
                        if isinstance(t, ast.Name) and t.id in declared:
                            self.globals[t.id] = s.value
        for name, value in self.globals.items():                     # Th = threading.Thread
            if _names_thread_ctor(value):
                self.thread_aliases.add(name)
        self.thread_classes = {}             # module classes whose bases (here, transitively) name Thread or an alias of it
        for name, c in self.classes.items():
            if self.derives_thread(c):
                self.thread_classes[name] = c
        self._units = None
        self._unit_of = {}

    def base_names_thread(self, base, local_aliases=()):
        """The base expression names Thread / Timer, an alias of it (module-level or handed in), or a module class that
        derives from it."""
        if _names_thread_ctor(base):
            return True
        return isinstance(base, ast.Name) and (base.id in self.thread_aliases or base.id in local_aliases
                                               or base.id in self.thread_classes)

    def derives_thread(self, cls, local_aliases=(), local_classes=None):
        """The class or a base of it in this file (or a local class handed in) has a base that names Thread / Timer or an
        alias of it."""
        seen, q = set(), [cls]
        while q:
            c = q.pop(0)
            if c.name in seen:
                continue
            seen.add(c.name)
            for b in c.bases:
                if self.base_names_thread(b, local_aliases):
                    return True
                nm = ast.unparse(b).split(".")[-1]
                nxt = (local_classes or {}).get(nm) or self.classes.get(nm)
                if nxt is not None:
                    q.append(nxt)
        return False

    def bases_of(self, cls):
        """The class and its bases in this file, nearest first."""
        out, q, seen = [], [cls], set()
        while q:
            c = q.pop(0)
            if c.name in seen:
                continue
            seen.add(c.name)
            out.append(c)
            for b in c.bases:
                nm = ast.unparse(b).split(".")[-1]
                if nm in self.classes:
                    q.append(self.classes[nm])
        return out

    def is_testcase(self, cls):
        return any(ast.unparse(b).split(".")[-1] == "TestCase" for c in self.bases_of(cls) for b in c.bases)

    def methods_of(self, cls, name):
        return [f for c in self.bases_of(cls) for f in c.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == name]

    def units(self):
        """Every function the walk classes on its own: module-level functions and every method of every class."""
        if self._units is None:
            out = []
            for f in self.tree.body:
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append(_Unit(self, None, f))
            for c in self.tree.body:
                if isinstance(c, ast.ClassDef):
                    for f in c.body:
                        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            out.append(_Unit(self, c, f))
            self._units = out
            for u in out:
                self._unit_of[id(u.fn)] = u
        return self._units

    def unit_for(self, fn, cls=None, parent=None):
        """The unit that reads `fn`: the module's own for a top-level function or a method, else one built for a function
        defined inside another (its free names resolve through `parent`)."""
        self.units()
        u = self._unit_of.get(id(fn))
        if u is None:
            u = _Unit(self, cls, fn, parent=parent)
            self._unit_of[id(fn)] = u
        return u


def _stmts(body, stack, out):
    """Every statement in `body`, recursively, with the block holding it, its index there and the compound statements
    enclosing it, outermost first."""
    for i, s in enumerate(body):
        out.append((s, body, i, tuple(stack)))
        for field in ("body", "orelse", "finalbody"):
            sub = getattr(s, field, None)
            if isinstance(sub, list) and sub and isinstance(sub[0], ast.stmt):
                _stmts(sub, stack + [(s, field)], out)
        for h in getattr(s, "handlers", []) or []:
            _stmts(h.body, stack + [(s, "handler")], out)
        for c in getattr(s, "cases", []) or []:
            _stmts(c.body, stack + [(s, "case")], out)


class _Unit:
    def __init__(self, module, cls, fn, parent=None):
        self.module, self.cls, self.fn, self.parent = module, cls, fn, parent
        self.qualname = ("%s.%s" % (cls.name, fn.name)) if cls is not None else fn.name
        self.params = {a.arg for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs}
        self.rows = []
        _stmts(fn.body, [], self.rows)
        self.row_of = {id(s): (s, block, i, stack) for s, block, i, stack in self.rows}
        self.owner, self.parent_node = {}, {}
        for s, _b, _i, _st in self.rows:
            for child in ast.iter_child_nodes(s):
                if isinstance(child, ast.stmt):
                    continue
                self.parent_node.setdefault(id(child), s)
                for node in ast.walk(child):
                    self.owner.setdefault(id(node), s)
                    for sub in ast.iter_child_nodes(node):
                        self.parent_node.setdefault(id(sub), node)
        self.bindings = {}          # name or attribute text -> [(line, value)], in source order: the binding in force at a
        self.appends = {}           # use is the last one at or before the use's line (a name reused across loops rebinds)
        for s, _b, _i, _st in self.rows:
            self._bind(s)
        self.local_defs = {}
        self.local_classes = {}
        for s, _b, _i, _st in self.rows:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.local_defs.setdefault(s.name, s)
            elif isinstance(s, ast.ClassDef):
                self.local_classes.setdefault(s.name, s)
        self.thread_aliases = {nm for nm, vals in self.bindings.items()          # Real = threading.Thread, in the body
                               if any(not isinstance(v, tuple) and _names_thread_ctor(v) for _l, v in vals)}
        self.thread_classes = {nm: c for nm, c in self.local_classes.items()     # class W(threading.Thread), in the body
                               if module.derives_thread(c, self.thread_aliases | module.thread_aliases, self.local_classes)}

    # ── bindings ──

    def _bind(self, s):
        if isinstance(s, ast.Assign):
            for t in s.targets:
                self._bind_target(t, s.value, s.lineno)
        elif isinstance(s, ast.AnnAssign) and s.value is not None:
            self._bind_target(s.target, s.value, s.lineno)
        elif isinstance(s, ast.AugAssign) and isinstance(s.op, ast.Add):          # self.threads += [peer, handler]
            holder = ast.unparse(s.target)
            for v in (s.value.elts if isinstance(s.value, (ast.List, ast.Tuple)) else [s.value]):
                self.appends.setdefault(holder, []).append(v)
        elif isinstance(s, (ast.For, ast.AsyncFor)):
            self._bind_target(s.target, ("for", s.iter), s.lineno)
        elif isinstance(s, (ast.With, ast.AsyncWith)):
            for it in s.items:
                if it.optional_vars is not None:
                    self._bind_target(it.optional_vars, ("with", it.context_expr), s.lineno)
        for sub in _expr_children(s):
            if isinstance(sub, ast.NamedExpr):
                self._bind_target(sub.target, sub.value, s.lineno)
            elif isinstance(sub, ast.comprehension):
                self._bind_target(sub.target, ("for", sub.iter), s.lineno)
            elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in ("append", "add") and sub.args:
                self.appends.setdefault(ast.unparse(sub.func.value), []).append(sub.args[0])

    def _bind_target(self, t, value, line):
        if isinstance(t, ast.Name):
            self.bindings.setdefault(t.id, []).append((line, value))
        elif isinstance(t, ast.Attribute):
            self.bindings.setdefault(ast.unparse(t), []).append((line, value))
        elif isinstance(t, ast.Subscript):                                          # holder["a"] = Thread(...): the element
            self.bindings.setdefault(ast.unparse(t), []).append((line, value))    # by its text, and as one of the holder's
            self.appends.setdefault(ast.unparse(t.value), []).append(value)
        elif isinstance(t, (ast.Tuple, ast.List)):
            if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(t.elts):
                for e, v in zip(t.elts, value.elts):
                    self._bind_target(e, v, line)
            else:
                for i, e in enumerate(t.elts):
                    self._bind_target(e, ("unpack", value, i), line)

    def binding_at(self, text, line):
        """(line, value) of the binding of `text` in force at `line`: the last one at or before it, else the first one after
        it (a use inside a loop body ahead of the rebinding), else the enclosing function's, else None."""
        vals = self.bindings.get(text)
        if vals:
            before = [lv for lv in vals if lv[0] <= line]
            return before[-1] if before else vals[0]
        if self.parent is not None:
            return self.parent.binding_at(text, line)
        return None

    def class_bindings(self, attr):
        """Every value bound to `self.<attr>` / `cls.<attr>` by any spelling across the class and its bases (an assignment,
        an element assigned by subscript, a += of a list), plus every `.append(v)` into it."""
        if self.cls is None:
            return []
        out = []
        for c in self.module.bases_of(self.cls):
            for sub in ast.walk(c):
                if isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Attribute) and t.attr == attr:
                            out.append(sub.value)
                        elif isinstance(t, ast.Subscript) and isinstance(t.value, ast.Attribute) and t.value.attr == attr:
                            out.append(sub.value)
                elif isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Attribute) and sub.target.attr == attr:
                    out += sub.value.elts if isinstance(sub.value, (ast.List, ast.Tuple)) else [sub.value]
                elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in ("append", "add") \
                        and isinstance(sub.func.value, ast.Attribute) and sub.func.value.attr == attr and sub.args:
                    out.append(sub.args[0])
        return out

    # ── what a call constructs ──

    def is_thread_ctor(self, node, line=None):
        """A Thread / Timer construction: by name, through an alias (`from threading import Thread as Th`, a module-level or
        local `Real = threading.Thread`), or of a Thread subclass defined in this module or in this function."""
        if not isinstance(node, ast.Call):
            return False
        f = node.func
        if _names_thread_ctor(f):
            return True
        if isinstance(f, ast.Name):
            if f.id in self.module.thread_aliases or f.id in self.thread_aliases:
                return True
            if f.id in self.thread_classes or f.id in self.module.thread_classes:
                return True
            if self.parent is not None and (f.id in self.parent.thread_aliases or f.id in self.parent.thread_classes):
                return True
        return False

    def thread_class_of(self, call):
        """The ClassDef when the construction is of a Thread subclass defined in this module or this function."""
        f = call.func
        if isinstance(f, ast.Name):
            for scope in (self, self.parent):
                if scope is not None and f.id in scope.thread_classes:
                    return scope.thread_classes[f.id]
            return self.module.thread_classes.get(f.id)
        return None

    def run_method_of(self, cls):
        """The `run` method of a Thread subclass, in the class or a base of it defined in this module or this function."""
        seen, q = set(), [cls]
        while q:
            c = q.pop(0)
            if c.name in seen:
                continue
            seen.add(c.name)
            for f in c.body:
                if isinstance(f, ast.FunctionDef) and f.name == "run":
                    return f
            for b in c.bases:
                nm = ast.unparse(b).split(".")[-1]
                nxt = self.local_classes.get(nm) or (self.parent.local_classes.get(nm) if self.parent else None) or self.module.classes.get(nm)
                if nxt is not None:
                    q.append(nxt)
        return None

    def callee_of(self, call, line):
        """(function or lambda, the unit that reads it) for a call of a function defined in this function, a module
        function, a method of the class (self.x() / cls.x()), or a name bound to a lambda; None for anything else."""
        f = call.func
        if isinstance(f, ast.Name):
            for scope in (self, self.parent):
                if scope is not None and f.id in scope.local_defs:
                    fn = scope.local_defs[f.id]
                    return fn, self.module.unit_for(fn, scope.cls, parent=scope)
            if f.id in self.module.functions:
                fn = self.module.functions[f.id]
                return fn, self.module.unit_for(fn)
            b = self.binding_at(f.id, line)
            if b is not None and isinstance(b[1], ast.Lambda):
                return b[1], self
            g = self.module.globals.get(f.id)
            if isinstance(g, ast.Lambda):
                return g, self
            return None
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in ("self", "cls") and self.cls is not None:
            ms = self.module.methods_of(self.cls, f.attr)
            if ms:
                return ms[0], self.module.unit_for(ms[0], self.cls)
        return None

    def known_non_thread(self, call):
        """The call constructs something whose start() is not a thread of ours: a mock patcher, a regex match, the
        tracemalloc module, or an object of a product or library module (sb.SdkSession(...), socket.socket()): a product
        Thread subclass is the exception, listed unreadable so the walk is extended rather than silent."""
        parts = ast.unparse(call.func).split(".")
        if parts[0] in NON_THREAD_HEADS or any(p in NON_THREAD_PARTS for p in parts) or parts[-1] in NON_THREAD_ATTRS:
            return True
        if len(parts) >= 2 and isinstance(call.func, ast.Attribute):
            head = parts[0]
            g = self.module.globals.get(head)
            if head in self.module.imports or isinstance(g, (ast.Call, ast.Attribute)):
                return parts[-1] not in self.module.product_thread_classes
        return False

    # ── what a receiver is ──

    def resolve(self, node, line, depth=0):
        """'thread' when the expression is (or is bound to) a Thread/Timer construction, 'other' when it is bound to
        something else the walk can read, 'empty' for an empty container, None when it cannot read it."""
        if depth > 8 or node is None:
            return None
        if isinstance(node, tuple):
            kind, inner = node[0], node[1]
            if kind == "for":
                return self.resolve(inner, line, depth + 1)
            if kind == "with":
                return "other"
            if kind == "unpack":                                    # t, ev = helper(): the helper's returned tuple, by position
                callee = self.callee_of(inner, line) if isinstance(inner, ast.Call) else None
                if callee is None:
                    return None
                fn, u = callee
                kinds = set()
                for v in (_returns(fn) if not isinstance(fn, ast.Lambda) else [fn.body]):
                    if isinstance(v, (ast.Tuple, ast.List)) and len(v.elts) > node[2]:
                        kinds.add(u.resolve(v.elts[node[2]], v.lineno, depth + 1))
                    else:
                        kinds.add(None)
                return _join_kinds(kinds) if kinds else None
            return None
        if isinstance(node, ast.Call):
            if self.is_thread_ctor(node, line):
                return "thread"
            callee = self.callee_of(node, line)
            if callee is not None:                                  # a helper: what its returns resolve to, in its own unit
                fn, u = callee
                if isinstance(fn, ast.Lambda):
                    return u.resolve(fn.body, fn.lineno, depth + 1)
                vals = list(_returns(fn))
                if not vals:
                    return "other"                                  # returns None: nothing to start
                return _join_kinds({u.resolve(v, v.lineno, depth + 1) for v in vals})
            return "other" if self.known_non_thread(node) else None
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return _join_kinds({self.resolve(e, line, depth + 1) for e in node.elts})
        if isinstance(node, ast.Dict):
            return _join_kinds({self.resolve(v, line, depth + 1) for v in node.values if v is not None})
        if isinstance(node, ast.BoolOp):
            return _join_kinds({self.resolve(e, line, depth + 1) for e in node.values})
        if isinstance(node, ast.IfExp):
            return _join_kinds({self.resolve(node.body, line, depth + 1), self.resolve(node.orelse, line, depth + 1)})
        if isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            return self.resolve(node.elt, line, depth + 1)
        if isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)):
            text = node.id if isinstance(node, ast.Name) else ast.unparse(node)
            b = self.binding_at(text, line)
            if b is not None:
                r = self.resolve(b[1], b[0], depth + 1)
                if r == "empty" or (r is None and text in self.appends):
                    return self._appended(text, depth)
                return r
            if text in self.appends:
                return self._appended(text, depth)
            if isinstance(node, ast.Name):
                if node.id in self.module.globals:
                    g = self.module.globals[node.id]
                    r = self.resolve(g, g.lineno, depth + 1)
                    return self._appended(text, depth) if r == "empty" else r
                if node.id in self.module.imports or node.id in self.module.functions or node.id in self.module.classes:
                    return "other"                                  # a module, a function, a class: no thread of ours
                return None
            if isinstance(node, ast.Attribute):
                vals = self.class_bindings(node.attr)
                if vals:
                    r = _join_kinds({self.resolve(v, v.lineno, depth + 1) for v in vals})
                    return "other" if r == "empty" else r
                if isinstance(node.value, ast.Name) and (node.value.id in self.module.globals or node.value.id in self.module.imports):
                    return "other"      # a module object's attribute (mock.patch, tracemalloc.start): never a thread of ours
                return None
            r = self.resolve(node.value, line, depth + 1)           # a subscript of a container the walk read
            if r in ("empty", None) and ast.unparse(node.value) in self.appends:
                return self._appended(ast.unparse(node.value), depth)
            return r if r in ("thread", "other") else None
        if isinstance(node, (ast.Constant, ast.JoinedStr, ast.BinOp, ast.Compare, ast.Lambda, ast.UnaryOp)):
            return "other"
        return None

    def _appended(self, holder, depth):
        kinds = {self.resolve(v, v.lineno, depth + 1) for v in self.appends.get(holder, [])}
        return _join_kinds(kinds) if kinds else None

    def thread_of(self, node, line, depth=0):
        """(the construction, the unit it is read in) behind a start receiver, following the same roads as resolve."""
        if depth > 8 or node is None:
            return None
        if isinstance(node, tuple):
            if node[0] == "for":
                return self.thread_of(node[1], line, depth + 1)
            if node[0] == "unpack" and isinstance(node[1], ast.Call):
                callee = self.callee_of(node[1], line)
                if callee is not None:
                    fn, u = callee
                    for v in (_returns(fn) if not isinstance(fn, ast.Lambda) else [fn.body]):
                        if isinstance(v, (ast.Tuple, ast.List)) and len(v.elts) > node[2]:
                            r = u.thread_of(v.elts[node[2]], v.lineno, depth + 1)
                            if r:
                                return r
            return None
        if isinstance(node, ast.Call):
            if self.is_thread_ctor(node, line):
                return node, self
            callee = self.callee_of(node, line)
            if callee is not None:
                fn, u = callee
                for v in (_returns(fn) if not isinstance(fn, ast.Lambda) else [fn.body]):
                    r = u.thread_of(v, v.lineno, depth + 1)
                    if r:
                        return r
            return None
        elts = None
        if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.BoolOp)):
            elts = node.elts if not isinstance(node, ast.BoolOp) else node.values
        elif isinstance(node, ast.Dict):
            elts = [v for v in node.values if v is not None]
        elif isinstance(node, ast.IfExp):
            elts = [node.body, node.orelse]
        elif isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            elts = [node.elt]
        if elts is not None:
            for e in elts:
                r = self.thread_of(e, line, depth + 1)
                if r:
                    return r
            return None
        if isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)):
            text = node.id if isinstance(node, ast.Name) else ast.unparse(node)
            b = self.binding_at(text, line)
            if b is not None:
                r = self.thread_of(b[1], b[0], depth + 1)
                if r:
                    return r
            for v in self.appends.get(text, []):
                r = self.thread_of(v, v.lineno, depth + 1)
                if r:
                    return r
            if isinstance(node, ast.Name) and node.id in self.module.globals:
                g = self.module.globals[node.id]
                return self.thread_of(g, g.lineno, depth + 1)
            if isinstance(node, ast.Attribute):
                for v in self.class_bindings(node.attr):
                    r = self.thread_of(v, v.lineno, depth + 1)
                    if r:
                        return r
            if isinstance(node, ast.Subscript):
                r = self.thread_of(node.value, line, depth + 1)
                if r:
                    return r
                for v in self.appends.get(ast.unparse(node.value), []):
                    r = self.thread_of(v, v.lineno, depth + 1)
                    if r:
                        return r
        return None

    # ── the starts ──

    def starts(self):
        """Every `.start()` in the unit whose receiver resolves to a thread, or to nothing the walk can read."""
        out = []
        for s, block, i, stack in self.rows:
            for sub in _expr_children(s):
                if not (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "start"
                        and not sub.args and not sub.keywords):
                    continue
                if self._value_used(sub):
                    continue            # `m.start() - width`, `heads[-1].start()` in a subscript: a regex match, not a thread
                recv = sub.func.value
                kind = self.resolve(recv, sub.lineno)
                if kind in ("other", "empty"):
                    continue
                found = self.thread_of(recv, sub.lineno) if kind == "thread" else None
                ctor, ctor_unit = found if found else (None, self)
                out.append(_Start(self, sub, recv, ctor, ctor_unit, s, block, i, stack, kind == "thread" and ctor is not None))
        return out

    def _value_used(self, call):
        """The call's value is consumed (an operand, a subscript, an argument, an assigned value): Thread.start() returns
        None, so this is some other object's start()."""
        p = self.parent_node.get(id(call))
        while p is not None and isinstance(p, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.Tuple, ast.List, ast.Lambda, ast.IfExp, ast.BoolOp)):
            if isinstance(p, ast.Lambda):
                return False
            p = self.parent_node.get(id(p))
        return not (p is None or isinstance(p, ast.Expr))

    def forward(self, stmt):
        """The statements that run after `stmt`, in order: the rest of its block, then, when the block is the body of a
        for, a with, an if or a try without a finally, the rest of the block holding that, climbing."""
        s = stmt
        while True:
            row = self.row_of.get(id(s))
            if row is None:
                return
            _s, block, i, stack = row
            yield from block[i + 1:]
            if not stack:
                return
            parent, field = stack[-1]
            if isinstance(parent, (ast.For, ast.AsyncFor, ast.With, ast.AsyncWith, ast.If)) and field in ("body", "orelse"):
                s = parent
                continue
            if isinstance(parent, ast.Try) and field == "body" and not parent.finalbody:
                s = parent
                continue
            return

    def assigned_attrs(self, stmt):
        """The self/cls attributes an assignment statement stores its value in (self.bus, self.ver = _serve(), _serve())."""
        out = []
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                for node in ast.walk(t):
                    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in ("self", "cls"):
                        out.append(node.attr)
        return out

    def hooks(self):
        """(name, FunctionDef) for every hook of the class and its bases, plus the module's tearDownModule."""
        out = []
        if self.cls is not None:
            for c in self.module.bases_of(self.cls):
                for f in c.body:
                    if isinstance(f, ast.FunctionDef) and f.name in HOOK_NAMES:
                        out.append((f.name, f))
        for nm in ("tearDownModule", "setUpModule"):
            if nm in self.module.functions:
                out.append((nm, self.module.functions[nm]))
        return out

    def callers(self):
        """(unit, call, statement, block, index, stack) for every call of this unit by name from the same class, a
        subclass in this file, or the module."""
        out = []
        for u in self.module.units():
            if u.fn is self.fn:
                continue
            if self.cls is not None and (u.cls is None or self.cls not in self.module.bases_of(u.cls)):
                continue
            for s, block, i, stack in u.rows:
                for sub in _expr_children(s):
                    if isinstance(sub, ast.Call) and _callee_name(sub) == self.fn.name:
                        out.append((u, sub, s, block, i, stack))
        return out


class _Start:
    def __init__(self, unit, call, recv, ctor, ctor_unit, stmt, block, index, stack, is_thread):
        self.unit, self.call, self.recv, self.ctor, self.ctor_unit = unit, call, recv, ctor, ctor_unit
        self.stmt, self.block, self.index, self.stack = stmt, block, index, stack
        self.is_thread = is_thread
        self.recv_text = ast.unparse(recv)
        self.subclass = ctor_unit.thread_class_of(ctor) if ctor is not None else None
        if self.subclass is not None:                 # a Thread subclass: its run() is what the thread does
            run = ctor_unit.run_method_of(self.subclass)
            self.target_expr = run
            self.target = "%s.run" % self.subclass.name if run is not None else "%s (no run)" % self.subclass.name
        else:
            self.target_expr = _target_expr(ctor) if ctor is not None else None
            self.target = ast.unparse(self.target_expr) if self.target_expr is not None else "?"
        self.line = call.lineno
        self._words = {}
        self.kind, self.why = ("?", "") if ctor is None else _kind(self)
        # a test function that CALLS a product function with a while (run -> em.hydrate) is loop-kind by evidence the
        # walk cannot weigh (the product loop may well return): for the timed-join rule it is read as bounded
        self.indirect = self.kind == "loop" and self.why.startswith("calls ") and "product function" in self.why

    def words(self, extra=()):
        """_thread_words, memoised per caller binding (`extra`)."""
        key = tuple(extra)
        if key not in self._words:
            self._words[key] = _thread_words(self, extra)
        return self._words[key]

    def file(self):
        return os.path.relpath(self.unit.module.path, ROOT)

    def describe(self):
        if self.ctor is None:
            return "%s:%d %s calls %s.start()" % (self.file(), self.line, self.unit.qualname, self.recv_text)
        return "%s:%d %s starts Thread(target=%s) via %s.start()" % (self.file(), self.line, self.unit.qualname, self.target, self.recv_text)


# ── the kind of a thread ────────────────────────────────────────────────────────────────────────────────

def _body_kind(unit, fn_body_nodes, loops, depth):
    """The kind a function body gives its thread: loop, waits or bounded, with the reason."""
    for sub in fn_body_nodes:
        if isinstance(sub, ast.While):
            if CLOCK.search(ast.unparse(sub.test)) or _clock_break(sub):
                continue
            return "loop", "a while loop"
        if isinstance(sub, (ast.For, ast.AsyncFor)) and isinstance(sub.iter, ast.Call) and _callee_name(sub.iter) == "iter" and len(sub.iter.args) == 2:
            return "loop", "iterates iter(f, sentinel)"
    for sub in fn_body_nodes:
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr in BLOCKING and not sub.args and not sub.keywords:
                return "waits", "an untimed .%s()" % sub.func.attr
            if sub.func.attr in READS:
                return "waits", "a read of .%s()" % sub.func.attr
            if sub.func.attr in FOREVER:
                return "loop", sub.func.attr
    if depth < 2:
        for sub in fn_body_nodes:
            if isinstance(sub, ast.Call):
                nm = _callee_name(sub)
                fn = unit.local_defs.get(nm) or (unit.parent.local_defs.get(nm) if unit.parent is not None else None)
                if fn is not None:
                    k, why = _body_kind(unit, list(ast.walk(fn)), loops, depth + 1)
                    if k != "bounded":
                        return k, "calls %s, %s" % (nm, why)
                elif nm in unit.module.functions:
                    k, why = _body_kind(unit, list(ast.walk(unit.module.functions[nm])), loops, depth + 1)
                    if k != "bounded":
                        return k, "calls %s, %s" % (nm, why)
                elif nm in loops and nm not in BUILTIN_METHODS and _product_call(unit, sub):
                    return "loop", "calls %s, a product function with a while loop" % nm
    return "bounded", "no loop, no untimed wait"


def _clock_break(loop):
    """The while's body leaves it on a clock reading (`if time.monotonic() > deadline: break`): bounded, as a while whose
    test reads the clock is."""
    for sub in ast.walk(loop):
        if isinstance(sub, ast.If) and CLOCK.search(ast.unparse(sub.test)) \
                and any(isinstance(n, (ast.Break, ast.Return)) for b in sub.body for n in ast.walk(b)):
            return True
    return False


def _is_module_alias(unit, node):
    """The name is a module object: an import, or a module-level name bound to a call or an attribute (km = load_source(...))."""
    if not isinstance(node, ast.Name):
        return False
    g = unit.module.globals.get(node.id)
    return node.id in unit.module.imports or isinstance(g, (ast.Call, ast.Attribute))


def _product_call(unit, call):
    """The call reaches a product function: a bare name the module imported (not one it defines), or an attribute of a
    module alias (km = load_source(...), sb, jd, pm: a module-level name bound to a call or imported)."""
    f = call.func
    if isinstance(f, ast.Name):
        return f.id not in unit.local_defs and f.id not in unit.module.functions and f.id in unit.module.imports
    if isinstance(f, ast.Attribute):
        return _is_module_alias(unit, f.value)
    return False


def _target_fn(start):
    """The function body behind the target, when it is in the test module: a local def, a module function, a lambda, a
    method of the class the construction sits in, or a Thread subclass's run()."""
    unit, expr = start.ctor_unit, start.target_expr
    if isinstance(expr, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return expr
    if isinstance(expr, ast.Lambda):
        return expr
    if isinstance(expr, ast.Name):
        fn = unit.local_defs.get(expr.id) or (unit.parent.local_defs.get(expr.id) if unit.parent is not None else None) \
            or unit.module.functions.get(expr.id)
        if fn is not None:
            return fn
        b = unit.binding_at(expr.id, start.ctor.lineno)
        if b is not None and isinstance(b[1], ast.Lambda):
            return b[1]
    if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name) and expr.value.id in ("self", "cls") and unit.cls is not None:
        ms = unit.module.methods_of(unit.cls, expr.attr)
        if ms:
            return ms[0]
    return None


def _kind(start):
    unit, expr, ctor = start.ctor_unit, start.target_expr, start.ctor
    loops = unit.module.loops
    if expr is None:
        return "bounded", "no target"
    if isinstance(expr, (ast.FunctionDef, ast.AsyncFunctionDef)):          # a Thread subclass: what its run() does
        return _body_kind(unit, list(ast.walk(expr)), loops, 0)
    if isinstance(expr, ast.Lambda):
        return _body_kind(unit, list(ast.walk(expr.body)), loops, 0)
    if isinstance(expr, ast.Attribute):
        if expr.attr in FOREVER:
            return "loop", expr.attr
        if expr.attr in BLOCKING and not _has_args(ctor):
            return "waits", "the target is an untimed .%s" % expr.attr
        if expr.attr in READS:
            return "waits", "the target is a read"
        fn = _target_fn(start)
        if fn is not None:
            return _body_kind(unit, list(ast.walk(fn)), loops, 0)
        if expr.attr in loops and expr.attr not in BUILTIN_METHODS:
            return "loop", "a product function with a while loop"
        return "bounded", "a function outside the test module with no while loop"
    if isinstance(expr, ast.Name):
        fn = _target_fn(start)
        if fn is not None:
            body = fn.body if isinstance(fn, ast.Lambda) else fn
            return _body_kind(unit, list(ast.walk(body)), loops, 0)
        if expr.id in loops:
            return "loop", "a product function with a while loop"
        return "bounded", "a function outside the test module with no while loop"
    return "bounded", "a callable the walk does not read"


def _release_names(start):
    """The names a waiting or polling thread would be released by: the receivers of the untimed waits and the is_set
    polls in its target, or the target's own receiver when the target is an Event.wait. A Thread subclass's run() waits
    on the fake's own attributes, which are not the test's: none."""
    expr = start.target_expr
    out = set()
    if expr is None or isinstance(expr, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return out
    if isinstance(expr, ast.Attribute) and expr.attr in BLOCKING:
        out.add(ast.unparse(expr.value))
        return out
    body = _target_fn(start)
    if body is not None:
        for sub in ast.walk(body):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in BLOCKING + ("is_set",):
                out.add(ast.unparse(sub.func.value))
    elif _outside_target(start):
        out |= _handed_names(start)                     # an Event handed to a product loop is what releases it
    return out


def _target_receivers(start):
    """The object the target runs on, whose shutdown / stop / cancel ends the thread: `srv` for srv.serve_forever, `loop` for
    a run_forever the target's body calls; never a module alias (km._producer runs on the module)."""
    out = set()
    expr = start.target_expr
    if isinstance(expr, ast.Attribute) and not _is_module_alias(start.ctor_unit, expr.value):
        out.add(ast.unparse(expr.value))
    body = _target_fn(start)
    if body is not None and not isinstance(expr, (ast.FunctionDef, ast.AsyncFunctionDef)):   # not a subclass's run(): its
        for sub in ast.walk(body):                                                            # self.* are the fake's own
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in FOREVER:
                out.add(ast.unparse(sub.func.value))
    return out


def _outside_target(start):
    """The target is a function outside the test module (km._producer, self.km._producer, pm._heartbeat_loop, an imported
    name): the kernel loops' seam (_LOOPS_STOP) is what such a loop watches, and the walk cannot read its body."""
    expr = start.target_expr
    if isinstance(expr, ast.Attribute):
        return expr.attr not in FOREVER + BLOCKING + READS and _target_fn(start) is None
    if isinstance(expr, ast.Name):
        return _target_fn(start) is None
    return False


def _handed_names(start):
    """The names handed to the target through the construction's args= / kwargs= (`kwargs={"stop": stop}`): what the
    thread holds, so a cleanup that sets or releases one is about this thread."""
    out = set()
    if start.ctor is None:
        return out
    for kw in start.ctor.keywords:
        if kw.arg in ("args", "kwargs"):
            for sub in ast.walk(kw.value):
                if isinstance(sub, (ast.Name, ast.Attribute)) and not (isinstance(sub, ast.Name) and sub.id in ("self", "cls")):
                    out.add(ast.unparse(sub))
    return out


# ── the shape of the stop ───────────────────────────────────────────────────────────────────────────────

def _is_cleanup_call(unit, call):
    nm = _callee_name(call)
    if nm in CLEANUP_NAMES:
        return True
    return isinstance(call.func, ast.Name) and call.func.id in unit.params and "cleanup" in call.func.id.lower()


def _thread_words(start, extra=()):
    """The names a stop of this thread would mention: its receiver (and the attribute and holder behind `self.x`, `h[k]`),
    the list a for-target iterates, its release names, its target and the object the target runs on (a server, a loop;
    a module alias is not one, the loops' seam stands for a product loop), the attributes on self that hold it, and the
    names a caller binds a helper's result to."""
    words = set(extra)
    words.add(start.recv_text)
    node = start.recv
    while isinstance(node, ast.Subscript):
        node = node.value
        words.add(ast.unparse(node))
    if isinstance(node, ast.Attribute):
        words.add(node.attr)
    if isinstance(start.recv, ast.Name):
        b = start.unit.binding_at(start.recv.id, start.line)
        if b is not None and isinstance(b[1], tuple) and b[1][0] == "for":
            words.add(ast.unparse(b[1][1]))
            if isinstance(b[1][1], ast.Attribute):
                words.add(b[1][1].attr)
    for nm in _release_names(start):
        words.add(nm)
        if "." in nm:
            words.add(nm.rsplit(".", 1)[1])
    expr = start.target_expr
    if isinstance(expr, (ast.Name, ast.Attribute)):
        words.add(ast.unparse(expr))
        if isinstance(expr, ast.Attribute):
            words.add(expr.attr)
    for r in _target_receivers(start) | _handed_names(start):
        words.add(r)
        if "." in r:
            words.add(r.rsplit(".", 1)[1])
    if start.kind == "loop" and _outside_target(start):
        words.add(STOP_SEAM)
    words.update(_stored_attrs(start))
    return {w for w in words if w and w not in ("self", "cls")}


def _cleanup_stops(unit, call, start, extra=()):
    """The cleanup names a stop (an attribute or call of a stop verb, the loops' seam, or a name that says stop, in its own
    arguments or in the body of the local function, lambda or method of the class it names) AND that text mentions the
    started thread (_thread_words): a cleanup that stops another thread excuses nothing about this one. With no start the
    stop shape alone is read."""
    nodes = []
    for a in list(call.args) + [k.value for k in call.keywords]:
        nodes.append(a)
        if isinstance(a, ast.Name):
            fn = unit.local_defs.get(a.id) or (unit.parent.local_defs.get(a.id) if unit.parent is not None else None) \
                or unit.module.functions.get(a.id)
            if fn is not None:
                nodes.append(fn)
            b = unit.binding_at(a.id, call.lineno)
            if b is not None and isinstance(b[1], ast.Lambda):
                nodes.append(b[1])
        if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.value.id in ("self", "cls") and unit.cls is not None:
            nodes += unit.module.methods_of(unit.cls, a.attr)
    if not any(_stop_shaped(n) for n in nodes):
        return False
    if start is None:
        return True
    text = "\n".join(ast.unparse(n) for n in nodes)
    return any(_word_in(w, text) for w in start.words(extra))


def _is_assertion(stmt):
    """The statement is a designed failure point: an assert* or fail call, a bare assert, a raise. A raise or an assertion
    inside a function the statement defines is that function's, not the statement's."""
    for sub in _run_nodes(stmt):
        if isinstance(sub, (ast.Assert, ast.Raise)):
            return True
        if isinstance(sub, ast.Call):
            nm = _callee_name(sub)
            if nm is not None and (nm.startswith("assert") or nm in ASSERTS):
                return True
    return False


def _cleanup_before(unit, line, start, extra=()):
    """A cleanup that names a stop of THIS thread, registered at or before `line` in the unit, or in the class's setUp /
    setUpClass (which run before every test body)."""
    for s, _b, _i, _st in unit.rows:
        for sub in _expr_children(s):
            if isinstance(sub, ast.Call) and _is_cleanup_call(unit, sub) and sub.lineno <= line and _cleanup_stops(unit, sub, start, extra):
                return True
    if unit.cls is not None and unit.fn.name not in ("setUp", "setUpClass"):
        for name, fn in unit.hooks():
            if name in ("setUp", "setUpClass"):
                hook_unit = unit.module.unit_for(fn, unit.cls)
                for sub in ast.walk(fn):
                    if isinstance(sub, ast.Call) and _is_cleanup_call(hook_unit, sub) and _cleanup_stops(hook_unit, sub, start, extra):
                        return True
    return False


def _in_try_finally(stack):
    return any(isinstance(s, ast.Try) and s.finalbody and field == "body" for s, field in stack)


def _stop_in(unit, stmt, names, releases, start, extra=()):
    """The stop one statement holds for the thread: a cleanup naming its stop ('cleanup-before-first-assertion'); a join
    of the same receiver or list, a shutdown / stop / cancel of it or of the object its target runs on (called, or handed
    over as loop.call_soon_threadsafe(loop.stop)), a set / release of what it waits on, or the loops' seam set for a
    product loop ('stop-before-first-assertion'). A TIMED join of a loop thread is a wait, not its stop: when it returns
    the loop runs on unless something else ended it, so it counts only beside a release, a shutdown or the seam."""
    loop_vars = {}
    for loop in ast.walk(stmt):
        if isinstance(loop, (ast.For, ast.comprehension)) and isinstance(loop.target, ast.Name):
            loop_vars[loop.target.id] = ast.unparse(loop.iter)
    target_recvs = _target_receivers(start) if start is not None else set()
    seam_ok = start is not None and start.kind == "loop" and _outside_target(start)
    loop_kind = start is not None and start.kind == "loop" and not start.indirect
    timed_join, ended = False, False
    for sub in ast.walk(stmt):
        if isinstance(sub, ast.Call):
            if _is_cleanup_call(unit, sub) and _cleanup_stops(unit, sub, start, extra):
                return "cleanup-before-first-assertion"
            if not isinstance(sub.func, ast.Attribute):
                continue
            f = sub.func
            r = ast.unparse(f.value)
            same = r in names or (r in loop_vars and loop_vars[r] in names)
            if f.attr == "join" and same:
                if loop_kind and (sub.args or sub.keywords):
                    timed_join = True
                    continue
                return "stop-before-first-assertion"
            if f.attr in ("shutdown", "stop", "cancel", "close", "server_close") and (same or r in target_recvs):
                ended = True
            if f.attr in ("set", "release") and (r in releases or (seam_ok and STOP_SEAM in r)):
                ended = True
        elif isinstance(sub, ast.Attribute) and sub.attr in ("stop", "shutdown", "cancel", "close") and ast.unparse(sub.value) in target_recvs:
            ended = True                                    # handed over: loop.call_soon_threadsafe(loop.stop)
    if ended:
        return "stop-before-first-assertion"
    return "timed-join" if timed_join else None


def _guard_ahead(unit, stmt, names, releases, start, extra=()):
    """The shape the walk forward from `stmt` meets before the first assertion: 'finally', 'cleanup-before-first-assertion',
    'stop-before-first-assertion', or None. The start's own statement is read first (`t.start(), t.join()` in one), then
    the statements after it. A timed join of a loop thread is passed over: the walk goes on to a release, a shutdown or
    the seam, and finds none before the assertion, the stop is behind it."""
    for nxt in [stmt] + list(unit.forward(stmt)):
        if nxt is not stmt:
            if isinstance(nxt, ast.Try) and nxt.finalbody:
                return "finally"
            if _is_assertion(nxt):
                return None
        r = _stop_in(unit, nxt, names, releases, start, extra)
        if r and r != "timed-join":
            return r
    return None


def _self_attrs_holding(unit, name):
    """The attributes on self/cls the unit stores the local name `name` in (assigned, appended or += into)."""
    out = []
    for s, _b, _i, _st in unit.rows:
        if isinstance(s, ast.Assign) and isinstance(s.value, ast.Name) and s.value.id == name:
            out += [t.attr for t in s.targets if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id in ("self", "cls")]
    for holder, values in unit.appends.items():
        if holder.startswith(("self.", "cls.")) and any(isinstance(v, ast.Name) and v.id == name for v in values):
            out.append(holder.split(".", 1)[1].split("[", 1)[0])
    return out


def _stored_attrs(start):
    """The attribute names on self/cls that hold the thread, the object its target runs on, or the event it waits on."""
    u, recv, names = start.unit, start.recv, []
    node = recv
    while isinstance(node, ast.Subscript):                    # self.threads["a"].start(): the holder
        node = node.value
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in ("self", "cls"):
        names.append(node.attr)
    if isinstance(recv, ast.Name):
        names += _self_attrs_holding(u, recv.id)
        for s, _b, _i, _st in u.rows:               # producer = self.producer = Thread(...)
            if isinstance(s, ast.Assign) and u.is_thread_ctor(s.value) and any(isinstance(t, ast.Name) and t.id == recv.id for t in s.targets):
                names += [t.attr for t in s.targets if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id in ("self", "cls")]
    expr = start.target_expr
    holders = []
    if isinstance(expr, ast.Attribute):
        holders.append(expr.value)
    for nm in _release_names(start):
        holders.append(ast.parse(nm, mode="eval").body if nm.isidentifier() or "." in nm else None)
    body = _target_fn(start)
    if body is not None and not isinstance(expr, (ast.FunctionDef, ast.AsyncFunctionDef)):   # not a subclass's run()
        for sub in ast.walk(body):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in FOREVER + BLOCKING + ("is_set",):
                holders.append(sub.func.value)
    for h in holders:
        if h is None:
            continue
        if isinstance(h, ast.Attribute) and isinstance(h.value, ast.Name) and h.value.id in ("self", "cls"):
            names.append(h.attr)
        elif isinstance(h, ast.Name):
            names += _self_attrs_holding(start.ctor_unit, h.id)
            if start.ctor_unit is not u:
                names += _self_attrs_holding(u, h.id)
    return sorted(set(names))


def _applies_stop(fn, attrs, loops_seam=True):
    """The function applies a stop verb to one of `attrs` (as a call or as a callback handed over), to a loop variable
    over one of them, or sets the loops' seam."""
    text = ast.unparse(fn)
    if not any(_word_in(a, text) for a in attrs):
        return False
    loop_vars = {}
    for loop in ast.walk(fn):
        if isinstance(loop, (ast.For, ast.comprehension)) and isinstance(loop.target, ast.Name):
            loop_vars[loop.target.id] = ast.unparse(loop.iter)
    for sub in ast.walk(fn):
        if isinstance(sub, ast.Attribute) and sub.attr in STOP_VERBS:
            recv = ast.unparse(sub.value)
            if any(_word_in(a, recv) for a in attrs):
                return True
            if recv in loop_vars and any(_word_in(a, loop_vars[recv]) for a in attrs):
                return True
            if loops_seam and sub.attr == "set" and STOP_SEAM in recv:
                return True
    return False


def _hook_stops(unit, attrs, start):
    for name, fn in unit.hooks():
        if _applies_stop(fn, attrs):
            return name
        if name in ("setUp", "setUpClass", "setUpModule"):
            hook_unit = unit.module.unit_for(fn, unit.cls)
            for sub in ast.walk(fn):
                if isinstance(sub, ast.Call) and _is_cleanup_call(hook_unit, sub) and _cleanup_stops(hook_unit, sub, start) \
                        and any(_word_in(a, ast.unparse(sub)) for a in attrs):
                    return name
    return None


def _object_owned(unit):
    if unit.cls is None or unit.module.is_testcase(unit.cls):
        return None
    for c in unit.module.bases_of(unit.cls):
        for f in c.body:
            if isinstance(f, ast.FunctionDef) and f.name in OWNER_ENDS:
                if any(isinstance(sub, ast.Attribute) and sub.attr in STOP_VERBS for sub in ast.walk(f)):
                    return f.name
    return None


def _start_names(start):
    names = {start.recv_text}
    if isinstance(start.recv, ast.Name):
        b = start.unit.binding_at(start.recv.id, start.line)
        if b is not None and isinstance(b[1], tuple) and b[1][0] == "for":
            names.add(ast.unparse(b[1][1]))
    return names


def classify(start, at=None):
    """The stop shape of one start, read in its own function or, for a helper's start, at a caller's call site `at`
    (unit, statement, stack, line)."""
    if at is None:
        unit, stmt, stack, line, extra = start.unit, start.stmt, start.stack, start.line, ()
    else:
        unit, stmt, stack, line = at
        extra = tuple(ast.unparse(t) for t in getattr(stmt, "targets", [])) + tuple(unit.assigned_attrs(stmt))
    if _in_try_finally(stack):
        return "finally"
    if _cleanup_before(unit, line, start, extra):
        return "cleanup-before-start"
    names, releases = _start_names(start) | set(extra), _release_names(start)
    ahead = _guard_ahead(unit, stmt, names, releases, start, extra)
    if ahead:
        return ahead
    attrs = _stored_attrs(start) if at is None else sorted(set(_stored_attrs(start)) | set(unit.assigned_attrs(stmt)))
    if attrs:
        hook = _hook_stops(unit, attrs, start)
        if hook:
            return "class-hook:" + hook
    if at is None:
        owner = _object_owned(unit)
        if owner:
            return "object-owned:" + owner
    return "tail-only"


def census(paths, loops=None, thread_classes=None):
    """Every thread start under `paths`: rows (start, shape, where) with `where` the unit the shape was read in (the
    start's own, or a caller's); a receiver the walk cannot read is a row with shape 'unreadable'."""
    loops = product_loops() if loops is None else loops
    thread_classes = product_thread_classes() if thread_classes is None else thread_classes
    out = []
    for p in paths:
        m = _Module(p, loops, thread_classes=thread_classes)
        for u in m.units():
            for st in u.starts():
                if not st.is_thread:
                    out.append((st, "unreadable", u.qualname))
                    continue
                shape = classify(st)
                if shape != "tail-only" or u.fn.name.startswith("test_") or u.fn.name in HOOK_NAMES:
                    out.append((st, shape, u.qualname))
                    continue
                callers = u.callers()
                if not callers:
                    out.append((st, shape, u.qualname))
                    continue
                for (cu, call, s, block, i, stack) in callers:
                    out.append((st, classify(st, at=(cu, s, stack, call.lineno)), cu.qualname))
    return out


def tail_only(rows, allow=None):
    """(loop/waits sites whose stop is tail-only and not excused, unreadable sites, stale allow entries, the bounded
    tail-only sites the BOUNDED rule excuses)."""
    allow = ALLOW if allow is None else allow
    tails, unread, bounded, seen = [], [], [], set()
    for st, shape, where in rows:
        if shape == "unreadable":
            unread.append((st, where))
        elif shape == "tail-only":
            key = (st.file(), where, st.target)
            seen.add(key)
            if st.kind not in KINDS_PINNED:
                bounded.append((st, where))
            elif key not in allow:
                tails.append((st, where))
    stale = [k for k in allow if k not in seen]
    return tails, unread, stale, bounded


def module_paths(root=HERE):
    return sorted(os.path.join(root, f) for f in os.listdir(root) if f.startswith("test_") and f.endswith(".py"))


def _report(rows, only_tail=False):
    lines = []
    for st, shape, where in sorted(rows, key=lambda r: (r[0].file(), r[0].line)):
        if only_tail and (shape not in ("tail-only", "unreadable") or (shape == "tail-only" and st.kind not in KINDS_PINNED)):
            continue
        lines.append("%-8s %-24s %s  [at %s]  (%s)" % (st.kind, shape, st.describe(), where, st.why))
    return "\n".join(lines)


class ThreadStopCensus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loops = product_loops()
        cls.thread_classes = product_thread_classes()
        cls.rows = census(module_paths(), cls.loops, cls.thread_classes)

    def test_every_loop_or_waiting_thread_a_test_starts_is_stopped_on_every_exit_path(self):
        tails, unread, stale, _bounded = tail_only(self.rows)
        problems = []
        for st, where in tails:
            problems.append("TAIL-ONLY stop of a %s thread (%s): %s (classed at %s). Register the stop as a cleanup BEFORE the "
                            "start (self.addCleanup(end), where end sets the stop, releases the gate and joins), or store the "
                            "thread on self and stop it in tearDown, or start it inside a try whose finally stops it."
                            % (st.kind, st.why, st.describe(), where))
        for st, where in unread:
            problems.append("UNREADABLE receiver: %s: the walk could not resolve what .start() is called on; bind the receiver "
                            "in the same function (t = threading.Thread(...)) or on self, or return the construction from the "
                            "helper that builds it." % st.describe())
        for k in stale:
            problems.append("STALE allow entry %r: it matches no tail-only site at this head; remove it." % (k,))
        self.assertEqual(problems, [], "\n" + "\n".join(problems))

    def test_the_product_loops_the_walk_reads_include_the_kernels_three_long_lived_loops(self):
        for name in ("_producer", "_pusher", "_heartbeat", "_jobs_loop", "_ws_sender"):
            self.assertIn(name, self.loops, name)

    def test_the_census_reads_the_shapes_the_tree_has(self):
        """The heartbeat module's loops through its _start helper (stored on self, joined in tearDown); the parked-ops
        module's producer (a cleanup registered before the start); the judges' process module's producer through its
        _pass helper (the stop seam set and the join done before any assertion); a fake server owned by its close();
        a peer server whose shutdown is the cleanup registered right after the start; the ws liveness module's Thread
        SUBCLASSES (_Peer, _Handler: their run() loops, appended to self.threads by +=, joined in tearDown); the update
        module's local alias (Real = threading.Thread) serving a fake manager inside a try whose finally shuts it down;
        the served checkpoint module's sampler bound by a conditional expression; and the atomic-write hammers, whose
        for-target name a comprehension had bound earlier (the binding in force at the start is the later one)."""
        by_file = {}
        for st, shape, where in self.rows:
            by_file.setdefault(st.file(), []).append((st.target, st.kind, shape, where))
        hb = by_file.get("tests/test_heartbeat_thread.py", [])
        self.assertTrue(any(t == "target" and s.startswith("class-hook:tearDown") for t, k, s, w in hb), hb)
        po = by_file.get("tests/test_kernel_parked_ops_liveness.py", [])
        self.assertTrue(po, "the parked-ops module starts a producer")
        self.assertTrue(all(k == "loop" and s == "cleanup-before-start" for t, k, s, w in po), po)
        sd = by_file.get("tests/test_spend_detail.py", [])
        self.assertTrue(any(t == "srv.serve_forever" and s == "cleanup-before-first-assertion" for t, k, s, w in sd), sd)
        bs = by_file.get("tests/test_bus_seed_token.py", [])
        self.assertTrue(bs and all(s.startswith("class-hook:tearDown") for t, k, s, w in bs), bs)
        jp = by_file.get("tests/test_judges_process.py", [])
        self.assertTrue(any(t == "km._producer" and k == "loop" and s == "stop-before-first-assertion" for t, k, s, w in jp), jp)
        fb = by_file.get("tests/test_kernel_bus_restore.py", [])
        self.assertTrue(any(t == "self.srv.serve_forever" and s == "object-owned:close" for t, k, s, w in fb), fb)
        wl = {(t, k, s) for t, k, s, w in by_file.get("tests/test_ws_liveness.py", [])}
        self.assertTrue({("_Handler.run", "loop", "class-hook:tearDown"), ("_Peer.run", "loop", "class-hook:tearDown")} <= wl, wl)
        ku = {(t, k, s, w) for t, k, s, w in by_file.get("tests/test_kernel_update.py", [])}
        for where in ("Routes.test_a_converge_thread_that_fails_to_start_gives_the_flag_back_and_the_next_click_converges",
                      "Routes._drift_click_whose_thread_fails_to_start"):                  # Real(target=mgr.serve_forever)
            self.assertIn(("mgr.serve_forever", "loop", "finally", where), ku)
        cs = by_file.get("tests/test_asm_checkpoint_served.py", [])
        self.assertIn(("sample", "finally"), [(t, s) for t, k, s, w in cs], cs)
        aw = by_file.get("tests/test_atomic_write.py", [])
        self.assertIn(("hammer", "bounded", "stop-before-first-assertion"), [(t, k, s) for t, k, s, w in aw], aw)

    def test_the_bounded_rule_excuses_at_least_one_site_or_it_is_stale(self):
        _tails, _unread, _stale, bounded = tail_only(self.rows)
        self.assertTrue(bounded, "no bounded thread has a tail-only join anymore: retire the BOUNDED shape rule")


class PlantedShapes(unittest.TestCase):
    """The rules read on synthetic modules: each shape planted alone, the walk's answer for it."""
    HEAD = ("import threading\nimport time\nimport unittest\nfrom unittest import mock\n"
            "def _loop():\n    while True:\n        time.sleep(0.01)\n"
            "def _once():\n    return 1\n\nclass T(unittest.TestCase):\n")
    HEAD_KM = HEAD.replace("class T(", "km = __import__('types').ModuleType('km')   # a module alias, as km = load_source(...)\nclass T(")

    def _census(self, body, allow=None, head=None):
        d = tempfile.mkdtemp(prefix="romp-tests-census-")
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "test_planted.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write((self.HEAD if head is None else head) + body)
        rows = census([p], loops={"_producer"}, thread_classes={"KernelWorker"})
        return rows, tail_only(rows, allow={} if allow is None else allow), os.path.relpath(p, ROOT)

    def _tails(self, tails):
        return sorted((s.target, w) for s, w in tails)

    def test_a_loops_stop_on_the_bodys_tail_after_an_assertion_is_named(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        t.join(5)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_x")])
        self.assertEqual((unread, bounded), ([], []))

    def test_a_loop_never_stopped_is_named_and_a_product_loop_is_read_by_name(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        threading.Thread(target=_loop, daemon=True).start()\n"
            "        self.assertTrue(True)\n"
            "    def test_y(self):\n"
            "        threading.Thread(target=km._producer, daemon=True).start()\n"
            "        self.assertTrue(True)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_x"), ("km._producer", "T.test_y")])

    def test_a_bounded_worker_joined_on_the_tail_is_excused_by_the_bounded_rule(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        out = []\n"
            "        def run():\n"
            "            out.append(_once())\n"
            "        ts = [threading.Thread(target=run) for _ in range(3)]\n"
            "        for t in ts:\n"
            "            t.start()\n"
            "        self.assertTrue(False)\n"
            "        for t in ts:\n"
            "            t.join(5)\n")
        self.assertEqual(tails, [])
        self.assertEqual([(s.target, s.kind) for s, w in bounded], [("run", "bounded")])

    def test_a_waiting_worker_is_pinned_and_its_release_as_the_next_statement_counts(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        go = threading.Event()\n"
            "        def run():\n"
            "            go.wait()\n"
            "        t = threading.Thread(target=run)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        go.set(); t.join(5)\n"
            "    def test_y(self):\n"
            "        go = threading.Event()\n"
            "        def run():\n"
            "            go.wait()\n"
            "        ts = [threading.Thread(target=run) for _ in range(2)]\n"
            "        for t in ts:\n"
            "            t.start()\n"
            "        go.set()\n"
            "        self.assertTrue(False)\n"
            "    def test_z(self):\n"
            "        gate = threading.Event()\n"
            "        t = threading.Thread(target=gate.wait, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        gate.set()\n")
        self.assertEqual(self._tails(tails), [("gate.wait", "T.test_z"), ("run", "T.test_x")])
        self.assertIn(("run", "waits", "stop-before-first-assertion", "T.test_y"), [(s.target, s.kind, sh, w) for s, sh, w in rows])

    def test_a_cleanup_registered_before_the_start_or_right_after_it_is_not_named(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        stop = threading.Event()\n"
            "        def end():\n"
            "            stop.set()\n"
            "            t.join(5)\n"
            "        self.addCleanup(end)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_y(self):\n"
            "        srv = object()\n"
            "        threading.Thread(target=srv.serve_forever, daemon=True).start()\n"
            "        self.addCleanup(srv.shutdown)\n"
            "        self.assertTrue(False)\n"
            "    def test_z(self):\n"
            "        stop = self._go()\n"
            "        self.addCleanup(stop)\n"
            "        self.assertTrue(False)\n"
            "    def _go(self):\n"
            "        threading.Thread(target=_loop, daemon=True).start()\n"
            "        return lambda: None\n")
        self.assertEqual(tails, [])
        self.assertEqual(sorted(s for _s, s, _w in rows), ["cleanup-before-first-assertion"] * 2 + ["cleanup-before-start"])

    def test_a_cleanup_registered_after_an_assertion_or_naming_no_stop_does_not_count(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        self.addCleanup(t.join)\n"
            "    def test_y(self):\n"
            "        self.addCleanup(print, 'bye')\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        t.join(5)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_x"), ("_loop", "T.test_y")])

    def test_a_cleanup_that_stops_another_thread_excuses_nothing_about_this_one(self):
        """A stop-shaped cleanup counts only for the thread it names: setUp's addCleanup(self.srv.shutdown) covers the
        server's serve_forever thread and no other start in the class; a cleanup for loop thread a says nothing about
        loop thread b, whose only stop stands behind the assertion."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def setUp(self):\n"
            "        self.srv = object()\n"
            "        self.addCleanup(self.srv.shutdown)\n"
            "    def test_x(self):\n"
            "        threading.Thread(target=self.srv.serve_forever, daemon=True).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_y(self):\n"
            "        b = threading.Thread(target=_loop, daemon=True)\n"
            "        b.start()\n"
            "        self.assertTrue(False)\n"
            "        b.join()\n"
            "    def test_z(self):\n"
            "        a = threading.Thread(target=_loop, daemon=True)\n"
            "        b = threading.Thread(target=_loop, daemon=True)\n"
            "        self.addCleanup(a.join)\n"
            "        a.start(); b.start()\n"
            "        self.assertTrue(False)\n"
            "        b.join()\n"
            "    def test_w(self):\n"
            "        b = threading.Thread(target=_loop, daemon=True)\n"
            "        def end():\n"
            "            b.join()\n"
            "        self.addCleanup(end)\n"
            "        b.start()\n"
            "        self.assertTrue(False)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_y"), ("_loop", "T.test_z")])
        self.assertEqual(sorted((s.recv_text, sh, w) for s, sh, w in rows if sh == "cleanup-before-start"),
                         [("a", "cleanup-before-start", "T.test_z"), ("b", "cleanup-before-start", "T.test_w"),
                          ("threading.Thread(target=self.srv.serve_forever, daemon=True)", "cleanup-before-start", "T.test_x")])

    def test_a_start_inside_a_try_with_a_finally_or_right_before_one_is_not_named(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        try:\n"
            "            t.start()\n"
            "            self.assertTrue(False)\n"
            "        finally:\n"
            "            t.join(5)\n"
            "    def test_y(self):\n"
            "        gate = threading.Event()\n"
            "        ts = [threading.Thread(target=gate.wait) for _ in range(2)]\n"
            "        for t in ts:\n"
            "            t.start()\n"
            "        try:\n"
            "            self.assertTrue(False)\n"
            "        finally:\n"
            "            gate.set()\n")
        self.assertEqual(tails, [])
        self.assertEqual([s for _s, s, _w in rows], ["finally", "finally"])

    def test_a_thread_on_self_stopped_in_tear_down_is_not_named_and_one_only_read_there_is(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def tearDown(self):\n"
            "        t = getattr(self, 't', None)\n"
            "        if t is not None:\n"
            "            self.stop.set(); self.t.join(5)\n"
            "        for loop in self.loops:\n"
            "            loop.call_soon_threadsafe(loop.stop)\n"
            "    def test_x(self):\n"
            "        self.stop = threading.Event()\n"
            "        self.t = threading.Thread(target=_loop, daemon=True)\n"
            "        self.t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_y(self):\n"
            "        loop = object()\n"
            "        threading.Thread(target=loop.run_forever, daemon=True).start()\n"
            "        self.loops.append(loop)\n"
            "        self.assertTrue(False)\n")
        self.assertEqual(tails, [])
        self.assertEqual([s for _s, s, _w in rows], ["class-hook:tearDown", "class-hook:tearDown"])
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def tearDown(self):\n"
            "        p = getattr(self, 'producer', None)\n"
            "        if p is None or not p.is_alive():\n"
            "            self.flag.clear()\n"
            "    def test_x(self):\n"
            "        self.flag = threading.Event()\n"
            "        producer = self.producer = threading.Thread(target=_loop, daemon=True)\n"
            "        producer.start()\n"
            "        self.assertTrue(False)\n"
            "        self.flag.set(); producer.join(5)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_x")], "a tearDown that reads the thread but stops nothing is not a stop")

    def test_a_fakes_thread_is_owned_by_its_end_method_and_a_fake_without_one_is_named(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    pass\n\n"
            "class _Fake:\n"
            "    def __init__(self):\n"
            "        self.stop = threading.Event()\n"
            "        threading.Thread(target=self.stop.wait, daemon=True).start()\n"
            "    def close(self):\n"
            "        self.stop.set()\n\n"
            "class _Bare:\n"
            "    def __init__(self):\n"
            "        threading.Thread(target=_loop, daemon=True).start()\n")
        self.assertEqual(self._tails(tails), [("_loop", "_Bare.__init__")])
        self.assertIn("object-owned:close", [s for _s, s, _w in rows])

    def test_a_helper_start_is_classed_at_its_callers(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def _go(self):\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        t.start()\n"
            "        return t\n"
            "    def test_guarded(self):\n"
            "        self.addCleanup(self.stop.set)\n"
            "        self._go()\n"
            "        self.assertTrue(False)\n"
            "    def test_bare(self):\n"
            "        t = self._go()\n"
            "        self.assertTrue(False)\n"
            "        t.join()\n"
            "    def test_named(self):\n"
            "        t = self._go()\n"
            "        self.addCleanup(t.join)\n"
            "        self.assertTrue(False)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_bare"), ("_loop", "T.test_guarded")],
                         "a cleanup that names no thread of the helper's excuses nothing (self.stop is not what _loop waits on)")
        self.assertIn(("_loop", "cleanup-before-first-assertion", "T.test_named"), [(s.target, sh, w) for s, sh, w in rows])

    def test_a_stop_before_the_first_assertion_is_not_named_even_for_a_loop(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        t.start()\n"
            "        t.join()\n"
            "        self.assertTrue(False)\n"
            "    def test_many(self):\n"
            "        ts = [threading.Thread(target=_loop) for _ in range(3)]\n"
            "        for t in ts:\n"
            "            t.start()\n"
            "        for t in ts:\n"
            "            t.join()\n"
            "        self.assertTrue(False)\n"
            "    def test_comp(self):\n"
            "        ts = [threading.Thread(target=_loop) for _ in range(3)]\n"
            "        [t.start() for t in ts]\n"
            "        [t.join() for t in ts]\n"
            "        self.assertTrue(False)\n"
            "    def test_between(self):\n"
            "        srv = object()\n"
            "        for s in (srv,):\n"
            "            threading.Thread(target=srv.serve_forever, daemon=True).start()\n"
            "        port = 1\n"
            "        saved = dict(a=1)\n"
            "        def helper():\n"
            "            return port\n"
            "        try:\n"
            "            self.assertTrue(False)\n"
            "        finally:\n"
            "            srv.shutdown()\n")
        self.assertEqual(tails, [])
        self.assertEqual(sorted(s for _s, s, _w in rows), ["finally"] + ["stop-before-first-assertion"] * 3)

    def test_a_join_in_the_starts_own_statement_counts_and_a_timed_join_alone_does_not_stop_a_loop(self):
        """The start statement's remaining nodes are read first (`t.start(), t.join()` in one statement is a stop, not
        tail-only); a TIMED join of a loop thread is a wait the loop outlives, so alone it is not the stop (test_y is
        named), while the loops' seam set beside it (a product loop), a shutdown of the object the target runs on, or a
        release of what the thread waits on is."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        t.start(), t.join()\n"
            "        self.assertTrue(False)\n"
            "    def test_y(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        t.start()\n"
            "        t.join(5)\n"
            "        self.assertTrue(False)\n"
            "    def test_z(self):\n"
            "        t = threading.Thread(target=km._producer, daemon=True)\n"
            "        t.start()\n"
            "        km._LOOPS_STOP.set(); km._producer_wake.set()\n"
            "        t.join(10)\n"
            "        self.assertTrue(False)\n"
            "    def test_w(self):\n"
            "        srv = object()\n"
            "        t = threading.Thread(target=srv.serve_forever)\n"
            "        t.start()\n"
            "        srv.shutdown(); t.join(5)\n"
            "        self.assertTrue(False)\n"
            "    def test_v(self):\n"
            "        go = threading.Event()\n"
            "        def run():\n"
            "            while not go.is_set():\n"
            "                time.sleep(0.01)\n"
            "        t = threading.Thread(target=run)\n"
            "        t.start()\n"
            "        go.set(); t.join(5)\n"
            "        self.assertTrue(False)\n", head=self.HEAD_KM)
        self.assertEqual(self._tails(tails), [("_loop", "T.test_y")])
        self.assertEqual(sorted((w, s) for _s, s, w in rows if w != "T.test_y"),
                         [(w, "stop-before-first-assertion") for w in ("T.test_v", "T.test_w", "T.test_x", "T.test_z")])

    def test_a_cleanup_registered_in_set_up_and_a_helpers_result_stored_on_self_count_for_the_class(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def setUp(self):\n"
            "        self.addCleanup(self._sweep)\n"
            "    def _sweep(self):\n"
            "        self.loop.call_soon_threadsafe(self.loop.stop)\n"
            "    def test_x(self):\n"
            "        self.loop = object()\n"
            "        def run_loop():\n"
            "            self.loop.run_forever()\n"
            "        threading.Thread(target=run_loop, daemon=True).start()\n"
            "        self.assertTrue(False)\n\n"
            "class U(unittest.TestCase):\n"
            "    def setUp(self):\n"
            "        self.bus, self.ver = _serve(), _serve()\n"
            "    def tearDown(self):\n"
            "        for srv in (self.bus, self.ver):\n"
            "            srv.shutdown()\n"
            "    def test_y(self):\n"
            "        self.assertTrue(False)\n\n"
            "def _serve():\n"
            "    srv = object()\n"
            "    threading.Thread(target=srv.serve_forever, daemon=True).start()\n"
            "    return srv\n")
        self.assertEqual(tails, [])
        self.assertEqual(sorted(s for _s, s, _w in rows), ["class-hook:tearDown", "class-hook:tearDown", "cleanup-before-start"])

    def test_a_raise_inside_a_function_the_body_defines_is_not_the_bodys_assertion(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        mgr = object()\n"
            "        threading.Thread(target=mgr.serve_forever, daemon=True).start()\n"
            "        port = 1\n"
            "        def build():\n"
            "            raise RuntimeError('esbuild vanished')\n"
            "        def check():\n"
            "            self.assertEqual(1, 1)\n"
            "        try:\n"
            "            self.assertTrue(False)\n"
            "        finally:\n"
            "            mgr.shutdown()\n")
        self.assertEqual(tails, [])
        self.assertEqual([s for _s, s, _w in rows], ["finally"])

    def test_a_patcher_a_match_and_a_module_are_not_threads_and_an_unbound_receiver_is_listed(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def setUp(self):\n"
            "        self._patches = [mock.patch.object(threading, 'x', 1)]\n"
            "        for p in self._patches:\n"
            "            p.start()\n"
            "    def test_x(self):\n"
            "        import re, tracemalloc\n"
            "        mock.patch.object(threading, 'y', 1).start()\n"
            "        tracemalloc.start()\n"
            "        heads = [m.start() for m in re.finditer('a', 'aa')]\n"
            "        self.assertTrue(heads[-1].start() or True)\n"
            "        ths = []\n"
            "        for _ in range(2):\n"
            "            ths.append(threading.Thread(target=_once))\n"
            "        for t in ths:\n"
            "            t.start()\n"
            "        for t in ths:\n"
            "            t.join()\n"
            "    def test_y(self, worker=None):\n"
            "        worker.start()\n"
            "    def _context(self, text, m, width=40):\n"
            "        return text[max(0, m.start() - width):m.end() + width]\n")
        self.assertEqual(tails, [])
        self.assertEqual([(s.recv_text, w) for s, w in unread], [("worker", "T.test_y")])
        self.assertEqual([(s.target, sh) for s, sh, w in rows if sh != "unreadable"], [("_once", "stop-before-first-assertion")])

    def test_a_helper_built_thread_a_subclass_an_alias_and_a_container_element_are_read_as_threads(self):
        """Four starts the walk used to pass in silence, each named now: a thread a helper returns (a module function, a
        method of the class, a function of the body, a tuple the caller unpacks), a Thread SUBCLASS defined in the module
        or in the body (its run() gives the kind), an import alias or a local alias of threading.Thread, and a thread
        stored in a dict or list element and started from it. Also a name a comprehension bound earlier and a for
        rebinds (the binding in force at the start is the for's), and a thread bound by a conditional expression."""
        head = ("import threading\nimport time\nimport unittest\nfrom threading import Thread as Th\n"
                "def _loop():\n    while True:\n        time.sleep(0.01)\n"
                "def _once():\n    return 1\n"
                "def _make():\n    t = threading.Thread(target=_loop, daemon=True)\n    return t\n"
                "def _pair():\n    return threading.Thread(target=_loop, daemon=True), threading.Event()\n"
                "class W(threading.Thread):\n    def run(self):\n        while True:\n            time.sleep(0.01)\n"
                "class W2(W):\n    pass\n"
                "class Once(threading.Thread):\n    def run(self):\n        return _once()\n"
                "class T(unittest.TestCase):\n")
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def _mk(self):\n"
            "        return threading.Thread(target=_loop, daemon=True)\n"
            "    def test_helper(self):\n"
            "        t = _make()\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_method(self):\n"
            "        t = self._mk()\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_local(self):\n"
            "        def build():\n"
            "            return threading.Thread(target=_loop, daemon=True)\n"
            "        build().start()\n"
            "        self.assertTrue(False)\n"
            "    def test_unpack(self):\n"
            "        t, ev = _pair()\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_subclass(self):\n"
            "        w = W2(daemon=True)\n"
            "        w.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_subclass_bounded(self):\n"
            "        Once().start()\n"
            "        self.assertTrue(False)\n"
            "    def test_local_subclass(self):\n"
            "        Real = threading.Thread\n"
            "        class L(Real):\n"
            "            def run(self):\n"
            "                while True:\n"
            "                    time.sleep(0.01)\n"
            "        L().start()\n"
            "        Real(target=_loop).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_alias(self):\n"
            "        Th(target=_loop, daemon=True).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_dict(self):\n"
            "        self.threads = {}\n"
            "        self.threads['a'] = threading.Thread(target=_loop, daemon=True)\n"
            "        self.threads['a'].start()\n"
            "        self.assertTrue(False)\n"
            "    def test_list(self):\n"
            "        ts = []\n"
            "        ts.append(threading.Thread(target=_loop, daemon=True))\n"
            "        ts[0].start()\n"
            "        self.assertTrue(False)\n"
            "    def test_rebound(self):\n"
            "        ts = [threading.Thread(target=_loop, args=(t,)) for t in range(3)]\n"
            "        for t in ts:\n"
            "            t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_ifexp(self):\n"
            "        th = threading.Thread(target=_loop) if _once() else None\n"
            "        if th is not None:\n"
            "            th.start()\n"
            "        self.assertTrue(False)\n", head=head)
        self.assertEqual(unread, [], [(s.recv_text, w) for s, w in unread])
        self.assertEqual(self._tails(tails), sorted([
            ("_loop", "T.test_helper"), ("_loop", "T.test_method"), ("_loop", "T.test_local"), ("_loop", "T.test_unpack"),
            ("W2.run", "T.test_subclass"), ("L.run", "T.test_local_subclass"), ("_loop", "T.test_local_subclass"),
            ("_loop", "T.test_alias"), ("_loop", "T.test_dict"), ("_loop", "T.test_list"), ("_loop", "T.test_rebound"),
            ("_loop", "T.test_ifexp")]))
        self.assertEqual([(s.target, s.kind) for s, w in bounded], [("Once.run", "bounded")])

    def test_a_call_the_walk_cannot_read_is_listed_and_a_known_non_thread_is_not(self):
        """A receiver built by a call the walk cannot classify (a parameter's, a method the class does not define, a
        product Thread subclass) is UNREADABLE and listed; a mock patcher, a regex match, tracemalloc and an object of a
        product or library module (its start() is its own) are not thread starts of the test."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self, factory=None):\n"
            "        factory().start()\n"
            "        self.other().start()\n"
            "        km.KernelWorker().start()\n"
            "        mock.patch.object(threading, 'y', 1).start()\n"
            "        from unittest.mock import patch\n"
            "        patch.dict({}, {}).start()\n"
            "        km.SdkSession(1).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_none(self):\n"
            "        def nothing():\n"
            "            return None\n"
            "        self.addCleanup(nothing)\n", head=self.HEAD_KM)
        self.assertEqual(sorted((s.recv_text, w) for s, w in unread),
                         [("factory()", "T.test_x"), ("km.KernelWorker()", "T.test_x"), ("self.other()", "T.test_x")])
        self.assertEqual([sh for _s, sh, _w in rows if sh != "unreadable"], [])

    def test_an_allow_entry_excuses_one_site_and_a_stale_one_is_named(self):
        body = ("    def test_x(self):\n"
                "        t = threading.Thread(target=_loop, daemon=True)\n"
                "        t.start()\n"
                "        self.assertTrue(False)\n"
                "        t.join(5)\n")
        rows, (tails, unread, stale, bounded), rel = self._census(body, allow={(None, "T.test_x", "_loop"): "x"})
        self.assertEqual(self._tails(tails), [("_loop", "T.test_x")])
        tails, unread, stale, bounded = tail_only(rows, allow={(rel, "T.test_x", "_loop"): "the fake's loop ends with the process"})
        self.assertEqual((tails, stale), ([], []))
        tails, unread, stale, bounded = tail_only(rows, allow={(rel, "T.test_gone", "_loop"): "an entry for a site that is gone"})
        self.assertEqual(self._tails(tails), [("_loop", "T.test_x")])
        self.assertEqual(stale, [(rel, "T.test_gone", "_loop")])


if __name__ == "__main__":
    if "--table" in sys.argv or "--tail" in sys.argv:
        loops = product_loops()
        rows = census(module_paths(), loops, product_thread_classes())
        print(_report(rows, only_tail="--tail" in sys.argv))
        tails, unread, stale, bounded = tail_only(rows)
        from collections import Counter
        print("\nshapes:", dict(Counter(s for _st, s, _w in rows)))
        print("kinds:", dict(Counter(st.kind for st, _s, _w in rows)))
        print("pinned tail-only (not excused): %d, unreadable: %d, stale allow: %d, bounded tail-only (excused): %d"
              % (len(tails), len(unread), len(stale), len(bounded)))
        sys.exit(0)
    unittest.main()
