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
# each with the names the hook gives its copies and a probe it reports.
PATH_RULES="pkcs12-file nuget-config-password kubernetes-secret-yaml hashicorp-tf-password freemius-secret-key"

# The names the hook's path-scoped run gives a rule's copies, one per suffix its selection takes
# for that rule: the piece number and the suffix the selection matched, lower-cased, nuget.config
# whole, in a directory named by the piece number (round 10b, from the round 9 rulings' group F
# and the coordinator's decision 4; until then each copy took the pushed file's basename, which
# cert.p12, nuget.config, secret.yaml, main.tf and fs.php stood for here).
path_rule_copies() {
    case $1 in
        pkcs12-file) echo 1.p12 1.pfx ;;
        nuget-config-password) echo nuget.config ;;
        kubernetes-secret-yaml) echo 1.yaml 1.yml ;;
        hashicorp-tf-password) echo 1.tf 1.hcl ;;
        freemius-secret-key) echo 1.php ;;
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

@test "round 9d, G2: a piece of the hook's cap, CAP bytes read from its awk line, is read whole: each of its dense distinct tokens is found (red for a CAP of 125,011 bytes or more, CAP=130000 among them)" {
    # The hook caps a piece at CAP bytes (98,304 at this writing) because gitleaks reads a file of
    # up to 100,000 bytes in one chunk and a larger one in chunks, missing a match that crosses a
    # cut (in a 200,000-byte file of these lines 8.28.0 and 8.30.1 miss 3 of 4,878). A piece of
    # exactly the cap, packed with distinct github-pat shaped lines behind the ~ line, must be read
    # whole: every token found, and the byte figure the piece's size. A later gitleaks that reads
    # files in smaller chunks turns this red, and the hook's cap moves with it.
    # CAP is read from the hook (hook_constant; round 10b, from the round 9 rulings' group C): until
    # then this case built a piece of a restated 98,304 bytes and stayed green whatever CAP the hook
    # held. Its range, measured on this layout under 8.28.0 and 8.30.1: gitleaks' first chunk is its
    # 100,000-byte read plus a peek of up to 25,000 bytes for a blank line, and this piece holds
    # none, so a CAP up to 125,010 is still read whole (green) and a CAP of 125,011 or more puts the
    # token that starts at byte 124,970 across the cut (red, that token missed). The band
    # above 100,000 that stays green here belongs to the round 10b cap pin below and to the
    # blank-line witness it names.
    cap=$(hook_constant CAP)
    mkdir "$TEST_DIR/p"
    n=$(( (cap - 2) / 41 ))                       # 41 bytes a line, after the 2-byte ~ line
    pad=$(( cap - 2 - n * 41 ))
    { printf '~\n'; dense_tokens "$n"; [ "$pad" -eq 0 ] || printf '%*s\n' $(( pad - 1 )) '' | tr ' ' x; } > "$TEST_DIR/p/1"
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

@test "round 9d, G4: each path-scoped rule fires under the name the hook gives its copy, the piece number and the suffix the rule keys on, which a piece named by number alone lacks" {
    # Five default rules key on the file's path. A piece named by number carries no such name, so
    # the hook's main run cannot fire them (until round 9 the hook ran gitleaks over git, where the
    # path is real, and they fired), and the hook scans the pushed files whose paths match those
    # rules a second time, each copy named by its piece number and the suffix the selection
    # matched, lower-cased (1.p12, 1.yaml; nuget.config whole), in a directory named by the piece
    # number, with --enable-rule naming the five. Until round 10b each copy took the pushed file's
    # git-quoted basename, and a selected file whose quoted basename passes 255 bytes could not be
    # written (the round 9 rulings' group F); the fixed name keeps what the five rules' paths key
    # on and nothing of the pushed name. Both halves per rule, in that second run's shape: the
    # probe under each of its copy names, in a directory named by number, is reported under the
    # rule; the same bytes named by number give no finding.
    five=${PATH_RULES// /,}
    for r in $PATH_RULES; do
        for c in $(path_rule_copies "$r"); do
            rm -rf "$TEST_DIR/p" "$TEST_DIR/r.json"; mkdir -p "$TEST_DIR/p/1"
            path_rule_probe "$r" > "$TEST_DIR/p/1/$c"
            run scan_pieces "$TEST_DIR/p" --config "$CFG" --enable-rule "$five" --report-format json --report-path "$TEST_DIR/r.json"
            [ "$status" -eq 2 ] && grep -q "\"RuleID\": \"$r\"" "$TEST_DIR/r.json" || {
                echo "$r: not reported for its copy named 1/$c (exit $status):"; echo "$output"; false; }
        done
        rm -rf "$TEST_DIR/p"; mkdir "$TEST_DIR/p"
        path_rule_probe "$r" > "$TEST_DIR/p/1"
        run scan_pieces "$TEST_DIR/p" --config "$CFG" --enable-rule "$five"
        [ "$status" -eq 0 ] || { echo "$r: reported for the same bytes named by number (exit $status):"; echo "$output"; false; }
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
    # CAP=130000, and G2 above for a CAP of 125,011 or more. The values just above 100,000 that the
    # witness cannot reach, which its title names as this pin's, are the band this pin backs up;
    # it guards the value only.
    cap=$(hook_constant CAP)
    [ "$cap" -le 100000 ] || {
        echo "the hook's CAP is $cap bytes, above 100,000, the most gitleaks reads of a file in one chunk."
        echo "This pin guards the constant's value; the executed proof of the property, a piece read whole, is the case"
        echo "'round 10b (C, the blank-line witness for the band from 100,000 to 125,000)' in tests/pre-push-hook.bats,"
        echo "with G2 in this file for a CAP of 125,011 or more."
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
