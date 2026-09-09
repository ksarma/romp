// The anchor map over a paragraph marked joined onto the one before it (anchor-map.ts sourceRaw). marked 12's block
// lexer sets its lastParagraphClipped flag whenever any block extension's start hint returned a position, however far
// below, and then joins the next top-level paragraph onto the previous one with `lastToken.raw += "\n" + token.raw`
// after the single newline between them was already moved onto the previous raw, so the joined raw holds one newline
// per join the source does not, while `text` gets one per join and is the source's text. The paragraph regex stops
// early for its own reasons, and the tokenizer it stopped for then refuses: a header-looking line over a delimiter row
// with a different cell count (the table), a lowercase `<prefix>` line (the paragraph rule's html lookahead is a
// prefix test, the html tokenizer's is not), a bare `* ` or `1. ` bullet (the list refuses an empty item that would
// interrupt). With a display formula anywhere later in the note, which is what puts a block hint into files.js and
// feed.js with this slice (the math hint is the grammar's one block hint: the callout's, which joined alike, went in
// round 3, its line being a paragraph interrupt already, md-config.ts), the join fired, the raw tiled nothing from
// there on, every later block's span collapsed to the join's start and every selection past it refused; inside a
// quote's or a callout's body the same join refused that block alone (the Slice 4 review, rounds 2 and 3). A second
// join needs no hint: the gfm table interrupt admits any indentation on its header line, so a paragraph stops before a
// line indented four columns (four spaces, or a tab) that a delimiter-row-shaped line or a `---` follows, the code
// tokenizer, which runs before the table's, takes the indented line, and the lexer joins it onto the paragraph with the
// indentation gone from `text` (CommonMark's own reading: an indented code block cannot interrupt a paragraph), at the
// top level, in a quote's body and in a list item's block text; a walk of the raw that allowed for the doubled newline
// alone stopped at the first stripped space and every later block's span collapsed to the join's start (round 5; the
// same at the base). The mapping now rebuilds the source's lines from raw and text (each text line the raw line it came
// from less up to four spaces, a blank raw line no text line matches a join's newline) and maps the text into them
// line by line. These tests hold that over every trigger shape of both joins at the top level and nested, over
// controls that never joined (a callout below in place of the formula among them), and over a fuzz of the joins;
// md-config-merged-paragraph-browser.test.ts maps past both joins over the real Files bundle. The
// rendered shape is anchor-map-obsidian.test.ts's stand-in (marked's output parsed into a DOM stand-in, the fill's
// KaTeX root stood in for). Synthetic notes only.
import { test } from "node:test";
import assert from "node:assert/strict";
import { Lexer, marked } from "marked";
import type { Token } from "marked";
import { applyMdConfig } from "./md-config";
import { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex, type SelLike, type MapResult, type SourceRange } from "./anchor-map";

