#!/usr/bin/env python3
"""Every lab kernel a test starts as a PROCESS is hermetic about the postal bus (2026-09-10): its environment carries
ROMP_POSTAL_CLIENT_ONLY=1 (the kernel's boot-time ensure then starts no bus) and its own ROMP_POSTAL_PORT (an ephemeral
port, never the machine's fixed one) and ROMP_POSTAL_PEERS=0, the trio tests/test_ship_reship_served.py kernel_env gives.

Why a guard: one served test built its kernel environment by hand without the trio. Its kernel ran the postal
service's `ensure`, which starts the bus detached (its own session, so the kernel's death never reaches it) on the
FIXED port whenever nothing listens there. During a kernel restart the machine's real bus was down for a moment, the
lab bus took the port, the test's teardown killed the kernel and not the bus, and every session's mail then failed
against the lab's token until someone found the process.

The later leaks of that day came by a shape no spawn scan can see: a test module that loads the kernel module
IN-PROCESS (load_source of bin/romp-kernel, no subprocess at all) makes a bus call that is refused, and the kernel's
revive path runs `ensure` from inside the test process, with the test's environment and no trio. Three sites, one
afternoon: tests/test_federation_missing_served.py (a lab kernel started as a process, its environment built by hand),
tests/test_kernel_tunnels.py (an in-process kernel, an attach whose bus call was refused) and tests/test_kernel.py's
PostalPeerTunnels.test_notify_bus_peer_is_guarded (an in-process kernel, a peer notify forced to fail). So the rule
here scans every process spawn whose argv names the kernel (Popen, run, check_output, check_call, call; the argument
span read across lines, whatever spells the path, a path held in a name included), and the in-process shape is met in
the bus itself: `romp-postal-service serve` and `ensure` refuse the fixed port under a test (PYTEST_CURRENT_TEST set, or the
state root under a temporary directory) unless ROMP_POSTAL_PORT names the port as the run's own (ROMP_POSTAL_HERMETIC beside
it, as the runner, the shell suite's setup and kernel_env set; an inherited name does not count), pinned by
tests/test_postal_fixed_port_belt.py.
A module that loads the kernel in-process and exercises the bus still carries the trio, each leg where it is read: the
port before the load (the kernel reads it at import), client-only before the load, and peers PER TEST, set in the setUp
of every class that attaches or detaches and put back by a cleanup that setUp registers (the tunnel tests), or all
three around the one call that provokes the revive, held until that revive has ended (the peer-notify test). Peers is
never set at import: the kernel reads it at call time, and under xdist every worker imports every collected module
before it runs a test, so the "0" the tunnel tests once wrote at module level reached every module on every worker,
and the remote-identity absorb case (a bus notice gated on peers) was red in 5 of 6 full runs (diagnosed 2026-09-18).
The placement test below reads the module's assignments by position (a fault list, run over the real module and over
synthetic copies with the leak planted, so it is known to be able to fail), the import-time half of the rule is held
for EVERY module under tests/, walked recursively, fixtures/ included (941 files on 2026-09-18): no module-level write
of the variable, module-level if/try/for/with bodies included, in each shape the scan reads (a subscript assignment,
setdefault, update of a literal or of a module-level name bound to one, |=, os.putenv, through os.environ or a name
a plain assignment binds to it (`env = os.environ`, the one target a name); review round 2, 2026-09-18, after the
subscript and setdefault alone left a module-level update invisible; the dunder spellings __setitem__ and __ior__,
called on the mapping or unbound with the mapping as the first argument, and os.environb with a bytes key, since the
third commit of 2026-09-22, when the verifier found those three passing silently; an augmented assignment to a key
and a key bound as a for, comprehension or with target since round 2 of fork PR #894; the shapes it does not read
are listed above _Module, each with a plant), and a write whose keys the scan cannot read fails the test rather than
passing unread. The probe beside them imports the module in a fresh interpreter and runs one setUp, and one that
fails, to see the value. The restore is a cleanup rather than a tearDown since review round 1 (2026-09-18): unittest
skips tearDown when a subclass's setUp raises after the base's returned, and a tearDown restore left the 0 in the
worker on that path.

Since 2026-09-22 (the reviewer's ruling on fork PR #813's finding) the import-time rule covers EVERY environment name,
not peers alone, and no leg of the trio is written at module level in the tunnels module any more: a module-level
write executes at collection and holds for every test in the process and for every child any test spawns, whether or
not the writing module's tests run. A real bus started from the peer-notify guard test in tests/test_kernel.py with
the environment of the test process at the moment its revive thread spawned the child: the guard's own trio had
already been restored (the thread raced the restore, and the restore won), so the child read the tunnels module's
module-level port (the run's own, with conftest's marker beside it, which is what licensed the bind under a test) and
its module-level client-only (inert with peers on), and the sessions-file seam a third module wrote at module level,
whose one row kept the bus from ever autostopping; it wrote into a shared state root every 30 s and turned another
module's snapshot test red in the 3.10 CI cell. The port and client-only join peers in _PostalTrio.setUp (the kernel's
BUS_PORT, read at import, patched beside them and restored by the same cleanups), conftest pops the bus port before
every test, the seam moves per test in the ten postal modules that wrote it at import, and the repo-wide pin holds the
set of names the test modules write at module level EQUAL to a licensed set (LICENSED_MODULE_LEVEL_WRITES: each name
with a checked condition, a temporary licence dated and pointed at the item it waits on), never a floor. Under this
kernel the guard test's refused notify kicks the revive on EVERY run, and the test holds that revive inside itself
(the reviewer's re-ruling of round 2 on fork PR #894): its trio stays around the call, the revive is rebound to a
wrapper that sets an Event in a finally, the restore waits on that Event, and for the whole window subprocess.run is a
scoped fake that records and answers any call whose argv names romp-postal-service and passes every other call, from
any thread, to the real run; its one assertion on the fake is that no postal-service call reached the real run. Why:
with the test at its base text (round 2's first commit) the restore won the race in every run, and the ensure's
child, forked with the restored environment, which names no port, pinged the machine's fixed bus port, so on a box
whose own bus listens there a plain run reached that bus; the bus's fixed-port refusal
(tests/test_postal_fixed_port_belt.py) stops a bind, not that ping. The round-1 rewrite asserted that the refused
notify runs the ensure once, the opposite of upstream's fix (their PR 1848 returns before the ensure under
client-only; fork PR #875 folds it with the skip gated on the kernel having ensured no bus of its own), and the
reviewer's ruling of round 1 removed that assertion: the test asserts nothing about whether the revive runs the
ensure, so it holds under this kernel, upstream's and fork PR #875's. Its text conflicts with fork PR #875's copy of
the test, and whichever of the two lands second keeps fork PR #875's assertion beside this wait and fake. The pins
below read the test's parts as statements that run (the trio, the wrap and the fake set before the call; the wait
before the fake and the environment are put back; none after a return, a raise, a skip or an exit, none in the body of a
try with an except clause), hold every other statement of the test to putting back none of what those set, in any
binding form or by reflection named in any reference form, hold each name those parts are read by to one value,
bound once and read only where they read it, and hold the window, from the first of the revive's rebind and the fake's
install to the wait, to those parts alone (a plant test reds each rule, each binding form, each read half and each
identifier of reflection or of the environment on a plant of its own), run its fake's own def over the argv shapes it must
tell apart, and run the test in a child pytest with a sitecustomize that records every connect and every Python
process of the run: none dials the fixed port, and no ensure child starts.
The census pin passes one floor write of a leak name, upstream's client-only "1" (FLOOR_LEAK_WRITES), and the tunnels
probe compares client-only with the value the floor modules left. `python -m tests.test_hermetic_kernel_postal
--census` prints the counts by name and shape (fork PR #871's by-product figures, derived by ast), with the parsed
module count, a total line per name and the split between test_*.py files and the others; the census parses each file
itself, once per run of this module, keeps the trees of the files its resolver may read and drops each other tree after
its walk, and derives once per path tuple, what it keeps held by one object the module releases in its tearDownModule,
and the module changes no collector state (the reviewer's rulings of
2026-09-24 on round 2 of fork PR #894: parse_cache.derived() freezes the heap, and every perf-snapshot reader after this
module in CI's serial order then pays per read; the census's own parse rather than parse_cache's shared one, by the
measurement module_level_env_census's docstring gives); that docstring also says which of its figures are compared and
which are not (the reviewer's ruling of round 1 on fork PR #894). Beside it,
tests/conftest.py's run-end process check makes a run red that leaves any process holding its temp root
(tests/test_run_end_leaked_processes.py). Every kernel a module loads in-process gets a dead BUS_PORT for each test,
and every postal service loaded in-process a dead client BASE (conftest's _dead_bus_port: with ROMP_POSTAL_PORT popped,
each read the machine's fixed bus port at import and its bus calls reached the bus running there, the reviewer's ruling
of round 1 on fork PR #894), and the pin over BUS_DIALLING_MODULES runs the modules whose calls dialled it together in
both orders under a connect and spawn spy.
The fixup of the same day (the verifier's findings on this PR) made "module level" mean everything that EXECUTES AT
IMPORT: the class bodies (a write planted in one had left the pin green), the header parts of a def, class or block
statement (decorators, default argument values, bases, an if test, the with items) and the writes reached through a
call at import the scan can resolve to a def or class under tests/ (a module-local helper, a name imported from a
tests-local module, a bare decorator, an instantiation; two such calls exist today, both to
test_asm_checkpoint.kernel_module(), whose setdefault of the browser switch is licensed; since round 2 of fork PR #894
a def in any import-time block or class body, every binding of a name, a re-export, a metaclass's hooks and a base's
__init_subclass__, the mapping passed into a parameter of such a def (not a lambda's, nor one of a def or class bound
inside a function), and a bare name read as a call only where Python calls it),
with what stays outside the scan named above _Module; and every licence carries a checkable value condition (a value written through a name is read
through the name) and every temporary licence a since date, held by _licence_table_faults. The third commit of the same
day closes the second verification's findings: the call resolver reads a dotted `import tests.helper` and a star import,
the temp-root licences accept a bare mkdtemp (or one with a literal prefix) and nothing with a `dir=`, and the comment
above _Module names what stays outside the scan after that.

The fixture rule below is static, so it holds for tests that skip here (no browser, no extension deps) and fails at
the spawn site, naming the file.
"""
import ast
import collections
import gc
import glob
import importlib.util
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
import weakref

HERE = os.path.dirname(os.path.realpath(__file__))
if __package__:                        # under pytest tests/ is a package: THE SAME parse_cache module object every census in
    from . import parse_cache as PC    # the process shares; this module reads its singleton check alone, neither its parse
else:                                  # nor its derived() (module_level_env_census's docstring says why); as a script
    if HERE not in sys.path:           # (`python3 tests/test_hermetic_kernel_postal.py --census`) it imports the module by name
        sys.path.insert(0, HERE)
    import parse_cache as PC           # noqa: E402
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)

CALL = re.compile(r"(?:subprocess\.(?:Popen|run|check_output|check_call|call)|(?<![\w.])Popen)\s*\(")
# the kernel's path as an argv spells it: the script's name, the bare CLI (not the other bin/romp-* scripts), a path
# joined from BIN with "romp"
KERNEL_ARGV = re.compile(r"""romp-kernel|bin/romp(?![\w-])|\bBIN\b[^\]\n]*?["']romp["']""")
KERNEL_NAME = re.compile(r"^[ \t]*([A-Za-z_]\w*)\s*=\s*[^\n]*romp-kernel", re.M)   # a name bound to the kernel's path
TRIO = ("ROMP_POSTAL_PORT", "ROMP_POSTAL_PEERS", "ROMP_POSTAL_CLIENT_ONLY")


def _call_spans(src):
    """The argument span of every subprocess call in `src`, read across lines to the matching parenthesis."""
    for m in CALL.finditer(src):
        i = m.end(); depth = 1; j = i
        while j < len(src) and depth:   # loop-ok: a bounded scan of one call's argument span
            c = src[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            j += 1
        yield src[i:j]


def _spawns_kernel(src):
    names = [re.compile(r"\b%s\b" % re.escape(n)) for n in KERNEL_NAME.findall(src)]
    return any(KERNEL_ARGV.search(span) or any(n.search(span) for n in names) for span in _call_spans(src))


def _hermetic(src):
    return "kernel_env(" in src or all(k in src for k in TRIO)


class UnreadableEnvWrite(AssertionError):
    """A write to the process environment whose keys the scan cannot read from the source: an update of a computed
    mapping or of `**kw`, a key that is not a string literal. Raised rather than skipped (review round 2, 2026-09-18): a
    write the scan passed over would hold the repo-wide import-time rule vacuously for that module."""


def _literal_mapping(node):
    """{key: value node} for a dict literal, or for a `dict(...)` call of keywords alone; None for anything else (a
    computed mapping, a `**spread`, a key that is not a string literal). The values ride along since 2026-09-22: a
    licence on a module-level write can be a condition on the value written (the dead port is "1", the catalog is
    "off"), and the banner module writes its dead ports through a name bound to a dict literal."""
    if isinstance(node, ast.Dict):
        if all(isinstance(k, ast.Constant) and isinstance(k.value, (str, bytes)) for k in node.keys):
            return {_key_text(k.value): v for k, v in zip(node.keys, node.values)}
        return None
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict" and not node.args
            and all(kw.arg is not None for kw in node.keywords)):
        return {kw.arg: kw.value for kw in node.keywords}
    return None


def _key_text(k):
    """A key as os.environ spells it: a str as written; a bytes key (os.environb's) decoded the way environb decodes one."""
    return os.fsdecode(k) if isinstance(k, bytes) else k


def _literal_mapping_keys(node):
    """The string keys of a dict literal or of a `dict(...)` of keywords; None when _literal_mapping cannot read it."""
    m = _literal_mapping(node)
    return None if m is None else set(m)


_TYPE_ALIAS = getattr(ast, "TypeAlias", None)     # the `type X = ...` statement, 3.12 on; None where it does not parse


class _EnvNames:
    """What spells the process environment in a module, so a write is read whatever name it goes through (review round 2,
    2026-09-18; before it the scan read `os.environ[...]` and `os.environ.setdefault` alone, and a module-level
    `os.environ.update(...)` was invisible to it): `os.environ` under any name os is imported as, `environ` after
    `from os import environ` (or its `as` name) or after `from os import *` (since the verifier's finding on round 2 of
    fork PR #894: os.__all__ carries environ and environb, and a write through the star-imported name passed silently),
    and every name a plain assignment binds to it, the one target a name (`env = os.environ`; a name bound to it any
    other way, an annotated or a chained assignment among them, is [held-otherwise] above _Module); `os.environb`,
    the same environment keyed by bytes, the same way (the third commit of 2026-09-22); a parameter of the def a call
    at import resolves to (_resolve: a function, a method, or a class's __new__ or __init__) that the call passes the
    mapping to, or whose default is the mapping (_environ_params; round 2 of fork PR #894, the reviewer's ruling of
    round 1, where the parameter route was missed silently). A lambda's parameter is never one, whether the lambda
    defaults it to the mapping or is called with it: the lambda is read where it stands with every parameter
    unreadable, and the comment above _Module names that ([lambda-parameter], with its two plants). Nor is a parameter
    of a def or class bound inside a function, whether a call there passes it the mapping or its default is the mapping
    (`def _o(): def _i(env): env[K] = v; _i(os.environ)`): _resolve never resolves a call to a def or class bound inside
    a function, so the nested code is read where it stands as part of the function around it, every parameter unreadable,
    as a lambda is ([nested-def-parameter], with its plants; the verifier's finding on round 2's thirteenth commit of
    fork PR #894, where only the lambda was named). Beside those, the
    names bound to a dict literal or to `dict(...)` of keywords, which an `update(NAME)` reads through the name
    (tests/test_update_banner_confirm_served.py updates its DEAD_PORTS that way at import).
    THE RULE (the reviewer's ruling of round 1 on fork PR #894, where the first binding was read as the only one and a
    later mutation or rebinding left the census recording writes that did not happen and missing ones that did): a
    first binding is read and any later binding the module's own code spells invalidates it. A name bound again by a
    binding form (another assignment, an augmented or annotated one, a walrus, an import, a def, a class, a for or with
    target, an except name, a match capture, a `type` statement, a `global` declaration in any def, a parameter of the
    function being read) is unreadable in every table (`_rebound`), except that a for loop's own target keeps the loop's
    literals and a single-name assignment keeps its dict literal (the first binding of each); a star import at import
    time (`from helper import *`) binds names no text of the module spells, so it makes EVERY name bound at import
    unreadable in every table (the verifier's finding on round 2 of fork PR #894: a loop name or a dict a star import
    rebound was read through its first binding). A tracked dict is read ONLY through the allowed reads (_DICT_READS:
    an environment update's mapping argument, a ** spread, a for or comprehension iterable, a membership test, the one
    binding itself), which is what DEAD_PORTS does; any other reference to its name in any scope (a subscript store or
    delete, a mutating method, an augmented assignment, an alias, a use inside a def, a rebinding) makes it unreadable, so
    an update through it is loud (UnreadableEnvWrite naming the module and the line), since no list of mutations can
    enumerate aliasing. What the rule does not read: a binding or a mutation made through the module's namespace rather
    than spelled by name (`globals()["k"] = v`, `vars()["k"] = v`, `sys.modules[__name__].k = v`, setattr on the
    module, `vars()["D"][K] = v`, `sys.modules[__name__].D[K] = v`), by another module that imports this one back, or by
    a string that exec or eval runs (`exec("k = v")`, a walrus in `eval("(k := v)")`, `eval("D.update(K=v)")`); the
    comment above _Module names them ([namespace-rebinding], [exec-eval]) with the reason and the plants. Built from the
    code that runs at import (a class body's bindings among it, read as the module's: the body runs at import, and a
    name bound in both scopes is bound twice); a function's own bindings are added when the function is walked
    (`within`), its parameters shadowing every table. `bindings` (since
    the fixup of 2026-09-22, the verifier's finding that five licences had no value condition) is every name bound at
    import, to its value expression when its one binding is an assignment and None otherwise, so a licence's value check
    reads a value written through a name (`_ROOT = tempfile.mkdtemp(); os.environ["XDG_STATE_HOME"] = _ROOT`,
    `_STATE_TD.name`), and a name rebound by any form above stays a name the check cannot read (_shown_value says so);
    _resolved does the substitution."""

    def __init__(self, tree=None):
        self.os_names = {"os"}
        self.environ_names = set()
        self.dicts = {}
        self.loop_literals = {}      # a name a `for` binds to each of a tuple or list of string literals, in turn
        self.bindings = {}           # a name bound at import -> its value node when that one binding is an assignment; else None
        self._scope, self._parent, self._dicts_checked = tree, None, False     # the dict check's scope (dict_items)
        self._star = False           # a star import seen at import time (absorb): every name it could bind is unreadable
        if tree is not None:
            self.absorb([node for node, _nested in _import_time_nodes(tree.body)])
            for loop in _module_level_compounds(tree.body, (ast.For, ast.AsyncFor)):
                self._absorb_loop(loop)              # the loop header itself: the import-time walk yields only its body
                self._bind_targets([loop.target])    # and its target is a binding, which the value resolver reads too
            for name in _import_time_other_bindings(tree.body):
                self._rebound(name)                  # a with target, an except name, a match capture, a def or class name
            for st in _every_statement(tree.body):
                if isinstance(st, ast.Global):
                    for name in st.names:
                        self._rebound(name)          # a def that declares it global rebinds it when it runs
            if self._star:
                for name in set(self.bindings) | set(self.loop_literals) | set(self.dicts):
                    self._rebound(name)              # a star import may bind any of them, so each is bound twice

    def _absorb_loop(self, n):
        """`for var in ("A", "B"): environ[var] = v` writes exactly A and B (conftest's service-env fixture, the guard
        test's restore): the literals are read; a loop over anything computed, a name bound by two loops, or a name
        bound as well by any other binding the module's code spells, stays unreadable (absorb marks what the import-time
        walk hands it, an assignment of any kind, an import, a walrus or a `type` statement, before a module-level loop
        is read here, and __init__ marks a with target, an except name, a match capture, a def or class name, a `global`
        and a star import after it; either order leaves the name unreadable); a target that is not a bare name leaves
        each name it binds unreadable. A rebinding the module does not spell is not seen, and the loop's literals are
        still read: through the module's namespace (`globals()["k"] = v`, `vars()`, `sys.modules[__name__].k = v`,
        setattr on the module) or by a string that exec or eval runs (`exec("k = v")`, a walrus in `eval("(k := v)")`;
        the verifier's findings on round 2's thirteenth commit of fork PR #894, where this docstring said a name bound
        by anything else stays unreadable, and on its fourteenth, where it named exec alone). The comment above _Module
        names both ([namespace-rebinding], [exec-eval]), with a plant of a loop name for each form."""
        if isinstance(n.target, ast.Name):
            literal = (isinstance(n.iter, (ast.Tuple, ast.List)) and n.iter.elts
                       and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in n.iter.elts))
            self.loop_literals[n.target.id] = {e.value for e in n.iter.elts} if literal and n.target.id not in self.loop_literals else None
        else:
            for t in _flat_targets([n.target]):
                if isinstance(t, ast.Name):
                    self.loop_literals[t.id] = None

    def _bind(self, name, value):
        """`name` bound at import to the expression `value`, or to None (bound by something that is not an assignment); a
        second binding handed here, of any kind, makes the name unreadable (None). A rebinding the module's code does not
        spell is never handed here (_absorb_loop names those)."""
        self.bindings[name] = None if name in self.bindings else value

    def _bind_targets(self, targets):
        for t in _flat_targets(targets):
            if isinstance(t, ast.Name):
                self._bind(t.id, None)

    def _rebound(self, name):
        """`name` bound by something the tables cannot read a value from: unreadable in every table (THE RULE above)."""
        self._bind(name, None)
        self.loop_literals[name] = None
        self.dicts[name] = None

    def absorb(self, nodes):
        for node in nodes:
            for n in ast.walk(node):
                if isinstance(n, (ast.For, ast.AsyncFor)):
                    self._absorb_loop(n)             # not cleared after: that would wipe a function's own literal loop
                    self._bind_targets([n.target])
                elif isinstance(n, ast.Import):
                    self.os_names.update(a.asname for a in n.names if a.name == "os" and a.asname)
                    for a in n.names:
                        self._rebound((a.asname or a.name).split(".")[0])
                elif isinstance(n, ast.ImportFrom):
                    if n.module == "os":
                        self.environ_names.update(a.asname or a.name for a in n.names if a.name in ("environ", "environb"))
                        if any(a.name == "*" for a in n.names):
                            self.environ_names.update(("environ", "environb"))     # os.__all__ carries both
                    for a in n.names:
                        if a.name == "*":
                            self._star = True        # binds names no text here spells: every name, after the walk (__init__)
                        else:
                            self._rebound(a.asname or a.name)
                elif _TYPE_ALIAS and isinstance(n, _TYPE_ALIAS):
                    self._rebound(n.name.id)         # `type k = ...` (3.12) binds k
                elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    self._rebound(n.name)
                elif isinstance(n, (ast.With, ast.AsyncWith)):
                    for t in _flat_targets([i.optional_vars for i in n.items if i.optional_vars is not None]):
                        if isinstance(t, ast.Name):
                            self._rebound(t.id)
                elif isinstance(n, ast.ExceptHandler) and n.name:
                    self._rebound(n.name)
                elif isinstance(n, ast.match_case):
                    for name in _pattern_captures(n.pattern):
                        self._rebound(name)
                elif isinstance(n, ast.NamedExpr):
                    self._rebound(n.target.id)
                elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                    self._rebound(n.target.id)
                elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                    self._bind(n.target.id, n.value)
                    self.loop_literals[n.target.id] = self.dicts[n.target.id] = None
                elif isinstance(n, ast.Assign):
                    whole = {id(t) for t in n.targets if isinstance(t, ast.Name)}     # `A = v`, `A = environ[K] = v`
                    single = len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                    for t in _flat_targets(n.targets):
                        if isinstance(t, ast.Name):
                            self._bind(t.id, n.value if id(t) in whole else None)      # an unpacked name is not the value
                            self.loop_literals[t.id] = None
                            if not single:
                                self.dicts[t.id] = None
                    if single:
                        name = n.targets[0].id
                        if self.is_environ(n.value):
                            self.environ_names.add(name)
                        else:
                            self.dicts[name] = None if name in self.dicts else _literal_mapping(n.value)
        return self

    def dict_items(self, name):
        """{key: value node} of the dict literal `name` is bound to, or None when it is unreadable: bound more than once by
        bindings the module's code spells, or referenced by name anywhere in its scope other than by one of _DICT_READS
        (_drop_dicts_referenced_outside_the_reads, which names the references it does not see).
        The reference check runs when a write first reads a dict through its name, once per scope: over the whole module
        for a module-level dict (a use inside any def counts), over the function for a dict the function binds itself;
        the census reads a dict through its name in one module of the tree, so the other modules never pay for the walk."""
        items = self.dicts.get(name)
        if items is None:
            return None
        if self._parent is not None and self._parent.dicts.get(name) is items:
            return self._parent.dict_items(name)        # the enclosing scope's binding, not rebound here
        if not self._dicts_checked:
            self._dicts_checked = True
            self._drop_dicts_referenced_outside_the_reads(self._scope)
        return self.dicts.get(name)

    def _drop_dicts_referenced_outside_the_reads(self, scope):
        """Every tracked dict (a name bound once to a literal mapping) referenced anywhere under `scope` (the module's tree,
        or a function), in any nested scope, other than by one of _DICT_READS becomes unreadable (None). A reference is a
        Name node or a string that binds the name (_names_bound_by_a_string); one through the module's namespace
        (`globals()["D"]`, `sys.modules[__name__].D`), from another module or in a string that exec or eval runs
        (`exec("D[K] = v")`, `eval("D.update(K=v)")`) is not seen, and the comment above _Module names those
        ([namespace-rebinding], [exec-eval]). One BFS walk:
        ast.walk visits a parent before its children, so an allowed reference is recorded, by id(node) in a side table,
        before the name under it is reached."""
        tracked = {name for name, items in self.dicts.items() if items is not None}
        if not tracked or scope is None:
            return
        allowed = set()
        for n in ast.walk(scope):
            if isinstance(n, ast.Name):
                if n.id in tracked and id(n) not in allowed:
                    self.dicts[n.id] = None
                continue
            for name in _names_bound_by_a_string(n):
                if name in tracked:
                    self.dicts[name] = None
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                allowed.add(id(n.targets[0]))        # the binding itself (a second one at import already made it None)
            elif isinstance(n, ast.Call):
                method_args = _mapping_write_call(n, self)
                if method_args is not None and method_args[0] in ("update", "__ior__"):
                    allowed.update(id(a) for a in method_args[1])
                allowed.update(id(kw.value) for kw in n.keywords if kw.arg is None)
            elif isinstance(n, ast.AugAssign) and self.is_environ(n.target):
                allowed.add(id(n.value))
            elif isinstance(n, ast.Dict):
                allowed.update(id(v) for k, v in zip(n.keys, n.values) if k is None)
            elif isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)):
                allowed.add(id(n.iter))
            elif isinstance(n, ast.Compare):
                allowed.update(id(c) for op, c in zip(n.ops, n.comparators) if isinstance(op, (ast.In, ast.NotIn)))

    def within(self, node, environ_params=()):
        """These names plus whatever `node` (a function) binds itself. Every parameter (its own and a nested def's or
        lambda's) is unreadable in `bindings`, `loop_literals` and `dicts`, and the function's own parameters leave
        `environ_names`, so a module-level loop, dict or alias of the same name is never read through one (the reviewer's
        ruling of round 1 on fork PR #894); `environ_params` names the parameters the call being followed binds to the
        mapping (_environ_params), which are the mapping here."""
        inner = _EnvNames()
        inner.os_names, inner.environ_names, inner.dicts = set(self.os_names), set(self.environ_names), dict(self.dicts)
        inner.loop_literals, inner.bindings = dict(self.loop_literals), dict(self.bindings)
        inner._scope, inner._parent = node, self
        for a in ast.walk(node):
            if isinstance(a, ast.arg):
                inner.bindings[a.arg] = inner.loop_literals[a.arg] = inner.dicts[a.arg] = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            inner.environ_names.difference_update(a.arg for a in _parameters(node))
        inner.environ_names.update(environ_params)
        return inner.absorb([node])

    def is_environ(self, node):
        if isinstance(node, ast.Attribute) and node.attr in ("environ", "environb") and isinstance(node.value, ast.Name):
            return node.value.id in self.os_names
        return isinstance(node, ast.Name) and node.id in self.environ_names


_DICT_READS = ("an environment update's mapping argument (environ.update(D), environ |= D, the dunder __ior__ spellings), "
               "a ** spread (f(**D), {**D}), a for or comprehension iterable, a membership test (K in D), the one binding")
#   the only references through which a tracked dict stays readable (_EnvNames._drop_dicts_referenced_outside_the_reads)


def _parameters(fn):
    """Every parameter of the def or lambda `fn`, in order: positional-only, positional, *args, keyword-only, **kwargs."""
    a = fn.args
    return list(a.posonlyargs) + list(a.args) + ([a.vararg] if a.vararg else []) + list(a.kwonlyargs) + ([a.kwarg] if a.kwarg else [])


def _names_bound_by_a_string(n):
    """The names the node `n` binds by a string rather than a Name node: a def or class name, an import's alias, an except
    name, a match capture, a global or nonlocal declaration, a parameter."""
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [n.name]
    if isinstance(n, ast.alias):
        return [(n.asname or n.name).split(".")[0]]
    if isinstance(n, ast.ExceptHandler):
        return [n.name] if n.name else []
    if isinstance(n, (ast.MatchAs, ast.MatchStar)):
        return [n.name] if n.name else []
    if isinstance(n, ast.MatchMapping):
        return [n.rest] if n.rest else []
    if isinstance(n, (ast.Global, ast.Nonlocal)):
        return list(n.names)
    if isinstance(n, ast.arg):
        return [n.arg]
    return []


def _pattern_captures(pattern):
    """The names a match-case pattern captures: a MatchAs or MatchStar name and a MatchMapping rest, however nested."""
    return [name for p in ast.walk(pattern) for name in _names_bound_by_a_string(p)]


def _fresh(node):
    """A tree of the expression `node` parsed anew from its own text: the one tree the substitution below may rewrite.
    THE CONTRACT (the reviewer's ruling of 2026-09-22, from a CI red on fork PR #891): a parsed tree is read-only for
    every consumer, per-node data lives in a side table keyed by id(node), and no consumer deep-copies a parsed node.
    THE MECHANISM: the parser hands out ast.Load, Store, Del and the operator nodes as process-wide singletons, so an
    attribute another census writes on one (`child._parent = node` over every node it walks, the singletons among them)
    is on every tree parsed afterwards, and a deepcopy of a small expression that holds a tagged singleton follows the
    tag into that census's whole graph (a RecursionError through copy.py on CI's 3.10 and 3.11, a 147 s copy on 3.12).
    Until the fourth commit of the same day both substitution sites deep-copied the parsed node; the pins in the test
    class plant the tag and hold the walk to the contract. The text is parsed as a CALL ARGUMENT (the reviewer's ruling of
    round 1 on fork PR #894): a starred argument (`os.putenv(K, *rest)`) unparses to `*rest`, which does not parse as an
    expression of its own, so a parse of the bare text raised a SyntaxError naming no module and no line, on 3.10 and
    3.12; every other value shape round-trips either way."""
    return ast.parse("_(%s)" % ast.unparse(node), mode="eval").body.args[0]


class _Substitute(ast.NodeTransformer):
    """An expression with every name whose one binding at import is an assignment replaced by that value expression,
    recursively, rewritten over a FRESH tree parsed from the expression's text (_fresh), never over the parsed node or a
    copy of it; a name already under substitution (`seen`) is left as it is, so a self-referencing binding cannot loop.
    THE RULE (_EnvNames): a first binding is read and any later binding the module's code spells invalidates it, so a
    name rebound by a for or with target, an except name, a match capture, a def, a class, a `type` statement or a
    `global` in a def, or any name after a star import, stays a name here (the reviewer's ruling of round 1 on fork PR
    #894: before it such a name resolved to its first assignment, and a licence's value check passed a value the module
    never writes; the star import since the verifier's finding on round 2). A name rebound through the module's
    namespace (`globals()["_ROOT"] = v`) or by a string that exec or eval runs (`exec('_ROOT = v')`, a walrus in
    `eval('(_ROOT := v)')`) is not seen, and still resolves to its first assignment: the comment above _Module names
    both ([namespace-rebinding], [exec-eval])."""

    def __init__(self, bindings, seen=frozenset()):
        self.bindings, self.seen = bindings, seen

    def visit_Name(self, node):
        bound = self.bindings.get(node.id)
        if bound is None or node.id in self.seen or not isinstance(node.ctx, ast.Load):
            return node
        # Contract: a parsed tree is read-only for every consumer, so the bound value is re-parsed from its text, never
        # deep-copied. Mechanism: its ctx nodes are parser singletons another census may have tagged with its whole graph.
        return _Substitute(self.bindings, self.seen | {node.id}).visit(_fresh(bound))


def _resolved(node, names):
    """The value expression `node` as text with every name whose one binding at import is an assignment replaced by what it
    is bound to (`_ROOT` -> `tempfile.mkdtemp()`, `_STATE_TD.name` -> `tempfile.TemporaryDirectory().name`,
    `os.path.join(_tmp, 'romp')` -> `os.path.join(tempfile.mkdtemp(), 'romp')`), so a licence's value check reads the
    value and not the name; the text of `node` itself where nothing substitutes (a name bound again by any binding the
    module's code spells, or bound by something other than an assignment, stays a name: THE RULE in _EnvNames); "" for
    None. A name rebound through the module's namespace (`globals()["_ROOT"] = "/srv/real-state"`) or by a string that
    exec or eval runs (`exec('_ROOT = "/srv/real-state"')`, a walrus in `eval('(_ROOT := "/srv/real-state")')`) is not
    seen and still resolves to its first assignment, so a licence's value check passes the first value (the verifier's
    findings on round 2 of fork PR #894, where this docstring said a name bound again by anything stays a name, on its
    thirteenth commit, where it named the namespace alone, and on its fourteenth, where it named exec alone); the
    comment above _Module names both ([namespace-rebinding], [exec-eval]), and the licence test holds a plant of the
    namespace form, the exec form and the eval form clean, so a change that starts reading any of them reds."""
    if node is None:
        return ""
    # Contract: a parsed tree is read-only for every consumer, so the value is re-parsed from its text, never deep-copied.
    # Mechanism: its ctx nodes are parser singletons another census may have tagged with its whole graph (_fresh).
    return ast.unparse(_Substitute(names.bindings).visit(_fresh(node)))


def _unreadable(what, node, where):
    return UnreadableEnvWrite("cannot read the key%s of this %s at line %d of %s: %s (a string or bytes literal key, a dict literal, "
                              "keyword arguments, or a name bound once to a dict literal are read; a computed key or "
                              "mapping is not)" % ("s" if what == "update" else "", what, node.lineno, where, ast.unparse(node)))


def _keys(node, stmt, where, what, names):
    """The key(s) a subscript, setdefault, __setitem__ or putenv names: a string literal (a bytes literal for os.environb),
    or a name a `for` over string literals binds (each literal in turn); loud for anything else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        return {_key_text(node.value)}
    if isinstance(node, ast.Name) and names.loop_literals.get(node.id):
        return set(names.loop_literals[node.id])
    raise _unreadable(what, stmt, where)


def _mapping_items(node, names, stmt, where):
    """{key: value node} the mapping expression `node` gives an update or a `|=`: a literal, or a name bound to one; loud
    otherwise."""
    items = _literal_mapping(node)
    if items is None and isinstance(node, ast.Name):
        items = names.dict_items(node.id)
    if items is None:
        raise _unreadable("update", stmt, where)
    return items


def _mapping_keys(node, names, stmt, where):
    """The keys the mapping expression `node` gives an update or a `|=`: a literal, or a name bound to one; loud otherwise."""
    return set(_mapping_items(node, names, stmt, where))


def _flat_targets(targets):
    for t in targets:
        if isinstance(t, (ast.Tuple, ast.List)):
            yield from _flat_targets(t.elts)
        elif isinstance(t, ast.Starred):
            yield from _flat_targets([t.value])
        else:
            yield t


_Write = collections.namedtuple("_Write", "key shape value line resolved via", defaults=("",))
#   one environment write as the scan reads it: the KEY written, the SHAPE (assignment, setdefault, update, |=, putenv;
#   __setitem__ and __ior__ for the dunder spellings, called on the mapping or unbound with the mapping as the first argument;
#   augmented for `environ[KEY] += ...` and target for a key bound as a for, comprehension or with target, both with no
#   value), the VALUE expression (an ast node, or None where the shape has none the scan reads), the LINE of the statement (of
#   the CALL, for a write reached through one), the value RESOLVED through the names bound once at import (_resolved) and
#   VIA: "" for a write made where it stands, else the callee chain a write at import is reached through (_reached_writes)


def _env_write_records(node, names, where="<module>", environ_params=()):
    """Every environment write under `node`, as _Write records: `environ[KEY] = v`, `environ |= {...}`,
    `environ.update({...})`, `environ.update(KEY=v)`, `environ.update(NAME)` for a NAME bound to a dict literal,
    `environ.setdefault(KEY, v)` and `os.putenv(KEY, v)`, environ spelled any way `names` knows (review round 2,
    2026-09-18: the subscript and setdefault alone before, so a module-level update was invisible), and since the third
    commit of 2026-09-22 the dunder spellings `environ.__setitem__(KEY, v)` and `environ.__ior__({...})`, the same two
    unbound with the mapping as the first argument (`dict.__setitem__(environ, KEY, v)`), and every shape through
    `os.environb` with a bytes key (the verifier found the three passing silently against the contract). A write whose keys
    cannot be read from the source raises UnreadableEnvWrite naming the line, never skips: the repo-wide import-time
    rule is only as good as the writes it reads. Since round 2 of fork PR #894 (the reviewer's ruling of round 1, where
    `os.environ["PATH"] += ...` and a key bound as a loop target passed silently) two shapes more: an augmented
    assignment to a key (`environ[KEY] += suffix`, shape "augmented", recorded with NO value: the right side is a suffix,
    not the value written, and read as the value it would satisfy a value licence), and a key bound as a for,
    comprehension or with target (`for environ[KEY] in ...`, shape "target", no value), any environment subscript in a
    store position that no assignment above names; a module-level for or with target reaches here because
    _compound_header yields it. `environ_params` names the parameters of the def `node` that the call being followed
    binds to the mapping (_EnvNames.within). Removals (`pop`, `del`) are not writes and are outside this scan's
    contract: unset is the production default and the state a clean shell gives every module, so a removal at import
    sets nothing a later module would not have found on its own; _env_removals reads them where a restore counts."""
    return _writes_in_scope(node, names.within(node, environ_params), where)


def _writes_in_scope(node, names, where):
    """_env_write_records over `node` with `names` already the scope's own (the resolver computes it once per callee)."""
    out = []
    assigned = set()        # id() of every environment subscript an assignment names: read with its value, never again;
                            # and of a bare annotation's target, which writes nothing

    def write(key, shape, value, line):
        out.append(_Write(key, shape, value, line, _resolved(value, names)))

    for n in ast.walk(node):
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            if isinstance(n, ast.AnnAssign) and n.value is None:
                # a bare annotation writes nothing: `os.environ[K]: str` evaluates the mapping and the key and sets
                # nothing, so its target is not read as a store below either (the verifier's finding on round 2 of fork
                # PR #894: it was recorded as a write of shape "target", a write that does not happen)
                assigned.add(id(n.target))
                continue
            for t in _flat_targets(n.targets if isinstance(n, ast.Assign) else [n.target]):
                if isinstance(t, ast.Subscript) and names.is_environ(t.value):
                    assigned.add(id(t))
                    for k in sorted(_keys(t.slice, n, where, "environment assignment", names)):
                        write(k, "assignment", n.value, n.lineno)
        elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Subscript) and names.is_environ(n.target.value):
            assigned.add(id(n.target))
            for k in sorted(_keys(n.target.slice, n, where, "augmented assignment", names)):
                write(k, "augmented", None, n.lineno)
        elif (isinstance(n, ast.Subscript) and isinstance(n.ctx, ast.Store) and id(n) not in assigned
              and names.is_environ(n.value)):
            for k in sorted(_keys(n.slice, n, where, "environment target", names)):
                write(k, "target", None, n.lineno)
        elif isinstance(n, ast.AugAssign) and names.is_environ(n.target):
            for k, v in _mapping_items(n.value, names, n, where).items():
                write(k, "|=", v, n.lineno)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            method_args = _mapping_write_call(n, names)
            if method_args is not None:
                method, args = method_args
                if method == "update":
                    if len(args) > 1 or any(kw.arg is None for kw in n.keywords):
                        raise _unreadable("update", n, where)
                    for a in args:
                        for k, v in _mapping_items(a, names, n, where).items():
                            write(k, "update", v, n.lineno)
                    for kw in n.keywords:
                        write(kw.arg, "update", kw.value, n.lineno)
                elif method == "__ior__":
                    for k, v in _mapping_items(args[0] if args else None, names, n, where).items():
                        write(k, "__ior__", v, n.lineno)
                else:       # setdefault and __setitem__: (KEY, value)
                    for k in sorted(_keys(args[0] if args else None, n, where, method, names)):
                        write(k, method, args[1] if len(args) > 1 else None, n.lineno)
            elif isinstance(n.func.value, ast.Name) and n.func.value.id in names.os_names and n.func.attr == "putenv":
                for k in sorted(_keys(n.args[0] if n.args else None, n, where, "putenv", names)):
                    write(k, "putenv", n.args[1] if len(n.args) > 1 else None, n.lineno)
    return out


_MAPPING_WRITERS = ("update", "setdefault", "__setitem__", "__ior__")


def _mapping_write_call(n, names):
    """(method, args) for a call of a writing method of the environment mapping: update, setdefault, __setitem__ or __ior__
    called on the mapping (`environ.update(...)`), or the two dunders called unbound with the mapping as the first
    argument (`dict.__setitem__(os.environ, K, v)`), the argument list then starting after the mapping; None for any other
    call. The third commit of 2026-09-22: the verifier found `os.environ.__setitem__(K, v)` and `dict.__setitem__(os.environ,
    K, v)` passing the scan silently where the contract says a write is read or loud. An unbound update or setdefault
    (`MutableMapping.update(os.environ, {...})`) is NOT read: the scan cannot tell it from `saved.update(os.environ)`, a
    read of the environment into another mapping, so it stays outside and is named above _Module."""
    if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _MAPPING_WRITERS):
        return None
    if names.is_environ(n.func.value):
        return n.func.attr, list(n.args)
    if n.func.attr in ("__setitem__", "__ior__") and n.args and names.is_environ(n.args[0]):
        return n.func.attr, list(n.args[1:])
    return None


def _env_writes(node, names, where="<module>"):
    """The environment keys the code under `node` sets, in every shape _env_write_records reads."""
    return {w.key for w in _env_write_records(node, names, where)}


def _env_removals(node, names):
    """The environment keys the code under `node` removes by a string literal: `environ.pop(KEY, ...)`, `del environ[KEY]`,
    `os.unsetenv(KEY)`. Read for the restore a cleanup makes (a pop is how a value found unset is put back). A key the
    scan cannot read is passed over here and hidden by nothing: the cleanup check then faults for a restore it cannot
    see."""
    names = names.within(node)
    keys = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.args and isinstance(n.args[0], ast.Constant) \
                and isinstance(n.args[0].value, (str, bytes)):
            if (names.is_environ(n.func.value) and n.func.attr == "pop") or (
                    isinstance(n.func.value, ast.Name) and n.func.value.id in names.os_names and n.func.attr == "unsetenv"):
                keys.add(_key_text(n.args[0].value))
        elif isinstance(n, ast.Delete):
            for t in n.targets:
                if isinstance(t, ast.Subscript) and names.is_environ(t.value) and isinstance(t.slice, ast.Constant) \
                        and isinstance(t.slice.value, (str, bytes)):
                    keys.add(_key_text(t.slice.value))
    return keys


_COMPOUND = tuple(getattr(ast, name) for name in ("If", "For", "AsyncFor", "While", "With", "AsyncWith", "Try", "TryStar", "Match")
                  if hasattr(ast, name))


def _module_level_compounds(body, kind):
    """The compound statements of `kind` (ast.For, say) that run at import, however nested in the module's
    if/for/while/with/try (and match) blocks and in its class bodies (a class body runs at import; the fixup of
    2026-09-22); nothing inside a def."""
    for s in body:
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(s, ast.ClassDef):
            yield from _module_level_compounds(s.body, kind)
            continue
        if isinstance(s, kind):
            yield s
        if isinstance(s, _COMPOUND):
            for attr in ("body", "orelse", "finalbody"):
                yield from _module_level_compounds(getattr(s, attr, None) or [], kind)
            for h in getattr(s, "handlers", []):
                yield from _module_level_compounds(h.body, kind)
            for c in getattr(s, "cases", []):
                yield from _module_level_compounds(c.body, kind)


def _def_header(s):
    """The parts of a def statement that execute at import: its decorators and its default argument values."""
    return list(s.decorator_list) + [d for d in list(s.args.defaults) + list(s.args.kw_defaults) if d is not None]


def _class_header(s):
    """The parts of a class statement that execute at import beside its body: decorators, bases and keywords."""
    return list(s.decorator_list) + list(s.bases) + [k.value for k in s.keywords]


def _compound_header(s):
    """The expressions a block statement evaluates at import beside its bodies: an if or while test, a for iterable and
    its target, the with items and their targets, a match subject and its guards, the handler types of a try. The for
    and with targets since round 2 of fork PR #894 (the reviewer's ruling of round 1: `for os.environ[K] in ...` at
    module level wrote K with the scan silent, since no node of the header held the target): a target is a store, so
    _env_write_records reads an environment subscript in one as a write. A target also runs code of its own: Python
    evaluates the object and the key of a subscript target and the object of an attribute target before each store, so
    a call in them (`for _d[_w()] in ...`, `for _w().x in ...`) runs at import and _reached_writes follows it like any
    call; a bare name in a target is a store or a reference, never a call (the verifier's finding on round 2 of fork PR
    #894, where this docstring said nothing in a target ran as a call). The bare-name test plants every position in a
    for and in a with target (the target itself, a subscript's key and object, an attribute's object), a def named bare
    in each and a call in each but the first (the verifier's finding on round 2's thirteenth commit, where the plants
    held four of them)."""
    out = [getattr(s, a) for a in ("test", "iter", "subject") if getattr(s, a, None) is not None]
    if isinstance(s, (ast.For, ast.AsyncFor)):
        out.append(s.target)
    out += [i.context_expr for i in getattr(s, "items", [])]
    out += [i.optional_vars for i in getattr(s, "items", []) if i.optional_vars is not None]
    out += [h.type for h in getattr(s, "handlers", []) if h.type is not None]
    out += [c.guard for c in getattr(s, "cases", []) if c.guard is not None]
    return out


def _import_time_nodes(body, nested=False):
    """(node, nested) for everything in `body` that EXECUTES AT IMPORT: the simple statements; the header expressions of
    the if/for/while/with/try (and match) blocks and the statements in their bodies however nested (a write of the
    peers setting planted inside a module-level `if` body leaks exactly like a bare one, review round 1, 2026-09-18);
    the decorators and default argument values of a def (its body runs when called and is not read here; a call of it
    at import is, _reached_writes); the decorators, bases and keywords of a class and, since the fixup of 2026-09-22
    (the verifier's finding on this PR: a write planted in a class body left the pin green), the class body itself,
    which runs at import exactly like the module's own (its methods' bodies skipped like any def). `nested` is True for
    anything not directly in the module's body, the writes a column-0 grep misses."""
    for node, nested_, _scope in _import_time_nodes_scoped(body, nested):
        yield node, nested_


def _import_time_nodes_scoped(body, nested=False, scope=None):
    """_import_time_nodes with the class body each node runs in beside it (`scope`: the innermost ClassDef, or None at
    module level): a class's decorators, bases and keywords run in the scope around the class, its body in its own. The
    call resolver reads a bare name in a class body against that body's defs (_resolve)."""
    for s in body:
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for h in _def_header(s):
                yield h, nested, scope
        elif isinstance(s, ast.ClassDef):
            for h in _class_header(s):
                yield h, nested, scope
            yield from _import_time_nodes_scoped(s.body, True, s)
        elif isinstance(s, _COMPOUND):
            for h in _compound_header(s):
                yield h, nested, scope
            for b in _block_bodies(s):
                yield from _import_time_nodes_scoped(b, True, scope)
        else:
            yield s, nested, scope


def _block_bodies(s):
    """The statement lists a block statement runs: its body, else and finally bodies, handler bodies and case bodies."""
    out = [getattr(s, attr, None) or [] for attr in ("body", "orelse", "finalbody")]
    out += [h.body for h in getattr(s, "handlers", [])]
    out += [c.body for c in getattr(s, "cases", [])]
    return out


def _import_time_statements(body):
    """Every statement of `body` that runs at import, compound ones included, however nested in the module's blocks and
    class bodies; a def is yielded (its name is bound at import) and its body is not."""
    for s in body:
        yield s
        if isinstance(s, ast.ClassDef):
            yield from _import_time_statements(s.body)
        elif isinstance(s, _COMPOUND):
            for b in _block_bodies(s):
                yield from _import_time_statements(b)


def _import_time_other_bindings(body):
    """The names bound at import by a form the import-time walk hands the value resolver no statement for (the reviewer's
    ruling of round 1 on fork PR #894, correctness-3's shapes): a with target, an except name, a match capture (MatchAs,
    MatchStar, a MatchMapping rest), a def or class name, in the module's blocks and its class bodies. A walker of its
    own: _module_level_compounds yields no def and no class. The for target is bound beside _absorb_loop."""
    for s in _import_time_statements(body):
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield s.name
        if isinstance(s, (ast.With, ast.AsyncWith)):
            for i in s.items:
                if i.optional_vars is not None:
                    yield from (t.id for t in _flat_targets([i.optional_vars]) if isinstance(t, ast.Name))
        for h in getattr(s, "handlers", []):
            if h.name:
                yield h.name
        for c in getattr(s, "cases", []):
            yield from _pattern_captures(c.pattern)


def _import_time_defs(body):
    """({name: [FunctionDef, ...]}, {name: [ClassDef, ...]}): every def and class a block of `body` binds at import, in
    `body` itself and in its if, try (else, finally, handlers), for, while, with and match bodies however nested (the
    reviewer's ruling of round 1 on fork PR #894: a def under `if` or in a `try/except ImportError` fallback, called at
    import, was missed silently); every binding of a name, not the last, so a redefinition in an else body is read beside
    the first (the safe side). Not a class body's: those bind the class's names, read for a call in that body (_resolve)
    and for a method (_method_chain). An async def is left out: calling it runs nothing of its body."""
    defs, classes = collections.defaultdict(list), collections.defaultdict(list)
    todo = [body]
    while todo:             # loop-ok: bounded by the statements of `body`
        for s in todo.pop(0):
            if isinstance(s, ast.FunctionDef):
                defs[s.name].append(s)
            elif isinstance(s, ast.ClassDef):
                classes[s.name].append(s)
            elif isinstance(s, _COMPOUND):
                todo.extend(_block_bodies(s))
    return dict(defs), dict(classes)


# ───────── writes reached through a call at import: a def or class under tests/ the scan can resolve ─────────
#
# A module-level call runs at import, so a write in the callee's body is a module-level write (the verifier's finding on
# this PR, 2026-09-22: `def _floor(): os.environ[...] = ...` then `_floor()` at module level left the pin green). The
# scan resolves a call's callee to code under tests/ and reads it (_resolve), EVERY binding the name has rather than an
# order-aware pick (the reviewer's ruling of round 1 on fork PR #894): a def of the module in any import-time block (a
# module-level if, try, else, finally, for, while, with or match body, a `try/except ImportError` fallback among them);
# a def of a class body, for a call in that body; a class (its __new__ and __init__, for an instantiation; a method, for
# `Class.method()`); a def or class imported from a module under tests/ (`from helper import floor; floor()`, `import
# helper; helper.floor()`, `import helper as h; h.floor()`, `helper.Seam.arm()`), by its dotted name (`import
# tests.helper; tests.helper.floor()`), through a star import (`from helper import *; floor()`; `__all__` is not
# consulted, so a private name reads as bound, the safe side; the dotted and star shapes since the third commit of
# 2026-09-22) and through a helper that re-exports it (`from helper2 import floor` where helper2 imported it); a def
# shadowed by a later import of its name, both read; a bare decorator (`@_arm` calls `_arm(fn)` at import) and a
# decorator factory's call; a `metaclass=M` value (M's __prepare__, __new__, __call__ and __init__; __prepare__ since the
# verifier's finding on round 2 of fork PR #894, where a write in it passed silently); a base named bare (not called:
# its __init_subclass__ chain, which creating the subclass runs); recursively through the callee's own calls, the
# mapping followed into a parameter of the def the call resolves to that the call passes it to or that defaults to it
# (_environ_params; passed into *args, **kwargs or a spread, it is loud; a lambda's parameter is not followed, nor a
# parameter of a def or class bound inside a function, [lambda-parameter] and [nested-def-parameter] below). A bare name
# anywhere else (a default, an if test, a with item, a for iterable, a for or with target, an except type, a keyword
# other than metaclass=) is a reference or a store and not a call; a call inside a for or with target's subscript or
# attribute runs and is followed (_compound_header), and so are the calls inside a base or keyword expression. The whole
# callee is read, so a write or a call in a def, class or lambda nested in it counts whether or not the callee calls it
# (read where it stands, every parameter unreadable), and a module-level block's body is read whatever its test, an `if
# __name__ == "__main__":` body among them, which runs when the file runs as a script and not at import: both on the
# safe side. A chain of calls is followed to _CALL_DEPTH_CAP (40) calls and raises past it, naming the chain (the
# deepest chain in the tree, and how it is derived, is under _CALL_DEPTH_CAP). The census at round 2 of fork PR #894
# finds two calls at import that reach a write, both licensed: tests/test_intr_marks_memo.py and
# tests/test_merge_tx_sets_light.py call test_asm_checkpoint.kernel_module() at module level (`import
# test_asm_checkpoint as TA; km = TA.kernel_module()`) and its body setdefaults ROMP_KERNEL_NO_OPEN to "1" (the
# verifier's own walker had counted the shape empty, so the module-alias form is one a resolver misses easily); no other
# call, decorator, metaclass or base it follows reaches one.
#
# OUTSIDE the scan, named here so nobody mistakes the pin for wider than it is. This is the list's one home
# (tests/README.md points here). Each entry's tag is a key of _OUTSIDE_THE_SCAN, whose plants
# test_every_shape_named_outside_the_scan_writes_when_run_and_the_scan_reads_none runs in a child interpreter (each
# writes its name) and through the scan (which records nothing and raises nothing for it), and the tags here are held
# EQUAL to the plants' keys, so a change that starts or stops reading a shape reds.
#   [product-code] a callee in product code: a module a test loads by path (romp_load.load_source, itself a name bound
#     to product code and not a def under tests/); what product code writes at import is the product's own tests' matter.
#   [stdlib-callee] a standard-library callee that writes the mapping, `operator.setitem(os.environ, K, v)` among them.
#   [instance-method] a method called on an instance (`Seam().arm()`).
#   [helper-lambda] a lambda another module binds (`from helper import ARM; ARM()`); a lambda in the module's own
#     import-time code is read where it stands, called or not.
#   [lambda-parameter] the mapping reaching a lambda's parameter, by the parameter's default (`lambda env=os.environ:
#     env.__setitem__(K, v)`) or by a call of the lambda itself (`(lambda env: env.update(K=v))(os.environ)`): a lambda is
#     read where it stands with every parameter unreadable (_EnvNames.within), and the parameter route (_environ_params)
#     is followed for a def or class a call resolves to, never for a lambda.
#   [nested-def-parameter] the mapping reaching a parameter of a def or class bound inside a function, by a call of it
#     there (`def _o(): def _i(env): env[K] = v; _i(os.environ)`, the mapping passed by keyword, a nested class's
#     __init__ called the same way) or by the parameter's default (`def _i(env=os.environ)`): _resolve reads the defs
#     and classes bound in the module's import-time blocks and class bodies, never one bound inside a function, so that
#     call is not followed, and the nested code is read where it stands as part of the function around it, with every
#     parameter unreadable (_EnvNames.within), as a lambda is (the verifier's finding on round 2's thirteenth commit of
#     fork PR #894, where only the lambda was named).
#   [aliased-callee] a def or class called through anything but its own name, an import of it or a class's method: a
#     module-level alias (`_g = _floor; _g()`, `_A = _Seam; _A()`), an expression (`[_floor][0]()`, `(_floor if x else
#     None)()`), getattr (`getattr(module, "_floor")()`), functools.partial (`functools.partial(_floor)()`) or an
#     attribute of the def (`_floor.__call__()`): _resolve reads a dotted name chain, and the value an alias is bound to
#     is not followed.
#   [callback] code under tests/ that a callee outside tests/ runs: a def passed as an argument (`map(_w, xs)`,
#     `sorted(xs, key=_w)`, `threading.Thread(target=_w)`; a bare name passed is a reference, not a call, the reviewer's
#     ruling of round 1 on fork PR #894) and an async def's coroutine run by it (`asyncio.run(_f())`; a call of an async
#     def runs nothing of its body, so _import_time_defs leaves async defs out).
#   [protocol-hook] a special method Python runs without a call the scan sees: a context manager's __enter__ (`with
#     _C():`), a descriptor's __set_name__ (`x = _D()` in a class body) and __get__ (`_K.x`, a property's getter among
#     them), a class's __class_getitem__ (`_B[int]`, and a base spelled that way, whose __init_subclass__ is not read
#     either), an instance's __mro_entries__ (`class K(_E())`), an iteration's __iter__ (`for x in _It()`), an operator
#     (`_C() + 1`), a truth test (`if _C():`), a format (`f"{_C()}"`) and a finalizer (`_C()`, collected at once). An
#     instantiation reads __new__ and __init__, a metaclass its __prepare__, __new__, __call__ and __init__, a base named
#     bare its __init_subclass__, and no other special method is read.
#   [call-result] a callee or a base bound to a call's result (`arm = make(); arm()`, `class K(make_base())`,
#     `under_conftest = unittest.skipUnless(...)`): the call itself is followed, not what it returns.
#   [exec-eval] `exec` or `eval` of a string: a write in it, and a binding or a mutation it makes (`exec("k = v")`, or
#     a walrus in `eval("(k := v)")`, after a loop binds k; `exec("D[K] = v")` or `eval("D.update(K=v)")` on a tracked
#     dict), which leaves the name read through its first binding, as under [namespace-rebinding]; the value side
#     (`exec('_ROOT = "/srv/real-state"')`, `eval('(_ROOT := "/srv/real-state")')`) is held clean by the licence test
#     beside that entry's. Each form has its plant for exec and for eval (the verifier's finding on round 2's fourteenth
#     commit of fork PR #894, where the binding, the mutation and the value side were planted for exec alone).
#   [inherited-metaclass] a metaclass a class inherits from a base of another module (`class K(helper.B)` where B has
#     `metaclass=M`).
#   [inherited-method] a method a class inherits from a base of another module (`class K(helper.Base)`, then `K()` runs
#     helper.Base.__init__); _method_chain follows bases of the same module only.
#   [held-otherwise] the mapping held by anything but a name the scan binds (`os.environ` under any name os is imported
#     as, `from os import environ` or its `as` name, `environ` after `from os import *`, a name a plain assignment binds
#     to either mapping, the one target a name, and a parameter the call being followed binds to it): an attribute
#     (`ns.env = os.environ`), a container item, a name bound by unpacking, an annotated assignment (`env: dict =
#     os.environ`), a chained one (`A = env = os.environ`), a walrus, or a for or with target, a name another module
#     binds to it (`from helper import ENV`, or through `from helper import *`), the mapping fetched by getattr
#     (`getattr(os, "environ")`) or through sys.modules.
#   [from-os-putenv] `from os import putenv` or `from os import *`, then `putenv(K, v)`.
#   [namespace-rebinding] a name rebound, or a tracked dict mutated, through the module's namespace rather than by a
#     binding or a reference the module spells (`globals()["k"] = v`, `vars()["k"] = v`, `sys.modules[__name__].k = v`,
#     `setattr(sys.modules[__name__], "k", v)`, `globals()["D"][K] = v`, `vars()["D"][K] = v`,
#     `sys.modules[__name__].D[K] = v`), or by a module it imports that reaches back into it through sys.modules: the
#     name reads through its first binding (THE RULE in _EnvNames), so a write through it is recorded under the first
#     binding's key and a licence's value check reads the first binding's value. The key side has the plants below;
#     the value side (`_ROOT = tempfile.mkdtemp()`, then `globals()["_ROOT"] = "/srv/real-state"`, then XDG_STATE_HOME
#     set to `_ROOT`) is a plant the licence test holds clean, since that write is recorded and so does not fit the
#     plants' form. Not read as rebinding every name wherever such a reference appears: many of the tree's writer
#     modules reference globals(), vars(), sys.modules or a __dict__ for other ends, and each value they write through
#     a name would go unreadable and fault its licence (five licensed writes in four modules, measured at the fix of
#     the verifier's findings on round 2 of fork PR #894).
#   [bound-method] a bound method of the mapping held in a name or fetched by getattr (`_set = os.environ.__setitem__;
#     _set(K, v)`, `getattr(os.environ, "update")(K=v)`), or a functools.partial of one.
#   [posix-putenv] `posix.putenv(K, v)`.
#   [unbound-update] an unbound update or setdefault on the mapping's class (`MutableMapping.update(os.environ, {...})`),
#     which the scan cannot tell from `saved.update(os.environ)`, a read (the dunders __setitem__ and __ior__ unbound
#     with the mapping first ARE read).
#   [after-import] what runs after the import: a write in setUpModule, setUpClass or a fixture of any scope, a def the
#     import does not call. conftest's _module_env_restored checks it for the names it watches (the seams and the postal
#     trio), naming the module that leaves one changed after its teardown (the reviewer's ruling of round 1 on fork PR
#     #894). A write by a session- or package-scoped fixture is read by the module check, or the per-test check, only
#     when the fixture's setup follows that check's snapshot: one requested by name by the first of the module's tests
#     to be set up (always, for an autouse one; a test a skip, skipif or xfail(run=False) mark ends is not set up, so
#     that first test can be a later one) runs before both and neither reads it, while one first requested by a later
#     test, or requested at run time by request.getfixturevalue, is read by one check or both depending on where the
#     request runs (conftest's comment above _module_env_restored; run by
#     test_a_write_by_a_fixture_scoped_above_module_is_named_by_each_check_whose_snapshot_its_setup_follows); the tree
#     has none (_fixtures_scoped_above_module, held at none by a pin).

_Module = collections.namedtuple("_Module", "where tree names defs classes imports stars root roles")
#   a module the resolver reads: its label (WHERE), TREE, import-time NAMES (_EnvNames), DEFS and CLASSES by name, each a
#   list of every def or class the module's import-time blocks bind to it (_import_time_defs), IMPORTS {local name,
#   dotted for `import tests.helper`: (path of a module under ROOT, attribute or None for the module itself)}, STARS, the
#   paths of the modules under ROOT it star-imports, the ROOT the imports resolve against (tests/, or a synthetic tree's
#   directory in the tests of the scan itself) and ROLES, {id(node): role} for each bare name or attribute Python calls
#   where it stands (_call_roles), a side table keyed by id(node) since a parsed tree is read-only for every consumer

class _Census(dict):
    """Everything the census holds between its reads in one run of this module, as ONE object that takes a weak reference
    (a plain dict cannot), so tearDownModule can read that its release freed it: "trees", realpath -> the tree of each
    file the census parsed itself and holds (_own_tree: every file the resolver reads, and every file the census loop
    walks that the resolver may read later, _resolver_targets; the loop's other trees are dropped after their walk);
    "modules", (path, root) -> the _Module the resolver built over one of those trees (_module_at); "derivations", path
    tuple -> what _census_build returned for it (_census_derivation); "proofs", the execution proof's _Reasserted for
    tests/conftest.py (_conftest_reasserts_proved: strings and frozensets). _HELD is its one owner. No test keeps a
    reference of its own: each reads through _held() and keeps what it gets as a local."""
    __slots__ = ("__weakref__",)


_HELD = []
#   THE ONE OWNER (the reviewer's rulings of 2026-09-24 on round 2 of fork PR #894): [the _Census] from the first census
#   read in this module's run until tearDownModule empties it, which frees the _Census, its trees, records and derivations
#   by reference count (none of them holds a cycle; tearDownModule's weak reference pins the _Census itself). A module
#   slot rather than a class attribute: the class's tests land on several xdist workers, and a build in setUpClass would
#   make each worker that runs any of its tests derive the whole tree; the first read builds instead.
_OWN_PARSES = collections.Counter()
#   realpath -> the number of times _own_tree parsed the file in this module's run, zeroed by setUpModule: the parse-once
#   pins read it (red under a second parse of a file in the run)


def _held():
    """The _Census _HELD holds, made on the first read of this module's run."""
    if not _HELD:
        _HELD.append(_Census(trees={}, modules={}, derivations={}, proofs={}))
    return _HELD[0]


def _own_tree(path, rel=None, hold=True):
    """The tree of the file at `path`, parsed by the census itself, never through tests/parse_cache.py (the exception to
    that module's one-cache rule, for the measured reason module_level_env_census's docstring gives): a tree the _Census
    holds ("trees") is served as it is; otherwise the file is parsed, counted in _OWN_PARSES, and, when `hold`, held in
    the _Census until tearDownModule's release, so the census loop and the resolver read one tree per file. The census
    loop passes `hold` False for a file under tests/ that the resolver cannot read later (_resolver_targets), and drops
    that tree after its walk; it holds a file outside tests/ (a test's synthetic file, small, which the test may census
    again under another path tuple), and the resolver always holds. A file parsed unheld and then read again would be
    parsed a second time, which the parse-once pins red naming it. `rel` is the filename the tree carries, else `path`.
    A file that does not parse, or is not UTF-8, raises as ast.parse or the decode does, and nothing is held. READ-ONLY
    all the same: no attribute is written on a node (the parser shares its singleton nodes, a Load or an operator, with
    every tree in the process) and no node is copied; per-node data lives in side tables keyed by id(node) (_Module's
    ROLES). The holder never re-reads a file: one rewritten after its parse in the same run is served its first tree (no
    caller rewrites one; each plant is a fresh temporary directory)."""
    real = os.path.realpath(path)
    trees = _held()["trees"]
    tree = trees.get(real)
    if tree is None:
        with open(real, encoding="utf-8") as f:
            text = f.read()
        _OWN_PARSES[real] += 1
        tree = ast.parse(text, filename=rel or path)
        if hold:
            trees[real] = tree
    return tree


_IMPORT_WORD = re.compile(r"\bimport\b")
_IMPORT_PAREN = re.compile(r"\bimport\s*\(")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _import_statement_words(text):
    """Every identifier on each line of `text` that holds the word `import`, backslash continuations joined, and, where
    a parenthesis follows the word (`from M import (`), on every line up to the one that closes it (a comment's
    parentheses not counted): a superset of the module and the names of every import statement in the file, since each
    has the word, its module before the word on the same logical line and its names after it on that line or in that
    list. It reads the text, not a tree (the census loop decides from it which trees to keep before it parses any), so a
    docstring, a comment or a string with the word adds words too, the safe side (a tree kept that nothing reads). It
    does not see an import spelled without the keyword (importlib.import_module, __import__), which the resolver does
    not follow either."""
    lines = text.replace("\\\n", " ").split("\n")       # a text-mode read has already turned \r\n and \r into \n
    chunks, i = [], 0
    while i < len(lines):       # loop-ok: bounded by the text's lines
        line = lines[i]
        i += 1
        if "import" not in line or not _IMPORT_WORD.search(line):
            continue
        chunks.append(line)
        paren = _IMPORT_PAREN.search(line)
        if paren:
            code = line[paren.end() - 1:].split("#", 1)[0]
            depth = code.count("(") - code.count(")")
            while depth > 0 and i < len(lines):       # loop-ok: bounded by the text's lines
                code = lines[i].split("#", 1)[0]
                chunks.append(lines[i])
                i += 1
                depth += code.count("(") - code.count(")")
    return set(_IDENTIFIER.findall("\n".join(chunks)))


def _under_tests(path, root=None):
    """True for a path under tests/ (this module's directory; `root` in the plants of the target scan), read as given,
    before any symlink is followed."""
    return os.path.abspath(path).startswith((HERE if root is None else root) + os.sep)


def _resolver_targets(paths, root=None):
    """The realpaths of the files among `paths` that the resolver may read during a census build over them, whose trees
    the census loop therefore holds (_own_tree) where it drops every other tree after its walk (the reviewer's third
    ruling of 2026-09-24 on round 2 of fork PR #894: the test files' trees dropped after their walk, the files the
    resolver reads held to teardown, and no file parsed twice in the module's run). The census resolves every import
    against tests/ (_module_level_env_write_records' default root), so the resolver reads only files under tests/, each
    named by an import statement of a file under tests/ or of a file handed in: a file under tests/ is a target when its
    name without .py (a package's __init__.py: its directory's name) is among the words of those files' import
    statements (_import_statement_words, a superset read from the text). A census over no file under tests/ has no
    target and reads no text. A file the resolver reads that this missed is parsed a second time, which the parse-once
    pins red naming it. `root` stands in for tests/ in the plants of the target scan (a synthetic tree run through the
    whole function); the census passes none."""
    inside = [p for p in paths if _under_tests(p, root)]
    if not inside:
        return frozenset()
    words = set()
    for p in sorted(set(_tests_tree_walk(root)) | set(paths)):
        with open(p, encoding="utf-8", errors="replace") as f:
            words |= _import_statement_words(f.read())
    return _named_by(inside, words)


_WORD_IMPORT = re.compile(r"\bimport\b")
_WORD_IMPORT_PAREN = re.compile(r"\bimport\s*\(")
_NAME_CHARS = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
#   the census pin's own copies of the three patterns the census rule is written in (the word import, the word followed
#   by a parenthesis, an identifier), compiled apart from _import_statement_words' so a change to those is not a change
#   to these


def _import_line_named_files(paths, root=None):
    """THE CENSUS PIN'S OWN READER of the files the census loop keeps past their walk (the verifier's finding at round 2's
    twentieth commit of fork PR #894: the pin compared the kept trees with _resolver_targets read again, so a widening
    inside that function, every file under tests/ returned or every identifier of every file read, held all 958 trees
    and left the module green): the realpaths of the files among `paths` under tests/ (`root` in a plant) whose module
    name (the file's name without .py; for a package's __init__.py, its directory's name) is an identifier on a line, of
    some file under tests/ or among `paths`, that holds the word `import` (backslash continuations joined), or on a line
    up to the one that closes a parenthesis opened right after that word (a comment's parentheses not counted). It is
    the census's rule, read by code of its own: none of _resolver_targets, _import_statement_words, _named_by or
    _tests_tree_walk runs here, so the pin that holds the census's kept trees EQUAL to this set is red under a change to
    any of them that moves what the census keeps, in either direction. It reads what the rule reads and no more: an
    import spelled without the keyword (importlib.import_module, __import__), which the resolver does not follow either,
    is not read, and neither is a file outside tests/ that is not handed in. It is not the set of files an import
    statement names: the rule reads text, before any tree is parsed, so a docstring, a comment or a string on an import
    line adds its words, the safe side (measured at round 2's thirty-first commit of fork PR #894: 73 files kept, where
    an ast read of every import statement under tests/ names 38, all among the 73; an ast read here would parse every
    file a second time, which the parse-once rule forbids, and could not equal what the census keeps)."""
    base = HERE if root is None else root
    by_name = collections.defaultdict(set)
    for p in paths:
        full = os.path.abspath(p)
        if not full.startswith(base + os.sep):
            continue
        folder, leaf = os.path.split(full)
        by_name[os.path.basename(folder) if leaf == "__init__.py" else os.path.splitext(leaf)[0]].add(os.path.realpath(p))
    if not by_name:
        return frozenset()
    found = set()
    corpus = {os.path.join(d, f) for d, _, fs in os.walk(base) for f in fs if f.endswith(".py")} | set(paths)
    for p in sorted(corpus):
        with open(p, encoding="utf-8", errors="replace") as f:
            lines = f.read().replace("\\\n", " ").split("\n")
        at = 0
        while at < len(lines):          # loop-ok: `at` moves forward on every pass, bounded by the file's lines
            first = lines[at]
            last = at
            if "import" in first and _WORD_IMPORT.search(first):
                opened = _WORD_IMPORT_PAREN.search(first)
                if opened:
                    depth, row, code = 0, at, first[opened.end() - 1:]
                    while True:         # loop-ok: `row` moves forward, bounded by the file's lines
                        code = code.split("#", 1)[0]
                        depth += code.count("(") - code.count(")")
                        if depth <= 0 or row + 1 >= len(lines):
                            break
                        row += 1
                        code = lines[row]
                    last = row
                for word in _NAME_CHARS.findall("\n".join(lines[at:last + 1])):
                    found |= by_name.get(word, set())
            at = last + 1
    return frozenset(found)


def _named_by(paths, words):
    """The realpaths of the files among `paths` whose module name is among `words`: a file's name without .py, or, for a
    package's __init__.py, its directory's name. Pure on its arguments (a path need not exist): the step of
    _resolver_targets its plants run on."""
    out = set()
    for p in paths:
        base = os.path.basename(p)
        stem = os.path.basename(os.path.dirname(os.path.abspath(p))) if base == "__init__.py" else base[:-3]
        if stem in words:
            out.add(os.path.realpath(p))
    return frozenset(out)


def _tests_module_path(modname, root, level=0):
    """The file under `root` a `from <modname> import ...` or `import <modname>` names, or None: `tests.X`, a bare `X`
    (tests/ is on sys.path in every test module) and a relative `from . import X` all resolve against `root`; anything
    else is the standard library or a product module, outside the scan."""
    if not modname:
        return None
    parts = modname.split(".")
    if level == 0 and parts[0] == "tests":
        parts = parts[1:]
    if not parts or not all(parts):
        return None
    base = os.path.join(root, *parts)
    for cand in (base + ".py", os.path.join(base, "__init__.py")):
        if os.path.isfile(cand):
            return os.path.realpath(cand)
    return None


def _imports_of(tree, root):
    """({local name: (path, attribute)}, [star-imported paths]) for every import at import time that names a module under
    `root`: `import M [as m]` and `from . import M` bind the module (attribute None), under its alias or, with none, its
    own spelling, dotted when it is (`import tests.helper` binds "tests.helper", the spelling a call then uses); `from M
    import f [as g]` binds f, a def or class of M; `from M import *` puts M's path in the second value, and _resolve reads a
    name the module does not bind itself through it. The dotted and the star shapes are read since the third commit of
    2026-09-22 (the verifier found both passing the resolver silently)."""
    out, stars = {}, []
    for node, _nested in _import_time_nodes(tree.body):
        for n in ast.walk(node):
            if isinstance(n, ast.Import):
                for a in n.names:
                    path = _tests_module_path(a.name, root)
                    if path:
                        out[a.asname or a.name] = (path, None)
            elif isinstance(n, ast.ImportFrom):
                path = _tests_module_path(n.module, root, n.level)
                for a in n.names:
                    if a.name == "*":
                        if path:
                            stars.append(path)
                    elif path:
                        out[a.asname or a.name] = (path, a.name)
                    else:
                        sub = _tests_module_path(("%s.%s" % (n.module, a.name)) if n.module else a.name, root, n.level)
                        if sub:
                            out[a.asname or a.name] = (sub, None)
    return out, stars


def _every_statement(body):
    """Every statement under `body`, in any scope (def and class bodies, block bodies, handlers, cases), itself included:
    a def, a class and a `global` are statements, and no expression holds one, so this reaches each of them without
    walking the expressions."""
    todo = [body]
    while todo:             # loop-ok: bounded by the statements under `body`
        for s in todo.pop():
            yield s
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                todo.append(s.body)
            elif isinstance(s, _COMPOUND):
                todo.extend(_block_bodies(s))


def _call_roles(tree):
    """{id(node): role} for every bare name or attribute (no parentheses) that Python CALLS where it stands, anywhere in
    `tree`: a decorator ("decorator": `@_arm` calls `_arm(fn)`), a class's `metaclass=` value ("metaclass": creating the
    class runs M.__prepare__, then calls M, which runs M.__new__ and M.__init__; M.__call__ is read beside them, the safe
    side) and a class's base ("base": NOT a call; creating the subclass runs the base's __init_subclass__). Any other
    bare name, in a base expression's arguments, a default, an if test, a with item, a for iterable, a for or with
    target or an except type, is a reference or a store and not a call (the reviewer's ruling of round 1 on fork PR
    #894: the resolver read every bare name handed in as a call, so a base's __init__ counted as the class statement's
    write and a def named in a default was reported as called)."""
    roles = {}
    for n in _every_statement(tree.body):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            roles.update((id(d), "decorator") for d in n.decorator_list if isinstance(d, (ast.Name, ast.Attribute)))
        if isinstance(n, ast.ClassDef):
            roles.update((id(b), "base") for b in n.bases if isinstance(b, (ast.Name, ast.Attribute)))
            roles.update((id(k.value), "metaclass") for k in n.keywords
                         if k.arg == "metaclass" and isinstance(k.value, (ast.Name, ast.Attribute)))
    return roles


def _module_record(tree, where, root):
    imports, stars = _imports_of(tree, root)
    defs, classes = _import_time_defs(tree.body)
    return _Module(where, tree, _EnvNames(tree), defs, classes, imports, stars, root, _call_roles(tree))


def _module_at(path, root):
    """The _Module for the file `path`, built once per (path, root) in this module's run over the census's own tree of the
    file (_own_tree: the tree the census loop reads for the same file, parsed once in the run) and held in the _Census
    ("modules") until tearDownModule's release. The tree is read-only here as everywhere: _module_record keeps its
    per-node data in side tables keyed by id(node)."""
    modules = _held()["modules"]
    hit = modules.get((path, root))
    if hit is None:
        hit = modules[(path, root)] = _module_record(_own_tree(path), os.path.relpath(path, root), root)
    return hit


def _dotted(node):
    """["tests", "helper", "arm"] for the attribute chain `tests.helper.arm` on a name; None for anything else in the chain
    (a call, a subscript, a literal)."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return parts[::-1]
    return None


_ROLE_METHODS = {"call": ("__new__", "__init__"), "decorator": ("__new__", "__init__"),
                 "metaclass": ("__prepare__", "__new__", "__call__", "__init__"), "base": ("__init_subclass__",)}
#   the methods of a CLASS that run when a name resolved to it is called (an instantiation, or a class used as a
#   decorator), used as a metaclass, or subclassed; a DEF runs itself when called, as a decorator or as a metaclass,
#   and nothing when named as a base

_CALL_DEPTH_CAP = 40
#   the longest chain of calls the resolver follows from one call at import; a chain longer than it raises
#   (_CallChainAtTheCap), naming the chain, and a cycle is cut by the per-chain seen set before it. The cap was six until
#   round 2 of fork PR #894, a silent cut (the reviewer's ruling of round 1: 33 callees in the tree sat past it, none
#   reaching a write), and a cap of 40 derives the same census. THE FIGURE, stated here and nowhere else in the tree: the
#   deepest chain the census follows over tests/ was 16 calls, from tests/test_thread_stop_census.py's __main__ block,
#   derived at the fix of the verifier's findings on round 2 of fork PR #894 on 3.10 and 3.12, with the memo and with a
#   memo that stores nothing (`python -m tests.test_hermetic_kernel_postal --deepest-chain` prints it, from
#   _deepest_call_chain). It is not pinned: it moves with the tree, as the census counts do. What holds the cap above
#   every chain in the tree is the census pin itself, which a chain at the cap turns red by raising.


class _CallChainAtTheCap(UnreadableEnvWrite):
    """A call chain from import longer than _CALL_DEPTH_CAP calls: raised with the whole chain named, never cut silently."""


def _as_list(v):
    return [] if v is None else (list(v) if isinstance(v, list) else [v])


def _is_classmethod(fn):
    return any(isinstance(d, ast.Name) and d.id == "classmethod" for d in fn.decorator_list)


def _in_tables(target, defs, classes, rest, methods, defs_ok):
    """[(module, FunctionDef, bound)] for the name chain `rest` in one scope of the module `target` (`defs` and `classes`:
    {name: [node, ...]}): one name, a def (when `defs_ok`) or a class, whose `methods` chains run (_ROLE_METHODS); two
    names, a method on a class. `bound` is how many leading parameters the call binds itself (the self or cls a method
    receives), so _environ_params maps the call's own arguments to the parameters after them."""
    out = []
    if len(rest) == 1:
        if defs_ok:
            out += [(target, fn, 0) for fn in defs.get(rest[0], [])]
        for cls in classes.get(rest[0], []):
            for m in methods:
                out += [(target, fn, 1) for fn in _method_chain(cls, m, target.classes)]
    elif len(rest) == 2:
        for cls in classes.get(rest[0], []):
            out += [(target, fn, 1 if _is_classmethod(fn) else 0) for fn in _method_chain(cls, rest[1], target.classes)]
    return out


def _resolve(mod, parts, methods=_ROLE_METHODS["call"], scope=None, defs_ok=True, _hops=frozenset()):
    """[(module, FunctionDef, bound)], one entry per callee, for the dotted chain `parts` (_dotted) called in `mod` (in
    the class body `scope`, or at module level): EVERY binding the name has, not an order-aware pick (the reviewer's
    ruling of round 1 on fork PR #894: a def shadowed by a later import of the same name read as the def alone, and a def
    under `if` or `try` or in a class body as nothing). The class body's own defs and classes when `scope` is one; the
    module's, from every import-time block (_import_time_defs); the LONGEST prefix of the chain an import binds (`floor`,
    `_h`, `Seam`, `tests.helper`), the rest of the chain resolved in that module the same way, so a name the helper
    re-exports (`from helper2 import floor` where helper2 imported it) is followed to its def; and, for a bare name or a
    `Class.method`, every star-imported module (the module's `__all__` not consulted, so a private name reads as bound,
    the safe side). `methods` names the chains of a class that run (_ROLE_METHODS); `defs_ok` is False for a base, which
    is not called. `_hops`, the modules this resolution has entered, cuts a re-export cycle."""
    out = []
    tables = ([_import_time_defs(scope.body)] if scope is not None else []) + [(mod.defs, mod.classes)]
    for defs, classes in tables:
        out += _in_tables(mod, defs, classes, parts, methods, defs_ok)
    for i in range(len(parts), 0, -1):
        base = ".".join(parts[:i])
        if base in mod.imports:
            path, attr = mod.imports[base]
            rest = ([attr] if attr is not None else []) + parts[i:]
            if rest and path not in _hops:
                out += _resolve(_module_at(path, mod.root), rest, methods, None, defs_ok, _hops | {path})
            break
    if len(parts) <= 2:
        for path in mod.stars:
            if path not in _hops:
                out += _resolve(_module_at(path, mod.root), parts, methods, None, defs_ok, _hops | {path})
    seen, unique = set(), []
    for target, fn, bound in out:
        key = (target.where, fn.name, fn.lineno, bound)
        if key not in seen:
            seen.add(key)
            unique.append((target, fn, bound))
    return unique


def _environ_params(fn, call, bound, names, target, where):
    """The parameters of `fn` that `call` binds to the environment mapping (the reviewer's ruling of round 1 on fork PR
    #894, where `def put(env): env[K] = v` called as `put(os.environ)` and `def put(env=os.environ)` called as `put()`
    passed silently): a positional argument that is the mapping (as `names`, the caller's scope, reads it), by position
    after the `bound` parameters the call binds itself; a keyword argument that is, by name; and a parameter the call
    does not pass whose default is the mapping (as `target`'s names read it: a default is evaluated where the def
    stands). The mapping passed where no parameter takes it by name (into *args or **kwargs, or through a * or ** spread)
    is loud: the scan cannot say what the callee does with it. `call` is None for a callee that receives no argument of
    the caller's (a decorator, a metaclass, a base's __init_subclass__)."""
    a = fn.args
    positional = list(a.posonlyargs) + list(a.args)
    takes = positional[bound:]
    out, passed = set(), set()
    named = {p.arg for p in list(a.args) + list(a.kwonlyargs)}

    def loud(how):
        return UnreadableEnvWrite("the environment mapping is passed %s at line %d of %s (%s): the scan cannot read what "
                                  "the callee does with it" % (how, call.lineno, where, ast.unparse(call)))

    if isinstance(call, ast.Call):
        for i, arg in enumerate(call.args):
            if isinstance(arg, ast.Starred):
                if any(names.is_environ(n) for n in ast.walk(arg.value)):
                    raise loud("inside a * argument")
                takes = []          # the positions after a star are not known
                continue
            if i < len(takes):
                passed.add(takes[i].arg)
                if names.is_environ(arg):
                    out.add(takes[i].arg)
            elif names.is_environ(arg):
                raise loud("into *args of %s()" % fn.name)
        for kw in call.keywords:
            if kw.arg is None:
                if any(names.is_environ(n) for n in ast.walk(kw.value)):
                    raise loud("inside a ** argument")
                continue
            passed.add(kw.arg)
            if names.is_environ(kw.value):
                if kw.arg not in named:
                    raise loud("into **kwargs of %s()" % fn.name)
                out.add(kw.arg)
    for p, d in zip(positional[len(positional) - len(a.defaults):], a.defaults):
        if p.arg not in passed and target.names.is_environ(d):
            out.add(p.arg)
    for p, d in zip(a.kwonlyargs, a.kw_defaults):
        if d is not None and p.arg not in passed and target.names.is_environ(d):
            out.add(p.arg)
    return frozenset(out)


def _reached_writes(node, mod, seen=frozenset(), depth=0, names=None, scope=None, origin=None, chain=(), memo=None):
    """Every environment write the import-time code `node` of `mod` reaches THROUGH A CALL the scan can resolve
    (_resolve), as _Write records at the CALL's line with `via` naming the callee, where it is defined and the write's
    own line, recursively through the callee's own calls. What counts as a call: a Call node; a bare name or attribute
    only where Python calls it, as a decorator or a `metaclass=` value, and a base named bare, whose __init_subclass__
    chain runs (_call_roles; the reviewer's ruling of round 1 on fork PR #894). The calls inside a base or keyword
    expression are Call nodes and followed. `names` is the scope the call's arguments are read in (the module's, or a
    callee's own with the parameters its call bound to the mapping, _environ_params); `scope` is the class body a
    module-level node runs in. A callee is read once per chain (a cycle is cut there), and a chain longer than
    _CALL_DEPTH_CAP calls raises naming the chain rather than being cut. A write in a callee that the scan cannot read
    is loud, naming the callee's line and the call site. `memo` ({} per module, _module_level_env_write_records) holds
    what a callee reached for the parameters its call bound, reused where the reading did not depend on the chain above
    it (_reach)."""
    return _reach(node, mod, seen, depth, names, scope, origin, chain, {} if memo is None else memo)[0]


def _reach(node, mod, seen, depth, names, scope, origin, chain, memo):
    """(records, height, cuts, visited) for _reached_writes: `height` is the longest chain of callees read under `node`,
    `cuts` the keys in `seen` (the callees above) a cycle was cut at under it, and `visited` the keys of every callee read
    under it. A callee's reading is memoized by (id of its def, the parameters bound to the mapping), with the height and
    the callees it read, when nothing under it was cut against a callee above it; it is reused only where none of the
    callees it read is above it now (a fresh reading would cut the cycle there: the verifier's finding on round 2 of fork
    PR #894, where `_a -> _b -> _c -> _a`, read first from `_b`, was reused under `_a` and recorded `_a`'s write a second
    time through the chain back to `_a`) and where the stored height still fits under the cap from the depth it is
    reached at. Under those three conditions a fresh reading makes every seen-set check the same way, so the memo
    changes neither what is read nor where the cap raises. The cap and cycle pin plants each condition and compares the
    records with a reading whose memo stores nothing; over the whole tree the two were byte-identical when measured at
    the fix of the verifier's findings on round 2 of fork PR #894 (not pinned: a whole-tree reading costs a census)."""
    names = mod.names if names is None else names
    out, height, cuts, visited = [], 0, set(), set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            role, parts = "call", _dotted(n.func)
        elif isinstance(n, (ast.Name, ast.Attribute)) and id(n) in mod.roles:
            role, parts = mod.roles[id(n)], _dotted(n)
        else:
            continue
        if not parts:
            continue
        start = origin or (mod.where, n.lineno)
        for target, fn, bound in _resolve(mod, parts, _ROLE_METHODS[role], scope, defs_ok=role != "base"):
            key = (target.where, fn.name, fn.lineno)
            if key in seen:
                cuts.add(key)
                continue
            label = "%s() at %s:%d" % (fn.name, target.where, fn.lineno)
            if depth >= _CALL_DEPTH_CAP:
                raise _CallChainAtTheCap("the call chain reached at import from %s:%d is longer than the resolver's cap of %d "
                                         "calls (_CALL_DEPTH_CAP): %s" % (start[0], start[1], _CALL_DEPTH_CAP,
                                                                           " -> ".join(chain + (label,))))
            try:
                params = _environ_params(fn, n if role == "call" else None, bound, names, target, mod.where)
                hit = memo.get((id(fn), params))
                if hit is not None and depth + hit[1] < _CALL_DEPTH_CAP and hit[2].isdisjoint(seen):
                    inner, sub_height, sub_visited = hit
                else:
                    inner_names = target.names.within(fn, params)
                    sub, sub_height, sub_cuts, sub_visited = _reach(fn, target, seen | {key}, depth + 1, inner_names, None,
                                                                    start, chain + (label,), memo)
                    inner = _writes_in_scope(fn, inner_names, target.where) + sub
                    sub_cuts.discard(key)
                    if not sub_cuts:
                        memo[(id(fn), params)] = (inner, sub_height, frozenset(sub_visited))
                    cuts |= sub_cuts
            except _CallChainAtTheCap:
                raise
            except UnreadableEnvWrite as e:
                raise UnreadableEnvWrite("%s; reached at import from %s:%d through %s" % (e, mod.where, n.lineno, label)) from None
            height = max(height, sub_height + 1)
            visited.add(key)
            visited |= sub_visited
            for w in inner:
                via = ("%s -> %s" % (label, w.via)) if w.via else ("%s, the write at line %d" % (label, w.line))
                out.append(w._replace(line=n.lineno, via=via))
    return out, height, cuts, visited


def _module_level_env_write_records(tree, where="<module>", root=None):
    """Every environment write the module makes at import, as (_Write, nested) pairs: `nested` is True for a write not
    directly in the module body (inside a module-level if/for/while/with/try body, a class body, a header; a bare grep
    at column 0 misses those). In every shape _env_write_records reads, in every node _import_time_nodes yields, plus
    every write reached through a call at import the scan can resolve (_reached_writes; at the call's line, `via`
    set; a call in a class body resolved against that body's defs too); `where` names the file in the loud message for
    a write the scan cannot read; `root` is where the module's tests-local imports resolve (tests/ by default)."""
    mod = _module_record(tree, where, HERE if root is None else root)
    out, memo = [], {}
    for node, nested, scope in _import_time_nodes_scoped(tree.body):
        out += [(w, nested) for w in _env_write_records(node, mod.names, where)]
        out += [(w, nested) for w in _reached_writes(node, mod, scope=scope, memo=memo)]
    return out


def _deepest_call_chain(paths=None):
    """(calls, "module:line") for the longest chain of calls the resolver follows from one call at import over `paths`
    (every .py under tests/ by default): the figure _CALL_DEPTH_CAP is set above. Printed by
    `python -m tests.test_hermetic_kernel_postal --deepest-chain`."""
    best = (0, "")
    for path in (_tests_tree_paths() if paths is None else list(paths)):
        rel = os.path.relpath(path, HERE)
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read(), filename=path)
        mod, memo = _module_record(tree, rel, HERE), {}
        for node, _nested, scope in _import_time_nodes_scoped(tree.body):
            height = _reach(node, mod, frozenset(), 0, None, scope, None, (), memo)[1]
            line = getattr(node, "lineno", 0)
            if height > best[0]:
                best = (height, "%s:%d" % (rel, line))
    return best


def _module_level_env_writes(tree, where="<module>", root=None):
    """The environment keys the module writes at import, in every shape _env_writes reads, in any node
    _import_time_nodes yields, through any call _reached_writes resolves; `where` names the file in the loud message for
    a write the scan cannot read."""
    return {w.key for w, _nested in _module_level_env_write_records(tree, where, root)}


def _outside_plant(src, files=None, hook=None):
    """One plant of a shape outside the scan: the planted module's source, the helper files beside it (a path relative to
    the planted module's directory; "../product/..." for product code, outside the directory the scan resolves imports
    in) and, for code that runs after the import, the statement that runs it; "{key}" stands for the name it writes."""
    return {"src": src, "files": files or {}, "hook": hook}


_OUTSIDE_THE_SCAN = {
    "product-code": [_outside_plant("import importlib.util, os\n"
                            "_spec = importlib.util.spec_from_file_location('prod_writer', os.path.join(os.path.dirname("
                            "os.path.abspath(__file__)), '..', 'product', 'prod_writer.py'))\n"
                            "_prod = importlib.util.module_from_spec(_spec)\n_spec.loader.exec_module(_prod)\n_prod.arm()\n",
                            {"../product/prod_writer.py": "import os\ndef arm():\n    os.environ['{key}'] = '1'\n"})],
    "stdlib-callee": [_outside_plant("import operator, os\noperator.setitem(os.environ, '{key}', '1')\n")],
    "instance-method": [_outside_plant("import os\nclass _Seam:\n    def arm(self):\n        os.environ['{key}'] = '1'\n_Seam().arm()\n")],
    "helper-lambda": [_outside_plant("from h_lambda import ARM\nARM()\n",
                             {"h_lambda.py": "import os\nARM = lambda: os.environ.__setitem__('{key}', '1')\n"})],
    "call-result": [_outside_plant("from h_factory import make\narm = make()\narm()\n",
                           {"h_factory.py": "import os\ndef _arm():\n    os.environ['{key}'] = '1'\ndef make():\n    return _arm\n"}),
                    _outside_plant("from h_basefactory import make_base\nclass _K(make_base()):\n    pass\n",
                           {"h_basefactory.py": "import os\nclass _B:\n    def __init_subclass__(cls, **kw):\n"
                                                "        os.environ['{key}'] = '1'\ndef make_base():\n    return _B\n"})],
    "exec-eval": [_outside_plant("import os\nexec(\"os.environ['{key}'] = '1'\")\n"),
                  _outside_plant("import os\neval(\"os.environ.update({key}='1')\")\n"),
                  # the verifier's finding on round 2's thirteenth commit: a binding or a mutation the string makes
                  _outside_plant("import os\nfor k in ('ROMP_PLANTED_DECOY',):\n    pass\nexec(\"k = '{key}'\")\nos.environ[k] = '1'\n"),
                  _outside_plant("import os\nD = {'ROMP_PLANTED_DECOY': '1'}\nexec(\"D['{key}'] = '1'\")\nos.environ.update(D)\n"),
                  # the verifier's finding on round 2's fourteenth commit: that binding (a walrus) and mutation by eval
                  _outside_plant("import os\nfor k in ('ROMP_PLANTED_DECOY',):\n    pass\neval(\"(k := '{key}')\")\nos.environ[k] = '1'\n"),
                  _outside_plant("import os\nD = {'ROMP_PLANTED_DECOY': '1'}\neval(\"D.update({key}='1')\")\nos.environ.update(D)\n")],
    "inherited-metaclass": [_outside_plant("from h_meta import B\nclass _K(B):\n    pass\n",
                                   {"h_meta.py": "import os\nclass M(type):\n    def __init__(cls, *a):\n"
                                                 "        if cls.__name__ == '_K':\n            os.environ['{key}'] = '1'\n"
                                                 "class B(metaclass=M):\n    pass\n"})],
    "inherited-method": [_outside_plant("from h_base import Base\nclass _K(Base):\n    pass\n_K()\n",
                                {"h_base.py": "import os\nclass Base:\n    def __init__(self):\n        os.environ['{key}'] = '1'\n"})],
    "held-otherwise": [_outside_plant("import os, types\nns = types.SimpleNamespace()\nns.env = os.environ\nns.env['{key}'] = '1'\n"),
                       _outside_plant("import os\n[os.environ][0]['{key}'] = '1'\n"),
                       _outside_plant("import os\nenv, _x = os.environ, None\nenv['{key}'] = '1'\n"),
                       # the fix of the verifier's findings on round 2 of fork PR #894 (an alias claim wider than the read)
                       _outside_plant("import os\nenv: dict = os.environ\nenv['{key}'] = '1'\n"),
                       _outside_plant("import os\n_a = env = os.environ\nenv['{key}'] = '1'\n"),
                       _outside_plant("import os\nif (env := os.environ) is not None:\n    env['{key}'] = '1'\n"),
                       _outside_plant("import os\nfor env in (os.environ,):\n    env['{key}'] = '1'\n"),
                       _outside_plant("import contextlib, os\nwith contextlib.nullcontext(os.environ) as env:\n    env['{key}'] = '1'\n"),
                       _outside_plant("from h_env import ENV\nENV['{key}'] = '1'\n", {"h_env.py": "import os\nENV = os.environ\n"}),
                       _outside_plant("from h_env_star import *\nENV['{key}'] = '1'\n", {"h_env_star.py": "import os\nENV = os.environ\n"}),
                       _outside_plant("import os\ngetattr(os, 'environ')['{key}'] = '1'\n"),
                       _outside_plant("import sys\nsys.modules['os'].environ['{key}'] = '1'\n")],
    "from-os-putenv": [_outside_plant("from os import putenv\nputenv('{key}', '1')\n"),
                       _outside_plant("from os import *\nputenv('{key}', '1')\n")],
    # the verifier's findings on round 2 of fork PR #894: shapes missed silently with none of them named here
    "lambda-parameter": [_outside_plant("import os\n_arm = lambda env=os.environ: env.__setitem__('{key}', '1')\n_arm()\n"),
                         _outside_plant("import os\n(lambda env: env.update({key}='1'))(os.environ)\n")],
    # the verifier's finding on round 2's thirteenth commit: the lambda's class, a def or class bound inside a function
    "nested-def-parameter": [_outside_plant("import os\ndef _o():\n    def _i(env):\n        env['{key}'] = '1'\n    _i(os.environ)\n_o()\n"),
                             _outside_plant("import os\ndef _o():\n    def _i(env):\n        env['{key}'] = '1'\n"
                                            "    _i(env=os.environ)\n_o()\n"),
                             _outside_plant("import os\ndef _o():\n    def _i(env=os.environ):\n        env['{key}'] = '1'\n    _i()\n_o()\n"),
                             _outside_plant("import os\ndef _o():\n    class _N:\n        def __init__(self, env):\n"
                                            "            env['{key}'] = '1'\n    _N(os.environ)\n_o()\n"),
                             _outside_plant("import os\nclass _C:\n    @staticmethod\n    def m():\n        def _i(env):\n"
                                            "            env['{key}'] = '1'\n        _i(os.environ)\n_C.m()\n")],
    "aliased-callee": [_outside_plant("import os\ndef _floor():\n    os.environ['{key}'] = '1'\n_g = _floor\n_g()\n"),
                       _outside_plant("import os\nclass _Seam:\n    def __init__(self):\n        os.environ['{key}'] = '1'\n"
                                      "_A = _Seam\n_A()\n"),
                       _outside_plant("import os\ndef _floor():\n    os.environ['{key}'] = '1'\n[_floor][0]()\n"),
                       _outside_plant("import os\ndef _floor():\n    os.environ['{key}'] = '1'\n(_floor if True else None)()\n"),
                       _outside_plant("import os, sys\ndef _floor():\n    os.environ['{key}'] = '1'\n"
                                      "getattr(sys.modules[__name__], '_floor')()\n"),
                       _outside_plant("import functools, os\ndef _floor():\n    os.environ['{key}'] = '1'\n"
                                      "functools.partial(_floor)()\n"),
                       _outside_plant("import os\ndef _floor():\n    os.environ['{key}'] = '1'\n_floor.__call__()\n")],
    "callback": [_outside_plant("import os\ndef _w(x):\n    os.environ['{key}'] = '1'\nlist(map(_w, [1]))\n"),
                 _outside_plant("import os\ndef _w(x):\n    os.environ['{key}'] = '1'\n    return x\nsorted([1, 2], key=_w)\n"),
                 _outside_plant("import os, threading\ndef _w():\n    os.environ['{key}'] = '1'\n"
                                "_t = threading.Thread(target=_w)\n_t.start()\n_t.join()\n"),
                 _outside_plant("import asyncio, os\nasync def _f():\n    os.environ['{key}'] = '1'\nasyncio.run(_f())\n")],
    "protocol-hook": [_outside_plant("import os\nclass _C:\n    def __enter__(self):\n        os.environ['{key}'] = '1'\n"
                                     "    def __exit__(self, *a):\n        pass\nwith _C():\n    pass\n"),
                      _outside_plant("import os\nclass _D:\n    def __set_name__(self, owner, name):\n"
                                     "        os.environ['{key}'] = '1'\nclass _K:\n    x = _D()\n"),
                      _outside_plant("import os\nclass _D:\n    def __get__(self, obj, owner):\n        os.environ['{key}'] = '1'\n"
                                     "class _K:\n    x = _D()\n_K.x\n"),
                      _outside_plant("import os\nclass _S:\n    @property\n    def p(self):\n        os.environ['{key}'] = '1'\n"
                                     "_S().p\n"),
                      _outside_plant("import os\nclass _B:\n    def __class_getitem__(cls, x):\n        os.environ['{key}'] = '1'\n"
                                     "        return cls\n_A = _B[int]\n"),
                      _outside_plant("import os\nclass _B:\n    def __class_getitem__(cls, x):\n        return cls\n"
                                     "    def __init_subclass__(cls, **kw):\n        os.environ['{key}'] = '1'\n"
                                     "class _K(_B[int]):\n    pass\n"),
                      _outside_plant("import os\nclass _B:\n    def __init_subclass__(cls, **kw):\n        os.environ['{key}'] = '1'\n"
                                     "class _E:\n    def __mro_entries__(self, bases):\n        return (_B,)\n"
                                     "class _K(_E()):\n    pass\n"),
                      _outside_plant("import os\nclass _It:\n    def __iter__(self):\n        os.environ['{key}'] = '1'\n"
                                     "        return iter(())\nfor _x in _It():\n    pass\n"),
                      _outside_plant("import os\nclass _C:\n    def __add__(self, other):\n        os.environ['{key}'] = '1'\n"
                                     "        return 0\n_s = _C() + 1\n"),
                      _outside_plant("import os\nclass _C:\n    def __bool__(self):\n        os.environ['{key}'] = '1'\n"
                                     "        return True\nif _C():\n    pass\n"),
                      _outside_plant("import os\nclass _C:\n    def __format__(self, spec):\n        os.environ['{key}'] = '1'\n"
                                     "        return ''\n_t = f'{_C()}'\n"),
                      _outside_plant("import os\nclass _C:\n    def __del__(self):\n        os.environ['{key}'] = '1'\n_C()\n")],
    "namespace-rebinding": [_outside_plant("import os\nfor k in ('ROMP_PLANTED_DECOY',):\n    pass\nglobals()['k'] = '{key}'\n"
                                           "os.environ[k] = '1'\n"),
                            # the verifier's finding on round 2's thirteenth commit: the other namespace forms of a name
                            _outside_plant("import os\nfor k in ('ROMP_PLANTED_DECOY',):\n    pass\nvars()['k'] = '{key}'\n"
                                           "os.environ[k] = '1'\n"),
                            _outside_plant("import os, sys\nfor k in ('ROMP_PLANTED_DECOY',):\n    pass\n"
                                           "sys.modules[__name__].k = '{key}'\nos.environ[k] = '1'\n"),
                            _outside_plant("import os, sys\nfor k in ('ROMP_PLANTED_DECOY',):\n    pass\n"
                                           "setattr(sys.modules[__name__], 'k', '{key}')\nos.environ[k] = '1'\n"),
                            _outside_plant("import os\nD = {'ROMP_PLANTED_DECOY': '1'}\nglobals()['D']['{key}'] = '1'\n"
                                           "os.environ.update(D)\n"),
                            _outside_plant("import os\nD = {'ROMP_PLANTED_DECOY': '1'}\nvars()['D']['{key}'] = '1'\n"
                                           "os.environ.update(D)\n"),
                            _outside_plant("import os, sys\nD = {'ROMP_PLANTED_DECOY': '1'}\nsys.modules[__name__].D['{key}'] = '1'\n"
                                           "os.environ.update(D)\n"),
                            _outside_plant("import os\nD = {'ROMP_PLANTED_DECOY': '1'}\nimport h_back\nos.environ.update(D)\n",
                                           {"h_back.py": "import sys\nfor _n, _m in list(sys.modules.items()):\n"
                                                         "    if _n.startswith('planted_'):\n        _m.D['{key}'] = '1'\n"})],
    "bound-method": [_outside_plant("import os\n_set = os.environ.__setitem__\n_set('{key}', '1')\n"),
                     _outside_plant("import os\ngetattr(os.environ, 'update')({key}='1')\n"),
                     _outside_plant("import functools, os\nfunctools.partial(os.environ.__setitem__, '{key}')('1')\n")],
    "posix-putenv": [_outside_plant("import posix\nposix.putenv('{key}', '1')\n")],
    "unbound-update": [_outside_plant("import os\nfrom collections.abc import MutableMapping\n"
                              "MutableMapping.update(os.environ, {'{key}': '1'})\n"),
                       _outside_plant("import os\nfrom collections.abc import MutableMapping\n"
                              "MutableMapping.setdefault(os.environ, '{key}', '1')\n")],
    "after-import": [_outside_plant("import os\ndef setUpModule():\n    os.environ['{key}'] = '1'\n", hook="setUpModule()"),
                     _outside_plant("import os, unittest\nclass _T(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n"
                            "        os.environ['{key}'] = '1'\n", hook="_T.setUpClass()"),
                     _outside_plant("import os, pytest\n@pytest.fixture(scope='module')\ndef _f():\n    os.environ['{key}'] = '1'\n"
                            "    yield\n", hook="next(_f.__wrapped__())")],
}
#   the plants of the shapes the comment above _Module names as OUTSIDE the scan, by the comment's tags; run by
#   test_every_shape_named_outside_the_scan_writes_when_run_and_the_scan_reads_none

_OUTSIDE_RUNNER = textwrap.dedent("""\
    import ctypes, json, runpy, sys
    libc = ctypes.CDLL(None)
    libc.getenv.restype = ctypes.c_char_p
    out = {}
    for pid, root, path, key, hook in json.loads(sys.argv[1]):
        sys.path.insert(0, root)
        try:
            ns = runpy.run_path(path, run_name="planted_%s" % pid)
            at_import = libc.getenv(key.encode()) is not None
            if hook:
                exec(hook, ns)
            out[pid] = [at_import, libc.getenv(key.encode()) is not None, ""]
        except BaseException as e:
            out[pid] = [False, False, "%s: %s" % (type(e).__name__, e)]
        finally:
            sys.path.remove(root)
    print(json.dumps(out))
    """)
#   runs every plant in one child interpreter, each from its own directory, and reports whether its name is set in the
#   process environment (read through the C library, which os.putenv and posix.putenv write and os.environ does not
#   mirror) after its import and after its hook


def _tests_tree_walk(root=None):
    """Every .py under tests/ that an os.walk finds, recursively (fixtures/ included), sorted: the module's own population,
    which _tests_tree_paths checks its glob against and the census pin compares the census's parsed count with, by
    equality. `root` walks a synthetic tree instead (the target scan's plants)."""
    return sorted(os.path.join(d, f) for d, _, fs in os.walk(HERE if root is None else root) for f in fs if f.endswith(".py"))


def _tests_tree_paths():
    """Every .py under tests/, recursively (fixtures/ included), sorted; the glob is checked against an independent
    os.walk (_tests_tree_walk) so no file is silently unscanned (review round 1, 2026-09-18)."""
    paths = sorted(glob.glob(os.path.join(HERE, "**", "*.py"), recursive=True))
    if paths != _tests_tree_walk():
        raise AssertionError("the glob walks every .py under tests/, subdirectories included: the set an os.walk finds")
    return paths


_Record = collections.namedtuple("_Record", "module line shape value nested resolved via")
#   one module-level write in the tree: the writer MODULE (relative to tests/), its LINE (of the call, for a write reached
#   through one), the SHAPE, the VALUE text (ast.unparse of the expression, or "" where the shape has none), whether the
#   statement is NESTED in a block or a class body, the value RESOLVED through the names bound once at import (the same
#   text as VALUE where nothing substitutes) and VIA, "" for a write made where it stands, else the callee chain


def _record(module, w, nested):
    return _Record(module, w.line, w.shape, ast.unparse(w.value) if w.value is not None else "", nested, w.resolved, w.via)


def _module_level_records(tree, module, root=None):
    """Every module-level write of `tree` as (name, _Record) pairs, `module` naming the file (relative to tests/)."""
    return [(w.key, _record(module, w, nested)) for w, nested in _module_level_env_write_records(tree, module, root)]


_CENSUS_BUILDS = collections.Counter()
#   path tuple -> the number of times _census_build ran for it in this module's run, counted by the build itself and
#   zeroed by setUpModule (under xdist a worker can set the module up more than once, each run dropping the held
#   derivation at its teardown and building again): the built-once pins read it, red under a build per read or per test


def _is_test_module(module):
    """True for a module whose file name is test_*.py (fork PR #871's glob; every test_*.py under tests/ is at the top
    level today, so the name and the top-level glob select the same files)."""
    base = os.path.basename(module)
    return base.startswith("test_") and base.endswith(".py")


_Derivation = collections.namedtuple("_Derivation", "parsed counts records walks outlived born held_before parts_outlived")
#   what _census_build returns for a path tuple: PARSED, the modules (relative to tests/) that parsed, in order; COUNTS,
#   {name: {shape: count}}; RECORDS, {name: (_Record, ...)}; WALKS, {module: walks} (_walk_unit); OUTLIVED, the modules
#   whose tree was still alive right after the loop dropped its own reference to it, in order, read through a weak
#   reference taken just before the drop: the trees something else keeps (the census pin holds them equal to the files
#   its own reader derives, _import_line_named_files); BORN, for a build that drops a tree, {class name: count} of the
#   ast objects alive right after its loop that were not alive just before it, whatever holds them (_born, through
#   gc.get_objects(): the census pin holds it EQUAL to the node count, by class, of the trees of the files its own reader
#   derives, _tree_classes), None for a build that drops none; HELD_BEFORE, the realpaths whose tree the holder held
#   before the build, sorted (a tree held before is not born in it); PARTS_OUTLIVED, for a build over a
#   synthetic tree (_census_build's `root` given), the modules some node of whose tree was still alive right after the
#   loop dropped its own reference to it, in order, read through a weak reference to every leaf of the tree taken just
#   before the drop (_leaf_refs): the trees of which something keeps any node, the tree itself or one of its nodes; None for a
#   build over tests/ itself


_SHARED_NODE_TYPES = (ast.expr_context, ast.boolop, ast.operator, ast.unaryop, ast.cmpop)
#   the node types whose instances the parser shares with every tree in the process (one Load, one Add, ...), made by
#   the ast module when it is imported: left out of a tree's count (_tree_classes), which would count one at every place
#   the tree uses it and none of which a build makes


def _ast_nodes_alive():
    """Every ast object alive in the process (an instance of ast.AST), as a list, read through gc.get_objects(), which
    lists every object the collector tracks (every ast object is one) and changes no collector state (no collection, no
    freeze, no threshold); an object frozen before the read is not listed, and the census freezes none. The drop's pin
    by live objects reads it just before the census loop and holds the list until its read after the loop
    (_census_build, _born)."""
    return [o for o in gc.get_objects() if isinstance(o, ast.AST)]


def _tree_classes(trees):
    """{class name: count} of the nodes of `trees` (each a node, walked by ast.walk) but the shared ones
    (_SHARED_NODE_TYPES, which the parser made before any tree and every tree points at): what the trees add to the ast
    objects alive, by class."""
    return dict(collections.Counter(type(n).__name__ for t in trees for n in ast.walk(t)
                                    if not isinstance(n, _SHARED_NODE_TYPES)))


def _born(before):
    """{class name: count} of the ast objects alive now (gc.get_objects(), every instance of ast.AST the collector
    tracks) that are not among `before` (_ast_nodes_alive, read earlier and held since, so none of it has died and no
    id among it was reused): the ast objects made since `before` was read and still alive, whatever holds them (a
    tree, a list, a record, a closure), by class. A read that changes no collector state (no collection, no freeze):
    THE DROP BY LIVE OBJECTS, the census build's `born`."""
    seen = {id(o) for o in before}
    return dict(collections.Counter(type(o).__name__ for o in gc.get_objects() if isinstance(o, ast.AST) and id(o) not in seen))


def _leaf_refs(tree):
    """A weak reference to every leaf of `tree`: each of its nodes but the shared ones (_SHARED_NODE_TYPES) that has no
    child node but shared ones, reached through ast.iter_child_nodes. Every node of the tree reaches a leaf through its
    own fields, so any node kept alive keeps a leaf alive: after the tree is dropped, a leaf's weak reference alive means
    something keeps a part of the tree (that leaf, or a node or a list above it), and every one dead means no node of
    the tree is alive. Read-only: the walk reads each node's fields and writes nothing on a node. What it does not read:
    a node's attribute dict or a field's value (a string, a number) kept without the node, which is not a node."""
    out, todo = [], [tree]
    while todo:     # loop-ok: bounded by the nodes of the tree
        n = todo.pop()
        children = [c for c in ast.iter_child_nodes(n) if not isinstance(c, _SHARED_NODE_TYPES)]
        if children:
            todo.extend(children)
        else:
            out.append(weakref.ref(n))
        n = children = None
    return out


def _walk_unit(tree, rel, walks):
    """One walk of a parsed file for the census (_module_level_records), counted in `walks` under the file: the per-unit
    walk count the census pin holds at 1 for every file, so a build that walks a file twice is red there. A walk made
    outside this function (a second ast.walk of a file by another road inside the build) is outside the count; the
    module's measured time at each head is the guard for that."""
    walks[rel] += 1
    return _module_level_records(tree, rel)


def _census_build(paths, root=None):
    """THE DERIVATION behind module_level_env_census, run once per path tuple per run of this module (_census_derivation
    holds what it returns): a _Derivation (parsed, counts, records, walks, outlived, born, held_before,
    parts_outlived), `parsed` the modules (relative to tests/) that parsed, in order. `root` stands in for tests/ in deciding which trees the loop drops and
    which files the resolver may read (_under_tests, _resolver_targets), for the plant of the drop's count, a synthetic
    tree run through the build; the census passes none. Each file is parsed by the census itself (_own_tree: once in
    this module's run, never through tests/parse_cache.py; the tree is read-only here), its tree held by the one owner
    until tearDownModule when the resolver may read the file later (_resolver_targets) or the file lies outside tests/,
    and dropped after its walk otherwise, and it is added to `parsed` inside the loop once it has parsed, so a path the
    loop skipped shows as a count short of the population (the census pin compares len(parsed) with the os.walk
    population by equality); a file that does not parse fails the census naming it; each parsed file is walked through
    _walk_unit, whose count per file the census pin holds at 1. THE DROP, observed: just before the loop drops its
    reference to a file's tree it takes a weak reference to it, and just after, a tree still alive is one something else
    keeps (`outlived`); the census pin holds the holder's trees of the files handed in, and `outlived`, equal to the
    files its own reader derives (_import_line_named_files, the census rule by code that runs none of this build's),
    so a loop that kept every tree (fork PR #850's E shape, which the measured rule did not ship), kept a dropped one by
    another road, or dropped it only when the next file's tree replaced it, and a _resolver_targets that names more or
    fewer files than the rule, is red there (the verifier's findings at round 2's nineteenth and twentieth commits of
    fork PR #894: the shape's defining property, the drop, had no pin, and then a pin that read _resolver_targets
    again, so a loop holding every tree, and then a _resolver_targets naming every file, left the module green). THE
    DROP BY LIVE OBJECTS (the reviewer's ruling of 2026-09-24 21:09Z on round 2 of fork PR #894, (2)), for a build that
    drops a tree: the ast objects alive are listed just before the loop (_ast_nodes_alive, the list held until the read
    after the loop, so none of it dies and no id among it is reused) and read again, by identity and by class, right
    after it (_born), before the build returns and long before teardown: `born`, the ast objects made in the build and
    still alive, whatever holds them. The census pin holds `born` EQUAL, by class, to the nodes of the trees of the
    files its own reader derives (_import_line_named_files, _tree_classes; the resolver targets derived, not the
    holder's list and not a figure), so a road that keeps any ast object of a dropped tree (its statement list on a
    list of its own, one statement, a node inside one), whatever holds it, which leaves the tree object to die and the
    weak reference with nothing to see, is red there, and so is a tree the holder keeps beyond the derived ones (the
    verifier's findings at round 2's thirty-first commit of fork PR #894, and the reviewer's ruling, which replaced the count of nodes beyond the
    holder's trees with this equality). A thread that makes ast objects while the loop runs and keeps them would count
    in `born` too; no thread of a test process does. A build that drops no tree reads nothing (None).
    EACH DROP, BY EVERY LEAF, for a build over a synthetic tree (`root` given): just before the loop drops its reference
    to a file's tree it takes a weak reference to every leaf of it (_leaf_refs), and just after, a leaf still alive
    means something keeps a part of that tree (`parts_outlived`), so a road that keeps part of a dropped tree past its
    drop and lets it go before the loop ends, which neither the weak reference to the tree nor the count after the loop
    sees, is named at the drop (the verifier's finding at round 2's thirty-second commit of fork PR #894: a loop that
    kept each dropped tree's statement list in a list of its own until the loop ended left the module green); the drop
    count's test runs the build so, and the census loop is the same code in every build. WHAT THE DROP'S READS DO NOT
    SEE: in the build over tests/ itself, a road that keeps a part of a dropped tree, not the tree, past its drop and
    lets it go before the loop ends, where it does so in that build alone (a road keyed on the population, not on the
    loop): the read by every leaf would cost that build about 4 s (measured at round 2's thirty-third commit of fork PR
    #894, three fresh processes each: 8.2 to 8.7 s without it and 12.8 to 13.1 s with it on Python 3.12, 11.3 to 11.4 s
    and 15.1 to 15.5 s on 3.10; 1.23 million leaves under tests/, a weak reference to each, and the collections their
    allocation starts), where the build over a synthetic tree runs the same loop in milliseconds; a node the walk
    makes itself (a fresh parse of an expression's text, _fresh) kept past its file's walk and let go before the loop
    ends, which is no part of the dropped tree (the count after the loop sees one kept past it); what _leaf_refs
    does not read; and, in every build, a piece of a node kept with no ast object of the tree: a node's attribute dict,
    a list of strings it holds, a field's string or number (the verifier's finding at round 2's thirty-fourth commit of
    fork PR #894: a road that kept each Name node's attribute dict in the build over tests/ left the module green). The
    count reads ast objects, the ruling's measure, and the weak references are to nodes, so neither sees such a piece;
    and what the build returns is made of the same kinds of object, dicts, strings and numbers, so a count of those
    would not tell a node's piece from the derivation's (planted as a witness: a walk that keeps each Name node's
    attribute dict to the build's end reads as nothing kept, in the drop's test).
    THE SINGLETON CHECK (tests/parse_cache.py's check_singletons, which parse_cache.derived ran around the build before
    the reviewer's ruling of 2026-09-24 took derived() out of this module): before the build (a writer that ran earlier;
    the build neither runs nor counts) and after it, on the returning road and on the raising road (the build itself
    wrote on a node the parser shares with every tree: the build is counted and nothing is held, so the next read builds
    again; a raising build's exception is the AssertionError's __cause__ when the singletons carry attributes, else it
    propagates as it was). No collector state is touched: no gc.freeze, gc.disable or gc.collect here or anywhere in the
    module (the same ruling; the freeze is process-global, and the other two walk every tracked object); the drop's two
    gc.get_objects() reads change none. What the build returns holds only strings, numbers, tuples, dicts and _Record
    tuples, no node and no cycle."""
    key = tuple(paths)
    where = "the census build over %s (tests/test_hermetic_kernel_postal.py)" % ("1 path" if len(key) == 1 else "%d paths" % len(key))
    PC.check_singletons("before %s: an earlier writer" % where)
    _CENSUS_BUILDS[key] += 1
    counts = collections.defaultdict(lambda: collections.defaultdict(int))
    records = collections.defaultdict(list)
    parsed, walks, outlived = [], collections.Counter(), []
    targets = _resolver_targets(key, root)
    trees = _held()["trees"]
    drops = any(_under_tests(p, root) and os.path.realpath(p) not in targets for p in key)
    before = _ast_nodes_alive() if drops else None      # held to the read below, so no object alive now dies in between
    held_before = tuple(sorted(trees))
    parts = None if root is None else []                # each drop read by every leaf: a synthetic tree's build alone
    try:
        for path in key:
            rel = os.path.relpath(path, HERE)
            try:
                tree = _own_tree(path, rel, hold=not _under_tests(path, root) or os.path.realpath(path) in targets)
            except (SyntaxError, ValueError) as e:        # ValueError: a null byte before 3.12, and a file that is not UTF-8
                raise AssertionError("the census could not parse %s (%s: %s): every file it is handed is read, or it fails "
                                     "naming the file" % (rel, type(e).__name__, e)) from e
            parsed.append(rel)
            for name, rec in _walk_unit(tree, rel, walks):
                counts[name][rec.shape] += 1
                records[name].append(rec)
            ref = weakref.ref(tree)
            leaves = () if parts is None else _leaf_refs(tree)
            tree = None         # an unheld tree is freed here, before the next file is parsed (_own_tree)
            if ref() is not None:
                outlived.append(rel)
            if parts is not None and any(leaf() is not None for leaf in leaves):
                parts.append(rel)
            leaves = None
    except BaseException as exc:
        found = PC.singleton_attributes()
        if found:
            raise AssertionError(PC.singleton_message("after %s raised %s: the build that just raised wrote them, or a thread "
                                                      "beside it" % (where, type(exc).__name__), found)) from exc
        raise
    born = None
    if before is not None:
        born = _born(before)
        before = None
    PC.check_singletons("after %s: the build itself wrote them, or a thread beside it" % where)
    return _Derivation(tuple(parsed), {k: dict(v) for k, v in counts.items()}, {k: tuple(v) for k, v in records.items()},
                       dict(walks), tuple(outlived), born, held_before, None if parts is None else tuple(parts))


def _census_derivation(paths=None):
    """The census's derivation over `paths` (every .py under tests/ when None) as _census_build returned it: held in the
    _Census ("derivations") from the first read in this module's run until tearDownModule's release, so every later
    read in the run is the same object and builds nothing. A build that raised is not held: the next read builds again.
    The holder never re-reads a file: a path censused and then rewritten in the same run is served the first derivation
    (no caller rewrites one; each plant is a fresh temporary directory)."""
    key = tuple(_tests_tree_paths() if paths is None else paths)
    derivations = _held()["derivations"]
    held = derivations.get(key)
    if held is None:
        held = derivations[key] = _census_build(key)
    return held


def module_level_env_census(paths=None):
    """The census of module-level environment writes under tests/ (fork PR #871's by-product counts, derived by ast
    rather than by grep, 2026-09-22): (parsed, {name: {shape: count}}, {name: [_Record, ...]}), `parsed` the number of
    files the census parsed, counted inside its loop (_census_build), fresh containers on every call over the one
    derivation; _census_parsed_modules reads the same derivation's list of those files. Run it as
    `python -m tests.test_hermetic_kernel_postal --census` for a table. A write the scan cannot read raises, as the pin
    does: a census that skipped a write would be a floor with silent slack.
    ONE PARSE PER FILE AND ONE DERIVATION PER PATH TUPLE PER RUN OF THE MODULE, HELD BY THE MODULE AND RELEASED AT ITS END
    (the reviewer's rulings of 2026-09-24 on round 2 of fork PR #894). WHY NOT tests/parse_cache.py's derived(), round 1's
    shape: derived() freezes every object tracked after a build, and every later call of the kernel's _PerfStats.snapshot
    reads gc.get_freeze_count(), which walks the frozen objects, so every snapshot reader that sorts after this module in
    CI's serial order paid per read; the module changes no collector state at all (no gc.freeze, gc.disable or
    gc.collect). WHY NOT THE CACHE'S SHARED PARSE EITHER, this census's exception to tests/parse_cache.py's one-cache
    rule, chosen by the measured rule the reviewer set (the shape whose snapshot readers stay inside main's spread ships):
    read through source_and_tree, which freezes nothing, the trees stayed in that cache, tracked, for the rest of the
    process, and every full collection after this module walked them. THE MEASUREMENT, at round 2 of fork PR #894 (this
    module then the 29 test modules after it in CI's serial order whose tests read gc.get_freeze_count(), the
    perf-snapshot readers, one serial process per run, each shape paired with main in the same rounds; the figures with
    their heads are in the PR's body): with the trees kept in that cache the readers ran 50 to 72 s slower than main on
    Python 3.10 and about 35 s slower on 3.12; with every tree held by this module until its end, 4.3 s slower on 3.12
    on the mean of seven rounds, slower than main in each; with the shape below, 0.3 s slower on 3.12 on the mean of
    seven rounds (1.5 s above the top of main's spread in one of them) and 0.1 s faster on 3.10 on the mean of nine,
    inside main's spread there. THE SHAPE (the reviewer's third ruling of the day): the census parses each file itself
    (_own_tree), once in the module's run; the census loop drops each tree under tests/ after its walk unless the
    resolver may read that file later (_resolver_targets: a file some import statement under tests/ names, read from the
    text, a superset), so it never holds more than those and the one tree it is walking; and the _Census (_held) holds
    the kept trees, the resolver's records and the derivations until tearDownModule empties its one owner, which frees
    them by reference count. What the exception costs: the
    files under tests/ that tests/test_thread_stop_census.py also reads through tests/parse_cache.py (the test modules
    and the helpers) are parsed again there, in a process that runs both, since the two parses do not share; that module
    is one of the 29 readers, so the measurement above includes it. THE RULE FOR WHAT IS HELD: no cycle, so the release
    frees it with no collection; the trees and their nodes, _Module records with side tables keyed by id(node), and
    derivations of strings, numbers, tuples, dicts and _Record tuples, with no closure or object that refers back to
    itself. THE PINS (the ruling's clauses 2 and 3, and fork PR #909's pin (2), which the reviewer's second ruling of the
    day applies here): the census pin and a second test that reads the whole tree each assert the whole tree was built
    once in the module's run (_CENSUS_BUILDS; red under a build per read or per test), the census pin that each file was
    walked once in that build (_walk_unit's count; red under a file walked twice) and that each file the census read was
    parsed once in the module's run (_OWN_PARSES; red under a second parse, and under a loop that keeps no tree, whose
    dropped files the resolver then parses again); the one-path census test asserts those three counts of its own path;
    the census pin holds THE DROP too, the shape's defining property (the verifier's finding at round 2's nineteenth
    commit of fork PR #894, where a loop that kept every tree left the module green), BY EQUALITY with a set the pin
    derives by a reader of its own (_import_line_named_files, the same rule by code that runs none of the census's;
    the verifier's finding at the twentieth commit, where the pin read _resolver_targets again and a widening inside it
    passed): the holder's trees of the tree's files are exactly that set, fewer than the files walked, and the files
    whose tree outlived its walk in the whole-tree build (_Derivation's `outlived`, read through weak references) are
    that set too (red under a loop that keeps every tree, fork PR #850's E shape, a loop that keeps none,
    _resolver_targets returning every file under tests/ or reading every identifier, a tree kept alive by another road,
    and a drop only when the next file's tree replaces it), and the ast objects made in the build and alive after its
    loop, by class, equal the nodes of the trees of that set the build took (_Derivation's `born`, read through
    gc.get_objects() by identity; red under a road that keeps an ast object of a dropped tree, which the weak references
    do not see, and blind, as they are, to a piece of a node kept with no ast object, _census_build's docstring says
    why; the verifier's finding at the thirty-first commit, and the reviewer's ruling of 2026-09-24 21:09Z, (2)); the
    drop's read has a test of its own, one planted road at a time, which also runs the build over a synthetic tree
    and holds the files some leaf of whose tree outlived its drop (_Derivation's `parts_outlived`, a weak reference to
    every leaf) equal to the file the build keeps (red under a loop that keeps each dropped tree's statement list until
    the loop ends, and under a walk that keeps a statement list or one leaf until the next file's walk, none of which
    the whole tree's two reads see; the verifier's finding at the thirty-second commit, and what the build over tests/
    itself does not read is in _census_build's docstring); the target scan's test runs _resolver_targets and the pin's
    reader whole over a synthetic tree, plant by plant, beside the scan's pure parts; the
    resolver's test, that its record of an imported module is built over the census's own tree of the file; and
    tearDownModule asserts that no file was parsed twice in the module's run, whichever test read it (the same count),
    that the _Census is gone after the release (a weak reference, read with no collection; red under the release
    removed, under a module-scope cache that keeps it and under a value that refers back to it), and that
    gc.get_freeze_count() is not above what setUpModule read (red under a build restored behind parse_cache.derived).
    The weak reference does not see an inner container kept by another name, or a cycle among the inner containers that
    does not pass through the _Census; that half is a measurement, re-run at each head: with the collector off, a
    collection right after the build found nothing unreachable, and right after the release neither, the release
    freeing about 1.1 million tracked objects by reference count on Python 3.10 and 3.12, with the whole tree and one
    synthetic path censused (round 2's nineteenth commit of fork PR #894, measured, not committed, with a weak reference
    to a held tree dead after it).
    WHAT IS COMPARED, and with what: the parsed count, with the os.walk population (the census pin, equality); the set of
    names the test modules write, with LICENSED_MODULE_LEVEL_WRITES, and every write's value with its licence
    (_licence_faults); the writer modules of ROMP_SERVE_TOKEN and ROMP_KERNEL_NO_OPEN and of every floor-only name other
    than a leak name, each with its committed file (_writer_set_faults); and each leak name's writers, with none but the
    floor's client-only "1" (_leak_writers). WHAT IS NOT: the per-name, per-shape write and module counts, and the nested,
    by-call and test_*.py columns of the table. --census prints them; they move with every new test module, and a
    committed table would turn that churn red (the refuter's correction on round 1 of fork PR #894)."""
    parsed, counts, records = _census_derivation(paths)[:3]
    return len(parsed), {k: dict(v) for k, v in counts.items()}, {k: list(v) for k, v in records.items()}


def _census_parsed_modules(paths=None):
    """The modules (relative to tests/) the census over `paths` parsed, in order: the same held derivation as
    module_level_env_census's."""
    return list(_census_derivation(paths)[0])


def _census_table(paths=None):
    """The census as text: the parsed-module count with its split between test_*.py and the other files; then per name
    a total line (shape `(all)`: the writes and the writer-module union, no shape added up by hand) and one line per
    (name, shape), each with the write count, the writer-module count, how many of the writes are nested in a
    module-level block or a class body (the ones a column-0 grep misses), how many are reached through a call at import,
    and the writes and writer modules among test_*.py files and among the others, so every figure a reader quotes from
    the census (fork PR #871's by-product figures are counts of test_*.py files) is printed here verbatim."""
    n, counts, records = module_level_env_census(paths)
    tests = sum(1 for m in _census_parsed_modules(paths) if _is_test_module(m))
    lines = ["modules: %d parsed (.py files under tests/, recursively; fixtures/ and the helpers beside the test modules "
             "included): %d test_*.py, %d other" % (n, tests, n - tests),
             "%-34s %-11s %6s %8s %7s %8s %8s %8s %8s %8s" % ("name", "shape", "writes", "modules", "nested", "by call",
                                                               "t-writes", "t-mods", "o-writes", "o-mods"),
             "(t-: among test_*.py files; o-: among the other files)"]

    def line(name, shape, recs):
        t = [r for r in recs if _is_test_module(r.module)]
        o = [r for r in recs if not _is_test_module(r.module)]
        return "%-34s %-11s %6d %8d %7d %8d %8d %8d %8d %8d" % (
            name, shape, len(recs), len({r.module for r in recs}), sum(1 for r in recs if r.nested),
            sum(1 for r in recs if r.via), len(t), len({r.module for r in t}), len(o), len({r.module for r in o}))
    for name in sorted(counts):
        lines.append(line(name, "(all)", records[name]))
        for shape in sorted(counts[name]):
            lines.append(line(name, shape, [r for r in records[name] if r.shape == shape]))
    return "\n".join(lines)


# ───────────── the licensed set: every module-level environment write under tests/, by name, with its reason ─────────────
#
# THE PROPERTY (the reviewer's ruling on fork PR #813's finding, 2026-09-22): no test module writes an environment
# variable at module level that a spawned child could inherit, except the writers licensed here BY NAME, each with a
# reason that can be checked. A module-level write takes effect at COLLECTION and holds for every test in the process
# and for every child any test spawns, whether or not the writing module's own tests run (deselecting does not help):
# tests/test_kernel_tunnels.py's module-level ROMP_POSTAL_PORT and ROMP_POSTAL_CLIENT_ONLY, and the sessions-file seam
# ten postal modules set at import, were the environment a real bus started with from inside the peer-notify guard test
# (the revive road's ensure runs with the test process's environment, and the guard's own trio was restored by the time
# the thread spawned; since round 2 of fork PR #894's review the test waits the revive out before its restore, and a
# scoped fake answers the revive's ensure, so no ensure child starts from it): the port named as the
# run's own (conftest's marker beside it) licensed the bind, client-only was inert with peers on, and the seam's one
# row kept the bus from ever autostopping. The pin below holds the set of names
# written at module level by the test modules EQUAL to this table, with every licence's condition checked per write, so
# a new name reds by construction and a licence with no writer left is removed rather than kept. The two floor modules
# (FLOOR_MODULES) are the one home of the run-wide values and are licensed wholesale, except for the five leak names
# (LEAK_NAMES), of which a floor module may write only upstream's client-only "1" (FLOOR_LEAK_WRITES, _leak_writers).
#
# A licence is PER NAME and CHECKABLE: `value` names the one literal the writers may set (the dead port, the off
# switch); `value_ok` is a predicate over the value expression; `reasserted` requires tests/conftest.py to set or pop
# the name before every test (an unconditional plain assignment or pop before the yield of a function-scoped autouse
# fixture, which a child pytest over a copy of the conftest sees run for its probe's tests, _conftest_reasserts_proved,
# whose docstring names what that does not read), so the module-level
# value cannot outlive collection under pytest (the dead-port fixture's rule); `until` DATES a licence that waits on an item, naming it: a
# licence with no date and no owner is how a temporary exemption becomes permanent. A date bounds no writer (it is read
# for its form alone): the writer modules of the two dated names whose population nothing mandates are committed and
# compared as sets (below the table).

FLOOR_MODULES = ("conftest.py", "__init__.py")     # the runner's floor and its unittest twin (tests/__init__.py)

CLASS_ITEM_871 = ("the class item filed 2026-09-21 in the small-asks notes from fork PR #871's polluter investigation: "
                  "import-time environment writers in the test modules reach every test in the process and every "
                  "spawned child; the writers move from module scope into fixtures or the floor, migrated by class")


_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _a_string_literal(v):
    """A non-empty string literal, as ast.unparse spells one."""
    return bool(re.fullmatch(r"""'[^']+'|"[^"]+\"""", v))


def _expr(v):
    """The value text `v` (ast.unparse's spelling, resolved through the names bound once) parsed back to an expression node,
    so a licence's predicate reads the value's structure and not a regex over its text; None when it is not one."""
    try:
        return ast.parse(v, mode="eval").body
    except SyntaxError:
        return None


def _str_literal(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _call_of(node, dotted):
    """True for a call whose callee is spelled exactly `dotted` ("tempfile.mkdtemp")."""
    return isinstance(node, ast.Call) and _dotted(node.func) == dotted.split(".")


def _is_mkdtemp(node):
    """`tempfile.mkdtemp()` bare, or with a string-literal `prefix` and nothing else: no positional argument (the third is
    dir) and no other keyword, so no `dir=`, which would put the directory under a real path while the licence's reason
    says the run's temp root (the third commit of 2026-09-22: the regex before accepted any argument list). The forms the
    census finds over the tree, every one of them: `tempfile.mkdtemp()` (XDG_STATE_HOME's and CLAUDE_CONFIG_DIR's writes,
    and inside ROMP_STATE_DIR's join) and `tempfile.mkdtemp(prefix='romp-envnames-')` (an XDG_STATE_HOME write and the
    ROMP_SERVICE_ENV_FILE concatenation of the same module); the floor's are `prefix='romp-tests-state-'` and
    `prefix='romp-tests-claude-'`. No count is given here: the counts move with every new test module, --census prints
    them, and what holds the forms is the value check on every write (_licence_faults), not a figure (the verifier's
    finding on round 2 of fork PR #894: the XDG_STATE_HOME count this docstring gave was already one short at that
    head)."""
    return (_call_of(node, "tempfile.mkdtemp") and not node.args
            and all(kw.arg == "prefix" and _str_literal(kw.value) for kw in node.keywords))


def _is_temporary_directory_name(node):
    """`tempfile.TemporaryDirectory().name`, bare: the form of the three ROMP_STATE_DIR writers that use it; a `dir=` or a
    positional argument would place it under a real directory."""
    return (isinstance(node, ast.Attribute) and node.attr == "name" and _call_of(node.value, "tempfile.TemporaryDirectory")
            and not node.value.args and not node.value.keywords)


def _is_join_onto(node, base_ok):
    """`os.path.join(<base>, '<literal>', ...)`: `base_ok` over the first argument, every further part a string literal."""
    return (_call_of(node, "os.path.join") and not node.keywords and len(node.args) >= 2
            and base_ok(node.args[0]) and all(_str_literal(a) for a in node.args[1:]))


def _is_module_state_home(node):
    """`os.environ['XDG_STATE_HOME']`: the module's own root, which its own licence checks."""
    return (isinstance(node, ast.Subscript) and _dotted(node.value) == ["os", "environ"]
            and _str_literal(node.slice) and node.slice.value == "XDG_STATE_HOME")


def _a_mkdtemp(v):
    """A fresh private directory under the run's temp root: a bare `tempfile.mkdtemp()`, or one with a literal prefix
    (_is_mkdtemp); a `dir=` is a fault naming the module and the line."""
    return _is_mkdtemp(_expr(v))


def _a_state_dir(v):
    """A private state directory for ROMP_STATE_DIR: a bare TemporaryDirectory's name, a path of literals joined onto a
    mkdtemp (`os.path.join(tempfile.mkdtemp(), 'romp')`), or the shell's own value written back after the load (the three
    converge and update modules); each of the three the exact form the census shows. A bare mkdtemp is not one: no
    ROMP_STATE_DIR writer uses it, and the disjunct that accepted it was exercised by nothing (the reviewer's ruling of
    round 1 on fork PR #894), so a future writer of that form gets a visible refusal."""
    node = _expr(v)
    return _is_temporary_directory_name(node) or _is_join_onto(node, _is_mkdtemp) or v == "os.environ.get('ROMP_STATE_DIR')"


def _under_the_state_root(v):
    """A path built on the module's own state root and nowhere real: literals joined onto its XDG_STATE_HOME, or onto a
    mkdtemp, or a literal concatenated onto a mkdtemp (`tempfile.mkdtemp(prefix='romp-envnames-') + '/absent.env'`); the
    mkdtemp bare or with a literal prefix, never with a `dir=`."""
    node = _expr(v)
    return (_is_join_onto(node, _is_module_state_home) or _is_join_onto(node, _is_mkdtemp)
            or (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add) and _is_mkdtemp(node.left) and _str_literal(node.right)))


def _a_serve_token(v):
    """A synthetic serve token: a string literal, or the shell's own value written back (test_postal_token.py)."""
    return _a_string_literal(v) or v == "os.environ.get('ROMP_SERVE_TOKEN')"


def _a_service_env(v):
    """The service-env path: the same value as the sibling name (which is checked itself), or a path under the root."""
    return v == "os.environ['ROMP_SERVICE_ENV_FILE']" or _under_the_state_root(v)


def _a_loopback_url(v):
    """A URL on port 9 of 127.0.0.1, the one writer's (the discard port: privileged, so no test process binds it, and
    nothing answers there). Any other port is refused, a live one included (the reviewer's ruling of round 1 on fork PR
    #894: the condition accepted any port on a permanent licence that nothing re-asserts per test)."""
    return bool(re.fullmatch(r"'http://127\.0\.0\.1:9/[^']*'", v))


def _shown_value(rec):
    """The written value for a fault message: the text as written, with the resolved text beside it where a name was
    read through, and a note where a bare name could not be."""
    if not rec.value:
        return ""
    if rec.resolved != rec.value:
        return "%s (that is, %s)" % (rec.value, rec.resolved)
    if re.fullmatch(r"[A-Za-z_]\w*", rec.value):
        return ("%s (a name the scan cannot read through: bound more than once at import, a star import counting as a "
                "binding of every name, or not by an assignment)" % rec.value)
    return rec.value


class _Licence:
    """One licensed module-level write, per name (the comment above): `reason` says why a child may inherit the write;
    the CHECKABLE conditions are `value` (the one literal the writers may set), `value_ok` (a predicate over the written
    value's text, resolved through the names bound once at import, so `_ROOT = tempfile.mkdtemp()` is read as the
    mkdtemp), `reasserted` (tests/conftest.py sets or pops the name before every test, proved by a child pytest in
    the context _conftest_reasserted_names' docstring names with what the proof does not read:
    _conftest_reasserts_proved) and,
    for a licence that waits on an item, `since` (the ISO date it was granted) with `until` (the item, named with the
    date it was filed).
    _licence_table_faults holds every licence to that shape: since the fixup of 2026-09-22 (the verifier's finding
    that since and until were stored and read by nothing) a licence must carry a per-write condition, an `until` must
    come with a `since`, and the dates must be dates."""

    def __init__(self, reason, value=None, value_ok=None, reasserted=False, since=None, until=None):
        self.reason, self.value, self.value_ok, self.reasserted, self.since, self.until = reason, value, value_ok, reasserted, since, until

    def fault(self, rec, reasserted_names, refused=()):
        """Why the write `rec` (a _Record) falls outside this licence, or None when it is covered. `refused` is the
        conftest reader's refusals (_Reasserted.refused: the filter's fixtures and the proof's names): a re-assert fault
        counts them, and _licence_faults names each once at the end of its list, so a refusal is seen with its reason."""
        if self.reasserted and self._name not in reasserted_names:
            return ("licensed only while tests/conftest.py re-asserts %s before every test (an unconditional plain assignment "
                    "or pop before the yield of a function-scoped autouse fixture, which a child pytest over the conftest "
                    "sees run), and it no longer does%s"
                    % (self._name, ("; the conftest reader refused %d of its fixtures or names, named at the end of this "
                                    "list" % len(refused)) if refused else ""))
        shown = _shown_value(rec)
        if self.value is not None and rec.resolved != repr(self.value):
            return "licensed for the value %r alone, not %s" % (self.value, shown or "a shape with no value")
        if self.value_ok is not None and not self.value_ok(rec.resolved):
            return "the value %s is not one this licence covers" % (shown or "(none)")
        return None


def _licence_table_faults(table):
    """Every way a licence in `table` ({name: _Licence}) is not the checkable, dated thing the reviewer's ruling asks for
    (the fixup of 2026-09-22): a licence needs a per-write condition (a value, a value predicate, or conftest's
    re-assert); a licence that waits on an item (`until`) needs the date it was granted (`since`, an ISO date) and the
    item named with the date it was filed; a licence with no date and no owner is how a temporary exemption becomes
    permanent. A list rather than assertions so the check runs over synthetic tables and is known to be able to fail."""
    faults = []
    for name in sorted(table):
        lic = table[name]
        if lic.value is None and lic.value_ok is None and not lic.reasserted:
            faults.append("%s: the licence has no per-write condition (a value, a value predicate or conftest's re-assert)" % name)
        if lic.since is not None and not _ISO_DATE.fullmatch(lic.since):
            faults.append("%s: since=%r is not an ISO date" % (name, lic.since))
        if lic.until is not None:
            if lic.since is None:
                faults.append("%s: the licence waits on an item (until) and has no since date: date it" % name)
            if not _ISO_DATE.search(lic.until):
                faults.append("%s: until names no filed item (no filing date in it)" % name)
    return faults


LICENSED_MODULE_LEVEL_WRITES = {
    "XDG_STATE_HOME": _Licence(
        "the state preamble tests/test_state_isolation_order.py mandates before a module loads bin/romp-*, which bind "
        "their state root at import: a private root under the run's temp root (tempfile.mkdtemp(), directly or through "
        "a name bound to one), removed with the run; a child that inherits it writes under that root and nowhere real. "
        "Licensed 2026-09-22 until the class item is taken, which may retire the mandate, and this licence with it. The "
        "mandate grows the writer population with every new module that loads bin/romp-*, so the date bounds no "
        "writer: the value check on every write is what holds the licence",
        value_ok=_a_mkdtemp, since="2026-09-22", until=CLASS_ITEM_871),
    "ROMP_STATE_DIR": _Licence(
        "the other half of the same preamble (a live kernel exports it and it outranks the XDG floor): a private root "
        "(a TemporaryDirectory's name, a path joined onto a mkdtemp), or the shell's own value written back after the "
        "load, in the four modules that do not pop it. Licensed 2026-09-22 until the class item is taken. The mandate "
        "grows its writers as it grows XDG_STATE_HOME's, so the date bounds no writer: the value check does",
        value_ok=_a_state_dir, since="2026-09-22", until=CLASS_ITEM_871),
    "ROMP_SERVE_TOKEN": _Licence(
        "a synthetic serve token so a kernel or bus loaded in-process mints none under the module's root: a string "
        "literal, by setdefault in most modules and by assignment in the rest (test_postal_token.py puts the shell's "
        "value back after its load, the one non-literal). Licensed 2026-09-22 until the class item is taken, by the "
        "reviewer's ruling: a dated licence, not current practice. The writer modules are the committed set "
        "(WRITER_SET_FILES), compared by equality: a new writer faults, a migrated one reds until its line is removed",
        value_ok=_a_serve_token, since="2026-09-22", until=CLASS_ITEM_871),
    "ROMP_KERNEL_NO_OPEN": _Licence(
        "the kernel's one reader opens a browser when the name is unset (kernel/kernel.py, the serve path), and \"1\" "
        "is the value every test wants for itself and for any kernel it starts (kernel_env sets it too): a child that "
        "inherits it opens no browser. Licensed for that one value, its writer modules the committed set "
        "(WRITER_SET_FILES), compared by equality",
        value="1", since="2026-09-22", until=CLASS_ITEM_871),
    "ROMP_MANAGER_PORT": _Licence(
        "the dead port \"1\", the floor tests/conftest.py and tests/__init__.py set so no test reaches a real manager, "
        "written again by modules that run bare; conftest re-asserts it per test, so the module value cannot outlive "
        "collection under pytest", value="1", reasserted=True),
    "ROMP_KERNEL_PORT": _Licence(
        "the dead port \"1\" for the kernel's port (the same floor, both spellings); re-asserted per test",
        value="1", reasserted=True),
    "ROMP_SERVE_PORT": _Licence(
        "the dead port \"1\" for the kernel's port, the second spelling; re-asserted per test", value="1", reasserted=True),
    "ROMP_MODEL_CATALOG": _Licence(
        "\"off\", the floor value (no catalog fetch reaches the network); re-asserted per test by conftest's fixture",
        value="off", reasserted=True),
    "ROMP_CLI_SCOPE": _Licence(
        "\"0\", the floor value (no backend construction probes the real systemd-run); re-asserted per test",
        value="0", reasserted=True),
    "CLAUDE_CONFIG_DIR": _Licence(
        "a private directory (tempfile.mkdtemp(), under the run's temp root) in place of the real ~/.claude, the floor "
        "conftest sets and re-asserts per test", value_ok=_a_mkdtemp, reasserted=True),
    "ROMP_SERVICE_ENV_FILE": _Licence(
        "a never-created path under the module's own state root (joined onto its XDG_STATE_HOME or onto a mkdtemp), the "
        "floor's shape (no test reads the real service.env); re-asserted per test", value_ok=_under_the_state_root, reasserted=True),
    "ROMP_SERVICE_ENV": _Licence(
        "the second spelling of the service-env path, the same floor: the sibling name's value, or a path under the "
        "root; re-asserted per test", value_ok=_a_service_env, reasserted=True),
    "ROMP_MODELS_URL": _Licence(
        "the kernel reads it at import (MODELS_API_URL) and the one writer, test_model_catalog.py, names a dead loopback "
        "URL, port 9 of 127.0.0.1 and no other (privileged, so no test process binds it), so a kernel that inherits it "
        "fetches its catalog from nothing rather than from the network",
        value_ok=_a_loopback_url),
}
for _name, _lic in LICENSED_MODULE_LEVEL_WRITES.items():
    _lic._name = _name


# ───────────── the committed writer sets: who writes a dated name, and who writes a floor-only name ─────────────
#
# A date bounds no writer: since and until are read for their form alone, so a dated licence accepted a write from any
# module, one added after the date included (the reviewer's ruling of round 1 on fork PR #894). For the two dated names
# whose population nothing mandates, ROMP_SERVE_TOKEN and ROMP_KERNEL_NO_OPEN, the writer modules (the floor modules
# aside, which are licensed wholesale) are COMMITTED, one path per line relative to tests/, in a file under
# WRITER_SETS_DIR derived by the census, and compared with the census by equality, a set and not a count, so a swap is
# caught and each offender is named: a new writer faults naming itself and the remedy, and a writer that migrated reds
# until the migrating change removes its line. XDG_STATE_HOME and ROMP_STATE_DIR have no committed set: the isolation-order
# mandate (tests/test_state_isolation_order.py) adds a writer with every new module that loads bin/romp-*, so their
# licences rest on the value check of every write. The names only the floor modules write (FLOOR_ONLY_FILE: one
# "NAME module" line per writer module) are committed the same way, every name but the five leak names, which
# _leak_writers holds to none but the floor's client-only "1" (fork PR #875 adds that line to tests/conftest.py, and it is
# passed there whichever of the two lands first). The rest of the census's table is not committed (module_level_env_census
# says what is compared and what is not).

WRITER_SETS_DIR = os.path.join(HERE, "fixtures", "module-level-env-writers")
WRITER_SET_FILES = {"ROMP_SERVE_TOKEN": "ROMP_SERVE_TOKEN.txt", "ROMP_KERNEL_NO_OPEN": "ROMP_KERNEL_NO_OPEN.txt"}
FLOOR_ONLY_FILE = "floor-only.txt"
NEW_WRITER_REMEDY = ("omit the write, or move it to the conftest floor (tests/conftest.py); not setUp, since a module that "
                     "loads the kernel at import needs the value before the load. A module renamed from one in the file "
                     "renames its line there")


def _committed_lines(path):
    """The lines of a committed writer-set file other than its `#` comments and blank lines, each stripped."""
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.lstrip().startswith("#")]


def _committed_writer_sets(root=None):
    """{name: set of module paths relative to tests/} from the committed files of WRITER_SET_FILES under `root`
    (WRITER_SETS_DIR by default); a missing file is an error, never an empty set."""
    root = WRITER_SETS_DIR if root is None else root
    return {name: set(_committed_lines(os.path.join(root, fname))) for name, fname in WRITER_SET_FILES.items()}


def _committed_floor_only(root=None):
    """{name: set of floor modules} from FLOOR_ONLY_FILE under `root` (WRITER_SETS_DIR by default), one `NAME module`
    line per writer module; a line of any other shape is an error naming it."""
    out = {}
    path = os.path.join(WRITER_SETS_DIR if root is None else root, FLOOR_ONLY_FILE)
    for ln in _committed_lines(path):
        parts = ln.split()
        if len(parts) != 2:
            raise AssertionError("%s: %r is not a `NAME module` line" % (path, ln))
        out.setdefault(parts[0], set()).add(parts[1])
    return out


def _floor_only_writers(records):
    """{name: set of floor modules} for every name in `records` ({name: [_Record]}) that only the floor modules
    (FLOOR_MODULES) write at module level, the leak names (LEAK_NAMES) aside."""
    return {name: {r.module for r in recs} for name, recs in records.items()
            if recs and name not in LEAK_NAMES and all(r.module in FLOOR_MODULES for r in recs)}


def _writer_set_faults(records, committed=None, floor_only=None):
    """Every way the writer modules in `records` ({name: [_Record]}) differ from the committed sets: for each name of
    WRITER_SET_FILES, a test module that writes it and is not in its file (a new writer, named with its first write's
    line and NEW_WRITER_REMEDY) and a module in its file that no longer writes it (a migrated writer, whose line the
    migrating change removes); and for the floor-only names (_floor_only_writers against FLOOR_ONLY_FILE), a name whose
    writer modules differ from its committed lines. `committed` and `floor_only` default to the committed files. Empty
    exactly when every set is equal. A list rather than assertions so the check runs over synthetic records and is known
    to be able to fail."""
    committed = _committed_writer_sets() if committed is None else committed
    floor_only = _committed_floor_only() if floor_only is None else floor_only
    rel_dir = os.path.relpath(WRITER_SETS_DIR, os.path.dirname(HERE))
    faults = []
    for name in sorted(WRITER_SET_FILES):
        where = os.path.join(rel_dir, WRITER_SET_FILES[name])
        recs = [r for r in records.get(name, []) if r.module not in FLOOR_MODULES]
        current, want = {r.module for r in recs}, committed.get(name, set())
        for module in sorted(current - want):
            line = min(r.line for r in recs if r.module == module)
            faults.append("%s is written at module level by %s:%d, a module outside the committed writer set (%s): %s"
                          % (name, module, line, where, NEW_WRITER_REMEDY))
        for module in sorted(want - current):
            faults.append("%s: %s is in the committed writer set (%s) and no longer writes it at module level: remove its "
                          "line there" % (name, module, where))
    where = os.path.join(rel_dir, FLOOR_ONLY_FILE)
    now = _floor_only_writers(records)
    for name in sorted(set(now) | set(floor_only)):
        have, want = sorted(now.get(name, ())), sorted(floor_only.get(name, ()))
        if have != want:
            faults.append("%s: the floor modules that alone write it at module level are %s, and the committed floor-only set "
                          "(%s) says %s: a floor module added or dropped the write, or a test module now writes it too; the "
                          "file lists each floor-only name once per writer module (`NAME module`)" % (name, have, where, want))
    return faults


def _is_autouse_fixture(fn):
    for d in fn.decorator_list:
        if not (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "fixture"):
            continue
        for kw in d.keywords:
            if kw.arg == "autouse" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
    return False


def _is_function_scoped_fixture(fn):
    """True when every fixture decorator on `fn` (`<x>.fixture(...)`) passes no positional argument and no scope, or
    scope="function" as a string literal: a fixture set up again before every test. A scope that is not a literal, or
    any other scope, is not."""
    for d in fn.decorator_list:
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "fixture":
            if d.args:
                return False
            for kw in d.keywords:
                if kw.arg == "scope" and not (isinstance(kw.value, ast.Constant) and kw.value.value == "function"):
                    return False
    return True


def _holds_an_end(stmt):
    """True when `stmt` holds a yield, a return or a raise of the fixture's own: anywhere in it (`stmt` itself included)
    but the body of a def or a lambda, whose yield and return are its own; a def's decorators and defaults and a lambda's
    defaults run where they stand, and are read, and so is a class body nested in the fixture, which runs where it stands
    (a raise there ends the fixture; a yield or a return there does not parse). A return or a raise nested in a block
    (`if os.environ.get("CI"): return`) ends the fixture on the runs where the block's test holds, so a statement after
    it does not run on those (the verifier's finding on round 2 of fork PR #894: the reader stopped only at a return or a
    raise that was itself a statement of the body, and counted the write after an `if ...: return`)."""
    todo = [stmt]
    while todo:             # loop-ok: bounded by the nodes under `stmt`
        n = todo.pop()
        if isinstance(n, (ast.Yield, ast.YieldFrom, ast.Return, ast.Raise)):
            return True
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            todo.extend(c for c in ast.iter_child_nodes(n) if not any(c is s for s in n.body))
        elif isinstance(n, ast.Lambda):
            todo.extend(c for c in ast.iter_child_nodes(n) if c is not n.body)
        else:
            todo.extend(ast.iter_child_nodes(n))
    return False


def _statements_before_the_yield(body):
    """The statements of `body` that run before the test on every run, in order: every statement up to the first that holds
    the fixture's yield, a return or a raise at any depth (_holds_an_end: a statement of the body, or nested in a block of
    it), that one not included. A statement after a block that may return runs only on the runs where it does not."""
    out = []
    for st in body:
        if _holds_an_end(st):
            break
        out.append(st)
    return out


def _plain_reasserts(stmts, names, loop=None):
    """(writes, removals) among `stmts`, each counted only as a statement of its own: an assignment whose target is an
    environment subscript (`os.environ[K] = v`, `a = os.environ[K] = v`) and a pop as a statement
    (`os.environ.pop(K, ...)`), the key a string literal, or, inside a for over a literal tuple, the loop's own name
    (`loop`: (name, its literals)). Nothing nested in a statement is read here."""
    writes, removals = set(), set()

    def keys_of(key):
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            return {key.value}
        if loop is not None and isinstance(key, ast.Name) and key.id == loop[0]:
            return set(loop[1])
        return set()
    for st in stmts:
        if isinstance(st, ast.Assign):
            for t in st.targets:
                if isinstance(t, ast.Subscript) and names.is_environ(t.value):
                    writes |= keys_of(t.slice)
        elif (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Attribute)
              and st.value.func.attr == "pop" and names.is_environ(st.value.func.value) and st.value.args):
            removals |= keys_of(st.value.args[0])
    return writes, removals


def _literal_tuple_loop(st):
    """(name, literals) for `for NAME in ("A", "B", ...):` over a non-empty tuple of string literals, with no else and
    nothing in its body that ends an iteration early or the fixture (a break, a continue, a return, a raise or a yield,
    outside a def, class or lambda nested in it) or binds or deletes the loop's name, so every statement of the body runs
    once for every literal with the name bound to it; else None."""
    if not (isinstance(st, ast.For) and isinstance(st.target, ast.Name) and isinstance(st.iter, ast.Tuple) and st.iter.elts
            and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in st.iter.elts) and not st.orelse):
        return None
    todo = list(st.body)
    while todo:             # loop-ok: bounded by the nodes under the loop's body
        n = todo.pop()
        if isinstance(n, (ast.Break, ast.Continue, ast.Return, ast.Raise, ast.Yield, ast.YieldFrom)):
            return None
        if isinstance(n, ast.Name) and n.id == st.target.id and not isinstance(n.ctx, ast.Load):
            return None
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            todo.extend(ast.iter_child_nodes(n))
    return st.target.id, tuple(e.value for e in st.iter.elts)


_Reasserted = collections.namedtuple("_Reasserted", "writes removals refused", defaults=((),))
#   what _conftest_reasserted_names returns: WRITES and REMOVALS, the names set and the names popped before every
#   test, kept apart, and REFUSED, one line per function-scoped autouse fixture the reader did not count because it
#   could not prove pytest runs it, naming the fixture and why (empty when it proved every one)


def _module_name_bindings(tree):
    """(Counter {name: bindings}, star) for the names `tree`'s import-time code binds in the module's own namespace: a def
    or class name, an import's name (`import a.b` binds a; an alias its alias), a name stored or deleted (an assignment,
    augmented or annotated with a value, a for or with target, a walrus, a `type` statement, a del), an except name and a
    match capture, in the module's body and its blocks however nested, the header parts of a def or class (decorators,
    defaults, bases) included; and a `global` declaration of the name in any def at any depth, which lets the def rebind it
    when called. Not a def's or a lambda's body (their names are their own) nor a class body (its names are the class's).
    `star` is True when an import at import time is a star import, which binds names no text of the module spells. A name
    stored in a comprehension at import time is counted though it binds in the comprehension's own scope (the safe side
    for the reader that refuses a name bound more than once)."""
    counts, star = collections.Counter(), False
    todo = list(tree.body)
    while todo:             # loop-ok: bounded by the nodes of the module's import-time code
        n = todo.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            counts[n.name] += 1
            todo.extend(c for c in ast.iter_child_nodes(n) if not any(c is s for s in n.body))
            continue
        if isinstance(n, ast.Lambda):
            todo.extend(c for c in ast.iter_child_nodes(n) if c is not n.body)
            continue
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                if a.name == "*":
                    star = True
                else:
                    counts[a.asname or (a.name.split(".")[0] if isinstance(n, ast.Import) else a.name)] += 1
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            counts[n.id] += 1
        elif isinstance(n, ast.ExceptHandler) and n.name:
            counts[n.name] += 1
        elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name:
            counts[n.name] += 1
        elif isinstance(n, ast.MatchMapping) and n.rest:
            counts[n.rest] += 1
        todo.extend(ast.iter_child_nodes(n))
    for n in ast.walk(tree):
        if isinstance(n, ast.Global):
            counts.update(n.names)
    return counts, star


_FixtureNames = collections.namedtuple("_FixtureNames", "by_keyword unknown")


def _fixture_names_by_keyword(tree):
    """_FixtureNames(by_keyword, unknown) over EVERY call in `tree`, whatever it calls and wherever it stands:
    BY_KEYWORD, Counter {name: calls}, the string literals the calls pass as name=, the name pytest registers a fixture
    under whatever attribute holds it when the call reaches one of its fixture functions; UNKNOWN, True when any call
    passes a name= that is not a string literal or unpacks keywords (**kw), so the name it registers could be any. Every
    call rather than those spelled as a fixture function (_fixture_spellings), since the verifier's finding on round 2 of
    fork PR #894: a fixture function reached by a road the spellings do not follow registers its name= all the same
    (`functools.partial(pytest.fixture, autouse=True, name="_f")` used as a decorator, whose name= sits on the partial's
    call; `getattr(pytest, "fixture")(autouse=True, name="_f")`; one held in a container or returned by a call; pytest's
    private FixtureManager._register_fixture(name=...)), and a child pytest showed the fixture it shadows never ran. The
    name is keyword-only in pytest's fixture function, so a call that registers one passes it as name= or inside
    unpacked keywords, both read here. The safe side: a name= of a call that registers no fixture (a thread's name, say)
    equal to a fixture's name refuses that fixture, and a name= that is not a literal or unpacked keywords in any call of
    the module refuse every fixture of it (tests/conftest.py has neither), a visible refusal whose remedy is to spell
    the call's keywords out."""
    by_keyword, unknown = collections.Counter(), False
    for c in ast.walk(tree):
        if isinstance(c, ast.Call):
            for kw in c.keywords:
                if kw.arg is None:
                    unknown = True
                elif kw.arg == "name":
                    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        by_keyword[kw.value.value] += 1
                    else:
                        unknown = True
    return _FixtureNames(by_keyword, unknown)


_PYTEST_OWN = ("pytest", "_pytest")
#   the top-level packages of pytest's own code: the runner imported them before any conftest, and a name imported from
#   one of them is pytest's own object
_PYTEST_DECORATORS = (("fixture",), ("yield_fixture",), ("hookimpl",))
#   the attributes of the pytest module a module read by its text may decorate with or call (besides any
#   pytest.mark.<name>): the two fixture functions, whose name= is keyword-only and read in the tree
#   (_fixture_names_by_keyword), and hookimpl, which registers no fixture (a hook it marks is read by
#   _unproven_statements' hook clause)
_PROVEN_DUNDERS = ("__all__", "__doc__")
#   the only double-underscore names a module read by its text may bind at module level: a module-level __getattr__ or
#   __dir__ changes what an attribute read returns and what dir() lists, which is how pytest finds a module's fixtures,
#   and a binding of __builtins__ changes what a builtin name calls
_ENVIRON_METHODS = ("get", "pop", "setdefault", "update")
#   the methods of os.environ a module read by its text may call: each reads or writes the process environment and runs
#   no other code (os._Environ's own methods, which call putenv and unsetenv)
_LISTED_HOOKS = {
    "pytest_configure": "pytest calls it once, before collection, and reads no result from it",
    "pytest_collectreport": "pytest calls it with each collector's report once the collector has collected, and reads no "
                            "result from it",
    "pytest_runtest_makereport": "pytest calls it after each phase of a test, the setup phase's once every fixture of the "
                                 "test has run or raised, and reads its result as that phase's report",
    "pytest_sessionfinish": "pytest calls it once the session's last test has run and been torn down",
    "pytest_unconfigure": "pytest calls it after pytest_sessionfinish, when no test is left to run",
}
#   THE HOOKS A MODULE MAY IMPLEMENT and still have its fixtures counted (the verifier's finding at round 2's thirty-first
#   commit of fork PR #894: a conftest hook kept pytest from running a fixture the reader counted, on both roads),
#   {spec: when pytest calls it and what it reads from it}: the five tests/conftest.py implements. Pytest reads no result
#   from any of them that decides whether a fixture runs before a test, where other hooks decide it
#   (pytest_fixture_setup's result replaces the fixture's run, pytest_generate_tests can parametrize the fixture's name
#   over it, pytest_collection_modifyitems can take it out of a test's fixtures, pytest_runtest_protocol and
#   pytest_runtestloop replace the runner), so every hook off this list refuses every fixture of the module, a hook
#   pytest adds in a later release included. ONE EXCEPTION on the list: pytest reads pytest_runtest_makereport's setup
#   report to decide whether the test's body runs, so a report made to pass where the setup failed would run the body
#   after a fixture raised before its re-assert. What a listed hook can still do through its code (that report, a
#   plugin registered from pytest_configure, a collected node edited) is refused on the text road, which reads a hook's
#   body by THE PROVEN LIST (no call, no attribute write) and refuses a hook that returns or yields a value, and taken on
#   trust on the module road (_conftest_reasserted_names names it: tests/conftest.py's pytest_runtest_makereport turns a
#   skip into a failure and redacts text). The list equals the hooks tests/conftest.py implements (a pin compares them
#   by equality), so a hook the conftest drops leaves the list with it.


def _import_roots(where):
    """(package, directories) for a module sitting in the directory `where`, each part with its plant (the registration
    test, test_the_reader_counts_a_fixture_only_where_it_proves_pytest_runs_it): PACKAGE, the dotted names of `where`
    and its parents that hold an __init__.py (planted: a package two deep reads "outer.inner", a directory with none
    reads ""); DIRECTORIES, `where` and each parent up to and including the first with no __init__.py (planted: that
    package's directory, its parent and the first parent with none; the directory with none, alone). That a child pytest
    takes a module from the last of them ahead of the standard library's is planted by two child cases: sched.py in a
    package's first parent with no __init__.py, and colorsys.py beside a conftest in a directory with none."""
    parts, d = [], os.path.abspath(where)
    dirs = [d]
    while os.path.isfile(os.path.join(d, "__init__.py")):      # loop-ok: one parent per turn, ends at the root
        parts.insert(0, os.path.basename(d))
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
        dirs.append(d)
    return ".".join(parts), dirs


def _shadowed(top, dirs):
    """The first of `dirs` that holds an entry named `top` or one whose name begins `top.`, or that os.listdir refuses,
    else None, each part with its plant (the registration test): the first of them, the directories read in order
    (planted directly: a regular file named bisect in the first directory and bisect.py in the last name the first), an
    entry that is the name (planted directly by a bare directory, heapq/, and by that regular file, and in a child run
    by a package directory, wave/, taken ahead of the standard library's), an entry beginning `top.` (planted directly
    by sched.py in the last directory, and in child runs by sched.py and by colorsys.py), the directories past the first
    (the same sched.py, two directories down), and a directory os.listdir refuses (planted directly by a regular file
    and by a missing path). Nothing else about the entry is read: its kind, and whether the import system would take
    it, are not (planted: the regular file named bisect, which no import takes)."""
    for d in dirs:
        try:
            entries = os.listdir(d)
        except OSError:
            return d
        if any(e == top or e.startswith(top + ".") for e in entries):
            return d
    return None


def _pytest_object_is_fixture(module, name):
    """Why `from <module> import <name>`, `module` pytest's own, binds an object pytest may register as a fixture, else
    None, read from the installed pytest (its public package imported here, which imports the modules of _pytest it is
    made of; a module of pytest's own that this leaves unimported is refused, named, rather than imported by name): a
    module of _pytest defines fixtures (the monkeypatch fixture, say), and one imported into a module registers there
    too."""
    try:
        import pytest  # noqa: F401  (pytest's public package, and with it the modules of _pytest it imports)
        from _pytest.fixtures import FixtureFunctionDefinition
    except Exception as e:
        return "the reader could not import the installed pytest (%s: %s)" % (type(e).__name__, e)
    mod = sys.modules.get(module)
    obj = getattr(mod, name, None) if mod is not None else None
    if obj is None:
        obj = sys.modules.get("%s.%s" % (module, name))
    if obj is None:
        return ("%s.%s is not an object of the pytest this process imported, so the reader cannot read whether it is a "
                "fixture" % (module, name))
    if type(obj) is FixtureFunctionDefinition:
        return "%s.%s is a fixture of pytest's own, registered again wherever it is imported" % (module, name)
    return None


def _first_binding(tree, name):
    """The first node of `tree`, in ast.walk's order, that binds `name` in some scope (a def or class of that name, a
    stored or deleted Name, an import naming it, a `global` of it), else the module itself: where a refusal of the
    name points."""
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name:
            return n
        if isinstance(n, ast.Name) and n.id == name and not isinstance(n.ctx, ast.Load):
            return n
        if isinstance(n, (ast.Import, ast.ImportFrom)) and any((a.asname or a.name.split(".")[0]) == name for a in n.names):
            return n
        if isinstance(n, ast.Global) and name in n.names:
            return n
    return tree


def _returns_a_value(fn):
    """True when the def `fn`'s own body (not a def, a lambda or a class nested in it) holds a return with a value
    (`return None` spelled out included), a yield with one or a yield from: the parts pytest may read as a hook's
    result."""
    todo = list(fn.body)
    while todo:             # loop-ok: bounded by the nodes of fn's own body
        n = todo.pop()
        if ((isinstance(n, (ast.Return, ast.Yield)) and n.value is not None) or isinstance(n, ast.YieldFrom)):
            return True
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            todo.extend(ast.iter_child_nodes(n))
    return False


def _unproven_statements(tree, where=None):
    """[(line, what)] for every statement of `tree`, wherever it stands, that is off THE PROVEN LIST below, and every
    hook implementation of the module THE HOOK CLAUSE does not prove, each named with why the reader cannot prove it
    leaves pytest registering and running the module's fixtures; empty when all of it is proven. Wherever it stands: the
    module's body, its blocks and class bodies however nested, the header parts of a def or class, and, since the
    verifier's finding at round 2's thirty-first commit of fork PR #894 (a hook of the module kept pytest from running a
    fixture the reader counted, and the reader read no def's body), the body of every def and lambda at any depth,
    which runs when pytest calls it as a fixture or a hook, or when anything else does. `where` is the directory the
    module is read as sitting in (tests/, where tests/conftest.py sits, when None). This is the text road of
    _conftest_reasserted_names, for a source handed in: anything off the list refuses every fixture of the module, so a
    road not yet named is refused rather than counted (the ruling on the verifier's findings at round 2's twentieth
    commit of fork PR #894, which found the fifth case of one class, a fixture the reader counted and pytest never ran,
    each earlier fix having closed one case by name). THE PROVEN LIST:
    - an import of pytest's own code (_PYTEST_OWN; the runner imported pytest before any conftest), a `from` import of it
      that names no fixture of pytest's (_pytest_object_is_fixture), an `import` of the module's own package or a parent
      of it (Python imported it before the module's body ran, so the statement runs no code; tests/conftest.py's
      `import tests as _tests`), and an import of a standard-library module (sys.stdlib_module_names, or built in) that
      no entry of that name in `where` or a parent up to the first with no __init__.py can shadow (_import_roots,
      _shadowed; the same verifier's finding: a sibling colorsys.py registered a fixture over `_f` through `from colorsys
      import thing`, the standard library's name proving nothing); every other import, a relative one included, is off
      the list, since the imported module's code or object may register a fixture under any name or rebind
      pytest.fixture (the same finding: `import _rv4p`, whose code rebound pytest.fixture);
    - a def or class whose decorators are each pytest's own (a name, or an attribute chain on a name, bound once at import
      by `import pytest` under any alias or by `from pytest import <attribute>`, that reaches pytest.fixture,
      pytest.yield_fixture, pytest.hookimpl or a pytest.mark attribute, called or not) and whose defaults and annotations
      are proven, a class having no base and no keyword too (a base's __init_subclass__ and a metaclass run when the class
      is made), its body read by these rules, a def's in the def's own scope;
    - an assignment (plain, annotated, or augmented where its target is a subscript of os.environ), a for, an if, a
      while, a try, a del, an expression statement, an assert, a raise, a pass, a global, a nonlocal and a `type`
      statement, and in a def's body a return, whose targets are names or a subscript of os.environ (through a name
      bound once by `import os` or by `from os import environ`) and every expression of which is proven: a literal, an
      f-string, a tuple, list, set or dict display, a name, an
      attribute chain on a name that no import of the module's own package binds (a value of that package's may be a
      fixture registered under any name, as a plant of `thing = _pkg.thing` shows; any other module's values come only
      through an import already off the list), a lambda whose defaults and body are proven, an operator, a comparison, a
      conditional expression, a walrus, a yield or a yield from, over proven parts, a call of pytest.fixture,
      pytest.yield_fixture, pytest.hookimpl or a pytest.mark attribute, reached as a decorator is, and a call of a method
      of os.environ among _ENVIRON_METHODS, reached as its subscript is, each with proven arguments; every other call is
      off the list, since the code a call runs may register a fixture, rebind a name or change pytest's own objects
      (importlib.import_module, exec, eval, globals, setattr, getattr, a def of the module's own, a method of any other
      object, a plugin registered through request.config), and so are a subscript read, a comprehension, a with, a match
      and an await;
    - THE IN-PLACE RULE, in one sentence: an augmented assignment to a name is off the list whatever the name holds,
      since its operator calls the in-place method of the object bound to the name (list.__imul__, dict.__ior__),
      which changes that object where it stands, and the reader proves no object's type (the verifier's finding at
      round 2's thirty-second commit of fork PR #894: `names *= 0` on an alias of a test's list of fixtures, in a listed
      pytest_collectreport and in an autouse fixture that sorts before `_f`, and `|=` on an alias of
      pytest.fixture.__kwdefaults__ at import, of config.option.__dict__ in a listed pytest_configure, and of a
      report's __dict__ in a listed pytest_runtest_makereport, each kept pytest from running a pop the reader counted;
      `n += 1` on a counter is refused with them, a false refusal). An augmented assignment to a subscript of
      os.environ stays on the list: the value it reads is a string, which has no in-place method.
    - no module-level binding of a double-underscore name but __all__ and __doc__ (_PROVEN_DUNDERS), and no binding, in a
      def's or a class's own scope (a parameter, a target, an import, a def or class name, an except name) or by a walrus
      anywhere, of a name the reader resolves as the module's (bound at import to pytest, to a module of the standard
      library or to the module's own package), under which it would read another object as that one.
    THE HOOK CLAUSE: every module-level name beginning pytest_ that the module binds (pytest's prefix for the hook
    implementations it takes from a plugin, which _pytest_hook_impls reads on the module road) is bound once, by a def at
    the top of the module, whose spec (the string literal its one pytest.hookimpl decorator passes as specname=, else its
    name) is one of _LISTED_HOOKS, and whose own body neither returns nor yields a value (_returns_a_value); a hookimpl
    that passes a positional argument, unpacked keywords or a specname= that is not a literal is off the list, and so is
    pytest_plugins, which pytest reads to import plugins.
    What the list takes on trust, all of it outside the module's text: code that runs before the module whatever its text
    says (its package's __init__.py, which Python imports first, a plugin, the interpreter's startup), which may rebind
    pytest.fixture or an attribute of the standard library before the module's first line; a directory ahead of the
    standard library other than those _import_roots names (PYTHONPATH, a .pth file, the directory a run starts in);
    and the methods the forms on the list call implicitly, other than the in-place ones: a plain operator, a comparison,
    an f-string's formatting, an attribute read and a for's iteration run the operands' own methods, which on the
    objects the list reaches (literals and displays, pytest's own objects and the standard library's, and what pytest
    hands a fixture or a hook) make a new object or read one and change none; an object a plugin's fixture hands a def
    is that plugin's code, taken on trust with it.
    tests/conftest.py is not read by this road: its text runs code the list cannot prove (a value of the tests package,
    defs of its own and standard-library functions called at import and in its fixtures and hooks,
    tests/credential_patterns.py loaded through importlib), so the reader reads the fixtures and the hooks of the module
    Python imported instead, and the registration test prints what this road refuses there."""
    where = HERE if where is None else where
    package, dirs = _import_roots(where)
    bindings, _star = _module_name_bindings(tree)
    pytest_roots, std_roots, package_roots, out = {}, {}, set(), []
    todo = list(tree.body)
    while todo:             # loop-ok: bounded by the nodes of the module's import-time code (not a class body's names)
        n = todo.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(n, ast.Import):
            for a in n.names:
                top = a.name.split(".")[0]
                bound = a.asname or top
                if top == "pytest":
                    pytest_roots[bound] = tuple(a.name.split(".")[1:]) if a.asname else ()
                elif package and (a.name == package or package.startswith(a.name + ".")):
                    package_roots.add(bound)
                elif top in sys.stdlib_module_names or top in sys.builtin_module_names:
                    std_roots[bound] = tuple(a.name.split(".")) if a.asname else (top,)
        elif isinstance(n, ast.ImportFrom) and not n.level:
            for a in n.names:
                if n.module == "pytest":
                    pytest_roots[a.asname or a.name] = (a.name,)
                elif (n.module or "").split(".")[0] in sys.stdlib_module_names:
                    std_roots[a.asname or a.name] = tuple(n.module.split(".")) + (a.name,)
        todo.extend(ast.iter_child_nodes(n))
    roots = set(pytest_roots) | set(std_roots) | package_roots

    def off(node, why):
        text = ast.unparse(node).split("\n", 1)[0]
        out.append((getattr(node, "lineno", 0), "%s: %s" % (text if len(text) <= 100 else text[:97] + "...", why)))

    def dunder(node, name, scope):
        if scope == "module" and name.startswith("__") and name.endswith("__") and name not in _PROVEN_DUNDERS:
            off(node, "a module-level binding of %s, which changes what an attribute read or dir() gives, or what a builtin "
                      "name calls, and so what pytest registers" % name)

    def shadow(node, name, scope):
        if scope != "module" and name in roots:
            off(node, "a binding of %s in a def's or a class's own scope, a name the reader resolves as the module's (to "
                      "pytest, the standard library or the module's own package), so it would read another object as "
                      "that one" % name)

    def pytest_path(node):
        parts = _dotted(node)
        if parts and parts[0] in pytest_roots and bindings[parts[0]] == 1:
            path = pytest_roots[parts[0]] + tuple(parts[1:])
            if path in _PYTEST_DECORATORS or path[:1] == ("mark",):
                return path
        return None

    def environ_method(node):
        parts = _dotted(node)
        return bool(parts and len(parts) > 1 and parts[-1] in _ENVIRON_METHODS and parts[0] in std_roots
                    and bindings[parts[0]] == 1 and std_roots[parts[0]] + tuple(parts[1:-1]) == ("os", "environ"))

    def value(n):
        """None when the expression `n` is proven, else why not (its first part off the list)."""
        if n is None or isinstance(n, (ast.Constant, ast.Name)):
            return None
        if isinstance(n, ast.Attribute):
            parts = _dotted(n)
            if parts is None:
                return value(n.value)
            if parts[0] in package_roots:
                return ("%s is a value of the module's own package, which may be a fixture registered under any name"
                        % ".".join(parts))
            return None
        if isinstance(n, ast.Call):
            if pytest_path(n.func) is None and not environ_method(n.func):
                return ("a call of %s: of the calls a module makes the reader proves only pytest.fixture, "
                        "pytest.yield_fixture, pytest.hookimpl, a pytest.mark attribute and a method of os.environ, since "
                        "the code a call runs may register a fixture under any name, rebind a name or change pytest's own "
                        "objects" % ast.unparse(n.func))
            parts = list(n.args) + [k.value for k in n.keywords]
        elif isinstance(n, ast.NamedExpr):
            if n.target.id.startswith("__") and n.target.id.endswith("__") and n.target.id not in _PROVEN_DUNDERS:
                return "a walrus binding %s" % n.target.id
            if n.target.id in roots:
                return "a walrus binding %s, a name the reader resolves as the module's" % n.target.id
            parts = [n.value]
        elif isinstance(n, ast.Lambda):
            a = n.args
            mine = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg] if x is not None and x.arg in roots]
            if mine:
                return "a lambda whose parameter %s is a name the reader resolves as the module's" % mine[0]
            parts = list(a.defaults) + [d for d in a.kw_defaults if d is not None] + [n.body]
        elif isinstance(n, (ast.Yield, ast.YieldFrom)):
            parts = [n.value]
        elif isinstance(n, (ast.Tuple, ast.List, ast.Set)):
            parts = n.elts
        elif isinstance(n, ast.Dict):
            parts = [k for k in n.keys if k is not None] + list(n.values)
        elif isinstance(n, ast.JoinedStr):
            parts = n.values
        elif isinstance(n, ast.FormattedValue):
            parts = [n.value, n.format_spec]
        elif isinstance(n, ast.Starred):
            parts = [n.value]
        elif isinstance(n, ast.BinOp):
            parts = [n.left, n.right]
        elif isinstance(n, ast.BoolOp):
            parts = n.values
        elif isinstance(n, ast.UnaryOp):
            parts = [n.operand]
        elif isinstance(n, ast.Compare):
            parts = [n.left] + list(n.comparators)
        elif isinstance(n, ast.IfExp):
            parts = [n.test, n.body, n.orelse]
        else:
            return "a %s expression, which the reader does not read" % type(n).__name__
        for p in parts:
            why = value(p)
            if why:
                return why
        return None

    def check(node, *exprs):
        for e in exprs:
            why = value(e)
            if why:
                off(node, why)
                return

    def target(t, scope):
        if isinstance(t, ast.Name):
            dunder(t, t.id, scope)
            shadow(t, t.id, scope)
        elif isinstance(t, (ast.Tuple, ast.List)):
            for e in t.elts:
                target(e, scope)
        elif isinstance(t, ast.Starred):
            target(t.value, scope)
        elif (isinstance(t, ast.Subscript) and _dotted(t.value) and _dotted(t.value)[0] in std_roots
              and bindings[_dotted(t.value)[0]] == 1
              and std_roots[_dotted(t.value)[0]] + tuple(_dotted(t.value)[1:]) == ("os", "environ")):
            check(t, t.slice)
        else:
            off(t, "a write through %s, which may rebind a name of the module's or an attribute of pytest's, or change "
                   "an object pytest reads" % ast.unparse(t))

    def module_ok(name, node):
        top = name.split(".")[0]
        if top in sys.stdlib_module_names or top in sys.builtin_module_names:
            where_ = _shadowed(top, dirs)
            if where_ is None:
                return
            off(node, "%s is named like a standard-library module, and %s holds an entry of that name an import may take "
                      "instead (or cannot be listed), whose code may register a fixture or rebind a name" % (top, where_))
            return
        off(node, "an import of %s, a module other than pytest's own, the standard library's and the module's own "
                  "package: its code runs at the import and may register a fixture under any name or rebind "
                  "pytest.fixture" % name)

    def stmts(body, scope):
        for s in body:
            if isinstance(s, ast.Import):
                for a in s.names:
                    dunder(s, a.asname or a.name.split(".")[0], scope)
                    shadow(s, a.asname or a.name.split(".")[0], scope)
                    if a.name.split(".")[0] in _PYTEST_OWN or (package and (a.name == package or package.startswith(a.name + "."))):
                        continue
                    module_ok(a.name, s)
            elif isinstance(s, ast.ImportFrom):
                for a in s.names:
                    if a.name != "*":
                        dunder(s, a.asname or a.name, scope)
                        shadow(s, a.asname or a.name, scope)
                top = (s.module or "").split(".")[0]
                if s.level:
                    off(s, "a relative import: the module it names is of the module's own package, whose code runs at the "
                           "import and whose objects may be fixtures registered under any name")
                elif top in _PYTEST_OWN:
                    for a in s.names:
                        why = ("a star import of pytest's own, which binds names no text spells" if a.name == "*"
                               else _pytest_object_is_fixture(s.module, a.name))
                        if why:
                            off(s, why)
                elif package and (s.module == package or s.module.startswith(package + ".")):
                    off(s, "a `from` import of the module's own package, which may import a submodule (running its code) "
                           "and binds an object of the package's, which may be a fixture registered under any name")
                else:
                    module_ok(s.module, s)
            elif isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                dunder(s, s.name, scope)
                shadow(s, s.name, scope)
                for d in s.decorator_list:
                    if pytest_path(d.func if isinstance(d, ast.Call) else d) is None:
                        off(d, "a decorator that is not pytest's own, which may register a fixture under a name no text "
                               "spells")
                    elif isinstance(d, ast.Call):
                        check(d, *(list(d.args) + [k.value for k in d.keywords]))
                if isinstance(s, ast.ClassDef):
                    if s.bases or s.keywords:
                        off(s, "a class with a base or a keyword: making it runs the base's __init_subclass__ or a "
                               "metaclass's code")
                    stmts(s.body, "class")
                else:
                    a = s.args
                    params = [x for x in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg] if x is not None]
                    check(s, *(list(a.defaults) + [d for d in a.kw_defaults if d is not None]
                               + [x.annotation for x in params if x.annotation is not None] + [s.returns]))
                    for x in params:
                        shadow(s, x.arg, "function")
                    stmts(s.body, "function")
            elif isinstance(s, ast.Assign):
                for t in s.targets:
                    target(t, scope)
                check(s, s.value)
            elif isinstance(s, ast.AnnAssign):
                target(s.target, scope)
                check(s, s.annotation, s.value)
            elif isinstance(s, ast.AugAssign):
                if isinstance(s.target, ast.Name):
                    off(s, "an in-place operator on %s, which calls the in-place method of whatever %s holds and may "
                           "change that object where it stands (a test's list of fixtures, pytest's own defaults, a "
                           "report's fields), where the reader proves no object's type" % (s.target.id, s.target.id))
                target(s.target, scope)
                check(s, s.value)
            elif isinstance(s, (ast.Expr, ast.Return)):
                check(s, s.value)
            elif isinstance(s, (ast.If, ast.While)):
                check(s, s.test)
                stmts(s.body, scope)
                stmts(s.orelse, scope)
            elif isinstance(s, ast.For):
                target(s.target, scope)
                check(s, s.iter)
                stmts(s.body, scope)
                stmts(s.orelse, scope)
            elif isinstance(s, _TRIES):
                stmts(s.body, scope)
                for h in s.handlers:
                    check(h, h.type)
                    if h.name:
                        dunder(h, h.name, scope)
                        shadow(h, h.name, scope)
                    stmts(h.body, scope)
                stmts(s.orelse, scope)
                stmts(s.finalbody, scope)
            elif isinstance(s, ast.Delete):
                for t in s.targets:
                    target(t, scope)
            elif isinstance(s, ast.Assert):
                check(s, s.test, s.msg)
            elif isinstance(s, ast.Raise):
                check(s, s.exc, s.cause)
            elif isinstance(s, (ast.Pass, ast.Global, ast.Nonlocal, ast.Break, ast.Continue)):
                continue
            elif _TYPE_ALIAS is not None and isinstance(s, _TYPE_ALIAS):
                target(s.name, scope)
            else:
                off(s, "a %s statement, which the reader does not read" % type(s).__name__)
    stmts(tree.body, "module")

    def hook_spec(fn):
        """(the spec the def `fn` implements, None) or (None, why the reader cannot read it)."""
        marks = [d for d in fn.decorator_list if pytest_path(d.func if isinstance(d, ast.Call) else d) == ("hookimpl",)]
        if len(marks) > 1:
            return None, "the hook %s carries pytest.hookimpl %d times" % (fn.name, len(marks))
        spec = fn.name
        for d in marks:
            if not isinstance(d, ast.Call):
                continue
            if d.args or any(k.arg is None for k in d.keywords):
                return None, ("the hook %s's pytest.hookimpl passes a positional argument or unpacked keywords, either of "
                              "which may name the hook it implements (specname)" % fn.name)
            for k in d.keywords:
                if k.arg == "specname":
                    if isinstance(k.value, ast.Constant) and isinstance(k.value.value, str):
                        spec = k.value.value
                    elif not (isinstance(k.value, ast.Constant) and k.value.value is None):
                        return None, "the hook %s's specname= is not a string literal" % fn.name
        return spec, None
    tops = collections.defaultdict(list)
    for s in tree.body:
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
            tops[s.name].append(s)
    for name in sorted(n for n in bindings if n.startswith("pytest_")):
        if name == "pytest_plugins":
            off(_first_binding(tree, name), "pytest_plugins, which pytest reads to import plugins whose hooks and fixtures "
                                            "the reader does not read")
            continue
        if bindings[name] != 1 or len(tops[name]) != 1:
            off(_first_binding(tree, name), "%s, a name pytest takes a hook implementation from (a routine whose name "
                                            "begins pytest_), bound at import %d times and by %d defs at the top of the "
                                            "module, where the reader proves one binding, that def" % (
                                                name, bindings[name], len(tops[name])))
            continue
        fn = tops[name][0]
        spec, why = hook_spec(fn)
        if why:
            off(fn, why)
        elif spec not in _LISTED_HOOKS:
            off(fn, "a hook implementation of %s, which pytest may call to decide whether a fixture runs before a test, "
                    "or in its place: the reader proves only the hooks of _LISTED_HOOKS" % spec)
        if _returns_a_value(fn):
            off(fn, "the hook %s returns or yields a value, which pytest may read as the hook's result (a report made to "
                    "pass, a fixture's value)" % name)
    return sorted(out)


def _why_not_registered_once(fn, bindings, star, names=None):
    """None when the module's text registers the module-level fixture def `fn`, and nothing else, under the name it is
    registered by, else why not (the text road's per-fixture half; _unproven_statements is the other). Pytest registers
    the fixtures it finds among the module's attributes after the import, each under its name= keyword when the decorator
    passes one, else under the attribute's name, and of two fixtures a module registers under one name it runs the one
    it registered last (the attributes in dir()'s order) and never the other's body. So: the def's name is the one
    binding it has at import (_module_name_bindings) and no star import could bind it (the verifier's finding on round 2
    of fork PR #894: the reader counted a fixture shadowed by a later `def _f(): yield` or `_f = None`, which a child
    pytest showed never ran; a binding before the def, which the def replaces, is refused too, the safe side: bound
    once, not bound last); and, from `names` (_fixture_names_by_keyword over the same tree), the name it registers under
    is registered by no other call's name= (the same verifier's finding at the next commit: a fixture of another def
    given `name="_f"` shadows `_f` whatever its own attribute is called; a name= on ANY call counts since the verifier's
    finding at the eighteenth commit, a fixture function reached through functools.partial or getattr registering it
    too), and when the def passes name= itself, that name is a string literal, equal to the def's own name or bound by no
    statement of the module (a def or an assignment of that name may register a fixture under it by a spelling the reader
    does not see; the safe side), and no call in the module passes a name= that is not a literal or unpacks keywords,
    which could register any name. `names` None reads no name= at all."""
    if bindings[fn.name] != 1:
        return "the module binds its name %s %d times at import, and pytest registers what the name holds at the end" % (
            fn.name, bindings[fn.name])
    if star:
        return "a star import at import time may bind its name"
    if names is None:
        return None
    if names.unknown:
        return "a call of the module passes a name= that is not a string literal, or unpacks keywords, which may register any name"
    own = [kw.value.value for d in fn.decorator_list
           if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in _FIXTURE_FUNCTIONS
           for kw in d.keywords if kw.arg == "name" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str)]
    if not own:
        return None if names.by_keyword[fn.name] == 0 else "another call passes name=%r, which registers a fixture over it" % fn.name
    if len(own) != 1:
        return "its decorators pass name= %d times" % len(own)
    if names.by_keyword[own[0]] != 1:
        return "its name=%r is passed by another call too, which registers a fixture over it" % own[0]
    if own[0] != fn.name and bindings[own[0]] != 0:
        return "its name=%r is a name the module binds, which may register a fixture under it" % own[0]
    return None


def _pytest_registrations(module):
    """[(attribute, name, autouse, scope, (file, def name, first line) or None)] for the fixtures pytest registers from
    `module`'s attributes, in the order it registers them, each part of the rule with its plant (the registration test's
    child cases, where the module road's verdict over these registrations is held to what the child pytest ran): each
    name dir(module) lists, in that order (planted: a module-level __dir__ that leaves the fixture's name out), whose
    attribute is a FixtureFunctionDefinition (planted: every case), registered under its marker's name when the marker
    has one (planted: another def given the fixture's name=, and the fixture renamed by its own decorator), else under
    the attribute's name (planted: the fixture aliased under a second name); an attribute that raises when read is
    skipped (planted directly, by the module road's test). Of the fixtures one module registers under one name, the
    last registered is the one pytest runs (planted: another def given the name, registered after it, and one sorting
    before it). The last entry is the code of the function the fixture wraps (_why_pytest_does_not_run matches it).
    Self-contained, for the child pytest of the registration test, which runs this function's own source over each
    synthetic conftest it imports. Raises when _pytest.fixtures has no FixtureFunctionDefinition; the caller refuses,
    naming the error (planted by the module road's test)."""
    import os
    from _pytest.fixtures import FixtureFunctionDefinition
    out = []
    for attr in dir(module):
        try:
            obj = getattr(module, attr)
        except Exception:
            continue
        if type(obj) is not FixtureFunctionDefinition:
            continue
        marker = obj._fixture_function_marker
        code = getattr(obj._get_wrapped_function(), "__code__", None)
        out.append((attr, marker.name or attr, marker.autouse, marker.scope,
                    (os.path.realpath(code.co_filename), code.co_name, code.co_firstlineno) if code is not None else None))
    return out


def _why_pytest_does_not_run(fn, registrations, path):
    """None when pytest runs the module-level def `fn` of the file at `path` before every test as a function-scoped
    autouse fixture, read from `registrations` (_pytest_registrations), else why not; each part of THE CODE MATCH with
    its plant (the registration test's child cases): a fixture of the module wraps fn's code, matched by the file
    (planted: another file's def of the name at the fixture's first line), the def's name (planted: a def of another
    name compiled in the conftest's file at that line) and its first line, the first decorator's (planted: a second
    def of the name later in the conftest); the last fixture registered under the name it is registered by wraps that
    code too (planted: another def given the fixture's name=); and that one's marker is autouse (planted: the fixture's
    own function registered again without autouse) with scope "function" (planted: the same, module-scoped)."""
    code = (os.path.realpath(path), fn.name, (fn.decorator_list[0] if fn.decorator_list else fn).lineno)
    mine = [r for r in registrations if r[4] is not None and tuple(r[4]) == code]
    if not mine:
        return ("no fixture of the module wraps this def once its import ends: its name holds something else, or what "
                "its decorator made is not a fixture pytest registers")
    whys = []
    for _attr, name, _autouse, _scope, _code in mine:
        last = [r for r in registrations if r[1] == name][-1]
        if last[4] is None or tuple(last[4]) != code:
            whys.append("it is registered under %s, and pytest registers %s under that name after it and runs that"
                        % (name, last[0]))
        elif last[2] is not True or last[3] != "function":
            whys.append("pytest registers it under %s with autouse=%r and scope=%r, which do not run it before every test"
                        % (name, last[2], last[3]))
        else:
            return None
    return "; ".join(whys)


def _pytest_hook_impls(module):
    """[(attribute, spec)] for every hook implementation pytest takes from `module` when it registers it as a plugin, as a
    conftest is, read by the installed pytest's own parse (PytestPluginManager.parse_hookimpl_opts over dir(module), in
    the order pluggy's register reads them), each part with its plant (the hook test: its module road half on module
    objects, and its child runs, where the hooks read equal the hooks pytest registered from each conftest): an
    attribute whose name begins pytest_ (planted: a routine not named so reads as no hook) and that is a routine
    (planted: a def, a lambda and a builtin read, a number and a class not), listed by dir() (planted: a routine the
    module's own __dir__ leaves out is not read), under the spec its pytest.hookimpl marker names by specname=
    (planted), else under its own name; and ("pytest_plugins", None) when the module has that attribute (planted),
    which pytest reads to import more plugins. Self-contained, for the child pytest of the registration tests, which
    runs this function's own source over each synthetic conftest it imports and compares the specs with the hooks
    pytest registered from it; raises as the parse raises (an attribute that raises when read); the caller refuses,
    naming the error."""
    from _pytest.config import PytestPluginManager
    parse = PytestPluginManager().parse_hookimpl_opts
    out = []
    for attr in dir(module):
        opts = parse(module, attr)
        if opts is not None:
            out.append((attr, opts.get("specname") or attr))
    if hasattr(module, "pytest_plugins"):
        out.append(("pytest_plugins", None))
    return out


def _why_a_hook_may_stop_it(hooks):
    """None when every hook implementation in `hooks` (_pytest_hook_impls) is of a spec on _LISTED_HOOKS and the module
    has no pytest_plugins, else why not, naming each other one: the module road's half for the hooks (the verifier's
    finding at round 2's thirty-first commit of fork PR #894: a conftest's pytest_fixture_setup, pytest_generate_tests or
    pytest_collection_modifyitems kept pytest from running a fixture whose registration the reader had proven). A hook
    off the list refuses every fixture of the module, since one hook can reach every fixture."""
    whys = []
    for attr, spec in hooks:
        if spec is None:
            whys.append("it has pytest_plugins, which pytest reads to import plugins whose hooks and fixtures the reader "
                        "does not read")
        elif spec not in _LISTED_HOOKS:
            whys.append("it implements the hook %s%s, which pytest may call to decide whether a fixture runs before a test, "
                        "or in its place: the reader proves only the hooks of _LISTED_HOOKS"
                        % (spec, "" if attr == spec else " (as %s)" % attr))
    return "; ".join(whys) or None


def _real_conftest_module():
    """tests/conftest.py as Python imported it: tests.conftest, the name pytest imports it under in this tree (tests/ is a
    package, and pytest's default prepend import), which the test modules import restore_env from too; so under pytest
    it is the module pytest registered, and under any other runner this import runs it."""
    from tests import conftest
    return conftest


def _registration_refusals(tree, candidates, real, where=None):
    """{id(def): None, or why the reader cannot prove pytest runs it} for each def of `candidates` (the function-scoped
    autouse fixture defs of `tree`), by the reader's two roads. THE MODULE ROAD, for tests/conftest.py (`real`): the
    fixtures of the module Python imported (_real_conftest_module), read the way pytest registers them
    (_pytest_registrations, _why_pytest_does_not_run), and its hook implementations, read the way pytest takes them
    (_pytest_hook_impls, _why_a_hook_may_stop_it: a hook off _LISTED_HOOKS, or pytest_plugins, refuses every fixture); a
    module that cannot be imported, is not tests/conftest.py, or whose fixtures or hooks cannot be read so refuses every
    fixture, naming why. THE TEXT ROAD, for a source handed in: every fixture is refused while any statement of the
    module, wherever it stands, or any of its hook implementations is off the proven list (_unproven_statements), and
    otherwise each is read by its own registration (_why_not_registered_once)."""
    if not candidates:
        return {}
    if real:
        try:
            module = _real_conftest_module()
        except Exception as e:
            return dict.fromkeys(map(id, candidates), "the reader reads what pytest registers from tests/conftest.py in "
                                 "the module Python imported, and importing tests.conftest failed (%s: %s)"
                                 % (type(e).__name__, e))
        file = getattr(module, "__file__", None)
        if not file or os.path.realpath(file) != os.path.realpath(os.path.join(HERE, "conftest.py")):
            return dict.fromkeys(map(id, candidates), "the module read is %r, not tests/conftest.py" % (file,))
        try:
            registrations = _pytest_registrations(module)
        except Exception as e:
            return dict.fromkeys(map(id, candidates), "the reader could not read the module's fixtures the way pytest "
                                 "registers them (%s: %s)" % (type(e).__name__, e))
        try:
            hooks = _pytest_hook_impls(module)
        except Exception as e:
            return dict.fromkeys(map(id, candidates), "the reader could not read the module's hook implementations the way "
                                 "pytest takes them (%s: %s)" % (type(e).__name__, e))
        stop = _why_a_hook_may_stop_it(hooks)
        if stop:
            return dict.fromkeys(map(id, candidates), stop)
        return {id(fn): _why_pytest_does_not_run(fn, registrations, file) for fn in candidates}
    unproven = _unproven_statements(tree, where)
    if unproven:
        why = ("its module has code the reader cannot prove leaves pytest registering and running its fixtures: "
               + "; ".join("line %d: %s" % u for u in unproven))
        return dict.fromkeys(map(id, candidates), why)
    bindings, star = _module_name_bindings(tree)
    names = _fixture_names_by_keyword(tree)
    return {id(fn): _why_not_registered_once(fn, bindings, star, names) for fn in candidates}


def _conftest_reasserted_names(src=None, where=None):
    """The environment names tests/conftest.py re-asserts before every test, as _Reasserted(writes, removals, refused):
    two frozensets kept apart (a pin that reads a pop asks for the removals), and one line per fixture refused.
    THE RULE (the ruling on the verifier's findings at round 2's twentieth commit of fork PR #894, and the hook clause
    since its thirty-first): a function-scoped autouse fixture counts only when the reader proves that the fixture pytest
    runs under the name this def is registered by is this def and that no hook of the module but those on _LISTED_HOOKS
    can keep pytest from running it, and anything it cannot prove is refused, named in `refused`. It reads for
    tests/conftest.py the fixtures and the hooks of the module Python imported, as pytest registers them, and for a
    source handed in its text alone, where every statement, wherever it stands, and every hook implementation must be on
    the proven list and every name the def could be registered under bound once in the module, by the def or its literal
    name=, and registered by no other call; so a road not yet named is refused rather than counted
    (_registration_refusals has the two roads, and _unproven_statements the list).
    WHY TWO ROADS: before this ruling the reader closed the class one case at a time, each found by a child pytest in
    which a counted fixture never ran (a later binding of the fixture's name, the sixteenth commit; another def given its
    name=, the seventeenth; a name= passed through functools.partial or getattr, the eighteenth; a decorator or a name
    imported from another module, the nineteenth; a module named like the standard library's that a sibling file
    shadows, and an imported module whose code rebinds pytest.fixture, the twentieth; a hook of the conftest that keeps
    pytest from running a fixture it registered, the thirty-first; an in-place operator on a name bound to a test's
    list of fixtures, pytest.fixture's defaults, pytest's options or a report, the thirty-second, which the text road
    now refuses by _unproven_statements' in-place rule), and the proof by text alone cannot take
    tests/conftest.py, whose import-time code takes values from the tests package, calls defs of its own and the
    standard library, and loads tests/credential_patterns.py through importlib, and whose fixtures and hooks call code of
    their own (a refusal there would fault the eight licences marked `reasserted`), so for tests/conftest.py the reader
    reads the registration and the hooks themselves.
    WHAT IS COUNTED, once proven: a name the fixture sets by a plain assignment, or pops by a pop as a statement, as one of
    the statements that run before its yield on every run (_statements_before_the_yield), unconditionally: a statement
    of the fixture's own body, or one of the body of a for over a non-empty tuple of string literals there
    (_literal_tuple_loop; `for var in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV"): os.environ[var] = ...` re-asserts
    both, and a rule without it reds the correct conftest). Refused, each read here as no re-assert (the reviewer's
    ruling of round 1 on fork PR #894, where any write or pop anywhere in an autouse fixture counted): a setdefault or any
    other write shape; a fixture scoped above function or by a scope that is not a literal; a statement after the yield,
    or after any statement that holds a return or a raise at any depth (a return nested in an if, a try, a with, a loop or
    a match ends the fixture on the runs where it is reached, and the verifier's finding on round 2 of fork PR #894
    showed a test reading the name unasserted after an `if ...: return`); one under an if, while, with, try or match, or
    in a for over anything else; one in a def or class nested in the fixture; a del. Re-asserted so, a module-level write
    of the name cannot outlive collection under pytest (the dead-port fixture's rule, 2026-08-27); the value conftest
    writes is not read (the licence's property does not depend on it).
    What it does not read, each passing as no re-assert (the safe side, a licence that rests on it faults): a write
    through a call the fixture makes, and a pop whose value is assigned. Not read as an end, and harmless: an exception
    a call or an assert raises before the statement (pytest.skip, pytest.fail, sys.exit, a failing assert), which errors
    or skips the test before its body runs, so no test body reads the name unasserted, unless a pytest_runtest_makereport
    makes the failed setup's report pass (below). What it does not see, each read as a re-assert although pytest may not
    run the fixture for some test (the unsafe side; no pin reds on them): what code outside tests/conftest.py does, a
    fixture of the same name defined closer to a test (in a test module, a class or a conftest.py below tests/), which
    pytest resolves for that test in place of this one, a test module's parametrization of the fixture's name (its
    pytest_generate_tests, or a parametrize mark naming it), and a hook of another conftest or of an installed plugin,
    since the reader reads tests/conftest.py alone. On the module road, what tests/conftest.py's own code does beyond
    what pytest registers from it, which the reader takes on trust since it would refuse the conftest if it read that
    code by the proven list (the text road refuses it on the statements the registration test prints): its import-time
    code, its fixtures' bodies and the bodies of its hooks on _LISTED_HOOKS may register a plugin, patch pytest's code,
    change pytest's options or edit a test's fixtures (a fixture that registers a plugin whose hook takes `_f` out of
    each test's fixtures is planted, a pop the reader counts and pytest never runs, and so are an in-place operator
    that empties a test's list of fixtures in a listed pytest_collectreport and in an autouse fixture, and one that
    turns on pytest's setup plan in a listed pytest_configure), and its pytest_runtest_makereport may make a failed
    setup's report pass, which runs the test's body after a fixture raised before its re-assert (planted too, by an
    attribute write and by an in-place operator on the report's __dict__; the conftest's own turns a skip into a
    failure and redacts text); and an attribute of tests.conftest that code sets or
    deletes after pytest registered the module's fixtures (pytest read them once, at the conftest's import, and the
    reader reads them when it runs; the one test that sets an attribute of it in the test process,
    tests/test_tempdir_hygiene.py's patch of _TMP_ROOT, puts it back). The execution proof below runs a copy of
    tests/conftest.py and refuses what that code does to keep a counted fixture from re-asserting a name in a test of
    its child's context, for every name this reader counts (and test_a_port_one_test_sets_is_gone_when_the_next_test_starts
    does so for ROMP_POSTAL_PORT beside it); the next paragraph names that context and what the proof does not read.
    On the text road, what _unproven_statements takes on trust (code that runs
    before the module whatever its text says, and directories ahead of the standard library that _import_roots does
    not name).
    THIS IS THE FILTER, REFUSE-ONLY (the reviewer's ruling of 2026-09-24 21:09Z on round 2 of fork PR #894, (1)): a
    name it counts is a candidate, and no licence rests on it alone. The licence's condition is
    _conftest_reasserts_proved, which grants a name only where a child pytest over a copy of the conftest observes the
    counted fixture's own re-assert (_reassert_proof) in each read of the child's context (the ruling of 23:17Z, (4);
    _PROOF_READS, _proof_modes): V1, the conftest and the probe modules in a directory named tests; V3, a module
    collected first and one collected after it; V4, in each, function tests and a unittest TestCase; V5, a run with no
    xdist worker and, where pytest-xdist is installed, a run with -n 2. A road in the conftest's own code, in the code
    that runs before it or in pytest that keeps pytest from running that re-assert in a test of that context, keyed on
    those facts alone or together, is refused, named above or not (planted: the module road's residuals and every
    facet of _proof_facets, and a road keyed on each fact, on its complement and on one conjunction,
    _proof_context_roads). WHAT THE PROOF DOES NOT READ, each granted where the filter counts it (the unsafe side, as
    above): any conftest hook condition the child's context does not reproduce, a mark, an environment variable, a
    host name, or another collection-time signal (the witness, V2: a copy of tests/conftest.py whose listed
    pytest_collectreport takes _dead_manager_port out of each marked test is granted, and a real run of that copy reads
    a module-level write in a marked test and the floor in the unmarked control); what a real test module, a class or
    a conftest.py below tests/ does for its own tests (a fixture of the same name, a parametrization of it, a hook),
    since the child runs the conftest beside probe modules of its own; a plugin a run loads by -p on its command line,
    which the child is not given; and an attribute of tests.conftest a test changes in the test process after pytest
    registered it. The filter still refuses every fixture of a module with a hook off _LISTED_HOOKS
    (test_a_hook_that_may_keep_pytest_from_running_a_fixture_refuses_it_on_both_roads), so that limit is reached only
    by code the module road takes on trust (import-time code, a fixture's body, a listed hook's body) that keys a
    removal on such a condition."""
    sites, refused = _reassert_sites(src, where)
    return _Reasserted(frozenset(n for n, s in sites.items() if any(op == "write" for _f, _l, op in s)),
                       frozenset(n for n, s in sites.items() if any(op == "pop" for _f, _l, op in s)), refused)


def _reassert_sites(src=None, where=None):
    """THE FILTER's reading (_conftest_reasserted_names' rule), with the fixture behind each name: ({name: frozenset of
    (def name, first line, "write" or "pop")}, refused), one entry per function-scoped autouse fixture def the reader did
    not refuse that sets or pops the name before its yield, its first line the one its code carries (the first
    decorator's), and REFUSED, one line per fixture refused (_Reasserted.refused's form). The execution proof reads a
    name as re-asserted only where the child pytest sees the code of one of these defs set or pop it."""
    tree = ast.parse(open(os.path.join(HERE, "conftest.py"), encoding="utf-8", errors="replace").read() if src is None else src)
    names = _EnvNames(tree)
    candidates = [fn for fn in tree.body
                  if isinstance(fn, ast.FunctionDef) and _is_autouse_fixture(fn) and _is_function_scoped_fixture(fn)]
    whys = _registration_refusals(tree, candidates, src is None, where)
    sites, refused = collections.defaultdict(set), []
    for fn in candidates:
        if whys[id(fn)]:
            refused.append("%s (line %d): %s" % (fn.name, fn.lineno, whys[id(fn)]))
            continue
        scope = names.within(fn)
        before = _statements_before_the_yield(fn.body)
        found = [_plain_reasserts(before, scope)]
        for st in before:
            loop = _literal_tuple_loop(st)
            if loop is not None:
                found.append(_plain_reasserts(st.body, scope, loop))
        line = (fn.decorator_list[0] if fn.decorator_list else fn).lineno
        for w, r in found:
            for name in w:
                sites[name].add((fn.name, line, "write"))
            for name in r:
                sites[name].add((fn.name, line, "pop"))
    return {name: frozenset(s) for name, s in sites.items()}, tuple(refused)


_REASSERT_SENTINEL = "45678"
#   the value the execution proof's probe module writes to each name at its import and its second test writes again:
#   one no licence covers and no fixture of tests/conftest.py writes, so a probe test that reads it read a write the
#   conftest did not re-assert over

_REASSERT_PROBE = textwrap.dedent('''\
    import _collections_abc, json, os, re, sys, unittest

    NAMES, SENTINEL = __NAMES__, __SENTINEL__
    for _name in NAMES:
        os.environ[_name] = SENTINEL        # the licensed shape: a module-level write, run at collection


    def _recorder():
        """One recorder per process, a second probe module reusing it: each write and pop of a str key of the
        environment (os._Environ's __setitem__ and __delitem__, which an assignment, a del, a pop, a setdefault and an
        update reach) as [key, "write" or "pop", the code that made it (file, def name, first line of the first frame
        outside _collections_abc, whose code carries the file name MutableMapping's own functions carry, a frozen
        module's included: os.environ.pop runs MutableMapping.pop there, which deletes the key), PYTEST_CURRENT_TEST at
        the time]."""
        setitem, delitem = os._Environ.__setitem__, os._Environ.__delitem__
        if hasattr(setitem, "reassert_events"):
            return setitem.reassert_events
        events = []
        own = {_collections_abc.MutableMapping.pop.__code__.co_filename}

        def code():
            f = sys._getframe(2)
            while f is not None and f.f_code.co_filename in own:
                f = f.f_back
            return None if f is None else [os.path.realpath(f.f_code.co_filename), f.f_code.co_name, f.f_code.co_firstlineno]

        def record_set(self, key, value):
            if isinstance(key, str) and key != "PYTEST_CURRENT_TEST":
                events.append([key, "write", code(), os.environ.get("PYTEST_CURRENT_TEST")])
            return setitem(self, key, value)

        def record_del(self, key):
            if isinstance(key, str) and key != "PYTEST_CURRENT_TEST":
                events.append([key, "pop", code(), os.environ.get("PYTEST_CURRENT_TEST")])
            return delitem(self, key)
        record_set.reassert_events = events
        os._Environ.__setitem__, os._Environ.__delitem__ = record_set, record_del
        return events


    EVENTS = _recorder()


    def _read_then_set():
        """What the running test's setup phase did to each name and the value its body reads, in a file of its own
        under proof-reports/ beside the module; then each name set and left, as a test can, so the next probe test's
        setup finds each set (a pop of an unset name deletes nothing, so nothing would show its re-assert)."""
        test = os.environ["PYTEST_CURRENT_TEST"].rsplit(" (", 1)[0]
        seen = {n: {"setup": [e[1:3] for e in EVENTS if e[0] == n and e[3] == test + " (setup)"], "value": os.environ.get(n)}
                for n in NAMES}
        at = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proof-reports")
        os.makedirs(at, exist_ok=True)
        with open(os.path.join(at, re.sub(r"\\W", "_", test) + ".json"), "w", encoding="utf-8") as f:
            json.dump({"test": test, "seen": seen}, f)
        for name in NAMES:
            os.environ[name] = SENTINEL


    def test_1_reads_then_sets():
        _read_then_set()


    def test_2_reads_then_sets():
        _read_then_set()


    class ProbeCase(unittest.TestCase):
        def test_1_reads_then_sets(self):
            _read_then_set()

        def test_2_reads_then_sets(self):
            _read_then_set()
''')
#   THE EXECUTION PROOF's probe module, two per case directory (_reassert_proof): it writes each probed name at its
#   import, the licensed shape, and installs the recorder; as function tests and again as a unittest TestCase, each of
#   its two tests reads each name and then sets each and leaves it, each read written to a file of its own (the run
#   captures a passing test's output). The
#   recorder's skip of the mapping's own frames is planted by every pop (os.environ.pop runs in _collections_abc, so a
#   recorder that skipped nothing would name that frame, and the control and tests/conftest.py's pops would be refused),
#   and its reading of a frozen module's file name by every pop on Python 3.11 and later, where _collections_abc is
#   frozen and its code's file name is not the module's __file__. It skips no frame of os's (the verifier's finding at
#   round 2's thirty-fourth commit of fork PR #894: that skip had no plant, and no write or pop the filter counts runs
#   through os's own code, so it is cut)

_PROOF_MODES = {"serial": "in a run with no xdist worker", "xdist": "on an xdist worker of a run with -n 2"}
_PROOF_READS = tuple(((module, cls, test), "the %s test of %s, %s" % (when, where, kind))
                     for module, where in (("a", "the first module collected"), ("b", "a module collected after it"))
                     for cls, kind in (("", "a function test"), ("ProbeCase", "a unittest TestCase test"))
                     for test, when in (("test_1_reads_then_sets", "first"), ("test_2_reads_then_sets", "second")))
#   THE CHILD'S CONTEXT (the reviewer's ruling of 2026-09-24 23:17Z on round 2 of fork PR #894, (4)): the reads the
#   proof requires of each run it makes (_proof_modes), keyed (module, class, test), the module by its last letter.
#   Each case directory is named tests (V1), holds a probe module collected first and one collected after it (V3), each
#   read as function tests and as a unittest TestCase (V4), and the run is made with no xdist worker and with -n 2
#   (V5): every combination of V3, V4 and V5 is read, and _proof_context_roads plants a road keyed on each fact


def _proof_modes():
    """The runs the execution proof makes: one with no xdist worker, and one with -n 2 where pytest-xdist is installed
    in this interpreter. Where it is not, as in CI's pytest job, which does not install it, no run of the suite in this
    interpreter has an xdist worker, so no road keyed on one can keep a fixture from a test here."""
    return ("serial", "xdist") if importlib.util.find_spec("xdist") is not None else ("serial",)


def _proof_verdicts(sites, reports, conftest, rcs):
    """{name: None, or why the execution proof refuses it} for each name of `sites` (_reassert_sites' form), from
    `reports` ({mode: {(module, class, test): the probe's report}} for each run the proof made, _PROOF_READS' keys),
    `conftest`, the realpath of the case's conftest.py in the child, and `rcs` ({mode: the run's return code}). THE
    FIXTURE'S OWN RE-ASSERT is what is read, not the value alone, in EACH read of _PROOF_READS in each run. Each part
    of the match with its plant (_proof_facets, run by
    test_a_re_asserted_licence_holds_only_where_a_child_pytest_sees_the_fixtures_own_re_assert): among the writes and
    pops the recorder saw in the SETUP of the first probe test a process runs, after the import's write (planted: a
    listed makereport that makes a failed setup pass, whose fixture raises in a process's first setup and pops in the
    later ones), and of each later one, after a probe test's write (planted: the fixture rebound to a module-scoped
    fixture, which pops in its module's first setup alone), those setups' own events and no others (planted: a fixture
    that pops in the first test's setup and after every test, never in a later test's setup, which a read of every
    event so far would grant), one is by the code of a def `sites` counts for the name, matched by its file (planted:
    another file's def of the name at the fixture's first line), its def name (planted: a def of another name compiled
    in the conftest's file at that line), its first line (planted: a later def of the fixture's name) and the operation
    counted (planted: the fixture sets a name counted as popped);
    and the test's body then reads something other than the probe's value (planted: the fixture's pop undone by a
    fixture that sorts after it). A read not reported refuses the name (planted: the probe's second tests taken out of
    the run). Refusals are grouped by their reason, each naming the reads it holds for."""
    out = {}
    for name in sorted(sites):
        codes = {(conftest, fname, line, op) for fname, line, op in sites[name]}
        whys = collections.OrderedDict()
        for mode in sorted(reports):
            for key, where in _PROOF_READS:
                rep = reports[mode].get(key)
                if rep is None:
                    why = "reported no read (the run's return code %d)" % rcs[mode]
                else:
                    got = rep["seen"][name]
                    if not any(e[1] is not None and (e[1][0], e[1][1], e[1][2], e[0]) in codes for e in got["setup"]):
                        why = "the counted fixture's own code (%s) did not set or pop it in the test's setup; the setup %s" % (
                            ", ".join("%s at line %d, %s" % (f, ln, op) for f, ln, op in sorted(sites[name])),
                            "; ".join("%s it from %s" % ("set" if op == "write" else "popped",
                                                         "%s (%s, line %d)" % (c[1], os.path.basename(c[0]), c[2]) if c else "no frame")
                                      for op, c in got["setup"]) or "neither set nor popped it")
                    elif got["value"] == _REASSERT_SENTINEL:
                        why = "read the value the probe wrote, %r, after the counted fixture's re-assert" % _REASSERT_SENTINEL
                    else:
                        continue
                whys.setdefault(why, []).append("%s, %s" % (where, _PROOF_MODES[mode]))
        total = len(_PROOF_READS) * len(reports)
        out[name] = "; ".join("%s (%s)" % (why, "in each of the %d reads" % total if len(at) == total else "in " + " | ".join(at))
                              for why, at in whys.items()) or None
    return out


def _reassert_proof(cases, real=False):
    """THE EXECUTION PROOF (the reviewer's ruling of 2026-09-24 21:09Z on round 2 of fork PR #894, (1): a static reader
    with no closed boundary is replaced by the property, run, here in the context of the ruling of 23:17Z, (4); what
    that does not read is named at the end of _conftest_reasserted_names' docstring). A child pytest over a scratch root
    holding a directory per case of `cases` ((label, conftest text, or None for a copy of tests/conftest.py, {helper
    file: text}, sites in _reassert_sites' form)), run once for each of _proof_modes (-q, the default capture, and -n 2
    for the second): each directory, cNN/tests, has its conftest.py, its helpers (a name may carry a directory) and two
    probe modules (_REASSERT_PROBE) over the names of its sites, collected in the order _PROOF_READS names. With
    `real`, tests/credential_patterns.py is copied beside each conftest (tests/conftest.py loads it by path) and the
    checkout is put on PYTHONPATH (it imports the tests package), as the executed checks that copy tests/conftest.py
    do. The child's environment drops PYTEST_CURRENT_TEST and the probed names, and its TMPDIR is the scratch root,
    which is removed after. Returns ({label: _proof_verdicts over the case's reports}, 0 or the first nonzero return
    code of the runs, their output)."""
    root = os.path.realpath(tempfile.mkdtemp())
    try:
        subs = []
        for i, (label, text, helpers, sites) in enumerate(cases):
            sub = os.path.join(root, "c%02d" % i, "tests")
            os.makedirs(sub)
            subs.append(sub)
            files = dict(helpers)
            for module in "ab":
                files["test_reassert_probe_%02d_%s.py" % (i, module)] = (_REASSERT_PROBE.replace("__NAMES__", repr(sorted(sites)))
                                                                          .replace("__SENTINEL__", repr(_REASSERT_SENTINEL)))
            if text is None:
                shutil.copy(os.path.join(HERE, "conftest.py"), os.path.join(sub, "conftest.py"))
            else:
                files["conftest.py"] = text
            if real:
                shutil.copy(os.path.join(HERE, "credential_patterns.py"), os.path.join(sub, "credential_patterns.py"))
            for name, body in files.items():
                at = os.path.join(sub, name)
                os.makedirs(os.path.dirname(at), exist_ok=True)
                with open(at, "w", encoding="utf-8") as f:
                    f.write(body)
        probed = {n for _l, _t, _h, sites in cases for n in sites}
        child = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST" and k not in probed}
        if real:
            child["PYTHONPATH"] = os.pathsep.join(p for p in (os.path.dirname(HERE), child.get("PYTHONPATH")) if p)
        child["TMPDIR"] = root
        reports, rcs, outs = [{} for _c in cases], {}, []
        for mode in _proof_modes():
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
                               + (["-n", "2"] if mode == "xdist" else []) + ["--rootdir", root, root],
                               cwd=root, env=child, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
            rcs[mode] = r.returncode
            outs.append("[the run %s: return code %d]\n%s%s" % (_PROOF_MODES[mode], r.returncode, r.stdout, r.stderr))
            for i, sub in enumerate(subs):
                got, at = {}, os.path.join(sub, "proof-reports")
                for fn in sorted(os.listdir(at)) if os.path.isdir(at) else ():
                    with open(os.path.join(at, fn), encoding="utf-8") as f:
                        rep = json.load(f)
                    path, _sep, rest = rep["test"].partition("::")
                    cls, _sep, test = rest.rpartition("::")
                    got[(os.path.basename(path)[:-3].rsplit("_", 1)[1], cls, test)] = rep
                shutil.rmtree(at, True)
                reports[i][mode] = got
        verdicts = {label: _proof_verdicts(sites, reports[i], os.path.join(subs[i], "conftest.py"), rcs)
                    for i, (label, _t, _h, sites) in enumerate(cases)}
        return verdicts, next((rc for rc in rcs.values() if rc), 0), "\n".join(outs)
    finally:
        shutil.rmtree(root, True)


def _conftest_reasserts_proved(src=None, where=None, helpers=None, real=None):
    """THE CONDITION A `reasserted` LICENCE RESTS ON (the reviewer's ruling of 2026-09-24 21:09Z on round 2 of fork PR
    #894, (1)): _Reasserted(writes, removals, refused) of the names tests/conftest.py (or `src`, beside `helpers`, read
    as sitting in `where`) re-asserts before every test, each PROVED BY EXECUTION: the filter (_reassert_sites,
    refuse-only) names the candidates and the fixture def behind each, and a child pytest over the conftest
    (_reassert_proof) grants a name only where it observes that def's own code set or pop it in the setup of each
    probe test of the child's context, each following a write of the name (the module-level write for the first probe
    test a process runs, a probe test's for the rest). REFUSED: the filter's refusals, and one line per name the proof
    refused, `NAME: why`. The filter may refuse early and never grants: a shape it does not model, which it counts, is
    refused by the run wherever it keeps pytest from running the re-assert in a test of that context, and granted
    where it keys on a condition the context does not reproduce. `real` (default: `src` is None) runs the child as
    tests/conftest.py's copy runs, beside tests/credential_patterns.py with the checkout on PYTHONPATH. For
    tests/conftest.py itself the result is read once per run of this module and held by the _Census ("proofs") until
    tearDownModule's release. What the proof does not read is named at the end of _conftest_reasserted_names'
    docstring."""
    proofs = _held()["proofs"] if src is None else None
    if proofs is not None and "tests/conftest.py" in proofs:
        return proofs["tests/conftest.py"]
    sites, refused = _reassert_sites(src, where)
    writes, removals, refused = set(), set(), list(refused)
    if sites:
        verdicts, _rc, _out = _reassert_proof([("conftest", src, dict(helpers or {}), sites)],
                                              real=(src is None) if real is None else real)
        for name, why in sorted(verdicts["conftest"].items()):
            if why:
                refused.append("%s: %s" % (name, why))
                continue
            ops = {op for _f, _l, op in sites[name]}
            if "write" in ops:
                writes.add(name)
            if "pop" in ops:
                removals.add(name)
    got = _Reasserted(frozenset(writes), frozenset(removals), tuple(refused))
    if proofs is not None:
        proofs["tests/conftest.py"] = got
    return got


def _conftest_fixtures(tree):
    """Every def at the top of tests/conftest.py's body decorated `<x>.fixture` or `<x>.fixture(...)`, autouse or not,
    whatever its scope and whether or not pytest registers it: the population the two wide reads below walk."""
    def fixture_decorator(d):
        f = d.func if isinstance(d, ast.Call) else d
        return isinstance(f, ast.Attribute) and f.attr == "fixture"
    return [fn for fn in tree.body if isinstance(fn, ast.FunctionDef) and any(fixture_decorator(d) for d in fn.decorator_list)]


def _conftest_fixture_env_writes(src=None):
    """Every environment name a fixture of tests/conftest.py (_conftest_fixtures: autouse or not) WRITES anywhere in its
    body, in any shape _env_write_records reads, whatever the fixture's scope and wherever the statement stands (before or
    after the yield, conditional, in any loop, a setdefault included): the wide read of the writes alone, for a pin that
    asserts a name is NOT written, the ROMP_POSTAL_PORT pin (the verifier's finding on round 2 of fork PR #894: that pin's
    "not among the writes" half read the narrow writes, _conftest_reasserted_names', which a conditional, late, setdefault
    or session-scoped write of the port passes unread). A fixture that is not autouse is read beside the autouse ones (the
    verifier's finding at the next commit, which found false the reason this docstring gave for leaving it unread): it
    runs for every test that requests it, by name, through a fixture that requests it (an autouse one among them) or by a
    usefixtures mark, and a write it makes to the process environment holds for every later test in the process and every
    child those tests spawn until something puts it back, not for the requesting tests alone. What it does not read, each
    passing that pin unread: a write through a call the fixture makes (a helper def: tests/conftest.py's restore_env writes
    computed keys, which the scan cannot read); a fixture decorated through a bare name or an alias (`from pytest import
    fixture`, `fx = pytest.fixture`) or by yield_fixture, registered by a call rather than a decorator, defined inside a
    block, or an async def; and a write through the module's namespace or a string exec or eval runs. The executed check
    beside the pin (test_a_port_one_test_sets_is_gone_when_the_next_test_starts, a child pytest under the real conftest)
    reads the port at run time whatever route set it, on the machine and environment the run has."""
    tree = ast.parse(open(os.path.join(HERE, "conftest.py"), encoding="utf-8", errors="replace").read() if src is None else src)
    names = _EnvNames(tree)
    out = set()
    for fn in _conftest_fixtures(tree):
        out |= _env_writes(fn, names, "conftest.py")
    return out


def _conftest_fixture_env_names(src=None):
    """Every environment name a fixture of tests/conftest.py (_conftest_fixtures: autouse or not) writes or pops anywhere
    in its body, in any shape _env_write_records reads, whatever the fixture's scope and wherever the statement stands
    (before or after the yield, conditional, in a literal loop): the WIDE read, for a check that asks whether conftest
    touches a name per test at all (the module env fixture's watched list, where conftest's own write would read as the
    module's). The narrow read,
    _conftest_reasserted_names, would be the unsafe side there: a conditional or late write of a watched name would pass
    it unread. The writes are _conftest_fixture_env_writes' (what it does not read is in its docstring)."""
    tree = ast.parse(open(os.path.join(HERE, "conftest.py"), encoding="utf-8", errors="replace").read() if src is None else src)
    names = _EnvNames(tree)
    out = _conftest_fixture_env_writes(src)
    for fn in _conftest_fixtures(tree):
        out |= _env_removals(fn, names)
    return out


def _conftest_reasserted_union(src=None):
    """Every name tests/conftest.py re-asserts before every test, set or popped, as the execution proof grants it
    (_conftest_reasserts_proved): the condition a `reasserted` licence rests on, which either form meets."""
    got = _conftest_reasserts_proved(src)
    return got.writes | got.removals


def _conftest_import_pops(src=None):
    """The environment names tests/conftest.py pops at its import: a module-level statement os.environ.pop(<name>, ...)
    whose name is a string literal, the form the floor lines take. What it does not read: a pop inside a def the file
    calls at import (_scrub_key_source_env's credential names) and a pop through a name bound to os.environ; a watched name
    popped only that way reads here as not popped, which reds the pin that uses this rather than passing it."""
    tree = ast.parse(open(os.path.join(HERE, "conftest.py"), encoding="utf-8", errors="replace").read() if src is None else src)
    out = set()
    for st in tree.body:
        c = st.value if isinstance(st, ast.Expr) else None
        if (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "pop"
                and ast.unparse(c.func.value) == "os.environ" and c.args
                and isinstance(c.args[0], ast.Constant) and isinstance(c.args[0].value, str)):
            out.add(c.args[0].value)
    return out


_SCOPE_WORD = re.compile(r"\bscope\s*=")
_FIXTURE_FUNCTIONS = ("fixture", "yield_fixture")
#   pytest's two public functions that register a fixture: fixture, and yield_fixture, deprecated since pytest 3.0 and
#   still shipped by the installed pytest (9.1.1), which passes the same keywords on to fixture with a warning


def _fixture_spellings(tree, passes=None):
    """The names a call to one of pytest's fixture functions (_FIXTURE_FUNCTIONS) is spelled by in `tree`, besides any
    attribute named for one: the functions' own names, an as-name a from-import gives fixture or yield_fixture (`from
    pytest import fixture as fx`), and every name target of a plain assignment of one of these (`fx = pytest.fixture`,
    `fx2 = fx`, and every name of a chain, `fx = fx2 = fx3 = pytest.fixture`), followed to a fixed point: ast.walk is
    breadth-first, so a module-level `fx2 = fx` is reached before an `fx = pytest.fixture` nested in a try and is read
    on the next pass, and the loop ends on the first pass that adds no name. `passes`, when a list, receives each pass's
    outcome (True when the pass added a name), for the pin that holds the loop to that end. It reads `tree` alone, so a
    name another module binds to one of the functions is not among them when this one takes it by a from-import, under
    that name or an as-name, or by a star import (the verifier's finding on round 2 of fork PR #894;
    _fixtures_scoped_above_module's docstring lists it as unread)."""
    names = set(_FIXTURE_FUNCTIONS)
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            names |= {a.asname for a in n.names if a.name in _FIXTURE_FUNCTIONS and a.asname}
    grew = True
    while grew:
        grew = False
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and _spelled_fixture(n.value, names):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id not in names:
                        names.add(t.id)
                        grew = True
        if passes is not None:
            passes.append(grew)
    return names


def _spelled_fixture(f, names):
    return (isinstance(f, ast.Attribute) and f.attr in _FIXTURE_FUNCTIONS) or (isinstance(f, ast.Name) and f.id in names)


def _fixtures_scoped_above_module(root=None):
    """Every fixture defined under tests/ (or `root`) whose scope is above module, as (path relative to the root, line,
    function name, the scope as written): "session", "package", or a scope that is not a string literal (either at run
    time). conftest's two environment checks read a watched name such a fixture writes only when its setup runs after
    the check's snapshot, which turns on how the fixture is requested and from where (conftest's comment above
    _module_env_restored says which request each check reads), and a write set up before both reaches every later module
    unread, so the tree holds none. It reads every call to one of pytest's fixture functions (_FIXTURE_FUNCTIONS:
    fixture, and yield_fixture) that passes scope= (the installed pytest takes the scope by keyword only in both; a
    positional first argument is the fixture function), wherever the call is: a decorator
    (`@pytest.fixture(scope="session")`), a call applied to the function (`pytest.fixture(scope="session")(body)`) or
    passed it (`pytest.fixture(body, scope="session")`), and a factory held in a name (`sess =
    pytest.fixture(scope="session")`), under any name _fixture_spellings finds for the function (an attribute named for
    one, the function's own name, an as-name a from-import gives fixture or yield_fixture, a name target of a plain
    assignment, each name of a chain `fx = fx2 = fx3 = ...` included, followed to a fixed point). And it reads every
    call to an attribute named parametrize (`@pytest.mark.parametrize(...)`, `metafunc.parametrize(...)`) that passes a
    scope, by keyword or as its fifth argument, other than None (the default, the scope of the fixtures it names): a
    parametrization's scope overrides the scope of a fixture it parametrizes indirectly, so a function-scoped fixture
    given scope="session" there is torn down at the end of the session; it is listed whether or not the parametrization
    is indirect, the safe side. Each file under the root whose text has parametrize, or both fixture and scope=, is
    read. The function name is the decorated def's, or the one a fixture call is applied to or passed, else "?". What it
    does not read, each passing here unread (none is in the tree): a scope passed through *args or **kwargs; a fixture
    function or a parametrize reached by any other route (functools.partial(pytest.fixture, scope=...), whose scope sits
    on the partial's call; getattr(pytest, "fixture"); a name bound by any statement other than a from-import that gives
    fixture or yield_fixture an as-name or a plain assignment with the name as a target: a tuple, list or starred target
    (`fx, _ = pytest.fixture, None`), an annotated or augmented assignment, a walrus, a for, with or match-case target,
    and a from-import of a name other than fixture and yield_fixture, under that name or an as-name, or a star import,
    either of which may bind a name another module bound to the function (`from helpers import fx`, where helpers binds
    `fx = pytest.fixture`): the scan reads each file alone and knows nothing another module binds, while pytest
    registers the fixture with its scope all the same (the verifier's finding on round 2 of fork PR #894); the other
    binding statements, an import of a module, a def, a class, a type alias and an except name, bind something other
    than the function; a plain assignment whose value is neither the function nor one of these names (`fx =
    pytest.fixture if X else None`); an attribute of another name, such as a class attribute holding the function; a
    name bound to parametrize; one returned by a call, held in a container, or passed as an argument or a parameter's
    default); a fixture registered through pytest's private fixture manager (FixtureManager._register_fixture, which a
    plugin can call with a scope); and a fixture a plugin outside the root defines. A wrapper def that calls the fixture
    function with scope= is read at that call, the safe side: a parameter it passes as the function is shown as the
    function name, and one it passes as the scope as the scope."""
    root = HERE if root is None else root
    out = []
    for path in sorted(glob.glob(os.path.join(root, "**", "*.py"), recursive=True)):
        text = open(path, encoding="utf-8", errors="replace").read()
        if "parametrize" not in text and ("fixture" not in text or not _SCOPE_WORD.search(text)):
            continue
        tree = ast.parse(text, filename=path)
        names = _fixture_spellings(tree)
        parent, decorates = {}, {}
        for n in ast.walk(tree):
            for c in ast.iter_child_nodes(n):
                parent[id(c)] = n
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for d in n.decorator_list:
                    decorates[id(d)] = n
        found = []
        for c in ast.walk(tree):
            if not isinstance(c, ast.Call):
                continue
            fixture_call = _spelled_fixture(c.func, names)
            if not fixture_call and not (isinstance(c.func, ast.Attribute) and c.func.attr == "parametrize"):
                continue
            scopes = [kw.value for kw in c.keywords if kw.arg == "scope"]
            if not fixture_call and len(c.args) >= 5:
                scopes.append(c.args[4])
            for value in scopes:
                literal = value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None
                if literal in ("function", "class", "module"):
                    continue
                if not fixture_call and isinstance(value, ast.Constant) and value.value is None:
                    continue
                up = parent.get(id(c))
                if id(c) in decorates:
                    line, name = decorates[id(c)].lineno, decorates[id(c)].name
                elif fixture_call and isinstance(up, ast.Call) and up.func is c and up.args:
                    line, name = c.lineno, ast.unparse(up.args[0])
                elif fixture_call and c.args:
                    line, name = c.lineno, ast.unparse(c.args[0])
                else:
                    line, name = c.lineno, "?"
                found.append((os.path.relpath(path, root), line, name, ast.unparse(value)))
        out.extend(sorted(found, key=lambda r: (r[1], r[2])))
    return out


def _licence_faults(records, reasserted_names=None, refused=()):
    """Every way the module-level writes in `records` ({name: [_Record]}) fall outside the licensed set; empty when the set
    of names the TEST MODULES write equals the licensed names and every write meets its licence's condition. A list
    rather than assertions so the check runs over synthetic records and is known to be able to fail. The floor modules'
    writes are licensed wholesale and never faulted; a licensed name with no writer left is a fault too (a dead licence
    is removed, not kept). With no `reasserted_names` the execution proof over tests/conftest.py supplies them and its
    refusals (_conftest_reasserts_proved); a test hands both in."""
    if reasserted_names is None:
        got = _conftest_reasserts_proved()
        reasserted_names, refused = got.writes | got.removals, got.refused
    faults = []
    written = set()
    for name in sorted(records):
        for rec in records[name]:
            if rec.module in FLOOR_MODULES:
                continue
            written.add(name)
            lic = LICENSED_MODULE_LEVEL_WRITES.get(name)
            at = "%s:%d (%s%s%s)" % (rec.module, rec.line, rec.shape, ", nested in a module-level block or a class body" if rec.nested else "",
                                     (", through %s" % rec.via) if rec.via else "")
            if lic is None:
                faults.append("%s is written at module level by %s and is not in the licensed set: set it in setUp and put "
                              "it back with a cleanup registered right after the write (tests/README.md), or license the "
                              "name here with its reason, a date and the item it waits on" % (name, at))
                continue
            why = lic.fault(rec, reasserted_names, refused)
            if why:
                faults.append("%s at %s: %s" % (name, at, why))
    for name in sorted(set(LICENSED_MODULE_LEVEL_WRITES) - written):
        faults.append("%s is licensed but no test module writes it at module level any more: remove the licence" % name)
    if refused and any("the conftest reader refused" in f for f in faults):
        faults.append("the conftest reader's refusals (_conftest_reasserts_proved): " + " | ".join(refused))
    return faults


LEAK_NAMES = ("ROMP_POSTAL_PEERS", "ROMP_POSTAL_PORT", "ROMP_POSTAL_CLIENT_ONLY", "ROMP_SESSIONS_FILE", "ROMP_POSTAL_HOST")
#   the names a module-level write of which is the leak this rule exists to catch: never licensed, and held by the census
#   pin's per-name check against every writer, a floor module included (_leak_writers)
FLOOR_LEAK_WRITES = {"ROMP_POSTAL_CLIENT_ONLY": "'1'"}
#   the one module-level write of a leak name a floor module may make, as ast.unparse spells its resolved value:
#   client-only "1", upstream's floor line (their PR 1848, which fork PR #875 folds), under which no in-process kernel of
#   the run starts a bus by an ensure or a revive. A floor module's write of any other leak name, or of client-only with
#   any other value, is the leak a test module's write is: a port in the floor names the run's own port to every child
#   of every test (the bind the fixed-port refusal then licenses), peers in the floor reaches every module on every
#   xdist worker, the sessions-file seam in the floor keeps a bus from autostopping.


def _leak_writers(records, name):
    """The modules in `records` ({name: [_Record]}) that write the leak name `name` at module level: every writer, the
    floor modules (FLOOR_MODULES) included, except a floor module's write of the one value FLOOR_LEAK_WRITES names for
    `name`. The census pin's per-name check reads this. What it does not read, and why: a floor module's client-only of
    "1", the runner's floor under which no kernel of the run starts a bus. Before round 2 of fork PR #894's review the
    check read every record, so upstream's floor line (os.environ["ROMP_POSTAL_CLIENT_ONLY"] = "1" in tests/conftest.py)
    red it; the round's first commit skipped every floor record, as the equality above the check skips them (the
    reviewer's ruling of round 1), which left a floor module's write of the other four names, and of client-only with any
    value, unread (the verifier's finding on round 2: the sessions-file seam planted in tests/__init__.py passed)."""
    floor_value = FLOOR_LEAK_WRITES.get(name)
    return [r.module for r in records.get(name, [])
            if not (r.module in FLOOR_MODULES and floor_value is not None and r.resolved == floor_value)]


def _attribute_assigns(node):
    """The attribute names the code under `node` assigns as `<something>.<attr> = ...` (km.BUS_PORT = port)."""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Assign):
            out.update(t.attr for t in _flat_targets(n.targets) if isinstance(t, ast.Attribute))
    return out


def _cleanup_restores(funcs, cls, classes, tree, names, where):
    """(environment keys, attribute names) the cleanups registered under `funcs` (`self.addCleanup(callee, ...)`) write,
    pop or assign: the callee resolved to a method of `cls` (`self.<name>`, its own or a base's through the module's
    classes) or to a function defined at module level, plus any key named as a string argument of the registration (a
    helper that takes the name, conftest's restore_env). A restore registered as a cleanup runs when a later setUp
    statement raises, which a tearDown does not (review round 1, 2026-09-18). The attributes are read since 2026-09-22:
    the kernel's BUS_PORT, read at import, is patched per test and must come back the same way."""
    module_funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    keys, attrs = set(), set()
    for f in funcs:
        for n in ast.walk(f):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "addCleanup"
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "self" and n.args):
                continue
            callee = n.args[0]
            keys.update(a.value for a in n.args[1:] if isinstance(a, ast.Constant) and isinstance(a.value, str))
            targets = []
            if isinstance(callee, ast.Attribute) and isinstance(callee.value, ast.Name) and callee.value.id == "self":
                targets = _method_chain(cls, callee.attr, classes)
            elif isinstance(callee, ast.Name) and callee.id in module_funcs:
                targets = [module_funcs[callee.id]]
            for t in targets:
                keys |= _env_writes(t, names, where) | _env_removals(t, names)
                attrs |= _attribute_assigns(t)
    return keys, attrs


def _placement_faults(tree, where="test_kernel_tunnels.py"):
    """Every way a module that loads the kernel in-process and attaches misplaces a leg of the trio; empty when the
    placement holds. Since 2026-09-22 NO leg is written at module level: the port and client-only were, before the load
    (the kernel reads the port at import), and a module-level write holds for every test in the process and for every
    child any test spawns, whether or not the writing module's tests run: the real bus of fork PR #813's CI started with
    exactly this module's port (the run's own, so the bus's belt licensed the bind) and its client-only (inert with
    peers on); peers never was, since the leak of 2026-09-18. Every class that attaches or detaches has a setUp (its
    own or through super()) that sets all three names AND assigns the kernel's BUS_PORT (the import-time read, patched
    to the test's port) and its _ensure_postal_bus (the revive road, stubbed with a recorder), and registers a cleanup
    that restores the three names and both attributes (the reviewer's ruling of round 1 on fork PR #894: before it the
    stub, the restore of the road and the recorder's check could each be deleted with no test failing). What the stub
    does and what the cleanup checks is not read here, since a read of the assignments cannot tell a stub that records
    from one that does not: the revive probe runs them (_REVIVE_PROBE). A list rather than
    assertions so the check itself can be run over a synthetic module with the leak planted and shown to go red; a
    write the scan cannot read raises UnreadableEnvWrite out of it."""
    faults = []
    loads = [i for i, s in enumerate(tree.body) if _loads_kernel(s)]
    if not loads:
        return ["the module does not load the kernel in-process at module level"]
    names = _EnvNames(tree)
    at_import = _module_level_env_writes(tree, where)
    for leg in TRIO:
        if leg in at_import:
            faults.append("%s is written at module level: a module-level write executes at collection and holds for every test "
                          "in the process and every child a test spawns (the port and client-only started a real bus from "
                          "another module's test, fork PR #813's CI, 2026-09-22; peers reached every module on every xdist "
                          "worker, 2026-09-18); set it in setUp beside km.BUS_PORT" % leg)
    classes = {c.name: c for c in tree.body if isinstance(c, ast.ClassDef)}
    attaching = [c for c in classes.values() if _attaches_or_detaches(c)]
    if len(attaching) < 2:
        faults.append("the scan sees fewer than two classes that attach or detach: %r" % [c.name for c in attaching])
    for cls in attaching:
        set_up = _method_chain(cls, "setUp", classes)
        if not set_up:
            faults.append("%s attaches or detaches and has no setUp" % cls.name)
            continue
        in_setup, attrs = set(), set()
        for f in set_up:
            in_setup |= _env_writes(f, names, where)
            attrs |= _attribute_assigns(f)
        for leg in TRIO:
            if leg not in in_setup:
                faults.append("%s.setUp (own or through super()) does not set %s for its tests (a refused bus notice revives the "
                              "bus with the process's environment otherwise)" % (cls.name, leg))
        if "BUS_PORT" not in attrs:
            faults.append("%s.setUp (own or through super()) does not patch the kernel's BUS_PORT, which it read at import, to the "
                          "test's port" % cls.name)
        if "_ensure_postal_bus" not in attrs:
            faults.append("%s.setUp (own or through super()) does not stub the kernel's _ensure_postal_bus, the revive road a "
                          "refused bus call the trio did not prevent would run the postal service's ensure through" % cls.name)
        restored, rattrs = _cleanup_restores(set_up, cls, classes, tree, names, where)
        for leg in TRIO:
            if leg not in restored:
                faults.append("%s.setUp (own or through super()) registers no cleanup that restores %s: a tearDown restore is "
                              "skipped when a later setUp statement raises, and the value outlives the class (review round 1, "
                              "2026-09-18)" % (cls.name, leg))
        if "BUS_PORT" not in rattrs:
            faults.append("%s.setUp (own or through super()) registers no cleanup that restores the kernel's BUS_PORT" % cls.name)
        if "_ensure_postal_bus" not in rattrs:
            faults.append("%s.setUp (own or through super()) registers no cleanup that restores the kernel's _ensure_postal_bus"
                          % cls.name)
    return faults


def _tunnels_source():
    return open(os.path.join(HERE, "test_kernel_tunnels.py"), encoding="utf-8", errors="replace").read()


_PLANT_ANCHOR = 'load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))\n'


def _plant(src, lines):
    """`src` with `lines` inserted at module level just before the first load, that is before the kernel load: the place
    the leaked writes used to be (peers until 2026-09-18, the port and client-only until 2026-09-22). Loud when the
    anchor is not there once."""
    if src.count(_PLANT_ANCHOR) != 1:
        raise AssertionError("the planting anchor %r is in the module %d times, not once" % (_PLANT_ANCHOR, src.count(_PLANT_ANCHOR)))
    return src.replace(_PLANT_ANCHOR, lines + _PLANT_ANCHOR)


_CLIENT_ONLY_FLOOR = 'os.environ["ROMP_POSTAL_CLIENT_ONLY"] = "1"\n'    # upstream's floor line (their PR 1848, folded by fork PR #875)
_HERMETIC_MARKER = 'os.environ["ROMP_POSTAL_HERMETIC"] = "1"\n'


_DIAL_SPY = textwrap.dedent("""\
    # sitecustomize for the child pytest runs of tests/test_hermetic_kernel_postal.py's spied pins (the peer-notify guard
    # test; the modules whose in-process kernels dialled the fixed bus port): every Python process of the run records each
    # socket connect by port (and whether its PYTHONPATH still names this spy, so a child forked then with its
    # environment loads it too), each process it starts through subprocess.Popen whose command names
    # romp-postal-service, its own start when its argv names romp-postal-service, and its own argv at exit, each record
    # with the test phase (PYTEST_CURRENT_TEST) and the thread current at it; and it refuses a connect to the machine's
    # fixed bus port before it reaches the network
    import atexit, errno, json, os, socket, subprocess, sys, threading
    _OUT, _FIXED = os.environ.get("ROMP_TEST_DIAL_SPY"), os.environ.get("ROMP_TEST_DIAL_SPY_FIXED")
    _HERE = os.path.dirname(os.path.abspath(__file__))
    if _OUT and _FIXED:
        def _record(kind, **fields):
            fields.update(kind=kind, pid=os.getpid(), argv=[str(a) for a in getattr(sys, "argv", [])],
                          spy_on_path=_HERE in os.environ.get("PYTHONPATH", "").split(os.pathsep),
                          test=os.environ.get("PYTEST_CURRENT_TEST", ""), thread=threading.current_thread().name)
            with open(_OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps(fields) + "\\n")

        def _port(address):
            try:
                return int(address[1]) if isinstance(address, tuple) else None    # an AF_UNIX path is not a port
            except Exception:
                return None

        def _command(args):
            return " ".join(str(a) for a in args) if isinstance(args, (list, tuple)) else str(args)
        _popen_init = subprocess.Popen.__init__

        def popen_init(self, args, *a, **kw):
            if "romp-postal-service" in _command(args):
                _record("spawn", command=_command(args)[:300])
            return _popen_init(self, args, *a, **kw)
        subprocess.Popen.__init__ = popen_init
        if any("romp-postal-service" in str(a) for a in getattr(sys, "argv", [])):
            _record("start")
        _connect, _connect_ex = socket.socket.connect, socket.socket.connect_ex

        def connect(self, address):
            _record("dial", port=_port(address))
            if _port(address) == int(_FIXED):
                raise ConnectionRefusedError("the machine's fixed bus port is never dialled from this run")
            return _connect(self, address)

        def connect_ex(self, address):
            _record("dial", port=_port(address))
            if _port(address) == int(_FIXED):
                return errno.ECONNREFUSED
            return _connect_ex(self, address)
        socket.socket.connect, socket.socket.connect_ex = connect, connect_ex
        atexit.register(_record, "exit")
""")


def _fixed_bus_port():
    """The machine's fixed bus port, the postal service's default, read from bin/romp-postal-service (named there once)."""
    m = re.findall(r'^PORT = int\(os\.environ\.get\("ROMP_POSTAL_PORT", "(\d+)"\)\)',
                   open(os.path.join(os.path.dirname(HERE), "bin", "romp-postal-service"), encoding="utf-8").read(), re.M)
    if len(m) != 1:
        raise AssertionError("bin/romp-postal-service names its default port %d times, not once" % len(m))
    return int(m[0])


BUS_DIALLING_MODULES = ("tests/test_kernel_known_hosts.py", "tests/test_peer_reconnect.py", "tests/test_kernel_remote_update.py",
                        "tests/test_postal_relay_honesty.py")
#   every module a connect to the fixed bus port, or a spawn of romp-postal-service with no port of the run's own, came
#   from in one full serial run of tests/ at the head before the dead-port fixture, recorded by a spy with each record's
#   PYTEST_CURRENT_TEST (the reviewer's ruling of round 1 on fork PR #894 derives the population by execution): the
#   in-process kernels' peer notifies and GET /peers (the first three), and the in-process postal client's heartbeat in
#   the fourth. The pin below runs them together in both orders. The same run recorded two classes of spawn outside the
#   population, each for its reason: tests/test_postal_fixed_port_belt.py starts the postal service on purpose, as the
#   subject of its tests, to show the belt refuses the fixed port (the spy does not see inside those children, whose bare
#   environment carries no PYTHONPATH; by reading, each imports the module and calls _fixed_port_refusal, or runs serve
#   under a test, which refuses before it binds, and none dials a port); and the served tests' lab kernels, started as
#   processes by kernel_env with the trio, run their boot ensure with a port of their own and client-only, so it starts
#   nothing


_TRIES = tuple(getattr(ast, name) for name in ("Try", "TryStar") if hasattr(ast, name))
_ENDS_BY_CALL = ("skipTest", "skip", "xfail", "exit", "_exit")


def _runs_with(node):
    """Every node that executes when `node` does, in the same frame: a def contributes its decorators, default values and
    annotations and a lambda its default values, never their bodies, which run when called; a class its decorators, bases
    and keywords and its body, which runs at the class statement (the defs in it again by their headers)."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        a = node.args
        parts = _def_header(node) + [x.annotation for x in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg]
                                     if x is not None and x.annotation is not None] + ([node.returns] if node.returns else [])
    elif isinstance(node, ast.Lambda):
        parts = [d for d in list(node.args.defaults) + list(node.args.kw_defaults) if d is not None]
    elif isinstance(node, ast.ClassDef):
        parts = _class_header(node) + list(node.body)
    else:
        yield node
        parts = ast.iter_child_nodes(node)
    for p in parts:
        yield from _runs_with(p)


def _ends_the_run(stmt):
    """`stmt` can end the test's run before the statements after it while the run still passes, is skipped or exits with
    status 0: it is, or holds in its own frame (_runs_with), a return or a raise (a raise of SkipTest skips; a raise an
    except clause catches jumps past the statements between), or a call named skipTest, skip, xfail, exit or _exit
    (unittest's and pytest's skips and expected failure, sys.exit, pytest.exit, and os._exit, which ends the process with
    the status it is given). A break or continue is not among them: _executed never reads inside a loop, so one ends
    only a loop the list does not read into. NOT READ: a skip, an expected failure or an exit raised from inside a
    function the test calls (the executed pin's child run requires the test to PASS and reds on it)."""
    return any(isinstance(n, (ast.Return, ast.Raise))
               or (isinstance(n, ast.Call) and (_dotted(n.func) or [""])[-1] in _ENDS_BY_CALL) for n in _runs_with(stmt))


def _run_prefix(body):
    """The statements of `body` in order, up to and including the first that can end the run (_ends_the_run): the ones
    after it are in the tree and never run on a run that returns there (the verifier's mutant on round 2's third commit of
    fork PR #894, a `return` between the try and the test's two final assertions, under which the guard test and all
    three pins passed)."""
    out = []
    for stmt in body:
        out.append(stmt)
        if _ends_the_run(stmt):
            break
    return out


def _executed(body):
    """The statements of a function body that run on every run of it that passes: each statement of its run prefix
    (_run_prefix) and, for a try among them, the statements of its finally and, when it has no except clause, of its
    body, recursively. Never an if or loop body, a with body, an except or else clause, the body of a try that has an
    except clause (a statement after one that raises there is skipped and the run goes on), or a nested def's body: a
    statement under `if False:`, in a def the test never calls, after a caught raise or after a `return` is in the tree
    and never runs (the verifier's two mutants of round 2 on fork PR #894 passed a pin that walked the whole function, and
    two more, a `return` after the try and one in its finally before the put-backs, a pin that read every statement of a
    list). A try* statement always has handlers, so its body is never read."""
    out = []
    for stmt in _run_prefix(body):
        out.append(stmt)
        if isinstance(stmt, _TRIES):
            out += (_executed(stmt.body) if not stmt.handlers else []) + _executed(stmt.finalbody)
    return out


def _own_calls(stmt):
    """The calls a SIMPLE statement makes itself, a lambda's body excluded; none for a compound statement or a def, whose
    bodies hold statements of their own."""
    if isinstance(stmt, _COMPOUND + (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return []

    def calls(n):
        if isinstance(n, ast.Lambda):
            return []
        return ([n] if isinstance(n, ast.Call) else []) + [c for child in ast.iter_child_nodes(n) for c in calls(child)]
    return calls(stmt)


_REPEATS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _repeats(node):
    """The comprehensions and generator expressions inside `node` (_REPEATS: a list, set or dict comprehension, a
    generator expression), read by ast.walk. Each runs its element once per item, so a call written once in one runs as
    many times as its iterable has items (the re-verifier's notify run twice by a list comprehension, on round 2's
    twenty-fifth commit of fork PR #894, passed a rule that counted the call nodes of the notify statement). ast.walk
    reads a lambda's body too, so a comprehension there counts, though it runs only when the lambda is called. What
    that part alone refuses does no harm. The notify statement makes one call beside its assertion, a lambda's calls
    counted (the window rule of _guard_shape), so a comprehension in a lambda's body there either calls nothing or
    holds that one call; and a call inside a lambda's body is no call of the statement's own (_own_calls), so the tries
    rule reds unless another statement makes the notify call, and then the window rule, which exempts the first notify
    statement alone, reds one of the two (the re-verifier's lambda comprehension that runs the notify twice, in the
    notify statement's place or after it, reds with the part skipped). The part is kept as the safe side, and the plant
    test holds two plants it alone refuses, harmless ones that pass with it skipped: a lambda holding a call-free
    list comprehension handed to the notify statement as its msg, and one holding a call-free set comprehension as the
    notify's own argument (the re-verifier's on the twenty-seventh commit, where this docstring said no plant could
    tell the two readings apart)."""
    return [n for n in ast.walk(node) if isinstance(n, _REPEATS)]


def _call_stmt(stmt, dotted):
    """`stmt` is an expression statement whose value is a call of the dotted chain `dotted` (["os", "environ", "update"])."""
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and _dotted(stmt.value.func) == dotted


def _assign_to(stmt, target):
    """`stmt` is an assignment with one target, the dotted chain `target` (["km", "subprocess", "run"])."""
    return isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and _dotted(stmt.targets[0]) == target


def _names_bound(stmts, value):
    """(index, name) for each `name = <value>` among `stmts`, `value` a dotted chain (["km", "_revive_postal_bus"]) or, as
    ("call", chain), a call of one."""
    def matches(v):
        if isinstance(value, tuple):
            return isinstance(v, ast.Call) and _dotted(v.func) == value[1]
        return _dotted(v) == value
    return [(i, s.targets[0].id) for i, s in enumerate(stmts) if isinstance(s, ast.Assign) and len(s.targets) == 1
            and isinstance(s.targets[0], ast.Name) and matches(s.value)]


def _environ_writes(node):
    """Every write to os.environ inside `node`, nested defs included: a call of pop, popitem, update, setdefault, clear,
    __setitem__ or __delitem__ on it, or a subscript of it stored or deleted. What the guard pin requires of the restore;
    its safe side reads every mention of the environment instead (_environ_mentions)."""
    return [n for n in ast.walk(node)
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and _dotted(n.func.value) == ["os", "environ"]
                and n.func.attr in ("pop", "popitem", "update", "setdefault", "clear", "__setitem__", "__delitem__"))
            or (isinstance(n, ast.Subscript) and _dotted(n.value) == ["os", "environ"] and isinstance(n.ctx, (ast.Store, ast.Del)))]


_ENV_NAMES = ("environ", "environb", "putenv", "unsetenv")


def _environ_mentions(node):
    """Every node inside `node`, nested defs included, that names the process environment or a function that changes it:
    an attribute environ, environb, putenv or unsetenv on any object (os under any name, or reached any way), a bare
    name so spelled (after `from os import environ`), whatever its context (loaded, stored or deleted), and an import of
    a name so spelled, under its own name or another (`from os import environ as _e`: before round 2's twenty-fourth
    commit on fork PR #894 that import, with a pop through `_e` in the guard test's window, passed the guard pin, since
    an import's name is neither an attribute nor a bare name). A write through a name bound to the mapping (`env =
    os.environ`) is read at the binding, which names it. Not read: an import's as name so spelled (`from json import
    loads as environ`), which binds a name to some other object; each use of that name is a bare name, and read."""
    return [n for n in ast.walk(node)
            if (isinstance(n, ast.Attribute) and n.attr in _ENV_NAMES) or (isinstance(n, ast.Name) and n.id in _ENV_NAMES)
            or (isinstance(n, ast.alias) and n.name in _ENV_NAMES)]


def _attribute_binds(node):
    """Every node inside `node`, nested defs included, that binds or deletes an attribute, whatever its name and on ANY
    object, so a module reached through another name (`subprocess.run = ...` beside `km.subprocess.run`), an assertion
    method (`self.assertEqual = ...`) and an Event's own method are read too: an attribute target in every binding form,
    one target of an assignment or one of several, unpacked from a tuple or a list or starred, an augmented or annotated
    one, a for, with or comprehension target, or a del. Every one of those carries a Store or Del context on the
    attribute node, which is what this reads."""
    return [n for n in ast.walk(node) if isinstance(n, ast.Attribute) and isinstance(n.ctx, (ast.Store, ast.Del))]


def _name_binds(node, names):
    """Every node inside `node`, nested defs included, that binds or deletes one of `names`: a name stored or deleted (an
    assignment, augmented or annotated, a for, with or comprehension target, a walrus, a del), a parameter of `node` or
    of a def or lambda inside it (which binds the name in that scope, so a nested def's `real_run=None` parameter hides
    the test's own real_run there: round 2's fifth commit on fork PR #894), an import's name or `as` name, a def or class
    so named, an except clause's `as` name, a match capture or rest, and a global or nonlocal declaration of it."""
    names = set(names)
    return [n for n in ast.walk(node)
            if (isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)) and n.id in names)
            or (isinstance(n, ast.arg) and n.arg in names)
            or (isinstance(n, ast.alias) and (n.asname or n.name.split(".")[0]) in names)
            or (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.ExceptHandler)) and n.name in names)
            or (isinstance(n, (ast.Global, ast.Nonlocal)) and names & set(n.names))
            or (type(n).__name__ in ("MatchAs", "MatchStar") and getattr(n, "name", None) in names)
            or (type(n).__name__ == "MatchMapping" and getattr(n, "rest", None) in names)]


def _name_loads(node, name):
    """Every read of the bare name `name` inside `node`, nested defs included: a load, which is how a call, an attribute
    or a subscript on it (`name.set()`, `del name[:]`), an argument and an alias (`other = name`) all begin."""
    return [n for n in ast.walk(node) if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load)]


def _calls_of(node, name):
    """Every call of the bare name `name` inside `node`, nested defs included."""
    return [c for c in ast.walk(node) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == name]


def _bound_value(stmt, target):
    """The value an assignment `stmt` gives the name node `target`: the value itself for a lone target, the matching element
    when a tuple or list of names is assigned a tuple or list of the same length; None for any other shape."""
    if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1):
        return None
    t, v = stmt.targets[0], stmt.value
    if t is target:
        return v
    if (isinstance(t, (ast.Tuple, ast.List)) and isinstance(v, (ast.Tuple, ast.List)) and len(t.elts) == len(v.elts)
            and not any(isinstance(e, ast.Starred) for e in t.elts + v.elts)):
        return next((ve for te, ve in zip(t.elts, v.elts) if te is target), None)
    return None


# Reflection, read by identifier: a builtin or a function that reaches an attribute, a module, a name, a frame or a
# namespace by a string or at run time, and the attributes that expose a namespace, a function's bindings or a frame.
_REFLECTIVE_NAMES = ("setattr", "delattr", "getattr", "vars", "globals", "locals", "exec", "eval", "compile", "__import__",
                     "patch", "builtins", "__builtins__", "import_module", "attrgetter", "methodcaller", "_getframe",
                     "currentframe", "get_referrers", "get_referents", "get_objects")
_REFLECTIVE_ATTRS = ("__setattr__", "__delattr__", "__getattribute__", "__dict__", "__globals__", "__closure__", "__code__",
                     "__defaults__", "__kwdefaults__", "cell_contents", "f_locals", "f_globals", "f_builtins", "modules")


def _reflective(n):
    """`n` names reflection, so what the statement holding it binds is decided at run time. Read by identifier in every
    reference form, not only a call by the bare name (the verifier's `_s = setattr; _s(...)`, `functools.partial(setattr,
    ...)` and `_g = getattr` on round 2's fourth commit of fork PR #894 passed the call-only reading): a bare name in any
    context (loaded: called, aliased or passed as an argument; stored; deleted) that is one of _REFLECTIVE_NAMES
    (setattr, delattr, getattr, vars, globals, locals, exec, eval, compile, __import__, mock's patch, the builtins module
    and __builtins__, importlib's import_module, operator's attrgetter and methodcaller, sys._getframe,
    inspect.currentframe, gc's get_referrers, get_referents and get_objects); an attribute so named (builtins.setattr,
    operator.methodcaller, mock.patch and patch.object and patch.dict, pytest's monkeypatch.setattr) or one of
    _REFLECTIVE_ATTRS (__setattr__, __delattr__, __getattribute__, __dict__, a function's __globals__, __closure__,
    __code__, __defaults__ and __kwdefaults__, a cell's cell_contents, a frame's f_locals, f_globals and f_builtins,
    sys.modules); and an import whose name's last dotted part (the whole name when it has no dot) or whose as name is
    any of those (`from builtins import setattr as _s`, `import six.moves.builtins`, `from json import loads as
    setattr`). NOT READ: a namespace or a callable reached through a module neither list names (a pickle or marshal
    payload, ctypes): _guard_shape names what sees what that could put back."""
    reflective = _REFLECTIVE_NAMES + _REFLECTIVE_ATTRS
    return ((isinstance(n, ast.Name) and n.id in _REFLECTIVE_NAMES)
            or (isinstance(n, ast.Attribute) and n.attr in reflective)
            or (isinstance(n, ast.alias) and bool({n.name.split(".")[-1], n.asname} & set(reflective))))


def _plant_at(src, node, text, where, col=None):
    """`src` with the lines of `text`, each indented as the statement `node` is (or by `col` columns), put before its first
    line (its decorators included), after its last line, or in its place: `where` is "before", "after" or "replace".
    `node` is a node of a parse of `src` itself, so its line numbers count in `src`."""
    lines = src.splitlines(keepends=True)
    new = ["%s%s\n" % (" " * (node.col_offset if col is None else col), line) for line in text.split("\n")]
    first = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    start, end = {"before": (first - 1, first - 1), "after": (node.end_lineno, node.end_lineno), "replace": (first - 1, node.end_lineno)}[where]
    return "".join(lines[:start] + new + lines[end:])


def _conftest_with_the_client_only_floor():
    """tests/conftest.py's text with upstream's client-only floor line right after the hermetic marker, where their PR
    1848 puts it (fork PR #875 folds it). Loud when the marker is not there once."""
    src = open(os.path.join(HERE, "conftest.py"), encoding="utf-8", errors="replace").read()
    if src.count(_HERMETIC_MARKER) != 1:
        raise AssertionError("the hermetic marker %r is in tests/conftest.py %d times, not once" % (_HERMETIC_MARKER, src.count(_HERMETIC_MARKER)))
    return src.replace(_HERMETIC_MARKER, _HERMETIC_MARKER + _CLIENT_ONLY_FLOOR)


def _teardown_only_restore(src):
    """`src` (the tunnels module) with _PostalTrio's restore moved back into a tearDown and no cleanup registered: the
    shape the round-1 review found leaking on a subclass setUp that raises. The tearDown puts back the three names and,
    from _restore_bus's body, which it takes over, both kernel attributes, BUS_PORT and the _ensure_postal_bus road
    (checked on the rewritten class's tree, so each fault the copy draws is for the missing cleanup and none for a
    restore the copy dropped)."""
    cleanups = ('        self.addCleanup(self._restore_bus, bus_port, ensure)\n'
                '        self.addCleanup(restore_env, "ROMP_POSTAL_PEERS", prior["ROMP_POSTAL_PEERS"])\n'
                '        self.addCleanup(restore_env, "ROMP_POSTAL_CLIENT_ONLY", prior["ROMP_POSTAL_CLIENT_ONLY"])\n'
                '        self.addCleanup(restore_env, "ROMP_POSTAL_PORT", prior["ROMP_POSTAL_PORT"])\n')
    out = src.replace(cleanups, "        self._saved_bus = (prior, bus_port, ensure)\n", 1)
    out = out.replace("    def _restore_bus(self, bus_port, ensure):\n",
                      "    def tearDown(self):\n        prior, bus_port, ensure = self._saved_bus\n"
                      "        for k in prior:\n            restore_env(k, prior[k])\n", 1)
    trio = out.split("class _PostalTrio", 1)[1].split("\nclass ", 1)[0]     # the rewritten class's body alone
    if "addCleanup" in trio or "def tearDown(self):" not in trio or out.count("def _restore_bus") != 0 or cleanups not in src:
        raise AssertionError("the tunnels module no longer has the _PostalTrio shape this synthetic copy rewrites")
    cls = next(n for n in ast.parse(out).body if isinstance(n, ast.ClassDef) and n.name == "_PostalTrio")
    down = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "tearDown")
    if not {"BUS_PORT", "_ensure_postal_bus"} <= _attribute_assigns(down):
        raise AssertionError("the rewritten tearDown does not put back both kernel attributes: %r" % sorted(_attribute_assigns(down)))
    return out


_PROBE = textwrap.dedent("""
    import json, os, shutil, sys, unittest
    TRIO = ("ROMP_POSTAL_PORT", "ROMP_POSTAL_CLIENT_ONLY", "ROMP_POSTAL_PEERS")
    for k in TRIO:
        os.environ.pop(k, None)
    here, planted, planted_conftest = sys.argv[1], sys.argv[2], sys.argv[3]
    sys.path.insert(0, here)
    sys.path.insert(0, os.path.dirname(here))    # the checkout: the module imports tests.conftest for restore_env
    env = lambda: {k: os.environ.get(k) for k in TRIO}
    # the floor modules the module imports first (the package's twin, then conftest), imported here so what they set is
    # read before the module's own import; a synthetic conftest is compiled under the real file's name and registered
    # as tests.conftest, so the module's own import of it finds that one
    import tests
    if planted_conftest:
        c = type(sys)("tests.conftest")
        c.__file__, c.__package__ = os.path.join(here, "conftest.py"), "tests"
        sys.modules["tests.conftest"] = tests.conftest = c
        exec(compile(open(planted_conftest, encoding="utf-8").read(), c.__file__, "exec"), c.__dict__)
    else:
        import tests.conftest
    before = env()
    if planted:
        # a synthetic copy of the module, compiled under the real file's name so its HERE and BIN resolve
        real = os.path.join(here, "test_kernel_tunnels.py")
        t = type(sys)("test_kernel_tunnels_planted")
        t.__file__ = real
        exec(compile(open(planted, encoding="utf-8").read(), real, "exec"), t.__dict__)
    else:
        import test_kernel_tunnels as t
    out = {"before_import": before, "after_import": env(), "bus_port_at_import": t.km.BUS_PORT}
    os.environ["ROMP_POSTAL_PEERS"] = "1"
    case = t.TunnelConcierge("test_attach_requires_host")
    case.setUp()
    out["in_setup"] = env()
    out["bus_port_in_setup_matches"] = str(t.km.BUS_PORT) == os.environ.get("ROMP_POSTAL_PORT")
    case.tearDown()
    out["after_teardown"] = env()
    case.doCleanups()
    out["after_cleanups"] = env()
    out["bus_port_after_cleanups"] = t.km.BUS_PORT

    class Raises(t._PostalTrio):
        def setUp(self):
            super().setUp()
            raise OSError("planted: the rest of a subclass's setUp failing after the trio's writes")

        def test_never_reached(self):
            pass

    result = unittest.TestResult()
    Raises("test_never_reached").run(result)
    out["setup_raise_errors"] = len(result.errors)
    out["after_setup_raise"] = env()
    out["bus_port_after_setup_raise"] = t.km.BUS_PORT
    for d in (case.td, os.environ.get("XDG_STATE_HOME")):
        shutil.rmtree(d, ignore_errors=True)
    print(json.dumps(out))
""")


_REVIVE_PROBE = textwrap.dedent("""
    # The trio's second guard, run (the reviewer's ruling of round 1 on fork PR #894): a TunnelConcierge case of this
    # probe's own drives the revive road after the trio's setUp and reports the recorder, what the cleanups return and
    # which checks fired in them, and whether the road is the import-time function again after them.
    import json, os, shutil, sys
    here = sys.argv[1]
    sys.path.insert(0, here)
    sys.path.insert(0, os.path.dirname(here))    # the checkout: the module imports tests.conftest for restore_env
    import tests, tests.conftest
    import test_kernel_tunnels as t
    at_import = t.km._ensure_postal_bus
    case = t.TunnelConcierge("test_attach_requires_host")
    case.setUp()
    out = {"port": t.km.BUS_PORT, "stubbed_in_setup": t.km._ensure_postal_bus is not at_import}
    t.km._revive_postal_bus()
    out["revives"] = list(case.revives)
    case.tearDown()
    fired, check = [], case.assertEqual

    def recorded_check(first, second, msg=None):
        try:
            return check(first, second, msg)
        except AssertionError as e:
            fired.append(str(e))
            raise
    case.assertEqual = recorded_check
    out["cleanups_succeeded"] = case.doCleanups()
    out["fired"] = fired
    out["road_restored"] = t.km._ensure_postal_bus is at_import
    for d in (case.td, os.environ.get("XDG_STATE_HOME")):
        shutil.rmtree(d, ignore_errors=True)
    print(json.dumps(out))
""")


def _loads_kernel(stmt):
    """True for a module-level statement that load_source()s the kernel (its module name starts with romp_kernel)."""
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "load_source" and n.args
               and isinstance(n.args[0], ast.Constant) and str(n.args[0].value).startswith("romp_kernel")
               for n in ast.walk(stmt))


def _attaches_or_detaches(cls):
    """True for a class whose tests reach the tunnel spawn or a detach: a detach_remote call, the /tunnels routes, or an
    attach_remote call outside an assertRaises (an attach expected to raise is refused by host validation before the
    tunnel or the bus is touched)."""
    expected = set()
    for n in ast.walk(cls):
        if isinstance(n, ast.With) and any(isinstance(i.context_expr, ast.Call) and isinstance(i.context_expr.func, ast.Attribute)
                                            and i.context_expr.func.attr == "assertRaises" for i in n.items):
            expected.update(id(c) for b in n.body for c in ast.walk(b))
    for n in ast.walk(cls):
        if isinstance(n, ast.Attribute) and n.attr == "detach_remote":
            return True
        if isinstance(n, ast.Attribute) and n.attr == "attach_remote" and id(n) not in expected:
            return True
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith("/tunnels"):
            return True
    return False


def _method_chain(cls, name, classes, _seen=frozenset()):
    """The FunctionDefs that run when `name` is called on `cls`: its own, then a base's (through the bases defined in
    the same module) when the own one delegates with super().<name>() or there is no own one. Empty when nothing runs.
    Its own are every def of that name its body's import-time blocks bind (_import_time_defs; one under a class-body
    `if` included, round 2 of fork PR #894); `classes` maps a name to a class or to a list of every class bound to it,
    each read; a base defined in another module is not followed (named above _Module); `_seen` cuts a class that names
    itself, through a redefinition, as its own base."""
    owns = _import_time_defs(cls.body)[0].get(name, [])
    chain = list(owns)
    delegates = not owns or any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == name
        and isinstance(n.func.value, ast.Call) and isinstance(n.func.value.func, ast.Name) and n.func.value.func.id == "super"
        for own in owns for n in ast.walk(own))
    if delegates:
        for b in cls.bases:
            if isinstance(b, ast.Name):
                for base in _as_list(classes.get(b.id)):
                    if id(base) not in _seen and base is not cls:
                        chain += _method_chain(base, name, classes, _seen | {id(cls)})
    return chain


def _parser_singletons():
    """{"Load": node, "Store": node, "Del": node}: the expression-context nodes the PARSER hands out, one object each for
    the whole process (`ast.Load()` constructs a new one, so the pins read them from a parse), asserted shared between two
    parses, since the two pins that rest on the sharing would hold vacuously without it."""
    one, two = ast.parse("a = b\ndel c").body, ast.parse("x = y\ndel z").body
    pairs = {"Load": (one[0].value.ctx, two[0].value.ctx), "Store": (one[0].targets[0].ctx, two[0].targets[0].ctx),
             "Del": (one[1].targets[0].ctx, two[1].targets[0].ctx)}
    for kind, (p, q) in pairs.items():
        if p is not q:
            raise AssertionError("two parses gave two %s nodes; the parser hands out one for the process, and the pins over "
                                 "the shared singletons rest on that" % kind)
    return {kind: p for kind, (p, _q) in pairs.items()}


def _restore_dict(obj, saved):
    """`obj.__dict__` put back to `saved`: the cleanup for a plant on a process-wide singleton every test shares."""
    obj.__dict__.clear()
    obj.__dict__.update(saved)


class _Link:
    """One link of the deep synthetic chain the plant hangs on the parser's Load singleton: a deepcopy that follows the tag
    walks the chain and recurses once per link."""

    def __init__(self, tail):
        self.tail = tail


_COLLECTOR_READS = ("get_freeze_count", "get_objects")
#   the two attributes of gc this module may touch, each a read that changes no collector state: the freeze-count pin's
#   (setUpModule, tearDownModule), and the list of tracked objects the drop's pin by live objects reads ast objects in
#   (_ast_nodes_alive and _born, read before and after the loop of a census build that drops a tree)


def _collector_touches(tree):
    """(line, spelling) for every place in `tree` that reaches the collector's state or parse_cache's memo: an attribute of
    a name bound to the gc module (`import gc`, `import gc as g`) other than _COLLECTOR_READS, any name imported from gc
    (`from gc import freeze`), and the attribute `derived` of a name bound to tests/parse_cache.py (`PC.derived`,
    `parse_cache.derived`, or under any alias an import gives it). An attribute is read wherever it stands, called or not,
    so `f = gc.freeze` counts as `gc.freeze`. What it does not read: a string that names one (getattr(gc, "freeze"),
    importlib.import_module("gc"), exec or eval of a text), a module reached through another (sys.modules["gc"]), and a
    helper module this one imports that touches them (tests/parse_cache.py itself calls gc.freeze inside derived(), which
    this module does not call)."""
    gc_names, pc_names, out = set(), set(), []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name == "gc":
                    gc_names.add(a.asname or "gc")
                elif a.name.split(".")[-1] == "parse_cache":
                    pc_names.add(a.asname or a.name)
        elif isinstance(n, ast.ImportFrom):
            if n.module == "gc":
                out += [(n.lineno, "from gc import %s" % a.name) for a in n.names]
            for a in n.names:
                if a.name == "parse_cache":
                    pc_names.add(a.asname or a.name)
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute):
            base = ".".join(_dotted(n.value) or [])
            if base in gc_names and n.attr not in _COLLECTOR_READS:
                out.append((n.lineno, "%s.%s" % (base, n.attr)))
            elif base in pc_names and n.attr == "derived":
                out.append((n.lineno, "%s.derived" % base))
    return sorted(out)


_FREEZE_AT_START = []
#   gc.get_freeze_count() as setUpModule read it, for tearDownModule's second read (THE FREEZE-COUNT PIN)


def setUpModule():
    """The start of this module's run: the built-once and parse-once counts are zeroed (a worker that sets the module up
    again parses and builds again, after tearDownModule released what the run held), and gc.get_freeze_count() is read
    for THE FREEZE-COUNT PIN in tearDownModule (the reviewer's ruling of 2026-09-24 on round 2 of fork PR #894, clause 3).
    Read here and not at import: pytest imports every module at collection, before any test runs, and another module's
    freeze may run in between."""
    _CENSUS_BUILDS.clear()
    _OWN_PARSES.clear()
    _FREEZE_AT_START[:] = [gc.get_freeze_count()]


def tearDownModule():
    """The end of this module's run, and its three pins on what the module leaves behind (the reviewer's rulings of
    2026-09-24 on round 2 of fork PR #894: clause 3 of the first, fork PR #909's pin (2), which the second applies, and
    the third's parse-once rule).
    THE RELEASE: _HELD, the one owner, is emptied, which frees the _Census, and with it the census's own trees, the
    resolver's records and the derivations, by reference count, no collection running here. THE RELEASE PIN: a weak
    reference to the _Census, taken just before the release, is dead just after it. Red under the release removed (the
    trees would stay tracked for the rest of the process, the cost the shape exists to avoid), under a module-scope
    cache that keeps the _Census, and under a value inside it that refers back to it, a cycle only a collection frees.
    It does not see an inner container kept by another name or a cycle among the inner containers that does not pass
    through the _Census (module_level_env_census's docstring gives that half as a measurement), and it is not read
    through gc.get_objects(), which does not list frozen objects. A module run that read no census holds nothing and has
    nothing to release. THE PARSE-ONCE PIN OVER THE RUN: no file was parsed twice by the census in the module's run
    (_OWN_PARSES), whichever tests read it and in whatever order, the per-test pins reading only the files of their own
    census at their own moment; red under a census loop that keeps no tree (a file it dropped is parsed again when the
    resolver reads it), the failure _resolver_targets exists to prevent. THE FREEZE-COUNT PIN: gc.get_freeze_count() is
    read again after the release and is not above what setUpModule read, so the module froze nothing (a build behind
    parse_cache.derived freezes every object tracked when it returns, and every later perf-snapshot read in the process
    walks them). The count is live and falls when a frozen object dies, so an object frozen before this module can lower
    it in between, while only a freeze in this module's run raises it; hence not above, rather than equal. Two reads
    only: each walks the frozen objects. A red here is pytest's error at the teardown of the module's last test, naming
    each pin that failed."""
    held = _HELD[0] if _HELD else None
    ref = weakref.ref(held) if held is not None else None
    del held
    _HELD.clear()
    problems = []
    if ref is not None and ref() is not None:
        problems.append("the release pin: the census's _Census is alive after tearDownModule emptied _HELD, its one owner: "
                        "something else keeps it (a module-scope cache, a test's own reference) or a value inside it refers "
                        "back to it, a cycle only a collection frees, and this module runs none; its trees stay tracked for "
                        "the rest of the process")
    twice = sorted(os.path.relpath(real, HERE) for real, n in _OWN_PARSES.items() if n > 1)
    if twice:
        problems.append("the parse-once pin over the module's run: %s parsed more than once by the census (_own_tree): a file "
                        "the census loop dropped after its walk was read again, by the resolver or another census; "
                        "_resolver_targets decides which trees the loop keeps" % ", ".join(twice))
    after = gc.get_freeze_count()
    before = _FREEZE_AT_START.pop() if _FREEZE_AT_START else None
    if before is not None and after > before:
        problems.append("the freeze-count pin: tests/test_hermetic_kernel_postal.py froze objects in its run: "
                        "gc.get_freeze_count() read %d at setUpModule and %d at tearDownModule, after the release. The module "
                        "changes no collector state (the reviewer's ruling of 2026-09-24 on round 2 of fork PR #894): its "
                        "census parses its own trees and never derives through parse_cache.derived, which calls gc.freeze() "
                        "after a build" % (before, after))
    if problems:
        raise AssertionError("; ".join(problems))


class HermeticKernelPostal(unittest.TestCase):
    def test_kernel_env_gives_every_lab_kernel_its_own_never_started_bus(self):
        env = _lab.kernel_env("/tmp/lab", "/tmp/lab/claude", "/tmp/lab/dist", 1, "tok")
        self.assertEqual(env.get("ROMP_POSTAL_CLIENT_ONLY"), "1", "the kernel's ensure starts no bus")
        self.assertEqual(env.get("ROMP_POSTAL_PEERS"), "0")
        port = int(env.get("ROMP_POSTAL_PORT") or 0)
        self.assertTrue(port and port != 25302, "an ephemeral port, never the machine's fixed bus port: %r" % env.get("ROMP_POSTAL_PORT"))
        self.assertEqual(env.get("ROMP_POSTAL_HERMETIC"), "1", "…marked as the run's own, so the bus honours it under a test (2026-09-11)")

    def test_the_runner_pops_an_inherited_bus_port_and_marks_the_runs_own(self):
        src = open(os.path.join(HERE, "conftest.py"), encoding="utf-8", errors="replace").read()
        self.assertIn('os.environ.pop("ROMP_POSTAL_PORT", None)', src, "a machine's named bus port never reaches a lab or an in-process kernel")
        self.assertIn('os.environ["ROMP_POSTAL_HERMETIC"] = "1"', src)
        floor = src.index('os.environ.pop("ROMP_STATE_DIR", None)')
        self.assertLess(floor, src.index('os.environ.pop("ROMP_POSTAL_PORT", None)'), "…beside the state floor, at import, before any test module loads")
        self.assertLess(src.index('os.environ.pop("ROMP_POSTAL_PORT", None)') - floor, 600, "…right beside it")

    def test_every_test_that_starts_a_kernel_process_carries_the_trio(self):
        offenders = []
        for name in sorted(os.listdir(HERE)):
            if not name.endswith(".py") or name == os.path.basename(__file__):
                continue
            src = open(os.path.join(HERE, name), encoding="utf-8", errors="replace").read()
            if _spawns_kernel(src) and not _hermetic(src):
                offenders.append(name)
        self.assertEqual(offenders, [], "these tests start a kernel process without the postal trio (use kernel_env, or set "
                                        "ROMP_POSTAL_PORT to a free port, ROMP_POSTAL_PEERS=0 and ROMP_POSTAL_CLIENT_ONLY=1): %r" % offenders)

    def test_the_guard_itself_sees_the_spawn_sites(self):
        """the scan must match the spawn idioms the labs use, else the rule above would pass vacuously"""
        hits = [n for n in os.listdir(HERE) if n.endswith(".py") and _spawns_kernel(open(os.path.join(HERE, n), encoding="utf-8", errors="replace").read())]
        self.assertIn("test_federation_missing_served.py", hits)
        self.assertIn("test_notification_tap_resume_browser.py", hits)
        # the shapes the scan must read: a list literal, a path joined or divided, a call split across lines, run as well as Popen
        for src in ('subprocess.Popen([os.path.join(BIN, "romp-kernel")], env=env)',
                    'subprocess.run(\n    [sys.executable, str(BIN / "romp-kernel")],\n    capture_output=True)',
                    'Popen(["python3", "bin/romp-kernel"])',
                    'subprocess.check_output([os.path.join(BIN, "romp"), "kernel", "--serve"])',
                    'KERNEL = os.path.join(BIN, "romp-kernel")\nproc = subprocess.Popen([sys.executable, KERNEL], env=env)'):
            self.assertTrue(_spawns_kernel(src), src)
        for src in ('subprocess.run(["node", "esbuild.js"], cwd=EXT)',
                    'subprocess.run(["bin/romp-postal-service", "ensure"])',
                    'subprocess.run([os.path.join(BIN, "romp-judge"), "--once"])',
                    'load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))'):
            self.assertFalse(_spawns_kernel(src), "not a kernel spawn (a build, the other scripts, an in-process load): " + src)

    def test_the_module_that_loads_the_kernel_in_process_and_attaches_places_each_leg_of_the_trio_where_it_is_read(self):
        """Read by position from the module's ast, not by text (_placement_faults): no leg of the trio is written at
        module level; the setUp of every class that attaches or detaches (its own or through super()) sets all three,
        patches the kernel's BUS_PORT, the import-time read, and stubs its _ensure_postal_bus, the revive road, and
        registers cleanups that put all five back. A
        module-level peers assignment is the leak of 2026-09-18 (the header); a module-level port or client-only
        assignment is the leak of 2026-09-22 (fork PR #813's CI: a real bus from another module's test with this module's
        port and client-only); a tearDown-only restore is the hole of review round 1 (a subclass setUp that raises skips
        it)."""
        self.assertEqual(_placement_faults(ast.parse(_tunnels_source())), [])

    def test_the_placement_check_reds_on_a_planted_module_level_write_and_on_a_teardown_only_restore(self):
        """The check is run over synthetic copies of the real module so it is known to be able to fail (review round 1,
        2026-09-18): a module-level write of ROMP_POSTAL_PEERS restored before the load, in every shape a write takes
        (review round 2 widened the scan from the subscript and setdefault to update, |=, a name bound to os.environ and
        putenv: the subscript alone left a module-level update invisible), each copy faulting exactly once, for the
        write and nothing else; the port and client-only put back at module level where they were until 2026-09-22,
        each faulting once; the dunder and bytes spellings the second verification found passing silently (the third
        commit of 2026-09-22), each faulting once; an augmented write and the key bound as a for, comprehension or with
        target (round 2 of fork PR #894, silent at the round-1 head), each faulting once; a planted update whose keys the
        scan cannot read is loud, naming the line, never a clean pass; and the restore moved back into a tearDown with no cleanup registered, which faults
        every leg and the BUS_PORT and _ensure_postal_bus restores of both attaching classes (the road joined BUS_PORT
        on the reviewer's ruling of round 1 on fork PR #894); and the road's stub deleted from the setUp, and its restore
        dropped from the cleanup, each faulting once per attaching class for that half and nothing else."""
        src = _tunnels_source()
        plants = (
            ("the port, as it was written until 2026-09-22", 'import socket as _socket\n_s = _socket.socket(); _s.bind(("127.0.0.1", 0)); os.environ["ROMP_POSTAL_PORT"] = str(_s.getsockname()[1]); _s.close()\n'),
            ("client-only, as it was written until 2026-09-22", 'os.environ["ROMP_POSTAL_CLIENT_ONLY"] = "1"\n'),
            ("bare", 'os.environ["ROMP_POSTAL_PEERS"] = "0"\n'),
            ("in an if body", 'if True:\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n'),
            ("by setdefault", 'os.environ.setdefault("ROMP_POSTAL_PEERS", "0")\n'),
            ("by update of a dict literal", 'os.environ.update({"ROMP_POSTAL_PEERS": "0"})\n'),
            ("by update with a keyword", 'os.environ.update(ROMP_POSTAL_PEERS="0")\n'),
            ("by update of a module-level name bound to a dict literal", 'PEERS_OFF = {"ROMP_POSTAL_PEERS": "0"}\nos.environ.update(PEERS_OFF)\n'),
            ("by update of a dict() of keywords", 'os.environ.update(dict(ROMP_POSTAL_PEERS="0"))\n'),
            ("by |=", 'os.environ |= {"ROMP_POSTAL_PEERS": "0"}\n'),
            ("through from os import environ", 'from os import environ as _environ\n_environ["ROMP_POSTAL_PEERS"] = "0"\n'),
            ("through a name bound to os.environ", '_env = os.environ\n_env["ROMP_POSTAL_PEERS"] = "0"\n'),
            ("through a name bound to os.environ, by update", '_env = os.environ\n_env.update(ROMP_POSTAL_PEERS="0")\n'),
            ("by os.putenv", 'os.putenv("ROMP_POSTAL_PEERS", "0")\n'),
            # the fixup of 2026-09-22: everything that executes at import is module level
            ("in a class body", 'class _Planted:\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n'),
            ("in a block inside a class body", 'class _Planted:\n    if True:\n        os.environ["ROMP_POSTAL_PEERS"] = "0"\n'),
            ("in an if test", 'if os.environ.setdefault("ROMP_POSTAL_PEERS", "0"):\n    pass\n'),
            ("in a default argument value", 'def _planted_default(x=os.environ.setdefault("ROMP_POSTAL_PEERS", "0")):\n    pass\n'),
            ("through a module-local def called at import", 'def _planted_floor():\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n_planted_floor()\n'),
            ("through a bare decorator", 'def _planted_arm(fn):\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n    return fn\n@_planted_arm\ndef _planted_decorated():\n    pass\n'),
            ("through an instantiation", 'class _PlantedSeam:\n    def __init__(self):\n        os.environ["ROMP_POSTAL_PEERS"] = "0"\n_PlantedSeam()\n'),
            # the third commit of 2026-09-22: the three shapes that passed silently, read now
            ("by __setitem__", 'os.environ.__setitem__("ROMP_POSTAL_PEERS", "0")\n'),
            ("by __setitem__ unbound, the mapping as the first argument", 'dict.__setitem__(os.environ, "ROMP_POSTAL_PEERS", "0")\n'),
            ("through os.environb with a bytes key", 'os.environb[b"ROMP_POSTAL_PEERS"] = b"0"\n'),
            # round 2 of fork PR #894 (the reviewer's ruling of round 1): an augmented write and a key bound as a target
            ("by +=", 'os.environ["ROMP_POSTAL_PEERS"] += ""\n'),
            ("as a for target", 'for os.environ["ROMP_POSTAL_PEERS"] in ["0"]:\n    pass\n'),
            ("as a comprehension target", '[None for os.environ["ROMP_POSTAL_PEERS"] in ["0"]]\n'),
            ("as a with target", 'import contextlib as _contextlib\nwith _contextlib.nullcontext("0") as os.environ["ROMP_POSTAL_PEERS"]:\n    pass\n'),
        )
        for label, lines in plants:
            faults = _placement_faults(ast.parse(_plant(src, lines)))
            self.assertEqual(len(faults), 1, "%s planted write: one fault, for the write, and nothing else: %r" % (label, faults))
            self.assertIn("written at module level", faults[0], label)
        planted_line = src[:src.index(_PLANT_ANCHOR)].count("\n") + 1
        with self.assertRaises(UnreadableEnvWrite) as loud:
            _placement_faults(ast.parse(_plant(src, "os.environ.update(dict(os.environ))\n")))
        self.assertIn("cannot read the keys of this update at line %d" % planted_line, str(loud.exception))
        faults = _placement_faults(ast.parse(_teardown_only_restore(src)))
        self.assertTrue(faults and all("registers no cleanup" in f for f in faults), "tearDown-only restore: %r" % faults)
        for leg in TRIO + ("BUS_PORT", "_ensure_postal_bus"):
            self.assertEqual(sum(1 for f in faults if leg in f), 2, "%s: one fault per attaching class: %r" % (leg, faults))
        self.assertEqual(len(faults), 2 * (len(TRIO) + 2),
                         "the three legs, BUS_PORT and the _ensure_postal_bus road, per attaching class, nothing else: %r" % faults)
        # the revive road's two halves, each planted out of a copy of the real module (the reviewer's ruling of round 1 on
        # fork PR #894): the stub deleted from _PostalTrio.setUp, and the road's restore dropped from _restore_bus
        for label, old, new, want in (
                ("the stub deleted", "        km._ensure_postal_bus = lambda: self.revives.append(port)\n", "",
                 "does not stub the kernel's _ensure_postal_bus"),
                ("the road's restore dropped", "        km._ensure_postal_bus, km.BUS_PORT = ensure, bus_port\n",
                 "        km.BUS_PORT = bus_port\n", "registers no cleanup that restores the kernel's _ensure_postal_bus")):
            self.assertEqual(src.count(old), 1, "%s: the line the copy rewrites is in the module once" % label)
            faults = _placement_faults(ast.parse(src.replace(old, new)))
            self.assertEqual(len(faults), 2, "%s: one fault per attaching class and nothing else: %r" % (label, faults))
            self.assertTrue(all(want in f for f in faults), "%s: %r" % (label, faults))

    def test_no_module_under_tests_writes_an_environment_name_at_module_level_outside_the_licensed_set(self):
        """The import-time half of the rule, held for every .py under tests/, walked recursively so fixtures/ is read too
        (the glob is checked against an independent walk so no file is silently unscanned), and since 2026-09-22 for
        EVERY environment name, not ROMP_POSTAL_PEERS alone (the reviewer's ruling on fork PR #813's finding: a real bus
        started from the peer-notify guard test with the port and client-only tests/test_kernel_tunnels.py wrote at
        module level and the sessions-file seam ten postal modules wrote at module level, and outlived the run). The
        property: no test module writes an environment variable at module level that a spawned child could inherit,
        except the names licensed in LICENSED_MODULE_LEVEL_WRITES, each with a reason that is checked per write (a
        value, a per-test re-assert in conftest, a date and the item a temporary licence waits on). Held as an
        EQUALITY, never a floor: the set of names the test modules write at module level is the licensed set, so a new
        name reds by construction and a licence with no writer left is removed. Every write shape _env_write_records
        reads, in everything that executes at import (module-level if/try/for/with bodies, class bodies, the header
        parts of a def, class or block statement, and the writes reached through a call the scan resolves to a def or
        class under tests/; the fixup of 2026-09-22); a write whose keys the scan cannot read fails here naming the
        file and line rather than passing unread. The per-test half (set in setUp, put back by a cleanup) is a
        convention, checked above for the tunnels module alone; tests/README.md says so. The census's parsed count is
        compared with the module's own os.walk population by EQUALITY (a path the census loop skipped reds here; the
        reviewer's ruling of round 1 on fork PR #894, where the count returned was the paths handed in), and the writer
        modules of the two dated names without a mandate and of the floor-only names equal their committed files
        (_writer_set_faults). THE MECHANISM PINS (the reviewer's ruling of 2026-09-24 on round 2 of fork PR #894, clause
        2, which superseded round 1's builds_of pins with the derived() build): the census is read twice here and the
        whole tree was built once in this module's run (_CENSUS_BUILDS, the count the build keeps; red under a build per
        read, and, with test_the_whole_tree_census_is_built_once_in_the_modules_run_however_many_tests_read_it reading
        it too, under a build per test), each file was walked once in that build (_walk_unit's count; red under a file
        walked twice), and every file the census read was parsed once in the module's run (_OWN_PARSES; red under
        a second parse, and under a census loop that keeps no tree, whose dropped files the resolver then parses again),
        whatever ran before this test. THE DROP, the shape's defining property (the verifier's finding at round 2's
        nineteenth commit of fork PR #894: a loop that kept every tree, fork PR #850's E shape, left the module green),
        held BY EQUALITY with a set this pin derives by a reader of its own (the verifier's finding at the twentieth
        commit: the pin compared the build with _resolver_targets read again, so a widening inside that function, every
        file under tests/ returned or every identifier of every file read, held all 958 trees and passed): the holder
        keeps the tree of a file of the tree for exactly the files _import_line_named_files derives from the import
        lines under tests/, which runs none of _resolver_targets, _import_statement_words, _named_by or
        _tests_tree_walk (red under a loop that keeps every tree, a loop that keeps none, _resolver_targets returning
        every file under tests/ or reading every identifier, and a tree the holder keeps by another road); every file
        the resolver has read is among them (red under a census rule that misses a file the resolver reads); the build
        keeps fewer trees than it walks; the files whose tree outlived its walk in the build (_Derivation's
        `outlived`, a weak reference read right after the loop drops its own) are exactly the derived files (red under
        a loop that keeps a dropped tree alive outside the holder, under one that drops it only when the next file's
        tree replaces it, and under a build that records no survivor); and, BY LIVE OBJECTS (the verifier's finding at
        round 2's thirty-first commit of fork PR #894: a road that kept each dropped tree's statement list left the tree
        object to die, the weak reference saw nothing, and about two million nodes stayed alive; the reviewer's ruling of
        2026-09-24 21:09Z, (2), which set the property as this equality), the ast objects made in the build and alive
        right after its loop, read through gc.get_objects() by identity and counted by class (_Derivation's `born`), EQUAL
        the nodes, by class, of the trees of the files this pin's own reader derives, less any the holder held before the
        build (_tree_classes over _import_line_named_files; red under a road that keeps a dropped tree's statement list on
        a list, its last statement, or the nodes inside its first, each of which the equality of the kept trees and of
        `outlived` above passes)."""
        walked = _tests_tree_walk()
        self.assertGreater(len(walked), 900, "the os.walk finds the tree, recursively, not an empty population: %d files" % len(walked))
        paths = _tests_tree_paths()
        n, counts, records = module_level_env_census(paths)
        self.assertEqual(n, len(walked), "the census parsed every file the os.walk finds, counted inside its loop")
        self.assertEqual(module_level_env_census(paths)[0], n, "the second call reads the held derivation")
        self.assertEqual(_CENSUS_BUILDS[tuple(paths)], 1, "the whole tree was built once in this module's run, however many "
                                                          "reads (the count _census_build keeps; setUpModule zeroes it)")
        parsed, walks = _census_parsed_modules(paths), _census_derivation(paths)[3]
        self.assertEqual({m: k for m, k in walks.items() if k != 1}, {}, "each file was walked once in the build (_walk_unit)")
        self.assertEqual(sorted(walks), sorted(parsed), "every file the build parsed was walked, and no other")
        self.assertEqual([os.path.relpath(p, HERE) for p in paths if _OWN_PARSES[os.path.realpath(p)] != 1], [],
                         "every file the census read was parsed once in this module's run, by the census itself (_own_tree)")
        reals = {p: os.path.realpath(p) for p in paths}
        derived, in_tree = _import_line_named_files(paths), set(reals.values())
        rel = lambda reals_: sorted(os.path.relpath(r, HERE) for r in reals_)
        kept = rel(r for r in _held()["trees"] if r in in_tree)      # no local keeps the holder or its trees
        read = rel(p for p, _root in _held()["modules"] if p in in_tree and p not in derived)
        self.assertEqual(read, [], "every file of the tree the resolver has read is one the pin's own reader derives "
                                   "(_import_line_named_files): the census rule missed a file the resolver reads")
        self.assertEqual(kept, rel(derived),
                         "THE DROP, BY EQUALITY: the holder keeps the tree of a file of the tree for exactly the files the "
                         "pin's own reader derives from the import lines under tests/ (_import_line_named_files, which "
                         "shares no code with _resolver_targets): %s kept and not derived, %s derived and not kept (a loop "
                         "that keeps every tree is fork PR #850's E shape, which the measured rule did not ship)"
                         % (sorted(set(kept) - set(rel(derived))), sorted(set(rel(derived)) - set(kept))))
        self.assertLess(len(kept), n, "THE DROP: the build keeps fewer trees than it walks")
        self.assertEqual(sorted(_census_derivation(paths).outlived), sorted(os.path.relpath(p, HERE) for p in paths if reals[p] in derived),
                         "THE DROP: the files whose tree outlived its walk in the build are exactly the files the pin's own "
                         "reader derives; every other tree is freed when the loop drops it, before the next file is parsed")
        build = _census_derivation(paths)
        taken = sorted(r for r in derived if r not in build.held_before)
        want = _tree_classes(_held()["trees"][r] for r in taken)
        self.assertGreater(sum(want.values()), 0, "the derived files' trees taken in the build have nodes: %d trees" % len(taken))
        self.assertEqual(build.born, want,
                         "THE DROP, BY LIVE OBJECTS: the ast objects made in the build and alive right after its loop (read "
                         "through gc.get_objects(), by identity against the list held from before the loop, by class; None: "
                         "the build dropped no tree) are exactly the nodes of the trees of the files the pin's own reader "
                         "derives (_import_line_named_files), by class: beyond them %s, short of them %s. A road keeps an ast "
                         "object of a tree the loop dropped (its statement list on a list of its own, one statement, a node inside one), "
                         "which the weak reference to the tree itself does not see, or the holder keeps a tree the reader "
                         "does not derive"
                         % (dict(collections.Counter(build.born or {}) - collections.Counter(want)),
                            dict(collections.Counter(want) - collections.Counter(build.born or {}))))
        self.assertEqual(_licence_table_faults(LICENSED_MODULE_LEVEL_WRITES), [], "every licence is checkable and a temporary one is dated")
        self.assertEqual(_licence_faults(records), [])
        faults = _writer_set_faults(records)
        self.assertEqual(faults, [], "the committed writer sets (tests/fixtures/module-level-env-writers) differ from the census's:\n"
                         + "\n".join(faults))
        written = sorted(name for name, recs in records.items() if any(r.module not in FLOOR_MODULES for r in recs))
        self.assertEqual(written, sorted(LICENSED_MODULE_LEVEL_WRITES),
                         "the names the test modules write at module level are exactly the licensed ones (equality, not a floor)")
        for name in LEAK_NAMES:
            self.assertNotIn(name, LICENSED_MODULE_LEVEL_WRITES, "%s is a leak this rule exists to catch, never a licence" % name)
            writers = _leak_writers(records, name)
            self.assertEqual(writers, [], "%s is written at module level by %r (a test module's write, or a floor module's "
                                          "other than the floor value FLOOR_LEAK_WRITES names)" % (name, writers))

    def test_the_whole_tree_census_is_built_once_in_the_modules_run_however_many_tests_read_it(self):
        """The built-once pin's second reader (the reviewer's ruling of 2026-09-24 on round 2 of fork PR #894, clause 2: the
        count is red under a build per test). This test reads the whole-tree census as the census pin does, and each of
        the two asserts, after its own reads, that the module's run built the whole tree once (_CENSUS_BUILDS). With the
        derivation held by the module, the second of the two to run reads the held one, whichever it is; a build per
        test makes that second one red, and a build per read makes the census pin red on its own. Under xdist the two
        can run on different workers, each a process of its own that builds once and counts one."""
        paths = _tests_tree_paths()
        self.assertEqual(module_level_env_census(paths)[0], len(_tests_tree_walk()), "the census parsed the os.walk population")
        self.assertEqual(_CENSUS_BUILDS[tuple(paths)], 1, "the whole tree was built once in this module's run, whichever of "
                                                          "its readers ran first")

    def test_the_drops_count_by_every_node_sees_each_part_a_road_keeps_of_a_dropped_tree(self):
        """THE DROP BY LIVE OBJECTS' read, planted (the verifier's finding at round 2's thirty-first commit of fork PR
        #894: a road that kept each dropped tree's statement list left the tree object to die, so the census pin's weak
        references saw nothing while two million nodes stayed alive; the reviewer's ruling of 2026-09-24 21:09Z, (2)).
        Beside a tree held before the read began and one taken during it, five trees are parsed and dropped while five
        roads keep one part of each (the whole tree, its statement list, one statement, a node inside one, and nothing),
        and what the census build reads as `born` (_born: the ast objects alive after that were not alive before, by
        identity, counted by class) is exactly, class by class, the nodes of the tree taken during it and of the kept
        parts (_tree_classes), the tree held before counted neither twice nor at all. THROUGH THE BUILD: _census_build over
        a synthetic tree whose temporary root stands in for tests/, with its walk (_walk_unit, replaced for the one build)
        keeping each walked tree's statement list on a list, keeps the file an import names and drops the other two, and
        its `born` is the kept file's nodes and the two dropped files' statement lists, by class. The census pin holds
        `born` equal to the derived files' nodes for the whole tree's build, red under a road of each of those shapes put
        in the census loop (the round's notes record the mutants). Each read lists every object the collector tracks
        (gc.get_objects), a cost that grows with the process, so the test takes twelve: two for the read, two for each of
        five builds.
        EACH DROP, BY EVERY LEAF (the verifier's finding at round 2's thirty-second commit of fork PR #894: a loop that
        kept each dropped tree's statement list in a list of its own until the loop ended, and let the list go before
        the read after it, left both reads above with nothing to see and the module green): _leaf_refs over a small tree
        leaves some leaf alive whichever one node or statement list of the tree is kept, and none when nothing is; and
        four builds over synthetic trees of their own, the file an import names sorting last, give (outlived, born beyond
        the kept file's nodes, parts_outlived) as ([kept], {}, [kept]) with nothing kept, and, with a walk that keeps a
        part of each tree until the next file's walk, ([kept], {}, every file) for its statement list and for one leaf,
        which only the read by every leaf sees, and (every file, {}, every file) for the tree itself. The census loop is
        the same code in every build, so a road put in it is red here (the round's notes record the loop's mutant); what
        the build over tests/ itself does not read is in _census_build's docstring. WHAT NO READ SEES, planted as a
        witness (the verifier's finding at round 2's thirty-fourth commit of fork PR #894): a walk that keeps each Name
        node's attribute dict until the build ends, no ast object among what it keeps but the parser's shared ones,
        gives ([kept], {}, [kept]), as nothing kept does."""
        from unittest import mock
        text = "import os\n\n\ndef f(a, b=2):\n    return [a + b, {'k': a}]\n\n\nclass C:\n    x = f(1)\n"
        roads = (("the tree", lambda t: [t]), ("its statement list", lambda t: t.body), ("one statement", lambda t: [t.body[1]]),
                 ("a node inside one", lambda t: [t.body[1].body[0].value]), ("nothing", lambda t: []))
        held = ast.parse(text)
        before = _ast_nodes_alive()
        taken = ast.parse(text)
        kept = {what: road(ast.parse(text)) for what, road in roads}      # each tree dies here, but for the part kept
        want = {what: _tree_classes(part) for what, part in kept.items()}
        born = _born(before)
        total = collections.Counter(_tree_classes([taken]))
        for part in want.values():
            total.update(part)
        kept = before = taken = held = None      # the tree held before the read stays alive through it, and is not born
        self.assertEqual(born, dict(total), "the ast objects alive after the drops that were not alive before are, class by "
                                            "class, the nodes of the tree taken during the read and of the parts the roads "
                                            "keep: %s" % want)
        self.assertEqual((want["nothing"], sum(want["the tree"].values()) - sum(want["its statement list"].values()),
                          set(want["the tree"]) - set(want["its statement list"])), ({}, 1, {"Module"}),
                         "nothing kept, nothing read; the tree is its statement list and its own Module node")
        self.assertGreater(min(sum(want["one statement"].values()), sum(want["a node inside one"].values())), 1,
                           "a part is read with the nodes it holds")
        # THROUGH THE BUILD: a synthetic tree under a temporary root standing in for tests/ (_census_build's `root`), one
        # file an import of another names (the resolver may read it, so the build keeps it) and two no import names
        # (dropped after their walk)
        texts = {"kept_helper.py": "X = 1\n", "uses_it.py": "import kept_helper\n\nY = kept_helper.X\n",
                 "dropped.py": "import os\n\n\ndef g(x):\n    return {x: [x, x + 1]}\n"}
        root = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        for name, body in texts.items():
            with open(os.path.join(root, name), "w", encoding="utf-8") as f:
                f.write(body)
        lists, walk = [], _walk_unit

        def leaky(tree, rel, walks):
            lists.append(tree.body)
            return walk(tree, rel, walks)
        with mock.patch.dict(globals(), {"_walk_unit": leaky}):
            build = _census_build(tuple(os.path.join(root, name) for name in sorted(texts)), root)
        lists = None
        want = collections.Counter(_tree_classes([ast.parse(texts["kept_helper.py"])]))
        want.update(_tree_classes(s for name in ("dropped.py", "uses_it.py") for s in ast.parse(texts[name]).body))
        self.assertEqual(([os.path.basename(m) for m in build.outlived], build.born,
                          [os.path.basename(m) for m in build.parts_outlived]),
                         (["kept_helper.py"], dict(want), ["dropped.py", "kept_helper.py", "uses_it.py"]),
                         "the build keeps the file an import names and drops the other two, and with a walk that keeps each "
                         "tree's statement list `born` is, class by class, the kept file's nodes and the two dropped files' "
                         "lists, and every file's drop leaves a leaf of its tree alive")
        # EACH DROP, BY EVERY LEAF (the verifier's finding at round 2's thirty-second commit of fork PR #894: a loop that
        # kept each dropped tree's statement list until it ended, and let the lists go before the count, left the module
        # green). The reader first: on a small tree, whichever one node or statement list is kept, some leaf outlives the
        # tree, and none does when nothing is kept
        small = "def f(a, b=2):\n    return [a + b, {'k': a}]\n"

        def parts_of(t):
            return [n for n in ast.walk(t) if not isinstance(n, _SHARED_NODE_TYPES)] + [t.body, t.body[0].body]
        alive = []
        for i in range(len(parts_of(ast.parse(small))) + 1):
            tree = ast.parse(small)
            leaves = _leaf_refs(tree)
            kept = parts_of(tree)[i:i + 1]      # the i-th part, and nothing past the last
            tree = None
            alive.append(sum(1 for leaf in leaves if leaf() is not None))
            kept = leaves = None
        self.assertEqual((alive[-1], [i for i, n in enumerate(alive[:-1]) if n == 0]), (0, []),
                         "no leaf outlives a tree of which nothing is kept, and some leaf outlives it whichever part is kept: "
                         "%s" % alive)
        # THROUGH THE BUILD, one road at a time, each over a synthetic tree of its own (a file parsed twice in the module's
        # run reds tearDownModule): the file an import names sorts last, so a part kept until the next file's walk is let
        # go after each dropped file's drop and before the loop ends, and the last file's part is of the tree the build
        # keeps, whose nodes the read after the loop finds born and the pin derives
        last, walk = [], _walk_unit
        order = ("dropped.py", "uses_it.py", "zz_kept.py")
        bodies = {"dropped.py": texts["dropped.py"], "uses_it.py": "import zz_kept\n\nY = zz_kept.X\n", "zz_kept.py": "X = 1\n"}

        def build_over(walk_):
            where = os.path.realpath(tempfile.mkdtemp())
            self.addCleanup(shutil.rmtree, where, True)
            for name in order:
                with open(os.path.join(where, name), "w", encoding="utf-8") as f:
                    f.write(bodies[name])
            with mock.patch.dict(globals(), {"_walk_unit": walk_}):
                b = _census_build(tuple(os.path.join(where, name) for name in order), where)
            last.clear()
            beyond = collections.Counter(b.born) - collections.Counter(_tree_classes([_held()["trees"][os.path.join(where, order[-1])]]))
            return ([os.path.basename(m) for m in b.outlived], dict(beyond), [os.path.basename(m) for m in b.parts_outlived])

        def until_the_next_walk(part):
            def walk_(tree, rel, walks):
                last[:] = [part(tree)]      # the previous file's part is let go here, after that file's drop
                return walk(tree, rel, walks)
            return walk_
        roads = (("its statement list", lambda t: t.body),
                 ("one leaf", lambda t: [n for n in ast.walk(t) if not isinstance(n, _SHARED_NODE_TYPES)][-1]),
                 ("the tree", lambda t: t))
        got = dict([("nothing", build_over(walk))] + [(what, build_over(until_the_next_walk(part))) for what, part in roads])
        dicts = []

        def keeps_attribute_dicts(tree, rel, walks):
            dicts.extend(n.__dict__ for n in ast.walk(tree) if isinstance(n, ast.Name))
            return walk(tree, rel, walks)
        got["each Name node's attribute dict, to the build's end"] = build_over(keeps_attribute_dicts)
        values = [v for d in dicts for v in d.values()]
        dicts = None
        self.assertEqual((len(values) > 0, [v for v in values if isinstance(v, ast.AST) and not isinstance(v, _SHARED_NODE_TYPES)]),
                         (True, []), "the witness keeps a piece of each Name node and no ast object but the parser's shared ones")
        values = None
        kept, every = ["zz_kept.py"], list(order)
        self.assertEqual(got, {"nothing": (kept, {}, kept), "its statement list": (kept, {}, every), "one leaf": (kept, {}, every),
                               "the tree": (every, {}, every), "each Name node's attribute dict, to the build's end": (kept, {}, kept)},
                         "EACH DROP, BY EVERY LEAF, as (outlived, born beyond the kept file's nodes, parts_outlived): with "
                         "nothing kept the build names the one file it keeps; a walk that keeps each tree's statement list, "
                         "or one leaf of it, until the next file's walk leaves the weak reference to the tree and the read "
                         "after the loop nothing to see, and the read by every leaf names both dropped files; one that keeps "
                         "the tree itself is seen by the weak reference too; one that keeps each Name node's attribute dict, no "
                         "ast object, reads as nothing kept (the witness of what no read sees)")

    def test_the_per_name_check_passes_the_floors_client_only_and_faults_every_other_leak_write(self):
        """The census pin's per-name check (_leak_writers) passes one floor write, upstream's client-only line
        (os.environ["ROMP_POSTAL_CLIENT_ONLY"] = "1", their PR 1848, which fork PR #875 folds; the reviewer's ruling of
        round 1 on fork PR #894), and reads every other record of the five leak names. Run over the walker's own
        records: that line spliced into the real tests/conftest.py beside the hermetic marker, and the same line as the
        unittest twin's (tests/__init__.py), leave no writer; the same line planted at module level in a test module (the
        tunnels module, where client-only stood until 2026-09-22) is a writer, named, beside the floor's; so is a floor
        module's client-only of another value, and a floor module's write of each of the other four names (the round's
        first commit skipped every floor record, and the verifier's plant of the sessions-file seam in tests/__init__.py
        passed the census pin); and a conftest.py or __init__.py below tests/ is not a floor module (FLOOR_MODULES names
        the two at the top by their path relative to tests/)."""
        def records_of(src, rel):
            out = collections.defaultdict(list)
            for name, rec in _module_level_records(ast.parse(src), rel):
                out[name].append(rec)
            return out

        def conftest_with(line):
            src = open(os.path.join(HERE, "conftest.py"), encoding="utf-8", errors="replace").read()
            self.assertEqual(src.count(_HERMETIC_MARKER), 1, "the hermetic marker is in tests/conftest.py once")
            return src.replace(_HERMETIC_MARKER, _HERMETIC_MARKER + line)
        leg, line = "ROMP_POSTAL_CLIENT_ONLY", _CLIENT_ONLY_FLOOR
        self.assertEqual(FLOOR_LEAK_WRITES, {leg: "'1'"}, "the one floor write the check passes")
        floor = records_of(open(os.path.join(HERE, "conftest.py"), encoding="utf-8", errors="replace").read(), "conftest.py")
        if not floor[leg]:                  # a conftest that floors client-only already (fork PR #875's) is read as it stands
            floor = records_of(_conftest_with_the_client_only_floor(), "conftest.py")
        self.assertEqual([r.module for r in floor[leg]], ["conftest.py"], "the walker reads the spliced floor line as conftest's write")
        twin = records_of("import os\n" + line, "__init__.py")
        self.assertEqual([r.module for r in twin[leg]], ["__init__.py"])
        self.assertEqual(_leak_writers({leg: floor[leg] + twin[leg]}, leg), [], "the floor's client-only of 1 is the runner's own")
        planted = records_of(_plant(_tunnels_source(), line), "test_kernel_tunnels.py")
        self.assertEqual(_leak_writers({leg: floor[leg] + twin[leg] + planted[leg]}, leg), ["test_kernel_tunnels.py"],
                         "a test module's write still faults, named, beside the floor's")
        for value in ("0", "on"):
            other = 'os.environ["ROMP_POSTAL_CLIENT_ONLY"] = "%s"\n' % value
            self.assertEqual(_leak_writers(records_of(conftest_with(other), "conftest.py"), leg), ["conftest.py"],
                             "a floor module's client-only of %r is not the floor value: a writer" % value)
            self.assertEqual(_leak_writers(records_of("import os\n" + other, "__init__.py"), leg), ["__init__.py"])
        values = {"ROMP_POSTAL_PEERS": "0", "ROMP_POSTAL_PORT": "45678", "ROMP_SESSIONS_FILE": "sessions.json", "ROMP_POSTAL_HOST": "TESTHOST"}
        self.assertEqual(sorted(values), sorted(set(LEAK_NAMES) - {leg}), "every leak name other than client-only is planted")
        for name, value in sorted(values.items()):
            write = 'os.environ["%s"] = "%s"\n' % (name, value)
            self.assertEqual(_leak_writers(records_of(conftest_with(write), "conftest.py"), name), ["conftest.py"],
                             "%s written by the runner's floor is a leak, named" % name)
            self.assertEqual(_leak_writers(records_of("import os\n" + write, "__init__.py"), name), ["__init__.py"],
                             "%s written by the unittest twin is a leak, named" % name)
        for rel in (os.path.join("fixtures", "notes-api", "conftest.py"), os.path.join("fixtures", "notes-api", "__init__.py")):
            self.assertEqual(_leak_writers(records_of("import os\n" + line, rel), leg), [rel], "%s is not a floor module" % rel)

    def test_the_licence_check_reds_on_a_new_name_on_each_fixed_leak_put_back_and_on_a_value_outside_its_licence(self):
        """The fault list is run over synthetic records so it is known to be able to fail: a name outside the licensed set
        (one fault naming the module, the line and the remedy); each leak this rule was written for, put back into the
        real module that wrote it (the tunnels module's port and client-only through the same planting the placement
        check uses, the sessions-file seam and the postal host after the seam file's line in the delegation module);
        the dead port, the browser switch, the catalog switch, the scope switch, the models URL and the claude config
        dir written with a value outside their licence, the models URL on a live loopback port and the state dir as a
        bare mkdtemp among them (each passing at the round-1 head; the reviewer's ruling of round 1 on fork PR #894
        narrowed the URL to port 9 and dropped the bare mkdtemp no state-dir writer uses); the temp-root licences (the
        state preamble, the claude config dir, the service-env path) written with a mkdtemp or a TemporaryDirectory
        under a real directory (`dir=`, or the positional dir), which the regex before the third commit of 2026-09-22
        accepted; a name bound once to a mkdtemp
        and rebound at import by a for target (in a block or a class body too), a with target, an except name, a def, a
        class, a match capture or a `global` in a def the module calls, each passing the licence at the round-1 head
        (round 2 of fork PR #894), and by a star import or a `type` statement (3.12 on), each passing the licence at
        round 2's eleventh commit (the verifier's findings on it); an augmented write of the browser switch, and a starred
        putenv (a SyntaxError naming no module at the round-1 head); a licence whose re-assert conftest dropped; and a
        dead licence. The floor modules are never faulted, whatever they write; a licensed write is clean, every mkdtemp
        form the census shows among them, and so is a bare annotation of a leak name, which writes nothing (a new-name
        fault at the eleventh commit). A name rebound through the module's namespace (`globals()["_ROOT"] = v`) is not
        seen, so its first assignment is the value checked and the write passes: that residual is named above _Module
        ([namespace-rebinding]) and held here as it is, so a change that starts reading it reds (the verifier's finding on
        round 2 of fork PR #894, where _resolved's docstring said a name bound again by anything stays a name). The same
        holds for a name rebound by a string that exec or eval runs, an assignment in an exec string and a walrus in an
        eval string ([exec-eval]; the verifier's findings on round 2's thirteenth commit, where the texts named the
        namespace alone, and on its fourteenth, where only the exec form was held), each held here beside it."""
        def records_of(src, rel):
            out = collections.defaultdict(list)
            for name, rec in _module_level_records(ast.parse(src), rel):
                out[name].append(rec)
            return dict(out)
        reasserted = _conftest_reasserted_union()
        full = lambda src, rel: _licence_faults({**_all_licensed_once(), **records_of(src, rel)}, reasserted)
        faults = full('import os\nos.environ["ROMP_NEW_NAME"] = "1"\n', "test_planted.py")
        self.assertEqual(len(faults), 1, faults)
        self.assertIn("ROMP_NEW_NAME is written at module level by test_planted.py:2 (assignment)", faults[0])
        self.assertIn("not in the licensed set", faults[0])
        self.assertIn("set it in setUp", faults[0])
        # the fixup of 2026-09-22: a class body and a call at import are module level, and the locator says how
        faults = full('import os\nclass _Planted:\n    os.environ["ROMP_NEW_NAME"] = "1"\n', "test_planted.py")
        self.assertEqual(len(faults), 1, faults)
        self.assertIn("ROMP_NEW_NAME is written at module level by test_planted.py:3 (assignment, nested in a module-level block or a class body)", faults[0])
        faults = full('import os\ndef _floor():\n    os.environ["ROMP_NEW_NAME"] = "1"\n_floor()\n', "test_planted.py")
        self.assertEqual(len(faults), 1, faults)
        self.assertIn("ROMP_NEW_NAME is written at module level by test_planted.py:4 (assignment, through _floor() at test_planted.py:2, "
                      "the write at line 3)", faults[0])
        # each fixed leak, put back where it was
        port_back = _plant(_tunnels_source(), 'import socket as _socket\n_s = _socket.socket(); _s.bind(("127.0.0.1", 0)); '
                                              'os.environ["ROMP_POSTAL_PORT"] = str(_s.getsockname()[1]); _s.close()\n'
                                              'os.environ["ROMP_POSTAL_CLIENT_ONLY"] = "1"\n')
        faults = full(port_back, "test_kernel_tunnels.py")
        self.assertEqual(sorted(f.split(" is written")[0] for f in faults), ["ROMP_POSTAL_CLIENT_ONLY", "ROMP_POSTAL_PORT"], faults)
        deleg = open(os.path.join(HERE, "test_tracked_delegation.py"), encoding="utf-8", errors="replace").read()
        anchor = 'os.environ["ROMP_SESSIONS_FILE"]'
        self.assertNotIn("\n" + anchor + " = ", deleg, "the delegation module writes the seam at module level again")
        seam_line = next(l for l in deleg.splitlines() if l.startswith("_SESS = "))
        seam_back = deleg.replace(seam_line + "\n", seam_line + "\nos.environ[\"ROMP_SESSIONS_FILE\"] = _SESS\nos.environ[\"ROMP_POSTAL_HOST\"] = \"TESTHOST\"\n", 1)
        faults = full(seam_back, "test_tracked_delegation.py")
        self.assertEqual(sorted(f.split(" is written")[0] for f in faults), ["ROMP_POSTAL_HOST", "ROMP_SESSIONS_FILE"], faults)
        self.assertEqual(full(deleg, "test_tracked_delegation.py"), [], "the real delegation module is clean")
        for name in ("ROMP_POSTAL_PEERS", "ROMP_POSTAL_PORT", "ROMP_POSTAL_CLIENT_ONLY", "ROMP_SESSIONS_FILE", "ROMP_POSTAL_HOST"):
            faults = full('import os\nos.environ["%s"] = "x"\n' % name, "test_planted.py")
            self.assertEqual(len(faults), 1, (name, faults))
            self.assertTrue(faults[0].startswith(name + " is written at module level"), faults[0])
        # a value outside the licence
        for line, expect in (('os.environ["ROMP_MANAGER_PORT"] = "7432"', "licensed for the value '1' alone"),
                             ('os.environ["ROMP_KERNEL_NO_OPEN"] = "0"', "licensed for the value '1' alone"),
                             ('os.environ["ROMP_MODEL_CATALOG"] = "on"', "licensed for the value 'off' alone"),
                             ('os.environ["ROMP_CLI_SCOPE"] = "1"', "licensed for the value '0' alone"),
                             ('os.environ["ROMP_MODELS_URL"] = "https://api.example.invalid/v1/models"', "not one this licence covers"),
                             # the reviewer's ruling of round 1 on fork PR #894: a live loopback port, and a bare mkdtemp as
                             # the state dir, each passed before
                             ('os.environ["ROMP_MODELS_URL"] = "http://127.0.0.1:45678/v1/models"',
                              "the value 'http://127.0.0.1:45678/v1/models' is not one this licence covers"),
                             ('os.environ["ROMP_MODELS_URL"] = "http://127.0.0.1:19/v1/models"', "not one this licence covers"),
                             ('os.environ["ROMP_STATE_DIR"] = tempfile.mkdtemp()', "the value tempfile.mkdtemp() is not one this licence covers"),
                             ('_ROOT = tempfile.mkdtemp()\nos.environ["ROMP_STATE_DIR"] = _ROOT',
                              "_ROOT (that is, tempfile.mkdtemp()) is not one this licence covers"),
                             ('os.environ["CLAUDE_CONFIG_DIR"] = "/x/claude"', "not one this licence covers"),
                             ('DEAD = {"ROMP_KERNEL_PORT": "29855"}\nos.environ.update(DEAD)', "licensed for the value '1' alone"),
                             # the fixup of 2026-09-22: the five licences that had no value condition, and a value through a name
                             ('os.environ["XDG_STATE_HOME"] = "/srv/romp-state"', "not one this licence covers"),
                             ('os.environ["XDG_STATE_HOME"] = os.path.expanduser("~/.local/state")', "not one this licence covers"),
                             ('_ROOT = tempfile.mkdtemp()\n_ROOT = "/srv/romp-state"\nos.environ["XDG_STATE_HOME"] = _ROOT', "bound more than once at import"),
                             ('_ROOT = "/srv/romp-state"\nos.environ["XDG_STATE_HOME"] = _ROOT', "_ROOT (that is, '/srv/romp-state') is not one this licence covers"),
                             ('os.environ["ROMP_STATE_DIR"] = "/srv/romp"', "not one this licence covers"),
                             ('os.environ["ROMP_STATE_DIR"] = os.environ["XDG_STATE_HOME"]', "not one this licence covers"),
                             ('os.environ["ROMP_SERVE_TOKEN"] = open("/srv/serve-token").read()', "not one this licence covers"),
                             ('os.environ["ROMP_SERVE_TOKEN"] = os.environ["SOME_OTHER_NAME"]', "not one this licence covers"),
                             ('os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.expanduser("~/.config/romp/service.env")', "not one this licence covers"),
                             ('os.environ["ROMP_SERVICE_ENV"] = "/etc/romp/service.env"', "not one this licence covers"),
                             ('_ROOT = "/x/claude"\nos.environ["CLAUDE_CONFIG_DIR"] = _ROOT', "_ROOT (that is, '/x/claude') is not one this licence covers"),
                             # the third commit of 2026-09-22: a temp-root licence requires a bare mkdtemp (a literal prefix allowed), never a dir=
                             ('os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp(dir="/srv/real-state")', "the value tempfile.mkdtemp(dir='/srv/real-state') is not one this licence covers"),
                             ('os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp("", "romp-", "/srv/real-state")', "not one this licence covers"),
                             ('_ROOT = tempfile.mkdtemp(dir="/srv/real-state")\nos.environ["XDG_STATE_HOME"] = _ROOT', "_ROOT (that is, tempfile.mkdtemp(dir='/srv/real-state')) is not one this licence covers"),
                             ('os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp(dir="/srv/real-state")', "not one this licence covers"),
                             ('_TD = tempfile.TemporaryDirectory(dir="/srv/real-state")\nos.environ["ROMP_STATE_DIR"] = _TD.name', "not one this licence covers"),
                             ('os.environ["ROMP_STATE_DIR"] = os.path.join(tempfile.mkdtemp(dir="/srv/real-state"), "romp")', "not one this licence covers"),
                             ('os.environ["ROMP_STATE_DIR"] = os.path.join(tempfile.mkdtemp(), sub)', "not one this licence covers"),
                             ('os.environ["ROMP_SERVICE_ENV_FILE"] = tempfile.mkdtemp(dir="/srv/real-state") + "/absent.env"', "not one this licence covers"),
                             ('os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.join(os.environ["XDG_STATE_HOME"], sub)', "not one this licence covers"),
                             ('os.environ["ROMP_SERVICE_ENV"] = os.path.join(tempfile.mkdtemp(suffix="-real"), "service.env")', "not one this licence covers"),
                             # round 2 of fork PR #894 (the reviewer's ruling of round 1): a name rebound at import by a
                             # form the value resolver read no binding from passed a value the module never writes
                             ('_ROOT = tempfile.mkdtemp()\nfor _ROOT in ("/srv/real-state",):\n    pass\nos.environ["XDG_STATE_HOME"] = _ROOT', "bound more than once at import"),
                             ('_ROOT = tempfile.mkdtemp()\nif True:\n    for _ROOT in ("/srv/real-state",):\n        pass\nos.environ["XDG_STATE_HOME"] = _ROOT', "bound more than once at import"),
                             ('_ROOT = tempfile.mkdtemp()\nwith open("/srv/real-state") as _ROOT:\n    pass\nos.environ["XDG_STATE_HOME"] = _ROOT', "bound more than once at import"),
                             ('_ROOT = tempfile.mkdtemp()\ntry:\n    pass\nexcept OSError as _ROOT:\n    pass\nos.environ["XDG_STATE_HOME"] = _ROOT', "bound more than once at import"),
                             ('_ROOT = tempfile.mkdtemp()\ndef _ROOT():\n    pass\nos.environ["XDG_STATE_HOME"] = _ROOT', "bound more than once at import"),
                             ('_ROOT = tempfile.mkdtemp()\nclass _ROOT:\n    pass\nos.environ["XDG_STATE_HOME"] = _ROOT', "bound more than once at import"),
                             ('_ROOT = tempfile.mkdtemp()\nmatch "/srv/real-state":\n    case _ROOT:\n        pass\nos.environ["XDG_STATE_HOME"] = _ROOT', "bound more than once at import"),
                             ('_ROOT = tempfile.mkdtemp()\nmatch ["/srv/real-state"]:\n    case [*_ROOT]:\n        pass\nos.environ["XDG_STATE_HOME"] = _ROOT', "bound more than once at import"),
                             ('_ROOT = tempfile.mkdtemp()\nmatch {"k": 1}:\n    case {**_ROOT}:\n        pass\nos.environ["XDG_STATE_HOME"] = _ROOT', "bound more than once at import"),
                             ('_ROOT = tempfile.mkdtemp()\nclass _K:\n    for _ROOT in ("/srv/real-state",):\n        pass\nos.environ["XDG_STATE_HOME"] = _ROOT', "bound more than once at import"),
                             ('_ROOT = tempfile.mkdtemp()\ndef _real():\n    global _ROOT\n    _ROOT = "/srv/real-state"\n_real()\nos.environ["XDG_STATE_HOME"] = _ROOT', "bound more than once at import"),
                             # the verifier's findings on round 2 of fork PR #894: a star import binds names no text spells
                             ('_ROOT = tempfile.mkdtemp()\nfrom h_star import *\nos.environ["XDG_STATE_HOME"] = _ROOT',
                              "a star import counting as a binding of every name"),
                             # an augmented write has no value to meet a licence with; a starred value is read, not a crash
                             ('os.environ["ROMP_KERNEL_NO_OPEN"] += "1"', "licensed for the value '1' alone, not a shape with no value"),
                             ('rest = ("0",)\nos.putenv("ROMP_X", *rest)', "by test_planted.py:3 (putenv) and is not in the licensed set")):
            faults = full("import os\n" + line + "\n", "test_planted.py")
            self.assertEqual(len(faults), 1, (line, faults))
            self.assertIn(expect, faults[0], line)
        for line in ('os.environ["ROMP_MANAGER_PORT"] = "1"', 'os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")',
                     'os.environ["ROMP_KERNEL_NO_OPEN"] = "1"', 'os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()',
                     'os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()', 'DEAD = {"ROMP_KERNEL_PORT": "1"}\nos.environ.update(DEAD)',
                     # the fixup of 2026-09-22: every value shape the tree writes, through a name where the tree does
                     '_ROOT = tempfile.mkdtemp()\nos.environ["XDG_STATE_HOME"] = _ROOT',
                     'STATE_HOME = os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp(prefix="romp-tests-state-")',
                     '_TD = tempfile.TemporaryDirectory()\nos.environ["ROMP_STATE_DIR"] = _TD.name',
                     '_PREV = os.environ.get("ROMP_STATE_DIR")\nos.environ["ROMP_STATE_DIR"] = _PREV',
                     '_ROOT = tempfile.mkdtemp()\nos.environ["ROMP_STATE_DIR"] = os.path.join(_ROOT, "romp")',
                     'os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")',
                     '_prev = os.environ.get("ROMP_SERVE_TOKEN")\nos.environ["ROMP_SERVE_TOKEN"] = _prev',
                     'os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")\n'
                     'os.environ["ROMP_SERVICE_ENV"] = os.environ["ROMP_SERVICE_ENV_FILE"]',
                     '_STATE = tempfile.mkdtemp()\nos.environ["ROMP_SERVICE_ENV_FILE"] = _STATE + "/absent.env"',
                     # the third commit of 2026-09-22: the prefixed forms the census shows, clean
                     'os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp(prefix="romp-envnames-")',
                     '_ROOT = tempfile.mkdtemp(prefix="romp-envnames-")\nos.environ["ROMP_SERVICE_ENV_FILE"] = _ROOT + "/absent.env"',
                     'os.environ["ROMP_STATE_DIR"] = os.path.join(tempfile.mkdtemp(prefix="romp-tests-state-"), "romp")',
                     'class _K:\n    os.environ["ROMP_KERNEL_NO_OPEN"] = "1"',
                     'def _floor():\n    os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")\n_floor()',
                     'os.environ["ROMP_POSTAL_PEERS"]: str'):          # a bare annotation writes nothing
            self.assertEqual(full("import os, tempfile\n" + line + "\n", "test_planted.py"), [], line)
        if _TYPE_ALIAS is not None:     # `type X = ...` parses from 3.12 on
            faults = full('import os, tempfile\n_ROOT = tempfile.mkdtemp()\ntype _ROOT = str\nos.environ["XDG_STATE_HOME"] = _ROOT\n',
                          "test_planted.py")
            self.assertEqual(len(faults), 1, faults)
            self.assertIn("bound more than once at import", faults[0])
        # the disclosed residuals [namespace-rebinding] and [exec-eval]: the rebinding through globals() or by a string
        # exec or eval runs (a walrus binds in an eval string) is not seen, the value resolves to the first assignment,
        # and the licence passes a value the module never writes
        for tag, rebinding in (("namespace-rebinding", 'globals()["_ROOT"] = "/srv/real-state"'),
                               ("exec-eval", "exec('_ROOT = \"/srv/real-state\"')"),
                               ("exec-eval", "eval('(_ROOT := \"/srv/real-state\")')")):
            spoofed = 'import os, tempfile\n_ROOT = tempfile.mkdtemp()\n%s\nos.environ["XDG_STATE_HOME"] = _ROOT\n' % rebinding
            recs = _module_level_env_write_records(ast.parse(spoofed), "test_planted.py")
            self.assertEqual([(w.key, w.resolved) for w, _n in recs], [("XDG_STATE_HOME", "tempfile.mkdtemp()")],
                             "a rebinding the module does not spell is not seen by the value resolver: %s" % rebinding)
            self.assertEqual(full(spoofed, "test_planted.py"), [], "the residual named above _Module, [%s]" % tag)
        # the floor modules are licensed wholesale
        self.assertEqual(full('import os\nos.environ["ROMP_ANYTHING"] = "1"\n', "conftest.py"), [])
        # a re-asserted licence stands only while conftest re-asserts the name
        faults = _licence_faults(_all_licensed_once(), reasserted - {"ROMP_MANAGER_PORT"})
        self.assertEqual(faults, ["ROMP_MANAGER_PORT at test_licensed.py:1 (assignment): licensed only while tests/conftest.py "
                                  "re-asserts ROMP_MANAGER_PORT before every test (an unconditional plain assignment or pop "
                                  "before the yield of a function-scoped autouse fixture, which a child pytest over the "
                                  "conftest sees run), and it no longer does"])
        # a refusal of the conftest reader is named in the fault it causes (_Reasserted.refused)
        faults = _licence_faults(_all_licensed_once(), reasserted - {"ROMP_MANAGER_PORT"}, ("_p (line 3): planted",))
        self.assertEqual(faults, ["ROMP_MANAGER_PORT at test_licensed.py:1 (assignment): licensed only while tests/conftest.py "
                                  "re-asserts ROMP_MANAGER_PORT before every test (an unconditional plain assignment or pop "
                                  "before the yield of a function-scoped autouse fixture, which a child pytest over the "
                                  "conftest sees run), and it no longer does; the conftest reader refused 1 of its fixtures "
                                  "or names, named at the end of this list",
                                  "the conftest reader's refusals (_conftest_reasserts_proved): _p (line 3): planted"],
                         "a refusal of the conftest reader is counted in the fault it causes and named once at the end")
        # a dead licence is a fault
        without = {k: v for k, v in _all_licensed_once().items() if k != "ROMP_MODELS_URL"}
        self.assertEqual(_licence_faults(without, reasserted),
                         ["ROMP_MODELS_URL is licensed but no test module writes it at module level any more: remove the licence"])

    def test_conftest_re_asserts_the_names_the_re_asserted_licences_rest_on(self):
        """The licences marked `reasserted` are conditions on tests/conftest.py, read from its autouse fixtures by
        _conftest_reasserted_names: the dead ports (both spellings of the kernel's), the catalog and scope switches, the
        claude config dir, the service-env pair (a for over a literal tuple), and since 2026-09-22 the postal port,
        POPPED per test (a pop is how an unset floor is re-asserted; the finding's module-level port survived collection
        because the pop was at import alone). The port is asserted among the removals and NOT among the writes: a
        fixture that set it, to any value, would name a port to every test with the run's hermetic marker beside it,
        which licenses a bind under a test at any value but the fixed port (the refuter's narrowing on round 1 of fork
        PR #894); the executed check is test_a_port_one_test_sets_is_gone_when_the_next_test_starts, a child pytest in
        which one test sets the port to a non-default value and the next reads it absent. Since the reviewer's ruling of
        round 1 on fork PR #894 only an unconditional plain assignment or pop before the yield of a function-scoped
        autouse fixture counts, one in a for over a non-empty literal tuple included. Seventeen shapes, each accepted at
        the round-1 head, are planted here and refused: the refuter's six (a setdefault, a session or module scope, a
        write after the yield, one under an if, one in a nested def) and eleven more of the classes the ruling names (a
        scope that is not a literal, a class scope, a with, a try, a while, a match, a del, a literal loop that breaks, a
        for over a list literal, a write after a return, a nested def whose default is the fixture's yield). The
        refuter's other two probes, a plain assignment and a value other than the floor's, are planted and accepted with
        the forms today's conftest uses: the rule does not read the value. The two shapes the reader's docstring names as
        not read, a write through a call and a pop whose value is assigned, are planted as read as no re-assert, and so is
        a literal loop that rebinds its own name. Since the verifier's findings on round 2 of fork PR #894 the port's "not
        among the writes" half reads the WIDE writes (_conftest_fixture_env_writes), so a write of the port in an autouse
        fixture beside the pop, conditional, after the yield, by setdefault or in a session-scoped fixture, is among them,
        where the narrow writes the half read at round 2's sixteenth commit had none of the four; and since the verifier's
        findings at the next commit a write of the port in a fixture that is not autouse, under the bare decorator or the
        called one, is among them too (the wide read had named that class unread for a false reason:
        test_a_fixture_that_is_not_autouse_writes_for_the_tests_after_it runs the premise); the other classes of those
        findings have tests of their own (a write after a block that may end the fixture, and a fixture pytest never
        registers or never runs). Since the ruling on the findings at round 2's twentieth commit, the reader
        counts a fixture only where it proves pytest runs it, reading tests/conftest.py's fixtures from the module Python
        imported, and this pin asserts it refused none there
        (test_the_reader_counts_a_fixture_only_where_it_proves_pytest_runs_it holds both roads to a child pytest).
        Since the reviewer's ruling of 2026-09-24 21:09Z (1), that reader is the FILTER, refuse-only, and every plant
        below that it counts is a candidate, not a licence: the names the licences rest on are the ones the EXECUTION
        PROOF grants (_conftest_reasserts_proved: a child pytest over a copy of tests/conftest.py sees the counted
        fixture's own code set or pop each name in the setup of each probe test of its context, each following a write
        of the name; test_a_re_asserted_licence_holds_only_where_a_child_pytest_sees_the_fixtures_own_re_assert
        runs every facet under it). Here: the proof refuses nothing over the real conftest and grants every name the
        filter counts, eleven today, among them each name a `reasserted` licence names; and THE LIVE CONFTEST MODULES,
        the conftest.py files a run under tests/ loads (every one under tests/, walked, and one at the checkout's root),
        are one, tests/conftest.py, whose fixtures the filter refuses none of."""
        got = _conftest_reasserts_proved()
        names = got.writes | got.removals
        self.assertEqual(got.refused, (), "the filter refuses none of tests/conftest.py's function-scoped autouse fixtures "
                                          "(its module road), and the child pytest sees every name it counts re-asserted")
        live = sorted(p for p in _tests_tree_walk() if os.path.basename(p) == "conftest.py")
        live += [p for p in (os.path.join(os.path.dirname(HERE), "conftest.py"),) if os.path.isfile(p)]
        self.assertEqual([os.path.relpath(p, HERE) for p in live], ["conftest.py"], "the live conftest modules: one")
        sites, refused = _reassert_sites()
        self.assertEqual((refused, set(sites), len(sites)), ((), names, 11),
                         "the filter refuses none of the one live conftest module's fixtures, and the proof grants every name "
                         "it counts")
        for name, lic in LICENSED_MODULE_LEVEL_WRITES.items():
            if lic.reasserted:
                self.assertIn(name, names, "tests/conftest.py no longer re-asserts %s before every test (an unconditional plain "
                                           "assignment or pop before the yield of a function-scoped autouse fixture, seen by "
                                           "a child pytest to run); the reader refused: %s" % (name, list(got.refused)))
        self.assertEqual(("ROMP_POSTAL_PORT" in got.removals, "ROMP_POSTAL_PORT" in _conftest_fixture_env_writes()), (True, False),
                         "the dead-port fixture pops ROMP_POSTAL_PORT before every test, and no fixture of conftest, autouse or "
                         "not, writes it anywhere in its body, in any shape or scope (2026-09-22); the executed check is "
                         "test_a_port_one_test_sets_is_gone_when_the_next_test_starts")
        pop = '    os.environ.pop("ROMP_POSTAL_PORT", None)\n'
        for what, src in (("a conditional write", "@pytest.fixture(autouse=True)\ndef _p():\n" + pop +
                           "    if os.environ.get('CI'):\n        os.environ['ROMP_POSTAL_PORT'] = '45678'\n    yield\n"),
                          ("a write after the yield", "@pytest.fixture(autouse=True)\ndef _p():\n" + pop +
                           "    yield\n    os.environ['ROMP_POSTAL_PORT'] = '45678'\n"),
                          ("a setdefault", "@pytest.fixture(autouse=True)\ndef _p():\n" + pop +
                           "    os.environ.setdefault('ROMP_POSTAL_PORT', '45678')\n    yield\n"),
                          ("a session-scoped fixture's write", "@pytest.fixture(autouse=True)\ndef _p():\n" + pop + "    yield\n"
                           "@pytest.fixture(autouse=True, scope='session')\ndef _s():\n    os.environ['ROMP_POSTAL_PORT'] = '45678'\n    yield\n"),
                          ("a write in a fixture that is not autouse, the bare decorator", "@pytest.fixture(autouse=True)\ndef _p():\n"
                           + pop + "    yield\n@pytest.fixture\ndef _n():\n    os.environ['ROMP_POSTAL_PORT'] = '45678'\n    yield\n"),
                          ("a write in a fixture that is not autouse, the called decorator", "@pytest.fixture(autouse=True)\ndef _p():\n"
                           + pop + "    yield\n@pytest.fixture(scope='module')\ndef _n():\n    os.environ['ROMP_POSTAL_PORT'] = '45678'\n    yield\n")):
            src = "import os, pytest\n" + src
            self.assertEqual(("ROMP_POSTAL_PORT" in _conftest_reasserted_names(src).removals,
                              "ROMP_POSTAL_PORT" in _conftest_fixture_env_writes(src),
                              "ROMP_POSTAL_PORT" in _conftest_reasserted_names(src).writes), (True, True, False),
                             "%s of the port beside the pop: among the wide writes, which the pin reads, and not the narrow ones: %s" % (what, src))
        for name in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV"):
            self.assertIn(name, got.writes, "the service-env pair is re-asserted by a for over a literal tuple")
        # the scan reads a fixture's pop and its assignment apart, and nothing outside an autouse fixture
        planted = ("import os, pytest\n"
                   "os.environ['ROMP_AT_IMPORT'] = '1'\n"
                   "@pytest.fixture(autouse=True)\ndef _f():\n    os.environ['ROMP_SET'] = '1'\n    os.environ.pop('ROMP_POPPED', None)\n    yield\n"
                   "@pytest.fixture\ndef _g():\n    os.environ['ROMP_NOT_AUTOUSE'] = '1'\n    yield\n")
        self.assertEqual(_conftest_reasserted_names(planted), _Reasserted(frozenset({"ROMP_SET"}), frozenset({"ROMP_POPPED"})))

        def conftest(body, decorator="@pytest.fixture(autouse=True)"):
            return "import os, pytest\nSCOPE = 'function'\n%s\ndef _f():\n%s" % (decorator, textwrap.indent(body, "    "))
        plain = 'os.environ["ROMP_MANAGER_PORT"] = "1"\n'
        accepted = (("a plain assignment", conftest(plain + "yield\n")),
                    ("a pop", conftest('os.environ.pop("ROMP_MANAGER_PORT", None)\nyield\n')),
                    ("a chained assignment", conftest('_PORT = os.environ["ROMP_MANAGER_PORT"] = "1"\nyield\n')),
                    ("scope='function' spelled out", conftest(plain + "yield\n", '@pytest.fixture(autouse=True, scope="function")')),
                    ("a for over a literal tuple", conftest('for var in ("ROMP_KERNEL_PORT", "ROMP_MANAGER_PORT"):\n'
                                                            '    os.environ[var] = "1"\nyield\n')),
                    ("a fixture with no yield", conftest(plain)),
                    ("a write after a nested generator def", conftest("def _gen():\n    yield\n" + plain + "yield\n")),
                    ("a value other than the floor's (the licence does not read it)", conftest('os.environ["ROMP_MANAGER_PORT"] = "7432"\nyield\n')))
        for what, src in accepted:
            got = _conftest_reasserted_names(src)
            self.assertIn("ROMP_MANAGER_PORT", got.writes | got.removals, "%s re-asserts the name: %s" % (what, src))
        refused = (("a setdefault", conftest('os.environ.setdefault("ROMP_MANAGER_PORT", "1")\nyield\n')),
                   ("scope='session'", conftest(plain + "yield\n", '@pytest.fixture(autouse=True, scope="session")')),
                   ("scope='module'", conftest(plain + "yield\n", '@pytest.fixture(autouse=True, scope="module")')),
                   ("a scope that is not a literal", conftest(plain + "yield\n", "@pytest.fixture(autouse=True, scope=SCOPE)")),
                   ("a write after the yield", conftest("yield\n" + plain)),
                   ("a write under an if", conftest("if os.environ.get('CI'):\n    " + plain + "yield\n")),
                   ("a write under a with", conftest("with open(os.devnull):\n    " + plain + "yield\n")),
                   ("a write in a def the fixture never calls", conftest("def _later():\n    " + plain + "yield\n")),
                   ("a write under a try", conftest("try:\n    " + plain + "except OSError:\n    pass\nyield\n")),
                   ("scope='class'", conftest(plain + "yield\n", '@pytest.fixture(autouse=True, scope="class")')),
                   ("a del", conftest('del os.environ["ROMP_MANAGER_PORT"]\nyield\n')),
                   ("a literal loop that breaks after its first item", conftest(
                       'for var in ("ROMP_KERNEL_PORT", "ROMP_MANAGER_PORT"):\n    os.environ[var] = "1"\n    break\nyield\n')),
                   ("a write after a return", conftest("return\n" + plain + "yield\n")),
                   ("a write after a nested def whose default is the fixture's yield", conftest(
                       "def _later(x=(yield)):\n    pass\n" + plain)),
                   ("a write under a while", conftest("while not os.environ.get('ROMP_MANAGER_PORT'):\n    " + plain + "yield\n")),
                   ("a write under a match", conftest("match os.environ.get('CI'):\n    case None:\n        " + plain + "yield\n")),
                   ("a for over a list literal", conftest('for var in ["ROMP_MANAGER_PORT"]:\n    os.environ[var] = "1"\nyield\n')))
        self.assertEqual(len(refused), 17, "the refuter's six shapes and eleven more, each accepted at the round-1 head")
        for what, src in refused:
            got = _conftest_reasserted_names(src)
            self.assertNotIn("ROMP_MANAGER_PORT", got.writes | got.removals, "%s does not re-assert the name before every "
                                                                            "test: %s" % (what, src))
        unread = (("a write through a call the fixture makes", "import os, pytest\n\ndef _set():\n    " + plain +
                   "\n@pytest.fixture(autouse=True)\ndef _f():\n    _set()\n    yield\n"),
                  ("a pop whose value is assigned", conftest('_saved = os.environ.pop("ROMP_MANAGER_PORT", None)\nyield\n')))
        for what, src in unread:
            got = _conftest_reasserted_names(src)
            self.assertNotIn("ROMP_MANAGER_PORT", got.writes | got.removals, "%s is not read (the docstring names it): %s" % (what, src))
        rebound = conftest('for var in ("ROMP_KERNEL_PORT", "ROMP_MANAGER_PORT"):\n    var = "ROMP_OTHER"\n'
                           '    os.environ[var] = "1"\nyield\n')
        self.assertEqual(_conftest_reasserted_names(rebound), _Reasserted(frozenset(), frozenset()),
                         "a literal loop that rebinds its own name writes something else: not read")

    def test_a_write_after_a_block_that_may_end_the_fixture_is_no_re_assert(self):
        """The verifier's finding on round 2 of fork PR #894 (the ruled clause: only an UNCONDITIONAL plain assignment or pop
        before the yield counts): the reader stopped at a return or a raise only where it was itself a statement of the
        fixture's body, so a write after `if os.environ.get("CI"): return` counted, and a child pytest showed the test after
        a test that set the name reading it unasserted on the runs the condition held. Each plant was accepted at round 2's
        sixteenth commit and is refused now: a write after an if, a try handler, a with, a for, a while or a match that
        returns, after an if that raises, and after a class body that raises (a class body runs where it stands). A write
        after a block with neither, after a nested def whose body returns (its return is its own) and after an assert (not
        read as an end: the docstring of _conftest_reasserted_names says why) is accepted."""
        def conftest(body):
            return "import os, pytest\n@pytest.fixture(autouse=True)\ndef _f():\n%s" % textwrap.indent(body, "    ")
        plain = 'os.environ["ROMP_MANAGER_PORT"] = "1"\n'
        ends = (("a write after an if that returns", conftest("if os.environ.get('CI'):\n    return\n" + plain)),
                ("a write after a try whose handler returns", conftest("try:\n    import planted_missing\nexcept ImportError:\n"
                                                                        "    return\n" + plain)),
                ("a write after a with that returns", conftest("with open(os.devnull):\n    if os.environ.get('CI'):\n"
                                                                "        return\n" + plain)),
                ("a write after a for that returns", conftest("for _x in ('a',):\n    if os.environ.get('CI'):\n        return\n" + plain)),
                ("a write after a while that returns", conftest("while os.environ.get('CI'):\n    return\n" + plain)),
                ("a write after a match that returns", conftest("match os.environ.get('CI'):\n    case '1':\n        return\n" + plain)),
                ("a write after an if that raises", conftest("if os.environ.get('CI'):\n    raise RuntimeError('planted')\n" + plain)),
                ("a write after a class body that raises", conftest("class _K:\n    if os.environ.get('CI'):\n"
                                                                     "        raise RuntimeError('planted')\n" + plain)))
        for what, src in ends:
            got = _conftest_reasserted_names(src)
            self.assertNotIn("ROMP_MANAGER_PORT", got.writes | got.removals, "%s: not re-asserted before every test: %s" % (what, src))
        for what, src in (("a write after an if with no return or raise", conftest("if os.environ.get('CI'):\n    pass\n" + plain)),
                          ("a write after a nested def whose body returns", conftest("def _g():\n    return 1\n" + plain)),
                          ("a write after an assert", conftest("assert os.devnull\n" + plain))):
            got = _conftest_reasserted_names(src)
            self.assertIn("ROMP_MANAGER_PORT", got.writes | got.removals, "%s re-asserts the name: %s" % (what, src))

    def test_a_fixture_whose_name_the_module_binds_again_re_asserts_nothing(self):
        """The verifier's finding on round 2 of fork PR #894 (the ruled clause: a function-scoped autouse fixture): pytest
        registers the fixtures it finds among the module's attributes after the import, so a fixture def whose name the
        module binds again is never registered and its body never runs, and the reader counted it (a later `def _f():
        yield` and a later `_f = None`, each shown by a child pytest to leave the fixture unrun). Each plant was accepted at
        round 2's sixteenth commit and is refused now: the fixture's name bound by a later plain def, a later assignment,
        an assignment before the def (the def replaces it, refused on the safe side), a later class, a later import, a del,
        a global in a def, a for target, a with target, a walrus and an except name, and a star import, which could bind
        any name. A local of the same name in another def binds nothing of the module's and is accepted."""
        base = '@pytest.fixture(autouse=True)\ndef _f():\n    os.environ["ROMP_MANAGER_PORT"] = "1"\n    yield\n'
        shadowed = (("a later plain def of the name", base + "def _f():\n    yield\n"),
                    ("a later assignment of the name", base + "_f = None\n"),
                    ("an assignment of the name before the def", "_f = None\n" + base),
                    ("a later class of the name", base + "class _f:\n    pass\n"),
                    ("a later import of the name", base + "from os import sep as _f\n"),
                    ("a del of the name", base + "del _f\n"),
                    ("a global of the name in a def", base + "def _g():\n    global _f\n    _f = None\n"),
                    ("a for target of the name", base + "for _f in ():\n    pass\n"),
                    ("a with target of the name", base + "with open(os.devnull) as _f:\n    pass\n"),
                    ("a walrus of the name", base + "(_f := None)\n"),
                    ("an except name of the name", base + "try:\n    pass\nexcept Exception as _f:\n    pass\n"),
                    ("a star import", base + "from os.path import *\n"))
        for what, text in shadowed:
            src = "import os, pytest\n" + text
            got = _conftest_reasserted_names(src)
            self.assertNotIn("ROMP_MANAGER_PORT", got.writes | got.removals, "%s: pytest never registers the fixture: %s" % (what, src))
        kept = "import os, pytest\n" + base + "def _g():\n    _f = 1\n    return _f\n"
        self.assertEqual(_conftest_reasserted_names(kept), _Reasserted(frozenset({"ROMP_MANAGER_PORT"}), frozenset()),
                         "a local of the name in another def binds nothing of the module's: %s" % kept)

    def _synthetic_conftest_run(self, conftest_src, module_src):
        """A child pytest in a scratch directory holding `conftest_src` as its conftest.py (a synthetic one: no copy of
        tests/conftest.py, whose floors would hide what the plant does) and `module_src` as test_probe.py, run with -s so
        the module's prints reach the output. Returns the child's output; its return code must be 0."""
        d = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        for name, text in (("conftest.py", conftest_src), ("test_probe.py", module_src)):
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(text)
        child = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST" and not k.startswith("ROMP_PROBE_")}
        child["TMPDIR"] = d
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-s", "-p", "no:cacheprovider", "--rootdir", d, "test_probe.py"],
                           cwd=d, env=child, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, 0, out[-3000:])
        return out

    def test_a_fixture_another_fixture_registers_over_by_name_re_asserts_nothing(self):
        """The verifier's finding at round 2's seventeenth commit of fork PR #894 (the ruled clause: a function-scoped
        autouse fixture, which the reader counts only where pytest runs it): pytest registers a fixture under its name=
        keyword when its decorator passes one, and of two fixtures a module registers under one name it runs one, so a
        fixture of another def given `name="_f"` leaves `_f`'s body unrun, and the reader read the def's attribute
        name alone. THE PREMISE, run: a child pytest whose conftest pops a probe name in `_f` and registers a second
        autouse fixture `_g` under the name `_f`; its second test reads the value its first test set (the pop never ran),
        where the same conftest without `_g` pops it. THE PLANTS, each read as a re-assert at the seventeenth commit and
        refused now: a later fixture registered over the name, an earlier one, one that is not autouse, one through a
        factory held in a name, one registered by a call that is passed the function, yield_fixture's name= and an
        aliased fixture function's; a name= that is not a literal on another fixture, and keywords unpacked there (either
        could register any name); the fixture's own name= not a literal; its own name= registered again by another
        fixture; and its own name= naming a name another statement of the module binds. Since the verifier's finding at
        round 2's eighteenth commit (a child pytest showed each shadow `_f` as the others do), refused too: a fixture
        registered over the name through functools.partial(pytest.fixture, name=...) and through getattr(pytest,
        "fixture")(name=...), read at eighteen commits as a re-assert; and, the safe side of reading every call's name=,
        a name= equal to the fixture's name, a name= that is not a literal and unpacked keywords on a call of a function
        that registers no fixture.
        Accepted: the fixture's own name= literal that nothing else registers or binds, that name= equal to the def's own
        name (bound once, by the def), and another fixture registered by name= under a different name."""
        probe = "ROMP_PROBE_REASSERT"
        module = ("import os\n\n\ndef test_1_sets_the_name():\n    os.environ[%r] = '45678'\n\n\n"
                  "def test_2_reads_it():\n    print('SEEN=%%s' %% os.environ.get(%r))\n" % (probe, probe))
        popper = "import os, pytest\n\n\n@pytest.fixture(autouse=True)\ndef _f():\n    os.environ.pop(%r, None)\n    yield\n" % probe
        shadowed = popper + "\n\n@pytest.fixture(autouse=True, name='_f')\ndef _g():\n    yield\n"
        self.assertIn("SEEN=45678", self._synthetic_conftest_run(shadowed, module), "a fixture registered over _f by name=: _f's pop never ran")
        self.assertIn("SEEN=None", self._synthetic_conftest_run(popper, module), "the control: _f alone pops the name before each test")
        self.assertEqual((_conftest_reasserted_names(shadowed).removals, _conftest_reasserted_names(popper).removals),
                         (frozenset(), frozenset({probe})), "the reader follows the run: the shadowed pop is no re-assert")
        base = '@pytest.fixture(autouse=True)\ndef _f():\n    os.environ["ROMP_MANAGER_PORT"] = "1"\n    yield\n'
        refused = (("a later fixture registered over the name", base + "@pytest.fixture(autouse=True, name='_f')\ndef _g():\n    yield\n"),
                   ("an earlier fixture registered over the name", "@pytest.fixture(name='_f')\ndef _a():\n    yield\n" + base),
                   ("a fixture that is not autouse registered over the name", base + "@pytest.fixture(name='_f')\ndef _z():\n    yield\n"),
                   ("a factory held in a name that registers the name", base + "_fx = pytest.fixture(name='_f')\n@_fx\ndef _y():\n    yield\n"),
                   ("a fixture registered by a call passed the function", base + "def _body():\n    yield\n_h = pytest.fixture(_body, name='_f')\n"),
                   ("yield_fixture's name=", base + "@pytest.yield_fixture(name='_f')\ndef _w():\n    yield\n"),
                   ("an aliased fixture function's name=", base + "from pytest import fixture as _fixture\n@_fixture(name='_f')\n"
                    "def _v():\n    yield\n"),
                   ("the fixture's own name= registered again by another fixture", base.replace("autouse=True)", "autouse=True, name='_registered')")
                    + "@pytest.fixture(name='_registered')\ndef _g():\n    yield\n"),
                   ("another fixture's name= that is not a literal", base + "N = '_f'\n@pytest.fixture(name=N)\ndef _g():\n    yield\n"),
                   ("another fixture's keywords unpacked", base + "KW = {'name': '_f'}\n@pytest.fixture(**KW)\ndef _g():\n    yield\n"),
                   ("the fixture's own name= not a literal", "N = '_f'\n" + base.replace("autouse=True)", "autouse=True, name=N)")),
                   ("the fixture's own name= naming a name the module binds", base.replace("autouse=True)", "autouse=True, name='_other')")
                    + "def _other():\n    pass\n"),
                   ("a fixture registered over the name through functools.partial", base + "import functools\n"
                    "_fx = functools.partial(pytest.fixture, autouse=True, name='_f')\n@_fx\ndef _g():\n    yield\n"),
                   ("a fixture registered over the name through getattr", base + "@getattr(pytest, 'fixture')(autouse=True, name='_f')\n"
                    "def _g():\n    yield\n"),
                   ("a name= equal to the fixture's name on a call of any other function", base + "_T = dict(name='_f')\n"),
                   ("a name= that is not a literal on a call of any other function", base + "N = '_f'\n_T = dict(name=N)\n"),
                   ("keywords unpacked in a call of any other function", base + "KW = {'name': '_f'}\n_T = dict(**KW)\n"))
        for what, text in refused:
            src = "import os, pytest\n" + text
            got = _conftest_reasserted_names(src)
            self.assertNotIn("ROMP_MANAGER_PORT", got.writes | got.removals, "%s: pytest may not run the fixture: %s" % (what, src))
        accepted = (("the fixture's own name= literal that nothing else registers", base.replace("autouse=True)", "autouse=True, name='_registered')")),
                    ("the fixture's own name= equal to its def's name", base.replace("autouse=True)", "autouse=True, name='_f')")),
                    ("another fixture registered by name= under another name", base + "@pytest.fixture(name='_other')\ndef _g():\n    yield\n"))
        for what, text in accepted:
            src = "import os, pytest\n" + text
            got = _conftest_reasserted_names(src)
            self.assertIn("ROMP_MANAGER_PORT", got.writes | got.removals, "%s: pytest registers and runs the fixture: %s" % (what, src))

    def _synthetic_conftest_dirs_run(self, cases):
        """ONE child pytest over a scratch root holding a directory per case of `cases` ((label, conftest source, {helper
        file: source}, probe name)): each directory has its own conftest.py (pytest scopes a conftest to its directory),
        its helper modules and a test module whose first test sets the probe name and whose second prints it. Returns
        {label: the value the second test read, "None" when unset}; the child's return code must be 0."""
        d = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        for i, (label, conftest_src, helpers, probe) in enumerate(cases):
            sub = os.path.join(d, "c%d" % i)
            os.mkdir(sub)
            module = ("import os\n\n\ndef test_1_sets_the_name():\n    os.environ[%r] = '45678'\n\n\ndef test_2_reads_it():\n"
                      "    print('SEEN[%s]=%%s' %% os.environ.get(%r))\n" % (probe, label, probe))
            for name, text in dict(helpers, **{"conftest.py": conftest_src, "test_case_%d.py" % i: module}).items():
                with open(os.path.join(sub, name), "w", encoding="utf-8") as f:
                    f.write(text)
        child = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST" and not k.startswith("ROMP_PROBE_")}
        child["TMPDIR"] = d
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-s", "-p", "no:cacheprovider", "--rootdir", d, d],
                           cwd=d, env=child, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, 0, out[-3000:])
        seen = {}
        for line in out.splitlines():
            for label, _c, _h, _p in cases:
                mark = "SEEN[%s]=" % label
                if mark in line:
                    seen[label] = line.split(mark, 1)[1].strip()
        return seen

    def test_a_fixture_another_modules_code_registers_over_by_name_re_asserts_nothing(self):
        """The verifier's finding at round 2's nineteenth commit of fork PR #894 (the ruled clause: the reader counts a
        fixture only where pytest runs it): a fixture can be registered over `_f` by code of ANOTHER module, whose name=
        sits in that module's text, where _fixture_names_by_keyword does not read. THE PREMISE, run in one child pytest,
        a directory per case, each conftest popping its probe name in `_f`: the second test reads the value the first
        set (the pop never ran) under the verifier's case (`from _h import fx` and `@fx def _g()`, the helper's fx a
        functools.partial of pytest.fixture with autouse=True and name="_f"), a fixture object imported by name from the
        helper, an attribute of an imported helper module as the decorator, a def of the conftest's own as the decorator
        that applies the helper's factory, an assignment of the helper module's fixture object, and an assignment that
        applies the helper's factory to a def; the control, `_f` alone, pops it, and so does `_f` beside a fixture
        object imported under a name that sorts before `_f` (pytest registers `_f` after it and runs `_f`). THE PLANTS:
        every road, each read as a re-assert at the nineteenth commit, is refused now with every fixture of the module
        (_unproven_statements, the text road's proven list: a decorator that is not pytest's own, an import of a module
        other than pytest's own, the standard library's and the module's own package, and a call other than pytest's
        fixture functions, hookimpl and mark; the case that sorts first is the safe side), and so are a called factory,
        a class decorator, an async def's decorator, a decorator of a def in a module-level block, a subscript as the
        decorator, an attribute of pytest outside the fixture functions, hookimpl and mark (one a plugin could set on
        the module), _pytest's FixtureFunctionMarker (the name passed positionally) and any other name imported from
        _pytest as the decorator (a root is bound by `import pytest` or `from pytest import`, never from the private
        package), pytest rebound by a second import, and a relative import (one named like a standard module too). The
        last two roads, an assignment of the helper module's fixture object and one that applies the helper's factory,
        were read as a re-assert until the reviewer's ruling on the twentieth commit's findings, the unsafe side the
        reader named then (the real conftest takes values from the test package through a module binding, which the
        reader now reads on its module road instead). A decorator and a `from` import inside a def's body, accepted
        until round 2's thirty-second commit of fork PR #894 as code that runs only when the def is called, are refused
        now that the text road reads every def's body (pytest calls a fixture's and a hook's; a false refusal where
        nothing calls the def, the safe side). Accepted: pytest's own decorators (pytest.fixture, pytest.yield_fixture,
        pytest.hookimpl on a hook of _LISTED_HOOKS, a pytest.mark.<name>, pytest under an alias, `from pytest import
        fixture` and a fixture it decorates), and `from` imports of the standard library and of pytest's own (the real
        conftest imports from _pytest._code.code). The real tests/conftest.py is read on the reader's module road
        (test_the_reader_counts_a_fixture_only_where_it_proves_pytest_runs_it has its refusals on the text road)."""
        fx = "import functools, pytest\nfx = functools.partial(pytest.fixture, autouse=True, name='_f')\n"
        thing = "import pytest\n\n\n@pytest.fixture(autouse=True, name='_f')\ndef thing():\n    yield\n"
        roads = (("imported-factory-as-decorator", "from _h_a import fx\n\n\n@fx\ndef _g():\n    yield\n", {"_h_a.py": fx}, "refused"),
                 ("imported-fixture-object", "from _h_b import thing\n", {"_h_b.py": thing}, "refused"),
                 ("module-attribute-as-decorator", "import _h_c\n\n\n@_h_c.fx\ndef _g():\n    yield\n", {"_h_c.py": fx}, "refused"),
                 ("own-def-applying-the-factory", "import _h_d\n\n\ndef reg(f):\n    return _h_d.fx(f)\n\n\n@reg\ndef _g():\n    yield\n",
                  {"_h_d.py": fx}, "refused"),
                 ("imported-fixture-object-sorting-first", "from _h_s import thing as _a\n", {"_h_s.py": thing}, "refused-safe"),
                 ("assigned-module-attribute", "import _h_e\nthing = _h_e.thing\n", {"_h_e.py": thing}, "refused"),
                 ("assigned-factory-call", "import _h_f\n\n\ndef _g():\n    yield\n\n\n_g = _h_f.fx(_g)\n", {"_h_f.py": fx}, "refused"))
        cases, texts = [], {}
        for i, (label, extra, helpers, _kind) in enumerate((("control", "", {}, None),) + roads):
            probe = "ROMP_PROBE_FOREIGN_%d" % i
            texts[label] = ("import os, pytest\n\n\n@pytest.fixture(autouse=True)\ndef _f():\n    os.environ.pop(%r, None)\n"
                            "    yield\n\n\n" % probe + extra, probe)
            cases.append((label, texts[label][0], helpers, probe))
        seen = self._synthetic_conftest_dirs_run(cases)
        self.assertEqual(seen, dict({"control": "None"}, **{label: "None" if kind == "refused-safe" else "45678"
                                                            for label, _e, _h, kind in roads}),
                         "the control's _f pops its name before each test; under each road but the fixture object imported "
                         "under a name that sorts first, _f's pop never ran")
        for label, _e, _h, kind in (("control", "", {}, "counted"),) + roads:
            src, probe = texts[label]
            self.assertEqual(probe in _conftest_reasserted_names(src).removals, kind == "counted",
                             "%s: %s: %s" % (label, {"refused": "refused", "refused-safe": "refused, the safe side",
                                                     "counted": "the control counts"}[kind], src))
        base = '@pytest.fixture(autouse=True)\ndef _f():\n    os.environ["ROMP_MANAGER_PORT"] = "1"\n    yield\n'
        refused = (("a called factory imported from another module", "from _h import make\n@make(autouse=True)\ndef _g():\n    yield\n"),
                   ("a class decorator imported from another module", "import _h\n@_h.fx\nclass _C:\n    pass\n"),
                   ("an async def's decorator from another module", "import _h\n@_h.fx\nasync def _g():\n    pass\n"),
                   ("a decorator of a def in a module-level block", "import _h\nif True:\n    @_h.fx\n    def _g():\n        yield\n"),
                   ("a subscript as the decorator", "DECS = [pytest.fixture(autouse=True)]\n@DECS[0]\ndef _g():\n    yield\n"),
                   ("an attribute of pytest outside the fixture functions, hookimpl and mark", "@pytest.fx\ndef _g():\n    yield\n"),
                   ("_pytest's FixtureFunctionMarker, the name passed positionally", "from _pytest.fixtures import FixtureFunctionMarker\n"
                    "@FixtureFunctionMarker('function', None, True, None, '_f')\ndef _g():\n    yield\n"),
                   ("a fixture function imported from _pytest", "from _pytest.fixtures import fixture as _fx\n@_fx(autouse=True)\ndef _g():\n    yield\n"),
                   ("pytest bound again by a second import", "import _h as pytest\n"),
                   ("a relative import", "from . import _h\n"),
                   ("a relative import named like a standard module", "from .json import loads\n"),
                   ("a decorator and a from import inside a def's body", "def _later():\n    from _h import fx\n\n    @fx\n"
                    "    def _g():\n        yield\n    return _g\n"))
        for what, text in refused:
            src = "import os, pytest\n" + base + text
            got = _conftest_reasserted_names(src)
            self.assertNotEqual(_unproven_statements(ast.parse(src)), [], "%s: %s" % (what, src))
            self.assertNotIn("ROMP_MANAGER_PORT", got.writes | got.removals, "%s: another module's code may register over the name: %s"
                             % (what, src))
        accepted = (("pytest.hookimpl", "@pytest.hookimpl(trylast=True)\ndef pytest_sessionfinish(session):\n    pass\n"),
                    ("a pytest.mark decorator", "@pytest.mark.usefixtures('_f')\ndef _helper():\n    pass\n"),
                    ("from pytest import fixture, and a fixture it decorates", "from pytest import fixture\n@fixture\ndef _other():\n    yield\n"),
                    ("pytest.yield_fixture", "@pytest.yield_fixture\ndef _other():\n    yield\n"),
                    ("pytest imported under an alias", "import pytest as _pt\n@_pt.fixture\ndef _other():\n    yield\n"),
                    ("from imports of the standard library", "from os import path\nfrom collections import abc as _abc\n"),
                    ("a from import of pytest's own", "from _pytest._code.code import ReprFileLocation\n"))
        for what, text in accepted:
            src = "import os, pytest\n" + base + text
            got = _conftest_reasserted_names(src)
            self.assertIn("ROMP_MANAGER_PORT", got.writes | got.removals, "%s: pytest's own, or code that runs only when called: %s"
                          % (what, src))

    def _registration_cases_run(self, cases):
        """ONE child pytest over a scratch root holding a directory per case of `cases` ((label, conftest source, {helper
        file: source}, probe name[, package])): each directory has its own conftest.py and helper modules, and a test
        module whose first test sets the probe name, whose second prints the value it reads, and whose third (the one
        that takes pytest's `request`, which a failed setup made to pass leaves unset) prints the fixtures pytest
        registered from the directory's conftest, read by _pytest_registrations' own source (the function's text, run in
        the child), and its hook implementations, read by _pytest_hook_impls' own source and by the hooks pytest
        registered from it (the plugin manager's hook callers for the module), over the conftest module found among the
        run's plugins by its file. With a package, the conftest and the test module sit in a package of that name inside
        the case's directory (an __init__.py beside them) and the helpers in the case's directory, the first with no
        __init__.py, which pytest puts on sys.path; a helper named with a directory (wave/__init__.py) is written inside
        it. Returns {label: (the value the second test read, "None" when unset;
        the registrations as _pytest_registrations returns them; the conftest's directory; the hooks as
        _pytest_hook_impls returns them; the specs of the hooks pytest registered)}; the child's return code must be 0,
        and every case must report."""
        d = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        reader = textwrap.dedent(inspect.getsource(_pytest_registrations)) + "\n\n" + textwrap.dedent(inspect.getsource(_pytest_hook_impls))
        dirs = {}
        for i, (label, conftest_src, helpers, probe, *package) in enumerate(cases):
            sub = os.path.join(d, "c%02d" % i)
            os.mkdir(sub)
            home = dirs[label] = os.path.join(sub, package[0]) if package else sub
            if package:
                os.mkdir(home)
                with open(os.path.join(home, "__init__.py"), "w", encoding="utf-8"):
                    pass
            module = ("import json, os\n\n\n%s\n\ndef test_1_sets_the_name():\n    os.environ[%r] = '45678'\n\n\n"
                      "def test_2_reads_it():\n"
                      "    print('SEEN[%s]=%%s' %% os.environ.get(%r))\n\n\n"
                      "def test_3_reads_the_conftest(request):\n"
                      "    here = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'conftest.py')\n"
                      "    pm = request.config.pluginmanager\n"
                      "    mods = [m for m in pm.get_plugins()\n"
                      "            if os.path.realpath(getattr(m, '__file__', None) or os.devnull) == here]\n"
                      "    print('REGS[%s]=%%s' %% json.dumps([_pytest_registrations(m) for m in mods], default=repr))\n"
                      "    print('HOOKS[%s]=%%s' %% json.dumps([_pytest_hook_impls(m) for m in mods]))\n"
                      "    print('LIVE[%s]=%%s' %% json.dumps([sorted(h.name for h in pm.get_hookcallers(m) or ()) for m in mods]))\n"
                      % (reader, probe, label, probe, label, label, label))
            for name, text in dict(helpers, **{"conftest.py": conftest_src, "test_case_%02d.py" % i: module}).items():
                at = os.path.join(home if name in ("conftest.py", "test_case_%02d.py" % i) else sub, name)
                os.makedirs(os.path.dirname(at), exist_ok=True)     # a helper inside a package of its own (wave/__init__.py)
                with open(at, "w", encoding="utf-8") as f:
                    f.write(text)
        child = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST" and not k.startswith("ROMP_PROBE_")}
        child["TMPDIR"] = d
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-s", "-p", "no:cacheprovider", "--rootdir", d, d],
                           cwd=d, env=child, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, 0, out[-3000:])
        got = {}
        for label, *_rest in cases:
            reads = {}
            for key in ("SEEN", "REGS", "HOOKS", "LIVE"):
                mark = "%s[%s]=" % (key, label)
                reads[key] = [ln.split(mark, 1)[1].strip() for ln in out.splitlines() if mark in ln]
                self.assertEqual(len(reads[key]), 1, "%s reported %s once: %s" % (label, key, out[-3000:]))
            regs, hooks, live = (json.loads(reads[k][0]) for k in ("REGS", "HOOKS", "LIVE"))
            self.assertEqual((len(regs), len(hooks), len(live)), (1, 1, 1),
                             "%s: the child found its directory's conftest among the plugins once" % label)
            got[label] = (reads["SEEN"][0], [tuple(r[:4]) + (tuple(r[4]) if r[4] else None,) for r in regs[0]], dirs[label],
                          [tuple(h) for h in hooks[0]], live[0])
        return got

    def test_the_reader_counts_a_fixture_only_where_it_proves_pytest_runs_it(self):
        """THE CLASS, closed by construction (the ruling on the verifier's findings at round 2's twentieth
        commit of fork PR #894): the reader counted a fixture that pytest never runs in five cases, each closed by name
        once a child pytest had found it (F2 a later binding of the fixture's name; F2b another def given its name=; F2c
        a name= passed through functools.partial; F2e a decorator imported from another module; N2b a module named like
        the standard library's that a sibling file shadows, and an imported module whose code rebinds pytest.fixture).
        Now a fixture counts only where the reader proves pytest runs it (_conftest_reasserted_names' rule, read on two
        roads). THE PREMISE, run: ONE child pytest, a directory per case, each conftest popping its probe name in `_f`
        and each test module's first test setting it: under each of the five cases (N2b twice), under N2b's third road
        (a value taken through importlib.import_module), and under six roads no earlier plant covered (a write through
        globals(), a string exec, a setattr through sys.modules, a module-level __dir__, a base class whose
        __init_subclass__ rebinds `_f`, and a fixture taken from the conftest's own package, `import <package> as _pkg`
        then `thing = _pkg.thing`, the shape tests/conftest.py takes values from the tests package in), `_f`'s pop never
        ran before the second test, and neither did it under `_f` rebound to a module-scoped fixture of its own
        function; under the control it ran, and under three more cases: another fixture registered under `_f` from an
        attribute that sorts before it (pytest registers `_f` after it), `_f` registered by its own decorator under
        another name (an autouse fixture runs under any name), and `_f` aliased under a second name. Since the verifier's
        finding at round 2's thirty-first commit, whose mutants of the three-part code match and of the import roots
        stayed green, two more cases, each run: a second def of `_f` later in the conftest (pytest registers the later
        def's code, which the first line alone tells from the popper's), and a conftest in a package whose first parent
        with no __init__.py holds a module named like the standard library's (sched.py, taken by `from sched import
        thing` ahead of the standard library's); `_f`'s pop never ran under either. Since its finding at the
        thirty-second commit, whose mutants of the match's other two parts and of _shadowed's other two entry forms
        stayed green, three more, each run: a fixture of another file wrapping a def named `_f` whose first line is the
        popper's, registered under `_f` after it (the file alone tells the two apart), a def of another name compiled in
        the conftest's own file at the popper's first line and registered under `_f` after it (the name alone does), and
        a package directory named like the standard library's (wave/, taken by `from wave import thing`); `_f`'s pop
        never ran under any of the three. Since the reviewer's ruling of 2026-09-24 21:09Z, (3) (every claimed part of
        the helpers' matching rules names its plant or is cut), one more, run: `_f`'s own function registered again
        without autouse, the plant of the code match's autouse part; `_f`'s pop never ran. THE MODULE ROAD: the child's second
        test reads its conftest's fixtures with _pytest_registrations' own source and its hooks with _pytest_hook_impls'
        own, which equal the hooks pytest registered from it, and _why_pytest_does_not_run over the fixtures, with
        _why_a_hook_may_stop_it over the hooks, says pytest runs `_f` in exactly the cases the child saw the pop run, so
        the road that reads tests/conftest.py is held to pytest's behaviour by execution, road by road. THE TEXT ROAD (a
        source handed in, read as sitting in the case's directory) counts `_f` in the control, the renamed case and the
        alias alone, and refuses it everywhere else, each refusal naming what it could not prove: the cases that bind or
        register `_f` by the module's own text by the registration half (_why_not_registered_once), every road through
        another module's code, a call or a namespace write by the proven list (_unproven_statements, a statement of
        which refuses every fixture), and the sorting-first case on the safe side, a false refusal. Before this commit
        the reader counted each of the N2b roads and each of the six new ones, and the round-1 reader counted all of
        them (the round's notes record the runs). THE PROVEN LIST, clause by clause: each shape it leaves off (a
        relative import, a `from` import of the module's own package or an import of its submodule, a fixture or a star
        import of pytest's own, a write through an attribute of pytest or a subscript other than os.environ's, a
        subscript read, a comprehension, a with, a match, a binding of __builtins__ or a module-level __getattr__, a
        decorator not pytest's own, a class keyword, a call in a def's default or a class body, a name of pytest's own
        this process never imported, and an in-place operator on a name at import, in a class body, on a def's
        parameter and on a counter, the last a false refusal) is named, and each it takes (literals, f-strings and
        displays, an attribute chain of the standard library's, a lambda, operators, a conditional and a walrus,
        os.environ written, deleted and added to in place through `os` or a from-imported `environ`, the blocks,
        __all__, an annotation, a class body, pytest's fixture, mark and hookimpl decorators, and imports of the module's own package, the standard library and pytest's own)
        passes. THE IMPORT ROOTS, planted directly: _import_roots names a package's directory and each parent up to the
        first with no __init__.py, and _shadowed finds an entry in the last of them, an entry that is the name itself (a
        bare directory), and a path it cannot list, and names the first of the directories that holds an entry of the
        name, whatever its kind (a regular file named bisect in the first and bisect.py in the last). THE REAL tests/conftest.py is read on
        the module road, where the conftest pin asserts no refusal; the text road would refuse every one of its fixtures,
        on the statements printed here if this test fails (values of the tests package, and calls of defs of its own and
        of the standard library at import and in its fixtures and hooks), which is why it is not read that way."""
        thing = "import pytest\n\n\n@pytest.fixture(autouse=True, name='_f')\ndef thing():\n    yield\n"
        fx = "import functools, pytest\nfx = functools.partial(pytest.fixture, autouse=True, name='_f')\n"
        rebind = "import functools, pytest\npytest.fixture = functools.partial(pytest.fixture, name='_f')\n"

        def popper(probe, decorator="@pytest.fixture(autouse=True)"):
            return "import os, pytest\n\n\n%s\ndef _f():\n    os.environ.pop(%r, None)\n    yield\n\n\n" % (decorator, probe)
        # (label, the conftest's text after the popper, helpers, the popper's decorator, pytest runs _f, the text road
        # counts it, a word its refusal names)
        cases = (("control", "", {}, None, True, True, None),
                 ("F2-later-binding", "_f = None\n", {}, None, False, False, "binds its name _f 2 times"),
                 ("F2b-name-on-another-def", "@pytest.fixture(autouse=True, name='_f')\ndef _g():\n    yield\n", {}, None,
                  False, False, "another call passes name='_f'"),
                 ("F2c-partial", "import functools\n_fx = functools.partial(pytest.fixture, autouse=True, name='_f')\n\n\n"
                  "@_fx\ndef _g():\n    yield\n", {}, None, False, False, "functools.partial"),
                 ("F2e-imported-factory", "from _rc_e import fx\n\n\n@fx\ndef _g():\n    yield\n", {"_rc_e.py": fx}, None,
                  False, False, "an import of _rc_e"),
                 ("N2b-stdlib-named-sibling", "from colorsys import thing\n", {"colorsys.py": thing}, None, False, False,
                  "colorsys is named like a standard-library module"),
                 ("N2b-import-rebinds-pytest-fixture", "import _rc_b\n\n\n@pytest.fixture(autouse=True)\ndef _g():\n    yield\n\n\n"
                  "pytest.fixture = pytest.fixture.func\n", {"_rc_b.py": rebind}, None, False, False, "an import of _rc_b"),
                 ("N2b-importlib-value", "import importlib\nthing = importlib.import_module('_rc_c').thing\n", {"_rc_c.py": thing},
                  None, False, False, "a call of importlib.import_module"),
                 ("new-globals-write", "globals()['_f'] = None\n", {}, None, False, False, "globals()"),
                 ("new-exec-string", "exec('_f = None')\n", {}, None, False, False, "a call of exec"),
                 ("new-sys-modules-setattr", "import sys\nsetattr(sys.modules[__name__], '_f', None)\n", {}, None, False, False,
                  "a call of setattr"),
                 ("new-module-dir", "def __dir__():\n    return ['os', 'pytest']\n", {}, None, False, False,
                  "a module-level binding of __dir__"),
                 ("module-scoped-rebinding", "_f = pytest.fixture(autouse=True, scope='module')(_f._get_wrapped_function())\n",
                  {}, None, False, False, "a call of pytest.fixture(autouse=True, scope='module')"),
                 ("another-name-sorting-first", "@pytest.fixture(autouse=True, name='_f')\ndef _a():\n    yield\n", {}, None,
                  True, False, "another call passes name='_f'"),
                 ("renamed-by-its-own-decorator", "", {}, "@pytest.fixture(autouse=True, name='_renamed')", True, True, None),
                 ("aliased-under-a-second-name", "_z = _f\n", {}, None, True, True, None),
                 ("class-base-init-subclass", "class _B:\n    def __init_subclass__(cls, **kw):\n        globals()['_f'] = None\n\n\n"
                  "class _K(_B):\n    pass\n", {}, None, False, False, "a class with a base or a keyword"),
                 ("own-package-value", "import {package} as _pkg\nthing = _pkg.thing\n", {"__init__.py": thing}, None, False, False,
                  "a value of the module's own package"),
                 ("second-def-of-the-name-later", "@pytest.fixture(autouse=True)\ndef _f():\n    yield\n", {}, None, False, False,
                  "binds its name _f 2 times"),
                 ("N2b-stdlib-named-in-the-first-parent-with-no-init", "from sched import thing\n", {"sched.py": thing}, None,
                  False, False, "sched is named like a standard-library module"),
                 ("another-files-def-of-the-name-at-the-same-first-line", "from _rc_v import _f as _z\n",
                  {"_rc_v.py": thing.replace("def thing", "def _f")}, None, False, False, "an import of _rc_v"),
                 ("a-def-of-another-name-in-the-conftests-file-at-the-same-first-line",
                  "_ns = {}\nexec(compile('\\n\\n\\n' + 'def _h():\\n    yield\\n', __file__, 'exec'), _ns)\n"
                  "_z = pytest.fixture(autouse=True, name='_f')(_ns['_h'])\n", {}, None, False, False, "a call of exec"),
                 ("N2b-stdlib-named-package-directory", "from wave import thing\n", {"wave/__init__.py": thing}, None, False,
                  False, "wave is named like a standard-library module"),
                 ("not-autouse-rebinding", "_f = pytest.fixture(_f._get_wrapped_function())\n", {}, None, False, False,
                  "a call of _f._get_wrapped_function"))
        packages = {"N2b-stdlib-named-in-the-first-parent-with-no-init": "pkg"}
        #   a case whose conftest sits in a package of its own (the name with the case's number), its helpers in the
        #   case's directory, the parent pytest puts on sys.path
        texts, run = {}, []
        for i, (label, extra, helpers, decorator, _runs, _counts, _word) in enumerate(cases):
            probe = "ROMP_PROBE_CLASS_%02d" % i
            extra = extra.replace("{package}", "c%02d" % i)     # a case directory with an __init__.py is the package c<NN>
            texts[label] = (popper(probe, decorator or "@pytest.fixture(autouse=True)") + extra, probe)
            run.append((label, texts[label][0], helpers, probe) + (("%s%02d" % (packages[label], i),) if label in packages else ()))
        got = self._registration_cases_run(run)
        self.assertEqual({label: got[label][0] for label, *_ in cases},
                         {label: "None" if runs else "45678" for label, _e, _h, _d, runs, _c, _w in cases},
                         "THE PREMISE: `_f`'s pop ran before the second test in the control and the three cases pytest runs it "
                         "in, and never under the others")
        for label, _extra, _helpers, _decorator, runs, counts, word in cases:
            src, probe = texts[label]
            seen, registrations, where, hooks, live = got[label]
            self.assertEqual(sorted(spec for _a, spec in hooks if spec is not None), live,
                             "%s: the hooks _pytest_hook_impls reads are the hooks pytest registered from the conftest" % label)
            fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_f")
            why = _why_pytest_does_not_run(fn, registrations, os.path.join(where, "conftest.py")) or _why_a_hook_may_stop_it(hooks)
            self.assertEqual(why is None, runs, "THE MODULE ROAD, %s: pytest runs _f: %s; the reader says %s over %s"
                             % (label, runs, why or "it runs", registrations))
            text = _conftest_reasserted_names(src, where=where)
            self.assertEqual(probe in text.removals, counts, "THE TEXT ROAD, %s: counted %s, refusals %s: %s"
                             % (label, probe in text.removals, list(text.refused), src))
            if not counts:
                mine = [r for r in text.refused if r.startswith("_f (line %d)" % fn.lineno)]
                self.assertEqual(len(mine), 1, "%s: _f is refused, named: %s" % (label, list(text.refused)))
                self.assertIn(word, mine[0], "%s: the refusal names what the reader could not prove" % label)
        # THE PROVEN LIST, clause by clause, on the text road alone: each shape off the list is named, and each on it passes
        refused = (("a relative import", "from . import helper\n", "a relative import"),
                   ("a `from` import of the module's own package", "from tests import helper\n",
                    "a `from` import of the module's own package"),
                   ("an import of a submodule of the module's own package", "import tests.helper\n", "an import of tests.helper"),
                   ("a fixture of pytest's own imported", "from _pytest.monkeypatch import monkeypatch\n",
                    "a fixture of pytest's own"),
                   ("a star import of pytest's own", "from pytest import *\n", "a star import of pytest's own"),
                   ("a name of pytest's own the process never imported", "from _pytest.no_such_module import thing\n",
                    "is not an object of the pytest this process imported"),
                   ("a write through an attribute of pytest", "pytest.fixture = pytest.fixture\n", "a write through pytest.fixture"),
                   ("a write through a subscript of anything but os.environ", "import sys\nsys.modules['x'] = None\n",
                    "a write through sys.modules"),
                   ("a subscript read", "X = os.environ['HOME']\n", "a Subscript expression"),
                   ("a comprehension", "X = [n for n in ()]\n", "a ListComp expression"),
                   ("a with", "with open(os.devnull):\n    pass\n", "a With statement"),
                   ("a match", "match 1:\n    case 1:\n        pass\n", "a Match statement"),
                   ("a binding of __builtins__", "__builtins__ = {}\n", "a module-level binding of __builtins__"),
                   ("a module-level __getattr__", "def __getattr__(name):\n    return None\n",
                    "a module-level binding of __getattr__"),
                   ("a decorator that is not pytest's own", "def deco(f):\n    return f\n@deco\ndef _h():\n    pass\n",
                    "a decorator that is not pytest's own"),
                   ("a class keyword", "class _M(metaclass=type):\n    pass\n", "a class with a base or a keyword"),
                   ("a call in a def's default", "def _d(x=print()):\n    pass\n", "a call of print"),
                   ("a call in a class body", "class _C:\n    X = print()\n", "a call of print"),
                   ("an in-place operator on a name at import", "X = []\nX += [1]\n", "an in-place operator on X"),
                   ("an in-place operator on a name in a class body", "class _C:\n    Y = 1\n    Y -= 1\n",
                    "an in-place operator on Y"),
                   ("an in-place operator on a parameter in a def's body", "def _h(xs):\n    xs |= {1}\n",
                    "an in-place operator on xs"),
                   ("an in-place operator on a counter, a false refusal", "N = 0\nN += 1\n", "an in-place operator on N"))
        for what, text, word in refused:
            got_ = _unproven_statements(ast.parse("import os, pytest\n" + text))
            self.assertTrue(got_ and any(word in w for _l, w in got_), "%s is off the proven list, named %r: %s" % (what, word, got_))
        accepted = ("X = 1\nY = f'{X}'\nZ = (X, [X], {X}, {'k': X})\n", "X = os.devnull\nY = os.path.sep + 'x'\n",
                    "F = lambda a=1: a\nB = not (1 < 2) and 3 if True else 4\n(W := 5)\n",
                    "os.environ['ROMP_X'] = '1'\ndel os.environ['ROMP_X']\nos.environ['ROMP_Y'] += 'x'\n",
                    "from os import environ\nenviron['ROMP_X'] = '1'\n",
                    "for _v in ('a', 'b'):\n    pass\nif True:\n    pass\nwhile False:\n    pass\n"
                    "try:\n    pass\nexcept OSError as _e:\n    pass\nassert True, 'x'\n",
                    "__all__ = ['X']\nX: int = 1\nclass _C:\n    Y = 2\n",
                    "@pytest.fixture(scope='function', params=[1, 2])\ndef _p(request):\n    yield\n@pytest.mark.skipif(True, reason='x')\n"
                    "def test_x():\n    pass\n@pytest.hookimpl(trylast=True)\ndef pytest_configure(config):\n    pass\n",
                    "import tests as _t\nimport tests\nimport json\nfrom collections import abc\n"
                    "from _pytest._code.code import ReprFileLocation\n")
        for text in accepted:
            self.assertEqual(_unproven_statements(ast.parse("import os, pytest\n" + text)), [], "on the proven list: %s" % text)
        # THE IMPORT ROOTS, planted directly (the verifier's finding at round 2's thirty-first commit of fork PR #894: a
        # shadow check that read the first directory alone, and roots that named no parent, each left the module green):
        # a package's directory and each parent up to the first with no __init__.py, and an entry found in any of them
        root = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        outer = os.path.join(root, "outer")
        inner = os.path.join(outer, "inner")
        os.makedirs(inner)
        for name in (os.path.join(outer, "__init__.py"), os.path.join(inner, "__init__.py"), os.path.join(root, "sched.py")):
            with open(name, "w", encoding="utf-8"):
                pass
        self.assertEqual((_import_roots(inner), _import_roots(root)), (("outer.inner", [inner, outer, root]), ("", [root])),
                         "the package's directory, then each parent up to and including the first with no __init__.py; a "
                         "directory with none is no package and its own one root")
        self.assertEqual((_shadowed("sched", [inner, outer, root]), _shadowed("colorsys", [inner, outer, root])), (root, None),
                         "an entry of the name in the last of the directories shadows the standard library's; none, nothing")
        # _shadowed's two other entry forms (the verifier's finding at round 2's thirty-second commit of fork PR #894: a
        # match on `top.` alone, and a directory that cannot be listed read as holding nothing, each left the module
        # green): an entry that IS the name (a package's or a namespace's directory), and a path os.listdir refuses (a
        # regular file, a path that does not exist; neither depends on who runs the test, as a directory's mode would)
        os.mkdir(os.path.join(outer, "heapq"))
        unlistable = (os.path.join(root, "sched.py"), os.path.join(root, "no-such-directory"))
        self.assertEqual((_shadowed("heapq", [inner, outer, root]), [_shadowed("colorsys", [u, root]) for u in unlistable]),
                         (outer, list(unlistable)), "an entry that is the name itself shadows, and a directory that cannot "
                                                    "be listed is taken as one that may")
        # the first of the directories, and an entry's kind not read (the verifier's finding at round 2's thirty-fourth
        # commit of fork PR #894: a shadow check that read the directories last first left the module green): a regular
        # file named bisect in the first directory, which no import takes, and bisect.py in the last
        for name in (os.path.join(inner, "bisect"), os.path.join(root, "bisect.py")):
            with open(name, "w", encoding="utf-8"):
                pass
        self.assertEqual(_shadowed("bisect", [inner, outer, root]), inner,
                         "the first of the directories holding an entry of the name is named, whatever the entry's kind")
        real = ast.parse(open(os.path.join(HERE, "conftest.py"), encoding="utf-8").read())
        unproven = _unproven_statements(real)
        self.assertTrue(any("_TMP_ROOT = _tests.TMP_ROOT" in what for _l, what in unproven)
                        and any("_credpat = _load_credential_patterns()" in what for _l, what in unproven),
                        "the text road cannot prove tests/conftest.py (a value of the tests package, a def of its own called "
                        "at import), which is why the reader reads it on the module road:\n"
                        + "\n".join("line %d: %s" % u for u in unproven))

    def test_the_module_road_refuses_every_fixture_it_cannot_read_and_names_why(self):
        """The module road's own failure modes (_registration_refusals), each a refusal of every fixture named with its
        cause, never a count: tests.conftest cannot be imported, the module read is not tests/conftest.py, and its fixtures
        cannot be read the way pytest registers them (an installed pytest with no FixtureFunctionDefinition, say), and,
        since round 2's thirty-second commit of fork PR #894, its hook implementations cannot be read the way pytest
        takes them, or one of them is off _LISTED_HOOKS. Each is planted by replacing _real_conftest_module,
        _pytest_registrations or _pytest_hook_impls for the one call; unplanted, the road proves every function-scoped
        autouse fixture of tests/conftest.py. And one part of _pytest_registrations' rule planted directly (the
        reviewer's ruling of 2026-09-24 21:09Z, (3)): an attribute that raises when read is skipped, not raised."""
        from unittest import mock
        tree = ast.parse(open(os.path.join(HERE, "conftest.py"), encoding="utf-8").read())
        candidates = [fn for fn in tree.body
                      if isinstance(fn, ast.FunctionDef) and _is_autouse_fixture(fn) and _is_function_scoped_fixture(fn)]
        self.assertGreater(len(candidates), 5, "tests/conftest.py's function-scoped autouse fixtures")
        self.assertEqual(set(_registration_refusals(tree, candidates, True).values()), {None}, "unplanted, every one is proven")
        raising = type(sys)("_synthetic_conftest")
        raising.__dir__ = lambda: ["boom"]
        raising.__getattr__ = lambda name: 1 / 0
        self.assertEqual(_pytest_registrations(raising), [], "an attribute that raises when read is skipped, not raised")

        def planted_import():
            raise ImportError("planted")

        def planted_read(module):
            raise AttributeError("planted")
        elsewhere = type(sys)("tests.conftest")
        elsewhere.__file__ = os.path.join(os.sep, "elsewhere", "conftest.py")
        real_hooks = _pytest_hook_impls
        for what, planted, word in (
                ("an import that fails", {"_real_conftest_module": planted_import},
                 "importing tests.conftest failed (ImportError: planted)"),
                ("a module of another file", {"_real_conftest_module": lambda: elsewhere}, "not tests/conftest.py"),
                ("fixtures it cannot read", {"_pytest_registrations": planted_read},
                 "could not read the module's fixtures the way pytest registers them (AttributeError: planted)"),
                ("hooks it cannot read", {"_pytest_hook_impls": planted_read},
                 "could not read the module's hook implementations the way pytest takes them (AttributeError: planted)"),
                ("a hook off the list beside the conftest's own", {"_pytest_hook_impls": lambda module: list(real_hooks(module))
                                                                   + [("pytest_fixture_setup", "pytest_fixture_setup")]},
                 "it implements the hook pytest_fixture_setup")):
            with mock.patch.dict(globals(), planted):
                whys = _registration_refusals(tree, candidates, True)
            self.assertEqual(len(whys), len(candidates), what)
            for why in whys.values():
                self.assertIn(word, why or "", "%s refuses every fixture, naming why" % what)

    def test_a_hook_that_may_keep_pytest_from_running_a_fixture_refuses_it_on_both_roads(self):
        """THE HOOK CLAUSE (the verifier's finding at round 2's thirty-first commit of fork PR #894, a sixth case of the
        class this reader closed by construction: a hook of the conftest kept pytest from running `_f` while both roads
        counted its pop; the ruling's rule, that a new case is a refusal and never a silent count, extended to what pytest
        runs besides the registration). THE PREMISE, run: ONE child pytest, a directory per case, each conftest popping
        its probe name in `_f` (each hook reaching the tests of its own directory alone): `_f`'s pop ran in the control
        and beside a listed hook that does nothing, and never under a pytest_fixture_setup that answers for `_f`, a
        pytest_generate_tests that parametrizes `_f`, a pytest_collection_modifyitems that takes `_f` out of each test's
        fixtures, that hook under another name by specname= and bound to a lambda, and a listed pytest_configure that
        rebinds `_f`. At the thirty-first commit both roads counted each but the last (the module road refused that one,
        its registration read after the rebinding), the text road that one too. Now: the MODULE ROAD refuses every one
        (_why_a_hook_may_stop_it over the hooks _pytest_hook_impls reads, which equal the hooks pytest registered), and
        so does the TEXT ROAD, whose refusal names the hook, or what in the hook's body it cannot prove
        (_unproven_statements' hook clause and its reading of every def's body). THE MODULE ROAD'S RESIDUAL, planted as its witness (the reader's docstring
        names it; the text road refuses both): a session-scoped fixture of the conftest that registers a plugin whose
        pytest_runtest_setup takes `_f` out of each later test's fixtures, and a listed pytest_runtest_makereport that
        makes a failed setup's report pass, so the second test's body runs after `_f` raised before its pop; the module
        road counts each, and pytest never runs the pop before the second test. THE IN-PLACE CASES (the verifier's
        finding at round 2's thirty-second commit of fork PR #894, another case of the class): an in-place operator on a
        name bound to a test's list of fixtures (in a listed pytest_collectreport, and in an autouse fixture that sorts
        before `_f`), to pytest.fixture's keyword defaults at import, to config.option's __dict__ in a listed
        pytest_configure (pytest's setup plan turned on, run in a child pytest of its own since the option holds for the
        whole run) and to a report's __dict__ in a listed pytest_runtest_makereport (a failed setup made to pass);
        `_f`'s pop never ran under any of the five, the text road counted each at that commit and refuses each now by
        _unproven_statements' in-place rule, naming the operator, and the module road counts each but the defaults case
        (whose registration of `_g` under `_f` it reads), four more witnesses of its residual. THE CLAUSE, planted by
        text: each shape off it is named (a hook off the list with a body that proves, pytest_plugins, a hook name bound
        by an import, twice, in a block or through a global, a listed hook that returns or yields a value, a specname= that is not a
        literal, a hookimpl with a positional argument or carried twice, a listed name implementing another spec, and in
        a def's body a call, an import, an attribute write, a binding of a name the reader resolves as the module's, a
        lambda's call or parameter, an await, a walrus on such a name, and a call of a method of os.environ off
        _ENVIRON_METHODS, of a listed method on another object, or through os bound twice), and each on it passes (the five listed hooks, a
        wrapper that yields no value, a listed spec by specname=, a fixture body of os.environ's methods, a nested def,
        and a hookimpl on a def pytest takes no hook from). THE MODULE ROAD'S HALF, planted on module objects: a routine
        off the list, under its own name, by specname=, a lambda or a builtin, and pytest_plugins, each refused naming
        it; a listed hook, a non-routine and a routine whose name does not begin pytest_ pass, and a routine the module's
        __dir__ leaves out is read as pytest reads a plugin, through dir(), so not at all. THE REAL
        tests/conftest.py: its hooks are the listed five, by equality."""
        drop = ("        if '_f' in {i}.fixturenames and str({i}.path).startswith(os.path.dirname(os.path.realpath(__file__))):\n"
                "            {i}.fixturenames.remove('_f')\n")

        def popper(probe):
            return "import os, pytest\n\n\n@pytest.fixture(autouse=True)\ndef _f():\n    os.environ.pop(%r, None)\n    yield\n\n\n" % probe

        def failing(probe):
            return ("import os, pytest\n\n_ONCE = []\n\n\ndef _boom():\n    if os.environ.get(%r) == '45678' and not _ONCE:\n"
                    "        _ONCE.append(1)\n        raise RuntimeError('boom')\n\n\n"
                    "@pytest.fixture(autouse=True)\ndef _f():\n    _boom()\n    os.environ.pop(%r, None)\n    yield\n\n\n"
                    "@pytest.hookimpl(hookwrapper=True)\ndef pytest_runtest_makereport(item, call):\n    outcome = yield\n"
                    "    rep = outcome.get_result()\n    if rep.when == 'setup' and rep.failed:\n        rep.outcome = 'passed'\n"
                    % (probe, probe))
        # THE IN-PLACE CASES (the verifier's finding at round 2's thirty-second commit of fork PR #894), each spelled as
        # that finding's run spelled it: an in-place operator on a name bound to a test's list of fixtures (the hook
        # and the fixture leave the third test's alone, so it can report), to pytest.fixture's keyword defaults, or to a
        # report's __dict__, where the proven list took the statement as an assignment to a name
        in_place_collectreport = ("def pytest_collectreport(report):\n    for item in report.result:\n        try:\n"
                                  "            names = item.fixturenames\n        except AttributeError:\n            continue\n"
                                  "        if 'test_3' not in item.name:\n            names *= 0\n")
        in_place_fixture = ("@pytest.fixture(autouse=True)\ndef _a(request):\n    names = request.node.fixturenames\n"
                            "    if 'test_3' not in request.node.name:\n        names *= 0\n    yield\n")
        in_place_kwdefaults = ("_d = pytest.fixture.__kwdefaults__\n_d |= {'name': '_f'}\n\n\n"
                               "@pytest.fixture(autouse=True)\ndef _g():\n    yield\n\n\n_d |= {'name': None}\n")

        def in_place_makereport(probe):
            once = probe + "_ONCE"
            return ("import os, pytest\n\n\n@pytest.fixture(autouse=True)\ndef _f():\n"
                    "    assert (os.environ.get(%r) != '45678' or os.environ.get(%r) is not None\n"
                    "            or os.environ.setdefault(%r, '1') is None)\n"
                    "    os.environ.pop(%r, None)\n    yield\n\n\n"
                    "@pytest.hookimpl(hookwrapper=True)\ndef pytest_runtest_makereport(item, call):\n    outcome = yield\n"
                    "    d = outcome._result.__dict__\n"
                    "    if call.when == 'setup' and call.excinfo is not None:\n        d |= {'outcome': 'passed'}\n"
                    % (probe, once, once, probe))
        # (label, the conftest (a text, or a function of the probe name), pytest runs _f's pop, the module road counts it,
        # the text road counts it, a word the text road's refusal names)
        cases = (("control", popper, True, True, True, None),
                 ("a listed hook that does nothing", lambda p: popper(p) + "@pytest.hookimpl(trylast=True)\n"
                  "def pytest_configure(config):\n    pass\n", True, True, True, None),
                 ("pytest_fixture_setup", lambda p: popper(p) + "def pytest_fixture_setup(fixturedef, request):\n"
                  "    if fixturedef.argname == '_f':\n        fixturedef.cached_result = (0, fixturedef.cache_key(request), None)\n"
                  "        return 0\n", False, False, False, "a hook implementation of pytest_fixture_setup"),
                 ("pytest_generate_tests", lambda p: popper(p) + "def pytest_generate_tests(metafunc):\n"
                  "    if '_f' in metafunc.fixturenames:\n        metafunc.parametrize('_f', [0])\n", False, False, False,
                  "a hook implementation of pytest_generate_tests"),
                 ("pytest_collection_modifyitems", lambda p: popper(p) + "def pytest_collection_modifyitems(items):\n"
                  "    for item in items:\n" + drop.format(i="item"), False, False, False,
                  "a hook implementation of pytest_collection_modifyitems"),
                 ("a hook under another name by specname=", lambda p: popper(p) + "@pytest.hookimpl(specname="
                  "'pytest_collection_modifyitems')\ndef pytest_drop_f(items):\n    for item in items:\n" + drop.format(i="item"),
                  False, False, False, "a hook implementation of pytest_collection_modifyitems"),
                 ("a hook bound to a lambda", lambda p: popper(p) + "pytest_collection_modifyitems = lambda items: [\n"
                  "    i.fixturenames.remove('_f') for i in items\n    if '_f' in i.fixturenames and "
                  "str(i.path).startswith(os.path.dirname(os.path.realpath(__file__)))]\n", False, False, False,
                  "pytest_collection_modifyitems, a name pytest takes a hook implementation from"),
                 ("a listed hook that rebinds the fixture name", lambda p: popper(p) + "def pytest_configure(config):\n"
                  "    globals()['_f'] = None\n", False, False, False, "a write through globals()['_f']"),
                 ("RESIDUAL: a fixture that registers a plugin", lambda p: popper(p) + "class _Drop:\n"
                  "    def pytest_runtest_setup(self, item):\n" + textwrap.indent(drop.format(i="item"), "    ") + "\n\n"
                  "@pytest.fixture(autouse=True, scope='session')\ndef _a(request):\n"
                  "    request.config.pluginmanager.register(_Drop())\n    yield\n", False, True, False,
                  "a call of request.config.pluginmanager.register"),
                 ("RESIDUAL: a listed makereport that makes a failed setup pass", failing, False, True, False, "a call of _boom"),
                 ("IN-PLACE: an alias of the fixtures of a test emptied in a listed pytest_collectreport",
                  lambda p: popper(p) + in_place_collectreport, False, True, False, "an in-place operator on names"),
                 ("IN-PLACE: an alias of the fixtures of a test emptied in an autouse fixture that sorts before _f",
                  lambda p: popper(p) + in_place_fixture, False, True, False, "an in-place operator on names"),
                 ("IN-PLACE: the keyword defaults of pytest.fixture given the name _f at import",
                  lambda p: popper(p) + in_place_kwdefaults, False, False, False, "an in-place operator on _d"),
                 ("IN-PLACE: a listed makereport that makes a failed setup pass through the __dict__ of the report",
                  in_place_makereport, False, True, False, "an in-place operator on d"))
        # the setup-plan case runs in a child pytest of its own: pytest calls a conftest's pytest_configure when it
        # registers the conftest, and the option it turns on holds for every test of the run, every other case's included
        alone = (("IN-PLACE: the setup plan of pytest turned on through the __dict__ of config.option in a listed "
                  "pytest_configure",
                  lambda p: popper(p) + "def pytest_configure(config):\n    opts = config.option.__dict__\n"
                  "    opts |= {'setupplan': True}\n", False, True, False, "an in-place operator on opts"),)
        texts, got = {}, {}
        for group in (cases, alone):
            run = []
            for label, conftest, _runs, _module, _text, _word in group:
                probe = "ROMP_PROBE_HOOK_%02d" % len(texts)
                texts[label] = (conftest(probe), probe)
                run.append((label, texts[label][0], {}, probe))
            got.update(self._registration_cases_run(run))
        cases += alone
        self.assertEqual({label: got[label][0] for label, *_ in cases},
                         {label: "None" if runs else "45678" for label, _c, runs, _m, _t, _w in cases},
                         "THE PREMISE: `_f`'s pop ran in the control and beside the listed hook that does nothing, and never "
                         "under each other case")
        for label, _conftest, runs, module_counts, text_counts, word in cases:
            src, probe = texts[label]
            _seen, registrations, where, hooks, live = got[label]
            self.assertEqual(sorted(spec for _a, spec in hooks if spec is not None), live,
                             "%s: the hooks _pytest_hook_impls reads are the hooks pytest registered from the conftest" % label)
            fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_f")
            why = _why_pytest_does_not_run(fn, registrations, os.path.join(where, "conftest.py")) or _why_a_hook_may_stop_it(hooks)
            self.assertEqual(why is None, module_counts, "THE MODULE ROAD, %s: counts %s; the reader says %s over %s and %s"
                             % (label, module_counts, why or "it runs", registrations, hooks))
            text = _conftest_reasserted_names(src, where=where)
            self.assertEqual(probe in text.removals, text_counts, "THE TEXT ROAD, %s: counted %s, refusals %s: %s"
                             % (label, probe in text.removals, list(text.refused), src))
            if not text_counts:
                mine = [r for r in text.refused if r.startswith("_f (line %d)" % fn.lineno)]
                self.assertEqual(len(mine), 1, "%s: _f is refused, named: %s" % (label, list(text.refused)))
                self.assertIn(word, mine[0], "%s: the refusal names what the reader could not prove" % label)
        # THE CLAUSE, by text alone: each shape off it is named, and each on it passes
        refused = (("a hook off the list whose body proves", "def pytest_fixture_setup(fixturedef, request):\n    pass\n",
                    "a hook implementation of pytest_fixture_setup"),
                   ("pytest_plugins", "pytest_plugins = ['_h']\n", "pytest_plugins, which pytest reads to import plugins"),
                   ("a hook name bound by an import", "from os import path as pytest_configure\n",
                    "pytest_configure, a name pytest takes a hook implementation from"),
                   ("a listed hook bound twice", "def pytest_configure(config):\n    pass\ndef pytest_configure(config):\n    pass\n",
                    "bound at import 2 times"),
                   ("a listed hook in a block", "if True:\n    def pytest_configure(config):\n        pass\n", "and by 0 defs"),
                   ("a listed hook bound again through a global", "def pytest_configure(config):\n    pass\n"
                    "def _later():\n    global pytest_configure\n", "bound at import 2 times"),
                   ("a listed hook that returns a value", "def pytest_runtest_makereport(item, call):\n    return item\n",
                    "returns or yields a value"),
                   ("a listed hook that yields a value", "@pytest.hookimpl(hookwrapper=True)\n"
                    "def pytest_runtest_makereport(item, call):\n    yield 1\n", "returns or yields a value"),
                   ("a specname= that is not a literal", "N = 'pytest_configure'\n@pytest.hookimpl(specname=N)\n"
                    "def pytest_x(config):\n    pass\n", "specname= is not a string literal"),
                   ("a hookimpl with a positional argument", "@pytest.hookimpl(None)\ndef pytest_configure(config):\n    pass\n",
                    "a positional argument or unpacked keywords"),
                   ("a hookimpl carried twice", "@pytest.hookimpl(trylast=True)\n@pytest.hookimpl(tryfirst=True)\n"
                    "def pytest_configure(config):\n    pass\n", "carries pytest.hookimpl 2 times"),
                   ("a listed name implementing another spec", "@pytest.hookimpl(specname='pytest_fixture_setup')\n"
                    "def pytest_configure(fixturedef, request):\n    pass\n", "a hook implementation of pytest_fixture_setup"),
                   ("a call in a fixture's body", "@pytest.fixture\ndef _g():\n    print()\n    yield\n", "a call of print"),
                   ("an import in a def's body", "def _later():\n    import _h\n", "an import of _h"),
                   ("an attribute write in a listed hook's body", "def pytest_collectreport(report):\n    report.result = []\n",
                    "a write through report.result"),
                   ("a call in a listed hook's body", "def pytest_configure(config):\n    config.pluginmanager.register(object())\n",
                    "a call of config.pluginmanager.register"),
                   ("a parameter named like a name the reader resolves", "def pytest_configure(os):\n    pass\n",
                    "a binding of os in a def's or a class's own scope"),
                   ("that name bound in a fixture's body", "@pytest.fixture\ndef _g():\n    os = pytest\n    yield\n",
                    "a binding of os in a def's or a class's own scope"),
                   ("that name bound in a class body", "from os import environ\nclass _C:\n    environ = {}\n",
                    "a binding of environ in a def's or a class's own scope"),
                   ("a walrus binding that name", "X = (os := 1)\n", "a walrus binding os"),
                   ("a lambda whose parameter is that name", "F = lambda os: os\n", "a lambda whose parameter os"),
                   ("a call in a lambda's body", "F = lambda: print()\n", "a call of print"),
                   ("an await in a def's body", "async def _a():\n    await _b\n", "a Await expression"),
                   ("a method of os.environ off _ENVIRON_METHODS", "X = os.environ.copy()\n", "a call of os.environ.copy"),
                   ("a listed method of another object of the standard library", "import sys\nsys.modules.pop('x', None)\n",
                    "a call of sys.modules.pop"),
                   ("a listed method of os.environ through os bound twice", "os = pytest\nos.environ.pop('X', None)\n",
                    "a call of os.environ.pop"))
        for what, text, word in refused:
            got_ = _unproven_statements(ast.parse("import os, pytest\n" + text))
            self.assertTrue(got_ and any(word in w for _l, w in got_), "%s is off the list, named %r: %s" % (what, word, got_))
        accepted = ("def pytest_configure(config):\n    pass\ndef pytest_collectreport(report):\n    pass\n"
                    "def pytest_runtest_makereport(item, call):\n    pass\ndef pytest_sessionfinish(session, exitstatus):\n    pass\n"
                    "def pytest_unconfigure(config):\n    pass\n",
                    "@pytest.hookimpl(hookwrapper=True)\ndef pytest_runtest_makereport(item, call):\n    outcome = yield\n",
                    "@pytest.hookimpl(specname='pytest_configure')\ndef pytest_configure_again(config):\n    pass\n",
                    "@pytest.fixture(autouse=True)\ndef _g():\n    os.environ.pop('X', None)\n    os.environ.setdefault('Y', '1')\n"
                    "    if os.environ.get('Z'):\n        os.environ.update(W='1')\n    yield\n    return\n",
                    "def _outer():\n    def _inner():\n        yield 1\n    return lambda a=1: a + 1\n",
                    "@pytest.hookimpl(specname='pytest_fixture_setup')\ndef _not_a_hook(fixturedef, request):\n    pass\n")
        for text in accepted:
            self.assertEqual(_unproven_statements(ast.parse("import os, pytest\n" + text)), [], "on the list: %s" % text)
        # THE MODULE ROAD'S HALF, on module objects
        import pytest

        def module(**attrs):
            m = type(sys)("_synthetic_conftest")
            for k, v in attrs.items():
                setattr(m, k, v)
            return m

        def hook(config):
            return None

        def marked(spec):
            return pytest.hookimpl(specname=spec)(lambda *a: None)
        for what, m, word in (("a routine off the list", module(pytest_fixture_setup=hook), "it implements the hook pytest_fixture_setup"),
                              ("a routine off the list by specname=", module(pytest_drop_f=marked("pytest_collection_modifyitems")),
                               "it implements the hook pytest_collection_modifyitems (as pytest_drop_f)"),
                              ("a lambda off the list", module(pytest_generate_tests=lambda metafunc: None),
                               "it implements the hook pytest_generate_tests"),
                              ("a builtin off the list", module(pytest_collection_modifyitems=len),
                               "it implements the hook pytest_collection_modifyitems"),
                              ("pytest_plugins", module(pytest_plugins=[]), "it has pytest_plugins")):
            why = _why_a_hook_may_stop_it(_pytest_hook_impls(m))
            self.assertIn(word, why or "", "%s is refused, named: %s" % (what, why))
        passing = module(pytest_configure=hook, pytest_sessionfinish=hook, pytest_x=1, pytest_y=type("C", (), {}),
                         _not_a_hook=marked("pytest_fixture_setup"))
        self.assertEqual((_pytest_hook_impls(passing), _why_a_hook_may_stop_it(_pytest_hook_impls(passing))),
                         ([("pytest_configure", "pytest_configure"), ("pytest_sessionfinish", "pytest_sessionfinish")], None),
                         "listed hooks pass; a non-routine, and a routine whose name does not begin pytest_, are no hooks")
        hidden = module(pytest_configure=hook, pytest_fixture_setup=hook, __dir__=lambda: ["pytest_configure"])
        self.assertEqual(_pytest_hook_impls(hidden), [("pytest_configure", "pytest_configure")],
                         "pytest registers a plugin's hooks from dir() (a module's own __dir__ included), and so does the reader")
        real = _pytest_hook_impls(_real_conftest_module())
        self.assertEqual((sorted(spec for _a, spec in real), _why_a_hook_may_stop_it(real)), (sorted(_LISTED_HOOKS), None),
                         "THE REAL tests/conftest.py implements exactly the listed hooks, and has no pytest_plugins")

    def test_a_re_asserted_licence_holds_only_where_a_child_pytest_sees_the_fixtures_own_re_assert(self):
        """THE EXECUTION PROOF (the reviewer's ruling of 2026-09-24 21:09Z on round 2 of fork PR #894, (1): the static
        reader had no closed boundary, each fix closing one facet of the class, a fixture counted that pytest never ran,
        so the licence is proved by running the property). A `reasserted` licence holds only where
        _conftest_reasserts_proved grants the name: the filter (_reassert_sites) names the fixture def behind it, and a
        child pytest over the conftest (_reassert_proof, _REASSERT_PROBE) writes the name at each probe module's import,
        reads it and then sets it in each probe test, and sees, in the setup of each, that def's own code (its file, its
        name, its first line) make the counted write or pop, the body then reading something other than the probe's
        value. THE FACETS (_proof_facets), each run with the site counted as though the filter had counted it, so the
        proof's verdict is its own: every facet the reader was found counting while pytest never ran the pop (F2, F2b,
        F2c, F2e, N2b's three, the pytest hooks, the in-place operator on a bound mutable object, the module road's
        residuals, a module-scoped rebinding) is refused, and the control, a
        listed hook that does nothing, and the three cases pytest runs the pop in are licensed. THE RE-ASSERT ITSELF: the
        value right at each read, set by another def registered under the name, a helper the fixture calls, another
        file's def of the name at its first line, a def of another name compiled in the conftest's file at that line, or
        a later def of the name, is refused, each naming the code that did set it; so are the fixture setting a name
        counted as popped, the fixture's pop undone by a fixture that sorts after it, the fixture popping in the first
        test's setup and after every test but never in a later test's setup, and a read not reported (the probe's second
        tests taken out of the run). THE LICENCE READS THE PROOF: with a proof that refuses every name, each
        `reasserted` licence faults, the refusals named at the end of the list. THE FILTER IS REFUSE-ONLY: the
        fixture under a name another fixture sorting first takes, which the proof licenses, is refused by the filter (a
        false refusal on the safe side, the text road's), and a conftest in a package whose __init__.py makes
        pytest.fixture drop autouse, which the filter counts (the package's code runs before the module, outside what it
        reads), is refused by the proof. THE REAL tests/conftest.py, run as its copy: a copy with a
        pytest_collection_modifyitems that takes _dead_manager_port out of each test refuses the four names that fixture
        re-asserts and licenses the rest (the conftest pin reads the unplanted copy, where every name is licensed)."""
        verdicts = {}
        for group in _proof_facets():
            got, rc, out = _reassert_proof([(label, text, helpers, {probe: frozenset({("_f", line, "pop")})})
                                            for label, text, helpers, probe, line, _licensed in group])
            self.assertEqual(rc, 0, out[-3000:])
            for label, _text, _helpers, probe, _line, licensed in group:
                verdicts[label] = (got[label][probe], licensed)
        self.assertEqual(len(verdicts), 35, "the facets of _proof_facets, each run")
        self.assertEqual({label: why is None for label, (why, _l) in verdicts.items()},
                         {label: licensed for label, (_w, licensed) in verdicts.items()},
                         "THE PROOF licenses `_f`'s pop exactly where the child pytest ran it before both reads and the "
                         "body read the re-asserted value:\n" + "\n".join("%s: %s" % (label, why or "licensed")
                                                                         for label, (why, _l) in verdicts.items()))
        for label, word in (("itself: the value right, popped by another def registered under the fixture's name", "from _g "),
                            ("itself: the value right, popped by a helper the fixture calls", "from _clear "),
                            ("itself: the value right, popped by another file's def of the name at the fixture's first line",
                             "from _f (_pf_v.py, line 4)"),
                            ("itself: the value right, popped by a def of another name compiled in the conftest's file at that "
                             "line", "from _h (conftest.py, line 4)"),
                            ("itself: the fixture sets the name where the reader counted a pop", "set it from _f (conftest.py, line 4)"),
                            ("itself: the fixture's pop, then another fixture writes the probe's value back", "read the value the probe wrote"),
                            ("report: the probe's second tests taken out of the run", "reported no read")):
            self.assertIn(word, verdicts[label][0] or "", "%s: the refusal names what the run saw" % label)
        # the licence check reads the proof: with a proof that refuses every name, each `reasserted` licence faults
        from unittest import mock
        proofs = _held()["proofs"]
        saved = dict(proofs)
        proofs.clear()
        refusing = lambda cases, real=False: ({label: {n: "planted refusal" for n in sites} for label, _t, _h, sites in cases}, 0, "")
        try:
            with mock.patch.dict(globals(), {"_reassert_proof": refusing}):
                faults = _licence_faults(_all_licensed_once())
        finally:
            proofs.clear()
            proofs.update(saved)
        reasserted = sorted(n for n, lic in LICENSED_MODULE_LEVEL_WRITES.items() if lic.reasserted)
        self.assertEqual(sorted(f.split(" at ", 1)[0] for f in faults if "licensed only while tests/conftest.py re-asserts" in f),
                         reasserted, "every `reasserted` licence faults when the proof refuses its name: %s" % faults)
        self.assertIn("ROMP_MANAGER_PORT: planted refusal", faults[-1], "the proof's refusals are named at the end")
        facets = _proof_facets()[0]
        popper, probe = facets[0][1], facets[0][3]
        self.assertEqual(_conftest_reasserts_proved(popper), _Reasserted(frozenset(), frozenset({probe}), ()),
                         "the filter counts the control and the proof licenses it")
        first = next(t for label, t, _h, _p, _l, _x in facets if label.startswith("licensed: another fixture that sorts first"))
        got = _conftest_reasserts_proved(first)
        mine = [r for r in got.refused if r.startswith("_f (line 5)")]
        self.assertEqual((got.removals, len(mine)), (frozenset(), 1), "the filter refuses what the proof would license: %s"
                         % list(got.refused))
        self.assertIn("another call passes name='_f'", mine[0])
        not_autouse = ("import pytest\n_real = pytest.fixture\n\n\ndef _no_autouse(*args, **kwargs):\n    kwargs['autouse'] = False\n"
                       "    return _real(*args, **kwargs)\n\n\npytest.fixture = _no_autouse\n")
        self.assertEqual(_reassert_sites(popper)[0], {probe: frozenset({("_f", 4, "pop")})},
                         "the filter reads the module's text alone and counts the pop")
        got = _conftest_reasserts_proved(popper, helpers={"__init__.py": not_autouse})
        self.assertEqual((got.removals, len(got.refused)), (frozenset(), 1),
                         "a package whose __init__.py drops autouse from pytest.fixture: the proof refuses the pop the filter counts")
        self.assertIn("%s: the counted fixture's own code (_f at line 4, pop) did not set or pop it" % probe, got.refused[0])
        # the real conftest, as its copy, with a hook that keeps pytest from running one of its fixtures
        sites, refused = _reassert_sites()
        self.assertEqual(refused, ())
        hook = ("\n\ndef pytest_collection_modifyitems(items):\n    for item in items:\n"
                "        if '_dead_manager_port' in item.fixturenames:\n            item.fixturenames.remove('_dead_manager_port')\n")
        planted = open(os.path.join(HERE, "conftest.py"), encoding="utf-8").read() + hook
        got, rc, out = _reassert_proof([("planted", planted, {}, sites)], real=True)
        stopped = {n for n, s in sites.items() if any(f == "_dead_manager_port" for f, _l, _o in s)}
        self.assertEqual(stopped, {"ROMP_MANAGER_PORT", "ROMP_KERNEL_PORT", "ROMP_SERVE_PORT", "ROMP_POSTAL_PORT"})
        self.assertEqual({n for n, why in got["planted"].items() if why}, stopped,
                         "the copy of tests/conftest.py whose hook takes _dead_manager_port out of each test: the proof "
                         "refuses the four names it re-asserts and licenses the rest (rc %d): %s" % (rc, got["planted"]))

    def test_the_proof_refuses_a_road_keyed_on_each_fact_of_the_childs_context_and_grants_a_road_keyed_on_a_mark(self):
        """THE CHILD'S CONTEXT (the reviewer's ruling of 2026-09-24 23:17Z on round 2 of fork PR #894, (4), after the
        verifier's plants V1 to V5 in tests/conftest.py's pytest_collectreport were granted by a proof whose child ran
        three plain function tests of one module, serially, beside a copy of the conftest in a directory of its own).
        The child now reproduces the four finite facts of a real run the ruling names (_PROOF_READS, _proof_modes):
        each road of _proof_context_roads, `_f` popping a name and a listed pytest_collectreport taking `_f` out of
        each test one fact names, is refused, for the reads that share that fact and no others (V1, the conftest's
        directory and the test's, in every read; V3, the first module's reads or the later module's; V4, the function
        tests' or the TestCase's; V5, the run's with no worker or the -n 2 run's; the conjunction, the TestCase reads
        of the later module on a worker), and the road keyed on a mark, V2, is granted. V5's worker road and the conjunction are
        refused only where the proof makes the -n 2 run: where pytest-xdist is not installed (CI's pytest job) no run
        there has a worker, and the proof makes the one run and grants them, which this test reads from _proof_modes and
        runs for the worker road with pytest-xdist taken out of reach."""
        try:
            import xdist  # noqa: F401
            installed = True
        except ImportError:
            installed = False
        self.assertEqual(_proof_modes(), ("serial", "xdist") if installed else ("serial",),
                         "the proof makes the -n 2 run wherever pytest-xdist imports")
        popper = lambda p: "import os, pytest\n\n\n@pytest.fixture(autouse=True)\ndef _f():\n    os.environ.pop(%r, None)\n    yield\n" % p
        roads = [(label, "ROMP_PROBE_CONTEXT_%02d" % i, condition, mode) for i, (label, condition, mode) in enumerate(_proof_context_roads())]
        got, rc, out = _reassert_proof([(label, popper(p) + _CONTEXT_ROAD_HOOK.replace("__CONDITION__", condition), {},
                                         {p: frozenset({("_f", 4, "pop")})}) for label, p, condition, _m in roads])
        self.assertEqual(rc, 0, out[-3000:])
        modes = _proof_modes()
        self.assertEqual({label: got[label][p] is not None for label, p, _c, _m in roads},
                         {label: mode in modes for label, _p, _c, mode in roads},
                         "THE PROOF refuses each road keyed on a fact of the child's context, where it makes the run that has "
                         "the fact, and grants the road keyed on a mark (modes %s):\n%s"
                         % (modes, "\n".join("%s: %s" % (label, got[label][p] or "granted") for label, p, _c, _m in roads)))
        reads = [("%s, %s" % (where, _PROOF_MODES[mode]), key, mode) for mode in modes for key, where in _PROOF_READS]
        facts = {"V1: the conftest in a directory named tests": lambda key, mode: True,
                 "V1: a test in a directory named tests": lambda key, mode: True,
                 "V3: a test of the first module collected": lambda key, mode: key[0] == "a",
                 "V3: a test of a module collected after the first": lambda key, mode: key[0] == "b",
                 "V4: a function test": lambda key, mode: key[1] == "",
                 "V4: a unittest TestCase test": lambda key, mode: key[1] == "ProbeCase",
                 "V5: a test in a run with no xdist worker": lambda key, mode: mode == "serial",
                 "V5: a test on an xdist worker": lambda key, mode: mode == "xdist",
                 "V3, V4 and V5 at once: a TestCase test of a module collected after the first, on an xdist worker":
                     lambda key, mode: key[0] == "b" and key[1] == "ProbeCase" and mode == "xdist"}
        self.assertEqual(sorted(facts), sorted(label for label, _p, _c, mode in roads if mode is not None))
        for label, p, _c, mode in roads:
            if mode not in modes:
                continue
            why = got[label][p]
            listed = {ctx for ctx, _k, _m in reads if ctx in why or "in each of the %d reads" % len(reads) in why}
            self.assertEqual(listed, {ctx for ctx, key, m in reads if facts[label](key, m)},
                             "%s: refused for the reads that share its fact and no others: %s" % (label, why))
        # with pytest-xdist taken out of reach, as in CI's pytest job, the proof makes the run with no worker alone and
        # grants V5's worker road
        from unittest import mock
        find = importlib.util.find_spec
        with mock.patch.object(importlib.util, "find_spec", lambda name, *a: None if name == "xdist" else find(name, *a)):
            self.assertEqual(_proof_modes(), ("serial",))
            label, p, condition, _m = next(r for r in roads if r[0] == "V5: a test on an xdist worker")
            got, rc, out = _reassert_proof([(label, popper(p) + _CONTEXT_ROAD_HOOK.replace("__CONDITION__", condition), {},
                                             {p: frozenset({("_f", 4, "pop")})})])
        self.assertEqual((got[label][p], rc, out.count("[the run ")), (None, 0, 1),
                         "with no pytest-xdist the proof makes one run and grants the worker road: %s" % out[-3000:])

    def test_the_proofs_disclosed_limit_a_road_keyed_on_a_mark_is_granted_and_a_real_run_of_it_reads_the_module_level_write(self):
        """THE PROOF'S DISCLOSED LIMIT, WITNESSED (the reviewer's ruling of 2026-09-24 23:17Z on round 2 of fork PR #894,
        (4)): the proof grants a conftest hook condition its child's context does not reproduce, a mark, an environment
        variable, a host name, or another collection-time signal. The witness is V2: a copy of tests/conftest.py with a
        listed pytest_collectreport that takes _dead_manager_port out of each test with a mark. The proof grants every
        name the filter counts, the four that fixture re-asserts among them, and a real run of the same copy, beside a
        module that writes ROMP_KERNEL_PORT at its import, reads the module's '45678' in a marked test and the floor,
        '1', in the unmarked control after it."""
        sites, refused = _reassert_sites()
        self.assertEqual(refused, ())
        hook = ("\n\ndef pytest_collectreport(report):\n    for item in report.result:\n"
                "        if hasattr(item, 'fixturenames') and item.get_closest_marker('filterwarnings') is not None:\n"
                "            if '_dead_manager_port' in item.fixturenames:\n"
                "                item.fixturenames.remove('_dead_manager_port')\n")
        planted = open(os.path.join(HERE, "conftest.py"), encoding="utf-8").read() + hook
        got, _rc, out = _reassert_proof([("V2", planted, {}, sites)], real=True)
        self.assertEqual(got["V2"], dict.fromkeys(sites), "the proof grants every name, the mark's road unread: %s" % out[-3000:])
        self.assertTrue({"ROMP_MANAGER_PORT", "ROMP_KERNEL_PORT", "ROMP_SERVE_PORT", "ROMP_POSTAL_PORT"} <= set(sites))
        root = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        tests_dir = os.path.join(root, "tests")
        os.mkdir(tests_dir)
        with open(os.path.join(tests_dir, "conftest.py"), "w", encoding="utf-8") as f:
            f.write(planted)
        shutil.copy(os.path.join(HERE, "credential_patterns.py"), os.path.join(tests_dir, "credential_patterns.py"))
        with open(os.path.join(tests_dir, "test_witness.py"), "w", encoding="utf-8") as f:
            f.write("import json, os, pytest\n\nos.environ['ROMP_KERNEL_PORT'] = '45678'\n\n\n"
                    "def _record(key):\n    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), key + '.json'), 'w') as f:\n"
                    "        json.dump(os.environ.get('ROMP_KERNEL_PORT'), f)\n\n\n"
                    "@pytest.mark.filterwarnings('default')\ndef test_1_marked():\n    _record('marked')\n\n\n"
                    "def test_2_control():\n    _record('control')\n")
        child = {k: v for k, v in os.environ.items() if k not in ("PYTEST_CURRENT_TEST", "ROMP_KERNEL_PORT")}
        child["PYTHONPATH"] = os.pathsep.join(p for p in (os.path.dirname(HERE), child.get("PYTHONPATH")) if p)
        child["TMPDIR"] = root
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", root, tests_dir],
                           cwd=root, env=child, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
        reads = {}
        for key in ("marked", "control"):
            try:
                with open(os.path.join(tests_dir, key + ".json"), encoding="utf-8") as f:
                    reads[key] = json.load(f)
            except OSError:
                reads[key] = "no read"
        self.assertEqual(reads, {"marked": "45678", "control": "1"},
                         "THE WITNESS RUN: the marked test reads the module-level write the proof granted, the control the floor "
                         "(rc %d): %s" % (r.returncode, (r.stdout + r.stderr)[-3000:]))

    def test_a_fixture_that_is_not_autouse_writes_for_the_tests_after_it(self):
        """The verifier's finding at round 2's seventeenth commit of fork PR #894: the wide read of conftest's fixture writes
        (_conftest_fixture_env_writes, the ROMP_POSTAL_PORT pin's "not among the writes" half) left a fixture that is not
        autouse unread, on the reason that it names its value only to the tests that request it by name, which is false:
        the write goes to the process environment and holds for every later test. THE PREMISE, run: a child pytest whose
        conftest has a fixture, not autouse, that writes a probe name; the first test requests it, and the second, which
        does not, reads the value. The wide read now reads such a fixture (at the seventeenth commit it read neither
        plant): the write of the probe name in it, under the bare decorator and under the called one, is among the wide
        writes, and the narrow read, which counts function-scoped autouse fixtures alone, still does not count it. And a
        POP of the probe name in such a fixture is among the wide names (_conftest_fixture_env_names, whose removals half
        reads every fixture, autouse or not; the verifier's finding at the eighteenth commit: no plant reached that half
        from a fixture that is not autouse, and a reader of autouse fixtures' pops alone stayed green), and not among the
        writes."""
        probe = "ROMP_PROBE_NOT_AUTOUSE"
        module = ("import os\n\n\ndef test_1_requests_it(_n):\n    pass\n\n\n"
                  "def test_2_does_not():\n    print('SEEN=%%s' %% os.environ.get(%r))\n" % (probe,))
        for decorator in ("@pytest.fixture", "@pytest.fixture(scope='function')"):
            conftest_src = "import os, pytest\n\n\n%s\ndef _n():\n    os.environ[%r] = '45678'\n    yield\n" % (decorator, probe)
            self.assertIn("SEEN=45678", self._synthetic_conftest_run(conftest_src, module),
                          "%s: the write outlives the test that requested the fixture" % decorator)
            got = _conftest_reasserted_names(conftest_src)
            self.assertEqual((probe in _conftest_fixture_env_writes(conftest_src), probe in _conftest_fixture_env_names(conftest_src),
                              probe in got.writes | got.removals), (True, True, False),
                             "%s: among the wide writes and names, not a re-assert: %s" % (decorator, conftest_src))
            popper = "import os, pytest\n\n\n%s\ndef _n():\n    os.environ.pop(%r, None)\n    yield\n" % (decorator, probe)
            got = _conftest_reasserted_names(popper)
            self.assertEqual((probe in _conftest_fixture_env_names(popper), probe in _conftest_fixture_env_writes(popper),
                              probe in got.writes | got.removals), (True, False, False),
                             "%s: a pop in it is among the wide names, the removals half, and is no write and no re-assert: %s"
                             % (decorator, popper))

    def test_every_licence_carries_a_checkable_condition_and_a_temporary_one_is_dated(self):
        """The licensed set is held to the reviewer's shape by _licence_table_faults (the fixup of 2026-09-22: the table
        stored since and until and nothing read them, and the two preamble licences waited on the class item undated):
        every licence has a per-write condition (a value, a value predicate or conftest's re-assert), every licence that
        waits on an item is dated and names the item with its filing date, and a date is a date. The four temporary
        licences are dated 2026-09-22 and wait on fork PR #871's class item, filed 2026-09-21 in the small-asks notes.
        Run over a synthetic table so it is known to be able to fail, one fault per defect, in name order."""
        self.assertEqual(_licence_table_faults(LICENSED_MODULE_LEVEL_WRITES), [])
        for name in ("XDG_STATE_HOME", "ROMP_STATE_DIR", "ROMP_SERVE_TOKEN", "ROMP_KERNEL_NO_OPEN"):
            lic = LICENSED_MODULE_LEVEL_WRITES[name]
            self.assertEqual((lic.since, lic.until), ("2026-09-22", CLASS_ITEM_871), name)
        for word in ("2026-09-21", "small-asks", "fork PR #871"):
            self.assertIn(word, CLASS_ITEM_871, "the item is named with where and when it was filed")
        for name, lic in LICENSED_MODULE_LEVEL_WRITES.items():
            self.assertTrue(lic.value is not None or lic.value_ok is not None or lic.reasserted, "%s has a per-write condition" % name)
        faults = _licence_table_faults({
            "ROMP_A": _Licence("waits on an item, undated", until="the class item filed 2026-09-21 in the small-asks notes"),
            "ROMP_B": _Licence("no condition at all"),
            "ROMP_C": _Licence("a date that is not one", value="1", since="22 Sept 2026"),
            "ROMP_D": _Licence("waits on nothing filed", value="1", since="2026-09-22", until="some later cleanup"),
            "ROMP_E": _Licence("the shape asked for", value_ok=lambda v: True, since="2026-09-22", until="an item filed 2026-09-21")})
        self.assertEqual(faults, [
            "ROMP_A: the licence has no per-write condition (a value, a value predicate or conftest's re-assert)",
            "ROMP_A: the licence waits on an item (until) and has no since date: date it",
            "ROMP_B: the licence has no per-write condition (a value, a value predicate or conftest's re-assert)",
            "ROMP_C: since='22 Sept 2026' is not an ISO date",
            "ROMP_D: until names no filed item (no filing date in it)"])

    def test_the_committed_writer_sets_fault_a_new_writer_a_migrated_one_a_swap_and_a_floor_only_change(self):
        """The committed writer sets (the reviewer's ruling of round 1 on fork PR #894: a date bounds no writer, so the two
        dated names whose population nothing mandates, ROMP_SERVE_TOKEN and ROMP_KERNEL_NO_OPEN, have their writer
        modules committed and compared as SETS, and so do the floor-only names), run over synthetic records so the check
        is known to be able to fail: a new writer of each name faults naming its module, its line and the remedy (omit the
        write or move it to the conftest floor; not setUp, since a module that loads the kernel at import needs the
        value before the load); a migrated writer faults until its line is removed; a swap, one writer gone and one new,
        faults on both although the count is unchanged; a floor module's write of either name is not a writer here (the
        floor is licensed wholesale); a floor-only name added, dropped or moved between the two floor modules faults;
        a leak name the floor writes (fork PR #875's client-only "1" in tests/conftest.py) is no floor-only name, since
        _leak_writers holds the leak names; and the committed files read back as the census derived them (the census pin
        compares them with the real tree)."""
        def rec(module, line=2, value="'1'"):
            return _Record(module, line, "assignment", value, False, value, "")
        committed = {"ROMP_SERVE_TOKEN": {"test_a.py", "test_b.py"}, "ROMP_KERNEL_NO_OPEN": {"test_a.py"}}
        floor = {"ROMP_FLOOR_X": {"conftest.py"}, "ROMP_FLOOR_Y": {"__init__.py", "conftest.py"}}
        clean = {"ROMP_SERVE_TOKEN": [rec("test_a.py"), rec("test_b.py")], "ROMP_KERNEL_NO_OPEN": [rec("test_a.py")],
                 "ROMP_FLOOR_X": [rec("conftest.py")], "ROMP_FLOOR_Y": [rec("conftest.py"), rec("__init__.py")]}
        self.assertEqual(_writer_set_faults(clean, committed, floor), [])
        where = os.path.join("tests", "fixtures", "module-level-env-writers")
        for name in ("ROMP_SERVE_TOKEN", "ROMP_KERNEL_NO_OPEN"):
            planted = dict(clean, **{name: clean[name] + [rec("test_new_writer.py", 7)]})
            self.assertEqual(_writer_set_faults(planted, committed, floor), [
                "%s is written at module level by test_new_writer.py:7, a module outside the committed writer set (%s): omit the "
                "write, or move it to the conftest floor (tests/conftest.py); not setUp, since a module that loads the kernel at "
                "import needs the value before the load. A module renamed from one in the file renames its line there"
                % (name, os.path.join(where, name + ".txt"))])
        migrated = dict(clean, ROMP_SERVE_TOKEN=[rec("test_a.py")])
        self.assertEqual(_writer_set_faults(migrated, committed, floor), [
            "ROMP_SERVE_TOKEN: test_b.py is in the committed writer set (%s) and no longer writes it at module level: remove "
            "its line there" % os.path.join(where, "ROMP_SERVE_TOKEN.txt")])
        swapped = dict(clean, ROMP_SERVE_TOKEN=[rec("test_a.py"), rec("test_c.py", 4)])
        faults = _writer_set_faults(swapped, committed, floor)
        self.assertEqual(len(swapped["ROMP_SERVE_TOKEN"]), len(committed["ROMP_SERVE_TOKEN"]), "the count is unchanged")
        self.assertEqual([f.split(",")[0].split(": ")[0] for f in faults],
                         ["ROMP_SERVE_TOKEN is written at module level by test_c.py:4", "ROMP_SERVE_TOKEN"], faults)
        self.assertIn("test_b.py is in the committed writer set", faults[1])
        by_floor = dict(clean, ROMP_SERVE_TOKEN=clean["ROMP_SERVE_TOKEN"] + [rec("conftest.py"), rec("__init__.py")])
        self.assertEqual(_writer_set_faults(by_floor, committed, floor), [], "a floor module's write is the floor's, licensed wholesale")
        for what, records, want in (
                ("a floor name added", dict(clean, ROMP_FLOOR_Z=[rec("conftest.py")]), ("ROMP_FLOOR_Z", ["conftest.py"], [])),
                ("a floor name dropped", {k: v for k, v in clean.items() if k != "ROMP_FLOOR_X"}, ("ROMP_FLOOR_X", [], ["conftest.py"])),
                ("a floor name moved", dict(clean, ROMP_FLOOR_X=[rec("__init__.py")]), ("ROMP_FLOOR_X", ["__init__.py"], ["conftest.py"])),
                ("a floor name a test module now writes too", dict(clean, ROMP_FLOOR_X=[rec("conftest.py"), rec("test_a.py")]),
                 ("ROMP_FLOOR_X", [], ["conftest.py"]))):
            name, have, committed_modules = want
            self.assertEqual(_writer_set_faults(records, committed, floor), [
                "%s: the floor modules that alone write it at module level are %s, and the committed floor-only set (%s) says "
                "%s: a floor module added or dropped the write, or a test module now writes it too; the file lists each "
                "floor-only name once per writer module (`NAME module`)" % (name, have, os.path.join(where, "floor-only.txt"),
                                                                          committed_modules)], what)
        leak = dict(clean, ROMP_POSTAL_CLIENT_ONLY=[rec("conftest.py")])
        self.assertEqual(_writer_set_faults(leak, committed, floor), [], "a leak name is _leak_writers's, not a floor-only name")
        self.assertEqual(sorted(WRITER_SET_FILES), ["ROMP_KERNEL_NO_OPEN", "ROMP_SERVE_TOKEN"])
        real = _committed_writer_sets()
        self.assertTrue(all(real[name] for name in WRITER_SET_FILES), "each committed set is read, not empty")
        self.assertFalse(set().union(*real.values()) & set(FLOOR_MODULES), "no floor module is in a committed writer set")
        self.assertFalse(set(_committed_floor_only()) & set(LEAK_NAMES), "no leak name is in the committed floor-only set")

    def test_the_census_counts_by_name_and_shape_and_the_table_reads_back(self):
        """module_level_env_census over a synthetic tree: one module, eight shapes (the dunder spelling among them since the
        third commit of 2026-09-22, the augmented write and the target since round 2 of fork PR #894), three names; the
        nested write is counted as such; the table names the parsed-module count. The per-name, per-shape counts over the
        real tree are the by-product fork PR #871's docstring recorded from a grep, re-derived by ast here and pasted at
        the head in the PR from --census; they are NOT pinned by equality, since they move with every new module (what
        is compared is listed in module_level_env_census's docstring). Since the reviewer's ruling of round 1 on fork PR
        #894: this one-path census is a derivation of its own (the holder's key is the path tuple), read once by the
        census and again by the table (built once in the module's run, the file walked once and parsed once; the ruling of
        2026-09-24 re-aimed these from parse_cache's counters to the module's own counts); a second tree of a test module
        and a helper prints each name's total line and the split between test_*.py files and the others, the figures fork
        PR #871's by-product counts are compared with; the parsed count is the files parsed, so a census handed a file
        that does not parse fails naming it."""
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        src = ("import os\nos.environ['A'] = '1'\nos.environ.setdefault('A', '2')\nos.environ.update({'B': '3'})\n"
               "os.environ |= {'B': '4'}\nos.putenv('B', '5')\nif True:\n    os.environ['A'] = '6'\n"
               "os.environ.__setitem__('B', '9')\n"                  # the dunder spelling, its own shape
               "def f():\n    os.environ['C'] = 'never counted'\n"
               "class K:\n    os.environ['A'] = '7'\n"                 # a class body runs at import: counted, nested
               "def g():\n    os.environ['D'] = '8'\ng()\n"             # a def called at import: counted at the call, via set
               "os.environ['A'] += 'z'\nfor os.environ['B'] in ['w']:\n    pass\n")    # round 2 of fork PR #894: augmented, target
        path = os.path.join(d, "test_planted.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        n, counts, records = module_level_env_census([path])
        self.assertEqual(n, 1)
        self.assertEqual(counts, {"A": {"assignment": 3, "setdefault": 1, "augmented": 1},
                                  "B": {"update": 1, "|=": 1, "putenv": 1, "__setitem__": 1, "target": 1}, "D": {"assignment": 1}})
        self.assertEqual([r.nested for r in records["A"]], [False, False, True, True, False])
        self.assertEqual([(r.shape, r.value, r.line) for r in records["A"] + records["B"] if r.shape in ("augmented", "target")],
                         [("augmented", "", 17), ("target", "", 18)], "no value is read for either: the right side of += is a suffix")
        self.assertEqual(records["A"][2].value, "'6'")
        self.assertEqual(records["A"][3].value, "'7'")
        rel = os.path.relpath(path, HERE)          # the census labels a module relative to tests/, a synthetic one included
        self.assertEqual((records["D"][0].line, records["D"][0].via), (16, "g() at %s:14, the write at line 15" % rel))
        table = _census_table([path])
        row = "%-34s %-11s %6d %8d %7d %8d %8d %8d %8d %8d"
        lines = table.splitlines()
        self.assertEqual(lines[0], "modules: 1 parsed (.py files under tests/, recursively; fixtures/ and the helpers beside the "
                                   "test modules included): 1 test_*.py, 0 other")
        for want in (row % ("A", "(all)", 5, 1, 2, 0, 5, 1, 0, 0), row % ("A", "assignment", 3, 1, 2, 0, 3, 1, 0, 0),
                     row % ("D", "assignment", 1, 1, 0, 1, 1, 1, 0, 0), row % ("A", "augmented", 1, 1, 0, 0, 1, 1, 0, 0),
                     row % ("B", "target", 1, 1, 0, 0, 1, 1, 0, 0)):
            self.assertIn(want, lines)
        self.assertEqual((_CENSUS_BUILDS[(path,)], _census_derivation([path])[3], _OWN_PARSES[os.path.realpath(path)]),
                         (1, {rel: 1}, 1), "the census and the table read one held derivation of this path tuple, the file "
                         "walked once in it and parsed once in the module's run")
        # the split and the total line: a test module and a helper, one name each writes, one only the helper writes
        with open(os.path.join(d, "test_split.py"), "w", encoding="utf-8") as f:
            f.write("import os\nos.environ['S'] = '1'\nos.environ.setdefault('S', '2')\n")
        with open(os.path.join(d, "split_helper.py"), "w", encoding="utf-8") as f:
            f.write("import os\nos.environ.setdefault('S', '3')\nos.environ['H'] = '4'\n")
        split = [os.path.join(d, "split_helper.py"), os.path.join(d, "test_split.py")]
        lines = _census_table(split).splitlines()
        self.assertTrue(lines[0].startswith("modules: 2 parsed ") and lines[0].endswith(": 1 test_*.py, 1 other"), lines[0])
        for want in (row % ("S", "(all)", 3, 2, 0, 0, 2, 1, 1, 1), row % ("S", "assignment", 1, 1, 0, 0, 1, 1, 0, 0),
                     row % ("S", "setdefault", 2, 2, 0, 0, 1, 1, 1, 1), row % ("H", "(all)", 1, 1, 0, 0, 0, 0, 1, 1)):
            self.assertIn(want, lines)
        # a file that does not parse fails the census naming it
        bad = os.path.join(d, "test_unparsable.py")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("import os\nos.environ['S'] = (\n")
        with self.assertRaises(AssertionError) as caught:
            module_level_env_census([path, bad])
        self.assertIn("the census could not parse %s (SyntaxError" % os.path.relpath(bad, HERE), str(caught.exception))

    def test_the_scan_reads_every_write_shape_ignores_a_def_and_is_loud_on_a_key_it_cannot_read(self):
        """The scan the repo-wide pin rests on is known to see a planted write in every shape, bare and in an if body, and
        to ignore one inside a def; the one module-level update in the tree today reads its mapping through a name bound
        to a dict literal (tests/test_update_banner_confirm_served.py's DEAD_PORTS) and the scan reads the keys AND the
        values through the name; a `for` over string literals binds its name to each in turn (conftest's service-env
        fixture writes that way) and the literals are the keys; a write the scan cannot read is loud, with the file and
        the line, never a clean pass (review round 2, 2026-09-18; the loop shape 2026-09-22). Since the third commit of
        2026-09-22 the dunder spellings (__setitem__ and __ior__, on the mapping or unbound with the mapping first) and
        os.environb with a bytes key are read, a computed key in them is loud, a dotted `import tests.helper` and a star
        import resolve a call, and `saved.update(os.environ, ...)` is a write to `saved`, not read as one to the
        environment. Since round 2 of fork PR #894 (the reviewer's ruling of round 1) an augmented write and a key bound as
        a for, comprehension or with target are read in every form (the exact records in
        test_an_augmented_write_and_a_key_bound_as_a_target_are_read_with_no_value), and a dict or loop name misread
        through its first binding at the round-1 head is loud (the rule in
        test_a_tracked_dict_is_read_only_through_the_allowed_reads_and_any_other_reference_is_loud and
        test_a_name_is_read_through_its_first_binding_alone_and_a_later_binding_or_a_parameter_makes_it_loud). Since the
        verifier's findings on round 2: `environ` after `from os import *` is the mapping (os.__all__ carries it; missed
        silently at round 2's eleventh commit), and a bare annotation of a key (`os.environ[K]: str`), which evaluates the
        mapping and the key and sets nothing, is no write (recorded as a write of shape "target" at that commit)."""
        for shape in ('os.environ["ROMP_POSTAL_PEERS"] = "0"',
                      'if True:\n    os.environ["ROMP_POSTAL_PEERS"] = "0"',
                      'os.environ.setdefault("ROMP_POSTAL_PEERS", "0")',
                      'os.environ.update({"ROMP_POSTAL_PEERS": "0"})',
                      'os.environ.update(ROMP_POSTAL_PEERS="0")',
                      'OFF = {"ROMP_POSTAL_PEERS": "0"}\nos.environ.update(OFF)',
                      'try:\n    OFF = dict(ROMP_POSTAL_PEERS="0")\nfinally:\n    os.environ.update(OFF)',
                      'os.environ |= {"ROMP_POSTAL_PEERS": "0"}',
                      'from os import environ\nenviron["ROMP_POSTAL_PEERS"] = "0"',
                      'import os as _o\n_o.environ["ROMP_POSTAL_PEERS"] = "0"',
                      'env = os.environ\nenv["ROMP_POSTAL_PEERS"] = "0"',
                      'env = os.environ\nenv.update(ROMP_POSTAL_PEERS="0")',
                      'os.putenv("ROMP_POSTAL_PEERS", "0")',
                      'for v in ("ROMP_POSTAL_PEERS", "ROMP_X"):\n    os.environ[v] = "0"',
                      # the fixup of 2026-09-22: everything that executes at import
                      'class _Planted:\n    os.environ["ROMP_POSTAL_PEERS"] = "0"',
                      'class _Planted:\n    if True:\n        os.environ["ROMP_POSTAL_PEERS"] = "0"',
                      'class _Planted:\n    for v in ("ROMP_POSTAL_PEERS",):\n        os.environ[v] = "0"',
                      'if os.environ.setdefault("ROMP_POSTAL_PEERS", "0"):\n    pass',
                      'with open(os.environ.setdefault("ROMP_POSTAL_PEERS", "0")):\n    pass',
                      'def _f(x=os.environ.setdefault("ROMP_POSTAL_PEERS", "0")):\n    pass',
                      'def _floor():\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n_floor()',
                      'def _floor():\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\ndef _outer():\n    _floor()\n_outer()',
                      'def _arm(fn):\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n    return fn\n@_arm\ndef _decorated():\n    pass',
                      'def _arm(v):\n    os.environ["ROMP_POSTAL_PEERS"] = v\n    return lambda fn: fn\n@_arm("0")\ndef _decorated():\n    pass',
                      'class _Seam:\n    def __init__(self):\n        os.environ["ROMP_POSTAL_PEERS"] = "0"\n_Seam()',
                      'class _Base:\n    def __init__(self):\n        os.environ["ROMP_POSTAL_PEERS"] = "0"\nclass _Seam(_Base):\n    pass\n_Seam()',
                      'class _Seam:\n    @classmethod\n    def arm(cls):\n        os.environ["ROMP_POSTAL_PEERS"] = "0"\n_Seam.arm()',
                      # the third commit of 2026-09-22: the dunder spellings and the bytes mapping
                      'os.environ.__setitem__("ROMP_POSTAL_PEERS", "0")',
                      'dict.__setitem__(os.environ, "ROMP_POSTAL_PEERS", "0")',
                      'os.environ.__ior__({"ROMP_POSTAL_PEERS": "0"})',
                      'dict.__ior__(os.environ, {"ROMP_POSTAL_PEERS": "0"})',
                      'env = os.environ\nenv.__setitem__("ROMP_POSTAL_PEERS", "0")',
                      'os.environb[b"ROMP_POSTAL_PEERS"] = b"0"',
                      'os.environb.setdefault(b"ROMP_POSTAL_PEERS", b"0")',
                      'os.environb.update({b"ROMP_POSTAL_PEERS": b"0"})',
                      'from os import environb\nenvironb[b"ROMP_POSTAL_PEERS"] = b"0"',
                      'class _Planted:\n    os.environb.__setitem__(b"ROMP_POSTAL_PEERS", b"0")',
                      # round 2 of fork PR #894 (the reviewer's ruling of round 1): an augmented write and a key bound as
                      # a for, comprehension or with target, in the direct, alias, bytes, class-body and helper forms
                      'os.environ["ROMP_POSTAL_PEERS"] += "0"',
                      'env = os.environ\nenv["ROMP_POSTAL_PEERS"] += "0"',
                      'os.environb[b"ROMP_POSTAL_PEERS"] += b"0"',
                      'class _Planted:\n    os.environ["ROMP_POSTAL_PEERS"] += "0"',
                      'def _floor():\n    os.environ["ROMP_POSTAL_PEERS"] += "0"\n_floor()',
                      'for os.environ["ROMP_POSTAL_PEERS"] in ["0"]:\n    pass',
                      '[None for os.environ["ROMP_POSTAL_PEERS"] in ["0"]]',
                      'import contextlib\nwith contextlib.nullcontext("0") as os.environ["ROMP_POSTAL_PEERS"]:\n    pass',
                      'env = os.environ\nfor env["ROMP_POSTAL_PEERS"] in ["0"]:\n    pass',
                      'for os.environb[b"ROMP_POSTAL_PEERS"] in [b"0"]:\n    pass',
                      'class _Planted:\n    for os.environ["ROMP_POSTAL_PEERS"] in ["0"]:\n        pass',
                      'def _floor():\n    for os.environ["ROMP_POSTAL_PEERS"] in ["0"]:\n        pass\n_floor()',
                      # the verifier's findings on round 2 of fork PR #894: the name a star import of os binds
                      'from os import *\nenviron["ROMP_POSTAL_PEERS"] = "0"',
                      'from os import *\nenvironb.update({b"ROMP_POSTAL_PEERS": b"0"})'):
            self.assertIn("ROMP_POSTAL_PEERS", _module_level_env_writes(ast.parse("import os\n" + shape + "\n"), "planted.py"), shape)
        dunder = _module_level_env_write_records(ast.parse('import os\nos.environ.__setitem__("ROMP_POSTAL_PEERS", "0")\nos.environ.__ior__({"ROMP_X": "1"})\n'), "planted.py")
        self.assertEqual([(w.key, w.shape, ast.unparse(w.value)) for w, _n in dunder], [("ROMP_POSTAL_PEERS", "__setitem__", "'0'"), ("ROMP_X", "__ior__", "'1'")],
                         "the dunder spellings are their own shapes, with the value read")
        looped = _module_level_env_writes(ast.parse('import os\nfor v in ("ROMP_POSTAL_PEERS", "ROMP_X"):\n    os.environ[v] = "0"\n'), "planted.py")
        self.assertEqual(looped, {"ROMP_POSTAL_PEERS", "ROMP_X"}, "each literal the loop binds is a key")
        for shape in ('def setUp(self):\n    os.environ["ROMP_POSTAL_PEERS"] = "0"',                                  # a def never called at import
                      'class _Seam:\n    def setUp(self):\n        os.environ["ROMP_POSTAL_PEERS"] = "0"',            # a method never called at import
                      'class _Seam:\n    def arm(self):\n        os.environ["ROMP_POSTAL_PEERS"] = "0"\n_Seam().arm()',   # a method on an instance: outside the scan, named
                      'saved = {}\nsaved.update(os.environ, ROMP_POSTAL_PEERS="0")',                                 # a write to `saved`; the environment is read
                      'saved = {}\nsaved.setdefault(os.environ, "0")',                                            # not the environment's setdefault
                      'os.environ["ROMP_POSTAL_PEERS"]: str',                                                      # a bare annotation sets nothing
                      'class _Planted:\n    os.environ["ROMP_POSTAL_PEERS"]: str',
                      'def _f():\n    os.environ["ROMP_POSTAL_PEERS"]: str\n_f()'):
            self.assertNotIn("ROMP_POSTAL_PEERS", _module_level_env_writes(ast.parse("import os\n" + shape + "\n"), "planted.py"), shape)
        # through a helper under the root: imported by name, as a module, aliased, with the package prefix, by its dotted
        # name and by a star import (the last two since the third commit of 2026-09-22: both passed the resolver
        # silently); the record names the chain; a class's __init__ is read, and a method on a class of the helper; a
        # computed key in the helper is loud with both places named
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        with open(os.path.join(root, "planted_helper.py"), "w", encoding="utf-8") as f:
            f.write('import os\ndef floor():\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\ndef restore(name, value):\n    os.environ[name] = value\n'
                    'class Seam:\n    def __init__(self):\n        os.environ["ROMP_X"] = "1"\n'
                    '    @classmethod\n    def arm(cls):\n        os.environ["ROMP_Y"] = "1"\n')
        for shape in ('from planted_helper import floor\nfloor()', 'import planted_helper\nplanted_helper.floor()',
                      'import planted_helper as _h\n_h.floor()', 'from planted_helper import floor as _floor\n_floor()',
                      'from tests.planted_helper import floor\nfloor()',
                      'import tests.planted_helper\ntests.planted_helper.floor()', 'from planted_helper import *\nfloor()',
                      'from tests.planted_helper import *\nfloor()'):
            self.assertIn("ROMP_POSTAL_PEERS", _module_level_env_writes(ast.parse(shape + "\n"), "planted.py", root=root), shape)
        self.assertIn("ROMP_X", _module_level_env_writes(ast.parse("from planted_helper import Seam\nSeam()\n"), "planted.py", root=root))
        for shape in ('import planted_helper\nplanted_helper.Seam.arm()', 'from planted_helper import Seam\nSeam.arm()',
                      'import tests.planted_helper\ntests.planted_helper.Seam.arm()', 'from planted_helper import *\nSeam.arm()',
                      'import tests.planted_helper\ntests.planted_helper.Seam()'):
            keys = _module_level_env_writes(ast.parse(shape + "\n"), "planted.py", root=root)
            self.assertIn("ROMP_Y" if "arm" in shape else "ROMP_X", keys, shape)
        self.assertEqual(_module_level_env_writes(ast.parse("import planted_helper\ndef floor():\n    pass\nfloor()\n"), "planted.py", root=root), set(),
                         "a bare name reaches the module's own def when no import binds that name: the helper's floor is "
                         "bound to planted_helper.floor alone")
        star = _module_level_env_write_records(ast.parse('from planted_helper import *\nfloor()\n'), "planted.py", root=root)
        self.assertEqual([(w.key, w.line, w.via) for w, _nested in star], [("ROMP_POSTAL_PEERS", 2, "floor() at planted_helper.py:2, the write at line 3")])
        recs = _module_level_env_write_records(ast.parse('from planted_helper import floor\nfloor()\n'), "planted.py", root=root)
        self.assertEqual([(w.key, w.line, w.via) for w, _nested in recs], [("ROMP_POSTAL_PEERS", 2, "floor() at planted_helper.py:2, the write at line 3")])
        with self.assertRaises(UnreadableEnvWrite) as loud:
            _module_level_env_writes(ast.parse('from planted_helper import restore\nrestore("ROMP_POSTAL_PEERS", "0")\n'), "planted.py", root=root)
        self.assertIn("at line 5 of planted_helper.py", str(loud.exception))
        self.assertIn("reached at import from planted.py:2 through restore() at planted_helper.py:4", str(loud.exception))
        self.assertEqual(_module_level_env_writes(ast.parse("from romp_load import load_source\nload_source('x', 'y')\n"), "planted.py"), set(),
                         "load_source is a name bound to product code in tests/romp_load.py, not a def under tests/: outside the scan, as the comment above _Module says")
        banner = "test_update_banner_confirm_served.py"
        recs = _module_level_env_write_records(ast.parse(open(os.path.join(HERE, banner), encoding="utf-8", errors="replace").read()), banner)
        seen = {w.key: ast.unparse(w.value) for w, _nested in recs}
        self.assertEqual({k: seen.get(k) for k in ("ROMP_MANAGER_PORT", "ROMP_KERNEL_PORT", "ROMP_SERVE_PORT")},
                         {"ROMP_MANAGER_PORT": "'1'", "ROMP_KERNEL_PORT": "'1'", "ROMP_SERVE_PORT": "'1'"},
                         "%s updates os.environ from DEAD_PORTS at import; the scan reads the keys and the values through the name: %r" % (banner, seen))
        for shape in ("os.environ.update(computed())", "os.environ.update(**saved)", "os.environ.update(saved, ROMP_X=\"1\")",
                      "os.environ |= saved", 'os.environ[name] = "0"', 'os.environ.setdefault(name, "0")', 'os.putenv(name, "0")',
                      "saved = dict(os.environ)\nos.environ.update(saved)",
                      'OFF = {"ROMP_POSTAL_PEERS": "0"}\nOFF = computed()\nos.environ.update(OFF)',
                      'for v in NAMES:\n    os.environ[v] = "0"',
                      # the third commit of 2026-09-22: a computed key or mapping in the dunder and bytes spellings
                      'os.environ.__setitem__(name, "0")', 'dict.__setitem__(os.environ, name, "0")', "os.environ.__ior__(saved)",
                      "dict.__ior__(os.environ, saved)", 'os.environb[name] = b"0"', "os.environb.update(saved)",
                      # round 2 of fork PR #894 (the reviewer's ruling of round 1): a name read through its first binding
                      # alone, and a dict only through the allowed reads, so each of these is loud rather than misread
                      'D = {"ROMP_MANAGER_PORT": "1"}\nD["ROMP_POSTAL_PEERS"] = "0"\nos.environ.update(D)',
                      'D = {"ROMP_SERVE_PORT": "1"}\nD["ROMP_SERVE_PORT"] = "7432"\nos.environ.update(D)',
                      'D = {"ROMP_MANAGER_PORT": "1"}\nD |= {"ROMP_POSTAL_PEERS": "0"}\nos.environ.update(D)',
                      'D = {"ROMP_MANAGER_PORT": "1"}\nD.update(ROMP_POSTAL_PEERS="0")\nos.environ.update(D)',
                      'D = {"ROMP_MANAGER_PORT": "1"}\nD.setdefault("ROMP_POSTAL_PEERS", "0")\nos.environ.update(D)',
                      'D = {"ROMP_MANAGER_PORT": "1"}\nE = D\nE["ROMP_POSTAL_PEERS"] = "0"\nos.environ.update(D)',
                      'D = {"ROMP_MANAGER_PORT": "1"}\ndef _f():\n    D["ROMP_POSTAL_PEERS"] = "0"\n_f()\nos.environ.update(D)',
                      'D = {"ROMP_MANAGER_PORT": "1"}\ndict.update(D, ROMP_POSTAL_PEERS="0")\nos.environ.update(D)',
                      'for k in ("ROMP_KERNEL_NO_OPEN",):\n    pass\nk = "ROMP_POSTAL_PORT"\nos.environ[k] = "1"',
                      'for json in ("ROMP_MANAGER_PORT",):\n    pass\nimport json\nos.environ[json] = "1"',
                      'os.environ[name] += "0"', '[None for os.environ[name] in ["0"]]'):
            with self.assertRaises(UnreadableEnvWrite, msg=shape) as loud:
                _module_level_env_writes(ast.parse("import os\n" + shape + "\n"), "planted.py")
            self.assertIn("cannot read the key", str(loud.exception), shape)
            self.assertIn("at line %d of planted.py" % (shape.count("\n") + 2), str(loud.exception), shape)

    def test_a_name_is_read_through_its_first_binding_alone_and_a_later_binding_or_a_parameter_makes_it_loud(self):
        """The reviewer's ruling of round 1 on fork PR #894 (extra4-1, correctness-2): a loop name's literals were read
        from its first binding whatever the module did with the name later at import, and a callee's parameter shadowed
        only the value table, so a write keyed by a rebound loop name, or by a parameter or a local of the same name,
        was recorded as the module-level loop's literal (a licensed name) while the module wrote another, a leak name
        among them. Now any later binding the module's code spells makes the name unreadable (a rebinding through the
        module's namespace or by a string exec or eval runs is not seen: [namespace-rebinding] and [exec-eval] above
        _Module, each with a plant of a loop name), and a write through it is loud, naming the module
        and the line: an assignment, an import, a def, a with target, a loop over a tuple target, and in a callee a
        parameter or a local assignment. At the round-1 head each was recorded as ROMP_KERNEL_NO_OPEN or
        ROMP_MANAGER_PORT (the reassigned loop name had been loud before that round's commits). A function's own loop over
        literals, the module's and a class body's are still read. The verifier's findings on round 2 of fork PR #894 added
        three kinds: a star import, which binds names no text of the module spells and so makes every name unreadable, and
        a `type` statement (3.12 on), each recorded as ROMP_KERNEL_NO_OPEN at round 2's eleventh commit; and the walrus,
        the annotated and the augmented rebinding and a callee's match capture, except name and with target, loud at that
        commit too but held by no plant, so a mutant that dropped any one of those readings left every pin green."""
        self.maxDiff = None
        loud = (
            ("a loop name reassigned at import", 'for k in ("ROMP_KERNEL_NO_OPEN",):\n    pass\nk = "ROMP_POSTAL_PORT"\nos.environ[k] = "1"',
             "at line 5 of planted.py"),
            ("a loop name rebound by an import", 'for json in ("ROMP_MANAGER_PORT",):\n    pass\nimport json\nos.environ[json] = "1"',
             "at line 5 of planted.py"),
            ("a loop name rebound by a def", 'for k in ("ROMP_MANAGER_PORT",):\n    pass\ndef k():\n    pass\nos.environ[k] = "1"',
             "at line 6 of planted.py"),
            ("a loop name rebound by a with target", 'for k in ("ROMP_MANAGER_PORT",):\n    pass\nwith open(os.devnull) as k:\n    pass\n'
             'os.environ[k] = "1"', "at line 6 of planted.py"),
            ("a loop name rebound by a loop over a tuple target", 'for k in ("ROMP_MANAGER_PORT",):\n    pass\n'
             'for k, _v in (("ROMP_POSTAL_PORT", 1),):\n    pass\nos.environ[k] = "1"', "at line 6 of planted.py"),
            ("a callee's parameter over a module loop name", 'for name in ("ROMP_KERNEL_NO_OPEN",):\n    pass\ndef _put(name):\n'
             '    os.environ[name] = "1"\n_put("ROMP_POSTAL_PORT")', "at line 5 of planted.py: os.environ[name] = '1' (a string or bytes literal key"),
            ("a callee's local assignment over a module loop name", 'for name in ("ROMP_MANAGER_PORT",):\n    pass\ndef _f():\n'
             '    name = "ROMP_POSTAL_PORT"\n    os.environ[name] = "1"\n_f()', "at line 6 of planted.py: os.environ[name] = '1' (a string or bytes literal key"),
            ("a callee's parameter over a module dict name", 'D = {"ROMP_MANAGER_PORT": "1"}\ndef _put(D):\n    os.environ.update(D)\n'
             '_put({"ROMP_POSTAL_PORT": "1"})', "at line 4 of planted.py"),
            # the verifier's findings on round 2 of fork PR #894
            ("a loop name rebound by a star import", 'for k in ("ROMP_KERNEL_NO_OPEN",):\n    pass\nfrom h_star import *\n'
             'os.environ[k] = "1"', "at line 5 of planted.py"),
            ("a loop name rebound by a walrus", 'for k in ("ROMP_KERNEL_NO_OPEN",):\n    pass\nif (k := "ROMP_POSTAL_PORT"):\n    pass\n'
             'os.environ[k] = "1"', "at line 6 of planted.py"),
            ("a loop name rebound by an annotated assignment", 'for k in ("ROMP_KERNEL_NO_OPEN",):\n    pass\nk: str = "ROMP_POSTAL_PORT"\n'
             'os.environ[k] = "1"', "at line 5 of planted.py"),
            ("a loop name rebound by an augmented assignment", 'for k in ("ROMP_POSTAL",):\n    pass\nk += "_PORT"\nos.environ[k] = "1"',
             "at line 5 of planted.py"),
            ("a callee's match capture over a module loop name", 'for k in ("ROMP_KERNEL_NO_OPEN",):\n    pass\ndef _f():\n'
             '    match "ROMP_POSTAL_PORT":\n        case k:\n            os.environ[k] = "1"\n_f()', "at line 7 of planted.py"),
            ("a callee's except name over a module loop name", 'for k in ("ROMP_KERNEL_NO_OPEN",):\n    pass\ndef _f():\n    try:\n'
             '        pass\n    except OSError as k:\n        pass\n    os.environ[k] = "1"\n_f()', "at line 9 of planted.py"),
            ("a callee's with target over a module loop name", 'import contextlib\nfor k in ("ROMP_KERNEL_NO_OPEN",):\n    pass\n'
             'def _f():\n    with contextlib.nullcontext("ROMP_POSTAL_PORT") as k:\n        os.environ[k] = "1"\n_f()',
             "at line 7 of planted.py"))
        if _TYPE_ALIAS is not None:     # the statement parses from 3.12 on
            loud += (("a loop name rebound by a type statement", 'for k in ("ROMP_KERNEL_NO_OPEN",):\n    pass\ntype k = str\n'
                      'os.environ[k] = "1"', "at line 5 of planted.py"),)
        wrong = []
        for label, body, where in loud:
            try:
                recs = _module_level_env_write_records(ast.parse("import os\n" + body + "\n"), "planted.py")
                wrong.append("%s: recorded %r and raised nothing" % (label, sorted(w.key for w, _n in recs)))
            except UnreadableEnvWrite as e:
                if "cannot read the key" not in str(e) or where not in str(e):
                    wrong.append("%s: loud, but not naming %r: %s" % (label, where, e))
        self.assertEqual(wrong, [], "every later binding the module spells makes the name unreadable and the write loud, naming the module and line")
        for body, keys in (('def _f():\n    for v in ("ROMP_A", "ROMP_B"):\n        os.environ[v] = "0"\n_f()', ["ROMP_A", "ROMP_B"]),
                           ('for v in ("ROMP_A", "ROMP_B"):\n    os.environ[v] = "0"', ["ROMP_A", "ROMP_B"]),
                           ('class _K:\n    for v in ("ROMP_A",):\n        os.environ[v] = "0"', ["ROMP_A"])):
            recs = _module_level_env_write_records(ast.parse("import os\n" + body + "\n"), "planted.py")
            self.assertEqual(sorted(w.key for w, _n in recs), keys, body)

    def test_a_tracked_dict_is_read_only_through_the_allowed_reads_and_any_other_reference_is_loud(self):
        """The reviewer's ruling of round 1 on fork PR #894 (extra4-1): a dict name's keys and values were read from its
        first binding whatever the module did to it later at import, so a module that mutated the dict after binding it
        wrote ROMP_POSTAL_PEERS (or a dead port of 7432) while the census recorded the first binding's keys and values
        and the pin passed. A tracked dict is read only through _DICT_READS, and any other reference to its name, in any
        scope, makes an update through it loud, naming the module and the line: a subscript store, a value overwritten,
        |=, update with a keyword, setdefault, an alias (no list of mutations can enumerate aliasing), a mutation inside
        a def the module calls, an unbound dict.update, a del, a rebinding by a for target, a def of the same name, and a
        star import (the verifier's finding on round 2 of fork PR #894: it rebinds names no text of the module spells, and
        the update read the first binding at round 2's eleventh commit). At the
        round-1 head each recorded the dict's first binding, not what the module had made of it by the update. A module that reads its dict
        the way DEAD_PORTS is read, through every allowed read (the update argument, `|=`, ** spreads in a call and a
        dict display, a for and a comprehension iterable, a membership test, inside a def as well) is still read, keys
        and values, and so is the real banner module (the shape test above)."""
        self.maxDiff = None
        first = 'D = {"ROMP_MANAGER_PORT": "1"}\n'
        loud = (("a subscript store", first + 'D["ROMP_POSTAL_PEERS"] = "0"\nos.environ.update(D)', 4),
                ("a value overwritten", 'D = {"ROMP_SERVE_PORT": "1"}\nD["ROMP_SERVE_PORT"] = "7432"\nos.environ.update(D)', 4),
                ("|=", first + 'D |= {"ROMP_POSTAL_PEERS": "0"}\nos.environ.update(D)', 4),
                ("update with a keyword", first + 'D.update(ROMP_POSTAL_PEERS="0")\nos.environ.update(D)', 4),
                ("setdefault", first + 'D.setdefault("ROMP_POSTAL_PEERS", "0")\nos.environ.update(D)', 4),
                ("an alias", first + 'E = D\nE["ROMP_POSTAL_PEERS"] = "0"\nos.environ.update(D)', 5),
                ("a mutation inside a def the module calls", first + 'def _f():\n    D["ROMP_POSTAL_PEERS"] = "0"\n_f()\nos.environ.update(D)', 6),
                ("an unbound dict.update", first + 'dict.update(D, ROMP_POSTAL_PEERS="0")\nos.environ.update(D)', 4),
                ("a del", 'D = {"ROMP_MANAGER_PORT": "1", "ROMP_POSTAL_PEERS": "0"}\ndel D["ROMP_MANAGER_PORT"]\nos.environ.update(D)', 4),
                ("a rebinding by a for target", first + 'for D in ({"ROMP_POSTAL_PEERS": "0"},):\n    pass\nos.environ.update(D)', 5),
                ("a def of the same name", first + 'def D():\n    pass\nos.environ.update(D)', 5),
                ("an update through |= of the environment", first + 'D["ROMP_POSTAL_PEERS"] = "0"\nos.environ |= D', 4),
                ("a rebinding by a star import", first + 'from h_star import *\nos.environ.update(D)', 4))
        wrong = []
        for label, body, line in loud:
            try:
                recs = _module_level_env_write_records(ast.parse("import os\n" + body + "\n"), "planted.py")
                wrong.append("%s: recorded %r and raised nothing" % (label, sorted((w.key, ast.unparse(w.value)) for w, _n in recs)))
            except UnreadableEnvWrite as e:
                if "cannot read the keys of this update at line %d of planted.py" % line not in str(e):
                    wrong.append("%s: loud, but not naming line %d: %s" % (label, line, e))
        self.assertEqual(wrong, [], "a dict referenced other than by an allowed read is unreadable, and an update through it loud")
        kept = ('DEAD = {"ROMP_MANAGER_PORT": "1", "ROMP_KERNEL_PORT": "1"}\nos.environ.update(DEAD)\nos.environ |= DEAD\n'
                'env = dict(os.environ, **DEAD)\nshown = {**DEAD}\nfor k in DEAD:\n    pass\nnames = [k for k in DEAD]\n'
                'there = "ROMP_X" in DEAD\n'
                'def _later():\n    return dict(os.environ, **DEAD), {k: "2" for k in DEAD}, "ROMP_Y" not in DEAD\n')
        recs = _module_level_env_write_records(ast.parse("import os\n" + kept), "planted.py")
        self.assertEqual(sorted((w.key, w.shape, ast.unparse(w.value)) for w, _n in recs),
                         [("ROMP_KERNEL_PORT", "update", "'1'"), ("ROMP_KERNEL_PORT", "|=", "'1'"),
                          ("ROMP_MANAGER_PORT", "update", "'1'"), ("ROMP_MANAGER_PORT", "|=", "'1'")],
                         "every allowed read keeps the dict readable, keys and values")

    def test_a_bare_name_is_a_call_only_as_a_decorator_or_a_metaclass_and_a_base_runs_its_init_subclass(self):
        """The reviewer's ruling of round 1 on fork PR #894 (correctness-5, extra4-5, correctness-4): the resolver read every
        bare name or attribute it was handed as a call, so a base whose __init__ writes counted as the class statement's
        write (a false red for a write that never runs at import) and a writing def named in a default, an if test, a
        with item, a for iterable or an except type was reported as called; and it missed calls that do run when a class
        is created: a base's __init_subclass__, a metaclass's __new__ and __call__. A bare name is read as a call only as a
        decorator or a `metaclass=` value, and a base named bare runs its __init_subclass__ chain. At the round-1 head the
        eight that never run were recorded, and the metaclass's __new__ and __call__ and both __init_subclass__ plants were
        not; the metaclass's __init__ (the control, found through the rule this narrows), the bare decorator and the call
        inside a base expression were recorded at both heads. The verifier's findings on round 2 of fork PR #894 added two:
        a metaclass's __prepare__, which creating the class runs before it calls the metaclass (not recorded at round 2's
        eleventh commit), and a metaclass named by attribute (`metaclass=helper.Meta`), recorded at that commit but held by
        no plant, so a mutant that read a Name alone as the metaclass left every pin green. The fix of those findings adds
        three more, each read at round 2's twelfth commit and held by no plant, while _compound_header's docstring said
        nothing in a for or with target ran as a call: a call in a for or with target's key and a call in a for target's
        attribute object run at import and are read, and a def named bare as a for target's key is not a call. The
        verifier's finding on round 2's thirteenth commit: the texts say that of every for AND with target, but the plants
        held four of its positions, so a mutant that read a bare name in a with target as a call, one that read a bare
        name as a for target's attribute object as a call, and one that dropped an attribute with target from the block
        header each left every pin green. The plants now hold each position in both statements: the target itself (a
        store), a subscript target's key and object and an attribute target's object, with a def named bare in each (never
        a call; as a subscript's object the store then raises TypeError, and the def still never runs) and a call in each
        position a call can take (run at import, and read). The scan read every one of them that way at the thirteenth
        commit; only the plants were missing."""
        self.maxDiff = None
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        with open(os.path.join(root, "planted_base.py"), "w", encoding="utf-8") as f:
            f.write('import os\nclass Base:\n    def __init__(self):\n        os.environ["ROMP_POSTAL_PEERS"] = "0"\n'
                    'class Hooked:\n    def __init_subclass__(cls, **kw):\n        os.environ["ROMP_POSTAL_PEERS"] = "0"\n'
                    'class Meta(type):\n    def __init__(cls, *a):\n        os.environ["ROMP_POSTAL_PEERS"] = "0"\n')
        write = 'def _w():\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n'
        never = (("a base whose __init__ writes, never instantiated", 'class _Base:\n    def __init__(self):\n'
                  '        os.environ["ROMP_POSTAL_PEERS"] = "0"\nclass _K(_Base):\n    pass'),
                 ("an imported base whose __init__ writes, never instantiated", 'import planted_base\nclass _K(planted_base.Base):\n    pass'),
                 ("a def named in a default", write + 'def _f(cb=_w):\n    pass'),
                 ("a def named in an if test", write + 'if _w:\n    pass'),
                 ("a def named in a with item", write + 'with _w:\n    pass'),
                 ("a def named as a for iterable", write + 'for _x in _w:\n    pass'),
                 ("a def named as an except type", write + 'try:\n    pass\nexcept _w:\n    pass'),
                 ("a def named in a keyword other than metaclass", write + 'class _K(flag=_w):\n    pass'),
                 ("a def named bare as a for target's key", '_d = {}\n' + write + 'for _d[_w] in [1]:\n    pass'),
                 # the verifier's finding on round 2's thirteenth commit: every other position of a for or with target
                 ("a def named bare as a for target (a store)", write + 'for _w in [1]:\n    pass'),
                 ("a def named bare as a for target's subscript object", write + 'for _w[0] in [1]:\n    pass'),
                 ("a def named bare as a for target's attribute object", write + 'for _w.x in [1]:\n    pass'),
                 ("a def named bare as a with target (a store)", 'import contextlib\n' + write +
                  'with contextlib.nullcontext(1) as _w:\n    pass'),
                 ("a def named bare as a with target's key", 'import contextlib\n_d = {}\n' + write +
                  'with contextlib.nullcontext(1) as _d[_w]:\n    pass'),
                 ("a def named bare as a with target's subscript object", 'import contextlib\n' + write +
                  'with contextlib.nullcontext(1) as _w[0]:\n    pass'),
                 ("a def named bare as a with target's attribute object", 'import contextlib\n' + write +
                  'with contextlib.nullcontext(1) as _w.x:\n    pass'))
        run = (("a metaclass's __init__ (the control)", 'class _M(type):\n    def __init__(cls, *a):\n'
                '        os.environ["ROMP_POSTAL_PEERS"] = "0"\nclass _K(metaclass=_M):\n    pass'),
               ("a metaclass's __new__", 'class _M(type):\n    def __new__(mcs, *a):\n        os.environ["ROMP_POSTAL_PEERS"] = "0"\n'
                '        return type.__new__(mcs, *a)\nclass _K(metaclass=_M):\n    pass'),
               ("a metaclass's __call__", 'class _M(type):\n    def __call__(cls, *a):\n        os.environ["ROMP_POSTAL_PEERS"] = "0"\n'
                'class _K(metaclass=_M):\n    pass'),
               ("a base's __init_subclass__", 'class _Base:\n    def __init_subclass__(cls, **kw):\n'
                '        os.environ["ROMP_POSTAL_PEERS"] = "0"\nclass _K(_Base):\n    pass'),
               ("an imported base's __init_subclass__", 'from planted_base import Hooked\nclass _K(Hooked):\n    pass'),
               ("a bare decorator", write.replace("():", "(fn):") + '@_w\ndef _d():\n    pass'),
               ("a call inside a base expression", write + 'class _K(_w() or object):\n    pass'),
               ("a metaclass's __prepare__", 'class _M(type):\n    @classmethod\n    def __prepare__(mcs, name, bases, **kw):\n'
                '        os.environ["ROMP_POSTAL_PEERS"] = "0"\n        return {}\nclass _K(metaclass=_M):\n    pass'),
               ("a metaclass named by attribute", 'import planted_base\nclass _K(metaclass=planted_base.Meta):\n    pass'),
               ("a call in a for target's key", '_d = {}\n' + write + 'for _d[_w()] in [1]:\n    pass'),
               ("a call in a with target's key", 'import contextlib\n_d = {}\n' + write +
                'with contextlib.nullcontext(1) as _d[_w()]:\n    pass'),
               ("a call in a for target's attribute object", 'import types\n' + write +
                '    return types.SimpleNamespace()\nfor _w().x in [1]:\n    pass'),
               # the verifier's finding on round 2's thirteenth commit: the positions a call can take in both statements
               ("a call as a for target's subscript object", write + '    return {}\nfor _w()["k"] in [1]:\n    pass'),
               ("a call as a with target's subscript object", 'import contextlib\n' + write +
                '    return {}\nwith contextlib.nullcontext(1) as _w()["k"]:\n    pass'),
               ("a call in a with target's attribute object", 'import contextlib, types\n' + write +
                '    return types.SimpleNamespace()\nwith contextlib.nullcontext(1) as _w().x:\n    pass'))
        wrong = []
        for label, body in never + run:
            keys = _module_level_env_writes(ast.parse("import os\n" + body + "\n"), "planted.py", root=root)
            if ("ROMP_POSTAL_PEERS" in keys) != any(label == r[0] for r in run):
                wrong.append("%s: %s" % (label, "recorded, though it never runs at import" if keys else "not recorded, though it runs at import"))
        self.assertEqual(wrong, [], "a bare name is a call only where Python calls it, and a base runs its __init_subclass__")

    def test_the_resolver_reads_every_binding_of_a_name_in_every_import_time_block_and_follows_the_mapping_into_a_parameter(self):
        """The reviewer's ruling of round 1 on fork PR #894 (correctness-4, extra4-2): silently missed at the round-1 head, and
        read now: a def in a module-level if or try block (the try/except ImportError fallback among them) or an else or
        finally body, called after the block or in it; a def in a class body called from that body; a def shadowed by a
        later import of its name (both bindings read, the safe side, not an order-aware pick); a class whose __new__
        writes, instantiated; the mapping passed to a callee's parameter by position, by keyword, to a method, or as the
        parameter's default; a def re-exported by a helper (`from helper2 import floor`, `helper2.floor()`, a helper's
        module attribute). A class-body def shadowed by a later import in the body was read at both heads, through the
        import alone at the round-1 head and through both bindings now. A parameter is the mapping only where the call
        binds it so, and it shadows a module name bound to the mapping. The mapping passed into *args or **kwargs is loud,
        since the scan cannot say what the callee does with it. A keyword-only parameter defaulting to the mapping was read
        at round 2's eleventh commit and held by no plant (the verifier's finding on round 2 of fork PR #894: a mutant that
        dropped that route left every pin green); it has one now."""
        self.maxDiff = None
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        for name, text in (("planted_floor.py", 'import os\ndef floor():\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n'),
                           ("planted_reexport.py", "from planted_floor import floor\n"),
                           ("planted_reexport_module.py", "import planted_floor\n")):
            with open(os.path.join(root, name), "w", encoding="utf-8") as f:
                f.write(text)
        write = '    os.environ["ROMP_POSTAL_PEERS"] = "0"\n'
        read = (("a def in an if body, called after it", "if True:\n    def _f():\n    " + write + "_f()"),
                ("a def in an if body, called in it", "if True:\n    def _f():\n    " + write + "    _f()"),
                ("a def in a try/except ImportError fallback", "try:\n    import _no_such_module\nexcept ImportError:\n"
                 "    def _f():\n    " + write + "_f()"),
                ("a def in an else body", "if False:\n    pass\nelse:\n    def _f():\n    " + write + "_f()"),
                ("a def in a finally body", "try:\n    pass\nfinally:\n    def _f():\n    " + write + "_f()"),
                ("a def in a class body called from that body", "class _K:\n    def _f():\n    " + write + "    _f()"),
                ("a class-body def shadowed by a later import in the body", "class _K:\n    def floor():\n        pass\n"
                 "    from planted_floor import floor\n    floor()"),
                ("a def shadowed by a later import of its name", "def floor():\n    pass\nfrom planted_floor import floor\nfloor()"),
                ("a class whose __new__ writes, instantiated", "class _K:\n    def __new__(cls):\n    " + write +
                 "        return object.__new__(cls)\n_K()"),
                ("the mapping passed by position", "def _put(env):\n    env['ROMP_POSTAL_PEERS'] = '0'\n_put(os.environ)"),
                ("the mapping passed by keyword", "def _put(env=None):\n    env['ROMP_POSTAL_PEERS'] = '0'\n_put(env=os.environ)"),
                ("the mapping passed to a method", "class _S:\n    def __init__(self, env):\n        env['ROMP_POSTAL_PEERS'] = '0'\n_S(os.environ)"),
                ("the mapping as a parameter's default", "def _put(env=os.environ):\n    env['ROMP_POSTAL_PEERS'] = '0'\n_put()"),
                ("the mapping as a keyword-only parameter's default", "def _put(*, env=os.environ):\n    env['ROMP_POSTAL_PEERS'] = '0'\n_put()"),
                ("the mapping passed on through two callees", "def _inner(e):\n    e.update(ROMP_POSTAL_PEERS='0')\ndef _outer(env):\n"
                 "    _inner(env)\n_outer(os.environ)"),
                ("a def a helper re-exports, imported by name", "from planted_reexport import floor\nfloor()"),
                ("a def a helper re-exports, through the helper", "import planted_reexport\nplanted_reexport.floor()"),
                ("a module a helper imports, through the helper", "from planted_reexport_module import planted_floor\nplanted_floor.floor()"))
        wrong = []
        for label, body in read:
            try:
                keys = _module_level_env_writes(ast.parse("import os\n" + body + "\n"), "planted.py", root=root)
                if "ROMP_POSTAL_PEERS" not in keys:
                    wrong.append("%s: not recorded" % label)
            except UnreadableEnvWrite as e:
                wrong.append("%s: loud: %s" % (label, e))
        self.assertEqual(wrong, [], "each of these runs a write at import, and the resolver reads it")
        self.assertEqual(_module_level_env_writes(ast.parse("import os\ndef _put(env):\n    env['ROMP_X'] = '0'\n_put({})\n"), "planted.py"),
                         set(), "a parameter the call does not bind to the mapping is not the mapping")
        self.assertEqual(_module_level_env_writes(ast.parse("import os\nenv = os.environ\ndef _put(env):\n    env['ROMP_X'] = '0'\n_put({})\n"),
                                                  "planted.py"), set(), "a parameter shadows the module's name bound to the mapping")
        for body, how in (("def _put(*args):\n    pass\n_put(os.environ)", "into *args of _put()"),
                          ("def _put(**kw):\n    pass\n_put(env=os.environ)", "into **kwargs of _put()"),
                          ("def _put(env):\n    pass\n_put(*[os.environ])", "inside a * argument")):
            with self.assertRaises(UnreadableEnvWrite, msg=body) as loud:
                _module_level_env_writes(ast.parse("import os\n" + body + "\n"), "planted.py")
            self.assertIn("the environment mapping is passed %s at line 4 of planted.py" % how, str(loud.exception), body)

    def test_a_call_chain_longer_than_the_cap_raises_naming_the_chain_and_a_cycle_is_cut(self):
        """The reviewer's ruling of round 1 on fork PR #894 (correctness-4, extra4-2): the resolver cut a chain at six calls,
        silently, so a write seven callees down passed unread. The cap is now 40 calls, above the deepest chain the
        census follows in the tree (the figure, and how it is derived, is under _CALL_DEPTH_CAP), and a chain longer than
        the cap raises naming every call in it; a cycle is still cut by the per-chain seen set, without a raise. At the
        round-1 head the chain of 40 below was not recorded and the chain of 41 passed silently. The memo (_reach) is
        reused only under its three conditions, each planted here with the records compared to a reading whose memo
        stores nothing: no cycle cut under the callee against a callee above it, none of the callees it read above it now
        (the verifier's finding on round 2 of fork PR #894: `_a -> _b -> _c -> _a` read from `_b` first and reused under
        `_a` recorded `_a`'s write a second time, back through `_a`), and its height still under the cap."""
        def chain(n):
            defs = "".join("def _f%d():\n    _f%d()\n" % (i, i + 1) for i in range(n - 1))
            return "import os\n" + defs + "def _f%d():\n    os.environ['ROMP_POSTAL_PEERS'] = '0'\n_f0()\n" % (n - 1)
        recs = _module_level_env_write_records(ast.parse(chain(40)), "planted.py")
        self.assertEqual([(w.key, w.line) for w, _n in recs], [("ROMP_POSTAL_PEERS", 82)], "a chain of 40 calls is read to its write")
        with self.assertRaises(UnreadableEnvWrite) as loud:
            _module_level_env_write_records(ast.parse(chain(41)), "planted.py")
        self.assertIn("the call chain reached at import from planted.py:84 is longer than the resolver's cap of 40 calls", str(loud.exception))
        self.assertIn(" -> ".join("_f%d() at planted.py:%d" % (i, 2 + 2 * i) for i in range(41)), str(loud.exception),
                      "the message names every call of the chain")
        self.assertEqual(_CALL_DEPTH_CAP, 40)
        cycle = "import os\ndef _a():\n    os.environ['ROMP_POSTAL_PEERS'] = '0'\n    _b()\ndef _b():\n    _a()\n_a()\n"
        recs = _module_level_env_write_records(ast.parse(cycle), "planted.py")
        self.assertEqual(sorted((w.key, w.via) for w, _n in recs), [("ROMP_POSTAL_PEERS", "_a() at planted.py:2, the write at line 3")],
                         "a cycle is read once around, cut where it comes back to _a, without a raise")
        # the memo (_reach): a callee read under a cycle cut is not reused where the cut does not hold, and a callee read
        # shallow is not reused where its chain would pass the cap from deeper down
        recs = _module_level_env_write_records(ast.parse(cycle + "_b()\n"), "planted.py")
        self.assertEqual(sorted((w.key, w.line, w.via) for w, _n in recs),
                         [("ROMP_POSTAL_PEERS", 7, "_a() at planted.py:2, the write at line 3"),
                          ("ROMP_POSTAL_PEERS", 8, "_b() at planted.py:5 -> _a() at planted.py:2, the write at line 3")],
                         "_b read under _a's chain is cut at _a; called at import itself, it reaches _a's write")
        deep = "".join("def _x%d():\n    _x%d()\n" % (i, i + 1) for i in range(30)) + "def _x30():\n    pass\n"
        deep += "".join("def _y%d():\n    _y%d()\n" % (i, i + 1) for i in range(15)) + "def _y15():\n    _x0()\n"
        _module_level_env_write_records(ast.parse("import os\n" + deep + "_x0()\n"), "planted.py")
        with self.assertRaises(UnreadableEnvWrite, msg="a chain through a callee read shallow first") as loud:
            _module_level_env_write_records(ast.parse("import os\n" + deep + "_x0()\n_y0()\n"), "planted.py")
        self.assertIn("is longer than the resolver's cap of 40 calls", str(loud.exception))
        # and a callee is not reused under a callee it read (the verifier's finding on round 2 of fork PR #894): _b, read
        # from its own call, reaches _a through _c (cut where _a calls _b back); under _a's call a fresh reading of _b cuts
        # at _a, so _a's write is recorded once there, not again through _b -> _c -> _a
        loop3 = ("import os\ndef _a():\n    os.environ['ROMP_POSTAL_PEERS'] = '0'\n    _b()\ndef _b():\n    _c()\n"
                 "def _c():\n    _a()\n_b()\n_a()\n")
        recs = _module_level_env_write_records(ast.parse(loop3), "planted.py")
        self.assertEqual([(w.key, w.line, w.via) for w, _n in recs],
                         [("ROMP_POSTAL_PEERS", 9, "_b() at planted.py:5 -> _c() at planted.py:7 -> _a() at planted.py:2, the write at line 3"),
                          ("ROMP_POSTAL_PEERS", 10, "_a() at planted.py:2, the write at line 3")],
                         "_b's reading from line 9 went through _a, so it is not reused under _a's call at line 10")

        class _StoresNothing(dict):
            def __setitem__(self, key, value):
                pass

        def projected(pairs):       # a record's value is a node of its own parse: compared by its text
            return [(w.key, w.shape, None if w.value is None else ast.unparse(w.value), w.line, w.resolved, w.via, nested)
                    for w, nested in pairs]

        def without_memo(src):
            tree = ast.parse(src)
            mod, out = _module_record(tree, "planted.py", HERE), []
            for node, nested, scope in _import_time_nodes_scoped(tree.body):
                out += [(w, nested) for w in _env_write_records(node, mod.names, "planted.py")]
                out += [(w, nested) for w in _reached_writes(node, mod, scope=scope, memo=_StoresNothing())]
            return out
        for src in (cycle, cycle + "_b()\n", loop3, "import os\n" + deep + "_x0()\n", chain(40)):
            self.assertEqual(projected(_module_level_env_write_records(ast.parse(src), "planted.py")), projected(without_memo(src)),
                             "the memo changes nothing a reading that stores nothing records")
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "test_planted_chain.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write("def _f0():\n    _f1()\ndef _f1():\n    _f2()\ndef _f2():\n    pass\nX = 1\n_f0()\n")
        self.assertEqual(_deepest_call_chain([path]), (3, "%s:8" % os.path.relpath(path, HERE)),
                         "the derivation --deepest-chain prints counts the calls of the longest chain and names where it starts")

    def test_every_shape_named_outside_the_scan_writes_when_run_and_the_scan_reads_none(self):
        """The list of what stays OUTSIDE the scan has one home, the comment above _Module (the reviewer's ruling of round 1
        on fork PR #894: tests/README.md's copy had dropped eval and the unbound setdefault, and nine shapes were in
        neither), and every shape on it carries an executed plant (_OUTSIDE_THE_SCAN): its tags are held EQUAL to the
        plants' keys; each plant, run in a child interpreter, writes its name to the process environment (after its hook,
        and not at its import, for what runs after the import); and the scan records nothing and raises nothing for it.
        A change that starts reading a shape reds here, and so does one that names a shape with no plant. README points
        at the comment and keeps no list of its own. The verifier's findings on round 2 of fork PR #894 found shapes the
        scan missed silently with none of them named (a metaclass's __prepare__, now read; the rest named under
        lambda-parameter, aliased-callee, callback, protocol-hook and namespace-rebinding, and a star import added to
        held-otherwise and from-os-putenv), each with its plants. The verifier's findings on round 2's thirteenth commit
        found two of those classes wider than their plants: a def or class bound inside a function takes the mapping into
        a parameter the way a lambda does, with the scan silent (now nested-def-parameter), and a loop name or a tracked
        dict is rebound or mutated with the scan silent through vars(), sys.modules, setattr on the module or a string
        that exec runs, as through globals() (plants added under namespace-rebinding and exec-eval). Its finding on the
        fourteenth commit found exec-eval's binding and mutation planted for exec alone: a walrus in an eval string
        binds a loop name, and a method call in one mutates a tracked dict, with the scan silent (eval plants added)."""
        self.maxDiff = None
        text = open(os.path.join(HERE, "test_hermetic_kernel_postal.py"), encoding="utf-8").read()
        self.assertIn("OUTSIDE the scan, named here", text, "the list's one home is the comment above _Module")
        block = text[text.index("OUTSIDE the scan, named here"):text.index("\n_Module = collections.namedtuple")]
        tags = re.findall(r"^#   \[([a-z-]+)\] ", block, re.M)
        self.assertEqual(sorted(tags), sorted(_OUTSIDE_THE_SCAN), "the comment's tags are the plants' keys, each once")
        self.assertEqual(len(tags), len(set(tags)))
        top = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, top, True)
        jobs, read = [], []
        for tag in sorted(_OUTSIDE_THE_SCAN):
            for i, plant in enumerate(_OUTSIDE_THE_SCAN[tag]):
                pid = "%s-%d" % (tag, i)
                key = "ROMP_PLANTED_OUTSIDE_%s_%d" % (tag.upper().replace("-", "_"), i)
                root = os.path.join(top, pid, "root")
                os.makedirs(os.path.join(top, pid, "product"))
                os.makedirs(root)
                for rel, body in plant["files"].items():
                    with open(os.path.normpath(os.path.join(root, rel)), "w", encoding="utf-8") as f:
                        f.write(body.replace("{key}", key))
                src = plant["src"].replace("{key}", key)
                path = os.path.join(root, "planted_%s.py" % tag.replace("-", "_"))
                with open(path, "w", encoding="utf-8") as f:
                    f.write(src)
                try:
                    keys = _module_level_env_writes(ast.parse(src), "planted.py", root=root)
                    if key in keys:
                        read.append("%s: recorded" % pid)
                except UnreadableEnvWrite as e:
                    read.append("%s: loud: %s" % (pid, e))
                jobs.append((pid, root, path, key, plant["hook"]))
        self.assertEqual(read, [], "the scan reads none of the shapes the comment names as outside it")
        proc = subprocess.run([sys.executable, "-c", _OUTSIDE_RUNNER, json.dumps(jobs)], capture_output=True, text=True,
                              timeout=120, stdin=subprocess.DEVNULL, cwd=top)
        self.assertEqual(proc.returncode, 0, proc.stderr[-3000:])
        ran = json.loads(proc.stdout)
        want = {pid: [not hook, True, ""] for pid, _r, _p, _k, hook in jobs}
        self.assertEqual(ran, want, "each plant writes its name when run: at its import, or after its hook and not before")
        readme = " ".join(open(os.path.join(HERE, "README.md"), encoding="utf-8").read().split())
        self.assertIn("What stays outside the scan is listed in one place, the comment above `_Module` in that module, each "
                      "shape with a plant the scan is held to recording nothing for", readme, "README points at the one list")
        for item in ("operator.setitem", "functools.partial", "posix.putenv"):
            self.assertNotIn(item, readme, "README keeps no second copy of the list")

    def test_an_augmented_write_and_a_key_bound_as_a_target_are_read_with_no_value(self):
        """The reviewer's ruling of round 1 on fork PR #894 (fresh-1): `os.environ["PATH"] += ...` and a key bound as a for,
        comprehension or with target wrote the name at import with the scan silent, in the direct, alias, os.environb,
        class-body and helper-called forms, and a module-level for or with target was out of reach of any fix inside
        _env_write_records, since the block's header yielded no target (_compound_header does now). An augmented write
        is read as shape "augmented" and a target as shape "target", each with NO value: the right side of `+=` is a
        suffix, not the value written, so it fails a value licence rather than meeting it ("1" += "1" writes "11"). A
        computed key in either is loud. At the round-1 head every shape below was recorded as nothing."""
        self.maxDiff = None
        wrong = []
        for body, shape, line in (('os.environ["ROMP_X"] += "y"', "augmented", 2),
                                  ('env = os.environ\nenv["ROMP_X"] += "y"', "augmented", 3),
                                  ('os.environb[b"ROMP_X"] += b"y"', "augmented", 2),
                                  ('class _K:\n    os.environ["ROMP_X"] += "y"', "augmented", 3),
                                  ('def _f():\n    os.environ["ROMP_X"] += "y"\n_f()', "augmented", 4),
                                  ('for os.environ["ROMP_X"] in ["y"]:\n    pass', "target", 2),
                                  ('for _a, os.environ["ROMP_X"] in [(1, "y")]:\n    pass', "target", 2),
                                  ('if True:\n    for os.environ["ROMP_X"] in ["y"]:\n        pass', "target", 3),
                                  ('class _K:\n    for os.environ["ROMP_X"] in ["y"]:\n        pass', "target", 3),
                                  ('[None for os.environ["ROMP_X"] in ["y"]]', "target", 2),
                                  ('import contextlib\nwith contextlib.nullcontext("y") as os.environ["ROMP_X"]:\n    pass', "target", 3),
                                  ('def _f():\n    for os.environ["ROMP_X"] in ["y"]:\n        pass\n_f()', "target", 5)):
            recs = _module_level_env_write_records(ast.parse("import os\n" + body + "\n"), "planted.py")
            got = [(w.key, w.shape, w.value, w.line) for w, _n in recs]
            if got != [("ROMP_X", shape, None, line)]:
                wrong.append("%r: %r" % (body, got))
        self.assertEqual(wrong, [], "each is one write of ROMP_X, its own shape, no value, at its line")
        for body in ('os.environ[name] += "y"', 'for os.environ[name] in ["y"]:\n    pass'):
            with self.assertRaises(UnreadableEnvWrite, msg=body) as loud:
                _module_level_env_writes(ast.parse("import os\n" + body + "\n"), "planted.py")
            self.assertIn("at line 2 of planted.py", str(loud.exception), body)

        def faults(body):
            out = collections.defaultdict(list)
            for name, rec in _module_level_records(ast.parse("import os\n" + body + "\n"), "test_planted.py"):
                out[name].append(rec)
            return _licence_faults({**_all_licensed_once(), **out}, _conftest_reasserted_union())
        self.assertEqual(faults('os.environ["ROMP_KERNEL_NO_OPEN"] += "1"'),
                         ["ROMP_KERNEL_NO_OPEN at test_planted.py:2 (augmented): licensed for the value '1' alone, not a shape with no value"])
        self.assertEqual(faults('os.environ["XDG_STATE_HOME"] += "/x"'),
                         ["XDG_STATE_HOME at test_planted.py:2 (augmented): the value (none) is not one this licence covers"])
        self.assertEqual(faults('for os.environ["ROMP_KERNEL_NO_OPEN"] in ["1"]:\n    pass'),
                         ["ROMP_KERNEL_NO_OPEN at test_planted.py:2 (target): licensed for the value '1' alone, not a shape with no value"])

    def test_a_starred_value_is_a_licence_fault_naming_its_line_and_every_other_value_shape_round_trips(self):
        """The reviewer's ruling of round 1 on fork PR #894 (extra10-1): _fresh re-parsed a value's text as an expression of
        its own, and a starred call argument (`os.putenv(K, *rest)`, and the setdefault and __setitem__ spellings) unparses
        to `*rest`, which is not one, so every consumer of the scan died on a SyntaxError naming no module and no line, on
        3.10 and 3.12. _fresh parses the text as a call argument now: the starred write is a licence fault naming its
        module, line and shape, on whichever interpreter runs this, and the eleven value shapes the refuter probed round
        -trip to the same tree as before, the starred one too."""
        for body, shape in (('rest = ("0",)\nos.putenv("ROMP_X", *rest)', "putenv"),
                            ('rest = ("0",)\nos.environ.setdefault("ROMP_X", *rest)', "setdefault"),
                            ('rest = ("0",)\nos.environ.__setitem__("ROMP_X", *rest)', "__setitem__"),
                            ('rest = ("0",)\ndict.__setitem__(os.environ, "ROMP_X", *rest)', "__setitem__")):
            out = collections.defaultdict(list)
            for name, rec in _module_level_records(ast.parse("import os\n" + body + "\n"), "test_planted.py"):
                out[name].append(rec)
            self.assertEqual([(r.value, r.resolved) for r in out["ROMP_X"]], [("*rest", "*('0',)")], body)
            faults = _licence_faults({**_all_licensed_once(), **out}, _conftest_reasserted_union())
            self.assertEqual(len(faults), 1, faults)
            self.assertTrue(faults[0].startswith("ROMP_X is written at module level by test_planted.py:3 (%s) and is not in the licensed set" % shape), faults[0])
        for text in ("'x'", "f(a, b=1)", "a.b[c]", "(yield x)", "(yield from x)", "await x", "(i for i in x)", "(y := 1)",
                     "(1, 2)", "(*a, b)", "lambda: 0"):
            node = ast.parse(text, mode="eval").body
            self.assertEqual(ast.dump(_fresh(node)), ast.dump(node), text)
        star = ast.parse("f(*rest)", mode="eval").body.args[0]
        self.assertEqual(ast.dump(_fresh(star)), ast.dump(star), "the starred argument round-trips")

    def _tunnels_probe(self, planted_text=None, conftest_text=None):
        """_PROBE in a fresh interpreter over the real module (imported) or over `planted_text`, a synthetic copy compiled
        under the real file's name, with the real tests/conftest.py or `conftest_text` in its place; returns the child's
        report."""
        paths = []
        for text, name in ((planted_text, "planted_tunnels_module.py"), (conftest_text, "planted_conftest.py")):
            paths.append("")
            if text is not None:
                d = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, d, True)
                paths[-1] = os.path.join(d, name)
                with open(paths[-1], "w", encoding="utf-8") as f:
                    f.write(text)
        env = dict(os.environ)
        env.pop("ROMP_POSTAL_PEERS", None)
        res = subprocess.run([sys.executable, "-c", _PROBE, HERE] + paths, capture_output=True, text=True, timeout=180, env=env, cwd=HERE)
        self.assertEqual(res.returncode, 0, res.stderr[-2000:])
        return json.loads(res.stdout.strip().splitlines()[-1])

    def test_importing_the_attaching_module_writes_no_leg_of_the_trio_and_its_setup_pins_all_three_for_the_test(self):
        """Executed, not read: a fresh interpreter pops the three names, imports the floor modules the tunnels module
        imports first (tests/__init__.py and tests/conftest.py) and reads the three names, imports
        tests/test_kernel_tunnels.py (which loads the kernel in-process against its own temp state and starts no bus)
        and reports them after the import (no port, no peers value, client-only at the value the floor modules left, and
        the kernel's BUS_PORT is its default, read from an environment with no port), inside an attaching class's setUp
        (peers off, client-only, a port of the test's own with BUS_PORT patched to match), after its tearDown, after its
        cleanups with a peers value a shell might have left (the three names and BUS_PORT put back), and after a
        subclass setUp that raises past the writes. Client-only is compared with the floor's value, not with unset: this
        conftest floors none, and a conftest carrying upstream's floor line (their PR 1848, which fork PR #875 folds)
        sets "1" for the run, which the module must neither change nor leave changed (the reviewer's ruling of round 1
        on fork PR #894). Before 2026-09-18 the import alone wrote peers "0"; before 2026-09-22 it wrote the port and
        client-only, the two names the real bus of fork PR #813's CI inherited; before review round 1 the raising setUp
        left the 0 behind (the restore was a tearDown)."""
        self._assert_the_module_leaves_the_trio_as_the_floor_left_it(self._tunnels_probe())

    def test_the_import_probe_holds_under_a_conftest_that_floors_client_only(self):
        """The probe above with tests/conftest.py replaced, in the child, by a copy carrying upstream's floor line right
        after the hermetic marker (their PR 1848, which fork PR #875 folds): the floor modules leave client-only "1",
        and the import, the setUp's cleanups and a raising setUp leave it "1" too. Held by execution so the probe is
        known to hold under that conftest before fork PR #875 lands (the reviewer's ruling of round 1 on fork PR #894);
        before round 2 the probe expected client-only unset after the import and red under it."""
        out = self._tunnels_probe(conftest_text=_conftest_with_the_client_only_floor())
        self.assertEqual(out["before_import"]["ROMP_POSTAL_CLIENT_ONLY"], "1", "the copy of conftest floors client-only for the run")
        self._assert_the_module_leaves_the_trio_as_the_floor_left_it(out)

    def _assert_the_module_leaves_the_trio_as_the_floor_left_it(self, out):
        floor = out["before_import"]["ROMP_POSTAL_CLIENT_ONLY"]
        self.assertEqual(out["after_import"], {"ROMP_POSTAL_PORT": None, "ROMP_POSTAL_CLIENT_ONLY": floor, "ROMP_POSTAL_PEERS": None},
                         "importing the module writes no leg of the trio, client-only left at the floor's value %r (a write at import "
                         "holds for every child of every test in the process)" % (floor,))
        self.assertEqual(out["in_setup"]["ROMP_POSTAL_PEERS"], "0", "an attaching class's setUp turns peers off for its test")
        self.assertEqual(out["in_setup"]["ROMP_POSTAL_CLIENT_ONLY"], "1", "...and client-only on")
        self.assertTrue((out["in_setup"]["ROMP_POSTAL_PORT"] or "").isdigit(), "...and a port of the test's own: %r" % out["in_setup"])
        self.assertNotEqual(out["in_setup"]["ROMP_POSTAL_PORT"], str(out["bus_port_at_import"]), "...not the kernel's import-time default")
        self.assertTrue(out["bus_port_in_setup_matches"], "the kernel's BUS_PORT, read at import, is patched to the test's port")
        self.assertEqual(out["after_teardown"]["ROMP_POSTAL_PEERS"], "0", "the value is still set when tearDown returns: the subclass's detach there reads it, and the restore is a cleanup, which runs after tearDown")
        self.assertEqual(out["after_cleanups"], {"ROMP_POSTAL_PORT": None, "ROMP_POSTAL_CLIENT_ONLY": floor, "ROMP_POSTAL_PEERS": "1"},
                         "...and the cleanup restores what it found: the shell's peers value, no port, client-only at the floor's value")
        self.assertEqual(out["bus_port_after_cleanups"], out["bus_port_at_import"], "...and BUS_PORT")
        self.assertEqual(out["setup_raise_errors"], 1, "the planted subclass setUp raised, as an error on the case")
        self.assertEqual(out["after_setup_raise"], {"ROMP_POSTAL_PORT": None, "ROMP_POSTAL_CLIENT_ONLY": floor, "ROMP_POSTAL_PEERS": "1"},
                         "a subclass setUp that raises after the writes still restores them: a tearDown restore is skipped on that path (review round 1, 2026-09-18)")
        self.assertEqual(out["bus_port_after_setup_raise"], out["bus_port_at_import"])

    def test_the_import_probe_reds_on_a_planted_module_level_write_of_any_leg(self):
        """The same planted writes, run: a copy of the module with `os.environ["ROMP_POSTAL_PEERS"] = "0"` restored
        before the load reports "0" after the import, so does one with `os.environ.update(ROMP_POSTAL_PEERS="0")` there
        (the shape review round 2 found the static scan blind to), and a copy with the port written back before the
        load reports the port after the import AND a kernel whose BUS_PORT is that port (the import-time read, which is
        why the leak's child could bind it), so the probe is known to see the leaks it guards against (review rounds 1
        and 2, 2026-09-18; the port 2026-09-22). Client-only is planted as "on", a value no floor module sets, since the
        probe compares it with the floor's value: planted as "1" it would be invisible under a conftest that floors "1"
        (upstream's PR 1848, which fork PR #875 folds). A module-level write of the floor's own value changes nothing
        the probe can read; the census pin reads that write statically. The comparison itself is run over a planted
        client-only write alone, under the real conftest and under a copy carrying the floor line: the check the two
        probe tests above share must red on it at the import, which it cannot if its floor value is read after the
        import (the verifier's mutation on round 2 of fork PR #894, under which the whole module passed)."""
        for label, lines in (("assignment", 'os.environ["ROMP_POSTAL_PEERS"] = "0"\n'),
                             ("update", 'os.environ.update(ROMP_POSTAL_PEERS="0")\n'),
                             ("class body", 'class _Planted:\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n')):    # runs at import (the fixup of 2026-09-22)
            out = self._tunnels_probe(_plant(_tunnels_source(), lines))
            self.assertEqual(out["after_import"]["ROMP_POSTAL_PEERS"], "0", "%s: the probe sees a module-level write at import" % label)
            self.assertEqual(out["after_cleanups"]["ROMP_POSTAL_PEERS"], "1", "%s: the planted copy's own cleanup still restores the shell's value" % label)
        out = self._tunnels_probe(_plant(_tunnels_source(), 'os.environ["ROMP_POSTAL_PORT"] = "45678"\nos.environ["ROMP_POSTAL_CLIENT_ONLY"] = "on"\n'))
        self.assertEqual(out["after_import"]["ROMP_POSTAL_PORT"], "45678", "the probe sees the port written at import")
        self.assertNotEqual(out["before_import"]["ROMP_POSTAL_CLIENT_ONLY"], "on", "the planted client-only value is not the floor's, so the write is visible")
        self.assertEqual(out["after_import"]["ROMP_POSTAL_CLIENT_ONLY"], "on", "the probe sees client-only written at import")
        self.assertEqual(out["bus_port_at_import"], 45678, "...and the kernel read it at import: the bus a stray revive would start binds it")
        self.assertEqual(out["after_cleanups"]["ROMP_POSTAL_PORT"], "45678", "the planted copy's cleanup puts the import-time value back, which is the leak")
        planted = _plant(_tunnels_source(), 'os.environ["ROMP_POSTAL_CLIENT_ONLY"] = "on"\n')
        for label, conftest_text in (("the real conftest", None), ("a conftest that floors client-only", _conftest_with_the_client_only_floor())):
            out = self._tunnels_probe(planted, conftest_text=conftest_text)
            if conftest_text is not None:
                self.assertEqual(out["before_import"]["ROMP_POSTAL_CLIENT_ONLY"], "1", "the copy of conftest floors client-only")
            self.assertNotEqual(out["before_import"]["ROMP_POSTAL_CLIENT_ONLY"], "on", "%s: the floor's value is not the planted one" % label)
            self.assertEqual(out["after_import"]["ROMP_POSTAL_CLIENT_ONLY"], "on", "%s: the planted write moves client-only at the import" % label)
            with self.assertRaises(AssertionError) as caught:
                self._assert_the_module_leaves_the_trio_as_the_floor_left_it(out)
            self.assertIn("importing the module writes no leg of the trio", str(caught.exception),
                          "%s: the shared check reds on the import leg, its floor value read before the import" % label)

    def test_the_trio_stubs_the_revive_road_and_its_cleanup_fails_on_a_revive_and_puts_the_road_back(self):
        """_PostalTrio's second guard, run in a fresh interpreter (_REVIVE_PROBE) on a TunnelConcierge case of its own, so
        the import probe's after_cleanups and after_setup_raise stay independent of it: after the trio's setUp a call
        of km._revive_postal_bus() lands in the stub's recorder (the test's port, once) and runs no ensure; the cleanups
        then return False, because the recorder check in _restore_bus fired on that revive and no other check did; and
        km._ensure_postal_bus is the import-time function again after them. Each of the three pieces the round-1 review
        could delete with no test failing reds here: the stub deleted (M1: the revive runs the real ensure in the probe
        child, with the trio's environment, and client-only makes that ensure start nothing: it pings the test's own
        port and returns, so the recorder is empty and the cleanups succeed), the road's restore dropped from
        _restore_bus (M2: the stub is still the road after the cleanups), and the recorder check disabled (M3: the
        cleanups succeed with the recorder full). The placement check reds on M1 and M2 as well, from the assignments."""
        env = dict(os.environ)
        env.pop("ROMP_POSTAL_PEERS", None)
        res = subprocess.run([sys.executable, "-c", _REVIVE_PROBE, HERE], capture_output=True, text=True, timeout=180, env=env, cwd=HERE)
        self.assertEqual(res.returncode, 0, res.stderr[-2000:])
        out = json.loads(res.stdout.strip().splitlines()[-1])
        self.assertEqual(out["revives"], [out["port"]], "a revive after the setUp lands in the stub's recorder, the test's port, once, "
                                                        "and runs no ensure")
        self.assertIs(out["cleanups_succeeded"], False, "the cleanups fail on a revive the test did not expect")
        self.assertEqual(len(out["fired"]), 1, "...because one check fired in them: %r" % out["fired"])
        self.assertIn("a refused bus call revived the bus from this test", out["fired"][0], "...the recorder check in _restore_bus")
        self.assertTrue(out["road_restored"], "the cleanups put the import-time _ensure_postal_bus back, the check's failure notwithstanding")
        self.assertTrue(out["stubbed_in_setup"], "the trio's setUp replaced the kernel's _ensure_postal_bus for the test")

    def _guard_test(self, src=None):
        """tests/test_kernel.py's PostalPeerTunnels.test_notify_bus_peer_is_guarded as a parsed function node, or the same
        test in `src`, a module text that defines the class (a planted copy of it; _guard_class_source); the pins below read
        code, never text: a statement commented out is not in the tree."""
        if src is None:
            src = open(os.path.join(HERE, "test_kernel.py"), encoding="utf-8", errors="replace").read()
        cls = [c for c in ast.parse(src).body if isinstance(c, ast.ClassDef) and c.name == "PostalPeerTunnels"]
        self.assertEqual(len(cls), 1, "tests/test_kernel.py defines PostalPeerTunnels once")
        fns = [f for f in cls[0].body if isinstance(f, ast.FunctionDef) and f.name == "test_notify_bus_peer_is_guarded"]
        self.assertEqual(len(fns), 1, "PostalPeerTunnels defines test_notify_bus_peer_is_guarded once")
        return fns[0]

    def _guard_class_source(self):
        """The text of tests/test_kernel.py's PostalPeerTunnels class, its decorators included: parsed alone it defines the
        class and the guard test at the same shape, so the plants below edit a copy of it and hand it to _guard_shape."""
        src = open(os.path.join(HERE, "test_kernel.py"), encoding="utf-8", errors="replace").read()
        cls = [c for c in ast.parse(src).body if isinstance(c, ast.ClassDef) and c.name == "PostalPeerTunnels"]
        self.assertEqual(len(cls), 1, "tests/test_kernel.py defines PostalPeerTunnels once")
        first = min([cls[0].lineno] + [d.lineno for d in cls[0].decorator_list])
        return "".join(src.splitlines(keepends=True)[first - 1:cls[0].end_lineno])

    def _guard_shape(self, src=None):
        """The guard test's parts (in tests/test_kernel.py, or in `src`, a planted copy of its class), each required as a
        statement that RUNS on a run of the test that passes (_executed): among the statements of the test that run
        (_run_prefix) before the try that makes the notify call, in that try's finally, after the try, or in the body and
        the finally of the wrapper's own try. A statement under an if, in a loop, in a def the test never calls, in the
        body of a try that has an except clause, or after a statement that can end the run (a return, a raise, a skip or an
        exit: _ends_the_run) satisfies nothing here; and the test is undecorated and no generator, since a skip decorator,
        or a yield anywhere in it, passes a run in which none of its statements ran.
        The wrapper's body is that try alone, the real revive's call in its body and the Event's set in its finally; the
        wrapper, the fake and each road carry no decorator, which would bind the def's name to whatever it returns. The
        window, every statement that runs in the test's frame from the first of the rebind and the install to the wait
        (in the finally, each statement before the wait that runs, a statement of a try there included: _executed),
        holds the parts alone: the install and the rebind, the saved mapping, the trio, one notify statement (a
        self.assert... call that makes one other call, a lambda's body included, and holds no comprehension or
        generator expression, whose element runs once per item, a lambda's body again included: _repeats; that the
        call is km._notify_bus_peer follows from the tries rule, as the comment at the window rule says), a
        self.assert... statement
        that calls nothing else (fork PR #875's, inside the try where upstream's text has it), km.BUS_PORT put back from
        a name, and the wait, a statement that calls nothing else. A second notify, another kernel call, a process or a
        thread started in the window or the wrapper kicks a revive, a notify or an ensure that the one wait does not
        cover (the verifier's second notify and Popen of the postal service inside the try, on round 2's twenty-fourth
        commit of fork PR #894, passed every rule; the executed pin saw the second, and the first on none of the
        verifier's eight runs. The re-verifier's notify run twice by a list comprehension, second notify in the wait
        statement's own argument and second notify in a try of the finally that holds the wait, on the twenty-fifth,
        passed a rule that read the call nodes of the direct statements, and the executed pin on each run made; with the
        ensure's run delayed by 0.05 s in a scratch kernel the first reddened the executed pin: the child of the revive
        it kicked first forked after the test and dialled the fixed port).
        The environment's put-back is read by the mapping it restores from: one for statement in the finally, after the
        wait, over that mapping's items(), putting each name back and popping one that was unset, and nothing else; the
        mapping made before the trio as {name: os.environ.get(name) for name in <the trio's three names>}.
        The safe side is read over the whole function, every statement, run or not, nested defs included, so a conditional
        or early put-back still reds: no statement names reflection in any reference form, called, aliased, passed or
        imported (_reflective: setattr and the verifier's tuple target of round 2's third commit on fork PR #894 passed a
        scan that read single-target assignments alone, and the verifier's `_s = setattr`, functools.partial(setattr, ...)
        and `_g = getattr` on the fourth commit a scan that read a reflective call by its bare name alone); none binds the
        names km or os (_name_binds, a parameter of a nested def or lambda included); the environment is named only in
        os.environ.get reads, in the trio and in the restore (_environ_mentions); and no statement binds or deletes an
        attribute, whatever its name, on any object, in any binding form (_attribute_binds), other than the four put-ins
        and put-backs and the assignments of km.BUS_PORT, so no assertion method or Event method is replaced either.
        Every name the parts are read by holds one value (the verifier's five one-line plants on the fourth commit
        rebound real_run or real_revive, cleared the saved mapping, set the Event before the call or rebound it, and
        every pin passed): the kept real run and real revive, the Event, the wait's result, the fake, the wrapper and
        each road def, the saved mapping, the road's list, the threading module and the test case (self) are each bound
        ONCE in the whole test, parameters of nested defs and lambdas included, by the statement the parts are read from
        (_name_binds), and each but self is read only where the parts read it (_name_loads: the real run in the unfake
        and in a road's call, the real revive in the unwrap and the wrapper's call, the Event in the wrapper's set and
        the wait, and so on); the road's list is made by an empty list literal. The plant test holds each rule of this
        pin (a decorator on each of the parts' defs, and a statement at each end of each stretch of the window and in
        each argument place the window reads, among them), each binding form _name_binds reads, each half of each of
        those names' reads but self's (the kept real
        run's calls in the road and the kept real revive's in the wrapper among them, and each name bound to another
        name after the try), each kind of comprehension _REPEATS lists and a comprehension in a lambda's body, and each
        identifier the reflection and environment readers list, in each reference form its reader reads, to a plant of
        its own that the pin reds with that rule's message; the window rule's lower bound on the notify statement's one
        call to a plant it passes; and, where another reading of the window refuses the same plants, the lines the
        message names. NOT READ by the name rule: the fake's own list (the plants read it; nothing
        the pin guarantees rests on it, and fork PR #875's assertion reads it); the names local to a nested def (the
        fake's argv and text), whose behaviour the pin on the fake runs; and the restore loop's two names and the saved
        mapping's comprehension name, bound and read inside texts the pin requires exactly.
        NOT READ, each with what sees it instead: a put-back made by code the test calls but does not contain (a helper of
        the module, setUp or tearDown), code outside the test that rebinds what it names (module-level code of
        tests/test_kernel.py, a fixture), a put-back through a module _reflective does not name (a pickle or marshal
        payload, ctypes), and the class's own decorators. An early put-back of the fake by any of them lets the revive's
        real ensure child start, which the executed pin's spy records (the verifier's setattr mutants reddened it there);
        of the revive, the kick runs the real revive, the Event is never set and the guard test's own wait fails; of the
        Event, a wait that returns before the revive ends is seen by the executed pin only on a run where the revive is
        still running at the put-back; of the environment, nothing sees it while the fake holds, since every
        postal-service call is then answered in the process, so the restore's place after the wait is a second belt. A
        skip or an exit from a callee or from the class reds the executed pin, which requires the child run to pass.
        NOT READ either: what else the test starts outside the window and the wrapper. Before the window or after the
        wait, a statement that kicks a revive, a notify or an ensure passes this pin and the guard test (the
        re-verifier's three on round 2's fifth commit: the real revive started on a thread through km.threading before
        the rebind, a second notify after the try, and km._ensure_postal_bus() called after the try). The executed pin
        sees each that starts an ensure child, by the child's spawn: its spy records a Popen of the postal service in the process that makes it,
        whichever thread makes it, before the fork, and the pin has read that record since round 2's twenty-seventh
        commit. Before it the pin read a child's exit and its dial of the fixed port alone, which can come after the
        run's end for a child a thread forks as the run ends. The fake answered the first one's ensure on none of the
        runs made, at the test's own pace or with the ensure's run delayed by 0.02 s or 0.05 s in a scratch kernel,
        which puts the install before that thread reaches subprocess.run: its revive holds the revive's single-flight
        flag, so the notify's kick joins it, the wrapper sets the Event at once, and the put-back comes before the delayed
        thread reaches the run; its child then forks after the restore, with the restored environment, and dials the
        fixed port (on each of the re-verifier's six delayed runs on the twenty-fifth commit, read three seconds after the
        run's end; at the run's end, where the executed pin reads, two of the three delayed by 0.05 s held the spawn
        alone, a record the pin did not then read). The
        fake's and the road's bodies, which run in the revive's thread inside the window, are not read for a kick
        either: the pin on the fake runs them over its argv shapes with the kernel as a namespace that holds the
        subprocess module alone, so a kick through any other name of the kernel raises there, and the executed pin runs
        them in the guard test's window, where a real ensure child a kick starts is recorded at its spawn. Nor is code
        that a part of the window runs without a call of its own: a callable handed to an assertion method that calls it
        (self.assertRaises(Exception, km._ensure_postal_bus) in the try), and a method (a truth test, a comparison) of an
        object the test made before the window and handed to the notify or to an assertion there, or to the wait as its
        timeout (Event.wait compares a timeout with 0 while the Event is not set). The executed pin
        records a real ensure child such code starts, and sees a second revive it kicks on a thread only on a run where
        that revive reaches the real run after the put-back (the verifier's second notify inside the try, which kicks the
        same second revive, passed the executed pin on each of eight runs). Nor is the port the notify dials: the pin
        lets a plain assignment of km.BUS_PORT stand before the window and reads no value one assigns there, so the
        test's own km.BUS_PORT = 1 rewritten to another port, or a second assignment before the window (km.BUS_PORT = 2
        before the rebind, the re-verifier's on round 2's twenty-seventh commit), passes it. The executed pin sees both:
        it requires the test process's refused dial to BUS_PORT 1, which a notify that dials another port does not make,
        the fixed port included (its spy refuses that connect before it is made), and it reds on that check on each of
        the two plants. The plant test holds a plant of each kind named here (the three, a kick in the fake's body, the
        kernel's ensure handed to assertRaises, two such objects, one handed to the notify and one to the wait, and the
        port the notify dials changed in each of the two ways) as one this pin passes.
        Returns what the pin on the fake's behaviour and the plants need."""
        fn = self._guard_test(src)
        self.assertEqual(fn.decorator_list, [], "the guard test carries no decorator: a skip or an expected failure passes a run that never reached its statements")
        self.assertEqual([n.lineno for s in fn.body for n in _runs_with(s) if isinstance(n, (ast.Yield, ast.YieldFrom))], [],
                         "the guard test is no generator: called, a generator runs none of its statements, and the run still passes")
        top = _run_prefix(fn.body)
        tries = [i for i, s in enumerate(top) if isinstance(s, ast.Try) and not s.handlers
                 and any(_dotted(c.func) == ["km", "_notify_bus_peer"] for st in _executed(s.body) for c in _own_calls(st))]
        self.assertEqual(len(tries), 1, "the notify call runs in one try with no except clause, among the statements of the test that run")
        before, final, after = top[:tries[0]], _executed(top[tries[0]].finalbody), top[tries[0] + 1:]
        defs = {s.name: i for i, s in enumerate(before) if isinstance(s, ast.FunctionDef)}
        # the trio, set before the call
        trio_at = [i for i, s in enumerate(before) if _call_stmt(s, ["os", "environ", "update"])]
        self.assertEqual(len(trio_at), 1, "the trio is set by one os.environ.update statement that runs before the call")
        trio = [before[trio_at[0]].value]
        self.assertEqual((trio[0].args, sorted((k.arg, ast.unparse(k.value)) for k in trio[0].keywords)),
                         ([], [("ROMP_POSTAL_CLIENT_ONLY", "'1'"), ("ROMP_POSTAL_PEERS", "'0'"), ("ROMP_POSTAL_PORT", "'1'")]),
                         "client-only with peers off and a port nothing can bind")
        # the wrap: the real revive kept, a wrapper of the test's own, the revive rebound to it before the call
        kept_revive = _names_bound(before, ["km", "_revive_postal_bus"])
        self.assertEqual(len(kept_revive), 1, "the real revive is kept in a name before the call")
        events = _names_bound(before, ("call", ["threading", "Event"]))
        self.assertEqual(len(events), 1, "one Event is made before the call")
        event = events[0][1]
        rebind = [i for i, s in enumerate(before) if _assign_to(s, ["km", "_revive_postal_bus"])]
        self.assertEqual(len(rebind), 1, "km._revive_postal_bus is rebound by one statement that runs before the call")
        wrapper = before[rebind[0]].value
        self.assertTrue(isinstance(wrapper, ast.Name) and defs.get(wrapper.id, len(before)) < rebind[0] and kept_revive[0][0] < rebind[0],
                        "...to a function the test defines first, after keeping the real revive")
        self.assertEqual([ast.unparse(s) for s in before[defs[wrapper.id]].body],
                         [ast.unparse(ast.parse("try:\n    %s()\nfinally:\n    %s.set()" % (kept_revive[0][1], event)).body[0])],
                         "the wrapper runs the real revive in a try whose finally sets the Event (%s), whatever the revive does, and runs "
                         "nothing else: a kick in the wrapper starts what the one wait does not cover" % event)
        # the scoped fake: the real run kept, a fake of the test's own taking (*a, **kw), installed before the call
        kept_run = _names_bound(before, ["km", "subprocess", "run"])
        self.assertEqual(len(kept_run), 1, "the real subprocess.run is kept in a name before the call")
        install = [i for i, s in enumerate(before) if _assign_to(s, ["km", "subprocess", "run"])]
        self.assertEqual(len(install), 1, "km.subprocess.run is replaced by one statement that runs before the call: the fake holds from the start of the window")
        fake = before[install[0]].value
        self.assertTrue(isinstance(fake, ast.Name) and defs.get(fake.id, len(before)) < install[0] and kept_run[0][0] < install[0],
                        "...by a function the test defines first, after keeping the real run")
        sig = before[defs[fake.id]].args
        self.assertTrue(sig.vararg and sig.kwarg and not (sig.posonlyargs or sig.args or sig.kwonlyargs),
                        "the fake takes (*a, **kw): a call that passes the argv by keyword, or anything else, reaches it")
        # the finally: the wait, then the fake, the revive and the environment put back
        waits = [i for i, s in enumerate(final) if isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name)
                 and isinstance(s.value, ast.Call) and _dotted(s.value.func) == [event, "wait"]]
        self.assertEqual(len(waits), 1, "the finally waits on the Event (%s) once, in a statement that runs, keeping the result" % event)
        wait = waits[0]
        ended = final[wait].targets[0].id
        unfake = [i for i, s in enumerate(final) if _assign_to(s, ["km", "subprocess", "run"]) and _dotted(s.value) == [kept_run[0][1]]]
        self.assertEqual(len(unfake), 1, "the finally puts the real run back")
        self.assertLess(wait, unfake[0], "...after the wait: every call the revive makes goes through the fake")
        unwrap = [i for i, s in enumerate(final) if _assign_to(s, ["km", "_revive_postal_bus"]) and _dotted(s.value) == [kept_revive[0][1]]]
        self.assertEqual(len(unwrap), 1, "the finally puts the real revive back")
        restores = [i for i, s in enumerate(final) if _environ_writes(s)]
        self.assertTrue(restores, "the finally restores the trio")
        self.assertLess(wait, min(restores), "...after the wait: the revive's calls run under the trio")
        # the environment's put-back, read by the mapping it restores from: one for statement of the finally puts each of
        # the trio's names back from a mapping made before the trio, popping a name that was unset, and does nothing else
        loops = [i for i, s in enumerate(final) if isinstance(s, ast.For) and isinstance(s.iter, ast.Call) and not (s.iter.args or s.iter.keywords)
                 and isinstance(s.iter.func, ast.Attribute) and s.iter.func.attr == "items" and isinstance(s.iter.func.value, ast.Name)]
        self.assertEqual(len(loops), 1, "the finally restores the environment in one for statement over a saved mapping's items()")
        loop = final[loops[0]]
        env_saved = loop.iter.func.value.id
        elts = loop.target.elts if isinstance(loop.target, ast.Tuple) else []
        pair = [e.id for e in elts if isinstance(e, ast.Name)]
        self.assertTrue(len(pair) == len(elts) == 2 and pair[0] != pair[1], "the restore loop binds two names, a name and its saved value")
        restore_text = ("for {k}, {v} in {m}.items():\n    if {v} is None:\n        os.environ.pop({k}, None)\n    else:\n        os.environ[{k}] = {v}\n"
                        .format(k=pair[0], v=pair[1], m=env_saved))
        self.assertEqual(ast.unparse(loop), ast.unparse(ast.parse(restore_text).body[0]),
                         "the restore puts each name back from %s, popping one that was unset, and does nothing else" % env_saved)
        made = [i for i, s in enumerate(before) if isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name)
                and s.targets[0].id == env_saved]
        self.assertEqual(len(made), 1, "the mapping the restore reads (%s) is made by one statement that runs before the call" % env_saved)
        comp = before[made[0]].value
        gen = comp.generators[0] if isinstance(comp, ast.DictComp) and len(comp.generators) == 1 else None
        q = gen.target.id if gen is not None and isinstance(gen.target, ast.Name) and not gen.ifs and not gen.is_async else None
        keys = [e.value for e in gen.iter.elts if isinstance(e, ast.Constant)] if q and isinstance(gen.iter, (ast.Tuple, ast.List)) else []
        self.assertTrue(q is not None and isinstance(comp.key, ast.Name) and comp.key.id == q and ast.unparse(comp.value) == "os.environ.get(%s)" % q
                        and len(keys) == len(gen.iter.elts) and sorted(keys) == sorted(k.arg for k in trio[0].keywords),
                        "%s is made as {name: os.environ.get(name) for name in <the trio's three names>}" % env_saved)
        self.assertLess(made[0], trio_at[0], "...before the trio is set")
        # the safe side, over every statement of the test, run or not, nested defs included
        self.assertEqual([n.lineno for n in ast.walk(fn) if _reflective(n)], [],
                         "no statement of the test names reflection, in any reference form (called, aliased, passed or imported): what it binds "
                         "would be decided at run time")
        self.assertEqual([n.lineno for n in _name_binds(fn, ("km", "os"))], [],
                         "no statement of the test binds the names km or os: every km and os it writes through is the kernel module and the os module")
        gets = {id(c.func.value) for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "get"}
        where_writes_go = {id(n) for s in (trio[0], loop) for n in ast.walk(s)}
        self.assertEqual([n.lineno for n in _environ_mentions(fn) if id(n) not in gets and id(n) not in where_writes_go], [],
                         "the test names the environment only in os.environ.get reads, in the trio and in the restore after the wait")
        allowed = [before[install[0]].targets[0], final[unfake[0]].targets[0], before[rebind[0]].targets[0], final[unwrap[0]].targets[0]]
        allowed += [s.targets[0] for s in ast.walk(fn) if isinstance(s, ast.Assign) and len(s.targets) == 1 and _dotted(s.targets[0]) == ["km", "BUS_PORT"]]
        self.assertEqual([(n.lineno, n.attr) for n in _attribute_binds(fn) if not any(n is a for a in allowed)], [],
                         "no other statement of the test binds or deletes an attribute, on any object, in any binding form (the four put-ins and "
                         "put-backs and the assignments of km.BUS_PORT aside): not run, subprocess or _revive_postal_bus, an assertion method or "
                         "an Event's method")
        # after the try: the wait's result, and the one assertion on the fake
        asserted = [s.value for s in after if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)]
        self.assertTrue(any(_dotted(c.func) == ["self", "assertTrue"] and c.args and _dotted(c.args[0]) == [ended] for c in asserted),
                        "after the try the wait's result (%s) is asserted: a revive never kicked, or never ended, fails the test" % ended)
        roads = [s for s in before if isinstance(s, ast.FunctionDef)
                 and any(isinstance(c, ast.Call) and _dotted(c.func) == [kept_run[0][1]] for c in ast.walk(s))]
        fake_calls = {c.func.id for c in ast.walk(before[defs[fake.id]]) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        self.assertTrue(roads and all(r.name == fake.id or r.name in fake_calls for r in roads),
                        "the real run is called only in a def of the test that the fake is or calls by name: the road from the fake to the real run")
        on_every_road = set.intersection(*[{c.func.value.id for c in ast.walk(r) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                                            and c.func.attr == "append" and isinstance(c.func.value, ast.Name)} for r in roads])
        reached = sorted({c.args[0].id for c in asserted if _dotted(c.func) == ["self", "assertEqual"] and len(c.args) >= 2
                          and isinstance(c.args[0], ast.Name) and isinstance(c.args[1], ast.List) and not c.args[1].elts} & on_every_road)
        self.assertEqual(len(reached), 1, "after the try one list is asserted empty that every road to the real run appends to: the postal-service "
                                          "calls that reached it (a list asserted empty beside it, fork PR #875's, is not what this reads)")
        # every name the parts above are read by holds one value: bound once in the whole test, by the statement read above,
        # and read only where the parts read it (the verifier's five one-line plants on round 2's fourth commit of fork PR
        # #894 rebound a kept name, cleared the saved mapping, and set the Event early or rebound it, and every pin passed)
        fake_def, wrapper_def = before[defs[fake.id]], before[defs[wrapper.id]]
        # the parts' defs carry no decorator: the rules above read the wrapper, the fake and each road by the body and the
        # signature of the def, and a decorator binds the def's name to whatever it returns (the re-verifier's
        # decorators on round 2's twenty-sixth commit of fork PR #894, among them a second notify run after the wrapper
        # and the fake replaced by the real run, passed every pin)
        self.assertEqual([(d.name, d.decorator_list[0].lineno) for d in [wrapper_def, fake_def] + [r for r in roads if r is not fake_def]
                          if d.decorator_list], [],
                         "the wrapper, the fake and each road carry no decorator: the pin reads each by its def's body and signature, and a "
                         "decorator binds the name to whatever it returns")
        wrapper_tries = [t for t in _executed(wrapper_def.body) if isinstance(t, ast.Try) and not t.handlers]
        list_made = [(s, n) for s in before if isinstance(s, ast.Assign) for n in ast.walk(s.targets[0])
                     if isinstance(n, ast.Name) and n.id == reached[0] and isinstance(n.ctx, ast.Store)]
        threading_import = [a for s in before if isinstance(s, ast.Import) for a in s.names if a.name == "threading" and a.asname in (None, "threading")]
        held = [  # (what the parts read it as, the name, the one node that may bind it, the reads the parts make of it; None: any read)
            ("the kept real run", kept_run[0][1], before[kept_run[0][0]].targets[0],
             [final[unfake[0]].value] + [c.func for r in roads for c in _calls_of(r, kept_run[0][1])]),
            ("the kept real revive", kept_revive[0][1], before[kept_revive[0][0]].targets[0],
             [final[unwrap[0]].value] + [c.func for c in _calls_of(wrapper_def, kept_revive[0][1])]),
            ("the Event", event, before[events[0][0]].targets[0],
             [final[wait].value.func.value] + [s.value.func.value for t in wrapper_tries for s in _executed(t.finalbody) if _call_stmt(s, [event, "set"])]),
            ("the wait's result", ended, final[wait].targets[0],
             [c.args[0] for c in asserted if _dotted(c.func) == ["self", "assertTrue"] and c.args and _dotted(c.args[0]) == [ended]]),
            ("the fake", fake.id, fake_def, [fake]),
            ("the wrapper", wrapper.id, wrapper_def, [wrapper]),
            ("the saved environment", env_saved, before[made[0]].targets[0], [loop.iter.func.value]),
            ("the road's list", reached[0], list_made[0][1] if len(list_made) == 1 else None,
             [c.func.value for r in roads for c in ast.walk(r) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
              and c.func.attr == "append" and _dotted(c.func.value) == [reached[0]]]
             + [c.args[0] for c in asserted if _dotted(c.func) == ["self", "assertEqual"] and c.args and _dotted(c.args[0]) == [reached[0]]]),
            ("the threading module", "threading", threading_import[0] if threading_import else None, [before[events[0][0]].value.func.value]),
            ("the test case", "self", fn.args.args[0] if fn.args.args else None, None),
        ] + [("a road from the fake to the real run", r.name, r, [c.func for c in _calls_of(fake_def, r.name)]) for r in roads if r is not fake_def]
        faults = []
        for role, name, binding, reads in held:
            binds = _name_binds(fn, (name,))
            if binding is None or len(binds) != 1 or binds[0] is not binding:
                faults.append("%s (%s) is bound at lines %s, not once by the statement the parts are read from" % (role, name, [b.lineno for b in binds]))
            stray = sorted(n.lineno for n in _name_loads(fn, name) if reads is not None and not any(n is r for r in reads))
            if stray:
                faults.append("%s (%s) is read at lines %s, where the parts do not read it" % (role, name, stray))
        self.assertEqual(faults, [], "each name the pin reads the test's parts by holds one value: bound once, by the statement the parts are read "
                                     "from, and read only where they read it")
        made_empty = _bound_value(*list_made[0])
        self.assertTrue(isinstance(made_empty, ast.List) and not made_empty.elts,
                        "the road's list (%s) is made by an empty list literal: an object of another kind can compare equal to [] whatever the road "
                        "appends" % reached[0])
        # the window, from the first of the rebind and the install to the wait: in the test's frame nothing runs there but
        # the parts (the verifier's second notify and Popen of the postal service inside the try, on round 2's
        # twenty-fourth commit of fork PR #894, passed every rule above; a second revive kicked in the window is not the
        # one the wait waits on, and the revive is single-flight, so the wrapper of a kick that coalesces sets the Event
        # before the revive it joined has ended). Read by what runs, not by the call nodes of the direct statements (the
        # re-verifier's three on the twenty-fifth commit passed that reading: the notify run twice by a list comprehension,
        # a second notify in the wait statement's own argument, and one in a try of the finally that holds the wait): the
        # finally's statements that run before the wait, a nested try's among them (_executed), the wait statement's own
        # calls, and a comprehension or generator expression in the notify statement, whose element runs once per item.
        # In the try, every statement that makes a call is stray but the first notify statement (an assertion that makes
        # one call beside its own and holds no comprehension). No count of the notify statements and no check that the
        # one call is the notify is read beside this: on the twenty-sixth commit both were conjuncts no plant could red,
        # and the argument this comment gave for them was inexact (the re-verifier: with the check dropped, an assertion
        # on another kernel call counted as a notify statement, and the count reddened, not a stray statement). The
        # tries rule above found the try by a notify call among its statements that run, so when nothing is stray the
        # statement that makes that call is the first notify statement, whose one call is then the notify (a try in the
        # try that holds the call is no assertion, and stray), and a second notify statement, whatever its one call, is
        # stray. Two other readings refuse the same plants as this one and differ from it only in the lines the message
        # names (the re-verifier's on the twenty-seventh commit: under either, every pin passed): the finally's stretch
        # read from its own statements alone, not the statements a try there runs, and the last notify statement
        # exempted in the first's place. A compound statement of the finally before the wait is stray itself, so reading
        # the statements a try there runs refuses nothing more, and of two notify statements one is stray whichever is
        # exempted. The plant test holds the lines this reading names: a try of the finally before the wait names its
        # own line and each line it runs, and a second notify statement after the test's own names the second. The one
        # call's lower bound is held there by a plant the pin passes: an assertion that calls nothing, before the notify
        # statement in the try (with the one call read as at most one, that assertion counts as the first notify
        # statement, and the test's own is stray).

        def beside(s):             # the calls an assertion statement makes beside its own, a lambda's body included; None: no assertion
            f = _dotted(s.value.func) if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) else None
            if not (f and len(f) == 2 and f[0] == "self" and f[1].startswith("assert")):
                return None
            return [c for c in ast.walk(s) if isinstance(c, ast.Call) and c is not s.value]
        notify_stmts = [s for s in top[tries[0]].body if beside(s) is not None and len(beside(s)) == 1 and not _repeats(s)]
        beside_wait = [c for c in ast.walk(final[wait]) if isinstance(c, ast.Call) and c is not final[wait].value]
        parts_before = (before[install[0]], before[rebind[0]], before[made[0]], before[trio_at[0]])
        stray = ([s.lineno for s in before[min(rebind[0], install[0]) + 1:] if not any(s is p for p in parts_before)]
                 + [s.lineno for s in top[tries[0]].body if not any(s is n for n in notify_stmts[:1]) and beside(s) != []]
                 + [s.lineno for s in final[:wait] if not (_assign_to(s, ["km", "BUS_PORT"]) and isinstance(s.value, ast.Name))]
                 + ([final[wait].lineno] if beside_wait else []))
        self.assertTrue(not stray,
                        "from the first of the rebind and the install to the wait nothing runs in the test's frame but the parts: the install, "
                        "the rebind, the saved mapping, the trio, one notify statement that calls nothing beside its assertion but the notify, "
                        "once (no comprehension or generator expression), an assertion that calls nothing else, km.BUS_PORT put back from a "
                        "name, and the wait, calling nothing else (notify statements: %d; other statements at lines %s): a second notify, "
                        "another kernel call, a process or a thread started there kicks what the one wait does not cover" % (len(notify_stmts), stray))
        notify = notify_stmts[0] if notify_stmts else None    # there when nothing is stray (the comment above); None only under a cut reading
        return {"fn": fn, "fake": fake.id, "real_run": kept_run[0][1], "reached": reached[0], "event": event, "ended": ended,
                "real_revive": kept_revive[0][1], "try": top[tries[0]], "install": before[install[0]], "wait": final[wait],
                "after": after, "wrapper": wrapper_def, "fake_def": fake_def, "saved_env": env_saved, "restore": loop,
                "saved_made": before[made[0]], "list_made": list_made[0][0], "trio_stmt": before[trio_at[0]],
                "roads": [r for r in roads if r is not fake_def], "rebind": before[rebind[0]], "notify": notify,
                "kept_revive": before[kept_revive[0][0]], "kept_run": before[kept_run[0][0]], "event_made": before[events[0][0]],
                "unfake": final[unfake[0]], "unwrap": final[unwrap[0]],
                "held": sorted((role, name) for role, name, _, reads in held if reads is not None)}

    def test_the_peer_notify_guard_test_runs_the_trio_the_wrap_the_wait_and_the_scoped_fake_as_statements_that_run(self):
        """Read by ast from tests/test_kernel.py's PostalPeerTunnels.test_notify_bus_peer_is_guarded, each part required as
        a statement that runs on a run of the test that passes, so none after a return, a raise, a skip or an exit and none
        in the body of a try with an except clause (_guard_shape; the reviewer's re-ruling of round 2 on fork PR #894): the
        trio, os.environ.update(ROMP_POSTAL_CLIENT_ONLY="1", ROMP_POSTAL_PEERS="0", ROMP_POSTAL_PORT="1"), set before the
        km._notify_bus_peer call (the refusal that kicks the bus revive on a thread); km._revive_postal_bus rebound
        before the call to a wrapper of the test's own whose body is a try that runs the real revive and whose finally
        sets an Event;
        km.subprocess.run replaced before the call by a fake of the test's own taking (*a, **kw); the call in a try whose
        finally waits on that Event, keeping the result, BEFORE it puts the fake and the environment back, and puts the
        real revive back; and, after the try, the wait's result asserted and one list asserted empty that the road from the
        fake to the real run appends to, the postal-service calls that reached the real run (another list asserted empty
        beside it, as fork PR #875's assertion will be once the two texts meet, is not what this reads). The environment
        goes back in one for statement over the mapping saved before the trio from os.environ.get of the trio's three
        names. The wrapper, the fake and the road carry no decorator. No other statement of the test, run or not, binds or
        deletes an attribute on any object in any binding form
        (km.BUS_PORT aside), binds km or os, names reflection in any reference form, or names the environment outside
        os.environ.get reads, the trio and the restore; from the first of the rebind and the install to the wait nothing
        runs in the test's frame but the parts, one notify statement among them; and every name the parts are read by
        (the kept real run and real
        revive, the Event, the wait's result, the fake, the wrapper, the road, the saved mapping, the road's list,
        threading and self) is bound once, by the statement the parts are read from, and read only where they read it
        (self excepted, read anywhere). What that leaves unread (a put-back made by code the test calls, and a kick
        outside the window, among others) is named in _guard_shape with what sees it, and the plant test below reds each
        rule on a plant of its own.
        Why the wait and the fake: with the test at its base text the restore won the race in every run, and the ensure's
        child, forked with the restored environment, which names no port, pinged the machine's fixed bus port (the
        verifier's plant in round 2); the fake answers the revive's ensure, so under this kernel no ensure child starts at
        all, and the wait keeps every call the revive makes inside the window the fake covers. The test asserts nothing
        about whether the revive runs the ensure, so it holds under upstream's PR 1848 and fork PR #875's gate as under
        this kernel. What this pin GUARANTEES is the shape, the weaker thing; what the fake does with each argv is run by
        the pin below it, and that no process of the test's run dials the fixed port or starts an ensure child by the
        executed pin after that."""
        self._guard_shape()

    def test_the_guard_pin_reds_on_a_part_that_never_runs_and_on_a_put_back_in_any_form(self):
        """THE PLANTS for the guard pin's readers (the verifier's three findings on round 2's third commit of fork PR #894):
        each is planted into a copy of the PostalPeerTunnels class (_guard_class_source, _plant_at) and read by
        _guard_shape, which must red with the message of the part it breaks. Parts that never run: a return between the
        try and the final assertions, and one in the finally between the wait and the put-backs (the verifier's two
        mutants, under which the guard test and all three pins passed), a raise of SkipTest, a skipTest call and an
        os._exit after the try, a conditional return before it, the wait in a try whose except clause catches what the
        call before it raises (int("planted"), no raise statement, so only the except-clause rule sees it), a return in
        the wrapper before its try, an except clause on the notify's try and on the wrapper's, a yield that never runs,
        and a skip decorator. Put-backs, planted right after the fake is installed or right before the wait: setattr and a
        tuple target (the verifier's two, which reddened only the executed pin), a chained, an augmented, an annotated and
        a starred assignment, a for and a with target, a del, the module through another name, the kernel's subprocess
        attribute rebound, the module's __dict__, vars(), object.__setattr__, mock.patch by a string, exec of a string,
        getattr, sys.modules, the revive by a tuple target, km rebound and bound by an import, os rebound; and for the
        environment a pop in the finally before the wait, a pop and a del before the call, |=, dict.__setitem__ on it, a
        name bound to it, os.environb, os.putenv, os.unsetenv, environ imported from os, os.environ rebound and
        mock.patch.dict. The road: the fake calling the real run itself reds, and so does a second road from the fake that
        records nothing. And fork PR #875's assertion kept beside this test's, after the try as the guard test's comment
        anticipates or inside the try where upstream's text has it, reads green with the road's list read (the verifier's
        third finding: the pin counted two lists asserted empty and reddened); with the fake's own list asserted in the
        road's place it reds.
        Since round 2's fifth commit (the verifier's two findings on the fourth), a name the parts are read by holding
        another value: the verifier's five, each of which passed every pin (real_run rebound to the fake, real_revive to
        the wrapper, the Event set before the call, the Event rebound to an object whose wait returns at once, the saved
        mapping cleared after the trio); one per name, so that name alone is what the plant breaks, the kept real run
        rebound to what subprocess.run holds, the kept real revive to a function that does nothing, the fake before it is
        installed, the wrapper before the revive is rebound to it, and the road; the wait's result rebound, the road's list
        emptied before its assertion, the real run handed to a thread outside the road, a nested def's parameter, the
        road's own parameter and the wrapper's own parameter hiding a kept name, threading and self rebound, a lambda's
        parameter named km, the road's list made by an object equal to any list, an assertion method and the Event's wait
        rebound; the restore rewritten, binding one name twice, or followed by an environment write, and the saved mapping
        made over two names, holding None, filtered by an if, or made after the trio. Reflection in every reference form:
        the verifier's three (setattr and getattr through another name, setattr handed to functools.partial), setattr and
        getattr imported under another name, builtins.setattr, operator's attrgetter and methodcaller by a string, a
        closure cell rewritten, a function's globals and a frame's locals.
        Since round 2's twenty-fourth commit (the re-verifier's findings on the fifth: a name's read half set to accept
        any read, a binding form dropped from _name_binds, or an identifier dropped from a reflection list, left every
        pin green), a plant for each such rule that only that rule refuses. For the read half of the kept real run and
        real revive, the wait's result, the wrapper, the fake, threading and the road: the real run handed to a thread
        through km.threading, outside the road, the real revive started on a thread outside the wrapper, the wait's
        result read outside its assertion, the wrapper called directly (which sets the Event before the notify, so the
        wait no longer covers the revive the notify kicks), the fake bound to another name, threading read to start the
        real revive before the rebind, and the road called outside the fake. For each binding form no plant above
        reaches: the Event rebound by a def, by a class statement, by an except clause's as name and by a match star,
        and declared nonlocal in a nested def; the wrapper rebound by an async def; the kept real run declared global
        and rebound by a match capture and by a match mapping's rest; the saved mapping deleted; os bound by a dotted
        import. For the import forms: environ imported under another name, which passed the pin before that commit,
        another object imported under a reflective name, and a dotted import whose last part is one. And every
        identifier of _REFLECTIVE_NAMES, _REFLECTIVE_ATTRS and _ENV_NAMES alone, in each reference form its reader reads
        (a bare name loaded, stored or deleted where the reader reads one, an attribute, an imported name, and for
        reflection an import's as name), from lists written out in the test and held equal to the readers' lists after
        the loop: an identifier dropped from a reader's list leaves its plants passing, and one added without a plant
        fails the equality.
        Since round 2's twenty-fifth commit (the verifier's findings on the twenty-fourth, and the same mutations
        carried to every rule of their kind: with a scoped read half read anywhere in the test, one of fifteen parts'
        rules removed, a bare-name reader narrowed to loads, or an import's as name read for _REFLECTIVE_NAMES alone,
        every pin passed; and a second notify, and a Popen of the postal service, inside the try passed every pin), a
        plant for each: every scoped read half read outside its part (the kept real run called outside the road, the
        kept real revive called before the rebind, the Event waited on before the rebind, the wait's result asserted a
        second time, the road's list appended to outside the road and asserted inside the try); each part under an if or
        made otherwise (the trio, and its values; the kept real revive and real run; the Event; the rebind and the
        install, each also to something that is no def of the test; the fake's signature in each of five ways; the real
        run put back before the wait; the real revive's put-back under an if; the restore dropped or under an if; the
        saved mapping under an if); a kick in the window for each clause of its rule (a second notify and a Popen of the
        postal service in the try, another kernel call between the rebind and the install and between the install and
        the trio; in the try an assertion that calls the kernel, a second notify statement, the notify statement calling
        a second notify, another method of the test case, a kernel call named like an assertion and the test case
        reached through an assertion method; before the wait another kernel call, km.BUS_PORT put back from one and a
        name bound from a name); and another kernel call in the wrapper's try.
        Since round 2's twenty-sixth commit (the re-verifier's findings on the twenty-fifth: the notify run twice by a list
        comprehension, a second notify in the wait statement's own argument, and one in a try of the finally that holds
        the wait passed the window rule and the executed pin; with the window read from the rebind alone, beside()
        reading no lambda's body, any assignment's value taken as a read of the kept real run, the kept real revive or
        the wrapper, or any items() call as the restore's read, every pin passed), a plant for each: the notify run twice
        by each kind of comprehension _REPEATS lists (a list, a set and a dict comprehension, and a generator
        expression), the two second notifies, the install moved before the rebind with another kernel call between them,
        an assertion in the try whose lambda runs a kernel call and raises, the saved mapping's items() read after the
        try, and every name the parts are read by, self aside, bound to another name after the try. The kinds and the
        names are written out in the test and held equal to _REPEATS and to the names _guard_shape reads after their
        loops. The kernel's ensure handed to assertRaises in the try, a kick that runs without a call node of its own, is
        held among the plants the pin passes, as its NOT READ list names it.
        Since round 2's twenty-seventh commit (the re-verifier's findings on the twenty-sixth: a decorator on the wrapper,
        the fake or the road passed every pin, and with a stretch of the window cut by one statement at one end, the
        wait's calls read from its positional arguments alone, or the notify statement's comprehension read from its
        first argument alone, every pin passed), a plant for each: a decorator on the wrapper that runs a second notify
        after it, one on the fake that replaces it with the real run, and one on the road that makes another kernel
        call; a kernel call right before the try, in the try before the notify statement, and as the finally's first
        statement; a second notify in the wait's timeout keyword; and the notify run twice by a comprehension in the
        notify statement's second argument and in a keyword argument. An object made before the window and handed to
        the wait as its timeout, whose comparison with 0 runs a second notify, is held among the plants the pin
        passes, as its NOT READ list names it.
        Since round 2's twenty-eighth commit (the re-verifier's on the twenty-seventh: under four of its mutants,
        _repeats reading no lambda's body, the notify statement's one call read as at most one, the finally's stretch
        read from its own statements alone, and the last notify statement exempted in the first's place, every pin
        passed; and a change of the port the notify dials passed the pin and no text named it): two harmless plants that
        _repeats reading a lambda's body alone refuses, a lambda holding a call-free list comprehension handed to the
        notify statement as its msg and one holding a call-free set comprehension as the notify's own argument;
        fork PR #875's assertion inside the try before the notify statement, held among the placements the pin passes;
        the lines the message names for a try of the finally before the wait and for a second notify statement after
        the test's own, the one thing those two readings change; and the test's own km.BUS_PORT = 1 rewritten to
        another port and a second assignment of it before the rebind, held among the plants the pin passes, as its NOT
        READ list names them."""
        cls_src = self._guard_class_source()
        shape = self._guard_shape(cls_src)
        stubbed = sorted({c.func.value.id for c in ast.walk(shape["fake_def"]) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                          and c.func.attr == "append" and isinstance(c.func.value, ast.Name)})
        self.assertEqual(len(stubbed), 1, "the fake records the calls it answers in one list of its own: %r" % stubbed)
        names = {k: shape[k] for k in ("event", "ended", "real_run", "real_revive", "fake", "reached", "saved_env")}
        names["stubbed"], names["wrapper"] = stubbed[0], shape["wrapper"].name
        self.assertEqual(len(shape["roads"]), 1, "one road from the fake to the real run, a def of its own")
        names["road"] = shape["roads"][0].name
        self.assertIsInstance(shape["fake_def"].body[-1], ast.Return, "the fake ends by returning what the road to the real run returns")
        names["fake_return"] = ast.unparse(shape["fake_def"].body[-1].value)
        road_assert = [s for s in shape["after"] if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) and s.value.args
                       and isinstance(s.value.args[0], ast.Name) and s.value.args[0].id == shape["reached"]]
        self.assertEqual(len(road_assert), 1, "the road's list is asserted once after the try")
        wrapper_try = [t for t in shape["wrapper"].body if isinstance(t, ast.Try)][0]
        anchors = {"after the try": (shape["after"][0], "before"), "after the wait": (shape["wait"], "after"),
                   "the wait": (shape["wait"], "replace"), "before the wait": (shape["wait"], "before"),
                   "before the try": (shape["try"], "before"), "in the try": (shape["try"].body[0], "after"),
                   "the wrapper's try": (wrapper_try, "before"),
                   "the def": (shape["fn"], "before"), "after the install": (shape["install"], "after"),
                   "the road's assertion": (road_assert[0], "replace"), "the fake's return": (shape["fake_def"].body[-1], "replace"),
                   "the notify try's clauses": (shape["try"].body[-1], "after", shape["try"].col_offset),
                   "the wrapper try's clauses": (wrapper_try.body[-1], "after", wrapper_try.col_offset),
                   "the restore": (shape["restore"], "replace"), "after the restore": (shape["restore"], "after"),
                   "the saved mapping": (shape["saved_made"], "replace"), "the road's list": (shape["list_made"], "replace"),
                   "before the install": (shape["install"], "before"), "before the rebind": (shape["rebind"], "before"),
                   "the body's start": (shape["fn"].body[0], "before"),
                   "the trio": (shape["trio_stmt"], "replace"), "the kept revive": (shape["kept_revive"], "replace"),
                   "the Event made": (shape["event_made"], "replace"), "the rebind": (shape["rebind"], "replace"),
                   "the kept run": (shape["kept_run"], "replace"), "the install": (shape["install"], "replace"),
                   "the unwrap": (shape["unwrap"], "replace"), "the notify": (shape["notify"], "replace"),
                   "in the wrapper's try": (wrapper_try.body[0], "after"),
                   "the wrapper def": (shape["wrapper"], "before"), "the fake def": (shape["fake_def"], "before"),
                   "the road def": (shape["roads"][0], "before"), "before the notify": (shape["try"].body[0], "before"),
                   "the finally's first": (shape["try"].finalbody[0], "before")}
        after_try, finally_run, one_try, wait_msg = ("after the try the wait's result", "the finally puts the real run back",
                                                    "the notify call runs in one try", "the finally waits on the Event")
        reflect, binds, rebinds, env = ("names reflection, in any reference form", "binds or deletes an attribute",
                                        "binds the names km or os", "names the environment only in")
        held = "holds one value"
        window = "nothing runs in the test's frame but the parts"
        undecorated = "the wrapper, the fake and each road carry no decorator"

        def under_if(node):                # a part of the test under an if, so it never runs
            return ("if saved:\n" + textwrap.indent(ast.unparse(node), "    ")).replace("%", "%%")

        def read_at(role, name):           # the name rule's fault for that row's read half, and no other row's
            return "%s (%s) is read at lines" % (role, name)

        def bound_at(role, name):          # ...and for its bind half
            return "%s (%s) is bound at lines" % (role, name)
        plants = (
            ("a return between the try and the final assertions", "after the try", "return", after_try),
            ("a return in the finally between the wait and the put-backs", "after the wait", "return", finally_run),
            ("a raise of SkipTest after the try", "after the try", 'raise unittest.SkipTest("planted")', after_try),
            ("a skipTest call after the try", "after the try", 'self.skipTest("planted")', after_try),
            ("os._exit after the try", "after the try", "os._exit(0)", after_try),
            ("a conditional return before the try", "before the try", "if saved:\n    return", one_try),
            ("the wait in a try whose except clause catches what the call before it raises", "the wait",
             'try:\n    int("planted")\n    %(ended)s = %(event)s.wait(60)\nexcept ValueError:\n    %(ended)s = True', wait_msg),
            ("a return in the wrapper before its try", "the wrapper's try", "return", "the wrapper runs the real revive in a try"),
            ("an except clause on the notify's try", "the notify try's clauses", "except AssertionError:\n    pass", one_try),
            ("an except clause on the wrapper's try", "the wrapper try's clauses", "except BaseException:\n    pass", "the wrapper runs the real revive in a try"),
            ("a yield that never runs", "after the try", "if False:\n    yield", "no generator"),
            ("a skip decorator", "the def", '@unittest.skip("planted")', "carries no decorator"),
            ("setattr on the module", "after the install", 'setattr(km.subprocess, "run", %(real_run)s)', reflect),
            ("a tuple target", "after the install", "km.subprocess.run, _x = %(real_run)s, 0", binds),
            ("a chained assignment", "after the install", "_y = km.subprocess.run = %(real_run)s", binds),
            ("an augmented assignment", "after the install", "km.subprocess.run |= %(real_run)s", binds),
            ("an annotated assignment", "after the install", "km.subprocess.run: object = %(real_run)s", binds),
            ("a starred target", "after the install", "*km.subprocess.run, = [%(real_run)s]", binds),
            ("a for target", "after the install", "for km.subprocess.run in (%(real_run)s,):\n    pass", binds),
            ("a with target", "after the install", "with contextlib.nullcontext(%(real_run)s) as km.subprocess.run:\n    pass", binds),
            ("a del", "after the install", "del km.subprocess.run", binds),
            ("the module through another name", "after the install", "subprocess.run = %(real_run)s", binds),
            ("the kernel's subprocess attribute rebound", "after the install", "km.subprocess = subprocess", binds),
            ("the module's __dict__", "after the install", 'km.subprocess.__dict__["run"] = %(real_run)s', reflect),
            ("vars() of the kernel", "after the install", 'vars(km)["_revive_postal_bus"] = %(real_revive)s', reflect),
            ("object.__setattr__", "after the install", 'object.__setattr__(km, "_revive_postal_bus", %(real_revive)s)', reflect),
            ("mock.patch by a string", "after the install", 'mock.patch("subprocess.run", %(real_run)s).start()', reflect),
            ("exec of a string", "after the install", 'exec("km.subprocess.run = %(real_run)s")', reflect),
            ("getattr of the kernel", "after the install", 'getattr(km, "subprocess").run = %(real_run)s', reflect),
            ("sys.modules", "after the install", 'sys.modules["subprocess"].run = %(real_run)s', reflect),
            ("the revive by a tuple target", "after the install", "km._revive_postal_bus, _x = %(real_revive)s, 0", binds),
            ("km rebound", "after the install", "km = importlib.reload(km)", rebinds),
            ("km bound by an import", "after the install", "import json as km", rebinds),
            ("os rebound", "after the install", "os = types.SimpleNamespace(environ={})", rebinds),
            ("a pop in the finally before the wait", "before the wait", 'os.environ.pop("ROMP_POSTAL_PORT", None)', "the revive's calls run under the trio"),
            ("a pop before the call", "after the install", 'os.environ.pop("ROMP_POSTAL_PORT", None)', env),
            ("a del before the call", "after the install", 'del os.environ["ROMP_POSTAL_PORT"]', env),
            ("|= on the environment", "before the wait", 'os.environ |= {"ROMP_POSTAL_PORT": "0"}', env),
            ("dict.__setitem__ on the environment", "before the wait", 'dict.__setitem__(os.environ, "ROMP_POSTAL_PORT", "0")', env),
            ("a name bound to the environment", "after the install", 'env = os.environ\nenv.pop("ROMP_POSTAL_PORT", None)', env),
            ("os.environb", "before the wait", 'os.environb.pop(b"ROMP_POSTAL_PORT", None)', env),
            ("os.putenv", "before the wait", 'os.putenv("ROMP_POSTAL_PORT", "0")', env),
            ("os.unsetenv", "before the wait", 'os.unsetenv("ROMP_POSTAL_PORT")', env),
            ("environ imported from os", "before the wait", 'from os import environ\nenviron.pop("ROMP_POSTAL_PORT", None)', env),
            ("os.environ rebound", "before the wait", "os.environ = dict(os.environ)", env),
            ("mock.patch.dict of the environment", "before the wait", 'mock.patch.dict(os.environ, {"ROMP_POSTAL_PORT": "0"}).start()', reflect),
            ("the fake calling the real run itself", "the fake's return", "return %(real_run)s(*a, **kw)", "the road from the fake to the real run"),
            ("a second road from the fake that records nothing", "the fake's return",
             "return %(fake_return)s if a else %(real_run)s(*a, **kw)", "one list is asserted empty that every road to the real run appends to"),
            ("the fake's list asserted in the road's place", "the road's assertion", 'self.assertEqual(%(stubbed)s, [], "planted")',
             "one list is asserted empty that every road to the real run appends to"),
            # round 2's fifth commit on fork PR #894: a name the parts are read by, holding another value (the verifier's
            # five first, each of which passed every pin), and its other routes
            ("the kept real run rebound after the install", "after the install", "%(real_run)s = %(fake)s", held),
            ("the kept real revive rebound", "after the install", "%(real_revive)s = %(wrapper)s", held),
            ("the Event set before the call", "after the install", "%(event)s.set()", held),
            ("the Event rebound to an object whose wait returns at once", "after the install",
             '%(event)s = type("_Done", (), {"wait": lambda s, t: True, "set": lambda s: None})()', held),
            ("the saved mapping cleared after the trio is set", "before the try", "%(saved_env)s.clear()", held),
            ("the kept real run rebound to what subprocess.run holds", "after the install", "%(real_run)s = subprocess.run", held),
            ("the kept real revive rebound to a function that does nothing", "after the install", "%(real_revive)s = lambda: None", held),
            ("the fake rebound before it is installed", "before the install", "%(fake)s = subprocess.run", held),
            ("the wrapper rebound before the revive is rebound to it", "before the rebind", "%(wrapper)s = lambda: None", held),
            ("the road rebound", "after the install", "%(road)s = subprocess.run", held),
            ("the wait's result rebound", "after the try", "%(ended)s = True", held),
            ("the road's list emptied before its assertion", "after the try", "del %(reached)s[:]", held),
            ("the real run handed to a thread outside the road", "after the install", 'threading.Thread(target=%(real_run)s, args=(["true"],)).start()', held),
            ("a nested def's parameter hiding the kept real run", "after the install", "def _planted(%(real_run)s=None):\n    return %(real_run)s", held),
            ("threading rebound", "after the install", "threading = types.SimpleNamespace(Event=lambda: None)", held),
            ("the test case rebound", "after the try", "self = types.SimpleNamespace(assertTrue=lambda *a: None, assertEqual=lambda *a: None)", held),
            ("a lambda's parameter hiding km", "after the install", "_planted = lambda km=None: km", rebinds),
            ("the road's list made by an object equal to any list", "the road's list",
             '%(stubbed)s, %(reached)s = [], type("_L", (list,), {"__eq__": lambda s, o: True})()', "made by an empty list literal"),
            ("an assertion method rebound", "after the try", "self.assertEqual = lambda *a, **kw: None", binds),
            ("the Event's wait rebound", "after the install", "%(event)s.wait = lambda t: True", binds),
            ("the restore rewritten to put back another name", "the restore", 'for k, v in %(saved_env)s.items():\n    os.environ.pop("ROMP_X", None)',
             "the restore puts each name back from"),
            ("an environment write after the restore", "after the restore", 'os.environ["ROMP_POSTAL_PORT"] = "1"', env),
            ("the restore loop binding one name twice", "the restore",
             "for k, k in %(saved_env)s.items():\n    if k is None:\n        os.environ.pop(k, None)\n    else:\n        os.environ[k] = k",
             "binds two names, a name and its saved value"),
            ("the saved mapping made over two of the trio's names", "the saved mapping",
             '%(saved_env)s = {k: os.environ.get(k) for k in ("ROMP_POSTAL_PEERS", "ROMP_POSTAL_PORT")}', "is made as {name: os.environ.get(name)"),
            ("the saved mapping holding None for every name", "the saved mapping",
             '%(saved_env)s = {k: None for k in ("ROMP_POSTAL_CLIENT_ONLY", "ROMP_POSTAL_PEERS", "ROMP_POSTAL_PORT")}', "is made as {name: os.environ.get(name)"),
            ("the saved mapping filtered by an if", "the saved mapping",
             '%(saved_env)s = {k: os.environ.get(k) for k in ("ROMP_POSTAL_CLIENT_ONLY", "ROMP_POSTAL_PEERS", "ROMP_POSTAL_PORT") if k != "ROMP_POSTAL_PORT"}',
             "is made as {name: os.environ.get(name)"),
            # round 2's twenty-fourth commit on fork PR #894 (the re-verifier's findings on the fifth: one row's read
            # half set to accept any read, or one binding form dropped from _name_binds, left every pin green): each
            # row's read half that no plant above reaches, and each binding form, planted so that rule alone refuses it
            ("the kept real run handed to a thread through km.threading, outside the road", "after the install",
             'km.threading.Thread(target=%(real_run)s, args=(["true"],)).start()', read_at("the kept real run", names["real_run"])),
            ("the kept real revive started on a thread outside the wrapper", "after the install",
             "km.threading.Thread(target=%(real_revive)s, daemon=True).start()", read_at("the kept real revive", names["real_revive"])),
            ("the wait's result read outside its assertion", "after the try", "_planted = %(ended)s", read_at("the wait's result", names["ended"])),
            ("the wrapper called directly, which sets the Event before the notify", "after the install", "%(wrapper)s()",
             read_at("the wrapper", names["wrapper"])),
            ("the fake bound to another name", "after the install", "_planted = %(fake)s", read_at("the fake", names["fake"])),
            ("threading read to start the real revive before the rebind", "before the rebind",
             "threading.Thread(target=km._revive_postal_bus, daemon=True).start()", read_at("the threading module", "threading")),
            ("the road called outside the fake", "after the install", '%(road)s("true", (["true"],), {})',
             read_at("a road from the fake to the real run", names["road"])),
            ("the Event rebound by a def", "after the install", "def %(event)s():\n    pass", bound_at("the Event", names["event"])),
            ("the Event rebound by a class statement", "after the install", "class %(event)s:\n    wait = staticmethod(lambda t: True)",
             bound_at("the Event", names["event"])),
            ("the wrapper rebound by an async def", "before the rebind", "async def %(wrapper)s():\n    pass", bound_at("the wrapper", names["wrapper"])),
            ("the Event bound by an except clause's as name, and unbound at its end", "after the install",
             'try:\n    int("planted")\nexcept ValueError as %(event)s:\n    pass', bound_at("the Event", names["event"])),
            ("the kept real run declared global", "the body's start", "global %(real_run)s", bound_at("the kept real run", names["real_run"])),
            ("the Event declared nonlocal in a nested def", "after the install", "def _planted():\n    nonlocal %(event)s",
             bound_at("the Event", names["event"])),
            ("the kept real run rebound by a match capture", "after the install", "match km.subprocess.run:\n    case %(real_run)s:\n        pass",
             bound_at("the kept real run", names["real_run"])),
            ("the Event rebound by a match star", "after the install", "match [0]:\n    case [*%(event)s]:\n        pass",
             bound_at("the Event", names["event"])),
            ("the kept real run rebound by a match mapping's rest", "after the install", "match {}:\n    case {**%(real_run)s}:\n        pass",
             bound_at("the kept real run", names["real_run"])),
            ("the saved mapping deleted", "before the try", "del %(saved_env)s", bound_at("the saved environment", names["saved_env"])),
            ("os bound by a dotted import", "after the install", "import os.path", rebinds),
            # the same commit: the import forms of the environment and reflection readers (environ imported under another
            # name passed the pin before it)
            ("environ imported under another name", "before the wait", 'from os import environ as _e\n_e.pop("ROMP_POSTAL_PORT", None)', env),
            ("another object imported under a reflective name", "after the install", "from json import loads as setattr", reflect),
            ("a dotted import whose last part is a reflective name", "after the install", "import six.moves.builtins", reflect),
            # reflection in every reference form (the verifier's three first: the getattr one reddened nothing, the two setattr
            # ones only the executed pin); in each pair the plant that names no other name the pin reads comes first, so it is
            # the reflection rule alone that reds it
            ("getattr through another name onto the environment", "after the install", '_g = getattr\n_g(os, "environ").pop("ROMP_POSTAL_PORT", None)', reflect),
            ("setattr through another name", "after the install", '_s = setattr\n_s(km.subprocess, "run", %(real_run)s)', reflect),
            ("setattr handed to functools.partial", "after the install", 'functools.partial(setattr, km.subprocess, "run")(%(real_run)s)', reflect),
            ("getattr imported under another name onto the environment", "after the install",
             'from builtins import getattr as _g\n_g(os, "environ").pop("ROMP_POSTAL_PORT", None)', reflect),
            ("setattr imported under another name", "after the install", 'from builtins import setattr as _s\n_s(km.subprocess, "run", %(real_run)s)', reflect),
            ("builtins.setattr", "after the install", 'import builtins\nbuiltins.setattr(km.subprocess, "run", %(real_run)s)', reflect),
            ("the environment popped through operator's attrgetter and methodcaller", "after the install",
             'operator.methodcaller("pop", "ROMP_POSTAL_PORT")(operator.attrgetter("environ")(os))', reflect),
            ("operator.methodcaller by a string", "after the install", 'operator.methodcaller("__setattr__", "run", %(real_run)s)(km.subprocess)', reflect),
            ("a function's globals", "after the install", '(lambda: 0).__globals__["km"] = types.SimpleNamespace()', reflect),
            ("a closure cell rewritten", "after the install", "%(fake)s.__closure__[0].cell_contents = %(fake)s", reflect),
            ("a frame's locals", "after the install", 'sys._getframe().f_locals["%(real_run)s"] = %(fake)s', reflect),
            # round 2's twenty-fifth commit on fork PR #894 (the verifier's findings on the twenty-fourth). The kept real
            # run's and real revive's calls outside the road and the wrapper (with either row's calls read anywhere in the
            # test, every pin passed): the real run called directly, and the real revive called directly before the rebind
            ("the kept real run called directly outside the road", "after the try", '_planted = %(real_run)s(["true"])',
             read_at("the kept real run", names["real_run"])),
            ("the kept real revive called directly before the rebind", "before the rebind", "%(real_revive)s()",
             read_at("the kept real revive", names["real_revive"])),
            # ...and each other read half that is scoped to a part, read outside it (with the half read anywhere in the
            # test, every pin passed): the Event waited on before the rebind, the wait's result asserted a second time in
            # the finally, the road's list appended to outside the road and asserted inside the try
            ("the Event waited on before the rebind", "before the rebind", "%(event)s.wait(0)", read_at("the Event", names["event"])),
            ("the wait's result asserted a second time, in the finally", "after the restore", 'self.assertTrue(%(ended)s, "planted")',
             read_at("the wait's result", names["ended"])),
            ("the road's list appended to outside the road", "after the try", '%(reached)s.append("planted")',
             read_at("the road's list", names["reached"])),
            ("the road's list asserted inside the try", "in the try", 'self.assertEqual(%(reached)s, [], "planted")',
             read_at("the road's list", names["reached"])),
            # ...a part that is missing, never runs or is made otherwise (with any of these rules removed, every pin passed)
            ("the trio set under an if, so it never runs", "the trio", under_if(shape["trio_stmt"]), "the trio is set by one os.environ.update statement"),
            ("the trio naming the fixed port", "the trio", 'os.environ.update(ROMP_POSTAL_CLIENT_ONLY="1", ROMP_POSTAL_PEERS="0", ROMP_POSTAL_PORT="25302")',
             "client-only with peers off and a port nothing can bind"),
            ("the trio with client-only off", "the trio", 'os.environ.update(ROMP_POSTAL_CLIENT_ONLY="0", ROMP_POSTAL_PEERS="0", ROMP_POSTAL_PORT="1")',
             "client-only with peers off and a port nothing can bind"),
            ("the real revive kept under an if", "the kept revive", under_if(shape["kept_revive"]), "the real revive is kept in a name before the call"),
            ("the Event made under an if", "the Event made", under_if(shape["event_made"]), "one Event is made before the call"),
            ("the revive rebound under an if", "the rebind", under_if(shape["rebind"]), "km._revive_postal_bus is rebound by one statement that runs"),
            ("the revive rebound to the kept real revive, no def of the test", "the rebind", "km._revive_postal_bus = %(real_revive)s",
             "to a function the test defines first, after keeping the real revive"),
            ("the real run kept under an if", "the kept run", under_if(shape["kept_run"]), "the real subprocess.run is kept in a name before the call"),
            ("the fake installed under an if", "the install", under_if(shape["install"]), "km.subprocess.run is replaced by one statement that runs"),
            ("subprocess.run replaced by a lambda, no def of the test", "the install",
             'km.subprocess.run = lambda *a, **kw: km.subprocess.CompletedProcess(a, 1, "", "")', "by a function the test defines first, after keeping the real run"),
            ("the real revive put back under an if", "the unwrap", under_if(shape["unwrap"]), "the finally puts the real revive back"),
            ("the restore dropped from the finally", "the restore", "pass", "the finally restores the trio"),
            ("the restore under an if", "the restore", under_if(shape["restore"]), "the finally restores the environment in one for statement"),
            ("the saved mapping made under an if", "the saved mapping", under_if(shape["saved_made"]), "is made by one statement that runs before the call"),
            # ...a kick in the window or the wrapper (the verifier's second notify and Popen of the postal service inside
            # the try passed every pin but, on some runs, the executed one), one per clause of the window rule
            ("a second notify inside the try", "in the try", 'km._notify_bus_peer("TESTHOST", 50002, True)', window),
            ("a Popen of the postal service inside the try", "in the try",
             'km.subprocess.Popen([sys.executable, "bin/romp-postal-service", "ensure"]).wait()', window),
            ("another kernel call between the install and the trio", "after the install", 'km._notify_bus_origin_trust("TESTHOST", "directed")', window),
            ("another kernel call between the rebind and the install", "before the install", 'km._notify_bus_origin_trust("TESTHOST", "directed")', window),
            ("an assertion inside the try that calls the kernel", "in the try", 'self.assertFalse(km._notify_bus_origin_trust("TESTHOST", "directed"))', window),
            ("a second notify statement inside the try", "in the try", 'self.assertFalse(km._notify_bus_peer("TESTHOST", 50003, True))', window),
            ("the notify statement calling a second notify", "the notify",
             'self.assertFalse(km._notify_bus_peer("TESTHOST", 50002, True) or km._notify_bus_peer("TESTHOST", 50003, True))', window),
            ("another kernel call in the finally before the wait", "before the wait", 'km._notify_bus_origin_trust("TESTHOST", "directed")', window),
            ("km.BUS_PORT put back from a kernel call before the wait", "before the wait",
             'km.BUS_PORT = km._notify_bus_origin_trust("TESTHOST", "directed")', window),
            ("a name bound from a name before the wait", "before the wait", "_planted = saved", window),
            ("another method of the test case called inside the try", "in the try", 'self.addCleanup(km._notify_bus_origin_trust, "TESTHOST", "directed")', window),
            ("a kernel call named like an assertion inside the try", "in the try", "km.assert_planted()", window),
            ("the test case reached through an assertion method inside the try", "in the try",
             'self.assertTrue.__self__.addCleanup(km._notify_bus_origin_trust, "TESTHOST", "directed")', window),
            ("another kernel call in the wrapper's try", "in the wrapper's try", 'km._notify_bus_origin_trust("TESTHOST", "directed")',
             "the wrapper runs the real revive in a try"),
            # round 2's twenty-sixth commit on fork PR #894 (the re-verifier's findings on the twenty-fifth): the window read
            # by what runs (each passed the pin and the executed pin), the clause of the window rule no plant reached
            # (with beside() reading no lambda's body, every pin passed), and the saved mapping's items() read outside
            # the restore (with any items() call taken as the restore's read, every pin passed)
            ("a second notify in the wait statement's own argument", "the wait",
             '%(ended)s = %(event)s.wait(km._notify_bus_peer("TESTHOST", 50003, True) or 60)', window),
            ("a second notify in a try of the finally, before the wait it holds", "the wait",
             'try:\n    km._notify_bus_peer("TESTHOST", 50003, True)\nfinally:\n    %(ended)s = %(event)s.wait(60)', window),
            ("an assertion inside the try whose lambda runs a kernel call and raises", "in the try",
             'self.assertRaises(ZeroDivisionError, lambda: km._notify_bus_origin_trust("TESTHOST", "directed") / 0)', window),
            ("the saved mapping's items read after the try", "after the try", "_planted = %(saved_env)s.items()",
             read_at("the saved environment", names["saved_env"])),
            # round 2's twenty-seventh commit on fork PR #894 (the re-verifier's findings on the twenty-sixth): a decorator
            # on each of the parts' defs (each passed every pin), and a statement at each end of each stretch of the window,
            # and in each argument place the window reads, that no plant above reached (with a stretch cut by one statement
            # at that end, the wait's calls read from its positional arguments alone, or the notify statement's
            # comprehension from its first argument alone, every pin passed)
            ("a decorator on the wrapper that runs a second notify after it", "the wrapper def",
             '@(lambda f: lambda: (f(), km._notify_bus_peer("TESTHOST", 50003, True)))', undecorated),
            ("a decorator on the fake that replaces it with the real run", "the fake def", "@(lambda f: km.subprocess.run)", undecorated),
            ("a decorator on the road that makes another kernel call", "the road def",
             '@(lambda f: lambda *a: (km._notify_bus_origin_trust("TESTHOST", "directed"), f(*a))[1])', undecorated),
            ("a kernel call right before the try", "before the try", 'km._notify_bus_origin_trust("TESTHOST", "directed")', window),
            ("a kernel call in the try before the notify statement", "before the notify", 'km._notify_bus_origin_trust("TESTHOST", "directed")',
             window),
            ("a kernel call as the finally's first statement", "the finally's first", 'km._notify_bus_origin_trust("TESTHOST", "directed")', window),
            ("a second notify in the wait's timeout keyword", "the wait",
             '%(ended)s = %(event)s.wait(timeout=km._notify_bus_peer("TESTHOST", 50003, True) or 60)', window),
            ("the notify run twice by a comprehension in the notify statement's second argument", "the notify",
             'self.assertEqual([False, False], [km._notify_bus_peer("TESTHOST", p, True) for p in (50002, 50003)], "planted")', window),
            ("the notify run twice by a comprehension in a keyword argument of the notify statement", "the notify",
             'self.assertEqual([False, False], second=[km._notify_bus_peer("TESTHOST", p, True) for p in (50002, 50003)])', window),
            # round 2's twenty-eighth commit on fork PR #894 (the re-verifier's findings on the twenty-seventh): two
            # plants that _repeats reading a lambda's body alone refuses, harmless ones (with that part skipped, every
            # pin passed, and its docstring said no plant could tell)
            ("a lambda holding a call-free list comprehension handed to the notify statement as its msg", "the notify",
             'self.assertFalse(km._notify_bus_peer("TESTHOST", 50002, True), msg=(lambda: [p for p in (1, 2)]))', window),
            ("a lambda holding a call-free set comprehension as the notify's own argument", "the notify",
             'self.assertFalse(km._notify_bus_peer("TESTHOST", 50002, (lambda: {p for p in (1, 2)})))', window))
        lines = cls_src.splitlines(keepends=True)

        def with_args(fn, args):           # the one-line header of a def of the test, its parameters replaced
            self.assertEqual(fn.body[0].lineno, fn.lineno + 1, "%s's header is one line" % fn.name)
            return "".join(lines[:fn.lineno - 1] + ["%sdef %s(%s):\n" % (" " * fn.col_offset, fn.name, args)] + lines[fn.lineno:])

        def with_parameter(fn, extra):     # ...a parameter added at its end
            return with_args(fn, ", ".join(p for p in (ast.unparse(fn.args), extra) if p))
        saved_made, trio_stmt = shape["saved_made"], shape["trio_stmt"]
        self.assertEqual(trio_stmt.lineno, saved_made.end_lineno + 1, "the saved mapping is made on the line before the trio")
        whole = [("the road's own parameter hiding the kept real run", with_parameter(shape["roads"][0], "%(real_run)s=None" % names), held),
                 ("the wrapper's own parameter hiding the Event", with_parameter(shape["wrapper"], "%(event)s=None" % names), held),
                 ("the saved mapping made after the trio is set",
                  "".join(lines[:saved_made.lineno - 1] + lines[trio_stmt.lineno - 1:trio_stmt.end_lineno]
                          + lines[saved_made.lineno - 1:saved_made.end_lineno] + lines[trio_stmt.end_lineno:]), "before the trio is set")]
        wait, unfake = shape["wait"], shape["unfake"]
        self.assertEqual(unfake.lineno, wait.end_lineno + 1, "the real run is put back on the line after the wait")
        whole += [("the real run put back before the wait",   # the twenty-fifth commit: the parts that no plant above reached
                   "".join(lines[:wait.lineno - 1] + lines[unfake.lineno - 1:unfake.end_lineno] + lines[wait.lineno - 1:wait.end_lineno]
                           + lines[unfake.end_lineno:]), "every call the revive makes goes through the fake")]
        whole += [("the fake taking %s" % what, with_args(shape["fake_def"], args), "the fake takes (*a, **kw)")
                  for what, args in (("no keywords", "*a"), ("no positional arguments", "**kw"), ("the argv as a parameter", "argv, *a, **kw"),
                                     ("a positional-only parameter", "argv, /, *a, **kw"), ("a keyword-only parameter", "*a, timeout=None, **kw"))]
        rebind, install = shape["rebind"], shape["install"]    # the twenty-sixth commit: the window starts at the first of the two
        self.assertEqual(install.lineno, rebind.end_lineno + 1, "the fake is installed on the line after the revive is rebound")
        whole += [("the install moved before the rebind, another kernel call between them",
                   "".join(lines[:rebind.lineno - 1] + lines[install.lineno - 1:install.end_lineno]
                           + ['%skm._notify_bus_origin_trust("TESTHOST", "directed")\n' % (" " * rebind.col_offset)]
                           + lines[rebind.lineno - 1:rebind.end_lineno] + lines[install.end_lineno:]), window)]
        for label, planted, fragment in [(label, _plant_at(cls_src, anchors[anchor][0], text % names, anchors[anchor][1], *anchors[anchor][2:]), fragment)
                                         for label, anchor, text, fragment in plants] + whole:
            with self.assertRaises(AssertionError, msg="%s: the pin passed it" % label) as caught:
                self._guard_shape(planted)
            self.assertIn(fragment, str(caught.exception), "%s: the pin reds for the part it breaks" % label)
        # the twenty-eighth commit: the lines the window rule's message names, where two other readings refuse the same
        # plants as the pin's own (the re-verifier's on the twenty-seventh: with the finally's stretch read from its own
        # statements alone, not the statements a try there runs, or with the last notify statement exempted in the
        # first's place, every pin passed). A try of the finally before the wait names its own line and each line it
        # runs; a second notify statement after the test's own names the second
        wait_line, notify_end = shape["wait"].lineno, shape["notify"].end_lineno
        for label, planted, named in (
                ("a try of the finally before the wait whose body is a kernel call",
                 _plant_at(cls_src, shape["wait"], 'try:\n    km._notify_bus_origin_trust("TESTHOST", "directed")\nfinally:\n    pass', "before"),
                 [wait_line, wait_line + 1, wait_line + 3]),
                ("a second notify statement after the test's own",
                 _plant_at(cls_src, shape["notify"], 'self.assertFalse(km._notify_bus_peer("TESTHOST", 50003, True))', "after"), [notify_end + 1])):
            with self.assertRaises(AssertionError, msg="%s: the pin passed it" % label) as caught:
                self._guard_shape(planted)
            self.assertIn("other statements at lines %s)" % named, str(caught.exception), "%s: the message names each statement of the window that runs "
                                                                                         "and is not a part" % label)
        # the twenty-sixth commit: the notify run twice by each kind of comprehension _repeats reads (the re-verifier's list
        # comprehension and generator passed the pin and the executed pin), and every name the parts are read by, self
        # aside, bound to another name after the try (with any assignment's value taken as the put-back's read, or as the
        # wrapper's, every pin passed). Both written out here, not read from what the pin reads, so a kind dropped from
        # _REPEATS or a row dropped from the name rule leaves its plant passing; held equal to them after each loop, so
        # one added without a plant fails the test
        repeats = (("a list comprehension", ast.ListComp, '[km._notify_bus_peer("TESTHOST", p, True) for p in (50002, 50003)], [False, False]'),
                   ("a set comprehension", ast.SetComp, '{km._notify_bus_peer("TESTHOST", p, True) for p in (50002, 50003)}, {False}'),
                   ("a dict comprehension", ast.DictComp,
                    '{p: km._notify_bus_peer("TESTHOST", p, True) for p in (50002, 50003)}, {50002: False, 50003: False}'),
                   ("a generator expression", ast.GeneratorExp, '(*(km._notify_bus_peer("TESTHOST", p, True) for p in (50002, 50003)),), (False, False)'))
        for what, _, args in repeats:
            with self.assertRaises(AssertionError, msg="the notify run twice by %s: the pin passed it" % what) as caught:
                self._guard_shape(_plant_at(cls_src, shape["notify"], 'self.assertEqual(%s, "planted")' % args, "replace"))
            self.assertIn(window, str(caught.exception), "the notify run twice by %s: the pin reds for the window" % what)
        self.assertEqual(tuple(kind for _, kind, _ in repeats), _REPEATS, "every kind of comprehension _repeats reads is planted above")
        aliases = (("the kept real run", names["real_run"]), ("the kept real revive", names["real_revive"]), ("the Event", names["event"]),
                   ("the wait's result", names["ended"]), ("the fake", names["fake"]), ("the wrapper", names["wrapper"]),
                   ("the saved environment", names["saved_env"]), ("the road's list", names["reached"]),
                   ("the threading module", "threading"), ("a road from the fake to the real run", names["road"]))
        for role, name in aliases:
            with self.assertRaises(AssertionError, msg="%s bound to another name after the try: the pin passed it" % role) as caught:
                self._guard_shape(_plant_at(cls_src, shape["after"][0], "_planted = %s" % name, "before"))
            self.assertIn(read_at(role, name), str(caught.exception), "%s bound to another name after the try: the pin reds for its read half" % role)
        self.assertEqual(sorted(aliases), shape["held"], "every name the parts are read by, self aside, is planted above bound to another name")
        # ...and inside the try before the notify statement, an assertion that calls nothing ahead of it (the twenty-eighth
        # commit: with the notify statement's one call read as at most one, that assertion counts as the first notify
        # statement and the test's own is stray; every pin passed under that reading before this placement was held)
        for label, anchor in (("after the try, as the guard test's comment anticipates", "after the try"),
                              ("inside the try, where upstream's text has it", "in the try"),
                              ("inside the try, before the notify statement", "before the notify")):
            node, where = anchors[anchor]
            both = _plant_at(cls_src, node, 'self.assertEqual(%(stubbed)s, [], "a client-only kernel never runs the bus ensure")' % names, where)
            self.assertEqual(self._guard_shape(both)["reached"], shape["reached"],
                             "fork PR #875's assertion kept %s: the pin passes and reads the road's list" % label)
        # the kicks _guard_shape's NOT READ list names as unread, with what sees each, held here as plants the pin
        # passes, so a change that reads one shows here and moves it among the plants above: the re-verifier's three
        # outside the window, a kick in the fake's body, the kernel's ensure handed to assertRaises in the try, an
        # object made before the window whose truth test the notify runs, and one whose comparison with 0 the wait runs
        # (the re-verifier's on round 2's twenty-sixth commit: Event.wait compares its timeout with 0 while the Event is
        # not set), and the port the notify dials changed before the window, the test's own km.BUS_PORT = 1 rewritten
        # and a second assignment before the rebind (the re-verifier's on the twenty-seventh; the executed pin reds on
        # each)
        notify_call = 'km._notify_bus_peer("TESTHOST", 50002, True)'
        port_set = [s for s in shape["fn"].body if _assign_to(s, ["km", "BUS_PORT"]) and isinstance(s.value, ast.Constant)]
        self.assertEqual([ast.unparse(s) for s in port_set], ["km.BUS_PORT = 1"], "the guard test sets km.BUS_PORT = 1 once, in a statement of its own body")
        self.assertEqual(cls_src.count(notify_call), 1, "the guard test's notify call is written once as %s" % notify_call)
        truth = _plant_at(cls_src, shape["rebind"], "class _K:\n    def __bool__(_s):\n        km._ensure_postal_bus()\n"
                          "        return True\n_k = _K()", "before").replace(notify_call, notify_call.replace("True", "_k"))
        timeout = _plant_at(_plant_at(cls_src, shape["wait"], "%(ended)s = %(event)s.wait(_t)" % names, "replace"), shape["rebind"],
                            'class _T:\n    def __gt__(_s, o):\n        km._notify_bus_peer("TESTHOST", 50003, True)\n        return True\n\n'
                            "    def __float__(_s):\n        return 60.0\n_t = _T()", "before")
        for label, planted in (("the real revive on a thread through km.threading before the rebind",
                                _plant_at(cls_src, shape["rebind"], "km.threading.Thread(target=km._revive_postal_bus, daemon=True).start()", "before")),
                               ("a second notify after the try", _plant_at(cls_src, shape["after"][0], notify_call, "before")),
                               ("the kernel's ensure after the try", _plant_at(cls_src, shape["after"][0], "km._ensure_postal_bus()", "before")),
                               ("another kernel call in the fake's body",
                                _plant_at(cls_src, shape["fake_def"].body[0], 'km._notify_bus_origin_trust("TESTHOST", "directed")', "before")),
                               ("the kernel's ensure handed to an assertion method that calls it, in the try",
                                _plant_at(cls_src, shape["notify"], "self.assertRaises(Exception, km._ensure_postal_bus)", "after")),
                               ("an object made before the window whose truth test the notify runs", truth),
                               ("an object made before the window, handed to the wait as its timeout, whose comparison runs a second notify",
                                timeout),
                               ("the test's own km.BUS_PORT = 1 rewritten to another port", _plant_at(cls_src, port_set[0], "km.BUS_PORT = 2", "replace")),
                               ("a second assignment of km.BUS_PORT before the rebind", _plant_at(cls_src, shape["rebind"], "km.BUS_PORT = 2", "before"))):
            try:
                self._guard_shape(planted)
            except AssertionError as e:
                self.fail("%s: named as unread in _guard_shape's NOT READ list, and the pin now reds it (%s): move it among the "
                          "plants the pin refuses and out of that list" % (label, e))
        # every identifier the reflection and environment readers list, planted alone in each reference form its reader
        # reads (the re-verifier's finding on round 2's fifth commit: an identifier dropped from a list left both pins
        # green). Written out here, not read from the readers' lists, so an identifier dropped from a list leaves its
        # plants passing the pin; held equal to those lists after the loop, so one added without a plant fails the test
        reflective_names = ("setattr", "delattr", "getattr", "vars", "globals", "locals", "exec", "eval", "compile", "__import__",
                            "patch", "builtins", "__builtins__", "import_module", "attrgetter", "methodcaller", "_getframe",
                            "currentframe", "get_referrers", "get_referents", "get_objects")
        reflective_attrs = ("__setattr__", "__delattr__", "__getattribute__", "__dict__", "__globals__", "__closure__", "__code__",
                            "__defaults__", "__kwdefaults__", "cell_contents", "f_locals", "f_globals", "f_builtins", "modules")
        env_names = ("environ", "environb", "putenv", "unsetenv")
        forms = {"a bare name": "_planted = %s", "a bare name stored": "%s = None", "a bare name deleted": "del %s",
                 "an attribute": "_planted = km.%s", "an imported name": "from _anywhere import %s as _planted",
                 "an import's as name": "from _anywhere import _planted as %s"}
        bare = ("a bare name", "a bare name stored", "a bare name deleted")
        for fragment, idents, read_forms in ((reflect, reflective_names, bare + ("an attribute", "an imported name", "an import's as name")),
                                             (reflect, reflective_attrs, ("an attribute", "an imported name", "an import's as name")),
                                             (env, env_names, bare + ("an attribute", "an imported name"))):
            for ident in idents:
                for form in read_forms:
                    with self.assertRaises(AssertionError, msg="%s as %s: the pin passed it" % (ident, form)) as caught:
                        self._guard_shape(_plant_at(cls_src, shape["install"], forms[form] % ident, "after"))
                    self.assertIn(fragment, str(caught.exception), "%s as %s: the pin reds for the reader that lists it" % (ident, form))
        self.assertEqual((reflective_names, reflective_attrs, env_names), (_REFLECTIVE_NAMES, _REFLECTIVE_ATTRS, _ENV_NAMES),
                         "every identifier the two readers list is planted above, in each reference form its reader reads")

    def test_the_guard_tests_fake_answers_only_a_postal_service_call_and_passes_every_other_call_to_the_real_run(self):
        """The guard test's own fake, run: its def (and any def of the test it calls by name) is compiled from the test's
        source inside a factory that binds the test's top-level names, the kept real run bound to a recorder, and called
        with the argv shapes it must tell apart (regression-2 of round 1 on fork PR #894, with its refuter's corrected
        shape). A call whose argv names romp-postal-service, positional or by the args keyword, a list, a tuple or one
        string, the verb at argv[2] or moved off it, never reaches the recorder and is answered with a CompletedProcess
        the kernel can read; a foreign call (a one-element argv, which indexing argv[1] or argv[2] would raise on; an
        empty argv; the argv by keyword; a shell string) reaches the recorder exactly as made and gets the recorder's own
        answer, never a fake one; and the list the guard test asserts empty stays empty. What this does not run: the
        fake inside the guard test's window, under a live revive thread (the guard test itself, and the executed pin
        below, do that)."""
        shape = self._guard_shape()
        fn = shape["fn"]
        src = open(os.path.join(HERE, "test_kernel.py"), encoding="utf-8", errors="replace").read()
        defs = {s.name: s for s in fn.body if isinstance(s, ast.FunctionDef)}
        called = sorted({c.func.id for c in ast.walk(defs[shape["fake"]]) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                         and c.func.id in defs and c.func.id != shape["fake"]})
        bound = sorted({t.id for s in fn.body if isinstance(s, ast.Assign) for target in s.targets
                        for t in (target.elts if isinstance(target, ast.Tuple) else [target]) if isinstance(t, ast.Name)})
        body = "".join(textwrap.indent(textwrap.dedent(ast.get_source_segment(src, defs[n], padded=True)) + "\n", "    ")
                       for n in [shape["fake"]] + called)
        ns = {"km": type("km", (), {"subprocess": subprocess})}
        exec(compile("def _factory(%s):\n%s    return %s\n" % (", ".join(bound), body, shape["fake"]), "<the guard test's fake>", "exec"), ns)
        real_calls, answer = [], object()

        def recorder(*a, **kw):
            real_calls.append((a, kw))
            return answer
        names = {n: [] for n in bound}
        names[shape["real_run"]] = recorder
        fake = ns["_factory"](**names)
        postal = [sys.executable, "/nonexistent/bin/romp-postal-service", "ensure"]
        for label, a, kw in (("the argv positional, as the kernel passes it", (postal,), {"stdout": subprocess.DEVNULL, "timeout": 30}),
                             ("the argv by keyword", (), {"args": postal}),
                             ("a tuple", (tuple(postal),), {}),
                             ("the verb moved off argv[2]", ([sys.executable, "/nonexistent/bin/romp-postal-service", "--quiet", "ensure"],), {}),
                             ("a two-element argv", (["/nonexistent/bin/romp-postal-service", "ensure"],), {}),
                             ("one string", ("romp-postal-service ensure",), {"shell": True})):
            r = fake(*a, **kw)
            self.assertEqual(real_calls, [], "%s: a postal-service call never reaches the real run" % label)
            self.assertIsInstance(r, subprocess.CompletedProcess, "%s: ...and is answered with a CompletedProcess the kernel can read" % label)
        for label, a, kw in (("a one-element argv", (["true"],), {}),
                             ("an empty argv", ([],), {}),
                             ("a foreign argv by keyword", (), {"args": ["true"], "capture_output": True}),
                             ("a foreign shell string", ("true",), {"shell": True})):
            del real_calls[:]
            self.assertIs(fake(*a, **kw), answer, "%s: a foreign call gets the real run's own answer" % label)
            self.assertEqual(real_calls, [(a, kw)], "%s: ...passed to the real run exactly as made" % label)
        self.assertEqual(names[shape["reached"]], [], "nothing the fake passed to the real run names the postal service")

    def test_the_peer_notify_guard_test_starts_no_ensure_child_and_dials_no_fixed_port(self):
        """Executed: a child pytest runs tests/test_kernel.py's PostalPeerTunnels.test_notify_bus_peer_is_guarded with a
        sitecustomize (_DIAL_SPY) on its PYTHONPATH, so every Python process of that run records each socket connect by
        port, each subprocess.Popen whose command names romp-postal-service, and its argv at exit, and refuses a connect to the machine's fixed bus port (the postal service's default
        port, read from bin/romp-postal-service) before it reaches the network. No process of the run dials the fixed
        port, and no romp-postal-service process is started or exits: the test's fake answers the revive's ensure. The
        start is read from the spy's spawn record, which the process that runs subprocess.Popen on the postal service
        writes before the fork, from whichever thread runs it, so a child a thread forks as the run ends is seen though
        its dial and its exit come after the run (since round 2's twenty-seventh commit on fork PR #894: before it this
        pin read the exit and the dial alone, and on two of the re-verifier's runs of a real revive started on a thread
        before the guard test's rebind, with the ensure's run delayed by 0.05 s, the spawn was the only record at the
        run's end; and with a scratch postal service whose ensure waits two seconds and ends by os._exit, leaving no
        exit record, as a kill does, this pin at the twenty-sixth commit passed that plant, and now reds on its spawn).
        The spy is shown
        live where it must be: in the test process it records the notify's refused dial to BUS_PORT 1, and at that dial
        the test process's PYTHONPATH still names the spy, so an ensure child forked in the window (it inherits that
        environment) would load it and be recorded. What it does not read, and why that leaves the revive's ensure read:
        a process that is not Python, one started with -S or -I, or one handed an environment without the PYTHONPATH
        (none of them loads the sitecustomize; the ensure is Python, started with neither flag, and inherits the test
        process's environment), a connect made below socket.socket (a C extension's own socket; the postal service's
        ping goes through urllib.request, which connects through socket.socket), and a postal service started other than
        through subprocess.Popen (os.system, os.posix_spawn, a fork and exec: the kernel's ensure runs subprocess.run,
        which starts it through Popen), which this reads only by its exit or its dial before the run ends. With the test at its base text (round
        2's first commit on fork PR #894) this run's ensure child, forked after the test's restore, dialled the fixed
        port in every run (the verifier's plant), which on a box whose own bus listens there reached that bus."""
        m = re.findall(r'^PORT = int\(os\.environ\.get\("ROMP_POSTAL_PORT", "(\d+)"\)\)', open(os.path.join(os.path.dirname(HERE), "bin", "romp-postal-service"), encoding="utf-8").read(), re.M)
        self.assertEqual(len(m), 1, "bin/romp-postal-service names its default port once")
        fixed = int(m[0])
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "sitecustomize.py"), "w", encoding="utf-8") as f:
            f.write(_DIAL_SPY)
        out = os.path.join(d, "dials.jsonl")
        env = dict(os.environ, ROMP_TEST_DIAL_SPY=out, ROMP_TEST_DIAL_SPY_FIXED=str(fixed),
                   PYTHONPATH=os.pathsep.join([d] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else [])))
        env.pop("PYTEST_CURRENT_TEST", None)
        p = subprocess.Popen([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                              "tests/test_kernel.py::PostalPeerTunnels::test_notify_bus_peer_is_guarded"],
                             cwd=os.path.dirname(HERE), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
        try:
            text = p.communicate(timeout=300)[0]
        finally:
            if p.poll() is None:
                p.kill()
                p.wait()
        self.assertEqual(p.returncode, 0, text[-3000:])
        self.assertIn("1 passed", text)
        recs = [json.loads(line) for line in open(out, encoding="utf-8")] if os.path.exists(out) else []
        dials = [r for r in recs if r["kind"] == "dial"]
        notify = [r for r in dials if r["pid"] == p.pid and r["port"] == 1]
        self.assertTrue(notify, "the spy is live in the test process: the notify's dial to BUS_PORT 1: %r" % recs)
        self.assertTrue(all(r["spy_on_path"] for r in notify),
                        "...and the test process's PYTHONPATH names the spy at that dial, so a child forked in the window loads it: %r" % notify)
        self.assertEqual([r for r in dials if r["port"] == fixed], [], "no process of the run dials the machine's fixed bus port %d" % fixed)
        self.assertEqual([r for r in recs if r["kind"] == "spawn"
                          or (r["kind"] == "exit" and any(a.endswith("romp-postal-service") for a in r["argv"]))], [],
                         "no romp-postal-service process is started (the spawn, recorded before the fork) or exits: the test's fake answers "
                         "the revive's ensure")

    def _spied_pytest(self, targets, fixed):
        """A child pytest over `targets` from the checkout with _DIAL_SPY as its sitecustomize, refusing and recording every
        connect to the port `fixed`; returns (returncode, output, records, the child's pid)."""
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "sitecustomize.py"), "w", encoding="utf-8") as f:
            f.write(_DIAL_SPY)
        out = os.path.join(d, "dials.jsonl")
        env = dict(os.environ, ROMP_TEST_DIAL_SPY=out, ROMP_TEST_DIAL_SPY_FIXED=str(fixed),
                   PYTHONPATH=os.pathsep.join([d] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else [])))
        env.pop("PYTEST_CURRENT_TEST", None)
        p = subprocess.Popen([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + list(targets),
                             cwd=os.path.dirname(HERE), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
        try:
            text = p.communicate(timeout=300)[0]
        finally:
            if p.poll() is None:
                p.kill()
                p.wait()
        recs = [json.loads(line) for line in open(out, encoding="utf-8")] if os.path.exists(out) else []
        return p.returncode, text, recs, p.pid

    def test_the_modules_whose_kernels_dialled_the_fixed_bus_port_dial_none_and_start_no_postal_service_in_either_order(self):
        """THE PIN for the path from the run's in-process kernels to the machine's fixed bus port (the reviewer's ruling of
        round 1 on fork PR #894). Every kernel a test module loads in-process read BUS_PORT 25302 at import (conftest pops
        ROMP_POSTAL_PORT), so a bus call of one dialled the machine's own bus; where nothing listened, a refused peer
        notify revived the bus with a real romp-postal-service ensure. The population was derived by execution, a spy over
        one full serial run of tests/ recording every connect to the fixed port and every romp-postal-service spawn with
        its PYTEST_CURRENT_TEST: BUS_DIALLING_MODULES holds every module a recorded connect or spawn came from, the
        in-process postal client's heartbeat in tests/test_postal_relay_honesty.py among them (its BASE was built from the
        same popped name). They run here together, in both orders, in a child pytest with _DIAL_SPY as its sitecustomize
        (every Python process of the run records each connect and refuses one to the fixed port, and records each
        romp-postal-service process started through subprocess.Popen, each such process's own start and every process's
        argv at exit): no process dials the fixed port and none starts the postal service. conftest's _dead_bus_port gives
        every loaded romp_kernel* module DEAD_BUS_PORT for each test and points every loaded romp_postal* module's BASE at
        it, and the tests whose notify is refused stub _revive_postal_bus. The spy is shown live where it must be: the
        test process records its dials to the dead port. The spawn half holds under this
        kernel and under fork PR #875's, whose floor skips the revive and not the connect. What the spy does not read: a
        process that is not Python, or is started with -S or -I or an environment without this PYTHONPATH (none loads
        the sitecustomize), a connect below socket.socket, and a spawn outside subprocess.Popen whose child is not a
        Python process that loads the spy (os.system, os.exec*, os.posix_spawn called directly). At the round-1 head
        (951479a14), with this module's text overlaid, the pin is red. In every run, each order records dials to the
        fixed port from six tests, the three set_working tests of tests/test_postal_relay_honesty.py and KnownHostMemory's
        detach and set-trust tests and PersistedIntent's detach test, and postal-service starts from two of the three
        detach tests the refuters named, KnownHostMemory's test_detach_remembers_the_host_and_its_trust and
        PersistedIntent's test_detach_is_the_one_end_of_intent (a revive still in flight absorbs a later one: the kernel's
        revive is single-flight). The rest depends on timing, for two reasons. First, the five tests that build the
        tunnels listing (KnownHostRoutes' forget-route and tunnels-payload tests and UpdateListing's three) read the bus's
        /peers snapshot through the kernel's 3-second cache, which the two modules share, since both load the one
        romp_kernel module. The first of them in the run always dials: the forget-route test when
        tests/test_kernel_known_hosts.py runs first, the listing test in the other order. A later one dials only when it
        runs 3 s or more after the last dial, which varies with the box's load: in the known_hosts-first order,
        UpdateListing's test_the_route_and_the_cli_agree_on_the_flag did so in all seven of the verifier's runs on round
        2's seventh commit on fork PR #894 and in neither of the two runs that commit's message cited. With the cache
        disabled all five dial in both orders; with a cache that never expires only the first does. Second, a revive's
        ensure child that starts after its test's call phase has ended is listed under that test's teardown."""
        self.maxDiff = None
        fixed = _fixed_bus_port()
        phase = lambda r: r["test"] or "(no test phase, thread %s)" % r["thread"]     # noqa: E731
        runs, seen = {}, {}
        for order in (list(BUS_DIALLING_MODULES), list(reversed(BUS_DIALLING_MODULES))):
            label = " then ".join(os.path.basename(m) for m in order)
            runs[label] = self._spied_pytest(order, fixed)
            recs = runs[label][2]
            seen[label] = {"dials to the fixed port": sorted({phase(r) for r in recs if r["kind"] == "dial" and r["port"] == fixed}),
                           "romp-postal-service starts": sorted({phase(r) for r in recs if r["kind"] in ("spawn", "start") or (
                               r["kind"] == "exit" and any(a.endswith("romp-postal-service") for a in r["argv"]))})}
        self.assertEqual(seen, {label: {"dials to the fixed port": [], "romp-postal-service starts": []} for label in runs},
                         "no process of either run dials the machine's fixed bus port %d or starts the postal service (each "
                         "listed by the test phase current at it)" % fixed)
        from tests.conftest import DEAD_BUS_PORT
        for label, (rc, text, recs, pid) in runs.items():
            self.assertEqual(rc, 0, "%s: %s" % (label, text[-3000:]))
            live = [r for r in recs if r["kind"] == "dial" and r["pid"] == pid and r["port"] == DEAD_BUS_PORT]
            self.assertTrue(live, "%s: the spy is live in the test process: its dials to the dead port %d" % (label, DEAD_BUS_PORT))

    def _scratch_conftest_run(self, modules, env=None):
        """A child pytest over `modules` ({file name: text}) in a scratch directory holding copies of tests/conftest.py and
        the pattern module it loads by path, the checkout on PYTHONPATH (the copied conftest imports the tests package),
        built as tests/test_env_value_redaction.py builds its child runs; `env` names to set, a None value a name to
        remove. A file name may carry a directory (`pkg/__init__.py`), made as needed; the child is given the test_*.py
        files only. Returns (returncode, output, the scratch directory, which is the child's TMPDIR)."""
        d = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        for name in ("conftest.py", "credential_patterns.py"):
            shutil.copy(os.path.join(HERE, name), os.path.join(d, name))
        for name, text in modules.items():
            os.makedirs(os.path.dirname(os.path.join(d, name)), exist_ok=True)
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(text)
        modules = [m for m in modules if os.path.basename(m).startswith("test_")]
        child = dict(os.environ)
        child.pop("PYTEST_CURRENT_TEST", None)
        for k, v in (env or {}).items():
            if v is None:
                child.pop(k, None)
            else:
                child[k] = v
        child["PYTHONPATH"] = os.pathsep.join(p for p in (os.path.dirname(HERE), child.get("PYTHONPATH")) if p)
        child["TMPDIR"] = d
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", d] + sorted(modules),
                           cwd=d, env=child, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
        return r.returncode, r.stdout + r.stderr, d

    def test_the_dead_bus_port_holds_for_each_test_and_comes_back_after_it(self):
        """conftest's _dead_bus_port, run: a child pytest (a copy of tests/conftest.py) over a module that registers two
        synthetic modules, the shapes loaded in-process at import, romp_kernel_restore_probe with BUS_PORT 45678 and
        romp_postal_restore_probe with HOST 127.0.0.1 and BASE http://127.0.0.1:45678, and reads both from every phase
        around its one test. The test reads DEAD_BUS_PORT in both: the fixture holds the dead port for the test. Every
        read outside the test's own window reads 45678 in both: setUpModule, a module-scoped fixture's setup and teardown,
        setUpClass, tearDownClass, tearDownModule, and a thread the test starts that reads after the test's teardown. So
        the port and the URL are put back by the fixture's own cleanup, as the ruling of round 1 on fork PR #894 asks, and
        neither is left dead outside a test; and the windows conftest's paragraph "What this does not reach" names (the
        verifier's finding on round 2 of fork PR #894) are the ones a bus call there dials the import-time port from."""
        self.maxDiff = None
        probe = textwrap.dedent("""\
            import json, os, sys, threading, types, unittest
            import pytest
            _km = types.ModuleType("romp_kernel_restore_probe")
            _km.BUS_PORT = 45678
            _pm = types.ModuleType("romp_postal_restore_probe")
            _pm.HOST, _pm.BASE = "127.0.0.1", "http://127.0.0.1:45678"
            sys.modules["romp_kernel_restore_probe"], sys.modules["romp_postal_restore_probe"] = _km, _pm
            _seen = {}
            _after = threading.Event()
            _threads = []

            def _read(where):
                _seen[where] = [_km.BUS_PORT, _pm.BASE]
                with open(os.environ["ROMP_TEST_BUS_PORT_PROBE"], "w") as f:
                    json.dump(_seen, f)

            def setUpModule():
                _read("setUpModule")

            def tearDownModule():
                _read("tearDownModule")

            @pytest.fixture(scope="module", autouse=True)
            def _module_fixture():
                _read("module fixture")
                yield
                _read("module fixture teardown")

            class Window(unittest.TestCase):
                @classmethod
                def setUpClass(cls):
                    _read("setUpClass")

                @classmethod
                def tearDownClass(cls):
                    _after.set()
                    for t in _threads:
                        t.join(30)
                    _read("tearDownClass")

                def test_during(self):
                    _read("test")
                    t = threading.Thread(target=lambda: (_after.wait(30), _read("a thread after the test")))
                    t.start()
                    _threads.append(t)
        """)
        marker = os.path.join(tempfile.mkdtemp(), "seen.json")
        self.addCleanup(shutil.rmtree, os.path.dirname(marker), True)
        rc, out, _d = self._scratch_conftest_run({"test_bus_port_probe.py": probe}, env={"ROMP_TEST_BUS_PORT_PROBE": marker})
        self.assertEqual(rc, 0, out[-3000:])
        with open(marker, encoding="utf-8") as f:
            seen = json.load(f)
        from tests import conftest
        dead = getattr(conftest, "DEAD_BUS_PORT", "conftest.DEAD_BUS_PORT")
        live = [45678, "http://127.0.0.1:45678"]
        self.assertEqual(seen, {"test": [dead, "http://127.0.0.1:%s" % dead], "setUpModule": live, "module fixture": live,
                                "setUpClass": live, "a thread after the test": live, "tearDownClass": live,
                                "module fixture teardown": live, "tearDownModule": live},
                         "the kernel's BUS_PORT and the postal client's BASE name the dead port during the test and their "
                         "import-time values in every phase outside it")

    def test_a_port_one_test_sets_is_gone_when_the_next_test_starts(self):
        """THE EXECUTED CHECK behind the static pin on conftest's per-test pop of ROMP_POSTAL_PORT (the reviewer's ruling of
        round 1 on fork PR #894; test_conftest_re_asserts_the_names_the_re_asserted_licences_rest_on reads the pop where it
        stands): a child pytest over a copy of tests/conftest.py and a module whose first test sets the port to a
        non-default value (45678, the value that, with the run's hermetic marker beside it, licenses a bind under a test)
        and leaves it, and whose second test reads it absent. Both pass: conftest pops the name before every test. A
        conftest that sets the port instead, to any value, or that drops the pop, fails the second test."""
        module = textwrap.dedent("""\
            import os


            def test_1_sets_the_port_and_leaves_it():
                os.environ["ROMP_POSTAL_PORT"] = "45678"


            def test_2_reads_it_absent():
                assert "ROMP_POSTAL_PORT" not in os.environ, "the port at the second test's start: %s" % os.environ["ROMP_POSTAL_PORT"]
        """)
        rc, out, _d = self._scratch_conftest_run({"test_port_per_test.py": module})
        self.assertEqual(rc, 0, out[-3000:])
        self.assertIn("2 passed", out, out[-3000:])

    def test_the_module_env_fixture_watches_the_seams_and_the_trio_and_no_name_conftest_re_asserts_but_the_port(self):
        """The list conftest's _module_env_restored watches (the reviewer's ruling of round 1 on fork PR #894): at least the
        seams _shared_state_restored watches per test and the postal trio; not PYTEST_CURRENT_TEST, which pytest writes
        for every phase; and no name conftest re-asserts before every test (read from its fixtures, autouse or not, by
        _conftest_fixture_env_names, the wide read: a name written or popped anywhere in a fixture's own body, and not
        one reached through a call or a loop over a name, the credential names and the scope limits among them, none of
        which is watched), since
        conftest's own write would read as the module's, except ROMP_POSTAL_PORT, which the fixture compares with the
        value conftest's pop gives it (unset) instead of with its snapshot."""
        from tests import conftest
        watched = set(conftest.MODULE_WATCHED_ENV_NAMES)
        self.assertLessEqual(set(conftest._SEAM_ENV_NAMES) | set(TRIO), watched)
        self.assertIn("ROMP_POSTAL_HOST", conftest._SEAM_ENV_NAMES, "the bus-name seam is watched per test beside the sessions file")
        self.assertNotIn("PYTEST_CURRENT_TEST", watched)
        self.assertEqual(watched & _conftest_fixture_env_names(), {"ROMP_POSTAL_PORT"})
        self.assertEqual(conftest.MODULE_ENV_FLOORS, {"ROMP_POSTAL_PORT": None}, "the port is compared with its floor, unset")

    def test_a_seam_written_in_setupmodule_setupclass_or_a_module_fixture_with_no_restore_is_named_by_its_module(self):
        """THE PLANTS for conftest's _module_env_restored (the reviewer's ruling of round 1 on fork PR #894): a child pytest
        (a copy of tests/conftest.py) over three planted modules that write ROMP_SESSIONS_FILE with no restore, one in
        setUpModule, one in setUpClass and one in a module-scoped autouse fixture, each followed by a module whose test
        spawns a child that reports the value it inherited. Each later child inherits its planted module's value (the
        leak: the census reads import time, and the per-test fixture's snapshot is taken after module and class setup),
        and the run is red naming each planted module and no other; the setUpModule plant red shows the snapshot is taken
        before setUpModule runs. At the round-1 head (951479a14) the same run was green. A fourth plant leaves
        ROMP_POSTAL_PORT set in its tearDownModule, and the module after it, whose snapshot then carries that port and
        whose test's per-test pop clears it, is not named: the port is compared with its floor (unset), not with the
        snapshot, so conftest's own pop is never read as the next module's change."""
        later = textwrap.dedent("""\
            import os, subprocess, sys

            def test_a_child_reports_what_it_inherited():
                v = subprocess.run([sys.executable, "-c", "import os; print(os.environ.get('ROMP_SESSIONS_FILE'))"],
                                   capture_output=True, text=True, timeout=60).stdout.strip()
                with open(os.environ["ROMP_TEST_MODULE_ENV_MARKER"], "a") as f:
                    f.write("%s %s\\n" % (os.path.basename(__file__), v))
        """)
        plants = {
            "test_a1_setupmodule.py": textwrap.dedent("""\
                import os

                def setUpModule():
                    os.environ["ROMP_SESSIONS_FILE"] = os.path.join(os.environ["ROMP_TEST_PLANT_DIR"], "a1-sessions.json")

                def test_one():
                    pass
            """),
            "test_b1_setupclass.py": textwrap.dedent("""\
                import os, unittest

                class Seam(unittest.TestCase):
                    @classmethod
                    def setUpClass(cls):
                        os.environ["ROMP_SESSIONS_FILE"] = os.path.join(os.environ["ROMP_TEST_PLANT_DIR"], "b1-sessions.json")

                    def test_one(self):
                        pass
            """),
            "test_c1_module_fixture.py": textwrap.dedent("""\
                import os, pytest

                @pytest.fixture(scope="module", autouse=True)
                def _seam():
                    os.environ["ROMP_SESSIONS_FILE"] = os.path.join(os.environ["ROMP_TEST_PLANT_DIR"], "c1-sessions.json")
                    yield

                def test_one():
                    pass
            """),
            "test_d1_port_left.py": textwrap.dedent("""\
                import os

                def tearDownModule():
                    os.environ["ROMP_POSTAL_PORT"] = "45679"

                def test_one():
                    pass
            """),
        }
        after_port = textwrap.dedent("""\
            import os

            def test_the_port_is_popped_for_the_test():
                assert os.environ.get("ROMP_POSTAL_PORT") is None
        """)
        modules = dict(plants, **{"test_a2_later.py": later, "test_b2_later.py": later, "test_c2_later.py": later,
                                  "test_d2_after_the_port.py": after_port})
        marker = os.path.join(tempfile.mkdtemp(), "inherited.txt")
        self.addCleanup(shutil.rmtree, os.path.dirname(marker), True)
        plant_dir = os.path.dirname(marker)
        rc, out, _d = self._scratch_conftest_run(modules, env={"ROMP_TEST_MODULE_ENV_MARKER": marker, "ROMP_TEST_PLANT_DIR": plant_dir,
                                                               "ROMP_SESSIONS_FILE": None})
        with open(marker, encoding="utf-8") as f:
            inherited = dict(line.split(" ", 1) for line in f.read().splitlines())
        self.assertEqual(inherited,
                         {"test_%s2_later.py" % p: os.path.join(plant_dir, "%s1-sessions.json" % p) for p in "abc"},
                         "each later module's child inherits the value its planted module wrote: %s" % out[-2000:])
        self.assertEqual(rc, 1, "the run is red on the planted modules: %s" % out[-3000:])
        self.assertIn("8 passed, 4 errors", out, "every test passes; the four errors are the planted modules' teardowns")
        named = sorted(set(re.findall(r"module (test_\w+\.py) left the environment changed after its teardown", out)))
        self.assertEqual(named, sorted(plants), "each planted module is named, and no other: %s" % out[-3000:])
        self.assertIn("module test_a1_setupmodule.py left the environment changed after its teardown: ROMP_SESSIONS_FILE was "
                      "unset and is now set", out, "the setUpModule plant: the snapshot precedes setUpModule")
        self.assertIn("module test_d1_port_left.py left the environment changed after its teardown: ROMP_POSTAL_PORT was unset "
                      "and is now set", out, "the port a module leaves set is named against its floor")

    def test_every_watched_name_is_popped_at_import_so_a_shell_carrying_each_leaves_both_checks_green(self):
        """The verifier's finding on round 2 of fork PR #894: conftest popped ROMP_POSTAL_PORT at import and no other name
        _module_env_restored watches, and the postal modules put peers and client-only back with a pop in their tearDowns,
        so from a shell carrying ROMP_POSTAL_PEERS or ROMP_POSTAL_CLIENT_ONLY a run ended those modules with the name unset
        and was red where a clean shell's run was green. conftest now pops every watched name at import: the names its
        module-level os.environ.pop lines name (_conftest_import_pops) include all of MODULE_WATCHED_ENV_NAMES. Executed:
        a child pytest (a copy of tests/conftest.py) from a shell carrying none of the six records the floor each has at
        setUpModule; then a module whose setUpModule records what it found and whose test sets every name the floor leaves
        unset (the port aside) in setUp and pops it in tearDown (the postal modules' shape) runs from that clean shell and
        from a shell carrying all six. Both runs find the floor and are green, neither check naming anything: the shell
        changes nothing the checks read. The floor is read rather than assumed unset, so a conftest that floors
        client-only "1" (upstream's PR 1848, which fork PR #875 folds) holds too. Before round 2's seventh commit on fork
        PR #894 the run from the carrying shell was red: the module named for the five names and the test for the three
        seams the per-test check watches."""
        from tests import conftest
        watched = tuple(conftest.MODULE_WATCHED_ENV_NAMES)
        self.assertEqual(sorted(set(watched) - _conftest_import_pops()), [], "every watched name is popped at conftest's import")
        record = textwrap.dedent("""\
            import json, os
            NAMES = %r

            def setUpModule():
                with open(os.environ["ROMP_TEST_SHELL_MARKER"], "w") as f:
                    json.dump({k: os.environ.get(k) for k in NAMES}, f)
        """) % (watched,)
        clean = {name: None for name in watched}

        def run(body, env):
            marker = os.path.join(tempfile.mkdtemp(), "found.json")
            self.addCleanup(shutil.rmtree, os.path.dirname(marker), True)
            rc, out, _d = self._scratch_conftest_run({"test_postal_shape.py": body}, env=dict(env, ROMP_TEST_SHELL_MARKER=marker))
            with open(marker, encoding="utf-8") as f:
                return rc, out, json.load(f)
        rc, out, floor = run(record + "\n\ndef test_one():\n    pass\n", clean)
        self.assertEqual((rc, sorted(floor)), (0, sorted(watched)), out[-3000:])
        shape = record + textwrap.dedent("""\


            import unittest
            SET = %r

            class PostalShape(unittest.TestCase):
                def setUp(self):
                    for k in SET:
                        os.environ[k] = "set-in-setup"

                def tearDown(self):
                    for k in SET:
                        os.environ.pop(k, None)

                def test_one(self):
                    pass
        """) % (tuple(k for k in watched if floor[k] is None and k != "ROMP_POSTAL_PORT"),)
        shell = {name: "-".join(("shell", name.lower(), "value")) for name in watched}
        shell["ROMP_POSTAL_PORT"] = "45681"
        for label, env in (("a clean shell", clean), ("a shell carrying all six", shell)):
            rc, out, found = run(shape, env)
            self.assertEqual(found, floor, "%s: setUpModule finds the floor: %s" % (label, out[-6000:]))
            self.assertEqual(re.findall(r"left (?:the environment|shared state) changed", out), [], "%s: %s" % (label, out[-6000:]))
            self.assertEqual(rc, 0, "%s: %s" % (label, out[-6000:]))
            self.assertIn("1 passed", out, label)

    def test_a_write_by_a_fixture_scoped_above_module_is_named_by_each_check_whose_snapshot_its_setup_follows(self):
        """THE PLANTS for the class conftest's comment above _module_env_restored names (the verifier's findings on round
        2 of fork PR #894: its plants showed the module check naming a module whose second test first requested a session
        fixture, and then both checks naming a session fixture the module's first test requested at run time, where the
        texts had keyed on which test first uses the fixture). Child pytests (a copy of tests/conftest.py), each over a
        planted module that writes ROMP_SESSIONS_FILE with no restore from a fixture scoped above module, and a later
        module whose test spawns a child that reports the value it inherited. Every later child inherits the planted
        value; what decides which check names the write is whether the fixture's setup follows that check's snapshot.
        Requested by name (a test's signature, a fixture's signature, or autouse), pytest sets the fixture up before the
        requesting test's module- and function-scoped fixtures: for the first test to be set up, before both snapshots,
        so neither check names it (session and package, autouse or requested, by the test or through a module fixture's
        signature); first for the second test, after the module's snapshot and before that test's, so only the module
        check names it. Requested at run time (request.getfixturevalue), it is set up where the call runs: in a test's
        body, the first's or the second's, or in a function-scoped fixture the first test requests, after that test's
        snapshot, so the per-test check names the test and the module check the module; in a module-scoped fixture the
        first test requests, after the module's snapshot and before the test's, so only the module check names it. The
        first test to be set up is what counts, not the module's first (the verifier's findings on round 2 of fork PR
        #894, where the texts had keyed on the module's first test, and then counted a skip in a session or package
        fixture as set up). When the module's first test is ended before its module-scoped fixtures are set up, it sets
        up none of them, and a session fixture the second test requests by name is named by neither check: a skipif or a
        skip mark, an xfail mark with run=False, a skip in the setup of a session fixture it requests by name, through a
        function fixture or by a usefixtures mark, a skip in the setup of a package fixture it requests by name, an
        error in the setup of a session fixture it requests, and a skip by a conftest's pytest_runtest_setup, which runs
        before pytest's runner sets the test's fixtures up. A session fixture that is autouse and skips ends the second
        test as well, so nothing writes the value and the later child inherits none. When the first test is ended after
        that point it was set up, and the module check names the module: a skip in its body, in a module-, class- or
        function-scoped fixture it requests, in setUpModule (which skips the second test too, after the session fixture
        that test requests has written the value), in setUpClass, by a unittest skip decorator on its method or its
        class, or by a conftest's pytest_runtest_setup marked trylast, which runs after the runner's, and an xfail mark
        with run=False under --runxfail, which runs it. The two hook cases put the hook in a pkg/conftest.py beside the
        planted modules (the verifier's finding on round 2 of fork PR #894, where the texts' lists of routes had left a
        conftest's hook out). The child's PYTEST_ADDOPTS is popped in every case but that last one, which sets
        --runxfail there."""
        later = textwrap.dedent("""\
            import os, subprocess, sys

            def test_a_child_reports_what_it_inherited():
                v = subprocess.run([sys.executable, "-c", "import os; print(os.environ.get('ROMP_SESSIONS_FILE'))"],
                                   capture_output=True, text=True, timeout=60).stdout.strip()
                with open(os.environ["ROMP_TEST_MODULE_ENV_MARKER"], "w") as f:
                    f.write(v)
        """)
        seam = textwrap.dedent("""\
            import os, pytest, unittest

            @pytest.fixture(scope=%r, autouse=%r)
            def seam():
                os.environ["ROMP_SESSIONS_FILE"] = os.path.join(os.environ["ROMP_TEST_PLANT_DIR"], "planted.json")
                yield


            @pytest.fixture(scope="module")
            def mod_by_name(seam):
                yield


            @pytest.fixture(scope="module")
            def mod_at_run_time(request):
                request.getfixturevalue("seam")
                yield


            @pytest.fixture
            def fn_at_run_time(request):
                request.getfixturevalue("seam")
                yield


            %s


            def test_two(%s):
                %s
        """)
        at_run_time = ("request", "request.getfixturevalue('seam')")

        def plant(scope, autouse, first=("", "pass"), second=("", "pass"), first_def=None):
            return seam % ((scope, autouse, first_def or "def test_one(%s):\n    %s" % first) + second)

        def behind(first_def):
            return plant("session", False, second=("seam", "pass"), first_def=first_def)

        def gate(scope, body="pytest.skip('synthetic')", autouse=False):
            return "@pytest.fixture(scope=%r, autouse=%r)\ndef skip_gate():\n    %s\n\n\n" % (scope, autouse, body)

        def hook(mark=""):
            return ("import pytest\n\n\n%sdef pytest_runtest_setup(item):\n    if item.name == 'test_one':\n"
                    "        pytest.skip('synthetic')\n" % mark)
        cases = [("a session fixture that is autouse", "", plant("session", True), [], []),
                 ("a session fixture the first test requests by name", "", plant("session", False, ("seam", "pass")),
                  [], []),
                 ("a session fixture only the second test requests by name", "",
                  plant("session", False, second=("seam", "pass")), [], ["test_p1.py"]),
                 ("a package fixture that is autouse", "pkg/", plant("package", True), [], []),
                 ("a package fixture only the second test requests by name", "pkg/",
                  plant("package", False, second=("seam", "pass")), [], ["pkg/test_p1.py"]),
                 ("a session fixture named in the signature of a module fixture the first test requests", "",
                  plant("session", False, ("mod_by_name", "pass")), [], []),
                 ("a session fixture the first test's body requests at run time", "",
                  plant("session", False, at_run_time), ["test_p1.py::test_one"], ["test_p1.py"]),
                 ("a session fixture the second test's body requests at run time", "",
                  plant("session", False, second=at_run_time), ["test_p1.py::test_two"], ["test_p1.py"]),
                 ("a package fixture the first test's body requests at run time", "pkg/",
                  plant("package", False, at_run_time), ["pkg/test_p1.py::test_one"], ["pkg/test_p1.py"]),
                 ("a session fixture a function fixture the first test requests asks for at run time", "",
                  plant("session", False, ("fn_at_run_time", "pass")), ["test_p1.py::test_one"], ["test_p1.py"]),
                 ("a session fixture a module fixture the first test requests asks for at run time", "",
                  plant("session", False, ("mod_at_run_time", "pass")), [], ["test_p1.py"]),
                 ("a session fixture the second test requests by name, the first skipped by a skipif mark", "",
                  behind("@pytest.mark.skipif(True, reason='synthetic')\ndef test_one():\n    pass"), [], [],
                  "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first skipped by a skip mark", "",
                  behind("@pytest.mark.skip(reason='synthetic')\ndef test_one():\n    pass"), [], [],
                  "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first ended by xfail(run=False)", "",
                  behind("@pytest.mark.xfail(run=False, reason='synthetic')\ndef test_one():\n    pass"), [], [],
                  "2 passed, 1 xfailed"),
                 ("a session fixture the second test requests by name, the first skipped in its body", "",
                  behind("def test_one():\n    pytest.skip('synthetic')"), [], ["test_p1.py"], "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first a unittest method skip", "",
                  behind("class TestOne(unittest.TestCase):\n    @unittest.skip('synthetic')\n    def test_one(self):\n"
                         "        pass"), [], ["test_p1.py"], "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first in a unittest class skip", "",
                  behind("@unittest.skip('synthetic')\nclass TestOne(unittest.TestCase):\n    def test_one(self):\n"
                         "        pass"), [], ["test_p1.py"], "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first skipped by a session fixture it "
                  "requests by name", "", behind(gate("session") + "def test_one(skip_gate):\n    pass"), [], [],
                  "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first skipped by a package fixture it "
                  "requests by name", "pkg/", behind(gate("package") + "def test_one(skip_gate):\n    pass"), [], [],
                  "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first skipped by a session fixture a "
                  "function fixture it requests requests", "",
                  behind(gate("session") + "@pytest.fixture\ndef through_gate(skip_gate):\n    yield\n\n\n"
                         "def test_one(through_gate):\n    pass"), [], [], "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first skipped by a session fixture its "
                  "usefixtures mark names", "",
                  behind(gate("session") + "@pytest.mark.usefixtures('skip_gate')\ndef test_one():\n    pass"), [], [],
                  "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first erroring in the setup of a session "
                  "fixture it requests by name", "",
                  behind(gate("session", "raise RuntimeError('synthetic')") + "def test_one(skip_gate):\n    pass"), [],
                  [], "2 passed, 1 error", {"rc": 1}),
                 ("a session fixture the second test requests by name, an autouse session fixture skipping both", "",
                  behind(gate("session", autouse=True) + "def test_one():\n    pass"), [], [], "1 passed, 2 skipped",
                  {"inherits": False}),
                 ("a session fixture the second test requests by name, the first skipped by a module fixture it "
                  "requests", "", behind(gate("module") + "def test_one(skip_gate):\n    pass"), [], ["test_p1.py"],
                  "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first skipped by a class fixture it "
                  "requests", "", behind(gate("class") + "def test_one(skip_gate):\n    pass"), [], ["test_p1.py"],
                  "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first skipped by a function fixture it "
                  "requests", "", behind(gate("function") + "def test_one(skip_gate):\n    pass"), [], ["test_p1.py"],
                  "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first in a class whose setUpClass skips", "",
                  behind("class TestOne(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n"
                         "        raise unittest.SkipTest('synthetic')\n\n    def test_one(self):\n        pass"), [],
                  ["test_p1.py"], "2 passed, 1 skipped"),
                 ("a session fixture the second test requests by name, the first skipped by a conftest's "
                  "pytest_runtest_setup, which runs before the runner's", "pkg/", behind("def test_one():\n    pass"),
                  [], [], "2 passed, 1 skipped", {"files": {"pkg/conftest.py": hook()}}),
                 ("a session fixture the second test requests by name, the first skipped by a conftest's "
                  "pytest_runtest_setup marked trylast, which runs after the runner's", "pkg/",
                  behind("def test_one():\n    pass"), [], ["pkg/test_p1.py"], "2 passed, 1 skipped",
                  {"files": {"pkg/conftest.py": hook("@pytest.hookimpl(trylast=True)\n")}}),
                 ("a session fixture the second test requests by name, the first in a module whose setUpModule skips",
                  "", behind("def setUpModule():\n    raise unittest.SkipTest('synthetic')\n\n\ndef test_one():\n"
                             "    pass"), [], ["test_p1.py"], "1 passed, 2 skipped"),
                 ("a session fixture the second test requests by name, the first under xfail(run=False) with "
                  "--runxfail", "", behind("@pytest.mark.xfail(run=False, reason='synthetic')\ndef test_one():\n    pass"),
                  [], ["test_p1.py"], "3 passed", {"env": {"PYTEST_ADDOPTS": "--runxfail"}})]
        for case in cases:
            label, where, text, per_test_expected, module_expected = case[:5]
            tally = case[5] if len(case) > 5 else "3 passed"
            opts = case[6] if len(case) > 6 else {}
            plant_dir = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, plant_dir, True)
            marker = os.path.join(plant_dir, "inherited.txt")
            modules = {where + "test_p1.py": text, where + "test_p2_later.py": later}
            if where:
                modules[where + "__init__.py"] = ""
            modules.update(opts.get("files", {}))
            env = {"ROMP_TEST_MODULE_ENV_MARKER": marker, "ROMP_TEST_PLANT_DIR": plant_dir, "ROMP_SESSIONS_FILE": None,
                   "PYTEST_ADDOPTS": None}
            env.update(opts.get("env", {}))
            rc, out, _d = self._scratch_conftest_run(modules, env=env)
            inherits = os.path.join(plant_dir, "planted.json") if opts.get("inherits", True) else "None"
            with open(marker, encoding="utf-8") as f:
                self.assertEqual(f.read(), inherits, "%s: the later module's child inherits %s: %s"
                                 % (label, "the planted value" if opts.get("inherits", True) else "nothing", out[-3000:]))
            # a check's message can appear more than once (the error, an exception group's copy of it, the summary line),
            # and the fail call's source line can be quoted with its %s, so the names are compared as sets, %s excluded
            per_test = sorted(set(re.findall(r"([^\s%]\S*\.py::\S+) left shared state changed after its teardown", out)))
            self.assertEqual(per_test, per_test_expected, "%s: the per-test check names %s: %s"
                             % (label, per_test_expected or "nothing", out[-3000:]))
            named = sorted(set(re.findall(r"module ([^\s%]\S*) left the environment changed after its teardown", out)))
            self.assertEqual(named, module_expected, "%s: the module check names %s: %s"
                             % (label, module_expected or "nothing", out[-3000:]))
            self.assertEqual(rc, opts.get("rc", 1 if per_test_expected or module_expected else 0), "%s: %s" % (label, out[-3000:]))
            self.assertIn(tally, out, label)

    def test_no_fixture_in_the_tree_is_scoped_above_module(self):
        """The class conftest's environment checks read only in part (the verifier's findings on round 2 of fork PR
        #894): a watched name a session- or package-scoped fixture writes is read by a check only when the fixture's
        setup follows that check's snapshot, and one set up before both, as one requested by name by the first of the
        module's tests to be set up is, reaches every later module unread (the executed plants in
        test_a_write_by_a_fixture_scoped_above_module_is_named_by_each_check_whose_snapshot_its_setup_follows).
        conftest's comment above _module_env_restored and tests/README.md name the class; the tree has no such fixture,
        and the list _fixtures_scoped_above_module derives is held EQUAL to empty. Over a planted tree it lists a
        session fixture, a package fixture, a fixture imported by its bare name and one whose scope is a name; a fixture
        registered by a call applied to its function, or passed it, a decorator imported under another name or bound to
        one by an assignment, every name of a chained assignment, both of two (`ch1 = ch2 = pytest.fixture`) and each
        of three (`ch3 = ch4 = ch5 = pytest.fixture`, a fixture under each name, so a scan that reads any two of the
        three targets misses one: the first and the last miss ch4's, the first two ch5's, the last two ch3's; the
        verifier's findings on round 2 of fork PR #894), an alias bound before the binding it copies in the walk's
        order (read on the fixed point's second pass; the fixed point itself is held by
        test_the_fixture_spelling_scan_follows_an_alias_chain_to_the_pass_that_adds_nothing), a factory held in a name,
        and wrapper defs; yield_fixture as an attribute, by its bare name and under an as-name a from-import gives it;
        and a parametrization's scope above module, by keyword, as the fifth argument (also in a file whose text has
        neither fixture nor scope=) and on metafunc.parametrize. It does not list a module or a class fixture, a
        parametrization scoped to module or None, nor the routes its docstring names as unread (a scope through **kwargs
        or *args, functools.partial, getattr, an annotated assignment, a tuple target, a walrus, a for target, a
        conditional expression's value, a class attribute, a name bound to parametrize, pytest's private
        _register_fixture, and a name the planted tree's sub/helpers.py binds to pytest.fixture, taken by a from-import
        under that name, under an as-name, and by a star import, the verifier's finding on round 2 of fork PR #894), so
        the list is known to fill when a read one appears and the unread list is known to be true."""
        self.maxDiff = None
        self.assertEqual(_fixtures_scoped_above_module(), [], "no fixture under tests/ is scoped above module")
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        os.makedirs(os.path.join(d, "sub"))
        with open(os.path.join(d, "sub", "test_planted.py"), "w", encoding="utf-8") as f:
            f.write(textwrap.dedent("""\
                import functools
                import pytest
                import pytest as pt
                from pytest import fixture
                from pytest import fixture as fx
                from pytest import yield_fixture
                from pytest import yield_fixture as yfx
                from sub.helpers import imported_fx
                from sub.helpers import imported_fx as renamed_fx
                from sub.helpers import *
                SCOPE = "session"
                OPTS = {"scope": "session"}
                PARGS = ("a", [1], True, None, "session")
                alias = pytest.fixture
                alias2 = alias

                @pytest.fixture(scope="session")
                def a():
                    yield

                @pytest.fixture(autouse=True, scope="package")
                def b():
                    yield

                @fixture(scope="session")
                def c():
                    yield

                @pytest.fixture(scope=SCOPE)
                def d():
                    yield

                @pytest.fixture(scope="module")
                def e():
                    yield

                @pytest.fixture(scope="class")
                def f():
                    yield

                def g_body():
                    yield

                g = pt.fixture(scope="session", autouse=True, name="g")(g_body)

                def h_body():
                    yield

                h = pytest.fixture(h_body, scope="package")

                @fx(scope="session")
                def i():
                    yield

                def j_body():
                    yield

                j = alias2(scope="session")(j_body)

                sess = pytest.fixture(scope="session")

                @sess
                def k():
                    yield

                def session_fixture(fn):
                    return pytest.fixture(scope="session")(fn)

                def make(scope):
                    return pytest.fixture(scope=scope)

                m = pytest.fixture(scope="module")(g_body)

                @pytest.fixture(**OPTS)
                def u1():
                    yield

                u2_factory = functools.partial(pytest.fixture, scope="session")

                @u2_factory
                def u2():
                    yield

                @getattr(pytest, "fixture")(scope="session")
                def u3():
                    yield

                try:
                    late = pytest.fixture
                except AttributeError:
                    late = None
                late2 = late

                @late2(scope="session")
                def n():
                    yield

                @pytest.yield_fixture(scope="session")
                def y1():
                    yield

                @yield_fixture(scope="package")
                def y2():
                    yield

                @yfx(scope="session", autouse=True)
                def y3():
                    yield

                @pytest.mark.parametrize("a", [1], indirect=True, scope="session")
                def test_p1(a):
                    pass

                @pytest.mark.parametrize("a", [1], True, None, "package")
                def test_p2(a):
                    pass

                @pytest.mark.parametrize("a", [1], indirect=True, scope="module")
                def test_p3(a):
                    pass

                @pytest.mark.parametrize("a", [1], indirect=True, scope=None)
                def test_p4(a):
                    pass

                def pytest_generate_tests(metafunc):
                    metafunc.parametrize("a", [1], indirect=True, scope="session")

                @pytest.mark.parametrize(*PARGS)
                def test_u4(a):
                    pass

                ann: object = pytest.fixture

                @ann(scope="session")
                def u5():
                    yield

                class Holder:
                    held = pytest.fixture

                @Holder.held(scope="session")
                def u6():
                    yield

                par = pytest.mark.parametrize

                @par("a", [1], indirect=True, scope="session")
                def test_u7(a):
                    pass

                def pytest_configure(config):
                    config.pluginmanager.get_plugin("funcmanage")._register_fixture(name="u8", func=g_body, nodeid="",
                                                                                    scope="session")

                ch1 = ch2 = pytest.fixture

                @ch1(scope="session")
                def o1():
                    yield

                @ch2(scope="package")
                def o2():
                    yield

                tup, spare = pytest.fixture, None

                @tup(scope="session")
                def u9():
                    yield

                if (wal := pytest.fixture):
                    pass

                @wal(scope="session")
                def u10():
                    yield

                for looped in (pytest.fixture,):
                    pass

                @looped(scope="session")
                def u11():
                    yield

                cond = pytest.fixture if SCOPE else None

                @cond(scope="session")
                def u12():
                    yield

                @imported_fx(scope="session")
                def u13():
                    yield

                @renamed_fx(scope="session")
                def u14():
                    yield

                @starred_fx(scope="session")
                def u15():
                    yield

                ch3 = ch4 = ch5 = pytest.fixture

                @ch3(scope="package")
                def o3():
                    yield

                @ch4(scope="session")
                def o4():
                    yield

                @ch5(scope="session")
                def o5():
                    yield
            """))
        with open(os.path.join(d, "sub", "helpers.py"), "w", encoding="utf-8") as f:
            f.write("import pytest\n\nimported_fx = pytest.fixture\nstarred_fx = pytest.fixture\n")
        with open(os.path.join(d, "sub", "test_positional.py"), "w", encoding="utf-8") as f:
            f.write(textwrap.dedent("""\
                import pytest

                @pytest.mark.parametrize("a", [1], True, None, "session")
                def test_q(a):
                    pass
            """))
        at = os.path.join("sub", "test_planted.py")
        self.assertEqual([(p, n, sc) for p, _line, n, sc in _fixtures_scoped_above_module(d)],
                         [(at, "a", "'session'"), (at, "b", "'package'"), (at, "c", "'session'"), (at, "d", "SCOPE"),
                          (at, "g_body", "'session'"), (at, "h_body", "'package'"), (at, "i", "'session'"),
                          (at, "j_body", "'session'"), (at, "?", "'session'"), (at, "fn", "'session'"),
                          (at, "?", "scope"), (at, "n", "'session'"), (at, "y1", "'session'"), (at, "y2", "'package'"),
                          (at, "y3", "'session'"), (at, "test_p1", "'session'"), (at, "test_p2", "'package'"),
                          (at, "?", "'session'"), (at, "o1", "'session'"), (at, "o2", "'package'"),
                          (at, "o3", "'package'"), (at, "o4", "'session'"), (at, "o5", "'session'"),
                          (os.path.join("sub", "test_positional.py"), "test_q", "'session'")])

    def test_the_fixture_spelling_scan_follows_an_alias_chain_to_the_pass_that_adds_nothing(self):
        """_fixture_spellings's fixed point, run (the verifier's finding on round 2 of fork PR #894: with the loop cut
        to two passes the planted tree's two-link chain was still read, so no test failed). A chain of LINKS aliases,
        each link's source nested one level deeper than the link, so ast.walk (breadth-first) reaches every link before
        its source and the scan as written reads one link a pass: `c0 = pytest.fixture` at the deepest level, `c1 = c0`
        one level up, and so on to the module-level name the session fixture's decorator calls. For every length from
        one to six the scan lists the fixture, and the passes it records are all True up to one final False: the loop
        runs until a pass adds no name, and stops there. A loop cut to any fixed number of passes fails on some length:
        fewer passes than a chain needs miss its fixture or end on a pass that added a name, and more add a pass that
        adds nothing before the last."""
        for links in range(1, 7):
            lines = ["import pytest", ""]
            for depth in range(links):
                link = links - 1 - depth
                lines.append("    " * depth + ("c0 = pytest.fixture" if link == 0 else "c%d = c%d" % (link, link - 1)))
                if depth < links - 1:
                    lines.append("    " * depth + "if True:")
            lines += ["", "", "@c%d(scope='session')" % (links - 1), "def f():", "    yield", ""]
            text = "\n".join(lines)
            d = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, d, True)
            with open(os.path.join(d, "test_chain.py"), "w", encoding="utf-8") as f:
                f.write(text)
            self.assertEqual([(p, n, sc) for p, _line, n, sc in _fixtures_scoped_above_module(d)],
                             [("test_chain.py", "f", "'session'")],
                             "a chain of %d links is followed: %s" % (links, text))
            passes = []
            names = _fixture_spellings(ast.parse(text), passes)
            self.assertLessEqual({"c%d" % i for i in range(links)}, names, text)
            self.assertEqual(passes, [True] * (len(passes) - 1) + [False],
                             "a chain of %d links: the loop stops on the first pass that adds no name, not before and "
                             "not after: %s" % (links, passes))

    def test_the_scan_completes_and_derives_the_same_records_under_a_tag_another_census_left_on_the_parsers_shared_singletons(self):
        """THE PLANT for the contract _fresh states (the reviewer's ruling of 2026-09-22, from a CI red on fork PR #891):
        the tag another census writes over every node it walks (`child._parent = node`) put on the parser's Load
        singleton, the parent the root of a chain of 5000 plain objects, and the walker's derivation run over the
        smallest input whose value check reaches _resolved, one module-level environment write whose value is a bound
        name. At the third commit `_Substitute.visit_Name` and `_resolved` deep-copied the parsed node, whose ctx IS the
        tagged singleton, and the copy followed the tag down the chain: a RecursionError on 3.12 and on 3.10. Both
        substitute over a fresh parse of the expression's text now, so the tag is never followed, the records equal the
        untagged run's and the licence's value check reads the resolved value. The singleton's dict is put back by a
        cleanup registered before the write, since every test in the process shares it."""
        load = _parser_singletons()["Load"]
        src = 'import os\nimport tempfile\n_ROOT = tempfile.mkdtemp()\nos.environ["XDG_STATE_HOME"] = _ROOT\n'
        untagged = _module_level_records(ast.parse(src), "planted.py")
        self.assertEqual([(name, r.value, r.resolved) for name, r in untagged], [("XDG_STATE_HOME", "_ROOT", "tempfile.mkdtemp()")],
                         "the smallest input: one write, its value a bound name, so _resolved substitutes through visit_Name")
        chain = None
        for _ in range(5000):
            chain = _Link(chain)
        self.addCleanup(_restore_dict, load, dict(vars(load)))
        load._parent = chain
        tagged = _module_level_records(ast.parse(src), "planted.py")
        self.assertEqual(tagged, untagged, "the walk under the tag completes and derives the records the untagged walk did")
        records = _all_licensed_once()
        records["XDG_STATE_HOME"] = [r for _name, r in tagged]
        self.assertEqual(_licence_faults(records), [], "the licence's value check reads the resolved value under the tag")

    def test_a_census_walk_that_writes_on_a_parser_singleton_is_refused_by_its_build_and_held_as_nothing(self):
        """The contract's read-only clause, for this walker, held by the census's build (the reviewer's ruling of round 1
        on fork PR #894: this pin walked the whole tree a second time and compared the parser's singletons before and
        after, and once the census reads one held derivation a before and after around a held read proves nothing). The
        build checks the parser's shared singleton nodes (one object each for the process; a write on one is on every
        tree parsed after it) before and after it runs (tests/parse_cache.py's check_singletons, the check
        parse_cache.derived ran around the build until the reviewer's ruling of 2026-09-24 took derived() out of this
        module) and refuses a build that wrote on one, so the whole-tree derivation the census pin reads passed that check
        when it was built. THE PLANT: the census's walker, wrapped to write the tag another census's walker once left on
        every node (`_parent`, fork PR #891's census before the ruling) on the parser's Load singleton, derives a
        one-module tree: the build raises AssertionError naming itself as the build that wrote it and the attribute, and
        nothing is held (after the tag is put back, the next read builds again: two builds of the path tuple in the
        module's run); unplanted, that build derives the module's one write and leaves the singletons as it found them. A
        build without the check would raise nothing here."""
        load = _parser_singletons()["Load"]
        singletons = _parser_singletons()
        before = {kind: dict(vars(node)) for kind, node in singletons.items()}
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "test_singleton_plant.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write('import os\nos.environ["ROMP_KERNEL_NO_OPEN"] = "1"\n')
        me = sys.modules[_census_build.__module__]
        walker = me._module_level_records
        saved = dict(vars(load))
        self.addCleanup(_restore_dict, load, saved)
        self.addCleanup(setattr, me, "_module_level_records", walker)

        def tagging(tree, module, root=None):
            load._parent = tree                      # the planted write on a node the parser shares with every tree
            return walker(tree, module, root)
        me._module_level_records = tagging
        try:
            with self.assertRaises(AssertionError) as caught:
                module_level_env_census([path])
        finally:
            me._module_level_records = walker
            _restore_dict(load, saved)
        message = str(caught.exception)
        self.assertIn("after the census build over 1 path (tests/test_hermetic_kernel_postal.py): the build itself wrote them", message)
        self.assertIn("Load carries _parent (Module)", message)
        self.assertEqual(((path,) in _held()["derivations"], _CENSUS_BUILDS[(path,)]), (False, 1),
                         "the refused build was counted and not held")
        n, counts, records = module_level_env_census([path])
        self.assertEqual((n, counts), (1, {"ROMP_KERNEL_NO_OPEN": {"assignment": 1}}))
        self.assertEqual(_CENSUS_BUILDS[(path,)], 2, "nothing was held: the next read built again")
        after = {kind: dict(vars(node)) for kind, node in singletons.items()}
        self.assertEqual(after, before, "the unplanted walk writes no attribute on a node: per-node data belongs in a side "
                                        "table keyed by id(node)")

    def test_the_resolver_reads_an_imported_module_through_the_census_own_parse(self):
        """_module_at, the resolver's reader of a module a call at import leads into, reads it through the census's own
        parse like the census loop (_own_tree; round 1 of fork PR #894 ruled one parse per file for the two, and the
        reviewer's second ruling of 2026-09-24 moved that parse out of tests/parse_cache.py by measurement): a synthetic
        module that calls test_asm_checkpoint.kernel_module() at import is censused, the write is read through the call,
        the record the resolver holds for test_asm_checkpoint.py is built over THE tree the census holds for the file (the
        same object), and the file was parsed once in the module's run. A _module_at that parsed the file itself, or read
        it through parse_cache, would hold a tree of its own, which the census's parse counter does not see; the identity
        does."""
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "test_reads_through.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write("import os\nfrom test_asm_checkpoint import kernel_module\nkernel_module()\n")
        _n, counts, records = module_level_env_census([path])
        self.assertEqual(counts, {"ROMP_KERNEL_NO_OPEN": {"setdefault": 1}})
        self.assertIn("kernel_module() at", records["ROMP_KERNEL_NO_OPEN"][0].via)
        asm = os.path.realpath(os.path.join(HERE, "test_asm_checkpoint.py"))
        self.assertIs(_held()["modules"][(asm, HERE)].tree, _held()["trees"][asm],
                      "the resolver's record of the imported module is built over the census's own tree of it")
        self.assertEqual(_OWN_PARSES[asm], 1, "the imported module was parsed once in this module's run")

    def test_the_target_scan_names_only_the_files_an_import_statement_names(self):
        """The files whose tree the census loop keeps past its walk, held plant by plant (the verifier's findings at round
        2's nineteenth and twentieth commits of fork PR #894: the drop had no pin, and then the pieces planted here were
        the scan's two pure parts alone, so a widening in _resolver_targets' own loop, every file returned or every
        identifier read, passed). THE PURE PARTS: _import_statement_words reads the lines that hold the word `import`
        and nothing else: a name used on another line is not among its words, `important` is not the word, a
        parenthesized list is read to the line that closes it (a parenthesis in a comment not counted), a backslash
        continuation is joined, and a docstring line with the word adds its words too (the safe side the scan's
        docstring names). _named_by keeps a file whose module name, or a package's directory name for its __init__.py,
        is among the words, and no other. THE WHOLE FUNCTION, and the census pin's own reader beside it
        (_import_line_named_files): each runs over a synthetic tree standing in for tests/ and names exactly the files
        an import line names there: a module and a package imported, a submodule named in a `from` import, two names of
        a parenthesized list that a comment's parenthesis does not close, a module joined by a backslash continuation,
        and a module named on a docstring's import line (the rule's safe side); and not a module named only on another
        line, one named after the list closes, one reached through importlib.import_module, nor the file that imports
        them. A census over no file under tests/ has no target."""
        words = _import_statement_words('import os\nx = helper_one\n"""import helper_two"""\nimportant = helper_three\n'
                                        'from pkg.sub import (a,  # b (\n    c)\nd = helper_four\nfrom e \\\n    import f\n')
        self.assertEqual(sorted(words), sorted({"import", "os", "helper_two", "from", "pkg", "sub", "a", "b", "c", "e", "f"}),
                         "the words of the lines that hold an import statement, and of no other line")
        d = os.path.join(os.sep, "nonexistent-tests-root")
        paths = [os.path.join(d, "test_one.py"), os.path.join(d, "helper_two.py"), os.path.join(d, "pkg", "__init__.py"),
                 os.path.join(d, "pkg", "helper_three.py")]
        self.assertEqual(sorted(_named_by(paths, words)), sorted(os.path.realpath(p) for p in paths[1:3]),
                         "a file is named by its module name, a package by its directory's, and a file no word names is not")
        self.assertEqual(_resolver_targets([os.path.join(d, "test_one.py")]), frozenset(), "no file under tests/: no target")
        self.assertEqual(_import_line_named_files([os.path.join(d, "test_one.py")]), frozenset(), "no file under tests/: none derived")
        root = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        files = {"test_a.py": ('import helper_x\nfrom pkg import sub_y\n"""a docstring line: import helper_w"""\n'
                               'value = helper_z\nfrom pkg2 import (\n    helper_p,  # a parenthesis ) in a comment\n'
                               '    helper_q)\nlater = helper_r\nfrom helper_b \\\n    import thing\n'
                               'import importlib\nmod = importlib.import_module("helper_i")\n'),
                 "pkg/__init__.py": "", "pkg/sub_y.py": "", "pkg2/__init__.py": "", "pkg3/__init__.py": ""}
        for name in ("helper_x", "helper_w", "helper_z", "helper_p", "helper_q", "helper_r", "helper_b", "helper_i"):
            files[name + ".py"] = ""
        for name, text in files.items():
            os.makedirs(os.path.dirname(os.path.join(root, name)), exist_ok=True)
            with open(os.path.join(root, name), "w", encoding="utf-8") as f:
                f.write(text)
        paths = sorted(os.path.join(root, name) for name in files)
        want = sorted(("helper_x.py", "pkg/__init__.py", "pkg/sub_y.py", "helper_w.py", "pkg2/__init__.py", "helper_p.py",
                       "helper_q.py", "helper_b.py"))
        for reader in (_resolver_targets, _import_line_named_files):
            self.assertEqual(sorted(os.path.relpath(p, root) for p in reader(paths, root=root)), want,
                             "%s over a synthetic tree names exactly the files its import lines name" % reader.__name__)

    def test_the_module_imports_no_copy_and_deep_copies_no_node(self):
        """The contract's no-deepcopy clause, held on this module's own tree rather than its text (a comment naming the
        call would not count): no import of copy, no call of copy.deepcopy, copy.copy or a bare deepcopy anywhere in
        the module, and no `copy` name among its globals. At the third commit `_Substitute.visit_Name` and `_resolved`
        each deep-copied a parsed node; both substitute over a fresh parse now (_fresh)."""
        tree = ast.parse(open(__file__, encoding="utf-8").read(), filename=__file__)
        imports = sorted(n.lineno for n in ast.walk(tree)
                         if (isinstance(n, ast.Import) and any(a.name.split(".")[0] == "copy" for a in n.names))
                         or (isinstance(n, ast.ImportFrom) and n.module == "copy"))
        copies = sorted(n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and (
            _dotted(n.func) in (["copy", "deepcopy"], ["copy", "copy"]) or (isinstance(n.func, ast.Name) and n.func.id == "deepcopy")))
        self.assertEqual((imports, copies, "copy" in globals()), ([], [], False),
                         "the contract (the reviewer, 2026-09-22): no consumer deep-copies a parsed node; a substitution runs over a "
                         "fresh parse of the expression's text (_fresh)")

    def test_the_module_touches_no_collector_state_and_derives_nothing_through_parse_cache(self):
        """Clause 1 of the reviewer's ruling of 2026-09-24 on round 2 of fork PR #894, held on this module's own tree (a
        comment or a string naming a call does not count): no gc.freeze, gc.disable, gc.collect, nor any other attribute
        of gc but the two reads of _COLLECTOR_READS (the freeze-count read the behavioural pin makes, and gc.get_objects,
        which the drop's pin by live objects reads ast objects in since round 2's thirty-second commit of fork PR #894;
        neither changes collector state), and no parse_cache.derived, however the module is imported
        (_collector_touches). Run over plants so the reader is known to see each spelling: each of those calls, another
        read of gc outside the two (gc.get_referrers), an attribute taken without a call, a name imported from gc, gc
        under an alias, and derived through each import road of tests/parse_cache.py (the package road, the script road,
        a dotted import) is named with its line; the two reads and a string that spells a call are not. What the reader
        does not see is in its docstring."""
        self.assertEqual(_collector_touches(ast.parse(open(__file__, encoding="utf-8").read(), filename=__file__)), [],
                         "the module changes no collector state and never derives through parse_cache.derived")
        head = "import gc\nfrom . import parse_cache as PC\n"
        for body, want in (("gc.freeze()\n", "gc.freeze"), ("gc.disable()\n", "gc.disable"), ("gc.collect()\n", "gc.collect"),
                           ("gc.enable()\n", "gc.enable"), ("gc.unfreeze()\n", "gc.unfreeze"), ("f = gc.freeze\n", "gc.freeze"),
                           ("r = gc.get_referrers(1)\n", "gc.get_referrers"),
                           ("PC.derived(('k',), list)\n", "PC.derived")):
            self.assertEqual(_collector_touches(ast.parse(head + body)), [(3, want)], body)
        for src, want in (("from gc import freeze\n", "from gc import freeze"), ("import gc as g\ng.collect()\n", "g.collect"),
                          ("import parse_cache as P\nP.derived(('k',), list)\n", "P.derived"),
                          ("import tests.parse_cache\ntests.parse_cache.derived(('k',), list)\n", "tests.parse_cache.derived")):
            self.assertEqual([w for _line, w in _collector_touches(ast.parse(src))], [want], src)
        self.assertEqual(_collector_touches(ast.parse(head + "n = gc.get_freeze_count()\no = gc.get_objects()\ns = 'gc.freeze()'\n")), [],
                         "the freeze-count read, the list of tracked objects and a string are not touches")


def _all_licensed_once():
    """Synthetic records: one licensed write per licensed name, from a test module, each meeting its licence (the input
    the planted-fault test adds one offending write to, so the equality half of the check is satisfied by construction
    and the one planted fault is the whole list)."""
    sample = {"XDG_STATE_HOME": "tempfile.mkdtemp()", "ROMP_STATE_DIR": "tempfile.TemporaryDirectory().name", "ROMP_SERVE_TOKEN": "'testtok'",
              "ROMP_KERNEL_NO_OPEN": "'1'", "ROMP_MANAGER_PORT": "'1'", "ROMP_KERNEL_PORT": "'1'", "ROMP_SERVE_PORT": "'1'",
              "ROMP_MODEL_CATALOG": "'off'", "ROMP_CLI_SCOPE": "'0'", "CLAUDE_CONFIG_DIR": "tempfile.mkdtemp()",
              "ROMP_SERVICE_ENV_FILE": "os.path.join(os.environ['XDG_STATE_HOME'], 'no-such-service.env')",
              "ROMP_SERVICE_ENV": "os.environ['ROMP_SERVICE_ENV_FILE']",
              "ROMP_MODELS_URL": "'http://127.0.0.1:9/v1/models'"}
    assert set(sample) == set(LICENSED_MODULE_LEVEL_WRITES), sorted(set(sample) ^ set(LICENSED_MODULE_LEVEL_WRITES))
    return {name: [_Record("test_licensed.py", 1, "assignment", value, False, value, "")] for name, value in sample.items()}


def _proof_facets():
    """THE FACETS UNDER THE EXECUTION PROOF (the reviewer's ruling of 2026-09-24 21:09Z on round 2 of fork PR #894, (1)
    (b)): two groups of synthetic conftests, each case (label, conftest text, {helper file: text}, probe name, the first
    line of the popper `_f`, whether the proof must license `_f`'s pop), for one proof per group
    (_reassert_proof, the counted site being `_f`'s pop in every case, as if the filter had counted it: the filter
    refuses nearly all of these, and none of that is read here). Every facet the reader was found counting while pytest
    never ran the pop: F2, a later binding of the fixture's name; F2b, another def given its name=; F2c, a name= passed
    through functools.partial; F2e, a decorator imported from another module; N2b, a sibling named like a standard
    module, an imported module that rebinds pytest.fixture, and a value taken through importlib; the pytest hooks (one
    that answers for the fixture, parametrizes its name, or takes it out of each test, by its name, by specname= or as
    a lambda, and a listed pytest_configure that rebinds the name); the in-place operator on a bound mutable object (a
    test's list of fixtures in a listed pytest_collectreport and in a fixture that sorts first, pytest.fixture's keyword
    defaults, a report's __dict__, and config.option's __dict__, which turns on the setup plan for the whole run and so
    runs alone); the module road's residuals (a fixture that registers a plugin, a listed makereport that makes a failed
    setup pass). Each is licensed or refused by the run. THE RE-ASSERT ITSELF, not the value: the value right at each
    read but set by another def registered under the name, by a helper the fixture calls, by another file's def of the
    name at the popper's first line, by a def of another name compiled in the conftest's file at that line, or by a
    later def of the name; the fixture setting the name where the site counts a pop; and the fixture's pop followed by
    another fixture writing the probe's value back. The fixture popping in the first test's setup and after every test,
    never in a later test's setup, is refused, and so is a read not reported, the probe's second tests taken out of the
    run. Licensed: the control, a listed hook that does nothing, the fixture
    under a name another fixture sorting first also takes, the fixture renamed by its own decorator, and the fixture
    aliased under a second name."""
    thing = "import pytest\n\n\n@pytest.fixture(autouse=True, name='_f')\ndef thing():\n    yield\n"
    fx = "import functools, pytest\nfx = functools.partial(pytest.fixture, autouse=True, name='_f')\n"
    rebind = "import functools, pytest\npytest.fixture = functools.partial(pytest.fixture, name='_f')\n"
    drop = ("        if '_f' in {i}.fixturenames and str({i}.path).startswith(os.path.dirname(os.path.realpath(__file__))):\n"
            "            {i}.fixturenames.remove('_f')\n")

    def popper(p, decorator="@pytest.fixture(autouse=True)"):
        return "import os, pytest\n\n\n%s\ndef _f():\n    os.environ.pop(%r, None)\n    yield\n\n\n" % (decorator, p)

    def later(text):
        return lambda p: popper(p) + text.replace("__QUOTED__", '"%s"' % p).replace("__NAME__", repr(p))
    failing = lambda p: (
        "import os, pytest\n\n_ONCE = []\n\n\ndef _boom():\n    if os.environ.get(%r) == '45678' and not _ONCE:\n"
        "        _ONCE.append(1)\n        raise RuntimeError('boom')\n\n\n"
        "@pytest.fixture(autouse=True)\ndef _f():\n    _boom()\n    os.environ.pop(%r, None)\n    yield\n\n\n"
        "@pytest.hookimpl(hookwrapper=True)\ndef pytest_runtest_makereport(item, call):\n    outcome = yield\n"
        "    rep = outcome.get_result()\n    if rep.when == 'setup' and rep.failed:\n        rep.outcome = 'passed'\n" % (p, p))
    in_place_makereport = lambda p: (
        "import os, pytest\n\n\n@pytest.fixture(autouse=True)\ndef _f():\n"
        "    assert (os.environ.get(%r) != '45678' or os.environ.get(%r) is not None\n"
        "            or os.environ.setdefault(%r, '1') is None)\n"
        "    os.environ.pop(%r, None)\n    yield\n\n\n"
        "@pytest.hookimpl(hookwrapper=True)\ndef pytest_runtest_makereport(item, call):\n    outcome = yield\n"
        "    d = outcome._result.__dict__\n"
        "    if call.when == 'setup' and call.excinfo is not None:\n        d |= {'outcome': 'passed'}\n" % (p, p + "_ONCE", p + "_ONCE", p))
    helper_pops = lambda p: ("import os, pytest\n\n\n@pytest.fixture(autouse=True)\ndef _f():\n    _clear()\n    yield\n\n\n"
                             "def _clear():\n    os.environ.pop(%r, None)\n" % p)
    sets_it = lambda p: "import os, pytest\n\n\n@pytest.fixture(autouse=True)\ndef _f():\n    os.environ[%r] = '1'\n    yield\n" % p
    # (label, the conftest as a function of the probe name, helpers (a function of it too, or a dict), licensed)
    cases = (
        ("control", popper, {}, True),
        ("F2: a later binding of the fixture's name", later("_f = None\n"), {}, False),
        ("F2b: another def given the fixture's name=", later("@pytest.fixture(autouse=True, name='_f')\ndef _g():\n    yield\n"),
         {}, False),
        ("F2c: a name= passed through functools.partial", later(
            "import functools\n_fx = functools.partial(pytest.fixture, autouse=True, name='_f')\n\n\n@_fx\ndef _g():\n    yield\n"),
         {}, False),
        ("F2e: a decorator imported from another module", later("from _pf_e import fx\n\n\n@fx\ndef _g():\n    yield\n"),
         {"_pf_e.py": fx}, False),
        ("N2b: a sibling named like a standard-library module", later("from colorsys import thing\n"), {"colorsys.py": thing}, False),
        ("N2b: an imported module that rebinds pytest.fixture", later(
            "import _pf_b\n\n\n@pytest.fixture(autouse=True)\ndef _g():\n    yield\n\n\npytest.fixture = pytest.fixture.func\n"),
         {"_pf_b.py": rebind}, False),
        ("N2b: a value taken through importlib", later("import importlib\nthing = importlib.import_module('_pf_c').thing\n"),
         {"_pf_c.py": thing}, False),
        ("hook: a listed hook that does nothing", later("@pytest.hookimpl(trylast=True)\ndef pytest_configure(config):\n    pass\n"),
         {}, True),
        ("hook: pytest_fixture_setup answers for the fixture", later(
            "def pytest_fixture_setup(fixturedef, request):\n    if fixturedef.argname == '_f':\n"
            "        fixturedef.cached_result = (0, fixturedef.cache_key(request), None)\n        return 0\n"), {}, False),
        ("hook: pytest_generate_tests parametrizes the fixture's name", later(
            "def pytest_generate_tests(metafunc):\n    if '_f' in metafunc.fixturenames:\n        metafunc.parametrize('_f', [0])\n"),
         {}, False),
        ("hook: pytest_collection_modifyitems takes the fixture out of each test", later(
            "def pytest_collection_modifyitems(items):\n    for item in items:\n" + drop.format(i="item")), {}, False),
        ("hook: that hook under another name by specname=", later(
            "@pytest.hookimpl(specname='pytest_collection_modifyitems')\ndef pytest_drop_f(items):\n    for item in items:\n"
            + drop.format(i="item")), {}, False),
        ("hook: that hook bound to a lambda", later(
            "pytest_collection_modifyitems = lambda items: [\n    i.fixturenames.remove('_f') for i in items\n    if '_f' in "
            "i.fixturenames and str(i.path).startswith(os.path.dirname(os.path.realpath(__file__)))]\n"), {}, False),
        ("hook: a listed pytest_configure that rebinds the fixture's name", later(
            "def pytest_configure(config):\n    globals()['_f'] = None\n"), {}, False),
        ("in-place: a test's fixtures emptied in a listed pytest_collectreport", later(
            "def pytest_collectreport(report):\n    for item in report.result:\n        try:\n            names = item.fixturenames\n"
            "        except AttributeError:\n            continue\n        names *= 0\n"), {}, False),
        ("in-place: a test's fixtures emptied in a fixture that sorts before it", later(
            "@pytest.fixture(autouse=True)\ndef _a(request):\n    names = request.node.fixturenames\n    names *= 0\n    yield\n"),
         {}, False),
        ("in-place: pytest.fixture's keyword defaults given the name at import", later(
            "_d = pytest.fixture.__kwdefaults__\n_d |= {'name': '_f'}\n\n\n@pytest.fixture(autouse=True)\ndef _g():\n    yield\n\n\n"
            "_d |= {'name': None}\n"), {}, False),
        ("in-place: a listed makereport makes a failed setup pass through the report's __dict__", in_place_makereport, {}, False),
        ("residual: a fixture that registers a plugin that takes the fixture out", later(
            "class _Drop:\n    def pytest_runtest_setup(self, item):\n" + textwrap.indent(drop.format(i="item"), "    ") + "\n\n"
            "@pytest.fixture(autouse=True, scope='session')\ndef _a(request):\n    request.config.pluginmanager.register(_Drop())\n"
            "    yield\n"), {}, False),
        ("residual: a listed makereport makes a failed setup pass", failing, {}, False),
        ("module-scoped: the fixture's own function rebound to a module-scoped fixture", later(
            "_f = pytest.fixture(autouse=True, scope='module')(_f._get_wrapped_function())\n"), {}, False),
        ("itself: the value right, popped by another def registered under the fixture's name", later(
            "@pytest.fixture(autouse=True, name='_f')\ndef _g():\n    os.environ.pop(__NAME__, None)\n    yield\n"), {}, False),
        ("itself: the value right, popped by a helper the fixture calls", helper_pops, {}, False),
        ("itself: the value right, popped by another file's def of the name at the fixture's first line",
         later("from _pf_v import _f as _z\n"),
         lambda p: {"_pf_v.py": "import os, pytest\n\n\n@pytest.fixture(autouse=True, name='_f')\ndef _f():\n"
                                "    os.environ.pop(%r, None)\n    yield\n" % p}, False),
        ("itself: the value right, popped by a def of another name compiled in the conftest's file at that line", later(
            "_ns = {'os': os}\nexec(compile('\\n\\n\\n' + 'def _h():\\n    os.environ.pop(__QUOTED__, None)\\n    yield\\n', "
            "__file__, 'exec'), _ns)\n_z = pytest.fixture(autouse=True, name='_f')(_ns['_h'])\n"), {}, False),
        ("itself: the value right, popped by a later def of the fixture's name", later(
            "@pytest.fixture(autouse=True)\ndef _f():\n    os.environ.pop(__NAME__, None)\n    yield\n"), {}, False),
        ("itself: the fixture sets the name where the reader counted a pop", sets_it, {}, False),
        ("itself: the fixture's pop, then another fixture writes the probe's value back", later(
            "@pytest.fixture(autouse=True)\ndef _z():\n    os.environ[__NAME__] = '45678'\n    yield\n"), {}, False),
        ("setup: the fixture pops in the first test's setup and after every test, never in a later test's setup",
         lambda p: ("import os, pytest\n\n\n@pytest.fixture(autouse=True)\ndef _f():\n    if not _RUNS:\n"
                    "        os.environ.pop(%r, None)\n    _RUNS.append(1)\n    yield\n    os.environ.pop(%r, None)\n\n\n"
                    "_RUNS = []\n" % (p, p)), {}, False),
        ("report: the probe's second tests taken out of the run", later(
            "def pytest_collection_modifyitems(items):\n    here = os.path.dirname(os.path.realpath(__file__))\n"
            "    items[:] = [i for i in items if not (i.name.startswith('test_2') and str(i.path).startswith(here))]\n"),
         {}, False),
        ("licensed: another fixture that sorts first takes the fixture's name", later(
            "@pytest.fixture(autouse=True, name='_f')\ndef _a():\n    yield\n"), {}, True),
        ("licensed: the fixture renamed by its own decorator",
         lambda p: popper(p, "@pytest.fixture(autouse=True, name='_renamed')"), {}, True),
        ("licensed: the fixture aliased under a second name", later("_z = _f\n"), {}, True))
    alone = (("in-place: pytest's setup plan turned on through config.option's __dict__ in a listed pytest_configure", later(
        "def pytest_configure(config):\n    opts = config.option.__dict__\n    opts |= {'setupplan': True}\n"), {}, False),)
    groups = []
    for g, group in enumerate((cases, alone)):
        out = []
        for i, (label, conftest, helpers, licensed) in enumerate(group):
            probe = "ROMP_PROBE_PROOF_%d%02d" % (g, i)
            text = conftest(probe)
            fn = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "_f")
            out.append((label, text, helpers(probe) if callable(helpers) else helpers, probe,
                        (fn.decorator_list[0] if fn.decorator_list else fn).lineno, licensed))
        groups.append(out)
    return groups


_CONTEXT_ROAD_HOOK = textwrap.dedent('''\


    import unittest

    _MODULES = []


    def pytest_collectreport(report):
        for item in report.result:
            if not hasattr(item, "fixturenames"):
                continue
            if str(item.path) not in _MODULES:
                _MODULES.append(str(item.path))
            if (__CONDITION__) and "_f" in item.fixturenames:
                item.fixturenames.remove("_f")
''')
#   the hook of each road of _proof_context_roads, the verifier's plants' shape: pytest_collectreport, a hook on
#   _LISTED_HOOKS, whose body the module road takes on trust, takes `_f` out of each test the road's condition names;
#   _MODULES lists the modules of the tests reported to it, in the order they were collected


def _proof_context_roads():
    """THE CHILD'S CONTEXT, PLANTED (the reviewer's ruling of 2026-09-24 23:17Z on round 2 of fork PR #894, (4)): each
    road (label, the condition on `item` its hook keys on, the run of _proof_modes that must refuse it, or None) takes
    `_f` out of the tests one fact of the context names. The finite facts the child reproduces, each and its
    complement: V1, the conftest in a directory named tests, and a test in one; V3, a test of the first module
    collected, and one of a module collected after it; V4, a function test, and a unittest TestCase test; V5, a test in
    a run with no xdist worker, and one on an xdist worker, which only the -n 2 run refuses; and one conjunction of V3,
    V4 and V5. The one road of the proof's disclosed limit, V2, a test with a mark, is granted."""
    return (
        ("V1: the conftest in a directory named tests", "os.path.basename(os.path.dirname(os.path.abspath(__file__))) == 'tests'",
         "serial"),
        ("V1: a test in a directory named tests", "os.path.basename(os.path.dirname(str(item.path))) == 'tests'", "serial"),
        ("V3: a test of the first module collected", "len(_MODULES) == 1", "serial"),
        ("V3: a test of a module collected after the first", "len(_MODULES) > 1", "serial"),
        ("V4: a function test", "getattr(item, 'cls', None) is None", "serial"),
        ("V4: a unittest TestCase test", "isinstance(getattr(item, 'cls', None), type) and issubclass(item.cls, unittest.TestCase)",
         "serial"),
        ("V5: a test in a run with no xdist worker", "not hasattr(item.config, 'workerinput')", "serial"),
        ("V5: a test on an xdist worker", "hasattr(item.config, 'workerinput')", "xdist"),
        ("V3, V4 and V5 at once: a TestCase test of a module collected after the first, on an xdist worker",
         "len(_MODULES) > 1 and getattr(item, 'cls', None) is not None and hasattr(item.config, 'workerinput')", "xdist"),
        ("V2: a test with a mark", "item.get_closest_marker('filterwarnings') is not None", None))


if __name__ == "__main__":
    if "--census" in sys.argv:
        print(_census_table())     # `python -m tests.test_hermetic_kernel_postal --census`: the by-product counts, by name and shape
        sys.exit(0)
    if "--deepest-chain" in sys.argv:
        print("the deepest call chain from import: %d calls, from %s (the resolver's cap: %d)" % (_deepest_call_chain() + (_CALL_DEPTH_CAP,)))
        sys.exit(0)
    unittest.main()
