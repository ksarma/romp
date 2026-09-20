#!/usr/bin/env bats
# The shell job's home for the two tests of tests/test_bats_bare_negation.py that need bats: the register's agreement with the bats
# on PATH (BatsGroundTruth.test_the_record_is_what_bats_says_under_both_rewrites: 367 shapes, every one run under both rewrites of
# its negation, the verdicts against RECORDED) and the oracle over the corpus (BatsCorpus: every bare `!` in a test body of every
# tests/*.bats, decided by running its test alone with the negation rewritten to `! true` and to `! false`). Both skip in the python
# cells of CI, which install no bats; the shell job's `bats --print-output-on-failure tests/*.bats` (.github/workflows/ci.yml)
# picks this file up, and that job is the one cell with a bats (1.11.1, from the release tarball), so this is where the record is
# verified and where every negation of the tree is decided. python3 is on the runner image, as that job's header comment says, and
# the module is stdlib-only; the tests print their tables, and bats shows the output when a test fails.
#
# One test per module test, not one for both: the job's BATS_TEST_TIMEOUT is a per-test bound of 180 s, and a single test running
# both took 139 s under it on a loaded box (each alone, 52 s and 95 s); one each leaves room for a slower runner.
#
# Every BATS_* variable is unset for the inner run. Under the job's BATS_TEST_TIMEOUT bats's timeout watcher is a background child
# of each test, and a bare `wait` in a test waits on it: the register's D_bg shape hung to a 40 s kill with the variable set
# (exit 124) and passed in 0.07 s without it. A nested bats must also not read the outer run's BATS_ROOT, BATS_RUN_TMPDIR and the
# rest. The module strips them again at its own bats calls; the scrub here keeps the python process itself clean, so nothing it
# starts inherits them either.
#
# macOS, the weekly and dispatch cell of the shell job, skips with the reason: its bash is 3.2.57 and Homebrew's bats-core is
# 1.14.0; the register's two `|&` shapes do not parse under that bash, and the record is verified against 1.10.0 and 1.11.1 only.

# Runs one test of the module under python3 with every BATS_* variable unset, from the repository root.
run_module_test() {   # $1 the test's dotted name under tests.test_bats_bare_negation
    if [ "$(uname -s)" = Darwin ]; then
        skip "the macOS cell runs bash 3.2.57 with Homebrew bats-core 1.14.0: the register's two |& shapes do not parse under that bash, and the record is verified against bats 1.10.0 and 1.11.1 only"
    fi
    command -v python3 >/dev/null || { echo "python3 is not on PATH: the module runs under it"; return 1; }
    local root; root="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    local -a scrub=(); local v
    for v in "${!BATS_@}"; do scrub+=(-u "$v"); done
    cd "$root"
    env "${scrub[@]}" python3 -m unittest -v "tests.test_bats_bare_negation.$1"
}

@test "bats bare negation: the record agrees with this bats under both rewrites (tests/test_bats_bare_negation.py, the register)" {
    run_module_test BatsGroundTruth.test_the_record_is_what_bats_says_under_both_rewrites
}

@test "bats bare negation: every candidate of the tree is read by bats (tests/test_bats_bare_negation.py, the corpus)" {
    run_module_test BatsCorpus.test_every_candidate_of_every_suite_is_read_by_bats
}
