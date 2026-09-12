// Three properties of the Rendered view's deletion points (plans/file-review.md, the inline-display follow-on of
// 2026-09-07) that the review found the suite did not pin: each held in the code, and a one-token mutation of
// the code left every test green. Driven over marked's output under the viewer's configuration, parsed into the
// structural stand-in anchor-map.test.ts uses (there is no jsdom in this tree).
//
//   1. A table nested in a list item. Until Slice 8 of plans/markdown-viewer.md it was a HOLE with the table's own
//      extent: renderedSpot places a point past a hole only when the offset is at or after the hole's END (`endN`);
//      with the table's endN mis-set to its start, a deletion INSIDE the table was painted immediately before the
//      text after it, the wrong-words placement the plan says a hole must never produce, and no test failed
//      (anchor-map.test.ts covers the code-fence hole only). Since Slice 8 the table's cells are positioned, so a
//      point inside a cell places in that cell, and the same guard holds for the rest of the table's source: a
//      point on the delimiter row or after the last cell's bar stays unpainted (renderedSpot's table rule), never
//      beside the words after the table.
//   2. Where one mapped block ends exactly as the next begins (a heading and the paragraph under it: marked's
//      heading raw swallows its trailing newlines, so the pair is adjacent with or without a blank line), the
//      block that BEGINS at the offset holds the point. A deletion of a paragraph's first word otherwise lands
//      at the end of the heading, struck at heading size.
//   3. A label with no visible character (a removed space or tab) keeps its width in Rendered. deletionLabel
//      leaves spaces and tabs as they are, which the Raw rows (white-space: pre-wrap) show at their width; a
//      rendered block's white-space is normal, and the sheet's generated content follows it, so the label
//      collapsed against the space beside it: a 0px point with no struck mark, no underline and nothing to hover
//      or tap, while the painter reported it shown and its card offered a scroll to it. The point now carries
//      the rows' white-space when its label has no visible character; a label with one keeps the block's, which
//      folds a multi-line label onto its line. anchor-map-whitespace-point-browser.test.ts measures the result.
//
// And Slice 8's item 4 (the change points inside a fence), pinned with the table's rule above: the code's lines
// are positioned, so a point inside a line places in its row, before or after the nearest character of the line,
// and a point on a fence's opener or closer line, which renders nothing, keeps its card (renderedSpot's FENCE_LINE
// rule), except at the lines' edges, where it sits beside the text it borders: a top-level opener's first
// character places before the code's first character (no text before it in the block), and the line feed that
// ends the last code line places after that line's last character. A point on a blank code line goes into the
// line's own row where the pre has rows (the Slice 8 review, round 1; anchor-map-code-lines.test.ts holds it over
// the viewer's rows); this stand-in's pre has none, so the rule's fallback places it before the next line's first
// character, the nearest positioned one. An empty fence is nothing's; an indented block has no fence lines.
//
// Fixtures are synthetic (the notes-api world).
import { test } from "node:test";
import assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";   // the one markdown configuration, applied here as the viewer applies it
import { paintChangesRaw, paintChangesRendered, unpaintChanges, deletionLabel, PILCROW, type ChangePaint } from "./anchor-map";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const FIX = (f: string) => path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map-fixtures", f);

