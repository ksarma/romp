// A table cell maps from the Rendered view (plans/markdown-viewer.md, Slice 8, items 1 and 3; decision 7: the anchor map
// learns how marked lays out a table cell, so a selection made in the Rendered view inside one maps back to the note's
// source offsets and the highlight lands on the right occurrence; a selection spanning two cells is refused with the reason
// named). Until this slice a table was ONE hole over its raw: every cell's text went through putHole with a negative position,
// a selection in a cell refused as "touches a table" with the Raw view offered on an indexOf of the selected text, a drag
// across two cells refused with no preselect (the cells' text tab-joined in the selection, pipe-joined in the source), and a
// change inside a cell painted by the fallback's ordinal. Now walkTable (anchor-map.ts) re-cuts each row of the table's raw
// as marked's splitCells does, verifies each cell's text against marked's, and walks the cell's inline tokens over the cell's
// own characters (the backslash of every `\|` skipped), the header's cells then each row's left to right, so the block's
// chars are byte for byte what they were and the `<table>` pairs as before, with every character positioned; a cell the
// reading cannot place is a hole of its own (an entity's cell: the walk's sentence), the cells beside it mapping; and the
// selection map's one-cell rule refuses a range covering two cells of one table with the reason named and the Raw view
// offered on the exact span, first covered character through last, where Save works. Driven over the synthetic fixture
// anchor-map-fixtures/cells.md (the notes-api demo domain) rebuilt as the viewer renders it: marked's output under the one
// configuration (md-config.ts) parsed into the DOM stand-in, which nests the nodes after an unclosed tag as a browser does,
// KaTeX's fill stood in for; the idiom of anchor-map-obsidian.test.ts and anchor-map-wrappers.test.ts. The browser leg,
// anchor-map-cells-browser.test.ts, runs the real viewer and the real panel. Every case that maps or names the one-cell rule
// refuses "touches a table" over the tree before this slice. One case is the Slice 8 review's (round 1): an astral character in
// a cell the per-cell fallback holds, whose hole was counted by code point and shifted every later cell of the table; it fails
// over the build's head (c68f52212 since the branch's rebase onto main, cd3a06501 before it) with the later cells' offsets
// shifted, and refuses whole over the base. A last case times the index, one map and forty marks over a 1,000-row table for the
// build note (the brief's open question 13; diagnostics, not a bound). Synthetic values only: an invented note, no real session
// text.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex, renderedBlockElements, paintRendered, paintChangesRendered, unpaintChanges, type SelLike, type MapResult, type ChangePaint } from "./anchor-map";
import { hideEdges } from "../test-dom-shim";

