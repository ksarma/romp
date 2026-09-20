"""The link-drop lab's old-hub mint writes nothing into the clone it runs from (2026-09-19).

LinkDropOldLocal (tests/test_federated_linkdrop_served.py) needs a hub kernel and bundle from before PR 815; under
ROMP_LINKDROP_OLD_HUB_BUILD=1 it mints that checkout itself. Round 1 of the fork PR that added the lab found the mint was a
worktree of the clone every session on this box shares: an interrupted add (a SIGKILL, a timeout) leaves a record git locks
as "initializing" that neither a forced remove nor a repo-wide clearing of stale records reaches, and the teardown's fallback
ran that repo-wide clearing there, which can delete the records of worktrees the test never made. A test may not run a
repo-global mutation on a clone it shares. The mint is now a private clone under the lab's scratch (git clone --shared
--no-checkout: the objects are borrowed through an alternates file, nothing is written under the source's .git) checked out
detached at OLD_HUB_SHA, and teardown is the scratch's removal, with no git command against the source.

Pinned here against a SCRATCH repository (the lab module's ROOT, OLD_HUB_SHA and EXT are repointed for the test and restored;
the shared clone is never the subject): the source's worktree records and its .git/worktrees directory are byte-identical
before the mint, after it and after teardown, with no locked record at any of the three; the minted checkout is at the sha
and borrows the source's objects; an interrupted mint (git killed as the clone starts, the failure path) raises with git's
words and leaves the source's records untouched; every git command the mint runs is either the clone, which reads the
source, or bound by -C to a path under the lab, and none names a worktree, a record clearing or an object collection; the
class's teardown, spied the same way WITH a minted checkout present (round 3: spied with none, a teardown step conditioned
on the mint, the round-1 defect's own shape, was never exercised), runs no command at all (the lab's rmtree takes the
checkout); and no string constant in the lab module's source, in either quoting, is such an argv token (an ast walk, so a
spelling cannot slip past it). What the spies see is a rule over NAMES, not a list of commands: the recorder patched over
the lab module's `subprocess` attribute records the argv of every call to one of that module's spawning functions, `run`,
`Popen`, `call`, `check_call`, `check_output`, `getoutput` and `getstatusoutput` (SPAWNERS, pinned against this Python's
`subprocess.__all__`), each once (a shell string as one token), and hands the call to the real function; every other name
read through the attribute (PIPE, STDOUT, DEVNULL, TimeoutExpired, CompletedProcess) is delegated and unrecorded, so a
command reaches the record only through a recorded name. A token assembled at run time or joined into one shell string is
caught whichever recorded function the module used (round 4: the spies saw `run` alone, and round 1's defect re-planted as a
`Popen` with its tokens assembled passed every pin, the byte-identical records included, since the peer worktree's directory
was still alive; the fixer pass of that round found `call`, `check_call` and `check_output` reaching the real module through
the delegation unseen while this docstring said the record saw them, and the same plant as a `check_call` passed every pin).
What the recorder cannot see, a second census refuses by NODE over the parsed source of the lab module and of every module
it imports from this directory, transitively (_lab_modules, its import derivation reading every spelling of a sibling
import, bare, package-qualified or relative, and refusing a package sibling rather than dropping it): a program-starting
os function (OS_SPAWNERS, pinned against this Python's os module) as an attribute on any value, a bare call, an import from
os or a string constant; the other stdlib spawner families the same way (OTHER_SPAWNERS: pty.spawn, asyncio's
create_subprocess_exec and create_subprocess_shell, an event loop's subprocess_exec and subprocess_shell,
_posixsubprocess.fork_exec, os.fork and os.forkpty, each pinned against the module that carries it); a road to the subprocess
module other than `import subprocess` (an import under another name, a name imported from it, os under another name, the
bare name `subprocess` read anywhere but as the value of an attribute, an attribute named `subprocess` on any other value,
a constant "subprocess"); a spawning function of subprocess BOUND rather than called (`_run = subprocess.run`, a dict value,
a default argument, a functools.partial, a class attribute: round 5 found such a binding, made before the recorder is
installed, calls the real module past it); the reflective primitives (REFLECTIVE_CALLS and REFLECTIVE_ATTRS: exec, eval,
compile, __import__, vars, globals, locals; import_module, __getattribute__, __dict__, sys.modules, attrgetter; and getattr
over os) as nodes whatever their argument; and any import outside ALLOWED_IMPORTS, the modules the censused set uses
today, held equal to the imports in use so that a new module is a red until it is read. The recorder closes the alias
road on its own side too: before it is installed, _spy walks the lab module's namespace by IDENTITY (its globals, its own
classes' attributes, its functions' defaults and closure cells, partials, containers, instances of its own classes) and
refuses any object that IS a spawning function of the real subprocess module, however it was spelled (_bound_spawners).

What the census cannot see is stated as a rule, not a count: it refuses the nodes it enumerates and nothing else, so a road
to a process is unseen exactly when no enumerated node spells it. The class is a name that is not a whole node of the
parsed source: a spawning name reached through a reflective primitive the census does not enumerate (the enumerated ones
are refused whatever their argument, so exec over text that carries the spelling whole is refused at the exec, where the
earlier disclosure, which called this class "built text", let it pass). And on the recorder's side, a program a censused
module's own function starts through that module's own subprocess binding when the lab module calls the function: the
recorder patches the lab module's attribute alone, and the census reads that call as the module's own. Both are derived
where they are read, in the disclosure cell (_own_spawn_sites over the censused modules: the sibling labs' kernel boots and
lab_dist's builds, as the derivation prints them; the module objects _bound_spawners does not enter), and the derived list
is printed there, never carried here as a number or a name.

Synthetic: a scratch repository minted here, hostname TESTHOST; no kernel, no browser.
"""
import _posixsubprocess
import ast
import asyncio
import functools
import os
import pty
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import test_federated_linkdrop_served as L   # noqa: E402  the lab module: _mint_old_hub and the globals it reads

FORBIDDEN_ARGV = ("worktree", "prune", "gc")
# every public callable of the subprocess module that starts a process: what the recorder records, by name (the pin below
# checks the tuple against this Python's subprocess.__all__, so a spawning function added to the module is not delegated unseen)
SPAWNERS = ("run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput")
# every os function that starts a program, by name: what the recorder over the lab module's `subprocess` attribute cannot
# see, refused by the census below in the lab module and its imports from this directory (the tuple is pinned against this
# Python's os module, every name beginning spawn, exec or posix_spawn plus system and popen, so a member it lacks is a red)
OS_SPAWNERS = ("system", "popen",
               "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp",
               "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe")
