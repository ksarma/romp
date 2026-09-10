// The reader's place at BLOCK level, the pure parts (reader-place.ts; plans/markdown-viewer.md Slice 2, and the Slice 2
// review's findings on it): the top-visible search around a hidden element and a floated figure, the block table the
// two views share (anchor-map.ts sourceBlockSpans against renderedBlockIndex), the follow with the successor fallback,
// the three rules of seatedTop, and readPlace / seatPlace over a DOM stand-in with boxes: a blank Raw row reads as the
// block after it, a row inside a code block as the code block with the block's rows as its box, an html block of two
// sibling tags as one block with the two boxes together, a place partway into a block seats the other view at the same
// fraction of the block's height, a replaced block keeps the depth in pixels and moves down by what it lost, a body at
// its top stays at its top. The review's second round added: an element an html wrapper swallowed (the map pairs every
// later element to the wrapper) reads as no place and lends no box; the Raw row at the edge is kept and seated where it
// was through an edit inside its block; a block deleted under the eye seats the block after it at the edge; with the
// block and both neighbours gone, the nearest block before that stands places it. The third round replaced the text
// test on a swallowed element with a trusted pairing (the block's own source parsed by DOMParser yields as many
// elements with the same text; the review found the hand decoder throwing on an out-of-range entity and refusing a
// caption on `&mdash;`), refused the wrapper's run from any element (a picture, a rule) and a seat on the wrapper's own
// rows, refused both of two adjacent html blocks, and kept the line rule to a line that stands (a rewritten or
// recurring line falls to the depth rule). The fourth round refused a wrapper's one-element pairing too (a wrapper
// closing at the document's end, or never closed, is paired to itself alone, holding every paragraph after it; the third
// round trusted any one element), keeping a one-tag html block and any other block's one element, and pinned codeOf's
// html `<pre>` exclusion here (the stand-in has no hit test, so a seat cannot reach it). The Slice 3 review's third
// round pinned that the math fill's source fallback (a `$$` or `\[` block) is no code block to codeOf either, and that a
// code element with no rows (the stand-in's fences, which nothing wraps) reads and seats no line whatever hit test the
// document offers: the hit-test path Slice 2 read a code line with, kept in Slice 3 for that fallback, could never reach
// it and went. The real thing is measured in headless Chromium by file-view-place-blocks-browser.test.ts,
// file-view-place-edits-browser.test.ts, file-view-place-html-browser.test.ts and
// file-view-place-wrapper-end-browser.test.ts.
// The stand-in is the anchor-map suite's minimal tree (marked's output parsed into nodes, no jsdom) with a box per
// element a test gives it; an element with no box reads as having no layout. Its DOMParser parses with the same
// parser, so the trusted pairing reads as it does in a browser. Synthetic fixtures only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { marked } from "marked";
import { topVisibleIndex, blockIndexAt, blockHolding, followPlace, seatedTop, readPlace, seatPlace, codeOf, type Place } from "./reader-place";
import { sourceBlockSpans, renderedBlockIndex, renderedBlockElements } from "./anchor-map";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

// ── a DOM stand-in ─────────────────────────────────────────────────────────────────────────────────
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
class FakeText extends FakeNode { nodeType = 3; constructor(doc: FakeDocument, public data: string) { super(doc); hideEdges(this); } }
class FakeElement extends FakeNode {
  nodeType = 1;
  attrs = new Map<string, string>();
  scrollTop = 0;
  /** the box a test gives the element; none means no layout (every edge 0, no client rects) */
  box: { top: number; bottom: number } | null = null;
  constructor(doc: FakeDocument, public tagName: string) { super(doc); hideEdges(this); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  appendChild(n: FakeNode): FakeNode { this.childNodes.push(n); n.parentNode = this; return n; }
  contains(n: FakeNode | null): boolean { for (let p = n; p; p = p.parentNode) if (p === this) return true; return false; }
  get className(): string { return this.attrs.get("class") || ""; }
  matches(sel: string): boolean {
    const m = /^([a-z]+)?((?:\.[\w-]+)*)$/.exec(sel);
    if (!m) throw new Error("stand-in: unsupported selector " + sel);
    if (m[1] && m[1].toUpperCase() !== this.tagName) return false;
    const classes = this.className.split(/\s+/);
    return (m[2].match(/\.[\w-]+/g) || []).every((c) => classes.includes(c.slice(1)));
  }
  querySelectorAll(sel: string): FakeElement[] {
    const out: FakeElement[] = [];
    const walk = (n: FakeNode) => { for (const c of n.childNodes) if (c instanceof FakeElement) { if (c.matches(sel)) out.push(c); walk(c); } };
    walk(this); return out;
  }
  querySelector(sel: string): FakeElement | null { return this.querySelectorAll(sel)[0] || null; }
  getBoundingClientRect(): { top: number; bottom: number; left: number; right: number; width: number; height: number } {
    const b = this.box || { top: 0, bottom: 0 };
    return { top: b.top, bottom: b.bottom, left: 0, right: this.box ? 400 : 0, width: this.box ? 400 : 0, height: b.bottom - b.top };
  }
}
class FakeDocument {
  createElement(tag: string): FakeElement { return new FakeElement(this, tag.toUpperCase()); }
  createTextNode(s: string): FakeText { return new FakeText(this, s); }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
const decodeEntities = (s: string) => s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
  if (e[0] === "#") {
    // an HTML parser replaces a code point past U+10FFFF (or none at all) with U+FFFD; String.fromCodePoint would throw
    const cp = parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10);
    return Number.isFinite(cp) && cp <= 0x10ffff ? String.fromCodePoint(cp) : "\uFFFD";
  }
  return e in NAMED ? NAMED[e] : m;
});
/** marked's output as a tree: tags, text, entities; void elements do not nest; a newline right after <pre> is dropped. */
function parseHTML(doc: FakeDocument, html: string): FakeNode[] {
  const root = doc.createElement("ROOT");
  let cur: FakeElement = root;
  const re = /<!--[\s\S]*?-->|<\/?([a-zA-Z][\w-]*)([^>]*)>|([^<]+)/g;   // a comment is no node the pairing counts (nodeType 8 in a real DOM)
  let m: RegExpExecArray | null;
  while ((m = re.exec(html))) {
    if (m[0].startsWith("<!--")) continue;
    if (m[3] !== undefined) { cur.appendChild(doc.createTextNode(decodeEntities(m[3]))); continue; }
    const tag = m[1].toLowerCase();
    if (m[0][1] === "/") { if (cur.tagName === tag.toUpperCase() && cur.parentNode) cur = cur.parentNode as FakeElement; continue; }
    const el = doc.createElement(tag);
    const attrRe = /([\w-]+)(?:="([^"]*)")?/g; let a: RegExpExecArray | null;
    while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], a[2] === undefined ? "" : decodeEntities(a[2]));
    cur.appendChild(el);
    if (!VOID.has(tag) && !m[2].endsWith("/")) { cur = el; if (tag === "pre" && html[re.lastIndex] === "\n") re.lastIndex++; }
  }
  return root.childNodes.slice();
}
/** The browser's DOMParser, over parseHTML: reader-place.ts trusts an html block's pairing when the block's own source
 *  parses to the elements the map paired it with (the same parser both sides, so entities decode alike). */
class FakeDOMParser {
  parseFromString(html: string, _type: string): { body: FakeElement } {
    const doc = new FakeDocument();
    const body = doc.createElement("body");
    for (const n of parseHTML(doc, html)) body.appendChild(n);
    return { body };
  }
}
if (typeof (globalThis as { DOMParser?: unknown }).DOMParser !== "function") (globalThis as { DOMParser?: unknown }).DOMParser = FakeDOMParser;
const El = (n: FakeNode) => n as unknown as Element;
const H = (n: FakeNode) => n as unknown as HTMLElement;

/** `.fileview-body > div.fileview-md > marked output`; `heights` gives each top-level element's box height in order
 *  (40 by default), stacked from `top0` with an 8px gap; the body's top edge is at 100. */
