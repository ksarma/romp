// The reader's place across a paint of the file viewer's body (plans/markdown-viewer.md, Slice 2: "reader keeps
// their place"). A paint that REPLACES the body's children (a Rendered/Raw switch, a reload after a session's write)
// leaves the numeric scrollTop standing over new content, so the passage under the reader's eye changes: on the audit's
// note a reload that inserted twenty paragraphs above moved the top passage from 40 to 28, and the Rendered/Raw round
// trip drifted 648 to 918px (the Raw view is taller). A reflow that keeps the children (the pane dragged, the Comments
// aside opening or closing, a text-size step) moves the passage the same way: closing the aside at 900px took the top
// paragraph from 40 to 73. So the place is kept in the file's own terms: the SOURCE SPAN of the top-visible block (the
// first top-level block of the Rendered view whose box ends below the body's top edge; the first row of the Raw view
// that does) and how far its top edge sits from the body's top (negative when the reader is partway into it). After
// the paint the block for that span is found in the new view, whichever view it is, and the body is scrolled so it
// sits at the same distance. Across a reload the span is followed through the edit first (followPassage, the
// composer's own follow): a block after the inserted paragraphs shifts by their length, one before them keeps its
// offset, and one the write rewrote is placed by the block before it, followed the same way, so the reader lands on
// what replaced it; only when that block is gone too does the place fall to where the edit begins.
//
// The two views meet through the anchor map's tables (anchor-map.ts): a Rendered block's span comes from
// renderedBlockSpan and the block for a span from renderedBlockAt, which takes the block whose start is the largest
// at or below the offset (so an offset inside a paragraph, or one whose block was edited away, still lands); a Raw
// row's span from rawRowSpan and the row for an offset from rawRowForOffset. A refused block (a table, a code block,
// an HTML block) answers both: the place needs an element to measure, not text to quote. So a place read in Rendered
// seats in Raw at the block's first line, and one read in Raw seats in Rendered at the block holding the line.
//
// Written over the DOM the viewer builds and nothing else (querySelector, childNodes, getBoundingClientRect,
// scrollTop), so a stand-in with no layout (every box at 0,0) reads no place and seats nothing, and the node tests
// over the viewer run unchanged; the browser leg (file-view-place-browser.test.ts) measures the real thing.
import { followPassage } from "./file-comments";
import { renderedBlockSpan, renderedBlockAt, rawRowForOffset, rawRowSpan, type SourceRange } from "./anchor-map";

/** Where the reader is: the file text the view was painted from, the source span of the top-visible block (or Raw
 *  row) in it, that block's top edge measured from the body's top edge, and the span of the block (or non-empty row)
 *  before it, the fallback when the write rewrote the block itself. */
export type Place = { source: string; start: number; end: number; top: number; prev: SourceRange | null };

/** The index of the first of `count` boxes, stacked top to bottom, whose bottom edge lies below `edge`; `count` when
 *  none does. A binary search over the boxes' bottoms, which increase down a column of blocks (a Rendered view's
 *  top-level blocks, a Raw view's rows), so a long document costs a handful of box reads per scroll frame, not one per
 *  block. The one box the order need not hold for is a floated or positioned figure that reaches below the blocks
 *  after it (the paragraphs wrapping beside an `<img align="left">`), so the LOOKBACK boxes before the hit are read
 *  too and the earliest still showing wins; a figure with more wrapped paragraphs than that beside it is passed over
 *  for the first of them, a place as good to keep. A box with no layout at all (a hidden element: every edge 0) reads
 *  as above the edge. */
export const LOOKBACK = 8;
export function topVisibleIndex(count: number, bottomOf: (i: number) => number, edge: number): number {
  let lo = 0, hi = count;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (bottomOf(mid) > edge) hi = mid; else lo = mid + 1;
  }
  for (let i = lo - 1, k = 0; i >= 0 && k < LOOKBACK; i--, k++) if (bottomOf(i) > edge) lo = i;
  return lo;
}

const elementsOf = (n: Node): Element[] => Array.from(n.childNodes).filter((c) => c.nodeType === 1) as Element[];
const hasBox = (n: unknown): n is Element => !!n && typeof (n as Element).getBoundingClientRect === "function";

/** The reader's place in `body` as it stands: the top-visible block of the Rendered view (`.fileview-md`'s children)
 *  or row of the Raw view (`code.hljs .fv-cl`), read against `source`, the text that view was painted from. null
 *  when the body shows neither, when nothing is in view (a stand-in with no layout), or when no block at or below
 *  the top edge has a span (whitespace between blocks, an HTML block's leftover node: the next block is read). */
