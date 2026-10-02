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
nothing. Rules R, A and F also read THE RESERVERS (reservers()): every other module under tests/ whose AST calls
lab_ports.reserve or kernel_env, or binds the door under another name (an alias would hide its reserves), since a unit test that builds a lab kernel's environment holds the postal port as
surely as a served lab does (three modules outside the served step left a postal port held for each kernel_env call
until the process exited, 2026-10-02).

THE RULES, each read per module by AST (scan()):
  D  no draw and release: in one scope (a function, a lambda, a class body or the module body), a socket bound to port 0
     (an address written in place, or a name the module binds to one: ADDR = ("127.0.0.1", 0); s.bind(ADDR)) whose port
     is read (getsockname) and that is released in the same scope, by close(), by a with block (one that binds it or is
     entered on it), or by going out of scope (a local name used only for its own methods). A listener is read the same
     way, released by close(), server_close() or a with block only: a socket that listens, a socket.create_server or
     asyncio loop.create_server listener built on port 0, or a server of http.server or socketserver (SERVER_CLASSES:
     HTTPServer, ThreadingHTTPServer, TCPServer and the rest, or a class the module derives from one) built on a port-0
     address, its port read by getsockname, socket.getsockname, server_address, server_port or sockets. A listener left
     open at the scope's end keeps its port (a thread serving from it can hold it past the scope), and so does a holder
     kept on an attribute and closed by another method. By this reading a server built, served and closed within one
     function is a draw, so a test that needs one hands its close to a cleanup (self.addCleanup(srv.server_close)).
  W  no hand-written /healthz wait: no call other than an assert* has an argument holding /healthz as a path or in a
     URL (at a string's start or right after a non-space: "http://127.0.0.1:%d/healthz", base + "/healthz", an
     f-string's "{p}/healthz"), written in place or through a name bound to such a string in the call's own scope or
     the module's (url = "http://127.0.0.1:%d/healthz" % p; urlopen(url); or HZ at module level and urlopen(HZ % p)).
     Prose that mentions it after a space (a skip's "never served /healthz here") is not a request, an assertion over
     results keyed by the route asks nothing, a node driver's /healthz inside a JavaScript text that Python writes to a
     file or hands to the driver is not a URL, and a cfg dict holding a /healthz URL for the node driver ({"healthz":
     url}, handed to json.dumps) is the driver's to read, not a Python request.
  K  every function that starts the kernel (a Popen whose argv names romp-kernel, directly or through a name the module
     binds to an expression naming it; Popen spelled by its own name or by a name an import or an assignment binds it
     to: from subprocess import Popen as P, or P = subprocess.Popen) calls lab_ports.wait_owned; a spawn outside any
     function is an offence too.
  R  a module that reserves a port, through lab_ports.reserve or through kernel_env (which reserves the kernel's postal
     port), reads lab_ports.release (a call of it, or a call it is handed to as an argument, as addCleanup is; a read
     that is neither, rel = lab_ports.release, is no release); and so does every class that reserves in its own body, by
     a reserve written there or by a bare-name call of a function the module defines at its top level that reserves
     (directly or through another such function), reading the release there or in a base class the module defines, so a
     class of stand-in tests that builds environments in a module whose served lab releases its own is still held to
     releasing them. A release inherited from a class another module defines is not read: such a class releases in its
     own body.
  F  every class that reserves in its setUpClass (a reserve written there, a bare-name call of a function the module
     defines that reserves, or a call through cls of a method the class defines that reserves, followed through such
     methods: cls._boot()) releases on that setUpClass's failure path, where tearDownClass is never run. Each reserving
     call is covered by cls.addClassCleanup(lab_ports.release, ...) as a statement of setUpClass's own body before the
     one that holds the call (right after the lab is made), or by a try whose body holds it and whose every handler calls
     cls.tearDownClass(), one of them catching broadly (bare, BaseException or Exception), in a class whose
     tearDownClass (its own, or the first a base the module defines has) reads lab_ports.release. unittest and pytest
     both run the class cleanups when setUpClass raises an Exception, SkipTest included.
  A  the door is bound under its own name only and its members are read as lab_ports.<name>: no `import lab_ports as x`,
     no `import tests.lab_ports` (it binds tests), no `from tests import lab_ports as x` or `from . import lab_ports as
     x`, no from-import of its members (`from lab_ports import wait_owned`, `from .lab_ports import reserve`), no
     from-import from the package (`from tests import`, `from . import`) of a name tests/__init__.py binds the door to
     (_lab_ports today, read from that file), no read of the door or of such a name as an attribute (`tests.lab_ports`,
     `tests._lab_ports`), no assignment of the bare name lab_ports (`lp = lab_ports`), and no assignment of a member the
     rules read, lab_ports.reserve or lab_ports.wait_owned, alone or as an element of a tuple or list value (`r =
     lab_ports.reserve`). Each would hide the calls the rules above read. `import lab_ports`, `from tests import
     lab_ports` and `from . import lab_ports` all bind the name lab_ports. lab_ports.release bound to another name is
     not refused: it hides a release, not a reserve, and R reads the module as never releasing.
D, K and W read a name as bound by any assignment to it (plain, annotated, augmented or walrus). A tuple or list target
is read element by element against a tuple or list value of its length with nothing starred on either side, so that
ADDR, N = ("127.0.0.1", 0), 1 binds ADDR to the address; any other tuple or list target binds each of its elements to
the whole value.
At run time wait_owned itself refuses a port that was not reserved in the process, which covers a port drawn by a road
the AST does not read.

WHAT IT CANNOT SEE (stated, not closed): a draw split across functions, or reached through getattr or partial; a port
picked without a bind; Python inside a subprocess -c string; a JavaScript wait on a kernel the node driver relaunches in
place (tests/test_ship_reship_served.py and tests/test_dashboard_reload_served.py relaunch from the driver and wait
there), or a node driver's own wait on a /healthz URL its cfg carries; a kernel started by a shell or by a name bound
outside the module; a module imported by a computed name; readiness read by another road than an HTTP call naming
/healthz; a /healthz URL bound in an enclosing function or a class body (W reads the call's own scope and the module's;
D and K read every assignment in the module by spelling); an address, a URL or Popen that reaches its use through a
container, a call's result or a parameter; the door handed to a call as an argument (getattr(lab_ports, name); the
mock.patch.object(lab_ports, ...) in tests/test_federated_linkdrop_served.py is such a hand-off and is green), bound by
a for, a with or a default argument, bound through an expression that holds it (lp = lab_ports if c else None, lp =
lab_ports or None, a lambda returning it), or reached through sys.modules, importlib.import_module or __import__; a port
0 spelled by a name (s.bind(("127.0.0.1", ZERO))); a kernel started by asyncio.create_subprocess_exec; a URL bound to a
name with /healthz as the right operand of % (url = "http://127.0.0.1:%d%s" % (p, "/healthz")); a port reserved through
a function another module defines, other than kernel_env, or through a function of the module called by any spelling but
its bare name; a listener built by a server class another module derives or by a constructor outside SERVER_CLASSES, or
one whose port is read through a call's result or a container; a reserve in setUp or setUpModule (F reads setUpClass
only); a class cleanup handed an owner other than the one reserved (no rule compares owners); a tearDownClass that
releases only through another method it calls (F reads it as no release, the safe side). The planted modules below are
each red under exactly the rule they break, and the clean shapes (a listener that outlives its scope, a kept holder, a
server whose close is handed to a cleanup, the door's own use, a /healthz inside a JavaScript text, a driver's cfg holding
a /healthz URL, each form F accepts) are green.

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
RULES = ("D", "W", "K", "R", "A", "F")
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


