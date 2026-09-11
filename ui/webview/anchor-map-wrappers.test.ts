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
import { hideEdges, sameNodes } from "../test-dom-shim";

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
/** The end tags the HTML parser honours through an open `<p>` (anchor-map.ts P_CLOSERS and FORMATTING): any other end tag met with
 *  a `<p>` open above its element is IGNORED by the parser ("any other end tag" in body: a special element on the way stops the
 *  walk), so `</label>` or `</span>` inside a paragraph closes nothing and mints no `<p>` (the Slice 5 review, round 3). */
const HONOURED_END = /^(?:ADDRESS|ARTICLE|ASIDE|BLOCKQUOTE|BUTTON|CENTER|DETAILS|DIALOG|DIR|DIV|DL|FIELDSET|FIGCAPTION|FIGURE|FOOTER|FORM|HEADER|HGROUP|LISTING|MAIN|MENU|NAV|OL|PRE|SEARCH|SECTION|SUMMARY|UL|TABLE|H[1-6]|LI|DD|DT|P|A|B|BIG|CODE|EM|FONT|I|NOBR|S|SMALL|STRIKE|STRONG|TT|U)$/;
/** marked's HTML into the stand-in, as a browser's parser reads a fragment: an unclosed tag stays open and the nodes after it
 *  nest inside it (the wrapper shape this file is about); an end tag closes down to its element, unless a `<p>` stands open above
 *  that element and the tag is one the parser ignores there (HONOURED_END); one with no open element is dropped, a `</p>` minting
 *  the parser's empty `<p>`; a block-level start tag closes the nearest open `<p>` in button scope, whatever inline elements stand
 *  open inside it (the review's round 3: `<p>Lead` then `<br>`, `<img>` and `<span class="w">` blocks nest in the p, and the next
 *  paragraph's `<p>` closes it through the span). */
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
        let found = false, ignored = false;
        for (let k = stack.length - 1; k > 0; k--) {
          if (stack[k].tagName === name) { stack.length = k; found = true; break; }
          if (stack[k].tagName === "P" && !HONOURED_END.test(name)) { ignored = true; break; }   // the parser's "any other end tag" met a special element
        }
        if (!found && !ignored && name === "P") top().appendChild(doc.createElement("p"));   // the parser mints an empty <p></p> for a stray </p>
        i = e + 1; continue;
      }
      const m = /^<([a-zA-Z][\w:-]*)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*)\s*(\/?)>/.exec(html.slice(i));
      if (!m) { top().appendChild(doc.createTextNode("<")); i++; continue; }
      const el = doc.createElement(m[1]);
      const attrRe = /([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
      let a: RegExpExecArray | null;
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], decodeEntities(a[2] ?? a[3] ?? a[4] ?? ""));
      // the parser closes an open <p> when a block-level tag starts (so marked's next block never nests in an author's `<p>`): the
      // nearest <p> in button scope, through any inline element open inside it (a table closes none in DOMPurify's quirks-mode
      // document, which the browser legs cover; the stand-in keeps the standards reading for it)
      if (/^(?:p|div|details|h[1-6]|ul|ol|pre|blockquote|table|hr|section|figure|summary)$/i.test(m[1])) {
        for (let k = stack.length - 1; k > 0; k--) { if (stack[k].tagName === "P") { stack.length = k; break; } if (/^(?:BUTTON|TABLE|TD|TH|CAPTION|TEMPLATE|OBJECT)$/.test(stack[k].tagName)) break; }
      }
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

// ── the Slice 5 review, round 1: the pairing's edges ──
/** The tag names of block b's elements, in order. */
const tagsOf = (box: FakeElement, src: string, b: number): string[] => renderedBlockElements(El(box), src, b).map((e) => (e as unknown as FakeElement).tagName);
const P = (i: number): string => `Paragraph ${i} carries several plain words for the probe to find.`;

test("a wrapper whose raw holds its own child (a summary, a lead text) followed at once by another html block: the summary stays the outer block's and the inner block takes its own element, so the passages nested in the inner wrapper and every later one map (before: the outer's resync ended at the next html block with the summary left over in its place, the inner's scan found the summary where its element should be, took nothing, and fell to every node to the end of the document, every later selection refused as an HTML block at the inner's offset); nested details, details then a centred div, a lead text then an inner div, a comment between, an empty details then a details, and details then an img, which owns its img alone", () => {
  const NESTED = `# T\n\n${P(1)}\n\n<details><summary>Outer</summary>\n\n<details><summary>Inner</summary>\n\n${P(2)}\n\n</details>\n\n${P(3)}\n\n</details>\n\n${P(4)}\n`;
  let box = buildRendered(NESTED);
  assert.deepEqual(kidsOf(box).map(tagOf), ["H1", "P", "DETAILS", "P"]);
  assert.deepEqual(kidsOf(kidsOf(box)[2]).map(tagOf), ["SUMMARY", "DETAILS", "P"], "the inner details and the outer's paragraph nest in the outer details");
  for (const para of [P(2), P(3), P(4)]) mapsWhole(box, NESTED, para);
  const outer = blockAt(NESTED, "<details><summary>Outer"), inner = blockAt(NESTED, "<details><summary>Inner");
  assert.deepEqual([tagsOf(box, NESTED, outer), wraps(box, NESTED, outer)], [["DETAILS", "SUMMARY"], ["DETAILS"]], "the outer block: its details and its summary, the details the wrapper");
  assert.deepEqual([tagsOf(box, NESTED, inner), wraps(box, NESTED, inner)], [["DETAILS", "SUMMARY"], ["DETAILS"]], "the inner block: its own details and summary (before: the outer's summary, the inner details, and every paragraph after)");
  assert.equal(owner(box, NESTED, find(box, "SUMMARY", "Outer")), outer);
  assert.equal(owner(box, NESTED, find(box, "SUMMARY", "Inner")), inner);
  assert.deepEqual(tagsOf(box, NESTED, blockAt(NESTED, P(2))), ["P"]);
  const sum = bad(mapText(box, NESTED, "Inner"), "the inner summary");
  assert.match(sum.reason, /an HTML block/);
  assert.equal(sum.blockStartOffset, at(NESTED, "<details><summary>Inner"), "refused at the inner details' own offset");
  // details then a centred div
  const DIV = `# T\n\n${P(1)}\n\n<details><summary>Sum</summary>\n\n<div align="center">\n\n${P(2)}\n\n</div>\n\n${P(3)}\n\n</details>\n\n${P(4)}\n`;
  box = buildRendered(DIV);
  for (const para of [P(2), P(3), P(4)]) mapsWhole(box, DIV, para);
  assert.deepEqual(tagsOf(box, DIV, blockAt(DIV, "<div align")), ["DIV"], "the div block owns its div alone");
  assert.deepEqual(tagsOf(box, DIV, blockAt(DIV, "<details>")), ["DETAILS", "SUMMARY"]);
  // a lead text inside the wrapper's own line, then an inner div
  const LEAD = `# T\n\n<div align="center">Lead\n\n<div class="in">\n\n${P(2)}\n\n</div>\n\n${P(3)}\n\n</div>\n`;
  box = buildRendered(LEAD);
  for (const para of [P(2), P(3)]) mapsWhole(box, LEAD, para);
  assert.deepEqual(tagsOf(box, LEAD, blockAt(LEAD, "<div class")), ["DIV"]);
  assert.match(bad(mapText(box, LEAD, "Lead"), "the lead text").reason, /an HTML block/, "the wrapper's own text stays the html block's");
  // a comment between the two
  const COMMENT = `# T\n\n<details><summary>Sum</summary>\n\n<!-- c -->\n\n<div align="center">\n\n${P(2)}\n\n</div>\n\n${P(3)}\n\n</details>\n`;
  box = buildRendered(COMMENT);
  for (const para of [P(2), P(3)]) mapsWhole(box, COMMENT, para);
  // an empty details (closed at once), then a details holding text
  const EMPTY = `# T\n\n<details><summary>Empty</summary>\n\n</details>\n\n<details><summary>Second</summary>\n\n${P(2)}\n\n</details>\n\n${P(3)}\n`;
  box = buildRendered(EMPTY);
  for (const para of [P(2), P(3)]) mapsWhole(box, EMPTY, para);
  assert.deepEqual(tagsOf(box, EMPTY, blockAt(EMPTY, "<details><summary>Empty")), ["DETAILS", "SUMMARY"]);
  assert.deepEqual(tagsOf(box, EMPTY, blockAt(EMPTY, "<details><summary>Second")), ["DETAILS", "SUMMARY"]);
  assert.deepEqual(tagsOf(box, EMPTY, blockAt(EMPTY, "</details>")), [], "the closing tag's block owns nothing");
  // details then an img block: the img block owns the img alone, and the summary's refusal names the details' offset
  const IMG = `# T\n\n<details><summary>Sum</summary>\n\n<img src="a.png" alt="x">\n\n${P(2)}\n\n</details>\n\n${P(3)}\n`;
  box = buildRendered(IMG);
  for (const para of [P(2), P(3)]) mapsWhole(box, IMG, para);
  assert.deepEqual(tagsOf(box, IMG, blockAt(IMG, "<img")), ["IMG"], "the img block owns its img (before: the summary and the img)");
  assert.deepEqual(tagsOf(box, IMG, blockAt(IMG, "<details>")), ["DETAILS", "SUMMARY"]);
  assert.equal(bad(mapText(box, IMG, "Sum"), "the summary").blockStartOffset, at(IMG, "<details>"), "the Raw view opens at the details, not at the img");
  // a paragraph between the two wrappers, the shape that paired before, still does
  const BETWEEN = `# T\n\n<details><summary>Outer</summary>\n\n${P(5)}\n\n<details><summary>Inner</summary>\n\n${P(2)}\n\n</details>\n\n</details>\n`;
  box = buildRendered(BETWEEN);
  for (const para of [P(5), P(2)]) mapsWhole(box, BETWEEN, para);
});

