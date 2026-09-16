---
title: ui/CLAUDE.md's accent rule records the T301 exception beside T394: the rail's API-health dot wears the accent in its fine state
status: candidate
where: ui/CLAUDE.md (the accent-color section: the exception line after the T394 paragraph)
added: 2026-09-16
pr:
tier: docs
offered:
closed:
---
Upstream's T301 (romp-on/romp#1338, merged 2026-09-10; the user's decision, recorded in kernel/kernel.py's cell comment and the `.ah-dot[data-dot=fine]` rule of the served CSS) paints the rail's API-health dot `var(--accent)` when every connected kernel is fine, the blocked red for errors and the label gray for no traffic. Upstream's own ui/CLAUDE.md accent rule forbids the accent for status colors and names one exception, T394's command rows, added two days after T301 with no T301 line, so at 14f1548a9 the doc and the served CSS disagree. The fork adds the T301 exception line after the T394 paragraph in the stage 1 pull-in of 14f1548a9 (the Python and shell tests area's review round 1, item 6): a record of a decision upstream made, no code or pin changed (the fork's pre-merge never-the-accent rule for that dot and its pins retired at the merge, R1, with the cell). The offer is the same line on upstream's file; the T394 line stays byte for byte because ui/webview/bg-kinds.test.ts pins its text.
