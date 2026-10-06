#!/usr/bin/env python3
"""CI's shards (.github/workflows/ci.yml, 2026-10-04): each Linux Python cell runs as SHARD_COUNT one-worker jobs, each
over its own share of the test files, since one worker running the whole suite does not fit the private runner's 8 GB
(tests/conftest.py's CI's shards section has the measurement, the rule and the hook).

Two kinds of pin:
1. The census (ShardsPartitionTheCollectedFiles): the shards partition the collected test files, each file in one
   shard, none in two, none left out, and each shard is the rule's. It asks pytest itself, in child runs from the
   repository root with the Run pytest step's selection: once with no shard (the collected files) and once for each
   shard, with SHARD_ENV (ROMP_TESTS_SHARD) set to it, as the step sets it. Each child loads tests/ci_shard_probe.py,
   which lists each file pytest decides to make a test module of without importing it (a real collection of this
   suite took 696 s and more than 5 GB on 2026-10-04); every step before that one, tests/conftest.py's
   pytest_ignore_collect among them, runs as in CI. Red under a selection that drops a file from every shard, that
   puts a file in two shards, or that is absent (every shard collects every file), and when a module tests/conftest.py's
   HEAVY_MODULES lists (the weighted rule's short list) runs anywhere but its listed shard. TheRule holds the list in
   process: each entry an existing test file, at most one to a shard, and every other path placed by the hash.
   The census runs in CI's form too (round 1 of fork PR 986, 2026-10-06), since a collect-only run with no -n never
   reaches tests/conftest.py's handling of the variable in an xdist controller. ShardsRunInCIsForms runs each shard's
   probe items, under -n 1 (an xdist controller and one worker, the Linux cells' form) and with no -n, and holds the
   files whose item passed to that shard's collected files; each item asserts the variable is absent from its
   process's environment. TheShardEnvironmentInCIsForm runs synthetic test files in a temporary directory outside the
   checkout under -n 1 and -n 0, and under two forms outside CI's that run in process, --dist load with no workers and
   --tx popen with no dist mode, and holds that only the named shard's files run and that neither a test nor a process
   it starts sees the variable. Both classes are red when the controller removes the variable before its worker starts
   (the worker then runs every file) and when a process that runs tests keeps it; the two forms outside CI's are red
   when the conftest tells a controller by xdist's dist option alone (--dist load) or by its tx list alone (--tx
   popen), where xdist's own test needs both. The legs that pass xdist's options skip where pytest-xdist is not
   installed; the form with no -n runs on any interpreter. BothSidesReadOneEnvironment holds that the collect-only run
   and the run of the probe's items read one environment, and that ShardsRunInCIsForms's file-set message names the
   xdist controller only for the -n 1 form (round 2 of fork PR 986's review). AValueThatNamesNoShard runs the census's
   child with values that name no shard: each ends in pytest's usage error, naming the variable and the value, with no
   file collected.
2. Source pins over ci.yml, read by line shape with no YAML library, as tests/test_ci_workflow_concurrency.py reads it
   (ShardMatrix): the python job's shard axis lists 1 to SHARD_COUNT; a batch push runs each interpreter as
   SHARD_COUNT Linux jobs, one per shard, and a dispatch with its macos input on (tests/test_ci_macos_input.py) adds one
   macOS job per macOS interpreter, unsharded; the Run
   pytest step hands each Linux cell its shard and each macOS cell an empty value; and each cell's job name differs.
   Each shard's cap is tests/test_ci_bats_bound.py's (PythonJobCeiling).
3. The shape switch (ShapeSwitch, 2026-10-06): three lines of ci.yml choose the python job's shape, the on: block's
   two schedule lines, its schedule: key and its one cron entry (both commented under full, both live under smaller),
   and the 'full' or 'smaller' literal that opens the python job's python-version expression
   (tests/test_ci_workflow_concurrency.py's shape_lines, shape_of and with_shape). The pins read the three lines, each
   exactly once, the two schedule lines as one unit, and refuse every half-flip, any one or two of the three lines
   switched without the rest (the schedule lines live under full, the literal smaller with the schedule commented, one
   schedule line live without the other); hold that switching is a change of exactly those three lines; and, for EACH
   shape, build the python job's cells for a batch push, a pull request (not a trigger; the expression's default), the
   schedule and a manual dispatch with its macos input off and on, and hold them: under full, all five interpreters on
   Linux for every run and no scheduled run (no schedule trigger); under smaller, 3.12 and 3.14t on a batch push and a
   pull request, 3.10, 3.11 and 3.13 on the weekly schedule, Linux alone, and all five on a dispatch; the macOS cells,
   3.10 and 3.13 unsharded, on a dispatch with macos on alone, in both. Every interpreter runs on a batch push or on the
   schedule, and none on both. Red at the commit before the switch, whose python-version axis was a flow list with no
   shape literal.
4. Prose that holds in both shapes (ProseHoldsInBothShapes, 2026-10-06): switching the shape is a three-line change, so
   no other tracked line may say which shape is in force. A spelling census over every tracked text file (`git
   ls-files`, through tests/ref_reader_census.py's tracked_files) for the two phrasings found stale after the switch was
   built: full named as the default shape, and ci.yml's weekly schedule called paused, each matched across line breaks
   and comment markers (ONE_SHAPE_SPELLINGS). It reads those two phrasings, not their meaning, so another wording of
   either claim passes it. Red at the commit before it: CLAUDE.md called the weekly schedule paused, and ci.yml,
   secret-scan.yml, CONTRIBUTING.md, docs/batching.md, three test modules' docstrings and one test's pattern named full
   as the default.
"""
import importlib.util
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import pytest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
# the checkout root on sys.path before the imports from sibling modules, as tests/test_ci_macos_schedule.py does
sys.path.insert(0, ROOT)
from tests.conftest import (  # noqa: E402
    HEAVY_MODULES, SHARD_COUNT, SHARD_ENV, hash_shard, is_test_file, parse_shard, shard_of, shard_repo_path)
from tests.ci_shard_probe import PROBE_ITEM  # noqa: E402
from tests.ref_reader_census import tracked_files  # noqa: E402
from tests.test_ci_workflow_concurrency import (  # noqa: E402
    MAIN, SHA_A, SHAPES, SWITCH_LINES, _children, _keys_at, _strip_comment, _unquote, dispatch_run, evaluate,
    every_python, job_lines, os_list, python_versions, run, set_line, shape_lines, shape_of, triggers, with_shape)

WF = os.path.join(ROOT, ".github", "workflows", "ci.yml")
BATCH = "refs/heads/batch/2026-10-04a"
# a dispatch's inputs that put the macOS cells in the matrix (ci.yml's macos input, off by default)
MACOS_ON = {"macos": True}
# -n, --dist and --tx are pytest-xdist's options, so the legs that pass them skip where it is not installed, as
# tests/test_run_end_leaked_processes.py's do; CI's Python cells install it
HAS_XDIST = importlib.util.find_spec("xdist") is not None


# ---- the census -------------------------------------------------------------------------------------------------------

