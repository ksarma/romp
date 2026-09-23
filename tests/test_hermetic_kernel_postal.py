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
here reads every process spawn (a call whose callee resolves by binding to Popen, run, check_output, check_call or
call of the subprocess module: through the name the module imports the library under, a from-import of the function
under any name, or an assignment that binds a name to either) whose argv HOLDS the kernel's path as an element, or
whose `executable=` is the path: a string, an f-string, a % or a .format template that is the path or has it as ANY
whole word (a shell command: a word bounded by whitespace or the string's edge whose text ends in the kernel's name,
or that ends in a placeholder whose value is the path), a path joined onto it (os.path.join, Path, /, either operand
of +, any element of a str.join over a literal list, the callee of the join resolved by binding as well, so `from
os.path import join`, `import os.path as osp` and `j = os.path.join` reach it), a path-preserving wrapper of one
(str, os.fspath, .resolve(), joinpath), any value of an `or` or a conditional, a walrus's value, the default of an
env-override lookup (`os.environ.get(key, KERNEL)`, `os.getenv(key, KERNEL)`), the element expression or an iterable
of a comprehension argv (its own targets never resolved), the element a subscript takes from a literal dict by key
or from a literal list or tuple by index, or a name or self.X target bound to any of those in the scope the call reads, the
name resolved to its declaration by tests/ast_bindings.py (the function the call is in, its enclosing functions,
then the module; a class body encloses no method; self.X per concrete class, the method's class and every class of
the module below it, each reading the self.X writes of its method resolution order and the class-body binding of X
nearest in that order, each class's reading decided as a name's is, a path for any class being the path and two
classes that read it differently no refusal).
The reads that key on a SPELLING, each because the binding cannot reach it: any other dotted target (`cfg.kernel`,
`Lab.KERNEL`) by the target's text, which ast_bindings.Bindings.resolve_target says; a name no scope binds (a
snippet's `subprocess`, a star import's `join`) by its own spelling; a method (.resolve(), .format(), .strip()) by
the method's name, its receiver a value and not a module; the bin directory of a CLI join (`os.path.join(BIN,
"romp")`) by the directory name's shape; and the trio by its text (_hermetic). The CLI counts only with a kernel
verb (KERNEL_VERBS: up, the verb that starts one) as the next argv element or the next word of a command string, a
splatted next element being no verb; the comment at KERNEL_VERBS says why each verb is in or out. The element's
INDEX is not read: a wrapper launch (`["timeout", "30", KERNEL]`) is a
kernel process, and so, an accepted false red, is a grep or a git over the kernel's file, the side that requires
the trio; a subscript whose slice the scan cannot read (`SCRIPTS[i]`) is read as any element of its container, the
same side. A name bound twice in the scope the call reads, once to the path and once to something else, is refused
loudly (UnreadableSpawn, naming the call's line and both declarations), never read either way; a declaration with
no readable value beside one bound to the path leaves the path standing. A string that MENTIONS the path inside a
word (a -c program that load_sources the kernel, `load_source('k', %r)`), a comment or a docstring is not a kernel
process: that is the
in-process shape in a child, met by the bus belt below like the in-process shape itself (the ruling point below).
The scan replaced a regex pair on 2026-09-21, in the author's pass applying the ruling of PR #850's eighth review
round: the old KERNEL_NAME pattern took any name bound on ONE line that spelled romp-kernel as a name bound to the
kernel's path and looked for it as a whole WORD in every subprocess call span, so a local `p` bound to TEXT that
spelled the path collided with the "-p" of a nested pytest argv (a false offender at a commit of that PR's eighth
round that was never pushed, fixed at its ruled head; the loud half), while a path bound across two lines, through
a constant holding the script's name, to a tuple target or to self.kernel never entered the pattern and a spawn
through it would have passed this rule vacuously (the silent half; a plant showed the miss, the tree had no such
spawn); at that head most of the names the pattern bound were the `km` of an in-process load, a module object and
no path (the author's pass measured it before the rewrite). PLANT_TABLE below runs both halves, every row labelled
with what the scan must do; the guard test's report carries the row count. The rewrite then read less than the regex
pair in places (a command string with the path after its first word, a placeholder template, an env-override default,
Popen's executable=, a comprehension argv, `romp up`) with every check green, since the tree held no instance of
those shapes and the table was written from what the scan read (PR #850's ninth review round). So the comparison
case runs the regex pair, copied verbatim (_round8_regex_census), beside the scan over every module the trio test
reads and every row, and reds on a call the regex flags that the scan accounts for by none of a site, a listed entry
containing the match, a refusal, or one of three exclusions derived from the call: a word collision (a word a
one-line binding named, which resolves at the call to no path; the name is read through the scan itself, so a value
bound on one line that the scan cannot read is excused there, and each shape the scan once dropped has an inline row
too), a match inside a -c program (the ruling point below; tests/test_chat_pages.py in the tree), and the CLI with a
verb outside KERNEL_VERBS, while every verb in it is one bin/romp dispatches.

Roads and residual, derived by one command (`python tests/test_hermetic_kernel_postal.py --roads [directory]`, one
line per module the trio test reads, then the unresolved names, then a summary line with every count): a module's
kernel spawn is found by the argv road (an element that is the path as written), the binding road (a name or target
resolved to a declaration bound to it), or neither, and a module the scan can read neither way is labelled refused.
The guard test holds the two lab modules on the argv road and no module refused, and reports the counts at whatever
size the tree has.
The residual, as a rule: whatever the scan does not read is no path. What it LISTS, under `# unresolved:` with its
kind: a name or target in an argv that resolves to a declaration with no readable value (a parameter, an import, a
loop or with target, an unpacking the scan cannot split) or to none at all (an attribute of an imported module,
sys.executable most of all), a call of a function defined in the module or of a name no scope binds (a helper's
return, a star import's), a passthrough's splatted argv, and a keywords splat a spawn is handed alone. What it does
not list, by class, each held by a PLANT_TABLE row: an argv mutated by append, extend or insert (N29), a spawn
function reached through functools.partial or getattr (N30), a spawn function outside the subprocess module
(os.execv, os.posix_spawn, asyncio.create_subprocess_exec; N31), and a consumer call's arguments (a builtin, a
function imported from any module, a helper of another test module included, or any method but the path-preserving
ones: `os.path.relpath(K)`, `shutil.which(K)`, `K.replace(...)`; N32). The comparison case measures the split with
the regex pair: it flags no call in the rows of the first three classes, which it missed as well; it flags a
consumer call whose arguments spell the path or name a one-line binding it read, and the comparison reds on that
call, so only a consumer call the regex misses too passes both (N32 binds its path across two lines). The regex
pair's other matches the scan does not read are the comparison's three exclusions.

