"""The link-drop lab's old-hub mint writes nothing into the clone it runs from (2026-09-19).

LinkDropOldLocal (tests/test_federated_linkdrop_served.py) needs a hub kernel and bundle from before PR 815; under
ROMP_LINKDROP_OLD_HUB_BUILD=1 it mints that checkout itself. The maintainer's round 1 of the fork PR that added the lab found the mint was a
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
class's teardown, spied the same way WITH a minted checkout present (pass 5: spied with none, a teardown step conditioned
on the mint, the maintainer's round 1 defect's own shape, was never exercised), runs no command at all (the lab's rmtree takes the
checkout); and no string constant in the lab module's source, in either quoting, is such an argv token (an ast walk, so a
spelling cannot slip past it). What the spies see is a rule over NAMES, not a list of commands: the recorder patched over
the lab module's `subprocess` attribute records the argv of every call to one of that module's spawning functions, `run`,
`Popen`, `call`, `check_call`, `check_output`, `getoutput` and `getstatusoutput` (SPAWNERS, pinned against this Python's
`subprocess.__all__`), each once (a shell string as one token), and hands the call to the real function; every other name
read through the attribute (PIPE, STDOUT, DEVNULL, TimeoutExpired, CompletedProcess) is delegated and unrecorded, so a
command reaches the record only through a recorded name. A token assembled at run time or joined into one shell string is
caught whichever recorded function the module used (the maintainer's round 3, tests-2: the spies saw `run` alone, and the maintainer's round 1's defect re-planted as a
`Popen` with its tokens assembled passed every pin, the byte-identical records included, since the peer worktree's directory
was still alive; pass 8's fixer pass found `call`, `check_call` and `check_output` reaching the real module through
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
a default argument, a functools.partial, a class attribute: the maintainer's round 4 (its addendum) found such a binding, made before the recorder is
installed, calls the real module past it); the reflective primitives (REFLECTIVE_CALLS and REFLECTIVE_ATTRS: exec, eval,
compile, __import__, vars, globals, locals; import_module, __getattribute__, __dict__, sys.modules, attrgetter; getattr
over os, and, since pass 10, getattr over ANY name the source imports with a name that is not a string constant, since a
name built at run time over a module is a name the census cannot read) as nodes whatever their argument; and any import
outside ALLOWED_IMPORTS, the modules the censused set uses today, held equal to the imports in use so that a new module is a
red until it is read. The recorder closes the alias
road on its own side too: before it is installed, _spy walks the lab module's namespace by IDENTITY (its globals, its own
classes' attributes, its functions' defaults and closure cells, partials, properties, bound methods, generators' frames,
containers, and the instance dict of any object that has one) and refuses any object that IS a spawning function of the
real subprocess module, however it was spelled, and any object it cannot read (_bound_spawners; pass 9's fixer pass: a
property's getter, a SimpleNamespace, a bound method and a generator held `subprocess.run` unseen and unlisted).

What the census cannot see is stated as a rule, not a count: it refuses the nodes it enumerates and nothing else, so a road
to a process is unseen exactly when no enumerated node spells it. On the census's side the class is a spawning name resolved
from a STRING inside a function of an allowed module that the censused set calls with it. The enumerated primitives are
refused as nodes whatever their argument (exec over text that carries the spelling whole is refused at the exec, where the
earlier disclosure, which called this class "built text", let it pass; the dunder roads since pass 9's fixer pass; a built
name handed to getattr over any imported name since pass 10, and since its fixer pass over ANY value, with a reflective
primitive read bare, a second binding of `subprocess`, a spawn or a callable at import time refused too), and an attribute
chain rooted at a foreign import binding is RESOLVED step by step through the modules' own import tables, read by path
(_reach): a module ALLOWED_IMPORTS does not name, reached through an allowed module's own import (`mock.builtins`,
`mock.partial` from functools, `subprocess.builtins`, `http.server.socketserver`; `mock.pkgutil` on a Python whose mock imports
pkgutil, 3.11 and later, since the tables are THIS interpreter's standard library and a plant that rides one Python's imports
is a sample of the matrix: pass 11, after the two pkgutil plants redded Python 3.10 alone), and a member of a module
whose source the census cannot read that the censused set does not read today (UNREAD_MEMBERS: `sys._getframe`,
`sys.meta_path`, `mock.sys.modules`), are refused. What remains is a call of an allowed module's OWN function whose body
resolves a name from the string it is handed (`mock.patch("sub" + "process.run")` resolves its target by import inside
mock). The modules whose own source does so are DERIVED, the second family `_foreign_reflective_roads` scans for and the
disclosure cell prints (on this Python `subprocess`, which reads a frame, and `unittest.mock`, which runs exec and resolves
names); which call of the censused set hands which string to one of them is not read, and that is the class.
On the recorder's side the residual is FIVE roads, and the rule over them: the recorder sees a call only through the lab
module's own `subprocess` attribute, and only while it is installed, and it records the argv the lab module hands that
attribute and nothing of what the program then does; the census reads only the censused set's own Python sources; so a
spawning call whose source is outside both, whose time is outside the recorder's window (before it is installed, or
deferred past its removal), or whose spawner is the RECORDED PROGRAM itself is unseen, however far out the import that
reaches it. (1) A program a censused module's own function starts through that module's own subprocess
binding when the lab module calls the function (the recorder patches the lab module's attribute alone, and the census reads
that call as the module's own). (2) A program a function of an IMPORTED module starts through that module's own binding,
the same road one import further out, which pass 8 named and pass 9 narrowed away. (3) A program a foreign module the
import allow-list permits starts inside its own source, reached by a whole-node name no spawner table carries:
`uuid.getnode()` runs a program on an interpreter without the `_uuid` extension, `http.server`'s CGI handler forks and
execs, `os.popen` is a Python body that calls `subprocess.Popen`, `subprocess` itself reaches `_posixsubprocess` and
`os.posix_spawn`, and `unittest.mock` imports asyncio, a spawner family's module, which the scan's own rule counts as a
road. (4) A program started OUTSIDE the recorder's window, in either direction, by code the census cannot resolve as
running then. BEFORE the recorder is installed, at IMPORT time: the module-level statements of the censused set run at
import, a spawning call and a callable handed to a call there are refused, and what a module-level call does inside its
callee is the callee's own source, road (2) or (3) at import time; the package's own `__init__.py` and the sibling modules
only it imports run before the lab module under both entry points and are outside the censused set (`_lab_modules` walks
the lab module's imports, not the package's), so they are derived and printed as an UNWALKED item
(`_package_init_unwalked`) beside the unread modules, never counted as read (the maintainer's round 6, extra6-4: the
import-time docstring called its list everything that could start a program before a recorder). AFTER the recorder is
lifted: a callable deferred past it from inside a function body (a threading.Timer, a thread, an atexit hook, a finalizer)
is not refused, since the census refuses a callable handed to a call outside every function body alone and reads nothing
of when a callable inside one runs, so a program it starts runs under no recorder and is in no derived list (pass 11's
fixer pass planted a timer-deferred spawn after the checkout: the census and the recorder were both silent, and the plant
cell pins the shape as not refused, the disclosed class's witness).
(5) A program a RECORDED program starts: the record is the argv of the lab module's own call, and a static census over
Python source reads nothing of what git, node or a kernel then runs, so a program started by one of them is in no derived
list by construction. The tree's own live instance is the mint: its clone starts git-upload-pack against the source (a
read-only child the refuters traced) and its checkout starts none under the runner's config, which is why the mint cell pins
that conftest.py's git floor (GIT_CONFIG_GLOBAL at os.devnull, GIT_CONFIG_NOSYSTEM set) is in place when the mint runs: a
hook in a user's or the system's git config would be such a program, and the floor is what keeps git from reading one.
The lists are derived and printed by the disclosure cell, none counted here: `_own_spawn_sites` for road (1) (module,
line, function); `_foreign_spawn_roads` for roads (2) and (3), its attribute arm being (2) at the direct depth (a spawner
named on a foreign module's own os, subprocess, pty, asyncio or _posixsubprocess binding) and the whole scan (3), over every
module the censused set's import bindings LOAD (`_import_bindings`; a submodule imported by `from pkg import sub` included,
since the source read is the submodule's: pass 10's fixer pass, when `from unittest import mock` was read as an import of
unittest and unittest.mock's own source went unread), each module's own source read by path under the standard library
without importing it and scanned for the spawner families (an attribute of os, subprocess, pty, asyncio or _posixsubprocess
named as a spawner, on the module's literal name or on a name the module's own imports bind to it at any depth, a spawner
imported from one of them by name and called bare, or an import of subprocess, pty, _posixsubprocess, multiprocessing,
socketserver or asyncio; a module held on an instance, in a container or bound by an assignment is no import binding and is
not resolved, the rule over what the scan cannot read: the maintainer's round 6, extra6-2), at the
depth of the DIRECT sites, a module those modules import being a further road, with the modules whose source the scan
cannot read (built in, an extension module) named as unread rather than dropped, and the derived road set held EQUAL to
FOREIGN_ROADS by the road cell, so a new road is a red until it is read; `_foreign_reflective_roads` for the second family;
`_foreign_touch_sites` for where the censused set touches the road modules other than os and subprocess, keyed on the names
its import statements BIND (an alias, a from-imported name) and spelled by the module's name (`uuid.uuid4`,
`http.server.ThreadingHTTPServer`, `unittest.mock.patch.dict`), by module and line, so the reader sees where the residual is
reachable from (os and subprocess are the census's own subject: os.popen and os.fork are refused as attributes, and
subprocess is the recorder's); `_import_time_statements` for road (4), the module-level statements of the censused set that
are not a def, a class, an import or a constant, and `_package_init_unwalked` for the package's `__init__` and the siblings
only it imports, which no derivation here reads; road (5) has no list, since what a recorded program starts is not in any
source the census parses, and is stated as the rule above; `_unread_member_reads` for the members read on the source-less
modules, held equal to UNREAD_MEMBERS; and the identity walk's boundary (path, kind) with the depth it reached against its
bound. A green run
shows them under pytest's -rA or -s and a red run carries them in its message; no site, module or count of them is written
here.

Synthetic: a scratch repository minted here, hostname TESTHOST; no kernel, no browser.
"""
import _posixsubprocess
import ast
import asyncio
import contextlib
import functools
import glob
import io
import os
import pty
import shutil
import subprocess
import sys
import sysconfig
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
# against the os module); their modules except os are outside ALLOWED_IMPORTS, so those imports are refused before the
# attribute is, while os.fork and os.forkpty are refused as attributes and bare calls alone (os is an allowed import).
# Pinned against this Python's modules below: every name is an attribute of the module named for it (a loop's two are on
# asyncio.AbstractEventLoop). A fork is a process the recorder never sees, whatever it goes on to exec.
OTHER_SPAWNERS = {"pty": ("spawn",), "asyncio": ("create_subprocess_exec", "create_subprocess_shell"),
                  "asyncio.AbstractEventLoop": ("subprocess_exec", "subprocess_shell"), "_posixsubprocess": ("fork_exec",), "os": ("fork", "forkpty")}
