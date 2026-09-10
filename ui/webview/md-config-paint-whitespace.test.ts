// The paint's neighbour reads cost a paragraph its inline children once, not once per whitespace node. skipBlockWs (anchor-map.ts)
// reads the neighbours of a whitespace-only text node for its one DOM-side skip below the root (a block box on both sides, or a
// block-box parent's edge; every other blank is painted and the browser's layout decides, trimCollapsedMarks, which a stand-in
// with no layout leaves alone), stepping with sibling, and wrapRuns joins adjacent units by asking whether one follows the other
// (follows); both step over the DOM's own sibling pointers when the node offers them, constant time a step, and index the
// parent's child list only for a stand-in without them. Round 8 of the Slice 4 review indexed every time: each space between two
// inline elements of a paragraph is a whitespace-only node the rule reads both neighbours of, and each read scanned the
// paragraph's child list from the start, so one mark across a paragraph of N links cost N squared child reads (over 3,000 links,
// 850 ms in Chromium against 27 ms before the rule; md-config-paint-whitespace-browser.test.ts times the same in equal-work legs
// over the real bundle). Here the stand-in offers the pointers and each element counts the indexed reads of its child list
// through a Proxy the stand-in's own methods bypass, so the count is the paint's alone; the bound is linear in the children with
// room, and the marks are the ones a stand-in WITHOUT pointers paints (the fallback path, which the other test files' stand-ins
// take). Synthetic prose.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { paintRendered } from "./anchor-map";
import { hideEdges, defineHidden } from "../test-dom-shim";

applyMdConfig();

// ── a DOM stand-in with sibling pointers (optional: a document built without them has neither property) ────────────────────
// Nodes hide their edges at construction (hideEdges, ui/test-dom-shim.ts; the sibling pointers through defineHidden), so a failing
// assertion's dump shows a node's primitives and not the tree (the ratchet in ui/test-dom-shim.test.ts).
class FakeDocument {
  constructor(public readonly pointers: boolean) {}
  createElement(tag: string): FakeElement { return new FakeElement(this, tag.toUpperCase()); }
  createTextNode(s: string): FakeText { return new FakeText(this, s); }
}
class FakeNode {
  nodeType = 0;
  parentNode: FakeElement | null = null;
  previousSibling?: FakeNode | null;
  nextSibling?: FakeNode | null;
  constructor(public ownerDocument: FakeDocument) { hideEdges(this); }
  get childNodes(): FakeNode[] { return []; }
  get textContent(): string { return this.nodeType === 3 ? (this as unknown as FakeText).data : this.childNodes.map((c) => c.textContent).join(""); }
}
class FakeText extends FakeNode {
  nodeType = 3;
  constructor(doc: FakeDocument, public data: string) { super(doc); }
  splitText(offset: number): FakeText {
    const tail = new FakeText(this.ownerDocument, this.data.slice(offset));
    this.data = this.data.slice(0, offset);
    const p = this.parentNode;
    if (p) p.insertBefore(tail, p.kids[p.kids.indexOf(this) + 1] ?? null);
    return tail;
  }
}
class FakeElement extends FakeNode {
  nodeType = 1;
  attrs = new Map<string, string>();
  /** The children, the stand-in's own view: its methods read and write this list and never the counted one. */
  kids: FakeNode[] = [];
  /** Indexed reads of `childNodes` (a `[k]`, not `.length`) by whoever holds the node: the paint. */
  reads = 0;
  private view: FakeNode[] | null = null;
  constructor(doc: FakeDocument, public tagName: string) { super(doc); hideEdges(this); }
  get childNodes(): FakeNode[] {
    if (!this.view) this.view = new Proxy(this.kids, { get: (t, k, r) => { if (typeof k === "string" && k !== "length" && /^\d+$/.test(k)) this.reads++; return Reflect.get(t, k, r); } });
    return this.view;
  }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  private relink(): void {
    for (let i = 0; i < this.kids.length; i++) {
      const c = this.kids[i];
      c.parentNode = this;
      if (this.ownerDocument.pointers) { defineHidden(c, "previousSibling", this.kids[i - 1] ?? null); defineHidden(c, "nextSibling", this.kids[i + 1] ?? null); }
    }
  }
  private detach(n: FakeNode): void {
    const p = n.parentNode;
    if (p) { p.kids.splice(p.kids.indexOf(n), 1); n.parentNode = null; if (p.ownerDocument.pointers) { defineHidden(n, "previousSibling", null); defineHidden(n, "nextSibling", null); } p.relink(); }
  }
  appendChild(n: FakeNode): FakeNode { this.detach(n); this.kids.push(n); this.relink(); return n; }
  insertBefore(n: FakeNode, ref: FakeNode | null): FakeNode {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    this.kids.splice(this.kids.indexOf(ref), 0, n); this.relink(); return n;
  }
  removeChild(n: FakeNode): FakeNode { this.detach(n); return n; }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: "\u00a0" };