applyMdConfig();
const FIXDIR = path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map-fixtures");
const FIX = fs.readFileSync(path.join(FIXDIR, "cells.md"), "utf8");

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser (anchor-map-wrappers.test.ts's) ──
// Nodes hide their edges at construction (hideEdges, ui/test-dom-shim.ts), so a failing assertion's dump shows a node's primitives
// and not the tree (the ratchet in ui/test-dom-shim.test.ts).
class FakeNode {
  nodeType = 0;
  parentNode: FakeNode | null = null;
  childNodes: FakeNode[] = [];
  constructor(public ownerDocument: FakeDocument) { hideEdges(this); }
  get textContent(): string { return this.nodeType === 3 ? (this as unknown as FakeText).data : this.childNodes.map((c) => c.textContent).join(""); }
}
class FakeText extends FakeNode {
  nodeType = 3;
  constructor(doc: FakeDocument, public data: string) { super(doc); }
  splitText(offset: number): FakeText {
    const tail = new FakeText(this.ownerDocument, this.data.slice(offset));
    this.data = this.data.slice(0, offset);
    const p = this.parentNode as FakeElement | null;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
class FakeElement extends FakeNode {
  nodeType = 1;
  attrs = new Map<string, string>();
  constructor(doc: FakeDocument, public tagName: string) { super(doc); hideEdges(this); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeChild(n: FakeNode): FakeNode { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; return n; }
  appendChild(n: FakeNode): FakeNode { if (n.parentNode) (n.parentNode as FakeElement).removeChild(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore(n: FakeNode, ref: FakeNode | null): FakeNode {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) (n.parentNode as FakeElement).removeChild(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i, 0, n); n.parentNode = this; return n;
  }
  replaceChild(n: FakeNode, old: FakeNode): FakeNode { this.insertBefore(n, old); this.removeChild(old); return old; }
}
class FakeDocument {
  createElement(tag: string): FakeElement { return new FakeElement(this, tag.toUpperCase()); }
  createTextNode(s: string): FakeText { return new FakeText(this, s); }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
    return e in NAMED ? NAMED[e] : m;
  });
}
/** marked's HTML into the stand-in, as a browser's parser reads a fragment: an unclosed tag stays open and the nodes after it
 *  nest inside it (the `<div align="center">` wrapper the fixture holds); an end tag closes down to its element; a block-level
 *  start tag closes the nearest open `<p>` (anchor-map-wrappers.test.ts's parser, less the rules this fixture never reaches). */
function parseHTML(doc: FakeDocument, html: string): FakeNode[] {
  html = html.replace(/\r\n?/g, "\n");
  const root = doc.createElement("#fragment");
  const stack: FakeElement[] = [root];
  let i = 0;
  const top = () => stack[stack.length - 1];
  while (i < html.length) {
    if (html[i] === "<") {
      if (html.startsWith("<!--", i)) { const e = html.indexOf("-->", i); i = e < 0 ? html.length : e + 3; continue; }
      if (html[i + 1] === "/") {
        const e = html.indexOf(">", i);
        const name = html.slice(i + 2, e).trim().toUpperCase();
        for (let k = stack.length - 1; k > 0; k--) if (stack[k].tagName === name) { stack.length = k; break; }
        i = e + 1; continue;
      }
      const m = /^<([a-zA-Z][\w:-]*)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*)\s*(\/?)>/.exec(html.slice(i));
      if (!m) { top().appendChild(doc.createTextNode("<")); i++; continue; }
      const el = doc.createElement(m[1]);
      const attrRe = /([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
      let a: RegExpExecArray | null;
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], decodeEntities(a[2] ?? a[3] ?? a[4] ?? ""));
      if (/^(?:address|article|aside|blockquote|center|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|h[1-6]|header|hgroup|hr|li|listing|main|menu|nav|ol|p|plaintext|pre|search|section|summary|table|ul|xmp)$/i.test(m[1])) {
        for (let k = stack.length - 1; k > 0; k--) { if (stack[k].tagName === "P") { stack.length = k; break; } if (/^(?:BUTTON|TABLE|TD|TH|CAPTION|TEMPLATE|OBJECT)$/.test(stack[k].tagName)) break; }
      }
      top().appendChild(el);
      i += m[0].length;
      if (!m[3] && !VOID.has(m[1].toLowerCase())) {
        stack.push(el);
        if (m[1].toLowerCase() === "pre" && html[i] === "\n") i++;
      }
      continue;
    }
    let e = html.indexOf("<", i);
    if (e < 0) e = html.length;
    top().appendChild(doc.createTextNode(decodeEntities(html.slice(i, e))));
    i = e;
  }
  return root.childNodes.slice();
}
/** What the fill leaves where a placeholder stood (math.ts renderMathPlaceholders): a `.katex` root whose text is the formula's glyphs. */
function standInFill(root: FakeElement): void {
  for (const c of root.childNodes.slice()) {
    if (c.nodeType !== 1) continue;
    const el = c as FakeElement;
    const cls = el.getAttribute("class") || "";
    if (cls === "md-math-inline" || cls === "md-math-display") {
      const doc = el.ownerDocument;
      const katex = doc.createElement("span"); katex.setAttribute("class", "katex");
      katex.appendChild(doc.createTextNode(el.textContent.replace(/[\\^_{}]/g, "")));
      let repl: FakeElement = katex;
      if (cls === "md-math-display") { repl = doc.createElement("span"); repl.setAttribute("class", "katex-display"); repl.appendChild(katex); }
      root.replaceChild(repl, el);
    } else standInFill(el);
  }
}
/** `.fileview-md > marked output`, filled as the viewer's body is. */
function buildRendered(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);
  standInFill(box);
  return box;
}
const El = (n: FakeNode) => n as unknown as Element;
function allText(root: FakeNode): FakeText[] {
  if (root.nodeType === 3) return [root as FakeText];
  const out: FakeText[] = [];
  for (const c of root.childNodes) out.push(...allText(c));
  return out;
}
type Pt = { node: FakeNode; offset: number };
/** The point at the start (or, with `atEnd`, the end) of the k-th occurrence of `needle` inside ONE text node under root. */
function point(root: FakeNode, needle: string, atEnd = false, k = 0): Pt {
  let seen = 0;
  for (const t of allText(root)) {
    let from = 0;
    for (;;) {
      const i = t.data.indexOf(needle, from);
      if (i < 0) break;
      if (seen++ === k) return { node: t, offset: atEnd ? i + needle.length : i };
      from = i + 1;
    }
  }
  throw new Error("not in the rendered text: " + JSON.stringify(needle));
}
const sel = (a: Pt, f: Pt): SelLike => ({ anchorNode: a.node as unknown as Node, anchorOffset: a.offset, focusNode: f.node as unknown as Node, focusOffset: f.offset, isCollapsed: false });
const ok = (r: MapResult, msg: string) => { assert.equal(r.ok, true, msg + ": " + ((r as { reason?: string }).reason || "")); return r as Extract<MapResult, { ok: true }>; };
const bad = (r: MapResult, msg: string) => { assert.equal(r.ok, false, msg); return r as Extract<MapResult, { ok: false }>; };
/** Select the k-th occurrence of `text` (inside one text node) in the rendered box and map it against `src`. */
const mapText = (box: FakeElement, src: string, text: string, k = 0): MapResult => mapRenderedSelection(sel(point(box, text, false, k), point(box, text, true, k)), El(box), src);
/** A selection from the start of `from` to the end of `to` (their k-th occurrences in the rendered text), mapped against `src`. */
const mapSpan = (box: FakeElement, src: string, from: string, to: string, kf = 0, kt = 0): MapResult => mapRenderedSelection(sel(point(box, from, false, kf), point(box, to, true, kt)), El(box), src);
/** The k-th occurrence of `s` in `src`, which must exist. */
const at = (src: string, s: string, k = 0): number => { let i = -1; for (let n = 0; n <= k; n++) { i = src.indexOf(s, i + 1); assert.ok(i >= 0, "in the source: " + s); } return i; };
const rangeOf = (src: string, s: string, k = 0): { start: number; end: number } => ({ start: at(src, s, k), end: at(src, s, k) + s.length });
const lineOf = (src: string, s: string, k = 0): number => src.slice(0, at(src, s, k)).split("\n").length - 1;
/** The k-th occurrence of `text` maps to its own offsets with the quote the source's text. */
function mapsWhole(box: FakeElement, src: string, text: string, k = 0): void {
  const r = ok(mapText(box, src, text, k), text + (k ? " (occurrence " + k + ")" : ""));
  assert.deepEqual(r.range, rangeOf(src, text, k), text + ": its own offsets");
  assert.equal(r.quote, text);
}
/** The first element of `tag` UNDER `root` whose text holds `text`, in document order. */
const find = (root: FakeNode, tag: string, text: string): FakeElement => {
  const hit = (n: FakeNode): FakeElement | null => {
    if (n !== root && n instanceof FakeElement && n.tagName === tag && n.textContent.includes(text)) return n;
    for (const c of n.childNodes) { const h = hit(c); if (h) return h; }
    return null;
  };
  const h = hit(root); assert.ok(h, tag + " holding " + JSON.stringify(text)); return h;
};
/** The elements of `tag` under root, document order. */
const allOf = (root: FakeNode, tag: string, out: FakeElement[] = []): FakeElement[] => { for (const c of root.childNodes) { if (c instanceof FakeElement) { if (c.tagName === tag) out.push(c); allOf(c, tag, out); } } return out; };
/** The nearest ancestor of `n` with `tag`, and its index among its parent's element children. */
const cellOf = (n: FakeNode, tag: string): { el: FakeElement; index: number } => {
  let p = n.parentNode;
  while (p && !(p instanceof FakeElement && p.tagName === tag)) p = p.parentNode;
  assert.ok(p, "inside a " + tag);
  const kids = (p!.parentNode as FakeElement).childNodes.filter((c) => c instanceof FakeElement);
  return { el: p as FakeElement, index: kids.indexOf(p as FakeElement) };
};
const shape = (n: FakeNode): string[] => n.childNodes.map((c) => c.nodeType === 3 ? "#text(" + (c as FakeText).data + ")" : (c as FakeElement).tagName + "." + ((c as FakeElement).getAttribute("class") || "").split(" ")[0]);
const marksOf = (box: FakeElement, src: string, range: { start: number; end: number }, cls = "fc-hl"): FakeElement[] => (paintRendered(El(box), src, range, cls, { act: "fcopen", id: "k1" }) as unknown as FakeElement[] | null) || [];
const textMarks = (marks: FakeElement[]): FakeElement[] => marks.filter((m) => m.textContent.trim() !== "");
const ONE_CELL = /^This selection spans more than one cell of a table; select within one cell, or comment on it from the Raw view\.$/;
const A_TABLE = /^This selection touches a table; comment on it from the Raw view\.$/;

// ── the pairing: nothing about the block table changes ──

test("the fixture's tables pair as before: every <table> is its own block's one element (a top-level table), or its container's (a list item's, a quote's), or the table spliced out of the div wrapper (Slice 5), and the blocks' count is the source's", () => {
  const box = buildRendered(FIX);
  const tables = allOf(box, "TABLE");
  assert.equal(tables.length, 9, "nine tables in the fixture");
  const spans = sourceBlockSpans(FIX);
  // the node a block renders as: the table itself at the top level (or spliced out of the wrapper), else its container (a
  // nested table's block is the list's or the quote's, whose element holds it)
  const ownerOf = (n: FakeNode): { b: number; node: FakeNode } => { for (let x: FakeNode | null = n; x && x !== box; x = x.parentNode) { const b = renderedBlockIndex(El(box), FIX, x as unknown as Node); if (b >= 0) return { b, node: x }; } throw new Error("no block above the node"); };
  for (const tb of tables) {
    const { b, node } = ownerOf(tb);
    const els = renderedBlockElements(El(box), FIX, b) as unknown as FakeElement[];
    const head = FIX.slice(spans[b].start, spans[b].end).slice(0, 12);
    if (head.startsWith("- ") || head.startsWith("> ")) { assert.ok(node !== tb, "a nested table is no block's own node: " + head); assert.ok(els.length === 1 && (els[0].tagName === "UL" || els[0].tagName === "BLOCKQUOTE"), "a nested table's block is its container's: " + head); }
    else { assert.equal(node, tb, "the table is its block's node: " + head); assert.deepEqual(els.map((e) => e.tagName), ["TABLE"], "block " + b + " (" + JSON.stringify(head) + ") owns its one table"); }
  }
  // the div wrapper's own block owns the div, and the table nested in it is its own block's
  const div = find(box, "DIV", "in a div");
  const wrapped = find(div, "TABLE", "in a div");
  assert.notEqual(renderedBlockIndex(El(box), FIX, wrapped as unknown as Node), renderedBlockIndex(El(box), FIX, div as unknown as Node), "the table inside the wrapper is its own block's, not the wrapper's");
  // the aligned columns render as the sanitizer keeps them
  assert.deepEqual([find(box, "TH", "Method").getAttribute("align"), find(box, "TH", "Path").getAttribute("align"), find(box, "TH", "Budget").getAttribute("align")], ["left", "center", "right"]);
});

// ── item 1: a cell maps ──

test("a header cell and a body cell map to their indexOf offsets with the quote the cell's source text (before: refused, `touches a table`, the Raw view offered on an indexOf of the text); a part of a cell maps to its own characters", () => {
  const box = buildRendered(FIX);
  mapsWhole(box, FIX, "Route");
  mapsWhole(box, FIX, "p95");
  mapsWhole(box, FIX, "GET /notes");
  mapsWhole(box, FIX, "120 ms");
  mapsWhole(box, FIX, "180 ms");
  const part = ok(mapRenderedSelection(sel(point(box, "POST /notes"), { node: point(box, "POST /notes").node, offset: point(box, "POST /notes").offset + 4 }), El(box), FIX), "part of a cell");
  assert.equal(part.quote, "POST");
  assert.deepEqual(part.range, rangeOf(FIX, "POST"));
});

test("the second of two cells with the same text maps to the second (the selection made in the second <td>: positions, not a text search), in an aligned table; and the first to the first", () => {
  const box = buildRendered(FIX);
  mapsWhole(box, FIX, "/notes/{id}", 0);
  mapsWhole(box, FIX, "/notes/{id}", 1);
  mapsWhole(box, FIX, "90 ms", 0);
  mapsWhole(box, FIX, "90 ms", 1);
  assert.equal(cellOf(point(box, "90 ms", false, 1).node, "TR").index, 1, "the second occurrence is in the second body row");
  mapsWhole(box, FIX, "DELETE");
  // the paint lands on the right occurrence by position
  for (const k of [0, 1]) {
    const marks = marksOf(box, FIX, rangeOf(FIX, "90 ms", k));
    assert.equal(textMarks(marks).length, 1, "one mark for occurrence " + k);
    assert.equal(cellOf(textMarks(marks)[0], "TR").index, k, "in body row " + k);
    for (const m of marks) { const p = m.parentNode as FakeElement; while (m.childNodes.length) p.insertBefore(m.childNodes[0], m); p.removeChild(m); }
  }
});

test("a cell holding `\\|` maps with the quote holding the backslash where the selection runs across the escape: inside a code span the escaped pipe is the source's own two characters; a selection of the shown pipe alone maps to the pipe's own character, the backslash before it being markup the walk skips, as an emphasis delimiter is", () => {
  const box = buildRendered(FIX);
  const code = find(box, "CODE", "tag=a|b");
  assert.equal(code.textContent, "tag=a|b", "the cell shows the pipe unescaped");
  const inCode = ok(mapRenderedSelection(sel({ node: code.childNodes[0], offset: 0 }, { node: code.childNodes[0], offset: 7 }), El(box), FIX), "the code span's content");
  assert.equal(inCode.quote, "tag=a\\|b");
  assert.deepEqual(inCode.range, rangeOf(FIX, "tag=a\\|b"));
  const alone = allOf(box, "CODE").find((c) => c.textContent === "|");
  assert.ok(alone, "the lone pipe's code span");
  const r = ok(mapRenderedSelection(sel({ node: alone!.childNodes[0], offset: 0 }, { node: alone!.childNodes[0], offset: 1 }), El(box), FIX), "the lone escaped pipe");
  assert.equal(r.quote, "|", "the pipe's own character (the escape's backslash is not selected text)");
  assert.equal(r.range.start, at(FIX, "`\\|` alone") + 2);
  // the whole cell, from the first code span's first character to `alone`: the source's markup inside the quote
  const whole = ok(mapRenderedSelection(sel({ node: code.childNodes[0], offset: 0 }, point(box, "alone", true)), El(box), FIX), "the whole cell");
  assert.equal(whole.quote, "tag=a\\|b` and `\\|` alone");
});

test("a cell holding a code span, a bold word and a link maps with the source's markup inside the quote, the selection's edges inside the markup mapping to the inner characters", () => {
  const box = buildRendered(FIX);
  const r = ok(mapSpan(box, FIX, "web", "the guide"), "bold through the link's label");
  assert.equal(r.quote, "web** session, see [the guide");
  assert.deepEqual(r.range, { start: at(FIX, "web** session"), end: at(FIX, "the guide") + "the guide".length });
  mapsWhole(box, FIX, "by owner");
  const strong = find(box, "STRONG", "web");
  assert.equal(cellOf(strong, "TD").index, 1);
  const marks = marksOf(box, FIX, rangeOf(FIX, "**web** session"));
  assert.deepEqual(textMarks(marks).map((m) => m.textContent), ["web", " session"], "the paint of the source range: the bold word and the words after it, one mark per run");
});

test("a cell holding inline math or a footnote reference keeps the hole inside the cell: the words map with the formula's TeX inside the quote, a boundary strictly inside the glyphs refuses as a formula with the formula preselected (the Slice 5 review's round 2 finding, routed here), a boundary in the reference's number refuses as the reference, and a Raw-made range over the cell paints the cell's text around the formula in one mark", () => {
  const box = buildRendered(FIX);
  const r = ok(mapSpan(box, FIX, "count", "here"), "the words around the formula");
  assert.equal(r.quote, "count $xy$ here");
  const katex = find(find(box, "TD", "count"), "SPAN", "xy");
  assert.equal(katex.getAttribute("class"), "katex");
  const glyphs = katex.childNodes[0] as FakeText;
  assert.equal(glyphs.data, "xy");
  const inF = bad(mapRenderedSelection(sel({ node: glyphs, offset: 1 }, point(box, "here", true)), El(box), FIX), "strictly inside the formula");
  assert.equal(inF.reason, "This selection touches a formula; comment on it from the Raw view.");
  assert.equal(inF.rawHasQuote, true);
  assert.equal(FIX.slice(inF.rawRange!.start, inF.rawRange!.end), "$xy$", "the Raw view preselects the formula with its delimiters (before: the table was one hole and the offer was the selected text's occurrence)");
  mapsWhole(box, FIX, "the count");
  const sup = find(find(box, "TD", "the count"), "SUP", "1");
  const num = allText(sup)[0];
  const inRef = bad(mapRenderedSelection(sel(point(box, "the count"), { node: num, offset: 1 }), El(box), FIX), "into the footnote's number");
  assert.match(inRef.reason, /a footnote reference/);
  // a Raw comment on the cell: one mark holding the words and the formula between them
  const marks = marksOf(box, FIX, rangeOf(FIX, "count $xy$ here"));
  assert.equal(marks.length, 1, "one mark");
  assert.deepEqual(shape(marks[0]), ["#text(count )", "SPAN.katex", "#text( here)"], "the formula under the mark with the words beside it (before: nothing painted, the hay dropping the formula while the needle kept its TeX)");
  // a formula alone in a cell paints the formula
  const only = "| a | b |\n|---|---|\n| $x$ | c |\n";
  const box2 = buildRendered(only);
  const fm = marksOf(box2, only, rangeOf(only, "$x$"));
  assert.equal(fm.length, 1);
  assert.deepEqual(shape(fm[0]), ["SPAN.katex"]);
});

test("a padded short row and a truncated long row: the cells the rendering shows map (`padded`, `long`, `row`), the padded cell shows nothing, and the tail past the header's width is not rendered, so it cannot be selected and a Raw comment on it paints nothing (open question 14's default)", () => {
  const box = buildRendered(FIX);
  mapsWhole(box, FIX, "padded");
  mapsWhole(box, FIX, "long");
  mapsWhole(box, FIX, "row");
  const rowEl = cellOf(point(box, "padded").node, "TR").el;
  const tds = rowEl.childNodes.filter((c) => c instanceof FakeElement) as FakeElement[];
  assert.deepEqual(tds.map((t) => t.textContent), ["padded", ""], "the padded cell is an empty <td>");
  assert.throws(() => point(box, "extra tail"), /not in the rendered text/, "the truncated tail is not rendered");
  assert.equal(paintRendered(El(box), FIX, rangeOf(FIX, "extra tail"), "fc-hl"), null, "a Raw comment on the tail paints nothing and keeps its card");
  // the cells after the odd rows still map: the reading did not lose its place
  mapsWhole(box, FIX, "A padded and a truncated row.");
});

test("a table inside a list item, one inside a blockquote and one nested in a `<div align=\"center\">` wrapper map through the container's view (the item's indent, the quote's markers, Slice 5's splice)", () => {
  const box = buildRendered(FIX);
  mapsWhole(box, FIX, "pen");
  mapsWhole(box, FIX, "Qty");
  mapsWhole(box, FIX, "after the item's table");
  mapsWhole(box, FIX, "qbody");
  mapsWhole(box, FIX, "qtail");
  mapsWhole(box, FIX, "Quoted");
  mapsWhole(box, FIX, "in a div");
  mapsWhole(box, FIX, "Wrapped");
  mapsWhole(box, FIX, "After the wrapper.");
  // a row of the quoted table: two cells, the one-cell rule, the Raw offer the row's span inside the quote line
  const r = bad(mapSpan(box, FIX, "qbody", "qtail"), "two cells of the quoted table");
  assert.match(r.reason, ONE_CELL);
  assert.equal(FIX.slice(r.rawRange!.start, r.rawRange!.end), "qbody | qtail");
  // the list item's prose into its table's first cell: one cell, so it maps, the table's opening pipe inside the quote
  const into = ok(mapSpan(box, FIX, "holding a table:", "Item"), "the item's prose into the table's first cell");
  assert.equal(into.quote, "holding a table:\n\n  | Item");
});

test("a cell with an HTML entity refuses that cell alone with the entity's sentence and the Raw offer at the cell (the per-cell fallback, open question 9's default; before: the whole table refused), while the cells beside and below it map, a picture's cell among them; a drag from the entity's cell into the next names the entity, the first obstacle", () => {
  const box = buildRendered(FIX);
  const td = find(box, "TD", "Fast & simple");
  assert.equal(td.textContent, "Fast & simple", "the browser shows the entity decoded");
  const r = bad(mapText(box, FIX, "Fast & simple"), "the entity's cell");
  assert.equal(r.reason, "This selection touches prose with an HTML entity; comment on it from the Raw view.");
  assert.equal(r.blockStartOffset, at(FIX, "Fast &amp;"), "the Raw offer at the cell");
  assert.equal(r.blockStartLine, lineOf(FIX, "Fast &amp;"));
  mapsWhole(box, FIX, "maps fine");
  mapsWhole(box, FIX, "Beside");
  mapsWhole(box, FIX, "Entity");
  mapsWhole(box, FIX, "also maps");
  const pic = ok(mapText(box, FIX, "picture"), "the text beside the picture");
  assert.equal(pic.quote, "picture");
  assert.equal(pic.range.start, at(FIX, " picture") + 1);
  assert.equal(find(box, "TD", "picture").childNodes.filter((c) => c instanceof FakeElement && c.tagName === "IMG").length, 1, "the picture stands in the cell");
  assert.equal(bad(mapSpan(box, FIX, "Fast & simple", "maps fine"), "the entity's cell into the next").reason, "This selection touches prose with an HTML entity; comment on it from the Raw view.");
  // a Raw comment on the entity's cell still paints, through the fallback (the cell is a hole; its text is the block's)
  const marks = marksOf(box, FIX, rangeOf(FIX, "Fast &amp; simple"));
  assert.deepEqual(textMarks(marks).map((m) => m.textContent), ["Fast & simple"]);
});

// ── the per-cell fallback beside positioned cells: a hole's characters are counted as every other character is ──

test("an astral character in a cell the per-cell fallback holds (an emoji beside an entity, or a numeric reference that decodes to one) leaves every later cell of the table mapping to its own offsets, painting in its own <td> and taking a deletion point at its own character: a hole's characters are counted per UTF-16 code unit as positioned text is (the Slice 8 review, round 1; before: one position per code point, so every later character read the position of the one after it, `ue2` mapped to `e2 |` plus the line feed and `| u`, the last cell to no end, a Raw comment on `ue2` painted `&` in the emoji's cell and `ue` in its own, and a deletion one character into `ue2` landed before the cell; on the base the table refused whole); the same emoji in a positioned cell and a BMP symbol in a hole cell are the controls", () => {
  const SRC = "Status marks.\n\n| E1 | E2 |\n|----|----|\n| \u{1F600} &amp; | ue2 |\n| ue3 | ue4 |\n\nNumeric.\n\n| N1 | N2 |\n|----|----|\n| &#128512; grin | nb2 |\n| nb3 | nb4 |\n\nControls.\n\n| C1 | C2 |\n|----|----|\n| \u{1F600} smile | pc2 |\n| pc3 | pc4 |\n\n| A1 | A2 |\n|----|----|\n| ✅ &amp; | ub2 |\n| ub3 | ub4 |\n\nAfter.\n";
  const ENTITY = "This selection touches prose with an HTML entity; comment on it from the Raw view.";
  const box = buildRendered(SRC);
  // the hole cells: each refuses alone with the entity's sentence and the Raw offer at the cell, its character shown decoded
  for (const [shown, src] of [["\u{1F600} &", "\u{1F600} &amp;"], ["\u{1F600} grin", "&#128512; grin"], ["✅ &", "✅ &amp;"]] as const) {
    assert.equal(find(box, "TD", shown).textContent, shown, shown + ": the browser shows the entity decoded");
    const r = bad(mapText(box, SRC, shown), shown);
    assert.equal(r.reason, ENTITY, shown);
    assert.equal(r.blockStartOffset, at(SRC, src), shown + ": the Raw offer at the cell");
  }
  // every cell beside and below a hole maps to its own offsets (before: ue2 -> `e2 |` + LF + `| u`, ue3 -> `e3 | u`, ue4 -> no end; nb the same)
  for (const cell of ["ue2", "ue3", "ue4", "nb2", "nb3", "nb4", "ub2", "ub3", "ub4", "pc2", "pc3", "pc4"]) mapsWhole(box, SRC, cell);
  mapsWhole(box, SRC, "\u{1F600} smile");   // the control: the same emoji positioned, its two code units emitted as two
  mapsWhole(box, SRC, "After.");
  // a Raw comment on a later cell paints that cell alone (before: two marks, `&` in the emoji's cell and `ue` in ue2's)
  for (const cell of ["ue2", "ue3", "nb2", "nb3", "pc2", "ub2"]) {
    const fresh = buildRendered(SRC);
    const marks = textMarks(marksOf(fresh, SRC, rangeOf(SRC, cell)));
    assert.deepEqual(marks.map((m) => m.textContent), [cell], cell + ": one mark over the cell's text");
    assert.equal(cellOf(marks[0], "TD").el.textContent, cell, cell + ": in its own cell");
  }
  // a deletion point one character into a later cell sits between its first and second characters (before: before the cell)
  for (const cell of ["ue2", "nb2", "ub2", "pc2"]) {
    const fresh = buildRendered(SRC);
    const r = paintChangesRendered(El(fresh), SRC, [{ id: "d-" + cell, kind: "del", curFrom: at(SRC, cell) + 1, curTo: at(SRC, cell) + 1, oldText: "x", author: "web" }], () => ({}));
    assert.deepEqual(r, { painted: ["d-" + cell], unpainted: [] }, cell);
    const pt = allOf(fresh, "SPAN").find((e) => (e.getAttribute("class") || "") === "fc-del" && e.getAttribute("data-id") === "d-" + cell);
    assert.ok(pt, cell + ": the point painted");
    const td = cellOf(pt!, "TD").el;
    assert.equal(td.textContent, cell, cell + ": in the cell the change is in");
    const i = td.childNodes.indexOf(pt!);
    assert.deepEqual([(td.childNodes[i - 1] as FakeText).data, (td.childNodes[i + 1] as FakeText).data], [cell[0], cell.slice(1)], cell + ": between its first and second characters");
    unpaintChanges(El(fresh));
  }
});

// ── item 3: a selection spanning cells is refused with the reason named, the Raw view offered on the exact span ──

test("two body cells refuse with the one-cell sentence, rawHasQuote true and rawRange the span `GET /notes | 120 ms` (before: `touches a table`, rawHasQuote false, the tab-joined selection found nowhere); the same across two rows; prose before the table into a body cell (the header's cells lie in the span) refuses the same with the span from the header's first cell; the whole table refuses with the span from the first header cell through the last body cell; and each offer's blockStartOffset is the span's start, so the panel's search begins there", () => {
  const box = buildRendered(FIX);
  const cases: Array<[string, string, string, string]> = [
    ["GET /notes", "120 ms", "GET /notes | 120 ms", "GET /notes"],
    ["120 ms", "POST /notes", "120 ms |\n| POST /notes", "120 ms"],
    ["for the review.", "GET /notes", "Route | p95 |\n|-------|-----|\n| GET /notes", "Route"],
    ["Route", "180 ms", "Route | p95 |\n|-------|-----|\n| GET /notes | 120 ms |\n| POST /notes | 180 ms", "Route"],
    ["p95", "GET /notes", "p95 |\n|-------|-----|\n| GET /notes", "p95"],
  ];
  for (const [from, to, span, first] of cases) {
    const r = bad(mapSpan(box, FIX, from, to), from + " to " + to);
    assert.match(r.reason, ONE_CELL, from + " to " + to + ": " + r.reason);
    assert.equal(r.rawHasQuote, true, from + " to " + to + ": the Raw view is offered on the span");
    assert.equal(FIX.slice(r.rawRange!.start, r.rawRange!.end), span, from + " to " + to + ": the exact span");
    assert.equal(r.blockStartOffset, at(FIX, first), from + " to " + to + ": the search begins at the span's start");
    assert.equal(r.blockStartLine, lineOf(FIX, first));
  }
  // the sentence keeps the shape the guide and the composer pin, and names the table
  assert.match(bad(mapSpan(box, FIX, "GET /notes", "120 ms"), "two cells").reason, /a table/);
  assert.match(bad(mapSpan(box, FIX, "GET /notes", "120 ms"), "two cells").reason, /^This selection .*; .*from the Raw view\.$/);
});

test("one cell and the prose after the table maps, the row's closing pipe and line feeds inside the quote as a Raw selection over the same characters mints; a selection ending in the whitespace after a cell is that cell's; a selection whose second cell is reached only through the whitespace between them is still two cells", () => {
  const box = buildRendered(FIX);
  const out = ok(mapSpan(box, FIX, "180 ms", "returns JSON."), "the last cell into the paragraph after");
  assert.equal(out.quote, "180 ms |\n\nEvery route above returns JSON.");
  const td = find(box, "TD", "GET /notes");
  const tr = td.parentNode as FakeElement;
  const ws = tr.childNodes[tr.childNodes.indexOf(td) + 1];
  assert.equal(ws.nodeType, 3, "a whitespace node stands after the cell");
  assert.equal((ws as FakeText).data.trim(), "");
  const endInWs = ok(mapRenderedSelection(sel(point(box, "GET /notes"), { node: ws, offset: 1 }), El(box), FIX), "ending in the whitespace after the cell");
  assert.equal(endInWs.quote, "GET /notes");
  const next = find(box, "TD", "120 ms");
  const intoNext = bad(mapRenderedSelection(sel(point(box, "GET /notes"), { node: next.childNodes[0], offset: 1 }), El(box), FIX), "one character into the next cell");
  assert.match(intoNext.reason, ONE_CELL);
  assert.equal(FIX.slice(intoNext.rawRange!.start, intoNext.rawRange!.end), "GET /notes | 1");
});

test("the one-cell rule counts a cell holding a formula alone, and a formula that begins the next cell's text (the review's round 3): a selection from `a1` to the end of the next cell's `$x$` glyphs, or released on the <td> past them, refuses with the one-cell sentence and the Raw view offered on `a1 | $x$` (before: it mapped, the quote carrying the pipe the person did not select as text, since a formula emits no character, the cell holding one alone has no record and the count saw one cell); the mirror, from the glyphs of a first cell's `$yz$` into `b1`, or from the <td> before them, refuses on `$yz$ | b1`; from `a1` into the `$x$` that begins the next cell's text `$x$ here` refuses on `a1 | $x$`; within one cell the words and the formula still map (`count $xy$`), `a1` alone maps, a boundary at the glyphs' start covers none of the formula, a boundary strictly inside the glyphs names the formula, and a last cell holding a formula alone runs into the prose after the table as the last-cell-into-prose rule maps it", () => {
  const SRC = "Intro paragraph.\n\n| A | B | C |\n|---|---|---|\n| count $xy$ here | a1 | $x$ |\n\nMiddle paragraph.\n\n| D | E |\n|---|---|\n| $yz$ | b1 |\n\n| F | G |\n|---|---|\n| e1 | $w$ |\n\nAfter.\n";
  const box = buildRendered(SRC);
  const tds = allOf(box, "TD");
  assert.deepEqual(tds.map((t) => t.textContent), ["count xy here", "a1", "x", "yz", "b1", "e1", "w"], "the three tables' body cells, the formulas' glyphs stood in for");
  const glyphsOf = (td: FakeElement, tex: string): FakeText => { const k = find(td, "SPAN", tex); assert.equal(k.getAttribute("class"), "katex", tex + ": the formula's root"); return k.childNodes[0] as FakeText; };
  const expectOneCell = (r: MapResult, src: string, span: string, label: string): void => {
    const b = bad(r, label);
    assert.match(b.reason, ONE_CELL, label + ": " + b.reason);
    assert.equal(b.rawHasQuote, true, label + ": the Raw view is offered on the span");
    assert.equal(src.slice(b.rawRange!.start, b.rawRange!.end), span, label + ": the exact span, the formula with its delimiters");
    assert.equal(b.blockStartOffset, b.rawRange!.start, label + ": the search begins at the span's start");
    assert.equal(b.blockStartLine, src.slice(0, b.rawRange!.start).split("\n").length - 1, label);
  };
  const gx = glyphsOf(tds[2], "x");
  assert.deepEqual(shape(tds[2]), ["SPAN.katex"], "the third cell holds the formula alone");
  expectOneCell(mapRenderedSelection(sel(point(box, "a1"), { node: gx, offset: gx.data.length }), El(box), SRC), SRC, "a1 | $x$", "a1 to the end of the next cell's glyphs (before: mapped `a1 | $x$`)");
  expectOneCell(mapRenderedSelection(sel(point(box, "a1"), { node: tds[2], offset: tds[2].childNodes.length }), El(box), SRC), SRC, "a1 | $x$", "a1 to the <td> past its glyphs");
  const gyz = glyphsOf(tds[3], "yz");
  expectOneCell(mapRenderedSelection(sel({ node: gyz, offset: 0 }, point(box, "b1", true)), El(box), SRC), SRC, "$yz$ | b1", "the first cell's glyphs into b1");
  expectOneCell(mapRenderedSelection(sel({ node: tds[3], offset: 0 }, point(box, "b1", true)), El(box), SRC), SRC, "$yz$ | b1", "the <td> before the glyphs into b1");
  // the formula begins the next cell's text: the cell has a record, and the formula stands before its first positioned character
  const SRC2 = "| A | B |\n|---|---|\n| a1 | $x$ here |\n";
  const box2 = buildRendered(SRC2);
  const gx2 = glyphsOf(allOf(box2, "TD")[1], "x");
  expectOneCell(mapRenderedSelection(sel(point(box2, "a1"), { node: gx2, offset: gx2.data.length }), El(box2), SRC2), SRC2, "a1 | $x$", "a1 through the formula that begins the next cell (before: mapped)");
  assert.equal(ok(mapRenderedSelection(sel(point(box2, "here"), point(box2, "here", true)), El(box2), SRC2), "the word after the formula").quote, "here");
  // controls
  const gxy = glyphsOf(tds[0], "xy");
  assert.equal(ok(mapRenderedSelection(sel(point(box, "count"), { node: gxy, offset: gxy.data.length }), El(box), SRC), "within one cell: the word and the formula after it").quote, "count $xy$");
  mapsWhole(box, SRC, "a1");
  assert.equal(ok(mapRenderedSelection(sel(point(box, "a1"), { node: gx, offset: 0 }), El(box), SRC), "at the glyphs' start: none of the formula").quote, "a1");
  const inF = bad(mapRenderedSelection(sel({ node: gyz, offset: 1 }, point(box, "b1", true)), El(box), SRC), "strictly inside the glyphs");
  assert.equal(inF.reason, "This selection touches a formula; comment on it from the Raw view.");
  assert.equal(SRC.slice(inF.rawRange!.start, inF.rawRange!.end), "$yz$");
  const gw = glyphsOf(tds[6], "w");
  assert.equal(ok(mapRenderedSelection(sel({ node: gw, offset: 0 }, point(box, "After.", true)), El(box), SRC), "a last cell's formula into the prose after the table").quote, "$w$ |\n\nAfter.", "the last-cell-into-prose rule: the row's closing pipe and line feeds inside the quote");
});

// ── the paint and the change points inside a table go by position ──

test("a Raw-made comment paints by position: one cell one mark in its <td>, two cells one mark each and none over the pipe (the same marks the fallback painted, now through the exact path), and a deletion point inside a cell places in the cell while one on the delimiter row or on the row's closing pipe stays unpainted", () => {
  const box = buildRendered(FIX);
  let marks = marksOf(box, FIX, rangeOf(FIX, "GET /notes"));
  assert.equal(marks.length, 1);
  assert.deepEqual([marks[0].textContent, cellOf(marks[0], "TD").index, cellOf(marks[0], "TR").index], ["GET /notes", 0, 0]);
  for (const m of marks) { const p = m.parentNode as FakeElement; while (m.childNodes.length) p.insertBefore(m.childNodes[0], m); p.removeChild(m); }
  marks = marksOf(box, FIX, rangeOf(FIX, "GET /notes | 120 ms"));
  assert.deepEqual(textMarks(marks).map((m) => m.textContent), ["GET /notes", "120 ms"]);
  assert.equal(marks.length, 2, "no mark over the whitespace between the cells");
  for (const m of marks) { const p = m.parentNode as FakeElement; while (m.childNodes.length) p.insertBefore(m.childNodes[0], m); p.removeChild(m); }
  const del = (id: string, curFrom: number): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText: "gone", author: "web" });
  const res = paintChangesRendered(El(box), FIX, [
    del("in-cell", at(FIX, "120 ms") + 3),
    del("cell-end", at(FIX, "120 ms") + 6),
    del("rule", at(FIX, "|-------|-----|") + 2),
    del("bar", at(FIX, "| 120 ms |") + "| 120 ms ".length),
  ], () => ({}));
  assert.deepEqual(res, { painted: ["in-cell", "cell-end"], unpainted: ["rule", "bar"] });
  const points = allOf(box, "SPAN").filter((s) => (s.getAttribute("class") || "").split(" ").includes("fc-del"));
  assert.deepEqual(points.map((p) => [p.getAttribute("data-id"), (p.parentNode as FakeElement).tagName, (p.parentNode as FakeElement).textContent]), [["in-cell", "TD", "120 ms"], ["cell-end", "TD", "120 ms"]]);
  unpaintChanges(El(box));
});

