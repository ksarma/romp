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
2. Source pins over ci.yml, read by line shape with no YAML library, as tests/test_ci_workflow_concurrency.py reads it
   (ShardMatrix): the python job's shard axis lists 1 to SHARD_COUNT; a batch push runs each interpreter as
   SHARD_COUNT Linux jobs, one per shard, and a dispatch with its macos input on (tests/test_ci_macos_input.py) adds one
   macOS job per macOS interpreter, unsharded; the Run
   pytest step hands each Linux cell its shard and each macOS cell an empty value; and each cell's job name differs.
   Each shard's cap is tests/test_ci_bats_bound.py's (PythonJobCeiling).
"""
import itertools
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
# the checkout root on sys.path before the imports from sibling modules, as tests/test_ci_macos_schedule.py does
sys.path.insert(0, ROOT)
from tests.conftest import (  # noqa: E402
    HEAVY_MODULES, SHARD_COUNT, SHARD_ENV, hash_shard, is_test_file, parse_shard, shard_of, shard_repo_path)
from tests.ci_shard_probe import PROBE_ITEM  # noqa: E402
from tests.test_ci_workflow_concurrency import (  # noqa: E402
    MAIN, SHA_A, _children, _keys_at, _strip_comment, _unquote, evaluate, job_lines, os_list, run)

WF = os.path.join(ROOT, ".github", "workflows", "ci.yml")
BATCH = "refs/heads/batch/2026-10-04a"
# a dispatch's inputs that put the macOS cells in the matrix (ci.yml's macos input, off by default)
MACOS_ON = {"macos": True}


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

    def test_each_listed_heavy_module_runs_in_its_listed_shard_and_no_other(self):
        # read against HEAVY_MODULES itself rather than shard_of, so a shard_of that ignored the list would be red here
        # while the rule's census above, which reads shard_of, stayed green
        for path, k in sorted(HEAVY_MODULES.items()):
            with self.subTest(module=path):
                self.assertIn(path, self.collected, "a HEAVY_MODULES entry the run with no shard does not collect")
                self.assertEqual(sorted(j for j, files in self.shards.items() if path in files), [k],
                                 "%s is listed for shard %d, and the shards that collect it are not that one alone" % (path, k))


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


# ---- the workflow -----------------------------------------------------------------------------------------------------

def _flow_list(text):
    """A one-line flow sequence of plain or quoted scalars, `['3.10', '3.11']`, as its strings; else LookupError."""
    m = re.fullmatch(r"\[(.*)\]", _strip_comment(text))
    if m is None:
        raise LookupError("%r is not a one-line flow sequence; re-anchor this pin" % text)
    return [_unquote(w) for w in m.group(1).split(",") if w.strip()]


def python_matrix(src):
    """The python job's strategy.matrix as written: (os: expression, [python-version], [shard], [exclude entry as a
    dict]). An include: is refused (python_cells models exclude alone), and so is any other key."""
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
    return (_strip_comment(keys["os"][0]), _flow_list(keys["python-version"][0]), _flow_list(keys["shard"][0]), excludes)


def python_cells(src, event, ref=MAIN, inputs=None):
    """The python job's cells for a run of `event` on `ref`, as GitHub builds them: the product of the os list (the
    os: expression evaluated by tests/test_ci_workflow_concurrency.py's os_list, a dispatch carrying `inputs`), the
    python-version list and the shard list, less each cell an exclude entry matches (every key of the entry equal to the
    cell's; a key the matrix lacks is an error, as GitHub makes it one). [{"os", "python-version", "shard"}]."""
    os_expr, versions, shards, excludes = python_matrix(src)
    for e in excludes:
        unknown = set(e) - {"os", "python-version", "shard"}
        if unknown:
            raise LookupError("an exclude entry names %r, which the matrix does not define" % sorted(unknown))
    cells = [{"os": o, "python-version": v, "shard": s}
             for o, v, s in itertools.product(os_list(os_expr, run(event, ref, SHA_A, inputs)), versions, shards)]
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
        versions = python_matrix(self.src)[1]
        self.assertTrue({"3.10", "3.12", "3.14t"} <= set(versions), versions)
        self.assertEqual(sorted((c["os"], c["python-version"], c["shard"]) for c in cells),
                         sorted(("ubuntu-latest", v, s) for v in versions for s in self.want_shards),
                         "a batch push runs every interpreter as one Linux job per shard, and no macOS job")

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

    def test_the_names_render_per_cell(self):
        name = re.search(r"^    name: (.+)$", self.HEAD, re.M).group(1)
        self.assertEqual(cell_value(name, {"os": "ubuntu-latest", "python-version": "3.12", "shard": "2"}),
                         "Python 3.12 (ubuntu-latest, shard 2)")
        self.assertEqual(cell_value(name, {"os": "macos-latest", "python-version": "3.10", "shard": "1"}),
                         "Python 3.10 (macos-latest)")


if __name__ == "__main__":
    unittest.main()
