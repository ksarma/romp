// A rendered blank under a highlight is painted; a collapsed one is not. skipBlockWs (anchor-map.ts) skips a text node of white
// space between blocks so that no mark rings an empty box, and two readings of "white space" went wrong in the same function
// (the Slice 4 review, round 10):
// 1. Whitespace-only was JavaScript's `\s`, which matches a no-break space (U+00A0) and an ideographic space (U+3000) besides the
//    ASCII five; the browser collapses HTML's ASCII white space alone (space, tab, line feed, form feed, carriage return) and
//    renders every other space as a glyph of its own width. Round 9's readings (a block box or a `<br>` beside the node; the
//    edge of a block-level parent) so unpainted the `&nbsp;` spacer cell of a table, a `<p>&nbsp;</p>` spacer, a nbsp before a
//    paragraph's first inline element or alone between two `<br>`s and a paragraph's full-width indent, each a visible 7.89 x 16
//    (18 x 16) px mark on main and at round 8. Whitespace-only is now the collapsible set (isCollapsibleWs); a node of rendered
//    spaces is the passage's text wherever it stands, so `<div>&nbsp;</div>` and `<li>&nbsp;</li>`, which main's container rule
//    skipped, paint too (a blank line the note renders).
// 2. Main's first reading skipped any whitespace-only node whose PARENT was one of twelve block containers (UL, OL, LI,
//    BLOCKQUOTE, DIV, TABLE, THEAD, TBODY, TR, SECTION, ARTICLE, BODY; TD never among them, so the spacer cell of point 1
//    painted on main), whatever its neighbours, so the rendered space between two inline children of a list item
//    (`- **a** *b*`, a task item's after its checkbox), a centred badge row, an html blockquote or a section was never painted
//    and the highlight ring broke at it: two ringed boxes with a 4.75 px bare gap under the viewer's sheet, on main too. The
//    neighbour and edge readings cover every block-child case the list covered, so the list is gone; what stays is a guard for
//    the render root alone (its white space is the block pairing's, never the passage's: a mark there would be a top-level
//    node the next paint's pairing meets).
// Every scene is driven through paintRendered from the paragraph before the block to the paragraph after, over marked with the
// one configuration (md-config.ts) and a DOM stand-in that keeps `&nbsp;` as U+00A0 (the sibling files' stand-ins decode it to a
// plain space and cannot see the distinction). md-config-paint-rendered-space-browser.test.ts measures the same scenes over the
// real bundle in Chromium: the blank's rendered width before the paint, the mark after, the layout box for box unchanged.
// Synthetic prose, no paths.
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
/** The entities marked's output holds: `&nbsp;` is a no-break space, U+00A0, as the HTML parser decodes it (the point of the file). */
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
const isWsOnly = (s: string): boolean => /^\s*$/.test(s);
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

