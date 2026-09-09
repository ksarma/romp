// The reader's place across a paint of the file viewer's body. A paint that REPLACES the body's children (the
// Rendered/Raw switch of a markdown file, in the local viewer and in a document opened from a link) leaves the numeric
// scrollTop standing over content laid out differently, and a text-size step (file-view.ts textSizeControl) reflows the
// text under it, so the passage under the reader's eye changes with every switch and every step: the Raw view of a note
// is taller than its Rendered view, and a round trip that began on one paragraph came back on another, a screen away.
// So the place is kept in the file's own terms: the top-visible BLOCK, one of the top-level blocks marked's lexer finds
// in the text (a paragraph, a heading, a code block, a table, a list, an html block), as its source span, plus how far
// its top edge sits from the body's top edge and how tall its box is. Both views show the same blocks. In Rendered a
// block is a top-level element of .fileview-md (an html block of sibling tags several, whose boxes are read together);
// in Raw it is the run of rows (.fv-cl, one per line: file-view.ts codeBlock) from its first line to its last, so a
// blank row between two paragraphs belongs to neither and the block after it is the place, while a blank row inside a
// fenced code block belongs to the code block. A block that started below the edge keeps its distance in pixels;
// partway into one, the depth is kept as a fraction of the block's height, since the same block is another height in
// the other view and after a size step (half way into a paragraph's rendered lines is half way into its Raw rows). A
// body at its very top goes to the other view's very top. The seat runs before a deep link's landing (file-view.ts
// renderBody), so the landing wins.
//
// Nothing is guessed. The block table comes from marked's own lexer over the text (blockSpans), and the pairing of the
// Rendered view's elements to the blocks (renderedBlocks) is by order, each element confirmed against its block's
// rendered text, an html block taking the run of elements up to the first from which the blocks after it fit again. A
// formula is no part of the text on either side (in the chat page the sanitizer's post-pass renders KaTeX where marked's
// placeholder stood, math.ts, so the element's text is the layout's, not the file's), nor is the Copy button a fence
// wears. Where the table or the pairing cannot be confirmed (a raw the lexer's tokens do not lay end to end over the
// text, an html wrapper the browser nests the following markdown into, two html blocks with no text between them, a
// block the sanitizer changed, a formula KaTeX could not lay out and shows as its source), readPlace answers null and
// seatPlace false, and the body's scrollTop is left alone: the reader sees the view as it was before this module, never
// a wrong jump. Every read costs a binary search over the boxes (a handful of getBoundingClientRect calls, not one per
// block) plus the kept block's box; the block table is kept for the last text and a root's pairing for the root, so a
// switch pays the lex once per text and the pairing once per paint.
import { Lexer, marked, type Token } from "marked";

export type View = "rendered" | "raw";
export type Span = { start: number; end: number };
/** Where the reader is: the text the view was painted from and which view it was; the source span of the top-visible
 *  block; that block's top edge measured from the body's top edge (negative when the reader is partway into it) and
 *  its box's height in that view; whether the body stood at its very top. */
export type Place = { source: string; view: View; start: number; end: number; top: number; height: number; atTop: boolean };

type Box = { top: number; bottom: number };
/** A block of the table: its span in the source (the token's raw with its trailing line feeds trimmed); whether it is an
 *  html block, and whether that html is comments alone (nothing renders); for every other kind, its rendered text with
 *  the whitespace stripped, what the Rendered pairing confirms an element against. */
type Block = Span & { html: boolean; blank: boolean; text: string };
type Table = { blocks: Block[]; lineStarts: number[] };

// ── the block table ────────────────────────────────────────────────────────────────────────────────
/** marked's own preprocessing applied to the text as N, with the source offset of every N index (length N.length + 1).
 *  Lexer.lex turns a CRLF and a lone CR into LF (the LF maps to the CR), and blockTokens expands ONE run of tabs per
 *  line, the run right after the line's leading spaces, to four spaces a tab (each space maps to the tab; a space after
 *  the run ends the expansion for the rest of the line). null where the text needs neither, and N is the source. */