def _pairs(target, value):
    """(target, value) pairs for one assignment target: a tuple or list target against a tuple or list value of the same
    length with no starred element on either side is paired element by element (ADDR, N = ("127.0.0.1", 0), 1 binds
    ADDR to the address), each pair read the same way in turn; any other tuple or list target pairs each of its elements
    with the whole value; a single target pairs with the value."""
    if not isinstance(target, (ast.Tuple, ast.List)):
        return [(target, value)]
    if (isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(target.elts)
            and not any(isinstance(e, ast.Starred) for e in target.elts + value.elts)):
        return [p for t, v in zip(target.elts, value.elts) for p in _pairs(t, v)]
    return [p for t in target.elts for p in _pairs(t, value)]


def _assigns(nodes):
    """(target, value) of every assignment among `nodes` (plain, annotated, augmented or walrus), a tuple or list target
    taken element by element (_pairs)."""
    out = []
    for n in nodes:
        if isinstance(n, ast.Assign):
            pairs = [(t, n.value) for t in n.targets]
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)) and n.value is not None:
            pairs = [(n.target, n.value)]
        else:
            continue
        for t, v in pairs:
            out += _pairs(t, v)
    return out


def _bound(assigns, holds, seed=()):
    """The spellings (a name, or an attribute chain like self.addr) that `assigns` bind to a value `holds(value, bound)`
    accepts, followed to a fixed point from `seed`, so a spelling bound to another bound spelling is bound too."""
    bound, grew = set(seed), True
    while grew:
        grew = False
        for t, v in assigns:
            name = _text(t)
            if name and name not in bound and holds(v, bound):
                bound.add(name)
                grew = True
    return bound


def _holds_port_zero(node, bound):
    """Is `node` an address with port 0, ("127.0.0.1", 0), or a spelling bound to one?"""
    return _port_zero(node) or _text(node) in bound


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


SERVER_CLASSES = frozenset({   # the stdlib's server classes that bind and listen on the address they are built with
    "HTTPServer", "ThreadingHTTPServer",                                                  # http.server
    "TCPServer", "UDPServer", "ThreadingTCPServer", "ThreadingUDPServer", "ForkingTCPServer", "ForkingUDPServer",   # socketserver
})


def _server_classes(tree):
    """SERVER_CLASSES and every class the module defines with one of them as a base (by the base's last part), followed to
    a fixed point (class _Quiet(ThreadingHTTPServer), and a class built on _Quiet)."""
    names, classes, grew = set(SERVER_CLASSES), [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)], True
    while grew:
        grew = False
        for c in classes:
            if c.name not in names and any(_last(b) in names for b in c.bases):
                names.add(c.name)
                grew = True
    return names


def _arg(call, i, key):
    """The call's argument at position `i`, else its keyword `key`, else None."""
    if len(call.args) > i:
        return call.args[i]
    return next((k.value for k in call.keywords if k.arg == key), None)


def _builds_listener(value, zero, servers):
    """Is `value` (an await of one included) a listener built on port 0: socket.create_server(addr) with addr an address
    with port 0 (or a spelling the module binds to one), a server class built on such an address (servers:
    _server_classes), or asyncio's loop.create_server(factory, host, 0) (the port as its third argument or port=0)?"""
    if isinstance(value, ast.Await):
        value = value.value
    if not isinstance(value, ast.Call):
        return False
    name = _callee(value)
    if name == "create_server":
        port = _arg(value, 2, "port")
        return (_holds_port_zero(_arg(value, 0, "address"), zero)
                or (isinstance(port, ast.Constant) and port.value == 0 and not isinstance(port.value, bool)))
    return name in servers and _holds_port_zero(_arg(value, 0, "server_address"), zero)


def _reads_port(recv, method, attrs):
    """Does the scope read the port of the socket or server spelled `recv`: recv.getsockname(), recv.socket.getsockname(),
    or recv.server_address, recv.server_port or recv.sockets (asyncio's server) read?"""
    return (bool(method.get((recv, "getsockname")) or method.get((recv + ".socket", "getsockname")))
            or any(recv + "." + a in attrs for a in ("server_address", "server_port", "sockets")))


def _draws(scope, zero=frozenset(), servers=SERVER_CLASSES):
    """(line, receiver) of every draw and release in `scope` (rule D). `zero` holds the spellings the module binds to an
    address with port 0 (ADDR = ("127.0.0.1", 0); s.bind(ADDR) is a bind to port 0 too), and `servers` the server
    classes a listener is built from (_server_classes)."""
    own = _own(scope)
    calls = [n for n in own if isinstance(n, ast.Call)]
    method = {}
    for c in calls:
        if isinstance(c.func, ast.Attribute):
            method.setdefault((_text(c.func.value), c.func.attr), []).append(c)
    attrs = {_text(n) for n in own if isinstance(n, ast.Attribute)}
    # a with block releases what it binds (with socket.socket() as s) and what it is entered on (async with srv)
    withs = {_text(e) for n in own if isinstance(n, (ast.With, ast.AsyncWith)) for i in n.items
             for e in (i.optional_vars, i.context_expr) if e is not None} - {None}
    binds = []   # (line, receiver, listens)
    for c in calls:
        if isinstance(c.func, ast.Attribute) and c.func.attr == "bind" and c.args and _holds_port_zero(c.args[0], zero):
            recv = _text(c.func.value)
            if recv is not None:
                binds.append((c.lineno, recv, bool(method.get((recv, "listen")))))
    built = [(t, v) for t, v in _assigns(own)] + [(i.optional_vars, i.context_expr) for n in own
                                                  if isinstance(n, (ast.With, ast.AsyncWith)) for i in n.items
                                                  if i.optional_vars is not None]
    for t, v in built:
        if _text(t) is not None and _builds_listener(v, zero, servers):
            binds.append((v.lineno, _text(t), True))
    out = []
    for line, recv, listens in binds:
        if not _reads_port(recv, method, attrs):
            continue
        released = bool(method.get((recv, "close")) or method.get((recv, "server_close"))) or recv in withs
        if listens:
            # a listener is released only by a close, a server_close or a with block in this scope: one left open at the
            # scope's end may be serving from a thread that holds it
            if released:
                out.append((line, recv))
            continue
        if not released and "." not in recv and not isinstance(scope, (ast.Module, ast.ClassDef)):
            # a local name that never escapes: every read of it is the receiver of one of its own methods, so the socket
            # is closed when the scope ends
            reads = [n for n in own if isinstance(n, ast.Name) and n.id == recv and isinstance(n.ctx, ast.Load)]
            receivers = {id(a.value) for a in own if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name)}
            released = all(id(r) in receivers for r in reads)
        if released:
            out.append((line, recv))
    return out


