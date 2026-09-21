// anchor-map.ts driven behaviorally over the viewer's two DOM shapes, rebuilt here exactly as
// file-view.ts builds them (its Raw rows and marked configuration are replicated and pinned to the
// source, the repo's convention) and parsed into a small DOM stand-in — there is no jsdom in this tree.
// DOMPurify is not applied: it needs a window, and the mapping reads only text nodes, which the sanitizer
// keeps as they are with one exception: an element in its FORBID_CONTENTS set (script always, style since
// md-sanitize.ts forbade the tag) goes with its text, so a paragraph carrying one mid-line maps here and is
// refused in the viewer as a rendered-text mismatch; md-sanitize-anchor-map-browser.test.ts pins that shape
// over the real sanitizer. Fixtures are synthetic (a notes-api world) and live in anchor-map-fixtures/. The Rendered
// shape's HTML follows mdBlock's parse step by step (viewerHtml, below): marked's lexer, the literal-tags rule of
// md-literal-tags.ts (an inline start tag with no end tag in its block is literal text, decision 52 of plans/file-review.md),
// its parser; the fixtures hold no such tag, so the HTML is marked.parse's for them, and a note that holds one renders here
// as the viewer renders it.
import { test } from "node:test";
import assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import { pathToFileURL } from "node:url";
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import xml from "highlight.js/lib/languages/xml";
import cssLang from "highlight.js/lib/languages/css";
import markdown from "highlight.js/lib/languages/markdown";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";   // the one markdown configuration, applied here as the viewer applies it
import { viewerHtml } from "./file-view";   // the viewer's parse (mdBlock's recipe: marked's lexer, the literal-tags rule of md-literal-tags.ts, the per-call walk, its parser), the stand-in's too
import {
  mapRawSelection, mapRenderedSelection, makeAnchor, locateComment, paintRaw, paintRendered,
  rawOffsetToLine, rawRowForOffset, type SelLike, type MapResult, type SourceRange,
  paintRawPoint, paintChangesRaw, paintChangesRendered, unpaintChanges, deletionLabel, DEL_LABEL_MAX, PILCROW, type ChangePaint,
  sourceBlockSpans, renderedBlockIndex, renderedBlockElements, rawRows, rawRowSpan,
} from "./anchor-map";
// @ts-ignore -- untyped CommonJS module (see anchor-map.ts)
import engine from "../../vendor/track-changents/engine.js";
import { hideEdges, sameNodes, staysEnumerable } from "../test-dom-shim";

const FIX = (f: string) => path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map-fixtures", f);
const fixture = (f: string) => fs.readFileSync(FIX(f), "utf8");
const VIEW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8");
// The host script that places every passage comment (tools/file-comments-host.mjs), loaded as the real ESM module at
// run time for the tie tests below — bundling it would copy its vendored engine; its main runs only when invoked directly.
const HOST = path.resolve(process.cwd(), "..", "tools", "file-comments-host.mjs");
type HostAnchor = { quote: string; prefix: string; suffix: string };
type HostModule = {
  locateExact(text: string, anchor: HostAnchor, hint: number | undefined, opts?: { exact?: boolean }): { from: number; to: number } | { error: string };
  buildComment(text: string, args: { note: string; anchor?: HostAnchor; hintOffset?: number }, now: number, suggestions: unknown[]):
    { comment: { anchorAt?: number }; range?: { from: number; to: number } } | { error: string };
};

// ── the viewer's marked configuration: the one every bundle applies (md-config.ts; pinned by anchor-map.test.ts) ──
applyMdConfig();
for (const [name, lang] of Object.entries({ python, py: python, xml, html: xml, css: cssLang, markdown, md: markdown })) {
  try { hljs.registerLanguage(name, lang as any); } catch { /* dup */ }
}

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser ─────
class FakeNode {
  nodeType = 0;
  parentNode!: FakeNode | null;
  childNodes!: FakeNode[];
  constructor(public ownerDocument: FakeDocument) {
    // the edges are non-enumerable, and so is every other object the node holds (hideEdges, ui/test-dom-shim.ts): a
    // failing assertion's dump of a node is its own primitives, never the tree it hangs in
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get textContent(): string { return this.nodeType === 3 ? (this as unknown as FakeText).data : this.childNodes.map((c) => c.textContent).join(""); }
}
class FakeText extends FakeNode {
  nodeType = 3;
  constructor(doc: FakeDocument, public data: string) { super(doc); hideEdges(this); }
  get length(): number { return this.data.length; }
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
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: "\u00a0", copy: "\u00a9" };
function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
    return e in NAMED ? NAMED[e] : m;
  });
}
/** The HTML fragment parser a browser's innerHTML applies, reduced to what marked and hljs emit:
 *  CR and CRLF become LF before tokenizing, entities decode, void elements do not nest, a newline right
 *  after <pre> is dropped. */
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

// ── the viewer's two DOM shapes, replicated from file-view.ts ─────────────────────────────────────
const LANG: Record<string, string> = { py: "python", html: "xml", htm: "xml", xml: "xml", svg: "xml", css: "css", md: "markdown" };
const langFor = (p: string): string | null => LANG[p.slice(p.lastIndexOf(".") + 1).toLowerCase()] || null;
const escapeHtml = (s: string): string => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
// replica of file-view.ts wrapNumberedHtml (pinned below): since Slice 7 of plans/markdown-viewer.md (item 7, contract C6) the
// rows split on CRLF, a lone CR and LF alike, the viewer's RAW_ROW_SPLIT, so no row's text carries a "\r". `split` is the
// one line the two builders below differ in.
function wrapNumbered(html: string, split: RegExp | string): string {
  const lines = html.split(split);
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  let open: string[] = [];
  return lines.map((ln) => {
    const prefix = open.join("");
    const re = /<span[^>]*>|<\/span>/g; let m; const stack = open.slice();
    while ((m = re.exec(ln))) { if (m[0] === "</span>") stack.pop(); else stack.push(m[0]); }
    const suffix = "</span>".repeat(Math.max(0, stack.length));
    open = stack;
    return `<span class="fv-cl"><span class="fv-ct">${prefix}${ln}${suffix}</span></span>`;
  }).join("");
}
const wrapNumberedHtml = (html: string): string => wrapNumbered(html, /\r\n|\r|\n/);
// The Raw grid as the viewer built it BEFORE Slice 7: an LF-only split, so a CRLF source's rows each carried a "\r" (which
// parseHTML normalises as the browser does) and a lone CR stayed inside its row. The cases built on `buildRaw` were written
// over that grid (their offsets, row counts and quotes assume it), and the map takes whatever rows it is given, verifying them
// against the source character by character, so they keep it as the map's input; the viewer's rows since Slice 7 are the
// replica's above (buildRawSplit and the three-ending cases). Re-aiming the replica alone turned nine of them red, so the
// consolidation pass of Slice 7 kept the older grid here by name rather than re-derive them (recorded in the plan note).
// Both grids are inputs the map takes, and both are built here: `buildRaw` the older one for those cases, `buildRawViewer`
// the viewer's for the two cases after paintRawPoint's, which lay the CRLF fixture and four small sources on the three-ending
// split and paint points, highlights and changes over them (Slice 7's review, round 1: until then the painters over a CR or
// CRLF source on the viewer's own rows had no node case; the three-ending case covers the map's index, not the painters).
const wrapNumberedHtmlLf = (html: string): string => wrapNumbered(html, "\n");
type RawDom = { body: FakeElement; before: FakeElement; after: FakeElement; wrap: FakeElement; code: FakeElement };
/** `.fileview-body > div.fileview-code > pre > code.hljs > rows`, with a sibling before and after; `rowsOf` lays the rows. */
function buildRawWith(rowsOf: (html: string) => string, text: string, filePath: string): RawDom {
  const doc = new FakeDocument();
  const lang = langFor(filePath);
  let hl: string | null = null;
  if (lang) hl = hljs.highlight(text, { language: lang }).value;
  const body = doc.createElement("div"); body.setAttribute("class", "fileview-body");
  const before = doc.createElement("div"); before.setAttribute("class", "fileview-actions"); before.appendChild(doc.createTextNode("Rendered · Raw"));
  const wrap = doc.createElement("div"); wrap.setAttribute("class", "fileview-code");
  const pre = doc.createElement("pre"); pre.setAttribute("class", "fileview-pre fileview-wrap");
  const code = doc.createElement("code"); code.setAttribute("class", "hljs");
  for (const n of parseHTML(doc, rowsOf(hl !== null ? hl : escapeHtml(text)))) code.appendChild(n);
  pre.appendChild(code); wrap.appendChild(pre);
  const after = doc.createElement("div"); after.setAttribute("class", "fileview-footer"); after.appendChild(doc.createTextNode("footer text"));
  body.appendChild(before); body.appendChild(wrap); body.appendChild(after);
  return { body, before, after, wrap, code };
}
/** The older grid (wrapNumberedHtmlLf), which the cases built on it were written over. */
function buildRaw(text: string, filePath: string): RawDom { return buildRawWith(wrapNumberedHtmlLf, text, filePath); }
/** The viewer's grid since Slice 7 (the replica wrapNumberedHtml: the three-ending split), the highlighter included. */
function buildRawViewer(text: string, filePath: string): RawDom { return buildRawWith(wrapNumberedHtml, text, filePath); }
type MdDom = { body: FakeElement; box: FakeElement; before: FakeElement };
/** `.fileview-body > div.fileview-md > marked output` (mdBlock without DOMPurify, see the header). */
function buildRendered(text: string): MdDom {
  const doc = new FakeDocument();
  const body = doc.createElement("div");
  const before = doc.createElement("div"); before.appendChild(doc.createTextNode("Rendered · Raw"));
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, viewerHtml(text))) box.appendChild(n);
  body.appendChild(before); body.appendChild(box);
  return { body, box, before };
}
const El = (n: FakeNode) => n as unknown as Element;

// ── selection helpers ───────────────────────────────────────────────────────────────────────────────
type Pt = { node: FakeNode; offset: number };
const sel = (a: Pt, f: Pt): SelLike => ({ anchorNode: a.node as unknown as Node, anchorOffset: a.offset, focusNode: f.node as unknown as Node, focusOffset: f.offset, isCollapsed: a.node === f.node && a.offset === f.offset });
function allText(root: FakeNode, counts: ((el: FakeElement) => boolean) | null, inCounted = false): FakeText[] {
  if (root.nodeType === 3) return inCounted || !counts ? [root as FakeText] : [];
  const here = inCounted || !counts || counts(root as FakeElement);
  const out: FakeText[] = [];
  for (const c of root.childNodes) out.push(...allText(c, counts, here));
  return out;
}
const isRow = (el: FakeElement) => (el.getAttribute("class") || "").split(" ").includes("fv-cl");
/** Every DOM boundary at global text index g under root: text-node boundaries first, then element
 *  boundaries climbing while the position is at an edge (the two ways a browser reports one spot). */
function boundaries(root: FakeNode, g: number, counts: ((el: FakeElement) => boolean) | null): { text: Pt[]; elem: Pt[] } {
  const nodes = allText(root, counts);
  const text: Pt[] = [], elem: Pt[] = [];
  let cum = 0;
  for (const t of nodes) {
    const len = t.data.length;
    if (g > cum && g < cum + len) { text.push({ node: t, offset: g - cum }); }
    if (g === cum || g === cum + len) {
      text.push({ node: t, offset: g - cum });
      let n: FakeNode = t;
      const atEnd = g === cum + len;
      while (n.parentNode && n !== root) {
        const p = n.parentNode;
        const i = p.childNodes.indexOf(n);
        if (atEnd ? i !== p.childNodes.length - 1 && n !== t : i !== 0 && n !== t) break;
        elem.push({ node: p, offset: atEnd ? i + 1 : i });
        if (atEnd ? i !== p.childNodes.length - 1 : i !== 0) break;
        n = p;
      }
    }
    cum += len;
  }
  return { text, elem };
}
const domText = (root: FakeNode, counts: ((el: FakeElement) => boolean) | null) => allText(root, counts).map((t) => t.data).join("");
const ok = (r: MapResult, msg?: string) => { assert.equal(r.ok, true, msg || ("expected ok, got refusal: " + (r as { reason?: string }).reason)); return r as Extract<MapResult, { ok: true }>; };
const bad = (r: MapResult, msg?: string) => { assert.equal(r.ok, false, msg || "expected a refusal"); return r as Extract<MapResult, { ok: false }>; };
const stripWs = (s: string) => s.replace(/\s+/g, "");
const noEol = (s: string) => s.replace(/[\r\n]/g, "");
function isSubsequence(small: string, big: string): boolean {
  let j = 0;
  for (let i = 0; i < big.length && j < small.length; i++) if (big[i] === small[j]) j++;
  return j === small.length;
}
/** Source offset → global Raw DOM index, from the viewer's own "\n" split (one row per line). */
function rawDomIndexOf(source: string): (srcOff: number) => number | null {
  const lines = source.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  const starts: number[] = []; let p = 0;
  for (const ln of lines) { starts.push(p); p += ln.length + 1; }
  return (srcOff) => {
    for (let r = 0; r < lines.length; r++) {
      if (srcOff >= starts[r] && srcOff < starts[r] + lines[r].length) {
        let g = 0; for (let k = 0; k < r; k++) g += lines[k].length;
        return g + (srcOff - starts[r]);
      }
    }
    return null;   // a "\n" between rows has no DOM character
  };
}
/** Source offset → global Raw DOM index over the viewer's grid since Slice 7 (rows split on CRLF, a lone CR and LF, none
 *  carrying an ending): an offset on an ending's own character has no DOM character. */
function rawDomIndexOfSplit(source: string): (srcOff: number) => number | null {
  const rows: { start: number; len: number; dom: number }[] = [];
  let p = 0, g = 0;
  for (const m of source.matchAll(/\r\n|\r|\n/g)) { rows.push({ start: p, len: (m.index as number) - p, dom: g }); g += (m.index as number) - p; p = (m.index as number) + m[0].length; }
  if (p < source.length) rows.push({ start: p, len: source.length - p, dom: g });
  return (srcOff) => {
    for (const r of rows) if (srcOff >= r.start && srcOff < r.start + r.len) return r.dom + (srcOff - r.start);
    return null;
  };
}

// ── source pins: the DOM shapes this test rebuilds are the viewer's ──────────────────────────────
test("pins: the viewer's Raw rows, marked configuration, and lexer identity", () => {
  assert.match(VIEW, /return `<span class="fv-cl"><span class="fv-ct">\$\{prefix\}\$\{ln\}\$\{suffix\}<\/span><\/span>`;/);
  assert.match(VIEW, /^const RAW_ROW_SPLIT = \/\\r\\n\|\\r\|\\n\/;$/m,
    "one module-level regex: a CRLF as one ending, then a lone CR, then LF (Slice 7 of plans/markdown-viewer.md, item 7; contract C6)");
  assert.match(VIEW, /const lines = html\.split\(RAW_ROW_SPLIT\);\n\s+if \(lines\.length && lines\[lines\.length - 1\] === ""\) lines\.pop\(\);/,
    "the rows split on it, the one trailing empty piece popped (the replica above follows)");
  // the viewer's configuration is the one every bundle applies (md-config.ts, Slice 4 of plans/markdown-viewer.md): the
  // viewer calls it at load, as this suite does, and holds no options of its own
  const CONFIG = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "md-config.ts"), "utf8");
  assert.match(VIEW, /^applyMdConfig\(\);/m);
  assert.doesNotMatch(VIEW, /marked\.(setOptions|use)\(/, "file-view.ts configures nothing of its own");
  assert.match(CONFIG, /marked\.setOptions\(\{ gfm: true, breaks: false \}\);/);
  assert.match(CONFIG, /const m = \/\^~~\(\?=\\S\)\(\[\\s\\S\]\*\?\\S\)~~\/\.exec\(src\);/);
  // the viewer's parse carries its link-target hook (file-view-links.ts viewerWalkTokens) as a PER-CALL option: the tokens are
  // marked's own, so the shapes replicated here are unchanged; only a link token's href is rewritten before the render, and only
  // for the file kind (the 2026-09-07 fold: a URL document takes marked's defaults). The walkTokens itself runs for every kind
  // since the Slice 3 review, collecting the code tokens for the fence pass's Copy (fence-source.ts); it reads them, never
  // rewrites them, so the lexer's shapes stand. Since decision 52 the parse is marked.parse's three steps called apart (its lexer,
  // the walk, its parser, over a copy of the defaults as marked.parse copies them), with the literal-tags rule between the lexer and
  // the walk (md-literal-tags.ts): the one rewrite of the tokens, and the same one this map applies after its own lex (placeTokens).
  // Since that decision's review (2026-09-19) the three steps are the exported viewerHtml, the recipe this suite's stand-in renders
  // through too, and mdBlock hands it the walk
  assert.match(VIEW, /export function viewerHtml\(text: string, walk\?: \(token: Token\) => void\): string \{\n\s*const opts = \{ \.\.\.marked\.defaults \};\n\s*const tokens = marked\.lexer\(text, opts\);\n\s*literalizeUnclosedTags\(tokens\);\n\s*if \(walk\) marked\.walkTokens\(tokens, walk\);\n\s*return marked\.parser\(tokens, opts\);\n\}/);
  assert.match(VIEW, /const dirty = viewerHtml\(text, \(t\) => \{\n\s*if \(t\.type === "code"\) \{ const c = t as Tokens\.Code; fences\.push\(\{ text: c\.text, indented: c\.codeBlockStyle === "indented" \}\); \}\n\s*if \(doc && doc\.kind === "file"\) viewerWalkTokens\(t\);\n\s*if \(base\) void base\.call\(marked, t\);\n\s*\}\);/);  const MAP = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map.ts"), "utf8");
  assert.match(MAP, /try \{ tokens = Lexer\.lex\(N\); literalizeUnclosedTags\(tokens\); \}/, "the walk lexes with the viewer's configured singleton (no private options) and runs the literal-tags rule right after its lex, as the viewer's parse does (md-literal-tags.ts)");
  assert.doesNotMatch(MAP, /marked\.(setOptions|use)\(/, "anchor-map holds no options of its own: it applies the one configuration (applyMdConfig) and lexes under it");
  assert.match(MAP, /^applyMdConfig\(\);/m, "…at load, so the static lexer sees every extension the renderer has, whichever module loaded first");
  assert.match(MAP, /from "\.\.\/\.\.\/vendor\/track-changents\/engine\.js"/, "the engine comes from the vendored copy (contract C4)");
});

// ── Raw: the offset grid over the CRLF fixture ─────────────────────────────────────────────────────
test("Raw grid: every offset pair with non-whitespace ends maps to the exact source slice (CRLF, tabs, lone CR, highlight spans, trailing newline)", () => {
  const source = fs.readFileSync(FIX("handlers-crlf.py"), "utf8");
  assert.ok(/\r\n/.test(source) && /\t/.test(source) && /\r[^\n]/.test(source) && source.endsWith("\n"), "fixture shape");
  const { wrap, code } = buildRaw(source, "handlers-crlf.py");
  assert.ok(allText(code, null).some((t) => (t.parentNode as FakeElement).getAttribute("class")?.startsWith("hljs-")), "highlight spans present");
  const domIdx = rawDomIndexOf(source);
  let pairs = 0, elemPairs = 0;
  for (let i = 0; i < source.length; i++) {
    if (/\s/.test(source[i])) continue;
    for (let j = i + 1; j <= source.length; j++) {
      if (/\s/.test(source[j - 1])) continue;
      const gs = domIdx(i), ge = domIdx(j - 1);
      assert.ok(gs !== null && ge !== null);
      const bs = boundaries(code, gs as number, isRow), be = boundaries(code, (ge as number) + 1, isRow);
      const expect = source.slice(i, j);
      const check = (r: MapResult, label: string) => {
        const o = ok(r, `${label} [${i},${j}) → ${(r as { reason?: string }).reason}`);
        assert.equal(o.quote, expect, `${label} [${i},${j})`);
        assert.deepEqual(o.range, { start: i, end: j });
      };
      // text-node boundaries, forward and backward, against both candidate roots
      check(mapRawSelection(sel(bs.text[0], be.text[0]), El(code), source), "text/code");
      check(mapRawSelection(sel(be.text[0], bs.text[0]), El(wrap), source), "text/wrap backward");
      pairs++;
      // element boundaries where the spot is an element edge (the outermost one a browser could report)
      if (bs.elem.length && be.elem.length) {
        check(mapRawSelection(sel(bs.elem[bs.elem.length - 1], be.elem[be.elem.length - 1]), El(code), source), "elem/elem");
        elemPairs++;
      }
      if (bs.elem.length) check(mapRawSelection(sel(bs.elem[0], be.text[be.text.length - 1]), El(code), source), "elem/text");
    }
  }
  assert.ok(pairs > 20000, "grid size " + pairs);
  assert.ok(elemPairs > 100, "element-boundary pairs " + elemPairs);
});

