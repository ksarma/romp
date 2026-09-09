// The anchor map over the Slice 4 constructs (plans/markdown-viewer.md: front matter, footnotes, callouts, ==mark==,
// wikilinks and embeds, and math in every bundle), driven behaviourally over the viewer's Rendered shape rebuilt as
// anchor-map.test.ts rebuilds it (marked's output parsed into the DOM stand-in; the one configuration applied through
// md-config.ts, as the viewer applies it) with the fill's result stood in for: KaTeX replaces a placeholder with a
// `.katex` root after the sanitize (math.ts), and the stand-in does the same, so the walk meets the element it meets in
// the browser. The acceptance: a paragraph after front matter and after a footnote definition maps to its source
// offset; here every paragraph after every construct maps to the offset `indexOf` finds, a selection inside a callout's
// body, a footnote definition's text, a mark and a wikilink's shown text maps to its own characters, a paragraph with
// inline math maps around the formula, and the text the viewer adds (a footnote's number, a callout's title, the front
// matter's YAML) refuses with a reason in the person's terms. The browser leg (md-config-obsidian-browser.test.ts)
// runs the same map over the real Files bundle. Fixture: anchor-map-fixtures/obsidian.md, synthetic.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex, renderedBlockElements, paintRendered, type SelLike, type MapResult } from "./anchor-map";

applyMdConfig();
const FIX = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map-fixtures", "obsidian.md"), "utf8");

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
  replaceChild(n: FakeNode, old: FakeNode): FakeNode { this.insertBefore(n, old); this.removeChild(old); return old; }
}
class FakeDocument {
  createElement(tag: string): FakeElement { return new FakeElement(this, tag.toUpperCase()); }
  createTextNode(s: string): FakeText { return new FakeText(this, s); }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
    return e in NAMED ? NAMED[e] : m;
  });
}
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
/** What the fill leaves where a placeholder stood (math.ts renderMathPlaceholders): katex.render fills the placeholder with a
 *  `.katex` root (inside a `.katex-display` span in display mode) whose text is the formula's glyphs, and unwraps it. */
function standInFill(root: FakeElement): void {
  const walk = (n: FakeNode) => {
    for (const c of n.childNodes.slice()) {
      if (c.nodeType !== 1) continue;
      const el = c as FakeElement;
      const cls = el.getAttribute("class") || "";
      if (cls === "md-math-inline" || cls === "md-math-display") {
        const doc = el.ownerDocument;
        const katex = doc.createElement("span"); katex.setAttribute("class", "katex");
        katex.appendChild(doc.createTextNode(el.textContent.replace(/[\\^_{}]/g, "")));   // glyphs, not TeX
        let repl: FakeElement = katex;
        if (cls === "md-math-display") { repl = doc.createElement("span"); repl.setAttribute("class", "katex-display"); repl.appendChild(katex); }
        (n as FakeElement).replaceChild(repl, el);
      } else walk(el);
    }
  };
  walk(root);
}
/** `.fileview-md > marked output`, the fill stood in for. */
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
const bad = (r: MapResult, msg: string) => { assert.equal(r.ok, false, msg); return r as Extract<MapResult, { ok: false }>; };
/** Select `text` (one occurrence in the rendered box) and map it. */
function mapText(box: FakeElement, text: string, k = 0): MapResult {
  return mapRenderedSelection(sel(point(box, text, false, k), point(box, text, true, k)), El(box), FIX);
}
const at = (s: string, from = 0): number => { const i = FIX.indexOf(s, from); assert.ok(i >= 0, "in the fixture: " + s); return i; };

