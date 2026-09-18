// The Slice 8 review, round 4 (plans/markdown-viewer.md, Slice 8, items 1, 3 and 4): the shapes a formula inside a table cell
// makes for a selection across cells and for a change's point, found unpinned or wrong by the round's finders and fixed in
// anchor-map.ts, re-aimed for decision 53 of plans/file-review.md (the owner overturned Slice 8's one-cell ruling, 2026-09-18).
// A formula emits no positioned character (a zero-text hole, walkInline's mathInline case), so a cell holding one alone has an
// empty Cell record (walkRow) and lies in a selection through its source span alone; a point inside a formula that ended a
// cell's text once placed against the block's next positioned character, the next cell's, and renderedSpot reads a cell's
// own characters alone since round 4. Until decision 53 the one-cell rule counted such cells (cellsRule, coveredCells) and
// refused two or more in one span with the Raw view offered on the covered cells; now every such selection ANCHORS as any
// selection over more than one block does, from its first positioned character to its last, widened by a formula it covered
// whole at either end (widened), so the quote holds the formula with its delimiters and the pipes between the cells, the
// characters a Raw selection over the same text mints (anchors, below, holds the two paths equal on every case). A selection
// whose characters are covered formulas alone, two formula-only cells with no positioned text, is the formula's, as a
// paragraph's formula-only selection is (orFormula), with the Raw view offered on the formula the drag began on; a picture
// alone in a cell is no formula, so a drag released on the pad past one anchors the positioned cells alone and one that runs
// through such a cell carries it inside the quote. Driven over the DOM stand-in anchor-map-cells.test.ts drives, marked's
// output under the one configuration parsed as a browser parses a fragment, KaTeX's fill stood in for (the browser leg's
// fourth and fifth tests drag over the real fill). Every anchoring case here refuses with the one-cell sentence over the tree
// before decision 53. Synthetic values only: invented notes, no real session text.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { mapRenderedSelection, mapRawSelection, paintChangesRendered, unpaintChanges, type SelLike, type MapResult, type ChangePaint } from "./anchor-map";
import { hideEdges } from "../test-dom-shim";

applyMdConfig();

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
// ── this file's own helpers ──
/** The glyph text node of the formula `tex` stood in under `cell` (the `.katex` root's one text node). */
const glyphsOf = (cell: FakeElement, tex: string): FakeText => { const k = find(cell, "SPAN", tex); assert.equal(k.getAttribute("class"), "katex", tex + ": the formula's root"); return k.childNodes[0] as FakeText; };
/** The end of `t`'s text (a boundary right after its last character). */
const endOf = (t: FakeText): Pt => ({ node: t, offset: t.data.length });
const startOf = (t: FakeText): Pt => ({ node: t, offset: 0 });
const M = (box: FakeElement, src: string, a: Pt, f: Pt): MapResult => mapRenderedSelection(sel(a, f), El(box), src);
const escapeHtml = (s: string): string => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
/** The Raw view's `code.hljs` over `text`: one `.fv-cl` row per line, its text in a `.fv-ct` (file-view.ts wrapNumberedHtml's shape,
 *  no highlighting), the other path a selection over the same characters takes. */
function buildRaw(text: string): FakeElement {
  const doc = new FakeDocument();
  const code = doc.createElement("code"); code.setAttribute("class", "hljs");
  const rows = text.split(/\r\n|\r|\n/).map((ln) => `<span class="fv-cl"><span class="fv-ct">${escapeHtml(ln)}</span></span>`).join("");
  for (const n of parseHTML(doc, rows)) code.appendChild(n);
  return code;
}
/** A Raw selection over the source offsets [start, end): the rows' text nodes at those columns, mapped. */
function mapRawAt(src: string, start: number, end: number): MapResult {
  const code = buildRaw(src);
  const rows = allOf(code, "SPAN").filter((s) => (s.getAttribute("class") || "") === "fv-cl");
  const lines = src.split(/\r\n|\r|\n/);
  const spot = (o: number, atEnd: boolean): Pt => {
    let p = 0;
    for (let i = 0; i < lines.length; i++) {
      const len = lines[i].length;
      if (o < p + len || (atEnd && o === p + len)) { const t = allText(rows[i])[0]; assert.ok(t, "row " + i + " holds text"); return { node: t, offset: o - p }; }
      p += len + (src.slice(p + len, p + len + 2) === "\r\n" ? 2 : 1);
    }
    throw new Error("offset past the rows: " + o);
  };
  return mapRawSelection(sel(spot(start, false), spot(end, true)), El(code), src);
}
/** `r` anchors to `quote` (decision 53): ok, the quote that string, which occurs once in `src`, the range its offsets, and the Raw path
 *  over the same characters minting the same range and quote. */
