// The map's side of the rule for an inline start tag with no end tag in its block (md-literal-tags.ts; plans/file-review.md,
// decision 52), over a rendered DOM: the viewer renders such a tag as its own characters and the anchor map predicts them, so
// the paragraph holding it pairs with its element, every later block with its own, and a selection anywhere after it maps.
// Driven over marked's output as the viewer's mdBlock (file-view.ts) renders it, parsed into the DOM stand-in the anchor-map
// suites use (anchor-map-cells.test.ts's idiom), here with what the browser's parser does to marked's HTML in DOMPurify's
// quirks-mode document, the defect's mechanism (the assessment of 2026-09-18, verified in Chromium): a `<table>` start tag
// closes no open `<p>`, so the table opens inside the paragraph and the content up to its `</table>` that is not a table's
// own (text, a heading, a paragraph, a `</p>` minted as an empty `<p>`) is foster-parented before the table, inside the
// paragraph; a raw-text or RCDATA element (`<title>`, `<script>`, `<style>`, `<textarea>`) takes everything up to its end
// tag, or the document's end, as its text; and the sanitizer then drops a title, a script or a style with that text and
// unwraps a textarea around it (md-sanitize.ts). The rendering is the viewer's own parse, viewerHtml imported from
// file-view.ts (the recipe mdBlock parses through, since decision 52's review), so a change to the recipe reaches these
// verdicts directly: with the rule's call removed from viewerHtml, or with literalizeUnclosedTags a no-op, the two FAILS
// BEFORE cases go red where the defect stood (the four passages refused with the mismatch sentence; after an unclosed
// `<title>` the paragraph alone, the heading, the paragraph and the list gone). Over the base tree itself this module does
// not build, since viewerHtml is this slice's export. The browser leg, anchor-map-literal-tags-browser.test.ts, drives the
// real pane in Chromium. Synthetic text only: an invented note in the notes-api demo domain, an invented file name.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { viewerHtml } from "./file-view";   // the viewer's parse (mdBlock's recipe)
import { mapRenderedSelection, mapRawSelection, paintRendered, paintChangesRendered, unpaintChanges, renderedBlockIndex, sourceBlockSpans, type SelLike, type MapResult } from "./anchor-map";
import { hideEdges } from "../test-dom-shim";

applyMdConfig();

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser (the cells test's, with the quirks) ──
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
}
class FakeDocument {
  createElement(tag: string): FakeElement { return new FakeElement(this, tag.toUpperCase()); }
  createTextNode(s: string): FakeText { return new FakeText(this, s); }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr", "param"]);
/** The elements whose start tag closes an open `<p>` in button scope (anchor-map.ts CLOSES_P), less `table`, which closes none in a quirks-mode document. */
const CLOSES_P = /^(?:address|article|aside|blockquote|center|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|h[1-6]|header|hgroup|hr|li|listing|main|menu|nav|ol|p|plaintext|pre|search|section|summary|ul|xmp)$/i;
/** The button-scope barriers: a `<p>` below one of these is out of scope for a start tag's implied end and for a `</p>`. */
const P_BARRIER = /^(?:BUTTON|TABLE|TD|TH|CAPTION|TEMPLATE|OBJECT|MARQUEE|APPLET)$/;
/** The elements whose content the parser reads as text up to their own end tag (raw text and RCDATA). */
const RAW_TEXT = new Set(["script", "style", "textarea", "title", "xmp", "iframe", "noembed", "noframes", "plaintext"]);
/** The table context: with one of these the current node, a start tag that is not a table's own part and a text that is not blank are foster-parented before the table. */
const TABLE_CTX = new Set(["TABLE", "TBODY", "THEAD", "TFOOT", "TR"]);
const TABLE_OWN = new Set(["caption", "colgroup", "col", "tbody", "thead", "tfoot", "tr", "td", "th", "template", "script", "style", "form"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
    return e in NAMED ? NAMED[e] : m;
  });
}
/** marked's HTML into the stand-in as the browser's parser reads it in DOMPurify's quirks-mode document (the header): an
 *  unclosed tag stays open and the nodes after it nest inside it; a block-level start tag closes the nearest `<p>` in button
 *  scope, a `<table>` none; inside a table, content that is not the table's own is foster-parented before it, and a `<table>`
 *  start tag closes the open table first; a stray `</p>` mints an empty `<p>`; a raw-text element takes everything to its end
 *  tag or the document's end as text; the self-closing flag is ignored on a non-void element, which opens. */
