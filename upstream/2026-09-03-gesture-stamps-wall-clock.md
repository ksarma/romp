---
title: Gesture stamps order by device WALL CLOCK: a laptop ten minutes ahead picks X and every pick from a correctly-clocked phone is refused for ten minutes with copy asserting another device changed it — no gesture can win
status: offered
where: maintainer’s follow-up on their #879 (2026-09-03); not yet built
added: 2026-09-03
pr:
tier: fix
offered: their PR #945
closed:
---
His proposed shape keeps the design: stamp gestures as `max(Date.now(), lastSeenGt + 1)` (the gear already fetches /version on open and could learn each store’s current gt), add an explicit "apply anyway" action on the settingStale toast (a new user gesture is legitimate new information), and toast copy that does not claim another device acted when the kernel cannot know that. Event-over-clock doctrine.

Status detail (migrated from the table): **offered** — their PR #945 (2026-09-06), label `fix`; combined with the other #879 follow-up row into one PR
