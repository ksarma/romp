---
title: Timeline: a live lane whose goal store faulted is derived, not served from the memo (a skip counted under complain_skip, keyed apart from the empty store)
status: merged
where: kernel/kernel.py (_lane_memo), tests/test_timeline_lane_memo.py (NotHeld, two tests)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1263
closed: 2026-09-10
---
Should-fix recorded in the review of their #1241 (our live-lane memo offer): a faulted store and an empty store shared the memo key while the derivation differs. Filed directly from the upstream base.