function anchors(r: MapResult, src: string, quote: string, label: string): void {
  const a = ok(r, label + ": anchors where the one-cell rule refused");
  const start = src.indexOf(quote);
  assert.ok(start >= 0 && src.indexOf(quote, start + 1) < 0, label + ": the expected quote occurs once in the source: " + JSON.stringify(quote));
  assert.deepEqual([a.quote, a.range], [quote, { start, end: start + quote.length }], label + ": the quote and its range");
  const raw = ok(mapRawAt(src, start, start + quote.length), label + " (the Raw path)");
  assert.deepEqual([raw.quote, raw.range], [a.quote, a.range], label + ": the Raw view mints the same anchor over the same characters");
}
const FORMULA = "This selection touches a formula; comment on it from the Raw view.";
/** The refusal is the formula's, with the Raw view offered on one of `offers` (the formula the drag began on, whichever end that is). */
function expectFormula(r: MapResult, src: string, offers: string[], label: string): void {
  const b = bad(r, label + ": a selection of formulas alone is the formula's");
  assert.equal(b.reason, FORMULA, label + ": " + b.reason);
  assert.equal(b.rawHasQuote, true, label + ": the Raw view is offered on the formula");
  const offered = src.slice(b.rawRange!.start, b.rawRange!.end);
  assert.ok(offers.includes(offered), label + ": the offer is a covered formula with its delimiters: " + JSON.stringify(offered));
}
const del = (id: string, curFrom: number): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText: "gone", author: "web" });
/** Where a painted point stands: the table's index, its row (-1 for the header) and column, and the text before and after it
 *  in its cell (the formula's glyphs squashed to `<tex>`). */
type Where = { table: number; row: number; col: number; before: string; after: string };
function whereIs(box: FakeElement, id: string): Where | null {
  const pt = allOf(box, "SPAN").find((s) => (s.getAttribute("class") || "").split(" ").includes("fc-del") && s.getAttribute("data-id") === id);
  if (!pt) return null;
  let td: FakeNode | null = pt.parentNode;
  while (td && !(td instanceof FakeElement && (td.tagName === "TD" || td.tagName === "TH"))) td = td.parentNode;
  assert.ok(td, id + ": inside a cell");
  const cell = td as FakeElement;
  const tr = cell.parentNode as FakeElement, section = tr.parentNode as FakeElement, table = section.parentNode as FakeElement;
  const rows = allOf(section, "TR").filter((r) => r.parentNode === section);
  const text = (ns: FakeNode[]): string => ns.map((n) => n instanceof FakeElement && (n.getAttribute("class") || "") === "katex" ? "<" + n.textContent + ">" : n.textContent).join("");
  const i = cell.childNodes.indexOf(pt);
  return { table: allOf(box, "TABLE").indexOf(table), row: cell.tagName === "TH" ? -1 : rows.indexOf(tr), col: tr.childNodes.filter((c) => c instanceof FakeElement).indexOf(cell), before: text(cell.childNodes.slice(0, i)), after: text(cell.childNodes.slice(i + 1)) };
}

// ── item 4: a deletion point inside a cell places against the cell's own characters ──