function parseHTML(doc: FakeDocument, html: string): FakeNode[] {
  html = html.replace(/\r\n?/g, "\n");
  const root = doc.createElement("#fragment");
  const stack: FakeElement[] = [root];
  let i = 0;
  const top = () => stack[stack.length - 1];
  /** Where a node goes: the current node, or before the innermost open table when the current node is table context and the node is not the table's own. */
  const insert = (n: FakeNode, own: boolean): void => {
    if (TABLE_CTX.has(top().tagName) && !own) {
      for (let k = stack.length - 1; k > 0; k--) if (stack[k].tagName === "TABLE") { (stack[k].parentNode as FakeElement).insertBefore(n, stack[k]); return; }
    }
    top().appendChild(n);
  };
  /** The index of the nearest open `<p>` in button scope, or -1. */
  const pInScope = (): number => { for (let k = stack.length - 1; k > 0; k--) { if (stack[k].tagName === "P") return k; if (P_BARRIER.test(stack[k].tagName)) return -1; } return -1; };
  while (i < html.length) {
    if (html[i] === "<") {
      if (html.startsWith("<!--", i)) { const e = html.indexOf("-->", i); i = e < 0 ? html.length : e + 3; continue; }
      if (html[i + 1] === "!" || html[i + 1] === "?") { const e = html.indexOf(">", i); i = e < 0 ? html.length : e + 1; continue; }   // a declaration, a processing instruction or a CDATA section in HTML content: a bogus comment, dropped
      if (html[i + 1] === "/") {
        const e = html.indexOf(">", i);
        const name = html.slice(i + 2, e).trim().toUpperCase();
        i = e + 1;
        if (name === "P") { const k = pInScope(); if (k > 0) stack.length = k; else insert(doc.createElement("p"), false); continue; }   // a stray `</p>` mints an empty p
        for (let k = stack.length - 1; k > 0; k--) if (stack[k].tagName === name) { stack.length = k; break; }
        continue;
      }
      const m = /^<([a-zA-Z][\w:-]*)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*)\s*(\/?)>/.exec(html.slice(i));
      if (!m) { insert(doc.createTextNode("<"), false); i++; continue; }
      const lower = m[1].toLowerCase();
      if (lower === "table") { for (let k = stack.length - 1; k > 0; k--) { if (/^(?:TD|TH|CAPTION)$/.test(stack[k].tagName)) break; if (stack[k].tagName === "TABLE") { stack.length = k; break; } } }   // a table start tag inside an open table closes it
      if (CLOSES_P.test(lower)) { const k = pInScope(); if (k > 0) stack.length = k; }
      const el = doc.createElement(m[1]);
      const attrRe = /([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
      let a: RegExpExecArray | null;
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], decodeEntities(a[2] ?? a[3] ?? a[4] ?? ""));
      insert(el, TABLE_OWN.has(lower));
      i += m[0].length;
      if (VOID.has(lower)) continue;
      stack.push(el);
      if (RAW_TEXT.has(lower)) {
        const close = lower === "plaintext" ? -1 : html.toLowerCase().indexOf("</" + lower, i);
        const to = close < 0 ? html.length : close;
        const raw = html.slice(i, to);
        el.appendChild(doc.createTextNode(lower === "title" || lower === "textarea" ? decodeEntities(raw) : raw));
        if (close < 0) { i = html.length; continue; }
        const gt = html.indexOf(">", close);
        i = gt < 0 ? html.length : gt + 1;
        stack.pop();
      }
      continue;
    }
    let e = html.indexOf("<", i);
    if (e < 0) e = html.length;
    const text = html.slice(i, e);
    insert(doc.createTextNode(decodeEntities(text)), /^\s*$/.test(text));
    i = e;
  }
  return root.childNodes.slice();
}
/** The sanitizer's drops, stood in for (md-sanitize.ts): a title, a script, a style and the other raw-text elements the profile
 *  drops go WITH their text (dropBodyTitle, DOMPurify's FORBID_CONTENTS), a textarea is unwrapped around its text (KEEP_CONTENT). */
