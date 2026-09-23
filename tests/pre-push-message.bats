#!/usr/bin/env bats

# .githooks/pre-push: the MESSAGE scan, driven by hand against real commits. The
# subject and body of each commit a push publishes, and an annotated tag's own
# message.
#
# A commit is published with its metadata, and the hook's two content scans (the
# tip's tree, each new commit's added lines) read none of it. The address scan
# (pre-push-identity.bats) covers the author and committer addresses; this file
# covers the message, which is where a commit describing a fix names the path
# that failed or the machine it failed on. A string a file carries can be
# redacted forward once it is out; a string a message carries cannot, since only
# a rewrite of the commit takes it back. So the hook greps every new commit's
# message like lines of content, against the whole denylist, and names the
# commit and the line.
#
# Three limits, all pinned here: only what THIS push publishes is read (a message
# a remote already holds is refused to no purpose, like an added line it holds);
# the author and committer NAMES on the commit are not read, being the author's
# own and on every commit they make; and the message is all that is read of a
# signed commit, not the verification report a log.showSignature config has git
# log print ahead of it, which names the signer. The message itself is read
# whole, the author's own name included: it is text they typed, and a FILE naming
# them is refused on the same ground. An annotated TAG's message is read the same
# way (every other read the hook makes peels a tag to its commit): the tag case
# near the end holds that. A message the hook cannot READ refuses the push as
# unscanned (the last cases): a log that failed is not an empty message.
#
# Every identifier below is SYNTHETIC: the denylist, the logins, the hosts and
# the paths are invented per test (the repo may go public, and a real one written
# here would be the very leak the hook exists to stop).

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOK="$ROMP_DIR/.githooks/pre-push"

load git-hermetic

setup() {
    # Hermetic git: the fixture commits with plain defaults under a synthetic identity
    # (git-hermetic exports GIT_AUTHOR_EMAIL / GIT_COMMITTER_EMAIL as tests@example.invalid,
    # which the address scan excuses as an address the environment chose), so the only
    # thing a fixture can trip here is the message scan.
    git_hermetic
    unset EMAIL        # a chosen address to the hook, and the developer's shell may set it
    TEST_DIR="$(mktemp -d)"
    REPO="$TEST_DIR/repo"
    mkdir -p "$REPO"
    git -C "$REPO" init -q
    git -C "$REPO" symbolic-ref HEAD refs/heads/main     # whatever init.defaultBranch says
    git -C "$REPO" config user.email tests@example.invalid
    git -C "$REPO" config user.name  Tester
    # The hook under test is run BY HAND below; the fixture's own git operations must
    # not run this machine's hooks.
    mkdir -p "$TEST_DIR/no-hooks"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/no-hooks"

    # the denylist: an invented login and host, nothing that exists on any real machine
    STRINGS="$TEST_DIR/private-strings.txt"
    printf '# synthetic\nzzsynthuser\nTESTHOST\n' > "$STRINGS"

    export ROMP_PRIVATE_STRINGS="$STRINGS"
    export ROMP_NO_GITLEAKS=1          # the credential half has its own test file
}

teardown() { rm -rf "${TEST_DIR:-}"; }

ZERO=0000000000000000000000000000000000000000

# Run the hook from inside the repo, the way git does. bats' `run` executes the
# command in a subshell, so the cd here does not leak into the test.
_hook_in() { cd "$1" && shift && bash "$@"; }

# Feed the hook a ref line the way git does: <local_ref> <sha> <remote_ref> <remote_sha>.
# The default remote sha of zero means a new branch, i.e. every commit here is
# being published; pass the sha the remote holds to model updating a branch it has.
run_hook() {
    local sha remote_sha="${1:-$ZERO}"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run _hook_in "$REPO" "$HOOK" origin git@example.invalid:x/y.git <<< \
        "refs/heads/main $sha refs/heads/main $remote_sha"
}

# Stage one clean file, ready for a commit made with whatever options a test needs.
stage_file() {   # <path>
    printf '%s\n' "the web session's work on $1" > "$REPO/$1"
    git -C "$REPO" add "$1"
}

# ssh signing (gpg.format ssh) arrived in git 2.34; the signed-commit case skips below it.
git_at_least_2_34() {
    local v major rest minor
    v="$(git --version | awk '{print $3}')"
    major="${v%%.*}"; rest="${v#*.}"; minor="${rest%%.*}"
    [ "$major" -gt 2 ] 2>/dev/null || { [ "$major" -eq 2 ] && [ "$minor" -ge 34 ]; } 2>/dev/null
}

