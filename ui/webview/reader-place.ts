// The reader's place across a paint of the file viewer's body (plans/markdown-viewer.md, Slice 2: "reader keeps
// their place"). A paint that REPLACES the body's children (a Rendered/Raw switch, a reload after a session's write)
// leaves the numeric scrollTop standing over new content, so the passage under the reader's eye changes: on the audit's
// note a reload that inserted twenty paragraphs above moved the top passage from 40 to 28, and the Rendered/Raw round
// trip drifted 648 to 918px (the Raw view is taller). A reflow that keeps the children (the pane dragged, the Comments
// aside opening or closing, a text-size step) moves the passage the same way: closing the aside at 900px took the top
// paragraph from 40 to 73. So the place is kept in the file's own terms: the top-visible BLOCK, one of the top-level
// blocks the markdown lexer finds in the file (anchor-map.ts sourceBlockSpans: a paragraph, a heading, a code block, a
// table, an html block), the first whose box ends below the body's top edge, as its source span, plus how far its top
// edge sits from the body's top and how tall its box is. Both views show the same blocks. In Rendered a block is a
// top-level element (an html block of sibling tags several, whose boxes are read together); in Raw it is the run of
// rows from its first line to its last, so a blank row between two paragraphs belongs to neither and the block after
// it is the place (the Slice 2 review: read as its own place, a blank top row seated the paragraph BEFORE the first
// text the reader saw), while a blank row inside a fenced code block belongs to the code block. After the paint the
// block is found in the new view, whichever view it is, and the body is scrolled so it sits where the block sat:
//   - a block that started below the edge keeps that distance;
//   - a block the reader was partway into keeps the DEPTH. As a fraction of the block's height when the block is the
//     same text (a view switch, a reflow of the same text): the height differs between the views (a 60-row table is
//     1800px rendered and 1100px raw, a 600px figure one raw row, a 120-line code block about the same in both) and
//     changes with the column's width, and the fraction keeps the words at the edge at the edge, so line 50 of the
//     code block stays there, row 45 of the table near it, and a reader 400px into the figure comes back 400px into it
//     (the review: the top-edge offset alone put the table's first row 1300px above the edge, past its last row in Raw,
//     and the reader four paragraphs on after the figure; and a Raw row's offset seated the whole block at the row's
//     height, so line 50 came back as line 1). In pixels when the write REPLACED the block: a reader at line 5 of a
//     code block a session appended to stays at line 5, and a replacement shorter than the depth is moved down by the
//     difference, to the edge at most, so as much of it shows below the edge as showed of the block before (the
//     review: a one-line replacement for a two-line paragraph the reader was 30px into sat wholly above the edge).
//   - a body at its very top stays at its very top: the views pad differently (14px rendered, 10px raw), so seating
//     the first block at the other view's padding drifted a round trip from scrollTop 0 to 4.
// Across a reload the span is followed through the edit first (followPassage, the composer's own follow): a block
// after the inserted paragraphs shifts by their length, one before them keeps its offset, and one the write rewrote is
// placed by the block before it, followed the same way, so the reader lands on what replaced it; with that block
// rewritten too, by the block after (a session rewriting two paragraphs and adding a preamble above them); only with
// all three gone does the place fall to where the edit begins.
//
// Written over the DOM the viewer builds and nothing else (querySelector, childNodes, getBoundingClientRect,
// scrollTop) and the anchor map's block table, so a stand-in with no layout (every box at 0,0) reads no place and seats
// nothing, and the node tests over the viewer run unchanged; the browser legs (file-view-place-browser.test.ts,
// file-view-place-blocks-browser.test.ts) measure the real thing.
import { followPassage } from "./file-comments";
import { sourceBlockSpans, renderedBlockIndex, renderedBlockElements, rawRows, rawRowForOffset, rawRowSpan, type SourceRange } from "./anchor-map";

export type View = "rendered" | "raw";
/** Where the reader is: the file text the view was painted from and which view it was; the source span of the
 *  top-visible block in it; that block's top edge measured from the body's top edge (negative when the reader is
 *  partway into it) and its box's height in that view; whether the body stood at its very top; and the spans of the
 *  blocks before and after it, the fallbacks when the write rewrote the block itself. */
