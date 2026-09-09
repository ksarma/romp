// The reader's place, the module alone (reader-place.ts): the block table over marked's lexer, the top-visible search
// over a column of boxes, the pairing of a Rendered view's elements to the blocks, and the place read and seated over a
// DOM stand-in with boxes (marked's own output parsed into a minimal tree; no layout engine, so every box is given).
// The viewer's wiring runs for real in file-view-place.test.ts. Synthetic fixtures throughout. The marked singleton is
// armed with the chat's grammar (chatMdExtensions), as render.ts arms it in the chat page where the viewer runs, so a
// formula lexes to marked's placeholder here as it does there.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { marked } from "marked";
import { chatMdExtensions } from "./chat-md";
import { MATH_INLINE_CLASS, MATH_DISPLAY_CLASS } from "./math";
import { blockSpans, blockIndexAt, blockHolding, topVisibleIndex, renderedBlocks, rawRows, readPlace, seatPlace, type Place } from "./reader-place";

marked.use(...chatMdExtensions);

// ── a DOM stand-in: a tree with boxes, and the members reader-place reads ───────────────────────────
class FakeNode {
  readonly nodeType: number = 0;
  parentNode: FakeElement | null = null;
  childNodes: FakeNode[] = [];
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
}
class FakeText extends FakeNode {
  readonly nodeType = 3;
  constructor(public data: string) { super(); }
  get textContent(): string { return this.data; }
}
class FakeElement extends FakeNode {
  readonly nodeType = 1;
  attrs = new Map<string, string>();
  scrollTop = 0;
  /** the box a test gives the element (top, bottom); none by default, so getBoundingClientRect answers all zeros: no layout */
  box: { top: number; bottom: number } | null = null;
  constructor(public tagName: string) { super(); }
  get className(): string { return this.attrs.get("class") || ""; }
  classList = { contains: (c: string) => this.className.split(/\s+/).includes(c) };
  get children(): FakeElement[] { return this.childNodes.filter((c): c is FakeElement => c instanceof FakeElement); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeChild(n: FakeNode): FakeNode { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; return n; }
  appendChild(n: FakeNode): FakeNode { if (n.parentNode) n.parentNode.removeChild(n); this.childNodes.push(n); n.parentNode = this; return n; }
  /** `tag`, `.class`, `tag.class`, and comma groups of those: what the module asks for. */
  matches(sel: string): boolean {
    return sel.split(",").some((one) => {
      const m = /^([a-z]+)?((?:\.[\w-]+)*)$/.exec(one.trim());
      if (!m) throw new Error("stand-in: unsupported selector " + sel);
      if (m[1] && m[1].toUpperCase() !== this.tagName) return false;
      const classes = this.className.split(/\s+/);
      return (m[2].match(/\.[\w-]+/g) || []).every((c) => classes.includes(c.slice(1)));
    });
  }
  querySelectorAll(sel: string): FakeElement[] {
    const out: FakeElement[] = [];
    const walk = (n: FakeNode) => { for (const c of n.childNodes) if (c instanceof FakeElement) { if (c.matches(sel)) out.push(c); walk(c); } };
    walk(this); return out;
  }
  querySelector(sel: string): FakeElement | null { return this.querySelectorAll(sel)[0] || null; }
  getBoundingClientRect(): { top: number; bottom: number; left: number; right: number; width: number; height: number } {
    const b = this.box || { top: 0, bottom: 0 };
    return { top: b.top, bottom: b.bottom, left: 0, right: 0, width: 0, height: b.bottom - b.top };
  }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
const decode = (s: string) => s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
  if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
  return e in NAMED ? NAMED[e] : m;
});
/** marked's output as a tree: tags, text, entities; void elements do not nest; a comment is no node; an unclosed tag
 *  nests what follows, as a browser's parser does. */
