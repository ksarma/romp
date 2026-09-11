// The Rendered fallback's occurrence when the quote carries markup of its own (anchor-map.ts paintRendered;
// plans/file-review.md: a comment inside a refused block "falls back to a whitespace-tolerant match of its
// quote stripped of inline markup"). The Slice 2 ordinal (anchor-map-change-marks.test.ts, part 2) picks the
// range's occurrence among the block's repeats of a token, and refuses when the rendering shows the text a
// different number of times than the source holds it. Counted over the RAW slice, that refused every quote
// whose markup wrapped it: a comment left from Raw on `` `GET /notes` `` (backticks included) in a table
// whose other cell says "GET /notes lists notes" occurs once in the source and twice, stripped, in the
// rendering — so a highlight Slice 1 painted on the right cell was dropped and its card fell to Reveal.
// The count is now taken over the block's source stripped the same way, with each surviving character
// mapped back to its origin (stripMarkupMapped), and the range's occurrence is the one whose characters
// map inside it. Driven over the viewer's two DOM shapes the way anchor-map.test.ts drives them; fixtures
// are synthetic (the notes-api world).
// Parts 3 and 4 (Slice 5 of plans/markdown-viewer.md, items 2 and 8) cover the two holes whose text the rendering
// shows differently from prose: a code block's lines are shown raw, so the strip that serves prose broke the needle
// (`total = a * b * 2` lost its asterisks to the emphasis rule and painted in Raw alone; `# a comment` lost its `# `
// and painted two characters in), and a table row's `|` delimiters are shown nowhere, so a quote across two cells,
// `cell one | cell two`, matched nothing. Inside a code hole the fallback reads the quote and the scope's source raw
// (fence lines dropped); inside a table hole it reads each unescaped `|` as a blank on both sides, with a blank in the
// hay between two adjacent table parts; the stored quote stays the exact source slice (the owner's ruling 5: the
// plan's "strip cell delimiters" is a paint-time rule). The browser leg anchor-map-code-table-paint-browser.test.ts
// drives both through the real viewer and panel, a Raw save and a fresh open.
import { test } from "node:test";
import assert from "node:assert/strict";
import { inspect } from "node:util";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";   // the one markdown configuration, applied here as the viewer applies it
import {
  mapRawSelection, paintRendered, paintChangesRendered, unpaintChanges, stripMarkupMapped,
  type ChangePaint, type SelLike,
} from "./anchor-map";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

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
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
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
function serialize(n: FakeNode): string {
  if (n.nodeType === 3) return "#" + JSON.stringify((n as FakeText).data);
  const e = n as FakeElement;
  const attrs = [...e.attrs.entries()].sort().map(([k, v]) => ` ${k}=${JSON.stringify(v)}`).join("");
  return `<${e.tagName}${attrs}>` + e.childNodes.map(serialize).join("") + `</${e.tagName}>`;
}
const docOrder = (root: FakeNode): FakeNode[] => { const out: FakeNode[] = []; const visit = (n: FakeNode) => { out.push(n); n.childNodes.forEach(visit); }; visit(root); return out; };
const elements = (root: FakeNode): FakeElement[] => docOrder(root).filter((n) => n.nodeType === 1) as FakeElement[];
const withClass = (root: FakeNode, cls: string): FakeElement[] => elements(root).filter((e) => (e.getAttribute("class") || "").split(" ").includes(cls));
/** The nearest ancestor with `tag`, and its index among same-tag siblings (the cell's column). */
function cellOf(n: FakeNode, tag: string): { el: FakeElement; index: number } {
  let p: FakeNode | null = n;
  while (p && !(p.nodeType === 1 && (p as FakeElement).tagName === tag)) p = p.parentNode;
  assert.ok(p, "inside a " + tag);
  const el = p as FakeElement;
  const sibs = (el.parentNode as FakeElement).childNodes.filter((c) => c.nodeType === 1 && (c as FakeElement).tagName === tag);
  return { el, index: sibs.indexOf(el) };
}
const sel = (a: FakeNode, ao: number, f: FakeNode, fo: number): SelLike =>
  ({ anchorNode: a as unknown as Node, anchorOffset: ao, focusNode: f as unknown as Node, focusOffset: fo, isCollapsed: a === f && ao === fo });
