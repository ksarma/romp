#!/usr/bin/env bats

# .gitleaks.toml and the credential scan, exercised against the REAL scanner
# (tests/install-sh.bats stubs it, because what it tests there is the hook's
# wiring; what is under test here is the config itself, and what a push through
# the hook looks like when gitleaks really runs, which a stub cannot check).
#
# Skipped when gitleaks is not installed, so a clone that never wanted the
# scanner still runs a green suite; CI installs it and is the arbiter, and
# sets ROMP_GITLEAKS_REQUIRE=1 so that an absence there fails with the reason
# instead of skipping (see setup). ROMP_GITLEAKS names a binary that is not on
# PATH, as it does for the hook.
#
# Nothing in this file may contain a credential-shaped literal: gitleaks scans
# this repo, and a fixture secret written out longhand would flag the very test
# that proves the scanner works. The probes below are assembled at run time and
# only ever exist in a temp file.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

load git-hermetic

setup() {
    git_hermetic
    # The hook's credential feed reads GIT_DIFF_OPTS as main's git log does (round 12n): a runner's value would move its hunks.
    unset GIT_DIFF_OPTS
    GL="${ROMP_GITLEAKS:-$(command -v gitleaks || true)}"
    if [ -z "$GL" ] || [ ! -x "$GL" ]; then
        # ROMP_GITLEAKS_REQUIRE=1 makes the absence a failure naming the reason, not a skip:
        # CI's Linux Shell job installs the pinned gitleaks in the step before it runs bats
        # and sets the switch, so a skip there would report a broken install as a green skip
        # per case (the stance ROMP_SERVED_TESTS_REQUIRE takes in tests/conftest.py). Without
        # the switch the file skips, and a clone that never wanted the scanner stays green.
        # The reason names the property the test above keyed on: [ ! -x ] is true for a path
        # that is absent as well as for one that exists without the execute bit, and the two
        # have different remedies (a typo in ROMP_GITLEAKS, a chmod), so they are told apart.
        if [ -z "$GL" ]; then why="gitleaks is not on PATH and ROMP_GITLEAKS is unset or empty"
        elif [ ! -e "$GL" ]; then why="ROMP_GITLEAKS names $GL, which does not exist"
        else why="ROMP_GITLEAKS names $GL, which is not executable"; fi
        if [ "${ROMP_GITLEAKS_REQUIRE:-}" = "1" ]; then
            echo "ROMP_GITLEAKS_REQUIRE=1: $why, and this runner must have it: the arbiter runner" \
                "installs the pinned gitleaks before bats, so its absence here is a broken install," \
                "not a missing tool" >&2
            return 1
        fi
        skip "gitleaks not installed"
    fi
    TEST_DIR="$(mktemp -d)"
    CFG="$ROMP_DIR/.gitleaks.toml"
}

teardown() { rm -rf "${TEST_DIR:-}"; }

# Exit 2 is a finding, 1 is gitleaks failing (an unreadable config, say), so a
# case that expects a finding cannot pass on a scanner that never scanned.
scan() { "$GL" dir "$TEST_DIR" --no-banner --redact --exit-code 2 --config "$CFG"; }

# ghp_ + 36 chars, assembled so the literal never lives in a tracked file.
probe_token() { printf 'gh%s_%s%s' p "$(printf '0123456789%.0s' 1 2 3)" abcdef; }

@test "the config parses and the committed tree is clean" {
    # HEAD's tracked content, not the working tree: a scratch file or an ignored
    # build product in a developer's clone is not the repo's to answer for.
    mkdir "$TEST_DIR/tree"
    git -C "$ROMP_DIR" archive HEAD | tar -x -C "$TEST_DIR/tree"
    run "$GL" dir "$TEST_DIR/tree" --no-banner --redact --exit-code 2 --config "$CFG"
    [ "$status" -eq 0 ]
}

# The history case below reads the commits this branch adds over main, not every commit HEAD can
# reach. Until 2026-10-02 it read all of HEAD's history, so its cost grew with every commit: about
# 155 s at 13,762 commits on a development box at load 17, and past the 180 s that CI's Run bats
# step allows a test (BATS_TEST_TIMEOUT) on a busier one. The commits main already holds are read
# by CI's secret-scan job, which checks out all of history (fetch-depth: 0) and scans it with --all
# on every PR and every push to main, so this case owes only what the branch adds.
#
# history_scan_range <repo> sets two variables: scan_revs, the revisions the case hands git log
# through gitleaks' --log-opts (empty when there is nothing to scan), and scan_scope, what they
# cover, in words, which the case prints. Its choice, in order:
# - A shallow clone: HEAD, the history the clone holds. Its graph stops at its depth, so a merge
#   base read from it need not be the base on the full graph, and branch commits past the cut lie
#   outside any range drawn from it. CI's Shell job checks out one commit (actions/checkout with no
#   fetch-depth), so there the case reads the tip alone, as it did before.
# - main is refs/remotes/origin/main when the clone has it, else refs/heads/main: main as this
#   clone knows it, in the order scripts/pr-orphans.sh reads it (origin/main is also the branch
#   scripts/batch.py lands on). The remote-tracking ref comes first because a local main is often
#   stale: work happens on branches, and nothing advances a local main until someone pulls into it.
#   Not upstream/main: in a fork that is the project's main, and a range over it would hold every
#   commit the fork carries; branches are cut from origin/main and land there, in the project's own
#   clones as in a fork. With neither ref, HEAD: the whole history, and the scope says why.
# - With main found, <base>..HEAD, base being what git merge-base HEAD <main> answers. Under
#   criss-cross merges git names one of several bases, and the range then also holds commits main
#   has: more than the branch adds, the safe side. A HEAD that shares no commit with main (an
#   unrelated history) gets HEAD, the whole history, and the scope says why.
# - HEAD the base itself (HEAD is main, or an ancestor of it): nothing. The case skips with the
#   scope as its reason rather than pass on a scan of no commits, which gitleaks exits 0 on.
# The case passes --diff-merges=first-parent over whichever range this chooses, so a merge on the
# branch (main merged in, a conflict resolved) is still read by its first-parent diff.
history_scan_range() {   # <repo>: sets scan_revs and scan_scope
    local repo=$1 head shallow ref name base rc n
    scan_revs="" scan_scope=""
    head=$(git -C "$repo" rev-parse --verify --quiet HEAD) || {
        echo "history_scan_range: $repo has no HEAD commit to scan from" >&2; return 1; }
    shallow=$(git -C "$repo" rev-parse --is-shallow-repository) || {
        echo "history_scan_range: whether $repo is a shallow clone could not be read" >&2; return 1; }
    case $shallow in
        true)
            n=$(git -C "$repo" rev-list --count HEAD) || return 1
            scan_revs=HEAD
            scan_scope="the history this shallow clone holds, $n commit(s) from HEAD: its graph stops at its depth, so no merge base with main is read from it"
            return 0 ;;
        false) ;;
        *) echo "history_scan_range: git rev-parse --is-shallow-repository answered \"$shallow\", neither true nor false" >&2
           return 1 ;;
    esac
    if git -C "$repo" rev-parse --verify --quiet refs/remotes/origin/main > /dev/null; then
        ref=refs/remotes/origin/main name=origin/main
    elif git -C "$repo" rev-parse --verify --quiet refs/heads/main > /dev/null; then
        ref=refs/heads/main name=main
    else
        n=$(git -C "$repo" rev-list --count HEAD) || return 1
        scan_revs=HEAD
        scan_scope="all of HEAD's history, $n commit(s): the clone has neither origin/main nor main to scope the scan by"
        return 0
    fi
    # merge-base exits 1 with no output when the two share no commit; any other failure is loud.
    base=$(git -C "$repo" merge-base HEAD "$ref") && rc=0 || rc=$?
    case $rc in
        0) ;;
        1) [ -z "$base" ] || { echo "history_scan_range: git merge-base HEAD $ref exited 1 and answered \"$base\"" >&2; return 1; }
           n=$(git -C "$repo" rev-list --count HEAD) || return 1
           scan_revs=HEAD
           scan_scope="all of HEAD's history, $n commit(s): HEAD shares no commit with $name, so there is no merge base to scope the scan by"
           return 0 ;;
        *) echo "history_scan_range: git merge-base HEAD $ref exited $rc" >&2; return 1 ;;
    esac
    if [ "$base" = "$head" ]; then
        if [ "$(git -C "$repo" rev-parse --verify "$ref")" = "$head" ]; then
            scan_scope="nothing to scan: HEAD is $name itself (${head:0:10}), so the branch adds no commits over main"
        else
            scan_scope="nothing to scan: HEAD (${head:0:10}) is an ancestor of $name, so the branch adds no commits over main"
        fi
        return 0
    fi
    n=$(git -C "$repo" rev-list --count "$base..HEAD") || return 1
    scan_revs="$base..HEAD"
    scan_scope="the $n commit(s) HEAD adds over $name (merge base ${base:0:10})"
}

