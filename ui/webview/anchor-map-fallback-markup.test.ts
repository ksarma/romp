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
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import {
  mapRawSelection, paintRendered, paintChangesRendered, unpaintChanges, stripMarkupMapped,
  type ChangePaint, type SelLike,
} from "./anchor-map";

// ── the viewer's marked configuration (file-view.ts; pinned by anchor-map.test.ts) ────────────────
marked.setOptions({ gfm: true, breaks: false });
marked.use({
  tokenizer: {
    del(src: string) {
      const m = /^~~(?=\S)([\s\S]*?\S)~~/.exec(src);
      if (!m) return undefined;
      return { type: "del", raw: m[0], text: m[1], tokens: (this as { lexer: { inlineTokens(s: string): unknown[] } }).lexer.inlineTokens(m[1]) };
    },
  },
} as Parameters<typeof marked.use>[0]);

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser ─────
class FakeNode {
  nodeType = 0;
  parentNode: FakeNode | null = null;
  childNodes: FakeNode[] = [];
  constructor(public ownerDocument: FakeDocument) {}
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
  constructor(doc: FakeDocument, public tagName: string) { super(doc); }
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
    ["a * b * c", "a  b  c"],
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