function rendered(src: string, top0 = 0, heights: number[] | number = 40): { body: FakeElement; md: FakeElement; blocks: FakeElement[] } {
  const doc = new FakeDocument();
  const body = doc.createElement("div"); body.setAttribute("class", "fileview-body"); body.box = { top: 100, bottom: 700 };
  const md = doc.createElement("div"); md.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(src) as string)) md.appendChild(n);
  body.appendChild(md);
  const blocks = md.childNodes.filter((n): n is FakeElement => n instanceof FakeElement);
  let y = top0;
  blocks.forEach((b, i) => { const h = Array.isArray(heights) ? heights[i] : heights; b.box = { top: y, bottom: y + h }; y += h + 8; });
  return { body, md, blocks };
}
/** `.fileview-body > div.fileview-code > pre > code.hljs > span.fv-cl*`, one row per line, rows `h` px apart from `top0`. */
function raw(src: string, top0 = 0, h = 20): { body: FakeElement; code: FakeElement; rows: FakeElement[] } {
  const doc = new FakeDocument();
  const body = doc.createElement("div"); body.setAttribute("class", "fileview-body"); body.box = { top: 100, bottom: 700 };
  const wrap = doc.createElement("div"); wrap.setAttribute("class", "fileview-code");
  const pre = doc.createElement("pre"); const code = doc.createElement("code"); code.setAttribute("class", "hljs");
  const lines = src.split("\n"); if (lines.length && lines[lines.length - 1] === "") lines.pop();
  const rows = lines.map((ln, i) => {
    const row = doc.createElement("span"); row.setAttribute("class", "fv-cl");
    const t = doc.createElement("span"); t.setAttribute("class", "fv-ct"); if (ln) t.appendChild(doc.createTextNode(ln));
    row.appendChild(t); row.box = { top: top0 + i * h, bottom: top0 + (i + 1) * h }; code.appendChild(row); return row;
  });
  pre.appendChild(code); wrap.appendChild(pre); body.appendChild(wrap);
  return { body, code, rows };
}
const PARA = (i: number) => `Paragraph ${i}: some words of the report, enough to make a line.`;
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
const CODE = "```python\ndef f(x):\n    return x\n\nprint(f(1))\n```";
const TABLE = "| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |";
const HTML2 = "<p>Html A: a raw paragraph.</p>\n<p>Html B: another on the next line, one block with the first.</p>";
/** heading, 1..3, a code block with a blank line inside, 4..5, a table, 6, an html block of two sibling tags, a comment, 7..8 */
const DOC = "# Report\n\n" + paras(1, 3) + "\n\n" + CODE + "\n\n" + paras(4, 5) + "\n\n" + TABLE + "\n\n" + PARA(6) + "\n\n" + HTML2 + "\n\n<!-- a note to self -->\n\n" + paras(7, 8) + "\n";
const at = (s: string, text: string) => { const i = s.indexOf(text); assert.ok(i >= 0, "fixture holds " + text); return i; };
const lineOf = (s: string, off: number) => s.slice(0, off).split("\n").length - 1;

// ── topVisibleIndex ────────────────────────────────────────────────────────────────────────────────
test("topVisibleIndex: a box with no layout (NaN) below the reader on the search's path is read around, not taken for a box above the edge; the answer skips it too", () => {
  // 102 boxes of 60px; the reader's edge inside box 20. The first probe is (0 + 102) >> 1 = 51.
  const stack = (hidden: number[]) => (i: number) => (hidden.includes(i) ? NaN : (i + 1) * 60);
  const edge = 20 * 60 + 30;
  assert.equal(topVisibleIndex(102, stack([]), edge), 20);
  assert.equal(topVisibleIndex(102, stack([51]), edge), 20, "the hidden box at the first probe (the review read block 44 here)");
  assert.equal(topVisibleIndex(102, stack([50, 51, 52, 53]), edge), 20, "a run of hidden boxes at the probe");
  assert.equal(topVisibleIndex(102, stack([25]), edge), 20, "hidden between the reader and the first probe");
  assert.equal(topVisibleIndex(102, stack([20]), edge), 21, "the hidden box is where the reader's block would be: the next box with a layout");
  assert.equal(topVisibleIndex(102, stack([19, 20]), edge), 21);
  for (let hid = 0; hid < 102; hid++) for (const top of [0, 1, 19, 20, 21, 60, 100, 101]) {
    const want = hid === top ? top + 1 : top;
    assert.equal(topVisibleIndex(102, stack([hid]), top * 60 + 30), want > 101 ? 102 : want, `hidden ${hid}, reader in ${top}`);
  }
  assert.equal(topVisibleIndex(3, () => NaN, 10), 3, "every box hidden: count, as when none ends below the edge");
  assert.equal(topVisibleIndex(0, () => 0, 0), 0);
  const bottoms = [40, 80, 120, 160, 200];
  assert.equal(topVisibleIndex(5, (i) => bottoms[i], 40), 1, "a bottom ON the edge is not below it");
  assert.equal(topVisibleIndex(5, (i) => bottoms[i], 200), 5, "none below: count");
});

test("topVisibleIndex: a floated figure reaching below the paragraphs beside it is passed over for the first paragraph ending below the edge, when the search lands on the figure too; a figure whose successor ends below the edge is the top box itself", () => {
  // boxes: the heading and three paragraphs (40, 80, 120, 160), a figure (index 4) reaching to 400, three paragraphs
  // beside it ending at 200, 240, 280. The search's first probe, (0 + 8) >> 1, is the figure, whose bottom lies below
  // every edge here, so the search settles on it and the pass-over decides (the review's third round: the earlier
  // fixture's figure, at index 1, was never the search's answer while a paragraph beside it ended above the edge, so
  // the search alone answered every case and the pass-over went untested; a search that stops where it lands answers
  // 4 for the first two cases)
  const floated = [40, 80, 120, 160, 400, 200, 240, 280];
  assert.equal(topVisibleIndex(8, (i) => floated[i], 250), 7, "the reader is beside the figure at its third paragraph: that paragraph, the two ending above the edge passed over");
  assert.equal(topVisibleIndex(8, (i) => floated[i], 210), 6, "at its second paragraph: that paragraph");
  assert.equal(topVisibleIndex(8, (i) => floated[i], 170), 4, "the first paragraph beside it still ends below the edge: the figure, first in the order, as in a plain column");
  assert.equal(topVisibleIndex(8, (i) => floated[i], 100), 2, "the edge above the figure: the paragraph there");
  assert.equal(topVisibleIndex(8, (i) => floated[i], 300), 4, "past the last paragraph beside it, the figure still shows: the figure (nothing ends below the edge but it)");
  // the figure at the search's second probe from the left ((6 + 11) >> 1 = 8, after box 5 read as above the edge)
  const later = [54, 67, 114, 153, 175, 238, 252, 310, 423, 339, 391];
  assert.equal(topVisibleIndex(11, (i) => later[i], 343), 10, "the paragraph beside the figure that ends below the edge, not the figure the search landed on");
  const farFig = [40, 900, ...Array.from({ length: 12 }, (_, i) => 60 + i * 20)];
  assert.equal(topVisibleIndex(farFig.length, (i) => farFig[i], 500), farFig.length, "a figure more than the tail's boxes before the end is passed over there: count, no place");
  // the same figure with the paragraph after it ending below the edge: the figure is the top box, as in a plain column
  const column = [40, 250, 300, 340];
  assert.equal(topVisibleIndex(4, (i) => column[i], 130), 1);
  // a hidden element among the paragraphs beside the figure is passed over with them
  const withHidden = [40, 80, 120, 160, 400, 200, NaN, 240, 280];
  assert.equal(topVisibleIndex(9, (i) => withHidden[i], 250), 8);
});

