// The one test-side home of the sentence beside "Print anyway", fixed here so a compare against it does not move with the
// product. ui/webview/file-print.ts anywayWords() is the product's copy. A test that held the rendered line to anywayWords()
// alone held both sides to one function, so a wording change reddened nothing (the round-7 review of the fork PR, cluster A,
// 2026-09-21: the round-7 fix had put that self-reference where a hand-spelled copy stood in the driver leg). The census
// module's text pin (file-print.test.ts) holds anywayWords() to this constant, and the driver leg's case (15b)
// (file-print-driver-browser.test.ts) holds the line it reads off the rendered pre-press DOM to it, at both of its reads,
// beside the case's reads of the print's boxes under print media and of the print stub; a wording change reds both modules.
// What the leg's compare proves is that the wording reaches the RENDERED pre-press DOM, the line the person reads before
// pressing. Nothing here proves the sentence is printed, because it is not: the sheets hide the line under print media
// (case (15a) measures a 0 by 0 box for it), so no read of the paper carries the sentence.
// Test-side only: no product module imports this file (the record test, tools/markdown-viewer-plan-print-record.test.mjs,
// derives the sentence from this file and holds the product module to it). Synthetic values only.
export const ANYWAY_SENTENCE = "Print anyway leaves out any picture still loading.";