Ruling point, the maintainers' to decide (2026-09-21): a child interpreter that load_sources the kernel
(`[sys.executable, "-c", <program>]`) is read here as NOT a kernel process. It is the in-process shape one process
down, and the belt below covers it exactly as it covers the parent, provided the child inherits the parent's
environment (PYTEST_CURRENT_TEST under pytest) or runs under a temporary state root. Derived on that day by reading
every `-c` program under tests/ (`grep -n '"-c"' tests/*.py`, each program read by hand), the sites whose program
loads bin/romp-kernel, directly or through a module that loads it, are: tests/test_assembly_road_counters.py:935, env
dict(os.environ) plus one key, the state root the parent's temporary floor; tests/test_kernel_serve_token_mode.py:608,
env dict(os.environ), ROMP_STATE_DIR a mkdtemp; tests/test_manager_write_token.py:402, env filtered from os.environ
(ROMP_STATE_DIR and ROMP_MANAGER_PID dropped, PYTEST_CURRENT_TEST kept), XDG_STATE_HOME the class's mkdtemp;
tests/test_perf_stats.py:2605, env dict(os.environ, TMPDIR=...), the state root the parent's floor;
tests/test_perf_stats.py:4099, env dict(os.environ), ROMP_STATE_DIR a mkdtemp; tests/test_chat_pages.py:1151, env
dict(os.environ, ...) carrying the trio, the program setting its own mkdtemp as XDG_STATE_HOME. Every one meets both
conditions. Were such a child a kernel process (the path mentioned anywhere in the argv's strings), the first four
modules would be offenders, a separate change to make hermetic; nothing here decides that. The in-process shape is
met in the bus itself: `romp-postal-service serve` and `ensure` refuse the fixed port under a test (PYTEST_CURRENT_TEST set, or the
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

The fixture rule below is static, so it holds for tests that skip here (no browser, no extension deps) and fails at
the spawn site, naming the file.
"""
import ast
import builtins
import glob
import json
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)
import ast_bindings   # noqa: E402  names resolved to their declarations by scope (tests/ast_bindings.py)

TRIO = ("ROMP_POSTAL_PORT", "ROMP_POSTAL_PEERS", "ROMP_POSTAL_CLIENT_ONLY")

# -- the spawn scan: a subprocess call whose argv holds the kernel's path, read from the module's ast with every name
# -- resolved to its binding (ast_bindings, 2026-09-21; a regex pair before) -------------------------------------------
SPAWN = ("Popen", "run", "check_output", "check_call", "call")
# the spawn functions by the canonical dotted name a callee resolves to (_SpawnScan._callee_names: its import, or the
# import an assignment such as `run = subprocess.run` follows to), plus the one bare spelling the unbound fallback reads,
# a snippet's `Popen(...)` with no import (an unbound `subprocess` is its own spelling, so `subprocess.run` resolves too)
SPAWN_FUNCTIONS = {"subprocess.%s" % s for s in SPAWN} | {"Popen"}
# a string constant that IS the kernel's path: the script by name or under a directory (an argv element, or any whole
# word of a shell command string)
KERNEL_PATH = re.compile(r"(?:^|/)romp-kernel$")
# the CLI's path: a kernel spawn only with a kernel verb as the next argv element or the next word of a command string
# (`romp up --foreground`). up is the verb that starts one: it execs romp-manager up, which starts romp-serve and
# romp-kernel with the caller's environment. refresh and update act through a manager already running, not a fresh
# environment, and --help and version start nothing (`romp --help`, tests/test_headless_verbs_help.py). A splatted
# next element is no verb. The pin test_every_kernel_verb_is_a_verb_bin_romp_dispatches holds each verb to bin/romp's
# dispatch.
CLI_PATH = re.compile(r"(?:^|/)bin/romp$")
KERNEL_VERBS = {"up"}
PLACEHOLDER = re.compile(r"^%[sr]$|^\{\}$|^\{0\}$")   # a template, or its first word, that is nothing but its argument: "%s" % KERNEL
# callables whose value is the path built from, or preserved from, their LAST positional argument, by the canonical
# dotted name the callee resolves to (_SpawnScan._callee_names: `from os.path import join`, `import os.path as osp;
# osp.join` and `j = os.path.join; j(...)` all resolve to os.path.join, `from pathlib import Path as P` to pathlib.Path)
PATH_FUNCTIONS = {"os.path.join", "posixpath.join", "ntpath.join", "os.path.realpath", "os.path.abspath", "os.path.normpath",
                  "os.path.expanduser", "os.fspath", "os.fsdecode", "str", "pathlib.Path", "pathlib.PurePath", "pathlib.PurePosixPath",
                  "pathlib.PosixPath", "shlex.quote"}
# ...and the bare spellings an UNBOUND callee is read by (a snippet's `Path(...)` with no import, a star import's `join`):
# the spelling fallback, which the module docstring states
PATH_FUNCTIONS |= {"Path", "PurePath", "PurePosixPath", "PosixPath", "join", "realpath", "abspath", "normpath", "expanduser", "fspath"}
# methods whose value is the receiver's path, preserved (joined onto, for joinpath); a method is read by its NAME, the
# receiver being a value and not a module (the module docstring states the spelling read)
PATH_METHODS = {"resolve", "absolute", "expanduser", "as_posix", "strip", "rstrip", "lstrip", "decode", "encode", "joinpath"}
BIN_NAME = re.compile(r"(?i)^(?:.*_)?bin(?:_?dir)?$")   # BIN, bin_dir, LAB_BIN: the directory the CLI is joined from
# the env-override idiom's function spelling, `os.getenv("ROMP_KERNEL", KERNEL)`, by the canonical name the callee
# resolves to (and the bare spelling of an unbound one): its default, the second argument, is a possible value; the
# method spelling, `os.environ.get(key, KERNEL)`, is read by the method's name (_call_is_kernel_path)
ENV_DEFAULT_FUNCTIONS = {"os.getenv", "getenv"}
# one %-conversion of a template: an optional mapping key, flags, width, precision, length and the conversion ("%%" is a
# literal percent sign)
PERCENT_FIELD = re.compile(r"%(?:\((?P<key>[^)]*)\))?[#0 +-]*(?P<width>\*|\d+)?(?:\.(?P<prec>\*|\d+))?[hlL]?(?P<conv>[diouxXeEfFgGcrsab%])")


class UnreadableSpawn(AssertionError):
    """A spawn whose argv the scan can read neither way: a name, or a target of the form self.X, with two declarations
    in the scope the call reads, one bound to the kernel's path and one bound to something else, so the census cannot
    say which the call runs. Raised naming the module, the call's line and both declarations, never a verdict either
    way (2026-09-21: a silent miss of a two-line binding and a loud match on a word were the regex census's failures).
    Two declarations that agree
    are read as one; a declaration with no readable value (a parameter, an import, a loop or with target, a None
    placeholder) beside one bound to the path leaves the path standing, the side that requires the trio."""


class _SpawnScan:
    """One module's spawn calls and the reading of each argv. A spawn is a call whose callee resolves by binding
    (_callee_names) to Popen, run, check_output, check_call or call of the subprocess module: through the name the
    module imports the library under, a from-import of the function under any name, or an assignment that binds a
    name to either (`run = subprocess.run`); an unbound `subprocess` or `Popen`, a snippet's, is the library by its
    spelling. Its argv (the first positional or `args=`) holds the kernel's path when an ELEMENT evaluates to it, and
    so does its `executable=` when that is the path: a string, an f-string, a % or a .format template with a whole
    word whose text ends in romp-kernel or that ends in a placeholder the path fills (_template_is_path; the tail and
    first-word reads beside it); a path joined onto it (os.path.join, Path, /, either operand of +, any element of a
    str.join over a literal list, the callee of a path-building call resolved by binding too); a path-preserving
    wrapper (str, os.fspath, .resolve(), joinpath); any value of an `or` or a conditional, a walrus's value, the
    default of `.get(key, default)` or `os.getenv(key, default)`; the element a subscript takes from a literal dict
    by key or from a literal list or tuple by index (_element); or a name or a self.X target bound to one of those,
    resolved by ast_bindings in the scope the call reads. A splat element, an argv held in a name, one built by + or
    by `or`, a walrus and a comprehension or generator (its element expression or an iterable; its own targets never
    resolved) are followed. The CLI's path counts only with a kernel verb (KERNEL_VERBS) as the next element or the
    next word of a command string. A constant that MENTIONS the path inside a word (a -c program's
    `load_source('k', %r)`, a comment) is not the path; a value derived by a consumer (open(...).read(),
    load_source(...), Popen(...), a function imported from any module) is not the path. Whatever the scan does not
    read is no path. It LISTS under `unresolved` a name or target with no readable declaration (a parameter, an
    import, a loop target, an attribute of an imported module), a call of a function defined in the module or of a
    name no scope binds (a helper's return, a star import's), the argv of a passthrough (`run(*a)`) and a keywords
    splat a spawn is handed alone; what it does not list is the module docstring's residual."""

    def __init__(self, tree, filename="<src>"):
        self.filename = filename
        self.bindings = ast_bindings.Bindings.of(tree)
        self.calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and self._is_spawn(n)]
        self.unresolved = []          # (line, text, kind) for every unread name or target met while reading an argv
        self.unresolved_nodes = []    # (line, node) beside each: the expression whose value is unread (the comparison's)
        self._unresolved_keys = set()
        self._bound_paths = 0         # resolutions that yielded the path while reading one argv (the road label)
        self._line = 0

    def _is_spawn(self, call):
        """Keyed on the callee's binding: any of the canonical names it resolves to is a spawn function (SPAWN_FUNCTIONS;
        `import subprocess32 as subprocess` beside `import subprocess` under a guard resolves to both, and either side
        being the library makes the call a spawn, as before the resolver)."""
        return bool(self._callee_names(call.func, self.bindings.scope_of(call)) & SPAWN_FUNCTIONS)

    def _callee_names(self, node, scope, seen=frozenset()):
        """The canonical dotted names a callee, or the receiver of a dotted one, may denote, resolved by binding: a Name
        resolves in the scope it is read in to its declarations, an import declaration giving what the bound name
        denotes (`from os.path import join` gives os.path.join, `import os.path as osp` gives os.path, `import os.path`
        gives os for the name os, `import subprocess as sp` gives subprocess), an assignment to a name or a dotted name
        being followed (`run = subprocess.run`, `j = os.path.join`); a name no scope binds is its own spelling (a
        builtin such as str; a snippet's or a star import's unbound library: the spelling fallback the module docstring
        states); an Attribute is its receiver's names with the attribute appended, so `osp.join` is os.path.join. A
        declaration of any other kind (a def, a parameter, a loop target, an assignment to a call's value) denotes no
        function the scan can name, so the set is EMPTY for a callee bound that way alone, and _call_is_kernel_path
        lists it under the residual; a name whose read is already under way (a cycle) adds nothing."""
        if isinstance(node, ast.Name):
            decls, where = scope.resolve(node.id)
            if not decls:
                return {node.id}
            key = (id(where), node.id)
            if key in seen:
                return set()
            names = set()
            for d in decls:
                if d.kind == "import":
                    names.add(d.origin)
                elif d.kind == "assign" and isinstance(d.value, (ast.Name, ast.Attribute)):
                    names |= self._callee_names(d.value, self.bindings.scope_of(d.value), seen | {key})
            return names
        if isinstance(node, ast.Attribute):
            return {"%s.%s" % (n, node.attr) for n in self._callee_names(node.value, scope, seen)}
        return set()

    def _callee_kind(self, node, scope):
        """The residual's label for a bare-name callee the scan reads no function for: "call of def" for a helper
        defined in the module, "call of parameter", "call of assign" (a name bound to a call's value), "call of an
        unbound name" for a name no scope binds that is no builtin (a star import's); kinds joined by + when the
        declarations differ."""
        decls, _ = scope.resolve(node.id)
        return "call of " + ("+".join(sorted({d.kind for d in decls})) if decls else "an unbound name")

    def sites(self):
        """(line, argv text, road) for every spawn whose argv holds the kernel's path, or whose `executable=` is the
        path (Popen runs that program with the argv as its arguments; the text is then `executable=...`): road "argv"
        when an element is the path with no name resolved on the way, "binding" when a name or target had to be
        resolved to a declaration bound to it. A call handed no argv and no program but a `**` splat is listed under
        `unresolved` with the splatted value's kind. Loud (UnreadableSpawn) for an argv the scan can read neither way."""
        found = []
        for call in self.calls:
            argv = _spawn_argv(call)
            program = next((kw.value for kw in call.keywords if kw.arg == "executable"), None)
            self._bound_paths, self._line = 0, call.lineno
            scope = self.bindings.scope_of(call)
            if argv is None and program is None:
                for kw in call.keywords:
                    if kw.arg is None:
                        self._note_unresolved(kw.value, "keywords splat of " + self._splat_kind(kw.value, scope))
                continue
            if argv is not None and self.holds_kernel_path(argv, scope):
                found.append((call.lineno, ast.unparse(argv), "binding" if self._bound_paths else "argv"))
                continue
            self._bound_paths = 0
            if program is not None and self.is_kernel_path(program, scope):
                found.append((call.lineno, "executable=" + ast.unparse(program), "binding" if self._bound_paths else "argv"))
        return found

    def _splat_kind(self, node, scope):
        """The residual's label for a `**` splat a spawn is handed alone: a name by its declarations' kinds ("an unbound
        name" for none), any other value by its shape."""
        if isinstance(node, ast.Name):
            decls, _ = scope.resolve(node.id)
            return "+".join(sorted({d.kind for d in decls})) if decls else "an unbound name"
        return {ast.Call: "a call's value", ast.Attribute: "an attribute", ast.Subscript: "a subscript",
                ast.Dict: "a dict literal"}.get(type(node), type(node).__name__)

    def _decide(self, readings, node, key, seen, evaluate, scope):
        """The verdict on a name or target from its declarations, `readings` one declaration list per value it can hold
        (a name one; self.X one per concrete class, ast_bindings.Bindings.resolve_target), each decided on its own: each
        declaration with a value is read in the scope its value is read in; one with none (a parameter, an import, a
        loop, with or except target, an unpacking the scan cannot split, a del) or bound to None says nothing. Path and
        not-path together inside one reading: loud. A path in any reading: the path (and the binding road), so two
        classes reading self.X differently are no refusal. A reading in which nothing says anything, while none holds
        the path: no path, listed as unresolved."""
        verdicts, path, silent = {}, False, []
        for decls in readings:
            said = []
            for d in decls:
                if d.value is None or (isinstance(d.value, ast.Constant) and d.value.value is None):
                    continue
                if id(d) not in verdicts:
                    verdicts[id(d)] = evaluate(d.value, self.bindings.scope_of(d.value), seen | {key})
                said.append((d, verdicts[id(d)]))
            paths = [d for d, v in said if v]
            others = [d for d, v in said if not v]
            if paths and others:
                raise UnreadableSpawn("%s line %d: %s is bound twice in the scope the call reads, once to the kernel's path (line %d: "
                                      "%s) and once to something else (line %d: %s), so the census cannot say which the call runs: "
                                      "bind it once, or under two names" % (self.filename, self._line, ast.unparse(node), paths[0].lineno,
                                                                            ast.unparse(paths[0].node), others[0].lineno,
                                                                            ast.unparse(others[0].node)))
            path = path or bool(paths)
            if not said:
                silent.append(decls)
        if path:
            self._bound_paths += 1
            return True
        if silent:
            kinds = {d.kind for decls in silent for d in decls}
            self._note_unresolved(node, "+".join(sorted(kinds)) if kinds else self._receiver_kind(node, scope))
        return False

    def _note_unresolved(self, node, kind, value=None):
        """List `node` under the residual as (line, text, kind); `value` is the expression whose value is unread when it
        is not `node` itself (the call of a helper listed by its callee's name)."""
        key = (self._line, ast.unparse(node))
        if key not in self._unresolved_keys:
            self._unresolved_keys.add(key)
            self.unresolved.append((self._line, ast.unparse(node), kind))
        self.unresolved_nodes.append((self._line, node if value is None else value))

    def _receiver_kind(self, node, scope):
        """The label of a name or target the scan reads no value for: a bare name with no declaration is "unbound"; an
        attribute is "attribute of" its receiver, a name by the kinds of its declarations (an import, a parameter, a
        with target) or "the instance" when the receiver is a method's own and no method of the class writes the
        attribute, else the receiver's shape (a call's value, an attribute, a subscript)."""
        if isinstance(node, ast.Name):
            return "unbound"
        if scope is not None and self.bindings.instance_class(node, scope) is not None:
            return "attribute of the instance, written by no method of its class"
        receiver = node.value
        if isinstance(receiver, ast.Name):
            decls, _ = scope.resolve(receiver.id) if scope is not None else ([], None)
            return "attribute of " + ("+".join(sorted({d.kind for d in decls})) if decls else "an unbound name")
        return "attribute of " + {ast.Call: "a call's value", ast.Attribute: "an attribute", ast.Subscript: "a subscript",
                                  ast.Constant: "a constant"}.get(type(receiver), type(receiver).__name__)

    def _resolve(self, node, scope, seen, evaluate):
        """A Name or a dotted target, read through its declarations; False (and a `seen` key, against a cycle) when the
        same name is already being read."""
        if isinstance(node, ast.Name):
            decls, where = scope.resolve(node.id)
            key = (id(where), node.id)
            return key not in seen and self._decide([decls], node, key, seen, evaluate, scope)
        readings, road = scope.resolve_target(node)
        key = ("target", ast.unparse(node), id(self.bindings.instance_class(node, scope)) if road == "instance" else 0)
        if key in seen:
            return False
        if not any(readings):
            if isinstance(node, ast.Attribute):   # a subscript with no binding is read through its container instead
                self._note_unresolved(node, self._receiver_kind(node, scope))
            return False
        return self._decide(readings, node, key, seen, evaluate, scope)

    def is_kernel_path(self, node, scope, seen=frozenset(), cli=False):
        """Does `node`, read in `scope`, evaluate to the kernel script's path (with `cli`, to the CLI's)? A string, an
        f-string, a % template or a .format template is read at every whole word (_template_is_path), beside the
        tail and first-word reads below."""
        pattern = CLI_PATH if cli else KERNEL_PATH
        pieces = _template_pieces(node)
        if pieces is not None and self._template_is_path(pieces, scope, seen, cli):
            return True
        if isinstance(node, ast.Constant):
            return isinstance(node.value, str) and _text_is_path(node.value, pattern)
        read = lambda v, s, seen: self.is_kernel_path(v, s, seen, cli)   # noqa: E731  the same question of a bound value
        if isinstance(node, ast.Name):
            return self._resolve(node, scope, seen, read)
        if isinstance(node, ast.Attribute):   # km.X is not km: read through the target's own binding
            return self._resolve(node, scope, seen, read)
        if isinstance(node, ast.Subscript):   # PATHS["kernel"], SCRIPTS[1]: the target's own binding, else the element taken
            return self._resolve(node, scope, seen, read) or self._element(node, scope, seen | {("container", id(node))}, read)
        if isinstance(node, ast.Starred):
            return self.holds_kernel_path(node.value, scope, seen)
        if isinstance(node, ast.JoinedStr):   # f"{BIN}/romp-kernel", f"{KERNEL}": the tail
            last = node.values[-1] if node.values else None
            if isinstance(last, ast.FormattedValue):
                return self.is_kernel_path(last.value, scope, seen, cli)
            return last is not None and self.is_kernel_path(last, scope, seen, cli)
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Mod):   # "%s/romp-kernel --serve" % BIN, "%s --serve" % KERNEL: the template's text or
                if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):   # its first word decides
                    if _text_is_path(node.left.value, pattern):
                        return True
                    if _head_is_placeholder(node.left.value):   # the argument is the program: the tuple's first, or the value
                        first = node.right.elts[0] if isinstance(node.right, ast.Tuple) and node.right.elts else node.right
                        return self.is_kernel_path(first, scope, seen, cli)
                return False
            if isinstance(node.op, ast.Add):   # BIN + "/romp-kernel", KERNEL + " --serve": either operand
                return self.is_kernel_path(node.right, scope, seen, cli) or self.is_kernel_path(node.left, scope, seen, cli)
            return self.is_kernel_path(node.right, scope, seen, cli)   # BIN / "romp-kernel": the tail
        if isinstance(node, ast.IfExp):
            return self.is_kernel_path(node.body, scope, seen, cli) or self.is_kernel_path(node.orelse, scope, seen, cli)
        if isinstance(node, ast.BoolOp):   # os.environ.get("ROMP_KERNEL") or KERNEL: any of its values
            return any(self.is_kernel_path(v, scope, seen, cli) for v in node.values)
        if isinstance(node, ast.NamedExpr):   # (k := KERNEL) used as a value: its value
            return self.is_kernel_path(node.value, scope, seen, cli)
        if isinstance(node, ast.Call):
            return self._call_is_kernel_path(node, scope, seen, cli)
        return False

    def _template_is_path(self, pieces, scope, seen, cli):
        """A template's words (_template_words) hold the path: a word whose text ends in the path's pattern (a
        placeholder standing for any directory), or a word that ends in a placeholder whose value is the path; without
        `cli`, also the CLI's path as a word with a kernel verb as the next word (`bin/romp up --foreground`)."""
        words = _template_words(pieces)
        for i, word in enumerate(words):
            if self._word_is_path(word, scope, seen, cli):
                return True
            if (not cli and i + 1 < len(words) and all(isinstance(p, str) for p in words[i + 1])
                    and "".join(words[i + 1]) in KERNEL_VERBS and self._word_is_path(word, scope, seen, True)):
                return True
        return False

    def _word_is_path(self, word, scope, seen, cli):
        if (CLI_PATH if cli else KERNEL_PATH).search("".join(p if isinstance(p, str) else "/" for p in word)):
            return True
        if isinstance(word[-1], str):
            return False
        values, every = word[-1]
        return any(self.is_kernel_path(v, scope, seen, cli) or (every and self.holds_kernel_path(v, scope, seen)) for v in values)

    def _call_is_kernel_path(self, call, scope, seen, cli):
        """A call's value is the path when its callee resolves by binding to a path-building function (PATH_FUNCTIONS)
        whose last positional argument is the path, or is a path-preserving method (by the method's NAME) on the path,
        or a template's .format. A bare-name callee the scan reads no function for (a helper defined in the module, a
        parameter, a name bound to a call's value, an unbound name that is no builtin) is listed under the residual
        with its kind; a builtin or an imported function other than the path builders is a consumer, and is not."""
        f = call.func
        names = self._callee_names(f, scope)
        if names & PATH_FUNCTIONS:
            if not call.args:
                return False
            if self.is_kernel_path(call.args[-1], scope, seen, cli):
                return True
            last = call.args[-1]   # the CLI joined from the bin directory: os.path.join(BIN, "romp"), Path(BIN, "romp")
            return (cli and len(call.args) > 1 and isinstance(last, ast.Constant) and last.value == "romp"
                    and any(self._is_bin_dir(a) for a in call.args[:-1]))
        if names & ENV_DEFAULT_FUNCTIONS:   # os.getenv("ROMP_KERNEL", KERNEL): the default is a possible value
            default = call.args[1] if len(call.args) > 1 else next((k.value for k in call.keywords if k.arg == "default"), None)
            return default is not None and self.is_kernel_path(default, scope, seen, cli)
        if isinstance(f, ast.Attribute):   # a method on a value: template.format(...), path.resolve(), base.joinpath(...)
            pattern = CLI_PATH if cli else KERNEL_PATH
            if f.attr == "get":   # os.environ.get("ROMP_KERNEL", KERNEL), the env-override idiom: the default is a possible value
                default = call.args[1] if len(call.args) > 1 else next((k.value for k in call.keywords if k.arg == "default"), None)
                return default is not None and self.is_kernel_path(default, scope, seen, cli)
            if f.attr == "join" and len(call.args) == 1 and isinstance(call.args[0], (ast.List, ast.Tuple)):
                return any(self.holds_kernel_path(e.value, scope, seen) if isinstance(e, ast.Starred)   # " ".join([...]): any element
                           else self.is_kernel_path(e, scope, seen, cli) for e in call.args[0].elts)
            if f.attr == "format":
                return isinstance(f.value, ast.Constant) and isinstance(f.value.value, str) and (
                    _text_is_path(f.value.value, pattern)
                    or (_head_is_placeholder(f.value.value) and bool(call.args) and self.is_kernel_path(call.args[0], scope, seen, cli)))
            if f.attr == "joinpath":
                return bool(call.args) and self.is_kernel_path(call.args[-1], scope, seen, cli)
            if f.attr in PATH_METHODS:
                return self.is_kernel_path(f.value, scope, seen, cli)
            return False   # a consumer's method (open(...).read(), a helper's): its value is not the path
        if isinstance(f, ast.Name):
            declared = bool(scope.resolve(f.id)[0])
            if (not names) if declared else (f.id not in vars(builtins)):
                self._note_unresolved(f, self._callee_kind(f, scope), call)   # a def, a parameter, a name bound to a call's value; a star import's name
        return False   # a builtin (open, repr, list) or an imported function (load_source, a helper of another module): a consumer

    @staticmethod
    def _is_bin_dir(node):
        if isinstance(node, ast.Name):
            return bool(BIN_NAME.match(node.id))
        return isinstance(node, ast.Constant) and isinstance(node.value, str) and (node.value == "bin" or node.value.endswith("/bin"))

    def holds_kernel_path(self, node, scope, seen=frozenset()):
        """Does `node`, an argv expression (or a container a subscript reads), hold the kernel's path as an element, or
        as the whole (a command string, a path handed as the program)? An argv that is a splat (`run(*a)`) is read
        through what is splatted, so a passthrough's parameter is listed under the residual."""
        if isinstance(node, (ast.Name, ast.Attribute)):
            return self._resolve(node, scope, seen, self.holds_kernel_path)
        if isinstance(node, ast.Subscript):   # CMDS["kernel"]: the target's own binding, else the element taken from the container
            return (self._resolve(node, scope, seen, self.holds_kernel_path)
                    or self._element(node, scope, seen | {("container", id(node))}, self.holds_kernel_path))
        if isinstance(node, ast.Starred):
            return self.holds_kernel_path(node.value, scope, seen)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            elts = node.elts
            for i, e in enumerate(elts):
                if isinstance(e, ast.Starred):
                    if self.holds_kernel_path(e.value, scope, seen):
                        return True
                elif self.is_kernel_path(e, scope, seen):
                    return True
                elif (self.is_kernel_path(e, scope, seen, cli=True) and i + 1 < len(elts)
                      and isinstance(elts[i + 1], ast.Constant) and elts[i + 1].value in KERNEL_VERBS):
                    return True   # `romp kernel ...`: the CLI with the kernel verb next
            return False
        if isinstance(node, ast.Dict):
            return any(v is not None and self.is_kernel_path(v, scope, seen) for v in node.values)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return self.holds_kernel_path(node.left, scope, seen) or self.holds_kernel_path(node.right, scope, seen)
        if isinstance(node, ast.IfExp):
            return self.holds_kernel_path(node.body, scope, seen) or self.holds_kernel_path(node.orelse, scope, seen)
        if isinstance(node, ast.BoolOp):   # CMD or [KERNEL]: any of its values
            return any(self.holds_kernel_path(v, scope, seen) for v in node.values)
        if isinstance(node, ast.NamedExpr):   # (cmd := [...]): its value
            return self.holds_kernel_path(node.value, scope, seen)
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            # [str(p) for p in (KERNEL, "--serve")]: the element expression read as an element, each iterable as a container;
            # the comprehension's own targets are never resolved (their keys enter `seen`, so a read of one says nothing)
            own = {(id(self.bindings.scopes[id(node)]), name) for name in self.bindings.scopes[id(node)].names}
            return (self.is_kernel_path(node.elt, self.bindings.scope_of(node.elt), seen | own)
                    or any(self.holds_kernel_path(g.iter, self.bindings.scope_of(g.iter), seen | own) for g in node.generators))
        if isinstance(node, (ast.Constant, ast.JoinedStr)) or (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod)):
            return self.is_kernel_path(node, scope, seen)   # the program as a string, or a command string (shell=True)
        if isinstance(node, ast.Call):   # the path itself; list(cmd), tuple(cmd), shlex.split(s), a helper handed the argv
            return self.is_kernel_path(node, scope, seen) or any(
                self.holds_kernel_path(a, scope, seen) or self.is_kernel_path(a, scope, seen) for a in _call_args(node))
        return False

    def _element(self, node, scope, seen, read):
        """`read` (is_kernel_path or holds_kernel_path) over the element a Subscript takes from its container, the
        container read through its binding (_resolve, so a container bound to the path and to something else is
        refused like a name): a str constant slice picks a literal dict's value by key, an int constant slice (negative
        too) a literal list's or tuple's element by index, and a key or an index the literal has not is no path. A slice
        the scan cannot read (a name, a range) or a container that is no literal list, tuple or dict falls back to
        EVERY element read as if taken (_any_element), the over-approximating side, which the module docstring states
        as an accepted false red."""
        index = _constant_slice(node.slice)

        def evaluate(container, s, seen):
            if isinstance(container, ast.Dict) and isinstance(index, str) and all(isinstance(k, ast.Constant) for k in container.keys):
                return any(k.value == index and read(v, s, seen) for k, v in zip(container.keys, container.values))
            if isinstance(container, (ast.List, ast.Tuple)) and isinstance(index, int) and not any(isinstance(e, ast.Starred) for e in container.elts):
                return -len(container.elts) <= index < len(container.elts) and read(container.elts[index], s, seen)
            return self._any_element(container, s, seen, read)

        container = node.value
        if isinstance(container, (ast.Name, ast.Attribute, ast.Subscript)):
            return self._resolve(container, scope, seen, evaluate)
        return evaluate(container, scope, seen)

    def _any_element(self, container, scope, seen, read):
        """`read` over every element of a literal container (a dict's values), true when any is; a container of another
        shape is read whole."""
        if isinstance(container, (ast.List, ast.Tuple, ast.Set)):
            return any(read(e.value if isinstance(e, ast.Starred) else e, scope, seen) for e in container.elts)
        if isinstance(container, ast.Dict):
            return any(v is not None and read(v, scope, seen) for v in container.values)
        return read(container, scope, seen)