test("a closing tag inside a paragraph (`**Bold** </div>` on the paragraph's own line, `Last line.</details>`): the parser closes the wrapper with the paragraph's `<p>` and mints an empty `<p></p>` for the paragraph's own `</p>`, which the pairing steps over as no block's, so every paragraph after the closer maps to its own offsets, two identical paragraphs to their own copies (before: the paragraph after the closer took the empty `<p>` as a mismatch, each later one its predecessor's element, the FIRST rendered copy of a repeated paragraph mapped to the SECOND copy's offsets, and the last paragraph was no block's); a stray `</div>` in a top-level paragraph, which the parser drops, mints nothing", () => {
  const REPEAT = `# T\n\n${P(1)}\n\n<div align="center">\n\n${P(2)}\n\n**Bold** </div>\n\nGo\n\nGo\n\n${P(3)}\n`;
  let box = buildRendered(REPEAT);
  const div = find(box, "DIV", "Bold");
  assert.deepEqual(kidsOf(div).map(tagOf), ["P", "P"], "the div holds its two paragraphs, the closer's among them");
  assert.deepEqual(kidsOf(box).map(tagOf), ["H1", "P", "DIV", "P", "P", "P", "P"], "an empty <p> after the div (the parser's, for the stray </p>), then Go, Go and the last paragraph");
  const minted = kidsOf(box)[3];
  assert.equal(minted.textContent, "", "the minted <p> is empty");
  assert.equal(owner(box, REPEAT, minted), -1, "the minted <p> is no block's");
  const first = ok(mapText(box, REPEAT, "Go", 0), "the first rendered Go");
  assert.equal(first.range.start, at(REPEAT, "\nGo\n") + 1, "maps to the FIRST copy's offsets (before: the second's)");
  const second = ok(mapText(box, REPEAT, "Go", 1), "the second rendered Go (before: a mismatch refusal)");
  assert.equal(second.range.start, REPEAT.lastIndexOf("\nGo\n") + 1);
  mapsWhole(box, REPEAT, P(3));
  mapsWhole(box, REPEAT, P(2));
  assert.deepEqual(tagsOf(box, REPEAT, blockAt(REPEAT, "**Bold**")), ["P"], "the closer's paragraph owns its nested <p>");
  assert.equal(owner(box, REPEAT, kidsOf(box)[6]), blockAt(REPEAT, P(3)), "the last paragraph is its block's (before: no block's)");
  // distinct paragraphs after the closer
  const PLAINER = `# T\n\n<div align="center">\n\n${P(2)}\n\n**Bold** </div>\n\n${P(3)}\n\n${P(4)}\n`;
  box = buildRendered(PLAINER);
  for (const para of [P(2), P(3), P(4)]) mapsWhole(box, PLAINER, para);
  // a details closed on the last nested paragraph's line
  const DET = `# T\n\n<details><summary>Sum</summary>\n\n${P(2)}\n\nLast line.</details>\n\n${P(3)}\n`;
  box = buildRendered(DET);
  for (const para of [P(2), "Last line.", P(3)]) mapsWhole(box, DET, para);
  assert.deepEqual(tagsOf(box, DET, blockAt(DET, P(3))), ["P"]);
  // a top-level paragraph with a stray closer: no wrapper is open, the parser drops the tag, nothing is minted, the next maps
  const STRAY = `# T\n\n${P(1)}\n\nText </div>\n\n${P(3)}\n`;
  box = buildRendered(STRAY);
  assert.deepEqual(kidsOf(box).map(tagOf), ["H1", "P", "P", "P"]);
  mapsWhole(box, STRAY, P(3));
  assert.equal(owner(box, STRAY, kidsOf(box)[3]), blockAt(STRAY, P(3)));
});

