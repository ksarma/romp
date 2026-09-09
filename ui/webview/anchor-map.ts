// Anchor mapping for file comments (plans/file-review.md, "Commenting from either view, and in every
// format"). A comment made from a DOM selection in the viewer must be stored with a quote that is an
// EXACT substring of the file text, so the agent CLIs, the sidecar's load-time re-anchoring, and the two
// other editor hosts treat it like a comment their own tools wrote. This module is the pure half of that:
//
//   - Raw view: one `.fv-cl` row per line whose text nodes hold the line's characters (line numbers are
//     CSS counters and never enter a selection). Every row is verified against the source before any
//     offset is trusted; a selection endpoint becomes a row and a column, the pair a source range.
//   - Rendered view: the rendered text is REBUILT from the source with the same marked lexer the viewer
//     renders with, recording the source index of every character it emits and verifying every token's
//     raw text at the position the walk assigns it. Marks the renderer consumes (heading hashes, list
//     bullets, emphasis delimiters, backticks, link brackets and destinations, escapes, hard breaks,
//     task checkboxes) are dropped; a block whose text with all whitespace removed does not equal the
//     rendered element's is refused, never mis-anchored. Code, tables, HTML, entity-bearing prose, and
//     escaped link labels refuse by design (the plan's list).
//   - makeAnchor / locateComment delegate to the vendored track-changents engine, so the browser's anchor
//     is byte-identical to the one `track-comment` would build.
//   - paintRaw / paintRendered wrap exactly the text nodes of a source range in mark elements.
//   - paintChangesRaw / paintChangesRendered / unpaintChanges (Slice 2) paint a session's pending changes:
//     an insertion is its new text wrapped, a deletion a ZERO-WIDTH point whose struck label is CSS
//     content, and the author's chip is CSS content too (`data-fc-chip` on a change's last Raw element),
//     so no text node is ever added under a row and every Raw walk above stays exact. The Rendered view
//     places the same point through the index map (paintRenderedPoint; the inline-display follow-on,
//     2026-09-07), so a deletion reads struck in the prose too and the Rendered walks stay exact for the
//     same reason.
//
// Everything walks a MINIMAL structural DOM (nodeType, childNodes, parentNode, data, splitText,
// ownerDocument.createElement/createTextNode, getAttribute/setAttribute, insertBefore/appendChild/
// removeChild), so anchor-map.test.ts runs it under node against a small stand-in with no jsdom.
//
// Offsets are UTF-16 code-unit indexes into the source string the viewer fetched (the same units the
// engine, the fingerprint, and the host script use); `end` is exclusive.

import { Lexer, type Token, type Tokens } from "marked";
import { applyMdConfig, type FrontMatterToken, type FootnoteRefToken, type FootnoteDefToken, type CalloutToken, type MarkToken, type WikilinkToken, calloutTitle } from "./md-config";
import { findExact } from "./comments";
// The vendored engine is CommonJS with no declaration file (gaps-3 map, TS7016 under this tsconfig). The
// import is bundled by esbuild as-is; the two functions used here are typed locally below. If a shared
// declaration lands later, this directive becomes a no-op.
// @ts-ignore -- untyped CommonJS module
import engineUntyped from "../../vendor/track-changents/engine.js";

// The lexer below is the static `Lexer.lex`, which reads marked's module defaults, so the one configuration every
// renderer applies (md-config.ts) is applied here too: the tokens this walk places are the tokens the viewer
// rendered, whichever bundle it runs in and whether or not the viewer's module loaded first. Idempotent.
applyMdConfig();

// ── public types (contract C4) ─────────────────────────────────────────────────────────────────────

export type Anchor = { quote: string; prefix: string; suffix: string };
/** UTF-16 offsets into the source text, `end` exclusive. */
export type SourceRange = { start: number; end: number };
export type MapOk = { ok: true; range: SourceRange; quote: string };
export type MapRefusal = {
  ok: false;
  /** One line, in the person's terms, for the composer to show. */
  reason: string;
  /** 0-based line of the refused block's first line (same numbering as rawOffsetToLine). */
  blockStartLine?: number;
  /** Source offset of the refused block's first character (for scrollToOffset). */
  blockStartOffset?: number;
  /** Whether the selected rendered text occurs in the source, so a switch to Raw can preselect it. */
  rawHasQuote: boolean;
  /** Where the selected rendered text occurs in the source, when rawHasQuote is true. */
  rawRange?: SourceRange;
};
export type MapResult = MapOk | MapRefusal;
export type SelLike = {
  anchorNode: Node | null; anchorOffset: number;
  focusNode: Node | null; focusOffset: number;
  isCollapsed: boolean;
};
export type Located = { state: "located" | "context" | "detached"; range?: SourceRange };

// ── the structural DOM the walks run over ──────────────────────────────────────────────────────────

type DNode = {
  nodeType: number;
  parentNode: DNode | null;
  childNodes: ArrayLike<DNode>;
};
type DText = DNode & { data: string; splitText(offset: number): DText };
type DElement = DNode & {
  tagName: string;
  getAttribute(name: string): string | null;
  setAttribute(name: string, value: string): void;
  insertBefore(node: DNode, ref: DNode | null): DNode;
  appendChild(node: DNode): DNode;
  removeChild(node: DNode): DNode;
  ownerDocument: { createElement(tag: string): DElement; createTextNode(s: string): DText } | null;
};

const TEXT = 3;
const ELEMENT = 1;
const isText = (n: DNode): n is DText => n.nodeType === TEXT;
const isElement = (n: DNode): n is DElement => n.nodeType === ELEMENT;
const hasClass = (n: DNode, cls: string): boolean => {
  if (!isElement(n)) return false;
  const c = n.getAttribute("class");
  return !!c && (" " + c + " ").indexOf(" " + cls + " ") >= 0;
};
const WS = /\s/;
const isWs = (c: string): boolean => WS.test(c);

/** Every text node under `root`, document order. */
function textNodes(root: DNode): DText[] {
  const out: DText[] = [];
  const visit = (n: DNode) => {
    if (isText(n)) { out.push(n); return; }
    if (isControl(n)) return;
    for (let i = 0; i < n.childNodes.length; i++) visit(n.childNodes[i]);
  };
  visit(root);
  return out;
}
const textOf = (root: DNode): string => textNodes(root).map((t) => t.data).join("");
const stripWs = (s: string): string => s.replace(/\s+/g, "");
/** A control the viewer parks inside the rendered markup, not the note's text: the Copy button code-block.ts puts in every
 *  fence's <pre>. Its label "Copy" joined a block's rendered text, so every block holding a fence, and every list or quote
 *  with one anywhere in it, failed to pair with its source and was refused as not matching the file, and paintRendered's
 *  fallback counted the label in its hay (the Slice 3 review). Every walk over a rendered node's text skips it, and since
 *  Slice 4 the other elements whose text is not the note's: a rendered formula (its glyph text is KaTeX's layout of the
 *  TeX, so the paragraph maps AROUND the formula and the mathInline / mathBlock tokens are zero-text holes), a footnote's
 *  back link, the front matter's fold label, and a gated figure's placeholder. */
const CONTROL_CLASSES = [
  "code-copy",              // the fence's Copy button (code-block.ts)
  "katex",                  // a formula KaTeX rendered (math.ts renderMathPlaceholders): glyphs laid out from the TeX, not the TeX
  "md-fnback",              // a footnote definition's back link (md-config.ts): its label is the footnote's number
  "md-frontmatter-head",    // the front matter's fold control (md-config.ts): its label is the viewer's
  "fv-gate",                // a gated figure's placeholder (figure-gate.ts): its label names the host, and holds the media
];
const isControl = (n: DNode): boolean => CONTROL_CLASSES.some((cls) => hasClass(n, cls));

// ── code lines under a wrap ────────────────────────────────────────────────────────────────────────
//
// The viewer's fenced code is wrapped in per-line rows (code-block.ts wrapCodeLines: `<span class="cl"><span
// class="ct">…</span></span>` per line; the Raw view's `.fv-cl` rows are built the same way), and the wrap DROPS the
// newline each row stands for, so a wrapped code element's textContent runs its lines together. Everything that reads a
// code block's LINES reads them through here, and sees the source's line structure whether the code was wrapped or not:
// paintRendered's fallback below (a comment across two code lines matched its quote, which holds a newline, against a
// hay reading "commentdef" and painted nothing; Slice 3 of plans/markdown-viewer.md), reader-place.ts (the code line at
// the body's top edge, kept across a paint), and Slice 8's exact mapping of code lines. One reading, so the three agree.

const isCodeRow = (n: DNode): boolean => hasClass(n, "cl") || hasClass(n, "fv-cl");

/** One run of a code element's text: a text node with its data, or the newline (no node) between two adjacent rows,
 *  which `row` is the second of. */
export type CodeRun = { node: DText | null; text: string; row?: DElement };

/** The text runs of `code` in document order: its text nodes, with a "\n" run put back between two adjacent rows. A
 *  text node itself is its one run. */
export function codeRuns(code: DNode): CodeRun[] {
  const out: CodeRun[] = [];
  const visit = (n: DNode) => {
    if (isText(n)) { out.push({ node: n, text: n.data }); return; }
    let prevRow = false;
    for (let i = 0; i < n.childNodes.length; i++) {
      const c = n.childNodes[i];
      if (isControl(c)) continue;
      const row = isElement(c) && isCodeRow(c);
      if (row && prevRow) out.push({ node: null, text: "\n", row: c as DElement });
      visit(c);
      prevRow = row;
    }
  };
  visit(code);
  return out;
}

/** The text of `code` as its source shows it: the text nodes' data with the newline between rows put back. */
export const codeText = (code: DNode): string => codeRuns(code).map((r) => r.text).join("");

/** The 0-based line of the DOM position (`node`, `offset`) in `code`: a text node and an index into it, or an element
 *  and an index among its children (a caret between two of them, or at its end, the shapes caretRangeFromPoint gives);
 *  -1 for a position not under `code`. The newlines before the position count, real and between rows. The position is
 *  taken as a DOM position, not a character offset, on purpose: once the wrap has dropped the newline, the end of one
 *  row's text and the start of the next are the same character offset and different lines, and the row that holds the
 *  position tells them apart. */
export function codeLineAt(code: DNode, node: DNode, offset: number): number {
  const target: DNode | null = isText(node) ? node : node.childNodes[offset] || null;
  const atEnd = !isText(node) && !target;   // the end of an element: after its last content
  let lines = 0;
  const nl = (s: string, end: number): number => { let n = 0; for (let i = 0; i < end; i++) if (s.charCodeAt(i) === 10) n++; return n; };
  const visit = (n: DNode): boolean => {   // true once the position is reached
    if (target && n === target) { if (isText(n)) lines += nl(n.data, Math.min(offset, n.data.length)); return true; }
    if (isText(n)) { lines += nl(n.data, n.data.length); return false; }
    let prevRow = false;
    for (let i = 0; i < n.childNodes.length; i++) {
      const c = n.childNodes[i];
      if (isControl(c)) continue;
      const row = isElement(c) && isCodeRow(c);
      if (row && prevRow) lines++;   // the boundary before this row, whether the position is in it or past it
      if (visit(c)) return true;
      prevRow = row;
    }
    if (atEnd && n === node) return true;
    return false;
  };
  return visit(code) ? lines : -1;
}

/** The text position where line `k` (0-based) of `code` starts: the character after the k-th newline (the start of the
 *  next text node when the newline ends one, or the row after it when the newline is a row boundary; the row element
 *  itself, at offset 0, when that row holds no text); null past the last line. */
export function codeLineStart(code: DNode, k: number): { node: DNode; offset: number } | null {
  const runs = codeRuns(code);
  const firstTextFrom = (i: number): DText | null => { for (let j = i; j < runs.length; j++) if (runs[j].node) return runs[j].node; return null; };
  if (k === 0) { const t = firstTextFrom(0); return t ? { node: t, offset: 0 } : null; }
  let seen = 0;
  for (let i = 0; i < runs.length; i++) {
    const r = runs[i];
    if (!r.node) {
      if (++seen < k) continue;
      const rowText = textNodes(r.row as DNode)[0];
      return rowText ? { node: rowText, offset: 0 } : { node: r.row as DNode, offset: 0 };
    }
    const d = r.text;
    for (let j = 0; j < d.length; j++) {
      if (d.charCodeAt(j) !== 10 || ++seen < k) continue;
      if (j + 1 < d.length) return { node: r.node, offset: j + 1 };
      const next = firstTextFrom(i + 1);
      return next ? { node: next, offset: 0 } : { node: r.node, offset: d.length };
    }
  }
  return null;
}