def _constant_slice(node):
    """A subscript's slice as the key or index it reads: a str, an int (a negative one written as -1 too); None for a
    slice the scan cannot read (a name, a range, a bool)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int)) and not isinstance(node.value, bool):
        return node.value
    if (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, int) and not isinstance(node.operand.value, bool)):
        return -node.operand.value
    return None


def _text_is_path(text, pattern):
    """A string constant, or a template's text, IS the path when `pattern` matches it whole or matches its first word
    (a shell command string's program: "bin/romp-kernel --serve", "%s/romp-kernel --serve")."""
    words = text.split()
    return bool(pattern.search(text) or (words and pattern.search(words[0])))


def _template_pieces(node):
    """A string template as a list of pieces, each a str (the template's own text) or a placeholder, (the argument
    nodes that may fill it, whether they are every argument); None for a node that is no template. A str constant is
    its text; an f-string its constant parts and, for each `{...}`, the formatted expression; `"..." % args` and
    `"...".format(...)` their text with each placeholder's argument: by position or by key where the placeholder names
    one the arguments have, else (a %-mapping over no dict literal, a splat, a `*` width, a count that does not match,
    a field with an attribute or an index) every argument, each read as a value or as a container of one (a mapping
    or a tuple held in a name), the over-approximating side."""
    if isinstance(node, ast.Constant):
        return [node.value] if isinstance(node.value, str) else None
    if isinstance(node, ast.JoinedStr):
        return [v.value if isinstance(v, ast.Constant) else ([v.value], False) for v in node.values
                if isinstance(v, (ast.Constant, ast.FormattedValue))]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        if not (isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)):
            return None
        text, right = node.left.value, node.right
        every = ([e.value if isinstance(e, ast.Starred) else e for e in right.elts] if isinstance(right, ast.Tuple)
                 else [v for v in right.values if v is not None] if isinstance(right, ast.Dict) else [right])
        fields = list(PERCENT_FIELD.finditer(text))
        slots = [m for m in fields if m.group("conv") != "%"]
        keyed = isinstance(right, ast.Dict) and all(isinstance(k, ast.Constant) for k in right.keys)
        positional = (isinstance(right, ast.Tuple) and not any(isinstance(e, ast.Starred) for e in right.elts)
                      and len(right.elts) == len(slots)) or (not isinstance(right, (ast.Tuple, ast.Dict)) and len(slots) == 1)
        pieces, at, i = [], 0, 0
        for m in fields:
            pieces.append(text[at:m.start()])
            at = m.end()
            if m.group("conv") == "%":
                pieces.append("%")
                continue
            if "*" in (m.group("width") or "") + (m.group("prec") or ""):
                pieces.append((every, True))
            elif m.group("key") is not None:
                pieces.append(([v for k, v in zip(right.keys, right.values) if k.value == m.group("key")], False) if keyed else (every, True))
            else:
                pieces.append(([right.elts[i] if isinstance(right, ast.Tuple) else right], False) if positional else (every, True))
            i += 1
        pieces.append(text[at:])
        return pieces
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format"
            and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str)):
        try:
            parsed = list(string.Formatter().parse(node.func.value.value))
        except ValueError:
            return None
        args = [a for a in node.args if not isinstance(a, ast.Starred)]
        every = [a.value if isinstance(a, ast.Starred) else a for a in node.args] + [k.value for k in node.keywords]
        splat = len(args) != len(node.args) or any(k.arg is None for k in node.keywords)
        pieces, auto = [], 0
        for literal, field, _, _ in parsed:
            pieces.append(literal)
            if field is None:
                continue
            head = re.match(r"[^.\[]*", field).group(0)
            if head == "":
                index, auto = auto, auto + 1
            else:
                index = int(head) if head.isdigit() else head
            if splat or head != field:
                pieces.append((every, True))
            elif isinstance(index, int):
                pieces.append((args[index:index + 1], False))
            else:
                pieces.append(([k.value for k in node.keywords if k.arg == index], False))
        return pieces
    return None


def _template_words(pieces):
    """The whole words of a template's pieces (_template_pieces): maximal runs bounded by whitespace in its text or by
    its edges, the neighbouring constant fragments concatenated, a placeholder joining the word it sits in. Each word is
    a list of str fragments and placeholders."""
    words, word = [], []
    for piece in pieces:
        if not isinstance(piece, str):
            word.append(piece)
            continue
        for chunk in re.split(r"(\s+)", piece):
            if chunk and chunk.isspace():
                if word:
                    words.append(word)
                word = []
            elif chunk:
                word.append(chunk)
    if word:
        words.append(word)
    return words


def _head_is_placeholder(text):
    """A template that is nothing but its argument, whole ("%s" % KERNEL) or in its first word ("%s --serve" % KERNEL,
    "{} --serve".format(KERNEL)): the argument is then the program, and is read for the path."""
    words = text.split()
    return bool(PLACEHOLDER.match(text) or (words and PLACEHOLDER.match(words[0])))


def _call_args(call):
    for a in call.args:
        yield a.value if isinstance(a, ast.Starred) else a
    for kw in call.keywords:
        yield kw.value


def _spawn_argv(call):
    if call.args:
        return call.args[0]
    for kw in call.keywords:
        if kw.arg == "args":
            return kw.value
    return None


def _kernel_spawn_sites(src, filename="<src>"):
    """(line, argv text, road) of every subprocess call in `src` whose argv holds the kernel's path (_SpawnScan.sites)."""
    return _SpawnScan(ast.parse(src, filename=filename), filename).sites()


def _spawns_kernel(src, filename="<src>"):
    return bool(_kernel_spawn_sites(src, filename))


def _hermetic(src):
    return "kernel_env(" in src or all(k in src for k in TRIO)


def _census_modules(directory, skip=()):
    """The (name, source) of the test modules a census reads: the .py files of `directory` by name, `skip` left out."""
    for name in sorted(os.listdir(directory)):
        if name.endswith(".py") and name not in skip:
            with open(os.path.join(directory, name), encoding="utf-8", errors="replace") as f:
                yield name, f.read()


def _kernel_spawn_offenders(directory, skip=()):
    """The test modules in `directory` that start a kernel process without the postal trio: (file name, line, argv text)
    for every such spawn. Loud (UnreadableSpawn, naming the module) for a module whose argv the scan can read neither
    way; never a silent verdict on it."""
    offenders = []
    for name, src in _census_modules(directory, skip):
        sites = _kernel_spawn_sites(src, name)
        if sites and not _hermetic(src):
            offenders.extend((name, line, argv) for line, argv, _ in sites)
    return offenders


def spawn_roads(directory, skip=()):
    """Per module of `directory`: (road, sites, unresolved). The road is "neither" for a module with no kernel spawn,
    "binding" when any of its spawn sites needed a name or target resolved to a declaration bound to the path, else
    "argv" (every site an element that is the path as written). `sites` is _SpawnScan.sites; `unresolved` the names,
    targets and calls met in ANY subprocess argv of the module that the scan reads no value or no function for, (line,
    text, kind). A module
    the scan can read neither way is reported with the road "refused" and the message as its one site."""
    roads = {}
    for name, src in _census_modules(directory, skip):
        scan = _SpawnScan(ast.parse(src, filename=name), name)
        try:
            sites = scan.sites()
        except UnreadableSpawn as e:
            roads[name] = ("refused", [(0, str(e), "refused")], scan.unresolved)
            continue
        road = "neither" if not sites else "binding" if any(r == "binding" for _, _, r in sites) else "argv"
        roads[name] = (road, sites, scan.unresolved)
    return roads


