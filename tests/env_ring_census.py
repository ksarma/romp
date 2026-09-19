"""The ring-keyed census of the problem ring's doors (review round 6 of the env-pick door, 2026-09-19).

The question the census answers: which lines of kernel/sdk_backend.py, kernel/kernel.py and kernel/credentials.py can
put a row on the problem ring the dashboard's error centre reads, and which of those rows carry a value derived from
a per-session env or its flag-settings file. Round 5 found the earlier derivation (a walk over calls NAMED `_log` or
`log` whose message opened with an env head) narrower than the universal it enforced, four ways: a third door
(problem_row), a vacuous negative half (kernel.py names no call `_log`), a silent drop (a message the walk could not
reduce fell out of both assertions), and a head filter standing in for a rule. So this census is keyed on the RING,
by resolution and not by name:

  1. THE APPENDER. The one method whose body appends to `self._problems` is the ring writer (SdkBackend._log); its
     name is read from the file, and the census asserts no other def in the three files carries it, so a reference to
     that attribute on any receiver is a reference to the writer. The ring is PRIVATE to that class: every other
     reference to `_problems`, on any receiver in any of the files, must be a read inside the writer's class through
     self (a copying or counting builtin, a loop, a comprehension), the writer's own trim or __init__'s empty-list
     binding; a second appender, an insert or extend, an alias, a return, a store, a del, or a touch from another
     class or module is a CensusError (the round-6 blind-pin lens appended rows from kernel.py, from a session and
     from a second SdkBackend method with the census at its baseline).
  2. CALLS REACHING IT. Every call resolving to the writer: `self.<door>` inside the writer's class; `<any>.<door>` on
     another receiver (the backend held by a session, a `be` parameter); `<Class>.<door>(self, ...)`, unbound, its
     message read after the explicit self; `self.<door>` inside a class that binds the
     attribute in its __init__ from a parameter (ApiHealth), followed through every constructor call; a call through
     a PARAMETER (`log(...)`) followed through every call site of the enclosing function, positional or keyword,
     through `getattr(x, "<door>", None)`, `partial`, a conditional expression and a forwarded parameter, through a
     default argument (`log=_log` in the writer's class body, `log=SdkBackend._log` at module level) and
     through a closure that calls its enclosing function's parameter; a call through a local alias assigned from
     a door expression; and a call through an alias bound at CLASS scope (`_ring_door = _log` in the writer's class
     body, called as `self._ring_door(...)`; an alias whose name is also an attribute or method of another class is a
     failure, since a call on an untyped receiver could not be resolved) or at MODULE scope (`_RING = SdkBackend._log`
     or `getattr(SdkBackend, "_log")` at import, called by its bare name). Whether the message comes first or after an
     explicit self is read from the binding (bound through an instance or getattr on one; unbound through the class).
  3. CONDUITS. A function whose door call's message is one of its own parameters (SdkSession._log_quietly,
     problem_row) is a conduit: each of its call sites is a door call whose message is the argument it passes, whose
     problem= is the inner call's when that is a constant, or the site's own argument when the inner call forwards a
     parameter (problem_row's `bool(ring)`), and whose ring text follows the same rule.
  4. THE KERNEL'S FEEDERS. kernel.py has no call to the writer; its rows reach the same bell through the lists
     _sdk_problem_rows merges beside the backend's ring. The census reads _sdk_problem_rows, takes every module-level
     list it reads as a sibling of the ring, finds the functions that append to those lists (_sdk_problem,
     _note_ws_drop) and counts their call sites as door calls.
  5. DOOR VALUES. Every occurrence of a door expression that is not itself called (a `log=self._log` argument, a
     `getattr(be, "_log", None)`, an alias assignment, a default argument, a module- or class-level binding) is
     followed to a call, in function bodies and at module and class scope alike: a parameter that is called or
     forwarded, an attribute bound in __init__ that a method calls, an alias that is called (a module alias by its
     bare name in some function of its module, a class alias as an attribute call). A door value the walk cannot
     follow (one that escapes through a return, a container, an unresolvable callee, an alias nothing calls) is a
     FAILURE named by site, never a drop: a pin that cannot see must say so. So is the door's name spelled as a
     string anywhere but the getattr form the walk follows (`operator.attrgetter("_log")`, `LOG_ATTR = "_log"`,
     `vars(be)["_log"]`: a door reached by reflection), and the ring's name spelled as a string at all.
  6. TAINT. A door call is VALUE-TAINTED when its message or its ring text carries a value derived from a per-session
     env source: the data road's sources (the env attributes of a session, the 'env' key of a registry row, launch
     shape or request body, the flag-settings constants and helpers, the reserved and credential name sets and the
     functions that judge them; tag "env") and the pending-pick surface set (_reconnect_surfaces and _pick_names,
     which can name the env pick's existence; tag "pick"). Taint flows through assignments (flow-insensitively,
     within a function), into a callee's parameters from every call site and out of a callee's return to every call
     site (context-insensitively: a helper whose parameter is tainted anywhere returns taint everywhere, the safe
     direction for a guard), through tuple returns by position, and into a nested function or lambda from the
     enclosing scope; through augmented assignment (`names += k`); through an add in place (`parts.append(k)`,
     `seen.extend(names)`, `d.setdefault(k, v)`, `d.update(...)`: the argument's taint marks the receiver, a local, a
     module-level name for every reader in its module, or an attribute); through an attribute store (`self.x = v`
     marks `.x` for every reader of `.x` on any receiver in the files, the direction that finds a value stored in one
     method and read in another; the ring attribute itself excepted, being the sink); and through a dict return or
     store per key: a dict carries "env" alone, and only what sits under a key that is NOT a source (the per-session
     env's own key, 'env', is a source at every READ, so a dict does not carry it; a value re-keyed under any other
     name crosses with the dict), while the existence of a pick (tag "pick") does not cross a dict at all, since a
     session snapshot would carry the pending picks to every reader of every other field (the existence rows are the
     direct readers of the surface set). A source FUNCTION that returns a dict (the launch shape) is a source at its
     env key, not whole. `_options`' return is opaque (the whole options dict; its env overlay is a source of its own),
     and reads of the kernel's _pending_ops carry no value taint (a mixed container of every parked op kind).
  7. REDUCTION. Every door call's message is reduced to its literal head(s): a string constant, an f-string's leading
     text, the left side of a `%` or `+`, a `str()` wrap, a local followed to every assignment (a tuple unpacking to
     its position), a module-level string constant by name, a helper followed into its returns, and a conduit's
     parameter followed to every call site. A door call with NO literal head is recorded in `unreduced` by site and
     the pin holds that set to the sites it names; an unreduced call stays in the population and is judged by taint
     like every other, so nothing falls out of an assertion by failing to reduce.

From these the pin derives the CONTENT rows (value-tainted door calls filed with problem=True), holds them to the nine
the module's ENV ROWS line names by identity (writing function plus the module-level format the ring text starts
from), requires every value-tainted door call to declare problem= explicitly (False, or True with a ring text that
reduces to one module-level format the worst-case table bounds), asserts the negative half of kernel.py and
credentials.py only after asserting it FOUND their doors, and refuses to pass on a derivation that finds fewer
entries than the floors the test states (a walk that sees less than the last one did is blind, not clean).

Pure AST: imports nothing of romp, executes nothing of it, and parses each file once per process (ASTS below). The
public entry is `census(files=None, sources=None)`, returning a Census with the counts, the door calls and the
failures as data; `content_rows_line` spells the ENV ROWS line; `main` prints the summary for a command line.
"""
import ast
import asyncio
import collections
import concurrent.futures
import datetime
import io
import json
import logging
import os
import pathlib
import queue
import re
import socket
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
KERNEL_DIR = os.path.join(ROOT, "kernel")
DEFAULT_FILES = (os.path.join(KERNEL_DIR, "sdk_backend.py"), os.path.join(KERNEL_DIR, "kernel.py"),
                 os.path.join(KERNEL_DIR, "credentials.py"))

# The per-session env sources (the data road of review round 5, 35 identifiers, plus the pending-pick surface set of
# its lens A). Keyed by kind; a file-qualified entry names the file by basename so a synthetic module can carry the
# same names without being mistaken for the real one. Tags: "env" (a value of the pick, its file or its rule),
# "pick" (the existence of a pending pick, never a name or a value).
DEFAULT_SOURCES = {
    "attr": {"env_vars": "env", "_launched_env": "env", "_reconnect_surfaces": "pick"},
    "key": {"env": "env"},
    "name": {
        ("sdk_backend.py", "FLAG_SETTINGS_DIR"): "env", ("sdk_backend.py", "FLAG_SETTINGS_KEYS"): "env",
        ("sdk_backend.py", "_flag_settings_lock"): "env", ("sdk_backend.py", "FLAG_SID_REASONS"): "env",
        ("sdk_backend.py", "ENV_RESERVED_NAMES"): "env", ("sdk_backend.py", "AUTH_ENV_NAMES"): "env",
        ("kernel.py", "_ENV_RESERVED_NAMES"): "env",
        ("credentials.py", "CREDENTIAL_ENV_SUFFIXES"): "env", ("credentials.py", "OP_ENV_NAMES"): "env",
        ("credentials.py", "OP_ENV_PREFIX"): "env", ("credentials.py", "CONTROL_TOKEN_VAR"): "env",
        ("credentials.py", "CREDENTIAL_RING_FORMAT"): "env", ("credentials.py", "CREDENTIAL_RING_ROADS"): "env",
    },
    "func": {
        ("sdk_backend.py", "flag_settings_path"): "env", ("sdk_backend.py", "_flag_settings_sid_error"): "env",
        ("sdk_backend.py", "_flag_settings_link_rows"): "env", ("sdk_backend.py", "env_request_error"): "env",
        ("sdk_backend.py", "spawn_env_secret_names"): "env", ("sdk_backend.py", "split_spawn_secrets"): "env",
        ("sdk_backend.py", "env_credential_names"): "env", ("sdk_backend.py", "stored_offender_ring_text"): "env",
        ("sdk_backend.py", "SdkBackend._launch_shape"): "env", ("sdk_backend.py", "SdkSession._launched_shape"): "env",
        ("sdk_backend.py", "SdkSession._pick_names"): "pick", ("sdk_backend.py", "SdkSession._pick_names_locked"): "pick",
        ("kernel.py", "_env_error"): "env",
        ("credentials.py", "is_credential_env_name"): "env", ("credentials.py", "is_op_env_name"): "env",
        ("credentials.py", "credential_env_names"): "env", ("credentials.py", "credential_env_refusal"): "env",
        ("credentials.py", "_env_roads"): "env", ("credentials.py", "credential_env_ring_text"): "env",
    },
    # read at function level only, never a value (the data road's decision 3): the kernel's parked-op mirror
    "opaque_names": {("kernel.py", "_pending_ops")},
    # a return the walk treats as untainted whatever flows in: the whole options dict, whose env overlay is a source
    "opaque_returns": {("sdk_backend.py", "SdkBackend._options")},
}

# Method names of the builtin and stdlib types the three files use: an attribute call `x.<name>(...)` on a receiver
# other than self is NOT resolved to a def of the same bare name in our files when the name is one of these (a
# `reg.get(...)` is a dict's get, not _SharedParseView.get). Self-calls resolve through the class first regardless.
COMMON_METHODS = set()
for _t in (str, bytes, dict, list, set, frozenset, tuple, int, float, bool, object, pathlib.Path, threading.Thread,
           threading.Event, type(threading.Lock()), type(threading.RLock()), asyncio.Task, asyncio.Future,
           asyncio.Queue, asyncio.Event, asyncio.Lock, asyncio.AbstractEventLoop, socket.socket, subprocess.Popen,
           io.TextIOWrapper, io.BytesIO, re.Pattern, re.Match, collections.deque, collections.Counter,
           collections.OrderedDict, queue.Queue, logging.Logger, datetime.datetime, datetime.timedelta,
           concurrent.futures.Future, concurrent.futures.ThreadPoolExecutor, json, os, sys, re, io, subprocess):
    COMMON_METHODS.update(n for n in dir(_t) if not n.startswith("__"))
