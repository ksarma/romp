---
title: The ui-bench replay asserts each delivery was measured, not that it took time (a hidden page's 0.0 ms reading)
status: candidate
where: tests/ui-bench.test.mjs (the replay loop's bundle percentiles and first-frame delivery claims, the FROZEN_DELIVERY_CLOCK entry, the buildReport zero-reading pin), tools/ui-bench.mjs (replay's pageInit option)
added: 2026-09-19
pr:
tier: docs
offered:
closed:
---
Fork CI 2026-09-19: the hidden timeline replay's data row read p50 0.0 in 4 of 131 runs and the strict p50 > 0 went red. The bundle column is a performance.now() difference rounded to 0.1 ms; under the paint hold the timeline view buffers a whole-state frame and returns before draw(), so a skeleton re-push's delivery is a merge of about 0.1 ms, and Chromium's performance.now() moves in 0.1 ms steps in this non-isolated context, so the reading is 0.1 or 0.0 by clock phase. The property is that every delivery was measured: the count (bundleMs.n equals delivered; an untaken or negative reading drops out of n) is the witness, the percentiles are its shape, and a visible page must show at least one delivery above 0 (its deliveries render inside the bracket). The project's copy carries the same two strict claims on visible pages, where they have not fired; the hidden entry is fork-only. A fourth replay entry holds the page's clock still across every delivery (replay's new pageInit option installs the stub after the instrument), so every reading is 0.0 on each run, with its own pin that the stub took effect (every delivered type's p50 and max exactly 0, the first frame's delivery 0 when it went alone), and a buildReport unit test pins that a 0 reading counts while -1 and a negative one do not. The one strict `> 0` timing claim left in the file is the first frame's handlerMs (0.2 to 0.4 ms in 12 of 12 probe runs, two clock steps above the floor), named as such beside the assertion. Tests and the bench tool only.