test("a formula at the selection's END is judged in document order with the other obstacles: a drag from a table cell (or from the intro across the table) into a formula's glyphs names the table, the obstacle the person's eye meets first, with the table's Raw offer (before: the formula, judged ahead of the pass); a drag from the paragraph before the formula into it still names the formula with the formula preselected, and so does one from the whitespace between two formulas into the second, and a drag begun inside a formula names the formula whatever follows", () => {
  const src = "Intro para.\n\n| Col A | Col B |\n|-------|-------|\n| cell one | cell two |\n\nBetween para.\n\nTail $tt$ formula.\n\nPair $aa$ $bb$ here.\n";
  const box = buildRendered(src);
  const inT = { node: find(box, "SPAN", "tt").childNodes[0], offset: 1 };   // strictly inside the stand-in fill's glyphs for $tt$ (a `.katex` span holding "tt")
  assert.equal((inT.node as FakeText).data, "tt", "the formula's glyph node");
  const span = (from: Pt, to: Pt) => mapRenderedSelection(sel(from, to), El(box), src);
  let r = bad(span(point(box, "cell two"), inT), "a cell into the formula's glyphs");
  assert.match(r.reason, /^This selection touches a table; comment on it from the Raw view\.$/, "the table comes first (before: a formula): " + r.reason);
  assert.equal(r.blockStartOffset, at(src, "| Col A"), "the table's Raw offer");
  r = bad(span(point(box, "Intro para."), inT), "the intro across the table into the formula");
  assert.match(r.reason, /a table/, r.reason);
  r = bad(span(inT, point(box, "cell two")), "the same drag made backwards (the anchor inside the formula, the focus in the cell)");
  assert.match(r.reason, /a table/, "the end of the span in document order is still the formula: " + r.reason);
  // no obstacle before the formula: the formula, preselected
  r = bad(span(point(box, "Between para."), inT), "the paragraph before into the formula");
  assert.match(r.reason, /a formula/, r.reason);
  assert.equal(src.slice(r.rawRange!.start, r.rawRange!.end), "$tt$", "the formula with its delimiters preselected");
  assert.equal(r.blockStartOffset, at(src, "$tt$"));
  // the whitespace between two formulas into the second: a formula, not "only whitespace"
  const pairP = find(box, "P", "Pair");
  const ws = pairP.childNodes.find((n) => n instanceof FakeText && n.data === " " && n.parentNode === pairP && pairP.childNodes.indexOf(n) > 0 && pairP.childNodes[pairP.childNodes.indexOf(n) - 1] instanceof FakeElement) as FakeText;
  assert.ok(ws, "the space between $a$ and $b$");
  const bGlyph = find(box, "SPAN", "bb").childNodes[0];
  r = bad(span({ node: ws, offset: 0 }, { node: bGlyph, offset: 1 }), "the space between the formulas into the second");
  assert.match(r.reason, /a formula/, r.reason);
  assert.equal(src.slice(r.rawRange!.start, r.rawRange!.end), "$bb$");
  // begun strictly inside a formula: the formula is the first obstacle, whatever the span crosses after it
  r = bad(span({ node: inT.node, offset: 1 }, point(box, "here.", true)), "from inside $tt$ to the end of the next paragraph");
  assert.match(r.reason, /a formula/, r.reason);
  assert.equal(src.slice(r.rawRange!.start, r.rawRange!.end), "$tt$");
  // begun at the formula's first glyph: the formula is covered whole and travels inside the quote (the review's round 2 ruling)
  const fromEdge = ok(span({ node: inT.node, offset: 0 }, point(box, "formula.", true)), "from the formula's first glyph to the end of its paragraph");
  assert.equal(fromEdge.quote, "$tt$ formula.");
  // the spans that end in prose read as before
  assert.match(bad(span(point(box, "cell two"), point(box, "Tail", true)), "a cell into prose").reason, /a table/);
  assert.equal(ok(span(point(box, "Between para."), point(box, "Tail", true)), "prose to prose").quote, "Between para.\n\nTail");
});

// ── the Slice 5 review, round 2: the minted <p> in the run check, the regions layer's span, the sanitizer's unwraps, the
//    closing-tag block, the quoted and loose-item closers, and the paint fallback's scope ──
/** The regions layer's wrap of every picture while the Comments panel is open (file-comments-regions.ts): a `span.fc-imgwrap`
 *  around the <img>, the drawing overlay after it inside the span. */
function wrapImgs(box: FakeElement): number {
  const imgs = ((): FakeElement[] => { const out: FakeElement[] = []; const visit = (n: FakeNode) => { if (n instanceof FakeElement && n.tagName === "IMG") out.push(n); n.childNodes.forEach(visit); }; visit(box); return out; })();
  for (const img of imgs) {
    const doc = box.ownerDocument, parent = img.parentNode as FakeElement;
    const span = doc.createElement("span"); span.setAttribute("class", "fc-imgwrap");
    parent.replaceChild(span, img); span.appendChild(img);
    const overlay = doc.createElement("div"); overlay.setAttribute("class", "fc-overlay fc-overlay-off"); span.appendChild(overlay);
  }
  return imgs.length;
}
/** The texts of the marks a paint from `from` to `to` leaves over an existing box, in order. */
function paintedIn(box: FakeElement, src: string, from: string, to: string): string[] {
  const marks = paintRendered(El(box), src, { start: at(src, from), end: at(src, to) + to.length }, "fc-hl") as unknown as FakeElement[] | null;
  return (marks || []).map((m) => m.textContent);
}
/** The minted <p> after a closer: an empty top-level or nested P that no block owns, one such node in the box. */
function mintedIn(box: FakeElement, src: string): FakeElement {
  const empties: FakeElement[] = [];
  const visit = (n: FakeNode) => { if (n instanceof FakeElement && n.tagName === "P" && n.childNodes.length === 0) empties.push(n); n.childNodes.forEach(visit); };
  visit(box);
  assert.equal(empties.length, 1, "one empty <p> in the box, the parser's");
  assert.equal(owner(box, src, empties[0]), -1, "the minted <p> is no block's");
  return empties[0];
}

