#!/usr/bin/env python3
"""The Python job's Run pytest step runs two pytest-xdist workers (.github/workflows/ci.yml, 2026-09-25).

Serially the cells had reached the 25-minute cap they had then (this fork's main, run 35890814789: the 3.14t cell at
24 min 35 s). Measured on 2026-09-22 with Python 3.10 on a four-CPU budget (a systemd CPUQuota of 400 percent; GitHub
documents its Linux runner for a public repository at 4 CPUs and 16 GB), the suite took 1437 s serially and 739 s with
two workers, whose run's cgroup memory peaked at 10.9 GB (decimal, page cache included), and three workers peaked at
15.8 GB. So the step sets the worker count once, to 2, and a step before it installs pytest-xdist, without which pytest
refuses -n. The job's cap and its pin in tests/test_ci_bats_bound.py are romp-on/romp PR #2130 as merged: their figures
and run ids are romp-on/romp's Actions runs of its serial suite, and with two workers the measurement puts this fork's
Linux cells at about half their serial time, well inside that cap. Source pins, as tests/test_ci_bats_bound.py: the
workflow text read by line shape, with no YAML library in the test deps."""
import os
import re
import shlex
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
WF = os.path.join(os.path.dirname(HERE), ".github", "workflows", "ci.yml")


def python_job_steps(path=WF):
    """[(name, run command)] of the python job's named steps, in file order, read off the workflow text at path. The job
    is the run of lines under `  python:` that are blank or indented four spaces or more (the shape
    tests/test_ci_bats_bound.py reads the job's head with); a step is a `      - name:` line and the lines under it
    indented eight spaces or more, and its command is its one-line `        run:` value, None when it has none. Raises
    LookupError when the job moved or was renamed."""
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(r"^  python:\n((?:    .*\n|\n)+)", src, re.M)
    if not m:
        raise LookupError("the python job moved or was renamed (%s): re-anchor this pin" % path)
    steps = []
    for s in re.finditer(r"^      - name: (.*)\n((?:        .*\n|\n)*)", m.group(1), re.M):
        run = re.search(r"^        run: (.+)$", s.group(2), re.M)
        steps.append((s.group(1).strip(), run.group(1) if run else None))
    return steps


# pytest's short flags that take a value, besides xdist's -n, as pytest 9.1.1's parser lists them with pytest-xdist 3.8.0
# and pytest-timeout loaded: in a short-flag cluster such a letter takes the rest of the token as its value. worker_counts
# reads every other letter as an argument-less flag, the side that reads a count rather than missing one (pytest refuses a
# letter it does not know).
VALUE_FLAGS = frozenset("Wckmopr")


def worker_counts(cmd):
    """Every worker count the command's tokens set, in order, as text, read the way pytest's parser reads them on Python
    3.11 and later: the token after `--numprocesses`, the value of `--numprocesses=N`, and in a token with one leading
    dash, its letters in turn: a letter in VALUE_FLAGS ends the read (the rest is that flag's value), `n` takes the rest
    of the token with one leading `=` dropped (`-n2`, `-n=2` and `-qn3` read 2, 2 and 3) or the next token when nothing
    follows it, and any other letter passes to the next. Only those spellings are read: a count set through addopts (the
    step's PYTEST_ADDOPTS, an ini file, or `-o addopts=...` on the line) or by xdist's --tx specs is not seen, nor an
    abbreviated long option, which pytest refuses (it reads `--numproc=2` as an unrecognized argument)."""
    toks = shlex.split(cmd)
    out = []
    for i, t in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        if t == "--numprocesses":
            out.append(nxt)
        elif t.startswith("--numprocesses="):
            out.append(t.split("=", 1)[1])
        elif t.startswith("-") and not t.startswith("--"):
            for j, c in enumerate(t[1:], 1):
                if c in VALUE_FLAGS:
                    break
                if c == "n":
                    rest = t[j + 1:]
                    out.append((rest[1:] if rest.startswith("=") else rest) if rest else nxt)
                    break
    return out


