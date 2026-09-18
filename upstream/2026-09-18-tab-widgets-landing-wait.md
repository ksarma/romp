---
title: The tab widgets lab waits for a landing at the new viewport height
status: candidate
where: tests/test_tab_widgets_browser.py, the driver tall scene: a MutationObserver journals the viewport height at each landing mark and the resize scenes wait for a landing at their height
added: 2026-09-18
pr:
tier: docs
offered:
closed:
---
Upstream's test waited for the landing mark's mere presence after a resize, but a re-ask writes the mark twice (synchronously, then one frame later from the ask's observer's first observation) and a resize's landing runs one frame after the browser clamps the scroll, so a mark cleared between them can stand again before the resize is issued and the read that follows sees the clamped card with the smaller window's room (303 px off in the taller scene). The fix is test-side only: a MutationObserver journals the viewport height at each write of the mark and the two resize scenes wait for a landing at their own height (900, then 1400); the landing code in gear.js is unchanged. The fork's CI hit the race once on 2026-09-18 during the catch-up fold; the race is in upstream's tree too (same test text, same observer), and the offer waits on the user's word under the standing no-new-upstreaming rule.
