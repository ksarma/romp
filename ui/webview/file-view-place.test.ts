// The reader's place, the pure parts (reader-place.ts; plans/markdown-viewer.md Slice 2): the top-visible search over a
// column of boxes, the follow of a kept span through an edit, and the anchor map's block-table reads and its Raw row
// span, run under node over the anchor-map suite's DOM stand-in (marked's output parsed into a minimal tree, no
// jsdom). The DOM halves (readPlace, seatPlace) need a layout and are measured in headless Chromium by
// file-view-place-browser.test.ts; here they are shown to stand down over a tree with no layout (every box at 0, 0),
// which is what keeps every node test over the viewer unchanged. Source pins hold the order file-view.ts runs the
// keeper in: the place read before the swap, seated after the hooks (the selection keeper's order), and the width reflow
// and text-size step seating too. Synthetic fixtures only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { marked } from "marked";
import { topVisibleIndex, blockIndexAt, followPlace, readPlace, seatPlace, type Place } from "./reader-place";
import { sourceBlockSpans, renderedBlockIndex, renderedBlockElements, rawRowSpan, rawRowForOffset } from "./anchor-map";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = read("file-view.ts");

// ── a DOM stand-in: the anchor-map suite's minimal tree, plus the members reader-place reads ───────────
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
  get length(): number { return this.data.length; }
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
  scrollTop = 0;
  /** the box a test gives the element (top, bottom); none by default, so getBoundingClientRect answers all zeros */
  box: { top: number; bottom: number } | null = null;
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
  get className(): string { return this.attrs.get("class") || ""; }
  get nextElementSibling(): FakeElement | null {
    const p = this.parentNode; if (!p) return null;
    for (let i = p.childNodes.indexOf(this) + 1; i < p.childNodes.length; i++) if (p.childNodes[i] instanceof FakeElement) return p.childNodes[i] as FakeElement;
    return null;
  }
  matches(sel: string): boolean {
    const m = /^([a-z]+)?((?:\.[\w-]+)*)$/.exec(sel);
    if (!m) throw new Error("stand-in: unsupported selector " + sel);
    if (m[1] && m[1].toUpperCase() !== this.tagName) return false;
    const classes = this.className.split(/\s+/);
    return (m[2].match(/\.[\w-]+/g) || []).every((c) => classes.includes(c.slice(1)));
  }
  querySelectorAll(sel: string): FakeElement[] {
    const out: FakeElement[] = [];
    const walk = (n: FakeNode) => { for (const c of n.childNodes) { if (c instanceof FakeElement) { if (c.matches(sel)) out.push(c); walk(c); } } };
    walk(this); return out;
  }
  querySelector(sel: string): FakeElement | null { return this.querySelectorAll(sel)[0] || null; }
  getBoundingClientRect(): { top: number; bottom: number; left: number; right: number; width: number; height: number } {
    const b = this.box || { top: 0, bottom: 0 };
    return { top: b.top, bottom: b.bottom, left: 0, right: 0, width: 0, height: b.bottom - b.top };
  }
}
class FakeDocument {
  createElement(tag: string): FakeElement { return new FakeElement(this, tag.toUpperCase()); }
  createTextNode(s: string): FakeText { return new FakeText(this, s); }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
const decodeEntities = (s: string) => s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
  if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
  return e in NAMED ? NAMED[e] : m;
});
/** marked's output as a tree: tags, text, entities; void elements do not nest; a newline right after <pre> is dropped. */
function parseHTML(doc: FakeDocument, html: string): FakeNode[] {
  html = html.replace(/\r\n?/g, "\n");
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

/** `.fileview-body > div.fileview-md > marked output`, the blocks given boxes stacked `h` px apart from `top0`. */
function rendered(src: string, top0 = 0, h = 40): { body: FakeElement; md: FakeElement; blocks: FakeElement[] } {
  const doc = new FakeDocument();
  const body = doc.createElement("div"); body.setAttribute("class", "fileview-body"); body.box = { top: 100, bottom: 700 };
  const md = doc.createElement("div"); md.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(src) as string)) md.appendChild(n);
  body.appendChild(md);
  const blocks = md.childNodes.filter((n): n is FakeElement => n instanceof FakeElement);
  blocks.forEach((b, i) => { b.box = { top: top0 + i * h, bottom: top0 + (i + 1) * h - 8 }; });
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
const DOC = "# Report\n\n" + Array.from({ length: 10 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";

// ── topVisibleIndex ────────────────────────────────────────────────────────────────────────────────
test("topVisibleIndex: the first box whose bottom lies below the edge; count when none; a floated figure reaching below the paragraphs beside it is passed over for the first of those ending below the edge; a hidden box (every edge 0) reads as above", () => {
  const bottoms = [40, 80, 120, 160, 200];
  const at = (i: number) => bottoms[i];
  assert.equal(topVisibleIndex(5, at, -1), 0, "everything below the edge: the first");
  assert.equal(topVisibleIndex(5, at, 40), 1, "a bottom ON the edge is not below it");
  assert.equal(topVisibleIndex(5, at, 39.5), 0);
  assert.equal(topVisibleIndex(5, at, 130), 3);
  assert.equal(topVisibleIndex(5, at, 200), 5, "none below: count");
  assert.equal(topVisibleIndex(0, at, 0), 0, "no boxes");
  // a floated figure (index 1) reaching below the paragraphs wrapping beside it: whichever box the search lands on, the
  // top block is the first paragraph beside the figure that ends below the edge, the one the reader is reading (the
  // figure, kept instead, is one row in Raw and moves as the paragraphs beside it grow taller; the Slice 2 review)
  const floated = [40, 250, 120, 160, 200];
  assert.equal(topVisibleIndex(5, (i) => floated[i], 130), 3);
  assert.equal(topVisibleIndex(5, (i) => floated[i], 50), 1, "the edge above every paragraph beside it: the figure");
  assert.equal(topVisibleIndex(5, (i) => floated[i], 210), 1, "past the last paragraph beside it, the figure still showing: the figure, read back from the end");
  // a hidden box (NaN: no layout) on the search's path below the reader is read around, in the search and in the answer
  const withNaN = [40, 80, 120, NaN, 160, 200];
  assert.equal(topVisibleIndex(6, (i) => withNaN[i], 100), 2);
  assert.equal(topVisibleIndex(6, (i) => withNaN[i], 130), 4, "the hidden box where the top block would be: the next with a layout");
  // a hidden element between two boxes reads as above the edge, and the search still finds the first showing box after it
  const hidden = [40, 0, 120, 160, 200];
  assert.equal(topVisibleIndex(5, (i) => hidden[i], 100), 2);
});

// ── followPlace ────────────────────────────────────────────────────────────────────────────────────
test("followPlace: unchanged text keeps the offset; an insertion above shifts it by the inserted length; one below leaves it; a rewrite of the block itself is placed by the block before it (an insertion above at the same time included); with that block gone too, by the block after; with all three gone, the nearest block before that stands; with none, the edit's start", () => {
  const at = (s: string, i: number) => s.indexOf(PARA(i));
  const span = (source: string, i: number) => ({ start: at(source, i), end: at(source, i) + PARA(i).length });
  const place = (source: string, i: number): Place => ({ source, view: "rendered", ...span(source, i), top: -12, height: 32, atTop: false, prev: i > 1 ? span(source, i - 1) : null, next: i < 10 ? span(source, i + 1) : null });
  assert.deepEqual(followPlace(place(DOC, 5), DOC), { at: at(DOC, 5), step: 0 }, "the same text: the same offset");
  const above = DOC.replace(PARA(2), "Inserted A: new words.\n\nInserted B: more new words.\n\n" + PARA(2));
  assert.deepEqual(followPlace(place(DOC, 5), above), { at: at(above, 5), step: 0 }, "twenty (here two) paragraphs above: shifted by their length");
  assert.equal(at(above, 5) - at(DOC, 5), "Inserted A: new words.\n\nInserted B: more new words.\n\n".length);
  const below = DOC.replace(PARA(8), PARA(8) + "\n\nAppended: words after the reader.");
  assert.deepEqual(followPlace(place(DOC, 5), below), { at: at(DOC, 5), step: 0 }, "an edit below: the offset stands");
  const rewritten = DOC.replace(PARA(5), "Rewritten 5: the session replaced this paragraph.");
  assert.deepEqual(followPlace(place(DOC, 5), rewritten), { at: at(DOC, 4), step: 1 }, "the block itself rewritten: the block before it, and `step` 1 says the one after that");
  const both = above.replace(PARA(5), "Rewritten 5: the session replaced this paragraph.");
  assert.deepEqual(followPlace(place(DOC, 5), both), { at: at(above, 4), step: 1 }, "inserted above AND rewritten: the block before, followed through the insertion (the edit's start would be twenty paragraphs up)");
  const rewrittenFrom4 = DOC.replace(PARA(4) + "\n\n" + PARA(5), "Rewritten 4 and 5: two paragraphs became one.");
  assert.deepEqual(followPlace(place(DOC, 5), rewrittenFrom4), { at: at(rewrittenFrom4, 6), step: -1 }, "the block before rewritten too: the block after, and `step` -1 says the one before that (the Slice 2 review: this fell to the edit's start, and with an insertion above, to the top)");
  const three = rewrittenFrom4.replace(PARA(6), "Rewritten 6.");
  assert.deepEqual(followPlace(place(DOC, 5), three), { at: at(three, 3), step: 1 }, "all three rewritten: the nearest block before them that stands (paragraph 3), and the kept block is the one after it, the first of the rewritten run (the review's second round: this fell to the edit's start)");
  assert.deepEqual(followPlace(place(DOC, 5), "Every paragraph rewritten, the heading too.\n"), { at: 0, step: 0 }, "no block standing on either side: the edit's start");
  // the block's text moved whole to another place inside the edited region: followed there
  const swapped = DOC.replace(PARA(5) + "\n\n" + PARA(6), PARA(6) + "\n\n" + PARA(5));
  assert.deepEqual(followPlace(place(DOC, 5), swapped), { at: swapped.indexOf(PARA(5)), step: 0 }, "two blocks swapped: the block is found where it went");
  // a block read in the Raw view follows the same way
  assert.deepEqual(followPlace({ source: DOC, view: "raw", start: at(DOC, 7), end: at(DOC, 7) + 12, top: 3, height: 20, atTop: false, prev: null, next: null }, above), { at: at(above, 7), step: 0 });
  // the whole text replaced: the offset is clamped into the new text
  assert.deepEqual(followPlace(place(DOC, 9), "short"), { at: 0, step: 0 });
});

// ── the anchor map's block table ──────────────────────────────────────────────────────────────────
test("sourceBlockSpans / renderedBlockIndex / renderedBlockElements: element k of the Rendered view is block k of the table, and the block its source span; a refused block (a table, a code block) answers both; whitespace between blocks is no block's; a comment is a block with no element, and blockIndexAt places an offset inside it on the comment", () => {
  const src = "# Title\n\nFirst paragraph here.\n\n| a | b |\n| - | - |\n| 1 | 2 |\n\n```\ncode line\n```\n\nLast paragraph.\n";
  const { md, blocks } = rendered(src);
  assert.deepEqual(blocks.map((b) => b.tagName), ["H1", "P", "TABLE", "PRE", "P"]);
  const spans = sourceBlockSpans(src);
  assert.equal(spans.length, 5);
  assert.deepEqual(blocks.map((b) => renderedBlockIndex(El(md), src, El(b))), [0, 1, 2, 3, 4], "element k is block k");
  assert.deepEqual(spans[0], { start: 0, end: "# Title".length });
  assert.deepEqual(spans[1], { start: src.indexOf("First"), end: src.indexOf("here.") + 5 });
  assert.deepEqual(spans[2], { start: src.indexOf("| a |"), end: src.indexOf("| 1 | 2 |") + "| 1 | 2 |".length }, "the table, a refused block, still spans its rows");
  assert.deepEqual(spans[3], { start: src.indexOf("```"), end: src.lastIndexOf("```") + 3 }, "the code block too");
  assert.deepEqual(spans[4], { start: src.indexOf("Last"), end: src.length - 1 });
  for (let b = 0; b < 5; b++) assert.deepEqual(renderedBlockElements(El(md), src, b), [El(blocks[b])], "block " + b + " renders as element " + b + ", refused or not");
  // whitespace text between blocks is no block
  const ws = md.childNodes.find((n) => n instanceof FakeText);
  assert.ok(ws, "marked leaves newlines between the blocks");
  assert.equal(renderedBlockIndex(El(md), src, ws as unknown as Node), -1);
  // offset to block: the block whose start is the largest at or below the offset
  assert.equal(blockIndexAt(spans, 0), 0);
  assert.equal(blockIndexAt(spans, src.indexOf("paragraph here")), 1, "inside the paragraph");
  assert.equal(blockIndexAt(spans, src.indexOf("| 1 |")), 2, "inside the table: its block, though refused");
  assert.equal(blockIndexAt(spans, src.indexOf("code line")), 3);
  assert.equal(blockIndexAt(spans, src.indexOf("First") - 1), 0, "the blank line after a block: the block before it");
  assert.equal(blockIndexAt(spans, src.length + 50), 4, "past the end: the last block");
  assert.equal(blockIndexAt(spans, -1), -1, "before the first block: nothing stands there");
  // a block with no element of its own (an HTML comment) is a block of the table with no element; the seat reads the
  // nearest block with a box instead (reader-place.ts renderedBoxNear), and its neighbours are paired past it
  const withComment = "First.\n\n<!-- a note to self -->\n\nSecond.\n";
  const r2 = rendered(withComment);
  const cs = sourceBlockSpans(withComment);
  assert.equal(r2.blocks.length, 2, "the comment renders nothing");
  assert.equal(cs.length, 3, "and is a block of the table");
  assert.equal(blockIndexAt(cs, withComment.indexOf("<!--") + 3), 1, "an offset in the comment: the comment's block");
  assert.deepEqual(renderedBlockElements(El(r2.md), withComment, 1), [], "which has no element");
  assert.deepEqual([0, 2].map((b) => renderedBlockElements(El(r2.md), withComment, b)), [[El(r2.blocks[0])], [El(r2.blocks[1])]], "the paragraphs before and after it keep their elements");
});

test("rawRowSpan: a row answers its line's span in the file (CRLF included), a row not of the view null; rawRowForOffset pairs with it", () => {
  const src = "line one\r\nline two\r\n\r\nline four\r\n";
  const { code, rows } = raw(src.replace(/\r\n/g, "\n"));
  assert.equal(rows.length, 4);
  assert.deepEqual(rawRowSpan(El(code), src, El(rows[0])), { start: 0, end: 8 });
  assert.deepEqual(rawRowSpan(El(code), src, El(rows[1])), { start: 10, end: 18 }, "after the CRLF");
  assert.deepEqual(rawRowSpan(El(code), src, El(rows[2])), { start: 20, end: 20 }, "an empty row: an empty span");
  assert.deepEqual(rawRowSpan(El(code), src, El(rows[3])), { start: 22, end: 31 });
  const doc = new FakeDocument(); const stranger = doc.createElement("span"); stranger.setAttribute("class", "fv-cl");
  assert.equal(rawRowSpan(El(code), src, El(stranger)), null, "not a row of this view");
  for (const [off, i] of [[0, 0], [7, 0], [9, 0], [10, 1], [21, 2], [25, 3], [400, 3]] as const) assert.equal(rawRowForOffset(El(code), src, off), El(rows[i]), "offset " + off + " sits in row " + i);
  assert.equal(rawRowSpan(El(code), "line one\nline TWO\n\nline four\n", El(rows[1])), null, "rows that disagree with the source answer nothing");
});

// ── readPlace / seatPlace over the stand-in ───────────────────────────────────────────────────────
test("readPlace: the top-visible block's span, height and view in the Rendered view and the Raw view, where a blank row between blocks reads as the block after it; null over a tree with no layout, over the loader, and when the edge is past every block", () => {
  // blocks 40px apart from y=0, the body's top at 100: block 2 (y 80..112) is the first whose bottom lies below the edge
  const r = rendered(DOC, 0, 40);
  const p = readPlace(r.body as unknown as HTMLElement, DOC)!;
  assert.ok(p, "a place");
  assert.equal(DOC.slice(p.start, p.end), PARA(2), "the block under the edge: paragraph 2 (block 2 of heading, 1, 2, ...)");
  assert.equal(p.top, 80 - 100, "its top edge, 20px above the body's top");
  assert.equal(p.height, 32, "the block's box"); assert.equal(p.view, "rendered"); assert.equal(p.atTop, true, "the body at scrollTop 0");
  assert.equal(p.source, DOC);
  assert.equal(DOC.slice(p.prev!.start, p.prev!.end), PARA(1), "and the block before it, the fallback");
  assert.equal(DOC.slice(p.next!.start, p.next!.end), PARA(3), "and the block after it, the second fallback");
  // the Raw view: rows 20px apart from y=0; row 5 (y 100..120) is the first ending below the edge, and it is the blank
  // line between paragraphs 2 and 3, which belongs to no block: the place is paragraph 3, one row below the edge (the
  // Slice 2 review: read as its own place, the blank row seated paragraph 2, the block the reader had scrolled past)
  const w = raw(DOC, 0, 20);
  const q = readPlace(w.body as unknown as HTMLElement, DOC)!;
  const lines = DOC.split("\n");
  assert.equal(lines[5], "", "row 5 is a blank line between two paragraphs");
  assert.equal(DOC.slice(q.start, q.end), PARA(3), "the block after the blank row");
  assert.equal(q.top, 20, "paragraph 3's row, one row below the body's top edge"); assert.equal(q.height, 20); assert.equal(q.view, "raw");
  assert.equal(DOC.slice(q.prev!.start, q.prev!.end), PARA(2), "the block before it");
  // no layout (every box 0,0: the node stand-ins): nothing is in view, so nothing is kept
  const flat = rendered(DOC); for (const b of flat.blocks) b.box = null;
  assert.equal(readPlace(flat.body as unknown as HTMLElement, DOC), null);
  // the loader holds the body
  const doc = new FakeDocument(); const body = doc.createElement("div"); body.box = { top: 0, bottom: 600 };
  const load = doc.createElement("div"); load.setAttribute("class", "fileview-load"); body.appendChild(load);
  assert.equal(readPlace(body as unknown as HTMLElement, DOC), null);
  // every block above the edge
  const gone = rendered(DOC, -2000, 40);
  assert.equal(readPlace(gone.body as unknown as HTMLElement, DOC), null);
});

test("seatPlace: scrolls the body by the difference between where the kept block stands and where it stood, following the span through the edit; a Rendered place seats in a Raw view at the same fraction of the block's rows; false when nothing stands at the offset", () => {
  // the reader had paragraph 5 (a 32px block) with its top 12px above the body's top edge
  const kept: Place = { source: DOC, view: "rendered", start: DOC.indexOf(PARA(5)), end: DOC.indexOf(PARA(5)) + PARA(5).length, top: -12, height: 32, atTop: false,
    prev: { start: DOC.indexOf(PARA(4)), end: DOC.indexOf(PARA(4)) + PARA(4).length }, next: { start: DOC.indexOf(PARA(6)), end: DOC.indexOf(PARA(6)) + PARA(6).length } };
  // the new view (the same text) lays paragraph 5 (block 5) at y=200, the body's top at 100: 100 below the edge, wanted 12 above
  const r = rendered(DOC, 0, 40);
  r.body.scrollTop = 500;
  assert.equal(seatPlace(r.body as unknown as HTMLElement, DOC, kept), true);
  assert.equal(r.body.scrollTop, 500 + (200 - 100) - (-12), "scrolled down by the block's distance from where it stood");
  // after an insertion above, the block is followed to its new offset and the new tree's block 7 is the one seated
  const above = DOC.replace(PARA(2), "Inserted A: new words.\n\nInserted B: more new words.\n\n" + PARA(2));
  const r2 = rendered(above, 0, 40);
  assert.deepEqual(followPlace(kept, above), { at: above.indexOf(PARA(5)), step: 0 });
  assert.equal(r2.blocks[7].textContent.startsWith("Paragraph 5:"), true, "block 7 of the new tree is paragraph 5");
  r2.body.scrollTop = 0;
  assert.equal(seatPlace(r2.body as unknown as HTMLElement, above, kept), true);
  assert.equal(r2.body.scrollTop, (280 - 100) - (-12), "paragraph 5's new element (y 280) brought to 12px above the edge");
  // inserted above and the block rewritten: the block before is followed, and the one after it, the rewritten paragraph,
  // is seated (the new tree: heading, A, B, 1, 2, 3, 4, Rewritten = index 7)
  const both = above.replace(PARA(5), "Rewritten 5: the session replaced this paragraph.");
  const r4 = rendered(both, 0, 40);
  assert.equal(r4.blocks[7].textContent.startsWith("Rewritten 5:"), true);
  r4.body.scrollTop = 0;
  assert.equal(seatPlace(r4.body as unknown as HTMLElement, both, kept), true);
  assert.equal(r4.body.scrollTop, (280 - 100) - (-12), "the rewritten paragraph brought to where the block stood");
  // the same in the Raw view: the block after paragraph 4's, the rewritten line's row; the view changed, so the reader's
  // depth (12 of 32px) is kept as the fraction of the row's 20px, 7.5px
  const w4 = raw(both, 0, 20);
  const rewrittenLine = both.slice(0, both.indexOf("Rewritten 5:")).split("\n").length - 1;
  w4.body.scrollTop = 0;
  assert.equal(seatPlace(w4.body as unknown as HTMLElement, both, kept), true);
  assert.equal(w4.body.scrollTop, (rewrittenLine * 20 - 100) - (-7.5), "row " + rewrittenLine + ", the rewritten line");
  // a Rendered place seats in the Raw view: the block's rows (here one), at the same fraction of their height
  const w = raw(DOC, 0, 20);
  const line = DOC.slice(0, DOC.indexOf(PARA(5))).split("\n").length - 1;
  w.body.scrollTop = 0;
  assert.equal(seatPlace(w.body as unknown as HTMLElement, DOC, kept), true);
  assert.equal(w.body.scrollTop, (line * 20 - 100) - (-7.5), "row " + line + " brought to where the block stood, 12/32 of its height above the edge");
  // a delta under half a pixel writes nothing
  const r3 = rendered(DOC, 0, 40); r3.blocks[5].box = { top: 88.2, bottom: 120 }; r3.body.scrollTop = 7;
  seatPlace(r3.body as unknown as HTMLElement, DOC, kept);
  assert.equal(r3.body.scrollTop, 7);
  // nothing to seat in: the loader, or an offset before the first block
  const doc = new FakeDocument(); const body = doc.createElement("div"); body.box = { top: 0, bottom: 600 }; body.appendChild(doc.createElement("div"));
  assert.equal(seatPlace(body as unknown as HTMLElement, DOC, kept), false);
  assert.equal(seatPlace(r.body as unknown as HTMLElement, DOC, { ...kept, start: -5, end: -5, prev: null, next: null }), false);
});

// ── the order file-view.ts runs the keeper in ─────────────────────────────────────────────────────
test("file-view.ts: the place is read before the text swap and seated after the hooks (the selection keeper's order); the width reflow seats the place read at scroll time; a text-size step reads and seats around its reflow; the URL viewer's switch seats too", () => {
  const local = VIEW.split("export function openFileView(")[1].split("\nexport function ")[0];
  assert.match(local, /const kept = keptPlace\(\);[^\n]*\n\s*body\.replaceChildren\(rendered \? mdBlock\(text, \{ kind: "file", path, sid: sid \|\| null \}\) : codeBlock\(text, path, true\)\);[^\n]*\n\s*fireRendered\(\);[^\n]*\n\s*shownText = text;\n\s*seat\(kept\);/,
    "read, swap, hooks, then seat over the new text");
  assert.match(local, /const seat = \(kept: Place \| null\) => \{ if \(kept && shownText !== null\) seatPlace\(body, shownText, kept\); notePlace\(\); \};/, "a seat reads the place anew after it");
  assert.match(local, /const notePlace = \(\) => \{ if \(shownText !== null && textShowing\(\)\) \{ place = readPlace\(body, shownText\); placeWidth = body\.clientWidth; placeScrollTop = body\.scrollTop; \} \};/);
  // under a width the last read did not see, the browser's own adjustments are skipped, each by its signature: the clamp
  // (the body landed at its end coming from above it) and the anchoring adjustment (the kept block's top edge within a
  // pixel of where it stood); a scroll made on purpose in the same task as the width change (the panel's reveal) is read,
  // so the repaint holds it
  assert.match(local, /const clamped = \(\): boolean => body\.scrollTop < placeScrollTop && body\.scrollTop >= body\.scrollHeight - body\.clientHeight - 1;/, "the clamp's signature");
  assert.match(local, /const anchored = \(\): boolean => \{\n\s*if \(!place \|\| place\.source !== shownText \|\| !textShowing\(\)\) return false;\n\s*const top = keptBlockTop\(body, place\);\n\s*return top !== null && Math\.abs\(top - place\.top\) <= 1;/,
    "the anchoring's signature: the kept block's own top edge (reader-place.ts keptBlockTop) within a pixel of where it stood");
  assert.match(local, /body\.addEventListener\("scroll", \(\) => \{\n\s*if \(placeFrame\) return;\n\s*const read = \(\) => \{ placeFrame = 0; if \(body\.clientWidth === placeWidth \|\| !\(clamped\(\) \|\| anchored\(\)\)\) notePlace\(\); \};/,
    "the scroll-time read, once per frame: every scroll under the width last read, and under a new width every scroll but the browser's own, the clamp and the anchoring adjustment");
  assert.match(local, /paintedWidth = seenWidth;\n\s*if \(textShowing\(\)\) \{ fireRenderedKeepingSelection\(\); seat\(place\); \}/, "the width reflow seats the tracked place");
  assert.match(local, /const kept = textShowing\(\) \? keptPlace\(\) : null;[^\n]*\n\s*applyTextSize\(\);\n\s*if \(textShowing\(\)\) \{ fireRenderedKeepingSelection\(\); seat\(kept\); \}/, "a text-size step reads before the size changes and seats after the hooks");
  const url = VIEW.split("export function openUrlView(")[1].split("\nexport function ")[0];
  assert.match(url, /const kept = shownText === null \? null : readPlace\(body, shownText\);[^\n]*\n\s*body\.replaceChildren\(fmt\.md === "rendered"\n[^\n]*\n[^\n]*\n\s*shownText = text;\n\s*if \(kept\) seatPlace\(body, text, kept\);/, "the URL viewer reads before its swap and seats after it");
  // the note bar: a child of the card above the body row, in both builders' place (the fallback editor's calls noteBar now)
  assert.match(local, /bar2\.textContent = msg;\n\s*box\.insertBefore\(bar2, main\);/);
  assert.equal((local.match(/bar2\.id = "fileview-save-err";/g) || []).length, 1, "one builder of the bar");
  assert.match(local, /enterFallback\(\);\n\s*noteBar\(why \+ " — editing in the plain fallback editor\."\);/, "the fallback editor's notice goes through noteBar");
  assert.match(local, /document\.getElementById\("fileview-save-err"\)\?\.remove\(\);\n\s*\/\/ per the loading-state rule the chunk wait shows the romp loader/, "the editor's entry removes a standing notice, as the body swap used to");
  assert.match(local, /document\.getElementById\("fileview-save-err"\)\?\.remove\(\);\n\s*renderBody\(\);\n\s*\/\/ a fetch that landed while the editor was up/, "the editor's exit removes the edit's notices, as the repaint used to");
  // the float hides on the body's scroll, installed with the float's other listeners (the constructor), not in installLayout
  const PANEL = read("file-comments.ts");
  assert.match(PANEL, /hideFloatOnScroll = \(\) => \{\n\s*if \(this\.float\.hidden\) return;\n\s*const was = this\.floatAt, now = this\.floatSubjectRect\(\);\n\s*if \(was && now && Math\.abs\(now\.top - was\.top\) < 1 && Math\.abs\(now\.right - was\.right\) < 1\) return;[^\n]*\n\s*this\.hideFloat\(\);\n\s*\};/,
    "hides on the body's scroll unless the passage stayed within a pixel of where the button was offered (Chromium's anchoring adjustment)");
  assert.match(PANEL, /ctx\.body\(\)\.addEventListener\("scroll", this\.hideFloatOnScroll, \{ passive: true \}\);\n\s*ctx\.onSelection\(\(sel\) => this\.onSelection\(sel\)\);/, "beside the selection hook in the constructor");
  assert.match(PANEL, /this\.ctx\.body\(\)\.removeEventListener\("scroll", this\.hideFloatOnScroll\);/, "and removed with the float at dispose");
  const install = PANEL.split("private installLayout(row: HTMLElement): void {")[1].split("\n  }\n")[0];
  assert.doesNotMatch(install, /hideFloatOnScroll/, "not among installLayout's scroll listeners, which feed the margin lock's mirrorScroll and act in the margin layout alone");
  // the sheets: no overflow-anchor rule (the swap never relied on anchoring, and anchoring helps after the seat when a
  // figure above loads late), and the row declares no container of its own
  for (const f of ["styles.css", "feed.css"]) {
    const css = read(f);
    assert.doesNotMatch(css, /overflow-anchor/, f + ": no overflow-anchor");
    assert.match(css, /\n\.fileview-main \{ flex: 1 1 auto; min-height: 0; display: flex; \}\n/, f + ": the row without container-type");
    assert.match(css, /\n\.fileview > \.fileview-err \{ flex: 0 0 auto; \}\n/, f + ": the note bar's rule");
  }
});
