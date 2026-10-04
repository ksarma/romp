#!/usr/bin/env python3
"""CI's shards (.github/workflows/ci.yml, 2026-10-04): each Linux Python cell runs as SHARD_COUNT one-worker jobs, each
over its own share of the test files, since one worker running the whole suite does not fit the private runner's 8 GB
(tests/conftest.py's CI's shards section has the measurement, the rule and the hook).

The census (ShardsPartitionTheCollectedFiles): the shards partition the collected test files, each file in one shard,
none in two, none left out, and each shard is the rule's. It asks pytest itself, in child runs from the repository
root with no path, as ci.yml's Run pytest step runs it: once with no shard (the collected files) and once for each
shard, with SHARD_ENV (ROMP_TESTS_SHARD) set to it. Each child loads tests/ci_shard_probe.py, which lists each file
pytest decides to make a test module of without importing it (a real collection of this suite took 696 s and more
than 5 GB on 2026-10-04); every step before that one, tests/conftest.py's pytest_ignore_collect among them, runs as
in CI. Red under a selection that drops a file from every shard, that puts a file in two shards, or that is absent
(every shard collects every file).
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
# the checkout root on sys.path before the imports from sibling modules, as tests/test_ci_macos_schedule.py does
sys.path.insert(0, ROOT)
from tests.conftest import SHARD_COUNT, SHARD_ENV, is_test_file, parse_shard, shard_of, shard_repo_path  # noqa: E402
from tests.ci_shard_probe import PROBE_ITEM  # noqa: E402


# ---- the census -------------------------------------------------------------------------------------------------------

def probe_files(shard):
    """The test files a run collects, as repository-relative paths, asked of pytest in a child run from the repository
    root: `pytest --collect-only` with tests/ci_shard_probe.py loaded and no path, as the Run pytest step runs it (no
    path, so pytest walks the tree and asks pytest_ignore_collect about each file), with SHARD_ENV set to `shard`, or
    absent for None. A child that fails, or lists no file, raises AssertionError with its output."""
    env = dict(os.environ)
    env.pop(SHARD_ENV, None)
    if shard is not None:
        env[SHARD_ENV] = str(shard)
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


class ShardsPartitionTheCollectedFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.collected = probe_files(None)
        cls.shards = {k: probe_files(k) for k in range(1, SHARD_COUNT + 1)}

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
        want = int.from_bytes(hashlib.sha256(path.encode()).digest()[:8], "big") % SHARD_COUNT + 1
        self.assertEqual(shard_of(path), want)

    def test_a_shard_value_names_a_shard_or_none(self):
        self.assertIsNone(parse_shard(None))
        self.assertIsNone(parse_shard(""))
        for k in range(1, SHARD_COUNT + 1):
            self.assertEqual(parse_shard(str(k)), k)
        for bad in ("0", str(SHARD_COUNT + 1), "1/2", "x", " 1", "-1"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    parse_shard(bad)

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


if __name__ == "__main__":
    unittest.main()
