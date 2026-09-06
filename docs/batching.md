# Landing PRs in a batch

PRs on this fork land in batches. One session, the batcher, merges the heads of every ready PR into
a branch `batch/<date><letter>`, runs the full test sweep once at that head, and opens one PR to
main with a generated body. The maintainer reads that one page, drops anything he does not want
with a comment, and merges once with a merge commit. GitHub then marks every member PR merged on
its own, because a PR counts as merged when its head becomes reachable from its base branch through
another merge. No PR is merged into another PR's branch, and no batch is squashed or rebased.

The tooling is `scripts/batch.py` (subcommands `plan`, `assemble`, `verify`, `summarize`, `pull`,
`land`, `finish`, `bisect`; `--help` on each), `scripts/land.sh` for one or two PRs that cannot
wait, and `scripts/pr-orphans.sh`, which reports a merged PR whose content never reached main (it
also runs on every push to main).

## If you open a PR

1. Base it on main. If it depends on an open PR you own, base it on that branch and put
   `Depends-on: #N` on one of the body's first 20 lines, outside fenced code (one PR per line, or
   `#N, #M` on one line), so the batcher orders it. Do not open a PR against another session's
   branch. Do not merge a PR into another PR's branch. If a PR's base branch belongs to a PR that
   has already merged, retarget it before anything else: `gh pr edit N --base main`.
   `scripts/land.sh` refuses any base but main (a merged PR's branch, an open PR's branch, a branch
   with no PR), unless the base is the branch of the other PR in the same call, which then merges
   first.
2. Give it one tier label: `fix`, `tests-only`, `feature`, or `major-feature`
   (`gh pr edit N --add-label fix`). A `major-feature` PR is discussed before it joins a batch; a
   `hold` label keeps a PR out of the next batch.
3. Optionally end the body with a trailer the batch body reads:
   `<!-- romp-pr: {"tier":"fix","rounds":8,"sweep":{"pytest":"8461 passed","bats":528,"npm":3013,"typecheck":"clean"},"sweep_head":"<sha>","flakes":[]} -->`.
   A missing trailer is not a failure; the member is listed under "Read these first" with "not
   stated", which costs the maintainer a look.
4. For an upstream-worthy change, add the ledger entry file and commit it with the change. Do not
   edit UPSTREAM.md.
5. Do not click merge. If a change must land now, say so in the body; the maintainer merges it
   alone or asks for it by name.
6. Once the batcher has commented `in batch <name> at <sha>` on your PR, do not push to the branch.
   If a review finds something, push the fix and tell the batcher by postal (kind: coordinate); it
   re-pins your head and rebuilds. A push after the cut leaves your PR open after the batch merges,
   and `finish` reports that rather than hiding it.
7. When the batch merges, remove your worktree and local branch. `finish` deletes the remote one.

## If you are the maintainer

Once, already done on this fork: delete branches on merge, squash and rebase merges off, so
"Create a merge commit" is the only button. A ruleset on main (required checks by name, strict mode
off, admin bypass) is optional and comes after the first batch has shown the check names.

Auto-merge (`gh pr merge --auto`) needs two things: the repository's "Allow auto-merge" setting
(`gh api repos/{owner}/{repo} --jq .allow_auto_merge`; off on this fork today, and turning it on is
your call: `gh repo edit --enable-auto-merge`) and a rule on main that gates a merge: a ruleset rule
of type `required_status_checks` or `pull_request` (`required_deployments`, `merge_queue` and
`code_scanning` count too), or classic branch protection with required status checks or required
reviews. A ruleset that only blocks force pushes or deletion does not count. Without the setting
GitHub rejects it; without such a rule it merges at once and protects nothing. `scripts/land.sh
--auto` reads both and refuses, naming the missing one or the rules it found instead. A rules read
that fails, or a protection read that fails with anything but a 404 (GitHub's answer for no
protection), is refused with gh's error, not reported as none. `scripts/batch.py land --auto` reads
the setting and the rules on main and refuses, naming the one that is missing. Neither adds `--auto`
on its own.

Per batch, in order:

1. Open the batch PR and read the first block: what was verified, at which SHA, provenance clean.
   If it is missing or says anything but green, stop and tell the batcher.
2. Read "Read these first". For a conflict resolution, expand the combined diff: that is the only
   code no one else has reviewed. For a kernel-touching or unlabeled member, open the member PR
   only if its row does not answer your question.
3. Skim the members table. A row saying "not stated" is a session that skipped the trailer; pull it
   or accept it.
4. Read "Upstream entries this batch adds or changes". Prune or promote later by editing `status:`
   in the entry file.