const at = (source: string, s: string, from = 0): number => { const i = source.indexOf(s, from); assert.ok(i >= 0, "source has " + JSON.stringify(s)); return i; };
const rangeOf = (source: string, s: string, from = 0) => { const start = at(source, s, from); return { start, end: start + s.length }; };
const noStyles = (): Record<string, string> => ({});
/** A comment highlight over `range`: the marks, their joined text, and the table cell they sit in. */
function highlight(source: string, range: { start: number; end: number }, tag = "TD") {
  const box = buildRendered(source);
  const marks = paintRendered(El(box), source, range, "fc-hl", { act: "fcopen", id: "k1" }) as unknown as FakeElement[] | null;
  return { box, marks, text: marks ? marks.map((m) => m.textContent).join("") : null, cell: marks && marks.length ? cellOf(marks[0], tag) : null };
}

// ── 1. the mapped strip ────────────────────────────────────────────────────────────────────────────

test("stripMarkupMapped: the text is the flat strip's, byte for byte, and every surviving character maps to its own index in the source, in order", () => {
  const cases: [string, string][] = [
    ["> quoted *text* here", "quoted text here"],
    ["- [x] a task **done**", "a task done"],
    ["1) numbered _item_", "numbered item"],
    ["## Heading with `code` ##", "Heading with code"],
    ["```python", ""],
    ["![alt](img.png) and [label](http://x) and [ref][r]", " and label and ref"],
    ["<https://example.com/x> and __also__ and ~~del~~", "https://example.com/x and also and del"],
    ["\\*escaped\\* and \\#", "\\escaped\\ and #"],
    ["trailing two  ", "trailing two"],
    ["trailing backslash\\", "trailing backslash"],
    ["| `GET /notes` | GET /notes lists notes |", "| GET /notes | GET /notes lists notes |"],
    ["| **cache** | cache |", "| cache | cache |"],
    ["a * b * c", "a * b * c"],   // no emphasis: the asterisks are not flanking (they were read as a pair around " b " before)
    ["*em* and a * b", "em and a * b"],
    ["`__init__` and `f(*args, **kwargs)` and `a*b*c`", "__init__ and f(*args, **kwargs) and a*b*c"],   // a code span's content is the rendering's
    ["`` a ` b `` and **`x`**", " a ` b  and x"],
    ["\\`not code\\` *em*", "`not code` em"],   // an escaped backtick opens no span and is the backtick it shows (before: the backticks went and the backslashes stayed)
    ["-\tTab after the marker", "Tab after the marker"],
    ["# T\n\n| a | b |\n|---|---|\n| `x` | x |\n```\nfence\n```\n", "T\n\n| a | b |\n|---|---|\n| x | x |\n\nfence\n\n"],
  ];
  for (const [s, want] of cases) {
    const m = stripMarkupMapped(s);
    assert.equal(m.text, want, JSON.stringify(s));
    assert.equal(m.map.length, m.text.length, JSON.stringify(s) + ": one origin per character");
    for (let i = 0; i < m.text.length; i++) {
      assert.equal(s[m.map[i]], m.text[i], JSON.stringify(s) + ": character " + i + " maps to itself");
      if (i > 0) assert.ok(m.map[i] > m.map[i - 1], JSON.stringify(s) + ": the map is strictly increasing at " + i);
    }
  }
  // the map tells the two "GET /notes" apart: the first lives inside the backticks, the second is the plain one
  const row = "| `GET /notes` | GET /notes lists notes |";
  const m = stripMarkupMapped(row);
  const a = m.text.indexOf("GET /notes"), b = m.text.indexOf("GET /notes", a + 1);
  assert.equal(m.map[a], row.indexOf("`") + 1);
  assert.equal(m.map[b], row.lastIndexOf("GET /notes"));
});

// ── 2. the finding: a marked-up quote whose plain text recurs in the block ─────────────────────────

