# Upstream candidates

Things on this fork we may want to offer to the upstream romp project. This is a QUEUE for
decisions, not a promise: per `CLAUDE.md`'s fork rule, nothing goes upstream — no PR, no issue, no
advisory — until the user says so, per change. Each candidate is one file under `upstream/`; add one
when you land something upstream-worthy, and the user prunes or promotes it by editing its status.

A good candidate fixes or improves something upstream has too. Fork-specific infrastructure (the
private-strings hooks, fork-remotes guard, this ledger) never qualifies.

## Adding an entry

Run `scripts/upstream-ledger.py new <slug> --title '...' --where '...' [--pr N] [--tier fix]`, fill in
the body, and commit the file with the change. Never edit this file per change: it holds no table,
so two unrelated PRs cannot conflict on the ledger (the test refuses a table row here). Writing the
file by hand is equally valid. An entry is `upstream/<YYYY-MM-DD>-<slug>.md`, dated the day it was
added, with a header of `key: value` lines between `---` lines and a Markdown body whose first
paragraph is the rendered Notes cell:

    ---
    title: Kernel performance counters and `romp perf`
    status: candidate
    where: fork PR #199 (`romp-perf`): `kernel/kernel.py` (`_PerfStats`), `bin/romp` (`perf`)
    added: 2026-09-06
    pr: 199
    tier: feature
    offered:
    closed:
    ---
    Why upstream wants it, in one paragraph.

Required: `title`, `status`, `where`, `added` (the filename's date). Optional: `pr` (fork PR
number), `tier` (`fix`, `tests-only`, `feature`, `major-feature`), `offered` (the upstream PR once
one is open), `closed` (the date a terminal status was set), `supersedes` (another entry's
filename). Anything else fails the test. Whoever acts on an entry appends a dated line to its body.

## Status

Status meanings: **candidate** (worth offering, decision not yet made) · **waiting** (candidate,
but gated on something first) · **approved** (the user has said to offer it; the upstream session
reads this as its signal) · **offered** (a PR is open upstream) · **merged** (landed upstream via
our PR) · **landed** (upstream took it, possibly rebuilt clean) · **resolved-upstream** (they fixed
it independently) · **declined** · **keep-private** · **divergence** (the fork deliberately
differs from upstream here; not for offering as-is) · **follow-up** (a fold left work pending).

Pruning is `declined` or `keep-private` (or deleting the file); promoting is `approved`. Change a
status with `scripts/upstream-ledger.py set <slug> status <value>` or by editing the one line.

## Reading the ledger

- `scripts/upstream-ledger.py render` prints the table: open entries first (`approved`, then
  `candidate` newest first, `waiting`, `follow-up`, `offered`), a short divergence and
  keep-private table, then the closed entries collapsed. `--active` prints the open table only.
- The Ledger workflow renders the same table into its job summary on every push to `main`, so the
  latest Ledger run on the Actions tab always shows `main`'s ledger.
- `scripts/upstream-ledger.py list --status approved` prints one JSON object per entry, which is
  what the upstream session reads before opening an offer.
- `scripts/upstream-ledger.py check` runs every rule the guard test (`tests/test_upstream_ledger.py`)
  runs.

## Offering

When offering: work from a branch cut off the upstream default, carrying only that change —
never a fork branch with fork-only commits tangled in. Record the offer on the entry (`set <slug>
status offered`, `set <slug> offered 'their PR #N'`) and, when it lands, `merged` plus `closed`.

Security items ship as ordinary per-chain PRs, not private advisories (the user's call, 2026-08-14):
the fork is public, so the findings are already discoverable in its history, and upstream has no
private-reporting intake. See the security audit entry (`upstream/2026-08-14-security-audit-chains.md`)
and `~/romp-handoffs/security-session.md`. Still do NOT enumerate an upstream-unfixed hole anywhere
public beyond the PR that fixes it.
