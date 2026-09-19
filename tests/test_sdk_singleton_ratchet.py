#!/usr/bin/env python3
"""The suite's backend-singleton ratchet (tests/conftest.py: _sdk_singleton_restored and the class- and module-scoped
_sdk_singleton_class_boundary and _sdk_singleton_module_boundary), tested by running pytest in a child over scratch
modules that load the real kernel under this checkout's conftest, the way tests/test_tempdir_hygiene.py's
RunLeavesNothing tests the temp-root floors: each scratch case takes one of the roads the suite takes to
km._sdk_backend, and the outer test reads what the ratchet said about it.

The defect the ratchet guards (2026-09-19): kernel.py builds its SdkBackend lazily, the first km._sdk() call
constructing it over jd.STATE as it stands and caching it in km._sdk_backend for the life of the process.
tests/test_kernel.py::ViewBuilder pointed jd.STATE at a sandbox, its card builds reached km._sdk() and built the
singleton over the sandbox, and its tearDown restored jd.STATE and removed the directory without touching the
singleton; a later module's chat signature consulted that backend, whose fork_children statted the removed
registry, answered {} on the OSError and scanned no registry, so a derivation counting registry stats read 0
against 39 in a test that did nothing wrong, and only under an order that ran ViewBuilder first.

The population, measured at this branch's base: six classes in five modules leaked the singleton (ViewBuilder,
CostWeighting, BuildSessionDiffRows, FeedWarmResolveBumpsTheLedgerRevision, SharedViewInBuilds and
PushSurvivesOneFailedChatBuild), each fixed in a commit of its own with ViewBuilder's shape: ViewBuilder's before the
ratchet, the other four after it, one per module, found by the review round that ran the modules alone. The count
comes from running every module ALONE with the ratchet on. The population is a union, every set saved beside the list
with the script that derives it: the 237 modules a census plugin (a scratch pytest plugin over two full -n 4 runs) saw
take a road to a root change (a jd.STATE assignment, a jd._rebind_state call, a singleton construction, or a singleton
that changed), the 94 that load the kernel under its shared name, the 272 whose text assigns jd.STATE or calls
_rebind_state in process (the private-kernel modules among them included: a private name isolates the kernel's
globals and not jd's, so they move the shared jd.STATE, and their own singletons are outside this fixture by the
stated limit), and the 316 the first sweep ran; 364 modules in all. The first sweep, over its 316 at the base, found
the 4 red on these leaks and 1 red for an unrelated pre-existing reason (tests/test_sdk_rate_limit_usage.py, an
unrestored ROMP_SERVE_TOKEN setdefault the judge fixture's environment check names; identical with the ratchet off);
at this head every one of the 364 is green alone except that one. The full-suite census saw none of the five, because
an earlier first builder in every worker made their builds cache hits: a green suite run is no evidence a module is
clean, and the module-alone sweep is the measurement.

The ratchet judges TRANSITIONS, at three windows. The test: the singleton read before the test and after its own
teardown, and the test whose own transition made the bad state fails (a different object left, or the directory
removed under the object it found). The class and module boundaries: a read at the scope's start and at its end,
after tearDownClass or tearDownModule, and the scope whose setup or teardown made the bad state fails, the error
landing on the scope's last test with the boundary named. The setup before a test: a singleton found over a gone
directory that no verdict has named yet was made by something outside every window (import-time code) and is
reported once per worker, at the first test that meets it, worded as inherited; every later test that inherits
the same object is quiet. Its allowances are derived from the transition, never from a list of test names:
None before and, after, the kernel's own class (module romp_sdk_backend, qualname SdkBackend; a look-alike is
refused) over jd.STATE AS THE TEST FOUND IT, that directory present, is a worker's lazy first build under the root
the test inherited, the kernel's own design; None before and False after is the kernel's own unavailable outcome.
WHICH test builds first depends on the run (the xdist scheduler, the subset, the module order), so a name list
could never be right: the census that found ViewBuilder saw a different first builder on each of three workers.
The remedy is one per road: the sandbox sentence when the value left is the kernel's class over a root that is
not the reference or not a directory; put back the object you found otherwise. A kernel re-execution inside a test replaces the marker
function and resets the singleton, so the before value is stale and only what the test LEFT is judged, against
jd.STATE as the reload re-bound it: None or False pass, the lazy build over the loader's root passes, and a build
anywhere else is named with the re-execution wording; the kernel's FIRST load inside a test (no marker before) is
the same road, never an exemption.

The scratch modules, one nested run each, the cases in method order (unittest runs a class's methods
alphabetically, and each case's `before` is what the previous case left):
  A, the singleton built under the run root first:
    a. the worker's lazy first build (None before; after, a backend over jd.STATE, present) passes;
    b. ViewBuilder's fixed shape (save km._sdk_backend, sandbox jd.STATE, build, put both back, remove the
       sandbox) passes;
    c. a kernel re-execution inside the test, the singleton reset and rebuilt over jd.STATE, is not judged;
    d. a rebuild over the SAME root left in place fails: another object under an equal state_dir, said as such
       (the readers hold the object, not the path), with the object road's remedy;
    e. ViewBuilder's original leak with the sandbox kept fails, naming the change and no gone directory;
    f. removing the directory under the singleton e left (the same object, present before and gone after) fails
       as this test's own transition, with the gone clause;
    g. ViewBuilder's original leak with the sandbox removed and a regular FILE written at the path fails, naming
       the change, the gone clause (a file is not a directory) and the sandbox remedy (its before value, f's gone
       object, was already named, so g starts quietly);
    h. a test that does nothing under g's gone object passes: inherited, already named, not accused;
    i. resetting the singleton to None and leaving it fails with the object road's remedy and no sandbox sentence.
  B, the leak as the worker's first build, and the re-execution road:
    a. None before and, after, a backend over a removed sandbox: the allowance does not cover it;
    b. a kernel re-execution that then builds over a removed sandbox fails with the re-execution wording and the
       gone clause;
    c. a kernel re-execution that then builds over a KEPT sandbox, jd.STATE restored, fails with the re-execution
       wording and no gone clause (the road the first form of the fixture exempted);
    d. XDG_STATE_HOME moved to a fresh root (hosts off), a re-execution so the judge re-binds jd.STATE there, then
       the lazy build over that root passes: the reference on this road is jd.STATE after the test (last in B,
       since it moves the child's environment).
  C, the first build over a sandbox that stands:
    a. None before and, after, a backend over a kept sandbox, jd.STATE elsewhere: the allowance does not
       cover it either (it asks for jd.STATE, not for any directory that exists).
  D, a class teardown that removes the directory under the singleton its tests left:
    One.a builds over a kept sandbox stored on the class and fails as its own; One.b does nothing and passes at
    its own window; tearDownClass removes the sandbox and writes a regular FILE at the path, and the class
    boundary fails at One.b's teardown with the gone clause (a file is not a directory); Two.a and Two.b do
    nothing under the named object and pass.
  E, an import-time leak (the module builds over a sandbox after loading the kernel, restores jd.STATE and
    removes the sandbox, before any test runs):
    a. does nothing and is the first test to meet the state: an ERROR at setup, worded as inherited, with no remedy
       addressed to it; b. does nothing and passes; c. makes a kept-sandbox leak of its own and fails as its own.
  K, a class that moves jd.STATE for its tests:
    One: setUpClass moves jd.STATE to a class sandbox; a's lazy build lands over it and passes at its own window
    (it inherited that root); b passes; tearDownClass restores jd.STATE and keeps the sandbox, and the class
    boundary fails at One.b's teardown as the author. Two: setUpClass saves the singleton and jd.STATE, resets
    the singleton and moves jd.STATE to its sandbox; a builds and passes; tearDownClass puts both back and
    removes its sandbox: quiet.
  L, a module teardown that removes the directory under the singleton its tests left:
    a builds over a kept sandbox stored on the module and fails as its own; b passes; tearDownModule removes it
    and the module boundary fails at b's teardown with the module named; the class end is quiet on the named
    object.
  H and H2, over a head that loads NO kernel at import (the worker's first load happens inside the test):
    H.a loads the kernel, then builds over a kept sandbox and fails with the first-load wording; H2.a loads the
    kernel, then makes the lazy build over the loader's root and passes (the run exits 0).
  F, the values the slot can be handed that are not the kernel's build over the inherited root:
    a. a class named SdkBackend defined in the scratch module, over jd.STATE, as the worker's first value: refused
       by the class check, rendered module-qualified (test_scratch.SdkBackend over ...), the object remedy;
    b. None left in place of it fails (object remedy); c. the kernel's own unavailable outcome (km._sdk_import_notice
       made to raise, so _sdk_locked's except branch sets False) passes; d. None left in place of False fails;
    e. the real lazy build over the run root passes; f. False left in place of the backend fails; g. a
    SimpleNamespace left fails, rendered as types.SimpleNamespace over no state_dir. Every failing case carries
    the object remedy and no sandbox sentence.
  J, the first build over a sandbox with jd.STATE LEFT at the sandbox: the singleton agrees with jd.STATE as left,
    and the ratchet still fails it, on the root the test inherited; the judge fixture names the STATE leak in the
    same teardown (two failures on one item render as an exception group in pytest 9), and the outer test reads
    both texts.

Mutations of the fixture run against this module, each landed and reverted (2026-09-19): the same-object gone
transition deleted (A.f passes silently); the gone check made absolute again (A.h, E.b and D.Two fail as false
accusations and every error count rises); the inherited report deleted (E.a passes: an import-time leak is never
reported); the named list dropped from the inherited report (E.b errors too); the class-scoped end judgment
deleted (D.One.b and K.One.b show no boundary error); the module-scoped end judgment deleted (L.b shows none);
the boundary comparing its end only to the last read (K.One passes silently); the boundary's restore exemption
dropped (K.Two errors); os.path.isdir replaced by os.path.exists (D.One's boundary verdict disappears: a file at
the path exists); the named skip at the boundary dropped (a second report at the class or module end of A, B, C, D, E, K
and L; where the scope's last case fails on its own, the boundary failure folds into that item's one teardown
report, so those runs pin it by reading the boundary text, not the count); the old re-execution exemption restored,
only the gone check surviving a changed marker (B.c and H.a pass silently); the marker ignored, every test on the
same-marker road (A.c fails falsely on the stale pre-reload object); a None marker before treated as the same-marker
road (H2.a fails falsely once the reference is the before read) or as an exemption (H.a passes); the changed road
compared to jd.STATE before the test (B.d fails falsely); the gone clause dropped from the re-execution wording
(B.b's clause assertion); the class check dropped, or reduced to the qualname (F.a's look-alike passes); the
reference moved to jd.STATE after the test (J.a passes this fixture); the None-to-False allowance removed (F.c
errors); any False after admitted (F.f passes); a None after treated as nothing left (A.i and F.d pass); the
sandbox remedy printed on every road (F.a, F.b, F.d, F.f, F.g and A.i assert it absent); the rebuild road rendered
as before (A.d's text); the allowance gate opened to any before value (A.d passes); identity replaced by equality of
state_dir (A.d passes); the root comparison dropped (C.a passes).
"""
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from romp_load import load_source  # noqa: F401  a direct run's floor lands with this import (tests/romp_load.py)

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
# Hermetic state BEFORE any load: romp modules resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