const DROP_WITH_TEXT = new Set(["TITLE", "SCRIPT", "STYLE", "IFRAME", "XMP", "PLAINTEXT", "NOEMBED", "NOFRAMES", "TEMPLATE"]);
function standInSanitize(root: FakeElement): void {
  for (const c of root.childNodes.slice()) {
    if (c.nodeType !== 1) continue;
    const el = c as FakeElement;
    if (DROP_WITH_TEXT.has(el.tagName)) { root.removeChild(el); continue; }
    if (el.tagName === "TEXTAREA") { for (const k of el.childNodes.slice()) root.insertBefore(k, el); root.removeChild(el); continue; }
    standInSanitize(el);
  }
}
/** `.fileview-md > marked output`, as the viewer renders `text` at this revision (viewerHtml), parsed and sanitized as above. */
function buildRendered(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, viewerHtml(text))) box.appendChild(n);
  standInSanitize(box);
  return box;
}
const escapeHtml = (s: string): string => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
/** The Raw view's `code.hljs`: one `.fv-cl` row per line, its text in a `.fv-ct` (file-view.ts wrapNumberedHtml's shape, no highlighting). */
function buildRaw(text: string): FakeElement {
  const doc = new FakeDocument();
  const code = doc.createElement("code"); code.setAttribute("class", "hljs");
  const rows = text.split(/\r\n|\r|\n/).map((ln) => `<span class="fv-cl"><span class="fv-ct">${escapeHtml(ln)}</span></span>`).join("");
  for (const n of parseHTML(doc, rows)) code.appendChild(n);
  return code;
}
const El = (n: FakeNode) => n as unknown as Element;
function allText(root: FakeNode): FakeText[] {
  if (root.nodeType === 3) return [root as FakeText];
  const out: FakeText[] = [];
  for (const c of root.childNodes) out.push(...allText(c));
  return out;
}
type Pt = { node: FakeNode; offset: number };
/** The point at the start (or, with `atEnd`, the end) of the k-th occurrence of `needle` inside ONE text node under root; null when none. */
function point(root: FakeNode, needle: string, atEnd = false, k = 0): Pt | null {
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
  return null;
}
const sel = (a: Pt, f: Pt): SelLike => ({ anchorNode: a.node as unknown as Node, anchorOffset: a.offset, focusNode: f.node as unknown as Node, focusOffset: f.offset, isCollapsed: false });
/** The k-th occurrence of `s` in `src`, which must exist. */
const at = (src: string, s: string, k = 0): number => { let i = -1; for (let n = 0; n <= k; n++) { i = src.indexOf(s, i + 1); assert.ok(i >= 0, "in the source: " + s); } return i; };
const rangeOf = (src: string, s: string, k = 0): { start: number; end: number } => ({ start: at(src, s, k), end: at(src, s, k) + s.length });
type Verdict = { needle: string; ok: boolean; reason: string; range: { start: number; end: number } | null; quote: string | null };
/** The map's answer for a selection over the k-th occurrence of `needle` in the rendered box: what a comment made there gets. */
function verdict(box: FakeElement, src: string, needle: string, k = 0): Verdict {
  const a = point(box, needle, false, k), f = point(box, needle, true, k);
  if (!a || !f) return { needle, ok: false, reason: "not in the rendered text", range: null, quote: null };
  const r: MapResult = mapRenderedSelection(sel(a, f), El(box), src);
  return r.ok ? { needle, ok: true, reason: "", range: r.range, quote: r.quote } : { needle, ok: false, reason: r.reason, range: null, quote: null };
}
/** `verdict` for a run of passages: the failure message lists every refusal, so the defect's shape is read in it. */
function verdicts(box: FakeElement, src: string, needles: string[]): Verdict[] { return needles.map((n) => verdict(box, src, n)); }
const refusals = (vs: Verdict[]): string => vs.filter((v) => !v.ok).map((v) => JSON.stringify(v.needle) + ": " + v.reason).join("; ");
/** Each passage maps to its own offsets with the quote the source's text. */
function mapsEach(box: FakeElement, src: string, needles: string[], what: string): void {
  const vs = verdicts(box, src, needles);
  assert.equal(refusals(vs), "", what + ": every passage maps (the refusals listed)");
  for (const v of vs) { assert.deepEqual(v.range, rangeOf(src, v.needle), what + ": " + JSON.stringify(v.needle) + " at its own offsets"); assert.equal(v.quote, v.needle); }
}
/** The box's element children (the whitespace text nodes marked leaves between blocks are not counted). */
const elems = (box: FakeElement): FakeElement[] => box.childNodes.filter((c) => c.nodeType === 1) as FakeElement[];
const kids = (box: FakeElement): string[] => elems(box).map((c) => c.tagName);
const norm = (s: string): string => s.replace(/\s+/g, " ").trim();
/** The first element of `tag` under root whose text holds `text`, else null. */
function find(root: FakeNode, tag: string, text: string): FakeElement | null {
  const hit = (n: FakeNode): FakeElement | null => {
    if (n !== root && n instanceof FakeElement && n.tagName === tag && n.textContent.includes(text)) return n;
    for (const c of n.childNodes) { const h = hit(c); if (h) return h; }
    return null;
  };
  return hit(root);
}
const MISMATCH = "This selection touches a block whose rendered text does not match the file; comment on it from the Raw view.";

