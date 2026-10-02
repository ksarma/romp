#!/usr/bin/env python3
"""Every served module takes its kernels' ports from tests/lab_ports.py and waits for its kernels there (2026-10-02).

WHY. The served labs drew ports by drawing and releasing (bind to port 0, read the port, close the socket) and waited for a
kernel by polling /healthz on its port until anything answered. Two draws in a row can return the same port, and an
answer on a port proves nothing about which process gave it: a federated lab whose hub was handed its remote's port read
the remote's /healthz as the hub's, and its check-in to the hub got the remote's 403 (tests/lab_ports.py says how).
tests/lab_ports.py is the door that closes both: reserve() hands out ports no live reservation holds, and wait_owned()
returns only once the kernel answering is the one the lab started, on the port it was given.

THE POPULATION is derived, never listed: the files CI's served step names (its globs and its by-file names, read from
.github/workflows/ci.yml by tests/test_served_labs_under_ci.py's readers), every module under tests/ they import, followed
to a fixed point, and tests/conftest.py, less the door itself. An import is followed in each of the seven forms a module
can name another under tests/ by (`import x`, `import tests.x`, `from x import`, `from tests.x import`, `from tests
import x`, `from . import x`, `from .x import`), each pinned by a planted helper. A glob matching nothing, a named file
absent, an empty population or a population with no kernel spawn in it fails the run, so the census never passes on
nothing.

THE RULES, each read per module by AST (scan()):
  D  no draw and release: in one scope (a function, a lambda, a class body or the module body), a socket bound to port 0
     whose port is read (getsockname) and that is released in the same scope, by close(), by a with block, or by going
     out of scope (a local name used only for its own methods), and that never listens there. A listener keeps its port
     and a holder kept on an attribute keeps it too, so neither is a draw.
  W  no hand-written /healthz wait: no call other than an assert* has an argument holding /healthz as a path or in a
     URL (at a string's start or right after a non-space: "http://127.0.0.1:%d/healthz", base + "/healthz", an
     f-string's "{p}/healthz"). Prose that mentions it after a space (a skip's "never served /healthz here") is not a
     request, an assertion over results keyed by the route asks nothing, and a node driver's /healthz inside a JavaScript
     text that Python only writes to a file is not a call argument.
  K  every function that starts the kernel (a Popen whose argv names romp-kernel, directly or through a name the module
     binds to an expression naming it) calls lab_ports.wait_owned; a spawn outside any function is an offence too.
  R  a module that reserves a port, through lab_ports.reserve or through kernel_env (which reserves the kernel's postal
     port), calls lab_ports.release.
  A  the door is bound under its own name only and its members are read as lab_ports.<name>: no `import lab_ports as
     x`, no `import tests.lab_ports` (it binds tests), no `from tests import lab_ports as x` or `from . import lab_ports
     as x`, no from-import of its members (`from lab_ports import wait_owned`, `from .lab_ports import reserve`), and no
     assignment of the bare name lab_ports (`lp = lab_ports`). Each would hide the calls the rules above read.
     `import lab_ports`, `from tests import lab_ports` and `from . import lab_ports` all bind the name lab_ports.
At run time wait_owned itself refuses a port that was not reserved in the process, which covers a port drawn by a road
the AST does not read.

WHAT IT CANNOT SEE (stated, not closed): a draw split across functions, or reached through getattr or partial; a port
picked without a bind; Python inside a subprocess -c string; a JavaScript wait on a kernel the node driver relaunches in
place (tests/test_ship_reship_served.py and tests/test_dashboard_reload_served.py relaunch from the driver and wait
there); a kernel started by a shell or by a name bound outside the module; a module imported by a computed name;
readiness read by another road than an HTTP call naming /healthz; the door handed to a call as an argument
(getattr(lab_ports, name); the mock.patch.object(lab_ports, ...) in tests/test_federated_linkdrop_served.py is such a
hand-off and is green) or bound by a for, a with or a default argument. The planted modules below are each red under exactly
the rule they break, and the clean shapes (a listener, a kept holder, the door's own use, a /healthz inside a JavaScript
text) are green.

Synthetic: reads the tree only; no kernel, no browser, no socket.
"""
import ast
import glob
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import parse_cache                                  # noqa: E402  one parse per file per process, shared with the other AST censuses
import test_served_labs_under_ci as _ci             # noqa: E402  the served step's readers (the module, so its tests are not collected twice)

