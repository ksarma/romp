// A code line maps from the Rendered view (plans/markdown-viewer.md, Slice 8, item 2; decision 7: the anchor map learns how
// marked lays out a code line, so a selection made in the Rendered view inside one maps back to the note's source offsets and
// the highlight lands on the right occurrence). Until this slice a code block was ONE hole over its raw: its text went through
// putHole with a negative position, so a selection in a code line refused as "touches a code block" (or "an indented code
// block") with the Raw view offered on an indexOf of the selected text, and a change inside a fence painted by the fallback's
// ordinal. Now walkCode (anchor-map.ts) reads the block's raw line by line as marked lays it out (the opener line, the content
// lines each less the whitespace prefix the compensation or an indented block's four spaces took, the closer) and emits every
// text line's characters at the raw line's own positions, so the block's chars are byte for byte what they were and the `<pre>`
// pairs as before, with every character positioned: a selection inside a row maps to the line's source span, tabs and CRLFs as
// the source holds them, and one across rows to the span from the first character to the last, the line feeds and a quoted
// fence's markers inside the quote as a Raw selection over the same characters mints (the brief's open question 2). Driven over
// the synthetic fixture anchor-map-fixtures/cells.md's code section and anchor-map-fixtures/fenced.md (both in the notes-api
// demo domain) rebuilt as the viewer renders them: marked's output as mdBlock parses it (its lexer, the literal-tags rule of
// md-literal-tags.ts, its parser: viewerHtml) under the one configuration (md-config.ts) parsed into the DOM stand-in, then
// every fence dressed as mdBlock dresses it (file-view.ts): a language the viewer registers highlighted into
// hljs spans, the lines cut into `.cl` rows by the real wrapLinesHtml (code-block.ts) with the line feeds dropped, the Copy
// button parked in the `<pre>`, and a URL in a row split into an `<a>` as linkifyFileText splits it. The idiom of
// anchor-map-cells.test.ts. The browser leg, anchor-map-code-lines-browser.test.ts, runs the real viewer and the real panel.
// Every case that maps a code character here refuses "touches a code block" or "an indented code block" over the tree before
// this slice, with one exception: test 8, the empty fence, is a guard, green there by design (nothing to select, the blocks
// around it map, and a Raw comment on its fence lines paints nothing, before the slice and since); the
// case of the Slice 8 review's round 1, a deletion point on a code line that shows no character placed in the line's own row,
// fails over the build's head (c68f52212 since the branch's rebase onto main, cd3a06501 before it) with the point one row down.
// Synthetic values only: an invented note, no real session text.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { marked } from "marked";
import hljs from "highlight.js/lib/core";
import bash from "highlight.js/lib/languages/bash";
import python from "highlight.js/lib/languages/python";
import javascript from "highlight.js/lib/languages/javascript";
import { applyMdConfig } from "./md-config";
import { viewerHtml } from "./file-view";   // the viewer's parse (mdBlock's recipe: marked's lexer, the literal-tags rule of md-literal-tags.ts, the per-call walk, its parser), the stand-in's too
import { wrapLinesHtml } from "./code-block";
import { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex, renderedBlockElements, paintRendered, paintChangesRendered, unpaintChanges, type SelLike, type MapResult, type ChangePaint } from "./anchor-map";
import { hideEdges } from "../test-dom-shim";

applyMdConfig();
// the languages the viewer registers that the fixtures name (file-view.ts's table; `sh` is bash's alias there)
for (const [name, lang] of Object.entries({ bash, sh: bash, python, py: python, javascript, js: javascript })) {
  try { hljs.registerLanguage(name, lang as any); } catch { /* dup alias */ }
}
const FIXDIR = path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map-fixtures");
const FIX = fs.readFileSync(path.join(FIXDIR, "cells.md"), "utf8");
const FENCED = fs.readFileSync(path.join(FIXDIR, "fenced.md"), "utf8");

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser (anchor-map-cells.test.ts's) ──
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
const escapeHtml = (s: string): string => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
/** marked's HTML into the stand-in, as a browser's parser reads a fragment: an unclosed tag stays open and the nodes after it
 *  nest inside it; an end tag closes down to its element; a block-level start tag closes the nearest open `<p>`; a newline right
 *  after `<pre>` is dropped (anchor-map-cells.test.ts's parser). */
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
        for (let k = stack.length - 1; k > 0; k--) if (stack[k].tagName === name) { stack.length = k; break; }
        i = e + 1; continue;
      }
      const m = /^<([a-zA-Z][\w:-]*)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*)\s*(\/?)>/.exec(html.slice(i));
      if (!m) { top().appendChild(doc.createTextNode("<")); i++; continue; }
      const el = doc.createElement(m[1]);
      const attrRe = /([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
      let a: RegExpExecArray | null;
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], decodeEntities(a[2] ?? a[3] ?? a[4] ?? ""));
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
const URL_RE = /https?:\/\/[^\s"'<>)]+/;
/** mdBlock's dress of every fence (file-view.ts): a language the viewer registers is highlighted into hljs spans, EVERY fence is cut
 *  into `.cl` rows by wrapLinesHtml (code-block.ts) with the line feeds dropped, the Copy button is parked as the `<pre>`'s last
 *  child, and a URL in a row's text is split into an `<a>` (file-view-links.ts linkifyFileText, stood in for by the split alone). */
function dressCode(box: FakeElement): void {
  const doc = box.ownerDocument;
  for (const pre of allOf(box, "PRE")) {
    const code = pre.childNodes.find((c) => c instanceof FakeElement && c.tagName === "CODE") as FakeElement | undefined;
    if (!code) continue;
    const raw = code.textContent;
    const lang = ((code.getAttribute("class") || "").match(/language-([\w-]+)/) || [])[1];
    let html = escapeHtml(raw);
    if (lang && hljs.getLanguage(lang)) { html = hljs.highlight(raw, { language: lang }).value; code.setAttribute("class", (code.getAttribute("class") || "") + " hljs"); }
    for (const c of code.childNodes.slice()) code.removeChild(c);
    for (const n of parseHTML(doc, wrapLinesHtml(html))) code.appendChild(n);
    for (const t of allText(code)) {
      const m = URL_RE.exec(t.data);
      if (!m) continue;
      const a = doc.createElement("a"); a.setAttribute("href", m[0]); a.setAttribute("class", "fv-url");
      const after = t.splitText(m.index + m[0].length);
      const url = t.splitText(m.index);
      (t.parentNode as FakeElement).insertBefore(a, after);
      a.appendChild(url);
    }
    const btn = doc.createElement("button"); btn.setAttribute("class", "code-copy"); btn.appendChild(doc.createTextNode("Copy"));
    pre.appendChild(btn);
  }
}
/** `.fileview-md > marked output`, filled and dressed as the viewer's body is. */
function buildRendered(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, viewerHtml(text))) box.appendChild(n);
  standInFill(box);
  dressCode(box);
  return box;
}
/** The same body with no fence dressed: a pre no renderer cut into rows, the shape a point on a blank code line falls back on. */
function undressed(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, viewerHtml(text))) box.appendChild(n);
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
const isCopy = (n: FakeNode): boolean => n instanceof FakeElement && (n.getAttribute("class") || "").split(" ").includes("code-copy");
/** The text nodes under `root` less the Copy button's, document order. */
function shownText(root: FakeNode): FakeText[] {
  if (root.nodeType === 3) return [root as FakeText];
  if (isCopy(root)) return [];
  const out: FakeText[] = [];
  for (const c of root.childNodes) out.push(...shownText(c));
  return out;
}
type Pt = { node: FakeNode; offset: number };
/** The point at the start (or, with `atEnd`, the end) of the k-th occurrence of `needle` in the text shown under `root`, the text
 *  nodes read in order as one string (a highlighted line is several nodes: `total = ` and its number, say), the Copy button's
 *  label left out. */