const decode = (s: string): string => s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => e[0] === "#" ? String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10)) : (e in NAMED ? NAMED[e] : m));
/** marked's HTML into the stand-in (anchor-map.test.ts's parser, cut to what the scenes here emit: elements with attributes, text,
 *  entities, comments). Two readings a pin over white space rests on: `&nbsp;` decodes to U+00A0, the character the browser
 *  builds and renders (a plain space here would be collapsible white space to skipBlockWs, and a scene meant to hold a rendered
 *  blank would test the wrong character); and an HTML comment is dropped, as DOMPurify drops it before the viewer adopts the
 *  DOM, so the white space on its two sides stands as two adjacent text nodes, the shape the browser holds (round 10). */
function parseHTML(doc: FakeDocument, html: string): FakeNode[] {
  const root = doc.createElement("#fragment");
  const stack: FakeElement[] = [root];
  const top = () => stack[stack.length - 1];
  let i = 0;
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
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], decode(a[2] ?? a[3] ?? a[4] ?? ""));
      top().appendChild(el);
      i += m[0].length;
      if (!m[3] && !VOID.has(m[1].toLowerCase())) stack.push(el);
      continue;
    }
    let e = html.indexOf("<", i);
    if (e < 0) e = html.length;
    top().appendChild(doc.createTextNode(decode(html.slice(i, e))));
    i = e;
  }
  return root.kids.slice();
}
/** The fill's result stood in for (math.ts renderMathPlaceholders): a `.katex` root holding the formula's glyphs where an
 *  inline placeholder stood, so the walk meets the control it meets in the browser (anchor-map-obsidian.test.ts standInFill). */
function standInFill(root: FakeElement): void {
  for (const c of root.kids.slice()) {
    if (c.nodeType !== 1) continue;
    const el = c as FakeElement;
    if (el.getAttribute("class") === "md-math-inline") {
      const katex = el.ownerDocument.createElement("span"); katex.setAttribute("class", "katex");
      katex.appendChild(el.ownerDocument.createTextNode(el.textContent.replace(/[\\^_{}]/g, "")));
      root.insertBefore(katex, el); root.removeChild(el);
    } else standInFill(el);
  }
}
function buildRendered(text: string, pointers: boolean): FakeElement {
  const doc = new FakeDocument(pointers);
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);
  standInFill(box);
  return box;
}
const El = (n: FakeNode) => n as unknown as Element;
const topEl = (box: FakeElement, k: number): FakeElement => box.kids.filter((n) => n.nodeType === 1)[k] as FakeElement;
const textsOf = (marks: FakeElement[]): string => marks.map((m) => m.textContent).join("|");

// ── the scenes ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
const N = 1000;
/** A paragraph of N links separated by spaces: 2N - 1 children under one P, every space a whitespace-only node between two
 *  inline elements (the passage's own text, painted; in the browser the trim unwraps the ones at the wrap points), each read
 *  for both neighbours by skipBlockWs. */
