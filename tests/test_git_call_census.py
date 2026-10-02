#!/usr/bin/env python3
"""The census behind the 02:43Z ruling on PR 926, item 1(a), in the form the closing check wf_3b100f5e-b38 ruled (its item
7): it reads LAUNCH SITES, not argv spellings. Every place scripts/sweep.py and scripts/batch.py can start a process is a
launch site, and each one is on a named allowlist (ALLOWED), with its reason and the number of sites its function holds;
a site anywhere else, or one more in a listed function, is a finding, whatever it would run. run_git, the one helper
each script starts git through (a bounded wait, GIT_BOUND, killed with its process group at the bound, the repository
named: GIT_DIR, GIT_COMMON_DIR and GIT_WORK_TREE set and GIT_CEILING_DIRECTORIES above it), is the first entry in each.
The census it replaces looked for git in argvs, and missed git spelled through `shutil.which('git') or 'git'`,
os.path.join, str.split and five more idioms (the closing check's census finding): an argv it could not read was a git
call it did not see. Where processes start does not depend on how their argv is spelled.

The census reads each file's source with ast and runs none of it; it imports only standard library modules its tables
name, to follow a chain of names through them. A launch site is a reference, called or not, to:
  - a standard library name that starts a process (LAUNCH_RULES): subprocess's launchers (every attribute of subprocess
    but its constants, exceptions and CompletedProcess), os.system, popen, fork, forkpty, startfile and the exec*, spawn*
    and posix_spawn* families (and the same names of posix and nt, which os takes them from), asyncio.create_subprocess_exec
    and _shell (and an event loop's subprocess_exec and subprocess_shell, by method name), pty.fork and spawn,
    concurrent.futures' ProcessPoolExecutor, any attribute of multiprocessing, webbrowser, pydoc, platform, ctypes (but
    get_errno and set_errno), _posixsubprocess and _winapi, and the builtins help (pydoc's pager is a process) and
    globals, vars and locals (each hands on a namespace that holds the file's modules: globals()['subprocess'].run);
  - such a name reached through a module that holds one of those modules (shutil.os.system, tempfile._os.popen,
    os.path.os.system): each dotted name is walked from its first module, a name that is itself a module is followed
    (the live module's attribute, or, where this interpreter's module lacks it, a module a table names spelled as the
    attribute is, its leading underscores dropped: shlex.os is gone in Python 3.14), and the name after each module is
    read against that module's rule (the verify pass at the wf_3b100f5e-b38 build, its code finding 3: the census read
    only the first name after a known module, and eight of the inert modules hold os, sys or posix);
  - a call through a ctypes library handle (an attribute of a name bound to one), since native code can start a process;
  - such a module handed on whole (a bare reference to it, getattr on it with a name that is not a literal, or its
    __dict__), and so a module that holds one (shutil), and a name imported from one with `from ... import`, at the
    import;
  - one of the file's OPEN runners: a helper on the allowlist that starts whatever its caller hands it (batch.py's _run
    and run_tool, sweep.py's probe, run_leg and _build_venv's step). Each reference to one is a site, allowed only from
    the callers ALLOWED names, so a new caller of _run is a finding as a new subprocess.run would be.
A reference counts where it is written: `r = subprocess.run` and functools.partial(subprocess.run, ...) are sites in
their function, so a launcher reached through a name or a partial is not missed.

Code a file loads at run time is read the same way (LOAD_RULES, the "load" sites): importlib's import_module,
spec_from_file_location and spec_from_loader, importlib.machinery, runpy, zipimport, sys.modules, a loader's exec_module
or load_module, and the builtins exec, eval, compile and __import__. Each is on the allowlist with the file it loads
(LOADS), and that file must be one the census reads (SCRIPTS): batch.py's sweep_reader loads scripts/sweep.py, so a
launch in sweep.py is a launch in batch.py's process too. So is every module either file imports that resolves to a file
in this repository, and every module imported at all must be classified (LAUNCH_RULES, LOAD_RULES or INERT_MODULES), so
an import the census does not know whether to read is a finding rather than a module it skips.

The census holds where processes start; what an allowed site runs is a named line of the source, for review. The
behavioural pins in tests/test_sweep_runner.py and tests/test_batch_tool.py hold run_git and run_tool to their bound and
to the repository they name.
"""
import ast
import collections
import importlib
import os
import tempfile
import types
import unittest
from pathlib import Path

# Hermetic state BEFORE the loads (tests/test_state_isolation_order.py): this module imports only standard library modules
# its tables name (_live), but the ratchet counts every in-process load, import_module among them, and a module that
# loads pays these two lines rather than the ratchet resolving what it loads.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ("scripts/sweep.py", "scripts/batch.py")