// ── the viewer's marked configuration: the one every bundle applies (md-config.ts; pinned by anchor-map.test.ts) ──
applyMdConfig();

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser ─────
class FakeNode {
  nodeType = 0;
  parentNode!: FakeNode | null;
  childNodes!: FakeNode[];
  constructor(public ownerDocument: FakeDocument) {
    // the edges are non-enumerable, and so is every other object the node holds (hideEdges, ui/test-dom-shim.ts): a
    // failing assertion's dump of a node is its own primitives, never the tree it hangs in
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get textContent(): string { return this.nodeType === 3 ? (this as unknown as FakeText).data : this.childNodes.map((c) => c.textContent).join(""); }
}
class FakeText extends FakeNode {
  nodeType = 3;
  constructor(doc: FakeDocument, public data: string) { super(doc); hideEdges(this); }
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
/** The fragment parser a browser's innerHTML applies, reduced to what marked emits (anchor-map.test.ts's). */
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
        for (let k = stack.length - 1; k > 0; k--) { if (stack[k].tagName === name) { stack.length = k; break; } }
        i = e + 1; continue;
      }
      const m = /^<([a-zA-Z][\w:-]*)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*)\s*(\/?)>/.exec(html.slice(i));
      if (!m) { top().appendChild(doc.createTextNode("<")); i++; continue; }
      const el = doc.createElement(m[1]);
      const attrRe = /([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
      let a: RegExpExecArray | null;
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], decodeEntities(a[2] ?? a[3] ?? a[4] ?? ""));
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
const escapeHtml = (s: string): string => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
/** The viewer's Raw rows for a plain-text file (no highlighter): one `.fv-cl > .fv-ct` per line. */
function buildRaw(text: string): FakeElement {
  const doc = new FakeDocument();
  const lines = text.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  const code = doc.createElement("code"); code.setAttribute("class", "hljs");
  for (const n of parseHTML(doc, lines.map((ln) => `<span class="fv-cl"><span class="fv-ct">${escapeHtml(ln)}</span></span>`).join(""))) code.appendChild(n);
  return code;
}
/** The viewer's Rendered body: `div.fileview-md > marked output`. */
function buildRendered(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);
  return box;
}
const El = (n: FakeNode) => n as unknown as Element;

// ── helpers ────────────────────────────────────────────────────────────────────────────────────────
/** A structural serialization: every text node its own `#"..."`, every attribute shown. */
function serialize(n: FakeNode): string {
  if (n.nodeType === 3) return "#" + JSON.stringify((n as FakeText).data);
  const e = n as FakeElement;
  const attrs = [...e.attrs.entries()].sort().map(([k, v]) => ` ${k}=${JSON.stringify(v)}`).join("");
  return `<${e.tagName}${attrs}>` + e.childNodes.map(serialize).join("") + `</${e.tagName}>`;
}
const docOrder = (root: FakeNode): FakeNode[] => { const out: FakeNode[] = []; const visit = (n: FakeNode) => { out.push(n); n.childNodes.forEach(visit); }; visit(root); return out; };
const elements = (root: FakeNode): FakeElement[] => docOrder(root).filter((n) => n.nodeType === 1) as FakeElement[];
const withClass = (root: FakeNode, cls: string): FakeElement[] => elements(root).filter((e) => (e.getAttribute("class") || "").split(" ").includes(cls));
const withTag = (root: FakeNode, tag: string): FakeElement[] => elements(root).filter((e) => e.tagName === tag);
/** The text of `block` before `point` and after it, in document order (the point itself holds none). */
function around(block: FakeNode, point: FakeNode): [string, string] {
  let pre = "", post = "", seen = false;
  const visit = (n: FakeNode) => {
    if (n === point) { seen = true; return; }
    if (n.nodeType === 3) { if (seen) post += (n as FakeText).data; else pre += (n as FakeText).data; return; }
    for (const c of n.childNodes) visit(c);
  };
  visit(block);
  return [pre, post];
}
/** The nearest top-level block (a child of the .fileview-md box) holding `n`. */
const blockOf = (box: FakeNode, n: FakeNode): FakeElement => { let x = n; while (x.parentNode && x.parentNode !== box) x = x.parentNode; return x as FakeElement; };
const inside = (n: FakeNode, tag: string): boolean => { let p = n.parentNode; while (p) { if (p.nodeType === 1 && (p as FakeElement).tagName === tag) return true; p = p.parentNode; } return false; };
const at = (source: string, s: string, from = 0): number => { const i = source.indexOf(s, from); assert.ok(i >= 0, "source has " + JSON.stringify(s)); return i; };
const COLORS: Record<string, string> = { web: "rgb(10, 20, 30)" };   // api has no live match: no colour (the plan's Risks entry)
const stylesFor = (c: ChangePaint): Record<string, string> => (COLORS[c.author] ? { "--fc-author": COLORS[c.author] } : {});
const del = (id: string, curFrom: number, oldText = "gone", author = "web"): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText, author });
const point = (root: FakeNode, id: string): FakeElement => { const x = withClass(root, "fc-del").find((m) => m.getAttribute("data-id") === id); assert.ok(x, id + " painted"); return x!; };

