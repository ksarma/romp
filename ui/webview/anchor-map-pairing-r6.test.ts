// The block pairing across an html wrapper, the Slice 5 review's round 6 (anchor-map.ts analyzeRendered: topTags, pastKids,
// nextAnchor, runFits), beside anchor-map-wrappers.test.ts's rounds 1 to 5: an element the sanitizer unwraps (a `<button>`, a
// `<form>`, a `<label>`, a `<fieldset>`) inside an open wrapper is listed as its own children, so a badge picture or a `<b>` it
// held no longer stands unread at k before the depth-1 wrapper; the resume of a swallowed run at the next html block's element is
// the first node of its tag from which the blocks after it line up through to the content's end, so an html `<p>Go</p>` after the
// run takes its own `<p>` and not a swallowed paragraph's, and an html `<p></p>` its own and not the run's minted one; and the
// run check through to the end reads one mismatch in a confirmed tail as the loop pairs it, with its node. Driven over the
// viewer's Rendered shape rebuilt as anchor-map-wrappers.test.ts rebuilds it (the DOM stand-in below is that file's, byte for
// byte: marked's output parsed as a browser nests it, the sanitizer's drops and unwraps stood in for), or over a DOM written by
// hand where the shape needs a parser rule the stand-in has not (a `<button>` start tag's implied end tags), as that file's
// domOf does. Every case fails over a git archive of 8924fa17e's module, the tree the round reviewed, unless its comment says it is
// a control. Fixtures are synthetic.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import { applyMdConfig, resolveWikilink } from "./md-config";
import { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex, renderedBlockElements, renderedBlockWrappers, paintRendered, type SelLike, type MapResult } from "./anchor-map";
import { hideEdges } from "../test-dom-shim";

applyMdConfig();

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser (anchor-map-wrappers.test.ts's) ──
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
      // document, which the browser legs cover; the stand-in keeps the standards reading for it). The set is anchor-map.ts's
      // CLOSES_P (the review's round 4: center, dir, li, dd and dt among them; a `<button>` start tag closes no p)
      if (/^(?:address|article|aside|blockquote|center|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|h[1-6]|header|hgroup|hr|li|listing|main|menu|nav|ol|p|plaintext|pre|search|section|summary|table|ul|xmp)$/i.test(m[1])) {
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
/** A DOM built from HTML written by hand, as the browser's parser and the sanitizer leave it (for a shape the stand-in's parser does
 *  not model: a start tag's implied end tags). */
function domOf(html: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, html)) box.appendChild(n);
  return box;
}

test("an element the sanitizer unwraps inside an open wrapper (`<button>`, `<form>`, `<label>`, `<fieldset>`) is read as its own children, which the unwrap leaves where it stood (topTags flattens its kids into the wrapper's): with a badge picture in a `<button>` or a `<b>`, a `<p>` or a lead text and a `<b>` in a `<form>`, a `<label>` or a `<fieldset>` before the depth-1 wrapper, the nested paragraph and the paragraph after the wrapper map to their own offsets, the opener's block holds its two wrappers and the nested paragraph's `<p>` is its own block's, with a `<details><summary>` as the inner wrapper too (the review's round 6, a regression against 701728eae, and against main for the `<button><img>` badge shape: the unwrapped kid was listed by name and read as a text node, so the IMG or B the unwrap left stayed at k, the depth-1 rule found no inner element there, the holder was dropped, the nested paragraph took the leftover element as a mismatch and the paragraph after was no block's); a kept element kid and a text-only unwrapped kid still read as before (controls)", () => {
  const IMG = '<img src="badge.svg" alt="b">';
  const A = "Alpha para one.", AFTER = "After para two.";
  const four = (opener: string, closer: string): string => `${opener}\n\n${A}\n\n${closer}\n\n${AFTER}\n`;
  // [what, the source, the opener's two wrappers]
  const SHAPES: Array<[string, string, string[]]> = [
    ["a button holding a badge picture (the README header shape)", four(`<div align="center"><button>${IMG}</button><div>`, "</div></div>"), ["DIV", "DIV"]],
    ["a form holding a b", four("<div><form><b>x</b></form><div>", "</div></div>"), ["DIV", "DIV"]],
    ["a label holding a b", four("<div><label><b>x</b></label><div>", "</div></div>"), ["DIV", "DIV"]],
    ["a form holding a p", four("<div><form><p>Lead words.</p></form><div>", "</div></div>"), ["DIV", "DIV"]],
    ["a fieldset holding a legend and a b", four("<div><fieldset><legend>L</legend><b>x</b></fieldset><div>", "</div></div>"), ["DIV", "DIV"]],
    ["a form holding a lead text and a b", four("<div><form>Lead <b>x</b></form><div>", "</div></div>"), ["DIV", "DIV"]],
    ["a button holding a badge before a details with a summary", four(`<div><button>${IMG}</button><details><summary>S</summary>`, "</details></div>"), ["DIV", "DETAILS"]],
    ["a select with two options before the inner div (two text kids)", four("<div><select><option>One</option><option>Two</option></select><div>", "</div></div>"), ["DIV", "DIV"]],
    ["a textarea before the inner div (its content stays as text, references decoded)", four("<div><textarea>typed words &amp; more</textarea><div>", "</div></div>"), ["DIV", "DIV"]],
    ["a kept element kid (a control)", four('<div align="center"><div>Lead</div><div>', "</div></div>"), ["DIV", "DIV"]],
    ["a text-only unwrapped kid (a control)", four("<div><form>words.</form><div>", "</div></div>"), ["DIV", "DIV"]],
  ];
  for (const [what, src, two] of SHAPES) {
    const box = buildRendered(src);
    for (const t of [A, AFTER]) mapsWhole(box, src, t);
    assert.deepEqual(wraps(box, src, 0), two, what + ": the opener's block holds its two wrappers");
    assert.equal(owner(box, src, find(box, "P", A)), blockAt(src, A), what + ": the nested paragraph's <p> is its own block's");
    assert.deepEqual(elems(box, src, blockAt(src, A)), [`P:"${A}"`], what + ": the nested paragraph's block owns its one <p>");
    assert.equal(owner(box, src, kidsOf(box)[kidsOf(box).length - 1]), blockAt(src, AFTER), what + ": the paragraph after the wrapper is its block's");
  }
  // a top-level unwrapped block still leaves its text to the resync as before (a control: the wrappers test's form shapes)
  const TOP = "Intro one.\n\n<form>Lead text here.\n\nAlpha para one.\n\n</form>\n\nAfter para two.\n";
  const box = buildRendered(TOP);
  for (const t of ["Alpha para one.", "After para two."]) mapsWhole(box, TOP, t);
});