test("a deletion point inside an inline formula that ENDS a cell's text places after the cell's last character, in the cell (the review's round 4; before: in the NEXT cell, before its first character, or in the next row's first cell when the formula ended the row's last cell, a cell the change is not in): inside `head $x$`'s TeX and at its opening dollar, inside `end $w$`'s TeX with `plain` beside it, and inside `tail $q$`'s TeX, the row's last cell, with a row below; a point inside a formula that BEGINS a cell's text places before the cell's first character, one inside a mid-cell formula before the character after it, one inside the table's last cell's formula after that cell's text (unchanged), and a cell holding a formula alone keeps its card", () => {
  const A = "Points intro.\n\n| F1 | F2 | F3 |\n|---|---|---|\n| head $x$ | $y$ tail | a $z$ b |\n| end $w$ | plain | $v$ |\n| r3a | r3b | r3c |\n\nAfter points.\n";
  const box = buildRendered(A);
  assert.deepEqual(allOf(box, "TD").map((t) => t.textContent), ["head x", "y tail", "a z b", "end w", "plain", "v", "r3a", "r3b", "r3c"], "the body cells, the formulas' glyphs stood in for");
  const pts = [
    del("x-tex", at(A, "head $x$") + 6), del("x-dollar", at(A, "head $x$") + 5), del("w-tex", at(A, "end $w$") + 5),
    del("y-tex", at(A, "$y$ tail") + 1), del("z-tex", at(A, "a $z$ b") + 3), del("v-tex", at(A, "| $v$ |") + 3), del("after-head", at(A, "head $x$") + 4),
  ];
  const res = paintChangesRendered(El(box), A, pts, () => ({}));
  assert.deepEqual(res, { painted: ["x-tex", "x-dollar", "w-tex", "y-tex", "z-tex", "after-head"], unpainted: ["v-tex"] }, "the formula-alone cell keeps its card, every other point places");
  assert.deepEqual(whereIs(box, "x-tex"), { table: 0, row: 0, col: 0, before: "head", after: " <x>" }, "inside `head $x$`'s TeX: after `head`, in its own cell (before: before `tail` in the next cell)");
  assert.deepEqual(whereIs(box, "x-dollar"), { table: 0, row: 0, col: 0, before: "head", after: " <x>" }, "at the opening dollar: the same");
  assert.deepEqual(whereIs(box, "after-head"), { table: 0, row: 0, col: 0, before: "head", after: " <x>" }, "right after `head`: the control, the same place");
  assert.deepEqual(whereIs(box, "w-tex"), { table: 0, row: 1, col: 0, before: "end", after: " <w>" }, "inside `end $w$`'s TeX: after `end` (before: before `plain`)");
  assert.deepEqual(whereIs(box, "y-tex"), { table: 0, row: 0, col: 1, before: "<y> ", after: "tail" }, "inside the formula that begins `$y$ tail`: before `tail`, in its own cell");
  assert.deepEqual(whereIs(box, "z-tex"), { table: 0, row: 0, col: 2, before: "a <z> ", after: "b" }, "inside the mid-cell formula: before `b`");
  unpaintChanges(El(box));
  const B = "Row-end formula.\n\n| R1 | R2 |\n|---|---|\n| first | tail $q$ |\n| next1 | next2 |\n\nBetween.\n\n| S1 | S2 |\n|---|---|\n| sa | sb $r$ |\n\nAfter last.\n";
  const bb = buildRendered(B);
  const res2 = paintChangesRendered(El(bb), B, [del("q-tex", at(B, "tail $q$") + 6), del("q-dollar", at(B, "tail $q$") + 5), del("r-tex", at(B, "sb $r$") + 4), del("after-tail", at(B, "tail $q$") + 4)], () => ({}));
  assert.deepEqual(res2, { painted: ["q-tex", "q-dollar", "r-tex", "after-tail"], unpainted: [] });
  assert.deepEqual(whereIs(bb, "q-tex"), { table: 0, row: 0, col: 1, before: "tail", after: " <q>" }, "inside `tail $q$`'s TeX, the row's last cell: after `tail` (before: before `next1`, the NEXT row's first cell)");
  assert.deepEqual(whereIs(bb, "q-dollar"), { table: 0, row: 0, col: 1, before: "tail", after: " <q>" }, "at its opening dollar: the same");
  assert.deepEqual(whereIs(bb, "after-tail"), { table: 0, row: 0, col: 1, before: "tail", after: " <q>" }, "right after `tail`: the control");
  assert.deepEqual(whereIs(bb, "r-tex"), { table: 1, row: 0, col: 1, before: "sb", after: " <r>" }, "inside the table's last cell's formula: after `sb`, as before");
  unpaintChanges(El(bb));
});

// ── item 3, overturned by decision 53: a cell holding a formula alone lies inside the anchor wherever it stands in the span ──