export type Place = {
  source: string; view: View;
  start: number; end: number;
  top: number; height: number;
  atTop: boolean;
  prev: SourceRange | null; next: SourceRange | null;
};

type Box = { top: number; bottom: number };

/** The index of the first of `count` boxes, stacked top to bottom, whose bottom edge lies below `edge`; `count` when
 *  none does. A binary search over the boxes' bottoms, which increase down a column of blocks (a Rendered view's
 *  top-level elements, a Raw view's rows), so a long document costs a handful of box reads per scroll frame, not one
 *  per block. Two kinds of box break the order and are read around. A box with no layout at all (a hidden element;
 *  `bottomOf` answers NaN) is passed over for the next box with one, in the search and in the answer, so a hidden
 *  element below the reader on the search's path cannot send it past every block before it (the Slice 2 review: a
 *  `<div hidden>` at the search's first probe read as above the edge and the place was read twenty-four blocks below
 *  the reader). A floated or positioned figure that reaches below the blocks beside it (the paragraphs wrapping an
 *  `<img align="left">`) is a box whose successors end above the edge: the top block is then the first of those that
 *  ends below it, the paragraph the reader is reading beside the figure, whichever box the search happened to land
 *  on, and that paragraph is what a view switch or a reflow keeps (the figure, kept instead, is one row in Raw and
 *  moves when the paragraphs beside it grow taller). When no box at all ends below the edge, the last TAIL boxes are
 *  read for a figure at the document's end that still does. */
const TAIL = 8;
export function topVisibleIndex(count: number, bottomOf: (i: number) => number, edge: number): number {
  let lo = 0, hi = count;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    let m = mid, b = bottomOf(m);
    while (Number.isNaN(b) && m + 1 < hi) b = bottomOf(++m);
    if (Number.isNaN(b)) hi = mid;                    // no box with a layout from mid on: the answer, if any, lies before mid
    else if (b > edge) hi = m; else lo = m + 1;
  }
  while (lo < count && Number.isNaN(bottomOf(lo))) lo++;   // the answer is a box with a layout
  if (lo === count) {
    for (let i = count - 1, k = 0; i >= 0 && k < TAIL; i--, k++) if (bottomOf(i) > edge) return i;
    return count;
  }
  let j = lo + 1, above = false;
  for (; j < count; j++) { const b = bottomOf(j); if (Number.isNaN(b)) continue; if (b > edge) break; above = true; }
  return above && j < count ? j : lo;
}

/** The index of the block, among `spans` in source order, whose start is the largest at or below `offset`; -1 when
 *  none starts there or before. */
export function blockIndexAt(spans: SourceRange[], offset: number): number {
  let lo = 0, hi = spans.length - 1;
  if (hi < 0 || spans[0].start > offset) return -1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (spans[mid].start <= offset) lo = mid; else hi = mid - 1;
  }
  return lo;
}
/** The block holding `offset` (its start at or before it, its text's end after it), else the block after the gap the
 *  offset lies in (a blank line between two blocks, a reference definition; the first block for one before it); -1 for
 *  an offset past the last block's text. */
export function blockHolding(spans: SourceRange[], offset: number): number {
  const k = blockIndexAt(spans, offset);
  if (k < 0) return spans.length ? 0 : -1;
  return offset < spans[k].end ? k : k + 1 < spans.length ? k + 1 : -1;
}

const elementsOf = (n: Node): Element[] => Array.from(n.childNodes).filter((c) => c.nodeType === 1) as Element[];
const hasBox = (n: unknown): n is Element => !!n && typeof (n as Element).getBoundingClientRect === "function";
/** An element's box, or null for one with no layout: every edge 0 and no client rect (display: none, a `hidden`
 *  attribute the sanitizer keeps; a stand-in with no layout reads the same, and so keeps no place). */
function boxOf(el: Element): Box | null {
  const r = el.getBoundingClientRect();
  if (r.top === 0 && r.bottom === 0 && r.width === 0 && r.height === 0 && (typeof el.getClientRects !== "function" || el.getClientRects().length === 0)) return null;
  return { top: r.top, bottom: r.bottom };
}
const bottomOrNaN = (el: Element): number => { const b = boxOf(el); return b ? b.bottom : NaN; };
/** The boxes together: the topmost top to the bottommost bottom; null when none has a layout. */
function union(boxes: (Box | null)[]): Box | null {
  let out: Box | null = null;
  for (const b of boxes) { if (b) out = out ? { top: Math.min(out.top, b.top), bottom: Math.max(out.bottom, b.bottom) } : b; }
  return out;
}
/** Block `b`'s box in the Rendered view: its elements' boxes together (an html block of sibling tags), null when none
 *  has a layout. */
