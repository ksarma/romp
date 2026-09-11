// The reader's place at the edge of a CLOSED `<details>`, over a DOM stand-in that lays the fold out as Chromium does
// (plans/markdown-viewer.md Slice 5, item 1b; the Slice 5 review, round 1). The rule: a `<summary>` is a row of the
// wrapper's block's own and is passed over, and a closed details reads the block after it (reader-place.ts readRendered).
// file-view-place-blocks.test.ts pins that rule over a stand-in whose shut content has NO box, the layout the rule was
// written for. Chromium 151 lays a shut fold out otherwise: the content of a closed `<details>` is skipped through its
// `::details-content` pseudo-element's content-visibility: hidden, and a skipped element KEEPS a box on a forced read
// (getBoundingClientRect answers a full rect and one client rect, the blocks stacked from where the fold's content would
// open, so the first hidden paragraph's box coincides with the block after the fold's); only checkVisibility() says the
// element is not shown (md-config-goto-closed-details-browser.test.ts found the same phantom under a highlight, and
// anchor-map-obsidian.test.ts records it for the trim). Read by its rect alone, the hidden paragraph was the place: its
// box ends below the edge like the visible block's, so the Raw switch seated the fold's hidden source at the edge, the
// summary's row above it, where the reader had the block after the fold in view (the review: paragraph 11's row at the
// edge for paragraph 16, and the way back 26px off at 900px). Now boxOf asks checkVisibility where the browser offers it:
// an element the browser does not show has no layout for the place, whatever its rect says, on the read side (the fold
// at the edge reads the block after it) and on the seat side (a Raw row of the fold's hidden source seats no phantom;
// its block has no box, the blocks before it inside the fold none, and the wrapper's own block is refused, so nothing is
// seated and the body stands, as it does for every pairing the map cannot confirm). Where the browser offers no
// checkVisibility the rect alone decides, as before. With that alone the round trip from a shut fold's edge lost the
// place by the fold's source height (370px at 900px): the Raw seat put the block after the fold where it was, so the
// fold's closing row (`</details>`) was the top Raw row, its block owns no element, and its seat walked back through the
// fold's unshown paragraphs to the wrapper's refused block and seated nothing. So the Raw read treats a row of a closing
// tag alone as it treats a blank row between blocks: the block after it is the place (the third test; a closing tag that
// is the document's last block stays its own). The review's round 2 widened that rule and added a second (the third
// and fourth tests): a Raw row of any block that renders nothing (closing tags alone, one or several, `</details>\n</div>`;
// a comment) or whose own element is never seated (a wrapper's html block: its `<details>` or `<div align="center">` row,
// its `<summary>`, a README's `<h1>` and `<p>` lead rows, an `<img>` line, and the blank row before the opener) reads as
// the block after it, through a run of such blocks (the owner's ruling on the opener rows; before, the wrapper's block
// was the place and its refused seat lost a fold title's round trip by 26 to 203px); and a Raw row inside a `<details>`
// keeps its own block but CARRIES the block after the fold, and after each fold that block lies in, each with its
// first row's top (Place.after), since the Raw view shows the fold's text whatever the Rendered view's fold state, which
// is the DOM's alone (file-view.ts keeps a fold as the person left it across a paint): the seat stands on the first
// carried block the view shows when the kept block is not (before, a shut fold whose summary wrapped put the fold's
// hidden rows on top of Raw after the switch, the way back refused them, and the reader landed 361 to 562px down). The
// stand-in's elements answer checkVisibility as Chromium does (false under a closed details, outside its summary); the
// real thing is measured in file-view-place-closed-details-browser.test.ts. Synthetic fixtures only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { marked } from "marked";
import { readPlace, seatPlace, type Place } from "./reader-place";
import { sourceBlockSpans, renderedBlockIndex, renderedBlockWrappers } from "./anchor-map";
import { hideEdges, sameNodes } from "../test-dom-shim";

// ── a DOM stand-in: marked's output as nodes, a box per element, checkVisibility as Chromium answers it ────────
class FakeNode {
  nodeType = 0;
  parentNode!: FakeNode | null;
  childNodes!: FakeNode[];
  constructor() {
    // the edges are non-enumerable, and so is every other object the node holds (hideEdges, ui/test-dom-shim.ts): a
    // failing assertion's dump of a node is its own primitives, never the tree it hangs in
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get textContent(): string { return this.nodeType === 3 ? (this as unknown as FakeText).data : this.childNodes.map((c) => c.textContent).join(""); }
}
class FakeText extends FakeNode { nodeType = 3; constructor(public data: string) { super(); hideEdges(this); } }
class FakeElement extends FakeNode {
  nodeType = 1;
  attrs = new Map<string, string>();
  scrollTop = 0;
  /** the box a test gives the element; none means no rect at all (every edge 0, no client rects) */
  box: { top: number; bottom: number } | null = null;
  constructor(public tagName: string) { super(); hideEdges(this); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeAttribute(n: string): void { this.attrs.delete(n); }
  appendChild(n: FakeNode): FakeNode { this.childNodes.push(n); n.parentNode = this; return n; }
  get className(): string { return this.attrs.get("class") || ""; }
  elements(): FakeElement[] { return this.childNodes.filter((n): n is FakeElement => n instanceof FakeElement); }
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
  getClientRects(): unknown[] { return this.box ? [this.getBoundingClientRect()] : []; }
  /** As Chromium answers it: false for an element inside a closed `<details>` that is not (inside) its summary, whatever
   *  box the element answers; true otherwise. */
  checkVisibility(): boolean {
    for (let child: FakeNode = this, p = this.parentNode; p; child = p, p = p.parentNode) {
      if (p instanceof FakeElement && p.tagName === "DETAILS" && p.getAttribute("open") === null && !(child instanceof FakeElement && child.tagName === "SUMMARY")) return false;
    }
    return true;
  }
}
class FakeDocument {
  /** `rectOnly`: a stand-in whose elements offer no checkVisibility (a browser before the API), so the rect alone decides */
  constructor(public rectOnly = false) {}
  createElement(tag: string): FakeElement {
    const el = new FakeElement(tag.toUpperCase());
    if (this.rectOnly) Object.defineProperty(el, "checkVisibility", { value: undefined, enumerable: false, configurable: true });
    return el;
  }
  createTextNode(s: string): FakeText { return new FakeText(s); }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
const decodeEntities = (s: string) => s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
  if (e[0] === "#") { const cp = parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10); return Number.isFinite(cp) && cp <= 0x10ffff ? String.fromCodePoint(cp) : "�"; }
  return e in NAMED ? NAMED[e] : m;
});
/** marked's output as a tree: tags, text, entities; void elements do not nest; a newline right after <pre> is dropped. */
function parseHTML(doc: FakeDocument, html: string): FakeNode[] {
  const root = doc.createElement("ROOT");
  let cur: FakeElement = root;
  const re = /<!--[\s\S]*?-->|<\/?([a-zA-Z][\w-]*)([^>]*)>|([^<]+)/g;
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
 *  parses to the elements the map paired it with, and refuses the wrapper's own block (one parsed against the wrapper
 *  and its summary), the refusal the seat case below reaches. */
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

