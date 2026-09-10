// The block pairing across an html wrapper the browser nests the following markdown into (plans/markdown-viewer.md,
// Slice 5: "pair blocks inside an unclosed HTML container (a flattened walk)", the plan's High defect; the Slice 2
// refusals (1) and (2) handed to this slice; Slice 1's merge-review finding, the text-alike html node; the Slice 4 build
// note's item 10 (d), the resync across an html block). Driven behaviourally over the viewer's Rendered shape rebuilt as
// anchor-map-obsidian.test.ts rebuilds it: marked's output under the one configuration (md-config.ts) parsed into the
// DOM stand-in, which nests the nodes after an unclosed tag inside it as a browser does, with the sanitizer's drops stood
// in for (a `<style>` goes with its text, a non-checkbox `<input>` goes, a form-associated element is unwrapped: md-sanitize.ts)
// and KaTeX's fill stood in for (a `.katex` root where a placeholder stood). Before this slice the html block that left a
// `<div align="center">` or a `<details><summary>` open took every node to the end of the document (its nested blocks'
// text occurs in no top-level node, so the resync fit at no end), every later selection was refused as "an HTML block"
// with the wrapper's offset, and the reader's place read the run as no place; a kept `<div>Go</div>` or an html `<p>Go</p>`
// before the paragraph `Go` was taken for it and every later block paired one node early. Now the tag scan over the
// block's raw (anchor-map.ts topTags) says which top-level tags the block closes and which it leaves open; a closed tag
// takes its element, an open one takes its element and splices the element's children into the pairing, and the resync
// confirms a run by two mapped blocks with text and requires a mapped block's element tag as well as its text. The
// browser leg (anchor-map-wrappers-browser.test.ts) runs the same fixtures through the real viewer and panel. Fixtures:
// anchor-map-fixtures/wrappers-*.md and blank-scenes.json, synthetic.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { marked } from "marked";
import { applyMdConfig, resolveWikilink } from "./md-config";
import { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex, renderedBlockElements, renderedBlockWrappers, paintRendered, type SelLike, type MapResult } from "./anchor-map";
import { hideEdges } from "../test-dom-shim";

applyMdConfig();
const FIXDIR = path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map-fixtures");
const read = (f: string): string => fs.readFileSync(path.join(FIXDIR, f), "utf8");
const PLAIN = read("wrappers-plain.md");
const TWO = read("wrappers-2block.md");
const OPEN = read("wrappers-unclosed.md");
const SCENES = (JSON.parse(read("blank-scenes.json")) as { scenes: Array<{ name: string; markdown: string }> }).scenes;

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser (anchor-map-obsidian.test.ts's) ──
// Nodes hide their edges at construction (hideEdges, ui/test-dom-shim.ts), so a failing assertion's dump shows a node's primitives
// and not the tree (the ratchet in ui/test-dom-shim.test.ts).
class FakeNode {
  nodeType = 0;
  parentNode: FakeNode | null = null;
  childNodes: FakeNode[] = [];
  constructor(public ownerDocument: FakeDocument) { hideEdges(this); }
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
/** marked's HTML into the stand-in, as a browser's parser reads a fragment: an unclosed tag stays open and the nodes after it
 *  nest inside it (the wrapper shape this file is about); an end tag closes down to its element; one with no open element is dropped. */
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
        let found = false;
        for (let k = stack.length - 1; k > 0; k--) { if (stack[k].tagName === name) { stack.length = k; found = true; break; } }
        if (!found && name === "P") top().appendChild(doc.createElement("p"));   // the parser mints an empty <p></p> for a stray </p>
        i = e + 1; continue;
      }
      const m = /^<([a-zA-Z][\w:-]*)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*)\s*(\/?)>/.exec(html.slice(i));
      if (!m) { top().appendChild(doc.createTextNode("<")); i++; continue; }
      const el = doc.createElement(m[1]);
      const attrRe = /([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
      let a: RegExpExecArray | null;
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], decodeEntities(a[2] ?? a[3] ?? a[4] ?? ""));
      // the parser closes an open <p> when a block-level tag starts (so marked's next block never nests in an author's `<p>`)
      if (/^(?:p|div|details|h[1-6]|ul|ol|pre|blockquote|table|hr|section|figure|summary)$/i.test(m[1]) && top().tagName === "P") stack.length--;
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
/** The sanitizer's drops, stood in for (md-sanitize.ts): a `<style>` or `<script>` goes with its text (FORBID_CONTENTS), every
 *  other forbidden tag is unwrapped with its content kept (a `<form>`, a `<button>`, a `<label>`), and an `<input>` that is not a
 *  checkbox goes (keepOnlyInertCheckboxes). */
