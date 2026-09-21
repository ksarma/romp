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
front of the producer's first pass, against a test written 2026-09-03 that polled 5 s for the pass. The module still
passed serially, because its alphabetically first test's km._pusher_cycle() reached _sdk() through _turn_notify_tick
and _alive_sessions and built a real SdkBackend whose boot reconcile fired attachDone within a second, pre-setting
_BOOT_ATTACHED as a side effect; under xdist --dist load the target landed in a worker with no module-mate ahead of it
and failed, red in every full sweep since 2026-09-11 and never in CI (serial). The failed assertion skipped the stop on
the tail, the tearDown only CLEARED the stop flag when the producer was already dead and never SET it, so a live,
fully UNPATCHED judge loop (the with-block's eleven patches were undone on the way out while the producer was still in
its hold) ran for the rest of the worker's life. The T282 census in tearDown named the leftover thread (the "1 error"
beside the "1 failed") but could not stop it.

THE BLAST RADIUS, proven by romp-manager's probe: the leaked loop runs _compact_goal_stores() on its 3 s backstop,
globbing jd.GOALDIR and rewriting any store whose mtime moved; km.jd is the ONE process-wide sys.modules["romp_judge"]
(kernel.py loads it by that name; tests/conftest.py's shared-judge note), and later modules jd._rebind_state() it onto
their own roots, so the leaked loop archives stores it never owned (a store saved under a private sid with a cleared
root was archived 7.5 s later by the leaked thread); 13 modules save stores with cleared roots and 18 assert on the
archive, so the leak can produce a SPURIOUS PASS as well as a spurious failure in a module that did nothing wrong.
NOT DETERMINED, carried and not dropped: whether the leaked loop produced flakes in earlier sweeps. The SdkBackend
side-effect build is benign on its own (its orphan reap is gated on its own empty registry; sweep_dead_test_roots
removes only romp-tests-* roots whose marker names a dead pid).

THE START SITES. A `.start()` call whose receiver the walk resolves to a threading.Thread or Timer construction:
chained (`Thread(...).start()`), through a name bound in the same function (an assignment, a for-target or a
comprehension target over a list of such, a list appended to), through an attribute bound on self or cls anywhere in
the class or a base in the same file, or through a module name. A receiver bound to anything else (a mock patcher, a
server, a regex match, tracemalloc) is not a thread start; a receiver the walk cannot resolve (a parameter, a call's
result) is UNREADABLE and LISTED, never passed in silence.

THE KIND of a thread, read from its target: what it does if the test never stops it.
  loop:    it runs until told: serve_forever / run_forever; a function of the test module whose body has a `while`
           (a `while` bounded by a clock reading is not one), or that iterates `iter(f, sentinel)`, or that calls a
           product function that has one; a product function (kernel/, postal/, cli/, the bin scripts) whose body has
           a `while` (km._producer, _pusher, _heartbeat, _jobs_loop, _ws_sender, _apply_pending_ops, pm._heartbeat_loop).
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
    as a parameter whose name says cleanup) that names a stop (an attribute or call of join / set / shutdown / stop /
    close / cancel / terminate / kill, the loops' seam _LOOPS_STOP, a name that says stop / end / close, or a local
    function, a lambda or a method of the class that does), registered at or before the start in the same function or
    in the class's setUp. unittest runs cleanups after tearDown, LIFO, on every exit path.
  cleanup-before-first-assertion: such a cleanup registered by a statement the walk forward meets before any assertion
    (`Thread(target=srv.serve_forever).start()` then `self.addCleanup(srv.shutdown)`).
  stop-before-first-assertion: the walk forward meets the stop itself before any assertion: a join, shutdown or cancel
    of the same receiver or the same list (`for t in ts: t.start()` then `for t in ts: t.join()`), or, for a thread that
    waits or polls, a set or release of what it waits on (`go.set()`).
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