def probe_files(shard):
    """The test files a run collects, as repository-relative paths, asked of pytest in a child run from the repository
    root: `pytest --collect-only` with tests/ci_shard_probe.py loaded and no path, as the Run pytest step runs it (no
    path, so pytest walks the tree and asks pytest_ignore_collect about each file), with SHARD_ENV set to `shard`, or
    absent for None, in probe_child_env's environment, the one probe_run's run reads, so an option a caller exported in
    PYTEST_ADDOPTS reaches neither (BothSidesReadOneEnvironment). A child that fails, or lists no file, raises
    AssertionError with its output."""
    env = probe_child_env(None if shard is None else str(shard))
    p = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "-p", "no:anyio",
                        "-p", "tests.ci_shard_probe"],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    suffix = "::" + PROBE_ITEM
    files = [line[:-len(suffix)] for line in p.stdout.splitlines() if line.endswith(suffix)]
    if p.returncode != 0 or not files:
        raise AssertionError("the probe's child run for shard %r exited %d listing %d files: %s"
                             % (shard, p.returncode, len(files), (p.stdout + p.stderr)[-3000:]))
    if len(set(files)) != len(files):
        raise AssertionError("the probe's child run for shard %r listed a file twice: %r"
                             % (shard, sorted(f for f in set(files) if files.count(f) > 1)))
    return set(files)


def partition_faults(collected, shards):
    """What keeps {shard: files} from partitioning `collected`, as {fault: sorted files}: "left out", a collected file
    in no shard; "in two or more", a file in more than one shard; "not collected", a shard's file the run with no shard
    does not collect. Empty when each collected file is in exactly one shard and the shards hold nothing else."""
    counts = {}
    for files in shards.values():
        for f in files:
            counts[f] = counts.get(f, 0) + 1
    faults = {"left out": sorted(f for f in collected if f not in counts),
              "in two or more": sorted(f for f, n in counts.items() if n > 1),
              "not collected": sorted(f for f in counts if f not in collected)}
    return {k: v for k, v in faults.items() if v}


_COLLECTED = {}


def collected_files(shard):
    """probe_files(shard), run once a process: the census's classes share the collect-only runs."""
    if shard not in _COLLECTED:
        _COLLECTED[shard] = frozenset(probe_files(shard))
    return _COLLECTED[shard]


def probe_child_env(shard):
    """A child pytest's environment, built as tests/test_hermetic_kernel_postal.py's _proof_child_env builds one: this
    process's, less PYTEST_CURRENT_TEST, the variables pytest-xdist sets in a worker (PYTEST_XDIST_*: this process's,
    when it is a worker, would otherwise reach the child's controller and its worker) and PYTEST_ADDOPTS (options a
    caller exported would join the child's command line), with SHARD_ENV set to `shard`, a string, or absent for None.
    The census's collect-only child (probe_files) reads it as well as the child that runs the probe's items (probe_run),
    for the same reasons, so the two sides ShardsRunInCIsForms compares read one environment."""
    env = {k: v for k, v in os.environ.items()
           if k != "PYTEST_CURRENT_TEST" and not k.startswith("PYTEST_XDIST_") and k != "PYTEST_ADDOPTS"}
    env.pop(SHARD_ENV, None)
    if shard is not None:
        env[SHARD_ENV] = shard
    return env


class ShardsPartitionTheCollectedFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.collected = collected_files(None)
        cls.shards = {k: collected_files(k) for k in range(1, SHARD_COUNT + 1)}

    def test_the_collected_files_are_the_trees_test_files(self):
        # the derivation is not empty or partial: every tests/test_*.py file is collected, this one and the SDK pin's
        # among them
        on_disk = {"tests/" + n for n in os.listdir(HERE) if n.startswith("test_") and n.endswith(".py")}
        self.assertIn("tests/test_ci_shards.py", self.collected)
        self.assertIn("tests/test_ci_sdk_pin.py", self.collected)
        self.assertEqual(sorted(on_disk - self.collected), [], "test files on disk the run with no shard does not collect")

    def test_the_shards_partition_the_collected_files(self):
        self.assertEqual(partition_faults(self.collected, self.shards), {},
                         "the shards (%s) do not partition the %d collected test files: each file must be in exactly one "
                         "shard" % (", ".join("%d: %d files" % (k, len(v)) for k, v in sorted(self.shards.items())),
                                    len(self.collected)))

    def test_each_shard_is_the_rules(self):
        for k, files in sorted(self.shards.items()):
            with self.subTest(shard=k):
                want = {f for f in self.collected if shard_of(f) == k}
                self.assertEqual((sorted(files - want), sorted(want - files)), ([], []),
                                 "shard %d's run collects (beyond the rule's files, short of them) instead of exactly the "
                                 "files tests/conftest.py's shard_of assigns it" % k)
                self.assertTrue(files, "shard %d collects no file, and pytest exits 5 on a run that collects nothing" % k)

    def test_each_listed_heavy_module_runs_in_its_listed_shard_and_no_other(self):
        # read against HEAVY_MODULES itself rather than shard_of, so a shard_of that ignored the list would be red here
        # while the rule's census above, which reads shard_of, stayed green
        for path, k in sorted(HEAVY_MODULES.items()):
            with self.subTest(module=path):
                self.assertIn(path, self.collected, "a HEAVY_MODULES entry the run with no shard does not collect")
                self.assertEqual(sorted(j for j, files in self.shards.items() if path in files), [k],
                                 "%s is listed for shard %d, and the shards that collect it are not that one alone" % (path, k))


PROBE_PASSED_RE = re.compile(r"^PASSED (\S+)::%s$" % re.escape(PROBE_ITEM), re.M)


def probe_run(shard, workers):
    """Run the probe's items for `shard` as CI's cells run the suite, from the repository root with no path: `pytest
    -rA` with tests/ci_shard_probe.py loaded, under -n `workers` (an xdist controller and that many workers) or with no
    -n when `workers` is None, and SHARD_ENV set to the shard (probe_child_env). The items run, since xdist hands a
    collect-only run to no worker, and each asserts the variable is absent from its process's environment. Returns
    (the exit status, the files whose item passed, the summary's FAILED and ERROR lines, the output's tail)."""
    argv = [sys.executable, "-m", "pytest", "-q", "-rA", "-p", "no:cacheprovider", "-p", "no:anyio",
            "-p", "tests.ci_shard_probe"]
    if workers is not None:
        argv += ["-n", str(workers)]
    p = subprocess.run(argv, cwd=ROOT, env=probe_child_env(str(shard)), capture_output=True, text=True, timeout=600)
    passed = PROBE_PASSED_RE.findall(p.stdout)
    if len(set(passed)) != len(passed):
        raise AssertionError("the probe's run of shard %r under -n %r passed a file's item twice: %r"
                             % (shard, workers, sorted(f for f in set(passed) if passed.count(f) > 1)))
    failed = [line for line in p.stdout.splitlines() if line.startswith(("FAILED ", "ERROR "))]
    return p.returncode, set(passed), failed, (p.stdout + p.stderr)[-3000:]