applyMdConfig();

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser (anchor-map.test.ts's) ──
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
  replaceChild(n: FakeNode, old: FakeNode): FakeNode { this.insertBefore(n, old); this.removeChild(old); return old; }
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
function parseHTML(doc: FakeDocument, html: string): FakeNode[] {
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
/** What the fill leaves where a math placeholder stood (math.ts renderMathPlaceholders): a `.katex` root of glyphs, inside a
 *  `.katex-display` span for a display formula, the placeholder unwrapped. */
function standInFill(root: FakeElement): void {
  const walk = (n: FakeNode) => {
    for (const c of n.childNodes.slice()) {
      if (c.nodeType !== 1) continue;
      const el = c as FakeElement;
      const cls = el.getAttribute("class") || "";
      if (cls === "md-math-inline" || cls === "md-math-display") {
        const doc = el.ownerDocument;
        const katex = doc.createElement("span"); katex.setAttribute("class", "katex");
        katex.appendChild(doc.createTextNode(el.textContent.replace(/[\\^_{}]/g, "")));
        let repl: FakeElement = katex;
        if (cls === "md-math-display") { repl = doc.createElement("span"); repl.setAttribute("class", "katex-display"); repl.appendChild(katex); }
        (n as FakeElement).replaceChild(repl, el);
      } else walk(el);
    }
  };
  walk(root);
}
function buildRendered(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);
  standInFill(box);
  return box;
}
const El = (n: FakeNode) => n as unknown as Element;
function allText(root: FakeNode): FakeText[] {
  if (root.nodeType === 3) return [root as FakeText];
  const out: FakeText[] = [];
  for (const c of root.childNodes) out.push(...allText(c));
  return out;
}
type Pt = { node: FakeNode; offset: number };
/** The point at the start (or, with `atEnd`, the end) of the k-th occurrence of `needle` in the rendered text under root. */
function point(root: FakeNode, needle: string, atEnd = false, k = 0): Pt {
  let seen = 0;
  for (const t of allText(root)) {
    let from = 0;
    for (;;) {
      const i = t.data.indexOf(needle, from);
      if (i < 0) break;
      if (seen++ === k) return { node: t, offset: atEnd ? i + needle.length : i };
      from = i + 1;
    }
  }
  throw new Error("not in the rendered text: " + JSON.stringify(needle));
}
const sel = (a: Pt, f: Pt): SelLike => ({ anchorNode: a.node as unknown as Node, anchorOffset: a.offset, focusNode: f.node as unknown as Node, focusOffset: f.offset, isCollapsed: false });
const ok = (r: MapResult, msg: string) => { assert.equal(r.ok, true, msg + ": " + ((r as { reason?: string }).reason || "")); return r as Extract<MapResult, { ok: true }>; };
/** Select `text` (its k-th occurrence in the rendered box) and map it. */
const mapText = (box: FakeElement, source: string, text: string, k = 0): MapResult => mapRenderedSelection(sel(point(box, text, false, k), point(box, text, true, k)), El(box), source);
/** `text` maps to its k-th occurrence in the source, whole. */
function mapsAt(box: FakeElement, source: string, text: string, k = 0): void {
  let at = -1;
  for (let i = 0; i <= k; i++) { at = source.indexOf(text, at + 1); assert.ok(at >= 0, "in the source: " + JSON.stringify(text)); }
  const r = ok(mapText(box, source, text, k), JSON.stringify(text));
  assert.deepEqual(r.range, { start: at, end: at + text.length }, JSON.stringify(text) + " maps to its own offset");
  assert.equal(r.quote, text);
}

const nonSpace = (src: string): Token[] => Lexer.lex(src).filter((t) => t.type !== "space");
const trimNL = (s: string): string => s.replace(/\n+$/, "");
/** The source as marked's lexer reads it: a line's leading tabs are four spaces each (its raws index that text). */
const expandTabs = (s: string): string => s.replace(/^( *)(\t+)/gm, (_, sp: string, tabs: string) => sp + "    ".repeat(tabs.length));
/** A joined paragraph's span reads the source's lines of its text: line i of the text is line i of the span less up to
 *  four spaces of indentation, the code join's (anchor-map.ts sourceRaw). */
function readsLines(got: string, text: string): boolean {
  const g = expandTabs(got).split("\n"), t = text.split("\n");
  return g.length === t.length && g.every((l, i) => l.endsWith(t[i]) && /^ {0,4}$/.test(l.slice(0, l.length - t[i].length)));
}
/** The block table against the tokens: as many spans as tokens, in order and disjoint, each paragraph's span reading
 *  the token's text (the source's text, whatever the raw holds; a joined paragraph's, the source's lines of it) and
 *  every other token's span its raw. */
function checkSpans(source: string, why: string): { spans: SourceRange[]; tokens: Token[]; joins: number } {
  const tokens = nonSpace(source);
  const spans = sourceBlockSpans(source);
  assert.equal(spans.length, tokens.length, why + ": one span per top-level token");
  let last = -1, joins = 0;
  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i], s = spans[i];
    assert.ok(s.start > last || (i === 0 && s.start === 0), `${why}: span ${i} starts at ${s.start}, after ${last}: ${JSON.stringify(spans)}`);
    assert.ok(s.end >= s.start, why + ": span " + i + " is ordered");
    const got = source.slice(s.start, s.end);
    if (t.type === "paragraph" && t.raw.includes("\n\n")) {
      joins++;
      assert.ok(readsLines(got, trimNL((t as { text: string }).text)), `${why}: span ${i} (a joined paragraph) reads the source's lines of the token's text: ${JSON.stringify(got)} against ${JSON.stringify((t as { text: string }).text)}`);
    } else {
      const want = t.type === "paragraph" ? trimNL((t as { text: string }).text) : trimNL(t.raw);
      assert.equal(expandTabs(got), want, `${why}: span ${i} (${t.type}) reads the token`);
    }
    last = s.end;
  }
  return { spans, tokens, joins };
}
/** Every top-level element is its own block, in order (the 1:1 pairing), and the whole text of every paragraph element
 *  maps to its block's span. */