test("Raw: the quote keeps interior CRLF and a lone CR exactly as the file has them", () => {
  const source = fs.readFileSync(FIX("handlers-crlf.py"), "utf8");
  const { code } = buildRaw(source, "handlers-crlf.py");
  const domIdx = rawDomIndexOf(source);
  // across two lines: from "if" on line 3 to the closing paren of the return on line 4
  const i = source.indexOf("if note is None"), j = source.indexOf('"missing")') + '"missing")'.length;
  const r = ok(mapRawSelection(sel(boundaries(code, domIdx(i) as number, isRow).text[0], boundaries(code, (domIdx(j - 1) as number) + 1, isRow).text[0]), El(code), source));
  assert.equal(r.quote, 'if note is None:\r\n\t\treturn respond(404, "missing")');
  // across the lone CR: the DOM shows a line break there; the quote keeps the "\r"
  const a = source.indexOf("comment"), b = source.indexOf("and this text") + "and".length;
  const r2 = ok(mapRawSelection(sel(boundaries(code, domIdx(a) as number, isRow).text[0], boundaries(code, (domIdx(b - 1) as number) + 1, isRow).text[0]), El(code), source));
  assert.equal(r2.quote, "comment\rand");
  // the "<" the highlighter escaped comes back as one character
  const c = source.indexOf("5 < 10"), d = c + "5 < 10".length;
  assert.equal(ok(mapRawSelection(sel(boundaries(code, domIdx(c) as number, isRow).text[0], boundaries(code, (domIdx(d - 1) as number) + 1, isRow).text[0]), El(code), source)).quote, "5 < 10");
});

test("Raw: whitespace at the selection's edges is trimmed; an all-whitespace selection refuses", () => {
  const source = "alpha  beta\n\tgamma\n";
  const { code } = buildRaw(source, "notes.txt");
  const t = allText(code, isRow);
  // "alpha  " → "alpha"
  let r = ok(mapRawSelection(sel({ node: t[0], offset: 0 }, { node: t[0], offset: 7 }), El(code), source));
  assert.equal(r.quote, "alpha"); assert.deepEqual(r.range, { start: 0, end: 5 });
  // "  beta" + the whole tabbed row → "beta\n\tgamma"
  r = ok(mapRawSelection(sel({ node: t[0], offset: 5 }, { node: t[1], offset: 6 }), El(code), source));
  assert.equal(r.quote, "beta\n\tgamma");
  const w = bad(mapRawSelection(sel({ node: t[0], offset: 5 }, { node: t[0], offset: 7 }), El(code), source));
  assert.match(w.reason, /whitespace/);
  bad(mapRawSelection({ anchorNode: t[0] as unknown as Node, anchorOffset: 2, focusNode: t[0] as unknown as Node, focusOffset: 2, isCollapsed: true }, El(code), source));
});

test("Raw: a selection ending past the last row snaps to it when the container is an ancestor, and refuses from a sibling", () => {
  const source = fs.readFileSync(FIX("handlers-crlf.py"), "utf8");
  const { body, before, after, wrap, code } = buildRaw(source, "handlers-crlf.py");
  const domIdx = rawDomIndexOf(source);
  const start = boundaries(code, domIdx(source.indexOf("LIMIT")) as number, isRow).text[0];
  // focus after the code's wrapper inside the body (an ancestor of the code element) → the last row's end
  const r = ok(mapRawSelection(sel(start, { node: body, offset: body.childNodes.indexOf(wrap) + 1 }), El(code), source));
  assert.equal(r.quote, "LIMIT = 5 < 10  # a lone CR follows this comment\rand this text sits after it");
  assert.equal(r.range.end, source.length - 2, "the trailing CRLF is not part of the quote");
  // anchor before the wrapper → the first row's start
  const r2 = ok(mapRawSelection(sel({ node: body, offset: 0 }, boundaries(code, domIdx(source.indexOf("note_id):")) as number, isRow).text[0]), El(code), source));
  assert.equal(r2.range.start, 0);
  assert.ok(r2.quote.startsWith("def get_note(store,"));
  // focus inside the footer (a sibling, not an ancestor) → refusal
  const f = after.childNodes[0];
  const bad1 = bad(mapRawSelection(sel(start, { node: f, offset: 3 }), El(code), source));
  assert.match(bad1.reason, /outside/);
  bad(mapRawSelection(sel({ node: before.childNodes[0], offset: 0 }, start), El(code), source));
});

test("Raw: rows that disagree with the source refuse instead of guessing", () => {
  const shown = "one\ntwo\nthree\n";
  const { code } = buildRaw(shown, "notes.txt");
  const t = allText(code, isRow);
  const r = bad(mapRawSelection(sel({ node: t[0], offset: 0 }, { node: t[2], offset: 5 }), El(code), "one\nTWO\nthree\n"));
  assert.match(r.reason, /does not match the file text/);
  assert.equal(r.rawHasQuote, false);
  // and the same DOM against its own source is fine
  assert.equal(ok(mapRawSelection(sel({ node: t[0], offset: 0 }, { node: t[2], offset: 5 }), El(code), shown)).quote, "one\ntwo\nthree");
});

// ── Raw: painting after reload ──────────────────────────────────────────────────────────────────────
test("Raw paint: after a reload the highlight wraps exactly the text nodes of the slice, for a sample of the grid", () => {
  const source = fs.readFileSync(FIX("handlers-crlf.py"), "utf8");
  const nonWs: number[] = [];
  for (let i = 0; i < source.length; i++) if (!/\s/.test(source[i])) nonWs.push(i);
  let n = 0;
  for (let a = 0; a < nonWs.length; a += 7) {
    for (const span of [1, 3, 11, 37, 90, 400]) {
      const bIdx = a + span;
      if (bIdx >= nonWs.length) continue;
      const range: SourceRange = { start: nonWs[a], end: nonWs[bIdx] + 1 };
      const quote = source.slice(range.start, range.end);
      const { code, wrap } = buildRaw(source, "handlers-crlf.py");                 // the "reload"
      const totalBefore = domText(code, isRow);
      const marks = paintRaw(El(wrap), source, range, "fc-hl", { cid: "11111111-2222-3333-4444-555555555555", state: "located" }) as unknown as FakeElement[];
      assert.ok(marks.length >= 1, `marks for [${range.start},${range.end})`);
      const painted = marks.map((m) => m.textContent).join("");
      assert.equal(noEol(painted), noEol(quote), `painted text for [${range.start},${range.end})`);
      assert.equal(domText(code, isRow), totalBefore, "painting never changes the text");
      for (const m of marks) {
        assert.equal(m.tagName, "MARK");
        assert.equal(m.getAttribute("class"), "fc-hl");
        assert.equal(m.getAttribute("data-cid"), "11111111-2222-3333-4444-555555555555");
        assert.equal(m.getAttribute("data-state"), "located");
        let p: FakeNode | null = m; let inRow = false;
        while (p) { if (p.nodeType === 1 && isRow(p as FakeElement)) inRow = true; p = p.parentNode; }
        assert.ok(inRow, "every mark sits inside a row");
        assert.ok(m.childNodes.every((c) => c.nodeType === 3), "a mark wraps text nodes only");
      }
      // exactness: the text before the first mark and after the last mark is the rest of the file
      const all = allText(code, isRow);
      const firstIdx = all.indexOf(marks[0].childNodes[0] as FakeText);
      const lastMark = marks[marks.length - 1];
      const lastIdx = all.indexOf(lastMark.childNodes[lastMark.childNodes.length - 1] as FakeText);
      const beforeText = all.slice(0, firstIdx).map((t) => t.data).join("");
      const afterText = all.slice(lastIdx + 1).map((t) => t.data).join("");
      assert.equal(noEol(beforeText), noEol(source.slice(0, range.start)));
      assert.equal(noEol(afterText), noEol(source.slice(range.end)));
      // a stored range that covers a whole line plus its line ending paints the same visible text
      n++;
    }
  }
  assert.ok(n > 60, "sampled " + n);
  // the row lookup follows the verified map
  const { wrap } = buildRaw(source, "handlers-crlf.py");
  const row = rawRowForOffset(El(wrap), source, source.indexOf("def put_note")) as unknown as FakeElement;
  assert.ok(row && row.textContent.startsWith("def put_note"));
  assert.equal(rawRowForOffset(El(wrap), "different text", 0), null);
});

test("Raw paint: a range that ends inside a line ending paints only the line's text; a mismatched source paints nothing", () => {
  const source = "ab\r\ncd\r\n";
  const { code } = buildRaw(source, "notes.txt");
  const marks = paintRaw(El(code), source, { start: 0, end: 4 }, "fc-hl") as unknown as FakeElement[];   // "ab\r\n"
  // the row's DOM text is "ab\n" (CR shown as LF by the HTML parser): the "\n" standing for "\r" is inside the range
  assert.equal(marks.map((m) => m.textContent).join(""), "ab\n");
  assert.deepEqual(paintRaw(El(code), "ab\ncd\n", { start: 0, end: 2 }, "fc-hl"), [], "rows that do not match the text paint nothing");
});

// ── Raw: every text format ─────────────────────────────────────────────────────────────────────────
test("Raw: HTML, SVG, CSS, CSV, and code fixtures store the exact source slice", () => {
  const cases: [string, string][] = [
    ["index.html", "<strong>120 ms</strong>"],
    ["index.html", "notes-api &amp; friends"],
    ["logo.svg", 'fill="#9cd2ff"/>\n  <text x="32"'],
    ["styles.css", "color: var(--accent); }\n.lead strong"],
    ["latency.csv", "GET /notes/{id},12,35"],
    ["handlers-crlf.py", "store.get(note_id)\r\n\tif"],
  ];
  for (const [f, passage] of cases) {
    const source = fixture(f);
    const { code } = buildRaw(source, f);
    const domIdx = rawDomIndexOf(source);
    const i = source.indexOf(passage); assert.ok(i >= 0, f + " has " + passage);
    const j = i + passage.length;
    const r = ok(mapRawSelection(sel(boundaries(code, domIdx(i) as number, isRow).text[0], boundaries(code, (domIdx(j - 1) as number) + 1, isRow).text[0]), El(code), source), f);
    assert.equal(r.quote, passage, f);
    assert.deepEqual(r.range, { start: i, end: j });
    const anchor = makeAnchor(source, r.range);
    assert.deepEqual(locateComment(source, anchor, r.range.start), { state: "located", range: r.range });
  }
});

// ── the engine: anchors and relocation ─────────────────────────────────────────────────────────────
test("makeAnchor equals the engine's own anchor; locateComment reports located / context / detached", () => {
  const source = fixture("report.md");
  const start = source.indexOf("cut p95 latency"), end = start + "cut p95 latency".length;
  const a = makeAnchor(source, { start, end });
  assert.deepEqual(a, engine.makeAnchor(source, start, end));
  assert.deepEqual(a, engine.makeAnchor(source, start, end, 24));
  assert.equal(a.quote, "cut p95 latency");
  assert.equal(a.prefix.length, 24); assert.equal(a.suffix.length, 24);
  // moved: two lines inserted above
  const moved = "Preface line one.\n\nPreface line two.\n\n" + source;
  const shift = moved.length - source.length;
  assert.deepEqual(locateComment(moved, a, start), { state: "located", range: { start: start + shift, end: end + shift } });
  // altered: the quote is rewritten but its context survives → the between-context region
  const altered = source.replace("cut p95 latency", "halved p95 latency");
  const ctx = locateComment(altered, a, start);
  assert.equal(ctx.state, "context");
  assert.equal(altered.slice(ctx.range!.start, ctx.range!.end), "halved p95 latency");
  // removed: the passage and its context are gone
  const removed = source.replace(/The `api` session cut p95 latency by 40% on the notes endpoint\. /, "");
  assert.deepEqual(locateComment(removed, a, start), { state: "detached" });
});

test("Raw: a quote that occurs twice anchors to the selected occurrence, also after two lines are inserted above — the panel's follow moves the pair with its copy and the host places it there; a stale offset is refused, never guessed", async () => {
  // The acceptance criterion (plans/file-review.md, Commenting from either view) as the system meets it: the HOST
  // places every passage comment (the host paragraph), so the criterion is pinned against the real host module's
  // locateExact, driven the way the comment verb drives it (`exact`), and against the panel's followPassage, the
  // one thing that moves the composer's offset; the engine's own nearest-wins from the pre-edit offset is
  // production's path nowhere, and the pin until 2026-09-07 asserted only that.
  const source = fs.readFileSync(FIX("handlers-crlf.py"), "utf8");
  const needle = 'return respond(404, "missing")';
  const first = source.indexOf(needle), second = source.indexOf(needle, first + 1);
  assert.ok(second > first, "the passage occurs twice");
  // identical 24-character contexts around both occurrences: only the hint can tell them apart
  const ctx = (i: number) => source.slice(i - 24, i) + "|" + source.slice(i + needle.length, i + needle.length + 24);
  assert.equal(ctx(first), ctx(second));
  const { code } = buildRaw(source, "handlers-crlf.py");
  const domIdx = rawDomIndexOf(source);
  const r = ok(mapRawSelection(sel(boundaries(code, domIdx(second) as number, isRow).text[0], boundaries(code, (domIdx(second + needle.length - 1) as number) + 1, isRow).text[0]), El(code), source));
  assert.equal(r.range.start, second);
  const anchor = makeAnchor(source, r.range);
  assert.deepEqual(locateComment(source, anchor, r.range.start), { state: "located", range: r.range });
  assert.deepEqual(locateComment(source, anchor), { state: "located", range: { start: first, end: first + needle.length } }, "without the hint the engine takes the earliest tie");
  // A save with no edit in between: Save sends the anchor and the pair's start (saveComposer), and the host settles the
  // tie by that hint because it sits on a tied copy in the text the host read — the selected one. No offset: refused.
  const host = (await import(pathToFileURL(HOST).href)) as HostModule;
  const span = (at: number) => ({ from: at, to: at + needle.length });
  assert.deepEqual(host.locateExact(source, anchor, r.range.start, { exact: true }), span(second));
  assert.deepEqual(host.locateExact(source, anchor, undefined, { exact: true }), { error: "anchor-ambiguous" }, "a tie the request cannot settle");
  // The session inserts two lines above the passage between the selection and the save. The pair the composer holds
  // indexes the text the selection was made over; two paths reach the host from here.
  const at = source.indexOf("def put_note");
  assert.ok(first < at && at < second, "the insertion lands between the copies");
  const inserted = "# reviewed\r\n# twice\r\n";
  const edited = source.slice(0, at) + inserted + source.slice(at);
  const moved = second + inserted.length;
  // (a) The panel saw the edit before the save — the poll or Reload repainted over the new text: retargetComposer follows
  // the pair with its copy, exactly, by the edit's common prefix and suffix rather than by the anchor, and Save builds
  // the anchor over the edited text at the followed range and sends its start. The host places it on the selected copy,
  // and the panel paints the saved comment there with its stored anchorAt as the hint.
  const { followPassage } = await import("./file-comments");
  const f = followPassage(source, r.range, edited);
  if (f.state !== "moved") assert.fail("the passage sits after the edit's span: followed exactly");
  assert.deepEqual(f.range, { start: moved, end: moved + needle.length });
  const followed = makeAnchor(edited, f.range);
  assert.deepEqual(host.locateExact(edited, followed, f.range.start, { exact: true }), span(moved));
  assert.equal(edited.slice(moved, moved + needle.length), needle);
  assert.deepEqual(locateComment(edited, followed, moved), { state: "located", range: f.range });
  // (b) The save fired before the panel saw the edit: the hint is the pre-edit offset, which sits on no copy now. The
  // engine's nearest-wins from it happens to pick the selected copy here (the insertion is shorter than the gap between
  // the copies), a coincidence the host does not take: the request refuses (`anchor-moved`, surfaced by the comment
  // verb as `anchor-ambiguous` naming the moved text), nothing is written, and the note stays in the composer to be
  // placed by a reselect. A stored position keeps nearest-wins: it indexes this very text.
  assert.deepEqual(locateComment(edited, anchor, r.range.start), { state: "located", range: f.range }, "the engine's guess, right by luck");
  assert.deepEqual(host.locateExact(edited, anchor, r.range.start, { exact: true }), { error: "anchor-moved" });
  assert.deepEqual(host.locateExact(edited, anchor, r.range.start), span(moved), "the same offset as a stored anchorAt: nearest wins");
  // the same stale request when the insertion sits above BOTH copies and is longer than half the gap between them: the
  // guess is the copy that was not selected, and the refusal is the same — the reason the host refuses rather than guesses
  const above = "# " + "reviewed ".repeat(9) + "\r\n";
  assert.ok(above.length > (second - first) / 2 && above.length < second - first);
  const shifted = above + source;
  assert.deepEqual(locateComment(shifted, anchor, r.range.start), { state: "located", range: { start: first + above.length, end: first + above.length + needle.length } }, "nearest-wins picks the other copy");
  assert.deepEqual(host.locateExact(shifted, anchor, r.range.start, { exact: true }), { error: "anchor-moved" });
  assert.deepEqual(followPassage(source, r.range, shifted), { state: "moved", range: { start: second + above.length, end: second + above.length + needle.length } }, "the panel's follow is exact whatever the length");
  // The comment verb itself (buildComment), driven with the browser's offset: the offset indexes the text the fetch
  // handed the viewer, which strips a leading UTF-8 BOM, while the host's text keeps it, so on a BOM-prefixed file the
  // host maps the offset past the BOM (browserHint) before the exact check — without that, a tie on a BOM file was
  // refused `anchor-moved` for the correct selection, and no reload cleared it (the review, 2026-09-08). Placed on the
  // selected copy either way; the stored position is the host's offset.
  const now = 1_700_000_000_000;
  const placed = host.buildComment(source, { note: "n", anchor, hintOffset: r.range.start }, now, []);
  if ("error" in placed) assert.fail(`the plain file places: ${placed.error}`);
  assert.equal(placed.comment.anchorAt, second, "no BOM: the browser's offset is the host's offset");
  assert.deepEqual(placed.range, span(second));
  const bom = "\uFEFF" + source;
  assert.deepEqual(host.locateExact(bom, anchor, r.range.start, { exact: true }), { error: "anchor-moved" }, "unmapped, the browser's offset sits one short of every copy");
  const placedBom = host.buildComment(bom, { note: "n", anchor, hintOffset: r.range.start }, now, []);
  if ("error" in placedBom) assert.fail(`the BOM file places: ${placedBom.error}`);
  assert.equal(placedBom.comment.anchorAt, second + 1, "BOM: placed on the selected copy, the offset mapped past the BOM");
  assert.deepEqual(placedBom.range, span(second + 1));
  assert.deepEqual(host.buildComment(bom, { note: "n", anchor }, now, []), { error: "anchor-ambiguous" }, "no offset passes through unmapped: still a tie the request cannot settle");
  // the verb and the panel, pinned to their sources: the comment verb is the exact caller, its hint the browser's offset
  // mapped into the host's text, and its anchor-moved is the anchor-ambiguous refusal that names the moved text; Save's
  // hint is the pair's start, which retargetComposer alone moves
  const hostSrc = fs.readFileSync(HOST, "utf8");
  assert.ok(hostSrc.includes("const loc = locateExact(text, anchor, browserHint(text, args.hintOffset), { exact: true });"), "buildComment places with exact, the hint mapped past a BOM");
  assert.ok(/if \(built\.error === 'anchor-moved'\) \{\s*\n\s*throw new Refusal\('anchor-ambiguous', `\$\{what\} occurs more than once in \$\{ctx\.shown\}[^`]*\$\{moved\} no longer says which copy was meant — \$\{again\}`\);/.test(hostSrc), "the refusal names the moved text, in the words of the gesture");
  assert.ok(hostSrc.includes(`"the text moved after it was selected, so the selection's position"`) && hostSrc.includes(`'reload and select it again'`), "a passage: selected, so select it again");
  const panel = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-comments.ts"), "utf8");
  assert.ok(panel.includes("if (c.range && src !== null) { args.anchor = makeAnchor(src, c.range); args.hintOffset = c.range.start; }"), "saveComposer sends the pair's start");
  assert.ok(/const f = followPassage\(c\.text, c\.range, src\);\s*\n\s*if \(f\.state === "moved"\) \{ c\.range = f\.range; c\.text = src; c\.tied = false; \}/.test(panel), "retargetComposer moves the pair with its copy");
});

test("rawOffsetToLine counts the Raw view's rows", () => {
  const src = "a\r\nb\r\n\r\nc";
  assert.equal(rawOffsetToLine(src, 0), 0);
  assert.equal(rawOffsetToLine(src, 3), 1);
  assert.equal(rawOffsetToLine(src, 7), 2, "the LF that ends line 3 still lies on it");
  assert.equal(rawOffsetToLine(src, 8), 3);
  assert.equal(rawOffsetToLine(src, 99), 3);
  assert.equal(rawOffsetToLine("x\ry", 2), 1, "a lone CR ends its row since Slice 7, as the viewer's split has it (before: 0, the CR inside its row)");
});

// ── Raw: the rows split on CR, CRLF and LF (Slice 7 of plans/markdown-viewer.md, item 7) ───────────────────────
/** The row split the viewer takes since Slice 7 (contract C6; the replica `wrapNumberedHtml` above follows it): a CRLF as one
 *  ending, then a lone CR, then LF, the one trailing empty piece popped. */
const ROW_SPLIT = /\r\n|\r|\n/;
/** `code.hljs` holding `text`'s rows on that split, through the replica (no highlighter: the endings are what these cases read). */
function buildRawSplit(text: string): FakeElement {
  const doc = new FakeDocument();
  const code = doc.createElement("code"); code.setAttribute("class", "hljs");
  for (const n of parseHTML(doc, wrapNumberedHtml(escapeHtml(text)))) code.appendChild(n);
  return code;
}
/** The row that holds `offset` by the split alone: the endings whose last character lies before the offset. */
const rowBySplit = (text: string, offset: number): number => {
  let row = 0;
  for (const m of text.matchAll(/\r\n|\r|\n/g)) if ((m.index as number) + m[0].length <= offset) row++; else break;
  return row;
};

test("Raw over a CR-only and a CRLF source: rows laid on the three-ending split verify against the file and give its offsets (rawRows, a selection, rawRowForOffset), and rawOffsetToLine answers the row the split gives for every offset, agreeing with rawRowForOffset row for row (before Slice 7: an LF-only count, every offset of a CR-only file on row 0); zero rows over an empty source are accepted", () => {
  for (const [what, text] of [["CR-only", "alpha\rbeta\rgamma\r"], ["CRLF", "alpha\r\nbeta\r\ngamma\r\n"], ["mixed", "alpha\rbeta\r\ngamma\ndelta"], ["blank rows", "a\r\r\nb\n\rc"]] as Array<[string, string]>) {
    const code = buildRawSplit(text);
    const rows = rawRows(El(code), text) as unknown as FakeElement[] | null;
    assert.ok(rows, what + ": the rows verify against the source");
    const expected = text.split(ROW_SPLIT); if (expected[expected.length - 1] === "") expected.pop();
    assert.deepEqual(rows!.map((r) => r.textContent), expected, what + ": one row per line, no row carrying an ending");
    assert.ok(rows!.every((r) => !/[\r\n]/.test(r.textContent)), what + ": no CR or LF in a row's text");
    for (let n = 0; n <= text.length; n++) {
      const byMap = rawRowForOffset(El(code), text, n) as unknown as FakeElement | null;
      const line = rawOffsetToLine(text, n);
      assert.equal(line, rowBySplit(text, n), what + ": rawOffsetToLine at " + n + " is the split's row (unclamped: at the end of a text closed by an ending it counts one past the last row, and the callers clamp, as landOn does)");
      assert.equal(byMap, rows![Math.min(line, rows!.length - 1)], what + ": rawRowForOffset and rawOffsetToLine agree at offset " + n);
    }
    assert.equal(rawOffsetToLine(text, text.length + 5), rows!.length - 1 + (text.endsWith("\r") || text.endsWith("\n") ? 1 : 0), what + ": past the end, one past the last row when the text ends in an ending (the caller clamps)");
    // a selection from the first row's start to the end of the second row that holds text maps to the file's offsets, the file's
    // own endings inside the quote (a blank row has no text node, so the second text node may sit a row further down)
    const t = allText(code, isRow);
    const rowOf = (n: FakeNode): FakeElement => { let e = n; while (!(e.nodeType === 1 && isRow(e as FakeElement))) e = e.parentNode as FakeNode; return e as FakeElement; };
    const end = rawRowSpan(El(code), text, El(rowOf(t[1])))!.end;
    const r = ok(mapRawSelection(sel({ node: t[0], offset: 0 }, { node: t[1], offset: t[1].data.length }), El(code), text), what + ": a selection across the first ending");
    assert.equal(r.quote, text.slice(0, end), what + ": the quote keeps the file's endings");
    assert.deepEqual(r.range, { start: 0, end });
  }
  // item 6's control: an empty file paints no rows, and zero rows over "" are the rows of that file, not a mismatch
  const empty = buildRawSplit("");
  assert.equal(empty.childNodes.length, 0, "no row for an empty file");
  assert.deepEqual(rawRows(El(empty), ""), [], "zero rows over an empty source: accepted, no error");
  assert.equal(rawRowForOffset(El(empty), "", 0), null, "no row to land on");
  assert.equal(rawOffsetToLine("", 0), 0);
});

// ── Rendered: the aligned fixture ──────────────────────────────────────────────────────────────────
type NonWsPos = { t: FakeText; off: number; ch: string };
const nonWsPositions = (root: FakeNode): NonWsPos[] => {
  const out: NonWsPos[] = [];
  for (const t of allText(root, null)) for (let i = 0; i < t.data.length; i++) if (!/\s/.test(t.data[i])) out.push({ t, off: i, ch: t.data[i] });
  return out;
};

test("Rendered: every selection inside aligned blocks yields a quote whose mapped characters are the selected ones, and painting re-wraps exactly them", () => {
  const source = fixture("report.md");
  const { box } = buildRendered(source);
  const blocks = box.childNodes.filter((n) => n.nodeType === 1) as FakeElement[];
  assert.ok(blocks.length >= 12, "blocks: " + blocks.length);
  // the fixture holds every construct the acceptance names
  for (const re of [/^# /m, /^-{5,}$/m, /^### .* ###$/m, /^- \*\*/m, /^  - /m, /^\d\. /m, /^- \[x\] /m, /^- \[ \] /m, /^> /m, /~~legacy~~/, /`GET/, /\]\(https/, /\]\[runbook\]/, /\[collapsed\]\[\]/, /\[shortcut\] link/, /<https:/, /bare https:/, /!\[Latency/, /\\\*not/, /spaces  \n/, /break\\\n/, /^\[runbook\]: /m]) {
    assert.match(source, re);
  }
  let selections = 0, painted = 0;
  const fullRendered = stripWs(domText(box, null));
  for (let bi = 0; bi < blocks.length; bi++) {
    const b = blocks[bi];
    const pos = nonWsPositions(b);
    if (!pos.length) continue;   // <hr> has no text
    // every start inside this block, a spread of ends within it and into the following blocks
    for (let i = 0; i < pos.length; i++) {
      const ends: { bj: number; k: number }[] = [];
      for (const d of [1, 2, 4, 9, 20, 55]) if (i + d <= pos.length) ends.push({ bj: bi, k: i + d });
      ends.push({ bj: bi, k: pos.length });
      if (i % 5 === 0) for (const nb of [bi + 1, bi + 2, bi + 4]) if (nb < blocks.length && nonWsPositions(blocks[nb]).length) ends.push({ bj: nb, k: Math.min(3, nonWsPositions(blocks[nb]).length) });
      for (const e of ends) {
        const endPos = nonWsPositions(blocks[e.bj])[e.k - 1];
        const a = { node: pos[i].t, offset: pos[i].off };
        const f = { node: endPos.t, offset: endPos.off + 1 };
        const r = ok(mapRenderedSelection(sel(a, f), El(box), source), `block ${bi} char ${i} → block ${e.bj} char ${e.k}`);
        // the selected rendered characters, whitespace aside
        const selectedNonWs = (() => {
          const all = allText(box, null);
          const startG = all.slice(0, all.indexOf(pos[i].t)).reduce((s, t) => s + t.data.length, 0) + pos[i].off;
          const endG = all.slice(0, all.indexOf(endPos.t)).reduce((s, t) => s + t.data.length, 0) + endPos.off + 1;
          return stripWs(domText(box, null).slice(startG, endG));
        })();
        assert.equal(r.quote, source.slice(r.range.start, r.range.end));
        assert.equal(r.quote[0], selectedNonWs[0], "the quote starts at the first selected character");
        assert.equal(r.quote[r.quote.length - 1], selectedNonWs[selectedNonWs.length - 1], "and ends at the last");
        assert.ok(isSubsequence(selectedNonWs, stripWs(r.quote)), `selected text is inside the quote: ${JSON.stringify(selectedNonWs)} vs ${JSON.stringify(r.quote)}`);
        // backward selection: the same answer
        assert.deepEqual(mapRenderedSelection(sel(f, a), El(box), source), r);
        selections++;
        // the engine locates the stored anchor at the range, and painting it after a reload wraps exactly the selection
        if (selections % 9 === 0) {
          const anchor = makeAnchor(source, r.range);
          const loc = locateComment(source, anchor, r.range.start);
          assert.deepEqual(loc, { state: "located", range: r.range });
          const fresh = buildRendered(source);
          const marks = paintRendered(El(fresh.box), source, loc.range!, "fc-hl", { cid: "c1" }) as unknown as FakeElement[] | null;
          assert.ok(marks && marks.length, "painted");
          const paintedText = stripWs(marks!.map((m) => m.textContent).join(""));
          assert.equal(paintedText, selectedNonWs, `paint [${r.range.start},${r.range.end}) = ${JSON.stringify(r.quote)}`);
          assert.equal(stripWs(domText(fresh.box, null)), fullRendered, "painting keeps the rendered text");
          for (const m of marks!) { assert.equal(m.getAttribute("class"), "fc-hl"); assert.equal(m.getAttribute("data-cid"), "c1"); }
          painted++;
        }
      }
    }
  }
  assert.ok(selections > 1500, "selections " + selections);
  assert.ok(painted > 150, "painted " + painted);
});