const LINKS = "# Title\n\n" + Array.from({ length: N }, (_, i) => "[w" + i + "](#a" + i + ")").join(" ") + "\n\nAfter para.\n";
/** A paragraph of N inline formulas with text between: 2N + 1 units that are all siblings (the formula roots are units of
 *  their own), so wrapRuns asks follows() of every adjacent pair and wraps the whole paragraph in one mark. */
const MATH = "# Title\n\n" + Array.from({ length: N }, (_, i) => "$x_" + i + "$ then" + i).join(" ") + "\n\nAfter para.\n";
const paraRange = (src: string): { start: number; end: number } => ({ start: src.indexOf("\n\n") + 2, end: src.indexOf("\n\nAfter para.") });
/** The child reads a paint may cost, linear in the paragraph's children: a few passes over them (the block's text nodes for
 *  the endpoints' positions, its units for the highlight, its formulas for the pairing; five to six reads a child measured),
 *  and the pointers make every neighbour and adjacency read free; round 8's index scans cost about the square of the children
 *  over two on top (N = 1,000 links: 2,009,993 reads measured at round 8's source against 9,995 here). */
const LINEAR = (children: number): number => 8 * children + 16;

/** Two shapes the viewer's DOM (DOMPurify's output of marked's HTML) holds and a stand-in must build the same way before a
 *  pin over them here means anything: a `&nbsp;` decodes to U+00A0, the character the browser renders and never collapses,
 *  not the U+0020 the skip readings treat as collapsible; an HTML comment is dropped, as the sanitizer drops it, leaving the
 *  white space on its two sides as two adjacent text nodes. The expected marks are Chromium's over the real bundle (the
 *  Slice 4 review, round 10). */
const NBSP_BETWEEN = "Intro para.\n\n<b>a</b>&nbsp;<i>b</i>\n\nAfter para.\n";
const COMMENT_BETWEEN = "Intro para.\n\n<b>a</b> <!-- c --> <i>b</i>\n\nAfter para.\n";
const fullRange = (src: string): { start: number; end: number } => ({ start: src.indexOf("Intro para."), end: src.indexOf("After para.") + "After para.".length });
const kidsOf = (p: FakeElement): string[] => p.kids.map((c) => c.nodeType === 3 ? "#text(" + JSON.stringify((c as FakeText).data) + ")" : "<" + (c as FakeElement).tagName + ">");

test("the stand-in builds what the sanitizer's DOM holds: `&nbsp;` is a U+00A0 text node (painted between two inline elements as Chromium paints it) and an HTML comment is dropped, its two sides two adjacent whitespace nodes painted as one mark", () => {
  for (const pointers of [true, false]) {
    const nb = buildRendered(NBSP_BETWEEN, pointers);
    assert.deepEqual(kidsOf(topEl(nb, 1)), ["<B>", '#text("\u00a0")', "<I>"], "a no-break space entity decodes to U+00A0, the browser's character, not to a plain space (pointers " + pointers + ")");
    const nbMarks = paintRendered(El(nb), NBSP_BETWEEN, fullRange(NBSP_BETWEEN), "fc-hl") as unknown as FakeElement[];
    assert.equal(textsOf(nbMarks), "Intro para.|a|\u00a0|b|After para.", "the nbsp between two inline elements is painted, and the mark's text is the no-break space (pointers " + pointers + ")");
    const cb = buildRendered(COMMENT_BETWEEN, pointers);
    assert.deepEqual(kidsOf(topEl(cb, 1)), ["<B>", '#text(" ")', '#text(" ")', "<I>"], "the comment is dropped as DOMPurify drops it, the white space on its two sides left as two adjacent text nodes (pointers " + pointers + ")");
    const cbMarks = paintRendered(El(cb), COMMENT_BETWEEN, fullRange(COMMENT_BETWEEN), "fc-hl") as unknown as FakeElement[];
    assert.equal(textsOf(cbMarks), "Intro para.|a|  |b|After para.", "the two adjacent whitespace nodes between two inline elements are one run and one mark of two spaces, as in Chromium (pointers " + pointers + ")");
  }
});