// ── the block table ────────────────────────────────────────────────────────────────────────────────
test("sourceBlockSpans: the lexer's top-level blocks in order, spans to the end of their text; a blank line inside a code block is the block's, one between two paragraphs is no block's (blockHolding takes the block after); block b of the table is block b of the rendered index", () => {
  const spans = sourceBlockSpans(DOC);
  const texts = spans.map((s) => DOC.slice(s.start, s.end));
  assert.equal(texts[0], "# Report");
  assert.equal(texts[1], PARA(1));
  assert.equal(texts[4], CODE, "the code block, its inner blank line included");
  assert.equal(texts[7], TABLE);
  assert.equal(texts[9], HTML2, "two sibling tags with no blank line between: one html block");
  assert.equal(texts[10], "<!-- a note to self -->");
  assert.equal(texts[12], PARA(8));
  assert.equal(spans.length, 13);
  assert.equal(sourceBlockSpans(DOC), spans, "the last source's table is kept");
  // offsets
  assert.equal(blockIndexAt(spans, at(DOC, "return x")), 4);
  assert.equal(blockHolding(spans, at(DOC, "return x")), 4, "inside the code block");
  assert.equal(blockHolding(spans, at(DOC, "\n\nprint(f(1))") + 1), 4, "the blank line inside the code block belongs to it");
  assert.equal(blockHolding(spans, at(DOC, PARA(2)) - 1), 2, "the blank line between paragraphs 1 and 2: paragraph 2, the block after it");
  assert.equal(blockHolding(spans, spans[12].end + 1), -1, "past the last block's text");
  assert.equal(blockIndexAt(spans, -1), -1);
  assert.equal(blockHolding([], 3), -1);
  // the rendered index pairs elements to the same blocks
  const { md, blocks } = rendered(DOC);
  assert.deepEqual(blocks.map((b) => b.tagName), ["H1", "P", "P", "P", "PRE", "P", "P", "TABLE", "P", "P", "P", "P", "P"]);
  const idx = blocks.map((b) => renderedBlockIndex(El(md), DOC, El(b)));
  assert.deepEqual(idx, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 11, 12], "the html block's two <p> are both block 9; the comment (10) renders nothing");
  assert.deepEqual(renderedBlockElements(El(md), DOC, 9).map((e) => (e as unknown as FakeElement).textContent.slice(0, 6)), ["Html A", "Html B"]);
  assert.deepEqual(renderedBlockElements(El(md), DOC, 10), [], "the comment has no element");
  assert.equal(renderedBlockElements(El(md), DOC, 4)[0], El(blocks[4]));
  const ws = md.childNodes.find((n) => n instanceof FakeText)!;
  assert.equal(renderedBlockIndex(El(md), DOC, ws as unknown as Node), -1, "whitespace between blocks is no block");
  // markdown the lexer cannot place is one block over the whole text, in both tables
  const crlf = "line one\r\n\r\nline two\r\n";
  assert.deepEqual(sourceBlockSpans(crlf), [{ start: 0, end: 8 }, { start: 12, end: 20 }], "CRLF offsets are the file's");
});

// ── followPlace ────────────────────────────────────────────────────────────────────────────────────
test("followPlace: the block itself when intact (unchanged text, an insertion above, moved whole); the block before it (step 1) when rewritten; the block after it (step -1) when the block before is rewritten too; the nearest block before that stands with all three gone; the edit's start with none standing", () => {
  const spanOf = (s: string, i: number) => ({ start: at(s, PARA(i)), end: at(s, PARA(i)) + PARA(i).length });
  const place = (s: string, i: number): Place => ({ source: s, view: "rendered", ...spanOf(s, i), top: -12, height: 40, atTop: false, prev: spanOf(s, i - 1), next: spanOf(s, i + 1) });
  const doc = "# Report\n\n" + paras(1, 10) + "\n";
  assert.deepEqual(followPlace(place(doc, 5), doc), { at: at(doc, PARA(5)), step: 0 });
  const above = doc.replace(PARA(2), "Inserted A: new words.\n\nInserted B: more new words.\n\n" + PARA(2));
  assert.deepEqual(followPlace(place(doc, 5), above), { at: at(above, PARA(5)), step: 0 }, "shifted by the insertion");
  const rewritten = above.replace(PARA(5), "Rewritten 5: the session replaced this paragraph.");
  assert.deepEqual(followPlace(place(doc, 5), rewritten), { at: at(above, PARA(4)), step: 1 }, "the block before, followed through the insertion; the kept block is the one after it");
  const two = above.replace(PARA(4), "Rewritten 4: new.").replace(PARA(5), "Rewritten 5: new.");
  assert.deepEqual(followPlace(place(doc, 5), two), { at: two.indexOf(PARA(6)), step: -1 }, "the block before rewritten too: the block after, and the kept block is the one before it (the review: this fell to the edit's start, twenty paragraphs up)");
  const three = two.replace(PARA(6), "Rewritten 6: new.");
  assert.deepEqual(followPlace(place(doc, 5), three), { at: at(three, PARA(3)), step: 1 }, "all three rewritten: the nearest block before them that stands (paragraph 3, followed through the insertion), and the kept block is the one after it, the first of the rewritten run (the review round 2: this fell to where the edit begins, the insertion under paragraph 1)");
  const whole = "Every paragraph rewritten, the heading too.\n";
  assert.deepEqual(followPlace(place(doc, 5), whole), { at: 0, step: 0 }, "no block standing on either side: where the edit begins");
  const below = doc.replace(PARA(8), PARA(8) + "\n\nAppended: words after the reader.");
  assert.deepEqual(followPlace(place(doc, 5), below), { at: at(doc, PARA(5)), step: 0 });
  const first: Place = { source: doc, view: "rendered", ...spanOf(doc, 1), top: -12, height: 40, atTop: false, prev: null, next: spanOf(doc, 2) };
  const firstGone = doc.replace(PARA(1), "Rewritten 1.");
  assert.deepEqual(followPlace(first, firstGone), { at: firstGone.indexOf(PARA(2)), step: -1 }, "no block before: the block after, at its offset in the new text");
});

// ── seatedTop ──────────────────────────────────────────────────────────────────────────────────────
test("seatedTop: a block below the edge keeps its distance; partway in, the depth is a fraction of the height for the same text or the other view, pixels for a block whose text changed, moved down by what it lost", () => {
  const p = (top: number, height: number, view: "rendered" | "raw" = "rendered"): Place => ({ source: "", view, start: 0, end: 1, top, height, atTop: false, prev: null, next: null });
  assert.equal(seatedTop(p(18, 40), "rendered", 60, true), 18);
  assert.equal(seatedTop(p(18, 40), "raw", 20, false), 18);
  // a reader 900px into a 2184px code block: the Raw block of 2196px at the same fraction (line 50 stays at the edge)
  assert.equal(Math.round(seatedTop(p(-900, 2184), "raw", 2196, true)), -905);
  // 400px into a 600px figure, which is one 72px row in Raw, and back
  assert.equal(seatedTop(p(-400, 600), "raw", 72, true), -48);
  assert.equal(seatedTop(p(-48, 72, "raw"), "rendered", 600, true), -400);
  // the same view, the same text, reflowed taller (the aside opened): the fraction
  assert.equal(seatedTop(p(-30, 60), "rendered", 120, true), -60);
  // replaced in the same view: pixels; a 10-line block the session appended 90 lines to keeps line 5 at the edge
  assert.equal(seatedTop(p(-90, 180), "rendered", 1800, false), -90);
  // replaced by something shorter than the depth: moved down by the loss, so 12px show, as 12px showed before
  assert.equal(Math.round(seatedTop(p(-29.6, 41.6), "rendered", 20.8, false) * 10) / 10, -8.8);
  // a hair into a two-line paragraph, replaced by one line: the replacement at the edge, not 20px below it
  assert.equal(seatedTop(p(-0.125, 41.6), "rendered", 20.8, false), 0);
  assert.equal(seatedTop(p(-30, 100), "rendered", 20, false), 0, "a five-line block the reader was 30px into, replaced by one line: whole, at the edge");
  // replaced and the view changed at once: the fraction
  assert.equal(seatedTop(p(-30, 60, "raw"), "rendered", 90, false), -45);
  assert.equal(seatedTop(p(-30, 0), "raw", 90, true), 0, "a block of no height: its top");
});