// ── the defect's shape: a `<table>` placeholder mid-paragraph ────────────────────────────────────────────────────────────────
const TABLE_TAG = "Intro (<table>__widths.csv) mid line.\n\n## Second heading\n\nPara after the heading.\n\n| Col A | Col B |\n|---|---|\n| cell one | cell two |\n";

test("FAILS BEFORE: a paragraph with `(<table>__widths.csv)` mid-line followed by a heading, a paragraph and a pipe table: every block maps, a selection in the later paragraph and in a cell of the table anchors to its own source, and the rendered paragraph's text is the source text, `<table>` included (before: the browser opened a table inside the paragraph and parsed the three blocks into it, so the paragraph's text did not match the file and the four passages were refused with the mismatch sentence)", () => {
  const box = buildRendered(TABLE_TAG);
  const vs = verdicts(box, TABLE_TAG, ["Intro (", "Second heading", "Para after the heading.", "cell one"]);
  assert.equal(refusals(vs), "", "the four passages map (before: each refused, " + JSON.stringify(MISMATCH) + ")");
  assert.deepEqual(kids(box), ["P", "H2", "P", "TABLE"], "four top-level elements, one per block (before: one, the paragraph holding the rest)");
  assert.equal(norm(elems(box)[0].textContent), "Intro (<table>__widths.csv) mid line.", "the paragraph's rendered text is the source line");
  mapsEach(box, TABLE_TAG, ["Intro (", "<table>", "__widths.csv", "Second heading", "Para after the heading.", "cell one", "cell two", "Col B"], "the tag paragraph, the heading, the paragraph, the cells");
  assert.deepEqual(elems(box).map((c) => renderedBlockIndex(El(box), TABLE_TAG, El(c))), [0, 1, 2, 3], "each element is its block's");
  assert.equal(sourceBlockSpans(TABLE_TAG).length, 4);
});

// ── the silent loss: a raw-text or RCDATA start tag left open ───────────────────────────────────────────────────────────────
const AFTER = "\n\n## After heading\n\nPara after the tag.\n\n- item one\n- item two\n";

test("FAILS BEFORE: a paragraph with an unclosed `<title>` (and `<script>`, `<style>`, `<textarea>` as cases) followed by three blocks: the later blocks render and map, and the tag's characters read as text (before: the parser took the rest of the note as the element's text, which the sanitizer dropped with the element, or showed as raw text for a textarea, so the heading, the paragraph and the list were absent from the rendered view)", () => {
  for (const name of ["title", "script", "style", "textarea"]) {
    const src = `Lead <${name}> rest of the line.` + AFTER;
    const box = buildRendered(src);
    assert.deepEqual(kids(box), ["P", "H2", "P", "UL"], `<${name}>: the four blocks' elements (before: the paragraph alone)`);
    assert.equal(norm(elems(box)[0].textContent), `Lead <${name}> rest of the line.`, `<${name}>: the line as written`);
    mapsEach(box, src, [`<${name}>`, "rest of the line.", "After heading", "Para after the tag.", "item two"], `<${name}>`);
  }
});