test("a wrapper with a leftover (a lead text, a summary) closed inline on its ONLY paragraph, followed by an html block (an img, a centred div, a details) or by plain paragraphs: the run's end confirms past the parser's minted <p>, so the closer maps to its own offsets, the following html block owns its own element and every later passage maps (before: the run check met the minted <p> where the next block's element should be, or where the next paragraph was expected, no end confirmed, the wrapper kept its element alone, the closer paired with the leftover as a mismatch and was swallowed by the following html block, refused as an HTML block at that block's offset, or every later paragraph paired one node early and the last was no block's)", () => {
  const IMG = `<div align="center">Lead\n\n**Bold** </div>\n\n<img src="a.png" alt="x">\n\nAfter.\n`;
  let box = buildRendered(IMG);
  const bold = ok(mapText(box, IMG, "Bold"), "the closer's text (before: refused as an HTML block at the img's offset)");
  assert.deepEqual(bold.range, { start: at(IMG, "Bold"), end: at(IMG, "Bold") + 4 });
  mapsWhole(box, IMG, "After.");
  const div = blockAt(IMG, "<div align");
  assert.deepEqual(tagsOf(box, IMG, div), ["DIV"], "the div block's element");
  assert.equal(owner(box, IMG, find(box, "DIV", "Lead").childNodes[0]), div, "the lead text is the div block's leftover");
  assert.deepEqual(tagsOf(box, IMG, blockAt(IMG, "<img")), ["IMG"], "the img block owns its img alone (before: the closer's <p>, the minted <p> and the img)");
  assert.deepEqual(tagsOf(box, IMG, blockAt(IMG, "**Bold**")), ["P"], "the closer's paragraph owns its nested <p>");
  mintedIn(box, IMG);
  // the same with a centred div after the closer, and with a details
  const DIV = `<div align="center">Lead\n\n**Bold** </div>\n\n<div align="center">\n\n${P(2)}\n\n</div>\n\n${P(3)}\n`;
  box = buildRendered(DIV);
  assert.equal(ok(mapText(box, DIV, "Bold"), "Bold before an inner div").range.start, at(DIV, "Bold"));
  for (const para of [P(2), P(3)]) mapsWhole(box, DIV, para);
  const secondDiv = sourceBlockSpans(DIV).findIndex((sp) => sp.start === DIV.lastIndexOf("<div align"));
  assert.ok(secondDiv > 0, "the second div's block");
  assert.deepEqual(tagsOf(box, DIV, secondDiv), ["DIV"], "the second div block owns its div alone");
  const DET = `Intro.\n\n<details><summary>Notes</summary>\n\nOnly line.</details>\n\n<details><summary>More</summary>\n\nSecond body.\n\n</details>\n\nAfter.\n`;
  box = buildRendered(DET);
  for (const para of ["Only line.", "Second body.", "After."]) mapsWhole(box, DET, para);
  assert.deepEqual(tagsOf(box, DET, blockAt(DET, "<details><summary>Notes")), ["DETAILS", "SUMMARY"]);
  assert.deepEqual(tagsOf(box, DET, blockAt(DET, "<details><summary>More")), ["DETAILS", "SUMMARY"], "the second details block owns its own details and summary (before: the first's closer, the minted <p>, the second details and everything after)");
  // a summary and a single closer, then plain paragraphs (the other half of the same model: before, the closer was a mismatch
  // against the summary and the paragraphs after it were no block's)
  const PLAIN1 = `<details><summary>Notes</summary>\n\nOnly line.</details>\n\nAfter one.\n\nAfter two.\n`;
  box = buildRendered(PLAIN1);
  for (const para of ["Only line.", "After one.", "After two."]) mapsWhole(box, PLAIN1, para);
  assert.equal(owner(box, PLAIN1, kidsOf(box)[kidsOf(box).length - 1]), blockAt(PLAIN1, "After two."), "the last paragraph is its block's");
  mintedIn(box, PLAIN1);
  // comments on the passages paint (the exact path, now that each maps)
  assert.deepEqual(paintedIn(box, PLAIN1, "After two.", "After two."), ["After two."]);
  assert.deepEqual(paintedIn(buildRendered(IMG), IMG, "After.", "After."), ["After."]);
});

test("with the Comments panel open the regions layer wraps every <img> in a span (file-comments-regions.ts), and the pairing reads the span as the picture: a standalone <img> block after a lead-text div closed in the same block, after a `<details><summary>` fold, a README's logo, screenshot and demo pictures, and an `<img>` then `<div align=\"center\">` in one block pair as they do with the panel closed, so the nested passages map and a comment on them paints (before: the span hid the IMG from every tag test; the wrapper before it confirmed its run at no end and kept its element alone, its nested paragraph paired with the leftover as a mismatch and was swallowed by the img block, refused as an HTML block at the img block's offset with the panel open while it mapped with the panel closed, and its comment painted nothing, the card offering Reveal; an `<img>` then `<div>` block took every node to the end)", () => {
  const LEAD = `Intro.\n\n<div align="center">Lead text.\n\n${P(3)}\n\n</div>\n<img src="c004.png" alt="c">\n\nAfter.\n`;
  const FOLD = `Intro.\n\n<details><summary>More</summary>\n\n${P(3)}\n\n</details>\n<img src="c004.png" alt="c">\n\nAfter.\n`;
  const README = `<div align="center">\n<img src="logo.png" alt="logo">\n\nTag line.\n\n</div>\n\n<img src="shot.png" alt="s">\n\nIntro.\n\n<details>\n<summary>More</summary>\n\nHidden text.\n\n</details>\n\n<img src="demo.gif" alt="d">\n\nAfter.\n`;
  const LOGO = `<img src="logo.png" alt="l">\n<div align="center">\n\n# Head\n\n${P(4)}\n\n</div>\n\nAfter.\n`;
  const scenes: [string, string, string[], string][] = [
    ["lead-text div then </div> and <img> in one block", LEAD, [P(3), "After."], "</div>\n<img"],
    ["details then </details> and <img> in one block", FOLD, [P(3), "After."], "</details>\n<img"],
    ["a README: logo inside the div, a screenshot, a fold, a demo", README, ["Tag line.", "Intro.", "Hidden text.", "After."], "<img src=\"shot"],
    ["<img> then <div> in one block", LOGO, ["Head", P(4), "After."], "<img src=\"logo"],
  ];
  for (const [name, src, passages, imgBlock] of scenes) {
    // the panel closed: the shape the slice's fixtures pin
    let box = buildRendered(src);
    for (const para of passages) mapsWhole(box, src, para);
    // the panel open: every <img> wrapped, the pairing re-analysed over the new shape (the cache reads the root's children)
    box = buildRendered(src);
    assert.ok(wrapImgs(box) >= 1, name + ": pictures wrapped");
    for (const para of passages) mapsWhole(box, src, para);
    for (const para of passages) assert.deepEqual(paintedIn(box, src, para, para), [para], name + ": a comment on " + JSON.stringify(para) + " paints with the panel open");
    const b = blockAt(src, imgBlock);
    assert.ok(elems(box, src, b).some((e) => e.startsWith("SPAN.fc-imgwrap:")), name + ": the img block owns the regions layer's span as its picture: " + JSON.stringify(elems(box, src, b)));
  }
  // a control that maps either way: a markdown picture paragraph inside the wrapper, and an <img> before the wrapper
  const CONTROL = `<img src="a.png" alt="a">\n\n<div align="center">\n\n![b](b.png)\n\n${P(2)}\n\n</div>\n\n${P(3)}\n`;
  const box = buildRendered(CONTROL);
  wrapImgs(box);
  for (const para of [P(2), P(3)]) mapsWhole(box, CONTROL, para);
});

