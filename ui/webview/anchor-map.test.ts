// anchor-map.ts driven behaviorally over the viewer's two DOM shapes, rebuilt here exactly as
// file-view.ts builds them (its Raw rows and marked configuration are replicated and pinned to the
// source, the repo's convention) and parsed into a small DOM stand-in — there is no jsdom in this tree.
// DOMPurify is not applied: it needs a window, and it never alters text nodes, which is all the mapping
// reads. Fixtures are synthetic (a notes-api world) and live in anchor-map-fixtures/.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import xml from "highlight.js/lib/languages/xml";
import cssLang from "highlight.js/lib/languages/css";
import markdown from "highlight.js/lib/languages/markdown";
import { marked } from "marked";
import {
  mapRawSelection, mapRenderedSelection, makeAnchor, locateComment, paintRaw, paintRendered,
  rawOffsetToLine, rawRowForOffset, type SelLike, type MapResult, type SourceRange,
} from "./anchor-map";
// @ts-ignore -- untyped CommonJS module (see anchor-map.ts)
import engine from "../../vendor/track-changents/engine.js";

const FIX = (f: string) => path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map-fixtures", f);
const fixture = (f: string) => fs.readFileSync(FIX(f), "utf8");
const VIEW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8");

// ── the viewer's marked configuration (file-view.ts) ──────────────────────────────────────────────
marked.setOptions({ gfm: true, breaks: false });
marked.use({
  tokenizer: {
    del(src: string) {
      const m = /^~~(?=\S)([\s\S]*?\S)~~/.exec(src);
      if (!m) return undefined;
      return { type: "del", raw: m[0], text: m[1], tokens: (this as { lexer: { inlineTokens(s: string): unknown[] } }).lexer.inlineTokens(m[1]) };
    },
  },
} as Parameters<typeof marked.use>[0]);
for (const [name, lang] of Object.entries({ python, py: python, xml, html: xml, css: cssLang, markdown, md: markdown })) {
  try { hljs.registerLanguage(name, lang as any); } catch { /* dup */ }
}

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser ─────
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
// replica of file-view.ts wrapNumberedHtml (pinned below)
function wrapNumberedHtml(html: string): string {
  const lines = html.split("\n");
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
type RawDom = { body: FakeElement; before: FakeElement; after: FakeElement; wrap: FakeElement; code: FakeElement };
/** `.fileview-body > div.fileview-code > pre > code.hljs > rows`, with a sibling before and after. */
function buildRaw(text: string, filePath: string): RawDom {
  const doc = new FakeDocument();
  const lang = langFor(filePath);
  let hl: string | null = null;
  if (lang) hl = hljs.highlight(text, { language: lang }).value;
  const body = doc.createElement("div"); body.setAttribute("class", "fileview-body");
  const before = doc.createElement("div"); before.setAttribute("class", "fileview-actions"); before.appendChild(doc.createTextNode("Rendered · Raw"));
  const wrap = doc.createElement("div"); wrap.setAttribute("class", "fileview-code");
  const pre = doc.createElement("pre"); pre.setAttribute("class", "fileview-pre fileview-wrap");
  const code = doc.createElement("code"); code.setAttribute("class", "hljs");
  for (const n of parseHTML(doc, wrapNumberedHtml(hl !== null ? hl : escapeHtml(text)))) code.appendChild(n);
  pre.appendChild(code); wrap.appendChild(pre);
  const after = doc.createElement("div"); after.setAttribute("class", "fileview-footer"); after.appendChild(doc.createTextNode("footer text"));
  body.appendChild(before); body.appendChild(wrap); body.appendChild(after);
  return { body, before, after, wrap, code };
}
type MdDom = { body: FakeElement; box: FakeElement; before: FakeElement };
/** `.fileview-body > div.fileview-md > marked output` (mdBlock without DOMPurify, see the header). */
function buildRendered(text: string): MdDom {
  const doc = new FakeDocument();
  const body = doc.createElement("div");
  const before = doc.createElement("div"); before.appendChild(doc.createTextNode("Rendered · Raw"));
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);
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

// ── source pins: the DOM shapes this test rebuilds are the viewer's ──────────────────────────────
test("pins: the viewer's Raw rows, marked configuration, and lexer identity", () => {
  assert.match(VIEW, /return `<span class="fv-cl"><span class="fv-ct">\$\{prefix\}\$\{ln\}\$\{suffix\}<\/span><\/span>`;/);
  assert.match(VIEW, /const lines = html\.split\("\\n"\);\n\s+if \(lines\.length && lines\[lines\.length - 1\] === ""\) lines\.pop\(\);/);
  assert.match(VIEW, /marked\.setOptions\(\{ gfm: true, breaks: false \}\);/);
  assert.match(VIEW, /const m = \/\^~~\(\?=\\S\)\(\[\\s\\S\]\*\?\\S\)~~\/\.exec\(src\);/);
  assert.match(VIEW, /const dirty = marked\.parse\(text\) as string;/);
  const MAP = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map.ts"), "utf8");
  assert.match(MAP, /Lexer\.lex\(N\)/, "the walk lexes with the viewer's configured singleton (no private options)");
  assert.doesNotMatch(MAP, /marked\.(setOptions|use)\(/, "anchor-map never reconfigures marked");
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

test("Raw: a quote that occurs twice anchors to the selected occurrence, also after two lines are inserted above", () => {
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
  // the session inserted two lines above the passage between the selection and Enter
  const inserted = "# reviewed\r\n# twice\r\n";
  const edited = source.slice(0, source.indexOf("def put_note")) + inserted + source.slice(source.indexOf("def put_note"));
  const loc = locateComment(edited, anchor, r.range.start);
  assert.equal(loc.state, "located");
  assert.equal(loc.range!.start, second + inserted.length);
  assert.equal(edited.slice(loc.range!.start, loc.range!.end), needle);
});

test("rawOffsetToLine counts the Raw view's rows", () => {
  const src = "a\r\nb\r\n\r\nc";
  assert.equal(rawOffsetToLine(src, 0), 0);
  assert.equal(rawOffsetToLine(src, 3), 1);
  assert.equal(rawOffsetToLine(src, 7), 2, "the LF that ends line 3 still lies on it");
  assert.equal(rawOffsetToLine(src, 8), 3);
  assert.equal(rawOffsetToLine(src, 99), 3);
  assert.equal(rawOffsetToLine("x\ry", 2), 0, "a lone CR stays inside its row, as the viewer's split has it");
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
test("Rendered refusals: code, table, HTML block, entity prose, escaped link label, tab after a marker — each refuses with the note-preserving fields", () => {
  const source = fixture("refusals.md");
  const { box } = buildRendered(source);
  const els = box.childNodes.filter((n) => n.nodeType === 1) as FakeElement[];
  const byTag = (tag: string, n = 0) => els.filter((e) => e.tagName === tag)[n];
  const inside = (e: FakeElement, from: number, to: number) => { const p = nonWsPositions(e); return sel({ node: p[from].t, offset: p[from].off }, { node: p[to - 1].t, offset: p[to - 1].off + 1 }); };
  const lineOf = (needle: string) => source.slice(0, source.indexOf(needle)).split("\n").length - 1;
  // fenced code (its tab was expanded to spaces by the renderer; the Raw offer still finds it through the map)
  const pre = byTag("PRE", 0);
  let r = bad(mapRenderedSelection(inside(pre, 0, 20), El(box), source));   // "def handler(request):" has 20 non-whitespace characters
  assert.match(r.reason, /code block/);
  assert.equal(r.blockStartLine, lineOf("```python"));
  assert.equal(r.blockStartOffset, source.indexOf("```python"));
  assert.equal(r.rawHasQuote, true);
  assert.equal(source.slice(r.rawRange!.start, r.rawRange!.end), "def handler(request):");
  r = bad(mapRenderedSelection(inside(pre, 20, 26), El(box), source));          // "return" — after the tab
  assert.equal(r.rawHasQuote, true);
  assert.equal(source.slice(r.rawRange!.start, r.rawRange!.end), "return");
  // indented code
  r = bad(mapRenderedSelection(inside(byTag("PRE", 1), 0, 3), El(box), source));
  assert.match(r.reason, /indented code/);
  assert.equal(r.blockStartLine, lineOf("    indented"));
  // table
  r = bad(mapRenderedSelection(inside(byTag("TABLE"), 0, 2), El(box), source));
  assert.match(r.reason, /table/);
  assert.equal(r.blockStartLine, lineOf("| Route |"));
  assert.equal(r.rawHasQuote, true, "the cell text occurs in the source");
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
  // blockquote line beginning with a tab after the marker (the lexer turned it into code)
  r = bad(mapRenderedSelection(inside(byTag("BLOCKQUOTE"), 0, 4), El(box), source));
  assert.match(r.reason, /code block|tab/);
  assert.equal(r.blockStartLine, lineOf("> \tquoted"));
  // the aligned paragraphs around them still map, before and after every refused block (alignment resynced)
  const before = ps.find((p) => p.textContent.startsWith("An aligned paragraph before"))!;
  assert.equal(ok(mapRenderedSelection(inside(before, 0, 9), El(box), source)).quote, "An aligned");
  const after = ps.find((p) => p.textContent.startsWith("An aligned paragraph after"))!;
  assert.equal(ok(mapRenderedSelection(inside(after, 2, 9), El(box), source)).quote, "aligned");
  assert.equal(ok(mapRenderedSelection(inside(after, 0, 34), El(box), source)).quote, "An aligned paragraph after everything.");
  // a selection reaching from an aligned paragraph into a refused block refuses with the block's line
  const bp = nonWsPositions(before), cp = nonWsPositions(pre);
  r = bad(mapRenderedSelection(sel({ node: bp[0].t, offset: bp[0].off }, { node: cp[3].t, offset: cp[3].off + 1 }), El(box), source));
  assert.match(r.reason, /code block/);
  assert.equal(r.blockStartLine, lineOf("```python"));
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

// ── Rendered: holes, html resync, inline html, autolinks, cache validity ───────────────────────────
const firstEl = (root: FakeNode, tag: string, n = 0): FakeElement => {
  const found: FakeElement[] = [];
  const visit = (x: FakeNode) => { if (x.nodeType === 1 && (x as FakeElement).tagName === tag) found.push(x as FakeElement); x.childNodes.forEach(visit); };
  visit(root); return found[n];
};
const wholeOf = (e: FakeElement) => { const p = nonWsPositions(e); return sel({ node: p[0].t, offset: p[0].off }, { node: p[p.length - 1].t, offset: p[p.length - 1].off + 1 }); };
const partOf = (e: FakeElement, from: number, to: number) => { const p = nonWsPositions(e); return sel({ node: p[from].t, offset: p[from].off }, { node: p[to - 1].t, offset: p[to - 1].off + 1 }); };

test("Rendered: code and tables nested in list items are holes — the other items still map, the hole refuses with its own line", () => {
  const source = [
    "- Install it:", "", "  ```sh", "  npm install notes-api", "  ```", "", "- Then run the server.", "", "- A table:", "",
    "  | a | b |", "  |---|---|", "  | 1 | 2 |", "", "- After the table.", "",
  ].join("\n");
  const { box } = buildRendered(source);
  const ul = firstEl(box, "UL");
  assert.equal(ok(mapRenderedSelection(wholeOf(firstEl(ul, "LI", 1)), El(box), source)).quote, "Then run the server.");
  assert.equal(ok(mapRenderedSelection(wholeOf(firstEl(ul, "LI", 3)), El(box), source)).quote, "After the table.");
  assert.equal(ok(mapRenderedSelection(partOf(firstEl(ul, "LI", 0), 0, 7), El(box), source)).quote, "Install");
  let r = bad(mapRenderedSelection(partOf(firstEl(ul, "PRE"), 0, 3), El(box), source));
  assert.match(r.reason, /code block/);
  assert.equal(r.blockStartLine, 2);
  assert.equal(r.rawHasQuote, true);
  assert.equal(source.slice(r.rawRange!.start, r.rawRange!.end), "npm");
  r = bad(mapRenderedSelection(partOf(firstEl(ul, "TABLE"), 0, 1), El(box), source));
  assert.match(r.reason, /table/);
  assert.equal(r.blockStartLine, 10);
  // a selection from the prose item into the code touches the hole
  const li0 = nonWsPositions(firstEl(ul, "LI", 0)), pre = nonWsPositions(firstEl(ul, "PRE"));
  r = bad(mapRenderedSelection(sel({ node: li0[0].t, offset: li0[0].off }, { node: pre[2].t, offset: pre[2].off + 1 }), El(box), source));
  assert.match(r.reason, /code block/);
  // a selection across the two prose items keeps the code's source between them
  const li1 = nonWsPositions(firstEl(ul, "LI", 1));
  r = bad(mapRenderedSelection(sel({ node: li0[0].t, offset: li0[0].off }, { node: li1[3].t, offset: li1[3].off + 1 }), El(box), source));
  assert.match(r.reason, /code block/, "the hole lies inside the selection");
  // painting a range inside the hole falls back to the code element's text
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
  for (const n of parseHTML(box.ownerDocument, marked.parse(B) as string)) box.appendChild(n);
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
