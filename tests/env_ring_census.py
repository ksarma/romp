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
     attribute in its __init__ from a parameter (ApiHealth), followed through every constructor call;
     `<class object>.<door>(self, ...)` through `cls` in a classmethod, `type(self)` or `self.__class__`, the plain
     function, its message read after the explicit self like the class name's (the rulings' lens: `cls._log(be or 'x',
     msg, ...)` was read with `be or 'x'` as its message, whose literal head hid the row from the unreduced pin);
     `getattr(x, "<door>")(...)` and `getattr(x, "<alias>")(...)`, a call through reflection with the name spelled,
     resolved as `x.<door>(...)`; a call through
     a PARAMETER (`log(...)`) followed through every call site of the enclosing function, positional or keyword,
     through `getattr(x, "<door>", None)`, `partial`, a conditional expression and a forwarded parameter, through a
     default argument (`log=_log` in the writer's class body, `log=SdkBackend._log` at module level) and
     through a closure that calls its enclosing function's parameter; a call through a local alias assigned from
     a door expression; and a call through an alias bound at CLASS scope (`_ring_door = _log` in the writer's class
     body, called as `self._ring_door(...)`) or at MODULE scope (`_RING = SdkBackend._log` or
     `getattr(SdkBackend, "_log")` at import, called by its bare name). A class alias whose name ANOTHER class also
     binds (the lens's `_ring = _log` in the writer's class beside ApiHealth's `self._ring` deque) is two bindings the
     AST tells apart by SCOPE (ruling 4 of review round 6): the receiver's classes are typed (`self` or `cls`, the
     enclosing class; a class name; `type(x)` and `x.__class__`; a parameter annotated with a class of the files, a
     string annotation, an Optional, a union and a keyword-only parameter included, unless the body reassigns it, when
     every assignment counts too; a local every assignment of which is a constructor call or another typed
     expression; a `self.<attr>` bound in __init__ from one of these), and EVERY class an instance of a typed receiver
     can be is decided by its own MRO, the class and each subclass of it (a mixin's self is an instance of whatever
     the mixin is mixed into): the first class of the MRO that owns the alias makes it the alias, a door; the first
     that binds the name itself (an attribute bound in __init__, a method, a class-body name) makes it that binding,
     no door. All door is a door; all not is not; both at once (a mixin mixed into the writer's class and into
     ApiHealth; a receiver typed by a base that binds the name while the writer's class, its subclass, owns the alias)
     is the loud door-alias-ambiguous failure naming both bindings and the remedy. A receiver the walk cannot type
     (no annotation; `object`, `Any` or a string of either, which every instance satisfies; a Protocol of the files;
     a class defining __getattr__ or __getattribute__, a proxy; an annotated parameter reassigned from an untyped
     value) resolves to the alias when no other class binds the name, and where one does it is the same failure.
     Whether the message comes first or after an explicit self is read from the binding (bound through an instance or
     getattr on one; unbound through a class object).
  3. CONDUITS. A function whose door call's message is one of its own parameters (SdkSession._log_quietly,
     problem_row) is a conduit: each of its call sites is a door call whose message is the argument it passes, whose
     problem= is the inner call's when that is a constant, or the site's own argument when the inner call forwards a
     parameter (problem_row's `bool(ring)`), and whose ring text follows the same rule. A conduit whose door is its
     own parameter (problem_row's log=) has a site only where that parameter is bound to something other than None:
     a site binding it to None, the default or None written, files nothing through the conduit. A conduit's inner
     calls are judged at their sites, each site carrying every inner road as an alternative, so a conduit that keeps
     a fallback road with no problem= (problem_row's plainer-callable `log(line)`) can carry no value-tainted row:
     a tainted site through it is a rule-(2) violation whatever it declares, and such a row takes the conduit's
     other outputs and files its own ring row (the post-merge census of the env-pick door, 2026-09-20, on main's two
     refused-launch rows). An inner call is judged at its sites ONLY where its taint is wholly its sites' (round 7
     of that review, 2026-09-20, kernel-1): a site carries the taint of the argument it passes and nothing the
     conduit's own body folds in, so the census recomputes each inner call's taint, over its message, its ring text
     and its key, with the conduit's parameters reading as clean and re-propagated through the conduit's own locals
     and the returns of the helpers they are assigned from (problem_row's `line` is built from its `prose` through a
     helper's returned row), and an inner call whose RESIDUAL is empty is skipped, while one that folds a source of
     its own into any of the three (a fold into the message as much as into the ring text) keeps its own row in the
     rule-(2) check and is judged on its own declaration, since no site carries that taint. A parameters-only mask
     (the arguments read as clean, the locals left with their propagated taint) reds the clean head through that
     `line`; the residual walk is what keeps the head green and the fold refused.
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
     FAILURE named by site, never a drop: a pin that cannot see must say so. So is the door's name, or a door
     alias's, spelled as a string anywhere but the getattr form the walk follows (`operator.attrgetter("_log")`,
     `LOG_ATTR = "_log"`, `vars(be)["_log"]`, `ATTR = "_ring"`: a door reached by reflection), and the ring's name
     spelled as a string at all.
  6. TAINT. A door call is VALUE-TAINTED when its message, its ring text or its key carries a value derived from a
     per-session env source (the key since round 7, 2026-09-20: SdkBackend._log stores it on the ring row, which
     problems() hands back whole, so a value in a key is a value on the ring; no key at the head carries one): the data road's sources (the env attributes of a session, the 'env' key of a registry row, launch
     shape or request body, the flag-settings constants and helpers, the reserved and credential name sets and the
     functions that judge them; tag "env") and the pending-pick surface set (_reconnect_surfaces and _pick_names,
     which can name the env pick's existence; tag "pick"). Taint flows through assignments (flow-insensitively,
     within a function), into a callee's parameters from every call site and out of a callee's return to every call
     site (context-insensitively: a helper whose parameter is tainted anywhere returns taint everywhere, the safe
     direction for a guard), through tuple returns by position, and into a nested function or lambda from the
     enclosing scope; through augmented assignment (`names += k`); through an add in place (`parts.append(k)`,
     `seen.extend(names)`, `d.setdefault(k, v)`, `d.update(...)`: the argument's taint marks the receiver, a local, a
     module-level name for every reader in its module, or an attribute; `operator.setitem(d, k, v)` is
     `d.__setitem__(k, v)`); through a store by reflection with the name spelled (`setattr(x, "n", v)`,
     `x.__dict__["n"] = v`, `x.__dict__.setdefault("n", v)` are stores into `.n`; under a name the census cannot place
     a tainted value is a reflection-store FAILURE); through an attribute store (`self.x = v` marks `.x` for every
     reader of `.x` on any receiver in the files, the direction that finds a value stored in one method and read in
     another; the ring attribute itself excepted, being the sink), read back by `.x`, `getattr(x, "x")`, `vars(x)["x"]`
     or `x.__dict__["x"]` alike (a source attribute read by any of these is a source read; a SOURCE'S NAME spelled as
     a string anywhere else is a source-name-string failure, the door's own rule); through a nested tuple target to
     its leaves (`(k, v), = d.items()`, `for i, (k, v) in ...`, `*_rest, (k, v) = ...`); into a lambda bound to a local
     and called by its name, and out of a generator's yields, which are its returns. Every value has two sets: the
     WHOLE value's, and what a read of ONE non-source key of it yields (its CARRIED set: a local's, a parameter's from
     its call sites, a return's, an attribute's), so a dict return or store carries "env" across its boundary only
     from what sits under a key that is NOT a source (the per-session env's own key, 'env', is a source at every
     READ, by subscript, `.get`, `.pop` or `.setdefault`, so a keyed read of another key, `shape["mode"]`,
     `shape.get("mode")`, `(shape or {}).get("mode")`, yields the carried set), while a whole-value use of the same
     dict (`str(shape)`, `shape.values()`, a loop over it, a splat, a pass to a helper that stringifies it, the dict
     held whole on an attribute and read back whole) yields the env with everything else; an identity test against
     None (`x is None`) yields nothing, a truth about x and no value of it. The census does NOT follow the pick tag
     across a dict return: a pick that crosses one is OUTSIDE the census, and the existence population is the direct
     readers of the surface set by construction. That is a bound on the census's reach, not a property of the kernel
     (ruling 3 of review round 6; followed whole, a session snapshot would carry the pending picks to every reader of
     every other field). A source FUNCTION whose every return is a dict (the launch shape) is a source at its env
     key, not whole, and the value it stores under that key (a literal's, `dict(env=v)`, `d["env"] = v`,
     `d.update(env=v)`, `d.setdefault("env", v)`, `operator.setitem(d, "env", v)`) is the env BY DECLARATION (ruling 2
     of review round 6): the taint follows the VALUE to its ROOTS, the Names, attribute chains and constant-keyed
     subscripts it derives from, a local followed to its own assignments, a walrus target, a constructor's arguments
     (a namedtuple or holder built from it), through comprehensions, `dict(e)`, `e or {}`, a tuple index and a second
     read of the origin, so a Name root is tainted in the function, an attribute root for every reader, and any other
     root wherever the same access is spelled again in the function; the dict holding the key is tainted whole; and
     where the census cannot locate the env inside such a return (no source key in the literal, a conditional with an
     unlocated branch, a dict(...) call without the key, a local nothing stored the key into) the whole return
     crosses with the tag, the over-approximating side, never a drop. Three bounds of the walk, stated as such: the
     roots are not followed backward through a call into a function of the files (its return is analysed forward
     from its parameters; a value copied under the source key by such a helper roots in nothing); an attribute takes
     a WHOLE set only from a store whose value is a dict by shape at the store (a literal, dict(...), a call to a
     function returning dicts, a local built as one), since attributes are keyed by NAME over every receiver and a
     scalar attribute given an over-approximated whole set handed the env to every reader of that name (95 content
     rows at the head), so a dict reaching an attribute only through a parameter is read there by its carried set;
     and a reflected read under a COMPUTED name (`getattr(x, name)`) is read as no attribute at all, which is why the
     spelled forms are the followed ones and a source's name in any other string fails. `_options`' return is opaque
     (the whole options dict; its env overlay is a source of its own), and reads of the kernel's _pending_ops carry no
     value taint (a mixed container of every parked op kind).
  7. REDUCTION. Every door call's message is reduced to its literal head(s): a string constant, an f-string's leading
     text, the left side of a `%` or `+`, a `str()` wrap, a local followed to every assignment (a tuple unpacking to
     its position), a module-level string constant by name, a helper followed into its returns (a return that is a
     wrap of the helper's own parameter read as the argument the call passed: problem_row's returned line opens with
     the caller's prose), and a conduit's
     parameter followed to every call site. A door call with NO literal head is recorded in `unreduced` by site and
     the pin holds that set to the sites it names; an unreduced call stays in the population and is judged by taint
     like every other, so nothing falls out of an assertion by failing to reduce.

From these the pin derives the CONTENT rows (value-tainted door calls filed with problem=True), holds them to the rows
the module's ENV ROWS line names by identity (writing function plus the module-level format the ring text starts
from), requires every value-tainted door call to declare problem= explicitly (False, or True with a ring text that
reduces to one module-level format the worst-case table bounds), asserts the negative half of kernel.py and
credentials.py only after asserting it FOUND their doors, and refuses to pass on a derivation that finds fewer
entries than the floors the test states (a walk that sees less than the last one did is blind, not clean). An
EXISTENCE row (tag "pick" alone, a fixed vocabulary plus names, never a value) filed problem=True owes the constant
and no format, and the reason is stated where it is declared (ruling 1 of review round 6: a declared residual with no
reason reads later as an oversight): four at this head. Three are _do_set_mode's failure reports about the mode
landing, each carrying no ring_text, so each row's text is its whole line, the session name, the two mode words and
an exception's class and text, unbounded by a module-level format, and each is a report about a mechanism outside
what the env-pick door bounds (the pick's values and file); the comment at each line says so. The fourth is
SdkSession._log_quietly's problem road (the post-merge census, 2026-09-20, ruling 2): its text is the union of every
caller's line, each formatted inline by its caller over the session name and the surface names, and the conduit
shapes nothing of it and forwards ring_text as given, so the bound of a row through it is its CALLER's
responsibility; the callers passing problem=True at this head (read off the module with each call's arguments bound
against the conduit's signature, positional or keyword: the live-work reconcile's unknown label and unreadable list,
and the five failure reports the merge of main brought, the reconnect's reg-flag clear and slot wait, the reconcile's
mirror write and the guard around each of the two reconciles; round 7, 2026-09-20, which re-derived the roster over
the merged population rather than citing the round-6 ruling, made over a population in which no caller was itself a
failure report) pass no ring_text, so each rings its whole line, again about a mechanism outside what the door
bounds. That responsibility is CURRENTLY UNMET: every caller formats self.name uncut (kernel.NAME_RE caps no length),
the unreadable-list line joins up to twelve CLI key names uncut into its text and its key, and the five failure
reports interpolate an exception's text uncut; tracked as ITEM: _log_quietly True callers unbounded (2026-09-20) in
~/romp-handoffs/romp-general-notes/small-asks.md, outside the repo. The comment at the road names them.

Pure AST: imports nothing of romp, executes nothing of it, and parses each canonical file once per process (ASTS below;
any other path is parsed for the construction that asked and not retained after it, the retention rule there). The
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

# The parse cache: realpath -> (source, tree), for the census's canonical inputs ALONE, parsed once per process. The
# retention rule (fork PR 781, the reviewer's ruling of 2026-09-20): a path in retained_paths() is kept for the
# process's life; any other path is parsed for the construction that asked and dropped after it (the Mod holds its
# own tree for the Census's life, and no phase parses a path twice within one construction). Until the rule, every
# path stayed: tests/test_session_env.py's blind-spot class constructs about 180 censuses, each over a distinct
# sabotaged copy of kernel/sdk_backend.py, so each construction left about 165k objects alive (about 70k AST nodes,
# 60k dicts, 37k lists) under a dead path, and after about 150 copies every full garbage collection walked tens of
# millions of objects. Measured before the rule, serial, with a plugin timing every construction: 154 of 185
# constructions took 1.0 to 1.5 s, 14 at or above 2 s carried 120.5 s of the module's 329.4 s inside __init__, the
# slowest 21.8 s; every slow construction held exactly one gen-2 collection, the slow ones shared no plant shape
# and moved between items on a rerun. Over 30 plain copies in one process, before the rule, the gen-2 pauses grew from
# 0.23 s at the second copy to 3.42 s at the 27th, 10 collections carrying 14.5 of 44.0 s; with the rule the same
# script's figures are in tests/test_session_env.py's retention pins' class docstring. The cache exists for the
# `census(CENSUS_FILES)` sites, which share one construction of the canonical files through `_CENSUS` below (the
# door keeps a Census under the same rule). gc is neither disabled nor tuned anywhere: the heap that grew was this
# cache's, and the fix is at the cache. The module's tail was a process-lifetime cache and a fixpoint's enqueue rule,
# not the per-copy walk over the real file: the real-file plants (one sabotaged copy of the real 21,735-line file
# per defect) are not the cost, and must not be traded for synthetic small modules the next time someone reads
# about 300 seconds and reaches for the obvious lever; the evidence-preserving option was also the fast one.
ASTS = {}


def retained_paths():
    """The paths `parsed` keeps for the process's life: the census's canonical inputs, DEFAULT_FILES by realpath, the
    same table `census()` defaults to and keys `_CENSUS` by. Derived on every call (three realpaths, once per file per
    construction), so a table edited in a scratch copy of this module changes the retained set with it."""
    return frozenset(os.path.realpath(f) for f in DEFAULT_FILES)


def parsed(path):
    path = os.path.realpath(path)
    hit = ASTS.get(path)
    if hit is None:
        src = pathlib.Path(path).read_text(encoding="utf-8")
        hit = (src, ast.parse(src, filename=path))
        if path in retained_paths():
            ASTS[path] = hit
    return hit


class Fn:
    __slots__ = ("qual", "name", "file", "base", "node", "cls", "parent", "params", "kwonly", "vararg", "kwarg",
                 "defaults", "kind", "calls", "assigns", "returns", "lexical", "nested", "globals_", "annotations",
                 "name_reads", "_params_set", "_assigned", "_loops", "_chain")

    def __init__(self, qual, name, file, node, cls, parent):
        self.qual, self.name, self.file, self.node, self.cls, self.parent = qual, name, file, node, cls, parent
        self.base = os.path.basename(file)
        self.calls, self.assigns, self.returns, self.nested, self.globals_ = [], [], [], {}, set()
        self.name_reads = set()    # every identifier read as a bare Name under this def (Census._index says which nodes)
        self.lexical = {}          # id(call) -> True when the call sits inside an except handler of this def
        self.kind = "function"     # function | method | static | classmethod | lambda
        args = node.args
        self.params = [a.arg for a in getattr(args, "posonlyargs", ()) + args.args]
        self.kwonly = [a.arg for a in args.kwonlyargs]
        # parameter annotations, by name: the type a receiver resolves by (`be: SdkBackend`, `backend: "SdkBackend"`)
        self.annotations = {a.arg: a.annotation for a in getattr(args, "posonlyargs", ()) + args.args + args.kwonlyargs
                            if a.annotation is not None}
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

    LOOP_NODES = (ast.For, ast.AsyncFor, ast.comprehension, ast.With, ast.AsyncWith)

    def loops(self):
        """The for loops, comprehensions and with items of this function's own body: every such node under the def's
        own node (its decorators, default arguments and annotations included) outside any nested def or lambda. The
        walk below defines the set; Census._index fills it during its one pass (fork PR 781: the walk was a second full
        traversal per function, 0.12 s of a 0.9 s construction over the real pair), so the walk runs only for a Fn the
        index did not build. The two orders differ; _taint_fn unions its stores to a fixpoint, so the result does not."""
        if self._loops is None:
            out = []
            stack = [self.node]
            while stack:
                n = stack.pop()
                for ch in ast.iter_child_nodes(n):
                    if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                        continue
                    if isinstance(ch, Fn.LOOP_NODES):
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
    __slots__ = ("path", "base", "src", "tree", "top_defs", "classes", "top_assigns", "top_lists", "fns", "imports")

    def __init__(self, path):
        self.path = os.path.realpath(path)
        self.base = os.path.basename(path)
        self.src, self.tree = parsed(path)
        self.top_defs, self.classes, self.top_assigns, self.top_lists, self.fns = {}, {}, {}, set(), []
        self.imports = set()      # the names `import` and `from ... import` bind at module level (os, json, deque)


class DoorCall:
    """One call that reaches the ring. `site` is the call node whose line names it; `kind` says how it resolves."""
    __slots__ = ("file", "base", "lineno", "fn", "kind", "node", "message", "ring_text", "problem", "key", "heads",
                 "unreduced", "taint", "ring_formats", "lexical", "via", "alts", "residual")

    def __init__(self, fn, node, kind, message, ring_text, problem, key, via=None):
        self.fn, self.node, self.kind = fn, node, kind
        self.file, self.base, self.lineno = fn.file, fn.base, node.lineno
        self.message, self.ring_text, self.problem, self.key, self.via = message, ring_text, problem, key, via
        self.heads, self.unreduced, self.taint, self.ring_formats, self.lexical = [], False, frozenset(), [], False
        self.alts = []     # (problem, ring_text, inner DoorCall) of further inner calls the same conduit site reaches
        self.residual = frozenset()   # a conduit's inner call: the taint its sites do NOT carry (residual_taint)

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
        self.attr_readers = collections.defaultdict(set)   # attribute name -> Fns reading `<x>.<name>`, or it by reflection
        self.global_readers = collections.defaultdict(set)  # (module path, name) -> Fns reading the module-level name
        self.ring_refs = []      # (Mod, Attribute node, enclosing Fn or None) for every `<x>._problems` in the files
        self.ident_consts = []   # (Mod, Constant node, enclosing Fn or None) for every string constant spelling an identifier
        self.all_fns = []
        self.failures = []       # (kind, base, lineno, text)
        self._failed_sites = set()
        # every identifier a source is spelled by, for the string-constant rule (the key source 'env' excepted: a key
        # is spelled as a string at every read by nature)
        self._source_idents = set(sources["attr"]) | {q.split(".")[-1] for _b, q in sources["func"]} | {n for _b, n in sources["name"]}
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
            fn._loops = []              # filled below as the pass meets the loop nodes (Fn.loops says which)
            mod.fns.append(fn)
            self.all_fns.append(fn)
            self.fn_by_node[id(node)] = fn
            self.defs_by_name[name].append(fn)
            if parent is not None:
                parent.nested.setdefault(name, []).append(fn)
            return fn

        def stray_loops(nodes, owner):
            """The loop nodes under fields this pass does not otherwise visit (a class statement's keywords, a def's or
            class's type parameters), for Fn.loops of `owner`, by the walk that defines the set; and the reads under
            those fields, for the readers indexes (name_reads, so global_readers; attr_readers, the reflected forms
            too), the way `handle` records a read it visits. Fork PR 781's independent verifier found the loop nodes
            fed without their reads: a comprehension in a class keyword read a module list a later method extends,
            the readers-only enqueue on the grown name did not know its function, and the comprehension's variable
            stayed clean where the module-wide sweep had tainted it (pinned in tests/test_session_env.py). The nodes
            go to no other record (`handle` would file their calls in fn.calls, which changes a result)."""
            if owner is None:
                return
            stack = list(nodes)
            while stack:
                n = stack.pop()
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                    owner.name_reads.add(n.id)
                elif isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load):
                    self.attr_readers[n.attr].add(owner)
                elif isinstance(n, (ast.Call, ast.Subscript)):
                    ra = self._reflected_attr(n)
                    if ra is not None:
                        self.attr_readers[ra[1]].add(owner)
                for ch in ast.iter_child_nodes(n):
                    if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                        continue
                    if isinstance(ch, Fn.LOOP_NODES):
                        owner._loops.append(ch)
                    stack.append(ch)
            for n in nodes:
                if isinstance(n, Fn.LOOP_NODES):
                    owner._loops.append(n)

        def handle(child, cls, fn, handler, also=None):
            """One node, in the scope (cls, fn) and lexical handler state of its parent. `also` is a second Fn the taint
            pass evaluates the node under besides the lexical `fn`: the def or lambda whose decorators, default arguments
            or annotations hold it (Fn.loops walks them from the def's own node, so a comprehension there is tainted
            under the def, while the node's calls and assignments are the enclosing scope's), or the function whose body
            holds the class body the node sits in (the same walk crosses a nested class). Both Fns are readers of the
            attributes and module-level names the node reads."""
            if isinstance(child, ast.Attribute):
                if child.attr == self.RING_ATTR:
                    self.ring_refs.append((mod, child, fn))
                if isinstance(child.ctx, ast.Load):
                    if fn is not None:
                        self.attr_readers[child.attr].add(fn)
                    if also is not None:
                        self.attr_readers[child.attr].add(also)
            elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                if fn is not None:
                    fn.name_reads.add(child.id)
                if also is not None:
                    also.name_reads.add(child.id)
            elif isinstance(child, ast.Constant) and isinstance(child.value, str) and child.value.isidentifier():
                self.ident_consts.append((mod, child, fn))
            elif isinstance(child, Fn.LOOP_NODES):
                # Fn.loops: the node belongs to the innermost enclosing def or lambda, `also` where the node sits in a
                # def's decorators, defaults or annotations or in a class body inside a function, else the lexical fn
                owner = also if also is not None else fn
                if owner is not None:
                    owner._loops.append(child)
            elif isinstance(child, (ast.Call, ast.Subscript)):
                # an attribute read by REFLECTION (`getattr(x, "n", d)`, `vars(x)["n"]`, `x.__dict__["n"]`, `x.__dict__.get("n")`)
                # is a reader of `n` like `<x>.n` is, by the recognition expr_taint reads it through (_reflected_attr). Found
                # by fork PR 781's differential when the module-wide sweep below went: _stamp_launch_login reads
                # `getattr(sess, "_launching", None)`, the attribute's taint grows after its first visit, and the sweep on a
                # grown module name had been giving it the re-visit the attribute owed it
                ra = self._reflected_attr(child)
                if ra is not None:
                    for reader in (fn, also):
                        if reader is not None:
                            self.attr_readers[ra[1]].add(reader)
            if isinstance(child, ast.ClassDef):
                c = Cls(child.name, mod.path, child, [ast.unparse(b) for b in child.bases])
                if fn is None:
                    mod.classes[child.name] = c
                self.classes_by_name[child.name].append(c)
                self.cls_by_node[id(child)] = c
                stray_loops([kw.value for kw in child.keywords] + list(getattr(child, "type_params", ())), fn if fn is not None else also)
                for d in child.decorator_list + child.bases:
                    self.parents[d] = child
                    handle(d, cls, fn, handler, also)
                for stmt in child.body:
                    self.parents[stmt] = child
                    handle(stmt, c, None, False, fn if fn is not None else also)
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
                stray_loops(list(getattr(child, "type_params", ())), f)
                for d in child.decorator_list:
                    self.parents[d] = child
                    handle(d, cls, fn, handler, f)
                self.parents[child.args] = child
                handle(child.args, cls, fn, handler, f)
                if child.returns is not None:
                    self.parents[child.returns] = child
                    handle(child.returns, cls, fn, handler, f)
                for stmt in child.body:
                    self.parents[stmt] = child
                    handle(stmt, None, f, False)
                return
            if isinstance(child, ast.Lambda):
                f = new_fn(child, None, fn, "<lambda@%d>" % child.lineno, "lambda")
                self.parents[child.args] = child
                handle(child.args, cls, fn, handler, f)
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
            elif isinstance(child, (ast.Yield, ast.YieldFrom)):
                # a generator's yields are its returns: what its consumer receives (`dict(_gen())`, a for over it);
                # blind-spot lens of review round 6: a yielded ("opts", e) crossed into a dict with its taint unread
                if fn is not None and child.value is not None:
                    fn.returns.append(child.value)
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                if fn is None and cls is None:
                    for alias in child.names:
                        mod.imports.add((alias.asname or alias.name).split(".")[0])
            elif fn is not None:
                if isinstance(child, ast.Call):
                    fn.calls.append(child)
                    fn.lexical[id(child)] = handler
                    self.fn_of[id(child)] = fn
                elif isinstance(child, (ast.Name, ast.Attribute)):
                    self.fn_of[id(child)] = fn
            for sub in ast.iter_child_nodes(child):
                self.parents[sub] = child
                handle(sub, cls, fn, handler, also)

        for stmt in mod.tree.body:
            self.parents[stmt] = mod.tree
            handle(stmt, None, None, False)
        # the readers of each module-level name, built like attr_readers: the functions with a bare Name read of it that
        # no scope of theirs binds, the test expr_taint and _keyed_taint make before they fall to the name's stored taint
        # (_binds, then _global_read). The taint pass re-visits these, and only these, when the stored taint grows
        # (_taint says why); the module's defs are complete here, so every scope's bindings are known.
        for fn in mod.fns:
            for name in fn.name_reads:
                if not self._binds(fn, name):
                    self.global_readers[(mod.path, name)].add(fn)

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
    def _scope_binds(s, name):
        """Whether the scope `s` (a Fn or ScopeFn) binds `name` as a parameter or by an assignment statement. A loop or
        with target is no binding here: its taint sits in tainted_names alone, which the readers check first."""
        return name in s.all_params() or name in s.assigned()

    def _binds(self, fn, name):
        """Whether any scope of fn's chain binds `name`. A bare Name read that none binds falls to the module-level
        name's stored taint (_global_read); the readers index global_readers is built in _index from this same test,
        so the functions the taint pass re-visits on a grown module name are the ones whose reads can reach it."""
        return any(self._scope_binds(s, name) for s in self.scope_chain(fn))

    def _global_read(self, fn, name):
        """The stored taint of the module-level name `name` as read from fn (a name of fn's own module), or None: the
        one read of global_taint the walks make. A subclass observing it sees every such read (the readers-index pin)."""
        return self.global_taint.get((self.mod_of(fn).path, name))

    def _global_growth_readers(self, key):
        """The functions to re-visit when the module-level name `key` ((module path, name)) gains taint: its readers by
        the index. Returning self.mods[key[0]].fns restores the module-wide sweep this replaced (the fixpoint pin in
        tests/test_session_env.py does, to show the two reach the same result)."""
        return self.global_readers.get(key, ())

    @staticmethod
    def _leaves(t):
        """The leaf targets of an assignment or loop target: a nested tuple or list is flattened to any depth (blind-spot
        lens of review round 6: `(k, v), = d.items()`, `for i, (k, v) in enumerate(d.items())` and
        `*_rest, (k, v) = list(d.items())` bound their inner names past a one-level flatten, so the env under v went
        unread). A starred name stays starred (its reader unwraps it)."""
        if isinstance(t, (ast.Tuple, ast.List)):
            out = []
            for el in t.elts:
                out.extend(Census._leaves(el))
            return out
        if isinstance(t, ast.Starred) and isinstance(t.value, (ast.Tuple, ast.List)):
            return Census._leaves(t.value)
        return [t]

    @staticmethod
    def _targets(st):
        if isinstance(st, ast.Assign):
            out = []
            for t in st.targets:
                out.extend(Census._leaves(t))
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
        if isinstance(f, ast.Call) and self._getattr_name(f) is not None and f.args:
            # `getattr(x, "<name>")(...)`: a call through reflection with the name spelled, resolved as `x.<name>(...)`
            # (blind-spot lens of review round 6: a source method called this way had its return read as clean)
            f = ast.Attribute(value=f.args[0], attr=self._getattr_name(f), ctx=ast.Load())
        if isinstance(f, ast.Name):
            if self.is_param(f.id, fn) is not None:
                return []
            for s in self.scope_chain(fn):
                if f.id in s.nested:
                    return [(x, "name") for x in s.nested[f.id]]
                sts = list(self._assigns_name(s, f.id))
                if sts:
                    # a local bound to a lambda (`f = lambda: {...}; f()`) or to a nested def's name is that function
                    # (blind-spot lens of review round 6: a lambda re-keying the env, called by its name, went unread)
                    out = []
                    for st in sts:
                        v = self._value_for(st, f.id)
                        if isinstance(v, ast.Lambda) and id(v) in self.fn_by_node:
                            out.append((self.fn_by_node[id(v)], "name"))
                        elif isinstance(v, ast.Name):
                            for s2 in self.scope_chain(fn):
                                if v.id in s2.nested:
                                    out.extend((x, "name") for x in s2.nested[v.id])
                                    break
                    return out
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

    @staticmethod
    def _getattr_name(call):
        """The spelled name of `getattr(x, "<name>"[, default])`, else None."""
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "getattr" \
                and 2 <= len(call.args) <= 3 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
            return call.args[1].value
        return None

    def _class_object(self, x):
        """Whether an attribute's receiver is a CLASS OBJECT, so that `<x>.<door>` is the plain function and a call
        through it supplies self explicitly and the message second: a class name; `cls` (a classmethod's class);
        `type(self)`; `self.__class__` (blind-spot lens of review round 6: `cls._log(be or 'x', msg, ...)` in a
        classmethod was read with `be or 'x'` as its message, and the literal head hid the row from the unreduced
        pin)."""
        if isinstance(x, ast.Name):
            return x.id == "cls" or (x.id in self.classes_by_name and x.id != "self")
        if isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == "type" and len(x.args) == 1:
            return True
        return isinstance(x, ast.Attribute) and x.attr == "__class__"

    @staticmethod
    def _reflected_attr(node):
        """(receiver, attribute name, [extra arguments]) for an attribute read by REFLECTION with the name spelled:
        `getattr(x, "n"[, d])`, `vars(x)["n"]`, `x.__dict__["n"]`, `x.__dict__.get("n"[, d])` / `.setdefault("n", v)` /
        `.pop("n"[, d])`; else None. Read as `x.n` (blind-spot lens of review round 6: `getattr(sess, "env_vars")` and
        `vars(sess)["env_vars"]` were no source read, and the reflection guard knew the door's name alone)."""
        if isinstance(node, ast.Call):
            name = Census._getattr_name(node)
            if name is not None:
                return (node.args[0], name, list(node.args[2:]))
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr in ("get", "setdefault", "pop") and isinstance(f.value, ast.Attribute) \
                    and f.value.attr == "__dict__" and node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                return (f.value.value, node.args[0].value, list(node.args[1:]))
            return None
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            v = node.value
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "vars" and len(v.args) == 1:
                return (v.args[0], node.slice.value, [])
            if isinstance(v, ast.Attribute) and v.attr == "__dict__":
                return (v.value, node.slice.value, [])
        return None

    @staticmethod
    def _reflection_follows(node, up):
        """Whether a string constant spelling a name sits where the census reads it as that attribute (the forms
        _reflected_attr reads, plus `setattr(x, "n", v)`, which the in-place store pass reads)."""
        if isinstance(up, ast.Call) and isinstance(up.func, ast.Name) and up.func.id in ("getattr", "setattr") \
                and len(up.args) >= 2 and up.args[1] is node:
            return True
        if isinstance(up, ast.Subscript) and up.slice is node:
            v = up.value
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "vars":
                return True
            if isinstance(v, ast.Attribute) and v.attr == "__dict__":
                return True
        if isinstance(up, ast.Call) and isinstance(up.func, ast.Attribute) and up.func.attr in ("get", "setdefault", "pop") \
                and isinstance(up.func.value, ast.Attribute) and up.func.value.attr == "__dict__" and up.args and up.args[0] is node:
            return True
        return False

    def _fail(self, kind, base, lineno, text):
        """A failure named by site, recorded once (the taint pass runs to a fixpoint and would otherwise repeat it)."""
        key = (kind, base, lineno)
        if key not in self._failed_sites:
            self._failed_sites.add(key)
            self.failures.append((kind, base, lineno, text))

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
        self.alias_collisions = {}      # alias name -> ["<Class>.<name> (<how bound>)"] for every OTHER class binding the name
        self.ambiguous_aliases = set()  # the names with a collision: resolved by the receiver's scope, failed when untyped
        self._ambiguous_seen = set()    # id(Attribute node) already failed as an untyped receiver of such a name
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
        # an alias name that is also an instance attribute, a method or a class-body name of ANOTHER class (the lens's
        # `_ring`, ApiHealth's deque) is two bindings the AST tells apart by scope (ruling 4 of review round 6): the
        # collision is recorded here, and _alias_resolution decides each reference by its receiver, failing only the
        # untyped receiver where both bindings could apply
        for name, lst in self.class_alias_doors.items():
            owners = {id(c) for c, _v in lst}
            elsewhere = []
            for cl in self.classes_by_name.values():
                for c in cl:
                    if id(c) in owners:
                        continue
                    hows = [how for has, how in ((name in c.bindings, "an attribute bound in __init__"), (name in c.methods, "a method"),
                                                 (name in c.class_assigns, "a class-body name")) if has]
                    if hows:
                        elsewhere.append("%s.%s (%s)" % (c.name, name, ", ".join(hows)))
            if elsewhere:
                self.ambiguous_aliases.add(name)
                self.alias_collisions[name] = sorted(elsewhere)

    OPAQUE_TYPES = frozenset({"object", "Any"})    # annotations every instance satisfies: they type nothing

    def _opaque_class(self, c):
        """A class of the files that types its instances structurally or forwards attributes, so that a receiver of it
        can be any object: a Protocol (`class X(Protocol)`), or a class defining __getattr__ or __getattribute__ (a
        proxy). Blind-spot lens of review round 6: a receiver typed by a Protocol declaring the alias, and a proxy
        forwarding to a backend, each resolved to the other binding silently."""
        return any(b.split("[")[0].split(".")[-1] == "Protocol" for b in c.bases) \
            or "__getattr__" in c.methods or "__getattribute__" in c.methods

    def receiver_classes(self, e, fn, depth=0):
        """The classes an attribute's receiver can be an instance of, or None when the walk cannot type it: `self` or
        `cls` (the enclosing class); a class name (an unbound access on the class itself); `type(x)` and `x.__class__`
        (x's classes); a parameter annotated with a class of the files (`be: SdkBackend`, the string form
        `backend: "SdkBackend"`, an Optional or a union of one), unless the body reassigns it, when every assignment
        counts too; a local every assignment of which is a constructor call or another typed expression; and
        `self.<attr>` bound in __init__ from a typed expression, through the MRO. A list may be empty (a typed receiver
        of no class of the files: `x: int`), which is typed all the same; `object`, `Any` and a Protocol or proxy class
        of the files type nothing (None)."""
        r = self._receiver_classes(e, fn, depth)
        if r and any(self._opaque_class(c) for c in r):
            return None
        return r

    def _receiver_classes(self, e, fn, depth=0):
        if depth > 4 or e is None:
            return None
        if isinstance(e, ast.Name):
            if e.id in ("self", "cls"):
                c = self.class_of(fn)
                return [c] if c is not None else []
            owner = self.is_param(e.id, fn)
            if owner is not None:
                ann = self._annotation_classes(getattr(owner, "annotations", {}).get(e.id))
                sts = list(self._assigns_name(owner, e.id)) if owner.kind != "scope" else []
                if not sts:
                    return ann
                # an annotated parameter REASSIGNED in the body is what the assignments make it, the annotation
                # included (blind-spot lens of review round 6: `h: ApiHealth` then `h = be` kept the annotation's type)
                if ann is None:
                    return None
                out = list(ann)
                for st in sts:
                    v = self._value_for(st, e.id)
                    r = self.receiver_classes(v, owner, depth + 1) if v is not None and not isinstance(v, tuple) else None
                    if r is None:
                        return None
                    out.extend(r)
                return out
            for s in self.scope_chain(fn):
                sts = list(self._assigns_name(s, e.id))
                if sts:
                    out = []
                    for st in sts:
                        v = self._value_for(st, e.id)
                        r = self.receiver_classes(v, s, depth + 1) if v is not None and not isinstance(v, tuple) else None
                        if r is None:
                            return None
                        out.extend(r)
                    return out
            if e.id in self.classes_by_name:
                return list(self.classes_by_name[e.id])
            return None
        if isinstance(e, ast.Call):
            f = e.func
            if isinstance(f, ast.Name) and f.id == "type" and len(e.args) == 1:
                return self.receiver_classes(e.args[0], fn, depth + 1)
            name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if name in self.classes_by_name and not (isinstance(f, ast.Name) and self.is_param(name, fn) is not None):
                return list(self.classes_by_name[name])
            return None
        if isinstance(e, ast.Attribute) and e.attr == "__class__":
            return self.receiver_classes(e.value, fn, depth + 1)
        if isinstance(e, ast.Attribute) and isinstance(e.value, ast.Name) and e.value.id == "self":
            c = self.class_of(fn)
            if c is None:
                return None
            binds = [b for k in self.mro(c) for b in k.bindings.get(e.attr, [])]
            if not binds:
                return None
            out = []
            for v, bfn in binds:
                r = self.receiver_classes(v, bfn, depth + 1)
                if r is None:
                    return None
                out.extend(r)
            return out
        return None

    def _annotation_classes(self, ann):
        """The classes of the files an annotation names, [] for a type of no class of ours, None for no annotation or
        one the walk cannot read."""
        if ann is None:
            return None
        if isinstance(ann, ast.Constant):
            if ann.value is None:
                return []
            if not isinstance(ann.value, str):
                return None
            name = ann.value.split("[")[0].split(".")[-1].strip()
            if not name.isidentifier():
                return None
        elif isinstance(ann, ast.Name):
            name = ann.id
        elif isinstance(ann, ast.Attribute):
            name = ann.attr
        elif isinstance(ann, ast.Subscript):          # Optional[X]
            return self._annotation_classes(ann.slice)
        elif isinstance(ann, ast.BinOp) and isinstance(ann.op, ast.BitOr):     # X | None
            sides = [self._annotation_classes(ann.left), self._annotation_classes(ann.right)]
            if any(s is None for s in sides):
                return None
            return sides[0] + sides[1]
        else:
            return None
        if name in self.OPAQUE_TYPES:
            return None           # `object`, `Any`, `typing.Any`, "Any": every instance satisfies it, so it types nothing
        return list(self.classes_by_name.get(name, []))

    def _alias_resolution(self, e, fn):
        """'door' | 'not' for `<receiver>.<alias>`, <alias> a class-body alias of the door, by the receiver's SCOPE
        (ruling 4 of review round 6, where the lens planted `_ring = _log` in the writer's class beside ApiHealth's
        `self._ring` deque): the receiver's classes are walked in MRO order and the first that is the alias's owner
        resolves to the alias (a door), the first that binds the name itself (an attribute bound in __init__, a method,
        a class-body name) resolves to that binding (no door); a class with neither whose subclass owns the alias
        resolves to the alias (self may be that subclass); a receiver the walk cannot type resolves to the alias when no
        other class binds the name, and is the loud door-alias-ambiguous failure naming both bindings when one does."""
        name = e.attr
        owners = [c for c, _v in self.class_alias_doors[name]]
        recv = self.receiver_classes(e.value, fn)
        if recv is None:
            if name in self.alias_collisions:
                self._ambiguous_site(e, fn, "the receiver is untyped")
                return "not"
            return "door"
        decided = set()
        for c in recv:
            # every class an instance of c can be: c itself and each subclass of it (self in a mixin is an instance of
            # the class the mixin is mixed into; a parameter typed by a base is an instance of the base or a subclass),
            # each decided by its own MRO (blind-spot lens of review round 6: a mixin mixed into the writer's class
            # resolved to the deque, and a mixin mixed into both classes resolved silently to no door)
            for k in [c] + self.subclasses(c):
                d = self._binding_of(k, name, owners)
                if d is not None:
                    decided.add(d)
        if decided == {"door"}:
            return "door"
        if len(decided) == 2:
            self._ambiguous_site(e, fn, "the receiver's type admits both bindings")
        return "not"

    def _binding_of(self, cls, name, owners):
        """'door' | 'not' | None: what `<an instance of cls>.<name>` is, by the MRO: the first class that owns the alias
        is the door, the first that binds the name itself (an attribute bound in __init__, a method, a class-body name)
        is that binding; None when no class of the MRO does either."""
        for k in self.mro(cls):
            if any(k is o for o in owners):
                return "door"
            if name in k.bindings or name in k.methods or name in k.class_assigns:
                return "not"
        return None

    def _ambiguous_site(self, e, fn, why):
        key = (fn.base, e.lineno, ast.unparse(e))
        if key in self._ambiguous_seen:
            return
        self._ambiguous_seen.add(key)
        name = e.attr
        both = ["%s.%s (a class-body alias of the door, line %d)" % (c.name, name, v.lineno) for c, v in self.class_alias_doors[name]] \
            + self.alias_collisions[name]
        self.failures.append(("door-alias-ambiguous", fn.base, e.lineno,
                              "%s in %s: %s and %s is bound twice, %s; type the receiver (an annotation "
                              "naming the class, a constructor call) or rename one binding" % (ast.unparse(e), fn.qual, why, name, " and ".join(both))))

    def door_value(self, e, fn, seen=None):
        """'door' | 'not' | 'unfollowed' for an expression used as a value (or as a callee)."""
        seen = seen if seen is not None else set()
        door = self.door
        if isinstance(e, ast.Attribute) and e.attr != door and e.attr in getattr(self, "class_alias_doors", {}):
            # a class-body alias of the door (resolved in _scope_aliases), read through a receiver: resolved by the
            # receiver's scope (_alias_resolution), so ApiHealth's `self._ring` deque and a planted `_ring = _log` in
            # the writer's class are told apart, and only an untyped receiver of such a twice-bound name fails
            return self._alias_resolution(e, fn)
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
            name = self._getattr_name(e)
            if name == door:
                return "door"
            if name is not None and name in getattr(self, "class_alias_doors", {}):
                # `getattr(x, "<alias>")`: the alias's name spelled, resolved by x's scope like `x.<alias>` (blind-spot
                # lens of review round 6: the reflection guard read the door's own name only)
                return self._alias_resolution(ast.Attribute(value=e.args[0], attr=name, ctx=ast.Load(), lineno=e.lineno,
                                                            col_offset=e.col_offset), fn)
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
            if e.attr == door or e.attr in self.class_alias_doors:
                # the alias is the writer's function: access through an instance binds it, through the class object
                # (a class name, cls, type(self), self.__class__) it is the plain function and the message comes second
                return "unbound" if self._class_object(e.value) else "bound"
            return None
        if isinstance(e, ast.Call):
            f = e.func
            name = self._getattr_name(e)
            if name == door or (name is not None and name in self.class_alias_doors):
                return "unbound" if self._class_object(e.args[0]) else "bound"
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
                        if isinstance(el, (ast.Tuple, ast.List, ast.Starred)) and any(
                                isinstance(leaf, ast.Name) and leaf.id == name for leaf in Census._leaves(el)):
                            return ("index", st.value, i)       # bound from inside the i-th element: read whole
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
                gname = self._getattr_name(f) if isinstance(f, ast.Call) else None
                if gname is not None and (gname == door or gname in self.class_alias_doors):
                    # `getattr(x, "<door or alias>")(...)`: the door called through reflection with the name spelled
                    if self.door_value(f, fn) == "door":
                        kind = "typed" if gname == door else "alias"
                elif isinstance(f, ast.Attribute) and f.attr == door:
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
                    if inner.kind == "param" and isinstance(inner.node.func, ast.Name):
                        # the conduit's door is its own parameter (problem_row's log=): a site that binds it to None, the
                        # default or None written, files nothing through this conduit and is no site of it; any other
                        # binding keeps the site (a door, or an expression the walk keeps on the safe side). The post-merge
                        # census of the env-pick door (2026-09-20): the two refused-launch rows take problem_row's ledger
                        # row and its returned line without log= and file their own bounded ring row.
                        bound = b.get(inner.node.func.id)
                        if isinstance(bound, ast.Constant) and bound.value is None:
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
            name = self._getattr_name(node)
            return name == door or (name is not None and name in self.class_alias_doors and self.door_value(node, fn) == "door")
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
        alias_names = set(self.class_alias_doors) | {name for _path, name in self.module_alias_doors}
        for mod, node, _fn in self.ident_consts:
            up = self.parents.get(node)
            if node.value == door or node.value in alias_names:
                followed = (isinstance(up, ast.Call) and isinstance(up.func, ast.Name) and up.func.id == "getattr"
                            and len(up.args) >= 2 and up.args[1] is node)
                if not followed:
                    what = "the door's name" if node.value == door else "a door alias's name"
                    self.failures.append(("door-name-string", mod.base, node.lineno, "%s %r is a string outside "
                                          "getattr(x, %r): %s" % (what, node.value, node.value, ast.unparse(up)[:60] if up is not None else "?")))
            elif node.value in self._source_idents and not self._reflection_follows(node, up):
                # a SOURCE's name spelled as a string anywhere but the reflected read or store the census follows
                # (`ATTR = "env_vars"; getattr(sess, ATTR)`): a source reached by reflection the walk cannot see, so
                # the string is the failure (blind-spot lens of review round 6: the door had this rule, no source did)
                self.failures.append(("source-name-string", mod.base, node.lineno, "a source's name %r is a string outside a "
                                      "reflected read or store the census follows: %s" % (node.value, ast.unparse(up)[:60] if up is not None else "?")))
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
                    # a class-body alias: called as an attribute (`self.<alias>(...)`, `<typed>.<alias>(...)`) anywhere
                    # the receiver resolves to the alias (a call resolving to another class's binding of the name is
                    # no call of the alias)
                    called = any((isinstance(c.func, ast.Attribute) and c.func.attr == name and self.door_value(c.func, f) == "door")
                                 or (self._getattr_name(c) == name and self.door_value(c, f) == "door")     # getattr(x, "<alias>"), followed
                                 for f in self.all_fns for c in f.calls)
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
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in self.KEY_READS and node.args \
                and isinstance(node.args[0], ast.Constant) and node.args[0].value in s["key"]:
            # a read of the key by method: `d.get("env")`, and `d.pop("env")` or `d.setdefault("env", x)`, which hand
            # the value back too (ruling 2 of review round 6: a helper re-keying by pop read as clean)
            return s["key"][node.args[0].value]
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            tag = s["name"].get((fn.base, node.id))
            if tag and (fn.base, node.id) not in s["opaque_names"] and self.is_param(node.id, fn) is None:
                return tag
        if isinstance(node, ast.Call):
            for callee, _via in self.callees.get(id(node), []):
                tag = s["func"].get((callee.base, callee.qual))
                if tag:
                    # a source function's call read WHOLE (expr_taint is the whole-value context): a function returning
                    # a DICT (the launch shape) holds the env under its key, so `str(shape)` or `shape.values()` carries
                    # it, while a read of one of its OTHER keys goes through _keyed_taint to the return's carried set
                    return tag
        ra = self._reflected_attr(node)
        if ra is not None and ra[1] in s["attr"]:
            return s["attr"][ra[1]]          # `getattr(sess, "env_vars")`, `vars(sess)["env_vars"]`: the attribute by reflection
        dt = self._decl_node_tags.get(id(node))
        if dt:
            return dt          # a root of the value a declared dict source stores under the source key (_declare_roots)
        return None

    def _returns_dicts(self, callee):
        """Every return of `callee` is dict-valued (a literal, a comprehension, dict(...), a local built as one, a call
        to a function that returns dicts)."""
        hit = self._dict_returners.get(callee)
        if hit is None:
            self._dict_returners[callee] = False      # pessimistic while computing: a return through a cycle is no dict
            hit = self._dict_returners[callee] = bool(callee.returns) and all(self._dict_valued(r, callee) for r in callee.returns)
        return hit

    def _declared_dict_source(self, fn):
        """The tag of a function declared a SOURCE (sources["func"]) whose every return is dict-valued, else None: such a
        function is a source at its env key, not whole, and _taint_fn follows the value it stores under that key."""
        tag = self.sources["func"].get((fn.base, fn.qual))
        if tag and (fn.base, fn.qual) not in self.sources["opaque_returns"] and self._returns_dicts(fn):
            return tag
        return None

    def _source_key_stores(self, fn):
        """Every store under a SOURCE key in fn's own body, as (holder, value): the dict literal's or dict(...) call's
        target when it is assigned to a Name or an attribute on the spot (None when used in place), a subscript
        store's container (`d["env"] = v`), an update's or setdefault's receiver (`d.update(env=v)`,
        `d.setdefault("env", v)`); nested defs and lambdas excluded."""
        out, keys = [], self.sources["key"]
        stack = list(fn.node.body) if isinstance(fn.node, (ast.FunctionDef, ast.AsyncFunctionDef)) else [fn.node.body]
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            if isinstance(n, ast.Dict):
                for k, v in zip(n.keys, n.values):
                    if isinstance(k, ast.Constant) and k.value in keys:
                        out.append((self._holder_of(n), v))
            elif isinstance(n, ast.Call):
                f = n.func
                if isinstance(f, ast.Name) and f.id == "dict":
                    for kw in n.keywords:
                        if kw.arg in keys:
                            out.append((self._holder_of(n), kw.value))
                elif isinstance(f, ast.Attribute) and f.attr == "update":
                    for kw in n.keywords:
                        if kw.arg in keys:
                            out.append((f.value, kw.value))
                elif isinstance(f, ast.Attribute) and f.attr in ("setdefault", "__setitem__") and len(n.args) >= 2 \
                        and isinstance(n.args[0], ast.Constant) and n.args[0].value in keys:
                    out.append((f.value, n.args[1]))
                elif ((isinstance(f, ast.Name) and f.id == "setitem") or (isinstance(f, ast.Attribute) and f.attr == "setitem")) \
                        and len(n.args) >= 3 and isinstance(n.args[1], ast.Constant) and n.args[1].value in keys:
                    out.append((n.args[0], n.args[2]))       # operator.setitem(d, "env", v)
            stack.extend(ast.iter_child_nodes(n))
        for st in fn.assigns:
            if isinstance(st, (ast.Assign, ast.AnnAssign)) and st.value is not None:
                for t in self._targets(st):
                    if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and t.slice.value in keys:
                        out.append((t.value, st.value))
        return out

    def _holder_of(self, n):
        """The single Name or attribute target a dict expression is assigned to on the spot, else None."""
        up = self.parents.get(n)
        while isinstance(up, ast.IfExp):
            n, up = up, self.parents.get(up)
        if isinstance(up, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and getattr(up, "value", None) is n:
            targets = self._targets(up)
            if len(targets) == 1 and isinstance(targets[0], (ast.Name, ast.Attribute)):
                return targets[0]
        return None

    def _locates_source_key(self, r, fn, depth=0):
        """Whether the census can place the env inside a declared dict source's return `r`: a literal with the source
        key (a splat beside it is fine: the key is still read as a source), dict(...) with the key as a keyword, a
        conditional of two such, or a local some store in the function put the key into. A comprehension (its keys
        cannot be tracked), a literal without the key or a local nothing stored the key into is not located."""
        if depth > 4 or r is None:
            return False
        keys = self.sources["key"]
        if isinstance(r, ast.Dict):
            return any(isinstance(k, ast.Constant) and k.value in keys for k in r.keys)
        if isinstance(r, ast.Call) and isinstance(r.func, ast.Name) and r.func.id == "dict":
            return any(kw.arg in keys for kw in r.keywords)
        if isinstance(r, ast.IfExp):
            return self._locates_source_key(r.body, fn, depth + 1) and self._locates_source_key(r.orelse, fn, depth + 1)
        if isinstance(r, ast.Name):
            return any(isinstance(h, ast.Name) and h.id == r.id for h, _v in self._source_key_stores(fn))
        return False

    def expr_taint(self, expr, fn):
        """The union of tags carried by any node in the expression's subtree; a resolved call contributes its callee's
        return taint and is not walked into (its parameters are tainted by propagation instead). A Name that is no
        parameter and no local of any enclosing scope reads the module-level name's taint; an attribute read
        (`<x>.<attr>`) carries whatever any store into `.<attr>` put there (keyed by attribute NAME over every receiver,
        the direction that finds a value stored in one method and read in another)."""
        tags = set()
        stack = [expr]
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
                    if self._scope_binds(s, node.id):
                        found = True
                        break
                if not found:
                    gt = self._global_read(fn, node.id)
                    if gt:
                        tags |= gt
                continue
            if isinstance(node, ast.Compare) and all(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops) \
                    and all(isinstance(cmp, ast.Constant) and cmp.value is None for cmp in node.comparators):
                # `x is None`, `x is not None`: an identity test against None is a truth value about x, never a value
                # of x, so a shape held whole in x (`launching = self._launching`) does not reach the flag it sets
                continue
            if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load) and isinstance(node.slice, ast.Constant) \
                    and node.slice.value not in self.sources["key"] and self._reflected_attr(node) is None:
                # a read of ONE key that is no source key: what the container's carried set holds (the values under
                # its other keys), not the container whole; `shape["mode"]` after `shape = self._launch_shape(sess)`
                tags |= self._keyed_taint(node.value, fn)
                continue
            ra = self._reflected_attr(node)
            if ra is not None:
                # `getattr(x, "n")`, `vars(x)["n"]`, `x.__dict__["n"]`: the attribute by reflection, read whole, plus
                # the default's own taint
                tags |= self.attr_taint.get(ra[1], set()) | self.attr_whole.get(ra[1], set())
                for a in ra[2]:
                    tags |= self.expr_taint(a, fn)
                continue
            kr = self._keyed_read(node)
            if kr is not None and kr[1] not in self.sources["key"]:
                # `d.get("mode")`, `d.pop("mode")`, `d.setdefault("mode", x)`: a keyed read by method, plus its defaults
                tags |= self._keyed_taint(kr[0], fn)
                for a in node.args[1:]:
                    tags |= self.expr_taint(a, fn)
                continue
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                # an attribute read whole: what any store put there, whole (its keyed reads take attr_taint alone)
                tags |= self.attr_taint.get(node.attr, set()) | self.attr_whole.get(node.attr, set())
            if isinstance(node, ast.Call):
                res = self.callees.get(id(node), [])
                if res:
                    for callee, _via in res:
                        if (callee.base, callee.qual) in self.sources["opaque_returns"]:
                            continue
                        rt = self.ret_whole.get(callee)
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
        self.carried_names = {}      # Fn -> {name: set(tags)} what a read of one non-source key of the name yields: its
        #                              taint minus what sits under a SOURCE key of a dict (the whole set for a non-dict)
        self.ret_taint = {}          # Fn -> {"all"|index: set(tags)} what CROSSES a return's dict boundary (a keyed read)
        self.ret_whole = {}          # Fn -> {"all"|index: set(tags)} the returned value WHOLE (`str(shape)`, `shape.values()`)
        self.attr_taint = {}         # attribute name -> set(tags) stored into `<x>.<attr>` anywhere, what a keyed read yields
        self.attr_whole = {}         # attribute name -> set(tags) the stored value whole
        self._dict_returners = {}    # Fn -> whether every return is dict-valued (a source at its env key, not whole)
        self.global_taint = {}       # (module path, name) -> set(tags) stored into a module-level name from a function
        self._decl_node_tags = {}    # id(node) -> tag: the structural roots of a declared dict source's env (_declare_roots)
        self._decl_roots = {}        # Fn -> (Name roots, attribute roots) of the value it stores under the source key
        self._grown_attrs, self._grown_globals = set(), set()
        self._residual_returns, self._residual_stack = {}, set()   # residual_taint's caches (round 7, kernel-1)
        work = collections.deque(self.all_fns)
        queued = set(id(f) for f in self.all_fns)
        rounds = 0
        self.cap_requeues = 0

        def enqueue(f):
            if id(f) not in queued:
                queued.add(id(f))
                work.append(f)

        while work:
            fn = work.popleft()
            queued.discard(id(fn))
            rounds += 1
            self._inner_cap_hit = False
            locals_changed, returns_changed = self._taint_fn(fn)
            if self._inner_cap_hit:
                # the visit's inner loop over the function's own stores ran out of iterations while still growing: the
                # function's own inputs (its locals) changed, so it is a reader of its own state and is owed another
                # visit. Before the readers index below, the module-wide sweep on a grown module name gave such a
                # function its next visit by accident, when a name grew after it; the sweep is gone, so the visit is
                # owed here (the blind-spot class plants a chain the loop needs seven passes for)
                self.cap_requeues += 1
                enqueue(fn)
            if returns_changed:
                # a caller reads this function's returns at the call (expr_taint, _container_taint, _keyed_taint), and
                # nothing else of it: until fork PR 781 a change of its locals alone enqueued every caller too, and the
                # writer's parameters gaining taint sent every door-call function back through the walk for nothing
                for call, caller, _via in self.callers.get(fn, []):
                    enqueue(caller)
            if locals_changed:
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
                # a module-level name's stored taint grew: re-visit its READERS (global_readers, built in _index from the
                # same test expr_taint and _keyed_taint make before they read the name's stored taint, a bare Name read
                # that no scope of the function binds), the way a grown attribute re-visits attr_readers. Until fork
                # PR 781 this enqueued every function of the module: three such events over 715 functions made 2101
                # visits of 743 functions, 85 of which changed anything, and with the blind-spot class constructing 175
                # censuses that put tests/test_session_env.py at 337 s serial against 1.55 s at the PR's base, past CI's
                # 25-minute job ceiling. A function with no read of the grown name re-derives the same sets from the
                # same inputs, so its visit was a no-op; every result is unchanged (the differential over the real pair
                # and the class's copies, and the fixpoint pin in tests/test_session_env.py, which restores the sweep
                # through _global_growth_readers and compares).
                for key in self._grown_globals:
                    for reader in self._global_growth_readers(key):
                        enqueue(reader)
                self._grown_globals = set()
        self.taint_rounds = rounds

    # methods that add to a container in place: a tainted argument taints the receiver (blind-pin lens of review
    # round 6: `parts.append(k)` in a loop over the env names and a module list's `.extend(...)` carried the names to
    # a door with the receiver read as clean)
    MUTATING_METHODS = frozenset({"append", "extend", "insert", "add", "update", "setdefault", "appendleft", "extendleft",
                                  "__setitem__", "push", "put", "put_nowait"})
    # dict methods that READ a key by name and hand its value back: a source key read through one is a source read
    KEY_READS = frozenset({"get", "pop", "setdefault"})
    ENV_ONLY = frozenset({"env"})

    def _taint_fn(self, fn):
        names = self.tainted_names.setdefault(fn, {})
        carried = self.carried_names.setdefault(fn, {})
        self._newly_tainted_callees = []
        before = {k: set(v) for k, v in names.items()}
        before_carried = {k: set(v) for k, v in carried.items()}
        before_ret = {k: set(v) for k, v in self.ret_taint.get(fn, {}).items()}
        before_whole = {k: set(v) for k, v in self.ret_whole.get(fn, {}).items()}
        mod = self.mod_of(fn)
        decl = self._declared_dict_source(fn)
        for _ in range(6):
            grew = False
            if decl:
                # a source FUNCTION whose returns are dicts is a source at its env key, not whole, so the value it stores
                # under that key is the env BY DECLARATION (ruling 2 of review round 6), and the taint follows the VALUE
                # to its ROOTS (_roots: the Names, attribute chains and constant-keyed subscripts the value derives from,
                # a local followed to its own assignments, a walrus target): a Name root is tainted in the function, an
                # attribute root for every reader of the attribute, and any other root structurally, so a second read of
                # the origin under another key, a copy through `dict(e)` or `e or {}`, a comprehension over the value, a
                # tuple index, a second local from the same origin and a walrus all carry the env with it. The dict
                # holding the key is tainted WHOLE (an iteration over its items, a splat, a pop of it carries the env)
                # while what crosses its boundary still excludes the key (the read of the key is a source of its own).
                # Six of the round's ten re-keying variants were quiet before the declaration marked the value; seven
                # of the lens's further variants were quiet while it marked a bare Name or attribute alone.
                name_roots, attr_roots, holders = self._declare_roots(fn, decl)
                for r in name_roots:
                    grew |= self._store(fn, mod, names, carried, r, {decl}, {decl})
                for r in attr_roots:
                    grew |= self._mark_attr(r.attr, {decl})
                for holder in holders:
                    grew |= self._mark(names, holder, {decl})
            for st in fn.assigns:
                value = st.value
                if value is None:
                    continue
                vt = self.expr_taint(value, fn)
                ct = self._container_taint(value, fn)
                dv = self._dict_valued(value, fn)
                if isinstance(st, ast.AugAssign):
                    grew |= self._store(fn, mod, names, carried, st.target, vt, ct)
                    continue
                targets = st.targets if isinstance(st, ast.Assign) else [st.target]
                for t in targets:
                    if isinstance(t, (ast.Tuple, ast.List)):
                        for i, el in enumerate(t.elts):
                            edv = False
                            if isinstance(value, (ast.Tuple, ast.List)) and i < len(value.elts):
                                et, ec = self.expr_taint(value.elts[i], fn), self._container_taint(value.elts[i], fn)
                                edv = self._dict_valued(value.elts[i], fn)
                            elif isinstance(value, ast.Call) and self.callees.get(id(value)):
                                et, ec = self.expr_taint(("index", value, i), fn), self._container_taint(("index", value, i), fn)
                            else:
                                et, ec = vt, vt
                            for leaf in self._leaves(el):        # a nested tuple target takes its element whole
                                grew |= self._store(fn, mod, names, carried, leaf, et, ec, edv)
                    else:
                        grew |= self._store(fn, mod, names, carried, t, vt, ct, dv)
            for node in fn.loops():
                if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                    it = self.expr_taint(node.iter, fn)
                    if it:
                        for el in self._leaves(node.target):
                            grew |= self._store(fn, mod, names, carried, el, it, it)
                elif isinstance(node, (ast.With, ast.AsyncWith)):
                    for item in node.items:
                        if item.optional_vars is not None:
                            it = self.expr_taint(item.context_expr, fn)
                            if it:
                                for el in self._leaves(item.optional_vars):
                                    grew |= self._store(fn, mod, names, carried, el, it, it)
            # in-place adds: `parts.append(k)`, `seen.extend(names)`, `d.setdefault(k, v)`, `self.x.append(v)`; and the
            # stores by reflection, `operator.setitem(d, k, v)` (d.__setitem__), `setattr(x, "n", v)` (x.n = v) and
            # `x.__dict__.setdefault("n", v)` (blind-spot lens of review round 6: each went unread as a store)
            for call in fn.calls:
                f = call.func
                recv, method, cargs = None, None, None
                if isinstance(f, ast.Attribute) and f.attr in self.MUTATING_METHODS:
                    recv, method, cargs = f.value, f.attr, list(call.args)
                elif ((isinstance(f, ast.Name) and f.id in ("setitem", "setattr")) or (isinstance(f, ast.Attribute) and f.attr == "setitem")) \
                        and len(call.args) >= 3:
                    if isinstance(f, ast.Name) and f.id == "setattr":
                        svt = self.expr_taint(call.args[2], fn)
                        if svt:
                            if isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
                                grew |= self._mark_attr(call.args[1].value, self._container_taint(call.args[2], fn),
                                                        svt if self._dict_valued(call.args[2], fn) else None)
                            else:
                                self._fail("reflection-store", fn.base, call.lineno, "a tainted value is stored by %s, a name the "
                                           "census cannot place" % ast.unparse(call)[:60])
                        continue
                    recv, method, cargs = call.args[0], "__setitem__", list(call.args[1:])
                if recv is None:
                    continue
                args = cargs + [k.value for k in call.keywords]
                vt = set()
                for a in args:
                    vt |= self.expr_taint(a, fn)
                if not vt:
                    continue
                if method in ("setdefault", "__setitem__") and cargs and isinstance(cargs[0], ast.Constant) \
                        and cargs[0].value in self.sources["key"]:
                    ct = set()                       # stored under a source key: a source at the read
                elif method == "update":
                    ct = set()
                    for a in cargs:
                        ct |= self._container_taint(a, fn)
                    for k in call.keywords:
                        if k.arg not in self.sources["key"]:
                            ct |= self.expr_taint(k.value, fn)
                else:
                    ct = vt
                if isinstance(recv, ast.Attribute) and recv.attr == "__dict__" and method in ("setdefault", "__setitem__") and cargs:
                    if isinstance(cargs[0], ast.Constant) and isinstance(cargs[0].value, str):
                        # `x.__dict__.setdefault("n", v)`: the attribute n, whole when v is a dict by shape
                        grew |= self._mark_attr(cargs[0].value, ct, vt if any(self._dict_valued(a, fn) for a in cargs[1:]) else None)
                    else:
                        self._fail("reflection-store", fn.base, call.lineno, "a tainted value is stored through %s, a name the "
                                   "census cannot place" % ast.unparse(call)[:60])
                    continue
                grew |= self._store(fn, mod, names, carried, recv, vt, ct, method in ("setdefault", "__setitem__", "update"))
            if not grew:
                break
        else:
            self._inner_cap_hit = True      # every pass grew: _taint gives the function another visit
        # returns. A dict-valued return carries "env" alone, and only what sits under a key that is NOT a source
        # (the per-session env's own key, 'env' in DEFAULT_SOURCES, is a source at the READ, so a dict does not carry
        # it; a value re-keyed under any other name crosses with the dict: blind-pin lens of review round 6, a helper
        # returning {"names": sorted(sess.env_vars)} read as clean). The census does not follow the pick tag (tag
        # "pick") across a dict return: a pick that crosses one is OUTSIDE the census, and the existence population is
        # the direct readers of the surface set by construction. That bounds the census's reach and says nothing of
        # the kernel (ruling 3 of review round 6); followed whole, a session snapshot would carry the pending picks to
        # every reader of every other field (946 functions' returns at the round's head).
        # Two sets per return: what CROSSES the dict's boundary (ret_taint, what a keyed read of the result yields) and the
        # value WHOLE (ret_whole, what `str(shape)`, `shape.values()`, a loop over it or a second dict built from it reads).
        rt = self.ret_taint.setdefault(fn, {})
        rw = self.ret_whole.setdefault(fn, {})
        for r in fn.returns:
            if r is None:
                continue
            if isinstance(r, (ast.Tuple, ast.List)):
                for i, el in enumerate(r.elts):
                    t, w = self._return_taint(el, fn), self._return_whole(el, fn)
                    if t:
                        rt.setdefault(i, set()).update(t)
                    if w:
                        rw.setdefault(i, set()).update(w)
            else:
                t, w = self._return_taint(r, fn), self._return_whole(r, fn)
                if decl:
                    # the declared source's return holds the env, WHOLE, always; across its boundary only where the census
                    # cannot locate the key (no source key in the literal, a comprehension whose keys it cannot track, a
                    # local nothing stored the key into): then the whole return crosses with the tag, the
                    # over-approximating side, never a drop
                    w = set(w) | {decl}
                    if not self._locates_source_key(r, fn):
                        t = set(t) | {decl}
                if t:
                    rt.setdefault("all", set()).update(t)
                if w:
                    rw.setdefault("all", set()).update(w)
        # calls: taint the callees' parameters, whole and carried (what a keyed read of the parameter yields)
        for call in fn.calls:
            for callee, via in self.callees.get(id(call), []):
                b = self.bind_args(call, callee, via)
                cn = self.tainted_names.setdefault(callee, {})
                cc = self.carried_names.setdefault(callee, {})
                for p, v in b.items():
                    if v is callee.defaults.get(p):
                        continue
                    t = self.expr_taint(v, fn)
                    if not t:
                        continue
                    if not t <= cn.get(p, set()):
                        cn.setdefault(p, set()).update(t)
                        self._newly_tainted_callees.append(callee)
                    c = self._container_taint(v, fn)
                    if c and not c <= cc.get(p, set()):
                        cc.setdefault(p, set()).update(c)
                        self._newly_tainted_callees.append(callee)
        # two signals for two kinds of reader (fork PR 781): a nested def reads this function's locals (tainted_names,
        # carried_names, through its scope chain) and a caller reads its returns (ret_taint, ret_whole, at the call);
        # _taint re-visits each kind on its own signal
        return (names != before or carried != before_carried,
                self.ret_taint.get(fn, {}) != before_ret or self.ret_whole.get(fn, {}) != before_whole)

    def _return_taint(self, expr, fn):
        """What a return CARRIES across its boundary (its carried set), less the pick tag when the return is a dict (the
        census does not follow the pick tag across a dict return: ruling 3 of review round 6)."""
        if self._dict_valued(expr, fn):
            return self._container_taint(expr, fn) & self.ENV_ONLY
        return self._container_taint(expr, fn)

    def _return_whole(self, expr, fn):
        """The returned value WHOLE: for a dict, every tag its values carry (the env under its own key included), less the
        pick tag by the same bound; for anything else the same as _return_taint."""
        if self._dict_valued(expr, fn):
            return self.expr_taint(expr, fn) & self.ENV_ONLY
        return self.expr_taint(expr, fn)

    def _keyed_read(self, node):
        """(receiver, key) for `x.get("k")`, `x.pop("k"[, d])`, `x.setdefault("k", v)` with a constant key, else None."""
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in self.KEY_READS \
                and node.args and isinstance(node.args[0], ast.Constant):
            return (node.func.value, node.args[0].value)
        return None

    def _keyed_taint(self, x, fn):
        """What a read of ONE non-source key of `x` yields: a local's or parameter's carried set (its taint minus what
        sits under a source key of a dict; the whole set for a non-dict), a module name's stored set, an attribute's
        stored carried set, a call's carried return, the union over a conditional's or a BoolOp's values
        (`(launching or {}).get("mode")`); anything else whole (a key the census cannot see past)."""
        if isinstance(x, ast.BoolOp):
            out = set()
            for v in x.values:
                out |= self._keyed_taint(v, fn)
            return out
        if isinstance(x, ast.IfExp):
            return self._keyed_taint(x.body, fn) | self._keyed_taint(x.orelse, fn) | self.expr_taint(x.test, fn)
        if isinstance(x, ast.Name):
            for s in self.scope_chain(fn):
                cn = self.carried_names.get(s, {})
                if x.id in cn:
                    return set(cn[x.id])
                if self._scope_binds(s, x.id):
                    return set()
            gt = self._global_read(fn, x.id)
            return set(gt) if gt else set()
        if isinstance(x, ast.Attribute) and isinstance(x.ctx, ast.Load):
            return set(self.attr_taint.get(x.attr, set()))
        if isinstance(x, ast.Call):
            res = self.callees.get(id(x), [])
            if res:
                out = set()
                for callee, _via in res:
                    if (callee.base, callee.qual) in self.sources["opaque_returns"]:
                        continue
                    for v in self.ret_taint.get(callee, {}).values():
                        out |= v
                return out
        return self.expr_taint(x, fn)

    def _roots(self, expr, fn, depth=0, seen=None):
        """The ROOTS a value derives from: the Names, attribute chains (`self.x`, `sess.env_vars`) and constant-keyed
        subscripts (`raw["vars"]`, `t[0]`) at its leaves, a local followed to its own assignments (`e = raw["vars"]`
        roots e in raw["vars"]; `t = (e,)` roots t[0] in e; a `self.<attr>` in what __init__ or any method stores there), a
        walrus rooting its target too; through a comprehension's iterables (its own targets excluded), a call's receiver
        and arguments, an operator's operands, a conditional's two values, a container's elements. Not through a
        condition, a comparison or a lambda (they select or judge a value, they do not supply it), and not to a subscript's
        or attribute's base (raw in raw["vars"] is the parameter, whose other keys are not the env; sess in
        sess.env_vars is the session)."""
        seen = seen if seen is not None else set()
        out = []
        if depth > 6 or expr is None:
            return out
        if isinstance(expr, tuple):
            return self._roots(expr[1], fn, depth + 1, seen)

        def follow_name(name, scope_fn):
            for s in self.scope_chain(scope_fn):
                sts = list(self._assigns_name(s, name))
                if sts:
                    for st in sts:
                        k = ("assign", id(st), name)
                        if k in seen:
                            continue
                        seen.add(k)
                        out.extend(self._roots(self._value_for(st, name), s, depth + 1, seen))
                    return
                if name in s.all_params():
                    return

        if isinstance(expr, ast.Name):
            out.append(expr)
            follow_name(expr.id, fn)
            return out
        if isinstance(expr, ast.Attribute):
            # the chain is the root (self._launched_env, sess.env_vars); its stores are not followed backward (the value
            # stored on `self._launched_env` was read from a dict holding the env under its key, and that dict is not the
            # env: the first draft of this walk marked `_launching` an env attribute that way and every keyed reader of
            # it with the env) and its base is not a root, except that a LOCAL base built by a constructor or a factory
            # the census cannot resolve (`p = _Pair(e, e)`, a namedtuple; `b = _Box(e, e)`) holds its arguments, so the
            # field read `p.left` roots in them
            out.append(expr)
            if isinstance(expr.value, ast.Name):
                for s in self.scope_chain(fn):
                    sts = list(self._assigns_name(s, expr.value.id))
                    if sts:
                        for st in sts:
                            v = self._value_for(st, expr.value.id)
                            if not isinstance(v, ast.Call):
                                continue
                            k = ("ctor", id(v))
                            if k in seen:
                                continue
                            seen.add(k)
                            res = self.callees.get(id(v), [])
                            if not res or all(via == "self" and c.name == "__init__" for c, via in res):
                                for a in v.args:
                                    out.extend(self._roots(a, s, depth + 1, seen))
                                for kw in v.keywords:
                                    out.extend(self._roots(kw.value, s, depth + 1, seen))
                        break
                    if expr.value.id in s.all_params():
                        break
            return out
        if isinstance(expr, ast.Subscript):
            if not isinstance(expr.slice, ast.Constant):
                return self._roots(expr.value, fn, depth + 1, seen)
            out.append(expr)
            base, key = expr.value, expr.slice.value
            if isinstance(base, ast.Name):
                for s in self.scope_chain(fn):
                    sts = list(self._assigns_name(s, base.id))
                    if sts:
                        for st in sts:
                            k = ("assign", id(st), base.id, key)
                            if k in seen:
                                continue
                            seen.add(k)
                            v = self._value_for(st, base.id)
                            if isinstance(v, (ast.Tuple, ast.List)):
                                if isinstance(key, int) and 0 <= key < len(v.elts):
                                    out.extend(self._roots(v.elts[key], s, depth + 1, seen))
                            elif isinstance(v, ast.Dict):
                                for kk, vv in zip(v.keys, v.values):
                                    if isinstance(kk, ast.Constant) and kk.value == key:
                                        out.extend(self._roots(vv, s, depth + 1, seen))
                            elif v is not None:
                                out.extend(self._roots(v, s, depth + 1, seen))
                        break
                    if base.id in s.all_params():
                        break
            return out
        if isinstance(expr, ast.NamedExpr):
            out.append(expr.target)
            out.extend(self._roots(expr.value, fn, depth + 1, seen))
            return out
        if isinstance(expr, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            bound = {leaf.id for g in expr.generators for leaf in self._leaves(g.target) if isinstance(leaf, ast.Name)}
            for g in expr.generators:
                out.extend(self._roots(g.iter, fn, depth + 1, seen))
            parts = [expr.key, expr.value] if isinstance(expr, ast.DictComp) else [expr.elt]
            for p in parts:
                out.extend(r for r in self._roots(p, fn, depth + 1, seen) if not (isinstance(r, ast.Name) and r.id in bound))
            return out
        if isinstance(expr, ast.IfExp):
            return self._roots(expr.body, fn, depth + 1, seen) + self._roots(expr.orelse, fn, depth + 1, seen)
        if isinstance(expr, ast.BoolOp):
            for v in expr.values:
                out.extend(self._roots(v, fn, depth + 1, seen))
            return out
        if isinstance(expr, ast.Call):
            if self.callees.get(id(expr)):
                # a call into a function of the files: its result is the callee's RETURN, analysed forward from its
                # parameters, and its arguments and receiver are not the value (`self.backend._launch_shape(self)` is
                # neither the backend nor the session); a value copied through such a helper under the source key is
                # therefore not followed back to the helper's argument (a bound of this walk, stated in the docstring)
                return out
            if isinstance(expr.func, ast.Attribute):
                out.extend(self._roots(expr.func.value, fn, depth + 1, seen))      # e.items(), e.copy(), os.environ.copy()
            for a in expr.args:
                out.extend(self._roots(a, fn, depth + 1, seen))                    # dict(e), sorted(e), copy.deepcopy(e)
            for kw in expr.keywords:
                out.extend(self._roots(kw.value, fn, depth + 1, seen))
            return out
        if isinstance(expr, ast.Dict):
            for k, v in zip(expr.keys, expr.values):
                if k is not None:
                    out.extend(self._roots(k, fn, depth + 1, seen))
                out.extend(self._roots(v, fn, depth + 1, seen))
            return out
        if isinstance(expr, (ast.Tuple, ast.List, ast.Set)):
            for el in expr.elts:
                out.extend(self._roots(el, fn, depth + 1, seen))
            return out
        if isinstance(expr, (ast.Starred, ast.Await, ast.FormattedValue, ast.UnaryOp)):
            return self._roots(getattr(expr, "value", None) or getattr(expr, "operand", None), fn, depth + 1, seen)
        if isinstance(expr, ast.JoinedStr):
            for v in expr.values:
                out.extend(self._roots(v, fn, depth + 1, seen))
            return out
        if isinstance(expr, ast.BinOp):
            return self._roots(expr.left, fn, depth + 1, seen) + self._roots(expr.right, fn, depth + 1, seen)
        return out

    @staticmethod
    def _shape(node):
        """A hashable key for a root's SHAPE, context ignored, so a second spelling of the same access matches it:
        Name -> its id; an attribute chain -> its base's shape and the attribute; a constant-keyed subscript -> its
        base's shape and the key; anything else -> its unparsed text."""
        if isinstance(node, ast.Name):
            return ("name", node.id)
        if isinstance(node, ast.Attribute):
            return ("attr", Census._shape(node.value), node.attr)
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            return ("sub", Census._shape(node.value), repr(node.slice.value))
        return ("other", ast.unparse(node))

    def _declare_roots(self, fn, decl):
        """Once per declared dict source: the roots of every value it stores under a source key (_roots), split into
        the Names to taint in the function (a local, a parameter; a module-level name is matched structurally instead,
        since a constant that filters the env is not the env), the attributes to taint for every reader (a chain not
        rooted in an imported module: os.environ is nobody's per-session state) and the holders to taint whole; every
        other root (a constant-keyed subscript, a chain rooted in a module) is matched by SHAPE over the function's
        body, nested defs and lambdas included, and each matching node reads as a source (_decl_node_tags)."""
        hit = self._decl_roots.get(fn)
        if hit is not None:
            return hit
        mod = self.mod_of(fn)
        name_roots, attr_roots, holders, shapes = {}, {}, [], set()
        for holder, value in self._source_key_stores(fn):
            v = value.value if isinstance(value, ast.Starred) else value
            for r in self._roots(v, fn):
                if isinstance(r, ast.Name):
                    local = any(r.id in s.all_params() or r.id in s.assigned() for s in self.scope_chain(fn))
                    if local:
                        name_roots.setdefault(r.id, r)
                    else:
                        shapes.add(self._shape(r))
                elif isinstance(r, ast.Attribute):
                    base = r
                    while isinstance(base, ast.Attribute):
                        base = base.value
                    if isinstance(base, ast.Name) and base.id in mod.imports:
                        shapes.add(self._shape(r))
                    else:
                        attr_roots.setdefault(r.attr, r)
                        shapes.add(self._shape(r))
                else:
                    shapes.add(self._shape(r))
            if isinstance(holder, ast.Name):
                holders.append(holder.id)
            elif isinstance(holder, ast.Attribute):
                attr_roots.setdefault(holder.attr, holder)
        if shapes:
            for node in ast.walk(fn.node):
                if isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)) and isinstance(getattr(node, "ctx", None), ast.Load) \
                        and self._shape(node) in shapes:
                    self._decl_node_tags[id(node)] = decl
        hit = self._decl_roots[fn] = (list(name_roots.values()), list(attr_roots.values()), holders)
        return hit

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
        if isinstance(value, ast.Name):
            # a name's CARRIED set, whatever it holds (for a non-dict the same as its whole set: _store gives a local
            # both, a loop or with target both, a call site gives a parameter both); a module-level name's stored set
            return self._keyed_taint(value, fn)
        if isinstance(value, ast.Attribute) and isinstance(value.ctx, ast.Load):
            return set(self.attr_taint.get(value.attr, set()))     # the attribute's carried set, never its whole set
        if isinstance(value, tuple):        # ("index", call, i): a tuple-unpacked position of a call's return
            _k, call, i = value
            res = self.callees.get(id(call), []) if isinstance(call, ast.Call) else []
            if res:
                out = set()
                for callee, _via in res:
                    rt = self.ret_taint.get(callee, {})
                    out |= rt.get(i, set()) | rt.get("all", set())
                return out
            return self.expr_taint(value, fn)
        if isinstance(value, ast.Call):
            res = self.callees.get(id(value), [])
            if res:
                # a call's CARRIED return: what crosses the callee's dict boundary, plus a non-dict source function's tag
                # whole (a list of names crosses whole); a dict source's tag sits under its key and does not cross
                out = set()
                for callee, _via in res:
                    if (callee.base, callee.qual) in self.sources["opaque_returns"]:
                        continue
                    for v in self.ret_taint.get(callee, {}).values():
                        out |= v
                    tag = self.sources["func"].get((callee.base, callee.qual))
                    if tag and not self._returns_dicts(callee):
                        out.add(tag)
                return out
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
        if isinstance(expr, ast.Call):
            # a call whose every callee returns dicts (the launch shape held in a local): what crosses from the local
            # is the call's carried return, and a whole-value use of it reads the return whole
            res = self.callees.get(id(expr), [])
            return bool(res) and all(self._returns_dicts(c) for c, _via in res)
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

    def _store(self, fn, mod, names, carried, target, tags, ctags, dict_value=False):
        """`tags` flow into `target` (a Name, a `<x>.<attr>`, a subscript, a starred name): a local of fn takes them
        (its carried set takes `ctags`, what crosses a dict boundary); a module-level name (declared global, or a module
        list mutated in place) takes them for every reader in the module; an attribute takes `ctags` for every reader
        of `.<attr>` in the three files, and `tags` as its WHOLE set only when the value stored is a dict by shape
        (`dict_value`: a literal, dict(...), a call to a function returning dicts, a local built as one) or the store is
        under a source key: attributes are keyed by NAME over every receiver, so a scalar attribute (`mode`) given the
        whole set of an over-approximated local would hand the env to every reader of that name in the files (the
        first draft of the whole set did, and read 95 content rows at the head). A subscript store under a constant
        SOURCE key ('env') marks the container whole (a whole-value use reads it) but not its carried set (the read of
        that key is a source of its own)."""
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
            attr = root.attr
            t0 = target.value if isinstance(target, ast.Starred) else target
            if attr == "__dict__" and isinstance(t0, ast.Subscript) and t0.value is root:
                # `x.__dict__["n"] = v`: an attribute store by reflection, followed by the spelled name; a computed name
                # the census cannot place is a failure when the value is tainted
                if isinstance(t0.slice, ast.Constant) and isinstance(t0.slice.value, str):
                    attr = t0.slice.value
                else:
                    self._fail("reflection-store", fn.base, t0.lineno, "a tainted value is stored through %s, a name the census "
                               "cannot place" % ast.unparse(t0)[:60])
                    return False
            return self._mark_attr(attr, set() if src_key else ctags, tags if (src_key or dict_value) else None)
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

    def _mark_attr(self, attr, tags, whole=None):
        """`tags` is what a keyed read of `<x>.<attr>` yields (attr_taint), `whole` what the attribute read whole yields
        (attr_whole; the same set when not given)."""
        if attr == self.RING_ATTR:
            return False          # the ring is the sink; what its rows carry is the population itself, not a source
        grew = False
        cur = self.attr_taint.get(attr, set())
        if tags and not tags <= cur:
            self.attr_taint[attr] = cur | tags
            grew = True
        w = tags if whole is None else whole
        curw = self.attr_whole.get(attr, set())
        if w and not w <= curw:
            self.attr_whole[attr] = curw | w
            grew = True
        if grew:
            self._grown_attrs.add(attr)
        return grew

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
            for callee, via in self.callees.get(id(expr), []):
                k = ("call", callee.qual)
                if k in seen:
                    continue
                got = set()
                for r in callee.returns:
                    got |= self.reduce(r, callee, depth + 1, seen | {k})
                # a return that is (a wrap of) the callee's OWN parameter is the argument this call passed, read in the
                # caller (problem_row's returned line opens with its prose: the post-merge census of the env-pick door,
                # 2026-09-20, where the refused-launch rows' message is that line)
                bound = None
                for r in list(got):
                    if r[0] == "param" and r[2] == callee.qual:
                        bound = self.bind_args(expr, callee, via) if bound is None else bound
                        if r[1] in bound:
                            got.discard(r)
                            got |= self.reduce(bound[r[1]], fn, depth + 1, seen | {k})
                out |= got
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
            if dc.key is not None and not isinstance(dc.key, tuple):
                tags |= self.expr_taint(dc.key, dc.fn if dc.key is not (dc.via.key if dc.via else None) else dc.via.fn)
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
        # a conduit's inner call is judged at each of its SITES (rule 3): its own keyword is the forwarded parameter
        # (problem_row's bool(ring)) or a fallback that passes none (problem_row's plainer-callable road), and each site
        # carries every inner road as an alternative, so a tainted site through a conduit that keeps such a fallback is
        # a violation whatever it declares, and the inner call's own row would say the same thing twice (the post-merge
        # census of the env-pick door, 2026-09-20: the first tainted problem_row sites flagged the inner calls too)
        inner_calls = {id(inner) for lst in self.conduits.values() for inner, _p in lst}
        for dc in self.tainted:
            if id(dc) in inner_calls:
                # narrowed (round 7, kernel-1): skipped only when its taint is wholly its sites' (the residual, with the
                # conduit's parameters clean and its locals re-propagated, is empty); a fold of the conduit's own into
                # the message, the ring text or the key keeps this row in the check, judged on its own declaration
                dc.residual = frozenset(self.residual_taint(dc))
                if not dc.residual:
                    continue
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

    # ------------------------------------------------------------------ residual taint (round 7, kernel-1)
    RESIDUAL_DEPTH = 6

    def residual_taint(self, inner):
        """The taint a conduit's inner door call carries that its SITES do not: its message's, ring text's and key's
        taint recomputed with the conduit's own parameters reading as clean and re-propagated through the conduit's
        locals (a flow-insensitive fixpoint over its assignments, loops, with-items and in-place adds) and through the
        returns of the helpers those locals are assigned from, each helper read the same way with ITS parameters clean
        (problem_row's `line` is str(prose) + a mark + json.dumps(row), `row` the return of append_session_event over
        the same parameters: with the parameters clean and the helper's return recomputed, the residual is empty, and
        the inner call is judged at its sites; with the parameters clean and the helper's return read from the
        context-insensitive pass, `row` carries the env every caller ever passed and the clean head reds). A source
        read in the conduit's body (a source name, an attribute source on any receiver, a source function's call), an
        attribute read's stored taint, a module name's stored taint and an enclosing scope's taint all count; a call
        the walk cannot resolve is walked into; a helper deeper than RESIDUAL_DEPTH, or one in a recursion, reads as
        its whole return from the main pass, the over-approximating side."""
        fn = inner.fn
        names = self._residual_names(fn, 0)
        tags = set()
        for e in (inner.message, inner.ring_text, inner.key):
            if e is not None and not isinstance(e, tuple):
                tags |= self._residual_expr(e, fn, names, 0)
        return tags

    def _residual_names(self, fn, depth):
        """{local: tags} over fn's own body with fn's parameters clean (residual_taint says how)."""
        names = {}

        def store(target, tags):
            grew = False
            for leaf in Census._leaves(target):
                if isinstance(leaf, ast.Starred):
                    leaf = leaf.value
                if isinstance(leaf, ast.Name) and tags and not tags <= names.get(leaf.id, set()):
                    names.setdefault(leaf.id, set()).update(tags)
                    grew = True
            return grew
        for _ in range(6):
            grew = False
            for st in fn.assigns:
                if st.value is None:
                    continue
                vt = self._residual_expr(st.value, fn, names, depth)
                if not vt:
                    continue
                for t in (st.targets if isinstance(st, ast.Assign) else [st.target]):
                    grew |= store(t, vt)
            for node in fn.loops():
                if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                    grew |= store(node.target, self._residual_expr(node.iter, fn, names, depth))
                elif isinstance(node, (ast.With, ast.AsyncWith)):
                    for item in node.items:
                        if item.optional_vars is not None:
                            grew |= store(item.optional_vars, self._residual_expr(item.context_expr, fn, names, depth))
            for call in fn.calls:
                f = call.func
                if isinstance(f, ast.Attribute) and f.attr in self.MUTATING_METHODS:
                    vt = set()
                    for a in list(call.args) + [k.value for k in call.keywords]:
                        vt |= self._residual_expr(a, fn, names, depth)
                    grew |= store(f.value, vt)
            if not grew:
                break
        return names

    def _residual_return(self, callee, depth):
        """What `callee` returns with ITS parameters clean, by the same walk; past RESIDUAL_DEPTH or inside a recursion,
        its whole return from the main pass."""
        if depth > self.RESIDUAL_DEPTH or callee in self._residual_stack:
            out = set()
            for v in self.ret_whole.get(callee, {}).values():
                out |= v
            return out
        hit = self._residual_returns.get(callee)
        if hit is not None:
            return hit
        self._residual_stack.add(callee)
        try:
            names = self._residual_names(callee, depth)
            tags = set()
            for r in callee.returns:
                if r is not None:
                    tags |= self._residual_expr(r, callee, names, depth)
            decl = self._declared_dict_source(callee)
            if decl:
                tags.add(decl)
        finally:
            self._residual_stack.discard(callee)
        self._residual_returns[callee] = tags
        return tags

    def _residual_expr(self, expr, fn, names, depth):
        """expr_taint with fn's parameters clean: a parameter Name yields nothing, a local its residual, everything else
        what the main pass gives it (a source read, a stored attribute, a module name, an enclosing scope), a resolved
        call its callee's residual return plus its arguments' residual (the safe side: an argument's fold reaches the
        return whether or not the callee keeps it)."""
        tags = set()
        stack = [expr]
        params = fn.all_params()
        while stack:
            node = stack.pop()
            if node is None or isinstance(node, tuple):
                continue
            tag = self._source_tag(node, fn)
            if tag:
                tags.add(tag)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id in params:
                    continue
                if node.id in names:
                    tags |= names[node.id]
                    continue
                if node.id in fn.assigned():
                    continue
                found = False
                for s in self.scope_chain(fn)[1:]:
                    tn = self.tainted_names.get(s)
                    if tn and node.id in tn:
                        tags |= tn[node.id]
                        found = True
                        break
                    if self._scope_binds(s, node.id):
                        found = True
                        break
                if not found:
                    gt = self._global_read(fn, node.id)
                    if gt:
                        tags |= gt
                continue
            if isinstance(node, ast.Compare) and all(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops) \
                    and all(isinstance(cmp, ast.Constant) and cmp.value is None for cmp in node.comparators):
                continue
            ra = self._reflected_attr(node)
            if ra is not None:
                tags |= self.attr_taint.get(ra[1], set()) | self.attr_whole.get(ra[1], set())
                stack.append(ra[0])
                stack.extend(ra[2])
                continue
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                tags |= self.attr_taint.get(node.attr, set()) | self.attr_whole.get(node.attr, set())
            if isinstance(node, ast.Call):
                res = self.callees.get(id(node), [])
                if res:
                    for callee, _via in res:
                        if (callee.base, callee.qual) in self.sources["opaque_returns"]:
                            continue
                        tags |= self._residual_return(callee, depth + 1)
                stack.extend(node.args)
                stack.extend(k.value for k in node.keywords)
                if not res:
                    stack.append(node.func)
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            stack.extend(ast.iter_child_nodes(node))
        return tags

    # ------------------------------------------------------------------ bound site arguments (round 7, tests-2, extra7-1)
    def bound_site_args(self, fn, constants=()):
        """Every call reaching the def `fn` (a Fn, or its qualified name in one of the files), its arguments bound against
        the def's signature the way the conduit walk binds them (bind_args: a positional by index, a keyword by name, a
        receiver's self dropped, a parameter left unsaid reading its default), as [(caller Fn, call node, {parameter:
        argument node})]; beside them the FAILURE rows (kind, file, line, text) for a site the signature cannot read: a
        starred argument or a ** mapping, whose parameters the walk cannot place, and, for each parameter named in
        `constants`, an argument that is not an ast.Constant (a name, a call, an expression), whose road the census cannot
        tell from the text. Both are REFUSED, never read as absent (round 7 of the env-pick door's review, 2026-09-20,
        tests-2 and extra7-1: the pin naming the conduit's problem=True callers read n.keywords alone, so a caller passing
        problem positionally counted as saying nothing and the roster it holds the declaration to went stale with every
        test green); an unverifiable value goes to the restricted side, never to False. A site whose bound argument is
        the parameter's own default said nothing of it."""
        if isinstance(fn, str):
            hits = [f for f in self.all_fns if f.qual == fn]
            if len(hits) != 1:
                raise CensusError("%d defs named %s in the files" % (len(hits), fn))
            fn = hits[0]
        rows, failures = [], []
        for call, caller, via in self.callers.get(fn, []):
            starred = [a for a in call.args if isinstance(a, ast.Starred)] + [k for k in call.keywords if k.arg is None]
            if starred:
                failures.append(("site-unbound", caller.base, call.lineno, "%s at %s passes %s, which the signature cannot place; "
                                 "the site is refused, not read" % (fn.qual, caller.qual, ", ".join(ast.unparse(x) for x in starred))))
                continue
            b = self.bind_args(call, fn, via)
            for name in constants:
                v = b.get(name)
                if v is not None and not isinstance(v, ast.Constant):
                    failures.append(("site-argument-unread", caller.base, call.lineno, "%s= at %s is the expression %s, not a "
                                     "constant: the road is unread and the site refused, never counted as False"
                                     % (name, caller.qual, ast.unparse(v)[:60])))
            rows.append((caller, call, b))
        return rows, failures

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
        out["inner_residuals"] = [(dc.base, dc.lineno, dc.owner, sorted(dc.residual)) for dc in
                                  sorted(self.tainted, key=lambda d: (d.base, d.lineno)) if dc.residual]
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


# The Census cache of the `census()` door: (realpaths, id(sources)) -> Census, under the retention rule of ASTS above
# (a Census holds its trees through its Mods, so a kept Census over a foreign path would keep that path's tree too).
_CENSUS = {}


def census(files=None, sources=None):
    """The census over `files` (the three kernel modules by default), computed once per process per file set when
    every file is a canonical input (retained_paths); a set with any other file is computed for the call."""
    files = tuple(os.path.realpath(f) for f in (files or DEFAULT_FILES))
    key = (files, id(sources) if sources is not None else 0)
    hit = _CENSUS.get(key)
    if hit is None:
        hit = Census(files, sources or DEFAULT_SOURCES)
        if set(files) <= retained_paths():
            _CENSUS[key] = hit
    return hit


def main(argv):
    import time
    files = argv[1:] or list(DEFAULT_FILES)
    t0 = time.time()
    for f in files:   # a file outside retained_paths() is parsed again by the construction, so `census` includes it
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
