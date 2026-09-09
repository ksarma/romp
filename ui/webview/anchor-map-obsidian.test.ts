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
import { Lexer, marked } from "marked";
import { applyMdConfig, resolveWikilink } from "./md-config";
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
 *  `.katex` root (inside a `.katex-display` span in display mode) whose text is the formula's glyphs, and unwraps it. The two
 *  shapes the fill falls back to are stood in for by a marker in the TeX: `\BROKEN` renders KaTeX's flag on TeX it could not
 *  parse (throwOnError: false), a bare `span.katex-error` holding the TeX as text with no `.katex` root around it (KaTeX's
 *  renderError, as md-config-math-map-browser.test.ts reads it off the real fill); `\HUGE` renders the fill's own belt for a
 *  formula past a bound (showSource): `code.md-math-src` holding the TeX, inside a `pre` for a display formula, which the
 *  viewer then dresses with its Copy button (file-view.ts: the pre wears has-copy and holds a button.code-copy). */
function standInFill(root: FakeElement): void {
  const walk = (n: FakeNode) => {
    for (const c of n.childNodes.slice()) {
      if (c.nodeType !== 1) continue;
      const el = c as FakeElement;
      const cls = el.getAttribute("class") || "";
      if (cls === "md-math-inline" || cls === "md-math-display") {
        const doc = el.ownerDocument;
        const tex = el.textContent;
        let repl: FakeElement;
        if (tex.includes("\\BROKEN")) {
          repl = doc.createElement("span"); repl.setAttribute("class", "katex-error"); repl.setAttribute("title", "ParseError: KaTeX parse error: Undefined control sequence: \\BROKEN"); repl.setAttribute("style", "color:#cc0000");
          repl.appendChild(doc.createTextNode(tex));   // the TeX as text, no .katex root
        } else if (tex.includes("\\HUGE")) {
          const code = doc.createElement("code"); code.setAttribute("class", "md-math-src"); code.appendChild(doc.createTextNode(tex));
          if (el.tagName === "DIV") {
            repl = doc.createElement("pre"); repl.setAttribute("class", "has-copy"); repl.setAttribute("title", "Not rendered: 20001 characters of TeX; the limit is 20000.");
            repl.appendChild(code);
            const btn = doc.createElement("button"); btn.setAttribute("class", "code-copy"); btn.appendChild(doc.createTextNode("Copy")); repl.appendChild(btn);
          } else { repl = code; repl.setAttribute("title", "Not rendered: 20001 characters of TeX; the limit is 20000."); }
        } else {
          const katex = doc.createElement("span"); katex.setAttribute("class", "katex");
          katex.appendChild(doc.createTextNode(tex.replace(/[\\^_{}]/g, "")));   // glyphs, not TeX
          repl = katex;
          if (cls === "md-math-display") { repl = doc.createElement("span"); repl.setAttribute("class", "katex-display"); repl.appendChild(katex); }
        }
        (n as FakeElement).replaceChild(repl, el);
      } else walk(el);
    }
  };
  walk(root);
}
/** `.fileview-md > marked output`, the fill stood in for, and the file kind's wikilink stamp applied (resolveWikilink, as
 *  file-view-links.ts viewerWalkTokens applies it for a file document), so a `[[Note]]` is an anchor and `![[image.png]]`
 *  an <img>, as the Files pane renders them; the dead span, which the mapping never sees in production, shows the source
 *  with its brackets and would not match the token's shown text. */
function buildRendered(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text, { walkTokens: (t) => { resolveWikilink(t); } }) as string)) box.appendChild(n);
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
  // the embeds' paragraph: `![[image.png]]` renders no text (an <img>, stamped resolved as in the Files pane), and a
  // selection over the whole line quotes the source line
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

// ── the fill's fallback shapes (the Slice 4 review: a formula shown as its source left the TeX in the block's text) ──
const MATH_NOTE = (tex: string) => "# Title\n\nPara before the block.\n\n$$\n" + tex + "\n$$\n\nPara after the block.\n\nSecond para after.\n\nThird para after.\n";
const mapIn = (box: FakeElement, src: string, text: string) => mapRenderedSelection(sel(point(box, text), point(box, text, true)), El(box), src);
const ownersOf = (box: FakeElement, src: string) => box.childNodes.filter((n) => n.nodeType === 1).map((k) => renderedBlockIndex(El(box), src, k as unknown as Node));

test("a display formula the fill could not render (KaTeX's flag, or the source past a bound) is a block of its own like a rendered one: every block after it pairs with its element and its paragraphs map", () => {
  for (const [name, tex] of [["rendered", "\\frac{a}{b}"], ["katex-error", "\\frac{a}{b\\BROKEN"], ["md-math-src", "\\HUGE" + "x".repeat(40)]] as const) {
    const src = MATH_NOTE(tex);
    const box = buildRendered(src);
    const kids = box.childNodes.filter((n) => n.nodeType === 1) as FakeElement[];
    assert.deepEqual(kids.map((k) => k.tagName), ["H1", "P", name === "rendered" ? "SPAN" : name === "katex-error" ? "SPAN" : "PRE", "P", "P", "P"], name);
    assert.equal(sourceBlockSpans(src).length, 6, name + ": six blocks");
    assert.deepEqual(ownersOf(box, src), [0, 1, 2, 3, 4, 5], name + ": element i is block i (the formula's element, whatever shape the fill left, is the formula's block)");
    for (const para of ["Para before the block.", "Para after the block.", "Second para after.", "Third para after."]) {
      const r = ok(mapIn(box, src, para), name + ": " + para);
      assert.deepEqual(r.range, { start: src.indexOf(para), end: src.indexOf(para) + para.length }, name + ": " + para);
    }
  }
});

test("a paragraph whose inline formula fell back (KaTeX's flag, or the source past a bound) maps around it as one with a rendered formula does, and a selection across it quotes the TeX between", () => {
  for (const [name, tex] of [["rendered", "\\frac{a}{b}"], ["katex-error", "\\frac{a}{b\\BROKEN"], ["md-math-src", "\\HUGE" + "x".repeat(40)]] as const) {
    const src = "Prose before $" + tex + "$ and prose after.\n\nNext para.\n";
    const box = buildRendered(src);
    assert.deepEqual(ownersOf(box, src), [0, 1], name);
    const before = ok(mapIn(box, src, "Prose before"), name + ": before the formula");
    assert.deepEqual(before.range, { start: 0, end: "Prose before".length });
    const after = ok(mapIn(box, src, "and prose after"), name + ": after the formula");
    assert.equal(after.range.start, src.indexOf("and prose after"));
    const across = ok(mapRenderedSelection(sel(point(box, "Prose before"), point(box, "and prose", true)), El(box), src), name + ": across the formula");
    assert.equal(across.quote, "Prose before $" + tex + "$ and prose", name + ": the TeX travels inside the quote");
    ok(mapIn(box, src, "Next para."), name + ": the next paragraph");
  }
});