// ── the shapes marked accepts ──

test("shapes marked accepts map cell by cell: a table with no leading or trailing pipes, an empty middle cell, a header-only table, a cell of markup alone, a cell ending in an escaped backslash before the delimiter (`\\\\|` splits the row), trailing spaces before a pipe, a CRLF source, and a table interrupting a paragraph", () => {
  const bare = "a | b\n--|--\nc | d\n\nAfter.\n";
  let box = buildRendered(bare);
  for (const t of ["a", "b", "c", "d", "After."]) mapsWhole(box, bare, t);
  const empty = "| a |  | c |\n|---|---|---|\n| 1 | 2 | 3 |\n";
  box = buildRendered(empty);
  for (const t of ["a", "c", "1", "2", "3"]) mapsWhole(box, empty, t);
  const headOnly = "| a | b |\n|---|---|\n\nAfter.\n";
  box = buildRendered(headOnly);
  for (const t of ["a", "b", "After."]) mapsWhole(box, headOnly, t);
  const markup = "| x | y |\n|---|---|\n| **bold** | _em_ |\n";
  box = buildRendered(markup);
  const bold = ok(mapText(box, markup, "bold"), "a cell of markup alone");
  assert.deepEqual([bold.quote, bold.range.start], ["bold", at(markup, "bold")]);
  assert.deepEqual([ok(mapText(box, markup, "em"), "an emphasis cell").quote, ok(mapText(box, markup, "em"), "").range.start], ["em", at(markup, "_em_") + 1]);
  const split = "| a\\\\ | b |\n|---|---|\n| c | d |\n";
  box = buildRendered(split);
  assert.equal(find(box, "TH", "a").textContent, "a\\", "the cell shows one backslash");
  const esc = ok(mapText(box, split, "a\\"), "the escaped backslash's cell");
  assert.equal(esc.quote, "a\\\\", "the quote holds both backslashes (the shown one is the escape's second)");
  mapsWhole(box, split, "b");
  const spaced = "| a   | b |\n|---|---|\n| c   | d |\n";
  box = buildRendered(spaced);
  for (const t of ["a", "b", "c", "d"]) mapsWhole(box, spaced, t);
  const crlf = "| a | b |\r\n|---|---|\r\n| c | d |\r\n";
  box = buildRendered(crlf);
  for (const t of ["a", "c", "d"]) mapsWhole(box, crlf, t);
  const two = bad(mapSpan(box, crlf, "c", "d"), "two cells under CRLF");
  assert.equal(crlf.slice(two.rawRange!.start, two.rawRange!.end), "c | d");
  const interrupt = "Intro\n| a | b |\n|---|---|\n| c | d |\n";
  box = buildRendered(interrupt);
  for (const t of ["Intro", "a", "c"]) mapsWhole(box, interrupt, t);
});