function normalizeSource(source: string): { N: string; nStart: Int32Array | null } {
  if (!/\r|^ *\t/m.test(source)) return { N: source, nStart: null };
  const map: number[] = [];
  let N = "";
  let spacesOnly = true, tabRun = false;
  for (let i = 0; i < source.length; i++) {
    const c = source[i];
    if (c === "\r") {
      N += "\n"; map.push(i);
      if (source[i + 1] === "\n") i++;
      spacesOnly = true; tabRun = false; continue;
    }
    if (c === "\n") { N += "\n"; map.push(i); spacesOnly = true; tabRun = false; continue; }
    if (c === "\t" && (spacesOnly || tabRun)) { N += "    "; map.push(i, i, i, i); spacesOnly = false; tabRun = true; continue; }
    if (c === " ") { if (tabRun) tabRun = false; }
    else { spacesOnly = false; tabRun = false; }
    N += c; map.push(i);
  }
  map.push(source.length);
  return { N, nStart: Int32Array.from(map) };
}

const DEF = Lexer.rules.block.gfm.def;   // a reference definition: the lexer consumes it and emits no token
const stripWs = (s: string): string => s.replace(/\s+/g, "");
const commentsOnly = (raw: string): boolean => raw.replace(/<!--[\s\S]*?-->/g, "").trim() === "";
/** marked's placeholder for a formula (math.ts mathPlaceholder: the TeX as text under the class that names its mode), and
 *  the KaTeX root the sanitizer's post-pass puts where it stood (math.ts renderMathPlaceholders). A formula's text is the
 *  file's on neither side, so renderedText and ownText both leave it out (the placeholder in the markup, the KaTeX root
 *  or a placeholder still standing in the tree) and the rest of the block confirms the pairing. */
const MATH_PLACEHOLDER = /<(span|div) class="md-math-(?:inline|display)">[^<]*<\/\1>/g;
const MATH_ROOTS = "button, .katex, .katex-display, .md-math-inline, .md-math-display";   // the Copy button among them: ownText's one query
const isMathRoot = (el: Element): boolean => ["katex", "katex-display", "md-math-inline", "md-math-display"].some((c) => el.classList.contains(c));
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
let decoder: HTMLTextAreaElement | null | undefined;
/** Entities decoded as the browser decodes them, through a textarea's innerHTML (RCDATA: a text node and nothing else)
 *  when a document is at hand; without one, the five marked itself emits and nbsp, an entity beyond them left as
 *  written (the pairing then declines the block, never guesses). */
function decodeEntities(s: string): string {
  if (s.indexOf("&") < 0) return s;
  if (decoder === undefined) decoder = typeof document === "object" && document && typeof document.createElement === "function" ? document.createElement("textarea") : null;
  if (decoder) { decoder.innerHTML = s; return decoder.textContent || ""; }
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] !== "#") return e in NAMED ? NAMED[e] : m;
    try { return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10)); } catch { return m; }
  });
}
/** A block's text as the Rendered view shows it, whitespace stripped: the token rendered by marked's own parser (the
 *  renderer mdBlock's parse used, extensions and all), its formulas' placeholders dropped, then its tags, and its
 *  entities decoded. "" for a token the parser refuses; mdBlock's parse of the same text fails the same way and shows it
 *  as one text node, which the pairing then finds no element for. */
function renderedText(t: Token): string {
  try { return stripWs(decodeEntities(marked.parser([t]).replace(MATH_PLACEHOLDER, "").replace(/<[^>]*>/g, ""))); } catch { return ""; }
}
/** marked's top-level tokens laid over the text, in order, `space` tokens dropped, each token's raw found where the
 *  lexer cut it: a reference definition between two tokens (the lexer consumes it and emits no token) is stepped over,
 *  and the lexer's one liberty with a raw is allowed for, a lone space on the text's last line, which blockTokens moves
 *  onto the token before it as a line feed (a one-character space token is taken for one). Markdown the lexer cannot
 *  parse, or a raw that still cannot be placed, reads as NO table (an empty one): readPlace then answers null in both
 *  views and seatPlace false, never a block over the whole text seated by a fraction no view measured. */
