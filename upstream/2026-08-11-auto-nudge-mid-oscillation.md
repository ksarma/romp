---
title: The auto-nudge status-checks goals mid-oscillation — a blocked-on-the-user card flipped to 'working' by an unblock gets nudged in the gap before the closer's next word
status: landed
where: fork PR #48
added: 2026-08-11
pr: 48
tier:
offered: their PR #333
closed: 2026-08-14
---
Upstream ships the same `_nudge_fire_list` and judges, so the same flap produces the same false status checks: a goal blocked on the USER's decision is unblocked by "new work filed" / "answered in passing" rulings that don't answer the block, the nudge reads the flip as a stall, and the closer re-files the same block minutes later. Five live fires in one weekend on the fork. Fix holds a goal whose newest judge row is an unblock WITH an earlier judge unblock on record (a goal's FIRST unblock stays nudgeable — that doctrine's own incident was a wrongly-gagged nudge, pinned in tests) until the closer's next word, loudly via the deferral record + backstop; `held` rows carry per-goal whys. Pure fix, no fork-specific content; tests rebuild the incident shapes synthetically. Review arc worth remembering: the maintainer first closed it for a writer-side fix (floor a re-block on the lift's evidence time), his own suite refuted that (`test_interrupt_lift_evidence_time` — an interrupt stamps the lift and the legitimate follow-up block at the SAME evidence time, so there is no writer-side signal), he reopened, then also retracted his adjacent-cycle discriminator tweak after checking it against the first-unblock doctrine test, and merged UNCHANGED. Fork copy verified code-identical (comment-attribution deltas only). Offer branch cleaned up.

Status detail (migrated from the table): **landed — merged upstream as their #333 (2026-08-14, as-is)**
