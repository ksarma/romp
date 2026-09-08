// Three edges of the Rendered view's deletion points that the review of the inline-display follow-on
// (plans/file-review.md, 2026-09-07) found unpinned or wrong; each is now the code's rule, and each has a test a
// one-token mutation of the code fails. Driven over marked's output under the viewer's configuration, parsed into
// the structural stand-in anchor-map.test.ts uses (there is no jsdom in this tree).
//
//   1. The blank lines a token's raw swallows belong to no block. marked's heading, setext-heading and hr regexes
//      take every trailing newline into the token's raw (`## Title\n\n` is one heading token, `\n\n` and all), and
//      its lexer moves a lone newline onto the token before it (a blockquote followed by one blank line), while a
//      paragraph's blank line is a separate `space` token the index skips. renderedSpot went by the raw's extent,
//      so a deletion on the blank line under a heading found no mapped character at or past its offset and was
//      placed after the heading's last word — the struck paragraph read at heading size, inside a block it never
//      belonged to — while the same blank line under a paragraph was left unpainted. The plan's rule is one: a
//      blank line between blocks leaves the change unpainted. A block now holds the offsets of its own rows (its
//      text lines, the last one's line ending, and the end of the file when it comes right after that ending), so
//      the outcome no longer depends on the kind of block above the blank line, and Raw's placement — the empty
//      row — has no counterpart in Rendered, which is why the change keeps its card there.
//   2. A deletion at the first character of a nested hole (a fenced code block or a table inside a list item)
//      sits after the item text before the hole. The rule held (`offset <= first.startN`) but no test placed a
//      deletion exactly there: with the comparison narrowed to `<` every suite stayed green while the change went
//      card-only. The nested-block tests probe the text before the hole, its inside and the text after it; this
//      one probes the boundary itself, on both kinds of hole, with the offset one before (the indentation) and one
//      after (inside) as the controls.
//   3. The design block that introduces the change painters (the "change marks" section of anchor-map.ts) says what
//      paintChangesRendered does with a deletion. It kept Slice 2's sentence — Rendered leaves a deletion to its
//      card — after the follow-on made the painter place it, so the module said two things about one branch; the
//      plan tests (tests/test_file_review_plan_rendered_deletions.py) read the branch and the plan, not this comment.
//
// Fixtures are synthetic (the notes-api world).
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { marked } from "marked";
import { paintChangesRaw, paintChangesRendered, unpaintChanges, PILCROW, type ChangePaint } from "./anchor-map";

const SRC = path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map.ts");

// ── the viewer's marked configuration (file-view.ts; pinned by anchor-map.test.ts) ────────────────
marked.setOptions({ gfm: true, breaks: false });
marked.use({
  tokenizer: {
    del(src: string) {
      const m = /^~~(?=\S)([\s\S]*?\S)~~/.exec(src);
      if (!m) return undefined;
      return { type: "del", raw: m[0], text: m[1], tokens: (this as { lexer: { inlineTokens(s: string): unknown[] } }).lexer.inlineTokens(m[1]) };
    },
  },
} as Parameters<typeof marked.use>[0]);

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser ─────
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
}
class FakeDocument {
  createElement(tag: string): FakeElement { return new FakeElement(this, tag.toUpperCase()); }
  createTextNode(s: string): FakeText { return new FakeText(this, s); }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
    return e in NAMED ? NAMED[e] : m;
  });
}
/** The fragment parser a browser's innerHTML applies, reduced to what marked emits (anchor-map.test.ts's). */
function parseHTML(doc: FakeDocument, html: string): FakeNode[] {
  html = html.replace(/\r\n?/g, "\n");
  const root = doc.createElement("#fragment");
  const stack: FakeElement[] = [root];
  let i = 0;
  const top = () => stack[stack.length - 1];
  while (i < html.length) {
    if (html[i] === "<") {
      if (html.startsWith("<!--", i)) { const e = html.indexOf("-->", i); i = e < 0 ? html.length : e + 3; continue; }
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
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], decodeEntities(a[2] ?? a[3] ?? a[4] ?? ""));
      top().appendChild(el);
      i += m[0].length;
      if (!m[3] && !VOID.has(m[1].toLowerCase())) {
        stack.push(el);
        if (m[1].toLowerCase() === "pre" && html[i] === "\n") i++;
      }
      continue;
    }
    let e = html.indexOf("<", i);
    if (e < 0) e = html.length;
    top().appendChild(doc.createTextNode(decodeEntities(html.slice(i, e))));
    i = e;
  }
  return root.childNodes.slice();
}
const escapeHtml = (s: string): string => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
/** The viewer's Raw rows for a plain-text file (no highlighter): one `.fv-cl > .fv-ct` per line. */
function buildRaw(text: string): FakeElement {
  const doc = new FakeDocument();
  const lines = text.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  const code = doc.createElement("code"); code.setAttribute("class", "hljs");
  for (const n of parseHTML(doc, lines.map((ln) => `<span class="fv-cl"><span class="fv-ct">${escapeHtml(ln)}</span></span>`).join(""))) code.appendChild(n);
  return code;
}
/** The viewer's Rendered body: `div.fileview-md > marked output`. */
function buildRendered(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);
  return box;
}
const El = (n: FakeNode) => n as unknown as Element;

