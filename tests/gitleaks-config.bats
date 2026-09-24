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
    GL="${ROMP_GITLEAKS:-$(command -v gitleaks || true)}"
    if [ -z "$GL" ] || [ ! -x "$GL" ]; then
        # ROMP_GITLEAKS_REQUIRE=1 makes the absence a failure naming the reason, not a skip:
        # CI's Linux Shell job installs the pinned gitleaks in the step before it runs bats
        # and sets the switch, so a skip there would report a broken install as fourteen green
        # skips (the stance ROMP_SERVED_TESTS_REQUIRE takes in tests/conftest.py). Without
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

@test "every commit in this branch's history is clean" {
    # Each merge by its first-parent diff, as CI scans it.
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
# (pieces) of at most 98,304 bytes, each beginning with a line holding ~, and runs `gitleaks dir .`
# from inside their directory, so gitleaks runs no git. Each case below pins one premise of that
# design against the installed scanner; tests/pre-push-hook.bats drives the hook itself.

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
# each with the file name it needs and a probe it reports.
PATH_RULES="pkcs12-file nuget-config-password kubernetes-secret-yaml hashicorp-tf-password freemius-secret-key"

path_rule_name() {
    case $1 in
        pkcs12-file) echo cert.p12 ;;
        nuget-config-password) echo nuget.config ;;
        kubernetes-secret-yaml) echo secret.yaml ;;
        hashicorp-tf-password) echo main.tf ;;
        freemius-secret-key) echo fs.php ;;
    esac
}

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
    # must hold there: RFC 6455's nonce behind the ~ line gives no finding under the config and one
    # under the default rules (so the config is what excuses it), and a secret that contains the
    # nonce gives one finding under the config.
    mkdir "$TEST_DIR/p"
    printf '~\nheaders = {"Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ=="}\n' > "$TEST_DIR/p/1"
    run scan_pieces "$TEST_DIR/p" --config "$CFG"
    [ "$status" -eq 0 ] || { echo "the nonce was not excused in directory mode (exit $status):"; echo "$output"; false; }
    unset GITLEAKS_CONFIG GITLEAKS_CONFIG_TOML   # no --config below: the default rules, whatever the environment names
    run scan_pieces "$TEST_DIR/p"
    [ "$status" -eq 2 ] || { echo "the default rules did not report the nonce, so the case proves nothing (exit $status):"; echo "$output"; false; }
    printf '~\napi_key = "%s%s%s"\n' "dGhlIHNhbXBsZSBub25jZQ==" "Zk8vQ2xhdWRl" "U2VjcmV0OTk5" > "$TEST_DIR/p/1"
    run scan_pieces "$TEST_DIR/p" --config "$CFG"
    [ "$status" -eq 2 ] || { echo "a secret containing the nonce was excused (exit $status):"; echo "$output"; false; }
    [[ "$output" =~ leaks\ found:\ ([0-9]+) ]] && [ "${BASH_REMATCH[1]}" -eq 1 ] || {
        echo "expected one finding for the secret containing the nonce:"; echo "$output"; false; }
}

@test "round 9d, G2: a piece of the hook's cap, 98,304 bytes, is read whole: each of its dense distinct tokens is found" {
    # The hook caps a piece at 98,304 bytes because gitleaks reads a file of up to 100,000 bytes in
    # one chunk and a larger one in chunks, missing a match that crosses a cut (in a 200,000-byte
    # file of these lines 8.28.0 and 8.30.1 miss 3 of 4,878). A piece of exactly the cap, packed with
    # distinct github-pat shaped lines behind the ~ line, must be read whole: every token found, and
    # the byte figure the piece's size. A later gitleaks that reads files in smaller chunks turns
    # this red, and the hook's cap moves with it.
    mkdir "$TEST_DIR/p"
    n=$(( (98304 - 2) / 41 ))                     # 41 bytes a line, after the 2-byte ~ line
    pad=$(( 98304 - 2 - n * 41 ))
    { printf '~\n'; dense_tokens "$n"; printf '%*s\n' $(( pad - 1 )) '' | tr ' ' x; } > "$TEST_DIR/p/1"
    [ "$(( $(wc -c < "$TEST_DIR/p/1") ))" -eq 98304 ]
    [ "$(( $(grep -c '^gh' "$TEST_DIR/p/1") ))" -eq "$n" ]
    [ "$(( $(grep '^gh' "$TEST_DIR/p/1" | sort -u | wc -l) ))" -eq "$n" ]   # distinct
    run scan_pieces "$TEST_DIR/p" --config "$CFG"
    [ "$status" -eq 2 ] || { echo "no finding in the dense piece (exit $status):"; echo "$output"; false; }
    [[ "$output" == *"scanned ~98304 bytes"* ]] || { echo "the byte figure is not the piece's 98304 bytes:"; echo "$output"; false; }
    [[ "$output" =~ leaks\ found:\ ([0-9]+) ]] && [ "${BASH_REMATCH[1]}" -eq "$n" ] || {
        echo "expected all $n tokens found in a piece of the cap:"; echo "$output"; false; }
}

@test "round 9d, G3: a piece that begins with an archive or document signature is read only behind the hook's ~ line" {
    # gitleaks skips a file whose first bytes carry a zip, gzip or PDF signature: it counts 0 bytes
    # and finds nothing below the signature. A pushed file's added lines can begin that way, so each
    # piece the hook writes begins with a line holding ~, which moves the signature off byte 0. Both
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

@test "round 9d, G4: each path-scoped rule fires only under its file's own name, which a piece named by number lacks" {
    # Five default rules key on the file's path. A piece named by number carries no such name, so
    # the hook's main run cannot fire them (until round 9 the hook ran gitleaks over git, where the
    # path is real, and they fired), and the hook scans the pushed files whose paths match those
    # rules a second time, each under its basename, with --enable-rule naming the five. Both halves
    # per rule, in that second run's shape: the probe under its own name, in a directory named by
    # number, is reported under the rule; the same bytes named by number give no finding.
    five=${PATH_RULES// /,}
    for r in $PATH_RULES; do
        rm -rf "$TEST_DIR/p"; mkdir -p "$TEST_DIR/p/1"
        path_rule_probe "$r" > "$TEST_DIR/p/1/$(path_rule_name "$r")"
        run scan_pieces "$TEST_DIR/p" --config "$CFG" --enable-rule "$five" --report-format json --report-path "$TEST_DIR/r.json"
        [ "$status" -eq 2 ] && grep -q "\"RuleID\": \"$r\"" "$TEST_DIR/r.json" || {
            echo "$r: not reported for $(path_rule_name "$r") under its own name (exit $status):"; echo "$output"; false; }
        rm -rf "$TEST_DIR/p"; mkdir "$TEST_DIR/p"
        path_rule_probe "$r" > "$TEST_DIR/p/1"
        run scan_pieces "$TEST_DIR/p" --config "$CFG" --enable-rule "$five"
        [ "$status" -eq 0 ] || { echo "$r: reported for the same bytes named by number (exit $status):"; echo "$output"; false; }
    done
}
