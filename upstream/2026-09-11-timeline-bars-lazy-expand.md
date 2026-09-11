---
title: Timeline: a bars frame expands on its first read, not on arrival, and reuses the last expansion for unchanged bars
status: candidate
where: ui/romp-timeline-view.js (_bindBars, expandBarsMemo, expandJudgingMemo, reuseLane, sameWire), ui/timeline-bars-hidden-expand.test.ts, ui/webview/timeline-warming-loader.test.ts, tools/ui-bench.mjs (--hidden, --compare), tests/ui-bench.test.mjs, CONTRIBUTING.md
added: 2026-09-11
pr: 746
tier: fix
offered:
closed:
---
Since T278c the view expanded every compact wire bar and judging entry in _mergeBars, ahead of the paint hold that skips draw() while the pane is hidden, so a dashboard tab in the background paid the whole expansion for frames nobody saw (700 to 2200 ms of main-thread time per minute on a board of 33 sessions, against about 2 ms before T278c), and a visible tab paid it again for every lane a full frame repeated unchanged. The wire payload is now merged as received and data.turns and data.judging expand on their first read; the expansion reuses its previous result wherever the wire says the same thing. The bench gained a --hidden regime that measures the background-tab case.