function parseHTML(html: string): FakeNode[] {
  const root = new FakeElement("ROOT");
  let cur: FakeElement = root;
  const re = /<!--[\s\S]*?-->|<\/?([a-zA-Z][\w-]*)([^>]*)>|([^<]+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html))) {
    if (m[0].startsWith("<!--")) continue;
    if (m[3] !== undefined) { cur.appendChild(new FakeText(decode(m[3]))); continue; }
    const tag = m[1].toUpperCase();
    if (m[0][1] === "/") { if (cur !== root && cur.tagName === tag && cur.parentNode) cur = cur.parentNode; continue; }
    const el = new FakeElement(tag);
    const attrRe = /([\w-]+)(?:="([^"]*)")?/g; let a: RegExpExecArray | null;
    while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], a[2] === undefined ? "" : decode(a[2]));
    cur.appendChild(el);
    if (!VOID.has(tag.toLowerCase()) && !m[2].endsWith("/")) cur = el;
  }
  return root.childNodes.slice();
}
const H = (n: FakeNode) => n as unknown as HTMLElement;
const el = (tag: string, cls?: string): FakeElement => { const e = new FakeElement(tag); if (cls) e.setAttribute("class", cls); return e; };

/** `.fileview-body > div.fileview-md > marked's output`, the body's box 100..700 (its top edge at 100), block i boxed
 *  from top0 down: one height for all (each box 8px short of the next) or a height per block (boxes touching). */
function rendered(src: string, top0 = 0, h: number | number[] = 40): { body: FakeElement; md: FakeElement; blocks: FakeElement[] } {
  const body = el("DIV", "fileview-body"); body.box = { top: 100, bottom: 700 };
  const md = el("DIV", "fileview-md");
  for (const n of parseHTML(marked.parse(src) as string)) md.appendChild(n);
  body.appendChild(md);
  const blocks = md.children;
  let top = top0;
  blocks.forEach((b, i) => { const hi = Array.isArray(h) ? h[i] : h; b.box = { top, bottom: Array.isArray(h) ? top + hi : top + hi - 8 }; top += hi; });
  return { body, md, blocks };
}
/** `.fileview-body > div.fileview-code > pre > code.hljs > span.fv-cl*`, one row per line as codeBlock cuts them (a
 *  trailing line feed makes no row), rows h px tall from top0, touching. */
function raw(src: string, top0 = 0, h = 20): { body: FakeElement; code: FakeElement; rows: FakeElement[] } {
  const body = el("DIV", "fileview-body"); body.box = { top: 100, bottom: 700 };
  const wrap = el("DIV", "fileview-code"); const pre = el("PRE", "fileview-pre fileview-wrap"); const code = el("CODE", "hljs");
  const lines = src.split("\n"); if (lines.length && lines[lines.length - 1] === "") lines.pop();
  const rows = lines.map((ln, i) => {
    const row = el("SPAN", "fv-cl"); const t = el("SPAN", "fv-ct");
    if (ln) t.appendChild(new FakeText(ln));
    row.appendChild(t); row.box = { top: top0 + i * h, bottom: top0 + (i + 1) * h }; code.appendChild(row); return row;
  });
  pre.appendChild(code); wrap.appendChild(pre); body.appendChild(wrap);
  return { body, code, rows };
}

// ── fixtures ───────────────────────────────────────────────────────────────────────────────────────
const PARA = (i: number) => `Paragraph ${i}: some words of the report, enough to make a line.`;
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
const CODE = "```python\ndef f(x):\n    return x\n\nprint(f(1))\n```";
const TABLE = "| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |";
const HTML2 = "<p>Html A: a raw paragraph.</p>\n<p>Html B: another on the next line, one block with the first.</p>";
const DEF = '[report]: https://example.test/notes-api/report "The report"';
const LAST = "Paragraph 8: see [the report][report] for the rest.";
/** heading; 1..3; a fenced block with a blank line inside; 4..5; a table; 6; an html block of two sibling tags; a
 *  comment; a reference definition (no block); 7; 8, which uses the reference. Thirteen blocks. */
const DOC = "# Report\n\n" + paras(1, 3) + "\n\n" + CODE + "\n\n" + paras(4, 5) + "\n\n" + TABLE + "\n\n" + PARA(6) + "\n\n" + HTML2
  + "\n\n<!-- a note to self -->\n\n" + DEF + "\n\n" + PARA(7) + "\n\n" + LAST + "\n";