// ── 1. a nested table: its cells are positioned (Slice 8), the rest of its source is nothing's ─────────────────────────────
// Until Slice 8 the table was a hole with the table's own extent and every point inside it was unpainted. Now a point inside a
// cell places in that cell, and a point in the table's source outside every cell (the delimiter row, the bar after the last
// cell) stays unpainted, as before: a point there would land in a cell the change is not in.

test("Rendered deletion points and a table nested in a list item: inside a cell (a body cell, the header) the point places in that cell (Slice 8; before: unpainted, the table a hole); on the delimiter row and right after the last cell's bar the change stays unpainted; at the text before the table and at the text after it the point sits against that text, never beside the words after the table; at the table's first character it sits after the item's text before the table, and at a TOP-LEVEL table's, whose block holds no text before it, before the first header cell's first character, the block's edge (the Slice 8 review, round 2, recorded)", () => {
  const source = "- Item one\n\n  | a | b |\n  |---|---|\n  | 1 | 2 |\n\n  after table\n";
  const box = buildRendered(source);
  assert.equal(withTag(box, "TABLE").length, 1, "marked lexes the table inside the item");
  const before = serialize(box);
  const r = paintChangesRendered(El(box), source, [
    del("t-in", at(source, "| 1 |") + 2),        // the cell "1"
    del("t-head", at(source, "| a |") + 2),      // the header cell "a"
    del("t-rule", at(source, "|---|") + 1),      // the delimiter row, which renders nothing
    del("t-end", at(source, "| 2 |") + 4),       // right after the last cell's bar, still the table's source
    del("t-before", at(source, "Item one") + "Item one".length),
    del("t-after", at(source, "after table")),
  ], stylesFor);
  assert.deepEqual(r, { painted: ["t-in", "t-head", "t-before", "t-after"], unpainted: ["t-rule", "t-end"] });
  assert.deepEqual(withClass(box, "fc-del").map((m) => m.getAttribute("data-id")), ["t-before", "t-head", "t-in", "t-after"], "the painted ones in document order; the unpainted ones are nowhere in the body");
  for (const id of ["t-in", "t-head"]) {
    const pt = point(box, id);
    assert.ok(inside(pt, id === "t-in" ? "TD" : "TH"), id + ": inside its cell");
    assert.equal((pt.parentNode as FakeElement).textContent, id === "t-in" ? "1" : "a", id + ": the cell the change is in");
  }
  for (const m of withClass(box, "fc-del")) if (!["t-in", "t-head"].includes(m.getAttribute("data-id") || "")) assert.ok(!inside(m, "TABLE"), "no other point inside the table");
  let [pre, post] = around(blockOf(box, point(box, "t-before")), point(box, "t-before"));
  assert.ok(pre.endsWith("Item one"), "against the text before the table: " + JSON.stringify(pre.slice(-12)));
  assert.ok(!post.trimStart().startsWith("Item"), JSON.stringify(post.slice(0, 10)));
  [pre, post] = around(blockOf(box, point(box, "t-after")), point(box, "t-after"));
  assert.ok(post.startsWith("after table"), "before the text after the table: " + JSON.stringify(post.slice(0, 12)));
  assert.ok(/1\s*2\s*$/.test(pre), "…with the table's cells before it: " + JSON.stringify(pre.slice(-8)));
  // exactly one point stands before "after table": the change that was there, not one from inside the table
  const li = withTag(box, "LI")[0];
  const afterPara = li.childNodes.filter((n) => n.nodeType === 1 && (n as FakeElement).tagName === "P").pop() as FakeElement;
  assert.equal(afterPara.textContent, "after table");
  assert.deepEqual(withClass(afterPara, "fc-del").map((m) => m.getAttribute("data-id")), ["t-after"]);
  unpaintChanges(El(box));
  assert.equal(serialize(box), before);
  // the table's first character (its leading pipe), the boundary: after the text before the table when the block holds such text
  // (the item's), and, for a TOP-LEVEL table, whose block holds nothing before it, before the first header cell's first character,
  // the block's edge, as a top-level fence's opener sits before the code's first character (test 1b); the blank line before a
  // top-level table is nothing's, and a point one character into its leading pipe's row, between the pipe and the cell, is the
  // table's source outside every cell (the Slice 8 review, round 2, recorded; before Slice 8 both tables' first characters were
  // unpainted, the table a hole)
  const r2 = paintChangesRendered(El(box), source, [del("t-first", at(source, "| a |"))], stylesFor);
  assert.deepEqual(r2, { painted: ["t-first"], unpainted: [] });
  assert.ok(!inside(point(box, "t-first"), "TABLE"), "the nested table's first character: not inside the table");
  [pre, post] = around(blockOf(box, point(box, "t-first")), point(box, "t-first"));
  assert.ok(pre.endsWith("Item one"), "...after the text before the table: " + JSON.stringify(pre.slice(-12)));
  assert.ok(post.replace(/\s+/g, "").startsWith("ab12"), JSON.stringify(post.slice(0, 12)));
  unpaintChanges(El(box));
  assert.equal(serialize(box), before);
  const top = "Para before.\n\n| Route | p95 |\n|-------|-----|\n| GET /notes | 120 ms |\n\nAfter.\n";
  const tb = buildRendered(top);
  assert.equal(withTag(tb, "TABLE").length, 1, "marked lexes the top-level table");
  const tFirst = at(top, "| Route");
  const rt = paintChangesRendered(El(tb), top, [del("tt-first", tFirst), del("tt-blank", tFirst - 1), del("tt-in", tFirst + 1), del("tt-cell", tFirst + 2)], stylesFor);
  assert.deepEqual(rt, { painted: ["tt-first", "tt-cell"], unpainted: ["tt-blank", "tt-in"] }, "the table's first character and a cell's place; the blank line before and the pipe's row outside the cell do not");
  const first = point(tb, "tt-first");
  assert.ok(inside(first, "TH"), "a top-level table's first character: inside the first header cell (no text before it in the block)");
  assert.equal(around(withTag(tb, "TABLE")[0], first)[0].trim(), "", "...before the table's first character (marked's whitespace between the table's tags aside)");
  assert.ok(around(withTag(tb, "TABLE")[0], first)[1].startsWith("Route"), "...the header cell's first character right after it");
  assert.equal(withClass(tb, "fc-del").filter((m) => !inside(m, "TABLE")).length, 0, "no point outside the table: the paragraph before it holds none");
  unpaintChanges(El(tb));
});

