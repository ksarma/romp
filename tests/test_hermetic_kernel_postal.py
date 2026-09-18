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
of every class that attaches or detaches and restored in its tearDown (the tunnel tests), or all three around the one
call that provokes the revive (the peer-notify test), so its kernel never even asks. Peers is never set at import: the
kernel reads it at call time, and under xdist every worker imports every collected module before it runs a test, so the
"0" the tunnel tests once wrote at module level reached every module on every worker, and the remote-identity absorb
case (a bus notice gated on peers) was red in 5 of 6 full runs (diagnosed 2026-09-18). The placement test below reads
the module's assignments by position, and the probe beside it imports the module and runs one setUp to see the value.

The fixture rule below is static, so it holds for tests that skip here (no browser, no extension deps) and fails at
the spawn site, naming the file.
"""
import ast
import json
import os
import re
import subprocess
import sys
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


def _env_pops(node):
    """The keys `os.environ.pop(KEY, ...)` names anywhere under `node`."""
    keys = set()
    for n in ast.walk(node):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "pop" and _is_environ(n.func.value)
                and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
            keys.add(n.args[0].value)
    return keys


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
        """Read by position from the module's ast, not by text: the port is assigned at module level before the kernel
        loads (the kernel reads it at import); client-only is assigned before the load or in the setUp of every class
        that attaches or detaches; peers is assigned in each of those setUps and popped or restored in the matching
        tearDown, and NEVER at module level. A module-level peers assignment is the leak of 2026-09-18 (the header)."""
        tree = ast.parse(open(os.path.join(HERE, "test_kernel_tunnels.py"), encoding="utf-8", errors="replace").read())
        loads = [i for i, s in enumerate(tree.body) if _loads_kernel(s)]
        self.assertTrue(loads, "the module loads the kernel in-process at module level")
        top = [s for s in tree.body if not isinstance(s, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
        before_load = set().union(*(_env_writes(s) for s in tree.body[:loads[0]] if s in top)) if loads[0] else set()
        module_level = set().union(*(_env_writes(s) for s in top)) if top else set()
        self.assertIn("ROMP_POSTAL_PORT", before_load, "the port is set before the kernel module loads (it reads the port at import)")
        self.assertNotIn("ROMP_POSTAL_PEERS", module_level,
                         "peers is never set at module level: the kernel reads it at call time, and under xdist a value written at "
                         "import reaches every module on every worker (the remote-identity absorb case, red in 5 of 6 full runs)")
        classes = {c.name: c for c in tree.body if isinstance(c, ast.ClassDef)}
        attaching = [c for c in classes.values() if _attaches_or_detaches(c)]
        self.assertGreaterEqual(len(attaching), 2, "the scan sees the classes that attach or detach: %r" % [c.name for c in attaching])
        for cls in attaching:
            set_up, tear_down = _method_chain(cls, "setUp", classes), _method_chain(cls, "tearDown", classes)
            self.assertTrue(set_up, "%s attaches or detaches and so has a setUp" % cls.name)
            in_setup = set().union(*(_env_writes(f) for f in set_up))
            self.assertIn("ROMP_POSTAL_PEERS", in_setup, "%s.setUp (own or through super()) sets peers for its tests (a detach's refused bus notice revives the bus otherwise)" % cls.name)
            self.assertIn("ROMP_POSTAL_CLIENT_ONLY", before_load | in_setup, "%s: client-only before the load or in its setUp" % cls.name)
            self.assertTrue(tear_down, "%s restores peers in a tearDown" % cls.name)
            self.assertIn("ROMP_POSTAL_PEERS", set().union(*(_env_writes(f) | _env_pops(f) for f in tear_down)),
                          "%s.tearDown (own or through super()) pops or restores peers, so the value never outlives the test" % cls.name)

    def test_importing_the_attaching_module_writes_no_peers_setting_and_its_setup_pins_one_for_the_test(self):
        """Executed, not read: a fresh interpreter pops ROMP_POSTAL_PEERS, imports tests/test_kernel_tunnels.py (which
        loads the kernel in-process against its own temp state and starts no bus) and reports the variable after the
        import, inside an attaching class's setUp, and after its tearDown with a value a shell might have left. Before
        2026-09-18 the import alone wrote "0"."""
        probe = textwrap.dedent("""
            import json, os, shutil, sys
            os.environ.pop("ROMP_POSTAL_PEERS", None)
            sys.path.insert(0, %r)
            import test_kernel_tunnels as t
            out = {"after_import": os.environ.get("ROMP_POSTAL_PEERS")}
            os.environ["ROMP_POSTAL_PEERS"] = "1"
            case = t.TunnelConcierge("test_attach_requires_host")
            case.setUp()
            out["in_setup"] = os.environ.get("ROMP_POSTAL_PEERS")
            case.tearDown()
            out["after_teardown"] = os.environ.get("ROMP_POSTAL_PEERS")
            for d in (case.td, os.environ.get("XDG_STATE_HOME")):
                shutil.rmtree(d, ignore_errors=True)
            print(json.dumps(out))
        """ % HERE)
        env = dict(os.environ)
        env.pop("ROMP_POSTAL_PEERS", None)
        res = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=180, env=env, cwd=HERE)
        self.assertEqual(res.returncode, 0, res.stderr[-2000:])
        out = json.loads(res.stdout.strip().splitlines()[-1])
        self.assertIsNone(out["after_import"], "importing the module writes no peers setting (the kernel reads it at call time; a write at import leaks under xdist)")
        self.assertEqual(out["in_setup"], "0", "an attaching class's setUp turns peers off for its test")
        self.assertEqual(out["after_teardown"], "1", "...and its tearDown restores what it found")

    def test_the_peer_notify_guard_test_carries_the_trio_around_the_call_it_forces_to_fail(self):
        src = open(os.path.join(HERE, "test_kernel.py"), encoding="utf-8", errors="replace").read()
        body = src[src.index("def test_notify_bus_peer_is_guarded"):src.index("class CheckinMechanics")]
        self.assertIn('os.environ.update(ROMP_POSTAL_CLIENT_ONLY="1", ROMP_POSTAL_PEERS="0", ROMP_POSTAL_PORT="1")', body,
                      "client-only with peers off and a port nothing can bind, for the call the refusal revives the bus from")
        self.assertLess(body.index("os.environ.update("), body.index("km._notify_bus_peer("), "…set before the call")
        self.assertIn("os.environ.pop(k, None)", body, "…and restored after it")


if __name__ == "__main__":
    unittest.main()