const TWIN = "Before.\n\n<p>A</p>\n\n<p>B</p>\n\nAfter.\n";   // two html blocks with no text between them
const at = (s: string, text: string) => { const i = s.indexOf(text); assert.ok(i >= 0, "fixture holds " + text); return i; };
const lineOf = (s: string, off: number) => s.slice(0, off).split("\n").length - 1;

// ── the block table ────────────────────────────────────────────────────────────────────────────────
test("blockSpans: marked's top-level blocks in order, each to the end of its text; a blank line inside a fenced block is the block's, one between paragraphs is no block's; two sibling tags with no blank line between are one html block; a comment is a block; a reference definition is no block; offsets are the file's own through CRLF, a lone CR and leading tabs", () => {
  const spans = blockSpans(DOC);
  assert.deepEqual(spans.map((s) => DOC.slice(s.start, s.end)),
    ["# Report", PARA(1), PARA(2), PARA(3), CODE, PARA(4), PARA(5), TABLE, PARA(6), HTML2, "<!-- a note to self -->", PARA(7), LAST]);
  assert.equal(blockIndexAt(spans, at(DOC, "return x")), 4);
  assert.equal(blockHolding(spans, at(DOC, "return x")), 4, "inside the code block");
  assert.equal(blockHolding(spans, at(DOC, "\n\nprint(f(1))") + 1), 4, "the blank line inside the code block is the code block's");
  assert.equal(blockHolding(spans, at(DOC, PARA(2)) - 1), 2, "the blank line between paragraphs 1 and 2: paragraph 2, the block after it");
  assert.equal(blockHolding(spans, at(DOC, DEF)), 11, "the reference definition: the block after it");
  assert.equal(blockHolding(spans, spans[12].end + 1), -1, "past the last block's text");
  assert.equal(blockHolding(spans, -1), 0, "before the first block: the first");
  assert.equal(blockIndexAt(spans, -1), -1);
  assert.equal(blockHolding([], 3), -1);
  // line endings: a span ends before its CR; a lone CR is a line ending to the lexer and the paragraph runs over it
  assert.deepEqual(blockSpans("line one\r\n\r\nline two\r\n"), [{ start: 0, end: 8 }, { start: 12, end: 20 }]);
  assert.deepEqual(blockSpans("a\rb\n"), [{ start: 0, end: 3 }]);
  // leading tabs: the lexer expands each to four spaces before it cuts, and the spans come back to the tab
  const indented = "\tcode line\n\nAfter.\n";
  assert.deepEqual(blockSpans(indented).map((s) => indented.slice(s.start, s.end)), ["\tcode line", "After."]);
  const fenced = "```\n\tone\n\t\ttwo\n```\n\na\tb\n";
  assert.deepEqual(blockSpans(fenced).map((s) => fenced.slice(s.start, s.end)), ["```\n\tone\n\t\ttwo\n```", "a\tb"], "tabs inside a fence, and a tab mid-line that the lexer leaves alone");
  const spaced = "  \tx\n\ny\n";
  assert.deepEqual(blockSpans(spaced).map((s) => spaced.slice(s.start, s.end)), ["  \tx", "y"], "a tab after leading spaces is expanded too");
  assert.deepEqual(blockSpans(""), []);
  // a lone space on the last line: the lexer moves it onto the block before it as a line feed, and the span still ends at
  // the block's text, whatever kind of block is last
  for (const last of ["## End", TABLE, "<p>End.</p>", "---", "- item"]) {
    const tailed = "# Title\n\nPara one.\n\n" + last + "\n ";
    assert.deepEqual(blockSpans(tailed).map((s) => tailed.slice(s.start, s.end)), ["# Title", "Para one.", last], "a lone space after " + JSON.stringify(last));
  }
  assert.deepEqual(blockSpans("Para.\n ").map((s) => "Para.\n ".slice(s.start, s.end)), ["Para."], "after a paragraph, which takes the line: the span ends at the text");
  assert.deepEqual(blockSpans("# Title\n\n  \n"), [{ start: 0, end: 7 }], "two spaces are a space token of their own, dropped");
  assert.deepEqual(blockSpans(DOC), spans, "the same text again: the same table");
});

