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
// text the reader saw), while a blank row inside a fenced code block belongs to the code block. When the reader is
// partway into a block that shows LINES (any block in Raw; in Rendered a markdown code block, fenced or indented, whose
// code element shows the block's lines one for one), the line at the edge is kept too, as its own source span and its
// top edge: the Raw row under the edge, or, in Rendered, the code line the browser's hit test finds there
// (caretRangeFromPoint on the code element's first column at the edge), measured at its FIRST character (a
// one-character Range's rect), the point the seat puts back, so a read and a seat under one layout move nothing (the
// review round 3: measured at the hit itself, a wrapped code line the reader was partway into shifted by its wrapped
// rows on the first reflow). An html block's `<pre>` is not a code block here: its lines and the block's are one off
// (the block's first line is the tag), so it keeps the depth rule below, within a line. After the paint the block is
// found in the new view, whichever view it is, and the body is scrolled so it sits where the block sat:
//   - a block that started below the edge keeps that distance;
//   - a block the reader was partway into keeps the LINE when one was kept and it still STANDS (its own span followed
//     through the edit, followPassage's `moved`): the row, or the code line's first character, goes where the line's
//     top was, so line 50 of a code block is line 50 after the switch, after a reload that inserted five lines above
//     it inside the block (the review round 2: the block's top held and line 45 stood at the edge), and after one that
//     deleted five below it. A line the write rewrote, or one whose text recurs so that no copy is its own, is no line
//     to follow, and the depth rule applies (the review round 3: a walk to the line after the nearest standing
//     predecessor seated the edit's first line, 44 rows up, when every line between was a copy; a rewritten line's
//     neighbours inside the edit cannot place it exactly, so the rule is kept to the scene it wins, a line that
//     stands). Otherwise the DEPTH is kept. As a fraction of the block's height when the block is the same text (a
//     view switch, a reflow of the same text): the height differs between the views (a 60-row table is 1800px
//     rendered and 1100px raw, a 600px figure one raw row) and changes with the column's width, and the fraction
//     keeps the words at the edge near the edge, so row 45 of the table comes back near row 45 and a reader 400px into
//     the figure comes back 400px into it (the review: the top-edge offset alone put the table's first row 1300px
//     above the edge, past its last row in Raw, and the reader four paragraphs on after the figure; and a Raw row's
//     offset seated the whole block at the row's height, so line 50 came back as line 1). In pixels when the write
//     REPLACED the block (the block under the eye rewritten, or a block whose line at the edge is gone with no line of
//     it standing on either side): a reader 30px into a paragraph a session appended a sentence to stays 30px in, and
//     a block now SHORTER than it was, by however much, is moved down by the difference, to the edge at most, so as
//     much of it shows below the edge as showed of the block before (the review: a one-line replacement for a
//     two-line paragraph the reader was 30px into sat wholly above the edge; a block that lost two of five lines while
//     the reader was 30px in reaches the edge and shows whole).
//   - a block DELETED under the reader's eye (the blocks before and after it now adjacent, so nothing stands in its
//     place) is read as replaced by nothing: the block after it is seated as a replacement of no height would be, at
//     the edge when the deleted block reached below it, at the deleted block's old distance below the edge otherwise
//     (the review round 2: the successor inherited the reader's depth into the deleted block, its first line above
//     the edge though the reader never read into it).
//   - a body at its very top stays at its very top: the views pad differently (14px rendered, 10px raw), so seating
//     the first block at the other view's padding drifted a round trip from scrollTop 0 to 4.
// Across a reload the span is followed through the edit first (followPassage, the composer's own follow): a block
// after the inserted paragraphs shifts by their length, one before them keeps its offset, and one the write rewrote is
// placed by the block before it, followed the same way, so the reader lands on what replaced it; with that block
// rewritten too, by the block after (a session rewriting two paragraphs and adding a preamble above them); with both
// neighbours gone as well, by the nearest block before it that still stands, walking outward (the kept block is the
// one after it), else the nearest after (the review round 2: three paragraphs deleted and twenty inserted above fell
// to where the edit begins, the top of the document; now the paragraph after the deleted three); only with no block
// standing on either side does the place fall to where the edit begins.
//
// What the place refuses. The anchor map pairs the Rendered elements to the blocks. Every block but an html block
// renders as one element; an html block of sibling tags renders as several, and the map's pairing across one is a
// resync on the blocks after it, which the map as it stands gets wrong two ways (Slice 5's flattened walk takes them
// up): an html block that opens a wrapper the browser nests the following markdown into (`<details>` with a blank line
// after its summary, a centred `<div>` around a heading) is paired to every element after it, since no later top-level
// element carries the nested block's text (the review round 2, and the plan's defect "an unclosed HTML wrapper
// swallows later blocks"; read as that block, a Raw switch from paragraph 80 landed on `<summary>`, 3500px up); and
// two html blocks a blank line apart (`<p>Alpha</p>` over `<p>Beta</p>`, a README's centred heading over its tagline)
// pair the first to nothing and the second to both elements; and a wrapper whose closing tag is the document's last
// block, or is missing, is paired to exactly ONE element, itself, holding every paragraph after it (the review round
// 4: trusted as any one element was, the Raw switch from a nested paragraph landed on the `<div align="center">` row
// with the passage 1395px below the viewport, and the paragraph's Raw row switched to Rendered borrowed the wrapper's
// box and landed on paragraph 43). So an html block's pairing, to one element or several, is trusted only when its
// own source, parsed by the browser's HTML parser (DOMParser), yields as many elements with the same text, whitespace
// apart: that parser is the one the sanitizer read the block with, so entities, inline tags and line breaks decode the
// same on both sides and nothing is decoded by hand (the review round 3: a hand decoder threw on an out-of-range
// numeric entity, which stopped the Raw click and the text-size step where it stood, and knew six entity names, so a
// caption hanging on `&mdash;` read as swallowed). Any other block's one element is trusted without a parse (its source
// is markdown, not html); an html block is told from the rest by marked's lexer over its own text, the lexer the map's
// table comes from, asked only for a block that opens with `<`. A pairing the parse does not confirm reads as NO place
// from whichever element is at the edge (a swallowed paragraph, the wrapper itself, a picture or a rule inside the run,
// either of two adjacent html blocks), so the numeric scrollTop stands, as it did before the slice; and a seat that
// would borrow such a block's box for a block with no element of its own (the swallowed paragraph read from Raw, a Raw
// row of the wrapper's own) declines the same way, the body unmoved (the review round 3: a Raw row of `<summary>`
// seated the whole swallowed run, 3200px, in Rendered). An html block of sibling tags, each in its source, is read as
// one block still. Where DOMParser is absent (a stand-in) such a block reads as no place too. Two shapes the parse
// reads as no place though the pairing is right, both malformed input and each recorded in the plan's Slice 2 build
// note: an html block holding a tag the sanitizer removes, when the removal changes the block's text (a `<script>` or
// `<style>` inside a tag goes with its text) or its element count (a `<style>`, an `<iframe>` or a form control between
// two `<p>`s goes, the control's text staying as a text node), parses to other elements or other text than the
// sanitizer kept (a removed tag nested inside a tag, its text kept as a `<label>`'s is or none as an `<iframe>`'s, is
// trusted as ever); and a hex character reference with no digits (`&#x;`), which Chromium decodes to U+FFFD
// when its fast-path parser reads a short string of simple tags (the block's source alone) and keeps as the literal
// text when its full parser reads it, which the sanitizer's whole-document parse is whenever the note holds a tag
// outside that path's subset (a heading, a code block, emphasis, a picture), so the two sides disagree on that one
// form in nearly every note. Every other entity form, valid or not, decodes alike on both sides.
//
// Written over the DOM the viewer builds and nothing else (querySelector, childNodes, getBoundingClientRect,
// scrollTop, and for a Rendered code line the document's caret hit test and a Range's rects, both absent from a
// stand-in) and the anchor map's block table, so a stand-in with no layout (every box at 0,0) reads no place and seats
// nothing, and the node tests over the viewer run unchanged; the browser legs (file-view-place-browser.test.ts,
// file-view-place-blocks-browser.test.ts, file-view-place-edits-browser.test.ts, file-view-place-html-browser.test.ts,
// file-view-place-wrapper-end-browser.test.ts) measure the real thing.
import { Lexer } from "marked";
import { followPassage } from "./file-comments";
import { sourceBlockSpans, renderedBlockIndex, renderedBlockElements, rawRows, rawRowForOffset, rawRowSpan, type SourceRange } from "./anchor-map";

