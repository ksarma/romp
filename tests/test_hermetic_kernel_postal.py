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
for EVERY module under tests/ (no module-level write of the variable, module-level if/try/for/with bodies included),
and the probe beside them imports the module in a fresh interpreter and runs one setUp, and one that fails, to see the
value. The restore is a cleanup rather than a tearDown since review round 1 (2026-09-18): unittest skips tearDown when
a subclass's setUp raises after the base's returned, and a tearDown restore left the 0 in the worker on that path.

The fixture rule below is static, so it holds for tests that skip here (no browser, no extension deps) and fails at
the spawn site, naming the file.
"""
import ast
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


def _is_environ(node):
    return isinstance(node, ast.Attribute) and node.attr == "environ" and isinstance(node.value, ast.Name) and node.value.id == "os"


def _env_writes(node):
    """The keys `os.environ[KEY] = ...` assigns anywhere under `node`."""
    keys = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Subscript) and _is_environ(t.value) and isinstance(t.slice, ast.Constant) and isinstance(t.slice.value, str):
                    keys.add(t.slice.value)
    return keys


def _env_pops(node, method="pop"):
    """The keys `os.environ.pop(KEY, ...)` names anywhere under `node` (`method` picks another mutator, setdefault)."""
    keys = set()
    for n in ast.walk(node):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == method and _is_environ(n.func.value)
                and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
            keys.add(n.args[0].value)
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


def _module_level_env_writes(tree):
    """The environment keys the module writes at import: `os.environ[KEY] = ...` and `os.environ.setdefault(KEY, ...)`
    in any statement _module_level_statements yields."""
    keys = set()
    for s in _module_level_statements(tree.body):
        keys |= _env_writes(s) | _env_pops(s, "setdefault")
    return keys


def _cleanup_restores(funcs, cls, classes, tree):
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
                keys |= _env_writes(t) | _env_pops(t)
    return keys


def _placement_faults(tree):
    """Every way a module that loads the kernel in-process and attaches misplaces a leg of the trio; empty when the
    placement holds. The port is assigned at module level before the kernel loads (the kernel reads it at import);
    peers is NEVER written at module level (the leak of 2026-09-18, module-level if/try/for/with bodies included);
    every class that attaches or detaches has a setUp (its own or through super()) that sets peers and registers a
    cleanup that restores it, and client-only is set before the load or in that setUp. A list rather than assertions
    so the check itself can be run over a synthetic module with the leak planted and shown to go red."""
    faults = []
    loads = [i for i, s in enumerate(tree.body) if _loads_kernel(s)]
    if not loads:
        return ["the module does not load the kernel in-process at module level"]
    before_load = set()
    for s in _module_level_statements(tree.body[:loads[0]]):
        before_load |= _env_writes(s)
    if "ROMP_POSTAL_PORT" not in before_load:
        faults.append("the port is not set before the kernel module loads (it reads the port at import)")
    if "ROMP_POSTAL_PEERS" in _module_level_env_writes(tree):
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
            in_setup |= _env_writes(f)
        if "ROMP_POSTAL_PEERS" not in in_setup:
            faults.append("%s.setUp (own or through super()) does not set peers for its tests (a detach's refused bus notice "
                          "revives the bus otherwise)" % cls.name)
        if "ROMP_POSTAL_CLIENT_ONLY" not in before_load | in_setup:
            faults.append("%s: client-only is neither before the load nor in its setUp" % cls.name)
        if "ROMP_POSTAL_PEERS" not in _cleanup_restores(set_up, cls, classes, tree):
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
        """Read by position from the module's ast, not by text (_placement_faults): the port is assigned at module level
        before the kernel loads (the kernel reads it at import); client-only is assigned before the load or in the setUp
        of every class that attaches or detaches; peers is assigned in each of those setUps and put back by a cleanup
        that setUp registers, and NEVER at module level. A module-level peers assignment is the leak of 2026-09-18 (the
        header); a tearDown-only restore is the hole of review round 1 (a subclass setUp that raises skips it)."""
        self.assertEqual(_placement_faults(ast.parse(_tunnels_source())), [])

    def test_the_placement_check_reds_on_a_planted_module_level_write_and_on_a_teardown_only_restore(self):
        """The check is run over synthetic copies of the real module so it is known to be able to fail (review round 1,
        2026-09-18): a module-level `os.environ["ROMP_POSTAL_PEERS"] = "0"` restored before the load, bare and inside a
        module-level `if` body; and the restore moved back into a tearDown with no cleanup registered."""
        src = _tunnels_source()
        for label, text in (("bare", _plant(src, 'os.environ["ROMP_POSTAL_PEERS"] = "0"\n')),
                            ("in an if body", _plant(src, 'if True:\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n')),
                            ("by setdefault", _plant(src, 'os.environ.setdefault("ROMP_POSTAL_PEERS", "0")\n'))):
            faults = _placement_faults(ast.parse(text))
            self.assertTrue(any("written at module level" in f for f in faults), "%s planted write: %r" % (label, faults))
        faults = _placement_faults(ast.parse(_teardown_only_restore(src)))
        self.assertTrue(any("registers no cleanup" in f for f in faults), "tearDown-only restore: %r" % faults)
        self.assertEqual(len(faults), 2, "one fault per attaching class, nothing else: %r" % faults)

    def test_no_module_under_tests_writes_the_peers_setting_at_module_level(self):
        """The import-time half of the rule, held for every .py under tests/ (review round 1, 2026-09-18): no module-level
        write of ROMP_POSTAL_PEERS, module-level if/try/for/with bodies included. The per-test half (set in setUp, put
        back by a cleanup) is a convention, checked above for the tunnels module alone; tests/README.md says so."""
        paths = sorted(glob.glob(os.path.join(HERE, "**", "*.py"), recursive=True))
        self.assertGreater(len(paths), 100, "the scan sees the test modules")
        writers = []
        for path in paths:
            tree = ast.parse(open(path, encoding="utf-8", errors="replace").read(), filename=path)
            if "ROMP_POSTAL_PEERS" in _module_level_env_writes(tree):
                writers.append(os.path.relpath(path, HERE))
        self.assertEqual(writers, [], "these modules write ROMP_POSTAL_PEERS at import; the kernel and the postal service "
                                      "read it at call time, and under xdist every worker imports every collected module")
        # the scan itself is known to see a planted write, bare and in an if body, and to ignore one inside a def
        seen = _module_level_env_writes(ast.parse('import os\nif True:\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n'))
        self.assertIn("ROMP_POSTAL_PEERS", seen)
        unseen = _module_level_env_writes(ast.parse('import os\ndef setUp(self):\n    os.environ["ROMP_POSTAL_PEERS"] = "0"\n'))
        self.assertNotIn("ROMP_POSTAL_PEERS", unseen)

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
        """The same planted assignment, run: a copy of the module with `os.environ["ROMP_POSTAL_PEERS"] = "0"` restored
        before the load reports "0" after the import, so the probe is known to see the leak it guards against (review
        round 1, 2026-09-18)."""
        out = self._tunnels_probe(_plant(_tunnels_source(), 'os.environ["ROMP_POSTAL_PEERS"] = "0"\n'))
        self.assertEqual(out["after_import"], "0", "the probe sees a module-level write at import")
        self.assertEqual(out["after_cleanups"], "1", "the planted copy's own cleanup still restores the shell's value")

    def test_the_peer_notify_guard_test_carries_the_trio_around_the_call_it_forces_to_fail(self):
        src = open(os.path.join(HERE, "test_kernel.py"), encoding="utf-8", errors="replace").read()
        body = src[src.index("def test_notify_bus_peer_is_guarded"):src.index("class CheckinMechanics")]
        self.assertIn('os.environ.update(ROMP_POSTAL_CLIENT_ONLY="1", ROMP_POSTAL_PEERS="0", ROMP_POSTAL_PORT="1")', body,
                      "client-only with peers off and a port nothing can bind, for the call the refusal revives the bus from")
        self.assertLess(body.index("os.environ.update("), body.index("km._notify_bus_peer("), "…set before the call")
        self.assertIn("os.environ.pop(k, None)", body, "…and restored after it")


if __name__ == "__main__":
    unittest.main()