// ── 1. rendered spaces at the skip readings' positions ───────────────────────────────────────────────────────────────────────
const NBSP = "\u00a0", IDEO = "\u3000";
const RENDERED: Scene[] = [
  ["a nbsp alone in a paragraph, a spacer (the parent's edge on both sides)", wrap("<p>&nbsp;</p>"), ["Intro para.", NBSP, "After para."]],
  ["a nbsp spacer cell in an html table (the cell's edge)", wrap("<table><tr><td>&nbsp;</td><td>x</td></tr></table>"), ["Intro para.", NBSP, "x", "After para."]],
  ["a nbsp spacer cell in a markdown table", wrap("| a | b |\n|---|---|\n| &nbsp; | x |"), ["Intro para.", "a", "b", NBSP, "x", "After para."]],
  ["a nbsp before a paragraph's first inline element, html", wrap("<p>&nbsp;<b>bold</b> tail</p>"), ["Intro para.", NBSP, "bold", " tail", "After para."]],
  ["a nbsp entity before a paragraph's first inline element, markdown", wrap("&nbsp;**bold** tail"), ["Intro para.", NBSP, "bold", " tail", "After para."]],
  ["a nbsp alone on a line between two line breaks", wrap("line one<br>\n&nbsp;<br>\nline three"), ["Intro para.", "line one", "\n" + NBSP, "\nline three", "After para."]],
  ["an ideographic space indenting a paragraph, html", wrap("<p>" + IDEO + "<b>x</b> tail</p>"), ["Intro para.", IDEO, "x", " tail", "After para."]],
  ["an ideographic space indenting a paragraph, markdown", wrap(IDEO + "**x** tail"), ["Intro para.", IDEO, "x", " tail", "After para."]],
  ["a nbsp beside a block box at a div's edge (main's container rule and round 9's edge reading both skipped it)", wrap("<div>&nbsp;<p>x</p></div>"), ["Intro para.", NBSP, "x", "After para."]],
  ["a nbsp alone in a div, a blank line the note renders (main's container rule skipped it: the change in the other direction)", wrap("<div>&nbsp;</div>"), ["Intro para.", NBSP, "After para."]],
  ["a nbsp alone in a list item (the same)", wrap("<ul><li>&nbsp;</li><li>two</li></ul>"), ["Intro para.", NBSP, "two", "After para."]],
];
/** The other side: collapsible white space at the same positions renders nothing and is skipped, as round 9 left it. */
const COLLAPSED: Scene[] = [
  ["a space alone in a paragraph", wrap("<p> </p>"), ["Intro para.", "After para."]],
  ["a tab alone in a paragraph", wrap("<p>\t</p>"), ["Intro para.", "After para."]],
  ["a form feed alone in a paragraph", wrap("<p>\f</p>"), ["Intro para.", "After para."]],
  ["a newline alone in a cell", wrap("<table><tr><td>\n</td><td>x</td></tr></table>"), ["Intro para.", "x", "After para."]],
  ["a newline between two line breaks", wrap("line one<br>\n<br>\nline three"), ["Intro para.", "line one", "\nline three", "After para."]],
  ["the newline between a figure and its image", wrap('<figure>\n<img src="a.png" alt="pic">\n<figcaption>Caption text</figcaption>\n</figure>'), ["Intro para.", "Caption text", "After para."]],
];

test("the fixtures hold the shapes: the stand-in keeps a nbsp as U+00A0, and each rendered scene has a whitespace-only text node of a rendered space where the collapsed scenes have one of ASCII white space", () => {
  const box = buildRendered(wrap("<p>&nbsp;<b>bold</b> tail</p>"));
  const p = box.kids.filter((n) => n.nodeType === 1)[1] as FakeElement;
  assert.equal(p.tagName, "P");
  assert.equal((p.kids[0] as FakeText).data, NBSP, "the entity decodes to a no-break space, not a plain space");
  assert.ok(/^\s$/.test(NBSP) && /^\s$/.test(IDEO), "JavaScript's \\s matches both (the reading the fix leaves behind for the skip)");
  const wsNodes = (root: FakeNode, out: FakeText[] = []): FakeText[] => { for (const c of root.childNodes) { if (c.nodeType === 3) { if (isWsOnly((c as FakeText).data)) out.push(c as FakeText); } else wsNodes(c, out); } return out; };
  for (const [why, src] of RENDERED) {
    const b = buildRendered(src);
    assert.ok(wsNodes(b).some((t) => t.parentNode !== b && !/^[ \t\n\r\f]*$/.test(t.data)), why + ": a whitespace-only text node of a rendered space below the top level");
  }
  for (const [why, src] of COLLAPSED) {
    const b = buildRendered(src);
    assert.ok(wsNodes(b).some((t) => t.parentNode !== b && /^[ \t\n\r\f]*$/.test(t.data)), why + ": a whitespace-only text node of ASCII white space below the top level");
  }
});

test("a highlight across a nbsp or an ideographic space at a block's edge, beside a block box or between two line breaks paints it: a rendered blank is the passage's text, as on main; collapsible white space at the same positions is skipped", () => {
  for (const scene of RENDERED) drive(scene);
  for (const scene of COLLAPSED) drive(scene);
});