function checkPairing(source: string, why: string): FakeElement {
  const box = buildRendered(source);
  const spans = sourceBlockSpans(source);
  const tokens = nonSpace(source);
  const kids = box.childNodes.filter((n) => n.nodeType === 1) as FakeElement[];
  assert.equal(kids.length, spans.length, why + ": as many elements as blocks");
  for (let i = 0; i < kids.length; i++) {
    if (tokens[i].type === "html") continue;   // an html block is the author's markup: refused by the walk, paired by resync, not this test's subject
    assert.equal(renderedBlockIndex(El(box), source, kids[i] as unknown as Node), i, why + ": element " + i + " is block " + i);
    if (kids[i].tagName !== "P") continue;
    const texts = allText(kids[i]);
    if (!texts.length) continue;
    const first = texts[0], lastT = texts[texts.length - 1];
    const r = ok(mapRenderedSelection(sel({ node: first, offset: 0 }, { node: lastT, offset: lastT.data.length }), El(box), source), why + ": paragraph element " + i);
    const shown = kids[i].textContent.trim();
    if (/^[^<*`$_\\[\]]*$/.test(source.slice(spans[i].start, spans[i].end))) {
      // plain prose: the whole element is the whole block
      assert.deepEqual(r.range, spans[i], `${why}: paragraph element ${i} maps to its block ${JSON.stringify(spans[i])}, got ${JSON.stringify(r.range)}`);
    } else {
      // inline markup renders no text of its own (an inline html tag, a delimiter): the range lies inside the block and starts and
      // ends on the characters shown
      assert.ok(r.range.start >= spans[i].start && r.range.end <= spans[i].end && r.range.end > r.range.start, `${why}: paragraph element ${i} maps inside its block ${JSON.stringify(spans[i])}, got ${JSON.stringify(r.range)}`);
      assert.equal(source[r.range.start], shown[0], why + ": the range starts on the first shown character");
      assert.equal(source[r.range.end - 1], shown[shown.length - 1], why + ": the range ends on the last shown character");
    }
  }
  return box;
}

const SEEDED = "Intro line\nColumn A\n|---|---|\n\nAfter merged.\n\nMiddle para.\n\n$$\nx\n$$\n\nLast one.\n";

test("the seeded shape: a header-looking line over a mismatched delimiter row and a display formula below join the two paragraphs, and every block maps", () => {
  // the lexer's join is what this test is about: the tokens say so, or the shape has changed
  const toks = nonSpace(SEEDED);
  assert.deepEqual(toks.map((t) => [t.type, t.raw]), [["paragraph", "Intro line\n\nColumn A\n|---|---|"], ["paragraph", "After merged."], ["paragraph", "Middle para."], ["mathBlock", "$$\nx\n$$\n\n"], ["paragraph", "Last one.\n"]], "marked 12 joins the resumed paragraph with a doubled newline in raw");
  assert.equal((toks[0] as { text: string }).text, "Intro line\nColumn A\n|---|---|", "the joined text is the source's text");
  const { spans } = checkSpans(SEEDED, "seeded");
  assert.deepEqual(spans, [{ start: 0, end: 29 }, { start: 31, end: 44 }, { start: 46, end: 58 }, { start: 60, end: 67 }, { start: 69, end: 78 }]);
  const box = checkPairing(SEEDED, "seeded");
  for (const s of ["Intro line", "Column A", "After merged.", "Middle para.", "Last one."]) mapsAt(box, SEEDED, s);
  // across the join: one paragraph, its source text between
  const r = ok(mapRenderedSelection(sel(point(box, "Intro"), point(box, "Column A", true)), El(box), SEEDED), "across the join");
  assert.equal(r.quote, "Intro line\nColumn A");
  // the same shape with a callout below in place of the formula: the callout registers no start hint (round 3 dropped
  // it, its line being a paragraph interrupt already; round 2's hint joined here alike), so the lines stay two paragraphs
  const CALLOUT = SEEDED.replace("$$\nx\n$$", "> [!note] Title\n> Callout body.");
  assert.deepEqual(nonSpace(CALLOUT).slice(0, 2).map((t) => t.raw), ["Intro line\n", "Column A\n|---|---|"], "a callout below is no hint: no join");
  checkSpans(CALLOUT, "callout");
  const cb = checkPairing(CALLOUT, "callout");
  for (const s of ["Intro line", "Column A", "After merged.", "Callout body.", "Last one."]) mapsAt(cb, CALLOUT, s);
  // and without any later hint the same lines are two paragraphs, as before
  const NONE = SEEDED.replace("$$\nx\n$$\n\n", "");
  assert.deepEqual(nonSpace(NONE).slice(0, 2).map((t) => t.raw), ["Intro line\n", "Column A\n|---|---|"]);
  checkSpans(NONE, "no hint");
});

test("every trigger shape joins and maps: the table's two cell-count mismatches, a lowercase html-looking line, a bare bullet, several joins in one paragraph, a definition after a join; the controls never joined, a callout below among them", () => {
  const HINTS: Array<[string, string]> = [["$$", "$$\nx\n$$"]];   // the grammar's one block hint (the callout's went in round 3)
  const TRIGGERS: Array<[string, string, string[]]> = [
    ["1 header cell over 2 delimiter cells", "Intro line\nColumn A\n|---|---|", ["Intro line", "Column A"]],
    ["2 header cells over 1 delimiter cell", "Lead in\nHead | Two\n|---|", ["Lead in", "Head | Two"]],
    ["<prefix>", "Run the tool with\n<prefix>/bin/tool\nand check the output.", ["Run the tool with", "/bin/tool", "and check the output."]],
    ["<preview>", "Run it\n<preview>\nthen check.", ["Run it", "then check."]],
    ["<scripts/>", "Says\n<scripts/>\nand more.", ["Says", "and more."]],
    ["* bullet", "Para line\n* \nMore text.", ["Para line", "More text."]],
    ["1. bullet", "Para line\n1. \nMore text.", ["Para line", "More text."]],
    ["two joins", "A line\n<prefix>\nB line\n<prefix>\nC line", ["A line", "B line", "C line"]],
    ["a definition after the join", "A line\n<prefix>\nB line\n[foo]: /url", ["A line", "B line", "[foo]: /url"]],
  ];
  for (const [hn, hint] of HINTS) for (const [tn, trigger, needles] of TRIGGERS) {
    const src = trigger + "\n\nAfter merged.\n\n" + hint + "\n\nLast one.\n";
    const why = tn + " + " + hn;
    const first = nonSpace(src)[0];
    assert.equal(first.type, "paragraph", why);
    assert.ok(first.raw.includes("\n\n"), why + ": the shape joins (raw " + JSON.stringify(first.raw) + ")");
    checkSpans(src, why);
    const box = checkPairing(src, why);
    for (const n of needles) mapsAt(box, src, n);
    mapsAt(box, src, "After merged.");
    mapsAt(box, src, "Last one.");
  }
  // controls: an uppercase tag, a real html block, a real list item, a `- ` line (a setext underline), a real table; none joins,
  // every one tiles and maps as before
  for (const [cn, control] of [["<PREFIX>", "A line\n<PREFIX>\nB line"], ["a real <pre> block", "A line\n<pre>\nB\n</pre>"], ["a real list", "A line\n* item\nB line"], ["a setext underline", "A line\n- \nB line"], ["a real table", "Intro\n| a | b |\n|---|---|\n| 1 | 2 |"]] as Array<[string, string]>) {
    const src = control + "\n\nAfter.\n\n$$\nx\n$$\n\nLast one.\n";
    assert.ok(!nonSpace(src).some((t) => t.type === "paragraph" && t.raw.includes("\n\n")), cn + ": no join");
    checkSpans(src, cn);
    const box = checkPairing(src, cn);
    mapsAt(box, src, "After.");
    mapsAt(box, src, "Last one.");
  }
  // one more control, every trigger with a callout below in place of the formula: the callout registers no start hint
  // (round 3), so marked's clip flag is never set, the trigger's lines stay two paragraphs, and every line maps
  for (const [tn, trigger, needles] of TRIGGERS) {
    const src = trigger + "\n\nAfter merged.\n\n> [!note] Title\n> Callout body.\n\nLast one.\n";
    const why = tn + " + a callout below";
    assert.ok(!nonSpace(src).some((t) => t.type === "paragraph" && t.raw.includes("\n\n")), why + ": no join (a callout is no hint)");
    checkSpans(src, why);
    const box = checkPairing(src, why);
    for (const n of needles) mapsAt(box, src, n);
    mapsAt(box, src, "Callout body.");
    mapsAt(box, src, "Last one.");
  }
});

test("the code join: a paragraph, an indented line (four spaces, a tab, five spaces, two of them) and a delimiter-row-shaped line or a rule join with no hint and under one, and every line maps to its own characters", () => {
  // marked's `code` tokenizer runs before the table's, so the cell count is beside the point (a matching count joins too)
  const CODE_JOINS: Array<[string, string, string[]]> = [
    ["four spaces over a two-cell delimiter row", "Intro line\n    Column A\n|---|---|", ["Intro line", "Column A", "|---|---|"]],
    ["a tab over the row", "Intro line\n\tColumn A\n|---|---|", ["Intro line", "Column A", "|---|---|"]],
    ["the matching cell count", "Results:\n    metric | value\n|---|---|", ["Results:", "metric | value"]],
    ["five spaces, one of which stays in the text", "Intro\n     Column A\n|---|", ["Intro", "Column A"]],
    ["an indented continuation line before the joined one", "Intro\n    a line\n    b line\n|---|", ["Intro", "a line", "b line"]],
    ["a rule under the indented line", "Some prose\n    an afterthought\n---", ["Some prose", "an afterthought"]],
    ["a heading after the row", "Some prose\n\ta | b\n|---|\n\n# Heading", ["Some prose", "a | b", "Heading"]],
  ];
  for (const [tn, trigger, needles] of CODE_JOINS) for (const [hn, tail] of [["no hint", ""], ["a formula below", "$$\nx\n$$\n\n"]]) {
    const src = trigger + "\n\nAfter merged.\n\n" + tail + "Last one.\n";
    const why = tn + ", " + hn;
    // the lexer's join is what this test is about: the first token's raw holds a doubled newline and its text lost the indentation
    const first = nonSpace(src)[0] as { type: string; raw: string; text: string };
    assert.equal(first.type, "paragraph", why);
    assert.ok(first.raw.includes("\n\n"), why + ": the shape joins (raw " + JSON.stringify(first.raw) + ")");
    assert.notEqual(trimNL(first.raw.replace(/\n\n/g, "\n")), trimNL(first.text), why + ": the text lost the indentation, so the raw less the joins' newlines is not the text (raw " + JSON.stringify(first.raw) + ", text " + JSON.stringify(first.text) + ")");
    checkSpans(src, why);
    const box = checkPairing(src, why);
    for (const n of needles) mapsAt(box, src, n);
    mapsAt(box, src, "After merged.");
    mapsAt(box, src, "Last one.");
    // across the join: one paragraph, the source's text between, indentation included
    const r = ok(mapRenderedSelection(sel(point(box, needles[0]), point(box, needles[1], true)), El(box), src), why + ": across the join");
    assert.equal(r.quote, src.slice(src.indexOf(needles[0]), src.indexOf(needles[1]) + needles[1].length), why + ": the quote is the source between");
  }
  // the same join inside a quote's body, a callout's body and a list item's block text (the `text` token's join), and a tight
  // list item whose second line is indented four columns past the content: every line maps to its own characters
  const NESTED: Array<[string, string, string[]]> = [
    ["a quote", "> Intro line\n>     Column A\n> |---|---|\n\nAfter.\n", ["Intro line", "Column A", "|---|---|", "After."]],
    ["a callout", "> [!note] T\n> Intro line\n>     Column A\n> |---|---|\n\nAfter.\n", ["Intro line", "Column A", "|---|---|", "After."]],
    ["a list item", "- Intro line\n      Column A\n  |---|---|\n\nAfter.\n", ["Intro line", "Column A", "|---|---|", "After."]],
    ["a tight list item with an indented second line", "- a line\n      indented line\n- b line\n\nAfter.\n", ["a line", "indented line", "b line", "After."]],
  ];
  for (const [nn, src, needles] of NESTED) {
    const outer = nonSpace(src)[0] as { type: string; tokens?: Token[]; items?: Array<{ tokens: Token[] }> };
    const inner = (outer.items ? outer.items[0].tokens : outer.tokens!).filter((t) => t.type !== "space")[0] as { raw: string; text: string };
    assert.ok(inner.raw.includes("\n\n    ") && !inner.text.includes("    "), nn + ": the join inside (raw " + JSON.stringify(inner.raw) + ")");
    checkSpans(src, nn);
    const box = checkPairing(src, nn);
    for (const n of needles) mapsAt(box, src, n);
  }
  // controls: an indented line that nothing delimiter-shaped follows is the paragraph's own continuation (no join), and a
  // line indented three spaces before the row is the next paragraph's first line, prose the table interrupt reads as a
  // header and the code tokenizer does not take (no join; that block begins with spaces no element shows, so checkPairing's
  // whole-element check is not for it, and each line is mapped on its own)
  for (const [cn, control, pairing] of [["an indented continuation", "Intro line\n    Column A\nplain line", true], ["three spaces", "Intro line\n   Column A\n|---|---|", false]] as Array<[string, string, boolean]>) {
    const src = control + "\n\nAfter.\n";
    const first = nonSpace(src)[0];
    assert.ok(!first.raw.includes("\n\n"), cn + ": no join (raw " + JSON.stringify(first.raw) + ")");
    checkSpans(src, cn);
    const box = pairing ? checkPairing(src, cn) : buildRendered(src);
    for (const n of ["Intro line", "Column A", "After."]) mapsAt(box, src, n);
  }
});

test("the same join inside a callout's body and a blockquote's body maps the lines inside, and the blocks around", () => {
  const CALLOUT = "Before para.\n\n> [!note] T\n> Intro\n> Column A\n> |---|---|\n> After inside\n> $$\n> x\n> $$\n\nOutside para.\n";
  const inner = (nonSpace(CALLOUT)[1] as { tokens: Token[] }).tokens.filter((t) => t.type !== "space");
  assert.equal(inner[0].raw, "Intro\n\nColumn A\n|---|---|\nAfter inside\n", "the join inside the callout's body");
  checkSpans(CALLOUT, "nested callout");
  const box = checkPairing(CALLOUT, "nested callout");
  for (const s of ["Before para.", "Intro", "Column A", "After inside", "Outside para."]) mapsAt(box, CALLOUT, s);
  const QUOTE = "Before.\n\n> A line\n> <prefix>\n> B line\n>\n> $$\n> x\n> $$\n\nOutside.\n";
  const qi = (nonSpace(QUOTE)[1] as { tokens: Token[] }).tokens.filter((t) => t.type !== "space");
  assert.equal(qi[0].raw, "A line\n\n<prefix>\nB line", "the join inside the quote's body");
  checkSpans(QUOTE, "nested quote");
  const qb = checkPairing(QUOTE, "nested quote");
  for (const s of ["Before.", "A line", "B line", "Outside."]) mapsAt(qb, QUOTE, s);
  // a join inside a quote whose hint stands OUTSIDE it: the quote's body is its own frame, so no join there, and the top level maps
  const OUTER = "Before.\n\n> A line\n> <prefix>\n> B line\n\n$$\nx\n$$\n\nOutside.\n";
  checkSpans(OUTER, "hint outside the quote");
  const ob = checkPairing(OUTER, "hint outside the quote");
  for (const s of ["A line", "B line", "Outside."]) mapsAt(ob, OUTER, s);
});

test("a fuzz of the join: notes of the trigger shapes, the hints, plain prose and other blocks in every order, single newlines between them too", () => {
  let seed = 0x5eed;
  const rnd = (): number => { seed |= 0; seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const pick = <T>(xs: T[]): T => xs[Math.floor(rnd() * xs.length)];
  const PROSE = ["Plain paragraph one.", "Another line of prose here.", "Third prose piece with `code` and *em* inside it.", "Two lines\nof prose."];
  const TRIGGERS = ["Intro line\nColumn A\n|---|---|", "Lead in\nHead | Two\n|---|", "Run the tool with\n<prefix>/bin/tool\nand check the output.", "Run it\n<preview>\nthen check.", "Para line\n* \nMore text.", "Para line\n1. \nMore text.", "Says\n<scripts/>\nand more.",
    "Indented next\n    Column A\n|---|---|", "Tabbed next\n\tCol | Two\n|---|", "Indented then a rule\n    an afterthought\n---"];   // the code join's shapes (round 5): they join with no hint
  const HINTS = ["$$\nx = 1\n$$"];   // the one block hint; a callout (below, under OTHER) registers none since round 3 and never joins
  const OTHER = ["# Heading", "> plain quote\n> second line", "- item one\n- item two", "```\ncode\n```", "| a | b |\n|---|---|\n| 1 | 2 |", "Inline $x^2$ math here.", "<PREFIX>\nkept as prose", "<pre>\nblock\n</pre>", "* item\nlazy line", "---", "Quoted trigger:\n\n> Intro\n> Column A\n> |---|---|\n> After inside\n> $$\n> y\n> $$", "> [!note] Title\n> A callout body.", "> [!tip]- Folded\n> Hidden text.",
    "> Quoted indent\n>     Column A\n> |---|---|", "- Listed indent\n      Column A\n  |---|---|", "    an indented code block"];   // the code join nested (round 5), and a real indented code block
  let joined = 0, notes = 0;
  const JOIN_FLOOR = 1000;   // the seed is fixed, so the count is: 1,386 of 2,500 with the code join's three shapes among the triggers (round 5; 826 before them, round 3, with the callout shapes as controls; 308 when they were hints)
  for (let n = 0; n < 2500; n++) {
    const k = 2 + Math.floor(rnd() * 6);
    let src = "";
    for (let i = 0; i < k; i++) {
      const r = rnd();
      const piece = r < 0.35 ? pick(TRIGGERS) : r < 0.55 ? pick(HINTS) : r < 0.75 ? pick(PROSE) : pick(OTHER);
      src += piece + (i < k - 1 ? (rnd() < 0.15 ? "\n" : "\n\n") : rnd() < 0.5 ? "\n" : "");
    }
    const why = "note " + n + " " + JSON.stringify(src);
    const { joins } = checkSpans(src, why);
    if (joins) joined++;
    notes++;
    if (n % 5 === 0) checkPairing(src, why);   // the walk and the pairing over the stand-in, one note in five
  }
  assert.ok(joined > JOIN_FLOOR, `the fuzz exercised the join: ${joined} of ${notes} notes joined`);
});