// ── readPlace over the stand-in ────────────────────────────────────────────────────────────────────
test("readPlace: Rendered reads the top-visible element's BLOCK with the block's box (an html block's two tags together), its neighbours and whether the body is at its top; a hidden element on the search's path is skipped", () => {
  // heading at 0..40, paragraphs 48.., the body's edge at 100: paragraph 2 (index 2: 96..136) straddles the edge
  const r = rendered(DOC, 0, 40);
  const p = readPlace(H(r.body), DOC)!;
  assert.equal(DOC.slice(p.start, p.end), PARA(2));
  assert.equal(p.top, 96 - 100); assert.equal(p.height, 40); assert.equal(p.view, "rendered"); assert.equal(p.atTop, true, "scrollTop 0");
  assert.equal(DOC.slice(p.prev!.start, p.prev!.end), PARA(1)); assert.equal(DOC.slice(p.next!.start, p.next!.end), PARA(3));
  r.body.scrollTop = 7;
  assert.equal(readPlace(H(r.body), DOC)!.atTop, false);
  // the html block: its second <p> is the first element ending below the edge, the block's box starts at the first
  const spans = sourceBlockSpans(DOC);
  const r2 = rendered(DOC, 0, 40);
  const [pA, pB] = [r2.blocks[9], r2.blocks[10]];
  assert.equal(pA.textContent.slice(0, 6), "Html A");
  pA.box = { top: 60, bottom: 90 }; pB.box = { top: 98, bottom: 130 };   // pA ends above the edge (100), pB below it
  for (let i = 0; i < 9; i++) r2.blocks[i].box = { top: -1000 + i * 40, bottom: -1000 + i * 40 + 32 };
  const q = readPlace(H(r2.body), DOC)!;
  assert.deepEqual([q.start, q.end], [spans[9].start, spans[9].end], "the html block, not its second tag");
  assert.equal(q.top, 60 - 100, "the box starts at the first tag"); assert.equal(q.height, 130 - 60);
  assert.equal(DOC.slice(q.next!.start, q.next!.end), "<!-- a note to self -->", "the block after it is the comment");
  // a hidden element (no box) where the search first probes: (0 + 13) >> 1 = 6, below the reader at block 2
  const r3 = rendered(DOC, 0, 40); r3.blocks[6].box = null;
  assert.equal(DOC.slice(readPlace(H(r3.body), DOC)!.start, readPlace(H(r3.body), DOC)!.end), PARA(2), "paragraph 2 still");
  // no layout at all: no place
  const flat = rendered(DOC); for (const b of flat.blocks) b.box = null;
  assert.equal(readPlace(H(flat.body), DOC), null);
  const gone = rendered(DOC, -2000, 40);
  assert.equal(readPlace(H(gone.body), DOC), null, "every block above the edge");
});

test("readPlace: Raw reads the block holding the top row, with the block's rows as its box; a blank row between two blocks reads as the block after it, below the edge; a row inside the code block reads as the code block from its fence", () => {
  const lines = DOC.split("\n");
  const spans = sourceBlockSpans(DOC);
  // rows 20px apart from y = 0, the edge at 100: row 5 is the first ending below it
  const w = raw(DOC, 0, 20);
  assert.equal(lines[5], "", "row 5 is the blank line between paragraphs 2 and 3");
  const q = readPlace(H(w.body), DOC)!;
  assert.equal(DOC.slice(q.start, q.end), PARA(3), "the block after the blank row (the review: the blank row read as the place seated paragraph 2)");
  assert.equal(q.top, 6 * 20 - 100, "paragraph 3's row, 20px below the edge"); assert.equal(q.height, 20); assert.equal(q.view, "raw");
  assert.equal(DOC.slice(q.prev!.start, q.prev!.end), PARA(2));
  // the edge inside the code block: row `return x` (the block's third line)
  const codeLine = lineOf(DOC, at(DOC, "```python"));
  const w2 = raw(DOC, -(codeLine + 2) * 20 + 100 - 10, 20);   // the `return x` row straddles the edge
  const q2 = readPlace(H(w2.body), DOC)!;
  assert.deepEqual([q2.start, q2.end], [spans[4].start, spans[4].end], "the code block");
  assert.equal(q2.top, -2 * 20 - 10, "the fence row's top, two rows and 10px above the edge");
  assert.equal(q2.height, 6 * 20, "fence to fence, the inner blank line included");
  // the blank line INSIDE the code block at the edge: still the code block
  const w3 = raw(DOC, -(codeLine + 3) * 20 + 100 - 10, 20);
  assert.deepEqual([readPlace(H(w3.body), DOC)!.start, readPlace(H(w3.body), DOC)!.top], [spans[4].start, -3 * 20 - 10]);
  // rows that disagree with the source: no place
  assert.equal(readPlace(H(w.body), DOC.replace("Paragraph 3", "Paragraph X")), null);
});

// ── seatPlace over the stand-in ────────────────────────────────────────────────────────────────────
test("seatPlace: a place partway into a block seats the other view's block at the same fraction of its height, and back; a Raw place keeps the block's rows as the box; a body at its top goes to its top; a replaced block keeps the depth in pixels and moves down by what it lost; the successor fallback seats the block before it", () => {
  const spans = sourceBlockSpans(DOC);
  const codeLine = lineOf(DOC, at(DOC, "```python"));
  // Rendered: the code block (block 4) 600px tall, the reader 300px into it (top -300 from the edge at 100)
  const kept: Place = { source: DOC, view: "rendered", start: spans[4].start, end: spans[4].end, top: -300, height: 600, atTop: false, prev: spans[3], next: spans[5] };
  const w = raw(DOC, 0, 20); w.body.scrollTop = 1000;
  assert.equal(seatPlace(H(w.body), DOC, kept), true);
  // the block's rows: 6 of 20px = 120px; half way in is 60px, so the fence row goes 60px above the edge
  assert.equal(w.body.scrollTop, 1000 + (codeLine * 20 - 100) - (-60), "the fence row seated 60px above the edge: line 3 of 6 at the edge, as line 300 of 600 was");
  // and back: a Raw place at the fence's row, 60px in, seats the 600px block 300px in
  const rawKept: Place = { source: DOC, view: "raw", start: spans[4].start, end: spans[4].end, top: -60, height: 120, atTop: false, prev: spans[3], next: spans[5] };
  const r = rendered(DOC, 0, [40, 40, 40, 40, 600, 40, 40, 40, 40, 40, 40, 40, 40]); r.body.scrollTop = 50;
  assert.equal(seatPlace(H(r.body), DOC, rawKept), true);
  const preTop = r.blocks[4].box!.top;
  assert.equal(r.body.scrollTop, 50 + (preTop - 100) - (-300));
  // the same text, the same view, the block reflowed taller: the fraction (the aside opened, the paragraph wraps to twice the lines)
  const r2 = rendered(DOC, 0, 80); r2.body.scrollTop = 0;
  const half: Place = { ...kept, start: spans[2].start, end: spans[2].end, top: -20, height: 40 };
  assert.equal(seatPlace(H(r2.body), DOC, half), true);
  assert.equal(r2.body.scrollTop, (r2.blocks[2].box!.top - 100) - (-40), "twice as tall: twice as deep");
  // at the top of the body: the top of the body, whatever the block's height in the new view
  const w2 = raw(DOC, 0, 20); w2.body.scrollTop = 33;
  assert.equal(seatPlace(H(w2.body), DOC, { ...kept, atTop: true }), true);
  assert.equal(w2.body.scrollTop, 0);
  // the block rewritten (shorter), the reader 30px into its 40px: seated 10px above the edge, so 10px show, as 10px did
  const shorter = DOC.replace(PARA(2), "Rewritten 2.");
  const r3 = rendered(shorter, 0, [40, 40, 20, 40, 600, 40, 40, 40, 40, 40, 40, 40, 40]); r3.body.scrollTop = 0;
  const p2: Place = { ...kept, start: spans[2].start, end: spans[2].end, top: -30, height: 40, prev: spans[1], next: spans[3] };
  assert.equal(r3.blocks[2].textContent, "Rewritten 2.");
  assert.equal(seatPlace(H(r3.body), shorter, p2), true);
  assert.equal(r3.body.scrollTop, (r3.blocks[2].box!.top - 100) - (-10), "the replacement's top 10px above the edge");
  // the block rewritten (taller: lines appended), the reader 30px in: still 30px in, not the fraction
  const taller = DOC.replace(PARA(2), PARA(2) + " And ninety more lines of words the session appended.");
  const r4 = rendered(taller, 0, [40, 40, 400, 40, 600, 40, 40, 40, 40, 40, 40, 40, 40]); r4.body.scrollTop = 0;
  assert.equal(seatPlace(H(r4.body), taller, p2), true);
  assert.equal(r4.body.scrollTop, (r4.blocks[2].box!.top - 100) - (-30));
  // paragraphs 1 AND 2 rewritten, two paragraphs inserted above: the block after (3) is followed and the block before it seated
  const both = DOC.replace(PARA(1), "Inserted A.\n\nInserted B.\n\nRewritten 1.").replace(PARA(2), "Rewritten 2.");
  const r5 = rendered(both, 0, 40); r5.body.scrollTop = 0;
  assert.equal(r5.blocks[4].textContent, "Rewritten 2.");
  assert.equal(seatPlace(H(r5.body), both, p2), true);
  assert.equal(r5.body.scrollTop, (r5.blocks[4].box!.top - 100) - (-30), "the rewritten paragraph 2, where paragraph 2 stood (the edit's start would be Inserted A)");
  // nothing to seat in: the loader, or an offset before the first block
  const doc = new FakeDocument(); const body = doc.createElement("div"); body.box = { top: 0, bottom: 600 }; body.appendChild(doc.createElement("div"));
  assert.equal(seatPlace(H(body), DOC, kept), false);
  assert.equal(seatPlace(H(r.body), DOC, { ...kept, start: -5, end: -5, prev: null, next: null }), false);
});