# A commit of one clean file with the given message paragraphs (each -m is one;
# git joins them with a blank line, so the second paragraph is message line 3).
commit_msg() {   # <path> <paragraph>...
    local path="$1"; shift
    local args=()
    local para
    for para in "$@"; do args+=(-m "$para"); done
    stage_file "$path"
    git -C "$REPO" commit -q "${args[@]}"
}

@test "a clean message passes (the control)" {
    commit_msg ok.txt "clean tree, clean message"
    run_hook
    [ "$status" -eq 0 ]
}

@test "a banned string in the SUBJECT is refused, naming the commit and line 1" {
    commit_msg web.txt "fix the path /home/zzsynthuser/code on that machine"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit ${sha:0:10} carries a personal identifier on line 1 (line 1 is the subject)"* ]]
    [[ "$output" != *"zzsynthuser"* ]]          # the line is named; the string itself is not echoed
    [[ "$output" == *"BLOCKED"* ]]
    # the remedy is a rewrite of the commit, and it is the message's own
    [[ "$output" == *"A commit MESSAGE is never redacted forward"* ]]
    [[ "$output" == *"git commit --amend"* ]]
    [[ "$output" == *"reword rebase"* ]]
    # the tree and the added lines were clean: no content report, and not the address remedy
    [[ "$output" != *"ADDS a personal identifier"* ]]
    [[ "$output" != *"personal identifier in:"* ]]
    [[ "$output" != *"--reset-author"* ]]
}

@test "a banned string in the BODY alone is refused, naming the body's line" {
    commit_msg web.txt "fix the poll" "the failing run was on TESTHOST"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    [ "$(git -C "$REPO" log -1 --format=%B | sed -n 3p)" = "the failing run was on TESTHOST" ]
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit ${sha:0:10} carries a personal identifier on line 3 "* ]]
    [[ "$output" != *"TESTHOST"* ]]
}

@test "every matching line is named, subject and body alike" {
    commit_msg web.txt "seen on TESTHOST" "reproduced under /home/zzsynthuser/x"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit ${sha:0:10} carries a personal identifier on line 1,3 "* ]]
}

@test "the match is case-insensitive, like a line of content" {
    commit_msg web.txt "seen on testhost"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit"* ]]
}

@test "the author's and committer's NAMES are not read: they are on every commit they make" {
    # the name is on the denylist because a FILE must not carry it; the commit's own
    # author line carries it regardless, and refusing that would refuse every push
    stage_file web.txt
    GIT_AUTHOR_NAME=zzsynthuser GIT_COMMITTER_NAME=TESTHOST git -C "$REPO" commit -qm "clean message"
    [ "$(git -C "$REPO" log -1 --format='%an|%cn')" = "zzsynthuser|TESTHOST" ]
    run_hook
    [ "$status" -eq 0 ]
}

@test "the message is read whole: a trailer naming the author is refused like a file naming them" {
    commit_msg web.txt "clean subject" "Signed-off-by: zzsynthuser <dev@example.invalid>"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit ${sha:0:10} carries a personal identifier on line 3 "* ]]
}

@test "the message remedy is not printed for a content hit" {
    printf '%s\n' "home is /home/zzsynthuser/code" > "$REPO/leak.txt"
    git -C "$REPO" add leak.txt
    git -C "$REPO" commit -qm "leak in a file, clean message"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"personal identifier in:"* ]]
    [[ "$output" != *"the MESSAGE of commit"* ]]
    [[ "$output" != *"never redacted forward"* ]]
}

@test "a leaking message on an INTERMEDIATE commit is caught and named when the tip's is clean" {
    commit_msg web.txt "broke on TESTHOST"
    leaky_sha="$(git -C "$REPO" rev-parse HEAD)"
    commit_msg api.txt "clean follow-up"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit ${leaky_sha:0:10} carries"* ]]
}

@test "a leaking message a remote already has is not rechecked: only what THIS push publishes counts" {
    # the string is already public through that remote, and a message has no forward
    # remedy; refusing every later push of the branch would fix nothing
    commit_msg web.txt "broke on TESTHOST, and pushed"
    git -C "$REPO" update-ref refs/remotes/origin/main HEAD
    commit_msg api.txt "the one commit new to every remote"
    run_hook "$(git -C "$REPO" rev-parse origin/main)"
    [ "$status" -eq 0 ]
}

@test "no denylist file means no message scan (a fresh clone is unaffected)" {
    export ROMP_PRIVATE_STRINGS="$TEST_DIR/does-not-exist.txt"
    commit_msg web.txt "broke on TESTHOST"
    run_hook
    [ "$status" -eq 0 ]
}

