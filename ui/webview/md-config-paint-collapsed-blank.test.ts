// The comments painter's DOM shape over the blank scenes the Slice 4 review collected (rounds 7 to 12): a run of zero-width
// format characters, a space beside an inline element that renders nothing or beside an atomic inline, a space after a neighbour
// whose text ends with one, indentation and block children under pre, a form feed, an svg icon, an audio element. Since round 12
// the painter predicts nothing about which of these blanks the browser collapses: it paints the text nodes of its range below
// the render root (the root guard and the block-neighbour pre-skip, skipBlockWs's header in anchor-map.ts, are the DOM-side skips
// left), and the browser's own layout decides afterwards (anchor-map.ts, the layout-time trim: a mark whose text is blank and
// lays out at zero width is unwrapped; the Comments panel measures its standing marks again on the seam's reflow, file-comments.ts
// trimBlanks, since the seam re-places the cards on a reflow and does not repaint). This DOM stand-in has
// no layout, so the trim measures nothing here and a blank the DOM-side skips leave in the range carries a mark; which blank
// marks the browser keeps is the browser leg's question (md-config-paint-collapsed-blank-browser.test.ts, the real bundle in
// Chromium). This file pins the shape that holds whatever layout decides, over every scene, with sibling pointers and on the
// index path:
// 1. No mark is a top-level child of the render root, and the top level stays as rendered while painted (the block pairing reads
//    the top-level children; the white space between blocks is the root guard's subject, a zero-width run there too).
// 2. Never an empty mark.
// 3. The marks' text, the blank marks set aside, is exactly the passage from the paragraph before to the paragraph after.
// 4. The panel's unpaint restores the top level as rendered, and a repaint gives the same marks.
// Each test's title says what its body checks and no more (the round 12 review: round 11's fixture tests here claimed a reading
// of each blank's neighbour that their bodies never made). Synthetic prose, no paths.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { paintRendered } from "./anchor-map";
import { hideEdges, defineHidden } from "../test-dom-shim";

applyMdConfig();

// ── a DOM stand-in with sibling pointers (a browser's Node offers them; one built without takes the paint's index path) ───────
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
  kids: FakeNode[] = [];
  constructor(doc: FakeDocument, public tagName: string) { super(doc); hideEdges(this); }
  get childNodes(): FakeNode[] { return this.kids; }
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
/** Blank to the trim: JavaScript's `\s` (ASCII white space, the Unicode spaces, U+FEFF) plus the zero-width format characters
 *  U+200B to U+200D and U+2060 to U+2064. */
const BLANK = /^[\s\u200b-\u200d\u2060-\u2064]*$/;
const isBlank = (s: string): boolean => BLANK.test(s);
const ASCII_WS = /^[ \t\n\r\f]+$/;
const ZERO_WIDTH_RUN = /^[\u200b-\u200d\u2060-\u2064\ufeff]+$/;
const wrap = (block: string): string => "Intro para.\n\n" + block + "\n\nAfter para.\n";
const acrossRange = (src: string): { start: number; end: number } => ({ start: src.indexOf("Intro para."), end: src.indexOf("After para.") + "After para.".length });
/** A scene: the shape, the markdown, and the passage's text as the marks hold it once the blank marks are set aside. */
type Scene = [why: string, src: string, content: string[]];
/** Paint the scene's range from the paragraph before to the paragraph after and hold the DOM shape: the marks' text, blank marks
 *  set aside, is `content`; no mark is empty or a top-level node and the top level is as rendered while painted; unpaint, and
 *  the top level is as rendered; repaint, the same marks, blank marks included. */