// ── the Slice 2 review, round 2: a wrapper's swallowed run, the line at the edge, a deleted block, the wider walk ────
test("readPlace / seatPlace: an html wrapper the browser nests the following markdown into is paired, as the map stands, to every element after it; any element of the run (a swallowed paragraph, the wrapper, a rule) reads as no place, and a seat that would borrow the wrapper's box, or seat the wrapper's own rows, declines; an html block of sibling tags parsing to its elements reads as one block, whatever markup or entity it carries; two adjacent html blocks read as no place", () => {
  const WRAP = "<details>\n<summary>More</summary>\n\nHidden details text here.\n\n</details>";
  const doc = "# Report\n\n" + paras(1, 4) + "\n\n" + WRAP + "\n\n" + paras(5, 12) + "\n";
  const spans = sourceBlockSpans(doc);
  const wb = spans.findIndex((sp) => doc.slice(sp.start, sp.end).startsWith("<details>"));
  const r = rendered(doc, 0, 40);
  const p8 = r.blocks.find((k) => k.textContent.startsWith("Paragraph 8:"))!;
  const i8 = r.blocks.indexOf(p8);
  // the fixture: the stand-in nests the inner paragraph inside <details> as a browser does, and the map pairs every later element to the wrapper's block
  assert.equal(r.blocks[5].tagName, "DETAILS");
  assert.equal(r.blocks[5].childNodes.filter((n) => n instanceof FakeElement).length, 2, "the summary and the nested paragraph");
  assert.equal(renderedBlockIndex(El(r.md), doc, El(p8)), wb, "paragraph 8's element is paired to the wrapper's block");
  assert.equal(renderedBlockElements(El(r.md), doc, wb).length, r.blocks.length - 5, "the wrapper holds every element from itself on");
  // paragraph 8 straddles the edge (its box 80..120, the edge at 100): no place, where the union of the rest of the document was read
  const r2 = rendered(doc, 100 - i8 * 48 - 20, 40);
  assert.equal(readPlace(H(r2.body), doc), null, "the swallowed paragraph reads as no place (the review round 2: read as the wrapper's block, a Raw switch landed on <summary>, 3500px up)");
  // a Raw place at paragraph 8 seated in this Rendered view: its block has no element of its own, and the nearest block before it with elements is the wrapper's run: no seat, the body unmoved
  const b8 = blockIndexAt(spans, doc.indexOf("Paragraph 8:"));
  const kept: Place = { source: doc, view: "raw", start: spans[b8].start, end: spans[b8].end, top: -10, height: 20, atTop: false, prev: spans[b8 - 1], next: spans[b8 + 1] };
  r2.body.scrollTop = 500;
  assert.equal(seatPlace(H(r2.body), doc, kept), false);
  assert.equal(r2.body.scrollTop, 500);
  // the wrapper element itself at the edge: its text is the nested paragraph's, not the block's own, so no place either
  const r3 = rendered(doc, 100 - 5 * 48 - 20, 40);
  assert.equal(readPlace(H(r3.body), doc), null);
  // a paragraph before the wrapper reads as ever
  const r4 = rendered(doc, 100 - 3 * 48 - 20, 40);
  assert.equal(doc.slice(readPlace(H(r4.body), doc)!.start, readPlace(H(r4.body), doc)!.end), PARA(3));
  // DOC's two-tag html block (block 9): each tag's text is in the block's source, so the pair reads as the block, as before
  const r5 = rendered(DOC, 0, 40);
  r5.blocks[9].box = { top: 60, bottom: 90 }; r5.blocks[10].box = { top: 98, bottom: 130 };
  for (let i = 0; i < 9; i++) r5.blocks[i].box = { top: -1000 + i * 40, bottom: -1000 + i * 40 + 32 };
  const q5 = readPlace(H(r5.body), DOC)!;
  assert.deepEqual([q5.start, q5.end], [sourceBlockSpans(DOC)[9].start, sourceBlockSpans(DOC)[9].end]);
  // entities in a sibling tag decode before the check
  const ENT = "<p>Tom &amp; Jerry, a first tag.</p>\n<p>Second tag &lt;here&gt; &#169;.</p>";
  const doc6 = "# Report\n\n" + paras(1, 2) + "\n\n" + ENT + "\n\n" + PARA(3) + "\n";
  const r6 = rendered(doc6, 100 - 4 * 48 - 20, 40);   // the second tag (element 4) straddles the edge
  assert.equal(r6.blocks[4].textContent, "Second tag <here> ©.");
  const q6 = readPlace(H(r6.body), doc6)!;
  assert.equal(doc6.slice(q6.start, q6.end), ENT, "the html block, its entities read as the browser shows them");
  // ── the review's third round ──
  // a two-tag block whose FIRST tag is at the edge reads as the block whatever the tag carries: markup the round-2 text
  // test could not see through (its textContent is not a substring of the raw), an entity name it did not know, an entity
  // out of range (the round-2 decoder threw a RangeError, which stopped the Raw click and the text-size step), a
  // 100,003-digit entity, an entity with no semicolon
  const HUGE = "&#" + "1".repeat(100_000) + ";";
  const twoTags: Array<[string, string]> = [
    ["inline tags", "<p>A <b>bold</b> and <a href=\"https://example.test\">linked</a> <code>tag</code> first.</p>\n<p>Second tag.</p>"],
    ["a line break", "<p>First line<br>second line of the first tag.</p>\n<p>Second tag.</p>"],
    ["the README pair", "<p align=\"center\"><a href=\"https://example.test\"><img src=\"badge.svg\" alt=\"\"></a></p>\n<p align=\"center\"><b>notes-api</b> keeps your notes in sync.</p>"],
    ["named entities", "<p>Caption &mdash; one &copy; &hellip; &nbsp;here.</p>\n<p>Caption two.</p>"],
    ["an out-of-range decimal entity", "<p>First tag &#1114112; here.</p>\n<p>Second tag.</p>"],
    ["an out-of-range hex entity", "<p>First tag &#x110000; here.</p>\n<p>Second tag.</p>"],
    ["a 100,003-character entity", "<p>First tag " + HUGE + " here.</p>\n<p>Second tag.</p>"],
    ["an entity with no semicolon", "<p>Tom &amp Jerry, a first tag.</p>\n<p>Second tag.</p>"],
  ];
  for (const [what, html] of twoTags) {
    const d = "# Report\n\n" + paras(1, 2) + "\n\n" + html + "\n\n" + PARA(3) + "\n";
    const bh = sourceBlockSpans(d).findIndex((sp) => d.slice(sp.start, sp.end) === html);
    assert.ok(bh > 0, what + ": the fixture holds the html block as one block");
    const rr = rendered(d, 100 - 3 * 48 - 20, 40);   // the first tag (element 3) straddles the edge
    assert.equal(renderedBlockElements(El(rr.md), d, bh).length, 2, what + ": paired to its two tags");
    const qq = readPlace(H(rr.body), d);
    assert.ok(qq, what + ": a place (the round-2 text test read the first tag as swallowed, or threw)");
    assert.equal(d.slice(qq!.start, qq!.end), html, what + ": the html block");
    assert.equal(qq!.top, -20, what + ": the block's box from its first tag");
  }
  // a textless element inside the wrapper's run (a rule after paragraph 8, rendered as <hr>): the run's pairing is what is
  // tested, not the element's text, so the rule reads as no place too (round 2 accepted it and lent the run's union box:
  // a Raw switch from a rule or a picture there landed on <details>, 1750px up)
  const docHr = "# Report\n\n" + paras(1, 4) + "\n\n" + WRAP + "\n\n" + paras(5, 8) + "\n\n---\n\n" + paras(9, 12) + "\n";
  const rh = rendered(docHr, 0, 40);
  const hr = rh.blocks.find((k) => k.tagName === "HR")!;
  assert.ok(hr && hr.textContent === "", "the fixture: a rule with no text");
  assert.equal(renderedBlockIndex(El(rh.md), docHr, El(hr)), sourceBlockSpans(docHr).findIndex((sp) => docHr.slice(sp.start, sp.end).startsWith("<details>")), "paired to the wrapper's block");
  const rh2 = rendered(docHr, 100 - rh.blocks.indexOf(hr) * 48 - 20, 40);
  assert.equal(readPlace(H(rh2.body), docHr), null, "the rule at the edge: no place (round 2: the wrapper's block with the union box)");
  // a Raw place on the wrapper's OWN rows (the summary row) seated in Rendered: the block's pairing is the swallowed run,
  // so no seat and the body unmoved (round 2 seated the run's union, 3200px)
  const rowSummary = { start: doc.indexOf("<summary>More</summary>"), end: doc.indexOf("<summary>More</summary>") + "<summary>More</summary>".length };
  const onWrapper: Place = { source: doc, view: "raw", start: spans[wb].start, end: spans[wb].end, top: -8, height: 36, atTop: false, prev: spans[wb - 1], next: spans[wb + 1], line: { ...rowSummary, top: -8 } };
  const r7 = rendered(doc, 0, 40); r7.body.scrollTop = 360;
  assert.equal(seatPlace(H(r7.body), doc, onWrapper), false, "no seat for the wrapper's own rows");
  assert.equal(r7.body.scrollTop, 360, "the numeric scrollTop stands");
  // the neighbour fallback stands: a Raw place on DOC's comment block (no element of its own) seats the two-tag html
  // block before it, whose pairing is trusted, at the same fraction of its box
  const spansD = sourceBlockSpans(DOC);
  const cb = spansD.findIndex((sp) => DOC.slice(sp.start, sp.end) === "<!-- a note to self -->");
  const onComment: Place = { source: DOC, view: "raw", start: spansD[cb].start, end: spansD[cb].end, top: -4, height: 20, atTop: false, prev: spansD[cb - 1], next: spansD[cb + 1] };
  const r8 = rendered(DOC, 0, 40); r8.body.scrollTop = 0;
  assert.equal(seatPlace(H(r8.body), DOC, onComment), true);
  const htmlTop = r8.blocks[9].box!.top, htmlHeight = r8.blocks[10].box!.bottom - htmlTop;
  assert.equal(r8.body.scrollTop, (htmlTop - 100) - (-4 * htmlHeight / 20), "the two-tag block before the comment, 4/20 of its box above the edge");
  // two html blocks a blank line apart: the map pairs the first to nothing and the second to both elements, so neither
  // pairing is confirmed by the parse and both elements read as no place (round 2 read Beta's element as its block and put
  // the Raw view one row off; the anchor-map half is Slice 5's)
  const docAB = "# Report\n\n" + paras(1, 2) + "\n\n<p>Alpha</p>\n\n<p>Beta</p>\n\n" + PARA(3) + "\n";
  const spansAB = sourceBlockSpans(docAB);
  const rab = rendered(docAB, 0, 40);
  const bAlpha = spansAB.findIndex((sp) => docAB.slice(sp.start, sp.end) === "<p>Alpha</p>"), bBeta = spansAB.findIndex((sp) => docAB.slice(sp.start, sp.end) === "<p>Beta</p>");
  assert.deepEqual([renderedBlockElements(El(rab.md), docAB, bAlpha).length, renderedBlockElements(El(rab.md), docAB, bBeta).length], [0, 2], "the fixture: the map's pairing as it stands");
  assert.equal(readPlace(H(rendered(docAB, 100 - 3 * 48 - 20, 40).body), docAB), null, "Alpha's element at the edge: no place");
  assert.equal(readPlace(H(rendered(docAB, 100 - 4 * 48 - 20, 40).body), docAB), null, "Beta's element at the edge: no place");
  assert.equal(readPlace(H(rendered(docAB, 100 - 2 * 48 - 20, 40).body), docAB)!.start, spansAB[2].start, "paragraph 2 before them reads as ever");
});

