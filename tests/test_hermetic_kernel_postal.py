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
of the variable, module-level if/try/for/with bodies included, in every shape a write takes (a subscript assignment,
setdefault, update of a literal or of a module-level name bound to one, |=, os.putenv, through os.environ or any name
bound to it; review round 2, 2026-09-18, after the subscript and setdefault alone left a module-level update
invisible; the dunder spellings __setitem__ and __ior__, called on the mapping or unbound with the mapping as the first
argument, and os.environb with a bytes key, since the third commit of 2026-09-22, when the verifier found those three
passing silently), and a write whose keys the scan cannot read fails the test rather than passing unread. The probe beside
them imports the module in a fresh interpreter and runs one setUp, and one that fails, to see the value. The restore is
a cleanup rather than a tearDown since review round 1 (2026-09-18): unittest skips tearDown when a subclass's setUp
raises after the base's returned, and a tearDown restore left the 0 in the worker on that path.

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
try with an except clause) and hold every other statement of the test to putting back none of what those set, in any
binding form or by reflection (a plant test reds each part), run its fake's own def over the argv shapes it must
tell apart, and run the test in a child pytest with a sitecustomize that records every connect and every Python
process of the run: none dials the fixed port, and no ensure child starts.
The census pin passes one floor write of a leak name, upstream's client-only "1" (FLOOR_LEAK_WRITES), and the tunnels
probe compares client-only with the value the floor modules left. `python -m tests.test_hermetic_kernel_postal
--census` prints the counts by name and shape (fork PR #871's by-product figures, derived by ast). Beside it,
tests/conftest.py's run-end process check makes a run red that leaves any process holding its temp root
(tests/test_run_end_leaked_processes.py).
The fixup of the same day (the verifier's findings on this PR) made "module level" mean everything that EXECUTES AT
IMPORT: the class bodies (a write planted in one had left the pin green), the header parts of a def, class or block
statement (decorators, default argument values, bases, an if test, the with items) and the writes reached through a
call at import the scan can resolve to a def or class under tests/ (a module-local helper, a name imported from a
tests-local module, a bare decorator, an instantiation; two such calls exist today, both to
test_asm_checkpoint.kernel_module(), whose setdefault of the browser switch is licensed), with what stays outside the
scan named above _Module; and every licence carries a checkable value condition (a value written through a name is read
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


class _EnvNames:
    """What spells the process environment in a module, so a write is read whatever name it goes through (review round 2,
    2026-09-18; before it the scan read `os.environ[...]` and `os.environ.setdefault` alone, and a module-level
    `os.environ.update(...)` was invisible to it): `os.environ` under any name os is imported as, `environ` after
    `from os import environ` (or its `as` name), and every name bound to it (`env = os.environ`); `os.environb`, the same
    environment keyed by bytes, the same way (the third commit of 2026-09-22). Beside those, the names
    bound to a dict literal or to `dict(...)` of keywords, which an `update(NAME)` reads through the name
    (tests/test_update_banner_confirm_served.py updates its DEAD_PORTS that way at import); a name bound any other way,
    or more than once, is unreadable, and an update of it is loud. Built from the code that runs at import (a class
    body's bindings among it, read as the module's: the body runs at import, and a name bound in both scopes is bound
    twice); a function's own bindings are added when the function is walked (`within`), its parameters shadowing.
    Since the fixup of 2026-09-22 (the verifier's finding that five licences had no value condition) it also keeps
    `bindings`: every name bound at import by an assignment, to its value expression when bound exactly once (None when
    bound again by anything that binds: another assignment, a for or with target, an import, a def, a class, a walrus),
    so a licence's value check reads a value written through a name (`_ROOT = tempfile.mkdtemp();
    os.environ["XDG_STATE_HOME"] = _ROOT`, `_STATE_TD.name`); _resolved does the substitution."""

    def __init__(self, tree=None):
        self.os_names = {"os"}
        self.environ_names = set()
        self.dicts = {}
        self.loop_literals = {}      # a name a `for` binds to each of a tuple or list of string literals, in turn
        self.bindings = {}           # a name bound at import by one assignment -> its value node; None when unreadable
        if tree is not None:
            self.absorb([node for node, _nested in _import_time_nodes(tree.body)])
            for loop in _module_level_compounds(tree.body, ast.For):
                self._absorb_loop(loop)      # the loop header itself: the import-time walk yields only its body

    def _absorb_loop(self, n):
        """`for var in ("A", "B"): environ[var] = v` writes exactly A and B (conftest's service-env fixture, the guard
        test's restore): the literals are read; a loop over anything computed, or a name bound by two loops, stays
        unreadable."""
        if isinstance(n.target, ast.Name):
            literal = (isinstance(n.iter, (ast.Tuple, ast.List)) and n.iter.elts
                       and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in n.iter.elts))
            self.loop_literals[n.target.id] = {e.value for e in n.iter.elts} if literal and n.target.id not in self.loop_literals else None

    def _bind(self, name, value):
        """`name` bound at import to the expression `value`, or to None (bound by something that is not an assignment); a
        second binding of any kind makes the name unreadable (None)."""
        self.bindings[name] = None if name in self.bindings else value

    def _bind_targets(self, targets):
        for t in _flat_targets(targets):
            if isinstance(t, ast.Name):
                self._bind(t.id, None)

    def absorb(self, nodes):
        for node in nodes:
            for n in ast.walk(node):
                if isinstance(n, ast.For):
                    self._absorb_loop(n)
                    self._bind_targets([n.target])
                elif isinstance(n, ast.Import):
                    self.os_names.update(a.asname for a in n.names if a.name == "os" and a.asname)
                    for a in n.names:
                        self._bind((a.asname or a.name).split(".")[0], None)
                elif isinstance(n, ast.ImportFrom):
                    if n.module == "os":
                        self.environ_names.update(a.asname or a.name for a in n.names if a.name in ("environ", "environb"))
                    for a in n.names:
                        self._bind(a.asname or a.name, None)
                elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    self._bind(n.name, None)
                elif isinstance(n, (ast.With, ast.AsyncWith)):
                    self._bind_targets([i.optional_vars for i in n.items if i.optional_vars is not None])
                elif isinstance(n, ast.NamedExpr):
                    self._bind(n.target.id, None)
                elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                    self._bind(n.target.id, None)
                elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                    self._bind(n.target.id, n.value)
                elif isinstance(n, ast.Assign):
                    whole = {id(t) for t in n.targets if isinstance(t, ast.Name)}     # `A = v`, `A = environ[K] = v`
                    for t in _flat_targets(n.targets):
                        if isinstance(t, ast.Name):
                            self._bind(t.id, n.value if id(t) in whole else None)      # an unpacked name is not the value
                    if len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                        name = n.targets[0].id
                        if self.is_environ(n.value):
                            self.environ_names.add(name)
                        else:
                            self.dicts[name] = None if name in self.dicts else _literal_mapping(n.value)
        return self

    def within(self, node):
        """These names plus whatever `node` (a function) binds itself; its parameters shadow the module's names."""
        inner = _EnvNames()
        inner.os_names, inner.environ_names, inner.dicts = set(self.os_names), set(self.environ_names), dict(self.dicts)
        inner.loop_literals, inner.bindings = dict(self.loop_literals), dict(self.bindings)
        for a in ast.walk(node):
            if isinstance(a, ast.arg):
                inner.bindings[a.arg] = None
        return inner.absorb([node])

    def is_environ(self, node):
        if isinstance(node, ast.Attribute) and node.attr in ("environ", "environb") and isinstance(node.value, ast.Name):
            return node.value.id in self.os_names
        return isinstance(node, ast.Name) and node.id in self.environ_names


def _fresh(node):
    """A tree of the expression `node` parsed anew from its own text: the one tree the substitution below may rewrite.
    THE CONTRACT (the reviewer's ruling of 2026-09-22, from a CI red on fork PR #891): a parsed tree is read-only for
    every consumer, per-node data lives in a side table keyed by id(node), and no consumer deep-copies a parsed node.
    THE MECHANISM: the parser hands out ast.Load, Store, Del and the operator nodes as process-wide singletons, so an
    attribute another census writes on one (`child._parent = node` over every node it walks, the singletons among them)
    is on every tree parsed afterwards, and a deepcopy of a small expression that holds a tagged singleton follows the
    tag into that census's whole graph (a RecursionError through copy.py on CI's 3.10 and 3.11, a 147 s copy on 3.12).
    Until the fourth commit of the same day both substitution sites deep-copied the parsed node; the pins in the test
    class plant the tag and hold the walk to the contract."""
    return ast.parse(ast.unparse(node), mode="eval").body


class _Substitute(ast.NodeTransformer):
    """An expression with every name bound once at import replaced by its value expression, recursively, rewritten over a
    FRESH tree parsed from the expression's text (_fresh), never over the parsed node or a copy of it; a name already
    under substitution (`seen`) is left as it is, so a self-referencing binding cannot loop."""

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
    """The value expression `node` as text with every name bound once at import replaced by what it is bound to (`_ROOT`
    -> `tempfile.mkdtemp()`, `_STATE_TD.name` -> `tempfile.TemporaryDirectory().name`, `os.path.join(_tmp, 'romp')` ->
    `os.path.join(tempfile.mkdtemp(), 'romp')`), so a licence's value check reads the value and not the name; the text
    of `node` itself where nothing substitutes (a name bound twice, or not by an assignment, stays a name); "" for None."""
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
        items = names.dicts.get(node.id)
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
#   __setitem__ and __ior__ for the dunder spellings, called on the mapping or unbound with the mapping as the first argument),
#   the VALUE expression (an ast node, or None where the shape has none the scan reads), the LINE of the statement (of
#   the CALL, for a write reached through one), the value RESOLVED through the names bound once at import (_resolved) and
#   VIA: "" for a write made where it stands, else the callee chain a write at import is reached through (_reached_writes)


def _env_write_records(node, names, where="<module>"):
    """Every environment write under `node`, as _Write records: `environ[KEY] = v`, `environ |= {...}`,
    `environ.update({...})`, `environ.update(KEY=v)`, `environ.update(NAME)` for a NAME bound to a dict literal,
    `environ.setdefault(KEY, v)` and `os.putenv(KEY, v)`, environ spelled any way `names` knows (review round 2,
    2026-09-18: the subscript and setdefault alone before, so a module-level update was invisible), and since the third
    commit of 2026-09-22 the dunder spellings `environ.__setitem__(KEY, v)` and `environ.__ior__({...})`, the same two
    unbound with the mapping as the first argument (`dict.__setitem__(environ, KEY, v)`), and every shape through
    `os.environb` with a bytes key (the verifier found the three passing silently against the contract). A write whose keys
    cannot be read from the source raises UnreadableEnvWrite naming the line, never skips: the repo-wide import-time
    rule is only as good as the writes it reads. Removals (`pop`, `del`) are not writes and are outside this scan's
    contract: unset is the production default and the state a clean shell gives every module, so a removal at import
    sets nothing a later module would not have found on its own; _env_removals reads them where a restore counts."""
    names = names.within(node)
    out = []

    def write(key, shape, value, line):
        out.append(_Write(key, shape, value, line, _resolved(value, names)))

    for n in ast.walk(node):
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            if isinstance(n, ast.AnnAssign) and n.value is None:
                continue        # a bare annotation writes nothing
            for t in _flat_targets(n.targets if isinstance(n, ast.Assign) else [n.target]):
                if isinstance(t, ast.Subscript) and names.is_environ(t.value):
                    for k in sorted(_keys(t.slice, n, where, "environment assignment", names)):
                        write(k, "assignment", n.value, n.lineno)
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
    """The expressions a block statement evaluates at import beside its bodies: an if or while test, a for iterable,
    the with items, a match subject and its guards, the handler types of a try."""
    out = [getattr(s, a) for a in ("test", "iter", "subject") if getattr(s, a, None) is not None]
    out += [i.context_expr for i in getattr(s, "items", [])]
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
    for s in body:
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for h in _def_header(s):
                yield h, nested
        elif isinstance(s, ast.ClassDef):
            for h in _class_header(s):
                yield h, nested
            yield from _import_time_nodes(s.body, True)
        elif isinstance(s, _COMPOUND):
            for h in _compound_header(s):
                yield h, nested
            for attr in ("body", "orelse", "finalbody"):
                yield from _import_time_nodes(getattr(s, attr, None) or [], True)
            for h in getattr(s, "handlers", []):
                yield from _import_time_nodes(h.body, True)
            for c in getattr(s, "cases", []):
                yield from _import_time_nodes(c.body, True)
        else:
            yield s, nested


# ───────── writes reached through a call at import: a def or class under tests/ the scan can resolve ─────────
#
# A module-level call runs at import, so a write in the callee's body is a module-level write (the verifier's finding on
# this PR, 2026-09-22: `def _floor(): os.environ[...] = ...` then `_floor()` at module level left the pin green). The
# scan resolves a call's callee to code under tests/ and reads it: a def of the module, a class of the module (its
# __init__, for an instantiation; a method, for `Class.method()`), a def or class imported from a module under tests/
# (`from helper import floor; floor()`, `import helper; helper.floor()`, `import helper as h; h.floor()`,
# `helper.Seam.arm()`), a module imported by its dotted name (`import tests.helper; tests.helper.floor()`) and a name a
# star import binds (`from helper import *; floor()`; the module's `__all__` is not consulted, so a private name is read
# as bound too, the safe side: the two dotted and star shapes passed the resolver silently until the third commit of
# 2026-09-22), a bare decorator (`@_arm` calls `_arm(fn)` at import) and a decorator factory's call, recursively through
# the callee's own calls. OUTSIDE the scan, named here so nobody mistakes the pin for wider than it is. Callees the
# resolver cannot reach: product code (the modules a test loads by path through romp_load.load_source, itself a name
# bound to product code and not a def under tests/; what product code writes to the environment at import is the
# product's own tests' matter), the standard library, a method called on an instance (`Seam().arm()`), a lambda, a call
# through a name bound to a call's result (`under_conftest = unittest.skipUnless(...)`), and `exec`/`eval` of a string.
# Writes that reach the mapping other than by a method called on it (or __setitem__/__ior__ unbound with the mapping as
# the first argument): `operator.setitem(os.environ, K, v)`, a bound method held in a name or fetched by getattr
# (`_set = os.environ.__setitem__; _set(K, v)`), a functools.partial of one, `posix.putenv`, and an unbound update or
# setdefault on the mapping's class (`MutableMapping.update(os.environ, {...})`, which the scan cannot tell from
# `saved.update(os.environ)`, a read). None of these is in the tree at module level. The census at this head found two
# calls at import that reach a write, both licensed: tests/test_intr_marks_memo.py and tests/test_merge_tx_sets_light.py
# call test_asm_checkpoint.kernel_module() at module level (`import test_asm_checkpoint as TA; km = TA.kernel_module()`)
# and its body setdefaults ROMP_KERNEL_NO_OPEN to "1"; the verifier's own walker had counted the shape empty, so the
# module-alias form is one a resolver misses easily. The 79 module-level calls to local defs reach no write; the 1179
# through tests-local imports are almost all load_source; 0 on module classes; 0 decorators or defaults reach one.

_Module = collections.namedtuple("_Module", "where tree names defs classes imports stars root")
#   a module the resolver reads: its label (WHERE), TREE, import-time NAMES (_EnvNames), module-level DEFS and CLASSES by
#   name, IMPORTS {local name, dotted for `import tests.helper`: (path of a module under ROOT, attribute or None for the
#   module itself)}, STARS, the paths of the modules under ROOT it star-imports, and the ROOT the imports resolve against
#   (tests/, or a synthetic tree's directory in the tests of the scan itself)

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
    import f [as g]` binds f, a def or class of M; `from M import *` puts M's path in the second value, and _callee reads a
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


def _module_record(tree, where, root):
    imports, stars = _imports_of(tree, root)
    return _Module(where, tree, _EnvNames(tree), {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)},
                   {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}, imports, stars, root)


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


def _in_module(target, rest):
    """(target, [FunctionDef, ...]) for the name chain `rest` in the module `target`: one name, a def (or a class, whose
    __init__ chain runs on instantiation); two names, a method on a class of the module; (None, []) for anything else."""
    if len(rest) == 1:
        if rest[0] in target.defs:
            return target, [target.defs[rest[0]]]
        if rest[0] in target.classes:
            return target, _method_chain(target.classes[rest[0]], "__init__", target.classes)
    elif len(rest) == 2 and rest[0] in target.classes:
        return target, _method_chain(target.classes[rest[0]], rest[1], target.classes)
    return None, []


def _callee(call, mod):
    """(module, [FunctionDef, ...]) for a call at import in `mod` whose callee the scan can resolve to code under
    `mod.root`, read along the callee's dotted chain (_dotted): a def of the module, a class of the module (its __init__
    chain), a method called on a class of the module; else the LONGEST prefix of the chain an import binds (`floor`,
    `_h`, `Seam`, `tests.helper`) with the rest of the chain looked up in that module (a def, a class, `Class.method`);
    else, for a bare name or a `Class.method`, the star-imported modules in order (the third commit of 2026-09-22, with
    the dotted import); (None, []) for anything else (the comment above names what that is)."""
    f = call.func if isinstance(call, ast.Call) else call
    parts = _dotted(f)
    if not parts:
        return None, []
    target, fns = _in_module(mod, parts)
    if fns:
        return target, fns
    for i in range(len(parts), 0, -1):
        base = ".".join(parts[:i])
        if base in mod.imports:
            path, attr = mod.imports[base]
            rest = ([attr] if attr is not None else []) + parts[i:]
            return _in_module(_module_at(path, mod.root), rest) if rest else (None, [])
    if len(parts) <= 2:
        for path in mod.stars:
            target, fns = _in_module(_module_at(path, mod.root), parts)
            if fns:
                return target, fns
    return None, []


def _reached_writes(node, mod, seen=frozenset(), depth=0):
    """Every environment write the import-time code `node` of `mod` reaches THROUGH A CALL the scan can resolve
    (_callee), as _Write records at the CALL's line with `via` naming the callee, where it is defined and the write's
    own line, recursively through the callee's own calls (a callee is read once per chain, six deep at most). A bare
    name or attribute handed in (a decorator without parentheses) is read as a call of it. A write in a callee that the
    scan cannot read is loud, naming the callee's line and the call site."""
    calls = [n for n in ast.walk(node) if isinstance(n, ast.Call)]
    if isinstance(node, (ast.Name, ast.Attribute)):
        calls.append(node)
    out = []
    for call in calls:
        target, fns = _callee(call, mod)
        for fn in fns:
            key = (target.where, fn.name, fn.lineno)
            if key in seen or depth > 6:
                continue
            label = "%s() at %s:%d" % (fn.name, target.where, fn.lineno)
            try:
                inner = _env_write_records(fn, target.names, target.where) + _reached_writes(fn, target, seen | {key}, depth + 1)
            except UnreadableEnvWrite as e:
                raise UnreadableEnvWrite("%s; reached at import from %s:%d through %s" % (e, mod.where, call.lineno, label)) from None
            for w in inner:
                via = ("%s -> %s" % (label, w.via)) if w.via else ("%s, the write at line %d" % (label, w.line))
                out.append(w._replace(line=call.lineno, via=via))
    return out


def _module_level_env_write_records(tree, where="<module>", root=None):
    """Every environment write the module makes at import, as (_Write, nested) pairs: `nested` is True for a write not
    directly in the module body (inside a module-level if/for/while/with/try body, a class body, a header; a bare grep
    at column 0 misses those). In every shape _env_write_records reads, in every node _import_time_nodes yields, plus
    every write reached through a call at import the scan can resolve (_reached_writes; at the call's line, `via`
    set); `where` names the file in the loud message for a write the scan cannot read; `root` is where the module's
    tests-local imports resolve (tests/ by default)."""
    mod = _module_record(tree, where, HERE if root is None else root)
    out = []
    for node, nested in _import_time_nodes(tree.body):
        out += [(w, nested) for w in _env_write_records(node, mod.names, where)]
        out += [(w, nested) for w in _reached_writes(node, mod)]
    return out


def _module_level_env_writes(tree, where="<module>", root=None):
    """The environment keys the module writes at import, in every shape _env_writes reads, in any node
    _import_time_nodes yields, through any call _reached_writes resolves; `where` names the file in the loud message for
    a write the scan cannot read."""
    return {w.key for w, _nested in _module_level_env_write_records(tree, where, root)}


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
        return "%s (a name the scan cannot read through: bound more than once at import, or not by an assignment)" % rec.value
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
    to the test's port), and registers a cleanup that restores the three names and BUS_PORT. A list rather than
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
        restored, rattrs = _cleanup_restores(set_up, cls, classes, tree, names, where)
        for leg in TRIO:
            if leg not in restored:
                faults.append("%s.setUp (own or through super()) registers no cleanup that restores %s: a tearDown restore is "
                              "skipped when a later setUp statement raises, and the value outlives the class (review round 1, "
                              "2026-09-18)" % (cls.name, leg))
        if "BUS_PORT" not in rattrs:
            faults.append("%s.setUp (own or through super()) registers no cleanup that restores the kernel's BUS_PORT" % cls.name)
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
    # sitecustomize for one child pytest run of the peer-notify guard test (tests/test_hermetic_kernel_postal.py): every
    # Python process of the run records each socket connect by port (and whether its PYTHONPATH still names this spy, so
    # a child forked then with its environment loads it too) and its own argv at exit, and refuses a connect to the
    # machine's fixed bus port before it reaches the network
    import atexit, errno, json, os, socket, sys
    _OUT, _FIXED = os.environ.get("ROMP_TEST_DIAL_SPY"), os.environ.get("ROMP_TEST_DIAL_SPY_FIXED")
    _HERE = os.path.dirname(os.path.abspath(__file__))
    if _OUT and _FIXED:
        def _record(kind, **fields):
            fields.update(kind=kind, pid=os.getpid(), argv=[str(a) for a in getattr(sys, "argv", [])],
                          spy_on_path=_HERE in os.environ.get("PYTHONPATH", "").split(os.pathsep))
            with open(_OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps(fields) + "\\n")

        def _port(address):
            try:
                return int(address[1])
            except Exception:
                return None
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


def _attribute_binds(node, attrs):
    """Every node inside `node`, nested defs included, that binds or deletes an attribute named in `attrs` on ANY object,
    so a module reached through another name (`subprocess.run = ...` beside `km.subprocess.run`) is read too: an
    attribute target in every binding form, one target of an assignment or one of several, unpacked from a tuple or a
    list or starred, an augmented or annotated one, a for, with or comprehension target, or a del. Every one of those
    carries a Store or Del context on the attribute node, which is what this reads."""
    return [n for n in ast.walk(node) if isinstance(n, ast.Attribute) and isinstance(n.ctx, (ast.Store, ast.Del)) and n.attr in attrs]


def _name_binds(node, names):
    """Every node inside `node`, nested defs included, that binds or deletes one of `names`: a name stored or deleted (an
    assignment, augmented or annotated, a for, with or comprehension target, a walrus, a del), an import's name or `as`
    name, a def or class so named, an except clause's `as` name, a match capture or rest, and a global or nonlocal
    declaration of it."""
    names = set(names)
    return [n for n in ast.walk(node)
            if (isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)) and n.id in names)
            or (isinstance(n, ast.alias) and (n.asname or n.name.split(".")[0]) in names)
            or (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.ExceptHandler)) and n.name in names)
            or (isinstance(n, (ast.Global, ast.Nonlocal)) and names & set(n.names))
            or (type(n).__name__ in ("MatchAs", "MatchStar") and getattr(n, "name", None) in names)
            or (type(n).__name__ == "MatchMapping" and getattr(n, "rest", None) in names)]


_REFLECTIVE_CALLS = ("setattr", "delattr", "getattr", "vars", "globals", "locals", "exec", "eval", "compile", "__import__", "patch")
_REFLECTIVE_ATTRS = ("__setattr__", "__delattr__", "__dict__", "setattr", "delattr", "patch", "modules", "import_module")


def _reflective(n):
    """`n` reaches an attribute, a module or a name by reflection or by a string, so what it binds is decided at run time:
    a call of setattr, delattr, getattr, vars, globals, locals, exec, eval, compile, __import__ or patch by that bare
    name; an attribute __setattr__, __delattr__, __dict__, setattr or delattr (a method so named, as pytest's monkeypatch
    spells them), patch (mock's, mock.patch.object and mock.patch.dict among them), modules (sys.modules) or
    import_module (importlib's)."""
    return ((isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _REFLECTIVE_CALLS)
            or (isinstance(n, ast.Attribute) and n.attr in _REFLECTIVE_ATTRS))


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
    shape the round-1 review found leaking on a subclass setUp that raises."""
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


def _method_chain(cls, name, classes):
    """The FunctionDefs that run when `name` is called on `cls`: its own, then a base's (through the bases defined in
    the same module) when the own one delegates with super().<name>() or there is no own one. Empty when nothing runs."""
    own = next((n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name), None)
    chain = [own] if own is not None else []
    delegates = own is None or any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == name
        and isinstance(n.func.value, ast.Call) and isinstance(n.func.value.func, ast.Name) and n.func.value.func.id == "super"
        for n in ast.walk(own))
    if delegates:
        for b in cls.bases:
            if isinstance(b, ast.Name) and b.id in classes:
                chain += _method_chain(classes[b.id], name, classes)
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
        module level; the setUp of every class that attaches or detaches (its own or through super()) sets all three and
        patches the kernel's BUS_PORT, the import-time read, and registers a cleanup that puts all four back. A
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
        commit of 2026-09-22), each faulting once; a planted update whose keys the scan cannot read is loud, naming the
        line, never a clean pass; and the restore moved back into a tearDown with no cleanup registered, which faults
        every leg and the BUS_PORT restore of both attaching classes."""
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
        for leg in TRIO + ("BUS_PORT",):
            self.assertEqual(sum(1 for f in faults if leg in f), 2, "%s: one fault per attaching class: %r" % (leg, faults))
        self.assertEqual(len(faults), 2 * (len(TRIO) + 1), "the three legs and BUS_PORT, per attaching class, nothing else: %r" % faults)

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
        positional dir), which the regex before the third commit of 2026-09-22 accepted; a licence whose re-assert
        conftest dropped; and a dead licence. The floor modules are never faulted, whatever they write; a licensed write
        is clean, every mkdtemp form the census shows among them."""
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
                             ('os.environ["ROMP_SERVICE_ENV"] = os.path.join(tempfile.mkdtemp(suffix="-real"), "service.env")', "not one this licence covers")):
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
                     'def _floor():\n    os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")\n_floor()'):
            self.assertEqual(full("import os, tempfile\n" + line + "\n", "test_planted.py"), [], line)
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
        """module_level_env_census over a synthetic tree: one module, six shapes (the dunder spelling among them since the
        third commit of 2026-09-22), two names; the nested write is counted as such; the table names the module count. The counts over the real tree are the by-product fork PR #871's
        docstring recorded from a grep, re-derived by ast here and pasted at the head in the PR; they are NOT pinned by
        equality, since they move with every new module (the enforced property is the licensed set's equality)."""
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        src = ("import os\nos.environ['A'] = '1'\nos.environ.setdefault('A', '2')\nos.environ.update({'B': '3'})\n"
               "os.environ |= {'B': '4'}\nos.putenv('B', '5')\nif True:\n    os.environ['A'] = '6'\n"
               "os.environ.__setitem__('B', '9')\n"                  # the dunder spelling, its own shape
               "def f():\n    os.environ['C'] = 'never counted'\n"
               "class K:\n    os.environ['A'] = '7'\n"                 # a class body runs at import: counted, nested
               "def g():\n    os.environ['D'] = '8'\ng()\n")           # a def called at import: counted at the call, via set
        path = os.path.join(d, "test_planted.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        n, counts, records = module_level_env_census([path])
        self.assertEqual(n, 1)
        self.assertEqual(counts, {"A": {"assignment": 3, "setdefault": 1}, "B": {"update": 1, "|=": 1, "putenv": 1, "__setitem__": 1},
                                  "D": {"assignment": 1}})
        self.assertEqual([r.nested for r in records["A"]], [False, False, True, True])
        self.assertEqual(records["A"][2].value, "'6'")
        self.assertEqual(records["A"][3].value, "'7'")
        rel = os.path.relpath(path, HERE)          # the census labels a module relative to tests/, a synthetic one included
        self.assertEqual((records["D"][0].line, records["D"][0].via), (16, "g() at %s:14, the write at line 15" % rel))
        table = _census_table([path])
        self.assertIn("modules: 1", table)
        self.assertIn("%-34s %-11s %6d %8d %7d %8d" % ("A", "assignment", 3, 1, 2, 0), table)
        self.assertIn("%-34s %-11s %6d %8d %7d %8d" % ("D", "assignment", 1, 1, 0, 1), table)

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
        environment."""
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
                      'class _Planted:\n    os.environb.__setitem__(b"ROMP_POSTAL_PEERS", b"0")'):
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
                      'saved = {}\nsaved.setdefault(os.environ, "0")'):                                           # not the environment's setdefault
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
                         "a def of the module itself outranks a helper's of the same name")
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
                      "dict.__ior__(os.environ, saved)", 'os.environb[name] = b"0"', "os.environb.update(saved)"):
            with self.assertRaises(UnreadableEnvWrite, msg=shape) as loud:
                _module_level_env_writes(ast.parse("import os\n" + shape + "\n"), "planted.py")
            self.assertIn("cannot read the key", str(loud.exception), shape)
            self.assertIn("at line %d of planted.py" % (shape.count("\n") + 2), str(loud.exception), shape)

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
        The safe side is read over the whole function, every statement, run or not, nested defs included, so a conditional
        or early put-back still reds: no statement binds or deletes run, subprocess or _revive_postal_bus on any object, in
        any binding form (_attribute_binds), other than the four required; none binds the names km or os (_name_binds);
        none reaches anything by reflection or by a string (_reflective: setattr and the verifier's tuple target of round
        2's third commit on fork PR #894 passed a scan that read single-target assignments alone); and the environment is
        named only in os.environ.get reads, in the trio and in the finally after the wait (_environ_mentions).
        NOT READ, each with what sees it instead: a put-back made by code the test calls but does not contain (a helper of
        the module, setUp or tearDown), and the class's own decorators. An early put-back of the fake lets the revive's
        real ensure child start, which the executed pin's spy records (the verifier's two mutants reddened it there); of
        the revive, the kick runs the real revive, the Event is never set and the guard test's own wait fails; of the
        environment, nothing sees it while the fake holds, since every postal-service call is then answered in the
        process, so the restore's place after the wait is a second belt. A skip or an exit from a callee or from the class
        reds the executed pin, which requires the child run to pass.
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
        trio = [s.value for s in before if _call_stmt(s, ["os", "environ", "update"])]
        self.assertEqual(len(trio), 1, "the trio is set by one os.environ.update statement that runs before the call")
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
        # the safe side, over every statement of the test, run or not, nested defs included
        self.assertEqual([n.lineno for n in ast.walk(fn) if _reflective(n)], [],
                         "no statement of the test reaches an attribute, a module or a name by reflection or by a string: what it binds is decided at run time")
        allowed = (before[install[0]].targets[0], final[unfake[0]].targets[0], before[rebind[0]].targets[0], final[unwrap[0]].targets[0])
        self.assertEqual([(n.lineno, n.attr) for n in _attribute_binds(fn, ("run", "subprocess", "_revive_postal_bus")) if not any(n is a for a in allowed)], [],
                         "no other statement of the test binds or deletes run, subprocess or _revive_postal_bus, on any object, in any binding form")
        self.assertEqual([n.lineno for n in _name_binds(fn, ("km", "os"))], [],
                         "no statement of the test binds the names km or os: every km and os it writes through is the kernel module and the os module")
        gets = {id(c.func.value) for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "get"}
        where_writes_go = {id(n) for s in [trio[0]] + final[wait + 1:] for n in ast.walk(s)}
        self.assertEqual([n.lineno for n in _environ_mentions(fn) if id(n) not in gets and id(n) not in where_writes_go], [],
                         "the test names the environment only in os.environ.get reads, in the trio and in the finally after the wait")
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
        return {"fn": fn, "fake": fake.id, "real_run": kept_run[0][1], "reached": reached[0], "event": event, "ended": ended,
                "real_revive": kept_revive[0][1], "try": top[tries[0]], "install": before[install[0]], "wait": final[wait],
                "after": after, "wrapper": before[defs[wrapper.id]], "fake_def": before[defs[fake.id]]}

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
        beside it, as fork PR #875's assertion will be once the two texts meet, is not what this reads). No other statement
        of the test, run or not, binds or deletes run, subprocess or _revive_postal_bus on any object in any binding form,
        binds km or os, reaches anything by reflection or by a string, or names the environment outside os.environ.get
        reads, the trio and the finally after the wait; what that leaves unread (a put-back made by code the test calls) is
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
        road's place it reds."""
        cls_src = self._guard_class_source()
        shape = self._guard_shape(cls_src)
        stubbed = sorted({c.func.value.id for c in ast.walk(shape["fake_def"]) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                          and c.func.attr == "append" and isinstance(c.func.value, ast.Name)})
        self.assertEqual(len(stubbed), 1, "the fake records the calls it answers in one list of its own: %r" % stubbed)
        names = {k: shape[k] for k in ("event", "ended", "real_run", "real_revive")}
        names["stubbed"] = stubbed[0]
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
                   "the wrapper try's clauses": (wrapper_try.body[-1], "after", wrapper_try.col_offset)}
        after_try, finally_run, one_try, wait_msg = ("after the try the wait's result", "the finally puts the real run back",
                                                    "the notify call runs in one try", "the finally waits on the Event")
        reflect, binds, rebinds, env = ("by reflection or by a string", "binds or deletes run, subprocess or _revive_postal_bus",
                                        "binds the names km or os", "names the environment only in")
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
             "one list is asserted empty that every road to the real run appends to"))
        for label, anchor, text, fragment in plants:
            node, where = anchors[anchor][:2]
            planted = _plant_at(cls_src, node, text % names, where, *anchors[anchor][2:])
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
    unittest.main()