WHAT THIS CENSUS DOES NOT SEE. The shape rules read constructs and not their meaning: a cleanup that names a
stop verb but stops the wrong thread, a finally that does not join, a tearDown whose join bound the thread outlives,
an end method no test calls, are all classed as guaranteed here and caught only by the runtime oracle. A thread started
by code outside tests/*.py (a kernel helper that spawns its own worker) is the kernel's to end. Run the module directly
for the table (`--table`; `--tail` prints only the tail-only and unreadable rows).
"""
import ast
import os
import re
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


def _is_thread_ctor(node):
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


def product_loops(root=ROOT):
    """The name of every function in the product sources whose body has a `while`: kernel/, postal/, cli/ and the bin
    scripts that are files of their own (the rest of bin/ are links into those directories)."""
    names = set()
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
            tree = ast.parse(open(p, encoding="utf-8").read(), p)
        except (SyntaxError, UnicodeDecodeError):
            continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(isinstance(s, ast.While) for s in ast.walk(n)):
                names.add(n.name)
    return names


class _Module:
    def __init__(self, path, loops, src=None):
        self.path = path
        self.loops = loops
        self.src = open(path, encoding="utf-8").read() if src is None else src
        self.tree = ast.parse(self.src, path)
        self.classes = {n.name: n for n in self.tree.body if isinstance(n, ast.ClassDef)}
        self.functions = {n.name: n for n in self.tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.globals, self.imports = {}, set()
        for n in ast.walk(self.tree):
            if isinstance(n, ast.Import):
                self.imports.update((a.asname or a.name).split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                self.imports.update(a.asname or a.name for a in n.names)
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
        self._units = None

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
        return self._units


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
    def __init__(self, module, cls, fn):
        self.module, self.cls, self.fn = module, cls, fn
        self.qualname = ("%s.%s" % (cls.name, fn.name)) if cls is not None else fn.name
        self.params = {a.arg for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs}
        self.rows = []
        _stmts(fn.body, [], self.rows)
        self.row_of = {id(s): (s, block, i, stack) for s, block, i, stack in self.rows}
        self.owner, self.parent = {}, {}
        for s, _b, _i, _st in self.rows:
            for child in ast.iter_child_nodes(s):
                if isinstance(child, ast.stmt):
                    continue
                self.parent.setdefault(id(child), s)
                for node in ast.walk(child):
                    self.owner.setdefault(id(node), s)
                    for sub in ast.iter_child_nodes(node):
                        self.parent.setdefault(id(sub), node)
        self.bindings = {}
        self.appends = {}
        for s, _b, _i, _st in self.rows:
            self._bind(s)
        self.local_defs = {}
        for s, _b, _i, _st in self.rows:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.local_defs.setdefault(s.name, s)

    def _bind(self, s):
        if isinstance(s, ast.Assign):
            for t in s.targets:
                self._bind_target(t, s.value)
        elif isinstance(s, ast.AnnAssign) and s.value is not None:
            self._bind_target(s.target, s.value)
        elif isinstance(s, (ast.For, ast.AsyncFor)):
            self._bind_target(s.target, ("for", s.iter))
        elif isinstance(s, (ast.With, ast.AsyncWith)):
            for it in s.items:
                if it.optional_vars is not None:
                    self._bind_target(it.optional_vars, ("with", it.context_expr))
        for sub in _expr_children(s):
            if isinstance(sub, ast.NamedExpr):
                self._bind_target(sub.target, sub.value)
            elif isinstance(sub, ast.comprehension):
                self._bind_target(sub.target, ("for", sub.iter))
            elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in ("append", "add") and sub.args:
                self.appends.setdefault(ast.unparse(sub.func.value), []).append(sub.args[0])

    def _bind_target(self, t, value):
        if isinstance(t, ast.Name):
            self.bindings.setdefault(t.id, value)
        elif isinstance(t, ast.Attribute):
            self.bindings.setdefault(ast.unparse(t), value)
        elif isinstance(t, (ast.Tuple, ast.List)):
            if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(t.elts):
                for e, v in zip(t.elts, value.elts):
                    self._bind_target(e, v)
            else:
                for e in t.elts:
                    self._bind_target(e, ("unpack", value))

    def class_bindings(self, attr):
        """Every value bound to `self.<attr>` / `cls.<attr>` by any spelling across the class and its bases, plus every
        `.append(v)` into it."""
        if self.cls is None:
            return []
        out = []
        for c in self.module.bases_of(self.cls):
            for sub in ast.walk(c):
                if isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Attribute) and t.attr == attr:
                            out.append(sub.value)
                elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in ("append", "add") \
                        and isinstance(sub.func.value, ast.Attribute) and sub.func.value.attr == attr and sub.args:
                    out.append(sub.args[0])
        return out

    def resolve(self, node, depth=0):
        """'thread' when the expression is (or is bound to) a Thread/Timer construction, 'other' when it is bound to
        something else the walk can read, None when it cannot read it."""
        if depth > 8 or node is None:
            return None
        if isinstance(node, tuple):
            kind, inner = node
            if kind == "for":
                return self.resolve(inner, depth + 1)
            if kind == "with":
                return "other"
            return None
        if isinstance(node, ast.Call):
            if _is_thread_ctor(node):
                return "thread"
            return "other"
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            kinds = {self.resolve(e, depth + 1) for e in node.elts}
            if "thread" in kinds:
                return "thread"
            if None in kinds:
                return None
            return "other" if kinds else "empty"
        if isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            return self.resolve(node.elt, depth + 1)
        if isinstance(node, ast.Name):
            if node.id in self.bindings:
                r = self.resolve(self.bindings[node.id], depth + 1)
                if r == "empty" or (r is None and node.id in self.appends):
                    kinds = {self.resolve(v, depth + 1) for v in self.appends.get(node.id, [])}
                    return "thread" if "thread" in kinds else ("other" if kinds and None not in kinds else None)
                return r
            if node.id in self.module.globals:
                return self.resolve(self.module.globals[node.id], depth + 1)
            if node.id in self.module.imports or node.id in self.module.functions or node.id in self.module.classes:
                return "other"
            return None
        if isinstance(node, ast.Attribute):
            text = ast.unparse(node)
            if text in self.bindings:
                r = self.resolve(self.bindings[text], depth + 1)
                if r == "empty" or (r is None and text in self.appends):
                    kinds = {self.resolve(v, depth + 1) for v in self.appends.get(text, [])}
                    return "thread" if "thread" in kinds else ("other" if kinds and None not in kinds else None)
                return r
            vals = self.class_bindings(node.attr)
            if vals:
                kinds = {self.resolve(v, depth + 1) for v in vals}
                if "thread" in kinds:
                    return "thread"
                if None in kinds:
                    return None
                return "other"
            if isinstance(node.value, ast.Name) and (node.value.id in self.module.globals or node.value.id in self.module.imports):
                return "other"      # a module object's attribute (mock.patch, tracemalloc.start): never a thread of ours
            return None
        if isinstance(node, ast.Subscript):
            r = self.resolve(node.value, depth + 1)
            return r if r in ("thread", "other") else None
        if isinstance(node, (ast.Constant, ast.Dict, ast.JoinedStr, ast.BinOp, ast.Compare, ast.Lambda, ast.BoolOp, ast.IfExp)):
            return "other"
        return None

    def thread_of(self, expr):
        """The ctor call behind a start receiver, when the walk can find it (for the target)."""
        node = expr
        for _ in range(8):
            if _is_thread_ctor(node):
                return node
            if isinstance(node, ast.Name):
                nxt = self.bindings.get(node.id) or self.module.globals.get(node.id)
                if (nxt is None or (isinstance(nxt, ast.List) and not nxt.elts)) and node.id in self.appends:
                    nxt = next((v for v in self.appends[node.id] if _is_thread_ctor(v)), None)
                node = nxt
            elif isinstance(node, ast.Attribute):
                text = ast.unparse(node)
                nxt = self.bindings.get(text)
                if nxt is None:
                    vals = self.class_bindings(node.attr)
                    nxt = next((v for v in vals if _is_thread_ctor(v)), vals[0] if vals else None)
                node = nxt
            elif isinstance(node, tuple):
                node = node[1]
            elif isinstance(node, (ast.List, ast.Tuple)):
                node = next((e for e in node.elts if _is_thread_ctor(e)), None)
            elif isinstance(node, (ast.ListComp, ast.GeneratorExp)):
                node = node.elt
            elif isinstance(node, ast.Subscript):
                node = node.value
            else:
                return None
        return None

    def starts(self):
        """Every `.start()` in the unit whose receiver resolves to a thread, or to nothing."""
        out = []
        for s, block, i, stack in self.rows:
            for sub in _expr_children(s):
                if not (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "start"
                        and not sub.args and not sub.keywords):
                    continue
                if self._value_used(sub):
                    continue            # `m.start() - width`, `heads[-1].start()` in a subscript: a regex match, not a thread
                recv = sub.func.value
                kind = self.resolve(recv)
                if kind in ("other", "empty"):
                    continue
                ctor = self.thread_of(recv)
                out.append(_Start(self, sub, recv, ctor, s, block, i, stack, kind == "thread"))
        return out

    def _value_used(self, call):
        """The call's value is consumed (an operand, a subscript, an argument, an assigned value): Thread.start() returns
        None, so this is some other object's start()."""
        p = self.parent.get(id(call))
        while p is not None and isinstance(p, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.Tuple, ast.List, ast.Lambda, ast.IfExp, ast.BoolOp)):
            if isinstance(p, ast.Lambda):
                return False
            p = self.parent.get(id(p))
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
    def __init__(self, unit, call, recv, ctor, stmt, block, index, stack, is_thread):
        self.unit, self.call, self.recv, self.ctor = unit, call, recv, ctor
        self.stmt, self.block, self.index, self.stack = stmt, block, index, stack
        self.is_thread = is_thread
        self.recv_text = ast.unparse(recv)
        self.target_expr = _target_expr(ctor) if ctor is not None else None
        self.target = ast.unparse(self.target_expr) if self.target_expr is not None else "?"
        self.line = call.lineno
        self.kind, self.why = ("?", "") if ctor is None else _kind(self)

    def file(self):
        return os.path.relpath(self.unit.module.path, ROOT)

    def describe(self):
        return "%s:%d %s starts Thread(target=%s) via %s.start()" % (self.file(), self.line, self.unit.qualname, self.target, self.recv_text)


# ── the kind of a thread ────────────────────────────────────────────────────────────────────────────────

def _body_kind(unit, fn_body_nodes, loops, depth):
    """The kind a function body gives its thread: loop, waits or bounded, with the reason."""
    for sub in fn_body_nodes:
        if isinstance(sub, ast.While):
            if CLOCK.search(ast.unparse(sub.test)):
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
                if nm in unit.local_defs and unit.local_defs[nm] is not None:
                    k, why = _body_kind(unit, list(ast.walk(unit.local_defs[nm])), loops, depth + 1)
                    if k != "bounded":
                        return k, "calls %s, %s" % (nm, why)
                elif nm in unit.module.functions:
                    k, why = _body_kind(unit, list(ast.walk(unit.module.functions[nm])), loops, depth + 1)
                    if k != "bounded":
                        return k, "calls %s, %s" % (nm, why)
                elif nm in loops and nm not in BUILTIN_METHODS and _product_call(unit, sub):
                    return "loop", "calls %s, a product function with a while loop" % nm
    return "bounded", "no loop, no untimed wait"


def _product_call(unit, call):
    """The call reaches a product function: a bare name the module imported (not one it defines), or an attribute of a
    module alias (km = load_source(...), sb, jd, pm: a module-level name bound to a call or imported)."""
    f = call.func
    if isinstance(f, ast.Name):
        return f.id not in unit.local_defs and f.id not in unit.module.functions and f.id in unit.module.imports
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        g = unit.module.globals.get(f.value.id)
        return f.value.id in unit.module.imports or isinstance(g, (ast.Call, ast.Attribute))
    return False


def _kind(start):
    unit, expr, ctor = start.unit, start.target_expr, start.ctor
    loops = unit.module.loops
    if expr is None:
        return "bounded", "no target"
    if isinstance(expr, ast.Lambda):
        return _body_kind(unit, list(ast.walk(expr.body)), loops, 0)
    if isinstance(expr, ast.Attribute):
        if expr.attr in FOREVER:
            return "loop", expr.attr
        if expr.attr in BLOCKING and not _has_args(ctor):
            return "waits", "the target is an untimed .%s" % expr.attr
        if expr.attr in READS:
            return "waits", "the target is a read"
        if isinstance(expr.value, ast.Name) and expr.value.id in ("self", "cls") and unit.cls is not None:
            ms = unit.module.methods_of(unit.cls, expr.attr)
            if ms:
                return _body_kind(unit, list(ast.walk(ms[0])), loops, 0)
        if expr.attr in loops and expr.attr not in BUILTIN_METHODS:
            return "loop", "a product function with a while loop"
        return "bounded", "a function outside the test module with no while loop"
    if isinstance(expr, ast.Name):
        fn = unit.local_defs.get(expr.id) or unit.module.functions.get(expr.id)
        if fn is not None:
            return _body_kind(unit, list(ast.walk(fn)), loops, 0)
        if expr.id in unit.bindings and isinstance(unit.bindings[expr.id], ast.Lambda):
            return _body_kind(unit, list(ast.walk(unit.bindings[expr.id].body)), loops, 0)
        if expr.id in loops:
            return "loop", "a product function with a while loop"
        return "bounded", "a function outside the test module with no while loop"
    return "bounded", "a callable the walk does not read"


def _release_names(start):
    """The names a waiting or polling thread would be released by: the receivers of the untimed waits and the is_set
    polls in its target, or the target's own receiver when the target is an Event.wait."""
    expr = start.target_expr
    out = set()
    if expr is None:
        return out
    if isinstance(expr, ast.Attribute) and expr.attr in BLOCKING:
        out.add(ast.unparse(expr.value))
        return out
    body = None
    if isinstance(expr, ast.Lambda):
        body = expr.body
    elif isinstance(expr, ast.Name):
        body = start.unit.local_defs.get(expr.id) or start.unit.module.functions.get(expr.id)
    elif isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name) and expr.value.id in ("self", "cls") and start.unit.cls is not None:
        ms = start.unit.module.methods_of(start.unit.cls, expr.attr)
        body = ms[0] if ms else None
    if body is not None:
        for sub in ast.walk(body):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in BLOCKING + ("is_set",):
                out.add(ast.unparse(sub.func.value))
    return out


# ── the shape of the stop ───────────────────────────────────────────────────────────────────────────────

def _is_cleanup_call(unit, call):
    nm = _callee_name(call)
    if nm in CLEANUP_NAMES:
        return True
    return isinstance(call.func, ast.Name) and call.func.id in unit.params and "cleanup" in call.func.id.lower()


def _names_a_stop(unit, call):
    for a in list(call.args) + [k.value for k in call.keywords]:
        if _stop_shaped(a):
            return True
        if isinstance(a, ast.Name):
            fn = unit.local_defs.get(a.id) or unit.module.functions.get(a.id)
            if fn is not None and _stop_shaped(fn):
                return True
            bound = unit.bindings.get(a.id)
            if isinstance(bound, ast.Lambda) and _stop_shaped(bound):
                return True
        if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.value.id in ("self", "cls") and unit.cls is not None:
            if any(_stop_shaped(m) for m in unit.module.methods_of(unit.cls, a.attr)):
                return True
    return False


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


def _cleanup_before(unit, line):
    """A cleanup that names a stop, registered at or before `line` in the unit, or in the class's setUp / setUpClass (which
    run before every test body)."""
    for s, _b, _i, _st in unit.rows:
        for sub in _expr_children(s):
            if isinstance(sub, ast.Call) and _is_cleanup_call(unit, sub) and sub.lineno <= line and _names_a_stop(unit, sub):
                return True
    if unit.cls is not None and unit.fn.name not in ("setUp", "setUpClass"):
        for name, fn in unit.hooks():
            if name in ("setUp", "setUpClass"):
                hook_unit = _Unit(unit.module, unit.cls, fn)
                for sub in ast.walk(fn):
                    if isinstance(sub, ast.Call) and _is_cleanup_call(hook_unit, sub) and _names_a_stop(hook_unit, sub):
                        return True
    return False


def _in_try_finally(stack):
    return any(isinstance(s, ast.Try) and s.finalbody and field == "body" for s, field in stack)


def _guard_ahead(unit, stmt, names, releases):
    """The shape the walk forward from `stmt` meets before the first assertion: 'finally', 'cleanup-before-first-assertion',
    'stop-before-first-assertion', or None."""
    for nxt in unit.forward(stmt):
        if isinstance(nxt, ast.Try) and nxt.finalbody:
            return "finally"
        if _is_assertion(nxt):
            return None
        loop_vars = {}
        for loop in ast.walk(nxt):
            if isinstance(loop, (ast.For, ast.comprehension)) and isinstance(loop.target, ast.Name):
                loop_vars[loop.target.id] = ast.unparse(loop.iter)
        for sub in ast.walk(nxt):
            if not isinstance(sub, ast.Call):
                continue
            if _is_cleanup_call(unit, sub) and _names_a_stop(unit, sub):
                return "cleanup-before-first-assertion"
            if isinstance(sub.func, ast.Attribute):
                r = ast.unparse(sub.func.value)
                if sub.func.attr in ("join", "shutdown", "cancel") and (r in names or (r in loop_vars and loop_vars[r] in names)):
                    return "stop-before-first-assertion"
                if sub.func.attr in ("set", "release") and r in releases:
                    return "stop-before-first-assertion"
    return None


def _self_attrs_holding(unit, name):
    """The attributes on self/cls the unit stores the local name `name` in (assigned or appended)."""
    out = []
    for s, _b, _i, _st in unit.rows:
        if isinstance(s, ast.Assign) and isinstance(s.value, ast.Name) and s.value.id == name:
            out += [t.attr for t in s.targets if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id in ("self", "cls")]
    for holder, values in unit.appends.items():
        if holder.startswith(("self.", "cls.")) and any(isinstance(v, ast.Name) and v.id == name for v in values):
            out.append(holder.split(".", 1)[1])
    return out


def _stored_attrs(start):
    """The attribute names on self/cls that hold the thread, the object its target runs on, or the event it waits on."""
    u, recv, names = start.unit, start.recv, []
    if isinstance(recv, ast.Attribute) and isinstance(recv.value, ast.Name) and recv.value.id in ("self", "cls"):
        names.append(recv.attr)
    if isinstance(recv, ast.Name):
        names += _self_attrs_holding(u, recv.id)
        for s, _b, _i, _st in u.rows:               # producer = self.producer = Thread(...)
            if isinstance(s, ast.Assign) and _is_thread_ctor(s.value) and any(isinstance(t, ast.Name) and t.id == recv.id for t in s.targets):
                names += [t.attr for t in s.targets if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id in ("self", "cls")]
    expr = start.target_expr
    holders = []
    if isinstance(expr, ast.Attribute):
        holders.append(expr.value)
    for nm in _release_names(start):
        holders.append(ast.parse(nm, mode="eval").body if nm.isidentifier() or "." in nm else None)
    body = None
    if isinstance(expr, ast.Name):
        body = u.local_defs.get(expr.id)
    elif isinstance(expr, ast.Lambda):
        body = expr.body
    if body is not None:
        for sub in ast.walk(body):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in FOREVER + BLOCKING + ("is_set",):
                holders.append(sub.func.value)
    for h in holders:
        if h is None:
            continue
        if isinstance(h, ast.Attribute) and isinstance(h.value, ast.Name) and h.value.id in ("self", "cls"):
            names.append(h.attr)
        elif isinstance(h, ast.Name):
            names += _self_attrs_holding(u, h.id)
    return sorted(set(names))


def _applies_stop(fn, attrs, loops_seam=True):
    """The function applies a stop verb to one of `attrs` (as a call or as a callback handed over), to a loop variable
    over one of them, or sets the loops' seam."""
    text = ast.unparse(fn)
    if not any(re.search(r"\b%s\b" % re.escape(a), text) for a in attrs):
        return False
    loop_vars = {}
    for loop in ast.walk(fn):
        if isinstance(loop, (ast.For, ast.comprehension)) and isinstance(loop.target, ast.Name):
            loop_vars[loop.target.id] = ast.unparse(loop.iter)
    for sub in ast.walk(fn):
        if isinstance(sub, ast.Attribute) and sub.attr in STOP_VERBS:
            recv = ast.unparse(sub.value)
            if any(re.search(r"\b%s\b" % re.escape(a), recv) for a in attrs):
                return True
            if recv in loop_vars and any(re.search(r"\b%s\b" % re.escape(a), loop_vars[recv]) for a in attrs):
                return True
            if loops_seam and sub.attr == "set" and STOP_SEAM in recv:
                return True
    return False


def _hook_stops(unit, attrs):
    for name, fn in unit.hooks():
        if _applies_stop(fn, attrs):
            return name
        if name in ("setUp", "setUpClass", "setUpModule"):
            for sub in ast.walk(fn):
                if isinstance(sub, ast.Call) and _is_cleanup_call(unit, sub) and _names_a_stop(unit, sub) \
                        and any(re.search(r"\b%s\b" % re.escape(a), ast.unparse(sub)) for a in attrs):
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
    if isinstance(start.recv, ast.Name) and isinstance(start.unit.bindings.get(start.recv.id), tuple):
        kind, inner = start.unit.bindings[start.recv.id]
        if kind == "for":
            names.add(ast.unparse(inner))
    return names


def classify(start, at=None):
    """The stop shape of one start, read in its own function or, for a helper's start, at a caller's call site `at`
    (unit, statement, stack, line)."""
    if at is None:
        unit, stmt, stack, line = start.unit, start.stmt, start.stack, start.line
    else:
        unit, stmt, stack, line = at
    if _in_try_finally(stack):
        return "finally"
    if _cleanup_before(unit, line):
        return "cleanup-before-start"
    names, releases = _start_names(start), _release_names(start)
    if at is not None:
        names = names | {ast.unparse(t) for t in getattr(stmt, "targets", [])}
    ahead = _guard_ahead(unit, stmt, names, releases)
    if ahead:
        return ahead
    attrs = _stored_attrs(start) if at is None else sorted(set(_stored_attrs(start)) | set(unit.assigned_attrs(stmt)))
    if attrs:
        hook = _hook_stops(unit, attrs)
        if hook:
            return "class-hook:" + hook
    if at is None:
        owner = _object_owned(unit)
        if owner:
            return "object-owned:" + owner
    return "tail-only"


def census(paths, loops=None):
    """Every thread start under `paths`: rows (start, shape, where) with `where` the unit the shape was read in (the
    start's own, or a caller's); an unreadable receiver is a row with shape 'unreadable'."""
    loops = product_loops() if loops is None else loops
    out = []
    for p in paths:
        m = _Module(p, loops)
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
        cls.rows = census(module_paths(), cls.loops)

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
                            "in the same function (t = threading.Thread(...)) or on self." % st.describe())
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
        a peer server whose shutdown is the cleanup registered right after the start."""
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

    def test_the_bounded_rule_excuses_at_least_one_site_or_it_is_stale(self):
        _tails, _unread, _stale, bounded = tail_only(self.rows)
        self.assertTrue(bounded, "no bounded thread has a tail-only join anymore: retire the BOUNDED shape rule")


class PlantedShapes(unittest.TestCase):
    """The rules read on synthetic modules: each shape planted alone, the walk's answer for it."""
    HEAD = ("import threading\nimport time\nimport unittest\nfrom unittest import mock\n"
            "def _loop():\n    while True:\n        time.sleep(0.01)\n"
            "def _once():\n    return 1\n\nclass T(unittest.TestCase):\n")

    def _census(self, body, allow=None):
        d = tempfile.mkdtemp(prefix="romp-tests-census-")
        p = os.path.join(d, "test_planted.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.HEAD + body)
        rows = census([p], loops={"_producer"})
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
            "        t.join()\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_bare")])
        self.assertIn(("_loop", "cleanup-before-start", "T.test_guarded"), [(s.target, sh, w) for s, sh, w in rows])

    def test_a_stop_before_the_first_assertion_is_not_named_even_for_a_loop(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        t.start()\n"
            "        t.join(5)\n"
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
        rows = census(module_paths(), loops)
        print(_report(rows, only_tail="--tail" in sys.argv))
        tails, unread, stale, bounded = tail_only(rows)
        from collections import Counter
        print("\nshapes:", dict(Counter(s for _st, s, _w in rows)))
        print("kinds:", dict(Counter(st.kind for st, _s, _w in rows)))
        print("pinned tail-only (not excused): %d, unreadable: %d, stale allow: %d, bounded tail-only (excused): %d"
              % (len(tails), len(unread), len(stale), len(bounded)))
        sys.exit(0)
    unittest.main()