// ── topVisibleIndex ────────────────────────────────────────────────────────────────────────────────
test("topVisibleIndex: the first box whose bottom lies below the edge, count when none; a box with no layout (NaN) on the search's path is read around, and the answer skips it; a floated figure reaching below the paragraphs beside it is passed over for the first of those ending below the edge", () => {
  const bottoms = [40, 80, 120, 160, 200];
  const plain = (i: number) => bottoms[i];
  assert.equal(topVisibleIndex(5, plain, -1), 0, "everything below the edge: the first");
  assert.equal(topVisibleIndex(5, plain, 40), 1, "a bottom ON the edge is not below it");
  assert.equal(topVisibleIndex(5, plain, 39.5), 0);
  assert.equal(topVisibleIndex(5, plain, 130), 3);
  assert.equal(topVisibleIndex(5, plain, 200), 5, "none below: count");
  assert.equal(topVisibleIndex(0, plain, 0), 0, "no boxes");
  // 102 boxes of 60px, the reader's edge inside box 20; the search's first probe is (0 + 102) >> 1 = 51
  const stack = (hidden: number[]) => (i: number) => (hidden.includes(i) ? NaN : (i + 1) * 60);
  const edge = 20 * 60 + 30;
  assert.equal(topVisibleIndex(102, stack([]), edge), 20);
  assert.equal(topVisibleIndex(102, stack([51]), edge), 20, "hidden at the first probe");
  assert.equal(topVisibleIndex(102, stack([50, 51, 52, 53]), edge), 20, "a run of hidden boxes at the probe");
  assert.equal(topVisibleIndex(102, stack([25]), edge), 20, "hidden between the reader and the probe");
  assert.equal(topVisibleIndex(102, stack([20]), edge), 21, "the reader's own box hidden: the next with a layout");
  for (let hid = 0; hid < 102; hid++) for (const top of [0, 1, 19, 20, 21, 60, 100, 101]) {
    const want = hid === top ? top + 1 : top;
    assert.equal(topVisibleIndex(102, stack([hid]), top * 60 + 30), want > 101 ? 102 : want, `hidden ${hid}, reader in ${top}`);
  }
  assert.equal(topVisibleIndex(3, () => NaN, 10), 3, "every box hidden: count");
  // a figure (index 4) reaching to 400 beside three paragraphs ending at 200, 240, 280: the paragraph the reader is
  // beside, not the figure the search lands on
  const floated = [40, 80, 120, 160, 400, 200, 240, 280];
  assert.equal(topVisibleIndex(8, (i) => floated[i], 250), 7);
  assert.equal(topVisibleIndex(8, (i) => floated[i], 210), 6);
  assert.equal(topVisibleIndex(8, (i) => floated[i], 170), 4, "the first paragraph beside it still ends below the edge: the figure, first in the order");
  assert.equal(topVisibleIndex(8, (i) => floated[i], 100), 2, "the edge above the figure");
  assert.equal(topVisibleIndex(8, (i) => floated[i], 300), 4, "past the last paragraph beside it: the figure, the only box still ending below the edge");
  const farFig = [40, 900, ...Array.from({ length: 12 }, (_, i) => 60 + i * 20)];
  assert.equal(topVisibleIndex(farFig.length, (i) => farFig[i], 500), farFig.length, "a figure more than the tail's boxes before the end: count");
  // a long column costs a handful of box reads, not one per box: 4096 boxes of 30px, every 97th hidden, the reader in
  // box `top`, under 2 * log2(4096) + the tail's 8 reads
  let reads = 0;
  const counted = (i: number) => { reads++; return i % 97 === 0 ? NaN : (i + 1) * 30; };
  for (const top of [0, 1, 97, 1000, 2048, 4000, 4095]) {
    reads = 0;
    assert.equal(topVisibleIndex(4096, counted, top * 30 + 15), top % 97 === 0 ? top + 1 : top);
    assert.ok(reads <= 2 * 12 + 8, reads + " box reads for a reader in box " + top + " of 4096: a binary search, not a walk");
  }
});

