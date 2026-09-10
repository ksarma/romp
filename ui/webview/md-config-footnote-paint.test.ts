// A footnote definition's body is a paragraph inside its div, so a highlight across the note paints the spaces between the
// body's inline elements as it paints a paragraph's (md-config.ts footnoteDef, the Slice 4 review, round 10). Before this the
// body rendered as inline content directly under `div.md-footnote`, and the Rendered paint (anchor-map.ts skipBlockWs) read
// each whitespace-only text node under the DIV as white space between blocks and skipped it: `[^1]: **a** *b*` painted `a` and
// `b` with the rendered space between them bare (a 4 px gap between two ring ends, in headless Chromium), two links in a
// definition likewise, where main, which rendered the line as a plain paragraph, painted it whole. The same round retired that
// container reading in anchor-map.ts (a rendered space between two inline children of a div paints now), so the paragraph
// stands on GitHub's shape, and this file pins it whichever way the paint reads a DIV. Driven behaviourally over
// the viewer's Rendered shape rebuilt as anchor-map.test.ts rebuilds it (marked's output under the one configuration parsed into
// the DOM stand-in) and through paintRendered from the paragraph before the definition to the paragraph after, the panel's
// gesture; the browser leg (md-config-footnote-paint-browser.test.ts) measures the same shapes over the real bundle. Synthetic
// prose, hosts under .test.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { paintRendered } from "./anchor-map";
import { hideEdges } from "../test-dom-shim";

applyMdConfig();

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser (anchor-map.test.ts's shape) ──
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
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
    return e in NAMED ? NAMED[e] : m;
  });
}
function parseHTML(doc: FakeDocument, html: string): FakeNode[] {
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
      if (!m[3] && !VOID.has(m[1].toLowerCase())) stack.push(el);
      continue;
    }
    let e = html.indexOf("<", i);
    if (e < 0) e = html.length;
    top().appendChild(doc.createTextNode(decodeEntities(html.slice(i, e))));
    i = e;
  }
  return root.childNodes.slice();
}
/** `.fileview-md > marked output` under the one configuration, as the viewer's mdBlock builds it (no math, no wikilinks here). */
function buildRendered(src: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(src) as string)) box.appendChild(n);
  return box;
}
const El = (n: FakeNode) => n as unknown as Element;
const isEl = (n: FakeNode): n is FakeElement => n.nodeType === 1;
const label = (n: FakeNode): string => { const e = n as FakeElement; const c = e.getAttribute("class"); return e.tagName + (c ? "." + c : ""); };
function byClass(root: FakeNode, cls: string, out: FakeElement[] = []): FakeElement[] {
  for (const c of root.childNodes) { if (isEl(c)) { if ((c.getAttribute("class") || "").split(/\s+/).includes(cls)) out.push(c); byClass(c, cls, out); } }
  return out;
}
function allText(root: FakeNode, out: FakeText[] = []): FakeText[] {
  if (root.nodeType === 3) out.push(root as FakeText);
  for (const c of root.childNodes) allText(c, out);
  return out;
}
const inMark = (n: FakeNode): boolean => { for (let p = n.parentNode; p; p = p.parentNode) if (isEl(p) && p.tagName === "MARK") return true; return false; };
/** The whitespace-only text nodes under `root` that no mark holds: the paint's gaps at a rendered space (each such node between
 *  two inline elements is a space the browser renders; the ones between blocks it collapses, and the stand-in has none of those
 *  under a footnote's paragraph). */
const wsGaps = (root: FakeNode): string[] => allText(root).filter((t) => t.data.length && !t.data.trim() && !inMark(t)).map((t) => label(t.parentNode!) + " " + JSON.stringify(t.data));
/** Paint from the start of `from` to the end of `to` (both once in `src`), the panel's gesture; each mark as [its parent, its text]. */
function paint(box: FakeElement, src: string, from = "Intro para.", to = "After para."): Array<[string, string]> {
  const start = src.indexOf(from), end = src.indexOf(to) + to.length;
  assert.ok(start >= 0 && end > start, "the range's ends are in the source");
  const marks = paintRendered(El(box), src, { start, end }, "fc-hl", { id: "c1" }) as unknown as FakeElement[];
  return marks.map((m) => [label(m.parentNode!), m.textContent]);
}
const doc = (body: string): string => "Intro para.\n\n" + body + "\n\nAfter para.\n";
const BACK = '<a class="md-fnback" href="#fnref-1" title="Back to the text">1</a>';

