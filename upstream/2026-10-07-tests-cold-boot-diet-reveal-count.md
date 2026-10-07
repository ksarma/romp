---
title: test_cold_boot_diet_browser counts the skeletons the filter's reveal leaves in the reveal's own hashchange dispatch, so an idle prefetch cannot fill one before the count
status: candidate
where: tests/test_cold_boot_diet_browser.py (ColdBootDiet.test_the_visible_skeletons_fill_on_later_idle_callbacks_and_hidden_tabs_wait_for_the_filter_to_show_them: the driver's reveal and count in one evaluate, through its own hashchange listener); upstream/2026-10-07-tests-cold-boot-diet-reveal-count.md
added: 2026-10-07
pr: 998
tier: docs
offered:
closed:
---
The test cleared the #only filter in one browser evaluate and counted the revealed skeletons in a second one. Clearing the filter fires the page's hashchange listener, whose repaint re-arms the idle prefetch for the revealed tabs, so under load the prefetch's request and the kernel's full frame could fill one revealed skeleton before the second evaluate counted, and the test failed with 17 != 18 (about 1 run in 60 under load on the fork's box). The driver now adds its own hashchange listener and clears the hash inside one evaluate; the page's listener, bound at load, repaints first, and the driver's reads the counts in the same dispatch, before any idle callback or websocket frame can run. A new assertion on the tab count at the reveal fails if the read ever comes before the repaint. The test only; no product change.

The race is in the project's public tree (upstream/main, last updated 2026-09-24): its copy of the test has the same two evaluates, the reveal and then the skeleton count in a second one, and its ui/webview/render.ts re-arms the idle prefetch inside renderTabs when a reveal shows tabs (the hashchange listener calls renderTabs), so the same failure can occur there. The fork's copy of the test differs from upstream's elsewhere, so the change would be offered as the same edit to the driver's reveal and count, not as a byte-identical file.