@test "the commits this branch adds over main are clean, or the history the clone holds when no merge base with main is reachable" {
    # The range, and why it is not all of history: history_scan_range, above. Each merge by its
    # first-parent diff, as CI scans it. The scope goes to fd 3, which bats prints for a passing case
    # too, so every run says what it read.
    history_scan_range "$ROMP_DIR"
    [ -n "$scan_revs" ] || skip "$scan_scope"
    echo "# history scan: $scan_scope" >&3
    run "$GL" git "$ROMP_DIR" --no-banner --redact --exit-code 2 --config "$CFG" \
        --log-opts="$scan_revs --diff-merges=first-parent"
    [ "$status" -eq 0 ] || {
        echo "the history scan of $scan_scope did not pass (exit $status: 2 is a credential found, 1 gitleaks failing):"
        echo "$output"; false; }
}

@test "a planted credential is caught" {
    printf 'token = "%s"\n' "$(probe_token)" > "$TEST_DIR/probe.py"
    run scan
    [ "$status" -eq 2 ]
}

@test "a secret introduced only in a merge commit is caught by the history scan" {
    # `gitleaks git` runs `git log -p`, which shows NO diff for a merge commit by default, so a
    # credential added during a conflict resolution (present in neither parent, only the merge
    # tree) is scanned by nothing. CI passes --diff-merges=first-parent to close that;
    # this proves the flag actually surfaces the secret, against the real scanner.
    R="$TEST_DIR/repo"; mkdir -p "$R"
    git -C "$R" init -q
    git -C "$R" symbolic-ref HEAD refs/heads/main     # whatever init.defaultBranch says
    echo base > "$R/base"; git -C "$R" add -A && git -C "$R" commit -qm base
    git -C "$R" checkout -q -b side; echo sideline > "$R/s"; git -C "$R" add -A && git -C "$R" commit -qm side
    git -C "$R" checkout -q main
    echo mainline > "$R/m"; git -C "$R" add -A && git -C "$R" commit -qm main
    git -C "$R" merge -q --no-commit side
    # the secret lands ONLY in the merge tree, assembled at run time, never a tracked literal
    printf 'token = "%s"\n' "$(probe_token)" > "$R/evil.py"
    git -C "$R" add -A && git -C "$R" commit -qm "merge (evil)"

    # Default log-opts (the gap): the merge diff is never shown, so the secret is missed. A
    # scanner that shows merge diffs on its own makes the flag redundant, not wrong, so that is
    # a skip, not a failure.
    run "$GL" git "$R" --no-banner --redact --exit-code 2 --config "$CFG" --log-opts=--all
    [ "$status" -ne 1 ]
    [ "$status" -eq 0 ] || skip "this gitleaks reads merge diffs by default; the flag is redundant here"
    # With the flag CI passes, the first-parent diff surfaces it and the scan refuses.
    run "$GL" git "$R" --no-banner --redact --exit-code 2 --config "$CFG" \
        --log-opts="--all --diff-merges=first-parent"
    [ "$status" -eq 2 ]
}

@test "a credential in a path a committed .gitattributes marks -diff is caught by CI's configured history scan" {
    # `gitleaks git` runs `git log -p`, and git reads the checkout's .gitattributes for it: a path
    # marked -diff prints a `Binary files ... differ` line with no hunk, so a credential committed
    # there and removed in a later commit is text the history scan never sees, while the tree scan
    # reads HEAD, where the file is gone. CI's line carries an option for this. What is asserted is
    # that CI's CONFIGURED invocation, whatever its spelling, surfaces the secret: the arguments are
    # read from .github/workflows/ci.yml itself, not copied here, since a copied string stays green
    # while CI drifts.
    R="$TEST_DIR/repo"; mkdir -p "$R"
    git -C "$R" init -q
    git -C "$R" symbolic-ref HEAD refs/heads/main     # whatever init.defaultBranch says
    printf '*.cfg -diff\n' > "$R/.gitattributes"
    git -C "$R" add -A && git -C "$R" commit -qm "attributes"
    # the secret, assembled at run time, in a path the attribute covers
    printf 'token = "%s"\n' "$(probe_token)" > "$R/app.cfg"
    git -C "$R" add -A && git -C "$R" commit -qm "add app.cfg"
    git -C "$R" rm -q app.cfg && git -C "$R" commit -qm "remove app.cfg"
    # The premise, against this git: with the attribute at HEAD, the plain log shows no hunk for
    # the file, so a scanner reading that log has nothing to match.
    run git -C "$R" log -p --all
    [[ "$output" == *"Binary files"* ]]

    # CI's line, from the workflow's own text: exactly one `run: gitleaks git .` line is expected,
    # the credential-scan job's history step. Zero or two and the premise is gone, so say so. grep -c
    # prints 0 and exits 1 on no match, and bats runs under errexit, so without `|| true` the zero
    # case would stop at this assignment and never reach the message below.
    ci="$ROMP_DIR/.github/workflows/ci.yml"
    n=$(grep -cE '^[[:space:]]*run: gitleaks git \. ' "$ci" || true)
    [ "$n" -eq 1 ] || { echo "expected exactly one 'run: gitleaks git .' line in ci.yml, found $n"; false; }
    line=$(grep -E '^[[:space:]]*run: gitleaks git \. ' "$ci")
    # The arguments after `gitleaks git .`, split the way the runner's bash splits the run line:
    # `eval` into an array honours the quotes around the --log-opts value, so its several words stay
    # one argument, as they are in CI. Two positions belong to the checkout rather than the scanner:
    # `.` is the repository (the scratch one here) and `.gitleaks.toml` its config.
    eval "ci_args=(${line#*run: gitleaks git . })"
    for i in "${!ci_args[@]}"; do [ "${ci_args[$i]}" = ".gitleaks.toml" ] && ci_args[$i]="$CFG"; done
    # --exit-code 2 as in every case here: CI's line lets a finding and a scanner failure share exit
    # 1 (the step is red either way), and this test has to tell them apart.
    run "$GL" git "$R" "${ci_args[@]}" --exit-code 2
    [ "$status" -eq 2 ] || {
        echo "CI's history scan did not report the credential (exit $status):"; echo "$output"; false; }
    [[ "$output" == *"app.cfg"* ]]               # -v: the file to fix
    [[ "$output" != *"$(probe_token)"* ]]        # --redact: the value stays out of the log
}

@test "RFC 6455's example WebSocket key is excused" {
    # The handshake nonce the kernel's tests hand a fake request. High entropy by
    # protocol design, published in the RFC, not a credential.
    printf 'headers = {"Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ=="}\n' > "$TEST_DIR/probe.py"
    run scan
    [ "$status" -eq 0 ]
}

@test "the excuse is the EXACT nonce: a secret that merely contains it still trips" {
    # Unanchored, the allowlist regex forgives any secret with the nonce as a substring. Anchored
    # (^...$) it excuses only the one published value. Assembled from pieces at run time: the nonce
    # itself is the excused value (fine to appear), but the full SUPERSTRING as one tracked literal
    # would, correctly, trip the scan of this very repo.
    printf 'api_key = "%s%s%s"\n' "dGhlIHNhbXBsZSBub25jZQ==" "Zk8vQ2xhdWRl" "U2VjcmV0OTk5" > "$TEST_DIR/probe.py"
    run scan
    [ "$status" -eq 2 ]
}