function drive(scene: Scene): void {
  const [why, src, content] = scene;
  for (const pointers of [true, false]) {
    const what = why + (pointers ? "" : " (the index path, a stand-in without sibling pointers)");
    const box = buildRendered(src, pointers);
    const fresh = shape(box);
    const marks = paintRendered(El(box), src, acrossRange(src), "fc-hl") as unknown as FakeElement[] | null;
    assert.ok(marks && marks.length, what + ": painted: " + JSON.stringify(marks && marks.map((m) => m.textContent)));
    const texts = marks!.map((m) => m.textContent);
    assert.deepEqual(texts.filter((t) => !isBlank(t)), content, what + ": the marks' text, the blank marks set aside: " + JSON.stringify(texts));
    for (const m of marks!) {
      assert.notEqual(m.parentNode, box, what + ": no mark is a top-level node (the block pairing reads the top-level children)");
      assert.ok(m.textContent.length, what + ": never an empty mark");
    }
    assert.deepEqual(shape(box), fresh, what + ": painted, the top level as rendered (no mark and no split text node there)");
    unpaintAll(box);
    assert.deepEqual(shape(box), fresh, what + ": unpainted, the top level as rendered");
    const again = paintRendered(El(box), src, acrossRange(src), "fc-hl") as unknown as FakeElement[];
    assert.deepEqual(again.map((m) => m.textContent), texts, what + ": the same marks on a repaint");
  }
}
/** Every blank-only text node below the top level, with its parent's tag. */
function blanks(box: FakeElement): Array<{ parent: string; data: string }> {
  const out: Array<{ parent: string; data: string }> = [];
  const visit = (n: FakeNode) => { for (const c of n.childNodes) { if (c.nodeType === 3) { if (isBlank((c as FakeText).data) && c.parentNode !== box) out.push({ parent: c.parentNode!.tagName, data: (c as FakeText).data }); } else visit(c); } };
  visit(box);
  return out;
}
/** The fixture check every scene passes: whitespace-only text at the top level (the root guard's subject) and a blank-only text
 *  node below it whose text matches `run` (the node layout decides). */
function holdsShape(scene: Scene, run: RegExp): void {
  const [why, src] = scene;
  const box = buildRendered(src);
  assert.ok(box.kids.some((n) => n.nodeType === 3 && /^\s+$/.test((n as FakeText).data)), why + ": whitespace-only text at the top level: " + JSON.stringify(shape(box)));
  const b = blanks(box);
  assert.ok(b.some((t) => run.test(t.data)), why + ": a blank-only text node below the top level matching " + run + ": " + JSON.stringify(b));
}

const NBSP = "\u00a0", FEFF = "\ufeff", ZWSP = "\u200b";
const ZERO_WIDTH_CHARS = ["\u200b", "\u200c", "\u200d", "\u2060", "\u2061", "\u2062", "\u2063", "\u2064"];
const IMG_A = '<img src="a.png" alt="a">', IMG_B = '<img src="b.png" alt="b">';

// ── 1. zero-width format characters: a run alone, one beside a space, one ending a neighbour ────────────────────────────────
//    (the browser leg: a run alone measures 0 px wherever it stands and its mark is trimmed; a space beside one renders)
const ZERO_WIDTH: Scene[] = [
  ["a lone U+FEFF under a div beside a paragraph (an html block)", wrap("<div>" + FEFF + "<p>x</p></div>"), ["Intro para.", "x", "After para."]],
  ["a lone U+FEFF in a list item", wrap("<ul><li>" + FEFF + "</li><li>two</li></ul>"), ["Intro para.", "two", "After para."]],
  ["a lone U+FEFF in a paragraph", wrap("<p>" + FEFF + "</p>"), ["Intro para.", "After para."]],
  ["a U+FEFF between two inline elements of a paragraph", wrap("<p><b>a</b>" + FEFF + "<i>b</i></p>"), ["Intro para.", "a", "b", "After para."]],
  ["a lone U+200B in a list item (not `\\s`: a positioned character of the mapping)", wrap("<ul><li>" + ZWSP + "</li><li>two</li></ul>"), ["Intro para.", "two", "After para."]],
  ...ZERO_WIDTH_CHARS.map((ch): Scene => ["a lone U+" + ch.codePointAt(0)!.toString(16) + " in a paragraph", wrap("<p>" + ch + "</p>"), ["Intro para.", "After para."]]),
  ["a node of U+FEFF and a space between two inline children of an item", wrap("<ul><li><b>a</b>" + FEFF + " <i>b</i></li></ul>"), ["Intro para.", "a", "b", "After para."]],
  ["a neighbour ending in U+FEFF, a space after it", wrap("<ul><li><b>a" + FEFF + "</b> <i>b</i></li></ul>"), ["Intro para.", "a" + FEFF, "b", "After para."]],
  ["a neighbour ending in a space then U+FEFF, a space after it", wrap("<ul><li><b>a " + FEFF + "</b> <i>b</i></li></ul>"), ["Intro para.", "a " + FEFF, "b", "After para."]],
  ["a nbsp alone in a paragraph", wrap("<p>&nbsp;</p>"), ["Intro para.", "After para."]],
];