class ShardsRunInCIsForms(unittest.TestCase):
    """The census in CI's form (round 1 of fork PR 986, 2026-10-06). tests/conftest.py's _stash_run_shard keeps
    SHARD_ENV in an xdist controller, whose worker inherits the controller's environment and applies the shard, and
    removes it in every process that runs tests, so no process a test starts inherits it. ShardsPartitionTheCollectedFiles
    collects with no -n, so neither half of that conditional ran in it. Here each shard's probe items run under -n 1, the
    Linux cells' form, and with no -n: the files whose item passed are that shard's collected files, and no item failed.
    Red under a mutant of either half: a controller that removes the variable (its one worker runs every file, under
    -n 1), and a process that runs tests and keeps it (every item fails its assert, in both forms). The -n 1 runs need
    pytest-xdist: without it they are not run and their test skips, and the form with no -n runs on any interpreter.
    Both sides read probe_child_env's environment (BothSidesReadOneEnvironment)."""

    @classmethod
    def setUpClass(cls):
        cls.collected = {k: collected_files(k) for k in range(1, SHARD_COUNT + 1)}
        cls.runs = {(k, w): probe_run(k, w) for k in range(1, SHARD_COUNT + 1) for w in ((1, None) if HAS_XDIST else
                                                                                         (None,))}

    def hold_each_shard(self, workers, form):
        for k in range(1, SHARD_COUNT + 1):
            with self.subTest(shard=k, form=form):
                rc, passed, failed, tail = self.runs[(k, workers)]
                want = self.collected[k]
                self.assertEqual(failed[:5], [], "shard %d %s: %d probe items failed, each finding %s in the environment of "
                                 "the process that runs it (tests/conftest.py's _stash_run_shard removes it in every "
                                 "process that runs tests): %s" % (k, form, len(failed), SHARD_ENV, tail))
                beyond, short = sorted(passed - want), sorted(want - passed)
                # only the -n 1 form has a controller; with no -n the two runs, from one environment, chose other files
                cause = ("under -n 1 the xdist controller must keep %s for its worker" % SHARD_ENV if workers == 1 else
                         "the run and the collect-only run, both from probe_child_env's environment, chose other files")
                self.assertEqual((beyond, short), ([], []),
                                 "shard %d %s ran the items of %d files where its collect-only run lists %d: %d beyond those "
                                 "and %d short of them (the lists above); %s" % (k, form, len(passed), len(want),
                                                                                len(beyond), len(short), cause))
                self.assertEqual(rc, 0, "shard %d %s exited %d: %s" % (k, form, rc, tail))

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_under_one_worker_each_shard_runs_its_collected_files_and_no_item_sees_the_variable(self):
        self.hold_each_shard(1, "under -n 1")

    def test_with_no_workers_each_shard_runs_its_collected_files_and_no_item_sees_the_variable(self):
        self.hold_each_shard(None, "with no -n")


class BothSidesReadOneEnvironment(unittest.TestCase):
    """ShardsRunInCIsForms holds two child runs of each shard to each other, the collect-only run (probe_files) and the
    run of the probe's items (probe_run), so both read probe_child_env's environment (round 2 of fork PR 986's review,
    2026-10-06): an option exported in PYTEST_ADDOPTS would otherwise reach the collect-only run alone, and the class
    would be red with no defect in tests/conftest.py. The file-set message names the xdist controller only for the -n 1
    form, the one form that has a controller. Red at the commit before: the collect-only run read the exported option,
    and the message of the form with no -n named the controller."""

    def test_the_collect_only_run_does_not_read_an_exported_pytest_addopts(self):
        # probe_files directly, never collected_files, so the run under the option does not enter the cache the census's
        # classes share; tests/test_ci_shards.py is a file the run with no shard collects (the census holds it)
        old = os.environ.get("PYTEST_ADDOPTS")
        self.addCleanup(lambda: os.environ.pop("PYTEST_ADDOPTS", None) if old is None
                        else os.environ.__setitem__("PYTEST_ADDOPTS", old))
        os.environ["PYTEST_ADDOPTS"] = "--ignore=tests/test_ci_shards.py"
        self.assertIn("tests/test_ci_shards.py", probe_files(None), "the collect-only run read PYTEST_ADDOPTS from this "
                      "process's environment, which probe_run's run does not read, so the two can list other files")

    def test_the_file_set_message_names_the_controller_for_the_one_worker_form_alone(self):
        for workers, form, names in ((None, "with no -n", False), (1, "under -n 1", True)):
            with self.subTest(form=form):
                case = ShardsRunInCIsForms("test_with_no_workers_each_shard_runs_its_collected_files_and_no_item_sees_"
                                           "the_variable")
                case.collected = {k: frozenset({"tests/test_a.py"}) for k in range(1, SHARD_COUNT + 1)}
                case.runs = {(k, workers): (0, {"tests/test_a.py"}, [], "") for k in range(1, SHARD_COUNT + 1)}
                case.runs[(1, workers)] = (0, {"tests/test_b.py"}, [], "")
                # a case that is not running: its subTest lets the first failure raise
                with self.assertRaises(AssertionError) as cm:
                    case.hold_each_shard(workers, form)
                msg = str(cm.exception)
                self.assertIn("shard 1 %s ran the items of 1 files where its collect-only run lists 1" % form, msg,
                              "the failure is not the file-set one: %s" % msg)
                self.assertEqual("xdist controller" in msg, names, "shard 1 %s: the file-set message %s name the xdist "
                                 "controller: %s" % (form, "must" if names else "must not", msg))


# A synthetic test file for TheShardEnvironmentInCIsForm, written outside the checkout: it records the shard variable as
# its test sees it and as a process the test starts sees it, in a file named for itself under @RECORDS@
SHARD_ENV_PROBE = '''\
import json
import os
import subprocess
import sys

RECORDS = @RECORDS@


def test_records_the_shard_variable():
    child = subprocess.run([sys.executable, "-c", "import json, os; print(json.dumps(os.environ.get('ROMP_TESTS_SHARD')))"],
                           capture_output=True, text=True, timeout=120)
    record = {"own": os.environ.get("ROMP_TESTS_SHARD"), "child": child.stdout.strip(), "child_rc": child.returncode}
    with open(os.path.join(RECORDS, os.path.basename(__file__) + ".json"), "w") as fh:
        json.dump(record, fh)
'''


class TheShardEnvironmentInCIsForm(unittest.TestCase):
    """tests/conftest.py's handling of SHARD_ENV, run in CI's forms (round 1 of fork PR 986, 2026-10-06): a child
    `pytest -n 1` (the Linux cells' form, an xdist controller and one worker) and a child `pytest -n 0` (the macOS
    cells' form, in process). And in two forms outside CI's, each in process too, since xdist hands tests to workers
    only when its dist option is not "no" and its tx list is not empty: `pytest --dist load` (a dist mode with neither
    -n nor --tx, so no tx list) and `pytest --tx popen` (a tx list with no dist mode). Each runs with SHARD_ENV set to a
    shard k, over synthetic test files written to a temporary directory outside the checkout, under the checkout's
    conftest loaded as a plugin (-p tests.conftest, from the repository root: tests/test_sdk_singleton_ratchet.py's
    nested_run shape). Outside, because a test file written under tests/ during a run would join
    tests/test_thread_stop_census.py's stray check and this module's census, which collects from the root, on another
    worker at the same moment. Each file records the variable as its test sees it and as a process the test starts sees
    it. Held: exactly the files the rule puts in shard k ran (shard_of over each file's path, which depends on the
    temporary path, so k is the first file's shard and files are added until another shard holds one), and every record
    reads None in both views. Each form is red under its own defect: -n 1 under a controller that removes the variable
    (its worker then runs every file); -n 0 under a process that runs tests and keeps it (both views read k); --dist
    load under a test of the dist option alone, and --tx popen under a test of the tx list alone, each of which keeps
    the variable in that run's one process (both views read k). All four forms pass pytest-xdist's options, -n 0 among
    them, so each skips where it is not installed."""

    def run_ci_form(self, *opts):
        base = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, base, True)
        self.assertFalse(base == ROOT or base.startswith(ROOT + os.sep),
                         "the synthetic files' directory %s is inside the checkout" % base)
        case, records, tmp = (os.path.join(base, d) for d in ("case", "records", "tmp"))
        for d in (case, records, tmp):
            os.makedirs(d)
        text = SHARD_ENV_PROBE.replace("@RECORDS@", repr(records))
        shards = {}
        while len(shards) < 4 or set(shards.values()) == {shards["test_shard_env_0.py"]}:
            self.assertLess(len(shards), 64, "64 synthetic files all landed in one shard")
            name = "test_shard_env_%d.py" % len(shards)
            path = os.path.join(case, name)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            shards[name] = shard_of(shard_repo_path(path))
        k = shards["test_shard_env_0.py"]
        want = {n for n, j in shards.items() if j == k}
        others = {n for n, j in shards.items() if j != k}
        self.assertTrue(want and others, "the synthetic files must put one file in shard %d and one in another shard" % k)
        env = probe_child_env(str(k))
        env["TMPDIR"] = tmp
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "tests.conftest", "-p", "no:cacheprovider",
                            "-p", "no:anyio", "--rootdir", case, *opts, case],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
        tail = (p.stdout + p.stderr)[-3000:]
        got = {}
        for n in sorted(shards):
            rec = os.path.join(records, n + ".json")
            if os.path.exists(rec):
                with open(rec, encoding="utf-8") as fh:
                    got[n] = json.load(fh)
        views = {}
        for n, r in sorted(got.items()):
            child = json.loads(r["child"]) if r["child_rc"] == 0 else "child exited %d" % r["child_rc"]
            if (r["own"], child) != (None, None):
                views[n] = (r["own"], child)
        self.assertEqual({"ran beyond shard k's files": sorted(set(got) - want), "short of them": sorted(want - set(got)),
                          "views (the test's own, a child's) that are not None": views},
                         {"ran beyond shard k's files": [], "short of them": [],
                          "views (the test's own, a child's) that are not None": {}},
                         "pytest %s with %s=%d over %d synthetic files (%d of them in shard %d) exited %d: %s"
                         % (" ".join(opts), SHARD_ENV, k, len(shards), len(want), k, p.returncode, tail))
        self.assertEqual(p.returncode, 0, tail)

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_under_one_worker_only_the_shards_files_run_and_no_view_sees_the_variable(self):
        self.run_ci_form("-n", "1")

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_in_process_only_the_shards_files_run_and_no_view_sees_the_variable(self):
        self.run_ci_form("-n", "0")

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_a_dist_mode_with_no_workers_runs_in_process_and_no_view_sees_the_variable(self):
        self.run_ci_form("--dist", "load")

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_a_tx_list_with_no_dist_mode_runs_in_process_and_no_view_sees_the_variable(self):
        self.run_ci_form("--tx", "popen")


