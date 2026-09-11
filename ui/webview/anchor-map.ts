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
//   - paintRaw / paintRendered wrap exactly the text nodes of a source range in mark elements; in the Rendered view an
//     inline formula whose TeX the range holds goes under the mark with the words beside it (wrapBetween), so a passage
//     with a formula in it is one highlight and not two with the formula bare between them.
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
// removeChild), so anchor-map.test.ts runs it under node against a small stand-in with no jsdom. One
// reading of the LAYOUT is taken when the document offers it (ownerDocument.createRange and the Range's
// getClientRects, the element's own getClientRects): the Rendered paint's trim of collapsed blanks
// (trimCollapsedMarks), a no-op over a stand-in without them.
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
  /** The DOM's sibling pointers, when the node offers them (a browser's Node does; a test's stand-in may not): a step to a
   *  neighbour in constant time, where indexing the parent's child list costs its length (sibling, follows). */
  previousSibling?: DNode | null;
  nextSibling?: DNode | null;
};
type DText = DNode & { data: string; splitText(offset: number): DText };
type DElement = DNode & {
  tagName: string;
  getAttribute(name: string): string | null;
  setAttribute(name: string, value: string): void;
  insertBefore(node: DNode, ref: DNode | null): DNode;
  appendChild(node: DNode): DNode;
  removeChild(node: DNode): DNode;
  ownerDocument: { createElement(tag: string): DElement; createTextNode(s: string): DText; createRange?(): DRange } | null;
};
/** The one layout reading (trimCollapsedMarks): a Range over a mark's contents and the widths the browser lays them out at. A
 *  stand-in that offers no createRange, or a Range with no getClientRects, is measured by nothing and every mark stays. */
type DRange = { selectNodeContents(n: DNode): void; getClientRects(): ArrayLike<{ width: number }> };

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

/** Every text node under `root`, document order, appended to `out`. */
function textNodes(root: DNode, out: DText[] = []): DText[] {
  const visit = (n: DNode) => {
    if (isText(n)) { out.push(n); return; }
    if (isControl(n)) return;
    for (let i = 0; i < n.childNodes.length; i++) visit(n.childNodes[i]);
  };
  visit(root);
  return out;
}
/** The child of `root` that `n` sits under (`n` itself when it is one), or null when `n` is not under `root`. */
function topChildOf(root: DNode, n: DNode): DNode | null {
  let c = n;
  while (c.parentNode && c.parentNode !== root) c = c.parentNode;
  return c.parentNode === root ? c : null;
}
const textOf = (root: DNode): string => textNodes(root).map((t) => t.data).join("");
const stripWs = (s: string): string => s.replace(/\s+/g, "");
/** The three shapes the fill leaves where a formula's placeholder stood (math.ts renderMathPlaceholders): KaTeX's layout
 *  (`.katex`, glyphs laid out from the TeX), KaTeX's flag on TeX it could not parse (`.katex-error`, the TeX as text, with
 *  no `.katex` root around it), and the fill's own belt for a formula past a bound (`code.md-math-src`, the TeX as text, in a
 *  `pre` for a display formula). Each is a control below: its text is not the note's, whether glyphs or the TeX (the source
 *  holds the TeX between delimiters, and the mathInline / mathBlock tokens are zero-text holes), and a formula the fill fell
 *  back on used to leave the TeX in the block's rendered text, so a paragraph with one refused as not matching the file, and
 *  a display formula took no element and every block after it paired one element early, its paragraphs refused and the
 *  reader's place a block off (the Slice 4 review). A selection endpoint inside one is a formula touched (mapRenderedSelection). */
const FORMULA_CLASSES = ["katex", "katex-error", "md-math-src"];
const isFormula = (n: DNode): boolean => FORMULA_CLASSES.some((cls) => hasClass(n, cls));
/** A control the viewer parks inside the rendered markup, not the note's text: the Copy button code-block.ts puts in every
 *  fence's <pre>. Its label "Copy" joined a block's rendered text, so every block holding a fence, and every list or quote
 *  with one anywhere in it, failed to pair with its source and was refused as not matching the file, and paintRendered's
 *  fallback counted the label in its hay (the Slice 3 review). Every walk over a rendered node's text skips it, and since
 *  Slice 4 the other elements whose text is not the note's: a formula in any of the fill's three shapes (FORMULA_CLASSES: the
 *  paragraph maps AROUND the formula and the mathInline / mathBlock tokens are zero-text holes), a footnote's back link, the
 *  front matter's fold label, and a gated figure's placeholder. */
const CONTROL_CLASSES = [
  "code-copy",              // the fence's Copy button (code-block.ts)
  ...FORMULA_CLASSES,       // a formula, rendered or shown as its TeX (math.ts renderMathPlaceholders)
  "md-fnback",              // a footnote definition's back link (md-config.ts): its label is the footnote's number
  "md-frontmatter-head",    // the front matter's fold control (md-config.ts): its label is the viewer's
  "fv-gate",                // a gated figure's placeholder (figure-gate.ts): its label names the host, and holds the media
];
const isControl = (n: DNode): boolean => CONTROL_CLASSES.some((cls) => hasClass(n, cls));
/** The span the regions layer wraps a picture in while the Comments panel is open (file-comments-regions.ts: the <img> and its
 *  drawing overlay inside it). Where a tag test reads a node's element, this span stands for its IMG: an html block whose
 *  top-level tag is <img> renders that span with the panel open and the bare <img> without it, and the pairing must find the
 *  block's element either way (the Slice 5 review, round 2: the span hid the IMG from every tag test, so a wrapper before such a
 *  block could not confirm its run and the passages nested in it were refused, and their comments unpainted, with the panel open). */
const IMG_WRAP_CLASS = "fc-imgwrap";
/** The tag a node answers a tag test with: its own element's, or IMG for the regions layer's span around a picture. */
const tagNameOf = (n: DElement): string => hasClass(n, IMG_WRAP_CLASS) ? "IMG" : n.tagName.toUpperCase();

// ── code lines under a wrap ────────────────────────────────────────────────────────────────────────
//
// The viewer's fenced code is wrapped in per-line rows (code-block.ts wrapCodeLines: `<span class="cl"><span
// class="ct">…</span></span>` per line; the Raw view's `.fv-cl` rows are built the same way), and the wrap DROPS the
// newline each row stands for, so a wrapped code element's textContent runs its lines together. The helpers below put
// the newline back, so a reader of a code block's text sees the source's line structure whether the code was wrapped or
// not. paintRendered's fallback below builds its hay from hayRuns, codeRuns with a blank put between two adjacent table
// parts as well (a comment across two code lines matched its quote, which holds a newline, against a hay reading
// "commentdef" and painted nothing, Slice 3 of plans/markdown-viewer.md; a comment across two cells reads its pipe as a
// blank and finds the cells apart, Slice 5).
// codeLineAt and codeLineStart, the line of a DOM position and the position where a line starts, are exported for
// Slice 8's exact mapping of code lines and have no caller in production today: reader-place.ts read the code line at
// the body's top edge through codeLineAt until the Slice 3 review's round 3 retired that hit-test read, and now counts
// the `.cl` row under the edge as its line, the line codeLineAt gives any position in the row (one row per line).
// anchor-map-wrapped-code.test.ts exercises the two and pins that no production module calls them; a caller added later
// updates this paragraph and the plan's Slice 3 build note (item 9).

const isCodeRow = (n: DNode): boolean => hasClass(n, "cl") || hasClass(n, "fv-cl");

/** One run of a code element's text: a text node with its data, or the newline (no node) between two adjacent rows,
 *  which `row` is the second of. */
export type CodeRun = { node: DText | null; text: string; row?: DElement };

/** A table's parts, as the sanitizer keeps them. Two of them adjacent with no text between (two cells of a row, two rows)
 *  hold text the browser lays out apart, and the fallback's hay puts a blank between them (hayRuns): a DOM the parser left
 *  whitespace nodes between has the blank already, one it did not (a minified table) ran the cells' text together. */
const TABLE_PARTS = new Set(["TD", "TH", "TR", "THEAD", "TBODY", "TFOOT", "CAPTION"]);
const isTablePart = (n: DNode): boolean => isElement(n) && TABLE_PARTS.has(n.tagName.toUpperCase());

/** The runs under `n`, appended to `out`: its text nodes, with a "\n" run put back between two adjacent code rows and,
 *  when `cells`, a " " run between two adjacent table parts. */
function runsUnder(n: DNode, out: CodeRun[], cells: boolean): void {
  if (isText(n)) { out.push({ node: n, text: n.data }); return; }
  let prevRow = false, prevCell = false;
  for (let i = 0; i < n.childNodes.length; i++) {
    const c = n.childNodes[i];
    if (isControl(c)) continue;
    const row = isElement(c) && isCodeRow(c);
    if (row && prevRow) out.push({ node: null, text: "\n", row: c as DElement });
    const cell = cells && isTablePart(c);
    if (cell && prevCell) out.push({ node: null, text: " " });
    runsUnder(c, out, cells);
    prevRow = row; prevCell = cell;
  }
}
/** The text runs of `code` in document order: its text nodes, with a "\n" run put back between two adjacent rows. A
 *  text node itself is its one run. */
export function codeRuns(code: DNode): CodeRun[] { const out: CodeRun[] = []; runsUnder(code, out, false); return out; }
/** The runs paintRendered's fallback builds its hay from: codeRuns's, plus a blank between two adjacent table parts (a
 *  quote across two cells, `cell one | cell two`, reads its pipe as a blank and must find the cells apart; Slice 5 of
 *  plans/markdown-viewer.md, item 8). */
function hayRuns(n: DNode): CodeRun[] { const out: CodeRun[] = []; runsUnder(n, out, true); return out; }

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

/** A selection boundary inside a control (isControl): the control, the global text index at its place (a control counts no
 *  text, so its place is one index, the same before and after it), and where in the control's own text the boundary sits
 *  (`inner` of `len`: 0 at its leading edge, `len` at its trailing edge). The browser puts a boundary there for ordinary
 *  gestures on the Slice 4 constructs: a triple-click on a footnote definition anchors on the back link's label, a drag
 *  that starts or ends on a formula's glyphs, a triple-click on the paragraph before a display formula, whose focus lands
 *  on the formula's first glyph. boundaryIndex used to answer null for these, the answer for a node under another surface,
 *  and the selection was refused as reaching outside the rendered text (the Slice 4 review). */
type InControl = { control: DElement; at: number; inner: number; len: number };
type Boundary = number | "before" | "after" | InControl | null;
const inControl = (b: Boundary): b is InControl => typeof b === "object" && b !== null;
/** The global text index a boundary stands at: a boundary inside a control at the control's place. */
const boundaryAt = (b: Exclude<Boundary, null>, total: number): number => (b === "before" ? 0 : b === "after" ? total : inControl(b) ? b.at : b);
/** Whether `node` is `el` or under it. */
function isUnder(node: DNode, el: DNode): boolean {
  for (let n: DNode | null = node; n; n = n.parentNode) if (n === el) return true;
  return false;
}

/**
 * The number of counted characters under `root` before the boundary (node, offset), i.e. the boundary's
 * global text index. "before"/"after" when the boundary is outside `root` but `node` is an ancestor of
 * it (the selection reached past the text and may snap to its edge); an InControl when the boundary sits
 * inside a control under `root` (whose text is not counted: the control's place, and the boundary's place
 * in its own text); null when the boundary is unrelated to `root` (a sibling surface, which refuses).
 * `counts` limits counting to text under elements it admits (the Raw rows), so text outside a row never
 * shifts an index.
 */
function boundaryIndex(root: DNode, node: DNode, offset: number,
                       counts: ((el: DElement) => boolean) | null): Boundary {
  let total = 0;
  let within: InControl | null = null;
  const visit = (n: DNode, inCounted: boolean): boolean => {
    if (isControl(n) && n !== root) {
      if (!isUnder(node, n)) return false;
      // the boundary's place in the control's own text: every text node under the control counts toward `len`, and toward
      // `inner` while it lies before the boundary (a control holds no control, so nothing is skipped here)
      let inner = 0, len = 0, seen = false;
      const walk = (c: DNode): void => {
        if (c === node) {
          if (isText(c)) { inner += Math.min(Math.max(0, offset), c.data.length); len += c.data.length; }
          else for (let i = 0; i < c.childNodes.length; i++) { if (i === offset) seen = true; walk(c.childNodes[i]); }
          seen = true;
          return;
        }
        if (isText(c)) { len += c.data.length; if (!seen) inner += c.data.length; return; }
        for (let i = 0; i < c.childNodes.length; i++) walk(c.childNodes[i]);
      };
      walk(n);
      within = { control: n as DElement, at: total, inner, len };
      return true;
    }
    if (n === node) {
      if (isText(n)) { if (inCounted || !counts) total += Math.min(Math.max(0, offset), n.data.length); return true; }
      const here = inCounted || !counts || (isElement(n) && counts(n));
      for (let i = 0; i < offset && i < n.childNodes.length; i++) total += textLenUnder(n.childNodes[i], here, counts);
      return true;
    }
    if (isText(n)) { if (inCounted || !counts) total += n.data.length; return false; }
    const here = inCounted || !counts || (isElement(n) && counts(n));
    for (let i = 0; i < n.childNodes.length; i++) if (visit(n.childNodes[i], here)) return true;
    return false;
  };
  if (visit(root, false)) return within ?? total;
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
 *  view switch). A hit costs one pointer compare per child. The Rendered index's shape holds the children of every
 *  element the pairing read nested blocks out of as well (a wrapper, analyzeRendered): a nested block's node is that
 *  element's child, so the same layer wrapping a picture INSIDE a wrapper changes the wrapper's children and nothing
 *  of the root's (Slice 5 of plans/markdown-viewer.md). */
type Shape = { source: string; parents: DNode[]; children: DNode[][] };
const shapeOf = (root: DNode, source: string, wrappers: DNode[] = []): Shape => {
  const parents = [root, ...wrappers];
  return { source, parents, children: parents.map((p) => Array.from(p.childNodes)) };
};
const sameShape = (a: Shape, root: DNode, source: string): boolean => {
  if (a.source !== source || a.parents[0] !== root) return false;
  for (let p = 0; p < a.parents.length; p++) {
    const was = a.children[p], now = a.parents[p].childNodes;
    if (was.length !== now.length) return false;
    for (let i = 0; i < was.length; i++) if (was[i] !== now[i]) return false;
  }
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
  let s = Math.min(boundaryAt(a, idx.total), boundaryAt(f, idx.total)), e = Math.max(boundaryAt(a, idx.total), boundaryAt(f, idx.total));
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
/** Wrap a run of ADJACENT SIBLINGS (text nodes and inline formulas, in order) in one mark, in their parent where the first stood. */
function wrapRun(run: DNode[], className: string, data?: Record<string, string>): DElement {
  const parent = run[0].parentNode as DElement | null;
  if (!parent) throw new Error("anchor-map: node has no parent");
  const m = makeMark(parent.ownerDocument, className, data);
  parent.insertBefore(m, run[0]);
  for (const n of run) m.appendChild(n);
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
// dedented / de-prefixed and then lexed with THEIR leading tabs expanded (the block lexer expands on every
// call, so a tab after a quote's marker reaches its nested tokens as four spaces; blockLexView), block-level
// `text` tokens double their interior newlines in `raw`, and a
// paragraph marked joined onto the one before it (sourceRaw) doubles the newline at the join and, when the
// joined block was an indented line, loses its indentation in `text`. The walk therefore runs over the
// normalized text N with a map back to source offsets, places every token by verifying its raw (or, for
// block text and a joined paragraph, the raw as the source holds it, sourceRaw) at the assigned position,
// and maps child text through a per-line "suffix of the raw line" view for list items, blockquotes and
// joined paragraphs. Only non-whitespace characters are recorded: the renderer's own line breaks carry no
// text, so alignment and mapping ignore whitespace.

class Refusal extends Error {}

/** The noun a refusal names a token by, in the person's terms (plans/markdown-viewer.md, Slice 5: "no token names in
 *  refusals"): the Slice 4 constructs (md-config.ts) by what they show, "a footnote definition" and never `footnoteDef`,
 *  marked's built-ins as they read, each with its article, and "content" for a kind the map has no name for. A refusal's
 *  sentence names what the person selected, and a camelCase token name is the lexer's word, not theirs. `inline` tells an
 *  inline `html` token (a tag in a line of text) from an html block, the one type both levels share. Every registered token
 *  has a case, so the default is for a future extension. The message sites below (a token whose raw the walk could not
 *  place, emphasis whose marks did not tile) are its callers; exported for the test that pins the catalogue and the
 *  sentence a misplaced construct reads (anchor-map-obsidian.test.ts), which no input the lexer accepts today reaches. */
export function refusalNoun(type: string, inline = false): string {
  switch (type) {
    // marked's block tokens
    case "paragraph": return "a paragraph";
    case "heading": return "a heading";
    case "list": return "a list";
    case "list_item": return "a list item";
    case "table": return "a table";
    case "code": return "a code block";
    case "blockquote": return "a quote";
    case "hr": return "a rule";
    case "space": return "blank lines";
    case "def": return "a link definition";
    case "html": return inline ? "an HTML tag" : "an HTML block";
    // marked's inline tokens (`text` is block text in a tight list item too)
    case "text": return "text";
    case "escape": return "an escaped character";
    case "codespan": return "an inline code span";
    case "em": return "emphasis";
    case "strong": return "strong emphasis";
    case "del": return "a strikethrough";
    case "link": return "a link";
    case "image": return "an image";
    case "br": return "a line break";
    // the Slice 4 constructs (md-config.ts, math.ts)
    case "frontMatter": return "the front matter";
    case "footnoteDef": return "a footnote definition";
    case "footnoteRef": return "a footnote reference";
    case "callout": return "a callout";
    case "mark": return "a highlight";
    case "wikilink": return "a wikilink";
    case "mathBlock": return "a display formula";
    case "mathInline": return "a formula";
    default: return "content";
  }
}
/** The refusal for a token of a kind the walk has no case for: a future extension's (every registered token has one). The
 *  kind is not named: the sentence is the person's, and a token type is not their word (refusalNoun). */
const NOT_HANDLED = "content of a kind the mapping does not handle";

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

/** A lazy `===` or `--` line as marked's blockquote tokenizer guards it: up to three spaces, a run of `=` or `-`, spaces. */
const SETEXT_LAZY_RE = /^ {0,3}(?:=+|-+) *$/;
/** A quote line with nothing after its marker, as marked's blockquote tokenizer reads one: `^ *>[ \t]?` comes off every
 *  line of the quote's raw, under ANY indentation, since a lazy continuation line indented four or more spaces enters the
 *  quote through the paragraph's continuation (the quote rule's own ` {0,3}>` is what OPENS a line, not what the strip
 *  takes: the Slice 4 review, round 6, where `> first\n    >` and `> first\n\t>` refused whole and `> first\n   >`
 *  mapped); the tokenizer rtrims the newlines that remain of the quote's last such lines, so at the quote's end the line
 *  is a raw line past the text. A raw line matching this is by construction one the tokenizer emptied. */
const QUOTE_BLANK_RE = /^ *>[ \t]?$/;
/** Child text of a list item or blockquote, and the text of a paragraph marked joined an indented line onto
 *  (sourceRaw): line i of `text` is a suffix of line i of the raw view (the bullet, indentation, or `> `
 *  prefix removed); raw lines past the text are blank, or a quote's empty `>` lines (QUOTE_BLANK_RE: the
 *  blockquote tokenizer strips the marker and rtrims what is left, so `> first\n>` has a raw line more than
 *  its text; the Slice 4 review, round 5: before this a quote closed with an empty `>` line, a common way to
 *  write one, refused whole, its nested and list-hosted forms too, where a callout of the same shape mapped).
 *  One more shape passes, marked's setext protection: a quote's (or md-config.ts's callout's) lazy `===` or
 *  `--` line after another line is prefixed with four spaces in `text`, so the nested lex reads a paragraph's
 *  text and not a setext underline. The spaces are the tokenizer's, not the note's, and the emitter records
 *  no whitespace, so they take the underline's own start and the underline's characters their raw offsets
 *  (the Slice 4 review, round 3: before this the callout or the quote refused whole, with a reason naming
 *  a tab, and a selection on its body was sent to the Raw view). A tab after the marker's own whitespace is
 *  a suffix like any other and stays a tab here; the nested lexer's expansion of it is the caller's next
 *  step (blockLexView). Anything else fails the suffix test and refuses with `mismatch`, the caller's reason. */
function suffixLineView(raw: View, text: string, mismatch = "a block whose lines the mapping could not place"): View {
  const rawLines = raw.str.split("\n"), textLines = text.split("\n");
  if (textLines.length > rawLines.length) throw new Refusal("a block whose lines the mapping could not place");
  const map: number[] = new Array(text.length + 1);
  let rawLineStart = 0, ti = 0, endN = raw.n(0);
  for (let i = 0; i < textLines.length; i++) {
    const rl = rawLines[i], tl = textLines[i];
    if (rl.endsWith(tl)) {
      const off = rl.length - tl.length;
      for (let k = 0; k < tl.length; k++) map[ti + k] = raw.n(rawLineStart + off + k);
    } else if (i > 0 && SETEXT_LAZY_RE.test(rl) && tl === "    " + rl.replace(/^ {0,3}/, "")) {
      // marked's guard: four spaces the source does not hold, then the raw line less its indentation
      const lead = rl.length - rl.replace(/^ {0,3}/, "").length;
      for (let k = 0; k < tl.length; k++) map[ti + k] = raw.n(rawLineStart + lead + Math.max(0, k - 4));
    } else throw new Refusal(mismatch);
    ti += tl.length;
    endN = raw.n(rawLineStart + rl.length);
    if (i < textLines.length - 1) { map[ti] = raw.n(rawLineStart + rl.length); ti++; }
    rawLineStart += rl.length + 1;
  }
  for (let i = textLines.length; i < rawLines.length; i++) {
    if (rawLines[i].trim() !== "" && !QUOTE_BLANK_RE.test(rawLines[i])) throw new Refusal("a block whose lines the mapping could not place");
  }
  map[text.length] = endN;
  return new View(text, null, map);
}

/** marked's tab expansion, the block lexer's first step on every text it is handed (blockTokens: `^( *)(\t+)`, four
 *  spaces per tab, the run being the tabs right after a line's leading spaces; a space after the run ends it for the
 *  rest of the line). `n(i)` is the position str[i] carries; each tab's four spaces carry the tab's own. The result's
 *  map has one entry per character and one past the end. */
function expandTabs(str: string, n: (i: number) => number): { str: string; map: number[] } {
  let out = "";
  const map: number[] = [];
  let spacesOnly = true, tabRun = false;
  for (let i = 0; i < str.length; i++) {
    const c = str[i], at = n(i);
    if (c === "\n") { out += c; map.push(at); spacesOnly = true; tabRun = false; continue; }
    if (c === "\t" && (spacesOnly || tabRun)) { out += "    "; map.push(at, at, at, at); spacesOnly = false; tabRun = true; continue; }
    if (c === " ") { if (tabRun) tabRun = false; }
    else { spacesOnly = false; tabRun = false; }
    out += c; map.push(at);
  }
  map.push(n(str.length));
  return { str: out, map };
}
/** The view a NESTED block lex's tokens tile: a blockquote's text, a callout's body and a list item's text each go
 *  through blockTokens again, which expands their leading tab runs before lexing (expandTabs), so a tab the container's
 *  marker left in the text (`> \tquoted`, `>\t\tcode`, a closing `> \t`, `- \titem`) is four spaces in the nested
 *  tokens' raws. The top-level walk runs over N, the source with the same expansion (normalizeSource); this is that step
 *  one level down, and the four spaces take the tab's position, so no emitted character moves and a block the tab opens
 *  (an indented code block) places as a hole where the tab stands. The Slice 4 review, round 6: before this the nested
 *  walk ran over the unexpanded text, the nested raws did not tile it, and any such quote refused whole, a closing
 *  `> \t` line with "a paragraph the mapping could not place" (round 5 covered `>\t` and `> ` singly: the strip takes
 *  one whitespace and the nested lexer expanded the second), a `> \tquoted` line with a reason naming the tab. */
function blockLexView(v: View): View {
  if (!/^ *\t/m.test(v.str)) return v;
  const { str, map } = expandTabs(v.str, (i) => v.n(i));
  return new View(str, null, map);
}

type Hole = { reason: string; startN: number; endN: number };
/** The reason of a formula's hole (mathInline, mathBlock), the one formulaExtra finds a hole by. */
const FORMULA_HOLE = "a formula";
/** The reasons of a code block's and a table's holes (the walk shows their text and refuses to map inside them). */
const CODE_HOLE = "a code block", INDENTED_CODE_HOLE = "an indented code block", TABLE_HOLE = "a table";
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

/** A token's raw as the SOURCE holds it. That is `raw` for every token but a paragraph, or a list item's block text, that
 *  marked 12's block lexer (blockTokens) joined another block onto. Every join site there runs `lastToken.raw += "\n" +
 *  token.raw` after the single newline between the two was already moved onto the previous raw by the space step, so the
 *  joined raw holds one newline per join the source does not, while `text` gets one per join. Two joins reach a paragraph.
 *  The clip join: the lexer sets its lastParagraphClipped flag whenever any block extension's start hint returned a position,
 *  however far below, and then joins the next paragraph onto the previous one; the paragraph regex itself stops early for
 *  its own reasons (a header-looking line over a delimiter row the table tokenizer then rejects on the cell count, a
 *  lowercase `<prefix>` line the paragraph rule's html lookahead stops at and the html tokenizer refuses, a bare `* ` or
 *  `1. ` bullet the list tokenizer refuses as empty), so the join fires with a display formula anywhere later in the note
 *  (the math hint, the grammar's one block hint; the callout's, which joined alike, went in round 3 of the review,
 *  md-config.ts), top level or inside a quote's body (the Slice 4 review, rounds 2 and 3: the raw tiled nothing from there
 *  on, every later block's span collapsed to the join's start, and every selection past it refused). The code join: the
 *  gfm table interrupt admits any indentation on its header line, so the paragraph regex stops before a line indented four
 *  columns (four spaces, or a tab the lexer expanded) when a delimiter-row-shaped line follows it, as in
 *  `Intro\n    Column A\n|---|---|`, or a `---` under the indented line; the code tokenizer, which runs before the table's,
 *  takes the indented line as indented code, and the lexer joins it onto the paragraph with `text += "\n" + code.text`, the indentation
 *  stripped (`^ {1,4}` per line): CommonMark's own reading, since an indented code block cannot interrupt a paragraph and
 *  a continuation line's indentation is not shown. That join needs no hint, so it fires at the top level, in a quote's
 *  body and in a list item's block text (the same join onto a `text` token), and both joins stack (round 5 of the review:
 *  every later block's span collapsed to the join's start, as under the clip join, because a walk of the raw that allowed
 *  for the doubled newline alone stopped at the first stripped space; the same at the base, where the shape was a
 *  refusal from the join to the end of the note). The renderer emits the joined block as ONE element over `text`, so the
 *  source raw is rebuilt line by line (joinedSourceRaw): each line of `text` is the raw line it came from less up to four
 *  leading spaces, a blank raw line no text line matches is a join's newline and goes, and the raw lines past the text
 *  are its trailing newlines. The block table and the walk place that string as they place any raw, and the walk maps the
 *  text into it through the per-line suffix view (suffixLineView). A raw the relation does not hold for comes back
 *  unchanged, and the usual placement then refuses whatever it cannot place. md-config-merged-paragraph.test.ts holds
 *  both joins over every trigger shape and a fuzz of them; the browser leg maps past both over the real Files bundle. */
function sourceRaw(t: Token): string {
  if (t.type !== "paragraph" && t.type !== "text") return t.raw;
  const { raw, text } = t as Tokens.Paragraph | Tokens.Text;
  if (raw.indexOf("\n\n") < 0) return raw;
  return joinedSourceRaw(raw, text) ?? raw;
}
/** The lines of a joined block's raw as the source holds them (sourceRaw), joined by newlines; null when raw and text are
 *  not in the join's relation. Each text line takes the next raw line that ends with it after no more than four spaces
 *  (the indentation the code tokenizer strips; a blank text line takes a blank raw line); a blank raw line a non-blank
 *  text line passes over is a join's newline; anything else the text lacks fails. */
function joinedSourceRaw(raw: string, text: string): string | null {
  const rawLines = raw.split("\n"), textLines = text.split("\n");
  const out: string[] = [];
  let ri = 0;
  for (const tl of textLines) {
    for (;;) {
      if (ri >= rawLines.length) return null;
      const rl = rawLines[ri++];
      if (rl.endsWith(tl) && /^ {0,4}$/.test(rl.slice(0, rl.length - tl.length))) { out.push(rl); break; }
      if (rl !== "") return null;
    }
  }
  for (; ri < rawLines.length; ri++) { if (rawLines[ri] !== "") return null; out.push(""); }
  return out.join("\n");
}

// marked's escape() leaves an `&` alone when it begins an entity; the browser then decodes it to ONE
// character, so the rendered text is shorter than the source. Such prose refuses (plan).
const ENTITY_RE = /&(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);/;

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
      default: throw new Refusal(NOT_HANDLED);
    }
  }
  return out;
}

