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
main's copy of the file, so a member PR's pushes are scanned even on a branch cut from main before
the file landed. Among the pushes that start no run: a push to such a branch that has no open PR,
until it merges main; a tag on such a commit; and a push whose commit lacks the file because it or
an earlier commit on its branch deleted it. A PR that conflicts with its base gets no run of its
own until the conflict is resolved (CLAUDE.md, "Credentials", says what the scan reads, which
pushes start no run and GitHub's other limits). Nothing in the landing reads that workflow's runs.

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
   does). To resolve a small conflict instead, `assemble <name> --resolve N`, resolve per hunk in
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
   push, a manual run, the weekly schedule), and the macOS cells only in a manual run
   (`workflow_dispatch`) or the weekly schedule. CI's free-threaded cell runs pytest with
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
   writes into your repository: each job's clone holds the sha alone, with no branch and no tag of
   yours, as CI's checkout fetches the pushed sha alone, and names no remote, so a `git fetch` in
   a later job copies nothing. When your repository is shallow as the sweep starts, each clone is
   shallow the same way: the sweep reads your shallow file before the first leg and gives every
   clone that copy, so a leg that writes the file changes no later job's clone. After the last leg
   the sweep reads the file again, and when it differs from that copy (a leg wrote or removed it,
   or anything else did during the run) the run is invalid, naming the file: the sweep does not
   restore it, so the next sweep's clones read it as it now stands: cut where the file now says,
   or, when a leg removed it, not shallow at all. A shallow file that is not a regular file (a
   FIFO, a device, or a symlink, which the sweep does not follow) is never opened: one there as the
   sweep starts refuses the run before the sweep's first `git` call that would read it, and one a
   leg leaves makes the run invalid, each naming the file; `scripts/sweep.py check` refuses one
   the same way, before its first `git` call. The legs of one job share its
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
   names each one it finds, and opens none of them, since reading one could wait or read without
   end, and `git` follows a `.git` file to the directory it names. A leg can also leave
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
   your shallow file before the re-read after the last leg, and the run then names the file. The sweep writes every
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
   checkouts and TMPDIRs, and the legs start with both signals at their default action either way. A leg that
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
   batcher's own tree, is, and so is a result with a run that records no private checkout). A missing result names the directory verify read and the variable it
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
