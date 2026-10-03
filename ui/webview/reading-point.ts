// The reader's line in the chat, kept across a change that reshapes the text above it INSIDE the turn they are reading (the
// review of iOS item 6, 2026-10-02). The chat keeps a scrolled-up reader's place by the first turn still visible at the
// viewport top (render.ts captureScrollAnchor and restoreScrollAnchor: that turn's top goes back to its offset), which holds
// while the change happens in an EARLIER turn. The math renderer's arrival lays out every formula waiting for it in place
// (math.ts), and a reply's formulas usually sit in the same turn the reader is partway down: the turn's top stayed put while
// its formulas grew, so the text being read slid down by their growth (about 133 px on a phone for a reply with eight short
// display formulas, in either engine, with the browser's own scroll anchoring on or off). The point here is finer: the first
// line of text at the viewport top that no formula owns, named by the markdown block that holds it and the offset of the
// line's first character in that block's text, with the line's offset from the viewport top.
//
// The name is portable on purpose. A formula's text is left out of every count in each form it takes (waiting: the
// placeholder holding its TeX; laid out: KaTeX's root; refused: the source fallback, a code element, in a pre of its own for a
// display formula), and the blocks counted are the markdown's own, never a formula's, so one point names one character
// before and after the swap and across a page reload, where the record is taken over laid-out formulas and landed over
// waiting ones (render.ts persistScrollForReload and landActive's reload restore). A comment mark splits a text node and adds
// no text, so it moves no offset. A subtree wholly above the viewport top is passed over by one rect read, and a sticky or
// fixed one is never the anchor, since it does not move with the text. Synthetic DOM in reading-point-browser.test.ts holds
// each of these in Chromium; tests/test_math_chunk_served.py holds the chat's use of it in both engines.

/** A reader's line: `block` is the index of the markdown block holding it among the turn's blocks (BLOCKS, formulas left out),
 *  or -1 for text in no such block; `char` the offset of the line's first character in that block's text, formula text left
 *  out; `y` the line's top less the scroller's top, in CSS pixels, when the point was taken. */
export type ReadingPoint = { block: number; char: number; y: number };

/** Formula text in each of its forms (math.ts): the waiting placeholders, KaTeX's roots (a display formula's .katex-display
 *  holds a .katex) and its error span, and the source fallback's code element. */
const FORMULA = ".md-math-inline, .md-math-display, .katex, .katex-display, .katex-error, code.md-math-src";
/** The markdown blocks a point is named by. */
const BLOCKS = "p, li, pre, blockquote, h1, h2, h3, h4, h5, h6, td, th, dt, dd, summary, figcaption";

/** A formula's element: one of FORMULA, or the pre a display formula's source fallback stands in (math.ts showSource). */
function isFormula(el: Element): boolean {
  if (el.matches(FORMULA)) return true;
  return el.localName === "pre" && el.childElementCount === 1 && el.firstElementChild!.matches("code.md-math-src");
}

/** The turn's markdown blocks in document order, formulas' own left out: the list `block` indexes. */
function blocksOf(turn: Element): Element[] {
  return Array.from(turn.querySelectorAll(BLOCKS)).filter((b) => !isFormula(b));
}

/** The text nodes under `scope` outside every formula, in document order; `pass` rejects a subtree the caller has no use for. */
function textWalker(scope: Element, pass?: (el: Element) => boolean): TreeWalker {
  return scope.ownerDocument.createTreeWalker(scope, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => n.nodeType === Node.TEXT_NODE ? NodeFilter.FILTER_ACCEPT
      : isFormula(n as Element) || (pass ? pass(n as Element) : false) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_SKIP,
  });
}

/** The top of the first box of the character at `at` in `t`, or of the next of the following few that has one (a collapsed
 *  space has none); with `below`, only a box whose bottom is past it counts. Null when none has. */
function charTop(range: Range, t: Text, at: number, below: number | null): number | null {
  for (let i = at; i < Math.min(t.data.length, at + 8); i++) {
    range.setStart(t, i); range.setEnd(t, i + 1);
    for (const r of Array.from(range.getClientRects())) if (r.height > 0 && (below === null || r.bottom > below)) return r.top;
  }
  return null;
}

/** The reader's line in `turn`: the first line of text outside every formula whose box reaches below the scroller's top, or null
 *  when the turn shows none (its visible part is formulas, or nothing with text). */
export function captureReadingPoint(scroller: Element, turn: Element): ReadingPoint | null {
  const top = scroller.getBoundingClientRect().top;
  const edge = top + 1;                         // the viewport top as captureScrollAnchor reads it: a box must reach past it
  const range = turn.ownerDocument.createRange();
  const reaches = (): boolean => Array.from(range.getClientRects()).some((r) => r.height > 0 && r.bottom > edge);
  const view = turn.ownerDocument.defaultView;
  // a subtree to pass over: wholly above the viewport top (one rect read), not displayed, or not moving with the text
  const pass = (el: Element): boolean => {
    const r = el.getBoundingClientRect();
    const boxed = r.width > 0 || r.height > 0;
    if (boxed && r.bottom <= edge) return true;
    const cs = view ? view.getComputedStyle(el) : null;
    if (!cs) return false;
    if (!boxed && cs.display === "none") return true;
    return cs.position === "sticky" || cs.position === "fixed";
  };
  const w = textWalker(turn, pass);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    const t = n as Text;
    if (!t.data.trim()) continue;
    range.selectNodeContents(t);
    if (!reaches()) continue;
    // the first character whose box reaches below the top, by halving: the prefix [0, lo) does not reach, [0, hi) does
    let lo = 0, hi = t.data.length;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      range.setStart(t, 0); range.setEnd(t, mid);
      if (reaches()) hi = mid; else lo = mid;
    }
    const lineTop = charTop(range, t, lo, edge);
    if (lineTop === null) continue;
    let b: Element | null = t.parentElement;
    while (b && b !== turn && !(b.matches(BLOCKS) && !isFormula(b))) b = b.parentElement;
    const scope = b && b !== turn ? b : turn;
    const block = scope === turn ? -1 : blocksOf(turn).indexOf(scope);
    if (block < 0 && scope !== turn) return null;
    let char = lo;
    const all = textWalker(scope);
    for (let m = all.nextNode(); m && m !== t; m = all.nextNode()) char += (m as Text).data.length;
    return { block, char, y: lineTop - top };
  }
  return null;
}

/** How far the point's line has moved since it was taken, in CSS pixels (positive: down), or null when the turn no longer
 *  holds it (no such block, an offset past the block's text, a character with no box) or the point is malformed (a record
 *  read back from storage). Scrolling the scroller by the result puts the line back where it was. */
export function readingPointShift(scroller: Element, turn: Element, p: ReadingPoint): number | null {
  if (!p || !Number.isInteger(p.block) || p.block < -1 || !Number.isInteger(p.char) || p.char < 0 || !Number.isFinite(p.y)) return null;
  const scope = p.block < 0 ? turn : blocksOf(turn)[p.block];
  if (!scope) return null;
  const range = turn.ownerDocument.createRange();
  let left = p.char;
  const w = textWalker(scope);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    const t = n as Text;
    if (left < t.data.length) {
      const lineTop = charTop(range, t, left, null);
      return lineTop === null ? null : lineTop - scroller.getBoundingClientRect().top - p.y;
    }
    left -= t.data.length;
  }
  return null;
}