# the modules the table is pinned against, imported statically (an import_module call here would read to
# tests/test_state_isolation_order.py as an in-process load of romp code, which this module never makes)
OTHER_SPAWNER_MODULES = {"pty": pty, "asyncio": asyncio, "_posixsubprocess": _posixsubprocess, "os": os}
# the reflective primitives a spawning name could be reached through without being a whole node of the source: refused as
# NODES, whatever their argument, so the road through them is closed at the primitive and not at the spelling it carries
# (the maintainer's round 4: `exec("import subprocess as _s; _s.run(...)")` passed a census that read the constant "subprocess" alone); a
# getattr whose first argument is the os module is refused the same way (a getattr on the lab module's `subprocess` is the
# recorder's, which sees the dynamic lookup). The dunder roads (pass 9's fixer pass: a function's `__globals__` reaches
# its module's namespace whole, `subprocess.CompletedProcess.__init__.__globals__["run"]`; `__spec__` and `__loader__` reach
# the loader; `__class__`, `__subclasses__`, `__code__`, `__closure__`, `__wrapped__`, `__self__` and `__func__` reach an
# object's type, code or bound function; the bare name `__builtins__` reaches `__import__` by a string) are refused the
# same way, as attributes or as a bare name (REFLECTIVE_NAMES), whatever follows them.
REFLECTIVE_CALLS = ("exec", "eval", "compile", "__import__", "vars", "globals", "locals")
# the attribute-reading builtins: refused with a name that is not a string constant over ANY value (a name built at run time is one
# the census cannot read), and, like REFLECTIVE_CALLS, refused read as a bare name anywhere but as the function of a call (an alias
# carries the road under another name: pass 10's fixer pass, `_gi = __import__`, `_ga = getattr`, `map(exec, [...])`)
ATTR_BUILTINS = ("getattr", "setattr", "delattr", "hasattr")
REFLECTIVE_ATTRS = ("import_module", "__getattribute__", "__getattr__", "__dict__", "modules", "attrgetter",
                    "__globals__", "__spec__", "__loader__", "__builtins__", "__class__", "__subclasses__", "__code__", "__closure__", "__wrapped__", "__self__", "__func__")
REFLECTIVE_NAMES = ("__builtins__",)
# every module the censused set imports today, foreign to this directory (a sibling is walked, never listed): an import
# outside this tuple is refused, so the eight modules DENIED_IMPORTS names (the stdlib starters pty, asyncio, multiprocessing,
# ctypes and _posixsubprocess, and importlib, builtins and operator, which reach one by reflection) are a red the moment one is
# imported; the cell holds the tuple EQUAL to the imports in use, so a name here that nothing imports is a red too. The tuple
# does NOT say that no allowed module starts a program: which of them do inside their own source is DERIVED by
# _foreign_spawn_roads (FOREIGN_ROADS, held equal) and printed by the disclosure cell, the module docstring's third road; what
# the censused set REACHES through an allowed module's own imports is resolved and refused by _reach.
ALLOWED_IMPORTS = ("base64", "contextlib", "fcntl", "fnmatch", "hashlib", "http", "json", "os", "pathlib", "re", "select", "shlex",
                   "shutil", "signal", "socket", "subprocess", "sys", "tempfile", "threading", "time", "unittest", "urllib", "uuid")
# the hand-kept DENY list the import pin keys on beside the equality: none of these eight is allowed (the check is this list,
# not a property of every allowed module's source; that property is derived, above)
DENIED_IMPORTS = ("pty", "asyncio", "_posixsubprocess", "multiprocessing", "ctypes", "importlib", "builtins", "operator")
# the modules whose import inside a FOREIGN module's own source is a road to a program (the spawner families' modules, and
# socketserver, whose ForkingMixIn forks), for _foreign_spawn_roads; the attribute roots it reads the spawner names on
FOREIGN_SPAWN_MODULES = ("subprocess", "pty", "_posixsubprocess", "multiprocessing", "socketserver", "asyncio")
FOREIGN_SPAWN_ROOTS = ("os", "subprocess", "pty", "asyncio", "_posixsubprocess")
# the reflective calls a foreign module's OWN source may make, resolving a name from a string handed to it (the second family
# _foreign_reflective_roads scans for, printed beside the spawner roads): a bare call of one of REFLECTIVE_CALLS, or an attribute
# named as one of these
FOREIGN_REFLECTIVE_CALLS = ("__import__", "exec", "eval", "compile")
FOREIGN_REFLECTIVE_ATTRS = ("import_module", "resolve_name", "_getframe", "__import__")
# The foreign modules whose own source starts a program, on this Python, DERIVED by _foreign_spawn_roads over the censused
# set's import bindings and held EQUAL to this tuple by the road cell, so a new road (a new import, or a Python whose source
# changes) is a red until it is read (pass 10's fixer pass: the cell pinned a subset, so a fifth road could not red it).
FOREIGN_ROADS = ("http.server", "os", "subprocess", "unittest.mock", "uuid")
# The members the censused set reads on the foreign modules whose source the scan cannot read (built in, an extension module:
# fcntl, select, sys, time), as {module: (member, ...)}, held EQUAL to the derived reads by the allow-list cell: a member of such a
# module is a name the census cannot resolve (its source is not there to read), so one outside the tuple (`sys._getframe`,
# `sys.meta_path`, `sys.modules`) is refused until it is read, the rule the parsed census's KNOWN_MEMBERS states for the driver.
UNREAD_MEMBERS = {"fcntl": ("LOCK_EX", "flock"), "select": ("select",), "sys": ("path",), "time": ("gmtime", "monotonic", "sleep", "strftime", "time")}
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
    is refused, never dropped (the maintainer's round 4 addendum: the file check dropped one, and a helper carrying `os.popen` in its __init__ passed the
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


def _commands_around_the_recorder(src, siblings=(), stdlib=None):
    """Every node of the parsed source that is a road to a process around the recorder, as (line, form), keyed on the ROAD
    (the maintainer's round 4) and not on a spelling: an attribute read named as one of OS_SPAWNERS or OTHER_SPAWNERS on ANY value (`os.system`,
    `pty.spawn`, a renamed module and a nested attribute are refused alike, the safe side); a call to such a bare name, or its
    import (`from os import system`, `from os import *`, `from pty import spawn`); a spawning function of subprocess BOUND
    rather than called (`subprocess.run` anywhere but as the function of a call: an alias, a dict value, a default argument,
    a partial's first argument, a class attribute); the bare name `subprocess` read anywhere but as the value of an attribute
    (`_sp = subprocess`, `f(subprocess)`); an attribute named `subprocess` on any other value (`_dial.subprocess.run`); an
    import of the subprocess module or of os under another name, or of a name from subprocess; a constant "subprocess" or one
    equal to an OS_SPAWNERS name (the road through a string handed to a primitive); a call to one of REFLECTIVE_CALLS, an
    attribute named as one of REFLECTIVE_ATTRS, a bare read of one of REFLECTIVE_NAMES, a getattr whose first argument is the
    os module, a getattr, setattr, delattr or hasattr whose name argument is not a string constant over ANY first argument
    (pass 10: `getattr(_dial, "subproce" + "ss")` was inside the stated class with no red, and the fixer pass found the same
    over an alias of os and over an attribute; a built name over any value is a name the census cannot read, and a constant
    name is read by the constant arm), a reflective primitive or an attribute-reading builtin read as a BARE NAME anywhere but
    as the function of a call (`_gi = __import__`, `map(exec, [...])`: an alias carries the road under another name, the rule
    the bare name `subprocess` already had), or an import of such a name, each refused as a node whatever its argument, so the
    text it carries is not what is matched, a constant compared by its decoded text (b"subprocess" is "subprocess"); the name
    `subprocess` BOUND anywhere but by a module-level `import subprocess` (an import inside a function or a class, a `global` or
    `nonlocal` declaration, an assignment, a parameter, a name imported as it: the recorder patches ONE binding, the module's
    attribute, and a function-local import rebinds the name to the real module past it); a spawning call of subprocess outside
    every function BODY (at module level, in a class body, in a default argument or a decorator: it runs at import, before any
    recorder is installed); a function literal or a def's name handed as an argument to a call outside every function body
    (a thread target, a signal handler: when it runs is a bound this census cannot read, and a program it starts runs under no
    recorder); an import of any module outside ALLOWED_IMPORTS that is not a sibling this census walks (`siblings`; a
    relative import is one by construction); and a name a from-import BINDS that _reach cannot resolve to something the census
    reads, the same two refusals the attribute chains get (a member of a module whose source the census cannot read, outside
    UNREAD_MEMBERS; a module ALLOWED_IMPORTS does not name, reached through an allowed module's own import), keyed on the
    BINDING and not on the attribute spelling (the maintainer's round 6, extra6-1: `from sys import _getframe` escaped where
    `sys._getframe` was refused); and a star import from ANY module (`from sys import *`), since it binds names the census
    cannot resolve without importing the module (pass 11's fixer pass: the os arm refused `from os import *` alone, and
    `from sys import *` followed by a read of the star-bound `modules` was silent). A chain rooted at anything but an import binding (a class attribute holding a module, a
    default argument, a container, an assignment `_s = sys`) is not resolved: the rule over what stays unread, since the census
    resolves import bindings and nothing else. `stdlib` is the standard library the modules' own sources are read from (a
    synthetic one in the cells). A comment or a docstring is no node of these kinds, so the words in one do not
    count; a docstring is one constant equal to its whole text, so a docstring that names os.system is not equal to "system"."""
    found = []
    tree = ast.parse(src)
    parent = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[child] = node
    spawners = set(OS_SPAWNERS) | set(OTHER_NAMES)
    defs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    bindings, loaded = _import_bindings(src, stdlib)

    def in_a_body(n):
        """Whether the node sits inside some function's BODY: a default argument, a decorator and an annotation are outside it
        (they run at definition time), as is a class body and the module level."""
        q = n
        while q in parent:
            up = parent[q]
            if (isinstance(up, (ast.FunctionDef, ast.AsyncFunctionDef)) and q in up.body) or (isinstance(up, ast.Lambda) and q is up.body):
                return True
            q = up
        return False
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
        elif isinstance(n, ast.Name) and n.id in REFLECTIVE_NAMES and isinstance(n.ctx, ast.Load):
            found.append((n.lineno, n.id))
        elif isinstance(n, ast.Name) and (n.id in REFLECTIVE_CALLS or n.id in ATTR_BUILTINS) and isinstance(n.ctx, ast.Load) and not (isinstance(p, ast.Call) and p.func is n):
            found.append((n.lineno, "%s read bare (an alias of a reflective primitive)" % n.id))
        elif isinstance(n, ast.Name) and n.id == "subprocess" and isinstance(n.ctx, (ast.Store, ast.Del)):
            found.append((n.lineno, "subprocess bound by an assignment"))
        elif isinstance(n, (ast.Global, ast.Nonlocal)) and "subprocess" in n.names:
            found.append((n.lineno, "%s subprocess" % type(n).__name__.lower()))
        elif isinstance(n, ast.arg) and n.arg == "subprocess":
            found.append((n.lineno, "subprocess bound as a parameter"))
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id in spawners:
                found.append((n.lineno, n.func.id + "("))
            elif n.func.id in REFLECTIVE_CALLS:
                found.append((n.lineno, n.func.id + "("))
            elif n.func.id == "getattr" and n.args and isinstance(n.args[0], ast.Name) and n.args[0].id == "os":
                found.append((n.lineno, "getattr(os,"))
            elif n.func.id in ATTR_BUILTINS and len(n.args) > 1 and not isinstance(n.args[1], ast.Constant):
                found.append((n.lineno, "%s(%s, <a name built at run time>" % (n.func.id, ast.unparse(n.args[0]))))
        elif isinstance(n, ast.ImportFrom):
            top = n.module.split(".")[0] if n.module else ""
            names = [a.name for a in n.names]
            if n.module == "os" and any(a in spawners or a == "*" for a in names):
                found.append((n.lineno, "from os import " + ", ".join(names)))
            elif n.module and top == "subprocess":
                found.append((n.lineno, "from %s import %s" % (n.module, ", ".join(names))))
            elif n.module and any(a in OTHER_NAMES or a in REFLECTIVE_CALLS or a in REFLECTIVE_ATTRS or a in ATTR_BUILTINS for a in names):
                found.append((n.lineno, "from %s import %s" % (n.module, ", ".join(names))))
            if any((a.asname or a.name) == "subprocess" for a in n.names):
                found.append((n.lineno, "from %s import ... as subprocess (a second binding of the name)" % (n.module,)))
            if "*" in names:
                found.append((n.lineno, "from %s import * (a star import binds names the census cannot resolve)" % (n.module or ".",)))
            if n.level == 0 and top not in ALLOWED_IMPORTS and top not in siblings and top != PACKAGE:
                found.append((n.lineno, "from %s import ... (a module ALLOWED_IMPORTS does not name)" % (n.module,)))
            for a in n.names:   # the binding resolved: a member of a source-less module outside UNREAD_MEMBERS, or a module reached through the import table
                bound = bindings.get(a.asname or a.name)
                hit = _reach(a.asname or a.name, bindings, loaded, siblings, stdlib) if bound is not None and bound[1] is not None and a.name != "*" else None
                if hit is not None:
                    found.append((n.lineno, "from %s import %s: %s.%s %s" % (n.module, a.name, hit[0], hit[1], hit[2])))
        elif isinstance(n, ast.Import):
            for a in n.names:
                top = a.name.split(".")[0]
                if top == "subprocess" and (a.asname or a.name != "subprocess"):
                    found.append((n.lineno, "import %s as %s" % (a.name, a.asname)))
                elif top == "subprocess" and not isinstance(p, ast.Module):
                    found.append((n.lineno, "import subprocess inside a function or a class (a second binding of the name, past the recorder)"))
                elif top == "os" and a.asname:
                    found.append((n.lineno, "import %s as %s" % (a.name, a.asname)))
                elif top not in ALLOWED_IMPORTS and top not in siblings and top != PACKAGE:
                    found.append((n.lineno, "import %s (a module ALLOWED_IMPORTS does not name)" % (a.name,)))
        elif isinstance(n, ast.Constant) and isinstance(n.value, (str, bytes)):
            text = n.value.decode("utf-8", "replace") if isinstance(n.value, bytes) else n.value
            if text == "subprocess" or text in OS_SPAWNERS:
                found.append((n.lineno, '"%s"' % (text,)))
        if isinstance(n, ast.Attribute) and not (isinstance(p, ast.Attribute) and p.value is n):
            chain = _dotted(n)
            hit = _reach(chain, bindings, loaded, siblings, stdlib) if chain else None
            if hit is not None:
                found.append((n.lineno, "%s.%s %s" % (hit[0], hit[1], hit[2])))
        if isinstance(n, ast.Call) and not in_a_body(n):
            if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess" and n.func.attr in SPAWNERS:
                found.append((n.lineno, "subprocess.%s(...) outside every function body: it runs at import, before any recorder" % n.func.attr))
            for a in list(n.args) + [k.value for k in n.keywords]:
                if isinstance(a, ast.Lambda) or (isinstance(a, ast.Name) and a.id in defs):
                    found.append((n.lineno, "a callable handed to a call outside every function body (%s): when it runs is a bound the census cannot read" % ast.unparse(n.func)))
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


def _stdlib_source(dotted, stdlib=None):
    """The path of a module's Python source under the standard library (`<stdlib>/a/b.py` or `<stdlib>/a/b/__init__.py`), else
    None (built in, an extension module, or no such module)."""
    stdlib = stdlib or sysconfig.get_paths()["stdlib"]
    rel = dotted.replace(".", os.sep)
    return next((p for p in (os.path.join(stdlib, rel + ".py"), os.path.join(stdlib, rel, "__init__.py")) if os.path.isfile(p)), None)


def _import_bindings(src, stdlib=None, package=None):
    """What the source's absolute import statements BIND, and which modules they load: ({bound name: (module, member)}, {dotted
    module}). `import a.b.c` binds `a` to the package `a` and loads a, a.b and a.b.c; `import a.b as x` binds x to a.b; `from M
    import n` binds n to the SUBMODULE M.n when the standard library holds its source (`from unittest import mock` is
    unittest.mock, whose own source the road scan must read: pass 10's fixer pass, residual-1) and otherwise to the member n of
    M (`from pathlib import Path`); `from M import n as x` binds x the same way. A relative import (a sibling of this directory,
    or, for a stdlib module read by path, its own package's module, resolved against `package`) binds its name to that
    package-qualified module. The touch derivation and the reach rule key on these bindings, not on the dotted spelling as
    written (pass 10's fixer pass: `import uuid as u; u.getnode()` and `from uuid import getnode; getnode()` printed no touch)."""
    bindings, loaded = {}, set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import):
            for a in n.names:
                parts = a.name.split(".")
                loaded.update(".".join(parts[:i + 1]) for i in range(len(parts)))
                bindings[a.asname or parts[0]] = (a.name if a.asname else parts[0], None)
        elif isinstance(n, ast.ImportFrom):
            if n.level == 0:
                base = n.module or ""
            elif package is None:
                continue
            else:
                up = package.split(".")
                base = ".".join(up[:len(up) - (n.level - 1)] + ([n.module] if n.module else []))
            if not base:
                continue
            loaded.add(base)
            for a in n.names:
                if a.name == "*":
                    continue
                if _stdlib_source(base + "." + a.name, stdlib) is not None:
                    loaded.add(base + "." + a.name)
                    bindings[a.asname or a.name] = (base + "." + a.name, None)
                else:
                    bindings[a.asname or a.name] = (base, a.name)
    return bindings, loaded