// ── 2. white space beside an inline element that renders nothing, or beside an atomic inline ────────────────────────────────
//    (the browser leg: the line's leading or trailing space beside an empty anchor, span, sup or code, or a hidden element,
//    measures 0 px and its mark is trimmed; beside an image, a checkbox, an empty kbd, a rendered element, the space renders)
const EMPTY_INLINE: Scene[] = [
  ["an anchor-led markdown item", wrap('- <a name="install"></a> **Install** the package'), ["Intro para.", "Install", " the package", "After para."]],
  ["an icon-led html item", wrap('<ul><li><i class="fa fa-check"></i> <b>Item</b> text</li></ul>'), ["Intro para.", "Item", " text", "After para."]],
  ["an anchor-led centred badge row, a newline after the anchor and one between the images",
   wrap('<div align="center">\n<a name="top"></a>\n' + IMG_A + "\n" + IMG_B + "\n</div>"), ["Intro para.", "After para."]],
  ["an id-anchor-led div", wrap('<div><a id="sec"></a> <b>Section</b> text</div>'), ["Intro para.", "Section", " text", "After para."]],
  ["an anchor-led html blockquote", wrap('<blockquote><a name="q"></a> <b>quote</b> text</blockquote>'), ["Intro para.", "quote", " text", "After para."]],
  ["an empty span leading an item", wrap('<ul><li><span></span> <a href="#x">Link</a></li></ul>'), ["Intro para.", "Link", "After para."]],
  ["an empty sup leading an item", wrap("<ul><li><sup></sup> <b>x</b></li></ul>"), ["Intro para.", "x", "After para."]],
  ["an empty code span leading an item", wrap("<ul><li><code></code> <b>x</b></li></ul>"), ["Intro para.", "x", "After para."]],
  ["a hidden span leading an item (its own text is in the range)", wrap("<ul><li><span hidden>h</span> <b>x</b></li></ul>"), ["Intro para.", "h", "x", "After para."]],
  ["an anchor closing an item", wrap('<ul><li><b>a</b> <a name="end"></a></li></ul>'), ["Intro para.", "a", "After para."]],
  ["an anchor between two inline children, a space on each side", wrap('- **a** <a name="m"></a> *b*'), ["Intro para.", "a", "b", "After para."]],
  ["an empty anchor nested in a bold", wrap('<ul><li><b><a name="x"></a></b> <i>y</i></li></ul>'), ["Intro para.", "y", "After para."]],
  ["an empty link, a space, then an image", wrap('<ul><li><a href="#x"></a> ' + IMG_A + "</li></ul>"), ["Intro para.", "After para."]],
  ["an anchor-led table cell", wrap('<table><tr><td><a name="c"></a> <b>x</b></td></tr></table>'), ["Intro para.", "x", "After para."]],
  ["an anchor-led paragraph", wrap('<p><a name="p"></a> <b>para</b> text</p>'), ["Intro para.", "para", " text", "After para."]],
  ["a space leading an inline element at its paragraph's start", wrap("<p><em> <b>a</b></em> tail</p>"), ["Intro para.", "a", " tail", "After para."]],
  ["a space closing an inline element at its paragraph's end", wrap("<p>head <em><b>a</b> </em></p>"), ["Intro para.", "head ", "a", "After para."]],
  ["a block inside an inline after the space", wrap("<ul><li><b>a</b> <span><p>x</p></span></li></ul>"), ["Intro para.", "a", "x", "After para."]],
  ["a block inside an inline before the space", wrap("<ul><li><span><p>x</p></span> <b>a</b></li></ul>"), ["Intro para.", "x", "a", "After para."]],
  ["an empty kbd, a space after it", wrap("<ul><li><kbd></kbd> <b>x</b></li></ul>"), ["Intro para.", "x", "After para."]],
  ["a span hidden until-found, a space after it", wrap('<ul><li><span hidden="until-found">h</span> <b>x</b></li></ul>'), ["Intro para.", "h", "x", "After para."]],
  ["a task item, a space after its checkbox", wrap("- [ ] **a** *b*"), ["Intro para.", "a", "b", "After para."]],
  ["a space between two inline children of an inline parent", wrap("<p><em><b>a</b> <i>b</i></em></p>"), ["Intro para.", "a", "b", "After para."]],
  ["a badge row's space between two linked images", wrap('<div align="center"><a href="#a">' + IMG_A + '</a> <a href="#b">' + IMG_B + "</a></div>"), ["Intro para.", "After para."]],
];

