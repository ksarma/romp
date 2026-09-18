---
title: The unfocused-pane lab tells its kernel the vanished session is gone
status: approved
where: tests/test_unfocused_pane_browser.py, the driver: the vanished session's registry row goes dead after the synthetic teardown and the driver waits for the kernel's own strip without it before the other session appears; the row goes live again behind the re-listing strip
added: 2026-09-18
pr:
tier: docs
offered:
closed:
---
The test's host drop was the page's alone: the lab kernel kept listing the vanished session live, so any push of its own could carry that session's frame, and the pane then re-appended the tab and ran T357's restore (render.ts, the vanishedId arm on a session frame). The push that did it was the answer to the page's idle prefetch for the skeleton tab the test injects (needFull, a full push whose session frames went out whenever their bytes had moved since the connect push), so the assertion that a different session appearing does not take focus failed 1 run in 3 on CI and on an idle box, dev and production bundles alike. The fix is test-side only: the driver flips the session's registry row to alive false after the synthetic teardown (the field the backend's kill flips) and waits for the kernel's own strip without the session, the event after which no kernel push can carry it; the row goes live again right behind the re-listing strip, whose skeleton-click ask is answered with the session's full frame either way. No product code changes. Five of five green here after the change; the race is in upstream's copy of the test too.

2026-09-18: approved for offer by the user (batch 7 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded).