@test "the excuse is the value, not the header: another WebSocket key still trips" {
    # The narrowness that makes the allowlist safe: it forgives one published
    # string, not every line that mentions Sec-WebSocket-Key. Halves, because a
    # whole one written here would trip the scan of this very repo.
    printf 'headers = {"Sec-WebSocket-Key": "%s%s"}\n' "9kLm2QpXvTz7" "RbNc4WdY1A==" > "$TEST_DIR/probe.py"
    run scan
    [ "$status" -eq 2 ]
}

# ── the history case's range, on synthetic repositories ───────────────────
# history_scan_range's choices, each on a repository built here, and the history case itself run
# end to end over some of them as a child bats (history_case_over). The probe is probe_token's,
# written at run time, as everywhere in this file.

# A synthetic repository: main's first commit, with HEAD on main whatever init.defaultBranch says.
# Files are added by name, never with add -A, so the copy of this suite that history_case_over puts
# in the tree stays out of every commit.
synth_repo() {   # <dir>
    git init -q "$1"
    git -C "$1" symbolic-ref HEAD refs/heads/main
    synth_commit "$1" base.txt base "main: first"
}

synth_commit() {   # <repo> <file> <line> <message>: the file holding the line, committed
    printf '%s\n' "$3" > "$1/$2"
    git -C "$1" add -- "$2"
    git -C "$1" commit -qm "$4"
}

synth_probe() {   # <repo> <file> <message>: the probe in the file, committed
    printf 'token = "%s"\n' "$(probe_token)" > "$1/$2"
    git -C "$1" add -- "$2"
    git -C "$1" commit -qm "$3"
}

# The history case run over a synthetic repository, by a child bats as tests/gitleaks-require.bats
# runs this suite. This suite (the file bats is running, so a scratch copy under test copies
# itself), its git-hermetic helper and the config are copied into the repository's tree, untracked
# and so in none of its commits. That makes the copy's ROMP_DIR the synthetic repository, so the
# case's own body, range and flags are what run. The filter matches the history case's title alone
# (no case in this section begins with it), and each caller checks the plan line says one case ran.
history_case_over() {   # <repo>
    mkdir -p "$1/tests"
    cp "$BATS_TEST_FILENAME" "$1/tests/gitleaks-config.bats"
    cp "$BATS_TEST_DIRNAME/git-hermetic.bash" "$1/tests/"
    cp "$CFG" "$1/.gitleaks.toml"
    ROMP_GITLEAKS="$GL" bats --filter '^the commits this branch adds over main' "$1/tests/gitleaks-config.bats" < /dev/null
}

# The child's TAP line for the history case: exactly one line that begins "ok 1" or "not ok 1"
# with the case's title words, printed. Fails when there is not exactly one.
history_case_line() {   # <the child's output>
    local l n=0 hit=""
    while IFS= read -r l; do
        case $l in
            "ok 1 the commits this branch adds over main"* | "not ok 1 the commits this branch adds over main"*) n=$((n + 1)); hit=$l ;;
        esac
    done <<< "$1"
    [ "$n" -eq 1 ] || { echo "expected one TAP line for the history case in the child's output, found $n:" >&2; echo "$1" >&2; return 1; }
    printf '%s\n' "$hit"
}

@test "the history case over a synthetic main: a credential in a commit the branch adds is refused (exit 2), and the same branch without it passes, naming the commits it read" {
    R="$TEST_DIR/repo"; synth_repo "$R"
    synth_commit "$R" main2.txt two "main: second"
    git -C "$R" checkout -q -b clean
    synth_commit "$R" f1.txt one "branch: first"
    synth_commit "$R" f2.txt two "branch: second"
    git -C "$R" checkout -q -b probe main
    synth_commit "$R" f1.txt one "branch: first"
    synth_probe "$R" probe.py "branch: the probe"
    main=$(git -C "$R" rev-parse main)
    # The range history_scan_range picks, scanned with the case's flags.
    history_scan_range "$R"
    [ "$scan_revs" = "$main..HEAD" ] || { echo "expected the range $main..HEAD, got \"$scan_revs\" ($scan_scope)"; false; }
    run "$GL" git "$R" --no-banner --redact --exit-code 2 --config "$CFG" --log-opts="$scan_revs --diff-merges=first-parent"
    [ "$status" -eq 2 ] || { echo "the scoped scan did not report the probe the branch adds (exit $status):"; echo "$output"; false; }
    # The case itself, end to end: refused, with the scanner's exit and the scope in its output.
    run history_case_over "$R"
    [ "$status" -eq 1 ] && [ "${lines[0]}" = "1..1" ] || { echo "expected the history case to fail alone (exit 1, plan 1..1), got exit $status:"; echo "$output"; false; }
    line=$(history_case_line "$output")
    [[ "$line" == "not ok 1 "* ]] || { echo "the history case did not fail: $line"; echo "$output"; false; }
    [[ "$output" == *"the history scan of the 2 commit(s) HEAD adds over main (merge base ${main:0:10}) did not pass (exit 2:"* ]] || {
        echo "the failure does not name the scope and exit 2:"; echo "$output"; false; }
    [[ "$output" != *"$(probe_token)"* ]]        # --redact: the value stays out of the log
    # The same shape without the probe passes, and its output says what it read.
    git -C "$R" checkout -q clean
    run history_case_over "$R"
    [ "$status" -eq 0 ] && [ "${lines[0]}" = "1..1" ] || { echo "expected the history case to pass alone, got exit $status:"; echo "$output"; false; }
    line=$(history_case_line "$output")
    [[ "$line" == "ok 1 "* && "$line" != *" # skip "* ]] || { echo "the history case did not pass: $line"; echo "$output"; false; }
    [[ "$output" == *"# history scan: the 2 commit(s) HEAD adds over main (merge base ${main:0:10})"* ]] || {
        echo "the passing case does not say what it read:"; echo "$output"; false; }
}

@test "the history case over a synthetic main: a credential typed only into a merge on the branch (main merged in, the probe added while resolving it) is refused through the merge's first-parent diff" {
    R="$TEST_DIR/repo"; synth_repo "$R"
    git -C "$R" checkout -q -b feature
    synth_commit "$R" f1.txt one "branch: first"
    git -C "$R" checkout -q main
    synth_commit "$R" main2.txt two "main: second"
    git -C "$R" checkout -q feature
    git -C "$R" merge -q --no-commit main
    # the probe lands ONLY in the merge's tree, in neither parent
    printf 'token = "%s"\n' "$(probe_token)" > "$R/evil.py"
    git -C "$R" add -- evil.py
    git -C "$R" commit -qm "branch: main merged in, the probe added in the resolution"
    main=$(git -C "$R" rev-parse main)
    # main's tip is the merge base now, so the range is the branch's first commit and the merge.
    history_scan_range "$R"
    [ "$scan_revs" = "$main..HEAD" ] || { echo "expected the range $main..HEAD, got \"$scan_revs\" ($scan_scope)"; false; }
    # The premise, over the same range: without the flag git log shows the merge no diff and the
    # scan finds nothing. A gitleaks that reads merge diffs by default makes the flag redundant, not
    # wrong, so that is a skip, as in the merge case above.
    run "$GL" git "$R" --no-banner --redact --exit-code 2 --config "$CFG" --log-opts="$scan_revs"
    [ "$status" -ne 1 ]
    [ "$status" -eq 0 ] || skip "this gitleaks reads merge diffs by default; the flag is redundant here"
    run "$GL" git "$R" --no-banner --redact --exit-code 2 --config "$CFG" --log-opts="$scan_revs --diff-merges=first-parent"
    [ "$status" -eq 2 ] || { echo "the scoped scan did not report the probe in the merge (exit $status):"; echo "$output"; false; }
    run history_case_over "$R"
    [ "$status" -eq 1 ] && [ "${lines[0]}" = "1..1" ] || { echo "expected the history case to fail alone (exit 1, plan 1..1), got exit $status:"; echo "$output"; false; }
    line=$(history_case_line "$output")
    [[ "$line" == "not ok 1 "* ]] || { echo "the history case did not fail: $line"; echo "$output"; false; }
    [[ "$output" == *"the history scan of the 2 commit(s) HEAD adds over main (merge base ${main:0:10}) did not pass (exit 2:"* ]] || {
        echo "the failure does not name the scope and exit 2:"; echo "$output"; false; }
}