test("a definition renders as one div holding one paragraph, the back link first in it and the body after; nothing stands directly under the div", () => {
  const html = marked.parse(doc("x[^1]\n\n[^1]: **a** *b*")) as string;
  assert.ok(html.includes(`<div class="md-footnote" id="fn-1"><p>${BACK} <strong>a</strong> <em>b</em></p></div>`), html);
  assert.ok((marked.parse("[^x]: **a** *b*\n") as string).startsWith('<div class="md-footnote" id="fn-x"><p><span class="md-fnback"'), "the orphan definition's label opens the paragraph too");
  assert.ok((marked.parse("x[^1]\n\n[^1]: **a**\n  *b* continued\n") as string).includes(`<p>${BACK} <strong>a</strong>\n<em>b</em> continued</p></div>`), "a continuation line stays inside the paragraph");
  const box = buildRendered(doc("x[^1]\n\n[^1]: **a** *b*"));
  const fn = byClass(box, "md-footnote");
  assert.equal(fn.length, 1);
  assert.deepEqual(fn[0].childNodes.map((c) => (isEl(c) ? c.tagName : JSON.stringify((c as FakeText).data))), ["P"], "one paragraph and no text node directly under the div");
  assert.equal(box.childNodes.filter(isEl).map((c) => c.tagName).join(" "), "P P DIV P", "still one top-level element per block: the block pairing holds");
});

test("a highlight from the paragraph before a definition to the paragraph after paints the spaces between the body's inline elements, as it paints a paragraph's; no whitespace-only text node under the footnote is left outside a mark", () => {
  const shapes: Array<[string, string, Array<[string, string]>]> = [
    ["strong and em", "x[^1]\n\n[^1]: **a** *b*", [["P", " "], ["STRONG", "a"], ["P", " "], ["EM", "b"]]],
    ["two links", "x[^1]\n\n[^1]: See [the RFC](https://example.test/a) [and the spec](https://example.test/b).", [["P", " See "], ["A", "the RFC"], ["P", " "], ["A", "and the spec"], ["P", "."]]],
    ["two code spans", "x[^1]\n\n[^1]: `foo` `bar`", [["P", " "], ["CODE", "foo"], ["P", " "], ["CODE", "bar"]]],
    ["an orphan definition", "[^x]: **a** *b*", [["P", " "], ["STRONG", "a"], ["P", " "], ["EM", "b"]]],
    ["a continuation line", "x[^1]\n\n[^1]: **a**\n  *b* continued", [["P", " "], ["STRONG", "a"], ["P", "\n"], ["EM", "b"], ["P", " continued"]]],
    ["inside a blockquote", "> x[^1]\n>\n> [^1]: **a** *b*", [["P", " "], ["STRONG", "a"], ["P", " "], ["EM", "b"]]],
  ];
  for (const [name, body, want] of shapes) {
    const src = doc(body);
    const box = buildRendered(src);
    const fn = byClass(box, "md-footnote")[0];
    assert.ok(fn, name + ": the definition rendered");
    const marks = paint(box, src);
    const fnMarks = marksUnder(fn);   // the footnote's own marks: each under its paragraph or under an inline element inside it
    assert.deepEqual(fnMarks, want, name + ": the footnote's marks (all marks: " + JSON.stringify(marks) + ")");
    assert.deepEqual(wsGaps(fn), [], name + ": every whitespace-only text node under the footnote is inside a mark");
    assert.equal(marks.filter(([, text]) => !text.length).length, 0, name + ": no empty mark");
    assert.equal(marks.filter(([parent]) => parent.startsWith("DIV.md-footnote")).length, 0, name + ": no mark directly under the div (the paragraph holds them)");
  }
});
/** The marks under `root` in document order, each as [its parent, its text]. */
function marksUnder(root: FakeNode, out: Array<[string, string]> = []): Array<[string, string]> {
  for (const c of root.childNodes) { if (isEl(c)) { if (c.tagName === "MARK") out.push([label(c.parentNode!), c.textContent]); else marksUnder(c, out); } }
  return out;
}

test("a highlight over the body alone paints the body's space and nothing of the back link or the separator after it; the number of a reference to the note is untouched by a paint that stops before it", () => {
  const src = doc("x[^1]\n\n[^1]: **a** *b*");
  const box = buildRendered(src);
  const body = paint(box, src, "**a**", "*b*");
  assert.deepEqual(body, [["STRONG", "a"], ["P", " "], ["EM", "b"]], "the body's three pieces, the space between them painted");
  const back = byClass(box, "md-fnback")[0];
  assert.ok(back && !inMark(back) && !back.childNodes.some(inMark), "the back link is outside every mark");
  const fresh = buildRendered(src);
  const before = paint(fresh, src, "Intro para.", "Intro para.");
  assert.deepEqual(before, [["P", "Intro para."]]);
  assert.deepEqual(wsGaps(byClass(fresh, "md-footnote")[0]).length, 2, "a paint that never reaches the footnote leaves its two spaces unpainted, as any paragraph's outside the range");
});