function lexBlocks(source: string): Block[] {
  const { N, nStart } = normalizeSource(source);
  const at = (i: number): number => (nStart ? nStart[i] : i);
  let tokens: Token[];
  try { tokens = Lexer.lex(N); } catch { return []; }
  const blocks: Block[] = [];
  let pos = 0;
  for (const t of tokens) {
    let raw = t.raw;
    if (!N.startsWith(raw, pos)) {
      for (;;) {
        const m = DEF.exec(N.slice(pos));
        if (!m || !m[0]) break;
        pos += m[0].length;
        if (N.startsWith(raw, pos)) break;
      }
      if (!N.startsWith(raw, pos)) {
        // the moved lone space: the raw's last line feed stands for the whitespace the text ends in
        const moved = raw.endsWith("\n") && N.startsWith(raw.slice(0, -1), pos) && N.slice(pos + raw.length - 1).trim() === "";
        if (!moved) return [];
        raw = raw.slice(0, -1);
      }
    }
    const end = pos + raw.length;
    if (t.type !== "space") {
      let textEnd = end;
      while (textEnd > pos && /\s/.test(N[textEnd - 1])) textEnd--;
      const html = t.type === "html";
      blocks.push({ start: at(pos), end: at(textEnd), html, blank: html && commentsOnly(raw), text: html ? "" : renderedText(t) });
    }
    pos = end;
  }
  return blocks;
}
/** The source offset each Raw row starts at: codeBlock cuts the text at every line feed and drops the empty piece after a
 *  trailing one, so row k is line k. */
function lineStarts(source: string): number[] {
  const starts = [0];
  for (let i = source.indexOf("\n"); i >= 0; i = source.indexOf("\n", i + 1)) starts.push(i + 1);
  if (source === "" || source.endsWith("\n")) starts.pop();
  return starts;
}
let lastTable: { source: string; table: Table } | null = null;
/** The table for `source`, kept for the last text: the viewer paints one text many times over fresh roots (a switch
 *  swaps the body's children and keeps the text), and the lex is the costly half. */
function tableOf(source: string): Table {
  if (lastTable && lastTable.source === source) return lastTable.table;
  const table = { blocks: lexBlocks(source), lineStarts: lineStarts(source) };
  lastTable = { source, table };
  return table;
}
/** The top-level blocks of `source` in order, each as the span of its text in the source: the token's raw with its
 *  trailing line feeds trimmed, so the blank lines between two blocks belong to neither, and the blank line inside a
 *  fenced block to it. A reference definition is no block. Offsets are the file's own through CRLF and leading tabs. */
export function blockSpans(source: string): Span[] {
  return tableOf(source).blocks.map((b) => ({ start: b.start, end: b.end }));
}
/** The index of the block, among `spans` in source order, whose start is the largest at or below `offset`; -1 when
 *  none starts there or before. */
export function blockIndexAt(spans: Span[], offset: number): number {
  let lo = 0, hi = spans.length - 1;
  if (hi < 0 || spans[0].start > offset) return -1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (spans[mid].start <= offset) lo = mid; else hi = mid - 1;
  }
  return lo;
}
/** The block holding `offset` (its start at or before it, its text's end after it), else the block after the gap the
 *  offset lies in (a blank line between two blocks, a reference definition; the first block for an offset before it);
 *  -1 for an offset past the last block's text. */
export function blockHolding(spans: Span[], offset: number): number {
  const k = blockIndexAt(spans, offset);
  if (k < 0) return spans.length ? 0 : -1;
  return offset < spans[k].end ? k : k + 1 < spans.length ? k + 1 : -1;
}

