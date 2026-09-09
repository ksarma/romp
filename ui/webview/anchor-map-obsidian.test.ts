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