// ── the Rendered pairing ───────────────────────────────────────────────────────────────────────────
test("renderedBlocks: one element per block in order, the html block's two sibling tags together, none for the comment; a fenced block's rows and Copy button are not its text; declined (null) for a text the sanitizer changed, a wrapper that swallowed the following markdown, two html blocks with no text between them, an element no block accounts for, and a root with no elements", () => {
  const { md, blocks } = rendered(DOC);
  assert.deepEqual(blocks.map((b) => b.tagName), ["H1", "P", "P", "P", "PRE", "P", "P", "TABLE", "P", "P", "P", "P", "P"]);
  const paired = renderedBlocks(H(md), DOC);
  assert.ok(paired);
  assert.deepEqual(paired!.map((els) => els.length), [1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 0, 1, 1]);
  assert.equal(paired![9][0], H(blocks[9])); assert.equal(paired![9][1], H(blocks[10]), "the html block's two tags");
  assert.equal(paired![4][0], H(blocks[4])); assert.equal(paired![12][0], H(blocks[12]));
  assert.equal(renderedBlocks(H(md), DOC), paired, "kept for the root");
  // the viewer's fence dress (code-block.ts): rows without their newlines and a Copy button leave the pairing standing
  const dressed = rendered(DOC);
  const pre = dressed.blocks[4]; const code = pre.children[0];
  code.childNodes = [];
  for (const ln of "def f(x):\n    return x\n\nprint(f(1))".split("\n")) { const row = el("SPAN", "cl"); row.appendChild(new FakeText(ln)); code.appendChild(row); }
  const btn = el("BUTTON", "code-copy"); btn.appendChild(new FakeText("Copy")); pre.appendChild(btn);
  assert.equal(renderedBlocks(H(dressed.md), DOC)!.length, 13);
  // the sanitizer removed a paragraph's script and its text: the text differs
  const scripted = DOC.replace(PARA(3), "Paragraph 3 <script>alert(1)</script> and words.");
  const s = rendered(scripted);
  const script = s.md.querySelector("script")!;
  assert.ok(script && script.parentNode === s.blocks[3], "the fixture: the script rendered inside paragraph 3");
  script.parentNode!.removeChild(script);
  assert.equal(renderedBlocks(H(s.md), scripted), null);
  // an html wrapper the browser nests the following markdown into: the run never fits again
  const wrapped = "# Report\n\n<div class=\"wrap\">\n\n" + paras(1, 4) + "\n";
  const w = rendered(wrapped);
  assert.equal(w.blocks.length, 2, "the fixture: the paragraphs nest inside the unclosed div, as a browser's parser puts them");
  assert.equal(renderedBlocks(H(w.md), wrapped), null);
  // two html blocks with only a blank line between: their elements cannot be told apart
  assert.equal(renderedBlocks(H(rendered(TWIN).md), TWIN), null);
  // an html block last takes the run to the end; one followed by a rule, then text: the rule fits by order
  const tail = "Before.\n\n<p>A</p>\n<p>B</p>\n";
  assert.deepEqual(renderedBlocks(H(rendered(tail).md), tail)!.map((e) => e.length), [1, 2]);
  const ruled = "<p>A</p>\n<p>B</p>\n\n---\n\nAfter.\n";
  assert.deepEqual(renderedBlocks(H(rendered(ruled).md), ruled)!.map((e) => e.length), [2, 1, 1]);
  const commented = "Before.\n\n<!-- a -->\n\nAfter.\n";
  assert.deepEqual(renderedBlocks(H(rendered(commented).md), commented)!.map((e) => e.length), [1, 0, 1]);
  // an element the table does not account for; a root with none
  const extra = rendered(DOC); extra.md.appendChild(parseHTML("<p>Stray.</p>")[0]);
  assert.equal(renderedBlocks(H(extra.md), DOC), null);
  assert.equal(renderedBlocks(H(el("DIV", "fileview-md")), DOC), null);
});

