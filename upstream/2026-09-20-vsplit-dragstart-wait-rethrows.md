---
title: The vertical-split drag lab's 15 s dragstart wait rethrows a non-TimeoutError
status: candidate
where: tests/test_chat_vsplit_served.py (the pointer driver's dragstart wait: the waitForFunction on window.__vsplitDragStarted with the 15000 ms timeout and its catch); upstream/2026-09-20-vsplit-dragstart-wait-rethrows.md (this entry)
added: 2026-09-20
pr:
tier: docs
offered:
closed:
---
Upstream PR 1832's dragstart wait in tests/test_chat_vsplit_served.py catches every rejection of the 15 s waitForFunction as false, so a page, context or browser closure during the wait is reported as the drag threshold not crossed under load, the wrong cause (the same file's earlier tab wait and its later zone wait rethrow a non-TimeoutError). The fork carries the one-line divergence on upstream's test: the catch rethrows anything that is not a TimeoutError and returns false only on the timeout, so a closed page or browser keeps its own error text. The offer waits on the offers pipeline; tests only.
