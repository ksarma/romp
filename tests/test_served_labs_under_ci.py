"""Every served lab runs in CI's served job (2026-09-15).

CI's browser-backed step (.github/workflows/ci.yml, "Browser-backed served-page tests") runs ONLY the files its pytest
line names, the two globs tests/test_*_browser.py and tests/test_*_served.py and one module named by file (the handler-parse
leg's test below), under ROMP_SERVED_TESTS_REQUIRE=1; tests/conftest.py turns a skip in the files the globs collect into a
failure (_is_served_test_file, the same two suffixes). A lab whose name misses
both suffixes therefore skips on the Python matrix runners (no node deps, no browser), never runs in the served job,
and its skip stays a skip: eleven labs stood outside the globs on 2026-09-15, and one of them
(the ship-reship lab, since renamed with the suffix; its NackNoticeSurvivesReload class) hid a real regression on main
for a day.

The pin lists the served labs by CONTENT, from the tree, and checks the names against both name rules:
  a served lab is a test module under tests/ that names playwright (a browser drives it) and either boots the hermetic
  kernel (the romp-kernel module), imports the lab kernel's environment (the ship-reship module), or hands the extension
  package to a node driver (EXT_PKG). tests/test_served_tests_require.py names playwright too, in prose, and does none of
  the three: it drives pytest itself on synthetic files, and stands here as the named control.
  This pin names every marker in its own source and reads the tree only, so it leaves itself out by file name.
Every lab must (1) satisfy the conftest's own predicate, (2) match a glob the CI step's pytest line names, read from the
workflow file, and (3) the CI globs must be the conftest's two suffixes, so the two name rules cannot drift apart.

Synthetic: reads the tree only; no kernel, no browser.
"""
import fnmatch
import glob
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CI_YML = os.path.join(ROOT, ".github", "workflows", "ci.yml")
CONTROL = "test_served_tests_require.py"
CONFTEST = os.path.join(HERE, "conftest.py")
CORNERS = os.path.join(HERE, "test_federated_capability_corners_served.py")
# the shared browser-legs step and its roster, by the names the shared change fixed (the reviewer's ruling of 2026-09-21: the step
# that runs browser legs after the Chromium install lands once, as its own change, and each PR adds its leg's roster line)
BROWSER_LEGS_STEP = "Browser legs (node --test over ci-browser-legs.txt)"
# the gating job the step sits in, after that job's Chromium install
BROWSER_LEGS_JOB = "vscode-extension"
# a job's key line under jobs: two spaces, a bare key and a colon (the workflow's own spelling of every job key)
JOB_KEY_LINE = re.compile(r"  ([A-Za-z0-9_-]+):\s*(#.*)?")
ROSTER = os.path.join(ROOT, "vscode-extension", "ci-browser-legs.txt")
GEAR_LEG = "out-tests/ui/webview/gear-sub-focus-browser.test.js"
GEAR_SRC = os.path.join(ROOT, "ui", "webview", "gear-sub-focus-browser.test.ts")


def conftest_module():
    """tests/conftest.py as pytest itself loaded it (its name in the module table is pytest's to choose), so the
    predicate checked is the one the runs use, never a second copy of a module with import-time effects."""
    for m in list(sys.modules.values()):
        if os.path.realpath(getattr(m, "__file__", None) or "") == os.path.realpath(CONFTEST):
            return m
    raise AssertionError("tests/conftest.py is not loaded: run this pin under pytest")


def is_served_lab(text: str) -> bool:
    """A browser drives it, and it boots the hermetic kernel, imports the lab kernel's environment, or hands the
    extension package to a node driver."""
    drives = "playwright" in text
    boots = ("romp-kernel" in text) or ("import test_ship_reship" in text) or ("EXT_PKG" in text)
    return drives and boots


def served_labs():
    out = []
    for path in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
        if os.path.basename(path) == os.path.basename(__file__):
            continue   # this pin names every marker in its own text; it is a census, not a lab
        with open(path, encoding="utf-8") as f:
            if is_served_lab(f.read()):
                out.append(os.path.basename(path))
    return out


