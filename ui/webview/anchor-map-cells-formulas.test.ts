// The Slice 8 review, round 4 (plans/markdown-viewer.md, Slice 8, items 1, 3 and 4): the shapes a formula inside a table cell
// makes for the one-cell rule and for a change's point, found unpinned or wrong by the round's finders and fixed in
// anchor-map.ts. A formula emits no positioned character (a zero-text hole, walkInline's mathInline case), so a cell holding one
// alone had no Cell record and the two one-cell counts, which read the records, never saw two such cells in one span; a point
// inside a formula that ended a cell's text placed against the block's next positioned character, the next cell's; and the
// pass's refusal offered the Raw view from the first positioned character it counted, leaving a covered formula at the span's
// edge out. Now every cell whose source holds something has a record (walkRow, an empty character range for a formula alone),
// the covered-formula check counts the table's cells by source span and offers the covered cells' span (coveredCells), the
// pass's offer widens by a covered formula of the same table, a selection whose characters are two covered formulas alone is
// the one-cell rule's before it is the formula's (orFormula), and renderedSpot reads a cell's own characters alone. Driven over
// the DOM stand-in anchor-map-cells.test.ts drives, marked's output under the one configuration parsed as a browser parses a
// fragment, KaTeX's fill stood in for (the browser leg's fifth test drags over the real fill). Every behaviour case here fails
// over a git archive of 90c6ff242, round 3's fix commit, at the assertion its title names. Synthetic values only: invented notes,
// no real session text.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { mapRenderedSelection, paintChangesRendered, unpaintChanges, type SelLike, type MapResult, type ChangePaint } from "./anchor-map";
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
const ONE_CELL = /^This selection spans more than one cell of a table; select within one cell, or comment on it from the Raw view\.$/;

// ── this file's own helpers ──
/** The glyph text node of the formula `tex` stood in under `cell` (the `.katex` root's one text node). */
const glyphsOf = (cell: FakeElement, tex: string): FakeText => { const k = find(cell, "SPAN", tex); assert.equal(k.getAttribute("class"), "katex", tex + ": the formula's root"); return k.childNodes[0] as FakeText; };
/** The end of `t`'s text (a boundary right after its last character). */
const endOf = (t: FakeText): Pt => ({ node: t, offset: t.data.length });
const startOf = (t: FakeText): Pt => ({ node: t, offset: 0 });
const M = (box: FakeElement, src: string, a: Pt, f: Pt): MapResult => mapRenderedSelection(sel(a, f), El(box), src);
/** The refusal is the one-cell sentence, the Raw view offered on exactly `span`, the search beginning at the span's start. */
function expectOneCell(r: MapResult, src: string, span: string, label: string): void {
  const b = bad(r, label + ": maps where the one-cell rule refuses");
  assert.match(b.reason, ONE_CELL, label + ": " + b.reason);
  assert.equal(b.rawHasQuote, true, label + ": the Raw view is offered on the span");
  assert.equal(src.slice(b.rawRange!.start, b.rawRange!.end), span, label + ": the exact span");
  assert.equal(b.blockStartOffset, b.rawRange!.start, label + ": the search begins at the span's start");
  assert.equal(b.blockStartLine, src.slice(0, b.rawRange!.start).split("\n").length - 1, label + ": the span's line");
}
const FORMULA = "This selection touches a formula; comment on it from the Raw view.";
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

// ── item 3: the one-cell rule counts every cell of the span, a cell holding a formula alone among them ──