def _print_roads(directory, skip=()):
    """The --roads arm: one line per module (`<module> <road> [<line>:<road>:<argv> ...]`), the unresolved names,
    targets and calls under `# unresolved:`, and a summary line with every count, so the census's population is derived
    by one command rather than stated."""
    roads = spawn_roads(directory, skip)
    for name, (road, sites, _) in roads.items():
        print("%s %s%s" % (name, road, "".join(" %d:%s:%s" % (line, r, argv.replace("\n", " ")) for line, argv, r in sites)))
    print("# unresolved: names, targets and calls met in a subprocess argv that the scan reads no value or no function for (line, text, kind)")
    kinds, calls, modules = {}, set(), set()
    for name, (_, _, unresolved) in roads.items():
        for line, text, kind in unresolved:
            print("%s:%d %s (%s)" % (name, line, text, kind))
            kinds[kind] = kinds.get(kind, 0) + 1
            calls.add((name, line))
            modules.add(name)
    count = {r: sum(1 for road, _, _ in roads.values() if road == r) for r in ("argv", "binding", "neither", "refused")}
    sites = [(r, name) for name, (_, s, _) in roads.items() for _, _, r in s]
    offenders = [(name, line, argv) for name, (road, s, _) in roads.items() if road in ("argv", "binding") and
                 not _hermetic(open(os.path.join(directory, name), encoding="utf-8", errors="replace").read()) for line, argv, _ in s]
    print("# summary: modules %d; argv %d; binding %d; neither %d; refused %d; spawn sites %d (argv %d, binding %d); offenders %d; "
          "unresolved names %d in %d calls of %d modules by kind %s; sys.executable %d of them"
          % (len(roads), count["argv"], count["binding"], count["neither"], count["refused"], len(sites),
             sum(1 for r, _ in sites if r == "argv"), sum(1 for r, _ in sites if r == "binding"), len(offenders),
             sum(kinds.values()), len(calls), len(modules), dict(sorted(kinds.items())),
             sum(1 for _, (_, _, u) in roads.items() for _, text, _ in u if text == "sys.executable")))


def _round8_regex_census(src):
    """The census the spawn scan replaced, run beside it by the old-versus-new comparison and by nothing else
    (test_the_scan_covers_every_call_the_regex_census_it_replaced_flagged). The five definitions below are copied
    verbatim from this module as it stood at the head of PR #850's eighth review round, the last head to run them as
    the census. Returns, for each call span _spawns_kernel reads that matches, (offset of the call's opening
    parenthesis, [(offset, matched text, name)]): every KERNEL_ARGV match with name None and every match of a name
    KERNEL_NAME bound, with that name. Loud if that per-call reading disagrees with the verbatim verdict."""
    # -- verbatim: the round-8 regex census ---------------------------------------------------------------------------
    CALL = re.compile(r"(?:subprocess\.(?:Popen|run|check_output|check_call|call)|(?<![\w.])Popen)\s*\(")
    # the kernel's path as an argv spells it: the script's name, the bare CLI (not the other bin/romp-* scripts), a path
    # joined from BIN with "romp"
    KERNEL_ARGV = re.compile(r"""romp-kernel|bin/romp(?![\w-])|\bBIN\b[^\]\n]*?["']romp["']""")
    KERNEL_NAME = re.compile(r"^[ \t]*([A-Za-z_]\w*)\s*=\s*[^\n]*romp-kernel", re.M)   # a name bound to the kernel's path

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
    # -- end of the verbatim copy ---------------------------------------------------------------------------------------
    hits = []
    for m, span in zip(CALL.finditer(src), _call_spans(src)):
        found = [(m.end() + x.start(), x.group(0), None) for x in KERNEL_ARGV.finditer(span)]
        found += [(m.end() + x.start(), x.group(0), n) for n in KERNEL_NAME.findall(src)
                  for x in re.finditer(r"\b%s\b" % re.escape(n), span)]
        if found:
            hits.append((m.end() - 1, sorted(found, key=lambda f: f[0])))
    if bool(hits) != _spawns_kernel(src):
        raise AssertionError("the per-call reading of the round-8 census disagrees with its verbatim verdict")
    return hits


def _source_offsets(src):
    """(line, UTF-8 byte column) of an ast position to an offset into `src` (ast counts columns in bytes)."""
    lines = src.split("\n")
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line) + 1)

    def at(lineno, col):
        if lineno > len(lines):
            return len(src)
        return starts[lineno - 1] + len(lines[lineno - 1].encode("utf-8")[:col].decode("utf-8", errors="ignore"))
    return at


def _bin_romp_verbs(text):
    """The verbs bin/romp's top level dispatches, read from its text: every literal pattern (no glob character, so
    not the catch-all arms that refuse an unknown word) of an arm of a column-0 `case "${1:-}" in` block up to its
    column-0 `esac`, and every string a column-0 `if` or `elif` compares "${1:-}" to with ==; beside them the
    patterns such a line matches "${1:-}" against with =~ (a verb is dispatched when one of them finds it)."""
    verbs, patterns, inside = set(), [], False
    for line in text.splitlines():
        if re.match(r'case "\$\{1:-\}" in\b', line):
            inside = True
        elif inside and re.match(r"esac\b", line):
            inside = False
        elif inside:
            arm = re.match(r"    ([^\s()#][^()]*)\)", line)
            if arm:
                verbs |= {p for p in arm.group(1).split("|") if not set(p) & set("*?[")}
        elif re.match(r"(?:el)?if \[\[ ", line):
            verbs |= set(re.findall(r'"\$\{1:-\}" == "([^"]*)"', line))
            patterns += re.findall(r'"\$\{1:-\}" =~ (\S+) \]\]', line)
    return verbs, patterns


def _verbs_bin_romp_lacks(verbs, text):
    """The members of `verbs` bin/romp's top-level dispatch (_bin_romp_verbs over `text`) does not dispatch, sorted."""
    dispatched, patterns = _bin_romp_verbs(text)
    return sorted(v for v in verbs if v not in dispatched and not any(re.search(p, v) for p in patterns))


def _bin_romp_text():
    with open(os.path.join(os.path.dirname(HERE), "bin", "romp"), encoding="utf-8", errors="replace") as f:
        return f.read()


def _regex_scan_comparison(src, name, verbs_hold=True, scan_all=False):
    """Every call the round-8 regex census (_round8_regex_census) flags in `src`, held against the spawn scan over the
    same source. Returns (dropped, regex_missed, not_calls, flagged): `dropped` the (line, matched text, call text) of every
    match the scan accounts for in none of these ways: a site at the call's line (the module then owes the trio); an
    entry listed under `unresolved` whose expression contains the match (a listing requires no trio, so an unrelated
    one at the same call, sys.executable most often, explains nothing); the module refused (UnreadableSpawn, loud); or
    one of three exclusions, each derived from the call: (a) a match of a word a one-line binding named, where no name
    or attribute of that spelling in the call resolves to the path (the word collisions); (b) a match inside the
    program element after a "-c" (the ruling point below); (c) the CLI followed by a verb outside KERNEL_VERBS, a
    string constant as the next argv element or the next word of a command string, and only while every verb in
    KERNEL_VERBS is one bin/romp dispatches (`verbs_hold`: an exclusion keyed on a list that names a verb the CLI has
    not excuses nothing). `regex_missed` the lines of the sites the regex census did not flag, reported and asserting
    nothing; `not_calls` the lines of regex matches at no call of the module's ast (a comment, a docstring, a string
    holding a snippet); `flagged` the number of calls of the ast the regex flags. A source the regex flags nowhere is
    not scanned unless `scan_all`, so its `regex_missed` is empty."""
    hits = _round8_regex_census(src)
    if not hits and not scan_all:
        return [], [], [], 0
    tree = ast.parse(src, filename=name)
    scan = _SpawnScan(tree, name)
    try:
        sites, refused = scan.sites(), False
    except UnreadableSpawn:
        sites, refused = [], True
    listed = list(scan.unresolved_nodes)
    at = _source_offsets(src)

    def extent(node):
        return at(node.lineno, node.col_offset), at(node.end_lineno, node.end_col_offset)

    calls = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            paren = at(node.func.end_lineno, node.func.end_col_offset)
            while paren < len(src) and src[paren].isspace():   # loop-ok: bounded by the source's length
                paren += 1
            calls[paren] = node
    site_lines = {line for line, _, _ in sites}
    flagged, dropped, not_calls = set(), [], []   # flagged: the lines of the calls the regex flags
    for paren, matches in hits:
        call = calls.get(paren)
        if call is None:
            not_calls.append(src[:paren].count("\n") + 1)
            continue
        flagged.add(call.lineno)
        if refused or call.lineno in site_lines:
            continue
        for offset, text, word in matches:
            if any(start <= offset < end for line, node in listed if line == call.lineno for start, end in [extent(node)]):
                continue
            if not _regex_match_excluded(scan, call, offset, text, word, extent, verbs_hold):
                dropped.append((call.lineno, text, ast.unparse(call)))
    return dropped, sorted(site_lines - flagged), not_calls, len(hits) - len(not_calls)


def _regex_match_excluded(scan, call, offset, text, word, extent, verbs_hold):
    """Is one regex match in `call` one of the comparison's three exclusions (_regex_scan_comparison)?"""
    scan._line = call.lineno
    if word is not None:   # (a): every name or attribute of the word's spelling in the call resolves to no path, each read
        parent = {id(c): n for n in ast.walk(call) for c in ast.iter_child_nodes(n)}   # with the subscripts taken from it
        spelled = []
        for n in ast.walk(call):
            if (isinstance(n, ast.Name) and n.id == word) or (isinstance(n, ast.Attribute) and n.attr == word):
                while isinstance(parent.get(id(n)), ast.Subscript) and parent[id(n)].value is n:   # loop-ok: climbs the call's tree
                    n = parent[id(n)]
                spelled.append(n)
        try:
            if not any(scan.is_kernel_path(n, scan.bindings.scope_of(n)) or scan.holds_kernel_path(n, scan.bindings.scope_of(n))
                       for n in spelled):
                return True
        except UnreadableSpawn:
            pass
    argv = _spawn_argv(call)
    lists = [n for n in ast.walk(argv) if isinstance(n, (ast.List, ast.Tuple))] if argv is not None else []
    for elts in (n.elts for n in lists):   # (b): inside the element after "-c"
        for i, e in enumerate(elts[:-1]):
            if isinstance(e, ast.Constant) and e.value == "-c":
                start, end = extent(elts[i + 1])
                if start <= offset < end:
                    return True
    if word is None and verbs_hold and "romp-kernel" not in text:   # (c): the CLI with another verb
        for elts in (n.elts for n in lists):
            for i, e in enumerate(elts[:-1]):
                start, end = extent(e)
                nxt = elts[i + 1]
                if (start <= offset < end and isinstance(nxt, ast.Constant) and isinstance(nxt.value, str)
                        and nxt.value not in KERNEL_VERBS and scan.is_kernel_path(e, scan.bindings.scope_of(e), cli=True)):
                    return True
        for c in (n for n in ast.walk(argv) if isinstance(n, ast.Constant) and isinstance(n.value, str)) if argv is not None else ():
            start, end = extent(c)
            words = c.value.split()
            cli = [i for i, w in enumerate(words) if CLI_PATH.search(w)]
            if start <= offset < end and cli and all(i + 1 < len(words) and words[i + 1] not in KERNEL_VERBS for i in cli):
                return True
    return False


class UnreadableEnvWrite(AssertionError):
    """A write to the process environment whose keys the scan cannot read from the source: an update of a computed
    mapping or of `**kw`, a key that is not a string literal. Raised rather than skipped (review round 2, 2026-09-18): a
    write the scan passed over would hold the repo-wide import-time rule vacuously for that module."""


def _literal_mapping_keys(node):
    """The string keys of a dict literal, or of a `dict(...)` call of keywords alone; None for anything else (a computed
    mapping, a `**spread`, a key that is not a string literal)."""
    if isinstance(node, ast.Dict):
        if all(isinstance(k, ast.Constant) and isinstance(k.value, str) for k in node.keys):
            return {k.value for k in node.keys}
        return None
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict" and not node.args
            and all(kw.arg is not None for kw in node.keywords)):
        return {kw.arg for kw in node.keywords}
    return None


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
        if tree is not None:
            self.absorb(_module_level_statements(tree.body))

    def absorb(self, nodes):
        for node in nodes:
            for n in ast.walk(node):
                if isinstance(n, ast.Import):
                    self.os_names.update(a.asname for a in n.names if a.name == "os" and a.asname)
                elif isinstance(n, ast.ImportFrom) and n.module == "os":
                    self.environ_names.update(a.asname or a.name for a in n.names if a.name == "environ")
                elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                    name = n.targets[0].id
                    if self.is_environ(n.value):
                        self.environ_names.add(name)
                    else:
                        self.dicts[name] = None if name in self.dicts else _literal_mapping_keys(n.value)
        return self

    def within(self, node):
        """These names plus whatever `node` (a function) binds itself."""
        inner = _EnvNames()
        inner.os_names, inner.environ_names, inner.dicts = set(self.os_names), set(self.environ_names), dict(self.dicts)
        return inner.absorb([node])

    def is_environ(self, node):
        if isinstance(node, ast.Attribute) and node.attr == "environ" and isinstance(node.value, ast.Name):
            return node.value.id in self.os_names
        return isinstance(node, ast.Name) and node.id in self.environ_names


def _unreadable(what, node, where):
    return UnreadableEnvWrite("cannot read the key%s of this %s at line %d of %s: %s (a string-literal key, a dict literal, "
                              "keyword arguments, or a name bound once to a dict literal are read; a computed key or "
                              "mapping is not)" % ("s" if what == "update" else "", what, node.lineno, where, ast.unparse(node)))


def _key(node, stmt, where, what):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    raise _unreadable(what, stmt, where)


def _mapping_keys(node, names, stmt, where):
    """The keys the mapping expression `node` gives an update or a `|=`: a literal, or a name bound to one; loud otherwise."""
    keys = _literal_mapping_keys(node)
    if keys is None and isinstance(node, ast.Name):
        keys = names.dicts.get(node.id)
    if keys is None:
        raise _unreadable("update", stmt, where)
    return keys


def _flat_targets(targets):
    for t in targets:
        if isinstance(t, (ast.Tuple, ast.List)):
            yield from _flat_targets(t.elts)
        elif isinstance(t, ast.Starred):
            yield from _flat_targets([t.value])
        else:
            yield t