// ── what the rule leaves alone ─────────────────────────────────────────────────────────────────────────────────────────────
test("closed tags keep their HTML: `<b>x</b>` renders bold, `<span class=\"a\">y</span>` keeps its element, `<kbd>Ctrl</kbd>` too, and the map maps those blocks and the passages around them", () => {
  const src = "Press <b>bold</b> now.\n\nSee <span class=\"a\">spanned</span> here.\n\nHold <kbd>Ctrl</kbd> down.\n\nClosing words.\n";
  const box = buildRendered(src);
  assert.deepEqual(kids(box), ["P", "P", "P", "P"]);
  assert.equal(find(box, "B", "bold")?.textContent, "bold");
  assert.equal(find(box, "SPAN", "spanned")?.getAttribute("class"), "a");
  assert.equal(find(box, "KBD", "Ctrl")?.textContent, "Ctrl");
  mapsEach(box, src, ["Press", "bold", "spanned", "here.", "Ctrl", "Closing words."], "closed tags");
});

test("void and self-closing tags are unchanged in the output and in the map: `<br>`, `<img src=...>`, `<x/>`, `<wbr>`, `<input>`: the viewer's HTML is marked.parse's for the same input, and the prose around them maps (`<x/>` is an unknown name, harmless either way; the self-closing spelling of a known name, and `<hr>` inline, the one void tag whose start tag closes an open `<p>`, are recorded below)", () => {
  const src = "First line<br>second line.\n\nA picture <img src=\"figs/plot.png\" alt=\"p\"> beside it.\n\nA custom <x/> tag and a <wbr> break and <input type=\"checkbox\"> a box.\n\nClosing words.\n";
  assert.equal(viewerHtml(src), marked.parse(src), "the viewer's HTML is marked.parse's");
  const box = buildRendered(src);
  assert.deepEqual(kids(box), ["P", "P", "P", "P"]);
  mapsEach(box, src, ["First line", "second line.", "A picture", "beside it.", "A custom", "tag and a", "a box.", "Closing words."], "void and self-closing");
});

// ── decision 52's deliberate exclusion, RECORDED: the self-closing spelling stays HTML, and the parser opens it ──────────────
/** The stand-in's element shape: the tag, then its element children in brackets. */
const shapeOf = (el: FakeElement): string => el.tagName + (elems(el).length ? "[" + elems(el).map(shapeOf).join(",") + "]" : "");
const SC_TAIL = "\n\n## Second heading t2\n\nPara after the heading t3.\n\nClosing words t4.\n";
const SC_PASSAGES = ["rest of the line t1", "Second heading t2", "Para after the heading t3", "Closing words t4"];

test("RECORDED, decision 52's deliberate exclusion: a start tag written with the self-closing flag stays HTML (md-literal-tags.ts isSelfClosingTag: the viewer's HTML is marked.parse's), and the parser ignores the flag on an HTML element and opens it, so `<div/>` in prose closes the paragraph and holds its rest and every later block (DIV[P,H2,P,P]), `(<table/>__widths.csv)` opens a table inside the paragraph with every later block foster-parented before it (P[P,H2,P,P,TABLE]), and `<title/>` takes the rest of the note as its text, dropped with the element: every later passage is refused with the mismatch sentence, or is not on the page, where the bare spelling of each is literal text and every block maps; `<x/>`, the control, is an unknown name popped with its paragraph, and every block maps. `<b/>` is recorded in the browser leg alone (anchor-map-literal-tags-browser.test.ts): the browser's active formatting elements reopen the `<b>` after the paragraph as a wrapper around every later block (P[B], B[H2,P,P]), which this stand-in does not model (it pops the `<b>` with its `<p>` and shows every block mapping, the false comfort the `<x/>` case above gave for the self-closing spelling as a whole)", () => {
  const mismatches = SC_PASSAGES.map((n) => JSON.stringify(n) + ": " + MISMATCH).join("; ");
  const absent = SC_PASSAGES.map((n) => JSON.stringify(n) + ": not in the rendered text").join("; ");
  const cases: Array<[string, string, string]> = [
    ["Lead <div/> rest of the line t1.", "P DIV[P,H2,P,P]", mismatches],
    ["Lead (<table/>__widths.csv) rest of the line t1.", "P[P,H2,P,P,TABLE]", mismatches],
    ["Lead <title/> rest of the line t1.", "P", absent],
  ];
  for (const [lead, shape, refused] of cases) {
    const src = lead + SC_TAIL;
    assert.equal(viewerHtml(src), marked.parse(src), lead + ": the viewer's HTML is marked.parse's, the tag left HTML");
    const box = buildRendered(src);
    assert.equal(elems(box).map(shapeOf).join(" "), shape, lead + ": the shape");
    assert.equal(refusals(verdicts(box, src, SC_PASSAGES)), refused, lead + ": every later passage refused or absent");
  }
  assert.equal(norm(buildRendered("Lead <title/> rest of the line t1." + SC_TAIL).textContent), "Lead", "`<title/>`: the page's whole text");
  for (const lead of ["Lead <div> rest of the line t1.", "Lead (<table>__widths.csv) rest of the line t1.", "Lead <title> rest of the line t1."]) {
    const src = lead + SC_TAIL;
    const box = buildRendered(src);
    assert.equal(kids(box).join(" "), "P H2 P P", lead + ": the bare spelling, one element per block");
    mapsEach(box, src, SC_PASSAGES, lead + ": the bare spelling");
  }
  const x = "Lead <x/> rest of the line t1." + SC_TAIL;
  const control = buildRendered(x);
  assert.equal(kids(control).join(" "), "P H2 P P", "`<x/>`: one element per block");
  mapsEach(control, x, SC_PASSAGES, "`<x/>`, the control");
});