export type View = "rendered" | "raw";
/** A line of the kept block at the body's top edge: the span of its text in the file (before its line ending) and its
 *  top edge measured from the body's top. */
export type Line = SourceRange & { top: number };
/** Where the reader is: the file text the view was painted from and which view it was; the source span of the
 *  top-visible block in it; that block's top edge measured from the body's top edge (negative when the reader is
 *  partway into it) and its box's height in that view; whether the body stood at its very top; the spans of the
 *  blocks before and after it, the first fallbacks when the write rewrote the block itself; and, when the reader is
 *  partway into a block that shows lines (a Raw block, a Rendered code block), the line at the edge. */
export type Place = {
  source: string; view: View;
  start: number; end: number;
  top: number; height: number;
  atTop: boolean;
  prev: SourceRange | null; next: SourceRange | null;
  line?: Line | null;
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
 *  has a layout or the pairing is not trusted (ownedElements). */
const renderedBlockBox = (md: Element, source: string, spans: SourceRange[], b: number): Box | null => { const els = ownedElements(md, source, spans[b], b); return els ? union(els.map(boxOf)) : null; };
/** A block's box in the Raw view: the row of its first line through the row of its last. */
function rawBlockBox(code: Element, source: string, span: SourceRange): Box | null {
  const first = rawRowForOffset(code, source, span.start), last = rawRowForOffset(code, source, Math.max(span.start, span.end - 1));
  const a = first && boxOf(first), z = last && boxOf(last);
  return a && z ? { top: a.top, bottom: z.bottom } : null;
}
const placeOf = (source: string, view: View, spans: SourceRange[], b: number, box: Box, edge: number, atTop: boolean, line: Line | null): Place => ({
  source, view, start: spans[b].start, end: spans[b].end, top: box.top - edge, height: box.bottom - box.top, atTop,
  prev: b > 0 ? spans[b - 1] : null, next: b + 1 < spans.length ? spans[b + 1] : null, line,
});

// ── the elements paired to a block: trusted, or a pairing the map got wrong (the header's "what the place refuses") ──
const stripWs = (s: string): string => s.replace(/\s+/g, "");
/** Whether the block is an html block (marked's `html` token), the one kind whose element count the map's pairing
 *  guesses. Every kind of html block opens with `<` after at most three spaces, so a block that does not is none and
 *  costs no lex (every paragraph); one that does is lexed alone, by the lexer the anchor map's block table comes from:
 *  a block's kind is decided at its first line, at a block's start either way, so the block's own text lexes to the
 *  token it lexed to inside the file (a paragraph opening with an inline tag or an autolink lexes to a paragraph). */
function isHtmlBlock(source: string, span: SourceRange): boolean {
  if (!/^ {0,3}</.test(source.slice(span.start, Math.min(span.end, span.start + 4)))) return false;
  try { const t = Lexer.lex(source.slice(span.start, span.end))[0]; return !!t && t.type === "html"; } catch { return false; }
}
/** Block `b`'s elements when the pairing can be trusted, null when it cannot. None always can, and one element of any
 *  block but an html block (every other block renders as exactly one). An html block's, one or several, are trusted
 *  when the block's own source, parsed by the browser's HTML parser, yields as many elements with the same text,
 *  whitespace apart: the parser the sanitizer read the block with, so entities, inline tags and `<br>` decode alike on
 *  both sides and nothing is decoded here. A wrapper's swallowed run (one element parsed, the rest of the document
 *  paired), a wrapper closing at the document's end or never closed (one element parsed, with the block's own text; one
 *  paired, holding every paragraph after it: the review round 4, which found the third round trusting any one element)
 *  and the second of two adjacent html blocks (one parsed, two paired) are not; nor is any such block where DOMParser
 *  is absent (a stand-in). */
function ownedElements(md: Element, source: string, span: SourceRange, b: number): Element[] | null {
  const els = renderedBlockElements(md, source, b);
  if (!els.length || (els.length === 1 && !isHtmlBlock(source, span))) return els;
  if (typeof DOMParser !== "function") return null;
  const parsed = elementsOf(new DOMParser().parseFromString(source.slice(span.start, span.end), "text/html").body);
  if (parsed.length !== els.length) return null;
  for (let i = 0; i < els.length; i++) if (stripWs(parsed[i].textContent || "") !== stripWs(els[i].textContent || "")) return null;
  return els;
}

// ── lines: the Raw rows, and the code lines of a Rendered code block ─────────────────────────────────
/** The count of line feeds in `s[a, b)`. */
function countNL(s: string, a: number, b: number): number {
  let n = 0;
  for (let i = a; i < b; i++) if (s.charCodeAt(i) === 10) n++;
  return n;
}
/** Line `k` (0-based) of the block's source text, its line ending excluded (a CR before the LF too); null past the
 *  block's last line. */
function lineSpanIn(source: string, span: SourceRange, k: number): SourceRange | null {
  let s = span.start;
  for (let i = 0; i < k; i++) { const nl = source.indexOf("\n", s); if (nl < 0 || nl >= span.end) return null; s = nl + 1; }
  if (s > span.end) return null;
  let e = source.indexOf("\n", s);
  if (e < 0 || e > span.end) e = span.end;
  if (e > s && source.charCodeAt(e - 1) === 13) e--;
  return { start: s, end: e };
}
/** A Rendered markdown code block: its code element (`pre > code`) and how many of the block's source lines the code
 *  does not show (`skip`: the fence line of a fenced block; none for an indented one, whose lines the code shows one
 *  for one, indentation apart). null for any other block, an html block's `<pre>` included: the tag is its first line,
 *  so its lines and the code's are one off, and the block keeps the depth rule (the review round 3). Exported for the
 *  pure part's test (file-view-place-blocks.test.ts): the stand-in has no hit test, so only the browser leg reaches it
 *  through a seat. */
export type Code = { code: Element; skip: number };
export function codeOf(source: string, span: SourceRange, els: Element[]): Code | null {
  if (els.length !== 1 || String(els[0].tagName).toUpperCase() !== "PRE") return null;
  const head = source.slice(span.start, Math.min(span.end, span.start + 8));
  const skip = /^ {0,3}(?:`{3,}|~{3,})/.test(head) ? 1 : /^(?: {4}|\t)/.test(head) ? 0 : -1;
  return skip < 0 ? null : { code: els[0].querySelector("code") || els[0], skip };
}
type CaretDoc = {
  caretRangeFromPoint?: (x: number, y: number) => { startContainer: Node; startOffset: number } | null;
  caretPositionFromPoint?: (x: number, y: number) => { offsetNode: Node; offset: number } | null;
  createRange?: () => Range;
};
/** The document's own hit test at a point: the text position under it (Chromium and WebKit's caretRangeFromPoint,
 *  Firefox's caretPositionFromPoint), null where the document has neither (a stand-in) or nothing is there. */
function caretAt(doc: CaretDoc, x: number, y: number): { node: Node; offset: number } | null {
  if (typeof doc.caretRangeFromPoint === "function") { const r = doc.caretRangeFromPoint(x, y); return r ? { node: r.startContainer, offset: r.startOffset } : null; }
  if (typeof doc.caretPositionFromPoint === "function") { const c = doc.caretPositionFromPoint(x, y); return c ? { node: c.offsetNode, offset: c.offset } : null; }
  return null;
}
function textNodesOf(root: Node, out: Text[] = []): Text[] {
  for (let i = 0; i < root.childNodes.length; i++) { const c = root.childNodes[i]; if (c.nodeType === 3) out.push(c as Text); else textNodesOf(c, out); }
  return out;
}
/** The offset, into `root`'s text, of the position (`node`, `offset`): a text node and an index into it, or an
 *  element and an index among its children (the caret between two of them, or at its end); -1 for a position not
 *  under `root`. */
function textOffsetAt(root: Node, node: Node, offset: number): number {
  const target: Node | null = node.nodeType === 3 ? node : node.childNodes[offset] || null;
  const atEnd = node.nodeType !== 3 && !target;
  let acc = 0, out = -1;
  const walk = (n: Node): boolean => {
    if (target && n === target) { out = acc + (n.nodeType === 3 ? offset : 0); return true; }
    if (n.nodeType === 3) { acc += (n as Text).data.length; return false; }
    for (let i = 0; i < n.childNodes.length; i++) if (walk(n.childNodes[i])) return true;
    if (atEnd && n === node) { out = acc; return true; }
    return false;
  };
  walk(root);
  return out;
}
/** The text position where line `k` (0-based) of the code element's text starts: the character after the k-th line
 *  feed (the start of the next text node when the feed ends one); null past its last line. */
function codeLineStart(code: Element, k: number): { node: Node; offset: number } | null {
  const texts = textNodesOf(code);
  if (!texts.length) return null;
  if (k === 0) return { node: texts[0], offset: 0 };
  let seen = 0;
  for (let i = 0; i < texts.length; i++) {
    const d = texts[i].data;
    for (let j = 0; j < d.length; j++) {
      if (d.charCodeAt(j) !== 10 || ++seen < k) continue;
      return j + 1 < d.length ? { node: texts[i], offset: j + 1 } : i + 1 < texts.length ? { node: texts[i + 1], offset: 0 } : { node: texts[i], offset: d.length };
    }
  }
  return null;
}
/** The top edge of the character at a text position (a one-character Range's first rect), null without a Range or a rect. */
function charTop(doc: CaretDoc, node: Node, offset: number): number | null {
  if (typeof doc.createRange !== "function") return null;
  const len = node.nodeType === 3 ? (node as Text).data.length : node.childNodes.length;
  const rg = doc.createRange();
  rg.setStart(node, Math.min(offset, len)); rg.setEnd(node, Math.min(offset + 1, len));
  const rects = rg.getClientRects();
  if (rects.length) return rects[0].top;
  const r = rg.getBoundingClientRect();
  return r.height > 0 || r.width > 0 ? r.top : null;
}
/** The code line under the body's top edge in a Rendered code block, when the code's text starts above the edge: the
 *  hit test on the code element's first column a pixel below the edge, read to its line and the line's source span,
 *  its top the top of the line's FIRST character (what renderedLineTop seats and what the Raw row records), so a read
 *  and a seat under one layout move nothing: a long line wraps, and the hit a pixel below the edge is on one of its
 *  wrapped rows, not its first (the review round 3: a reader partway into a wrapped code line was moved by its rows on
 *  the first reflow). */
function renderedLineAt(source: string, span: SourceRange, els: Element[], edge: number): Line | null {
  const c = codeOf(source, span, els);
  if (!c) return null;
  const doc = c.code.ownerDocument as unknown as CaretDoc;
  const r = c.code.getBoundingClientRect();
  if (!(r.top < edge)) return null;
  const hit = caretAt(doc, r.left + 2, edge + 1);
  if (!hit || typeof c.code.contains !== "function" || !c.code.contains(hit.node)) return null;
  const off = textOffsetAt(c.code, hit.node, hit.offset);
  if (off < 0) return null;
  const k = countNL(c.code.textContent || "", 0, off);
  const ls = lineSpanIn(source, span, k + c.skip);
  const pos = ls ? codeLineStart(c.code, k) : null;
  const top = pos ? charTop(doc, pos.node, pos.offset) : null;
  return ls && top !== null ? { start: ls.start, end: ls.end, top: top - edge } : null;
}
/** Where a source line of block `span` starts in the Rendered code block: the top of its first character; null for
 *  any other block or a line the code does not show. */
function renderedLineTop(source: string, span: SourceRange, els: Element[], lineStart: number): number | null {
  const c = codeOf(source, span, els);
  if (!c) return null;
  const k = countNL(source, span.start, lineStart) - c.skip;
  const pos = k < 0 ? null : codeLineStart(c.code, k);
  return pos ? charTop(c.code.ownerDocument as unknown as CaretDoc, pos.node, pos.offset) : null;
}
/** Where a source line of block `span` starts in the Raw view: its row's top; null when the row is not the block's. */
function rawLineTop(code: Element, source: string, span: SourceRange, lineStart: number): number | null {
  const row = rawRowForOffset(code, source, lineStart);
  const sp = row && rawRowSpan(code, source, row);
  if (!row || !sp || sp.start < span.start || sp.start >= span.end) return null;
  const box = boxOf(row);
  return box ? box.top : null;
}

/** The reader's place in `body` as it stands: the top-visible block of the Rendered view (`.fileview-md`'s children,
 *  read to their blocks) or of the Raw view (the block holding the top row of `code.hljs .fv-cl`, or the one after a
 *  blank row between blocks), read against `source`, the text that view was painted from, with the line at the edge
 *  when the reader is partway into a block that shows lines. null when the body shows neither view, when nothing is in
 *  view (a stand-in with no layout), when no element at or below the top edge is a block's (whitespace between
 *  blocks, an html block's leftover node: the next is read), when the top element is one an html wrapper swallowed
 *  (the header), or when the Raw rows disagree with the source. */
export function readPlace(body: HTMLElement, source: string): Place | null {
  if (!hasBox(body)) return null;
  const edge = body.getBoundingClientRect().top;
  const atTop = !((body.scrollTop || 0) > 0.5);
  const spans = sourceBlockSpans(source);
  const md = body.querySelector(".fileview-md");
  if (md) {
    const kids = elementsOf(md);
    for (let i = topVisibleIndex(kids.length, (k) => bottomOrNaN(kids[k]), edge + 0.5); i < kids.length; i++) {
      const b = renderedBlockIndex(md, source, kids[i]);
      if (b < 0 || b >= spans.length) continue;
      const els = ownedElements(md, source, spans[b], b);
      if (!els) return null;   // a pairing the map got wrong (a wrapper's swallowed run, adjacent html blocks): no place
      const box = union(els.map(boxOf));
      if (!box) continue;
      return placeOf(source, "rendered", spans, b, box, edge, atTop, box.top < edge ? renderedLineAt(source, spans[b], els, edge) : null);
    }
    return null;
  }
  const code = body.querySelector("code.hljs");
  const rows = code ? rawRows(code, source) : null;
  if (!code || !rows) return null;
  for (let i = topVisibleIndex(rows.length, (k) => bottomOrNaN(rows[k]), edge + 0.5); i < rows.length; i++) {
    const rowBox = boxOf(rows[i]);
    if (!rowBox) continue;
    const span = rawRowSpan(code, source, rows[i]);
    if (!span) return null;
    const b = blockHolding(spans, span.start);
    if (b < 0) return null;
    const box = rawBlockBox(code, source, spans[b]);
    if (!box) return null;
    // the row is the block's own when the block starts above the edge: a blank row between blocks reads as the block after
    // it, whose rows all start below the row and so below the edge
    return placeOf(source, "raw", spans, b, box, edge, atTop, box.top < edge ? { start: span.start, end: span.end, top: rowBox.top - edge } : null);
  }
  return null;
}

// ── following spans through an edit ─────────────────────────────────────────────────────────────────
/** The two texts' common prefix `p` and suffix `s` (followPassage's own bounds on the span the edit changed). */
function commonEnds(old: string, nw: string): { p: number; s: number } {
  const oldLen = old.length, newLen = nw.length, min = Math.min(oldLen, newLen);
  let p = 0;
  while (p < min && old.charCodeAt(p) === nw.charCodeAt(p)) p++;
  let s = 0;
  while (s < min - p && old.charCodeAt(oldLen - 1 - s) === nw.charCodeAt(newLen - 1 - s)) s++;
  return { p, s };
}
/** Whether a span of the old text lies in the region the edit changed (any of it past the common prefix and before
 *  the common suffix); a span outside it stands where it was, or shifted by the edit's length, with no search. */
const inEdit = (old: string, sp: SourceRange, p: number, s: number): boolean => !(sp.end <= p || sp.start >= old.length - s);
/** Where a span of `old` starts in `nw`, or null when its text stands intact nowhere the edit put text (followPassage:
 *  `gone`, `tied` between copies, or `elsewhere`). Exact and free for a span outside the edit. */
function survive(old: string, nw: string, sp: SourceRange, p: number, s: number): number | null {
  const range = { start: sp.start, end: Math.max(sp.end, sp.start + 1) };
  if (range.end <= p) return range.start;
  if (range.start >= old.length - s) return range.start + (nw.length - old.length);
  const f = followPassage(old, range, nw);
  return f.state === "moved" ? f.range.start : null;
}
/** How many spans INSIDE the edit a walk searches for (followPassage's anchor search over the new text) before it
 *  settles for the spans outside it, which cost nothing: a whole document rewritten is one search per block otherwise. */
const PROBES = 8;

/** Where the kept block stands in `newText`: `at`, an offset inside it (`step` 0); or, when the write rewrote it,
 *  inside the block BEFORE it (`step` 1: the kept block is the one after that), or inside the block AFTER it (`step`
 *  -1: the one before that). Its own offset when the text is unchanged; followed through the edit otherwise
 *  (followPassage: unchanged before the edit, shifted by the edit's length after it, re-found when the block's text
 *  moved whole). A block the edit rewrote, or one whose text recurs so that no copy is its own, is placed by its
 *  neighbours, followed the same way, so a write that inserted paragraphs above AND rewrote the block under the
 *  reader's eye still lands on what replaced it, and one that rewrote that block and the one before it too (a section
 *  rewritten, a preamble added) lands there by the block after; with both neighbours gone as well, by the nearest
 *  block before it that stands, walking outward through the old block table (each block inside the edit one anchor
 *  search, PROBES of them at most; a block outside the edit stands for free), else the nearest after; with none, the
 *  place is where the edit begins, the first character that differs, and no further than the block's own start (a
 *  block that began before the edit keeps its start, since the text there is unchanged). */
export type Followed = { at: number; step: -1 | 0 | 1 };
export function followPlace(place: Place, newText: string): Followed {
  const { at, step } = followBlock(place, newText);
  return { at, step };
}
type Survivor = { at: number; span: SourceRange };
/** followPlace, with `deleted`: the kept block was placed by the block before it, and between that block and the
 *  nearest block after the kept one that stands there is nothing but whitespace in the new text, so nothing stands in
 *  the kept block's place (it was deleted, alone or with its neighbours), and the block the step lands on is that
 *  block after. */
function followBlock(place: Place, newText: string): Followed & { deleted: boolean } {
  const old = place.source;
  if (old === newText) return { at: place.start, step: 0, deleted: false };
  const { p, s } = commonEnds(old, newText);
  const clamp = (n: number) => Math.max(0, Math.min(n, newText.length));
  const f = survive(old, newText, place, p, s);
  if (f !== null) return { at: clamp(f), step: 0, deleted: false };
  const gap = (pred: Survivor, succ: Survivor | null): boolean => !!succ && /^\s*$/.test(newText.slice(pred.at + (pred.span.end - pred.span.start), succ.at));
  // the neighbours the place carries, first: no block table to build
  const g = place.prev ? survive(old, newText, place.prev, p, s) : null;
  const h = place.next ? survive(old, newText, place.next, p, s) : null;
  const pred1 = g !== null && place.prev ? { at: g, span: place.prev } : null, succ1 = h !== null && place.next ? { at: h, span: place.next } : null;
  if (pred1) return { at: clamp(pred1.at), step: 1, deleted: gap(pred1, succ1) };
  if (succ1) return { at: clamp(succ1.at), step: -1, deleted: false };
  // both gone: the old block table, walked outward on each side from the next block on
  const oldSpans = sourceBlockSpans(old);
  const bi = blockIndexAt(oldSpans, place.start);
  const walk = (from: number, dir: -1 | 1): Survivor | null => {
    let budget = PROBES;
    for (let k = from; k >= 0 && k < oldSpans.length; k += dir) {
      const sp = oldSpans[k];
      if (inEdit(old, sp, p, s)) { if (budget <= 0) continue; budget--; }
      const r = survive(old, newText, sp, p, s);
      if (r !== null) return { at: r, span: sp };
    }
    return null;
  };
  const pred = bi >= 0 ? walk(bi - 2, -1) : null;
  const succ = bi >= 0 ? walk(bi + 2, 1) : null;
  if (pred) return { at: clamp(pred.at), step: 1, deleted: gap(pred, succ) };
  if (succ) return { at: clamp(succ.at), step: -1, deleted: false };
  return { at: Math.min(place.start, p), step: 0, deleted: false };
}

/** Where the kept line starts in `newText`, inside `block` (the kept block's span there): its own start when it stands
 *  (followed as a block is: unchanged before the edit, shifted after it, re-found when the edit moved it whole); null
 *  when the write rewrote it, when its text recurs so that no copy is its own (followPassage's `tied`), or when the
 *  line found lies outside the block. Nothing else: a rewritten line's neighbours inside the edit cannot place it
 *  exactly (the header), and the block's depth rule takes over. */
function followLine(place: Place, newText: string, block: SourceRange): number | null {
  const { p, s } = commonEnds(place.source, newText);
  const f = survive(place.source, newText, place.line as Line, p, s);
  return f !== null && f >= block.start && f < block.end ? f : null;
}

/** Where the kept block's top edge goes, measured from the body's top, given the block's box `height` in the view
 *  being seated (`view`): its old distance when it started below the edge; else the reader's depth into it, as a
 *  fraction of the block's height when the block's text is the `same` (a view switch, a reflow: the words at the edge
 *  stay near the edge, whatever the block's height is now) or the view changed, and in pixels when the write changed
 *  the block's text in the same view (30px into a paragraph the session appended to stays 30px in), less whatever the
 *  block is now shorter than it was, so as much of it shows below the edge as showed before, and no further down than
 *  the edge itself (a block that fits shows whole, its top at the edge: seated lower, the tail of the block before it
 *  would come into view above it). A `height` of 0 is a block replaced by nothing (deleted), and answers where the
 *  block after it goes. */
export function seatedTop(place: Place, view: View, height: number, same: boolean): number {
  if (place.top >= 0) return place.top;
  if (same || view !== place.view) return place.height > 0 ? place.top * height / place.height : 0;
  return Math.min(0, place.top + Math.max(0, place.height - height));
}

/** Scroll `body`, now painted from `source`, so the block holding the kept place's offset (followPlace: followed
 *  through any edit, stepped to a neighbour when the block itself was rewritten) sits where the kept block sat: the
 *  kept line where the line sat when the block stands and the line, or a line of the block beside it, does
 *  (followLine); else the block's top where seatedTop puts it, and, for a block deleted under the reader's eye (its
 *  neighbours now adjacent: the block the step lands on is the old neighbour itself), the block after it as a
 *  replacement of no height. A body that stood at its very top goes to its very top. false when the body shows no
 *  text view, when no block stands at or before the offset, or when the block has no box (the Raw rows disagree with
 *  the source; the block's pairing, or the box to borrow, is a wrapper's swallowed run). A write the browser clamps (the
 *  new view is shorter) leaves the body at its end. */
export function seatPlace(body: HTMLElement, source: string, place: Place): boolean {
  if (!hasBox(body)) return false;
  const md = body.querySelector(".fileview-md");
  const code = md ? null : body.querySelector("code.hljs");
  if (!md && !code) return false;
  if (place.atTop) { if (body.scrollTop !== 0) body.scrollTop = 0; return true; }
  const { at, step, deleted } = followBlock(place, source);
  const spans = sourceBlockSpans(source);
  const found = blockIndexAt(spans, at);
  if (found < 0) return false;
  const b = Math.max(0, Math.min(spans.length - 1, found + step));
  const edge = body.getBoundingClientRect().top;
  const els = md ? renderedBlockElements(md, source, b) : [];
  // the kept line, when the block stands or a block stands in its place (a changed block is found through a neighbour,
  // and the line is followed into it; a line found outside it is not the block's)
  if (place.line && place.top < 0 && !deleted) {
    const ls = followLine(place, source, spans[b]);
    const top = ls === null ? null : md ? renderedLineTop(source, spans[b], els, ls) : rawLineTop(code as Element, source, spans[b], ls);
    if (top !== null) {
      const delta = top - (edge + place.line.top);
      if (Math.abs(delta) >= 0.5) body.scrollTop += delta;
      return true;
    }
  }
  const view: View = md ? "rendered" : "raw";
  const box = md ? renderedBoxNear(md, source, spans, b) : rawBlockBox(code as Element, source, spans[b]);
  if (!box) return false;
  // the same block with the same text (a view switch, a reflow, an edit elsewhere), or one the write changed: a
  // paragraph the session added a sentence to is its own span followed intact, and still a longer block now
  const same = step === 0 && source.slice(spans[b].start, spans[b].end) === place.source.slice(place.start, place.end);
  const delta = (box.top - edge) - (deleted ? seatedTop(place, view, 0, false) : seatedTop(place, view, box.bottom - box.top, same));
  if (Math.abs(delta) >= 0.5) body.scrollTop += delta;
  return true;
}
/** Block `b`'s box in the Rendered view, or, when it has no element with a layout (a comment, a hidden element, a block
 *  the sanitizer dropped, a block nested inside an html wrapper), the nearest block's before it, else after it. null
 *  when block `b`'s own pairing, or the nearest before it with elements, is one the map got wrong (a wrapper's swallowed
 *  run, which may hold block `b`'s very element; the wrapper's own rows read from Raw): its box is the rest of the
 *  document's, and no seat is better than that one (the review round 3: a Raw row of `<summary>` seated the run's
 *  union, 3200px, in Rendered). */
function renderedBoxNear(md: Element, source: string, spans: SourceRange[], b: number): Box | null {
  const own = ownedElements(md, source, spans[b], b);
  if (!own) return null;
  const box = union(own.map(boxOf));
  if (box) return box;
  for (let k = b - 1; k >= 0; k--) {
    if (!renderedBlockElements(md, source, k).length) continue;
    const els = ownedElements(md, source, spans[k], k);
    if (!els) return null;
    const near = union(els.map(boxOf));
    if (near) return near;
  }
  for (let k = b + 1; k < spans.length; k++) { const after = renderedBlockBox(md, source, spans, k); if (after) return after; }
  return null;
}
