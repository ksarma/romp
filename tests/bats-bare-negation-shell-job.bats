#!/usr/bin/env bats
# The shell job's home for the bats-backed tests of tests/test_bats_bare_negation.py: the register class (BatsGroundTruth: every
# shape run under both rewrites of its negation, the verdicts against RECORDED, and decide asked about every one-candidate test
# from the same run), the road class (BatsRoad: the corpus road's pieces against the bats on PATH, the TAP reader, the bound on a
# run, the TERM to the process running one, a synthetic suite decided candidate by candidate) and the oracle over the corpus
# (BatsCorpus: every bare `!` in a test body of every suite the job's bats command names, its glob read off the workflow, decided
# by running its test alone with the negation rewritten to `! true` and to `! false`, each rewrite run twice and its runs required
# to agree; and, since fork PR #871's round 2, eleventh commit, its routes pin: a token and a state root planted in the python
# process's environment reach no suite, the three candidates that read them decided in seconds). The corpus's other pin, the child
# pytest with a polluting module collected and deselected, is not run here: it needs pytest importable by the runner's python3,
# which this job does not install, and it skips there saying so (a skipping test here would pin nothing). All skip in the python
# cells of CI, which install no bats (warning once per process, since the tenth commit); the shell job's
# `bats --print-output-on-failure tests/*.bats`
# (.github/workflows/ci.yml) picks this file up. That job has two cells, ubuntu-latest on every run and macos-latest on a manual
# dispatch or the weekly schedule, and both install a bats: the Linux cell 1.11.1 from the release tarball (`Install bats (Linux)`),
# the macOS cell Homebrew's bats-core (`Install bats (macOS)`); run_module_tests below skips every test of this file on Darwin, so
# the Linux cell is where the record is verified and where every negation of the tree is decided. python3 is on the runner image,
# as that job's header comment says, and the module is stdlib-only; the tests print their tables, and bats shows the output when a
# test fails.
#
# One test per class or module test, not one for all: the job's BATS_TEST_TIMEOUT is a per-test bound of 180 s, and a single test
# running the register and the corpus took 139 s under it on a loaded box (2:19.14 total); apart, each of the three stays well
# inside the bound (the register's and the corpus's measured times, under both bats versions the record is verified against, are
# in the module docstring, the one home of those figures; the road's tests each bound the runs they start themselves). Every
# bats run the module starts is bounded itself (RUN_TIMEOUT, 60 s per corpus run), and the corpus prints each candidate's row as
# it is decided, so a run the outer bound ends still names its candidate in the output bats shows. Since fork PR #871's round 2
# each rewrite of a candidate runs twice (REPEATS) and four candidates are decided at a time (CORPUS_WORKERS), each run in its own
# copy of the tree; the corpus's time under that is in the module docstring.
#
# Every BATS_* variable is unset for the inner run. Under the job's BATS_TEST_TIMEOUT bats's timeout watcher is a background child
# of each test, and a bare `wait` in a test waits on it: the register's D_bg shape hung to a 40 s kill with the variable set
# (exit 124) and passed in 0.07 s without it. A nested bats must also not read the outer run's BATS_ROOT, BATS_RUN_TMPDIR and the
# rest. Since fork PR #871's round 2, tenth commit, the module builds the environment of every bats run it starts from a rule
# (BATS_ENV_KEYS: PATH, a fresh HOME and TMPDIR, LANG) and from nothing else of its process, so no BATS_* variable and no
# import-time write of a test module reaches them, by construction; the scrub here keeps the python process itself clean, so
# nothing else it starts (its bash probes run under its own environment) inherits them either. The module also drops the outer's
# libexec directory from the inner run's PATH (bats puts it first there, and the `bats` in it expects the BATS_ROOT this scrub
# removes: left on PATH, the inner bats ran with BATS_ROOT empty and did not load at all under CI's /usr/local layout, measured
# with 1.11.1 from a scratch prefix as the outer and the inner bats).
#
# macOS, the weekly and dispatch cell of the shell job, skips with the reason: its bash is 3.2.57 (actions/runner-images,
# images/macos/macos-15-Readme.md) and Homebrew's bats-core is 1.14.0; the register's `|&`, `coproc` and `;;&` shapes do not parse
# under that bash, which also gives no here-document warning under -n (the module reads it to find where a here-document
# ends), and the record is verified against 1.10.0 and 1.11.1 only. Every test of the module that derives from bash skips
# under such a bash too, wherever it runs (skip_unless_bash_serves), since the Python cells run the module on macOS with no bats.

# Runs tests of the module under python3 with every BATS_* variable unset, from the repository root.
run_module_tests() {   # $1 the dotted name under tests.test_bats_bare_negation: a class, or one test
    if [ "$(uname -s)" = Darwin ]; then
        skip "the macOS cell runs bash 3.2.57 with Homebrew bats-core 1.14.0: the register's |&, coproc and ;;& shapes do not parse under that bash, and the record is verified against bats 1.10.0 and 1.11.1 only; the Linux cell is where these run"
    fi
    command -v python3 >/dev/null || { echo "python3 is not on PATH: the module runs under it"; return 1; }
    local root; root="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    local -a scrub=(); local v
    for v in "${!BATS_@}"; do scrub+=(-u "$v"); done
    cd "$root"
    env "${scrub[@]}" python3 -m unittest -v "tests.test_bats_bare_negation.$1"
}

@test "bats bare negation: the record agrees with this bats under both rewrites and decide reads every differing shape (tests/test_bats_bare_negation.py, BatsGroundTruth)" {
    run_module_tests BatsGroundTruth
}

@test "bats bare negation: the corpus road's pieces against this bats, the bound on a run among them (tests/test_bats_bare_negation.py, BatsRoad)" {
    run_module_tests BatsRoad
}

@test "bats bare negation: every candidate of the tree is read by bats (tests/test_bats_bare_negation.py, the corpus)" {
    run_module_tests BatsCorpus.test_every_candidate_of_every_suite_is_read_by_bats
}

@test "bats bare negation: a token and a state root in the python process's environment reach no suite (tests/test_bats_bare_negation.py, the routes pin)" {
    run_module_tests BatsCorpus.test_a_token_and_a_state_root_written_into_the_process_environment_reach_no_suite
}