export function readPlace(body: HTMLElement, source: string): Place | null {
  if (!hasBox(body)) return null;
  const edge = body.getBoundingClientRect().top;
  const md = body.querySelector(".fileview-md");
  if (md) {
    const kids = elementsOf(md).filter(hasBox);
    const spanOf = (k: number) => renderedBlockSpan(md, source, kids[k]);
    for (let i = topVisibleIndex(kids.length, (k) => kids[k].getBoundingClientRect().bottom, edge + 0.5); i < kids.length; i++) {
      const span = spanOf(i);
      if (span) return { source, start: span.start, end: span.end, top: kids[i].getBoundingClientRect().top - edge, prev: before(i, spanOf, (sp) => sp.start < span.start) };
    }
    return null;
  }
  const code = body.querySelector("code.hljs");
  if (!code) return null;
  const rows = (Array.from(code.querySelectorAll(".fv-cl")) as Element[]).filter(hasBox);
  const spanOf = (k: number) => rawRowSpan(code, source, rows[k]);
  for (let i = topVisibleIndex(rows.length, (k) => rows[k].getBoundingClientRect().bottom, edge + 0.5); i < rows.length; i++) {
    const span = spanOf(i);
    if (span) return { source, start: span.start, end: span.end, top: rows[i].getBoundingClientRect().top - edge, prev: before(i, spanOf, (sp) => sp.end > sp.start) };
  }
  return null;
}
/** The span of the nearest box before index `i` that has one and passes `ok` (a block starting earlier; a Raw row with
 *  text, since a blank line's empty span cannot be followed). */
function before(i: number, spanOf: (k: number) => SourceRange | null, ok: (sp: SourceRange) => boolean): SourceRange | null {
  for (let k = i - 1; k >= 0; k--) { const sp = spanOf(k); if (sp && ok(sp)) return sp; }
  return null;
}

/** Where the kept block stands in `newText`: `at`, an offset inside it, or, with `next`, inside the block BEFORE it (the
 *  kept block is the one after that). Its own offset when the text is unchanged; followed through the edit otherwise
 *  (followPassage: unchanged before the edit, shifted by the edit's length after it, re-found when the block's text
 *  moved whole). A block the edit rewrote, or one whose text recurs so that no copy is its own, is placed by the block
 *  before it, followed the same way (`next`), so a write that inserted paragraphs above AND rewrote the block under the
 *  reader's eye still lands on what replaced it; with that block gone too the place is where the edit begins, the first
 *  character that differs, and no further than the block's own start (a block that began before the edit keeps its
 *  start, since the text there is unchanged). */
export type Followed = { at: number; next: boolean };
export function followPlace(place: Place, newText: string): Followed {
  const old = place.source;
  if (old === newText) return { at: place.start, next: false };
  const clamp = (n: number) => Math.max(0, Math.min(n, newText.length));
  const f = followPassage(old, { start: place.start, end: Math.max(place.end, place.start + 1) }, newText);
  if (f.state === "moved") return { at: clamp(f.range.start), next: false };
  if (place.prev) {
    const g = followPassage(old, { start: place.prev.start, end: Math.max(place.prev.end, place.prev.start + 1) }, newText);
    if (g.state === "moved") return { at: clamp(g.range.start), next: true };
  }
  const min = Math.min(old.length, newText.length);
  let p = 0;
  while (p < min && old.charCodeAt(p) === newText.charCodeAt(p)) p++;
  return { at: Math.min(place.start, p), next: false };
}

/** Scroll `body`, now painted from `source`, so the block (or Raw row) holding the kept place's offset sits at the
 *  distance from the body's top the kept block sat at. The offset is followed through any edit first (followPlace).
 *  false when the body shows no text view, or no block stands at or before the offset; a write the browser clamps
 *  (the new view is shorter) leaves the body at its end. */
export function seatPlace(body: HTMLElement, source: string, place: Place): boolean {
  if (!hasBox(body)) return false;
  const { at, next } = followPlace(place, source);
  const md = body.querySelector(".fileview-md");
  const code = md ? null : body.querySelector("code.hljs");
  let el = md ? renderedBlockAt(md, source, at) : code ? rawRowForOffset(code, source, at) : null;
  if (el && next) el = md ? el.nextElementSibling : nextRowWithText(el);
  if (!hasBox(el)) return false;
  const delta = (el.getBoundingClientRect().top - body.getBoundingClientRect().top) - place.top;
  if (Math.abs(delta) >= 0.5) body.scrollTop += delta;
  return true;
}
/** The first Raw row after `row` that holds text (the blank lines between two blocks are rows too). */
function nextRowWithText(row: Element): Element | null {
  let r = row.nextElementSibling;
  while (r && !(r.textContent || "").trim()) r = r.nextElementSibling;
  return r;
}