test("the one-cell rule counts a cell holding a formula alone wherever it stands in the span (the review's round 4; before: only the covered formula's own cell was counted, so a span over two or more such cells with no positioned cell in it counted one and mapped, the pipes and the delimiter row inside the Rendered quote): from the prose before a table through its all-formula header row, `Intro para.` to the end of the `$k$` glyphs or to the <th> past them, refuses with the one-cell sentence and the Raw view on `$h$ | $k$`, the table's covered cells; on into the body through the delimiter row, `$h$ | $k$ |\n|---|---|\n| $a$`, and the whole table; from a first cell holding a formula alone through the next into the prose after the table refuses on `$x$ | $y$` (before: mapped `$x$ | $y$ |\n\nAfter.`); three formula cells refuse; the controls: the prose into the first header cell alone maps by the one-cell-plus-prose rule, a header cell into two body formula cells refuses on the cells' span, the text twin refuses as before, two formulas in ONE cell are one cell and map, and a last cell holding a formula alone into the prose after maps", () => {
  const H = "Intro para.\n\n| $h$ | $k$ |\n|---|---|\n| $a$ | $b$ |\n\nAfter.\n";
  const box = buildRendered(H);
  const ths = allOf(box, "TH"), tds = allOf(box, "TD");
  assert.deepEqual([ths.map((t) => t.textContent), tds.map((t) => t.textContent)], [["h", "k"], ["a", "b"]], "every cell a formula alone, the glyphs stood in for");
  const intro = point(box, "Intro");
  expectOneCell(M(box, H, intro, endOf(glyphsOf(ths[1], "k"))), H, "$h$ | $k$", "Intro to the end of the `$k$` glyphs (before: mapped `Intro para.\\n\\n| $h$ | $k$`)");
  expectOneCell(M(box, H, intro, { node: ths[1], offset: ths[1].childNodes.length }), H, "$h$ | $k$", "Intro to the <th> past the `$k$` glyphs");
  expectOneCell(M(box, H, intro, endOf(glyphsOf(tds[0], "a"))), H, "$h$ | $k$ |\n|---|---|\n| $a$", "Intro to the end of the `$a$` glyphs (before: mapped, the delimiter row inside the quote)");
  expectOneCell(M(box, H, intro, endOf(glyphsOf(tds[1], "b"))), H, "$h$ | $k$ |\n|---|---|\n| $a$ | $b$", "Intro to the end of the `$b$` glyphs: the whole table (before: mapped)");
  assert.equal(ok(M(box, H, intro, endOf(glyphsOf(ths[0], "h"))), "Intro to the end of the `$h$` glyphs").quote, "Intro para.\n\n| $h$", "one cell and the prose before it map, the formula inside the quote");
  const X = "Intro paragraph.\n\n| A | B |\n|---|---|\n| $x$ | $y$ |\n\nAfter.\n";
  const xb = buildRendered(X);
  const xt = allOf(xb, "TD");
  expectOneCell(M(xb, X, startOf(glyphsOf(xt[0], "x")), point(xb, "After.", true)), X, "$x$ | $y$", "the `$x$` glyphs into the prose after the table (before: mapped `$x$ | $y$ |\\n\\nAfter.`)");
  expectOneCell(M(xb, X, { node: xt[0], offset: 0 }, point(xb, "After.", true)), X, "$x$ | $y$", "the <td> before the `$x$` glyphs into the prose after");
  expectOneCell(M(xb, X, point(xb, "B"), endOf(glyphsOf(xt[1], "y"))), X, "B |\n|---|---|\n| $x$ | $y$", "the header cell `B` through both body formula cells (round 3's path, the offer now the cells' span)");
  assert.equal(ok(M(xb, X, startOf(glyphsOf(xt[1], "y")), point(xb, "After.", true)), "the `$y$` glyphs into the prose after").quote, "$y$ |\n\nAfter.", "a last cell holding a formula alone into the prose after maps, the last-cell-into-prose rule");
  const T = "Intro paragraph.\n\n| $x$ | $y$ | $z$ |\n|---|---|---|\n| a | b | c |\n";
  const tb = buildRendered(T);
  expectOneCell(M(tb, T, point(tb, "Intro"), endOf(glyphsOf(allOf(tb, "TH")[2], "z"))), T, "$x$ | $y$ | $z$", "three formula-only header cells (before: mapped)");
  const K = "Intro para.\n\n| h | k |\n|---|---|\n| a | b |\n";
  const kb = buildRendered(K);
  expectOneCell(M(kb, K, point(kb, "Intro"), point(kb, "k", true)), K, "h | k", "the text twin: the pass's rule, unchanged");
  const ONE = "Intro paragraph.\n\n| $x$ $y$ | c |\n|---|---|\n| a | b |\n";
  const ob = buildRendered(ONE);
  assert.equal(ok(M(ob, ONE, point(ob, "Intro"), endOf(glyphsOf(allOf(ob, "TH")[0], "y"))), "two formulas in one cell").quote, "Intro paragraph.\n\n| $x$ $y$", "two formulas in ONE cell are one cell: the one-cell-plus-prose rule maps");
});