test("a selection across cells anchors with a formula-only cell inside the span wherever it stands (decision 53; the review's round 4 counted such a cell and refused): from the prose before a table through its all-formula header row, `Intro para.` to the end of the `$k$` glyphs or to the <th> past them, anchors `Intro para.\\n\\n| $h$ | $k$`, the formulas with their delimiters and the pipes inside the quote; on into the body through the delimiter row, and the whole table; from a first cell holding a formula alone through the next into the prose after the table anchors `$x$ | $y$ |\\n\\nAfter.`; three formula cells; a header cell into two body formula cells anchors through both; the text twin anchors alike; and, as before, the prose into the first header cell alone, two formulas in ONE cell and a last cell holding a formula alone into the prose after each map", () => {
  const H = "Intro para.\n\n| $h$ | $k$ |\n|---|---|\n| $a$ | $b$ |\n\nAfter.\n";
  const box = buildRendered(H);
  const ths = allOf(box, "TH"), tds = allOf(box, "TD");
  assert.deepEqual([ths.map((t) => t.textContent), tds.map((t) => t.textContent)], [["h", "k"], ["a", "b"]], "every cell a formula alone, the glyphs stood in for");
  const intro = point(box, "Intro");
  anchors(M(box, H, intro, endOf(glyphsOf(ths[1], "k"))), H, "Intro para.\n\n| $h$ | $k$", "Intro to the end of the `$k$` glyphs (before: the one-cell sentence, the Raw view on `$h$ | $k$`)");
  anchors(M(box, H, intro, { node: ths[1], offset: ths[1].childNodes.length }), H, "Intro para.\n\n| $h$ | $k$", "Intro to the <th> past the `$k$` glyphs");
  anchors(M(box, H, intro, endOf(glyphsOf(tds[0], "a"))), H, "Intro para.\n\n| $h$ | $k$ |\n|---|---|\n| $a$", "Intro to the end of the `$a$` glyphs: the delimiter row inside the quote");
  anchors(M(box, H, intro, endOf(glyphsOf(tds[1], "b"))), H, "Intro para.\n\n| $h$ | $k$ |\n|---|---|\n| $a$ | $b$", "Intro to the end of the `$b$` glyphs: the whole table");
  anchors(M(box, H, intro, endOf(glyphsOf(ths[0], "h"))), H, "Intro para.\n\n| $h$", "Intro to the end of the `$h$` glyphs: one cell and the prose before it, as before");
  const X = "Intro paragraph.\n\n| A | B |\n|---|---|\n| $x$ | $y$ |\n\nAfter.\n";
  const xb = buildRendered(X);
  const xt = allOf(xb, "TD");
  anchors(M(xb, X, startOf(glyphsOf(xt[0], "x")), point(xb, "After.", true)), X, "$x$ | $y$ |\n\nAfter.", "the `$x$` glyphs into the prose after the table (before: refused on `$x$ | $y$`)");
  anchors(M(xb, X, { node: xt[0], offset: 0 }, point(xb, "After.", true)), X, "$x$ | $y$ |\n\nAfter.", "the <td> before the `$x$` glyphs into the prose after");
  anchors(M(xb, X, point(xb, "B"), endOf(glyphsOf(xt[1], "y"))), X, "B |\n|---|---|\n| $x$ | $y$", "the header cell `B` through both body formula cells");
  anchors(M(xb, X, startOf(glyphsOf(xt[1], "y")), point(xb, "After.", true)), X, "$y$ |\n\nAfter.", "a last cell holding a formula alone into the prose after, as before");
  const T = "Intro paragraph.\n\n| $x$ | $y$ | $z$ |\n|---|---|---|\n| a | b | c |\n";
  const tb = buildRendered(T);
  anchors(M(tb, T, point(tb, "Intro"), endOf(glyphsOf(allOf(tb, "TH")[2], "z"))), T, "Intro paragraph.\n\n| $x$ | $y$ | $z$", "three formula-only header cells");
  const K = "Intro para.\n\n| h | k |\n|---|---|\n| a | b |\n";
  const kb = buildRendered(K);
  anchors(M(kb, K, point(kb, "Intro"), point(kb, "k", true)), K, "Intro para.\n\n| h | k", "the text twin: the pass's shape, anchoring alike");
  const ONE = "Intro paragraph.\n\n| $x$ $y$ | c |\n|---|---|\n| a | b |\n";
  const ob = buildRendered(ONE);
  anchors(M(ob, ONE, point(ob, "Intro"), endOf(glyphsOf(allOf(ob, "TH")[0], "y"))), ONE, "Intro paragraph.\n\n| $x$ $y$", "two formulas in ONE cell, as before");
});