@test "the history case over a synthetic main: a credential main already holds, below the branch's base, is outside the range, so the case passes naming the commits it read (CI's secret-scan job reads main's history)" {
    R="$TEST_DIR/repo"; synth_repo "$R"
    synth_probe "$R" probe.py "main: the probe"
    git -C "$R" rm -q probe.py
    git -C "$R" commit -qm "main: the probe removed"
    git -C "$R" checkout -q -b feature
    synth_commit "$R" f1.txt one "branch: first"
    main=$(git -C "$R" rev-parse main)
    # The probe is in main's history, where a scan of all of HEAD's history (this case before
    # 2026-10-02) reports it, so the pass below is the range at work, not a probe nothing finds.
    run "$GL" git "$R" --no-banner --redact --exit-code 2 --config "$CFG" --log-opts="HEAD --diff-merges=first-parent"
    [ "$status" -eq 2 ] || { echo "a scan of all of HEAD's history did not report the probe in main's history (exit $status):"; echo "$output"; false; }
    run history_case_over "$R"
    [ "$status" -eq 0 ] && [ "${lines[0]}" = "1..1" ] || { echo "expected the history case to pass alone, got exit $status:"; echo "$output"; false; }
    line=$(history_case_line "$output")
    [[ "$line" == "ok 1 "* && "$line" != *" # skip "* ]] || { echo "the history case did not pass: $line"; echo "$output"; false; }
    [[ "$output" == *"# history scan: the 1 commit(s) HEAD adds over main (merge base ${main:0:10})"* ]] || {
        echo "the passing case does not say what it read:"; echo "$output"; false; }
}

@test "history_scan_range: <base>..HEAD over origin/main when the clone has it, ahead of a stale local main, and over the local main when that is the only one" {
    R="$TEST_DIR/repo"; synth_repo "$R"
    c1=$(git -C "$R" rev-parse HEAD)
    # A commit main gained on the remote and the clone fetched, never pulled into its local main.
    git -C "$R" checkout -q -b fetched
    synth_commit "$R" main2.txt two "main: second"
    c2=$(git -C "$R" rev-parse HEAD)
    git -C "$R" update-ref refs/remotes/origin/main "$c2"
    git -C "$R" checkout -q -b feature
    git -C "$R" branch -q -D fetched
    synth_commit "$R" f1.txt one "branch: first"
    [ "$(git -C "$R" rev-parse refs/heads/main)" = "$c1" ]     # the local main is stale
    history_scan_range "$R"
    [ "$scan_revs" = "$c2..HEAD" ] || { echo "expected $c2..HEAD over origin/main, got \"$scan_revs\" ($scan_scope)"; false; }
    [ "$scan_scope" = "the 1 commit(s) HEAD adds over origin/main (merge base ${c2:0:10})" ] || { echo "scope: $scan_scope"; false; }
    # The remote-tracking ref gone: the local main stands for main.
    git -C "$R" update-ref -d refs/remotes/origin/main
    history_scan_range "$R"
    [ "$scan_revs" = "$c1..HEAD" ] || { echo "expected $c1..HEAD over the local main, got \"$scan_revs\" ($scan_scope)"; false; }
    [ "$scan_scope" = "the 2 commit(s) HEAD adds over main (merge base ${c1:0:10})" ] || { echo "scope: $scan_scope"; false; }
}

@test "history_scan_range: in a shallow clone, HEAD, the history the clone holds, even where a merge base can be read from it (CI's one-commit checkout of main among them)" {
    R="$TEST_DIR/repo"; synth_repo "$R"
    synth_commit "$R" main2.txt two "main: second"
    git -C "$R" checkout -q -b feature
    synth_commit "$R" f1.txt one "branch: first"
    # CI's shape on a push to main: one commit, origin/main the commit itself, so a merge base read
    # from the clone would make the range empty.
    S="$TEST_DIR/ci"
    git clone -q --depth 1 -b main "file://$R" "$S"
    [ "$(git -C "$S" rev-parse --is-shallow-repository)" = true ]
    [ "$(git -C "$S" merge-base HEAD refs/remotes/origin/main)" = "$(git -C "$S" rev-parse HEAD)" ]
    history_scan_range "$S"
    [ "$scan_revs" = HEAD ] || { echo "expected HEAD in the one-commit clone, got \"$scan_revs\" ($scan_scope)"; false; }
    [[ "$scan_scope" == "the history this shallow clone holds, 1 commit(s) from HEAD: "* ]] || { echo "scope: $scan_scope"; false; }
    # A deeper clone of the branch, where a merge base below HEAD can be read from the cut graph.
    S="$TEST_DIR/deep"
    git clone -q --depth 2 --no-single-branch -b feature "file://$R" "$S"
    [ "$(git -C "$S" rev-parse --is-shallow-repository)" = true ]
    [ "$(git -C "$S" merge-base HEAD refs/remotes/origin/main)" = "$(git -C "$R" rev-parse main)" ]
    history_scan_range "$S"
    [ "$scan_revs" = HEAD ] || { echo "expected HEAD in the shallow clone of the branch, got \"$scan_revs\" ($scan_scope)"; false; }
    [[ "$scan_scope" == "the history this shallow clone holds, "* ]] || { echo "scope: $scan_scope"; false; }
}

@test "history_scan_range: with neither origin/main nor main, or a HEAD that shares no commit with main, HEAD, the whole history, and the scope says why" {
    R="$TEST_DIR/repo"; git init -q "$R"
    git -C "$R" symbolic-ref HEAD refs/heads/trunk
    synth_commit "$R" a.txt a "trunk: first"
    synth_commit "$R" b.txt b "trunk: second"
    history_scan_range "$R"
    [ "$scan_revs" = HEAD ] || { echo "expected HEAD with no main ref, got \"$scan_revs\" ($scan_scope)"; false; }
    [ "$scan_scope" = "all of HEAD's history, 2 commit(s): the clone has neither origin/main nor main to scope the scan by" ] || { echo "scope: $scan_scope"; false; }
    U="$TEST_DIR/unrelated"; synth_repo "$U"
    git -C "$U" checkout -q --orphan other
    git -C "$U" rm -q --cached base.txt      # an orphan's index keeps main's files; this history holds none of them
    synth_commit "$U" o.txt o "other: first"
    [ "$(git -C "$U" rev-list --count HEAD)" -eq 1 ]
    history_scan_range "$U"
    [ "$scan_revs" = HEAD ] || { echo "expected HEAD for an unrelated history, got \"$scan_revs\" ($scan_scope)"; false; }
    [ "$scan_scope" = "all of HEAD's history, 1 commit(s): HEAD shares no commit with main, so there is no merge base to scope the scan by" ] || { echo "scope: $scan_scope"; false; }
}

@test "history_scan_range: HEAD is main, or an ancestor of it: an empty range and a stated scope, and the history case skips with that statement rather than pass on a scan of no commits" {
    R="$TEST_DIR/repo"; synth_repo "$R"
    c1=$(git -C "$R" rev-parse HEAD)
    synth_commit "$R" main2.txt two "main: second"
    c2=$(git -C "$R" rev-parse HEAD)
    history_scan_range "$R"
    [ -z "$scan_revs" ] || { echo "expected an empty range with HEAD on main, got \"$scan_revs\""; false; }
    [ "$scan_scope" = "nothing to scan: HEAD is main itself (${c2:0:10}), so the branch adds no commits over main" ] || { echo "scope: $scan_scope"; false; }
    # The case, end to end: a skip whose reason is that statement, not a pass.
    run history_case_over "$R"
    [ "$status" -eq 0 ] && [ "${lines[0]}" = "1..1" ] || { echo "expected the history case to run alone and not fail, got exit $status:"; echo "$output"; false; }
    line=$(history_case_line "$output")
    [[ "$line" == "ok 1 "*" # skip $scan_scope" ]] || { echo "the history case did not skip with the statement: $line"; echo "$output"; false; }
    git -C "$R" checkout -q --detach "$c1"
    history_scan_range "$R"
    [ -z "$scan_revs" ] || { echo "expected an empty range with HEAD an ancestor of main, got \"$scan_revs\""; false; }
    [ "$scan_scope" = "nothing to scan: HEAD (${c1:0:10}) is an ancestor of main, so the branch adds no commits over main" ] || { echo "scope: $scan_scope"; false; }
}