DOOR = "lab_ports"
DOOR_FILE = DOOR + ".py"
RULES = ("D", "W", "K", "R", "A")
SPAWN_CALLEES = {"Popen"}
KERNEL_NAME = "romp-kernel"


def _module_imports(tree, local):
    """The tests/ modules `tree` imports, as file names: `import x` and `import tests.x`, `from x import ...` and
    `from tests.x import ...`, `from tests import x, y` (each name that is a module under tests/), and the relative forms a
    module inside tests/ can use, `from . import x, y` (each name) and `from .x import ...`."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and not n.level and n.module == "tests":
            mods = ["tests." + a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and not n.level and n.module:
            mods = [n.module]
        elif isinstance(n, ast.ImportFrom) and n.level == 1:
            mods = [n.module] if n.module else [a.name for a in n.names]
        else:
            continue
        for m in mods:
            parts = m.split(".")
            base = parts[1] if parts[0] == "tests" and len(parts) > 1 else parts[0]
            if base in local:
                out.add(base + ".py")
    return out


def population(root=ROOT, globs=None, files=None):
    """The served population under `root`: (sorted file names under root/tests, {name: (text, tree)}). `globs` and
    `files` default to CI's served step's; a glob matching nothing, a named file absent or an empty result raises."""
    tests = os.path.join(root, "tests")
    globs = _ci.ci_served_globs() if globs is None else globs
    files = _ci.ci_served_files() if files is None else files
    if not globs and not files:
        raise AssertionError("the served step names no glob and no file: the census has nothing to read")
    names = set()
    for g in globs:
        hits = glob.glob(os.path.join(root, g))
        if not hits:
            raise AssertionError("the served step's glob %s matches no file under %s" % (g, root))
        names |= {os.path.basename(h) for h in hits}
    for f in files:
        if not os.path.isfile(os.path.join(root, f)):
            raise AssertionError("the served step names %s and it is absent under %s" % (f, root))
        names.add(os.path.basename(f))
    if os.path.isfile(os.path.join(tests, "conftest.py")):
        names.add("conftest.py")
    local = {f[:-3] for f in os.listdir(tests) if f.endswith(".py")}
    read, todo = {}, sorted(names)
    while todo:
        f = todo.pop()
        if f in read:
            continue
        text, tree = parse_cache.source_and_tree(os.path.join(tests, f))
        read[f] = (text, tree)
        todo.extend(sorted(_module_imports(tree, local) - set(read)))
    read.pop(DOOR_FILE, None)
    if not read:
        raise AssertionError("the served population under %s is empty" % root)
    return sorted(read), read


def _text(node):
    """A receiver's spelling (s, self._hold), or None for one that is not a name or an attribute chain."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and _text(node.value) is not None:
        return _text(node.value) + "." + node.attr
    return None


def _callee(call):
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None


def _door_call(call, name):
    """Is `call` lab_ports.<name>(...)?"""
    f = call.func
    return isinstance(f, ast.Attribute) and f.attr == name and isinstance(f.value, ast.Name) and f.value.id == DOOR


def _port_zero(arg):
    return (isinstance(arg, ast.Tuple) and len(arg.elts) == 2 and isinstance(arg.elts[1], ast.Constant)
            and arg.elts[1].value == 0 and not isinstance(arg.elts[1].value, bool))