test("Rendered: the marks the renderer consumes are dropped, so a whole-element selection quotes just the text", () => {
  const source = fixture("report.md");
  const { box } = buildRendered(source);
  const el = (tag: string, n = 0) => {
    const found: FakeElement[] = [];
    const visit = (x: FakeNode) => { if (x.nodeType === 1 && (x as FakeElement).tagName === tag) found.push(x as FakeElement); x.childNodes.forEach(visit); };
    visit(box); return found[n];
  };
  const whole = (e: FakeElement) => { const p = nonWsPositions(e); return sel({ node: p[0].t, offset: p[0].off }, { node: p[p.length - 1].t, offset: p[p.length - 1].off + 1 }); };
  assert.equal(ok(mapRenderedSelection(whole(el("H1")), El(box), source)).quote, "Latency report");
  assert.equal(ok(mapRenderedSelection(whole(el("H2")), El(box), source)).quote, "Second heading");
  assert.equal(ok(mapRenderedSelection(whole(el("H3")), El(box), source)).quote, "Summary");
  assert.equal(ok(mapRenderedSelection(whole(el("STRONG", 0)), El(box), source)).quote, "Cache");
  assert.equal(ok(mapRenderedSelection(whole(el("EM")), El(box), source)).quote, "five");
  assert.equal(ok(mapRenderedSelection(whole(el("DEL")), El(box), source)).quote, "legacy");
  assert.equal(ok(mapRenderedSelection(whole(el("CODE", 1)), El(box), source)).quote, "GET /notes/{id}");
  assert.equal(ok(mapRenderedSelection(whole(el("A", 0)), El(box), source)).quote, "pull request");
  assert.equal(ok(mapRenderedSelection(whole(el("A", 1)), El(box), source)).quote, "runbook");
  assert.equal(ok(mapRenderedSelection(whole(el("A", 2)), El(box), source)).quote, "shortcut");
  assert.equal(ok(mapRenderedSelection(whole(el("A", 3)), El(box), source)).quote, "collapsed");
  assert.equal(ok(mapRenderedSelection(whole(el("A", 4)), El(box), source)).quote, "https://example.com/notes-api");
  assert.equal(ok(mapRenderedSelection(whole(el("A", 5)), El(box), source)).quote, "https://example.com/status");
  assert.equal(ok(mapRenderedSelection(whole(el("BLOCKQUOTE")), El(box), source)).quote, "The web session asked for **one** more week.\n> Quoted second line.");
  // a task item: the checkbox is not text; the quote is the item's words
  const li = el("LI", 7);
  assert.ok(li.childNodes.some((c) => c.nodeType === 1 && (c as FakeElement).tagName === "INPUT"), "task item has its checkbox");
  assert.equal(ok(mapRenderedSelection(whole(li), El(box), source)).quote, "Ship the cache");
  // an escape: the rendered "*" maps to the source "*", not the backslash
  const esc = (() => { const found: FakeElement[] = []; const visit = (x: FakeNode) => { if (x.nodeType === 1 && (x as FakeElement).tagName === "P" && x.textContent.startsWith("Escapes:")) found.push(x as FakeElement); x.childNodes.forEach(visit); }; visit(box); return found[0]; })();
  const p = nonWsPositions(esc);
  const star = p.findIndex((x) => x.ch === "*");
  const r = ok(mapRenderedSelection(sel({ node: p[star].t, offset: p[star].off }, { node: p[star + 3].t, offset: p[star + 3].off + 1 }), El(box), source));
  assert.equal(r.quote, "*not");
});

test("Rendered: a selection spanning two aligned blocks keeps the blank line and block markers between them; whitespace between blocks snaps", () => {
  const source = fixture("report.md");
  const { box } = buildRendered(source);
  const h1 = box.childNodes.find((n) => n.nodeType === 1 && (n as FakeElement).tagName === "H1") as FakeElement;
  const p1 = box.childNodes.find((n) => n.nodeType === 1 && (n as FakeElement).tagName === "P") as FakeElement;
  const hp = nonWsPositions(h1), pp = nonWsPositions(p1);
  // rendered non-whitespace positions: the backticks around "api" are not in the DOM, so pp[5] is the "i"
  const r = ok(mapRenderedSelection(sel({ node: hp[7].t, offset: hp[7].off }, { node: pp[5].t, offset: pp[5].off + 1 }), El(box), source));
  assert.equal(r.quote, "report\n\nThe `api");
  // a start in the "\n" text node between the heading and the paragraph snaps to the paragraph's first character
  const gap = box.childNodes[box.childNodes.indexOf(h1) + 1];
  assert.equal(gap.nodeType, 3);
  const r2 = ok(mapRenderedSelection(sel({ node: gap, offset: 0 }, { node: pp[5].t, offset: pp[5].off + 1 }), El(box), source));
  assert.equal(r2.quote, "The `api");
  // an end in that gap snaps back to the heading's last character
  const r3 = ok(mapRenderedSelection(sel({ node: hp[0].t, offset: hp[0].off }, { node: gap, offset: 1 }), El(box), source));
  assert.equal(r3.quote, "Latency report");
  // the root itself as a boundary: (box, 0) … (box, 1) is the heading
  assert.equal(ok(mapRenderedSelection(sel({ node: box, offset: 0 }, { node: box, offset: 1 }), El(box), source)).quote, "Latency report");
  // the selection's edge outside the rendered root: an ancestor snaps, a sibling refuses
  const body = box.parentNode as FakeElement;
  assert.equal(ok(mapRenderedSelection(sel({ node: body, offset: 0 }, { node: hp[6].t, offset: hp[6].off + 1 }), El(box), source)).quote, "Latency");
  const last = ok(mapRenderedSelection(sel({ node: pp[0].t, offset: pp[0].off }, { node: body, offset: 2 }), El(box), source));
  assert.ok(last.quote.startsWith("The `api") && last.quote.endsWith("Done."), "snaps to the end of the last block: " + JSON.stringify(last.quote.slice(-20)));
  bad(mapRenderedSelection(sel({ node: body.childNodes[0].childNodes[0], offset: 0 }, { node: hp[6].t, offset: hp[6].off + 1 }), El(box), source));
  // whitespace only
  const w = bad(mapRenderedSelection(sel({ node: gap, offset: 0 }, { node: gap, offset: 1 }), El(box), source));
  assert.match(w.reason, /whitespace|Select/);
});

// ── Rendered: refusals ─────────────────────────────────────────────────────────────────────────────
test("Rendered refusals over the refusals fixture: the HTML block, entity prose, the escaped link label and the tab after a list marker each refuse with the note-preserving fields; the fenced code, the indented block, the table cell and the quote's tab-opened code map since Slice 8 (before: refused as a code block, an indented code block, a table)", () => {
  const source = fixture("refusals.md");
  const { box } = buildRendered(source);
  const els = box.childNodes.filter((n) => n.nodeType === 1) as FakeElement[];
  const byTag = (tag: string, n = 0) => els.filter((e) => e.tagName === tag)[n];
  const inside = (e: FakeElement, from: number, to: number) => { const p = nonWsPositions(e); return sel({ node: p[from].t, offset: p[from].off }, { node: p[to - 1].t, offset: p[to - 1].off + 1 }); };
  const lineOf = (needle: string) => source.slice(0, source.indexOf(needle)).split("\n").length - 1;
  // fenced code MAPS since Slice 8 of plans/markdown-viewer.md (before: refused as a code block with the Raw offer, the line found by
  // indexOf): the line's own offsets, and the `return` after the tab the renderer showed as four spaces
  const pre = byTag("PRE", 0);
  const line = ok(mapRenderedSelection(inside(pre, 0, 20), El(box), source), "a code line maps (before: refused as a code block)");   // "def handler(request):" has 20 non-whitespace characters
  assert.equal(line.quote, "def handler(request):");
  assert.deepEqual(line.range, { start: source.indexOf("def handler"), end: source.indexOf("def handler") + "def handler(request):".length }, "the line's own offsets");
  const ret = ok(mapRenderedSelection(inside(pre, 20, 26), El(box), source), "the word after the tab");          // "return", after the tab
  assert.equal(ret.quote, "return");
  assert.equal(ret.range.start, source.indexOf("\treturn") + 1, "the tab is not selected text; the word's own offset");
  // indented code maps too (before: refused as an indented code block)
  const ind = ok(mapRenderedSelection(inside(byTag("PRE", 1), 0, 3), El(box), source), "an indented block's line");
  assert.equal(ind.quote, "ind");
  assert.equal(ind.range.start, source.indexOf("indented code line"));
  let r: ReturnType<typeof bad>;
  // a table cell MAPS since Slice 8 of plans/markdown-viewer.md (before: refused as a table with the Raw offer, the cell text found
  // by indexOf); the first two characters of the header's first cell are its own two source characters
  const cell = ok(mapRenderedSelection(inside(byTag("TABLE"), 0, 2), El(box), source), "a table cell maps (before: refused as a table)");
  assert.equal(cell.quote, "Ro");
  assert.deepEqual(cell.range, { start: source.indexOf("Route"), end: source.indexOf("Route") + 2 }, "the cell's own offsets");
  // HTML block
  r = bad(mapRenderedSelection(inside(byTag("DIV"), 0, 3), El(box), source));
  assert.match(r.reason, /HTML block/);
  assert.equal(r.blockStartLine, lineOf("<div class"));
  assert.equal(r.rawHasQuote, true);
  // entity prose: the rendered "&" is five source characters, so the selection is refused and the Raw offer has no exact passage
  const ps = els.filter((e) => e.tagName === "P");
  const entity = ps.find((p) => p.textContent.includes("Fast & simple"))!;
  r = bad(mapRenderedSelection(inside(entity, 0, 11), El(box), source));   // "Fast & simple": the "&" is "&amp;" in the source
  assert.match(r.reason, /entity/);
  assert.equal(r.blockStartLine, lineOf("Fast &amp;"));
  assert.equal(r.rawHasQuote, false);
  r = bad(mapRenderedSelection(inside(entity, 0, 4), El(box), source));    // "Fast" alone does occur, so the Raw offer can preselect it
  assert.match(r.reason, /entity/);
  assert.equal(r.rawHasQuote, true);
  assert.equal(source.slice(r.rawRange!.start, r.rawRange!.end), "Fast");
  // escaped bracket in a link label
  const label = ps.find((p) => p.textContent.includes("label with"))!;
  r = bad(mapRenderedSelection(inside(label, 0, 6), El(box), source));
  assert.match(r.reason, /escaped bracket/);
  assert.equal(r.blockStartLine, lineOf("A [label"));
  // list line beginning with a tab after the marker
  r = bad(mapRenderedSelection(inside(byTag("UL"), 0, 4), El(box), source));
  assert.match(r.reason, /tab after its marker|could not place/);
  assert.equal(r.blockStartLine, lineOf("- Item one"));
  // blockquote line beginning with a tab after the marker: the lexer turned it into an indented code block inside the quote, whose
  // line maps since Slice 8 (before: refused as an indented code block at the quote's line)
  const quoted = ok(mapRenderedSelection(inside(byTag("BLOCKQUOTE"), 0, 4), El(box), source), "the quote's tab-opened code line");
  assert.equal(quoted.quote, "quot");
  assert.equal(quoted.range.start, source.indexOf("quoted after a tab"));
  // the aligned paragraphs around them still map, before and after every refused block (alignment resynced)
  const before = ps.find((p) => p.textContent.startsWith("An aligned paragraph before"))!;
  assert.equal(ok(mapRenderedSelection(inside(before, 0, 9), El(box), source)).quote, "An aligned");
  const after = ps.find((p) => p.textContent.startsWith("An aligned paragraph after"))!;
  assert.equal(ok(mapRenderedSelection(inside(after, 2, 9), El(box), source)).quote, "aligned");
  assert.equal(ok(mapRenderedSelection(inside(after, 0, 34), El(box), source)).quote, "An aligned paragraph after everything.");
  // a selection reaching from an aligned paragraph into the fence's first line maps since Slice 8, the opener line inside the quote
  // as a Raw selection over the same characters mints (before: refused as a code block with no Raw passage); one reaching from
  // the table's last cell into a refused block (the HTML block) still refuses with that block's line
  const bp = nonWsPositions(before), cp = nonWsPositions(pre);
  const intoCode = ok(mapRenderedSelection(sel({ node: bp[0].t, offset: bp[0].off }, { node: cp[3].t, offset: cp[3].off + 1 }), El(box), source), "prose into the fence");
  assert.equal(intoCode.quote, "An aligned paragraph before the code.\n\n```python\ndef h");
  const tp = nonWsPositions(byTag("TABLE")), dp = nonWsPositions(byTag("DIV"));
  r = bad(mapRenderedSelection(sel({ node: tp[17].t, offset: tp[17].off }, { node: dp[2].t, offset: dp[2].off + 1 }), El(box), source));   // "120 ms" starts at the table's 17th non-whitespace character
  assert.match(r.reason, /HTML block/);
  assert.equal(r.blockStartLine, lineOf("<div class"));
  assert.equal(r.rawHasQuote, false, "text spanning the two blocks is not one source passage");
});

