// The comments painter's layout-time trim (anchor-map.ts trimCollapsedMarks) after the Slice 4 review's round 13, over a DOM
// stand-in that MEASURES: md-config-paint-trim.test.ts's stand-in with one difference, its Range reports an element the Range
// selects whole as that element's border box, as CSSOM getClientRects does in a browser (a mark's box is its text plus 2 px of
// padding a side), so a Range over a mark's contents reads a nested mark's padding where a Range over each text node reads the
// text alone. Three round 13 fixes, each pinned here, where a browser cannot show the mechanism:
// 1. The fixpoint runs to convergence: a cascade of blanks, each collapsing only once the mark before it is gone, is unwrapped
//    whole, one pass a blank, where round 12 stopped after three passes and left the rest as the sheet's padding around nothing
//    (on the paragraph of 5,000 links hundreds of them at 700, 400 and 300 px; the browser leg holds the widths). TRIM_PASSES_MAX
//    is a safety cap alone: a cascade longer than it stops there and the call is counted in TRIM_STATS.capped; one that converges
//    is not counted.
// 2. Nested marks (two or more comments over one passage: the later paint wraps the text node where it stands, inside the earlier
//    comment's mark) over one collapsed blank are measured by their text and unwrapped together in ONE pass, whatever the depth. A
//    Range over each mark's contents read the inner mark's padding (4 px a level) and peeled the nest one level per pass, so four
//    levels or more stood as ringed boxes inside one another at round 12's cap.
// 3. The block-neighbour pre-skip does not apply under an author's `pre`: spaces or a tab between two block children there are
//    painted and measured (and kept, since white-space: pre renders them on a line of their own), a newline alone is painted,
//    measured at zero and unwrapped; the same node outside a pre is skipped unmeasured, as before. Round 12 skipped every such
//    node without a measurement and left the rendered spaces bare inside the pre, a gap in the ring.
// Synthetic prose, no paths.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { paintRendered, trimCollapsedMarks, TRIM_PASSES_MAX, TRIM_STATS } from "./anchor-map";

applyMdConfig();

// -- a DOM stand-in that measures, its Range reading an element's box ----------------------------------------------------------
/** The width a text node lays out at, by the test's rule of the moment. */
type Measure = (t: FakeText, doc: FakeDocument) => number;
/** A mark's padding, 2 px a side (feed.css `.fc-hl { padding: 0 2px }`): what a Range over an outer mark's contents reads of an
 *  inner mark around a collapsed blank. */