class AValueThatNamesNoShard(unittest.TestCase):
    """An executed run with a SHARD_ENV value that names no shard (round 1 of fork PR 986, 2026-10-06). TheRule holds
    parse_shard in process; this holds the wiring in tests/conftest.py's _stash_run_shard that turns its ValueError into
    pytest's usage error before collection starts, for a value set by hand on a local run and for a later edit of that
    except clause, either of which would otherwise let the run collect every file, as a run with no shard does. (A shard
    axis in ci.yml that lists a value past SHARD_COUNT is ShardMatrix's red already.) The census's child command, run
    from the repository root with each value: pytest's usage-error exit, the variable and the value named in the output,
    and no file listed."""

    def test_each_value_ends_in_a_usage_error_naming_it_with_no_file_collected(self):
        for bad in (str(SHARD_COUNT + 1), "x", "0"):
            with self.subTest(value=bad):
                p = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                                    "-p", "no:anyio", "-p", "tests.ci_shard_probe"],
                                   cwd=ROOT, env=probe_child_env(bad), capture_output=True, text=True, timeout=600)
                out = p.stdout + p.stderr
                listed = [line for line in out.splitlines() if line.endswith("::" + PROBE_ITEM)]
                self.assertEqual({"exit": p.returncode, "names the variable and the value": "%s=%r" % (SHARD_ENV, bad) in out,
                                  "files listed": len(listed)},
                                 {"exit": int(pytest.ExitCode.USAGE_ERROR), "names the variable and the value": True,
                                  "files listed": 0},
                                 "%s=%r: %s" % (SHARD_ENV, bad, out[-3000:]))


class PartitionFaultsReadsEachFault(unittest.TestCase):
    """partition_faults over synthetic shards: green on a partition, and each way out of one named."""
    COLLECTED = {"tests/test_a.py", "tests/test_b.py", "tests/test_c.py"}

    def test_a_partition_has_no_fault(self):
        self.assertEqual(partition_faults(self.COLLECTED, {1: {"tests/test_a.py"}, 2: {"tests/test_b.py", "tests/test_c.py"}}), {})

    def test_a_file_dropped_from_every_shard_is_left_out(self):
        self.assertEqual(partition_faults(self.COLLECTED, {1: {"tests/test_a.py"}, 2: {"tests/test_b.py"}}),
                         {"left out": ["tests/test_c.py"]})

    def test_a_file_in_two_shards_is_named(self):
        self.assertEqual(partition_faults(self.COLLECTED, {1: {"tests/test_a.py", "tests/test_c.py"},
                                                           2: {"tests/test_b.py", "tests/test_c.py"}}),
                         {"in two or more": ["tests/test_c.py"]})

    def test_no_selection_puts_every_file_in_every_shard(self):
        self.assertEqual(partition_faults(self.COLLECTED, {1: set(self.COLLECTED), 2: set(self.COLLECTED)}),
                         {"in two or more": sorted(self.COLLECTED)})

    def test_a_file_the_run_does_not_collect_is_named(self):
        self.assertEqual(partition_faults(self.COLLECTED, {1: {"tests/test_a.py", "tests/test_z.py"},
                                                           2: {"tests/test_b.py", "tests/test_c.py"}}),
                         {"not collected": ["tests/test_z.py"]})