test("readPlace / seatPlace: a wrapper whose closing tag is the document's last block, or is missing, is paired to its one element, holding every paragraph after it, and that pairing is refused like a run's (the wrapper at the edge reads as no place; a Raw place on a nested paragraph or on the wrapper's own row seats nothing); a one-tag html block, a paragraph opening with an inline tag and one opening with an autolink read as their own blocks; codeOf knows a markdown code block from an html <pre>", () => {
  for (const [what, tail] of [["closed as the last block", "\n\n</div>\n"], ["never closed", "\n"]] as const) {
    const doc = "# Report\n\n" + paras(1, 4) + "\n\n<div align=\"center\">\n\n" + paras(5, 12) + tail;
    const spans = sourceBlockSpans(doc);
    const wb = spans.findIndex((sp) => doc.slice(sp.start, sp.end).startsWith("<div"));
    const r = rendered(doc, 0, 40);
    // the fixture: the stand-in nests paragraphs 5 to 12 inside the div as a browser does, the div is the last top-level element, and the map pairs the wrapper's block to it alone
    assert.equal(r.blocks.length, 6, what + ": the heading, four paragraphs and the div at the top level");
    assert.equal(r.blocks[5].tagName, "DIV", what);
    assert.equal(r.blocks[5].childNodes.filter((n) => n instanceof FakeElement).length, 8, what + ": the eight paragraphs after the wrapper are nested in it");
    assert.deepEqual(renderedBlockElements(El(r.md), doc, wb), [r.blocks[5]], what + ": the wrapper's block is paired to the one element");
    const b8 = blockIndexAt(spans, doc.indexOf("Paragraph 8:"));
    assert.equal(renderedBlockElements(El(r.md), doc, b8).length, 0, what + ": a nested paragraph's block has no element of its own");
    // the div straddles the edge (its box 80..120, the edge at 100): the one element's text is the nested paragraphs', not the block's own, so no place
    const r2 = rendered(doc, 100 - 5 * 48 - 20, 40);
    assert.equal(readPlace(H(r2.body), doc), null, what + ": the wrapper at the edge reads as no place (the third round read the wrapper's block, 20px in, and seated that depth as a fraction of its one Raw row)");
    // a Raw place on nested paragraph 8 seated in this Rendered view: no element of its own, and the nearest block before it with one is the wrapper, refused: no seat, the body unmoved
    const kept: Place = { source: doc, view: "raw", start: spans[b8].start, end: spans[b8].end, top: -3, height: 20, atTop: false, prev: spans[b8 - 1], next: spans[b8 + 1] };
    r2.body.scrollTop = 500;
    assert.equal(seatPlace(H(r2.body), doc, kept), false, what + ": the nested paragraph's Raw place seats nothing (the third round borrowed the wrapper's box)");
    assert.equal(r2.body.scrollTop, 500, what + ": the numeric scrollTop stands");
    // the wrapper's own Raw row seated in Rendered: its pairing is refused, so no seat either
    const onWrapper: Place = { source: doc, view: "raw", start: spans[wb].start, end: spans[wb].end, top: -8, height: 20, atTop: false, prev: spans[wb - 1], next: spans[wb + 1], line: { start: spans[wb].start, end: spans[wb].end, top: -8 } };
    assert.equal(seatPlace(H(r2.body), doc, onWrapper), false, what + ": the wrapper's own row seats nothing");
    assert.equal(r2.body.scrollTop, 500, what);
    // a paragraph before the wrapper reads as ever
    const r4 = rendered(doc, 100 - 3 * 48 - 20, 40);
    assert.equal(doc.slice(readPlace(H(r4.body), doc)!.start, readPlace(H(r4.body), doc)!.end), PARA(3), what + ": paragraph 3 before the wrapper");
  }
  // the blocks the widened rule must keep, each one element: a one-tag html block (its parse yields the tag with its own
  // text), and two paragraphs whose source opens with `<` (an inline tag, an autolink), which are no html blocks and
  // are trusted without a parse (parsed as html, `<b>Note:</b> ...` is one B with less text than the paragraph, and the
  // autolink a bogus element, so a rule that parsed every `<`-opening block would refuse both)
  const CTRL: Array<[string, string]> = [
    ["a one-tag html block", "<p align=\"center\">Centered caption: one tag, its own block.</p>"],
    ["a paragraph opening with an inline tag", "<b>Note:</b> a paragraph that opens with an inline tag and runs on."],
    ["a paragraph opening with an autolink", "<https://example.test/docs> opens this paragraph with an autolink."],
  ];
  const docC = "# Report\n\n" + paras(1, 2) + "\n\n" + CTRL.map((c) => c[1]).join("\n\n") + "\n\n" + PARA(3) + "\n";
  const spansC = sourceBlockSpans(docC);
  CTRL.forEach(([what, src], k) => {
    const b = spansC.findIndex((sp) => docC.slice(sp.start, sp.end) === src);
    assert.ok(b > 0, what + ": the fixture holds it as one block");
    const rc = rendered(docC, 100 - (3 + k) * 48 - 20, 40);   // element 3 + k straddles the edge
    assert.equal(rc.blocks[3 + k].tagName, "P", what + ": one P element");
    assert.equal(renderedBlockElements(El(rc.md), docC, b).length, 1, what + ": paired to it");
    const q = readPlace(H(rc.body), docC);
    assert.ok(q, what + ": a place");
    assert.equal(docC.slice(q!.start, q!.end), src, what + ": its own block");
    assert.equal(q!.top, -20, what + ": the block's box");
  });
  // codeOf: a markdown code block shows the block's lines one for one (the fence line skipped for a fenced block, none
  // for an indented one); an html block's <pre> is none (the tag is its first line, so its lines and the block's are one
  // off), and the block keeps the depth rule (the review round 3; pinned by the html leg alone until this round)
  const HTML_PRE = "<pre>\nhtml line 1: words\nhtml line 2: words\n</pre>";
  const FENCED = "```text\nfenced line 1: words\nfenced line 2: words\n```";
  const INDENTED = "    indented line 1: words\n    indented line 2: words";
  const docK = "# Report\n\n" + HTML_PRE + "\n\n" + FENCED + "\n\n" + INDENTED + "\n\n" + PARA(1) + "\n";
  const spansK = sourceBlockSpans(docK);
  const rk = rendered(docK, 0, 40);
  const codeFor = (src: string) => { const b = spansK.findIndex((sp) => docK.slice(sp.start, sp.end) === src); assert.ok(b > 0, "the fixture holds " + JSON.stringify(src.slice(0, 12)) + " as one block"); const els = renderedBlockElements(El(rk.md), docK, b); assert.equal(els.length, 1); return codeOf(docK, spansK[b], els); };
  assert.equal(codeFor(HTML_PRE), null, "an html block's <pre> is no code block: the depth rule (a rule taking every <pre> answered skip 0 and seated line 11 for line 10)");
  assert.equal(codeFor(FENCED)!.skip, 1, "a fenced block: the fence line is skipped");
  assert.equal(codeFor(FENCED)!.code.tagName, "CODE", "its code element");
  assert.equal(codeFor(INDENTED)!.skip, 0, "an indented block: no line skipped");
  assert.equal(codeFor(PARA(1)), null, "a paragraph is no code block");
  // the math fill's source fallback (math.ts showSource: a top-level <pre><code class="md-math-src"> for a `$$` or `\[`
  // display block KaTeX refused) is no code block either: its block opens with the math delimiter, not a fence or an
  // indent, so the hit-test path that named it as its case (a code element with no rows) could never reach it
  const mathPre = (src: string) => { const doc = new FakeDocument(); const pre = doc.createElement("pre"); const c = doc.createElement("code"); c.setAttribute("class", "md-math-src"); c.appendChild(doc.createTextNode(src)); pre.appendChild(c); return [El(pre)]; };
  for (const src of ["$$\nE = mc^2\n$$", "\\[\nE = mc^2\n\\]", "   $$\nE = mc^2\n$$"]) assert.equal(codeOf(src, { start: 0, end: src.length }, mathPre(src)), null, "the math fill's source fallback is no code block: " + JSON.stringify(src.slice(0, 5)));
  // and the html <pre> still reads as its block: one element whose parse yields the tag with the same text
  const rk2 = rendered(docK, 100 - 1 * 48 - 20, 40);
  assert.equal(docK.slice(readPlace(H(rk2.body), docK)!.start, readPlace(H(rk2.body), docK)!.end), HTML_PRE, "the html <pre> block at the edge reads as its block");
});