const MARK_PAD = 4;
class FakeDocument {
  measure: Measure = () => 3.89;
  /** Layouts: a measurement taken while the tree is dirty (mutated since the last measurement) lays it out. */
  layouts = 0;
  dirty = true;
  /** Every text node measured by a Range over it, in order. */
  measured: FakeText[] = [];
  constructor(public readonly pointers: boolean) {}
  createElement(tag: string): FakeElement { return new FakeElement(this, tag.toUpperCase()); }
  createTextNode(s: string): FakeText { return new FakeText(this, s); }
  createRange(): FakeRange { return new FakeRange(this); }
  touched(): void { this.dirty = true; }
  layoutIfDirty(): void { if (this.dirty) { this.layouts++; this.dirty = false; } }
  /** An element's border box, as a Range that selects it whole reports it: its text's widths, plus a mark's padding. */
  boxOf(e: FakeElement): number {
    let w = e.tagName === "MARK" ? MARK_PAD : 0;
    for (const c of e.kids) w += c.nodeType === 3 ? this.measure(c as FakeText, this) : this.boxOf(c as FakeElement);
    return w;
  }
}
class FakeRange {
  private node: FakeNode | null = null;
  constructor(private doc: FakeDocument) {}
  selectNodeContents(n: FakeNode): void { this.node = n; }
  /** A text node: one rect at the width the rule gives it. An element's contents: a rect per text child at its width, and a rect
   *  per element child at that element's border box (CSSOM: an element the Range selects whole contributes its own boxes). */
  getClientRects(): Array<{ width: number }> {
    this.doc.layoutIfDirty();
    const n = this.node;
    if (!n) return [];
    if (n.nodeType === 3) { this.doc.measured.push(n as FakeText); return [{ width: this.doc.measure(n as FakeText, this.doc) }]; }
    return n.childNodes.map((c) => {
      if (c.nodeType === 3) { this.doc.measured.push(c as FakeText); return { width: this.doc.measure(c as FakeText, this.doc) }; }
      return { width: this.doc.boxOf(c as FakeElement) };
    });
  }
}
class FakeNode {
  nodeType = 0;
  parentNode: FakeElement | null = null;
  previousSibling?: FakeNode | null;
  nextSibling?: FakeNode | null;
  constructor(public ownerDocument: FakeDocument) {}
  get childNodes(): FakeNode[] { return []; }
  get textContent(): string { return this.nodeType === 3 ? (this as unknown as FakeText).data : this.childNodes.map((c) => c.textContent).join(""); }
  get isConnected(): boolean { let n: FakeNode = this; while (n.parentNode) n = n.parentNode; return n instanceof FakeElement && n.tagName === "#ROOT"; }
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
  kids: FakeNode[] = [];
  constructor(doc: FakeDocument, public tagName: string) { super(doc); }
  get childNodes(): FakeNode[] { return this.kids; }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  /** The element's own box: one rect (no scene here hides anything). */
  getClientRects(): unknown[] { this.ownerDocument.layoutIfDirty(); return [{}]; }
  private relink(): void {
    for (let i = 0; i < this.kids.length; i++) {
      const c = this.kids[i];
      c.parentNode = this;
      if (this.ownerDocument.pointers) { c.previousSibling = this.kids[i - 1] ?? null; c.nextSibling = this.kids[i + 1] ?? null; }
    }
    this.ownerDocument.touched();
  }
  private detach(n: FakeNode): void {
    const p = n.parentNode;
    if (p) { p.kids.splice(p.kids.indexOf(n), 1); n.parentNode = null; if (p.ownerDocument.pointers) { n.previousSibling = null; n.nextSibling = null; } p.relink(); }
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
/** marked's HTML into the stand-in (the sibling paint tests' parser): elements with attributes, text, entities. */
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
/** The rendered root (`#ROOT`, so isConnected reads the tree), marked's HTML for `text` under it. */
function buildRendered(text: string): { doc: FakeDocument; box: FakeElement } {
  const doc = new FakeDocument(true);
  const box = doc.createElement("#root"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);
  return { doc, box };
}
const El = (n: FakeNode) => n as unknown as Element;
const Els = (ns: FakeNode[]) => ns as unknown as Element[];
const shape = (e: FakeElement): string[] => e.kids.map((n) => n.nodeType === 3 ? "#text(" + JSON.stringify((n as FakeText).data) + ")" : "<" + (n as FakeElement).tagName + ">");
const wrap = (block: string): string => "Intro para.\n\n" + block + "\n\nAfter para.\n";
const acrossRange = (src: string): { start: number; end: number } => ({ start: src.indexOf("Intro para."), end: src.indexOf("After para.") + "After para.".length });
const isBlank = (s: string): boolean => /^[\s\p{Cf}\p{Mn}]*$/u.test(s);
const texts = (marks: FakeElement[]): string[] => marks.map((m) => m.textContent);
/** The scene's block: the second element child of the root. */
const block = (box: FakeElement): FakeElement => box.kids.filter((n) => n.nodeType === 1)[1] as FakeElement;
const blanksOf = (e: FakeElement): FakeText[] => e.kids.filter((c) => c.nodeType === 3 && isBlank((c as FakeText).data)) as FakeText[];
const inMark = (t: FakeNode): boolean => !!t.parentNode && t.parentNode.tagName === "MARK";
/** A cascade over `blanks`: blank k collapses only once the marks of blanks 0 .. k-1 are gone (each unwrap shortens the line and
 *  the next blank becomes the wrap point), a word is 7.8 px. */
const cascade = (blanks: FakeText[]): Measure => (t) => { const k = blanks.indexOf(t); if (k < 0) return 7.8; return blanks.slice(0, k).some(inMark) ? 3.89 : 0; };
const links = (n: number): string => wrap("<p>" + Array.from({ length: n }, (_, i) => "<b>w" + i + "</b>").join(" ") + "</p>");

// -- 1. the fixpoint runs to convergence -------------------------------------------------------------------------------------
test("the fixpoint runs to convergence: a cascade of five blanks, each collapsing only once the mark before it is gone, is unwrapped whole in five passes (round 12 stopped after three and left two padding-only marks); TRIM_STATS reads the passes, and a call that converges is not counted as capped", () => {
  const src = links(6);
  const { doc, box } = buildRendered(src);
  const blanks = blanksOf(block(box));
  assert.equal(blanks.length, 5);
  doc.measure = cascade(blanks);
  doc.layouts = 0;
  const capped = TRIM_STATS.capped;
  const marks = paintRendered(El(box), src, acrossRange(src), "fc-hl") as unknown as FakeElement[];
  assert.deepEqual(blanks.map(inMark), [false, false, false, false, false], "every blank of the cascade unwrapped, one pass each");
  assert.equal(doc.layouts, 5, "five layouts, one per pass; the fifth unwraps the last blank and the candidates run out");
  assert.equal(TRIM_STATS.passes, 5, "the record reads five passes");
  assert.equal(TRIM_STATS.capped, capped, "a call that converges is not counted as capped");
  assert.deepEqual(texts(marks), ["Intro para.", "w0", "w1", "w2", "w3", "w4", "w5", "After para."], "the word marks stay, in order");
  // a cascade of twelve, the longest measured in a browser (the paragraph of 5,000 links after a narrowing from 800 to 400 px)
  const long = links(13);
  const l = buildRendered(long);
  const lb = blanksOf(block(l.box));
  assert.equal(lb.length, 12);
  l.doc.measure = cascade(lb);
  l.doc.layouts = 0;
  paintRendered(El(l.box), long, acrossRange(long), "fc-hl");
  assert.equal(lb.filter(inMark).length, 0, "twelve passes unwrap the whole cascade");
  assert.equal(l.doc.layouts, 12);
  assert.equal(TRIM_STATS.capped, capped, "not capped");
});

test("the safety cap: a cascade longer than TRIM_PASSES_MAX stops at the cap with the rest of its blanks standing, and the call is counted in TRIM_STATS.capped; the cap is a guard above every cascade measured, never the mechanism", () => {
  assert.ok(TRIM_PASSES_MAX >= 20, "the cap stands above the longest cascade measured (twelve passes, the header): " + TRIM_PASSES_MAX);
  const n = TRIM_PASSES_MAX + 2;
  const src = links(n + 1);
  const { doc, box } = buildRendered(src);
  const blanks = blanksOf(block(box));
  assert.equal(blanks.length, n);
  doc.measure = cascade(blanks);
  doc.layouts = 0;
  const capped = TRIM_STATS.capped;
  const marks = paintRendered(El(box), src, acrossRange(src), "fc-hl") as unknown as FakeElement[];
  assert.equal(blanks.filter(inMark).length, 2, "the cap left the last two blanks of the cascade standing");
  assert.deepEqual(blanks.slice(0, TRIM_PASSES_MAX).map(inMark), Array.from({ length: TRIM_PASSES_MAX }, () => false), "the first TRIM_PASSES_MAX blanks unwrapped, one a pass");
  assert.equal(doc.layouts, TRIM_PASSES_MAX, "one layout per pass up to the cap");
  assert.equal(TRIM_STATS.passes, TRIM_PASSES_MAX);
  assert.equal(TRIM_STATS.capped, capped + 1, "the capped call is counted");
  assert.equal(marks.filter((m) => isBlank(m.textContent)).length, 2, "the two standing blank marks are returned as kept");
  // a call that measures nothing (no blank mark) reads zero passes and is not capped
  const plain = wrap("<p><b>a</b></p>");
  const q = buildRendered(plain);
  paintRendered(El(q.box), plain, acrossRange(plain), "fc-hl");
  assert.equal(TRIM_STATS.passes, 0);
  assert.equal(TRIM_STATS.capped, capped + 1);
});

// -- 2. nested marks measured by their text ----------------------------------------------------------------------------------
test("nested marks over one collapsed blank (overlapping comments, the later paint wrapping the text node inside the earlier mark) are measured by their text and unwrapped together in one pass whatever the depth; a Range over each mark's contents read the inner mark's padding and peeled one level a pass", () => {
  for (const depth of [2, 3, 4, 5, 8]) {
    const what = " (" + depth + " comments)";
    const src = wrap("<p><b>a</b> <b>b</b></p>");
    const { doc, box } = buildRendered(src);
    doc.measure = (t) => (isBlank(t.data) ? 0 : 7.8);
    const all: FakeElement[] = [];
    for (let i = 0; i < depth; i++) all.push(...(paintRendered(El(box), src, acrossRange(src), "fc-hl", { id: "c" + i }, { trim: false }) as unknown as FakeElement[]));
    const blankMarks = all.filter((m) => isBlank(m.textContent));
    assert.equal(blankMarks.length, depth, "one blank mark per comment" + what);
    const up = (m: FakeElement): number => { let d = 0; for (let e: FakeElement | null = m; e && e.tagName === "MARK"; e = e.parentNode) d++; return d; };
    assert.deepEqual(blankMarks.map(up).sort((x, y) => x - y), Array.from({ length: depth }, (_, i) => i + 1), "the blank marks nest, one level per comment" + what);
    // what a Range over the outermost mark's contents reads: the padding of every mark inside it, never zero
    const outer = blankMarks.find((m) => up(m) === 1) as FakeElement;
    const r = doc.createRange(); r.selectNodeContents(outer);
    assert.equal(r.getClientRects().reduce((w, b) => w + b.width, 0), (depth - 1) * MARK_PAD, "the outer mark's contents measure the inner marks' padding" + what);
    doc.touched(); doc.layouts = 0; doc.measured = [];                  // the reading above laid the tree out; the paint's mutations leave it dirty for the trim
    const kept = trimCollapsedMarks(Els(all)) as unknown as FakeElement[];
    assert.equal(kept.filter((m) => isBlank(m.textContent)).length, 0, "every level of the nest unwrapped" + what);
    assert.equal(doc.layouts, 1, "one pass: every level measured its text at zero and the nest was dropped together" + what);
    assert.equal(TRIM_STATS.passes, 1);
    assert.equal(doc.measured.filter((t) => t.data === " ").length, depth, "the one blank text node measured once per level, in the one pass" + what);
    assert.deepEqual(shape(block(box)), ["<B>", '#text(" ")', "<B>"], "the blank's text node stands between the two words (their marks nest inside the b elements), unwrapped" + what);
    assert.ok(kept.every((m) => m.isConnected) && blankMarks.every((m) => m.parentNode === null), "the kept marks stand, the nest is out of the tree" + what);
    assert.equal(kept.length, all.length - depth, "the word marks all stay" + what);
  }
});

// -- 3. the pre-skip does not apply under a pre ------------------------------------------------------------------------------
test("under an author's pre the block-neighbour pre-skip does not apply: spaces or a tab between two block children, before the first, or under a div inside the pre are painted and measured (kept at their width); a newline alone is painted, measured at zero and unwrapped; outside a pre the same node is skipped unmeasured", () => {
  const rendered: Array<[string, string, string]> = [
    ["two spaces between two divs of a pre", wrap("<pre><div>a</div>  <div>b</div></pre>"), "  "],
    ["two spaces before the first div of a pre", wrap("<pre>  <div>a</div></pre>"), "  "],
    ["a newline and two spaces between two divs of a pre", wrap("<pre><div>a</div>\n  <div>b</div></pre>"), "\n  "],
    ["a tab between two divs of a pre", wrap("<pre><div>a</div>\t<div>b</div></pre>"), "\t"],
    ["two spaces between two divs of a div inside a pre (the pre an ancestor, not the parent)", wrap("<pre><div><div>a</div>  <div>b</div></div></pre>"), "  "],
  ];
  for (const [why, src, blank] of rendered) {
    const { doc, box } = buildRendered(src);
    assert.equal(block(box).tagName, "PRE", why + ": the scene is an html block, the pre");
    doc.measure = (t) => (isBlank(t.data) ? 16.86 : 8.44);      // white-space: pre renders the blank on a line of its own
    const marks = paintRendered(El(box), src, acrossRange(src), "fc-hl") as unknown as FakeElement[];
    assert.deepEqual(marks.filter((m) => isBlank(m.textContent)).map((m) => m.textContent), [blank], why + ": painted and kept at its width");
    assert.deepEqual(doc.measured.map((t) => t.data), [blank], why + ": measured once");
    assert.deepEqual(marks.filter((m) => !isBlank(m.textContent)).map((m) => m.textContent), ["Intro para.", "a", "b", "After para."].filter((s) => src.includes(s)), why + ": the words painted");
  }
  // a newline alone between the divs: painted, measured at zero (a forced break) and unwrapped, the text node back in the pre
  const nl = wrap("<pre><div>a</div>\n<div>b</div></pre>");
  const n = buildRendered(nl);
  n.doc.measure = (t) => (isBlank(t.data) ? 0 : 8.44);
  const nm = paintRendered(El(n.box), nl, acrossRange(nl), "fc-hl") as unknown as FakeElement[];
  assert.equal(nm.filter((m) => isBlank(m.textContent)).length, 0, "the newline's mark is unwrapped at zero width");
  assert.deepEqual(n.doc.measured.map((t) => t.data), ["\n"], "the newline was painted and measured, not skipped");
  assert.deepEqual(shape(block(n.box)), ["<DIV>", '#text("\\n")', "<DIV>"], "the newline stands where it was");
  // the control: outside a pre the same node is skipped without a measurement
  const ctl = wrap("<div><div>a</div>  <div>b</div></div>");
  const c = buildRendered(ctl);
  c.doc.measure = () => 16.86;
  const cm = paintRendered(El(c.box), ctl, acrossRange(ctl), "fc-hl") as unknown as FakeElement[];
  assert.equal(cm.filter((m) => isBlank(m.textContent)).length, 0, "outside a pre: no blank mark");
  assert.equal(c.doc.measured.length, 0, "outside a pre: nothing measured");
});