# os's names that start a process: the exec*, spawn* and posix_spawn* families by prefix (os has no other names so
# spelled), and these. posix and nt, the modules os takes them from, are read by the same rule (OS_LIKE).
OS_LAUNCHERS = {"system", "popen", "fork", "forkpty", "startfile"}
OS_LIKE = {"os", "posix", "nt"}
# module: (the names of it that start a process, or None for every name but `inert`; inert). Any name of a module here
# starting with a double underscore (its __dict__, say) counts too, and so does the module handed on whole.
LAUNCH_RULES = {
    "subprocess": (None, {"PIPE", "DEVNULL", "STDOUT", "TimeoutExpired", "CompletedProcess", "SubprocessError",
                          "CalledProcessError"}),
    "os": (OS_LAUNCHERS, set()),
    "posix": (OS_LAUNCHERS, set()),
    "nt": (OS_LAUNCHERS, set()),
    "asyncio": ({"create_subprocess_exec", "create_subprocess_shell"}, set()),
    "pty": ({"fork", "spawn"}, set()),
    "concurrent.futures": ({"ProcessPoolExecutor", "process"}, set()),
    "multiprocessing": (None, set()),
    "webbrowser": (None, set()),
    "pydoc": (None, set()),
    "platform": (None, set()),
    "ctypes": (None, {"get_errno", "set_errno"}),
    "_posixsubprocess": (None, set()),
    "_winapi": (None, set()),
    "builtins": ({"help", "globals", "vars", "locals"}, set()),
}
# The same for the names that load and run code at run time.
LOAD_RULES = {
    "importlib": ({"import_module", "reload", "__import__"}, set()),
    "importlib.util": ({"spec_from_file_location", "spec_from_loader", "LazyLoader"}, set()),
    "importlib.machinery": (None, set()),
    "runpy": (None, set()),
    "zipimport": (None, set()),
    "sys": ({"modules"}, set()),
    "builtins": ({"exec", "eval", "compile", "__import__"}, set()),
}
# Method names that start a process or run code whatever object they are read from: an event loop's, a loader's.
LAUNCH_METHODS = {"subprocess_exec", "subprocess_shell"}
LOAD_METHODS = {"exec_module", "load_module"}
# Builtin names that run code, read as such unless the file binds the name itself.
LOAD_BUILTINS = {"exec", "eval", "compile", "__import__", "__builtins__"}
# Builtin names read as launch sites unless the file binds the name itself: help, whose pager pydoc starts as a process,
# and globals, vars and locals, which hand on a namespace that holds the file's modules (globals()['subprocess'].run).
LAUNCH_BUILTINS = {"help", "globals", "vars", "locals"}
# The standard library modules the two files import that start no process and load no code, so the census need not
# read their names. A module imported that is in none of the three tables is a finding.
INERT_MODULES = {"argparse", "collections", "datetime", "errno", "fcntl", "functools", "glob", "hashlib", "heapq", "json",
                 "random", "re", "shlex", "shutil", "signal", "stat", "string", "tempfile", "time", "urllib.parse",
                 "urllib.request"}

# Every launch site in each file, by (the function it is in, its kind) -> (the number of such sites there, why each is
# legitimate). The kind is "launch", "load", or the name of the OPEN runner a caller references. run_git's own launch is
# the first entry: the census is not vacuous while it is seen. A function written inside another is named by both,
# outer first (_build_venv.step).
ALLOWED = {
    "scripts/sweep.py": {
        ("run_git", "launch"): (1, "the helper every git call goes through: GIT_BOUND, the process group killed at the "
                                   "bound, the repository named explicitly"),
        ("tool_versions", "launch"): (1, "each tool's version flag (git --version among them) as the legs' own tool, from "
                                         "their PATH and in a leg's environment, bounded at 60 s, under the stop hold; "
                                         "it reads no repository"),
        ("probe", "launch"): (1, "OPEN: the PROBE in an interpreter, --python's or a venv's, bounded at 120 s, under the "
                                 "stop hold"),
        ("_build_venv.step", "launch"): (1, "OPEN: one step of a venv's build (python -m venv, pip install, get-pip.py), "
                                            "bounded at SDK_STEP_TIMEOUT, under the stop hold"),
        ("run_leg", "launch"): (1, "OPEN, the legs' launcher: a leg's command in its checkout and its own process group, "
                                   "under the stop hold, which the runner reaps and stops"),
        ("_become_subreaper", "launch"): (2, "ctypes loads the C library and calls prctl(PR_SET_CHILD_SUBREAPER) through "
                                             "it, the one native call the runner makes"),
        ("_venv_check", "probe"): (1, "the PROBE in a venv the runner built, to check it still holds its build"),
        ("_venv_environment", "probe"): (1, "the PROBE in the interpreter a leg's environment is built from"),
        ("_venv_build", "probe"): (1, "the PROBE in a venv just built, to record what it holds"),
        ("_build_venv", "step"): (4, "the venv's creation (with ensurepip, or without pip and then get-pip.py) and its "
                                     "install steps, read from ci.yml"),
        ("_run_locked", "run_leg"): (1, "each leg of the run, in its group's checkout"),
        ("_run_locked.run_setup", "run_leg"): (1, "npm ci as a group's setup, run as the deps leg runs"),
        ("_run_locked.block_rest.mark", "run_leg"): (1, "a leg a failed setup blocks, which run_leg records as blocked and "
                                                        "does not start"),
    },
    "scripts/batch.py": {
        ("run_git", "launch"): (1, "the helper every git call goes through: GIT_BOUND, the process group killed at the "
                                   "bound, the repository named explicitly"),
        ("_run", "launch"): (1, "OPEN, the runner for gh, whose callers are named below, under the stop hold"),
        ("run_tool", "launch"): (1, "OPEN, the runner for the processes that run git in the clone (the ledger script, "
                                    "scripts/pr-orphans.sh): run_git's bound, process-group kill and repository"),
        ("run_command", "launch"): (1, "OPEN, the runner for bisect's command, under the stop hold and unbounded on "
                                       "purpose: a test command can rightly take longer than any git call"),
        ("cmd_bisect", "run_command"): (3, "the user's bisect command at the tip, at the base and at each step"),
        ("sweep_reader", "load"): (2, "scripts/sweep.py, loaded from beside this file (spec_from_file_location and "
                                      "exec_module) for its reader and excuse rule"),
        ("gh", "_run"): (1, "gh, the program gh_bin() finds"),
        ("cmd_summarize", "_run"): (2, "gh pr edit and gh pr create, the program gh_bin() finds"),
        ("convert_ledger_rows", "run_tool"): (1, "the ledger script's import of a row, in the batch worktree"),
        ("ledger_check_on_branch", "run_tool"): (1, "the ledger script's check, in the ledger check's temporary tree"),
        ("cmd_finish", "run_tool"): (1, "scripts/pr-orphans.sh, in the clone"),
    },
}
# The helpers on ALLOWED that start whatever their caller hands them (a program or a command from a parameter): each
# reference to one is a site of that runner's kind, in the function it is written in.
OPEN = {"scripts/sweep.py": {"probe", "run_leg", "_build_venv.step"}, "scripts/batch.py": {"_run", "run_tool", "run_command"}}
# The closing check wf_fb19febe-36b, its item 4: every process either script starts is started under the stop hold, so
# every "launch" site is held (unheld_launches), but these, which start no process: (function, why).
NOT_A_PROCESS = {"scripts/sweep.py": {"_become_subreaper": "ctypes loads the C library and calls prctl through it, the "
                                                           "one native call the runner makes; no process starts"},
                 "scripts/batch.py": {}}