// ── a formula ──────────────────────────────────────────────────────────────────────────────────────
test("renderedBlocks: a formula is no part of the text on either side, so a note with math pairs in the chat page, where the sanitizer's post-pass renders KaTeX where marked's placeholder stood (an inline one, and a display formula as a block of its own); a formula KaTeX could not lay out, shown as its source, declines", () => {
  const MATH = "# Energy\n\nMass is energy: $E = mc^2$, as ever.\n\n$$\\alpha + \\beta$$\n\nAfter.\n";
  const spans = blockSpans(MATH);
  assert.deepEqual(spans.map((s) => MATH.slice(s.start, s.end)), ["# Energy", "Mass is energy: $E = mc^2$, as ever.", "$$\\alpha + \\beta$$", "After."]);
  const holders = (md: FakeElement) => md.querySelectorAll("." + MATH_INLINE_CLASS + ", ." + MATH_DISPLAY_CLASS);
  // the post-pass (math.ts renderMathPlaceholders): KaTeX's root where each placeholder stood, its text the layout's
  const katex = (display: boolean, text: string) => { const root = el("SPAN", display ? "katex-display" : "katex"); const inner = el("SPAN", display ? "katex" : "katex-html"); inner.appendChild(new FakeText(text)); root.appendChild(inner); return root; };
  const swap = (holder: FakeElement, root: FakeElement) => { const p = holder.parentNode!; p.childNodes.splice(p.childNodes.indexOf(holder), 1, root); root.parentNode = p; holder.parentNode = null; root.box = holder.box; };
  const r = rendered(MATH);
  const h = holders(r.md);
  assert.equal(h.length, 2, "the fixture: marked emitted the two placeholders");
  assert.equal(h[1].tagName, "DIV"); assert.equal(h[1].parentNode, r.md, "the display formula is a paragraph of its own, a top-level block");
  swap(h[0], katex(false, "E=mc2"));
  swap(h[1], katex(true, "\u03b1+\u03b2"));
  assert.deepEqual(r.md.children.map((b) => b.className), ["", "", "katex-display", ""]);
  const paired = renderedBlocks(H(r.md), MATH);
  assert.ok(paired, "paired: the formulas left out on both sides, the rest of each block's text confirms it");
  assert.deepEqual(paired!.map((e) => e.length), [1, 1, 1, 1]);
  assert.equal(paired![2][0], H(r.md.children[2]));
  const p = readPlace(H(r.body), MATH);   // block i at 40i..40i+32, the edge at 100: block 2, the formula, is the first ending below it
  assert.ok(p); assert.equal(MATH.slice(p!.start, p!.end), "$$\\alpha + \\beta$$", "the reader is on the formula");
  // the belt under the fill (math.ts showSource): KaTeX threw, and the TeX stands as source in a code element; that text
  // is not the file's, and the block declines
  const belt = rendered(MATH);
  const hb = holders(belt.md);
  const code = el("CODE"); code.appendChild(new FakeText("E = mc^2")); swap(hb[0], code);
  swap(hb[1], katex(true, "\u03b1+\u03b2"));
  assert.equal(renderedBlocks(H(belt.md), MATH), null);
  // the placeholder still standing (no post-pass ran): left out on the element's side too, and the block pairs
  assert.deepEqual(renderedBlocks(H(rendered(MATH).md), MATH)!.map((e) => e.length), [1, 1, 1, 1]);
});