test("the pass's one-cell refusal offers the Raw view on the span WITH a formula the selection covered whole at its start or its end inside the same table (the review's round 4; before: from the first positioned character it counted to the last, so the covered formula, which emits none, lay outside the preselection while round 3's path put it inside): a header cell through the header into a body cell holding a formula alone offers `A | B |\n|---|---|\n| $x$`, and through both body cells `... | $x$ | $y$`; a drag begun in a formula-only header cell into a body cell offers `$h$ | B |\n|---|---|\n| a1`, from the <th> before the glyphs too; two positioned cells and a trailing formula offer `a1 | b1 $x$`; a drag begun on a formula-alone cell's glyphs down through three rows offers from the formula, into the prose after too, and one ended on the `$y$` glyphs of a later row offers through the formula; round 3's one-positioned-cell shape still offers `$x$ |\n| $y$ tail`; and a formula in ANOTHER table, the drag having crossed the prose between, does not widen the refusing table's offer", () => {
  const S1 = "| A | B |\n|---|---|\n| $x$ | $y$ |\n";
  const b1 = buildRendered(S1);
  const t1 = allOf(b1, "TD");
  expectOneCell(M(b1, S1, point(b1, "A"), endOf(glyphsOf(t1[0], "x"))), S1, "A | B |\n|---|---|\n| $x$", "A to the end of the `$x$` glyphs (before: the offer `A | B`)");
  expectOneCell(M(b1, S1, point(b1, "A"), { node: t1[0], offset: t1[0].childNodes.length }), S1, "A | B |\n|---|---|\n| $x$", "A to the <td> past the `$x$` glyphs");
  expectOneCell(M(b1, S1, point(b1, "A"), endOf(glyphsOf(t1[1], "y"))), S1, "A | B |\n|---|---|\n| $x$ | $y$", "A to the end of the `$y$` glyphs (before: `A | B`)");
  const S3 = "| $h$ | B |\n|---|---|\n| a1 | b1 |\n";
  const b3 = buildRendered(S3);
  const h3 = allOf(b3, "TH");
  expectOneCell(M(b3, S3, startOf(glyphsOf(h3[0], "h")), point(b3, "a1", true)), S3, "$h$ | B |\n|---|---|\n| a1", "the `$h$` glyphs into a1 (before: `B |\\n|---|---|\\n| a1`)");
  expectOneCell(M(b3, S3, { node: h3[0], offset: 0 }, point(b3, "a1", true)), S3, "$h$ | B |\n|---|---|\n| a1", "the <th> before the glyphs into a1");
  const SM = "| A | B |\n|---|---|\n| a1 | b1 $x$ |\n";
  const bm = buildRendered(SM);
  expectOneCell(M(bm, SM, point(bm, "a1"), endOf(glyphsOf(allOf(bm, "TD")[1], "x"))), SM, "a1 | b1 $x$", "a1 to the end of `b1 $x$`'s glyphs (before: `a1 | b1`)");
  const MULTI = "| Head1 | Head2 |\n|---|---|\n| a1 | $x$ |\n| $y$ tail | b2 |\n| c1 | c2 |\n\nAfter the table.\n";
  const bmu = buildRendered(MULTI);
  const tmu = allOf(bmu, "TD");
  assert.deepEqual(tmu.map((t) => t.textContent), ["a1", "x", "y tail", "b2", "c1", "c2"]);
  const gx = glyphsOf(tmu[1], "x"), gy = glyphsOf(tmu[2], "y");
  expectOneCell(M(bmu, MULTI, startOf(gx), point(bmu, "c2", true)), MULTI, "$x$ |\n| $y$ tail | b2 |\n| c1 | c2", "the `$x$` glyphs down to c2 (before: the offer began at `tail`, the formula-alone cell the drag began on outside it)");
  expectOneCell(M(bmu, MULTI, startOf(gx), point(bmu, "After", true)), MULTI, "$x$ |\n| $y$ tail | b2 |\n| c1 | c2", "the `$x$` glyphs into the prose after the table: the same offer");
  expectOneCell(M(bmu, MULTI, { node: tmu[1], offset: 0 }, point(bmu, "c2", true)), MULTI, "$x$ |\n| $y$ tail | b2 |\n| c1 | c2", "the <td> before the `$x$` glyphs down to c2");
  expectOneCell(M(bmu, MULTI, point(bmu, "Head1"), endOf(gy)), MULTI, "Head1 | Head2 |\n|---|---|\n| a1 | $x$ |\n| $y$", "Head1 to the end of the `$y$` glyphs (before: the offer ended at a1)");
  expectOneCell(M(bmu, MULTI, startOf(gx), point(bmu, "tail", true)), MULTI, "$x$ |\n| $y$ tail", "the `$x$` glyphs to the end of `tail`: one positioned cell, round 3's path, the same offer as before");
  const TWO = "| A | B |\n|---|---|\n| a1 | $x$ |\n\nBetween.\n\n| C |\n|---|\n| c1 |\n";
  const btwo = buildRendered(TWO);
  expectOneCell(M(btwo, TWO, startOf(glyphsOf(allOf(btwo, "TD")[1], "x")), point(btwo, "c1", true)), TWO, "C |\n|---|\n| c1", "the first table's formula-alone last cell into the second table's body cell: the second table refuses on its own cells, the formula another table's");
});