RATCHET = "left the kernel's backend singleton (km._sdk_backend)"
REMEDY_A = "save km._sdk_backend before moving jd.STATE and put it back where jd.STATE is restored"
REMEDY_B = "Put back the object the test found, None or False included, not an equal one"
SANDBOX = "A test that reaches km._sdk() under a sandboxed jd.STATE"      # the sandbox road's sentence, absent on the object road
REBUILT = "after another SdkBackend over the same directory (the readers hold the object, not the path)"
GONE = "whose state_dir is no longer a directory"
REEXEC = ("re-executed the kernel (or loaded it for the first time) and left the kernel's backend singleton "
          "(km._sdk_backend)")
INHERITED = "starts under the kernel's backend singleton (km._sdk_backend) over a directory that no longer exists"
INHERITED_KEPT = ("starts under the kernel's backend singleton (km._sdk_backend) over a directory that is not jd.STATE, before any "
                  "test in this worker has run")
PUT_BACK_GONE = "put back the kernel's backend singleton (km._sdk_backend) it found, whose directory is gone: "
BOUNDARY = "'s class or module boundary (tearDownClass, tearDownModule or a class- or module-scoped fixture)"
SHARED_STATE = "left shared state changed"     # the judge fixture's text: quiet in every case here, so the ratchet's is the only red

SCRATCH_HEAD = textwrap.dedent('''\
    import os, shutil, sys, tempfile, unittest
    from pathlib import Path
    from romp_load import load_source     # the suite's loader (tests/__init__.py registers it under tests.conftest)
    os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
    os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
    os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
    os.environ.pop("ROMP_STATE_DIR", None)
    # This module's own state root, hosts off: per-session hosts are on by default, and a backend built over a root with
    # no session-hosts file starts a real bin/romp-session-host for any session it connects (CLAUDE.md, Testing). The
    # runner's conftest floors the run root it minted and only that one; the lazy first builds below (A.a and every case
    # that builds over this root) build over THIS one, so the switch is written here, before any build, as sandbox() does.
    os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"))
    Path(os.environ["XDG_STATE_HOME"], "romp", "session-hosts").write_text("off\\n")
    KERNEL = os.path.join(os.environ["ROMP_RATCHET_BIN"], "romp-kernel")
    km = load_source("romp_kernel", KERNEL)
    jd = km.jd

    def sandbox():
        """A state root of the test's own, hosts off: the runner's belt covers the run root only (CLAUDE.md, Testing)."""
        root = Path(tempfile.mkdtemp())
        (root / "session-hosts").write_text("off\\n")
        return root

    def build_over(root):
        """ViewBuilder's road to the singleton: jd.STATE at a sandbox and the lazy build reached through km._sdk()."""
        jd.STATE = root
        km._sdk_backend = None
        return km._sdk()
''')