// ── a selection endpoint inside a control (the Slice 4 review: it was refused as reaching outside the rendered text) ──
/** The element (first match, document order) of class `cls` under root. */
function byClass(root: FakeNode, cls: string): FakeElement {
  const hit = (n: FakeNode): FakeElement | null => {
    if (n.nodeType === 1 && ((" " + ((n as FakeElement).getAttribute("class") || "") + " ").includes(" " + cls + " "))) return n as FakeElement;
    for (const c of n.childNodes) { const r = hit(c); if (r) return r; }
    return null;
  };
  const r = hit(root);
  assert.ok(r, "an element of class " + cls);
  return r as FakeElement;
}
/** The element the k-th top-level element is. */
const topEl = (box: FakeElement, k: number): FakeElement => box.childNodes.filter((n) => n.nodeType === 1)[k] as FakeElement;

test("a selection endpoint inside a formula refuses as touching a formula, with the Raw view offered at the formula's line; one at the formula's edge that selects none of it maps the prose beside it", () => {
  for (const [name, tex] of [["rendered", "x^2"], ["katex-error", "x^2\\BROKEN"], ["md-math-src", "\\HUGE" + "x".repeat(40)]] as const) {
    const src = "Inline $" + tex + "$ math and after.\n\n$$\n" + tex + "\n$$\n\nPara after display.\n";
    const box = buildRendered(src);
    const inlineFormula = byClass(topEl(box, 0), name === "rendered" ? "katex" : name);
    const displayFormula = byClass(topEl(box, 1), name === "rendered" ? "katex" : name);
    const glyphs = allText(inlineFormula)[0], dglyphs = allText(displayFormula)[0];
    assert.ok(glyphs.data.length >= 2 && dglyphs.data.length >= 2, name + ": the stand-in has text to select inside");
    // strictly inside the inline formula, out into the prose after it
    const fromInside = bad(mapRenderedSelection(sel({ node: glyphs, offset: 1 }, point(box, " math and", true)), El(box), src), name + ": from inside the formula");
    assert.match(fromInside.reason, /^This selection touches a formula; comment on it from the Raw view\.$/, name + ": " + fromInside.reason);
    assert.equal(fromInside.blockStartLine, 0, name + ": the Raw view opens at the formula's line");
    assert.equal(fromInside.blockStartOffset, src.indexOf("$"), name + ": at the formula's first character");
    // from the prose before it into the formula
    const intoIt = bad(mapRenderedSelection(sel(point(box, "Inline "), { node: glyphs, offset: 1 }), El(box), src), name + ": into the formula");
    assert.match(intoIt.reason, /touches a formula/);
    // the formula alone (its whole text): the person selected the formula
    const whole = bad(mapRenderedSelection(sel({ node: glyphs, offset: 0 }, { node: glyphs, offset: glyphs.data.length }), El(box), src), name + ": the formula alone");
    assert.match(whole.reason, /touches a formula/);
    // from the formula's first character out into the prose: the whole formula is selected, and a formula is not text the mapping places
    const fromStart = bad(mapRenderedSelection(sel({ node: glyphs, offset: 0 }, point(box, " math and", true)), El(box), src), name + ": from the formula's start");
    assert.match(fromStart.reason, /touches a formula/);
    // the edge that selects none of the formula: a selection ENDING at its first character (a triple-click on the paragraph before a display
    // formula puts its focus there) maps the prose before; one STARTING past its last character maps the prose after
    const upTo = ok(mapRenderedSelection(sel(point(box, "Inline "), { node: glyphs, offset: 0 }), El(box), src), name + ": up to the formula");
    assert.equal(upTo.quote, "Inline");
    const fromEnd = ok(mapRenderedSelection(sel({ node: glyphs, offset: glyphs.data.length }, point(box, "math and", true)), El(box), src), name + ": from the formula's end");
    assert.equal(fromEnd.quote, "math and");
    // the display formula: a triple-click on the paragraph before it ends at its first glyph and maps the paragraph; one on the formula itself
    // starts at its first glyph and ends at the next paragraph's start, and names the formula, with the Raw view offered at its `$$` line
    const paraBefore = ok(mapRenderedSelection(sel(point(box, "Inline "), { node: dglyphs, offset: 0 }), El(box), src), name + ": the paragraph before the display formula, to its first glyph");
    assert.equal(paraBefore.quote, "Inline $" + tex + "$ math and after.");
    const nextP = topEl(box, 2);
    const tripleOnFormula = bad(mapRenderedSelection(sel({ node: dglyphs, offset: 0 }, { node: nextP, offset: 0 }), El(box), src), name + ": the display formula selected whole");
    assert.match(tripleOnFormula.reason, /^This selection touches a formula; comment on it from the Raw view\.$/);
    assert.equal(tripleOnFormula.blockStartLine, 2, name + ": the `$$` line");
    assert.equal(tripleOnFormula.blockStartOffset, src.indexOf("$$"));
    // a selection across the display formula from prose to prose still maps (the hole block has no text; its source travels inside the quote)
    const acrossDisplay = ok(mapRenderedSelection(sel(point(box, "and after."), point(box, "Para after", true)), El(box), src), name + ": across the display formula");
    assert.equal(acrossDisplay.quote, src.slice(src.indexOf("and after."), src.indexOf("Para after") + "Para after".length));
  }
});

test("a selection endpoint inside another control (a footnote's back link, the front matter's fold label) sits at the control's edge: a triple-click on a footnote definition maps the definition's text", () => {
  const box = buildRendered(FIX);
  // Chromium's triple-click on `div.md-footnote` selects the line from the back link's label: anchor at the label's text, focus at the next block's start
  const def1 = topEl(box, 4), nextP = topEl(box, 5);   // the first definition and the paragraph after it (the first test pins the order)
  assert.equal(def1.getAttribute("class"), "md-footnote"); assert.equal(nextP.tagName, "P");
  const label = allText(byClass(def1, "md-fnback"))[0];
  const triple = ok(mapRenderedSelection(sel({ node: label, offset: 0 }, { node: nextP, offset: 0 }), El(box), FIX), "a triple-click on the footnote definition");
  assert.equal(triple.quote, "The footnote definition text.");
  assert.deepEqual(triple.range, { start: at("The footnote definition text."), end: at("The footnote definition text.") + "The footnote definition text.".length });
  // a drag from inside the back link's label into the definition's own words
  const fromBack = ok(mapRenderedSelection(sel({ node: label, offset: 1 }, point(box, "footnote definition", true)), El(box), FIX), "from the back link into the text");
  assert.equal(fromBack.quote, "The footnote definition");
  // the label alone selects no text of the note
  const labelOnly = bad(mapRenderedSelection(sel({ node: label, offset: 0 }, { node: label, offset: label.data.length }), El(box), FIX), "the label alone");
  assert.equal(labelOnly.reason, "Select some text to comment on.");
  // the front matter's fold label: a selection from it into the first paragraph touches the front matter (the hole block), as one from the YAML does
  const head = byClass(box, "md-frontmatter-head");
  const fromHead = bad(mapRenderedSelection(sel({ node: allText(head)[0], offset: 2 }, point(box, "Para after front", true)), El(box), FIX), "from the fold label into the prose");
  assert.match(fromHead.reason, /the front matter/);
  // nothing here says the selection reaches outside the rendered text: every endpoint was inside the rendered box
  for (const r of [triple, fromBack, labelOnly, fromHead] as MapResult[]) if (!r.ok) assert.doesNotMatch(r.reason, /reaches outside/);
});

