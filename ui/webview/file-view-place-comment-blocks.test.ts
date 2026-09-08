// The block table's rule for an html block of comments (anchor-map.ts commentsOnly, behind the `blank` flag the Slice 2
// review added: such a block renders no node, so the pairing gives it none and reads past it). The Slice 2 review's
// second round found the rule's first form, an anchored regex over the whole raw, wrong in two ways, both pinned here:
// it tried every way of splitting a line of adjacent comments among its repeats when the raw ended in anything but a
// comment and doubled its time per comment (91 ms at 22 comments, 144 s at 30, on every Rendered paint of the
// file); and it let a comment at each end of the line vouch for whatever stood between them, so a line like
// `<!-- a --> words <!-- b -->` read as blank though it renders the words, the pairing skipped it, the next paragraph
// took the rendered words as its own node and was refused, and every block after it paired one node early (the Raw
// switch landed one paragraph on; a comment from the Rendered view on any paragraph after the line was refused).
// The rule is now a scan from left to right, one comment at a time, linear in the raw's length. The stand-in is the
// anchor-map suite's minimal tree (marked's output parsed into nodes, no jsdom); it drops a comment as a real DOM's
// Comment node is never a paired node. Synthetic fixtures only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { marked } from "marked";
import { sourceBlockSpans, renderedBlockIndex, renderedBlockElements, mapRenderedSelection, type SelLike } from "./anchor-map";

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
  constructor(doc: FakeDocument, public tagName: string) { super(doc); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  appendChild(n: FakeNode): FakeNode { this.childNodes.push(n); n.parentNode = this; return n; }
  get children(): FakeElement[] { return this.childNodes.filter((c): c is FakeElement => c instanceof FakeElement); }
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
const Nd = (n: FakeNode) => n as unknown as Node;

/** `div.fileview-md > marked output`, the viewer's Rendered root. */
function rendered(src: string): FakeElement {
  const doc = new FakeDocument();
  const md = doc.createElement("div"); md.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(src) as string)) md.appendChild(n);
  return md;
}
/** The top-level element whose text starts with `text`. */
const elementStarting = (md: FakeElement, text: string): FakeElement => {
  const el = md.children.find((c) => c.textContent.startsWith(text));
  assert.ok(el, "the rendered root holds an element starting " + JSON.stringify(text));
  return el;
};
/** The top-level text node with words in it (whitespace between blocks is no node's). */
const wordsNode = (md: FakeElement): FakeText | undefined =>
  md.childNodes.find((c): c is FakeText => c instanceof FakeText && c.data.trim() !== "");
const tags = (els: Element[]) => els.map((e) => (e as unknown as FakeElement).tagName);
/** A selection over the first `n` characters of `el`'s first text node. */
const selectStart = (el: FakeElement, n: number): SelLike => {
  const t = el.childNodes[0];
  assert.ok(t instanceof FakeText, "the element starts with text");
  return { anchorNode: t as unknown as Node, anchorOffset: 0, focusNode: t as unknown as Node, focusOffset: n, isCollapsed: false };
};

const PARA = (i: number) => `Paragraph ${i}: some words of the report, enough to make a line.`;
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
const comments = (k: number, gap = " ") => Array.from({ length: k }, (_, i) => `<!-- c${i} -->`).join(gap);
/** heading (block 0), paragraphs 1..3 (blocks 1..3), `line` (block 4), paragraphs 4..6 (blocks 5..7) */
const around = (line: string) => "# Report\n\n" + paras(1, 3) + "\n\n" + line + "\n\n" + paras(4, 6) + "\n";
/** A pairing that holds for blocks 5..7 after any one-line html block 4: each paragraph its own block, in both directions. */
function pairedAfter(md: FakeElement, src: string): void {
  assert.equal(sourceBlockSpans(src).length, 8, "heading, three paragraphs, the html line, three paragraphs");
  for (const i of [4, 5, 6]) {
    const p = elementStarting(md, `Paragraph ${i}:`);
    assert.equal(renderedBlockIndex(El(md), src, Nd(p)), i + 1, `Paragraph ${i} stands for block ${i + 1}`);
    assert.deepEqual(renderedBlockElements(El(md), src, i + 1), [El(p)], `block ${i + 1} renders as Paragraph ${i}`);
  }
  assert.equal(renderedBlockIndex(El(md), src, Nd(elementStarting(md, "Paragraph 3:"))), 3);
  assert.equal(mapRenderedSelection(selectStart(elementStarting(md, "Paragraph 4:"), 9), El(md), src).ok, true,
               "a comment from the Rendered view on the paragraph after the line maps");
}

