---
title: A pane divider drag moves a landing line and the panes take their widths once, at release
status: offered
where: upstream branch gutter-ghost-offer, re-derived from fork PR #420 (M3 only): `kernel/kernel.py` _LANDING_JS gutter() and the #gv-ghost element and rule; tests `tests/test_pane_gutter_drag.py` (a node-stub driver executing the served JS, six scenarios) and `tests/test_kernel_pane_rail.py`
added: 2026-09-09
pr:
tier: feature
offered: their PR #1220
closed:
---
Audit row 8 (the divider-drag mitigation of the Files pane freeze). Every pointer step wrote both panes' flex-grow variables and re-laid out every pane document; the drag now moves a fixed landing line and writes the pair once at release. Feature tier because the drag behaviour is visible; the body names the contributor's open #1126, which asserts the old behaviour in its test. M1, M2 and M4 ride other candidates; fork #428 is inside their #1057.