test("the fixture holds every construct, and the block table pairs one block to one element for each of them", () => {
  for (const re of [/^---\n/, /\[\^1\]/, /^\[\^1\]: /m, /^\[\^2\]: https:/m, /==marked text==/, /^> \[!note\] Title/m, /^> \[!NOTE\]/m, /^> \[!tip\]- /m, /\[\[Note\|alias\]\]/, /!\[\[image\.png\]\]/, /\$x\^2\$/, /^\$\$$/m]) assert.match(FIX, re);
  const spans = sourceBlockSpans(FIX);
  assert.deepEqual(spans[0], { start: 0, end: at("---", 4) + 3 }, "the front matter is ONE block from offset 0 to its closing rule (the hr and the setext h2 it lexed as before are gone)");
  const box = buildRendered(FIX);
  const kids = box.childNodes.filter((n) => n.nodeType === 1) as FakeElement[];
  const tags = kids.map((k) => k.tagName + (k.getAttribute("class") ? "." + (k.getAttribute("class") as string).split(" ")[0] : ""));
  assert.deepEqual(tags, ["DETAILS.md-frontmatter", "P", "H1", "P", "DIV.md-footnote", "P", "DIV.md-footnote", "P", "BLOCKQUOTE.md-callout", "P", "BLOCKQUOTE.md-callout", "DETAILS.md-callout", "P", "P", "P", "P", "SPAN.katex-display", "P", "H2", "P", "P"]);
  // every top-level element is its own block, in order: the 1:1 pairing the in-place shapes were chosen for
  const owners = kids.map((k) => renderedBlockIndex(El(box), FIX, k as unknown as Node));
  assert.deepEqual(owners, kids.map((_, i) => i), "element i is block i");
  assert.equal(spans.length, kids.length, "as many blocks as elements");
  for (let i = 0; i < kids.length; i++) assert.deepEqual(renderedBlockElements(El(box), FIX, i), [kids[i]], "block " + i + " renders as element " + i);
  // the display formula's block is the $$ paragraph; the paragraph after it is the next block, at its own offset
  assert.equal(FIX.slice(spans[16].start, spans[16].end), "$$\n\\sum_i i\n$$");
  assert.equal(spans[17].start, at("Para after display math."));
});

test("a paragraph after front matter, after each footnote definition, after each callout, after the embeds and after display math maps to its indexOf offset", () => {
  const box = buildRendered(FIX);
  for (const para of ["Para after front matter.", "Para after footnote def.", "Para after url-only footnote def.", "Para after callout.", "Para after folded callout.", "Para after display math.", "Last para."]) {
    const piece = para.split(" ").slice(0, 3).join(" ");   // three words name one paragraph ("Para after f" opens two of them) and end on a letter, not a space the mapper would trim
    const r = ok(mapText(box, piece), para);
    assert.deepEqual(r.range, { start: at(para), end: at(para) + piece.length }, para);
    assert.equal(r.quote, piece);
    // the whole paragraph too
    const w = ok(mapText(box, para), para + " (whole)");
    assert.deepEqual(w.range, { start: at(para), end: at(para) + para.length });
  }
  // a selection spanning the first two paragraphs after the front matter keeps the blank line and the heading's marker between them
  const r = ok(mapRenderedSelection(sel(point(box, "Para after front"), point(box, "Heading One", true)), El(box), FIX), "across the heading");
  assert.equal(r.quote, FIX.slice(at("Para after front matter."), at("# Heading One") + "# Heading One".length));
});

test("a callout's body, a folded callout's hidden body and a footnote definition's own text map to their characters inside the marker lines", () => {
  const box = buildRendered(FIX);
  const body = ok(mapText(box, "Callout body line."), "callout body");
  assert.deepEqual(body.range, { start: at("Callout body line."), end: at("Callout body line.") + "Callout body line.".length });
  const gh = ok(mapText(box, "GitHub alert body."), "alert body");
  assert.equal(gh.quote, "GitHub alert body.");
  const hidden = ok(mapText(box, "Hidden body."), "a folded callout's body (the details' text is in the DOM open or closed)");
  assert.deepEqual(hidden.range, { start: at("Hidden body."), end: at("Hidden body.") + "Hidden body.".length });
  const def = ok(mapText(box, "The footnote definition text."), "the definition's text, past its `[^1]: ` marker");
  assert.deepEqual(def.range, { start: at("The footnote definition text."), end: at("The footnote definition text.") + "The footnote definition text.".length });
  const url = ok(mapText(box, "https://example.test/def-only"), "the URL-only definition's link text");
  assert.equal(url.range.start, at("https://example.test/def-only"));
  // painting a definition's range wraps its text and nothing of the back link
  const fresh = buildRendered(FIX);
  const marks = paintRendered(El(fresh), FIX, def.range, "fc-hl") as unknown as FakeElement[];
  assert.equal(marks.map((m) => m.textContent).join(""), "The footnote definition text.");
});