test("RECORDED, decision 52's deliberately left `<hr>` inline: a void start tag, so the rule leaves it HTML (the viewer's HTML is marked.parse's), and the parser closes the open `<p>` at an `hr` start tag, so `Lead <hr> rest of the line t1.` renders as a paragraph holding `Lead`, a rule, the rest of the line as bare text and an empty paragraph minted from the stray `</p>` (P HR P, then H2 P P): both passages of that line are refused with the mismatch sentence and every later passage is not matched, where `<br>`, the control, is a void tag that closes nothing (P[BR] H2 P P) and every passage maps", () => {
  const src = "Lead <hr> rest of the line t1." + SC_TAIL;
  assert.equal(viewerHtml(src), marked.parse(src), "`<hr>` inline: the viewer's HTML is marked.parse's, the tag left HTML");
  const box = buildRendered(src);
  assert.equal(elems(box).map(shapeOf).join(" "), "P HR P H2 P P", "`<hr>` inline: the shape");
  const refused = ["Lead", "rest of the line t1"].map((n) => JSON.stringify(n) + ": " + MISMATCH)
    .concat(SC_PASSAGES.slice(1).map((n) => JSON.stringify(n) + ": The selection could not be matched to the file text.")).join("; ");
  assert.equal(refusals(verdicts(box, src, ["Lead", ...SC_PASSAGES])), refused, "`<hr>` inline: the line refused, the later passages unmatched");
  const br = "Lead <br> rest of the line t1." + SC_TAIL;
  const control = buildRendered(br);
  assert.equal(elems(control).map(shapeOf).join(" "), "P[BR] H2 P P", "`<br>`, the control: one element per block");
  mapsEach(control, br, ["Lead", ...SC_PASSAGES], "`<br>`, the control");
});

test("an unclosed formatting tag renders as text and maps: `<b>rest of line`, `<i>`, `<a href=...>`; nothing after it is bolded, italicised or linked", () => {
  const src = "Start <b>rest of the line.\n\nItalic <i>never closes here.\n\nLink <a href=\"http://a.test\">stays plain text.\n\nClosing words.\n";
  const box = buildRendered(src);
  assert.deepEqual(kids(box), ["P", "P", "P", "P"]);
  assert.equal(find(box, "B", "rest"), null, "no bold element holds the rest");
  assert.equal(find(box, "I", "never"), null, "no italic element");
  assert.equal(find(box, "A", "stays"), null, "no anchor");
  assert.equal(norm(elems(box)[0].textContent), "Start <b>rest of the line.");
  assert.equal(norm(elems(box)[2].textContent), "Link <a href=\"http://a.test\">stays plain text.");
  mapsEach(box, src, ["<b>", "rest of the line.", "<i>", "never closes here.", "<a href=\"http://a.test\">", "stays plain text.", "Closing words."], "unclosed formatting");
});