/** Sum of the lengths of the text nodes under `n` that a `counts` predicate admits (null = all). */
function textLenUnder(n: DNode, inCounted: boolean, counts: ((el: DElement) => boolean) | null): number {
  if (isText(n)) return inCounted || !counts ? n.data.length : 0;
  if (isControl(n)) return 0;
  const here = inCounted || !counts || (isElement(n) && counts(n));
  let sum = 0;
  for (let i = 0; i < n.childNodes.length; i++) sum += textLenUnder(n.childNodes[i], here, counts);
  return sum;
}

/**
 * The number of counted characters under `root` before the boundary (node, offset), i.e. the boundary's
 * global text index. "before"/"after" when the boundary is outside `root` but `node` is an ancestor of
 * it (the selection reached past the text and may snap to its edge); null when the boundary is unrelated
 * to `root` (a sibling surface, which refuses). `counts` limits counting to text under elements it
 * admits (the Raw rows), so text outside a row never shifts an index.
 */
function boundaryIndex(root: DNode, node: DNode, offset: number,
                       counts: ((el: DElement) => boolean) | null): number | "before" | "after" | null {
  let total = 0;
  const visit = (n: DNode, inCounted: boolean): boolean => {
    if (n === node) {
      if (isText(n)) { if (inCounted || !counts) total += Math.min(Math.max(0, offset), n.data.length); return true; }
      const here = inCounted || !counts || (isElement(n) && counts(n));
      for (let i = 0; i < offset && i < n.childNodes.length; i++) total += textLenUnder(n.childNodes[i], here, counts);
      return true;
    }
    if (isText(n)) { if (inCounted || !counts) total += n.data.length; return false; }
    if (isControl(n)) return false;
    const here = inCounted || !counts || (isElement(n) && counts(n));
    for (let i = 0; i < n.childNodes.length; i++) if (visit(n.childNodes[i], here)) return true;
    return false;
  };
  if (visit(root, false)) return total;
  // Not under root: is `node` an ancestor of root? Then the boundary sits before or after the whole root.
  let child: DNode = root;
  let p = root.parentNode;
  while (p) {
    if (p === node) {
      let idx = -1;
      for (let i = 0; i < p.childNodes.length; i++) if (p.childNodes[i] === child) { idx = i; break; }
      return idx >= 0 && idx < offset ? "after" : "before";
    }
    child = p; p = p.parentNode;
  }
  return null;
}

/** A refusal with the plan's note-preserving fields. */
function refuse(reason: string, extra?: Partial<MapRefusal>): MapRefusal {
  return { ok: false, reason, rawHasQuote: false, ...extra };
}

// ── Raw view ───────────────────────────────────────────────────────────────────────────────────────
//
// The viewer builds one `.fv-cl` row per line by splitting the text on "\n" and setting the rows through
// innerHTML, so a CRLF file's rows end in a "\r" that the HTML parser turns into "\n", and a lone CR
// inside a line does the same. The walk below does not assume either split: it verifies every row's
// text against the source character by character (a DOM "\n" may stand for a source "\r"), then consumes
// whichever line ending the source has between rows. Within a verified row every DOM character is one
// source character, so an (row, column) pair is a source offset with no further lookup.

type RawRow = { el: DElement; text: string; srcStart: number };
type RawIndex = { source: string; shape: Shape; rows: RawRow[]; els: DElement[]; rowOf: Map<DElement, number>; rowStart: number[]; total: number };

/** What a cached analysis was built over: the same source and the same children of the root, every child by
 *  identity. The viewer swaps a body's children wholesale on re-render, so a cache keyed on the root alone would go
 *  stale; and a check on the children's count and first and last alone went stale too: the Comments panel's regions
 *  layer wraps a top-level picture in a span of its own while the panel is open (file-comments-regions.ts), which
 *  changes none of the three, so the rendered table kept pairing the picture, by then a grandchild, and its wrapper
 *  stood for no block (the Slice 2 review: a reader partway into the figure was thrown to the document's top on a
 *  view switch). A hit costs one pointer compare per child. */
type Shape = { source: string; children: DNode[] };
const shapeOf = (root: DNode, source: string): Shape => ({ source, children: Array.from(root.childNodes) });
const sameShape = (a: Shape, root: DNode, source: string): boolean => {
  if (a.source !== source || a.children.length !== root.childNodes.length) return false;
  for (let i = 0; i < a.children.length; i++) if (a.children[i] !== root.childNodes[i]) return false;
  return true;
};

const isRow = (el: DElement): boolean => hasClass(el, "fv-cl");

/** The `.fv-cl` rows under `root`, document order, not descending into a row. */
function collectRows(root: DNode, out: DElement[] = []): DElement[] {
  for (let i = 0; i < root.childNodes.length; i++) {
    const c = root.childNodes[i];
    if (!isElement(c)) continue;
    if (isRow(c)) out.push(c); else collectRows(c, out);
  }
  return out;
}

const rawCache = new WeakMap<object, RawIndex>();

function rawIndex(codeRoot: DElement, source: string): RawIndex | { error: string } {
  const hit = rawCache.get(codeRoot);
  if (hit && sameShape(hit.shape, codeRoot, source)) return hit;
  const shape = shapeOf(codeRoot, source);
  const rows: RawRow[] = [];
  const rowStart: number[] = [];
  let pos = 0, total = 0;
  const els = collectRows(codeRoot);
  for (let r = 0; r < els.length; r++) {
    const text = textOf(els[r]);
    const srcStart = pos;
    for (let i = 0; i < text.length; i++) {
      const c = text[i], s = source[pos];
      if (c === s || (c === "\n" && s === "\r")) { pos++; continue; }
      return { error: `row ${r + 1} differs from the file text at column ${i + 1}` };
    }
    rows.push({ el: els[r], text, srcStart });
    rowStart.push(total);
    total += text.length;
    // the line ending that separated this row from the next
    if (source[pos] === "\r" && source[pos + 1] === "\n") pos += 2;
    else if (source[pos] === "\n" || source[pos] === "\r") pos += 1;
    else if (pos !== source.length) return { error: `row ${r + 1} is not followed by a line ending in the file text` };
  }
  if (pos !== source.length) return { error: `the rows end ${source.length - pos} characters before the file text does` };
  const rowOf = new Map<DElement, number>();
  for (let r = 0; r < rows.length; r++) rowOf.set(rows[r].el, r);
  const idx: RawIndex = { source, shape, rows, els, rowOf, rowStart, total };
  rawCache.set(codeRoot, idx);
  return idx;
}

/** The row holding global DOM index g (g in [0, total)). */
function rowAt(idx: RawIndex, g: number): number {
  let lo = 0, hi = idx.rows.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (idx.rowStart[mid] <= g) lo = mid; else hi = mid - 1;
  }
  return lo;
}
const rawDomChar = (idx: RawIndex, g: number): string => { const r = rowAt(idx, g); return idx.rows[r].text[g - idx.rowStart[r]]; };
const rawSrcOf = (idx: RawIndex, g: number): number => { const r = rowAt(idx, g); return idx.rows[r].srcStart + (g - idx.rowStart[r]); };
/** The DOM text of global range [s, e): the rows' texts, no separators. */
function rawDomSlice(idx: RawIndex, s: number, e: number): string {
  let out = "";
  for (let r = rowAt(idx, s); r < idx.rows.length && idx.rowStart[r] < e; r++) {
    const row = idx.rows[r];
    out += row.text.slice(Math.max(0, s - idx.rowStart[r]), Math.min(row.text.length, e - idx.rowStart[r]));
  }
  return out;
}

export function mapRawSelection(sel: SelLike, codeRoot: Element, source: string): MapResult {
  const root = codeRoot as unknown as DElement;
  if (sel.isCollapsed || !sel.anchorNode || !sel.focusNode) return refuse("Select some text to comment on.");
  const idx = rawIndex(root, source);
  if ("error" in idx) return refuse(`The Raw view does not match the file text (${idx.error}); reload the file and try again.`);
  const a = boundaryIndex(root, sel.anchorNode as unknown as DNode, sel.anchorOffset, isRow);
  const f = boundaryIndex(root, sel.focusNode as unknown as DNode, sel.focusOffset, isRow);
  if (a === null || f === null) return refuse("The selection reaches outside the file text.");
  const snap = (x: number | "before" | "after") => (x === "before" ? 0 : x === "after" ? idx.total : x);
  let s = Math.min(snap(a), snap(f)), e = Math.max(snap(a), snap(f));
  if (s >= e) return refuse("Select some text to comment on.");
  // Self-check on the untrimmed range: the text nodes' concatenation must equal the source slice with
  // its line endings removed (a DOM "\n" standing for a source "\r" is a line ending too).
  const dom = rawDomSlice(idx, s, e);
  const untrimmed = source.slice(rawSrcOf(idx, s), rawSrcOf(idx, e - 1) + 1);
  if (dom.replace(/[\r\n]/g, "") !== untrimmed.replace(/[\r\n]/g, "")) {
    return refuse("The Raw view does not match the file text; reload the file and try again.");
  }
  while (s < e && isWs(rawDomChar(idx, s))) s++;
  while (e > s && isWs(rawDomChar(idx, e - 1))) e--;
  if (s >= e) return refuse("The selection is only whitespace.");
  const start = rawSrcOf(idx, s), end = rawSrcOf(idx, e - 1) + 1;
  return { ok: true, range: { start, end }, quote: source.slice(start, end) };
}

/** 0-based line index of a source offset: the Raw view's row (rows split on LF; a lone CR stays in its row). */
export function rawOffsetToLine(source: string, offset: number): number {
  const upto = Math.max(0, Math.min(offset, source.length));
  let line = 0, i = -1;
  while ((i = source.indexOf("\n", i + 1)) !== -1 && i < upto) line++;
  return line;
}

/** The Raw row element whose source span holds `offset` (the verified row map, so it follows whatever
 *  split the viewer used), or null when the rows do not match the source. Addition beyond contract C4,
 *  for scrollToOffset / Reveal. */
export function rawRowForOffset(codeRoot: Element, source: string, offset: number): Element | null {
  const idx = rawIndex(codeRoot as unknown as DElement, source);
  if ("error" in idx || !idx.rows.length) return null;
  let lo = 0, hi = idx.rows.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (idx.rows[mid].srcStart <= offset) lo = mid; else hi = mid - 1;
  }
  return idx.rows[lo].el as unknown as Element;
}

/** The source span of a Raw row (`.fv-cl`): where its text starts in the file and where it ends, before the line
 *  ending (the verified row map, so a CRLF file's offsets are the file's). null when the rows do not match the source
 *  or `row` is not one of them. For the reader's place across a paint (reader-place.ts): the top row's span is
 *  what a view switch or a reload keeps. */
export function rawRowSpan(codeRoot: Element, source: string, row: Element): SourceRange | null {
  const idx = rawIndex(codeRoot as unknown as DElement, source);
  if ("error" in idx) return null;
  const i = idx.rowOf.get(row as unknown as DElement);
  if (i === undefined) return null;
  const r = idx.rows[i];
  return { start: r.srcStart, end: r.srcStart + r.text.length };
}

/** The Raw rows of the view in order, the verified row map's own array (read, never written), so a read once per
 *  scroll frame (reader-place.ts) queries the DOM for the rows once per paint, not once per frame. null when the rows
 *  do not match the source. */
export function rawRows(codeRoot: Element, source: string): Element[] | null {
  const idx = rawIndex(codeRoot as unknown as DElement, source);
  return "error" in idx ? null : (idx.els as unknown as Element[]);
}

// ── mark elements ──────────────────────────────────────────────────────────────────────────────────

function makeMark(doc: DElement["ownerDocument"], className: string, data?: Record<string, string>): DElement {
  if (!doc) throw new Error("anchor-map: node has no ownerDocument");
  const m = doc.createElement("mark");
  m.setAttribute("class", className);
  if (data) for (const k of Object.keys(data)) m.setAttribute("data-" + k, data[k]);
  return m;
}

function wrapNode(t: DText, className: string, data?: Record<string, string>): DElement {
  const parent = t.parentNode as DElement | null;
  if (!parent) throw new Error("anchor-map: text node has no parent");
  const m = makeMark((parent as DElement).ownerDocument, className, data);
  parent.insertBefore(m, t);
  m.appendChild(t);
  return m;
}

/** Wrap [a, b) of the concatenated text of `nodes` (consecutive text nodes) in marks, splitting at the
 *  edges; whitespace-only nodes are skipped when `skipWs` admits them. Returns the marks in order. */
