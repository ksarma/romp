"""The link-drop lab's driver ends before CI ends the served process (2026-09-19).

CI's served job runs every served lab in ONE pytest process under pytest-timeout's per-test cap (600 s, thread method:
the process ends with a thread dump and no summary), and tests/test_federated_linkdrop_served.py drives its two kernels
and the browser in setUpClass. Round 2's review found the node driver's subprocess timeout at 900 s, above the cap, with
waits that alone summed past it: a drive degraded by one unmet precondition (a supervisor that never re-read the row up)
would have been ended by pytest-timeout inside setUpClass, taking every served lab collected after the module with it
and leaving no summary for the labs already run. The module now bounds the drive in three layers, pinned here without a
kernel or a browser:
- the arithmetic: the driver's worst case (its shared wait budget plus the bounded work between the waits) is under the
  subprocess timeout, which is under CI's cap with room for the rest of setUpClass, and the cap the constant is chosen
  against is the one the workflow's served step states;
- the bytes sent: _drive hands subprocess.run the timeout and writes the budget, the wait caps and the settle values
  into the driver's cfg from the class that drives (a stub class, the driver replaced by a spy), and the driver it writes
  opens with the budget and reads every one of those keys;
- the budget under node: BUDGET_JS, the driver's opening lines, run with a clock of its own: a wait that never comes
  spends the budget once and is recorded, every later wait returns at once, no timeout handed on is ever 0 (playwright
  reads 0 as no timeout), and a wait that comes spends only what it took.

Two more pins ride here because the module they pin has no kernel-free test of its own: LinkDropBothNew gates on no
knob and LinkDropOldLocal skips as optional (round 1's high, closed by a value; round 2 asked for the pin), and a hub a
knob asked for whose bundle cannot be made ready is an error through _boot, while this checkout's own bundle failing to
build stays a skip (round 1's tests-3, ruled twice).

Synthetic: no kernel, no browser; stub classes over scratch directories.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import test_federated_linkdrop_served as L   # noqa: E402  the lab module: the constants, BUDGET_JS, _drive

CFG_KEYS = ("driverBudgetMs", "pageWaitMs", "phaseSettleMs", "quietTries", "quietStepMs")   # plus waitsMs.<mark>, below
KNOBS = ("ROMP_LINKDROP_LAB", "ROMP_CORNER_OLD_HUB_ROOT", "ROMP_LINKDROP_OLD_HUB_BUILD", "ROMP_LINKDROP_HUB_ROOT")   # the lab's four


def _without_knobs():
    """The environment with the lab's four knobs unset, the rest kept (a bare clear=True would take PATH and HOME too)."""
    return mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k not in KNOBS}, clear=True)

BUDGET_HARNESS = r"""
const out = { timeouts: [] };
let clock = 0; const now = () => clock; const sleep = async (ms) => { clock += ms; };
const res = {};
const b = makeBudget({ budgetMs: 1000, now, sleep, out });
res.capBig = b.capped(5000);
res.capSmall = b.capped(300);
let polls = 0;
res.r1 = await b.waitFor(async () => { polls++; return false; }, 5000, "w1");
res.clock1 = clock; res.polls1 = polls; res.timeouts1 = out.timeouts.slice(); res.left1 = b.left();
const c = clock;
res.r2 = await b.waitFor(async () => false, 5000, "w2");
res.spent2 = clock - c; res.timeouts2 = out.timeouts.slice(); res.capSpent = b.capped(5000);
const out2 = { timeouts: [] }; clock = 0; let n = 0;
const b2 = makeBudget({ budgetMs: 1000, now, sleep, out: out2 });
res.r3 = await b2.waitFor(async () => ++n >= 3, 5000, "w3");
res.clock3 = clock; res.left3 = b2.left(); res.timeouts3 = out2.timeouts;
console.log("RESULT:" + JSON.stringify(res));
"""