def _env_writes(node, names, where="<module>"):
    """The environment keys the code under `node` sets: `environ[KEY] = v`, `environ |= {...}`, `environ.update({...})`,
    `environ.update(KEY=v)`, `environ.update(NAME)` for a NAME bound to a dict literal, `environ.setdefault(KEY, v)` and
    `os.putenv(KEY, v)`, environ spelled any way `names` knows (review round 2, 2026-09-18: the subscript and setdefault
    alone before, so a module-level update was invisible). A write whose keys cannot be read from the source raises
    UnreadableEnvWrite naming the line, never skips: the repo-wide import-time rule is only as good as the writes it
    reads. Removals (`pop`, `del`) are not writes and are outside this scan's contract: unset is the production default
    and the state a clean shell gives every module, so a removal at import sets nothing a later module would not have
    found on its own; _env_removals reads them where a restore counts."""
    names = names.within(node)
    keys = set()
    for n in ast.walk(node):
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            if isinstance(n, ast.AnnAssign) and n.value is None:
                continue        # a bare annotation writes nothing
            for t in _flat_targets(n.targets if isinstance(n, ast.Assign) else [n.target]):
                if isinstance(t, ast.Subscript) and names.is_environ(t.value):
                    keys.add(_key(t.slice, n, where, "environment assignment"))
        elif isinstance(n, ast.AugAssign) and names.is_environ(n.target):
            keys |= _mapping_keys(n.value, names, n, where)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if names.is_environ(n.func.value) and n.func.attr == "update":
                if len(n.args) > 1 or any(kw.arg is None for kw in n.keywords):
                    raise _unreadable("update", n, where)
                for a in n.args:
                    keys |= _mapping_keys(a, names, n, where)
                keys.update(kw.arg for kw in n.keywords)
            elif names.is_environ(n.func.value) and n.func.attr == "setdefault":
                keys.add(_key(n.args[0] if n.args else None, n, where, "setdefault"))
            elif isinstance(n.func.value, ast.Name) and n.func.value.id in names.os_names and n.func.attr == "putenv":
                keys.add(_key(n.args[0] if n.args else None, n, where, "putenv"))
    return keys


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


def _module_level_env_writes(tree, where="<module>"):
    """The environment keys the module writes at import, in every shape _env_writes reads, in any statement
    _module_level_statements yields; `where` names the file in the loud message for a write the scan cannot read."""
    names = _EnvNames(tree)
    keys = set()
    for s in _module_level_statements(tree.body):
        keys |= _env_writes(s, names, where)
    return keys


def _cleanup_restores(funcs, cls, classes, tree, names, where):
    """The environment keys the cleanups registered under `funcs` (`self.addCleanup(callee, ...)`) write or pop: the
    callee resolved to a method of `cls` (`self.<name>`, its own or a base's through the module's classes) or to a
    function defined at module level, plus any key named as a string argument of the registration (a helper that takes
    the name, conftest's restore_env). A restore registered as a cleanup runs when a later setUp statement raises,
    which a tearDown does not (review round 1, 2026-09-18)."""
    module_funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    keys = set()
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
    return keys


def _placement_faults(tree, where="test_kernel_tunnels.py"):
    """Every way a module that loads the kernel in-process and attaches misplaces a leg of the trio; empty when the
    placement holds. The port is assigned at module level before the kernel loads (the kernel reads it at import);
    peers is NEVER written at module level (the leak of 2026-09-18, module-level if/try/for/with bodies included, in
    every shape _env_writes reads); every class that attaches or detaches has a setUp (its own or through super()) that
    sets peers and registers a cleanup that restores it, and client-only is set before the load or in that setUp. A
    list rather than assertions so the check itself can be run over a synthetic module with the leak planted and shown
    to go red; a write the scan cannot read raises UnreadableEnvWrite out of it."""
    faults = []
    loads = [i for i, s in enumerate(tree.body) if _loads_kernel(s)]
    if not loads:
        return ["the module does not load the kernel in-process at module level"]
    names = _EnvNames(tree)
    before_load = set()
    for s in _module_level_statements(tree.body[:loads[0]]):
        before_load |= _env_writes(s, names, where)
    if "ROMP_POSTAL_PORT" not in before_load:
        faults.append("the port is not set before the kernel module loads (it reads the port at import)")
    if "ROMP_POSTAL_PEERS" in _module_level_env_writes(tree, where):
        faults.append("peers is written at module level: the kernel reads it at call time, and under xdist a value written at "
                      "import reaches every module on every worker (the remote-identity absorb case, red in 5 of 6 full runs)")
    classes = {c.name: c for c in tree.body if isinstance(c, ast.ClassDef)}
    attaching = [c for c in classes.values() if _attaches_or_detaches(c)]
    if len(attaching) < 2:
        faults.append("the scan sees fewer than two classes that attach or detach: %r" % [c.name for c in attaching])
    for cls in attaching:
        set_up = _method_chain(cls, "setUp", classes)
        if not set_up:
            faults.append("%s attaches or detaches and has no setUp" % cls.name)
            continue
        in_setup = set()
        for f in set_up:
            in_setup |= _env_writes(f, names, where)
        if "ROMP_POSTAL_PEERS" not in in_setup:
            faults.append("%s.setUp (own or through super()) does not set peers for its tests (a detach's refused bus notice "
                          "revives the bus otherwise)" % cls.name)
        if "ROMP_POSTAL_CLIENT_ONLY" not in before_load | in_setup:
            faults.append("%s: client-only is neither before the load nor in its setUp" % cls.name)
        if "ROMP_POSTAL_PEERS" not in _cleanup_restores(set_up, cls, classes, tree, names, where):
            faults.append("%s.setUp (own or through super()) registers no cleanup that restores peers: a tearDown restore is "
                          "skipped when a later setUp statement raises, and the 0 outlives the class (review round 1, "
                          "2026-09-18)" % cls.name)
    return faults


def _tunnels_source():
    return open(os.path.join(HERE, "test_kernel_tunnels.py"), encoding="utf-8", errors="replace").read()


_PLANT_ANCHOR = 'os.environ["ROMP_POSTAL_CLIENT_ONLY"] = "1"\n'


def _plant(src, lines):
    """`src` with `lines` inserted at module level just before the client-only assignment, that is before the kernel
    load: the place the leaked "0" used to be written. Loud when the anchor is not there once."""
    if src.count(_PLANT_ANCHOR) != 1:
        raise AssertionError("the planting anchor %r is in the module %d times, not once" % (_PLANT_ANCHOR, src.count(_PLANT_ANCHOR)))
    return src.replace(_PLANT_ANCHOR, lines + _PLANT_ANCHOR)


def _teardown_only_restore(src):
    """`src` (the tunnels module) with _PeersOff's restore moved back into a tearDown and no cleanup registered: the
    shape the round-1 review found leaking on a subclass setUp that raises."""
    out = src.replace("        self.addCleanup(self._restore_peers)\n", "        pass\n", 1)
    out = out.replace("    def _restore_peers(self):\n", "    def tearDown(self):\n", 1)
    peers_off = out.split("class _PeersOff", 1)[1].split("\nclass ", 1)[0]     # the rewritten class's body alone
    if "addCleanup" in peers_off or "def tearDown(self):" not in peers_off or out.count("def _restore_peers") != 0:
        raise AssertionError("the tunnels module no longer has the _PeersOff shape this synthetic copy rewrites")
    return out