# ── the hook, with the real scanner ────────────────────────────────────────
# A clone with the hook installed and a bare remote, pushed to for real. No
# denylist (the identifier scan stands down) and no .gitleaks.toml (default
# rules): what is under test is the hook running gitleaks, not the config.
hook_repo() {
    export XDG_CONFIG_HOME="$TEST_DIR/cfg"
    export ROMP_GITLEAKS="$GL"
    unset ROMP_NO_GITLEAKS
    git init -q "$TEST_DIR/remote.git" --bare
    WORK="$TEST_DIR/work"
    git init -q "$WORK"
    git -C "$WORK" symbolic-ref HEAD refs/heads/main
    mkdir -p "$WORK/.git/hooks"
    cp "$ROMP_DIR/.githooks/pre-push" "$WORK/.git/hooks/pre-push"
    git -C "$WORK" remote add origin "$TEST_DIR/remote.git"
    echo base > "$WORK/base.txt"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm base
    git -C "$WORK" push -q origin HEAD:main
}

@test "through the hook: a pushed credential is refused, its file named, its value redacted" {
    hook_repo
    printf 'token = "%s"\n' "$(probe_token)" > "$WORK/probe.py"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm probe
    sha="$(git -C "$WORK" rev-parse HEAD)"
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -ne 0 ]
    [[ "$output" == *"gitleaks found a credential"* ]]
    # The file to fix and the rule that matched, on the hook's own line: gitleaks scans numbered
    # pieces, so -v's File names a piece, and the hook names the commit and file from its index.
    [[ "$output" == *"romp pre-push: commit ${sha:0:10} ADDS a credential (github-pat) in: probe.py"* ]]
    [[ "$output" != *"$(probe_token)"* ]]        # --redact: the value stays out of the terminal
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse main)" != "$(git -C "$WORK" rev-parse HEAD)" ]
}

@test "through the hook: a force-push over a remote tip this clone never fetched is refused" {
    # Another clone moves the branch; this one force-pushes a secret without
    # fetching. The hook's listing of a range with a sha this clone cannot
    # resolve fails, so the hook has to fall back to a range it can.
    hook_repo
    git clone -q -b main "$TEST_DIR/remote.git" "$TEST_DIR/other"
    echo other > "$TEST_DIR/other/other.txt"
    git -C "$TEST_DIR/other" add -A && git -C "$TEST_DIR/other" commit -qm other
    git -C "$TEST_DIR/other" push -q origin HEAD:main
    printf 'token = "%s"\n' "$(probe_token)" > "$WORK/probe.py"
    git -C "$WORK" add -A && git -C "$WORK" commit -qm probe
    run git -C "$WORK" push --force origin HEAD:main
    [ "$status" -ne 0 ]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse main)" = "$(git -C "$TEST_DIR/other" rev-parse HEAD)" ]
}

# ── round 9d: the scanner in the hook's directory mode ─────────────────────
# Since round 9 the hook reads the lines a push adds itself, writes them into numbered files
# (pieces) of at most 98,304 bytes, since round 12d one hunk's added lines to a piece, a piece
# beginning with a line holding ~ only where gitleaks' type check would skip it without one, and
# runs `gitleaks dir .` from inside their directory, so gitleaks runs no git. Each case below pins
# one premise of that
# design against the installed scanner, G2 with the cap read from the hook's awk text and G4 with
# the names the hook's own piecing awk gives its copies; tests/pre-push-hook.bats drives the hook
# itself, through pushes.

scan_pieces() {   # <piece directory> [gitleaks options...]: scanned from inside it, as the hook runs it
    local d=$1
    shift
    (cd "$d" && "$GL" dir . --no-banner --no-color --redact --exit-code 2 "$@")
}

# n distinct github-pat shaped lines from a fixed seed, assembled at run time like every probe here.
dense_tokens() {
    awk -v n="$1" 'BEGIN { srand(7); a = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        for (i = 0; i < n; i++) { s = ""; for (j = 0; j < 36; j++) s = s substr(a, int(rand() * 62) + 1, 1); print "gh" "p_" s } }'
}

# The five default rules that key on a file's path (the same five in gitleaks 8.28.0 and 8.30.1),
# each with a probe it reports (path_rule_probe). The names the hook gives their copies are read
# from the hook (hook_copy_names, above G4), never spelled here.
PATH_RULES="pkcs12-file nuget-config-password kubernetes-secret-yaml hashicorp-tf-password freemius-secret-key"

path_rule_probe() {
    case $1 in
        pkcs12-file) printf 'not a keystore: this rule reads the name alone\n' ;;
        nuget-config-password)
            printf '<configuration>\n  <packageSourceCredentials>\n    <feed>\n      <add key="Username" value="builder" />\n      <add key="Clear%sPassword" value="%s" />\n    </feed>\n  </packageSourceCredentials>\n</configuration>\n' \
                Text "Qz7$(printf 'w%.0s' 1 2)Kp9Lm2Xv" ;;
        kubernetes-secret-yaml)
            printf 'apiVersion: v1\nkind: %s\nmetadata:\n  name: probe\ndata:\n  password: %s%s\n' Secret "cHJvYmVw" "YXNzd29yZDEy" ;;
        hashicorp-tf-password) printf 'resource "x" "y" {\n  pass%s = "%s%s"\n}\n' word "Zq8wKp" "2Lm9Xv" ;;
        freemius-secret-key) printf "<?php\n\$fs = array(\n  'secret_%s' => 'sk_%s%s',\n);\n" key "Qz7wKp9Lm2Xv" "Rb4Nc8Wd1Yt6Hs3Jf" ;;
    esac
}

@test "round 9d, G1: the value excuse holds in directory mode over a piece named by number, as the hook scans it" {
    # A piece carries no real path, so .gitleaks.toml's excuse has only the value to key on, and it
    # must hold there: RFC 6455's nonce in a piece of one text line, framed as the hook frames a
    # text piece since round 12d (no ~ line), gives no finding under the config and one under the
    # default rules (so the config is what excuses it), and a secret that contains the nonce gives
    # one finding under the config.
    mkdir "$TEST_DIR/p"
    printf 'headers = {"Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ=="}\n' > "$TEST_DIR/p/1"
    run scan_pieces "$TEST_DIR/p" --config "$CFG"
    [ "$status" -eq 0 ] || { echo "the nonce was not excused in directory mode (exit $status):"; echo "$output"; false; }
    unset GITLEAKS_CONFIG GITLEAKS_CONFIG_TOML   # no --config below: the default rules, whatever the environment names
    run scan_pieces "$TEST_DIR/p"
    [ "$status" -eq 2 ] || { echo "the default rules did not report the nonce, so the case proves nothing (exit $status):"; echo "$output"; false; }
    printf 'api_key = "%s%s%s"\n' "dGhlIHNhbXBsZSBub25jZQ==" "Zk8vQ2xhdWRl" "U2VjcmV0OTk5" > "$TEST_DIR/p/1"
    run scan_pieces "$TEST_DIR/p" --config "$CFG"
    [ "$status" -eq 2 ] || { echo "a secret containing the nonce was excused (exit $status):"; echo "$output"; false; }
    [[ "$output" =~ leaks\ found:\ ([0-9]+) ]] && [ "${BASH_REMATCH[1]}" -eq 1 ] || {
        echo "expected one finding for the secret containing the nonce:"; echo "$output"; false; }
}