@test "a merge commit's message is read like any other commit's" {
    # a merge's message is typed by whoever resolves it, and a conflict note is where a machine's name lands
    commit_msg base.txt "base"
    git -C "$REPO" checkout -q -b feature
    commit_msg web.txt "branch work"
    git -C "$REPO" checkout -q main
    commit_msg api.txt "main work"
    git -C "$REPO" checkout -q feature
    git -C "$REPO" merge -q --no-ff -m "merge main, resolved on TESTHOST" main
    merge_sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit ${merge_sha:0:10} carries a personal identifier on line 1 "* ]]
}

@test "a signed commit is read as its message alone: the verification report log.showSignature prints ahead of it is not" {
    # With log.showSignature set, git log prints a signed commit's verification report before
    # whatever the format asks for, and the report names the signer: the address here, whose
    # domain goes on the denylist the way the author's own name is. Read as message text, that
    # refused a clean signed commit and numbered a real hit from the report's line, not the
    # subject. An ssh signature needs only ssh-keygen, which is on every machine that pushes.
    git_at_least_2_34 || skip "ssh signing needs git >= 2.34"
    command -v ssh-keygen >/dev/null || skip "ssh-keygen is not installed"
    ssh-keygen -q -t ed25519 -N '' -f "$TEST_DIR/key" -C 'romp tests' >/dev/null
    printf 'tests@example.invalid %s\n' "$(cut -d' ' -f1,2 "$TEST_DIR/key.pub")" > "$TEST_DIR/allowed"
    git -C "$REPO" config gpg.format ssh
    git -C "$REPO" config user.signingkey "$TEST_DIR/key.pub"
    git -C "$REPO" config gpg.ssh.allowedSignersFile "$TEST_DIR/allowed"
    git -C "$REPO" config log.showSignature true
    printf 'example.invalid\n' >> "$STRINGS"          # the signer's domain; the address scan excuses the address itself
    stage_file ok.txt
    git -C "$REPO" commit -q -S -m "clean subject" -m "clean body"
    [[ "$(git -C "$REPO" log -1 --format=%B)" == *"signature"* ]]      # the config is live: git log prepends the report
    run_hook
    [ "$status" -eq 0 ]
    stage_file web.txt
    git -C "$REPO" commit -q -S -m "seen on TESTHOST"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit ${sha:0:10} carries a personal identifier on line 1 "* ]]
}

@test "a message hit and an address hit on one push report both remedies" {
    # the two metadata scans are independent; each names its own way out
    stage_file web.txt
    GIT_AUTHOR_EMAIL=dev@TESTHOST.example GIT_COMMITTER_EMAIL=dev@TESTHOST.example \
        git -C "$REPO" commit -qm "broke under /home/zzsynthuser"
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit"* ]]
    [[ "$output" == *"whose domain carries a personal identifier"* ]]
    [[ "$output" == *"never redacted forward"* ]]
    [[ "$output" == *"--reset-author"* ]]
}

@test "an annotated tag's MESSAGE is read like a commit's, naming the tag and the line, with the tag's own remedy" {
    commit_msg ok.txt "clean"
    git -C "$REPO" tag -a v1 -m "release one" -m "cut on TESTHOST"
    sha="$(git -C "$REPO" rev-parse refs/tags/v1)"
    [ "$(git -C "$REPO" cat-file -t "$sha")" = tag ]
    run _hook_in "$REPO" "$HOOK" origin git@example.invalid:x/y.git <<< \
        "refs/tags/v1 $sha refs/tags/v1 $ZERO"
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of tag refs/tags/v1 (${sha:0:10}) carries a personal identifier on line 3"* ]]
    [[ "$output" != *"TESTHOST"* ]]
    [[ "$output" == *"git tag -f -a <name> <commit>"* ]]
    # the commit it names has a clean message and is reported as nothing
    [[ "$output" != *"the MESSAGE of commit"* ]]
}

# ── a message the hook cannot READ ────────────────────────────────────────
# The message read was one `git log` piped into the grep that judged it, so the
# pipeline's status was the grep's and a log that FAILED read as an empty
# message, git's own error line the only sign (found by execution, 2026-09-20:
# with that log refused, a commit whose subject named a denylist host went
# through a real push with every counter at zero). The hook now captures the
# message and its status before the grep, and numbers a hit's line from the
# subject as before. An EMPTY message is absent, not unreadable, and passes.
#
# The fault is a git first on the hook's PATH that refuses ONE command shape
# (the log format the hook reads messages with, keyed to one commit's sha when a
# case needs a clean commit beside it) and runs the real git for every other,
# written into the test's temp dir at run time. The test body is its own
# subshell, so the PATH change does not outlive the test. Once per test: a
# second call would resolve `command -v git` to the first shim, and the new one
# would exec itself forever.
git_refusing() {   # <bash test over the shim's "$@"> <exit status> <stderr line>
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then\n' "$1"
        printf '    echo %q >&2\n    exit %d\nfi\n' "$3" "$2"
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}
fail_log_message() {   # [<sha whose message log fails; every commit's when omitted>]
    # the one `git log` format the hook reads a commit's message with (the marker line, then %B, then the tail marker; rounds 7 and 8); the addresses log is another format
    if [ -n "${1:-}" ]; then
        git_refusing "[ \"\${1:-}\" = log ] && [ \"\${4:-}\" = --format=message%x09%H%n%B%nend%x09%H ] && [ \"\${!#}\" = $1 ]" 128 "fatal: shim: log (the message) refused for $1"
    else
        git_refusing '[ "${1:-}" = log ] && [ "${4:-}" = --format=message%x09%H%n%B%nend%x09%H ]' 128 "fatal: shim: log (the message) refused"
    fi
}

