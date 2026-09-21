#!/usr/bin/env bats

# .gitleaks.toml and the credential scan, exercised against the REAL scanner
# (tests/install-sh.bats stubs it, because what it tests there is the hook's
# wiring; what is under test here is the config itself, and what a push through
# the hook looks like when gitleaks really runs, which a stub cannot check).
#
# Skipped when gitleaks is not installed, so a clone that never wanted the
# scanner still runs a green suite; CI installs it and is the arbiter.
# ROMP_GITLEAKS names a binary that is not on PATH, as it does for the hook.
#
# Nothing in this file may contain a credential-shaped literal: gitleaks scans
# this repo, and a fixture secret written out longhand would flag the very test
# that proves the scanner works. The probes below are assembled at run time and
# only ever exist in a temp file.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

load git-hermetic

setup() {
    git_hermetic
    GL="${ROMP_GITLEAKS:-$(command -v gitleaks || true)}"
    if [ -z "$GL" ] || [ ! -x "$GL" ]; then skip "gitleaks not installed"; fi
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

@test "every commit in this branch's history is clean" {
    # Each merge by its first-parent diff, as the hook and CI scan it.
    run "$GL" git "$ROMP_DIR" --no-banner --redact --exit-code 2 --config "$CFG" \
        --log-opts="HEAD --diff-merges=first-parent"
    [ "$status" -eq 0 ]
}

@test "a planted credential is caught" {
    printf 'token = "%s"\n' "$(probe_token)" > "$TEST_DIR/probe.py"
    run scan
    [ "$status" -eq 2 ]
}

@test "a secret introduced only in a merge commit is caught by the history scan" {
    # `gitleaks git` runs `git log -p`, which shows NO diff for a merge commit by default, so a
    # credential added during a conflict resolution (present in neither parent, only the merge
    # tree) is scanned by nothing. The hook and CI pass --diff-merges=first-parent to close that;
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
    # With the flag the hook and CI pass, the first-parent diff surfaces it and the scan refuses.
    run "$GL" git "$R" --no-banner --redact --exit-code 2 --config "$CFG" \
        --log-opts="--all --diff-merges=first-parent"
    [ "$status" -eq 2 ]
}

@test "a credential in a path a committed .gitattributes marks -diff is caught by CI's configured history scan" {
    # `gitleaks git` runs `git log -p`, and git reads the checkout's .gitattributes for it: a path
    # marked -diff prints as "Binary files differ" with no hunk, so a credential committed there and
    # removed in a later commit is text the history scan never sees, while the tree scan reads HEAD,
    # where the file is gone. CI's line carries an option for this. What is asserted is that CI's
    # CONFIGURED invocation, whatever its spelling, surfaces the secret: the arguments are read from
    # .github/workflows/ci.yml itself, not copied here, since a copied string stays green while CI
    # drifts.
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
    # the credential-scan job's history step. Zero or two and the premise is gone, so say so.
    ci="$ROMP_DIR/.github/workflows/ci.yml"
    n=$(grep -cE '^[[:space:]]*run: gitleaks git \. ' "$ci")
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
    run git -C "$WORK" push origin HEAD:main
    [ "$status" -ne 0 ]
    [[ "$output" == *"gitleaks found a credential"* ]]
    [[ "$output" == *"probe.py"* ]]              # -v: the file to fix
    [[ "$output" == *"github-pat"* ]]            # and the rule that matched
    [[ "$output" != *"$(probe_token)"* ]]        # --redact: the value stays out of the terminal
    [ "$(git -C "$TEST_DIR/remote.git" rev-parse main)" != "$(git -C "$WORK" rev-parse HEAD)" ]
}

@test "through the hook: a force-push over a remote tip this clone never fetched is refused" {
    # Another clone moves the branch; this one force-pushes a secret without
    # fetching. gitleaks handed a range with a sha it cannot resolve scans no
    # commits and exits 0, so the hook has to fall back to a range it can.
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