const PARA = (i: number) => `Paragraph ${i}: some words of the report, enough to make a line.`;
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
/** the heading, paragraphs 1 to 4, a details holding paragraphs 5 and 6 after its summary, paragraphs 7 to 10 */
const fold = (open: boolean) => "# Report\n\n" + paras(1, 4) + "\n\n<details" + (open ? " open" : "") + ">\n<summary>Folded one</summary>\n\n" + paras(5, 6) + "\n\n</details>\n\n" + paras(7, 10) + "\n";
const GAP = 8, H_BLOCK = 40, EDGE = 100;

type Scene = { body: FakeElement; md: FakeElement; blocks: FakeElement[]; det: FakeElement; summary: FakeElement; hidden: FakeElement[]; p7: FakeElement };
/** `.fileview-body > div.fileview-md > marked output`, the body's top edge at 100 and every top-level block 40px, 8 apart,
 *  stacked from `top0`. The details is laid out as Chromium lays a fold out: OPEN, it is as tall as its summary and its two
 *  paragraphs stacked inside it; CLOSED, it is as tall as its summary alone, and its two paragraphs, skipped and not shown,
 *  still answer boxes stacked from the top of the block after the fold, the first coinciding with that block's. */
function scene(open: boolean, top0 = 0, rectOnly = false): Scene {
  const doc = new FakeDocument(rectOnly);
  const body = doc.createElement("div"); body.setAttribute("class", "fileview-body"); body.box = { top: EDGE, bottom: EDGE + 600 };
  const md = doc.createElement("div"); md.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(fold(open)) as string)) md.appendChild(n);
  body.appendChild(md);
  const blocks = md.elements();
  const det = blocks[5];
  assert.equal(det.tagName, "DETAILS", "the fixture: the details is the sixth top-level element");
  assert.equal(det.getAttribute("open") !== null, open, "the fixture: the details' open attribute");
  const [summary, ...hidden] = det.elements();
  assert.deepEqual([summary.tagName, hidden.map((k) => k.tagName), hidden.map((k) => k.textContent)], ["SUMMARY", ["P", "P"], [PARA(5), PARA(6)]], "the fixture: the summary and the two paragraphs nested after it");
  const detH = open ? H_BLOCK + (H_BLOCK + GAP) * hidden.length : H_BLOCK;
  let y = top0;
  blocks.forEach((b) => { const h = b === det ? detH : H_BLOCK; b.box = { top: y, bottom: y + h }; y += h + GAP; });
  summary.box = { top: det.box!.top, bottom: det.box!.top + H_BLOCK };
  const p7 = blocks[6];
  assert.equal(p7.textContent, PARA(7), "the fixture: paragraph 7 follows the details at the top level (the closing tag renders nothing)");
  let z = open ? summary.box.bottom + GAP : p7.box!.top;
  for (const k of hidden) { k.box = { top: z, bottom: z + H_BLOCK }; z += H_BLOCK + GAP; }
  return { body, md, blocks, det, summary, hidden, p7 };
}
/** Every box under `root` moved by `d` px (the root's own too, when it has one). */
function shiftBoxes(root: FakeElement, d: number): void {
  if (root.box) root.box = { top: root.box.top + d, bottom: root.box.bottom + d };
  for (const c of root.childNodes) if (c instanceof FakeElement) shiftBoxes(c, d);
}
/** The Rendered view scrolled so that `el`'s box straddles the body's top edge, `depth` px into it. */
const toEdge = (md: FakeElement, el: FakeElement, depth: number): void => shiftBoxes(md, EDGE - depth - el.box!.top);
const textOf = (doc: string, p: Place | null) => (p ? doc.slice(p.start, p.end) : null);