class TheRule(unittest.TestCase):
    """tests/conftest.py's rule, in process: a function of the path alone, total over 1 to SHARD_COUNT."""

    def test_every_path_lands_in_one_shard_from_one_to_the_count(self):
        for i in range(500):
            self.assertIn(shard_of("tests/test_synthetic_%d.py" % i), range(1, SHARD_COUNT + 1))

    def test_the_rule_is_the_digests_first_eight_bytes_modulo_the_count(self):
        import hashlib
        path = "tests/test_ci_shards.py"
        self.assertNotIn(path, HEAVY_MODULES, "the example is a file the hash places")
        want = int.from_bytes(hashlib.sha256(path.encode()).digest()[:8], "big") % SHARD_COUNT + 1
        self.assertEqual(hash_shard(path), want)
        self.assertEqual(shard_of(path), want)

    def test_a_listed_heavy_module_is_in_its_listed_shard_and_every_other_path_is_the_hashs(self):
        for path, k in sorted(HEAVY_MODULES.items()):
            self.assertEqual(shard_of(path), k, "shard_of gives %s, listed for shard %d, another shard" % (path, k))
        for i in range(500):
            path = "tests/test_synthetic_%d.py" % i
            self.assertEqual(shard_of(path), hash_shard(path))

    def test_the_heavy_list_names_existing_test_files_at_most_one_to_a_shard(self):
        self.assertTrue(HEAVY_MODULES, "the weighted rule's list is empty: the rule is the hash alone, and the comments "
                        "that state a weighted rule are stale")
        for path, k in sorted(HEAVY_MODULES.items()):
            with self.subTest(module=path):
                self.assertTrue(is_test_file(os.path.join(ROOT, path)), "a HEAVY_MODULES entry that is not a test file "
                                "on disk (renamed or removed): it would place nothing")
                self.assertEqual(shard_repo_path(os.path.join(ROOT, path)), path, "an entry is written as shard_of reads "
                                 "a path: repository-relative, with forward slashes")
                self.assertIs(type(k), int, "an entry's shard is a whole number, not a string or a bool")
                self.assertIn(k, range(1, SHARD_COUNT + 1), "an entry's shard must be one of 1 to SHARD_COUNT")
        shards = sorted(HEAVY_MODULES.values())
        self.assertEqual(sorted(set(shards)), shards, "two heavy modules share a shard: the list puts at most one in each")

    def test_parse_cache_states_the_shard_its_named_consumer_runs_in(self):
        # tests/parse_cache.py's singleton check is order-dependent: a Linux cell reds on a writer only when a check runs
        # after it in the same shard, and its named consumer, the thread-stop census, runs in one shard alone. The
        # passage names that shard and how the rule gives it (listed in HEAVY_MODULES, or by the hash), held here to
        # shard_of, so a move of the census by the list or by SHARD_COUNT reds until the passage is restated. A text pin:
        # it holds what the passage says, not what a run does (the census above holds where the module runs)
        census = "tests/test_thread_stop_census.py"
        how = "listed for" if census in HEAVY_MODULES else "hashed to"
        with open(os.path.join(HERE, "parse_cache.py"), encoding="utf-8") as fh:
            text = " ".join(fh.read().split())
        want = "the thread-stop census, %s shard %d, runs in shard %d alone" % (how, shard_of(census), shard_of(census))
        self.assertTrue(want in text, "tests/parse_cache.py's passage on the Linux cells does not say where the "
                        "thread-stop census runs as the rule places it (%r)" % want)
        self.assertTrue("tests/conftest.py's CI's shards section" in text, "tests/parse_cache.py's passage points to the "
                        "rule rather than copying its count")

    def test_the_count_the_cap_pin_reads_is_the_conftests(self):
        # tests/test_ci_bats_bound.py reads SHARD_COUNT from tests/conftest.py's text rather than importing it (the Shell
        # job imports that module under a python with no pytest); the text and the imported value agree
        from tests.test_ci_bats_bound import shard_count_as_written
        self.assertEqual(shard_count_as_written(), SHARD_COUNT)

    def test_a_shard_value_names_a_shard_or_none(self):
        self.assertIsNone(parse_shard(None))
        self.assertIsNone(parse_shard(""))
        for k in range(1, SHARD_COUNT + 1):
            self.assertEqual(parse_shard(str(k)), k)
        # the ASCII values 1 to SHARD_COUNT and no other: a superscript two, which str.isdigit takes and int() refuses
        # with its own message; an Arabic-Indic one and a fullwidth two, which int() reads as 1 and 2; and a leading
        # zero, which int() reads. Each refusal names the variable and the value
        for bad in ("0", str(SHARD_COUNT + 1), "1/2", "x", " 1", "-1", "01", "\u00b2", "\u0661", "\uff12"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError) as caught:
                    parse_shard(bad)
                self.assertIn("%s=%r" % (SHARD_ENV, bad), str(caught.exception),
                              "the refusal does not name the variable and the value")

    def test_a_test_file_is_one_pytest_makes_a_test_module_of(self):
        # pytest's default patterns (the census above holds them to what pytest collects); a pattern with a separator is
        # matched against the whole path, with */ put before a relative one, as pytest matches it
        here = os.path.realpath(__file__)
        self.assertTrue(is_test_file(here))
        self.assertFalse(is_test_file(os.path.join(HERE, "conftest.py")), "a helper module is not a test file")
        self.assertFalse(is_test_file(HERE), "a directory is not a test file")
        self.assertTrue(is_test_file(here, ["tests/test_ci_*.py"]))
        self.assertFalse(is_test_file(here, ["other/test_*.py"]))
        self.assertEqual(shard_repo_path(here), "tests/test_ci_shards.py")


# ---- the workflow -----------------------------------------------------------------------------------------------------

def _flow_list(text):
    """A one-line flow sequence of plain or quoted scalars, `['3.10', '3.11']`, as its strings; else LookupError."""
    m = re.fullmatch(r"\[(.*)\]", _strip_comment(text))
    if m is None:
        raise LookupError("%r is not a one-line flow sequence; re-anchor this pin" % text)
    return [_unquote(w) for w in m.group(1).split(",") if w.strip()]


def python_matrix(src):
    """The python job's strategy.matrix as written: (os: expression, python-version value as written (a flow list or the
    shape switch's expression; python_versions reads either for a run), [shard], [exclude entry as a dict]). An include:
    is refused (python_cells models exclude alone), and so is any other key."""
    jl = job_lines(src, "python")
    strat = next((_children(jl, i, 4) for k, _r, i in _keys_at(jl, 4) if k == "strategy"), None)
    mat = next((_children(strat, i, 6) for k, _r, i in _keys_at(strat, 6) if k == "matrix"), None) if strat else None
    if mat is None:
        raise LookupError("the python job has no strategy.matrix; re-anchor this pin")
    keys = {k: (rest, i) for k, rest, i in _keys_at(mat, 8)}
    if set(keys) != {"os", "python-version", "shard", "exclude"}:
        raise LookupError("the python job's matrix keys are %r, not os, python-version, shard and exclude; re-anchor this "
                          "pin" % sorted(keys))
    excludes = []
    for line in _children(mat, keys["exclude"][1], 8):
        m = re.match(r"^( *)(- )?([\w-]+): (.+)$", line)
        if m is None:
            raise LookupError("an exclude: line this reader does not read: %r; re-anchor this pin" % line)
        if m.group(2):
            excludes.append({})
        elif not excludes:
            raise LookupError("an exclude: line before any entry: %r; re-anchor this pin" % line)
        excludes[-1][m.group(3)] = _unquote(_strip_comment(m.group(4)))
    return (_strip_comment(keys["os"][0]), _strip_comment(keys["python-version"][0]), _flow_list(keys["shard"][0]),
            excludes)


def python_cells(src, event, ref=MAIN, inputs=None, ctx=None):
    """The python job's cells for a run of `event` on `ref`, as GitHub builds them: the product of the os list (the
    os: expression evaluated by tests/test_ci_workflow_concurrency.py's os_list, a dispatch carrying `inputs`), the
    python-version list (python_versions: the flow list, or the shape switch's expression evaluated for the run) and the
    shard list, less each cell an exclude entry matches (every key of the entry equal to the cell's; a key the matrix
    lacks is an error, as GitHub makes it one, and an entry whose value no list holds matches nothing). ctx, when given,
    is the run's context instead (dispatch_run's, with each input at its declared default).
    [{"os", "python-version", "shard"}]."""
    os_expr, versions_text, shards, excludes = python_matrix(src)
    for e in excludes:
        unknown = set(e) - {"os", "python-version", "shard"}
        if unknown:
            raise LookupError("an exclude entry names %r, which the matrix does not define" % sorted(unknown))
    ctx = run(event, ref, SHA_A, inputs) if ctx is None else ctx
    cells = [{"os": o, "python-version": v, "shard": s}
             for o, v, s in itertools.product(os_list(os_expr, ctx), python_versions(versions_text, ctx), shards)]
    return [c for c in cells if not any(all(c[k] == v for k, v in e.items()) for e in excludes)]


def python_job_head(src):
    m = re.search(r"^  python:\n((?:    .*\n|\n)+?)    strategy:\n", src, re.M)
    if m is None:
        raise LookupError("the python job's head moved; re-anchor this pin")
    return m.group(1)