function point(root: FakeNode, needle: string, atEnd = false, k = 0): Pt {
  const nodes = shownText(root);
  let all = "";
  const starts: number[] = [];
  for (const t of nodes) { starts.push(all.length); all += t.data; }
  let i = -1;
  for (let n = 0; n <= k; n++) { i = all.indexOf(needle, i + 1); if (i < 0) throw new Error("not in the rendered text: " + JSON.stringify(needle)); }
  const g = atEnd ? i + needle.length - 1 : i;   // the index of the character the boundary touches
  let x = 0;
  while (x + 1 < nodes.length && starts[x + 1] <= g) x++;
  return { node: nodes[x], offset: g - starts[x] + (atEnd ? 1 : 0) };
}
const sel = (a: Pt, f: Pt): SelLike => ({ anchorNode: a.node as unknown as Node, anchorOffset: a.offset, focusNode: f.node as unknown as Node, focusOffset: f.offset, isCollapsed: false });
const ok = (r: MapResult, msg: string) => { assert.equal(r.ok, true, msg + ": " + ((r as { reason?: string }).reason || "")); return r as Extract<MapResult, { ok: true }>; };
const bad = (r: MapResult, msg: string) => { assert.equal(r.ok, false, msg); return r as Extract<MapResult, { ok: false }>; };
/** Select the k-th occurrence of `text` under `scope` (the rendered box, or one element of it) and map it against `src`. */
const mapText = (box: FakeElement, src: string, text: string, k = 0, scope: FakeNode = box): MapResult => mapRenderedSelection(sel(point(scope, text, false, k), point(scope, text, true, k)), El(box), src);
/** A selection from the start of `from` to the end of `to` (their k-th occurrences under `scope`), mapped against `src`. */
const mapSpan = (box: FakeElement, src: string, from: string, to: string, kf = 0, kt = 0, scope: FakeNode = box): MapResult => mapRenderedSelection(sel(point(scope, from, false, kf), point(scope, to, true, kt)), El(box), src);
/** The k-th occurrence of `s` in `src`, which must exist. */
const at = (src: string, s: string, k = 0): number => { let i = -1; for (let n = 0; n <= k; n++) { i = src.indexOf(s, i + 1); assert.ok(i >= 0, "in the source: " + s); } return i; };
const rangeOf = (src: string, s: string, k = 0): { start: number; end: number } => ({ start: at(src, s, k), end: at(src, s, k) + s.length });
const lineOf = (src: string, s: string, k = 0): number => src.slice(0, at(src, s, k)).split("\n").length - 1;
/** The k-th occurrence of `text` (under `scope`, in the source) maps to its own offsets with the quote the source's text. */
function mapsWhole(box: FakeElement, src: string, text: string, k = 0, scope: FakeNode = box): void {
  const r = ok(mapText(box, src, text, k, scope), text + (k ? " (occurrence " + k + ")" : ""));
  assert.deepEqual(r.range, rangeOf(src, text, k), text + ": its own offsets");
  assert.equal(r.quote, text);
}
/** The first element of `tag` UNDER `root` whose text holds `text`, in document order. */
const find = (root: FakeNode, tag: string, text: string): FakeElement => {
  const hit = (n: FakeNode): FakeElement | null => {
    if (n !== root && n instanceof FakeElement && n.tagName === tag && n.textContent.includes(text)) return n;
    for (const c of n.childNodes) { const h = hit(c); if (h) return h; }
    return null;
  };
  const h = hit(root); assert.ok(h, tag + " holding " + JSON.stringify(text)); return h;
};
/** The elements of `tag` under root, document order. */
const allOf = (root: FakeNode, tag: string, out: FakeElement[] = []): FakeElement[] => { for (const c of root.childNodes) { if (c instanceof FakeElement) { if (c.tagName === tag) out.push(c); allOf(c, tag, out); } } return out; };
const hasClass = (n: FakeNode, cls: string): boolean => n instanceof FakeElement && (n.getAttribute("class") || "").split(" ").includes(cls);
/** The `.cl` rows of the fence `pre`, and the text each shows. */
const rowsOf = (pre: FakeElement): FakeElement[] => { const code = pre.childNodes.find((c) => c instanceof FakeElement && c.tagName === "CODE") as FakeElement; return code.childNodes.filter((c) => hasClass(c, "cl")) as FakeElement[]; };
const rowTexts = (pre: FakeElement): string[] => rowsOf(pre).map((r) => r.textContent);
/** The index of the row holding `n` in its fence, -1 outside every row. */
const rowIndexOf = (n: FakeNode): number => { let p: FakeNode | null = n; while (p && !hasClass(p, "cl")) p = p.parentNode; if (!p) return -1; const code = p.parentNode as FakeElement; return code.childNodes.filter((c) => hasClass(c, "cl")).indexOf(p as FakeElement); };
const inside = (n: FakeNode, tag: string): boolean => { let p = n.parentNode; while (p) { if (p instanceof FakeElement && p.tagName === tag) return true; p = p.parentNode; } return false; };
const marksOf = (box: FakeElement, src: string, range: { start: number; end: number }, cls = "fc-hl"): FakeElement[] => (paintRendered(El(box), src, range, cls, { act: "fcopen", id: "k1" }) as unknown as FakeElement[] | null) || [];
const textMarks = (marks: FakeElement[]): FakeElement[] => marks.filter((m) => m.textContent.trim() !== "");
const unwrap = (marks: FakeElement[]): void => { for (const m of marks) { const p = m.parentNode as FakeElement; while (m.childNodes.length) p.insertBefore(m.childNodes[0], m); p.removeChild(m); } };
const A_CODE = /^This selection touches a code block; comment on it from the Raw view\.$/;
const WHITESPACE = "The selection is only whitespace.";

// ── the pairing and the dress: nothing about the block table changes ──

