// The Outline's fixture (plans/markdown-viewer.md Slice 6, item 2), shared by the node cases (file-view-outline.test.ts)
// and the browser leg (file-view-outline-browser.test.ts) the way real-viewer-leg.ts carries the place legs' report, so
// the two read one note: a synthetic notes-api report of forty-two headings at mixed depths, a paragraph after each so
// every viewport scrolls. The shapes the list has to handle: a front-matter block first (a folded details with no heading,
// so no row); an h1 title; h2 sections with h3s under some; two headings with the same text (the second's id is the slug
// plus -1); one holding inline code; one holding a formula (once the math fill has run, KaTeX's text is what the row
// shows); one inside an author's own <details>, closed (listed, and the pick opens the fold); one inside a blockquote.
// Test-only: no webview bundle imports it. Synthetic values only: an invented report, no real text.
export const FOLD_HEADING = "Inside the fold";
export const MATH_HEADING = "Ratio $x$";
export const CODE_HEADING = "Using `cache.get`";
export const QUOTED_HEADING = "Quoted finding";
/** The headings in document order, as [depth, text as written]; forty-two of them. The 40th (index 39) is "Detail 9.1". */
export const OUTLINE_HEADINGS: Array<[number, string]> = [
  [1, "Report"], [2, "Summary"], [3, "Scope"], [3, "Method"],
  [2, "Results"], [3, "Latency"], [3, "Throughput"], [3, "Errors"],
  [2, "Results"], [3, CODE_HEADING], [3, MATH_HEADING],
  [2, "Evidence"], [2, QUOTED_HEADING], [3, FOLD_HEADING],
  ...Array.from({ length: 9 }, (_, k) => [[2, `Section ${k + 1}`], [3, `Detail ${k + 1}.1`], [3, `Detail ${k + 1}.2`]] as Array<[number, string]>).flat(),
  [2, "Closing"],
];
const para = (i: number): string => `Paragraph ${i}: lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore.`;
/** The note: front matter, then every heading with a paragraph after it (the quoted heading inside a blockquote, the
 *  fold's heading inside a closed <details> with a summary), and a tail of twelve paragraphs after the last heading, so
 *  the 40th heading has more than a body's height of text under it at every viewport the legs open and can sit at the
 *  top (a heading with less below it than the body shows lands where the scroll clamps, as any `#` link would). */
export const OUTLINE_NOTE = (() => {
  const out: string[] = ["---", "title: Report", "tags: [latency]", "---", ""];
  OUTLINE_HEADINGS.forEach(([depth, text], i) => {
    const line = "#".repeat(depth) + " " + text;
    if (text === QUOTED_HEADING) out.push("> " + line, "", para(i + 1), "");
    else if (text === FOLD_HEADING) out.push("<details>", "<summary>Fold</summary>", "", line, "", para(i + 1), "", "</details>", "");
    else out.push(line, "", para(i + 1), "");
  });
  for (let i = 0; i < 12; i++) out.push(para(OUTLINE_HEADINGS.length + i + 1), "");
  return out.join("\n");
})();
/** A note with `n` headings and nothing else worth reading between them, for the cost measurement. */
export const manyHeadings = (n: number): string => "# Report\n\n" + Array.from({ length: n - 1 }, (_, i) => `## Section ${i + 1}\n\n${para(i + 1)}\n`).join("\n");