test("an html wrapper the sanitizer unwraps (a <form>, KEEP_CONTENT: md-sanitize.ts) closed inline on a paragraph: the closer and every later paragraph map (before: the block's scan found no element, the run check met the minted <p> the unwrap left standing, no end confirmed and the block took every node to the document's end, every passage refused as an HTML block at the form's line); a form with a lead text keeps the hoisted text as its own; an <option> the sanitizer unwraps after a lead-text wrapper leaves a bare text node the wrapper's run reads past with the option's block, so the nested paragraph maps and its comment paints (before: the text stood where the next paragraph's element was expected, the wrapper kept its element alone and the paragraph was refused as the closing block's)", () => {
  const FORM = `Intro 001 alpha bravo.\n\n<form>\n\n${P(3)} </form>\n\nAfter 005 hotel india.\n\nAfter 006 juliet kilo.\n`;
  let box = buildRendered(FORM);
  assert.deepEqual(kidsOf(box).map(tagOf), ["P", "P", "P", "P", "P"], "the form unwrapped: its paragraph hoisted, the minted <p> after it");
  for (const para of [P(3), "After 005 hotel india.", "After 006 juliet kilo."]) mapsWhole(box, FORM, para);
  assert.deepEqual(tagsOf(box, FORM, blockAt(FORM, "<form>")), [], "the form's block owns nothing: its element is gone");
  mintedIn(box, FORM);
  const LEADFORM = `Intro.\n\n<form>Lead text here.\n\n${P(3)} </form>\n\nAfter one.\n`;
  box = buildRendered(LEADFORM);
  for (const para of [P(3), "After one."]) mapsWhole(box, LEADFORM, para);
  const lead = box.childNodes.find((n) => n instanceof FakeText && n.data.includes("Lead text here.")) as FakeText;
  assert.ok(lead, "the lead text hoisted to the top level");
  assert.equal(owner(box, LEADFORM, lead), blockAt(LEADFORM, "<form>"), "the hoisted lead text is the form block's");
  assert.match(bad(mapText(box, LEADFORM, "Lead text here."), "the lead").reason, /an HTML block/);
  // a wrapper before such a form: the form's hoisted text is read past by the wrapper's run
  const BEFORE = `<div align="center">Lead.\n\n${P(2)}\n\n</div>\n\n<form>Form lead.\n\n${P(3)} </form>\n\n${P(4)}\n`;
  box = buildRendered(BEFORE);
  for (const para of [P(2), P(3), P(4)]) mapsWhole(box, BEFORE, para);
  // the option
  const OPTION = `Intro.\n\n<div align="center">Lead 002 charlie.\n\n${P(3)}\n\n</div>\n\n<option>Opt 004 x.</option>\n\nAfter 005 hotel india.\n`;
  box = buildRendered(OPTION);
  for (const para of [P(3), "After 005 hotel india."]) mapsWhole(box, OPTION, para);
  assert.deepEqual(paintedIn(box, OPTION, P(3), P(3)), [P(3)], "a comment on the nested paragraph paints");
  const opt = box.childNodes.find((n) => n instanceof FakeText && n.data.includes("Opt 004 x.")) as FakeText;
  assert.ok(opt, "the option's text hoisted");
  assert.equal(owner(box, OPTION, opt), blockAt(OPTION, "<option>"), "the hoisted text is the option block's");
  assert.match(bad(mapText(box, OPTION, "Lead 002 charlie."), "the lead").reason, /an HTML block/, "the wrapper's own text stays the html block's");
});

test("a block that is a closing tag alone (`</details>`, `</div>`, a stray `</span>`) renders nothing and runs no resync, like a comment block: right before a paragraph carrying the OUTER wrapper's inline closer it owns no node and the closer and every later paragraph map (before: its resync started at the closer, met the minted <p> where the next paragraph was expected, confirmed at no end and, having no element of its own, took every node to the document's end: the closer and the paragraphs after it refused as an HTML block at the closing tag's line); a selection across such a block maps with its source inside the quote", () => {
  const NEST = `Intro.\n\n<div align="center">\n\n<details><summary>Sum.</summary>\n\n${P(3)}\n\n</details>\n\n${P(4)}</div>\n\nAfter 005 hotel india.\n\nAfter 006 juliet kilo.\n`;
  let box = buildRendered(NEST);
  for (const para of [P(3), P(4), "After 005 hotel india.", "After 006 juliet kilo."]) mapsWhole(box, NEST, para);
  assert.deepEqual(tagsOf(box, NEST, blockAt(NEST, "</details>")), [], "the closing tag's block owns nothing (before: the closer's <p>, the minted <p> and both paragraphs after)");
  assert.deepEqual(tagsOf(box, NEST, blockAt(NEST, `${P(4)}</div>`)), ["P"], "the closer's paragraph owns its <p>");
  mintedIn(box, NEST);
  const across = ok(mapRenderedSelection(sel(point(box, P(3)), point(box, P(4), true)), El(box), NEST), "from the fold's paragraph across the closing tag into the closer");
  assert.equal(across.quote, NEST.slice(at(NEST, P(3)), at(NEST, P(4)) + P(4).length), "the `</details>` line travels inside the quote");
  // the mirror: a details outside, a div inside, closed by `</div>` alone, then the details closed inline
  const MIRROR = `Intro.\n\n<details open><summary>Sum.</summary>\n\n<div align="center">\n\n${P(3)}\n\n</div>\n\n${P(4)}</details>\n\nAfter 005 hotel india.\n`;
  box = buildRendered(MIRROR);
  for (const para of [P(3), P(4), "After 005 hotel india."]) mapsWhole(box, MIRROR, para);
  // a stray `</span>` block, which the parser drops
  const STRAY = `Intro.\n\n<div align="center">\n\n${P(3)}\n\n</span>\n\n${P(4)}</div>\n\nAfter 005 hotel india.\n`;
  box = buildRendered(STRAY);
  for (const para of [P(3), P(4), "After 005 hotel india."]) mapsWhole(box, STRAY, para);
  assert.deepEqual(tagsOf(box, STRAY, blockAt(STRAY, "</span>")), []);
  // the control: an html comment block in the closing tag's place mapped before too
  const COMMENT = `Intro.\n\n<div align="center">\n\n${P(3)}\n\n<!-- a note -->\n\n${P(4)}</div>\n\nAfter 005 hotel india.\n`;
  box = buildRendered(COMMENT);
  for (const para of [P(3), P(4), "After 005 hotel india."]) mapsWhole(box, COMMENT, para);
});

test("an inline closer inside a blockquote's paragraph (`> quote </div>`) or a loose list item's mints an empty <p> at the top level as a paragraph's does, and the pairing steps over it: every paragraph after maps and a comment on it paints (before: the next paragraph took the minted <p> as a mismatch, every later one paired one node early, the last was no block's, and the comments on them painted nothing where the whole-text search had painted them); a tight item's closer and a heading's mint nothing, and nothing is skipped", () => {
  const QUOTE = `Intro.\n\n<div align="center">\n\n${P(2)}\n\n> Quote 003 echo foxtrot. </div>\n\nAfter 004 golf hotel.\n\nAfter 005 india juliet.\n`;
  let box = buildRendered(QUOTE);
  for (const para of [P(2), "After 004 golf hotel.", "After 005 india juliet."]) mapsWhole(box, QUOTE, para);
  assert.equal(ok(mapText(box, QUOTE, "Quote 003 echo foxtrot."), "the quoted closer").range.start, at(QUOTE, "Quote 003"));
  assert.deepEqual(tagsOf(box, QUOTE, blockAt(QUOTE, "> Quote")), ["BLOCKQUOTE"]);
  mintedIn(box, QUOTE);
  for (const para of ["After 004 golf hotel.", "After 005 india juliet."]) assert.deepEqual(paintedIn(box, QUOTE, para, para), [para], para + " paints");
  const LOOSE = `Intro.\n\n<div align="center">\n\n- Item 003 echo.\n\n- Item 004 foxtrot golf. </div>\n\nAfter 005 hotel india.\n\nAfter 006 juliet kilo.\n`;
  box = buildRendered(LOOSE);
  for (const para of ["After 005 hotel india.", "After 006 juliet kilo."]) mapsWhole(box, LOOSE, para);
  assert.deepEqual(tagsOf(box, LOOSE, blockAt(LOOSE, "- Item 003")), ["UL"]);
  mintedIn(box, LOOSE);
  // the controls: a tight item's closer and a heading's close the wrapper with no `</p>` after them
  const TIGHT = `Intro.\n\n<div align="center">\n\n- Item 003 echo.\n- Item 004 foxtrot golf. </div>\n\nAfter 005 hotel india.\n`;
  box = buildRendered(TIGHT);
  mapsWhole(box, TIGHT, "After 005 hotel india.");
  assert.equal(kidsOf(box).filter((k) => k.tagName === "P" && k.childNodes.length === 0).length, 0, "no empty <p> minted after a tight item's closer");
  const HEAD = `Intro.\n\n<div align="center">\n\n## Head 003 </div>\n\nAfter 005 hotel india.\n`;
  box = buildRendered(HEAD);
  mapsWhole(box, HEAD, "After 005 hotel india.");
  assert.equal(kidsOf(box).filter((k) => k.tagName === "P" && k.childNodes.length === 0).length, 0, "no empty <p> minted after a heading's closer");
});