test("readPlace / seatPlace, Rendered: a code element with no rows reads no line and seats none, whatever hit test and Range the document offers; the block keeps the depth rule", () => {
  // The Slice 3 review, round 3: renderedLineAt kept Slice 2's hit test (caretRangeFromPoint on the code's first column,
  // a one-character Range for the line's top) for "a code element with no rows, the math fill's source fallback", a block
  // codeOf refuses (the test above); every fence and indented block file-view.ts builds is wrapped in rows, so the path
  // was unreachable and went. The stand-in's fence is marked's output with nothing wrapped, a code element with no rows,
  // and its document is given a hit test and a Range that answer line 2 of the code: neither may be consulted.
  const doc = "# Report\n\n" + paras(1, 2) + "\n\n" + CODE + "\n\n" + paras(3, 4) + "\n";
  const spans = sourceBlockSpans(doc);
  const b = spans.findIndex((sp) => doc.slice(sp.start, sp.end) === CODE);
  assert.ok(b > 0, "the fixture holds the fence as one block");
  const line2 = "    return x";
  type HitDoc = { caretRangeFromPoint?: (x: number, y: number) => unknown; createRange?: () => unknown };
  /** the fence 20px into the edge (its box 80..120 against the edge at 100), its code element wearing the same box and
   *  no `.cl` rows; the document answers a hit test inside line 2 and a Range whose rect tops at 101 */
  const scene = () => {
    const r = rendered(doc, 100 - b * 48 - 20, 40);
    const codeEl = r.blocks[b].querySelector("code")!;
    assert.equal(codeEl.querySelectorAll(".cl").length, 0, "the stand-in's fence has no rows");
    codeEl.box = r.blocks[b].box;
    const text = codeEl.childNodes[0];
    const calls = { hits: 0, ranges: 0 };
    const hd = r.body.ownerDocument as unknown as HitDoc;
    hd.caretRangeFromPoint = () => { calls.hits++; return { startContainer: text, startOffset: (text.textContent || "").indexOf(line2) + 2 }; };
    hd.createRange = () => { calls.ranges++; return { setStart() { /* a stub */ }, setEnd() { /* a stub */ }, getClientRects: () => [{ top: 101, bottom: 115 }], getBoundingClientRect: () => ({ top: 101, bottom: 115, height: 14, width: 8 }) }; };
    return { ...r, calls };
  };
  const a = scene();
  const q = readPlace(H(a.body), doc)!;
  assert.ok(q, "a place");
  assert.equal(doc.slice(q.start, q.end), CODE, "the fence is the place");
  assert.equal(q.top, -20, "partway in");
  assert.equal(q.line, null, "no rows, no line: the depth rule (the hit test read line 2 here before)");
  assert.deepEqual(a.calls, { hits: 0, ranges: 0 }, "the document's hit test and Range are not consulted on a read");
  // a seat of a kept line into the rowless code element declines the line and keeps the depth: the block at -20 already,
  // so the body does not move (before: the Range's 101 seated the line, 6px down)
  const c = scene();
  const place: Place = { ...q, line: { start: doc.indexOf(line2), end: doc.indexOf(line2) + line2.length, top: -5 } };
  assert.equal(seatPlace(H(c.body), doc, place), true, "seated");
  assert.equal(c.body.scrollTop, 0, "the depth rule: the same block at the same depth moves nothing");
  assert.deepEqual(c.calls, { hits: 0, ranges: 0 }, "the document's hit test and Range are not consulted on a seat");
});