# The file each allowed load site's function loads; each must be in SCRIPTS.
LOADS = {"scripts/sweep.py": {}, "scripts/batch.py": {"sweep_reader": "scripts/sweep.py"}}


def _index(tree):
    """(nodes, parent, owner): every node, each node's parent, and the function or class each node is in, by qualified
    name (outer.inner, Class.method; None at module level). A def's decorators and defaults are read as its own."""
    nodes, parent, owner = [tree], {}, {}

    def visit(node, qual):
        for child in ast.iter_child_nodes(node):
            nodes.append(child)
            parent[id(child)] = node
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                inner = child.name if qual is None else "%s.%s" % (qual, child.name)
                owner[id(child)] = inner
                visit(child, inner)
            else:
                owner[id(child)] = qual
                visit(child, qual)
    visit(tree, None)
    return nodes, parent, owner


def _bindings(nodes):
    """(modules, direct): a name bound by `import` -> the module it names; a name bound by `from M import N` -> M.N."""
    modules, direct = {}, {}
    for n in nodes:
        if isinstance(n, ast.Import):
            for a in n.names:
                modules[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            for a in n.names:
                if a.name != "*":
                    direct[a.asname or a.name] = "%s.%s" % (n.module, a.name)
    return modules, direct


# The modules a table names, and their top-level names, for the walk in classify.
_RULED = set(LAUNCH_RULES) | set(LOAD_RULES)
_RULED_TOP = {m for m in _RULED if "." not in m}


def _live(name):
    """The module `name` imported, when its top-level package is one a table names (so nothing else is imported: a module
    the census does not know is never run), or None when it is not, or does not import on this interpreter."""
    if name.split(".")[0] not in {m.split(".")[0] for m in _RULED | INERT_MODULES}:
        return None
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def _kind_of(module, name):
    """"launch", "load" or None for `module`.`name` read against the module's rules, each table in turn; `name` None is
    the module handed on whole, and a double-underscore name of a ruled module counts as that."""
    for kind, rules in (("launch", LAUNCH_RULES), ("load", LOAD_RULES)):
        if module not in rules:
            continue
        names, inert = rules[module]
        if name is None or name.startswith("__"):
            return kind
        if module in OS_LIKE:
            if name in names or name.startswith(("exec", "spawn", "posix_spawn")):
                return kind
        elif names is None:
            if name not in inert:
                return kind
        elif name in names:
            return kind
    return None


_MISSING = object()


def _follow(module, obj, name):
    """(the module's name, the live module or None) of `module`.`name` when that is a module, else None: the live
    attribute, when this interpreter's `module` (`obj`) has it; else its submodule of that name; else, by name, a module
    a table names, spelled as the attribute is or with its leading underscores dropped, so shutil.os, tempfile._os and
    shutil.posix are read as os and posix, and so is shlex.os, which shlex has before Python 3.14 and not in it."""
    if obj is not None:
        val = getattr(obj, name, _MISSING)
        if isinstance(val, types.ModuleType):
            return val.__name__, val
        if val is not _MISSING:
            return None
        sub = _live(module + "." + name)
        if sub is not None:
            return sub.__name__, sub
    if module + "." + name in _RULED:
        return module + "." + name, _live(module + "." + name)
    for spelled in (name, name.lstrip("_")):
        if spelled in _RULED_TOP:
            return spelled, _live(spelled)
    return None


def _hands_on(module, obj):
    """The kind of site a module handed on whole is: its own when a table names it; else, when this interpreter's module
    (`obj`) holds a module a table names (shutil holds os and posix, tempfile holds os as _os), that module's kind,
    launch first, since a name of it then reaches the launcher (getattr(shutil, name), shutil.__dict__['os']); else
    None (stat, json and time hold none)."""
    kind = _kind_of(module, None)
    if kind or obj is None:
        return kind
    held = {_kind_of(v.__name__, None) for v in vars(obj).values() if isinstance(v, types.ModuleType)}
    return "launch" if "launch" in held else "load" if "load" in held else None


def classify(dotted):
    """"launch", "load" or None for the dotted name `dotted` (module.name..., as the file spells it). The chain is walked
    from its first module: at each module, the name that follows is read against that module's rule (_kind_of); one that
    starts nothing but is itself a module is followed (_follow), so a launcher reached through a module that holds os
    (shutil.os.system, os.path.os.system, tempfile._os.popen) is read as os's. A chain that ends at a module, or at a
    double-underscore name of one (its __dict__), hands that module on whole (_hands_on)."""
    parts = dotted.split(".")
    module, obj = parts[0], _live(parts[0])
    for name in parts[1:]:
        kind = _kind_of(module, name)
        if kind:
            return kind
        if name.startswith("__"):
            return _hands_on(module, obj)
        nxt = _follow(module, obj, name)
        if nxt is None:
            return None
        module, obj = nxt
    return _hands_on(module, obj)


def launch_sites(source, open_runners=()):
    """Every launch site in `source` (the module docstring says what one is), as a sorted list of (line, the function it
    is in or None, kind, the text): kind "launch", "load", or the name of the runner of `open_runners` it references."""
    nodes, parent, owner = _index(ast.parse(source))
    modules, direct = _bindings(nodes)
    # the names the file binds itself (a builtin of LOAD_BUILTINS so bound is not the builtin)
    bound = {n.id for n in nodes if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)} | {
        n.name for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    sites = set()

    def add(node, kind):
        sites.add((node.lineno, owner.get(id(node)), kind, ast.unparse(node)[:120]))

    def dotted(node):
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if not isinstance(node, ast.Name):
            return None
        root = modules.get(node.id) or direct.get(node.id)
        return ".".join([root] + parts[::-1]) if root else None

    def outermost(node):
        up = parent.get(id(node))
        return not (isinstance(up, ast.Attribute) and up.value is node)

    # names bound to a ctypes library handle, by the function they are bound in
    handles = {(owner.get(id(n)), t.id) for n in nodes if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
               and (dotted(n.value.func) or "").startswith("ctypes.") for t in n.targets if isinstance(t, ast.Name)}
    for n in nodes:
        if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            for a in n.names:
                kind = classify(n.module if a.name == "*" else "%s.%s" % (n.module, a.name))
                if kind:
                    add(n, kind)
        elif isinstance(n, (ast.Attribute, ast.Name)) and isinstance(getattr(n, "ctx", None), ast.Load) and outermost(n):
            d = dotted(n)
            up = parent.get(id(n))
            if d is not None and isinstance(up, ast.Call) and isinstance(up.func, ast.Name) and up.func.id == "getattr" \
                    and up.args and up.args[0] is n:
                name = up.args[1] if len(up.args) > 1 else None
                d = d + "." + name.value if isinstance(name, ast.Constant) and isinstance(name.value, str) else d
            kind = classify(d) if d is not None else None
            if kind:
                add(n, kind)
                continue
            if isinstance(n, ast.Name) and n.id not in bound and n.id not in modules and n.id not in direct:
                if n.id in LOAD_BUILTINS:
                    add(n, "load")
                elif n.id in LAUNCH_BUILTINS:
                    add(n, "launch")
        if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load):
            if n.attr in LAUNCH_METHODS or (isinstance(n.value, ast.Name) and (owner.get(id(n)), n.value.id) in handles):
                if dotted(n) is None or not classify(dotted(n)):
                    add(n, "launch")
            elif n.attr in LOAD_METHODS and (dotted(n) is None or not classify(dotted(n))):
                add(n, "load")
    names = [n for n in nodes if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)]
    for runner in open_runners:
        outer, _dot, name = runner.rpartition(".")
        for n in names:
            if n.id != name:
                continue
            where = owner.get(id(n))
            if where == runner or (where or "").startswith(runner + "."):
                continue                                    # the runner's own body
            if outer and not (where == outer or (where or "").startswith(outer + ".")):
                continue                                    # a nested runner is visible only inside the function it is in
            add(n, name)
    return sorted(sites, key=lambda s: (s[0], str(s[1]), s[2], s[3]))