function wrapSlices(nodes: DText[], a: number, b: number, className: string, data: Record<string, string> | undefined,
                    skipWs: ((t: DText) => boolean) | null): DElement[] {
  const marks: DElement[] = [];
  let off = 0;
  for (let i = 0; i < nodes.length && off < b; i++) {
    let t = nodes[i];
    const len = t.data.length;
    const s = Math.max(a, off), e = Math.min(b, off + len);
    off += len;
    if (e <= s) continue;
    if (s - (off - len) > 0) t = t.splitText(s - (off - len));
    if (e - s < t.data.length) t.splitText(e - s);
    if (skipWs && skipWs(t)) continue;
    marks.push(wrapNode(t, className, data));
  }
  return marks;
}

export function paintRaw(codeRoot: Element, source: string, range: SourceRange, className: string,
                         data?: Record<string, string>): Element[] {
  const idx = rawIndex(codeRoot as unknown as DElement, source);
  if ("error" in idx) return [];
  const marks: DElement[] = [];
  for (const row of idx.rows) {
    const a = Math.max(range.start, row.srcStart), b = Math.min(range.end, row.srcStart + row.text.length);
    if (b <= a) continue;
    marks.push(...wrapSlices(textNodes(row.el), a - row.srcStart, b - row.srcStart, className, data, null));
  }
  return marks as unknown as Element[];
}

// ── the vendored engine ────────────────────────────────────────────────────────────────────────────

type Engine = {
  makeAnchor(text: string, from: number, to: number, ctx?: number): Anchor;
  locateAnchor(text: string, anchor: Anchor, hint?: number): { from: number; to: number } | null;
};
const engine = engineUntyped as Engine;

/** The engine's own anchor (24 characters of context either side), so a comment made here is
 *  indistinguishable from one `track-comment` wrote. */
export function makeAnchor(source: string, range: SourceRange): Anchor {
  return engine.makeAnchor(source, range.start, range.end);
}

/** Where a stored anchor sits in the current text: at its quote ("located"), between its surviving
 *  context after the quote changed ("context", engine.js's between-context fallback), or nowhere
 *  ("detached"). `hintOffset` breaks ties between equally good candidates, nearest wins. */
export function locateComment(source: string, anchor: Anchor, hintOffset?: number): Located {
  const loc = engine.locateAnchor(source, anchor, hintOffset);
  if (!loc) return { state: "detached" };
  const range = { start: loc.from, end: loc.to };
  return { state: source.slice(loc.from, loc.to) === anchor.quote ? "located" : "context", range };
}

// ── Rendered view: rebuilding the rendered text with source positions ──────────────────────────────
//
// marked's tokens carry no positions and its `raw` strings index a PREPROCESSED text (CRLF and CR
// normalized to LF, leading tabs expanded to four spaces), children of list items and blockquotes are
// dedented / de-prefixed, and block-level `text` tokens double their interior newlines in `raw`. The walk
// therefore runs over the normalized text N with a map back to source offsets, places every token by
// verifying its raw (or, for block text, its text) at the assigned position, and maps child text through
// a per-line "suffix of the raw line" view for list items and blockquotes. Only non-whitespace characters
// are recorded: the renderer's own line breaks carry no text, so alignment and mapping ignore whitespace.

class Refusal extends Error {}

/** A window onto N: `str` is the text the tokens tile; n(i) is the N index of str[i] (i may equal length). */
class View {
  constructor(readonly str: string, private readonly base: number | null, private readonly map: number[] | null) {}
  static identity(str: string, base: number): View { return new View(str, base, null); }
  n(i: number): number { return this.map ? this.map[i] : (this.base as number) + i; }
  sub(from: number, to: number): View {
    if (this.map) {
      const m = this.map.slice(from, to + 1);
      return new View(this.str.slice(from, to), null, m);
    }
    return new View(this.str.slice(from, to), (this.base as number) + from, null);
  }
}

/** Child text of a list item or blockquote: line i of `text` is a suffix of line i of the raw view (the
 *  bullet, indentation, or `> ` prefix removed); raw lines past the text are blank. Anything else (a tab
 *  the lexer expanded after the marker, marked's setext protection) fails the suffix test and refuses. */
function suffixLineView(raw: View, text: string): View {
  const rawLines = raw.str.split("\n"), textLines = text.split("\n");
  if (textLines.length > rawLines.length) throw new Refusal("a block whose lines the mapping could not place");
  const map: number[] = new Array(text.length + 1);
  let rawLineStart = 0, ti = 0, endN = raw.n(0);
  for (let i = 0; i < textLines.length; i++) {
    const rl = rawLines[i], tl = textLines[i];
    if (!rl.endsWith(tl)) throw new Refusal("a line that begins with a tab after its marker");
    const off = rl.length - tl.length;
    for (let k = 0; k < tl.length; k++) map[ti + k] = raw.n(rawLineStart + off + k);
    ti += tl.length;
    endN = raw.n(rawLineStart + off + tl.length);
    if (i < textLines.length - 1) { map[ti] = raw.n(rawLineStart + rl.length); ti++; }
    rawLineStart += rl.length + 1;
  }
  for (let i = textLines.length; i < rawLines.length; i++) {
    if (rawLines[i].trim() !== "") throw new Refusal("a block whose lines the mapping could not place");
  }
  map[text.length] = endN;
  return new View(text, null, map);
}

type Hole = { reason: string; startN: number; endN: number };
/** The emitted characters of one top-level block: `chars` are its non-whitespace rendered characters in
 *  order; `pos[k]` is the N index of chars[k], or -(h+1) for a character inside holes[h] (a nested code
 *  block or table the renderer shows but the mapping refuses). */
class Emitter {
  chars = "";
  pos: number[] = [];
  holes: Hole[] = [];
  put(c: string, n: number): void {
    if (isWs(c)) return;
    if (this.pos.length && n >= 0) {
      const prev = this.pos[this.pos.length - 1];
      if (prev >= 0 && n <= prev) throw new Refusal("text the mapping could not order");
    }
    this.chars += c; this.pos.push(n);
  }
  putHole(text: string, hole: number): void {
    for (const c of text) if (!isWs(c)) { this.chars += c; this.pos.push(-(hole + 1)); }
  }
}

// marked's escape() leaves an `&` alone when it begins an entity; the browser then decodes it to ONE
// character, so the rendered text is shorter than the source. Such prose refuses (plan).
const ENTITY_RE = /&(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);/;
const countNL = (s: string): number => { let n = 0; for (let i = 0; i < s.length; i++) if (s[i] === "\n") n++; return n; };

function emitText(view: View, em: Emitter): void {
  if (ENTITY_RE.test(view.str)) throw new Refusal("prose with an HTML entity");
  for (let i = 0; i < view.str.length; i++) em.put(view.str[i], view.n(i));
}

/** Rendered text of inline tokens with no positions (table cells: shown, never mapped). */
function plainInline(tokens: Token[]): string {
  let out = "";
  for (const t of tokens) {
    switch (t.type) {
      case "text": {
        const tt = t as Tokens.Text;
        if (tt.tokens) { out += plainInline(tt.tokens); break; }
        if (ENTITY_RE.test(tt.raw)) throw new Refusal("prose with an HTML entity");
        out += tt.raw; break;
      }
      case "escape": out += (t as Tokens.Escape).raw.slice(1); break;
      case "codespan": { const n = /^`+/.exec(t.raw)![0].length; out += t.raw.slice(n, t.raw.length - n); break; }
      case "em": case "strong": case "del": case "link": case "mark": out += plainInline((t as Tokens.Em).tokens); break;
      case "footnoteRef": out += String((t as FootnoteRefToken).n); break;   // the number the reference shows
      case "wikilink": { const w = t as WikilinkToken; if (!w.image) out += w.text; break; }   // an image embed shows no text
      case "image": case "br": case "html": case "mathInline": break;   // a formula's glyphs are skipped as a control (isControl)
      default: throw new Refusal(`content of a kind the mapping does not handle (${t.type})`);
    }
  }
  return out;
}

function walkInline(tokens: Token[], view: View, em: Emitter): void {
  let p = 0;
  for (const t of tokens) {
    const raw = t.raw;
    if (!view.str.startsWith(raw, p)) throw new Refusal(`a ${t.type} the mapping could not place`);
    switch (t.type) {
      case "text": {
        const tt = t as Tokens.Text;
        if (tt.tokens) walkInline(tt.tokens, view.sub(p, p + raw.length), em);
        else emitText(view.sub(p, p + raw.length), em);
        break;
      }
      case "escape": em.put(raw.slice(1), view.n(p + 1)); break;
      case "codespan": {
        const n = /^`+/.exec(raw)![0].length;
        if (raw.length < 2 * n || raw.slice(raw.length - n) !== "`".repeat(n)) throw new Refusal("an inline code span the mapping could not place");
        for (let i = n; i < raw.length - n; i++) em.put(raw[i], view.n(p + i));
        break;
      }
      case "em": case "strong": case "del": case "mark": {
        const tt = t as Tokens.Em | Tokens.Strong | Tokens.Del | MarkToken;
        const d = t.type === "em" ? 1 : t.type === "strong" || t.type === "mark" ? 2 : (/^~+/.exec(raw) || [""])[0].length;
        if (!d || raw.slice(d, raw.length - d) !== tt.text) throw new Refusal(`${t.type} marks the mapping could not place`);
        walkInline(tt.tokens, view.sub(p + d, p + d + tt.text.length), em);
        break;
      }
      case "footnoteRef": {
        // `[^id]` shows its number, text the source does not hold: a hole the selection may not touch
        const tt = t as FootnoteRefToken;
        em.holes.push({ reason: "a footnote reference", startN: view.n(p), endN: view.n(p + raw.length) });
        em.putHole(String(tt.n), em.holes.length - 1);
        break;
      }
      case "wikilink": {
        // `[[Note]]`, `[[Note|alias]]`, `![[Note]]`: the shown text is the source text at textOffset (md-config.ts); an image
        // embed (`![[image.png]]`) is a picture and shows no text
        const tt = t as WikilinkToken;
        if (tt.image) break;
        if (raw.slice(tt.textOffset, tt.textOffset + tt.text.length) !== tt.text) throw new Refusal("a wikilink the mapping could not place");
        emitText(view.sub(p + tt.textOffset, p + tt.textOffset + tt.text.length), em);
        break;
      }
      case "mathInline": {
        // rendered by KaTeX into glyphs the walks skip (isControl): a zero-text hole, so the paragraph maps around it
        em.holes.push({ reason: "a formula", startN: view.n(p), endN: view.n(p + raw.length) });
        break;
      }
      case "link": {
        const tt = t as Tokens.Link;
        if (raw[0] === "[") {
          // The label's tokens tile `text`, which is the label with `\[` and `\]` unescaped: an escaped
          // bracket shifts every later position, so such labels refuse (plan).
          if (raw.slice(1, 1 + tt.text.length) !== tt.text || raw[1 + tt.text.length] !== "]") {
            throw new Refusal(/\\[\[\]]/.test(raw) ? "a link label with an escaped bracket" : "a link the mapping could not place");
          }
          walkInline(tt.tokens, view.sub(p + 1, p + 1 + tt.text.length), em);
        } else {
          // autolink <...> or a bare URL: the rendered text is the source text itself
          const off = raw[0] === "<" ? 1 : 0;
          emitText(view.sub(p + off, p + raw.length - off), em);
        }
        break;
      }
      case "image": case "br": case "html": break;   // no rendered text
      default: throw new Refusal(`content of a kind the mapping does not handle (${t.type})`);
    }
    p += raw.length;
  }
  if (p !== view.str.length) throw new Refusal("text the mapping could not place");
}

/** ATX: the text follows the hashes and whitespace; setext: the text starts the raw. */
function headingTextOffset(raw: string, text: string): number {
  const m = /^ {0,3}#{1,6}(?=\s|$)/.exec(raw);
  if (m) {
    let off = m[0].length;
    while (off < raw.length && isWs(raw[off])) off++;
    if (!raw.startsWith(text, off)) throw new Refusal("a heading the mapping could not place");
    return off;
  }
  if (!raw.startsWith(text)) throw new Refusal("a heading the mapping could not place");
  return 0;
}

const DEF_RE = (): RegExp => Lexer.rules.block.gfm.def;