def ci_served_step():
    """The served step as the workflow file states it, read by text (the runner installs no YAML reader): its env block (the
    one setting ROMP_SERVED_TESTS_REQUIRE to 1) as {name: value} and its pytest line's arguments; None when the step's
    anchors are gone, so a caller fails on nothing rather than passing on nothing."""
    with open(CI_YML, encoding="utf-8") as f:
        lines = f.read().split("\n")
    at = [i for i, l in enumerate(lines) if 'ROMP_SERVED_TESTS_REQUIRE: "1"' in l]
    if len(at) != 1:
        return None
    i = at[0]
    j = i
    while j >= 0 and lines[j].strip() != "env:":
        j -= 1
    k = i
    while k < len(lines) and "python -m pytest" not in lines[k]:
        k += 1
    if j < 0 or k >= len(lines):
        return None
    env = {}
    for l in lines[j + 1:k]:
        if l.strip().startswith("run:"):
            break
        m = re.match(r'\s+([A-Z_]+): "?([^"#]*?)"?\s*(#.*)?$', l)
        if m:
            env[m.group(1)] = m.group(2)
    return {"env": env, "pytest": lines[k].split("python -m pytest", 1)[1].split()}


def ci_served_globs():
    """The file globs on the served step's pytest line: the step that sets ROMP_SERVED_TESTS_REQUIRE to 1."""
    step = ci_served_step()
    if step is None:
        raise AssertionError("ci.yml has no pytest line after ROMP_SERVED_TESTS_REQUIRE: \"1\"")
    return [tok for tok in step["pytest"] if tok.startswith("tests/") and "*" in tok]


def ci_served_files():
    """The test modules the served step names by file, beside its globs."""
    step = ci_served_step()
    if step is None:
        raise AssertionError("ci.yml has no pytest line after ROMP_SERVED_TESTS_REQUIRE: \"1\"")
    return [tok for tok in step["pytest"] if tok.startswith("tests/") and "*" not in tok]


def ci_steps():
    """Every step of the workflow file in order, read by text (the runner installs no YAML reader): its name, the job it sits in
    and its lines up to the next step's name line or the next job's key line, whichever comes first. The job is the key of the
    nearest job key line above the step (JOB_KEY_LINE, below the one top-level `jobs:` line); a step above every job key, or a
    file without exactly one `jobs:` line, has the job None, so a caller that asks for a job fails on it."""
    with open(CI_YML, encoding="utf-8") as f:
        lines = f.read().split("\n")
    top = [i for i, l in enumerate(lines) if re.match(r"jobs:\s*(#.*)?$", l)]
    keys = [(i, JOB_KEY_LINE.fullmatch(l).group(1)) for i, l in enumerate(lines)
            if len(top) == 1 and i > top[0] and JOB_KEY_LINE.fullmatch(l)]
    starts = [(i, l.split("- name:", 1)[1].strip()) for i, l in enumerate(lines) if re.match(r"\s+- name: ", l)]
    steps = []
    for k, (i, name) in enumerate(starts):
        end = min([starts[k + 1][0] if k + 1 < len(starts) else len(lines)] + [j for j, _ in keys if j > i])
        above = [key for j, key in keys if j < i]
        steps.append({"name": name, "job": above[-1] if above else None, "lines": lines[i:end]})
    return steps


def ci_browser_legs_step():
    """The shared browser-legs step's place, by the exact name the shared change fixed, as indexes over ci_steps()'s order: the
    steps of that name anywhere in the file (a list, so a missing or a doubled step shows), and the steps of BROWSER_LEGS_JOB whose
    lines install playwright's Chromium. The install count is that job's own: the served-pages job installs Chromium for its labs
    too (fork PR 928 moved the served step there, 2026-09-28), and the browser legs run after the gating job's install."""
    steps = ci_steps()
    return {"steps": steps,
            "named": [k for k, s in enumerate(steps) if s["name"] == BROWSER_LEGS_STEP],
            "install": [k for k, s in enumerate(steps) if s["job"] == BROWSER_LEGS_JOB
                        and any("npx playwright install chromium" in l for l in s["lines"])]}