def shard_env_value(src):
    """The Run pytest step's SHARD_ENV value as written, read from the step's env: block."""
    step = re.search(r"^      - name: Run pytest\n((?:        .*\n|\n)*)", "".join(l + "\n" for l in job_lines(src, "python")), re.M)
    if step is None:
        raise LookupError("the python job has no Run pytest step; re-anchor this pin")
    vals = re.findall(r"^          %s: (.+)$" % re.escape(SHARD_ENV), step.group(1), re.M)
    if len(vals) != 1:
        raise LookupError("the Run pytest step's env sets %s %d times, not once; re-anchor this pin"
                          % (SHARD_ENV, len(vals)))
    return vals[0].strip()


def cell_value(template, cell):
    """A value holding ${{ }} expressions as a cell renders it: each expression evaluated with matrix.os,
    matrix.python-version and matrix.shard, a format('<text>', <name>) inside one read first as the text with {0}
    replaced by the name's value (the one form of format this reader models)."""
    ctx = {"matrix." + k: v for k, v in cell.items()}

    def fmt(m):
        if m.group(2) not in ctx:
            raise LookupError("format() of %s, which this reader does not model" % m.group(2))
        return "'%s'" % m.group(1).replace("{0}", ctx[m.group(2)]).replace("'", "''")

    def expr(m):
        inner = re.sub(r"format\('((?:[^']|'')*)', ([\w.-]+)\)", fmt, m.group(1))
        v = evaluate(inner, ctx)
        return "" if v in (None, False) else str(v)

    return re.sub(r"\$\{\{(.*?)\}\}", expr, template)


class ShardMatrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(WF, encoding="utf-8") as fh:
            cls.src = fh.read()
        cls.n = SHARD_COUNT
        cls.want_shards = [str(k) for k in range(1, cls.n + 1)]

    def test_the_shard_axis_lists_one_to_the_shard_count(self):
        self.assertEqual(python_matrix(self.src)[2], self.want_shards,
                         "the python job's shard axis must list 1 to SHARD_COUNT in tests/conftest.py (%d), each as a quoted "
                         "string, the values the Run pytest step hands the conftest" % self.n)

    def test_a_batch_push_runs_each_interpreter_once_per_shard_on_linux(self):
        cells = python_cells(self.src, "push", BATCH)
        shape = shape_of(self.src)
        versions = BATCH_PYTHONS[shape]
        self.assertEqual(sorted((c["os"], c["python-version"], c["shard"]) for c in cells),
                         sorted(("ubuntu-latest", v, s) for v in versions for s in self.want_shards),
                         "a batch push under the %s shape runs %s as one Linux job per shard each, and no macOS job"
                         % (shape, versions))

    def test_a_dispatch_adds_one_unsharded_macos_job_per_macos_interpreter(self):
        mac = [c for c in python_cells(self.src, "workflow_dispatch", inputs=MACOS_ON) if c["os"] == "macos-latest"]
        self.assertEqual(sorted(c["python-version"] for c in mac), ["3.10", "3.13"],
                         "a dispatch with the macos input on runs one macOS job for each of 3.10 and 3.13, as before the "
                         "shards: %r" % mac)
        for c in mac:
            self.assertEqual(cell_value(shard_env_value(self.src), c), "",
                             "a macOS cell's %s must be empty, so the cell runs every test file: %r" % (SHARD_ENV, c))

    def test_the_run_pytest_step_hands_each_linux_cell_its_shard(self):
        value = shard_env_value(self.src)
        for c in python_cells(self.src, "workflow_dispatch", inputs=MACOS_ON):
            if c["os"] == "ubuntu-latest":
                with self.subTest(cell=c):
                    self.assertEqual(cell_value(value, c), c["shard"], "the Run pytest step's %s on %r" % (SHARD_ENV, c))

    def test_each_cells_job_name_is_its_own(self):
        name = re.search(r"^    name: (.+)$", python_job_head(self.src), re.M)
        self.assertTrue(name, "the python job has no name: line")
        cells = python_cells(self.src, "workflow_dispatch", inputs=MACOS_ON)
        names = [cell_value(name.group(1), c) for c in cells]
        self.assertEqual(len(set(names)), len(names), "two cells share a job name, so their checks cannot be told apart: %r"
                         % sorted(names))
        for c, n in zip(cells, names):
            with self.subTest(cell=c):
                if c["os"] == "ubuntu-latest":
                    self.assertIn("shard %s" % c["shard"], n)
                else:
                    self.assertEqual(n, "Python %s (macos-latest)" % c["python-version"], "a macOS cell keeps its name")


# ---- the shape switch (2026-10-06) -------------------------------------------------------------------------------------
FIVE = ["3.10", "3.11", "3.12", "3.13", "3.14t"]
# the interpreters a batch push runs under each shape (a pull request too, were it a trigger: the expression's default)
BATCH_PYTHONS = {"full": FIVE, "smaller": ["3.12", "3.14t"]}
# the interpreters the weekly schedule runs under each shape; None: the schedule is no trigger, so no scheduled run starts
WEEKLY_PYTHONS = {"full": None, "smaller": ["3.10", "3.11", "3.13"]}
# a manual dispatch runs all five under both shapes, and its macos input on adds these, one unsharded job each
DISPATCH_PYTHONS = FIVE
MACOS_PYTHONS = ["3.10", "3.13"]
PR = "refs/pull/1/merge"


def cell_rows(cells):
    return sorted((c["os"], c["python-version"], c["shard"]) for c in cells)


def expected_rows(pythons, macos=False):
    """The cells, as cell_rows gives them, of a run of pythons on Linux, one job per shard, plus with macos the macOS
    cells: one shard-1 job (run unsharded) for each of MACOS_PYTHONS."""
    rows = [("ubuntu-latest", v, str(k)) for v in pythons for k in range(1, SHARD_COUNT + 1)]
    return sorted(rows + ([("macos-latest", v, "1") for v in MACOS_PYTHONS] if macos else []))


def changed_lines(a, b):
    """The indexes of the lines that differ between a and b (same line count asserted by the caller)."""
    return [i for i, (x, y) in enumerate(zip(a.split("\n"), b.split("\n"))) if x != y]