// ── 2. the space between two inline children of a list item, a div, a blockquote, a section ────────────────────────────────
const IMG_A = '<img src="a.png" alt="a">', IMG_B = '<img src="b.png" alt="b">';
const INLINE_CHILDREN: Scene[] = [
  ["a tight list item of two inline elements", wrap("- **a** *b*"), ["Intro para.", "a", " ", "b", "After para."]],
  ["a nested tight item", wrap("- top\n  - **a** *b*"), ["Intro para.", "top", "a", " ", "b", "After para."]],
  ["a task item: the space after its checkbox and the one between its inline elements", wrap("- [ ] **a** *b*"), ["Intro para.", " ", "a", " ", "b", "After para."]],
  ["two links in an item", wrap("- [a](#a) [b](#b)"), ["Intro para.", "a", " ", "b", "After para."]],
  ["a centred badge row: two linked images with a space between, in a div", wrap('<div align="center"><a href="#a">' + IMG_A + '</a> <a href="#b">' + IMG_B + "</a></div>"), ["Intro para.", " ", "After para."]],
  ["an html blockquote of inline elements (its edges' white space skipped, the middle painted)", wrap("<blockquote> <b>q</b> <i>r</i> </blockquote>"), ["Intro para.", "q", " ", "r", "After para."]],
  ["a section of inline elements", wrap("<section><b>a</b> <i>b</i></section>"), ["Intro para.", "a", " ", "b", "After para."]],
  ["an item inside a quote", wrap("> - **a** *b*"), ["Intro para.", "a", " ", "b", "After para."]],
];
/** Block children, and the root: the container list's cases, each skipped by the readings that stay. */
const BLOCK_CHILDREN: Scene[] = [
  ["a markdown list (the newlines between the items)", wrap("- one\n- two"), ["Intro para.", "one", "two", "After para."]],
  ["an html list with a blank line between its items", wrap("<ul>\n<li>one</li>\n\n<li>two</li>\n</ul>"), ["Intro para.", "one", "two", "After para."]],
  ["an html table with newlines between its parts", wrap("<table>\n<tr>\n<td>one</td>\n<td>two</td>\n</tr>\n</table>"), ["Intro para.", "one", "two", "After para."]],
  ["a quote of two paragraphs", wrap("> one\n>\n> two"), ["Intro para.", "one", "two", "After para."]],
  ["a div of two paragraphs", wrap("<div>\n<p>one</p>\n<p>two</p>\n</div>"), ["Intro para.", "one", "two", "After para."]],
  ["an item holding a space alone (the item's edge)", wrap("<ul><li> </li><li>two</li></ul>"), ["Intro para.", "two", "After para."]],
  ["an item of inline elements with a sub-list (the space between the inline elements painted, the sub-list's newlines not)", wrap("- top **x** *y*\n  - sub"), ["Intro para.", "top ", "x", " ", "y", "sub", "After para."]],
  ["two images as one html block: the newline between them is the root's, never a top-level mark", wrap(IMG_A + "\n" + IMG_B), ["Intro para.", "After para."]],
  ["two images with a nbsp line between them, the root's as well", wrap(IMG_A + "\n&nbsp;\n" + IMG_B), ["Intro para.", "After para."]],
];

test("the fixtures hold the shapes: each inline-children scene has a whitespace-only text node of one space between two inline elements under a list item, a div, a blockquote or a section, and the root scenes have theirs directly under the box", () => {
  const CONTAINERS = new Set(["LI", "DIV", "BLOCKQUOTE", "SECTION"]);
  const spaces = (root: FakeNode, out: FakeText[] = []): FakeText[] => { for (const c of root.childNodes) { if (c.nodeType === 3) { if ((c as FakeText).data === " ") out.push(c as FakeText); } else spaces(c, out); } return out; };
  for (const [why, src] of INLINE_CHILDREN) {
    const b = buildRendered(src);
    const between = spaces(b).filter((t) => { const p = t.parentNode!; const i = p.kids.indexOf(t); const l = p.kids[i - 1], r = p.kids[i + 1]; return CONTAINERS.has(p.tagName) && l && r && l.nodeType === 1 && r.nodeType === 1; });
    assert.ok(between.length >= 1, why + ": a space between two inline elements under " + Array.from(CONTAINERS).join("/"));
  }
  for (const [why, src] of BLOCK_CHILDREN.slice(-2)) {
    const b = buildRendered(src);
    assert.ok(b.kids.some((n) => n.nodeType === 3 && isWsOnly((n as FakeText).data) && n.previousSibling?.nodeType === 1 && (n.previousSibling as FakeElement).tagName === "IMG" && n.nextSibling?.nodeType === 1 && (n.nextSibling as FakeElement).tagName === "IMG"), why + ": a whitespace-only text node between two images directly under the box");
  }
});

test("a highlight across a list item, a task item, a badge row, an html blockquote or a section paints the space between two inline children (main's container rule skipped it and broke the ring); the white space between block children and the root's own is skipped as before", () => {
  for (const scene of INLINE_CHILDREN) drive(scene);
  for (const scene of BLOCK_CHILDREN) drive(scene);
});
