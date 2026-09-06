#!/usr/bin/env bats

# scripts/pr-orphans.sh: a merged PR whose merge commit is not an ancestor of main is printed as
# `#N` and the script exits 1; a clean set exits 0. The case it guards: a PR merged into another
# PR's branch after that base had already merged, so GitHub shows it merged while its content sits
# on a branch nobody has a PR for.
#
# A merged PR with no merge commit recorded (GitHub does not document what it records for a PR
# marked merged indirectly) is judged by its head commit instead: on main is clean, off main is
# "unknown, check by hand" (exit 1, distinct wording).
#
# The GitHub CLI is a stub on PATH that prints whatever rows the test hands it, so nothing here
# reaches GitHub; the ancestry is real, checked against a fixture repository.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

load git-hermetic

setup() {
    git_hermetic
    TEST_DIR="$(mktemp -d)"
    REPO="$TEST_DIR/repo"
    mkdir -p "$REPO/scripts" "$TEST_DIR/bin"
    cp "$ROMP_DIR/scripts/pr-orphans.sh" "$REPO/scripts/"
    git init -q "$REPO"
    git -C "$REPO" symbolic-ref HEAD refs/heads/main
    echo seed > "$REPO/f"
    git -C "$REPO" add f && git -C "$REPO" commit -qm seed
    # keyfree: one commit K, merged into main through "PR #4" (a merge commit ON main).
    git -C "$REPO" checkout -qb keyfree
    echo k > "$REPO/k" && git -C "$REPO" add k && git -C "$REPO" commit -qm k
    K="$(git -C "$REPO" rev-parse HEAD)"
    # dep: stacked on keyfree, then merged INTO keyfree ("PR #5") after keyfree had merged: its
    # merge commit M is on keyfree only, never on main.
    git -C "$REPO" checkout -qb dep
    echo d > "$REPO/d" && git -C "$REPO" add d && git -C "$REPO" commit -qm d
    D="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q keyfree
    git -C "$REPO" merge -q --no-ff -m "Merge #5: dep" dep
    M="$(git -C "$REPO" rev-parse HEAD)"
    git -C "$REPO" checkout -q main
    git -C "$REPO" merge -q --no-ff -m "Merge #4: keyfree" "$K"
    MAIN_MERGE="$(git -C "$REPO" rev-parse HEAD)"
    export ROWS="$TEST_DIR/rows.tsv"
    export HEADS="$TEST_DIR/heads.tsv"   # number <tab> headRefOid, for `pr view N --json headRefOid`
    : > "$HEADS"
    export GH_LOG="$TEST_DIR/gh.log"
    cat > "$TEST_DIR/bin/gh" <<'STUB'
#!/usr/bin/env bash
echo "$@" >> "$GH_LOG"
case "$1 $2" in
  "pr list") cat "$ROWS" ;;
  "pr view") sha="$(awk -F'\t' -v n="$3" '$1 == n { print $2 }' "$HEADS")"
             [ -n "$sha" ] && printf '{"headRefOid": "%s"}\n' "$sha" ;;
esac
exit 0
STUB
    chmod +x "$TEST_DIR/bin/gh"
    export PATH="$TEST_DIR/bin:$PATH"
}

teardown() { rm -rf "$TEST_DIR"; }

@test "a merged PR whose merge commit is not an ancestor of main exits 1 and prints the number" {
    printf '4\t%s\tmain\n5\t%s\tkeyfree\n' "$MAIN_MERGE" "$M" > "$ROWS"
    run "$REPO/scripts/pr-orphans.sh"
    [ "$status" -eq 1 ]
    [[ "$output" == *"#5"* ]]
    [[ "$output" != *"#4"* ]]
    [[ "$output" == *"merged into 'keyfree'"* ]]
    [[ "$output" == *"1 merged PR(s) whose content never reached main"* ]]
}

@test "a clean set exits 0" {
    printf '4\t%s\tmain\n' "$MAIN_MERGE" > "$ROWS"
    run "$REPO/scripts/pr-orphans.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"pr-orphans: clean (1 merged PR(s) checked against main)"* ]]
}