class ShapeSwitch(unittest.TestCase):
    """Item 3 of the module docstring: the three lines, their agreement, the three-line change, and each shape's cells."""

    @classmethod
    def setUpClass(cls):
        with open(WF, encoding="utf-8") as fh:
            cls.src = fh.read()
        cls.shapes = {shape: with_shape(cls.src, shape) for shape in SHAPES}

    def test_the_three_lines_are_each_read_once_and_agree(self):
        lines = shape_lines(self.src)
        self.assertEqual(sorted(lines), sorted(SWITCH_LINES))
        self.assertIn(lines["python-version"][1], SHAPES)
        self.assertIn(lines["schedule"][1], ("live", "commented"))
        self.assertEqual(lines["cron"][0], lines["schedule"][0] + 1, "the cron entry is the line after the schedule: key")
        self.assertEqual(lines["cron"][1], lines["schedule"][1], "the two schedule lines are commented or live together")
        self.assertIn(shape_of(self.src), SHAPES, "the schedule lines and the python-version literal say one shape")

    def test_each_half_flip_is_refused(self):
        # any one or two of the three lines switched without the rest: the schedule lines live under full bill a weekly
        # run nobody chose; commented under smaller, 3.10, 3.11 and 3.13 never run; one schedule line live without the
        # other is a schedule with no entries, or an entry outside the schedule, and the file is invalid
        flips = [c for n in (1, 2) for c in itertools.combinations(SWITCH_LINES, n)]
        self.assertEqual(len(flips), 6, "every proper subset of the three lines but the empty one")
        for shape in SHAPES:
            other = [s for s in SHAPES if s != shape][0]
            for flipped in flips:
                half = self.shapes[shape]
                for which in flipped:
                    half = set_line(half, which, other)
                with self.subTest(shape=shape, flipped=flipped):
                    self.assertEqual(len(changed_lines(self.shapes[shape], half)), len(flipped),
                                     "a half-flip changes the lines it flips and no other")
                    with self.assertRaises(LookupError):
                        shape_of(half)

    def test_switching_the_shape_changes_exactly_the_three_lines(self):
        lines = shape_lines(self.src)
        three = sorted(lines[which][0] for which in SWITCH_LINES)
        self.assertEqual(len(set(three)), 3, "three distinct lines")
        current = shape_of(self.src)
        for shape, src in self.shapes.items():
            with self.subTest(shape=shape):
                self.assertEqual(len(src.split("\n")), len(self.src.split("\n")), "the switch adds or drops no line")
                changed = changed_lines(self.src, src)
                self.assertEqual(len(changed), 0 if shape == current else 3, "switching the shape is a three-line change")
                self.assertEqual(changed, [] if shape == current else three,
                                 "switching to %s changes the two schedule lines and the python-version line, and "
                                 "nothing else" % shape)
                self.assertEqual(shape_of(src), shape)
                self.assertEqual(with_shape(src, current), self.src, "switching back restores the file")

    def test_each_shape_runs_its_cells_for_each_event(self):
        for shape, src in self.shapes.items():
            events = triggers(src)
            with self.subTest(shape=shape, run="batch push"):
                self.assertEqual(cell_rows(python_cells(src, "push", BATCH)), expected_rows(BATCH_PYTHONS[shape]))
            with self.subTest(shape=shape, run="pull request"):
                self.assertNotIn("pull_request", events, "a pull request is no trigger of ci.yml")
                self.assertEqual(cell_rows(python_cells(src, "pull_request", PR)), expected_rows(BATCH_PYTHONS[shape]),
                                 "were a pull request a trigger, it would run what a batch push runs")
            with self.subTest(shape=shape, run="schedule"):
                if WEEKLY_PYTHONS[shape] is None:
                    self.assertNotIn("schedule", events, "under %s no scheduled run can start: the schedule lines are "
                                     "commented" % shape)
                    self.assertEqual(cell_rows(python_cells(src, "schedule")), expected_rows(FIVE), "under full the "
                                     "expression gives all five for every event, so the shape alone decides")
                else:
                    self.assertIn("schedule", events, "under %s the weekly schedule is a trigger" % shape)
                    self.assertEqual(cell_rows(python_cells(src, "schedule")), expected_rows(WEEKLY_PYTHONS[shape]))
            with self.subTest(shape=shape, run="dispatch, macos at its default"):
                ctx = dispatch_run(src, MAIN, SHA_A)
                self.assertFalse(ctx["inputs.macos"], "the macos input is off by default")
                self.assertEqual(cell_rows(python_cells(src, "workflow_dispatch", ctx=ctx)), expected_rows(DISPATCH_PYTHONS))
            with self.subTest(shape=shape, run="dispatch, macos on"):
                ctx = dispatch_run(src, MAIN, SHA_A, macos=True)
                self.assertEqual(cell_rows(python_cells(src, "workflow_dispatch", ctx=ctx)),
                                 expected_rows(DISPATCH_PYTHONS, macos=True))

    def test_every_interpreter_runs_on_a_batch_push_or_the_schedule_and_none_on_both(self):
        for shape, src in self.shapes.items():
            with self.subTest(shape=shape):
                batch = {c["python-version"] for c in python_cells(src, "push", BATCH)}
                weekly = ({c["python-version"] for c in python_cells(src, "schedule")} if "schedule" in triggers(src)
                          else set())
                self.assertEqual(sorted(batch | weekly), sorted(DISPATCH_PYTHONS), "every interpreter runs at least weekly")
                self.assertEqual(batch & weekly, set(), "no interpreter is billed on both a batch push and the schedule")
        self.assertEqual(every_python(self.src), sorted(FIVE))


# ---- prose that holds in both shapes (2026-10-06) ----------------------------------------------------------------------
# The two phrasings of a claim about ci.yml that one of its shapes makes false, each found stale after the switch was
# built: full named as the default shape (false once the three lines say smaller), and ci.yml's weekly schedule called
# paused (false under smaller, whose weekly run is live). Between two words a pattern admits any run of blanks, line breaks
# and comment markers, so a phrase folded over comment lines is read.
_GAP = rb"[\s#*/>]+"
ONE_SHAPE_SPELLINGS = (
    re.compile(rb"\bfull(?:" + _GAP + rb"shape)?," + _GAP + rb"the" + _GAP + rb"default\b", re.I),
    re.compile(rb"\bweekly" + _GAP + rb"schedule" + _GAP + rb"is" + _GAP + rb"paused\b", re.I),
)


def one_shape_phrases(data):
    """[(line number, the phrase with its blanks and line breaks made single spaces)] for each match of
    ONE_SHAPE_SPELLINGS in the bytes `data`."""
    return [(data.count(b"\n", 0, m.start()) + 1, re.sub(rb"\s+", b" ", m.group(0)).decode("utf-8", "replace"))
            for pattern in ONE_SHAPE_SPELLINGS for m in pattern.finditer(data)]


def one_shape_hits(rels, root=ROOT):
    """[(path, line number, phrase)] over the text files among `rels`, paths under `root`: a symlink or a path that is not
    a regular file is not read, and a file with a NUL in its first 8000 bytes is not text (git's own test), as
    tests/ref_reader_census.py reads the tree."""
    hits = []
    for rel in rels:
        path = os.path.join(root, rel)
        if os.path.islink(path) or not os.path.isfile(path):
            continue
        with open(path, "rb") as fh:
            data = fh.read()
        if b"\0" not in data[:8000]:
            hits.extend((rel, n, phrase) for n, phrase in one_shape_phrases(data))
    return hits


class ProseHoldsInBothShapes(unittest.TestCase):
    """Item 4 of the module docstring: no tracked text says which shape is in force, by the census's two phrasings."""

    def test_no_tracked_text_names_the_shape_in_force(self):
        rels = tracked_files(ROOT)
        self.assertIn(".github/workflows/ci.yml", rels, "the listing is not this repository's: re-anchor this pin")
        self.assertEqual(one_shape_hits(rels), [], (
            "tracked text that one shape of ci.yml's switch makes false (path, line, phrase above): switching the shape "
            "is a three-line change (ci.yml's header, THE SHAPE SWITCH), so no other line may say which shape is in "
            "force; say what each shape does instead. A spelling census of two phrasings, not of their meaning."))

    def test_the_census_reads_a_folded_phrase_and_passes_the_neutral_ones(self):
        # each red sample assembled here, so this file's own text holds no phrase the census reads
        full, default, weekly = b"full", b"default", b"weekly schedule"
        red = (b"x\n# " + full + b", the\n# " + default + b": every batch push",
               b"under its " + full + b" shape, the " + default + b", or",
               b"a manual run (`ci.yml`'s " + weekly + b" is\n  paused), and",
               b"  // " + full.upper() + b", THE " + default.upper())
        for data in red:
            with self.subTest(data=data):
                self.assertEqual(len(one_shape_phrases(data)), 1)
        self.assertEqual(one_shape_phrases(red[0])[0], (2, full.decode() + ", the # " + default.decode()))
        green = (b"commented under " + full + b", the shape as built, and",
                 b"its schedule was paused from 2026-10-04",
                 b"The weekly macOS run stays PAUSED until the bill is read",
                 b"under " + full + b", the " + default + b"s",
                 b"under " + full + b" the " + default)
        for data in green:
            with self.subTest(data=data):
                self.assertEqual(one_shape_phrases(data), [])