// ── the highlight over a passage holding an inline formula (the Slice 4 review, round 2) ──
// paintRendered wrapped the text nodes either side of a formula and nothing else, so a comment on `Inline $x^2$ math and`
// showed two ringed boxes with the rendered formula bare between them, and a reader of the page could not tell whether the
// formula was part of the passage (the card's quote holds the TeX; the mapping was right). Now an inline formula whose TeX
// the range holds goes under the highlight with the words beside it, one mark per run of adjacent siblings.
/** The panel's unpaint (file-comments.ts): every child of a mark goes back in its place and the parent is normalized. */
function unpaintAll(root: FakeElement): void {
  const marks: FakeElement[] = [];
  const find = (n: FakeNode) => { for (const c of n.childNodes) if (c.nodeType === 1) { if ((c as FakeElement).tagName === "MARK") marks.push(c as FakeElement); find(c); } };
  find(root);
  for (const m of marks) {
    const p = m.parentNode as FakeElement;
    while (m.childNodes.length) p.insertBefore(m.childNodes[0], m);
    p.removeChild(m);
    for (let i = 0; i < p.childNodes.length; i++) {
      const c = p.childNodes[i];
      if (c.nodeType !== 3) continue;
      if ((c as FakeText).data === "") { p.removeChild(c); i--; continue; }
      while (i + 1 < p.childNodes.length && p.childNodes[i + 1].nodeType === 3) { (c as FakeText).data += (p.childNodes[i + 1] as FakeText).data; p.removeChild(p.childNodes[i + 1]); }
    }
  }
}
/** A node's children as `TAG.class` or `#text(data)`. */
const shape = (n: FakeNode): string[] => n.childNodes.map((c) => c.nodeType === 3 ? "#text(" + (c as FakeText).data + ")" : (c as FakeElement).tagName + "." + ((c as FakeElement).getAttribute("class") || "").split(" ")[0]);
const rangeOf = (src: string, text: string): { start: number; end: number } => { const i = src.indexOf(text); assert.ok(i >= 0, "in the source: " + text); return { start: i, end: i + text.length }; };
/** Every MARK under root, document order. */
const marksUnder = (root: FakeNode): FakeElement[] => { const out: FakeElement[] = []; const w = (n: FakeNode) => { for (const c of n.childNodes) if (c.nodeType === 1) { if ((c as FakeElement).tagName === "MARK") out.push(c as FakeElement); w(c); } }; w(root); return out; };

test("a comment across an inline formula is ONE highlight holding the formula: the text either side and the .katex root go under one mark (before: two marks with the formula bare between them), and the panel's unpaint restores the paragraph the map reads", () => {
  const box = buildRendered(FIX);
  const p = topEl(box, 15);
  assert.equal(p.tagName, "P"); assert.deepEqual(shape(p), ["#text(Inline )", "SPAN.katex", "#text( math and display:)"]);
  const range = rangeOf(FIX, "Inline $x^2$ math and");
  const marks = paintRendered(El(box), FIX, range, "fc-hl", { act: "fcopen", id: "c6" }) as unknown as FakeElement[];
  assert.equal(marks.length, 1, "one mark: " + JSON.stringify(marks.map((m) => shape(m))));
  assert.deepEqual(shape(marks[0]), ["#text(Inline )", "SPAN.katex", "#text( math and)"], "the formula is under the mark with the words beside it");
  assert.deepEqual(shape(p), ["MARK.fc-hl", "#text( display:)"], "the paragraph: the mark, then the text past the range");
  assert.deepEqual([marks[0].getAttribute("data-act"), marks[0].getAttribute("data-id")], ["fcopen", "c6"], "the panel's data rides on the mark, so a click on the formula opens the card");
  // the marks the map does not read: a selection across the formula over the painted paragraph still maps to the same range
  const painted = ok(mapRenderedSelection(sel(point(box, "Inline "), point(box, "math and", true)), El(box), FIX), "across the formula, painted");
  assert.deepEqual(painted.range, range);
  // the panel's unpaint puts the formula back beside its text nodes, and a repaint (a status refresh paints the SAME body) gives one mark again
  unpaintAll(box);
  assert.deepEqual(shape(p), ["#text(Inline )", "SPAN.katex", "#text( math and display:)"], "unpainted: the paragraph as rendered");
  const again = paintRendered(El(box), FIX, range, "fc-hl") as unknown as FakeElement[];
  assert.equal(again.length, 1); assert.deepEqual(shape(again[0]), ["#text(Inline )", "SPAN.katex", "#text( math and)"]);
});

test("the highlight holds an inline formula in each of the fill's three shapes (KaTeX's layout, its flag on TeX it could not parse, the belt's source), and one inside emphasis goes under the emphasis's own mark", () => {
  for (const [name, tex, cls] of [["rendered", "\\frac{a}{b}", "SPAN.katex"], ["katex-error", "\\frac{a}{b\\BROKEN", "SPAN.katex-error"], ["md-math-src", "\\HUGE" + "x".repeat(40), "CODE.md-math-src"]] as const) {
    const src = "Prose before $" + tex + "$ and prose after.\n\nNext para.\n";
    const box = buildRendered(src);
    const marks = paintRendered(El(box), src, rangeOf(src, "Prose before $" + tex + "$ and prose"), "fc-hl") as unknown as FakeElement[];
    assert.equal(marks.length, 1, name + ": one mark: " + JSON.stringify(marks.map((m) => shape(m))));
    assert.deepEqual(shape(marks[0]), ["#text(Prose before )", cls, "#text( and prose)"], name);
    assert.deepEqual(shape(topEl(box, 0)), ["MARK.fc-hl", "#text( after.)"], name);
  }
  // a formula inside emphasis: the run inside the <strong> takes its own mark, the formula in it
  const src = "Bold **$x$ math** and more.\n";
  const box = buildRendered(src);
  const strong = byClass(box, "katex").parentNode as FakeElement;
  assert.equal(strong.tagName, "STRONG");
  const marks = paintRendered(El(box), src, rangeOf(src, "Bold **$x$ math** and"), "fc-hl") as unknown as FakeElement[];
  assert.deepEqual(marks.map((m) => shape(m)), [["#text(Bold )"], ["SPAN.katex", "#text( math)"], ["#text( and)"]], "three runs: the paragraph's text, the emphasis's formula and text, the paragraph's text");
  assert.deepEqual(shape(strong), ["MARK.fc-hl"]);
});