// ── 1b. a fence: its lines are positioned (Slice 8), its fence lines are nothing's but at their edges ──────────────────────────

test("Rendered deletion points and a fenced code block (Slice 8, item 4): at the opener's first character the point places before the code's first character, inside the opener's info string it stays unpainted; at a line's end it sits after the line's last character, on a blank code line before the next line's first character (this pre has no rows; with the viewer's rows the point goes into the blank line's own row, anchor-map-code-lines.test.ts); at the line feed before the closer after the last code character, on the closer's backticks unpainted, on the blank line after the block unpainted (nothing's rows); an empty fence takes no point anywhere; an indented block's lines place at their indent (before Slice 8: the whole block a hole, every point inside it unpainted)", () => {
  const source = "Intro.\n\n```python\nfirst = 1\n\nthird = 3\n```\n\nAfter.\n";
  const box = buildRendered(source);
  assert.equal(withTag(box, "PRE").length, 1, "marked lexes the fence");
  const before = serialize(box);
  const open = at(source, "```python"), lastLine = at(source, "third = 3"), closer = at(source, "```\n\nAfter");
  const r = paintChangesRendered(El(box), source, [
    del("f-open", open),                                    // the opener's first backtick: the block's edge
    del("f-info", at(source, "python")),                    // inside the opener line: renders nothing
    del("f-line-end", at(source, "first = 1") + "first = 1".length),   // the line feed ending the first line
    del("f-blank", at(source, "first = 1") + "first = 1".length + 1),  // the blank code line
    del("f-mid", lastLine + "third ".length),               // inside the last line
    del("f-closer-lf", lastLine + "third = 3".length),      // the line feed before the closer
    del("f-closer", closer),                                // the closer's first backtick
    del("f-after", closer + 4),                             // the blank line after the block
    del("f-prose", at(source, "After.")),                   // the control
  ], stylesFor);
  assert.deepEqual(r, { painted: ["f-open", "f-line-end", "f-blank", "f-mid", "f-closer-lf", "f-prose"], unpainted: ["f-info", "f-closer", "f-after"] });
  const pre = withTag(box, "PRE")[0];
  for (const id of ["f-open", "f-line-end", "f-blank", "f-mid", "f-closer-lf"]) assert.ok(inside(point(box, id), "PRE"), id + ": inside the code");
  const aroundIn = (id: string) => around(pre, point(box, id));
  assert.deepEqual(aroundIn("f-open"), ["", "first = 1\n\nthird = 3\n"], "the opener's first character: before the code's first character (no text before it in the block)");
  let [a, b] = aroundIn("f-line-end");
  assert.ok(a.endsWith("first = 1") && b.startsWith("\n\nthird"), "the line's end: after its last character: " + JSON.stringify([a, b.slice(0, 8)]));
  [a, b] = aroundIn("f-blank");
  assert.ok(a.endsWith("first = 1\n\n") && b.startsWith("third = 3"), "the blank code line in a pre with no rows: before the next line's first character, the fallback: " + JSON.stringify([a.slice(-6), b.slice(0, 8)]));
  [a, b] = aroundIn("f-mid");
  assert.ok(a.endsWith("third ") && b.startsWith("= 3"), "inside a line: on its row: " + JSON.stringify([a.slice(-6), b.slice(0, 4)]));
  [a, b] = aroundIn("f-closer-lf");
  assert.ok(a.endsWith("third = 3") && b === "\n", "the line feed before the closer: after the last code character: " + JSON.stringify([a.slice(-9), b]));
  assert.deepEqual(withClass(box, "fc-del").filter((m) => !inside(m, "PRE")).map((m) => m.getAttribute("data-id")), ["f-prose"], "one point outside the code: the control's");
  unpaintChanges(El(box));
  assert.equal(serialize(box), before);
  // an empty fence: no line to place, one hole over the whole block; a point anywhere in it keeps its card
  const empty = "Intro.\n\n```\n```\n\nAfter.\n";
  const eb = buildRendered(empty);
  const re = paintChangesRendered(El(eb), empty, [del("e-open", at(empty, "```")), del("e-in", at(empty, "```") + 1), del("e-close", at(empty, "```\n\nAfter")), del("e-prose", at(empty, "After."))], stylesFor);
  assert.deepEqual(re, { painted: ["e-prose"], unpainted: ["e-open", "e-in", "e-close"] });
  unpaintChanges(El(eb));
  // an indented code block: no fence lines; a point at a line's indent places before the line's first character
  const ind = "Intro.\n\n    alpha = 1\n    beta = 2\n\nAfter.\n";
  const ib = buildRendered(ind);
  assert.equal(withTag(ib, "PRE").length, 1, "marked lexes the indented block");
  const ri = paintChangesRendered(El(ib), ind, [del("i-first", at(ind, "    alpha")), del("i-second", at(ind, "    beta")), del("i-in", at(ind, "beta = ") + "beta = ".length)], stylesFor);
  assert.deepEqual(ri, { painted: ["i-first", "i-second", "i-in"], unpainted: [] });
  const ipre = withTag(ib, "PRE")[0];
  assert.deepEqual(around(ipre, point(ib, "i-first")), ["", "alpha = 1\nbeta = 2\n"], "the first line's indent: before its first character");
  [a, b] = around(ipre, point(ib, "i-second"));
  assert.ok(a.endsWith("alpha = 1\n") && b.startsWith("beta"), "the second line's indent: before its first character: " + JSON.stringify([a, b.slice(0, 4)]));
  [a, b] = around(ipre, point(ib, "i-in"));
  assert.ok(a.endsWith("beta = ") && b.startsWith("2"), JSON.stringify([a.slice(-7), b.slice(0, 1)]));
  unpaintChanges(El(ib));
});

