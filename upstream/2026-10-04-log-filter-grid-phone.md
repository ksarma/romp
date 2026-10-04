---
title: The Log's filter grid fits a phone: as many equal columns as fit at 96px, five at most
status: candidate
where: kernel/kernel.py (_landing: the #rerr-fgrid rule); tests/test_error_center.py (ErrorCenterWiring: the rule's source pin); tests/test_log_filter_grid_served.py (LogFilterGrid, new); tests/log_filter_grid_browser.mjs (its driver, new); upstream/2026-10-04-log-filter-grid-phone.md (this entry)
added: 2026-10-04
pr: 972
tier: fix
offered:
closed:
---
On a phone the Log's filter toggles ran past the panel and off the screen. The grid's columns were repeat(5,1fr): a 1fr track's minimum is its chips' min-content width and the chips never wrap, so the five columns stayed 341px (WebKit, Firefox) to 362px (Chromium) wide. In the phone's min(700px, 94vw) panel, in WebKit and Firefox, they ran past the filter bar's content edge below 414px of viewport, past the panel below 401px and off the screen below 388 to 389px; in Chromium below 435, 422 and 409px. At 390px the last column ended 22 to 43px past the filter bar, and at 320px three toggles could not be tapped at all. The columns are now repeat(auto-fill,minmax(max(96px,20% - 5px),1fr)): as many equal columns as fit at 96px (the entry rows' chip column) and never more than five, so the desktop keeps its five equal columns and a phone gets three from about 370px and two below. A served test measures every toggle at six phone widths and two desktop widths in Chromium, WebKit and Firefox; it is red before the change at every phone width in all three.

upstream/main (last updated 2026-09-24) has the same rule: its kernel/kernel.py styles #rerr-fgrid as repeat(5,1fr) in the same panel and filter bar, over 14 kinds (no frozen kind, and refused reads "not saved"), and its tests/test_error_center.py pins that text. By the chip widths measured here (its one label not measured here, "not saved", counted as no wider than "api error" in the same column) its five columns need at least 329px (WebKit) and 346px (Chromium) where a 390px phone leaves the grid 319px, so it overflows the same way (not run against that tree). The kernel change applies there as it is. The served test reads the kinds from the grid, so it needs no change for the 14, but it takes its port and readiness wait from tests/lab_ports.py and its bundles from tests/lab_dist.py, which upstream does not have yet (upstream/2026-10-02-tests-served-lab-ports.md), so an offer carries those calls in upstream's own form.