test("Rendered paint inside a document-wide wrapper reads the nested blocks a range touches and no other: a mark costs its own paragraphs, as at the top level (before: every highlight unit under the wrapper per mark, the root's child being the wrapper; the Slice 5 review measured 0.8 ms per mark on a 1,000-paragraph note inside one div against 0.1 flat in Chromium, growing with the wrapper, where the stand-in had said 2x)", () => {
  const N = 40;
  const paras = Array.from({ length: N }, (_, i) => P(i));
  for (const [what, src] of [["a div", "# T\n\n<div align=\"center\">\n\n" + paras.join("\n\n") + "\n\n</div>\n"], ["a details", "# T\n\n<details><summary>More</summary>\n\n" + paras.join("\n\n") + "\n\n</details>\n"]] as const) {
    const box = buildRendered(src);
    const wrapper = kidsOf(box)[1];
    const ps = kidsOf(wrapper).filter((k) => k.tagName === "P");
    assert.equal(ps.length, N, what + ": the paragraphs nest in the wrapper");
    // the index is built once per root and source (it walks everything then); the first paint pays it
    assert.ok((paintRendered(El(box), src, { start: at(src, paras[0]), end: at(src, paras[0]) + 9 }, "fc-hl") || []).length >= 1, what + ": warm");
    const reads = new Map<FakeElement, number>();
    for (const p of ps) {
      const kids = p.childNodes;
      Object.defineProperty(p, "childNodes", { configurable: true, get() { reads.set(p, (reads.get(p) || 0) + 1); return kids; } });
    }
    const holder = (n: FakeNode): FakeElement => { let c: FakeNode = n; while (c.parentNode && c.parentNode !== wrapper) c = c.parentNode; return c as FakeElement; };
    // one nested paragraph
    const q = paras[10];
    const one = paintRendered(El(box), src, { start: at(src, q), end: at(src, q) + q.length }, "fc-hl") as unknown as FakeElement[];
    assert.equal(one.map((m) => m.textContent).join(""), q, what);
    sameNodes(ps.filter((p) => reads.has(p)), [ps[10]], what + ": only the paragraph holding the passage was read; read " + ps.filter((p) => reads.has(p)).map((p) => ps.indexOf(p)).join(",") + " where 10 was expected");
    assert.equal(holder(one[0]), ps[10]);
    // several: the run from the first mark's paragraph to the last mark's, none before or after
    reads.clear();
    const many = paintRendered(El(box), src, { start: at(src, paras[20]), end: at(src, paras[22]) + paras[22].length }, "fc-hl") as unknown as FakeElement[];
    assert.ok(many.length >= 3, what);
    sameNodes(ps.filter((p) => reads.has(p)), ps.slice(20, 23), what + ": the paragraphs between the two ends and no other; read " + ps.filter((p) => reads.has(p)).map((p) => ps.indexOf(p)).join(",") + " where 20..22 were expected");
  }
});

// ── the Slice 5 review, round 3 ──────────────────────────────────────────────────────────────────

/** A DOM built from HTML written by hand, as the browser's parser and the sanitizer leave it (for a shape the stand-in's parser does
 *  not model: a start tag's implied end tags). */
function domOf(html: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, html)) box.appendChild(n);
  return box;
}
/** A selection over a passage's first two and last two words (a passage a paint may have split over several text nodes), mapped. */
const mapWords = (box: FakeElement, src: string, text: string): MapResult => { const w = text.split(" "); return mapSpan(box, src, w.slice(0, 2).join(" "), w.slice(-2).join(" ")); };
const mapsWholeWords = (box: FakeElement, src: string, text: string): void => {
  const r = ok(mapWords(box, src, text), text);
  assert.deepEqual(r.range, { start: at(src, text), end: at(src, text) + text.length }, text + ": its own offsets");
};

test("a comment on a wrapper's own leftover, a `<details>` summary, a centred div's lead line, a README banner's heading and tagline, paints in Rendered (HIGH, the review's round 3: the fallback's scope held the wrapper AND the leftover the block owns beside it, so the hay counted the passage twice against the block's rendering once and the count guard refused; main had painted each); the nested paragraph still paints", () => {
  const DET = "Intro 001 alpha.\n\n<details><summary>Sum 002 charlie.</summary>\n\nPara 003 delta echo.\n\n</details>\n\nAfter 004 foxtrot.\n";
  assert.deepEqual(paintedIn(buildRendered(DET), DET, "Sum 002 charlie.", "Sum 002 charlie."), ["Sum 002 charlie."], "the summary (was nothing)");
  const TWO_LINE = "Intro 001 alpha.\n\n<details>\n<summary>Click to expand</summary>\n\nHidden 003 text here.\n\n</details>\n\nAfter 004 foxtrot.\n";
  assert.deepEqual(paintedIn(buildRendered(TWO_LINE), TWO_LINE, "Click to expand", "Click to expand"), ["Click to expand"], "the two-line details' summary");
  const LEAD = "Intro 001 alpha.\n\n<div align=\"center\">Lead 002 bravo.\n\nPara 003 delta echo.\n\n</div>\n\nAfter 004 foxtrot.\n";
  assert.deepEqual(paintedIn(buildRendered(LEAD), LEAD, "Lead 002 bravo.", "Lead 002 bravo."), ["Lead 002 bravo."], "the lead text (was nothing)");
  const BANNER = "<div align=\"center\"><img src=\"logo.png\" alt=\"logo\"><h1>Project</h1><p>A tagline here.</p>\n\nIntro 002 text.\n\n</div>\n\nAfter 003 foxtrot.\n";
  assert.deepEqual(paintedIn(buildRendered(BANNER), BANNER, "A tagline here.", "A tagline here."), ["A tagline here."], "the banner's tagline (was nothing)");
  assert.deepEqual(paintedIn(buildRendered(BANNER), BANNER, "Project", "Project"), ["Project"], "the banner's heading");
  assert.deepEqual(paintedIn(buildRendered(BANNER), BANNER, "Intro 002 text.", "Intro 002 text."), ["Intro 002 text."], "the nested paragraph still paints");
  assert.deepEqual(paintedIn(buildRendered(DET), DET, "Para 003 delta echo.", "Para 003 delta echo."), ["Para 003 delta echo."]);
});