@test "a commit whose MESSAGE cannot be read is refused as unscanned, naming the commit: a failed log is not an empty message" {
    commit_msg web.txt "fix the crash on TESTHOST"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    fail_log_message
    # the fault as the hook meets it, from the repo's top level: the message log fails, the addresses log and the diff work
    run _hook_in "$REPO" -c 'git log -1 --no-show-signature --format=message%x09%H%n%B%nend%x09%H "$1"' _ "$sha"
    [ "$status" -eq 128 ]
    run _hook_in "$REPO" -c 'git log -1 --no-show-signature --format=authored%x09%ae "$1" >/dev/null && git diff-tree -p -r --root --no-commit-id "$1" >/dev/null' _ "$sha"
    [ "$status" -eq 0 ]
    run_hook
    [ "$status" -eq 1 ]
    [[ "$output" == *"the MESSAGE of commit ${sha:0:10} could not be read (git log exited 128)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" == *"git push --no-verify"* ]]
    # reported as a failed read, not as a finding: nothing was read to find
    [[ "$output" != *"carries a personal identifier"* ]]
    [[ "$output" != *"never redacted forward"* ]]
    [[ "$output" != *"BLOCKED"* ]]
}

@test "an EMPTY message and a merge's clean one pass beside that git when the fault sits on a commit not in the push: an empty message is absent, not unreadable" {
    commit_msg base.txt "base"
    base="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" update-ref refs/remotes/origin/main HEAD     # base is published
    git -C "$REPO" checkout -q -b feature
    commit_msg web.txt "branch work"
    git -C "$REPO" checkout -q main
    stage_file api.txt
    git -C "$REPO" commit -q --allow-empty-message -m ""
    [ -z "$(git -C "$REPO" log -1 --format=%B | tr -d '\n')" ]
    git -C "$REPO" merge -q --no-ff -m "merge feature" feature
    fail_log_message "$base"
    run_hook "$base"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "the message is numbered from the subject under the captured read: a hit in the body's third paragraph is line 5" {
    commit_msg web.txt "fix: a subject" "a body line" "seen on TESTHOST"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    [ "$(git -C "$REPO" log -1 --format=%B | sed -n 5p)" = "seen on TESTHOST" ]
    run_hook
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit ${sha:0:10} carries a personal identifier on line 5 (line 1 is the subject)"* ]]
}

# ── the message grep through one helper: its status read ─────────────────
# The hook reads every grep over captured content through one helper
# (judged_read) that refuses a status outside 0 and 1 naming the read
# (pre-push-hook.bats pins the helper's derived lists). A grep exiting 2 over a
# message read as no match and published the message through a real push (the
# round 5 refuters, 2026-09-22); the two cases below are a commit's message and
# a tag's, each through a real push with that shim.
add_remote() {
    git init -q --bare "$TEST_DIR/remote.git"
    git -C "$REPO" remote add origin "$TEST_DIR/remote.git"
}
push_ref_through_hook_with_shim() {   # <refspec>: the hook installed for one real push behind a wrapper that puts the shim directory first on the hook's PATH
    mkdir -p "$TEST_DIR/hooks"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'export PATH=%q:"$PATH"\n' "$TEST_DIR/shim"
        printf 'exec %q "$@"\n' "$HOOK"
    } > "$TEST_DIR/hooks/pre-push"
    chmod 755 "$TEST_DIR/hooks/pre-push"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/hooks"
    run git -C "$REPO" push origin "$1"
    git -C "$REPO" config core.hooksPath "$TEST_DIR/no-hooks"
}
remote_holds_ref() { git -C "$TEST_DIR/remote.git" rev-parse -q --verify "$1" >/dev/null; }   # <ref>
grep_refusing_message_shape() {   # a grep exiting 2 for the message grep's shape (-in -F), the real grep otherwise
    local real_grep
    real_grep="$(command -v grep)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if [ "${1:-}" = -in ]; then echo "shim: grep refused" >&2; exit 2; fi\n'
        printf 'exec %q "$@"\n' "$real_grep"
    } > "$TEST_DIR/shim/grep"
    chmod 755 "$TEST_DIR/shim/grep"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "the MESSAGE grep exiting 2 (an error, not a no-match) over a commit whose subject names a banned host is refused as unscanned naming the read, through a real push: an unread message is not a clean one, and the remote holds nothing" {
    add_remote
    commit_msg web.txt "fix the crash on TESTHOST"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    grep_refusing_message_shape
    run _hook_in "$REPO" -c 'printf "x\n" | grep -in -F -e x; echo "status $?"'
    [[ "$output" == *"status 2"* ]]
    push_ref_through_hook_with_shim main
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit ${sha:0:10} could not be grepped (grep exited 2)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"carries a personal identifier"* ]]
    [[ "$output" != *"BLOCKED"* ]]
    run remote_holds_ref refs/heads/main
    [ "$status" -ne 0 ]
}