test("Rendered: a document whose rendering no longer matches the source refuses every block", () => {
  const rendered = "# Title\n\nOld paragraph text.\n";
  const { box } = buildRendered(rendered);
  const current = "# Title\n\nNew paragraph text.\n";
  const p = box.childNodes.filter((n) => n.nodeType === 1)[1] as FakeElement;
  const pp = nonWsPositions(p);
  const r = bad(mapRenderedSelection(sel({ node: pp[0].t, offset: pp[0].off }, { node: pp[3].t, offset: pp[3].off + 1 }), El(box), current));
  assert.match(r.reason, /does not match/);
  assert.equal(r.blockStartLine, 2);
  // the heading still matches and maps
  const h = box.childNodes[0] as FakeElement; const hp = nonWsPositions(h);
  assert.equal(ok(mapRenderedSelection(sel({ node: hp[0].t, offset: hp[0].off }, { node: hp[4].t, offset: hp[4].off + 1 }), El(box), current)).quote, "Title");
});

test("Rendered: CRLF markdown maps back to original offsets, and a quote across a soft break keeps the CRLF", () => {
  const source = "# Title\r\n\r\nFirst line\r\nsecond line of the same paragraph.\r\n\r\n- item **one**\r\n";
  const { box } = buildRendered(source);
  const p = box.childNodes.filter((n) => n.nodeType === 1)[1] as FakeElement;
  const pp = nonWsPositions(p);
  const r = ok(mapRenderedSelection(sel({ node: pp[5].t, offset: pp[5].off }, { node: pp[14].t, offset: pp[14].off + 1 }), El(box), source));
  assert.equal(r.quote, "line\r\nsecond");
  assert.equal(source.slice(r.range.start, r.range.end), r.quote);
  const li = box.childNodes.filter((n) => n.nodeType === 1)[2] as FakeElement;
  const lp = nonWsPositions(li);
  assert.equal(ok(mapRenderedSelection(sel({ node: lp[0].t, offset: lp[0].off }, { node: lp[6].t, offset: lp[6].off + 1 }), El(box), source)).quote, "item **one");
});

