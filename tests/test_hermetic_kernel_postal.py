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
invisible), and a write whose keys the scan cannot read fails the test rather than passing unread. The probe beside
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
        if all(isinstance(k, ast.Constant) and isinstance(k.value, str) for k in node.keys):
            return {k.value: v for k, v in zip(node.keys, node.values)}
        return None
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict" and not node.args
            and all(kw.arg is not None for kw in node.keywords)):
        return {kw.arg: kw.value for kw in node.keywords}
    return None


def _literal_mapping_keys(node):
    """The string keys of a dict literal or of a `dict(...)` of keywords; None when _literal_mapping cannot read it."""
    m = _literal_mapping(node)
    return None if m is None else set(m)


class _EnvNames:
    """What spells the process environment in a module, so a write is read whatever name it goes through (review round 2,
    2026-09-18; before it the scan read `os.environ[...]` and `os.environ.setdefault` alone, and a module-level
    `os.environ.update(...)` was invisible to it): `os.environ` under any name os is imported as, `environ` after
    `from os import environ` (or its `as` name), and every name bound to it (`env = os.environ`). Beside those, the names
    bound to a dict literal or to `dict(...)` of keywords, which an `update(NAME)` reads through the name
    (tests/test_update_banner_confirm_served.py updates its DEAD_PORTS that way at import); a name bound any other way,
    or more than once, is unreadable, and an update of it is loud. Built from the statements that run at import; a
    function's own bindings are added when the function is walked (`within`)."""

    def __init__(self, tree=None):
        self.os_names = {"os"}
        self.environ_names = set()
        self.dicts = {}
        self.loop_literals = {}      # a name a `for` binds to each of a tuple or list of string literals, in turn
        if tree is not None:
            self.absorb(_module_level_statements(tree.body))
            for loop in _module_level_compounds(tree.body, ast.For):
                self._absorb_loop(loop)      # the loop header itself: the statements walk yields only its body

    def _absorb_loop(self, n):
        """`for var in ("A", "B"): environ[var] = v` writes exactly A and B (conftest's service-env fixture, the guard
        test's restore): the literals are read; a loop over anything computed, or a name bound by two loops, stays
        unreadable."""
        if isinstance(n.target, ast.Name):
            literal = (isinstance(n.iter, (ast.Tuple, ast.List)) and n.iter.elts
                       and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in n.iter.elts))
            self.loop_literals[n.target.id] = {e.value for e in n.iter.elts} if literal and n.target.id not in self.loop_literals else None

    def absorb(self, nodes):
        for node in nodes:
            for n in ast.walk(node):
                if isinstance(n, ast.For):
                    self._absorb_loop(n)
                elif isinstance(n, ast.Import):
                    self.os_names.update(a.asname for a in n.names if a.name == "os" and a.asname)
                elif isinstance(n, ast.ImportFrom) and n.module == "os":
                    self.environ_names.update(a.asname or a.name for a in n.names if a.name == "environ")
                elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                    name = n.targets[0].id
                    if self.is_environ(n.value):
                        self.environ_names.add(name)
                    else:
                        self.dicts[name] = None if name in self.dicts else _literal_mapping(n.value)
        return self

    def within(self, node):
        """These names plus whatever `node` (a function) binds itself."""
        inner = _EnvNames()
        inner.os_names, inner.environ_names, inner.dicts = set(self.os_names), set(self.environ_names), dict(self.dicts)
        inner.loop_literals = dict(self.loop_literals)
        return inner.absorb([node])

    def is_environ(self, node):
        if isinstance(node, ast.Attribute) and node.attr == "environ" and isinstance(node.value, ast.Name):
            return node.value.id in self.os_names
        return isinstance(node, ast.Name) and node.id in self.environ_names


def _unreadable(what, node, where):
    return UnreadableEnvWrite("cannot read the key%s of this %s at line %d of %s: %s (a string-literal key, a dict literal, "
                              "keyword arguments, or a name bound once to a dict literal are read; a computed key or "
                              "mapping is not)" % ("s" if what == "update" else "", what, node.lineno, where, ast.unparse(node)))