test("readPlace: a paragraph inside a CLOSED details keeps a box in Chromium (coinciding with the block after the fold's) but is not shown (checkVisibility false), so it has no layout for the place: the fold's summary at the edge reads the block after the fold, not the hidden paragraph (before: the hidden paragraph, and the Raw switch seated the fold's hidden source at the edge); the same fold OPEN reads its first nested paragraph; a stand-in offering no checkVisibility reads by the rect alone", () => {
  const doc = fold(false), spans = sourceBlockSpans(doc);
  const b5 = spans.findIndex((sp) => doc.slice(sp.start, sp.end) === PARA(5)), b7 = spans.findIndex((sp) => doc.slice(sp.start, sp.end) === PARA(7));
  const wb = spans.findIndex((sp) => doc.slice(sp.start, sp.end).startsWith("<details>"));
  const c = scene(false);
  // the fixture, as Chromium lays a shut fold out: the details is its summary's height, the first hidden paragraph's box IS the
  // block after the fold's, the second's sits under it, and each answers a client rect; only checkVisibility tells them apart
  assert.deepEqual(c.det.box, c.summary.box, "the fixture: a closed details is as tall as its summary");
  assert.deepEqual(c.hidden[0].box, c.p7.box, "the fixture: the first hidden paragraph's box coincides with paragraph 7's");
  assert.equal(c.hidden[0].getClientRects().length, 1, "the fixture: the hidden paragraph answers a client rect");
  assert.deepEqual([c.hidden[0].checkVisibility(), c.hidden[1].checkVisibility(), c.summary.checkVisibility(), c.det.checkVisibility(), c.p7.checkVisibility()], [false, false, true, true, true], "the fixture: checkVisibility is false for the shut content alone");
  // the block table (anchor-map.ts, Slice 5): the details is the wrapper of its block, the hidden paragraphs are their own blocks
  sameNodes(renderedBlockWrappers(El(c.md), doc, wb), [c.det], "the fixture: the details is its block's wrapper");
  assert.equal(renderedBlockIndex(El(c.md), doc, El(c.hidden[0])), b5, "the fixture: the first hidden paragraph is paragraph 5's block's");
  assert.equal(renderedBlockIndex(El(c.md), doc, El(c.p7)), b7, "the fixture: paragraph 7 is its own block's");
  // the fold's summary straddling the edge, 20px in: the summary is a row of the wrapper's block's own and is passed over; the
  // hidden paragraphs are not shown, so nothing nested ends below the edge with a layout, and the block after the fold is the
  // place, at its distance below the edge (before: paragraph 5, whose phantom box ends below the edge like paragraph 7's)
  toEdge(c.md, c.summary, 20);
  const q = readPlace(H(c.body), doc);
  assert.equal(textOf(doc, q), PARA(7), "the block after the fold is the place (before: the hidden paragraph 5)");
  assert.deepEqual([q!.start, q!.end, q!.top, q!.height], [spans[b7].start, spans[b7].end, c.p7.box!.top - EDGE, H_BLOCK], "paragraph 7's span, its box's distance below the edge and its height");
  assert.ok(q!.top > 0, "below the edge, so a seat keeps its distance (a Raw switch puts paragraph 7's row there, the fold's own rows above it)");
  // the edge inside the phantom itself (paragraph 7 straddling the edge, so the hidden paragraph 5's coinciding box does too): the
  // top-level search lands on paragraph 7, its own block, and never on the phantom, which hangs in the details above
  const c2 = scene(false); toEdge(c2.md, c2.p7, 15);
  const q2 = readPlace(H(c2.body), doc);
  assert.deepEqual([textOf(doc, q2), q2!.top], [PARA(7), -15], "paragraph 7 partway in: its own block");
  // the same fold OPEN: its content is shown, so the summary at the edge reads the first nested paragraph, below the edge inside
  // the wrapper (file-view-place-blocks.test.ts's rule, unchanged)
  const docO = fold(true), spansO = sourceBlockSpans(docO);
  const b5o = spansO.findIndex((sp) => docO.slice(sp.start, sp.end) === PARA(5));
  const o = scene(true); toEdge(o.md, o.summary, 20);
  const qo = readPlace(H(o.body), docO);
  assert.equal(textOf(docO, qo), PARA(5), "the open fold's first nested paragraph");
  assert.deepEqual([qo!.start, qo!.top], [spansO[b5o].start, o.hidden[0].box!.top - EDGE], "paragraph 5's span, below the edge by the summary's remaining height and the gap");
  assert.equal(qo!.top, 28);
  // the open fold's nested paragraph partway in: its own block (checkVisibility true, the box read as ever)
  const o2 = scene(true); toEdge(o2.md, o2.hidden[1], 10);
  assert.deepEqual([textOf(docO, readPlace(H(o2.body), docO)), readPlace(H(o2.body), docO)!.top], [PARA(6), -10], "the open fold's second paragraph, 10px in");
  // a stand-in offering no checkVisibility (a browser before the API): the rect alone decides, so the phantom reads as before
  const r = scene(false, 0, true); toEdge(r.md, r.summary, 20);
  assert.equal(typeof (r.hidden[0] as { checkVisibility?: unknown }).checkVisibility, "undefined", "the fixture: no checkVisibility on this stand-in");
  assert.equal(textOf(doc, readPlace(H(r.body), doc)), PARA(5), "without checkVisibility the hidden paragraph's rect is read as a box, as before");
});

test("seatPlace: a Raw place on a paragraph inside a CLOSED details that carries no block after the fold (a place of another making: readPlace carries one since the review's round 2, the fourth test) seats nothing and leaves the body where it stands (before: it seated the paragraph's phantom box, two blocks past the fold); one on the block after the fold seats at that block's box; the same fold OPEN seats the nested paragraph at its own box", () => {
  const doc = fold(false), spans = sourceBlockSpans(doc);
  const b6 = spans.findIndex((sp) => doc.slice(sp.start, sp.end) === PARA(6)), b7 = spans.findIndex((sp) => doc.slice(sp.start, sp.end) === PARA(7));
  // a place 3px into paragraph 6's Raw row, inside the fold's source, with no block after the fold to stand on, switched to
  // Rendered: paragraph 6 is not shown, paragraph 5 before it is not shown, and the wrapper's own block before that is refused
  // (its source parses to one element against the wrapper and its summary: ruling 2), so nothing lends a box and the body stands
  const onHidden: Place = { source: doc, view: "raw", start: spans[b6].start, end: spans[b6].end, top: -3, height: 18, atTop: false, prev: spans[b6 - 1], next: spans[b6 + 1] };
  const c = scene(false, 0); c.body.scrollTop = 500;
  const phantom = c.hidden[1].box!;
  assert.equal(seatPlace(H(c.body), doc, onHidden), false, "no seat from the fold's hidden source (before: true, the phantom box seated)");
  assert.equal(c.body.scrollTop, 500, "the body stands (before: scrolled by " + ((phantom.top - EDGE) - (-3 * H_BLOCK / 18)) + "px, to the phantom's fraction)");
  // a Raw place on paragraph 7, the block after the fold, 3px in: its own box, at the row's depth as a fraction of its height
  const onAfter: Place = { source: doc, view: "raw", start: spans[b7].start, end: spans[b7].end, top: -3, height: 18, atTop: false, prev: spans[b7 - 1], next: spans[b7 + 1] };
  const a = scene(false, 0); a.body.scrollTop = 500;
  assert.equal(seatPlace(H(a.body), doc, onAfter), true, "the block after the fold seats");
  assert.equal(a.body.scrollTop, 500 + (a.p7.box!.top - EDGE) - (-3 * H_BLOCK / 18), "paragraph 7's box at the row's depth, scaled");
  // the same fold OPEN: paragraph 6 is shown and its own box is seated
  const docO = fold(true), spansO = sourceBlockSpans(docO);
  const b6o = spansO.findIndex((sp) => docO.slice(sp.start, sp.end) === PARA(6));
  const onShown: Place = { source: docO, view: "raw", start: spansO[b6o].start, end: spansO[b6o].end, top: -3, height: 18, atTop: false, prev: spansO[b6o - 1], next: spansO[b6o + 1] };
  const o = scene(true, 0); o.body.scrollTop = 500;
  assert.equal(seatPlace(H(o.body), docO, onShown), true, "the open fold's paragraph seats");
  assert.equal(o.body.scrollTop, 500 + (o.hidden[1].box!.top - EDGE) - (-3 * H_BLOCK / 18), "the nested paragraph's own box, at the row's depth scaled");
});