def census(source, allowed, open_runners=()):
    """The findings for `source` against `allowed` ({(function, kind): (count, why)}): each launch site whose function and
    kind no entry names, and each entry whose function holds another number of sites of its kind than it says (one
    more is a new launch; none is an entry the code no longer needs). Each finding is (line or None, text)."""
    sites = launch_sites(source, open_runners)
    seen = collections.Counter((fn, kind) for _l, fn, kind, _t in sites)
    findings = [(line, "a %s site in %s, on no allowlist: %s" % (kind, fn or "the module's top level", text))
                for line, fn, kind, text in sites if (fn, kind) not in allowed]
    findings += [(None, "%s holds %d %s site%s, and the allowlist says %d" % (fn, seen[(fn, kind)], kind,
                                                                              "" if seen[(fn, kind)] == 1 else "s", n))
                 for (fn, kind), (n, _why) in sorted(allowed.items()) if seen[(fn, kind)] != n]
    return findings


def imported_modules(source):
    """(line, module, level) for each module `source` imports (`from M import N` imports M, and M.N when N is a module
    of a table here); level is the relative import's dots."""
    tables = set(LAUNCH_RULES) | set(LOAD_RULES) | INERT_MODULES
    out = []
    for n in ast.walk(ast.parse(source)):
        if isinstance(n, ast.Import):
            out.extend((n.lineno, a.name, 0) for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            out.append((n.lineno, n.module or "", n.level))
            if not n.level:
                out.extend((n.lineno, "%s.%s" % (n.module, a.name), 0) for a in n.names
                           if "%s.%s" % (n.module, a.name) in tables)
    return out


def _known(module):
    tables = set(LAUNCH_RULES) | set(LOAD_RULES) | INERT_MODULES
    parts = module.split(".")
    return module in tables or any(".".join(parts[:i]) in set(LAUNCH_RULES) | set(LOAD_RULES) for i in range(1, len(parts)))


def repository_file(module):
    """The file of this repository `module` resolves to, as a path relative to ROOT, from the scripts' directory (the
    first entry of sys.path when a script runs) or the repository's root; None for a module that is not the
    repository's."""
    top = module.split(".")[0]
    for base in ("scripts", ""):
        d = ROOT / base if base else ROOT
        for cand in (d / (top + ".py"), d / top):
            if cand.exists():
                return str(cand.relative_to(ROOT))
    return None


def import_findings(source):
    """(line, text) for each import of `source` the census cannot follow: a relative import, a module of this
    repository that is not a file the census reads (SCRIPTS), and a module none of its tables classifies."""
    out = []
    for line, module, level in imported_modules(source):
        if level:
            out.append((line, "a relative import (%s%s), which the census cannot resolve" % ("." * level, module)))
            continue
        local = repository_file(module)
        if local is not None:
            if local not in SCRIPTS:
                out.append((line, "imports %s, this repository's %s, which the census does not read" % (module, local)))
        elif not _known(module):
            out.append((line, "imports %s, which the census does not classify (LAUNCH_RULES, LOAD_RULES, INERT_MODULES)"
                        % module))
    return out


# Launches planted at the end of a script's real source, each in a function named planted or at the top level; every one
# is a finding whatever it runs. The first eight are the spellings of git the closing check found the argv census missing.
PLANTS = {
    "git through shutil.which or a default": ("GITB = shutil.which('git') or 'git'\ndef planted():\n"
                                              "    subprocess.run([GITB, 'status'])\n"),
    "git from the environment or a default": "def planted():\n    subprocess.run([os.environ.get('ROMP_GIT') or 'git', 'status'])\n",
    "git from a conditional": "def planted(x):\n    subprocess.run(['git' if x else 'git', 'status'])\n",
    "git from a table": "TOOLS = {'git': 'git'}\ndef planted():\n    subprocess.run([TOOLS['git'], 'status'])\n",
    "git through os.path.join": "def planted():\n    subprocess.run([os.path.join('/usr/bin', 'git'), 'status'])\n",
    "git through pathlib": "import pathlib\ndef planted():\n    subprocess.run([pathlib.Path('/usr/bin/git'), 'status'])\n",
    "git through str.split": "def planted():\n    subprocess.run('git status'.split())\n",
    "git through shlex.split": "def planted(d):\n    subprocess.run(shlex.split(f'git -C {d} status'))\n",
    "a program that is not git": "def planted():\n    subprocess.run(['ls', '-l'])\n",
    "an argv from a parameter": "def planted(argv):\n    return subprocess.run(argv)\n",
    "Popen of a shell text": "def planted(text):\n    return subprocess.Popen(text, shell=True)\n",
    "check_output": "def planted(argv):\n    return subprocess.check_output(argv)\n",
    "getoutput": "def planted(text):\n    return subprocess.getoutput(text)\n",
    "os.system": "def planted(text):\n    os.system(text)\n",
    "os.popen": "def planted(text):\n    return os.popen(text).read()\n",
    "os.execvp": "def planted(argv):\n    os.execvp(argv[0], argv)\n",
    "os.spawnlp": "def planted(p):\n    os.spawnlp(os.P_WAIT, p, p)\n",
    "os.posix_spawn": "def planted(p, argv):\n    os.posix_spawn(p, argv, os.environ)\n",
    "os.fork": "def planted():\n    return os.fork()\n",
    "asyncio's exec": "import asyncio\nasync def planted(argv):\n    await asyncio.create_subprocess_exec(*argv)\n",
    "asyncio's shell": "import asyncio\nasync def planted(text):\n    await asyncio.create_subprocess_shell(text)\n",
    "an event loop's subprocess_exec": "async def planted(loop, argv):\n    await loop.subprocess_exec(lambda: None, *argv)\n",
    "pty.spawn": "import pty\ndef planted(argv):\n    pty.spawn(argv)\n",
    "multiprocessing": "import multiprocessing\ndef planted(f):\n    multiprocessing.Process(target=f).start()\n",
    "a process pool": "import concurrent.futures\ndef planted(f):\n    concurrent.futures.ProcessPoolExecutor().submit(f)\n",
    "webbrowser": "import webbrowser\ndef planted(url):\n    webbrowser.open(url)\n",
    "a call through ctypes": "import ctypes\ndef planted():\n    ctypes.CDLL(None).system(b'true')\n",
    "a module alias": "import subprocess as _sp\ndef planted(argv):\n    _sp.run(argv)\n",
    "a name imported from subprocess": "from subprocess import run as _r\ndef planted(argv):\n    _r(argv)\n",
    "a launcher bound to a name": "def planted(argv):\n    r = subprocess.run\n    r(argv)\n",
    "a partial": "import functools\ndef planted(argv):\n    functools.partial(subprocess.run, shell=True)(argv)\n",
    "getattr with a literal name": "def planted(argv):\n    getattr(subprocess, 'run')(argv)\n",
    "getattr with a computed name": "def planted(argv, name):\n    getattr(subprocess, name)(argv)\n",
    "the module handed on": "def planted(argv):\n    m = subprocess\n    m.run(argv)\n",
    "a module's __dict__": "def planted(text):\n    os.__dict__['system'](text)\n",
    "sys.modules": "def planted(argv):\n    sys.modules['subprocess'].run(argv)\n",
    "importlib.import_module": "import importlib\ndef planted(argv):\n    importlib.import_module('subprocess').run(argv)\n",
    "__import__": "def planted(argv):\n    __import__('subprocess').run(argv)\n",
    "exec of source text": "def planted(argv):\n    exec('import subprocess; subprocess.run(argv)')\n",
    "a file loaded by path": ("import importlib.util\ndef planted(path):\n"
                              "    spec = importlib.util.spec_from_file_location('m', path)\n"),
    # Spellings that reach a launcher through a module that holds os or posix, or through a namespace (the verify pass at
    # the wf_3b100f5e-b38 build, its code finding 3): the census before it found none of these. Each imports what it
    # uses, so each is a launch in either script.
    "os through shutil": "import shutil\ndef planted(t):\n    shutil.os.system(t)\n",
    "posix through shutil": "import shutil\ndef planted(t):\n    shutil.posix.system(t)\n",
    "os through tempfile's _os": "import tempfile\ndef planted(t):\n    return tempfile._os.popen(t).read()\n",
    "os through os.path": "def planted(t):\n    os.path.os.system(t)\n",
    "os through glob": "import glob\ndef planted(a):\n    glob.os.execvp(a[0], a)\n",
    "os through random's _os": "import random\ndef planted():\n    return random._os.fork()\n",
    "os through argparse's _os": "import argparse\ndef planted(t):\n    argparse._os.system(t)\n",
    "os through shlex": "import shlex\ndef planted(a):\n    shlex.os.posix_spawnp(a[0], a, {})\n",
    "os through urllib.request": "import urllib.request\ndef planted(t):\n    urllib.request.os.system(t)\n",
    "globals() and subprocess": "def planted(a):\n    globals()['subprocess'].run(a)\n",
    "globals() and os": "def planted(t):\n    globals()['os'].system(t)\n",
    "help, whose pager is a process": "def planted(x):\n    help(x)\n",
    "posix imported": "import posix\ndef planted(t):\n    posix.system(t)\n",
    "os imported from shutil": "from shutil import os as _o\ndef planted(t):\n    _o.system(t)\n",
    "a module that holds os, handed on": "import shutil\ndef planted(t):\n    m = shutil\n    m.os.system(t)\n",
    "getattr on a module that holds os": "import shutil\ndef planted(t, n):\n    getattr(shutil, n).system(t)\n",
    "the __dict__ of a module that holds os": "import shutil\ndef planted(t):\n    shutil.__dict__['os'].system(t)\n",
    "vars() of a module": "import shutil\ndef planted(t):\n    vars(shutil)['os'].system(t)\n",
    "locals()": "def planted(t, mod):\n    return locals()['mod'].run(t)\n",
    "builtins.help": "import builtins\ndef planted(x):\n    builtins.help(x)\n",
    "os.path imported whole": "import os.path as osp\ndef planted(t):\n    osp.os.system(t)\n",
    "at the top level": "subprocess.run(['true'])\n",
    "in a lambda": "planted = lambda argv: subprocess.run(argv)\n",
    "in a class body": "class Planted:\n    RUN = subprocess.run\n",
}
# A caller of one of the file's OPEN runners that the allowlist does not name, each planted at the end of its source.
OPEN_PLANTS = {
    "scripts/sweep.py": {"probe": "def planted(python, env):\n    return probe(python, env)\n",
                         "run_leg": "def planted(*a):\n    return run_leg(*a)\n"},
    "scripts/batch.py": {"_run": "def planted():\n    return _run(['true'])\n",
                         "run_tool": "def planted(root):\n    return run_tool(['true'], root)\n",
                         "_run bound to a name": "def planted():\n    r = _run\n    return r(['true'])\n",
                         "run_command": "def planted(root):\n    return run_command(['true'], root)\n"},
}
# One more launch written into an allowed function: (the text it goes before or after, the text with it), per file.
EXTRA_IN_ALLOWED = {
    "scripts/sweep.py": ("    return out\n\n\ndef npm_builtin(ctx):",
                         "    subprocess.run(['true'])\n    return out\n\n\ndef npm_builtin(ctx):"),
    "scripts/batch.py": ("    return _run([gh_bin(), *args], cwd=cwd, check=check)\n",
                         "    _run(['true'])\n    return _run([gh_bin(), *args], cwd=cwd, check=check)\n"),
}


def _calls(stmt, name):
    """Whether the statement `stmt` is a bare call of the function `name`: `name()`."""
    return (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name)
            and stmt.value.func.id == name and not stmt.value.args and not stmt.value.keywords)


