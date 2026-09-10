// A blank the browser collapses is never painted, whatever stands beside it; a blank it renders is. skipBlockWs (anchor-map.ts)
// skips a whitespace-only text node the browser renders nothing of, so that no mark rings an empty box (the sheet's 4 px of padding
// around nothing), and round 10's readings, a block box or a `<br>` beside the node and the edge of a block-level parent, still
// painted that box in three shapes (the Slice 4 review, round 11), each measured at 0 px before the paint in Chromium:
// 1. A text node of zero-width format characters alone (U+FEFF, the zero width no-break space a BOM leaves in a chunked file,
//    U+200B to U+200D, U+2060 to U+2064) renders no glyph anywhere. U+FEFF is JavaScript's `\s`, so the ASCII alphabet round 10
//    chose for "whitespace-only" made it text and painted a lone U+FEFF as the 4 px box under a div, a list item or a paragraph
//    (round 9 and main's container rule left it alone); a lone U+200B was the box on main too. Such a node is skipped wherever it
//    stands. As a NEIGHBOUR it is a character (the space after `a ` plus a zero-width character renders), and a node mixing the
//    characters with ASCII white space is text, painted.
// 2. An inline element that renders nothing between the node and the line's edge: an `<a name="x"></a>` anchor or an icon
//    `<i class="icon"></i>` leading a list item, an anchor closing one, an empty `<span>`, `<sup>` or `<code>`, a `hidden` element,
//    one nested in another. The node is the line's leading or trailing white space and collapses; the neighbour reading stopped at
//    any element and painted it as the box under LI, DIV, BLOCKQUOTE and TD, where main's container rule had skipped it. An atomic
//    inline (an `<img>`, a task item's checkbox, an empty `<kbd>`, an inline-block with a border) is content: the space beside it
//    renders. The parent's edge is read through inline ancestors (`<p><em> <b>a</b></em></p>`), and a block inside an inline splits
//    the line as a block sibling does.
// 3. A neighbour whose text ends with collapsible white space (`<b>Label: </b> <i>value</i>`, `[docs ](#a) *x*`, a code span, a
//    `<br>` closing the neighbour): CSS collapses a collapsible space that follows another, across inline boundaries, so the node
//    renders nothing while the space inside the neighbour shows. Only the side BEFORE the node reads text: the node is the retained
//    space before a neighbour that begins with one (`<i>a</i> <b> b</b>` renders the node), and a no-break space or a zero-width
//    character ending the neighbour does not collapse it.
// Under `pre` nothing is skipped, the ancestors read (a code line's indentation under the per-line wrap is rendered white space).
// Every scene is driven through paintRendered from the paragraph before the block to the paragraph after, over marked with the one
// configuration (md-config.ts) and a DOM stand-in that keeps `&nbsp;` as U+00A0, with sibling pointers and on the index path.
// md-config-paint-collapsed-blank-browser.test.ts measures the same scenes over the real bundle in Chromium: each whitespace-only
// node's width before the paint decides, 0 px skipped, a width painted. Synthetic prose, no paths.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { paintRendered } from "./anchor-map";

applyMdConfig();