# One of the piecing constants, CAP or V, read from the hook's own awk text (the line of
# CRED_PIECES_AWK that assigns CAP, V and LW), never restated here, so a case keyed on it moves with
# the hook (round 10b, from the round 9 rulings' group C). Exactly one assignment of the name to a
# number is expected in the hook; none (a rename, a move) or two (a second site) and the premise is
# gone, so say so.
hook_constant() {   # <CAP | V>
    local hook="$ROMP_DIR/.githooks/pre-push" pat n
    pat="(^|[;[:space:]])$1 = [0-9]+([;[:space:]]|\$)"
    n=$(grep -cE "$pat" "$hook" || true)
    [ "$n" -eq 1 ] || { echo "expected exactly one '$1 = <number>' assignment in the hook's awk text ($hook), found $n" >&2; return 1; }
    grep -E "$pat" "$hook" | sed -E "s/^(.*[;[:space:]])?$1 = ([0-9]+).*\$/\\2/"
}

@test "round 9d, G2: a piece of the hook's cap, CAP bytes read from its awk line, is read whole: each of its dense distinct tokens is found (red for a CAP of 125,009 bytes or more, CAP=130000 among them)" {
    # The hook caps a piece at CAP bytes (98,304 at this writing) because gitleaks reads a file of
    # up to 100,000 bytes in one chunk and a larger one in chunks, missing a match that crosses a
    # cut (in a 200,000-byte file of these lines 8.28.0 and 8.30.1 miss 3 of 4,878). A piece of
    # exactly the cap, packed with distinct github-pat shaped lines from its first byte, as the hook
    # writes a text piece since round 12d (no ~ line, which it writes only ahead of leading bytes
    # gitleaks' type check would skip), must be read whole: every token found, and the byte figure
    # the piece's size. A later gitleaks that reads files in smaller chunks turns this red, and the
    # hook's cap moves with it.
    # CAP is read from the hook (hook_constant; round 10b, from the round 9 rulings' group C): until
    # then this case built a piece of a restated 98,304 bytes and stayed green whatever CAP the hook
    # held. Its range, measured on this layout under 8.28.0 and 8.30.1: gitleaks' first chunk is its
    # 100,000-byte read plus a peek of up to 25,000 bytes for a blank line, and this piece holds
    # none, so a CAP up to 125,008 is still read whole (green) and a CAP of 125,009 or more puts the
    # token that starts at byte 124,968 across the cut (red, that token missed; re-derived in round
    # 12d2 for the piece without the ~ line, which moved each token two bytes, from 125,010 and
    # 125,011 and byte 124,970, by execution under 8.28.0 and 8.30.1). The band above 100,000 that
    # stays green here belongs to the round 10b cap pin below and to the blank-line witness it
    # names.
    cap=$(hook_constant CAP)
    mkdir "$TEST_DIR/p"
    n=$(( cap / 41 ))                             # 41 bytes a line, from the piece's first byte
    pad=$(( cap - n * 41 ))
    { dense_tokens "$n"; [ "$pad" -eq 0 ] || printf '%*s\n' $(( pad - 1 )) '' | tr ' ' x; } > "$TEST_DIR/p/1"
    [ "$(( $(wc -c < "$TEST_DIR/p/1") ))" -eq "$cap" ]
    [ "$(( $(grep -c '^gh' "$TEST_DIR/p/1") ))" -eq "$n" ]
    [ "$(( $(grep '^gh' "$TEST_DIR/p/1" | sort -u | wc -l) ))" -eq "$n" ]   # distinct
    run scan_pieces "$TEST_DIR/p" --config "$CFG"
    [ "$status" -eq 2 ] || { echo "no finding in the dense piece (exit $status):"; echo "$output"; false; }
    [[ "$output" == *"scanned ~$cap bytes"* ]] || { echo "the byte figure is not the piece's $cap bytes (the hook's CAP):"; echo "$output"; false; }
    [[ "$output" =~ leaks\ found:\ ([0-9]+) ]] && [ "${BASH_REMATCH[1]}" -eq "$n" ] || {
        echo "expected all $n tokens found in a piece of the cap:"; echo "$output"; false; }
}

@test "round 9d, G3: a piece that begins with an archive or document signature is read only behind the hook's ~ line" {
    # gitleaks skips a file whose first bytes carry a zip, gzip or PDF signature: it counts 0 bytes
    # and finds nothing below the signature. A hunk's added lines can begin that way, so a piece
    # whose leading bytes carry such a signature begins with a line holding ~, which moves the
    # signature off byte 0 (since round 12d the hook writes that line only there, its type table
    # deciding, and tests/pre-push-hook.bats derives the table against the running gitleaks). Both
    # halves, per signature: without the ~ line, 0 bytes and no finding; with it, the piece's size
    # and the token found.
    mkdir "$TEST_DIR/p"
    for sig in zip gzip pdf; do
        case $sig in
            zip) head_bytes='PK\003\004\n' ;;
            gzip) head_bytes='\037\213\010\000\n' ;;
            pdf) head_bytes='%%PDF-1.4\n' ;;
        esac
        { printf "$head_bytes"; printf 'token = "%s"\n' "$(probe_token)"; } > "$TEST_DIR/p/1"
        run scan_pieces "$TEST_DIR/p" --config "$CFG"
        [ "$status" -eq 0 ] && [[ "$output" == *"scanned ~0 bytes"* ]] || {
            echo "$sig: gitleaks read a piece that begins with the signature (exit $status), so this premise of the ~ line moved:"; echo "$output"; false; }
        { printf '~\n'; printf "$head_bytes"; printf 'token = "%s"\n' "$(probe_token)"; } > "$TEST_DIR/p/1"
        size=$(( $(wc -c < "$TEST_DIR/p/1") ))
        run scan_pieces "$TEST_DIR/p" --config "$CFG"
        [ "$status" -eq 2 ] && [[ "$output" == *"scanned ~$size bytes"* ]] || {
            echo "$sig: behind the ~ line the piece was not read whole with its token found (exit $status, $size bytes):"; echo "$output"; false; }
    done
}

