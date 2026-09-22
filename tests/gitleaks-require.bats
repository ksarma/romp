#!/usr/bin/env bats

# The ROMP_GITLEAKS_REQUIRE switch of tests/gitleaks-config.bats, pinned by running that suite as
# a child bats. The suite skips itself when gitleaks is absent, so a clone that never wanted the
# scanner still runs green; CI's Linux Shell job installs the pinned gitleaks in the step before
# bats and sets the switch in its Run bats step's env, so an absence THERE fails with the reason
# instead of passing as skips (the stance ROMP_SERVED_TESTS_REQUIRE takes, pinned by
# tests/test_served_tests_require.py: a pin that can skip on the runner meant to be the arbiter is
# worse than a missing pin). Three cases: the switch on with ROMP_GITLEAKS naming a missing path
# fails the suite, every case red, each naming the switch and the path's fault; the switch unset
# skips every case, green; and CI's Run bats step carries the switch in its env, read from
# .github/workflows/ci.yml itself the way the -diff case of the suite reads CI's scan line, since a
# copy of the line here would stay green while CI drifted.
#
# No gitleaks and no git runs here: ROMP_GITLEAKS names a path under a directory minted for the
# test, so the suite's setup() never consults PATH and stops before its first git command. The
# child bats is started from PATH like this one; bats resets BATS_RUN_TMPDIR and BATS_ROOT_PID on
# launch, so the two runs share no temp root. CI's Run bats step globs tests/*.bats, so this file
# runs there beside its subject.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SUITE="$ROMP_DIR/tests/gitleaks-config.bats"

setup() {
    TEST_DIR="$(mktemp -d)"
    # Under a directory minted for this test and never created: absent by construction, so the
    # suite's setup() takes its "does not exist" branch, whatever is on PATH.
    MISSING="$TEST_DIR/none/gitleaks"
}

teardown() { rm -rf "$TEST_DIR"; }

# The suite's case count, from its own text, so the expectations below move with it (ten at this
# writing). A count of zero would make every assertion below vacuous, so it is refused.
suite_cases() {
    local n
    n=$(grep -c '^@test ' "$SUITE" || true)
    [ "$n" -gt 0 ] || { echo "no @test lines found in $SUITE; the count the cases below derive from is empty"; return 1; }
    echo "$n"
}

@test "ROMP_GITLEAKS_REQUIRE=1 with ROMP_GITLEAKS naming a missing path: the suite fails, every case naming the switch and the path" {
    n=$(suite_cases)
    # env's -u before the assignments: GNU env reads options first, and a -u after an assignment is
    # taken for the command. The switch is set explicitly, whatever the environment this file runs in.
    run env -u ROMP_GITLEAKS_REQUIRE ROMP_GITLEAKS="$MISSING" ROMP_GITLEAKS_REQUIRE=1 bats "$SUITE" < /dev/null
    [ "$status" -eq 1 ] || {
        echo "expected exit 1 from tests/gitleaks-config.bats with the switch on and gitleaks missing, got exit $status:"
        echo "$output"; false; }
    [[ "$output" == *"which does not exist"* ]] || { echo "the failure does not name the path's fault (which does not exist):"; echo "$output"; false; }
    # Every case red, none skipped: the switch turns the file-level skip into a failure for each one.
    reds=$(printf '%s\n' "$output" | grep -c '^not ok ' || true)
    [ "$reds" -eq "$n" ] || { echo "expected $n 'not ok' lines (every case), got $reds:"; echo "$output"; false; }
    skips=$(printf '%s\n' "$output" | grep -c ' # skip ' || true)
    [ "$skips" -eq 0 ] || { echo "expected no skip with the switch on, got $skips:"; echo "$output"; false; }
    # Each red names the switch, so a reader of one TAP block knows what turned the skip red.
    named=$(printf '%s\n' "$output" | grep -c 'ROMP_GITLEAKS_REQUIRE=1:' || true)
    [ "$named" -eq "$n" ] || { echo "expected the switch named on $n reds, named on $named:"; echo "$output"; false; }
}