test("the fixture's fences pair as before, dressed as the viewer dresses them: every <pre> is its own block's one element (a top-level fence) or its container's (a list item's, a quote's); the python fence is highlighted and cut into four rows with the tab shown as four spaces, the compensation takes the backtick fence's opener indent and leaves the tilde fence's lines whole, the empty fence is one empty row, the unclosed fence runs to the note's end, the unknown language stays plain, and the URL in a row is an anchor", () => {
  const box = buildRendered(FIX);
  const pres = allOf(box, "PRE");
  assert.equal(pres.length, 10, "ten fences in the code section");
  const spans = sourceBlockSpans(FIX);
  const ownerOf = (n: FakeNode): { b: number; node: FakeNode } => { for (let x: FakeNode | null = n; x && x !== box; x = x.parentNode) { const b = renderedBlockIndex(El(box), FIX, x as unknown as Node); if (b >= 0) return { b, node: x }; } throw new Error("no block above the node"); };
  for (const pre of pres) {
    const { b, node } = ownerOf(pre);
    const els = renderedBlockElements(El(box), FIX, b) as unknown as FakeElement[];
    const head = FIX.slice(spans[b].start, spans[b].end).slice(0, 12);
    if (head.startsWith("- ") || head.startsWith("> ")) { assert.ok(node !== pre, "a nested fence is no block's own node: " + head); assert.ok(els.length === 1 && (els[0].tagName === "UL" || els[0].tagName === "BLOCKQUOTE"), "a nested fence's block is its container's: " + head); }
    else { assert.equal(node, pre, "the fence is its block's node: " + JSON.stringify(head)); assert.deepEqual(els.map((e) => e.tagName), ["PRE"], "block " + b + " (" + JSON.stringify(head) + ") owns its one pre"); }
    assert.ok(isCopy(pre.childNodes[pre.childNodes.length - 1]), "the Copy button is the pre's last child");
  }
  const py = find(box, "PRE", "def handler");
  assert.ok(hasClass(py.childNodes[0], "hljs") && allOf(py, "SPAN").some((s) => (s.getAttribute("class") || "").startsWith("hljs-")), "the python fence is highlighted into hljs spans");
  assert.deepEqual(rowTexts(py), ["total = 1", "def handler(request):", "    return respond(request)", "total = 1"], "four rows, the tab shown as four spaces, no line feed in any");
  assert.deepEqual(rowTexts(find(box, "PRE", "compensated")), ["compensated = 5", "  deeper = 6"], "the backtick fence's two-space opener indent comes off every line (indentCodeCompensation)");
  assert.deepEqual(rowTexts(find(box, "PRE", "tilde")), ["  tilde = 7"], "a tilde fence keeps its lines whole");
  assert.deepEqual(rowTexts(find(box, "PRE", "indented = 3")), ["indented = 3", "next = 4"], "an indented block's four spaces come off");
  const empty = pres.find((p) => p.textContent.replace("Copy", "") === "")!;
  assert.ok(empty, "the empty fence renders");
  assert.deepEqual(rowTexts(empty), [""], "one empty row");
  assert.deepEqual(rowTexts(find(box, "PRE", "open = 9")), ["open = 9"], "the unclosed fence's one line");
  assert.equal(pres.indexOf(find(box, "PRE", "open = 9")), pres.length - 1, "the unclosed fence is the note's last block");
  const zig = find(box, "PRE", "unknown");
  assert.equal((zig.childNodes[0] as FakeElement).getAttribute("class"), "language-zig", "a language the viewer does not register stays plain, its class as marked wrote it");
  const a = find(find(box, "PRE", "https://"), "A", "https://notes-api.test/handlers");
  assert.equal(a.textContent, "https://notes-api.test/handlers", "the URL is an anchor inside its row");
  assert.equal(rowIndexOf(a), 0);
});

// ── item 2: a line maps ──

test("a code line maps to its indexOf offsets with the quote the raw line (before: refused, `touches a code block`, the Raw view offered on an indexOf of the text): a highlighted line whose text is several hljs nodes, a plain fence's line, a fence in a language the viewer does not know, the unclosed fence's line; a part of a line maps to its own characters", () => {
  const box = buildRendered(FIX);
  const py = find(box, "PRE", "def handler");
  mapsWhole(box, FIX, "def handler(request):", 0, py);
  mapsWhole(box, FIX, "return respond(request)", 0, py);
  mapsWhole(box, FIX, "const unknown = 8;");
  mapsWhole(box, FIX, "open = 9");
  mapsWhole(box, FIX, "quoted = 1");
  const part = ok(mapRenderedSelection(sel(point(py, "handler"), point(py, "handler(req", true)), El(box), FIX), "part of a line");
  assert.equal(part.quote, "handler(req");
  assert.deepEqual(part.range, rangeOf(FIX, "handler(req"));
  // the fenced.md fixture: the probe's shapes, a comment line, an indented return with a trailing comment
  const fb = buildRendered(FENCED);
  const fp = find(fb, "PRE", "def f(x)");
  mapsWhole(fb, FENCED, "# a comment", 0, fp);
  mapsWhole(fb, FENCED, "return x + 1  # trailing", 0, fp);
  mapsWhole(fb, FENCED, "value = f(2)", 0, fp);
  mapsWhole(fb, FENCED, "plain fence, no language");
  mapsWhole(fb, FENCED, "second line of it");
});

test("the second copy of a repeated line maps to the second row (the selection made in the fourth row: positions, not a text search), and the first to the first; the paint of each lands on its own row", () => {
  const box = buildRendered(FIX);
  const py = find(box, "PRE", "def handler");
  mapsWhole(box, FIX, "total = 1", 0, py);
  mapsWhole(box, FIX, "total = 1", 1, py);
  assert.equal(rowIndexOf(point(py, "total = 1", false, 1).node), 3, "the second occurrence is in the fourth row");
  for (const [k, row] of [[0, 0], [1, 3]] as const) {
    const marks = textMarks(marksOf(box, FIX, rangeOf(FIX, "total = 1", k)));
    assert.ok(marks.length >= 1, "painted, occurrence " + k);
    assert.deepEqual(Array.from(new Set(marks.map(rowIndexOf))), [row], "occurrence " + k + " paints in row " + row);
    assert.equal(marks.map((m) => m.textContent).join(""), "total = 1");
    unwrap(marks);
  }
});