test("a range made in the Raw view that starts or ends at a formula, or holds the formula alone, highlights the formula (before: the words alone, or nothing at all)", () => {
  for (const [text, want] of [["$x^2$ math and", ["SPAN.katex", "#text( math and)"]], ["Inline $x^2$", ["#text(Inline )", "SPAN.katex"]], ["$x^2$", ["SPAN.katex"]]] as const) {
    const box = buildRendered(FIX);
    const marks = paintRendered(El(box), FIX, rangeOf(FIX, text), "fc-presel") as unknown as FakeElement[] | null;
    assert.ok(marks && marks.length === 1, text + ": one mark: " + JSON.stringify(marks && marks.map((m) => shape(m))));
    assert.deepEqual(shape(marks![0]), want, text);
    assert.equal(marks![0].getAttribute("class"), "fc-presel");
  }
});

test("a range holding a formula alone reads the top-level block the formula sits under and no other: the formula-only highlight costs its own block, not the document (before: a walk of the whole root per mark)", () => {
  // The Comments panel re-paints every mark on every paint pass, so a walk of every node under the rendered root per mark
  // costs marks x nodes; main's M1 (2026-09-09) scoped wrapBetween to the blocks a mark touches, and anchor-map.test.ts pins
  // that for a text range. The formula-only path (a comment made in the Raw view on `$x^2$` alone) still read
  // highlightUnits(root): 40 such marks over a 26k-node document were 142 ms a pass against 6.9 ms for 40 text marks on the
  // same paragraphs (the Slice 4 review, round 7). The bound, as main's: childNodes is read only under the formula's block.
  const box = buildRendered(FIX);
  const blocks = box.childNodes.filter((n) => n.nodeType === 1) as FakeElement[];
  const p = topEl(box, 15);
  assert.deepEqual(shape(p), ["#text(Inline )", "SPAN.katex", "#text( math and display:)"]);
  // the index is built once per root and source (it walks everything then); a first paint on another block pays it
  const warm = paintRendered(El(box), FIX, rangeOf(FIX, "Para after display math."), "fc-hl") as unknown as FakeElement[];
  assert.equal(warm.length, 1);
  const reads = new Map<FakeElement, number>();
  for (const b of blocks) {
    const kids = b.childNodes;
    Object.defineProperty(b, "childNodes", { configurable: true, get() { reads.set(b, (reads.get(b) || 0) + 1); return kids; } });
  }
  const marks = paintRendered(El(box), FIX, rangeOf(FIX, "$x^2$"), "fc-presel") as unknown as FakeElement[];
  assert.deepEqual(marks.map((m) => shape(m)), [["SPAN.katex"]], "the formula alone is the highlight");
  const touched = blocks.filter((b) => reads.has(b));
  assert.deepEqual(touched, [p], "only the formula's block was read; read: " + touched.length + " of " + blocks.length);
});

test("a formula the range does not hold stays outside the highlight, and a display formula is never wrapped: a range across the display block marks the prose either side and no mark stands at the top level", () => {
  const box = buildRendered(FIX);
  const p = topEl(box, 15);
  const before = paintRendered(El(box), FIX, rangeOf(FIX, "Inline"), "fc-hl") as unknown as FakeElement[];
  assert.deepEqual(before.map((m) => shape(m)), [["#text(Inline)"]]);
  assert.deepEqual(shape(p), ["MARK.fc-hl", "#text( )", "SPAN.katex", "#text( math and display:)"], "the formula past the range is bare");
  unpaintAll(box);
  const after = paintRendered(El(box), FIX, rangeOf(FIX, "math and"), "fc-hl") as unknown as FakeElement[];
  assert.deepEqual(after.map((m) => shape(m)), [["#text(math and)"]]);
  assert.deepEqual(shape(p), ["#text(Inline )", "SPAN.katex", "#text( )", "MARK.fc-hl", "#text( display:)"]);
  unpaintAll(box);
  // across the display formula: prose to prose, the .katex-display block untouched (a block of its own line needs a block-level treatment, not an inline mark)
  const s = FIX.indexOf("and display:"), e = FIX.indexOf("Para after display math.") + "Para after display math.".length;
  const across = paintRendered(El(box), FIX, { start: s, end: e }, "fc-hl") as unknown as FakeElement[];
  assert.deepEqual(across.map((m) => m.textContent), ["and display:", "Para after display math."]);
  const display = topEl(box, 16);
  assert.equal(display.getAttribute("class"), "katex-display");
  assert.deepEqual(shape(display), ["SPAN.katex"], "the display formula's root keeps its .katex child, no mark between them");
  for (const m of marksUnder(box)) assert.notEqual(m.parentNode, box, "no mark is a top-level node (the block pairing reads the top-level children)");
  assert.deepEqual(box.childNodes.filter((n) => n.nodeType === 1).map((n) => (n as FakeElement).tagName).slice(15, 18), ["P", "SPAN", "P"]);
});

