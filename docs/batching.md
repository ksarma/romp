# Landing PRs in a batch

PRs on this fork land in batches. One session, the batcher, merges the heads of every ready PR into
a branch `batch/<date><letter>`, runs the local test sweep (`scripts/sweep.py`) once at that head,
and opens one PR to main with a generated body. The maintainer reads that one page, drops anything
he does not want with a comment, and merges once with a merge commit. GitHub then marks every
member PR merged on its own, because a PR counts as merged when its head becomes reachable from its
base branch through another merge. No PR is merged into another PR's branch, and no batch is
squashed or rebased.

GitHub's CI runs once per batch, on the push of the batch branch. Member PRs run no CI of their
own, and neither does the merge to main: a batch lands only when its head contains main, so the
merged tree is the tree the sweep and CI tested.

The tooling is `scripts/batch.py` (subcommands `plan`, `assemble`, `verify`, `summarize`, `pull`,
`land`, `finish`, `bisect`; `--help` on each), `scripts/sweep.py` (`run` sweeps a worktree's head
and records the result, `check` reads it back), `scripts/land.sh`, which merges a batch PR by hand
and nothing else (a single PR lands as a one-member batch), and `scripts/pr-orphans.sh`, which reports a merged PR whose content never reached main (it
also runs on every push to main).

## If you open a PR

1. Base it on main. If it depends on an open PR you own, base it on that branch and put
   `Depends-on: #N` on one of the body's first 20 lines, outside fenced code (one PR per line, or
   `#N, #M` on one line), so the batcher orders it. Do not open a PR against another session's
   branch. Do not merge a PR into another PR's branch. If a PR's base branch belongs to a PR that
   has already merged, retarget it before anything else: `gh pr edit N --base main`; `plan` leaves
   such a PR out, naming the fix.
2. Give it one tier label: `docs`, `fix`, `feature`, or `major-feature`
   (`gh pr edit N --add-label fix`); `tests-only`, the old name for `docs` (upstream renamed the
   label on 2026-09-08 and still accepts the old spelling), is accepted too. A `major-feature` PR is
   discussed before it joins a batch; a `hold` label keeps a PR out of the next batch.
3. Sweep your head before its review round and again before its closing check:
   `scripts/sweep.py run --tree <your worktree>`. The round and the check read that result
   (`scripts/sweep.py check --tree <your worktree>`) where they read CI before, and it must pass
   at the head they read; a push after the sweep needs a new one. `scripts/batch.py plan` leaves out
   a PR whose head has no passing result, naming the case (missing, stale, red and the rest), and
   `assemble --repin` refuses a new head without one. Both read the batcher's state dir, so a
   result recorded on another machine is missing there: say so, and the batcher sweeps your head.
4. Optionally end the body with a trailer the batch body reads:
   `<!-- romp-pr: {"tier":"fix","rounds":8,"sweep":{"pytest":"8461 passed","bats":528,"npm":3013,"typecheck":"clean"},"sweep_head":"<sha>","flakes":[]} -->`.
   A missing trailer is not a failure; the member is listed under "Read these first" with "not
   stated", which costs the maintainer a look.
5. For an upstream-worthy change, add the ledger entry file and commit it with the change. Do not
   edit UPSTREAM.md.
6. Do not click merge. If a change must land now, say so in the body; it lands as a one-member
   batch (`scripts/batch.py plan --only N`) on the maintainer's word. Nothing merges alone.
7. Once the batcher has commented `in batch <name> at <sha>` on your PR, do not push to the branch.
   If a review finds something, push the fix, sweep the new head, and tell the batcher by postal
   (kind: coordinate); it re-pins your head and rebuilds. A push after the cut leaves your PR open after the batch merges,
   and `finish` reports that rather than hiding it.
8. When the batch merges, remove your worktree and local branch. `finish` deletes the remote one.
9. Expect no CI on your PR. Its one check is the tier label, which runs when the PR opens or
   reopens and when its labels change, not on a push. The tests run in your own sweep at your head
   (item 3), in the batch's sweep at the batch head, and in the one CI run on the batch branch.

## If you are the maintainer