/** Place `tokens`, which tile `view.str` from `p` (block-level; nested containers recurse). */
function walkBlocks(tokens: Token[], view: View, em: Emitter, p = 0): void {
  for (const t of tokens) {
    const raw = t.raw;
    if (t.type === "text") {
      // Block text (tight list items): `raw` doubles interior newlines; `text` is the source text, and
      // the raw's extra trailing newlines are the ones the lexer moved onto this token.
      const tt = t as Tokens.Text;
      if (!view.str.startsWith(tt.text, p)) throw new Refusal("a list item with indented code, or one the mapping could not place");
      if (tt.tokens) walkInline(tt.tokens, view.sub(p, p + tt.text.length), em);
      else emitText(view.sub(p, p + tt.text.length), em);
      p += tt.text.length;
      const trailing = raw.length - tt.text.length - countNL(tt.text);
      if (trailing < 0) throw new Refusal("a list item the mapping could not place");
      for (let k = 0; k < trailing; k++, p++) if (view.str[p] !== "\n") throw new Refusal("a list item the mapping could not place");
      continue;
    }
    if (!view.str.startsWith(raw, p)) {
      // reference definitions the lexer recorded without emitting tokens
      let q = p;
      for (;;) {
        const m = DEF_RE().exec(view.str.slice(q));
        if (!m) break;
        q += m[0].length;
        if (view.str.startsWith(raw, q)) break;
      }
      if (view.str.startsWith(raw, q)) p = q;
      else if (/^ *\t/.test(view.str.slice(p, p + 8))) throw new Refusal("a line that begins with a tab after its marker");
      else throw new Refusal(`a ${t.type} the mapping could not place`);
    }
    switch (t.type) {
      case "space": case "hr": break;
      case "heading": {
        const tt = t as Tokens.Heading;
        const off = headingTextOffset(raw, tt.text);
        walkInline(tt.tokens, view.sub(p + off, p + off + tt.text.length), em);
        break;
      }
      case "paragraph": {
        const tt = t as Tokens.Paragraph;
        if (!raw.startsWith(tt.text) || /[^\n]/.test(raw.slice(tt.text.length))) throw new Refusal("a paragraph the mapping could not place");
        walkInline(tt.tokens, view.sub(p, p + tt.text.length), em);
        break;
      }
      case "blockquote": {
        const tt = t as Tokens.Blockquote;
        walkBlocks(tt.tokens, suffixLineView(view.sub(p, p + raw.length), tt.text), em);
        break;
      }
      case "list": {
        const tt = t as Tokens.List;
        let q = p;
        for (const item of tt.items) {
          if (!view.str.startsWith(item.raw, q)) throw new Refusal("a list the mapping could not place");
          walkBlocks(item.tokens, suffixLineView(view.sub(q, q + item.raw.length), item.text), em);
          q += item.raw.length;
        }
        // the last item's raw is trimmed, and a single newline after the list is moved onto the list's raw
        while (q < p + raw.length && view.str[q] === "\n") q++;
        if (q !== p + raw.length) throw new Refusal("a list the mapping could not place");
        break;
      }
      case "code": {
        // shown by the renderer, refused by the mapping: a hole the selection may not touch
        const tt = t as Tokens.Code;
        em.holes.push({ reason: tt.codeBlockStyle === "indented" ? "an indented code block" : "a code block", startN: view.n(p), endN: view.n(p + raw.length) });
        em.putHole(tt.text, em.holes.length - 1);
        break;
      }
      case "table": {
        const tt = t as Tokens.Table;
        em.holes.push({ reason: "a table", startN: view.n(p), endN: view.n(p + raw.length) });
        const h = em.holes.length - 1;
        for (const cell of tt.header) em.putHole(plainInline(cell.tokens), h);
        for (const row of tt.rows) for (const cell of row) em.putHole(plainInline(cell.tokens), h);
        break;
      }
      case "frontMatter": {
        // one folded block over the YAML (md-config.ts): shown, never mapped; the fold's label is a control the walks skip
        const tt = t as FrontMatterToken;
        em.holes.push({ reason: "the front matter", startN: view.n(p), endN: view.n(p + raw.length) });
        em.putHole(tt.text, em.holes.length - 1);
        break;
      }
      case "footnoteDef": {
        // `[^id]: text` rendered in place (md-config.ts): line i of `text` is a suffix of raw line i (the marker, or a
        // continuation line's indent, removed), the blockquote's shape; the back link's label is a control the walks skip
        const tt = t as FootnoteDefToken;
        walkInline(tt.tokens, suffixLineView(view.sub(p, p + raw.length), tt.text), em);
        break;
      }
      case "callout": {
        // `> [!type] Title` and its body (md-config.ts): the `> ` prefixes come off as a blockquote's do; the title line is a
        // hole (the type marker is not shown, and a missing title is generated from the type), the body maps as blocks
        const tt = t as CalloutToken;
        const tv = suffixLineView(view.sub(p, p + raw.length), tt.text);
        const nl = tt.text.indexOf("\n");
        const bodyStart = nl < 0 ? tt.text.length : nl + 1;
        em.holes.push({ reason: "a callout's title", startN: view.n(p), endN: tv.n(bodyStart) });
        em.putHole(calloutTitle(tt), em.holes.length - 1);
        walkBlocks(tt.tokens, tv.sub(bodyStart, tt.text.length), em);
        break;
      }
      case "mathBlock": {
        // a display formula of its own: KaTeX's glyphs are skipped as a control (isControl), so the block has no text
        em.holes.push({ reason: "a formula", startN: view.n(p), endN: view.n(p + raw.length) });
        break;
      }
      case "html": throw new Refusal("an HTML block");
      default: throw new Refusal(`content of a kind the mapping does not handle (${t.type})`);
    }
    p += raw.length;
  }
}

/** N (the lexer's preprocessed text) and, unless N === source, the source offset of every N index
 *  (length N.length + 1; a "\n" from CRLF maps to the CR, the four spaces of a tab to the tab). */
function normalizeSource(source: string): { N: string; nStart: Int32Array | null } {
  if (!/\r|^ *\t/m.test(source)) return { N: source, nStart: null };
  const map: number[] = [];
  let N = "";
  // marked expands ONE run of tabs per line, the run right after the line's leading spaces
  // (`^( *)(\t+)`); a space after that run ends the expansion for the rest of the line.
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
    if (c === " ") { if (tabRun) { tabRun = false; } }
    else { spacesOnly = false; tabRun = false; }
    N += c; map.push(i);
  }
  map.push(source.length);
  return { N, nStart: Int32Array.from(map) };
}

type Block = {
  startN: number; endN: number;
  /** N index past the block's last non-newline character: the raw's trailing line feeds are its own line
   *  ending and, after that, blank lines a token swallows (a heading's, an hr's, a blockquote's single moved
   *  newline) — between blocks, not in one (renderedSpot's own-rows rule). */
  textEndN: number;
  chars: string; pos: number[]; holes: Hole[];
  refused: string | null;
  dom: DNode[];
  isHtml: boolean;
  /** an html block of comments alone (commentsOnly): it renders no node, so the pairing gives it none and reads past it
   *  (before this, an html block right before one lost its nodes to it: the resync accepted the comment block at once) */
  blank: boolean;
  tag: string | null;   // the element the token renders to, for resyncing past an html block
};
/** Whether an html token's raw is comments alone, whitespace between them, read left to right one comment at a time:
 *  each `<!--` is closed by the first `-->` after it (or is one of marked's two-character forms `<!-->` and `<!--->`),
 *  so a raw of many comments costs its length. marked lexes a line of comments and whatever follows them on that line
 *  as one html token, so the raw can hold any number of them. Not a regex: the anchored one this replaced,
 *  `^(?:\s*<!--[\s\S]*?-->)*\s*$`, tried every way of splitting the comments among its repeats whenever the raw ended
 *  in anything else (a tag, words, an unterminated comment) and doubled its time per comment (91 ms at 22, 144 s at
 *  30, on every Rendered paint), and it let a comment at each end of the line vouch for the words between them, which
 *  do render (the Slice 2 review, round 2: the next paragraph took their node and every block after paired one early). */
function commentsOnly(raw: string): boolean {
  let i = 0;
  for (;;) {
    while (i < raw.length && isWs(raw[i])) i++;
    if (i >= raw.length) return true;
    if (!raw.startsWith("<!--", i)) return false;
    i += 4;
    if (raw[i] === ">") { i++; continue; }
    if (raw.startsWith("->", i)) { i += 2; continue; }
    const close = raw.indexOf("-->", i);
    if (close < 0) return false;
    i = close + 3;
  }
}
type RenderedIndex = {
  source: string; shape: Shape; N: string; nStart: Int32Array | null;
  blocks: Block[];
  topNodes: DNode[]; topStart: number[]; total: number;   // every top-level child node with text, and its global index
  nodeBlock: Map<DNode, number>;
};

const nOf = (idx: { nStart: Int32Array | null }, n: number): number => (idx.nStart ? idx.nStart[n] : n);

/** The element marked's renderer emits for a top-level token (null when unknown or several). */
function tagOf(t: Token): string | null {
  switch (t.type) {
    case "heading": return "H" + (t as Tokens.Heading).depth;
    case "paragraph": case "text": return "P";
    case "list": return (t as Tokens.List).ordered ? "OL" : "UL";
    case "blockquote": return "BLOCKQUOTE";
    case "code": return "PRE";
    case "table": return "TABLE";
    case "hr": return "HR";
    // the Slice 4 constructs (md-config.ts), each ONE element in place
    case "frontMatter": return "DETAILS";
    case "footnoteDef": return "DIV";
    case "callout": return (t as CalloutToken).fold ? "DETAILS" : "BLOCKQUOTE";
    default: return null;   // mathBlock among them: a .katex-display span once filled, a code block when shown as source
  }
}

/** A top-level token laid over N: where it starts and ends, where its text ends (the raw's trailing line feeds
 *  excluded), and, from the first token whose raw could not be found at the position the walk assigned it, the
 *  reason, which every token from there on carries (the walk stops advancing). */
type Placed = { t: Token; startN: number; endN: number; textEndN: number; broken: string | null };
/** marked's top-level tokens placed over N, in order, `space` tokens dropped: a reference definition between two
 *  tokens is stepped over (never a token), else the walk resyncs on the next raw and leaves the gap unmapped. The one
 *  placement the rendered index and the source block table (sourceBlockSpans) share, so their blocks correspond. */
function placeTokens(N: string): { placed: Placed[]; lexError: string | null } {
  let tokens: Token[] = [];
  let lexError: string | null = null;
  try { tokens = Lexer.lex(N); } catch (e) { lexError = String((e as Error).message || e); }
  const placed: Placed[] = [];
  let pos = 0;
  let broken: string | null = lexError;
  for (const t of tokens) {
    if (broken === null && !N.startsWith(t.raw, pos)) {
      // a reference definition (never a token), else resync on the next raw and leave the gap unmapped
      for (;;) {
        const m = DEF_RE().exec(N.slice(pos));
        if (!m) break;
        pos += m[0].length;
        if (N.startsWith(t.raw, pos)) break;
      }
      if (!N.startsWith(t.raw, pos)) {
        const j = N.indexOf(t.raw, pos);
        if (j >= 0) pos = j; else broken = `a ${t.type} the mapping could not place`;
      }
    }
    if (t.type === "space") { if (broken === null) pos += t.raw.length; continue; }
    let textEndN = pos + t.raw.length;
    while (textEndN > pos && t.raw[textEndN - pos - 1] === "\n") textEndN--;
    placed.push({ t, startN: pos, endN: pos + t.raw.length, textEndN, broken });
    if (broken === null) pos += t.raw.length;
  }
  return { placed, lexError };
}

// ── the source half of the rendered index, kept for the last source ──────────────────────────────────
/** A block as the walk over the source alone answers it, before any root's pairing: everything in Block but `dom`
 *  (`refused` here is the walk's own, which the pairing may overwrite per root). */
type Walked = Omit<Block, "dom">;
/** What the rendered index reads from the source alone: N and its offset map, marked's top-level tokens placed over N
 *  and the block table they make (sourceBlockSpans), and, once a Rendered root has asked for it, each block's walk
 *  (Walked). One entry, keyed on the source string: the viewer shows one text at a time and paints it many times over
 *  new roots (a Rendered/Raw switch swaps the body's children and keeps the text; a reload of unchanged bytes does the
 *  same), and the reader's place seats through this table on every paint of a text view (reader-place.ts), so a fresh
 *  root used to pay the whole build again (the Slice 2 review, round 4: 5,000 paragraphs, 147 ms per fresh root, of
 *  which the lex was 48 ms and the walk about 70; the pairing, the root's own, about 22). The walk waits for the first
 *  Rendered root, so a Raw view (any non-markdown file) pays the lex alone, as before. */