const renderedBlockBox = (md: Element, source: string, b: number): Box | null => union(renderedBlockElements(md, source, b).map(boxOf));
/** A block's box in the Raw view: the row of its first line through the row of its last. */
function rawBlockBox(code: Element, source: string, span: SourceRange): Box | null {
  const first = rawRowForOffset(code, source, span.start), last = rawRowForOffset(code, source, Math.max(span.start, span.end - 1));
  const a = first && boxOf(first), z = last && boxOf(last);
  return a && z ? { top: a.top, bottom: z.bottom } : null;
}
const placeOf = (source: string, view: View, spans: SourceRange[], b: number, box: Box, edge: number, atTop: boolean): Place => ({
  source, view, start: spans[b].start, end: spans[b].end, top: box.top - edge, height: box.bottom - box.top, atTop,
  prev: b > 0 ? spans[b - 1] : null, next: b + 1 < spans.length ? spans[b + 1] : null,
});

/** The reader's place in `body` as it stands: the top-visible block of the Rendered view (`.fileview-md`'s children,
 *  read to their blocks) or of the Raw view (the block holding the top row of `code.hljs .fv-cl`, or the one after a
 *  blank row between blocks), read against `source`, the text that view was painted from. null when the body shows
 *  neither, when nothing is in view (a stand-in with no layout), when no element at or below the top edge is a block's
 *  (whitespace between blocks, an html block's leftover node: the next is read), or when the Raw rows disagree with
 *  the source. */
export function readPlace(body: HTMLElement, source: string): Place | null {
  if (!hasBox(body)) return null;
  const edge = body.getBoundingClientRect().top;
  const atTop = !((body.scrollTop || 0) > 0.5);
  const spans = sourceBlockSpans(source);
  const md = body.querySelector(".fileview-md");
  if (md) {
    const kids = elementsOf(md);
    for (let i = topVisibleIndex(kids.length, (k) => bottomOrNaN(kids[k]), edge + 0.5); i < kids.length; i++) {
      if (!boxOf(kids[i])) continue;
      const b = renderedBlockIndex(md, source, kids[i]);
      if (b < 0 || b >= spans.length) continue;
      const box = renderedBlockBox(md, source, b);
      if (box) return placeOf(source, "rendered", spans, b, box, edge, atTop);
    }
    return null;
  }
  const code = body.querySelector("code.hljs");
  const rows = code ? rawRows(code, source) : null;
  if (!code || !rows) return null;
  for (let i = topVisibleIndex(rows.length, (k) => bottomOrNaN(rows[k]), edge + 0.5); i < rows.length; i++) {
    if (!boxOf(rows[i])) continue;
    const span = rawRowSpan(code, source, rows[i]);
    if (!span) return null;
    const b = blockHolding(spans, span.start);
    if (b < 0) return null;
    const box = rawBlockBox(code, source, spans[b]);
    return box ? placeOf(source, "raw", spans, b, box, edge, atTop) : null;
  }
  return null;
}

/** Where the kept block stands in `newText`: `at`, an offset inside it (`step` 0); or, when the write rewrote it,
 *  inside the block BEFORE it (`step` 1: the kept block is the one after that), or inside the block AFTER it (`step`
 *  -1: the one before that). Its own offset when the text is unchanged; followed through the edit otherwise (followPassage: unchanged before the edit, shifted by the
 *  edit's length after it, re-found when the block's text moved whole). A block the edit rewrote, or one whose text
 *  recurs so that no copy is its own, is placed by its neighbours, followed the same way, so a write that inserted
 *  paragraphs above AND rewrote the block under the reader's eye still lands on what replaced it, and one that
 *  rewrote that block and the one before it too (a section rewritten, a preamble added) lands there by the block
 *  after; with all three gone the place is where the edit begins, the first character that differs, and no further
 *  than the block's own start (a block that began before the edit keeps its start, since the text there is
 *  unchanged). */