test("a ==mark== maps by its delimiters, a wikilink's shown text maps at its own offset (the alias, the target, the fragment form), an image embed has no text", () => {
  const box = buildRendered(FIX);
  const m = ok(mapText(box, "marked text"), "mark");
  assert.deepEqual(m.range, { start: at("marked text"), end: at("marked text") + "marked text".length });
  const struck = ok(mapText(box, "struck"), "del beside it");
  assert.equal(struck.range.start, at("struck"));
  const alias = ok(mapText(box, "alias"), "the alias of [[Note|alias]]");
  assert.deepEqual(alias.range, { start: at("|alias") + 1, end: at("|alias") + 6 });
  const heading = ok(mapText(box, "Note#Heading"), "[[Note#Heading]] shows its inner text");
  assert.equal(heading.range.start, at("[[Note#Heading]]") + 2);
  const frag = ok(mapText(box, "#Heading Two"), "[[#Heading Two]]");
  assert.equal(frag.range.start, at("[[#Heading Two]]") + 2);
  const img = ok(mapText(box, "img.png"), "[[img.png]]");
  assert.equal(img.range.start, at("[[img.png]]") + 2);
  // the embeds' paragraph: `![[image.png]]` renders no text (an <img> once resolved; here the dead span, whose text the
  // walk places at the same offset), and a selection over the whole line quotes the source line
  const wiki = ok(mapRenderedSelection(sel(point(box, "Wiki "), point(box, "img.png", true)), El(box), FIX), "the whole wikilink line");
  assert.equal(wiki.quote, FIX.slice(at("Wiki [[Note]]"), at("[[img.png]]") + "[[img.png".length));
});

test("a paragraph with inline math maps AROUND the formula: the .katex root is skipped and the mathInline token is a zero-text hole, so a selection across it quotes the TeX between", () => {
  const box = buildRendered(FIX);
  const p = box.childNodes.filter((n) => n.nodeType === 1)[15] as FakeElement;
  assert.equal(p.tagName, "P"); assert.ok(p.textContent.startsWith("Inline "), p.textContent);
  assert.ok(allText(p).some((t) => (t.parentNode as FakeElement).getAttribute("class") === "katex"), "the stand-in fill put a .katex root where the placeholder stood");
  const across = ok(mapRenderedSelection(sel(point(box, "Inline "), point(box, "math and", true)), El(box), FIX), "across the formula");
  assert.equal(across.quote, "Inline $x^2$ math and");
  assert.deepEqual(across.range, { start: at("Inline $x^2$"), end: at("math and display:") + "math and".length });
  const before = ok(mapText(box, "Inline"), "before the formula");
  assert.equal(before.range.start, at("Inline $x^2$"));
  const after = ok(mapText(box, "math and display:"), "after the formula");
  assert.equal(after.range.start, at("math and display:"));
});

test("the text the viewer adds refuses with a reason in the person's terms: a footnote's number, a callout's title, the front matter's YAML; a selection over a number and the words around it names the reference", () => {
  const box = buildRendered(FIX);
  const num = bad(mapRenderedSelection(sel(point(box, "footnote ref"), point(box, " here", true)), El(box), FIX), "over the reference's number");
  assert.match(num.reason, /a footnote reference/);
  assert.doesNotMatch(num.reason, /footnoteRef|token/, "no token name");
  const title = bad(mapText(box, "Title"), "the callout's title line");
  assert.match(title.reason, /a callout's title/);
  const generated = bad(mapText(box, "Note", 1), "the generated title of the GitHub alert (the second rendered 'Note': the first is the front matter's 'Test Note')");
  assert.match(generated.reason, /a callout's title/);
  const yaml = bad(mapText(box, "title: Test Note"), "the front matter's YAML");
  assert.match(yaml.reason, /the front matter/);
  // a selection from the YAML into the first paragraph refuses too (it touches the hole), and one wholly after it maps
  bad(mapRenderedSelection(sel(point(box, "tags: [a, b]"), point(box, "Para after front", true)), El(box), FIX), "from the YAML into the prose");
});

test("a note without front matter but with an hr at its top is unchanged: the hr and a setext heading lex as before, and the paragraph after them maps", () => {
  const src = "---\nA line\n\nPara after rule.\n";
  const box = buildRendered(src);
  assert.doesNotMatch(marked.parse(src) as string, /md-frontmatter/, "no closing rule: not front matter");
  const r = ok(mapRenderedSelection(sel(point(box, "Para after"), point(box, "rule.", true)), El(box), src), "after an hr and a paragraph");
  assert.deepEqual(r.range, { start: src.indexOf("Para after rule."), end: src.indexOf("Para after rule.") + "Para after rule.".length });
});