// ── helpers ────────────────────────────────────────────────────────────────────────────────────────
/** A structural serialization: every text node its own `#"..."`, every attribute shown. */
function serialize(n: FakeNode): string {
  if (n.nodeType === 3) return "#" + JSON.stringify((n as FakeText).data);
  const e = n as FakeElement;
  const attrs = [...e.attrs.entries()].sort().map(([k, v]) => ` ${k}=${JSON.stringify(v)}`).join("");
  return `<${e.tagName}${attrs}>` + e.childNodes.map(serialize).join("") + `</${e.tagName}>`;
}
const docOrder = (root: FakeNode): FakeNode[] => { const out: FakeNode[] = []; const visit = (n: FakeNode) => { out.push(n); n.childNodes.forEach(visit); }; visit(root); return out; };
const elements = (root: FakeNode): FakeElement[] => docOrder(root).filter((n) => n.nodeType === 1) as FakeElement[];
const withClass = (root: FakeNode, cls: string): FakeElement[] => elements(root).filter((e) => (e.getAttribute("class") || "").split(" ").includes(cls));
const withTag = (root: FakeNode, tag: string): FakeElement[] => elements(root).filter((e) => e.tagName === tag);
/** The text of `block` before `point` and after it, in document order (the point itself holds none). */
function around(block: FakeNode, point: FakeNode): [string, string] {
  let pre = "", post = "", seen = false;
  const visit = (n: FakeNode) => {
    if (n === point) { seen = true; return; }
    if (n.nodeType === 3) { if (seen) post += (n as FakeText).data; else pre += (n as FakeText).data; return; }
    for (const c of n.childNodes) visit(c);
  };
  visit(block);
  return [pre, post];
}
/** The nearest top-level block (a child of the .fileview-md box) holding `n`. */
const blockOf = (box: FakeNode, n: FakeNode): FakeElement => { let x = n; while (x.parentNode && x.parentNode !== box) x = x.parentNode; return x as FakeElement; };
const inside = (n: FakeNode, tag: string): boolean => { let p = n.parentNode; while (p) { if (p.nodeType === 1 && (p as FakeElement).tagName === tag) return true; p = p.parentNode; } return false; };
const at = (source: string, s: string, from = 0): number => { const i = source.indexOf(s, from); assert.ok(i >= 0, "source has " + JSON.stringify(s)); return i; };
const COLORS: Record<string, string> = { web: "rgb(10, 20, 30)" };   // api has no live match: no colour (the plan's Risks entry)
const stylesFor = (c: ChangePaint): Record<string, string> => (COLORS[c.author] ? { "--fc-author": COLORS[c.author] } : {});
const del = (id: string, curFrom: number, oldText = "gone", author = "web"): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText, author });
const point = (root: FakeNode, id: string): FakeElement => { const x = withClass(root, "fc-del").find((m) => m.getAttribute("data-id") === id); assert.ok(x, id + " painted"); return x!; };

// ── 1. the blank lines a token's raw swallows belong to no block ───────────────────────────────────

/** Paint one deletion at `offset` and report where it went: null when unpainted, else the block's tag and the block's
 *  text before and after the point (trimmed: marked wraps a blockquote's paragraph in newlines of its own). Restores
 *  the body afterwards. */