def roster_lines(path):
    """The compiled bundle paths the roster lists, one per line, blank lines and # lines ignored (the format the roster's header
    states). None when the file does not exist, so a caller tells absent from empty."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        raw = f.read().split("\n")
    return [line.strip() for line in raw if line.strip() and not line.strip().startswith("#")]


def two_host_lab_knob():
    """The env name TwoHostsBytesByHost's gate reads, derived from the corners module's source (the class body, up to the next
    class), so a renamed knob moves this pin with it instead of leaving the workflow's env stale and the pin green; None when the
    class or its one `os.environ.get("ROMP_CORNER_...")` gate is not found, and a caller fails on None."""
    with open(CORNERS, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"^class TwoHostsBytesByHost\b.*?(?=^class |\Z)", src, re.S | re.M)
    if not m:
        return None
    gates = re.findall(r'os\.environ\.get\("(ROMP_CORNER_[A-Z0-9_]+)"\)', m.group(0))
    return gates[0] if len(gates) == 1 else None


class _Item:
    """The shape conftest._is_served_test_file reads: an item with a path."""

    def __init__(self, name):
        self.path = os.path.join(HERE, name)
        self.fspath = self.path


class ServedLabsUnderCI(unittest.TestCase):
    def test_the_census_finds_labs_and_excludes_the_control(self):
        labs = served_labs()
        self.assertGreater(len(labs), 50, labs)
        self.assertNotIn(CONTROL, labs, "the require-road pin drives pytest, not a browser")
        self.assertTrue(os.path.exists(os.path.join(HERE, CONTROL)), "the control file is gone; name another")

    def test_every_served_lab_satisfies_the_conftest_predicate(self):
        missed = [n for n in served_labs() if not conftest_module()._is_served_test_file(_Item(n))]
        self.assertEqual(missed, [], "served labs outside the conftest's _browser/_served name rule (their skips stay "
                                     "skips and CI never runs them): %s" % missed)

    def test_every_served_lab_matches_a_glob_the_ci_step_runs(self):
        globs = ci_served_globs()
        self.assertTrue(globs, "the served step's pytest line names no tests/ globs")
        missed = [n for n in served_labs() if not any(fnmatch.fnmatch("tests/" + n, g) for g in globs)]
        self.assertEqual(missed, [], "served labs no CI glob %s runs: %s" % (globs, missed))

    def test_the_handler_parse_leg_is_named_on_the_served_step_by_file(self):
        """tests/test_relay_dial_declares_held_pair.py drives one hermetic kernel over a raw socket and needs the extension's
        built dist (lab_dist), which the Python matrix runners never have, so there it skips; no browser drives it, so the
        census above leaves it out and no glob names it, and it ran in no CI job (the maintainer's round 1 of the wsBytesByHost
        change, 2026-09-20). The served step names it by file: the one job with the deps runs its executed part (the first
        dials and their wsopen rows). The conftest's REQUIRE rule reads file names and this module carries no served suffix
        on purpose (the precedent is tests/test_session_host_restart.py, whose docstring records the same decision), so the
        module holds its own preconditions under the switch: a skip from lab_dist.copy_dist or the kernel boot is a failure
        there (its PreconditionSkipsUnderRequire drives that), and only the gen-key skip stays a plain skip: `optional:` is a
        runner-declared capability gap, and a kernel vintage that stamps no gen is a condition every runner shares."""
        files = ci_served_files()
        self.assertIn("tests/test_relay_dial_declares_held_pair.py", files, "the served step no longer names the handler-parse leg")
        for f in files:
            self.assertTrue(os.path.exists(os.path.join(ROOT, f)), "the served step names a module that is gone: %s" % f)
            self.assertFalse(conftest_module()._is_served_test_file(_Item(os.path.basename(f))),
                             "%s matches a served glob already; naming it by file is redundant" % f)

    def test_the_two_host_lab_runs_on_the_served_step(self):
        """TwoHostsBytesByHost (tests/test_federated_capability_corners_served.py) is the one end-to-end lab of the
        wsBytesByHost field, gated by ROMP_CORNER_TWO_HOSTS with an `optional:` skip so a contributor clone and the Python
        matrix runners leave it alone. The served step, which has the three kernels' deps and the browser, sets the knob
        (the maintainer's round 1, regression-2, 2026-09-20), so the lab runs there and a miss is a failure under REQUIRE, as its other skips are."""
        step = ci_served_step()
        self.assertIsNotNone(step, "ci.yml has no served step: re-aim ci_served_step()")
        self.assertEqual(step["env"].get("ROMP_SERVED_TESTS_REQUIRE"), "1")
        # the knob is derived from the lab's own gate, so a renamed knob fails here instead of leaving the workflow's env stale
        # while the lab skips as optional: in CI (the maintainer's round 1 of the same review)
        knob = two_host_lab_knob()
        self.assertIsNotNone(knob, "the corners module's TwoHostsBytesByHost gate was not found: re-aim two_host_lab_knob()")
        self.assertTrue((step["env"].get(knob) or "").strip(),
                        "the served step does not set the two-host lab's knob %s (the gate reads any non-blank value): %r" % (knob, step["env"]))

    def test_the_gear_browser_legs_are_rostered_in_the_step_after_the_browser_install(self):
        """ui/webview/gear-sub-focus-browser.test.ts holds the source pins and the browser legs of the description-on-focus work
        (the wsBytesByHost review). The Test step runs it before the job installs Chromium, so there its browser legs skip and the
        gate's read is the pins alone (the maintainer's round 5, tests-1); the browser legs run in a job with a browser only
        through the shared browser-legs step, which the reviewer's ruling of 2026-09-21 landed once as its own change, each PR
        adding its leg's line to the roster. Rostering is opt-in: nothing checks that every browser leg is rostered (the roster's
        header says so), so this pin is what holds this leg's line. It requires the step named BROWSER_LEGS_STEP once in the file,
        in the vscode-extension job (BROWSER_LEGS_JOB), directly after that job's one Chromium install step (before it every leg
        skips, or fails under the switch; the served-pages job's own install, for its labs, is outside the count), the roster
        vscode-extension/ci-browser-legs.txt, and the leg's bundle listed in it exactly once; a missing step, roster or line is a
        refusal naming what is missing. The leg launches through the shared helper, where the switch is read, and holds no private
        launch and no switch read of its own."""
        step = ci_browser_legs_step()
        roster = roster_lines(ROSTER)
        self.assertEqual(len(step["named"]), 1, "ci.yml holds %d steps named %r; one, the step that reads the roster (a renamed step moves "
                                                "this pin's name with it)" % (len(step["named"]), BROWSER_LEGS_STEP))
        self.assertIsNotNone(roster, "vscode-extension/ci-browser-legs.txt does not exist: the step %r reads the roster, so a step without "
                                     "one runs nothing" % BROWSER_LEGS_STEP)
        k = step["named"][0]
        self.assertEqual(step["steps"][k]["job"], BROWSER_LEGS_JOB, "the step %r sits in the %r job, the gating job whose Chromium "
                                                                    "install it follows; ci.yml has it in %r"
                         % (BROWSER_LEGS_STEP, BROWSER_LEGS_JOB, step["steps"][k]["job"]))
        self.assertEqual(len(step["install"]), 1, "the %s job holds %d steps installing playwright's Chromium; the pin places the "
                                                  "browser-legs step after the one (the served-pages job's own install is outside "
                                                  "this count)" % (BROWSER_LEGS_JOB, len(step["install"])))
        i = step["install"][0]
        after = step["steps"][i + 1]["name"] if i + 1 < len(step["steps"]) else None
        self.assertEqual(k, i + 1, "the browser-legs step sits directly after the %s job's Chromium install step (before it every leg "
                                   "skips, or fails under the switch); the step after the install is %r" % (BROWSER_LEGS_JOB, after))
        count = roster.count(GEAR_LEG)
        self.assertEqual(count, 1, "%s is listed %d times in ci-browser-legs.txt; the roster lists the leg once (the step runs each line "
                                   "once; a missing line leaves the leg's browser legs in no CI job with a browser: add it, with the "
                                   "leg's measured whole-file seconds in the PR body, as the roster's header asks)" % (GEAR_LEG, count))
        # the launch is the shared helper's, where the switch is read
        with open(GEAR_SRC, encoding="utf-8") as f:
            src = f.read()
        self.assertRegex(src, r'import \{[^}]*\binBrowser\b[^}]*\} from "\./real-viewer-leg"',
                         "the leg launches through the shared helper (real-viewer-leg.ts inBrowser), which reads the switch")
        self.assertIsNone(re.search(r"\.chromium\.launch\(", src), "the leg holds no private launch (a copy would read no switch)")
        self.assertIsNone(re.search(r"process\.env\.\w*REQUIRE", src), "the leg holds no switch read of its own: the shared helper's is the one read")

    def test_the_ci_globs_are_the_conftest_suffixes(self):
        self.assertEqual(sorted(ci_served_globs()), ["tests/test_*_browser.py", "tests/test_*_served.py"])
        self.assertTrue(conftest_module()._is_served_test_file(_Item("test_x_browser.py")))
        self.assertTrue(conftest_module()._is_served_test_file(_Item("test_x_served.py")))
        self.assertFalse(conftest_module()._is_served_test_file(_Item("test_x.py")))


if __name__ == "__main__":
    unittest.main()