test("the fixtures hold the shapes: a paragraph of 2N - 1 children with N - 1 whitespace-only nodes between inline elements, and a paragraph of 2N + 1 sibling units around N formula roots", () => {
  const lb = buildRendered(LINKS, true);
  const lp = topEl(lb, 1);
  assert.equal(lp.tagName, "P");
  assert.equal(lp.kids.length, 2 * N - 1, "N links and N - 1 spaces");
  assert.equal(lp.kids.filter((c) => c.nodeType === 3 && /^\s+$/.test((c as FakeText).data)).length, N - 1, "each space a whitespace-only text node under the paragraph");
  assert.equal(lp.kids.filter((c) => c.nodeType === 1 && (c as FakeElement).tagName === "A").length, N, "each link an element holding its text");
  assert.ok(lp.kids[1].previousSibling === lp.kids[0] && lp.kids[1].nextSibling === lp.kids[2], "the stand-in offers sibling pointers");
  const mb = buildRendered(MATH, true);
  const mp = topEl(mb, 1);
  assert.equal(mp.kids.length, 2 * N, "N formula roots and N text runs, all siblings");
  assert.equal(mp.kids.filter((c) => c.nodeType === 1 && (c as FakeElement).getAttribute("class") === "katex").length, N, "the fill's roots stand where the placeholders stood");
  const nb = buildRendered(LINKS, false);
  assert.equal(topEl(nb, 1).kids[1].nextSibling, undefined, "a stand-in built without pointers has neither property (the fallback path)");
});

test("one mark across a paragraph of N links reads the paragraph's child list a linear number of times when the nodes offer sibling pointers, paints every child (the spaces are the passage's own text) and gives the marks a pointer-less stand-in gives", () => {
  const withPtr = buildRendered(LINKS, true);
  const p = topEl(withPtr, 1);
  p.reads = 0;
  const marks = paintRendered(El(withPtr), LINKS, paraRange(LINKS), "fc-hl") as unknown as FakeElement[];
  assert.equal(marks.length, 2 * N - 1, "every child of the paragraph is a mark of its own: N link texts under their anchors and N - 1 spaces");
  assert.equal(marks.filter((m) => /^\s+$/.test(m.textContent)).length, N - 1, "the spaces between inline elements are painted (the passage's own text, not whitespace beside a block)");
  const reads = p.reads;
  assert.ok(reads <= LINEAR(p.kids.length), "the paragraph's child list was read " + reads + " times for " + p.kids.length + " children; the bound is " + LINEAR(p.kids.length) + " (round 8's neighbour scans read it 2,009,993 times, the same build)");
  const without = buildRendered(LINKS, false);
  const fallback = paintRendered(El(without), LINKS, paraRange(LINKS), "fc-hl") as unknown as FakeElement[];
  assert.equal(textsOf(fallback), textsOf(marks), "the fallback (indexing the child list) paints the same marks");
  assert.equal(fallback.length, 2 * N - 1);
});

test("one mark across a paragraph of N inline formulas and text, all siblings, reads the paragraph's child list a linear number of times: follows() takes the pointer too, and the run is one mark", () => {
  const withPtr = buildRendered(MATH, true);
  const p = topEl(withPtr, 1);
  p.reads = 0;
  const marks = paintRendered(El(withPtr), MATH, paraRange(MATH), "fc-hl") as unknown as FakeElement[];
  assert.equal(marks.length, 1, "adjacent siblings, text and formulas, are one run and one mark: " + marks.length);
  assert.equal(marks[0].kids.length, 2 * N, "the mark holds every unit of the paragraph");
  const reads = p.reads;
  assert.ok(reads <= LINEAR(2 * N), "the paragraph's child list was read " + reads + " times for " + 2 * N + " children; the bound is " + LINEAR(2 * N) + " (an index scan per adjacent pair read it 2,012,999 times, the same build)");
  const without = buildRendered(MATH, false);
  const fallback = paintRendered(El(without), MATH, paraRange(MATH), "fc-hl") as unknown as FakeElement[];
  assert.equal(fallback.length, 1);
  assert.equal(fallback[0].textContent, marks[0].textContent, "the fallback paints the same mark");
});