def _keys(node, stmt, where, what, names):
    """The key(s) a subscript, setdefault or putenv names: a string literal, or a name a `for` over string literals binds
    (each literal in turn); loud for anything else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
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


_Write = collections.namedtuple("_Write", "key shape value line")
#   one environment write as the scan reads it: the KEY written, the SHAPE (assignment, setdefault, update, |=, putenv),
#   the VALUE expression (an ast node, or None where the shape has none the scan reads) and the LINE of the statement


def _env_write_records(node, names, where="<module>"):
    """Every environment write under `node`, as _Write records: `environ[KEY] = v`, `environ |= {...}`,
    `environ.update({...})`, `environ.update(KEY=v)`, `environ.update(NAME)` for a NAME bound to a dict literal,
    `environ.setdefault(KEY, v)` and `os.putenv(KEY, v)`, environ spelled any way `names` knows (review round 2,
    2026-09-18: the subscript and setdefault alone before, so a module-level update was invisible). A write whose keys
    cannot be read from the source raises UnreadableEnvWrite naming the line, never skips: the repo-wide import-time
    rule is only as good as the writes it reads. Removals (`pop`, `del`) are not writes and are outside this scan's
    contract: unset is the production default and the state a clean shell gives every module, so a removal at import
    sets nothing a later module would not have found on its own; _env_removals reads them where a restore counts."""
    names = names.within(node)
    out = []
    for n in ast.walk(node):
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            if isinstance(n, ast.AnnAssign) and n.value is None:
                continue        # a bare annotation writes nothing
            for t in _flat_targets(n.targets if isinstance(n, ast.Assign) else [n.target]):
                if isinstance(t, ast.Subscript) and names.is_environ(t.value):
                    out += [_Write(k, "assignment", n.value, n.lineno) for k in sorted(_keys(t.slice, n, where, "environment assignment", names))]
        elif isinstance(n, ast.AugAssign) and names.is_environ(n.target):
            out += [_Write(k, "|=", v, n.lineno) for k, v in _mapping_items(n.value, names, n, where).items()]
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if names.is_environ(n.func.value) and n.func.attr == "update":
                if len(n.args) > 1 or any(kw.arg is None for kw in n.keywords):
                    raise _unreadable("update", n, where)
                for a in n.args:
                    out += [_Write(k, "update", v, n.lineno) for k, v in _mapping_items(a, names, n, where).items()]
                out += [_Write(kw.arg, "update", kw.value, n.lineno) for kw in n.keywords]
            elif names.is_environ(n.func.value) and n.func.attr == "setdefault":
                out += [_Write(k, "setdefault", n.args[1] if len(n.args) > 1 else None, n.lineno)
                        for k in sorted(_keys(n.args[0] if n.args else None, n, where, "setdefault", names))]
            elif isinstance(n.func.value, ast.Name) and n.func.value.id in names.os_names and n.func.attr == "putenv":
                out += [_Write(k, "putenv", n.args[1] if len(n.args) > 1 else None, n.lineno)
                        for k in sorted(_keys(n.args[0] if n.args else None, n, where, "putenv", names))]
    return out


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
                and isinstance(n.args[0].value, str):
            if (names.is_environ(n.func.value) and n.func.attr == "pop") or (
                    isinstance(n.func.value, ast.Name) and n.func.value.id in names.os_names and n.func.attr == "unsetenv"):
                keys.add(n.args[0].value)
        elif isinstance(n, ast.Delete):
            for t in n.targets:
                if isinstance(t, ast.Subscript) and names.is_environ(t.value) and isinstance(t.slice, ast.Constant) \
                        and isinstance(t.slice.value, str):
                    keys.add(t.slice.value)
    return keys


_COMPOUND = tuple(getattr(ast, name) for name in ("If", "For", "AsyncFor", "While", "With", "AsyncWith", "Try", "TryStar", "Match")
                  if hasattr(ast, name))


def _module_level_compounds(body, kind):
    """The compound statements of `kind` (ast.For, say) that run at import, however nested in the module's
    if/for/while/with/try (and match) blocks; nothing inside a def or a class."""
    for s in body:
        if isinstance(s, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
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


def _module_level_statements(body):
    """The simple statements that run at import: the module's own, and those in the bodies of its if/for/while/with/try
    (and match) blocks however nested; nothing inside a def or a class, which runs when called. A write of the peers
    setting planted inside a module-level `if` body leaks exactly like a bare one (review round 1, 2026-09-18)."""
    for s in body:
        if isinstance(s, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(s, _COMPOUND):
            for attr in ("body", "orelse", "finalbody"):
                yield from _module_level_statements(getattr(s, attr, None) or [])
            for h in getattr(s, "handlers", []):
                yield from _module_level_statements(h.body)
            for c in getattr(s, "cases", []):
                yield from _module_level_statements(c.body)
        else:
            yield s


def _module_level_env_write_records(tree, where="<module>"):
    """Every environment write the module makes at import, as (_Write, nested) pairs: `nested` is True for a write
    inside a module-level if/for/while/with/try body (a bare grep at column 0 misses those), False for one directly
    in the module body. In every shape _env_write_records reads; `where` names the file in the loud message for a
    write the scan cannot read."""
    names = _EnvNames(tree)
    top = {id(s) for s in tree.body}
    out = []
    for s in _module_level_statements(tree.body):
        out += [(w, id(s) not in top) for w in _env_write_records(s, names, where)]
    return out


def _module_level_env_writes(tree, where="<module>"):
    """The environment keys the module writes at import, in every shape _env_writes reads, in any statement
    _module_level_statements yields; `where` names the file in the loud message for a write the scan cannot read."""
    return {w.key for w, _nested in _module_level_env_write_records(tree, where)}


def _tests_tree_paths():
    """Every .py under tests/, recursively (fixtures/ included), sorted; the glob is checked against an independent
    os.walk so no file is silently unscanned (review round 1, 2026-09-18)."""
    paths = sorted(glob.glob(os.path.join(HERE, "**", "*.py"), recursive=True))
    walked = sorted(os.path.join(d, f) for d, _, fs in os.walk(HERE) for f in fs if f.endswith(".py"))
    if paths != walked:
        raise AssertionError("the glob walks every .py under tests/, subdirectories included: the set an os.walk finds")
    return paths


_Record = collections.namedtuple("_Record", "module line shape value nested")
#   one module-level write in the tree: the writer MODULE (relative to tests/), its LINE, the SHAPE, the VALUE text
#   (ast.unparse of the expression, or "" where the shape has none) and whether the statement is NESTED in a block


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
        for w, nested in _module_level_env_write_records(tree, rel):
            counts[w.key][w.shape] += 1
            records[w.key].append(_Record(rel, w.line, w.shape, ast.unparse(w.value) if w.value is not None else "", nested))
    return len(paths), {k: dict(v) for k, v in counts.items()}, dict(records)


def _census_table(paths=None):
    """The census as text: the module count, then one line per (name, shape) with the write count, the writer-module
    count and how many of the writes are nested in a module-level block (the ones a column-0 grep misses)."""
    n, counts, records = module_level_env_census(paths)
    lines = ["modules: %d (.py files under tests/, recursively; fixtures/ and the helpers beside the test modules included)" % n,
             "%-34s %-11s %6s %8s %7s" % ("name", "shape", "writes", "modules", "nested")]
    for name in sorted(counts):
        for shape in sorted(counts[name]):
            recs = [r for r in records[name] if r.shape == shape]
            lines.append("%-34s %-11s %6d %8d %7d" % (name, shape, len(recs), len({r.module for r in recs}),
                                                       sum(1 for r in recs if r.nested)))
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


def _const_str(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _is_mkdtemp_call(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "mkdtemp")


class _Licence:
    def __init__(self, reason, value=None, value_ok=None, reasserted=False, since=None, until=None):
        self.reason, self.value, self.value_ok, self.reasserted, self.since, self.until = reason, value, value_ok, reasserted, since, until

    def fault(self, rec, reasserted_names):
        """Why the write `rec` (a _Record) falls outside this licence, or None when it is covered."""
        if self.reasserted and self._name not in reasserted_names:
            return "licensed only while tests/conftest.py re-asserts %s in an autouse fixture, and it no longer does" % self._name
        if self.value is not None and rec.value != repr(self.value):
            return "licensed for the value %r alone, not %s" % (self.value, rec.value or "a shape with no value")
        if self.value_ok is not None and not self.value_ok(rec):
            return "the value %s is not one this licence covers" % (rec.value or "(none)")
        return None


LICENSED_MODULE_LEVEL_WRITES = {
    "XDG_STATE_HOME": _Licence(
        "the state preamble tests/test_state_isolation_order.py mandates before a module loads bin/romp-*, which bind "
        "their state root at import: a private root under the run's temp root, removed with the run; a child that "
        "inherits it writes under that root and nowhere real. The class item may retire the mandate, and this licence "
        "goes with it", until=CLASS_ITEM_871),
    "ROMP_STATE_DIR": _Licence(
        "the other half of the same preamble (a live kernel exports it and it outranks the XDG floor): assigned to a "
        "private root, or written back to what the shell had after the load, in the four modules that do not pop it",
        until=CLASS_ITEM_871),
    "ROMP_SERVE_TOKEN": _Licence(
        "a synthetic serve token so a kernel or bus loaded in-process mints none under the module's root; setdefault in "
        "most modules, an assignment of the same kind of literal in the rest (test_postal_token.py puts the shell's "
        "value back after its load). Licensed 2026-09-22 until the class item is taken, by the reviewer's ruling: a "
        "dated licence, not current practice", since="2026-09-22", until=CLASS_ITEM_871),
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
        "conftest sets and re-asserts per test", value_ok=lambda rec: rec.value.startswith("tempfile.mkdtemp("), reasserted=True),
    "ROMP_SERVICE_ENV_FILE": _Licence(
        "a never-created path under the module's own state root, the floor's shape (no test reads the real service.env); "
        "re-asserted per test", reasserted=True),
    "ROMP_SERVICE_ENV": _Licence(
        "the second spelling of the service-env path, the same floor; re-asserted per test", reasserted=True),
    "ROMP_MODELS_URL": _Licence(
        "the kernel reads it at import (MODELS_API_URL) and the one writer, test_model_catalog.py, names a dead loopback "
        "URL, so a kernel that inherits it fetches its catalog from nothing rather than from the network",
        value_ok=lambda rec: rec.value.startswith("'http://127.0.0.1:") or rec.value.startswith('"http://127.0.0.1:')),
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
            at = "%s:%d (%s%s)" % (rec.module, rec.line, rec.shape, ", nested in a module-level block" if rec.nested else "")
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
        each faulting once; a planted update whose keys the scan cannot read is loud, naming the line, never a clean
        pass; and the restore moved back into a tearDown with no cleanup registered, which faults every leg and the
        BUS_PORT restore of both attaching classes."""
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
        reads, module-level if/try/for/with bodies included; a write whose keys the scan cannot read fails here naming
        the file and line rather than passing unread. The per-test half (set in setUp, put back by a cleanup) is a
        convention, checked above for the tunnels module alone; tests/README.md says so."""
        paths = _tests_tree_paths()
        self.assertGreater(len(paths), 900, "the scan walks the whole tree, recursively: %d files (952 on 2026-09-22)" % len(paths))
        n, counts, records = module_level_env_census(paths)
        self.assertEqual(n, len(paths))
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
        dir written with a value outside their licence; a licence whose re-assert conftest dropped; and a dead licence.
        The floor modules are never faulted, whatever they write; a licensed write is clean."""
        def records_of(src, rel):
            return {w.key: [_Record(rel, w.line, w.shape, ast.unparse(w.value) if w.value is not None else "", nested)]
                    for w, nested in _module_level_env_write_records(ast.parse(src), rel)}
        reasserted = _conftest_reasserted_names()
        full = lambda src, rel: _licence_faults({**_all_licensed_once(), **records_of(src, rel)}, reasserted)
        faults = full('import os\nos.environ["ROMP_NEW_NAME"] = "1"\n', "test_planted.py")
        self.assertEqual(len(faults), 1, faults)
        self.assertIn("ROMP_NEW_NAME is written at module level by test_planted.py:2 (assignment)", faults[0])
        self.assertIn("not in the licensed set", faults[0])
        self.assertIn("set it in setUp", faults[0])
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
                             ('DEAD = {"ROMP_KERNEL_PORT": "29855"}\nos.environ.update(DEAD)', "licensed for the value '1' alone")):
            faults = full("import os\n" + line + "\n", "test_planted.py")
            self.assertEqual(len(faults), 1, (line, faults))
            self.assertIn(expect, faults[0], line)
        for line in ('os.environ["ROMP_MANAGER_PORT"] = "1"', 'os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")',
                     'os.environ["ROMP_KERNEL_NO_OPEN"] = "1"', 'os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()',
                     'os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()', 'DEAD = {"ROMP_KERNEL_PORT": "1"}\nos.environ.update(DEAD)'):
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

    def test_the_census_counts_by_name_and_shape_and_the_table_reads_back(self):
        """module_level_env_census over a synthetic tree: one module, five shapes, two names; the nested write is counted
        as such; the table names the module count. The counts over the real tree are the by-product fork PR #871's
        docstring recorded from a grep, re-derived by ast here and pasted at the head in the PR; they are NOT pinned by
        equality, since they move with every new module (the enforced property is the licensed set's equality)."""
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        src = ("import os\nos.environ['A'] = '1'\nos.environ.setdefault('A', '2')\nos.environ.update({'B': '3'})\n"
               "os.environ |= {'B': '4'}\nos.putenv('B', '5')\nif True:\n    os.environ['A'] = '6'\n"
               "def f():\n    os.environ['C'] = 'never counted'\n")
        path = os.path.join(d, "test_planted.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        n, counts, records = module_level_env_census([path])
        self.assertEqual(n, 1)
        self.assertEqual(counts, {"A": {"assignment": 2, "setdefault": 1}, "B": {"update": 1, "|=": 1, "putenv": 1}})
        self.assertEqual([r.nested for r in records["A"]], [False, False, True])
        self.assertEqual(records["A"][2].value, "'6'")
        table = _census_table([path])
        self.assertIn("modules: 1", table)
        self.assertIn("%-34s %-11s %6d %8d %7d" % ("A", "assignment", 2, 1, 1), table)

    def test_the_scan_reads_every_write_shape_ignores_a_def_and_is_loud_on_a_key_it_cannot_read(self):
        """The scan the repo-wide pin rests on is known to see a planted write in every shape, bare and in an if body, and
        to ignore one inside a def; the one module-level update in the tree today reads its mapping through a name bound
        to a dict literal (tests/test_update_banner_confirm_served.py's DEAD_PORTS) and the scan reads the keys AND the
        values through the name; a `for` over string literals binds its name to each in turn (conftest's service-env
        fixture writes that way) and the literals are the keys; a write the scan cannot read is loud, with the file and
        the line, never a clean pass (review round 2, 2026-09-18; the loop shape 2026-09-22)."""
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
                      'for v in ("ROMP_POSTAL_PEERS", "ROMP_X"):\n    os.environ[v] = "0"'):
            self.assertIn("ROMP_POSTAL_PEERS", _module_level_env_writes(ast.parse("import os\n" + shape + "\n"), "planted.py"), shape)
        looped = _module_level_env_writes(ast.parse('import os\nfor v in ("ROMP_POSTAL_PEERS", "ROMP_X"):\n    os.environ[v] = "0"\n'), "planted.py")
        self.assertEqual(looped, {"ROMP_POSTAL_PEERS", "ROMP_X"}, "each literal the loop binds is a key")
        unseen = _module_level_env_writes(ast.parse('import os\ndef setUp(self):\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n'), "planted.py")
        self.assertNotIn("ROMP_POSTAL_PEERS", unseen)
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
                      'for v in NAMES:\n    os.environ[v] = "0"'):
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
                             ("update", 'os.environ.update(ROMP_POSTAL_PEERS="0")\n')):
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