const DROP_WITH_TEXT = new Set(["STYLE", "SCRIPT"]);
const UNWRAP = new Set(["FORM", "BUTTON", "SELECT", "OPTION", "OPTGROUP", "TEXTAREA", "FIELDSET", "LEGEND", "LABEL", "DATALIST", "OUTPUT", "METER", "PROGRESS", "DIALOG", "MAP", "AREA"]);
function standInSanitize(root: FakeElement): void {
  for (const c of root.childNodes.slice()) {
    if (c.nodeType !== 1) continue;
    const el = c as FakeElement;
    if (DROP_WITH_TEXT.has(el.tagName) || (el.tagName === "INPUT" && (el.getAttribute("type") || "").toLowerCase() !== "checkbox")) { root.removeChild(el); continue; }
    if (UNWRAP.has(el.tagName)) { for (const k of el.childNodes.slice()) root.insertBefore(k, el); root.removeChild(el); standInSanitize(root); return; }
    standInSanitize(el);
  }
}
/** What the fill leaves where a placeholder stood (math.ts renderMathPlaceholders): a `.katex` root whose text is the formula's glyphs. */
function standInFill(root: FakeElement): void {
  for (const c of root.childNodes.slice()) {
    if (c.nodeType !== 1) continue;
    const el = c as FakeElement;
    const cls = el.getAttribute("class") || "";
    if (cls === "md-math-inline" || cls === "md-math-display") {
      const doc = el.ownerDocument;
      const katex = doc.createElement("span"); katex.setAttribute("class", "katex");
      katex.appendChild(doc.createTextNode(el.textContent.replace(/[\\^_{}]/g, "")));
      let repl: FakeElement = katex;
      if (cls === "md-math-display") { repl = doc.createElement("span"); repl.setAttribute("class", "katex-display"); repl.appendChild(katex); }
      root.replaceChild(repl, el);
    } else standInFill(el);
  }
}
/** `.fileview-md > marked output`, sanitized and filled as the viewer's body is (the file kind's wikilink stamp applied as file-view-links.ts applies it). */
function buildRendered(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text, { walkTokens: (t) => { resolveWikilink(t); } }) as string)) box.appendChild(n);
  standInSanitize(box);
  standInFill(box);
  return box;
}
const El = (n: FakeNode) => n as unknown as Element;
const kidsOf = (n: FakeNode): FakeElement[] => n.childNodes.filter((c): c is FakeElement => c instanceof FakeElement);
const tagOf = (k: FakeElement): string => k.tagName + (k.getAttribute("class") ? "." + (k.getAttribute("class") as string).split(" ")[0] : "");
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
/** Select the k-th occurrence of `text` in the rendered box and map it against `src`. */
const mapText = (box: FakeElement, src: string, text: string, k = 0): MapResult => mapRenderedSelection(sel(point(box, text, false, k), point(box, text, true, k)), El(box), src);
/** The k-th occurrence of `s` in `src`, which must exist. */
const at = (src: string, s: string, k = 0): number => { let i = -1; for (let n = 0; n <= k; n++) { i = src.indexOf(s, i + 1); assert.ok(i >= 0, "in the source: " + s); } return i; };
/** A paragraph's whole text maps to its indexOf offsets. */
function mapsWhole(box: FakeElement, src: string, text: string, k = 0): void {
  const r = ok(mapText(box, src, text, k), text);
  assert.deepEqual(r.range, { start: at(src, text, k), end: at(src, text, k) + text.length }, text + ": its own offsets");
  assert.equal(r.quote, text);
}
/** The index of the block whose source starts with `head`. */
const blockAt = (src: string, head: string): number => { const b = sourceBlockSpans(src).findIndex((sp) => src.slice(sp.start, sp.end).startsWith(head)); assert.ok(b >= 0, "a block starting " + JSON.stringify(head)); return b; };
const elems = (box: FakeElement, src: string, b: number): string[] => renderedBlockElements(El(box), src, b).map((e) => tagOf(e as unknown as FakeElement) + ":" + JSON.stringify((e.textContent || "").trim().split(/\s+/).slice(0, 3).join(" ")));
const wraps = (box: FakeElement, src: string, b: number): string[] => renderedBlockWrappers(El(box), src, b).map((e) => tagOf(e as unknown as FakeElement));
const owner = (box: FakeElement, src: string, n: FakeNode): number => renderedBlockIndex(El(box), src, n as unknown as Node);
/** The first element of `tag` UNDER `root` (never the root itself) whose text holds `text`. */
const find = (root: FakeNode, tag: string, text: string): FakeElement => {
  const hit = (n: FakeNode): FakeElement | null => {
    if (n !== root && n instanceof FakeElement && n.tagName === tag && n.textContent.includes(text)) return n;
    for (const c of n.childNodes) { const h = hit(c); if (h) return h; }
    return null;
  };
  const h = hit(root); assert.ok(h, tag + " holding " + JSON.stringify(text)); return h;
};
/** A selection from the start of `from` to the end of `to` (their k-th occurrences in the rendered text), mapped against `src`. */
const mapSpan = (box: FakeElement, src: string, from: string, to: string, kf = 0, kt = 0): MapResult => mapRenderedSelection(sel(point(box, from, false, kf), point(box, to, true, kt)), El(box), src);
/** The point at the start of the last occurrence of `needle` before point `to` in the rendered text. */
function pointBefore(root: FakeNode, needle: string, to: Pt): Pt {
  const ts = allText(root);
  for (let i = ts.indexOf(to.node as FakeText); i >= 0; i--) {
    const j = ts[i].data.lastIndexOf(needle, ts[i] === to.node ? to.offset - needle.length : ts[i].data.length);
    if (j >= 0) return { node: ts[i], offset: j };
  }
  throw new Error("not in the rendered text before the end: " + JSON.stringify(needle));
}
/** A paragraph whose text spans several text nodes (inline markup inside it): selected from its first word to its last three words
 *  (which name one paragraph in these fixtures, where a first word or two does not), mapped against `src`. */