function place(source: string, offset: number, oldText = "\nOld para.\n"): { tag: string; pre: string; post: string } | null {
  const box = buildRendered(source);
  const before = serialize(box);
  const r = paintChangesRendered(El(box), source, [del("d", offset, oldText)], stylesFor);
  let out: { tag: string; pre: string; post: string } | null = null;
  if (r.painted.length) {
    assert.deepEqual(r, { painted: ["d"], unpainted: [] });
    const pt = point(box, "d");
    const blk = blockOf(box, pt);
    const [pre, post] = around(blk, pt);
    out = { tag: blk.tagName, pre: pre.trim(), post: post.trim() };
  } else {
    assert.deepEqual(r, { painted: [], unpainted: ["d"] });
    assert.equal(withClass(box, "fc-del").length, 0, "an unpainted change is nowhere in the body");
  }
  unpaintChanges(El(box));
  assert.equal(serialize(box), before);
  return out;
}
/** The 0-based Raw row the same deletion lands on. */
function rawRow(source: string, offset: number): number {
  const code = buildRaw(source);
  const marks = paintChangesRaw(El(code), source, [del("d", offset)], stylesFor) as unknown as FakeElement[];
  assert.equal(marks.length, 1, "Raw paints every deletion");
  let row: FakeNode = marks[0];
  while (row.parentNode && row.parentNode !== code) row = row.parentNode;
  return code.childNodes.indexOf(row);
}
/** The raw of the token holding `offset` and the raw's trailing newline count, so each case states the shape it tests. */
function tokenAt(source: string, offset: number): { type: string; raw: string; tail: number } {
  let p = 0;
  for (const t of marked.lexer(source)) {
    if (p <= offset && offset < p + t.raw.length) return { type: t.type, raw: t.raw, tail: t.raw.length - t.raw.replace(/\n+$/, "").length };
    p += t.raw.length;
  }
  return { type: "(end)", raw: "", tail: 0 };
}