HEALTHZ_PATH = re.compile(r"(?:^|\S)/healthz")   # /healthz as a path or in a URL: at the start, or right after a non-space
HEALTHZ_URL = re.compile(r"^\S*/healthz")         # a string that IS a URL or path to /healthz: no space before the route


def _holds_url(node, bound):
    """Is the expression `node` a string that is a /healthz URL or path: a literal matching HEALTHZ_URL (so a JavaScript
    text with /healthz deep inside it is not), an f-string with a literal part that does, a + or a % of one, a .format()
    of one, or a spelling bound to one? A dict, list or call that holds such a string is not one: a driver's cfg
    {"healthz": url} is for the node driver to read, and the call handed the cfg asks nothing."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and bool(HEALTHZ_URL.search(node.value))
    if isinstance(node, ast.JoinedStr):
        return any(_holds_url(v, bound) for v in node.values if isinstance(v, ast.Constant))
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return _holds_url(node.left, bound) or (isinstance(node.op, ast.Add) and _holds_url(node.right, bound))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return _holds_url(node.func.value, bound)
    return isinstance(node, (ast.Name, ast.Attribute)) and _text(node) in bound


def _healthz_calls(tree):
    """(line, callee) of every call, other than an assertion, with an argument holding /healthz as a path or in a URL
    (rule W), written in place or through a spelling bound to such a URL in the call's own scope or the module's
    (url = "http://127.0.0.1:%d/healthz" % p; urlopen(url)). A string that mentions it in prose, after a space (a
    skip's "never served /healthz here"), is not a request for it, and an assertion comparing a result keyed by the route
    (an assertEqual over {"/healthz": 200}) asks nothing."""
    module = _bound(_assigns(_own(tree)), _holds_url)
    out = []
    for scope in _scopes(tree):
        own = _own(scope)
        bound = module if scope is tree else _bound(_assigns(own), _holds_url, module)
        for c in own:
            if not isinstance(c, ast.Call) or (_callee(c) or "").startswith("assert"):
                continue
            args = list(c.args) + [k.value for k in c.keywords]
            if any(isinstance(s, ast.Constant) and isinstance(s.value, str) and HEALTHZ_PATH.search(s.value)
                   for a in args for s in ast.walk(a)) or any(_holds_url(a, bound) for a in args if bound):
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
    return _bound(_assigns(ast.walk(tree)), _names_kernel)


def _last(node):
    """The last part of a name or an attribute chain (P, self.P: P), as _callee reads a call's callee; else None."""
    return node.attr if isinstance(node, ast.Attribute) else node.id if isinstance(node, ast.Name) else None


def _spawn_names(tree):
    """The names a Popen call is spelled by in the module, read as a callee's last part: Popen, each name an import binds
    it to (from subprocess import Popen as P), and each spelling assigned one of those (P = subprocess.Popen), followed to
    a fixed point."""
    names = set(SPAWN_CALLEES)
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            names |= {a.asname for a in n.names if a.name in SPAWN_CALLEES and a.asname}
    assigns, grew = _assigns(ast.walk(tree)), True
    while grew:
        grew = False
        for t, v in assigns:
            if _last(v) in names and _last(t) and _last(t) not in names:
                names.add(_last(t))
                grew = True
    return names


def _argv(call):
    if call.args:
        return call.args[0]
    return next((k.value for k in call.keywords if k.arg == "args"), None)


def _kernel_spawns(tree):
    """[(line, the enclosing function node or None)] of every kernel Popen in the module."""
    bound, spawn = _kernel_bound(tree), _spawn_names(tree)
    out = []
    for scope in _scopes(tree):
        fn = scope if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) else None
        for c in _own(scope):
            if isinstance(c, ast.Call) and _callee(c) in spawn:
                argv = _argv(c)
                if argv is not None and _names_kernel(argv, bound):
                    out.append((c.lineno, fn))
    return out


def scan(text, tree, name, package=None):
    """{rule: [(file, line, what)]}: one module's offences under each rule, and its kernel-spawning functions under the
    key "spawns" (the census's floor reads them). `package` holds the names the package binds the door to
    (_package_door_names); None reads them from this checkout's tests/__init__.py."""
    off = {r: [] for r in RULES}
    zero, servers = _bound(_assigns(ast.walk(tree)), _holds_port_zero), _server_classes(tree)
    for scope in _scopes(tree):
        for line, recv in _draws(scope, zero, servers):
            off["D"].append((name, line, "%s draws a port into %s and releases it" % (_scope_name(scope), recv)))
    for line, callee in _healthz_calls(tree):
        off["W"].append((name, line, "%s(...) asks /healthz by hand" % callee))
    spawns = _kernel_spawns(tree)
    for line, fn in spawns:
        if fn is None:
            off["K"].append((name, line, "a kernel spawn outside any function"))
        elif not any(isinstance(c, ast.Call) and _door_call(c, "wait_owned") for c in _own(fn)):
            off["K"].append((name, line, "%s starts the kernel and never calls lab_ports.wait_owned" % _scope_name(fn)))
    off.update(scan_reserves(tree, name, package))
    off["spawns"] = [(name, line, _scope_name(fn) if fn else "<module>") for line, fn in spawns]
    return off


def scan_reserves(tree, name, package=None):
    """{"R": [...], "A": [...], "F": [...]}: one module's offences under rules R, A and F, the three rules the census also
    reads in the modules outside the served population that reserve a port (reservers())."""
    off = {"R": [], "A": [], "F": []}
    if _reserves(tree) and not _reads_release(tree):
        off["R"].append((name, 1, "reserves ports (lab_ports.reserve or kernel_env) and never releases them through "
                                  "lab_ports.release"))
    for line, cls in _unreleased_classes(tree):
        off["R"].append((name, line, "class %s reserves ports (lab_ports.reserve, kernel_env, or a function this module "
                                     "defines that reserves) and neither it nor a base class this module defines reads "
                                     "lab_ports.release" % cls))
    for line, what in _door_aliases(tree, package):
        off["A"].append((name, line, what))
    for line, cls, at in _setup_unguarded(tree):
        off["F"].append((name, line, "class %s reserves a port in setUpClass (line %d) with no release on its failure path "
                                     "(cls.addClassCleanup(lab_ports.release, cls.lab) right after the lab is made, or a "
                                     "try whose handlers call cls.tearDownClass())" % (cls, at)))
    return off