test("a formula the selection covered whole at its start or its end inside the table travels inside the anchor with its delimiters (the existing widening; the review's round 4 had the one-cell offer widen the same way): a header cell through the header into a body cell holding a formula alone anchors `A | B |\\n|---|---|\\n| $x$`, and through both body cells `... | $x$ | $y$`; a drag begun in a formula-only header cell into a body cell anchors `$h$ | B |\\n|---|---|\\n| a1`, from the <th> before the glyphs too; two positioned cells and a trailing formula `a1 | b1 $x$`; a drag begun on a formula-alone cell's glyphs down through three rows anchors from the formula, into the prose after too, and one ended on the `$y$` glyphs of a later row anchors through the formula; the one-positioned-cell shape `$x$ |\\n| $y$ tail`; and a formula in ANOTHER table, the drag having crossed the prose between, begins the anchor, the prose and the second table's rows inside it", () => {
  const S1 = "| A | B |\n|---|---|\n| $x$ | $y$ |\n";
  const b1 = buildRendered(S1);
  const t1 = allOf(b1, "TD");
  anchors(M(b1, S1, point(b1, "A"), endOf(glyphsOf(t1[0], "x"))), S1, "A | B |\n|---|---|\n| $x$", "A to the end of the `$x$` glyphs");
  anchors(M(b1, S1, point(b1, "A"), { node: t1[0], offset: t1[0].childNodes.length }), S1, "A | B |\n|---|---|\n| $x$", "A to the <td> past the `$x$` glyphs");
  anchors(M(b1, S1, point(b1, "A"), endOf(glyphsOf(t1[1], "y"))), S1, "A | B |\n|---|---|\n| $x$ | $y$", "A to the end of the `$y$` glyphs");
  const S3 = "| $h$ | B |\n|---|---|\n| a1 | b1 |\n";
  const b3 = buildRendered(S3);
  const h3 = allOf(b3, "TH");
  anchors(M(b3, S3, startOf(glyphsOf(h3[0], "h")), point(b3, "a1", true)), S3, "$h$ | B |\n|---|---|\n| a1", "the `$h$` glyphs into a1");
  anchors(M(b3, S3, { node: h3[0], offset: 0 }, point(b3, "a1", true)), S3, "$h$ | B |\n|---|---|\n| a1", "the <th> before the glyphs into a1");
  const SM = "| A | B |\n|---|---|\n| a1 | b1 $x$ |\n";
  const bm = buildRendered(SM);
  anchors(M(bm, SM, point(bm, "a1"), endOf(glyphsOf(allOf(bm, "TD")[1], "x"))), SM, "a1 | b1 $x$", "a1 to the end of `b1 $x$`'s glyphs");
  const MULTI = "| Head1 | Head2 |\n|---|---|\n| a1 | $x$ |\n| $y$ tail | b2 |\n| c1 | c2 |\n\nAfter the table.\n";
  const bmu = buildRendered(MULTI);
  const tmu = allOf(bmu, "TD");
  assert.deepEqual(tmu.map((t) => t.textContent), ["a1", "x", "y tail", "b2", "c1", "c2"]);
  const gx = glyphsOf(tmu[1], "x"), gy = glyphsOf(tmu[2], "y");
  anchors(M(bmu, MULTI, startOf(gx), point(bmu, "c2", true)), MULTI, "$x$ |\n| $y$ tail | b2 |\n| c1 | c2", "the `$x$` glyphs down to c2: the anchor begins at the formula");
  anchors(M(bmu, MULTI, startOf(gx), point(bmu, "After", true)), MULTI, "$x$ |\n| $y$ tail | b2 |\n| c1 | c2 |\n\nAfter", "the `$x$` glyphs into the prose after the table");
  anchors(M(bmu, MULTI, { node: tmu[1], offset: 0 }, point(bmu, "c2", true)), MULTI, "$x$ |\n| $y$ tail | b2 |\n| c1 | c2", "the <td> before the `$x$` glyphs down to c2");
  anchors(M(bmu, MULTI, point(bmu, "Head1"), endOf(gy)), MULTI, "Head1 | Head2 |\n|---|---|\n| a1 | $x$ |\n| $y$", "Head1 to the end of the `$y$` glyphs: the anchor ends at the formula");
  anchors(M(bmu, MULTI, startOf(gx), point(bmu, "tail", true)), MULTI, "$x$ |\n| $y$ tail", "the `$x$` glyphs to the end of `tail`: one positioned cell");
  const TWO = "| A | B |\n|---|---|\n| a1 | $x$ |\n\nBetween.\n\n| C |\n|---|\n| c1 |\n";
  const btwo = buildRendered(TWO);
  anchors(M(btwo, TWO, startOf(glyphsOf(allOf(btwo, "TD")[1], "x")), point(btwo, "c1", true)), TWO, "$x$ |\n\nBetween.\n\n| C |\n|---|\n| c1", "the first table's formula-alone last cell into the second table's body cell: one anchor from the formula through the prose between");
});