test("a selection across two lines maps to the source span with the line feed inside the quote (open question 2's default: the span a Raw selection over the same characters mints); the tab-indented line's quote holds the tab byte where the row shows four spaces; the quoted fence's two lines carry the `> ` marker inside the quote; the indented block's two lines carry the second line's four spaces; a CRLF source keeps its CRLF", () => {
  const box = buildRendered(FIX);
  const py = find(box, "PRE", "def handler");
  const two = ok(mapSpan(box, FIX, "def handler", "respond(request)", 0, 0, py), "two lines");
  assert.equal(two.quote, "def handler(request):\n\treturn respond(request)", "the tab byte inside the quote");
  assert.deepEqual(two.range, { start: at(FIX, "def handler"), end: at(FIX, "respond(request)") + "respond(request)".length });
  const quoted = ok(mapSpan(box, FIX, "quoted = 1", "second = 2"), "the quoted fence's two lines");
  assert.equal(quoted.quote, "quoted = 1\n> second = 2");
  const indented = ok(mapSpan(box, FIX, "indented = 3", "next = 4"), "the indented block's two lines");
  assert.equal(indented.quote, "indented = 3\n    next = 4");
  const comp = ok(mapSpan(box, FIX, "compensated = 5", "deeper = 6"), "the compensated fence's two lines");
  assert.equal(comp.quote, "compensated = 5\n    deeper = 6", "the second line's own four spaces, the compensation's two among them");
  const crlf = "Intro.\r\n\r\n```\r\na = 1\r\nb = 2\r\n```\r\n\r\nAfter.\r\n";
  const cb = buildRendered(crlf);
  const r = ok(mapSpan(cb, crlf, "a = 1", "b = 2"), "two lines under CRLF");
  assert.equal(r.quote, "a = 1\r\nb = 2");
  assert.deepEqual(r.range, { start: at(crlf, "a = 1"), end: at(crlf, "b = 2") + 5 });
  mapsWhole(cb, crlf, "After.");
});

test("the whole fence selected maps to the content span, the fence lines outside it; a selection from the paragraph before a fence into its first line, and one out of its last line into the paragraph after, map with the fence line inside the quote; a selection across a whole fence between two paragraphs carries the fence, lines and all", () => {
  const box = buildRendered(FIX);
  const py = find(box, "PRE", "def handler");
  const whole = ok(mapRenderedSelection(sel(point(py, "total = 1", false, 0), point(py, "total = 1", true, 1)), El(box), FIX), "the whole fence");
  assert.equal(whole.quote, "total = 1\ndef handler(request):\n\treturn respond(request)\ntotal = 1");
  assert.deepEqual(whole.range, { start: at(FIX, "total = 1"), end: at(FIX, "total = 1", 1) + "total = 1".length });
  const into = ok(mapSpan(box, FIX, "Code lines below", "total = 1"), "the paragraph before into the first line");
  assert.equal(into.quote, "Code lines below, for the code section.\n\n```python\ntotal = 1");
  const out = ok(mapRenderedSelection(sel(point(py, "total = 1", false, 1), point(box, "tab-indented line above.", true)), El(box), FIX), "the last line into the paragraph after");
  assert.equal(out.quote, "total = 1\n```\n\nA repeated line and a tab-indented line above.");
  const across = ok(mapSpan(box, FIX, "An indented code block above.", "A backtick fence"), "across the two indented-opener fences");
  assert.equal(across.quote, "An indented code block above.\n\n  ```js\n  compensated = 5\n    deeper = 6\n  ```\n\n  ~~~\n  tilde = 7\n  ~~~\n\nA backtick fence");
});

test("an indent alone is only whitespace, and a selection begun in the indent snaps to the first glyph (the standing rule); the Copy button's label is not selectable text (a control): a selection run into it ends at the code's last character, and one of the label alone selects nothing", () => {
  const box = buildRendered(FIX);
  const py = find(box, "PRE", "def handler");
  const row = rowsOf(py)[2];
  const first = allText(row)[0];
  assert.equal(first.data.slice(0, 4), "    ", "the tab-indented row opens with the four spaces");
  assert.equal(bad(mapRenderedSelection(sel({ node: first, offset: 0 }, { node: first, offset: 4 }), El(box), FIX), "the indent alone").reason, WHITESPACE);
  const snapped = ok(mapRenderedSelection(sel({ node: first, offset: 1 }, point(py, "respond(request)", true)), El(box), FIX), "begun in the indent");
  assert.equal(snapped.quote, "return respond(request)", "the tab is not selected text");
  assert.deepEqual(snapped.range, rangeOf(FIX, "return respond(request)"));
  const copy = allText(py).find((t) => t.data === "Copy")!;
  assert.ok(copy && isCopy(copy.parentNode!), "the button's label");
  const intoCopy = ok(mapRenderedSelection(sel(point(py, "total = 1", false, 1), { node: copy, offset: 4 }), El(box), FIX), "into the Copy label");
  assert.equal(intoCopy.quote, "total = 1", "the label adds nothing");
  assert.deepEqual(intoCopy.range, rangeOf(FIX, "total = 1", 1));
  assert.equal(bad(mapRenderedSelection(sel({ node: copy, offset: 0 }, { node: copy, offset: 4 }), El(box), FIX), "the label alone").reason, "Select some text to comment on.");
});

test("a line inside a list item's fence, a quoted fence's line, an indented code block's line, the compensated fence's lines, the tilde fence's line and a linkified URL's line map through the container's view and past the anchor's split; the prose beside each still maps", () => {
  const box = buildRendered(FIX);
  mapsWhole(box, FIX, "npm run build");
  mapsWhole(box, FIX, "after the item's fence");
  mapsWhole(box, FIX, "A list item holding a fence:");
  mapsWhole(box, FIX, "quoted = 1");
  mapsWhole(box, FIX, "second = 2");
  mapsWhole(box, FIX, "A quote holding a fence:");
  mapsWhole(box, FIX, "indented = 3");
  mapsWhole(box, FIX, "next = 4");
  mapsWhole(box, FIX, "compensated = 5");
  mapsWhole(box, FIX, "deeper = 6");
  mapsWhole(box, FIX, "tilde = 7");
  const url = ok(mapSpan(box, FIX, "url = ", "handlers\""), "the line holding the linked URL");
  assert.equal(url.quote, "url = \"https://notes-api.test/handlers\"");
  assert.deepEqual(url.range, rangeOf(FIX, "url = \"https://notes-api.test/handlers\""));
  mapsWhole(box, FIX, "https://notes-api.test/handlers");
  mapsWhole(box, FIX, "Last of all, an unclosed fence:");
  // the item's prose into its fence's line: one span, the fence's opener inside the quote
  const into = ok(mapSpan(box, FIX, "holding a fence:", "npm run build"), "the item's prose into its fence");
  assert.equal(into.quote, "holding a fence:\n\n  ```sh\n  npm run build");
});

test("an empty fence: nothing to select, the blocks around it map, and a Raw comment on its two fence lines paints nothing and keeps its card (the fallback: the lines render nothing); a Raw comment on an opener line alone, or on the closer, paints nothing too (a guard: green before the slice, whose fence lines painted nothing then as now)", () => {
  const box = buildRendered(FIX);
  mapsWhole(box, FIX, "A backtick fence with an indented opener and a tilde fence with one.");
  mapsWhole(box, FIX, "An empty fence above.");
  const emptyAt = at(FIX, "```\n```\n\nAn empty");
  assert.equal(paintRendered(El(box), FIX, { start: emptyAt, end: emptyAt + 7 }, "fc-hl"), null, "the empty fence's lines paint nothing");
  assert.equal(paintRendered(El(box), FIX, rangeOf(FIX, "```python"), "fc-hl"), null, "the opener line alone paints nothing");
  const closer = at(FIX, "```\n\nA repeated line");
  assert.equal(paintRendered(El(box), FIX, { start: closer, end: closer + 3 }, "fc-hl"), null, "the closer alone paints nothing");
});

