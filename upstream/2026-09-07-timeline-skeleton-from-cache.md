---
title: Perf B3: on a warm cycle `_push` projects the timeline's lane skeleton from the cached full build instead of building a second timeline, serializes it once per build and sends it once per rebuild; the view signature keys the fields a lane or chip reads (`context`, `fastReason`, `modelPending`, subagents, background-task ids, the stats of `usage.json`, the views, comments and watches files) in place of a dead `ctx` key
status: merged
where: fork PR #235 (`perf-b3`, merged 2026-09-06): `kernel/kernel.py` (the skeleton projection in `_push`, the view signature, an open interval's end at the build clock on the wire), `ui/romp-timeline-view.js` (an end within two seconds of the frame's clock is drawn open to the live edge); tests `tests/test_kernel_timeline_split.py` (`SkeletonFromCache`, `OpenIntervals`), `tests/test_bg_scan_fold.py`, `ui/timeline-open-interval.test.ts` (a headless draw)
added: 2026-09-07
pr: 235
tier: fix
offered: their PR #1060
closed: 2026-09-08
---
Upstream builds a second, lane-only timeline every pusher cycle (about 200 ms on a 31-session state copy) beside the cached full build and sends its 27 KB lanes frame to every timeline client every cycle; and its view signature keys a dead `ctx` field instead of `context`, so a context change never busted the cached build and the five-second bucket hid it. A rebuild still happens on every signature change, on `_mark_views_dirty` and at the five-second bucket, so a quiet timeline gets a clock sample at least every 5 s and an unchanged cycle sends nothing; a connect push stamps the cached lanes with the cycle clock so a fresh pane anchors its live edge on the present; the skeleton path loads a goal store only for a dead lane. Two visible changes for the read-through: compaction markers now appear on lanes (the per-cycle skeleton had always sent an empty list), and a lane chip can lag a rebuild by up to two seconds, as the floor bars already did. Measured offline against the same base: a steady pusher cycle 280 to 104 ms; a timeline connect push 190 to 16 ms; timeline bytes per unchanged cycle 27 KB to 0.

No `/perf` dependency. The wire encoding of an open interval is unchanged, so already-loaded dashboards keep drawing; a wire break for loaded renderers and a starved live edge were the two regressions the review caught in the first version of this change, and both are pinned.

OFFERED 2026-09-08: offered upstream inside bundle PR #1060 (Pusher: one build, one encode and one compare per change; the timeline's live tick translates the plot; label fix; branch pusher-timeline-offer; head 7da31ce9; a draft while the branch is rebased onto the moved upstream tip) with `view-delta-identity-short-circuit`, `tool-result-scan-no-dumps`, `one-encode-per-payload-per-build-on-the-pusher-thread-plan`, `tick-jobs-wake-memos-discover-once` and the timeline's live tick (P5) of `browser-round2-cuts`.

MERGED 2026-09-08: merged upstream as their PR #1060 (merge dd310bb9, 2026-09-08T15:37:14Z) after the maintainer's own review commit.