test("a selection whose characters are two cells holding a formula alone, and nothing positioned, is the formula's, as a paragraph's selection of formulas alone is (the formula rule, kept by decision 53; the review's round 4 made it the one-cell rule's): the `$x$` glyphs to the end of the `$y$` glyphs in one row, from the <td> before to the <td> after, from the row's own start to its end, each with the Raw view offered on `$x$`, the formula the drag began on, and the drag reversed with the offer on the formula its anchor covers; two rows, `$x$` to `$y$`; a table of four formulas from the first header cell's glyphs to the last body cell's, and the table from end to end; the controls: one formula's glyphs alone name the formula with the Raw view on it, and a positioned cell into the next cell's formula anchors `a1 | $x$`", () => {
  const F1 = "Intro.\n\n| A | B |\n|---|---|\n| $x$ | $y$ |\n\nAfter.\n";
  const b1 = buildRendered(F1);
  const t1 = allOf(b1, "TD");
  const gx = glyphsOf(t1[0], "x"), gy = glyphsOf(t1[1], "y");
  expectFormula(M(b1, F1, startOf(gx), endOf(gy)), F1, ["$x$"], "the `$x$` glyphs to the end of the `$y$` glyphs");
  expectFormula(M(b1, F1, { node: t1[0], offset: 0 }, { node: t1[1], offset: t1[1].childNodes.length }), F1, ["$x$"], "the <td> before to the <td> after");
  const tr = t1[0].parentNode as FakeElement;
  expectFormula(M(b1, F1, { node: tr, offset: 0 }, { node: tr, offset: tr.childNodes.length }), F1, ["$x$"], "the row from its start to its end");
  expectFormula(M(b1, F1, endOf(gy), startOf(gx)), F1, ["$x$", "$y$"], "the drag reversed");
  const one = bad(M(b1, F1, startOf(gx), endOf(gx)), "the `$x$` glyphs alone");
  assert.equal(one.reason, FORMULA, "one formula alone is the formula's");
  assert.equal(F1.slice(one.rawRange!.start, one.rawRange!.end), "$x$", "...with the Raw view on it");
  const F2 = "Intro.\n\n| A | B |\n|---|---|\n| a1 | $x$ |\n| $y$ | b2 |\n\nAfter.\n";
  const b2 = buildRendered(F2);
  const t2 = allOf(b2, "TD");
  expectFormula(M(b2, F2, startOf(glyphsOf(t2[1], "x")), endOf(glyphsOf(t2[2], "y"))), F2, ["$x$"], "row 1's `$x$` glyphs to row 2's `$y$` glyphs");
  anchors(M(b2, F2, point(b2, "a1"), endOf(glyphsOf(t2[1], "x"))), F2, "a1 | $x$", "a1 into the next cell's formula: the positioned cell and the formula anchor");
  const F4 = "Intro.\n\n| $h$ | $k$ |\n|---|---|\n| $x$ | $y$ |\n\nAfter.\n";
  const b4 = buildRendered(F4);
  expectFormula(M(b4, F4, startOf(glyphsOf(allOf(b4, "TH")[0], "h")), endOf(glyphsOf(allOf(b4, "TD")[1], "y"))), F4, ["$h$"], "four formula-only cells, the first header cell's glyphs to the last body cell's");
  const table = allOf(b4, "TABLE")[0];
  expectFormula(M(b4, F4, { node: table, offset: 0 }, { node: table, offset: table.childNodes.length }), F4, ["$h$"], "the table from its start to its end");
});

// ── item 3, the review's round 5 shapes: a formula-only or picture-only cell the span runs through lies inside the anchor ──