function mapPara(box: FakeElement, src: string, para: string): MapResult {
  const words = para.replace(/\*\*/g, "").split(" ");
  const end = point(box, words.slice(-3).join(" "), true);
  return mapRenderedSelection(sel(pointBefore(box, words[0], end), end), El(box), src);
}
/** The texts of the marks a paint from `from` to `to` leaves, in order. */
function painted(src: string, from: string, to: string): string[] {
  const box = buildRendered(src);
  const marks = paintRendered(El(box), src, { start: at(src, from), end: at(src, to) + to.length }, "fc-hl") as unknown as FakeElement[] | null;
  return (marks || []).map((m) => m.textContent);
}

test("the plain fixture: every paragraph after and inside a `<div align=\"center\">` and a `<details><summary>` wrapper maps to its indexOf offsets (before: the div's block took every element from itself on and each was refused as an HTML block at the div's offset); the nested paragraph's element is its own block's, the closing tag's block has no element, the wrapper's block holds the wrapper and its summary, and renderedBlockWrappers names the wrapper alone; the wrapper's own rows stay refused", () => {
  const box = buildRendered(PLAIN);
  // the fixture: the stand-in nests the markdown after each wrapper inside it, as a browser does
  assert.deepEqual(kidsOf(box).map(tagOf).slice(-4), ["DIV", "P", "DETAILS", "P"], "the div holds its paragraph, then the paragraph after, then the details, then the last paragraph");
  assert.deepEqual(kidsOf(kidsOf(box)[kidsOf(box).length - 4]).map(tagOf), ["P"]);
  assert.deepEqual(kidsOf(kidsOf(box)[kidsOf(box).length - 2]).map(tagOf), ["SUMMARY", "P"]);
  for (const para of ["Centered **bold** paragraph inside the div.", "Paragraph after the div wrapper.", "Hidden paragraph inside details.", "Paragraph after the details.", "Final paragraph here."]) {
    const r = ok(mapPara(box, PLAIN, para), para);
    assert.deepEqual(r.range, { start: at(PLAIN, para), end: at(PLAIN, para) + para.length }, para + ": its own offsets");
    assert.equal(r.quote, para);
  }
  // the block table the reader's place reads (reader-place.ts): the wrapper's block owns the wrapper (and, through the resync,
  // its summary); the nested paragraph's block owns its <p>; the closing tag's block owns nothing
  const div = blockAt(PLAIN, "<div align"), inDiv = blockAt(PLAIN, "Centered **bold**"), divEnd = blockAt(PLAIN, "</div>");
  const det = blockAt(PLAIN, "<details>"), inDet = blockAt(PLAIN, "Hidden paragraph"), detEnd = blockAt(PLAIN, "</details>");
  assert.deepEqual([elems(box, PLAIN, div), wraps(box, PLAIN, div)], [['DIV:"Centered bold paragraph"'], ["DIV"]], "the div's block: its one element, a wrapper");
  assert.deepEqual([elems(box, PLAIN, inDiv), wraps(box, PLAIN, inDiv)], [['P:"Centered bold paragraph"'], []], "the nested paragraph's block: its own <p>, no wrapper");
  assert.deepEqual([elems(box, PLAIN, divEnd), wraps(box, PLAIN, divEnd)], [[], []], "the closing tag's block: no element");
  assert.deepEqual([elems(box, PLAIN, det), wraps(box, PLAIN, det)], [['DETAILS:"Click me Hidden"', 'SUMMARY:"Click me"'], ["DETAILS"]], "the details' block: the wrapper and its summary; the wrapper alone is the wrapper");
  assert.deepEqual([elems(box, PLAIN, inDet), wraps(box, PLAIN, inDet)], [['P:"Hidden paragraph inside"'], []]);
  assert.deepEqual([elems(box, PLAIN, detEnd), wraps(box, PLAIN, detEnd)], [[], []]);
  assert.equal(owner(box, PLAIN, find(box, "P", "Centered")), inDiv, "renderedBlockIndex answers for a nested node");
  assert.equal(owner(box, PLAIN, find(box, "SUMMARY", "Click me")), det, "the summary is the wrapper's block's");
  assert.equal(owner(box, PLAIN, find(box, "P", "Paragraph after the details.")), blockAt(PLAIN, "Paragraph after the details."));
  assert.deepEqual(wraps(box, PLAIN, inDiv).concat(wraps(box, PLAIN, blockAt(PLAIN, "# Wrappers"))), [], "a block that is no wrapper's answers none");
  // the wrapper's own rows stay refused (ruling 2): the summary's text is the html block's
  const summary = bad(mapText(box, PLAIN, "Click me"), "the summary");
  assert.match(summary.reason, /an HTML block/);
  assert.equal(summary.blockStartOffset, at(PLAIN, "<details>"));
  // a selection from the paragraph before the wrapper into the nested paragraph crosses the wrapper's block, which owns a node
  // now, so it refuses as an HTML block where the swallowed run used to (recorded: a quote should not carry raw html the person
  // did not select as text; the Raw view is offered at the wrapper)
  const across = bad(mapRenderedSelection(sel(point(box, "Final paragraph"), point(box, "inside the div.", true)), El(box), PLAIN), "across the opening tag");
  assert.match(across.reason, /an HTML block/);
  assert.equal(across.blockStartOffset, at(PLAIN, "<div align"));
  // a selection from the nested paragraph into the paragraph after the closing tag maps: the `</div>` block renders nothing, so
  // its source travels inside the quote as a comment block's does (anchor-map.test.ts, an HTML block that renders none)
  const out = ok(mapRenderedSelection(sel(point(box, "inside the div."), point(box, "div wrapper.", true)), El(box), PLAIN), "across the closing tag");
  assert.equal(out.quote, "inside the div.\n\n</div>\n\nParagraph after the div wrapper.");
  // controls: the blocks before the wrappers read as ever
  assert.match(bad(mapText(box, PLAIN, "total = a"), "code").reason, /a code block/);
  assert.match(bad(mapText(box, PLAIN, "cell one"), "table").reason, /a table/);
  mapsWhole(box, PLAIN, "Text inside the folded callout.");
  mapsWhole(box, PLAIN, "Repeated line here.", 1);
  mapsWhole(box, PLAIN, "Intro paragraph one with several words in it.");
});