// ── a DOM stand-in with sibling pointers (a browser's Node offers them; one built without takes the paint's index path) ───────
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
  constructor(public ownerDocument: FakeDocument) {}
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
  kids: FakeNode[] = [];
  constructor(doc: FakeDocument, public tagName: string) { super(doc); }
  get childNodes(): FakeNode[] { return this.kids; }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  private relink(): void {
    for (let i = 0; i < this.kids.length; i++) {
      const c = this.kids[i];
      c.parentNode = this;
      if (this.ownerDocument.pointers) { c.previousSibling = this.kids[i - 1] ?? null; c.nextSibling = this.kids[i + 1] ?? null; }
    }
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
/** The entities marked's output holds: `&nbsp;` is a no-break space, U+00A0, as the HTML parser decodes it. */
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: "\u00a0" };
const decode = (s: string): string => s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => e[0] === "#" ? String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10)) : (e in NAMED ? NAMED[e] : m));
/** marked's HTML into the stand-in (anchor-map.test.ts's parser, cut to what the scenes here emit: elements with attributes, text). */
function parseHTML(doc: FakeDocument, html: string): FakeNode[] {
  const root = doc.createElement("#fragment");
  const stack: FakeElement[] = [root];
  const top = () => stack[stack.length - 1];
  let i = 0;
  while (i < html.length) {
    if (html[i] === "<") {
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
function buildRendered(text: string, pointers = true): FakeElement {
  const doc = new FakeDocument(pointers);
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);
  return box;
}
const El = (n: FakeNode) => n as unknown as Element;
/** The top level as rendered: each child's tag and class, or its text. */
const shape = (box: FakeElement): string[] => box.kids.map((n) => n.nodeType === 3 ? "#text(" + (n as FakeText).data + ")" : (n as FakeElement).tagName + "." + ((n as FakeElement).getAttribute("class") || ""));
/** The panel's unpaint (file-comments.ts): every mark's children back in its place, the parent's adjacent text nodes joined. */
function unpaintAll(box: FakeElement): void {
  const marks: FakeElement[] = [];
  const find = (n: FakeNode) => { for (const c of n.childNodes) { if (c.nodeType === 1) { if ((c as FakeElement).tagName === "MARK") marks.push(c as FakeElement); else find(c); } } };
  find(box);
  for (const m of marks) {
    const p = m.parentNode!;
    while (m.kids.length) p.insertBefore(m.kids[0], m);
    p.removeChild(m);
    for (let i = 0; i < p.kids.length - 1;) {
      const a = p.kids[i], b = p.kids[i + 1];
      if (a.nodeType === 3 && b.nodeType === 3) { (a as FakeText).data += (b as FakeText).data; p.removeChild(b); } else i++;
    }
  }
}
/** Whitespace-only as the browser lays it out: ASCII white space, the Unicode spaces and the zero-width format characters. */
const BLANK = /^[\s\u200b-\u200d\u2060-\u2064\ufeff]*$/;
const isBlank = (s: string): boolean => BLANK.test(s);
const wrap = (block: string): string => "Intro para.\n\n" + block + "\n\nAfter para.\n";
const acrossRange = (src: string): { start: number; end: number } => ({ start: src.indexOf("Intro para."), end: src.indexOf("After para.") + "After para.".length });
type Scene = [why: string, src: string, texts: string[]];
/** Paint the scene's range, hold the marks' text to `texts` (which names every whitespace-only mark the scene may have), no mark a
 *  top-level node; unpaint, and the top level is as rendered; repaint, the same marks. */
function drive(scene: Scene): void {
  const [why, src, texts] = scene;
  for (const pointers of [true, false]) {
    const what = why + (pointers ? "" : " (the index path, a stand-in without sibling pointers)");
    const box = buildRendered(src, pointers);
    const fresh = shape(box);
    const marks = paintRendered(El(box), src, acrossRange(src), "fc-hl") as unknown as FakeElement[] | null;
    assert.ok(marks && marks.length, what + ": painted: " + JSON.stringify(marks && marks.map((m) => m.textContent)));
    assert.deepEqual(marks!.map((m) => m.textContent), texts, what + ": the marks' text");
    for (const m of marks!) {
      assert.notEqual(m.parentNode, box, what + ": no mark is a top-level node (the block pairing reads the top-level children)");
      assert.ok(m.textContent.length, what + ": never an empty mark");
    }
    unpaintAll(box);
    assert.deepEqual(shape(box), fresh, what + ": unpainted, the top level as rendered");
    const again = paintRendered(El(box), src, acrossRange(src), "fc-hl") as unknown as FakeElement[];
    assert.deepEqual(again.map((m) => m.textContent), texts, what + ": the same marks on a repaint");
  }
}
/** Every whitespace-only text node below the top level, with its parent's tag. */
function blanks(box: FakeElement): Array<{ parent: string; data: string }> {
  const out: Array<{ parent: string; data: string }> = [];
  const visit = (n: FakeNode) => { for (const c of n.childNodes) { if (c.nodeType === 3) { if (isBlank((c as FakeText).data) && c.parentNode !== box) out.push({ parent: c.parentNode!.tagName, data: (c as FakeText).data }); } else visit(c); } };
  visit(box);
  return out;
}

const NBSP = "\u00a0", FEFF = "\ufeff", ZWSP = "\u200b";
const IMG_A = '<img src="a.png" alt="a">', IMG_B = '<img src="b.png" alt="b">';

// ── 1. zero-width format characters ─────────────────────────────────────────────────────────────────────────────────────────
const ZERO_WIDTH: Scene[] = [
  ["a lone U+FEFF under a div beside a paragraph (an html block)", wrap("<div>" + FEFF + "<p>x</p></div>"), ["Intro para.", "x", "After para."]],
  ["a lone U+FEFF in a list item", wrap("<ul><li>" + FEFF + "</li><li>two</li></ul>"), ["Intro para.", "two", "After para."]],
  ["a lone U+FEFF in a paragraph (main painted it there too)", wrap("<p>" + FEFF + "</p>"), ["Intro para.", "After para."]],
  ["a U+FEFF between two inline elements of a paragraph", wrap("<p><b>a</b>" + FEFF + "<i>b</i></p>"), ["Intro para.", "a", "b", "After para."]],
  ["a lone U+200B in a list item (not `\\s`: a positioned character of the mapping, and the box on main too)", wrap("<ul><li>" + ZWSP + "</li><li>two</li></ul>"), ["Intro para.", "two", "After para."]],
  ...["\u200b", "\u200c", "\u200d", "\u2060", "\u2062", "\u2064"].map((ch): Scene => ["a lone U+" + ch.codePointAt(0)!.toString(16) + " in a paragraph", wrap("<p>" + ch + "</p>"), ["Intro para.", "After para."]]),
];
/** A zero-width character beside white space, or in a node with it: a character, so the white space renders and is painted. */
const ZERO_WIDTH_RENDERED: Scene[] = [
  ["a node of U+FEFF and a space between two inline children of an item is text, painted", wrap("<ul><li><b>a</b>" + FEFF + " <i>b</i></li></ul>"), ["Intro para.", "a", FEFF + " ", "b", "After para."]],
  ["a neighbour ending in U+FEFF does not collapse the space after it", wrap("<ul><li><b>a" + FEFF + "</b> <i>b</i></li></ul>"), ["Intro para.", "a" + FEFF, " ", "b", "After para."]],
  ["a neighbour ending in a space then U+FEFF does not collapse the space after it (the character breaks the run)", wrap("<ul><li><b>a " + FEFF + "</b> <i>b</i></li></ul>"), ["Intro para.", "a " + FEFF, " ", "b", "After para."]],
  ["a nbsp alone in a paragraph is a rendered blank, painted (the control)", wrap("<p>&nbsp;</p>"), ["Intro para.", NBSP, "After para."]],
];

test("the fixtures hold the shapes: every zero-width scene has a text node of zero-width characters alone below the top level, U+FEFF is `\\s` and the others are not", () => {
  assert.ok(/^\s$/.test(FEFF), "U+FEFF is JavaScript's \\s (the mapping drops it from a block's characters)");
  for (const ch of ["\u200b", "\u200c", "\u200d", "\u2060", "\u2062", "\u2064"]) assert.ok(!/\s/.test(ch), "U+" + ch.codePointAt(0)!.toString(16) + " is not \\s (a positioned character of the mapping)");
  for (const [why, src] of ZERO_WIDTH) {
    const b = blanks(buildRendered(src));
    assert.ok(b.some((t) => /^[\u200b-\u200d\u2060-\u2064\ufeff]+$/.test(t.data)), why + ": a text node of zero-width characters alone below the top level: " + JSON.stringify(b));
  }
});

test("a highlight across a text node of zero-width format characters alone paints no mark for it, wherever it stands; a node mixing them with a space, or a space after a neighbour ending in one, is a rendered blank and is painted", () => {
  for (const scene of ZERO_WIDTH) drive(scene);
  for (const scene of ZERO_WIDTH_RENDERED) drive(scene);
});

test("a passage that is one zero-width character alone gets no highlight: the exact path wraps nothing and the fallback skips the same node (the comment keeps its card)", () => {
  for (const [why, ch] of [["U+200B, a positioned character", ZWSP], ["U+FEFF, dropped by the mapping's alphabet", FEFF]] as Array<[string, string]>) {
    const src = wrap("<p>" + ch + "</p>");
    const box = buildRendered(src);
    const at = src.indexOf(ch);
    assert.ok(at > 0, why + ": the source holds the character");
    assert.equal(paintRendered(El(box), src, { start: at, end: at + 1 }, "fc-hl"), null, why + ": no mark, no highlight");
  }
});

// ── 2. an inline element that renders nothing, between the node and the line's edge ─────────────────────────────────────────
const EMPTY_INLINE: Scene[] = [
  ["an anchor-led markdown item", wrap('- <a name="install"></a> **Install** the package'), ["Intro para.", "Install", " the package", "After para."]],
  ["an icon-led html item", wrap('<ul><li><i class="fa fa-check"></i> <b>Item</b> text</li></ul>'), ["Intro para.", "Item", " text", "After para."]],
  ["an anchor-led centred badge row: the newline after the anchor collapses, the one between the images renders",
   wrap('<div align="center">\n<a name="top"></a>\n' + IMG_A + "\n" + IMG_B + "\n</div>"), ["Intro para.", "\n", "After para."]],
  ["an id-anchor-led div", wrap('<div><a id="sec"></a> <b>Section</b> text</div>'), ["Intro para.", "Section", " text", "After para."]],
  ["an anchor-led html blockquote", wrap('<blockquote><a name="q"></a> <b>quote</b> text</blockquote>'), ["Intro para.", "quote", " text", "After para."]],
  ["an empty span leading an item", wrap('<ul><li><span></span> <a href="#x">Link</a></li></ul>'), ["Intro para.", "Link", "After para."]],
  ["an empty sup leading an item", wrap("<ul><li><sup></sup> <b>x</b></li></ul>"), ["Intro para.", "x", "After para."]],
  ["an empty code span leading an item (padding, but no box of its own)", wrap("<ul><li><code></code> <b>x</b></li></ul>"), ["Intro para.", "x", "After para."]],
  ["a hidden span leading an item (display none; its own text is wrapped, invisibly)", wrap("<ul><li><span hidden>h</span> <b>x</b></li></ul>"), ["Intro para.", "h", "x", "After para."]],
  ["an anchor closing an item", wrap('<ul><li><b>a</b> <a name="end"></a></li></ul>'), ["Intro para.", "a", "After para."]],
  ["an anchor between two inline children: the space before it renders, the one after it collapses", wrap('- **a** <a name="m"></a> *b*'), ["Intro para.", "a", " ", "b", "After para."]],
  ["an empty anchor nested in a bold", wrap('<ul><li><b><a name="x"></a></b> <i>y</i></li></ul>'), ["Intro para.", "y", "After para."]],
  ["an empty link then an image (the line's leading white space)", wrap('<ul><li><a href="#x"></a> ' + IMG_A + "</li></ul>"), ["Intro para.", "After para."]],
  ["an anchor-led table cell", wrap('<table><tr><td><a name="c"></a> <b>x</b></td></tr></table>'), ["Intro para.", "x", "After para."]],
  ["an anchor-led paragraph (main painted the box there too)", wrap('<p><a name="p"></a> <b>para</b> text</p>'), ["Intro para.", "para", " text", "After para."]],
  ["a space leading an inline element at its paragraph's start", wrap("<p><em> <b>a</b></em> tail</p>"), ["Intro para.", "a", " tail", "After para."]],
  ["a space closing an inline element at its paragraph's end", wrap("<p>head <em><b>a</b> </em></p>"), ["Intro para.", "head ", "a", "After para."]],
  ["a block inside an inline after the space splits the line", wrap("<ul><li><b>a</b> <span><p>x</p></span></li></ul>"), ["Intro para.", "a", "x", "After para."]],
  ["a block inside an inline before the space", wrap("<ul><li><span><p>x</p></span> <b>a</b></li></ul>"), ["Intro para.", "x", "a", "After para."]],
];
/** Atomic inlines and the rest: the space beside them renders and is painted. */
const EMPTY_INLINE_RENDERED: Scene[] = [
  ["an empty kbd, an inline-block with a border, is a box: the space after it renders", wrap("<ul><li><kbd></kbd> <b>x</b></li></ul>"), ["Intro para.", " ", "x", "After para."]],
  ["a span hidden until-found renders as if the attribute were absent", wrap('<ul><li><span hidden="until-found">h</span> <b>x</b></li></ul>'), ["Intro para.", "h", " ", "x", "After para."]],
  ["a task item: the space after its checkbox", wrap("- [ ] **a** *b*"), ["Intro para.", " ", "a", " ", "b", "After para."]],
  ["a space between two inline children of an inline parent", wrap("<p><em><b>a</b> <i>b</i></em></p>"), ["Intro para.", "a", " ", "b", "After para."]],
  ["a badge row's space between two linked images", wrap('<div align="center"><a href="#a">' + IMG_A + '</a> <a href="#b">' + IMG_B + "</a></div>"), ["Intro para.", " ", "After para."]],
];

test("the fixtures hold the shapes: each empty-inline scene has a whitespace-only text node below the top level beside an element", () => {
  for (const [why, src] of [...EMPTY_INLINE, ...EMPTY_INLINE_RENDERED]) {
    const b = blanks(buildRendered(src));
    assert.ok(b.some((t) => /^[ \t\n\r\f]+$/.test(t.data)), why + ": a whitespace-only text node of ASCII white space below the top level: " + JSON.stringify(b));
  }
});

test("a highlight across an item, a div, a blockquote or a cell led or closed by an inline element that renders nothing paints no mark for the collapsed space beside it, through inline ancestors and past nested empties; beside an atomic inline or a rendered element the space is painted", () => {
  for (const scene of EMPTY_INLINE) drive(scene);
  for (const scene of EMPTY_INLINE_RENDERED) drive(scene);
});

// ── 3. a neighbour whose text ends with collapsible white space ─────────────────────────────────────────────────────────────
const TRAILING_SPACE: Scene[] = [
  ["a bold ending with a space in an item", wrap("<ul><li><b>Label: </b> <i>value</i></li></ul>"), ["Intro para.", "Label: ", "value", "After para."]],
  ["a markdown link whose text ends with a space", wrap("- [docs ](#a) *x*"), ["Intro para.", "docs ", "x", "After para."]],
  ["a bold ending with a space, a newline between, in a div", wrap("<div><b>a </b>\n<i>b</i></div>"), ["Intro para.", "a ", "b", "After para."]],
  ["a code span ending with a space in a blockquote", wrap("<blockquote><code>x </code> <i>b</i></blockquote>"), ["Intro para.", "x ", "b", "After para."]],
  ["the trailing space nested two inlines deep", wrap("<ul><li><b><i>x </i></b> <em>y</em></li></ul>"), ["Intro para.", "x ", "y", "After para."]],
  ["a line break closing the neighbour", wrap("<ul><li><b>x<br></b> <i>y</i></li></ul>"), ["Intro para.", "x", "y", "After para."]],
  ["the trailing space read through an empty anchor between", wrap('<ul><li><b>a </b><a name="z"></a> <i>x</i></li></ul>'), ["Intro para.", "a ", "x", "After para."]],
  ["a whitespace-only node inside the neighbour is the retained space; the node after the neighbour collapses", wrap("<ul><li><b>a<i> </i></b> <em>y</em></li></ul>"), ["Intro para.", "a", " ", "y", "After para."]],
  ["two whitespace-only siblings around an empty span: the first renders, the second collapses", wrap("<ul><li><b>a</b> <span></span> <i>b</i></li></ul>"), ["Intro para.", "a", " ", "b", "After para."]],
  ["a bold ending with a space in a paragraph (main painted the box there too)", wrap("<p><b>Label: </b> <i>value</i></p>"), ["Intro para.", "Label: ", "value", "After para."]],
];
const TRAILING_SPACE_RENDERED: Scene[] = [
  ["the next neighbour begins with a space: the node is the retained one", wrap("<ul><li><i>a</i> <b> b</b></li></ul>"), ["Intro para.", "a", " ", " b", "After para."]],
  ["a neighbour ending with a no-break space", wrap("<ul><li><b>a&nbsp;</b> <i>b</i></li></ul>"), ["Intro para.", "a" + NBSP, " ", "b", "After para."]],
  ["a neighbour ending with an image after its space", wrap("<ul><li><b>a " + IMG_A + "</b> <i>x</i></li></ul>"), ["Intro para.", "a ", " ", "x", "After para."]],
  ["plain neighbours, the space between them", wrap("<ul><li><b>a</b> <i>b</i></li></ul>"), ["Intro para.", "a", " ", "b", "After para."]],
  ["a kbd ending with a space is an inline-block: its inside is another line, the space after it renders", wrap("<ul><li><kbd>Ctrl </kbd> <b>x</b></li></ul>"), ["Intro para.", "Ctrl ", " ", "x", "After para."]],
  ["under pre nothing collapses", wrap("<pre><b>a </b> <i>b</i></pre>"), ["Intro para.", "a ", " ", "b", "After para."]],
  ["a code line's indentation under the viewer's per-line wrap, deep in a pre, is rendered white space", wrap('<pre><code><span class="cl"><span class="ct">  <b>if</b> x</span></span></code></pre>'), ["Intro para.", "  ", "if", " x", "After para."]],
];

test("the fixtures hold the shapes: each trailing-space scene has a whitespace-only node whose nearest text before it ends with collapsible white space or a line break, and each rendered control has one that does not", () => {
  for (const [why, src] of TRAILING_SPACE) {
    const b = blanks(buildRendered(src));
    assert.ok(b.some((t) => /^[ \t\n\r\f]+$/.test(t.data)), why + ": a whitespace-only text node below the top level: " + JSON.stringify(b));
  }
  for (const [why, src] of TRAILING_SPACE_RENDERED) {
    const b = blanks(buildRendered(src));
    assert.ok(b.some((t) => /^[ \t\n\r\f]+$/.test(t.data)), why + ": a whitespace-only text node below the top level: " + JSON.stringify(b));
  }
});

test("a highlight across an item, a div or a blockquote whose inline child ends with collapsible white space paints no mark for the collapsed node after it; the node before a neighbour beginning with a space, after a no-break space, an image or a kbd, and everything under pre is painted", () => {
  for (const scene of TRAILING_SPACE) drive(scene);
  for (const scene of TRAILING_SPACE_RENDERED) drive(scene);
});