type SourceTable = { source: string; N: string; nStart: Int32Array | null; lexError: string | null; placed: Placed[]; spans: SourceRange[]; walked: Walked[] | null };
let sourceCache: SourceTable | null = null;
function sourceTable(source: string): SourceTable {
  if (sourceCache && sourceCache.source === source) return sourceCache;
  const { N, nStart } = normalizeSource(source);
  const { placed, lexError } = placeTokens(N);
  const idx = { nStart };
  const spans: SourceRange[] = lexError !== null
    ? [{ start: 0, end: source.length }]
    : placed.map((p) => ({ start: nOf(idx, p.startN), end: nOf(idx, p.textEndN) }));
  sourceCache = { source, N, nStart, lexError, placed, spans, walked: null };
  return sourceCache;
}
/** The walk over each placed token (walkBlocks: the block's rendered text with a source position per character, its
 *  holes, its refusal), run once per source and kept on its table. */
function walkedBlocks(table: SourceTable): Walked[] {
  if (table.walked) return table.walked;
  const out: Walked[] = [];
  for (const { t, startN, endN, textEndN, broken } of table.placed) {
    const em = new Emitter();
    let refused: string | null = broken;
    if (refused === null) {
      try { walkBlocks([t], View.identity(table.N, 0), em, startN); }
      catch (e) { if (e instanceof Refusal) refused = e.message; else throw e; }
    }
    const isHtml = t.type === "html";
    out.push({ startN, endN, textEndN, chars: em.chars, pos: em.pos, holes: em.holes, refused, isHtml, blank: isHtml && commentsOnly(t.raw), tag: tagOf(t) });
  }
  if (table.lexError !== null) out.length = 0;
  table.walked = out;
  return out;
}

function analyzeRendered(root: DElement, source: string): RenderedIndex {
  const table = sourceTable(source);
  const { N, nStart, lexError } = table;
  // one Block per walked block for THIS root: the pairing below writes `dom`, and `refused` for an html block or a
  // mismatch, and another root over the same source starts from the walk's own answers
  const blocks: Block[] = walkedBlocks(table).map((w) => ({ ...w, dom: [] }));
  // ── the DOM's top-level nodes and their text
  const topNodes: DNode[] = [];
  const topStart: number[] = [];
  let total = 0;
  for (let i = 0; i < root.childNodes.length; i++) {
    const c = root.childNodes[i];
    if (!isElement(c) && !isText(c)) continue;
    topNodes.push(c); topStart.push(total);
    total += isText(c) ? c.data.length : textLenUnder(c, true, null);
  }
  const content = topNodes.filter((n) => isElement(n) || stripWs((n as DText).data) !== "");
  const nodeText = new Map<DNode, string>();
  for (const n of content) nodeText.set(n, stripWs(isText(n) ? n.data : textOf(n)));
  if (lexError !== null) {
    blocks.push({ startN: 0, endN: N.length, textEndN: N.length, chars: "", pos: [], holes: [], refused: `markdown the lexer could not parse (${lexError})`,
                  dom: content.slice(), isHtml: false, blank: false, tag: null });
  }
  // ── pair blocks with nodes, in order. Every token but `html` renders as exactly one element, so the
  //    pairing is 1:1 except across an html block, whose node count is unknown (zero for a comment, several
  //    for sibling tags, none of its text if DOMPurify dropped it). There the walk resyncs: it tries each
  //    candidate end and accepts the first from which the following blocks line up again — by text for a
  //    block the walk mapped, by element tag for one it refused — up to the next mapped block.
  const nodeBlock = new Map<DNode, number>();
  const fits = (blk: Block, node: DNode): boolean => {
    if (blk.refused !== null) return blk.tag === null || (isElement(node) && node.tagName.toUpperCase() === blk.tag);
    return nodeText.get(node) === blk.chars;
  };
  const runFits = (b: number, k: number): boolean => {
    for (; b < blocks.length; b++, k++) {
      const blk = blocks[b];
      if (blk.isHtml) { if (blk.blank) { k--; continue; } return true; }   // a comment block has no node; the next html block resyncs on its own
      if (k >= content.length) return blk.refused !== null && blk.chars.length === 0 ? true : false;
      if (!fits(blk, content[k])) return false;
      if (blk.refused === null && blk.chars.length > 0) return true;   // a mapped block with text confirms the run
    }
    return true;
  };
  let j = 0;
  for (let b = 0; b < blocks.length; b++) {
    const blk = blocks[b];
    if (lexError !== null) { for (const n of blk.dom) nodeBlock.set(n, b); break; }
    if (blk.isHtml) {
      blk.refused = blk.refused || "an HTML block";
      if (!blk.blank) {
        let jj = content.length;
        for (let k = j; k <= content.length; k++) if (runFits(b + 1, k)) { jj = k; break; }
        blk.dom = content.slice(j, jj);
        j = jj;
      }
    } else if (blk.refused !== null) {
      if (j < content.length) blk.dom = [content[j++]];
    } else if (blk.chars.length === 0) {
      if (j < content.length && nodeText.get(content[j]) === "") blk.dom = [content[j++]];
    } else if (j < content.length && nodeText.get(content[j]) === blk.chars) {
      blk.dom = [content[j++]];
    } else {
      blk.refused = "a block whose rendered text does not match the file";
      if (j < content.length) blk.dom = [content[j++]];
    }
    for (const n of blk.dom) nodeBlock.set(n, b);
  }
  return { source, shape: shapeOf(root, source), N, nStart, blocks, topNodes, topStart, total, nodeBlock };
}

const renderedCache = new WeakMap<object, RenderedIndex>();
function renderedIndex(root: DElement, source: string): RenderedIndex {
  const hit = renderedCache.get(root);
  if (hit && sameShape(hit.shape, root, source)) return hit;
  const idx = analyzeRendered(root, source);
  renderedCache.set(root, idx);
  return idx;
}

// ── the block table, for the reader's place (reader-place.ts) ─────────────────────────────────────────
// Three reads over the private table: the top-level blocks of a source as spans (sourceBlockSpans), which block a
// top-level rendered node stands for (renderedBlockIndex), and which elements a block renders as
// (renderedBlockElements). A REFUSED block answers all three (its node is paired by tag, and the reader's place
// needs an element to measure, not text to quote), where renderedSpot, built for a point inside the prose, answers
// null for one. A node the pairing could not place (whitespace between blocks, a node an html block's resync left
// over) is no block's, and the caller reads the next node.

/** The top-level blocks of `source` in order, each its source span (first character to the end of its text, the blank
 *  lines a token swallows after it excluded), from the same placement the rendered index pairs elements by, so block b
 *  here is block b there (renderedBlockIndex, renderedBlockElements). Markdown the lexer could not parse is one block
 *  over the whole text. For the reader's place (reader-place.ts): the blocks of the Raw view, which its rows alone do
 *  not show (a blank row between two paragraphs belongs to neither, one inside a fenced code block to the code block).
 *  The last source's table is kept (sourceTable): the viewer reads the same text once per scroll frame. */
export function sourceBlockSpans(source: string): SourceRange[] { return sourceTable(source).spans; }

/** The index, into sourceBlockSpans(source), of the top-level block that renders `node`, a child of `renderedRoot`;
 *  -1 when `node` is no block's (whitespace between blocks, a node an html block's resync left over). */
export function renderedBlockIndex(renderedRoot: Element, source: string, node: Node): number {
  const idx = renderedIndex(renderedRoot as unknown as DElement, source);
  const b = idx.nodeBlock.get(node as unknown as DNode);
  return b === undefined ? -1 : b;
}

/** The elements block `b` renders as, in order: one for most blocks, several for an html block of sibling tags, none
 *  for a comment or a block the sanitizer dropped. */
export function renderedBlockElements(renderedRoot: Element, source: string, b: number): Element[] {
  const idx = renderedIndex(renderedRoot as unknown as DElement, source);
  const blk = idx.blocks[b];
  return blk ? (blk.dom.filter((n) => isElement(n)) as unknown as Element[]) : [];
}

/** The top-level node holding global index g, and the index within it. */
function topAt(idx: RenderedIndex, g: number): { t: number; c: number } {
  let lo = 0, hi = idx.topNodes.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (idx.topStart[mid] <= g) lo = mid; else hi = mid - 1;
  }
  return { t: lo, c: g - idx.topStart[lo] };
}

/** Non-whitespace characters before index c of the node's text. */
function nonWsBefore(n: DNode, c: number): number {
  const s = isText(n) ? n.data : textOf(n);
  let k = 0;
  for (let i = 0; i < c && i < s.length; i++) if (!isWs(s[i])) k++;
  return k;
}

function srcRangeOf(idx: RenderedIndex, text: string): SourceRange | null {
  if (!text) return null;
  let i = idx.N.indexOf(text), len = text.length;
  if (i < 0) {
    const r = findExact(idx.N, text);
    if (!r) return null;
    i = r.start; len = r.end - r.start;
  }
  return { start: nOf(idx, i), end: nOf(idx, i + len) };
}

export function mapRenderedSelection(sel: SelLike, renderedRoot: Element, source: string): MapResult {
  const root = renderedRoot as unknown as DElement;
  if (sel.isCollapsed || !sel.anchorNode || !sel.focusNode) return refuse("Select some text to comment on.");
  const idx = renderedIndex(root, source);
  const a = boundaryIndex(root, sel.anchorNode as unknown as DNode, sel.anchorOffset, null);
  const f = boundaryIndex(root, sel.focusNode as unknown as DNode, sel.focusOffset, null);
  if (a === null || f === null) return refuse("The selection reaches outside the rendered text.");
  const snap = (x: number | "before" | "after") => (x === "before" ? 0 : x === "after" ? idx.total : x);
  const gs = Math.min(snap(a), snap(f)), ge = Math.max(snap(a), snap(f));
  if (gs >= ge || !idx.topNodes.length) return refuse("Select some text to comment on.");
  // the selected rendered text, for the Raw offer (computed only when a refusal needs it)
  let rawMemo: Partial<MapRefusal> | null = null;
  const rawExtra = (): Partial<MapRefusal> => {
    if (rawMemo) return rawMemo;
    let selected = "";
    for (const n of idx.topNodes) { selected += isText(n) ? n.data : textOf(n); }
    const rawRange = srcRangeOf(idx, selected.slice(gs, ge).trim());
    rawMemo = rawRange ? { rawHasQuote: true, rawRange } : { rawHasQuote: false };
    return rawMemo;
  };
  const blockExtra = (b: Block, startN?: number): Partial<MapRefusal> => {
    const off = nOf(idx, startN === undefined ? b.startN : startN);
    return { blockStartLine: rawOffsetToLine(source, off), blockStartOffset: off, ...rawExtra() };
  };
  // endpoint → (block, non-whitespace index); whitespace between blocks snaps to the nearest block edge
  // a block the selection can land on or touch: it shows text, or it is a refusal with an element on the
  // page. An html block that rendered nothing (a comment) is invisible and never in the way.
  const visible = (b: Block): boolean => b.chars.length > 0 || (b.refused !== null && b.dom.length > 0);
  const nextBlock = (from: number): number => { for (let b = from; b < idx.blocks.length; b++) if (visible(idx.blocks[b])) return b; return -1; };
  const prevBlock = (from: number): number => { for (let b = from; b >= 0; b--) if (visible(idx.blocks[b])) return b; return -1; };
  const locate = (g: number, isStart: boolean): { b: number; k: number } | null => {
    if (g >= idx.total) { const b = prevBlock(idx.blocks.length - 1); return b < 0 ? null : { b, k: idx.blocks[b].chars.length }; }
    const { t, c } = topAt(idx, g);
    const node = idx.topNodes[t];
    const b = idx.nodeBlock.get(node);
    if (b === undefined) {
      if (isText(node) && stripWs(node.data) === "") {
        // whitespace between blocks: the next block for a start, the previous for an end
        let nb = -1;
        for (let u = isStart ? t + 1 : t - 1; isStart ? u < idx.topNodes.length : u >= 0; isStart ? u++ : u--) {
          const bb = idx.nodeBlock.get(idx.topNodes[u]);
          if (bb !== undefined) { nb = bb; break; }
        }
        if (nb < 0) return null;
        return { b: nb, k: isStart ? 0 : idx.blocks[nb].chars.length };
      }
      return null;   // a node no block accounts for
    }
    return { b, k: nonWsBefore(node, c) };
  };
  const S = locate(gs, true), E = locate(ge, false);
  if (!S || !E) return refuse("The selection could not be matched to the file text.", rawExtra());
  let { b: bs, k: ks } = S;
  let { b: be, k: ke } = E;
  if (idx.blocks[bs].refused === null && ks >= idx.blocks[bs].chars.length) { bs = nextBlock(bs + 1); ks = 0; }
  if (be >= 0 && idx.blocks[be].refused === null && ke === 0) { be = prevBlock(be - 1); if (be >= 0) ke = idx.blocks[be].chars.length; }
  if (bs < 0 || be < 0) return refuse("The selection is only whitespace.", rawExtra());
  // a refused block anywhere in the span comes first: its text is what the person selected, whatever
  // the mapping knows about it
  for (let b = Math.min(bs, be); b <= Math.max(bs, be); b++) {
    const blk = idx.blocks[b];
    if (blk.refused !== null && visible(blk)) return refuse(`This selection touches ${blk.refused}; comment on it from the Raw view.`, blockExtra(blk));
  }
  if (bs > be || (bs === be && ks >= ke)) return refuse("The selection is only whitespace.", rawExtra());
  for (let b = bs; b <= be; b++) {
    const blk = idx.blocks[b];
    if (blk.refused !== null) continue;   // invisible (nothing rendered): its source travels inside the quote
    const from = b === bs ? ks : 0, to = b === be ? ke : blk.chars.length;
    for (let k = from; k < to; k++) {
      const p = blk.pos[k];
      if (p < 0) { const h = blk.holes[-p - 1]; return refuse(`This selection touches ${h.reason}; comment on it from the Raw view.`, blockExtra(blk, h.startN)); }
    }
  }
  const start = nOf(idx, idx.blocks[bs].pos[ks]);
  const end = nOf(idx, idx.blocks[be].pos[ke - 1]) + 1;
  return { ok: true, range: { start, end }, quote: source.slice(start, end) };
}