test("Rendered deletion points on the blank line under a heading (an ATX or a setext one), an hr, or a blockquote — a line marked's token raw swallows — are unpainted like the blank line under a paragraph, while the block's own line ending still sits after its last word and the block below still opens at its first", () => {
  const H = "## Title\n\nNext para.\n";
  // the shape under test: one heading token carries both newlines, so the blank line is inside its raw
  assert.deepEqual(tokenAt(H, at(H, "\n\n") + 1), { type: "heading", raw: "## Title\n\n", tail: 2 });
  assert.deepEqual(place(H, at(H, "\n\n")), { tag: "H2", pre: "Title", post: "" }, "the heading's own line ending: after its last word, as a paragraph's is");
  assert.equal(place(H, at(H, "\n\n") + 1), null, "the blank line: unpainted, not struck inside the heading");
  assert.deepEqual(place(H, at(H, "Next")), { tag: "P", pre: "", post: "Next para." }, "the paragraph's first character: the paragraph");
  assert.equal(rawRow(H, at(H, "\n\n") + 1), 1, "Raw shows the same deletion on the empty row, which Rendered has no counterpart for");
  // two swallowed blank lines: both unpainted
  const H2 = "## Title\n\n\nNext para.\n";
  assert.equal(tokenAt(H2, 9).tail, 3);
  assert.equal(place(H2, 9), null); assert.equal(place(H2, 10), null);
  assert.deepEqual(place(H2, at(H2, "Next")), { tag: "P", pre: "", post: "Next para." });
  // a removed blank line (the sidecar's del with oldText "\n": one pilcrow) on a swallowed blank line is unpainted too
  assert.equal(place(H2, 9, "\n"), null);
  assert.equal(PILCROW, "¶");
  // a heading followed by a code fence, a setext heading, an hr, a blockquote: the same rule whatever the token
  const F = "## Title\n\n```\ncode line\n```\n";
  assert.equal(place(F, at(F, "\n\n") + 1), null); assert.deepEqual(place(F, at(F, "\n\n")), { tag: "H2", pre: "Title", post: "" });
  const S = "Title\n=====\n\nNext para.\n";
  assert.deepEqual(tokenAt(S, at(S, "\n\n") + 1), { type: "heading", raw: "Title\n=====\n\n", tail: 2 });
  assert.equal(place(S, at(S, "\n\n") + 1), null, "setext: the blank line");
  assert.deepEqual(place(S, at(S, "\n\n")), { tag: "H1", pre: "Title", post: "" }, "setext: the underline's line ending, after the title");
  assert.deepEqual(place(S, at(S, "Next")), { tag: "P", pre: "", post: "Next para." });
  const R = "---\n\nNext para.\n";
  assert.deepEqual(tokenAt(R, 4), { type: "hr", raw: "---\n\n", tail: 2 });
  assert.equal(place(R, 4), null, "hr: the blank line"); assert.equal(place(R, 3), null, "hr: no text to sit against");
  assert.deepEqual(place(R, at(R, "Next")), { tag: "P", pre: "", post: "Next para." });
  const Q = "> quote\n\nNext para.\n";
  assert.deepEqual(tokenAt(Q, at(Q, "\n\n") + 1), { type: "blockquote", raw: "> quote\n\n", tail: 2 }, "the lexer moved the lone newline onto the blockquote");
  assert.deepEqual(place(Q, at(Q, "\n\n")), { tag: "BLOCKQUOTE", pre: "quote", post: "" });
  assert.equal(place(Q, at(Q, "\n\n") + 1), null, "blockquote: the blank line");
  assert.deepEqual(place(Q, at(Q, "Next")), { tag: "P", pre: "", post: "Next para." });
  // a blockquote before TWO blank lines keeps one newline and a `space` token follows: the first blank line begins
  // exactly where the raw ends, and was the "block that ends here" before — it is a blank line, unpainted
  const Q2 = "> quote\n\n\nNext para.\n";
  assert.deepEqual(tokenAt(Q2, 8), { type: "space", raw: "\n\n", tail: 2 });
  assert.deepEqual(place(Q2, 7), { tag: "BLOCKQUOTE", pre: "quote", post: "" });
  assert.equal(place(Q2, 8), null); assert.equal(place(Q2, 9), null);
  assert.deepEqual(place(Q2, at(Q2, "Next")), { tag: "P", pre: "", post: "Next para." });
  // the control the rule is modelled on: a paragraph's blank line is a `space` token and was always unpainted
  const P = "Alpha.\n\nOmega.\n";
  assert.deepEqual(tokenAt(P, 7), { type: "space", raw: "\n\n", tail: 2 });
  assert.deepEqual(place(P, 6), { tag: "P", pre: "Alpha.", post: "" });
  assert.equal(place(P, 7), null);
  assert.deepEqual(place(P, at(P, "Omega")), { tag: "P", pre: "", post: "Omega." });
});

test("Rendered deletion points at the end of a file whose last block is a heading: right after the heading's line ending (or with no line ending) the point sits after the title, as after a paragraph's; after a trailing blank line the file ends on an empty row and the change is unpainted, as it is under a paragraph", () => {
  for (const [src, tail] of [["## Title\n", ""], ["## Title", ""], ["## Title\n\n", null], ["## Title\n\n\n", null]] as const) {
    const got = place(src, src.length);
    if (tail === null) assert.equal(got, null, JSON.stringify(src) + ": a blank line ends the file");
    else assert.deepEqual(got, { tag: "H2", pre: "Title", post: tail }, JSON.stringify(src));
  }
  // the swallowed blank lines before the end are unpainted as well; the heading's own line ending is not
  assert.equal(place("## Title\n\n", 9), null);
  assert.deepEqual(place("## Title\n\n", 8), { tag: "H2", pre: "Title", post: "" });
  // the paragraph twins, as anchor-map.test.ts pins them
  assert.deepEqual(place("Alpha.\n\nOmega.\n", "Alpha.\n\nOmega.\n".length), { tag: "P", pre: "Omega.", post: "" });
  assert.equal(place("Alpha.\n\nOmega.\n\n", "Alpha.\n\nOmega.\n\n".length), null);
  // CRLF: the rows are the same rows; a line ending's CR and LF both sit at its row's end, a blank line's are unpainted
  const C = "Alpha.\r\n\r\n## Title\r\n\r\nNext.\r\n";
  const cr = at(C, "\r\n\r\nNext");
  assert.deepEqual(place(C, cr), { tag: "H2", pre: "Title", post: "" }, "the heading's CR");
  assert.deepEqual(place(C, cr + 1), { tag: "H2", pre: "Title", post: "" }, "the heading's LF");
  assert.equal(place(C, cr + 2), null, "the blank line's CR"); assert.equal(place(C, cr + 3), null, "the blank line's LF");
  assert.deepEqual(place(C, at(C, "Next")), { tag: "P", pre: "", post: "Next." });
  assert.deepEqual(place(C, C.length), { tag: "P", pre: "Next.", post: "" }, "the end of the file, right after the last row's CRLF");
  assert.equal(place(C + "\r\n", C.length + 2), null, "…but not after a trailing blank line");
});