function walkInline(tokens: Token[], view: View, em: Emitter): void {
  let p = 0;
  for (const t of tokens) {
    const raw = t.raw;
    if (!view.str.startsWith(raw, p)) throw new Refusal(refusalNoun(t.type, true) + " the mapping could not place");
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
        if (!d || raw.slice(d, raw.length - d) !== tt.text) throw new Refusal(refusalNoun(t.type, true) + " whose marks the mapping could not place");
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
        em.holes.push({ reason: FORMULA_HOLE, startN: view.n(p), endN: view.n(p + raw.length) });
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
      default: throw new Refusal(NOT_HANDLED);
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
    const raw = sourceRaw(t);   // a paragraph or block text marked joined a block onto: the raw as the source holds it
    if (t.type === "text") {
      // Block text (tight list items): marked's `text` tokenizer reads one line and the lexer joins the next onto it
      // with a doubled newline in raw, or an indented line its code tokenizer took first with the indentation gone
      // from `text` (sourceRaw rebuilt the source's lines, `raw` here); line i of `text` is a suffix of line i of that
      // raw, and the raw's extra trailing newlines are the ones the lexer moved onto this token.
      const tt = t as Tokens.Text;
      if (!view.str.startsWith(raw, p)) throw new Refusal("a list item the mapping could not place");
      const tv = suffixLineView(view.sub(p, p + raw.length), tt.text, "a list item the mapping could not place");
      if (tt.tokens) walkInline(tt.tokens, tv, em);
      else emitText(tv, em);
      p += raw.length;
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
      else throw new Refusal(refusalNoun(t.type) + " the mapping could not place");
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
        if (raw.startsWith(tt.text) && !/[^\n]/.test(raw.slice(tt.text.length))) walkInline(tt.tokens, view.sub(p, p + tt.text.length), em);
        // the code join (sourceRaw): the source holds the indentation `text` lost, so line i of text is a suffix of raw line i
        else if (raw !== tt.raw) walkInline(tt.tokens, suffixLineView(view.sub(p, p + raw.length), tt.text, "a paragraph the mapping could not place"), em);
        else throw new Refusal("a paragraph the mapping could not place");
        break;
      }
      case "blockquote": {
        const tt = t as Tokens.Blockquote;
        walkBlocks(tt.tokens, blockLexView(suffixLineView(view.sub(p, p + raw.length), tt.text)), em);
        break;
      }
      case "list": {
        const tt = t as Tokens.List;
        let q = p;
        for (const item of tt.items) {
          if (!view.str.startsWith(item.raw, q)) throw new Refusal("a list the mapping could not place");
          walkBlocks(item.tokens, blockLexView(suffixLineView(view.sub(q, q + item.raw.length), item.text)), em);
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
        em.holes.push({ reason: tt.codeBlockStyle === "indented" ? INDENTED_CODE_HOLE : CODE_HOLE, startN: view.n(p), endN: view.n(p + raw.length) });
        em.putHole(tt.text, em.holes.length - 1);
        break;
      }
      case "table": {
        const tt = t as Tokens.Table;
        em.holes.push({ reason: TABLE_HOLE, startN: view.n(p), endN: view.n(p + raw.length) });
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
        walkBlocks(tt.tokens, blockLexView(tv.sub(bodyStart, tt.text.length)), em);
        break;
      }
      case "mathBlock": {
        // a display formula of its own: KaTeX's glyphs are skipped as a control (isControl), so the block has no text
        em.holes.push({ reason: FORMULA_HOLE, startN: view.n(p), endN: view.n(p + raw.length) });
        break;
      }
      case "html": throw new Refusal("an HTML block");
      default: throw new Refusal(NOT_HANDLED);
    }
    p += raw.length;
  }
}

/** N (the lexer's preprocessed text) and, unless N === source, the source offset of every N index
 *  (length N.length + 1; a "\n" from CRLF maps to the CR, the four spaces of a tab to the tab). */
function normalizeSource(source: string): { N: string; nStart: Int32Array | null } {
  if (!/\r|^ *\t/m.test(source)) return { N: source, nStart: null };
  // CRLF and CR to LF first (the lexer's own order), the LF taking the CR's offset; then marked's tab expansion
  let lf = source, lfMap: number[] | null = null;
  if (source.includes("\r")) {
    lf = ""; lfMap = [];
    for (let i = 0; i < source.length; i++) {
      const c = source[i];
      if (c === "\r") { lf += "\n"; lfMap.push(i); if (source[i + 1] === "\n") i++; continue; }
      lf += c; lfMap.push(i);
    }
    lfMap.push(source.length);
  }
  const m = lfMap;
  const { str: N, map } = expandTabs(lf, m ? (i) => m[i] : (i) => i);
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
  /** an html block's top-level tags as the tag scan reads its raw (topTags), in order; null for every other block */
  tags: TopTag[] | null;
  /** the block's stray end tags (blockEnds): the elements its inline html closes without opening them, upper case, in order,
   *  each with whether it stands inside a `<p>` the renderer emits (a paragraph's, a quoted paragraph's, a loose list item's;
   *  not a heading's or a tight item's); empty for an html block. The parser closes such an element when it is open around the
   *  block (a wrapper), the `<p>` with it, and, for a closer inside a `<p>`, mints an empty `<p>` for that `</p>` (minted). */
  ends: EndTag[];
  /** whether the parser minted an empty `<p></p>` right after this block's node: one of its `ends` inside a `<p>` closed a
   *  wrapper the source had open around the block (the walk over the wrapper chain in walkedBlocks, which reads the html blocks'
   *  open tags and stray end tags and the blocks' own closers in order), so the paragraph's own `</p>` found no `<p>` open and
   *  the parser opened one. A node no block renders as, which the pairing steps over (analyzeRendered, pastMinted: the one
   *  model the run check and the pairing share). A closer naming no open wrapper mints nothing, whatever the DOM holds, and
   *  nor does an end tag the parser ignores inside an open `<p>` (P_CLOSERS, FORMATTING: the review's round 3). */
  minted: boolean;
  /** an html block whose raw leaves a top-level `<p>` open at its end (topTags): the block after it nests in that `<p>` unless
   *  its element's start tag closes a `<p>` (nested, below) */
  pOpen: boolean;
  /** a block the parser nests INSIDE the `<p>` an earlier html block left open, so none of its elements is a top-level node and
   *  the pairing gives it none: an html block whose first tag is not p-closing (`<br>`, `<img>`, `<span class="w">`), a table (a
   *  `<table>` start tag closes no `<p>` in a quirks-mode document, DOMPurify's) or a display formula (a span). The run check reads
   *  such a block past, as a blank one (the Slice 5 review, round 3: before, the `<img>` block's forward scan found a LATER
   *  top-level picture and refused every nearer end, so the open `<p>`'s block took the paragraphs between). */
  nested: boolean;
  /** an html block's text outside its tags and comments (htmlText), whitespace stripped: what the sanitizer's unwrap of a
   *  form-associated element leaves as a bare text node where the element stood; "" for every other block */
  htext: string;
  /** the elements of this block whose children the pairing took into the table: a tag the raw leaves open (`<div
   *  align="center">`, `<details><summary>x</summary>`), which the browser nests the markdown after the block inside,
   *  so the blocks after it pair against that element's children (Slice 5's flattened walk); renderedBlockWrappers */
  wrap: DNode[];
};
/** Whether an html token's raw is comments alone, whitespace between them, read left to right one comment at a time:
 *  each `<!--` is closed by the first `-->` after it (or is one of marked's two-character forms `<!-->` and `<!--->`),
 *  so a raw of many comments costs its length. marked lexes a line of comments and whatever follows them on that line
 *  as one html token, so the raw can hold any number of them. Not a regex: the anchored one this replaced,
 *  `^(?:\s*<!--[\s\S]*?-->)*\s*$`, tried every way of splitting the comments among its repeats whenever the raw ended
 *  in anything else (a tag, words, an unterminated comment) and doubled its time per comment (91 ms at 22, 144 s at
 *  30, on every Rendered paint), and it let a comment at each end of the line vouch for the words between them, which
 *  do render (the Slice 2 review, round 2: the next paragraph took their node and every block after paired one early). */
export function commentsOnly(raw: string): boolean {
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
/** A tag of an html token's raw, as topTags reads it: the element's name, upper case, and whether the raw leaves it OPEN. The
 *  browser nests the markdown after the block inside an element the block left open (`<div align="center">`, a
 *  `<details><summary>x</summary>` with a blank line after it), and closes the rest with the block (`<p>Alpha</p>`, a void
 *  element, a `<p>` whose end tag is missing: see topTags). `depth` is 0 for a top-level tag; an element left open INSIDE
 *  the open one before it (`<div><div>`, the second the last element child of the first) is listed after it at depth 1, 2,
 *  and so on, since the markdown after the block nests in the innermost. `empty` marks the `<p></p>` the parser mints for a
 *  stray `</p>`: an element with no text. `stray` marks any other end tag with no element of its name open in the raw
 *  (`</details>` alone, the `</div>` before an `<img>` in one block): it closes an element an earlier block left open, or
 *  nothing, and takes no node of its own; the wrapper chain in walkedBlocks reads it. */
type TopTag = { tag: string; open: boolean; depth: number; empty?: boolean; stray?: boolean;
  /** for a depth-0 tag, the nodes the raw itself puts inside it, in order: each element closed within the raw directly under it
   *  (its name) and each run of non-blank text there (`#text`); for a tag left open these are the children the browser has before
   *  the markdown it nests after the block (a `<details>`'s summary, a centred div's lead text or banner), which the pairing keeps
   *  as the block's own and reads past before the next block's scan (analyzeRendered; the review's round 3: the next html block's
   *  same-tag element, `<div class="in">` after `<div align="center"><div>Lead</div>`, took the leftover `<div>Lead</div>`) */
  kids?: string[] };
const VOID_TAGS = new Set(["AREA", "BASE", "BR", "COL", "EMBED", "HR", "IMG", "INPUT", "LINK", "META", "PARAM", "SOURCE", "TRACK", "WBR"]);
/** The elements whose start tag closes an open `<p>` (the HTML parser's rule for a `p` in button scope, "in body"). */
const CLOSES_P = new Set(["ADDRESS", "ARTICLE", "ASIDE", "BLOCKQUOTE", "DETAILS", "DIALOG", "DIV", "DL", "FIELDSET", "FIGCAPTION", "FIGURE", "FOOTER", "FORM",
                          "H1", "H2", "H3", "H4", "H5", "H6", "HEADER", "HGROUP", "HR", "MAIN", "MENU", "NAV", "OL", "P", "PRE", "SEARCH", "SECTION", "SUMMARY", "TABLE", "UL"]);
/** The elements whose content the parser reads as text up to their own end tag, tags inside it and all. */
const RAW_TEXT = new Set(["SCRIPT", "STYLE", "TEXTAREA", "TITLE", "XMP", "IFRAME", "NOEMBED", "NOFRAMES"]);
/** The elements the sanitizer removes and KEEPS the content of, as bare nodes where the element stood (md-sanitize.ts's
 *  MD_FORBID_TAGS, DOMPurify's KEEP_CONTENT, less `<style>`, whose text goes with it): the pairing reads a wrapper's child of one of
 *  these as its text (TopTag.kids, pastKids). Listed here rather than imported: md-sanitize.ts creates the DOMPurify instance at
 *  load, which this module's node tests, run on a DOM stand-in, must not. */
const UNWRAPPED = new Set(["DIALOG", "FORM", "BUTTON", "SELECT", "OPTION", "OPTGROUP", "TEXTAREA", "FIELDSET", "LEGEND", "LABEL", "DATALIST", "OUTPUT", "METER", "PROGRESS", "MAP", "AREA"]);
const isTagNameChar = (c: string): boolean => (c >= "a" && c <= "z") || (c >= "A" && c <= "Z") || (c >= "0" && c <= "9") || c === "-" || c === ":" || c === "_";
/** The top-level tags an html token's raw opens, in order, each CLOSED within the raw or left OPEN: what the pairing reads the
 *  block's rendered nodes by (analyzeRendered). A linear scan, left to right, one tag at a time, in the style of commentsOnly
 *  (no regex): a comment is skipped to its `-->`, a doctype or processing instruction to its `>`, a tag's attributes to the
 *  `>` outside their quotes, and a script's, style's or textarea's content to its own end tag. An element opened at depth 0
 *  is a top-level tag: closed when its end tag comes (the stack pops to it) or, for a void element or a `/>`, at once. Two of
 *  the parser's implied ends are read, because they decide what the block's nodes are: a `<p>` closes when a block-level
 *  start tag (CLOSES_P) follows it, and a top-level `<p>` the raw leaves open is CLOSED, since every block marked renders
 *  after it opens with a tag that closes a `p` (the paragraph's own `<p>`, a heading, a list, a `<pre>`, a table), so no
 *  markdown nests in it, where it nests in an open `<div>` or `<details>`; and a stray `</p>` at depth 0 is an empty `<p>`
 *  the parser mints, one node. Any other end tag with no open element of its name at depth 0 is listed as `stray`: it opens
 *  nothing and takes no node (a block that is `</div>` alone), and closes the element an earlier block left open, if one is
 *  (the chain walkedBlocks keeps). Where this reading and the DOM disagree (the sanitizer dropped a `<style>` with its text or
 *  unwrapped a `<form>`, the parser split a `<p>` around a `<div>`), the pairing's resync from the following blocks stands. */
function topTags(raw: string): { tags: TopTag[]; pOpen: boolean } {
  const out: TopTag[] = [];
  const stack: string[] = [];   // the open elements, outermost first; stack[0] is out[top]'s
  let top = -1;
  const n = raw.length;
  let lower: string | null = null;   // the raw lower-cased once, for a raw-text element's end tag
  let i = 0;
  const closeTo = (k: number): void => { stack.length = k; if (k === 0 && top >= 0) { out[top].open = false; top = -1; } };
  const openTop = (name: string): void => { out.push({ tag: name, open: true, depth: 0, kids: [] }); top = out.length - 1; };
  const kid = (name: string): void => { if (top >= 0 && stack.length === 1) (out[top].kids as string[]).push(name); };   // a child of the depth-0 open element
  while (i < n) {
    const lt = raw.indexOf("<", i);
    if (lt < 0) break;
    if (stripWs(raw.slice(i, lt)) !== "") kid("#text");
    i = lt + 1;
    const c = raw[i];
    if (c === "!") {
      if (raw.startsWith("--", i + 1)) {
        i += 3;
        if (raw[i] === ">") { i++; continue; }
        if (raw.startsWith("->", i)) { i += 2; continue; }
        const close = raw.indexOf("-->", i);
        i = close < 0 ? n : close + 3;
      } else { const gt = raw.indexOf(">", i); i = gt < 0 ? n : gt + 1; }
      continue;
    }
    if (c === "?") { const gt = raw.indexOf(">", i); i = gt < 0 ? n : gt + 1; continue; }
    const end = c === "/";
    let j = end ? i + 1 : i;
    if (j >= n || !((raw[j] >= "a" && raw[j] <= "z") || (raw[j] >= "A" && raw[j] <= "Z"))) continue;   // a bare `<`: text
    let k = j;
    while (k < n && isTagNameChar(raw[k])) k++;
    const name = raw.slice(j, k).toUpperCase();
    // to the tag's `>`, outside quoted attribute values; a `/` right before it self-closes
    let selfClosing = false;
    for (i = k; i < n; i++) {
      const ch = raw[i];
      if (ch === '"' || ch === "'") { const q = raw.indexOf(ch, i + 1); if (q < 0) { i = n; break; } i = q; continue; }
      if (ch === ">") { selfClosing = raw[i - 1] === "/" && i - 1 >= k; i++; break; }
    }
    if (end) {
      let at = stack.length - 1;
      while (at >= 0 && stack[at] !== name) at--;
      if (at === 1 && top >= 0) (out[top].kids as string[]).push(name);   // an element the raw opened and closed directly inside the open top-level one
      if (at >= 0) closeTo(at);
      else if (stack.length === 0) out.push(name === "P" ? { tag: "P", open: false, depth: 0, empty: true } : { tag: name, open: false, depth: 0, stray: true });   // the parser's empty `<p></p>`; else an earlier block's element closed, or nothing
      continue;
    }
    if (CLOSES_P.has(name) && stack.length && stack[stack.length - 1] === "P") closeTo(stack.length - 1);
    const leaf = selfClosing || VOID_TAGS.has(name);
    if (leaf) kid(name);
    if (stack.length === 0) { if (leaf) out.push({ tag: name, open: false, depth: 0 }); else openTop(name); }
    if (!leaf) stack.push(name);
    if (!leaf && RAW_TEXT.has(name)) {
      lower = lower || raw.toLowerCase();
      const close = lower.indexOf("</" + name.toLowerCase(), i);
      i = close < 0 ? n : close;   // the end tag is read by the next turn
    }
  }
  if (stripWs(raw.slice(i)) !== "") kid("#text");
  // an open `<p>`: the next block's tag closes it (above), with whatever is open inside it, unless that tag is inline-level
  // (walkedBlocks reads `pOpen` and marks the next block nested); the elements still open after that are the chain the markdown
  // after the block nests in, the innermost last
  const pOpen = stack.length > 0 && stack[0] === "P";
  if (pOpen) closeTo(0);
  else if (stack.length > 1 && stack[stack.length - 1] === "P") stack.pop();
  for (let d = 1; d < stack.length; d++) out.push({ tag: stack[d], open: true, depth: d });
  return { tags: out, pOpen };
}
/** The end tags the HTML parser honours through an open `<p>` ("in body", an end tag whose element is in scope generates implied
 *  end tags and pops to it): the block-level elements, and the few others with a handler of their own (button, select, the list
 *  parts, the headings). One of these inside a paragraph closes the open `<p>` with its element, and the paragraph's own `</p>`
 *  then mints an empty `<p></p>` (Block.minted). Every other end tag met inside an open `<p>` (`</label>`, `</span>`, `</option>`,
 *  `</legend>`) is IGNORED by the parser: it closes nothing and mints nothing, and the element stays open around what follows
 *  (the Slice 5 review, round 3: before, every closer naming an open wrapper was read as minting, and after a `<label>` closed
 *  inline the pairing skipped a following html `<p></p>` block's own element as the minted one and took the next paragraph's). */
const P_CLOSERS = new Set([...CLOSES_P, "BUTTON", "CENTER", "DIR", "LISTING", "SELECT", "LI", "DD", "DT", "APPLET", "MARQUEE", "OBJECT"]);
/** The formatting elements, whose end tag inside an open `<p>` the parser's adoption agency handles: the element closes for what
 *  follows (the chain pops) and no `<p>` is minted. */
const FORMATTING = new Set(["A", "B", "BIG", "CODE", "EM", "FONT", "I", "NOBR", "S", "SMALL", "STRIKE", "STRONG", "TT", "U"]);
/** The common entities decoded, for a text the parser shows (`&amp;` is `&` in the DOM); an entity this does not know stays. */
const NAMED_ENTITIES: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: "\u00a0" };
function decodeBasicEntities(s: string): string {
  return s.replace(/&(#[xX][0-9a-fA-F]{1,6}|#\d{1,7}|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] !== "#") return e in NAMED_ENTITIES ? NAMED_ENTITIES[e] : m;
    const code = parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10);
    return code > 0 && code <= 0x10ffff ? String.fromCodePoint(code) : m;
  });
}
/** The text an html token's raw shows outside its tags and comments, whitespace stripped and the common entities decoded: what
 *  the sanitizer's unwrap of a form-associated element (md-sanitize.ts, `<option>Opt.</option>`) leaves as a bare text node
 *  where the element stood, which the pairing's run check reads past with the block (analyzeRendered). The content of an
 *  element the sanitizer drops with its text (RAW_TEXT but a textarea, whose content it keeps) is not shown. Empty for a block
 *  of tags alone (`</details>`, `<img src="a.png">`), which then renders nothing of its own when it opens no element (blank). */