_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _own(scope):
    """The nodes of `scope` that are not inside a nested function, lambda or class (each of those is a scope of its own)."""
    out, stack = [], list(ast.iter_child_nodes(scope))
    while stack:
        n = stack.pop()
        out.append(n)
        if not isinstance(n, _SCOPES):
            stack.extend(ast.iter_child_nodes(n))
    return out


def _scopes(tree):
    return [tree] + [n for n in ast.walk(tree) if isinstance(n, _SCOPES)]


def _scope_name(scope):
    return getattr(scope, "name", None) or ("<lambda>" if isinstance(scope, ast.Lambda) else "<module>")


def _draws(scope):
    """(line, receiver) of every draw and release in `scope` (rule D)."""
    own = _own(scope)
    calls = [n for n in own if isinstance(n, ast.Call)]
    method = {}
    for c in calls:
        if isinstance(c.func, ast.Attribute):
            method.setdefault((_text(c.func.value), c.func.attr), []).append(c)
    withs = {_text(i.optional_vars) for n in own if isinstance(n, (ast.With, ast.AsyncWith)) for i in n.items
             if i.optional_vars is not None}
    out = []
    for c in calls:
        if not (isinstance(c.func, ast.Attribute) and c.func.attr == "bind" and c.args and _port_zero(c.args[0])):
            continue
        recv = _text(c.func.value)
        if recv is None or not method.get((recv, "getsockname")) or method.get((recv, "listen")):
            continue
        released = bool(method.get((recv, "close"))) or recv in withs
        if not released and "." not in recv and not isinstance(scope, (ast.Module, ast.ClassDef)):
            # a local name that never escapes: every read of it is the receiver of one of its own methods, so the socket
            # is closed when the scope ends
            reads = [n for n in own if isinstance(n, ast.Name) and n.id == recv and isinstance(n.ctx, ast.Load)]
            receivers = {id(a.value) for a in own if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name)}
            released = all(id(r) in receivers for r in reads)
        if released:
            out.append((c.lineno, recv))
    return out


HEALTHZ_PATH = re.compile(r"(?:^|\S)/healthz")   # /healthz as a path or in a URL: at the start, or right after a non-space


def _healthz_calls(tree):
    """(line, callee) of every call, other than an assertion, with an argument holding /healthz as a path or in a URL
    (rule W). A string that mentions it in prose, after a space (a skip's "never served /healthz here"), is not a request
    for it, and an assertion comparing a result keyed by the route (an assertEqual over {"/healthz": 200}) asks nothing."""
    out = []
    for c in ast.walk(tree):
        if not isinstance(c, ast.Call) or (_callee(c) or "").startswith("assert"):
            continue
        args = list(c.args) + [k.value for k in c.keywords]
        if any(isinstance(s, ast.Constant) and isinstance(s.value, str) and HEALTHZ_PATH.search(s.value)
               for a in args for s in ast.walk(a)):
            out.append((c.lineno, _callee(c) or "<call>"))
    return out


def _names_kernel(node, bound):
    """Does the expression `node` name the kernel: a string ending in romp-kernel, or a name or attribute the module binds
    to such an expression?"""
    for s in ast.walk(node):
        if isinstance(s, ast.Constant) and isinstance(s.value, str) and s.value.endswith(KERNEL_NAME):
            return True
        if isinstance(s, (ast.Name, ast.Attribute)) and _text(s) in bound:
            return True
    return False


def _kernel_bound(tree):
    """The spellings the module binds to an expression naming the kernel (KERNEL = os.path.join(BIN, "romp-kernel")),
    followed to a fixed point."""
    assigns = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            assigns += [(t, n.value) for t in n.targets]
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign)) and n.value is not None:
            assigns.append((n.target, n.value))
    bound, grew = set(), True
    while grew:
        grew = False
        for t, v in assigns:
            for tt in (t.elts if isinstance(t, (ast.Tuple, ast.List)) else [t]):
                name = _text(tt)
                if name and name not in bound and _names_kernel(v, bound):
                    bound.add(name)
                    grew = True
    return bound


