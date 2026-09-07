// The PDF pages' size cap and its refusal, PURE (plans/file-review.md Slice 4; contract F3) — the two facts
// file-view.ts needs before the pdf.js chunk exists on the page, kept out of file-view.ts so a test can run
// them with no DOM stand-in (pdf-lazy.test.ts pins them equal to the chunk's own DEFAULT_MAX_BYTES and
// capMessage). Nothing here touches the document, and nothing here imports the chunk: the main bundles stay
// byte-stable, and a 40 MB PDF is refused before a megabyte of renderer is fetched.

/** The largest PDF whose pages the viewer renders itself: the chunk's own default (pdf-chunk.ts
 *  DEFAULT_MAX_BYTES). Over it, the browser's frame shows with the reason. */
export const PDF_MAX_BYTES = 25 * 1024 * 1024;

/** The cap refusal, in the chunk's own words (its capMessage, one decimal of MB): the size AND the cap, so the
 *  person knows how far over the file is. */
export function pdfCapMessage(size: number, cap: number): string {
  const mb = (n: number) => (n / (1024 * 1024)).toFixed(1) + " MB";
  return `this PDF is ${mb(size)}, over the ${mb(cap)} cap for rendering pages in the viewer`;
}