test("the shapes the review's round 5 refused by source span anchor to the selected characters, a formula-only cell the span runs through inside the quote (decision 53): from the prose before a table through an all-formula header row into a body cell, `Intro para.` to the end of `a`, anchors `Intro para.\\n\\n| $h$ | $k$ |\\n|---|---|\\n| a`, from mid-paragraph, to mid-cell and the drag reversed alike, to the end of `b` the whole row and to the end of `After.` the whole table with the prose after; from a positioned header cell through an all-formula body row into the prose after; a whole table of formulas between two paragraphs; a positioned cell through a trailing formula-only cell into the prose after, and through two rows; the prose before a formula-first header row into the second header cell and into a body cell; a header-only table's positioned cell through its formula cell into the prose after; two tables, the first's cell through the prose between into the second's positioned second cell; the text twins anchor alike; a formula-only last cell into the prose after, one cell alone and one table's last cell into the next table's formula-only first header cell map as before; and the pad before the first of two formula-only cells to the pad after the second is the formula's", () => {
  const S1 = "Intro para.\n\n| $h$ | $k$ |\n|---|---|\n| a | b |\n\nAfter.\n";
  const b1 = buildRendered(S1);
  const t1 = allOf(b1, "TD");
  const tA = t1[0].childNodes[0] as FakeText, tB = t1[1].childNodes[0] as FakeText;
  assert.deepEqual([allOf(b1, "TH").map((t) => t.textContent), t1.map((t) => t.textContent)], [["h", "k"], ["a", "b"]]);
  anchors(M(b1, S1, point(b1, "Intro"), endOf(tA)), S1, "Intro para.\n\n| $h$ | $k$ |\n|---|---|\n| a", "Intro to the end of `a` under an all-formula header row (before: refused on `$h$ | $k$ |...| a`)");
  anchors(M(b1, S1, point(b1, "para."), endOf(tA)), S1, "para.\n\n| $h$ | $k$ |\n|---|---|\n| a", "from mid-paragraph");
  anchors(M(b1, S1, point(b1, "Intro"), { node: tA, offset: 1 }), S1, "Intro para.\n\n| $h$ | $k$ |\n|---|---|\n| a", "to the selected character of the cell");
  anchors(M(b1, S1, endOf(tA), point(b1, "Intro")), S1, "Intro para.\n\n| $h$ | $k$ |\n|---|---|\n| a", "the drag reversed");
  anchors(M(b1, S1, point(b1, "Intro"), endOf(tB)), S1, "Intro para.\n\n| $h$ | $k$ |\n|---|---|\n| a | b", "to the end of `b`: the whole row");
  anchors(M(b1, S1, point(b1, "Intro"), point(b1, "After.", true)), S1, "Intro para.\n\n| $h$ | $k$ |\n|---|---|\n| a | b |\n\nAfter.", "to the end of `After.`: the whole table with the prose either side");
  const K1 = "Intro para.\n\n| h | k |\n|---|---|\n| a | b |\n\nAfter.\n";
  const kb = buildRendered(K1);
  anchors(M(kb, K1, point(kb, "Intro"), endOf(allOf(kb, "TD")[0].childNodes[0] as FakeText)), K1, "Intro para.\n\n| h | k |\n|---|---|\n| a", "the text twin anchors alike");
  const S2 = "Intro paragraph.\n\n| A | B |\n|---|---|\n| $x$ | $y$ |\n\nAfter.\n";
  const b2 = buildRendered(S2);
  anchors(M(b2, S2, point(b2, "B"), point(b2, "After.", true)), S2, "B |\n|---|---|\n| $x$ | $y$ |\n\nAfter.", "`B` to the end of `After.` through an all-formula body row");
  anchors(M(b2, S2, point(b2, "After.", true), point(b2, "B")), S2, "B |\n|---|---|\n| $x$ | $y$ |\n\nAfter.", "the drag reversed");
  anchors(M(b2, S2, point(b2, "A"), point(b2, "After.", true)), S2, "A | B |\n|---|---|\n| $x$ | $y$ |\n\nAfter.", "`A` to the end of `After.`: the whole table");
  anchors(M(b2, S2, point(b2, "B"), point(b2, "After.")), S2, "B |\n|---|---|\n| $x$ | $y$", "`B` to the START of `After.`: the end snaps back to the table and the formula beside it is covered");
  const x2 = allOf(b2, "TD");
  expectFormula(M(b2, S2, { node: x2[0], offset: 0 }, { node: x2[1], offset: x2[1].childNodes.length }), S2, ["$x$"], "the pad before `$x$` to the pad after `$y$`: formulas alone, the formula's");
  const S3 = "Intro.\n\n| $h$ | $k$ |\n|---|---|\n| $x$ | $y$ |\n\nAfter.\n";
  const b3 = buildRendered(S3);
  anchors(M(b3, S3, point(b3, "Intro"), point(b3, "After.", true)), S3, "Intro.\n\n| $h$ | $k$ |\n|---|---|\n| $x$ | $y$ |\n\nAfter.", "a whole table of formulas between two paragraphs");
  const FL = "| FL1 | FL2 |\n|---|---|\n| fl-a | $n$ |\n\nAfter the formula-last table.\n";
  const bl = buildRendered(FL);
  anchors(M(bl, FL, point(bl, "fl-a"), point(bl, "After the formula-last table.", true)), FL, "fl-a | $n$ |\n\nAfter the formula-last table.", "`fl-a` through the trailing formula-only cell into the prose after");
  anchors(M(bl, FL, startOf(glyphsOf(allOf(bl, "TD")[1], "n")), point(bl, "After the formula-last table.", true)), FL, "$n$ |\n\nAfter the formula-last table.", "a formula-only last cell into the prose after, as before");
  anchors(mapText(bl, FL, "fl-a"), FL, "fl-a", "one cell alone, as before");
  const TX = "| FL1 | FL2 |\n|---|---|\n| fl-a | tx |\n\nAfter the text-last table.\n";
  const bx = buildRendered(TX);
  anchors(M(bx, TX, point(bx, "fl-a"), point(bx, "After the text-last table.", true)), TX, "fl-a | tx |\n\nAfter the text-last table.", "the text twin anchors alike");
  const FB = "| FB1 | FB2 | FB3 |\n|---|---|---|\n| fb-a | $m$ | fb-c |\n| fb-d | fb-e | $n$ |\n\nAfter the formula-body table.\n";
  const bb = buildRendered(FB);
  anchors(M(bb, FB, point(bb, "fb-e"), point(bb, "After the formula-body table.", true)), FB, "fb-e | $n$ |\n\nAfter the formula-body table.", "`fb-e` through `$n$` into the prose after");
  anchors(M(bb, FB, point(bb, "fb-d"), point(bb, "After the formula-body table.", true)), FB, "fb-d | fb-e | $n$ |\n\nAfter the formula-body table.", "`fb-d` to the prose after: the formula-only cell inside the quote");
  const FF = "Before the formula-first table.\n\n| $m$ | FF2 |\n|---|---|\n| ff-a | ff-b |\n";
  const bf = buildRendered(FF);
  anchors(M(bf, FF, point(bf, "Before"), point(bf, "FF2", true)), FF, "Before the formula-first table.\n\n| $m$ | FF2", "the prose before into the second header cell over a formula-first one");
  anchors(M(bf, FF, point(bf, "Before"), point(bf, "ff-a", true)), FF, "Before the formula-first table.\n\n| $m$ | FF2 |\n|---|---|\n| ff-a", "the prose before into a body cell");
  const Q1 = "Intro\n\n| a | $x$ |\n|---|---|\n\nAfter the table.\n";
  const bq = buildRendered(Q1);
  anchors(M(bq, Q1, point(bq, "a"), point(bq, "After the table.", true)), Q1, "a | $x$ |\n|---|---|\n\nAfter the table.", "a header-only table's positioned cell through its formula cell into the prose after, the delimiter row inside the quote");
  const Q4 = "| aaa |\n|---|\n\nmid sentence.\n\n| $y$ | cee |\n|---|---|\n";
  const b4 = buildRendered(Q4);
  anchors(M(b4, Q4, point(b4, "aaa"), point(b4, "cee", true)), Q4, "aaa |\n|---|\n\nmid sentence.\n\n| $y$ | cee", "one table's cell through the prose between into the next table's positioned second cell");
  anchors(M(b4, Q4, point(b4, "mid"), point(b4, "cee", true)), Q4, "mid sentence.\n\n| $y$ | cee", "the prose between into that cell");
  anchors(M(b4, Q4, point(b4, "aaa"), endOf(glyphsOf(allOf(b4, "TH")[1], "y"))), Q4, "aaa |\n|---|\n\nmid sentence.\n\n| $y$", "one table's last cell into the next table's formula-only FIRST header cell, as before");
});

