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
# A suite that instead exports ROMP_STATE_DIR to a path under its test directory satisfies both, and
# so do the equivalent spellings: `X="$TEST_DIR/..."` on one line with an `export X` on another, or
# the assignment unquoted. A helper the suite `load`s counts as part of the suite, both ways: a floor
# set in a helper's function isolates, and a helper that starts the manager makes the suite one that
# does (review round 2: the first version read only the suite file, so a manager started through a
# loaded helper was never checked).

TESTS="$(cd "$(dirname "$BATS_TEST_FILENAME")" && pwd)"

# The helper files a suite `load`s (bats resolves `load name` to name, else name.bash, beside the
# suite), one per line; nothing for a suite that loads none.
loaded_helpers() {   # $1 suite
    local dir name f
    dir="$(dirname "$1")"
    while IFS= read -r name; do
        name="${name%\"}"; name="${name#\"}"; name="${name%\'}"; name="${name#\'}"
        [ -n "$name" ] || continue
        for f in "$dir/$name" "$dir/$name.bash"; do
            [ -f "$f" ] && { printf '%s\n' "$f"; break; }
        done
    done < <(sed -nE 's/^[[:space:]]*load[[:space:]]+([^[:space:]]+).*/\1/p' "$1")
    return 0
}

# A suite "starts the manager" when it, or a helper it loads, resolves the real binary for execution:
# a path built from the tests directory (`.../bin" && pwd)/romp-manager"`), `.../bin/romp-manager"`,
# or `node "$<VAR>/romp-manager"`. Comment lines do not count, and neither do mocks written under a
# test directory (`"$MOCK_DIR/romp-manager"` as a heredoc target or as ROMP_MANAGER_BIN).
MANAGER_START_RE='(pwd\)/romp-manager"|/bin/romp-manager"|node "\$[A-Za-z_][A-Za-z_0-9]*/romp-manager")'

suite_text() {   # $1 suite: the suite plus every helper it loads, comment lines dropped
    local f
    grep -Ev '^[[:space:]]*#' "$1"
    while IFS= read -r f; do grep -Ev '^[[:space:]]*#' "$f"; done < <(loaded_helpers "$1")
    return 0
}