SCRATCH_A = SCRATCH_HEAD + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_lazy_first_build_under_the_run_root_passes(self):
            assert km._sdk_backend is None
            be = km._sdk()
            assert be is not None and be.state_dir == jd.STATE and jd.STATE.is_dir()
            assert not be.session_hosts_on()       # the module's root carries the off switch (CLAUDE.md, Testing)

        def test_b_a_saved_and_restored_singleton_passes(self):
            saved = (jd.STATE, km._sdk_backend)
            root = sandbox()
            assert build_over(root).state_dir == root
            jd.STATE, km._sdk_backend = saved
            shutil.rmtree(root)

        def test_c_a_kernel_reexecution_inside_the_test_is_not_judged(self):
            before = km._sdk_backend
            load_source("romp_kernel", KERNEL)
            assert km._sdk_backend is None            # the reload's module-level reset
            be = km._sdk()
            assert be is not before and be.state_dir == jd.STATE

        def test_d_a_rebuilt_singleton_over_the_same_root_fails(self):
            before = km._sdk_backend
            km._sdk_backend = None
            rebuilt = km._sdk()
            assert rebuilt is not before and rebuilt.state_dir == before.state_dir

        def test_e_the_leak_with_the_sandbox_kept_fails(self):
            saved = jd.STATE
            build_over(sandbox())
            jd.STATE = saved                          # the sandbox stands; the singleton stays over it

        def test_f_removing_the_directory_under_the_singleton_it_found_fails(self):
            be = km._sdk_backend                      # e's object, over its kept sandbox
            assert be.state_dir != jd.STATE and be.state_dir.is_dir()
            shutil.rmtree(be.state_dir)               # the same object before and after; its directory present, then gone

        def test_g_the_leak_with_the_sandbox_removed_fails(self):
            saved = jd.STATE
            root = sandbox()
            build_over(root)
            jd.STATE = saved
            shutil.rmtree(root)
            root.write_text("a regular file where the directory was\\n")   # exists, and is not a directory

        def test_h_doing_nothing_under_an_inherited_gone_singleton_passes(self):
            assert km._sdk_backend.state_dir.is_file()        # g's object; g was named for it, so this test is not

        def test_i_resetting_the_singleton_to_none_fails(self):
            km._sdk_backend = None                    # the next reader would rebuild over whatever jd.STATE is then
''')

SCRATCH_B = SCRATCH_HEAD + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_leak_as_the_first_build_fails(self):
            assert km._sdk_backend is None
            saved = jd.STATE
            root = sandbox()
            jd.STATE = root
            km._sdk()                                 # the worker's lazy first build, over the sandbox
            jd.STATE = saved
            shutil.rmtree(root)

        def test_b_a_reexecution_that_builds_over_a_removed_sandbox_fails(self):
            load_source("romp_kernel", KERNEL)
            saved = jd.STATE
            root = sandbox()
            build_over(root)
            jd.STATE = saved
            shutil.rmtree(root)

        def test_c_a_reexecution_that_builds_over_a_kept_sandbox_fails(self):
            load_source("romp_kernel", KERNEL)
            saved = jd.STATE
            build_over(sandbox())
            jd.STATE = saved                          # the sandbox stands; the singleton stays over it

        def test_d_a_reexecution_under_a_moved_environment_root_then_the_lazy_build_passes(self):
            new = Path(tempfile.mkdtemp())            # last in B: this moves the child's environment for good
            (new / "romp").mkdir()
            (new / "romp" / "session-hosts").write_text("off\\n")
            os.environ["XDG_STATE_HOME"] = str(new)
            load_source("romp_kernel", KERNEL)        # re-executes judge.py too: jd.STATE re-binds from the environment
            assert jd.STATE == new / "romp" and km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE
''')

SCRATCH_C = SCRATCH_HEAD + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_first_build_over_a_kept_sandbox_fails(self):
            assert km._sdk_backend is None
            saved = jd.STATE
            jd.STATE = sandbox()
            km._sdk()                                 # the worker's lazy first build, over a sandbox that stands
            jd.STATE = saved
''')

SCRATCH_D = SCRATCH_HEAD + textwrap.dedent('''\

    class One(unittest.TestCase):
        root = None

        @classmethod
        def tearDownClass(cls):
            shutil.rmtree(cls.root)
            cls.root.write_text("a regular file where the directory was\\n")   # exists, and is not a directory

        def test_a_builds_over_a_kept_sandbox_stored_on_the_class(self):
            saved = jd.STATE
            One.root = sandbox()
            build_over(One.root)
            jd.STATE = saved

        def test_b_does_nothing(self):
            assert km._sdk_backend.state_dir == One.root and One.root.is_dir()

    class Two(unittest.TestCase):
        def test_a_does_nothing(self):
            assert km._sdk_backend.state_dir == One.root and One.root.is_file()

        def test_b_does_nothing(self):
            pass
''')

SCRATCH_E = SCRATCH_HEAD + textwrap.dedent('''\

    _root = sandbox()                                 # import-time code, before any test: the leak no window sees made
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved
    shutil.rmtree(_root)

    class Cases(unittest.TestCase):
        def test_a_does_nothing_and_is_the_first_to_meet_the_state(self):
            pass

        def test_b_does_nothing(self):
            assert not km._sdk_backend.state_dir.exists()

        def test_c_makes_a_kept_sandbox_leak_of_its_own(self):
            saved = jd.STATE
            build_over(sandbox())
            jd.STATE = saved