# The hook's piecing awk, CRED_PIECES_AWK, read from the hook's own text and never restated here:
# the text between the quote that opens its one assignment and the next quote, which closes it (the
# hook holds the text in single quotes, so it contains none). No assignment opening a line (a
# rename, a move) or two, and the premise is gone, so say so.
hook_pieces_awk() {
    local hook="$ROMP_DIR/.githooks/pre-push" n text
    n=$(grep -c "^CRED_PIECES_AWK='" "$hook" || true)
    [ "$n" -eq 1 ] || { echo "expected exactly one line of the hook ($hook) opening CRED_PIECES_AWK='...', found $n" >&2; return 1; }
    text=$(< "$hook")
    text=${text#*$'\n'"CRED_PIECES_AWK='"}
    printf '%s' "${text%%"'"*}"
}

# The hook's piecing awk run as its feed runs it at a file's first added line: choose over the
# path, then newpiece, once for each path of the list, in order, so each path is one piece,
# numbered from 1. The hook's own code writes the index (piece, commit, path, closing field) and the
# path-scoped index (piece, the copy's name, the second copy's name, the rule, closing field), the
# files the hook's shell reads to write and scan the copies; it writes no piece file here, since a
# piece is written as its lines arrive and this driver gives none (and since round 12d a piece opens
# with the ~ line only ahead of leading bytes gitleaks' type check would skip).
# This driver adds one line per piece of what choose answered (sfx, the suffix it matched,
# lower-cased, and osfx, the same bytes as the path spells them), which G4's shape check composes
# its expected names from. Its status is the awk's: 1 when the list cannot be read.
hook_copy_names() {   # <list of paths> <piece directory> <index> <path-scoped index> <choose's answers>
    local text
    text=$(hook_pieces_awk) || return 1
    LC_ALL=C ROMP_LIST_FILE=$1 ROMP_PIECE_DIR=$2 ROMP_INDEX_FILE=$3 ROMP_PATH_INDEX_FILE=$4 ROMP_CHOSEN_FILE=$5 awk "$text"'
        BEGIN {
            list = ENVIRON["ROMP_LIST_FILE"]; dir = ENVIRON["ROMP_PIECE_DIR"]; chosen = ENVIRON["ROMP_CHOSEN_FILE"]
            idx = ENVIRON["ROMP_INDEX_FILE"]; pidx = ENVIRON["ROMP_PATH_INDEX_FILE"]
            pieces_begin(); sha = "TESTSHA"
            while ((r = (getline p < list)) > 0) { choose(p); forget(); newpiece(0); printf "%d\t%s\t%s\t.\n", pieces, sfx, osfx > chosen }
            shut()
            if (r < 0) exit 1
        }'
}

# One sample path per suffix the hook's path-scoped selection takes, each after the rule that
# suffix answers to: two for nuget.config (a bare basename and one with a stem), the case varied so
# the second copy's name shows the suffix as the path spells it, and ten paths so a piece's number
# reaches two digits (10, whose letters are ba). These are the case's inputs, not the names under
# test, and G4 checks each against gitleaks at its real path, as main's hook scanned it.
G4_SAMPLES='pkcs12-file keys/app.p12
pkcs12-file certs/Store.PFX
nuget-config-password src/NuGet.Config
nuget-config-password prod.nuget.config
kubernetes-secret-yaml deploy/secret.yaml
kubernetes-secret-yaml ci/Build.YML
hashicorp-tf-password infra/main.tf
hashicorp-tf-password infra/job.HCL
freemius-secret-key www/index.php
freemius-secret-key lib/Settings.PHP'

@test "round 9d, G4: each path-scoped rule fires under both names the hook gives a selected file's piece, read from the hook by running its piecing awk (choose, then newpiece) over a sample path per suffix: the copy's, in the piece's directory, and the second copy's, at the probe run's root, each in the shape the hook's texts state; none of the five fires under the piece's number alone" {
    # Five default rules key on the file's path. A piece named by number carries no such name, so
    # the hook's main run cannot fire them (until round 9 the hook ran gitleaks over git, where the
    # path is real, and they fired), and the hook scans each selected file's pieces again under
    # names that keep what those paths key on: a COPY in a directory named by the piece's number,
    # for the additive run (the piece's number and the suffix the selection matched, lower-cased,
    # or nuget.config alone; round 10b, from the round 9 rulings' group F), and since round 11b a
    # SECOND COPY at the probe run's root (romp-copy-, the piece's number in letters, a dot when the
    # suffix does not start with one, and the suffix as the path spells it; the round 10 rulings'
    # group A). Both
    # names are read from the hook: hook_copy_names runs the hook's own piecing awk over the sample
    # paths and the names come from the path-scoped index newpiece writes. Until round 11c this
    # case spelled the copy names itself (1.p12, nuget.config, 1.yaml and the rest) and stayed
    # green whatever names the hook gave its copies (the round 10 rulings, group F).
    # Checked, in this order:
    # - each sample is one piece of the index and one row of the path-scoped index, which names
    #   the rule the sample stands for (the probe run picks its probe by that field);
    # - each rule fires under each name, in the probe run's layout (the copy at <piece>/<name>,
    #   the second copy at the root), with the five rules alone as the hook runs them, the report
    #   read by file and rule; the same bytes at the sample's real path, where main's hook scanned
    #   them, fire too (so each sample is a path its rule keys on), and named by the piece's number
    #   alone they fire under none of the five;
    # - each name has the shape the header, the hook's comments and the rulings state and reason
    #   from, composed from choose's own answers (whose osfx must end the path, sfx its lower
    #   case). This check keys on that spelling, not on a property: a rename that keeps every rule
    #   firing (a prefix on the copy's name, another stem for the second copy's) is red here alone,
    #   and owes those texts the same change.
    # Red, each in a scratch copy of the hook under gitleaks 8.28.0 and 8.30.1 (round 11c): under
    # the stemless mutant of the copy's name (the piece's number with no suffix, so only the
    # nuget.config copies fire), under an "x" prefixed to it (the shape check) and under the second
    # copy renamed (romp-dup- for romp-copy-: the shape check). The executed proof that the hook's
    # own copies fire in a push stays in tests/pre-push-hook.bats: its round 10b cases titled
    # "round 10b (F, the coordinator's decision 4)" and its round 11b section's witnesses.
    local -a rules paths pcs cnames snames irow prow crow
    local l r p k piece cname sname prule fterm extra ipiece isha ipath iterm cpiece sfx osfx cterm want lt dot five
    five=${PATH_RULES// /,}
    while read -r r p; do rules+=("$r"); paths+=("$p"); done <<< "$G4_SAMPLES"
    printf '%s\n' "${paths[@]}" > "$TEST_DIR/paths"
    mkdir "$TEST_DIR/pieces" "$TEST_DIR/q" "$TEST_DIR/real" "$TEST_DIR/num"
    hook_copy_names "$TEST_DIR/paths" "$TEST_DIR/pieces" "$TEST_DIR/index" "$TEST_DIR/pindex" "$TEST_DIR/chosen" || {
        echo "the hook's piecing awk, run over the sample paths, failed"; false; }
    while IFS= read -r l; do irow+=("$l"); done < "$TEST_DIR/index"      # read loops, not mapfile: a stock mac's bash is 3.2
    while IFS= read -r l; do prow+=("$l"); done < "$TEST_DIR/pindex"
    while IFS= read -r l; do crow+=("$l"); done < "$TEST_DIR/chosen"
    [ "${#irow[@]}" -eq "${#paths[@]}" ] && [ "${#prow[@]}" -eq "${#paths[@]}" ] && [ "${#crow[@]}" -eq "${#paths[@]}" ] || {
        echo "the hook's piecing awk wrote ${#irow[@]} index rows, ${#prow[@]} path-scoped rows and ${#crow[@]} answers of choose for ${#paths[@]} sample paths, each of which its selection takes:"
        cat "$TEST_DIR/index" "$TEST_DIR/pindex"; false; }
    for k in "${!paths[@]}"; do
        IFS=$'\t' read -r ipiece isha ipath iterm <<< "${irow[$k]}"
        IFS=$'\t' read -r piece cname sname prule fterm extra <<< "${prow[$k]}"
        [ "$iterm" = . ] && [ "$ipiece" = "$((k + 1))" ] && [ "$ipath" = "${paths[$k]}" ] || {
            echo "index row $((k + 1)) is not piece $((k + 1)) for ${paths[$k]} with its closing field: ${irow[$k]}"; false; }
        [ "$fterm" = . ] && [ -z "$extra" ] && [ "$piece" = "$ipiece" ] || {
            echo "path-scoped index row $((k + 1)) is not piece $ipiece, the copy's name, the second copy's name, the rule and a closing field: ${prow[$k]}"; false; }
        [ "$prule" = "${rules[$k]}" ] || {
            echo "the path-scoped index names $prule for ${paths[$k]}, whose suffix answers to ${rules[$k]}"; false; }
        pcs+=("$piece"); cnames+=("$cname"); snames+=("$sname")
        mkdir -p "$TEST_DIR/q/$piece" "$TEST_DIR/real/$(dirname "${paths[$k]}")"
        path_rule_probe "${rules[$k]}" > "$TEST_DIR/q/$piece/$cname"
        path_rule_probe "${rules[$k]}" > "$TEST_DIR/q/$sname"
        path_rule_probe "${rules[$k]}" > "$TEST_DIR/real/${paths[$k]}"
        path_rule_probe "${rules[$k]}" > "$TEST_DIR/num/$piece"
    done
    printf '{{range .}}{{.File}}\t{{.RuleID}}\t.\n{{end}}' > "$TEST_DIR/tpl"
    run scan_pieces "$TEST_DIR/q" --config "$CFG" --enable-rule "$five" -f template --report-template "$TEST_DIR/tpl" -r "$TEST_DIR/q.rep"
    [ "$status" -eq 2 ] || { echo "no finding under the names the hook gives the copies (exit $status):"; echo "$output"; false; }
    run scan_pieces "$TEST_DIR/real" --config "$CFG" --enable-rule "$five" -f template --report-template "$TEST_DIR/tpl" -r "$TEST_DIR/real.rep"
    [ "$status" -eq 2 ] || { echo "no finding at the sample paths themselves (exit $status):"; echo "$output"; false; }
    for k in "${!paths[@]}"; do
        grep -qxF "${paths[$k]}"$'\t'"${rules[$k]}"$'\t.' "$TEST_DIR/real.rep" || {
            echo "${rules[$k]} did not fire at the sample's real path, ${paths[$k]}, so the sample is not one its rule keys on:"; cat "$TEST_DIR/real.rep"; false; }
        grep -qxF "${pcs[$k]}/${cnames[$k]}"$'\t'"${rules[$k]}"$'\t.' "$TEST_DIR/q.rep" || {
            echo "${rules[$k]} did not fire at ${pcs[$k]}/${cnames[$k]}, the copy's name the hook gives ${paths[$k]}:"; cat "$TEST_DIR/q.rep"; false; }
        grep -qxF "${snames[$k]}"$'\t'"${rules[$k]}"$'\t.' "$TEST_DIR/q.rep" || {
            echo "${rules[$k]} did not fire at ${snames[$k]}, the second copy's name the hook gives ${paths[$k]}:"; cat "$TEST_DIR/q.rep"; false; }
    done
    run scan_pieces "$TEST_DIR/num" --config "$CFG" --enable-rule "$five"
    [ "$status" -eq 0 ] || { echo "a path-scoped rule fired on a probe named by its piece's number alone (exit $status):"; echo "$output"; false; }
    # The shape check: the names as the texts state them, composed from choose's own answers.
    # It keys on spelling, not on firing. The refuter's x-prefix mutant (an "x" before the copy's
    # name) is equivalent for firing: the five default paths key on the end of a name, so an
    # x-prefixed copy name (x1.p12, xnuget.config, x5.yaml and the rest) fires every rule, under
    # both scanners, and the firing check above stays green under it. A rename of the second copy's
    # stem (romp-dup- for romp-copy-) keeps every rule firing the same way. So this check, whose
    # expected names come from choose's executed answers, is the one that turns red under either
    # (the round 10 rulings, the answer on round 11c's questions, 2026-09-26).
    for k in "${!paths[@]}"; do
        IFS=$'\t' read -r cpiece sfx osfx cterm <<< "${crow[$k]}"
        [ "$cterm" = . ] && [ "$cpiece" = "${pcs[$k]}" ] && [ -n "$osfx" ] && [[ "${paths[$k]}" == *"$osfx" ]] &&
            [ "$(printf '%s' "$osfx" | LC_ALL=C tr A-Z a-z)" = "$sfx" ] || {
            echo "choose answered \"${crow[$k]}\" for ${paths[$k]}: not its piece, the matched suffix lower-cased and the same bytes as the path ends in them"; false; }
        if [ "$sfx" = nuget.config ]; then want=$sfx; else want=${pcs[$k]}$sfx; fi
        [ "${cnames[$k]}" = "$want" ] || {
            echo "the hook names the copy of ${paths[$k]} ${cnames[$k]}, not $want, the shape its texts state (the piece's number and the"
            echo "suffix the selection matched, lower-cased, or nuget.config alone). This check keys on that spelling; the scan above"
            echo "pins the firing property, so a rename that keeps every rule firing owes the header and the comments the same change."
            false; }
        lt=$(printf '%s' "${pcs[$k]}" | tr 0123456789 abcdefghij)
        case $osfx in .*) dot="" ;; *) dot=. ;; esac
        want=romp-copy-$lt$dot$osfx
        [ "${snames[$k]}" = "$want" ] || {
            echo "the hook names the second copy of ${paths[$k]} ${snames[$k]}, not $want, the shape its texts state (romp-copy-, the"
            echo "piece's number in letters a to j, a dot when the suffix does not start with one, and the suffix as the path spells it). This check keys"
            echo "on that spelling; the scan above pins the firing property, so a rename that keeps every rule firing owes the header,"
            echo "the comments and the rulings' texts the same change."
            false; }
    done
}