def _reserves(node):
    """The calls under `node` that reserve a port: lab_ports.reserve(...), or kernel_env(...) by any receiver (it reserves
    the kernel's postal port under the lab it is given)."""
    return [c for c in ast.walk(node) if isinstance(c, ast.Call) and (_door_call(c, "reserve") or _callee(c) == "kernel_env")]


def _is_release(node):
    """Is `node` the spelling lab_ports.release?"""
    return (isinstance(node, ast.Attribute) and node.attr == "release" and isinstance(node.value, ast.Name)
            and node.value.id == DOOR)


def _reads_release(node):
    """Does `node` release through lab_ports.release: a call of it (lab_ports.release(lab)), or a call it is handed to as
    an argument (self.addCleanup(lab_ports.release, lab), addClassCleanup, atexit.register)? A read that is neither, rel
    = lab_ports.release with no call, releases nothing, and so does a call of the name it was bound to (the safe side:
    R reads that module as never releasing)."""
    return any(isinstance(c, ast.Call) and (_is_release(c.func) or any(_is_release(a) for a in c.args)
                                            or any(_is_release(k.value) for k in c.keywords))
               for c in ast.walk(node))


def _reserving_functions(tree):
    """The names of the functions the module defines at its top level that reserve a port: a def whose body reserves
    (_reserves), or calls by its bare name another such function, followed to a fixed point (def env(lab): return
    _lab.kernel_env(...), and a def that calls env(lab))."""
    defs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    out, grew = {d.name for d in defs if _reserves(d)}, True
    while grew:
        grew = False
        for d in defs:
            if d.name not in out and _calls_by_name(d, out):
                out.add(d.name)
                grew = True
    return out


def _calls_by_name(node, names):
    """The calls under `node` of a bare name in `names` (env(lab), never self.env(lab))."""
    return [c for c in ast.walk(node) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id in names]


def _unreleased_classes(tree):
    """(line, name) of every class that reserves a port in its own body (a reserve, or a call by its bare name of a
    function the module defines that reserves, _reserving_functions) and reads lab_ports.release neither there nor in a
    base class this module defines, followed through the bases to a fixed point (rule R per class)."""
    helpers = _reserving_functions(tree)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    releasing, grew = {c.name for c in classes if _reads_release(c)}, True
    while grew:
        grew = False
        for c in classes:
            if c.name not in releasing and any(_last(b) in releasing for b in c.bases):
                releasing.add(c.name)
                grew = True
    return [(c.lineno, c.name) for c in classes
            if c.name not in releasing and (_reserves(c) or _calls_by_name(c, helpers))]


BROAD_CATCHES = ("BaseException", "Exception")   # a handler for either (or a bare except) catches a failed setUpClass


def _first_param(fn):
    return fn.args.args[0].arg if fn.args.args else None


def _self_calls(fn, names):
    """The calls in `fn` of a method in `names` through its first parameter (cls._boot(), self._kernel())."""
    p = _first_param(fn)
    return [c for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
            and isinstance(c.func.value, ast.Name) and c.func.value.id == p and c.func.attr in names]


def _catches_broadly(handler):
    """Does the except clause catch a failed setUpClass whatever it raised: bare, BaseException or Exception, alone or in a
    tuple?"""
    if handler.type is None:
        return True
    types = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(_last(t) in BROAD_CATCHES for t in types)


def _calls_teardown(node, param):
    return any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "tearDownClass"
               and isinstance(c.func.value, ast.Name) and c.func.value.id == param for c in ast.walk(node))


def _teardown_releases(cls, classes):
    """Does the tearDownClass `cls` runs read lab_ports.release: its own, else the first one a base the module defines
    has (depth first, through the bases' last parts)? None defined in the module: no."""
    seen, todo = set(), [cls]
    while todo:
        c = todo.pop(0)
        if c.name in seen:
            continue
        seen.add(c.name)
        td = next((n for n in c.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "tearDownClass"),
                  None)
        if td is not None:
            return _reads_release(td)
        todo[:0] = [classes[_last(b)] for b in c.bases if _last(b) in classes]
    return False


