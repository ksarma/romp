---
title: Timeline: the live edge glides in 0.15 px moves (TICK_MIN_PX), the loop waking only when there is a move to make (_tickWaitMs); the per-look visibility check reads the observer's word, and the hover re-arms once per whole pixel
status: merged
where: ui/romp-timeline-view.js (_tickLive, _tickWaitMs, _tabHidden, the observer callback), ui/timeline-transform-tick.test.ts, ui/timeline-live-tick.test.ts
added: 2026-09-10
pr:
tier: feature
offered: their PR #1244
closed: 2026-09-10
---
Features audit row (gated on a headless measurement of the per-frame layout read and the hover hit test upstream's b0533177 paced away; both costs removed, figures in the body). The shape differs from the fork's four lines: the look sleeps TICK_MIN_PX's worth rather than running every frame; after a merge the fold takes the merged shape.
