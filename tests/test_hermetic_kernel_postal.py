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
binding form or by reflection named in any reference form, and hold each name those parts are read by to one value,
bound once and read only where they read it (a plant test reds each part), run its fake's own def over the argv
shapes it must tell apart, and run the test in a child pytest with a sitecustomize that records every connect and
every Python process of the run: none dials the fixed port, and no ensure child starts.
The census pin passes one floor write of a leak name, upstream's client-only "1" (FLOOR_LEAK_WRITES), and the tunnels
probe compares client-only with the value the floor modules left. `python -m tests.test_hermetic_kernel_postal
--census` prints the counts by name and shape (fork PR #871's by-product figures, derived by ast). Beside it,
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
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
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
    a string that exec runs (`exec("k = v")`); the comment above _Module names them ([namespace-rebinding],
    [exec-eval]) with the reason and the plants. Built from the code that runs at import (a class body's bindings among
    it, read as the module's: the body runs at import, and a name bound in both scopes is bound twice); a function's own
    bindings are added when the function is walked (`within`), its parameters shadowing every table. `bindings` (since
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
        setattr on the module) or by a string that exec runs (the verifier's finding on round 2's thirteenth commit of
        fork PR #894, where this docstring said a name bound by anything else stays unreadable). The comment above
        _Module names both ([namespace-rebinding], [exec-eval]), with a plant of a loop name for each form."""
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
        (`globals()["D"]`, `sys.modules[__name__].D`), from another module or in a string that exec runs
        (`exec("D[K] = v")`) is not seen, and the comment above _Module names those ([namespace-rebinding],
        [exec-eval]). One BFS walk:
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
    namespace (`globals()["_ROOT"] = v`) or by a string that exec runs (`exec('_ROOT = v')`) is not seen, and still
    resolves to its first assignment: the comment above _Module names both ([namespace-rebinding], [exec-eval])."""

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
    exec runs (`exec('_ROOT = "/srv/real-state"')`) is not seen and still resolves to its first assignment, so a
    licence's value check passes the first value (the verifier's findings on round 2 of fork PR #894, where this
    docstring said a name bound again by anything stays a name, and on its thirteenth commit, where it named the
    namespace alone); the comment above _Module names both ([namespace-rebinding], [exec-eval]), and the licence test
    holds a plant of each clean, so a change that starts reading either reds."""
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
#   [exec-eval] `exec` or `eval` of a string: a write in it, and a binding or a mutation it makes (`exec("k = v")` after
#     a loop binds k, `exec("D[K] = v")` on a tracked dict), which leaves the name read through its first binding, as
#     under [namespace-rebinding]; the value side (`exec('_ROOT = "/srv/real-state"')`) is held clean by the licence test
#     beside that entry's.
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

_MODULE_CACHE = {}     # path -> ((mtime_ns, size), _Module): the helper modules the resolver reads, parsed once per run


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
    """The _Module for the file `path`, parsed once per run and re-read when the file changes."""
    st = os.stat(path)
    key = (st.st_mtime_ns, st.st_size)
    hit = _MODULE_CACHE.get(path)
    if hit is None or hit[0] != key:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read(), filename=path)
        hit = (key, _module_record(tree, os.path.relpath(path, root), root))
        _MODULE_CACHE[path] = hit
    return hit[1]


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
                  _outside_plant("import os\nD = {'ROMP_PLANTED_DECOY': '1'}\nexec(\"D['{key}'] = '1'\")\nos.environ.update(D)\n")],
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


def _tests_tree_paths():
    """Every .py under tests/, recursively (fixtures/ included), sorted; the glob is checked against an independent
    os.walk so no file is silently unscanned (review round 1, 2026-09-18)."""
    paths = sorted(glob.glob(os.path.join(HERE, "**", "*.py"), recursive=True))
    walked = sorted(os.path.join(d, f) for d, _, fs in os.walk(HERE) for f in fs if f.endswith(".py"))
    if paths != walked:
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


def module_level_env_census(paths=None):
    """The census of module-level environment writes under tests/ (fork PR #871's by-product counts, derived by ast
    rather than by grep, 2026-09-22): (module count, {name: {shape: count}}, {name: [_Record, ...]}). Run it as
    `python -m tests.test_hermetic_kernel_postal --census` for a table. A write the scan cannot read raises, as the pin
    does: a census that skipped a write would be a floor with silent slack."""
    paths = _tests_tree_paths() if paths is None else list(paths)
    counts = collections.defaultdict(lambda: collections.defaultdict(int))
    records = collections.defaultdict(list)
    for path in paths:
        rel = os.path.relpath(path, HERE)
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read(), filename=path)
        for name, rec in _module_level_records(tree, rel):
            counts[name][rec.shape] += 1
            records[name].append(rec)
    return len(paths), {k: dict(v) for k, v in counts.items()}, dict(records)


def _census_table(paths=None):
    """The census as text: the module count, then one line per (name, shape) with the write count, the writer-module
    count, how many of the writes are nested in a module-level block or a class body (the ones a column-0 grep misses)
    and how many are reached through a call at import."""
    n, counts, records = module_level_env_census(paths)
    lines = ["modules: %d (.py files under tests/, recursively; fixtures/ and the helpers beside the test modules included)" % n,
             "%-34s %-11s %6s %8s %7s %8s" % ("name", "shape", "writes", "modules", "nested", "by call")]
    for name in sorted(counts):
        for shape in sorted(counts[name]):
            recs = [r for r in records[name] if r.shape == shape]
            lines.append("%-34s %-11s %6d %8d %7d %8d" % (name, shape, len(recs), len({r.module for r in recs}),
                                                           sum(1 for r in recs if r.nested), sum(1 for r in recs if r.via)))
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
# A licence is PER NAME and CHECKABLE: `value` names the one literal the writers may set (the dead port, the off switch);
# `value_ok` is a predicate over the value expression; `reasserted` requires tests/conftest.py to set or pop the name in
# an autouse fixture, so the module-level value cannot outlive collection under pytest (the dead-port fixture's rule);
# `until` DATES a licence that waits on an item, naming it: a licence with no date and no owner is how a temporary
# exemption becomes permanent.

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
    census finds over the tree, every one of them: `tempfile.mkdtemp()` (755 XDG_STATE_HOME writes, 6 CLAUDE_CONFIG_DIR,
    the one ROMP_STATE_DIR join) and `tempfile.mkdtemp(prefix='romp-envnames-')` (one XDG_STATE_HOME write and the
    ROMP_SERVICE_ENV_FILE concatenation of the same module); the floor's are `prefix='romp-tests-state-'` and
    `prefix='romp-tests-claude-'`."""
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
    """A private state directory for ROMP_STATE_DIR: a mkdtemp, a bare TemporaryDirectory's name, a path of literals joined
    onto a mkdtemp (`os.path.join(tempfile.mkdtemp(), 'romp')`), or the shell's own value written back after the load
    (the three converge and update modules); each of the four the exact form the census shows."""
    node = _expr(v)
    return (_is_mkdtemp(node) or _is_temporary_directory_name(node) or _is_join_onto(node, _is_mkdtemp)
            or v == "os.environ.get('ROMP_STATE_DIR')")


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
    return bool(re.fullmatch(r"'http://127\.0\.0\.1:\d+/[^']*'", v))


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
    mkdtemp), `reasserted` (tests/conftest.py sets or pops the name in an autouse fixture) and, for a licence that
    waits on an item, `since` (the ISO date it was granted) with `until` (the item, named with the date it was filed).
    _licence_table_faults holds every licence to that shape: since the fixup of 2026-09-22 (the verifier's finding
    that since and until were stored and read by nothing) a licence must carry a per-write condition, an `until` must
    come with a `since`, and the dates must be dates."""

    def __init__(self, reason, value=None, value_ok=None, reasserted=False, since=None, until=None):
        self.reason, self.value, self.value_ok, self.reasserted, self.since, self.until = reason, value, value_ok, reasserted, since, until

    def fault(self, rec, reasserted_names):
        """Why the write `rec` (a _Record) falls outside this licence, or None when it is covered."""
        if self.reasserted and self._name not in reasserted_names:
            return "licensed only while tests/conftest.py re-asserts %s in an autouse fixture, and it no longer does" % self._name
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
        "Licensed 2026-09-22 until the class item is taken, which may retire the mandate, and this licence with it",
        value_ok=_a_mkdtemp, since="2026-09-22", until=CLASS_ITEM_871),
    "ROMP_STATE_DIR": _Licence(
        "the other half of the same preamble (a live kernel exports it and it outranks the XDG floor): a private root "
        "(a mkdtemp, a TemporaryDirectory's name, a path joined onto one), or the shell's own value written back after "
        "the load, in the four modules that do not pop it. Licensed 2026-09-22 until the class item is taken",
        value_ok=_a_state_dir, since="2026-09-22", until=CLASS_ITEM_871),
    "ROMP_SERVE_TOKEN": _Licence(
        "a synthetic serve token so a kernel or bus loaded in-process mints none under the module's root: a string "
        "literal, by setdefault in most modules and by assignment in the rest (test_postal_token.py puts the shell's "
        "value back after its load, the one non-literal). Licensed 2026-09-22 until the class item is taken, by the "
        "reviewer's ruling: a dated licence, not current practice", value_ok=_a_serve_token, since="2026-09-22", until=CLASS_ITEM_871),
    "ROMP_KERNEL_NO_OPEN": _Licence(
        "the kernel's one reader opens a browser when the name is unset (kernel/kernel.py, the serve path), and \"1\" "
        "is the value every test wants for itself and for any kernel it starts (kernel_env sets it too): a child that "
        "inherits it opens no browser. Licensed for that one value; 530 writers on 2026-09-22",
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
        "URL, so a kernel that inherits it fetches its catalog from nothing rather than from the network",
        value_ok=_a_loopback_url),
}
for _name, _lic in LICENSED_MODULE_LEVEL_WRITES.items():
    _lic._name = _name


def _is_autouse_fixture(fn):
    for d in fn.decorator_list:
        if not (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "fixture"):
            continue
        for kw in d.keywords:
            if kw.arg == "autouse" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
    return False


def _conftest_reasserted_names(src=None):
    """The environment names tests/conftest.py sets or pops inside an autouse fixture: re-asserted before every test, so a
    module-level write of one cannot outlive collection under pytest (the dead-port fixture's rule, 2026-08-27)."""
    tree = ast.parse(open(os.path.join(HERE, "conftest.py"), encoding="utf-8", errors="replace").read() if src is None else src)
    names = _EnvNames(tree)
    out = set()
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and _is_autouse_fixture(fn):
            out |= _env_writes(fn, names, "conftest.py") | _env_removals(fn, names)
    return out


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
    attribute named for one: the functions' own names, a name an import binds to one (`from pytest import fixture as
    fx`), and every name target of a plain assignment of one of these (`fx = pytest.fixture`, `fx2 = fx`, and both
    names of the chain `fx = fx2 = pytest.fixture`), followed to a fixed point: ast.walk is breadth-first, so a
    module-level `fx2 = fx` is reached before an `fx = pytest.fixture` nested in a try and is read on the next pass,
    and the loop ends on the first pass that adds no name. `passes`, when a list, receives each pass's outcome (True
    when the pass added a name), for the pin that holds the loop to that end."""
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
    one, the function's own name, an import alias, a name target of a plain assignment, each name of a chain `fx = fx2 =
    ...` included, followed to a fixed point). And it reads every call to an attribute named parametrize
    (`@pytest.mark.parametrize(...)`, `metafunc.parametrize(...)`) that passes a scope, by keyword or as its fifth
    argument, other than None (the default, the scope of the fixtures it names): a parametrization's scope overrides the
    scope of a fixture it parametrizes indirectly, so a function-scoped fixture given scope="session" there is torn down
    at the end of the session; it is listed whether or not the parametrization is indirect, the safe side. Each file
    under the root whose text has parametrize, or both fixture and scope=, is read. The function name is the decorated
    def's, or the one a fixture call is applied to or passed, else "?". What it does not read, each passing here unread
    (none is in the tree): a scope passed through *args or **kwargs; a fixture function or a parametrize reached by any
    other route (functools.partial(pytest.fixture, scope=...), whose scope sits on the partial's call; getattr(pytest,
    "fixture"); a name bound by any statement other than a from-import alias or a plain assignment with the name as a
    target: a tuple, list or starred target (`fx, _ = pytest.fixture, None`), an annotated or augmented assignment, a
    walrus, and a for, with or match-case target (the other binding statements, an import of a module, a def, a class, a
    type alias and an except name, bind something other than the function); a plain assignment whose value is neither
    the function nor one of these names (`fx = pytest.fixture if X else None`); an attribute of another name, such as a
    class attribute holding the function; a name bound to parametrize; one returned by a call, held in a container, or
    passed as an argument or a parameter's default); a fixture registered through pytest's private fixture manager
    (FixtureManager._register_fixture, which a plugin can call with a scope); and a fixture a plugin outside the root
    defines. A wrapper def that calls the fixture function with scope= is read at that call, the safe side: a parameter
    it passes as the function is shown as the function name, and one it passes as the scope as the scope."""
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


def _licence_faults(records, reasserted_names=None):
    """Every way the module-level writes in `records` ({name: [_Record]}) fall outside the licensed set; empty when the set
    of names the TEST MODULES write equals the licensed names and every write meets its licence's condition. A list
    rather than assertions so the check runs over synthetic records and is known to be able to fail. The floor modules'
    writes are licensed wholesale and never faulted; a licensed name with no writer left is a fault too (a dead licence
    is removed, not kept)."""
    reasserted_names = _conftest_reasserted_names() if reasserted_names is None else reasserted_names
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
            why = lic.fault(rec, reasserted_names)
            if why:
                faults.append("%s at %s: %s" % (name, at, why))
    for name in sorted(set(LICENSED_MODULE_LEVEL_WRITES) - written):
        faults.append("%s is licensed but no test module writes it at module level any more: remove the licence" % name)
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
    an attribute environ, environb, putenv or unsetenv on any object (os under any name, or reached any way), and a bare
    name so spelled (after `from os import environ`), whatever its context. A write through a name bound to the mapping
    (`env = os.environ`) is read at the binding, which names it."""
    return [n for n in ast.walk(node)
            if (isinstance(n, ast.Attribute) and n.attr in _ENV_NAMES) or (isinstance(n, ast.Name) and n.id in _ENV_NAMES)]


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
    context (called, aliased, passed as an argument) that is one of _REFLECTIVE_NAMES (setattr, delattr, getattr, vars,
    globals, locals, exec, eval, compile, __import__, mock's patch, the builtins module and __builtins__, importlib's
    import_module, operator's attrgetter and methodcaller, sys._getframe, inspect.currentframe, gc's get_referrers,
    get_referents and get_objects); an attribute so named (builtins.setattr, operator.methodcaller, mock.patch and
    patch.object and patch.dict, pytest's monkeypatch.setattr) or one of _REFLECTIVE_ATTRS (__setattr__, __delattr__,
    __getattribute__, __dict__, a function's __globals__, __closure__, __code__, __defaults__ and __kwdefaults__, a
    cell's cell_contents, a frame's f_locals, f_globals and f_builtins, sys.modules); and an import that binds any of
    those (`from builtins import setattr as _s`). NOT READ: a namespace or a callable reached through a module neither
    list names (a pickle or marshal payload, ctypes): _guard_shape names what sees what that could put back."""
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
        convention, checked above for the tunnels module alone; tests/README.md says so."""
        paths = _tests_tree_paths()
        self.assertGreater(len(paths), 900, "the scan walks the whole tree, recursively: %d files (952 on 2026-09-22)" % len(paths))
        n, counts, records = module_level_env_census(paths)
        self.assertEqual(n, len(paths))
        self.assertEqual(_licence_table_faults(LICENSED_MODULE_LEVEL_WRITES), [], "every licence is checkable and a temporary one is dated")
        self.assertEqual(_licence_faults(records), [])
        written = sorted(name for name, recs in records.items() if any(r.module not in FLOOR_MODULES for r in recs))
        self.assertEqual(written, sorted(LICENSED_MODULE_LEVEL_WRITES),
                         "the names the test modules write at module level are exactly the licensed ones (equality, not a floor)")
        for name in LEAK_NAMES:
            self.assertNotIn(name, LICENSED_MODULE_LEVEL_WRITES, "%s is a leak this rule exists to catch, never a licence" % name)
            writers = _leak_writers(records, name)
            self.assertEqual(writers, [], "%s is written at module level by %r (a test module's write, or a floor module's "
                                          "other than the floor value FLOOR_LEAK_WRITES names)" % (name, writers))

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
        dir written with a value outside their licence; the temp-root licences (the state preamble, the claude config
        dir, the service-env path) written with a mkdtemp or a TemporaryDirectory under a real directory (`dir=`, or the
        positional dir), which the regex before the third commit of 2026-09-22 accepted; a name bound once to a mkdtemp
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
        holds for a name rebound by a string that exec runs ([exec-eval]; the verifier's finding on round 2's thirteenth
        commit, where the texts named the namespace alone), held here beside it."""
        def records_of(src, rel):
            out = collections.defaultdict(list)
            for name, rec in _module_level_records(ast.parse(src), rel):
                out[name].append(rec)
            return dict(out)
        reasserted = _conftest_reasserted_names()
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
        # exec runs is not seen, the value resolves to the first assignment, and the licence passes a value the module
        # never writes
        for tag, rebinding in (("namespace-rebinding", 'globals()["_ROOT"] = "/srv/real-state"'),
                               ("exec-eval", "exec('_ROOT = \"/srv/real-state\"')")):
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
                                  "re-asserts ROMP_MANAGER_PORT in an autouse fixture, and it no longer does"])
        # a dead licence is a fault
        without = {k: v for k, v in _all_licensed_once().items() if k != "ROMP_MODELS_URL"}
        self.assertEqual(_licence_faults(without, reasserted),
                         ["ROMP_MODELS_URL is licensed but no test module writes it at module level any more: remove the licence"])

    def test_conftest_re_asserts_the_names_the_re_asserted_licences_rest_on(self):
        """The licences marked `reasserted` are conditions on tests/conftest.py, read from its autouse fixtures by the same
        scan: the dead ports (both spellings of the kernel's), the catalog and scope switches, the claude config dir, the
        service-env pair, and since 2026-09-22 the postal port, popped per test (a pop is how an unset floor is
        re-asserted; the finding's module-level port survived collection because the pop was at import alone)."""
        names = _conftest_reasserted_names()
        for name, lic in LICENSED_MODULE_LEVEL_WRITES.items():
            if lic.reasserted:
                self.assertIn(name, names, "tests/conftest.py no longer re-asserts %s in an autouse fixture" % name)
        self.assertIn("ROMP_POSTAL_PORT", names, "the dead-port fixture pops ROMP_POSTAL_PORT before every test (2026-09-22)")
        # the scan reads a fixture's pop and its assignment, and nothing outside an autouse fixture
        planted = ("import os, pytest\n"
                   "os.environ['ROMP_AT_IMPORT'] = '1'\n"
                   "@pytest.fixture(autouse=True)\ndef _f():\n    os.environ['ROMP_SET'] = '1'\n    os.environ.pop('ROMP_POPPED', None)\n    yield\n"
                   "@pytest.fixture\ndef _g():\n    os.environ['ROMP_NOT_AUTOUSE'] = '1'\n    yield\n")
        self.assertEqual(_conftest_reasserted_names(planted), {"ROMP_SET", "ROMP_POPPED"})

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

    def test_the_census_counts_by_name_and_shape_and_the_table_reads_back(self):
        """module_level_env_census over a synthetic tree: one module, eight shapes (the dunder spelling among them since the
        third commit of 2026-09-22, the augmented write and the target since round 2 of fork PR #894), three names; the nested write is counted as such; the table names the module count. The counts over the real tree are the by-product fork PR #871's
        docstring recorded from a grep, re-derived by ast here and pasted at the head in the PR; they are NOT pinned by
        equality, since they move with every new module (the enforced property is the licensed set's equality)."""
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
        self.assertIn("modules: 1", table)
        self.assertIn("%-34s %-11s %6d %8d %7d %8d" % ("A", "assignment", 3, 1, 2, 0), table)
        self.assertIn("%-34s %-11s %6d %8d %7d %8d" % ("D", "assignment", 1, 1, 0, 1), table)
        self.assertIn("%-34s %-11s %6d %8d %7d %8d" % ("A", "augmented", 1, 1, 0, 0), table)
        self.assertIn("%-34s %-11s %6d %8d %7d %8d" % ("B", "target", 1, 1, 0, 0), table)

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
        module's namespace or by a string exec runs is not seen: [namespace-rebinding] and [exec-eval] above _Module, each
        with a plant of a loop name), and a write through it is loud, naming the module
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
        that exec runs, as through globals() (plants added under namespace-rebinding and exec-eval)."""
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
            return _licence_faults({**_all_licensed_once(), **out}, _conftest_reasserted_names())
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
            faults = _licence_faults({**_all_licensed_once(), **out}, _conftest_reasserted_names())
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
        Every name the parts are read by holds one value (the verifier's five one-line plants on the fourth commit rebound
        real_run or real_revive, cleared the saved mapping, set the Event before the call or rebound it, and every pin
        passed): the kept real run and real revive, the Event, the wait's result, the fake, the wrapper and each road def,
        the saved mapping, the road's list, the threading module and the test case (self) are each bound ONCE in the whole
        test, parameters of nested defs and lambdas included, by the statement the parts are read from (_name_binds), and
        each but self is read only where the parts read it (_name_loads: the real run in the unfake and in a road's call,
        the real revive in the unwrap and the wrapper's call, the Event in the wrapper's set and the wait, and so on); the
        road's list is made by an empty list literal. NOT READ by the name rule: the fake's own list (the plants read it;
        nothing the pin guarantees rests on it, and fork PR #875's assertion reads it); the names local to a nested def (the
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
        self.assertTrue(any(any(isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) and isinstance(s.value.func, ast.Name)
                                and s.value.func.id == kept_revive[0][1] for s in _executed(t.body))
                            and any(_call_stmt(s, [event, "set"]) for s in _executed(t.finalbody))
                            for t in _executed(before[defs[wrapper.id]].body) if isinstance(t, ast.Try) and not t.handlers),
                        "the wrapper runs the real revive in a try whose finally sets the Event (%s), whatever the revive does" % event)
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
        return {"fn": fn, "fake": fake.id, "real_run": kept_run[0][1], "reached": reached[0], "event": event, "ended": ended,
                "real_revive": kept_revive[0][1], "try": top[tries[0]], "install": before[install[0]], "wait": final[wait],
                "after": after, "wrapper": wrapper_def, "fake_def": fake_def, "saved_env": env_saved, "restore": loop,
                "saved_made": before[made[0]], "list_made": list_made[0][0], "trio_stmt": before[trio_at[0]],
                "roads": [r for r in roads if r is not fake_def], "rebind": before[rebind[0]]}

    def test_the_peer_notify_guard_test_runs_the_trio_the_wrap_the_wait_and_the_scoped_fake_as_statements_that_run(self):
        """Read by ast from tests/test_kernel.py's PostalPeerTunnels.test_notify_bus_peer_is_guarded, each part required as
        a statement that runs on a run of the test that passes, so none after a return, a raise, a skip or an exit and none
        in the body of a try with an except clause (_guard_shape; the reviewer's re-ruling of round 2 on fork PR #894): the
        trio, os.environ.update(ROMP_POSTAL_CLIENT_ONLY="1", ROMP_POSTAL_PEERS="0", ROMP_POSTAL_PORT="1"), set before the
        one km._notify_bus_peer call (the refusal that kicks the bus revive on a thread); km._revive_postal_bus rebound
        before the call to a wrapper of the test's own that runs the real revive in a try whose finally sets an Event;
        km.subprocess.run replaced before the call by a fake of the test's own taking (*a, **kw); the call in a try whose
        finally waits on that Event, keeping the result, BEFORE it puts the fake and the environment back, and puts the
        real revive back; and, after the try, the wait's result asserted and one list asserted empty that the road from the
        fake to the real run appends to, the postal-service calls that reached the real run (another list asserted empty
        beside it, as fork PR #875's assertion will be once the two texts meet, is not what this reads). The environment
        goes back in one for statement over the mapping saved before the trio from os.environ.get of the trio's three
        names. No other statement of the test, run or not, binds or deletes an attribute on any object in any binding form
        (km.BUS_PORT aside), binds km or os, names reflection in any reference form, or names the environment outside
        os.environ.get reads, the trio and the restore; and every name the parts are read by (the kept real run and real
        revive, the Event, the wait's result, the fake, the wrapper, the road, the saved mapping, the road's list,
        threading and self) is bound once, by the statement the parts are read from, and read only where they read it
        (self excepted, read anywhere). What that leaves unread (a put-back made by code the test calls, among others) is
        named in _guard_shape with what sees it, and the plant test below reds each part.
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
        closure cell rewritten, a function's globals and a frame's locals."""
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
                   "before the install": (shape["install"], "before"), "before the rebind": (shape["rebind"], "before")}
        after_try, finally_run, one_try, wait_msg = ("after the try the wait's result", "the finally puts the real run back",
                                                    "the notify call runs in one try", "the finally waits on the Event")
        reflect, binds, rebinds, env = ("names reflection, in any reference form", "binds or deletes an attribute",
                                        "binds the names km or os", "names the environment only in")
        held = "holds one value"
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
            ("a frame's locals", "after the install", 'sys._getframe().f_locals["%(real_run)s"] = %(fake)s', reflect))
        lines = cls_src.splitlines(keepends=True)

        def with_parameter(fn, extra):     # the one-line header of a def of the test, a parameter added at its end
            self.assertEqual(fn.body[0].lineno, fn.lineno + 1, "%s's header is one line" % fn.name)
            header = "%sdef %s(%s):\n" % (" " * fn.col_offset, fn.name, ", ".join(p for p in (ast.unparse(fn.args), extra) if p))
            return "".join(lines[:fn.lineno - 1] + [header] + lines[fn.lineno:])
        saved_made, trio_stmt = shape["saved_made"], shape["trio_stmt"]
        self.assertEqual(trio_stmt.lineno, saved_made.end_lineno + 1, "the saved mapping is made on the line before the trio")
        whole = [("the road's own parameter hiding the kept real run", with_parameter(shape["roads"][0], "%(real_run)s=None" % names), held),
                 ("the wrapper's own parameter hiding the Event", with_parameter(shape["wrapper"], "%(event)s=None" % names), held),
                 ("the saved mapping made after the trio is set",
                  "".join(lines[:saved_made.lineno - 1] + lines[trio_stmt.lineno - 1:trio_stmt.end_lineno]
                          + lines[saved_made.lineno - 1:saved_made.end_lineno] + lines[trio_stmt.end_lineno:]), "before the trio is set")]
        for label, planted, fragment in [(label, _plant_at(cls_src, anchors[anchor][0], text % names, anchors[anchor][1], *anchors[anchor][2:]), fragment)
                                         for label, anchor, text, fragment in plants] + whole:
            with self.assertRaises(AssertionError, msg="%s: the pin passed it" % label) as caught:
                self._guard_shape(planted)
            self.assertIn(fragment, str(caught.exception), "%s: the pin reds for the part it breaks" % label)
        for label, anchor in (("after the try, as the guard test's comment anticipates", "after the try"),
                              ("inside the try, where upstream's text has it", "in the try")):
            node, where = anchors[anchor]
            both = _plant_at(cls_src, node, 'self.assertEqual(%(stubbed)s, [], "a client-only kernel never runs the bus ensure")' % names, where)
            self.assertEqual(self._guard_shape(both)["reached"], shape["reached"],
                             "fork PR #875's assertion kept %s: the pin passes and reads the road's list" % label)

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
        port and its argv at exit, and refuses a connect to the machine's fixed bus port (the postal service's default
        port, read from bin/romp-postal-service) before it reaches the network. No process of the run dials the fixed
        port, and no romp-postal-service process starts: the test's fake answers the revive's ensure. The spy is shown
        live where it must be: in the test process it records the notify's refused dial to BUS_PORT 1, and at that dial
        the test process's PYTHONPATH still names the spy, so an ensure child forked in the window (it inherits that
        environment) would load it and be recorded. What it does not read, and why that leaves the revive's ensure read:
        a process that is not Python, one started with -S or -I, or one handed an environment without the PYTHONPATH
        (none of them loads the sitecustomize; the ensure is Python, started with neither flag, and inherits the test
        process's environment), and a connect made below socket.socket (a C extension's own socket; the postal service's
        ping goes through urllib.request, which connects through socket.socket). With the test at its base text (round
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
        self.assertEqual([r for r in recs if r["kind"] == "exit" and any(a.endswith("romp-postal-service") for a in r["argv"])], [],
                         "no romp-postal-service process starts: the test's fake answers the revive's ensure")

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

    def test_the_module_env_fixture_watches_the_seams_and_the_trio_and_no_name_conftest_re_asserts_but_the_port(self):
        """The list conftest's _module_env_restored watches (the reviewer's ruling of round 1 on fork PR #894): at least the
        seams _shared_state_restored watches per test and the postal trio; not PYTEST_CURRENT_TEST, which pytest writes
        for every phase; and no name conftest re-asserts before every test (read from its autouse fixtures by
        _conftest_reasserted_names, which reads a name written or popped in the fixture's own body and not one reached
        through a call or a loop, the credential names and the scope limits among them, none of which is watched), since
        conftest's own write would read as the module's, except ROMP_POSTAL_PORT, which the fixture compares with the
        value conftest's pop gives it (unset) instead of with its snapshot."""
        from tests import conftest
        watched = set(conftest.MODULE_WATCHED_ENV_NAMES)
        self.assertLessEqual(set(conftest._SEAM_ENV_NAMES) | set(TRIO), watched)
        self.assertIn("ROMP_POSTAL_HOST", conftest._SEAM_ENV_NAMES, "the bus-name seam is watched per test beside the sessions file")
        self.assertNotIn("PYTEST_CURRENT_TEST", watched)
        self.assertEqual(watched & _conftest_reasserted_names(), {"ROMP_POSTAL_PORT"})
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
        first test to be set up is what counts, not the module's first (the verifier's finding on round 2 of fork PR
        #894, where the texts had keyed on the module's first test): when the module's first test is skipped by a
        skipif or skip mark, or ended by an xfail mark with run=False, it sets up no fixture, and a session fixture the
        second test requests by name is named by neither check; when it is skipped in its body, or by a unittest skip
        decorator on its method or its class, it was set up, and the module check names the module."""
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
                         "        pass"), [], ["test_p1.py"], "2 passed, 1 skipped")]
        for case in cases:
            label, where, text, per_test_expected, module_expected = case[:5]
            tally = case[5] if len(case) > 5 else "3 passed"
            plant_dir = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, plant_dir, True)
            marker = os.path.join(plant_dir, "inherited.txt")
            modules = {where + "test_p1.py": text, where + "test_p2_later.py": later}
            if where:
                modules[where + "__init__.py"] = ""
            rc, out, _d = self._scratch_conftest_run(modules, env={"ROMP_TEST_MODULE_ENV_MARKER": marker, "ROMP_TEST_PLANT_DIR": plant_dir,
                                                                   "ROMP_SESSIONS_FILE": None})
            with open(marker, encoding="utf-8") as f:
                self.assertEqual(f.read(), os.path.join(plant_dir, "planted.json"),
                                 "%s: the later module's child inherits the planted value: %s" % (label, out[-3000:]))
            # a check's message can appear more than once (the error, an exception group's copy of it, the summary line),
            # and the fail call's source line can be quoted with its %s, so the names are compared as sets, %s excluded
            per_test = sorted(set(re.findall(r"([^\s%]\S*\.py::\S+) left shared state changed after its teardown", out)))
            self.assertEqual(per_test, per_test_expected, "%s: the per-test check names %s: %s"
                             % (label, per_test_expected or "nothing", out[-3000:]))
            named = sorted(set(re.findall(r"module ([^\s%]\S*) left the environment changed after its teardown", out)))
            self.assertEqual(named, module_expected, "%s: the module check names %s: %s"
                             % (label, module_expected or "nothing", out[-3000:]))
            self.assertEqual(rc, 1 if per_test_expected or module_expected else 0, "%s: %s" % (label, out[-3000:]))
            self.assertIn(tally, out, label)

    def test_no_fixture_in_the_tree_is_scoped_above_module(self):
        """The class conftest's environment checks read only in part (the verifier's findings on round 2 of fork PR #894):
        a watched name a session- or package-scoped fixture writes is read by a check only when the fixture's setup
        follows that check's snapshot, and one set up before both, as one requested by name by the first of the module's
        tests to be set up is, reaches every later module unread (the executed plants in
        test_a_write_by_a_fixture_scoped_above_module_is_named_by_each_check_whose_snapshot_its_setup_follows). conftest's
        comment above _module_env_restored and tests/README.md name the class; the tree has no such fixture, and the list
        _fixtures_scoped_above_module derives is held EQUAL to empty. Over a planted tree it lists a session fixture, a
        package fixture, a fixture imported by its bare name and one whose scope is a name; a fixture registered by a
        call applied to its function, or passed it, a decorator imported under another name or bound to one by an
        assignment, both names of a chained assignment (`ch1 = ch2 = pytest.fixture`, the verifier's finding on round 2
        of fork PR #894), an alias bound before the binding it copies in the walk's order (read on the fixed
        point's second pass; the fixed point itself is held by
        test_the_fixture_spelling_scan_follows_an_alias_chain_to_the_pass_that_adds_nothing), a factory held in a name,
        and wrapper defs; yield_fixture as an attribute, by its bare name and under an import alias; and a
        parametrization's scope above module, by keyword, as the fifth argument (also in a file whose text has neither
        fixture nor scope=) and on metafunc.parametrize. It does not list a module or a class fixture, a parametrization
        scoped to module or None, nor the routes its docstring names as unread (a scope through **kwargs or *args,
        functools.partial, getattr, an annotated assignment, a tuple target, a walrus, a for target, a conditional
        expression's value, a class attribute, a name bound to parametrize, pytest's private _register_fixture), so the
        list is known to fill when a read one appears and the unread list is known to be true."""
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
            """))
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

    def test_the_full_walk_writes_nothing_on_the_parsers_shared_singletons(self):
        """The contract's read-only clause, for this walker: the parser's Load, Store and Del nodes (one object each for
        the process; a write on one is on every tree parsed after it) carry the same attributes after the census over
        every module under tests/, the walk the equality pin runs, as before it. A walker that kept per-node data as an
        attribute (`child._parent = node`, fork PR #891's census before the ruling) fails here; a side table keyed by
        id(node) is where such data belongs."""
        singletons = _parser_singletons()
        before = {kind: dict(vars(node)) for kind, node in singletons.items()}
        paths = _tests_tree_paths()
        n, _counts, _records = module_level_env_census(paths)
        self.assertEqual(n, len(paths), "the walk ran over the whole tree")
        self.assertGreater(n, 900)
        after = {kind: dict(vars(node)) for kind, node in singletons.items()}
        self.assertEqual(after, before, "the walk writes no attribute on a node: per-node data belongs in a side table keyed by id(node)")

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


if __name__ == "__main__":
    if "--census" in sys.argv:
        print(_census_table())     # `python -m tests.test_hermetic_kernel_postal --census`: the by-product counts, by name and shape
        sys.exit(0)
    if "--deepest-chain" in sys.argv:
        print("the deepest call chain from import: %d calls, from %s (the resolver's cap: %d)" % (_deepest_call_chain() + (_CALL_DEPTH_CAP,)))
        sys.exit(0)
    unittest.main()
