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
three around the one call that provokes the revive (the peer-notify test), so its kernel never even asks. Peers is
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
BUS_PORT, read at import, patched beside them and restored by the same cleanups), the guard test stubs the revive road
and waits for it, conftest pops the bus port before every test, the seam moves per test in the ten postal modules that
wrote it at import, and the repo-wide pin holds the set of names the test modules write at module level EQUAL to a
licensed set (LICENSED_MODULE_LEVEL_WRITES: each name with a checked condition, a temporary licence dated and pointed
at the item it waits on), never a floor. `python -m tests.test_hermetic_kernel_postal --census` prints the counts by
name and shape (fork PR #871's by-product figures, derived by ast). Beside it, tests/conftest.py's run-end process
check makes a run red that leaves any process holding its temp root (tests/test_run_end_leaked_processes.py).
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
# (the revive road's ensure runs with the test process's environment; the guard's own trio is restored by the time the
# thread spawns): the port named as the run's own (conftest's marker beside it) licensed the bind, client-only was inert
# with peers on, and the seam's one row kept the bus from ever autostopping. The pin below holds the set of names
# written at module level by the test modules EQUAL to this table, with every licence's condition checked per write, so
# a new name reds by construction and a licence with no writer left is removed rather than kept. The two floor modules
# (FLOOR_MODULES) are the one home of the run-wide values and are licensed wholesale.
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
    here, planted = sys.argv[1], sys.argv[2]
    sys.path.insert(0, here)
    sys.path.insert(0, os.path.dirname(here))    # the checkout: the module imports tests.conftest for restore_env
    if planted:
        # a synthetic copy of the module, compiled under the real file's name so its HERE and BIN resolve
        real = os.path.join(here, "test_kernel_tunnels.py")
        t = type(sys)("test_kernel_tunnels_planted")
        t.__file__ = real
        exec(compile(open(planted, encoding="utf-8").read(), real, "exec"), t.__dict__)
    else:
        import test_kernel_tunnels as t
    env = lambda: {k: os.environ.get(k) for k in TRIO}
    out = {"after_import": env(), "bus_port_at_import": t.km.BUS_PORT}
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
        for name in ("ROMP_POSTAL_PEERS", "ROMP_POSTAL_PORT", "ROMP_POSTAL_CLIENT_ONLY", "ROMP_SESSIONS_FILE", "ROMP_POSTAL_HOST"):
            self.assertNotIn(name, LICENSED_MODULE_LEVEL_WRITES, "%s is a leak this rule exists to catch, never a licence" % name)
            self.assertNotIn(name, records, "%s is written at module level by %r" % (name, [r.module for r in records.get(name, [])]))

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

    def _tunnels_probe(self, planted_text=None):
        """_PROBE in a fresh interpreter over the real module (imported) or over `planted_text`, a synthetic copy compiled
        under the real file's name; returns the child's report."""
        path = ""
        if planted_text is not None:
            d = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, d, True)
            path = os.path.join(d, "planted_tunnels_module.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(planted_text)
        env = dict(os.environ)
        env.pop("ROMP_POSTAL_PEERS", None)
        res = subprocess.run([sys.executable, "-c", _PROBE, HERE, path], capture_output=True, text=True, timeout=180, env=env, cwd=HERE)
        self.assertEqual(res.returncode, 0, res.stderr[-2000:])
        return json.loads(res.stdout.strip().splitlines()[-1])

    def test_importing_the_attaching_module_writes_no_leg_of_the_trio_and_its_setup_pins_all_three_for_the_test(self):
        """Executed, not read: a fresh interpreter pops the three names, imports tests/test_kernel_tunnels.py (which loads
        the kernel in-process against its own temp state and starts no bus) and reports them after the import (none
        set, and the kernel's BUS_PORT is its default, read from an environment with no port), inside an attaching
        class's setUp (peers off, client-only, a port of the test's own with BUS_PORT patched to match), after its
        tearDown, after its cleanups with a peers value a shell might have left (the three names and BUS_PORT put back),
        and after a subclass setUp that raises past the writes. Before 2026-09-18 the import alone wrote peers "0";
        before 2026-09-22 it wrote the port and client-only, the two names the real bus of fork PR #813's CI inherited;
        before review round 1 the raising setUp left the 0 behind (the restore was a tearDown)."""
        out = self._tunnels_probe()
        self.assertEqual(out["after_import"], {"ROMP_POSTAL_PORT": None, "ROMP_POSTAL_CLIENT_ONLY": None, "ROMP_POSTAL_PEERS": None},
                         "importing the module writes no leg of the trio (a write at import holds for every child of every test in the process)")
        self.assertEqual(out["in_setup"]["ROMP_POSTAL_PEERS"], "0", "an attaching class's setUp turns peers off for its test")
        self.assertEqual(out["in_setup"]["ROMP_POSTAL_CLIENT_ONLY"], "1", "...and client-only on")
        self.assertTrue((out["in_setup"]["ROMP_POSTAL_PORT"] or "").isdigit(), "...and a port of the test's own: %r" % out["in_setup"])
        self.assertNotEqual(out["in_setup"]["ROMP_POSTAL_PORT"], str(out["bus_port_at_import"]), "...not the kernel's import-time default")
        self.assertTrue(out["bus_port_in_setup_matches"], "the kernel's BUS_PORT, read at import, is patched to the test's port")
        self.assertEqual(out["after_teardown"]["ROMP_POSTAL_PEERS"], "0", "the value is still set when tearDown returns: the subclass's detach there reads it, and the restore is a cleanup, which runs after tearDown")
        self.assertEqual(out["after_cleanups"], {"ROMP_POSTAL_PORT": None, "ROMP_POSTAL_CLIENT_ONLY": None, "ROMP_POSTAL_PEERS": "1"},
                         "...and the cleanup restores what it found: the shell's peers value, no port, no client-only")
        self.assertEqual(out["bus_port_after_cleanups"], out["bus_port_at_import"], "...and BUS_PORT")
        self.assertEqual(out["setup_raise_errors"], 1, "the planted subclass setUp raised, as an error on the case")
        self.assertEqual(out["after_setup_raise"], {"ROMP_POSTAL_PORT": None, "ROMP_POSTAL_CLIENT_ONLY": None, "ROMP_POSTAL_PEERS": "1"},
                         "a subclass setUp that raises after the writes still restores them: a tearDown restore is skipped on that path (review round 1, 2026-09-18)")
        self.assertEqual(out["bus_port_after_setup_raise"], out["bus_port_at_import"])

    def test_the_import_probe_reds_on_a_planted_module_level_write_of_any_leg(self):
        """The same planted writes, run: a copy of the module with `os.environ["ROMP_POSTAL_PEERS"] = "0"` restored
        before the load reports "0" after the import, so does one with `os.environ.update(ROMP_POSTAL_PEERS="0")` there
        (the shape review round 2 found the static scan blind to), and a copy with the port written back before the
        load reports the port after the import AND a kernel whose BUS_PORT is that port (the import-time read, which is
        why the leak's child could bind it), so the probe is known to see the leaks it guards against (review rounds 1
        and 2, 2026-09-18; the port 2026-09-22)."""
        for label, lines in (("assignment", 'os.environ["ROMP_POSTAL_PEERS"] = "0"\n'),
                             ("update", 'os.environ.update(ROMP_POSTAL_PEERS="0")\n'),
                             ("class body", 'class _Planted:\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n')):    # runs at import (the fixup of 2026-09-22)
            out = self._tunnels_probe(_plant(_tunnels_source(), lines))
            self.assertEqual(out["after_import"]["ROMP_POSTAL_PEERS"], "0", "%s: the probe sees a module-level write at import" % label)
            self.assertEqual(out["after_cleanups"]["ROMP_POSTAL_PEERS"], "1", "%s: the planted copy's own cleanup still restores the shell's value" % label)
        out = self._tunnels_probe(_plant(_tunnels_source(), 'os.environ["ROMP_POSTAL_PORT"] = "45678"\nos.environ["ROMP_POSTAL_CLIENT_ONLY"] = "1"\n'))
        self.assertEqual(out["after_import"]["ROMP_POSTAL_PORT"], "45678", "the probe sees the port written at import")
        self.assertEqual(out["after_import"]["ROMP_POSTAL_CLIENT_ONLY"], "1")
        self.assertEqual(out["bus_port_at_import"], 45678, "...and the kernel read it at import: the bus a stray revive would start binds it")
        self.assertEqual(out["after_cleanups"]["ROMP_POSTAL_PORT"], "45678", "the planted copy's cleanup puts the import-time value back, which is the leak")

    def test_the_peer_notify_guard_test_stubs_the_revive_road_before_the_call_and_waits_for_it(self):
        """Read from the source of tests/test_kernel.py's PostalPeerTunnels.test_notify_bus_peer_is_guarded, by ast: before
        the _notify_bus_peer call the test binds a stub over the revive road (km.subprocess.run, the call ensure makes)
        and sets the trio (client-only, peers off, a port nothing can bind); after the call it waits on the revive (an
        Event the stub sets) and asserts the recorded argv names the postal service's ensure, and the restore of the
        trio follows. What this pin GUARANTEES is the placement of those statements, the weaker thing; that no child
        starts and that the argv is the ensure's is the guarded test's own execution (it fails when the stub is not
        reached). Before 2026-09-22 the test set the trio and nothing else, the revive thread raced the restore, and
        the restore won: the child inherited another module's module-level port and client-only and started a real bus
        (fork PR #813's CI)."""
        src = open(os.path.join(HERE, "test_kernel.py"), encoding="utf-8", errors="replace").read()
        tree = ast.parse(src)
        cls = next(c for c in tree.body if isinstance(c, ast.ClassDef) and c.name == "PostalPeerTunnels")
        fn = next(f for f in cls.body if isinstance(f, ast.FunctionDef) and f.name == "test_notify_bus_peer_is_guarded")
        calls = {}
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                calls.setdefault(n.func.attr, []).append(n.lineno)
        notify = min(calls.get("_notify_bus_peer") or [0])
        self.assertTrue(notify, "the guarded test calls _notify_bus_peer")
        stubs = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Assign)
                 for t in n.targets if isinstance(t, ast.Attribute) and t.attr == "run"
                 and isinstance(t.value, ast.Attribute) and t.value.attr == "subprocess"]
        self.assertTrue(stubs and min(stubs) < notify, "km.subprocess.run is stubbed before the call whose refusal revives the bus: %r" % stubs)
        names = _EnvNames(tree)
        trio_writes = [w for w in _env_write_records(fn, names, "test_kernel.py") if w.key in TRIO]
        self.assertEqual({w.key for w in trio_writes}, set(TRIO), "the trio is set in the test")
        first = {leg: min(w.line for w in trio_writes if w.key == leg) for leg in TRIO}
        self.assertTrue(all(line < notify for line in first.values()), "...each leg before the call (the restore after it is a write too): %r" % first)
        self.assertTrue(any(l > notify for l in calls.get("wait", [])), "the test waits on the revive after the call (the Event the stub sets)")
        self.assertTrue(any(isinstance(n, ast.Constant) and n.value == "ensure" for n in ast.walk(fn)), "...and asserts the argv names ensure")
        self.assertTrue(any(l > notify for l in calls.get("pop", [])), "...and restores the trio after it")

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
