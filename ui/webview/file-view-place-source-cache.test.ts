// The anchor map's source half is built once per source, not once per Rendered root (anchor-map.ts sourceTable;
// plans/markdown-viewer.md Slice 2). The reader's place seats through the block table on every paint of a text view,
// and a Rendered/Raw switch or a reload of unchanged bytes gives the body new children over the same text, so before
// this every such paint lexed and walked the whole source again inside the click (the Slice 2 review, round 4: 5,000
// paragraphs, 147 ms per fresh root, 48 of them the lex and about 70 the walk; the pairing, which is the root's own,
// about 22). Here marked's Lexer.lex is counted across the block table and three roots over one source: one lex. And
// the per-root pairing must not leak between roots: a root whose paragraph text differs from the file (the sanitizer
// dropped an inline element's text) refuses that block, and a fresh root over the same source, correct, maps it still,
// so the walk's answers are copied per root and never written through. Node only, over the place suite's DOM stand-in
// (marked's output parsed into a minimal tree; the pairing needs no layout). Synthetic fixtures.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { marked, Lexer } from "marked";
import { sourceBlockSpans, renderedBlockIndex, renderedBlockElements, mapRenderedSelection, type SelLike } from "./anchor-map";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

// ── a DOM stand-in: the anchor-map suite's minimal tree ─────────────────────────────────────────────
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
class FakeText extends FakeNode {
  nodeType = 3;
  constructor(doc: FakeDocument, public data: string) { super(doc); hideEdges(this); }
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
  constructor(doc: FakeDocument, public tagName: string) { super(doc); hideEdges(this); }
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
const El = (n: FakeNode) => n as unknown as Element;

/** `div.fileview-md > marked output`, a fresh root each call (what a view switch or a reload gives the body). */
function rendered(src: string): { md: FakeElement; blocks: FakeElement[] } {
  const doc = new FakeDocument();
  const md = doc.createElement("div"); md.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(src) as string)) md.appendChild(n);
  return { md, blocks: md.childNodes.filter((n): n is FakeElement => n instanceof FakeElement) };
}
const firstText = (el: FakeElement): FakeText => { const t = el.childNodes.find((c) => c instanceof FakeText); assert.ok(t, "a text node"); return t as FakeText; };
/** A selection over the first `n` characters of an element's first text node. */
const selOver = (el: FakeElement, n: number): SelLike => { const t = firstText(el); return { anchorNode: t as unknown as Node, anchorOffset: 0, focusNode: t as unknown as Node, focusOffset: n, isCollapsed: false }; };

const PARA = (i: number) => `Paragraph ${i}: some words of the report, enough to make a line.`;
const DOC = "# Report\n\n" + Array.from({ length: 6 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n\n```py\nx = 1\n```\n";

test("the source is lexed and walked once across the block table and every Rendered root over it: one Lexer.lex for three roots; each root pairs the same blocks to its own elements", () => {
  const A = rendered(DOC), B = rendered(DOC), C = rendered(DOC);   // built first: marked's own parse lexes too
  const lex = Lexer.lex;
  let calls = 0;
  (Lexer as unknown as { lex: typeof Lexer.lex }).lex = function (this: unknown, ...args: Parameters<typeof Lexer.lex>) { calls++; return lex.apply(Lexer, args); };
  try {
    const spans = sourceBlockSpans(DOC);
    assert.equal(spans.length, 8, "the heading, six paragraphs and the code block");
    for (const root of [A, B, C]) {
      for (let i = 0; i < root.blocks.length; i++) {
        assert.equal(renderedBlockIndex(El(root.md), DOC, El(root.blocks[i])), i, `block ${i} of a root`);
        assert.deepEqual(renderedBlockElements(El(root.md), DOC, i), [El(root.blocks[i])], `block ${i}'s element is the root's own`);
      }
    }
    assert.equal(calls, 1, "one lex: the block table's; the three roots read the source half from the table");
  } finally {
    (Lexer as unknown as { lex: typeof Lexer.lex }).lex = lex;
  }
});

test("the pairing is each root's own: a root whose paragraph text differs from the file refuses that block, and a fresh root over the same source maps it still", () => {
  const src = DOC.replace("Paragraph 3:", "Paragraph 3 (mismatch scene):");   // a source of its own, so the table is built here
  const bad = rendered(src);
  firstText(bad.blocks[3]).data = "Paragraph 3 (mismatch scene): the sanitizer dropped words here.";   // the rendered text no longer matches the file
  assert.equal(renderedBlockIndex(El(bad.md), src, El(bad.blocks[3])), 3, "still paired, by the fallback for a mismatch");
  const refused = mapRenderedSelection(selOver(bad.blocks[3], 9), El(bad.md), src);
  assert.equal(refused.ok, false, "a selection in the mismatched paragraph is refused");
  assert.match(String((refused as { reason?: string }).reason || JSON.stringify(refused)), /does not match/);
  const good = rendered(src);
  const ok = mapRenderedSelection(selOver(good.blocks[3], 9), El(good.md), src);
  assert.equal(ok.ok, true, "the same block on a fresh, correct root maps (its walk was not written through by the other root's pairing)");
  assert.equal((ok as { quote: string }).quote, "Paragraph");
  // and the mismatched root still refuses after the good one was analysed: nothing flowed the other way either
  assert.equal(mapRenderedSelection(selOver(bad.blocks[3], 9), El(bad.md), src).ok, false);
  assert.equal(mapRenderedSelection(selOver(good.blocks[2], 9), El(good.md), src).ok, true);
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