def _argv(call):
    if call.args:
        return call.args[0]
    return next((k.value for k in call.keywords if k.arg == "args"), None)


def _kernel_spawns(tree):
    """[(line, the enclosing function node or None)] of every kernel Popen in the module."""
    bound = _kernel_bound(tree)
    out = []
    for scope in _scopes(tree):
        fn = scope if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) else None
        for c in _own(scope):
            if isinstance(c, ast.Call) and _callee(c) in SPAWN_CALLEES:
                argv = _argv(c)
                if argv is not None and _names_kernel(argv, bound):
                    out.append((c.lineno, fn))
    return out


def scan(text, tree, name):
    """{rule: [(file, line, what)]}: one module's offences under each rule, and its kernel-spawning functions under the
    key "spawns" (the census's floor reads them)."""
    off = {r: [] for r in RULES}
    for scope in _scopes(tree):
        for line, recv in _draws(scope):
            off["D"].append((name, line, "%s draws a port into %s and releases it" % (_scope_name(scope), recv)))
    for line, callee in _healthz_calls(tree):
        off["W"].append((name, line, "%s(...) asks /healthz by hand" % callee))
    spawns = _kernel_spawns(tree)
    for line, fn in spawns:
        if fn is None:
            off["K"].append((name, line, "a kernel spawn outside any function"))
        elif not any(isinstance(c, ast.Call) and _door_call(c, "wait_owned") for c in _own(fn)):
            off["K"].append((name, line, "%s starts the kernel and never calls lab_ports.wait_owned" % _scope_name(fn)))
    calls = [c for c in ast.walk(tree) if isinstance(c, ast.Call)]
    reserves = any(_door_call(c, "reserve") or _callee(c) == "kernel_env" for c in calls)
    if reserves and not any(_door_call(c, "release") for c in calls):
        off["R"].append((name, 1, "reserves ports (lab_ports.reserve or kernel_env) and never calls lab_ports.release"))
    for line, what in _door_aliases(tree):
        off["A"].append((name, line, what))
    off["spawns"] = [(name, line, _scope_name(fn) if fn else "<module>") for line, fn in spawns]
    return off