test("matching: `<b>x<b>y</b>` renders the inner pair as HTML and the first `<b>` as text; `<B>x</b>` is closed; a closer inside emphasis (`<b>x *y</b>*`) counts; each block maps", () => {
  const src = "Pair <b>x<b>y</b> z.\n\nCase <B>x</b> mixed.\n\nEmph <b>x *y</b>* z.\n\nClosing words.\n";
  const box = buildRendered(src);
  assert.deepEqual(kids(box), ["P", "P", "P", "P"]);
  const first = elems(box)[0];
  assert.equal(norm(first.textContent), "Pair <b>xy z.");
  assert.equal(first.childNodes.filter((c) => c.nodeType === 1 && (c as FakeElement).tagName === "B").length, 1, "one bold element");
  assert.equal(find(first, "B", "y")?.textContent, "y");
  assert.equal(find(elems(box)[1], "B", "x")?.textContent, "x", "`<B>x</b>`: a bold element");
  const emph = elems(box)[2];
  assert.ok(find(emph, "B", "x") && find(emph, "EM", "y"), "the bold and the emphasis both stand (the browser fixes the nesting)");
  mapsEach(box, src, ["Pair", "<b>", "z.", "mixed.", "Emph", "Closing words."], "matching");
  assert.equal(verdict(box, src, "y").ok, true, "the bold y");
});

test("the rule in a heading, a list item and a table cell: the tag's characters render as text and the block maps", () => {
  const src = "## Head <table> tail\n\n- item <b>one\n- item two\n\n| <span> x | y |\n|---|---|\n| a | <i>b |\n\nClosing words.\n";
  const box = buildRendered(src);
  assert.deepEqual(kids(box), ["H2", "UL", "TABLE", "P"]);
  assert.equal(norm(elems(box)[0].textContent), "Head <table> tail");
  assert.equal(norm(find(box, "LI", "one")!.textContent), "item <b>one");
  assert.equal(norm(find(box, "TH", "x")!.textContent), "<span> x");
  assert.equal(norm(find(box, "TD", "b")!.textContent), "<i>b");
  mapsEach(box, src, ["Head", "<table>", "tail", "<b>one", "item two", "<span> x", "<i>b", "Closing words."], "heading, item, cell");
});

test("offsets: a comment made on the literal `<table>` characters in the rendered view maps to those source characters; the Raw view maps the same selection to the same range; a comment highlight and a tracked-change mark over them paint the characters", () => {
  const box = buildRendered(TABLE_TAG);
  const range = rangeOf(TABLE_TAG, "<table>");
  const r = verdict(box, TABLE_TAG, "<table>");
  assert.deepEqual({ ok: r.ok, range: r.range, quote: r.quote }, { ok: true, range, quote: "<table>" }, "Rendered: the tag's own source offsets");
  const code = buildRaw(TABLE_TAG);
  const ra = point(code, "<table>", false), rf = point(code, "<table>", true);
  assert.ok(ra && rf, "the Raw rows show the tag");
  const raw = mapRawSelection(sel(ra!, rf!), El(code), TABLE_TAG);
  assert.deepEqual(raw, { ok: true, range, quote: "<table>" }, "Raw: the same range");
  const marks = paintRendered(El(box), TABLE_TAG, range, "fc-hl", { act: "fcopen", id: "c1" });
  assert.ok(marks && marks.length === 1, "one comment mark");
  assert.equal((marks![0] as unknown as FakeElement).textContent, "<table>", "the mark wraps the tag's characters");
  const box2 = buildRendered(TABLE_TAG);
  const res = paintChangesRendered(El(box2), TABLE_TAG, [{ id: "i1", kind: "ins", curFrom: range.start, curTo: range.end, oldText: "", author: "api", newText: "<table>" }], () => ({}));
  assert.deepEqual(res, { painted: ["i1"], unpainted: [] }, "the insertion paints");
  assert.equal(find(box2, "MARK", "<table>")?.textContent, "<table>", "the change mark reads the tag");
  unpaintChanges(El(box2));
  assert.equal(norm(elems(box2)[0].textContent), "Intro (<table>__widths.csv) mid line.", "unpainted clean");
});

test("a comment (`<!-- x -->`), a stray `</div>` and a declaration are untouched: the viewer's HTML is marked.parse's for the same input, and the prose maps", () => {
  const src = "Note <!-- an aside --> here.\n\nA stray </div> closer.\n\nA <!DOCTYPE x> declaration.\n\nClosing words.\n";
  assert.equal(viewerHtml(src), marked.parse(src), "the viewer's HTML is marked.parse's");
  const box = buildRendered(src);
  mapsEach(box, src, ["Note", "here.", "A stray", "closer.", "declaration.", "Closing words."], "untouched shapes");
});