5. To drop a member, comment `pull #N`. The batch is rebuilt without it (and without anything that
   depends on it); wait for the new green.
6. Merge: say "merge batch #B" to the batcher, or click "Create a merge commit", or run
   `gh pr merge <B> --merge --match-head-commit <sha>` (it refuses if the branch moved after you
   read it). Member PRs read merged on their own and their branches are deleted. If you click the
   button yourself, tell the batcher to run `finish`.
7. Nothing else. To revert a member later, `git revert -m 1 <its merge commit>` on a branch, as a PR.

For one or two PRs that cannot wait: `scripts/land.sh N [M]` (`--help` prints the refusal table).
It reads both PRs before merging either, merges each with a merge commit, and runs the orphan check
afterward. It refuses: squash and rebase; a PR that is not open, or a draft; a conflicting PR, or
one whose mergeability GitHub has not computed yet; failing checks (with or without `--auto`);
pending checks or a PR blocked by a rule on main (without `--auto`); a PR behind main; and any base
but main (a merged PR's branch, a branch with no PR, an open PR's branch). A PR with no checks at
all is noted, not refused.

A chain of two PRs lands in one call with no flag: the lower PR merges first whichever order you
typed, its branch is deleted, GitHub retargets the upper PR to main, and it merges there. Each PR is
read again right before its own merge. A head that moved since the check stops the run (exit 2):
nothing more is merged, and the orphan check still runs. A PR the first merge already marked merged
is skipped. To merge only the upper PR, into the lower PR's open branch, `--into-open-pr` overrides
the open-PR's-branch refusal; the content then sits on that branch until the lower PR merges, and
the orphan check reports it until then.

It never passes `--delete-branch`: gh's flag also deletes the local branch, which is checked out in
a session's worktree here; the remote branch is deleted by the repository setting, or through the
API when that setting is off. The web button is equally safe now that branches delete on merge. If
an urgent fix lands while a batch is open, the batcher merges main into the batch and re-verifies
(batcher step 7).

## If you are the batcher

One batcher at a time: the branch `origin/batch/*` is the mutex, and your working note names the
batch and its members. Any change you make outside a merge commit is its own commit with a `batch:`
subject; `verify` refuses the branch otherwise.

1. `scripts/batch.py plan`: every ready PR, dependencies first, then by number. `plan --labeled`
   takes only PRs labeled `land`. Message the authors of missing trailers once.
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
3. Run the full sweep at the batch head (pytest, bats, `npm test`, `npm run typecheck`); re-run the
   known-flake modules alone before calling anything red.
4. `scripts/batch.py verify <name> --sweep '<the counts>'`. If an earlier `assemble` died part-way,
   `verify` fails with "assembly incomplete"; run `assemble` again first.
5. `git push -u origin batch/<name>` (after a rebuild, `git push --force-with-lease origin
   batch/<name>`; `pull` pushes that way itself). If the pre-push hook refuses the push: it scans
   each pushed commit's tree, so a batch tip that inherits a pre-scrub string trips it although the
   new commits are merges; read what tripped and fix the member or ask. Never bypass the hook. Then
   `scripts/batch.py summarize <name>` and watch the one CI run. If CI is red:
   `scripts/batch.py bisect <name> -- <failing test>` names the member;
   `scripts/batch.py pull <name> N` rebuilds without it and says so on the PR.
6. When a member's owner pushes a fix after the cut (they tell you by postal), run
   `scripts/batch.py assemble <name> --repin N` (re-reads that head and rebuilds the branch;
   `--repin all` re-reads every member), then repeat steps 3 to 5. Without the re-pin, `verify`
   fails on the moved head.
7. When main moves and the batch PR reads behind or conflicting, run
   `scripts/batch.py assemble <name> --merge-main`: it merges origin/main into the assembled batch
   in its worktree (`../romp-batch-<name>`) instead of rebuilding. A clean merge is recorded. A
   conflict stops with exit 3, as `--resolve` does: resolve per hunk, `git add` the files, then
   `assemble <name> --continue --reviewed '<who, verdict>'` records it (or `--abort` drops the
   merge), and the body lists the merge under "Read these first" and in the conflict resolutions
   block. Then repeat steps 3 to 5.
8. On the maintainer's word: `scripts/batch.py land <name>`. It verifies again, merges with a merge
   commit, and runs `finish`. `land --auto` arms auto-merge instead: it needs the repository's
   "Allow auto-merge" setting and rules on main (a ruleset or branch protection), reads both before
   it retargets anything, and refuses naming the one that is missing; run `finish` once the PR
   lands. If the maintainer clicked the button, run `scripts/batch.py finish <name>` alone.

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
