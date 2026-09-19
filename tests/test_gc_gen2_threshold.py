#!/usr/bin/env python3
"""The collector's third threshold, raised once at boot (_raise_gc_gen2_threshold, 2026-09-19).

CPython decides at each young-generation trigger which generation to collect and runs a FULL collection only when
counts[2] exceeds thresholds[2] AND the objects promoted since the last full collection exceed a quarter of the
long-lived total (counts[2] rises by one per generation-1 collection, so a full one fires at the first young trigger
after the generation-1 collection that lifts it over thresholds[2]). A production kernel at 6.8 h up read
counts [188, 5, 175] against thresholds [700, 10, 10]: at 175 against 10 the count gate was permanently open, so the
quarter rule alone timed full collections, 701 in 6.8 h (103 an hour, mean 2.97 s, max 5.70 s, 8.5% of a core), each
holding the interpreter lock so every page and request stalled with it. The step reads thresholds 0 and 1 as found and
sets [t0, t1, N], N from ROMP_GC_GEN2_THRESHOLD (default 1,000: the measured generation-1 rate, 5.6 a second, times a
180 s gap, rounded), so the collector's own generation-1 count, never a clock, spaces full collections at least 1,001
generation-1 collections apart.

Pinned here, on every build the suite runs: (a) the step sets exactly [t0, t1, N], leaves the first two as FOUND (a seed
off the defaults comes back untouched), is idempotent, and sets N rather than at least N; (b) the knob: an explicit
value applies, 0 leaves CPython's own thresholds and says nothing, unset and empty are the default, and a value that is
not a non-negative integer the collector can hold is said once on stderr (one line, the prefix, the knob's name, the
raw value and the default, asserted by structure) with the default applied; (c) the interpreter gate: the reason table
over build facts, a forced decline through the seam leaving the thresholds and saying the reason once beside them, and
this interpreter's own branch asserted from the thresholds read back against the build facts, never a version string
alone; the read-back post-condition and the never-raises guard through a collector stub; (d) main calls the step once,
after the hook's install and before the boot warm, and the step's functions read no clock; loading the module under a
private name touches no threshold (the step runs from main alone, as install_gc_hook is kept out of test processes);
(e) the reference's gc bullet names the knob, the default, the mechanism and the read-back keys, as continuation lines
at 80 columns (the Documented pins slice the bullet to the next list item); and (f) the exact stderr line captured from
a child interpreter's real stderr, count one, for a malformed knob and for the default boot.

Interpreter facts the gate reads, measured 2026-09-19 with one probe per build: the third threshold binds the
full-collection rate on CPython 3.10 to 3.13 and 3.14.5 up; CPython 3.14.0 to 3.14.4 (the incremental collector) do not
store it and read back 0; the free-threaded build stores it and never consults it, with the GIL off and re-enabled
alike, so the gate reads sys.abiflags, never the runtime GIL state. Synthetic fixtures only."""
import ast
import gc
import inspect
import io
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads (the tests/test_perf_gc_block.py preamble): the modules resolve their state root at
# import, and only pytest runs conftest's floor. The root minted here is outside conftest's belt, so session hosts are
# switched off in it as well.
_ROOT = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = _ROOT
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.makedirs(os.path.join(_ROOT, "romp"), exist_ok=True)
with open(os.path.join(_ROOT, "romp", "session-hosts"), "w") as _fh:
    _fh.write("off")
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
_THRESHOLDS_BEFORE_LOAD = gc.get_threshold()
km = load_source("romp_kernel_gc_threshold", os.path.join(BIN, "romp-kernel"))
_THRESHOLDS_AFTER_LOAD = gc.get_threshold()
_SAID_AT_LOAD = set(getattr(km, "_GC_THRESHOLD_SAID", ()))

KNOB = "ROMP_GC_GEN2_THRESHOLD"
PREFIX = "romp-kernel: gc gen2 threshold:"