# the other stdlib roads to a program, by the module that carries each and the attribute's name: refused as an attribute on
# any value and as a bare call wherever they appear (the same rule as OS_SPAWNERS, whose comment above keeps its own pin
# against the os module), and their modules are outside ALLOWED_IMPORTS, so the import is refused before the attribute is.
# Pinned against this Python's modules below: every name is an attribute of the module named for it (a loop's two are on
# asyncio.AbstractEventLoop). A fork is a process the recorder never sees, whatever it goes on to exec.
OTHER_SPAWNERS = {"pty": ("spawn",), "asyncio": ("create_subprocess_exec", "create_subprocess_shell"),
                  "asyncio.AbstractEventLoop": ("subprocess_exec", "subprocess_shell"), "_posixsubprocess": ("fork_exec",), "os": ("fork", "forkpty")}
# the modules the table is pinned against, imported statically (an import_module call here would read to
# tests/test_state_isolation_order.py as an in-process load of romp code, which this module never makes)
OTHER_SPAWNER_MODULES = {"pty": pty, "asyncio": asyncio, "_posixsubprocess": _posixsubprocess, "os": os}
# the reflective primitives a spawning name could be reached through without being a whole node of the source: refused as
# NODES, whatever their argument, so the road through them is closed at the primitive and not at the spelling it carries
# (round 5: `exec("import subprocess as _s; _s.run(...)")` passed a census that read the constant "subprocess" alone); a
# getattr whose first argument is the os module is refused the same way (a getattr on the lab module's `subprocess` is the
# recorder's, which sees the dynamic lookup)
REFLECTIVE_CALLS = ("exec", "eval", "compile", "__import__", "vars", "globals", "locals")
REFLECTIVE_ATTRS = ("import_module", "__getattribute__", "__dict__", "modules", "attrgetter")
# every module the censused set imports today, foreign to this directory (a sibling is walked, never listed): an import
# outside this tuple is refused, so a module that starts a program (pty, asyncio, multiprocessing, ctypes, _posixsubprocess)
# or reaches one (importlib, builtins, operator) is a red the moment it is imported; the cell holds the tuple EQUAL to the
# imports in use, so a name here that nothing imports is a red too
ALLOWED_IMPORTS = ("base64", "contextlib", "fcntl", "fnmatch", "hashlib", "http", "json", "os", "pathlib", "re", "select", "shlex",
                   "shutil", "signal", "socket", "subprocess", "sys", "tempfile", "threading", "time", "unittest", "urllib", "uuid")
LAB_MODULE = "test_federated_linkdrop_served"
PACKAGE = os.path.basename(HERE)   # this directory is a package (tests/__init__.py), so a sibling is importable as tests.x and as .x too
OTHER_NAMES = tuple(sorted({n for names in OTHER_SPAWNERS.values() for n in names}))


def _sibling_imports(src, package=PACKAGE):
    """The names the import statements of the parsed source could resolve to a module beside the lab module in this directory:
    a bare name (`import lab_dist`, `from lab_dist import x`, the spelling the lab modules use, resolved through sys.path), the
    same name qualified by this directory's package (`import tests.lab_dist`, `from tests import lab_dist`, `from tests.lab_dist
    import x`) and a one-level relative import (`from . import lab_dist`, `from .lab_dist import x`, the spelling
    tests/__init__.py uses). An import from above this directory (`from .. import x`) names nothing here; a foreign module's
    name (`import os`) is returned and left for the caller's file check to drop. The follow-up's fixer pass: the derivation read
    the bare spelling alone, so a helper carrying `os.popen`, imported into the lab module as `from tests import <helper>` or
    `import tests.<helper>`, passed the census cell."""
    names = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import):
            for a in n.names:
                parts = a.name.split(".")
                names.add(parts[1] if parts[0] == package and len(parts) > 1 else parts[0])
        elif isinstance(n, ast.ImportFrom):
            parts = n.module.split(".") if n.module else []
            if n.level == 0 and parts[:1] == [package]:
                parts = parts[1:]
            elif n.level > 1:
                continue
            if parts:
                names.add(parts[0])
            else:
                names.update(a.name for a in n.names)
    return names


def _lab_modules(root=LAB_MODULE, here=HERE):
    """The lab module and, transitively, every module it imports that lives beside it in this directory, {name: source},
    derived from the parsed import statements (every spelling _sibling_imports resolves, each naming a file here/x.py), so a
    helper the lab module grows is censused without anyone listing it. `here` is the directory (its basename the package the
    qualified spellings name); the composition pin hands it a synthetic one. A sibling that is a PACKAGE (here/x/__init__.py)
    is refused, never dropped (round 5: the file check dropped one, and a helper carrying `os.popen` in its __init__ passed the
    census): the walk reads modules, and a package sibling needs it extended before it can be imported here. A name that is
    neither a module nor a package here is a foreign module's, left for ALLOWED_IMPORTS."""
    out, todo, package = {}, [root], os.path.basename(here)
    while todo:
        name = todo.pop()
        path = os.path.join(here, name + ".py")
        if name in out:
            continue
        if not os.path.isfile(path):
            if os.path.isfile(os.path.join(here, name, "__init__.py")):
                raise AssertionError("a package sibling the census does not walk: %s (%s/%s/__init__.py); the walk reads modules, so extend it before importing a package here" % (name, package, name))
            continue
        with open(path, encoding="utf-8") as f:
            out[name] = f.read()
        todo += sorted(_sibling_imports(out[name], package))
    return out