class TheDriverEndsBeforeCI(unittest.TestCase):
    maxDiff = None

    def _served_step_line(self):
        with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as f:
            ci = f.read()
        served = [ln for ln in ci.splitlines() if "tests/test_*_served.py" in ln and "pytest" in ln]
        self.assertEqual(len(served), 1, "the served step's one pytest line: %r" % (served,))
        return served[0]

    def test_the_arithmetic_and_the_cap_it_is_chosen_against(self):
        for cls in (L.LinkDropBothNew, L.LinkDropOldLocal):
            worst = L.driver_worst_case_s(cls)
            self.assertGreater(worst, cls.driver_budget_ms / 1000.0 + L.hub_restart_bound_s(),
                               "the worst case counts more than the budget and the restart (the bundles, the dwell, the settles): %r" % (worst,))
            self.assertLess(worst, L.DRIVER_TIMEOUT_S, "%s's driver at its worst (%.1f s) ends before its subprocess timeout (%d s)" % (cls.__name__, worst, L.DRIVER_TIMEOUT_S))
        self.assertLessEqual(L.DRIVER_TIMEOUT_S + L.BOOT_ROOM_S, L.CI_TEST_TIMEOUT_S,
                             "the subprocess timeout leaves BOOT_ROOM_S of CI's per-test cap for the rest of setUpClass")
        served = self._served_step_line()
        self.assertIn("--timeout=%d --timeout-method=thread" % L.CI_TEST_TIMEOUT_S, served,
                      "CI_TEST_TIMEOUT_S is the cap the served step runs under: %r" % (served,))

    def test_the_new_bundle_class_gates_on_no_knob_and_the_old_hub_class_skips_as_optional(self):
        """Round 1's high (this lab was the one served lab of 94 with no executing test in CI: its base class gated on a knob)
        was closed by a value, _LinkDrop._knobs returning None. The property, pinned (round 2, extra6-1): with the four knobs
        unset, LinkDropBothNew's _knobs returns, and LinkDropOldLocal's raises a SkipTest whose reason starts with "optional:"
        and names its knob. The first call is wrapped so a regression fails the pin instead of skipping it; throwaway
        subclasses, so nothing _knobs assigns reaches the real classes. And the served step runs with -rs, so an optional
        skip prints its reason in CI's log rather than folding into a count."""
        class New(L.LinkDropBothNew):
            pass

        class Old(L.LinkDropOldLocal):
            pass
        with _without_knobs():
            try:
                New._knobs()
            except unittest.SkipTest as e:
                self.fail("LinkDropBothNew._knobs raised SkipTest with the four knobs unset, so the lab would collect in CI's served job with no executing test: %s" % e)
            with self.assertRaises(unittest.SkipTest) as cm:
                Old._knobs()
        reason = str(cm.exception)
        self.assertTrue(reason.startswith("optional:"), "the old-hub class's skip is optional (the CI census reads the prefix): %r" % (reason,))
        self.assertIn("ROMP_LINKDROP_LAB", reason, "…and names the knob that runs it")
        self.assertIn(" -rs ", self._served_step_line(), "CI's served step prints skip reasons (-rs), so the optional skip is visible there")

    def _boot_stub(self, base, **attrs):
        """A class over a scratch lab that _boot runs to its build statement without node deps or a browser: L.EXT repointed
        at a scratch with a playwright package directory, the node probe answered by the spy with a path that exists, every
        other subprocess a failure of the test (the kernels are never reached), the remote's routes read from this checkout's
        kernel. Returns the class; the caller cleans its lab."""
        scratch = tempfile.mkdtemp(prefix="linkdrop-boot-")
        self.addCleanup(shutil.rmtree, scratch, True)
        os.makedirs(os.path.join(scratch, "node_modules", "playwright"))
        self.addCleanup(setattr, L, "EXT", L.EXT)
        L.EXT = scratch

        class Boot(base):
            pass
        Boot.procs, Boot.proxy, Boot.ctl = [], None, None
        for k, v in attrs.items():
            setattr(Boot, k, v)
        test = self

        def probe_only(cmd, *a, **kw):
            if cmd[:2] == ["node", "-e"]:
                return subprocess.CompletedProcess(cmd, 0, stdout=scratch + "\n", stderr="")
            test.fail("_boot ran a subprocess past the build statement: %r" % (cmd,))
        p = mock.patch.object(L.subprocess, "run", probe_only)
        p.start()
        self.addCleanup(p.stop)
        return Boot

    def _boot_expecting_error(self, Boot):
        """_boot's outcome as one of three: a RuntimeError (returned), a SkipTest (a failure of the pin, never a skip), a return."""
        try:
            Boot._boot()
        except RuntimeError as e:
            return e
        except unittest.SkipTest as e:
            self.fail("a build the runner asked for skipped instead of erring (the class would skip and the run report green): %s" % e)
        finally:
            shutil.rmtree(getattr(Boot, "lab", "") or "", ignore_errors=True)
        self.fail("_boot returned without building")

    def test_a_hub_a_knob_asked_for_errs_when_its_bundle_cannot_be_made_ready_and_this_checkouts_stays_a_skip(self):
        """Round 1's tests-3, through _boot with a stub build: the mint knob with a build that skips (lab_dist's esbuild
        failure) is a RuntimeError carrying the knob and the build's words; a knob-named root with no prebuilt dist is the
        same, under the old-hub class's own knob and under the base-hub lever; and with no knob this checkout's own bundle
        failing to build stays a SkipTest, as in every other served lab."""
        words = "esbuild failed here: the stub build"

        class StubBuild:
            def __init__(self, ext, root):
                self.ext, self.root = ext, root

            def copy_to(self, dest):
                raise unittest.SkipTest(words)
        # the mint knob: a mint that succeeds (stubbed: the checkout's kernel and extension directory appear) and a build that skips
        def mint(cls):
            wt = os.path.join(cls.lab, "oldhub")
            os.makedirs(os.path.dirname(os.path.join(wt, L.KERNEL_BIN)))   # the kernel entry point _boot requires, by the module's own name for it
            os.makedirs(os.path.join(wt, "vscode-extension"))
            with open(os.path.join(wt, L.KERNEL_BIN), "w") as f:
                f.write("#!/bin/sh\n")
            cls.old_hub_wt = wt
            return wt
        with _without_knobs(), mock.patch.dict(os.environ, {"ROMP_LINKDROP_LAB": "1", "ROMP_LINKDROP_OLD_HUB_BUILD": "1"}), mock.patch.object(L.lab_dist, "DistBuild", StubBuild):
            Boot = self._boot_stub(L.LinkDropOldLocal, _mint_old_hub=classmethod(mint))
            e = self._boot_expecting_error(Boot)
        self.assertIn("ROMP_LINKDROP_OLD_HUB_BUILD=1", str(e), "the error names the knob that asked: %s" % e)
        self.assertIn(words, str(e), "…and carries the build's words: %s" % e)
        self.assertTrue(Boot.old_hub_wt and Boot.old_hub_wt in str(e), "…and the minted checkout: %s" % e)
        # a knob-named root with a kernel and no prebuilt dist, under the old-hub class's knob and under the base-hub lever
        for base, knob, env in ((L.LinkDropOldLocal, "ROMP_CORNER_OLD_HUB_ROOT", {"ROMP_LINKDROP_LAB": "1"}), (L.LinkDropBothNew, "ROMP_LINKDROP_HUB_ROOT", {})):
            root = tempfile.mkdtemp(prefix="linkdrop-hubroot-")
            self.addCleanup(shutil.rmtree, root, True)
            os.makedirs(os.path.dirname(os.path.join(root, L.KERNEL_BIN)))
            with open(os.path.join(root, L.KERNEL_BIN), "w") as f:
                f.write("#!/bin/sh\n")
            with _without_knobs(), mock.patch.dict(os.environ, dict(env, **{knob: root})):
                Boot = self._boot_stub(base)
                e = self._boot_expecting_error(Boot)
            self.assertEqual(Boot.hub_knob, knob, "the knob that named the hub is recorded")
            self.assertIn(knob, str(e), "the error names the knob that asked: %s" % e)
            self.assertIn("no prebuilt dist under %s" % root, str(e), "…and says what was missing: %s" % e)
        # no knob: this checkout's own bundle, whose failed build stays a skip
        def skip_dist(dest):
            raise unittest.SkipTest(words)
        with _without_knobs(), mock.patch.object(L.lab_dist, "copy_dist", skip_dist):
            Boot = self._boot_stub(L.LinkDropBothNew)
            try:
                with self.assertRaises(unittest.SkipTest) as cm:
                    Boot._boot()
            finally:
                shutil.rmtree(getattr(Boot, "lab", "") or "", ignore_errors=True)
        self.assertEqual(str(cm.exception), words, "the unknobbed arm's skip is lab_dist's own, unwrapped")
        self.assertIsNone(Boot.hub_knob)

    def test_drive_sends_the_timeout_the_budget_and_the_caps(self):
        lab = tempfile.mkdtemp(prefix="linkdrop-bound-")
        self.addCleanup(shutil.rmtree, lab, True)

        class Drive(L._LinkDrop):
            # values of the stub's own, so the cfg is read from the class that drives and not from the base's defaults
            driver_budget_ms = 123456
            page_wait_ms = 7777
            waits_ms = {k: v + 1000 for k, v in L._LinkDrop.waits_ms.items()}
        Drive.lab, Drive.hport, Drive.htoken, Drive.ctl = lab, 1, "testtok-bound", types.SimpleNamespace(port=2)
        Drive.result, Drive.driver_error = None, None
        seen = {}

        def spy(cmd, *a, **kw):
            seen["cmd"], seen["kw"] = list(cmd), kw
            return subprocess.CompletedProcess(cmd, 0, stdout='RESULT:{"marks": {}}\n', stderr="")
        with mock.patch.object(L.subprocess, "run", spy):
            Drive._drive()
        self.assertEqual(seen["cmd"][:1], ["node"], seen)
        self.assertEqual(seen["kw"].get("timeout"), L.DRIVER_TIMEOUT_S, "the driver's subprocess timeout is DRIVER_TIMEOUT_S")
        self.assertEqual(Drive.result, {"marks": {}}, "the spy's result was read")
        with open(os.path.join(lab, "cfg.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["driverBudgetMs"], Drive.driver_budget_ms)
        self.assertEqual(cfg["waitsMs"], Drive.waits_ms)
        self.assertEqual(cfg["pageWaitMs"], Drive.page_wait_ms)
        self.assertEqual((cfg["phaseSettleMs"], cfg["quietTries"], cfg["quietStepMs"]), (L.PHASE_SETTLE_MS, L.QUIET_TRIES, L.QUIET_STEP_MS))
        with open(seen["cmd"][1], encoding="utf-8") as f:
            driver = f.read()
        self.assertTrue(driver.startswith(L.BUDGET_JS), "the driver the class writes opens with BUDGET_JS")
        unread = [k for k in CFG_KEYS if "cfg.%s" % k not in driver] + ["waitsMs.%s" % k for k in Drive.waits_ms if "cfg.waitsMs.%s" % k not in driver]
        self.assertEqual(unread, [], "every value the cfg carries is read by the driver by name: %r" % (unread,))
        self.assertEqual(set(Drive.waits_ms), set(re.findall(r"cfg\.waitsMs\.(\w+)", driver)), "…and the driver reads no cap the class does not send")

    def test_the_budget_binds_every_wait_under_node(self):
        if not shutil.which("node"):
            raise unittest.SkipTest("node absent: the budget's node run needs it")
        d = tempfile.mkdtemp(prefix="linkdrop-budget-")
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "budget.mjs")
        with open(path, "w", encoding="utf-8") as f:
            f.write(L.BUDGET_JS + BUDGET_HARNESS)
        p = subprocess.run(["node", path], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, "the budget ran under node: %s%s" % (p.stdout[-800:], p.stderr[-800:]))
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, p.stdout)
        res = json.loads(line[len("RESULT:"):])
        spent = " (the driver's wait budget was spent)"
        self.assertEqual((res["capBig"], res["capSmall"]), (1000, 300), "the budget caps a larger timeout and leaves a smaller one: %r" % (res,))
        self.assertEqual((res["r1"], res["clock1"], res["polls1"], res["left1"]), (False, 1000, 4, 0),
                         "a wait that never comes polls every 250 ms, spends the budget once and no more: %r" % (res,))
        self.assertEqual(res["timeouts1"], ["w1" + spent], "…and is recorded as expired with the budget spent: %r" % (res,))
        self.assertEqual((res["r2"], res["spent2"], res["capSpent"]), (False, 1, 1),
                         "with the budget spent the next wait returns at once and no timeout handed on is 0: %r" % (res,))
        self.assertEqual(res["timeouts2"], ["w1" + spent, "w2" + spent])
        self.assertEqual((res["r3"], res["clock3"], res["left3"], res["timeouts3"]), (True, 500, 500, []),
                         "a wait that comes on its third poll spends only what it took and records nothing: %r" % (res,))


if __name__ == "__main__":
    unittest.main()
