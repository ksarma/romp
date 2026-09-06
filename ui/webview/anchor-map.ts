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
//     so no text node is ever added under a row and every Raw walk above stays exact.
//
// Everything walks a MINIMAL structural DOM (nodeType, childNodes, parentNode, data, splitText,
// ownerDocument.createElement/createTextNode, getAttribute/setAttribute, insertBefore/appendChild/
// removeChild), so anchor-map.test.ts runs it under node against a small stand-in with no jsdom.
//
// Offsets are UTF-16 code-unit indexes into the source string the viewer fetched (the same units the
// engine, the fingerprint, and the host script use); `end` is exclusive.

import { Lexer, type Token, type Tokens } from "marked";
import { findExact } from "./comments";
// The vendored engine is CommonJS with no declaration file (gaps-3 map, TS7016 under this tsconfig). The
// import is bundled by esbuild as-is; the two functions used here are typed locally below. If a shared
// declaration lands later, this directive becomes a no-op.
// @ts-ignore -- untyped CommonJS module
import engineUntyped from "../../vendor/track-changents/engine.js";

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
    for (let i = 0; i < n.childNodes.length; i++) visit(n.childNodes[i]);
  };
  visit(root);
  return out;
}
const textOf = (root: DNode): string => textNodes(root).map((t) => t.data).join("");
const stripWs = (s: string): string => s.replace(/\s+/g, "");

/** Sum of the lengths of the text nodes under `n` that a `counts` predicate admits (null = all). */
function textLenUnder(n: DNode, inCounted: boolean, counts: ((el: DElement) => boolean) | null): number {
  if (isText(n)) return inCounted || !counts ? n.data.length : 0;
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
type RawIndex = { source: string; shape: Shape; rows: RawRow[]; rowStart: number[]; total: number };

/** What a cached analysis was built over: the same source and the same children of the root. The viewer
 *  swaps a body's children wholesale on re-render, so a cache keyed on the root alone would go stale. */
type Shape = { source: string; count: number; first: DNode | null; last: DNode | null };
const shapeOf = (root: DNode, source: string): Shape => ({
  source, count: root.childNodes.length, first: root.childNodes[0] || null, last: root.childNodes[root.childNodes.length - 1] || null,
});
const sameShape = (a: Shape, b: Shape): boolean => a.source === b.source && a.count === b.count && a.first === b.first && a.last === b.last;

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
  const shape = shapeOf(codeRoot, source);
  const hit = rawCache.get(codeRoot);
  if (hit && sameShape(hit.shape, shape)) return hit;
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
  const idx: RawIndex = { source, shape, rows, rowStart, total };
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

type Hole = { reason: string; startN: number };
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
      case "em": case "strong": case "del": case "link": out += plainInline((t as Tokens.Em).tokens); break;
      case "image": case "br": case "html": break;
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
      case "em": case "strong": case "del": {
        const tt = t as Tokens.Em | Tokens.Strong | Tokens.Del;
        const d = t.type === "em" ? 1 : t.type === "strong" ? 2 : (/^~+/.exec(raw) || [""])[0].length;
        if (!d || raw.slice(d, raw.length - d) !== tt.text) throw new Refusal(`${t.type} marks the mapping could not place`);
        walkInline(tt.tokens, view.sub(p + d, p + d + tt.text.length), em);
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
        em.holes.push({ reason: tt.codeBlockStyle === "indented" ? "an indented code block" : "a code block", startN: view.n(p) });
        em.putHole(tt.text, em.holes.length - 1);
        break;
      }
      case "table": {
        const tt = t as Tokens.Table;
        em.holes.push({ reason: "a table", startN: view.n(p) });
        const h = em.holes.length - 1;
        for (const cell of tt.header) em.putHole(plainInline(cell.tokens), h);
        for (const row of tt.rows) for (const cell of row) em.putHole(plainInline(cell.tokens), h);
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
  chars: string; pos: number[]; holes: Hole[];
  refused: string | null;
  dom: DNode[];
  isHtml: boolean;
  tag: string | null;   // the element the token renders to, for resyncing past an html block
};
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
    default: return null;
  }
}