test("the run check reads a comment's mark over an unwrapped element's hoisted text as that text: a comment spanning from the paragraph before a `<form>Lead` into its nested paragraph paints, and after the paint every passage still maps (the review's round 3: the read accepted a Text node alone, so the re-analysis met the top-level `<mark>` where the text was expected, no end confirmed, and the dropped `<input>` block before took every node, every later selection refused as an HTML block); a comment over part of the lead splits the text, and the run reads the pieces", () => {
  const HOIST = "Intro 001 alpha bravo.\n\n<input type=\"text\">\n\nPara 003 delta echo.\n\n<form>Lead 004 foxtrot.\n\nPara 005 golf hotel.\n\nPara 006 india juliet. </form>\n\nAfter 007 kilo lima.\n\nAfter 008 mike november.";
  const PASSAGES = ["Para 003 delta echo.", "Para 005 golf hotel.", "Para 006 india juliet.", "After 007 kilo lima.", "After 008 mike november."];
  let box = buildRendered(HOIST);
  for (const t of PASSAGES) mapsWholeWords(box, HOIST, t);
  const span = { start: at(HOIST, "delta echo."), end: at(HOIST, "Para 005") + "Para 005".length };
  let marks = paintRendered(El(box), HOIST, span, "fc-hl") as unknown as FakeElement[] | null;
  assert.deepEqual((marks || []).map((m) => m.textContent.trim()), ["delta echo.", "Lead 004 foxtrot.", "Para 005"], "the span paints across the hoisted lead");
  assert.ok(box.childNodes.some((n) => n instanceof FakeElement && n.tagName === "MARK"), "the lead's mark is a top-level node");
  for (const t of PASSAGES) mapsWholeWords(box, HOIST, t);
  assert.deepEqual(tagsOf(box, HOIST, blockAt(HOIST, "<form>")), ["MARK"], "the form block owns the mark over its hoisted text");
  // a comment over part of the lead: the text node splits around the mark, and the run reads the run of pieces as the block's text
  box = buildRendered(HOIST);
  marks = paintRendered(El(box), HOIST, { start: at(HOIST, "004 foxtrot"), end: at(HOIST, "004 foxtrot") + 3 }, "fc-hl") as unknown as FakeElement[] | null;
  assert.deepEqual((marks || []).map((m) => m.textContent), ["004"]);
  for (const t of PASSAGES) mapsWholeWords(box, HOIST, t);
});

test("an html `<p>` left open followed by html blocks whose tags do not close a `<p>` (`<br>`, `<img>`, `<span class=\"w\">`): the parser nests them inside the open `<p>`, the pairing gives them no top-level node, and every paragraph after maps, a later top-level `<img>` block owning its own picture (the review's round 3, a regression from main: the `<img>` block's forward scan found the later picture, refused every nearer end, and the `<p>`'s block took the paragraphs between, all four refused as an HTML block)", () => {
  const OPENP = "<p>Lead 002 charlie.\n\n<br>\n\n<img src=\"a.png\">\n\n<span class=\"w\">\n\nPara 003 delta echo.\n\nPara 004 foxtrot golf.\n\n<img src=\"b.png\">\n\nAfter 005 hotel india.\n\nAfter 006 juliet kilo.\n";
  const box = buildRendered(OPENP);
  assert.deepEqual(kidsOf(box).map((k) => tagOf(k) + "[" + kidsOf(k).map(tagOf).join(",") + "]"), ["P[BR,IMG,SPAN.w]", "P[]", "P[]", "IMG[]", "P[]", "P[]"], "the stand-in nests the inline-level blocks in the open p, as the browser does");
  for (const t of ["Para 003 delta echo.", "Para 004 foxtrot golf.", "After 005 hotel india.", "After 006 juliet kilo."]) mapsWhole(box, OPENP, t);
  assert.deepEqual(tagsOf(box, OPENP, blockAt(OPENP, "<p>Lead")), ["P"], "the open p's block: its one element");
  for (const head of ["<br>", "<img src=\"a.png\">", "<span class"]) assert.deepEqual(tagsOf(box, OPENP, blockAt(OPENP, head)), [], head + ": nested in the p, no top-level node");
  assert.deepEqual(tagsOf(box, OPENP, blockAt(OPENP, "<img src=\"b.png\">")), ["IMG"], "the later picture is its own block's");
  assert.match(bad(mapText(box, OPENP, "Lead 002 charlie."), "the p's own text").reason, /an HTML block/);
  // the same with a markdown paragraph closing the p at once: as before
  const CLOSED = "<p>Lead 002 charlie.\n\nPara 003 delta echo.\n\n<img src=\"b.png\">\n\nAfter 005 hotel india.\n";
  const box2 = buildRendered(CLOSED);
  for (const t of ["Para 003 delta echo.", "After 005 hotel india."]) mapsWhole(box2, CLOSED, t);
});

test("a stray `</p>` block after an html `<p>` left open closes that p and mints nothing; a second one mints the parser's empty `<p>`; and an image paragraph's `<p>` is not that empty `<p>` (it holds an element), so the run confirms at the right end and the heading, the paragraph and the passage after the picture all map (the review's round 3, a regression from main: every `</p>` was read as minting, the image paragraph's `<p>` passed for the minted one, and the first `</p>` block took every block up to the picture)", () => {
  const TWO = "Intro 001 alpha bravo.\n\n<p>Lead 002 charlie.\n\n</p>\n\n</p>\n\n## Head 003 delta.\n\nPara 004 echo foxtrot.\n\n![pic](pic.png)\n\nAfter 005 golf hotel.";
  let box = buildRendered(TWO);
  assert.deepEqual(kidsOf(box).map(tagOf), ["P", "P", "P", "H2", "P", "P", "P"], "the first </p> closes the open p; the second mints an empty <p>");
  for (const t of ["Head 003 delta.", "Para 004 echo foxtrot.", "After 005 golf hotel."]) mapsWhole(box, TWO, t);
  assert.deepEqual(tagsOf(box, TWO, blockAt(TWO, "</p>")), [], "the closer of the open p owns nothing");
  assert.deepEqual(tagsOf(box, TWO, sourceBlockSpans(TWO).findIndex((sp) => sp.start === TWO.lastIndexOf("</p>"))), ["P"], "the stray closer owns the minted <p>");
  assert.deepEqual(tagsOf(box, TWO, blockAt(TWO, "![pic]")), ["P"], "the picture's paragraph owns its own <p>");
  const ONE = TWO.replace("</p>\n\n</p>", "</p>");
  box = buildRendered(ONE);
  for (const t of ["Head 003 delta.", "Para 004 echo foxtrot.", "After 005 golf hotel."]) mapsWhole(box, ONE, t);
  // a README shape: a centred p of pictures, closed by its own block, then prose and a picture paragraph
  const README = "<p align=\"center\">\n<img src=\"logo.png\" alt=\"\">\n\n</p>\n\n## Head 003 delta.\n\nPara 004 echo foxtrot.\n\n![pic](pic.png)\n\nAfter 005 golf hotel.\n";
  box = buildRendered(README);
  for (const t of ["Head 003 delta.", "Para 004 echo foxtrot.", "After 005 golf hotel."]) mapsWhole(box, README, t);
});