test("a selection whose characters are two cells holding a formula alone, and nothing positioned, is refused by the one-cell rule on the cells' span (the review's round 4; before: as touching a formula, the Raw view offered on the FIRST formula alone, one cell of the two): the `$x$` glyphs to the end of the `$y$` glyphs in one row, from the <td> before to the <td> after, from the row's own start to its end, and the drag reversed; two rows, `$x$ |\n| $y$`; a table of four formulas from the first header cell's glyphs to the last body cell's, and its rows from end to end; the controls: one formula's glyphs alone still name the formula with the Raw view on it, and a positioned cell into the next cell's formula still refuses on `a1 | $x$`", () => {
  const F1 = "Intro.\n\n| A | B |\n|---|---|\n| $x$ | $y$ |\n\nAfter.\n";
  const b1 = buildRendered(F1);
  const t1 = allOf(b1, "TD");
  const gx = glyphsOf(t1[0], "x"), gy = glyphsOf(t1[1], "y");
  expectOneCell(M(b1, F1, startOf(gx), endOf(gy)), F1, "$x$ | $y$", "the `$x$` glyphs to the end of the `$y$` glyphs (before: touches a formula, the offer `$x$`)");
  expectOneCell(M(b1, F1, { node: t1[0], offset: 0 }, { node: t1[1], offset: t1[1].childNodes.length }), F1, "$x$ | $y$", "the <td> before to the <td> after");
  const tr = t1[0].parentNode as FakeElement;
  expectOneCell(M(b1, F1, { node: tr, offset: 0 }, { node: tr, offset: tr.childNodes.length }), F1, "$x$ | $y$", "the row from its start to its end");
  expectOneCell(M(b1, F1, endOf(gy), startOf(gx)), F1, "$x$ | $y$", "the drag reversed");
  const one = bad(M(b1, F1, startOf(gx), endOf(gx)), "the `$x$` glyphs alone");
  assert.equal(one.reason, FORMULA, "one formula alone is the formula's");
  assert.equal(F1.slice(one.rawRange!.start, one.rawRange!.end), "$x$", "...with the Raw view on it");
  const F2 = "Intro.\n\n| A | B |\n|---|---|\n| a1 | $x$ |\n| $y$ | b2 |\n\nAfter.\n";
  const b2 = buildRendered(F2);
  const t2 = allOf(b2, "TD");
  expectOneCell(M(b2, F2, startOf(glyphsOf(t2[1], "x")), endOf(glyphsOf(t2[2], "y"))), F2, "$x$ |\n| $y$", "row 1's `$x$` glyphs to row 2's `$y$` glyphs (before: touches a formula, the offer `$x$`)");
  expectOneCell(M(b2, F2, point(b2, "a1"), endOf(glyphsOf(t2[1], "x"))), F2, "a1 | $x$", "a1 into the next cell's formula: round 3's shape, unchanged");
  const F4 = "Intro.\n\n| $h$ | $k$ |\n|---|---|\n| $x$ | $y$ |\n\nAfter.\n";
  const b4 = buildRendered(F4);
  expectOneCell(M(b4, F4, startOf(glyphsOf(allOf(b4, "TH")[0], "h")), endOf(glyphsOf(allOf(b4, "TD")[1], "y"))), F4, "$h$ | $k$ |\n|---|---|\n| $x$ | $y$", "four formula-only cells, the first header cell's glyphs to the last body cell's (before: touches a formula, the offer `$h$`)");
  const table = allOf(b4, "TABLE")[0];
  expectOneCell(M(b4, F4, { node: table, offset: 0 }, { node: table, offset: table.childNodes.length }), F4, "$h$ | $k$ |\n|---|---|\n| $x$ | $y$", "the table from its start to its end");
});