test("a two-block div (a heading and a paragraph nested in it) pairs each nested block to its element, and the paragraphs after the div map (before: all four selections refused as an HTML block)", () => {
  const box = buildRendered(TWO);
  const title = ok(mapText(box, TWO, "Centered Title"), "the nested heading");
  assert.deepEqual(title.range, { start: at(TWO, "Centered Title"), end: at(TWO, "Centered Title") + "Centered Title".length });
  for (const para of ["Tagline paragraph.", "After the two-block div.", "Final paragraph here."]) mapsWhole(box, TWO, para);
  const div = blockAt(TWO, "<div align");
  assert.deepEqual([elems(box, TWO, div), wraps(box, TWO, div)], [['DIV:"Centered Title Tagline"'], ["DIV"]]);
  assert.deepEqual(elems(box, TWO, blockAt(TWO, "# Centered Title")), ['H1:"Centered Title"']);
  assert.deepEqual(elems(box, TWO, blockAt(TWO, "Tagline")), ['P:"Tagline paragraph."']);
  assert.deepEqual(elems(box, TWO, blockAt(TWO, "</div>")), []);
  assert.deepEqual(elems(box, TWO, blockAt(TWO, "After the two-block")), ['P:"After the two-block"']);
});

test("a div never closed, and one closed by the document's last block: the nested paragraphs map to their offsets, the wrapper's block owns the one element, and a formula inside a nested paragraph is refused at the formula's own offset (formulaExtra reads the nested paragraph's block, not the wrapper's)", () => {
  for (const [what, src] of [["never closed", OPEN], ["closed as the last block", OPEN + "\n</div>\n"]] as const) {
    const box = buildRendered(src);
    assert.deepEqual(kidsOf(box).map(tagOf), ["H1", "P", "DIV"], what + ": the div is the last top-level element");
    assert.deepEqual(kidsOf(kidsOf(box)[2]).map(tagOf), ["P", "P", "P"], what + ": the three paragraphs nest in it");
    for (const para of ["First nested paragraph of the open div.", "Third nested paragraph closes the note."]) mapsWhole(box, src, para);
    const second = ok(mapText(box, src, "Second nested paragraph, with a formula"), what + ": the prose before the formula");
    assert.equal(second.range.start, at(src, "Second nested"));
    const around = ok(mapRenderedSelection(sel(point(box, "with a formula"), point(box, "in it.", true, 1)), El(box), src), what + ": across the formula");
    assert.equal(around.quote, "with a formula $a^2 + b^2$ in it.", what + ": the TeX travels in the quote");
    const div = blockAt(src, "<div align");
    assert.deepEqual([elems(box, src, div), wraps(box, src, div)], [['DIV:"First nested paragraph"'], ["DIV"]], what);
    assert.deepEqual(elems(box, src, blockAt(src, "Second nested")), ['P:"Second nested paragraph,"'], what);
    if (what === "closed as the last block") assert.deepEqual(elems(box, src, blockAt(src, "</div>")), [], what + ": the closing tag's block owns nothing");
    // a boundary inside the formula's glyphs: refused as touching a formula, the Raw view offered at the formula inside the
    // NESTED paragraph (before the descent formulaExtra read the top-level node's block, the wrapper's, and named the div's start)
    const glyph = point(box, "a2 + b2");   // the stand-in fill's glyphs: the TeX less its markup characters
    const touched = bad(mapRenderedSelection(sel(point(box, "with a formula"), { node: glyph.node, offset: glyph.offset + 2 }), El(box), src), what + ": into the formula");
    assert.match(touched.reason, /touches a formula/);
    assert.equal(touched.blockStartOffset, at(src, "$a^2 + b^2$"), what + ": the formula's own offset");
    // ...and preselects the nested formula with its delimiters (Slice 5, item 3: formulaExtra's rawRange is the hole's span)
    assert.equal(touched.rawHasQuote, true, what + ": the Raw view has the formula to preselect");
    assert.equal(src.slice(touched.rawRange!.start, touched.rawRange!.end), "$a^2 + b^2$", what + ": the formula with its delimiters");
  }
});