# This interpreter's BUILD facts, the same ones the gate reads. The expectation below is derived from them; every test
# then asserts the branch taken from the thresholds READ BACK, so a gate keyed on the wrong fact is red here, not green
# by agreement with itself.
FREE_THREADED = "t" in getattr(sys, "abiflags", "")
INCREMENTAL = (3, 14, 0) <= tuple(sys.version_info[:3]) <= (3, 14, 4)
EXPECT_APPLIED = (sys.implementation.name == "cpython" and not FREE_THREADED and not INCREMENTAL
                  and (3, 10) <= tuple(sys.version_info[:2]) <= (3, 14))
# The word the decline line must carry on this build, so the line names the collector's shape, not just a refusal.
DECLINE_TOKEN = "free-threaded" if FREE_THREADED else ("incremental" if INCREMENTAL else None)


def _free_port():
    """An ephemeral port on the loopback for a child's never-started postal bus (the hermetic trio)."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Thresholds(unittest.TestCase):
    """A test that calls the step on this process's collector: the thresholds, the said-set and the knob are saved
    before and put back by cleanups, whatever happens (a leaked gc.set_threshold would change every later test's
    collection cadence in this worker; a leaked said-key would swallow a later test's line; tearDown alone is skipped
    when a subclass setUp raises, so cleanups do the restoring)."""

    def setUp(self):
        self.assertTrue(gc.isenabled(), "the step reads and sets the automatic collector's thresholds")
        saved = gc.get_threshold()
        self.addCleanup(gc.set_threshold, *saved)
        said = set(km._GC_THRESHOLD_SAID)
        km._GC_THRESHOLD_SAID.clear()
        self.addCleanup(self._restore_said, said)
        knob = os.environ.pop(KNOB, None)
        self.addCleanup(self._restore_knob, knob)

    @staticmethod
    def _restore_said(said):
        km._GC_THRESHOLD_SAID.clear()
        km._GC_THRESHOLD_SAID.update(said)

    @staticmethod
    def _restore_knob(value):
        if value is None:
            os.environ.pop(KNOB, None)
        else:
            os.environ[KNOB] = value

    def seed(self, third=10, t0=None, t1=None):
        """Set the collector to a known tuple and return what it READS BACK (on CPython 3.14.0 to 3.14.4 the third value
        is not stored and comes back 0; the seed is whatever the collector says it is)."""
        cur = gc.get_threshold()
        gc.set_threshold(cur[0] if t0 is None else t0, cur[1] if t1 is None else t1, third)
        return gc.get_threshold()

    def call(self):
        """Run the step with stderr captured; the result and the lines it said."""
        err = io.StringIO()
        with redirect_stderr(err):
            result = km._raise_gc_gen2_threshold()
        return result, err.getvalue().splitlines()

    def assertDeclined(self, seed, result, lines, token=None):
        """The decline shape: nothing set, None returned, one prefixed line naming the refusal and the thresholds left."""
        self.assertIsNone(result)
        self.assertEqual(gc.get_threshold(), seed, "a decline leaves the thresholds as found")
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith(PREFIX), lines[0])
        self.assertIn("not applied", lines[0])
        self.assertIn(str(list(seed)), lines[0], "the line carries the thresholds left in place")
        if token:
            self.assertIn(token, lines[0])


class Applies(_Thresholds):
    """(a) The step sets exactly [t0, t1, N], leaves the first two as found, is idempotent, and sets N, never at least N."""

    def test_the_boot_step_sets_exactly_the_third_threshold_and_leaves_the_first_two(self):
        seed = self.seed(10)
        t0, t1 = seed[:2]
        result, lines = self.call()
        if not EXPECT_APPLIED:
            self.assertDeclined(seed, result, lines, DECLINE_TOKEN)
            return
        self.assertEqual(km.GC_GEN2_THRESHOLD_DEFAULT, 1000)
        self.assertEqual(gc.get_threshold(), (t0, t1, 1000))
        self.assertEqual(result, (t0, t1, 1000))
        self.assertEqual(lines, [], "an applied step says nothing")
        result2, lines2 = self.call()                             # idempotent: the same tuple, no line
        self.assertEqual(result2, (t0, t1, 1000))
        self.assertEqual(gc.get_threshold(), (t0, t1, 1000))
        self.assertEqual(lines2, [])
        high = self.seed(5000)                                    # exactly N, never "at least N"
        self.assertEqual(high, (t0, t1, 5000))
        result3, lines3 = self.call()
        self.assertEqual(result3, (t0, t1, 1000))
        self.assertEqual(gc.get_threshold(), (t0, t1, 1000))
        self.assertEqual(lines3, [])

    def test_the_first_two_thresholds_are_read_at_the_call_not_assumed(self):
        cur = gc.get_threshold()
        seed = self.seed(10, t0=cur[0] + 3, t1=cur[1] + 1)       # off CPython's defaults, on purpose
        self.assertEqual(seed[:2], (cur[0] + 3, cur[1] + 1))
        result, lines = self.call()
        if not EXPECT_APPLIED:
            self.assertDeclined(seed, result, lines, DECLINE_TOKEN)
            return
        self.assertEqual(gc.get_threshold(), (cur[0] + 3, cur[1] + 1, km.GC_GEN2_THRESHOLD_DEFAULT))
        self.assertEqual(result, (cur[0] + 3, cur[1] + 1, km.GC_GEN2_THRESHOLD_DEFAULT))
        self.assertEqual(lines, [])


class Knob(_Thresholds):
    """(b) ROMP_GC_GEN2_THRESHOLD, read at the call: a value applies, 0 is the silent off switch, unset and empty are the
    default, and a malformed value is said once, by structure, with the default applied."""

    def knob(self):
        err = io.StringIO()
        with redirect_stderr(err):
            n = km._gc_gen2_threshold_knob()
        return n, err.getvalue().splitlines()

    def test_an_explicit_value_applies(self):
        os.environ[KNOB] = "250"
        self.assertEqual(self.knob(), (250, []))
        seed = self.seed(10)
        result, lines = self.call()
        if not EXPECT_APPLIED:
            self.assertDeclined(seed, result, lines, DECLINE_TOKEN)
            return
        self.assertEqual(gc.get_threshold(), seed[:2] + (250,))
        self.assertEqual(result, seed[:2] + (250,))
        self.assertEqual(lines, [])

    def test_zero_leaves_cpythons_own_thresholds_and_says_nothing(self):
        os.environ[KNOB] = "0"
        self.assertEqual(self.knob(), (0, []))
        seed = self.seed(10)
        result, lines = self.call()
        self.assertIsNone(result)                                 # on every build: 0 returns before the gate
        self.assertEqual(gc.get_threshold(), seed)
        self.assertEqual(lines, [])

    def test_unset_and_empty_are_the_default(self):
        self.assertEqual(km.GC_GEN2_THRESHOLD_DEFAULT, 1000)
        self.assertEqual(self.knob(), (km.GC_GEN2_THRESHOLD_DEFAULT, []))
        os.environ[KNOB] = ""
        self.assertEqual(self.knob(), (km.GC_GEN2_THRESHOLD_DEFAULT, []))

    def _malformed(self, raw):
        """The parser under a value it rejects: the default, and exactly one line whose STRUCTURE is the prefix, then
        knob=repr(value), then prose ending in the default; a second read adds no line."""
        default = km.GC_GEN2_THRESHOLD_DEFAULT
        os.environ[KNOB] = raw
        n, lines = self.knob()
        self.assertEqual(n, default)
        self.assertEqual(len(lines), 1, lines)
        line = lines[0]
        self.assertTrue(line.startswith(PREFIX), line)
        self.assertIn(KNOB, line)
        self.assertIn(repr(raw), line)
        self.assertRegex(line, r"^%s %s=%s .*\b%d$" % (re.escape(PREFIX), re.escape(KNOB), re.escape(repr(raw)), default))
        self.assertEqual(self.knob(), (default, []), "said once per process")
        return line

    def test_a_non_integer_says_one_line_naming_the_knob_and_the_value_and_yields_the_default(self):
        self._malformed("abc")

    def test_a_negative_integer_is_malformed_too(self):
        self._malformed("-5")

    def test_a_value_the_collector_cannot_hold_is_malformed(self):
        self._malformed(str(2 ** 31))                             # gc.set_threshold takes a C int

    def test_the_step_under_a_malformed_value_applies_the_default_and_says_the_line_once_across_two_calls(self):
        os.environ[KNOB] = "abc"
        seed = self.seed(10)
        result, lines = self.call()
        result2, lines2 = self.call()
        knob_lines = [l for l in lines + lines2 if KNOB in l]
        self.assertEqual(len(knob_lines), 1, lines + lines2)
        self.assertRegex(knob_lines[0], r"^%s %s='abc' .*\b%d$" % (re.escape(PREFIX), re.escape(KNOB), km.GC_GEN2_THRESHOLD_DEFAULT))
        if EXPECT_APPLIED:
            self.assertEqual(lines + lines2, knob_lines, "nothing else said")
            self.assertEqual(result, seed[:2] + (km.GC_GEN2_THRESHOLD_DEFAULT,))
            self.assertEqual(result2, result)
            self.assertEqual(gc.get_threshold(), result)
            return
        others = [l for l in lines + lines2 if KNOB not in l]
        self.assertDeclined(seed, result, others, DECLINE_TOKEN)   # the decline's own line, also once
        self.assertIsNone(result2)
        self.assertEqual(lines2, [], "the second call says nothing new")


class Gate(_Thresholds):
    """(c) The interpreter gate: a pure table over build facts; a forced decline through the seam; and this build's own
    branch, asserted from the thresholds read back."""

    def test_the_reason_table_over_build_facts(self):
        reason = km._gc_gen2_threshold_reason
        for v in ((3, 10, 20), (3, 11, 15), (3, 12, 3), (3, 13, 14), (3, 14, 5), (3, 14, 6), (3, 14, 12)):
            self.assertIsNone(reason("cpython", v, ""), v)
        for v in ((3, 14, 0), (3, 14, 2), (3, 14, 4)):
            r = reason("cpython", v, "")
            self.assertIsInstance(r, str, v)
            self.assertIn("incremental", r)
        for v in ((3, 14, 6), (3, 13, 14), (3, 12, 3)):
            r = reason("cpython", v, "t")                         # the BUILD fact: a t build declines at any version
            self.assertIsInstance(r, str, v)
            self.assertIn("free-threaded", r)
        self.assertIsNotNone(reason("cpython", (3, 14, 4), "t"), "two reasons hold at once; either declines")
        r = reason("pypy", (3, 10, 14), "")
        self.assertIsInstance(r, str)
        self.assertIn("pypy", r)
        for v in ((3, 9, 19), (3, 15, 0), (4, 0, 0)):
            r = reason("cpython", v, "")
            self.assertIsInstance(r, str, v)
            self.assertIn("%d.%d" % v[:2], r)
        here = reason()                                           # the defaults are this interpreter's build facts
        self.assertEqual(here, reason(sys.implementation.name, tuple(sys.version_info[:3]), getattr(sys, "abiflags", "")))
        self.assertEqual(here is None, EXPECT_APPLIED, here)

    def test_a_declining_reason_leaves_the_thresholds_and_is_said_once_beside_them(self):
        real = km._gc_gen2_threshold_reason
        km._gc_gen2_threshold_reason = lambda *a, **k: "a synthetic reason for this test"
        self.addCleanup(setattr, km, "_gc_gen2_threshold_reason", real)
        seed = self.seed(10)
        result, lines = self.call()
        self.assertDeclined(seed, result, lines, "a synthetic reason for this test")
        self.assertIn(sys.implementation.name, lines[0], "the line names the interpreter")
        self.assertIn("%d.%d.%d" % tuple(sys.version_info[:3]), lines[0])
        result2, lines2 = self.call()
        self.assertIsNone(result2)
        self.assertEqual(lines2, [], "said once")
        self.assertEqual(gc.get_threshold(), seed)

    def test_this_interpreter_takes_the_branch_its_build_facts_predict(self):
        before = self.seed(10)
        result, lines = self.call()
        after = gc.get_threshold()
        applied = after[2] == km.GC_GEN2_THRESHOLD_DEFAULT and after[:2] == before[:2] and result == after
        print("gc gen2 threshold step on %s %s%s: %s; thresholds %s -> %s; stderr %r"
              % (sys.implementation.name, ".".join(str(v) for v in sys.version_info[:3]), getattr(sys, "abiflags", ""),
                 "APPLIED" if applied else "DECLINED", list(before), list(after), lines))
        self.assertEqual(applied, EXPECT_APPLIED,
                         "the branch read back from the thresholds disagrees with the build facts: %s -> %s, %r"
                         % (before, after, lines))
        if EXPECT_APPLIED:
            self.assertEqual(lines, [])
        else:
            self.assertDeclined(before, result, lines, DECLINE_TOKEN)


class ReadBack(_Thresholds):
    """(c, continued) The post-condition and the guard, through a stub for the kernel's `gc`: a collector that does not
    store the value is said once and treated as not applied; one whose accessor raises is said once and the step
    returns (it runs in main before the credentials check, and a collector quirk must not stop the kernel)."""

    def _stub(self, stub):
        real_gc, real_reason = km.gc, km._gc_gen2_threshold_reason
        km.gc = stub
        km._gc_gen2_threshold_reason = lambda *a, **k: None        # the gate passes; the collector is the subject
        self.addCleanup(setattr, km, "gc", real_gc)
        self.addCleanup(setattr, km, "_gc_gen2_threshold_reason", real_reason)

    def test_a_collector_that_does_not_store_the_value_is_said_once_and_treated_as_not_applied(self):
        sets = []
        self._stub(types.SimpleNamespace(get_threshold=lambda: (700, 10, 0), set_threshold=lambda *a: sets.append(a)))
        real_before = gc.get_threshold()
        result, lines = self.call()
        self.assertIsNone(result)
        self.assertEqual(sets, [(700, 10, km.GC_GEN2_THRESHOLD_DEFAULT)], "the step asked for exactly [t0, t1, N]")
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith(PREFIX), lines[0])
        self.assertIn("reads back", lines[0])
        self.assertIn("[700, 10, 0]", lines[0])
        self.assertIn(str(km.GC_GEN2_THRESHOLD_DEFAULT), lines[0])
        self.assertIn("not applied", lines[0])
        self.assertEqual(gc.get_threshold(), real_before, "the real collector was never touched")
        result2, lines2 = self.call()
        self.assertIsNone(result2)
        self.assertEqual(lines2, [], "said once")
        self.assertEqual(sets, [(700, 10, km.GC_GEN2_THRESHOLD_DEFAULT)] * 2, "idempotent: the same tuple asked again")

    def test_a_collector_whose_accessor_raises_is_said_once_and_the_step_returns(self):
        def boom():
            raise RuntimeError("no thresholds here")
        self._stub(types.SimpleNamespace(get_threshold=boom, set_threshold=lambda *a: None))
        result, lines = self.call()                               # raises nothing
        self.assertIsNone(result)
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith(PREFIX), lines[0])
        self.assertIn("RuntimeError", lines[0])
        self.assertIn("no thresholds here", lines[0])
        result2, lines2 = self.call()
        self.assertIsNone(result2)
        self.assertEqual(lines2, [], "said once")


class Isolation(unittest.TestCase):
    """(d) The step runs from main alone: loading the module under a private name touches no threshold and says nothing,
    and by the module's own AST the only call site is inside main (install_gc_hook is kept out of test processes the
    same way)."""

    def test_loading_the_module_leaves_the_collectors_thresholds_and_says_nothing(self):
        self.assertEqual(_THRESHOLDS_BEFORE_LOAD, _THRESHOLDS_AFTER_LOAD)
        self.assertEqual(_SAID_AT_LOAD, set())

    def test_the_only_call_site_is_main(self):
        tree = ast.parse(Path(km.__file__).read_text(), filename=km.__file__)
        sites = []
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(fn):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "_raise_gc_gen2_threshold"):
                    sites.append(fn.name)
        self.assertEqual(sites, ["main"], sites)


class Wiring(unittest.TestCase):
    """(d, continued) main calls the step once, after the hook's install and before the boot warm; the step's functions
    read no clock (the event that spaces full collections is the collector's own generation-1 count)."""

    def test_main_raises_the_threshold_after_the_hook_and_before_the_boot_warm(self):
        src = inspect.getsource(km.main)
        self.assertEqual(src.count("_raise_gc_gen2_threshold()"), 1)
        self.assertLess(src.index("_PERF_STATS.install_gc_hook()"), src.index("_raise_gc_gen2_threshold()"))
        self.assertLess(src.index("_raise_gc_gen2_threshold()"), src.index("_boot_warm()"))

    def test_the_step_reads_no_clock(self):
        clocks = {"time", "monotonic", "perf_counter", "datetime", "sleep", "now"}
        for fn in (km._raise_gc_gen2_threshold, km._gc_gen2_threshold_knob, km._gc_gen2_threshold_reason,
                   km._gc_threshold_say):
            tree = ast.parse(inspect.getsource(fn))
            names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            self.assertFalse(names & clocks, (fn.__name__, names & clocks))
            self.assertFalse(attrs & clocks, (fn.__name__, attrs & clocks))


class Documented(unittest.TestCase):
    """(e) docs/reference.md's gc bullet names the knob, the default, the mechanism, the declining collectors, the
    stderr prefix and the read-back keys, as continuation lines (the bullet is sliced to the next list item here and
    in tests/test_perf_gc_block.py, so a blank line or a new bullet would cut both pins short)."""

    def test_the_reference_names_the_knob_the_default_the_mechanism_and_the_read_back(self):
        doc = Path(HERE).parent.joinpath("docs", "reference.md").read_text()
        para = doc[doc.index("- `gc`:"):]
        para = para[:para.index("\n- `", 10)]
        flat = " ".join(para.split())
        self.assertIn("`%s`" % KNOB, flat)
        self.assertIn("default %s" % format(km.GC_GEN2_THRESHOLD_DEFAULT, ","), flat)   # one source for the number
        self.assertIn("quarter", flat)
        self.assertIn("`%s`" % PREFIX, flat)
        self.assertIn("`heap.gc.thresholds`", flat)
        self.assertIn("free-threaded", flat)
        self.assertIn("3.14.0 to 3.14.4", flat)
        self.assertNotIn("\n\n", para, "continuation lines only")
        for line in para.splitlines():
            self.assertLessEqual(len(line), 80, line)


# The child a Subprocess test runs: the module loaded under a private name, the step called twice, the thresholds
# before and after and both results printed as one JSON line. Its stderr is the real one, so the line the parent reads
# is the exact bytes the kernel wrote.
CHILD = r'''
import gc, json, os, sys
sys.path.insert(0, sys.argv[1])
from romp_load import load_source
BIN = sys.argv[2]
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel_gc_threshold_child", os.path.join(BIN, "romp-kernel"))
before = list(gc.get_threshold())
r1 = km._raise_gc_gen2_threshold()
r2 = km._raise_gc_gen2_threshold()
print(json.dumps({"before": before, "after": list(gc.get_threshold()), "r1": r1, "r2": r2,
                  "said": sorted(km._GC_THRESHOLD_SAID)}))
'''


class Subprocess(unittest.TestCase):
    """(f) The exact stderr line, captured from a child interpreter of this build: count one for a malformed knob, and
    for the default boot nothing where the step applies and one decline line where it does not. The child carries the
    hermetic trio (a postal bus of its own that is never started) and a state root of its own."""

    def _run(self, knob):
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "romp"), exist_ok=True)
        with open(os.path.join(root, "romp", "session-hosts"), "w") as fh:
            fh.write("off")
        script = os.path.join(root, "child.py")
        with open(script, "w") as fh:
            fh.write(CHILD)
        env = dict(os.environ)
        env.pop("ROMP_STATE_DIR", None)
        env.pop(KNOB, None)
        env.update(XDG_STATE_HOME=root, ROMP_KERNEL_NO_OPEN="1", ROMP_SERVE_TOKEN="test-token-DO-NOT-USE",
                   PYTHONDONTWRITEBYTECODE="1",
                   ROMP_POSTAL_PORT=str(_free_port()), ROMP_POSTAL_PEERS="0", ROMP_POSTAL_CLIENT_ONLY="1",
                   ROMP_POSTAL_HERMETIC="1")
        if knob is not None:
            env[KNOB] = knob
        p = subprocess.run([sys.executable, "-B", script, HERE, BIN], env=env, capture_output=True, text=True,
                           timeout=180)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout.strip().splitlines()[-1])
        ours = [l for l in p.stderr.splitlines() if l.startswith(PREFIX)]
        return out, ours

    def test_a_malformed_knob_is_said_exactly_once_on_the_childs_stderr(self):
        out, ours = self._run("abc")
        knob_lines = [l for l in ours if KNOB in l]
        self.assertEqual(len(knob_lines), 1, ours)
        self.assertRegex(knob_lines[0], r"^%s %s='abc' .*\b%d$" % (re.escape(PREFIX), re.escape(KNOB), km.GC_GEN2_THRESHOLD_DEFAULT))
        if EXPECT_APPLIED:
            self.assertEqual(ours, knob_lines)
            self.assertEqual(out["after"], out["before"][:2] + [km.GC_GEN2_THRESHOLD_DEFAULT])
            self.assertEqual(out["r1"], out["after"])
            self.assertEqual(out["r2"], out["after"])
            self.assertEqual(out["said"], ["knob"])
            return
        others = [l for l in ours if KNOB not in l]
        self.assertEqual(len(others), 1, ours)
        self.assertIn("not applied", others[0])
        self.assertIn(str(out["before"]), others[0])
        if DECLINE_TOKEN:
            self.assertIn(DECLINE_TOKEN, others[0])
        self.assertEqual(out["after"], out["before"])
        self.assertIsNone(out["r1"])
        self.assertIsNone(out["r2"])
        self.assertEqual(out["said"], ["interpreter", "knob"])

    def test_the_default_boot_says_nothing_where_it_applies_and_one_line_where_it_does_not(self):
        out, ours = self._run(None)
        if EXPECT_APPLIED:
            self.assertEqual(ours, [])
            self.assertEqual(out["after"], out["before"][:2] + [km.GC_GEN2_THRESHOLD_DEFAULT])
            self.assertEqual(out["r1"], out["after"])
            self.assertEqual(out["r2"], out["after"])
            self.assertEqual(out["said"], [])
            return
        self.assertEqual(len(ours), 1, ours)
        self.assertIn("not applied", ours[0])
        self.assertIn(str(out["before"]), ours[0])
        if DECLINE_TOKEN:
            self.assertIn(DECLINE_TOKEN, ours[0])
        self.assertEqual(out["after"], out["before"])
        self.assertIsNone(out["r1"])
        self.assertEqual(out["said"], ["interpreter"])


if __name__ == "__main__":
    unittest.main()
