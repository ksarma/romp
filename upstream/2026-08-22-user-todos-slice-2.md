---
title: User todos slice 2 — ambient visibility and the endgame: build_feed's sid-keyed open-count map + quiet card marker, the ⚑ tab glyph, the badge widened to "things only the user can move" (with per-item decision classes: quarantine and parked handoffs count per card), the idle-escalation floor + goal-less placeholder (peer-wait gate, confirming skip, working-top fallback, floor-push latch), and the status-nudge stand-down scoped so the awaiting wake and debt machinery flow past
status: keep-private
where: fork branch `usertodos` (commits `5bee4179` / `13d74533` / `c0282461`)
added: 2026-08-22
pr:
tier: major-feature
offered: their PR #994
closed: 2026-09-20
---
(the user 2026-09-06: one of two example major features to offer in future) Same systems upstream: `_auto_nudge_tick`, `_needs_you_count`, `_wait_for_graph`, build_feed's perm-floor family, the feed/tab webview. Depends on slice 1; the floor/badge/nudge pieces are meaningless without the store.

Status detail (migrated from the table): candidate — **major-feature (tier 3)**, discuss with the maintainer first

APPROVED 2026-09-07 as an RFC: the fork owner approved offering the user-todos slices upstream as an RFC rather than a straight code PR — with docs and demo captures (headless captures over synthetic notes-api content only). Tier 3 stays: discuss with the maintainer first; the three slices travel as one conversation.

OFFERED 2026-09-07: all three slices ride one RFC, their draft PR #994 (label major-feature, head a408815d; discussion issue #993), with the per-install switch off by default, docs and twelve synthetic captures, and the fork #325 withdraw fix folded; under #991's policy it merges on the other maintainer's approval plus a non-author comment on #993.

2026-09-07: #994 head is now b8a906f3 (38 commits; a review fold added 23 commits; CI scaffold fork PR #356).

**Closed with their PR #994 on 2026-09-20, and kept fork-side (the user 2026-09-21, who decided the
feature stays with us for now).** The project closed #994 as a DIRECTION call rather than on any defect:
the maintainer's own design for the same need merged upstream overnight, adopts no store, and widens the
approval box the project already ships. So this is not declined by us and it is not a defect to fix; the
road is simply not the project's. The fork already runs the feature. Status is `keep-private` rather than
`declined` because we hold and maintain it, and the user is taking the direction question to the
maintainer himself. Standing design note for future work on this surface: encapsulate it as much as
possible, preferring fork-only modules and single call sites, because the fold runs twice a week and
every line shared with upstream is a recurring conflict cost.