''')

SCRATCH_K = SCRATCH_HEAD + textwrap.dedent('''\

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved_state = jd.STATE
            cls.root = sandbox()
            jd.STATE = cls.root                       # the class's root for every test in it

        @classmethod
        def tearDownClass(cls):
            jd.STATE = cls.saved_state                # the sandbox stands; the singleton built over it is not put back

        def test_a_the_lazy_build_over_the_class_root_passes_at_its_own_window(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == One.root

        def test_b_does_nothing(self):
            pass

    class Two(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved
            shutil.rmtree(cls.root)

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == Two.root
''')

SCRATCH_L = SCRATCH_HEAD + textwrap.dedent('''\

    _root = None

    def tearDownModule():
        shutil.rmtree(_root)

    class Cases(unittest.TestCase):
        def test_a_builds_over_a_kept_sandbox_stored_on_the_module(self):
            global _root
            saved = jd.STATE
            _root = sandbox()
            build_over(_root)
            jd.STATE = saved

        def test_b_does_nothing(self):
            assert km._sdk_backend.state_dir == _root and _root.is_dir()
''')


SCRATCH_HEAD_LAZY = SCRATCH_HEAD.replace(
    'km = load_source("romp_kernel", KERNEL)\njd = km.jd\n',
    'km = jd = None                        # no kernel at import: the worker\'s first load happens inside the test\n'
    '\n'
    'def load():\n'
    '    global km, jd\n'
    '    km = load_source("romp_kernel", KERNEL)\n'
    '    jd = km.jd\n')
assert "def load():" in SCRATCH_HEAD_LAZY and "km = jd = None" in SCRATCH_HEAD_LAZY, SCRATCH_HEAD_LAZY

SCRATCH_H = SCRATCH_HEAD_LAZY + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_first_load_then_a_build_over_a_kept_sandbox_fails(self):
            assert "romp_kernel" not in sys.modules
            load()
            saved = jd.STATE
            jd.STATE = sandbox()
            km._sdk()                                 # the first build of the worker, over a sandbox that stands
            jd.STATE = saved
''')

SCRATCH_H2 = SCRATCH_HEAD_LAZY + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_first_load_then_the_lazy_build_over_the_loaders_root_passes(self):
            assert "romp_kernel" not in sys.modules
            load()
            assert km._sdk().state_dir == jd.STATE
''')


SCRATCH_F = SCRATCH_HEAD + textwrap.dedent('''\
    import types

    class SdkBackend:
        """A look-alike: the kernel's class name, defined here, with a state_dir over the run root."""
        def __init__(self, root):
            self.state_dir = root

    class Cases(unittest.TestCase):
        def test_a_a_look_alike_over_jd_state_as_the_workers_first_value_fails(self):
            assert km._sdk_backend is None
            km._sdk_backend = SdkBackend(jd.STATE)

        def test_b_none_left_in_place_of_the_look_alike_fails(self):
            km._sdk_backend = None

        def test_c_the_kernels_unavailable_outcome_passes(self):
            assert km._sdk_backend is None
            saved = km._sdk_import_notice
            def unavailable():
                raise RuntimeError("the SDK will not import (scratch)")
            km._sdk_import_notice = unavailable
            try:
                assert km._sdk() is None               # _sdk_locked's except branch: the slot is False, the caller gets None
            finally:
                km._sdk_import_notice = saved
            assert km._sdk_backend is False

        def test_d_none_left_in_place_of_false_fails(self):
            assert km._sdk_backend is False
            km._sdk_backend = None

        def test_e_the_real_lazy_build_over_the_run_root_passes(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE

        def test_f_false_left_in_place_of_the_backend_fails(self):
            km._sdk_backend = False

        def test_g_a_simplenamespace_left_fails(self):
            km._sdk_backend = types.SimpleNamespace()
''')

SCRATCH_J = SCRATCH_HEAD + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_first_build_over_a_sandbox_with_jd_state_left_there_fails(self):
            assert km._sdk_backend is None
            jd.STATE = sandbox()                      # LEFT here: the singleton agrees with jd.STATE as left
            assert km._sdk().state_dir == jd.STATE
''')


SCRATCH_N = SCRATCH_HEAD + textwrap.dedent("""\

    class One(unittest.TestCase):
        def test_a_the_lazy_first_build(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE

    class Sandboxed(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved_state = jd.STATE
            cls.root = sandbox()
            jd.STATE = cls.root                       # moved for the tests, no build: One's singleton stays over the run root

        @classmethod
        def tearDownClass(cls):
            jd.STATE = cls.saved_state
            shutil.rmtree(cls.root)

        def test_a_does_nothing_under_a_singleton_over_the_run_root(self):
            assert km._sdk_backend is not None and km._sdk_backend.state_dir != jd.STATE

    class Two(unittest.TestCase):
        def test_a_leaves_none(self):
            km._sdk_backend = None                    # accused at its own window

        def test_b_the_lazy_rebuild_over_the_run_root_after_the_accused_reset(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE   # allowed at its own window; the class end has nothing to add

    class Three(unittest.TestCase):
        def test_a_leaves_none_as_the_last_test_of_a_class_that_started_on_a_real_backend(self):
            km._sdk_backend = None

    class Four(unittest.TestCase):
        def test_a_the_lazy_rebuild(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE

        def test_b_leaves_false_as_the_last_test(self):
            km._sdk_backend = False

    class Five(unittest.TestCase):
        def test_a_none_in_place_of_false(self):
            assert km._sdk_backend is False
            km._sdk_backend = None

        def test_b_the_lazy_rebuild(self):
            assert km._sdk().state_dir == jd.STATE

    class Six(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            km._sdk_backend = None                    # the class drops the object it found; a test then rebuilds over the same root

        def test_a_the_lazy_rebuild_the_next_module_inherits(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE
""")

SCRATCH_N2 = textwrap.dedent("""\
    import sys, unittest
    km = sys.modules["romp_kernel"]                   # the kernel the first module loaded: no re-execution here
    jd = km.jd

    class Follow(unittest.TestCase):
        def test_a_leaves_none_as_the_last_test_of_the_module(self):
            assert km._sdk_backend is not None
            km._sdk_backend = None
""")

SCRATCH_S6 = SCRATCH_HEAD + textwrap.dedent("""\

    _root = sandbox()                                 # import-time code: a build over a sandbox that STANDS, jd.STATE restored
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved

    class Cases(unittest.TestCase):
        def test_a_is_the_first_to_meet_the_state_and_leaks_on_its_own(self):
            assert km._sdk_backend.state_dir == _root and _root.is_dir() and jd.STATE != _root
            saved = jd.STATE
            build_over(sandbox())                     # a kept-sandbox leak of its own, judged in the same teardown
            jd.STATE = saved

        def test_b_does_nothing(self):
            pass
""")

SCRATCH_M = SCRATCH_HEAD + textwrap.dedent("""\

    class One(unittest.TestCase):
        def test_a_the_lazy_first_build(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE

    class Two(unittest.TestCase):
        @classmethod
        def tearDownClass(cls):
            saved = jd.STATE
            cls.root = sandbox()
            build_over(cls.root)                      # the teardown itself builds a new singleton over a sandbox that stands
            jd.STATE = saved

        def test_a_does_nothing(self):
            pass

    class Three(unittest.TestCase):
        @classmethod
        def tearDownClass(cls):
            km._sdk_backend = None                    # a class "cleaning up": the next reader rebuilds over whatever jd.STATE is then

        def test_a_does_nothing_under_twos_object(self):
            assert km._sdk_backend.state_dir == Two.root and Two.root.is_dir()

    class Four(unittest.TestCase):
        def test_a_does_nothing_under_none(self):
            assert km._sdk_backend is None

    class Five(unittest.TestCase):
        @classmethod
        def tearDownClass(cls):
            saved = jd.STATE
            cls.root = sandbox()
            build_over(cls.root)                      # None at the start, a singleton over a sandbox at the end
            jd.STATE = saved

        def test_a_does_nothing_under_none(self):
            assert km._sdk_backend is None

    class Six(unittest.TestCase):
        def test_a_does_nothing_under_fives_object(self):
            assert km._sdk_backend.state_dir == Five.root
""")

SCRATCH_P = SCRATCH_HEAD + textwrap.dedent("""\

    class One(unittest.TestCase):
        root = None

        def test_a_leaks_over_a_kept_sandbox(self):
            saved = jd.STATE
            One.root = sandbox()
            build_over(One.root)                      # named at its own window
            jd.STATE = saved

    class Two(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved     # the object it found, put back
            shutil.rmtree(cls.root)
            shutil.rmtree(One.root)                   # and the directory under it removed

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == Two.root

    class Three(unittest.TestCase):
        def test_a_does_nothing_under_the_gone_object(self):
            assert not km._sdk_backend.state_dir.exists()
""")

SCRATCH_G = SCRATCH_HEAD + textwrap.dedent("""\
    import types

    class Fake:
        __module__ = "romp_sdk_backend"               # the kernel's module name claimed by a class defined here
        def __init__(self, root):
            self.state_dir = root

    class Cases(unittest.TestCase):
        def test_a_a_look_alike_claiming_the_kernels_module_as_the_workers_first_value_fails(self):
            assert km._sdk_backend is None
            km._sdk_backend = Fake(jd.STATE)

        def test_b_a_reexecution_then_a_simplenamespace_left_fails(self):
            load_source("romp_kernel", KERNEL)
            assert km._sdk_backend is None            # the reload's module-level reset
            km._sdk_backend = types.SimpleNamespace(state_dir=jd.STATE)
""")

SCRATCH_R1 = SCRATCH_HEAD + textwrap.dedent("""\

    class Cases(unittest.TestCase):
        def test_a_the_first_build_then_the_run_root_removed_fails(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE
            shutil.rmtree(jd.STATE)                   # the singleton is over the reference root, which is now gone
""")

SCRATCH_R2 = SCRATCH_HEAD + textwrap.dedent("""\

    class Cases(unittest.TestCase):
        def test_a_a_reexecution_the_lazy_build_then_the_run_root_removed_fails(self):
            load_source("romp_kernel", KERNEL)        # the judge re-binds and creates jd.STATE
            assert km._sdk().state_dir == jd.STATE
            shutil.rmtree(jd.STATE)
""")


def nested_run(text, follower=None):
    """pytest in a child over one scratch module written to a fresh directory, under this checkout's conftest
    (loaded as a plugin: the module sits outside tests/, where no conftest is discovered), verbose and with the
    all-outcomes summary, so the outer test reads each case's outcome and the ratchet's text. The child's
    environment is the precedent's (tests/test_tempdir_hygiene.py, RunLeavesNothing): a fresh TMPDIR, the
    parent's pytest variables dropped so the child records its own run, and the bin directory the scratch
    module loads the kernel from. `follower` is the text of a second module written beside the first. Returns
    (returncode, stdout and stderr)."""
    fresh = tempfile.mkdtemp()
    case = os.path.join(fresh, "case")
    os.makedirs(case)
    path = os.path.join(case, "test_scratch.py")
    with open(path, "w") as f:
        f.write(text)
    if follower is not None:                # a second module, collected after the first (pytest keeps the directory order)
        with open(os.path.join(case, "test_scratch2.py"), "w") as f:
            f.write(follower)
    env = dict(os.environ, TMPDIR=fresh, PYTHONDONTWRITEBYTECODE="1", ROMP_RATCHET_BIN=BIN)
    for var in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_CURRENT_TEST",
                "PYTEST_XDIST_WORKER", "PYTEST_XDIST_WORKER_COUNT", "ROMP_TESTS_SYSTEM_TMPDIR"):
        env.pop(var, None)
    r = subprocess.run([sys.executable, "-m", "pytest", "-p", "tests.conftest", "-p", "no:cacheprovider",
                        "-v", "-rA", "--tb=short", case],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout + r.stderr


def outcomes(out):
    """{"<Class>.<method>": set of the phase outcomes pytest printed for it} from the verbose lines: a case the
    ratchet fails at its teardown shows PASSED for its call and ERROR for its teardown; one it reports at setup
    shows ERROR alone."""
    seen = {}
    for cls, m, o in re.findall(r"test_scratch2?\.py::(\w+)::(test_\w+) (PASSED|FAILED|ERROR)\b", out):
        seen.setdefault("%s.%s" % (cls, m), set()).add(o)
    return seen


def _split(m):
    """(clause, remedy) from a matched "<who> <clause>. Fix: <remedy>" message, the clause with the ratchet's
    common head stripped so the tests read the part that names the transition."""
    clause, remedy = m.group(1), m.group(2)
    if clause.startswith(RATCHET + " "):
        clause = clause[len(RATCHET) + 1:]
    return clause, remedy


def verdict(out, cls, method):
    """The ratchet's own-leak verdict on `cls.method` as (clause, remedy), from the message that starts with the
    case's nodeid; None when the ratchet said nothing about it as a test."""
    m = re.search(r"::%s::%s ((?:left|re-executed)[^\n]*?)\. Fix: ([^\n]*)" % (re.escape(cls), re.escape(method)), out)
    return _split(m) if m else None


def inherited(out, cls, method, head=INHERITED):
    """The text of the inherited report on `cls.method` (the object named, and the sentence saying this test did not
    make it), or None; `head` picks the gone wording (the default) or the kept-root one (INHERITED_KEPT)."""
    m = re.search(r"::%s::%s %s: ([^\n]*)" % (re.escape(cls), re.escape(method), re.escape(head)), out)
    return m.group(1) if m else None


def boundary(out, scope, module="test_scratch.py"):
    """The boundary verdict for `scope` ("::One" for a class, "" for the module) as (clause, remedy), or None."""
    m = re.search(r"%s%s%s ([^\n]*?)\. Fix: ([^\n]*)" % (re.escape(module), re.escape(scope), re.escape(BOUNDARY)), out)
    return _split(m) if m else None


class _NestedRun:
    """The shared half of a scratch run's tests; a mixin, so the runner collects only the runs below."""
    SCRATCH = ""
    FOLLOWER = None        # a second module's text, collected after the first, for the runs that need a module pair
    ERRORS = 0
    JUDGE_RED = False      # whether the judge fixture (_shared_state_restored) is expected to fail in the run too

    @classmethod
    def setUpClass(cls):
        cls.rc, cls.out = nested_run(cls.SCRATCH, cls.FOLLOWER)

    def assertRatchetPassed(self, cls, method):
        self.assertEqual(outcomes(self.out).get("%s.%s" % (cls, method)), {"PASSED"}, self.out)
        self.assertIsNone(verdict(self.out, cls, method), self.out)
        self.assertIsNone(inherited(self.out, cls, method), self.out)

    def assertRatchetFailed(self, cls, method, remedy=REMEDY_A):
        got = outcomes(self.out).get("%s.%s" % (cls, method), set())
        self.assertIn("PASSED", got, "the case's own asserts held; the ratchet is the only red: %s" % self.out)
        self.assertIn("ERROR", got, "the ratchet fails the case at its teardown: %s" % self.out)
        self.assertNotIn("FAILED", got, self.out)
        found = verdict(self.out, cls, method)
        self.assertIsNotNone(found, "the ratchet's message names the case's nodeid: %s" % self.out)
        clause, fix = found
        self.assertIn(remedy, fix, self.out)
        if remedy == REMEDY_A:
            self.assertIn(SANDBOX, fix, fix)
        return clause

    def assertObjectRoad(self, cls, method):
        """The case fails with the object road's remedy and no sandbox sentence: no sandbox was involved."""
        clause = self.assertRatchetFailed(cls, method, remedy=REMEDY_B)
        _, fix = verdict(self.out, cls, method)
        self.assertNotIn(SANDBOX, fix, "the sandbox sentence is the other road's: %s" % fix)
        self.assertNotIn(REMEDY_A, fix, fix)
        return clause

    def assertInherited(self, cls, method, head=INHERITED, own=False):
        """The inherited report lands on `cls.method` after its teardown, the body having run (PASSED, then ERROR); with
        `own`, the test's own verdict is expected beside it, else none."""
        self.assertEqual(outcomes(self.out).get("%s.%s" % (cls, method)), {"PASSED", "ERROR"},
                         "the body runs, and the report is the teardown's: %s" % self.out)
        text = inherited(self.out, cls, method, head)
        self.assertIsNotNone(text, self.out)
        if own:
            self.assertIsNotNone(verdict(self.out, cls, method), "the test's own verdict is judged too: %s" % self.out)
        else:
            self.assertIsNone(verdict(self.out, cls, method), "no own-leak verdict on the inheriting test: %s" % self.out)
        self.assertNotIn("Fix:", text, "no remedy is addressed to the test that inherited: %s" % text)
        self.assertIn("This test did not make it", text)
        return text

    def assertBoundaryFailed(self, scope, last, remedy=REMEDY_A):
        """The scope's boundary verdict, the error landing on `last` ("<Class>.<method>", the scope's last test)."""
        self.assertEqual(outcomes(self.out).get(last), {"PASSED", "ERROR"}, self.out)
        cls, method = last.split(".")
        self.assertIsNone(verdict(self.out, cls, method), "the last test is not accused as a test: %s" % self.out)
        found = boundary(self.out, scope)
        self.assertIsNotNone(found, "the boundary verdict names the scope %r: %s" % (scope, self.out))
        clause, fix = found
        self.assertIn(remedy, fix, self.out)
        return clause

    def test_the_judge_fixture_is_quiet_and_the_run_reds_only_on_the_ratchet(self):
        if not self.JUDGE_RED:
            self.assertNotIn(SHARED_STATE, self.out, "every case puts jd.STATE back; the ratchet's text is the only red")
        if self.ERRORS == 0:
            self.assertEqual(self.rc, 0, self.out)
            self.assertRegex(self.out, r"\d+ passed in", self.out)
        else:
            self.assertNotEqual(self.rc, 0, self.out)
            self.assertRegex(self.out, r"\d+ passed, %d errors? in" % self.ERRORS, self.out)


class LeakAfterFirstBuild(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_A
    ERRORS = 5

    def test_the_lazy_first_build_under_the_run_root_passes(self):
        self.assertRatchetPassed("Cases", "test_a_the_lazy_first_build_under_the_run_root_passes")

    def test_a_saved_and_restored_singleton_passes(self):
        self.assertRatchetPassed("Cases", "test_b_a_saved_and_restored_singleton_passes")

    def test_a_kernel_reexecution_inside_the_test_is_not_judged(self):
        self.assertRatchetPassed("Cases", "test_c_a_kernel_reexecution_inside_the_test_is_not_judged")

    def test_a_rebuilt_singleton_over_the_same_root_is_a_change(self):
        text = self.assertObjectRoad("Cases", "test_d_a_rebuilt_singleton_over_the_same_root_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + REBUILT), "identity, not the path, is the check, and the text says so: %s" % text)
        self.assertNotIn(GONE, text)

    def test_the_leak_with_the_sandbox_kept_names_the_change_and_no_gone_directory(self):
        text = self.assertRatchetFailed("Cases", "test_e_the_leak_with_the_sandbox_kept_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_removing_the_directory_under_the_singleton_it_found_is_this_tests_own_transition(self):
        text = self.assertRatchetFailed("Cases", "test_f_removing_the_directory_under_the_singleton_it_found_fails")
        self.assertTrue(text.startswith("over a directory it removed: SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), text)
        self.assertNotIn("changed", text)

    def test_the_leak_with_the_sandbox_removed_names_the_change_the_gone_directory_and_the_remedy(self):
        text = self.assertRatchetFailed("Cases", "test_g_the_leak_with_the_sandbox_removed_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), "a regular file at the path is not a directory: %s" % text)
        self.assertIsNone(inherited(self.out, "Cases", "test_g_the_leak_with_the_sandbox_removed_fails"),
                          "g starts under f's gone object, already named: no inherited report")

    def test_doing_nothing_under_an_inherited_gone_singleton_passes(self):
        self.assertRatchetPassed("Cases", "test_h_doing_nothing_under_an_inherited_gone_singleton_passes")

    def test_a_none_left_in_place_of_the_backend_is_the_object_road(self):
        text = self.assertObjectRoad("Cases", "test_i_resetting_the_singleton_to_none_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertTrue(text.endswith(", after None (not built)"), text)

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class LeakAsFirstBuild(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_B
    ERRORS = 3

    def test_the_leak_as_the_first_build_is_outside_the_allowance(self):
        text = self.assertRatchetFailed("Cases", "test_a_the_leak_as_the_first_build_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), text)

    def test_a_reexecution_that_builds_over_a_removed_sandbox_is_named_with_the_gone_clause(self):
        text = self.assertRatchetFailed("Cases", "test_b_a_reexecution_that_builds_over_a_removed_sandbox_fails")
        self.assertTrue(text.startswith(REEXEC + " over a root that is not jd.STATE: SdkBackend over "), text)
        self.assertIn(", jd.STATE ", text)
        self.assertTrue(text.endswith(", " + GONE), text)
        self.assertNotIn("changed", text)

    def test_a_reexecution_that_builds_over_a_kept_sandbox_is_named_by_what_it_left(self):
        text = self.assertRatchetFailed("Cases", "test_c_a_reexecution_that_builds_over_a_kept_sandbox_fails")
        self.assertTrue(text.startswith(REEXEC + " over a root that is not jd.STATE: SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_a_reexecution_under_a_moved_environment_root_then_the_lazy_build_passes(self):
        self.assertRatchetPassed("Cases", "test_d_a_reexecution_under_a_moved_environment_root_then_the_lazy_build_passes")

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        # The last case fails on its own at teardown, and a boundary failure on the same item would fold into that one
        # teardown report (one exception group, one counted error), so the count cannot see it: read the text.
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class FirstBuildOverAKeptSandbox(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_C
    ERRORS = 1

    def test_the_first_build_over_a_kept_sandbox_is_outside_the_allowance(self):
        text = self.assertRatchetFailed("Cases", "test_a_the_first_build_over_a_kept_sandbox_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)     # the one case is the last: see B's note on the count
        self.assertIsNone(boundary(self.out, ""), self.out)


class ClassTeardownRemovesTheDirectory(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_D
    ERRORS = 2

    def test_the_first_build_over_the_class_sandbox_fails_as_its_own(self):
        text = self.assertRatchetFailed("One", "test_a_builds_over_a_kept_sandbox_stored_on_the_class")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_the_class_boundary_names_the_directory_its_teardown_removed(self):
        self.assertEqual(outcomes(self.out).get("One.test_b_does_nothing"), {"PASSED", "ERROR"}, self.out)
        text = self.assertBoundaryFailed("::One", "One.test_b_does_nothing")
        self.assertTrue(text.startswith("over a directory it removed: SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), "a regular file at the path is not a directory: %s" % text)

    def test_the_class_that_inherits_the_named_object_is_quiet(self):
        self.assertRatchetPassed("Two", "test_a_does_nothing")
        self.assertRatchetPassed("Two", "test_b_does_nothing")
        self.assertIsNone(boundary(self.out, "::Two"), self.out)
        self.assertIsNone(boundary(self.out, ""), "the module end is quiet on the object the class end named: %s" % self.out)


class ImportTimeLeakIsInheritedOnce(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_E
    ERRORS = 2

    def test_the_first_test_to_meet_the_state_reports_it_as_inherited_after_its_body_ran(self):
        text = self.assertInherited("Cases", "test_a_does_nothing_and_is_the_first_to_meet_the_state")
        self.assertTrue(text.startswith("SdkBackend over "), text)
        self.assertIn("import-time code", text)
        self.assertIn("after that test's own teardown", text)

    def test_the_next_test_under_the_same_object_is_quiet(self):
        self.assertRatchetPassed("Cases", "test_b_does_nothing")

    def test_a_leak_of_its_own_is_still_named(self):
        text = self.assertRatchetFailed("Cases", "test_c_makes_a_kept_sandbox_leak_of_its_own")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_the_class_and_module_ends_are_quiet(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class ClassScopedRoot(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_K
    ERRORS = 1

    def test_the_lazy_build_over_the_class_root_passes_at_its_own_window(self):
        self.assertRatchetPassed("One", "test_a_the_lazy_build_over_the_class_root_passes_at_its_own_window")
        self.assertIsNone(verdict(self.out, "One", "test_b_does_nothing"), self.out)      # b's ERROR is the boundary's, below

    def test_the_class_that_moved_jd_state_and_kept_the_singleton_is_the_author(self):
        text = self.assertBoundaryFailed("::One", "One.test_b_does_nothing")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)
        _, fix = boundary(self.out, "::One")
        self.assertIn("setUpClass and tearDownClass when the class moves it", fix)

    def test_the_class_level_save_and_restore_is_quiet(self):
        self.assertRatchetPassed("Two", "test_a_builds_over_the_class_root")
        self.assertIsNone(boundary(self.out, "::Two"), self.out)
        self.assertIsNone(boundary(self.out, ""), "the module end is quiet on the object the class end named: %s" % self.out)


class ModuleTeardownRemovesTheDirectory(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_L
    ERRORS = 2

    def test_the_first_build_over_the_module_sandbox_fails_as_its_own(self):
        text = self.assertRatchetFailed("Cases", "test_a_builds_over_a_kept_sandbox_stored_on_the_module")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)

    def test_the_module_boundary_names_the_directory_its_teardown_removed(self):
        text = self.assertBoundaryFailed("", "Cases.test_b_does_nothing")
        self.assertTrue(text.startswith("over a directory it removed: SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), text)
        self.assertIsNone(boundary(self.out, "::Cases"), "the class end is quiet on the named object: %s" % self.out)


class FirstLoadInsideTheTest(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_H
    ERRORS = 1

    def test_the_first_load_then_a_build_over_a_kept_sandbox_is_named_by_what_it_left(self):
        text = self.assertRatchetFailed("Cases", "test_a_the_first_load_then_a_build_over_a_kept_sandbox_fails")
        self.assertTrue(text.startswith(REEXEC + " over a root that is not jd.STATE: SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class FirstLoadThenTheLazyBuild(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_H2
    ERRORS = 0

    def test_the_first_load_then_the_lazy_build_over_the_loaders_root_passes(self):
        self.assertRatchetPassed("Cases", "test_a_the_first_load_then_the_lazy_build_over_the_loaders_root_passes")
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class ValuesThatAreNotTheKernelsBuild(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_F
    ERRORS = 5

    def test_a_look_alike_over_jd_state_is_refused_by_the_class_check(self):
        text = self.assertObjectRoad("Cases", "test_a_a_look_alike_over_jd_state_as_the_workers_first_value_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after test_scratch.SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_none_left_in_place_of_the_look_alike_fails(self):
        text = self.assertObjectRoad("Cases", "test_b_none_left_in_place_of_the_look_alike_fails")
        self.assertTrue(text.startswith("changed after its teardown: before test_scratch.SdkBackend over "), text)
        self.assertTrue(text.endswith(", after None (not built)"), text)

    def test_the_kernels_unavailable_outcome_passes(self):
        self.assertRatchetPassed("Cases", "test_c_the_kernels_unavailable_outcome_passes")

    def test_none_left_in_place_of_false_fails(self):
        text = self.assertObjectRoad("Cases", "test_d_none_left_in_place_of_false_fails")
        self.assertTrue(text.startswith("changed after its teardown: before False"), text)
        self.assertTrue(text.endswith(", after None (not built)"), text)

    def test_the_real_lazy_build_over_the_run_root_passes(self):
        self.assertRatchetPassed("Cases", "test_e_the_real_lazy_build_over_the_run_root_passes")

    def test_false_left_in_place_of_the_backend_fails(self):
        text = self.assertObjectRoad("Cases", "test_f_false_left_in_place_of_the_backend_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertIn(", after False", text)

    def test_a_simplenamespace_left_fails_and_renders_module_qualified(self):
        text = self.assertObjectRoad("Cases", "test_g_a_simplenamespace_left_fails")
        self.assertTrue(text.endswith(", after types.SimpleNamespace over no state_dir"), text)

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class FirstBuildWithJdStateLeftAtTheSandbox(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_J
    ERRORS = 1
    JUDGE_RED = True

    def test_the_ratchet_judges_against_the_root_the_test_inherited_and_the_judge_names_the_state_leak(self):
        text = self.assertRatchetFailed("Cases", "test_a_the_first_build_over_a_sandbox_with_jd_state_left_there_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)
        self.assertIn(SHARED_STATE, self.out, "the judge fixture names the moved jd.STATE in the same teardown")
        self.assertIn("romp_judge.STATE changed from", self.out)
        self.assertRegex(self.out, r"errors while tearing down <TestCaseFunction test_a_\w+> \(2 sub-exceptions\)",
                         "pytest 9 renders the two teardown failures on the one item as one exception group")

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class BoundaryYieldsToTheTestsOwnWindows(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_N
    FOLLOWER = SCRATCH_N2
    ERRORS = 6

    def test_each_accused_test_is_named_once_on_the_object_road(self):
        for cls, method, after in (("Two", "test_a_leaves_none", ", after None (not built)"),
                                   ("Three", "test_a_leaves_none_as_the_last_test_of_a_class_that_started_on_a_real_backend",
                                    ", after None (not built)"),
                                   ("Four", "test_b_leaves_false_as_the_last_test", ", after False (the build failed)"),
                                   ("Follow", "test_a_leaves_none_as_the_last_test_of_the_module", ", after None (not built)")):
            text = self.assertObjectRoad(cls, method)
            self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
            self.assertTrue(text.endswith(after), text)
        text = self.assertObjectRoad("Five", "test_a_none_in_place_of_false")
        self.assertTrue(text.startswith("changed after its teardown: before False (the build failed), after None"), text)

    def test_the_allowed_rebuild_after_an_accused_reset_passes_alone(self):
        self.assertRatchetPassed("Two", "test_b_the_lazy_rebuild_over_the_run_root_after_the_accused_reset")
        self.assertRatchetPassed("Four", "test_a_the_lazy_rebuild")
        self.assertRatchetPassed("Five", "test_b_the_lazy_rebuild")

    def test_a_class_that_moves_jd_state_and_never_builds_is_quiet(self):
        # Sandboxed's test runs under an unnamed singleton whose state_dir is not jd.STATE, the picture the first-window
        # report names at the worker's first window only; here One.a's window made it, judged there, and nothing is said.
        self.assertRatchetPassed("Sandboxed", "test_a_does_nothing_under_a_singleton_over_the_run_root")
        self.assertIsNone(inherited(self.out, "Sandboxed", "test_a_does_nothing_under_a_singleton_over_the_run_root", head=INHERITED_KEPT))
        self.assertIsNone(boundary(self.out, "::Sandboxed"), self.out)

    def test_no_class_or_module_boundary_is_accused_of_what_its_tests_did(self):
        for scope in ("::One", "::Sandboxed", "::Two", "::Three", "::Four", "::Five", ""):
            self.assertIsNone(boundary(self.out, scope), "a boundary that did nothing is accused: %s" % self.out)
        self.assertIsNone(boundary(self.out, "::Follow", module="test_scratch2.py"), self.out)
        self.assertIsNone(boundary(self.out, "", module="test_scratch2.py"), self.out)
        self.assertEqual(self.out.count(BOUNDARY), 1, "the one boundary text in the run is Six's: %s" % self.out)
        self.assertNotIn("sub-exceptions", self.out, "no verdict folds into another's teardown report: %s" % self.out)

    def test_a_class_that_dropped_the_object_it_found_before_its_tests_rebuild_stays_the_author(self):
        # The first window inside Six started from None, not from the object Six found (Five.b's build), so the yield
        # does not apply and the class is named for the rebuild over the same root; the test itself passes alone.
        text = self.assertBoundaryFailed("::Six", "Six.test_a_the_lazy_rebuild_the_next_module_inherits", remedy=REMEDY_B)
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + REBUILT), text)
        self.assertIsNone(boundary(self.out, ""), "the module end is quiet on the object the class end named: %s" % self.out)


class ImportTimeLeakOverAKeptSandboxIsInheritedOnce(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_S6
    ERRORS = 1

    def test_the_first_window_reports_the_kept_root_as_inherited_beside_the_tests_own_verdict(self):
        text = self.assertInherited("Cases", "test_a_is_the_first_to_meet_the_state_and_leaks_on_its_own", head=INHERITED_KEPT, own=True)
        self.assertTrue(text.startswith("SdkBackend over "), text)
        self.assertIn(", jd.STATE ", text)
        self.assertIn("import-time code did", text)
        own = self.assertRatchetFailed("Cases", "test_a_is_the_first_to_meet_the_state_and_leaks_on_its_own")
        self.assertTrue(own.startswith("changed after its teardown: before SdkBackend over "), own)
        self.assertNotIn(GONE, own)

    def test_the_next_test_under_the_tests_own_object_is_quiet_and_the_ends_are_quiet(self):
        self.assertRatchetPassed("Cases", "test_b_does_nothing")
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class ClassTeardownInstallsAValue(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_M
    ERRORS = 3

    def test_a_teardown_that_builds_over_a_sandbox_is_named_at_the_class_boundary(self):
        text = self.assertBoundaryFailed("::Two", "Two.test_a_does_nothing")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertIn(", after SdkBackend over ", text)
        self.assertNotIn(GONE, text)
        self.assertNotIn(REBUILT, text, "another root, not a rebuild over the same one: %s" % text)

    def test_a_teardown_that_resets_the_slot_to_none_is_named_with_the_object_remedy(self):
        text = self.assertBoundaryFailed("::Three", "Three.test_a_does_nothing_under_twos_object", remedy=REMEDY_B)
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertTrue(text.endswith(", after None (not built)"), text)
        _, fix = boundary(self.out, "::Three")
        self.assertNotIn(SANDBOX, fix, fix)
        self.assertRatchetPassed("Four", "test_a_does_nothing_under_none")
        self.assertIsNone(boundary(self.out, "::Four"), "a class that inherits the None and does nothing is quiet: %s" % self.out)

    def test_a_teardown_that_builds_from_none_is_named_and_the_module_end_is_quiet_on_it(self):
        text = self.assertBoundaryFailed("::Five", "Five.test_a_does_nothing_under_none")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)
        self.assertRatchetPassed("Six", "test_a_does_nothing_under_fives_object")
        self.assertIsNone(boundary(self.out, "::Six"), self.out)
        self.assertIsNone(boundary(self.out, ""), "the module end is quiet on the object the class end named: %s" % self.out)


class ClassTeardownPutsBackAnObjectWhoseDirectoryItRemoved(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_P
    ERRORS = 2

    def test_the_leak_over_the_kept_sandbox_is_named_at_its_own_window(self):
        text = self.assertRatchetFailed("One", "test_a_leaks_over_a_kept_sandbox")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_the_put_back_of_the_found_object_over_a_removed_directory_is_named_at_the_class_boundary(self):
        # Two.a's lazy build over the root the class moved to passes at its own window; Two's one case is its last, so the
        # boundary verdict lands on it (PASSED for the call, ERROR at the teardown), and no test verdict names it.
        text = self.assertBoundaryFailed("::Two", "Two.test_a_builds_over_the_class_root")
        self.assertTrue(text.startswith(PUT_BACK_GONE + "SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), text)

    def test_the_class_that_inherits_the_gone_object_is_quiet(self):
        self.assertRatchetPassed("Three", "test_a_does_nothing_under_the_gone_object")
        self.assertIsNone(boundary(self.out, "::Three"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class ValuesOnTheOtherRoads(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_G
    ERRORS = 2

    def test_a_look_alike_claiming_the_kernels_module_is_refused_and_rendered_module_qualified(self):
        text = self.assertObjectRoad("Cases", "test_a_a_look_alike_claiming_the_kernels_module_as_the_workers_first_value_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after romp_sdk_backend.Fake over "), text)
        self.assertNotIn(GONE, text)

    def test_a_reexecution_that_leaves_a_value_that_is_not_the_kernels_build_is_named(self):
        text = self.assertObjectRoad("Cases", "test_b_a_reexecution_then_a_simplenamespace_left_fails")
        self.assertTrue(text.startswith(REEXEC + " as a value that is not the kernel's build: types.SimpleNamespace over "), text)
        self.assertNotIn("changed", text)

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class FirstBuildThenTheRunRootRemoved(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_R1
    ERRORS = 1
    JUDGE_RED = True

    def test_the_ratchet_names_the_gone_root_with_the_sandbox_remedy_beside_the_judges_verdict(self):
        text = self.assertRatchetFailed("Cases", "test_a_the_first_build_then_the_run_root_removed_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), "the allowance asks for a directory, and this one is gone: %s" % text)
        self.assertIn(SHARED_STATE, self.out, "the judge fixture names the removed root in the same teardown")
        self.assertIn("was a directory and is gone", self.out)
        self.assertRegex(self.out, r"errors while tearing down <TestCaseFunction test_a_\w+> \(2 sub-exceptions\)")

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class ReexecutionThenTheRunRootRemoved(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_R2
    ERRORS = 1
    JUDGE_RED = True

    def test_the_reload_road_names_the_gone_root_with_the_sandbox_remedy_beside_the_judges_verdict(self):
        text = self.assertRatchetFailed("Cases", "test_a_a_reexecution_the_lazy_build_then_the_run_root_removed_fails")
        self.assertTrue(text.startswith(REEXEC + " over jd.STATE, which is no longer a directory: SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), text)
        self.assertIn(SHARED_STATE, self.out)
        self.assertIn("is not a directory after the test reloaded the judge", self.out)

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


if __name__ == "__main__":
    unittest.main()
