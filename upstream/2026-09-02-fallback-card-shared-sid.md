---
title: `tests/test_model_fallback_card.py` `FallbackCard` mints its card under the SHARED placeholder sid, so another module's leftover override journal (replayed by `load_goals` on every load; node ids collide at `<sid>:g1`) can reopen the minted card mid-test — green alone, red only under whole-suite ordering; a parallel (xdist) run surfaced it
status: merged
where: the fold merge (`upfold0902`): the class takes a private synthetic sid and unlinks its journal in tearDown, exactly the shape the file's own `DedupeBackstop` already uses (reproduced red-first with a planted journaled follow-up, green after)
added: 2026-09-02
pr:
tier:
offered: their PR #881
closed: 2026-09-02
---
MERGED as-is (head is an ancestor). Branch retired. OFFERED 2026-09-02 (branch `fallback-sid`, `ea4cc4b4` off tip `70a36077`, test-only): the review REFUTED the port’s "why CI is green today" story (earlier tearDowns do NOT wipe the shared journal; the collision is live in serial order and the assertions held only because none of the leftover ops touches g1) — docstring, commit message and PR body rewritten to the measured facts before posting; scaffold CI green (since-closed fork #153). The file is byte-identical upstream, so the flake exists there too. Test-only, two-line fix plus a docstring.

Status detail (migrated from the table): ✅ **merged** — their PR #881, merged as-is 2026-09-02 — ✅ came home in upfold0905 (2026-09-05)