export type Followed = { at: number; step: -1 | 0 | 1 };
export function followPlace(place: Place, newText: string): Followed {
  const old = place.source;
  if (old === newText) return { at: place.start, step: 0 };
  const clamp = (n: number) => Math.max(0, Math.min(n, newText.length));
  const follow = (sp: SourceRange) => followPassage(old, { start: sp.start, end: Math.max(sp.end, sp.start + 1) }, newText);
  const f = follow(place);
  if (f.state === "moved") return { at: clamp(f.range.start), step: 0 };
  if (place.prev) { const g = follow(place.prev); if (g.state === "moved") return { at: clamp(g.range.start), step: 1 }; }
  if (place.next) { const h = follow(place.next); if (h.state === "moved") return { at: clamp(h.range.start), step: -1 }; }
  const min = Math.min(old.length, newText.length);
  let p = 0;
  while (p < min && old.charCodeAt(p) === newText.charCodeAt(p)) p++;
  return { at: Math.min(place.start, p), step: 0 };
}

/** Where the kept block's top edge goes, measured from the body's top, given the block's box `height` in the view
 *  being seated (`view`): its old distance when it started below the edge; else the reader's depth into it, as a
 *  fraction of the block's height when the block's text is the `same` (a view switch, a reflow: the words at the edge
 *  stay the words at the edge, whatever the block's height is now) or the view changed, and in pixels when the write
 *  changed the block's text in the same view (line 5 of a code block the session appended to stays line 5), less
 *  whatever the block is now shorter than it was, so as much of it shows below the edge as showed before, and no
 *  further down than the edge itself (a replacement that fits shows whole, its top at the edge: seated lower, the
 *  tail of the block before it would come into view above it). */
export function seatedTop(place: Place, view: View, height: number, same: boolean): number {
  if (place.top >= 0) return place.top;
  if (same || view !== place.view) return place.height > 0 ? place.top * height / place.height : 0;
  return Math.min(0, place.top + Math.max(0, place.height - height));
}

/** Scroll `body`, now painted from `source`, so the block holding the kept place's offset (followPlace: followed
 *  through any edit, stepped to a neighbour when the block itself was rewritten) sits where the kept block sat
 *  (seatedTop); a body that stood at its very top goes to its very top. false when the body shows no text view, when no
 *  block stands at or before the offset, or when the block has no box (the Raw rows disagree with the source). A write
 *  the browser clamps (the new view is shorter) leaves the body at its end. */
export function seatPlace(body: HTMLElement, source: string, place: Place): boolean {
  if (!hasBox(body)) return false;
  const md = body.querySelector(".fileview-md");
  const code = md ? null : body.querySelector("code.hljs");
  if (!md && !code) return false;
  if (place.atTop) { if (body.scrollTop !== 0) body.scrollTop = 0; return true; }
  const { at, step } = followPlace(place, source);
  const spans = sourceBlockSpans(source);
  const found = blockIndexAt(spans, at);
  if (found < 0) return false;
  const b = Math.max(0, Math.min(spans.length - 1, found + step));
  const view: View = md ? "rendered" : "raw";
  const box = md ? renderedBoxNear(md, source, spans, b) : rawBlockBox(code as Element, source, spans[b]);
  if (!box) return false;
  // the same block with the same text (a view switch, a reflow, an edit elsewhere), or one the write changed: a
  // paragraph the session added a sentence to is its own span followed intact, and still a longer block now
  const same = step === 0 && source.slice(spans[b].start, spans[b].end) === place.source.slice(place.start, place.end);
  const delta = (box.top - body.getBoundingClientRect().top) - seatedTop(place, view, box.bottom - box.top, same);
  if (Math.abs(delta) >= 0.5) body.scrollTop += delta;
  return true;
}
/** Block `b`'s box in the Rendered view, or, when it has no element with a layout (a comment, a hidden element, a block
 *  the sanitizer dropped), the nearest block's before it, else after it. */
function renderedBoxNear(md: Element, source: string, spans: SourceRange[], b: number): Box | null {
  for (let k = b; k >= 0; k--) { const box = renderedBlockBox(md, source, k); if (box) return box; }
  for (let k = b + 1; k < spans.length; k++) { const box = renderedBlockBox(md, source, k); if (box) return box; }
  return null;
}