COMMON_METHODS.discard("_log")   # logging.Logger has one; the door's own name is never filtered

ASTS = {}   # path -> (source, tree): parsed once per process


def parsed(path):
    path = os.path.realpath(path)
    hit = ASTS.get(path)
    if hit is None:
        src = pathlib.Path(path).read_text(encoding="utf-8")
        hit = ASTS[path] = (src, ast.parse(src, filename=path))
    return hit


class Fn:
    __slots__ = ("qual", "name", "file", "base", "node", "cls", "parent", "params", "kwonly", "vararg", "kwarg",
                 "defaults", "kind", "calls", "assigns", "returns", "lexical", "nested", "globals_", "_params_set",
                 "_assigned", "_loops", "_chain")

    def __init__(self, qual, name, file, node, cls, parent):
        self.qual, self.name, self.file, self.node, self.cls, self.parent = qual, name, file, node, cls, parent
        self.base = os.path.basename(file)
        self.calls, self.assigns, self.returns, self.nested, self.globals_ = [], [], [], {}, set()
        self.lexical = {}          # id(call) -> True when the call sits inside an except handler of this def
        self.kind = "function"     # function | method | static | classmethod | lambda
        args = node.args
        self.params = [a.arg for a in getattr(args, "posonlyargs", ()) + args.args]
        self.kwonly = [a.arg for a in args.kwonlyargs]
        self.vararg = args.vararg.arg if args.vararg else None
        self.kwarg = args.kwarg.arg if args.kwarg else None
        self.defaults = {}
        pos = self.params[len(self.params) - len(args.defaults):] if args.defaults else []
        for name_, d in zip(pos, args.defaults):
            self.defaults[name_] = d
        for a, d in zip(args.kwonlyargs, args.kw_defaults):
            if d is not None:
                self.defaults[a.arg] = d
        self._params_set = self._assigned = self._loops = self._chain = None

    def all_params(self):
        if self._params_set is None:
            self._params_set = frozenset(self.params) | frozenset(self.kwonly) | ({self.vararg} if self.vararg else set()) \
                | ({self.kwarg} if self.kwarg else set())
        return self._params_set

    def assigned(self):
        """{name: [assignment statements]} over this function's own body (nested defs excluded)."""
        if self._assigned is None:
            out = {}
            for st in self.assigns:
                for t in Census._targets(st):
                    if isinstance(t, ast.Name):
                        out.setdefault(t.id, []).append(st)
                    elif isinstance(t, ast.Starred) and isinstance(t.value, ast.Name):
                        out.setdefault(t.value.id, []).append(st)
            self._assigned = out
        return self._assigned

    def loops(self):
        """The for loops, comprehensions and with items of this function's own body."""
        if self._loops is None:
            out = []
            stack = [self.node]
            while stack:
                n = stack.pop()
                for ch in ast.iter_child_nodes(n):
                    if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                        continue
                    if isinstance(ch, (ast.For, ast.AsyncFor, ast.comprehension, ast.With, ast.AsyncWith)):
                        out.append(ch)
                    stack.append(ch)
            self._loops = out
        return self._loops

    def __repr__(self):
        return "Fn(%s:%s@%d)" % (self.base, self.qual, self.node.lineno)


class Cls:
    __slots__ = ("name", "file", "node", "bases", "methods", "bindings", "class_assigns")

    def __init__(self, name, file, node, bases):
        self.name, self.file, self.node, self.bases = name, file, node, bases
        self.methods, self.bindings = {}, {}     # bindings: attr -> [(value node, Fn)] for `self.attr = value`
        self.class_assigns = {}                  # name -> value node for `name = value` in the class body itself


class ScopeFn:
    """A stand-in for Fn where an expression is evaluated at MODULE or CLASS scope (a class-body alias, a method's
    default argument, a module-level assignment): no parameters, no locals, no calls of its own, so every lookup the
    walk makes through it falls to the class body and the module. `kind` is "scope"."""
    __slots__ = ("qual", "name", "file", "base", "node", "cls", "parent", "kind", "calls", "assigns", "returns",
                 "lexical", "nested", "_chain")

    def __init__(self, mod, cls):
        self.cls, self.parent, self.kind = cls, None, "scope"
        self.file, self.base, self.node = mod.path, mod.base, cls.node if cls else mod.tree
        self.name = self.qual = ("<class %s>" % cls.name) if cls else "<module>"
        self.calls, self.assigns, self.returns, self.nested, self.lexical, self._chain = [], [], [], {}, {}, None

    @staticmethod
    def all_params():
        return frozenset()

    @staticmethod
    def assigned():
        return {}

    def __repr__(self):
        return "ScopeFn(%s:%s)" % (self.base, self.qual)


class Mod:
    __slots__ = ("path", "base", "src", "tree", "top_defs", "classes", "top_assigns", "top_lists", "fns")

    def __init__(self, path):
        self.path = os.path.realpath(path)
        self.base = os.path.basename(path)
        self.src, self.tree = parsed(path)
        self.top_defs, self.classes, self.top_assigns, self.top_lists, self.fns = {}, {}, {}, set(), []


class DoorCall:
    """One call that reaches the ring. `site` is the call node whose line names it; `kind` says how it resolves."""
    __slots__ = ("file", "base", "lineno", "fn", "kind", "node", "message", "ring_text", "problem", "key", "heads",
                 "unreduced", "taint", "ring_formats", "lexical", "via", "alts")

    def __init__(self, fn, node, kind, message, ring_text, problem, key, via=None):
        self.fn, self.node, self.kind = fn, node, kind
        self.file, self.base, self.lineno = fn.file, fn.base, node.lineno
        self.message, self.ring_text, self.problem, self.key, self.via = message, ring_text, problem, key, via
        self.heads, self.unreduced, self.taint, self.ring_formats, self.lexical = [], False, frozenset(), [], False
        self.alts = []     # (problem, ring_text, inner DoorCall) of further inner calls the same conduit site reaches

    def decls(self):
        """Every problem= declaration this site files under: its own, plus each alternative inner call's."""
        return [self.problem_decl] + [DoorCall._decl(p) for p, _r, _i in self.alts]

    @staticmethod
    def _decl(p):
        if p is None:
            return ("none",)
        if isinstance(p, ast.Constant):
            return ("const", p.value)
        if isinstance(p, tuple) and p[0] == "const":
            return p
        return ("expr", ast.unparse(p) if isinstance(p, ast.AST) else str(p))

    @property
    def owner(self):
        return self.fn.name if self.fn.kind != "lambda" else self.fn.qual

    @property
    def problem_decl(self):
        """("const", True|False) | ("expr", text) | ("none",)"""
        return DoorCall._decl(self.problem)

    def __repr__(self):
        return "%s:%d %s [%s]" % (self.base, self.lineno, self.fn.qual, self.kind)


class CensusError(AssertionError):
    """A failure of the derivation itself (a door value the walk cannot follow, a ring writer it cannot find)."""