test("a highlight across two blocks inside a folded callout, or from a fold's body into the block after it, paints the blocks' text and never the whitespace between them: no whitespace-only mark, none directly under the details, the fold's children as rendered", () => {
  // marked's block output leaves a "\n" text node after each block inside a folded callout's details (md-config.ts: `<details><summary>
  // ..</summary><p>..</p>\n<p>..</p>\n</details>`), the same node it leaves between blocks at the top level, in a list item or in a
  // quote. skipBlockWs read the PARENT's tag from a list of block containers, and DETAILS was not on it, so wrapRuns wrapped each
  // such node as a mark of its own: an empty ringed box on a line between the blocks, 4 x 18 px in the viewer, the details 22 px
  // taller per mark and everything below moved down, on every paint pass and in the composer's pending target too; a closed fold
  // showed the box the moment it opened. On main the same markdown is a plain blockquote (in the list) and painted clean (the Slice
  // 4 review, round 8). A whitespace-only text node beside a block box renders nothing whatever its parent's tag (the browser
  // collapses it), so the rule reads the node's neighbours too: a block-level sibling on either side, and the node is skipped.
  // The rule reads tags, so an author's `<details>`, `<dl>` or `<figure>` (the same box on main) is held the same way; the test
  // after this one drives them, from the paragraph before the html block to the paragraph after (round 8 held a range across
  // their elements unpaintable, which is so for endpoints INSIDE the block, the fallback's quote holding the tags, and not for
  // a range that spans it; round 9).
  const SRC = [
    "# Title", "",
    "Intro para.", "",
    "> [!note]+ Two paragraphs", "> First body para.", ">", "> Second body para.", "",
    "Para after the open fold.", "",
    "> [!note]- Closed two", "> Closed first para.", ">", "> Closed second para.", "",
    "Para after the closed fold.", "",
    "> [!tip]+ Three blocks", "> Lead para.", ">", "> - alpha item", "> - beta item", ">", "> Tail para.", "",
    "Para after the three blocks.", "",
    "> [!note]+ Outer", "> Outer body.", ">", "> > [!note]+ Inner", "> > Inner first.", "> >", "> > Inner second.", ">", "> Outer after.", "",
    "Para after the nested fold.", "",
    "Last para.", "",
  ].join("\n");
  const span = (a: string, b: string): { start: number; end: number } => { const s = SRC.indexOf(a), e = SRC.indexOf(b, s); assert.ok(s >= 0 && e >= 0, a + " .. " + b); return { start: s, end: e + b.length }; };
  const stripWs = (s: string): string => s.replace(/\s+/g, "");
  const wsOnly = (m: FakeElement): boolean => stripWs(m.textContent) === "";
  const under = (m: FakeElement): string => { const p = m.parentNode as FakeElement; return p.tagName + "." + ((p.getAttribute("class") || "").split(" ")[0]); };
  const isTitle = (m: FakeElement): boolean => (((m.parentNode as FakeElement).getAttribute("class") || "").split(" ")).includes("md-callout-title");
  const wsKids = (f: FakeElement): number => f.childNodes.filter((c) => c.nodeType === 3 && stripWs((c as FakeText).data) === "").length;
  const cases: Array<[string, string, { start: number; end: number }, string[]]> = [
    ["two body paragraphs of an open fold", "fc-hl", span("First body para.", "Second body para."), ["First body para.", "Second body para."]],
    ["from a fold's last paragraph into the paragraph after it", "fc-hl", span("Second body para.", "Para after the open fold."), ["Second body para.", "Para after the open fold."]],
    ["two body paragraphs of a closed fold (the details' text is in the DOM shut or open)", "fc-hl", span("Closed first para.", "Closed second para."), ["Closed first para.", "Closed second para."]],
    ["the composer's pending target, the same shape", "fc-presel", span("First body para.", "Second body para."), ["First body para.", "Second body para."]],
    ["three blocks of a fold (a paragraph, a list, a paragraph) and the paragraph after", "fc-hl", span("Lead para.", "Para after the three blocks."), ["Lead para.", "alpha item", "beta item", "Tail para.", "Para after the three blocks."]],
    ["across a fold nested in a fold", "fc-hl", span("Outer body.", "Outer after."), ["Outer body.", "Inner first.", "Inner second.", "Outer after."]],
  ];
  for (const [why, cls, range, texts] of cases) {
    const box = buildRendered(SRC);
    const before = new Map<FakeElement, string[]>();
    const folds: FakeElement[] = [];
    const walk = (n: FakeNode) => { for (const c of n.childNodes) if (c.nodeType === 1) { const el = c as FakeElement; if (el.tagName === "DETAILS") { folds.push(el); before.set(el, shape(el)); } walk(el); } };
    walk(box);
    assert.equal(folds.length, 5, why + ": the five folds, the nested one among them");
    assert.ok(folds.every((f) => wsKids(f) >= 1), why + ": every fold holds whitespace-only text nodes between its blocks: " + folds.map((f) => JSON.stringify(shape(f))).join(" | "));
    const marks = paintRendered(El(box), SRC, range, cls) as unknown as FakeElement[] | null;
    assert.ok(marks && marks.length >= 2, why + ": both ends painted: " + JSON.stringify(marks && marks.map((m) => m.textContent)));
    const ws = marks!.filter(wsOnly);
    assert.deepEqual(ws.map((m) => under(m) + " " + JSON.stringify(m.textContent)), [], why + ": no whitespace-only mark");
    // a nested fold's title (its summary) is inside the range and painted with the rest, the standing rule for a hole a range covers;
    // it is left out of the block texts so this test says nothing about that rule
    assert.deepEqual(marks!.filter((m) => !isTitle(m)).map((m) => m.textContent), texts, why + ": the blocks' text, each block one mark");
    for (const m of marks!) assert.notEqual((m.parentNode as FakeElement).tagName, "DETAILS", why + ": no mark stands directly under a fold: " + under(m));
    for (const f of folds) assert.equal(wsKids(f), (before.get(f) as string[]).filter((s) => /^#text\(\s*\)$/.test(s)).length, why + ": the fold's own whitespace nodes stand where they were, none moved under a mark: " + JSON.stringify(shape(f)));
    // a repaint after the panel's unpaint gives the same marks: the whitespace nodes were never moved into a mark
    unpaintAll(box);
    for (const f of folds) assert.deepEqual(shape(f), before.get(f), why + ": unpainted, the fold as rendered");
    const again = paintRendered(El(box), SRC, range, cls) as unknown as FakeElement[];
    assert.deepEqual(again.filter((m) => !isTitle(m)).map((m) => m.textContent), texts, why + ": the same marks on a repaint");
  }
  // the control: a single paragraph inside a fold, one mark and no whitespace involved (what the fold-body legs elsewhere paint)
  const one = buildRendered(SRC);
  const single = paintRendered(El(one), SRC, span("First body para.", "First body para."), "fc-hl") as unknown as FakeElement[];
  assert.deepEqual(single.map((m) => m.textContent), ["First body para."]);
  // the rule stays a rule about whitespace BESIDE A BLOCK: a space between two inline elements inside a paragraph is the passage's
  // own text, a whitespace-only text node under the paragraph with an inline element on each side, and is painted with it
  const inl = "Some *em text* **strong text** here.\n";
  const ib = buildRendered(inl);
  assert.deepEqual(shape(topEl(ib, 0)), ["#text(Some )", "EM.", "#text( )", "STRONG.", "#text( here.)"], "the fixture: a whitespace-only text node between two inline elements");
  const im = paintRendered(El(ib), inl, { start: inl.indexOf("*em"), end: inl.indexOf("text**") + "text**".length }, "fc-hl") as unknown as FakeElement[];
  assert.deepEqual(im.map((m) => m.textContent), ["em text", " ", "strong text"], "the space between two inline elements is painted with the passage");
});

test("a highlight from the paragraph before an author's html block to the paragraph after it paints the block's text and never its whitespace: the parent's edge beside an image, the block-level tags round 8's list lacked, a double line break", () => {
  // Round 8's neighbour rule read the nearest non-whitespace sibling on either side against a hand-written list of block boxes
  // and missed three shapes, each an empty ringed box on main too (the Slice 4 review, round 9): the "\n" between an author's
  // `<figure>` or `<details>` and its `<img>`, first or last under the parent (no sibling on that side, an inline one on the
  // other), where the browser collapses a block's leading and trailing white space away; the "\n\n" beside a `<center>`, `<menu>`,
  // `<dir>`, `<search>` or `<hgroup>`, block-level tags the sanitizer keeps that the list lacked (the set is derived now:
  // md-config-paint-whitespace-browser.test.ts holds it to the sanitizer's allowlist and Chromium's computed display); and the
  // "\n" between two `<br>`s, where the white space before a break is its line's trailing space and the white space after it the
  // next line's leading space. Each range runs from the paragraph before the html block to the paragraph after: the endpoints
  // sit in prose the map places, and wrapBetween wraps every unit between them, the html block's included, so the block's own
  // nodes are painted or skipped by skipBlockWs alone. The controls: a space inside an inline element beside an image, mid-line
  // and rendered, is painted with the passage; a single break leaves no whitespace node to judge.
  const stripWs = (s: string): string => s.replace(/\s+/g, "");
  const wrap = (block: string): string => "Intro para.\n\n" + block + "\n\nAfter para.\n";
  const IMG = '<img src="a.png" alt="pic">';
  const cases: Array<[string, string, string[]]> = [
    ["a figure with an image and a caption", wrap("<figure>\n" + IMG + "\n<figcaption>Caption text</figcaption>\n</figure>"), ["Intro para.", "Caption text", "After para."]],
    ["a figure with an image alone, whitespace at both edges", wrap("<figure>\n" + IMG + "\n</figure>"), ["Intro para.", "After para."]],
    ["an open details with a summary and an image", wrap("<details open>\n<summary>Shots</summary>\n\n" + IMG + "\n\n</details>"), ["Intro para.", "Shots", "After para."]],
    ["a closed details with an image (its text is in the DOM shut or open)", wrap("<details>\n<summary>Shots</summary>\n\n" + IMG + "\n\n</details>"), ["Intro para.", "Shots", "After para."]],
    ["a center with an image alone: the tag the list lacked, as the parent", wrap("<center>\n" + IMG + "\n</center>"), ["Intro para.", "After para."]],
    ["a details whose body is a center", wrap("<details>\n<summary>Screenshots</summary>\n\n<center>alpha centred</center>\n\n</details>"), ["Intro para.", "Screenshots", "alpha centred", "After para."]],
    ["a figure whose body is a menu", wrap("<figure>\n\n<menu><li>one</li></menu>\n\n</figure>"), ["Intro para.", "one", "After para."]],
    ["a figure whose body is a dir", wrap("<figure>\n\n<dir><li>one</li></dir>\n\n</figure>"), ["Intro para.", "one", "After para."]],
    ["a details whose body is a search", wrap("<details>\n<summary>Find</summary>\n\n<search>find it</search>\n\n</details>"), ["Intro para.", "Find", "find it", "After para."]],
    ["a details whose body is an hgroup (not on CommonMark's html-block list; inside the details all the same)", wrap("<details>\n<summary>Head</summary>\n<hgroup>\n<h2>Title</h2>\n<p>Sub</p>\n</hgroup>\n</details>"), ["Intro para.", "Head", "Title", "Sub", "After para."]],
    ["a description list, round 8's shape, kept", wrap("<dl>\n<dt>Term</dt>\n<dd>Def</dd>\n</dl>"), ["Intro para.", "Term", "Def", "After para."]],
    ["a double line break in a paragraph", wrap("line one<br>\n<br>\nline three"), ["Intro para.", "line one", "\nline three", "After para."]],
    ["white space before and after a line break, beside inline elements", wrap("text *one* <br>\n**bold** tail"), ["Intro para.", "text ", "one", "bold", " tail", "After para."]],
  ];
  for (const [why, src, texts] of cases) {
    const box = buildRendered(src);
    const range = { start: src.indexOf("Intro para."), end: src.indexOf("After para.") + "After para.".length };
    const fresh = shape(box);
    const marks = paintRendered(El(box), src, range, "fc-hl") as unknown as FakeElement[] | null;
    assert.ok(marks && marks.length >= 2, why + ": both ends painted: " + JSON.stringify(marks && marks.map((m) => m.textContent)));
    const ws = marks!.filter((m) => stripWs(m.textContent) === "");
    assert.deepEqual(ws.map((m) => (m.parentNode as FakeElement).tagName + " " + JSON.stringify(m.textContent)), [], why + ": no whitespace-only mark");
    assert.deepEqual(marks!.map((m) => m.textContent), texts, why + ": the blocks' text and nothing else");
    unpaintAll(box);
    assert.deepEqual(shape(box), fresh, why + ": unpainted, the top level as rendered");
    const again = paintRendered(El(box), src, range, "fc-hl") as unknown as FakeElement[];
    assert.deepEqual(again.map((m) => m.textContent), texts, why + ": the same marks on a repaint");
  }
  // the controls
  const mid = wrap("Some text<span> " + IMG + "</span> tail.");
  const mb = buildRendered(mid);
  assert.deepEqual(shape(topEl(mb, 1)), ["#text(Some text)", "SPAN.", "#text( tail.)"], "the fixture: the space stands inside the span, beside the image");
  const mm = paintRendered(El(mb), mid, { start: mid.indexOf("Intro para."), end: mid.indexOf("After para.") + "After para.".length }, "fc-hl") as unknown as FakeElement[];
  assert.deepEqual(mm.map((m) => m.textContent), ["Intro para.", "Some text", " ", " tail.", "After para."], "a rendered space inside an inline element is painted with the passage (its parent is no block box, so the edge rule does not reach it)");
  const one = wrap("line one<br>\nline two");
  const ob = buildRendered(one);
  const om = paintRendered(El(ob), one, { start: one.indexOf("Intro para."), end: one.indexOf("After para.") + "After para.".length }, "fc-hl") as unknown as FakeElement[];
  assert.deepEqual(om.map((m) => m.textContent), ["Intro para.", "line one", "\nline two", "After para."], "a single break: the text after it is the passage's, painted");
});

test("a lazy `===` or `--` line under a callout's or a quote's body line is that paragraph's text and maps to its own characters: marked's setext guard puts four spaces before it in the token's text, and the suffix view reads through them (before: the whole block refused, with a reason naming a tab)", () => {
  // marked's blockquote tokenizer prefixes a lazy underline with four spaces so the nested lex reads a paragraph's text and not
  // a setext heading; md-config.ts's callout borrows the preparation from the body's second line on. The spaces are the guard's,
  // not the note's, so line i of the token's text is no longer a suffix of raw line i, and suffixLineView refused the block
  // (the Slice 4 review, round 3: a selection on `body text here` was sent to the Raw view over a tab that was not there).
  const mapIn = (box: FakeElement, source: string, text: string): MapResult => mapRenderedSelection(sel(point(box, text), point(box, text, true)), El(box), source);
  const cases: Array<[string, string[], string]> = [
    ["> [!note] Title\n> body text here\n===\n\nAfter para.\n", ["body text here", "===", "After para."], "a callout with a body line and a lazy ==="],
    ["> [!note] Title\n> body text here\n--\n\nAfter para.\n", ["body text here", "--", "After para."], "the -- twin"],
    ["> quote text here\n===\n\nAfter para.\n", ["quote text here", "===", "After para."], "a plain quote, the shape marked itself guards"],
    ["> [!tip]- Folded\n> hidden body\n  === \n\nAfter para.\n", ["hidden body", "===", "After para."], "a folded callout, the underline indented and with a trailing space (the guard strips up to three spaces and keeps the rest)"],
    ["> [!note] Title\n===\n\nAfter para.\n", ["===", "After para."], "the empty-body shape: the guard skips the body's first line (md-config.ts), so the text is a plain suffix"],
    ["> [!note]\n> first\n> second\n--\n===\n\nAfter para.\n", ["first", "second", "--", "===", "After para."], "two lazy underlines, each guarded"],
  ];
  for (const [src, needles, why] of cases) {
    const box = buildRendered(src);
    for (const s of needles) {
      const r = ok(mapIn(box, src, s), why + ": " + s);
      const i = src.indexOf(s);
      assert.deepEqual(r.range, { start: i, end: i + s.length }, why + ": " + s + " maps to its own offset");
      assert.equal(r.quote, s, why);
    }
    // across the body line and its underline: one paragraph, and the quote is the source's text between (no four spaces in it)
    const first = needles[0], under = needles[needles.length - 2];
    const across = ok(mapRenderedSelection(sel(point(box, first), point(box, under, true)), El(box), src), why + ": across the underline");
    assert.equal(across.quote, src.slice(src.indexOf(first), src.indexOf(under) + under.length), why + ": the source text between");
    assert.ok(!across.quote.includes("    "), why + ": the guard's spaces are not in the quote");
  }
  // the guard's spaces are one shape the view reads through; a tab after the marker is the other (round 6, blockLexView: the
  // nested lexer expands it to four spaces, and the nested walk runs over the expanded text as the top-level walk runs over N),
  // so `>\t\tcode line` is the paragraph's second line and both lines map to their own characters; round 5 pinned this shape as
  // a refusal of the whole quote (test 18 holds the class)
  const tabbed = "> quote\n>\t\tcode line\n\nAfter para.\n";
  const tb = buildRendered(tabbed);
  for (const s of ["quote", "code line", "After para."]) {
    const r = ok(mapIn(tb, tabbed, s), "a tab after the marker: " + s);
    assert.deepEqual(r.range, { start: tabbed.indexOf(s), end: tabbed.indexOf(s) + s.length }, s + " maps to its own offset");
  }
});

test("a quote closed with an empty `>` line maps: marked's blockquote tokenizer strips the marker and rtrims the newlines left, so the raw has a line more than the text; with a space or a tab after the marker, indented up to three spaces or, as a lazy line, four and more, at the end of the note, two paragraphs, nested, inside a list item", () => {
  // (the Slice 4 review, round 5: the whole quote refused with "a block whose lines the mapping could not place" and a selection on its first
  // line was sent to the Raw view, where a callout of the same shape mapped, md-config.ts keeping the trailing newlines in its text; the same
  // at the base, the round-3 suffix view being where the tail check lives)
  const mapIn = (box: FakeElement, source: string, text: string): MapResult => mapRenderedSelection(sel(point(box, text), point(box, text, true)), El(box), source);
  const closed = "> first\n>\n\nAfter para.\n";
  const t = Lexer.lex(closed)[0] as { type: string; raw: string; text: string };
  assert.deepEqual([t.type, t.raw, t.text], ["blockquote", "> first\n>\n\n", "first"], "the shape this test is about: the raw ends in the `>` line, the text does not");
  const lazy = Lexer.lex("> first\n    >\n\nAfter para.\n")[0] as { type: string; raw: string; text: string };
  assert.deepEqual([lazy.type, lazy.raw, lazy.text], ["blockquote", "> first\n    >\n\n", "first"], "the indented shape: the `>` line enters the quote as a lazy continuation and the strip (` *>`) empties it under any indentation");
  const cases: Array<[string, string[], string]> = [
    [closed, ["first", "After para."], "a bare > closing the quote"],
    ["> first\n> \n\nAfter para.\n", ["first", "After para."], "a > and a space"],
    ["> first\n>\t\n\nAfter para.\n", ["first", "After para."], "a > and a tab"],
    ["> first\n>", ["first"], "a bare > at the end of the note"],
    ["> first\n>\n=\n\nAfter para.\n", ["first", "=", "After para."], "a = line after the closing >"],
    ["> one para\n>\n> two para\n>\n\nAfter para.\n", ["one para", "two para", "After para."], "two paragraphs, a > between them and one closing"],
    ["> first\n   >\n\nAfter para.\n", ["first", "After para."], "the closing > indented three spaces"],
    ["> first\n    >\n\nAfter para.\n", ["first", "After para."], "the closing > indented four spaces (round 6: marked strips a lazy `>` line under any indentation; before, the quote refused whole where three spaces mapped)"],
    ["> first\n     >\n\nAfter para.\n", ["first", "After para."], "the closing > indented five spaces"],
    ["> first\n\t>\n\nAfter para.\n", ["first", "After para."], "the closing > after a tab (four spaces in N)"],
    ["> first\n    > \n\nAfter para.\n", ["first", "After para."], "the closing > indented four spaces, a space after it"],
    ["> first\n    >", ["first"], "the closing > indented four spaces at the end of the note"],
    ["> outer\n> > inner\n>     >\n\nAfter para.\n", ["outer", "inner", "After para."], "a nested quote closed with an indented >"],
    ["- > inner\n      >\n\nAfter para.\n", ["inner", "After para."], "a quote inside a list item closed with a > past the item's indent"],
    ["> first\n    >\n> second\n\nAfter para.\n", ["first", "second", "After para."], "an indented > in the middle (mapped before this too: the text keeps that blank line)"],
    ["> outer\n> > inner\n> >\n\nAfter para.\n", ["outer", "inner", "After para."], "a nested quote closed with > >"],
    ["- item\n\n> first\n>\n\nAfter para.\n", ["item", "first", "After para."], "after a list"],
    ["- > inner\n  >\n\nAfter para.\n", ["inner", "After para."], "a quote inside a list item"],
    ["> [!note] T\n> body text\n>\n\nAfter para.\n", ["body text", "After para."], "a callout of the same shape (mapped before this too)"],
    ["> first\n>\n> second\n\nAfter para.\n", ["first", "second", "After para."], "a bare > in the middle (mapped before this too: the text keeps that blank line)"],
  ];
  for (const [src, needles, why] of cases) {
    const box = buildRendered(src);
    for (const s of needles) {
      const r = ok(mapIn(box, src, s), why + ": " + s);
      const i = src.indexOf(s);
      assert.deepEqual(r.range, { start: i, end: i + s.length }, why + ": " + s + " maps to its own offset");
      assert.equal(r.quote, s, why);
    }
  }
  // (round 5 closed with `>\t\tcode line` refusing as the tail check's control; it refused for the tab the nested lexer expanded,
  // not for the tail, and it maps since round 6: test 18)
});

test("a tab after a quote's marker maps: the nested block lexer expands the leading tab run of every line it is handed, and the nested walk runs over that expanded text (blockLexView), so a closing `> \\t` line, a `> \\tsecond` continuation, a `>\\t\\tcode` line, a callout's body line and a list item's `- \\t` are placed; an indented code block a tab opens is a hole at the tab's position", () => {
  // (the Slice 4 review, round 6: marked's blockquote strip takes ONE whitespace after the marker, `^ *>[ \t]?`, so a second one stays
  // in the quote's text, and blockTokens expands a leading tab there to four spaces before lexing: the nested paragraph's raw was
  // `first\n    ` over a quote text of `first\n\t`, and the whole quote refused with "a paragraph the mapping could not place";
  // round 5 covered `>\t` and `> ` singly and pinned the content shape `>\t\tcode line` as a refusal naming the tab)
  const mapIn = (box: FakeElement, source: string, text: string): MapResult => mapRenderedSelection(sel(point(box, text), point(box, text, true)), El(box), source);
  const closed = "> first\n> \t\n\nAfter para.\n";
  const t = Lexer.lex(closed)[0] as unknown as { type: string; text: string; tokens: Array<{ type: string; raw: string }> };
  assert.deepEqual([t.type, t.text, t.tokens.map((x) => [x.type, x.raw])], ["blockquote", "first\n\t", [["paragraph", "first\n    "]]], "the shape this test is about: the tab stays in the quote's text and is four spaces in the nested paragraph's raw");
  const cases: Array<[string, string[], string]> = [
    [closed, ["first", "After para."], "a >, a space and a tab closing the quote"],
    ["> first\n>\t\t\n\nAfter para.\n", ["first", "After para."], "a > and two tabs"],
    ["> first\n> \t\t\n\nAfter para.\n", ["first", "After para."], "a >, a space and two tabs"],
    ["> first\n> \t", ["first"], "a >, a space and a tab at the end of the note"],
    ["> first\n> \t\n> second\n\nAfter para.\n", ["first", "second", "After para."], "the same line between two paragraphs (a space token of four spaces in the nested lex)"],
    ["> outer\n> > inner\n> > \t\n\nAfter para.\n", ["outer", "inner", "After para."], "a nested quote closed with > >, a space and a tab"],
    ["> first\n> \tsecond\n\nAfter para.\n", ["first", "second", "After para."], "a tab after the marker's space on a continuation line: one paragraph, its second line indented in the nested lex"],
    ["> quote\n>\t\tcode line\n\nAfter para.\n", ["quote", "code line", "After para."], "two tabs after the marker on a continuation line (round 5's control)"],
    ["> [!note] T\n> body text\n> \t\n\nAfter para.\n", ["body text", "After para."], "a callout closed with >, a space and a tab (the space token's raw is four spaces there too)"],
    ["> [!note] T\n> body\n> \tmore\n\nAfter para.\n", ["body", "more", "After para."], "a callout body line with a tab after the marker's space"],
    ["> first\r\n> \t\r\n\r\nAfter para.\r\n", ["first", "After para."], "CRLF line ends around the same closing line"],
  ];
  for (const [src, needles, why] of cases) {
    const box = buildRendered(src);
    for (const s of needles) {
      const r = ok(mapIn(box, src, s), why + ": " + s);
      const i = src.indexOf(s);
      assert.deepEqual(r.range, { start: i, end: i + s.length }, why + ": " + s + " maps to its own offset");
      assert.equal(r.quote, s, why);
    }
  }
  // a tab right after the marker's space on a line of its own paragraph is indented code in the nested lex: the code block is a
  // hole at the tab's position (a selection on it refuses as any code block does, in the person's terms), and the quote's other
  // paragraph and the paragraph after it map; before, the whole quote refused with a reason naming the tab
  const coded = "> first\n>\n> \tcode here\n\nAfter para.\n";
  const cb = buildRendered(coded);
  assert.match(marked.parse(coded) as string, /<blockquote>[\s\S]*<pre><code>code here/, "the lexer's reading: indented code inside the quote");
  const hole = bad(mapIn(cb, coded, "code here"), "the code block the tab opened");
  assert.match(hole.reason, /an indented code block/);
  assert.equal(hole.blockStartOffset, coded.indexOf("\t"), "the hole stands where the tab does");
  for (const s of ["first", "After para."]) assert.deepEqual(ok(mapIn(cb, coded, s), s).range, { start: coded.indexOf(s), end: coded.indexOf(s) + s.length });
  // the same in a list item: `- `, a tab and text is indented code in the item (marked's list tokenizer keeps a tab after the
  // bullet's space, and the item's nested lex expands it); the item after it and the paragraph after the list map
  const listed = "- \tcode here\n- plain item\n\nAfter para.\n";
  const lb = buildRendered(listed);
  assert.match(marked.parse(listed) as string, /<li><pre><code>code here/, "the lexer's reading: indented code inside the item");
  assert.match(bad(mapIn(lb, listed, "code here"), "the item's code block").reason, /an indented code block/);
  for (const s of ["plain item", "After para."]) assert.deepEqual(ok(mapIn(lb, listed, s), s).range, { start: listed.indexOf(s), end: listed.indexOf(s) + s.length });
});