# ── round 10b: the piecing constants' values ───────────────────────────────
# The round 9 rulings (group C, and the coordinator's decision 5) pin the hook's two piecing
# constants by value beside the witnesses that execute what each stands for: each is read from the
# hook's awk line (hook_constant, above), never restated, and each case's failure message says it
# guards the constant's value and names the executed witness that proves the property, a case in
# tests/pre-push-hook.bats' round 10b section that the pin also requires to be there, once. The
# cap's pin is red under CAP=110000 and CAP=130000 (G2 above under the second alone), the
# overlap's under V=4096 and V=2500.

# The count of cases in tests/pre-push-hook.bats whose title begins with round 10b (C, and the
# given words: a pin below names its executed witness by those words, and a witness renamed or
# gone would leave the pin's message pointing at nothing, so each pin requires exactly one.
witness_cases() {   # <the title's words after "round 10b (C, ">
    awk -v p="@test \"round 10b (C, $1" 'index($0, p) == 1 { n++ } END { print n + 0 }' "$ROMP_DIR/tests/pre-push-hook.bats"
}

@test "round 10b: the hook's CAP, read from its awk line, is at most 100,000 bytes, gitleaks' single read of a file (a value pin, red for any CAP above 100,000, CAP=110000 and CAP=130000 among them)" {
    # gitleaks reads a file of more than 100,000 bytes in chunks and misses a match across a cut,
    # so a piece must fit in one read. The executed proof of that property is elsewhere: the
    # blank-line witness in tests/pre-push-hook.bats (a PGP private key block whose blank line
    # falls at byte 100,000 of a one-piece reading, where gitleaks ends its first chunk, found
    # whole because the hook pieces the file at its CAP), red by publication under CAP=110000 and
    # CAP=130000, and G2 above for a CAP of 125,009 or more. The values just above 100,000 that the
    # witness cannot reach, which its title names as this pin's, are the band this pin backs up;
    # it guards the value only.
    cap=$(hook_constant CAP)
    [ "$cap" -le 100000 ] || {
        echo "the hook's CAP is $cap bytes, above 100,000, the most gitleaks reads of a file in one chunk."
        echo "This pin guards the constant's value; the executed proof of the property, a piece read whole, is the case"
        echo "'round 10b (C, the blank-line witness for the band from 100,000 to 125,000)' in tests/pre-push-hook.bats,"
        echo "with G2 in this file for a CAP of 125,009 or more."
        false; }
    n=$(witness_cases "the blank-line witness for the band from 100,000 to 125,000)")
    [ "$n" -eq 1 ] || {
        echo "the witness this pin names, 'round 10b (C, the blank-line witness for the band from 100,000 to 125,000)',"
        echo "is in tests/pre-push-hook.bats $n times, not once: renamed or gone, it leaves the message above pointing at nothing"
        false; }
}

@test "round 10b: the hook's V, read from its awk line, is the design value, 16,384 bytes (a value pin, red for any other V, V=4096 and V=2500 among them)" {
    # A continuation piece replays the last V bytes of its file's lines, and a long line's windows
    # overlap by V bytes, so a match that crosses a boundary lies whole in the next piece or window
    # when at most V of its bytes come before the boundary; the header states that bound at 16,384
    # bytes. The executed proof of the property is in tests/pre-push-hook.bats, placed by the V
    # those cases read from the hook: the property pin by the replay (a private key block with
    # exactly V of its bytes before a piece boundary between lines, refused) and the property pin
    # by windows (one of V + 1 bytes with exactly V before the end of a long line's first window,
    # refused). A witness placed by the hook's own V moves with it, so this pin is the one that
    # turns red when V itself changes; it guards the value only.
    v=$(hook_constant V)
    [ "$v" -eq 16384 ] || {
        echo "the hook's V is $v bytes, not the design value 16,384 that the header states as the overlap's bound."
        echo "This pin guards the constant's value; the executed proof of the property, the largest crossing match read"
        echo "whole, is the pair of cases 'round 10b (C, the property pin by the replay)' and 'round 10b (C, the property"
        echo "pin by windows)' in tests/pre-push-hook.bats, placed by the V they read from the hook."
        false; }
    for w in "the property pin by the replay)" "the property pin by windows)"; do
        n=$(witness_cases "$w")
        [ "$n" -eq 1 ] || {
            echo "the witness this pin names, 'round 10b (C, $w', is in tests/pre-push-hook.bats $n times, not once:"
            echo "renamed or gone, it leaves the message above pointing at nothing"
            false; }
    done
}
