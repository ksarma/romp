// The comments painter's layout-time trim (anchor-map.ts trimCollapsedMarks, the Slice 4 review's round 12), over a DOM stand-in
// that MEASURES: the stand-in's document offers createRange, its Range getClientRects, and its elements getClientRects, so the
// trim runs here as it runs in a browser, with the widths a test hands it instead of a layout's. The design under test: paintRendered
// paints every text node of its range below the render root (two DOM-side skips apart, skipBlockWs: the root guard and a node of
// collapsible white space between two block boxes), then measures every mark whose text is blank and unwraps the ones that lay out
// at zero width. Pinned here, where a browser cannot show the shape of the measurement:
// 1. The rule: a blank mark measured at zero width is unwrapped (its text node back in place, no normalize), one with a width is
//    kept; a mark holding a word is never measured; a mark with no client rect of its own (a display:none ancestor) is kept.
// 2. Two-phase: every candidate is measured, then every collapsed one unwrapped, so a pass is one layout however many marks it
//    unwraps (the stand-in counts a layout at each measurement taken after a mutation); a measurement per unwrap cost the
//    prototype 12 s on a paragraph of 5,000 code spans.
// 3. The fixpoint: after a pass that unwrapped something the remaining candidates are measured again (a stand-in whose widths
//    depend on which marks stand shows the second pass unwrapping what the first pass's unwraps collapsed), until a pass unwraps
//    nothing or no candidate is left: a cascade of five blanks, each collapsing once the marks before it are gone, is unwrapped
//    whole, one layout per pass and every pass over the marks the last one kept. The test holds the result and the passes the
//    scene takes (five layouts and 5+4+3+2+1 measurements for the cascade alone; six and 7+6+5+4+3+2 with two rendered blanks
//    after it, the sixth the confirming pass), never the loop's cap: round 12 capped the loop at three and pinned the cap here,
//    and the cap left 366 padding-only marks on a paragraph of 5,000 links at 700 px (round 13). TRIM_PASSES_MAX is a safety cap
//    above every cascade measured, pinned as a bound and never as the mechanism in md-config-paint-trim-fixpoint.test.ts, with
//    TRIM_STATS, the count of the calls that reached it.
// 4. Batching: paintRendered trims its own marks by default and defers when the caller passes `trim: false`; trimCollapsedMarks over
//    the marks of several paints measures them in one pass, the Comments panel's call shape (file-comments.ts paintAll).
// 5. The candidate alphabet picks what is MEASURED and nothing else: a lone bidi mark, soft hyphen, combining mark or hangul filler
//    is measured (round 12: the zero-width alphabet of round 11 missed them and painted a 4 px box); a letter, a digit, punctuation
//    or a symbol is not.
// 6. The two DOM-side skips: a zero-width run or a no-break space directly under the root gets no mark and no measurement (the
//    root guard); collapsible white space between two block boxes, a run of such nodes, or at a block-box parent's edge is skipped
//    unmeasured; one beside an inline is painted and measured.
// Synthetic prose, no paths.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { paintRendered, paintChangesRendered, trimCollapsedMarks, type ChangePaint } from "./anchor-map";
import { hideEdges, defineHidden } from "../test-dom-shim";

applyMdConfig();

// -- a DOM stand-in that measures --------------------------------------------------------------------------------------------
// Nodes hide their edges at construction (hideEdges, ui/test-dom-shim.ts; the sibling pointers through defineHidden), so a failing
// assertion's dump shows a node's primitives and not the tree (the ratchet in ui/test-dom-shim.test.ts).
/** The width a text node lays out at, by the test's rule of the moment: `measure` answers per text node (its data, its mark, the
 *  document), so a scene can make a blank collapse only while another mark stands. */