// ── 2. a deletion at the first character of a nested hole sits after the text before it ───────────

test("Rendered deletion points at the first character of a nested code fence or table inside a list item sit after the item text before the hole (one character earlier, in the indentation, too); one character in, they are inside the hole and unpainted", () => {
  const cases: [string, string, string][] = [
    // source, the hole's first characters, the text the point sits against
    ["- Item one\n\n  ```\n  code line\n  ```\n\n  after code\n", "```", "Item one"],
    ["- Item one\n\n  | a | b |\n  |---|---|\n  | 1 | 2 |\n\n  after table\n", "| a |", "Item one"],
  ];
  for (const [source, holeStart, text] of cases) {
    const box = buildRendered(source);
    assert.equal(withTag(box, "LI").length, 1, "one item holds the nested block");
    const before = serialize(box);
    const start = at(source, holeStart);
    const r = paintChangesRendered(El(box), source, [
      del("h-at", start),                     // the hole's first character: the boundary itself
      del("h-indent", start - 1),             // the indentation before it
      del("h-in", start + 1),                 // one character in: the hole
    ], stylesFor);
    assert.deepEqual(r, { painted: ["h-at", "h-indent"], unpainted: ["h-in"] }, JSON.stringify(holeStart));
    for (const id of ["h-at", "h-indent"]) {
      const pt = point(box, id);
      assert.ok(!inside(pt, "PRE") && !inside(pt, "TABLE"), id + ": not inside the hole's element");
      const para = pt.parentNode as FakeElement;
      assert.equal(para.tagName, "P", id + ": in the item's paragraph");
      assert.equal(para.textContent, text, id + ": the paragraph before the hole");
      const [pre, post] = around(para, pt);
      assert.equal(pre, text, id + ": after the text before the hole");
      assert.equal(post, "", id + ": nothing of the paragraph after it");
    }
    assert.deepEqual(withClass(box, "fc-del").map((m) => m.getAttribute("data-id")), ["h-at", "h-indent"], "two offsets, one position: the point painted second sits after the first (the boundary rule)");
    unpaintChanges(El(box));
    assert.equal(serialize(box), before);
  }
});

// ── 3. the change painters' design block says what the Rendered painter does with a deletion ─────

test("anchor-map.ts's change-marks section says the Rendered view places a deletion's point through the index map and leaves only an unplaceable change to its card — not Slice 2's sentence that every Rendered deletion is card-only, which paintChangesRendered stopped doing", () => {
  const src = fs.readFileSync(SRC, "utf8");
  const open = src.indexOf("// ── change marks");
  assert.ok(open >= 0, "the change-marks section banner");
  const close = src.indexOf("export type ChangePaint", open);
  assert.ok(close > open, "the section's first declaration");
  const design = src.slice(open, close);
  // the sentence the follow-on made false, in any wording that keeps its claim
  assert.ok(!/leaves a deletion to its\s+(?:\/\/ )?card/.test(design), "the design block no longer hands every Rendered deletion to its card");
  assert.ok(!/cannot be placed in rendered prose/.test(design), "…nor cites the plan for a rule the plan no longer states");
  // and the one that is true, in terms a reader can follow to the code
  assert.match(design, /paintRenderedPoint/, "the design block names the Rendered point painter");
  assert.match(design, /\bpoint\b/, "…and calls the Rendered deletion a point");
  // the module header agrees: it is the other place the file states the rule
  const header = src.slice(0, src.indexOf("import "));
  assert.match(header, /paintRenderedPoint/, "the module header states the same rule");
  // the painter itself still does what both say
  const branch = /if \(c\.kind === "del"\) \{[^}]*?paintRenderedPoint\(renderedRoot, source, c\.curFrom, "fc-del"/;
  assert.match(src, branch, "paintChangesRendered's del branch paints the point");
});