test("a wrapper whose raw holds a closed child of the SAME tag as the next html block's element (`<div align=\"center\"><div>Lead</div>` then `<div class=\"in\">`; `<span>Lead</span>` then `<span class=\"w\">`): the raw's own children are the block's and read past, so the inner block takes its own element and the nested and following paragraphs map (the review's round 3, a regression from round 1: the inner block took the leftover, its real element fell to the paragraph after the wrapper as a mismatch, and the last paragraph was no block's); round 1's recorded edge, `<div><p>Lead</p>` then an html `<p>Alpha</p>`, now pairs the leftover to the wrapper's block", () => {
  const SAME = "Intro 001 alpha bravo.\n\n<div align=\"center\"><div>Lead 002 charlie.</div>\n\n<div class=\"in\">\n\nPara 003 delta echo.\n\n</div>\n\n</div>\n\nAfter 004 foxtrot golf.\n\nAfter 005 hotel india.";
  let box = buildRendered(SAME);
  for (const t of ["Para 003 delta echo.", "After 004 foxtrot golf.", "After 005 hotel india."]) mapsWhole(box, SAME, t);
  assert.deepEqual(elems(box, SAME, blockAt(SAME, "<div align")), ['DIV:"Lead 002 charlie."', 'DIV:"Lead 002 charlie."'], "the outer block: its wrapper and the leftover div");
  assert.deepEqual(elems(box, SAME, blockAt(SAME, "<div class=\"in\">")), ['DIV.in:"Para 003 delta"'], "the inner block: its own element (was the leftover)");
  assert.equal(owner(box, SAME, kidsOf(box)[kidsOf(box).length - 1]), blockAt(SAME, "After 005"), "the last paragraph is its block's");
  const SPAN = "Intro 001 alpha bravo.\n\n<div align=\"center\"><span>Lead 002 charlie.</span>\n\n<span class=\"w\">\n\nPara 003 delta echo.\n\n</span>\n\n</div>\n\nAfter 004 foxtrot golf.\n\nAfter 005 hotel india.";
  box = buildRendered(SPAN);
  for (const t of ["After 004 foxtrot golf.", "After 005 hotel india."]) mapsWhole(box, SPAN, t);
  const EDGE = "<div><p>Lead</p>\n\n<p>Alpha</p>\n\nAfter one.\n\nAfter two.\n";
  box = buildRendered(EDGE);
  for (const t of ["After one.", "After two."]) mapsWhole(box, EDGE, t);
  assert.deepEqual(elems(box, EDGE, blockAt(EDGE, "<div>")), ['DIV:"Lead Alpha After"', 'P:"Lead"'], "the wrapper keeps its own <p>");
  assert.deepEqual(elems(box, EDGE, blockAt(EDGE, "<p>Alpha")), ['P:"Alpha"'], "the html <p> block takes its own element");
});

test("a closer the parser ignores inside an open `<p>` (`</label>`, `</legend>`, `</option>`) closes nothing and mints nothing: after a `<label>` opened as its own block and closed inline on a paragraph, an html `<p></p>` block owns its own empty element and the paragraphs after it map (the review's round 3, a regression from main: the closer was read as minting, the pairing stepped over the `<p></p>` block's element as the minted one, and that block took the next paragraph); a `</div>` closed inline mints as before", () => {
  for (const tag of ["label", "legend", "option"]) {
    const IGN = `Intro 001 alpha bravo.\n\n<${tag}>\n\nPara 003 delta echo. </${tag}>\n\n<p></p>\n\nAfter 005 hotel india.\n\nAfter 006 juliet kilo.\n`;
    const box = buildRendered(IGN);
    assert.deepEqual(kidsOf(box).map(tagOf), ["P", "P", "P", "P", "P"], tag + ": the stand-in ignores the closer inside the p, unwraps the element, and mints no <p>");
    for (const t of ["Para 003 delta echo.", "After 005 hotel india.", "After 006 juliet kilo."]) mapsWhole(box, IGN, t);
    assert.deepEqual(elems(box, IGN, blockAt(IGN, "<p></p>")), ['P:""'], tag + ": the html <p></p> block owns its own element");
  }
  const DIV = "Intro 001 alpha bravo.\n\n<div>\n\nPara 003 delta echo. </div>\n\n<p></p>\n\nAfter 005 hotel india.\n\nAfter 006 juliet kilo.\n";
  const box = buildRendered(DIV);
  for (const t of ["Para 003 delta echo.", "After 005 hotel india.", "After 006 juliet kilo."]) mapsWhole(box, DIV, t);
  assert.equal(kidsOf(box).filter((k) => k.tagName === "P" && k.childNodes.length === 0).length, 2, "the minted <p> and the block's own");
});

test("a block whose scan took nothing and whose run no end confirms hands the nodes back at the next html block's own element, not at the document's end: a `<button>` opened as its own block, whose paragraph's own `<button>` start tag closes it (the parser's implied end tags, the DOM here as the browser and the sanitizer leave it), loses the paragraphs up to the next html block and no more, and every paragraph after that block maps (the review's round 3, a regression from main: everything to the end was refused as an HTML block)", () => {
  const BTN = "Intro one here.\n\n<button>\n\n<button>probe xray quebec</button>\n\nNovember table bravo.\n\nLast line kilo.\n\n<div>marker</div>\n\nAfter one lima.\n\nAfter two mike.\n";
  const box = domOf("<p>Intro one here.</p>\n<p></p>probe xray quebec<p></p>\n<p>November table bravo.</p>\n<p>Last line kilo.</p>\n<div>marker</div>\n<p>After one lima.</p>\n<p>After two mike.</p>\n");
  for (const t of ["After one lima.", "After two mike."]) mapsWhole(box, BTN, t);
  assert.deepEqual(elems(box, BTN, blockAt(BTN, "<div>marker")), ['DIV:"marker"'], "the next html block owns its own element (before: nothing)");
  assert.deepEqual(elems(box, BTN, blockAt(BTN, "<button>")), ['P:""', 'P:""', 'P:"November table bravo."', 'P:"Last line kilo."'], "the button block's run ends at the marker (the opener is the first block starting so)");
  for (const t of ["November table bravo.", "Last line kilo."]) assert.match(bad(mapText(box, BTN, t), t).reason, /an HTML block/, t + ": inside the swallowed run, refused at the button's block");
});

test("a whole-paragraph selection right before a bare text node the parser hoisted (an unwrapped `<option>`'s text, a dropped `<td>`'s) maps: an end boundary is placed by the last character it selects, not by the node that starts where it ends (main's rule, and round 2's: the end read as the next node at offset 0, a refused block's, and the selection was refused as touching it while one stopping a character short mapped; the same after a comment's mark absorbed the whitespace node before the hoisted text)", () => {
  const OPT = "Para 001 bravo mike delta.\n\n<option>Opt 002 x.</option>\n\n## Head\n\nPara 003 hotel india.\n";
  const box = buildRendered(OPT);
  const t1 = allText(box).find((t) => t.data === "Para 001 bravo mike delta.")!;
  const whole = ok(mapRenderedSelection(sel({ node: t1, offset: 0 }, { node: t1, offset: t1.data.length }), El(box), OPT), "the whole paragraph, ending at its text's end");
  assert.equal(whole.quote, "Para 001 bravo mike delta.");
  const atP = ok(mapRenderedSelection(sel({ node: t1, offset: 0 }, { node: t1.parentNode!, offset: 1 }), El(box), OPT), "the whole paragraph, ending at its element's end");
  assert.equal(atP.quote, "Para 001 bravo mike delta.");
  assert.equal(ok(mapRenderedSelection(sel({ node: t1, offset: 9 }, { node: t1, offset: t1.data.length }), El(box), OPT), "the tail").quote, "bravo mike delta.");
  assert.match(bad(mapText(box, OPT, "Opt 002 x."), "the hoisted text itself").reason, /an HTML block/);
});