// marked lexes a line of comments and whatever follows them on that line as ONE html token (its block html rule
// takes the rest of the line after the first comment), so the whole line is the raw the rule reads. The regex this
// replaced took 91 ms at 22 comments with a tag after them and doubled per comment; the scan reads the raw once.
// The cost is read as the process's CPU time, not the wall clock: node runs test files in parallel, and a process the
// scheduler holds off between two wall-clock reads accrues no CPU time (the Slice 2 review's fourth round measured a
// 3 ms scan at 1.6 s of wall clock on a starved core), while the regressed form's backtracking was all CPU. The bound
// is loose (the scan takes well under a millisecond here); a doubling per comment stands no chance of it.
test("an html block of many adjacent comments is read in its length: 30 comments and a tag pair at once, 30 alone are a blank block", () => {
  const BOUND_MS = 250;
  /** The CPU milliseconds (user and system, every thread of the process) building the rendered index over `src` costs. */
  const timed = (src: string): { md: FakeElement; ms: number } => {
    const md = rendered(src);
    const c0 = process.cpuUsage();
    renderedBlockIndex(El(md), src, Nd(md.childNodes[0]));   // builds the rendered index, which reads every html block's raw
    const c = process.cpuUsage(c0);
    return { md, ms: (c.user + c.system) / 1000 };
  };
  // comments then a tag: not blank; the tag is the block's node and the paragraphs after it pair to their own blocks
  const withTag = around(comments(30) + " <b>badge</b>");
  let r = timed(withTag);
  assert.ok(r.ms < BOUND_MS, `30 comments and a tag: the index cost ${r.ms.toFixed(1)} ms of CPU`);
  assert.deepEqual(tags(renderedBlockElements(El(r.md), withTag, 4)), ["B"], "the html block renders as the badge");
  pairedAfter(r.md, withTag);
  // comments alone: blank, no node, the paragraphs after it pair to their own blocks
  const alone = around(comments(30));
  r = timed(alone);
  assert.ok(r.ms < BOUND_MS, `30 comments alone: the index cost ${r.ms.toFixed(1)} ms of CPU`);
  assert.deepEqual(renderedBlockElements(El(r.md), alone, 4), [], "a block of comments alone renders nothing");
  pairedAfter(r.md, alone);
  // comments then words, and comments then an unterminated comment (the two other failing tails), read in their length too
  for (const tail of [" trailing words", " <!-- open"]) {
    r = timed(around(comments(30) + tail));
    assert.ok(r.ms < BOUND_MS, `30 comments then ${JSON.stringify(tail)}: the index cost ${r.ms.toFixed(1)} ms of CPU`);
  }
  // the gaps can be any whitespace, and a comment may span lines (the block ends with the line holding its `-->`)
  for (const line of [comments(30, "\t  "), "<!-- a comment\nover two lines --> \t <!-- and another -->"]) {
    const spaced = around(line);
    r = timed(spaced);
    assert.ok(r.ms < BOUND_MS, `${JSON.stringify(line.slice(0, 24))}...: the index cost ${r.ms.toFixed(1)} ms of CPU`);
    assert.deepEqual(renderedBlockElements(El(r.md), spaced, 4), [], "still a block of comments alone");
    pairedAfter(r.md, spaced);
  }
});

test("a comment at each end of a line does not vouch for what stands between them: the block keeps its node and the blocks after it pair to their own elements", () => {
  // words between two comments render as a text node of the html block's; with the block read as blank, the next
  // paragraph took the text node (refused as a rendered-text mismatch) and every block after it paired one node early
  const words = around("<!-- a --> visible words between two comments <!-- b -->");
  let md = rendered(words);
  const wn = wordsNode(md);
  assert.ok(wn, "the words render as a top-level text node");
  assert.equal(renderedBlockIndex(El(md), words, Nd(wn)), 4, "the text node is the html block's");
  assert.deepEqual(renderedBlockElements(El(md), words, 4), [], "which has no element (a text node is not one)");
  pairedAfter(md, words);
  // a tag between two comments: the block's element
  const bold = around("<!-- a --><b>bold words</b><!-- b -->");
  md = rendered(bold);
  assert.deepEqual(tags(renderedBlockElements(El(md), bold, 4)), ["B"], "the html block renders as the tag between the comments");
  pairedAfter(md, bold);
  // the two shapes the rule always read right: one comment alone, and a comment followed by words
  const one = around("<!-- only a comment -->");
  md = rendered(one);
  assert.deepEqual(renderedBlockElements(El(md), one, 4), [], "one comment: blank");
  pairedAfter(md, one);
  const trailing = around("<!-- a --> trailing words after one comment");
  md = rendered(trailing);
  assert.equal(renderedBlockIndex(El(md), trailing, Nd(wordsNode(md) as FakeText)), 4, "the trailing words are the html block's");
  pairedAfter(md, trailing);
});
