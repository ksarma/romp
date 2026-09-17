---
title: The tab-drag lab's rebuild detector leaves the row hairlines out of its count, so a three-row strip's dragover tick no longer reads as a rebuild
status: candidate
where: tests/test_tab_drag_reorder_browser.py: the MutationObserver in the driver's init script (lines 128-129 at the catch-up fold's merge 2def2572f)
added: 2026-09-17
pr:
tier: docs
offered:
closed:
---
Upstream's 958be6d03 (pull 1792) gave the lab a second tag group, so the strip has three rows and the painter lays two hairlines. The #tabs dragover handler moves the dragged tab and then re-lays the hairlines in one task (render.ts insertBefore, then paintTabRowLines), so one observer delivery removes 1 + 2 = 3 nodes and the detector's threshold (more than two removals) logs a rebuild on every moving tick; test_a_drag_survives_a_kernel_push_that_lands_mid_drag then fails on rebuiltMidDrag with the hold itself working (the push's render lands after dragend, the drop under the cursor). The two-row fixture kept the count at two. The re-pin filters .tab-row-line out of the removed count; the wholesale rebuild after dragend still reads 27. Upstream CI installs no browser, so its copy of the lab cannot show it there. Found by the 2026-09-17 catch-up fold's sweep; the offer waits on the no-new-upstreaming hold, the ledger being the queue.
