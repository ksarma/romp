---
title: The vertical-split drag test waits for the timeline band to settle before it measures
status: candidate
where: tests/test_chat_vsplit_served.py (the pointer driver: the settled() wait on the band, test_0 pane-rect hold, VSplitDragLateTimeline)
added: 2026-09-18
pr:
tier: docs
offered:
closed:
---
Upstream copy has the same race: the timeline band collapses from its 250 px loader to two lanes when the bars land, the shell auto-fits the band, and a drag begun before that measures a drop zone the collapse moves (533 to 686 px pane). The driver now waits for the band settle event and names the step and the measured heights when it times out. Tests only.