// ── readPlace ──────────────────────────────────────────────────────────────────────────────────────
test("readPlace: Rendered reads the top-visible element's block with the block's box (an html block's two tags together) and whether the body is at its top; a hidden element on the search's path is skipped; every block above the edge, no layout, a declined pairing, or neither view reads as no place", () => {
  const r = rendered(DOC, 0, 40);   // block i at 40i..40i+32; the edge at 100: block 2 (80..112) is the first ending below it
  const p = readPlace(H(r.body), DOC);
  assert.ok(p);
  assert.equal(DOC.slice(p!.start, p!.end), PARA(2));
  assert.equal(p!.top, -20); assert.equal(p!.height, 32); assert.equal(p!.view, "rendered"); assert.equal(p!.atTop, true); assert.equal(p!.source, DOC);
  r.body.scrollTop = 7;
  assert.equal(readPlace(H(r.body), DOC)!.atTop, false);
  // the html block: its second tag is the first element ending below the edge, and the box starts at the first
  const spans = blockSpans(DOC);
  const r2 = rendered(DOC, 0, 40);
  for (let i = 0; i < 9; i++) r2.blocks[i].box = { top: -1000 + i * 40, bottom: -1000 + i * 40 + 32 };
  r2.blocks[9].box = { top: 60, bottom: 90 }; r2.blocks[10].box = { top: 98, bottom: 130 };
  const q = readPlace(H(r2.body), DOC)!;
  assert.deepEqual([q.start, q.end], [spans[9].start, spans[9].end], "the html block, not its second tag");
  assert.equal(q.top, -40); assert.equal(q.height, 70);
  // hidden at the search's first probe ((0 + 13) >> 1 = 6), below the reader at block 2
  const r3 = rendered(DOC, 0, 40); r3.blocks[6].box = null;
  const p3 = readPlace(H(r3.body), DOC)!;
  assert.equal(DOC.slice(p3.start, p3.end), PARA(2));
  const flat = rendered(DOC); for (const b of flat.blocks) b.box = null;
  assert.equal(readPlace(H(flat.body), DOC), null, "no layout at all");
  assert.equal(readPlace(H(rendered(DOC, -2000, 40).body), DOC), null, "every block above the edge");
  assert.equal(readPlace(H(rendered(TWIN, 0, 40).body), TWIN), null, "a declined pairing");
  const loader = el("DIV", "fileview-body"); loader.box = { top: 100, bottom: 700 }; loader.appendChild(el("DIV", "fileview-load"));
  assert.equal(readPlace(H(loader), DOC), null, "neither view up");
});

test("readPlace: Raw reads the block holding the top row with the block's rows as its box; a blank row between two blocks reads as the block after it; a row inside the fenced block, its inner blank line too, reads as the code block from its fence; rows that are not the text's, or a row past the last block, read as no place", () => {
  const lines = DOC.split("\n");
  const spans = blockSpans(DOC);
  const w = raw(DOC, 0, 20);   // rows 20px from 0, the edge at 100: row 5 is the first ending below it
  assert.equal(rawRows(H(w.code)).length, lines.length - 1, "one row per line, none for the trailing line feed");
  assert.equal(lines[5], "", "row 5 is the blank line between paragraphs 2 and 3");
  const q = readPlace(H(w.body), DOC)!;
  assert.equal(DOC.slice(q.start, q.end), PARA(3), "the block after the blank row");
  assert.equal(q.top, 20, "paragraph 3's row, 20px below the edge"); assert.equal(q.height, 20); assert.equal(q.view, "raw"); assert.equal(q.atTop, true);
  const codeLine = lineOf(DOC, at(DOC, "```python"));
  const w2 = raw(DOC, -(codeLine + 2) * 20 + 90, 20);   // the `return x` row straddles the edge
  const q2 = readPlace(H(w2.body), DOC)!;
  assert.deepEqual([q2.start, q2.end], [spans[4].start, spans[4].end], "the code block");
  assert.equal(q2.top, -50, "the fence row's top, two rows and 10px above the edge"); assert.equal(q2.height, 120, "fence to fence, the inner blank line included");
  const w3 = raw(DOC, -(codeLine + 3) * 20 + 90, 20);   // the blank line inside the code block at the edge
  const q3 = readPlace(H(w3.body), DOC)!;
  assert.deepEqual([q3.start, q3.top], [spans[4].start, -70]);
  assert.equal(readPlace(H(w.body), DOC + "one more line\n"), null, "rows that are not this text's");
  const tailed = DOC + "\n\n\n";
  const w4 = raw(tailed, -(lines.length + 1) * 20 + 90, 20);   // the last of the trailing blank rows at the edge
  assert.equal(readPlace(H(w4.body), tailed), null, "past the last block's text: no block to keep");
});