@test "the switch unset with ROMP_GITLEAKS naming a missing path: the suite skips every case and exits 0" {
    n=$(suite_cases)
    # -u so this holds where the environment already carries the switch, as CI's Linux Run bats step does.
    run env -u ROMP_GITLEAKS_REQUIRE ROMP_GITLEAKS="$MISSING" bats "$SUITE" < /dev/null
    [ "$status" -eq 0 ] || { echo "expected exit 0 from tests/gitleaks-config.bats with the switch unset and gitleaks missing, got exit $status:"; echo "$output"; false; }
    [[ "$output" == *"1..$n"* ]] || { echo "expected the plan line 1..$n:"; echo "$output"; false; }
    # The skip reason is the suite's own ("gitleaks not installed"), so a skip from any other guard
    # in that file would not count here.
    skips=$(printf '%s\n' "$output" | grep -c ' # skip gitleaks not installed$' || true)
    [ "$skips" -eq "$n" ] || { echo "expected $n skip lines (every case), got $skips:"; echo "$output"; false; }
    reds=$(printf '%s\n' "$output" | grep -c '^not ok ' || true)
    [ "$reds" -eq 0 ] || { echo "expected no failure with the switch unset, got $reds:"; echo "$output"; false; }
}

@test "CI's Run bats step carries ROMP_GITLEAKS_REQUIRE in its env, so the arbiter runner cannot skip the suite green" {
    # Keys on the step's env block: with the line gone, the Linux cell that installs gitleaks would
    # report a broken install as skips, and the suite's switch would guard nothing anywhere. Read from
    # the workflow's own text (the -diff case's pattern in tests/gitleaks-config.bats): exactly one
    # `- name: Run bats` step is expected; zero or two and the premise is gone, so say so. grep -c
    # prints 0 and exits 1 on no match, and bats runs under errexit, so without `|| true` the zero
    # case would stop at the assignment and never reach the message.
    ci="$ROMP_DIR/.github/workflows/ci.yml"
    n=$(grep -cE '^[[:space:]]*- name: Run bats[[:space:]]*$' "$ci" || true)
    [ "$n" -eq 1 ] || { echo "expected exactly one '- name: Run bats' step in ci.yml, found $n"; false; }
    start=$(grep -nE '^[[:space:]]*- name: Run bats[[:space:]]*$' "$ci" | cut -d: -f1)
    # The step's text runs from its name line to its run line, the first `run:` key at or after the
    # name (a comment line starts with `#` and is not a key, so it does not end the slice).
    end=$(awk -v s="$start" 'NR >= s && /^[[:space:]]*run:/ { print NR; exit }' "$ci")
    [ -n "$end" ] || { echo "the Run bats step at ci.yml:$start has no run: line"; false; }
    step=$(sed -n "${start},${end}p" "$ci")
    envat=$(printf '%s\n' "$step" | grep -nE '^[[:space:]]*env:[[:space:]]*$' | cut -d: -f1 | head -1)
    [ -n "$envat" ] || { echo "the Run bats step (ci.yml:$start-$end) has no env: block"; false; }
    # The line itself: a key at the start of a line (a comment naming the variable is not one), with
    # a value.
    reqs=$(printf '%s\n' "$step" | grep -cE '^[[:space:]]*ROMP_GITLEAKS_REQUIRE:[[:space:]]*[^[:space:]]' || true)
    [ "$reqs" -eq 1 ] || {
        echo "the Run bats step's env (ci.yml:$start-$end) must carry one 'ROMP_GITLEAKS_REQUIRE:' line with a value, found $reqs;"
        echo "without it the Linux cell that installs gitleaks reports a broken install as green skips"; false; }
    reqat=$(printf '%s\n' "$step" | grep -nE '^[[:space:]]*ROMP_GITLEAKS_REQUIRE:' | cut -d: -f1)
    [ "$reqat" -gt "$envat" ] || { echo "the ROMP_GITLEAKS_REQUIRE line (step line $reqat) is not under the step's env: (step line $envat)"; false; }
    # The value names 1, the on-value the suite's setup() reads. A GitHub expression is not
    # evaluated here; this is the necessary condition, that the value can write a 1 at all.
    value=$(printf '%s\n' "$step" | grep -E '^[[:space:]]*ROMP_GITLEAKS_REQUIRE:' | sed -E 's/^[[:space:]]*ROMP_GITLEAKS_REQUIRE:[[:space:]]*//')
    [[ "$value" == *1* ]] || { echo "the ROMP_GITLEAKS_REQUIRE value never writes 1, so the switch is never on: $value"; false; }
}