/** The (text node, offset) of the k-th non-whitespace character under `node`. */
function nthNonWs(node: DNode, k: number): { t: DText; off: number } | null {
  let seen = 0;
  for (const t of textNodes(node)) {
    for (let i = 0; i < t.data.length; i++) {
      if (isWs(t.data[i])) continue;
      if (seen === k) return { t, off: i };
      seen++;
    }
  }
  return null;
}

const BLOCK_CONTAINERS = new Set(["UL", "OL", "LI", "BLOCKQUOTE", "DIV", "TABLE", "THEAD", "TBODY", "TR", "SECTION", "ARTICLE", "BODY"]);
/** Whitespace-only text between block elements: marking it would paint a stray blob. */
const skipBlockWs = (t: DText): boolean => {
  if (stripWs(t.data) !== "") return false;
  const p = t.parentNode;
  return !!p && isElement(p) && BLOCK_CONTAINERS.has(p.tagName.toUpperCase());
};

/** Wrap from (startNode, startOff) to (endNode, endOff) — both text positions under `root`. */
function wrapBetween(root: DNode, s: { t: DText; off: number }, e: { t: DText; off: number },
                     className: string, data?: Record<string, string>): DElement[] {
  const all = textNodes(root);
  const i0 = all.indexOf(s.t), i1 = all.indexOf(e.t);
  if (i0 < 0 || i1 < 0 || i1 < i0) return [];
  const nodes = all.slice(i0, i1 + 1);
  let a = s.off, b = 0;
  for (let i = 0; i < nodes.length; i++) b += i < nodes.length - 1 ? nodes[i].data.length : e.off;
  return wrapSlices(nodes, a, b, className, data, skipBlockWs);
}

/** A string and, for each of its characters, the index in the string it was derived from: `text[i]` is
 *  `origin[map[i]]`, and `map` is strictly increasing. */
export type Mapped = { text: string; map: number[] };
/** One markup rule for stripMarkupMapped: every match is dropped, or, with `keep`, replaced by its first
 *  group, which begins `keep` characters into the match (the opening delimiter's length, so the group's
 *  characters keep their source indexes). All rules are global; the line-anchored ones match at most once. */
type MarkupRule = { re: RegExp; keep?: number };
/** Line-leading constructs the renderer consumes: blockquote markers, list bullets and task boxes, heading
 *  hashes (leading and closing). */