def _commands_around_the_recorder(src, siblings=()):
    """Every node of the parsed source that is a road to a process around the recorder, as (line, form), keyed on the ROAD
    (round 5) and not on a spelling: an attribute read named as one of OS_SPAWNERS or OTHER_SPAWNERS on ANY value (`os.system`,
    `pty.spawn`, a renamed module and a nested attribute are refused alike, the safe side); a call to such a bare name, or its
    import (`from os import system`, `from os import *`, `from pty import spawn`); a spawning function of subprocess BOUND
    rather than called (`subprocess.run` anywhere but as the function of a call: an alias, a dict value, a default argument,
    a partial's first argument, a class attribute); the bare name `subprocess` read anywhere but as the value of an attribute
    (`_sp = subprocess`, `f(subprocess)`); an attribute named `subprocess` on any other value (`_dial.subprocess.run`); an
    import of the subprocess module or of os under another name, or of a name from subprocess; a constant "subprocess" or one
    equal to an OS_SPAWNERS name (the road through a string handed to a primitive); a call to one of REFLECTIVE_CALLS, an
    attribute named as one of REFLECTIVE_ATTRS, a getattr whose first argument is the os module, or an import of such a name,
    each refused as a node whatever its argument, so the text it carries is not what is matched; and an import of any module
    outside ALLOWED_IMPORTS that is not a sibling this census walks (`siblings`; a relative import is one by construction). A
    comment or a docstring is no node of these kinds, so the words in one do not count; a docstring is one constant equal to
    its whole text, so a docstring that names os.system is not equal to "system"."""
    found = []
    tree = ast.parse(src)
    parent = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[child] = node
    spawners = set(OS_SPAWNERS) | set(OTHER_NAMES)
    for n in ast.walk(tree):
        p = parent.get(n)
        if isinstance(n, ast.Attribute):
            if n.attr in spawners:
                found.append((n.lineno, "." + n.attr))
            elif n.attr == "subprocess":
                found.append((n.lineno, ".subprocess on another value"))
            elif n.attr in REFLECTIVE_ATTRS:
                found.append((n.lineno, "." + n.attr))
            elif isinstance(n.value, ast.Name) and n.value.id == "subprocess" and n.attr in SPAWNERS and not (isinstance(p, ast.Call) and p.func is n):
                found.append((n.lineno, "subprocess.%s bound, not called" % n.attr))
        elif isinstance(n, ast.Name) and n.id == "subprocess" and isinstance(n.ctx, ast.Load) and not (isinstance(p, ast.Attribute) and p.value is n):
            found.append((n.lineno, "subprocess read bare"))
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id in spawners:
                found.append((n.lineno, n.func.id + "("))
            elif n.func.id in REFLECTIVE_CALLS:
                found.append((n.lineno, n.func.id + "("))
            elif n.func.id == "getattr" and n.args and isinstance(n.args[0], ast.Name) and n.args[0].id == "os":
                found.append((n.lineno, "getattr(os,"))
        elif isinstance(n, ast.ImportFrom):
            top = n.module.split(".")[0] if n.module else ""
            names = [a.name for a in n.names]
            if n.module == "os" and any(a in spawners or a == "*" for a in names):
                found.append((n.lineno, "from os import " + ", ".join(names)))
            elif n.module and top == "subprocess":
                found.append((n.lineno, "from %s import %s" % (n.module, ", ".join(names))))
            elif n.module and any(a in OTHER_NAMES or a in REFLECTIVE_CALLS or a in REFLECTIVE_ATTRS for a in names):
                found.append((n.lineno, "from %s import %s" % (n.module, ", ".join(names))))
            if n.level == 0 and top not in ALLOWED_IMPORTS and top not in siblings and top != PACKAGE:
                found.append((n.lineno, "from %s import ... (a module ALLOWED_IMPORTS does not name)" % (n.module,)))
        elif isinstance(n, ast.Import):
            for a in n.names:
                top = a.name.split(".")[0]
                if top == "subprocess" and (a.asname or a.name != "subprocess"):
                    found.append((n.lineno, "import %s as %s" % (a.name, a.asname)))
                elif top == "os" and a.asname:
                    found.append((n.lineno, "import %s as %s" % (a.name, a.asname)))
                elif top not in ALLOWED_IMPORTS and top not in siblings and top != PACKAGE:
                    found.append((n.lineno, "import %s (a module ALLOWED_IMPORTS does not name)" % (a.name,)))
        elif isinstance(n, ast.Constant) and (n.value == "subprocess" or n.value in OS_SPAWNERS):
            found.append((n.lineno, '"%s"' % (n.value,)))
    return found