def _door_aliases(tree):
    """(line, what) of every binding of the door under a name other than its own, and of every from-import of its
    members (rule A)."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                bound = a.asname or a.name.split(".")[0]
                if a.name.split(".")[-1] == DOOR and bound != DOOR:
                    out.append((n.lineno, "imports %s, bound as %s" % (a.name, bound)))
        elif isinstance(n, ast.ImportFrom):
            source = "." * n.level + (n.module or "")
            if n.module and n.module.split(".")[-1] == DOOR:
                out.append((n.lineno, "from-imports %s from %s" % (", ".join(a.name for a in n.names), source)))
            for a in n.names:
                if a.name == DOOR and a.asname not in (None, DOOR):
                    out.append((n.lineno, "from-imports %s from %s as %s" % (DOOR, source, a.asname)))
        elif isinstance(n, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and n.value is not None:
            values = n.value.elts if isinstance(n.value, (ast.Tuple, ast.List)) else [n.value]
            if any(isinstance(v, ast.Name) and v.id == DOOR for v in values):
                out.append((n.lineno, "assigns the bare name %s to another name" % DOOR))
    return out


def census(root=ROOT, globs=None, files=None):
    """(population names, {rule: offences, "spawns": spawning functions}) over the served population under `root`."""
    names, read = population(root, globs, files)
    total = {r: [] for r in RULES + ("spawns",)}
    for f in names:
        text, tree = read[f]
        for k, v in scan(text, tree, f).items():
            total[k] += v
    return names, total


def _census_here():
    return parse_cache.derived(("lab_ports_census", ROOT), census)


def _lines(offences, cap=40):
    shown = ["  %s:%d %s" % o for o in offences[:cap]]
    if len(offences) > cap:
        shown.append("  ... and %d more" % (len(offences) - cap))
    return "\n".join(shown)


PLANTS = {
    # name: (source, the one rule it breaks, or None for a clean shape)
    "draw-def": ('import socket\ndef _free_port():\n    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; '
                 's.close(); return p\n', "D"),
    "draw-with": ('import socket\ndef pick():\n    with socket.socket() as s:\n        s.bind(("127.0.0.1", 0))\n'
                  '        return s.getsockname()[1]\n', "D"),
    "draw-inline": ('import socket, unittest\nclass L(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n'
                    '        s = socket.socket()\n        s.bind(("", 0))\n        cls.port = s.getsockname()[1]\n'
                    '        s.close()\n', "D"),
    "draw-scope": ('import socket\ndef pick():\n    s = socket.socket()\n    s.bind(("127.0.0.1", 0))\n'
                   '    return s.getsockname()[1]\n', "D"),
    "draw-module": ('import socket\n_s = socket.socket()\n_s.bind(("127.0.0.1", 0))\nPORT = _s.getsockname()[1]\n_s.close()\n', "D"),
    "draw-lambda": ('import socket\npick = lambda s: (s.bind(("127.0.0.1", 0)), s.getsockname()[1], s.close())[1]\n', "D"),
    "wait-urlopen": ('import time, urllib.request\ndef wait(p):\n    for _ in range(9):\n        try:\n'
                     '            urllib.request.urlopen("http://127.0.0.1:%d/healthz" % p, timeout=1)\n            return\n'
                     '        except Exception:\n            time.sleep(0.5)\n', "W"),
    "wait-connection": ('import http.client\ndef wait(p):\n    c = http.client.HTTPConnection("127.0.0.1", p)\n'
                        '    c.request("GET", "/healthz")\n', "W"),
    "wait-fstring": ('import urllib.request\ndef wait(p):\n    urllib.request.urlopen(f"http://127.0.0.1:{p}/healthz")\n', "W"),
    "spawn-unproved": ('import os, subprocess\ndef boot(env):\n    return subprocess.Popen([os.path.join("bin", "romp-' 'kernel")], env=env)\n', "K"),
    "spawn-named": ('import os, subprocess\nKERNEL = os.path.join("bin", "romp-' 'kernel")\ndef boot(env):\n'
                    '    return subprocess.Popen([KERNEL], env=env)\n', "K"),
    "spawn-module": ('import os, subprocess\nP = subprocess.Popen([os.path.join("bin", "romp-' 'kernel")])\n', "K"),
    "reserve-unreleased": ('import lab_ports\ndef boot(lab):\n    return lab_ports.reserve(lab)\n', "R"),
    "kernel-env-unreleased": ('import test_ship_reship_served as _lab\ndef env(lab):\n'
                              '    return _lab.kernel_env(lab, lab, lab, 1, "t")\n', "R"),
    "door-aliased": ('import lab_ports as lp\nx = 1\n', "A"),
    "door-from-imported": ('from lab_ports import wait_owned\nx = 1\n', "A"),
    # the four alias forms below reserve under another spelling and never release, so R alone would pass each
    "door-from-tests-aliased": ('from tests import lab_ports as lp\ndef boot(lab):\n    return lp.reserve(lab)\n', "A"),
    "door-relative-aliased": ('from . import lab_ports as lp\ndef boot(lab):\n    return lp.reserve(lab)\n', "A"),
    "door-assigned": ('import lab_ports\nlp = lab_ports\ndef boot(lab):\n    return lp.reserve(lab)\n', "A"),
    "door-dotted": ('import tests.lab_ports\ndef boot(lab):\n    return tests.lab_ports.reserve(lab)\n', "A"),
    "clean-door-from-tests": ('from tests import lab_ports\ndef boot(lab):\n    p = lab_ports.reserve(lab)\n'
                              '    lab_ports.release(lab)\n    return p\n', None),
    "clean-door-patched": ('import lab_ports\nfrom unittest import mock\ndef t():\n'
                           '    with mock.patch.object(lab_ports, "reserve"):\n        pass\n', None),
    "clean-listener": ('import socket, http.server\ndef srv():\n    s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(8)\n'
                       '    p = s.getsockname()[1]\n    h = http.server.ThreadingHTTPServer(("127.0.0.1", 0), None)\n'
                       '    return s, h, p\n', None),
    "clean-holder": ('import socket\nclass P:\n    def __init__(self):\n        self.h = socket.socket()\n'
                     '        self.h.bind(("127.0.0.1", 0))\n        self.port = self.h.getsockname()[1]\n'
                     '    def stop(self):\n        self.h.close()\n', None),
    "clean-door": ('import lab_ports, os, subprocess\ndef boot(lab, env):\n    env["ROMP_KERNEL_PORT"] = str(lab_ports.reserve(lab))\n'
                   '    p = subprocess.Popen([os.path.join("bin", "romp-' 'kernel")], env=env)\n'
                   '    why = lab_ports.wait_owned(p, env)\n    return p, why\ndef down(lab):\n    lab_ports.release(lab)\n', None),
    "clean-js-healthz": ('DRIVER = r"""const r = await fetch("/healthz");"""\ndef write(p):\n    open(p, "w").write(DRIVER)\n', None),
    "wait-joined": ('import urllib.request\ndef wait(base):\n    urllib.request.urlopen(base + "/healthz", timeout=1)\n', "W"),
    "clean-assert-healthz": ('import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n'
                             '        self.assertEqual({"/healthz": 200}, {"/healthz": 200})\n', None),
    "clean-prose-healthz": ('import unittest\ndef boot(why):\n'
                            '    raise unittest.SkipTest("hermetic kernel never served /healthz here: " + why)\n', None),
}


def _scan_plant(src, name):
    return scan(src, ast.parse(src, name), name)


class LabPortsCensus(unittest.TestCase):
    maxDiff = None

    def test_the_population_is_derived_and_holds_kernel_spawns(self):
        names, total = _census_here()
        self.assertIn("conftest.py", names)
        self.assertNotIn(DOOR_FILE, names, "the door itself is not held to the rules it implements")
        self.assertIn("test_ship_reship_served.py", names, "kernel_env's module, which every lab kernel's environment comes from")
        spawning = sorted({o[0] for o in total["spawns"]})
        self.assertTrue(total["spawns"], "the census found no kernel spawn in %d files: it reads nothing, so it proves nothing"
                        % len(names))
        print("LABPORTS population=%d files, kernel spawns=%d in %d files" % (len(names), len(total["spawns"]), len(spawning)),
              file=sys.stderr)

    def _rule(self, rule, what):
        names, total = _census_here()
        self.assertEqual(total[rule], [], "%d %s in the served population (%d files; tests/lab_ports.py is the door):\n%s"
                         % (len(total[rule]), what, len(names), _lines(total[rule])))

    def test_no_served_module_draws_a_port_and_releases_it(self):
        self._rule("D", "draw-and-release sites (use lab_ports.reserve(lab), released by lab_ports.release(lab) after the "
                        "lab's kernels are reaped)")

    def test_no_served_module_waits_on_healthz_by_hand(self):
        self._rule("W", "calls asking /healthz by hand (use lab_ports.wait_owned(proc, env))")

    def test_every_kernel_spawn_proves_its_port(self):
        self._rule("K", "kernel spawns with no lab_ports.wait_owned in the function that starts them")

    def test_every_module_that_reserves_releases(self):
        self._rule("R", "modules that reserve ports and never release them")

    def test_the_door_is_imported_by_its_own_name(self):
        self._rule("A", "imports of the door under another spelling (use `import lab_ports`)")

    def test_each_planted_module_is_red_under_exactly_its_rule_and_the_clean_shapes_are_green(self):
        got = {}
        for name, (src, rule) in PLANTS.items():
            off = _scan_plant(src, name + ".py")
            got[name] = sorted(r for r in RULES if off[r])
        want = {name: [rule] if rule else [] for name, (_, rule) in PLANTS.items()}
        self.assertEqual(got, want)
        for rule in RULES:
            self.assertIn(rule, {r for _, r in PLANTS.values()}, "a red plant for rule %s" % rule)

    def test_a_new_served_module_is_read_by_glob_and_its_offence_is_named(self):
        root = tempfile.mkdtemp(prefix="labports-census-")
        self.addCleanup(shutil.rmtree, root, True)
        os.makedirs(os.path.join(root, "tests"))
        with open(os.path.join(root, "tests", "test_planted_served.py"), "w") as f:
            f.write(PLANTS["spawn-unproved"][0] + PLANTS["draw-def"][0])
        with open(os.path.join(root, "tests", "test_clean_served.py"), "w") as f:
            f.write(PLANTS["clean-door"][0])
        names, total = census(root, ["tests/test_*_served.py"], [])
        self.assertEqual(names, ["test_clean_served.py", "test_planted_served.py"])
        self.assertEqual([(o[0], o[1]) for o in total["K"]], [("test_planted_served.py", 3)])
        self.assertEqual([(o[0], o[1]) for o in total["D"]], [("test_planted_served.py", 6)])
        self.assertEqual(sorted(o[0] for o in total["spawns"]), ["test_clean_served.py", "test_planted_served.py"])

    def test_a_helper_a_served_module_imports_is_read_whatever_the_import_form(self):
        # a served module that reaches a port-drawing helper under tests/ by any import form brings the helper into the
        # population, so the helper's draw is named under D. Until this test (2026-10-02) `from tests import`, `from .
        # import` and `from .x import` were not followed, and a helper reached only that way was never read
        forms = ["import boothelper\n", "import tests.boothelper\n", "from tests.boothelper import _free_port\n",
                 "from tests import boothelper\n", "from . import boothelper\n", "from .boothelper import _free_port\n",
                 "def f():\n    from tests import os_helper, boothelper\n    return boothelper\n"]
        for form in forms:
            with self.subTest(form=form):
                root = tempfile.mkdtemp(prefix="labports-census-")
                self.addCleanup(shutil.rmtree, root, True)
                os.makedirs(os.path.join(root, "tests"))
                with open(os.path.join(root, "tests", "test_planted_served.py"), "w") as f:
                    f.write(form)
                with open(os.path.join(root, "tests", "boothelper.py"), "w") as f:
                    f.write(PLANTS["draw-def"][0])
                names, total = census(root, ["tests/test_*_served.py"], [])
                self.assertEqual(names, ["boothelper.py", "test_planted_served.py"], "the helper is read")
                self.assertEqual([(o[0], o[1]) for o in total["D"]], [("boothelper.py", 3)], "its draw is named")

    def test_an_empty_population_fails_loudly(self):
        root = tempfile.mkdtemp(prefix="labports-census-")
        self.addCleanup(shutil.rmtree, root, True)
        os.makedirs(os.path.join(root, "tests"))
        with self.assertRaisesRegex(AssertionError, "matches no file"):
            population(root, ["tests/test_*_served.py"], [])
        with self.assertRaisesRegex(AssertionError, "is absent"):
            population(root, [], ["tests/test_named.py"])
        with self.assertRaisesRegex(AssertionError, "names no glob and no file"):
            population(root, [], [])


if __name__ == "__main__":
    if sys.argv[1:2] == ["--table"]:
        names, total = census(sys.argv[2] if len(sys.argv) > 2 else ROOT)
        print("population %d files" % len(names))
        for r in RULES + ("spawns",):
            print("%s %d" % (r, len(total[r])))
            print(_lines(total[r], cap=10))
    else:
        unittest.main()