test("the resume of a swallowed run at the next html block's element is the first node of its tag from which the blocks AFTER the block line up through to the content's end, past the nodes the block's own scan takes (nextAnchor, scanTake, runFits with toEnd): after a `<button>` opener whose paragraph's own `<button>` closes it, an html `<p>Final para three.</p>` block takes its OWN `<p>`, not the first swallowed paragraph's, so a selection in the html block's rendered copy is refused as an HTML block, the markdown paragraph `Final para three.` after it maps to its own offsets from its own `<p>`, and the swallowed paragraphs stay the button's (the review's round 6: the first `<p>` from k was taken by tag alone, the html block's scan then owned the run and resynced at its own `<p>`, the paragraph after paired with the html copy, a selection in the html copy mapped to the paragraph's offsets, so a comment made there was stored on the wrong passage, and the paragraph's own `<p>` was no block's; present at 701728eae and 50b19bfdb, main refused both copies); an html `<p>Other words.</p>` and a `<div>` in the block's place as before (controls)", () => {
  const FINAL = "Final para three.";
  const S8 = `<button>\n\nAlpha <button>x</button>\n\nNov para one.\n\n<p>${FINAL}</p>\n\n${FINAL}\n`;
  const box = domOf(`<p>Alpha </p>x<p></p>\n<p>Nov para one.</p>\n<p>${FINAL}</p>\n<p>${FINAL}</p>\n`);
  const htmlCopy = kidsOf(box)[3], mdCopy = kidsOf(box)[4];   // the elements: Alpha's <p>, the minted <p>, Nov's, the html block's, the paragraph's (the bare `x` is a text node)
  assert.equal(owner(box, S8, htmlCopy), blockAt(S8, "<p>"), "the html block owns its own <p> (before: Alpha's)");
  assert.deepEqual(elems(box, S8, blockAt(S8, "<p>")), [`P:"${FINAL}"`]);
  assert.equal(owner(box, S8, mdCopy), sourceBlockSpans(S8).length - 1, "the markdown paragraph, the last block, owns its own <p> (before: no block's)");
  assert.deepEqual(elems(box, S8, blockAt(S8, "<button>")), ['P:"Alpha"', 'P:""', 'P:"Nov para one."'], "the button block's run ends at the html block's own element (before: the html block owned these)");
  assert.match(bad(mapText(box, S8, FINAL, 0), "the html copy").reason, /an HTML block/, "a selection in the html block's rendered copy is refused (before: it mapped to the markdown paragraph's offsets)");
  mapsWhole(box, S8, FINAL, 1);
  assert.match(bad(mapText(box, S8, "Nov para one."), "inside the run").reason, /an HTML block/);
  // a comment stored on the markdown paragraph paints on its own rendered copy
  const md2 = at(S8, FINAL, 1);
  const marks = paintRendered(El(box), S8, { start: md2, end: md2 + FINAL.length }, "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(marks && marks.length === 1, "one mark");
  assert.equal(marks![0].parentNode, mdCopy, "on the markdown paragraph's <p> (before: on the html copy)");
  // controls: distinct text in the html `<p>`, and a `<div>` carrying the repeated text
  const S8B = `<button>\n\nAlpha <button>x</button>\n\nNov para one.\n\n<p>Other words.</p>\n\n${FINAL}\n`;
  const boxB = domOf(`<p>Alpha </p>x<p></p>\n<p>Nov para one.</p>\n<p>Other words.</p>\n<p>${FINAL}</p>\n`);
  mapsWhole(boxB, S8B, FINAL);
  assert.match(bad(mapText(boxB, S8B, "Other words."), "the html block's text").reason, /an HTML block/);
  assert.deepEqual(elems(boxB, S8B, blockAt(S8B, "<p>")), ['P:"Other words."'], "the html block owns its own <p> (before: the run's three and its own)");
  const S8A = `<button>\n\nAlpha <button>x</button>\n\nNov para one.\n\n<div>${FINAL}</div>\n\n${FINAL}\n`;
  const boxA = domOf(`<p>Alpha </p>x<p></p>\n<p>Nov para one.</p>\n<div>${FINAL}</div>\n<p>${FINAL}</p>\n`);
  mapsWhole(boxA, S8A, FINAL, 1);
  assert.match(bad(mapText(boxA, S8A, FINAL, 0), "the div's copy").reason, /an HTML block/);
});

test("an html `<p></p>` block after a `<button>` opener's swallowed run takes its OWN empty `<p>`, not the run's first parser-minted one, so the swallower (the `<button>` block, or a `<tr><td>` note the parser drops before it) owns the run, the `<p></p>` block owns its one element, the run's paragraphs are refused at the swallower's offset, before the passage, and the Raw offer's search from that offset (file-comments.ts rawTarget) lands on the passage, on the run's own copy when the intro repeats its words (the review's round 6: the first empty `<p>` from k was taken, the run's minted one, so the `<p></p>` block owned the run's elements and its own, the refusal carried the `<p></p>` block's offset, after the passage, the search from there missed, and with the words repeated earlier the fall-back from the file's start preselected the intro's copy); the paragraphs after the `<p></p>` map, as before", () => {
  const NOV = "November table bravo.", LAST = "Last line kilo.", AFTER = "After one lima.";
  const RUN = `<button>\n\n<button>probe</button>\n\n${NOV}\n\n${LAST}\n\n`;
  const RUN_DOM = `<p></p>probe<p></p>\n<p>${NOV}</p>\n<p>${LAST}</p>\n`;
  const check = (what: string, src: string, box: FakeElement, swallower: string, novCopy: number): void => {
    mapsWhole(box, src, AFTER);
    const kids = kidsOf(box);
    const own = kids[kids.length - 2];
    assert.equal(own.tagName + own.textContent, "P", what + ": the element before the last paragraph is the html block's empty <p>");
    assert.equal(owner(box, src, own), blockAt(src, "<p></p>"), what + ": the <p></p> block owns its own element (before: the run's first minted <p>)");
    assert.deepEqual(elems(box, src, blockAt(src, "<p></p>")), ['P:""'], what + ": and nothing else (before: the run's four and its own)");
    assert.deepEqual(elems(box, src, blockAt(src, swallower)), ['P:""', 'P:""', `P:"${NOV}"`, `P:"${LAST}"`], what + ": the swallower's block owns the run (before: nothing)");
    for (const t of [NOV, LAST]) {
      const r = bad(mapText(box, src, t, t === NOV ? novCopy : 0), what + ": " + t + ", inside the run");
      assert.match(r.reason, /an HTML block/, what + ": " + t);
      assert.equal(r.blockStartOffset, at(src, swallower), what + ": refused at the swallower's offset (before: the <p></p> block's, after the passage)");
      const want = at(src, t, t === NOV ? novCopy : 0);
      assert.equal(src.indexOf(t, r.blockStartOffset as number), want, what + ": the Raw offer's search from the refusal's offset lands on the run's copy of " + t);
    }
  };
  const A = `Intro one here.\n\n${RUN}<p></p>\n\n${AFTER}\n`;
  check("a button opener", A, domOf("<p>Intro one here.</p>\n" + RUN_DOM + "<p></p>\n<p>" + AFTER + "</p>\n"), "<button>", 0);
  const B = `Intro one here.\n\n<tr><td>xray golf juliet.</td></tr>\n\n${RUN}<p></p>\n\n${AFTER}\n`;
  check("a dropped note before the opener", B, domOf("<p>Intro one here.</p>\nxray golf juliet.\n" + RUN_DOM + "<p></p>\n<p>" + AFTER + "</p>\n"), "<tr>", 0);
  // the intro repeats the passage: the search from the swallower's offset lands on the run's copy, not the intro's
  const C = `${NOV}\n\n${RUN}<p></p>\n\n${AFTER}\n`;
  check("the intro repeating the passage", C, domOf(`<p>${NOV}</p>\n` + RUN_DOM + "<p></p>\n<p>" + AFTER + "</p>\n"), "<button>", 1);
  // a `<div>marker</div>` in the `<p></p>`'s place bounds the run at its own element as before (a control: the wrappers test's shape)
  const D = `Intro one here.\n\n${RUN}<div>marker</div>\n\n${AFTER}\n`;
  const boxD = domOf("<p>Intro one here.</p>\n" + RUN_DOM + "<div>marker</div>\n<p>" + AFTER + "</p>\n");
  mapsWhole(boxD, D, AFTER);
  assert.deepEqual(elems(boxD, D, blockAt(D, "<button>")), ['P:""', 'P:""', `P:"${NOV}"`, `P:"${LAST}"`]);
  assert.equal(bad(mapText(boxD, D, NOV), "inside the run").blockStartOffset, at(D, "<button>"));
});

test("the run check through to the content's end (runFits with toEnd, the resume after a block of closing tags alone) reads ONE block that does not fit in a tail two blocks have confirmed as the pairing loop pairs it, with its node: after a `<button>` opener's run and a `</center>` alone, a tail whose third paragraph the sanitizer shortened (`Weird <style>x{}</style> line.`, rendered `Weird  line.`) or whose LAST paragraph it did has the other tail paragraphs mapping to their own offsets and the shortened one alone refused as a mismatch, the button's block owning the run's four elements (the review's round 6, the round-5 recheck's residual: the run check returned false at the mismatch for every candidate end, no bound was found, the button block owned every element to the document's end and all four tail paragraphs were refused as an HTML block, where 701728eae and main mapped the three); a mismatch with no closer before it is refused alone, as before (a control)", () => {
  const NOV = "November tango sierra.", LAST = "Last kilo lima.";
  const NOTE = "Note tango sierra.", FINAL = "Final para after tail.", WEIRD = "Weird <style>x{}</style> line.", AFTER = "After all done.";
  const HEAD = `Intro alpha bravo charlie.\n\n<button>\n\n<button>probe xray</button>\n\n${NOV}\n\n${LAST}\n\n</center>\n\n`;
  const HEAD_DOM = `<p>Intro alpha bravo charlie.</p>\n<p></p>probe xray<p></p>\n<p>${NOV}</p>\n<p>${LAST}</p>\n`;
  const P = (t: string): string => `<p>${t}</p>\n`;
  const WEIRD_DOM = P("Weird  line.");
  // [what, the tail's blocks, the tail's DOM]
  const TAILS: Array<[string, string[], string]> = [
    ["the third tail paragraph shortened", [NOTE, FINAL, WEIRD, AFTER], P(NOTE) + P(FINAL) + WEIRD_DOM + P(AFTER)],
    ["the last tail paragraph shortened", [NOTE, FINAL, AFTER, WEIRD], P(NOTE) + P(FINAL) + P(AFTER) + WEIRD_DOM],
    ["a fourth block shortened after three", [NOTE, FINAL, AFTER, WEIRD, "Very last words."], P(NOTE) + P(FINAL) + P(AFTER) + WEIRD_DOM + P("Very last words.")],
  ];
  for (const [what, tail, tailDom] of TAILS) {
    const src = HEAD + tail.join("\n\n") + "\n";
    const box = domOf(HEAD_DOM + tailDom);
    for (const t of tail) {
      if (t === WEIRD) assert.match(bad(mapText(box, src, "Weird"), what + ": the shortened paragraph").reason, /does not match the file/, what + ": the shortened paragraph is refused as a mismatch (before: as an HTML block)");
      else mapsWhole(box, src, t);
    }
    assert.deepEqual(elems(box, src, blockAt(src, "<button>")), ['P:""', 'P:""', `P:"${NOV}"`, `P:"${LAST}"`], what + ": the button block's run ends at the closer (before: at the document's end)");
    assert.equal(bad(mapText(box, src, "Weird"), what).blockStartOffset, at(src, WEIRD), what + ": the mismatch's refusal carries its own offset");
    for (const t of [NOV, LAST]) assert.match(bad(mapText(box, src, t), t).reason, /an HTML block/, what + ": " + t + " inside the run");
  }
  // no opener and no closer: the shortened paragraph is a mismatch on its own and its neighbours map (a control)
  const PLAIN = `Intro alpha bravo charlie.\n\n${NOTE}\n\n${FINAL}\n\n${WEIRD}\n\n${AFTER}\n`;
  const boxP = domOf(P("Intro alpha bravo charlie.") + P(NOTE) + P(FINAL) + WEIRD_DOM + P(AFTER));
  for (const t of [NOTE, FINAL, AFTER]) mapsWhole(boxP, PLAIN, t);
  assert.match(bad(mapText(boxP, PLAIN, "Weird"), "the mismatch").reason, /does not match the file/);
});

// ── the Slice 5 review, round 7 ──────────────────────────────────────────────────────────────────

test("an element the parser closes implicitly when an unwrapped element's end tag comes is listed among the wrapper's kids (topTags closes every element still open above the named one, each under the one below it, and a `</form>` removes the form alone): a `<p>` left open in a `<form>`, a `<button>`, a `<fieldset>` or a `<label>` (whose `</label>` the parser ignores; the `<div>` then closes the `<p>`, the same DOM), after a lead text and a `<b>`, and the `<option>`s of a `<select>` or its `<optgroup>`s written without their end tags, each before the depth-1 wrapper: the nested paragraph and the paragraph after map to their own offsets, the opener's block holds its two wrappers and the nested paragraph's `<p>` is its own block's; a `<form>` closed with a `<span>` still open leaves the span open, so the inner div nests in it and the opener's block holds three wrappers (the review's round 7, a regression against 701728eae: the flattening listed only the children closed with their own end tag, the `<p>` was discarded by the pop, the DOM held it where the depth-1 wrapper was expected, the holder was dropped, the nested paragraph was refused as a mismatch and the paragraph after could not be matched)", () => {
  const A = "Alpha para one.", AFTER = "After para two.";
  const four = (opener: string, closer: string): string => `${opener}\n\n${A}\n\n${closer}\n\n${AFTER}\n`;
  const SHAPES: Array<[string, string]> = [
    ["a form whose p its end tag closes", four('<div align="center"><form><p>Lead mp1</form><div>', "</div></div>")],
    ["a button whose p its end tag closes", four('<div align="center"><button><p>Lead mp1</button><div>', "</div></div>")],
    ["a fieldset whose p its end tag closes", four('<div align="center"><fieldset><p>Lead mp1</fieldset><div>', "</div></div>")],
    ["a label whose p the following div closes (the parser ignores the label's end tag)", four('<div align="center"><label><p>Lead mp1</label><div>', "</div></div>")],
    ["a form holding a lead text, a b and an open p", four('<div align="center"><form>Lead <b>x</b><p>Para mp1</form><div>', "</div></div>")],
    ["a form holding a lead text and an open p (the finder's shape)", four("<div><form>Lead<p>x</form><div>", "</div></div>")],
    ["a select whose options have no end tags", four('<div align="center"><select><option>a<option>b</select><div>', "</div></div>")],
    ["a select whose optgroups and options have no end tags", four('<div align="center"><select><optgroup><option>a<optgroup><option>b</select><div>', "</div></div>")],
    ["a form whose p is closed by name (round 6's control)", four('<div align="center"><form><p>Lead mp1</p></form><div>', "</div></div>")],
    ["a kept div whose p its end tag closes (a control)", four('<div align="center"><div><p>Lead mp1</div><div>', "</div></div>")],
  ];
  for (const [what, src] of SHAPES) {
    const box = buildRendered(src);
    for (const t of [A, AFTER]) mapsWhole(box, src, t);
    assert.deepEqual(wraps(box, src, 0), ["DIV", "DIV"], what + ": the opener's block holds its two wrappers");
    assert.equal(owner(box, src, find(box, "P", A)), blockAt(src, A), what + ": the nested paragraph's <p> is its own block's");
    assert.deepEqual(elems(box, src, blockAt(src, A)), [`P:"${A}"`], what + ": the nested paragraph's block owns its one <p>");
    assert.equal(owner(box, src, kidsOf(box)[kidsOf(box).length - 1]), blockAt(src, AFTER), what + ": the paragraph after the wrapper is its block's");
  }
  // `</form>` with a `<span>` still open: the parser removes the form and leaves the span, so the div opens inside it (a DOM by hand:
  // the stand-in's parser pops to the form as it does for every honoured end tag)
  const SPAN = four("<div><form>Lead<span>x</form><div>", "</div></div>");
  const boxS = domOf(`<div>Lead<span>x<div>\n<p>${A}</p>\n</div></span></div>\n<p>${AFTER}</p>\n`);
  for (const t of [A, AFTER]) mapsWhole(boxS, SPAN, t);
  assert.deepEqual(wraps(boxS, SPAN, 0), ["DIV", "SPAN", "DIV"], "the span left open by the form's end tag is the second wrapper");
  assert.equal(owner(boxS, SPAN, find(boxS, "P", A)), blockAt(SPAN, A));
});

test("the run check through to the content's end reads ONE block that does not fit before two confirmations as well, when the blocks after it line up from the node after its (runFits with toEnd, the lookahead): after a `<button>` opener's run and a `</center>` alone, a tail whose FIRST or SECOND paragraph the sanitizer shortened has the other tail paragraphs mapping to their own offsets and the shortened one alone refused as a mismatch, the button's block owning the run's four (the review's round 7: the mismatch returned false at every candidate before two confirmations, so the swallow ran to the document's end and all four tail paragraphs were refused as an HTML block, where main mapped the three when the shortened one was second); and nextAnchor's candidate after an html `<p>` block is confirmed the same way when the tail's first block is such a paragraph, so the html block takes its OWN `<p>` and the markdown copy after the shortened paragraph maps from its own (before: no candidate lined up, the first `<p>` from k stood, Alpha's, and every selection in the document was refused as unmatched; with the passage repeated inside the run, a selection in the FIRST rendered copy mapped to the tail copy's offsets); two shortened paragraphs before two confirmations still swallow (recorded)", () => {
  const NOV = "November tango sierra.", LAST = "Last kilo lima.";
  const NOTE = "Note tango sierra.", FINAL = "Final para after tail.", WEIRD = "Weird <style>x{}</style> line.", AFTER = "After all done.";
  const HEAD = `Intro alpha bravo charlie.\n\n<button>\n\n<button>probe xray</button>\n\n${NOV}\n\n${LAST}\n\n</center>\n\n`;
  const HEAD_DOM = `<p>Intro alpha bravo charlie.</p>\n<p></p>probe xray<p></p>\n<p>${NOV}</p>\n<p>${LAST}</p>\n`;
  const P = (t: string): string => `<p>${t}</p>\n`;
  const WEIRD_DOM = P("Weird  line.");
  const TAILS: Array<[string, string[], string]> = [
    ["the first tail paragraph shortened", [WEIRD, NOTE, FINAL, AFTER], WEIRD_DOM + P(NOTE) + P(FINAL) + P(AFTER)],
    ["the second tail paragraph shortened", [NOTE, WEIRD, FINAL, AFTER], P(NOTE) + WEIRD_DOM + P(FINAL) + P(AFTER)],
    ["the second of two shortened", [NOTE, WEIRD], P(NOTE) + WEIRD_DOM],
  ];
  for (const [what, tail, tailDom] of TAILS) {
    const src = HEAD + tail.join("\n\n") + "\n";
    const box = domOf(HEAD_DOM + tailDom);
    for (const t of tail) {
      if (t === WEIRD) assert.match(bad(mapText(box, src, "Weird"), what + ": the shortened paragraph").reason, /does not match the file/, what + ": the shortened paragraph is refused as a mismatch (before: as an HTML block)");
      else mapsWhole(box, src, t);
    }
    assert.deepEqual(elems(box, src, blockAt(src, "<button>")), ['P:""', 'P:""', `P:"${NOV}"`, `P:"${LAST}"`], what + ": the button block's run ends at the closer (before: at the document's end)");
    assert.equal(bad(mapText(box, src, "Weird"), what).blockStartOffset, at(src, WEIRD), what + ": the mismatch's refusal carries its own offset");
    for (const t of [NOV, LAST]) assert.match(bad(mapText(box, src, t), t).reason, /an HTML block/, what + ": " + t + " inside the run");
  }
  // two shortened paragraphs before two confirmations: no candidate lines up and the swallow runs to the end (recorded)
  const TWO = HEAD + [WEIRD, "Weird <style>y{}</style> too.", FINAL, AFTER].join("\n\n") + "\n";
  const boxT = domOf(HEAD_DOM + WEIRD_DOM + P("Weird  too.") + P(FINAL) + P(AFTER));
  assert.match(bad(mapText(boxT, TWO, FINAL), "two shortened").reason, /an HTML block/, "recorded: two unconfirmed mismatches in the tail still swallow it");
  // nextAnchor's candidate after an html `<p>` block, the tail's first block shortened (the finder's S5)
  const FINAL3 = "Final para three.";
  const S5 = `<button>\n\nAlpha <button>x</button>\n\nNov para one.\n\n<p>${FINAL3}</p>\n\n${WEIRD}\n\n${FINAL3}\n`;
  const box5 = domOf(`<p>Alpha </p>x<p></p>\n<p>Nov para one.</p>\n<p>${FINAL3}</p>\n${WEIRD_DOM}<p>${FINAL3}</p>\n`);
  const htmlCopy = kidsOf(box5)[3], mdCopy = kidsOf(box5)[5];
  assert.equal(owner(box5, S5, htmlCopy), blockAt(S5, "<p>"), "the html block owns its own <p> (before: Alpha's)");
  assert.deepEqual(elems(box5, S5, blockAt(S5, "<p>")), [`P:"${FINAL3}"`]);
  assert.equal(owner(box5, S5, mdCopy), sourceBlockSpans(S5).length - 1, "the markdown copy, the last block, owns its own <p> (before: no block's)");
  assert.deepEqual(elems(box5, S5, blockAt(S5, "<button>")), ['P:"Alpha"', 'P:""', 'P:"Nov para one."'], "the button block's run ends at the html block's own element");
  mapsWhole(box5, S5, FINAL3, 1);
  assert.match(bad(mapText(box5, S5, FINAL3, 0), "the html copy").reason, /an HTML block/);
  assert.match(bad(mapText(box5, S5, "Weird"), "the shortened paragraph").reason, /does not match the file/);
  assert.equal(bad(mapText(box5, S5, "Nov para one."), "inside the run").blockStartOffset, at(S5, "<button>"), "the run's refusal carries the swallower's offset");
  // the passage repeated inside the run: the FIRST rendered copy is the swallower's, refused, and the tail copy maps to its own offsets
  const NOVP = "Nov para one.";
  const V1 = `<button>\n\nAlpha <style>q</style>\n\nGo tango.\n\n${NOVP}\n\n<p>${FINAL3}</p>\n\n${WEIRD}\n\n${NOVP}\n`;
  const boxV = buildRendered(V1);
  assert.deepEqual(kidsOf(boxV).map((k) => k.tagName + ":" + k.textContent.trim().slice(0, 5)), ["P:Alpha", "P:Go ta", "P:Nov p", "P:Final", "P:Weird", "P:Nov p"], "the stand-in's shape: the button unwrapped, the style dropped");
  assert.match(bad(mapText(boxV, V1, NOVP, 0), "the first rendered copy").reason, /an HTML block/, "the swallowed copy is refused (before: it mapped to the tail copy's offsets, so a comment made there was stored on the wrong passage)");
  mapsWhole(boxV, V1, NOVP, 1);
  assert.deepEqual(elems(boxV, V1, blockAt(V1, "<p>")), [`P:"${FINAL3}"`]);
});

// ── the Slice 5 review, round 8 (each case red over a git archive of 99e7e2d0c's module unless its comment says it is a control) ──

test("a wrapper whose nested blocks are [P1, a paragraph the sanitizer shortened, P1 again] with nothing after (a README ending in a centred footer): each copy maps to its own offsets, the wrapper's block owns the wrapper alone (with its summary) and the shortened paragraph is refused as a mismatch with its own `<p>`, for a `<div>` open to the end, a `<div align=\"center\">` closed after the copy, a `<details><summary>`, a `<div>` closed right after the copy and a `<span/>` (runFits: a run whose content runs out while a block still needs a node is no run, main's rule; the review's round 8, HIGH: since 552f2bc20 one confirmed block had passed it, so the candidate end at the FIRST copy failed at the shortened paragraph and the one at the LAST copy passed, the wrapper's block took the first copy and the shortened paragraph, the first copy's block paired with the last copy, a selection in the last copy mapped to the first copy's offsets, so a comment made there was stored on the wrong passage, and the first copy was refused as an HTML block; main refused both copies, and 78c0806ce both under the `<span/>`, which round 7 opened); a paragraph after the copy, and no shortened paragraph between the copies, map as before (controls)", () => {
  const HT = "Hotel tango place note probe.", W = "Weird <style>x{}</style> line.", P1 = "Intro line here.";
  const J = (...b: string[]): string => b.join("\n\n") + "\n";
  const tags = (box: FakeElement, src: string, b: number): string[] => elems(box, src, b).map((e) => e.split(":")[0]);
  const check = (what: string, box: FakeElement, src: string, t: string, own: string[]): void => {
    for (const k of [0, 1]) mapsWhole(box, src, t, k);
    assert.deepEqual(tags(box, src, 0), own, what + ": the wrapper's block owns the wrapper alone (before: the first copy and the shortened paragraph too)");
    assert.equal(owner(box, src, find(box, "P", t)), blockAt(src, t), what + ": the first rendered copy is the first copy's block's");
    const shortened = sourceBlockSpans(src).findIndex((sp) => src.slice(sp.start, sp.end).startsWith("Weird"));
    assert.deepEqual(elems(box, src, shortened), ['P:"Weird line."'], what + ": the shortened paragraph is a mismatch with its own <p>");
    assert.match(bad(mapText(box, src, "Weird"), what).reason, /does not match the file/, what + ": refused as a mismatch, not as an HTML block");
  };
  const SHAPES: Array<[string, string, string, string[]]> = [
    ["a div open to the end", J("<div>", HT, W, HT), HT, ["DIV"]],
    ["a centred div closed after the copy (the README footer)", J('<div align="center">', P1, "Weird <script>x()</script> line.", P1, "</div>"), P1, ["DIV"]],
    ["a details with a summary", J("<details><summary>S</summary>", HT, W, HT), HT, ["DETAILS", "SUMMARY"]],
    ["a div closed right after the copy", J("<div>", HT, W, HT, "</div>"), HT, ["DIV"]],
  ];
  for (const [what, src, t, own] of SHAPES) check(what, buildRendered(src), src, t, own);
  // a `<span/>` block, which round 7 opens as the parser does (the stand-in's parser closes a `/>` at once, so the DOM is written by hand)
  const SPAN = J("<span/>", HT, W, HT);
  check("a self-closing span block", domOf(`<span><p>${HT}</p>\n<p>Weird  line.</p>\n<p>${HT}</p>\n</span>`), SPAN, HT, ["SPAN"]);
  // controls: a paragraph after the copy, and no shortened paragraph between the copies
  for (const [what, src] of [["a paragraph after the copy", J('<div align="center">', P1, "Weird <script>x()</script> line.", P1, "</div>", "After para here.")], ["no shortened paragraph between the copies", J('<div align="center">', P1, "Plain middle line.", P1, "</div>")]]) {
    const box = buildRendered(src);
    for (const k of [0, 1]) mapsWhole(box, src, P1, k);
    assert.deepEqual(tags(box, src, 0), ["DIV"], what);
  }
});

test("the run check's lookahead confirms nothing by an html block's TAG alone: inside it (runFits with `spent`) the block's element at k is read past with the nodes its scan takes and the blocks after must line up too, as nextAnchor's candidate check reads them; so after a `<button>` opener's run and a `</center>` alone a tail [paragraph, html `<p>`, paragraph] resumes at the paragraph's own `<p>`: the paragraph and the one after map to their own offsets, the html block owns its own `<p>`, the button's block the run's four and the run's refusals carry the button's offset, with a README's `<p align=\"center\"><img>` in the html block's place too; and nextAnchor's html `<p>` candidate before such a tail is confirmed at the html block's own `<p>` (the review's round 8, round 7's recheck residual, a regression against 78c0806ce and main: the tag match returned true, so the candidate one node before the paragraph's passed, the paragraph mismatched that node as the tolerated one, its own `<p>` stood for the html block's, the html block owned the run and the paragraph was refused as an HTML block at the html block's offset, the run's refusals carrying that offset too); a `<div>` block in the tail as before (a control)", () => {
  const NOV = "November tango sierra.", LAST = "Last kilo lima.", A = "Alpha text para.", H = "Html para here.", AFTER = "After all done.";
  const HEAD = `Intro alpha bravo charlie.\n\n<button>\n\n<button>probe xray</button>\n\n${NOV}\n\n${LAST}\n\n</center>\n\n`;
  const HEAD_DOM = `<p>Intro alpha bravo charlie.</p>\n<p></p>probe xray<p></p>\n<p>${NOV}</p>\n<p>${LAST}</p>\n`;
  const P = (t: string): string => `<p>${t}</p>\n`;
  const IMGP = '<p align="center"><img src="b.png" alt="badge"></p>';
  const TAILS: Array<[string, string, string, string, string[]]> = [
    ["an html <p> block in the tail", `${A}\n\n<p>${H}</p>\n\n${AFTER}\n`, P(A) + P(H) + P(AFTER), "<p>Html", [`P:"${H}"`]],
    ["a README's centred picture <p> in the tail", `${A}\n\n${IMGP}\n\n${AFTER}\n`, P(A) + IMGP + "\n" + P(AFTER), "<p align", ['P:""']],
    ["a <div> block in the tail (a control)", `${A}\n\n<div>${H}</div>\n\n${AFTER}\n`, P(A) + `<div>${H}</div>\n` + P(AFTER), "<div>", [`DIV:"${H}"`]],
  ];
  for (const [what, tail, tailDom, head, own] of TAILS) {
    const src = HEAD + tail;
    const box = domOf(HEAD_DOM + tailDom);
    for (const t of [A, AFTER]) mapsWhole(box, src, t);
    assert.deepEqual(elems(box, src, blockAt(src, head)), own, what + ": the html block owns its own element (before: the run's minted <p>, the run's two paragraphs, the paragraph's <p> and its own)");
    assert.deepEqual(elems(box, src, blockAt(src, A)), [`P:"${A}"`], what + ": the paragraph's block owns its own <p>");
    assert.deepEqual(elems(box, src, blockAt(src, "<button>")), ['P:""', 'P:""', `P:"${NOV}"`, `P:"${LAST}"`], what + ": the button's block owns the run's four");
    for (const t of [NOV, LAST]) assert.equal(bad(mapText(box, src, t), t).blockStartOffset, at(src, "<button>"), what + ": " + t + " is refused at the button's offset (before: at the html block's, past the passage)");
  }
  // nextAnchor's html `<p>` candidate before such a tail (round 6's candidate check, the lookahead recursing into the html block after the shortened paragraph)
  const MD = "Md para words.", OTHER = "Other html words.", FINAL3 = "Final para three.", NOVP = "Nov para one.";
  const R2 = `<button>\n\nAlpha <button>x</button>\n\n${NOVP}\n\n<p>${FINAL3}</p>\n\n${MD}\n\n<p>${OTHER}</p>\n\n${AFTER}\n`;
  const box2 = domOf(`<p>Alpha </p>x<p></p>\n<p>${NOVP}</p>\n<p>${FINAL3}</p>\n<p>${MD}</p>\n<p>${OTHER}</p>\n<p>${AFTER}</p>\n`);
  for (const t of [MD, AFTER]) mapsWhole(box2, R2, t);
  assert.deepEqual(elems(box2, R2, blockAt(R2, `<p>${FINAL3}`)), [`P:"${FINAL3}"`], "the html block owns its own <p> (before: Alpha's, the minted one, Nov's and its own)");
  assert.deepEqual(elems(box2, R2, blockAt(R2, `<p>${OTHER}`)), [`P:"${OTHER}"`]);
  assert.deepEqual(elems(box2, R2, blockAt(R2, "<button>")), ['P:"Alpha"', 'P:""', `P:"${NOVP}"`], "the button's block owns the run");
  assert.equal(bad(mapText(box2, R2, NOVP), NOVP).blockStartOffset, 0, "the run's refusal carries the button's offset (before: the html block's)");
});

test("in a run to the content's end (runFits with toEnd) an html block whose element stands BEHIND k is a misaligned run, not a dropped element: after a swallowed run, two raw `<table>` blocks with a foster-parented `<br>` between their elements, then a paragraph the sanitizer shortened and a last paragraph: the first table's block owns its own table and the `<br>`, the second its own table, and the last paragraph maps to its own offsets (the review's round 8, a regression against 78c0806ce: the second table's own element passed as the first table's candidate, from which the second table was read past as an element nowhere forward of k, the shortened paragraph was the lookahead's tolerated mismatch and the last paragraph lined up, so the first table's block took the second's element, the second's block owned the two paragraphs and the last paragraph was refused as an HTML block at the second table's offset); the paragraphs before the tables stay the leading stray `</p>` block's, for which the parser mints nothing before the body opens, on every Slice 5 tree (recorded), and with a `<p>Lead.</p>` block first every paragraph maps (a control)", () => {
  const ROM = "Romeo foxtrot bravo <iframe>if</iframe> kilo pairing echo.", UNI = "Uniform place sierra <noscript>ns</noscript> mike oscar fence.", QUE = "Quebec place edge mike delta juliet tango note.";
  const FOLD = "Fold echo edge <template>tp</template> place formula zulu.", TANGO = "Tango delta alpha india yankee romeo pairing place zulu place victor delta.";
  const T1 = "<table><tr><td>Aa<td>Bb</table>", T2 = "<table><tr><td>Cc</td><br><td>Dd</td></tr></table>";
  const J = (...b: string[]): string => b.join("\n\n") + "\n";
  // the DOM as the parser and the sanitizer leave it: no `<p>` minted for the leading `</p>`, the inline iframe, noscript and template
  // removed with their text, the second table's `<br>` foster-parented before it
  const DOM = (lead: string): string => `${lead}<p>Romeo foxtrot bravo  kilo pairing echo.</p>\n<p>Uniform place sierra  mike oscar fence.</p>\n<p>${QUE}</p>\n<table><tbody><tr><td>Aa</td><td>Bb</td></tr></tbody></table>\n<br><table><tbody><tr><td>Cc</td><td>Dd</td></tr></tbody></table>\n<p>Fold echo edge  place formula zulu.</p>\n<p>${TANGO}</p>\n`;
  const QJ = J("</p>", ROM, UNI, QUE, T1, T2, FOLD, TANGO);
  const box = domOf(DOM(""));
  mapsWhole(box, QJ, TANGO);
  mapsWhole(box, QJ, "yankee");
  assert.deepEqual(elems(box, QJ, blockAt(QJ, T1)), ['TABLE:"AaBb"', 'BR:""'], "the first table's block owns its table and the foster-parented br (before: the second table)");
  assert.deepEqual(elems(box, QJ, blockAt(QJ, T2)), ['TABLE:"CcDd"'], "the second table's block owns its own table (before: the two paragraphs after it)");
  assert.deepEqual(elems(box, QJ, blockAt(QJ, TANGO)), ['P:"Tango delta alpha"'], "the last paragraph's block owns its own <p>");
  assert.match(bad(mapText(box, QJ, "Fold echo"), "the shortened paragraph").reason, /does not match the file/);
  assert.match(bad(mapText(box, QJ, QUE), "before the tables").reason, /an HTML block/, "recorded: the leading `</p>` block, minting nothing, swallows the paragraphs before the tables on every Slice 5 tree");
  // a control: with a `<p>Lead.</p>` block first every paragraph maps
  const QK = J("<p>Lead.</p>", ROM, UNI, QUE, T1, T2, FOLD, TANGO);
  const boxK = domOf(DOM("<p>Lead.</p>\n"));
  for (const t of [TANGO, QUE]) mapsWhole(boxK, QK, t);
  assert.deepEqual(elems(boxK, QK, blockAt(QK, T1)), ['TABLE:"AaBb"', 'BR:""']);
});