type Measure = (t: FakeText, doc: FakeDocument) => number;
class FakeDocument {
  measure: Measure = () => 3.89;
  /** Layouts: a measurement taken while the tree is dirty (mutated since the last measurement) lays it out. */
  layouts = 0;
  dirty = true;
  /** Every text node measured, in order (the alphabet pin reads which marks were measured). */
  measured: FakeText[] = [];
  constructor(public readonly pointers: boolean) {}
  createElement(tag: string): FakeElement { return new FakeElement(this, tag.toUpperCase()); }
  createTextNode(s: string): FakeText { return new FakeText(this, s); }
  createRange(): FakeRange { return new FakeRange(this); }
  touched(): void { this.dirty = true; }
  layoutIfDirty(): void { if (this.dirty) { this.layouts++; this.dirty = false; } }
}
class FakeRange {
  private node: FakeNode | null = null;
  constructor(private doc: FakeDocument) {}
  selectNodeContents(n: FakeNode): void { this.node = n; }
  getClientRects(): Array<{ width: number }> {
    this.doc.layoutIfDirty();
    const out: Array<{ width: number }> = [];
    const visit = (n: FakeNode) => { if (n.nodeType === 3) { this.doc.measured.push(n as FakeText); out.push({ width: this.doc.measure(n as FakeText, this.doc) }); } else for (const c of n.childNodes) visit(c); };
    if (this.node) visit(this.node);
    return out;
  }
}
class FakeNode {
  nodeType = 0;
  parentNode: FakeElement | null = null;
  previousSibling?: FakeNode | null;
  nextSibling?: FakeNode | null;
  constructor(public ownerDocument: FakeDocument) { hideEdges(this); }
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
  constructor(doc: FakeDocument, public tagName: string) { super(doc); hideEdges(this); }
  get childNodes(): FakeNode[] { return this.kids; }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  /** The element's own box: none under a `hidden` element (display: none), else one rect. */
  getClientRects(): unknown[] { this.ownerDocument.layoutIfDirty(); for (let e: FakeElement | null = this; e; e = e.parentNode) if (e.attrs.has("hidden")) return []; return [{}]; }
  /** The marks under this element, document order. */
  marks(): FakeElement[] { const out: FakeElement[] = []; const find = (n: FakeNode) => { for (const c of n.childNodes) if (c.nodeType === 1) { if ((c as FakeElement).tagName === "MARK") out.push(c as FakeElement); find(c); } }; find(this); return out; }
  private relink(): void {
    for (let i = 0; i < this.kids.length; i++) {
      const c = this.kids[i];
      c.parentNode = this;
      if (this.ownerDocument.pointers) { defineHidden(c, "previousSibling", this.kids[i - 1] ?? null); defineHidden(c, "nextSibling", this.kids[i + 1] ?? null); }
    }
    this.ownerDocument.touched();
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
/** marked's HTML into the stand-in (the sibling paint tests' parser): elements with attributes, text, entities; a comment dropped
 *  as DOMPurify drops it, the white space on its two sides left as two adjacent text nodes. */
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
function buildRendered(text: string, pointers = true): { doc: FakeDocument; box: FakeElement } {
  const doc = new FakeDocument(pointers);
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
/** The paragraph of the scene: the second element child of the root. */
const para = (box: FakeElement): FakeElement => box.kids.filter((n) => n.nodeType === 1)[1] as FakeElement;
const hex = (ch: string): string => "U+" + ch.codePointAt(0)!.toString(16) + (ch.length > 1 ? "+" : "");

// -- 1. the rule -------------------------------------------------------------------------------------------------------------
const TWO_INLINES = wrap("<p><b>a</b> <i>b</i></p>");

test("a blank mark measured at zero width is unwrapped, its text node back where the mark stood and the neighbouring marks untouched; one with a width is kept; the mark's text nodes are what is measured, and a mark holding a word is never measured", () => {
  for (const pointers of [true, false]) {
    const what = pointers ? "" : " (the index path)";
    // collapsed: the blank between the two inlines lays out at zero width (the line's edge, say)
    const c = buildRendered(TWO_INLINES, pointers);
    c.doc.measure = (t) => (isBlank(t.data) ? 0 : 7.8);
    const p = para(c.box);
    assert.deepEqual(shape(p), ["<B>", '#text(" ")', "<I>"], "the paragraph as built" + what);
    const marks = paintRendered(El(c.box), TWO_INLINES, acrossRange(TWO_INLINES), "fc-hl") as unknown as FakeElement[];
    assert.deepEqual(texts(marks), ["Intro para.", "a", "b", "After para."], "the collapsed blank's mark is unwrapped, the others stay" + what);
    assert.deepEqual(shape(p), ["<B>", '#text(" ")', "<I>"], "the blank's text node stands where its mark stood, unwrapped" + what);
    assert.deepEqual(c.doc.measured.map((t) => t.data), [" "], "the one blank mark's text node is what was measured; the word marks were not" + what);
    assert.ok(marks.every((m) => m.isConnected), "every mark returned stands in the document" + what);
    // rendered: the same blank at a width keeps its mark
    const r = buildRendered(TWO_INLINES, pointers);
    r.doc.measure = () => 3.89;
    const kept = paintRendered(El(r.box), TWO_INLINES, acrossRange(TWO_INLINES), "fc-hl") as unknown as FakeElement[];
    assert.deepEqual(texts(kept), ["Intro para.", "a", " ", "b", "After para."], "a blank with a width keeps its mark" + what);
    assert.deepEqual(r.doc.measured.map((t) => t.data), [" "], "measured once" + what);
  }
});

test("a mark with no client rect of its own (a hidden ancestor) is kept though its text measures zero: its blank may render when the ancestor shows", () => {
  const src = wrap('<p><span hidden><b>a</b> <i>b</i></span> <em>c</em></p>');
  const { doc, box } = buildRendered(src);
  doc.measure = (t) => (isBlank(t.data) ? 0 : 7.8);
  const marks = paintRendered(El(box), src, acrossRange(src), "fc-hl") as unknown as FakeElement[];
  assert.deepEqual(texts(marks), ["Intro para.", "a", " ", "b", "c", "After para."], "the blank inside the hidden span keeps its mark (no rect of its own), the one outside it is unwrapped");
});

test("a framed picture (an img wearing the highlight class) and a deletion point in the list are never touched, and an empty list is returned as it came", () => {
  const src = wrap('<p><img src="a.png" alt="a"> <b>x</b></p>');
  const { doc, box } = buildRendered(src);
  doc.measure = () => 0;
  const img = para(box).kids[0] as FakeElement; img.setAttribute("class", "fc-hl fc-img");
  const point = doc.createElement("span"); point.setAttribute("class", "fc-del"); para(box).insertBefore(point, img);
  const kept = trimCollapsedMarks(Els([img, point])) as unknown as FakeElement[];
  assert.deepEqual(kept, [img, point], "neither is a mark: both returned, neither unwrapped");
  assert.ok(img.parentNode === para(box) && point.parentNode === para(box), "both stand where they were");
  assert.equal(doc.measured.length, 0, "nothing measured");
  assert.deepEqual(trimCollapsedMarks([]), [], "an empty list");
});

// -- 2. two-phase, one layout per pass ---------------------------------------------------------------------------------------
const N = 200;
const LINKS = wrap(Array.from({ length: N }, (_, i) => "[w" + i + "](#a" + i + ")").join(" "));

test("a pass measures every candidate first and unwraps afterwards: one layout for the pass however many marks it unwraps, and a second layout only to confirm the fixpoint (a measurement per unwrap would be a layout per unwrap)", () => {
  // every blank collapsed: one pass unwraps all N - 1 and the candidates run out, one layout
  const all = buildRendered(LINKS);
  all.doc.measure = (t) => (isBlank(t.data) ? 0 : 20);
  all.doc.layouts = 0;
  const m1 = paintRendered(El(all.box), LINKS, acrossRange(LINKS), "fc-hl") as unknown as FakeElement[];
  assert.equal(m1.length, N + 2, "the N link texts stay (and the two paragraphs around), the N - 1 spaces are unwrapped");
  assert.equal(m1.filter((m) => isBlank(m.textContent)).length, 0);
  assert.equal(all.doc.layouts, 1, "one layout: every measurement before any unwrap");
  assert.equal(all.doc.measured.length, N - 1, "each blank measured once");
  // every other blank collapsed: the first pass unwraps half, the second measures the rest again and unwraps nothing: two layouts
  const half = buildRendered(LINKS);
  let k = 0; const collapsed = new Set<FakeText>();
  for (const c of para(half.box).kids) if (c.nodeType === 3 && isBlank((c as FakeText).data) && k++ % 2 === 0) collapsed.add(c as FakeText);
  half.doc.measure = (t) => (collapsed.has(t) ? 0 : 3.89);
  half.doc.layouts = 0;
  const m2 = paintRendered(El(half.box), LINKS, acrossRange(LINKS), "fc-hl") as unknown as FakeElement[];
  assert.equal(m2.filter((m) => isBlank(m.textContent)).length, N - 1 - collapsed.size, "the rendered blanks keep their marks");
  assert.equal(half.doc.layouts, 2, "two layouts: the pass that unwrapped, and the pass that measured the rest again and unwrapped nothing");
  assert.equal(half.doc.measured.length, (N - 1) + (N - 1 - collapsed.size), "every blank measured in the first pass, the kept ones again in the second");
  // nothing collapsed: one layout, no unwrap
  const none = buildRendered(LINKS);
  none.doc.layouts = 0;
  const m3 = paintRendered(El(none.box), LINKS, acrossRange(LINKS), "fc-hl") as unknown as FakeElement[];
  assert.equal(m3.length, 2 * N - 1 + 2);
  assert.equal(none.doc.layouts, 1, "one layout, nothing to unwrap");
});

// -- 3. the fixpoint ---------------------------------------------------------------------------------------------------------
/** A cascade of `n` blanks in a paragraph of `n + tail + 1` bold words: blank k lays out at zero width only once the marks of
 *  blanks 0 .. k-1 are gone (each unwrap shortens the line by the mark's padding and the next blank becomes the wrap point), so
 *  pass k + 1 unwraps blank k and no pass unwraps two; the `tail` blanks after the cascade render whatever stands. */
function cascade(n: number, tail = 0): { doc: FakeDocument; box: FakeElement; src: string; blanks: FakeText[]; inMark: (t: FakeText) => boolean } {
  const words = Array.from({ length: n + tail + 1 }, (_, i) => "<b>" + String.fromCharCode(97 + i) + "</b>");
  const src = wrap("<p>" + words.join(" ") + "</p>");
  const { doc, box } = buildRendered(src);
  const blanks = para(box).kids.filter((c) => c.nodeType === 3 && isBlank((c as FakeText).data)) as FakeText[];
  assert.equal(blanks.length, n + tail, "the scene's blanks");
  const inMark = (t: FakeText): boolean => !!t.parentNode && t.parentNode.tagName === "MARK";
  doc.measure = (t) => { const k = blanks.indexOf(t); if (k < 0) return 7.8; if (k >= n) return 3.89; return blanks.slice(0, k).some(inMark) ? 3.89 : 0; };
  doc.layouts = 0;
  return { doc, box, src, blanks, inMark };
}

test("after a pass that unwrapped something the remaining candidates are measured again, until a pass unwraps nothing or no candidate is left: a cascade of five blanks, each collapsing only once the marks before it are gone, is unwrapped whole over five passes (one layout each, every pass over the marks the last one kept); two rendered blanks after it cost one confirming pass and keep their marks", () => {
  // round 12 stopped after three passes, so blanks 3 and 4 kept their marks: the sheet's padding around nothing, the box the
  // trim exists to remove (on a paragraph of 5,000 links at 700 px the cap kept 366 of them; round 13 runs the loop to its end)
  const a = cascade(5);
  const marks = paintRendered(El(a.box), a.src, acrossRange(a.src), "fc-hl") as unknown as FakeElement[];
  assert.deepEqual(a.blanks.map(a.inMark), [false, false, false, false, false], "pass k + 1 unwrapped blank k: the whole cascade, blanks 3 and 4 with it");
  assert.equal(a.doc.layouts, 5, "five layouts, one per unwrapping pass; the candidates ran out with the fifth, so no confirming pass");
  assert.equal(a.doc.measured.length, 5 + 4 + 3 + 2 + 1, "every pass measures the candidates the last one kept and no other");
  assert.equal(marks.filter((m) => isBlank(m.textContent)).length, 0, "no blank mark stands");
  assert.deepEqual(texts(marks), ["Intro para.", "a", "b", "c", "d", "e", "f", "After para."], "the returned list is the kept marks in the order given");
  // the same cascade before two blanks that render whatever stands: five unwrapping passes, then the pass that measures the two,
  // unwraps nothing and ends the loop
  const b = cascade(5, 2);
  const kept = paintRendered(El(b.box), b.src, acrossRange(b.src), "fc-hl") as unknown as FakeElement[];
  assert.deepEqual(b.blanks.map(b.inMark), [false, false, false, false, false, true, true], "the cascade unwrapped whole, the two rendered blanks keep their marks");
  assert.equal(b.doc.layouts, 6, "six layouts: five unwrapping passes and the one that confirmed the fixpoint");
  assert.equal(b.doc.measured.length, 7 + 6 + 5 + 4 + 3 + 2, "each pass over the marks the last one kept: seven, then six, down to the two of the confirming pass");
  assert.deepEqual(texts(kept), ["Intro para.", "a", "b", "c", "d", "e", "f", " ", "g", " ", "h", "After para."]);
});

// -- 4. batching: the panel's call shape -------------------------------------------------------------------------------------
test("paintRendered with `trim: false` leaves every blank mark for the caller, and trimCollapsedMarks over the marks of several paints measures them in one pass; paintChangesRendered takes the same option", () => {
  // two markdown paragraphs of two inline children each (an html block's inside is not mapped, so the ranges are markdown's)
  const src = "Intro para.\n\n**a** *b*\n\n**c** *d*\n\nAfter para.\n";
  const { doc, box } = buildRendered(src);
  doc.measure = (t) => (isBlank(t.data) ? 0 : 7.8);
  const r1 = { start: src.indexOf("**a**"), end: src.indexOf("*b*") + 3 };
  const r2 = { start: src.indexOf("**c**"), end: src.indexOf("*d*") + 3 };
  const m1 = paintRendered(El(box), src, r1, "fc-hl", { id: "c1" }, { trim: false }) as unknown as FakeElement[];
  const m2 = paintRendered(El(box), src, r2, "fc-hl", { id: "c2" }, { trim: false }) as unknown as FakeElement[];
  assert.deepEqual([texts(m1), texts(m2)], [["a", " ", "b"], ["c", " ", "d"]], "the trim deferred: the blank marks stand");
  assert.equal(doc.measured.length, 0, "nothing measured yet");
  doc.layouts = 0;
  const kept = trimCollapsedMarks(Els([...m1, ...m2])) as unknown as FakeElement[];
  assert.deepEqual(texts(kept), ["a", "b", "c", "d"], "one trim over both paints' marks unwraps both collapsed blanks");
  assert.equal(doc.layouts, 1, "one layout for the batch");
  assert.equal(doc.measured.length, 2, "the two blank marks measured, once each");
  assert.ok(kept.every((m) => m.isConnected) && m1[1].parentNode === null && m2[1].parentNode === null, "the kept marks stand, the unwrapped ones are out of the tree");
  // a change mark: the same option through paintChangesRendered; without it the trim runs in the call
  const ins = { id: "h1", kind: "ins", curFrom: r1.start, curTo: r1.end, oldText: "", newText: src.slice(r1.start, r1.end), author: "api" } as unknown as ChangePaint;
  const c = buildRendered(src);
  c.doc.measure = (t) => (isBlank(t.data) ? 0 : 7.8);
  const deferred = paintChangesRendered(El(c.box), src, [ins], () => ({}), { trim: false });
  assert.deepEqual(deferred.painted, ["h1"]);
  assert.equal(c.doc.measured.length, 0, "the change paint measured nothing with the trim deferred");
  assert.deepEqual(texts(para(c.box).marks()), ["a", " ", "b"], "the change's blank mark stands");
  const c2 = buildRendered(src);
  c2.doc.measure = (t) => (isBlank(t.data) ? 0 : 7.8);
  paintChangesRendered(El(c2.box), src, [ins], () => ({}));
  assert.deepEqual(texts(para(c2.box).marks()), ["a", "b"], "without the option the change paint trims its own marks");
});

// -- 5. the candidate alphabet -----------------------------------------------------------------------------------------------
test("what is measured: a mark of a bidi mark, a soft hyphen, a combining mark, a hangul filler, a control, a tab, a no-break space or a line separator alone is measured (layout decides); a mark holding a letter, a digit, punctuation or a symbol is not", () => {
  const measured: Array<[string, boolean]> = [["\u200e", true], ["\u00ad", true], ["\u0301", true], ["\u3164", true], ["\u115f", true], ["\u000b", true], ["\t", true], ["\u00a0", true], ["\u3000", true], ["\ufeff", true], ["\u2028", true], ["\u093f", true], ["a", false], ["1", false], [".", false], ["$", false], ["x" + "\u200e", false]];
  for (const [ch, expect] of measured) {
    const src = wrap("<p><b>a</b>" + ch + "<i>b</i></p>");
    const { doc, box } = buildRendered(src);
    doc.measure = () => 3.89;
    paintRendered(El(box), src, acrossRange(src), "fc-hl");
    const got = doc.measured.some((t) => t.data === ch);
    assert.equal(got, expect, hex(ch) + (expect ? " is measured" : " is never measured"));
  }
});

// -- 6. the two DOM-side skips, unmeasured -----------------------------------------------------------------------------------
test("the root guard: a text node of `\\s` or format characters alone directly under the root gets no mark and no measurement (a no-break space, U+200B, U+200E, a soft hyphen, U+FEFF, a newline); no mark is a top-level node", () => {
  for (const ch of ["\u00a0", "\u200b", "\u200e", "\u00ad", "\ufeff", "\n"]) {
    const src = wrap("<p>x</p>" + ch + "<p>y</p>");
    const { doc, box } = buildRendered(src);
    doc.measure = () => 3.89;
    assert.ok(box.kids.some((n) => n.nodeType === 3 && (n as FakeText).data === ch), "the fixture holds " + hex(ch) + " as a top-level text node: " + JSON.stringify(shape(box)));
    const marks = paintRendered(El(box), src, acrossRange(src), "fc-hl") as unknown as FakeElement[];
    assert.deepEqual(texts(marks), ["Intro para.", "x", "y", "After para."], hex(ch) + " at the top level: no mark");
    for (const m of marks) assert.notEqual(m.parentNode, box, "no mark is a top-level node");
    assert.equal(doc.measured.length, 0, "nothing measured");
  }
});

test("the block-neighbour pre-skip: collapsible white space between two block boxes, a run of two such nodes, or at a block-box parent's edge is skipped without a measurement; the same white space beside an inline is painted and measured, a no-break space between blocks is painted and measured", () => {
  const skipped: Array<[string, string]> = [
    ["between two paragraphs of a div", wrap("<div>\n<p>one</p>\n<p>two</p>\n</div>")],
    ["between two items", wrap("- one\n- two")],
    ["a run of two nodes where a comment stood, between two paragraphs of a quote", wrap("<blockquote><p>one</p>\n<!-- x -->\n<p>two</p></blockquote>")],
    ["at a cell's edge", wrap("<table><tr><td>\n</td><td>x</td></tr></table>")],
    ["alone in an item", wrap("<ul><li> </li><li>two</li></ul>")],
    ["between a fold's summary and its paragraph", wrap("<details open>\n<summary>Shots</summary>\n<p>x</p>\n</details>")],
  ];
  for (const [why, src] of skipped) {
    const { doc, box } = buildRendered(src);
    doc.measure = () => 0;
    const marks = paintRendered(El(box), src, acrossRange(src), "fc-hl") as unknown as FakeElement[];
    assert.equal(marks.filter((m) => isBlank(m.textContent)).length, 0, why + ": no blank mark");
    assert.equal(doc.measured.length, 0, why + ": nothing measured");
  }
  const measured: Array<[string, string, string[]]> = [
    ["beside an inline child (the figure's image)", wrap('<figure>\n<img src="a.png" alt="a">\n<figcaption>c</figcaption>\n</figure>'), ["\n", "\n"]],
    ["between two br elements", wrap("line one<br>\n<br>\nline three"), ["\n"]],
    ["beside an inline child at a block's edge", wrap("<blockquote> <b>q</b> <i>r</i> </blockquote>"), [" ", " ", " "]],
    ["a no-break space between two paragraphs of a div", wrap("<div><p>one</p>&nbsp;<p>two</p></div>"), ["\u00a0"]],
  ];
  for (const [why, src, blanks] of measured) {
    const { doc, box } = buildRendered(src);
    doc.measure = () => 3.89;
    const marks = paintRendered(El(box), src, acrossRange(src), "fc-hl") as unknown as FakeElement[];
    assert.deepEqual(marks.filter((m) => isBlank(m.textContent)).map((m) => m.textContent), blanks, why + ": painted (and kept at a width)");
    assert.deepEqual(doc.measured.map((t) => t.data), blanks, why + ": each measured once");
  }
});
