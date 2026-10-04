# Landing PRs in a batch

PRs on this fork land in batches. One session, the batcher, merges the heads of every ready PR into
a branch `batch/<date><letter>`, runs the local test sweep (`scripts/sweep.py`) once at that head,
and opens one PR to main with a generated body. The maintainer reads that one page, drops anything
he does not want with a comment, and merges once with a merge commit. GitHub then marks every
member PR merged on its own, because a PR counts as merged when its head becomes reachable from its
base branch through another merge. No PR is merged into another PR's branch, and no batch is
squashed or rebased.

GitHub's CI (`ci.yml`) runs once per batch, on the push of the batch branch. Member PRs run none
of it, and neither does the merge to main, so a batch should land only when its head contains main:
then the merged tree is the tree the sweep and CI tested. `scripts/batch.py land` reads main again
right before the merge and refuses if the batch head no longer contains it; a move after that read
is not stopped, and `finish` reports it loudly (maintainer step 6). One job of `ci.yml`, the secret
scan, also runs in a workflow of its own (`.github/workflows/secret-scan.yml`) on every push of a
branch or a tag whose commit carries that file, a member PR's and the merge to main included, and
on every push to an open PR's branch. GitHub reads a push's workflows from the commit the push puts
on its ref, and a PR's from the merge commit it makes of the PR's head and its base, which carries
the base's copy of the file unless the branch edited or deleted it, so a member PR's pushes are
scanned even on a branch cut from main before the file landed. Among the pushes that start no run: a
push to such a branch that has no open PR, until it merges main; a tag on such a commit; and a push
whose commit lacks the file because it or an earlier commit on its branch deleted it. A PR that
conflicts with its base gets no run of its own until the conflict is resolved (CLAUDE.md,
"Credentials", says what the scan reads, which pushes start no run and GitHub's other limits).
Nothing in the landing reads that workflow's runs.

The tooling is `scripts/batch.py` (subcommands `plan`, `assemble`, `verify`, `summarize`, `pull`,
`land`, `finish`, `bisect`; `--help` on each), `scripts/sweep.py` (`run` sweeps the commit a
worktree's HEAD names, in a private checkout of it, and records the result; `check` reads it back),
`scripts/land.sh <name>`, which runs `scripts/batch.py land` with its arguments and has no merge
logic of its own, and `scripts/pr-orphans.sh`, which reports a merged PR whose content never
reached main (`finish` runs it, and it also runs on every push to main).

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
   `scripts/sweep.py run --tree <your worktree> --python <python>` (step 3 under "If you are the
   batcher" says what that interpreter and your machine need: node, npm, bats, git and gitleaks on
   PATH, the Playwright Chromium the head's lockfile pins, Linux for full reaping, and about 2
   hours of wall time). It owes every leg at your head, as at a batch
   head, the webview legs, the PDF smoke test and the served leg included, whatever you changed. The round and the check read that result
   (`scripts/sweep.py check --tree <your worktree>`, which reads it as `verify` and `plan` do)
   where they read CI before, and it must pass at the head they read; a push after the sweep
   needs a new one. `scripts/batch.py plan` leaves out a PR whose head has no passing result,
   naming the case (missing, stale, red and the rest), and `assemble --repin` refuses a new head
   without one. Both read the batcher's state dir, so a result recorded on another machine is
   missing there: say so, and the batcher sweeps your head.
4. Optionally end the body with a trailer the batch body reads:
   `<!-- romp-pr: {"tier":"fix","rounds":8,"flakes":[]} -->`.
   `rounds` counts the review rounds whose reviewer has reported, so a push that answers round 5's
   findings still says 5, and the count moves to 6 when round 6's report comes in. The body takes
   your review rounds from it. Your sweep is not taken from it: the members table shows the
   passing result `plan` (or `assemble --repin`) read at your pinned head, so sweep counts or a
   sweep sha in the trailer are ignored. A missing trailer is not a failure; the member is listed
   under "Read these first" with "trailer not stated" and its Rounds column reads "not stated",
   which costs the maintainer a look.
5. For an upstream-worthy change, add the ledger entry file and commit it with the change. Do not
   edit UPSTREAM.md.
6. Do not click merge. If a change must land now, say so in the body; it lands as a one-member
   batch (`scripts/batch.py plan --only N`) on the maintainer's word. Nothing merges alone.
7. Once the batcher has commented `in batch <name> at <sha>` on your PR, do not push to the branch.
   If a review finds something, push the fix, sweep the new head, and tell the batcher by postal
   (kind: coordinate); it re-pins your head and rebuilds. A push after the cut leaves your PR open
   after the batch merges, and `finish` reports that rather than hiding it.
8. When the batch merges, remove your worktree and local branch. `finish` deletes the remote one.
9. Expect no `ci.yml` run on your PR. Its Checks tab shows the secret scan's runs of each push
   (`Secret scan on push (gitleaks)`: one for the pull request, and one for the push when its commit
   carries `.github/workflows/secret-scan.yml`, which a branch cut from main before that file landed
   does not until it merges main), the tier-label check after
   the PR opens or reopens or its labels change, not after a push, and Tier policy's skipped rows,
   which evaluate nothing on the fork. The tests run in your own sweep at your head (item 3), in the
   batch's sweep at the batch head, and in the one CI run on the batch branch.

## If you are the maintainer

Once, already done on this fork: delete branches on merge, squash and rebase merges off, so
"Create a merge commit" is the only button. A ruleset on main (required checks by name, strict mode
on, admin bypass) is optional and comes after the first batch has shown the check names. The checks
to require are the job checks a batch push reports: `Python <version> (ubuntu-latest)` for each
Linux cell (3.10, 3.11, 3.12, 3.13 and 3.14t), `Shell (bats, ubuntu-latest)`, `Secret scan (gitleaks)`,
`Vendored tooling (node --test, ubuntu-latest)`, `vscode-extension (typecheck + test + build)` and
`Served pages (pytest, ubuntu-latest)`. A batch push also reports `Secret scan on push
(gitleaks)`, from `.github/workflows/secret-scan.yml`, for the push and, once the batch PR is open,
for the pull request, the same scan as `Secret scan (gitleaks)`
under a name of its own, since a required check is matched by job name whatever the workflow;
requiring `Secret scan (gitleaks)` already covers the scan. Do not require `Exactly one tier
label` on the fork: its copy runs only when a PR opens or reopens or its labels change, never on a
push, so a batch head pushed after the last label event has no run of it, and a ruleset requiring
it would hold that batch. On a batch PR a required CI check is expected to be met by the run of the
push to its branch, attached to the batch head; the first batch confirms that ("Checked on the
first batch", below). Strict mode ("require branches to be up to date") makes GitHub itself refuse a batch PR that is
behind main, which is the case the no-CI-on-main rule cannot allow; without it only `scripts/batch.py
land` checks. A member PR has no `ci.yml` checks and never merges by itself: a single PR lands as a
one-member batch, and `scripts/land.sh` runs `scripts/batch.py land`.

Auto-merge (`gh pr merge --auto`) needs two things: the repository's "Allow auto-merge" setting
(`gh api repos/{owner}/{repo} --jq .allow_auto_merge`; off on this fork today, and turning it on is
your call: `gh repo edit --enable-auto-merge`) and a rule on main that gates a merge: a ruleset rule
of type `required_status_checks` or `pull_request` (`required_deployments`, `merge_queue` and
`code_scanning` count too), or classic branch protection with required status checks or required
reviews. A ruleset that only blocks force pushes or deletion does not count. Without the setting
GitHub rejects it; without such a rule it merges at once and protects nothing. `scripts/batch.py
land --auto` (and `scripts/land.sh --auto`, which runs it) reads both and refuses, naming the
missing one or the rules it found instead. A rules read that fails, or a protection read that fails
with anything but a 404 (GitHub's answer for no protection), is refused with gh's error, not reported
as none. It never adds `--auto` on its own.

Per batch, in order:

1. Open the batch PR and read the first block: what was verified, at which SHA (the sweep's legs
   and their exit status, provenance clean, main contained). If it is missing or says anything but
   green, stop and tell the batcher.
2. Read "Read these first". For a conflict resolution, expand the diff from the clean merge: that
   is the only code no one else has reviewed. When one side was taken outright, the line says
   whose version. For a kernel-touching or unlabeled member, open the member PR only if its row
   does not answer your question.
3. Skim the members table. "Sweep at own head" is the passing result `plan` (or `assemble
   --repin`) read at the member's pinned head, not what the author wrote; it reads "not recorded"
   for a member planned before `plan` recorded it. A Rounds cell saying "not stated" is a session
   that skipped the trailer; pull it or accept it.
4. Read "Upstream entries this batch adds or changes". Prune or promote later by editing `status:`
   in the entry file.
5. To drop a member, comment `pull #N`. The batch is rebuilt without it (and without anything that
   depends on it); wait for the new green.
6. Merge: say "merge batch #B" to the batcher, who runs `scripts/batch.py land`: it requires the
   batch branch's CI run green at the batch head, reads main on origin again right before the merge
   and refuses if the batch no longer contains it. A merge to main between that read and GitHub's
   merge is the one move it cannot stop; `finish`, which land runs next, then fails loudly: the
   merge commit's first parent is not the main verify read, so the tree on main was never swept or
   tested, and it names the sweep at the merge commit that is owed. The button and `gh pr merge <B>
   --merge --match-head-commit <sha>` check neither CI nor main. No `ci.yml` run follows the merge to main, so
   use either only while the batch PR's checks on its head are green, main is still at the SHA the
   first block names as contained, and the batch PR's head is still the SHA the first block names as
   verified (the button merges whatever the branch holds then); if main has moved, ask the batcher
   to merge it in, sweep and verify again, and if the branch has moved, to verify again. Member PRs
   read merged on their own and their branches are deleted. If you merge by hand, tell the batcher to
   run `finish`, which makes the same first-parent check and checks that the merge commit's second
   parent is the head verify read.
7. Nothing else. To revert a member later, `git revert -m 1 <its merge commit>` on a branch, as a PR.

A PR that cannot wait lands as a one-member batch, never alone: `scripts/batch.py plan --only N`
(`--only N --only M` for a pair; a dependency not named leaves its dependent out), then batcher
steps 2 to 5 and 8. It gets its own sweep at the batch head and the one CI run, like any batch.
One batch at a time still holds, so while a batch is open the PR joins it (a re-plan and rebuild)
or waits for it to land.

`scripts/land.sh <name>` runs `scripts/batch.py land <name>` with the same arguments and has no
merge logic of its own, so a batch has one gated merge path: the sweep result at the batch head, the
batch push's CI run, main read again right before the merge, and `finish`'s check of the merge
commit's first parent (`scripts/land.sh --help` prints its usage and then `batch.py land --help`).
It takes the batch's name, not a PR number. The rules it once kept for a member PR, a stacked pair
and a merge into an open PR's branch are gone: every PR lands through a batch.

`batch.py land` never passes `--delete-branch`: gh's flag also deletes the local branch, which is
checked out in a session's worktree here; `finish` deletes the member branches and the batch branch
on origin, and the repository deletes a merged head branch itself. The web button is equally safe
now that branches delete on merge. If main moves while a batch is open, `verify` refuses the batch
as behind until the batcher merges main into it, sweeps again and re-verifies (batcher step 7).

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
   does). Its merges, of a member and of origin/main, conflict where `git merge-tree` does, the
   merge `verify` checks each one against: they run `-s ort`, merge file contents with the
   histogram diff, and read none of the batch branch's `branch.<name>.mergeOptions`,
   `pull.twohead` or `diff.algorithm`, so an `-X` option, a strategy or a diff algorithm you set
   resolves no conflict there. To resolve a small conflict instead, `assemble <name> --resolve N`, resolve per hunk in
   the batch worktree, `git add` the files, then
   `assemble <name> --continue --reviewed '<who, verdict>'`. A resolution may change only the files
   that conflicted (plus entry files under `upstream/` when UPSTREAM.md was one of them):
   `--continue` refuses a staged change to any other path, naming the path and the `git restore`
   command that puts the merge's own content back; move such a change into a separate `batch:`
   commit after the merge instead. A member whose head is already in the batch (reachable through
   an earlier member's head) gets no merge commit of its own; it is recorded as contained, lands
   with the batch, and the body lists it as such under "Read these first" and in its table row.
3. Run the local sweep at the batch head: `scripts/sweep.py run --tree ../romp-batch-<name> --python
   <python>`, where `<python>` is a Python 3.12 interpreter, the version CI's served step runs.
   Nothing need be installed in it: the runner builds a venv for each leg that runs pytest and runs
   no test in `<python>` itself. When `<python>` is another version, pass
   `--served-python <a 3.12 interpreter>` as well; the sweep refuses to build the served leg's venv
   from any other version, naming what to pass. The machine also needs node, npm, bats, git and
   gitleaks on PATH (the legs' PATH is built from where yours finds each, and the result records
   their versions; the bats leg requires gitleaks, as CI's does); the Chromium build that the
   Playwright version pinned in the head's `vscode-extension/package-lock.json` (1.62.1 today)
   downloads, already in the Playwright cache your environment names (`PLAYWRIGHT_BROWSERS_PATH`,
   else on macOS `~/Library/Caches/ms-playwright`, and elsewhere `ms-playwright` under
   `$XDG_CACHE_HOME`, or under `~/.cache` when that is unset or empty), since the served
   leg requires it and the sweep installs no browser (`npx playwright install chromium` in
   `vscode-extension/`, after `npm ci`, puts it there); and Linux for full reaping, since only
   there is the sweep a child subreaper, so elsewhere a leg's orphaned descendants are not reaped
   (below). A full sweep takes about 2 hours: the full sweeps of 2026-09-30 took 2 h 11 min and
   2 h 8 min, with 2 pytest workers.
   The pytest leg runs in a venv holding what the batch head's `ci.yml` installs in CI's Python cells
   (pytest and its plugins, cryptography, and the Claude Agent SDK at the pin its SDK step reads),
   so the SDK-gated tests run as they do in CI. The runner builds the venv from `--python`
   (default: the interpreter running `sweep.py`) under `<state dir>/sweeps/sdk/`: the first sweep at
   a new pin or interpreter builds it (a download of about 110 MB), and later sweeps reuse it. An
   interpreter without `ensurepip` gets pip from PyPA's `get-pip.py`; `ROMP_GET_PIP_URL` names
   another file, and the URL is part of both venvs' keys, so a venv built from another file is never
   reused by a sweep without it. The file's sha256 is recorded with the venv. The
   legs outside the two venvs (bats, the node tests, the ledger check and the npm legs) have
   `--python`'s directory first on their PATH, so they run its `python3`: it should hold nothing
   installed, as the `python3` of CI's jobs other than the Python cells holds none of the test
   dependencies. A reused venv keeps the dependency versions pip resolved when it was built, while CI resolves them
   fresh on every run. A sweep reuses the venv only while its files match what its build wrote (new
   bytecode aside), so a file a test left in it is not carried into later sweeps: the next sweep
   builds it again, and a sweep that finds the venv changed after its pytest leg is invalid. A
   rebuild waits for any other sweep still using the venv. If the build fails, the sweep is refused
   with nothing recorded, and the message names the failed step and its log. A head whose `ci.yml`
   lacks one of those install steps is refused the same way; merge main into it. So is a `ci.yml`
   whose python job holds something else that could change what CI installs (an `env:`, `if:` or
   `working-directory:` on an install step, an `env:` or `defaults:` on the job or the workflow, or
   a step the runner does not read, named or not); change the runner with it. `--wrap LEG=PREFIX` runs a leg
   under this machine's slot or scope wrapper (the wrap keeps your environment; the leg does not
   see what it sets). The wrap must keep the leg in the sweep's process tree, as `systemd-run
   --scope` does and a `systemd-run` that starts a service does not; nothing checks this, and
   what a leg outside the tree leaves running is not reaped (below). The legs run in private clones of the batch
   head's exact sha under the state dir, one per CI job, each verified against the sha's tree before
   its first leg, never in the batch worktree: the worktree need not be clean, and its uncommitted
   edits are not swept (the runner prints how many there are). The legs run as CI's jobs run them:
   each mirrors one step of the head's `ci.yml`, found by its name, and the legs whose steps one job
   holds share one fresh checkout, in that job's step order, while each job's legs start from a
   checkout of their own, as CI's jobs do. `npm ci` runs only where that job runs it, so the legs
   of a job that installs nothing (bats, the manager tests and the tooling tests) run with no
   `node_modules`, as in CI. The runner reads the grouping from `ci.yml`, and the result records
   each group's job, legs and checkout. The pytest leg's job runs first: pytest runs over all of
   `tests/`, with no `node_modules` and with an empty browser directory, as CI's Python cells run
   it: the browser-backed tests skip there, as in CI, and the other tests in the served files run
   with the SDK. The legs are pytest, `npm ci` from the sha's lockfile, bats, the manager and
   tooling node tests, the ledger check (in a checkout of its own: CI runs it in a workflow of its
   own), `npm run typecheck`, `npm test`, the PDF renderer smoke test (`node --test
   tools/pdf-smoke.test.mjs`, after `npm ci` in the extension job's checkout, as CI's step runs it,
   so it opens a PDF with the installed `pdfjs-dist`; without `pdfjs-dist` the file's two tests of
   it skip and its fixture test passes, so the leg would pass, as CI's step would, and running
   after `npm ci` is what keeps it asserting), `npm run build` and
   the served leg: every leg at every
   head, whatever it changed, since the webview tests and the served tests
   also read files outside `kernel/kernel.py`, `ui/` and `vscode-extension/`. The served leg runs
   what CI's served step runs. The runner finds that step by its name, "Browser-backed served-page
   tests (pytest)", in whichever job of the head's `ci.yml` holds it. It runs the files the step's
   pytest line names (today the globs `tests/test_*_browser.py` and `tests/test_*_served.py`, and
   `tests/test_relay_dial_declares_held_pair.py` by file) with the step's own `env:` block, read
   from `ci.yml` (today `ROMP_SERVED_TESTS_REQUIRE`, under which a skip in the files the two globs
   select is a failure, while the module named by file turns only its own precondition skips into
   failures; `ROMP_SERVED_TESTS_ENGINES`; and `ROMP_CORNER_TWO_HOSTS`, which runs the two-host
   lab). It runs them in one pytest process, as CI does, in a venv of their
   own under `<state dir>/sweeps/served/`, built from the step's own pip line on the Python version
   the step's job sets up (3.12 today) and holding nothing else, so without the SDK, as CI runs them.
   That venv is reused, checked and rebuilt as the pytest leg's is. The served leg also runs the
   tests outside the served files that the pytest leg skipped for want of the extension's
   `node_modules` or a browser (1 test in 1 file when measured on 2026-09-28, the build guard in
   `tests/test_landing_bundles_built.py`). Neither of CI's jobs runs those tests, and the sweep
   ran them before its pytest leg moved ahead of `npm ci`, so the runner reads them from the pytest
   leg's own log, by the reasons their skips give, and runs them with the deps present. It reads
   the `SKIPPED` and `SUBSKIPPED` lines of that log's short summary (a subtest's skip, under
   pytest 9, names the test it belongs to, and the served leg runs that test whole; under pytest 8
   the same skip prints as a `SKIPPED` line of that test). The read is closed: a summary line of a
   kind pytest does not write, a skip line that does not name exactly one test, a line before
   any kind line, or a non-blank line after one that starts with `=` (or is shaped like pytest's
   closing line) and before the next kind line leaves the set unknown, and the served leg is then red
   naming the lines. These
   summaries pytest writes correctly end that way too, loudly and never with a skip dropped: a
   subtest message holding a newline, which splits its line; a parametrize id holding ` - `, read
   short at the first one (refused when that leaves a bracket open; an id holding `] - ` is read
   short and handed to the served leg's pytest, which exits 4 unless a test has exactly that id);
   a parametrize id whose own brackets do not balance, such as `a[`; a `SUBSKIPPED` line whose
   node id could start at more than one place, which `] tests/` or `) tests/` in its subtest's
   description or in its skip's reason can make it, or whose node id holds ` tests/`; a log that
   holds more than one short-summary header line (a skip reason or a failure message that quotes
   one), since which one opens pytest's own summary is then not known; a warnings summary pytest
   prints after the short summary (it does for a warning a `pytest_terminal_summary` hook emits),
   whose lines follow its `=` header; a reason or message running on to a line that starts with
   `=` (or is shaped like pytest's closing line), a quoted header or closing line of an inner
   pytest, say, when a non-blank line follows that line before the next kind line, as pytest's own
   closing line does when that reason or message is the short summary's last; and a reason or
   message running on to a line that starts with an upper-case word that is none of pytest's kinds and
   then `tests` before a slash, a space or the line's end (such as `ALL tests of this file ...`),
   which the reader takes for a line of a kind pytest does not write. Two summaries pytest writes
   correctly are read wrong with no refusal. The first: a reason or message running on to a line
   of a kind the reader reads is read as that kind. So a `SKIPPED` line there (a failure message or a skip
   reason quoting an inner pytest's output, say) adds its test to the set when the rule reads its
   reason, and the served leg's pytest then exits 4 unless a test has exactly that id, which it
   then runs again. And a skip reason that runs on to such a line is cut there, so its words
   after that line are not read: when only they would match the rule, the skip is dropped with no
   refusal (the pytest leg's record lists it among the other skips, so it can be seen). The
   second: a reason running on to a line that starts with `=` (or is shaped like pytest's closing
   line) ends there, and that line's own words are not read, so a skip whose words the rule would
   match only there is dropped the same way when the lines after it up to the next kind line are
   blank (a non-blank one leaves the set unknown). That
   covers the skips whose reasons
   the runner's rule reads, and three cases fall outside it: a skip for want of the deps in other words runs in no leg (the pytest leg's record lists
   every other skip outside the served files with its reason, so it can be seen); two real-tree pins in
   `tests/test_lab_dist.py` and `tests/test_kernel_bundle_staleness.py` do not skip without
   `node_modules` but read `esbuild.js` under a stand-in for the missing package, where they used
   to run after `npm ci` with the real one; and the tests the served leg adds run in its venv,
   without the SDK, so one that needed both the deps and the SDK would skip there. The runner
   refuses a served step it does not read in full: an expression in its `env:`, an `env:` on its
   job or the workflow, a line in its `run:` other than a pip install and the one pytest line, or a
   job whose setup-python step before it names no quoted `python-version:`. The served leg runs
   where CI's served step runs, after the steps its job runs before it. The pane bench
   (`tests/ui-bench.test.mjs`), the Browser legs step (its roster checks, and the rostered browser
   tests with `ROMP_BROWSER_LEGS_REQUIRE=1`; the sweep's `npm test` runs those tests without the
   switch, so a Chromium that fails to launch there skips instead of failing), the other Python
   versions and macOS run only in GitHub's CI: the Linux jobs in every run of `ci.yml` (a batch
   push or a manual run; the weekly schedule is paused), and the macOS cells only in a manual run
   (`workflow_dispatch`). CI's free-threaded cell runs pytest with
   `PYTHON_GIL=0`, which the sweep does not set, so a free-threaded `--python` runs with its own
   default. Each
   leg gets an allowlisted environment: a TMPDIR of its own, made when the leg starts and removed
   when it ends, with a private HOME and state dir under it, so nothing a leg leaves in any of the
   three reaches a later leg (the `npm ci` setup of a `--leg` re-run gets its own too); a PATH built
   from the tool directories, `--python`'s first; npm's global config and git's system config off; CI's switches; and
   nothing of your shell's (no key, token or session variable, no
   PYTEST_ADDOPTS or NODE_OPTIONS); `npm test` also gets this machine's 8 GB heap cap
   (`NODE_OPTIONS=--max-old-space-size=8192`), which CI does not set. npm's builtin config file
   (`npmrc` in npm's own package directory), which npm reads before any other and nothing turns
   off, is read by the sweep: one that sets anything but `prefix` refuses the run, naming the file,
   and the result records whether it exists and its sha256. An npm whose package the sweep cannot
   find above it (a shim, such as volta's) refuses the run, naming the npm, since its builtin file
   cannot be read: put an npm laid out as npm's installs lay it out first on PATH. The allowlist governs
   variables only: the legs run as your user, so a file stays readable at its absolute path (a
   credential file, an agent's socket), and a leg can read `/proc/<pid>/environ` of the runner and
   of your other processes, your shell and sessions included. Nothing a leg leaves in its checkout
   reaches a leg of another job: no file in the clone's `.git` (a hook, an attributes file, a
   replace ref) and no ignored file (bytecode, `node_modules`). Nor does a branch or tag a leg
   writes into your repository: each job's clone holds no branch and no tag of yours, and names
   no remote, so a `git fetch` in a later job copies nothing. CI's checkout differs here: it
   holds one local branch, the run's own, which `actions/checkout` creates at the commit it checks
   out (in every job a leg stands in for, the one commit it fetches, as that branch's
   remote-tracking ref; `ci.yml`'s secret-scan job, which no leg stands in for, fetches all of
   history), while the sweep's clone is detached at the sha, so a test that reads the current
   branch's name gets the run's branch in CI and none in the sweep.
   `tests/test_branch_name_readers.py` lists the tests that read it, and fails on each new or
   changed line, or run of up to three lines, that carries a spelling of such a read the census
   looks for, until that line is judged; among what it cannot see are a command that uses the
   current branch without naming it (a bare `git push`, say), `gh`'s own read of it, a name
   assembled at run time, another CI system's variables, a spelling split over more than three
   lines, a judged line moved to another place in its file, code that is not tracked, and a
   reader its execution check did not run (its docstring lists what it cannot see). Each clone
   holds one ref, `refs/remotes/origin/main`, at the commit your
   `origin/main` named as the sweep started, so a test that reads main finds it as it would in
   your clone; the sweep reads your `origin/main` once, before the first leg, and writes that
   commit into every clone, so a leg that moves the ref, in its clone or in your repository,
   moves no later job's. With no `origin/main` in your repository, no clone holds one. The result
   records the commit (`runner.checkout.main`, null without one). CI's job checkouts hold no
   `origin/main` except in a run on main itself: `actions/checkout@v4`, at its default depth 1
   in every job a leg stands in for, fetches the one commit as the remote-tracking ref of the
   branch the run is on (the batch branch's, in the run `land` reads), so a run on main (a
   dispatch on main, or the weekly schedule while it ran) holds it at the commit it checks out, and a batch
   branch's run holds none. A test that reads `origin/main` can therefore behave differently in the
   sweep than in CI; one that first checks whether its clone is shallow (fork PR 954's history
   case does) takes its shallow-clone handling in CI whether or not `origin/main` is there.
   `tests/test_origin_main_readers.py` lists the tests that read it, and fails on each new or
   changed line, or run of up to three lines, that carries a spelling of it the census looks
   for, until that line is judged; it cannot see a reader that spells the ref another way (a
   name assembled at run time, say), nor a judged line moved to another place in its file. The
   sweep reads `origin/main` by that exact name (`git show-ref --verify`), never as
   `git rev-parse` expands a name, so a
   branch or tag a typo made under a name that expansion tries (`git tag refs/remotes/origin/main`
   makes `refs/tags/refs/remotes/origin/main`) is never taken for it. When that read gives no
   commit, the sweep asks `git show-ref --exists`, which came in git 2.43, whether the ref is
   absent (no clone then holds one) or there, naming no commit it can read (the sweep is then
   refused). The sweep needs git 2.31 or later to start at all: an older git does not know
   `git rev-parse --path-format`, so the sweep is refused at its first look at your tree, saying
   the tree is not a git working tree that git recognizes (it names no version), and an older git
   ignores `GIT_CONFIG_COUNT`, which carries the sweep's neutral git settings. Git 2.31 does not
   honour `GIT_CONFIG_GLOBAL` either, so before git 2.32 your global git config is read. From git
   2.31 to 2.42, `git show-ref --exists` exits with a usage error, so a sweep whose `origin/main`
   is absent, names no commit or cannot be read is refused, naming git 2.43, and one whose
   `origin/main` names a commit runs. An
   `origin/main` kept as a loose ref file that is not a regular file refuses the sweep before its
   first `git` call that would read it, naming the file and its type, whatever `git` would make
   of it: `git`
   waits on a FIFO; follows a symlink, so it reads one to `/dev/zero` without end, takes the
   commit in one to a regular file and reads a dangling one as absent, except that a symlink
   whose target text is a ref name (`refs/heads/x`) it does not follow at all but reads as a
   symbolic ref to that ref, taking that ref's commit; reads a device's contents
   (`/dev/zero` without end, `/dev/null` as a ref it cannot parse); reads a
   directory as absent (`git show-ref --exists` before git 2.43.2 fails it as unreadable), or,
   with `origin/main` packed, as the packed commit; and reads a socket as a ref it cannot read.
   So does a loose ref file larger than a ref file holds (4 KiB; a sparse file of any size
   included), named with its size, or one holding a symbolic ref, named with its target, since
   `git` reads a loose ref file whole and follows a symbolic ref unchecked. So does your
   repository's `packed-refs` when it is not a regular file (a FIFO, a symlink), named with its
   type, since `git` reads it for any ref with no loose file, `origin/main` and your `HEAD`'s
   branch among them. A symlink there is refused whatever it leads to, a regular file holding
   your packed refs included, which `git` would read through, as a symlinked loose ref file is:
   replace it with the file it leads to (earlier sweeps read through such a symlink).
   `scripts/sweep.py check` refuses such a `packed-refs` the same way, before it reads your
   `HEAD`. These checks see the
   file as it is when the sweep checks it. One swapped in after them, by a process still running
   then, is opened by name by the `git` that reads the ref next: it waits on a FIFO until the
   time bound below, and reads a symlink to `/dev/zero`, or a sparse file too large for the
   memory limit below, until that limit ends the read (on Linux; elsewhere, until the time
   bound or the machine's memory does), and the sweep is refused naming the call and the limit,
   every file of your repository that read opens or looks for as one it may have met (the ref's
   file, or `packed-refs` when it has none, your `HEAD`, `config`, shallow file and
   `objects/info/alternates` among them), and those of them that are not regular files then;
   a symbolic ref swapped in is followed, and the commit of a readable ref it names is taken.
   Any such file a leg leaves there marks nothing in its own run, which read the ref before the
   first leg, and refuses the next sweep. A move of your `origin/main`
   during a sweep marks no run invalid, unlike a change to your shallow file (below), since a
   fetch of origin during the sweep moves it as a leg can and the sweep cannot tell the two
   apart: the next sweep's clones hold the ref as it then stands, and its result records that
   commit. When your repository is shallow as the sweep
   starts, each clone is shallow the same way: the sweep reads your shallow file before the first
   leg and gives every clone that copy, so a leg that writes the file changes no later job's clone.
   After the last leg the sweep reads the file again, and when it differs from that copy (a leg
   wrote or removed it,
   or anything else did during the run) the run is invalid, naming the file: the sweep does not
   restore it, so the next sweep's clones read it as it now stands: cut where the file now says,
   or, when a leg removed it, not shallow at all. A shallow file that is not a regular file (a
   FIFO, a device, or a symlink, which the sweep does not follow) is never opened by the sweep, and
   no `git` it starts reads one its check found: one there as the sweep starts refuses the run
   before the sweep's first `git` call that would read it, and one a leg leaves makes the run
   invalid, each naming the file; `scripts/sweep.py check` refuses one the same way, before its
   first `git` call that would read it. The sweep reads at most 16 MiB of the file (it holds an
   object id per commit at a shallow boundary, so that is over 250,000 of them): a larger one, a
   sparse file of any size included, refuses the run before the first leg, and after the last leg
   makes the run invalid, each naming its size. Every other file the sweep reads itself has a
   limit too (but for `/proc/<pid>/stat`, whose size the kernel bounds, and `get-pip.py`, which
   the sweep fetches itself into a directory no leg has seen), and is read only up to it, so a
   sparse file of any size is never read to its end: a
   result or a venv's marker 16 MiB; a checkout's marker 4 KiB; the `pytest` leg's log, read whole
   for the tests it skipped, 128 MiB; `ci.yml` and a file an install step's `sed` line reads 16 MiB;
   npm's `package.json` and builtin `npmrc` 1 MiB; a clone's `.git/HEAD`, `.git/config` and
   `.git/info/exclude` 64 KiB; and, read in pieces of 1 MiB, so that only the time the read takes
   grows with the size, the `bats` leg's log, whose lines are counted, and each file of a venv, or
   ignored file of a checkout, that the sweep hashes, 1 GiB. That limit is per file, and the time
   hashing takes across files has none: a leg can leave as many files just under it as it likes
   where the sweep hashes them (sparse ones cost it nothing on disk), and each costs the sweep the
   time to hash one of that size, about 0.7 s for 1 GiB (measured on 2026-10-03 at a load of 27 on
   a 60-core machine), so a thousand of them hold each pass over them about 12 minutes. The sweep
   also holds an entry for each file it walks, in a checkout (and in `git check-ignore`'s input,
   built from those entries) and in a venv, with no limit on their number, so many small files a
   leg leaves cost it memory as well as time, until `git check-ignore`'s output passes the 64 MiB
   limit below, which ends that call. Such a leg's files are there to see, and the run can be
   stopped. `scripts/batch.py` reads at most
   1 MiB of its batch state. Past its limit a file reads as one the sweep cannot read: a result is
   unreadable and kept until you move it aside, a venv is built again (or, read after a leg, makes
   the run invalid), the rebuild's line naming a venv marker's size, an ignored file a leg left
   counts as changed, the served leg is red naming the `pytest` log's size, a `bats` leg that
   exited 0 counts no test and is red, its line naming the log's size, the run is refused naming
   `ci.yml`, a `sed` line's file, npm's builtin file or npm's `package.json`, and `batch.py` stops
   naming its state file. Each limit's measurement, or the format that sets it where there was
   nothing to measure, is given at its constant in `scripts/sweep.py` (`STATE_MAX` in
   `scripts/batch.py`). The legs of one job share its
   checkout, as CI's steps do. The machine itself stays shared, and a leg can leave a file there
   that a later leg reads: `/tmp` outside each TMPDIR, `/dev/shm`, `/run/user/<uid>`, the npm and
   Playwright caches, your passwd home, tmux's socket directory (tmux ignores TMPDIR), `--python`'s
   directory and your repository's object store, which every clone reads. A leg that changes the
   checkout (a tracked file; a file no rule of a
   tracked `.gitignore` covers, whatever the clone's own git state says; after `npm ci`, any
   ignored file outside `vscode-extension/node_modules` that `npm ci` added or changed) makes the
   run invalid, and so does a job's fresh checkout that is not the sha's tree, or a shallow file
   changed during the run (above). So does a clone's `.git` that a leg leaves as anything but a
   directory, or its `.git/HEAD`, `.git/config` or `.git/info/exclude` left as anything but a
   regular file (a FIFO, a device, a symlink): the sweep checks `.git` and then those three first,
   names each one it finds, and neither it nor a `git` it starts opens one it found, since reading
   one could wait or read without end, and `git` follows a `.git` file to the directory it names.
   These checks see each file as it is when the sweep checks it: a file swapped in after the check
   (by a process still running then, such as one of the four kinds below) is still never read by the
   sweep itself, which reads only a regular file and opens without waiting, but a `git` it starts
   next opens the file by name and can wait on it, until the bound below ends the wait. Every `git`
   call the sweep makes into a repository names it explicitly (`GIT_DIR`, `GIT_COMMON_DIR` and
   `GIT_WORK_TREE` set, `GIT_CEILING_DIRECTORIES` at the directory above it), but for the one call
   that finds your repository, which sets the ceiling alone, at the parent of the directory holding
   `.git`, and refuses a directory whose work tree, as `git` reads it there, is another (a
   `core.worktree` in its config); so a clone's `.git` that `git` no longer recognizes (its `refs/`
   removed, say) fails the call instead of sending `git` up to a repository that encloses the clone.
   Every `git` call either script makes runs with `core.warnAmbiguousRefs` off. With it off, a
   call that resolves a full object id as an object (`rev-parse`, `cat-file`, `merge-base`,
   `ls-tree`, `log`, `show`, `diff` and `update-ref`'s value among them) reads no ref, and one
   that resolves a name opens the names its rules try up to the first that finds a ref, and none
   of the later names `git` would try only to warn that one is ambiguous: a symlink to `/dev/zero` a leg leaves at `refs/tags/<sha>`, say, is never read by
   those calls, where before `scripts/sweep.py check` met the memory limit there and
   `scripts/batch.py verify`'s own `git` read it without end. Some calls look an object id up as a
   ref name under every rule, whatever the setting: `git checkout <sha>` (with `--detach` or
   `-B`), `git bisect start`, `git bisect`'s good, bad and skip steps, which look up the ids
   of the commits the bisect has marked, and `git merge <sha>` when `merge.log` is set (in a
   repository's config or yours, or `--log` in a branch's `mergeOptions`), to describe the
   commit in the shortlog it appends, try
   `<git dir>/<sha>`, `refs/<sha>`, `refs/tags/<sha>`, `refs/heads/<sha>`, `refs/remotes/<sha>`
   and `refs/remotes/<sha>/HEAD`, and read a symlink to `/dev/zero` at any of them.
   `git bisect start`, run from `HEAD` detached, looks `HEAD` up the same way, and each step looks
   `BISECT_HEAD` up the same way (`refs/tags/HEAD`, `refs/tags/BISECT_HEAD` and the rest).
   `scripts/batch.py assemble` passes `--no-log` to its merges, of a member and of `origin/main`,
   so they make none (the shortlog `merge.log` would add to the merge commit's message is
   dropped; the tool reads only a merge's subject). Two callers still make them. The sweep's
   checkout of each job's clone runs in the fresh clone only, which holds
   no ref the sweep did not write, under the sweep's memory limit. `scripts/batch.py bisect`'s
   checkout of the base and of each commit it tests, its `git bisect start` and its good, bad
   and skip steps run after your
   command has run in the batch worktree, whose refs are your clone's, under `scripts/batch.py`'s
   memory limit (1 GiB), so such a read stops `bisect` there with an error naming the call. Its
   cleanups make none of them, but for the `git bisect reset` after a stop that ended
   `git bisect start` after it wrote `BISECT_START` and before `BISECT_HEAD`, which checks the
   tip out by its id; a symlink to `/dev/zero` there then fails that cleanup (a symlink already
   there when `git bisect start` runs stops it before it writes `BISECT_START`).
   The directory `--tree` names must itself hold `.git`: one that does not exist, or whose `.git` is
   gone, is refused, naming it, and never read as a repository that encloses it, and an empty
   `--tree` (an unset shell variable gives one) is refused rather than read as the current
   directory; only with no `--tree` does the sweep look up from the current directory for the
   nearest directory holding `.git`, and `check`'s remedy then names that directory. Each call has 120 s to end (`GIT_BOUND` in `scripts/sweep.py`; a job's checkout, the
   slowest call, took under a second when measured on 2026-10-01). A `git` still running then, waiting on a FIFO a leg left
   where `git` reads (a `.gitignore`, a file an `include.path` names, your repository's
   `objects/info/alternates`) or on one swapped in after the sweep's check, is killed, and the run
   is invalid, naming the call, or,
   where that happens before anything is recorded or in `check`, refused, naming it. On Linux each
   call also has a memory limit, its address space capped at 1 GiB (`GIT_MEMORY`; a job's checkout,
   the call that needs the most, needed 252 MiB when measured on 2026-10-03), so a `git` that reads
   without end (a symlink to `/dev/zero`, or a sparse file, where it reads a ref) fails at the
   limit within a second, and the call is named the same way, with the limit; a read of the
   branch your `HEAD` names that meets either limit is refused naming that ref's file, and a read
   of your `origin/main` naming every file of your repository that read opens or looks for as one
   it may have met, with those that are not regular files then. Off Linux no `git` has the memory limit, since macOS does not enforce it, and
   each result records which (`runner.git_memory`). On every platform the sweep holds at most
   64 MiB of what a `git` call prints on each of its output streams (`GIT_OUTPUT_MAX`; the most a
   real call printed was 0.5 MB, `git check-ignore` over the files `npm ci` and the builds leave,
   when measured on 2026-10-03), so a `git` that prints more (asked about files without end a
   leg left, or listing a tree object a leg rewrote) is ended, and the call named the same way,
   with the limit. The output of the other processes the sweep starts and reads (a probe of an
   interpreter, a tool's version) has a time limit and no size limit. A `git` the
   sweep kills, at the bound or on a stop, gets SIGTERM with its process group first, so it removes
   its own lock files (the `git status` in your tree holds your `index.lock` while it reads
   `info/exclude`), and SIGKILL 10 s later if anything of the group is left. A FIFO a leg
   leaves in your repository where no `git` of that run reads after it (its `config` or `HEAD`,
   since the sweep's `git` calls in your repository all come before the first leg; its `index` or
   `info/exclude`, which only `git status` there reads; or its `objects/info/alternates` once the
   run's last checkout is made and verified, since the reads after the legs read no object) leaves
   that run's verdict as recorded, and the next run is refused at its first `git` call that reads
   the file, naming the call. `check` is refused the same way for `config`, `HEAD` and
   `objects/info/alternates`. For `index` and `info/exclude`, of the sweep's two commands only the
   next run is refused: `check` reads neither file and reports the verdict the run recorded. `scripts/batch.py` names the
   repository and bounds its own `git` calls the same way (its discovery call, with the ceiling
   alone, runs again before each call in a batch worktree, and its clone, `ROMP_BATCH_REPO` or the
   directory above its `scripts/`, and each batch worktree must hold `.git` themselves, as
   `--tree` must, and be the work tree `git` reads there, a `core.worktree` naming another
   refused), at 600 s, since it also pushes through the pre-push hook and fetches, and stops with
   an error naming the call. Its `git` calls also have the sweep's memory limit, 1 GiB of address
   space (16 GiB for a `git push`, a `git commit` or a `git merge`, which run your clone's hooks:
   this project's pre-push hook starts `gitleaks`, which reserves more than 4 GiB as it starts, and
   a pre-commit hook you set for every clone can start it too; `git merge --abort` runs none of
   the merge hooks, only `post-index-change` and `reference-transaction` (measured with git
   2.43.0), so it runs under 1 GiB with no listing first; the tool never passes
   `--no-verify`, and a merge that your `pre-merge-commit`, `prepare-commit-msg` or `commit-msg`
   hook refuses is aborted and stops the command, quoting what `git` printed, the hook's words
   included; that limit covers the whole call, so a push's own reads of your refs run under
   it too, and before each such call the tool lists your refs under the 1 GiB limit with
   `git for-each-ref`, which reads every loose ref and `packed-refs` as a push does, so a sparse
   or oversized file at a loose ref stops it there, at 1 GiB, with or without a fetch first; a
   file placed after that listing, or one the call reads and the listing does not, such as
   `objects/info/alternates` or `shallow` at a push, or a state file in the git dir such as
   `MERGE_MSG` or `COMMIT_EDITMSG` at a merge or a commit, still meets 16 GiB), and its limit on what
   one call prints, 64 MiB a stream, read from
   `scripts/sweep.py`; a call that meets either stops the command with an error naming the call
   and the limit, and the memory limit's names the files of your repository that `git` reads whole
   and that are, when the error is made, not regular files or larger than a file of their kind
   holds: a loose ref under `refs/` (or a linked worktree's own `refs/`) over 4096 bytes, and
   `packed-refs`, `objects/info/alternates` or `shallow` at least the size of the limit, each with
   its type or size; for the call that lists the remote batch branches (`git for-each-ref` of
   `refs/remotes/origin/batch/`), the error also names that directory, as the one whose loose refs
   the call reads; the state files in the git dir that a commit, a merge or a bisect reads whole
   (`COMMIT_EDITMSG`, `MERGE_MSG`, `MERGE_MODE`, `SQUASH_MSG`, `MERGE_AUTOSTASH` and `BISECT_START`)
   are named the same way, when one is not a regular file or holds at least the limit; and the
   memory limit's error lists the places `git` reads a file whole, those state files among them.
   Some failures at the memory limit are reported as plain failures instead, the
   error naming the call and quoting what `git` printed, not the limit, and `git fetch` meets two
   of them. When its check that it received every object fails at the limit after `index-pack`
   has passed it, `git fetch` exits 1, printing an out-of-memory line or a `packfile ... cannot be
   mapped` line first and `did not send all necessary objects` after it. When `git` cannot start
   a thread at the limit, it prints `Resource temporarily unavailable` (a `git fetch` at a limit
   far below 1 GiB exited 128 with `error: cannot create async thread: Resource temporarily
   unavailable`), the words `git` also prints when a limit on processes stops it. The comment
   above `OUT_OF_MEMORY` in `scripts/sweep.py` lists the others that are known. The tool names
   `origin/main` and the batch branches by their full refs wherever it needs only
   their commit, and so do `finish`'s check that the local batch branch is still there and
   `bisect`'s cleanups, which put the branch's tree back with `git read-tree` and point `HEAD` at
   the branch with `git symbolic-ref` (`git checkout` stays on a branch only when given its short
   name), and end the bisect with a plain `git bisect reset`, which checks nothing out, since
   `bisect` runs `git bisect` with `--no-checkout` from `HEAD` detached at the tip and checks out
   each commit it tests itself (`git symbolic-ref` does not apply `git checkout`'s rule that a
   branch is checked out in one worktree at a time, so `bisect` applies it: it refuses to start
   when another worktree holds the batch branch, on it or bisecting or rebasing from it, and its
   cleanups check again before they point `HEAD` at the branch, leaving the worktree detached and
   naming the other one when it does), so while such a ref exists `git` opens no other name its rules try for it
   (`refs/tags/origin/main`, or `<common dir>/batch/<name>` beside the batch state, the common
   dir being your clone's `.git`). Three kinds
   of read still reach such names. A full ref that is absent sends `git` on through the names its
   rules make of the full name (`refs/tags/refs/heads/batch/<name>` and the rest): `plan`'s and
   `verify`'s reads of a base branch `origin` has deleted, and `verify`'s check that the batch
   branch exists before an assembly, are such reads (`finish`'s check reads the local branch
   with `git show-ref --verify`, which reads only that ref, so it is not one, even once the
   branch is gone). `assemble` names the batch branch by its short name when it makes it
   (`git worktree add -B batch/<name>`) and when it resets it in a worktree it reuses
   (`git checkout -B batch/<name> refs/remotes/origin/main`): `git` looks that name up by its
   rules once it has set the branch, and opens `<common dir>/batch/<name>`,
   `<common dir>/refs/batch/<name>` and `<common dir>/refs/tags/batch/<name>` before it finds
   `refs/heads/batch/<name>`, from the batch worktree too, and `git checkout -B` first looks its
   start point up as a local branch, `<common dir>/refs/heads/refs/remotes/origin/main` (the witness:
   `test_assembles_branch_reset_reads_the_branchs_short_name_and_stops_at_the_memory_limit` in
   `tests/test_batch_tool.py`). And the listing of the remote batch branches (`plan` without
   `--name`, and `assemble`'s check for another batch on `origin`) shortens each
   `refs/remotes/origin/batch/<x>` it finds to `origin/batch/<x>` and, to tell whether that name
   is ambiguous, opens `<common dir>/origin/batch/<x>`, `refs/origin/batch/<x>`,
   `refs/tags/origin/batch/<x>` and `refs/heads/origin/batch/<x>` (the witness:
   `test_the_listing_of_the_remote_batch_branches_opens_the_names_of_each_ones_short_name`, in the
   same file). Each of these calls runs under
   the memory limit, and one that meets it stops the command, naming the call; for the two
   `-B` calls the error names each of the files they open that is not a regular file or is
   oversized, `<common dir>/batch/<name>` included, and for the listing those under `refs/`, but
   not `<common dir>/origin/batch/<x>`, which is outside `refs/`. It runs its `git` calls without automatic gc
   or maintenance, which would run under the same
   limit with a need nobody measured; your own `git` calls in the clone still start them. Its
   `verify` and `plan` run `git` in your clone's own work tree, so the `index` they can meet is that
   work tree's, not a batch worktree's: a FIFO there stops `plan` at its `git fetch`, and `verify`
   at its `git fetch` or, with `--no-fetch`, at the `git diff-tree` of its check of a merge. A FIFO
   at `info/exclude` stops `verify`, fetching or not, at the `git worktree add` of its ledger check;
   `plan` does not read that file. It runs
   `scripts/pr-orphans.sh` and the ledger script, which run `git` in your clone, each with the
   repository of the tree it runs in named in its environment (your clone for `pr-orphans.sh`; the
   batch worktree, or the ledger check's temporary worktree, for the ledger script) and the same
   bound and limits, which stop the command only when the script itself fails at them (`finish`
   reports a `pr-orphans.sh` stopped at either limit, or at the bound, as unread and carries on,
   the merge having happened). Each `git` the scripts start also gets the tool's `git` settings,
   through its environment (`GIT_CONFIG_COUNT` and its pairs, after any pairs you set there): the
   pack window caps, one thread for the index, for `index-pack` and for `pack-objects`, and no
   automatic gc or maintenance. `pr-orphans.sh` runs `git remote get-url origin` and, when the
   clone has an origin, `git fetch --prune origin` (neither when `ROMP_ORPHANS_NO_FETCH` is set),
   then `git rev-parse --verify` of the main branch and `git merge-base --is-ancestor` for each
   merged pull request it reads, and the ledger script's import runs `git log -S` over the history
   of `UPSTREAM.md` to date a row (its check runs no `git`), so each needs what the tool's own
   calls need, and the fetch starts no gc under the
   limit, where one that failed in the background would write the `gc.log` that stops your
   clone's automatic gc while `pr-orphans.sh` still reports clean. A `-c` the script passes, or a
   `GIT_CONFIG_PARAMETERS` the tool runs under (a `git -c` that started it), overrides them. A
   `git` that one of the scripts starts and that fails at the memory
   limit is read by that script as any other failure: `pr-orphans.sh` reads it as a merged pull
   request whose content is not on main (or, with no merge commit recorded, as one it cannot
   place), and the ledger script's import as a row no commit introduced, dated today. `gh`'s output, which the tool holds whole, and the `git` that `gh` starts, have
   none of these limits. SIGTERM stops it, and so do SIGHUP and Ctrl-C (SIGINT) unless it was
   started with them ignored (under `nohup`, or as a shell's background job), which it keeps: any
   process it is waiting on is ended with its process group (a `git`, one of those two scripts,
   `gh`, or the command `bisect` runs, each started in a session of its own, so what it started goes
   too; neither `gh` nor that command has a controlling terminal, so a prompt through `/dev/tty`
   fails, while the descriptors they inherit work as before), its cleanup runs, and it exits 128 plus
   the signal's number. When a cleanup of `bisect`'s does not finish (its unforced restore refused by
   `git read-tree`, say), `bisect` says first what stopped it (that the command fails at the base too,
   the commit and the command's exit, the step that failed, or the signal), then the cleanup's
   error, the state the batch worktree is left in and the commands that put it back on the branch,
   and a stop still exits 128 plus the signal's number. Each step of that cleanup (in `bisect`, the
   restore of the batch branch's tree, the `git bisect reset` and the move of `HEAD` back to the
   branch; in `verify`, the removal of the ledger check's temporary worktree)
   runs to its end: a
   SIGTERM, SIGHUP or Ctrl-C that lands inside one runs it again from its start, with later ones
   ignored. The cleanup also runs for a stop during a step it undoes: one while `bisect` checks
   out the base or a commit it tests, or while its `git bisect start` runs, leaves the worktree on
   the batch branch with no bisect in progress. When the worktree had no changes to tracked files before those steps, the
   cleanup's restore of the branch's tree is forced (and in `bisect`'s cleanup after its steps it
   runs before the `git bisect reset`), so the branch's tree is back even when the stop ended a
   checkout after it had written the other commit's files and index and before it moved HEAD; a
   worktree that had changes to tracked files gets the unforced restore, the two-way merge
   `git checkout` makes, which keeps them. The batch
   worktree is `scripts/batch.py`'s own, and that cleanup runs whenever `bisect` ends, stopped or
   not: when the worktree had no changes to tracked files before those steps, the forced restore
   discards every change the test command made to tracked files there, at the base and at each
   commit the bisect tested. A change the command made in its first run, at the tip, is a change
   the worktree had before those steps, so the restore is not forced, and that change and the
   changes the command made after it are kept.
   A stop that arrives
   while it starts any of those processes, or the `git` of the sweep's excuse rule that `verify`,
   `plan` and `assemble --repin` run, is held until the process has started and then ends it the
   same way. Each of those processes gets SIGTERM first here too, then SIGKILL 10 s later, so a
   `git worktree add` stopped or killed at the bound removes the worktree it was adding and its
   registration rather than leaving them locked, and the next `assemble` is not refused on a lock it
   left. The files the
   sweep and `scripts/batch.py` keep for themselves, which a leg can reach (the state dir from its
   log's path, your clone's common dir through its checkout's alternates), are created or opened
   without waiting, and eight reads of them fail closed. (1) Each leg's log is created afresh,
   without following a symlink, under another name when anything is at its name, and its summary
   and counts are read through the file the sweep created, so nothing a leg puts at the log's path
   is written to or read for them. (2) The sweep reads the `pytest` leg's log again by its name,
   once its own file is closed, for the tests that leg skipped for want of the deps, which the
   `served` leg also runs: a log the leg replaced with anything but a regular file (a FIFO, a
   symlink) is not read, and the `served` leg is red, naming why, while one it replaced with another
   regular file is read as if the leg had written it. (3) A result that is not a regular file (a
   FIFO, a directory, or a symlink, a dangling one included) is never read and reads as unreadable:
   `check` and `verify` fail it, naming the file, and the next sweep at its sha is refused, keeping
   the file, so their line says to move it aside to sweep that sha again. (4) A
   checkout's marker that is not a regular file reads as no marker, and the checkout is removed as
   stale. (5) A venv's marker that is not a regular file
   reads as no finished build, the rebuild's line naming what is there, and the venv is built
   again. (6) A venv's build log that is not a
   regular file refuses that build, and so the sweep, naming the log. (7) The run's lock and a
   venv's lock are opened without waiting, without following a symlink and only as a regular file,
   so a FIFO, a symlink or a directory at either refuses the sweep, naming the lock. (8)
   `scripts/batch.py` reads its state file only as a regular file, without waiting, and otherwise
   stops, naming it. A leg can also leave
   a process running. The sweep reaps its own process tree: when a leg ends, it kills its children
   again and again until none is left or 30 s pass, and on Linux, where the sweep is a child
   subreaper and so adopts each orphaned descendant of a leg (a `setsid` child, a double-forked
   grandchild), that is everything the leg left running in the tree. Four kinds of process escape
   that reap, so each can still be running after its leg ends and write into a checkout, its own
   job's or a later job's, or anywhere else your user can write: a process started at a leg's
   request by one already running outside the sweep's tree, which the sweep neither waits for nor
   reaps (a unit of your user service manager, which a leg reaches by setting `XDG_RUNTIME_DIR` to
   `/run/user/<uid>`; a window of a tmux server already running; an `at` or `cron` job; a service
   D-Bus activates); a leg run under a `--wrap` that hands it to a service manager, since the sweep
   waits for the wrap's own process and the leg runs outside its tree; every orphaned descendant of
   a leg, and so everything the leg leaves running, where the sweep is not a child subreaper, which
   is the case off Linux (on Linux a `prctl` that fails refuses the run, and each run records which
   case it was, as `runner.subreaper`); and a descendant still alive when the reap's 30 s timeout
   runs out, which runs on into the next leg until the next reap. A write by one of these makes the
   run invalid only when the re-read after a leg, or the check of a later job's fresh checkout,
   reads the path it wrote, and the run then names the leg after which, or the checkout in which,
   the change was found, which need not be the leg that started the process; or when it changes
   your shallow file before the re-read after the last leg, and the run then names the file; or
   when a `git` call of the run waits on what it wrote until the bound, and the run then names the
   call. The sweep writes every
   run to
   `<state dir>/sweeps/<full sha>.json`, which keeps every run at that sha. The state dir is
   `$ROMP_STATE_DIR`, else `$XDG_STATE_HOME/romp`, else `~/.local/state/romp`, so run `sweep.py` and
   `batch.py` with the same environment. When one leg fails on a known flake,
   `scripts/sweep.py run --tree ../romp-batch-<name> --python <python> --leg <leg> --flake '<the flake>'` re-runs that
   leg alone at the same head; `--flake` names the failing test and where it is recorded as a known
   flake. A full run at a head whose last run failed a leg also needs it, as
   `--flake <leg>=<the flake>` for each failed leg: a later green counts over a red run only then. A
   flake is excused once per leg: a leg that fails again, or that a later run passes without
   `--flake`, leaves that head unable to pass, and the fix goes on a new head. An invalid run's
   failures count too: a leg that failed in a run that went invalid, the leg that made it invalid
   included, needs `--flake` like any other failure, and a second failure inside an invalid run
   leaves the head unable to pass (the runner exits 1 for such a run, not 3). A pass inside an
   invalid run counts for nothing, since the checkout or a venv changed under it, or your shallow
   file changed during it, and an invalid run
   that failed no leg needs no flake. A re-run of a leg (`--leg`) is refused while the newest full
   run is invalid, so the flake for a failure in an invalid run is spent on a full run. SIGTERM
   stops the runner, and so do SIGHUP and Ctrl-C (SIGINT) unless it was started with them ignored
   (under `nohup`, or as a shell's background job), which it keeps; a stopped run removes its
   checkouts and TMPDIRs, and the legs start with both signals at their default action either way.
   `check` stops on the same signals and kills the `git` it is waiting on with its process group,
   exiting 128 plus the signal's number. A stop that arrives while the sweep starts a process (a
   `git`, a leg, a probe of an interpreter, a step of a venv's build, a read of a tool's version)
   is held until the process has started and then ends it. A leg that
   fails is written to the result as soon as it exits, so stopping the runner during the re-read
   after it, or during that write itself, keeps the failure (a stop inside the write lets it finish
   first, as it does for the write of an invalid mark); a stop between the leg's exit and the
   write of its failure (the reap of what the leg left running, up to the reap's 30 s timeout,
   the reading of the leg's log for its summary and test count, which holds a bounded part of the
   log whatever its size, and the steps from the filled-in record to the write) loses that
   failure, and the next run needs no flake for it. An `npm ci` that a job runs before
   its legs where the `deps` leg is not among them (the served job's, or one a re-run runs first)
   and that fails marks each of that job's legs after it red, naming it, and writes them as soon as
   it exits, before the check of the checkout after it, so a stop during that check keeps them as
   failures (a stop after it exits and before its blocked legs are written loses them, as for a
   leg); one that also changed the checkout makes the run invalid, with those legs counted as
   its failures. In a re-run's first job, where nothing is recorded yet, such a failure refuses the
   re-run instead. A run that did not finish (stopped, or its runner died) is read as an invalid
   run is: its failures count and its passes count for nothing, since a later leg's re-read could
   have made the run invalid had it not been stopped. The runner refuses a run that cannot count,
   and refuses a re-run of a leg that did not fail. A re-run runs
   each leg it names in a fresh checkout of that leg's job, with `npm ci` first where that job runs
   it, so one re-run may name legs of several jobs; a re-run of pytest, or of a leg whose job runs
   no `npm ci`, has none, and `deps` named with a later leg of its job runs as a leg. `verify` reads the whole
   history, and the body's first block names each excused failure and its flake, and each invalid
   run with the legs it failed. `scripts/sweep.py check --tree ../romp-batch-<name>` prints
   what `verify` will read.
4. `scripts/batch.py verify <name>`. It reads the sweep result for the batch head's full sha and
   fails by name when it is missing, stale (recorded at another commit), unfinished, red (a red run
   no later run excused counts too), invalid (a result recorded under another sweep.py's leg
   environment is), incomplete or unreadable (a schema-1 result, from the runner that swept the
   batcher's own tree, is, and so is a result with a run that records no private checkout). For a
   result file the next sweep at that sha keeps and refuses (one it cannot read, one of another
   schema, or one that records another sha), the line says to move the file aside and sweep again,
   the remedy that refusal names. A missing result names the directory verify read and the variable it
   came from (`ROMP_STATE_DIR`, `XDG_STATE_HOME` or `HOME`): a sweep run with another environment
   wrote its result somewhere else. It also fails as "behind" when the batch head does not contain
   main as origin has it now: `ci.yml` does not run on the merge to main, so a batch should land only when
   the tree that lands is the tree the sweep and the batch's CI ran on; run step 7, then steps 3 and
   4 again. If an earlier `assemble` died part-way, `verify` fails with "assembly incomplete"; run
   `assemble` again first.
5. `git push -u origin batch/<name>` (after a rebuild, `git push --force-with-lease origin
   batch/<name>`; `pull` pushes that way itself). If the pre-push hook refuses the push: it scans
   each pushed commit's tree, so a batch tip that inherits a pre-scrub string trips it although the
   new commits are merges; read what tripped and fix the member or ask. Never bypass the hook. Then
   `scripts/batch.py summarize <name>` and watch the one `ci.yml` run: the push to `batch/<name>` starts
   it. The batch PR is expected to show its checks on its head, and a newer push to the branch to
   cancel the older run; the first batch confirms both ("Checked on the first batch", below). The
   batch PR carries the `batch` label and no tier; the fork's copy of the `PR tier` check counts
   `batch` as its one label, so that check is green when the PR opens. It does not run on a push,
   so after a rebuild the new head shows no `PR tier` check until a label changes; nothing gates on
   it, and nothing should (the maintainer section says which checks to require). If CI is red:
   `scripts/batch.py bisect <name> -- <failing test>` names the member (it runs the test in the
   batch worktree and, when it ends, puts the worktree back on the branch there; when the worktree
   had no changes to tracked files after the test's first run, at the tip, doing so discards the
   changes the test's later runs made to tracked files; the paragraph on stopping
   `scripts/batch.py`, above, gives the rule; when it had changes and that move is refused, a
   change to a file the commit it last tested and the tip hold differently, it prints the first
   bad member, fails, and leaves the worktree detached at that commit with the bisect in progress,
   naming the commands that put it back);
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
   included), when its success is not over `ci.yml`'s own jobs (every job of the head's `ci.yml`
   needs a job run in the run's latest attempt that passed, told by the name GitHub gives it, so a
   success over the tier-label checks alone, over no job run, or with a job skipped is refused as
   incomplete), or when the read fails or answers with anything but a list of run records (an error
   object, null, nothing); a run of another commit, a manual run and a run on another
   branch do not count. The newest run is the latest `createdAt`, then the highest run id, and a
   matching row with either one, or its attempt number, missing or malformed (the zero time gh
   prints for a missing time included) is refused by name. A red is not erased by a re-run on
   GitHub or by pushing the same sha again either: land reads the newest run's earlier attempts and
   every attempt of an older push run at the same head, and one that did not pass (cancelled
   included) is refused unless `land <name> --flake <run>/<attempt>='<the failing test, and where it
   is recorded as a known flake>'` names it, as the refusal spells out. One attempt across the runs
   at the head is excused; land records it, and `finish` reports it. It reads main on origin again before it retargets a stacked member to
   main, so a move already made refuses with nothing on GitHub changed, and once more right before
   the merge call; a refusal there after a retarget names each retargeted member and the
   `gh pr edit N --base <old>` that restores it. Then it merges with a merge commit and runs
   `finish`. GitHub's merge pins the head, not the base, so a merge to main between that last read
   and GitHub's merge is not stopped: `finish` reports it (below).
   `land --auto` arms auto-merge instead, after the same CI read (it does not wait for a pending
   run): it needs the repository's "Allow auto-merge" setting and a rule on main that gates a merge
   (the maintainer section above names the types), reads both before it retargets anything, and
   refuses naming what is missing or the rules it found instead; run `finish` once the PR lands.
   Auto-merge merges later, when the rule is met, and land cannot check main again then; on
   2026-09-27 the fork had neither the setting nor such a rule, so `land --auto` is refused and
   that case cannot arise yet. If the maintainer merged by the button or `gh pr merge`, run
   `scripts/batch.py finish <name>` alone. After its cleanup `finish` checks that the merge commit's
   first parent is the main verify read, and its second parent the batch head verify read, whoever
   merged. When either is not, or when it cannot tell (no merge commit reported, no main or head
   recorded by verify), it exits 1 naming the merge commit, the parent and what verify read: the
   tree on main was never swept or tested. Sweep a worktree at the
   merge commit then, as the message spells out (`git worktree add --detach ../romp-merge-<name>
   <merge>`, then `scripts/sweep.py run --tree ../romp-merge-<name> --python <python>`; it owes every leg there, as at
   any head), and tell the maintainer what it finds. `finish` also names the batch head's CI run,
   read as land read it (the push run at the landed head, the merge commit's second parent, never a
   manual run at the same commit),
   with its case: green, red, pending, missing, incomplete (a success not over `ci.yml`'s own jobs), or
   unread when the read fails after the merge.

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