// ── 2. the block that begins at the offset wins the tie ────────────────────────────────────────────

test("Rendered deletion points where one mapped block ends exactly as the next begins: a heading and the paragraph under it (with and without a blank line), a paragraph and the list under it, the fixture's title and first paragraph — the point opens the block that begins there, never closes the one that ends there", () => {
  const cases: [string, string, string, string][] = [
    // source, the deletion's offset (the start of this text), the block the point must be in, the text after it
    ["## Findings\nThe api session cut p95.\n", "The api", "P", "The api session cut p95."],
    ["## Findings\n\nThe api session cut p95.\n", "The api", "P", "The api session cut p95."],
    ["Key points:\n- one\n- two\n", "- one", "UL", "one"],
    [fs.readFileSync(FIX("report.md"), "utf8"), "The `api` session", "P", "The "],
  ];
  for (const [source, start, tag, after] of cases) {
    const box = buildRendered(source);
    const before = serialize(box);
    const offset = at(source, start);
    // the shape under test: a block ends at the offset and another begins there (marked's heading raw swallows its
    // trailing newlines, so the pair is adjacent even across a blank line)
    const blocks = marked.lexer(source);
    let p = 0; const ends: number[] = [], starts: number[] = [];
    for (const t of blocks) { starts.push(p); p += t.raw.length; ends.push(p); }
    assert.ok(ends.includes(offset) && starts.includes(offset), JSON.stringify(start) + " is a block boundary: " + JSON.stringify({ starts, ends, offset }));
    const r = paintChangesRendered(El(box), source, [del("b", offset, "First ")], stylesFor);
    assert.deepEqual(r, { painted: ["b"], unpainted: [] }, JSON.stringify(start));
    const pt = point(box, "b");
    const blk = blockOf(box, pt);
    assert.equal(blk.tagName, tag, JSON.stringify(start) + ": the block that begins at the offset, not the one that ends there");
    const [pre, post] = around(blk, pt);
    assert.equal(pre.trim(), "", JSON.stringify(start) + ": nothing of the block before the point (marked's own newline between a list and its first item aside)");
    assert.ok(post.startsWith(after), JSON.stringify(start) + ": " + JSON.stringify(post.slice(0, 24)));
    unpaintChanges(El(box));
    assert.equal(serialize(box), before);
  }
});

