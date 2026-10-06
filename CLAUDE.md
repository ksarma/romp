# romp — repo instructions

> **Picking up the security work?** Start with `~/romp-handoffs/security-session.md` (outside the
> repo — it names upstream-unfixed holes) for the live status: the audit was re-verified against
> v0.8.0 (2026-08-13) and now ships upstream as PER-CHAIN PRs, not a private advisory (user's call,
> 2026-08-14). Chains 1–2 are merged upstream (#337, #352); Chains 3–5 are pending. `HANDOFF.md` in
> this repo is the project's DESIGN HISTORY only — its file:line refs predate the v0.6.0 merge and
> are three releases stale; use it for *why*, `git show` the fork commits for *where*.

## Philosophy
The bottleneck in AI coding is human attention. romp lets one person direct many
agents by spending that attention where it counts and surfacing only what is
worth acting on, so they keep the focus and flow that good work needs while
running them all in parallel. Every feature should serve that aim:
- **Spend attention, don't drain it.** A feature should take load off the user's
  working memory, not add to it. Glanceable by default; mechanics one click away.
- **Make re-engagement cheap.** Speak in the user's terms, the outcome and the
  why, never the agent's play-by-play, so picking a thread back up costs a glance.
- **Interrupt only when the human is the bottleneck.** "Needs you" means a
  decision only they can make. Waiting on a peer, a build, or another session is
  not that. Every false interrupt is a broken flow state.
- **Scale to parallelism.** Features should hold up across many concurrent
  sessions and let agents coordinate among themselves, handling the details the
  user never needs to see.
- **Never lose the thread.** Context persists, dead sessions revive with their
  history, nothing important silently drops, so stepping away is safe.

## Vocabulary — do not use the word "fleet" (user rule, 2026-08-01)
"Fleet" is not the user's word and they don't like it. Don't reach for it in new
prose, code, identifiers, commit messages, UI copy, docs, or anything else you
write for them. Say the plain thing: **sessions**, "the sessions you're
running", "your sessions" — and "across every session" where you'd have written
"fleet-wide".

The word is still all over the existing repo — a UI pane named Fleet
(`ui/webview/fleet.ts`, `fleet-pane.css`, `#fleet-list`), plus docs, plans and
tests. That backlog is deliberately NOT a rename-on-sight task: a sweep like
that is its own change, and it needs the user's call on what the pane is called
instead. This rule governs what you ADD. Rephrasing a line you were already
editing is welcome; renaming identifiers is not, until that call is made.

## Privacy — no real session data or personal identifiers in this repo
This repo may go public; assume every commit is permanent and world-readable.
- **Never copy real recorded data into the repo** — no real prompts,
  transcripts, per-turn summaries, postal messages, or message ids, not even
  "just one" to reproduce a bug. When a real session triggers a bug, write a
  SYNTHETIC reproduction: invented prompt text, placeholder UUIDs
  (`11111111-2222-...`), hostname `TESTHOST`. Live data belongs only under
  `~/.local/state/romp/` and `~/.claude/` (both outside the repo).
- **No personal identifiers** in code, comments, fixtures, docs, or commit
  messages: no names, machine/host names, vault names, emails, or absolute
  home paths (use `$HOME`/`~`).
- **Paraphrase the user, never quote them.** The `(the user <date>: ...)`
  attribution convention that explains WHY code exists is fine — but it must
  paraphrase, never embed a verbatim quote of what they typed. A quoted
  utterance is real recorded data. Write `(the user 2026-07-02, who wanted one
  shared picker)`, NOT `(the user 2026-07-02: "same code path, one picker")`.
- **No real session or goal names from OTHER projects.** A bug that surfaced in
  some other session is documented with a SYNTHETIC session name (`web`, `api`,
  `TESTHOST`) and an invented goal title — never the real project's nickname or
  goal text (which leaks what that unrelated project is). Add any coined
  project/session nickname to `~/.config/romp/private-strings.txt` so the test
  catches it. Reuse the neutral demo domain the doc screenshots use (a
  `notes-api` with `web`/`api`/`tests` sessions) rather than inventing per-test
  worlds.
- Two machine-local backstops enforce this, neither a substitute for the rule:
  the `.githooks/pre-push` hook greps each pushed ref's TIP tree (regular files
  and symlink targets), plus, for every commit new to every fetched remote, the
  lines it ADDS, its message, and the domain of any author or committer address
  the clone is not configured to use (`user.email` in any scope, or the
  environment's), and an annotated tag's own tagger and message, for the strings
  in `~/.config/romp/private-strings.txt` (absent file → no-op, so contributors
  are unaffected; it reads pushed shas, not the working tree, so it arms every
  worktree — a working-tree scan missed a leak pushed from a peer worktree on
  2026-07-25; added lines rather than every commit's tree, so a branch that
  only INHERITED a string main has since redacted pushes once it merges the
  main that carries the redaction — 2026-09-06; "new" to EVERY fetched
  remote, so a clone with a fork and the project as two remotes is not refused
  over the project's own history when it pushes a branch cut from the project's
  main to the fork — 2026-09-07; and the metadata since 2026-09-09, when a
  clone with no `user.email` had git stamp `<login>@<hostname -f>` on a
  branch's commits and a pushed merge, through both content scans); a text
  file whose diff attribute marks it binary (a `-diff` line or the `binary`
  macro in `.gitattributes`, `.git/info/attributes` or the file
  `core.attributesFile` names, or a driver with `diff.<driver>.binary` true)
  is refused rather than read, since git's grep and diff both skip such a file
  and a banned string in one published (2026-09-21); the refusal names the
  path and the attribute as the cause, and the remedy: remove the attribute
  for that path, or keep the file text on purpose with an explicit `diff`
  line for it that outranks the `-diff`; a rename or copy of such a file is
  refused the same way, since its bytes reach the remote under the new path;
  the same refusal covers any other text blob that git's own read calls
  binary, whatever rule made it so, when that blob is absent from the pushed
  tip (one the tip holds is read by the tip's own scan): a blob over
  `core.bigFileThreshold`, where the refusal names the blob's size and the
  key's value, since no attribute of the path accounts for the verdict, and
  the remedy: an explicit `diff` line for the path, which outranks the key,
  or the key raised above the size or unset (for a symlink's target only the
  key helps); and a commit that turns a file binary by its bytes into text,
  where the refusal names the previous version's bytes as the cause, since
  git prints no text diff for such a pair and the scan could not read the
  new text, and the remedy: fetch the remote whose history already holds the
  commit and push again, or, when no remote holds it yet, set an explicit
  `<path> diff` line in `.gitattributes` on the previous version's path (the
  old path for a rename; the file's own path otherwise, a merge's parents'
  included), so git prints the change and the scan reads it; the hook names
  `--no-verify` last, since it publishes the new text unread;
  a commit whose header names an encoding off the hook's list of those git
  converts to UTF-8 with every ASCII byte kept (UTF-8, EUC-JP, ISO-8859-1 and
  CP1252 are on it; UTF-16, SHIFT_JIS, BIG5 and the EBCDIC pages are not) is
  refused by name, clean or not, since the message and address checks read
  the commit as git converts it, which under such an encoding can drop or
  change the bytes of a banned string (one published that way, 2026-09-26);
  recommit it under UTF-8, or push with `--no-verify`;
  and the maintainer's clone carries an UNTRACKED
  `tests/test_no_personal_identifiers.py` that scans the working tree for the
  same strings plus that machine's hostname and home path. The pytest file is
  deliberately not in the repo: one machine's identifiers mean nothing on anyone
  else's clone, and a contributor's test run must never trip over it. Both read
  text only, so screenshots and recordings under `docs/assets/` must be
  eyeballed for on-screen session content before release.

### Credentials: gitleaks scans every pushed commit and all of history (user rule, 2026-08-05)
The rule above is about identifiers a human can enumerate. Credentials are the
other half and cannot work that way: nobody knows a token's text until it leaks,
so there is no list to write. **gitleaks** covers them, in two places:
- **`.githooks/pre-push`** reads for itself the changes a push would publish:
  the lines the pushed commits add, each merge by its combined diff (the lines
  in none of its parents, so a secret typed into a conflict resolution is read
  too) and by its first-parent diff, and a merge's binary path whole (below).
  It hands those bytes to gitleaks, which runs no git, and refuses the push on
  a hit. It needs
  gitleaks 8.25.0 or later: the hook's flags need 8.24.0, and this
  repository's `.gitleaks.toml` uses the `[[allowlists]]` form, which gitleaks
  reads correctly from 8.25.0 on (CI's pinned 8.28.0 is above the floor). A
  push with something to scan is refused under an older gitleaks, or one whose
  version the hook cannot read, and the refusal names the floor and the
  remedies. No gitleaks on the machine means a
  loud notice and no scan (requiring an install to push would break every clone
  that never asked for it); a gitleaks that fails to run refuses the push and
  says so, and so does one that ran but cannot show what it scanned: an error
  line in its own log, a scanned-byte figure that is not the count of bytes
  the hook handed it or no figure at all, or a count of files read that is
  not the count of files the hook handed it. The
  hook's read carries `--text`, so a diff attribute cannot hide a credential
  in a commit that is not a merge (except in a submodule's own diff, below):
  a path git would otherwise call binary (a
  `-diff` line or the `binary` macro in an attributes file, or a blob over
  `core.bigFileThreshold`) is diffed as text and scanned like any other, while
  a plain patch stream prints no hunk for it. A merge's combined diff applies
  git's binary verdict whatever `--text` says, so the hook reads a merge's
  binary path whole from the merge's result blob. That whole read has a cost:
  a push is now refused when the blob holds a credential already published.
  Its witness is the round 10b case in `tests/pre-push-hook.bats` titled
  "A.2's disclosed cost, with its witness". The first-parent read has the
  same kind of cost: a merge that brings in a credential a remote already
  holds (say, a branch merging a `main` that gained one since the branch was
  cut) is refused, as it was before the hook read the changes itself.
  The hook also refuses a push on a line of git's answer it cannot read, and a
  push carrying a commit of 64 or more parents (the identifier scan refuses
  that too), since git's combined diff drops or garbles the lines such a merge
  adds. A push that changes a path whose diff attribute names a driver with
  a `diff.<driver>.textconv` is refused, naming the path and the driver, even
  for a pure rename or a mode change: a credential could show only in the
  driver's rendering, which the hook does not read. Review the path by hand,
  then set `ROMP_NO_GITLEAKS=1` for that push. The hook cuts the pushed
  lines into hunks as gitleaks' own git mode (`git log -p -U0`) would in
  this clone: it reads the clone's `diff.algorithm`, `diff.interHunkContext`,
  `diff.renames` and `diff.submodule`, and the environment's
  `GIT_DIFF_OPTS`, as git log does. It refuses a push under a value of any
  of those four `diff.` keys that it does not read, and under any
  `diff.<driver>.algorithm` in the clone's config, whether or not a file's
  attribute names that driver; each refusal names the key and its remedy.
  For `diff.submodule`, a value it does not read is anything but `short`,
  `log` or `diff`, spelled so: a spelling git warns about and ignores
  (`Diff`, say) is refused too, since the hook fails closed. Under
  `diff.submodule=diff` the hook also scans a submodule change's own diff,
  as git log shows it. Git produces that diff without `--text`, so a file
  git calls binary there is skipped, as it is in git log. An external diff
  that reaches the submodule's diff (`diff.external`, a driver's `command`,
  or `GIT_EXTERNAL_DIFF`) makes the hook refuse even a clean push, on lines
  it cannot read, until the external diff is unset. And the hook still
  reads a submodule change that `diff.ignoreSubmodules=all` or
  `submodule.<name>.ignore=all` has git log skip, so a credential there is
  refused.
  The hook refuses a push with something to scan when the gitleaks config gives
  any rule a path condition, naming the rule and the config file, since the
  scan cannot apply the condition; support for such rules is a held follow-up.
  Two path values are exempt: an empty one, which gitleaks reads as no
  condition, and, on each of the five gitleaks default rules scoped to a path,
  that rule's default path exactly as the hook's own table spells it, so a
  config copied from gitleaks' default passes. The hook reads the config before
  any scan: the repository's `.gitleaks.toml`, or, with none, the one
  `GITLEAKS_CONFIG` or `GITLEAKS_CONFIG_TOML` gives, each with the files its
  `[extend]` names. With none of these, gitleaks uses its own default, which
  the hook does not read. It refuses the push on a construct it cannot parse,
  and on a key set twice in one table, naming the key, both lines and the
  file. Keys are compared without case, as gitleaks compares them, so `id`
  beside `ID` refuses, and so does a table named in two spellings
  (`[extend]` beside `[Extend]`): gitleaks keeps one of the two by a rule
  the hook cannot follow. Every scanner run reads the hook's copy of the
  config, so the hook's check and the scan read the same bytes.
  A path allowlist on a rule (the rule's own, or a targeted one) is matched
  against the names the scan gives the pushed lines, not against the files'
  paths. Those names are numbers, and, for the five default rules scoped to
  a path, the names of two copies the hook makes of a file those rules
  could match. One that matches none of those names changes nothing, and
  the rule fires. One that matches them makes gitleaks skip the rule when
  its paths decide alone, as in an OR allowlist (the default condition) or
  an AND one that gives only paths: the push is then refused, even when the
  file is clean, naming the rule and the file. An allowlist for
  extensionless names does this, and so does `paths = ['.*']` written to
  switch a rule off. An AND allowlist that also gives a regex or stopwords
  drops only the values they match. Where its paths match the numbers, the
  push is still refused when it drops a value, and a clean file passes.
  Where they match both copies' names but not the file's path, a credential
  its regex or stopwords match is published. This is the residual stated in
  the hook's header: such an allowlist keys on names the hook makes up, and
  has no honest use.
  Excuse a false alarm by its value, with a regex or stopword allowlist
  that gives no paths, and switch a rule off with `disabledRules`.
  Under a config that carries such an allowlist, the hook first runs
  gitleaks once more, over text of its own, to check that the running
  release reports the skip in words the hook reads (every release from
  8.25.0 to 8.30.1 does); when it does not, the push is refused, naming the
  gitleaks version: re-verify the hook against that release, or set
  `ROMP_NO_GITLEAKS=1` for one push.
  A repository rule anchored at the start of the text (`^` outside `(?m)`,
  or `\A`) misses a credential on the first added line of a hunk whose
  leading bytes gitleaks' file-type check would skip (an executable's `MZ`,
  a PDF's `%PDF`, a zip's `PK` and the like); write such a rule with
  `(?m)^`, which matches there.
  `ROMP_NO_GITLEAKS=1` skips the credential scan for one push, and
  `ROMP_GITLEAKS` points at a binary. A clone that carries any replace ref
  (`git replace`) is refused before either scan runs when either scan is armed,
  whatever the ref replaces and whether or not that object is in the push: under
  a replacement what a scan reads and what the push transfers can differ, so a
  clean report could be false; the remedy is `git replace -d <object>`, or a
  push from a clone that carries none. This is the same hook as the identifier
  scan and both report before it refuses, so one push tells you about both.
- **CI's secret scan** runs on every push to the fork, of a branch or a tag,
  whose commit carries `.github/workflows/secret-scan.yml`: that workflow's push
  trigger has no branch filter, so every branch push is scanned, once, with no
  run cancelled by a later one (2026-09-30), and it has no `pull_request`
  trigger (dropped 2026-10-04, since the private runner bills every run).
  `ci.yml`'s `Secret scan (gitleaks)` job runs the same job on a batch push, a
  manual run, and, under `ci.yml`'s smaller shape alone, its weekly schedule
  (THE SHAPE SWITCH in `ci.yml`'s header), and
  `tests/test_ci_secret_scan.py` holds the two copies equal but for the job's
  name. Each run scans all of history from a pinned, checksummed binary: the
  commit its push put on its ref, and every branch and tag the checkout
  brings. When a push's ref has moved on or
  been deleted before the run, the checkout fetches that commit by its sha, so
  a commit force-pushed over is still scanned. It needs `fetch-depth: 0`: a
  default checkout scans one commit and reports clean. Its history scan
  carries `--text` too, so a committed `-diff` attribute cannot hide a path's
  credential from it: a plain patch stream prints no hunk for such a path, and
  the job's tree scan reads `HEAD` alone, where a removed file is gone (the
  road was verified 2026-09-21 on the pinned scanner and closed by the fork's
  PR 890; the tree's one `.gitattributes` sets `-text`, not `-diff`, so no
  commit here was hidden). GitHub reads a push's workflows from the commit the
  push puts on its ref. So a push to an open pull request's branch is scanned
  once when the branch carries the file, and not by this workflow when the
  branch never had it (a branch cut from `main` before the file landed, or cut
  from the project), until the branch merges `main`. A pull request from
  another repository is not scanned by this workflow, since its pushes go to
  that repository; its commits are scanned by the next run here whose checkout
  reaches them, such as a batch push that merges them.
  When a pull request's branch and its base both lack the file, its merge
  commit carries an older `ci.yml`, whose `Secret scan (gitleaks)` job runs on
  pull requests (`main`'s copy before the file landed runs it, and so does the
  project's), though that copy cancels a pull request's run in progress when a
  newer push to it arrives. Three kinds of push start no run: a push to a
  branch cut before the file landed, until it merges `main`, whether or not it
  has an open pull request; a tag on such a commit; and a push whose commit
  lacks the file because it or an earlier commit on its branch deleted it. A
  push that edits the file runs its edited copy. Nor does GitHub start a run
  for a push whose head commit's message carries a skip instruction (`[skip
  ci]` and the like), for the tags of a push of more than three tags at once,
  or for a push of more than 5,000 branches at once. A commit only such a push carries is
  scanned by the next run whose checkout reaches it, and by none if it leaves
  every branch and tag first. The hook does not scan six kinds of push or
  commit, and CI scans each in the run of the push when the push starts one: a
  push where no gitleaks resolves (none installed, or `ROMP_GITLEAKS` naming a
  non-executable), a push with `ROMP_NO_GITLEAKS=1` (the hook skips its
  credential scan), a push with `git push --no-verify` (no hook runs), a push
  from a clone where `install.sh` never linked the hook into git's hooks
  directory (no hook runs at all), a commit any of the clone's remote-tracking
  refs reaches, which the hook does not read (another remote's ref, or a stale
  ref of the pushed-to remote whose commit that remote has since dropped), and a
  commit GitHub makes itself (a web edit or suggestion, the Update branch
  button). What the hook's scan passes inside a push it does scan, and CI's
  git-mode history scan reports, is reported by the run of the same push when it
  starts one: the residuals the hook's header states (a path allowlist with an
  AND condition keyed on the hook's own copy names, a repository rule anchored
  at the start of the text on a hunk led by a file signature, and a change that
  only removes lines from a text `.p12` or `.pfx` file).

Three things follow for anyone touching this:
- **A hit means rotate, not amend.** A credential that reached a commit is
  compromised from that moment; removing it in a later commit leaves it in the
  old one, and on a repo that may go public that is a published secret. Rotate
  first, then clean the history.
- **Excuse a false positive narrowly, in `.gitleaks.toml`, with a reason**: an
  exact value, never a path. A path exclusion silences the scanner for every
  future line in that file. There is one entry today (RFC 6455's published
  example WebSocket key, which the kernel's handshake tests use), allowlisted by
  value so a real key on the same line is still caught.
- **Do not write a credential-shaped literal into a test fixture.** The scanner
  reads this repo too, so a longhand fake token flags the very test that proves
  the scanner works; assemble probes at run time, as
  `tests/gitleaks-config.bats` does.

## This clone is a fork — everything ships to the fork (user rule, 2026-08-05)
This repo is a fork of the romp project, kept for the user's own purposes. Two
repos are in play and only ONE of them is ours to write to:
- **`origin` is our fork.** Every branch, push and PR goes there, with no
  exception that does not begin with the user saying so.
- **`upstream` is the project we forked from, and it is FETCH-ONLY.** Never push
  a branch, a tag or a commit to it, and never open a PR against it. Offering
  work back upstream is a deliberate decision the user makes per change; until
  they say those words, upstream is something we read.
- **The user's write access to upstream changes nothing for sessions** (user
  rule, 2026-09-05). The user was made an upstream maintainer, so `gh` under
  their token CAN now merge an upstream PR or push an upstream branch — and the
  remote guard below does not cover `gh`. No session does either without a
  per-PR instruction from the user naming the PR ("merge #N"): an offer's own
  adversarial review is not a licence to land it, and the standing word the
  upstream maintainer extended to the user's PRs was earned by that pipeline's
  rigor, not a reason to relax it. Offering stays as before (a PR opened from a
  fork branch); who merges it is the user's call, PR by PR.
- **The ledger under `upstream/` is the queue for those decisions** (user ask,
  2026-08-07; one file per candidate since 2026-09-06). When you land something
  upstream-worthy — a fix in code upstream ships too, not fork-only
  infrastructure — add an entry with `scripts/upstream-ledger.py new <slug>
  --title '...' --where '...'` and commit it with the change. Never edit
  `UPSTREAM.md` per change: it is prose only, and a table row there fails the
  test. The user prunes (`declined`, `keep-private`) or promotes (`approved`)
  by editing the entry's `status:` line.
- **The guard is configuration, not care.** `scripts/fork-remotes.sh` sets
  `upstream`'s push URL to a dead sentinel, so a stray `git push upstream` fails
  loudly instead of landing on someone else's project, points
  `remote.pushDefault` at the fork so a bare `git push` cannot wander, and makes
  the fork gh's default repository (`remote.origin.gh-resolved = base`, the key
  `gh repo set-default` writes, on origin and on no other remote) so a bare
  `gh pr view N` or `gh pr merge N` reads the fork's PR N. Without that key gh
  consults `upstream` first: on a fresh clone with both remotes and no terminal
  to ask on, `gh pr view N` read the project's PR N (2026-09-09), and
  `scripts/batch.py land` (which `scripts/land.sh` runs), merging by number
  without `-R`, would have aimed a merge at the project.
  `scripts/fork-remotes.sh --check` verifies all of it without changing
  anything, and is worth a run in any new clone or worktree, since this lives
  in git config and a fresh clone starts without it.
- **Checking for upstream changes.** `scripts/upstream-check.sh` fetches and
  reports what the project has added since we diverged, and which of those files
  we have also changed — the ones a merge will actually cost attention on. It
  reports and stops; taking the changes is the user's call, on a branch.
- **Two upstream-facing scripts are not ours to run.** `scripts/release.sh`
  cuts the project's releases (it defaults to the upstream repo and opens PRs
  there) and `bootstrap.sh` clones the project for a fresh install. Neither is
  wrong to read; both would act on upstream if run unthinkingly.

## Worktrees — work on an isolated worktree by default (user rule, 2026-06-29)
Do ALL non-trivial work on its own git worktree, not the shared main tree — concurrent
peer sessions clobber/commit each other's uncommitted edits in the shared tree (a peer's
broad `git add` will sweep up your work). Conventions:
- **One worktree per session, named after the session.** Branch + directory take the
  session's name, e.g. session `bugsdk2` → branch `bugsdk2`, dir `../romp-bugsdk2`
  (`git worktree add -b <session> ../romp-<session> HEAD`). So a glance at
  `git worktree list` says who owns what.
- **Never commit on the shared `main` checkout** (user rule, 2026-07-24). Branches and
  worktrees are how work happens here, with no "quick one in main" exception. A commit
  that lands on the local `main` branch and is not pushed immediately makes local `main`
  diverge from `origin/main`, and then every peer session is stuck: they cannot push,
  cannot fast-forward, and cannot reset the shared tree without destroying whatever
  uncommitted edits other sessions are holding in it. This happened on 2026-07-24 (six
  docs commits stranded on local `main`, already duplicated on a PR branch, blocking two
  other sessions).
- **Standing green light to publish.** When the work is done and tests pass, publish it
  without asking — to the fork, always (user rule, 2026-08-05, superseding the
  upstream-PR flow this repo was written around):
  1. `git push -u origin <branch>`. `origin` is the fork; `remote.pushDefault` points
     there too, so a bare `git push` does the same. Never `git push upstream` — see
     the fork section above, and `scripts/fork-remotes.sh` makes it fail if tried.
  2. Open a PR within the fork against `main`. PRs land through a batch
     (`scripts/batch.py`; see `docs/batching.md`): do not click merge. A change that
     must land alone lands as a one-member batch (`scripts/batch.py plan --only N`) on the
     user's word; `scripts/land.sh` runs `scripts/batch.py land`. Opening a PR against the upstream
     project is a separate decision only the user makes.
  A fork PR runs no `ci.yml` of its own (2026-09-27): its Checks tab shows the secret scan's
  run of each push whose commit carries `secret-scan.yml` (that workflow's push trigger has no
  branch filter, and it has had no pull request trigger since 2026-10-04; the credentials section
  above says which pushes start none), the tier-label check (next bullet) after the PR opens or
  reopens or its labels change, and Tier policy's skipped rows, which evaluate nothing on the fork.
  GitHub's CI (`ci.yml`) runs once
  per batch, on the push to `batch/<name>`, and not on the merge to `main`. The landing
  gate is the local sweep, `scripts/sweep.py`, whose result for the batch head's full
  sha `scripts/batch.py verify` and `land` read. `land` also requires that batch push's CI
  run green at the batch head, read from GitHub when it runs, and refuses a batch whose head
  does not contain `main`. It reads `main` once more right before the merge call; `main` moving
  between that read and GitHub's merge, or before an `--auto` merge fires later (`--auto` is
  refused until auto-merge is allowed and a rule on `main` gates a merge; the fork had neither
  on 2026-09-27), is not stopped, and `finish` then fails loudly: the merge commit's first
  parent is not the `main` verify read, so the tree on `main` was never swept or tested. The
  button and `gh pr merge` make no such check, so a batch merged by hand needs `main` unmoved
  since verify, and `finish` makes the same first-parent check after it (docs/batching.md,
  maintainer step 6).
  A PR owes a passing `scripts/sweep.py` result at its own head before its review round and
  again before its closing check: the round and the check read that result (`scripts/sweep.py
  check --tree <worktree>`) where they read CI before, so a push after the sweep needs a new
  one. `scripts/batch.py plan` leaves out a PR without one, naming the case, and `assemble
  --repin` refuses a new head without one; both read the batcher's state dir, so a result
  recorded on another machine is missing there (docs/batching.md, "If you open a PR").
  Anything in the code that reads the canonical repo (the release script's post-merge
  fast-forward and tag push, the kernel's update and drift probes) resolves the remote
  as `upstream` when the clone has one, else `origin` (`_release_remote` in
  `kernel/kernel.py`, `canonical_remote` in `scripts/release.sh`); never a literal
  `origin`. In this clone that remote is the project, not the fork: the kernel's update
  and drift probes read the project's main and tags, and the release script is not
  ours to run (see the fork section above).
- **Every PR carries exactly one tier label, and upstream ENFORCES the tier**
  (maintainers' rule, 2026-09-06; the policy decided 2026-09-07 and reset by the
  repository owner 2026-09-08: the gate depends on the tier and on the AUTHOR's role,
  and no tier has a time-based path). The project holds a PR with two required checks:
  "Exactly one tier label" (`pr-tier`) goes red on a PR with no tier label, or two, so
  an unlabeled offer never auto-merges there; "Tier policy" then holds it until the
  tier's gate is met. The rules are a pure function (`scripts/ci/tier_policy.py`,
  pinned by `tests/test_tier_policy.py`); the workflow
  (`.github/workflows/tier-policy.yml`) only fetches PR data and posts the verdict. See
  `docs/pr-tiers.md`.
  Roles are the author's collaborator permission upstream: admin is the repository
  owner; write or maintain is a member; anyone else is a contributor (the check gates
  members and contributors alike). The user's write access upstream (the fork section
  above) makes an offer from a session a member's PR. The fork's copy of the first check
  (`.github/workflows/pr-tier.yml`) counts the same labels plus one of its own: a batch
  PR (`scripts/batch.py`, `docs/batching.md`) carries `batch` alone and no tier, so
  adding a tier to a batch PR turns the check red. Every other fork PR carries one tier
  label, and on the fork every PR lands through a batch whatever its tier. The fork's
  copy of the second check (`.github/workflows/tier-policy.yml`) is gated to the
  upstream repository by its job-level `if:` (the header comment there says why), so on
  the fork it evaluates nothing and posts no Tier policy verdict; a fork PR is judged by
  the label check alone, and runs no `ci.yml` (the publish step above says what gates
  it). The fork's label check also runs on fewer events than upstream's: when a PR opens
  or reopens and when its labels change, not on a push or an edit, so a push leaves the
  new head without it until the next label event (the second divergence in its header).
  The author picks the tier at filing time; upstream's tier workflow also reads a
  `Tier: <tier>` line in the PR body (`Tier: fix`, say) from a contributor who cannot label
  and applies the label (a label already present wins; maintainers re-tier by relabeling):
  - `docs` (tier 0; upstream renamed it from `tests-only` on 2026-09-08, and both checks
    still accept the old spelling): documentation. On the fork that is tests, docs and
    repo plumbing, landing through a batch like every PR. Upstream, to the check it is
    the same tier as `fix`: merges on green for every author.
  - `fix` (tier 1): a bug fix with a test that fails before it. Upstream it merges on
    green for every author: the check requires no approval, and whichever maintainer
    merges it is the whole requirement.
  - `feature` (tier 2): a self-contained new capability inside romp's existing model;
    put the design points in the body. Upstream, by the repository owner (an admin) it
    merges on green; by a member (write access) or a contributor it merges on the
    owner's approval on the current head. No issue, no waiting period.
  - `major-feature` (tier 3): new functionality that changes what romp does or its
    contracts. Discussed first (an issue, or the PR as the RFC) and merged only on
    agreement: upstream that is, for every author, a linked issue (`#N` in the body)
    with a comment by someone other than the author, the opener alone not counting; a
    member's or a contributor's additionally needs the owner's approval on the current
    head. An offer at this tier is filed **without** `--auto` and the merge is left to
    the maintainers.
  A standing change request by a maintainer (write, maintain or admin) other than the
  author holds a PR of ANY tier upstream until that reviewer lifts it; an approval by
  someone else does not. "Approval" upstream is a standing APPROVED review by an admin
  other than the author on the CURRENT head (standing = their latest approval, change
  request or dismissal; comment-only reviews never change it; a dismissed approval never
  counts, whoever dismissed it, and a dismissed change request clears only when the
  reviewer dismissed it themselves, so the author cannot dismiss the peer's objection
  away to merge on green). A renamed file counts under both its paths. Any PR touching
  `.github/` or `scripts/ci/`, the gate's own workflow and code, needs the owner's
  approval regardless of tier when the author is not an admin (a PR's own
  `pull_request` workflow can post a same-named check run, so a human looks; the
  owner's own PRs are exempt; the residual and the CODEOWNERS rule that closes it are
  in `docs/pr-tiers.md`). Those gates are the maintainers'; none of this changes what a
  session may do here: offering stays a PR from a fork branch, and merging or approving
  upstream stays the user's per-PR call (the fork section above). The line that matters
  is 2 vs 3: adds a capability inside the existing model, `feature`; changes what romp
  is, `major-feature`, talk first. The ledger entry's `tier:` line records the pick for
  an offer.
- **Clean up when finished.** After publishing, remove the worktree
  (`git worktree remove ../romp-<session>`) and delete its branch — don't leave stale
  worktrees lying around.
- **When you do touch the shared tree** (reading, or an explicit "do this in main"), use
  a focused `git add <paths>` — never `git add -A`, which sweeps peers' edits — and never
  `git reset --hard` or `git clean` there: other sessions' uncommitted work lives in that
  tree and it is not yours to discard. See [[shared-worktree-use-isolated]].

## Testing
Every bug fix or feature change must land with a test that covers it (user rule,
2026-06-12). Test homes: `tests/test_event_model_golden.py` and the other
`tests/test_*.py` for the Python pipeline (`kernel/`, `cli/`, `postal/`), `tests/*.bats` for shell
surfaces. Reproduce the bug in a failing test first when practical; fixtures
live in `tests/fixtures/`.

### Any `kernel/kernel.py` change runs the webview tests (2026-09-20)
A change to `kernel/kernel.py` owes the webview leg (`npm test` in `vscode-extension/`),
whatever the hunk's language. The leg pins kernel.py by SOURCE TEXT: well over a hundred of
its `.test.ts` files read the file and assert on its inline JavaScript AND on its Python
(`ui/webview/user-todos-switch.test.ts` reads kernel.py and asserts that the User-todos
switch's 409 literal appears at least twice, once per request route), so a pure-Python
refactor that touches no `ui/` file and no JavaScript line can still turn it red. Precedent:
our PR 994 to the project (2026-09-20) lifted the route bodies into functions and turned the
project's `vscode-extension` CI job red on that one test of 5224. The leg runs for every change:
the three webview legs (typecheck, `npm test`, build) also read files outside `kernel/kernel.py`,
`ui/` and `vscode-extension/` (other kernel modules, tests, docs, the CI workflow), and no derived
set of the files they read is kept, so no rule over the changed paths can say they may be skipped
(PR 926's review measured the old rule, "skip when those three are untouched": of the 581 PRs
merged since 2026-08-28 that it let skip, 191 touched a file those legs read or probe). `scripts/sweep.py` owes the three webview legs (typecheck, `npm test`, build) at
every head it sweeps, a member PR's included. Corollary for the pins themselves: a pin keyed on
WHERE code lives says in its message what it guards (the route still reaches the function) and
points to the executed test that proves the behaviour, so a reader never mistakes the weaker
guarantee for the stronger one.

### A test that mints its own state root pins `session-hosts` off (2026-09-11)
Per-session hosts are ON by default (T348): a backend over a state directory with no
`session-hosts` file starts a real `bin/romp-session-host` for any session it connects. The
runner's conftest writes `off` into the one state root it floors for the run, and only that
one. A test that builds its own temp state root (a bare `tempfile.mkdtemp()` handed to
`SdkBackend`, a lab kernel's xdg root) is outside that belt and must write `off` into
`<its root>/session-hosts` itself, unless it means to run a host, as the hosts-on end-to-end
tests do by writing `on`. Precedent: `tests/test_cut_turn_tree_kill.py` `_backend` and the
connect-loop harnesses in `tests/test_sdk_backend.py` (`_hosts_off`).

### Goal-store fixtures use a PRIVATE synthetic sid (2026-08-24)
An instance of the standing synthetic-fixtures rule with a mechanism behind it:
any Python test that MINTS GOALS under the shared `11111111-2222-…` placeholder
sid can be silently re-flagged by OTHER test modules' journaled user overrides —
`load_goals` replays the per-sid override journal (`STATE/overrides/<sid>.jsonl`)
on every load, and node ids collide across tests (every fresh store mints `g1`),
so a resolve another module journaled against the shared sid lands on YOUR node
mid-test. The failure is ordering-dependent: green alone, red only under the full
suite. Tests that mint goals therefore use a private synthetic sid of their own
(any invented uuid; still synthetic, never real) and clean their sid's journal in
tearDown. Precedent + worked diagnosis: the model-fallback dedupe tests' class
docstring (`tests/test_model_fallback_card.py`, DedupeBackstop). A second face of
the same collision (2026-09-08, four end-to-end tests green alone and red in CI's
serial order): a test that exercises the nudge walk and stubs `jd.load_goals` as
the walk's snapshot must ALSO stub `jd.load_goals_shared_or_fault`, the walk's
shared read-only view since the jobs-stage change, and move the goal directory
with the state (`jd._rebind_state(tmp)` repoints GOALDIR and every derived dir;
assigning `jd.STATE` alone leaves GOALDIR where import bound it), because the
shared view reads a store FILE when one exists and delegates to `load_goals` only
when none does, so an earlier module's store for the shared placeholder sid at the
unrebound GOALDIR was what the walk read (no goal due, no fire, a deferral never
cleared, a KeyError). Precedent: `tests/test_nudge_injected_turn_arm.py`,
`test_nudge_fresh_guard.py`, `test_nudge_memo_deadlock.py`, `test_nudge_bundle.py`.

## The documentation front pages are written for a person (user rule, 2026-09-20)
`docs/index.md`, `docs/install.md` and `docs/guide.md` (and `README.md`, which mirrors
the home page) are read by someone who knows nothing about romp yet. The scarce thing
is that person's attention, and an agent installing romp for them can find any detail
elsewhere, so these pages buy a first reader's understanding and spend nothing else.
- **Short paragraphs.** About 70 words is the cap, and shorter is better: one idea per
  paragraph, its point in the first sentence.
- **No implementation detail, no repo-internal vocabulary.** Judges by name, state
  files, environment variables, pick orders, failure modes and design history belong in
  `docs/reference.md`.
- **The install command inside the first screen** of the install page, above everything
  optional. A visitor came for that line; the interpreter rules and the service's
  environment are reference material.
- **One short paragraph per feature, no trailing link.** A new capability gets a
  paragraph in the guide stating what it does, and its detail goes into
  `docs/reference.md` under a heading that matches the feature's name. The guide points
  at the reference once, in its opening line; a paragraph never ends by sending the
  reader somewhere else, a link to a section of the same page included, except a
  paragraph that is only a link, directly under a heading (README's License line); and
  no page tells a reader that the details are elsewhere or that an agent can find them.
  Moving text OFF these pages is always welcome; adding to them is what needs a reason.
- **State what a thing does; do not sell it.** No benefit claims the reader can judge
  for themselves, no "more than a text box", no "opens where you are reading": name the
  behaviour ("the message box also supports attachments, session names and recall"). And
  write each page as it stands, never as a response to how it used to read.
- **A link carries the reason a reader would want it**, in the same clause, and then
  goes: "On a machine with several Pythons, [which one runs the kernel](...) matters".
- **Call each part of the interface what the interface calls it.** The pane labelled
  Sessions holds the timeline; write "the Sessions pane", not "the timeline", for the
  pane.
- **Process documents stay out of the site's navigation.** `docs/pr-tiers.md` and the
  plans are contributor process, reachable by path and by URL (`not_in_nav` in
  `mkdocs.yml`); the site's top-level sections are for people using romp.
- `tests/test_docs_front_pages.py` pins the word budget per page, the paragraph cap, the
  install command's position, the nav rule, the guide's single pointer to the reference
  and no paragraph ending on a link. A session adding to these pages keeps it
  green; when a page genuinely needs more room, raise the cap in the same change that
  spends it, so the budget stays a decision someone made.

The July 2026 pages are the shape to hold: by September the guide had grown to 11,000
words and the install page opened with a screen on which interpreter runs the kernel,
which is how the rule came to be written down.

## Authoritative sources — fail loudly, don't degrade silently (user rule, 2026-07-03)
Read state from its AUTHORITATIVE source — a designed API, or the live store that
owns the data — never a lossy reconstruction (scraping a transcript, a heuristic
guess). When choosing a source, first look for a real API; only fall to reading a
store/file if none exists, and say so.

When the authoritative source is UNAVAILABLE, **surface an error to the user** —
do NOT silently fall back to a worse heuristic that can be quietly wrong. A visible
error we can see and fix beats stale/incorrect data that looks fine and misleads.
A silent fallback hides the very breakage we need to know about. (Triggered by the
TO-DO card, which folded the transcript — missing subagent updates — instead of
reading Claude's task store; the fix reads the store and surfaces an error when it
can't, rather than quietly folding. There is no SDK API for the to-do checklist —
verified, not assumed.) This is the same spirit as the event-vs-heuristic rule
below: don't approximate when the real thing is available; when it isn't, be loud.

## Messages we inject into a session: the agent does not know romp exists (user rule, 2026-07-24)
Every message romp puts into a session — a nudge, a follow-up, a clear wrap-up, a
canned status ask — is read by an agent with NO idea it is being tracked. It has
never seen the feed, has no concept of a card, a goal, a board, or a column, and
cannot act on any of it. So write these as **the person it works for asking for
something**, in their words:
- **No romp nouns in the prose**: card, board, goal, column, cleared, dismissal,
  nudge, status check. Say the thing instead. "Status check on this card" → "Where
  does each of these stand?"; "the goal above was cleared off the board — a
  dismissal, not a completion" → "I'm dropping this one."
- **No taxonomy handed over as reply slots.** romp's planner files four verdicts
  (done / in progress / blocked-on-you / obsolete), but naming them at the agent
  turns a question into a form. Ask like a person — "what shipped, what's next, or
  exactly what you need from me if you're stuck" — and the same four answers come
  back for the planner to file.
- **Short.** A long directive reads as a system notice however it is worded. The
  clear wrap-up carries the same content in about half the words it started with.
- Draft this copy with the `jld` skill, the way any user-facing writing is drafted.

THREE deliberate exceptions, all fine, none a licence to widen:
- **The SessionStart instruction** that asks a session to report what it finished
  and what it is blocked on. That asks for ordinary self-reporting; it names no
  romp machinery and needs none.
- **The marker tail** (`<!-- romp-note: … an external tracking system that is not
  relevant to your work — ignore them -->`). It describes the markers WITHOUT
  naming romp, on purpose: naming it would explain nothing to a model that has
  never heard of it.
- **The session prompt's housekeeping note** (`claude/romp-session-prompt.md`) —
  the ONE place romp is named to a session, on purpose (the user 2026-07-25, after
  a restart notice reached a session that had no idea what "the romp kernel" was).
  It pre-explains the artifacts every session eventually sees: `[romp]` notices and
  `<!-- romp-* -->` comments are an external session manager's bookkeeping, to be
  ignored beyond any practical information they carry. It explains the ARTIFACTS
  only; cards, boards, goals and the rest of the machinery stay unnamed, and every
  injected message still speaks as the person the agent works for.
- Also fine: the `[romp] The kernel restarted…` notices in `sdk_backend.py`. Those
  are genuinely ABOUT romp — they tell a session why its turn was cut — so they
  name it (and the housekeeping note above gives the name meaning).

`tests/test_injected_voice.py` renders every injected body and fails on romp
vocabulary in the prose, so this holds without anyone remembering it.

## Design
Prefer exact event-based mechanisms over time-based heuristics (grace periods,
debounces, age thresholds). If a time window seems needed, find the event it is
approximating and key on that event instead.

### Cards move on new information, never on inference flaps (user rule, 2026-07-29)
Every card move claims something changed, and the user's eye follows it — so a
card may move only when NEW INFORMATION arrives (a judge verdict filed from fresh
evidence, a user gesture), and must move MINIMALLY: accurate, but never
ping-ponging without user action. Two standing corollaries:
- **Transient states latch until the deciding event.** A state like "reply
  pending judgment" holds its column until the judge actually rules — never
  re-derived per build from a flapping input (an open-turn bit, a per-build
  recomputation). The audited card flipped working↔needs-you seven times in six
  minutes because its drop-to-Working was bounded by the open turn, a proxy that
  toggles at every turn boundary of an active session; the fix latches on the
  unblocker's `blockCheckT` watermark, the event the proxy was approximating.
- **A writer whose evidence predates the diary stands down.** Any mechanism about
  to move a card must check, at the write moment, whether a verdict was FILED
  after the evidence it is acting on — and if so, yield (the judges already ruled
  on a newer world). The nudge does this at both ends now (`_nudge_fire_list`
  arm-time guard, `_mark_nudge_failed` moot retire): before it, a nudge fired
  five seconds after the unblocker had ruled its question answered, and then
  converted its own cut-off response turn into a false needs-you block
  presenting a brief the user had already answered.
When adding any mechanism that can change a card's column, name the exact event
that justifies the move; if the trigger can flap between builds without new
information, it is the wrong trigger.

### UI design rules live in `ui/CLAUDE.md`
Progressive disclosure, centered panels, font sizes, the menu vocabulary, the accent
color, loading/waiting states, click-safe buttons, and layouts for many tags and
sessions are covered there; it loads whenever you work under `ui/`.