// ── seatPlace ──────────────────────────────────────────────────────────────────────────────────────
test("seatPlace: partway into a block, the other view's block is seated at the same fraction of its height, and back; a block below the edge keeps its distance; the same view reflowed taller keeps the fraction; a body at its top goes to its top; another text, no text view, a block not in the table or a declined pairing seats nothing and moves nothing; a Raw place on a comment seats the block after it", () => {
  const spans = blockSpans(DOC);
  const codeLine = lineOf(DOC, at(DOC, "```python"));
  // Rendered: the code block (4) 600px tall, the reader 300px into it
  const kept: Place = { source: DOC, view: "rendered", start: spans[4].start, end: spans[4].end, top: -300, height: 600, atTop: false };
  const w = raw(DOC, 0, 20); w.body.scrollTop = 1000;
  assert.equal(seatPlace(H(w.body), DOC, kept), true);
  assert.equal(w.body.scrollTop, 1000 + (codeLine * 20 - 100) - (-60), "the fence row seated 60px above the edge: half of six rows, as 300 of 600 was");
  // and back: a Raw place 60px into the block's 120px seats the 600px block 300px in
  const rawKept: Place = { source: DOC, view: "raw", start: spans[4].start, end: spans[4].end, top: -60, height: 120, atTop: false };
  const r = rendered(DOC, 0, [40, 40, 40, 40, 600, 40, 40, 40, 40, 40, 40, 40, 40]); r.body.scrollTop = 50;
  assert.equal(seatPlace(H(r.body), DOC, rawKept), true);
  assert.equal(r.body.scrollTop, 50 + (r.blocks[4].box!.top - 100) - (-300));
  // below the edge: the distance in pixels, whatever the block's height now
  const r1 = rendered(DOC, 0, 80);
  assert.equal(seatPlace(H(r1.body), DOC, { ...kept, start: spans[2].start, end: spans[2].end, top: 18, height: 40 }), true);
  assert.equal(r1.body.scrollTop, (r1.blocks[2].box!.top - 100) - 18);
  // the same view, the block twice as tall (a size step): twice as deep
  const r2 = rendered(DOC, 0, new Array(13).fill(80));
  assert.equal(seatPlace(H(r2.body), DOC, { ...kept, start: spans[2].start, end: spans[2].end, top: -20, height: 40 }), true);
  assert.equal(r2.body.scrollTop, (r2.blocks[2].box!.top - 100) - (-40));
  // at the top of the body: the top of the body, whatever the block's height in the new view
  const w2 = raw(DOC, 0, 20); w2.body.scrollTop = 33;
  assert.equal(seatPlace(H(w2.body), DOC, { ...kept, atTop: true }), true);
  assert.equal(w2.body.scrollTop, 0);
  // nothing to seat in, nothing moved
  const other = DOC.replace("Paragraph 3", "Paragraph X");
  const w3 = raw(other, 0, 20); w3.body.scrollTop = 500;
  assert.equal(seatPlace(H(w3.body), other, kept), false, "another text");
  assert.equal(w3.body.scrollTop, 500);
  const loader = el("DIV", "fileview-body"); loader.box = { top: 100, bottom: 700 }; loader.appendChild(el("DIV", "fileview-load")); loader.scrollTop = 5;
  assert.equal(seatPlace(H(loader), DOC, kept), false, "no text view"); assert.equal(loader.scrollTop, 5);
  const w4 = raw(DOC, 0, 20); w4.body.scrollTop = 500;
  assert.equal(seatPlace(H(w4.body), DOC, { ...kept, start: spans[4].start + 3 }), false, "not a block's start"); assert.equal(w4.body.scrollTop, 500);
  const tw = rendered(TWIN, 0, 40); tw.body.scrollTop = 500;
  assert.equal(seatPlace(H(tw.body), TWIN, { source: TWIN, view: "raw", start: 0, end: 7, top: -10, height: 20, atTop: false }), false, "a declined pairing");
  assert.equal(tw.body.scrollTop, 500);
  // a Raw place on the comment (block 10), which renders nothing: the block after it, where the reader's eye was
  const r3 = rendered(DOC, 0, 40);
  assert.equal(seatPlace(H(r3.body), DOC, { source: DOC, view: "raw", start: spans[10].start, end: spans[10].end, top: -4, height: 20, atTop: false }), true);
  assert.equal(r3.body.scrollTop, (r3.blocks[11].box!.top - 100) - (-4 * 32 / 20));
});