// ── Slice 5, item 4: the first obstacle in document order, over the wrappers (the slice's probe (d), d10 and d11) ──
test("the first obstacle in document order is the one named over the plain fixture: a drag from a table cell to the `Click me` summary after it, and one from the math paragraph to the summary, refuse as touching the table (the probe's d10 and d11; before: an HTML block at the details' offset, the refused block named ahead of the table's hole); from the code line past the div wrapper as the code block; from the paragraph before the div into the div's nested paragraph still as an HTML block, the wrapper's block being the first obstacle", () => {
  const box = buildRendered(PLAIN);
  const lineOf = (needle: string) => PLAIN.slice(0, PLAIN.indexOf(needle)).split("\n").length - 1;
  for (const [what, from] of [["d10, a table cell", "cell one"], ["d11, the math paragraph", "Paragraph with inline math"]] as const) {
    const r = bad(mapSpan(box, PLAIN, from, "Click me"), what + " to the summary");
    assert.match(r.reason, /^This selection touches a table; comment on it from the Raw view\.$/, what + ": the table comes first (before: an HTML block): " + r.reason);
    assert.deepEqual([r.blockStartLine, r.blockStartOffset], [lineOf("| Col A"), at(PLAIN, "| Col A")], what + ": the Raw offer is the table's");
  }
  const code = bad(mapSpan(box, PLAIN, "total = a", "Paragraph after the div"), "the code line past the div wrapper");
  assert.match(code.reason, /a code block/, "the code block comes first (before: an HTML block): " + code.reason);
  assert.equal(code.blockStartOffset, at(PLAIN, "```python"));
  const div = bad(mapSpan(box, PLAIN, "Final paragraph", "inside the div."), "the paragraph before the div into its nested paragraph");
  assert.match(div.reason, /an HTML block/, "the wrapper's block is the first obstacle, as before: " + div.reason);
  assert.equal(div.blockStartOffset, at(PLAIN, "<div align"));
  // a span ending in the table names it, one starting in the code names it, as before
  assert.match(bad(mapSpan(box, PLAIN, "Intro paragraph", "cell two"), "the intro into the table").reason, /a code block/, "the code block stands between them");
  assert.match(bad(mapSpan(box, PLAIN, "Paragraph with inline math", "cell two"), "the math paragraph into the table").reason, /a table/);
  assert.match(bad(mapSpan(box, PLAIN, "total = a", "around it."), "the code into the math paragraph").reason, /a code block/);
});