class Census:
    def __init__(self, files, sources):
        self.files = [os.path.realpath(f) for f in files]
        self.sources = sources
        self.mods = {}
        self.parents = {}
        self.fn_of = {}          # id(node) -> Fn for Call/Name/Attribute/Return nodes
        self.defs_by_name = collections.defaultdict(list)
        self.classes_by_name = collections.defaultdict(list)
        self.cls_by_node = {}    # id(ClassDef) -> Cls
        self.fn_by_node = {}     # id(FunctionDef | Lambda) -> Fn
        self.attr_readers = collections.defaultdict(set)   # attribute name -> Fns reading `<x>.<name>`
        self.ring_refs = []      # (Mod, Attribute node, enclosing Fn or None) for every `<x>._problems` in the files
        self.ident_consts = []   # (Mod, Constant node, enclosing Fn or None) for every string constant spelling an identifier
        self.all_fns = []
        self.failures = []       # (kind, base, lineno, text)
        for f in self.files:
            self._index(f)
        self._resolve_all_calls()
        self._find_writer()
        self._scope_aliases()
        self._door_calls()
        self._follow_door_values()
        self._taint()
        self._reduce_all()
        self._classify()

    # ------------------------------------------------------------------ indexing
    def _index(self, path):
        mod = Mod(path)
        self.mods[mod.path] = mod
        self.mods[mod.base] = mod

        def new_fn(node, cls, parent, name, kind):
            if parent is None:
                qual = ("%s.%s" % (cls.name, name)) if cls else name
            else:
                qual = "%s.<locals>.%s" % (parent.qual, name)
            fn = Fn(qual, name, mod.path, node, cls, parent)
            fn.kind = kind
            mod.fns.append(fn)
            self.all_fns.append(fn)
            self.fn_by_node[id(node)] = fn
            self.defs_by_name[name].append(fn)
            if parent is not None:
                parent.nested.setdefault(name, []).append(fn)
            return fn

        def handle(child, cls, fn, handler):
            """One node, in the scope (cls, fn) and lexical handler state of its parent."""
            if isinstance(child, ast.Attribute):
                if child.attr == self.RING_ATTR:
                    self.ring_refs.append((mod, child, fn))
                if fn is not None and isinstance(child.ctx, ast.Load):
                    self.attr_readers[child.attr].add(fn)
            elif isinstance(child, ast.Constant) and isinstance(child.value, str) and child.value.isidentifier():
                self.ident_consts.append((mod, child, fn))
            if isinstance(child, ast.ClassDef):
                c = Cls(child.name, mod.path, child, [ast.unparse(b) for b in child.bases])
                if fn is None:
                    mod.classes[child.name] = c
                self.classes_by_name[child.name].append(c)
                self.cls_by_node[id(child)] = c
                for d in child.decorator_list + child.bases:
                    self.parents[d] = child
                    handle(d, cls, fn, handler)
                for stmt in child.body:
                    self.parents[stmt] = child
                    handle(stmt, c, None, False)
                return
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decos = [ast.unparse(d) for d in child.decorator_list]
                kind = "function"
                if cls is not None and fn is None:
                    kind = "static" if "staticmethod" in decos else "classmethod" if "classmethod" in decos else "method"
                f = new_fn(child, cls if fn is None else None, fn, child.name, kind)
                if cls is not None and fn is None:
                    cls.methods[child.name] = f
                elif fn is None and cls is None:
                    mod.top_defs[child.name] = f
                for d in child.decorator_list:
                    self.parents[d] = child
                    handle(d, cls, fn, handler)
                self.parents[child.args] = child
                handle(child.args, cls, fn, handler)
                if child.returns is not None:
                    self.parents[child.returns] = child
                    handle(child.returns, cls, fn, handler)
                for stmt in child.body:
                    self.parents[stmt] = child
                    handle(stmt, None, f, False)
                return
            if isinstance(child, ast.Lambda):
                f = new_fn(child, None, fn, "<lambda@%d>" % child.lineno, "lambda")
                self.parents[child.args] = child
                handle(child.args, cls, fn, handler)
                self.parents[child.body] = child
                self.fn_of[id(child.body)] = f
                f.returns.append(child.body)
                handle(child.body, None, f, False)
                return
            if isinstance(child, ast.ExceptHandler):
                handler = True
            elif isinstance(child, ast.Global):
                if fn is not None:
                    fn.globals_.update(child.names)
            elif isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
                if fn is not None:
                    fn.assigns.append(child)
                    if fn.cls is not None and fn.kind == "method" and isinstance(child, (ast.Assign, ast.AnnAssign)) and child.value is not None:
                        for t in (child.targets if isinstance(child, ast.Assign) else [child.target]):
                            if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                                fn.cls.bindings.setdefault(t.attr, []).append((child.value, fn))
                elif cls is not None:
                    # the class body's own names (a class-level alias `_ring = _log`, a constant): a Name evaluated in
                    # the class body or in a method's default argument resolves here first
                    if isinstance(child, ast.Assign):
                        for t in child.targets:
                            if isinstance(t, ast.Name):
                                cls.class_assigns.setdefault(t.id, child.value)
                    elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name) and child.value is not None:
                        cls.class_assigns.setdefault(child.target.id, child.value)
                elif cls is None:
                    if isinstance(child, ast.Assign):
                        for t in child.targets:
                            if isinstance(t, ast.Name):
                                mod.top_assigns.setdefault(t.id, child.value)
                                if isinstance(child.value, (ast.List, ast.ListComp)):
                                    mod.top_lists.add(t.id)
                    elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name) and child.value is not None:
                        mod.top_assigns.setdefault(child.target.id, child.value)
            elif isinstance(child, ast.Return):
                if fn is not None:
                    fn.returns.append(child.value)
                    self.fn_of[id(child)] = fn
            elif fn is not None:
                if isinstance(child, ast.Call):
                    fn.calls.append(child)
                    fn.lexical[id(child)] = handler
                    self.fn_of[id(child)] = fn
                elif isinstance(child, (ast.Name, ast.Attribute)):
                    self.fn_of[id(child)] = fn
            for sub in ast.iter_child_nodes(child):
                self.parents[sub] = child
                handle(sub, cls, fn, handler)

        for stmt in mod.tree.body:
            self.parents[stmt] = mod.tree
            handle(stmt, None, None, False)

    # ------------------------------------------------------------------ lookups
    def fn_for(self, node):
        return self.fn_of.get(id(node))

    def enclosing_fn(self, node):
        while node in self.parents:
            node = self.parents[node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                for fn in self.all_fns:
                    if fn.node is node:
                        return fn
        return None

    def scope_of(self, node):
        """The node whose namespace a Name at `node`'s position resolves in: the nearest enclosing def or lambda whose
        BODY holds it (a default argument, a decorator and an annotation belong to the scope enclosing the def), else
        the class body, else the module. None for a node the index never saw."""
        child, up = node, self.parents.get(node)
        while up is not None:
            if isinstance(up, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if any(child is st for st in up.body):
                    return up
            elif isinstance(up, ast.Lambda):
                if child is up.body:
                    return up
            elif isinstance(up, ast.ClassDef):
                if any(child is st for st in up.body):
                    return up
            elif isinstance(up, ast.Module):
                return up
            child, up = up, self.parents.get(up)
        return None

    def scope_fn(self, node, mod):
        """A ScopeFn for a node evaluated at module or class scope (None when the node sits in a function body)."""
        sc = self.scope_of(node)
        if isinstance(sc, ast.ClassDef):
            return ScopeFn(mod, self.cls_by_node.get(id(sc)))
        if isinstance(sc, ast.Module):
            return ScopeFn(mod, None)
        return None

    def mod_of(self, fn):
        return self.mods[fn.file]

    def scope_chain(self, fn):
        if fn._chain is None:
            out, f = [], fn
            while f is not None:
                out.append(f)
                f = f.parent
            fn._chain = out
        return fn._chain

    def is_param(self, name, fn):
        """The Fn (fn or an enclosing one) whose parameter `name` is, or None."""
        for f in self.scope_chain(fn):
            if name in f.all_params():
                return f
            if name in f.assigned():
                return None   # shadowed by a local before reaching an outer parameter
        return None

    def _assigns_name(self, fn, name):
        return fn.assigned().get(name, [])

    @staticmethod
    def _targets(st):
        if isinstance(st, ast.Assign):
            out = []
            for t in st.targets:
                out.extend(t.elts if isinstance(t, (ast.Tuple, ast.List)) else [t])
            return out
        if isinstance(st, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            return [st.target]
        return []

    def class_of(self, fn):
        f = fn
        while f is not None and f.cls is None:
            f = f.parent
        return f.cls if f is not None else None

    def mro(self, cls):
        out, todo, seen = [], [cls], set()
        while todo:
            c = todo.pop(0)
            if id(c) in seen:
                continue
            seen.add(id(c))
            out.append(c)
            for b in c.bases:
                b = b.split(".")[-1]
                todo.extend(self.classes_by_name.get(b, []))
        return out

    def subclasses(self, cls):
        return [c for lst in self.classes_by_name.values() for c in lst if c is not cls and cls in self.mro(c)]

    def method_lookup(self, cls, name):
        out = []
        for c in self.mro(cls):
            if name in c.methods:
                out.append(c.methods[name])
                break
        for c in self.subclasses(cls):
            if name in c.methods and c.methods[name] not in out:
                out.append(c.methods[name])
        return out

    def resolve_callee(self, call, fn):
        """The Fn(s) a call may reach, with how it was addressed ('name', 'self', 'attr', 'class') for argument binding."""
        f = call.func
        if isinstance(f, ast.Name):
            if self.is_param(f.id, fn) is not None:
                return []
            for s in self.scope_chain(fn):
                if f.id in s.nested:
                    return [(x, "name") for x in s.nested[f.id]]
                if any(self._assigns_name(s, f.id)):
                    return []
            mod = self.mod_of(fn)
            if f.id in mod.top_defs:
                return [(mod.top_defs[f.id], "name")]
            if f.id in mod.classes:
                init = mod.classes[f.id].methods.get("__init__")
                return [(init, "self")] if init else []
            out = []
            for m in set(self.mods.values()):
                if m is mod:
                    continue
                if f.id in m.top_defs:
                    out.append((m.top_defs[f.id], "name"))
                elif f.id in m.classes and "__init__" in m.classes[f.id].methods:
                    out.append((m.classes[f.id].methods["__init__"], "self"))
            return out
        if isinstance(f, ast.Attribute):
            attr = f.attr
            if isinstance(f.value, ast.Name) and f.value.id in ("self", "cls"):
                cls = self.class_of(fn)
                if cls is not None:
                    ms = self.method_lookup(cls, attr)
                    if ms:
                        return [(m, "self") for m in ms]
                    return []
            if isinstance(f.value, ast.Name) and f.value.id in self.classes_by_name and f.value.id not in ("self", "cls"):
                out = []
                for c in self.classes_by_name[f.value.id]:
                    if attr in c.methods:
                        out.append((c.methods[attr], "class"))
                if out:
                    return out
            if attr in COMMON_METHODS:
                return []
            out = []
            for d in self.defs_by_name.get(attr, []):
                if d.kind != "lambda" and d.parent is None:
                    out.append((d, "attr" if d.cls is not None else "name"))
            for c in self.classes_by_name.get(attr, []):
                if "__init__" in c.methods:
                    out.append((c.methods["__init__"], "self"))
            return out
        return []

    def bind_args(self, call, callee, via):
        """{param name: argument node} for a call reaching `callee`; a missing parameter with a default maps to it."""
        params = list(callee.params)
        if callee.kind in ("method", "classmethod") and via in ("self", "attr") and params:
            params = params[1:]
        elif callee.kind == "classmethod" and via == "class" and params:
            params = params[1:]
        out = {}
        pos = [a for a in call.args if not isinstance(a, ast.Starred)]
        for name, a in zip(params, pos):
            out[name] = a
        for kw in call.keywords:
            if kw.arg is None:
                continue
            if kw.arg in params or kw.arg in callee.kwonly:
                out[kw.arg] = kw.value
            elif callee.kwarg:
                out.setdefault(callee.kwarg, kw.value)
        for name, d in callee.defaults.items():
            out.setdefault(name, d)
        return out

    def _resolve_all_calls(self):
        self.callers = collections.defaultdict(list)     # Fn -> [(call, caller Fn, via)]
        self.callees = {}                                # id(call) -> [(Fn, via)]
        for fn in self.all_fns:
            for call in fn.calls:
                res = self.resolve_callee(call, fn)
                self.callees[id(call)] = res
                for callee, via in res:
                    self.callers[callee].append((call, fn, via))

    # ------------------------------------------------------------------ the ring writer
    RING_ATTR = "_problems"
    # what may be done to a list in place, by method name: the ring accepts none of these but the writer's one append,
    # and a merge-read list accepts them from its feeders (append, insert and extend add rows; the rest reorder or drop)
    LIST_ADDERS = frozenset({"append", "insert", "extend", "appendleft", "extendleft", "__iadd__", "__setitem__"})
    LIST_MUTATORS = LIST_ADDERS | frozenset({"pop", "remove", "clear", "sort", "reverse", "__delitem__"})
    RING_READS = frozenset({"list", "reversed", "len", "tuple", "iter", "enumerate", "sorted", "any", "all", "sum"})

    def _ring_refs(self):
        """Every reference to the ring attribute (`<any receiver>._problems`) in the three files, with the function it
        sits in (None at module or class scope). Blind-pin lens of review round 6: a row appended to the ring from
        kernel.py (`be._problems.append(...)`), from a session (`self.backend._problems.append(...)`) or by a second
        SdkBackend method (`self._problems.insert(0, ...)`) left the census at its baseline, because the writer was
        found by ONE shape (`self._problems.append`) and every other touch of the ring went unread."""
        return list(self.ring_refs)

    def _find_writer(self):
        refs = self._ring_refs()
        appenders, mutations = [], []
        for mod, node, fn in refs:
            up = self.parents.get(node)
            if isinstance(up, ast.Attribute) and up.attr in self.LIST_MUTATORS:
                call = self.parents.get(up)
                if isinstance(call, ast.Call) and call.func is up:
                    (appenders if up.attr == "append" else mutations).append((fn, call, node, mod))
        if mutations:
            raise CensusError("the ring is mutated other than by the writer's append: %s" % "; ".join(
                "%s:%d %s.%s in %s" % (mod.base, node.lineno, ast.unparse(node), self.parents[node].attr, fn.qual if fn else "<scope>")
                for fn, _call, node, mod in mutations))
        if len(appenders) != 1:
            raise CensusError("the ring has %d appenders (<receiver>._problems.append): %r" % (
                len(appenders), [(mod.base, node.lineno, fn.qual if fn else "<scope>") for fn, _c, node, mod in appenders]))
        self.writer, self.append_call, app_node, _mod = appenders[0]
        if self.writer is None or not (isinstance(app_node.value, ast.Name) and app_node.value.id == "self") or self.writer.cls is None:
            raise CensusError("the ring's appender is not a method appending to its own self._problems: %r" % (self.writer,))
        self.door = self.writer.name
        self.writer_cls = self.writer.cls
        others = [d for d in self.defs_by_name.get(self.door, []) if d is not self.writer]
        if others:
            raise CensusError("the door's name %r is defined more than once: %r" % (self.door, others))
        params = self.writer.params
        if len(params) < 2:
            raise CensusError("the writer takes no message parameter: %r" % (params,))
        self.msg_param = params[1]
        for needed in ("problem", "key", "ring_text"):
            if needed not in self.writer.all_params():
                raise CensusError("the writer has no %r parameter" % needed)
        # the ring is PRIVATE to its writer's class: every other reference to it is a read inside that class through
        # self, consumed by a copying or counting builtin, a loop or a comprehension (the writer's repeat lookup,
        # problems(), problem_keyed()), the writer's own trim (`del self._problems[:-N]`) or __init__'s empty-list
        # binding; a reference from any other class or module, an alias, a return, a store or a del anywhere else is a
        # census failure (an escape the walk cannot follow, or a second writer)
        for mod, node, fn in refs:
            if node is app_node:
                continue
            where = "%s:%d in %s" % (mod.base, node.lineno, fn.qual if fn else "<scope>")
            if fn is None or self.class_of(fn) is not self.writer_cls or not (isinstance(node.value, ast.Name) and node.value.id == "self"):
                raise CensusError("the ring is touched outside its writer's class (%s): %s" % (ast.unparse(node), where))
            up = self.parents.get(node)
            if isinstance(node.ctx, ast.Store):
                if not (fn.name == "__init__" and isinstance(up, (ast.Assign, ast.AnnAssign))
                        and isinstance(getattr(up, "value", None), ast.List) and not up.value.elts):
                    raise CensusError("the ring is rebound outside __init__'s empty list: %s" % where)
                continue
            if isinstance(node.ctx, ast.Del):
                raise CensusError("the ring is deleted: %s" % where)
            if isinstance(up, ast.Subscript) and isinstance(up.ctx, ast.Del):
                if fn is not self.writer:
                    raise CensusError("the ring is trimmed outside the writer: %s" % where)
                continue
            if isinstance(up, ast.Subscript) and isinstance(up.ctx, ast.Store):
                raise CensusError("a ring entry is assigned in place: %s" % where)
            if isinstance(up, ast.Call) and isinstance(up.func, ast.Name) and up.func.id in self.RING_READS and any(a is node for a in up.args):
                continue
            if isinstance(up, ast.comprehension) and up.iter is node:
                continue
            if isinstance(up, (ast.For, ast.AsyncFor)) and up.iter is node:
                continue
            if isinstance(up, ast.Subscript) and isinstance(up.ctx, ast.Load):
                continue
            raise CensusError("the ring is read where the walk cannot follow it (%s): %s" % (ast.unparse(up)[:60] if up is not None else "?", where))
        # the kernel's feeders: the module-level lists _sdk_problem_rows reads, and the functions adding to them (by
        # append, insert, extend or +=)
        self.merge_reads, self.feeders, self.feeder_appends = [], {}, []
        for fn in self.all_fns:
            if fn.name == "_sdk_problem_rows" and fn.parent is None:
                mod = self.mod_of(fn)
                for node in ast.walk(fn.node):
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in mod.top_lists:
                        self.merge_reads.append(("list", node.id, node.lineno))
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "problems":
                        self.merge_reads.append(("ring", "problems", node.lineno))
                lists = {name for kind, name, _ln in self.merge_reads if kind == "list"}
                for f2 in mod.fns:
                    for call in f2.calls:
                        c = call.func
                        if (isinstance(c, ast.Attribute) and c.attr in self.LIST_ADDERS and isinstance(c.value, ast.Name)
                                and c.value.id in lists and call.args):
                            self.feeder_appends.append((f2, call, c.value.id))
                            self.feeders[f2] = call
                    for st in f2.assigns:
                        if isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name) and st.target.id in lists:
                            self.feeder_appends.append((f2, st, st.target.id))
                            self.feeders[f2] = st

    # ------------------------------------------------------------------ door expressions and door calls
    def _scope_aliases(self):
        """Aliases of the door bound at CLASS or MODULE scope, resolved before the door calls are read (blind-pin lens
        of review round 6: a module-level `_RING = SdkBackend._log` or `getattr(SdkBackend, "_log")`, a class-body
        `_ring = _log` and a method default `log=_log` each carried a tenth env row past the census, which followed
        door values inside function bodies only). A call through a class alias (`self._ring(...)`, `<any>._ring(...)`)
        or a module alias (`_RING(...)`) is a door call of kind "alias"; the values themselves are followed to a call
        or failed by _follow_door_values like every other door value."""
        self.class_alias_doors = {}     # alias name -> [(Cls, value node)]
        self.module_alias_doors = {}    # (module path, alias name) -> value node
        self.ambiguous_aliases = set()  # class alias names also bound as an attribute or a method of another class
        for mod in {m.path: m for m in self.mods.values()}.values():
            sfn = ScopeFn(mod, None)
            for name, value in mod.top_assigns.items():
                if self.door_value(value, sfn) == "door":
                    self.module_alias_doors[(mod.path, name)] = value
            for lst in self.classes_by_name.values():
                for cls in lst:
                    if cls.file != mod.path:
                        continue
                    csfn = ScopeFn(mod, cls)
                    for name, value in cls.class_assigns.items():
                        if self.door_value(value, csfn) == "door":
                            self.class_alias_doors.setdefault(name, []).append((cls, value))
        # an alias name that is also an instance attribute, a method or a class-body name of an UNRELATED class cannot
        # be resolved on a receiver the walk does not type: named, so the alias is renamed rather than half-followed
        for name, lst in self.class_alias_doors.items():
            owners = {id(c) for c, _v in lst}
            elsewhere = []
            for cl in self.classes_by_name.values():
                for c in cl:
                    if id(c) in owners:
                        continue
                    if name in c.bindings or name in c.methods or name in c.class_assigns:
                        elsewhere.append("%s.%s" % (c.name, name))
            if elsewhere:
                self.ambiguous_aliases.add(name)
                for c, v in lst:
                    self.failures.append(("door-alias-ambiguous", os.path.basename(c.file), v.lineno,
                                          "class alias %s of %s is also a name of %s; a call on an untyped receiver cannot be resolved"
                                          % (name, c.name, ", ".join(sorted(elsewhere)))))

    def door_value(self, e, fn, seen=None):
        """'door' | 'not' | 'unfollowed' for an expression used as a value (or as a callee)."""
        seen = seen if seen is not None else set()
        door = self.door
        if isinstance(e, ast.Attribute) and e.attr != door and e.attr in getattr(self, "class_alias_doors", {}):
            # a class-body alias of the door (resolved in _scope_aliases), read through a receiver: `self.<alias>` in a
            # class related to the alias's owner, `<Class>.<alias>` on the owner, or any other receiver when the alias's
            # name is unambiguous across the files (an ambiguous name, one also bound as an instance attribute or a
            # method elsewhere, is a failure recorded by _scope_aliases; ApiHealth's `self._ring` deque is such a name)
            owners = [c for c, _v in self.class_alias_doors[e.attr]]
            if isinstance(e.value, ast.Name) and e.value.id in ("self", "cls"):
                cls = self.class_of(fn)
                if cls is None:
                    return "not"
                related = {id(c) for c in self.mro(cls)} | {id(c) for c in self.subclasses(cls)}
                return "door" if any(id(c) in related for c in owners) else "not"
            if isinstance(e.value, ast.Name) and e.value.id in self.classes_by_name:
                return "door" if any(c.name == e.value.id for c in owners) else "not"
            return "door" if e.attr not in self.ambiguous_aliases else "not"
        if isinstance(e, ast.Attribute) and e.attr == door:
            if isinstance(e.value, ast.Name) and e.value.id == "self":
                cls = self.class_of(fn)
                if cls is not None:
                    if self.writer_cls in self.mro(cls):
                        return "door"
                    binds = [b for c in self.mro(cls) for b in c.bindings.get(door, [])]
                    if not binds:
                        return "unfollowed"
                    return self._combine(self.door_value(v, bfn, seen) for v, bfn in binds)
            return "door"
        if isinstance(e, ast.Call):
            f = e.func
            if isinstance(f, ast.Name) and f.id == "getattr" and len(e.args) >= 2 and isinstance(e.args[1], ast.Constant) \
                    and e.args[1].value == door:
                return "door"
            if (isinstance(f, ast.Name) and f.id == "partial") or (isinstance(f, ast.Attribute) and f.attr == "partial"):
                return self.door_value(e.args[0], fn, seen) if e.args else "not"
            return "not"
        if isinstance(e, ast.IfExp):
            return self._combine([self.door_value(e.body, fn, seen), self.door_value(e.orelse, fn, seen)])
        if isinstance(e, ast.BoolOp):
            return self._combine(self.door_value(v, fn, seen) for v in e.values)
        if isinstance(e, ast.Name):
            owner = self.is_param(e.id, fn)
            if owner is not None:
                k = (owner.qual, e.id)
                if k in seen:
                    return "not"
                seen.add(k)
                binds = self.param_bindings(owner, e.id)
                return self._combine(self.door_value(v, caller, seen) for v, caller in binds)
            for s in self.scope_chain(fn):
                sts = list(self._assigns_name(s, e.id))
                if sts:
                    vals = []
                    for st in sts:
                        v = self._value_for(st, e.id)
                        if v is not None and not isinstance(v, tuple):
                            vals.append(v)
                    return self._combine(self.door_value(v, s, seen) for v in vals)
            return self._scope_name_value(e, fn, seen, self.door_value, "door", "not")
        return "not"

    def _scope_name_value(self, e, fn, seen, follow, hit, miss):
        """A bare Name that is no parameter and no local of `fn`: the class body it is evaluated in (the writer's own
        method name there, or a class-body alias), then the module's top-level assignments; `follow` is applied to the
        binding found (door_value or door_binding), `hit` returned for the writer's own name, `miss` when there is none."""
        sc = self.scope_of(e)
        mod = self.mod_of(fn)
        if isinstance(sc, ast.ClassDef):
            c = self.cls_by_node.get(id(sc))
            if c is not None:
                if e.id == self.door and c.methods.get(self.door) is self.writer:
                    return hit
                if e.id in c.class_assigns:
                    k = ("class", c.name, e.id)
                    if k in seen:
                        return miss
                    seen.add(k)
                    return follow(c.class_assigns[e.id], ScopeFn(mod, c), seen)
        if e.id in mod.top_assigns:
            k = ("module", mod.path, e.id)
            if k in seen:
                return miss
            seen.add(k)
            return follow(mod.top_assigns[e.id], ScopeFn(mod, None), seen)
        return miss

    def door_binding(self, e, fn, seen=None):
        """'bound' | 'unbound' | 'mixed' | None for a door expression: whether a call through it supplies the message
        FIRST (a bound method, `be._log(m)`) or after an explicit self (`SdkBackend._log(self, m)`, a class-body alias
        or default of the writer's own function object). Blind-pin lens of review round 6: the unbound call was read
        with `self` as its message, so the row's taint went unread and only the unreduced set caught it."""
        seen = seen if seen is not None else set()
        door = self.door
        if isinstance(e, ast.Attribute):
            if e.attr == door:
                unbound = isinstance(e.value, ast.Name) and e.value.id in self.classes_by_name and e.value.id not in ("self", "cls")
                return "unbound" if unbound else "bound"
            if e.attr in self.class_alias_doors:
                unbound = isinstance(e.value, ast.Name) and e.value.id in self.classes_by_name and e.value.id not in ("self", "cls")
                return "unbound" if unbound else "bound"      # the alias is the writer's function; instance access binds it
            return None
        if isinstance(e, ast.Call):
            f = e.func
            if isinstance(f, ast.Name) and f.id == "getattr" and len(e.args) >= 2 and isinstance(e.args[1], ast.Constant) and e.args[1].value == door:
                unbound = isinstance(e.args[0], ast.Name) and e.args[0].id in self.classes_by_name
                return "unbound" if unbound else "bound"
            if self._is_partial(e) and e.args:
                b = self.door_binding(e.args[0], fn, seen)
                return "bound" if b == "unbound" and len(e.args) > 1 else b    # partial(SdkBackend._log, be) supplies self
            return None
        if isinstance(e, ast.IfExp):
            return self._combine_binding([self.door_binding(e.body, fn, seen), self.door_binding(e.orelse, fn, seen)])
        if isinstance(e, ast.BoolOp):
            return self._combine_binding(self.door_binding(v, fn, seen) for v in e.values)
        if isinstance(e, ast.Name):
            owner = self.is_param(e.id, fn)
            if owner is not None:
                k = ("binding", owner.qual, e.id)
                if k in seen:
                    return None
                seen.add(k)
                return self._combine_binding(self.door_binding(v, caller, seen) for v, caller in self.param_bindings(owner, e.id))
            for s in self.scope_chain(fn):
                sts = list(self._assigns_name(s, e.id))
                if sts:
                    vals = [self._value_for(st, e.id) for st in sts]
                    return self._combine_binding(self.door_binding(v, s, seen) for v in vals if v is not None and not isinstance(v, tuple))
            return self._scope_name_value(e, fn, seen, self.door_binding, "unbound", None)
        return None

    @staticmethod
    def _combine_binding(results):
        found = {r for r in results if r}
        if not found:
            return None
        return found.pop() if len(found) == 1 else "mixed"

    @staticmethod
    def _combine(results):
        results = list(results)
        if "unfollowed" in results:
            return "unfollowed"
        return "door" if "door" in results else "not"

    def _value_for(self, st, name):
        """The value assigned to `name` by statement `st` (an element of a tuple value when the target is a tuple)."""
        if isinstance(st, ast.Assign):
            for t in st.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return st.value
                if isinstance(t, (ast.Tuple, ast.List)):
                    for i, el in enumerate(t.elts):
                        if isinstance(el, ast.Name) and el.id == name:
                            if isinstance(st.value, (ast.Tuple, ast.List)) and i < len(st.value.elts):
                                return st.value.elts[i]
                            return ("index", st.value, i)
            return None
        if isinstance(st, (ast.AnnAssign, ast.NamedExpr)):
            return st.value
        return None

    def param_bindings(self, fn, pname):
        """[(expr, caller Fn)] bound to parameter `pname` over every call site of `fn` (a default counts once)."""
        out = []
        for call, caller, via in self.callers.get(fn, []):
            b = self.bind_args(call, fn, via)
            if pname in b:
                out.append((b[pname], caller if b[pname] is not fn.defaults.get(pname) else fn))
        if pname in fn.defaults and not any(v is fn.defaults[pname] for v, _c in out):
            out.append((fn.defaults[pname], fn))
        return out

    def _door_calls(self):
        door, msg = self.door, self.msg_param
        self.calls_reaching = []       # DoorCalls that resolve to the writer itself (direct, typed, bound, param, alias)
        self.by_kind = collections.Counter()
        for fn in self.all_fns:
            for call in fn.calls:
                f = call.func
                kind = None
                if isinstance(f, ast.Attribute) and f.attr == door:
                    dv = self.door_value(f, fn)
                    if dv == "unfollowed":
                        self.failures.append(("door-unresolved", fn.base, call.lineno,
                                              "self.%s in %s binds to nothing the walk can see" % (door, fn.qual)))
                        continue
                    if isinstance(f.value, ast.Name) and f.value.id == "self":
                        cls = self.class_of(fn)
                        kind = "self" if cls is not None and self.writer_cls in self.mro(cls) else "bound-self"
                    else:
                        kind = "typed"
                elif isinstance(f, ast.Attribute) and f.attr in self.class_alias_doors:
                    if self.door_value(f, fn) == "door":
                        kind = "alias"          # a class-body alias of the door (`self._ring(...)`)
                elif isinstance(f, ast.Name):
                    if self.is_param(f.id, fn) is not None:
                        if self.door_value(f, fn) == "door":
                            kind = "param"
                    elif any(any(self._assigns_name(s, f.id)) for s in self.scope_chain(fn)):
                        if self.door_value(f, fn) == "door":
                            kind = "alias"
                    elif (self.mod_of(fn).path, f.id) in self.module_alias_doors:
                        if self.door_value(f, fn) == "door":
                            kind = "alias"      # a module-level alias of the door (`_RING(...)`)
                if kind is None:
                    continue
                kws = {k.arg: k.value for k in call.keywords if k.arg}
                binding = self.door_binding(f, fn) if kind in ("typed", "param", "alias") else "bound"
                if binding == "mixed":
                    self.failures.append(("door-binding", fn.base, call.lineno, "the door reaches %s both bound and unbound, so the "
                                          "message's position differs by site: %s" % (fn.qual, ast.unparse(call)[:60])))
                    binding = "bound"
                if binding == "unbound":
                    message = call.args[1] if len(call.args) > 1 else kws.get(msg)     # after the explicit self
                else:
                    message = call.args[0] if call.args else kws.get(msg)
                dc = DoorCall(fn, call, kind, message, kws.get("ring_text"), kws.get("problem"), kws.get("key"))
                dc.lexical = bool(fn.lexical.get(id(call)))
                self.calls_reaching.append(dc)
                self.by_kind[kind] += 1
        # the feeders' own adds are door calls of the kernel's siblings of the ring: the row they add (an append's or
        # extend's first argument, an insert's second, an augmented assignment's value) read for its "text" key
        self.feeder_calls = []
        for fn, call, listname in self.feeder_appends:
            if isinstance(call, ast.AugAssign):
                arg = call.value
            else:
                arg = call.args[1] if call.func.attr == "insert" and len(call.args) > 1 else call.args[0]
            text = arg
            if isinstance(arg, ast.Dict):
                text = None
                for k, v in zip(arg.keys, arg.values):
                    if isinstance(k, ast.Constant) and k.value == "text":
                        text = v
            dc = DoorCall(fn, call, "feeder-append:%s" % listname, text, None, ("const", True), None)
            self.feeder_calls.append(dc)
        # conduits: a door call whose message is one of the enclosing function's parameters
        self.conduits = {}       # Fn -> [(inner DoorCall, message param name)]
        frontier = list(self.calls_reaching) + list(self.feeder_calls)
        self.conduit_calls = []
        for _depth in range(4):
            new, by_site = [], {}
            for inner in frontier:
                pname = self._param_of(inner.message, inner.fn)
                if pname is None or inner.fn.kind == "lambda":
                    continue
                self.conduits.setdefault(inner.fn, []).append((inner, pname))
                for call, caller, via in self.callers.get(inner.fn, []):
                    b = self.bind_args(call, inner.fn, via)
                    if pname not in b:
                        continue
                    problem = self._through(inner.problem, inner.fn, b)
                    ring_text = self._through(inner.ring_text, inner.fn, b)
                    key = self._through(inner.key, inner.fn, b)
                    site = (id(call), inner.fn.qual)
                    if site in by_site:
                        by_site[site].alts.append((problem, ring_text, inner))
                        continue
                    dc = DoorCall(caller, call, "conduit:%s" % inner.fn.qual, b[pname], ring_text, problem, key, via=inner)
                    dc.lexical = bool(caller.lexical.get(id(call)))
                    by_site[site] = dc
                    new.append(dc)
            self.conduit_calls.extend(new)
            frontier = new
            if not new:
                break
        # a feeder whose text is its own (not a parameter's) is not a conduit, and its call sites are doors all the same
        self.feeder_site_calls = []
        for inner in self.feeder_calls:
            if inner.fn in self.conduits:
                continue
            for call, caller, via in self.callers.get(inner.fn, []):
                dc = DoorCall(caller, call, "feeder:%s" % inner.fn.qual, inner.message, None, ("const", True), None, via=inner)
                dc.lexical = bool(caller.lexical.get(id(call)))
                self.feeder_site_calls.append(dc)
        self.door_calls = list(self.calls_reaching) + list(self.feeder_calls) + list(self.conduit_calls) + list(self.feeder_site_calls)

    def _param_of(self, expr, fn):
        """The parameter name an expression reduces to when it is (a wrap of) one parameter of fn, else None."""
        seen = 0
        while seen < 8 and expr is not None:
            seen += 1
            if isinstance(expr, ast.Name):
                owner = self.is_param(expr.id, fn)
                if owner is fn:
                    return expr.id
                if owner is None:
                    sts = list(self._assigns_name(fn, expr.id))
                    if len(sts) == 1:
                        expr = self._value_for(sts[0], expr.id)
                        if isinstance(expr, tuple):
                            return None
                        continue
                return None
            if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id in ("str", "bool") and expr.args:
                expr = expr.args[0]
                continue
            if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
                expr = expr.left
                continue
            return None
        return None

    def _through(self, expr, inner_fn, bindings):
        """An inner call's keyword seen from a conduit call site: a constant stays; a parameter (or bool(param)) becomes
        the site's own argument or the default; anything else stays the inner expression."""
        if expr is None:
            return None
        if isinstance(expr, ast.Constant):
            return expr
        pname = self._param_of(expr, inner_fn)
        if pname is not None and pname in bindings:
            v = bindings[pname]
            if isinstance(expr, ast.Call) and isinstance(v, ast.Constant):
                return ("const", bool(v.value))
            return v
        return expr

    def _is_door_expr(self, node, fn):
        """A door EXPRESSION: `<x>.<door>` read as a value, `getattr(x, "<door>", ...)`, a class-body alias of the door
        read on a receiver, or the writer's bare name where a Name resolves in its class body (a class-level alias or a
        method's default argument)."""
        door = self.door
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            return node.attr == door or (node.attr in self.class_alias_doors and self.door_value(node, fn) == "door")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr":
            return len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and node.args[1].value == door
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == door:
            sc = self.scope_of(node)
            if isinstance(sc, ast.ClassDef):
                c = self.cls_by_node.get(id(sc))
                return c is not None and c.methods.get(door) is self.writer
        return False

    def _scope_walk(self, mod):
        """Every node evaluated at MODULE or CLASS scope, with the class whose body holds it (None at module level):
        module-level statements, class bodies, and the decorators, default arguments and annotations of the defs at
        either level (evaluated in the enclosing scope, not the def's). Function bodies and lambdas are the per-function
        walk's; nested classes' bodies are reached through their statements."""
        out = []

        def visit(n, cls):
            stack = [n]
            while stack:
                x = stack.pop()
                if isinstance(x, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                out.append((x, cls))
                stack.extend(ast.iter_child_nodes(x))

        def stmts(body, cls):
            for st in body:
                if isinstance(st, ast.ClassDef):
                    for d in st.decorator_list + st.bases + [kw.value for kw in st.keywords]:
                        visit(d, cls)
                    stmts(st.body, self.cls_by_node.get(id(st)))
                elif isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for d in st.decorator_list:
                        visit(d, cls)
                    visit(st.args, cls)
                    if st.returns is not None:
                        visit(st.returns, cls)
                else:
                    visit(st, cls)

        stmts(mod.tree.body, None)
        return out

    def _follow_door_values(self):
        """Every door expression that is a value, not a callee, followed to a call. Records the sites. Three walks: the
        body of every function (defaults, decorators and annotations excluded: they belong to the enclosing scope), the
        module and class scopes of every file, and every string constant spelling the door's or the ring's name (a door
        reached by reflection, `operator.attrgetter("_log")`, `getattr(be, LOG_ATTR)` with the name in a constant,
        `vars(be)["_log"]`, is a door the walk cannot follow: blind-pin lens of review round 6)."""
        door = self.door
        self.door_value_sites = []     # (base, lineno, kind, fn)
        self.log_param_fns = set()     # Fns whose parameter is bound to a door somewhere
        for mod, node, _fn in self.ident_consts:
            up = self.parents.get(node)
            if node.value == door:
                followed = (isinstance(up, ast.Call) and isinstance(up.func, ast.Name) and up.func.id == "getattr"
                            and len(up.args) >= 2 and up.args[1] is node)
                if not followed:
                    self.failures.append(("door-name-string", mod.base, node.lineno, "the door's name %r is a string outside "
                                          "getattr(x, %r): %s" % (door, door, ast.unparse(up)[:60] if up is not None else "?")))
            elif node.value == self.RING_ATTR:
                self.failures.append(("ring-name-string", mod.base, node.lineno, "the ring's name %r is a string: %s"
                                      % (self.RING_ATTR, ast.unparse(up)[:60] if up is not None else "?")))
        for fn in self.all_fns:
            roots = fn.node.body if isinstance(fn.node, (ast.FunctionDef, ast.AsyncFunctionDef)) else [fn.node.body]
            for root in roots:
                for node in ast.walk(root):
                    if not self._is_door_expr(node, fn):
                        continue
                    if self.fn_for(node) is not fn and self.enclosing_fn(node) is not fn:
                        continue
                    parent = self.parents.get(node)
                    if isinstance(parent, ast.Call) and parent.func is node:
                        continue      # called on the spot: a door call, counted above
                    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
                        cls = self.class_of(fn)
                        if cls is not None and self.writer_cls not in self.mro(cls):
                            # ApiHealth's `if self._log:` guard: a truthiness read of the bound attribute
                            if self._truthiness_use(node):
                                continue
                    self._follow_value(node, fn)
        for mod in {m.path: m for m in self.mods.values()}.values():
            for node, cls in self._scope_walk(mod):
                sfn = ScopeFn(mod, cls)
                if not self._is_door_expr(node, sfn):
                    continue
                parent = self.parents.get(node)
                if isinstance(parent, ast.Call) and parent.func is node:
                    self.failures.append(("door-escapes", mod.base, node.lineno, "the door is called at %s scope: %s"
                                          % (sfn.qual, ast.unparse(parent)[:60])))
                    continue
                self._follow_value(node, sfn)

    def _truthiness_use(self, node):
        up, n = self.parents.get(node), node
        while isinstance(up, (ast.BoolOp, ast.UnaryOp)):
            n, up = up, self.parents.get(up)
        return isinstance(up, (ast.If, ast.While, ast.IfExp, ast.Assert)) and getattr(up, "test", None) is n

    def _follow_value(self, node, fn, depth=0):
        base, ln = fn.base, node.lineno
        up, n = self.parents.get(node), node
        while isinstance(up, (ast.IfExp, ast.BoolOp)) or (isinstance(up, ast.Call) and self._is_partial(up)):
            n, up = up, self.parents.get(up)
        if isinstance(up, ast.keyword):
            n, up = up, self.parents.get(up)
        if isinstance(up, ast.arguments):
            # a default argument (`def m(self, sess, log=_log)`, `def f(be, log=SdkBackend._log)`): the parameter is
            # door-bound at the def itself, so it must be called or forwarded like one bound at a call site
            dfn = self.fn_by_node.get(id(self.parents.get(up)))
            pname = None
            if dfn is not None:
                for i, d in enumerate(up.defaults):
                    if d is n:
                        pname = dfn.params[len(dfn.params) - len(up.defaults) + i]
                for a, d in zip(up.kwonlyargs, up.kw_defaults):
                    if d is n:
                        pname = a.arg
            if dfn is None or pname is None:
                self.failures.append(("door-escapes", base, ln, "a door value is a default the walk cannot place: %s" % ast.unparse(up)[:80]))
                return
            self.door_value_sites.append((base, ln, "parameter %s of %s (default)" % (pname, dfn.qual), fn))
            if not self._param_consumed(dfn, pname, depth):
                self.failures.append(("door-escapes", base, ln, "parameter %s of %s (default) is never called or forwarded" % (pname, dfn.qual)))
            return
        if isinstance(up, (ast.Assign, ast.AnnAssign)) and fn.kind == "scope":
            targets = self._targets(up)
            if len(targets) == 1 and isinstance(targets[0], ast.Name):
                name = targets[0].id
                mod = self.mod_of(fn)
                if fn.cls is None:
                    # a module-level alias: called by its bare name in some function of the module where nothing
                    # nearer shadows it
                    called = any(isinstance(c.func, ast.Name) and c.func.id == name and self.is_param(name, f) is None
                                 and not any(self._assigns_name(s, name) for s in self.scope_chain(f))
                                 for f in mod.fns for c in f.calls)
                    how = "module alias %s" % name
                else:
                    # a class-body alias: called as an attribute (`self.<alias>(...)`, `<any>.<alias>(...)`) anywhere
                    called = any(isinstance(c.func, ast.Attribute) and c.func.attr == name for f in self.all_fns for c in f.calls)
                    how = "class alias %s of %s" % (name, fn.cls.name)
                if called:
                    self.door_value_sites.append((base, ln, how, fn))
                    return
                self.failures.append(("door-escapes", base, ln, "%s is never called" % how))
                return
            self.failures.append(("door-escapes", base, ln, "a door value is bound at %s scope where the walk cannot follow: %s" % (fn.qual, ast.unparse(up)[:80])))
            return
        if isinstance(up, ast.Call) and n is not up.func:
            callees = self.callees.get(id(up), [])
            if not callees:
                self.failures.append(("door-escapes", base, ln, "a door value is passed to a call the walk cannot resolve: %s" % ast.unparse(up)[:80]))
                return
            for callee, via in callees:
                b = self.bind_args(up, callee, via)
                pnames = [p for p, v in b.items() if v is n or (isinstance(n, ast.keyword) and v is n.value)]
                if not pnames:
                    self.failures.append(("door-escapes", base, ln, "a door value reaches %s outside any parameter" % callee.qual))
                    continue
                for p in pnames:
                    self.door_value_sites.append((base, ln, "parameter %s of %s" % (p, callee.qual), fn))
                    if not self._param_consumed(callee, p, depth):
                        self.failures.append(("door-escapes", base, ln, "parameter %s of %s is never called or forwarded" % (p, callee.qual)))
            return
        if isinstance(up, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = self._targets(up)
            if len(targets) == 1 and isinstance(targets[0], ast.Name):
                name = targets[0].id
                if any(isinstance(c.func, ast.Name) and c.func.id == name for c in fn.calls) or self._forwarded(fn, name, depth):
                    self.door_value_sites.append((base, ln, "alias %s in %s" % (name, fn.qual), fn))
                    return
                self.failures.append(("door-escapes", base, ln, "alias %s in %s is never called" % (name, fn.qual)))
                return
            if len(targets) == 1 and isinstance(targets[0], ast.Attribute) and isinstance(targets[0].value, ast.Name) \
                    and targets[0].value.id == "self" and fn.cls is not None:
                attr = targets[0].attr
                if any(isinstance(c.func, ast.Attribute) and c.func.attr == attr and isinstance(c.func.value, ast.Name)
                       and c.func.value.id == "self" for m in self.mro(fn.cls) for mf in m.methods.values() for c in mf.calls):
                    self.door_value_sites.append((base, ln, "bound to self.%s in %s" % (attr, fn.qual), fn))
                    return
                self.failures.append(("door-escapes", base, ln, "self.%s bound in %s is never called" % (attr, fn.qual)))
                return
            self.failures.append(("door-escapes", base, ln, "a door value is assigned where the walk cannot follow: %s" % ast.unparse(up)[:80]))
            return
        if isinstance(up, ast.Return):
            self.failures.append(("door-escapes", base, ln, "a door value escapes %s through its return" % fn.qual))
            return
        if self._truthiness_use(node):
            return
        self.failures.append(("door-escapes", base, ln, "a door value stands where the walk cannot follow: %s" % ast.unparse(up)[:80]))

    @staticmethod
    def _is_partial(call):
        f = call.func
        return (isinstance(f, ast.Name) and f.id == "partial") or (isinstance(f, ast.Attribute) and f.attr == "partial")

    def _param_consumed(self, fn, pname, depth):
        self.log_param_fns.add(fn)
        if depth > 6:
            return False
        called = any(isinstance(c.func, ast.Name) and c.func.id == pname for c in fn.calls)
        for nested in [x for lst in fn.nested.values() for x in lst]:
            called = called or any(isinstance(c.func, ast.Name) and c.func.id == pname for c in nested.calls)
        forwarded = self._forwarded(fn, pname, depth)     # explored even when called here: it records the pass-through
        if called or forwarded:
            return True
        # bound to self.<attr> in __init__ and called by a method
        if fn.cls is not None:
            for st in fn.assigns:
                if isinstance(st, ast.Assign) and isinstance(st.value, ast.Name) and st.value.id == pname:
                    for t in st.targets:
                        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                            attr = t.attr
                            if any(isinstance(c.func, ast.Attribute) and c.func.attr == attr and isinstance(c.func.value, ast.Name)
                                   and c.func.value.id == "self" for m in self.mro(fn.cls) for mf in m.methods.values() for c in mf.calls):
                                return True
        return False

    def _forwarded(self, fn, name, depth):
        """`name` (a parameter or alias of fn) passed as an argument to a resolvable call whose parameter is consumed."""
        for call in fn.calls:
            for callee, via in self.callees.get(id(call), []):
                b = self.bind_args(call, callee, via)
                for p, v in b.items():
                    if isinstance(v, ast.Name) and v.id == name and callee is not fn:
                        if self._param_consumed(callee, p, depth + 1):
                            return True
        return False

    # ------------------------------------------------------------------ taint
    def _source_tag(self, node, fn):
        """The tag a source READ carries at this node, or None."""
        s = self.sources
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load) and node.attr in s["attr"]:
            return s["attr"][node.attr]
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load) and isinstance(node.slice, ast.Constant) \
                and node.slice.value in s["key"]:
            return s["key"][node.slice.value]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args \
                and isinstance(node.args[0], ast.Constant) and node.args[0].value in s["key"]:
            return s["key"][node.args[0].value]
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            tag = s["name"].get((fn.base, node.id))
            if tag and (fn.base, node.id) not in s["opaque_names"] and self.is_param(node.id, fn) is None:
                return tag
        if isinstance(node, ast.Call):
            for callee, _via in self.callees.get(id(node), []):
                tag = s["func"].get((callee.base, callee.qual))
                if tag and not self._returns_dicts(callee):
                    # a source function that returns a DICT (the launch shape) is a source at its env key, a read of
                    # its own ('env' in the key sources), not whole: its other keys carry what its return carries
                    return tag
        return None

    def _returns_dicts(self, callee):
        """Every return of `callee` is dict-valued (a literal, a comprehension, dict(...), a local built as one)."""
        hit = self._dict_returners.get(callee)
        if hit is None:
            hit = self._dict_returners[callee] = bool(callee.returns) and all(self._dict_valued(r, callee) for r in callee.returns)
        return hit

    def expr_taint(self, expr, fn):
        """The union of tags carried by any node in the expression's subtree; a resolved call contributes its callee's
        return taint and is not walked into (its parameters are tainted by propagation instead). A Name that is no
        parameter and no local of any enclosing scope reads the module-level name's taint; an attribute read
        (`<x>.<attr>`) carries whatever any store into `.<attr>` put there (keyed by attribute NAME over every receiver,
        the direction that finds a value stored in one method and read in another)."""
        tags = set()
        stack = [expr]
        mod = self.mod_of(fn)
        while stack:
            node = stack.pop()
            if node is None:
                continue
            if isinstance(node, tuple):   # ("index", value, i): a tuple-unpacked position
                _k, value, i = node
                res = self.callees.get(id(value), []) if isinstance(value, ast.Call) else []
                if res:
                    for callee, _via in res:
                        rt = self.ret_taint.get(callee)
                        if rt:
                            tags |= rt.get(i, set()) | rt.get("all", set())
                    tag = self._source_tag(value, fn)
                    if tag:
                        tags.add(tag)
                else:
                    stack.append(value)
                continue
            tag = self._source_tag(node, fn)
            if tag:
                tags.add(tag)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                found = False
                for s in self.scope_chain(fn):
                    tn = self.tainted_names.get(s)
                    if tn and node.id in tn:
                        tags |= tn[node.id]
                        found = True
                        break
                    if node.id in s.all_params() or node.id in s.assigned():
                        found = True
                        break
                if not found:
                    gt = self.global_taint.get((mod.path, node.id))
                    if gt:
                        tags |= gt
                continue
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                at = self.attr_taint.get(node.attr)
                if at:
                    tags |= at
            if isinstance(node, ast.Call):
                res = self.callees.get(id(node), [])
                if res:
                    for callee, _via in res:
                        if (callee.base, callee.qual) in self.sources["opaque_returns"]:
                            continue
                        rt = self.ret_taint.get(callee)
                        if rt:
                            for v in rt.values():
                                tags |= v
                    continue
                stack.extend(node.args)
                stack.extend(k.value for k in node.keywords)
                stack.append(node.func)
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            stack.extend(ast.iter_child_nodes(node))
        return tags

    def _taint(self):
        self.tainted_names = {}      # Fn -> {name: set(tags)} (parameters and locals alike; the WHOLE value's taint)
        self.carried_names = {}      # Fn -> {name: set(tags)} a local's taint minus what sits under a SOURCE key of a dict
        self.ret_taint = {}          # Fn -> {"all"|index: set(tags)}
        self.attr_taint = {}         # attribute name -> set(tags) stored into `<x>.<attr>` anywhere
        self._dict_returners = {}    # Fn -> whether every return is dict-valued (a source at its env key, not whole)
        self.global_taint = {}       # (module path, name) -> set(tags) stored into a module-level name from a function
        self._grown_attrs, self._grown_globals = set(), set()
        work = collections.deque(self.all_fns)
        queued = set(id(f) for f in self.all_fns)
        rounds = 0

        def enqueue(f):
            if id(f) not in queued:
                queued.add(id(f))
                work.append(f)

        while work:
            fn = work.popleft()
            queued.discard(id(fn))
            rounds += 1
            changed = self._taint_fn(fn)
            if changed:
                for call, caller, _via in self.callers.get(fn, []):
                    enqueue(caller)
                for nested in [x for lst in fn.nested.values() for x in lst]:
                    enqueue(nested)
            for callee in self._newly_tainted_callees:
                enqueue(callee)
            if self._grown_attrs:
                for attr in self._grown_attrs:
                    for reader in self.attr_readers.get(attr, ()):
                        enqueue(reader)
                self._grown_attrs = set()
            if self._grown_globals:
                for path, _name in self._grown_globals:
                    for reader in self.mods[path].fns:
                        enqueue(reader)
                self._grown_globals = set()
        self.taint_rounds = rounds

    # methods that add to a container in place: a tainted argument taints the receiver (blind-pin lens of review
    # round 6: `parts.append(k)` in a loop over the env names and a module list's `.extend(...)` carried the names to
    # a door with the receiver read as clean)
    MUTATING_METHODS = frozenset({"append", "extend", "insert", "add", "update", "setdefault", "appendleft", "extendleft",
                                  "__setitem__", "push", "put", "put_nowait"})
    ENV_ONLY = frozenset({"env"})

    def _taint_fn(self, fn):
        names = self.tainted_names.setdefault(fn, {})
        carried = self.carried_names.setdefault(fn, {})
        self._newly_tainted_callees = []
        before = {k: set(v) for k, v in names.items()}
        before_ret = {k: set(v) for k, v in self.ret_taint.get(fn, {}).items()}
        mod = self.mod_of(fn)
        for _ in range(6):
            grew = False
            for st in fn.assigns:
                value = st.value
                if value is None:
                    continue
                vt = self.expr_taint(value, fn)
                ct = self._container_taint(value, fn)
                if isinstance(st, ast.AugAssign):
                    grew |= self._store(fn, mod, names, carried, st.target, vt, ct)
                    continue
                targets = st.targets if isinstance(st, ast.Assign) else [st.target]
                for t in targets:
                    if isinstance(t, (ast.Tuple, ast.List)):
                        for i, el in enumerate(t.elts):
                            if isinstance(value, (ast.Tuple, ast.List)) and i < len(value.elts):
                                et = self.expr_taint(value.elts[i], fn)
                            elif isinstance(value, ast.Call) and self.callees.get(id(value)):
                                et = self.expr_taint(("index", value, i), fn)
                            else:
                                et = vt
                            grew |= self._store(fn, mod, names, carried, el, et, et)
                    else:
                        grew |= self._store(fn, mod, names, carried, t, vt, ct)
            for node in fn.loops():
                if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                    it = self.expr_taint(node.iter, fn)
                    if it:
                        for el in (node.target.elts if isinstance(node.target, (ast.Tuple, ast.List)) else [node.target]):
                            grew |= self._store(fn, mod, names, carried, el, it, it)
                elif isinstance(node, (ast.With, ast.AsyncWith)):
                    for item in node.items:
                        if item.optional_vars is not None:
                            it = self.expr_taint(item.context_expr, fn)
                            if it:
                                grew |= self._store(fn, mod, names, carried, item.optional_vars, it, it)
            # in-place adds: `parts.append(k)`, `seen.extend(names)`, `d.setdefault(k, v)`, `self.x.append(v)`
            for call in fn.calls:
                f = call.func
                if not (isinstance(f, ast.Attribute) and f.attr in self.MUTATING_METHODS):
                    continue
                args = [a for a in call.args] + [k.value for k in call.keywords]
                vt = set()
                for a in args:
                    vt |= self.expr_taint(a, fn)
                if not vt:
                    continue
                if f.attr in ("setdefault", "__setitem__") and call.args and isinstance(call.args[0], ast.Constant) \
                        and call.args[0].value in self.sources["key"]:
                    ct = set()                       # stored under a source key: a source at the read
                elif f.attr == "update":
                    ct = set()
                    for a in call.args:
                        ct |= self._container_taint(a, fn)
                    for k in call.keywords:
                        if k.arg not in self.sources["key"]:
                            ct |= self.expr_taint(k.value, fn)
                else:
                    ct = vt
                grew |= self._store(fn, mod, names, carried, f.value, vt, ct)
            if not grew:
                break
        # returns. A dict-valued return carries "env" alone, and only what sits under a key that is NOT a source
        # (the per-session env's own key, 'env' in DEFAULT_SOURCES, is a source at the READ, so a dict does not carry
        # it; a value re-keyed under any other name crosses with the dict: blind-pin lens of review round 6, a helper
        # returning {"names": sorted(sess.env_vars)} read as clean). The existence of a pick (tag "pick") does not cross
        # a dict return: a session snapshot carries the pending picks to every reader of every other field, and
        # propagated whole it tainted 946 functions' returns at this head; the existence rows are the direct readers
        # of the surface set.
        rt = self.ret_taint.setdefault(fn, {})
        for r in fn.returns:
            if r is None:
                continue
            if isinstance(r, (ast.Tuple, ast.List)):
                for i, el in enumerate(r.elts):
                    t = self._return_taint(el, fn)
                    if t:
                        rt.setdefault(i, set()).update(t)
            else:
                t = self._return_taint(r, fn)
                if t:
                    rt.setdefault("all", set()).update(t)
        # calls: taint the callees' parameters
        for call in fn.calls:
            for callee, via in self.callees.get(id(call), []):
                b = self.bind_args(call, callee, via)
                cn = self.tainted_names.setdefault(callee, {})
                for p, v in b.items():
                    if v is callee.defaults.get(p):
                        continue
                    t = self.expr_taint(v, fn)
                    if t and not t <= cn.get(p, set()):
                        cn.setdefault(p, set()).update(t)
                        self._newly_tainted_callees.append(callee)
        return names != before or self.ret_taint.get(fn, {}) != before_ret

    def _return_taint(self, expr, fn):
        if self._dict_valued(expr, fn):
            return self._container_taint(expr, fn) & self.ENV_ONLY
        return self.expr_taint(expr, fn)

    def _container_taint(self, value, fn):
        """What a value carries ACROSS a container boundary (a return, an attribute store): for a dict literal, the
        taint of every key and of every value not under a source key; for a dict comprehension, its key's and value's;
        for dict(...), its arguments less the source-key keywords; for a local dict built in place, its carried taint;
        for anything else, the whole expression's."""
        if isinstance(value, ast.Dict):
            tags = set()
            for k, v in zip(value.keys, value.values):
                if isinstance(k, ast.Constant) and k.value in self.sources["key"]:
                    continue
                if k is not None:
                    tags |= self.expr_taint(k, fn)
                tags |= self._container_taint(v, fn) if isinstance(v, (ast.Dict, ast.DictComp)) else self.expr_taint(v, fn)
            return tags
        if isinstance(value, ast.DictComp):
            return self.expr_taint(value.key, fn) | self.expr_taint(value.value, fn)
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "dict":
            tags = set()
            for a in value.args:
                tags |= self._container_taint(a, fn)
            for k in value.keywords:
                if k.arg not in self.sources["key"]:
                    tags |= self.expr_taint(k.value, fn)
            return tags
        if isinstance(value, ast.IfExp):
            return self._container_taint(value.body, fn) | self._container_taint(value.orelse, fn)
        if isinstance(value, ast.Name) and self._dict_valued(value, fn):
            for s in self.scope_chain(fn):
                if value.id in s.all_params() or value.id in s.assigned():
                    return set(self.carried_names.get(s, {}).get(value.id, set()))
            return set()
        return self.expr_taint(value, fn)

    def _dict_valued(self, expr, fn, depth=0):
        """A dict literal, a dict comprehension, a dict(...) call, a conditional of such, or a local every assignment
        of which is one (a dict built up in place and returned)."""
        if depth > 4 or expr is None:
            return False
        if isinstance(expr, (ast.Dict, ast.DictComp)):
            return True
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "dict":
            return True
        if isinstance(expr, ast.IfExp):
            return self._dict_valued(expr.body, fn, depth + 1) and self._dict_valued(expr.orelse, fn, depth + 1)
        if isinstance(expr, ast.Name):
            sts = fn.assigned().get(expr.id, [])
            if not sts or self.is_param(expr.id, fn) is not None:
                return False
            for st in sts:
                v = self._value_for(st, expr.id)
                if isinstance(v, tuple) or not self._dict_valued(v, fn, depth + 1):
                    return False
            return True
        return False

    def _store(self, fn, mod, names, carried, target, tags, ctags):
        """`tags` flow into `target` (a Name, a `<x>.<attr>`, a subscript, a starred name): a local of fn takes them
        (its carried set takes `ctags`, what crosses a dict boundary); a module-level name (declared global, or a module
        list mutated in place) takes them for every reader in the module; an attribute takes `ctags` for every reader
        of `.<attr>` in the three files. A subscript store under a constant SOURCE key ('env') marks the container
        whole (a whole-value use reads it) but not its carried set (the read of that key is a source of its own)."""
        if not tags:
            return False
        root, src_key = target, False
        if isinstance(root, ast.Starred):
            root = root.value
        while isinstance(root, ast.Subscript):
            if isinstance(root.slice, ast.Constant) and root.slice.value in self.sources["key"]:
                src_key = True
            root = root.value
        if isinstance(root, ast.Attribute):
            return self._mark_attr(root.attr, set() if src_key else ctags)
        if not isinstance(root, ast.Name):
            return False
        name = root.id
        is_global = name in fn.globals_ or (name not in fn.assigned() and self.is_param(name, fn) is None
                                             and not any(name in s.assigned() or name in s.all_params() for s in self.scope_chain(fn))
                                             and (name in mod.top_assigns or name in mod.top_lists))
        if is_global:
            return self._mark_global(mod, name, set() if src_key else ctags)
        grew = self._mark(names, name, tags)
        if not src_key:
            self._mark(carried, name, ctags)
        return grew

    def _mark_attr(self, attr, tags):
        if not tags or attr == self.RING_ATTR:
            return False          # the ring is the sink; what its rows carry is the population itself, not a source
        cur = self.attr_taint.get(attr, set())
        if tags <= cur:
            return False
        self.attr_taint[attr] = cur | tags
        self._grown_attrs.add(attr)
        return True

    def _mark_global(self, mod, name, tags):
        if not tags:
            return False
        key = (mod.path, name)
        cur = self.global_taint.get(key, set())
        if tags <= cur:
            return False
        self.global_taint[key] = cur | tags
        self._grown_globals.add(key)
        return True

    @staticmethod
    def _mark(names, name, tags):
        if not tags:
            return False
        cur = names.get(name, set())
        if tags <= cur:
            return False
        names[name] = cur | tags
        return True

    # ------------------------------------------------------------------ reduction
    def reduce(self, expr, fn, depth=0, seen=frozenset()):
        """{("lit", text) | ("fstr", head) | ("fmt", NAME, text) | ("param", name, owner) | ("name", NAME) |
        ("other", text) | ("unresolved", name)}. `seen` is the path of assignments and calls above this point (a cycle
        guard handed down a branch, never shared across sibling branches, so two assignments through one local both
        resolve)."""
        if depth > 16:
            return {("other", "<deep>")}
        if expr is None:
            return {("other", "<none>")}
        if isinstance(expr, tuple):
            _k, value, i = expr
            out = set()
            if isinstance(value, ast.Call):
                for callee, _via in self.callees.get(id(value), []):
                    k = ("call", callee.qual)
                    if k in seen:
                        continue
                    for r in callee.returns:
                        if isinstance(r, (ast.Tuple, ast.List)) and i < len(r.elts):
                            out |= self.reduce(r.elts[i], callee, depth + 1, seen | {k})
            return out or {("other", ast.unparse(value)[:60])}
        if isinstance(expr, ast.Constant):
            return {("lit", expr.value)} if isinstance(expr.value, str) else {("other", repr(expr.value))}
        if isinstance(expr, ast.JoinedStr):
            head = expr.values[0].value if expr.values and isinstance(expr.values[0], ast.Constant) else ""
            return {("fstr", head)}
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, (ast.Mod, ast.Add)):
            return self.reduce(expr.left, fn, depth + 1, seen)
        if isinstance(expr, ast.IfExp):
            return self.reduce(expr.body, fn, depth + 1, seen) | self.reduce(expr.orelse, fn, depth + 1, seen)
        if isinstance(expr, ast.BoolOp):
            out = set()
            for v in expr.values:
                out |= self.reduce(v, fn, depth + 1, seen)
            return out
        if isinstance(expr, ast.Call):
            f = expr.func
            if isinstance(f, ast.Name) and f.id in ("str", "repr") and expr.args:
                return self.reduce(expr.args[0], fn, depth + 1, seen)
            if isinstance(f, ast.Attribute) and f.attr == "format":
                return self.reduce(f.value, fn, depth + 1, seen)
            if isinstance(f, ast.Attribute) and f.attr in ("strip", "rstrip", "lstrip", "upper", "lower", "replace", "removeprefix", "removesuffix"):
                return self.reduce(f.value, fn, depth + 1, seen)
            out = set()
            for callee, _via in self.callees.get(id(expr), []):
                k = ("call", callee.qual)
                if k in seen:
                    continue
                for r in callee.returns:
                    out |= self.reduce(r, callee, depth + 1, seen | {k})
            return out or {("other", ast.unparse(expr)[:60])}
        if isinstance(expr, ast.Name):
            owner = self.is_param(expr.id, fn)
            if owner is not None:
                return {("param", expr.id, owner.qual)}
            for s in self.scope_chain(fn):
                sts = self._assigns_name(s, expr.id)
                if sts:
                    out = set()
                    for st in sts:
                        k = ("assign", id(st), expr.id)
                        if k in seen:
                            continue
                        v = self._value_for(st, expr.id)
                        out |= self.reduce(v, s, depth + 1, seen | {k}) if v is not None else {("other", ast.unparse(st)[:60])}
                    return out or {("unresolved", expr.id)}
                if expr.id in s.all_params():
                    break
            mod = self.mod_of(fn)
            if expr.id in mod.top_assigns:
                v = mod.top_assigns[expr.id]
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    return {("fmt", expr.id, v.value)}
                return {("name", expr.id)}
            return {("unresolved", expr.id)}
        return {("other", ast.unparse(expr)[:60])}

    def _reduce_all(self):
        for dc in self.door_calls:
            ctx = dc.via.fn if dc.kind.startswith("feeder:") else dc.fn
            res = self.reduce(dc.message, ctx) if dc.message is not None else {("other", "<no message>")}
            heads, params = [], []
            for r in res:
                if r[0] in ("lit", "fstr"):
                    heads.append(r[1])
                elif r[0] == "fmt":
                    heads.append(r[2])
                elif r[0] == "param":
                    params.append(r)
            dc.heads = sorted(set(heads) - ({""} if len(set(heads)) > 1 else set()))
            if params and not dc.kind.startswith("conduit:"):
                # the inner call of a conduit: its heads are its call sites' heads
                for site in self.conduit_calls:
                    if site.via is dc:
                        dc.heads = sorted(set(dc.heads) | set(site.heads))
            dc.unreduced = not [h for h in dc.heads if h != ""] and not (params and dc.fn in self.conduits)
            if dc.ring_text is not None and not isinstance(dc.ring_text, tuple):
                rr = self.reduce(dc.ring_text, dc.fn)
                dc.ring_formats = sorted({r[1] for r in rr if r[0] == "fmt"})
                if any(r[0] not in ("fmt",) for r in rr):
                    dc.ring_formats = dc.ring_formats + ["UNBOUNDED:%s" % ",".join(sorted(str(r[1]) for r in rr if r[0] != "fmt"))]
        # a conduit's inner call reduces through its sites; re-run the unreduced flag for inner calls after the sites, to a
        # fixpoint, since a site can itself be a conduit (its message its own parameter) whose flag the pass recomputes:
        # read in one pass in source order, an inner call took its sites' first-pass flags (round-6 addendum: a conduit
        # whose two sites both forwarded run-time data read as reduced)
        for _ in range(8):
            changed = False
            for dc in self.door_calls:
                if dc.fn in self.conduits and any(inner is dc for inner, _p in self.conduits[dc.fn]):
                    sites = [s for s in self.conduit_calls if s.via is dc or any(i is dc for _p, _r, i in s.alts)]
                    heads = {h for s in sites for h in s.heads}
                    dc.heads = sorted(heads - ({""} if len(heads) > 1 else set()))
                    # a conduit's own call has the heads its sites give it: none at all (no site, or none that reduces) is unreduced
                    new = not sites or all(s.unreduced for s in sites)
                    if new != dc.unreduced:
                        dc.unreduced, changed = new, True
            if not changed:
                break

    # ------------------------------------------------------------------ classification
    def _classify(self):
        for dc in self.door_calls:
            tags = set()
            ctx = dc.via.fn if dc.kind.startswith("feeder:") else dc.fn
            if dc.message is not None and not isinstance(dc.message, tuple):
                tags |= self.expr_taint(dc.message, ctx)
            if dc.ring_text is not None and not isinstance(dc.ring_text, tuple):
                tags |= self.expr_taint(dc.ring_text, dc.fn if dc.ring_text is not (dc.via.ring_text if dc.via else None) else dc.via.fn)
            for _p, r, inner in dc.alts:
                if r is not None and not isinstance(r, tuple):
                    tags |= self.expr_taint(r, dc.fn if r is not inner.ring_text else inner.fn)
            dc.taint = frozenset(tags)
        self.tainted = [dc for dc in self.door_calls if dc.taint]
        # CONTENT rows: a value of the pick or its file (tag "env") filed as a problem. A row tainted by the surface set
        # alone (tag "pick") names a pick's existence, a word of a fixed vocabulary, never a value: an EXISTENCE row
        self.content_rows = [dc for dc in self.tainted if "env" in dc.taint and dc.problem_decl == ("const", True)]
        self.existence_rows = [dc for dc in self.tainted if "env" not in dc.taint]
        # rule (2): every value-tainted door call declares problem= as a constant on every inner call it can file
        # through; a content row's ring text reduces to ONE module-level format (the worst-case table bounds it); an
        # existence row owes no format bound (a surface name adds a fixed word), only the explicit constant
        self.explicit_violations = []
        for dc in self.tainted:
            decls = dc.decls()
            bad = [d for d in decls if d[0] != "const"]
            if bad:
                d = bad[0]
                self.explicit_violations.append((dc, "no explicit problem=" if d == ("none",) else "problem= is the expression %s" % d[1]))
                continue
            if any(d == ("const", True) for d in decls) and "env" in dc.taint:
                fmts = [f for f in dc.ring_formats if not f.startswith("UNBOUNDED")]
                if not (len(dc.ring_formats) == 1 and fmts):
                    self.explicit_violations.append((dc, "problem=True with a ring text that reduces to %s" % (dc.ring_formats or "no format")))
        self.unreduced = [dc for dc in self.door_calls if dc.unreduced]
        # floors
        self.counts = {
            "ring_appends": 1,
            "calls_reaching_writer": len(self.calls_reaching),
            "log_param_fns": len(self.log_param_fns),
            "door_value_sites": len([s for s in self.door_value_sites if s[2].startswith("parameter")]),
            "conduit_sites": collections.Counter(dc.kind for dc in self.conduit_calls + self.feeder_site_calls),
            "feeder_appends": len(self.feeder_appends),
            "feeder_sites": collections.Counter(dc.kind for dc in self.conduit_calls + self.feeder_site_calls if dc.via in self.feeder_calls),
            "existence_rows": len(self.existence_rows),
            "merge_reads": len(self.merge_reads),
            "content_rows": len(self.content_rows),
            "door_calls": len(self.door_calls),
            "tainted": len(self.tainted),
            "explicit_violations": len(self.explicit_violations),
            "unreduced": len(self.unreduced),
            "functions": len(self.all_fns),
            "failures": len(self.failures),
        }
        # the door total: the appender, every call reaching the writer, every conduit and feeder call site, every
        # site passing a door as an argument, every function whose parameter is bound to a door, the feeders' appends
        # and _sdk_problem_rows' merge reads; a call site is one entry however many inner calls it files through
        self.counts["doors"] = (self.counts["ring_appends"] + self.counts["calls_reaching_writer"]
                                + len(self.conduit_calls) + len(self.feeder_site_calls)
                                + self.counts["door_value_sites"] + self.counts["log_param_fns"] + self.counts["feeder_appends"]
                                + self.counts["merge_reads"])

    # ------------------------------------------------------------------ views
    def sites(self, calls):
        return sorted((dc.base, dc.lineno) for dc in calls)

    def content_identities(self):
        return [(dc.owner, dc.ring_formats[0] if len(dc.ring_formats) == 1 else "UNBOUNDED", dc.key is not None) for dc in
                sorted(self.content_rows, key=lambda d: (d.base, d.lineno))]

    def content_rows_line(self):
        groups = []
        for owner, fmt, keyed in self.content_identities():
            if not groups or groups[-1][0] != owner:
                groups.append((owner, []))
            groups[-1][1].append(fmt + ("(keyed)" if keyed else ""))
        return "# ENV ROWS: " + " | ".join("%s -> %s" % (owner, " ".join(tags)) for owner, tags in groups)

    def summary(self):
        out = dict(self.counts)
        out["by_kind"] = dict(self.by_kind)
        out["content_rows"] = [(dc.base, dc.lineno, dc.owner, dc.ring_formats, dc.key is not None, sorted(dc.taint)) for dc in
                               sorted(self.content_rows, key=lambda d: (d.base, d.lineno))]
        out["tainted_no_explicit"] = [(dc.base, dc.lineno, dc.owner, dc.kind, why, sorted(dc.taint), dc.heads[:1]) for dc, why in
                                      sorted(self.explicit_violations, key=lambda x: (x[0].base, x[0].lineno))]
        out["tainted_all"] = [(dc.base, dc.lineno, dc.owner, dc.kind, dc.problem_decl, sorted(dc.taint)) for dc in
                              sorted(self.tainted, key=lambda d: (d.base, d.lineno))]
        out["unreduced"] = [(dc.base, dc.lineno, dc.owner, dc.kind) for dc in sorted(self.unreduced, key=lambda d: (d.base, d.lineno))]
        out["existence_rows"] = [(dc.base, dc.lineno, dc.owner, dc.kind, dc.problem_decl, dc.heads[:1]) for dc in
                                 sorted(self.existence_rows, key=lambda d: (d.base, d.lineno))]
        out["failures"] = list(self.failures)
        out["log_param_fns"] = sorted(f.qual for f in self.log_param_fns)
        out["door_value_sites"] = sorted((b, ln, how) for b, ln, how, _fn in self.door_value_sites)
        out["conduits"] = {fn.qual: [(inner.lineno, p) for inner, p in lst] for fn, lst in self.conduits.items()}
        out["feeders"] = sorted((fn.qual, call.lineno, lst) for fn, call, lst in self.feeder_appends)
        out["merge_reads"] = list(self.merge_reads)
        out["writer"] = (self.writer.qual, self.writer.node.lineno, self.append_call.lineno)
        out["line"] = self.content_rows_line()
        out["taint_rounds"] = self.taint_rounds
        return out


_CENSUS = {}


def census(files=None, sources=None):
    """The census over `files` (the three kernel modules by default), computed once per process per file set."""
    files = tuple(os.path.realpath(f) for f in (files or DEFAULT_FILES))
    key = (files, id(sources) if sources is not None else 0)
    if key not in _CENSUS:
        _CENSUS[key] = Census(files, sources or DEFAULT_SOURCES)
    return _CENSUS[key]


def main(argv):
    import time
    files = argv[1:] or list(DEFAULT_FILES)
    t0 = time.time()
    for f in files:
        parsed(f)
    t1 = time.time()
    c = Census(files, DEFAULT_SOURCES)
    t2 = time.time()
    out = c.summary()
    out["seconds"] = {"parse": round(t1 - t0, 2), "census": round(t2 - t1, 2)}
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