// ── the paint and the change points inside a fence go by position ──

test("a Raw-made comment paints by position: one line one mark run in its row, two lines marks in both rows and none over the dropped line feed, a whole-fence quote (fence lines included) every row with text, a quote begun in the opener's info string the first line (the same marks the fallback's raw reading gave, now through the exact path); a deletion point inside a line places in its row and a substitution's point sits before its tint", () => {
  const box = buildRendered(FIX);
  const py = find(box, "PRE", "def handler");
  let marks = textMarks(marksOf(box, FIX, rangeOf(FIX, "return respond(request)")));
  assert.ok(marks.length >= 1);
  assert.deepEqual([marks.map((m) => m.textContent).join(""), Array.from(new Set(marks.map(rowIndexOf)))], ["return respond(request)", [2]]);
  assert.ok(marks.every((m) => inside(m, "PRE")));
  unwrap(marks);
  const two = { start: at(FIX, "def handler"), end: at(FIX, "respond(request)") + "respond(request)".length };
  marks = textMarks(marksOf(box, FIX, two));
  assert.deepEqual(Array.from(new Set(marks.map(rowIndexOf))).sort(), [1, 2], "both rows");
  assert.equal(marks.map((m) => m.textContent).join("").replace(/\s+/g, ""), "defhandler(request):returnrespond(request)", "both lines' characters, one mark per run of hljs nodes");
  unwrap(marks);
  const whole = { start: at(FIX, "```python"), end: at(FIX, "```\n\nA repeated line") + 3 };
  marks = textMarks(marksOf(box, FIX, whole));
  assert.deepEqual(Array.from(new Set(marks.map(rowIndexOf))).sort(), [0, 1, 2, 3], "every row with text");
  assert.ok(marks.every((m) => inside(m, "PRE")), "nothing outside the pre");
  unwrap(marks);
  marks = textMarks(marksOf(box, FIX, { start: at(FIX, "python\ntotal") + 2, end: at(FIX, "total = 1") + "total = 1".length }));
  assert.deepEqual([marks.map((m) => m.textContent).join(""), Array.from(new Set(marks.map(rowIndexOf)))], ["total = 1", [0]], "a quote begun in the info string paints the first line");
  unwrap(marks);
  // change marks: a deletion inside a line, a substitution whose tint is the line's word
  const del = (id: string, curFrom: number): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText: "gone", author: "web" });
  const off = at(FIX, "respond(request)");
  let res = paintChangesRendered(El(box), FIX, [del("in-line", off + 3), del("line-end", off + "respond(request)".length)], () => ({}));
  assert.deepEqual(res, { painted: ["in-line", "line-end"], unpainted: [] });
  const points = allOf(box, "SPAN").filter((s) => hasClass(s, "fc-del"));
  assert.deepEqual(points.map((p) => [p.getAttribute("data-id"), rowIndexOf(p)]), [["in-line", 2], ["line-end", 2]], "both in the tab-indented row");
  unpaintChanges(El(box));
  const s: ChangePaint = { id: "s", kind: "sub", curFrom: off, curTo: off + "respond".length, oldText: "reply", author: "web", newText: "respond" };
  res = paintChangesRendered(El(box), FIX, [s], () => ({}));
  assert.deepEqual(res, { painted: ["s"], unpainted: [] });
  const tint = allOf(py, "MARK").find((m) => hasClass(m, "fc-ins"))!;
  assert.ok(tint && tint.textContent === "respond", "the tint is the new word in its row");
  const pt = allOf(py, "SPAN").find((x) => hasClass(x, "fc-del"))!;
  assert.ok(pt, "the substitution's point");
  assert.equal(pt.parentNode!.childNodes[pt.parentNode!.childNodes.indexOf(pt) + 1], tint, "immediately before its tint");
  unpaintChanges(El(box));
});

/** The text of `el`'s text nodes before `pt` in document order, and after it. */
function around(el: FakeNode, pt: FakeNode): [string, string] {
  let pre = "", post = "", seen = false;
  const visit = (n: FakeNode) => { if (n === pt) { seen = true; return; } if (n.nodeType === 3) { if (seen) post += (n as FakeText).data; else pre += (n as FakeText).data; } for (const c of n.childNodes) visit(c); };
  visit(el);
  return [pre, post];
}
const pointOf = (box: FakeElement, id: string): FakeElement => { const x = allOf(box, "SPAN").find((x) => hasClass(x, "fc-del") && x.getAttribute("data-id") === id); assert.ok(x, id + " painted"); return x!; };

test("deletion points on a fence's lines: inside the opener (its second backtick, its info string) and inside the closer the change keeps its card (the lines render nothing: zero-text holes since Slice 8; before: the whole block a hole), a point at a nested fence's opener or in the indentation before it sits after the item's text before the fence, one at a top-level fence's opener sits before the code's first character (the block's edge), one at the line feed after the last code line sits after its last character; a point inside a line places in its row", () => {
  const box = buildRendered(FIX);
  const del = (id: string, curFrom: number): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText: "gone", author: "web" });
  const py = at(FIX, "```python"), pyClose = at(FIX, "```\n\nA repeated line"), sh = at(FIX, "```sh"), shClose = at(FIX, "  ```\n\n  after the item's fence") + 2;
  const res = paintChangesRendered(El(box), FIX, [
    del("top-open", py),                                  // the top-level fence's first backtick
    del("top-in-open", py + 1),                           // its second backtick
    del("top-info", py + 4),                              // the info string
    del("top-feed", pyClose - 1),                         // the line feed after the last code line
    del("top-close", pyClose),                            // the closer's first backtick
    del("top-in-close", pyClose + 2),                     // inside the closer
    del("item-indent", sh - 1),                           // the item's indentation before the nested opener
    del("item-open", sh),                                 // the nested fence's first backtick
    del("item-in-open", sh + 2),                          // its third backtick
    del("item-feed", at(FIX, "npm run build") + "npm run build".length),   // the line feed after the nested fence's line
    del("item-in-close", shClose + 1),                    // inside the nested closer
    del("quoted-feed", at(FIX, "second = 2") + "second = 2".length),      // the line feed after the quoted fence's last line
    del("in-line", at(FIX, "def handler") + 4),           // inside a line
  ], () => ({}));
  assert.deepEqual(res, { painted: ["top-open", "top-feed", "item-indent", "item-open", "item-feed", "quoted-feed", "in-line"], unpainted: ["top-in-open", "top-info", "top-close", "top-in-close", "item-in-open", "item-in-close"] });
  const topPre = find(box, "PRE", "def handler");
  assert.ok(inside(pointOf(box, "top-open"), "PRE") && around(topPre, pointOf(box, "top-open"))[1].startsWith("total = 1"), "the top-level opener's first character: before the code's first character, the block's edge");
  assert.deepEqual([inside(pointOf(box, "top-feed"), "PRE"), rowIndexOf(pointOf(box, "top-feed")), around(topPre, pointOf(box, "top-feed"))[0].endsWith("total = 1")], [true, 3, true], "the line feed after the last line: after its last character, in the last row");
  assert.equal(rowIndexOf(pointOf(box, "in-line")), 1, "a point inside a line sits in its row");
  const li = find(box, "LI", "npm run build");
  for (const id of ["item-indent", "item-open"]) {
    const pt = pointOf(box, id);
    assert.ok(!inside(pt, "PRE") && (pt.parentNode as FakeElement).tagName === "P", id + ": in the item's paragraph, not the fence");
    const [pre, post] = around(li, pt);
    assert.ok(pre.endsWith("A list item holding a fence:") && post.replace(/\s+/g, "").startsWith("npmrunbuild"), id + ": after the text before the fence: " + JSON.stringify([pre.slice(-12), post.slice(0, 12)]));
  }
  assert.ok(inside(pointOf(box, "item-feed"), "PRE") && around(find(box, "PRE", "npm run build"), pointOf(box, "item-feed"))[0].endsWith("npm run build"), "the nested fence's line feed: after its line's last character");
  assert.ok(inside(pointOf(box, "quoted-feed"), "PRE") && around(find(box, "PRE", "quoted = 1"), pointOf(box, "quoted-feed"))[0].endsWith("second = 2"), "the quoted fence's line feed: after its last line");
  unpaintChanges(El(box));
  // an indented block has no fence lines: a point in its first line's indentation sits before the line's first character
  const ind = at(FIX, "    indented = 3");
  const r2 = paintChangesRendered(El(box), FIX, [del("ind-indent", ind + 1), del("ind-in", ind + 6)], () => ({}));
  assert.deepEqual(r2, { painted: ["ind-indent", "ind-in"], unpainted: [] });
  assert.deepEqual([rowIndexOf(pointOf(box, "ind-indent")), rowIndexOf(pointOf(box, "ind-in"))], [0, 0]);
  assert.ok(around(find(box, "PRE", "indented = 3"), pointOf(box, "ind-indent"))[1].startsWith("indented = 3"), "before the line's first character");
  unpaintChanges(El(box));
});