// ── boxes ──────────────────────────────────────────────────────────────────────────────────────────
/** The index of the first of `count` boxes, stacked top to bottom, whose bottom edge lies below `edge`; `count` when
 *  none does. A binary search over the boxes' bottoms, which increase down a column of blocks (a Rendered view's
 *  top-level elements, a Raw view's rows), so a long document costs a handful of box reads, not one per block. Two
 *  kinds of box break the order and are read around. A box with no layout (a hidden element; `bottomOf` answers NaN)
 *  is passed over for the next box with one, in the search and in the answer, so a hidden element below the reader on
 *  the search's path cannot send the search past every block before it. A floated or positioned figure that reaches
 *  below the blocks beside it (the paragraphs wrapping an `<img align="left">`) is a box whose successors end above
 *  the edge: the top block is then the first of those that ends below it, the paragraph the reader is reading beside
 *  the figure, whichever box the search happened to land on. When no box at all ends below the edge, the last TAIL
 *  boxes are read for a figure at the document's end that still does. */
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

const hasBox = (n: unknown): n is Element => !!n && typeof (n as Element).getBoundingClientRect === "function";
/** An element's box, or null for one with no layout: every edge 0 and no client rect (display: none, a `hidden`
 *  attribute the sanitizer keeps). */
function boxOf(el: Element): Box | null {
  const r = el.getBoundingClientRect();
  if (r.top === 0 && r.bottom === 0 && r.width === 0 && r.height === 0 && (typeof el.getClientRects !== "function" || el.getClientRects().length === 0)) return null;
  return { top: r.top, bottom: r.bottom };
}
const bottomOrNaN = (el: Element): number => { const b = boxOf(el); return b ? b.bottom : NaN; };
/** The boxes together: the topmost top to the bottommost bottom; null when none has a layout. */
function union(boxes: Array<Box | null>): Box | null {
  let out: Box | null = null;
  for (const b of boxes) { if (b) out = out ? { top: Math.min(out.top, b.top), bottom: Math.max(out.bottom, b.bottom) } : b; }
  return out;
}

// ── the Rendered view: elements paired to blocks ───────────────────────────────────────────────────
type Pairing = { count: number; paired: Element[][] | null; blockOf: Map<Element, number> };
const pairings = new WeakMap<Element, { source: string; pairing: Pairing }>();

/** The element's text with what is not the file's left out: the Copy button a fenced block wears (code-block.ts) is the
 *  viewer's dress, and a KaTeX root (isMathRoot) shows a formula's layout, not the TeX the file holds. */
function ownText(el: Element): string {
  if (isMathRoot(el)) return "";                          // a display formula: a block of its own, no text of the file's
  if (!el.querySelector(MATH_ROOTS)) return el.textContent || "";
  let s = "";
  const walk = (n: Node): void => {
    for (const c of Array.from(n.childNodes)) {
      if (c.nodeType === 3) s += (c as Text).data;
      else if (c.nodeType === 1 && (c as Element).tagName.toUpperCase() !== "BUTTON" && !isMathRoot(c as Element)) walk(c);
    }
  };
  walk(el);
  return s;
}
/** The elements of `kids` paired to `blocks` in order, or null when the pairing cannot be confirmed. Every block but an
 *  html block owns exactly one element, whose text is the block's rendered text; an html block owns the run of elements
 *  up to the first from which the blocks after it fit again (the next block with text confirms the run; a block with
 *  none, an hr or a display formula, fits by order and passes the question on; no block after it, the run reaches the
 *  end); a comment block owns none. null: an element with another text (the sanitizer removed something, or KaTeX
 *  showed a formula as its source), no element for a block or an element no block accounts for (a wrapper the browser
 *  nested the following markdown into), an html block followed by another before any text (their elements cannot be
 *  told apart). */