_PROBE = textwrap.dedent("""
    import json, os, shutil, sys, unittest
    os.environ.pop("ROMP_POSTAL_PEERS", None)
    here, planted = sys.argv[1], sys.argv[2]
    sys.path.insert(0, here)
    if planted:
        # a synthetic copy of the module, compiled under the real file's name so its HERE and BIN resolve
        real = os.path.join(here, "test_kernel_tunnels.py")
        t = type(sys)("test_kernel_tunnels_planted")
        t.__file__ = real
        exec(compile(open(planted, encoding="utf-8").read(), real, "exec"), t.__dict__)
    else:
        import test_kernel_tunnels as t
    out = {"after_import": os.environ.get("ROMP_POSTAL_PEERS")}
    os.environ["ROMP_POSTAL_PEERS"] = "1"
    case = t.TunnelConcierge("test_attach_requires_host")
    case.setUp()
    out["in_setup"] = os.environ.get("ROMP_POSTAL_PEERS")
    case.tearDown()
    out["after_teardown"] = os.environ.get("ROMP_POSTAL_PEERS")
    case.doCleanups()
    out["after_cleanups"] = os.environ.get("ROMP_POSTAL_PEERS")

    class Raises(t._PeersOff):
        def setUp(self):
            super().setUp()
            raise OSError("planted: the rest of a subclass's setUp failing after the peers write")

        def test_never_reached(self):
            pass

    result = unittest.TestResult()
    Raises("test_never_reached").run(result)
    out["setup_raise_errors"] = len(result.errors)
    out["after_setup_raise"] = os.environ.get("ROMP_POSTAL_PEERS")
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


# The plant table the guard test runs (test_the_guard_itself_sees_the_spawn_sites): one synthetic module per row, each
# labelled with what the scan must do with it. caught-by-argv: one site, at the planted call's line, an argv element
# (or the executable=) that is the path as written; caught-by-binding: one site, at the planted call's line, read
# through a name or a self.X target resolved to a declaration bound to the path; no-spawn: no site (the word-collision
# class of the regex census, a -c child that loads the kernel, the CLI with another verb, the other bin/ scripts, an
# in-process load, a parameter, and each class of the residual the module docstring states); refused-loud:
# UnreadableSpawn naming the call's line and both declarations, (call line, path line, other line). Every row is
# synthetic (an unbound BIN, no real path). The row labelled B1 is the case the ruling of 2026-09-21 required: a kernel
# path bound across two lines, missed by the regex census because its KERNEL_NAME pattern read one line. The comparison
# case (test_the_scan_covers_every_call_the_regex_census_it_replaced_flagged) runs that census over every row as well,
# and every shape PR #850's ninth review round probed has a row here at the class that round's ruling gave it; a row
# whose label says the regex missed it too is held to that by the comparison case.
PLANT_TABLE = (
    ("B1 two-line binding (the ruling's required case)", 'caught-by-binding', 3,
     'KERNEL = os.path.join(\n    BIN, "romp-kernel")\nsubprocess.Popen([KERNEL])'),
    ("B2 a constant holding the script's name", 'caught-by-binding', 3,
     'NAME = "romp-kernel"\nK = os.path.join(BIN, NAME)\nsubprocess.run([K])'),
    ('B3 composed by +', 'caught-by-binding', 2,
     'K = BIN + "/romp-kernel"\nsubprocess.run([K])'),
    ('B4 composed by %', 'caught-by-binding', 2,
     'K = "%s/romp-kernel" % BIN\nsubprocess.run([K])'),
    ('B5 a resolved Path through str', 'caught-by-binding', 2,
     'KP = Path(BIN, "romp-kernel").resolve()\nsubprocess.run([str(KP)])'),
    ('B6 an instance attribute set in setUp', 'caught-by-binding', 5,
     'class T:\n    def setUp(self):\n        self.kernel = os.path.join(BIN, "romp-kernel")\n    def test_a(self):\n        subprocess.Popen([self.kernel])'),
    ('B7 a class attribute read through self', 'caught-by-binding', 4,
     'class T:\n    KERNEL = os.path.join(BIN, "romp-kernel")\n    def test_a(self):\n        subprocess.Popen([self.KERNEL])'),
    ('B8 a dict entry by subscript', 'caught-by-binding', 2,
     'PATHS = {"kernel": os.path.join(BIN, "romp-kernel")}\nsubprocess.run([PATHS["kernel"]])'),
    ('B9 a tuple target', 'caught-by-binding', 2,
     'KERNEL, JUDGE = os.path.join(BIN, "romp-kernel"), os.path.join(BIN, "romp-judge")\nsubprocess.run([KERNEL])'),
    ('B10 an annotated assignment', 'caught-by-binding', 2,
     'K: str = os.path.join(BIN, "romp-kernel")\nsubprocess.run([K])'),
    ('B11 a walrus', 'caught-by-binding', 2,
     'if (K := os.path.join(BIN, "romp-kernel")):\n    subprocess.run([K])'),
    ('B12 the argv held in a name', 'caught-by-binding', 2,
     'cmd = [sys.executable, os.path.join(BIN, "romp-kernel")]\nsubprocess.run(cmd)'),
    ('B13 a splat of a named argv', 'caught-by-binding', 2,
     'KARGV = [os.path.join(BIN, "romp-kernel")]\nsubprocess.run([sys.executable, *KARGV])'),
    ('B14 a local of the spawning function', 'caught-by-binding', 3,
     'def start():\n    k = os.path.join(BIN, "romp-kernel")\n    return subprocess.Popen([sys.executable, k])'),
    ('B15 a None placeholder rebound through global', 'caught-by-binding', 6,
     'KERNEL = None\ndef setUpModule():\n    global KERNEL\n    KERNEL = os.path.join(BIN, "romp-kernel")\ndef test_a():\n    subprocess.Popen([KERNEL])'),
    ("B16 a base class's setUp sets the attribute", 'caught-by-binding', 6,
     'class Base:\n    def setUp(self):\n        self.kernel = os.path.join(BIN, "romp-kernel")\nclass T(Base):\n    def test_a(self):\n        subprocess.Popen([self.kernel])'),
    ('B17 the join imported by name', 'caught-by-binding', 3,
     'from os.path import join\nK = join(BIN, "romp-kernel")\nsubprocess.Popen([K])'),
    ('B18 os.path under an import alias', 'caught-by-binding', 3,
     'import os.path as osp\nK = osp.join(BIN, "romp-kernel")\nsubprocess.Popen([K])'),
    ('B19 Path under an import alias, through str', 'caught-by-binding', 3,
     'from pathlib import Path as P\nK = str(P(BIN, "romp-kernel"))\nsubprocess.Popen([K])'),
    ('B20 import os.path, which binds the name os', 'caught-by-binding', 3,
     'import os.path\nK = os.path.join(BIN, "romp-kernel")\nsubprocess.run([K])'),
    ('B21 os.path.join under a name bound by assignment', 'caught-by-binding', 3,
     'j = os.path.join\nK = j(BIN, "romp-kernel")\nsubprocess.run([K])'),
    ("B22 a star import's bare join (unbound: read by its spelling)", 'caught-by-binding', 3,
     'from os.path import *\nK = join(BIN, "romp-kernel")\nsubprocess.run([K])'),
    ("B23 a tuple's kernel element by index, the judge's beside it", 'caught-by-binding', 2,
     'SCRIPTS = (os.path.join(BIN, "romp-judge"), os.path.join(BIN, "romp-kernel"))\nsubprocess.run([SCRIPTS[-1]])'),
    ("B24 a dict's kernel entry by key, the judge's beside it", 'caught-by-binding', 2,
     'PATHS = {"judge": os.path.join(BIN, "romp-judge"), "kernel": os.path.join(BIN, "romp-kernel")}\nsubprocess.run([PATHS["kernel"]])'),
    ('B25 a slice the scan cannot read: any element of the tuple (the over-approximating side)', 'caught-by-binding', 3,
     'SCRIPTS = (os.path.join(BIN, "romp-judge"), os.path.join(BIN, "romp-kernel"))\ndef t(i):\n    subprocess.run([SCRIPTS[i]])'),
    ('B26 a shell command by % template with arguments, held in a name', 'caught-by-binding', 2,
     'cmd = "%s/romp-kernel --serve" % BIN\nsubprocess.Popen(cmd, shell=True)'),
    ('B27 a placeholder head with arguments, the program a name', 'caught-by-binding', 3,
     'K = os.path.join(BIN, "romp-kernel")\ncmd = "%s --serve" % K\nsubprocess.Popen(cmd, shell=True)'),
    ('B28 a template whose path is itself a placeholder, held in a name (row N24 before review round 9)', 'caught-by-binding', 2,
     'K = "%s/%s" % (BIN, "romp-kernel")\nsubprocess.run([K])'),
    ('B29 an f-string command, the path first', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.Popen(f"{KERNEL} --serve", shell=True)'),
    ('B30 an f-string command, the interpreter first', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.Popen(f"{sys.executable} {KERNEL} --serve", shell=True)'),
    ('B31 an f-string command behind exec', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.Popen(f"exec {KERNEL} --serve", shell=True)'),
    ('B32 a % command behind exec', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.Popen("exec %s" % KERNEL, shell=True)'),
    ('B33 an f-string whose path is itself a placeholder, the name a constant', 'caught-by-binding', 2,
     'NAME = "romp-kernel"\nsubprocess.run([f"{BIN}/{NAME}"])'),
    ('B34 a .format command with a keyword field', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.Popen("{k} --serve".format(k=KERNEL), shell=True)'),
    ('B35 a %-mapping command over a dict literal', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.Popen("%(k)s --serve" % {"k": KERNEL}, shell=True)'),
    ('B36 a template whose path is a placeholder, the name bound on one line', 'caught-by-binding', 2,
     'NAME = "romp-kernel"\nsubprocess.run(["%s/%s" % (BIN, NAME)])'),
    ('B37 a template whose path is a placeholder, bound across two lines', 'caught-by-binding', 3,
     'K = "%s/%s" % (\n    BIN, "romp-kernel")\nsubprocess.run([K])'),
    ('B38 the path and its arguments joined by + inside one element', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.Popen([KERNEL + " --serve"], shell=True)'),
    ('B39 the env-override idiom by or', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.run([os.environ.get("ROMP_KERNEL") or KERNEL, "--serve"])'),
    ("B40 the env-override idiom by .get's default", 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.run([os.environ.get("ROMP_KERNEL", KERNEL), "--serve"])'),
    ("B41 the env-override idiom by os.getenv's default", 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.run([os.getenv("ROMP_KERNEL", KERNEL), "--serve"])'),
    ("B42 Popen's executable=, the program beside an argv that names it otherwise", 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.Popen(["kernel", "--serve"], executable=KERNEL)'),
    ('B43 a list comprehension argv', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.run([str(p) for p in (KERNEL, "--serve")])'),
    ('B44 a generator argv through list()', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.run(list(a for a in (KERNEL, "--serve")))'),
    ('B45 a set comprehension argv, the element expression the path', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.run({KERNEL for _ in range(1)})'),
    ('B46 an argv by or, a default list beside a name', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.run(CMD or [KERNEL, "--serve"])'),
    ('B47 an argv by a walrus', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.run(cmd := [KERNEL, "--serve"])'),
    ('B48 a %-mapping command over a name bound to a dict (every argument read)', 'caught-by-binding', 3,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nARGS = {"k": KERNEL}\nsubprocess.Popen("%(k)s --serve" % ARGS, shell=True)'),
    ('B49 a .format template handed a splat (every argument read)', 'caught-by-binding', 2,
     'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.run(["exec {}".format(*[KERNEL])])'),
    ("B50 a base's method reading self.SCRIPT, the base's own binding another script, a subclass's the kernel", 'caught-by-binding', 4,
     'class Base:\n    SCRIPT = os.path.join(BIN, "romp-judge")\n    def setUp(self):\n        subprocess.Popen([sys.executable, self.SCRIPT])\n'
     'class T(Base):\n    SCRIPT = os.path.join(BIN, "romp-kernel")'),
    ("B51 a base's method reading self.SCRIPT, the base's own binding the kernel, a subclass's another script", 'caught-by-binding', 4,
     'class Base:\n    SCRIPT = os.path.join(BIN, "romp-kernel")\n    def setUp(self):\n        subprocess.Popen([sys.executable, self.SCRIPT])\n'
     'class T(Base):\n    SCRIPT = os.path.join(BIN, "romp-judge")'),
    ("B52 a subclass's own method reading an attribute it overrides with the kernel", 'caught-by-binding', 6,
     'class Base:\n    SCRIPT = os.path.join(BIN, "romp-judge")\nclass T(Base):\n    SCRIPT = os.path.join(BIN, "romp-kernel")\n'
     '    def test_a(self):\n        subprocess.Popen([sys.executable, self.SCRIPT])'),
    ("B53 a base's method reading self.SCRIPT, the kernel bound two classes below it", 'caught-by-binding', 4,
     'class Base:\n    SCRIPT = os.path.join(BIN, "romp-judge")\n    def setUp(self):\n        subprocess.Popen([sys.executable, self.SCRIPT])\n'
     'class Mid(Base):\n    pass\nclass T(Mid):\n    SCRIPT = os.path.join(BIN, "romp-kernel")'),
    ("B54 a base's method reading self.SCRIPT, the kernel first in a subclass's C3 order and last breadth first", 'caught-by-binding', 4,
     'class Base:\n    SCRIPT = os.path.join(BIN, "romp-judge")\n    def setUp(self):\n        subprocess.Popen([sys.executable, self.SCRIPT])\n'
     'class KernelRoot:\n    SCRIPT = os.path.join(BIN, "romp-kernel")\nclass KernelMixin(KernelRoot):\n    pass\n'
     'class T(KernelMixin, Base):\n    pass'),
    ('A1 the library under an alias', 'caught-by-argv', 2,
     'import subprocess as sp\nsp.Popen([os.path.join(BIN, "romp-kernel")])'),
    ('A2 a from-import of run', 'caught-by-argv', 2,
     'from subprocess import run\nrun([os.path.join(BIN, "romp-kernel")])'),
    ('A3 the CLI with the verb that starts a kernel', 'caught-by-argv', 1,
     'subprocess.check_output([os.path.join(BIN, "romp"), "up", "--foreground"])'),
    ('A4 a list built by + onto an unread head', 'caught-by-argv', 1,
     'subprocess.run(HEAD + [os.path.join(BIN, "romp-kernel")])'),
    ('A5 an f-string', 'caught-by-argv', 1,
     'subprocess.Popen([f"{BIN}/romp-kernel"])'),
    ('A6 a call split across lines with Path division', 'caught-by-argv', 1,
     'subprocess.run(\n    [sys.executable, str(BIN / "romp-kernel")],\n    capture_output=True)'),
    ('A7 the spawn function bound by assignment', 'caught-by-argv', 2,
     'run = subprocess.run\nrun([os.path.join(BIN, "romp-kernel")])'),
    ('A8 a shell command by % template with arguments', 'caught-by-argv', 1,
     'subprocess.Popen("%s/romp-kernel --serve" % BIN, shell=True)'),
    ('A9 a shell command by .format with arguments', 'caught-by-argv', 1,
     'subprocess.Popen("{}/romp-kernel --serve".format(BIN), shell=True)'),
    ('A10 a wrapper launch, the path at index 2 (the index is not read)', 'caught-by-argv', 1,
     'subprocess.run(["timeout", "30", os.path.join(BIN, "romp-kernel")])'),
    ("A11 grep for the kernel's name (an accepted false red: the argv holds the path)", 'caught-by-argv', 1,
     'subprocess.run(["grep", "-l", "romp-kernel", "docs"])'),
    ('A12 an f-string command, the path written first', 'caught-by-argv', 2,
     'port = 29855\nsubprocess.Popen(f"bin/romp-kernel --serve --port {port}", shell=True)'),
    ('A13 a template whose path is itself a placeholder, inline', 'caught-by-argv', 1,
     'subprocess.run(["%s/%s" % (BIN, "romp-kernel")])'),
    ('A14 the CLI with the verb that starts a kernel, as a shell string', 'caught-by-argv', 1,
     'subprocess.Popen("bin/romp up --foreground", shell=True)'),
    ('A15 an f-string command, two placeholders joined onto the path', 'caught-by-argv', 1,
     'subprocess.Popen(f"{sys.executable}{BIN}/romp-kernel --serve", shell=True)'),
    ('A16 a .format template whose path is itself a placeholder, inline', 'caught-by-argv', 1,
     'subprocess.run(["{}/{}".format(BIN, "romp-kernel")])'),
    ('A17 a str.join over a literal list', 'caught-by-argv', 1,
     'subprocess.run([sys.executable, "/".join([BIN, "romp-kernel"])])'),
    ('A18 a walrus used as a value', 'caught-by-argv', 1,
     'subprocess.run([(k := os.path.join(BIN, "romp-kernel")), "--serve"])'),
    ('A19 the CLI after an environment assignment, as a shell string', 'caught-by-argv', 1,
     'subprocess.Popen("ROMP_X=1 bin/romp up", shell=True)'),
    ('A20 the CLI under env, as a shell string', 'caught-by-argv', 1,
     'subprocess.Popen("env ROMP_X=1 bin/romp up --foreground", shell=True)'),
    ('N1 a same-named local in another function', 'no-spawn', None,
     'def a():\n    k = os.path.join(BIN, "romp-kernel")\ndef b():\n    k = [sys.executable, "-m", "pytest"]\n    subprocess.run(k)'),
    ('N2 p beside -p', 'no-spawn', None,
     'p = os.path.join(BIN, "romp-kernel")\nopen(p).read()\nsubprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider"])'),
    ('N3 k beside -k', 'no-spawn', None,
     'k = os.path.join(BIN, "romp-kernel")\nopen(k).read()\nsubprocess.run([sys.executable, "-m", "pytest", "-k", "boot"])'),
    ('N4 src beside src/main.ts', 'no-spawn', None,
     'src = open(os.path.join(BIN, "romp-kernel")).read()\nsubprocess.run(["node", "src/main.ts"])'),
    ('N5 km beside import km', 'no-spawn', None,
     'km = load_source("romp_kernel_x", os.path.join(BIN, "romp-kernel"))\nsubprocess.run([sys.executable, "-c", "import km"])'),
    ('N6 kernel beside grep kernel', 'no-spawn', None,
     'kernel = os.path.join(BIN, "romp-kernel")\nsubprocess.run(["grep", "kernel", "docs"])'),
    ('N7 lines beside -k lines', 'no-spawn', None,
     'lines = open(os.path.join(BIN, "romp-kernel")).read().splitlines()\nsubprocess.run([sys.executable, "-m", "pytest", "-k", "lines"])'),
    ("N8 the shape that collided (text spelling the path, -p)", 'no-spawn', None,
     'p = "os.path.join(BIN, \'romp-kernel\')"\nsubprocess.run([sys.executable, "-m", "pytest", "-p", "tests.conftest"])'),
    ('N9 a -c child that loads the kernel, inline', 'no-spawn', None,
     'subprocess.run([sys.executable, "-c", "load_source(\'k\', os.path.join(%r, \'romp-kernel\'))" % BIN])'),
    ('N10 a -c child that loads the kernel, the program held in a name', 'no-spawn', None,
     'CODE = "km = load_source(\'k\', os.path.join(BIN, \'romp-kernel\'))\\n"\nsubprocess.run([sys.executable, "-c", CODE])'),
    ('N11 a comment spelling a launch', 'no-spawn', None,
     'x = 1  # subprocess.Popen([os.path.join(BIN, "romp-kernel")])\nsubprocess.run(["true"])'),
    ('N12 a docstring spelling a launch', 'no-spawn', None,
     '"""subprocess.Popen([os.path.join(BIN, "romp-kernel")])"""\nsubprocess.run(["true"])'),
    ('N13 the CLI with another verb', 'no-spawn', None,
     'ROMP = os.path.join(BIN, "romp")\nsubprocess.run(["bash", ROMP, "--help"])'),
    ('N14 an in-process load', 'no-spawn', None,
     'load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))'),
    ('N15 the judge script', 'no-spawn', None,
     'subprocess.run([os.path.join(BIN, "romp-judge"), "--once"])'),
    ('N16 a parameter (the stated residual)', 'no-spawn', None,
     'def start(argv):\n    return subprocess.Popen(argv)'),
    ('N17 a Popen handle named beside -k', 'no-spawn', None,
     'proc = subprocess.Popen([os.path.join(BIN, "romp-judge")])\nsubprocess.run([sys.executable, "-m", "pytest", "-k", "proc"])'),
    ('N18 a module constant shadowed by a local argv', 'no-spawn', None,
     'KERNEL = os.path.join(BIN, "romp-kernel")\ndef b():\n    KERNEL = [sys.executable, "-m", "pytest"]\n    subprocess.run(KERNEL)'),
    ('N19 a build and the postal service', 'no-spawn', None,
     'subprocess.run(["node", "esbuild.js"], cwd=EXT)\nsubprocess.run(["bin/romp-postal-service", "ensure"])'),
    ("N20 the judge's element of a tuple by index, the kernel's beside it", 'no-spawn', None,
     'SCRIPTS = (os.path.join(BIN, "romp-kernel"), os.path.join(BIN, "romp-judge"))\nsubprocess.run([SCRIPTS[1], "--once"])'),
    ("N21 the judge's entry of a dict by key, the kernel's beside it", 'no-spawn', None,
     'PATHS = {"kernel": os.path.join(BIN, "romp-kernel"), "judge": os.path.join(BIN, "romp-judge")}\nsubprocess.run([PATHS["judge"], "--once"])'),
    ('N22 a key the dict has not', 'no-spawn', None,
     'PATHS = {"kernel": os.path.join(BIN, "romp-kernel")}\nsubprocess.run([PATHS["judge"]])'),
    ('N23 a name bound by assignment to a builtin, no spawn function', 'no-spawn', None,
     'run = print\nrun(os.path.join(BIN, "romp-kernel"))'),
    ("N25 a helper's return (the stated residual, listed)", 'no-spawn', None,
     'def kpath():\n    return os.path.join(BIN, "romp-kernel")\nsubprocess.run([kpath()])'),
    ('N26 the CLI with refresh, which acts through a manager already running', 'no-spawn', None,
     'subprocess.run([os.path.join(BIN, "romp"), "refresh"])'),
    ('N27 the CLI with kernel, a verb bin/romp does not have', 'no-spawn', None,
     'subprocess.check_output([os.path.join(BIN, "romp"), "kernel", "--serve"])'),
    ('N28 a suffixed word: the path with .orig after it, bound across two lines', 'no-spawn', None,
     'KERNEL = os.path.join(\n    BIN, "romp-kernel")\nsubprocess.run(["cp", f"{KERNEL}.orig", "/tmp/TESTHOST"])'),
    ('N29 an argv mutated by append, extend or insert (the stated residual; the regex missed it too)', 'no-spawn', None,
     'a = ["python3"]\na.append(os.path.join(BIN, "romp-kernel"))\nsubprocess.run(a)\n'
     'b = ["python3"]\nb.extend([os.path.join(BIN, "romp-kernel")])\nsubprocess.run(b)\n'
     'c = ["python3"]\nc.insert(1, os.path.join(BIN, "romp-kernel"))\nsubprocess.run(c)'),
    ('N30 a spawn function reached through functools.partial or getattr (the stated residual; the regex missed it too)', 'no-spawn', None,
     'run = functools.partial(subprocess.run, check=True)\nrun([os.path.join(BIN, "romp-kernel")])\n'
     'getattr(subprocess, "Popen")([os.path.join(BIN, "romp-kernel")])'),
    ('N31 a spawn function outside the subprocess module (the stated residual; the regex missed it too)', 'no-spawn', None,
     'os.execv(os.path.join(BIN, "romp-kernel"), ["romp-kernel"])\n'
     'os.posix_spawn(os.path.join(BIN, "romp-kernel"), ["romp-kernel"], os.environ)\n'
     'asyncio.create_subprocess_exec(os.path.join(BIN, "romp-kernel"))'),
    ("N32 a consumer call's arguments, the path bound across two lines (the stated residual)", 'no-spawn', None,
     'K = os.path.join(\n    BIN, "romp-kernel")\nsubprocess.run(["python3", os.path.relpath(K)])\n'
     'subprocess.run([shutil.which(K)])\nsubprocess.run([K.replace("-kernel", "-judge")])'),
    ('N33 a one-line lambda (the stated residual, listed)', 'no-spawn', None,
     'k = lambda: os.path.join(BIN, "romp-kernel")\nsubprocess.run([k()])'),
    ('N34 type(self).X (the stated residual, listed)', 'no-spawn', None,
     'class T:\n    KERNEL = os.path.join(BIN, "romp-kernel")\n    def test_a(self):\n        subprocess.run([type(self).KERNEL])'),
    ('N35 a comprehension over a parameter (the stated residual, listed)', 'no-spawn', None,
     'def start(args):\n    return subprocess.run([a for a in args])'),
    ('N36 a call handed only a keywords splat (the stated residual, listed)', 'no-spawn', None,
     'def start(**kw):\n    return subprocess.run(**kw)'),
    ('N37 a class attribute read through the class name (the stated residual, listed)', 'no-spawn', None,
     'class Lab:\n    K = os.path.join(BIN, "romp-kernel")\nsubprocess.run([Lab.K])'),
    ("N38 a subclass's own method reading an attribute it overrides with another script, the base's the kernel", 'no-spawn', None,
     'class Base:\n    SCRIPT = os.path.join(BIN, "romp-kernel")\nclass T(Base):\n    SCRIPT = os.path.join(BIN, "romp-judge")\n'
     '    def test_a(self):\n        subprocess.Popen([sys.executable, self.SCRIPT])'),
    ('R1 a rebinding in one function', 'refused-loud', (4, 2, 3),
     'def t():\n    k = os.path.join(BIN, "romp-kernel")\n    k = [sys.executable, "-m", "pytest", "-k", "boot"]\n    subprocess.run(k)'),
    ('R2 two module-level bindings that disagree', 'refused-loud', (3, 1, 2),
     'K = os.path.join(BIN, "romp-kernel")\nK = os.path.join(BIN, "romp-judge")\nsubprocess.run([K])'),
)



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
        """Keyed on the spawn's argv read from each module's ast, every name resolved to its binding (_SpawnScan over
        ast_bindings), and on the trio's presence in the module's text (_hermetic); a module the scan can read neither
        way is loud here (UnreadableSpawn), never passed over. The offender is named with the file, the line and the
        argv."""
        offenders = _kernel_spawn_offenders(HERE, skip=(os.path.basename(__file__),))
        self.assertEqual(offenders, [], "these tests start a kernel process without the postal trio (use kernel_env, or set "
                                        "ROMP_POSTAL_PORT to a free port, ROMP_POSTAL_PEERS=0 and ROMP_POSTAL_CLIENT_ONLY=1), "
                                        "(file, line, argv): %r" % offenders)

    def test_the_guard_itself_sees_the_spawn_sites(self):
        """The scan must read the spawn idioms the labs use, else the trio rule above would pass vacuously; and it must
        refuse the shapes the regex census read wrongly (2026-09-21), else the rule reds on a module that starts no
        kernel. Three reads. (1) The tree: the roads table over every module the trio test reads (spawn_roads; the
        `--roads` arm prints it) holds the two lab modules on the argv road and no module refused, and the message
        REPORTS the four road counts, the module count and the plant-table row count at whatever size the tree has,
        so a change of population is visible here and fails nothing by itself. (2) The head's five positives and four negatives, snippets with no import of subprocess,
        so the library is read by its spelling as an unbound name (the stated fallback). (3) PLANT_TABLE: every row
        run and held to its label, the site's LINE held to the planted call's, the road held to the label's, the
        refusal's message held to name the call's line and both declarations. (4) The listed residual: a helper's
        call, a passthrough's splatted parameter, a star import's name, a class attribute read through the class
        name, a comprehension's parameter iterable and a keywords splat handed alone are no site and each is under
        `unresolved` with its line, text and kind; a comprehension's own target is not, and neither is a builtin's
        call, a consumer."""
        roads = spawn_roads(HERE, skip=(os.path.basename(__file__),))
        counts = {r: sum(1 for road, _, _ in roads.values() if road == r) for r in ("argv", "binding", "neither", "refused")}
        report = ("the roads table over %d modules under tests/ (python tests/test_hermetic_kernel_postal.py --roads): argv %d, "
                  "binding %d, neither %d, refused %d; PLANT_TABLE %d rows"
                  % (len(roads), counts["argv"], counts["binding"], counts["neither"], counts["refused"], len(PLANT_TABLE)))
        for lab in ("test_federation_missing_served.py", "test_notification_tap_resume_browser.py"):
            self.assertEqual(roads.get(lab, ("absent from the table",))[0], "argv",
                             "%s starts a lab kernel by an argv element that is the path as written; %s" % (lab, report))
        self.assertEqual([n for n, (road, _, _) in roads.items() if road == "refused"], [],
                         "a module under tests/ binds an argv name both to the kernel's path and to something else; %s" % report)
        # the head's shapes: a list literal, a path joined or divided, a call split across lines, run as well as Popen
        for src in ('subprocess.Popen([os.path.join(BIN, "romp-kernel")], env=env)',
                    'subprocess.run(\n    [sys.executable, str(BIN / "romp-kernel")],\n    capture_output=True)',
                    'Popen(["python3", "bin/romp-kernel"])',
                    'subprocess.check_output([os.path.join(BIN, "romp"), "up", "--foreground"])',
                    'KERNEL = os.path.join(BIN, "romp-kernel")\nproc = subprocess.Popen([sys.executable, KERNEL], env=env)'):
            self.assertTrue(_spawns_kernel(src), "a kernel spawn the labs write, the library by its spelling (unbound): " + src)
        for src in ('subprocess.run(["node", "esbuild.js"], cwd=EXT)',
                    'subprocess.run(["bin/romp-postal-service", "ensure"])',
                    'subprocess.run([os.path.join(BIN, "romp-judge"), "--once"])',
                    'load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))'):
            self.assertFalse(_spawns_kernel(src), "not a kernel spawn (a build, the other scripts, an in-process load): " + src)
        # the labelled table
        roads_by_label = {"caught-by-argv": "argv", "caught-by-binding": "binding"}
        for label, kind, site, src in PLANT_TABLE:
            if kind == "refused-loud":
                call, path, other = site
                with self.assertRaises(UnreadableSpawn, msg="%s: two declarations that disagree are refused loudly, never read either way" % label) as loud:
                    _kernel_spawn_sites(src, "planted.py")
                for needle in ("planted.py line %d:" % call, "(line %d:" % path, "(line %d:" % other):
                    self.assertIn(needle, str(loud.exception), "%s: the refusal names the call's line and both declarations: %s" % (label, loud.exception))
            elif kind == "no-spawn":
                self.assertEqual(_kernel_spawn_sites(src, "planted.py"), [], "%s: no kernel spawn (keyed on the argv's elements resolved "
                                 "to their bindings, never on a word of the argv's text)" % label)
            else:
                sites = _kernel_spawn_sites(src, "planted.py")
                self.assertEqual([(line, road) for line, _, road in sites], [(site, roads_by_label[kind])],
                                 "%s: one site, at the planted call's line %d, by the %s road: %r (%s)" % (label, site, roads_by_label[kind], sites, report))
        self.assertEqual(sorted({kind for _, kind, _, _ in PLANT_TABLE}), ["caught-by-argv", "caught-by-binding", "no-spawn", "refused-loud"],
                         "the table carries every label at least once")
        # the residual, listed (keyed on the callee's or the name's declarations: none readable, or none at all and no builtin)
        for src, listed in (('def kpath():\n    return os.path.join(BIN, "romp-kernel")\nsubprocess.run([kpath()])', (3, "kpath", "call of def")),
                            ('def fake_run(*a, **kw):\n    return subprocess.run(*a, **kw)', (2, "a", "parameter")),
                            ('from helpers import *\nsubprocess.run([kernel_argv()])', (2, "kernel_argv", "call of an unbound name")),
                            ('class Lab:\n    K = os.path.join(BIN, "romp-kernel")\nsubprocess.run([Lab.K])', (3, "Lab.K", "attribute of class")),
                            ('def start(args):\n    return subprocess.run([a for a in args])', (2, "args", "parameter")),
                            ('def start(**kw):\n    return subprocess.run(**kw)', (2, "kw", "keywords splat of parameter"))):
            scan = _SpawnScan(ast.parse(src), "planted.py")
            self.assertEqual(scan.sites(), [], "no site, the value unread (keyed on the declarations the scan resolves to): " + src)
            self.assertIn(listed, scan.unresolved, "the unread value is listed under the residual as (line, text, kind), never passed "
                          "over silently (keyed on the declarations' kinds): %r for %s" % (scan.unresolved, src))
        scan = _SpawnScan(ast.parse('def start(args):\n    return subprocess.run([str(a) for a in args])'), "planted.py")
        scan.sites()
        self.assertEqual([text for _, text, _ in scan.unresolved], ["args"], "a comprehension's own target is never resolved, so "
                         "it is never listed; its iterable, a parameter, is (keyed on the comprehension's scope): %r" % scan.unresolved)
        scan = _SpawnScan(ast.parse('subprocess.run([repr(BIN), open(BIN).read()])'), "planted.py")
        self.assertEqual((scan.sites(), scan.unresolved), ([], []),
                         "a builtin's call and a consumer's method are read as no path and not listed (keyed on the callee being a "
                         "builtin, or an attribute): %r" % ((scan.sites(), scan.unresolved),))

    def test_the_offender_census_names_a_planted_launch_by_its_line_and_not_a_planted_word_collision(self):
        """The composition the trio test runs (_kernel_spawn_offenders: the spawn scan and the trio read together, over a
        directory of modules) and the roads table (spawn_roads), over planted modules: the module that launches the
        kernel through a path bound across two lines with no trio is the one offender, named with its file, the line of
        the call and the argv; the same launch under kernel_env is none; eight modules whose only tie to the kernel is a
        local bound to its path, or to text spelling it, beside a nested pytest argv carrying the local's name as a flag
        or a word are none (the regex census named every one of them and missed the launch, the red-before of
        2026-09-21); the roads label the two launches binding and the eight neither. A separate directory holds a
        module that binds one name to the path and to a pytest argv in one function: the census is loud on it, naming
        the module and both lines, and the roads table labels it refused."""
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        head = 'import os, subprocess, sys, unittest\nBIN = "/tmp/TESTHOST/bin"\n\nclass T(unittest.TestCase):\n    def test_a(self):\n'
        launch = '        KERNEL = os.path.join(\n            BIN, "romp-kernel")\n        subprocess.Popen([KERNEL], env=%s)\n'
        pytest_argv = '        subprocess.run([sys.executable, "-m", "pytest", %s"tests/test_other.py"])\n'
        planted = {"test_launch_no_trio.py": head + launch % "{}",
                   "test_launch_kernel_env.py": head + launch % "kernel_env(d, c, x, 1, t)"}
        for local, flag in (("p", '"-p", "no:cacheprovider", '), ("x", '"-x", '), ("k", '"-k", "boot", '), ("path", '"path/of/tests", '),
                            ("kernel", '"kernel", '), ("src", '"src/main.ts", '), ("lines", '"-k", "lines", ')):
            planted["test_collide_%s.py" % local] = (head + '        %s = os.path.join(BIN, "romp-kernel")\n        open(%s).read()\n' % (local, local)
                                                    + pytest_argv % flag)
        planted["test_collide_text.py"] = head + '        p = "os.path.join(BIN, \'romp-kernel\')"\n' + pytest_argv % '"-p", "tests.conftest", '
        for name, text in planted.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(text)
        text = planted["test_launch_no_trio.py"]
        planted_line = text[:text.index("subprocess.Popen")].count("\n") + 1
        self.assertEqual(_kernel_spawn_offenders(d), [("test_launch_no_trio.py", planted_line, "[KERNEL]")],
                         "the one offender, named with the line of the planted call (the two-line binding read through KERNEL)")
        self.assertEqual(_kernel_spawn_offenders(d, skip=("test_launch_no_trio.py",)), [], "the launch under kernel_env and the eight collisions are none")
        roads = {name: road for name, (road, _, _) in spawn_roads(d).items()}
        self.assertEqual(roads, dict({n: "neither" for n in planted}, **{"test_launch_no_trio.py": "binding", "test_launch_kernel_env.py": "binding"}),
                         "the roads table over the planted directory: the two launches by the binding road, the eight collisions neither")
        loud_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, loud_dir, True)
        rebinding = (head + '        k = os.path.join(BIN, "romp-kernel")\n        k = [sys.executable, "-m", "pytest", "-k", "boot"]\n'
                     + '        subprocess.run(k)\n')
        with open(os.path.join(loud_dir, "test_rebinding.py"), "w", encoding="utf-8") as f:
            f.write(rebinding)
        with self.assertRaises(UnreadableSpawn, msg="a name bound to the path and to a pytest argv in one function is refused loudly by the census") as loud:
            _kernel_spawn_offenders(loud_dir)
        for needle in ("test_rebinding.py line 8:", "(line 6:", "(line 7:"):
            self.assertIn(needle, str(loud.exception), "the refusal names the module, the call's line and both declarations: %s" % loud.exception)
        self.assertEqual([road for road, _, _ in spawn_roads(loud_dir).values()], ["refused"], "the roads table labels the module refused")

    def test_the_scan_covers_every_call_the_regex_census_it_replaced_flagged(self):
        """The old-versus-new comparison (review round 9: a replacement instrument covers at least what it replaced,
        and the proof is the old and the new run over one population). The census the scan replaced
        (_round8_regex_census, round 8's regex pair copied verbatim) and the scan run over every module the trio test
        reads and every PLANT_TABLE row: for each call the regex flags, the scan gives a site at the call's line, lists
        an unresolved entry whose expression contains the match, or refuses the module, or the match is one of three
        exclusions derived from the call (_regex_scan_comparison: a word a one-line binding named that resolves to no
        path at the call, a match inside a -c program, the CLI with a verb outside KERNEL_VERBS). A match in none of
        these reds the case, naming the module or row, the line and the match. The tree has no instance of a shape the
        scan once dropped, so the rows are where such a shape reds. The rows whose label says the regex missed them
        too are held to carrying no call it flags. Reported and asserting nothing: the rows whose sites
        the regex missed (B1 and the rest of round 8's silent half) and the rows whose regex match lies at no call of
        the ast (N11, N12). Over the tree the scan runs only on the modules the regex flags a call in, so the sites
        the regex missed are reported for the rows alone. Then the comparison is run against two plants it must red:
        a consumer call the regex flags (os.path.relpath of a name bound to the path, beside a listed sys.executable
        that does not cover it), and the refresh row with KERNEL_VERBS taken to name a verb bin/romp lacks."""
        text = _bin_romp_text()
        verbs_hold = not _verbs_bin_romp_lacks(KERNEL_VERBS, text)
        dropped, tree_flagged, rows_flagged, missed, not_calls = [], 0, 0, [], []
        for name, src in _census_modules(HERE, skip=(os.path.basename(__file__),)):
            d, _, _, flagged = _regex_scan_comparison(src, name, verbs_hold)
            dropped += [(name,) + x for x in d]
            tree_flagged += flagged
        for label, _, _, src in PLANT_TABLE:
            d, rm, nc, flagged = _regex_scan_comparison(src, "planted.py", verbs_hold, scan_all=True)
            dropped += [(label,) + x for x in d]
            rows_flagged += flagged
            missed += [label.split()[0]] if rm else []
            not_calls += [label.split()[0]] if nc else []
        self.assertTrue(tree_flagged and rows_flagged, "the regex census flagged no call over the tree (%d) or the rows (%d): "
                        "the comparison's population is empty" % (tree_flagged, rows_flagged))
        also_missed = {label.split()[0]: _regex_scan_comparison(src, "planted.py", verbs_hold, scan_all=True)[3]
                       for label, _, _, src in PLANT_TABLE if "the regex missed it too" in label}
        self.assertTrue(also_missed and not any(also_missed.values()), "the rows whose label says the regex missed them too, "
                        "each with no call the regex flags (row: flagged calls): %r" % also_missed)
        self.assertEqual(dropped, [], "calls the round-8 regex census flagged that the scan neither reads as a site nor lists, "
                         "and that no exclusion covers ((module or row, line, match, call); KERNEL_VERBS held to bin/romp: %s): "
                         "%r. Over %d flagged calls of the tree and %d of the rows; the rows whose sites the regex missed: %s; "
                         "the rows whose regex match lies at no call: %s" % (verbs_hold, dropped, tree_flagged, rows_flagged,
                                                                             missed, not_calls))
        consumer = 'KERNEL = os.path.join(BIN, "romp-kernel")\nsubprocess.run([sys.executable, os.path.relpath(KERNEL)])'
        scan = _SpawnScan(ast.parse(consumer), "planted.py")
        self.assertEqual((scan.sites(), [text for line, text, _ in scan.unresolved if line == 2]), ([], ["sys.executable"]),
                         "the consumer plant: no site, and sys.executable the one entry listed at the call")
        self.assertEqual([(line, match) for line, match, _ in _regex_scan_comparison(consumer, "planted.py", verbs_hold)[0]],
                         [(2, "KERNEL")], "a consumer call the regex flags is dropped by the scan, and the comparison names it "
                         "(the listed sys.executable at that call does not contain the match)")
        refresh = next(src for label, _, _, src in PLANT_TABLE if label.startswith("N26 "))
        self.assertEqual(_regex_scan_comparison(refresh, "planted.py", verbs_hold)[0], [], "the refresh row: the CLI with a verb "
                         "outside KERNEL_VERBS, excluded while every verb in it is one bin/romp dispatches")
        self.assertEqual(len(_regex_scan_comparison(refresh, "planted.py", False)[0]), 1, "...and not excluded with verbs_hold "
                         "False, the value the case passes when KERNEL_VERBS names a verb bin/romp lacks")

    def test_every_kernel_verb_is_a_verb_bin_romp_dispatches(self):
        """Existence only: each verb in KERNEL_VERBS is one bin/romp's top-level dispatch has (_bin_romp_verbs, read from
        bin/romp's text), so the CLI road never narrows to a verb the CLI lacks (review round 9: it read `kernel`,
        which bin/romp answers with an unknown-command exit). Whether a dispatched verb starts a kernel is not read
        here: row A3 (`romp up --foreground`, caught by the argv) holds that reading. The reader is run over a
        synthetic dispatch too, one of each form it reads and the forms it must not."""
        text = _bin_romp_text()
        verbs, _ = _bin_romp_verbs(text)
        self.assertTrue(verbs, "the dispatch read found no verb in bin/romp: the reader no longer matches its dispatch")
        self.assertEqual(_verbs_bin_romp_lacks(KERNEL_VERBS, text), [],
                         "KERNEL_VERBS names a verb bin/romp's top-level dispatch does not have (existence only; row A3 holds "
                         "whether the scan reads `romp up` as a kernel spawn); dispatched: %s" % sorted(verbs))
        self.assertEqual(_verbs_bin_romp_lacks(KERNEL_VERBS | {"kernel"}, text), ["kernel"], "a planted verb bin/romp lacks is named")
        synthetic = ('if [[ "${1:-}" == "alpha" || "${1:-}" == "--alpha" ]]; then\n    exit 0\nfi\n'
                     'if [[ "${1:-}" =~ ^(beta|gamma)$ ]]; then\n    exit 0\nfi\n'
                     'case "${1:-}" in\n    delta|--delta)   # an arm (with a comment)\n        case "$2" in\n            inner) ;;\n'
                     '        esac\n        ;;\n    -*) exit 2 ;;\n    *) exit 2 ;;\nesac\nif [[ "$2" == "omega" ]]; then\n    exit 0\nfi\n')
        self.assertEqual(_verbs_bin_romp_lacks({"alpha", "--alpha", "beta", "gamma", "delta", "--delta", "inner", "omega", "-x"}, synthetic),
                         ["-x", "inner", "omega"], "the reader takes the == and =~ tests of the first word and the top-level "
                         "arms, and neither a nested case's arm, a test of another word nor a catch-all arm")

    def test_the_module_that_loads_the_kernel_in_process_and_attaches_places_each_leg_of_the_trio_where_it_is_read(self):
        """Read by position from the module's ast, not by text (_placement_faults): the port is assigned at module level
        before the kernel loads (the kernel reads it at import); client-only is assigned before the load or in the setUp
        of every class that attaches or detaches; peers is assigned in each of those setUps and put back by a cleanup
        that setUp registers, and NEVER at module level. A module-level peers assignment is the leak of 2026-09-18 (the
        header); a tearDown-only restore is the hole of review round 1 (a subclass setUp that raises skips it)."""
        self.assertEqual(_placement_faults(ast.parse(_tunnels_source())), [])

    def test_the_placement_check_reds_on_a_planted_module_level_write_and_on_a_teardown_only_restore(self):
        """The check is run over synthetic copies of the real module so it is known to be able to fail (review round 1,
        2026-09-18): a module-level write of ROMP_POSTAL_PEERS restored before the load, in every shape a write takes
        (review round 2 widened the scan from the subscript and setdefault to update, |=, a name bound to os.environ and
        putenv: the subscript alone left a module-level update invisible), each copy faulting exactly once, for the
        write and nothing else; a planted update whose keys the scan cannot read is loud, naming the line, never a clean
        pass; and the restore moved back into a tearDown with no cleanup registered."""
        src = _tunnels_source()
        plants = (
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
        self.assertTrue(any("registers no cleanup" in f for f in faults), "tearDown-only restore: %r" % faults)
        self.assertEqual(len(faults), 2, "one fault per attaching class, nothing else: %r" % faults)

    def test_no_module_under_tests_writes_the_peers_setting_at_module_level(self):
        """The import-time half of the rule, held for every .py under tests/ (review round 1, 2026-09-18), walked
        recursively so fixtures/ is read too (941 files on 2026-09-18: 925 test_*.py, 13 helpers beside them and 3 under
        fixtures/; the glob is checked against an independent walk so no file is silently unscanned): no module-level
        write of ROMP_POSTAL_PEERS, module-level if/try/for/with bodies included, in every shape a write takes (review
        round 2: a subscript, setdefault, update of a literal or of a module-level name bound to one, |=, putenv, through
        os.environ or any name bound to it), and a write whose keys the scan cannot read fails here naming the file
        and line rather than passing unread. The per-test half (set in setUp, put back by a cleanup) is a convention,
        checked above for the tunnels module alone; tests/README.md says so."""
        paths = sorted(glob.glob(os.path.join(HERE, "**", "*.py"), recursive=True))
        walked = sorted(os.path.join(d, f) for d, _, fs in os.walk(HERE) for f in fs if f.endswith(".py"))
        self.assertEqual(paths, walked, "the glob walks every .py under tests/, subdirectories included: the set an os.walk finds")
        self.assertGreater(len(paths), 900, "the scan walks the whole tree, recursively: %d files (941 on 2026-09-18)" % len(paths))
        writers = []
        for path in paths:
            rel = os.path.relpath(path, HERE)
            tree = ast.parse(open(path, encoding="utf-8", errors="replace").read(), filename=path)
            if "ROMP_POSTAL_PEERS" in _module_level_env_writes(tree, rel):
                writers.append(rel)
        self.assertEqual(writers, [], "these modules write ROMP_POSTAL_PEERS at import; the kernel and the postal service "
                                      "read it at call time, and under xdist every worker imports every collected module")
        # the scan itself is known to see a planted write in every shape, bare and in an if body, and to ignore one inside a def
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
                      'os.putenv("ROMP_POSTAL_PEERS", "0")'):
            self.assertIn("ROMP_POSTAL_PEERS", _module_level_env_writes(ast.parse("import os\n" + shape + "\n"), "planted.py"), shape)
        unseen = _module_level_env_writes(ast.parse('import os\ndef setUp(self):\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n'), "planted.py")
        self.assertNotIn("ROMP_POSTAL_PEERS", unseen)
        # the one module-level update in the tree today reads its mapping through a name bound to a dict literal
        # (tests/test_update_banner_confirm_served.py's DEAD_PORTS): the scan reads the keys, and the module stays clean
        banner = "test_update_banner_confirm_served.py"
        seen = _module_level_env_writes(ast.parse(open(os.path.join(HERE, banner), encoding="utf-8", errors="replace").read()), banner)
        self.assertTrue({"ROMP_MANAGER_PORT", "ROMP_KERNEL_PORT", "ROMP_SERVE_PORT"} <= seen,
                        "%s updates os.environ from DEAD_PORTS at import; the scan reads the keys through the name: %r" % (banner, sorted(seen)))
        # a write the scan cannot read is loud, with the file and the line, never a clean pass
        for shape in ("os.environ.update(computed())", "os.environ.update(**saved)", "os.environ.update(saved, ROMP_X=\"1\")",
                      "os.environ |= saved", 'os.environ[name] = "0"', 'os.environ.setdefault(name, "0")', 'os.putenv(name, "0")',
                      "saved = dict(os.environ)\nos.environ.update(saved)",
                      'OFF = {"ROMP_POSTAL_PEERS": "0"}\nOFF = computed()\nos.environ.update(OFF)'):
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

    def test_importing_the_attaching_module_writes_no_peers_setting_and_its_setup_pins_one_for_the_test(self):
        """Executed, not read: a fresh interpreter pops ROMP_POSTAL_PEERS, imports tests/test_kernel_tunnels.py (which
        loads the kernel in-process against its own temp state and starts no bus) and reports the variable after the
        import, inside an attaching class's setUp, after its tearDown and after its cleanups with a value a shell might
        have left, and after a subclass setUp that raises past the peers write. Before 2026-09-18 the import alone
        wrote "0"; before review round 1 the raising setUp left the 0 behind (the restore was a tearDown)."""
        out = self._tunnels_probe()
        self.assertIsNone(out["after_import"], "importing the module writes no peers setting (the kernel reads it at call time; a write at import leaks under xdist)")
        self.assertEqual(out["in_setup"], "0", "an attaching class's setUp turns peers off for its test")
        self.assertEqual(out["after_teardown"], "0", "the value is still set when tearDown returns: the subclass's detach there reads it, and the restore is a cleanup, which runs after tearDown")
        self.assertEqual(out["after_cleanups"], "1", "...and the cleanup restores what it found")
        self.assertEqual(out["setup_raise_errors"], 1, "the planted subclass setUp raised, as an error on the case")
        self.assertEqual(out["after_setup_raise"], "1", "a subclass setUp that raises after the peers write still restores it: a tearDown restore is skipped on that path (review round 1, 2026-09-18)")

    def test_the_import_probe_reds_on_a_planted_module_level_peers_write(self):
        """The same planted writes, run: a copy of the module with `os.environ["ROMP_POSTAL_PEERS"] = "0"` restored
        before the load reports "0" after the import, and so does one with `os.environ.update(ROMP_POSTAL_PEERS="0")`
        there (the shape review round 2 found the static scan blind to), so the probe is known to see the leak it
        guards against (review rounds 1 and 2, 2026-09-18)."""
        for label, lines in (("assignment", 'os.environ["ROMP_POSTAL_PEERS"] = "0"\n'),
                             ("update", 'os.environ.update(ROMP_POSTAL_PEERS="0")\n')):
            out = self._tunnels_probe(_plant(_tunnels_source(), lines))
            self.assertEqual(out["after_import"], "0", "%s: the probe sees a module-level write at import" % label)
            self.assertEqual(out["after_cleanups"], "1", "%s: the planted copy's own cleanup still restores the shell's value" % label)

    def test_the_peer_notify_guard_test_carries_the_trio_around_the_call_it_forces_to_fail(self):
        src = open(os.path.join(HERE, "test_kernel.py"), encoding="utf-8", errors="replace").read()
        body = src[src.index("def test_notify_bus_peer_is_guarded"):src.index("class CheckinMechanics")]
        self.assertIn('os.environ.update(ROMP_POSTAL_CLIENT_ONLY="1", ROMP_POSTAL_PEERS="0", ROMP_POSTAL_PORT="1")', body,
                      "client-only with peers off and a port nothing can bind, for the call the refusal revives the bus from")
        self.assertLess(body.index("os.environ.update("), body.index("km._notify_bus_peer("), "…set before the call")
        self.assertIn("os.environ.pop(k, None)", body, "…and restored after it")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--roads"]:
        # `python tests/test_hermetic_kernel_postal.py --roads [directory]`: the per-module roads table, the unresolved
        # names and the summary counts (the census's population, derived by this one command)
        _print_roads(sys.argv[2] if len(sys.argv) > 2 else HERE, skip=(os.path.basename(__file__),))
    else:
        unittest.main()