test("a deletion point on a code line that shows no character places in the line's own row (the Slice 8 review, round 1; before: before the next line's first character, one row down, which read as that line changed): a blank line's point goes into its empty text cell, a whitespace-only line's at its column among the spaces, two blank lines in a row each into their own row, a blank line of a nested fence (the item's indent stripped from it or kept on it) and of an indented block into theirs, and a CRLF note's on either byte of its ending; a blank line that ends a fence's text has no row (marked's renderer folds it) and its point sits after the last character as before, and a pre no renderer cut into rows keeps the rule before", () => {
  const SRC = "Intro.\n\n```python\nfirst = 1\n\nthird = 3\n    \nfifth = 5\n\n\neighth = 8\n\n```\n\nAfter.\n";
  const ROWS = ["first = 1", "", "third = 3", "    ", "fifth = 5", "", "", "eighth = 8"];
  const box = buildRendered(SRC);
  const pre = find(box, "PRE", "first = 1");
  assert.deepEqual(rowTexts(pre), ROWS, "the viewer's rows: one per line, the trailing blank line folded");
  const del = (id: string, curFrom: number): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText: "gone", author: "web" });
  const blank = at(SRC, "first = 1") + "first = 1".length + 1, ws = at(SRC, "\n    \n") + 1, blanks = at(SRC, "fifth = 5") + "fifth = 5".length + 1, trail = at(SRC, "eighth = 8") + "eighth = 8".length + 1;
  const res = paintChangesRendered(El(box), SRC, [
    del("blank", blank),          // the blank line after the first
    del("ws-0", ws),              // the whitespace line, before its spaces
    del("ws-2", ws + 2),          // between its second and third space
    del("ws-end", ws + 4),        // its line feed
    del("blank-a", blanks),       // the first of two blank lines
    del("blank-b", blanks + 1),   // the second
    del("trail", trail),          // the blank line that ends the fence's text: no row stands for it
    del("in-line", at(SRC, "third = 3") + 6),   // the control: inside a line
  ], () => ({}));
  assert.deepEqual(res, { painted: ["blank", "ws-0", "ws-2", "ws-end", "blank-a", "blank-b", "trail", "in-line"], unpainted: [] });
  const rowOf = (id: string): number => rowIndexOf(pointOf(box, id));
  assert.deepEqual([rowOf("blank"), rowOf("ws-0"), rowOf("ws-2"), rowOf("ws-end"), rowOf("blank-a"), rowOf("blank-b"), rowOf("in-line")], [1, 3, 3, 3, 5, 6, 2], "each point in its line's own row (before: the blank line's in row 2, the whitespace line's three in row 4, the two blank lines' in row 7)");
  for (const id of ["blank", "blank-a", "blank-b"]) {
    const pt = pointOf(box, id);
    assert.ok(hasClass(pt.parentNode!, "ct"), id + ": in the row's text cell");
    assert.equal((pt.parentNode as FakeElement).childNodes.length, 1, id + ": the empty cell holds the point alone");
  }
  const rows = rowsOf(pre);
  assert.deepEqual([around(rows[3], pointOf(box, "ws-0")), around(rows[3], pointOf(box, "ws-2")), around(rows[3], pointOf(box, "ws-end"))], [["", "    "], ["  ", "  "], ["    ", ""]], "the whitespace line's points at their columns");
  assert.deepEqual([rowOf("trail"), around(pre, pointOf(box, "trail"))[0].endsWith("eighth = 8")], [7, true], "the folded trailing blank line: after the last character, in the last row, as before");
  assert.deepEqual(rowTexts(pre), ROWS, "the rows' text is untouched: a point holds none");
  unpaintChanges(El(box));
  assert.equal(allOf(box, "SPAN").filter((e) => hasClass(e, "fc-del")).length, 0, "unpainted");
  assert.deepEqual(rowTexts(pre), ROWS);
  // a nested fence's blank line, bare or carrying the item's indent, and an indented block's
  const nested = "- Item:\n\n  ```\n  a = 1\n\n  b = 2\n  ```\n\n  after\n", kept = "- Item:\n\n  ```\n  a = 1\n  \n  b = 2\n  ```\n\n  after\n", ind = "Intro.\n\n    alpha = 1\n\n    beta = 2\n\nAfter.\n";
  const shapes: Array<[string, number, string]> = [
    [nested, at(nested, "a = 1") + 6, "a nested fence's bare blank line"],
    [kept, at(kept, "a = 1") + 6, "a nested fence's indented blank line, at the indent's first space"],
    [kept, at(kept, "a = 1") + 8, "a nested fence's indented blank line, at its line feed"],
    [ind, at(ind, "alpha = 1") + 10, "an indented block's blank line"],
  ];
  for (const [src, off, label] of shapes) {
    const b = buildRendered(src);
    assert.deepEqual(rowTexts(find(b, "PRE", "= 1")).length, 3, label + ": three rows");
    assert.deepEqual(paintChangesRendered(El(b), src, [del("n", off)], () => ({})), { painted: ["n"], unpainted: [] }, label);
    const pt = pointOf(b, "n");
    assert.equal(rowIndexOf(pt), 1, label + ": in the blank line's row");
    assert.ok(hasClass(pt.parentNode!, "ct") && (pt.parentNode as FakeElement).childNodes.length === 1, label + ": the empty cell holds the point alone");
  }
  // CRLF: the blank line's CR and its LF both place in its row
  const crlf = "Intro.\r\n\r\n```\r\nfirst = 1\r\n\r\nthird = 3\r\n```\r\n";
  const cb = buildRendered(crlf);
  const cr = at(crlf, "first = 1") + "first = 1".length + 2;   // the blank line's CR
  assert.equal(crlf.slice(cr, cr + 2), "\r\n");
  assert.deepEqual(paintChangesRendered(El(cb), crlf, [del("cr", cr), del("lf", cr + 1)], () => ({})), { painted: ["cr", "lf"], unpainted: [] });
  assert.deepEqual([rowIndexOf(pointOf(cb, "cr")), rowIndexOf(pointOf(cb, "lf"))], [1, 1], "CRLF: both bytes of the blank line's ending place in its row");
  // a pre no renderer cut into rows offers no box for the line: the point falls back on the rule before, before the next line's first character
  const plain = undressed(SRC);
  assert.equal(rowsOf(find(plain, "PRE", "first = 1")).length, 0, "no rows");
  assert.deepEqual(paintChangesRendered(El(plain), SRC, [del("blank", blank)], () => ({})), { painted: ["blank"], unpainted: [] });
  const [before, after] = around(find(plain, "PRE", "first = 1"), pointOf(plain, "blank"));
  assert.ok(before.endsWith("first = 1\n\n") && after.startsWith("third = 3"), "undressed: before the next line's first character: " + JSON.stringify([before.slice(-4), after.slice(0, 5)]));
});