@test "the same grep exiting 2 over an annotated TAG's message is refused naming the tag, through a real push of the tag over a commit the remote holds, and the remote never gets the tag" {
    add_remote
    commit_msg ok.txt "clean"
    git -C "$REPO" push -q origin main                 # the commit on the remote: the tag's own reads are the only ones the push makes
    git -C "$REPO" tag -a v1 -m "release one" -m "cut on TESTHOST"
    sha="$(git -C "$REPO" rev-parse refs/tags/v1)"
    grep_refusing_message_shape
    push_ref_through_hook_with_shim refs/tags/v1
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of tag refs/tags/v1 (${sha:0:10}) could not be grepped (grep exited 2)"* ]]
    [[ "$output" != *"carries a personal identifier"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

# ── round 7: the message reads under a tool that exits 0 and prints nothing ──
# Round 6's refuters drove the message grep with a grep exiting 0 and printing
# nothing: exit 0 is a match, and no line was read as no hit, so a commit and
# a tag whose message carried a banned string were published through real
# pushes with nothing printed. The same shape needs no shim: under a UTF-8
# locale GNU grep calls a line holding a byte that is no UTF-8 binary, and a
# match on such a line is a note on stderr, no line and exit 0. The grep now
# reads the message as text (-a) and a match with no line is refused as
# unscanned naming the message. The message reads themselves were open too: a
# git exiting 0 and printing nothing for the commit's log read as an empty
# message, and an awk exiting 0 and printing nothing for a tag's message read
# as a tag with none. The commit's log now asks for a marker line ahead of the
# message and refuses an answer without it; the tag object is read once, judged
# against its size, and its message parsed by the shell with no awk between.
grep_silent_message_shape() {   # a grep exiting 0 (a match) and printing nothing for the message grep's shape (-in ... -F), the real grep otherwise
    local real_grep
    real_grep="$(command -v grep)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if [ "${1:-}" = -in ]; then cat > /dev/null; exit 0; fi\n'
        printf 'exec %q "$@"\n' "$real_grep"
    } > "$TEST_DIR/shim/grep"
    chmod 755 "$TEST_DIR/shim/grep"
    export PATH="$TEST_DIR/shim:$PATH"
}
awk_silent_on_program() {   # <text of an awk program>: an awk exiting 0 and printing nothing when its arguments carry that text, the real awk for every other program
    local real_awk
    real_awk="$(command -v awk)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'real_awk=%q; marker=%q\n' "$real_awk" "$1"
        cat <<'SHIM'
case "$*" in *"$marker"*) cat > /dev/null; exit 0 ;; esac
exec "$real_awk" "$@"
SHIM
    } > "$TEST_DIR/shim/awk"
    chmod 755 "$TEST_DIR/shim/awk"
    export PATH="$TEST_DIR/shim:$PATH"
}
push_ref_through_hook() {   # <refspec>: the hook installed for one real push with no shim (an empty shim directory ahead of PATH: every tool the real one)
    mkdir -p "$TEST_DIR/shim"
    push_ref_through_hook_with_shim "$1"
}
tag_over_clean_commit_on_remote() {   # <tag message paragraphs...>: a clean commit pushed, so the tag's own reads are the only ones the push makes; sha is the tag's
    local para args=()
    for para in "$@"; do args+=(-m "$para"); done
    add_remote
    commit_msg ok.txt "clean"
    git -C "$REPO" push -q origin main
    git -C "$REPO" tag -a v1 "${args[@]}"
    sha="$(git -C "$REPO" rev-parse refs/tags/v1)"
}