def _dotted_foreign_imports(mods, stdlib=None):
    """Every dotted module the censused modules LOAD that is no sibling of theirs (`http`, `http.server`, `urllib.request`,
    `unittest.mock`, `uuid`), from their import bindings: the modules whose own source _foreign_spawn_roads reads.
    `_foreign_imports` above keeps the top-level names ALLOWED_IMPORTS is held equal to; this keeps every module loaded, a
    submodule imported by `from pkg import sub` included."""
    out = set()
    for src in mods.values():
        out.update(_import_bindings(src, stdlib)[1])
    return {name for name in out if name.split(".")[0] not in mods and name.split(".")[0] != PACKAGE}


_MODULE_IMPORTS = {}


def _module_imports(dotted, stdlib=None):
    """A foreign module's OWN module-level import bindings, read from its source by path and never imported: {bound name:
    (module, member)}, or None for a module with no Python source (built in, an extension module). A relative import inside a
    package's module resolves against the package (`from .util import safe_repr` in unittest/mock.py is unittest.util). Cached
    per (module, stdlib): the reach rule reads it for every attribute chain rooted at a foreign binding."""
    key = (dotted, stdlib)
    if key not in _MODULE_IMPORTS:
        path = _stdlib_source(dotted, stdlib)
        if path is None:
            _MODULE_IMPORTS[key] = None
        else:
            package = dotted if os.path.basename(path) == "__init__.py" else dotted.rpartition(".")[0]
            with open(path, encoding="utf-8") as f:
                body = ast.parse(f.read()).body
            _MODULE_IMPORTS[key] = _import_bindings("\n".join(ast.unparse(n) for n in body if isinstance(n, (ast.Import, ast.ImportFrom))), stdlib, package)[0]
    return _MODULE_IMPORTS[key]


def _reach(chain, bindings, loaded, siblings=(), stdlib=None):
    """Where an attribute chain rooted at a foreign import binding REACHES, resolved step by step through the modules' own
    import tables (_module_imports): None when every step lands on a module's own definition, an allowed module or a member the
    censused set reads today; else (module, attribute, why) for the first step the census cannot resolve to something it
    reads: an attribute that is the module's own import of a module outside ALLOWED_IMPORTS (`mock.builtins`, `mock.partial`
    from functools, `subprocess.builtins`, `http.server.socketserver`: a road the census would refuse as a direct import,
    reached through an allowed module's binding, pass 10's fixer pass), or a member of a module whose source the census
    cannot read that is outside UNREAD_MEMBERS (`sys._getframe`, `sys.meta_path`, `mock.sys.modules`). A chain rooted at a
    name a from-import binds to a MEMBER (`from sys import _getframe`, `from unittest.mock import builtins`) is resolved from
    that member on, the same two refusals (the maintainer's round 6, extra6-1: the earlier walk stopped at a member binding, so
    the from-import spelling of a refused attribute escaped). A binding to a def or a class imported by name (`Path`) is its
    own: the walk stops there."""
    names = chain.split(".")
    bound = bindings.get(names[0])
    if bound is None or bound[0].split(".")[0] in siblings or bound[0].split(".")[0] == PACKAGE:
        return None
    module = bound[0]
    for attr in ([bound[1]] if bound[1] is not None else []) + names[1:]:
        if module + "." + attr in loaded:
            module = module + "." + attr
            continue
        table = _module_imports(module, stdlib)
        if table is None:
            return None if attr in UNREAD_MEMBERS.get(module, ()) else (module, attr, "a member of %s, a module whose source the census cannot read (built in, an extension module), that the censused set does not read today (UNREAD_MEMBERS)" % module)
        if attr not in table:
            return None   # the module's own definition (a function, a class, a constant, a submodule it loads inside a function)
        nxt, member = table[attr]
        if nxt.split(".")[0] not in ALLOWED_IMPORTS and nxt.split(".")[0] not in siblings:
            return (module, attr, "reaches %s, a module ALLOWED_IMPORTS does not name, through %s's own import (a road the census refuses as a direct import)" % (nxt, module))
        if member is not None:
            return None
        module = nxt
    return None