const ROUTES = "# Routes\n\n| Route | Note |\n|-------|------|\n| `GET /notes` | GET /notes lists notes |\n\nDone.\n";
const CACHE = "# Cache\n\n| Term | Note |\n|---|---|\n| **cache** | the cache is shared |\n";
const ROUTES_REV = "# Routes\n\n| Note | Route |\n|---|---|\n| GET /notes lists notes | `GET /notes` |\n";

test("Rendered fallback: a comment on a code-span or bold cell whose plain text recurs in the table paints the commented cell — the first when it comes first, the second when it comes second", () => {
  // the finding's scenario A: the quote is `GET /notes`, backticks included; the plain text recurs after it
  let h = highlight(ROUTES, rangeOf(ROUTES, "`GET /notes`"));
  assert.ok(h.marks && h.marks.length, "painted (filereview-s1 painted this; the raw-slice count refused it)");
  assert.equal(h.text, "GET /notes");
  assert.equal(h.cell!.index, 0, "the commented cell, not the plain recurrence");
  assert.equal(h.cell!.el.textContent, "GET /notes");
  // scenario B: a bold word, plain elsewhere in the row
  h = highlight(CACHE, rangeOf(CACHE, "**cache**"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "cache");
  assert.equal(h.cell!.index, 0);
  // the plain text comes FIRST: the ordinal lands on the second cell (filereview-s1 painted the first, the wrong one)
  h = highlight(ROUTES_REV, rangeOf(ROUTES_REV, "`GET /notes`"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "GET /notes");
  assert.equal(h.cell!.index, 1, "the second cell holds the commented code span");
  // and a comment on the PLAIN cell of the same row still paints the plain cell
  h = highlight(ROUTES_REV, rangeOf(ROUTES_REV, "GET /notes lists notes"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.cell!.index, 0);
  h = highlight(ROUTES, rangeOf(ROUTES, "GET /notes lists notes"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.cell!.index, 1);
});

test("Rendered fallback: markup INSIDE the quote (a code span mid-phrase, a bold word before plain text) is stripped on both sides, so the ordinal still finds the commented cell", () => {
  const mid = "# Routes\n\n| a | b |\n|---|---|\n| the `GET /notes` route | the GET /notes route |\n";
  let h = highlight(mid, rangeOf(mid, "the `GET /notes` route"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "the GET /notes route");
  assert.equal(h.cell!.index, 0);
  const midRev = "# Routes\n\n| a | b |\n|---|---|\n| the GET /notes route | the `GET /notes` route |\n";
  h = highlight(midRev, rangeOf(midRev, "the `GET /notes` route"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.cell!.index, 1);
  const bold = "# Routes\n\n| a | b |\n|---|---|\n| GET /notes | **GET** /notes |\n";
  h = highlight(bold, rangeOf(bold, "**GET** /notes"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "GET /notes");
  assert.equal(h.cell!.index, 1);
});

test("Rendered fallback: the scenario is reachable — a Raw selection over the backticked cell mints the range with the backticks, and that range paints in Rendered", () => {
  const code = buildRaw(ROUTES);
  const rowIndex = ROUTES.split("\n").findIndex((ln) => ln.includes("`GET /notes`"));
  const row = code.childNodes[rowIndex] as FakeElement;
  const t = (row.childNodes[0] as FakeElement).childNodes[0] as FakeText;
  const col = t.data.indexOf("`GET /notes`");
  const r = mapRawSelection(sel(t, col, t, col + "`GET /notes`".length), El(code), ROUTES);
  assert.equal(r.ok, true, "expected ok: " + JSON.stringify(r));
  if (!r.ok) return;
  assert.equal(r.quote, "`GET /notes`", "the backticks are part of the quote a Raw selection stores");
  const h = highlight(ROUTES, r.range);
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.cell!.index, 0);
});

test("Rendered fallback: a change whose new text is the marked-up cell paints, in the changed cell, and unpaint restores the DOM", () => {
  for (const [source, cell] of [[ROUTES, 0], [ROUTES_REV, 1]] as [string, number][]) {
    const box = buildRendered(source);
    const before = serialize(box);
    const from = at(source, "`GET /notes`");
    const change: ChangePaint = { id: "c", kind: "ins", curFrom: from, curTo: from + "`GET /notes`".length, oldText: "", author: "web", newText: "`GET /notes`" };
    const res = paintChangesRendered(El(box), source, [change], noStyles);
    assert.deepEqual(res, { painted: ["c"], unpainted: [] }, "the change is painted, not left to Reveal");
    const marks = withClass(box, "fc-ins");
    assert.equal(marks.length, 1);
    assert.equal(marks[0].textContent, "GET /notes");
    assert.equal(cellOf(marks[0], "TD").index, cell);
    unpaintChanges(El(box));
    assert.equal(serialize(box), before);
  }
});

test("Rendered fallback: the count guard still holds for a marked-up quote — an HTML block whose attribute repeats the text paints nothing; a code-span quote with no plain recurrence paints as before", () => {
  // the rendering shows one "x" (inside the literal "**x**"); the stripped source holds two (the attribute's and the bold's)
  const html = "# Notes\n\n<div title=\"x\">**x**</div>\n";
  const box = buildRendered(html);
  const before = serialize(box);
  assert.equal(paintRendered(El(box), html, rangeOf(html, "**x**"), "fc-hl"), null, "the counts disagree, so nothing is painted");
  assert.equal(serialize(box), before);
  // the control: the quote's plain text occurs once in the rendering and once, stripped, in the source
  const one = "# Routes\n\n| Route | Note |\n|---|---|\n| `GET /notes` | lists notes |\n";
  const h = highlight(one, rangeOf(one, "`GET /notes`"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "GET /notes");
  assert.equal(h.cell!.index, 0);
});

// ── 3. Slice 5, item 2: a quote inside a code block is read raw ────────────────────────────────────

/** The rendered text before `n` in document order (the code's earlier lines, for a repeated line's ordinal). */
function textBefore(root: FakeNode, n: FakeNode): string {
  let out = "";
  for (const x of docOrder(root)) { if (x === n) break; if (x.nodeType === 3) out += (x as FakeText).data; }
  return out;
}
const norm = (s: string): string => s.replace(/\s+/g, " ").trim();
const TOTALS = "# Totals\n\nIntro paragraph with several words in it.\n\n```python\ntotal = a * b * 2\nname_ = under_score  # trailing comment\n```\n\nAfter paragraph.\n";
const FENCED = "# Handler notes\n\nBefore paragraph.\n\n```python\n# a comment\ndef f(x):\n    return x + 1  # trailing\n\nvalue = f(2)\n```\n\nAfter paragraph.\n";

test("Rendered fallback, a code hole: `total = a * b * 2` paints inside the pre with the marks' text the raw line (the emphasis rule stripped its asterisks and nothing matched); `name_ = under_score` still paints; `# a comment` paints from its `#`; the whole fence, fence lines included, paints from the `#` too", () => {
  let h = highlight(TOTALS, rangeOf(TOTALS, "total = a * b * 2"), "PRE");
  assert.ok(h.marks && h.marks.length, "painted (was null: the needle read `total = a  b  2`)");
  assert.equal(norm(h.text!), "total = a * b * 2");
  assert.equal(h.cell!.el.tagName, "PRE");
  // the neighbouring line painted before too (the `_` rule's word-boundary guard spared it) and still does
  h = highlight(TOTALS, rangeOf(TOTALS, "name_ = under_score  # trailing comment"), "PRE");
  assert.ok(h.marks && h.marks.length);
  assert.equal(norm(h.text!), "name_ = under_score # trailing comment");
  // a comment line: the heading rule took its `# ` and the mark began at the `a`
  h = highlight(FENCED, rangeOf(FENCED, "# a comment"), "PRE");
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "# a comment", "the mark begins at the `#`, not two characters in");
  // the whole block, fence lines included: the fences render nothing and drop from the needle; the marks cover the code from its `#`
  const whole = { start: FENCED.indexOf("```python"), end: FENCED.indexOf("```\n\nAfter") + 3 };
  h = highlight(FENCED, whole, "PRE");
  assert.ok(h.marks && h.marks.length, "the whole block paints");
  assert.equal(norm(h.text!), norm("# a comment\ndef f(x):\n    return x + 1  # trailing\n\nvalue = f(2)"));
});

test("Rendered fallback, a code hole: a line repeated in the fence paints the range's own line by ordinal, the count taken raw on both sides", () => {
  const src = "```\ntotal = a * b * 2\ntotal = a * b * 2\n```\n";
  const second = src.lastIndexOf("total = a * b * 2"), first = src.indexOf("total = a * b * 2");
  let h = highlight(src, { start: second, end: second + "total = a * b * 2".length }, "PRE");
  assert.ok(h.marks && h.marks.length === 1, "one mark (was null)");
  assert.equal(textBefore(h.box, h.marks![0]), "total = a * b * 2\n", "the second line");
  h = highlight(src, { start: first, end: first + "total = a * b * 2".length }, "PRE");
  assert.ok(h.marks && h.marks.length === 1);
  assert.equal(textBefore(h.box, h.marks![0]), "", "the first line");
});

test("Rendered fallback, a code hole: an indented code block, a fence in a list item and a fence in a blockquote read raw too; a quoted fence's lines shed the quote's markers, so a two-line quote there still paints", () => {
  const indented = "Intro paragraph.\n\n    total = a * b * 2\n    next = total * 2\n\nAfter paragraph.\n";
  let h = highlight(indented, rangeOf(indented, "total = a * b * 2"), "PRE");
  assert.ok(h.marks && h.marks.length, "indented code (was null)");
  assert.equal(norm(h.text!), "total = a * b * 2");
  const two = { start: indented.indexOf("total ="), end: indented.indexOf("next = total * 2") + "next = total * 2".length };
  h = highlight(indented, two, "PRE");   // the range holds the second line's indentation: white space the match ignores
  assert.ok(h.marks && h.marks.length, "two indented lines (was null)");
  assert.equal(norm(h.text!), "total = a * b * 2 next = total * 2");
  const listed = "- Item text with `make` in it.\n\n  ```\n  x * y\n  ```\n\n- Second item.\n";
  h = highlight(listed, rangeOf(listed, "x * y"), "PRE");
  assert.ok(h.marks && h.marks.length, "a fence in a list item (was null)");
  assert.equal(norm(h.text!), "x * y");
  assert.equal(cellOf(h.marks![0], "LI").index, 0);
  const quoted = "> Quoted intro.\n>\n> ```\n> a = 1\n> b = 2\n> ```\n";
  const span = { start: quoted.indexOf("a = 1"), end: quoted.indexOf("b = 2") + "b = 2".length };
  h = highlight(quoted, span, "PRE");   // the raw slice is "a = 1\n> b = 2": the second line's marker is the quote's, not the code's
  assert.ok(h.marks && h.marks.length, "a two-line quote in a quoted fence paints (the strip took the markers before; the markers still come off)");
  assert.equal(norm(h.text!), "a = 1 b = 2");
  h = highlight(quoted, rangeOf(quoted, "b = 2"), "PRE");
  assert.ok(h.marks && h.marks.length);
  assert.equal(norm(h.text!), "b = 2");
});

test("Rendered fallback, a code hole nested in a list item: the item's prose keeps the strip while the code reads raw, so a code token the prose repeats in a link's label and URL counts the same on both sides and the code's copy paints (a control: green before too; the raw source alone would count the URL's copy and paint nothing)", () => {
  const src = "- See [make](https://example.invalid/make) first.\n\n      make\n\n- Second item.\n";
  const h = highlight(src, rangeOf(src, "make", src.indexOf("      make")), "PRE");
  assert.ok(h.marks && h.marks.length, "painted");
  assert.equal(h.text, "make");
  assert.equal(h.cell!.el.tagName, "PRE");
});

// ── 4. Slice 5, item 8: a quote across two cells reads its pipe as a blank ──────────────────────────

const CELLS = "# Table\n\n| Col A | Col B |\n|-------|-------|\n| cell one | cell two |\n| cell three | cell four |\n\nAfter paragraph.\n";
/** The marks with text of their own (a blank between two cells is a trim candidate in a browser, never the passage). */
const textMarks = (marks: FakeElement[]): FakeElement[] => marks.filter((m) => m.textContent.trim() !== "");

test("Rendered fallback, a table hole: `cell one | cell two` paints one mark in each of the row's two cells (was null: the needle kept the pipe); one cell still paints one; a quote spanning the delimiter row paints nothing; `\\|` stays the cell's own pipe", () => {
  let h = highlight(CELLS, rangeOf(CELLS, "cell one | cell two"));
  assert.ok(h.marks && h.marks.length, "painted");
  const tm = textMarks(h.marks!);
  assert.deepEqual(tm.map((m) => m.textContent), ["cell one", "cell two"]);
  assert.deepEqual(tm.map((m) => cellOf(m, "TD").index), [0, 1]);
  assert.equal(cellOf(tm[0], "TR").el, cellOf(tm[1], "TR").el, "the same row");
  assert.equal(h.marks!.length, 2, "the blank between the two cells is skipped, not wrapped (skipBlockWs: collapsible white space between two table cells)");
  // one cell: as before
  h = highlight(CELLS, rangeOf(CELLS, "cell one"));
  assert.ok(h.marks && textMarks(h.marks!).length === 1);
  assert.equal(h.cell!.index, 0);
  // across the delimiter row: its dashes stand in no rendered text
  const acrossDelim = { start: CELLS.indexOf("Col B"), end: CELLS.indexOf("cell one") + "cell one".length };
  const box = buildRendered(CELLS);
  const before = serialize(box);
  assert.equal(paintRendered(El(box), CELLS, acrossDelim, "fc-hl"), null, "the quote spans the delimiter row: nothing painted, the card keeps Reveal");
  assert.equal(serialize(box), before);
  // an escaped pipe is the cell's own character
  const esc = "| a \\| b | c |\n|---|---|\n| d | e |\n";
  h = highlight(esc, rangeOf(esc, "a \\| b"), "TH");
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "a | b");
  assert.equal(h.cell!.index, 0);
});

test("Rendered fallback, a table hole: cells with no whitespace between them in the DOM are kept apart by the hay's blank; a quote across two rows paints both cells; a repeated row paints the range's own by ordinal; a quoted table reads the same", () => {
  // a DOM with the newlines between tags gone (a minifying step): the cells' text nodes are adjacent
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, (marked.parse(CELLS) as string).replace(/>\n</g, "><"))) box.appendChild(n);
  const marks = paintRendered(El(box), CELLS, rangeOf(CELLS, "cell one | cell two"), "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(marks && marks.length, "painted over adjacent cells");
  assert.deepEqual(textMarks(marks!).map((m) => m.textContent), ["cell one", "cell two"]);
  // two rows
  let h = highlight(CELLS, rangeOf(CELLS, "cell two |\n| cell three"));
  assert.ok(h.marks && h.marks.length, "two rows paint");
  const tm = textMarks(h.marks!);
  assert.deepEqual(tm.map((m) => m.textContent), ["cell two", "cell three"]);
  assert.notEqual(cellOf(tm[0], "TR").el, cellOf(tm[1], "TR").el, "two rows");
  // a repeated row: the ordinal picks the range's
  const rep = "| a | b |\n|---|---|\n| x | y |\n| x | y |\n";
  const second = rep.lastIndexOf("x | y"), first = rep.indexOf("x | y");
  h = highlight(rep, { start: second, end: second + "x | y".length });
  assert.ok(h.marks && h.marks.length, "the repeated row paints");
  assert.equal(cellOf(textMarks(h.marks!)[0], "TR").index, 1, "the second body row");
  h = highlight(rep, { start: first, end: first + "x | y".length });
  assert.ok(h.marks && h.marks.length);
  assert.equal(cellOf(textMarks(h.marks!)[0], "TR").index, 0, "the first body row");
  // a table in a blockquote: the quote's markers are the container's
  const quoted = "> | a | b |\n> |---|---|\n> | c | d |\n";
  h = highlight(quoted, rangeOf(quoted, "c | d"));
  assert.ok(h.marks && h.marks.length, "a quoted table's two cells paint");
  assert.deepEqual(textMarks(h.marks!).map((m) => m.textContent), ["c", "d"]);
});

// ── the Slice 5 review, round 1: a code span's content in a cell, and a quote begun inside a fence line ──

test("Rendered fallback, a table hole: a code span's content is read as the rendering shows it, so `__init__`, `f(*args, **kwargs)`, `_private_` and `a*b*c` in cells paint whole (before: the emphasis rules ran inside the backticks and the needle read `init`, `f(args, *kwargs)`, `private` and `abc`: a partial mark over `init`, or none, the card offering Reveal); a plain cell `x * y * z` paints too (before: its asterisks read as a pair); a bold cell and a code-span cell whose plain text recurs still paint their own cell", () => {
  const NAMES = "# Names\n\n| Name | Meaning |\n|------|---------|\n| `__init__` | the constructor |\n| `f(*args, **kwargs)` | a call |\n| `_private_` | hidden |\n| `a*b*c` | product |\n| x * y * z | stars |\n| **bold** `__x__` | both |\n| `GET /notes` | GET /notes lists notes |\n\nAfter.\n";
  for (const [quote, shown] of [["`__init__`", "__init__"], ["`f(*args, **kwargs)`", "f(*args, **kwargs)"], ["`_private_`", "_private_"], ["`a*b*c`", "a*b*c"], ["x * y * z", "x * y * z"], ["**bold** `__x__`", "bold __x__"]] as const) {
    const h = highlight(NAMES, rangeOf(NAMES, quote));
    assert.ok(h.marks && h.marks.length, quote + ": painted (was " + (quote === "`__init__`" || quote === "`_private_`" ? "a partial mark" : "null") + ")");
    assert.equal(norm(h.text!), shown, quote + ": the whole cell's text under the marks");
    assert.equal(h.cell!.index, 0, quote + ": the first cell");
  }
  // the ordinal over a recurring plain text still finds the commented cell (the control of part 2)
  const h = highlight(NAMES, rangeOf(NAMES, "`GET /notes`"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "GET /notes");
  assert.equal(h.cell!.index, 0);
});

test("Rendered fallback, a code hole: a quote begun inside the opening fence's info string (a Raw drag from the `p` of ```python, or from its second backtick, to the end of the first code line) paints the first code line (before: the sliced first line, `python`, was no fence by its text and stayed in the needle, which the code never holds: nothing painted, the card offering Reveal); one ending inside the closing fence's backticks paints the last line; a code line that itself opens with three backticks inside a four-backtick fence stays in the needle and paints (before: dropped as a fence line on the source side while the rendering shows it)", () => {
  const fence = TOTALS.indexOf("```python"), line1End = TOTALS.indexOf("total = a * b * 2") + "total = a * b * 2".length;
  let h = highlight(TOTALS, { start: fence + 3, end: line1End }, "PRE");
  assert.ok(h.marks && h.marks.length, "from the `p` of the info string (was null)");
  assert.equal(norm(h.text!), "total = a * b * 2");
  h = highlight(TOTALS, { start: fence + 1, end: line1End }, "PRE");
  assert.ok(h.marks && h.marks.length, "from the second backtick (was null)");
  assert.equal(norm(h.text!), "total = a * b * 2");
  const close = TOTALS.indexOf("```\n\nAfter");
  h = highlight(TOTALS, { start: TOTALS.indexOf("name_ ="), end: close + 2 }, "PRE");
  assert.ok(h.marks && h.marks.length, "to inside the closing fence (was null)");
  assert.equal(norm(h.text!), "name_ = under_score # trailing comment");
  const FOUR = "Intro paragraph.\n\n````\n```\ninner fence line\n```\n````\n\nAfter paragraph.\n";
  h = highlight(FOUR, rangeOf(FOUR, "```\ninner fence line"), "PRE");
  assert.ok(h.marks && h.marks.length);
  assert.equal(norm(h.text!), "``` inner fence line", "the three-backtick code line is in the needle (before: `inner fence line` alone)");
  // the whole block, fence lines included, still paints from its first character (part 3's pin, kept)
  const whole = { start: FENCED.indexOf("```python"), end: FENCED.indexOf("```\n\nAfter") + 3 };
  h = highlight(FENCED, whole, "PRE");
  assert.ok(h.marks && h.marks.length);
  assert.equal(norm(h.text!), norm("# a comment\ndef f(x):\n    return x + 1  # trailing\n\nvalue = f(2)"));
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