class TheReadersThemselves(unittest.TestCase):
    """python_cells and cell_value over synthetic matrices: an exclude that removes the macOS shards, an include that the
    reader refuses, and a dropped shard that the axis pin sees."""
    HEAD = ("jobs:\n  python:\n    name: Python ${{ matrix.python-version }} (${{ matrix.os }}${{ matrix.os == 'ubuntu-latest' "
            "&& format(', shard {0}', matrix.shard) || '' }})\n    runs-on: ${{ matrix.os }}\n    strategy:\n      matrix:\n"
            "        os: ${{ fromJSON(github.event_name == 'workflow_dispatch' && '[\"ubuntu-latest\",\"macos-latest\"]' || "
            "'[\"ubuntu-latest\"]') }}\n        python-version: ['3.10', '3.12']\n")

    def test_an_exclude_removes_the_macos_shards(self):
        src = self.HEAD + "        shard: ['1', '2']\n        exclude:\n          - os: macos-latest\n            shard: '2'\n"
        cells = python_cells(src, "workflow_dispatch")
        self.assertEqual(sorted((c["os"], c["python-version"], c["shard"]) for c in cells),
                         [("macos-latest", "3.10", "1"), ("macos-latest", "3.12", "1"), ("ubuntu-latest", "3.10", "1"),
                          ("ubuntu-latest", "3.10", "2"), ("ubuntu-latest", "3.12", "1"), ("ubuntu-latest", "3.12", "2")])
        self.assertEqual(len(python_cells(src, "push", BATCH)), 4)

    def test_without_the_exclude_macos_runs_every_shard(self):
        src = self.HEAD + "        shard: ['1', '2']\n        exclude:\n          - os: windows-latest\n"
        self.assertEqual(len([c for c in python_cells(src, "workflow_dispatch") if c["os"] == "macos-latest"]), 4)

    def test_an_include_is_refused(self):
        src = self.HEAD + "        shard: ['1', '2']\n        exclude:\n          - os: macos-latest\n            shard: '2'\n" \
                          "        include:\n          - os: ubuntu-latest\n            python-version: '3.11'\n"
        with self.assertRaises(LookupError):
            python_matrix(src)

    def test_a_shard_dropped_from_the_axis_is_seen(self):
        src = self.HEAD + "        shard: ['1']\n        exclude:\n          - os: macos-latest\n            shard: '2'\n"
        self.assertNotEqual(python_matrix(src)[2], [str(k) for k in range(1, SHARD_COUNT + 1)])

    SWITCH = ('on:\n  push:\n    branches: [\'batch/**\']\n  workflow_dispatch:\n  # schedule:   # line 1\n'
              '  #   - cron: "17 10 * * 1"   # line 2\njobs:\n  python:\n    strategy:\n      matrix:\n'
              '        python-version: ${{ fromJSON(\'full\' == \'smaller\' && github.event_name != \'workflow_dispatch\' && '
              '(github.event_name == \'schedule\' && \'["3.10"]\' || \'["3.12"]\') || \'["3.10","3.12"]\') }}   # line 3\n'
              '    steps:\n      - run: x\n')
    COMMENTED = '  # schedule:   # line 1\n  #   - cron: "17 10 * * 1"   # line 2\n'

    def test_the_switch_readers(self):
        self.assertEqual(self.SWITCH.count(self.COMMENTED), 1)
        self.assertEqual(shape_of(self.SWITCH), "full")
        small = with_shape(self.SWITCH, "smaller")
        self.assertEqual(shape_of(small), "smaller")
        self.assertIn('\n  schedule:   # line 1\n    - cron: "17 10 * * 1"   # line 2\n', small)
        self.assertEqual(with_shape(small, "full"), self.SWITCH)
        self.assertEqual(triggers(small)["schedule"], ['    - cron: "17 10 * * 1"   # line 2'],
                         "the live schedule is a trigger whose one child line is the cron entry")
        self.assertNotIn("schedule", triggers(self.SWITCH))
        for n in (1, 2):
            for flipped in itertools.combinations(SWITCH_LINES, n):
                half = self.SWITCH
                for which in flipped:
                    half = set_line(half, which, "smaller")
                with self.subTest(flipped=flipped):
                    with self.assertRaises(LookupError):
                        shape_of(half)
        live_key = self.SWITCH.replace("  # schedule:", "  schedule:")
        self.assertEqual(set_line(self.SWITCH, "schedule", "smaller"), live_key, "set_line flips the one line it names")
        with self.assertRaises(LookupError):   # a second cron entry under the key
            shape_lines(self.SWITCH.replace(self.COMMENTED, self.COMMENTED + '  #   - cron: "0 9 * * 2"\n'))
        with self.assertRaises(LookupError):   # a second schedule: key
            shape_lines(self.SWITCH.replace("jobs:\n", '  # schedule:\njobs:\n'))
        with self.assertRaises(LookupError):   # no cron entry after the key
            shape_lines(self.SWITCH.replace('  #   - cron: "17 10 * * 1"   # line 2\n', ""))
        with self.assertRaises(LookupError):   # the cron entry not right after the key
            shape_lines(self.SWITCH.replace(self.COMMENTED, '  # schedule:   # line 1\n  # a note\n'
                                            '  #   - cron: "17 10 * * 1"   # line 2\n'))
        with self.assertRaises(LookupError):   # the one-line flow form, which tests/test_ci_sdk_pin.py refuses live
            shape_lines(self.SWITCH.replace(self.COMMENTED, '  # schedule: [{cron: "17 10 * * 1"}]   # line 1\n'))
        with self.assertRaises(LookupError):   # no shape literal
            shape_lines(self.SWITCH.replace("fromJSON('full' == 'smaller' && ", "fromJSON("))
        with self.assertRaises(LookupError):   # no schedule lines
            shape_lines(self.SWITCH.replace(self.COMMENTED, ""))
        with self.assertRaises(ValueError):
            with_shape(self.SWITCH, "medium")
        with self.assertRaises(ValueError):
            set_line(self.SWITCH, "schedule-and-cron", "smaller")

    def test_python_versions_reads_a_flow_list_and_the_expression(self):
        self.assertEqual(python_versions("['3.10', \"3.14t\"]  # two", run("push", BATCH, SHA_A)), ["3.10", "3.14t"])
        expr = "${{ fromJSON(github.event_name == 'schedule' && '[\"3.10\"]' || '[\"3.12\",\"3.14t\"]') }}"
        self.assertEqual(python_versions(expr, run("schedule", MAIN, SHA_A)), ["3.10"])
        self.assertEqual(python_versions(expr, run("push", BATCH, SHA_A)), ["3.12", "3.14t"])
        for bad in ("[3.10, 3.12]", "['3.1x']", "${{ fromJSON('[]') }}", "${{ fromJSON(github.run_id) }}", "3.12",
                    "${{ fromJSON('[3.10]') }}"):
            with self.subTest(value=bad):
                with self.assertRaises(LookupError):
                    python_versions(bad, run("push", BATCH, SHA_A))

    def test_the_names_render_per_cell(self):
        name = re.search(r"^    name: (.+)$", self.HEAD, re.M).group(1)
        self.assertEqual(cell_value(name, {"os": "ubuntu-latest", "python-version": "3.12", "shard": "2"}),
                         "Python 3.12 (ubuntu-latest, shard 2)")
        self.assertEqual(cell_value(name, {"os": "macos-latest", "python-version": "3.10", "shard": "1"}),
                         "Python 3.10 (macos-latest)")


if __name__ == "__main__":
    unittest.main()
