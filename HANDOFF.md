# Handoff — security pass on the fork (2026-08-06)

For whoever picks this up next. Branch `claude/romp-fork-setup-p4myn7`, open as **PR #1** against
the fork's `main`. Nine commits, CI green on all seven checks. Working tree clean, everything
pushed.

Read `CLAUDE.md` first — it is the repo's own rules and they are load-bearing here. This file is
only what a fresh agent cannot reconstruct from the diff.

## What landed

| | |
|---|---|
| **Fork guards** | `scripts/fork-remotes.sh` gives `upstream` a dead push URL so a stray `git push upstream` fails instead of landing on the project we forked from. `scripts/upstream-check.sh` reports what upstream added since we diverged. |
| **Credential scanning** | gitleaks in `.githooks/pre-push` (pushed commits) and a CI `secrets` job (all history, `fetch-depth: 0`). One allowlist entry, by exact value: RFC 6455's published example WebSocket key. |
| **Nine security fixes** | From an 8-surface audit. Cookie/Origin gate on `/ws`, relay Content-Type, forged postal origin, `--safe-mode` + private cwd for the summarizer, judge scratch off `/tmp`, serve token out of argv, VS Code exec path, postal marker forgery, judge prompt marks. |

Two adversarial reviews ran over this work and both found real defects — including two rounds where
a fix's own test ratified the bug it was meant to catch. The commit messages carry the detail; they
are written to be read.

## Open work, most valuable first

### Resolved since the first handoff (2026-08-06)

The original items 1–4 are done, and a second, adversarial re-review (six Fable agents over the
whole diff, a different model than wrote it) landed on three stacked PRs against this branch:

- **The uninstaller guard hole (old item 1)** — fixed on PR #2, then a re-review found the *fix*
  was itself incomplete (a shell suffix-trimmer left a trailing newline and internal `//` / `/./`
  spellings reaching `rm -rf` on `$STATE`/`$HOME`). Rewritten to canonicalise the path in Python and
  validate what actually gets deleted; property tests over the spelling class, verified live.
- **The mid-test `! grep` assertions (old item 2)** — the 17 mid-test ones are armed on PR #3; the
  35 final-command ones work as written and were left alone. `grep -rn '^\s*!\s*grep' tests/*.bats`
  now finds zero mid-test occurrences.
- **The `/handoff` residual (old item 3)** and **the incomplete PR description (old item 4)** —
  both written into PR #1's description.

The re-review's own confirmed findings, fixed on PR #4 (`security-review-2`), each with a test that
fails before the fix: the judge scratch-refusal that blanked card summaries (a `""` counted as a
model failure); gitleaks missing merge-commit secrets in both the pre-push hook and CI
(`--diff-merges=first-parent`); an uncapped `/handoff` map; an unanchored gitleaks allowlist; a
`fork-remotes.sh --check` that gave false assurance; and `gitleaks-config.bats` never running in CI.

### Deferred follow-ups the re-review surfaced (tracked, not yet done)

Confirmed real, left for a deliberate change (some pre-existing, some need a live machine):

1. **Clickjacking — HOLD until a live client test.** No `X-Frame-Options`/CSP `frame-ancestors` on
   any kernel response, so the authenticated dashboard is frameable from a hostile same-site
   loopback page (the same attacker the `/ws` cookie gate defends against). The safe header is
   `SAMEORIGIN` / `frame-ancestors 'self'` — it preserves the dashboard's own same-origin sub-frames
   (`/chat`, `/feed`) — but framing is exactly what the VS Code webview / phone / tailnet clients
   might rely on, and those cannot be verified offline. Add the header and confirm every shipped
   client still loads before trusting it.
2. **Relay `.svg` is scriptable via `/remote`.** `image/svg+xml` is in the preview allowlist and the
   relay serves remote-controlled bytes under it. Not a live XSS in the shipped UI (SVG reaches only
   `<img>`, never a same-origin iframe), but it becomes one on any top-level load of the URL. Needs a
   fix that does not break inline preview (a plain `Content-Disposition: attachment` would).
3. **Postal `frm_id` is an unvalidated identity claim** (`postal_service.py:1876` → `event_model.py`
   postal index). A `trusted`/approved peer can stamp another local session's id and have its mail
   painted with that session's identity/color and filed on its board; `frm`/`frm_id` are also unsanitised
   into the maildir header block. Pre-existing, larger than the marker fix this branch made.
4. **The postal marker comment overclaims.** `event_model.py:51-53` says tool output echoing a marker
   used to render as a delivery, but `author_of` never saw tool output — the path that *does*
   (`kernel/kernel.py:9279`) still takes every id, not the trailing one, and still drops the tool row.
   Fix that path or downgrade the comment.