function pair(kids: Element[], blocks: Block[]): Element[][] | null {
  const texts = kids.map((k) => stripWs(ownText(k)));
  const fits = (b: number, k: number): boolean | null => {
    for (; b < blocks.length; b++) {
      const blk = blocks[b];
      if (blk.html) { if (blk.blank) continue; return null; }
      if (k >= kids.length || texts[k] !== blk.text) return false;
      if (blk.text !== "") return true;
      k++;
    }
    return k === kids.length;
  };
  const out: Element[][] = [];
  let j = 0;
  for (let b = 0; b < blocks.length; b++) {
    const blk = blocks[b];
    if (!blk.html) {
      if (j >= kids.length || texts[j] !== blk.text) return null;
      out.push([kids[j++]]);
    } else if (blk.blank) {
      out.push([]);
    } else {
      let k = j, fit: boolean | null = false;
      for (; k <= kids.length && fit === false; k++) fit = fits(b + 1, k);
      if (fit !== true) return null;
      k--;                                              // the loop stepped past the k that fit
      out.push(kids.slice(j, k));
      j = k;
    }
  }
  return j === kids.length ? out : null;
}
/** The pairing of `md`'s top-level elements to the blocks of `source`, kept for the root: the viewer paints a fresh
 *  root per switch and reads it once, and a root whose children changed under the pairing is paired again. */
function pairingOf(md: Element, source: string): Pairing {
  const kids = Array.from(md.children);
  const hit = pairings.get(md);
  if (hit && hit.source === source && hit.pairing.count === kids.length) return hit.pairing;
  const paired = pair(kids, tableOf(source).blocks);
  const blockOf = new Map<Element, number>();
  if (paired) paired.forEach((els, b) => { for (const e of els) blockOf.set(e, b); });
  const pairing = { count: kids.length, paired, blockOf };
  pairings.set(md, { source, pairing });
  return pairing;
}
/** The Rendered view's top-level elements paired to the blocks of `source` (blockSpans), block by block: one element
 *  for a paragraph, a heading, a code block, a table, a list; several or none for an html block; none for a comment.
 *  null when the pairing cannot be confirmed (the rules above `pair`), and the place is not kept over that view. */
export function renderedBlocks(md: Element, source: string): Element[][] | null {
  return pairingOf(md, source).paired;
}
/** Block `b`'s box in the Rendered view: its elements' boxes together; null when it has none with a layout. */
const renderedBox = (paired: Element[][], b: number): Box | null => union(paired[b].map(boxOf));
/** Block `b`'s box, or, when it has no element with a layout (a comment, a hidden element), the nearest block's after
 *  it, else before it: the content the reader had under the eye. */
function renderedBoxNear(paired: Element[][], b: number): Box | null {
  const own = renderedBox(paired, b);
  if (own) return own;
  for (let k = b + 1; k < paired.length; k++) { const box = renderedBox(paired, k); if (box) return box; }
  for (let k = b - 1; k >= 0; k--) { const box = renderedBox(paired, k); if (box) return box; }
  return null;
}

// ── the Raw view: rows ─────────────────────────────────────────────────────────────────────────────
/** The Raw view's rows: file-view.ts codeBlock in wrap mode gives every line its own `.fv-cl` row, the code element's
 *  children in order, row k for line k. */
export function rawRows(code: Element): Element[] {
  return Array.from(code.children).filter((c) => c.classList.contains("fv-cl"));
}
/** The row (line) holding `offset`: the last of `starts` at or below it. */
function lineOf(starts: number[], offset: number): number {
  let lo = 0, hi = starts.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (starts[mid] <= offset) lo = mid; else hi = mid - 1;
  }
  return lo;
}
/** A block's box in the Raw view: the row of its first line through the row of its last; null when either has no layout. */
function rawBlockBox(rows: Element[], table: Table, b: number): Box | null {
  if (!rows.length) return null;
  const { start, end } = table.blocks[b];
  const a = boxOf(rows[lineOf(table.lineStarts, start)]), z = boxOf(rows[lineOf(table.lineStarts, Math.max(start, end - 1))]);
  return a && z ? { top: a.top, bottom: z.bottom } : null;
}