const MARKUP_LEAD: MarkupRule[] = [
  { re: /^\s{0,3}(?:>\s?)+/g },
  { re: /^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?/g },
  { re: /^\s*#{1,6}\s+/g },
  { re: /\s+#+\s*$/g },
];
/** A fence line renders nothing of its own. */
const MARKUP_FENCE = /^\s*(`{3,}|~{3,})/;
/** Inline constructs: images (dropped whole), link labels, autolinks, emphasis pairs, code backticks,
 *  escapes, and a hard break's trailing blanks or backslash. */
const MARKUP_INLINE: MarkupRule[] = [
  { re: /!\[[^\]]*\]\([^)]*\)/g },
  { re: /\[([^\]]*)\]\([^)]*\)/g, keep: 1 },
  { re: /\[([^\]]*)\]\[[^\]]*\]/g, keep: 1 },
  { re: /<(https?:\/\/[^>]+)>/g, keep: 1 },
  { re: /\*\*(.+?)\*\*/g, keep: 2 },
  { re: /(?<!\w)__(.+?)__(?!\w)/g, keep: 2 },
  { re: /\*(.+?)\*/g, keep: 1 },
  { re: /(?<!\w)_(.+?)_(?!\w)/g, keep: 1 },
  { re: /~~(.+?)~~/g, keep: 2 },
  { re: /`+/g },
  { re: /\\([\\`*_{}[\]()#+\-.!>~|])/g, keep: 1 },
  { re: /(\s{2,}|\\)$/g },
];
/** `m` with one rule applied, its map carried through: what String.replace does, keeping every surviving
 *  character's origin. */
function applyMarkupRule(m: Mapped, rule: MarkupRule): Mapped {
  let text = "";
  const map: number[] = [];
  const take = (a: number, b: number) => { text += m.text.slice(a, b); for (let i = a; i < b; i++) map.push(m.map[i]); };
  let last = 0;
  for (const hit of m.text.matchAll(rule.re)) {
    const at = hit.index as number;
    take(last, at);
    if (rule.keep !== undefined) {
      const g = hit[1], gs = at + rule.keep;
      // the group must sit right after the opening delimiter, else the map would lie about its origin
      if (m.text.slice(gs, gs + g.length) !== g) throw new Error("anchor-map: a markup rule's group is not at its delimiter's length");
      take(gs, gs + g.length);
    }
    last = at + hit[0].length;
  }
  take(last, m.text.length);
  return { text, map };
}

/**
 * Inline markup a source slice carries that the rendered text does not (for the fallback matcher), applied
 * line by line, with every surviving character mapped back to its index in `s`. The text is what
 * stripMarkup returns; the map is what lets the fallback tell WHICH occurrence of a stripped quote in a
 * block's source is the one the comment's or change's range covers, when the quote carries markup of its
 * own (a code span in a table cell, a bold word) and its plain text recurs in the block.
 */
export function stripMarkupMapped(s: string): Mapped {
  let text = "";
  const map: number[] = [];
  const lines = s.split("\n");
  let lineStart = 0;
  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i];
    if (i > 0) { text += "\n"; map.push(lineStart - 1); }   // the line ending the split consumed
    let m: Mapped = { text: ln, map: Array.from({ length: ln.length }, (_, j) => lineStart + j) };
    for (const r of MARKUP_LEAD) m = applyMarkupRule(m, r);
    if (MARKUP_FENCE.test(m.text)) m = { text: "", map: [] };
    else for (const r of MARKUP_INLINE) m = applyMarkupRule(m, r);
    text += m.text;
    for (const x of m.map) map.push(x);
    lineStart += ln.length + 1;
  }
  return { text, map };
}
const stripMarkup = (q: string): string => stripMarkupMapped(q).text;

export function paintRendered(renderedRoot: Element, source: string, range: SourceRange, className: string,
                              data?: Record<string, string>): Element[] | null {
  const root = renderedRoot as unknown as DElement;
  const idx = renderedIndex(root, source);
  // ── the exact path: emitted characters whose source offset lies in the range
  let first: { b: number; k: number } | null = null, last: { b: number; k: number } | null = null;
  for (let b = 0; b < idx.blocks.length; b++) {
    const blk = idx.blocks[b];
    if (blk.refused !== null || !blk.dom.length) continue;
    const bs = nOf(idx, blk.startN), be = nOf(idx, blk.endN);
    if (be <= range.start || bs >= range.end) continue;
    for (let k = 0; k < blk.pos.length; k++) {
      const p = blk.pos[k];
      if (p < 0) continue;
      const s = nOf(idx, p);   // one source character: emitted text is never a tab expansion or a line ending
      if (s >= range.start && s < range.end) { if (!first) first = { b, k }; last = { b, k }; }
    }
  }
  if (first && last) {
    const s = nthNonWs(idx.blocks[first.b].dom[0], first.k);
    const e = nthNonWs(idx.blocks[last.b].dom[0], last.k);
    if (s && e) {
      const marks = wrapBetween(root, s, { t: e.t, off: e.off + 1 }, className, data);
      if (marks.length) return marks as unknown as Element[];
    }
  }
  // ── the fallback: a whitespace-tolerant match of the quote stripped of its markup, inside the blocks
  //    the range overlaps (a refused block, typically), else anywhere in the rendered text
  const raw = source.slice(range.start, range.end);
  const quote = stripMarkup(raw);
  if (stripWs(quote) === "") return null;
  let scope: DNode[] = [];
  let scopeStart = source.length, scopeEnd = 0;   // the source span the scope's blocks cover
  for (const blk of idx.blocks) {
    const bs = nOf(idx, blk.startN), be = nOf(idx, blk.endN);
    if (be > range.start && bs < range.end) {
      scope.push(...blk.dom);
      scopeStart = Math.min(scopeStart, bs); scopeEnd = Math.max(scopeEnd, be);
    }
  }
  if (!scope.length) { scope = idx.topNodes.slice(); scopeStart = 0; scopeEnd = source.length; }
  // the hay is the scope's text with the newline between a wrapped code block's rows put back (codeRuns, above): a
  // quote across two code lines holds one, and the rows' text nodes alone do not
  const nodes: DText[] = [];
  const gaps: number[] = [];   // where in the hay the row newlines sit; they are no text node's characters
  let hay = "";
  for (const n of scope) for (const r of codeRuns(n)) { if (r.node) { nodes.push(r.node); hay += r.text; } else { gaps.push(hay.length); hay += r.text; } }
  const inNodes = (i: number): number => { let g = 0; for (const p of gaps) { if (p < i) g++; else break; } return i - g; };
  const hits = occurrences(hay, quote);
  if (!hits.length) return null;
  // Which occurrence: the range's ORDINAL among the scope's own occurrences of the quote, in the scope's
  // source stripped the same way (stripMarkupMapped). A change's text is short (a word, a number), and a
  // table or a code block repeats such tokens; the first occurrence would mark an unchanged cell and report
  // it painted, the wrong passage under "Scroll to the change". The count is taken over the STRIPPED source,
  // not the raw slice: a comment's quote may carry markup of its own (`` `GET /notes` `` in a table cell,
  // `**cache**`) whose plain text recurs in the block, and the raw slice occurs once where the rendering
  // shows its text twice. The ordinal is exact when the rendering shows the text as many times as the
  // stripped source holds it, so the counts must agree, else nothing is painted and the comment or change
  // keeps its card (and Reveal). The range's own occurrence is the one whose characters map back inside it.
  const scopeSrc = stripMarkupMapped(source.slice(scopeStart, scopeEnd));
  const srcHits = occurrences(scopeSrc.text, quote);
  if (srcHits.length !== hits.length) return null;
  const k = srcHits.findIndex((h) => scopeStart + scopeSrc.map[h.start] >= range.start && scopeStart + scopeSrc.map[h.end - 1] < range.end);
  if (k < 0) return null;
  const hit = hits[k];
  const marks = wrapSlices(nodes, inNodes(hit.start), inNodes(hit.end), className, data, skipBlockWs);
  return marks.length ? (marks as unknown as Element[]) : null;
}

/** `s` with every whitespace run collapsed to one space and its edges trimmed, and `map[i]` the index in `s`
 *  of normalized character i (a run's space sits at the run's end). This is findExact's own view of a
 *  string (comments.ts), so the fallback keeps the tolerance it had; local because comments.ts keeps the
 *  helper private, and one pass per string keeps the enumeration below linear in the occurrences. */
function wsView(s: string): { norm: string; map: number[] } {
  let norm = "";
  const map: number[] = [];
  let inWs = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (isWs(c)) { inWs = true; continue; }
    if (inWs && norm.length) { norm += " "; map.push(i); }
    inWs = false;
    norm += c;
    map.push(i);
  }
  return { norm, map };
}

/** Every whitespace-tolerant occurrence of `needle` in `hay`, as [start, end) in `hay`, in order; a start is
 *  the match's first non-blank character, and overlapping matches count separately. The first one is what
 *  findExact(hay, needle) returns. */
function occurrences(hay: string, needle: string): { start: number; end: number }[] {
  const out: { start: number; end: number }[] = [];
  const target = wsView(needle).norm;
  if (!target) return out;
  const { norm, map } = wsView(hay);
  for (let at = norm.indexOf(target); at >= 0; at = norm.indexOf(target, at + 1)) {
    out.push({ start: map[at], end: map[at + target.length - 1] + 1 });
  }
  return out;
}

// ── change marks (plans/file-review.md Slice 2; contract D4) ───────────────────────────────────────
//
// A session's pending changes arrive as hunks in CURRENT-text coordinates: an `ins` occupies
// [curFrom, curTo) and its old text is empty; a `del` is a point (curFrom === curTo) whose old text is
// gone from the file; a `sub` is both, the new text at [curFrom, curTo) and the old text beside it.
// Raw view paints all three. Rendered paints all three too: the new text of an ins or sub wrapped, and a
// deletion — or a sub's old text — as the same zero-width point Raw draws, placed in the prose through the
// index map (paintRenderedPoint; the inline-display follow-on, 2026-09-07). Only a change the map cannot
// place there (a refused block, a hole, a blank line between blocks) is left to its card, whose Reveal
// switches to Raw.
//
// The deleted text is NOT in the file, so it must never become a text node under a `.fv-cl` row: every
// Raw walk above (rawIndex's row verification, boundaryIndex's counting, the selection self-check) reads
// the rows' text nodes as the source line. A deletion is therefore an EMPTY inline element at its offset
// whose visible label is CSS-generated from `data-fc-text` (`.fc-del::before { content: attr(...) }`);
// generated content is not a node and never enters a selection, the same way the row number is drawn.
//
// The author's chip (the plan's UX: in Raw, each change carries the author's session chip in the
// session's colour, the `▍web` beside the marked text) is drawn the same way: the LAST element painted
// for a change in Raw carries `data-fc-chip="<label>"`, for the sheet's `::after` to draw as generated
// content beside the text, coloured by the same `--fc-author`. One chip per change, after its text,
// whatever the change's shape: after the last row's slice of an insertion, on a deletion's point, after
// a substitution's new text. No element is added for it and it carries no data-act of its own, so the
// panel's count of `[data-act="fcchange"]` elements per change is unchanged and the mark beside it stays
// the one control. Rendered marks carry no chip (the plan gives the chip to Raw).

export type ChangePaint = {
  id: string;
  kind: "ins" | "del" | "sub";
  curFrom: number;
  curTo: number;
  oldText: string;
  /** The sidecar's author label (the session's name when it wrote the change). */
  author: string;
  /** The chip's label when the caller has a better one than `author`: the session's CURRENT name from the
   *  panel's colour map (a renamed session), or the neutral label the plan gives an author with no live
   *  match. Absent, the chip reads `author`. */
  label?: string;
  /** The change's new text, when the caller has it (a hunk's `newText`). With it present the painters
   *  verify the source slice at [curFrom, curTo) equals it before painting anything: hunks are computed
   *  over the host's string, and a file whose bytes the browser decodes differently (a BOM the fetch
   *  strips) would otherwise paint the wrong passages. One failure refuses the whole batch (offsetsIndex). */
  newText?: string;
};

/** The struck label of a deletion: the old text with the line endings the rows themselves show (the HTML
 *  parser turns a CR into an LF), capped at 80 characters with an ellipsis when cut; the card carries the
 *  whole text. A text with no visible character — a removed blank line, `track-edit --old $'\n\n' --new ''` —
 *  would hand the sheet's `::before` a string of line feeds and nothing to draw: the point sat there with a
 *  2px underline and no glyph, and the row grew by a blank visual line (the review, 2026-09-06). Such a
 *  label shows one ¶ per line ending instead, the mark a text editor draws for the same thing; spaces and
 *  tabs keep their own width and are left as they are (the Raw rows are pre-wrap; the Rendered point carries
 *  that white-space itself when its label is nothing else — renderedPointStyles). A label with any visible
 *  character keeps its line endings: the rows below show what was removed as it read. */
export const DEL_LABEL_MAX = 80;
export const PILCROW = "¶";
export function deletionLabel(oldText: string): string {
  let t = oldText.replace(/\r\n?/g, "\n");
  if (!/\S/.test(t)) t = t.replace(/\n/g, PILCROW);
  if (t.length <= DEL_LABEL_MAX) return t;
  let cut = DEL_LABEL_MAX - 1;
  if (/[\uD800-\uDBFF]/.test(t[cut - 1])) cut--;   // never split a surrogate pair
  return t.slice(0, cut) + "…";
}

/** Inline styles on a mark, `{"--fc-author": "<css color>"}` and the like, written as one `style`
 *  attribute so the structural DOM needs no CSSOM. A pair whose name is not a property or custom
 *  property name, or whose value could end the declaration, is skipped: the mark still paints, in the
 *  sheet's fallback colour. */
function applyStyles(el: DElement, styles: Record<string, string> | undefined): void {
  if (!styles) return;
  const decls: string[] = [];
  for (const k of Object.keys(styles)) {
    const v = styles[k];
    if (!/^-{0,2}[A-Za-z_][\w-]*$/.test(k) || typeof v !== "string" || /[;{}\r\n]/.test(v)) continue;
    decls.push(k + ": " + v);
  }
  if (decls.length) el.setAttribute("style", decls.join("; ") + ";");
}

const CHANGE_ACT = "fcchange";
const changeData = (c: ChangePaint): Record<string, string> => ({ act: CHANGE_ACT, id: c.id, author: c.author });

/** Whether a change's offsets index `source`: inside the text, a `del` a point, and, when the caller
 *  supplied the new text, exactly that text at [curFrom, curTo). The painters apply it to the BATCH: the
 *  hunks were computed over one string, so one offset that does not index `source` means none of them
 *  do, and a deletion alone has no text to check. Then nothing is painted and every change is left to
 *  its card (the panel sees no painted id), rather than some marks landing on the wrong passages. */
function offsetsIndex(c: ChangePaint, source: string): boolean {
  if (!(c.curFrom >= 0 && c.curFrom <= c.curTo && c.curTo <= source.length)) return false;
  if (c.kind === "del" && c.curFrom !== c.curTo) return false;
  return c.newText === undefined || source.slice(c.curFrom, c.curTo) === c.newText;
}
const batchIndexes = (changes: ChangePaint[], source: string): boolean => changes.every((c) => offsetsIndex(c, source));

/** The point element itself — a zero-width `span` with the change's data attributes, the label in
 *  `data-fc-text` for the sheet's `::before` to draw, and the inline styles — shared by the Raw and the
 *  Rendered painters so the two views' points are one element, byte for byte. */
function makePoint(doc: DElement["ownerDocument"], className: string, data: Record<string, string>, label: string,
                   styles: Record<string, string> | undefined): DElement {
  if (!doc) throw new Error("anchor-map: node has no ownerDocument");
  const m = doc.createElement("span");
  m.setAttribute("class", className);
  for (const k of Object.keys(data)) m.setAttribute("data-" + k, data[k]);
  m.setAttribute("data-fc-text", label);
  applyStyles(m, styles);
  return m;
}

// ── where a point at a mark's boundary goes ─────────────────────────────────────────────────────────
//
// A mark's extent is its text, so a point at either end of a painter's mark — a change's `fc-ins`, a
// comment's `fc-hl`, the composer's `fc-presel` — is not in it: a deletion right after an insertion sits
// after the insertion's mark, as its sibling, and one right before it sits before the mark; a substitution
// whose tint begins a comment highlight has its point before the highlight. This holds in both views and
// whichever mark was painted first, however the marks nest. Without it the placement followed the paint
// order: with the insertion painted first, the "after" position was the last text node INSIDE its mark,
// and the point became the mark's last child, so in Rendered the struck old text wore the insertion's tint
// and author underline as if it were part of the inserted run, while Raw, whose insertPointAt puts the
// same offset before the NEXT text node, showed it after the tint (the review, 2026-09-07); at a mark's
// start, and at a row's end in Raw, the point nested or not by the order the changes came in. The
// renderer's own inline elements are left alone: a point after the last word of a `<strong>` stays in it.
//
// Points at one offset keep the order they were painted in — a later point goes after the points already
// there — as Raw places a later point before the next text node, after the earlier ones.

/** The painters' own wrappers, which a point climbs out of at their edges. */
const isPaintMark = (n: DNode): boolean => hasClass(n, "fc-ins") || hasClass(n, "fc-hl") || hasClass(n, "fc-presel");
const isPoint = (n: DNode): boolean => hasClass(n, "fc-del");
const indexIn = (parent: DNode, n: DNode): number => {
  let i = 0;
  while (i < parent.childNodes.length && parent.childNodes[i] !== n) i++;
  return i;
};

/** Insert `m` right after text node `t` — outside every painter's mark that ends with `t`, and after the
 *  points already at that position. */
function insertAfterText(t: DText, m: DElement): void {
  let n: DNode = t;
  while (n.parentNode && isPaintMark(n.parentNode) && n.parentNode.childNodes[n.parentNode.childNodes.length - 1] === n) n = n.parentNode;
  const parent = n.parentNode as DElement;
  let i = indexIn(parent, n) + 1;
  while (i < parent.childNodes.length && isPoint(parent.childNodes[i])) i++;
  parent.insertBefore(m, i < parent.childNodes.length ? parent.childNodes[i] : null);
}

/** Insert `m` right before node `n` (a text node, or a mark whose text begins at the offset) — outside every
 *  painter's mark that begins with `n`, and so after the points already before it. */
function insertBeforeNode(n: DNode, m: DElement): void {
  while (n.parentNode && isPaintMark(n.parentNode) && n.parentNode.childNodes[0] === n) n = n.parentNode;
  (n.parentNode as DElement).insertBefore(m, n);
}

/** Insert `m` at character `col` of the concatenated text of `nodes` (consecutive text nodes): before the
 *  node the column begins, inside it after a split, or right after the last node when the column is the
 *  text's end — at a painter's mark's edge, outside the mark (insertBeforeNode / insertAfterText). False
 *  when there are no nodes to place it among. */
function insertPointAt(nodes: DText[], col: number, m: DElement): boolean {
  let cum = 0;
  for (const t of nodes) {
    const len = t.data.length;
    if (col < cum + len) {
      if (col === cum) insertBeforeNode(t, m);
      else (t.parentNode as DElement).insertBefore(m, t.splitText(col - cum));
      return true;
    }
    cum += len;
  }
  if (!nodes.length) return false;
  insertAfterText(nodes[nodes.length - 1], m);
  return true;
}

/**
 * A zero-width marker element at source `offset` in the Raw view: inserted between the row's text nodes,
 * splitting one when the offset falls inside it, never adding a text node. The label is carried in
 * `data-fc-text` for the sheet's `::before` to draw. An offset on a line ending sits at the end of its
 * row; the end of the file sits at the end of the last row; at the edge of another change's mark the point
 * sits outside the mark (the boundary rule above insertAfterText). Returns null when the rows do not match
 * `source` (nothing is trusted then) or the file has no rows.
 */
export function paintRawPoint(codeRoot: Element, source: string, offset: number, className: string,
                              data: Record<string, string>, label: string, styles?: Record<string, string>): Element | null {
  const idx = rawIndex(codeRoot as unknown as DElement, source);
  if ("error" in idx || !idx.rows.length) return null;
  let lo = 0, hi = idx.rows.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (idx.rows[mid].srcStart <= offset) lo = mid; else hi = mid - 1;
  }
  const row = idx.rows[lo];
  let col = Math.max(0, Math.min(offset - row.srcStart, row.text.length));
  // a CRLF row's DOM text ends in the "\n" the parser made of its CR: an offset on the line ending sits
  // before it, at the end of the visible text, so the label never opens a new line under the row
  if (col === row.text.length && col > 0 && row.text[col - 1] === "\n") col--;
  const m = makePoint(row.el.ownerDocument, className, data, label, styles);
  if (insertPointAt(textNodes(row.el), col, m)) return m as unknown as Element;
  // an empty row: the point goes into the row's text cell (its `.fv-ct`), else the row itself
  let host: DElement = row.el;
  for (let i = 0; i < row.el.childNodes.length; i++) {
    const c = row.el.childNodes[i];
    if (isElement(c) && hasClass(c, "fv-ct")) { host = c; break; }
  }
  host.appendChild(m);
  return m as unknown as Element;
}

/** The source offsets a block's own rows hold, as [lo, hi): the block's text lines through the line ending
 *  of the last of them (a deletion on that ending sits after the block's last character, as Raw puts it at
 *  the row's end), and the end of the file when it comes right after that ending (Raw: the end of the file
 *  sits at the end of the last row). The line feeds a token's raw carries after that are blank lines between
 *  blocks — marked's heading, setext heading and hr regexes swallow every trailing newline, and its lexer
 *  moves a lone newline onto the token before it — and hold nothing, as a `space` token's do (the plan: a
 *  blank line between blocks leaves the change unpainted). Before this, the raw's extent decided: a deletion
 *  on the blank line under a heading was struck inside the heading, after its last word, while the same
 *  blank line under a paragraph, a `space` token, was left unpainted (the review, 2026-09-07). */
function ownRows(idx: RenderedIndex, b: Block): { lo: number; hi: number } {
  const lo = nOf(idx, b.startN);
  if (b.textEndN >= idx.N.length) return { lo, hi: idx.source.length + 1 };   // the block's text ends the file
  const hi = nOf(idx, b.textEndN + 1);                                        // past the last row's line ending
  return { lo, hi: b.textEndN + 1 === idx.N.length ? hi + 1 : hi };          // …and the end of the file right after it
}

/** Where source `offset` falls in the rendered text: the text node and the offset in it BEFORE which a
 *  point at that source position sits. The block is the mapped (not refused) one whose own rows hold the
 *  offset (ownRows: its text lines, the last one's line ending, the end of the file right after it) — no
 *  two blocks' rows overlap, so where one block's raw ends exactly as the next begins the one that begins
 *  there has the offset. Inside the block the point goes before the first emitted character at or past
 *  the offset — or right after the last one before it, when the offset follows that character directly
 *  (a deletion at a word's end sits against the word, not past the space after it) or nothing follows.
 *  Null when no block's rows hold the offset (a blank line between blocks, whichever token's raw carries
 *  it), the block is refused or has no element, or the offset sits inside a hole (a nested code block or
 *  table the renderer shows but the mapping does not place): a point there would land beside the wrong
 *  words, so the change keeps its card and Reveal instead. */
function renderedSpot(idx: RenderedIndex, offset: number): { t: DText; off: number } | null {
  let blk: Block | null = null;
  for (const b of idx.blocks) {
    const { lo, hi } = ownRows(idx, b);
    if (lo <= offset && offset < hi) { blk = b; break; }
  }
  if (!blk || blk.refused !== null || !blk.dom.length) return null;
  // j: the last mapped character before the offset; k: the first at or past it. The entries between them,
  // if any, are hole characters (mapped characters are in source order, the Emitter's own rule).
  let j = -1, k = -1;
  for (let i = 0; i < blk.pos.length; i++) {
    const p = blk.pos[i];
    if (p < 0) continue;
    if (nOf(idx, p) < offset) j = i; else { k = i; break; }
  }
  if (j < 0 && k < 0) return null;   // a block with no mapped text
  const gapFrom = j + 1, gapTo = k < 0 ? blk.pos.length : k;
  let after: boolean;
  if (gapTo > gapFrom) {
    // hole characters between the two: the point belongs before the hole or after it, never inside
    const first = blk.holes[-blk.pos[gapFrom] - 1], last = blk.holes[-blk.pos[gapTo - 1] - 1];
    if (first && j >= 0 && offset <= nOf(idx, first.startN)) after = true;
    else if (last && k >= 0 && offset >= nOf(idx, last.endN)) after = false;
    else return null;
  } else if (k < 0) after = true;
  else if (j < 0) after = false;
  else after = nOf(idx, blk.pos[j]) + 1 === offset && nOf(idx, blk.pos[k]) !== offset;
  if (!after) return nthNonWs(blk.dom[0], k);
  const at = nthNonWs(blk.dom[0], j);
  return at ? { t: at.t, off: at.off + 1 } : null;
}

/**
 * The Rendered view's twin of paintRawPoint: the same zero-width element, placed in the rendered text at
 * the position the index map gives source `offset` (renderedSpot), splitting a text node when the offset
 * falls inside one and never adding a text node, so mapRenderedSelection and paintRendered read the body
 * as before. At the edge of another change's mark the point sits outside the mark, as in Raw (the
 * boundary rule above insertAfterText). Returns null when the offset cannot be placed (a refused block, a
 * hole, a blank line between blocks — a `space` token's or one a heading's raw swallowed; ownRows): the
 * change stays unpainted and keeps its card.
 */
export function paintRenderedPoint(renderedRoot: Element, source: string, offset: number, className: string,
                                   data: Record<string, string>, label: string, styles?: Record<string, string>): Element | null {
  const root = renderedRoot as unknown as DElement;
  const spot = renderedSpot(renderedIndex(root, source), offset);
  if (!spot) return null;
  const m = makePoint(root.ownerDocument, className, data, label, styles);
  const parent = spot.t.parentNode as DElement | null;
  if (!parent) return null;
  if (spot.off <= 0) insertBeforeNode(spot.t, m);
  else if (spot.off >= spot.t.data.length) insertAfterText(spot.t, m);
  else parent.insertBefore(m, spot.t.splitText(spot.off));
  return m as unknown as Element;
}

/** The author chip's label (the panel's own fallback order: the caller's label, the sidecar's author, else
 *  the neutral word). */
export const chipLabel = (c: ChangePaint): string => c.label || c.author || "unknown";
const CHIP_ATTR = "data-fc-chip";

/**
 * Paint pending changes over the Raw rows. `ins`: the new text wrapped in `mark.fc-ins`, one mark per
 * text-node slice, so a range crossing rows paints each row's slice. `del`: a `span.fc-del` point at
 * curFrom labelled with the old text (deletionLabel). `sub`: the point first, then the wrap. Every
 * painted element carries data-act="fcchange", data-id, data-author, and the inline styles `stylesFor`
 * returns for the change (`{"--fc-author": colour}` colours the mark by session); the LAST element of
 * each change also carries `data-fc-chip` with the author's chip label (chipLabel), the sheet's generated
 * content beside the text. Returns every element painted, so the caller reads which ids got paint from
 * the elements' data-id; a batch whose offsets do not index `source` (offsetsIndex) paints nothing and
 * returns [].
 */
export function paintChangesRaw(codeRoot: Element, source: string, changes: ChangePaint[],
                                stylesFor: (c: ChangePaint) => Record<string, string>): Element[] {
  const out: Element[] = [];
  if (!batchIndexes(changes, source)) return out;
  for (const c of changes) {
    const data = changeData(c);
    const styles = stylesFor(c);
    const mine: Element[] = [];
    if (c.kind === "del" || c.kind === "sub") {
      const p = paintRawPoint(codeRoot, source, c.curFrom, "fc-del", data, deletionLabel(c.oldText), styles);
      if (p) mine.push(p);
    }
    if (c.kind === "ins" || c.kind === "sub") {
      const marks = paintRaw(codeRoot, source, { start: c.curFrom, end: c.curTo }, "fc-ins", data);
      for (const m of marks) { applyStyles(m as unknown as DElement, styles); mine.push(m); }
    }
    if (mine.length) (mine[mine.length - 1] as unknown as DElement).setAttribute(CHIP_ATTR, chipLabel(c));
    for (const m of mine) out.push(m);
  }
  return out;
}

/** The inline styles of a Rendered point: the caller's, plus the Raw rows' `white-space: pre-wrap` when the label
 *  has no visible character. deletionLabel leaves spaces and tabs as they are, and the Raw rows show them at
 *  their width; a rendered block's white-space is normal, and the sheet's generated content follows it, so a
 *  label of one space beside a space that stayed (a doubled space a session collapsed) collapsed to nothing —
 *  a 0px point with no struck mark, no underline and nothing to hover or tap, while the painter reported it
 *  shown and its card offered a scroll to it (the review, 2026-09-07). With the rows' white-space on the point
 *  the label keeps its width in Rendered as in Raw; the sheets need no rule, and a label with a visible
 *  character keeps the block's white-space, which folds a multi-line label onto its line. */
function renderedPointStyles(label: string, styles: Record<string, string>): Record<string, string> {
  return /\S/.test(label) ? styles : { ...styles, "white-space": "pre-wrap" };
}

/**
 * Paint pending changes over the Rendered view: an `ins` or `sub` through paintRendered over its new
 * text (the source-offset path, the text-match fallback inside a refused block), class `fc-ins`, with the
 * same data attributes and styles as the Raw marks; a `del` as the Raw view's zero-width `span.fc-del`
 * point, placed through the index map (paintRenderedPoint) and labelled with the old text (deletionLabel);
 * a `sub` as that point immediately before its tint, wherever the tint was found (and before a highlight the
 * tint begins: the boundary rule above insertAfterText), so the struck old text and the new read together as
 * they do in Raw. No chip: the plan gives the author chip to the Raw view. A
 * point whose label has no visible character carries the Raw rows' white-space (renderedPointStyles), so a
 * removed space is a struck space here too and not a 0px point the block's white-space collapsed.
 * Returns which ids got paint and which did not — a deletion whose offset the map cannot place (a refused
 * block, a hole), an insertion whose text is not on the page — so the panel can mark the rest card-only;
 * a batch whose offsets do not index `source` (offsetsIndex) paints nothing and reports every id unpainted.
 */
export function paintChangesRendered(renderedRoot: Element, source: string, changes: ChangePaint[],
                                     stylesFor: (c: ChangePaint) => Record<string, string>): { painted: string[]; unpainted: string[] } {
  const painted: string[] = [], unpainted: string[] = [];
  if (!batchIndexes(changes, source)) return { painted, unpainted: changes.map((c) => c.id) };
  for (const c of changes) {
    const data = changeData(c);
    if (c.kind === "del") {
      const label = deletionLabel(c.oldText);
      const p = paintRenderedPoint(renderedRoot, source, c.curFrom, "fc-del", data, label, renderedPointStyles(label, stylesFor(c)));
      (p ? painted : unpainted).push(c.id);
      continue;
    }
    if (c.curFrom === c.curTo) { unpainted.push(c.id); continue; }
    const marks = paintRendered(renderedRoot, source, { start: c.curFrom, end: c.curTo }, "fc-ins", data);
    if (!marks || !marks.length) { unpainted.push(c.id); continue; }
    const styles = stylesFor(c);
    for (const m of marks) applyStyles(m as unknown as DElement, styles);
    if (c.kind === "sub") {
      const first = marks[0] as unknown as DElement;
      const label = deletionLabel(c.oldText);
      if (first.parentNode) insertBeforeNode(first, makePoint(first.ownerDocument, "fc-del", data, label, renderedPointStyles(label, styles)));
    }
    painted.push(c.id);
  }
  return { painted, unpainted };
}

/** Adjacent text nodes under `p` merged and empty ones dropped (Node.normalize for one parent), so the
 *  splits a paint made close back up. */
function mergeText(p: DElement): void {
  let i = 0;
  while (i < p.childNodes.length) {
    const c = p.childNodes[i];
    if (!isText(c)) { i++; continue; }
    if (c.data === "") { p.removeChild(c); continue; }
    while (i + 1 < p.childNodes.length && isText(p.childNodes[i + 1])) {
      const next = p.childNodes[i + 1] as DText;
      c.data += next.data;
      p.removeChild(next);
    }
    i++;
  }
}

/**
 * Remove every change mark under `root`: an `fc-ins` wrapper is unwrapped (its text nodes go back in
 * its place) and an `fc-del` point is removed, then the parent's text nodes are merged, so the DOM is
 * what it was before paintChangesRaw / paintChangesRendered ran. Comment highlights (`fc-hl`,
 * `fc-presel`) are left alone, nested either way round.
 */
export function unpaintChanges(root: Element): void {
  const marks: DElement[] = [];
  const visit = (n: DNode) => {
    if (isText(n)) return;   // a text node has no children (and a test stand-in may give it no childNodes at all)
    if (isElement(n) && (hasClass(n, "fc-ins") || hasClass(n, "fc-del"))) marks.push(n);
    for (let i = 0; i < n.childNodes.length; i++) visit(n.childNodes[i]);
  };
  visit(root as unknown as DNode);
  // innermost first, so an unwrapped mark's children are already plain when its ancestor unwraps
  for (let k = marks.length - 1; k >= 0; k--) {
    const m = marks[k];
    const p = m.parentNode as DElement | null;
    if (!p) continue;
    while (m.childNodes.length) p.insertBefore(m.childNodes[0], m);
    p.removeChild(m);
    mergeText(p);
  }
}