def _setup_unguarded(tree):
    """(line, class, line of the reserve) of every class whose setUpClass reserves a port that a failure of setUpClass would
    leave held (rule F). A class reserves in its setUpClass by a reserve written there (_reserves), a bare-name call of a
    function the module defines that reserves (_reserving_functions), or a call through setUpClass's first parameter of a
    method the class defines that reserves in one of those ways, followed through such methods (cls._boot()). Each such
    call is covered by either of two forms: a statement of setUpClass's own body before the one holding the call that
    hands lab_ports.release to cls.addClassCleanup (cls.addClassCleanup(lab_ports.release, cls.lab), right after the lab
    is made), or a try in setUpClass whose body holds the call and whose every handler calls cls.tearDownClass(), one of
    them catching broadly (_catches_broadly), in a class whose tearDownClass reads lab_ports.release
    (_teardown_releases). The tearDownClass of a class is not run when its setUpClass raises, and the class cleanups are
    (unittest and pytest both run them on an Exception, SkipTest included)."""
    helpers = _reserving_functions(tree)
    classes = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    out = []
    for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        meths = {n.name: n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        setup = meths.get("setUpClass")
        if setup is None:
            continue
        reserving, grew = {m for m, fn in meths.items() if _reserves(fn) or _calls_by_name(fn, helpers)}, True
        while grew:
            grew = False
            for m, fn in meths.items():
                if m not in reserving and _self_calls(fn, reserving):
                    reserving.add(m)
                    grew = True
        param = _first_param(setup)
        calls = {id(c): c for c in _reserves(setup) + _calls_by_name(setup, helpers) + _self_calls(setup, reserving)}
        if not calls:
            continue
        covered = set()
        for i, stmt in enumerate(setup.body):
            v = stmt.value if isinstance(stmt, ast.Expr) else None
            if (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "addClassCleanup"
                    and isinstance(v.func.value, ast.Name) and v.func.value.id == param and v.args
                    and _is_release(v.args[0])):
                covered |= {id(c) for later in setup.body[i + 1:] for c in ast.walk(later)}
                break
        guards = _teardown_releases(cls, classes)
        for t in ast.walk(setup) if guards else ():
            if (isinstance(t, (ast.Try, getattr(ast, "TryStar", ast.Try))) and t.handlers
                    and all(_calls_teardown(h, param) for h in t.handlers) and any(_catches_broadly(h) for h in t.handlers)):
                covered |= {id(c) for s in t.body for c in ast.walk(s)}
        bare = sorted(c.lineno for k, c in calls.items() if k not in covered)
        if bare:
            out.append((cls.lineno, cls.name, bare[0]))
    return out


def _package_door_names(root=ROOT):
    """The names tests/__init__.py under `root` binds the door to other than its own: today _lab_ports, which it binds
    (`from . import lab_ports as _lab_ports`) to register the door under its bare name. A module that from-imports one of
    them from the package, or reads one as the package's attribute, holds the door under that name. Read from the
    package's own imports of the door (`from . import lab_ports as x`, `from tests import lab_ports as x`, `import
    tests.lab_ports as x`) and its assignments of a name so bound (`y = x`), followed to a fixed point, so a renamed alias
    is still refused. No tests/__init__.py under `root`, no names."""
    path = os.path.join(root, "tests", "__init__.py")
    if not os.path.isfile(path):
        return frozenset()
    _, tree = parse_cache.source_and_tree(path)
    seed = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and ((n.level == 1 and not n.module) or (not n.level and n.module == "tests")):
            seed |= {a.asname for a in n.names if a.name == DOOR and a.asname}
        elif isinstance(n, ast.Import):
            seed |= {a.asname for a in n.names if a.name in ("tests." + DOOR, DOOR) and a.asname}
    bound = _bound(_assigns(ast.walk(tree)), lambda v, b: isinstance(v, ast.Name) and v.id in b, seed | {DOOR})
    return frozenset(bound - {DOOR})


DOOR_MEMBERS_READ = ("reserve", "wait_owned")   # the members rules R and K read by their spelling, lab_ports.<name>(...)


def _door_aliases(tree, package=None):
    """(line, what) of every binding of the door under a name other than its own, of every from-import of its members,
    of every from-import from the package of a name `package` holds (the names tests/__init__.py binds the door to,
    _package_door_names()), of every read of the door, or of one of those names, as an attribute (tests.lab_ports), and
    of every assignment of a member the rules read (r = lab_ports.reserve) (rule A)."""
    package = _package_door_names() if package is None else package
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and (n.attr == DOOR or n.attr in package):
            out.append((n.lineno, "reads the door as an attribute, %s" % ast.unparse(n)))
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
                if a.name in package and ((n.level == 1 and not n.module) or (not n.level and n.module == "tests")):
                    out.append((n.lineno, "from-imports %s, the package's name for the door, from %s" % (a.name, source)))
        elif isinstance(n, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and n.value is not None:
            values = n.value.elts if isinstance(n.value, (ast.Tuple, ast.List)) else [n.value]
            if any(isinstance(v, ast.Name) and v.id == DOOR for v in values):
                out.append((n.lineno, "assigns the bare name %s to another name" % DOOR))
            for v in values:
                if (isinstance(v, ast.Attribute) and v.attr in DOOR_MEMBERS_READ and isinstance(v.value, ast.Name)
                        and v.value.id == DOOR):
                    out.append((n.lineno, "assigns %s.%s to another name" % (DOOR, v.attr)))
    return out


def reservers(root=ROOT, served=()):
    """{name: (text, tree)} of every module under root/tests outside `served`, other than the door, that reserves a port
    (lab_ports.reserve or kernel_env) or binds the door under another name (rule A's offence, which would hide its
    reserves from R), read by AST in the files whose text names kernel_env, lab_ports or a name the package binds the
    door to (_package_door_names). Rules R, A and F read them too: a unit test that builds a lab kernel's environment
    holds a port as surely as a served lab does. tests/__init__.py is not read: it binds the door as _lab_ports only to
    register it under its bare name, and reserves nothing."""
    tests = os.path.join(root, "tests")
    package = _package_door_names(root)
    words = ("kernel_env", DOOR) + tuple(sorted(package))
    out = {}
    for f in sorted(os.listdir(tests)):
        if not f.endswith(".py") or f in served or f in (DOOR_FILE, "__init__.py"):
            continue
        path = os.path.join(tests, f)
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        if not any(w in raw for w in words):
            continue
        text, tree = parse_cache.source_and_tree(path)
        if _reserves(tree) or _door_aliases(tree, package):
            out[f] = (text, tree)
    return out


def census(root=ROOT, globs=None, files=None):
    """(population names, {rule: offences, "spawns": spawning functions, "reservers": the modules outside the population
    that reserve, read under R, A and F}) over the served population under `root`."""
    names, read = population(root, globs, files)
    package = _package_door_names(root)
    total = {r: [] for r in RULES + ("spawns",)}
    for f in names:
        text, tree = read[f]
        for k, v in scan(text, tree, f, package).items():
            total[k] += v
    extra = reservers(root, set(read) | {DOOR_FILE})
    for f in sorted(extra):
        for k, v in scan_reserves(extra[f][1], f, package).items():
            total[k] += v
    total["reservers"] = sorted(extra)
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
    # roads to the door those four leave open, each reserving or proving through a spelling the other rules do not read:
    # the name tests/__init__.py binds the door to, from-imported from the package (read from that file, so a renamed
    # alias is still refused); the door, or that name, read as the package's attribute; and a member the rules read
    # bound to another name, alone or as an element of a tuple
    "door-package-alias": ('from tests import _lab_ports\ndef boot(lab):\n    return _lab_ports.reserve(lab)\n', "A"),
    "door-package-alias-relative": ('from . import _lab_ports\ndef boot(lab):\n    return _lab_ports.reserve(lab)\n', "A"),
    "door-package-attribute": ('import tests\ndef boot(lab):\n    return tests.lab_ports.reserve(lab)\n', "A"),
    "door-package-attribute-assigned": ('import tests\nlp = tests.lab_ports\ndef boot(lab):\n    return lp.reserve(lab)\n', "A"),
    "door-package-alias-attribute": ('import tests\ndef boot(lab):\n    return tests._lab_ports.reserve(lab)\n', "A"),
    "door-member-assigned": ('import lab_ports\nr = lab_ports.reserve\ndef boot(lab):\n    return r(lab)\n', "A"),
    "door-member-in-tuple": ('import lab_ports\nw, n = lab_ports.wait_owned, 1\ndef ready(proc, env):\n    return w(proc, env)\n', "A"),
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
    # the address, the URL and Popen reached through a name the module binds (each passed the rules' literal reads)
    "draw-named-address": ('import socket\nADDR = ("127.0.0.1", 0)\ndef pick():\n    s = socket.socket()\n'
                           '    s.bind(ADDR)\n    p = s.getsockname()[1]\n    s.close()\n    return p\n', "D"),
    "spawn-aliased-popen": ('import os\nfrom subprocess import Popen as P\ndef boot(env):\n'
                            '    return P([os.path.join("bin", "romp-' 'kernel")], env=env)\n', "K"),
    "spawn-assigned-popen": ('import os, subprocess\nrun = subprocess.Popen\ndef boot(env):\n'
                             '    return run([os.path.join("bin", "romp-' 'kernel")], env=env)\n', "K"),
    "wait-url-variable": ('import time, urllib.request\ndef wait(p):\n    url = "http://127.0.0.1:%d/healthz" % p\n'
                          '    for _ in range(9):\n        try:\n            urllib.request.urlopen(url, timeout=1)\n'
                          '            return\n        except Exception:\n            time.sleep(0.5)\n', "W"),
    "wait-url-constant": ('import urllib.request\nHZ = "http://127.0.0.1:%d/healthz"\ndef wait(p):\n'
                          '    urllib.request.urlopen(HZ % p, timeout=1)\n', "W"),
    "clean-driver-cfg": ('import json\ndef cfg(p, path):\n    c = {"healthz": "http://127.0.0.1:%d/healthz" % p}\n'
                         '    open(path, "w").write(json.dumps(c))\n    return c\n', None),
    # the same three reached through one element of a tuple assignment, which binds each target to its own element
    "draw-tuple-unpacked-address": ('import socket\nADDR, N = ("127.0.0.1", 0), 1\ndef pick():\n    s = socket.socket()\n'
                                    '    s.bind(ADDR)\n    p = s.getsockname()[1]\n    s.close()\n    return p\n', "D"),
    "spawn-tuple-unpacked-popen": ('import os, subprocess\nrun, x = subprocess.Popen, 1\ndef boot(env):\n'
                                   '    return run([os.path.join("bin", "romp-' 'kernel")], env=env)\n', "K"),
    "wait-tuple-unpacked-url": ('import urllib.request\ndef wait(p):\n    url, n = "http://127.0.0.1:%d/healthz" % p, 9\n'
                                '    urllib.request.urlopen(url, timeout=1)\n', "W"),
    # R per class: the module releases (class A), and class B reserves and never does
    "reserve-class-unreleased": ('import lab_ports\nclass A:\n    def up(self, lab):\n        self.p = lab_ports.reserve(lab)\n'
                                 '    def down(self, lab):\n        lab_ports.release(lab)\nclass B:\n'
                                 '    def up(self, lab):\n        self.p = lab_ports.reserve(lab)\n', "R"),
    "clean-class-cleanup": ('import lab_ports, unittest\nimport test_ship_reship_served as _lab\n'
                            'class T(unittest.TestCase):\n    def test_env(self):\n'
                            '        self.addCleanup(lab_ports.release, "/lab")\n'
                            '        _lab.kernel_env("/lab", "/lab/c", "/lab/d", 1, "t")\n', None),
    "clean-class-inherits": ('import lab_ports, unittest\nclass Base(unittest.TestCase):\n    def setUp(self):\n'
                             '        self.lab = "/lab"\n        self.addCleanup(lab_ports.release, self.lab)\n'
                             'class T(Base):\n    def test_a(self):\n        lab_ports.reserve(self.lab)\n', None),
    # R per class through a function the module defines: the module releases (class A), and class B reserves only by
    # calling a module function that reserves, directly or through a chain of them defined outer first
    "reserve-class-via-helper": ('import lab_ports\nimport test_ship_reship_served as _lab\ndef _env(lab):\n'
                                 '    return _lab.kernel_env(lab, lab, lab, 1, "t")\nclass A:\n    def down(self, lab):\n'
                                 '        lab_ports.release(lab)\nclass B:\n    def up(self, lab):\n        return _env(lab)\n', "R"),
    "reserve-class-via-helper-chain": ('import lab_ports\ndef _boot(lab):\n    return _mid(lab)\ndef _mid(lab):\n'
                                       '    return _port(lab)\ndef _port(lab):\n    return lab_ports.reserve(lab)\nclass A:\n'
                                       '    def down(self, lab):\n        lab_ports.release(lab)\nclass B:\n'
                                       '    def up(self, lab):\n        return _boot(lab)\n', "R"),
    "clean-class-via-helper": ('import lab_ports, unittest\nimport test_ship_reship_served as _lab\ndef _env(lab):\n'
                               '    return _lab.kernel_env(lab, lab, lab, 1, "t")\nclass T(unittest.TestCase):\n'
                               '    def test_env(self):\n        self.addCleanup(lab_ports.release, "/lab")\n'
                               '        _env("/lab")\n', None),
    # a release read but never called nor handed to a call releases nothing: the module and its class are both unreleased
    "reserve-release-only-read": ('import lab_ports\nclass B:\n    def up(self, lab):\n        rel = lab_ports.release\n'
                                  '        self.p = lab_ports.reserve(lab)\n', "R"),
    # a listener whose port the scope reads and that the scope closes is a draw and release too, and so is a listener
    # built on port 0 by socket.create_server, a server class of http.server or socketserver (or one the module derives
    # from them) or asyncio's create_server
    "draw-listener-closed": ('import socket\ndef pick():\n    s = socket.socket()\n    s.bind(("127.0.0.1", 0))\n'
                             '    s.listen(8)\n    p = s.getsockname()[1]\n    s.close()\n    return p\n', "D"),
    "draw-listener-with": ('import socket\ndef pick():\n    with socket.socket() as s:\n        s.bind(("127.0.0.1", 0))\n'
                           '        s.listen(8)\n        return s.getsockname()[1]\n', "D"),
    "draw-create-server-with": ('import socket\ndef pick():\n    with socket.create_server(("127.0.0.1", 0)) as s:\n'
                                '        return s.getsockname()[1]\n', "D"),
    "draw-create-server-closed": ('from socket import create_server\ndef pick():\n    s = create_server(("127.0.0.1", 0))\n'
                                  '    p = s.getsockname()[1]\n    s.close()\n    return p\n', "D"),
    "draw-http-server-closed": ('import http.server\ndef pick():\n    h = http.server.HTTPServer(("127.0.0.1", 0), None)\n'
                                '    p = h.server_address[1]\n    h.server_close()\n    return p\n', "D"),
    "draw-threading-http-server-with": ('from http.server import ThreadingHTTPServer\ndef pick():\n'
                                        '    with ThreadingHTTPServer(("127.0.0.1", 0), None) as h:\n'
                                        '        return h.server_port\n', "D"),
    "draw-socketserver-closed": ('import socketserver\ndef pick():\n    srv = socketserver.TCPServer(("127.0.0.1", 0), None)\n'
                                 '    p = srv.socket.getsockname()[1]\n    srv.server_close()\n    return p\n', "D"),
    "draw-server-subclass": ('import socketserver\nclass Quiet(socketserver.ThreadingTCPServer):\n    daemon_threads = True\n'
                             'class Quieter(Quiet):\n    pass\ndef pick():\n    s = Quieter(("127.0.0.1", 0), None)\n'
                             '    p = s.server_address[1]\n    s.server_close()\n    return p\n', "D"),
    "draw-asyncio-create-server": ('import asyncio\nasync def pick(loop):\n'
                                   '    srv = await loop.create_server(asyncio.Protocol, "127.0.0.1", 0)\n'
                                   '    p = srv.sockets[0].getsockname()[1]\n    srv.close()\n    return p\n', "D"),
    "draw-asyncio-create-server-keyword": ('import asyncio\nasync def pick(loop):\n'
                                           '    srv = await loop.create_server(asyncio.Protocol, host="127.0.0.1", port=0)\n'
                                           '    async with srv:\n        return srv.sockets[0].getsockname()[1]\n', "D"),
    # a server that serves past its scope keeps its port: its close handed to a cleanup (not called here), or the server
    # kept on an attribute and closed by another method
    "clean-server-cleanup": ('import http.server, threading, unittest\nclass T(unittest.TestCase):\n    def serve(self):\n'
                             '        h = http.server.ThreadingHTTPServer(("127.0.0.1", 0), None)\n'
                             '        threading.Thread(target=h.serve_forever, daemon=True).start()\n'
                             '        self.addCleanup(h.server_close)\n        return h.server_port\n', None),
    "clean-server-attribute": ('import http.server, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                               '    def setUpClass(cls):\n        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), None)\n'
                               '        cls.port = cls.srv.server_address[1]\n    @classmethod\n    def tearDownClass(cls):\n'
                               '        cls.srv.server_close()\n', None),
    # F: a class that reserves in setUpClass releases on its failure path, by a class cleanup registered before the first
    # reserve, or by a try whose handlers all call tearDownClass (one catching broadly) in a class whose tearDownClass
    # releases
    "setup-unguarded": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                        '    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n'
                        '        cls.port = lab_ports.reserve(cls.lab)\n    @classmethod\n    def tearDownClass(cls):\n'
                        '        lab_ports.release(cls.lab)\n', "F"),
    "setup-unguarded-via-method": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                                   '    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n        cls._boot()\n'
                                   '    @classmethod\n    def _boot(cls):\n        cls._ports()\n    @classmethod\n'
                                   '    def _ports(cls):\n        cls.port = lab_ports.reserve(cls.lab)\n    @classmethod\n'
                                   '    def tearDownClass(cls):\n        lab_ports.release(cls.lab)\n', "F"),
    "setup-unguarded-via-helper": ('import lab_ports, tempfile, unittest\nimport test_ship_reship_served as _lab\n'
                                   'def _env(lab):\n    return _lab.kernel_env(lab, lab, lab, 1, "t")\n'
                                   'class T(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n'
                                   '        cls.lab = tempfile.mkdtemp()\n        cls.env = _env(cls.lab)\n'
                                   '    @classmethod\n    def tearDownClass(cls):\n        lab_ports.release(cls.lab)\n', "F"),
    "setup-cleanup-after-reserve": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                                    '    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n'
                                    '        cls.port = lab_ports.reserve(cls.lab)\n'
                                    '        cls.addClassCleanup(lab_ports.release, cls.lab)\n', "F"),
    "setup-cleanup-conditional": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                                  '    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n        if cls.lab:\n'
                                  '            cls.addClassCleanup(lab_ports.release, cls.lab)\n'
                                  '        cls.port = lab_ports.reserve(cls.lab)\n', "F"),
    "setup-cleanup-not-release": ('import lab_ports, shutil, tempfile, unittest\nclass T(unittest.TestCase):\n'
                                  '    @classmethod\n    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n'
                                  '        cls.addClassCleanup(shutil.rmtree, cls.lab)\n'
                                  '        cls.port = lab_ports.reserve(cls.lab)\n    @classmethod\n    def tearDownClass(cls):\n'
                                  '        lab_ports.release(cls.lab)\n', "F"),
    "setup-cleanup-atexit": ('import atexit, lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                             '    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n'
                             '        atexit.register(lab_ports.release, cls.lab)\n        cls.port = lab_ports.reserve(cls.lab)\n',
                             "F"),
    # a registrar of the class's own that tearDownClass drains: a failed setUpClass never runs it
    "setup-cleanup-own-registrar": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    _downs = []\n'
                                    '    @classmethod\n    def _on_down(cls, fn, *args):\n        cls._downs.append((fn, args))\n'
                                    '    @classmethod\n    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n'
                                    '        cls._on_down(lab_ports.release, cls.lab)\n        cls.port = lab_ports.reserve(cls.lab)\n'
                                    '    @classmethod\n    def tearDownClass(cls):\n        for fn, args in cls._downs:\n'
                                    '            fn(*args)\n', "F"),
    "setup-cleanup-other-class": ('import lab_ports, tempfile, unittest\nclass Other(unittest.TestCase):\n    pass\n'
                                  'class T(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n'
                                  '        cls.lab = tempfile.mkdtemp()\n        Other.addClassCleanup(lab_ports.release, cls.lab)\n'
                                  '        cls.port = lab_ports.reserve(cls.lab)\n', "F"),
    "setup-narrow-except": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                            '    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n        try:\n'
                            '            cls.port = lab_ports.reserve(cls.lab)\n        except unittest.SkipTest:\n'
                            '            cls.tearDownClass()\n            raise\n    @classmethod\n    def tearDownClass(cls):\n'
                            '        lab_ports.release(cls.lab)\n', "F"),
    "setup-handler-skips-teardown": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                                     '    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n        try:\n'
                                     '            cls.port = lab_ports.reserve(cls.lab)\n        except unittest.SkipTest:\n'
                                     '            raise\n        except BaseException:\n            cls.tearDownClass()\n'
                                     '            raise\n    @classmethod\n    def tearDownClass(cls):\n'
                                     '        lab_ports.release(cls.lab)\n', "F"),
    "setup-reserve-outside-try": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                                  '    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n'
                                  '        cls.port = lab_ports.reserve(cls.lab)\n        try:\n            cls.n = 1\n'
                                  '        except BaseException:\n            cls.tearDownClass()\n            raise\n'
                                  '    @classmethod\n    def tearDownClass(cls):\n        lab_ports.release(cls.lab)\n', "F"),
    "setup-teardown-keeps-port": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                                  '    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n        try:\n'
                                  '            cls.port = lab_ports.reserve(cls.lab)\n        except BaseException:\n'
                                  '            cls.tearDownClass()\n            raise\n    @classmethod\n'
                                  '    def tearDownClass(cls):\n        cls.lab = None\n    def test_down(self):\n'
                                  '        lab_ports.release(self.lab)\n', "F"),
    "clean-setup-class-cleanup": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                                  '    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n'
                                  '        cls.addClassCleanup(lab_ports.release, cls.lab)\n'
                                  '        cls.port = lab_ports.reserve(cls.lab)\n', None),
    "clean-setup-try-method": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                               '    def setUpClass(cls):\n        try:\n            cls._boot()\n        except BaseException:\n'
                               '            cls.tearDownClass()\n            raise\n    @classmethod\n    def _boot(cls):\n'
                               '        cls.lab = tempfile.mkdtemp()\n        cls.port = lab_ports.reserve(cls.lab)\n'
                               '    @classmethod\n    def tearDownClass(cls):\n        lab_ports.release(getattr(cls, "lab", None))\n',
                               None),
    "clean-setup-try-exception": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                                  '    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n        try:\n'
                                  '            cls.port = lab_ports.reserve(cls.lab)\n        except (OSError, Exception):\n'
                                  '            cls.tearDownClass()\n            raise\n    @classmethod\n    def tearDownClass(cls):\n'
                                  '        lab_ports.release(cls.lab)\n', None),
    "clean-setup-try-bare": ('import lab_ports, tempfile, unittest\nclass T(unittest.TestCase):\n    @classmethod\n'
                             '    def setUpClass(cls):\n        cls.lab = tempfile.mkdtemp()\n        try:\n'
                             '            cls.port = lab_ports.reserve(cls.lab)\n        except unittest.SkipTest:\n'
                             '            cls.tearDownClass()\n            raise\n        except:\n'
                             '            cls.tearDownClass()\n            raise\n    @classmethod\n    def tearDownClass(cls):\n'
                             '        lab_ports.release(cls.lab)\n', None),
    "clean-setup-teardown-inherited": ('import lab_ports, tempfile, unittest\nclass Base(unittest.TestCase):\n'
                                       '    @classmethod\n    def tearDownClass(cls):\n        lab_ports.release(cls.lab)\n'
                                       'class T(Base):\n    @classmethod\n    def setUpClass(cls):\n'
                                       '        cls.lab = tempfile.mkdtemp()\n        try:\n'
                                       '            cls.port = lab_ports.reserve(cls.lab)\n        except BaseException:\n'
                                       '            cls.tearDownClass()\n            raise\n', None),
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
        self.assertTrue(total["reservers"], "no module outside the served step reserves a port: R reads only the served "
                                            "population, and kernel_env's unit tests are unread")
        self.assertFalse(set(total["reservers"]) & set(names) | {DOOR_FILE} & set(total["reservers"]),
                         "the reservers are outside the population, and the door is in neither")
        print("LABPORTS population=%d files, kernel spawns=%d in %d files, reservers outside it=%d"
              % (len(names), len(total["spawns"]), len(spawning), len(total["reservers"])), file=sys.stderr)

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

    def test_every_class_that_reserves_in_setupclass_releases_on_its_failure_path(self):
        self._rule("F", "classes that reserve in setUpClass and would hold the ports if it raised")

    def test_each_planted_module_is_red_under_exactly_its_rule_and_the_clean_shapes_are_green(self):
        got = {}
        for name, (src, rule) in PLANTS.items():
            off = _scan_plant(src, name + ".py")
            got[name] = sorted(r for r in RULES if off[r])
        want = {name: [rule] if rule else [] for name, (_, rule) in PLANTS.items()}
        self.assertTrue(_package_door_names(), "tests/__init__.py binds the door under a name of its own, which the "
                                               "door-package-alias plants from-import; none was read from it")
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

    def test_a_module_outside_the_served_step_that_reserves_is_held_to_releasing(self):
        # a unit test that builds a lab kernel's environment holds the postal port kernel_env reserves; outside the served
        # step it is read under R (and A) all the same, and a module that reserves nothing is not read at all
        unit = ('import lab_ports, unittest\nimport test_ship_reship_served as _lab\nclass T(unittest.TestCase):\n'
                '    def test_env(self):\n%s        _lab.kernel_env("/lab", "/lab/c", "/lab/d", 1, "t")\n')
        for cleanup, want in (("", [("test_unit_env.py", 1), ("test_unit_env.py", 3)]),
                              ('        self.addCleanup(lab_ports.release, "/lab")\n', [])):
            with self.subTest(released=bool(cleanup)):
                root = tempfile.mkdtemp(prefix="labports-census-")
                self.addCleanup(shutil.rmtree, root, True)
                os.makedirs(os.path.join(root, "tests"))
                for f, src in (("test_clean_served.py", PLANTS["clean-door"][0]), ("test_unit_env.py", unit % cleanup),
                               ("test_other.py", "import os\nx = os.sep\n"),
                               (DOOR_FILE, "def reserve(owner):\n    return kernel_env(owner)\n")):
                    with open(os.path.join(root, "tests", f), "w") as fh:
                        fh.write(src)
                names, total = census(root, ["tests/test_*_served.py"], [])
                self.assertEqual(names, ["test_clean_served.py"])
                self.assertEqual(total["reservers"], ["test_unit_env.py"], "the door and a module reserving nothing are not read")
                self.assertEqual([(o[0], o[1]) for o in total["R"]], want)

    def test_a_module_outside_the_served_step_that_aliases_the_door_is_read_under_a(self):
        # a module outside the served step that reserves only through an alias calls no lab_ports.reserve, so the reserve
        # read alone would leave it unread; binding the door under another name brings it in, and A names it. The
        # package's names for the door are read from the root's own tests/__init__.py: under a package that binds it as
        # _door, a module from-importing _door is read and named although its text never spells lab_ports
        init = "from . import lab_ports as _lab_ports\nimport sys\nsys.modules.setdefault('lab_ports', _lab_ports)\n"
        cases = [(init, name, PLANTS[name][0], lines) for name, lines in (
            ("door-from-tests-aliased", [1]), ("door-package-alias", [1]), ("door-package-alias-relative", [1]),
            ("door-package-attribute", [3]), ("door-package-attribute-assigned", [2]),
            ("door-package-alias-attribute", [3]), ("door-member-assigned", [2]), ("door-member-in-tuple", [2]))]
        cases.append(("from . import lab_ports as _door\n", "renamed-package-alias",
                      "from tests import _door\ndef boot(lab):\n    return _door.reserve(lab)\n", [1]))
        for init_src, name, src, lines in cases:
            with self.subTest(plant=name):
                root = tempfile.mkdtemp(prefix="labports-census-")
                self.addCleanup(shutil.rmtree, root, True)
                os.makedirs(os.path.join(root, "tests"))
                for f, text in (("__init__.py", init_src), ("test_clean_served.py", PLANTS["clean-door"][0]),
                                ("test_unit_alias.py", src)):
                    with open(os.path.join(root, "tests", f), "w") as fh:
                        fh.write(text)
                names, total = census(root, ["tests/test_*_served.py"], [])
                self.assertEqual(total["reservers"], ["test_unit_alias.py"])
                self.assertEqual([(o[0], o[1]) for o in total["A"]], [("test_unit_alias.py", n) for n in lines])

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
        print("population %d files; reservers outside it, read under R, A and F: %d %s"
              % (len(names), len(total["reservers"]), total["reservers"]))
        for r in RULES + ("spawns",):
            print("%s %d" % (r, len(total[r])))
            print(_lines(total[r], cap=10))
    else:
        unittest.main()