@test "no merge commit recorded, head on main: clean, with a note, and the head was asked for" {
    printf '6\tnone\tmain\n' > "$ROWS"
    printf '6\t%s\n' "$K" > "$HEADS"
    run "$REPO/scripts/pr-orphans.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"#6 has no merge commit recorded; its head ${K:0:10} is on main"* ]]
    [[ "$output" == *"pr-orphans: clean (1 merged PR(s) checked against main; 1 with no merge commit recorded, reached main by head)"* ]]
    grep -q -- "pr view 6 --json headRefOid" "$GH_LOG"
}

@test "no merge commit recorded, head off main: reported as unknown, check by hand, exit 1" {
    printf '6\tnone\tmain\n' > "$ROWS"
    printf '6\t%s\n' "$D" > "$HEADS"
    run "$REPO/scripts/pr-orphans.sh"
    [ "$status" -eq 1 ]
    [[ "$output" == *"#6"* ]]
    [[ "$output" == *"no merge commit recorded, and its head $D is not an ancestor of main: unknown, check by hand"* ]]
    [[ "$output" == *"1 merged PR(s) with no merge commit recorded and a head not on main (of 1 checked): unknown, check by hand."* ]]
    [[ "$output" != *"never reached main"* ]]
}

@test "no merge commit recorded and no head answer: unknown, not stranded" {
    printf '6\tnone\tmain\n' > "$ROWS"
    run "$REPO/scripts/pr-orphans.sh"
    [ "$status" -eq 1 ]
    [[ "$output" == *"#6"* ]]
    [[ "$output" == *"its head (unknown) is not an ancestor of main: unknown, check by hand"* ]]
    [[ "$output" != *"never reached main"* ]]
}

@test "a stranded PR and an unknown one are each counted under their own wording" {
    printf '5\t%s\tkeyfree\n6\tnone\tmain\n' "$M" > "$ROWS"
    printf '6\t%s\n' "$D" > "$HEADS"
    run "$REPO/scripts/pr-orphans.sh"
    [ "$status" -eq 1 ]
    [[ "$output" == *"1 merged PR(s) whose content never reached main (of 2 checked)"* ]]
    [[ "$output" == *"1 merged PR(s) with no merge commit recorded and a head not on main (of 2 checked)"* ]]
}

@test "the stub was asked for merged PRs with the three fields the check needs" {
    printf '4\t%s\tmain\n' "$MAIN_MERGE" > "$ROWS"
    run "$REPO/scripts/pr-orphans.sh"
    [ "$status" -eq 0 ]
    grep -q -- "pr list --state merged --limit 200 --json number,mergeCommit,baseRefName" "$GH_LOG"
    ! grep -q -- "pr view" "$GH_LOG"   # a recorded merge commit needs no second read
}

@test "with an origin, the check is against origin/main, not a stale or ahead local main" {
    git init -q --bare "$TEST_DIR/origin.git"
    git -C "$REPO" remote add origin "$TEST_DIR/origin.git"
    git -C "$REPO" push -q origin main
    # A local commit on main that origin never saw is not "on main" for anyone else.
    echo local > "$REPO/l" && git -C "$REPO" add l && git -C "$REPO" commit -qm local
    LOCAL="$(git -C "$REPO" rev-parse HEAD)"
    printf '7\t%s\tmain\n' "$LOCAL" > "$ROWS"
    run "$REPO/scripts/pr-orphans.sh"
    [ "$status" -eq 1 ]
    [[ "$output" == *"#7"* ]]
    [[ "$output" == *"against origin/main"* ]] || [[ "$output" == *"not an ancestor of origin/main"* ]]
    # Once pushed, the same PR is clean.
    git -C "$REPO" push -q origin main
    run "$REPO/scripts/pr-orphans.sh"
    [ "$status" -eq 0 ]
}

@test "a clone without any main branch fails loudly" {
    git -C "$REPO" checkout -q keyfree
    git -C "$REPO" branch -D main >/dev/null
    printf '4\t%s\tmain\n' "$MAIN_MERGE" > "$ROWS"
    run "$REPO/scripts/pr-orphans.sh"
    [ "$status" -eq 2 ]
    [[ "$output" == *"no main branch"* ]]
}