manager_suites() {
    local f
    for f in "$TESTS"/*.bats; do
        [ "$f" = "$BATS_TEST_FILENAME" ] && continue     # this file quotes the pattern in its self-check
        if suite_text "$f" | grep -Eq "$MANAGER_START_RE"; then
            printf '%s\n' "$f"
        fi
    done
    return 0
}

before_first_test() { sed -n '1,/^@test /p' "$1"; }

# What a suite runs before its first @test: its own head plus every loaded helper, whole (a helper's
# functions run from setup()).
suite_head() {   # $1 suite
    local f
    before_first_test "$1"
    while IFS= read -r f; do cat "$f"; done < <(loaded_helpers "$1")
    return 0
}

# Whether `text` assigns VAR to a path under a shell variable and exports it: `export VAR="$..."` (other
# assignments may share the line), or `VAR="$..."` with an `export VAR` elsewhere (same line after a
# `;`, or its own line). The quote is optional.
assigned_and_exported() {   # $1 VAR, $2 text
    grep -Eq "^[[:space:]]*export[[:space:]]+([A-Za-z_][A-Za-z_0-9]*(=[^[:space:]]*)?[[:space:]]+)*$1=\"?\\\$" <<<"$2" && return 0
    grep -Eq "^[[:space:]]*$1=\"?\\\$" <<<"$2" \
        && grep -Eq "(^|;)[[:space:]]*export[[:space:]]+([A-Za-z_][A-Za-z_0-9]*[[:space:]]+)*$1([[:space:]]|;|$)" <<<"$2"
}

# One line per missing isolation line for a suite, nothing when it is isolated.
isolation_problems() {   # $1 suite
    local head
    head="$(suite_head "$1")"
    if ! grep -Eq '^[[:space:]]*unset[[:space:]]+([A-Za-z_][A-Za-z_0-9]*[[:space:]]+)*ROMP_STATE_DIR([[:space:]]|;|$)' <<<"$head" \
       && ! assigned_and_exported ROMP_STATE_DIR "$head"; then
        echo "$(basename "$1"): neither 'unset ROMP_STATE_DIR' nor an export of it to a test path before the first @test"
    fi
    if ! assigned_and_exported XDG_STATE_HOME "$head" && ! assigned_and_exported ROMP_STATE_DIR "$head"; then
        echo "$(basename "$1"): no 'export XDG_STATE_HOME=\"\$TEST_DIR/...\"' (or ROMP_STATE_DIR) before the first @test"
    fi
    return 0
}

@test "the detector finds the suites known to start a manager (a regex drift cannot pass vacuously)" {
    run manager_suites
    [[ "$output" == *"/romp-manager-ensure.bats"* ]]
    [[ "$output" == *"/romp-manager-origin.bats"* ]]
    [[ "$output" == *"/romp.bats"* ]]
}

@test "every suite that starts the real manager isolates its state root before its first @test" {
    local f bad=()
    while IFS= read -r f; do
        while IFS= read -r line; do bad+=("$line"); done < <(isolation_problems "$f")
    done < <(manager_suites)
    if [ "${#bad[@]}" -ne 0 ]; then
        printf 'These suites start a real bin/romp-manager without a state root of their own; its\n' >&2
        printf 'SIGTERM notes would land in the live restart-audit.jsonl:\n' >&2
        printf '  %s\n' "${bad[@]}" >&2
        return 1
    fi
}

# The self-checks below build synthetic suites line by line: a `@test` at column 0 inside a heredoc
# here would register with bats as a test of THIS file (it did: "unknown test name test_starts_one").

@test "the ratchet itself rejects a suite that starts a manager on the live root" {
    # the detector must see it and the rule must fail it, else a regex drift would make the test above
    # pass with nothing checked
    local d; d="$(mktemp -d)"
    printf '%s\n' '#!/usr/bin/env bats' 'setup() {' '    TEST_DIR="$(mktemp -d)"' \
        '    MGR="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp-manager"' '}' \
        '@'"test \"starts one\" { node \"\$MGR\" up; }" > "$d/leaky.bats"
    grep -q '^@test ' "$d/leaky.bats"                          # the fixture has a real first test line
    TESTS="$d" run manager_suites
    [ "$output" = "$d/leaky.bats" ]
    run isolation_problems "$d/leaky.bats"
    [ "${#lines[@]}" -eq 2 ]
    [[ "${lines[0]}" == "leaky.bats: neither 'unset ROMP_STATE_DIR'"* ]]
    [[ "${lines[1]}" == "leaky.bats: no 'export XDG_STATE_HOME"* ]]
    rm -rf "$d"
}

@test "a manager started through a loaded helper is seen, and the helper's missing floor is reported" {
    # the suite file alone never names the binary: the helper resolves and starts it
    local d; d="$(mktemp -d)"
    printf '%s\n' '# a helper that starts the real manager' 'start_mgr() {' \
        '    MGR="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp-manager"' \
        '    node "$MGR" up &' '}' > "$d/mgr-helper.bash"
    printf '%s\n' '#!/usr/bin/env bats' 'load mgr-helper' 'setup() {' '    TEST_DIR="$(mktemp -d)"' \
        '    start_mgr' '}' '@'"test \"starts one\" { true; }" > "$d/viahelper.bats"
    run loaded_helpers "$d/viahelper.bats"
    [ "$output" = "$d/mgr-helper.bash" ]
    TESTS="$d" run manager_suites
    [ "$output" = "$d/viahelper.bats" ]
    run isolation_problems "$d/viahelper.bats"
    [ "${#lines[@]}" -eq 2 ]
    rm -rf "$d"
}

@test "a floor set in a loaded helper, in the equivalent spellings, isolates the suite" {
    # the assignment and the export on separate lines, the unset with a second variable: all accepted
    local d; d="$(mktemp -d)"
    printf '%s\n' 'state_floor() {' '    unset OTHER_VAR ROMP_STATE_DIR' \
        '    XDG_STATE_HOME="$TEST_DIR/state"; export XDG_STATE_HOME' '}' > "$d/floor.bash"
    printf '%s\n' '#!/usr/bin/env bats' 'load floor' 'setup() {' '    TEST_DIR="$(mktemp -d)"' \
        '    state_floor' \
        '    MGR="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp-manager"' '}' \
        '@'"test \"starts one\" { node \"\$MGR\" up; }" > "$d/isolated.bats"
    TESTS="$d" run manager_suites
    [ "$output" = "$d/isolated.bats" ]
    run isolation_problems "$d/isolated.bats"
    [ -z "$output" ]
    # and the other accepted spelling: ROMP_STATE_DIR exported to a test path, unquoted, no XDG line
    printf '%s\n' '#!/usr/bin/env bats' 'setup() {' '    TEST_DIR="$(mktemp -d)"' \
        '    ROMP_STATE_DIR=$TEST_DIR/state' '    export ROMP_STATE_DIR' \
        '    MGR="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp-manager"' '}' \
        '@'"test \"starts one\" { node \"\$MGR\" up; }" > "$d/rompdir.bats"
    run isolation_problems "$d/rompdir.bats"
    [ -z "$output" ]
    rm -rf "$d"
}

@test "a floor set only inside a test, or only mentioned in a comment, does not isolate the suite" {
    local d; d="$(mktemp -d)"
    printf '%s\n' '#!/usr/bin/env bats' '# export XDG_STATE_HOME="$TEST_DIR/state" would go here' 'setup() {' \
        '    TEST_DIR="$(mktemp -d)"' \
        '    MGR="$(cd "$(dirname "$BATS_TEST_FILENAME")/../bin" && pwd)/romp-manager"' '}' \
        '@'"test \"starts one\" { export XDG_STATE_HOME=\"\$TEST_DIR/state\"; unset ROMP_STATE_DIR; node \"\$MGR\" up; }" \
        > "$d/late.bats"
    TESTS="$d" run manager_suites
    [ "$output" = "$d/late.bats" ]
    run isolation_problems "$d/late.bats"
    [ "${#lines[@]}" -eq 2 ]
    rm -rf "$d"
}
