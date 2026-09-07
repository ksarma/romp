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
  paintRawPoint, paintChangesRaw, paintChangesRendered, unpaintChanges, deletionLabel, DEL_LABEL_MAX, PILCROW, type ChangePaint,
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
  assert.deepEqual([...new Set(insMarks.map(rowOf))], [rows[1], rows[2]]);
  assert.equal(noEol(insMarks.map((m) => m.textContent).join("")), noEol(byId["c-ins"].newText!));
  const subMarks = marksOf("c-sub");
  // the blank CRLF rows in between show their CR as an LF, which the range covers, so each holds one mark over it
  assert.deepEqual([...new Set(subMarks.map(rowOf))], [rows[4], rows[5], rows[6], rows[7]]);
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

test("Rendered change marks: ins and sub paint their new text with the author's styles, a del is reported unpainted, unpaint restores the DOM", () => {
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

  const res = paintChangesRendered(El(box), source, changes, stylesFor);
  assert.deepEqual(res, { painted: ["r-ins", "r-sub"], unpainted: ["r-del"] });
  assert.equal(stripWs(domText(box, null)), textBefore, "painting keeps the rendered text");
  const marks = withClass(box, "fc-ins");
  assert.ok(marks.length >= 2);
  assert.equal(withClass(box, "fc-del").length, 0, "no deletion point in Rendered");
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
  // the selection maps the same over the painted DOM, from inside the mark
  const insMark = marks.find((m) => m.getAttribute("data-id") === "r-ins")!;
  const inner = insMark.childNodes[0] as FakeText;
  const post = ok(mapRenderedSelection(sel({ node: inner, offset: 0 }, { node: inner, offset: inner.data.length }), El(box), source));
  assert.deepEqual(post, preSel);
  unpaintChanges(El(box));
  assert.equal(serialize(box), before);
});

test("Rendered change marks: an insertion inside a code fence paints through the text-match fallback; one whose text is not on the page does not", () => {
  const source = fixture("refusals.md");
  const { box } = buildRendered(source);
  const before = serialize(box);
  const q = "respond(request)";
  const i = source.indexOf(q);
  // the table's separator row is in the file but renders no text: nothing on the page to paint
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