def _held(node, parent):
    """Whether `node` is in the body of a try statement that comes right after a `_hold_stops()` statement and has a
    handler whose first statement is `_release_stops()`: the shape that starts a process under the stop hold (run_git's).
    The walk up stops at the function `node` is in, so a hold outside it does not count."""
    child, up = node, parent.get(id(node))
    while up is not None and not isinstance(up, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
        if isinstance(up, ast.Try) and any(child is st for st in up.body):
            holder = parent.get(id(up))
            for field in ("body", "orelse", "finalbody"):
                seq = getattr(holder, field, None)
                if isinstance(seq, list) and any(st is up for st in seq):
                    i = next(k for k, st in enumerate(seq) if st is up)
                    if (i > 0 and _calls(seq[i - 1], "_hold_stops")
                            and any(h.body and _calls(h.body[0], "_release_stops") for h in up.handlers)):
                        return True
        child, up = up, parent.get(id(up))
    return False


def unheld_launches(source):
    """Every "launch" site of `source` (launch_sites: a reference to a standard library name that starts a process) that
    is not started under the stop hold (_held), as (line, the function it is in or None, the text). A launcher bound to
    a name, or handed on, is not in a held start, so it is one."""
    tree = ast.parse(source)
    nodes, parent, _owner = _index(tree)
    wanted = {(line, text) for line, _fn, kind, text in launch_sites(source) if kind == "launch"}
    found = []
    for n in nodes:
        if getattr(n, "lineno", None) is None or not isinstance(n, (ast.Attribute, ast.Name, ast.ImportFrom)):
            continue
        key = (n.lineno, ast.unparse(n)[:120])
        if key in wanted and not _held(n, parent):
            found.append((n.lineno, _owner.get(id(n)), key[1]))
            wanted.discard(key)
    return sorted(found, key=lambda f: (f[0], str(f[1]), f[2]))


# Plants for the held rule, each written over its script's real source (old, new): a launch site whose hold is removed.
UNHELD_PLANTS = {
    "scripts/sweep.py": {
        "run_git's hold removed": ("    argv = [\"git\", *args]\n    _hold_stops()\n    try:\n        p = subprocess.Popen(",
                                   "    argv = [\"git\", *args]\n    pass\n    try:\n        p = subprocess.Popen("),
        "probe's hold removed": ("        _hold_stops()\n        try:\n            proc = subprocess.Popen(argv,",
                                 "        pass\n        try:\n            proc = subprocess.Popen(argv,"),
    },
    "scripts/batch.py": {
        "run_command's hold removed": ("    _hold_stops()\n    try:\n        p = subprocess.Popen(cmd, cwd=cwd)\n",
                                       "    pass\n    try:\n        p = subprocess.Popen(cmd, cwd=cwd)\n"),
        "bisect's command through subprocess.run, as before the closing check wf_fb19febe-36b": (
            "    if run_command(args.cmd, wt) == 0:", "    if subprocess.run(args.cmd, cwd=wt).returncode == 0:"),
    },
}


class LaunchSiteCensus(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text()

    def test_every_launch_site_in_both_scripts_is_on_the_allowlist(self):
        """Each file's launch sites are exactly the allowlist's: no site outside it, and each listed function holds the
        number of sites its entry says (run_git's one launch among them, so a census that read nothing fails here)."""
        for rel in SCRIPTS:
            with self.subTest(script=rel):
                self.assertEqual(census(self.read(rel), ALLOWED[rel], OPEN[rel]), [])

    def test_the_allowlist_is_consistent(self):
        """Every OPEN runner has its own launch on the allowlist, every runner kind there is an OPEN runner's, the load
        sites' functions are the ones LOADS names, each loading a file the census reads, and every entry gives a count
        above zero and a reason."""
        for rel in SCRIPTS:
            with self.subTest(script=rel):
                kinds = {kind for _fn, kind in ALLOWED[rel]}
                for runner in OPEN[rel]:
                    self.assertIn((runner, "launch"), ALLOWED[rel])
                self.assertEqual(kinds - {"launch", "load"}, {r.rpartition(".")[2] for r in OPEN[rel]})
                self.assertEqual({fn for fn, kind in ALLOWED[rel] if kind == "load"}, set(LOADS[rel]))
                for loaded in LOADS[rel].values():
                    self.assertIn(loaded, SCRIPTS)
                # every entry says how many sites its function holds and why each is legitimate (the verify pass at
                # the wf_3b100f5e-b38 build, its code finding 6: every reason blanked, the census stayed green)
                for (fn, kind), (count, why) in ALLOWED[rel].items():
                    self.assertTrue(isinstance(count, int) and count > 0, (fn, kind, count))
                    self.assertTrue(isinstance(why, str) and why.strip(), "the entry %s, %s gives no reason" % (fn, kind))

    def test_every_module_either_script_imports_is_read_or_classified(self):
        """A module of this repository either script imports is a file the census reads, and every other module it
        imports is classified, so no launch hides in a helper module the census skips."""
        for rel in SCRIPTS:
            with self.subTest(script=rel):
                self.assertEqual(import_findings(self.read(rel)), [])

    def test_a_launch_planted_outside_the_allowlist_is_found_whatever_it_runs(self):
        """The census's red: each launch in PLANTS, appended to each script's real source, is found at a line the plant
        added. The argv census before it found none of the first eight (git spelled in ways it did not read) and none of
        the plants that start something other than git."""
        for rel in SCRIPTS:
            base = self.read(rel)
            first = len(base.splitlines()) + 2
            for label, plant in PLANTS.items():
                with self.subTest(script=rel, plant=label):
                    found = census(base + "\n" + plant, ALLOWED[rel], OPEN[rel])
                    self.assertTrue(found, "the census missed %s planted in %s" % (label, rel))
                    self.assertTrue(all(line is not None and line >= first for line, _w in found), found)

    def test_a_new_caller_of_an_open_runner_is_found(self):
        """A reference to batch.py's _run or run_tool, or to sweep.py's probe or run_leg, from a function the allowlist
        does not name is a finding, whatever it hands the runner."""
        for rel, plants in OPEN_PLANTS.items():
            base = self.read(rel)
            first = len(base.splitlines()) + 2
            for label, plant in plants.items():
                with self.subTest(script=rel, plant=label):
                    found = census(base + "\n" + plant, ALLOWED[rel], OPEN[rel])
                    self.assertTrue(found, "the census missed a new caller of %s in %s" % (label, rel))
                    self.assertTrue(all(line is not None and line >= first for line, _w in found), found)

    def test_one_more_launch_in_an_allowed_function_is_found(self):
        """A second subprocess.run in tool_versions, and a second _run in gh, each change their function's count from
        the allowlist's, which is a finding naming the function."""
        for rel, (old, new) in EXTRA_IN_ALLOWED.items():
            with self.subTest(script=rel):
                base = self.read(rel)
                planted = base.replace(old, new, 1)
                self.assertNotEqual(planted, base, "premise: the plant went in")
                found = census(planted, ALLOWED[rel], OPEN[rel])
                fn = "tool_versions" if rel == "scripts/sweep.py" else "gh"
                self.assertTrue(any(line is None and text.startswith(fn + " holds 2 ") for line, text in found), found)

    def test_an_entry_the_code_no_longer_needs_is_found(self):
        """An allowlist entry whose function holds none of its sites (the launch removed, the function renamed) is a
        finding, so the list follows the code."""
        source = "import subprocess\ndef run_git(args):\n    return subprocess.Popen(['git', *args])\n"
        allowed = {("run_git", "launch"): (1, "the helper"), ("gone", "launch"): (1, "a function that is no more")}
        self.assertEqual(census(source, allowed), [(None, "gone holds 0 launch sites, and the allowlist says 1")])

    def test_an_import_the_census_cannot_follow_is_found(self):
        """A relative import, a module of this repository the census does not read (kernel), and a module no table
        classifies are each a finding; one the census reads (sweep, beside batch.py) and a classified one are not."""
        for plant, want in (("from . import helper\n", "a relative import"),
                            ("import kernel\n", "imports kernel, this repository's kernel"),
                            ("import xmlrpc.client\n", "imports xmlrpc.client, which the census does not classify"),
                            ("import sweep\n", None), ("import subprocess as sp\n", None),
                            ("from multiprocessing import pool\n", None)):
            with self.subTest(plant=plant):
                found = import_findings(plant)
                if want is None:
                    self.assertEqual(found, [])
                else:
                    self.assertEqual(len(found), 1, found)
                    self.assertTrue(found[0][1].startswith(want), found)

    def test_every_launch_site_starts_its_process_under_the_stop_hold(self):
        """The closing check wf_fb19febe-36b, its item 4: every process either script starts is started under the stop
        hold, so a stop that arrives while it starts is raised inside the try that ends it. Every launch site in each
        file is held (_held: right after `_hold_stops()`, in a try whose handler starts with `_release_stops()`), but
        those NOT_A_PROCESS names; the behavioural pins (the START_WINDOW_DRIVER pins in tests/test_sweep_runner.py and
        tests/test_batch_tool.py) hold what the shape does."""
        for rel in SCRIPTS:
            with self.subTest(script=rel):
                source = self.read(rel)
                launches = [s for s in launch_sites(source) if s[2] == "launch"]
                self.assertTrue(any(fn == "run_git" for _l, fn, _k, _t in launches), "premise: run_git's launch is read")
                self.assertEqual([u for u in unheld_launches(source) if u[1] not in NOT_A_PROCESS[rel]], [])
                for fn in NOT_A_PROCESS[rel]:
                    self.assertIn(fn, {f for _l, f, _k, _t in launches}, "a NOT_A_PROCESS entry the code no longer needs")

    def test_an_unheld_launch_is_found(self):
        """The held rule's red: a launch with no hold, a hold with no try after it, a try that does not release in its
        handler, a hold in another function, and a launcher bound to a name are each found; the held shape is not. In
        each script's real source, a launch site whose hold is removed (UNHELD_PLANTS), and bisect's command started
        through subprocess.run again, as before this rule, are found where the plant went."""
        head = "import subprocess\n"
        cases = {
            "def f():\n    return subprocess.Popen(['true'])\n": 1,
            "def f():\n    _hold_stops()\n    p = subprocess.Popen(['true'])\n": 1,
            "def f():\n    _hold_stops()\n    try:\n        p = subprocess.Popen(['true'])\n    except BaseException:\n"
            "        raise\n": 1,
            "def g():\n    _hold_stops()\n    f()\ndef f():\n    try:\n        p = subprocess.Popen(['true'])\n"
            "    except BaseException:\n        _release_stops()\n        raise\n": 1,
            "def f():\n    run = subprocess.run\n    _hold_stops()\n    try:\n        p = run(['true'])\n"
            "    except BaseException:\n        _release_stops()\n        raise\n": 1,
            "def f():\n    _hold_stops()\n    try:\n        p = subprocess.Popen(['true'])\n    except BaseException:\n"
            "        _release_stops()\n        raise\n    return p\n": 0,
        }
        for source, want in cases.items():
            with self.subTest(source=source):
                self.assertEqual(len(unheld_launches(head + source)), want, unheld_launches(head + source))
        for rel, plants in UNHELD_PLANTS.items():
            base = self.read(rel)
            for label, (old, new) in plants.items():
                with self.subTest(script=rel, plant=label):
                    self.assertEqual(base.count(old), 1, "premise: the plant's text is in %s once" % rel)
                    planted = base.replace(old, new)
                    line = planted[:planted.index(new)].count("\n") + 1
                    found = unheld_launches(planted)
                    self.assertTrue(any(line <= f[0] <= line + new.count("\n") + 1 for f in found), (line, found))

    def test_names_that_start_no_process_are_not_sites(self):
        """subprocess's constants, exceptions and CompletedProcess, os's other names (os.path, os.kill, os.O_NOFOLLOW
        through getattr), ctypes.get_errno and importlib.util.module_from_spec are not sites, nor is a name of an inert
        module, an inert module that holds no module a table names handed on whole (stat, json), a parameter that shadows
        a module's name, or help as a keyword argument, so the allowlist holds launches alone."""
        source = ("import subprocess, os, ctypes, importlib.util, json, stat, shutil, tempfile, signal, argparse\n"
                  "def f(p):\n"
                  "    x = (subprocess.PIPE, subprocess.DEVNULL, subprocess.STDOUT, subprocess.TimeoutExpired,\n"
                  "         subprocess.CompletedProcess(['a'], 0), os.path.join('a', 'b'), os.kill, getattr(os, 'O_NOFOLLOW', 0),\n"
                  "         ctypes.get_errno(), importlib.util.module_from_spec, json.dumps(p), stat.S_ISREG(0), stat,\n"
                  "         json, shutil.rmtree, tempfile.mkdtemp, signal.SIGTERM, os.path.basename,\n"
                  "         argparse.ArgumentParser().add_argument('-x', help='a keyword, not the builtin'))\n"
                  "    return x\n"
                  "def g(stat):\n"
                  "    return stat[-1]\n")
        self.assertEqual(launch_sites(source), [])


if __name__ == "__main__":
    unittest.main()