def requirement_names(cmd):
    """The names a `python -m pip install` command lists, lower-cased with `_` and `.` read as `-`, each cut at its first
    extras bracket, version operator, marker or URL separator: every token after `install` that does not start with `-`.
    Empty for any command that does not start `python -m pip install`."""
    toks = shlex.split(cmd)
    if toks[:4] != ["python", "-m", "pip", "install"]:
        return []
    return [re.split(r"[\[<>=!~;@]", t, maxsplit=1)[0].lower().replace("_", "-").replace(".", "-")
            for t in toks[4:] if not t.startswith("-")]


class PythonJobRunsTwoWorkers(unittest.TestCase):
    def setUp(self):
        self.steps = python_job_steps()
        names = [n for n, _ in self.steps]
        self.assertEqual(names.count("Run pytest"), 1, "the python job has no single Run pytest step (%r): re-anchor this pin" % names)
        self.at = names.index("Run pytest")
        self.cmd = self.steps[self.at][1]
        self.assertTrue(self.cmd and shlex.split(self.cmd)[:3] == ["python", "-m", "pytest"],
                        "the Run pytest step's run value is not one `python -m pytest ...` line: %r" % (self.cmd,))

    def test_the_run_pytest_step_sets_two_workers_once(self):
        counts = worker_counts(self.cmd)
        self.assertEqual(counts, ["2"], "the Run pytest step must set the xdist worker count once, to 2 (-n 2); it sets %r in %r. "
                                        "Serially the suite took 1437 s against 739 s with two workers (2026-09-22, four CPUs), "
                                        "and three workers peaked at 15.8 GB, near the 16 GB GitHub documents for the runner"
                                        % (counts, self.cmd))

    def test_a_step_before_it_installs_pytest_xdist(self):
        before = self.steps[:self.at]
        installers = [n for n, run in before if run and "pytest-xdist" in requirement_names(run)]
        self.assertTrue(installers, "no step before Run pytest has a `python -m pip install` run line naming pytest-xdist, and "
                                    "without it pytest refuses -n: %r" % (before,))


class WorkerCountsReadsWhatPytestReads(unittest.TestCase):
    """worker_counts against pytest's own reading of each spelling: pytest 9.1.1 with pytest-xdist 3.8.0 read each of these
    on Python 3.11 to 3.14 as the counts below (on 3.10 its parser refuses a cluster that opens with an argument-less flag
    such as -q, so each cluster here that sets a count is a line 3.10 refuses outright)."""

    def read(self, spelling):
        return worker_counts("python -m pytest -q %s --durations=10" % spelling)

    def test_the_plain_spellings_read_their_count(self):
        for spelling in ("-n 2", "-n2", "--numprocesses 2", "--numprocesses=2"):
            with self.subTest(spelling=spelling):
                self.assertEqual(self.read(spelling), ["2"], "pytest reads %s as two workers" % spelling)

    def test_one_equals_sign_after_n_is_dropped(self):
        self.assertEqual(self.read("-n=2"), ["2"], "pytest reads -n=2 as two workers; a pin reading it as '=2' goes red on a "
                                                   "line that runs two")
        self.assertEqual(self.read("-n==2"), ["=2"], "pytest drops one = and no more, and refuses the '=2' left")

    def test_a_trailing_n_in_a_short_flag_cluster_is_a_count(self):
        for spelling, counts in (("-qn3", ["3"]), ("-n 2 -qn3", ["2", "3"]), ("-qn 3", ["3"]), ("-qn=3", ["3"]),
                                 ("-qvn=2", ["2"])):
            with self.subTest(spelling=spelling):
                self.assertEqual(self.read(spelling), counts, "%s sets the counts %r in pytest's parser, which keeps the last: "
                                                              "a cluster's trailing n sets a count, and a second count beside "
                                                              "-n 2 must not pass unseen" % (spelling, counts))

    def test_a_flag_that_takes_a_value_takes_the_rest_of_its_cluster(self):
        for spelling in ("-rfEn3", "-qrn3", "-kn3", "-qmn3"):
            with self.subTest(spelling=spelling):
                self.assertEqual(self.read(spelling), [], "pytest reads the n in %s as part of the value of the flag before "
                                                          "it, not as a count" % spelling)


if __name__ == "__main__":
    unittest.main()