5. **Judge legacy transcript pile.** The scratch moved from `/tmp/romp-judge` to `$STATE/judge-scratch`,
   but nothing sweeps the old `~/.claude/projects/-tmp-romp-judge` dir — orphaned on every existing
   install, and `--purge` misses it. A one-time migration sweep belongs somewhere.
6. **Summarizer cwd guard** (`hooks/romp-summarize.sh`) is weaker than the judge's (no uid/symlink/mode
   check, swallowed chmod) and rests entirely on `--safe-mode`; and the summarizer still uses an
   unmarked `<turn>` boundary. Uninstaller `ROMP_JUDGE_SCRATCH` is dead code in the kernel (A3), and
   its slug-side guard can no longer fire (A4) — both low severity, both worth a look.

The VS Code self-update and the postal marker/trust fixes came back SHIP; their findings above are
pre-existing or in adjacent paths, not regressions in what shipped.

## Checks nobody can do offline

These need a real machine with a live kernel. None of them are covered by any test here.

- **Claude Code's project-dir encoding.** `bin/romp-uninstall` and `kernel/judge.py:_proj_dir` both
  assume "every non-alphanumeric → `-`, over the realpath". All copies agree with each other, but
  the ground truth is Claude Code itself, and this is what aims an `rm -rf`. One
  `ls ~/.claude/projects | grep judge-scratch` after a judge pass settles it. **Do this before
  merging.**
- **Judge verdict quality under the new prompt marks.** Judge system prompts now wrap untrusted
  transcript content in per-call random marks. Every offline test passes, but nothing confirms the
  judges still classify as well. Watch the first few captions and cards on a live kernel.
- **The `?c=` handoff round trip** against a real browser: minted by `bin/romp`, spent exactly once
  by the opened tab, cookie seeded, and the landing page's `/ws` then authorising on that cookie.
- **Tailnet/phone and VS Code webview auth** after the cookie/Origin change. The gate was traced by
  hand across every shipped client and holds on paper; only a real phone proves it.
- **macOS**: the bats suite under stock bash 3.2, where a mid-test assertion does not fail a test.
  CI runs Linux only; the macOS cells are `workflow_dispatch`-only because they bill ~10×.

## Waiting on the user, not on you

- **Upstream disclosure.** These are nine real vulnerabilities in the upstream project, and
  `SECURITY.md` asks for private GitHub Security Advisories. The user parked the decision until the
  fixes worked; they now do. Do not open an advisory or contact upstream without them saying so —
  `CLAUDE.md`'s fork rule makes anything upstream-facing their call alone.
- **Whether to merge PR #1 or keep reviewing.**

## Working here

- **No `gh` CLI.** Use the GitHub MCP tools (`mcp__github__*`).
- **`bats` is not installed.** Clone `bats-core` and run `bats-core/bin/bats tests/*.bats`.
- **`vscode-extension/node_modules` disappears.** Run `npm install` there before `npm test`; the
  suite dies on `Cannot find module 'esbuild'` otherwise.
- **One pre-existing pytest failure**, not yours to fix:
  `tests/test_kernel_nudge_last_resort.py::PlanSyncGate::test_an_unreadable_task_store_defers_rather_than_nudging`
  chmods a directory to 000, which does not deny root in a container.
- **Expected green**: ~3965 pytest, ~331 bats, 1663 extension, typecheck clean.
- **Enabling Actions on a fork takes two separate settings.** "Allow all actions" in Settings
  governs which actions may be *used*; a fork's own workflows stay unregistered until someone
  clicks the green button on the **Actions tab**. Enabling does not replay events, so an already-open
  PR needs a new push (or a close/reopen) before CI runs. Never use "Run workflow" from the Actions
  tab: that is `workflow_dispatch`, which expands the matrix to macOS at ~10× billing.

## The lesson worth carrying forward

Three separate times on this branch, a test written to guard a fix could not fail:

- a bats assertion built with the same shell substitution as the buggy code it checked;
- four `! grep` absence checks, exempt from `set -e`, asserting nothing;
- a gate test comparing source offsets against an anchor that appears three times, so it measured
  the wrong function's gate and passed with the route served unauthenticated.

The pattern is consistent. **Asserting on structure reproduces the implementation; asserting on
behaviour tests the requirement.** A source offset, a shell substitution, a dict shape — each of
those encoded how the code happened to be written, so it agreed with the bug.

So: after writing a test, **break the source and watch it fail**. Not as ceremony — every one of the
three was found that way, and two of them only because the expected failure did not arrive. If a
test cannot be made to fail, it is documentation, and it should not be counted as a guard.

The two review passes are worth repeating on new work, and worth running on a **different model**
than the one that wrote the code — the second pass caught two blockers in the commits that fixed the
first pass's blockers, including a path that deleted a user's own transcripts at exit 0.