test("two html `<p>` blocks a blank line apart own one element each (before: nothing and both); a closed `<div>x</div>` stays refused with its one element; two sibling tags in one block own both; a `<style>` block the sanitizer dropped owns nothing and the paragraph after it maps; a stray `</p>` is the parser's empty `<p>`; a `<p>` the block leaves open is closed by the next block's tag and is no wrapper", () => {
  const AB = "# Report\n\nParagraph one here.\n\n<p>Alpha</p>\n\n<p>Beta</p>\n\nParagraph two here.\n";
  let box = buildRendered(AB);
  assert.deepEqual(kidsOf(box).map(tagOf), ["H1", "P", "P", "P", "P"]);
  assert.deepEqual([elems(box, AB, blockAt(AB, "<p>Alpha")), elems(box, AB, blockAt(AB, "<p>Beta"))], [['P:"Alpha"'], ['P:"Beta"']], "one element each (before: [0, 2])");
  assert.equal(owner(box, AB, kidsOf(box)[2]), blockAt(AB, "<p>Alpha"));
  assert.equal(owner(box, AB, kidsOf(box)[3]), blockAt(AB, "<p>Beta"));
  assert.match(bad(mapText(box, AB, "Beta"), "Beta").reason, /an HTML block/);
  assert.equal(bad(mapText(box, AB, "Beta"), "Beta").blockStartOffset, at(AB, "<p>Beta"), "refused at its own block");
  mapsWhole(box, AB, "Paragraph two here.");
  const CLOSED = "# Report\n\nParagraph one here.\n\n<div>x</div>\n\nParagraph two here.\n";
  box = buildRendered(CLOSED);
  assert.deepEqual([elems(box, CLOSED, blockAt(CLOSED, "<div>x")), wraps(box, CLOSED, blockAt(CLOSED, "<div>x"))], [['DIV:"x"'], []], "closed: its element, no wrapper");
  assert.match(bad(mapText(box, CLOSED, "x"), "the div's text").reason, /an HTML block/);
  mapsWhole(box, CLOSED, "Paragraph two here.");
  const TWOTAGS = "# Report\n\n<p>one</p>\n<p>two</p>\n\nParagraph two here.\n";
  box = buildRendered(TWOTAGS);
  assert.deepEqual(elems(box, TWOTAGS, blockAt(TWOTAGS, "<p>one")), ['P:"one"', 'P:"two"'], "both sibling tags");
  mapsWhole(box, TWOTAGS, "Paragraph two here.");
  const STYLE = "# Report\n\n<style>x{}</style>\n\nParagraph two here.\n";
  box = buildRendered(STYLE);
  assert.deepEqual(kidsOf(box).map(tagOf), ["H1", "P"], "the sanitizer dropped the style with its text");
  assert.deepEqual(elems(box, STYLE, blockAt(STYLE, "<style>")), [], "a dropped element owns nothing");
  mapsWhole(box, STYLE, "Paragraph two here.");
  const STRAY = "# Report\n\n</p>\n\nParagraph two here.\n";
  box = buildRendered(STRAY);
  assert.deepEqual(kidsOf(box).map(tagOf), ["H1", "P", "P"], "the parser mints an empty <p> for the stray end tag");
  assert.deepEqual(elems(box, STRAY, blockAt(STRAY, "</p>")), ['P:""'], "the html block owns the empty <p> and not the paragraph after it");
  mapsWhole(box, STRAY, "Paragraph two here.");
  const OPENP = "# Report\n\n<p align=\"center\">\n<img src=\"a.png\" alt=\"\">\n<img src=\"b.png\" alt=\"\">\n\nParagraph two here.\n\nParagraph three here.\n";
  box = buildRendered(OPENP);
  assert.deepEqual(kidsOf(box).map(tagOf), ["H1", "P", "P", "P"], "the paragraph's own <p> closed the author's");
  assert.deepEqual([elems(box, OPENP, blockAt(OPENP, "<p align")), wraps(box, OPENP, blockAt(OPENP, "<p align"))], [['P:""'], []], "the open <p>: its one element, closed by the next block, no wrapper");
  mapsWhole(box, OPENP, "Paragraph two here.");
  mapsWhole(box, OPENP, "Paragraph three here.");
});

test("a wrapper inside a wrapper: as two html blocks (each block's wrapper is its own div) and as `<div><div>` in one block (both divs are that block's wrappers); the paragraphs nested at each depth and the one after both map", () => {
  const NESTED = "Intro para.\n\n<div align=\"center\">\n\n<div class=\"inner\">\n\nInner paragraph here.\n\n</div>\n\nOuter paragraph here.\n\n</div>\n\nAfter para.\n";
  let box = buildRendered(NESTED);
  assert.deepEqual(kidsOf(box).map(tagOf), ["P", "DIV", "P"]);
  assert.deepEqual(kidsOf(kidsOf(box)[1]).map(tagOf), ["DIV.inner", "P"], "the inner div and the outer paragraph nest in the outer div");
  assert.deepEqual(kidsOf(kidsOf(kidsOf(box)[1])[0]).map(tagOf), ["P"]);
  for (const para of ["Inner paragraph here.", "Outer paragraph here.", "After para."]) mapsWhole(box, NESTED, para);
  assert.deepEqual(wraps(box, NESTED, blockAt(NESTED, "<div align")), ["DIV"]);
  assert.deepEqual(wraps(box, NESTED, blockAt(NESTED, "<div class")), ["DIV.inner"]);
  assert.deepEqual(elems(box, NESTED, blockAt(NESTED, "Inner paragraph")), ['P:"Inner paragraph here."']);
  assert.deepEqual([elems(box, NESTED, blockAt(NESTED, "</div>")), elems(box, NESTED, sourceBlockSpans(NESTED).length - 2)], [[], []], "both closing tags own nothing");
  const ONE = "Intro para.\n\n<div align=\"center\"><div class=\"inner\">\n\nInner paragraph here.\n\n</div></div>\n\nAfter para.\n";
  box = buildRendered(ONE);
  assert.deepEqual(kidsOf(box).map(tagOf), ["P", "DIV", "P"]);
  for (const para of ["Inner paragraph here.", "After para."]) mapsWhole(box, ONE, para);
  const b = blockAt(ONE, "<div align");
  assert.deepEqual([elems(box, ONE, b), wraps(box, ONE, b)], [['DIV:"Inner paragraph here."', 'DIV.inner:"Inner paragraph here."'], ["DIV", "DIV.inner"]], "one block, two wrappers, outer first; the inner div is the block's element through the resync");
  assert.equal(owner(box, ONE, kidsOf(kidsOf(box)[1])[0]), b, "the inner div is the block's too");
  assert.deepEqual(elems(box, ONE, blockAt(ONE, "Inner paragraph")), ['P:"Inner paragraph here."']);
});