@test "the MESSAGE grep exiting 0 (a match) and printing NO line over a commit whose subject names a banned host is refused as unscanned naming the message and the short answer, through a real push: the status says a match, the answer says none, and the remote holds nothing" {
    add_remote
    commit_msg web.txt "fix the crash on TESTHOST"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    grep_silent_message_shape
    run _hook_in "$REPO" -c 'printf "x\n" | grep -in -F -e x; echo "status $?"'
    [ "$output" = "status 0" ]
    push_ref_through_hook_with_shim main
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit ${sha:0:10} was grepped with no hit line listed (grep exited 0, a match, and printed no line), so the answer is short"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"carries a personal identifier"* ]]
    [[ "$output" != *"could not be grepped"* ]]
    [[ "$output" != *"BLOCKED"* ]]
    run remote_holds_ref refs/heads/main
    [ "$status" -ne 0 ]
}

@test "the same grep exiting 0 with no line over an annotated TAG's message is refused naming the tag, through a real push of the tag over a commit the remote holds, and the remote never gets the tag" {
    tag_over_clean_commit_on_remote "release one" "cut on TESTHOST"
    grep_silent_message_shape
    push_ref_through_hook_with_shim refs/tags/v1
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of tag refs/tags/v1 (${sha:0:10}) was grepped with no hit line listed (grep exited 0, a match, and printed no line), so the answer is short"* ]]
    [[ "$output" != *"carries a personal identifier"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "a tag MESSAGE holding a byte that is no UTF-8, beside the banned host, under a UTF-8 locale and the REAL grep: the hit is named through a real push and the remote never gets the tag (without -a, GNU grep calls the line binary and a match on it is a note and no line, exit 0, which read as no hit)" {
    locale -a 2>/dev/null | grep -qix 'C\.UTF-8\|C\.utf8' || skip "no C.UTF-8 locale on this machine"
    export LC_ALL=C.UTF-8
    add_remote
    commit_msg ok.txt "clean"
    git -C "$REPO" push -q origin main
    commit="$(git -C "$REPO" rev-parse HEAD)"
    # the tag object built by hand (git tag would not write the byte): its message's second line carries the banned host and a 0xFF byte
    printf 'object %s\ntype commit\ntag v2\ntagger Tester <tests@example.invalid> 1700000000 +0000\n\nrelease two\ncut on TESTHOST \377\n' "$commit" > "$TEST_DIR/tagobj"
    sha="$(git -C "$REPO" hash-object -t tag -w --stdin --literally < "$TEST_DIR/tagobj")"
    git -C "$REPO" update-ref refs/tags/v2 "$sha"
    [ "$(git -C "$REPO" cat-file -t "$sha")" = tag ]
    # the road, with the real grep and no shim: without -a a match on that line is a note on stderr, no line on stdout, exit 0
    run _hook_in "$REPO" -c 'git cat-file -p "$1" | grep -in -F -e TESTHOST; echo "status $?"' _ "$sha"
    [[ "$output" == *"status 0"* ]]
    [[ "$output" != *"7:"* ]]
    run _hook_in "$REPO" -c 'git cat-file -p "$1" | grep -in -a -F -e TESTHOST; echo "status $?"' _ "$sha"
    [[ "$output" == *"7:cut on TESTHOST"* ]]
    push_ref_through_hook refs/tags/v2
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of tag refs/tags/v2 (${sha:0:10}) carries a personal identifier on line 2"* ]]
    [[ "$output" != *"TESTHOST"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    [[ "$output" == *"git tag -f -a <name> <commit>"* ]]
    run remote_holds_ref refs/tags/v2
    [ "$status" -ne 0 ]
}

@test "a MESSAGE log that answers NOTHING (git log exiting 0 with no line, for any format holding %B) over a commit whose subject names a banned host is refused as unscanned naming the read and the empty first line, through a real push: the format asks for a marker line ahead of the message, so an answer without it is short, and the remote holds nothing" {
    add_remote
    commit_msg web.txt "fix the crash on TESTHOST"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git_refusing '[ "${1:-}" = log ] && [[ "${4:-}" == --format=*%B* ]]' 0 ""
    run _hook_in "$REPO" -c 'git log -1 --no-show-signature --format=message%x09%H%n%B%nend%x09%H "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    push_ref_through_hook_with_shim main
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit ${sha:0:10} could not be read (git log exited 0 and answered \"\" on its first line, not the marker line the format asks for ahead of the message)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"carries a personal identifier"* ]]
    run remote_holds_ref refs/heads/main
    [ "$status" -ne 0 ]
}

@test "a tag OBJECT that reads as NOTHING (cat-file -p exiting 0 with no output) over a tag whose message names a banned host is refused as unscanned naming the capture's byte count and the object's size, through a real push: every capture is judged against the size (round 8), so an empty capture of an object with bytes is a short read of 0 bytes, the tag's fields are parsed from that one capture, and the remote never gets the tag" {
    tag_over_clean_commit_on_remote "release one" "cut on TESTHOST"
    size="$(git -C "$REPO" cat-file -s "$sha")"
    [ "$size" -gt 0 ]
    git_refusing "[ \"\${1:-}\" = cat-file ] && [ \"\${2:-}\" = -p ] && [ \"\${3:-}\" = $sha ]" 0 ""
    run _hook_in "$REPO" -c 'git cat-file -p "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    push_ref_through_hook_with_shim refs/tags/v1
    [ "$status" -ne 0 ]
    [[ "$output" == *"the OBJECT of tag refs/tags/v1 (${sha:0:10}) was read short (git cat-file -p exited 0 and its capture holds 0 bytes where git cat-file -s gives the object's size as $size), which ends the peel here"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"carries a personal identifier"* ]]
    [[ "$output" != *"while its type read as tag"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "an awk exiting 0 and printing nothing for the program that read a tag's MESSAGE at the round 6 text changes nothing now: the tag's message is parsed by the shell from the object capture, the hit is named through a real push, and the remote never gets the tag" {
    tag_over_clean_commit_on_remote "release one" "cut on TESTHOST"
    awk_silent_on_program '!hdr { print }'
    run _hook_in "$REPO" -c 'printf "a\n\nb\n" | awk "BEGIN { hdr = 1 } hdr && !NF { hdr = 0; next } !hdr { print }"; echo "status $?"'
    [ "$output" = "status 0" ]
    push_ref_through_hook_with_shim refs/tags/v1
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of tag refs/tags/v1 (${sha:0:10}) carries a personal identifier on line 3"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

# ── round 8: an answer cut SHORT after the sibling fact, and a blank header terminator ──
# Round 7's refuters (2026-09-23) found the two message reads bounded at one
# end: the commit's log asked for a marker AHEAD of the message, which
# witnesses that the read began and not that it ended, so a log answering the
# marker and the subject alone passed the body unread; and the tag OBJECT
# capture was judged against the object's size only when EMPTY, so a
# cat-file -p answering the header and the blank line alone was parsed as a
# tag with no message. Each published a banned message through a real push
# with nothing printed. The log asks for a TAIL marker after the message now
# (the message is the text between the markers; a head marker with no tail is
# refused as short), and every tag capture's byte count is judged against the
# object's size (cat-file -p prints a tag object as its raw bytes, so the two
# agree for every whole read, an empty message's included). The same refuter
# found the shell parse of round 7 ending a tag's header at an EMPTY line where
# the awk it replaced ended it at a BLANK one: a hand-built tag whose
# terminator was a space alone had its message read as header lines. The
# header ends at the first blank line now, the awk's !NF exactly.
git_answering_head_lines_on() {   # <bash test over the shim's "$@"> <N>: for that shape the real git runs and only the first N lines of its answer are printed, exit 0 (an answer cut short after the marker); the real git for every other shape
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if %s; then %q "$@" | head -n %d; exit 0; fi\n' "$1" "$real_git" "$2"
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}
git_answering_header_only_on_cat_file_p() {   # <sha>: a git whose `cat-file -p <sha>` prints the object's header lines and the blank line after them, exit 0, and nothing more (the round 7 refuters' header-only shim); the real git for every other command
    local real_git
    real_git="$(command -v git)"
    mkdir -p "$TEST_DIR/shim"
    {
        printf '#!/usr/bin/env bash\n'
        printf 'if [ "${1:-}" = cat-file ] && [ "${2:-}" = -p ] && [ "${3:-}" = %q ]; then %q "$@" | sed "/^$/q"; exit 0; fi\n' "$1" "$real_git"
        printf 'exec %q "$@"\n' "$real_git"
    } > "$TEST_DIR/shim/git"
    chmod 755 "$TEST_DIR/shim/git"
    export PATH="$TEST_DIR/shim:$PATH"
}

@test "a MESSAGE log answering the marker line and the subject alone (git log exiting 0, the body and the tail marker cut off) over a commit whose BODY names a banned host is refused as unscanned naming the read and its last line, through a real push: a marker ahead of the message bounds its start alone, so the format asks for a tail marker too and an answer without it is short, and the remote holds nothing (the round 7 text grepped the subject alone and published the commit)" {
    add_remote
    commit_msg web.txt "fix: a subject" "seen on TESTHOST"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    git_answering_head_lines_on '[ "${1:-}" = log ] && [[ "${4:-}" == --format=message* ]]' 2
    run _hook_in "$REPO" -c 'git log -1 --no-show-signature --format=message%x09%H%n%B%nend%x09%H "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [ "$output" = "$(printf 'message\t%s\nfix: a subject' "$sha")" ]   # the head marker and the subject: no body, no tail marker
    push_ref_through_hook_with_shim main
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of commit ${sha:0:10} was read short (git log exited 0 and answered \"fix: a subject\" on its last line, not the tail marker line the format asks for after the message)"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"carries a personal identifier"* ]]
    [[ "$output" != *"not the marker line the format asks for ahead of the message"* ]]   # the head marker was there: the other arm's cause
    run remote_holds_ref refs/heads/main
    [ "$status" -ne 0 ]
}

@test "a tag OBJECT capture cut short after the HEADER and the blank line (cat-file -p exiting 0, the message cut off) over a tag whose message names a banned host is refused as unscanned naming the capture's byte count and the object's size, through a real push: every capture is judged against the size now, not only an empty one, so a header-only answer is not a tag with no message, and the remote never gets the tag (the round 7 text parsed it as one and published the tag)" {
    tag_over_clean_commit_on_remote "release one" "cut on TESTHOST"
    size="$(git -C "$REPO" cat-file -s "$sha")"
    git_answering_header_only_on_cat_file_p "$sha"
    run _hook_in "$REPO" -c 'git cat-file -p "$1"' _ "$sha"
    [ "$status" -eq 0 ]
    [[ "$output" == "object "*"tagger "* ]]
    [[ "$output" != *"release one"* ]]                          # the header alone: the message is cut off
    bytes="$(_hook_in "$REPO" -c 'git cat-file -p "$1" | wc -c' _ "$sha")"
    bytes="${bytes//[[:space:]]/}"
    [ "$bytes" -gt 0 ] && [ "$bytes" -lt "$size" ]
    push_ref_through_hook_with_shim refs/tags/v1
    [ "$status" -ne 0 ]
    [[ "$output" == *"the OBJECT of tag refs/tags/v1 (${sha:0:10}) was read short (git cat-file -p exited 0 and its capture holds $bytes bytes where git cat-file -s gives the object's size as $size), which ends the peel here"* ]]
    [[ "$output" == *"the scan is incomplete, so the push is refused"* ]]
    [[ "$output" != *"carries a personal identifier"* ]]
    run remote_holds_ref refs/tags/v1
    [ "$status" -ne 0 ]
}

@test "a hand-built tag whose header ends at a WHITESPACE-ONLY line (a space alone, and a tab alone; git hash-object -t tag -w --literally) with a message naming a banned host is refused naming the tag and the message line, through a real push of each, and the remote never gets either: the header ends at the first BLANK line, as the awk the shell parse replaced ended it (the round 7 text ended it at an EMPTY line, read the message as header lines and published both)" {
    add_remote
    commit_msg ok.txt "clean"
    git -C "$REPO" push -q origin main
    commit="$(git -C "$REPO" rev-parse HEAD)"
    sp="$(printf 'object %s\ntype commit\ntag sp\ntagger Tester <tests@example.invalid> 1700000000 +0000\n \nrelease one\ncut on TESTHOST\n' "$commit" | git -C "$REPO" hash-object -t tag -w --stdin --literally)"
    tab="$(printf 'object %s\ntype commit\ntag tab\ntagger Tester <tests@example.invalid> 1700000000 +0000\n\t\nrelease one\ncut on TESTHOST\n' "$commit" | git -C "$REPO" hash-object -t tag -w --stdin --literally)"
    git -C "$REPO" update-ref refs/tags/sp "$sp"
    git -C "$REPO" update-ref refs/tags/tab "$tab"
    [ "$(git -C "$REPO" cat-file -t "$sp")" = tag ]
    [ "$(git -C "$REPO" cat-file -p "$sp" | sed -n 5p)" = " " ]            # the terminator: a space alone
    [ "$(git -C "$REPO" cat-file -p "$tab" | sed -n 5p)" = "$(printf '\t')" ]   # a tab alone
    push_ref_through_hook refs/tags/sp
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of tag refs/tags/sp (${sp:0:10}) carries a personal identifier on line 2"* ]]
    [[ "$output" != *"the scan is incomplete"* ]]
    run remote_holds_ref refs/tags/sp
    [ "$status" -ne 0 ]
    push_ref_through_hook refs/tags/tab
    [ "$status" -ne 0 ]
    [[ "$output" == *"the MESSAGE of tag refs/tags/tab (${tab:0:10}) carries a personal identifier on line 2"* ]]
    run remote_holds_ref refs/tags/tab
    [ "$status" -ne 0 ]
}