// ── 3. white space after a neighbour whose text ends with collapsible white space, and under pre ───────────────────────────
//    (the browser leg: the space after `<b>Label: </b>` measures 0 px and its mark is trimmed; the space before a neighbour that
//    begins with one, after a no-break space, an image or a kbd, and everything under pre renders)
const TRAILING_SPACE: Scene[] = [
  ["a bold ending with a space in an item", wrap("<ul><li><b>Label: </b> <i>value</i></li></ul>"), ["Intro para.", "Label: ", "value", "After para."]],
  ["a markdown link whose text ends with a space", wrap("- [docs ](#a) *x*"), ["Intro para.", "docs ", "x", "After para."]],
  ["a bold ending with a space, a newline between, in a div", wrap("<div><b>a </b>\n<i>b</i></div>"), ["Intro para.", "a ", "b", "After para."]],
  ["a code span ending with a space in a blockquote", wrap("<blockquote><code>x </code> <i>b</i></blockquote>"), ["Intro para.", "x ", "b", "After para."]],
  ["the trailing space nested two inlines deep", wrap("<ul><li><b><i>x </i></b> <em>y</em></li></ul>"), ["Intro para.", "x ", "y", "After para."]],
  ["a line break closing the neighbour", wrap("<ul><li><b>x<br></b> <i>y</i></li></ul>"), ["Intro para.", "x", "y", "After para."]],
  ["the trailing space with an empty anchor between", wrap('<ul><li><b>a </b><a name="z"></a> <i>x</i></li></ul>'), ["Intro para.", "a ", "x", "After para."]],
  ["a whitespace-only node inside the neighbour and one after it", wrap("<ul><li><b>a<i> </i></b> <em>y</em></li></ul>"), ["Intro para.", "a", "y", "After para."]],
  ["two whitespace-only siblings around an empty span", wrap("<ul><li><b>a</b> <span></span> <i>b</i></li></ul>"), ["Intro para.", "a", "b", "After para."]],
  ["a bold ending with a space in a paragraph", wrap("<p><b>Label: </b> <i>value</i></p>"), ["Intro para.", "Label: ", "value", "After para."]],
  ["the next neighbour begins with a space", wrap("<ul><li><i>a</i> <b> b</b></li></ul>"), ["Intro para.", "a", " b", "After para."]],
  ["a neighbour ending with a no-break space", wrap("<ul><li><b>a&nbsp;</b> <i>b</i></li></ul>"), ["Intro para.", "a" + NBSP, "b", "After para."]],
  ["a neighbour ending with an image after its space", wrap("<ul><li><b>a " + IMG_A + "</b> <i>x</i></li></ul>"), ["Intro para.", "a ", "x", "After para."]],
  ["plain neighbours, the space between them", wrap("<ul><li><b>a</b> <i>b</i></li></ul>"), ["Intro para.", "a", "b", "After para."]],
  ["a kbd ending with a space, a space after it", wrap("<ul><li><kbd>Ctrl </kbd> <b>x</b></li></ul>"), ["Intro para.", "Ctrl ", "x", "After para."]],
  ["a bold ending with a space under pre, a space after it", wrap("<pre><b>a </b> <i>b</i></pre>"), ["Intro para.", "a ", "b", "After para."]],
  ["a code line's indentation under the viewer's per-line wrap, deep in a pre", wrap('<pre><code><span class="cl"><span class="ct">  <b>if</b> x</span></span></code></pre>'), ["Intro para.", "if", " x", "After para."]],
];

