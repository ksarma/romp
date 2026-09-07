#!/usr/bin/env bats

# Every bats suite that starts the REAL bin/romp-manager gives it a state root of its own. The
# manager's STATE_ROOT is ROMP_STATE_DIR || XDG_STATE_HOME/romp || ~/.local/state/romp, and since
# 2026-09-06 it writes a row to STATE_ROOT/restart-audit.jsonl before every SIGTERM it sends
# (auditSigterm): a suite whose teardown stops a real manager with neither variable set appends to
# the LIVE ledger, and those rows read as requests on record for kills nobody made (seven such rows
# landed there on 2026-09-06, from tests/romp-manager-ensure.bats). This is the ratchet for the
# bats side, as tests/test_state_isolation_order.py is for the pytest modules: the isolation lines
# must be present in each such suite, before its first @test (setup() runs before every test; a
# floor set inside one test leaves the others on the live root).
#
# The two lines, as the suites spell them:
#     unset ROMP_STATE_DIR                    # a profiled kernel exports it; it outranks the XDG floor
#     export XDG_STATE_HOME="$TEST_DIR/state"  # or another path under the test's own directory
# A suite that instead exports ROMP_STATE_DIR to a path under its test directory satisfies both.

TESTS="$(cd "$(dirname "$BATS_TEST_FILENAME")" && pwd)"

# A suite "starts the manager" when it resolves the real binary for execution. The suites all spell
# that `.../bin" && pwd)/romp-manager"` (a variable later handed to `node`), or run
# "$ROMP_DIR/bin/romp-manager" directly. Mocks under a test directory and mentions in comments or
# grep patterns do not count.
manager_suites() {
    local f
    for f in "$TESTS"/*.bats; do
        [ "$f" = "$BATS_TEST_FILENAME" ] && continue     # this file quotes the pattern in its self-check
        if grep -Eq '(pwd\)/romp-manager"|node "\$ROMP_DIR/bin/romp-manager")' "$f"; then
            printf '%s\n' "$f"
        fi
    done
    return 0
}

before_first_test() { sed -n '1,/^@test /p' "$1"; }

@test "the detector finds the suites known to start a manager (a regex drift cannot pass vacuously)" {
    run manager_suites
    [[ "$output" == *"/romp-manager-ensure.bats"* ]]
    [[ "$output" == *"/romp-manager-origin.bats"* ]]
    [[ "$output" == *"/romp.bats"* ]]
}

@test "every suite that starts the real manager isolates its state root before its first @test" {
    local f head bad=()
    while IFS= read -r f; do
        head="$(before_first_test "$f")"
        if ! grep -Eq '^[[:space:]]*(unset[[:space:]]+([A-Z_]+[[:space:]]+)*ROMP_STATE_DIR|export[[:space:]]+ROMP_STATE_DIR="\$)' <<<"$head"; then
            bad+=("$(basename "$f"): neither 'unset ROMP_STATE_DIR' nor an export of it to a test path before the first @test")
        fi
        if ! grep -Eq '^[[:space:]]*export[[:space:]]+(XDG_STATE_HOME|ROMP_STATE_DIR)="\$' <<<"$head"; then
            bad+=("$(basename "$f"): no 'export XDG_STATE_HOME=\"\$TEST_DIR/...\"' (or ROMP_STATE_DIR) before the first @test")
        fi
    done < <(manager_suites)
    if [ "${#bad[@]}" -ne 0 ]; then
        printf 'These suites start a real bin/romp-manager without a state root of their own; its\n' >&2
        printf 'SIGTERM notes would land in the live restart-audit.jsonl:\n' >&2
        printf '  %s\n' "${bad[@]}" >&2
        return 1
    fi
}

@test "the ratchet itself rejects a suite that starts a manager on the live root" {
    # Self-check with a synthetic suite: the detector must see it and the rule must fail it, else a
    # regex drift would make the test above pass with nothing checked.
    # Written line by line: a `@test` at column 0 inside a heredoc here would register with bats as a
    # test of THIS file (it did: "unknown test name test_starts_one").
    local d; d="$(mktemp -d)"
    printf '%s\n' '#!/usr/bin/env bats' 'setup() {' '    TEST_DIR="$(mktemp -d)"' \
        '    MGR="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp-manager"' '}' \
        '@'"test \"starts one\" { node \"\$MGR\" up; }" > "$d/leaky.bats"
    grep -q '^@test ' "$d/leaky.bats"                          # the fixture has a real first test line
    TESTS="$d" run manager_suites
    [ "$output" = "$d/leaky.bats" ]
    head="$(before_first_test "$d/leaky.bats")"
    run grep -Eq 'ROMP_STATE_DIR' <<<"$head"
    [ "$status" -ne 0 ]
    rm -rf "$d"
}