test("the text-alike html node (Slice 1's merge-review finding, ruling 10): a kept `<div>Go</div>` before the paragraph `Go` is refused as the html block's element and Go maps to its own offsets (the tag test); an html `<p>Go</p>` before `Go` owns the first <p> and the paragraph the second (the two-block confirmation); the same-text list item after `<p><b>a</b> <i>b</i></p>` keeps its <ul>; the last-block exception is recorded: a text-alike node a dropped `<form>` hoisted before the note's final paragraph is taken for it", () => {
  const DIV = "Intro para.\n\n<div>Go</div>\n\nGo\n\nAfter para.\n";
  let box = buildRendered(DIV);
  assert.deepEqual(kidsOf(box).map(tagOf), ["P", "DIV", "P", "P"]);
  assert.deepEqual(elems(box, DIV, blockAt(DIV, "<div>Go")), ['DIV:"Go"'], "the html block owns its div (before: nothing; the paragraph Go took it)");
  assert.equal(owner(box, DIV, kidsOf(box)[2]), blockAt(DIV, "Go"), "the paragraph Go owns its own <p>");
  assert.equal(ok(mapText(box, DIV, "Go", 1), "Go's own <p>").range.start, at(DIV, "\nGo\n") + 1);
  assert.match(bad(mapText(box, DIV, "Go", 0), "the div's text").reason, /an HTML block/);
  mapsWhole(box, DIV, "After para.");
  const P = "Intro para.\n\n<p>Go</p>\n\nGo\n\nAfter para.\n";
  box = buildRendered(P);
  assert.deepEqual(kidsOf(box).map(tagOf), ["P", "P", "P", "P"]);
  assert.deepEqual([owner(box, P, kidsOf(box)[1]), owner(box, P, kidsOf(box)[2]), owner(box, P, kidsOf(box)[3])], [blockAt(P, "<p>Go"), blockAt(P, "Go"), blockAt(P, "After")], "html <p>, then Go's <p>, then After's (before: Go took the html <p> and After took Go's)");
  assert.equal(ok(mapText(box, P, "Go", 1), "Go").range.start, at(P, "\nGo\n") + 1);
  mapsWhole(box, P, "After para.");
  // the hoisted shape, confirmed past the text-alike node by the block after it: the sanitizer unwraps the form and its <p>
  // stands at the top level with Go's text; the html block owns it through the resync, Go and After own their own
  const FORM = "Intro para.\n\n<form action=\"/x\"><p>Go</p></form>\n\nGo\n\nAfter para.\n";
  box = buildRendered(FORM);
  assert.deepEqual(kidsOf(box).map(tagOf), ["P", "P", "P", "P"], "the form is unwrapped, its <p> kept");
  assert.deepEqual([owner(box, FORM, kidsOf(box)[1]), owner(box, FORM, kidsOf(box)[2]), owner(box, FORM, kidsOf(box)[3])], [blockAt(FORM, "<form"), blockAt(FORM, "Go"), blockAt(FORM, "After")]);
  mapsWhole(box, FORM, "After para.");
  // the same-text list item (blank-scenes.json's note; the Slice 4 build note's item 10 (d), the same-text trigger): the list
  // block's element is a <ul>, so it never fits the html block's <p>, and a paint from the intro reaches the closing paragraph
  const LIST = "Intro para.\n\n<p><b>a</b> <i>b</i></p>\n\n- <b>a</b> <i>b</i>\n\nAfter para.\n";
  box = buildRendered(LIST);
  assert.deepEqual(kidsOf(box).map(tagOf), ["P", "P", "UL", "P"]);
  assert.deepEqual([elems(box, LIST, blockAt(LIST, "<p><b>a")), elems(box, LIST, blockAt(LIST, "- <b>a"))], [['P:"a b"'], ['UL:"a b"']], "the html block keeps its <p>, the list its <ul>");
  mapsWhole(box, LIST, "After para.");
  assert.equal(painted(LIST, "Intro para.", "After para.").pop(), "After para.", "the paint reaches the closing paragraph");
  // the last-block exception (ruling 10, recorded): a hoisted text-alike node right before the note's FINAL paragraph is taken
  // for it, since no block after confirms the run; the paragraph's quote is still its own source, and the leftover <p> is no
  // block's. A closed tag the scan can see (`<p>Go</p>`) is taken before the resync, so the exception needs a dropped wrapper.
  const LAST = "Intro para.\n\n<form action=\"/x\"><p>Go</p></form>\n\nGo\n";
  box = buildRendered(LAST);
  assert.deepEqual(kidsOf(box).map(tagOf), ["P", "P", "P"]);
  assert.deepEqual([owner(box, LAST, kidsOf(box)[1]), owner(box, LAST, kidsOf(box)[2])], [blockAt(LAST, "Go"), -1], "the hoisted <p> is taken for Go; the real one is no block's");
  assert.equal(ok(mapText(box, LAST, "Go", 0), "Go through the hoisted node").range.start, at(LAST, "\nGo\n") + 1, "the quote is Go's own source still");
  const CLOSEDLAST = "Intro para.\n\n<p>Go</p>\n\nGo\n";
  box = buildRendered(CLOSEDLAST);
  assert.deepEqual([owner(box, CLOSEDLAST, kidsOf(box)[1]), owner(box, CLOSEDLAST, kidsOf(box)[2])], [blockAt(CLOSEDLAST, "<p>Go"), blockAt(CLOSEDLAST, "Go")], "a closed <p> is taken by the scan, so the final paragraph pairs right");
});