// ── 4. the shapes round 12's review added (the browser leg measures each; here the DOM shape alone) ────────────────────────
const ROUND_12: Scene[] = [
  ["an inline svg icon leading an item, a space after it", wrap('<ul><li><svg width="16" height="16" viewBox="0 0 16 16"><circle cx="8" cy="8" r="8"/></svg> <b>x</b></li></ul>'), ["Intro para.", "x", "After para."]],
  ["an audio element without controls, a space after it", wrap('<ul><li><audio src="a.mp3"></audio> <b>x</b></li></ul>'), ["Intro para.", "x", "After para."]],
  ["an audio element with controls, a space after it", wrap('<ul><li><audio controls src="a.mp3"></audio> <b>x</b></li></ul>'), ["Intro para.", "x", "After para."]],
  ["an author pre with a newline between two br elements", wrap("<pre>a<br>\n<br>b</pre>"), ["Intro para.", "a", "b", "After para."]],
  ["an author pre with a newline between two block children", wrap("<pre><div>a</div>\n<div>b</div></pre>"), ["Intro para.", "a", "b", "After para."]],
  ["a form feed alone between two inline children of a paragraph", wrap("<p><b>a</b>\f<i>b</i></p>"), ["Intro para.", "a", "b", "After para."]],
  ["a CRLF between two inline children of an item", wrap("<ul><li><b>a</b>\r\n<i>b</i></li></ul>"), ["Intro para.", "a", "b", "After para."]],
  ["an ideographic space alone between two inline children of a paragraph", wrap("<p><b>a</b>\u3000<i>b</i></p>"), ["Intro para.", "a", "b", "After para."]],
];

test("the fixtures hold the shapes: every scene has whitespace-only text at the top level and a blank-only text node below it, a zero-width run in the zero-width scenes and ASCII white space in the empty-inline and trailing-space ones; U+FEFF is `\\s` and the other zero-width characters are not", () => {
  assert.ok(/^\s$/.test(FEFF), "U+FEFF is JavaScript's \\s (the mapping drops it from a block's characters)");
  for (const ch of ZERO_WIDTH_CHARS) assert.ok(!/\s/.test(ch), "U+" + ch.codePointAt(0)!.toString(16) + " is not \\s (a positioned character of the mapping)");
  assert.deepEqual(ZERO_WIDTH_CHARS.map((c) => c.codePointAt(0)), [0x200b, 0x200c, 0x200d, 0x2060, 0x2061, 0x2062, 0x2063, 0x2064], "every zero-width character of the trim's alphabet has a scene");
  for (let i = 0; i < ZERO_WIDTH.length; i++) holdsShape(ZERO_WIDTH[i], i < 5 + ZERO_WIDTH_CHARS.length ? ZERO_WIDTH_RUN : BLANK);
  for (const scene of [...EMPTY_INLINE, ...TRAILING_SPACE]) holdsShape(scene, ASCII_WS);
  for (const scene of ROUND_12) holdsShape(scene, BLANK);
});