// ── Rendered: painting ─────────────────────────────────────────────────────────────────────────────
test("Rendered paint: a range inside a refused block falls back to a whitespace-tolerant match; an absent passage is unpaintable", () => {
  const source = fixture("refusals.md");
  const { box } = buildRendered(source);
  // a comment the CLI anchored inside the fenced code
  const q = "return respond(request)";
  const start = source.indexOf(q);
  const marks = paintRendered(El(box), source, { start, end: start + q.length }, "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(marks && marks.length);
  assert.equal(stripWs(marks!.map((m) => m.textContent).join("")), stripWs(q));
  let p: FakeNode | null = marks![0]; let inPre = false;
  while (p) { if (p.nodeType === 1 && (p as FakeElement).tagName === "PRE") inPre = true; p = p.parentNode; }
  assert.ok(inPre, "painted inside the code block's element");
  // a quote carrying inline markup inside a table cell is matched with the markup stripped
  const cell = "GET /notes";
  const cs = source.indexOf(cell);
  const cm = paintRendered(El(box), source, { start: cs, end: cs + cell.length }, "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(cm && stripWs(cm.map((m) => m.textContent).join("")) === "GET/notes");
  // a passage whose text the DOM does not hold: null, never a wrong highlight
  const fresh = buildRendered(source);
  assert.equal(paintRendered(El(fresh.box), "Something entirely different.\n", { start: 0, end: 9 }, "fc-hl"), null);
  // an aligned range paints through the index map and skips the whitespace between blocks
  const two = buildRendered(source);
  const s2 = source.indexOf("everything."), e2 = s2 + "everything.".length;
  const m2 = paintRendered(El(two.box), source, { start: s2, end: e2 }, "fc-hl", { cid: "x" }) as unknown as FakeElement[];
  assert.equal(m2.length, 1);
  assert.equal(m2[0].textContent, "everything.");
  assert.equal((m2[0].parentNode as FakeElement).tagName, "P");
});

test("Rendered paint: a range over several blocks wraps each block's text and no inter-block whitespace", () => {
  const source = fixture("report.md");
  const { box } = buildRendered(source);
  const start = source.indexOf("Key points"), end = source.indexOf("minutes.") + "minutes.".length;
  const marks = paintRendered(El(box), source, { start, end }, "fc-hl") as unknown as FakeElement[];
  assert.ok(marks.length >= 3);
  for (const m of marks) assert.notEqual(stripWs(m.textContent), "", "no whitespace-only marks between blocks: " + JSON.stringify(m.textContent));
  assert.equal(stripWs(marks.map((m) => m.textContent).join("")), stripWs("Key points: Cache the rendered notes for five minutes."));
});

test("Rendered paint: a run of adjacent whitespace-only text nodes between blocks (the two the sanitizer leaves where a block-level comment stood) is never wrapped: no mark at the top level, the two nodes as rendered", () => {
  // marked emits a block-level HTML comment between two blocks as `</blockquote>\n<!-- ... -->\n\n<p>`, and DOMPurify removes
  // the comment node and leaves the "\n" and the "\n\n" as two ADJACENT text nodes under .fileview-md (the parser here does
  // the same; a <style> between two blocks leaves the same pair). wrapRuns skipped a whitespace-only run only when it was ONE
  // node, so a comment across the two blocks wrapped the pair in a mark of its own: a ringed box on a line between the
  // blocks, 4 x 18 px in Chromium, and everything below moved down by its height, back on every fresh Rendered paint (the
  // Slice 4 review, round 7). Main's wrapSlices skipped every such node on its own.
  const source = "> A quoted line before a block comment.\n\n<!-- a block comment between two blocks -->\n\nParagraph after the block comment with words.\n";
  const { box } = buildRendered(source);
  const kids = box.childNodes.slice();
  const tag = (n: FakeNode) => n.nodeType === 3 ? JSON.stringify((n as FakeText).data) : (n as FakeElement).tagName;
  const isWsText = (n: FakeNode) => n.nodeType === 3 && stripWs((n as FakeText).data) === "";
  assert.ok(kids.some((n, i) => i > 0 && isWsText(n) && isWsText(kids[i - 1])), "the fixture holds two adjacent whitespace-only text nodes at the top level: " + kids.map(tag).join(" | "));
  const start = source.indexOf("A quoted"), end = source.indexOf("with words.") + "with words.".length;
  const marks = paintRendered(El(box), source, { start, end }, "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(marks && marks.length >= 2, "both blocks' text painted: " + JSON.stringify(marks && marks.map((m) => m.textContent)));
  for (const m of marks) assert.notEqual(stripWs(m.textContent), "", "no whitespace-only mark: " + JSON.stringify(m.textContent));
  for (const m of marks) assert.notEqual(m.parentNode, box, "no mark stands at the top level: " + JSON.stringify(m.textContent));
  assert.ok(box.childNodes.length === kids.length && kids.every((n, i) => box.childNodes[i] === n), "the top-level children are as rendered, the two whitespace nodes among them: " + box.childNodes.map(tag).join(" | "));
  assert.equal(stripWs(marks.map((m) => m.textContent).join("")), stripWs("A quoted line before a block comment. Paragraph after the block comment with words."));
});

test("Rendered paint reads the top-level blocks a range touches and no other: a mark costs its own blocks, not the document", () => {
  // The Comments panel re-paints every mark on every paint pass, so a walk of the whole rendered root per mark
  // (textNodes(root) in wrapBetween) cost marks x nodes: 466 marks over a 24k-node document were 1.1 s of a 1.4 s
  // frame on every width change (2026-09-09). The bound: childNodes is read only under the blocks the range overlaps.
  const source = fixture("report.md");
  const { box } = buildRendered(source);
  const blocks = box.childNodes.filter((n) => n.nodeType === 1) as FakeElement[];
  assert.ok(blocks.length >= 8, "a document of several blocks: " + blocks.length);
  // the index is built once per root and source (it walks everything then); the first paint pays it
  const warm = source.indexOf("Key points");
  assert.ok((paintRendered(El(box), source, { start: warm, end: warm + 3 }, "fc-hl") || []).length >= 1);
  const reads = new Map<FakeElement, number>();
  for (const b of blocks) {
    const kids = b.childNodes;
    Object.defineProperty(b, "childNodes", { configurable: true, get() { reads.set(b, (reads.get(b) || 0) + 1); return kids; } });
  }
  const holder = (n: FakeNode): FakeElement => { let c: FakeNode = n; while (c.parentNode && c.parentNode !== box) c = c.parentNode; return c as FakeElement; };
  // one block
  const q = "Second ordered item, loose.";
  const s1 = source.indexOf(q);
  assert.ok(s1 > 0);
  const one = paintRendered(El(box), source, { start: s1, end: s1 + q.length }, "fc-hl") as unknown as FakeElement[];
  assert.equal(one.map((m) => m.textContent).join(""), q);
  const oneTouched = blocks.filter((b) => reads.has(b));
  sameNodes(oneTouched, [holder(one[0])], "only the block holding the passage was read; read: " + oneTouched.length + " of " + blocks.length + ", blocks " + oneTouched.map((b) => blocks.indexOf(b)).join(",") + " where " + blocks.indexOf(holder(one[0])!) + " was expected");   // by identity (ui/test-dom-shim.ts sameNodes)
  // several blocks: the run from the first mark's block to the last mark's block, none before or after
  reads.clear();
  const start = source.indexOf("Key points"), end = source.indexOf("minutes.") + "minutes.".length;
  const many = paintRendered(El(box), source, { start, end }, "fc-hl") as unknown as FakeElement[];
  assert.ok(many.length >= 3);
  const i0 = blocks.indexOf(holder(many[0])), i1 = blocks.indexOf(holder(many[many.length - 1]));
  assert.ok(i0 >= 0 && i1 > i0, "the range spans blocks");
  const run = blocks.slice(i0, i1 + 1);
  assert.ok(run.length < blocks.length, "blocks outside the range exist");
  const manyTouched = blocks.filter((b) => reads.has(b));
  sameNodes(manyTouched, run, "the blocks between the two ends were read and no other; read: " + manyTouched.length + " of " + blocks.length + ", blocks " + manyTouched.map((b) => blocks.indexOf(b)).join(",") + " where " + i0 + ".." + i1 + " were expected");
});

// ── Rendered: holes, html resync, inline html, autolinks, cache validity ───────────────────────────
const firstEl = (root: FakeNode, tag: string, n = 0): FakeElement => {
  const found: FakeElement[] = [];
  const visit = (x: FakeNode) => { if (x.nodeType === 1 && (x as FakeElement).tagName === tag) found.push(x as FakeElement); x.childNodes.forEach(visit); };
  visit(root); return found[n];
};
const wholeOf = (e: FakeElement) => { const p = nonWsPositions(e); return sel({ node: p[0].t, offset: p[0].off }, { node: p[p.length - 1].t, offset: p[p.length - 1].off + 1 }); };
const partOf = (e: FakeElement, from: number, to: number) => { const p = nonWsPositions(e); return sel({ node: p[from].t, offset: p[from].off }, { node: p[to - 1].t, offset: p[to - 1].off + 1 }); };

test("Rendered: a code block nested in a list item maps line by line since Slice 8 (before: a hole refusing with its own line), the other items map as before, a selection from the item's prose into the code and one across the items carry the fence inside the quote; a table nested in a list item maps cell by cell (before: a hole refusing with the table's line)", () => {
  const source = [
    "- Install it:", "", "  ```sh", "  npm install notes-api", "  ```", "", "- Then run the server.", "", "- A table:", "",
    "  | a | b |", "  |---|---|", "  | 1 | 2 |", "", "- After the table.", "",
  ].join("\n");
  const { box } = buildRendered(source);
  const ul = firstEl(box, "UL");
  assert.equal(ok(mapRenderedSelection(wholeOf(firstEl(ul, "LI", 1)), El(box), source)).quote, "Then run the server.");
  assert.equal(ok(mapRenderedSelection(wholeOf(firstEl(ul, "LI", 3)), El(box), source)).quote, "After the table.");
  assert.equal(ok(mapRenderedSelection(partOf(firstEl(ul, "LI", 0), 0, 7), El(box), source)).quote, "Install");
  const npm = ok(mapRenderedSelection(partOf(firstEl(ul, "PRE"), 0, 3), El(box), source), "the nested fence's line (before: refused as a code block at line 2, `npm` the Raw offer)");
  assert.equal(npm.quote, "npm");
  assert.equal(npm.range.start, source.indexOf("npm install"), "the line's own offset inside the item");
  // the nested table's header cell maps to its own offset (Slice 8; before: refused as a table at line 10)
  const cell = ok(mapRenderedSelection(partOf(firstEl(ul, "TABLE"), 0, 1), El(box), source), "a nested table's cell maps");
  assert.equal(cell.quote, "a");
  assert.equal(cell.range.start, source.indexOf("| a |") + 2);
  // a selection from the prose item into the code maps, the fence's opener inside the quote (before: touched the hole)
  const li0 = nonWsPositions(firstEl(ul, "LI", 0)), pre = nonWsPositions(firstEl(ul, "PRE"));
  const into = ok(mapRenderedSelection(sel({ node: li0[0].t, offset: li0[0].off }, { node: pre[2].t, offset: pre[2].off + 1 }), El(box), source), "the item's prose into its code");
  assert.equal(into.quote, "Install it:\n\n  ```sh\n  npm");
  // a selection across the two prose items carries the whole fence between them (before: refused, the hole inside the selection)
  const li1 = nonWsPositions(firstEl(ul, "LI", 1));
  const across = ok(mapRenderedSelection(sel({ node: li0[0].t, offset: li0[0].off }, { node: li1[3].t, offset: li1[3].off + 1 }), El(box), source), "across the fence");
  assert.equal(across.quote, "Install it:\n\n  ```sh\n  npm install notes-api\n  ```\n\n- Then");
  // painting a range inside the fence lands on the line by position (before: through the fallback's text match), the same marks
  const marks = paintRendered(El(box), source, { start: source.indexOf("npm install"), end: source.indexOf("npm install") + 11 }, "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(marks && stripWs(marks.map((m) => m.textContent).join("")) === "npminstall");
});

test("Rendered: an HTML block that renders several elements, or none, does not shift the blocks after it", () => {
  const source = "<p>one</p>\n<p>two</p>\n\nAfter the block.\n\n<!-- a comment -->\n\nLast paragraph.\n\n<div>x</div>\n\n# End\n";
  const { box } = buildRendered(source);
  const ps = box.childNodes.filter((n) => n.nodeType === 1 && (n as FakeElement).tagName === "P") as FakeElement[];
  assert.equal(ps.length, 4);
  let r = bad(mapRenderedSelection(wholeOf(ps[0]), El(box), source));
  assert.match(r.reason, /HTML block/);
  assert.equal(r.blockStartLine, 0);
  r = bad(mapRenderedSelection(wholeOf(ps[1]), El(box), source));
  assert.match(r.reason, /HTML block/);
  assert.equal(ok(mapRenderedSelection(wholeOf(ps[2]), El(box), source)).quote, "After the block.");
  assert.equal(ok(mapRenderedSelection(wholeOf(ps[3]), El(box), source)).quote, "Last paragraph.");
  assert.equal(ok(mapRenderedSelection(wholeOf(firstEl(box, "H1")), El(box), source)).quote, "End");
  const div = box.childNodes.find((n) => n.nodeType === 1 && (n as FakeElement).tagName === "DIV") as FakeElement;
  r = bad(mapRenderedSelection(wholeOf(div), El(box), source));
  assert.match(r.reason, /HTML block/);
  assert.equal(r.blockStartLine, 9);
  // a selection from the html block into the paragraph after it refuses; from the paragraph on it maps
  const a = nonWsPositions(ps[1]), b = nonWsPositions(ps[2]);
  bad(mapRenderedSelection(sel({ node: a[0].t, offset: a[0].off }, { node: b[2].t, offset: b[2].off + 1 }), El(box), source));
  assert.equal(ok(mapRenderedSelection(sel({ node: b[0].t, offset: b[0].off }, { node: nonWsPositions(ps[3])[3].t, offset: nonWsPositions(ps[3])[3].off + 1 }), El(box), source)).quote,
               "After the block.\n\n<!-- a comment -->\n\nLast");
});

test("Rendered: inline HTML tags carry no text and stay in a quote that spans them; an autolink with an ampersand maps", () => {
  const source = "Some <b>bold</b> words and <span class=\"x\">span</span> text.\n\nSee <https://example.com/?a=1&b=2> now.\n";
  const { box } = buildRendered(source);
  assert.equal(ok(mapRenderedSelection(wholeOf(firstEl(box, "B")), El(box), source)).quote, "bold");
  const p = nonWsPositions(firstEl(box, "P", 0));
  assert.equal(ok(mapRenderedSelection(sel({ node: p[0].t, offset: p[0].off }, { node: p[12].t, offset: p[12].off + 1 }), El(box), source)).quote, "Some <b>bold</b> words");
  assert.equal(ok(mapRenderedSelection(wholeOf(firstEl(box, "A")), El(box), source)).quote, "https://example.com/?a=1&b=2");
  // painting the span's word wraps just it
  const s = source.indexOf("span</span>");
  const marks = paintRendered(El(box), source, { start: s, end: s + 4 }, "fc-hl") as unknown as FakeElement[];
  assert.equal(marks.length, 1); assert.equal(marks[0].textContent, "span"); assert.equal((marks[0].parentNode as FakeElement).tagName, "SPAN");
});

test("caches re-analyze when a container's children are replaced or the source changes", () => {
  const A = "# Alpha\n\nFirst text.\n", B = "# Beta\n\nOther words here.\n";
  const { box } = buildRendered(A);
  assert.equal(ok(mapRenderedSelection(wholeOf(firstEl(box, "H1")), El(box), A)).quote, "Alpha");
  for (const c of box.childNodes.slice()) box.removeChild(c);
  for (const n of parseHTML(box.ownerDocument, viewerHtml(B))) box.appendChild(n);
  assert.equal(ok(mapRenderedSelection(wholeOf(firstEl(box, "H1")), El(box), B)).quote, "Beta");
  bad(mapRenderedSelection(wholeOf(firstEl(box, "H1")), El(box), A));
  // Raw: the same code element re-filled with another file
  const raw = buildRaw("one\ntwo\n", "notes.txt");
  let t = allText(raw.code, isRow);
  assert.equal(ok(mapRawSelection(sel({ node: t[0], offset: 0 }, { node: t[1], offset: 3 }), El(raw.code), "one\ntwo\n")).quote, "one\ntwo");
  for (const c of raw.code.childNodes.slice()) raw.code.removeChild(c);
  for (const n of parseHTML(raw.code.ownerDocument, wrapNumberedHtml(escapeHtml("three\nfour\n")))) raw.code.appendChild(n);
  t = allText(raw.code, isRow);
  assert.equal(ok(mapRawSelection(sel({ node: t[0], offset: 0 }, { node: t[1], offset: 4 }), El(raw.code), "three\nfour\n")).quote, "three\nfour");
});

// ── Rendered: a failed figure's label is a control (Slice 7 of plans/markdown-viewer.md, item 2) ──────────────────
/** The label file-view.ts parks beside a figure whose `error` event fired (contract C2): `span.fv-figerr[data-fv-figerr]`, the
 *  img's next sibling in the img's own parent, its text the viewer's (the fact, the authored source, the alt), never the note's. */
function failedFigureLabel(img: FakeElement, text: string): FakeElement {
  const doc = img.ownerDocument, parent = img.parentNode as FakeElement;
  const label = doc.createElement("span"); label.setAttribute("class", "fv-figerr"); label.setAttribute("data-fv-figerr", "");
  label.appendChild(doc.createTextNode(text));
  const i = parent.childNodes.indexOf(img);
  parent.insertBefore(label, parent.childNodes[i + 1] ?? null);
  return label;
}

test("Rendered: a failed figure's label (span.fv-figerr, the img's next sibling) is a control: the paragraph holding it pairs with its block, its prose maps and paints, a drag from inside the label lands at the label's edge, the label alone selects no text of the note, and a label beside a bare <img> html block leaves the blocks after it paired", () => {
  const caption = "The caption says what the plot showed.";
  const source = "# Report\n\nBefore the figure.\n\n![p95 latency](figs/missing.png) " + caption + "\n\nAfter the figure.\n";
  const { box } = buildRendered(source);
  const p = firstEl(box, "P", 1);
  const img = firstEl(p, "IMG");
  assert.ok(img && img.parentNode === p, "the fixture's img sits in the second paragraph");
  const label = failedFigureLabel(img, "Image failed to load: figs/missing.png (p95 latency)");
  assert.equal(p.childNodes.indexOf(label), p.childNodes.indexOf(img) + 1, "the label is the img's next sibling");
  const spans = sourceBlockSpans(source);
  assert.equal(source.slice(spans[2].start, spans[2].end), "![p95 latency](figs/missing.png) " + caption, "block 2 is the figure's paragraph");
  assert.equal(renderedBlockIndex(El(box), source, El(p)), 2, "the paragraph is block 2's node (a refused block answers its index by tag, so this held before Slice 7 too)");
  const start = source.indexOf(caption);
  const capText = allText(p, null).find((t) => t.data.includes(caption))!;
  assert.ok(capText, "the caption's text node");
  const at = capText.data.indexOf(caption);
  const r = ok(mapRenderedSelection(sel({ node: capText, offset: at }, { node: capText, offset: at + caption.length }), El(box), source),
    "the caption maps (before Slice 7 the label's text read as the note's, so the paragraph's text did not match its source and every selection in it was refused)");
  assert.deepEqual(r.range, { start, end: start + caption.length }); assert.equal(r.quote, caption);
  // a drag that starts inside the label and ends in the caption: the endpoint inside the control sits at its edge (the footnote back link's rule)
  const lt = allText(label, null)[0];
  const fromLabel = ok(mapRenderedSelection(sel({ node: lt, offset: 6 }, { node: capText, offset: at + "The caption".length }), El(box), source), "from the label into the caption");
  assert.equal(fromLabel.quote, "The caption");
  // the label alone selects no text of the note
  assert.equal(bad(mapRenderedSelection(sel({ node: lt, offset: 0 }, { node: lt, offset: lt.data.length }), El(box), source), "the label alone").reason, "Select some text to comment on.");
  // a highlight over the caption paints on the caption's characters and never on the label's
  const marks = paintRendered(El(box), source, { start, end: start + caption.length }, "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(marks && marks.length, "the highlight paints (before: the pairing refused and paintRendered answered null)");
  assert.equal(marks!.map((m) => m.textContent).join(""), caption);
  assert.equal(label.parentNode, p, "the label stands where it was"); assert.equal(label.childNodes.length, 1);
  // a bare <img> html block: the img is a top-level node of the box, so its label lands at the top level too; the blocks after it
  // still pair, so a comment on the paragraph after the figure paints
  const src2 = "# Report\n\n<img src=\"figs/missing.png\" alt=\"fig\">\n\nAfter the figure.\n";
  const { box: box2 } = buildRendered(src2);
  const img2 = firstEl(box2, "IMG");
  assert.equal(img2.parentNode, box2, "the html block's img is a top-level node");
  failedFigureLabel(img2, "Image failed to load: figs/missing.png (fig)");
  const after = firstEl(box2, "P", 0);
  assert.equal(after.textContent, "After the figure.");
  assert.equal(renderedBlockIndex(El(box2), src2, El(after)), 2, "the paragraph after the figure pairs with its block");
  const s2 = src2.indexOf("After the figure.");
  const m2 = paintRendered(El(box2), src2, { start: s2, end: s2 + "After the figure.".length }, "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(m2 && m2.length, "the comment after a failed top-level figure paints");
  assert.equal(m2!.map((m) => m.textContent).join(""), "After the figure.");
});

test("Rendered: a failed figure's label at the box's TOP level (an html block whose img is a top-level node) is no block's node: the img's block owns its img alone, or the Comments panel's wrap around it, never the label after it; a heading and a paragraph nested in the html block's own unclosed <div> map with the label standing between the img and the div, the panel open or closed (the Slice 7 consolidation pass; before: the block owned the img and the label, and with the panel open the heading in the div was refused as not matching the file)", () => {
  // the browser leg's reading of a block's elements (anchor-map-wrappers-browser.test.ts): the layer's wrap stands for its img
  const tags = (els: Element[]): string[] => els.map((e) => ((e as unknown as FakeElement).getAttribute("class") || "").split(" ").includes("fc-imgwrap") ? "IMG" : e.tagName);
  /** The regions layer's wrap around `img` while the Comments panel is open (file-comments-regions.ts), in the img's place. */
  const wrapImg = (img: FakeElement): FakeElement => {
    const doc = img.ownerDocument, parent = img.parentNode as FakeElement;
    const wrap = doc.createElement("span"); wrap.setAttribute("class", "fc-imgwrap");
    parent.insertBefore(wrap, img); parent.removeChild(img); wrap.appendChild(img);
    return wrap;
  };
  const whole = (e: FakeElement): SelLike => { const t = allText(e, null); return sel({ node: t[0], offset: 0 }, { node: t[t.length - 1], offset: t[t.length - 1].data.length }); };
  // a bare <img> html block, the label its top-level next sibling
  const src = "# Report\n\n<img src=\"figs/missing.png\" alt=\"fig\">\n\nAfter the figure.\n";
  const { box } = buildRendered(src);
  const img = firstEl(box, "IMG");
  assert.equal(img.parentNode, box, "the html block's img is a top-level node");
  const spans = sourceBlockSpans(src);
  assert.equal(src.slice(spans[1].start, spans[1].end), "<img src=\"figs/missing.png\" alt=\"fig\">", "block 1 is the img's html block");
  assert.deepEqual(tags(renderedBlockElements(El(box), src, 1)), ["IMG"], "before any label: the block owns its img");
  const label = failedFigureLabel(img, "Image failed to load: figs/missing.png (fig)");
  assert.equal(label.parentNode, box, "the label is a top-level node too");
  assert.deepEqual(tags(renderedBlockElements(El(box), src, 1)), ["IMG"], "with the label: the block owns its img alone (before the consolidation pass: the img and the label)");
  assert.equal(renderedBlockIndex(El(box), src, El(label)), -1, "the label is no block's node");
  assert.equal(renderedBlockIndex(El(box), src, El(firstEl(box, "P"))), 2, "the paragraph after pairs");
  const wrap = wrapImg(img);
  assert.equal(box.childNodes.indexOf(label), box.childNodes.indexOf(wrap) + 1, "the label follows the wrap (contract C2's addendum)");
  assert.deepEqual(tags(renderedBlockElements(El(box), src, 1)), ["IMG"], "with the panel's wrap around the img: the block owns the wrap alone");
  assert.equal(renderedBlockIndex(El(box), src, El(firstEl(box, "P"))), 2, "the paragraph after still pairs");
  // the README shape: the img and an unclosed <div align="center"> in one html block, the heading and the paragraph the
  // markdown after it renders nested inside the div (the parse nests as the browser does), the label between the img and the div
  const src2 = "<img src=\"logo.png\" alt=\"l\">\n<div align=\"center\">\n\n# Head 003\n\nPara 004 echo foxtrot.\n\n</div>\n\nAfter 005 hotel india.\n";
  const passages = ["Head 003", "Para 004 echo foxtrot.", "After 005 hotel india."];
  for (const panel of [false, true]) {
    const what = panel ? "panel open (the wrap around the img)" : "panel closed";
    const { box: box2 } = buildRendered(src2);
    const img2 = firstEl(box2, "IMG");
    assert.equal(img2.parentNode, box2, what + ": the img is a top-level node");
    const div = firstEl(box2, "DIV", 1);   // the box itself is the first DIV
    const h1 = firstEl(div, "H1");
    assert.equal(h1.textContent, "Head 003", what + ": the heading renders inside the open div");
    const label2 = failedFigureLabel(img2, "Image failed to load: logo.png (l)");
    if (panel) wrapImg(img2);
    const between = box2.childNodes.slice(box2.childNodes.indexOf(label2) + 1, box2.childNodes.indexOf(div));
    assert.ok(box2.childNodes.indexOf(div) > box2.childNodes.indexOf(label2) && between.every((n) => n.nodeType === 3 && n.textContent.trim() === ""), what + ": the label stands between the img and the div (the html block's own line feed the only text between)");
    assert.deepEqual(tags(renderedBlockElements(El(box2), src2, 0)), ["IMG", "DIV"], what + ": the html block owns the img and the div, never the label (before: [IMG, SPAN])");
    for (const p of passages) {
      const el = p.startsWith("Head") ? h1 : p.startsWith("Para") ? firstEl(div, "P") : firstEl(box2, "P", 1);
      assert.equal(el.textContent, p, what + ": the element of " + JSON.stringify(p));
      const r = ok(mapRenderedSelection(whole(el), El(box2), src2), what + ": " + JSON.stringify(p) + " maps (before the consolidation pass, with the panel open: refused as not matching the file)");
      assert.deepEqual(r.range, { start: src2.indexOf(p), end: src2.indexOf(p) + p.length }, what + ": " + JSON.stringify(p) + " to its own offsets");
      assert.equal(r.quote, p);
    }
  }
});

// ── Rendered: a figure's "Open the picture" control is a companion, left out with the label (the link-navigation follow-on's L3) ──
/** The control file-view.ts places after a loaded figure (decideFigureControl): `button.fv-figopen[data-fv-figopen]`, the img's
 *  next sibling in the img's own parent, holding the glyph's clone (an svg) and no text of the note's; with `label`, a text node
 *  of its own after the glyph, the label-bearing variant CONTROL_CLASSES' entry is for (the real control has none). */
function figureOpenControl(img: FakeElement, label?: string): FakeElement {
  const doc = img.ownerDocument, parent = img.parentNode as FakeElement;
  const b = doc.createElement("button"); b.setAttribute("class", "fileview-btn fileview-icon fv-figopen"); b.setAttribute("data-fv-figopen", ""); b.setAttribute("type", "button"); b.setAttribute("title", "Open the picture");
  const svg = doc.createElement("svg"); svg.setAttribute("viewBox", "0 0 16 16"); const path = doc.createElement("path"); path.setAttribute("d", "M2 9V2h7"); svg.appendChild(path); b.appendChild(svg);
  if (label !== undefined) b.appendChild(doc.createTextNode(label));
  const i = parent.childNodes.indexOf(img);
  parent.insertBefore(b, parent.childNodes[i + 1] ?? null);
  return b;
}

test("Rendered: a figure's Open the picture control (button.fv-figopen, the img's next sibling, a glyph with no text) at the box's TOP level is no block's node, as the failed figure's label is: the img's html block owns its img alone, or the panel's wrap around it, the control answers no block, the paragraph after pairs and paints, the README shape owns its img and its div with the control between, and beside prose the caption still maps (the file review's landing round, tests-2: this had a source-text pin alone under a name claiming the executed property)", () => {
  const tags = (els: Element[]): string[] => els.map((e) => ((e as unknown as FakeElement).getAttribute("class") || "").split(" ").includes("fc-imgwrap") ? "IMG" : e.tagName);
  const wrapImg = (img: FakeElement): FakeElement => {
    const doc = img.ownerDocument, parent = img.parentNode as FakeElement;
    const wrap = doc.createElement("span"); wrap.setAttribute("class", "fc-imgwrap");
    parent.insertBefore(wrap, img); parent.removeChild(img); wrap.appendChild(img);
    return wrap;
  };
  const src = "# Report\n\n<img src=\"figs/plot.png\" alt=\"fig\">\n\nAfter the figure.\n";
  const spans = sourceBlockSpans(src);
  assert.equal(src.slice(spans[1].start, spans[1].end), "<img src=\"figs/plot.png\" alt=\"fig\">", "block 1 is the img's html block");
  for (const panel of [false, true]) {
    const what = panel ? "panel open (the wrap around the img)" : "panel closed";
    const { box } = buildRendered(src);
    const img = firstEl(box, "IMG");
    assert.equal(img.parentNode, box, what + ": the html block's img is a top-level node");
    assert.deepEqual(tags(renderedBlockElements(El(box), src, 1)), ["IMG"], what + ": before any control the block owns its img");
    const ctrl = figureOpenControl(img);
    assert.equal(ctrl.parentNode, box, what + ": the control is a top-level node too");
    assert.equal(box.childNodes.indexOf(ctrl), box.childNodes.indexOf(img) + 1, what + ": the img's next sibling");
    assert.equal(allText(ctrl, null).length, 0, what + ": the control holds no text node (a glyph)");
    if (panel) { const wrap = wrapImg(img); assert.equal(box.childNodes.indexOf(ctrl), box.childNodes.indexOf(wrap) + 1, what + ": the control follows the wrap"); }
    assert.deepEqual(tags(renderedBlockElements(El(box), src, 1)), ["IMG"], what + ": with the control the block owns its img alone (without isFigureCompanion's fv-figopen arm a top-level button is a content node and the block owns [IMG, BUTTON])");
    assert.equal(renderedBlockIndex(El(box), src, El(ctrl)), -1, what + ": the control is no block's node");
    const after = firstEl(box, "P");
    assert.equal(after.textContent, "After the figure.");
    assert.equal(renderedBlockIndex(El(box), src, El(after)), 2, what + ": the paragraph after pairs");
    const s2 = src.indexOf("After the figure.");
    const marks = paintRendered(El(box), src, { start: s2, end: s2 + "After the figure.".length }, "fc-hl") as unknown as FakeElement[] | null;
    assert.ok(marks && marks.length, what + ": a comment on the paragraph after the figure paints");
    assert.equal(marks!.map((m) => m.textContent).join(""), "After the figure.");
    assert.equal(ctrl.parentNode, box, what + ": the control stands where it was");
  }
  // the README shape: the img and an unclosed <div align="center"> in one html block, the control between them
  const src2 = "<img src=\"logo.png\" alt=\"l\">\n<div align=\"center\">\n\n# Head 003\n\nPara 004 echo foxtrot.\n\n</div>\n\nAfter 005 hotel india.\n";
  const { box: box2 } = buildRendered(src2);
  const img2 = firstEl(box2, "IMG");
  const div = firstEl(box2, "DIV", 1);
  const ctrl2 = figureOpenControl(img2);
  assert.ok(box2.childNodes.indexOf(div) > box2.childNodes.indexOf(ctrl2) && box2.childNodes.indexOf(ctrl2) > box2.childNodes.indexOf(img2), "the control stands between the img and the div");
  assert.deepEqual(tags(renderedBlockElements(El(box2), src2, 0)), ["IMG", "DIV"], "the html block owns the img and the div, never the control (without the arm: [IMG, BUTTON, DIV])");
  assert.equal(renderedBlockIndex(El(box2), src2, El(firstEl(div, "H1"))), 1, "the heading nested in the div maps to its block");
  // inside a paragraph: the control beside the img, the caption maps and paints, the control untouched
  const caption = "The caption says what the plot showed.";
  const src3 = "# Report\n\nBefore the figure.\n\n![p95 latency](figs/plot.png) " + caption + "\n\nAfter the figure.\n";
  const { box: box3 } = buildRendered(src3);
  const p = firstEl(box3, "P", 1);
  const img3 = firstEl(p, "IMG");
  const ctrl3 = figureOpenControl(img3);
  assert.equal(p.childNodes.indexOf(ctrl3), p.childNodes.indexOf(img3) + 1, "the control is the img's next sibling inside the paragraph");
  assert.equal(renderedBlockIndex(El(box3), src3, El(p)), 2, "the paragraph is block 2's node");
  const start = src3.indexOf(caption);
  const capText = allText(p, null).find((t) => t.data.includes(caption))!;
  const at = capText.data.indexOf(caption);
  const r = ok(mapRenderedSelection(sel({ node: capText, offset: at }, { node: capText, offset: at + caption.length }), El(box3), src3), "the caption maps beside the control");
  assert.deepEqual(r.range, { start, end: start + caption.length }); assert.equal(r.quote, caption);
  const marks3 = paintRendered(El(box3), src3, { start, end: start + caption.length }, "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(marks3 && marks3.length, "the highlight paints");
  assert.equal(marks3!.map((m) => m.textContent).join(""), caption);
  assert.equal(ctrl3.parentNode, p, "the control stands where it was"); assert.equal(ctrl3.childNodes.length, 1);
});

test("Rendered: the Open the picture control carrying a text node of its own beside the img inside a paragraph: the caption still maps to its own offsets and paints, the control's text skipped as the fence's Copy button's is (the file review's landing round, extra9-1: the executed case of anchor-map.ts's fv-figopen entry, which the glyph-only control above cannot red on; without the entry the walk reads the label as the paragraph's text and refuses the block as not matching the file)", () => {
  const caption = "The caption says what the plot showed.";
  const src = "# Report\n\nBefore the figure.\n\n![p95 latency](figs/plot.png) " + caption + "\n\nAfter the figure.\n";
  const { box } = buildRendered(src);
  const p = firstEl(box, "P", 1);
  const img = firstEl(p, "IMG");
  const ctrl = figureOpenControl(img, "Open");
  assert.equal(ctrl.textContent, "Open", "the fixture: the control carries a text node");
  assert.equal(p.childNodes.indexOf(ctrl), p.childNodes.indexOf(img) + 1, "the control is the img's next sibling inside the paragraph");
  const start = src.indexOf(caption);
  const capText = allText(p, null).find((t) => t.data.includes(caption))!;
  const at = capText.data.indexOf(caption);
  const r = ok(mapRenderedSelection(sel({ node: capText, offset: at }, { node: capText, offset: at + caption.length }), El(box), src), "the caption maps beside the labelled control (without anchor-map.ts's fv-figopen entry: refused, the label counted as the paragraph's text)");
  assert.deepEqual(r.range, { start, end: start + caption.length }); assert.equal(r.quote, caption);
  const marks = paintRendered(El(box), src, { start, end: start + caption.length }, "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(marks && marks.length, "the highlight paints");
  assert.equal(marks!.map((m) => m.textContent).join(""), caption);
  assert.equal(ctrl.parentNode, p, "the control stands where it was"); assert.equal(ctrl.textContent, "Open", "its text untouched");
});


// ── change marks (Slice 2, contract D4) ────────────────────────────────────────────────────────────
// The changes are built through the engine's own toHunks over synthetic ops (the notes-api world), so
// the painter is fed the exact hunk shape the host ships: kind ins | del | sub, curFrom/curTo in
// current-text coordinates, oldText, newText.

/** A structural serialization: every text node its own `#"..."`, so a split that was not closed back up
 *  shows, as does any attribute or element left behind. */
function serialize(n: FakeNode): string {
  if (n.nodeType === 3) return "#" + JSON.stringify((n as FakeText).data);
  const e = n as FakeElement;
  const attrs = [...e.attrs.entries()].sort().map(([k, v]) => ` ${k}=${JSON.stringify(v)}`).join("");
  return `<${e.tagName}${attrs}>` + e.childNodes.map(serialize).join("") + `</${e.tagName}>`;
}
const withClass = (root: FakeNode, cls: string): FakeElement[] => {
  const out: FakeElement[] = [];
  const visit = (n: FakeNode) => { if (n.nodeType === 1 && (((n as FakeElement).getAttribute("class") || "").split(" ").includes(cls))) out.push(n as FakeElement); n.childNodes.forEach(visit); };
  visit(root); return out;
};
const rowOf = (n: FakeNode): FakeElement | null => { let p: FakeNode | null = n; while (p) { if (p.nodeType === 1 && isRow(p as FakeElement)) return p as FakeElement; p = p.parentNode; } return null; };
/** The rows' text before `target` in document order. */
function rowTextBefore(root: FakeNode, target: FakeNode): string {
  let out = ""; let done = false;
  const visit = (n: FakeNode, inRow: boolean) => {
    if (done) return;
    if (n === target) { done = true; return; }
    if (n.nodeType === 3) { if (inRow) out += (n as FakeText).data; return; }
    const here = inRow || isRow(n as FakeElement);
    for (const c of n.childNodes) visit(c, here);
  };
  visit(root, false);
  return out;
}
const docOrder = (root: FakeNode): FakeNode[] => { const out: FakeNode[] = []; const visit = (n: FakeNode) => { out.push(n); n.childNodes.forEach(visit); }; visit(root); return out; };
/** What the panel's own unpaint does to a comment highlight: children out, mark gone, the parent's text merged. */
function unwrapAll(root: FakeNode, cls: string): void {
  for (const m of withClass(root, cls).reverse()) {
    const p = m.parentNode as FakeElement;
    while (m.childNodes.length) p.insertBefore(m.childNodes[0], m);
    p.removeChild(m);
    let i = 0;
    while (i < p.childNodes.length) {
      const c = p.childNodes[i];
      if (c.nodeType !== 3) { i++; continue; }
      while (i + 1 < p.childNodes.length && p.childNodes[i + 1].nodeType === 3) { (c as FakeText).data += (p.childNodes[i + 1] as FakeText).data; p.removeChild(p.childNodes[i + 1]); }
      i++;
    }
  }
}
type Op = { id: string; author: string; ts: number; from: number; newText: string; oldText: string; anchor: null };
const op = (id: string, author: string, from: number, newText: string, oldText: string): Op => ({ id, author, ts: 1, from, newText, oldText, anchor: null });
/** engine.toHunks over the ops, mapped to the painter's record (what the panel does with the host's hunks). */
function changesOf(ops: Op[]): ChangePaint[] {
  return (engine.toHunks(ops) as { id: string; author: string; kind: "ins" | "del" | "sub"; curFrom: number; curTo: number; oldText: string; newText: string }[])
    .map((h) => ({ id: h.id, kind: h.kind, curFrom: h.curFrom, curTo: h.curTo, oldText: h.oldText, author: h.author, newText: h.newText }));
}
const COLORS: Record<string, string> = { web: "rgb(10, 20, 30)", api: "var(--st-ready-bg)" };
const stylesFor = (c: ChangePaint) => ({ "--fc-author": COLORS[c.author] });

/** The CRLF fixture's changes: an insertion across two rows, a long deletion, a substitution across a blank
 *  pair of rows, deletions at the file's start, a line ending, an empty row and the end of the file, an
 *  insertion across a lone CR, and one whose new text does not match the file (offsets from another string). */
function crlfChanges(source: string) {
  const at = (s: string, from = 0) => { const i = source.indexOf(s, from); assert.ok(i >= 0, "fixture has " + JSON.stringify(s)); return i; };
  const insNew = "store.get(note_id)\r\n\tif note is None";
  const subNew = "respond(200, note)\r\n\r\n\r\ndef put_note";
  const longOld = 'log.warning("note %s is missing", note_id)\r\n\t\traise NotFound(note_id)  # the older path\r\n\t\t';
  assert.ok(longOld.length > DEL_LABEL_MAX);
  const crNew = "lone CR follows this comment\rand this";
  const ops = [
    op("c-ins", "web", at(insNew), insNew, ""),
    op("c-del", "api", at('return respond(404, "missing")'), "", longOld),
    op("c-sub", "web", at(subNew), subNew, "respond(200, note)\r\n\r\ndef put_note"),
    op("c-del0", "api", 0, "", "# handlers\r\n"),
    op("c-delend", "web", at("\r\n"), "", "  # noqa"),
    op("c-delempty", "api", at("\r\n\r\nLIMIT"), "", "unused = None"),
    op("c-deleof", "web", source.length, "", "\r\n# trailing"),
    op("c-inscr", "api", at(crNew), crNew, ""),
  ];
  const changes = changesOf(ops);
  const kinds = Object.fromEntries(changes.map((c) => [c.id, c.kind]));
  assert.deepEqual(kinds, { "c-ins": "ins", "c-del": "del", "c-sub": "sub", "c-del0": "del", "c-delend": "del", "c-delempty": "del", "c-deleof": "del", "c-inscr": "ins" }, "the engine's three kinds (D1)");
  const byId = Object.fromEntries(changes.map((c) => [c.id, c]));
  assert.equal(byId["c-del"].curFrom, byId["c-del"].curTo, "a del is a point");
  assert.equal(source.slice(byId["c-ins"].curFrom, byId["c-ins"].curTo), insNew);
  return { changes, byId, longOld };
}

test("pins: the change-mark rules exist in both sheets inside the panel block, with the D4 declarations", () => {
  const MAP = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map.ts"), "utf8");
  assert.match(MAP, /m\.setAttribute\("data-fc-text", label\)/, "the label rides an attribute, never a text node");
  for (const sheet of ["styles.css", "feed.css"]) {
    const css = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", sheet), "utf8");
    const a = css.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
    const b = css.indexOf("/* ── end file comments panel ── */");
    const block = css.slice(a, b);
    assert.match(block, /\n\.fc-ins \{ background: color-mix\(in srgb, var\(--green\) 12%, transparent\); border-bottom: 2px solid var\(--fc-author, var\(--accent\)\);\n\s+color: inherit; cursor: pointer;/, sheet + ": .fc-ins tint, author underline, mark ink");
    assert.match(block, /\n\.fc-del \{ border-bottom: 2px solid var\(--fc-author, var\(--accent\)\); cursor: pointer; user-select: none;/, sheet + ": .fc-del author underline");
    assert.match(block, /\n\.fc-del::before \{ content: attr\(data-fc-text\); text-decoration: line-through; color: var\(--dim\);/, sheet + ": the struck label is generated content");
  }
});

test("Raw change marks over the CRLF fixture: the walks stay exact, no text node is added, each row's slice paints, the del label is capped, unpaint restores the DOM", () => {
  const source = fixture("handlers-crlf.py");
  const { code, wrap } = buildRaw(source, "handlers-crlf.py");
  const { changes, byId, longOld } = crlfChanges(source);
  const before = serialize(code);
  const textBefore = domText(code, isRow);
  const rows = withClass(code, "fv-cl");
  assert.equal(rows.length, 15);
  const domIdx = rawDomIndexOf(source);
  const g = (i: number) => domIdx(i) as number;
  // selections to compare across the paint: over the painted regions, across a mark's edge, and whole lines
  const probes: [number, number][] = [
    [byId["c-ins"].curFrom, byId["c-ins"].curTo],
    [byId["c-sub"].curFrom, byId["c-sub"].curTo],
    [source.indexOf("if note is None"), source.indexOf('"missing")') + '"missing")'.length],
    [0, source.indexOf("note_id):") + "note_id):".length],
    [source.indexOf("LIMIT"), source.length - 2],
    [byId["c-inscr"].curFrom + 5, byId["c-inscr"].curTo + 12],
  ];
  const probe = (root: FakeElement, [i, j]: [number, number]) => mapRawSelection(sel(boundaries(root, g(i), isRow).text[0], boundaries(root, g(j - 1) + 1, isRow).text[0]), El(root), source);
  const pre = probes.map((p) => ok(probe(code, p)));
  const rowBefore = probes.map(([i]) => rawRowForOffset(El(code), source, i));

  const painted = paintChangesRaw(El(code), source, changes, stylesFor) as unknown as FakeElement[];
  assert.ok(painted.length >= 12, "painted " + painted.length);
  assert.equal(domText(code, isRow), textBefore, "painting adds no text under any row");
  const ids = new Set(painted.map((m) => m.getAttribute("data-id")));
  assert.deepEqual([...ids].sort(), ["c-del", "c-del0", "c-delempty", "c-delend", "c-deleof", "c-ins", "c-inscr", "c-sub"], "every change got paint");
  for (const m of painted) {
    const cls = m.getAttribute("class");
    assert.ok(cls === "fc-ins" || cls === "fc-del", "class " + cls);
    assert.equal(m.getAttribute("data-act"), "fcchange");
    const c = byId[m.getAttribute("data-id") as string];
    assert.equal(m.getAttribute("data-author"), c.author);
    assert.equal(m.getAttribute("style"), "--fc-author: " + COLORS[c.author] + ";", "the author's colour rides inline");
    assert.ok(rowOf(m), "every mark sits inside a row");
    if (cls === "fc-ins") {
      assert.equal(m.tagName, "MARK");
      assert.ok(m.childNodes.length > 0 && m.childNodes.every((x) => x.nodeType === 3), "an insertion wraps text nodes only");
      assert.equal(m.getAttribute("data-fc-text"), null);
    } else {
      assert.equal(m.tagName, "SPAN");
      assert.equal(m.childNodes.length, 0, "a deletion point has no children");
      assert.equal(m.getAttribute("data-fc-text"), deletionLabel(c.oldText));
      // the point sits exactly at its offset: the rows' text before it is the file's text before curFrom
      assert.equal(noEol(rowTextBefore(code, m)), noEol(source.slice(0, c.curFrom)), "point " + c.id);
    }
  }
  // the deletion's label: capped at 80 with an ellipsis, line endings as the rows show them
  const delPoint = painted.find((m) => m.getAttribute("data-id") === "c-del")!;
  const label = delPoint.getAttribute("data-fc-text")!;
  assert.equal(label.length, DEL_LABEL_MAX);
  assert.ok(label.endsWith("…"));
  assert.equal(label.slice(0, -1), longOld.replace(/\r\n/g, "\n").slice(0, DEL_LABEL_MAX - 1));
  assert.equal(painted.find((m) => m.getAttribute("data-id") === "c-del0")!.getAttribute("data-fc-text"), "# handlers\n");
  assert.equal(rowOf(painted.find((m) => m.getAttribute("data-id") === "c-delempty")!), rows[12], "the point on an empty row is inside that row");
  assert.equal(rowOf(painted.find((m) => m.getAttribute("data-id") === "c-deleof")!), rows[14], "the end of the file is the last row's end");
  assert.equal(rowOf(painted.find((m) => m.getAttribute("data-id") === "c-delend")!), rows[0], "an offset on a line ending is the end of its row");
  // an insertion across rows paints each row's slice, in the rows it spans, and nothing else
  const marksOf = (id: string) => painted.filter((m) => m.getAttribute("class") === "fc-ins" && m.getAttribute("data-id") === id);
  const insMarks = marksOf("c-ins");
  assert.equal(new Set(insMarks.map(rowOf)).size, 2);
  sameNodes([...new Set(insMarks.map(rowOf))], [rows[1], rows[2]], "the insertion's marks sit in rows 1 and 2, in order");   // by identity (ui/test-dom-shim.ts sameNodes)
  assert.equal(noEol(insMarks.map((m) => m.textContent).join("")), noEol(byId["c-ins"].newText!));
  const subMarks = marksOf("c-sub");
  // the blank CRLF rows in between show their CR as an LF, which the range covers, so each holds one mark over it
  sameNodes([...new Set(subMarks.map(rowOf))], [rows[4], rows[5], rows[6], rows[7]], "the substitution's marks sit in rows 4 to 7, in order");
  assert.deepEqual(subMarks.filter((m) => rowOf(m) === rows[5] || rowOf(m) === rows[6]).map((m) => m.textContent), ["\n", "\n"]);
  assert.equal(noEol(subMarks.map((m) => m.textContent).join("")), noEol(byId["c-sub"].newText!));
  // the substitution's point comes first, right before its first mark
  const order = docOrder(code);
  const subPoint = painted.find((m) => m.getAttribute("class") === "fc-del" && m.getAttribute("data-id") === "c-sub")!;
  assert.ok(order.indexOf(subPoint) < order.indexOf(subMarks[0]), "point before the wrap");
  assert.equal(subPoint.parentNode!.childNodes[subPoint.parentNode!.childNodes.indexOf(subPoint) + 1], subMarks[0], "adjacent");
  // the lone-CR insertion: the DOM shows the CR as a line break inside the row; the mark covers it
  assert.equal(marksOf("c-inscr").map((m) => m.textContent).join(""), byId["c-inscr"].newText!.replace("\r", "\n"));

  // ── every Raw walk, over the painted DOM: a fresh analysis (root = the wrapper, never analyzed) and the cached one
  for (let k = 0; k < probes.length; k++) {
    assert.deepEqual(ok(probe(wrap, probes[k])), pre[k], "fresh analysis, probe " + k);
    assert.deepEqual(ok(probe(code, probes[k])), pre[k], "cached analysis, probe " + k);
    assert.equal(rawRowForOffset(El(wrap), source, probes[k][0]), rowBefore[k], "row lookup unaffected, probe " + k);
    // element boundaries at the marks' edges (what a browser reports when the caret sits on a mark's edge)
    const bs = boundaries(wrap, g(probes[k][0]), isRow), be = boundaries(wrap, g(probes[k][1] - 1) + 1, isRow);
    if (bs.elem.length && be.elem.length) assert.deepEqual(ok(mapRawSelection(sel(bs.elem[bs.elem.length - 1], be.elem[be.elem.length - 1]), El(wrap), source)), pre[k], "element boundaries, probe " + k);
  }
  // a selection that starts ON the deletion point and one that starts inside an insertion's mark
  const j = byId["c-del"].curFrom + 'return respond(404, "missing")'.length;
  const fromPoint = ok(mapRawSelection(sel({ node: delPoint, offset: 0 }, boundaries(wrap, g(j - 1) + 1, isRow).text[0]), El(wrap), source));
  assert.deepEqual(fromPoint.range, { start: byId["c-del"].curFrom, end: j });
  assert.equal(fromPoint.quote, 'return respond(404, "missing")');
  const inMark = (n: FakeNode): boolean => { let p: FakeNode | null = n; while (p) { if (p.nodeType === 1 && (p as FakeElement).getAttribute("class") === "fc-ins") return true; p = p.parentNode; } return false; };
  const s2 = boundaries(wrap, g(byId["c-ins"].curFrom + 6), isRow).text[0], e2 = boundaries(wrap, g(byId["c-ins"].curTo - 1) + 1, isRow).text[0];
  assert.ok(inMark(s2.node) && inMark(e2.node), "both ends inside the insertion's marks");
  assert.ok(rowOf(s2.node) === rows[1] && rowOf(e2.node) === rows[2], "in the two rows it spans");
  const r2 = ok(mapRawSelection(sel(s2, e2), El(wrap), source));
  assert.equal(r2.quote, "get(note_id)\r\n\tif note is None");
  assert.deepEqual(r2.range, { start: byId["c-ins"].curFrom + 6, end: byId["c-ins"].curTo });
  // a comment highlight still paints exactly over the marked rows
  const hl = paintRaw(El(wrap), source, { start: byId["c-ins"].curFrom - 7, end: byId["c-ins"].curFrom + 9 }, "fc-hl", { id: "k1" }) as unknown as FakeElement[];
  assert.equal(noEol(hl.map((m) => m.textContent).join("")), "note = store.get");
  assert.equal(domText(code, isRow), textBefore);

  // ── unpaint: the change marks go, the highlight stays (in the two pieces it was painted in, since it crossed an
  //    insertion's edge: the panel repaints every mark each pass, so a split never outlives one); with the highlight
  //    unwrapped the way the panel unwraps it, the original bytes
  unpaintChanges(El(code));
  assert.equal(withClass(code, "fc-ins").length + withClass(code, "fc-del").length, 0);
  const hlLeft = withClass(code, "fc-hl");
  assert.equal(hlLeft.length, 2);
  assert.equal(hlLeft.map((m) => m.textContent).join(""), "note = store.get");
  unwrapAll(code, "fc-hl");
  assert.equal(serialize(code), before, "the change marks left nothing behind");
  const again = buildRaw(source, "handlers-crlf.py");
  const p2 = paintChangesRaw(El(again.code), source, changes, stylesFor);
  assert.equal(p2.length, painted.length, "a repaint on a fresh body paints the same marks");
  unpaintChanges(El(again.code));
  assert.equal(serialize(again.code), before, "byte-identical to the unpainted DOM");
  // a second paint over the unpainted body (a status refresh) and a second unpaint: still identical
  paintChangesRaw(El(again.code), source, changes, stylesFor);
  unpaintChanges(El(again.code));
  assert.equal(serialize(again.code), before);
});

test("Raw change marks: a highlight painted BEFORE the changes, over an overlapping range, survives their unpaint", () => {
  const source = fixture("handlers-crlf.py");
  const { code } = buildRaw(source, "handlers-crlf.py");
  const { changes, byId } = crlfChanges(source);
  const hlRange: SourceRange = { start: byId["c-ins"].curFrom - 7, end: byId["c-ins"].curFrom + 9 };
  paintRaw(El(code), source, hlRange, "fc-hl fc-hl-context", { act: "fcopen", id: "k2" });
  const withHl = serialize(code);
  const textBefore = domText(code, isRow);
  const painted = paintChangesRaw(El(code), source, changes, stylesFor) as unknown as FakeElement[];
  assert.ok(painted.length >= 12);
  assert.equal(domText(code, isRow), textBefore);
  // the walks are exact with both kinds of mark nested
  const domIdx = rawDomIndexOf(source);
  const i = byId["c-ins"].curFrom, j = byId["c-ins"].curTo;
  const r = ok(mapRawSelection(sel(boundaries(code, domIdx(i) as number, isRow).text[0], boundaries(code, (domIdx(j - 1) as number) + 1, isRow).text[0]), El(code), source));
  assert.deepEqual(r.range, { start: i, end: j });
  unpaintChanges(El(code));
  assert.equal(serialize(code), withHl);
  assert.equal(withClass(code, "fc-hl").length, 1, "the comment highlight is not ours to remove");
});

test("paintRawPoint: offset 0, a line ending, a lone CR, an empty row, the end of the file; nothing for rows that disagree or an empty file", () => {
  const source = "ab\r\ncd\r\n\r\nx\ryz\r\n";
  const { code } = buildRaw(source, "notes.txt");
  const rows = withClass(code, "fv-cl");
  assert.equal(rows.length, 4);
  const textBefore = domText(code, isRow);
  const place = (offset: number, id: string) => {
    const p = paintRawPoint(El(code), source, offset, "fc-del", { act: "fcchange", id, author: "web" }, "old " + id) as unknown as FakeElement | null;
    assert.ok(p, "placed " + id);
    assert.equal(p!.childNodes.length, 0);
    assert.equal(p!.getAttribute("data-fc-text"), "old " + id);
    assert.equal(p!.getAttribute("style"), null, "no styles asked for, none written");
    return p!;
  };
  // the rows' DOM text: "ab\n" "cd\n" "\n" "x\nyz\n" — every CR shows as an LF, so a CRLF row ends in one and
  // an empty CRLF row is not DOM-empty
  assert.deepEqual(rows.map((r) => r.textContent), ["ab\n", "cd\n", "\n", "x\nyz\n"]);
  const p0 = place(0, "a");                         // before "ab"
  const p1 = place(2, "b");                         // on row 0's CR: the end of row 0's visible text
  const p2 = place(3, "c");                         // on the LF of that CRLF: the same spot
  const p3 = place(8, "d");                         // the empty row 2
  const p4 = place(12, "e");                        // after the lone CR, before "yz"
  const p5 = place(source.length, "f");             // the end of the file
  const p6 = place(11, "g");                        // between "x" and the lone CR
  assert.equal(domText(code, isRow), textBefore);
  assert.equal(rowOf(p0), rows[0]); assert.equal(rowOf(p1), rows[0]); assert.equal(rowOf(p2), rows[0]);
  assert.equal(rowOf(p3), rows[2]); assert.equal(rowOf(p4), rows[3]); assert.equal(rowOf(p5), rows[3]); assert.equal(rowOf(p6), rows[3]);
  assert.equal(rowTextBefore(code, p0), "");
  assert.equal(rowTextBefore(code, p1), "ab", "before the CR-as-LF, so the label stays on the row's line");
  assert.equal(rowTextBefore(code, p2), "ab", "the LF of a CRLF: the same end of the visible text");
  assert.equal(rowTextBefore(code, p3), "ab\ncd\n");
  assert.equal(rowTextBefore(code, p6), "ab\ncd\n\nx");
  assert.equal(rowTextBefore(code, p4), "ab\ncd\n\nx\n", "the row shows the lone CR as a line break; the point follows it");
  assert.equal(rowTextBefore(code, p5), "ab\ncd\n\nx\nyz", "the end of the file: before the last row's trailing CR-as-LF");
  // the two points at one spot keep their order of arrival, both before the row's line ending
  const order = docOrder(code);
  assert.ok(order.indexOf(p1) < order.indexOf(p2));
  // the walks over this DOM are exact: the whole text, and a selection that starts on a point
  const t = allText(code, isRow);
  const yz = t.find((x) => x.data === "yz")!;
  assert.equal(ok(mapRawSelection(sel({ node: t[0], offset: 0 }, { node: t[t.length - 1], offset: 1 }), El(code), source)).quote, "ab\r\ncd\r\n\r\nx\ryz");
  assert.equal(ok(mapRawSelection(sel({ node: p4, offset: 0 }, { node: yz, offset: 2 }), El(code), source)).quote, "yz");
  assert.equal(ok(mapRawSelection(sel({ node: p1, offset: 0 }, { node: yz, offset: 1 }), El(code), source)).quote, "cd\r\n\r\nx\ry");
  unpaintChanges(El(code));
  assert.equal(serialize(code), serialize(buildRaw(source, "notes.txt").code));
  // an LF file's blank line IS a DOM-empty row: the point goes into its text cell
  const lf = buildRaw("ab\n\ncd\n", "notes.txt");
  const lfRows = withClass(lf.code, "fv-cl");
  assert.equal(lfRows[1].textContent, "");
  const pe = paintRawPoint(El(lf.code), "ab\n\ncd\n", 3, "fc-del", { id: "e" }, "gone") as unknown as FakeElement;
  assert.equal(rowOf(pe), lfRows[1]);
  assert.equal((pe.parentNode as FakeElement).getAttribute("class"), "fv-ct", "an empty row takes the point in its text cell");
  assert.equal(rowTextBefore(lf.code, pe), "ab");
  const lt = allText(lf.code, isRow);
  assert.equal(ok(mapRawSelection(sel({ node: lt[0], offset: 0 }, { node: lt[1], offset: 2 }), El(lf.code), "ab\n\ncd\n")).quote, "ab\n\ncd");
  unpaintChanges(El(lf.code));
  assert.equal(serialize(lf.code), serialize(buildRaw("ab\n\ncd\n", "notes.txt").code));
  // refusals: rows that do not match the text, and a file with no rows
  assert.equal(paintRawPoint(El(code), "different\r\n", 0, "fc-del", {}, "x"), null);
  const empty = buildRaw("", "notes.txt");
  assert.equal(withClass(empty.code, "fv-cl").length, 0);
  assert.equal(paintRawPoint(El(empty.code), "", 0, "fc-del", {}, "x"), null);
  assert.deepEqual(paintChangesRaw(El(empty.code), "", [{ id: "z", kind: "del", curFrom: 0, curTo: 0, oldText: "gone", author: "web" }], () => ({})), []);
});

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
const nextSibling = (n: FakeNode): FakeNode | null => { const p = n.parentNode!; return p.childNodes[p.childNodes.indexOf(n) + 1] || null; };
/** The nearest top-level block (a child of the .fileview-md box) holding `n`. */
const blockOf = (box: FakeNode, n: FakeNode): FakeElement => { let x = n; while (x.parentNode && x.parentNode !== box) x = x.parentNode; return x as FakeElement; };

// ── Raw change marks on the viewer's grid since Slice 7 (the three-ending split; plans/markdown-viewer.md item 7) ──────────
// The Raw cases above lay the CRLF fixture on the older LF-only grid (buildRaw; see its comment). These two lay sources on
// the grid the viewer builds now, where no row carries an ending and a lone CR ends a row, and drive the painters over it:
// a point on an ending sits after its row's last character (on the older grid: before the CR shown as a line feed), an
// empty CRLF row has no text node and takes its point in its text cell, a highlight or an insertion across an ending is one
// mark per row with no ending in any, and every point lands on the row the verified row map and rawOffsetToLine give its
// offset, so a point one row off from Reveal's row would show here (Slice 7's review, round 1).
test("Raw change marks over the CRLF fixture laid on the viewer's grid: sixteen rows with no ending in any, the same marks as over the older grid, every point on the row its offset's ending closes and where the row map puts it, an empty CRLF row taking its point in its text cell, the walks exact over the paint, unpaint restores the DOM", () => {
  const source = fixture("handlers-crlf.py");
  const { code, wrap } = buildRawViewer(source, "handlers-crlf.py");
  const rows = withClass(code, "fv-cl");
  assert.equal(rows.length, 16, "the lone CR ends a row of its own (the older grid: 15 rows)");
  assert.ok(allText(code, null).some((t) => (t.parentNode as FakeElement).getAttribute("class")?.startsWith("hljs-")), "highlight spans present");
  assert.ok(rows.every((r) => !/[\r\n]/.test(r.textContent)), "no row's text carries an ending");
  const mapped = rawRows(El(code), source) as unknown as FakeElement[] | null;
  sameNodes(mapped, rows, "the map's rows verify against the source and are the grid's, in order");
  const { changes, byId, longOld } = crlfChanges(source);
  const before = serialize(code);
  const textBefore = domText(code, isRow);
  assert.equal(textBefore, noEol(source), "the rows' text is the file's without its endings");
  const domIdx = rawDomIndexOfSplit(source);
  const g = (i: number) => { const x = domIdx(i); assert.ok(x !== null, "offset " + i + " shows a character"); return x as number; };
  const rowIndex = (n: FakeNode) => rows.indexOf(rowOf(n)!);
  // selections to compare across the paint: over the painted regions, across a mark's edge, whole lines, across the lone CR
  const probes: [number, number][] = [
    [byId["c-ins"].curFrom, byId["c-ins"].curTo],
    [byId["c-sub"].curFrom, byId["c-sub"].curTo],
    [source.indexOf("if note is None"), source.indexOf('"missing")') + '"missing")'.length],
    [0, source.indexOf("note_id):") + "note_id):".length],
    [source.indexOf("LIMIT"), source.length - 2],
    [byId["c-inscr"].curFrom + 5, byId["c-inscr"].curTo + 12],
    [source.indexOf("comment"), source.indexOf("and this text") + "and".length],
  ];
  const probe = (root: FakeElement, [i, j]: [number, number]) => mapRawSelection(sel(boundaries(root, g(i), isRow).text[0], boundaries(root, g(j - 1) + 1, isRow).text[0]), El(root), source);
  const pre = probes.map(([i, j]) => {
    const r = ok(probe(code, [i, j]));
    assert.deepEqual(r, { ok: true, range: { start: i, end: j }, quote: source.slice(i, j) }, `[${i},${j}) maps to its own offsets, the file's endings inside the quote`);
    return r;
  });
  assert.equal(pre[2].quote, 'if note is None:\r\n\t\treturn respond(404, "missing")', "across a CRLF, now a row boundary, the quote keeps it");
  assert.equal(pre[6].quote, "comment\rand", "across the lone CR, now a row boundary, the quote keeps the CR");

  const painted = paintChangesRaw(El(code), source, changes, stylesFor) as unknown as FakeElement[];
  assert.equal(domText(code, isRow), textBefore, "painting adds no text under any row");
  assert.deepEqual([...new Set(painted.map((m) => m.getAttribute("data-id")))].sort(), ["c-del", "c-del0", "c-delempty", "c-delend", "c-deleof", "c-ins", "c-inscr", "c-sub"], "every change got paint");
  assert.ok(painted.every((m) => !/[\r\n]/.test(m.textContent)), "no mark holds an ending: the rows have none");
  for (const m of painted) {
    const c = byId[m.getAttribute("data-id") as string];
    assert.ok(rowOf(m), "every mark sits inside a row");
    assert.equal(m.getAttribute("data-author"), c.author);
    if (m.getAttribute("class") !== "fc-del") continue;
    assert.equal(m.childNodes.length, 0, "a deletion point has no children");
    assert.equal(m.getAttribute("data-fc-text"), deletionLabel(c.oldText));
    assert.equal(rowTextBefore(code, m), noEol(source.slice(0, c.curFrom)), "point " + c.id + " sits exactly at its offset");
    assert.equal(rowOf(m), rawRowForOffset(El(code), source, c.curFrom), "point " + c.id + " is on the row the verified row map gives its offset");
    assert.equal(rowIndex(m), Math.min(rawOffsetToLine(source, c.curFrom), rows.length - 1), "point " + c.id + " is on the row rawOffsetToLine counts, the landing cue's");
  }
  const pointOf = (id: string) => painted.find((m) => m.getAttribute("class") === "fc-del" && m.getAttribute("data-id") === id)!;
  const marksOf = (id: string) => painted.filter((m) => m.getAttribute("class") === "fc-ins" && m.getAttribute("data-id") === id);
  assert.equal(rowOf(pointOf("c-del0")), rows[0]); assert.equal(rowTextBefore(code, pointOf("c-del0")), "", "the start of the file");
  assert.equal(rowOf(pointOf("c-delend")), rows[0], "an offset on a CRLF's CR is the end of its row");
  assert.equal(rowTextBefore(code, pointOf("c-delend")), "def get_note(store, note_id):", "after the row's last character (the older grid: before the CR shown as a line feed)");
  assert.equal(rowOf(pointOf("c-delempty")), rows[12], "the point on an empty row is inside that row");
  assert.equal((pointOf("c-delempty").parentNode as FakeElement).getAttribute("class"), "fv-ct", "an empty CRLF row has no text node on this grid, so the point goes into its text cell (the older grid: before its CR-as-LF)");
  assert.equal(rowOf(pointOf("c-deleof")), rows[15], "the end of the file is the last row's end");
  assert.equal(rowTextBefore(code, pointOf("c-deleof")), noEol(source));
  const label = pointOf("c-del").getAttribute("data-fc-text")!;
  assert.equal(label.length, DEL_LABEL_MAX);
  assert.equal(label.slice(0, -1), longOld.replace(/\r\n/g, "\n").slice(0, DEL_LABEL_MAX - 1), "the label shows the endings as the rows do, whatever grid the rows are on");
  // an insertion across a CRLF paints each row's slice, the ending in neither
  sameNodes([...new Set(marksOf("c-ins").map(rowOf))], [rows[1], rows[2]], "the insertion's marks sit in rows 1 and 2, in order");
  assert.equal(marksOf("c-ins").map((m) => m.textContent).join(""), noEol(byId["c-ins"].newText!));
  // the substitution across the two blank CRLF rows: those rows hold no text node, so no mark (the older grid gave each a "\n" mark)
  const subMarks = marksOf("c-sub");
  sameNodes([...new Set(subMarks.map(rowOf))], [rows[4], rows[7]], "the substitution's marks sit in rows 4 and 7, the blank rows between them unmarked");
  assert.equal(subMarks.map((m) => m.textContent).join(""), noEol(byId["c-sub"].newText!));
  assert.equal(nextSibling(pointOf("c-sub")), subMarks[0], "the substitution's point right before its first mark");
  // the lone-CR insertion: the CR ends a row on this grid, so the marks sit in two rows and the CR in neither (the older grid:
  // one row, the CR shown as a line break inside the mark)
  sameNodes([...new Set(marksOf("c-inscr").map(rowOf))], [rows[14], rows[15]], "the lone-CR insertion's marks sit in rows 14 and 15, in order");
  assert.equal(marksOf("c-inscr").map((m) => m.textContent).join(""), noEol(byId["c-inscr"].newText!));
  // the same marks as over the older grid, mark for mark: [id, class, text without endings], the older grid's marks that held
  // only a CR-as-LF set aside, since these rows have no such character to wrap: the substitution's slices of the two blank
  // rows, and the lone CR, which stands as its own text node there between the comment's span and the keyword's after it
  const key = (ms: FakeElement[]) => ms.map((m) => [m.getAttribute("data-id"), m.getAttribute("class"), noEol(m.textContent)]).filter(([, cls, t]) => cls !== "fc-ins" || t !== "");
  const older = buildRaw(source, "handlers-crlf.py");
  const olderPainted = paintChangesRaw(El(older.code), source, changes, stylesFor) as unknown as FakeElement[];
  assert.deepEqual(key(painted), key(olderPainted), "both grids paint the same marks, in the same order, over the same text");
  const onlyEndings = olderPainted.filter((m) => m.getAttribute("class") === "fc-ins" && noEol(m.textContent) === "");
  assert.equal(onlyEndings.length, olderPainted.length - painted.length, "the older grid's extra marks are exactly its ending-only slices");
  assert.deepEqual(onlyEndings.map((m) => [m.getAttribute("data-id"), m.textContent]), [["c-sub", "\n"], ["c-sub", "\n"], ["c-inscr", "\n"]], "the two blank rows' CR-as-LF and the lone CR's");
  // a comment highlight across the CRLF: marks in the two rows the range spans, the ending in none
  const hlRange: SourceRange = { start: byId["c-ins"].curFrom - 7, end: byId["c-ins"].curTo };
  const hl = paintRaw(El(wrap), source, hlRange, "fc-hl", { id: "k1" }) as unknown as FakeElement[];
  assert.equal(hl.map((m) => m.textContent).join(""), noEol(source.slice(hlRange.start, hlRange.end)));
  assert.equal(noEol(source.slice(hlRange.start, hlRange.end)), "note = store.get(note_id)\tif note is None");
  sameNodes([...new Set(hl.map(rowOf))], [rows[1], rows[2]], "the highlight's marks sit in the two rows the range spans");
  assert.equal(domText(code, isRow), textBefore);
  // every Raw walk over the painted DOM: a fresh analysis (root = the wrapper, never analyzed) and the cached one, text and
  // element boundaries
  for (let k = 0; k < probes.length; k++) {
    assert.deepEqual(ok(probe(wrap, probes[k])), pre[k], "fresh analysis, probe " + k);
    assert.deepEqual(ok(probe(code, probes[k])), pre[k], "cached analysis, probe " + k);
    const bs = boundaries(wrap, g(probes[k][0]), isRow), be = boundaries(wrap, g(probes[k][1] - 1) + 1, isRow);
    if (bs.elem.length && be.elem.length) assert.deepEqual(ok(mapRawSelection(sel(bs.elem[bs.elem.length - 1], be.elem[be.elem.length - 1]), El(wrap), source)), pre[k], "element boundaries, probe " + k);
  }
  // a selection that starts ON the deletion point maps to the file's offsets
  const j = byId["c-del"].curFrom + 'return respond(404, "missing")'.length;
  assert.deepEqual(ok(mapRawSelection(sel({ node: pointOf("c-del"), offset: 0 }, boundaries(wrap, g(j - 1) + 1, isRow).text[0]), El(wrap), source)), { ok: true, range: { start: byId["c-del"].curFrom, end: j }, quote: 'return respond(404, "missing")' });
  // unpaint: the change marks go, the highlight stays; with it unwrapped the way the panel unwraps it, the original bytes
  unpaintChanges(El(code));
  assert.equal(withClass(code, "fc-ins").length + withClass(code, "fc-del").length, 0);
  assert.equal(withClass(code, "fc-hl").map((m) => m.textContent).join(""), noEol(source.slice(hlRange.start, hlRange.end)), "the comment highlight is not ours to remove");
  unwrapAll(code, "fc-hl");
  assert.equal(serialize(code), before, "the change marks left nothing behind");
  const again = buildRawViewer(source, "handlers-crlf.py");
  assert.equal(paintChangesRaw(El(again.code), source, changes, stylesFor).length, painted.length, "a repaint on a fresh body paints the same marks");
  unpaintChanges(El(again.code));
  assert.equal(serialize(again.code), before, "byte-identical to the unpainted DOM");
});

test("paintRawPoint, paintRaw and paintChangesRaw over LF, CRLF, CR-only and mixed sources laid on the viewer's grid: a point on any ending sits after its row's last character, on an empty row in its text cell, at the end of the file after the last row's text, always on the row the row map and rawOffsetToLine give; a highlight across an ending is one mark per row with no ending in any; changes across endings paint the same marks whichever ending the file has; unpaint restores the DOM", () => {
  const VISIBLE = ["ab", "cd", "", "x", "yz"];
  let control: (string | number | null)[][] | null = null;   // the LF file's marks: the other three files must paint the same
  for (const [what, text] of [["LF", "ab\ncd\n\nx\nyz\n"], ["CRLF", "ab\r\ncd\r\n\r\nx\r\nyz\r\n"], ["CR-only", "ab\rcd\r\rx\ryz\r"], ["mixed", "ab\r\ncd\r\rx\nyz\r\n"]] as Array<[string, string]>) {
    const code = buildRawSplit(text);
    const rows = withClass(code, "fv-cl");
    assert.deepEqual(rows.map((r) => r.textContent), VISIBLE, what + ": the same five rows");
    const rowIndex = (n: FakeNode) => rows.indexOf(rowOf(n)!);
    const cdAt = text.indexOf("cd"), xAt = text.indexOf("x"), yzAt = text.indexOf("yz");
    const emptyAt = rawRowSpan(El(code), text, El(rows[2]))!.start;
    const before = serialize(code), textBefore = domText(code, isRow);
    // offset, what it is, the row it lies on, the rows' text before the point
    const spots: [number, string, number, string][] = [
      [0, "the start of the file", 0, ""],
      [2, "the ending after ab, its first character", 0, "ab"],
      [cdAt + 2, "the ending after cd", 1, "abcd"],
      [emptyAt, "the empty row", 2, "abcd"],
      [xAt + 1, "the ending after x", 3, "abcdx"],
      [yzAt, "the start of yz", 4, "abcdx"],
      [yzAt + 1, "inside yz", 4, "abcdxy"],
      [text.length, "the end of the file", 4, "abcdxyz"],
    ];
    if (text.startsWith("ab\r\n")) spots.push([3, "the LF of the CRLF after ab", 0, "ab"]);
    if (text.endsWith("\r\n")) spots.push([text.length - 1, "the LF of the file's last CRLF", 4, "abcdxyz"]);
    for (const [offset, meaning, row, textBeforePoint] of spots) {
      const p = paintRawPoint(El(code), text, offset, "fc-del", { act: "fcchange", id: "p" + offset, author: "web" }, "old") as unknown as FakeElement | null;
      assert.ok(p, `${what}: a point at ${offset} (${meaning}) is placed`);
      assert.equal(rowIndex(p!), row, `${what}: the point at ${offset} (${meaning}) is on row ${row}`);
      assert.equal(rowTextBefore(code, p!), textBeforePoint, `${what}: the rows' text before the point at ${offset} (${meaning})`);
      assert.equal(rowOf(p!), rawRowForOffset(El(code), text, offset), `${what}: the point at ${offset} is on the row the verified row map gives`);
      assert.equal(row, Math.min(rawOffsetToLine(text, offset), rows.length - 1), `${what}: and on the row rawOffsetToLine counts for ${offset}`);
      if (row === 2) assert.equal((p!.parentNode as FakeElement).getAttribute("class"), "fv-ct", what + ": an empty row takes the point in its text cell");
    }
    assert.equal(domText(code, isRow), textBefore, what + ": points add no text");
    unpaintChanges(El(code));
    assert.equal(serialize(code), before, what + ": unpaint restores the rows");
    // a highlight across an ending: one mark per row it spans, none over the empty row, no ending in any; each painted on
    // the restored rows and unwrapped the way the panel unwraps it, so the marks are the rows' slices and not a split's
    const marks = (range: SourceRange) => {
      const out = (paintRaw(El(code), text, range, "fc-hl") as unknown as FakeElement[]).map((m) => [m.textContent, rowIndex(m)]);
      assert.equal(domText(code, isRow), textBefore, what + ": a highlight adds no text");
      unwrapAll(code, "fc-hl");
      assert.equal(serialize(code), before, what + ": the highlight unwrapped leaves the rows as they were");
      return out;
    };
    assert.deepEqual(marks({ start: 1, end: cdAt + 1 }), [["b", 0], ["c", 1]], what + ": b and c, one mark per row");
    assert.deepEqual(marks({ start: 0, end: 3 }), [["ab", 0]], what + ": a range ending inside the ending paints the row's text alone");
    assert.deepEqual(marks({ start: 0, end: text.length }), [["ab", 0], ["cd", 1], ["x", 3], ["yz", 4]], what + ": the whole file, the empty row skipped");
    // changes: an insertion across the first ending, a deletion on the second, a substitution of x
    const changes = changesOf([op("c-ins", "web", 0, text.slice(0, cdAt + 2), ""), op("c-del", "api", cdAt + 2, "", "gone"), op("c-sub", "web", xAt, "x", "old")]);
    assert.deepEqual(changes.map((c) => c.kind), ["ins", "del", "sub"]);
    const painted = paintChangesRaw(El(code), text, changes, stylesFor) as unknown as FakeElement[];
    const shape = painted.map((m) => [m.getAttribute("data-id"), m.getAttribute("class"), m.textContent, rowIndex(m)]);
    assert.deepEqual(shape, [["c-ins", "fc-ins", "ab", 0], ["c-ins", "fc-ins", "cd", 1], ["c-del", "fc-del", "", 1], ["c-sub", "fc-del", "", 3], ["c-sub", "fc-ins", "x", 3]], what + ": the marks and their rows");
    if (control) assert.deepEqual(shape, control, what + ": the same marks as the LF file's"); else control = shape;
    assert.equal(rowTextBefore(code, painted[2]), "abcd", what + ": the deletion's point after cd");
    assert.equal(nextSibling(painted[3]), painted[4], what + ": the substitution's point right before its mark");
    assert.equal(domText(code, isRow), textBefore);
    unpaintChanges(El(code));
    assert.equal(serialize(code), before, what + ": unpaint restores the rows");
  }
});

test("Rendered change marks: ins and sub paint their new text with the author's styles, a del is a point at its place and a sub's point sits right before its tint, unpaint restores the DOM", () => {
  const source = fixture("report.md");
  const { box } = buildRendered(source);
  const before = serialize(box);
  const textBefore = stripWs(domText(box, null));
  const at = (s: string) => { const i = source.indexOf(s); assert.ok(i >= 0, s); return i; };
  const insNew = "cut p95 latency";
  const subNew = "the rendered notes for *five* minutes";
  const changes = changesOf([
    op("r-ins", "web", at(insNew), insNew, ""),
    op("r-sub", "api", at(subNew), subNew, "the notes for ten minutes"),
    op("r-del", "web", at("Second heading"), "", "An old heading\n\n"),
  ]);
  assert.deepEqual(Object.fromEntries(changes.map((c) => [c.id, c.kind])), { "r-ins": "ins", "r-sub": "sub", "r-del": "del" });
  // a selection over the passage before painting, for the comparison after
  const p = box.childNodes.filter((n) => n.nodeType === 1)[1] as FakeElement;
  const pp = nonWsPositions(p);
  const k0 = stripWs(p.textContent).indexOf("cutp95");
  const preSel = ok(mapRenderedSelection(sel({ node: pp[k0].t, offset: pp[k0].off }, { node: pp[k0 + 12].t, offset: pp[k0 + 12].off + 1 }), El(box), source));
  assert.equal(preSel.quote, insNew);
  // …and one over the heading the deletion's point will sit in front of
  const h2 = box.childNodes.filter((n) => n.nodeType === 1 && (n as FakeElement).tagName === "H2")[0] as FakeElement;
  const hp = nonWsPositions(h2);
  const preHead = ok(mapRenderedSelection(sel({ node: hp[0].t, offset: hp[0].off }, { node: hp[hp.length - 1].t, offset: hp[hp.length - 1].off + 1 }), El(box), source));
  assert.equal(preHead.quote, "Second heading");

  const res = paintChangesRendered(El(box), source, changes, stylesFor);
  assert.deepEqual(res, { painted: ["r-ins", "r-del", "r-sub"], unpainted: [] }, "the deletion is painted too (the inline-display follow-on); ids in the hunks' order");
  assert.equal(stripWs(domText(box, null)), textBefore, "painting keeps the rendered text");
  const marks = withClass(box, "fc-ins");
  assert.ok(marks.length >= 2);
  const byId = Object.fromEntries(changes.map((c) => [c.id, c]));
  for (const m of marks) {
    assert.equal(m.tagName, "MARK");
    assert.equal(m.getAttribute("data-act"), "fcchange");
    const c = byId[m.getAttribute("data-id") as string];
    assert.ok(c && c.kind !== "del");
    assert.equal(m.getAttribute("data-author"), c.author);
    assert.equal(m.getAttribute("style"), "--fc-author: " + COLORS[c.author] + ";");
  }
  const textOfId = (id: string) => stripWs(marks.filter((m) => m.getAttribute("data-id") === id).map((m) => m.textContent).join(""));
  assert.equal(textOfId("r-ins"), stripWs(insNew));
  assert.equal(textOfId("r-sub"), "therenderednotesforfiveminutes", "the emphasis marks the renderer consumed are not text");
  // the points: the Raw view's element, byte for byte — a span, the change's data, the capped label in data-fc-text,
  // the author's styles, no text node, no chip (the plan gives the chip to Raw)
  const points = withClass(box, "fc-del");
  assert.deepEqual(points.map((x) => x.getAttribute("data-id")), ["r-del", "r-sub"], "one point per deletion and substitution, in document order");
  for (const x of points) {
    const c = byId[x.getAttribute("data-id") as string];
    assert.equal(x.tagName, "SPAN");
    assert.equal(x.getAttribute("class"), "fc-del");
    assert.equal(x.getAttribute("data-act"), "fcchange");
    assert.equal(x.getAttribute("data-author"), c.author);
    assert.equal(x.getAttribute("data-fc-text"), deletionLabel(c.oldText));
    assert.equal(x.getAttribute("style"), "--fc-author: " + COLORS[c.author] + ";");
    assert.equal(x.getAttribute("data-fc-chip"), null, "Rendered marks carry no chip");
    assert.equal(x.childNodes.length, 0, "a point adds no text node");
  }
  // the deletion's point sits in the setext heading, before its first character: the old heading struck, then the new
  const del = points[0];
  assert.equal(blockOf(box, del), h2);
  assert.deepEqual(around(h2, del), ["", "Second heading"]);
  assert.equal(del.getAttribute("data-fc-text"), "An old heading\n\n", "the label keeps its line endings (the sheet folds them in prose)");
  // the substitution's point is the node right before the first of its marks, in the same parent
  const sub = points[1];
  const subMarks = marks.filter((m) => m.getAttribute("data-id") === "r-sub");
  assert.equal(nextSibling(sub), subMarks[0], "struck old text, then the tinted new text");
  assert.equal(sub.getAttribute("data-fc-text"), "the notes for ten minutes");
  // the selection maps the same over the painted DOM: from inside the mark, and over the heading with the point in it
  const insMark = marks.find((m) => m.getAttribute("data-id") === "r-ins")!;
  const inner = insMark.childNodes[0] as FakeText;
  const post = ok(mapRenderedSelection(sel({ node: inner, offset: 0 }, { node: inner, offset: inner.data.length }), El(box), source));
  assert.deepEqual(post, preSel);
  const hp2 = nonWsPositions(h2);
  const postHead = ok(mapRenderedSelection(sel({ node: hp2[0].t, offset: hp2[0].off }, { node: hp2[hp2.length - 1].t, offset: hp2[hp2.length - 1].off + 1 }), El(box), source));
  assert.deepEqual(postHead, preHead, "the point adds no text, so the walk over the heading is unchanged");
  // a selection that begins at the element boundary the point occupies (the browser reports a spot two ways)
  const atPoint = ok(mapRenderedSelection(sel({ node: h2, offset: h2.childNodes.indexOf(del) + 1 }, { node: hp2[hp2.length - 1].t, offset: hp2[hp2.length - 1].off + 1 }), El(box), source));
  assert.deepEqual(atPoint, preHead);
  unpaintChanges(El(box));
  assert.equal(serialize(box), before);
});

test("Rendered deletion points: before the word the offset is on, against the word a deletion followed, at a paragraph's end, at the end of the file, in a list item and a blockquote, with the label capped; a selection across a point maps as before; unpaint restores the DOM", () => {
  const source = fixture("report.md");
  const { box } = buildRendered(source);
  const before = serialize(box);
  const at = (s: string) => { const i = source.indexOf(s); assert.ok(i >= 0, s); return i; };
  const longOld = "the p50 and the p75 and the p90 and the p95 and the p99 and every other percentile we once reported here";
  assert.ok(longOld.length > DEL_LABEL_MAX);
  const del = (id: string, curFrom: number, oldText: string, author = "web"): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText, author });
  const changes = [
    del("d-on", at("p95 latency"), "median "),                                   // on a word: before it
    del("d-after", at("endpoint.") + "endpoint".length, " today"),               // right after a word, before its period: against the word
    del("d-space", at(" on the notes endpoint"), longOld),                        // right after "40%", on the space: against "40%", not past the space
    del("d-end", at("Key points:") + "Key points:".length, " Three of them."),   // a paragraph's end
    del("d-item", at("legacy~~ v1 route.") + "legacy~~ v1 route.".length, " Keep v2.", "api"),   // a list item's end
    del("d-quote", at("Quoted second line."), "Quoted first line.\n> ", "api"),  // inside a blockquote, on a word
    del("d-defs", source.length, "\nOne more line.\n"),                           // after the reference definitions, which render nothing
  ];
  const res = paintChangesRendered(El(box), source, changes, stylesFor);
  assert.deepEqual(res, { painted: changes.slice(0, -1).map((c) => c.id), unpainted: ["d-defs"] }, "no rendered text stands where the definitions are: card-only");
  const point = (id: string) => { const x = withClass(box, "fc-del").find((m) => m.getAttribute("data-id") === id); assert.ok(x, id + " painted"); return x!; };
  const where = (id: string) => { const x = point(id); return around(blockOf(box, x), x); };
  let [pre, post] = where("d-on");
  assert.ok(pre.endsWith("session cut ") && post.startsWith("p95 latency"), "before the word: " + JSON.stringify([pre.slice(-12), post.slice(0, 12)]));
  [pre, post] = where("d-after");
  assert.ok(pre.endsWith("notes endpoint") && post.startsWith(". See the"), "against the word, before the period: " + JSON.stringify([pre.slice(-14), post.slice(0, 10)]));
  [pre, post] = where("d-space");
  assert.ok(pre.endsWith("by 40%") && post.startsWith(" on the notes"), "a deletion that followed a word directly sits against it, the space after: " + JSON.stringify([pre.slice(-6), post.slice(0, 13)]));
  assert.equal(point("d-space").getAttribute("data-fc-text"), deletionLabel(longOld));
  assert.equal(point("d-space").getAttribute("data-fc-text")!.length, DEL_LABEL_MAX, "capped like Raw's, with the ellipsis");
  [pre, post] = where("d-end");
  assert.equal(pre, "Key points:"); assert.equal(post, "");
  [pre, post] = where("d-item");
  assert.ok(pre.endsWith("v1 route.") && post.trimStart().startsWith("Nested: keep"), "at the item's own text's end, before its nested list: " + JSON.stringify([pre.slice(-9), post.slice(0, 12)]));
  assert.equal(blockOf(box, point("d-item")).tagName, "UL");
  [pre, post] = where("d-quote");
  assert.ok(pre.endsWith("more week.\n") && post.startsWith("Quoted second line."), JSON.stringify([pre.slice(-11), post.slice(0, 19)]));
  assert.equal(blockOf(box, point("d-quote")).tagName, "BLOCKQUOTE");
  // the walks are unaffected: a selection from before a point to after it maps to the same source range as with no point
  const para = blockOf(box, point("d-on"));
  const pp = nonWsPositions(para);
  const i0 = stripWs(para.textContent).indexOf("cutp95latency");
  const selNow = ok(mapRenderedSelection(sel({ node: pp[i0].t, offset: pp[i0].off }, { node: pp[i0 + 12].t, offset: pp[i0 + 12].off + 1 }), El(box), source));
  assert.equal(selNow.quote, "cut p95 latency");
  unpaintChanges(El(box));
  assert.equal(serialize(box), before);
  const fresh = buildRendered(source);
  const fp = nonWsPositions(fresh.box.childNodes.filter((n) => n.nodeType === 1)[1] as FakeElement);
  const selClean = ok(mapRenderedSelection(sel({ node: fp[i0].t, offset: fp[i0].off }, { node: fp[i0 + 12].t, offset: fp[i0 + 12].off + 1 }), El(fresh.box), source));
  assert.deepEqual(selNow, selClean);
  // the end of a file whose last block ends it: after the last character; with a trailing blank line, nothing stands there
  for (const [src, tail] of [["Alpha.\n\nOmega.\n", ""], ["Alpha.\n\nOmega.", ""], ["Alpha.\n\nOmega.\n\n", null]] as const) {
    const small = buildRendered(src);
    const r = paintChangesRendered(El(small.box), src, [del("e", src.length, "\nOne more line.")], stylesFor);
    if (tail === null) { assert.deepEqual(r, { painted: [], unpainted: ["e"] }, JSON.stringify(src) + ": a blank line ends the file"); continue; }
    assert.deepEqual(r, { painted: ["e"], unpainted: [] }, JSON.stringify(src));
    const x = withClass(small.box, "fc-del")[0];
    assert.deepEqual(around(blockOf(small.box, x), x), ["Omega.", tail], JSON.stringify(src));
  }
});

test("Rendered deletion points that cannot be placed stay unpainted, never beside the wrong words: an HTML block, a blank line between blocks; a code fence's line and a table's cell place their points since Slice 8 (before: unpainted, both holes), a nested code block's line too; either side of a nested block is placed", () => {
  const source = fixture("refusals.md");
  const { box } = buildRendered(source);
  const before = serialize(box);
  const at = (s: string) => { const i = source.indexOf(s); assert.ok(i >= 0, s); return i; };
  const del = (id: string, curFrom: number): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText: "gone", author: "web" });
  const res = paintChangesRendered(El(box), source, [
    del("u-code", at("respond(request)")),
    del("u-table", at("120 ms")),
    del("u-html", at("An HTML block")),
    del("u-blank", at("\n\n```python") + 1),                       // the blank line between the paragraph and the fence
    del("p-prose", at("An aligned paragraph after everything.")),   // the control: a mapped paragraph
  ], stylesFor);
  // a table's cell and a fence's line place their points since Slice 8 (before: unpainted, both holes); the html block and the blank line stay unplaced
  assert.deepEqual(res, { painted: ["u-code", "u-table", "p-prose"], unpainted: ["u-html", "u-blank"] });
  assert.equal(withClass(box, "fc-del").length, 3);
  const inCode = withClass(box, "fc-del").find((m) => m.getAttribute("data-id") === "u-code")!;
  let up: FakeNode | null = inCode, inPre = false;
  while (up) { if (up.nodeType === 1 && (up as FakeElement).tagName === "PRE") inPre = true; up = up.parentNode; }
  assert.ok(inPre, "the fence's point stands inside the code");
  const [cpre, cpost] = around(blockOf(box, inCode), inCode);
  assert.ok(cpre.endsWith("return ") && cpost.startsWith("respond(request)"), "right before the deleted call, on its line: " + JSON.stringify([cpre.slice(-12), cpost.slice(0, 16)]));
  const inCell = withClass(box, "fc-del").find((m) => m.getAttribute("data-id") === "u-table")!;
  assert.equal((inCell.parentNode as FakeElement).tagName, "TD", "the table's point stands inside the changed cell");
  assert.equal((inCell.parentNode as FakeElement).textContent, "120 ms");
  unpaintChanges(El(box));
  assert.equal(serialize(box), before);
  // a list item holding a nested code block: since Slice 8 the code's lines are positioned inside the item's block, so a deletion
  // inside a line places in the code (before: the block was a hole and the point was unpainted); one at the end of the text
  // before it sits against that text; one at the start of the text after it sits before that text
  const nested = "- Item one\n\n  ```\n  code line\n  ```\n\n  after code\n";
  const { box: nb } = buildRendered(nested);
  const nbefore = serialize(nb);
  const r2 = paintChangesRendered(El(nb), nested, [
    del("n-in", nested.indexOf("code line")),
    del("n-before", nested.indexOf("Item one") + "Item one".length),
    del("n-after", nested.indexOf("after code")),
  ], stylesFor);
  assert.deepEqual(r2, { painted: ["n-in", "n-before", "n-after"], unpainted: [] });
  const pt = (id: string) => withClass(nb, "fc-del").find((m) => m.getAttribute("data-id") === id)!;
  let np: FakeNode | null = pt("n-in"), nInPre = false;
  while (np) { if (np.nodeType === 1 && (np as FakeElement).tagName === "PRE") nInPre = true; np = np.parentNode; }
  assert.ok(nInPre, "the nested code's point stands inside its pre");
  assert.ok(around(blockOf(nb, pt("n-in")), pt("n-in"))[1].startsWith("code line"), "before the line's first character");
  let [pre, post] = around(blockOf(nb, pt("n-before")), pt("n-before"));
  assert.ok(pre.endsWith("Item one") && !post.startsWith("Item"), JSON.stringify([pre, post.slice(0, 10)]));
  [pre, post] = around(blockOf(nb, pt("n-after")), pt("n-after"));
  assert.ok(post.startsWith("after code") && pre.includes("code line"), JSON.stringify([pre.slice(-10), post]));
  unpaintChanges(El(nb));
  assert.equal(serialize(nb), nbefore);
});

test("Rendered change marks: an insertion inside a code fence paints by position, on its line (Slice 8; before: through the text-match fallback); a substitution over the table's delimiter row, whose text is not on the page, does not", () => {
  const source = fixture("refusals.md");
  const { box } = buildRendered(source);
  const before = serialize(box);
  const q = "respond(request)";
  const i = source.indexOf(q);
  // the table's delimiter row is in the file but renders no text and no cell's characters lie in it: nothing on the page to paint
  const sep = "|-------|-----|";
  const j = source.indexOf(sep);
  assert.ok(j >= 0);
  const res = paintChangesRendered(El(box), source, [
    { id: "f-code", kind: "ins", curFrom: i, curTo: i + q.length, oldText: "", author: "web", newText: q },
    { id: "f-sep", kind: "sub", curFrom: j, curTo: j + sep.length, oldText: "|---|---|", author: "web", newText: sep },
  ], stylesFor);
  assert.deepEqual(res, { painted: ["f-code"], unpainted: ["f-sep"] });
  const marks = withClass(box, "fc-ins");
  assert.equal(stripWs(marks.map((m) => m.textContent).join("")), stripWs(q));
  let n: FakeNode | null = marks[0]; let inPre = false;
  while (n) { if (n.nodeType === 1 && (n as FakeElement).tagName === "PRE") inPre = true; n = n.parentNode; }
  assert.ok(inPre);
  unpaintChanges(El(box));
  assert.equal(serialize(box), before);
});

test("change marks: offsets that do not index the viewer's text are left to the card, never painted at the wrong place", () => {
  const source = fixture("handlers-crlf.py");
  const { code } = buildRaw(source, "handlers-crlf.py");
  const before = serialize(code);
  // the same hunks computed over a string with one more leading character (a BOM the fetch stripped): every
  // offset is one too far, and the new text says so
  const shifted = "﻿" + source;
  const { changes } = crlfChanges(shifted);
  assert.ok(changes.some((c) => c.kind === "del" && c.curTo <= source.length), "the shifted deletions are in bounds and carry no text to check on their own");
  const painted = paintChangesRaw(El(code), source, changes, stylesFor);
  assert.deepEqual(painted, [], "one failed check refuses the batch: nothing painted one character off, deletions included");
  assert.equal(serialize(code), before);
  // without a newText to check against, an ins paints by offset as asked
  const blind = paintChangesRaw(El(code), source, [{ id: "b1", kind: "ins", curFrom: 4, curTo: 12, oldText: "", author: "web" }], stylesFor) as unknown as FakeElement[];
  assert.deepEqual(blind.map((m) => m.getAttribute("data-id")), ["b1"]);
  assert.equal(blind[0].textContent, "get_note");
  unpaintChanges(El(code));
  assert.equal(serialize(code), before);
  // a del past the text, or a del given a width, is an offset that indexes nothing: it fails its batch too
  const sound = { id: "b1", kind: "ins" as const, curFrom: 4, curTo: 12, oldText: "", author: "web", newText: "get_note" };
  assert.deepEqual(paintChangesRaw(El(code), source, [sound, { id: "b2", kind: "del", curFrom: source.length + 1, curTo: source.length + 1, oldText: "x", author: "web" }], stylesFor), []);
  assert.deepEqual(paintChangesRaw(El(code), source, [sound, { id: "b3", kind: "del", curFrom: 4, curTo: 8, oldText: "x", author: "web" }], stylesFor), []);
  assert.equal(serialize(code), before);
  // Rendered: the same verdicts
  const md = fixture("report.md");
  const { box } = buildRendered(md);
  const m1: ChangePaint = { id: "m1", kind: "ins", curFrom: 2, curTo: 9, oldText: "", author: "web", newText: "Latency" };
  const m2: ChangePaint = { id: "m2", kind: "ins", curFrom: 3, curTo: 10, oldText: "", author: "web", newText: "Latency" };
  const m3: ChangePaint = { id: "m3", kind: "sub", curFrom: 5, curTo: 5, oldText: "x", author: "web" };
  assert.deepEqual(paintChangesRendered(El(box), md, [m1, m2], stylesFor), { painted: [], unpainted: ["m1", "m2"] }, "the batch fails on m2");
  assert.deepEqual(paintChangesRendered(El(box), md, [m1, m3], stylesFor), { painted: ["m1"], unpainted: ["m3"] }, "m3 is in bounds; it has no new text to paint");
  assert.equal(withClass(box, "fc-ins").map((m) => m.textContent).join(""), "Latency");
});

test("deletionLabel and the inline styles: the cap, the ellipsis, line endings as the rows show them, a surrogate pair kept whole; a style value that could end the declaration is dropped", () => {
  assert.equal(deletionLabel("reduced"), "reduced");
  assert.equal(deletionLabel("a\r\nb\rc\nd"), "a\nb\nc\nd");
  // a label with no visible character would draw nothing (the sheet's ::before is handed line feeds): one ¶ per
  // ending, so a removed blank line has a struck glyph on its own row; spaces and tabs have width and stay; a label
  // with any visible character keeps its endings
  assert.equal(deletionLabel("\n"), PILCROW, "one removed line ending");
  assert.equal(deletionLabel("\n\n"), PILCROW + PILCROW, "a removed blank line: the two endings around it");
  assert.equal(deletionLabel("\r\n\r\n"), PILCROW + PILCROW, "CRLF endings, one glyph each");
  assert.equal(deletionLabel(" \n\t"), " " + PILCROW + "\t", "spaces and tabs keep their own width");
  assert.equal(deletionLabel("  "), "  ", "spaces alone are visible as they are");
  assert.equal(deletionLabel("ends.\n\nPara"), "ends.\n\nPara", "a visible character: the endings stay, as the rows show them");
  assert.equal(deletionLabel("\n".repeat(100)), PILCROW.repeat(79) + "…", "the cap applies to the glyphs");
  assert.equal(deletionLabel("x".repeat(80)), "x".repeat(80));
  const long = deletionLabel("y".repeat(81));
  assert.equal(long.length, 80);
  assert.equal(long, "y".repeat(79) + "…");
  const pair = deletionLabel("z".repeat(78) + "\u{1F600}" + "tail");   // the pair would straddle the cut
  assert.equal(pair, "z".repeat(78) + "…");
  assert.ok(!/[\uD800-\uDBFF]$/.test(pair.slice(0, -1)), "no dangling high surrogate");
  const source = "alpha beta\n";
  const { code } = buildRaw(source, "notes.txt");
  const marks = paintChangesRaw(El(code), source, [
    { id: "s1", kind: "ins", curFrom: 0, curTo: 5, oldText: "", author: "web", newText: "alpha" },
    { id: "s2", kind: "ins", curFrom: 6, curTo: 10, oldText: "", author: "api", newText: "beta" },
  ], (c): Record<string, string> => (c.id === "s1" ? { "--fc-author": "red; background: url(x)", color: "rgb(1, 2, 3)" } : { "not a name!": "red", "--fc-author": "#abc" })) as unknown as FakeElement[];
  assert.equal(marks[0].getAttribute("style"), "color: rgb(1, 2, 3);", "the unsafe value is dropped, the sound one kept");
  assert.equal(marks[1].getAttribute("style"), "--fc-author: #abc;");
  // painted: a removed blank line (the sidecar records `del` with oldText "\n\n" for track-edit --old $'\n\n' --new '')
  // is a point whose label the sheet can draw, on the row the offset falls in, with no text node added
  const two = "one\ntwo\n";
  const built = buildRaw(two, "notes.txt");
  const before = allText(built.code, null).length;
  const [p] = paintChangesRaw(El(built.code), two, [{ id: "d0", kind: "del", curFrom: 4, curTo: 4, oldText: "\n\n", author: "web", newText: "" }], () => ({})) as unknown as FakeElement[];
  assert.ok(p, "the point is painted");
  assert.equal(p.getAttribute("data-fc-text"), PILCROW + PILCROW, "the label is two glyphs, not two line feeds");
  assert.equal(allText(built.code, null).length, before, "no text node entered a row");
});

test("unpaintChanges walks elements only: a text node's children are never read (the panel tests' stand-in gives a Text none)", () => {
  const source = fixture("handlers-crlf.py");
  const { code } = buildRaw(source, "handlers-crlf.py");
  const { changes } = crlfChanges(source);
  const before = serialize(code);
  const painted = paintChangesRaw(El(code), source, changes, stylesFor);
  assert.ok(painted.length > 0);
  // after painting, every text node under the body loses its childNodes, as a Text in a DOM stand-in may never have had one
  const strip = (n: FakeNode) => {
    if (n.nodeType === 3) { (n as unknown as { childNodes: unknown }).childNodes = undefined; return; }
    for (const c of n.childNodes) strip(c);
  };
  strip(code);
  unpaintChanges(El(code));
  assert.equal(serialize(code), before, "every mark unwrapped, the text joined back, nothing thrown");
  assert.ok(!/fc-(ins|del)/.test(serialize(code)));
});

// ── the stand-in's nodes inspect as their own projection (ui/test-dom-shim.ts) ────────────────────
test("a stand-in node enumerates its primitives alone, and a dump of one names neither parentNode nor childNodes", () => {
  const doc = new FakeDocument();
  const root = doc.createElement("div"), p = doc.createElement("p"), t = doc.createTextNode("alpha");
  root.appendChild(p); p.appendChild(t); p.setAttribute("class", "row");
  for (const n of [root, p, t]) {
    for (const k of Object.keys(n)) assert.ok(staysEnumerable((n as any)[k]), k + " is enumerable and holds a " + typeof (n as any)[k]);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "a dump stays on the node: " + dump);
  }
  assert.ok(p.parentNode === root && root.childNodes[0] === p && t.parentNode === p, "the edges still hold the tree");
  assert.equal(root.textContent, "alpha"); assert.equal(p.getAttribute("class"), "row");
});