/** `.fileview-body > div.fileview-code > pre > code.hljs > span.fv-cl*`, one row per line, rows `h` px apart from `top0`;
 *  the body's top edge at 100. */
function raw(src: string, top0 = 0, h = 20): { body: FakeElement; code: FakeElement; rows: FakeElement[] } {
  const doc = new FakeDocument();
  const body = doc.createElement("div"); body.setAttribute("class", "fileview-body"); body.box = { top: EDGE, bottom: EDGE + 600 };
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
/** The Raw view with row `k` straddling the edge `depth` px in (or `-depth` below it). */
function rawRow(src: string, k: number, depth: number): ReturnType<typeof raw> & { row: FakeElement } {
  const r = raw(src, EDGE - depth - k * 20);
  return { ...r, row: r.rows[k] };
}
/** The Raw view with the row whose text is `text` straddling the edge `depth` px in (or `-depth` below it). */
function rawAt(src: string, text: string, depth: number): ReturnType<typeof raw> & { row: FakeElement } {
  const lines = src.split("\n"); const k = lines.indexOf(text); assert.ok(k >= 0, "the fixture holds the row " + JSON.stringify(text));
  return rawRow(src, k, depth);
}
/** The line index of the row whose text is `text`. */
const lineOf = (src: string, text: string): number => { const k = src.split("\n").indexOf(text); assert.ok(k >= 0, "the fixture holds the row " + JSON.stringify(text)); return k; };
/** The span of the block whose text is `text`. */
const spanOf = (src: string, text: string) => { const spans = sourceBlockSpans(src); const b = spans.findIndex((sp) => src.slice(sp.start, sp.end) === text); assert.ok(b >= 0, "the fixture holds the block " + JSON.stringify(text)); return spans[b]; };

test("readPlace in Raw: a row of a closing tag alone (`</details>`, `</div>`, a wrapper's end, which renders no element of its own) reads as the block after it, as a blank row between blocks does, whether the row straddles the edge or starts below it, and through a run of closers (before: the closing block itself, partway in, whose seat walked back to the fold's unshown paragraphs and the wrapper's refused block, so a shut fold's Rendered-Raw-Rendered round trip lost the place by the fold's source height); a closing tag that is the document's last block stays its own place; a closing tag inside a larger html block is that block's row", () => {
  for (const open of [false, true]) {
    const doc = fold(open), spans = sourceBlockSpans(doc);
    const b7 = spans.findIndex((sp) => doc.slice(sp.start, sp.end) === PARA(7)), bc = spans.findIndex((sp) => doc.slice(sp.start, sp.end) === "</details>");
    assert.equal(bc, b7 - 1, "the fixture: the closing tag is its own block, right before paragraph 7");
    // the closing row straddling the edge, 9px in
    const r = rawAt(doc, "</details>", 9);
    const q = readPlace(H(r.body), doc)!;
    assert.equal(textOf(doc, q), PARA(7), (open ? "open" : "closed") + ": the block after the closing tag is the place (before: the closing tag's block)");
    const p7Row = r.rows[doc.split("\n").indexOf(PARA(7))];
    assert.deepEqual([q.start, q.end, q.top, q.height, q.line], [spans[b7].start, spans[b7].end, p7Row.box!.top - EDGE, 20, null], "paragraph 7's span, its first row's distance below the edge (the blank row between), one row tall, no line kept");
    assert.equal(q.top, 31, "9px of the closing row, the blank row's 20, then paragraph 7's row");
    assert.deepEqual([doc.slice(q.prev!.start, q.prev!.end), doc.slice(q.next!.start, q.next!.end)], ["</details>", PARA(8)], "its neighbours are the closing tag and paragraph 8");
    // the closing row starting 5px below the edge (the row before it ends there): the same block after it
    const r2 = rawAt(doc, "</details>", -5);
    assert.deepEqual([textOf(doc, readPlace(H(r2.body), doc)), readPlace(H(r2.body), doc)!.top], [PARA(7), 45], "a closing row below the edge: paragraph 7 at its distance");
    // a row of the fold's own paragraphs reads as ever: paragraph 6, partway in, with its line, and CARRIES the block after the
    // fold, paragraph 7, with its row's top (Place.after: the seat stands on it when the fold is shut in Rendered, the fourth test);
    // the same for the fold open in the source, since the Rendered view's fold state is the DOM's, not the source's
    const r3 = rawAt(doc, PARA(6), 4);
    const q3 = readPlace(H(r3.body), doc)!;
    assert.deepEqual([textOf(doc, q3), q3.top, !!q3.line], [PARA(6), -4, true], "a nested paragraph's row is its own place");
    assert.deepEqual(q3.after, [{ ...spans[b7], top: -4 + 4 * 20 }], (open ? "open" : "closed") + ": the place carries paragraph 7, the block after the fold, at its row's top (paragraph 6's row, a blank, the closing row, a blank, then its own)");
    // the wrapper's own rows, the opener and the summary, and the blank row before the opener read as the first nested block,
    // paragraph 5, at its row's distance, carrying paragraph 7 (before: the wrapper's block, whose seat is refused, so the fold
    // title at the pane's top lost the place on the round trip, 26px at 900 and 203 at 380)
    const kDet = lineOf(doc, "<details" + (open ? " open" : "") + ">"), k5 = lineOf(doc, PARA(5)), k7 = lineOf(doc, PARA(7));
    for (const [what, k] of [["the opener's row", kDet], ["the summary's row", kDet + 1], ["the blank row before the opener", kDet - 1]] as const) {
      const rw = rawRow(doc, k, 9);
      const qw = readPlace(H(rw.body), doc)!;
      assert.equal(textOf(doc, qw), PARA(5), (open ? "open" : "closed") + ": " + what + " reads as the first nested block (before: the wrapper's block)");
      assert.deepEqual([qw.top, qw.line, qw.after], [-9 + (k5 - k) * 20, null, [{ ...spans[b7], top: -9 + (k7 - k) * 20 }]], what + ": paragraph 5 at its row's distance, no line kept, paragraph 7 carried");
    }
  }
  // a block of two closing tags, on two lines (`</details>\n</div>`, one html block to marked) or on one (`</details></div>`), reads as
  // the block after it from either row (before: one closing tag alone was accepted, the block was its own place, and its seat put
  // the last nested paragraph at the row, 63 to 144px off)
  for (const closers of ["</details>\n</div>", "</details></div>"]) {
    const docC = "# Report\n\n<div align=\"center\">\n\n<details open>\n<summary>Inner fold</summary>\n\n" + paras(1, 2) + "\n\n" + closers + "\n\n" + PARA(3) + "\n";
    const spansC = sourceBlockSpans(docC);
    assert.equal(docC.slice(spansC[spansC.length - 2].start, spansC[spansC.length - 2].end), closers, "the fixture: the two closing tags are one block, right before paragraph 3");
    const k3 = lineOf(docC, PARA(3));
    for (const k of closers.indexOf("\n") >= 0 ? [lineOf(docC, "</details>"), lineOf(docC, "</div>")] : [lineOf(docC, closers)]) {
      const rc = rawRow(docC, k, 9);
      const qc = readPlace(H(rc.body), docC)!;
      assert.deepEqual([textOf(docC, qc), qc.top, qc.after], [PARA(3), -9 + (k3 - k) * 20, undefined], JSON.stringify(closers) + " row " + k + ": the paragraph after the closers, at its row's distance, in no fold");
    }
  }
  // a comment block renders nothing too: after a closing row it is read past with the closer (before: the walk stopped at it, and the
  // comment was the place, seated through the block before it); on its own, inside a wrapper, it reads as the block after it, and right
  // after the opener as the first nested block (before: its own place, the walk back to the wrapper's refused block seating nothing)
  const docM = "# Report\n\n" + paras(1, 2) + "\n\n<details>\n<summary>Folded</summary>\n\n" + PARA(3) + "\n\n</details>\n\n<!-- a note to self -->\n\n" + paras(4, 5) + "\n";
  const k4 = lineOf(docM, PARA(4));
  for (const k of [lineOf(docM, "</details>"), lineOf(docM, "<!-- a note to self -->")]) {
    const qm = readPlace(H(rawRow(docM, k, 9).body), docM)!;
    assert.deepEqual([textOf(docM, qm), qm.top, qm.after], [PARA(4), -9 + (k4 - k) * 20, undefined], "row " + k + " of the closer and the comment: paragraph 4 at its row's distance");
  }
  const docW = "# Report\n\n<div align=\"center\">\n\n<!-- a note to self -->\n\n" + paras(1, 2) + "\n\n<!-- another -->\n\n" + PARA(3) + "\n\n</div>\n\n" + PARA(4) + "\n";
  const qa = readPlace(H(rawAt(docW, "<!-- another -->", 9).body), docW)!;
  assert.deepEqual([textOf(docW, qa), qa.top], [PARA(3), -9 + 40], "a comment's row inside a wrapper: the block after it");
  const qo = readPlace(H(rawAt(docW, "<!-- a note to self -->", 9).body), docW)!;
  assert.deepEqual([textOf(docW, qo), qo.top], [PARA(1), -9 + 40], "the comment right after the opener: the first nested block");
  assert.deepEqual([textOf(docW, readPlace(H(rawAt(docW, "<div align=\"center\">", 9).body), docW)), readPlace(H(rawAt(docW, "<div align=\"center\">", 9).body), docW)!.top], [PARA(1), -9 + 80], "the opener's row, through the comment: the first nested block");
  // a README's centred header: every row of the wrapper's block (the opener, the `<h1>`, the `<p>` tagline, an `<img>` line) and the
  // blank row before it read as the first nested block (before: the wrapper's block from each, its seat refused, 44 to 121px lost)
  const docR = "# Report\n\n" + paras(1, 2) + "\n\n<div align=\"center\">\n<h1>Project</h1>\n<p>A tagline for the project</p>\n\n" + paras(3, 4) + "\n\n</div>\n\n" + PARA(5) + "\n";
  const kDiv = lineOf(docR, "<div align=\"center\">"), k3r = lineOf(docR, PARA(3));
  for (const k of [kDiv - 1, kDiv, kDiv + 1, kDiv + 2]) {
    const qr = readPlace(H(rawRow(docR, k, 9).body), docR)!;
    assert.deepEqual([textOf(docR, qr), qr.top, qr.after], [PARA(3), -9 + (k3r - k) * 20, undefined], "README row " + k + ": the first nested block at its row's distance");
  }
  const docI = "# Report\n\n" + paras(1, 2) + "\n\n<div align=\"center\">\n<img src=\"logo.svg\" alt=\"logo\">\n\n## Centred title\n\n" + paras(3, 4) + "\n\n</div>\n\n" + PARA(5) + "\n";
  const qi = readPlace(H(rawAt(docI, "<img src=\"logo.svg\" alt=\"logo\">", 9).body), docI)!;
  assert.deepEqual([textOf(docI, qi), qi.top], ["## Centred title", -9 + 40], "the `<img>` line of the wrapper's block: the heading nested after it");
  // an html block that closes what it opens (`<p>Alpha</p>`) is its own place still
  const docP = "# Report\n\n" + PARA(1) + "\n\n<p>Alpha</p>\n\n" + PARA(2) + "\n";
  const qp = readPlace(H(rawAt(docP, "<p>Alpha</p>", 9).body), docP)!;
  assert.deepEqual([textOf(docP, qp), qp.top, !!qp.line], ["<p>Alpha</p>", -9, true], "a closed html block is its own place");
  // a fold right after a fold: a row inside the first carries the first block inside the second AND the block after both, in that
  // order, so the seat stands on the first shown (both shut: the block after both); a details tag inside a fence is text, not a fold
  const docCh = "# Report\n\n" + paras(1, 2) + "\n\n<details>\n<summary>A</summary>\n\n" + PARA(3) + "\n\n```\n</details>\n<details>\n```\n\n" + PARA(6) + "\n\n</details>\n\n<details>\n<summary>B</summary>\n\n" + PARA(4) + "\n\n</details>\n\n" + PARA(5) + "\n";
  const rch = rawAt(docCh, PARA(3), 4);
  const qch = readPlace(H(rch.body), docCh)!;
  const k3c = lineOf(docCh, PARA(3)), k6c = lineOf(docCh, PARA(6)), k4c = lineOf(docCh, PARA(4)), k5c = lineOf(docCh, PARA(5));
  assert.equal(textOf(docCh, qch), PARA(3));
  assert.deepEqual(qch.after, [{ ...spanOf(docCh, PARA(4)), top: -4 + (k4c - k3c) * 20 }, { ...spanOf(docCh, PARA(5)), top: -4 + (k5c - k3c) * 20 }], "paragraph 3 carries paragraph 4 (inside the second fold) then paragraph 5 (after both), each at its row's top; the fence's details tags counted for nothing");
  const q6 = readPlace(H(rawAt(docCh, PARA(6), 4).body), docCh)!;
  assert.deepEqual([textOf(docCh, q6), q6.after], [PARA(6), [{ ...spanOf(docCh, PARA(4)), top: -4 + (k4c - k6c) * 20 }, { ...spanOf(docCh, PARA(5)), top: -4 + (k5c - k6c) * 20 }]], "paragraph 6, after the fence and still inside the first fold, carries the same two");
  const q5 = readPlace(H(rawAt(docCh, PARA(5), 4).body), docCh)!;
  assert.deepEqual([textOf(docCh, q5), q5.after], [PARA(5), undefined], "paragraph 5, after both folds, carries nothing");
  // a run of closers: a div inside a div, both closed before the paragraph after them; the first closing row reads as that paragraph
  const docN = "# Report\n\n<div align=\"center\">\n<div>\n\n" + paras(1, 2) + "\n\n</div>\n\n</div>\n\n" + PARA(3) + "\n";
  const spansN = sourceBlockSpans(docN);
  assert.deepEqual(spansN.slice(-3).map((sp) => docN.slice(sp.start, sp.end)), ["</div>", "</div>", PARA(3)], "the fixture: two closing blocks then the paragraph");
  const rn = rawAt(docN, "</div>", 9);
  assert.equal(textOf(docN, readPlace(H(rn.body), docN)), PARA(3), "the first closer's row reads past both closers to the paragraph");
  assert.equal(readPlace(H(rn.body), docN)!.top, 9 + 20 + 20 + 20 + 20 - 9 - 9, "9px of the first closer, a blank, the second closer, a blank, then the paragraph's row");
  // the closing tag as the document's last block: nothing after it, so its own block is the place, partway in, with its line
  const docL = "# Report\n\n<div align=\"center\">\n\n" + paras(1, 2) + "\n\n</div>\n";
  const spansL = sourceBlockSpans(docL);
  assert.equal(docL.slice(spansL[spansL.length - 1].start, spansL[spansL.length - 1].end), "</div>", "the fixture: the closing tag is the last block");
  const rl = rawAt(docL, "</div>", 9);
  const ql = readPlace(H(rl.body), docL)!;
  assert.deepEqual([textOf(docL, ql), ql.top, !!ql.line], ["</div>", -9, true], "the last block's closing row is its own place, as before");
  // a closing tag inside a larger html block (`<p>Alpha</p>` on the line before `</div>` is one block): that block's own row
  const docB = "# Report\n\n<div align=\"center\">\n\n" + PARA(1) + "\n\n<p>Alpha</p>\n</div>\n\n" + PARA(2) + "\n";
  const spansB = sourceBlockSpans(docB);
  const bB = spansB.findIndex((sp) => docB.slice(sp.start, sp.end) === "<p>Alpha</p>\n</div>");
  assert.ok(bB >= 0, "the fixture: the closed tag and the closing tag are one html block");
  const rb = rawAt(docB, "</div>", 9);
  const qb = readPlace(H(rb.body), docB)!;
  assert.deepEqual([qb.start, qb.top, !!qb.line], [spansB[bB].start, -29, true], "the html block, its first row 29px above the edge, the closing row the line kept");
});

test("seatPlace: a Raw place inside a fold that carries the blocks after it (Place.after) stands on the first of them the Rendered view shows when the fold is shut, at that block's carried row top and no lower than the fold's summary at the edge (the review's round 3: the seat stands on what is shown; round 2 stood at the carried top alone, and a long fold's source put the summary off the pane; before round 2: no seat, the numeric scrollTop standing, off by the fold's source height); the fold open in the DOM, the source shut or not, seats the kept block itself at its own box, the carried blocks unused; a carried block that is not shown itself (a fold after a fold, both shut) is passed over for the next; and a block after a shut fold read through the fold's closing row keeps its row's distance under the same cap", () => {
  const doc = fold(false), spans = sourceBlockSpans(doc);
  const b5 = spans.findIndex((sp) => doc.slice(sp.start, sp.end) === PARA(5)), b6 = spans.findIndex((sp) => doc.slice(sp.start, sp.end) === PARA(6)), b7 = spans.findIndex((sp) => doc.slice(sp.start, sp.end) === PARA(7));
  const carried = (...ks: number[]): Place => ({ source: doc, view: "raw", start: spans[b6].start, end: spans[b6].end, top: -4, height: 20, atTop: false, prev: spans[b6 - 1], next: spans[b6 + 1], line: { start: spans[b6].start, end: spans[b6].end, top: -4 }, after: ks.map((k, i) => ({ ...spans[k], top: 76 + i * 60 })) });
  // the fold shut: paragraph 6 has its elements but none is shown, so the seat stands on paragraph 7, carried 76px below the edge (the
  // read of the third test), and no lower than the fold's summary at the edge: the shut details is 40px tall and paragraph 7 starts 48
  // below its top, so paragraph 7 goes 48px below the edge and the summary sits at it (round 2: 76, the summary 28px under the edge and
  // the tail of the block before the fold above it)
  const c = scene(false, 0); c.body.scrollTop = 500;
  assert.equal(c.p7.box!.top - c.summary.box!.top, 48, "the fixture: paragraph 7 starts 48px below the summary's top");
  assert.equal(seatPlace(H(c.body), doc, carried(b7)), true, "the shut fold: seated (before: refused)");
  assert.equal(c.body.scrollTop, 500 + (c.p7.box!.top - EDGE) - 48, "paragraph 7's box 48px below the edge, the summary at the edge (round 2: 76px, where the row was)");
  // a carried top under the cap keeps its distance: 30px, which leaves the summary 18px above the edge, partway (the round trip from a
  // wrapped summary partway in stays exact)
  const c2 = scene(false, 0); c2.body.scrollTop = 500;
  assert.equal(seatPlace(H(c2.body), doc, { ...carried(b7), after: [{ ...spans[b7], top: 30 }] }), true, "a carried top under the cap: seated");
  assert.equal(c2.body.scrollTop, 500 + (c2.p7.box!.top - EDGE) - 30, "paragraph 7's box 30px below the edge, where its row was: the summary 18px above the edge and the cap unmet");
  // the same cap for a Raw place read through the fold's closing row (readPlace's third test: paragraph 7 at its row's distance, 31px,
  // no block carried): under the cap, 31 stands; a closer followed by rows that render nothing (a comment) puts the row 67px down, and
  // the cap holds paragraph 7 at 48
  const viaCloser = (top: number): Place => ({ source: doc, view: "raw", start: spans[b7].start, end: spans[b7].end, top, height: 20, atTop: false, prev: spans[b7 - 1], next: spans[b7 + 1], line: null });
  const c3 = scene(false, 0); c3.body.scrollTop = 500;
  assert.equal(seatPlace(H(c3.body), doc, viaCloser(31)), true);
  assert.equal(c3.body.scrollTop, 500 + (c3.p7.box!.top - EDGE) - 31, "paragraph 7 31px below the edge, where its row was (the closing row 9px in)");
  const c4 = scene(false, 0); c4.body.scrollTop = 500;
  assert.equal(seatPlace(H(c4.body), doc, viaCloser(67)), true);
  assert.equal(c4.body.scrollTop, 500 + (c4.p7.box!.top - EDGE) - 48, "paragraph 7 48px below the edge, the summary at it (round 2: 67, the block before the fold's tail under the edge and the way back by its fraction, the fold's source between)");
  // the fold OPEN in the DOM: no shut fold before paragraph 7, and the distance stands (the recorded residual of an open fold's closing row)
  const c5 = scene(false, 0); c5.det.setAttribute("open", ""); c5.body.scrollTop = 500;
  assert.equal(seatPlace(H(c5.body), doc, viaCloser(67)), true);
  assert.equal(c5.body.scrollTop, 500 + (c5.p7.box!.top - EDGE) - 67, "the fold open: paragraph 7 67px below the edge, where its row was");
  // a place read in Rendered (a reflow) is not capped: the block keeps its distance whatever stands before it
  const c6 = scene(false, 0); c6.body.scrollTop = 500;
  assert.equal(seatPlace(H(c6.body), doc, { ...viaCloser(67), view: "rendered", height: H_BLOCK }), true);
  assert.equal(c6.body.scrollTop, 500 + (c6.p7.box!.top - EDGE) - 67, "a Rendered place: 67px, its own distance");
  // the fold OPEN in the DOM though the source says shut (the person opened it before the switch; file-view.ts restores it after the
  // paint, before the seat): paragraph 6 is shown and its own box is seated at the row's depth scaled, the carried block unused
  const o = scene(false, 0); o.det.setAttribute("open", ""); o.body.scrollTop = 500;
  assert.equal(o.hidden[1].checkVisibility(), true, "the fixture: the opened fold shows paragraph 6");
  assert.equal(seatPlace(H(o.body), doc, carried(b7)), true, "the opened fold: seated");
  assert.equal(o.body.scrollTop, 500 + (o.hidden[1].box!.top - EDGE) - (-4 * H_BLOCK / 20), "paragraph 6's own box at the row's depth scaled (the carried paragraph 7 unused)");
  // a carried block not shown itself (paragraph 5, inside the same shut fold, standing for the first block of a second shut fold) is
  // passed over for the next carried block, paragraph 7, whose carried top, 136px, the cap brings to 48
  const s2 = scene(false, 0); s2.body.scrollTop = 500;
  assert.equal(seatPlace(H(s2.body), doc, carried(b5, b7)), true, "two carried blocks, the first hidden: seated on the second");
  assert.equal(s2.body.scrollTop, 500 + (s2.p7.box!.top - EDGE) - 48, "paragraph 7's box under the cap, 48px below the edge (round 2: at ITS carried top, 136px)");
  // nothing carried, or every carried block hidden: the refusal of the second test stands
  const n = scene(false, 0); n.body.scrollTop = 500;
  assert.equal(seatPlace(H(n.body), doc, carried(b5)), false, "only a hidden block carried: no seat");
  assert.equal(n.body.scrollTop, 500, "the body stands");
});

// ── round 3: a wrapper's own picture (reader-place.ts Place.pic), over the same stand-in ──────────────────────
/** A README's centred header led by a picture: paragraphs 1 and 2, `<div align="center">` with `lead` on its own line (an `<img>`, or a
 *  linked logo `<a><img></a>`), a heading and paragraphs 3 and 4 nested in the div, `</div>`, paragraph 5. */
const readmeDoc = (lead: string) => "# Report\n\n" + paras(1, 2) + "\n\n<div align=\"center\">\n" + lead + "\n\n## Centred title\n\n" + paras(3, 4) + "\n\n</div>\n\n" + PARA(5) + "\n";
const IMG_LINE = '<img src="logo.svg" alt="logo">';
const IMG_H = 120;
type Readme = { body: FakeElement; md: FakeElement; div: FakeElement; img: FakeElement; h2: FakeElement };
/** `.fileview-body > div.fileview-md > marked output` for a README: the top-level blocks 40px tall, 8 apart, from `top0`; the div's
 *  children stacked inside it the same way, the picture (and the link around it) 120px tall, the div as tall as they are. */
function readmeScene(doc: string, top0 = 0): Readme {
  const d = new FakeDocument();
  const body = d.createElement("div"); body.setAttribute("class", "fileview-body"); body.box = { top: EDGE, bottom: EDGE + 600 };
  const md = d.createElement("div"); md.setAttribute("class", "fileview-md");
  for (const n of parseHTML(d, marked.parse(doc) as string)) md.appendChild(n);
  body.appendChild(md);
  const blocks = md.elements();
  const div = blocks[3];
  assert.equal(div.tagName, "DIV", "the fixture: the div is the fourth top-level element");
  const img = div.querySelector("img")!, h2 = div.elements().find((e) => e.tagName === "H2")!;   // the stand-in's selector grammar has no digits
  assert.ok(img && h2, "the fixture: the div holds the picture and the heading");
  let y = top0;
  for (const b of blocks) {
    if (b !== div) { b.box = { top: y, bottom: y + H_BLOCK }; y += H_BLOCK + GAP; continue; }
    const start = y;
    for (const k of div.elements()) {
      const pic = k === img || k.querySelector("img") !== null, h = pic ? IMG_H : H_BLOCK;
      k.box = { top: y, bottom: y + h };
      if (pic && k !== img) img.box = { top: y, bottom: y + h };
      y += h + GAP;
    }
    div.box = { top: start, bottom: y - GAP };
  }
  return { body, md, div, img, h2 };
}

test("readPlace / seatPlace: a picture of a wrapper's block's own (a README's logo on its own line inside `<div align=\"center\">`, or a linked logo) with the reader's edge inside it travels with the place as Place.pic: the Rendered read names the first nested block, as ruling 13 has it, and carries the picture's tag line with the picture's box; the Raw seat puts that line's row at the picture's fraction of its height, and the way back, from the row, puts the picture at the row's fraction (round 3; round 2 seated the heading where its row was, so a picture taller above the edge than the wrapper's rows put a block before the wrapper on top of Raw and the way back was that block's fraction seat, 36 to 442px off); a picture ending above the edge carries nothing; a picture the view does not show leaves the seat to the nested block at the row's distance", () => {
  for (const [what, lead] of [["an <img> on its own line", IMG_LINE], ["a linked logo", `<a href="https://example.test">${IMG_LINE}</a>`]] as const) {
    const doc = readmeDoc(lead), spans = sourceBlockSpans(doc);
    const bDiv = spans.findIndex((sp) => doc.slice(sp.start, sp.end).startsWith("<div align")), bH2 = spans.findIndex((sp) => doc.slice(sp.start, sp.end) === "## Centred title");
    const kImg = lineOf(doc, lead), kH2 = lineOf(doc, "## Centred title");
    const lineStart = doc.split("\n").slice(0, kImg).join("\n").length + 1;
    const picLine = { start: lineStart, end: lineStart + lead.length };
    assert.equal(doc.slice(picLine.start, picLine.end), lead, what + ": the fixture: the picture's tag line");
    // the fixture: the map pairs the picture (or the link around it) to the div's block as a row of its own, the div being the block's wrapper
    const c = readmeScene(doc);
    sameNodes(renderedBlockWrappers(El(c.md), doc, bDiv), [c.div], what + ": the fixture: the div is its block's wrapper");
    assert.equal(renderedBlockIndex(El(c.md), doc, El(c.div.elements()[0])), bDiv, what + ": the fixture: the picture's element is paired to the div's block");
    assert.equal(renderedBlockIndex(El(c.md), doc, El(c.h2)), bH2, what + ": the fixture: the heading is its own block");
    // Rendered, the edge 30px into the picture: the heading is the place (the picture passed over), 98px below the edge, and the picture
    // travels with it: its tag line, its top 30px above the edge, its height
    toEdge(c.md, c.img, 30); c.body.scrollTop = 400;   // scrolled: a body at its very top reads atTop, and its seat goes to the top
    const q = readPlace(H(c.body), doc)!;
    assert.deepEqual([textOf(doc, q), q.top, q.pic], ["## Centred title", IMG_H - 30 + GAP, { ...picLine, top: -30, height: IMG_H }], what + ": the heading at its distance, the picture's tag line and box carried");
    // the Raw seat: the picture's row at the same fraction of its height, 30/120 of a 20px row, 5px above the edge (round 2: the heading's
    // row 98px below the edge, the paragraph before the wrapper on top)
    const r = raw(doc, 0); r.body.scrollTop = 500;
    assert.equal(seatPlace(H(r.body), doc, q), true, what + ": seated in Raw");
    assert.equal(r.body.scrollTop, 500 + (r.rows[kImg].box!.top - EDGE) - (-30 * 20 / IMG_H), what + ": the picture's tag row 5px above the edge (round 2: the heading's row at 98)");
    // the Raw read from that row, 5px in: the heading's block at its row's distance, the row carried as pic
    const rr = rawRow(doc, kImg, 5); rr.body.scrollTop = 400;
    const qr = readPlace(H(rr.body), doc)!;
    assert.deepEqual([textOf(doc, qr), qr.top, qr.line, qr.pic], ["## Centred title", -5 + (kH2 - kImg) * 20, null, { ...picLine, top: -5, height: 20 }], what + ": the heading at its row's distance, the row carried as pic");
    // the Rendered seat from it: the picture at the row's fraction, 5/20 of 120px, 30px above the edge (round 2: the heading where its row
    // was, 35px below the edge, the picture 93px above it)
    const c2 = readmeScene(doc); c2.body.scrollTop = 500;
    assert.equal(seatPlace(H(c2.body), doc, qr), true, what + ": seated in Rendered");
    assert.equal(c2.body.scrollTop, 500 + (c2.img.box!.top - EDGE) - (-5 * IMG_H / 20), what + ": the picture 30px above the edge (round 2: the heading 35px below it)");
    // the picture ending above the edge (the edge 10px into the heading): nothing carried, the heading partway in
    const c3 = readmeScene(doc); toEdge(c3.md, c3.h2, 10);
    const q3 = readPlace(H(c3.body), doc)!;
    assert.deepEqual([textOf(doc, q3), q3.top, q3.pic], ["## Centred title", -10, undefined], what + ": the heading partway in, nothing carried");
    // the view does not show the picture (no layout, as a gated or dropped picture): the Raw place's seat falls to the heading at the row's distance
    const c4 = readmeScene(doc); c4.body.scrollTop = 500; c4.img.box = null;
    assert.equal(seatPlace(H(c4.body), doc, qr), true, what + ": seated without the picture");
    assert.equal(c4.body.scrollTop, 500 + (c4.h2.box!.top - EDGE) - qr.top, what + ": the heading at the row's distance (the rule below the picture's)");
  }
});
