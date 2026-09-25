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


def worker_counts(cmd):
    """Every worker count the command's tokens set, in order, as text: the token after `-n` or `--numprocesses`, the
    tail of a `-nN` token, the value of `--numprocesses=N`. Other spellings (a short-flag cluster such as `-qn2`) are
    not read, so they give no count."""
    toks = shlex.split(cmd)
    out = []
    for i, t in enumerate(toks):
        if t in ("-n", "--numprocesses"):
            out.append(toks[i + 1] if i + 1 < len(toks) else "")
        elif t.startswith("--numprocesses="):
            out.append(t.split("=", 1)[1])
        elif t.startswith("-n") and not t.startswith("--") and len(t) > 2:
            out.append(t[2:])
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


if __name__ == "__main__":
    unittest.main()