def _foreign_spawn_roads(mods, stdlib=None):
    """The DERIVED third road (the module docstring): for each dotted foreign import of the censused set, the spawner roads in
    that module's OWN source, as {module: [(line, form)]}, and the modules whose source the scan could not read, as {module:
    why}. The source is found by path under the standard library (`stdlib`, this interpreter's by default; the synthetic cell
    hands a directory of its own) and parsed, never imported (an import here would be an in-process load the state census
    reads, and would run the module). A road is an attribute named as a spawner (OS_SPAWNERS, OTHER_SPAWNERS, SPAWNERS) on a
    name that IS one of os, subprocess, pty, asyncio or _posixsubprocess or that the module's own imports BIND to one of them
    (`import os as _os; _os.execv(...)`, the spelling tempfile.py and threading.py use; any import at any depth, a
    function-local one included, since the module-level table alone missed those: the union the maintainer's round 6,
    extra6-2, asked for), a spawner imported from one of them by name (`from os import system`) and a bare call of a name so
    imported (`system("true")`), a star import from one of the os-family roots (`from os import *`: it binds every name of
    the module, a spawner among them, and the scan cannot say which name the module then calls; pass 11's fixer pass, where it
    bound `system` unseen), or an import of one of FOREIGN_SPAWN_MODULES (never `import os` itself: os is every module's
    import, and the road is the spawner named on it). What stays unread, the rule over what the scan RESOLVES: a spawner is
    read on an attribute whose value is a NAME the module's imports bind to an os-family module, and on nothing else, so a
    module held on an instance (`self._os.execv`), in a container, bound by an assignment (`_o = os`) or reached as another
    module's attribute (`os.path.os.system`, an attribute whose value is an attribute) is not resolved; and a local alias is
    read module-wide (the table is name-keyed, not scope-keyed: the safe side, a false road over a true miss).
    Read at the depth of the direct sites: a module these modules import is a further road, stated in the docstring, not
    followed here. A module with no Python source is reported as unread with the reason (built in; an extension module under
    lib-dynload) rather than dropped, and a name with no source anywhere is unread for a reason the caller must refuse."""
    stdlib = stdlib or sysconfig.get_paths()["stdlib"]
    dynload = os.path.join(sysconfig.get_paths()["platstdlib"], "lib-dynload")
    spawners = set(OS_SPAWNERS) | set(OTHER_NAMES) | set(SPAWNERS)
    roads, unread = {}, {}
    for name in sorted(_dotted_foreign_imports(mods, stdlib)):
        path = _stdlib_source(name, stdlib)
        if path is None:
            if name in sys.builtin_module_names:
                unread[name] = "built in (no Python source)"
            elif glob.glob(os.path.join(dynload, name + ".*")):
                unread[name] = "an extension module under lib-dynload (no Python source)"
            else:
                unread[name] = "no source found under the standard library"
            continue
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        aliases, from_names = {}, {}   # {a name the module binds to an os-family module: that module}, {a spawner imported by name: its dotted name}
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    if a.name.split(".")[0] in FOREIGN_SPAWN_ROOTS:
                        aliases[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
            elif isinstance(n, ast.ImportFrom) and n.module and n.module.split(".")[0] in FOREIGN_SPAWN_ROOTS:
                for a in n.names:
                    if a.name in spawners:
                        from_names[a.asname or a.name] = "%s.%s" % (n.module, a.name)
        for bound, (mod, member) in (_module_imports(name, stdlib) or {}).items():
            if member is None and mod.split(".")[0] in FOREIGN_SPAWN_ROOTS:
                aliases.setdefault(bound, mod)
        hits = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and n.attr in spawners and isinstance(n.value, ast.Name) and (n.value.id in FOREIGN_SPAWN_ROOTS or n.value.id in aliases):
                hits.append((n.lineno, "%s.%s" % (aliases.get(n.value.id, n.value.id), n.attr)))
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in from_names:
                hits.append((n.lineno, "%s()" % from_names[n.func.id]))
            elif isinstance(n, ast.Import):
                hits += [(n.lineno, "import " + a.name) for a in n.names if a.name.split(".")[0] in FOREIGN_SPAWN_MODULES]
            elif isinstance(n, ast.ImportFrom) and n.module and n.module.split(".")[0] in FOREIGN_SPAWN_MODULES:
                hits.append((n.lineno, "from %s import %s" % (n.module, ", ".join(a.name for a in n.names))))
            elif isinstance(n, ast.ImportFrom) and n.module and n.module.split(".")[0] in FOREIGN_SPAWN_ROOTS and any(a.name in spawners for a in n.names):
                hits.append((n.lineno, "from %s import %s" % (n.module, ", ".join(a.name for a in n.names if a.name in spawners))))
            elif isinstance(n, ast.ImportFrom) and n.module and n.module.split(".")[0] in FOREIGN_SPAWN_ROOTS and any(a.name == "*" for a in n.names):
                hits.append((n.lineno, "from %s import * (every name of the module, a spawner among them)" % (n.module,)))
        if hits:
            roads[name] = sorted(hits)
    return roads, unread


def _foreign_reflective_roads(mods, stdlib=None):
    """The second derived family (pass 10's fixer pass, plants-10): for each dotted foreign import of the censused set, the calls in
    that module's OWN source that resolve a name from a string handed to them, {module: [(line, form)]}: a bare call of one of
    FOREIGN_REFLECTIVE_CALLS (__import__, exec, eval, compile; globals, locals and vars return a namespace and are a road only
    with a string key, which is the censused set's own rule), or an attribute named as one of FOREIGN_REFLECTIVE_ATTRS
    (import_module, resolve_name, _getframe, __import__). Read the same way as the spawner roads, by path and never imported, at
    the direct depth. A program a module
    starts by resolving a name inside its own function from a string the censused set hands it (`mock.patch("sub" +
    "process.run")`) is the residual's fourth road; this is its derived list, printed by the disclosure cell."""
    stdlib = stdlib or sysconfig.get_paths()["stdlib"]
    roads = {}
    for name in sorted(_dotted_foreign_imports(mods, stdlib)):
        path = _stdlib_source(name, stdlib)
        if path is None:
            continue
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        hits = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FOREIGN_REFLECTIVE_CALLS:
                hits.append((n.lineno, n.func.id + "("))
            elif isinstance(n, ast.Attribute) and n.attr in FOREIGN_REFLECTIVE_ATTRS:
                hits.append((n.lineno, "." + n.attr))
        if hits:
            roads[name] = sorted(hits)
    return roads


def _unread_member_reads(mods, unread):
    """The members the censused set reads on the foreign modules whose source the scan could not read (`unread`, from
    _foreign_spawn_roads), as {module: sorted members}, over attribute chains rooted at a binding to such a module: what
    UNREAD_MEMBERS is held equal to."""
    out = {}
    for src in mods.values():
        bindings, _ = _import_bindings(src)
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in bindings:
                module, member = bindings[n.value.id]
                if member is None and module in unread:
                    out.setdefault(module, set()).add(n.attr)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in bindings:
                module, member = bindings[n.id]   # a member a from-import binds is a read of it (the maintainer's round 6, extra6-1)
                if member is not None and module in unread:
                    out.setdefault(module, set()).add(member)
    return {m: sorted(v) for m, v in out.items()}


def _import_time_statements(mods):
    """The module-level statements of the CENSUSED SET that RUN at import and are not a def, a class, an import or an
    assignment of a constant, as (module, line, text): the part of the import-time surface this census reads. It is not all
    of it (the maintainer's round 6, extra6-4: the earlier sentence called this list everything that could start a program
    before a recorder): the package's own __init__.py and the siblings only it imports run first under both entry points and
    are outside the set (_package_init_unwalked derives and prints them as unwalked), and what a module-level call does
    inside its callee is the callee's own source. The census refuses a spawning call and a callable handed to a call here;
    the rest is printed by the disclosure cell as the derived list of what runs then, never counted."""
    out = []
    for name, src in sorted(mods.items()):
        for n in ast.parse(src).body:
            if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(n, (ast.Assign, ast.AnnAssign, ast.Expr)) and isinstance(n.value, ast.Constant):
                continue   # a constant assignment, a docstring
            out.append((name, n.lineno, ast.unparse(n).splitlines()[0][:90]))
    return out


def _package_init_unwalked(mods, here=HERE):
    """The package's own `__init__.py` and the sibling modules ONLY it imports (by _sibling_imports over its source, every
    spelling), as sorted module names, none of them in the censused set `mods`: the import-time surface that runs before the
    lab module under both entry points (pytest imports the package first; `python -m unittest tests.x` too) and that
    _lab_modules never walks, since it follows the lab module's imports and not the package's. Derived and printed by the
    disclosure cell as an UNWALKED item beside the unread modules, never read as clean (the maintainer's round 6, extra6-4:
    tests/__init__.py imports a sibling that binds and calls subprocess, and a spawn planted at package import ran with every
    cell green). Empty when the directory is no package."""
    init = os.path.join(here, "__init__.py")
    if not os.path.isfile(init):
        return []
    with open(init, encoding="utf-8") as f:
        names = _sibling_imports(f.read(), os.path.basename(here))
    siblings = sorted(n for n in names if n not in mods and os.path.isfile(os.path.join(here, n + ".py")))
    return ["__init__"] + siblings


def _dotted(node):
    """The dotted spelling of an attribute chain rooted at a name (`http.server.HTTPServer`), else None."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _foreign_touch_sites(mods, roads):
    """Where the censused set touches a road module, as (module, line, dotted name), keyed on the names its import statements
    BIND (_import_bindings) and not on the spelling as written: an attribute chain rooted at a name bound to the module (`uuid.
    uuid4`, `u.getnode()` under `import uuid as u`, `mock.patch` under `from unittest import mock`, spelled by the module's
    name) and a bare read of a name imported from it (`getnode()` under `from uuid import getnode`), for the road modules other
    than os and subprocess, whose roads the census refuses itself (OS_SPAWNERS and OTHER_SPAWNERS as attributes; subprocess is
    the recorder's). The outermost chain only. Printed by the disclosure cell beside the roads: the residual's reach into the
    censused set, derived, never counted (pass 10's fixer pass: keyed on the dotted spelling, an alias or a from-import of a
    road module printed nothing)."""
    watch = sorted(r for r in roads if r not in ("os", "subprocess"))
    out = set()
    for name, src in sorted(mods.items()):
        bindings, _ = _import_bindings(src)
        tree = ast.parse(src)
        parent = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parent[child] = node
        for n in ast.walk(tree):
            p = parent.get(n)
            if isinstance(n, ast.Attribute) and not (isinstance(p, ast.Attribute) and p.value is n):
                chain = _dotted(n)
                if chain is None or chain.split(".")[0] not in bindings:
                    continue
                head, *rest = chain.split(".")
                module, member = bindings[head]
                spelled = ".".join([module] + ([member] if member else []) + rest)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in bindings and bindings[n.id][1] is not None and not (isinstance(p, ast.Attribute) and p.value is n):
                spelled = "%s.%s" % bindings[n.id]
            else:
                continue
            if any(spelled == r or spelled.startswith(r + ".") for r in watch):
                out.add((name, n.lineno, spelled))
    return sorted(out)


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


# a value that holds no reference of ours, never a holder: a scalar leaf, and a C type's slot or method descriptor (a class's own
# `__dict__` and `__weakref__` descriptors are in vars(cls) of every class)
LEAF_TYPES = (str, bytes, int, float, complex, bool, type(None), type(Ellipsis), range,
              types.GetSetDescriptorType, types.MemberDescriptorType, types.WrapperDescriptorType, types.MethodDescriptorType, types.ClassMethodDescriptorType)


def _bound_spawners(module, depth=8, stats=None):
    """Every object reachable from the module's namespace that IS a spawning function of the real subprocess module, by
    identity, as (path, name). Entered, to `depth`: the module's globals, its own classes' attributes, its functions' defaults,
    keyword defaults and closure cells, partials (function, arguments, keywords), staticmethods and classmethods, properties
    (fget, fset, fdel), bound methods (the function and the object), generators and coroutines (their frames' locals), dicts,
    lists, tuples, sets, and the instance dict of any object that has one (an instance of the module's own class or of a
    foreign one, a SimpleNamespace). Keyed on the ROAD and not the spelling: a binding made before the recorder is installed
    (`_run = subprocess.run` at module level, a dict value, a default argument, a partial, a class attribute, a property's
    getter) calls the real module past the recorder however it was written, and this is what _spy refuses before it patches.
    Not entered, and returned beside the findings as (path, kind), the derived list of what this walk cannot see: a module
    object (a boundary by design; the census over the parsed source reads the road to it), a class of another module (its
    attributes are that module's), an object the walk cannot read (no instance dict and no holder shape it knows: an
    iterator, a C-level object), which _spy refuses outright since a spawning function could sit in it unseen, and a holder
    past the walk's depth bound ("beyond the walk's depth of N": pass 9 cut it off silently, so a spawning function bound
    deeper than the walk was in neither list; _spy refuses it too, with its own sentence, since a holder not entered is not a
    holder read). A scalar leaf (LEAF_TYPES) holds no reference and is not listed. `stats`, when given, receives the
    deepest level the walk entered ("max_depth"), which the disclosure cell prints beside the bound."""
    spawners = {id(getattr(subprocess, n)): n for n in SPAWNERS}
    found, boundary, seen = [], [], set()
    if stats is not None:
        stats["max_depth"] = 0

    def visit(obj, path, d):
        if id(obj) in spawners:
            found.append((path, spawners[id(obj)]))
            return
        if id(obj) in seen or isinstance(obj, LEAF_TYPES):
            return
        if d > depth:
            boundary.append((path, "beyond the walk's depth of %d" % depth))
            return
        if stats is not None:
            stats["max_depth"] = max(stats["max_depth"], d)
        seen.add(id(obj))
        if isinstance(obj, types.ModuleType):
            boundary.append((path, "module"))
        elif isinstance(obj, functools.partial):
            visit(obj.func, path + ".func", d + 1)
            for i, a in enumerate(obj.args):
                visit(a, "%s.args[%d]" % (path, i), d + 1)
            for k, v in (obj.keywords or {}).items():
                visit(v, "%s.keywords[%r]" % (path, k), d + 1)
        elif isinstance(obj, (staticmethod, classmethod)):
            visit(obj.__func__, path + ".__func__", d + 1)
        elif isinstance(obj, property):
            for k in ("fget", "fset", "fdel"):
                visit(getattr(obj, k), "%s.%s" % (path, k), d + 1)
        elif isinstance(obj, types.MethodType):
            visit(obj.__func__, path + ".__func__", d + 1)
            visit(obj.__self__, path + ".__self__", d + 1)
        elif isinstance(obj, types.BuiltinFunctionType):
            if getattr(obj, "__self__", None) is not None:
                visit(obj.__self__, path + ".__self__", d + 1)   # a bound builtin method (`bag.append`) holds its object
        elif isinstance(obj, (types.GeneratorType, types.CoroutineType)):
            frame = obj.gi_frame if isinstance(obj, types.GeneratorType) else obj.cr_frame
            for k, v in (frame.f_locals if frame is not None else {}).items():
                visit(v, "%s.<frame %s>" % (path, k), d + 1)
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
            else:
                boundary.append((path, "class of %s" % obj.__module__))
        elif isinstance(obj, dict):
            for k, v in obj.items():
                visit(v, "%s[%r]" % (path, k), d + 1)
        elif isinstance(obj, (list, tuple, set, frozenset)):
            for i, v in enumerate(obj):
                visit(v, "%s[%d]" % (path, i), d + 1)
        elif hasattr(obj, "__dict__"):
            for k, v in vars(obj).items():
                visit(v, "%s.%s" % (path, k), d + 1)
        else:
            boundary.append((path, "%s the walk cannot read" % type(obj).__name__))
    for name, obj in vars(module).items():
        if not name.startswith("__"):
            visit(obj, name, 0)
    return found, boundary


def _unreadable(boundary):
    """The boundary entries that are neither a module, a foreign class nor a depth cut: objects the identity walk could not read."""
    return [b for b in boundary if b[1] != "module" and not b[1].startswith("class of ") and not b[1].startswith("beyond the walk's depth")]


def _beyond_depth(boundary):
    """The boundary entries the identity walk did not enter because they sit past its depth bound: holders not read."""
    return [b for b in boundary if b[1].startswith("beyond the walk's depth")]


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
        records once here. The recorder exists for the shape the maintainer's round 3 (tests-2) found passing every pin: the maintainer's round 1's repo-global sweep
        re-planted at the top of the class's teardown as `subprocess.Popen(["git", "-C", ROOT, "workt" + "ree", "pr" +
        "une"]).communicate()`, a `Popen` the `run` spy never saw with tokens the ast census never sees; the fixer pass of
        pass 8 re-planted it as `subprocess.check_call(...)`, which the two-name recorder delegated unseen. Neither plant
        can live in the repo; both are recorded as mutations in the builder's review note outside it (red on
        test_the_teardown_runs_no_command through this recorder). The maintainer's round 4 (its addendum): a spawning function BOUND in the lab module before
        the patch (`_run = subprocess.run` at module level, a dict value, a default argument, a partial, a class attribute)
        calls the real module past any recorder over the attribute, so before patching, every recorder refuses such a binding
        by identity (_bound_spawners over the lab module's namespace), whatever spelling made it."""
        bound, boundary = _bound_spawners(L)
        self.assertEqual(bound, [], "a spawning function of the subprocess module is bound in the lab module's namespace before the recorder is installed "
                                    "(an alias, a dict value, a default argument, a partial, a class attribute, a closure, a property's getter, an instance attribute), "
                                    "so a call through it reaches the real module past the recorder: %r (what this walk does not enter, by path and kind: %r)" % (bound, sorted(boundary)))
        self.assertEqual(_unreadable(boundary), [], "an object in the lab module's namespace the identity walk cannot read (no instance dict, no holder shape it knows: an "
                                                    "iterator, a C-level object), so a spawning function could sit in it unseen by this recorder: %r" % (_unreadable(boundary),))
        self.assertEqual(_beyond_depth(boundary), [], "a holder in the lab module's namespace past the identity walk's depth bound, not entered, so a spawning function "
                                                      "could sit in it unseen by this recorder (widen the bound or flatten the holder): %r" % (_beyond_depth(boundary),))
        seen = []
        real = subprocess

        class Recorder:
            def __getattr__(self, name):
                # every spawning function is a class attribute of the recorder, so a dunder lookup asking for one is a road
                # around the record (pass 10's fixer pass: `subprocess.__getattr__("ru" + "n")` under the recorder ran unrecorded)
                if name in SPAWNERS:
                    raise AssertionError("the recorder's __getattr__ was asked for %s: a spawning function is reached only as its class attribute" % name)
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
        """The instrument itself (pass 8's fixer pass, after a `check_call` sweep passed the `run`-and-`Popen` recorder): under
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
            with self.assertRaises(AssertionError, msg="the recorder's own __getattr__ hands out no spawning function (a dunder lookup would reach the real one unrecorded)") as cm:
                L.subprocess.__getattr__("run")
            self.assertIn("__getattr__ was asked for run", str(cm.exception),
                          "the recorder's own refusal, naming the spawning name it was asked for, not any red (the maintainer's round 4 addendum: a bare "
                          "assertRaises is satisfied by the cell's own breakage): %s" % cm.exception)
            self.assertIs(L.subprocess.__getattr__("PIPE"), subprocess.PIPE, "...and delegates every other name")

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
        # the fifth road's live instance (the module docstring): the recorded clone and checkout start programs of git's own, which
        # no census here reads, and a hook in a user's or the system's git config would be one; the floor conftest.py sets for
        # every pytest process is what keeps git from reading such a config, pinned here as the precondition of the mint
        self.assertEqual(os.environ.get("GIT_CONFIG_GLOBAL"), os.devnull, "the mint runs under the git floor: GIT_CONFIG_GLOBAL at os.devnull (tests/conftest.py), so the recorded "
                                                                              "commands read no user config and start no hook from one")
        self.assertTrue(os.environ.get("GIT_CONFIG_NOSYSTEM"), "the mint runs under the git floor: GIT_CONFIG_NOSYSTEM set (tests/conftest.py), so no system config is read either")
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
        subprocess at all: the lab's rmtree takes the checkout, and no git command of the class names the source (the maintainer's round 1's
        teardown ran a repo-wide record clearing there). The mint runs first under the spy, so a teardown step conditioned
        on the mint (old_hub_wt set, the maintainer's round 1 defect's own shape) is exercised; pass 5 found the pin spied a teardown
        with nothing minted, which such a step never entered. Behavioural, so the spelling of an argv token cannot matter,
        and the recorder sees every spawning function of the subprocess module alike (SPAWNERS), so the function it was
        issued through cannot matter either (the maintainer's round 3, tests-2: a `Popen` sweep with assembled tokens passed the `run` spy, and pass 8's fixer pass: a
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
        single-quoted spelling is seen as the double-quoted one is (the maintainer's round 2: the pin matched one quoting and passed the
        other). A cheap census beside the two spies, and only a census: a token assembled at run time is theirs to catch."""
        with open(L.__file__, encoding="utf-8") as f:
            src = f.read()
        constants = {n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertTrue(constants, "the lab module was parsed and has string constants")
        found = sorted(tok for tok in FORBIDDEN_ARGV if tok in constants)
        self.assertEqual(found, [], "string constants in the lab module that name a worktree, a record clearing or a collection: %r" % (found,))
        self.assertNotIn("_remove_old_hub", src, "the teardown has no git step of its own: the lab's rmtree takes the checkout")

    def test_the_lab_module_and_its_imports_carry_no_road_to_a_process_the_census_enumerates(self):
        """The census the module docstring names, keyed on the road (the maintainer's round 4; pass 8's fixer pass disclosed the first roads
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
                 ('import test_federated_dial_terms_served as _dial\ngetattr(_dial, "subproce" + "ss").run(["true"])\n', "getattr(_dial, <a name built at run time>"),
                 ('import uuid\ngetattr(uuid, "getn" + "ode")()\n', "getattr(uuid, <a name built at run time>"),
                 ('from unittest import mock\ngetattr(mock, NAME)\n', "getattr(mock, <a name built at run time>"),
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
                 ('from importlib import import_module\n', "from importlib import import_module"),
                 # the dunder roads (pass 9's fixer pass): a function's globals, a module's spec and loader, an object's type,
                 # code, closure, wrapped function, bound self and function, and the builtins by a bare name
                 ('import subprocess\nsubprocess.CompletedProcess.__init__.__globals__["run"](["true"])\n', ".__globals__"),
                 ('import subprocess\nsubprocess.__spec__.loader.exec_module(m)\n', ".__spec__"),
                 ('import subprocess\nsubprocess.__loader__.exec_module(m)\n', ".__loader__"),
                 ('__builtins__["__imp" + "ort__"]("sub" + "process")\n', "__builtins__"),
                 ('x.__builtins__["__imp" + "ort__"]\n', ".__builtins__"),
                 ('type(x).__subclasses__()\n', ".__subclasses__"),
                 ('x.__class__.__mro__\n', ".__class__"),
                 ('f.__code__\n', ".__code__"),
                 ('f.__closure__[0].cell_contents\n', ".__closure__"),
                 ('f.__wrapped__\n', ".__wrapped__"),
                 ('m.__self__\n', ".__self__"),
                 ('m.__func__\n', ".__func__"),
                 # pass 10's fixer pass: a second binding of the name subprocess; a spawn or a callable at import time; a
                 # reflective primitive read bare or handed a built name over any value; a bytes constant; __getattr__
                 ('def f():\n    import subprocess\n    return subprocess.run(["true"])\n', "import subprocess inside a function or a class"),
                 ('class K:\n    import subprocess\n', "import subprocess inside a function or a class"),
                 ('def f():\n    global subprocess\n    import subprocess\n', "global subprocess"),
                 ('def f():\n    nonlocal subprocess\n', "nonlocal subprocess"),
                 ('subprocess = None\n', "subprocess bound by an assignment"),
                 ('def f(subprocess):\n    return subprocess\n', "subprocess bound as a parameter"),
                 ('from unittest import mock as subprocess\n', "from unittest import ... as subprocess"),
                 ('import subprocess\n_p = subprocess.run(["true"])\n', "subprocess.run(...) outside every function body"),
                 ('import subprocess\nclass K:\n    r = subprocess.check_call(["true"])\n', "subprocess.check_call(...) outside every function body"),
                 ('import subprocess\ndef f(x=subprocess.run(["true"])):\n    return x\n', "subprocess.run(...) outside every function body"),
                 ('import subprocess\n@subprocess.Popen(["true"]).wait\ndef f():\n    pass\n', "subprocess.Popen(...) outside every function body"),
                 ('import threading\nthreading.Thread(target=lambda: 1).start()\n', "a callable handed to a call outside every function body (threading.Thread)"),
                 ('import signal\ndef h(*a):\n    pass\nsignal.signal(signal.SIGUSR2, h)\n', "a callable handed to a call outside every function body (signal.signal)"),
                 ('class K:\n    def m(self):\n        pass\n    t = list(map(lambda x: x, []))\n', "a callable handed to a call outside every function body (map)"),
                 ('_gi = __import__\n', "__import__ read bare"),
                 ('_ga = getattr\n', "getattr read bare"),
                 ('list(map(exec, ["1"]))\n', "exec read bare"),
                 ('import os\n_o = os\ngetattr(_o, "sys" + "tem")\n', "getattr(_o, <a name built at run time>"),
                 ('import os\nclass H:\n    m = os\ngetattr(H.m, NAME)\n', "getattr(H.m, <a name built at run time>"),
                 ('setattr(x, "subpro" + "cess", y)\n', "setattr(x, <a name built at run time>"),
                 ('hasattr(x, n)\n', "hasattr(x, <a name built at run time>"),
                 ('from builtins import getattr as g\n', "from builtins import getattr"),
                 ('b"subprocess".decode()\n', '"subprocess"'),
                 ('x.__getattr__("ru" + "n")\n', ".__getattr__"),
                 # the reach through an allowed module's own imports, resolved by the modules' import tables (pass 10's fixer
                 # pass, plants-10), and a member of a source-less module the censused set does not read; the roads through THIS
                 # interpreter's standard library are the ones every Python of the matrix holds (pass 11: two plants through
                 # unittest.mock's pkgutil import expected a refusal Python 3.10's mock, which imports no pkgutil, rightly did not
                 # give; the reach rule itself is pinned below over a synthetic standard library, a road that exists by construction)
                 ('from unittest import mock\nmock.builtins.__import__(NAME)\n', "unittest.mock.builtins reaches builtins"),
                 ('from unittest import mock\nmock.partial(f, x)\n', "unittest.mock.partial reaches functools"),
                 ('import subprocess\nsubprocess.builtins\n', "subprocess.builtins reaches builtins"),
                 ('import http.server\nclass F(http.server.socketserver.ForkingMixIn):\n    pass\n', "http.server.socketserver reaches socketserver"),
                 ('import sys\nsys._getframe(0)\n', "sys._getframe a member of sys, a module whose source the census cannot read"),
                 ('import sys as _s\n_s.meta_path\n', "sys.meta_path a member of sys"),
                 ('from unittest import mock\nmock.sys.modules\n', "sys.modules a member of sys"),
                 ('import time\ntime.perf_counter()\n', "time.perf_counter a member of time"),
                 # pass 11 (the maintainer's round 6, extra6-1): the from-import BINDING of the same members, resolved by _reach from the member on
                 ('from sys import _getframe\ndef f():\n    return _getframe(0)\n', "from sys import _getframe: sys._getframe a member of sys"),
                 ('from sys import meta_path\n', "from sys import meta_path: sys.meta_path a member of sys"),
                 ('from sys import modules\ndef f():\n    return modules["subpro" + "cess"]\n', "from sys import modules: sys.modules a member of sys"),
                 ('from unittest.mock import builtins\n', "from unittest.mock import builtins: unittest.mock.builtins reaches builtins, a module ALLOWED_IMPORTS does not name, through unittest.mock's own import"),
                 ('from unittest.mock import builtins as _b\n', "from unittest.mock import builtins: unittest.mock.builtins reaches builtins"),
                 ('from unittest.mock import partial as _p\n', "unittest.mock.partial reaches functools"),
                 # pass 11's fixer pass: a star import from any module binds names the census cannot resolve (the os arm above refused
                 # `from os import *` alone, and `from sys import *` then a read of the star-bound `modules` was silent on both interpreters)
                 ('from sys import *\ndef f():\n    return modules["subpro" + "cess"].run(["true"])\n', "from sys import * (a star import binds names the census cannot resolve)"),
                 ('from unittest.mock import *\n', "from unittest.mock import * (a star import binds names the census cannot resolve)"))
        for src, form in forms:
            with self.subTest(form=form, src=src):
                hits = _commands_around_the_recorder(src, siblings=("test_federated_dial_terms_served",))
                self.assertTrue(any(form in h[1] for h in hits), "the detector refuses %r as %r: %r" % (src, form, hits))
        # the reach rule over a synthetic standard library, a road that exists BY CONSTRUCTION on every Python (pass 11): an allowed
        # module (uuid, spelled as the synthetic library's own) whose source imports a module ALLOWED_IMPORTS does not name, reached
        # as an attribute, through an alias and as a from-import binding; the same module's import of an allowed module is no road
        top = tempfile.mkdtemp(prefix="linkdrop-reach-")
        self.addCleanup(shutil.rmtree, top, True)
        for name, src in (("uuid", "import notallowed\nimport os\n"), ("notallowed", "x = 1\n"), ("os", "path = 1\n")):
            with open(os.path.join(top, name + ".py"), "w", encoding="utf-8") as f:
                f.write(src)
        built = (('import uuid\nuuid.notallowed.x\n', "uuid.notallowed reaches notallowed, a module ALLOWED_IMPORTS does not name, through uuid's own import"),
                 ('import uuid as u\nu.notallowed\n', "uuid.notallowed reaches notallowed"),
                 ('from uuid import notallowed\n', "from uuid import notallowed: uuid.notallowed reaches notallowed"),
                 ('from uuid import notallowed as _n\n', "from uuid import notallowed: uuid.notallowed reaches notallowed"))
        for src, form in built:
            with self.subTest(form=form, src=src, stdlib="synthetic"):
                hits = _commands_around_the_recorder(src, siblings=("lab_dist",), stdlib=top)
                self.assertTrue(any(form in h[1] for h in hits), "the detector refuses %r as %r over the synthetic standard library: %r" % (src, form, hits))
        self.assertEqual(_commands_around_the_recorder('import uuid\nuuid.os.path\n', siblings=("lab_dist",), stdlib=top), [],
                         "an allowed module reached through the synthetic module's own import is no road")
        allowed = ('import os\nimport subprocess\nimport sys\nimport lab_dist\nfrom . import lab_dist_stub\nfrom tests import fs_clock\n'
                   'HERE = os.path.dirname(os.path.realpath(__file__))\nsys.path.insert(0, HERE)\n'
                   'def f():\n    import select\n    subprocess.run(["true"], stdout=subprocess.PIPE)\n    p = subprocess.Popen(["true"])\n    return select.select([], [], [], 0)\n'
                   'def g(cb=None):\n    return cb\ndef h():\n    return g(lambda: 1)\nos.path.join("a", "b")\n'
                   'getattr(cls, "procs", [])\ngetattr(type(self), "result", None)\ngetattr(lab_dist, "build", None)\nhasattr(x, "y")\n"""os.system in a docstring; exec and eval too"""\n'
                   'import time\nimport http.server\nimport urllib.request\nfrom unittest import mock\nfrom pathlib import Path\nfrom unittest.mock import patch as _patch\nfrom sys import path as _syspath\n'
                   'def k():\n    time.monotonic()\n    time.sleep(1)\n    mock.patch.object(a, "b", c)\n    http.server.ThreadingHTTPServer\n    urllib.request.urlopen(u)\n    subprocess.PIPE\n    subprocess.os.path\n    Path.home()\n'
                   # the residual's road (4) after the recorder is lifted, stated and NOT refused: a callable deferred past it from inside a function body
                   'import threading\ndef w():\n    threading.Timer(0.2, lambda: subprocess.run(["true"])).start()\n')
        self.assertEqual(_commands_around_the_recorder(allowed, siblings=("lab_dist", "fs_clock")), [], "the allowed spellings (a spawner CALLED inside a function body, a nested import of another module, a "
                                                                                                          "module-level call with no callable argument, a lambda handed to a call inside a function, a constant name to getattr or hasattr, a module's own "
                                                                                                          "definition or an allowed module reached through a binding, a source-less module's member the set reads, as an attribute or as a from-import "
                                                                                                          "binding; `patch` from unittest.mock is mock's own definition and stays the disclosed class; a callable deferred by a timer inside a "
                                                                                                          "function body, the residual's road (4) after the recorder is lifted), and the words in a docstring, are not refused")
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
        censused modules make today (a module added or dropped in one of them is a red until the tuple says so), none of
        the eight names of DENIED_IMPORTS is among them (a deny list, the check's key; which allowed modules start a program
        inside their own source is not this cell's claim but the next cell's derivation), and UNREAD_MEMBERS equals the members
        the set reads on the modules whose source the scan cannot read (pass 10's fixer pass: `sys._getframe(0).f_builtins`
        and `sys.meta_path` reached a loader with no red, since sys has no source to scan)."""
        for modname, names in OTHER_SPAWNERS.items():
            with self.subTest(module=modname):
                top, _, attr = modname.partition(".")
                mod = OTHER_SPAWNER_MODULES[top]
                holder = getattr(mod, attr) if attr else mod
                self.assertEqual([n for n in names if not hasattr(holder, n)], [], "every name filed under %s is its attribute on this Python" % modname)
                if top != "os":   # os is an allowed import (os.path and the rest): its fork and forkpty are refused as attributes and bare calls alone
                    self.assertNotIn(top, ALLOWED_IMPORTS, "a spawner family's module is outside the import allow-list: %s" % top)
        mods = _lab_modules()
        self.assertEqual(sorted(_foreign_imports(mods)), sorted(ALLOWED_IMPORTS), "ALLOWED_IMPORTS is exactly the foreign imports the censused modules make (%s)" % ", ".join(sorted(mods)))
        self.assertEqual([m for m in DENIED_IMPORTS if m in ALLOWED_IMPORTS], [],
                         "none of the eight names of DENIED_IMPORTS (%s) is allowed: a deny list, keyed on these names and nothing else" % ", ".join(DENIED_IMPORTS))
        _, unread = _foreign_spawn_roads(mods)
        self.assertEqual(_unread_member_reads(mods, unread), {m: list(v) for m, v in UNREAD_MEMBERS.items()},
                         "UNREAD_MEMBERS is exactly the members the censused set reads on the foreign modules whose source the scan cannot read (%s): a member of such a module is a "
                         "name the census cannot resolve, so one the set starts or stops reading is a red until the table says so" % ", ".join(sorted(unread)))

    def test_the_foreign_modules_whose_own_source_starts_a_program_are_derived(self):
        """The third road (the module docstring), derived and pinned: _foreign_spawn_roads over the censused set reads the
        own source of every module its import bindings load, by path, and names the modules that start a program inside it.
        The derived set is held EQUAL to FOREIGN_ROADS (pass 10's fixer pass: the cell pinned a subset, so a fifth road could
        not red it): on this Python uuid (its node lookup runs a program when the _uuid extension is absent), subprocess
        itself (its _posixsubprocess import and os.posix_spawn), http.server (the CGI handler's fork and exec, deprecated
        upstream), os (os.popen's body calls subprocess.Popen) and unittest.mock (it imports asyncio, a spawner family's
        module, a road by the scan's own rule; read since the fixer pass, when `from unittest import mock` was read as an
        import of unittest alone), so a Python that drops one or an import that adds one changes this tuple and the docstring's
        example. Every unread module is unread for a reason the scan can account for (built in, an extension module), never
        for a missing source, and every road module is a module the set loads. The second family, the modules whose own
        source resolves a name from a string (_foreign_reflective_roads), is non-empty on this Python and every entry is a
        loaded module. Then over a synthetic standard library: a module whose source calls a spawner, one that imports pty, a
        package whose submodule imports pty and is imported by `from pkg import sub` (the road is the SUBMODULE), one whose
        package __init__ is clean, one that runs exec (a reflective road, not a spawner one) and one with no source, imported
        by a synthetic censused module, give exactly the three spawner roads, the one reflective road and the one unread name
        (red before the derivation existed; the submodule and the reflective road red before the fixer pass)."""
        mods = _lab_modules()
        roads, unread = _foreign_spawn_roads(mods)
        self.assertEqual(sorted(roads), sorted(FOREIGN_ROADS), "the foreign modules whose own source starts a program, on this Python, are exactly FOREIGN_ROADS (a new import or a "
                                                              "changed Python source moves this set: read the road, then the tuple): %r" % ({k: v for k, v in roads.items()},))
        reflective = _foreign_reflective_roads(mods)
        self.assertTrue(reflective, "the derivation names the foreign modules whose own source resolves a name from a string: %r" % (reflective,))
        dotted = _dotted_foreign_imports(mods)
        self.assertLessEqual(set(reflective), dotted, "every reflective road is a module the set loads")
        self.assertLessEqual(set(roads) | set(unread), dotted, "every road and every unread name is a dotted foreign import of the censused set")
        self.assertEqual({name: why for name, why in unread.items() if "no source found" in why}, {}, "a module the scan could not read and cannot account for (no source anywhere) is a red, not a dropped name: %r" % (unread,))
        self.assertTrue(unread, "the built-in and extension modules among the imports are named as unread, not dropped: %r" % (unread,))
        for name, sites in roads.items():
            with self.subTest(road=name):
                self.assertTrue(sites and all(isinstance(ln, int) and form for ln, form in sites), "each road carries its sites by line and form: %r" % (sites,))
        top = tempfile.mkdtemp(prefix="linkdrop-stdlib-")
        self.addCleanup(shutil.rmtree, top, True)
        os.makedirs(os.path.join(top, "cleanpkg"))
        os.makedirs(os.path.join(top, "pkg"))
        with open(os.path.join(top, "spawner.py"), "w", encoding="utf-8") as f:
            f.write('import subprocess\ndef run(c):\n    return subprocess.run(c)\n')
        with open(os.path.join(top, "importer.py"), "w", encoding="utf-8") as f:
            f.write('import pty\n')
        with open(os.path.join(top, "cleanpkg", "__init__.py"), "w", encoding="utf-8") as f:
            f.write('import os\nx = os.path.join("a", "b")\n')
        with open(os.path.join(top, "pkg", "__init__.py"), "w", encoding="utf-8") as f:
            f.write('import os\n')
        with open(os.path.join(top, "pkg", "sub.py"), "w", encoding="utf-8") as f:
            f.write('import pty\n')
        with open(os.path.join(top, "runner.py"), "w", encoding="utf-8") as f:
            f.write('def go(text):\n    exec(text)\n')
        # pass 11 (the maintainer's round 6, extra6-2): the os family through an alias (module-level and function-local) and a spawner
        # imported by name are roads; a module held on an instance or bound by an assignment is not resolved (the stated residual)
        with open(os.path.join(top, "aliased.py"), "w", encoding="utf-8") as f:
            f.write("import os as _os\ndef go():\n    _os.execv('/bin/true', ['true'])\n")
        with open(os.path.join(top, "fnlocal.py"), "w", encoding="utf-8") as f:
            f.write("def go():\n    import os as o2\n    return o2.system('true')\n")
        with open(os.path.join(top, "fromos.py"), "w", encoding="utf-8") as f:
            f.write("from os import system, path\ndef go():\n    return system('true')\n")
        with open(os.path.join(top, "objheld.py"), "w", encoding="utf-8") as f:
            f.write("import os\nclass C:\n    def __init__(self):\n        self._os = os\n    def go(self):\n        return self._os.execv('/bin/true', ['true'])\n")
        with open(os.path.join(top, "assigned.py"), "w", encoding="utf-8") as f:
            f.write("import os\n_o = os\ndef go():\n    return _o.popen('true')\n")
        # pass 11's fixer pass: a star import from an os-family module is a road (it binds every name, a spawner among them); a spawner
        # reached as another module's attribute is not resolved (the stated residual: the scan reads a NAME the imports bind, and nothing else)
        with open(os.path.join(top, "starimport.py"), "w", encoding="utf-8") as f:
            f.write("from os import *\ndef go():\n    return system('true')\n")
        with open(os.path.join(top, "chained.py"), "w", encoding="utf-8") as f:
            f.write("import os\ndef go():\n    return os.path.os.system('true')\n")
        synthetic = {"root": "import spawner\nimport importer\nimport cleanpkg.sub\nimport nosource\nfrom pkg import sub\nimport runner\nimport aliased\nimport fnlocal\nimport fromos\nimport objheld\nimport assigned\nimport starimport\nimport chained\n"}
        roads, unread = _foreign_spawn_roads(synthetic, stdlib=top)
        self.assertEqual(roads, {"importer": [(1, "import pty")], "pkg.sub": [(1, "import pty")], "spawner": [(1, "import subprocess"), (3, "subprocess.run")],
                                 "aliased": [(3, "os.execv")], "fnlocal": [(3, "os.system")], "fromos": [(1, "from os import system"), (3, "os.system()")],
                                 "starimport": [(1, "from os import * (every name of the module, a spawner among them)")]},
                         "a module whose source imports a spawner family or calls a spawner is a road, by line and form, a submodule imported by `from pkg import sub` as itself, "
                         "an alias of os (module-level or function-local) resolved to os, a spawner imported by name read at its import and its call, and a star import from an "
                         "os-family module read at the import; a clean package, a reflective module, a module held on an instance, one bound by an assignment and a spawner "
                         "reached as another module's attribute are not (the last three are the stated residual: the scan resolves a name the imports bind, and nothing else)")
        self.assertEqual(unread, {"cleanpkg.sub": "no source found under the standard library", "nosource": "no source found under the standard library"},
                         "a module with no source is unread with its reason, never dropped")
        self.assertEqual(_foreign_reflective_roads(synthetic, stdlib=top), {"runner": [(2, "exec(")]}, "a module whose own source runs exec is a reflective road, by line and form; the spawner roads are not")
        self.assertEqual(_unread_member_reads({"m": "import sys\nfrom sys import meta_path, path as _p\nsys.argv\ndef f():\n    return meta_path, _p\n"}, {"sys": "built in (no Python source)"}),
                         {"sys": ["argv", "meta_path", "path"]}, "a member read on a source-less module counts as an attribute and as a from-import binding alike (the maintainer's round 6, extra6-1)")
        self.assertEqual(_import_bindings("import a.b.c\nimport a.b as x\nfrom pkg import sub, other\nfrom pkg.sub import thing as t\nfrom . import sibling\n", stdlib=top),
                         ({"a": ("a", None), "x": ("a.b", None), "sub": ("pkg.sub", None), "other": ("pkg", "other"), "t": ("pkg.sub", "thing")}, {"a", "a.b", "a.b.c", "pkg", "pkg.sub"}),
                         "the bindings: a dotted import binds its first name, an alias the whole module, a from-import the submodule when the standard library holds its source and else the member; a relative import binds nothing without a package")

    def test_the_touch_derivation_keys_on_the_binding_not_the_spelling(self):
        """_foreign_touch_sites over a synthetic censused set (pass 10's fixer pass): a road module reached through its bare name,
        an alias, a from-imported name and a submodule alias is one touch each, spelled by the module's name, and a module that
        is no road, or a name imported from one that is a class (`Path`), is none. Red before the fixer pass for every spelling
        but the bare one."""
        mods = {"a": "import uuid\nuuid.uuid4()\nuuid.getnode()\n",
                "b": "import uuid as u\nu.getnode()\n",
                "c": "from uuid import getnode\ngetnode()\n",
                "d": "import http.server as hs\nclass F(hs.HTTPServer):\n    pass\n",
                "e": "from unittest import mock\nmock.patch.object(x, 'y', z)\nimport pathlib\npathlib.Path('.')\nfrom pathlib import Path\nPath.home()\n"}
        roads = {"uuid": [], "http.server": [], "unittest.mock": [], "os": [], "subprocess": []}
        self.assertEqual(_foreign_touch_sites(mods, roads),
                         [("a", 2, "uuid.uuid4"), ("a", 3, "uuid.getnode"), ("b", 2, "uuid.getnode"), ("c", 2, "uuid.getnode"), ("d", 2, "http.server.HTTPServer"), ("e", 2, "unittest.mock.patch.object")],
                         "a touch is keyed on the name the import binds and spelled by the module; a module outside the roads and a class imported by name are none")

    def test_the_recorder_refuses_a_spawning_function_bound_before_it_is_installed(self):
        """The recorder's side of the alias road (pass 9): _bound_spawners over a synthetic module finds, by identity and by
        path, an alias at module level, a dict value, a default argument, a keyword default, a functools.partial, a class
        attribute of the module's own class, a closure cell, a staticmethod, and (the fixer pass) a property's getter, a
        SimpleNamespace attribute, a bound method's function, a generator frame's local and a bound builtin method's object,
        and reports what it does not enter as the boundary by path and kind (a module object, a class of another module, an
        object it cannot read such as an iterator, and, since pass 10, a holder past its depth bound: a spawner nested ten
        or twelve dicts deep is a boundary entry of its own kind where pass 9 dropped it silently, one nested nine deep is
        found, and the holder planted in the lab module's namespace reds _spy with the depth sentence); a module that reads
        subprocess.run at call time (a lambda, a decorator, a function body) binds nothing early and is clean; the lab module
        itself is clean and holds nothing the walk cannot read or enter, which is what every _spy asserts before it patches,
        so a binding planted there reds every recorder pin (the review record outside the repo runs the plants through
        them)."""
        m = types.ModuleType("linkdrop_synthetic_module")
        m.subprocess, m.os = subprocess, os
        m._run = subprocess.run
        m.SPAWN = {"run": subprocess.Popen}
        exec("def _sweep(run=subprocess.run):\n    return run\ndef _kw(*, call=subprocess.call):\n    return call\n"
             "def _mk():\n    f = subprocess.check_call\n    return lambda c: f(c)\n_closed = _mk()\n"
             "class _Sp:\n    out = staticmethod(subprocess.check_output)\n    go = subprocess.getoutput\n"
             "_L = lambda c: subprocess.run(c)\ndef _late(c):\n    return subprocess.Popen(c)\n"
             "def _g(f=subprocess.call):\n    yield f\n_gen = _g()\n_app = [subprocess.Popen].append\n", vars(m))
        m._Sp.__module__ = m.__name__
        m._partial = functools.partial(subprocess.getstatusoutput)
        m._ns = types.SimpleNamespace(r=subprocess.run)
        m._prop = property(subprocess.getoutput)
        m._meth = types.MethodType(subprocess.check_output, m._ns)
        m._it = iter((subprocess.run,))
        m.Foreign = unittest.TestCase
        found, boundary = _bound_spawners(m)
        self.assertEqual(sorted(found), sorted([("_run", "run"), ("SPAWN['run']", "Popen"), ("_sweep.__defaults__[0]", "run"), ("_kw.__kwdefaults__['call']", "call"),
                                                ("_closed.<closure 0>", "check_call"), ("_Sp.out.__func__", "check_output"), ("_Sp.go", "getoutput"), ("_partial.func", "getstatusoutput"),
                                                ("_g.__defaults__[0]", "call"), ("_gen.<frame f>", "call"), ("_app.__self__[0]", "Popen"),
                                                ("_ns.r", "run"), ("_prop.fget", "getoutput"), ("_meth.__func__", "check_output")]),
                         "every early binding is found by identity and named by its path")
        self.assertEqual(sorted(boundary), [("Foreign", "class of unittest.case"), ("_it", "tuple_iterator the walk cannot read"), ("os", "module"), ("subprocess", "module")],
                         "the module objects, the foreign class and the iterator are the boundary the walk does not enter, reported beside the findings by path and kind")
        self.assertEqual(_unreadable(boundary), [("_it", "tuple_iterator the walk cannot read")], "the iterator is what the walk could not read, and what _spy refuses")
        clean = types.ModuleType("linkdrop_synthetic_clean")
        clean.subprocess = subprocess
        exec("_L = lambda c: subprocess.run(c)\ndef _late(c):\n    return subprocess.Popen(c)\n", vars(clean))
        self.assertEqual(_bound_spawners(clean)[0], [], "a read of the attribute at call time binds nothing early: the recorder sees it")
        # the depth bound (pass 10): a spawner nested past the bound is a boundary entry of its own kind, refused by _spy with
        # its own sentence; one at the last entered level is still FOUND, not a boundary
        for levels, want_found in ((9, True), (10, False), (12, False)):
            with self.subTest(levels=levels):
                deep = types.ModuleType("linkdrop_synthetic_deep")
                holder = subprocess.run
                for _ in range(levels):
                    holder = {"d": holder}
                deep.deep = holder
                stats = {}
                found, boundary = _bound_spawners(deep, stats=stats)
                if want_found:
                    self.assertEqual(found, [("deep" + "['d']" * levels, "run")], "a spawner at the last level the walk enters is found: %r" % (found,))
                    self.assertEqual(_beyond_depth(boundary), [], "…and no holder is past the bound: %r" % (boundary,))
                    self.assertEqual(stats["max_depth"], 8, "the walk entered to its bound: %r" % (stats,))
                else:
                    self.assertEqual(found, [], "a spawner past the bound is not found…")
                    self.assertEqual(_beyond_depth(boundary), [("deep" + "['d']" * 9, "beyond the walk's depth of 8")],
                                     "…and the holder at the cut is a boundary entry of its own kind, so the recorder refuses what it did not enter: %r" % (boundary,))
                    self.assertEqual(_unreadable(boundary), [], "a depth cut is not an unreadable object: it rides its own sentence")
        # ...and the recorder's own refusal of it: a holder past the bound planted in the lab module's namespace reds every _spy
        # caller with the depth sentence before any recorder is installed (the lab module holds no such holder today, so this
        # plant is what exercises the assertion)
        holder = subprocess.run
        for _ in range(10):
            holder = {"d": holder}
        with mock.patch.object(L, "_deep_probe", holder, create=True):
            with self.assertRaises(AssertionError, msg="a spawner past the walk's depth bound in the lab module reds _spy") as cm:
                self._spy()
        self.assertIn("past the identity walk's depth bound", str(cm.exception), "the refusal is the depth sentence, not the unreadable one: %s" % cm.exception)
        bound, boundary = _bound_spawners(L)
        self.assertEqual(bound, [], "the lab module binds no spawning function before the recorder is installed: %r" % (bound,))
        self.assertEqual(_unreadable(boundary), [], "the lab module holds nothing the identity walk cannot read: %r" % (_unreadable(boundary),))
        self.assertTrue({"subprocess", "os", "lab_dist"} <= {path for path, kind in boundary if kind == "module"}, "the lab module's module objects are the walk's boundary: %r" % (sorted(boundary),))

    def test_what_the_census_cannot_see_is_a_rule_with_its_list_derived(self):
        """The disclosure, derived where it is read and never counted (the maintainer's round 4: the earlier docstring said two roads remained
        unseen and named a third's class wrongly; the maintainer's round 5: the rewritten residual then shrank while the blind
        set grew). The rule is the module docstring's: the census refuses the nodes it enumerates and nothing else, and on the
        recorder's side a spawning call whose source is outside the lab module's attribute and the censused sources is unseen.
        Derived here: road (1), the censused modules' own calls of a spawning function through their own subprocess binding
        (_own_spawn_sites; every such site is outside the lab module by construction, and no name is held here: the list is
        what the derivation prints); roads (2) and (3), the foreign modules whose own source starts a program
        (_foreign_spawn_roads, with the modules it could not read named as unread), the second family that resolves a name
        from a string (_foreign_reflective_roads), where the censused set touches the road modules other than os and
        subprocess (_foreign_touch_sites, by binding) and the members it reads on the source-less modules
        (_unread_member_reads); road (4), the import-time surface (_import_time_statements); and what _bound_spawners does
        not enter, by path and kind, with the depth it reached against its bound. Each list is printed to stdout, which pytest shows for a passed test under -rA or -s, and
        carried in an assertion's message for a red, so a run's record can carry the derived residual as it stood (pass 9's
        fixer pass: the lists sat in assertion messages alone, which a green run never prints; the maintainer's round 5, tests-3:
        the prints themselves are pinned, the cell's stdout captured, asserted to carry each list and re-emitted). Its two
        assertions over the sites state what they check about the DERIVATION (the maintainer's round 5, extra6-3): the
        derivation files no site for the lab module by construction (the lab module's own calls are the recorder's, pinned by
        test_the_recorder_sees_every_spawning_function_once_and_delegates_the_rest), and every filed site names a module the
        census read."""
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                mods = _lab_modules()
                sites = _own_spawn_sites(mods)
                print("the residual on the recorder's side, road 1, derived by _own_spawn_sites (module, line, function): %r" % (sites,))
                roads, unread = _foreign_spawn_roads(mods)
                touches = _foreign_touch_sites(mods, roads)
                reflective = _foreign_reflective_roads(mods)
                at_import = _import_time_statements(mods)
                unread_reads = _unread_member_reads(mods, unread)
                print("the residual on the recorder's side, roads 2 and 3, derived by _foreign_spawn_roads (module: [(line, form)]; direct sites in each module's own source, a module it imports being a further road): %r; unread (no Python source): %r"
                      % (roads, unread))
                print("the census's side, the second family, derived by _foreign_reflective_roads (module: [(line, form)]; a foreign module whose own source resolves a name from a string): %r" % (reflective,))
                print("where the censused set touches the road modules other than os and subprocess, derived by _foreign_touch_sites over the import bindings (module, line, dotted name): %r" % (touches,))
                print("the members the censused set reads on the modules the scan cannot read, derived by _unread_member_reads (held equal to UNREAD_MEMBERS): %r" % (unread_reads,))
                print("the residual on the recorder's side, road 4, derived by _import_time_statements (module, line, statement): what runs at import before any recorder, in the censused set: %r" % (at_import,))
                unwalked = _package_init_unwalked(mods)
                print("the package's own __init__ and the siblings only it imports, derived by _package_init_unwalked: UNWALKED (they run before the lab module under both entry points and no derivation here reads them): %r" % (unwalked,))
                stats = {}
                bound, boundary = _bound_spawners(L, stats=stats)
                print("the identity walk's boundary over the lab module, derived by _bound_spawners (path, kind): %r; the walk entered to depth %d of its bound %d"
                      % (sorted(boundary), stats["max_depth"], 8))
        finally:
            sys.stdout.write(buf.getvalue())   # re-emitted whole, so a green run still shows the lists under -rA or -s
        shown = buf.getvalue()
        for label, text in (("road 1 (the sites)", repr(sites)), ("roads 2 and 3 (the foreign roads)", repr(roads)), ("road 3 (the unread modules)", repr(unread)),
                            ("the reflective roads", repr(reflective)), ("the touches", repr(touches)), ("the unread member reads", repr(unread_reads)),
                            ("road 4 (the import-time statements)", repr(at_import)), ("the unwalked package init and its own siblings", repr(unwalked)), ("the boundary", repr(sorted(boundary)))):
            self.assertIn(text, shown, "the disclosure cell prints its %s list, so a run's record carries the derived residual: %r" % (label, shown[:300]))
        self.assertGreaterEqual(len(unwalked), 2, "the package's __init__ and at least one sibling only it imports are derived as unwalked (this directory is a package whose "
                                                  "__init__ imports siblings; a list of nothing where something is due proves nothing): %r" % (unwalked,))
        self.assertEqual([n for n in unwalked if n in mods], [], "an unwalked name inside the censused set: the derivation and the census disagree: %r" % (unwalked,))
        self.assertEqual([n for n in unwalked if not os.path.isfile(os.path.join(HERE, n + ".py"))], [], "every unwalked name is a module file here: %r" % (unwalked,))
        self.assertTrue(sites, "the derivation reads the censused modules' own spawning calls: %r" % (sites,))
        self.assertEqual([site for site in sites if site[0] == LAB_MODULE], [],
                         "the derivation files no site for the lab module by construction: its own calls are the recorder's (pinned by "
                         "test_the_recorder_sees_every_spawning_function_once_and_delegates_the_rest), so a lab-module site here is the derivation reading the wrong module: %r" % (sites,))
        self.assertTrue(all(name in mods for name, _, _ in sites),
                        "every filed site names a module the census read (a site under a module outside the censused set is a derivation over a source the census never saw): %r" % (sites,))
        self.assertTrue(roads and touches, "the derivation names the foreign roads and where the censused set reaches them: %r %r" % (roads, touches))
        self.assertTrue(reflective and at_import and unread_reads, "the derivation names the reflective roads, the import-time surface and the unread members: %r %r %r" % (reflective, at_import[:3], unread_reads))
        self.assertTrue(all(name in mods and isinstance(line, int) for name, line, _ in at_import), "every import-time statement names a censused module and a line: %r" % (at_import[:5],))
        self.assertEqual(bound, [])
        self.assertTrue(boundary, "the identity walk names what it does not enter: %r" % (sorted(boundary),))
        modules = [path for path, kind in boundary if kind == "module"]
        self.assertTrue(modules and all(isinstance(getattr(L, path.split(".")[0]), types.ModuleType) for path in modules), "each module entry is a module object: %r" % (sorted(boundary),))
        self.assertEqual(_unreadable(boundary), [], "nothing in the lab module's namespace is beyond the walk's reading (an unreadable holder is a red, not a residual): %r" % (_unreadable(boundary),))
        self.assertEqual(_beyond_depth(boundary), [], "no holder in the lab module's namespace sits past the walk's depth bound (a holder not entered is a red, not a residual): %r" % (_beyond_depth(boundary),))
        self.assertLess(stats["max_depth"], 8, "the walk's bound is above the deepest holder the lab module has, so the bound cuts nothing today: %r" % (stats,))

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
        # a PACKAGE sibling (pass 9): the walk refuses it by name rather than dropping it, so a helper in a package's __init__
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