// ── the cost, for the build note (the brief's open question 13; the fence's twin is in anchor-map-code-lines.test.ts) ──

test("a 1,000-row table: the index builds, one selection maps and forty marks paint, one per cell (the numbers are diagnostics for the build note, not a bound; before this slice the cell refused as a table)", (t) => {
  const rows = Array.from({ length: 1000 }, (_, i) => "| route_" + i + " | budget_" + i + " ms |");
  const src = "# Big\n\nIntro paragraph.\n\n| Route | Budget |\n|-------|--------|\n" + rows.join("\n") + "\n\nAfter paragraph.\n";
  const box = buildRendered(src);
  assert.equal(allOf(box, "TR").length, 1001, "the header row and a thousand body rows");
  let t0 = process.hrtime.bigint();
  const r = ok(mapText(box, src, "route_500"), "a cell deep in the table");
  const tMap = Number(process.hrtime.bigint() - t0) / 1e6;
  assert.deepEqual(r.range, rangeOf(src, "route_500"));
  t0 = process.hrtime.bigint();
  const painted: FakeElement[] = [];
  for (let k = 0; k < 40; k++) painted.push(...marksOf(box, src, rangeOf(src, "budget_" + (k * 25) + " ms"), "fc-hl"));
  const tPaint = Number(process.hrtime.bigint() - t0) / 1e6;
  const marks = textMarks(painted);
  assert.equal(marks.length, 40, "forty marks, one per cell");
  assert.equal(new Set(marks.map((m) => cellOf(m, "TD").el)).size, 40, "in forty different cells");
  t.diagnostic("1,000-row table on the stand-in: index build plus one map " + tMap.toFixed(1) + " ms, forty marks " + tPaint.toFixed(1) + " ms");
});