test("the resync across an html block, the sanitizer-shortened trigger (the Slice 4 build note's item 10 (d), blank-scenes.json's stripped-style scene): the html `<p>` owns its element and no more, the list item whose `<style>` went with its text is refused as a mismatch with its own <ul>, the closing paragraph maps, and a paint from the intro reaches it (before: the html block took every node and the paint stopped at it)", () => {
  const scene = SCENES.find((s) => s.name.startsWith("adjacent whitespace nodes left by a stripped comment"));
  assert.ok(scene, "the scene is in the fixture");
  const src = scene!.markdown;
  assert.match(src, /<style>x\{\}<\/style>/, "the list item holds the style the sanitizer strips");
  const box = buildRendered(src);
  assert.deepEqual(kidsOf(box).map(tagOf), ["P", "P", "UL", "P"]);
  assert.equal(find(box, "UL", "a").textContent.includes("x{}"), false, "the stand-in dropped the style's text");
  assert.deepEqual(elems(box, src, blockAt(src, "<p><b>a")), ['P:"a b"'], "the html block: its <p> and no more");
  const list = bad(mapText(box, src, "b", 1), "the list item's text (its <i>b</i>; the html block's <i>b</i> is the first shown)");
  assert.match(list.reason, /does not match the file/, "the shortened item is a mismatch, refused with its own element");
  assert.deepEqual(elems(box, src, blockAt(src, "- <b>a")), ['UL:"a b x"']);
  mapsWhole(box, src, "After para.");
  assert.equal(painted(src, "Intro para.", "After para.").pop(), "After para.", "the paint reaches the closing paragraph");
  // every other scene of the union reaches its closing paragraph too (the trim leg's oracle, md-config-paint-trim-browser.test.ts
  // test 1, is no longer confined to the scenes before this one)
  const stopped = SCENES.filter((s) => painted(s.markdown, "Intro para.", "After para.").pop() !== "After para.").map((s) => s.name);
  assert.deepEqual(stopped, [], "scenes whose paint stops before the closing paragraph");
});

test("a selection boundary in the whitespace between nested blocks snaps to the nested block beside it, as the top level's does; the wrapper's block keeps the summary's text; a node the resync left over inside a wrapper is no block's", () => {
  const box = buildRendered(PLAIN);
  const div = find(box, "DIV", "Centered");
  const ws = div.childNodes.filter((n) => n instanceof FakeText) as FakeText[];
  assert.ok(ws.length >= 2 && ws.every((t) => t.data.trim() === ""), "the div holds whitespace text either side of its paragraph");
  const fromWs = ok(mapRenderedSelection(sel({ node: ws[0], offset: 0 }, point(box, "paragraph inside", true)), El(box), PLAIN), "a start in the whitespace before the nested paragraph");
  assert.equal(fromWs.range.start, at(PLAIN, "Centered **bold**"), "snaps to the nested paragraph's first character");
  const toWs = ok(mapRenderedSelection(sel(point(box, "Centered"), { node: ws[ws.length - 1], offset: 1 }), El(box), PLAIN), "an end in the whitespace after it");
  assert.equal(toWs.range.end, at(PLAIN, "inside the div.") + "inside the div.".length, "snaps to its last character");
  const det = find(box, "DETAILS", "Click me");
  const detWs = det.childNodes.filter((n) => n instanceof FakeText && n.data.trim() === "") as FakeText[];
  const afterSummary = ok(mapRenderedSelection(sel({ node: detWs[0], offset: 0 }, point(box, "inside details.", true)), El(box), PLAIN), "a start in the whitespace after the summary");
  assert.equal(afterSummary.range.start, at(PLAIN, "Hidden paragraph"));
});

test("the cached index follows a wrapper's children: the regions layer wrapping a nested picture's paragraph in a span (file-comments-regions.ts) re-analyses the pairing, so the nested paragraph and the paragraph after it map still (a shape read from the root's children alone would keep the stale index and refuse)", () => {
  const src = "Intro para.\n\n<div align=\"center\">\n\n![a](a.png)\n\nCentered paragraph here.\n\n</div>\n\nAfter para.\n";
  const box = buildRendered(src);
  mapsWhole(box, src, "Centered paragraph here.");
  const div = find(box, "DIV", "Centered");
  const pic = kidsOf(div)[0];
  assert.equal(pic.tagName, "P"); assert.equal(pic.textContent, "");
  const span = new FakeElement(box.ownerDocument, "SPAN"); span.setAttribute("class", "fc-region-wrap");
  div.replaceChild(span, pic); span.appendChild(pic);
  mapsWhole(box, src, "Centered paragraph here.");
  mapsWhole(box, src, "After para.");
  assert.deepEqual(elems(box, src, blockAt(src, "![a]")), ['SPAN.fc-region-wrap:""'], "the picture's block pairs with the span by its empty text, as at the top level");
});