test("a CRLF note's code line endings: the point at the CR byte and the point at the LF byte of an inner line's ending both sit after the line's last character in its own row (the review's round 3; before: the LF byte's fell before the next line's first character, one row down, so the point read as that line changed, while the Raw view puts both bytes' points on the line they end), and both bytes of the LAST code line's ending sit after its last character (before: the LF byte's kept its card, strictly inside the closer's hole, whose first position is the CR's); a point inside a line is the control", () => {
  const src = "Intro.\r\n\r\n```\r\nc_one = 1\r\nc_two = 22\r\n```\r\n\r\nAfter.\r\n";
  const box = buildRendered(src);
  const pre = find(box, "PRE", "c_one = 1");
  assert.deepEqual(rowTexts(pre), ["c_one = 1", "c_two = 22"]);
  const del = (id: string, curFrom: number): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText: "gone", author: "web" });
  const one = at(src, "c_one = 1") + "c_one = 1".length, two = at(src, "c_two = 22") + "c_two = 22".length;
  assert.deepEqual([src.slice(one, one + 2), src.slice(two, two + 2)], ["\r\n", "\r\n"], "each line's ending is the two bytes");
  const res = paintChangesRendered(El(box), src, [del("one-cr", one), del("one-lf", one + 1), del("two-cr", two), del("two-lf", two + 1), del("in-two", two - 2)], () => ({}));
  assert.deepEqual(res, { painted: ["one-cr", "one-lf", "two-cr", "two-lf", "in-two"], unpainted: [] }, "every point places (before: two-lf kept its card)");
  assert.deepEqual(["one-cr", "one-lf", "two-cr", "two-lf", "in-two"].map((id) => rowIndexOf(pointOf(box, id))), [0, 0, 1, 1, 1], "each ending's two bytes in the line's own row (before: one-lf in row 1)");
  const rows = rowsOf(pre);
  for (const id of ["one-cr", "one-lf"]) assert.deepEqual(around(rows[0], pointOf(box, id)), ["c_one = 1", ""], id + ": after the line's last character");
  for (const id of ["two-cr", "two-lf"]) assert.deepEqual(around(rows[1], pointOf(box, id)), ["c_two = 22", ""], id + ": after the line's last character");
  assert.deepEqual(around(rows[1], pointOf(box, "in-two")), ["c_two = ", "22"], "the control: inside the line");
  assert.deepEqual(rowTexts(pre), ["c_one = 1", "c_two = 22"], "the rows' text is untouched");
  unpaintChanges(El(box));
  assert.equal(allOf(box, "SPAN").filter((e) => hasClass(e, "fc-del")).length, 0, "unpainted");
});

// ── the shapes marked accepts ──

test("shapes marked accepts map line by line: a fence with an info string and a padded closer, a four-backtick fence holding a ``` line, a tilde fence holding one, a fence closed by a longer run, a three-space opener whose lines carry less indent than it, a quoted fence with a bare `>` line inside it, an indented block under a list item, a note that opens on a fence and one that ends right after a closer with no line feed, a line of escaped characters, a fence inside a fence inside a quote, and a note ending inside a quoted fence", () => {
  const info = "```py  \nx = 1\n```   \n\nAfter.\n";
  let box = buildRendered(info);
  mapsWhole(box, info, "x = 1"); mapsWhole(box, info, "After.");
  const four = "````\n```\ninner\n```\n````\n";
  box = buildRendered(four);
  assert.deepEqual(rowTexts(find(box, "PRE", "inner")), ["```", "inner", "```"]);
  mapsWhole(box, four, "inner");
  assert.equal(ok(mapText(box, four, "```", 1, find(box, "PRE", "inner")), "the inner closer-shaped line").range.start, four.lastIndexOf("```\n````"), "the second ``` row is the inner line before the four-backtick closer");
  const tildes = "~~~\n```\nx\n```\n~~~\n";
  box = buildRendered(tildes);
  assert.deepEqual(rowTexts(find(box, "PRE", "x")), ["```", "x", "```"]);
  mapsWhole(box, tildes, "x");
  const longer = "```\nx = 2\n`````\n\nAfter.\n";
  box = buildRendered(longer);
  mapsWhole(box, longer, "x = 2"); mapsWhole(box, longer, "After.");
  const three = "   ```\n x = 3\n      y = 4\n   ```\n";
  box = buildRendered(three);
  assert.deepEqual(rowTexts(find(box, "PRE", "x = 3")), [" x = 3", "   y = 4"], "a line with less indent than the opener keeps it; one with more loses the opener's three");
  mapsWhole(box, three, "x = 3"); mapsWhole(box, three, "y = 4");
  const bare = "> ```\n> a = 1\n>\n> b = 2\n> ```\n";
  box = buildRendered(bare);
  assert.deepEqual(rowTexts(find(box, "PRE", "a = 1")), ["a = 1", "", "b = 2"]);
  mapsWhole(box, bare, "a = 1"); mapsWhole(box, bare, "b = 2");
  assert.equal(ok(mapSpan(box, bare, "a = 1", "b = 2"), "across the bare marker line").quote, "a = 1\n>\n> b = 2");
  const listed = "- item\n\n      code = 5\n\n- next\n";
  box = buildRendered(listed);
  assert.deepEqual(rowTexts(find(box, "PRE", "code = 5")), ["code = 5"]);
  mapsWhole(box, listed, "code = 5"); mapsWhole(box, listed, "next");
  const opens = "```\nfirst = 1\n```\n\nAfter.\n";
  box = buildRendered(opens);
  mapsWhole(box, opens, "first = 1"); mapsWhole(box, opens, "After.");
  const ends = "Before.\n\n```\nlast = 1\n```";
  box = buildRendered(ends);
  mapsWhole(box, ends, "Before."); mapsWhole(box, ends, "last = 1");
  const escaped = "```\nif a < b && c > d: print(\"<b>&amp;</b>\")\n```\n";
  box = buildRendered(escaped);
  assert.deepEqual(rowTexts(find(box, "PRE", "if a")), ["if a < b && c > d: print(\"<b>&amp;</b>\")"], "the renderer's escapes decode back to the source's characters");
  mapsWhole(box, escaped, "if a < b && c > d: print(\"<b>&amp;</b>\")");
  const nested = "> - item\n>\n>   ```\n>   deep = 6\n>   ```\n";
  box = buildRendered(nested);
  mapsWhole(box, nested, "deep = 6");
  assert.equal(ok(mapSpan(box, nested, "item", "deep = 6"), "the item's text into the nested fence").quote, "item\n>\n>   ```\n>   deep = 6");
  const unclosedQuote = "> intro\n>\n> ```\n> tail = 7\n";
  box = buildRendered(unclosedQuote);
  assert.deepEqual(rowTexts(find(box, "PRE", "tail")), ["tail = 7"]);
  mapsWhole(box, unclosedQuote, "tail = 7"); mapsWhole(box, unclosedQuote, "intro");
});