def _foreign_imports(mods):
    """The top-level names the censused modules import that are no sibling of theirs: what ALLOWED_IMPORTS must equal."""
    out = set()
    for src in mods.values():
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Import):
                out.update(a.name.split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                out.add(n.module.split(".")[0])
    return {name for name in out if name not in mods and name != PACKAGE}


def _own_spawn_sites(mods):
    """The DERIVED residual on the recorder's side: every call of a spawning function through a censused module's own
    `subprocess` binding in a module other than the lab module, as (module, line, function). The recorder patches the lab
    module's attribute alone, so a program one of these starts when the lab module calls the function is recorded by nothing;
    the census reads the call as the module's own. Printed by the disclosure cell, never counted in a docstring."""
    out = []
    for name, src in sorted(mods.items()):
        if name == LAB_MODULE:
            continue
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess" and n.func.attr in SPAWNERS:
                out.append((name, n.lineno, n.func.attr))
    return out


def _bound_spawners(module, depth=8):
    """Every object reachable from the module's namespace that IS a spawning function of the real subprocess module, by
    identity, as (path, name): the module's globals, its own classes' attributes, its functions' defaults, keyword defaults
    and closure cells, partials (function, arguments, keywords), staticmethods and classmethods, dicts, lists, tuples, sets,
    and the instance dicts of objects of its own classes, to `depth`. Keyed on the ROAD and not the spelling: a binding made
    before the recorder is installed (`_run = subprocess.run` at module level, a dict value, a default argument, a partial, a
    class attribute) calls the real module past the recorder however it was written, and this is what _spy refuses before it
    patches. Not entered, and returned beside the findings as the derived list of what this cannot see: other modules'
    namespaces (a module object is a boundary; the census over the parsed source reads the road to them) and objects of
    foreign classes."""
    spawners = {id(getattr(subprocess, n)): n for n in SPAWNERS}
    found, boundary, seen = [], [], set()

    def visit(obj, path, d):
        if id(obj) in spawners:
            found.append((path, spawners[id(obj)]))
            return
        if id(obj) in seen or d > depth:
            return
        seen.add(id(obj))
        if isinstance(obj, types.ModuleType):
            boundary.append(path)
        elif isinstance(obj, functools.partial):
            visit(obj.func, path + ".func", d + 1)
            for i, a in enumerate(obj.args):
                visit(a, "%s.args[%d]" % (path, i), d + 1)
            for k, v in (obj.keywords or {}).items():
                visit(v, "%s.keywords[%r]" % (path, k), d + 1)
        elif isinstance(obj, (staticmethod, classmethod)):
            visit(obj.__func__, path + ".__func__", d + 1)
        elif isinstance(obj, types.FunctionType):
            for i, v in enumerate(obj.__defaults__ or ()):
                visit(v, "%s.__defaults__[%d]" % (path, i), d + 1)
            for k, v in (obj.__kwdefaults__ or {}).items():
                visit(v, "%s.__kwdefaults__[%r]" % (path, k), d + 1)
            for i, cell in enumerate(obj.__closure__ or ()):
                try:
                    visit(cell.cell_contents, "%s.<closure %d>" % (path, i), d + 1)
                except ValueError:
                    pass   # an empty cell
        elif isinstance(obj, type):
            if obj.__module__ == module.__name__:
                for k, v in vars(obj).items():
                    visit(v, "%s.%s" % (path, k), d + 1)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                visit(v, "%s[%r]" % (path, k), d + 1)
        elif isinstance(obj, (list, tuple, set, frozenset)):
            for i, v in enumerate(obj):
                visit(v, "%s[%d]" % (path, i), d + 1)
        elif type(obj).__module__ == module.__name__ and hasattr(obj, "__dict__"):
            for k, v in vars(obj).items():
                visit(v, "%s.%s" % (path, k), d + 1)
    for name, obj in vars(module).items():
        if not name.startswith("__"):
            visit(obj, name, 0)
    return found, boundary


def _git(*args):
    """A git command for the test's own scratch, through this module's real `subprocess` (the spies replace the LAB module's
    `subprocess` attribute, so a command the test itself issues stays out of the record, whichever function it uses)."""
    p = subprocess.Popen(["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(timeout=60)
    if p.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(args), err.strip()))
    return out


class _Scratch:
    """A repository with two commits, an extension directory the mint symlinks into, and one linked worktree (a peer's
    record, so the record set the mint must leave alone is not empty)."""

    def __init__(self, test):
        self.root = tempfile.mkdtemp(prefix="linkdrop-mint-src-")
        test.addCleanup(shutil.rmtree, self.root, True)
        _git("init", "-q", "-b", "main", self.root)
        ident = ("-c", "user.name=lab", "-c", "user.email=lab@TESTHOST")
        os.makedirs(os.path.join(self.root, "vscode-extension"))
        with open(os.path.join(self.root, "vscode-extension", "package.json"), "w") as f:
            f.write("{}\n")
        _git("-C", self.root, "add", "vscode-extension/package.json")
        _git("-C", self.root, *ident, "commit", "-q", "-m", "the old main")
        self.old = _git("-C", self.root, "rev-parse", "HEAD").strip()
        with open(os.path.join(self.root, "later.txt"), "w") as f:
            f.write("after the old main\n")
        _git("-C", self.root, "add", "later.txt")
        _git("-C", self.root, *ident, "commit", "-q", "-m", "a later main")
        self.peer = self.root + "-peer"
        test.addCleanup(shutil.rmtree, self.peer, True)
        _git("-C", self.root, "worktree", "add", "-q", "--detach", self.peer, "HEAD")

    def records(self):
        """What a mint could disturb: the porcelain record list, the admin directory's entries, the locked lines."""
        porcelain = _git("-C", self.root, "worktree", "list", "--porcelain")
        admin = os.path.join(self.root, ".git", "worktrees")
        entries = sorted(os.listdir(admin)) if os.path.isdir(admin) else []
        locked = [ln for ln in porcelain.splitlines() if ln.startswith("locked")]
        return {"porcelain": porcelain, "admin": entries, "locked": locked}


class OldHubMintIsPrivate(unittest.TestCase):
    def setUp(self):
        self.src = _Scratch(self)
        saved = (L.ROOT, L.OLD_HUB_SHA, L.EXT)
        self.addCleanup(lambda: setattr(L, "ROOT", saved[0]))
        self.addCleanup(lambda: setattr(L, "OLD_HUB_SHA", saved[1]))
        self.addCleanup(lambda: setattr(L, "EXT", saved[2]))
        L.ROOT, L.OLD_HUB_SHA, L.EXT = self.src.root, self.src.old, os.path.join(self.src.root, "vscode-extension")
        self.lab = tempfile.mkdtemp(prefix="federated-linkdrop-")
        self.addCleanup(shutil.rmtree, self.lab, True)

        class Mint(L._LinkDrop):
            pass
        Mint.lab, Mint.old_hub_wt = self.lab, None
        self.Mint = Mint
        self.before = self.src.records()
        self.assertEqual(len(self.before["admin"]), 1, "the scratch holds one peer record before the mint: %r" % (self.before,))
        self.assertEqual(self.before["locked"], [], "…and nothing locked")

    def _spy(self, run=None):
        """One recording namespace to patch over the lab module's `subprocess` attribute: each spawning function of the module
        (SPAWNERS) appends the argv to one list (a shell string as one token) and hands the call to the real function (`run`,
        when given, stands in for the real `run`: the interrupted mint's drill); every other name (PIPE, STDOUT, DEVNULL,
        TimeoutExpired, CompletedProcess, which the lab module reads through the same attribute) delegates to the real
        module. One namespace over the attribute, never a second patch of `Popen` on the real module: `subprocess.run`,
        `call`, `check_call` and `check_output` start their process through `Popen` as their own module's global, so that
        spelling records every `run` twice (read as 4 != 2 on the mint pin), and for the same reason each recorded function
        records once here. The recorder exists for the shape round 4 found passing every pin: round 1's repo-global sweep
        re-planted at the top of the class's teardown as `subprocess.Popen(["git", "-C", ROOT, "workt" + "ree", "pr" +
        "une"]).communicate()`, a `Popen` the `run` spy never saw with tokens the ast census never sees; the fixer pass of
        that round re-planted it as `subprocess.check_call(...)`, which the two-name recorder delegated unseen. Neither plant
        can live in the repo; both are recorded as mutations in the builder's review note outside it (red on
        test_the_teardown_runs_no_command through this recorder). Round 5: a spawning function BOUND in the lab module before
        the patch (`_run = subprocess.run` at module level, a dict value, a default argument, a partial, a class attribute)
        calls the real module past any recorder over the attribute, so before patching, every recorder refuses such a binding
        by identity (_bound_spawners over the lab module's namespace), whatever spelling made it."""
        bound, boundary = _bound_spawners(L)
        self.assertEqual(bound, [], "a spawning function of the subprocess module is bound in the lab module's namespace before the recorder is installed "
                                    "(an alias, a dict value, a default argument, a partial, a class attribute, a closure), so a call through it reaches the real module "
                                    "past the recorder: %r (namespaces this walk does not enter, module objects the census reads the road to: %r)" % (bound, sorted(boundary)))
        seen = []
        real = subprocess

        class Recorder:
            def __getattr__(self, name):
                return getattr(real, name)

        def recording(name):
            target = run if (name == "run" and run is not None) else getattr(real, name)

            def spawn(cmd, *a, **k):
                seen.append([cmd] if isinstance(cmd, str) else list(cmd))
                return target(cmd, *a, **k)
            spawn.__name__ = name
            return staticmethod(spawn)
        for name in SPAWNERS:
            setattr(Recorder, name, recording(name))
        return seen, Recorder()

    def test_the_recorder_sees_every_spawning_function_once_and_delegates_the_rest(self):
        """The instrument itself (round 4's fixer pass, after a `check_call` sweep passed the `run`-and-`Popen` recorder): under
        the recorder each spawning function of the subprocess module records its argv exactly once (run, call, check_call and
        check_output start their process through the REAL module's Popen, so a recorder over `run` alone misses the others and
        a second patch of Popen doubles them), a shell string is recorded as one token, the names the lab module reads through
        the attribute are the real module's own objects, and SPAWNERS is every public callable of this Python's subprocess
        module that is not an exception class or CompletedProcess, so a spawning function added to the module is not
        delegated unseen."""
        public = {n for n in subprocess.__all__ if callable(getattr(subprocess, n))}
        not_spawning = {n for n in public if isinstance(getattr(subprocess, n), type) and n != "Popen"}   # CompletedProcess and the exception classes
        self.assertEqual(public - not_spawning, set(SPAWNERS), "SPAWNERS is every public callable of the subprocess module that starts a process")
        seen, recorder = self._spy()
        with mock.patch.object(L, "subprocess", recorder):
            for name in SPAWNERS:
                del seen[:]
                fn = getattr(L.subprocess, name)
                if name in ("getoutput", "getstatusoutput"):
                    fn("true")
                else:
                    p = fn(["true"], stdout=subprocess.DEVNULL) if name != "check_output" else fn(["true"])
                    if hasattr(p, "wait"):
                        p.wait()
                self.assertEqual(seen, [["true"]], "%s is recorded exactly once (a run, call, check_call or check_output recorded twice is the second-patch spelling): %r" % (name, seen))
            del seen[:]
            L.subprocess.run("true", shell=True, stdout=subprocess.DEVNULL)
            self.assertEqual(seen, [["true"]], "a shell string is recorded as one token: %r" % (seen,))
            for name in ("PIPE", "STDOUT", "DEVNULL", "TimeoutExpired", "CompletedProcess", "CalledProcessError"):
                self.assertIs(getattr(L.subprocess, name), getattr(subprocess, name), "%s is delegated to the real module" % name)

    def _assert_commands_are_private(self, seen, expect_commands=True):
        """Every git command the mint ran either reads the source (the clone) or is bound to a path under the lab; none
        carries a forbidden token. Derived from the spy's record, which must not be empty for a mint (expect_commands);
        a clean teardown runs none, and then the record is checked as it stands."""
        if expect_commands:
            self.assertTrue(seen, "the mint ran git (the spy saw its commands)")
        for cmd in seen:
            self.assertEqual(cmd[0], "git", cmd)
            self.assertEqual([t for t in cmd if t in FORBIDDEN_ARGV], [], "no worktree, record-clearing or collection command in the mint: %r" % (cmd,))
            if cmd[1] == "clone":
                self.assertEqual(cmd[-2], self.src.root, "the clone reads the source: %r" % (cmd,))
                self.assertTrue(cmd[-1].startswith(self.lab + os.sep), "…and writes under the lab: %r" % (cmd,))
            else:
                self.assertEqual(cmd[1], "-C", "every other command is bound by -C: %r" % (cmd,))
                self.assertTrue(cmd[2].startswith(self.lab + os.sep), "…to a path under the lab, never the source: %r" % (cmd,))

    def test_the_mint_registers_nothing_in_the_source_and_borrows_its_objects(self):
        seen, recorder = self._spy()
        with mock.patch.object(L, "subprocess", recorder):
            wt = self.Mint._mint_old_hub()
        self._assert_commands_are_private(seen)
        self.assertEqual(len(seen), 2, "the mint is one clone and one checkout: %r" % (seen,))
        after = self.src.records()
        self.assertEqual(after, self.before, "the source's worktree records are byte-identical after the mint")
        self.assertEqual(wt, os.path.join(self.lab, "oldhub"))
        self.assertEqual(self.Mint.old_hub_wt, wt)
        self.assertEqual(_git("-C", wt, "rev-parse", "HEAD").strip(), self.src.old, "the checkout is at OLD_HUB_SHA")
        self.assertTrue(os.path.isfile(os.path.join(wt, "vscode-extension", "package.json")), "…with the old main's tree")
        self.assertFalse(os.path.exists(os.path.join(wt, "later.txt")), "…and not the later main's")
        with open(os.path.join(wt, ".git", "objects", "info", "alternates")) as f:
            alt = f.read().strip()
        self.assertEqual(os.path.realpath(alt), os.path.realpath(os.path.join(self.src.root, ".git", "objects")), "the clone borrows the source's objects")
        self.assertTrue(os.path.islink(os.path.join(wt, "vscode-extension", "node_modules")), "the extension's node_modules is a symlink to this checkout's")
        shutil.rmtree(self.lab, ignore_errors=True)   # the class's teardown: the lab's rmtree, no git command
        self.assertEqual(self.src.records(), self.before, "…and byte-identical after teardown")

    def test_an_interrupted_mint_raises_and_leaves_the_source_untouched(self):
        def killed_at_the_clone(cmd, *a, **k):
            if cmd[:2] == ["git", "clone"]:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)   # the test's own Popen, not the lab's
                p.kill()   # the drill: the mint's git dies as the clone starts (a SIGKILL mid-mint, the failure path)
                out, err = p.communicate()
                return subprocess.CompletedProcess(cmd, p.returncode if p.returncode else -9, out, err or "killed as the clone started (the drill)")
            return subprocess.run(cmd, *a, **k)
        seen, recorder = self._spy(run=killed_at_the_clone)
        with mock.patch.object(L, "subprocess", recorder):
            with self.assertRaises(RuntimeError) as cm:
                self.Mint._mint_old_hub()
        self.assertIn(self.src.old, str(cm.exception), "the error names the sha: %s" % cm.exception)
        self.assertEqual(len(seen), 1, "the mint stopped at the killed clone: %r" % (seen,))
        self._assert_commands_are_private(seen)
        self.assertIsNone(self.Mint.old_hub_wt, "nothing is recorded as minted")
        self.assertEqual(self.src.records(), self.before, "the source's worktree records are byte-identical after the interrupted mint (nothing locked, nothing added)")
        shutil.rmtree(self.lab, ignore_errors=True)
        self.assertEqual(self.src.records(), self.before, "…and after the lab's removal")

    def test_a_sha_the_source_does_not_hold_is_an_error_with_gits_words(self):
        L.OLD_HUB_SHA = "0123456789abcdef0123456789abcdef01234567"
        with self.assertRaises(RuntimeError) as cm:
            self.Mint._mint_old_hub()
        self.assertIn(L.OLD_HUB_SHA, str(cm.exception))
        self.assertEqual(self.src.records(), self.before)

    def test_the_teardown_runs_no_command(self):
        """The class's teardown with a MINTED checkout present and nothing to stop (no procs, no door, no splice) runs no
        subprocess at all: the lab's rmtree takes the checkout, and no git command of the class names the source (round 1's
        teardown ran a repo-wide record clearing there). The mint runs first under the spy, so a teardown step conditioned
        on the mint (old_hub_wt set, the round-1 defect's own shape) is exercised; round 3 found the pin spied a teardown
        with nothing minted, which such a step never entered. Behavioural, so the spelling of an argv token cannot matter,
        and the recorder sees every spawning function of the subprocess module alike (SPAWNERS), so the function it was
        issued through cannot matter either (round 4: a `Popen` sweep with assembled tokens passed the `run` spy, and a
        `check_call` sweep passed the `run`-and-`Popen` recorder; _spy's docstring names the plants)."""
        seen, recorder = self._spy()
        with mock.patch.object(L, "subprocess", recorder):
            wt = self.Mint._mint_old_hub()
        self._assert_commands_are_private(seen)
        self.assertEqual(self.Mint.old_hub_wt, wt, "the mint recorded its checkout")
        self.assertTrue(os.path.isdir(os.path.join(wt, ".git")), "…and the checkout exists under the lab when the teardown runs: %r" % (wt,))
        del seen[:]
        with mock.patch.object(L, "subprocess", recorder):
            self.Mint.tearDownClass()
        self._assert_commands_are_private(seen, expect_commands=False)
        self.assertEqual(seen, [], "a teardown with the minted checkout present runs no command: %r" % (seen,))
        self.assertFalse(os.path.exists(self.lab), "…and the lab is gone, the checkout with it")
        self.assertEqual(self.src.records(), self.before, "the source's worktree records are byte-identical after teardown")

    def test_the_lab_module_names_no_forbidden_git_command(self):
        """No string constant in the lab module is a forbidden argv token, read from the parsed source (ast.Constant), so a
        single-quoted spelling is seen as the double-quoted one is (round 2: the pin matched one quoting and passed the
        other). A cheap census beside the two spies, and only a census: a token assembled at run time is theirs to catch."""
        with open(L.__file__, encoding="utf-8") as f:
            src = f.read()
        constants = {n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertTrue(constants, "the lab module was parsed and has string constants")
        found = sorted(tok for tok in FORBIDDEN_ARGV if tok in constants)
        self.assertEqual(found, [], "string constants in the lab module that name a worktree, a record clearing or a collection: %r" % (found,))
        self.assertNotIn("_remove_old_hub", src, "the teardown has no git step of its own: the lab's rmtree takes the checkout")

    def test_the_lab_module_and_its_imports_carry_no_road_to_a_process_the_census_enumerates(self):
        """The census the module docstring names, keyed on the road (round 5; round 4's fixer pass disclosed the first roads
        and its follow-up refused the os family): the recorder sees a command only through the lab module's `subprocess`
        attribute, so the lab module and every module it imports from this directory, transitively (_lab_modules, derived
        from the import statements), carry no node _commands_around_the_recorder refuses: no attribute named as a
        program-starting os function or as one of the other stdlib spawner families on any value, no call to or import of
        such a bare name, no spawning function of subprocess bound rather than called, no bare read of the name subprocess,
        no attribute named subprocess on another value, no import of subprocess or of os under another name or of a name
        from subprocess, no constant "subprocess" or one naming an os spawner, no reflective primitive as a node, no import
        outside ALLOWED_IMPORTS. OS_SPAWNERS is pinned against this Python's os module (every name beginning spawn, exec or
        posix_spawn, plus system and popen); the derivation must reach the lab module and lab_dist; and the detector is pinned
        on a synthetic source of each form it refuses and on the allowed spellings (import os, import subprocess,
        subprocess.run(...) called, subprocess.PIPE read, os.path.join, a sibling imported by any spelling, getattr on
        anything but os, the words in a docstring), so an empty census is a red and not a pass. The module object itself
        passed or bound anywhere (`getattr(subprocess, ...)` included, though the recorder would see that lookup) is a bare
        read and refused: the road is the module reaching a name, not what is then done with it. What the census cannot see is the rule in the module
        docstring and the derived lists in test_what_the_census_cannot_see_is_a_rule_with_its_list_derived."""
        wanted = {n for n in dir(os) if n.startswith(("spawn", "exec", "posix_spawn")) or n in ("system", "popen")}
        self.assertTrue(wanted, "this Python's os module names program-starting functions")
        self.assertEqual(sorted(wanted - set(OS_SPAWNERS)), [], "every program-starting os function of this Python is in OS_SPAWNERS")
        forms = (('import os\nos.system("true")\n', ".system"),
                 ('import os as o\no.popen("true")\n', "import os as o"),
                 ('import os as o\no.popen("true")\n', ".popen"),
                 ('import os\nos.posix_spawn("/bin/true", ["true"], {})\n', ".posix_spawn"),
                 ('from os import execv\n', "from os import execv"),
                 ('from os import *\n', "from os import *"),
                 ('def f(system):\n    system("true")\n', "system("),
                 ('import subprocess as sp\n', "import subprocess as sp"),
                 ('from subprocess import Popen as P\n', "from subprocess import Popen"),
                 ('import importlib\nimportlib.import_module("subprocess")\n', '"subprocess"'),
                 ('import importlib\nimportlib.import_module("subprocess")\n', ".import_module"),
                 ('import importlib\n', "import importlib (a module ALLOWED_IMPORTS does not name)"),
                 ('import sys\nsys.modules["subprocess"]\n', '"subprocess"'),
                 ('import sys\nsys.modules["sub" + "process"]\n', ".modules"),
                 ('import os\ngetattr(os, "system")("true")\n', '"system"'),
                 ('import os\ngetattr(os, "sys" + "tem")("true")\n', "getattr(os,"),
                 ('import os\nos.__dict__["execv"]\n', '"execv"'),
                 ('import os\nvars(os)["sys" + "tem"]\n', "vars("),
                 ('import subprocess\n_run = subprocess.run\n', "subprocess.run bound, not called"),
                 ('import subprocess\nSPAWN = {"run": subprocess.run}\n', "subprocess.run bound, not called"),
                 ('import subprocess\ndef f(run=subprocess.run):\n    return run\n', "subprocess.run bound, not called"),
                 ('import functools\nimport subprocess\n_s = functools.partial(subprocess.run, capture_output=True)\n', "subprocess.run bound, not called"),
                 ('import subprocess\nclass _Sp:\n    run = subprocess.run\n', "subprocess.run bound, not called"),
                 ('import subprocess\n_sp = subprocess\n', "subprocess read bare"),
                 ('import subprocess\ngetattr(subprocess, "ru" + "n")\n', "subprocess read bare"),
                 ('import subprocess\nsubprocess.__dict__["run"]\n', ".__dict__"),
                 ('import test_federated_dial_terms_served as _dial\n_dial.subprocess.run(["true"])\n', ".subprocess on another value"),
                 ('exec("import subprocess as _s; _s.run([\'true\'])")\n', "exec("),
                 ('eval("__imp" + "ort__")\n', "eval("),
                 ('__import__("sub" + "process")\n', "__import__("),
                 ('import pty\npty.spawn(["true"])\n', ".spawn"),
                 ('import pty\n', "import pty (a module ALLOWED_IMPORTS does not name)"),
                 ('import asyncio\nasyncio.create_subprocess_exec("true")\n', ".create_subprocess_exec"),
                 ('import asyncio\nloop.subprocess_shell(f, "true")\n', ".subprocess_shell"),
                 ('import _posixsubprocess\n_posixsubprocess.fork_exec()\n', ".fork_exec"),
                 ('import os\nos.fork()\n', ".fork"),
                 ('from pty import spawn\n', "from pty import spawn"),
                 ('from asyncio import create_subprocess_shell as sh\n', "from asyncio import create_subprocess_shell"),
                 ('import ctypes\nctypes.CDLL(None).system(b"true")\n', ".system"),
                 ('import operator\noperator.attrgetter("sys" + "tem")\n', ".attrgetter"),
                 ('from importlib import import_module\n', "from importlib import import_module"))
        for src, form in forms:
            with self.subTest(form=form, src=src):
                hits = _commands_around_the_recorder(src, siblings=("test_federated_dial_terms_served",))
                self.assertTrue(any(form in h[1] for h in hits), "the detector refuses %r as %r: %r" % (src, form, hits))
        allowed = ('import os\nimport subprocess\nimport lab_dist\nfrom . import lab_dist_stub\nfrom tests import fs_clock\n'
                   'subprocess.run(["true"], stdout=subprocess.PIPE)\np = subprocess.Popen(["true"])\nos.path.join("a", "b")\n'
                   'getattr(cls, "procs", [])\ngetattr(type(self), "result", None)\n"""os.system in a docstring; exec and eval too"""\n')
        self.assertEqual(_commands_around_the_recorder(allowed, siblings=("lab_dist", "fs_clock")), [], "the allowed spellings, and the words in a docstring, are not refused")
        mods = _lab_modules()
        self.assertTrue({LAB_MODULE, "lab_dist"} <= set(mods), "the derivation reaches the lab module and lab_dist: %r" % sorted(mods))
        found = {name: hits for name, src in sorted(mods.items()) for hits in [_commands_around_the_recorder(src, siblings=set(mods))] if hits}
        self.assertEqual(found, {}, "a node the census refuses (a road to a process it enumerates: the module docstring states the rule and what "
                                    "stays outside it) in the lab module or a module it imports from this directory (censused: %s): %r"
                                    % (", ".join(sorted(mods)), found))

    def test_the_spawner_families_and_the_import_allow_list_are_pinned_against_this_python_and_the_tree(self):
        """OTHER_SPAWNERS names a real attribute of the module it is filed under on this Python (a name the module lacks, or a
        module absent here, is a red naming it: the table is not a guess), and every family the census refuses by attribute
        is also refused by import, since its module is outside ALLOWED_IMPORTS; ALLOWED_IMPORTS equals the foreign imports the
        censused modules make today (a module added or dropped in one of them is a red until the tuple says so), and holds no
        module that starts a program or reaches one by reflection."""
        for modname, names in OTHER_SPAWNERS.items():
            with self.subTest(module=modname):
                top, _, attr = modname.partition(".")
                mod = OTHER_SPAWNER_MODULES[top]
                holder = getattr(mod, attr) if attr else mod
                self.assertEqual([n for n in names if not hasattr(holder, n)], [], "every name filed under %s is its attribute on this Python" % modname)
                self.assertNotIn(top, ALLOWED_IMPORTS + ("os",) if top != "os" else (), "a spawner family's module is outside the import allow-list: %s" % top)
        mods = _lab_modules()
        self.assertEqual(sorted(_foreign_imports(mods)), sorted(ALLOWED_IMPORTS), "ALLOWED_IMPORTS is exactly the foreign imports the censused modules make (%s)" % ", ".join(sorted(mods)))
        self.assertEqual([m for m in ("pty", "asyncio", "_posixsubprocess", "multiprocessing", "ctypes", "importlib", "builtins", "operator") if m in ALLOWED_IMPORTS], [],
                         "no module that starts a program or reaches one by reflection is allowed")

    def test_the_recorder_refuses_a_spawning_function_bound_before_it_is_installed(self):
        """The recorder's side of the alias road (round 5): _bound_spawners over a synthetic module finds, by identity and by
        path, an alias at module level, a dict value, a default argument, a keyword default, a functools.partial, a class
        attribute of the module's own class, a closure cell and a staticmethod, and reports the module objects it does not
        enter as the boundary; a module that reads subprocess.run at call time (a lambda, a decorator, a function body) binds
        nothing early and is clean; the lab module itself is clean, which is what every _spy asserts before it patches, so a
        binding planted there reds every recorder pin (the review record outside the repo runs the plants through them)."""
        m = types.ModuleType("linkdrop_synthetic_module")
        m.subprocess, m.os = subprocess, os
        m._run = subprocess.run
        m.SPAWN = {"run": subprocess.Popen}
        exec("def _sweep(run=subprocess.run):\n    return run\ndef _kw(*, call=subprocess.call):\n    return call\n"
             "def _mk():\n    f = subprocess.check_call\n    return lambda c: f(c)\n_closed = _mk()\n"
             "class _Sp:\n    out = staticmethod(subprocess.check_output)\n    go = subprocess.getoutput\n"
             "_L = lambda c: subprocess.run(c)\ndef _late(c):\n    return subprocess.Popen(c)\n", vars(m))
        m._Sp.__module__ = m.__name__
        m._partial = functools.partial(subprocess.getstatusoutput)
        found, boundary = _bound_spawners(m)
        self.assertEqual(sorted(found), sorted([("_run", "run"), ("SPAWN['run']", "Popen"), ("_sweep.__defaults__[0]", "run"), ("_kw.__kwdefaults__['call']", "call"),
                                                ("_closed.<closure 0>", "check_call"), ("_Sp.out.__func__", "check_output"), ("_Sp.go", "getoutput"), ("_partial.func", "getstatusoutput")]),
                         "every early binding is found by identity and named by its path")
        self.assertEqual(sorted(boundary), ["os", "subprocess"], "the module objects are the boundary the walk does not enter, reported beside the findings")
        clean = types.ModuleType("linkdrop_synthetic_clean")
        clean.subprocess = subprocess
        exec("_L = lambda c: subprocess.run(c)\ndef _late(c):\n    return subprocess.Popen(c)\n", vars(clean))
        self.assertEqual(_bound_spawners(clean)[0], [], "a read of the attribute at call time binds nothing early: the recorder sees it")
        bound, boundary = _bound_spawners(L)
        self.assertEqual(bound, [], "the lab module binds no spawning function before the recorder is installed: %r" % (bound,))
        self.assertTrue({"subprocess", "os", "lab_dist"} <= set(boundary), "the lab module's module objects are the walk's boundary: %r" % (sorted(boundary),))

    def test_what_the_census_cannot_see_is_a_rule_with_its_list_derived(self):
        """The disclosure, derived where it is read and never counted (round 5: the earlier docstring said two roads remained
        unseen and named a third's class wrongly). The rule is the module docstring's: the census refuses the nodes it
        enumerates and nothing else. Derived here: the censused modules' own calls of a spawning function through their own
        subprocess binding, which the recorder over the lab module's attribute does not reach when the lab module calls them
        (the sibling labs' kernel boots and lab_dist's builds, as the derivation reads them; every such site is outside the
        lab module by construction, and no name is held here: the list is what the derivation prints), and the module objects
        _bound_spawners does not enter. Each list is printed in an assertion's message, so a run's record carries the derived
        residual as it stood."""
        mods = _lab_modules()
        sites = _own_spawn_sites(mods)
        self.assertTrue(sites, "the derivation reads the censused modules' own spawning calls: %r" % (sites,))
        self.assertEqual([site for site in sites if site[0] == LAB_MODULE], [], "the lab module's own calls are the recorder's, never a residual")
        self.assertTrue(all(name in mods and name != LAB_MODULE for name, _, _ in sites),
                        "the residual on the recorder's side, derived: a program these modules' own functions start through their own subprocess "
                        "binding when the lab module calls them, unseen by the recorder over the lab module's attribute (module, line, function): %r" % (sites,))
        bound, boundary = _bound_spawners(L)
        self.assertEqual(bound, [])
        self.assertTrue(boundary, "the identity walk names the module objects it does not enter: %r" % (sorted(boundary),))
        self.assertTrue(all(isinstance(getattr(L, name.split(".")[0]), types.ModuleType) for name in boundary), "each boundary entry is a module object: %r" % (sorted(boundary),))

    def test_the_import_derivation_reads_every_spelling_of_a_sibling_import(self):
        """The census walks a module by the file its import names, whatever the spelling. The follow-up's fixer pass: the
        derivation followed `import x` and `from x import y` alone, so a helper reached as `from tests import x`, `import
        tests.x` or `from . import x` (the spelling tests/__init__.py itself uses) fell outside the census with no red, and a
        helper carrying `os.popen`, imported into the lab module the first two ways, passed the census cell. Each spelling of a
        sibling import resolves to the sibling's bare name; an import from above this directory resolves to nothing; a foreign
        module's name is left for _lab_modules's file check to drop (`import os` names `os`; no HERE/os.py exists)."""
        self.assertTrue(os.path.isfile(os.path.join(HERE, "__init__.py")), "this directory is a package, so the qualified and relative spellings import")
        self.assertEqual(PACKAGE, "tests", "the qualified spellings below are written for this directory's package name")
        cases = (("import lab_dist\n", {"lab_dist"}),
                 ("import lab_dist as d\n", {"lab_dist"}),
                 ("from lab_dist import x\n", {"lab_dist"}),
                 ("import tests.lab_dist\n", {"lab_dist"}),
                 ("import tests.lab_dist as d\n", {"lab_dist"}),
                 ("from tests import lab_dist\n", {"lab_dist"}),
                 ("from tests import lab_dist, fs_clock\n", {"lab_dist", "fs_clock"}),
                 ("from tests.lab_dist import x\n", {"lab_dist"}),
                 ("from . import lab_dist\n", {"lab_dist"}),
                 ("from .lab_dist import x\n", {"lab_dist"}),
                 ("from .. import kernel\n", set()),
                 ("import os\nfrom os.path import join\n", {"os"}))
        for src, want in cases:
            with self.subTest(src=src.strip()):
                self.assertEqual(_sibling_imports(src), want, "the sibling names %r resolves to" % (src,))
        self.assertNotIn("os", _lab_modules(), "the file check drops a foreign name")

    def test_the_census_walks_a_sibling_whatever_spelling_imports_it(self):
        """The composition: _lab_modules over a synthetic package directory (its basename `tests`, like this one) whose root
        imports four siblings, one by each spelling, one of which imports a fifth through a qualified spelling, beside a sixth
        nobody imports, reaches the five and not the sixth. Pinned apart from the resolver's own cells because a walk that
        never called the resolver (the derivation before the follow-up's fixer pass) passes those cells and the census alike:
        no module in this directory is reached through a qualified or relative spelling today, so only a synthetic one shows
        the walk following them."""
        top = tempfile.mkdtemp(prefix="linkdrop-census-")
        self.addCleanup(shutil.rmtree, top, True)
        here = os.path.join(top, "tests")
        os.makedirs(here)
        files = {"root": "import bare\nfrom tests import qualified_from\nimport tests.qualified_import as q\nfrom . import relative\n",
                 "bare": "import os\n", "qualified_from": "from tests.deeper import x\n", "qualified_import": "", "relative": "",
                 "deeper": "import os\n", "unimported": "import os\n"}
        for name, src in files.items():
            with open(os.path.join(here, name + ".py"), "w", encoding="utf-8") as f:
                f.write(src)
        self.assertEqual(sorted(_lab_modules("root", here)), ["bare", "deeper", "qualified_from", "qualified_import", "relative", "root"],
                         "the walk reaches a sibling by every spelling, transitively, and no unimported one")
        # a PACKAGE sibling (round 5): the walk refuses it by name rather than dropping it, so a helper in a package's __init__
        # cannot pass the census unread
        os.makedirs(os.path.join(here, "packaged"))
        with open(os.path.join(here, "packaged", "__init__.py"), "w", encoding="utf-8") as f:
            f.write("import os\n")
        with open(os.path.join(here, "root.py"), "a", encoding="utf-8") as f:
            f.write("import packaged\n")
        with self.assertRaises(AssertionError, msg="a package sibling is refused, not dropped") as cm:
            _lab_modules("root", here)
        self.assertIn("a package sibling the census does not walk: packaged", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