// ── the place ──────────────────────────────────────────────────────────────────────────────────────
const placeOf = (source: string, view: View, blk: Block, box: Box, edge: number, atTop: boolean): Place =>
  ({ source, view, start: blk.start, end: blk.end, top: box.top - edge, height: box.bottom - box.top, atTop });

/** The reader's place in `body` as it stands: the top-visible block of the Rendered view (`.fileview-md`'s children,
 *  read to their blocks) or of the Raw view (the block holding the top row of `code.hljs`, or the one after a blank row
 *  between blocks), read against `source`, the text that view was painted from. null when the body shows neither view
 *  (the loader, a picture, the editor), when no block is in view, when the Rendered pairing cannot be confirmed
 *  (renderedBlocks), or when the Raw rows are not the text's (their count differs). */
export function readPlace(body: HTMLElement, source: string): Place | null {
  if (!hasBox(body)) return null;
  const edge = body.getBoundingClientRect().top;
  const atTop = !((body.scrollTop || 0) > 0.5);
  const table = tableOf(source);
  const md = body.querySelector(".fileview-md");
  if (md) {
    const { paired, blockOf } = pairingOf(md, source);
    if (!paired) return null;
    const kids = Array.from(md.children);
    for (let i = topVisibleIndex(kids.length, (k) => bottomOrNaN(kids[k]), edge + 0.5); i < kids.length; i++) {
      const b = blockOf.get(kids[i]);
      if (b === undefined) continue;
      const box = renderedBox(paired, b);
      if (!box) continue;
      return placeOf(source, "rendered", table.blocks[b], box, edge, atTop);
    }
    return null;
  }
  const code = body.querySelector("code.hljs");
  const rows = code ? rawRows(code) : [];
  if (!code || rows.length !== table.lineStarts.length) return null;
  for (let i = topVisibleIndex(rows.length, (k) => bottomOrNaN(rows[k]), edge + 0.5); i < rows.length; i++) {
    if (!boxOf(rows[i])) continue;
    const b = blockHolding(table.blocks, table.lineStarts[i]);   // a blank row between blocks: the block after it
    if (b < 0) return null;
    const box = rawBlockBox(rows, table, b);
    if (!box) return null;
    return placeOf(source, "raw", table.blocks[b], box, edge, atTop);
  }
  return null;
}

/** Scroll `body`, painted anew from the same `source`, so the kept block sits where it sat: its top at the same distance
 *  below the edge when the block started below it, else the same fraction of the way into it; a body that stood at its
 *  very top goes to its very top. false, the body untouched, when the text is another, when the body shows no text view,
 *  when the block is not in the table, when the Rendered pairing cannot be confirmed or the Raw rows are not the text's,
 *  or when no block near the kept one has a box. A write past the body's end is the browser's to clamp. */
export function seatPlace(body: HTMLElement, source: string, place: Place): boolean {
  if (place.source !== source || !hasBox(body)) return false;
  const md = body.querySelector(".fileview-md");
  const code = md ? null : body.querySelector("code.hljs");
  if (!md && !code) return false;
  if (place.atTop) { if (body.scrollTop !== 0) body.scrollTop = 0; return true; }
  const table = tableOf(source);
  const b = blockIndexAt(table.blocks, place.start);
  if (b < 0 || table.blocks[b].start !== place.start) return false;
  let box: Box | null;
  if (md) {
    const { paired } = pairingOf(md, source);
    if (!paired) return false;
    box = renderedBoxNear(paired, b);
  } else {
    const rows = rawRows(code as Element);
    if (rows.length !== table.lineStarts.length) return false;
    box = rawBlockBox(rows, table, b);
  }
  if (!box) return false;
  const edge = body.getBoundingClientRect().top;
  const height = box.bottom - box.top;
  const target = place.top >= 0 ? place.top : place.height > 0 ? place.top * height / place.height : 0;
  const delta = (box.top - edge) - target;
  if (Math.abs(delta) >= 0.5) body.scrollTop += delta;
  return true;
}
