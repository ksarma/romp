// The reader's place at BLOCK level, the pure parts (reader-place.ts; plans/markdown-viewer.md Slice 2, and the Slice 2
// review's findings on it): the top-visible search around a hidden element and a floated figure, the block table the
// two views share (anchor-map.ts sourceBlockSpans against renderedBlockIndex), the follow with the successor fallback,
// the three rules of seatedTop, and readPlace / seatPlace over a DOM stand-in with boxes: a blank Raw row reads as the
// block after it, a row inside a code block as the code block with the block's rows as its box, an html block of two
// sibling tags as one block with the two boxes together, a place partway into a block seats the other view at the same
// fraction of the block's height, a replaced block keeps the depth in pixels and moves down by what it lost, a body at
// its top stays at its top. The real thing is measured in headless Chromium by file-view-place-blocks-browser.test.ts.
// The stand-in is the anchor-map suite's minimal tree (marked's output parsed into nodes, no jsdom) with a box per
// element a test gives it; an element with no box reads as having no layout. Synthetic fixtures only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { marked } from "marked";
import { topVisibleIndex, blockIndexAt, blockHolding, followPlace, seatedTop, readPlace, seatPlace, type Place } from "./reader-place";
import { sourceBlockSpans, renderedBlockIndex, renderedBlockElements } from "./anchor-map";

// ── a DOM stand-in ─────────────────────────────────────────────────────────────────────────────────
class FakeNode {
  nodeType = 0;
  parentNode: FakeNode | null = null;
  childNodes: FakeNode[] = [];
  constructor(public ownerDocument: FakeDocument) {}
  get textContent(): string { return this.nodeType === 3 ? (this as unknown as FakeText).data : this.childNodes.map((c) => c.textContent).join(""); }
}
class FakeText extends FakeNode { nodeType = 3; constructor(doc: FakeDocument, public data: string) { super(doc); } }
class FakeElement extends FakeNode {
  nodeType = 1;
  attrs = new Map<string, string>();
  scrollTop = 0;
  /** the box a test gives the element; none means no layout (every edge 0, no client rects) */
  box: { top: number; bottom: number } | null = null;
  constructor(doc: FakeDocument, public tagName: string) { super(doc); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  appendChild(n: FakeNode): FakeNode { this.childNodes.push(n); n.parentNode = this; return n; }
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
  if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
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

test("topVisibleIndex: a floated figure reaching below the paragraphs beside it is passed over for the first paragraph ending below the edge; a figure whose successor ends below the edge is the top box itself", () => {
  // boxes: heading 40, a figure (index 1) reaching to 250, three paragraphs beside it ending at 120, 160, 200
  const floated = [40, 250, 120, 160, 200];
  assert.equal(topVisibleIndex(5, (i) => floated[i], 130), 3, "the reader is beside the figure at the third paragraph: that paragraph");
  assert.equal(topVisibleIndex(5, (i) => floated[i], 90), 1, "the second paragraph beside it still ends below the edge: the figure, first in the order, as in a plain column");
  assert.equal(topVisibleIndex(5, (i) => floated[i], 50), 1, "the edge above every paragraph beside the figure: the figure");
  assert.equal(topVisibleIndex(5, (i) => floated[i], 210), 1, "past the last paragraph beside it, the figure still shows: the figure (nothing ends below the edge but it)");
  const farFig = [40, 900, ...Array.from({ length: 12 }, (_, i) => 60 + i * 20)];
  assert.equal(topVisibleIndex(farFig.length, (i) => farFig[i], 500), farFig.length, "a figure more than the tail's boxes before the end is passed over there: count, no place");
  // the same figure with the paragraph after it ending below the edge: the figure is the top box, as in a plain column
  const column = [40, 250, 300, 340];
  assert.equal(topVisibleIndex(4, (i) => column[i], 130), 1);
  // a hidden element among the wrapped paragraphs is skipped on the way
  const withHidden = [40, 250, 120, NaN, 160, 200];
  assert.equal(topVisibleIndex(6, (i) => withHidden[i], 130), 4);
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
test("followPlace: the block itself when intact (unchanged text, an insertion above, moved whole); the block before it (step 1) when rewritten; the block after it (step -1) when the block before is rewritten too; the edit's start with all three gone", () => {
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
  assert.deepEqual(followPlace(place(doc, 5), three), { at: at(doc, PARA(2)), step: 0 }, "all three rewritten: where the edit begins (the insertion under paragraph 1)");
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