test("readPlace / seatPlace, Raw: the row at the edge is kept with its block, and a reload seats the row where it was: lines inserted above it inside the block, lines deleted below it; the row itself rewritten, or a row whose text recurs, falls to the block's depth rule", () => {
  const code = (lines: string[]) => "```text\n" + lines.join("\n") + "\n```";
  const L = Array.from({ length: 12 }, (_, i) => `line ${i + 1} of the block: alpha beta`);
  const doc = "# Report\n\n" + paras(1, 2) + "\n\n" + code(L) + "\n\n" + paras(3, 4) + "\n";
  const rowOf = (s: string, text: string) => lineOf(s, s.indexOf(text));
  // the `line 7` row straddles the edge, 10px above it (rows 20px tall)
  const w = raw(doc, 90 - rowOf(doc, "line 7 of") * 20, 20); w.body.scrollTop = 500;   // scrolled: not a body at its very top
  const q = readPlace(H(w.body), doc)!;
  assert.equal(doc.slice(q.start, q.end), code(L), "the code block");
  assert.equal(doc.slice(q.line!.start, q.line!.end), L[6], "the row at the edge is line 7");
  assert.equal(q.line!.top, -10);
  // a blank row between blocks reads as the block after it, with no line (the block starts below the edge)
  const blank = raw(doc, 100 - rowOf(doc, PARA(2)) * 20 + 10, 20); blank.body.scrollTop = 500;   // the blank row before paragraph 2 straddles the edge
  const qb = readPlace(H(blank.body), doc)!;
  assert.equal(doc.slice(qb.start, qb.end), PARA(2)); assert.equal(qb.line, null);
  // a fresh Raw view of `text` at scrollTop 1000, the place seated: how far the body scrolled (a row r seated 10px above the edge is r * 20 - 90)
  const seatAt = (text: string, kept: Place) => { const w2 = raw(text, 0, 20); w2.body.scrollTop = 1000; assert.equal(seatPlace(H(w2.body), text, kept), true); return w2.body.scrollTop - 1000; };
  assert.equal(seatAt(doc, q), rowOf(doc, "line 7 of") * 20 - 90, "the same text: line 7's row 10px above the edge");
  const ins = doc.replace(code(L), code([...L.slice(0, 2), ...Array.from({ length: 5 }, (_, i) => `inserted ${i + 1}`), ...L.slice(2)]));
  assert.equal(seatAt(ins, q), rowOf(ins, "line 7 of") * 20 - 90, "five lines inserted above the row: line 7's row still 10px above the edge (the block's top held before, and line 2 stood at the edge)");
  const del = doc.replace(code(L), code([...L.slice(0, 8), L[11]]));
  assert.equal(seatAt(del, q), rowOf(del, "line 7 of") * 20 - 90, "three lines deleted below the row: line 7 still (the shorter block moved down three rows before)");
  // the row itself rewritten: no line to follow, so the block's depth rule (pixels for a changed block, moved down by what
  // the block lost, to the edge at most). The review's second round walked to the line after the nearest standing line
  // before it instead, which the third round found seating the edit's first line 44 rows up when every line between was a
  // copy (the cycling block below), and dropped
  const rw = doc.replace(code(L), code([...L.slice(0, 5), "new six", "new seven", ...L.slice(8)]));
  assert.equal(seatAt(rw, q), rowOf(rw, "new six") * 20 - 90, "lines 6 to 8 rewritten as two: the block lost a row and moves down by one, so the replacement's first line stands where line 7 did (the same row the round-2 walk chose here, by the depth rule now)");
  const rwTop = doc.replace(code(L), code(["fresh one", "fresh two", ...L.slice(9)]));
  assert.equal(seatAt(rwTop, q), rowOf(rwTop, "```text") * 20 - 90, "lines 1 to 9 rewritten as two: the block lost seven rows and moves down by them, its fence row 10px above the edge (round 2: fresh one at the edge)");
  const rwBottom = doc.replace(code(L), code([...L.slice(0, 3), "tail one"]));
  assert.equal(seatAt(rwBottom, q), rowOf(rwBottom, "```text") * 20 - 100, "lines 4 to 12 rewritten as one: the block now fits above where its tail was, so it shows whole, its fence at the edge (round 2: tail one at the edge)");
  // a block whose lines recur (three statements cycling), the reader on line 16 (index 15); three lines inserted at index 3
  // and line 28 (index 27) replaced in one write: no copy of the kept line is its own (followPassage's tie), so the depth
  // rule holds the block's top where it was, three rows off the reader's line (the round-2 walk found the nearest standing
  // predecessor outside the edit and seated the first inserted line, twelve rows up)
  const CYC = Array.from({ length: 30 }, (_, i) => ["    x = 1", "    y = 2", "    pass"][i % 3]);
  const docC = "# Report\n\n" + paras(1, 2) + "\n\n" + code(CYC) + "\n\n" + paras(3, 4) + "\n";
  const fenceRow = rowOf(docC, "```text");
  const wc = raw(docC, 90 - (fenceRow + 16) * 20, 20); wc.body.scrollTop = 500;   // row 16 of the block (line index 15) 10px above the edge
  const qc = readPlace(H(wc.body), docC)!;
  assert.equal(docC.slice(qc.start, qc.end), code(CYC)); assert.equal(qc.line!.top, -10); assert.equal(qc.top, -330);
  assert.equal(docC.slice(qc.line!.start, qc.line!.end), CYC[15], "the kept line is line index 15");
  const edited = docC.replace(code(CYC), code([...CYC.slice(0, 3), "    a = 3", "    b = 4", "    c = 5", ...CYC.slice(3, 27), "    z = 9  # replaced", ...CYC.slice(28)]));
  assert.equal(seatAt(edited, qc), rowOf(edited, "```text") * 20 - 100 + 330, "the block's top holds at 330px above the edge (depth rule: the block grew, so pixels)");
});

test("seatPlace: a block deleted under the reader's eye (its neighbours now adjacent) seats the block after it as a replacement of no height, at the edge; rewritten to the same height, the depth holds in pixels; three blocks deleted with two inserted above: the block after them at the edge, placed by the nearest block before that stands (the review round 2: the edit's start, the top of the document); three rewritten as one: the replacement at the depth", () => {
  const doc = "# Report\n\n" + paras(1, 8) + "\n";
  const spans = sourceBlockSpans(doc);
  const b3 = blockIndexAt(spans, doc.indexOf(PARA(3)));
  const kept: Place = { source: doc, view: "rendered", start: spans[b3].start, end: spans[b3].end, top: -30, height: 40, atTop: false, prev: spans[b3 - 1], next: spans[b3 + 1] };
  const seatIn = (text: string, place: Place) => { const r = rendered(text, 0, 40); r.body.scrollTop = 0; assert.equal(seatPlace(H(r.body), text, place), true); return { scrollTop: r.body.scrollTop, r }; };
  const topOf = (r: ReturnType<typeof rendered>, text: string) => r.blocks.find((k) => k.textContent.startsWith(text))!.box!.top - 100;
  const del = doc.replace(PARA(3) + "\n\n", "");
  const d = seatIn(del, kept);
  assert.equal(d.scrollTop, topOf(d.r, "Paragraph 4:"), "paragraph 3 deleted: paragraph 4's top at the edge (before: 30px above it, the reader's depth into a block that is gone)");
  const rw = doc.replace(PARA(3), "Rewritten 3: a paragraph of the same height.");
  const w = seatIn(rw, kept);
  assert.equal(w.scrollTop, topOf(w.r, "Rewritten 3:") + 30, "rewritten: 30px in still");
  const INS = "Inserted A: new words.\n\nInserted B: more new words.\n\n";
  const three = doc.replace(PARA(2) + "\n\n" + PARA(3) + "\n\n" + PARA(4) + "\n\n", "").replace("# Report\n\n", "# Report\n\n" + INS);
  assert.deepEqual(followPlace(kept, three), { at: three.indexOf(PARA(1)), step: 1 }, "the nearest block before that stands, paragraph 1, followed through the insertion");
  const t = seatIn(three, kept);
  assert.equal(t.scrollTop, topOf(t.r, "Paragraph 5:"), "paragraphs 2 to 4 deleted, two inserted above: paragraph 5 at the edge (the edit's start would be Inserted A)");
  const rw3 = doc.replace(PARA(2) + "\n\n" + PARA(3) + "\n\n" + PARA(4), "Rewritten 2 to 4: one paragraph now.").replace("# Report\n\n", "# Report\n\n" + INS);
  const u = seatIn(rw3, kept);
  assert.equal(u.scrollTop, topOf(u.r, "Rewritten 2 to 4:") + 30, "the same three rewritten as one: the replacement, 30px in");
  const e = seatIn(del, { ...kept, top: 18 });
  assert.equal(e.scrollTop, topOf(e.r, "Paragraph 4:") - 18, "a block that started below the edge and was deleted: the block after keeps its distance");
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