test("a tab-indented fence inside a list item, a fence whose lines open with tabs at every depth, and a fence right after a list (no blank line) each map their lines, the tab bytes inside a two-line quote", () => {
  const item = "- item\n\n\t```\n\tin_item = 1\n\t\tdeeper = 2\n\t```\n";
  let box = buildRendered(item);
  assert.deepEqual(rowTexts(find(box, "PRE", "in_item")), ["in_item = 1", "    deeper = 2"], "the item's tab is its indent; the second line keeps one tab's four spaces");
  mapsWhole(box, item, "in_item = 1"); mapsWhole(box, item, "deeper = 2");
  assert.equal(ok(mapSpan(box, item, "in_item = 1", "deeper = 2"), "two tab-opened lines").quote, "in_item = 1\n\t\tdeeper = 2");
  const tabs = "```\n\tone = 1\n\t\ttwo = 2\n\t\t\tthree = 3\n```\n";
  box = buildRendered(tabs);
  assert.deepEqual(rowTexts(find(box, "PRE", "one")), ["    one = 1", "        two = 2", "            three = 3"]);
  for (const t of ["one = 1", "two = 2", "three = 3"]) mapsWhole(box, tabs, t);
  assert.equal(ok(mapSpan(box, tabs, "one = 1", "three = 3"), "three tab-opened lines").quote, "one = 1\n\t\ttwo = 2\n\t\t\tthree = 3");
  const after = "- a\n- b\n```\nc = 3\n```\n";
  box = buildRendered(after);
  mapsWhole(box, after, "c = 3"); mapsWhole(box, after, "b");
});

test("the Raw offer stands where the mapping still refuses: a selection from a code line into an html block after it names the html block with the Raw view at the block, the code and the table between them no obstacle (since decision 53 of plans/file-review.md a selection across cells anchors; Slice 8 named the one-cell rule here), and one from a code line across the table's cells anchors, the fence's closer and the table's rows inside the quote", () => {
  const src = "```\ncode line one\ncode line two\n```\n\n| Col A | Col B |\n|-------|-------|\n| cell one | cell two |\n\n<div class=\"note\">Html block text</div>\n\nAfter para.\n";
  const box = buildRendered(src);
  const pre = find(box, "PRE", "code line one");
  const html = bad(mapRenderedSelection(sel(point(pre, "code line two"), point(box, "Html block text", true)), El(box), src), "the second code line to the html block");
  assert.match(html.reason, /an HTML block/, "the html block is the first obstacle (before: the one-cell rule; before Slice 8: the code block itself): " + html.reason);
  assert.equal(html.blockStartOffset, at(src, "<div"));
  const across = ok(mapRenderedSelection(sel(point(pre, "code line two"), point(box, "cell two", true)), El(box), src), "the second code line across the table's cells (before: the one-cell rule)");
  assert.equal(across.quote, "code line two\n```\n\n| Col A | Col B |\n|-------|-------|\n| cell one | cell two");
  const noTable = "```\ncode line one\n```\n\n<div class=\"note\">Html block text</div>\n\nAfter para.\n";
  const box2 = buildRendered(noTable);
  const r = bad(mapSpan(box2, noTable, "code line one", "Html block text"), "the code line to the html block");
  assert.match(r.reason, /an HTML block/, "the html block is the obstacle (before: the code block): " + r.reason);
  assert.equal(r.blockStartOffset, at(noTable, "<div"));
  mapsWhole(box2, noTable, "code line one");
  mapsWhole(box2, noTable, "After para.");
});

// ── the cost, for the build note (the brief's open question 13) ──

test("a 5,000-line fence: the index builds, one selection maps and forty marks paint (the numbers are diagnostics for the build note, not a bound)", (t) => {
  const lines = Array.from({ length: 5000 }, (_, i) => "line_" + i + " = value_" + i);
  const src = "# Big\n\nIntro paragraph.\n\n```\n" + lines.join("\n") + "\n```\n\nAfter paragraph.\n";
  const box = buildRendered(src);
  const pre = find(box, "PRE", "line_4999");
  let t0 = process.hrtime.bigint();
  const r = ok(mapText(box, src, "line_2500 = value_2500", 0, pre), "a line deep in the fence");
  const tMap = Number(process.hrtime.bigint() - t0) / 1e6;
  assert.deepEqual(r.range, rangeOf(src, "line_2500 = value_2500"));
  t0 = process.hrtime.bigint();
  const painted: FakeElement[] = [];
  for (let k = 0; k < 40; k++) painted.push(...marksOf(box, src, rangeOf(src, "line_" + (k * 100) + " = value_" + (k * 100)), "fc-hl"));
  const tPaint = Number(process.hrtime.bigint() - t0) / 1e6;
  assert.equal(textMarks(painted).length, 40, "forty marks, one per line");
  t.diagnostic("5,000-line fence on the stand-in: index build plus one map " + tMap.toFixed(1) + " ms, forty marks " + tPaint.toFixed(1) + " ms");
});