test("a highlight across a text node of zero-width format characters, or a space beside one, paints the passage's text with no top-level mark and no empty mark, the top level as rendered while painted and after the unpaint, and the same marks on a repaint", () => {
  for (const scene of ZERO_WIDTH) drive(scene);
});

test("a highlight across an item, a div, a blockquote, a cell or a paragraph with a space beside an inline element that renders nothing, or beside an atomic inline, paints the passage's text with no top-level mark and no empty mark, the top level as rendered while painted and after the unpaint, and the same marks on a repaint", () => {
  for (const scene of EMPTY_INLINE) drive(scene);
});

test("a highlight across a block whose inline child ends with collapsible white space, or with a space beside a nbsp, an image or a kbd, or under pre, paints the passage's text with no top-level mark and no empty mark, the top level as rendered while painted and after the unpaint, and the same marks on a repaint", () => {
  for (const scene of TRAILING_SPACE) drive(scene);
});

test("a highlight across an svg icon, an audio element, an author pre with br or block children, a form feed, a CRLF or an ideographic space paints the passage's text with no top-level mark and no empty mark, the top level as rendered while painted and after the unpaint, and the same marks on a repaint", () => {
  for (const scene of ROUND_12) drive(scene);
});

// ── the root guard's alphabet: a zero-width run AT the top level ──────────────────────────────────────────────────────────────
// An html block with a zero width space between two tags (`<p>x</p>` U+200B `<p>y</p>`, pasted from a web page) leaves a text
// node of U+200B alone directly under the render root. The root guard skips the white space between blocks so that no mark is
// ever a top-level child (the block pairing reads the top-level children); a zero-width run there is the same node to the
// pairing and must be skipped the same way, whatever `\s` says of the character (U+FEFF is `\s`, U+200B is not). Before round
// 12 the guard read `\s` alone and painted the U+200B as a top-level mark, the sheet's padding around nothing on a line of its
// own between the two paragraphs (the round 11 review's seed for round 12).
test("a text node of one zero-width character alone at the top level, between two tags of an html block, gets no mark: no mark is a top-level node and the top level is as rendered while painted, for U+200B as for U+FEFF", () => {
  for (const [why, ch] of [["U+200B, not `\\s`", ZWSP], ["U+FEFF, `\\s`", FEFF]] as Array<[string, string]>) {
    for (const pointers of [true, false]) {
      const what = why + (pointers ? "" : " (the index path)");
      const src = wrap("<p>x</p>" + ch + "<p>y</p>");
      const box = buildRendered(src, pointers);
      const fresh = shape(box);
      assert.ok(box.kids.some((n) => n.nodeType === 3 && (n as FakeText).data === ch), what + ": the fixture holds the character as a top-level text node: " + JSON.stringify(fresh));
      const marks = paintRendered(El(box), src, acrossRange(src), "fc-hl") as unknown as FakeElement[] | null;
      assert.ok(marks && marks.length, what + ": painted");
      assert.deepEqual(marks!.map((m) => m.textContent).filter((t) => !isBlank(t)), ["Intro para.", "x", "y", "After para."], what + ": the marks' text, the blank marks set aside");
      for (const m of marks!) assert.notEqual(m.parentNode, box, what + ": no mark is a top-level node: " + JSON.stringify(m.textContent));
      assert.deepEqual(shape(box), fresh, what + ": painted, the top level as rendered");
      unpaintAll(box);
      assert.deepEqual(shape(box), fresh, what + ": unpainted, the top level as rendered");
    }
  }
});