function analyzeRendered(root: DElement, source: string): RenderedIndex {
  const { N, nStart } = normalizeSource(source);
  const blocks: Block[] = [];
  let tokens: Token[] = [];
  let lexError: string | null = null;
  try { tokens = Lexer.lex(N); } catch (e) { lexError = String((e as Error).message || e); }
  // ── place the top-level tokens over N
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
    const em = new Emitter();
    let refused: string | null = broken;
    if (refused === null) {
      try { walkBlocks([t], View.identity(N, 0), em, pos); }
      catch (e) { if (e instanceof Refusal) refused = e.message; else throw e; }
    }
    blocks.push({ startN: pos, endN: pos + t.raw.length, chars: em.chars, pos: em.pos, holes: em.holes,
                  refused, dom: [], isHtml: t.type === "html", tag: tagOf(t) });
    if (broken === null) pos += t.raw.length;
  }
  if (lexError !== null) blocks.length = 0;
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
    blocks.push({ startN: 0, endN: N.length, chars: "", pos: [], holes: [], refused: `markdown the lexer could not parse (${lexError})`,
                  dom: content.slice(), isHtml: false, tag: null });
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
      if (blk.isHtml) return true;                       // the next html block resyncs on its own
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
      let jj = content.length;
      for (let k = j; k <= content.length; k++) if (runFits(b + 1, k)) { jj = k; break; }
      blk.dom = content.slice(j, jj);
      j = jj;
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
  if (hit && sameShape(hit.shape, shapeOf(root, source))) return hit;
  const idx = analyzeRendered(root, source);
  renderedCache.set(root, idx);
  return idx;
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
  const nodes: DText[] = [];
  for (const n of scope) { if (isText(n)) nodes.push(n); else nodes.push(...textNodes(n)); }
  const hay = nodes.map((t) => t.data).join("");
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
  const marks = wrapSlices(nodes, hit.start, hit.end, className, data, skipBlockWs);
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
// Raw view paints all three; Rendered paints the new text of an ins or sub and leaves a deletion to its
// card (the plan: a deletion cannot be placed in rendered prose; Reveal switches to Raw).
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
 *  whole text. */
export const DEL_LABEL_MAX = 80;
export function deletionLabel(oldText: string): string {
  const t = oldText.replace(/\r\n?/g, "\n");
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

/**
 * A zero-width marker element at source `offset` in the Raw view: inserted between the row's text nodes,
 * splitting one when the offset falls inside it, never adding a text node. The label is carried in
 * `data-fc-text` for the sheet's `::before` to draw. An offset on a line ending sits at the end of its
 * row; the end of the file sits at the end of the last row. Returns null when the rows do not match
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
  const doc = row.el.ownerDocument;
  if (!doc) throw new Error("anchor-map: node has no ownerDocument");
  const m = doc.createElement("span");
  m.setAttribute("class", className);
  for (const k of Object.keys(data)) m.setAttribute("data-" + k, data[k]);
  m.setAttribute("data-fc-text", label);
  applyStyles(m, styles);
  const nodes = textNodes(row.el);
  let cum = 0;
  for (const t of nodes) {
    const len = t.data.length;
    if (col < cum + len) {
      const parent = t.parentNode as DElement;
      if (col === cum) parent.insertBefore(m, t);
      else parent.insertBefore(m, t.splitText(col - cum));
      return m as unknown as Element;
    }
    cum += len;
  }
  if (nodes.length) {
    // at the end of the row's text: right after its last text node
    const t = nodes[nodes.length - 1];
    const parent = t.parentNode as DElement;
    let i = 0;
    while (i < parent.childNodes.length && parent.childNodes[i] !== t) i++;
    parent.insertBefore(m, i + 1 < parent.childNodes.length ? parent.childNodes[i + 1] : null);
    return m as unknown as Element;
  }
  // an empty row: the point goes into the row's text cell (its `.fv-ct`), else the row itself
  let host: DElement = row.el;
  for (let i = 0; i < row.el.childNodes.length; i++) {
    const c = row.el.childNodes[i];
    if (isElement(c) && hasClass(c, "fv-ct")) { host = c; break; }
  }
  host.appendChild(m);
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

/**
 * Paint pending changes over the Rendered view: an `ins` or `sub` through paintRendered over its new
 * text (the source-offset path, the text-match fallback inside a refused block), class `fc-ins`, with the
 * same data attributes and styles as the Raw marks. A `del` is never painted here; its card offers
 * Reveal. Returns which ids got paint and which did not, so the panel can mark the rest card-only; a
 * batch whose offsets do not index `source` (offsetsIndex) paints nothing and reports every id unpainted.
 */
export function paintChangesRendered(renderedRoot: Element, source: string, changes: ChangePaint[],
                                     stylesFor: (c: ChangePaint) => Record<string, string>): { painted: string[]; unpainted: string[] } {
  const painted: string[] = [], unpainted: string[] = [];
  if (!batchIndexes(changes, source)) return { painted, unpainted: changes.map((c) => c.id) };
  for (const c of changes) {
    if (c.kind === "del" || c.curFrom === c.curTo) { unpainted.push(c.id); continue; }
    const marks = paintRendered(renderedRoot, source, { start: c.curFrom, end: c.curTo }, "fc-ins", changeData(c));
    if (!marks || !marks.length) { unpainted.push(c.id); continue; }
    const styles = stylesFor(c);
    for (const m of marks) applyStyles(m as unknown as DElement, styles);
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