test("a cell holding a picture alone lies inside the anchor when the span runs through it (a picture emits no character and is no formula, so it is never covered at an end: a drag released on the pad past one anchors the positioned cells alone): a positioned cell through a trailing picture-only cell into the prose after anchors `pl-a | ![p](x.png) |\\n\\nAfter the picture-last table.`, the raw image markup inside the quote as a Raw selection mints it; the prose before a picture-only header row into a body cell anchors through the header's pictures; a header cell through a picture-first body cell into the next; one cell alone maps; the drag to the cell pad past the picture anchors the positioned cell alone; and an EMPTY trailing cell lies inside the anchor like any other characters", () => {
  const PL = "| PL1 | PL2 |\n|-----|-----|\n| pl-a | ![p](x.png) |\n\nAfter the picture-last table.\n";
  const bl = buildRendered(PL);
  const tl = allOf(bl, "TD");
  assert.deepEqual(tl.map((t) => shape(t)), [["#text(pl-a)"], ["IMG."]], "the picture cell holds the image alone");
  anchors(M(bl, PL, point(bl, "pl-a"), point(bl, "After the picture-last table.", true)), PL, "pl-a | ![p](x.png) |\n\nAfter the picture-last table.", "`pl-a` through the picture-only cell into the prose after (before: refused on `pl-a | ![p](x.png)`)");
  anchors(M(bl, PL, point(bl, "PL2"), point(bl, "pl-a", true)), PL, "PL2 |\n|-----|-----|\n| pl-a", "the header cell into `pl-a`");
  anchors(mapText(bl, PL, "pl-a"), PL, "pl-a", "pl-a alone");
  anchors(M(bl, PL, point(bl, "pl-a"), { node: tl[1], offset: tl[1].childNodes.length }), PL, "pl-a", "the drag to the cell pad past the picture selects no character of that cell and covers no formula: the positioned cell alone");
  const PH = "Before the picture-header table.\n\n| ![p](x.png) | ![q](y.png) |\n|---|---|\n| ph-a | ph-b |\n\nAfter the picture-header table.\n";
  const bh = buildRendered(PH);
  anchors(M(bh, PH, point(bh, "Before"), point(bh, "ph-a", true)), PH, "Before the picture-header table.\n\n| ![p](x.png) | ![q](y.png) |\n|---|---|\n| ph-a", "the prose before through a picture-only header row into `ph-a`");
  anchors(M(bh, PH, point(bh, "ph-a"), point(bh, "ph-b", true)), PH, "ph-a | ph-b", "two body cells");
  const PF = "| PF1 | PF2 |\n|---|---|\n| ![p](x.png) | pf-b |\n\nAfter the picture-first table.\n";
  const bf = buildRendered(PF);
  anchors(M(bf, PF, point(bf, "PF2"), point(bf, "pf-b", true)), PF, "PF2 |\n|---|---|\n| ![p](x.png) | pf-b", "a header cell through the picture-first body cell into `pf-b`, the picture inside the quote");
  const EL = "| EL1 | EL2 |\n|-----|-----|\n| el-a |  |\n\nAfter the empty-last table.\n";
  const be = buildRendered(EL);
  anchors(M(be, EL, point(be, "el-a"), point(be, "After the empty-last table.", true)), EL, "el-a |  |\n\nAfter the empty-last table.", "el-a into the prose after: the empty trailing cell's pipes inside the quote");
});