function htmlText(raw: string): string {
  let out = "";
  const n = raw.length;
  let i = 0;
  while (i < n) {
    const lt = raw.indexOf("<", i);
    if (lt < 0) { out += raw.slice(i); break; }
    out += raw.slice(i, lt);
    i = lt + 1;
    const c = raw[i];
    if (c === "!" || c === "?") {
      if (raw.startsWith("!--", i)) {
        i += 3;
        if (raw[i] === ">") i++;
        else if (raw.startsWith("->", i)) i += 2;
        else { const close = raw.indexOf("-->", i); i = close < 0 ? n : close + 3; }
      } else { const gt = raw.indexOf(">", i); i = gt < 0 ? n : gt + 1; }
      continue;
    }
    const j = c === "/" ? i + 1 : i;
    if (j >= n || !((raw[j] >= "a" && raw[j] <= "z") || (raw[j] >= "A" && raw[j] <= "Z"))) { out += "<"; continue; }   // a bare `<`: text
    let k = j;
    while (k < n && isTagNameChar(raw[k])) k++;
    const name = raw.slice(j, k).toUpperCase();
    for (i = k; i < n; i++) {
      const ch = raw[i];
      if (ch === '"' || ch === "'") { const q = raw.indexOf(ch, i + 1); if (q < 0) { i = n; break; } i = q; continue; }
      if (ch === ">") { i++; break; }
    }
    if (c !== "/" && RAW_TEXT.has(name) && name !== "TEXTAREA") {
      const close = raw.toLowerCase().indexOf("</" + name.toLowerCase(), i);
      i = close < 0 ? n : close;
    }
  }
  return stripWs(decodeBasicEntities(out));
}
/** A stray end tag of a block's inline html (blockEnds): the element it closes, upper case, and whether the tag stands inside a
 *  `<p>` the renderer emits, where the parser then mints an empty `<p></p>` for that paragraph's own `</p>`. */