Once, already done on this fork: delete branches on merge, squash and rebase merges off, so
"Create a merge commit" is the only button. A ruleset on main (required checks by name, strict mode
on, admin bypass) is optional and comes after the first batch has shown the check names. On a batch
PR a required CI check is met by the run of the push to its branch, which attaches to the batch head.
Strict mode ("require branches to be up to date") makes GitHub itself refuse a batch PR that is
behind main, which is the case the no-CI-on-main rule cannot allow; without it only `scripts/batch.py
land` checks. A member PR has no CI checks and never merges by itself: a single PR lands as a
one-member batch, and `scripts/land.sh` merges only a batch PR.

Auto-merge (`gh pr merge --auto`) needs two things: the repository's "Allow auto-merge" setting
(`gh api repos/{owner}/{repo} --jq .allow_auto_merge`; off on this fork today, and turning it on is
your call: `gh repo edit --enable-auto-merge`) and a rule on main that gates a merge: a ruleset rule
of type `required_status_checks` or `pull_request` (`required_deployments`, `merge_queue` and
`code_scanning` count too), or classic branch protection with required status checks or required
reviews. A ruleset that only blocks force pushes or deletion does not count. Without the setting
GitHub rejects it; without such a rule it merges at once and protects nothing. `scripts/land.sh
--auto` and `scripts/batch.py land --auto` read both and refuse, naming the missing one or the rules
they found instead. A rules read that fails, or a protection read that fails with anything but a 404
(GitHub's answer for no protection), is refused with gh's error, not reported as none. Neither adds
`--auto` on its own.

Per batch, in order:

1. Open the batch PR and read the first block: what was verified, at which SHA (the sweep's legs
   and their exit status, provenance clean, main contained). If it is missing or says anything but
   green, stop and tell the batcher.
2. Read "Read these first". For a conflict resolution, expand the diff from the clean merge: that
   is the only code no one else has reviewed. When one side was taken outright, the line says
   whose version. For a kernel-touching or unlabeled member, open the member PR only if its row
   does not answer your question.
3. Skim the members table. A row saying "not stated" is a session that skipped the trailer; pull it
   or accept it.
4. Read "Upstream entries this batch adds or changes". Prune or promote later by editing `status:`
   in the entry file.
5. To drop a member, comment `pull #N`. The batch is rebuilt without it (and without anything that
   depends on it); wait for the new green.
6. Merge: say "merge batch #B" to the batcher, who runs `scripts/batch.py land`: it requires the
   batch branch's CI run green at the batch head, reads main on origin again right before the merge
   and refuses if the batch no longer contains it. The button and `gh pr merge <B> --merge
   --match-head-commit <sha>` check neither. No CI runs on the merge to main, so use either only
   while the batch PR's checks on its head are green and main is still at the SHA the first block
   names as contained; if main has moved, ask the batcher to merge it in, sweep and verify again. Member PRs
   read merged on their own and their branches are deleted. If you merge by hand, tell the batcher
   to run `finish`.
7. Nothing else. To revert a member later, `git revert -m 1 <its merge commit>` on a branch, as a PR.

A PR that cannot wait lands as a one-member batch, never alone: `scripts/batch.py plan --only N`
(`--only N --only M` for a pair; a dependency not named leaves its dependent out), then batcher
steps 2 to 5 and 8. It gets its own sweep at the batch head and the one CI run, like any batch.
One batch at a time still holds, so while a batch is open the PR joins it (a re-plan and rebuild)
or waits for it to land.

`scripts/land.sh B` merges a batch PR by hand (`--help` prints the refusal table). It refuses any PR
that is not a batch PR, one without the `batch` label or whose head branch is not `batch/<name>`,
and names the one-member batch route, so it never merges a member PR. For a batch PR it reads the
checks GitHub reports at the head (failing refused; pending, or blocked by a rule on main, refused
without `--auto`), the mergeability and the merge state, merges with a merge commit pinned to the
head it checked, and runs the orphan check afterward. It reads neither the sweep result nor main,
so treat it as the button (step 6): only while the batch PR's checks are green and main is still at
the SHA the first block names. It still takes two numbers and keeps its rules for a stacked pair
(the lower PR first, each read again right before its merge, a stop when a head moved) from when it
merged member PRs; with one batch open at a time, one number is the case.

It never passes `--delete-branch`: gh's flag also deletes the local branch, which is checked out in
a session's worktree here; the remote branch is deleted by the repository setting, or through the
API when that setting is off. The web button is equally safe now that branches delete on merge. If
main moves while a batch is open, `verify` refuses the batch as behind until the batcher merges main
into it, sweeps again and re-verifies (batcher step 7).

## If you are the batcher

One batcher at a time: the branch `origin/batch/*` is the mutex, and your working note names the
batch and its members. Any change you make outside a merge commit is its own commit with a `batch:`
subject; `verify` refuses the branch otherwise.

1. `scripts/batch.py plan`: every ready PR, dependencies first, then by number. `plan --labeled`
   takes only PRs labeled `land`. A PR whose head has no passing sweep result of its own in your
   state dir is left out with the case named, and its dependents with it (the author owes one;
   when theirs was recorded on another machine, sweep that head here and plan again). Message the
   authors of missing trailers once.
2. `scripts/batch.py assemble <name>`. A conflicting member is held back and its owner told; the
   comment names what it conflicts with: origin/main when the member conflicts with main on its
   own, otherwise the earlier members whose diffs touch the same files (or the batch, when none
   does). To resolve a small conflict instead, `assemble <name> --resolve N`, resolve per hunk in
   the batch worktree, `git add` the files, then
   `assemble <name> --continue --reviewed '<who, verdict>'`. A resolution may change only the files
   that conflicted (plus entry files under `upstream/` when UPSTREAM.md was one of them):
   `--continue` refuses a staged change to any other path, naming the path and the `git restore`
   command that puts the merge's own content back; move such a change into a separate `batch:`
   commit after the merge instead. A member whose head is already in the batch (reachable through
   an earlier member's head) gets no merge commit of its own; it is recorded as contained, lands
   with the batch, and the body lists it as such under "Read these first" and in its table row.
3. Run the local sweep at the batch head: `scripts/sweep.py run --tree ../romp-batch-<name>`.
   `--python` names the interpreter for pytest (it needs pytest, pytest-xdist and pytest-timeout);
   `--wrap LEG=PREFIX` runs a leg under this machine's slot or scope wrapper. It runs pytest, bats,
   the manager and tooling node tests and the ledger check, plus `npm run typecheck`, `npm test` and
   `npm run build` when `kernel/kernel.py`, `ui/` or `vscode-extension/` changed since the merge
   base with origin/main (the webview rule in CLAUDE.md), and writes every leg's exit status to
   `<state dir>/sweeps/<full sha>.json`. The state dir is `$ROMP_STATE_DIR`, else
   `$XDG_STATE_HOME/romp`, else `~/.local/state/romp`, so run `sweep.py` and `batch.py` with the
   same environment. It refuses a dirty tree and records the run invalid if HEAD or the tree changes
   while it runs. When one leg fails on a known flake,
   `scripts/sweep.py run --tree ../romp-batch-<name> --leg <leg> --flake '<the flake>'` re-runs that
   leg alone at the same head; `--flake` names the failing test and where it is recorded as a known
   flake. The runner refuses a re-run without `--flake`, of a leg that did not fail, or of a leg
   already re-run once. The leg's record keeps both runs: the re-run, and the first failure with the
   flake and the sha each ran at. `verify` counts a re-run only when all three are there and name the
   batch head's sha, and the body's first block names the first failure and the flake. Any other
   failure means a full sweep again. `scripts/sweep.py check --tree ../romp-batch-<name>` prints what
   `verify` will read.
4. `scripts/batch.py verify <name>`. It reads the sweep result for the batch head's full sha and
   fails by name when it is missing, stale (recorded at another commit), unfinished, red, invalid,
   incomplete or unreadable. A missing result names the directory verify read and the variable it
   came from (`ROMP_STATE_DIR`, `XDG_STATE_HOME` or `HOME`): a sweep run with another environment
   wrote its result somewhere else. It also fails as "behind" when the batch head does not contain main as
   origin has it now: CI does not run on the merge to main, so a batch lands only when the tree that
   lands is the tree the sweep and the batch's CI ran on; run step 7, then steps 3 and 4 again. If
   an earlier `assemble` died part-way, `verify` fails with "assembly incomplete"; run `assemble`
   again first.
5. `git push -u origin batch/<name>` (after a rebuild, `git push --force-with-lease origin
   batch/<name>`; `pull` pushes that way itself). If the pre-push hook refuses the push: it scans
   each pushed commit's tree, so a batch tip that inherits a pre-scrub string trips it although the
   new commits are merges; read what tripped and fix the member or ask. Never bypass the hook. Then
   `scripts/batch.py summarize <name>` and watch the one CI run: the push to `batch/<name>` starts
   it, the batch PR shows its checks on its head, and a newer push to the branch cancels the older
   run. The batch PR carries the `batch` label and no tier; the fork's copy of the `PR tier` check
   counts `batch` as its one label, so that check is green when the PR opens. It does not run on a
   push, so after a rebuild the new head shows no `PR tier` check until a label changes; nothing
   gates on it. If CI is red:
   `scripts/batch.py bisect <name> -- <failing test>` names the member;
   `scripts/batch.py pull <name> N` rebuilds without it and says so on the PR.
6. When a member's owner pushes a fix after the cut (they tell you by postal), run
   `scripts/batch.py assemble <name> --repin N` (re-reads that head and rebuilds the branch;
   `--repin all` re-reads every member; a re-read head without a passing sweep of its own is
   refused and nothing is re-pinned), then repeat steps 3 to 5. Without the re-pin, `verify`
   fails on the moved head.
7. When main moves, `verify` refuses the batch as behind (and the batch PR may read conflicting);
   run `scripts/batch.py assemble <name> --merge-main`: it merges origin/main into the assembled batch
   in its worktree (`../romp-batch-<name>`) instead of rebuilding. A clean merge is recorded. A
   conflict stops with exit 3, as `--resolve` does: resolve per hunk, `git add` the files, then
   `assemble <name> --continue --reviewed '<who, verdict>'` records it (or `--abort` drops the
   merge), and the body lists the merge under "Read these first" and in the conflict resolutions
   block. Then repeat steps 3 to 5.
8. On the maintainer's word: `scripts/batch.py land <name>`. It verifies again (the sweep result at
   the verified head, main contained), then asks GitHub for the batch head's CI run: the newest run
   of `ci.yml` from a push to `batch/<name>` at exactly the verified head, read at that moment. It
   refuses when that run is missing, pending or red (any conclusion but success, cancelled
   included), or when the read fails; a run of another commit, a manual run and a run on another
   branch do not count. Then it reads main on origin once more right before the merge call and
   refuses if it moved, merges with a merge commit, and runs `finish`. GitHub's merge pins the
   head, not the base, so a merge to main between that last read and the merge call is not caught.
   `land --auto` arms auto-merge instead, after the same CI read (it does not wait for a pending
   run): it needs the repository's "Allow auto-merge" setting and a
   rule on main that gates a merge (the maintainer section above names the types), reads both before
   it retargets anything, and refuses naming what is missing or the rules it found instead; run
   `finish` once the PR lands. Auto-merge merges later, when the rule is met, and land cannot check
   main again then. If the maintainer merged by the button or `gh pr merge`, check that the merge
   commit's first parent is the main that verify saw (`git rev-parse <merge>^1` against the SHA the
   body's first block names), then run `scripts/batch.py finish <name>` alone. If it is not, the tree
   on main was never swept or tested: run `scripts/sweep.py run` on a worktree at the merge commit
   now and tell the maintainer what it finds.

## Checked on the first batch

The tools check four points about GitHub's behavior and record what they find, so the first batch
settles them:

- whether indirect-merge marking fires for every member (`finish` reports any member that stays
  open);
- whether GitHub deletes the head branch of an indirectly merged PR (`finish` deletes it if not and
  records which case it met);
- whether a dependent retargeted to main before its base branch is deleted stays open against main
  (`finish` rechecks after the deletion);
- whether a stacked member retargeted to main after the merge is marked merged (`land` retargets
  before the merge so the documented rule applies; `finish` records the outcome when it had to
  retarget afterward).

Two more, about CI running on the batch branch only (2026-09-27), are for the batcher to look at on
the first batch that lands under it; no tool records them:

- whether the batch PR shows the checks of the push run on its head (the Checks tab, and
  `gh pr view <B> --json statusCheckRollup`);
- whether a newer push to the batch branch cancels the run of the older one (the Actions tab).