def _all_licensed_once():
    """Synthetic records: one licensed write per licensed name, from a test module, each meeting its licence (the input
    the planted-fault test adds one offending write to, so the equality half of the check is satisfied by construction
    and the one planted fault is the whole list)."""
    sample = {"XDG_STATE_HOME": "tempfile.mkdtemp()", "ROMP_STATE_DIR": "_STATE_TD.name", "ROMP_SERVE_TOKEN": "'testtok'",
              "ROMP_KERNEL_NO_OPEN": "'1'", "ROMP_MANAGER_PORT": "'1'", "ROMP_KERNEL_PORT": "'1'", "ROMP_SERVE_PORT": "'1'",
              "ROMP_MODEL_CATALOG": "'off'", "ROMP_CLI_SCOPE": "'0'", "CLAUDE_CONFIG_DIR": "tempfile.mkdtemp()",
              "ROMP_SERVICE_ENV_FILE": "_NO_SERVICE_ENV", "ROMP_SERVICE_ENV": "_NO_SERVICE_ENV",
              "ROMP_MODELS_URL": "'http://127.0.0.1:9/v1/models'"}
    assert set(sample) == set(LICENSED_MODULE_LEVEL_WRITES), sorted(set(sample) ^ set(LICENSED_MODULE_LEVEL_WRITES))
    return {name: [_Record("test_licensed.py", 1, "assignment", value, False)] for name, value in sample.items()}


if __name__ == "__main__":
    if "--census" in sys.argv:
        print(_census_table())     # `python -m tests.test_hermetic_kernel_postal --census`: the by-product counts, by name and shape
        sys.exit(0)
    unittest.main()