type EndTag = { tag: string; p: boolean };
/** A tag in an html token's raw: its `<` or `</`, its name, its attributes (a `>` inside a quoted value passes), a `/>`. */
const TAG_RE = /<(\/?)([a-zA-Z][a-zA-Z0-9:_-]*)(?:[^>"']|"[^"]*"|'[^']*')*?(\/?)>/g;
/** The end tags a block's inline html carries with no start tag of theirs before them in the block (`**Bold** </div>`,
 *  `Last line.</details>`, `> quoted </div>`, a loose item's `- Item </div>`: an author closing a wrapper on the block's own
 *  line), in order, each with whether it stands inside a `<p>` the renderer emits. marked wraps a paragraph in `<p>...</p>` (a
 *  quoted paragraph's and a loose list item's the same) and the parser, meeting the end tag with its element open above the
 *  `<p>`, closes the `<p>` and the element, then mints an empty `<p></p>` for the paragraph's own `</p>`, a node right after
 *  the wrapper's children that no block renders as; a heading's or a tight item's closer closes the element and mints nothing,
 *  since no `</p>` follows. An end tag of an element not open is dropped by the parser and mints nothing, so the wrapper chain
 *  in walkedBlocks decides which of these closed one (Block.minted). Tokens are read recursively (the tag may stand inside
 *  emphasis, a link's label, a quote's paragraph or a list item); a table's cells are a scope of their own, where the parser
 *  ignores such a tag, and code holds no tag. */
function blockEnds(tokens: Token[] | undefined, p: boolean, open: string[], out: EndTag[]): void {
  if (!tokens) return;
  for (const t of tokens) {
    switch (t.type) {
      case "html":
        for (const m of t.raw.matchAll(TAG_RE)) {
          const name = m[2].toUpperCase();
          if (m[1]) { const at = open.lastIndexOf(name); if (at >= 0) open.length = at; else out.push({ tag: name, p }); }
          else if (!VOID_TAGS.has(name) && !m[3]) open.push(name);
        }
        continue;
      case "code": case "codespan": case "table": case "escape": continue;
      case "list": { const l = t as Tokens.List; for (const it of l.items) blockEnds(it.tokens, !!l.loose, open, out); continue; }
      case "paragraph": blockEnds((t as Tokens.Paragraph).tokens, true, open, out); continue;
      case "heading": case "blockquote": blockEnds((t as { tokens?: Token[] }).tokens, false, open, out); continue;
      default: blockEnds((t as { tokens?: Token[] }).tokens, p, open, out);
    }
  }
}
type RenderedIndex = {
  source: string; shape: Shape; N: string; nStart: Int32Array | null;
  blocks: Block[];
  topNodes: DNode[]; topStart: number[]; total: number;   // every top-level child node with text, and its global index
  /** every node a block renders as, top-level or nested in a wrapper, to its block (the pairing's one table) */
  nodeBlock: Map<DNode, number>;
  /** the elements whose children the pairing took into the table (Block.wrap, over every block), for the shape */
  wrappers: DNode[];
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
    const raw = sourceRaw(t);   // a paragraph marked joined a block onto: the raw as the source holds it
    if (broken === null && !N.startsWith(raw, pos)) {
      // a reference definition (never a token), else resync on the next raw and leave the gap unmapped
      for (;;) {
        const m = DEF_RE().exec(N.slice(pos));
        if (!m) break;
        pos += m[0].length;
        if (N.startsWith(raw, pos)) break;
      }
      if (!N.startsWith(raw, pos)) {
        const j = N.indexOf(raw, pos);
        if (j >= 0) pos = j; else broken = refusalNoun(t.type) + " the mapping could not place";
      }
    }
    if (t.type === "space") { if (broken === null) pos += raw.length; continue; }
    let textEndN = pos + raw.length;
    while (textEndN > pos && raw[textEndN - pos - 1] === "\n") textEndN--;
    placed.push({ t, startN: pos, endN: pos + raw.length, textEndN, broken });
    if (broken === null) pos += raw.length;
  }
  return { placed, lexError };
}

// ── the source half of the rendered index, kept for the last source ──────────────────────────────────
/** A block as the walk over the source alone answers it, before any root's pairing: everything in Block but `dom`
 *  (`refused` here is the walk's own, which the pairing may overwrite per root). */
type Walked = Omit<Block, "dom" | "wrap">;
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
/** The table for `source`, built afresh (stripMarkupMapped reads a string of its own through this without touching the cache). */
function buildSourceTable(source: string): SourceTable {
  const { N, nStart } = normalizeSource(source);
  const { placed, lexError } = placeTokens(N);
  const idx = { nStart };
  const spans: SourceRange[] = lexError !== null
    ? [{ start: 0, end: source.length }]
    : placed.map((p) => ({ start: nOf(idx, p.startN), end: nOf(idx, p.textEndN) }));
  return { source, N, nStart, lexError, placed, spans, walked: null };
}
function sourceTable(source: string): SourceTable {
  if (sourceCache && sourceCache.source === source) return sourceCache;
  sourceCache = buildSourceTable(source);
  return sourceCache;
}
/** The walk over each placed token (walkBlocks: the block's rendered text with a source position per character, its
 *  holes, its refusal), run once per source and kept on its table. */
function walkedBlocks(table: SourceTable): Walked[] {
  if (table.walked) return table.walked;
  const out: Walked[] = [];
  let openP = false;   // whether the html block before leaves a top-level `<p>` open that nothing has closed yet (Block.pOpen, nested)
  for (const { t, startN, endN, textEndN, broken } of table.placed) {
    const em = new Emitter();
    let refused: string | null = broken;
    if (refused === null) {
      try { walkBlocks([t], View.identity(table.N, 0), em, startN); }
      catch (e) { if (e instanceof Refusal) refused = e.message; else throw e; }
    }
    const isHtml = t.type === "html";
    const ends: EndTag[] = [];
    if (!isHtml) blockEnds([t], t.type === "text", [], ends);   // a top-level `text` token renders as a paragraph (tagOf)
    const scan = isHtml ? topTags(t.raw) : null;
    const tags = scan ? scan.tags : null;
    const htext = isHtml ? htmlText(t.raw) : "";
    const tag = tagOf(t);
    // the `<p>` an earlier html block left open (pOpen): a block whose element's start tag does not close a `<p>` nests inside it
    // (an inline-level tag's html block, a table, a display formula) and the `<p>` stays open; a stray `</p>` block closes it and
    // mints nothing (topTags read it as the parser's empty `<p>`, which it is only with no `<p>` open); any other block's element
    // closes it (the paragraph's own `<p>`, a heading, a list, a `<pre>`, a `<div>`)
    let nested = false;
    if (openP) {
      if (isHtml) {
        const first = (tags as TopTag[]).find((tt) => tt.depth === 0 && !tt.stray);
        if (first && first.empty) { first.stray = true; delete first.empty; openP = false; }
        else if (first && !CLOSES_P.has(first.tag)) nested = true;
        else if (first) openP = scan!.pOpen;
      } else if (tag === "TABLE" || t.type === "mathBlock") nested = true;
      else openP = false;
    } else if (isHtml) openP = scan!.pOpen;
    // an html block that renders no node of its own: comments alone, or tags that open nothing (a closing tag alone, `</details>`,
    // `</div>`) with no text outside them; the pairing gives it no node and reads past it (before this only a comment block was
    // read past, and a closing tag's block ran the resync, which, before a paragraph carrying an inline closer, confirmed at no
    // end and took every node to the document's end: the Slice 5 review, round 2)
    const blank = isHtml && (commentsOnly(t.raw) || (!(tags as TopTag[]).some((tt) => !tt.stray) && htext === ""));
    out.push({ startN, endN, textEndN, chars: em.chars, pos: em.pos, holes: em.holes, refused, isHtml, blank, tag, tags, ends, minted: false, pOpen: !!scan && scan.pOpen, nested, htext });
  }
  // the wrapper chain: the elements the source leaves open before each block, outermost first, read across the blocks in
  // order as the parser keeps them: an html block's open tags push (the innermost last), its stray end tags pop the chain to
  // the element they name (the parser closes down to it, and ignores an end tag naming no open element), and a block's own
  // inline closers pop the same way when the parser honours them through the block's `<p>` (P_CLOSERS, which mint the empty
  // `<p>`, Block.minted, when the closer stands inside one; FORMATTING, whose adoption agency closes the element and mints
  // nothing); an end tag the parser ignores there (`</label>`, `</span>`) leaves the chain as it is. The source is the model,
  // not the DOM's ancestry: the sanitizer unwraps a `<form>` after the parser minted the `<p>`, so the paragraph's element has
  // no such ancestor left while the node stands (the Slice 5 review, round 2).
  const chain: string[] = [];
  for (const w of out) {
    if (w.isHtml) {
      for (const tt of w.tags || []) {
        if (tt.stray) { const at = chain.lastIndexOf(tt.tag); if (at >= 0) chain.length = at; }
        else if (tt.open) chain.push(tt.tag);
      }
    } else {
      for (const e of w.ends) {
        if (!P_CLOSERS.has(e.tag) && !FORMATTING.has(e.tag)) continue;
        const at = chain.lastIndexOf(e.tag);
        if (at >= 0) { chain.length = at; if (e.p && P_CLOSERS.has(e.tag)) w.minted = true; }
      }
    }
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
  const blocks: Block[] = walkedBlocks(table).map((w) => ({ ...w, dom: [], wrap: [] }));
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
  // the nodes the blocks pair against: the root's children with text, and, spliced in after an element an html block leaves
  // open, that element's own children (below), so the blocks the browser nested inside it pair against them
  let content = topNodes.filter((n) => isElement(n) || stripWs((n as DText).data) !== "");
  const nodeText = new Map<DNode, string>();
  const textKey = (n: DNode): string => stripWs(isText(n) ? n.data : textOf(n));
  for (const n of content) nodeText.set(n, textKey(n));
  if (lexError !== null) {
    blocks.push({ startN: 0, endN: N.length, textEndN: N.length, chars: "", pos: [], holes: [], refused: `markdown the lexer could not parse (${lexError})`,
                  dom: content.slice(), isHtml: false, blank: false, tag: null, tags: null, ends: [], minted: false, pOpen: false, nested: false, htext: "", wrap: [] });
  }
  // ── pair blocks with nodes, in order. Every token but `html` renders as exactly one element, so the
  //    pairing is 1:1 except across an html block, whose node count is unknown (zero for a comment, several
  //    for sibling tags, none of its text if DOMPurify dropped it, and, for a tag the block leaves open, the
  //    browser nests every block after it inside that one element). There the tag scan's reading of the raw
  //    (topTags) goes first: each top-level tag takes the next node when that node is its element, and a tag left
  //    OPEN takes its element's children into `content` right after it, so the blocks after the wrapper pair against
  //    the nodes the browser nested in it (Slice 5 of plans/markdown-viewer.md, the flattened walk: before this the
  //    wrapper took every node to the end of the document and every later selection was refused as an HTML block).
  //    Then the walk resyncs from there: it tries each candidate end and accepts the first from which the following
  //    blocks line up again, by text AND element tag for a block the walk mapped (a kept `<div>Go</div>` or a `Go` the
  //    sanitizer hoisted out of a dropped `<form>` carries the next paragraph's text and is not its `<p>`), by element
  //    tag alone for one it refused, up to the second mapped block with text where two exist before the end or the
  //    next html block (an html `<p>Go</p>` before the paragraph `Go` fits the first and not the second; a note whose
  //    final paragraph follows a text-alike node keeps the one-block rule). So a wrapper's own child in the raw (a
  //    summary) goes to the html block through the resync, and where the scan and the DOM disagree (a dropped or
  //    unwrapped element, a hoisted text) the resync decides as it always did.
  const nodeBlock = new Map<DNode, number>();
  const wrappers: DNode[] = [];
  const tagIs = (node: DNode, tag: string): boolean => isElement(node) && tagNameOf(node) === tag;   // the regions layer's span is its IMG
  const hasElementChild = (n: DNode): boolean => { for (let i = 0; i < n.childNodes.length; i++) if (isElement(n.childNodes[i])) return true; return false; };
  /** the parser's minted `<p></p>` as a node: an element P with no text and no child element (an image paragraph's <p> holds one) */
  const emptyP = (n: DNode): boolean => tagIs(n, "P") && nodeText.get(n) === "" && !hasElementChild(n);
  /** the index past the empty `<p>` the parser minted after block b's node when b closed a wrapper inline (Block.minted, the
   *  source's own reading), k itself when no such node stands at k: the ONE model of the minted `<p>` the run check (runFits)
   *  and the pairing loop share (the Slice 5 review, round 2: the loop stepped over it and the run check did not, so a wrapper
   *  with a leftover closed inline on its only paragraph confirmed its run at no end and the closer was swallowed by the html
   *  block after it) */
  const pastMinted = (b: number, k: number): number => blocks[b].minted && k < content.length && emptyP(content[k]) ? k + 1 : k;
  /** the index past the bare text an html block's unwrapped element left at k (Block.htext: `<option>Opt.</option>`, a `<form>`'s
   *  lead): the run of text nodes and highlight marks from k whose text together is the block's, else k. A MARK is read as its text
   *  because a comment on the hoisted text wraps it in one, a top-level `<mark>` when the text is top-level (the Slice 5 review,
   *  round 3: the read accepted a Text node alone, so once such a comment painted, the re-analysis met the mark where the text was
   *  expected, no end confirmed, and the html block before took every node to the document's end; a comment over part of the text
   *  splits it, so the run is read, not one node) */
  const pastHoisted = (blk: Block, k: number): number => {
    if (blk.htext === "") return k;
    let acc = "", kk = k;
    while (kk < content.length && acc.length < blk.htext.length && (isText(content[kk]) || tagIs(content[kk], "MARK"))) { acc += nodeText.get(content[kk]); kk++; }
    return acc === blk.htext ? kk : k;
  };
  const firstTag = (blk: Block): TopTag | undefined => blk.tags ? blk.tags.find((tt) => tt.depth === 0 && !tt.stray) : undefined;
  /** the index past the nodes at k that are the open tag's own children in the raw (TopTag.kids: a summary, a lead text, a banner's
   *  picture, heading and tagline), read in order while the DOM holds each where the raw puts it: an element by its tag (the regions
   *  layer's span for a picture, tagNameOf), a text run by a text node; a child the sanitizer drops with its text (DROPPED_CONTENT, a
   *  non-checkbox input) has no node and is passed over, one it unwraps (UNWRAPPED) leaves its text as a bare node where the raw had
   *  the element; the first child the DOM does not hold as the raw describes ends the read, and the resync below decides from
   *  there. These nodes are the html block's own (they were the block's through the resync before), read past so the run check
   *  and the next html block's scan start at the wrapper's first nested block (the review's round 3: the next block's same-tag
   *  element took the leftover, `<div class="in">` after `<div align="center"><div>Lead</div>`) */
  const pastKids = (tt: TopTag, k: number): number => {
    for (const kid of tt.kids || []) {
      if (k >= content.length) break;
      const c = content[k];
      if (kid === "#text" ? isText(c) : tagIs(c, kid)) { k++; continue; }
      if (DROPPED_CONTENT.has(kid) || kid === "INPUT") continue;
      if (UNWRAPPED.has(kid)) { if (isText(c)) k++; continue; }
      break;
    }
    return k;
  };
  /** where a block whose scan took nothing and whose run no end confirms hands the nodes back: the index from k of the next html
   *  block's own element (the first top-level tag of the first block after b with one, by tag, an empty `<p>` by emptiness) and
   *  that block, so the blocks between are passed over and its scan resumes there; content.length and blocks.length when no later
   *  html block has an element in the content */
  const nextAnchor = (b: number, k: number): { at: number; block: number } => {
    for (let x = b + 1; x < blocks.length; x++) {
      const nb = blocks[x];
      if (!nb.isHtml || nb.blank || nb.nested) continue;
      const first = firstTag(nb);
      if (!first) continue;
      for (let i = k; i < content.length; i++) if (tagIs(content[i], first.tag) && (!first.empty || emptyP(content[i]))) return { at: i, block: x };
      break;
    }
    return { at: content.length, block: blocks.length };
  };
  const fits = (blk: Block, node: DNode): boolean => {
    if (blk.refused !== null) return blk.tag === null || tagIs(node, blk.tag);
    if (nodeText.get(node) !== blk.chars) return false;
    // an image paragraph pairs by its empty text alone: the regions layer wraps a top-level picture in a span while the
    // Comments panel is open (file-comments-regions.ts), and its block must go on pairing with that span
    return blk.chars.length === 0 || blk.tag === null || tagIs(node, blk.tag);
  };
  const runFits = (b: number, k: number): boolean => {
    let confirmed = 0;
    for (; b < blocks.length; b++) {
      const blk = blocks[b];
      if (blk.isHtml) {
        // an html block with no element of its own (a comment, a closing tag alone: blank) has no node and is read past; the
        // next html block with a tag resyncs on its own, and the run ends here when that tag's element is the node at k: a node
        // the wrapper before it left over (its summary, its lead text) is not that element, so the run reaches past it to
        // the element, the wrapper keeps the leftover and the next block's scan finds its own (before this the run ended at
        // any html block, the summary stayed in `content`, the next wrapper's scan took nothing and it fell to every node to
        // the end of the document). An element nowhere in the content is no node of the block's: the sanitizer dropped it,
        // and the block is read past like a comment's, or unwrapped it and left its text as a bare node at k, which the block
        // reads past with it (an `<option>Opt.</option>` after a wrapper; before this the text stood where the next
        // paragraph's element was expected and the wrapper's run confirmed at no end: the Slice 5 review, round 2).
        const first = firstTag(blk);
        if (blk.blank || blk.nested || !first) continue;
        const isFirst = (x: number): boolean => tagIs(content[x], first.tag) && (!first.empty || emptyP(content[x]));
        if (k < content.length && isFirst(k)) return true;
        for (let x = k + 1; x < content.length; x++) if (isFirst(x)) return false;
        k = pastHoisted(blk, k);
        continue;
      }
      if (blk.nested) continue;   // its element is inside the open `<p>` before it: no top-level node
      if (k >= content.length) return confirmed > 0 || (blk.refused !== null && blk.chars.length === 0);
      if (!fits(blk, content[k])) return false;
      k = pastMinted(b, k + 1);   // the empty `<p>` the parser minted after a block closing a wrapper inline is no block's node
      if (blk.refused === null && blk.chars.length > 0 && ++confirmed === 2) return true;   // two mapped blocks with text confirm the run
    }
    return true;
  };
  let j = 0;
  let handedTo = 0;   // the blocks before this index were swallowed by an html block whose run confirmed at no end (nextAnchor)
  for (let b = 0; b < blocks.length; b++) {
    const blk = blocks[b];
    if (lexError !== null) { for (const n of blk.dom) nodeBlock.set(n, b); break; }
    if (b < handedTo) {
      // inside a swallowed run: the block's nodes, if any, are the swallowing html block's, and the next html block's scan resumes
      // at its own element (before this the blocks here took the nodes from there on, one each, as mismatches)
      if (blk.refused === null) blk.refused = "a block whose rendered text does not match the file";
      continue;
    }
    if (blk.isHtml) {
      blk.refused = blk.refused || "an HTML block";
      if (!blk.blank && !blk.nested) {
        // an element the raw leaves open: its children (elements, and text that is not blank, as at the top level) join the
        // pairing right after it, and it is one of the block's wrappers
        const splice = (node: DNode, at: number): void => {
          const kids: DNode[] = [];
          for (let i = 0; i < node.childNodes.length; i++) {
            const c = node.childNodes[i];
            if (isElement(c) || (isText(c) && stripWs(c.data) !== "")) { kids.push(c); nodeText.set(c, textKey(c)); }
          }
          content = content.slice(0, at).concat(kids, content.slice(at));
          blk.wrap.push(node); wrappers.push(node);
        };
        let k = j;
        let holder: DNode | null = null;   // the open element the next deeper open tag's element is the last element child of
        for (const tt of blk.tags || []) {
          if (tt.stray) continue;   // an end tag for an earlier block's element: it opens nothing and takes no node
          if (tt.depth > 0) {
            let inner: DNode | null = null;
            const kids: ArrayLike<DNode> = holder ? holder.childNodes : [];
            for (let i = kids.length - 1; i >= 0; i--) { const c: DNode = kids[i]; if (isElement(c)) { inner = tagIs(c, tt.tag) ? c : null; break; } }
            if (inner) splice(inner, content.indexOf(inner, k) + 1);
            holder = inner;
            continue;
          }
          // dropped, unwrapped or reshaped between the raw and the DOM: the resync below decides
          if (k >= content.length || !tagIs(content[k], tt.tag) || (tt.empty && !emptyP(content[k]))) { holder = null; continue; }
          const node = content[k++];
          holder = tt.open ? node : null;
          if (tt.open) { splice(node, k); k = pastKids(tt, k); }
        }
        let jj = -1;
        for (let kk = k; kk <= content.length; kk++) if (runFits(b + 1, kk)) { jj = kk; break; }
        // no end lines the following blocks up (the block after this one is a mismatch: a list item whose source text the
        // sanitizer shortened, blank-scenes.json's stripped-style scene): the scan's answer stands where it took an element,
        // and the mismatch is refused with its own node; where the scan took nothing the block takes every node up to the next
        // html block's own element, where that block's scan resumes (the review's round 3: to the document's end before, so a
        // `<button>` opener whose paragraph's own `<button>` closed it lost every later paragraph, where main's resync at each
        // html block had recovered the ones after the next)
        if (jj < 0) { if (k > j) jj = k; else { const a = nextAnchor(b, k); jj = a.at; handedTo = a.block; } }
        blk.dom = content.slice(j, jj);
        j = jj;
      }
    } else if (blk.nested) {
      // inside the `<p>` an html block left open: no top-level node of its own
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
    // a block whose inline html closes a wrapper open around it (`**Bold** </div>`, `Last line.</details>`, a quoted `> line
    // </div>`, a loose item's; Block.minted, from the wrapper chain the source describes): the parser closed the block's `<p>`
    // with the wrapper and minted an empty `<p></p>` right after the wrapper's children for the paragraph's own stray `</p>`,
    // a node no block renders as; the pairing steps over it, through the model runFits reads too (before this the next
    // paragraph took the empty `<p>` as a mismatch and every block after paired one node early, a repeated paragraph mapping
    // to the wrong copy). A closer naming no open wrapper mints nothing and nothing is skipped.
    if (blk.dom.length) j = pastMinted(b, j);
    for (const n of blk.dom) nodeBlock.set(n, b);
  }
  return { source, shape: shapeOf(root, source, wrappers), N, nStart, blocks, topNodes, topStart, total, nodeBlock, wrappers };
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
// Four reads over the private table: the top-level blocks of a source as spans (sourceBlockSpans), which block a
// rendered node stands for (renderedBlockIndex), which elements a block renders as (renderedBlockElements), and which
// of a block's elements hold the blocks the browser nested in them (renderedBlockWrappers). A REFUSED block answers all
// four (its node is paired by tag, and the reader's place needs an element to measure, not text to quote), where
// renderedSpot, built for a point inside the prose, answers null for one. A node the pairing could not place (whitespace
// between blocks, a node an html block's resync left over, at the top level or inside a wrapper) is no block's, and the
// caller reads the next node.

/** The top-level blocks of `source` in order, each its source span (first character to the end of its text, the blank
 *  lines a token swallows after it excluded), from the same placement the rendered index pairs elements by, so block b
 *  here is block b there (renderedBlockIndex, renderedBlockElements). Markdown the lexer could not parse is one block
 *  over the whole text. For the reader's place (reader-place.ts): the blocks of the Raw view, which its rows alone do
 *  not show (a blank row between two paragraphs belongs to neither, one inside a fenced code block to the code block).
 *  The last source's table is kept (sourceTable): the viewer reads the same text once per scroll frame. */
export function sourceBlockSpans(source: string): SourceRange[] { return sourceTable(source).spans; }

/** The index, into sourceBlockSpans(source), of the block that renders `node`: a child of `renderedRoot`, or a child of
 *  an element renderedBlockWrappers names (a paragraph the browser nested inside an unclosed `<div>`); -1 when `node` is
 *  no block's (whitespace between blocks, a node an html block's resync left over). */
export function renderedBlockIndex(renderedRoot: Element, source: string, node: Node): number {
  const idx = renderedIndex(renderedRoot as unknown as DElement, source);
  const b = idx.nodeBlock.get(node as unknown as DNode);
  return b === undefined ? -1 : b;
}

/** The elements block `b` renders as, in order: one for most blocks (a paragraph nested inside an html wrapper included:
 *  its own `<p>`), several for an html block of sibling tags, the wrapper and its summary for an html block that leaves a
 *  `<details>` open, none for a comment, a block the sanitizer dropped or a closing tag alone (`</div>`). */
export function renderedBlockElements(renderedRoot: Element, source: string, b: number): Element[] {
  const idx = renderedIndex(renderedRoot as unknown as DElement, source);
  const blk = idx.blocks[b];
  return blk ? (blk.dom.filter((n) => isElement(n)) as unknown as Element[]) : [];
}

/** The elements of block `b` whose children the pairing took into the block table, in order: an element the html block's
 *  raw leaves open (`<div align="center">`, `<details><summary>x</summary>` with a blank line after it), which the browser
 *  nests the markdown after the block inside, so the blocks after it render as that element's children and pair with them
 *  (analyzeRendered, the tag scan topTags); two for `<div><div>` in one block. Empty for every other block, so a non-empty
 *  answer says block `b` is a wrapper's. For the reader's place (reader-place.ts), which reads the Rendered view's blocks
 *  through the top-level elements: an element in this answer stands for the blocks nested in it, and the reader reads its
 *  element children in its place; an element paired to the same block that is NOT in it (the wrapper's own summary) is a
 *  row of the block's own. A child no block took (a node the resync left over) answers -1 from renderedBlockIndex as a
 *  top-level leftover does. */
export function renderedBlockWrappers(renderedRoot: Element, source: string, b: number): Element[] {
  const idx = renderedIndex(renderedRoot as unknown as DElement, source);
  const blk = idx.blocks[b];
  return blk ? (blk.wrap.slice() as unknown as Element[]) : [];
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

/** Every formula element (FORMULA_CLASSES) under `n` in document order, none looked into. */
function formulaElements(n: DNode, out: DNode[] = []): DNode[] {
  if (isControl(n)) { if (isFormula(n)) out.push(n); return out; }
  for (let i = 0; i < n.childNodes.length; i++) formulaElements(n.childNodes[i], out);
  return out;
}
/** The Raw offer for a selection that touched a formula through its ELEMENT (a boundary inside it): the block that renders
 *  the nearest node above the formula that a block renders as (a top-level node, or a paragraph the browser nested inside
 *  an html wrapper, whose block is then the paragraph's and not the wrapper's), and the hole the element stands for, the
 *  k-th formula hole of the block for the k-th formula element under the node (the walk pushes holes in source order and
 *  the renderer emits elements in the same order). The Raw view opens at the hole and preselects it: the formula with its
 *  delimiters, `$E = mc^2$` or the `$$` block through its closing line (the hole's span less the line feeds a display
 *  block's raw carries after it, and any indent before it), so the composer quotes the formula (the owner's ruling 7: the
 *  whole formula, not the TeX between the delimiters). KaTeX's glyphs are not the source's text, so the offer every other
 *  refusal makes, the selected text's occurrence (rawExtra), is the answer only where the hole is not found: the block's
 *  own start when the count disagrees (a placeholder an author typed by hand renders a formula the walk never saw), or a
 *  formula under no block. The same fields blockExtra gives a hole touched through its characters. */
/** The block a formula ELEMENT belongs to and the hole it stands for: the block that renders the nearest node above the formula
 *  that a block renders as (a top-level node, or a paragraph the browser nested inside an html wrapper, whose block is then the
 *  paragraph's and not the wrapper's), and the k-th formula hole of the block for the k-th formula element under the node (the
 *  walk pushes holes in source order and the renderer emits elements in the same order); `hole` null when the count disagrees
 *  (a placeholder an author typed by hand renders a formula the walk never saw), the whole answer null for a formula under no
 *  block. */
function formulaHole(idx: RenderedIndex, root: DNode, control: DNode): { blk: Block; hole: Hole | null } | null {
  let top: DNode = control;
  while (top !== root && idx.nodeBlock.get(top) === undefined && top.parentNode) top = top.parentNode;
  const b = top === root ? undefined : idx.nodeBlock.get(top);
  if (b === undefined) return null;
  const blk = idx.blocks[b];
  const k = formulaElements(top).indexOf(control);
  const holes = blk.holes.filter((h) => h.reason === FORMULA_HOLE);
  return { blk, hole: k >= 0 && k < holes.length ? holes[k] : null };
}
/** A formula hole's span as the Raw view preselects it: the formula with its delimiters, less the line feeds a display block's
 *  raw carries after it and any indent before it (source offsets). */
function formulaSpan(idx: RenderedIndex, hole: Hole): SourceRange {
  let s = hole.startN, e = hole.endN;
  while (s < e && isWs(idx.N[s])) s++;
  while (e > s && isWs(idx.N[e - 1])) e--;
  return { start: nOf(idx, s), end: nOf(idx, e) };
}
function formulaExtra(idx: RenderedIndex, root: DNode, control: DNode, gs: number, ge: number): Partial<MapRefusal> {
  const selectedRaw = (): Partial<MapRefusal> => {
    let selected = "";
    for (const n of idx.topNodes) { selected += isText(n) ? n.data : textOf(n); }
    const rawRange = srcRangeOf(idx, selected.slice(gs, ge).trim());
    return rawRange ? { rawHasQuote: true, rawRange } : { rawHasQuote: false };
  };
  const fh = formulaHole(idx, root, control);
  if (!fh) return selectedRaw();
  const { blk, hole } = fh;
  const off = nOf(idx, hole ? hole.startN : blk.startN);
  const raw: Partial<MapRefusal> = hole ? { rawHasQuote: true, rawRange: formulaSpan(idx, hole) } : selectedRaw();
  return { blockStartLine: rawOffsetToLine(idx.source, off), blockStartOffset: off, ...raw };
}

/** The node before `n` in document order that is not an ancestor of it, below `root`: its previous sibling, or the previous
 *  sibling of the nearest ancestor below `root` that has one; null at the root's start (nextAfter's mirror). */
function prevBefore(root: DNode, n: DNode): DNode | null {
  for (let c: DNode | null = n; c && c !== root; c = c.parentNode) { const s = sibling(c, -1); if (s) return s; }
  return null;
}
/** The formula a selection boundary (node, offset) that is inside no control stands beside on the selection's side: the first
 *  thing after it (isStart) or before it in document order that is not white space, elements descended into, when that thing
 *  is a formula (isFormula) and lies before the selection's OTHER boundary (`other`); null when it is text, another control, an
 *  element with no children, the root's end, or the other boundary comes first. A boundary on the paragraph itself before its
 *  first child (a Range set there; in headless Chromium no click puts one there, the review's round 3 measured: a triple-click
 *  on a formula-first paragraph's words anchors on the text after the formula at its start, so the words alone map, and one on
 *  the glyphs anchors inside them and is the formula's), and one at the next block's start after a paragraph ending in a
 *  formula, the line feed between the blocks in between, both cover the formula whole. */
function formulaBeside(root: DNode, node: DNode, offset: number, isStart: boolean, other: { node: DNode; offset: number }): DNode | null {
  let n: DNode | null;
  // the first node at or past the selection's OTHER boundary in the walk's direction: the walk stops there, so a formula beyond it,
  // beside a selection of whitespace alone, is not covered (the Slice 5 review, round 3: a selection of the one space after
  // `$E = mc^2$`, or of the gap before a formula-first paragraph, was refused as touching the formula, with the Raw offer at it,
  // where it is whitespace alone)
  const stop: DNode | null = isText(other.node) ? other.node
    : isStart ? other.node.childNodes[other.offset] || nextAfter(root, other.node)
    : other.offset > 0 ? other.node.childNodes[other.offset - 1] : prevBefore(root, other.node);
  if (isText(node)) {
    if (stripWs(isStart ? node.data.slice(offset) : node.data.slice(0, offset)) !== "") return null;   // text on the selection's side
    if (node === stop) return null;   // both boundaries in one text node: nothing outside it lies between them
    n = isStart ? nextAfter(root, node) : prevBefore(root, node);
  } else {
    const kid = isStart ? node.childNodes[offset] : offset > 0 ? node.childNodes[offset - 1] : undefined;
    n = kid || (isStart ? nextAfter(root, node) : prevBefore(root, node));
  }
  while (n) {
    if (n === stop) return null;
    if (isText(n)) {
      if (stripWs(n.data) !== "") return null;
      n = isStart ? nextAfter(root, n) : prevBefore(root, n);
      continue;
    }
    if (isFormula(n)) return n;
    if (isControl(n) || !n.childNodes.length) return null;
    n = isStart ? n.childNodes[0] : n.childNodes[n.childNodes.length - 1];
  }
  return null;
}

export function mapRenderedSelection(sel: SelLike, renderedRoot: Element, source: string): MapResult {
  const root = renderedRoot as unknown as DElement;
  if (sel.isCollapsed || !sel.anchorNode || !sel.focusNode) return refuse("Select some text to comment on.");
  const idx = renderedIndex(root, source);
  const a = boundaryIndex(root, sel.anchorNode as unknown as DNode, sel.anchorOffset, null);
  const f = boundaryIndex(root, sel.focusNode as unknown as DNode, sel.focusOffset, null);
  if (a === null || f === null) return refuse("The selection reaches outside the rendered text.");
  // A boundary inside a control stands at the control's place: the control's text is the viewer's (a back link's number, a
  // fold label, a gated figure's label), so a selection that begins or ends on it begins or ends beside it, and a
  // triple-click on a footnote definition maps the definition's words. A FORMULA is the note's, though not text the mapping
  // places (its token is a zero-text hole): a boundary strictly inside one means the person selected part of the formula, and
  // the answer is the hole's, "touches a formula", with the Raw view offered at the formula. Two edges are not that. The edge
  // that selects none of it: a selection ending at a formula's first character (a triple-click on the paragraph before a
  // display formula puts its focus there) or starting past its last, which stands at the formula's place like any control.
  // And the edge that covers it WHOLE: a selection starting at the formula's first character, or ending at its last, with
  // its other end outside the formula, selected the formula and the prose beside it, which is prose holding a formula, and
  // maps as a drag from the prose before a formula into the prose after it does, the formula's source inside the quote
  // (the owner's ruling, the Slice 5 review's round 2; before this a selection begun on a formula-first paragraph's first glyph
  // was refused as the formula, and the Raw view preselected the formula alone). The same when the boundary stands beside the
  // formula from OUTSIDE it, with only white space between and the formula inside the selection (a boundary on the paragraph
  // before its first child, a Range's shape; one at the next block's start after a paragraph ending in a formula; a drag
  // released right after a formula's last glyph ends in the text node after it): the formula that is the first thing on the
  // selection's side of the boundary, before the other boundary, is covered (formulaBeside; a selection of whitespace alone
  // beside a formula covers nothing and is only whitespace, the review's round 3). In headless Chromium a triple-click on such
  // a paragraph's words anchors on the text after the formula at its start, so the words alone map, and one on the glyphs
  // anchors inside them (the round 3 measurement; md-config-math-map-browser.test.ts). A formula covered whole with no text
  // beside it in the selection (a triple-click on a display formula, or on a paragraph that is a formula alone) is the
  // formula's still.
  const sa = boundaryAt(a, idx.total), sf = boundaryAt(f, idx.total);
  const gs = Math.min(sa, sf), ge = Math.max(sa, sf);
  const FORMULA_TOUCHED = "This selection touches a formula; comment on it from the Raw view.";
  // a formula at the selection's END is an obstacle like a hole's: named after the obstacles before it in the span (the pass
  // below), so a drag from a table cell into a formula's glyphs names the table, the obstacle the person's eye meets first;
  // one at the START is the first obstacle and is named at once
  let formulaEnd: Partial<MapRefusal> | null = null;
  const covered: DNode[] = [];   // the formulas the selection covers whole, at its start or its end
  for (const [x, sx, other, o] of [[a, sa, sf, f], [f, sf, sa, a]] as const) {
    if (!inControl(x) || !isFormula(x.control)) continue;
    const isStart = sx < other, isEnd = sx > other;
    if (isStart ? x.inner >= x.len : isEnd ? x.inner <= 0 : false) continue;   // the start past its end, or the end at its start: none of it
    const whole = !(inControl(o) && o.control === x.control) && (isStart ? x.inner <= 0 : isEnd ? x.inner >= x.len : false);
    if (whole) { covered.push(x.control); continue; }
    if (sx <= other) return refuse(FORMULA_TOUCHED, formulaExtra(idx, root, x.control, gs, ge));
    formulaEnd = formulaExtra(idx, root, x.control, gs, ge);
  }
  if (sa !== sf) {
    const A = { node: sel.anchorNode as unknown as DNode, offset: sel.anchorOffset }, Fo = { node: sel.focusNode as unknown as DNode, offset: sel.focusOffset };
    for (const [x, at, other, isStart] of [[a, A, Fo, sa < sf], [f, Fo, A, sf < sa]] as const) {
      if (typeof x !== "number") continue;   // inside a control (above), or outside the root (the edge snaps)
      const F = formulaBeside(root, at.node, at.offset, isStart, other);
      if (F && covered.indexOf(F) < 0) covered.push(F);
    }
  }
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
  // the block at a node's edge: the node's own, or, for a wrapper (an element whose children the pairing took, Block.wrap),
  // the first or last nested block's, down through nested wrappers, so a boundary snapping onto a wrapper's box lands on
  // the prose inside it and not on the wrapper's own refused block
  const edgeBlock = (n: DNode, isStart: boolean): number => {
    let node = n;
    for (;;) {
      if (idx.wrappers.indexOf(node) < 0) return idx.nodeBlock.get(node) as number;
      const kids = node.childNodes;
      let hit: DNode | null = null;
      for (let u = isStart ? 0 : kids.length - 1; isStart ? u < kids.length : u >= 0; isStart ? u++ : u--) if (idx.nodeBlock.get(kids[u]) !== undefined) { hit = kids[u]; break; }
      if (!hit) return idx.nodeBlock.get(node) as number;
      node = hit;
    }
  };
  // whitespace between blocks snaps to the next block for a start and the previous for an end: among the siblings of the
  // whitespace node first (the top level's, or a wrapper's children), then at each level above it
  const snapFrom = (from: DNode, isStart: boolean): { b: number; k: number } | null => {
    for (let n: DNode = from; n.parentNode; n = n.parentNode) {
      const kids = n.parentNode.childNodes;
      let i = 0;
      while (i < kids.length && kids[i] !== n) i++;
      for (let u = isStart ? i + 1 : i - 1; isStart ? u < kids.length : u >= 0; isStart ? u++ : u--) {
        if (idx.nodeBlock.get(kids[u]) === undefined) continue;
        const bb = edgeBlock(kids[u], isStart);
        return { b: bb, k: isStart ? 0 : idx.blocks[bb].chars.length };
      }
      if (n.parentNode === root) break;
    }
    return null;
  };
  // the deepest node under `top` holding index `c` of its text that a block renders as, and the index inside it: the
  // pairing maps the blocks the browser nested inside an html wrapper (analyzeRendered), so a top-level node's block may
  // be the wrapper's while the character belongs to a nested paragraph's. Whitespace between nested blocks snaps as the
  // top level's does; a descendant with no block under a wrapper (a node the resync left over) is no block's, as at the
  // top level; one under any other node (a paragraph's own text) keeps that node's block, and so does a summary, whose
  // block is the wrapper's, refused.
  const descend = (top: DNode, c: number, isStart: boolean): { b: number; k: number } | null => {
    let node = top, b = idx.nodeBlock.get(top) as number;
    for (;;) {
      if (!isElement(node) || isControl(node)) break;
      let off = 0, hit: DNode | null = null, hitOff = 0;
      for (let i = 0; i < node.childNodes.length; i++) {
        const ch = node.childNodes[i];
        if (!isElement(ch) && !isText(ch)) continue;
        const len = isText(ch) ? ch.data.length : textLenUnder(ch, true, null);
        // the child holding index c for a start, the one holding the character before c for an end (c is exclusive there)
        if (isStart ? c < off + len : c > off && c <= off + len) { hit = ch; hitOff = off; break; }
        off += len;
      }
      if (!hit) break;
      const hb = idx.nodeBlock.get(hit);
      if (hb === undefined) {
        if (idx.wrappers.indexOf(node) < 0) break;   // a node's own text
        return isText(hit) && stripWs(hit.data) === "" ? snapFrom(hit, isStart) : null;
      }
      b = hb; node = hit; c -= hitOff;
    }
    return { b, k: nonWsBefore(node, c) };
  };
  // A start boundary stands at the node holding index g; an end boundary at the node holding the LAST character it selects (g - 1),
  // its offset one past that character: a selection ending exactly where a paragraph's text ends belongs to that paragraph, not to
  // the node that starts at the same index (the Slice 5 review, round 3, and main before it: the end read as the next node at its
  // offset 0, and where that node was a refused block's, a bare text node the parser hoisted out of a dropped `<td>` or a mark a
  // comment painted over a form's lead, a whole-paragraph selection right before it was refused as touching that block, while a
  // selection stopping one character short mapped; a mapped next block snapped back on its offset 0, a refused one has no offset)
  const locate = (g: number, isStart: boolean): { b: number; k: number } | null => {
    if (g >= idx.total) { const b = prevBlock(idx.blocks.length - 1); return b < 0 ? null : { b, k: idx.blocks[b].chars.length }; }
    const { t, c } = topAt(idx, isStart ? g : g - 1);
    const node = idx.topNodes[t];
    const b = idx.nodeBlock.get(node);
    if (b === undefined) {
      if (isText(node) && stripWs(node.data) === "") return snapFrom(node, isStart);   // whitespace between blocks
      return null;   // a node no block accounts for
    }
    return descend(node, isStart ? c : c + 1, isStart);
  };
  // a selection the text cannot place, or of whitespace alone, that ends inside a formula still touched the formula; one that
  // covered a formula whole and holds no text beside it selected the formula
  const orFormula = (r: MapResult): MapResult => formulaEnd ? refuse(FORMULA_TOUCHED, formulaEnd)
    : covered.length ? refuse(FORMULA_TOUCHED, formulaExtra(idx, root, covered[0], gs, ge)) : r;
  const S = locate(gs, true), E = locate(ge, false);
  if (!S || !E) return orFormula(refuse("The selection could not be matched to the file text.", rawExtra()));
  let { b: bs, k: ks } = S;
  let { b: be, k: ke } = E;
  if (idx.blocks[bs].refused === null && ks >= idx.blocks[bs].chars.length) { bs = nextBlock(bs + 1); ks = 0; }
  if (be >= 0 && idx.blocks[be].refused === null && ke === 0) { be = prevBlock(be - 1); if (be >= 0) ke = idx.blocks[be].chars.length; }
  if (bs < 0 || be < 0) return orFormula(refuse("The selection is only whitespace.", rawExtra()));
  // The obstacles in the span, in document order, the first one named: a refused block with an element on the page (an html
  // block, a mismatch) refuses when the pass reaches it, and a mapped block's selected characters are read for a hole (a
  // table, a code block, a footnote's number) before the block after it is looked at, so a selection from a table cell into
  // an html block after it is refused as touching the table, the obstacle the person's eye meets first (before this, every
  // refused block in the span was named ahead of any hole, and a span from a table into a `<details>` summary named the
  // HTML block). A refused block that rendered nothing (a comment, a closing tag alone) is never in the way: its source
  // travels inside the quote. The span's characters are read only when the endpoints stand in order (bs <= be): a
  // selection of the whitespace between two blocks lands its start on the block after and its end on the block before, and
  // that block's text, which the person did not select, is not scanned for a hole. A formula the selection ends inside
  // (formulaEnd) stands after every character the pass reads, so it is named last, when the pass met nothing before it.
  const lo = Math.min(bs, be), hi = Math.max(bs, be);
  for (let b = lo; b <= hi; b++) {
    const blk = idx.blocks[b];
    if (blk.refused !== null) {
      if (visible(blk)) return refuse(`This selection touches ${blk.refused}; comment on it from the Raw view.`, blockExtra(blk));
      continue;
    }
    if (bs > be) continue;
    const from = b === bs ? ks : 0, to = b === be ? ke : blk.chars.length;
    for (let k = from; k < to; k++) {
      const p = blk.pos[k];
      if (p < 0) { const h = blk.holes[-p - 1]; return refuse(`This selection touches ${h.reason}; comment on it from the Raw view.`, blockExtra(blk, h.startN)); }
    }
  }
  if (formulaEnd) return refuse(FORMULA_TOUCHED, formulaEnd);
  if (bs > be || (bs === be && ks >= ke)) return orFormula(refuse("The selection is only whitespace.", rawExtra()));
  let start = nOf(idx, idx.blocks[bs].pos[ks]);
  let end = nOf(idx, idx.blocks[be].pos[ke - 1]) + 1;
  // a formula covered whole at an end of the selection travels inside the quote, with its delimiters, as one between two
  // selected words does; where its hole is not found (the count disagrees) the prose alone is the quote
  for (const c of covered) {
    const fh = formulaHole(idx, root, c);
    if (!fh || !fh.hole) continue;
    const span = formulaSpan(idx, fh.hole);
    if (span.start < start) start = span.start;
    if (span.end > end) end = span.end;
  }
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

/** White space the browser collapses: HTML's ASCII white space (space, tab, line feed, form feed, carriage return), which
 *  CSS's white-space processing folds into one space inside a line and drops at a line's edges. JavaScript's `\s` matches these
 *  AND the Unicode spaces (a no-break space, an ideographic space, an em space, a thin space), which the browser renders as
 *  glyphs of their own width wherever they stand (3.89 px for U+00A0 and 14 px for U+3000 at 14px sans-serif in Chromium), so
 *  the block-neighbour pre-skip (skipBlockWs) reads this set and no other: a node of Unicode spaces between two blocks renders
 *  a blank line and is painted, as on main (the Slice 4 review, round 10; md-config-paint-rendered-space.test.ts and its browser
 *  leg). stripWs, which the walk and the matching use, keeps `\s`: the source and the rendering agree on it either way. */
const COLLAPSIBLE_WS_ONLY = /^[ \t\n\r\f]*$/;
const isCollapsibleWs = (s: string): boolean => COLLAPSIBLE_WS_ONLY.test(s);
/** Text the root guard skips (skipBlockWs): JavaScript's `\s`, the block pairing's own alphabet (stripWs, analyzeRendered), plus
 *  the format characters, Unicode's Cf (the zero width space, joiner and non-joiner, the word joiner and the invisible operators,
 *  the bidi marks, embeddings and isolates, a soft hyphen, U+FEFF), which render no glyph anywhere. A text node of these alone
 *  directly under the render root is the white space between two blocks, or the zero-width run an html block leaves at the top
 *  level (`<p>x</p>` U+200B `<p>y</p>`, pasted from a web page), never the passage's text, and a mark there would be a
 *  top-level child of the root. Round 11's guard read `\s` alone and painted a lone U+200B at the top level as the sheet's
 *  padding around nothing on a line of its own (the Slice 4 review, round 12; md-config-paint-collapsed-blank.test.ts). */
const ROOT_BLANK = /^[\s\p{Cf}]*$/u;
/** Every tag the sanitizer keeps (DOMPurify's html profile less MD_FORBID_TAGS, md-sanitize.ts) that Chromium lays out as a
 *  block-level box or a table or one of a table's parts (display block, list-item, table, table-caption, table-column, the
 *  row and column groups, table-row, table-cell), the document's own `html` and `body`, which the parser never places in a
 *  fragment, left out. Read that way, not hand-picked: an author's html block can hold any element the sanitizer lets
 *  through, so the list is the sanitizer's, not CommonMark's html-block tag list (an `<hgroup>` is not on that list and
 *  stands inside an author's `<details>` all the same). The Slice 4 review's round 8 wrote the list by hand and left out
 *  `center`, `dir`, `menu` and `search`, kept by the sanitizer and blocks in Chromium, while naming `form` and `fieldset`,
 *  which the sanitizer strips (round 9; md-config-paint-whitespace-browser.test.ts derives the set from the sanitizer's
 *  own allowlist and the browser's computed display and holds it equal to this one; md-config-block-boxes.test.ts holds it
 *  in node, where CI runs and the browser leg skips, equal to the Rendering section's block-level tags
 *  (anchor-map-fixtures/block-tags.json) the installed DOMPurify's allowlist keeps, less MD_FORBID_TAGS, html and body,
 *  round 10). The set serves one reading, the block-neighbour pre-skip of skipBlockWs: a text node of collapsible white space
 *  with one of these on both sides, or a block-box parent's edge, makes no line box at all and is skipped without a
 *  measurement; every other blank is painted and measured (trimCollapsedMarks). KaTeX's display root, the one span the sheets
 *  lay out as a block (`.katex-display`), is read by its class (isBlockBox). Exported for the tests alone. */
export const BLOCK_BOXES: ReadonlySet<string> = new Set([
  "P", "DIV", "UL", "OL", "LI", "MENU", "DIR", "BLOCKQUOTE", "PRE", "HR", "CENTER", "SEARCH", "HGROUP", "H1", "H2", "H3", "H4", "H5", "H6",
  "TABLE", "CAPTION", "COLGROUP", "COL", "THEAD", "TBODY", "TFOOT", "TR", "TD", "TH",
  "DETAILS", "SUMMARY", "FIGURE", "FIGCAPTION", "DL", "DT", "DD",
  "SECTION", "ARTICLE", "ASIDE", "NAV", "HEADER", "FOOTER", "MAIN", "ADDRESS",
]);
const isBlockBox = (n: DNode): boolean => isElement(n) && (BLOCK_BOXES.has(n.tagName.toUpperCase()) || hasClass(n, "katex-display"));
/** The sibling of `n` on the side `dir` (-1 before, 1 after), null at the parent's edge: the DOM's own pointer when the node
 *  offers one (a browser's Node: constant time a step), else by the index of `n` in its parent's child list (the tests'
 *  stand-ins). Indexing every time made a paint quadratic in a paragraph's inline children: each space between two inline
 *  elements is a whitespace-only node the paint reads the neighbours of, and each read scanned the paragraph's child list from
 *  the start, so one mark across a paragraph of 3,000 links cost 850 ms in Chromium against 27 ms before the neighbour
 *  rule; with the pointers 32 ms (the Slice 4 review, round 9; md-config-paint-whitespace.test.ts counts the child-list reads,
 *  its browser leg times equal work). */
function sibling(n: DNode, dir: -1 | 1): DNode | null {
  const s = dir < 0 ? n.previousSibling : n.nextSibling;
  if (s !== undefined) return s;
  const p = n.parentNode;
  if (!p) return null;
  const kids = p.childNodes;
  for (let k = 0; k < kids.length; k++) if (kids[k] === n) { const j = k + dir; return j >= 0 && j < kids.length ? kids[j] : null; }
  return null;
}
/** Whether the Rendered paint leaves the whitespace-only text node `t` unmarked without measuring it. Two readings of the DOM,
 *  each exact, are all the painter predicts about white space; every other blank in a range is painted, and the browser's own
 *  layout decides afterwards (trimCollapsedMarks: a mark whose text is blank and lays out at zero width is unwrapped).
 *  1. The root guard. A text node directly under the render root is skipped when it is `\s` and format characters alone
 *     (ROOT_BLANK). The top-level children are what the block pairing reads (analyzeRendered), such a node is never the
 *     passage's text to it (the "\n" marked leaves between two top-level blocks, the pair the sanitizer leaves where a
 *     block-level comment stood, a no-break space line an html block of two images holds), and a mark there would be a
 *     top-level child of the root that the next pairing meets (anchor-map-obsidian.test.ts, anchor-map.test.ts and
 *     md-config-paint-collapsed-blank.test.ts hold that no mark is a top-level node).
 *  2. The block-neighbour pre-skip. A text node of collapsible white space (isCollapsibleWs) whose nearest non-blank sibling
 *     on BOTH sides is a block-level box (isBlockBox), or whose parent is a block-level box and has no such sibling on that
 *     side, and that stands under no `pre`, generates no line box at all: CSS 2, section 9.2.2.1, an anonymous inline box that
 *     holds only collapsible white space between block-level boxes is not rendered, and a block's leading and trailing white
 *     space is collapsed away. Under an author's `pre` (`white-space: pre`; the one element the sanitizer keeps that preserves
 *     white space, since an inline style keeps its colours alone, md-sanitize.ts) nothing is collapsible, so the reading does
 *     not apply and the node is painted and measured like every other blank: two spaces or a tab between two block children
 *     render a line of their own (16.86 and 67.44 px at 14px sans-serif in Chromium) and keep their mark, a newline alone is a
 *     forced break of zero width and the trim unwraps it (the Slice 4 review, round 13: round 12's pre-skip read the node as
 *     collapsible whatever its ancestors and skipped the rendered spaces, a ring gap inside the pre;
 *     md-config-paint-trim-fixpoint.test.ts and its browser leg). The "\n" marked leaves between a list's items, a quote's
 *     paragraphs, a table's rows or a fold's blocks is this shape, hundreds of nodes in a long note, and the pre-skip saves the
 *     mark, the measurement and the unwrap each would cost (the review round 12 prototype: outside a pre the trim alone gives
 *     the same answer on every scene, so the reading is an optimisation, kept because it is exact where it applies).
 *  Everything else is painted and measured: a space between two inline children, beside an image, an svg, an anchor, an empty
 *  span, an audio element, a `<br>`, a floated image, a block inside an inline, after a neighbour ending in a space, at a wrap
 *  point, a zero-width or bidi character alone, a newline under a pre. The Slice 4 review's rounds 7 to 11 grew a DOM-side
 *  prediction of which of those the browser collapses (main's block-container list, then neighbour and edge readings over
 *  BLOCK_BOXES and `<br>`, then a reading of each side's rendered content through empty inlines, hidden elements, atomic inlines
 *  and text ending in white space), and each round's fresh reading found the next shape the prediction got wrong (round 12: an
 *  inline svg looked past as rendering nothing, an audio element without controls read as a box, a floated image read as in the
 *  line, a picture without an image, a form feed read as collapsible, the bidi marks and the soft hyphen outside the zero-width
 *  alphabet, a space inside an inline-block, and the line wrap no reading of the DOM can see). The repo's rule is an exact
 *  mechanism over a heuristic that approximates it, and the exact answer here is the browser's layout, read after the paint
 *  (round 12; md-config-paint-trim.test.ts and its browser leg over the scenes those rounds collected,
 *  anchor-map-fixtures/blank-scenes.json).
 *  History. Main skipped any whitespace-only node under one of twelve block containers (UL, OL, LI, BLOCKQUOTE, DIV, TABLE,
 *  THEAD, TBODY, TR, SECTION, ARTICLE, BODY; TD never among them) whatever its neighbours, so the rendered space between two
 *  inline children of a list item or a centred badge row was never painted and the ring broke at it, two ringed boxes with a
 *  bare gap of the space's width (round 10 removed the list); and it painted every other blank as a ringed 4 x 18 px box around
 *  nothing: the "\n" between a folded callout's paragraphs (round 8), beside an author's figure or center and between two
 *  `<br>`s (round 9), beside an empty anchor and after a neighbour ending in a space (round 11), and at every wrap point. */
const skipBlockWs = (t: DText, root: DNode): boolean => {
  const p = t.parentNode;
  if (!p || !isElement(p)) return false;
  if (p === root) return ROOT_BLANK.test(t.data);
  if (!isCollapsibleWs(t.data)) return false;
  // the nearest sibling that is not collapsible white space itself (a run of such nodes between two blocks is one anonymous
  // box, the pair the sanitizer leaves where a block-level comment stood), else the parent's edge
  const edge = (dir: -1 | 1): boolean => {
    let s = sibling(t, dir);
    while (s && isText(s) && isCollapsibleWs(s.data)) s = sibling(s, dir);
    return s ? isBlockBox(s) : isBlockBox(p);
  };
  if (!edge(-1) || !edge(1)) return false;
  // under a pre nothing is collapsible (point 2 above): the node is painted and the trim measures it
  for (let a: DNode | null = p; a && a !== root; a = a.parentNode) if (isElement(a) && a.tagName.toUpperCase() === "PRE") return false;
  return true;
};

/** A formula element (FORMULA_CLASSES) that stands in a line of text: KaTeX's inline layout, its flag on TeX it could not parse,
 *  or the belt's code span, under a paragraph, a heading, a list item, an emphasis. Not a display formula, which is a block of
 *  its own line: KaTeX's `.katex` inside its `.katex-display` wrapper (whose `>` selectors lay the formula out), the belt's
 *  `code` inside a `pre`, or KaTeX's flag standing as a top-level node (under `root`). An inline mark around a block-level box
 *  paints nothing over it, and a mark between `.katex-display` and its `.katex` breaks the layout, so a display formula is
 *  never wrapped: a highlight over one needs a block-level treatment of its own, which nothing paints today. */
function isInlineFormula(n: DNode, root: DNode): boolean {
  if (!isFormula(n)) return false;
  const p = n.parentNode;
  return !!p && p !== root && isElement(p) && !hasClass(p, "katex-display") && p.tagName.toUpperCase() !== "PRE";
}
/** What a Rendered highlight is made of, document order: every text node textNodes() returns and, standing among them, every
 *  inline formula (isInlineFormula), not looked into. Walks `from` (the whole of `root` by default, or one of its top-level
 *  children: wrapBetween reads the blocks a mark touches and no more), judging a formula's standing against `root` itself. */
function highlightUnits(root: DNode, from: DNode = root, out: DNode[] = []): DNode[] {
  const visit = (n: DNode) => {
    if (isText(n)) { out.push(n); return; }
    if (isControl(n)) { if (isInlineFormula(n, root)) out.push(n); return; }
    for (let i = 0; i < n.childNodes.length; i++) visit(n.childNodes[i]);
  };
  visit(from);
  return out;
}
/** Whether `b` is the sibling right after `a`. */
function follows(a: DNode, b: DNode): boolean {
  const p = a.parentNode;
  if (!p || b.parentNode !== p) return false;
  if (a.nextSibling !== undefined) return a.nextSibling === b;   // the DOM's pointer, constant time (sibling's note)
  const kids = p.childNodes;
  for (let i = 0; i < kids.length; i++) if (kids[i] === a) return kids[i + 1] === b;
  return false;
}
/** The node a highlight reads for `n`: the nearest of `n` and its ancestors below `root` that a block renders as (the
 *  pairing's table, idx.nodeBlock), else the child of `root` holding `n` (topChildOf). For a flat note that is the top-level
 *  block; for a paragraph the browser nested inside an html wrapper it is the paragraph's own `<p>`, not the wrapper: a mark
 *  inside a document-wide `<div align="center">` or `<details>` read every highlight unit under the wrapper when the top-level
 *  child was its unit (the Slice 5 review: 0.8 ms per mark on a 1,000-paragraph note inside one div against 0.1 flat in
 *  Chromium, growing with the wrapper, where the plan's stand-in measurement had said 2x), so the scoping the Files pane
 *  freeze fixes brought was lost for such notes. */
function blockTopOf(idx: RenderedIndex, root: DNode, n: DNode): DNode | null {
  for (let c: DNode | null = n; c && c !== root; c = c.parentNode) if (idx.nodeBlock.has(c)) return c;
  return topChildOf(root, n);
}
/** The index of `n` among its parent's children. */
function childIndexOf(n: DNode): number {
  const kids = n.parentNode ? n.parentNode.childNodes : [];
  for (let i = 0; i < kids.length; i++) if (kids[i] === n) return i;
  return -1;
}
/** Whether `a` comes before `b` in document order under `root` (an ancestor before its descendants; two distinct nodes are
 *  never equal). The chains from `root` to each are compared at their fork. */
function precedes(root: DNode, a: DNode, b: DNode): boolean {
  if (a === b) return false;
  const chain = (n: DNode): DNode[] => { const out: DNode[] = []; for (let c: DNode | null = n; c && c !== root; c = c.parentNode) out.push(c); return out.reverse(); };
  const ca = chain(a), cb = chain(b);
  let i = 0;
  while (i < ca.length && i < cb.length && ca[i] === cb[i]) i++;
  if (i === ca.length) return true;    // a is an ancestor of b
  if (i === cb.length) return false;   // b is an ancestor of a
  return childIndexOf(ca[i]) < childIndexOf(cb[i]);
}
/** The node after `n` in document order that is not under `n`, below `root`: its next sibling, or the next sibling of the
 *  nearest ancestor below `root` that has one; null at the end of the root. */
function nextAfter(root: DNode, n: DNode): DNode | null {
  for (let c: DNode | null = n; c && c !== root; c = c.parentNode) { const s = sibling(c, 1); if (s) return s; }
  return null;
}
/** The highlight units (highlightUnits) under the nodes in `tops` (each a node a block renders as, or a child of `root`:
 *  blockTopOf's result, at the top level or nested inside an html wrapper) and under the nodes between them, in document
 *  order from the first to the last: what a mark reads instead of the whole of `root`, so it costs the blocks it touches
 *  (wrapBetween's docstring has the numbers). A node between that holds the last top is entered child by child down to it,
 *  so the rest of a wrapper after the passage is not read. Both highlight paths read through this: wrapBetween for a passage
 *  of text, paintRendered for a range holding formulas alone. None when `tops` is empty. */
function unitsUnder(root: DNode, tops: Set<DNode>): DNode[] {
  const arr = Array.from(tops);
  if (!arr.length) return [];
  if (arr.length === 1) return highlightUnits(root, arr[0]);
  let first = arr[0], last = arr[0];
  for (const t of arr) { if (precedes(root, t, first)) first = t; if (precedes(root, last, t)) last = t; }
  const all: DNode[] = [];
  const collect = (n: DNode): boolean => {   // true once `last` is in
    if (n !== last && isUnder(last, n)) {
      for (let i = 0; i < n.childNodes.length; i++) if (collect(n.childNodes[i])) return true;
      return true;
    }
    highlightUnits(root, n, all);
    return n === last;
  };
  for (let n: DNode | null = first; n && !collect(n); n = nextAfter(root, n)) { /* the next node in document order */ }
  return all;
}
/** Wrap `units` (a contiguous slice of highlightUnits, its edge text nodes already cut to the range) in marks: one mark per run
 *  of adjacent siblings, so the text on both sides of an inline formula and the formula itself are ONE box when they stand
 *  side by side in their paragraph, and a formula inside an emphasis goes under the emphasis's own mark with the text beside it
 *  there. Before this each text node took a mark of its own and a formula none, so a comment across `Inline $x^2$ math and`
 *  showed two ringed boxes with the rendered formula bare between them, and a reader could not tell from the page whether the
 *  formula was part of the passage (the quote holds its TeX; the Slice 4 review). Whitespace-only text between block elements
 *  is skipped as before (skipBlockWs), a run of several such nodes with it. The panel's unpaint moves every child of a mark
 *  back in its place and normalizes the parent (file-comments.ts), so a formula under a mark returns to where it stood. */
function wrapRuns(root: DNode, units: DNode[], className: string, data?: Record<string, string>): DElement[] {
  const marks: DElement[] = [];
  let run: DNode[] = [];
  // never an empty mark: a run of text alone whose every node is empty (an edge cut that left nothing) or whitespace-only
  // between block elements is skipped, however many nodes the run has. The sanitizer leaves TWO adjacent whitespace nodes
  // under the root where it removed a block-level comment or a <style> between two blocks, and a rule that skipped the one
  // such node alone wrapped the pair as a mark of its own: a ringed box on a line between the blocks, everything below moved
  // down by its height, back on every fresh Rendered paint (the Slice 4 review, round 7; main's wrapSlices skipped each
  // such node on its own).
  const skip = (r: DNode[]): boolean => r.every((u) => isText(u) && (!u.data.length || skipBlockWs(u, root)));
  const flush = () => {
    if (run.length && !skip(run)) marks.push(wrapRun(run, className, data));
    run = [];
  };
  for (const u of units) {
    if (run.length && !follows(run[run.length - 1], u)) flush();
    run.push(u);
  }
  flush();
  return marks;
}
/** Wrap from (startNode, startOff) to (endNode, endOff), both text positions under `root`, and with them the inline formulas
 *  that stand between the two positions and the ones in `formulas` (the formulas whose TeX the range holds, paintRendered's
 *  coveredFormulas): a formula before the start or after the end of the text extends the highlight to itself, and the text
 *  between it and the passage (whitespace, since the passage's first and last characters are its first and last non-blank
 *  ones in the range) goes under the highlight with it. The units between the two positions are read from the blocks' nodes
 *  the positions and the formulas sit under (blockTopOf: the top-level children, or the paragraphs nested inside an html
 *  wrapper), and the nodes between those, not from the whole of `root`: a walk of every text node under the root per mark
 *  made the Comments panel's paint pass cost marks x nodes (0.11-0.22 ms per 1000 nodes per mark in Chromium; 466 marks over
 *  a 24k-node document were 1.1 s of a 1.4 s frame on every width change, and 0.7 s of each added comment on a 79k-node file
 *  with 32 comments, 2026-09-09). A mark now costs the blocks it touches, inside a wrapper as at the top level. */
function wrapBetween(idx: RenderedIndex, root: DNode, s: { t: DText; off: number }, e: { t: DText; off: number },
                     className: string, data?: Record<string, string>, formulas: DNode[] = []): DElement[] {
  const ts = blockTopOf(idx, root, s.t), te = blockTopOf(idx, root, e.t);
  if (!ts || !te) return [];
  // the blocks' nodes the highlight reads: the two the positions sit under, and the ones the covered formulas sit under
  // (a formula before the start or after the end of the text extends the highlight to itself, so its block is read too)
  const tops = new Set<DNode>([ts, te]);
  for (const f of formulas) { const tf = blockTopOf(idx, root, f); if (tf) tops.add(tf); }
  const all = unitsUnder(root, tops);
  let i0 = all.indexOf(s.t), i1 = all.indexOf(e.t);
  if (i0 < 0 || i1 < 0 || i1 < i0) return [];
  let a = s.off, b = e.off;
  for (const f of formulas) {
    const i = all.indexOf(f);
    if (i < 0) continue;
    if (i < i0) { i0 = i; a = 0; }
    if (i > i1) { i1 = i; b = e.t.data.length; }
  }
  const units = all.slice(i0, i1 + 1);
  // cut the passage's edge text nodes to the range, so every unit is wrapped whole
  if (s.t === e.t) {
    if (b <= a) return [];
    let t = s.t;
    if (a > 0) t = t.splitText(a);
    if (b - a < t.data.length) t.splitText(b - a);
    units[units.indexOf(s.t)] = t;
  } else {
    const j = units.indexOf(s.t);
    if (a > 0) units[j] = s.t.splitText(a);
    if (b < e.t.data.length) e.t.splitText(b);
  }
  return wrapRuns(root, units, className, data);
}
/** The formulas of `blk` whose TeX lies inside `range`, as elements: the k-th formula hole of the block stands for the k-th
 *  formula element under its nodes (formulaExtra's pairing, the walk's source order being the renderer's document order);
 *  none when the counts disagree (a placeholder an author typed by hand renders a formula the walk never saw). */
function coveredFormulas(idx: RenderedIndex, blk: Block, range: SourceRange, out: DNode[]): void {
  const holes = blk.holes.filter((h) => h.reason === FORMULA_HOLE);
  if (!holes.length) return;
  const els: DNode[] = [];
  for (const n of blk.dom) formulaElements(n, els);
  if (els.length !== holes.length) return;
  holes.forEach((h, k) => { if (nOf(idx, h.startN) >= range.start && nOf(idx, h.endN) <= range.end) out.push(els[k]); });
}

/** A string and, for each of its characters, the source index it was derived from: `text[i]` is what the rendering shows for
 *  `origin[map[i]]`, and `map` never decreases. A character the rendering shows as written maps to itself; one it shows for
 *  several source characters (an entity's decoded character, a footnote reference's number, a tab's four spaces) maps to the
 *  first of them; a character the rendering shows and the source never holds at all (a footnote's ordinal past its label)
 *  maps to the position after the last taken. */
export type Mapped = { text: string; map: number[] };

// ── the rendered text of the source, for the fallback matcher ──────────────────────────────────────
//
// paintRendered's fallback matches a quote against the rendered text: a whitespace-tolerant search of what the rendering SHOWS
// for the quote's source. Until the Slice 5 review's round 3 that reading was a hand-written strip, regexes for each inline
// construct run line by line over the source; the review found it wrong in a dozen shapes marked reads differently (a span
// holding a lone delimiter of its own kind, `_snake_case_` and `**5 * 3 = 15**`; an intraword underscore; a construct across
// a soft line break; a bare URL holding `__init__`; a lead rule applied mid-line to `2024. It was`; an inline tag rule taking
// `Map<K, V>` as a tag; a footnote or reference link the document never defines; a backslash before a tag in raw html; the
// ASCII-only `\w` beside `é`; the sanitizer's dropped `<script>` text) and the coordinator ruled the strip retired: the needle
// is the markdown pipeline's own answer. So the source is read through marked's TOKENS, the ones the one configuration
// (md-config.ts) lexes for the whole document (the document's link definitions and footnote book with them, so a reference
// link, a reference image or a footnote reference reads as defined or as literal text exactly as the rendering does), and each
// token's shown text is written out with a source position per character (renderedBlocks: the walk below mirrors the exact
// walk's placement, walkBlocks and walkInline, and never refuses). What the DOM then does to marked's HTML is applied as text
// rules where the DOM itself is not to hand (the node tests run this on a stand-in; the browser legs check the real one): the
// parser decodes entities, and the sanitizer removes a few elements WITH their text (DROPPED_CONTENT, DOMPurify's
// FORBID_CONTENTS less the elements the profile keeps; md-sanitize.ts) where it unwraps every other forbidden element and
// keeps its text. A raw html block's text is the text between its tags as written (marked passes an html block through; no
// escape, no emphasis, the browser's entity decoding alone); a code block's lines are the code as written (the fence lines
// render nothing); a table is read cell by cell as marked's splitCells cuts a row, a blank at each delimiter (the hay puts one
// between two adjacent table parts, hayRuns), the delimiter row kept as its dashes, which no rendered text holds, so a quote
// spanning it paints nothing and the card keeps Reveal (Slice 5, item 8, recorded); an inline formula and a picture show no
// text (a control the hay skips, isControl); a hard break shows nothing (`<br>`); a footnote reference shows its ordinal;
// a wikilink its file document text. The quote is then the rendered SCOPE's characters whose origin lies in the range, not a
// rendering of the raw slice on its own: a quote cut inside an emphasis pair, begun mid-line after a lead-like `2024. `, or
// spanning a construct that wraps across a soft break reads as the rendering shows those characters, since the pipeline read
// the whole block (the review's round 3: a slice rendered alone kept the unpaired `**`, lost the `2024. ` to a lead rule, and
// kept the markup of a pair whose opener and closer sat on different lines). Needle and scope are one text, so the ordinal
// count guard stays exact.
//
// Kept for the record, the constructs whose rendering the walk reads by rule rather than from the DOM, each with its reason:
// the sanitizer's drops (no DOM here); a wikilink's shown text is the FILE document's (the surface comments are made on;
// the chat's unresolved span shows the source); an entity the browser knows and NAMED_ENTITIES does not keeps its source form
// (the table holds the common ones); a `<pre>` inside an html block keeps the newline after its start tag, which the parser
// drops; a `<template>`'s content, a fragment the DOM never shows, is dropped like a removed element's.

/** The elements the sanitizer removes WITH their text (md-sanitize.ts's profile, html and svg, less MD_FORBID_TAGS, against
 *  DOMPurify's default FORBID_CONTENTS): a `<style>` is forbidden outright and its text goes; `<script>`, `<iframe>`, `<noscript>`,
 *  `<noembed>`, `<noframes>`, `<xmp>`, `<plaintext>` and MathML are outside the profile and in FORBID_CONTENTS, so they go with
 *  their content where a `<form>` or a `<button>` is unwrapped and keeps it (KEEP_CONTENT); a `<template>` is kept but its content
 *  is a fragment no walk of the DOM reaches. `<title>`, `<textarea>`, `<audio>` and `<video>` keep their text in the DOM (the
 *  profile keeps or unwraps them) and are not here. */
const DROPPED_CONTENT = new Set(["SCRIPT", "STYLE", "IFRAME", "NOSCRIPT", "TEMPLATE", "NOEMBED", "NOFRAMES", "XMP", "PLAINTEXT",
                                 "MATH", "MI", "MN", "MO", "MS", "MTEXT", "ANNOTATION-XML"]);

/** The rendered text as it is written out: each character with its N position (the index the token walk places it at; the
 *  caller maps N to source offsets). Whitespace is kept, unlike the exact walk's Emitter: the fallback's match is tolerant of
 *  the amount of whitespace but not of its absence (`cell one` is not `cellone`). */
class TextEmitter {
  text = "";
  map: number[] = [];
  put(c: string, n: number): void { this.text += c; this.map.push(n); }
  /** `s`, shown for the source `view` covers, aligned to it character by character: each character takes the position of its
   *  next occurrence in the view's text after the last one taken, and a character the view lacks (an entity's decoded
   *  character, an ordinal's digit) the position after the last taken. For text the rendering shows as written this is the
   *  identity; for a construct whose shown text marked rewrote (a label with an escaped bracket, `[a\]b]`) it is the closest
   *  reading of where each character came from. */
  align(s: string, view: View): void {
    let c = 0;
    const n = view.str.length;
    for (let i = 0; i < s.length; i++) {
      const p = view.str.indexOf(s[i], c);
      if (p >= 0) { this.put(s[i], view.n(p)); c = p + 1; }
      else this.put(s[i], view.n(Math.min(c, n)));
    }
  }
  /** The view's text as written, every character at its own position. */
  verbatim(view: View): void { for (let i = 0; i < view.str.length; i++) this.put(view.str[i], view.n(i)); }
  /** The view's whitespace alone (the blank lines between two blocks; a reference definition there renders nothing). */
  blanks(view: View): void { for (let i = 0; i < view.str.length; i++) if (isWs(view.str[i])) this.put(view.str[i], view.n(i)); }
  /** A line feed between two blocks, at `n`, unless the text already ends in whitespace: two blocks' texts never run together
   *  in the rendering (a list's items, a quote's paragraphs), whatever the source held between them. */
  sep(n: number): void { if (this.text.length && !isWs(this.text[this.text.length - 1])) this.put("\n", n); }
  append(o: TextEmitter): void { this.text += o.text; for (const n of o.map) this.map.push(n); }
}

/** The tag an inline html token is: its name, upper case, whether it is an end tag, and whether it closes at once (a void element
 *  or `/>`); null for a comment, a declaration or a processing instruction. */
function inlineTag(raw: string): { name: string; end: boolean; leaf: boolean } | null {
  const m = /^<(\/?)([a-zA-Z][a-zA-Z0-9:_-]*)/.exec(raw);
  if (!m) return null;
  const name = m[2].toUpperCase();
  return { name, end: m[1] === "/", leaf: VOID_TAGS.has(name) || /\/>$/.test(raw) };
}

/** The shown text of inline `tokens`, positioned over `view`, which their raws tile (marked's inline lexer consumes its input
 *  raw by raw). Mirrors walkInline with the exact walk's refusals turned into readings: an entity is decoded (the browser's
 *  reading), a label whose tokens do not tile its raw is aligned by its shown text (TextEmitter.align), a construct the walk has
 *  no case for shows its `text`. `drop` is the stack of DROPPED_CONTENT elements the block's inline tags have opened: text inside
 *  one shows nothing, as the sanitizer leaves none of it. */
function lenientInline(tokens: Token[], view: View, em: TextEmitter, drop: string[]): void {
  let p = 0;
  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    const raw = t.raw;
    if (!view.str.startsWith(raw, p)) {
      // the tokens do not tile the view here (marked rewrote the text before lexing it): the rest, aligned by its shown text
      em.align(plainInlineText(tokens.slice(i), drop), view.sub(p, view.str.length));
      return;
    }
    const tv = view.sub(p, p + raw.length);
    p += raw.length;
    if (t.type === "html") {
      const tag = inlineTag(raw);
      if (!tag) continue;   // a comment, a declaration
      if (tag.end) { const at = drop.lastIndexOf(tag.name); if (at >= 0) drop.length = at; }
      else if (DROPPED_CONTENT.has(tag.name) && !tag.leaf) drop.push(tag.name);
      continue;
    }
    if (drop.length) continue;   // inside an element the sanitizer removes with its text
    switch (t.type) {
      case "text": {
        const tt = t as Tokens.Text;
        if (tt.tokens) lenientInline(tt.tokens, tv, em, drop);
        else em.align(decodeBasicEntities(raw), tv);   // the browser decodes an entity; marked's escape leaves one alone
        break;
      }
      case "escape": em.put(raw.slice(1), tv.n(1)); break;
      case "codespan": {
        // marked's codespan: the backtick strings off, a newline a space, and one space off each end when the content has both and
        // is not spaces alone (CommonMark 6.1); the browser then shows it as it stands
        const n = /^`+/.exec(raw)![0].length;
        let a = n, b = raw.length - n;
        if (b < a || raw.slice(b) !== "`".repeat(n)) { em.align(decodeBasicEntities(raw), tv); break; }
        const inner = raw.slice(a, b).replace(/\n/g, " ");
        if (/[^ ]/.test(inner) && /^ /.test(inner) && / $/.test(inner)) { a++; b--; }
        for (let k = a; k < b; k++) em.put(raw[k] === "\n" ? " " : raw[k], tv.n(k));
        break;
      }
      case "em": case "strong": case "del": case "mark": {
        const tt = t as Tokens.Em | Tokens.Strong | Tokens.Del | MarkToken;
        const d = t.type === "em" ? 1 : t.type === "strong" || t.type === "mark" ? 2 : (/^~+/.exec(raw) || [""])[0].length;
        if (d && raw.slice(d, raw.length - d) === tt.text) lenientInline(tt.tokens, tv.sub(d, d + tt.text.length), em, drop);
        else em.align(plainInlineText(tt.tokens, drop), tv);
        break;
      }
      case "footnoteRef": em.align(String((t as FootnoteRefToken).n), tv); break;   // the ordinal the reference shows
      case "wikilink": {
        // the file document's rendering (file-view-links.ts resolves the token; the surface comments are made on): the shown text
        // at textOffset; an image embed is a picture and shows no text
        const tt = t as WikilinkToken;
        if (tt.image) break;
        if (raw.slice(tt.textOffset, tt.textOffset + tt.text.length) === tt.text) for (let k = 0; k < tt.text.length; k++) em.put(tt.text[k], tv.n(tt.textOffset + k));
        else em.align(tt.text, tv);
        break;
      }
      case "link": {
        const tt = t as Tokens.Link;
        if (raw[0] === "[") {
          if (raw.slice(1, 1 + tt.text.length) === tt.text && raw[1 + tt.text.length] === "]") lenientInline(tt.tokens, tv.sub(1, 1 + tt.text.length), em, drop);
          else em.align(plainInlineText(tt.tokens, drop), tv);   // a label with an escaped bracket: marked's text is the label unescaped
        } else {
          // an autolink `<...>` of any scheme, an email's, or a bare URL: the address is the text shown
          const off = raw[0] === "<" ? 1 : 0;
          for (let k = off; k < raw.length - off; k++) em.put(raw[k], tv.n(k));
        }
        break;
      }
      case "image": case "br": case "mathInline": break;   // a picture, a hard break, a formula (a control the hay skips): no text
      default: {
        // a construct the walk has no case for (a later extension's): its inline tokens if it has them, else its text
        const any = t as { tokens?: Token[]; text?: string };
        if (any.tokens) em.align(plainInlineText(any.tokens, drop), tv);
        else if (typeof any.text === "string") em.align(decodeBasicEntities(any.text), tv);
      }
    }
  }
}
/** The shown text of inline `tokens` with no positions: lenientInline over the raws they tile (a token's children tile its raw
 *  where marked did not rewrite the text, so this terminates one level down where the positioned read could not). */
function plainInlineText(tokens: Token[], drop: string[]): string {
  const em = new TextEmitter();
  lenientInline(tokens, View.identity(tokens.map((t) => t.raw).join(""), 0), em, drop.slice());
  return em.text;
}

/** The text an html block shows: the raw's text outside its tags and comments, entities decoded, less the content of the elements
 *  the sanitizer removes with their text (DROPPED_CONTENT; the parser reads a raw-text element's content, RAW_TEXT, as text up to
 *  its end tag, tags and all, so a `<textarea>` or a `<title>` shows what it holds and a `<script>` hides it). Positioned over
 *  `view` (htmlText, the pairing's stripped reading of the same, is not positioned and keeps a raw-text element's text by its
 *  own rule; the two scanners walk the raw the same way). */
function lenientHtml(raw: string, view: View, em: TextEmitter): void {
  const n = raw.length;
  const drop: string[] = [];
  const text = (from: number, to: number): void => {
    if (drop.length) return;
    for (let i = from; i < to; i++) {
      if (raw[i] === "&") {
        const m = /^&(#[xX][0-9a-fA-F]{1,6}|#\d{1,7}|[a-zA-Z]+);/.exec(raw.slice(i, Math.min(to, i + 12)));
        if (m) { const d = decodeBasicEntities(m[0]); if (d !== m[0]) { em.put(d, view.n(i)); i += m[0].length - 1; continue; } }
      }
      em.put(raw[i], view.n(i));
    }
  };
  let i = 0;
  while (i < n) {
    const lt = raw.indexOf("<", i);
    if (lt < 0) { text(i, n); break; }
    text(i, lt);
    i = lt + 1;
    const c = raw[i];
    if (c === "!" || c === "?") {
      if (raw.startsWith("!--", i)) {
        i += 3;
        if (raw[i] === ">") i++;
        else if (raw.startsWith("->", i)) i += 2;
        else { const close = raw.indexOf("-->", i); i = close < 0 ? n : close + 3; }
      } else { const gt = raw.indexOf(">", i); i = gt < 0 ? n : gt + 1; }
      continue;
    }
    const end = c === "/";
    const j = end ? i + 1 : i;
    if (j >= n || !((raw[j] >= "a" && raw[j] <= "z") || (raw[j] >= "A" && raw[j] <= "Z"))) { text(lt, lt + 1); continue; }   // a bare `<`: text
    let k = j;
    while (k < n && isTagNameChar(raw[k])) k++;
    const name = raw.slice(j, k).toUpperCase();
    let selfClosing = false;
    for (i = k; i < n; i++) {
      const ch = raw[i];
      if (ch === '"' || ch === "'") { const q = raw.indexOf(ch, i + 1); if (q < 0) { i = n; break; } i = q; continue; }
      if (ch === ">") { selfClosing = raw[i - 1] === "/" && i - 1 >= k; i++; break; }
    }
    if (end) { const at = drop.lastIndexOf(name); if (at >= 0) drop.length = at; continue; }
    const leaf = selfClosing || VOID_TAGS.has(name);
    if (RAW_TEXT.has(name) && !leaf) {
      // the content is text to the parser, up to the element's own end tag
      const close = raw.toLowerCase().indexOf("</" + name.toLowerCase(), i);
      const to = close < 0 ? n : close;
      if (!DROPPED_CONTENT.has(name)) text(i, to);
      i = to;
      continue;
    }
    if (DROPPED_CONTENT.has(name) && !leaf) drop.push(name);
  }
}

/** A table cell's escaped pipe, `\|`, which marked's splitCells turns into `|` in every cell before the cell's inline markup is
 *  read, so `\|` is the pipe it shows inside a code span as well as outside one. */
function unescapePipes(m: Mapped): Mapped {
  let text = "";
  const map: number[] = [];
  for (let i = 0; i < m.text.length; i++) {
    if (m.text[i] === "\\" && m.text[i + 1] === "|") continue;
    text += m.text[i]; map.push(m.map[i]);
  }
  return { text, map };
}
/** A table row's cells as marked's splitCells cuts them: at each `|` an even count of backslashes precedes (an odd count is the
 *  escape `\|`, the cell's own pipe: `\\|` is an escaped backslash and then a delimiter), each cell a Mapped over the row's own
 *  characters, with the origin of the delimiter before it (-1 for the first); a blank first cell (a leading pipe) and a blank last
 *  cell (a trailing pipe) dropped, as splitCells drops them. */
function splitCellsMapped(m: Mapped): { cell: Mapped; delim: number }[] {
  const out: { cell: Mapped; delim: number }[] = [];
  let from = 0, delim = -1;
  for (let i = 0; i < m.text.length; i++) {
    if (m.text[i] !== "|") continue;
    let slashes = 0;
    for (let b = i - 1; b >= 0 && m.text[b] === "\\"; b--) slashes++;
    if (slashes % 2) continue;
    out.push({ cell: { text: m.text.slice(from, i), map: m.map.slice(from, i) }, delim });
    delim = m.map[i]; from = i + 1;
  }
  out.push({ cell: { text: m.text.slice(from), map: m.map.slice(from) }, delim });
  if (out.length && out[0].cell.text.trim() === "") out.shift();
  if (out.length && out[out.length - 1].cell.text.trim() === "") out.pop();
  return out;
}
/** `m` less its leading and trailing whitespace (splitCells trims every cell). */
function trimMapped(m: Mapped): Mapped {
  let a = 0, b = m.text.length;
  while (a < b && isWs(m.text[a])) a++;
  while (b > a && isWs(m.text[b - 1])) b--;
  return { text: m.text.slice(a, b), map: m.map.slice(a, b) };
}
/** A table row (`line`, one line of the table's raw at `view`) written out cell by cell against marked's cells for it: a blank at
 *  each delimiter's position (the hay puts one between two adjacent table parts), each cell's inline tokens over the cell's own
 *  characters when marked's text for the cell is the row's cell trimmed and its pipes unescaped, else the cell's shown text
 *  aligned; a cell the row holds past marked's count shows nothing, and one marked padded (an empty string) has nothing to show. */
function lenientRow(line: string, view: View, cells: Tokens.TableCell[], em: TextEmitter): void {
  const parts = splitCellsMapped({ text: line, map: Array.from({ length: line.length }, (_, i) => i) });
  for (let c = 0; c < cells.length && c < parts.length; c++) {
    const part = parts[c];
    if (part.delim >= 0) em.put(" ", view.n(part.delim));
    const cell = unescapePipes(trimMapped(part.cell));
    const past = cell.map.length ? cell.map[cell.map.length - 1] + 1 : part.delim >= 0 ? part.delim + 1 : 0;
    const cv = new View(cell.text, null, cell.map.concat([past]).map((i) => view.n(i)));
    if (cell.text === cells[c].text) lenientInline(cells[c].tokens, cv, em, []);
    else em.align(plainInlineText(cells[c].tokens, []), cv);
  }
}

/** The text one block token shows, over `tv` (the view its raw tiles), written into `em`: mirrors walkBlocks case by case, the
 *  exact walk's holes written out as the rendering shows them. Throws Refusal where the walk would (a container whose lines the
 *  suffix view cannot place), and the caller writes the raw as written instead. */
function lenientBlock(t: Token, raw: string, tv: View, em: TextEmitter): void {
  switch (t.type) {
    case "space": em.blanks(tv); break;
    case "hr": case "mathBlock": break;   // a rule shows no text; a display formula's glyphs are a control the hay skips
    case "heading": {
      const tt = t as Tokens.Heading;
      const off = headingTextOffset(raw, tt.text);
      lenientInline(tt.tokens, tv.sub(off, off + tt.text.length), em, []);
      break;
    }
    case "paragraph": {
      const tt = t as Tokens.Paragraph;
      if (raw.startsWith(tt.text) && !/[^\n]/.test(raw.slice(tt.text.length))) lenientInline(tt.tokens, tv.sub(0, tt.text.length), em, []);
      else if (raw !== tt.raw) lenientInline(tt.tokens, suffixLineView(tv, tt.text), em, []);   // the code join (sourceRaw)
      else throw new Refusal("a paragraph the mapping could not place");
      break;
    }
    case "text": {
      // block text (a tight list item's): line i of `text` is a suffix of line i of the raw (walkBlocks)
      const tt = t as Tokens.Text;
      const tvv = suffixLineView(tv, tt.text);
      if (tt.tokens) lenientInline(tt.tokens, tvv, em, []);
      else em.align(decodeBasicEntities(tt.text), tvv);
      break;
    }
    case "blockquote": {
      const tt = t as Tokens.Blockquote;
      lenientBlocks(tt.tokens, blockLexView(suffixLineView(tv, tt.text)), em);
      break;
    }
    case "list": {
      const tt = t as Tokens.List;
      let q = 0;
      for (const item of tt.items) {
        if (!tv.str.startsWith(item.raw, q)) throw new Refusal("a list the mapping could not place");
        const iv = tv.sub(q, q + item.raw.length);
        lenientBlocks(item.tokens, blockLexView(suffixLineView(iv, item.text)), em);
        q += item.raw.length;
        em.sep(tv.n(Math.max(0, q - 1)));
      }
      break;
    }
    case "code": {
      // the code's lines as written, the fence lines dropped (they render nothing): line i of `text` is the tail of the raw line
      // that holds it, read in order past the opening fence (a fenced block's indentation and an indented block's four spaces
      // come off the front of each line); the rows' newlines are the hay's (hayRuns puts one between two rows)
      const tt = t as Tokens.Code;
      const rawLines = raw.split("\n"), textLines = tt.text.split("\n");
      let start = 0, rl = tt.codeBlockStyle === "indented" ? 0 : 1;
      for (let i = 0; i < rl && i < rawLines.length; i++) start += rawLines[i].length + 1;
      for (let i = 0; i < textLines.length; i++) {
        const tl = textLines[i];
        while (rl < rawLines.length && !rawLines[rl].endsWith(tl)) { start += rawLines[rl].length + 1; rl++; }
        if (rl >= rawLines.length) { em.align(textLines.slice(i).join("\n"), tv.sub(Math.min(start, raw.length), raw.length)); break; }
        const off = start + rawLines[rl].length - tl.length;
        if (i > 0) em.put("\n", tv.n(start - 1));
        for (let k = 0; k < tl.length; k++) em.put(tl[k], tv.n(off + k));
        start += rawLines[rl].length + 1; rl++;
      }
      break;
    }
    case "table": {
      // header, delimiter row, body rows: one line each of the raw, in order (marked's table token: `rows` are the body lines
      // after the delimiter row, one row a line); the delimiter row as written, the rest cell by cell (lenientRow)
      const tt = t as Tokens.Table;
      const lines = raw.split("\n");
      let ls = 0;
      for (let i = 0; i < lines.length; i++) {
        const ln = lines[i];
        const lv = tv.sub(ls, ls + ln.length);
        if (i > 0) em.put("\n", tv.n(ls - 1));
        if (i === 0) lenientRow(ln, lv, tt.header, em);
        else if (i === 1) em.verbatim(lv);
        else if (i - 2 < tt.rows.length) lenientRow(ln, lv, tt.rows[i - 2], em);
        else em.blanks(lv);
        ls += ln.length + 1;
      }
      break;
    }
    case "frontMatter": em.align((t as FrontMatterToken).text, tv); break;   // the YAML shown in the fold; its label is a control
    case "footnoteDef": {
      const tt = t as FootnoteDefToken;
      lenientInline(tt.tokens, suffixLineView(tv, tt.text), em, []);
      break;
    }
    case "callout": {
      // the title line shows the callout's title (the type marker is not shown, a missing title is generated), the body its blocks
      const tt = t as CalloutToken;
      const tvv = suffixLineView(tv, tt.text);
      const nl = tt.text.indexOf("\n");
      const bodyStart = nl < 0 ? tt.text.length : nl + 1;
      em.align(calloutTitle(tt), tvv.sub(0, bodyStart));
      em.sep(tvv.n(Math.max(0, bodyStart - 1)));
      lenientBlocks(tt.tokens, blockLexView(tvv.sub(bodyStart, tt.text.length)), em);
      break;
    }
    case "html": lenientHtml(raw, tv, em); break;
    default: {
      const any = t as { text?: string };
      if (typeof any.text === "string") em.align(decodeBasicEntities(any.text), tv);
      else em.verbatim(tv);
    }
  }
}
/** The shown text of block `tokens`, which tile `view.str` from `p` (walkBlocks' placement: a reference definition between two
 *  tokens is stepped over and shows nothing), a line feed between two blocks (TextEmitter.sep); a block the walk cannot place
 *  or read is written as its source holds it, and so is everything after a token whose raw is not found. */
function lenientBlocks(tokens: Token[], view: View, em: TextEmitter, p = 0): void {
  for (const t of tokens) {
    const raw = sourceRaw(t);
    if (!view.str.startsWith(raw, p)) {
      let q = p;
      for (;;) {
        const m = DEF_RE().exec(view.str.slice(q));
        if (!m) break;
        q += m[0].length;
        if (view.str.startsWith(raw, q)) break;
      }
      if (!view.str.startsWith(raw, q)) { em.verbatim(view.sub(p, view.str.length)); return; }
      em.blanks(view.sub(p, q));
      p = q;
    }
    const tv = view.sub(p, p + raw.length);
    const sub = new TextEmitter();
    try { lenientBlock(t, raw, tv, sub); em.append(sub); }
    catch (e) { if (e instanceof Refusal) em.verbatim(tv); else throw e; }
    p += raw.length;
    if (t.type !== "space") em.sep(view.n(Math.max(0, p - 1)));
  }
}

/** The text the rendering shows for blocks `bFrom` to `bTo` of `table`'s placed tokens, each character with its SOURCE offset
 *  (a Mapped over the whole source's coordinates): the blocks through lenientBlocks, the whitespace between them as written (a
 *  reference definition there shows nothing), a block the walk could not place (Placed.broken) as its span holds it. Markdown the
 *  lexer could not parse is the whole text as written. */
function renderedBlocks(table: SourceTable, bFrom: number, bTo: number): Mapped {
  const em = new TextEmitter();
  const { N, placed } = table;
  if (table.lexError !== null || !placed.length) em.verbatim(View.identity(N, 0));
  else {
    const view = View.identity(N, 0);
    for (let b = Math.max(0, bFrom); b <= bTo && b < placed.length; b++) {
      const pl = placed[b];
      if (b > bFrom) em.blanks(view.sub(placed[b - 1].endN, Math.max(placed[b - 1].endN, pl.startN)));
      if (pl.broken !== null) em.verbatim(view.sub(pl.startN, pl.endN));
      else lenientBlocks([pl.t], view, em, pl.startN);
    }
  }
  const idx = { nStart: table.nStart };
  return { text: em.text, map: em.map.map((n) => nOf(idx, n)) };
}
/** The part of `m` whose origins lie in [start, end): a contiguous run, since the map never decreases. */
function mappedSlice(m: Mapped, start: number, end: number): Mapped {
  let a = 0, b = m.map.length;
  while (a < b && m.map[a] < start) a++;
  while (b > a && m.map[b - 1] >= end) b--;
  return { text: m.text.slice(a, b), map: m.map.slice(a, b) };
}

/**
 * The text the Rendered view shows for `s`, read as a markdown document of its own (the header above), every character mapped to
 * its source index in `s`: what paintRendered's fallback matches a quote against, for a source the caller has whole. The block
 * table it builds is its own, not the cached one the viewer's source holds (sourceTable). Tests read the fallback's reading
 * through this and renderedQuote.
 */
export function stripMarkupMapped(s: string): Mapped {
  const t = buildSourceTable(s);
  return renderedBlocks(t, 0, t.placed.length - 1);
}
/** The needle paintRendered's fallback reads for `range` of `source`: the rendered text of the blocks the range overlaps
 *  (renderedBlocks over the viewer's cached table for `source`), cut to the characters whose origin lies in the range. Exported
 *  for the corpus test that holds it equal to marked's rendered text (anchor-map-fallback-markup.test.ts); no production caller
 *  but paintRendered, which reads the same two steps in place. */
export function renderedQuote(source: string, range: SourceRange): string {
  const table = sourceTable(source);
  const idx = { nStart: table.nStart };
  let bFrom = -1, bTo = -1;
  table.placed.forEach((pl, b) => { if (nOf(idx, pl.endN) > range.start && nOf(idx, pl.startN) < range.end) { if (bFrom < 0) bFrom = b; bTo = b; } });
  if (bFrom < 0) { bFrom = 0; bTo = table.placed.length - 1; }
  return mappedSlice(renderedBlocks(table, bFrom, bTo), range.start, range.end).text;
}

// ── the layout-time trim of collapsed blanks ───────────────────────────────────────────────────────
//
// paintRendered paints every text node of its range below the render root (skipBlockWs's two DOM-side skips apart), then
// measures every mark whose text is blank and unwraps the ones the browser lays out at zero width: a collapsible space at a
// line's edge or at the point where the line wraps, one after a neighbour ending in a space or beside an element that renders
// nothing (an empty anchor, an audio element without controls, a floated image), a zero-width or bidi character, a newline the
// browser drops. A rendered blank keeps its mark: a no-break or ideographic space, a space between two inline children on one
// line, the space beside an svg icon, an image or a checkbox. The measurement is the browser's own, a Range over each text node
// under the mark with its client rects' widths summed (a text node split over a wrap counts both fragments), never one Range over
// the mark's contents: two comments over one passage nest their marks (the later paint wraps the text node where it stands, inside
// the earlier comment's mark), and a Range over the outer mark's contents reads the inner MARK element's border box, 4 px of
// padding around a collapsed blank, so a nest of d marks over one wrap point was peeled one level per pass and stood as ringed
// boxes inside one another at the cap (the Slice 4 review, round 13; md-config-paint-trim-fixpoint.test.ts and the panel leg's
// overlapping comments); a mark with no client rect of its own (a display:none ancestor) is kept, since its blank may render
// when the ancestor shows (the panel measures it again on the show: through the seam's reflow report when a frame ran while the
// pane was hidden, Chromium's case, since a display:none frame's requestAnimationFrame runs there, or in the frame file-comments.ts
// trimBlanks armed on finding the body without a box when none did, the hide and the show in one task). Blank, to the trim, is
// text with no letter, digit, punctuation or symbol (`\s`, the format and control characters, a combining mark alone) or the
// hangul fillers alone (letters to Unicode, blank in most fonts); the alphabet picks what is MEASURED and layout decides, so a
// candidate that renders (U+093F alone draws a dotted circle, U+000B a glyph) keeps its mark.
// Three shapes the measurement takes, each measured by the review round 12's prototype:
// - Two-phase. Every candidate is measured, then every collapsed one unwrapped. An unwrap between two measurements invalidates
//   the layout and the next getClientRects lays the block out again: one pass that unwrapped as it measured cost the prototype
//   12.3 s on a paragraph of 5,000 code spans with 373 wrap points, against 0.4 s with one layout per pass. The shipped trim on a
//   paragraph of 5,000 links (4,999 blank marks, 324 wrap points at 800 px) costs about 30 ms on the build box, two passes of one
//   Range.getClientRects per blank mark (9,674 calls), once the layout is counted on both sides (300 ms against 269 with the
//   layout the panel reads next forced after each); measured alone the trimmed paint is 323 ms against 45, the difference being
//   that layout, which the trim forces and the panel would pay on its next frame (md-config-paint-whitespace-browser.test.ts leg
//   4 pins the shape).
// - Batched. paintRendered trims its own marks by default (PaintOptions.trim), one forced layout per call; the Comments panel
//   paints every comment of a pass and passes `trim: false`, then runs trimCollapsedMarks ONCE over every mark of the pass
//   (file-comments.ts paintAll), so a 200-comment pass pays one layout, not 200 (the prototype measured 0.45 ms a call on a
//   12k-element note, 90 ms added to a pass unbatched; on the build box the same pass measured 21 ms batched against 20 untrimmed
//   and 21 unbatched, Chromium laying the mutated paragraph out incrementally, so the batching is the shape that bounds the cost
//   rather than a saving measured here; md-config-paint-trim-browser.test.ts point 4).
// - To a fixpoint. A mark's own 2 px side padding is in the layout, so unwrapping a collapsed mark shortens its line and a
//   later blank on the line may collapse in turn; after a pass that unwrapped something the remaining candidates are measured
//   again, until a pass unwraps nothing. The loop ends by construction (a mark is only ever removed, so the candidates shrink on
//   every pass that continues); TRIM_PASSES_MAX is a safety cap, and a call that reaches it with candidates standing is counted in
//   TRIM_STATS.capped. Round 12 capped the passes at three, and on the paragraph of 5,000 links a fresh paint at 700 px left 366
//   padding-only marks (the passes unwrap 373, 373, 371, 366, 299, 298, 297 and 0: the 4 px freed per line moves nearly every
//   wrap point one word, so the paragraph's wrap-point marks collapse again after each pass), at 400 px 406 and at 300 px 271; a
//   re-trim after a narrowing from 800 to 400 px left 266 (twelve passes to converge) and 800 to 300 px 652 (eleven); 800, 600
//   and 500 px happened to converge in two passes, and 800 px was the one width the tests pinned (the Slice 4 review, round 13;
//   md-config-paint-trim-fixpoint-browser.test.ts holds zero padding-only marks at five widths, fresh and after a narrowing).
//   The reverse, a blank unwrapped as collapsed that renders once a later unwrap moved the wrap point, stays bare while the pane
//   keeps the width: a mark is never re-wrapped, since a blank at a line's last inch can flip with every pass, and the next paint
//   pass at the same width paints the blank again and runs the same cascade over the same layout, so it unwraps the same marks in
//   the same number of passes and leaves the same blanks bare (md-config-paint-trim-fixpoint-browser.test.ts leg 1 holds a second
//   pass at each of its widths equal to the first in passes, blank marks kept and bare blanks); a pass at another width runs that
//   width's cascade, with its own gaps or none. In a fresh paint's trim at one width the shape followed the pass count in every
//   cell the Slice 4 review's round 16 measured (the fixpoint leg's page under feed.css at 19 widths from 220 to 1,000 px and the
//   real pane at 19 viewports, content widths 220 to 660, each across the 120-link item and a paragraph of 600 links; the leg's
//   own five widths across the item and the paragraph of 5,000 links): a trim that converged in two passes (the first unwrapped
//   the wrap points' blanks, the second found nothing more collapsed) left no blank bare, and one that took three or more left
//   some, from a few to about two thousand with the passage's length: the 120-link item 4 to 24 (4 at 220 px under feed.css, 5 at
//   460 in the pane), the 600-link paragraph 27 to 207, the 5,000-link paragraph 2,005 at 700 px in eight passes, 1,884 at 400 in
//   six and 2,095 at 300 in five. A re-trim after a narrowing counts as well the blanks the old width's trim unwrapped that render
//   at the new one (shape (b), the Event-based paragraph below), so its pass count bounds nothing: the leg's item narrowed from 800
//   to 700, 400 and 300 px converges in two passes and leaves 12, 10 and 12 bare (five passes and 44 at 500), and the paragraph
//   648 to 3,267 (three passes at 700 and 500 px, twelve at 400, eleven at 300). In the real pane, one comment across the 120-link
//   item leaves 24 of its 119 spaces bare at a content width of 420 px, 13 at 660 and 5 at 460, none at the thirteen other widths
//   sampled between 220 and 660; across the paragraph of 600 links 167 at 220 px, 116 at 300, 83 at 380, 81 at 420 and 460, 71 at
//   400 and 49 at 560, none at nine others; the panel's own pass at the pane's opening width, 460 px, leaves 5 and 81, and a second
//   pass at every width the same counts (plans/markdown-viewer.md, the Slice 4 build note's item 10 (a), records the shape, its
//   counts under feed.css and under overlapping comments, and the layout-neutral mark as the option that removes it).
// Event-based: the measurement is taken at paint time, and the panel runs the trim again over its standing marks when the seam
// reports a reflow (file-comments.ts, onRendered "reflow": the body's width changed, a text-size step), so a blank that collapses
// at the new width loses its mark in the frame the cards are re-placed; a blank trimmed at the old width that renders at the
// new one stays unpainted until the next paint pass, which paints it and trims at the new width (the fixpoint's shape above; the
// panel repaints on new nodes, never on a reflow, since 2026-09-09). Since the Slice 4 review's round 13 the panel re-trims on
// two layout changes the seam never reports as well, the body's captured `load` (a figure's bytes landing) and the document's
// FontFaceSet `loadingdone` (a face arriving under font-display: swap), each re-wrapping the lines with no width report, folded
// into its layout frame (one trim per frame); and a trim that finds the body without a box (a display:none pane, where every blank
// mark measures nothing and is kept) asks for a frame and measures the marks again there, once per event and never per frame:
// when the hide and the show fall in one task that frame is the first after the show and re-trims it; when a frame runs while
// the pane is hidden (Chromium runs a display:none frame's requestAnimationFrame, so every hide that outlasts a frame) the armed
// frame runs hidden and keeps every mark, and the seam's width observer reports the hide and the show as reflows, the show's
// report re-trimming (file-comments.ts trimBlanks and scheduleRetrim; md-config-paint-retrim-events-browser.test.ts legs 4 and 5).
// Since round 14 the panel's own repaint of the pending target alone (file-comments.ts repaintPresel: a composer opened, closed
// or moved), whose 2 px side padding moves the wrap points of the lines it shares with a highlight, trims at once in the same
// call; since round 15 that repaint is a paint pass over the line boxes the target enters and leaves, since round 16 closed under
// the highlights standing in them (every box a repainted highlight's own marks stand in is read too, until no highlight is new; the
// highlights are painted again in cards() order, the pass's, the change marks whole-document through paintChanges when one stands in
// any of the boxes, the target inside them, then the one trim; lineBoxOf climbs past inline-level boxes, the embed chip's
// inline-block among them, and table parts to the block whose width does not follow its content), since a trim alone left the
// highlight's blanks trimmed at the old wrap points bare where they rendered at the new ones, while the composer stood and after
// Cancel; a repaint that adds and removes no Rendered mark (a reply, a re-place, a comment on the file, a region, the Raw view)
// trims nothing (md-config-paint-presel-retrim-browser.test.ts, the item of fourteen links at 300 to 600 px, no padding-only mark
// and no bare blank pending or after Cancel; md-config-paint-presel-kinds-browser.test.ts, zero measurements for those kinds;
// md-config-paint-presel-scope-browser.test.ts, two overlapping comments' nesting and click target the pass's, a highlight across
// two paragraphs, a change mark in an untouched paragraph, a target on the embed chip). Its price is a fresh paint of the boxes'
// marks to the fixpoint, one layout a pass, in the real pane at 1000 px: the fourteen-link item 5 to 6.5 ms an open and 2.2 to 2.5
// ms a Cancel, the 120-link item 27 to 39 and 14 to 22 ms, forty comments over sixty paragraphs 3 to 5 and 1.4 to 1.7 ms; one
// comment across the paragraph of 5,000 links 6.0 to 6.2 s an open (three passes, 13,821 Range.getClientRects calls) and 3.2 to 3.3
// s a Cancel (two passes, 9,510), against 2.7 to 2.8 and 1.3 s for round 14's trim of the standing marks and about 1.3 s for main's
// untrimmed paint, recorded and not optimised (the passes are the fixpoint's). The re-trim's price per reflow: realistic shapes
// under 10 ms (200 comments over 300 paragraphs 0.6 to 1.2 ms, a 120-link item 0.6 to 11 ms); one comment across the paragraph of
// 5,000 links 1 to 13 s in the real pane under the convergence loop (round 14's measurements, three runs agreeing on every call
// count: a window-resize step 1.0 to 1.1 s and 1,457 Range.getClientRects calls, a divider release narrowing 1000 to 700 px 2.1 to
// 2.4 s and 8,079, widening back 5.1 to 5.6 s and 11,514, a text-size step 12.4 to 13.3 s and 14,244, ten passes, nine that
// unwrapped and the tenth confirming, each pass after one that unwrapped laying the mutated paragraph out again at 1.0 to 1.3 s a
// layout; round 13 recorded 1.5 to 4.6 s, measured under the three-pass cap the same round replaced, which left 51 padding-only
// marks standing on the text-size step where the loop leaves none), recorded beside the paint's cost and not optimised. The
// divider's drag itself fires one reflow, at release (the shell moves a ghost line and lays the pane out once); a window-edge resize
// reflows every frame and pays the price per frame.
// In node the stand-ins offer no layout, so the trim measures nothing and every blank the DOM-side skips leave is a mark; the
// node tests pin the DOM shape and the two skips, the browser legs the trimmed result (md-config-paint-trim.test.ts and
// md-config-paint-trim-browser.test.ts, over anchor-map-fixtures/blank-scenes.json, the scenes the review rounds 7 to 13 collected).

export type PaintOptions = {
  /** Trim this call's collapsed blank marks (trimCollapsedMarks), the default. The Comments panel passes false and trims once
   *  per paint pass over every mark of the pass: one layout instead of one per call. */
  trim?: boolean;
};
/** The safety cap on a trim's measure-then-unwrap passes. The loop stops when a pass unwraps nothing and ends by construction
 *  before then (each pass that continues removes at least one mark); the cap guards against a cascade that unwraps one mark a pass,
 *  and a call that reaches it with candidates standing is counted in TRIM_STATS.capped. Over round 12's 91 fixture scenes 42 paints
 *  took one pass (nothing collapsed), 34 two (a pass that unwrapped, then the pass that confirmed nothing else had) and one three
 *  (the list item of fourteen links at 220 px); the paragraph of 5,000 links takes up to eight passes fresh and twelve after a
 *  narrowing (the header), the most measured. Exported for the tests. */
export const TRIM_PASSES_MAX = 20;
/** The last trim's pass count and the calls that reached the cap since the module loaded: the record the header names, read by
 *  the tests and by a devtools probe. */
export const TRIM_STATS = { passes: 0, capped: 0 };
/** A mark whose every text node matches this is measured: no letter, digit, punctuation or symbol in it (so `\s`, the Unicode
 *  spaces, the format characters Cf, the controls Cc, a combining mark alone), or the hangul fillers (U+115F, U+1160, U+3164,
 *  U+FFA0: letters to Unicode, blank in most fonts). The alphabet chooses what is measured, never what is unwrapped. */
const TRIM_CANDIDATE = /^(?:[^\p{L}\p{N}\p{P}\p{S}]|[\u115f\u1160\u3164\uffa0])*$/u;
type DMeasured = DElement & { getClientRects?(): ArrayLike<unknown> };
/** Whether `m` is a mark the trim measures: a `mark` element holding text, all of it blank (TRIM_CANDIDATE). A framed picture (an
 *  `img` wearing the highlight class, file-comments.ts frameImage), a deletion point or a mark with a word in it is never touched. */
function isBlankMark(m: DElement): boolean {
  if (m.tagName.toUpperCase() !== "MARK") return false;
  let texts = 0;
  const blank = (n: DNode): boolean => {
    if (isText(n)) { texts++; return TRIM_CANDIDATE.test(n.data); }
    for (let i = 0; i < n.childNodes.length; i++) if (!blank(n.childNodes[i])) return false;
    return true;
  };
  return blank(m) && texts > 0;
}
/** The document's Range for the measurement, null when the document offers none or the Range no getClientRects (the tests'
 *  stand-ins), in which case nothing is measured and every mark stays. */
function measureRange(m: DElement): DRange | null {
  const doc = m.ownerDocument;
  if (!doc || typeof doc.createRange !== "function") return null;
  const r = doc.createRange();
  return typeof r.getClientRects === "function" ? r : null;
}
/** The rendered width of the mark's text: a Range over each text node under it, the client rects' widths summed, a fragment per
 *  line a node runs over. Per text node and never over the mark's contents: a Range that selects an element whole reports the
 *  element's border box (CSSOM getClientRects), so over an outer mark holding an inner one (two comments over one passage) the
 *  inner mark's 4 px of padding around a collapsed blank read as content and the nest was peeled one level per pass (the header). */
function contentWidth(r: DRange, m: DElement): number {
  let w = 0;
  const visit = (n: DNode) => {
    if (isText(n)) {
      r.selectNodeContents(n);
      const rects = r.getClientRects();
      for (let i = 0; i < rects.length; i++) w += rects[i].width;
      return;
    }
    for (let i = 0; i < n.childNodes.length; i++) visit(n.childNodes[i]);
  };
  visit(m);
  return w;
}
/** The mark's own client rects: none under a display:none ancestor (kept, its blank may render when the ancestor shows, and the
 *  panel measures it again on the show, by the seam's reflow report or the frame it armed, file-comments.ts trimBlanks); a
 *  collapsed blank in a rendered line gives the mark its padding's rect. A stand-in without the method counts as rendered. */
const ownRects = (m: DMeasured): number => typeof m.getClientRects === "function" ? m.getClientRects().length : 1;
/** Unwrap every mark of `marks` whose text is blank (isBlankMark) and lays out at zero width: the browser collapsed the blank, so
 *  the mark was the sheet's padding around nothing. The mark's children go back before it and it is removed, with no normalize
 *  (the neighbouring marks keep their text nodes; the panel's unpaint normalizes). Two-phase and to a fixpoint, as the header
 *  says. Returns the marks kept, in the order given. Exported for the Comments panel's batched pass and its reflow re-trim, and
 *  for the tests. */
export function trimCollapsedMarks(marks: Element[]): Element[] {
  let kept = marks as unknown as DElement[];
  let cands = kept.filter(isBlankMark);
  const r = cands.length ? measureRange(cands[0]) : null;
  TRIM_STATS.passes = 0;
  if (!r) return marks;
  let converged = false;
  while (TRIM_STATS.passes < TRIM_PASSES_MAX && cands.length) {
    TRIM_STATS.passes++;
    // phase one: every measurement (one layout for the pass), no mutation among them
    const drop = new Set<DElement>();
    for (const m of cands) if (m.parentNode && contentWidth(r, m) === 0 && ownRects(m) > 0) drop.add(m);
    if (!drop.size) { converged = true; break; }
    // phase two: every unwrap (a nest of marks over one blank is dropped whole: the outer mark's children move up before it,
    // the inner mark among them, and the inner mark's move then finds its new parent; either order leaves the text in place)
    for (const m of drop) {
      const p = m.parentNode as DElement;
      while (m.childNodes.length) p.insertBefore(m.childNodes[0], m);
      p.removeChild(m);
    }
    kept = kept.filter((m) => !drop.has(m));
    cands = cands.filter((m) => !drop.has(m));
  }
  if (!converged && cands.length) TRIM_STATS.capped++;
  return kept as unknown as Element[];
}

export function paintRendered(renderedRoot: Element, source: string, range: SourceRange, className: string,
                              data?: Record<string, string>, opts?: PaintOptions): Element[] | null {
  const root = renderedRoot as unknown as DElement;
  // the marks of one wrap, trimmed of their collapsed blanks unless the caller batches the trim (the header above); none left
  // (a passage of one zero-width character, say) is no highlight, and the next path gets its turn
  const done = (marks: DElement[]): Element[] | null => {
    const out = opts && opts.trim === false ? (marks as unknown as Element[]) : trimCollapsedMarks(marks as unknown as Element[]);
    return out.length ? out : null;
  };
  const idx = renderedIndex(root, source);
  // ── the exact path: emitted characters whose source offset lies in the range, and the inline formulas whose TeX does
  //    (a formula emits no character: its hole names its span, and coveredFormulas pairs the hole with its element)
  let first: { b: number; k: number } | null = null, last: { b: number; k: number } | null = null;
  const formulas: DNode[] = [];
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
    coveredFormulas(idx, blk, range, formulas);
  }
  if (first && last) {
    const s = nthNonWs(idx.blocks[first.b].dom[0], first.k);
    const e = nthNonWs(idx.blocks[last.b].dom[0], last.k);
    if (s && e) {
      const out = done(wrapBetween(idx, root, s, { t: e.t, off: e.off + 1 }, className, data, formulas));
      if (out) return out;
    }
  } else if (formulas.length) {
    // the range holds formulas and no text (a comment made in the Raw view on `$x^2$` alone): the formulas are the highlight,
    // read from the blocks' nodes they sit under (blockTopOf, unitsUnder), as wrapBetween reads its units. A walk of the whole
    // root here cost marks x nodes for such marks after main's M1 had scoped the text path: 40 formula-only marks over a
    // 26k-node document were 142 ms a pass against 6.9 ms for 40 text marks on the same paragraphs (the Slice 4 review, round 7).
    const tops = new Set<DNode>();
    for (const f of formulas) { const tf = blockTopOf(idx, root, f); if (tf) tops.add(tf); }
    const all = unitsUnder(root, tops);
    const at = formulas.map((f) => all.indexOf(f)).filter((i) => i >= 0);
    if (at.length) {
      const out = done(wrapRuns(root, all.slice(Math.min(...at), Math.max(...at) + 1), className, data));
      if (out) return out;
    }
  }
  // ── the fallback: a whitespace-tolerant match of the quote read as the rendering shows it (renderedBlocks: the rendered
  //    text of the blocks the range overlaps, marked's tokens written out with a source position per character, cut to the
  //    characters whose origin lies in the range), inside the nodes those blocks render as (a refused block or a hole,
  //    typically), else, or when that scope's text holds the quote no times or a different number of times than the blocks'
  //    rendering holds it, anywhere in the rendered text
  const table = sourceTable(source);
  let scope: DNode[] = [];
  let bFrom = -1, bTo = -1;   // the blocks the range overlaps, first and last
  for (let b = 0; b < idx.blocks.length; b++) {
    const blk = idx.blocks[b];
    const bs = nOf(idx, blk.startN), be = nOf(idx, blk.endN);
    if (be <= range.start || bs >= range.end) continue;
    // the block's nodes less its wrappers: a wrapper's text holds every block the browser nested in it, and the leftover the
    // block owns beside it (its summary, its lead text, a banner's heading and tagline) is in the list on its own, so the hay
    // read a quote on the leftover twice against the block's rendering once and the count guard refused (the Slice 5 review,
    // round 3, HIGH: a comment on a details' summary, a centred div's lead line or a README tagline painted nothing where main
    // had painted it); the leftovers are the wrapper's own text, so they alone are the scope
    for (const n of blk.dom) if (idx.wrappers.indexOf(n) < 0) scope.push(n);
    if (bFrom < 0) bFrom = b;
    bTo = b;
  }
  let wholeText = false;
  const whole = (): void => { scope = idx.topNodes.slice(); bFrom = 0; bTo = idx.blocks.length - 1; wholeText = true; };
  if (!scope.length) whole();
  for (;;) {
    // the scope's rendering, and the quote as its characters whose origin lies in the range (renderedBlocks, mappedSlice): a quote
    // cut inside an emphasis pair or begun mid-line reads as the rendering shows those characters, the block having been read whole
    const scopeSrc = renderedBlocks(table, bFrom, bTo);
    const quote = mappedSlice(scopeSrc, range.start, range.end).text;
    if (stripWs(quote) === "") return null;
    // the hay is the scope's text with the newline between a wrapped code block's rows put back and a blank between two
    // adjacent table parts (hayRuns, above): a quote across two code lines holds a newline, one across two cells a blank
    // for its pipe, and the text nodes alone hold neither
    const nodes: DText[] = [];
    const gaps: number[] = [];   // where in the hay the put-back blanks sit; they are no text node's characters
    let hay = "";
    for (const n of scope) for (const r of hayRuns(n)) { if (r.node) { nodes.push(r.node); hay += r.text; } else { gaps.push(hay.length); hay += r.text; } }
    const inNodes = (i: number): number => { let g = 0; for (const p of gaps) { if (p < i) g++; else break; } return i - g; };
    const hits = occurrences(hay, quote);
    // Which occurrence: the range's ORDINAL among the scope's own occurrences of the quote, in the scope's rendering, which the
    // quote was cut from. A change's text is short (a word, a number), and a table or a code block repeats such tokens; the
    // first occurrence would mark an unchanged cell and report it painted, the wrong passage under "Scroll to the change".
    // The count is taken over the RENDERED scope, not the raw slice: a comment's quote may carry markup of its own (`` `GET
    // /notes` `` in a table cell, `**cache**`) whose plain text recurs in the block, and the raw slice occurs once where the
    // rendering shows its text twice. The ordinal is exact when the rendering shows the text as many times as the scope's
    // rendering holds it, so the counts must agree. The range's own occurrence is the one whose characters map back inside it.
    const srcHits = occurrences(scopeSrc.text, quote);
    if (!hits.length || srcHits.length !== hits.length) {
      // the scope's nodes hold the quote no times, or a different number of times than the blocks' rendering does: they are not
      // where the quote renders (a block a pairing cascade paired to a wrong node, the parser's minted `<p>` or the previous
      // paragraph, and marked a mismatch), so the whole text is searched, as when the scope is empty (the Slice 5 review, round 2:
      // before this every residual pairing error also unpainted a comment the whole-text search had painted, the card offering
      // Reveal and no Scroll; its round 3: the widening fired on no occurrence alone, and a wrong node whose text held the quote a
      // different number of times still refused). Over the whole text the counts must agree, else nothing is painted and the
      // comment or change keeps its card (and Reveal).
      if (wholeText) return null;
      whole();
      continue;
    }
    const k = srcHits.findIndex((h) => scopeSrc.map[h.start] >= range.start && scopeSrc.map[h.end - 1] < range.end);
    if (k < 0) return null;
    const hit = hits[k];
    return done(wrapSlices(nodes, inNodes(hit.start), inNodes(hit.end), className, data, (t) => skipBlockWs(t, root)));
  }
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
                                     stylesFor: (c: ChangePaint) => Record<string, string>, opts?: PaintOptions): { painted: string[]; unpainted: string[] } {
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
    const marks = paintRendered(renderedRoot, source, { start: c.curFrom, end: c.curTo }, "fc-ins", data, opts);
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