// ── 3. a label with no visible character keeps its width in Rendered ───────────────────────────────

test("Rendered deletion points whose label has no visible character (a removed space, tab, or two spaces; a substitution of whitespace) carry the Raw rows' white-space so the label keeps its width; a label with a visible character, or a removed line ending's pilcrow, takes the block's; the Raw twin needs none", () => {
  const source = "We recommend shipping the cache. Risks remain in the fallback path, and the runbook covers them.\n";
  const box = buildRendered(source);
  const before = serialize(box);
  const changes: ChangePaint[] = [
    del("w-space", at(source, "Risks"), " "),                 // a doubled space collapsed: the removed one sat beside the one that stays
    del("w-tab", at(source, "fallback"), "\t", "api"),        // no colour for api: the white-space is the whole style
    del("w-two", at(source, "in the"), "  "),
    { id: "w-sub", kind: "sub", curFrom: at(source, "runbook"), curTo: at(source, "runbook") + 7, oldText: " ", author: "web", newText: "runbook" },
    del("v-word", at(source, "shipping"), "quickly "),        // visible: the block's white-space folds it
    del("v-line", at(source, "the cache"), "\n"),             // a removed line ending is a pilcrow, visible
    del("v-mixed", at(source, "covers"), " \n\t"),            // spaces around a pilcrow: the glyph makes it visible
  ];
  const r = paintChangesRendered(El(box), source, changes, stylesFor);
  assert.deepEqual(r, { painted: changes.map((c) => c.id), unpainted: [] });
  const style = (id: string) => point(box, id).getAttribute("style");
  const label = (id: string) => point(box, id).getAttribute("data-fc-text");
  // the label is still the old text as deletionLabel gives it — the width comes from the white-space, not a glyph
  assert.equal(label("w-space"), " "); assert.equal(label("w-tab"), "\t"); assert.equal(label("w-two"), "  "); assert.equal(label("w-sub"), " ");
  assert.equal(style("w-space"), "--fc-author: rgb(10, 20, 30); white-space: pre-wrap;", "the author's colour, then the rows' white-space");
  assert.equal(style("w-tab"), "white-space: pre-wrap;", "no colour asked for: the white-space alone");
  assert.equal(style("w-two"), "--fc-author: rgb(10, 20, 30); white-space: pre-wrap;");
  assert.equal(style("w-sub"), "--fc-author: rgb(10, 20, 30); white-space: pre-wrap;", "a substitution's struck point too");
  const subTint = withClass(box, "fc-ins").find((m) => m.getAttribute("data-id") === "w-sub")!;
  assert.equal(subTint.getAttribute("style"), "--fc-author: rgb(10, 20, 30);", "…but not its tint, which holds visible text");
  for (const id of ["v-word", "v-line", "v-mixed"]) assert.equal(style(id), "--fc-author: rgb(10, 20, 30);", id + ": a visible label takes the block's white-space");
  assert.equal(label("v-line"), PILCROW); assert.equal(label("v-mixed"), " " + PILCROW + "\t");
  // the points sit where they would with any label: the whitespace-only ones before the word the offset is on
  for (const [id, word] of [["w-space", "Risks"], ["w-tab", "fallback"], ["w-two", "in the"]] as const) {
    const [, post] = around(blockOf(box, point(box, id)), point(box, id));
    assert.ok(post.startsWith(word), id + ": " + JSON.stringify(post.slice(0, 10)));
  }
  unpaintChanges(El(box));
  assert.equal(serialize(box), before);
  // Raw: the rows are pre-wrap already (styles.css .fileview-wrap .fv-ct), so its point carries only the caller's styles
  const code = buildRaw(source);
  const raw = paintChangesRaw(El(code), source, changes.slice(0, 4), stylesFor) as unknown as FakeElement[];
  const rawPoints = raw.filter((m) => m.getAttribute("class") === "fc-del");
  assert.equal(rawPoints.length, 4);
  for (const m of rawPoints) {
    assert.equal(m.getAttribute("data-fc-text"), deletionLabel(changes.find((c) => c.id === m.getAttribute("data-id"))!.oldText));
    assert.equal(m.getAttribute("style"), m.getAttribute("data-author") === "web" ? "--fc-author: rgb(10, 20, 30);" : null, m.getAttribute("data-id") + ": Raw adds no white-space");
  }
});

// ── the stand-in's nodes inspect as their own projection (ui/test-dom-shim.ts) ────────────────────
test("a stand-in node enumerates its primitives alone, and a dump of one names neither parentNode nor childNodes", () => {
  const doc = new FakeDocument();
  const root = doc.createElement("div"), p = doc.createElement("p"), t = doc.createTextNode("alpha");
  root.appendChild(p); p.appendChild(t); p.setAttribute("class", "row");
  for (const n of [root, p, t]) {
    for (const k of Object.keys(n)) assert.ok(staysEnumerable((n as any)[k]), k + " is enumerable and holds a " + typeof (n as any)[k]);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "a dump stays on the node: " + dump);
  }
  assert.ok(p.parentNode === root && root.childNodes[0] === p && t.parentNode === p, "the edges still hold the tree");
  assert.equal(root.textContent, "alpha"); assert.equal(p.getAttribute("class"), "row");
});
