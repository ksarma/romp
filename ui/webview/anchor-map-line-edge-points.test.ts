// The Slice 8 review, round 6 (plans/markdown-viewer.md, Slice 8, item 4): where a change's deletion point sits on the LINE of the
// text before a table or a code block, on an INNER code line past its last character, and at the first character of a fenced
// block the reading could not place, the shapes the round's finders found wrong and fixed in anchor-map.ts (renderedSpot's
// edgeSpot). Round 5's edgeSpot handed every offset on the line of the prose before a nested fence or table, past adjacency to
// the prose's last character (its trailing whitespace, its line feed), back to renderedSpot's adjacency rule, which placed the
// point before the block's first positioned character, inside the fence's first row or the table's first header cell, a row or a
// cell the change is not in, where round 4's fence-line edge and main 696229f84's hole rule placed it after the prose, the Raw
// view's row; the same adjacency rule placed a point on an inner code line's trailing whitespace or line feed before the NEXT
// line's first character, one row down, or two past a blank line, since the build (round 5 cured the last line alone); and the
// start edge's search for the next fenced block required the opener's hole, which a code block the reading could not place has
// none of, so the search latched onto a later fence of the same block and the point at the unplaceable fence's first character
// kept its card, or sat before the later fence's code, where main placed it after the text before. Now an offset on the line of a
// positioned character, past it through the line's ending, with the block's next positioned character on a later line inside a
// table or a code block (the line before a block) or inside the same code block (an inner code line), sits after that character,
// its own line's; and the unplaceable block counts for the start edge with its raw's first character. Driven over the DOM
// stand-in the block-edge-points tests drive, marked's output under the one configuration parsed as a browser parses a fragment,
// the KaTeX fill stood in for, and every fence cut into rows as the Files pane cuts it (wrapLinesHtml) or left undressed where
// the scene says so. Every case that changes behaviour fails over a git archive of 43dbcc722, round 5's fix commit, at the
// assertion its title names. The third test installs a `fences` tokenizer override for the info string `hole` alone, a text that
// does not lay out over its raw, the one way to reach walkCode's hole (marked's own tokenizer yields none); the notes of the two
// tests before it never use that info string, and the override leaves every other fence to marked. The fourth test is the review's
// closing pass: the line before a nested table or fence holding no positioned character at all, a formula alone or a picture
// alone, whose offsets, past the hole through the block's first character, rounds 2 to 6 placed before the block's first
// positioned character, inside the first header cell or the fence's first row (round 6's line-before rule needs a positioned
// character to place the point after); now the start edge keeps the point on its card, as main 696229f84 kept it, when the block
// begins neither its item nor its quote and no positioned character of the item's stands before it (edgeSpot's
// unpositionedBefore). Its cases fail over a git archive of b69116e26, round 6's fix commit. The fifth test is the review's landing
// round, on the maintainer's ruling over the closing pass's record: a sub-item's table under an outer item holding a formula alone
// begins its sub-item, so the closing pass's rule, reading the sub-item alone, placed the outer line's line feed, the sub-item's
// indent and marker and the table's first character before the first header cell's first character, bytes outside the cell
// painted inside it, where main kept the card; now unpositionedBefore reads the items and quotes enclosing the block's own, out
// to the block's node, and the point keeps its card. Its cases fail over a git archive of 4a3e18664, the head the landing review
// read, and the fourth test's control K, which pinned the closing pass's placement, is re-pinned to the card. Synthetic values
// only: invented notes, no real session text.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked, type Tokens } from "marked";
import { applyMdConfig } from "./md-config";
import { wrapLinesHtml } from "./code-block";
import { paintChangesRendered, type ChangePaint } from "./anchor-map";
import { hideEdges } from "../test-dom-shim";

applyMdConfig();

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser (anchor-map-cells-formulas.test.ts's) ──
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
/** marked's HTML into the stand-in, as a browser's parser reads a fragment (anchor-map-cells-formulas.test.ts's parser). */
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
const escapeHtml = (s: string): string => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
/** mdBlock's dress of every fence (file-view.ts): cut into `.cl` rows by wrapLinesHtml (code-block.ts) with the line feeds dropped,
 *  the Copy button parked in the pre (anchor-map-blank-fence-points.test.ts's). */
function dressCode(box: FakeElement): void {
  const doc = box.ownerDocument;
  for (const pre of allOf(box, "PRE")) {
    const code = pre.childNodes.find((c) => c instanceof FakeElement && c.tagName === "CODE") as FakeElement | undefined;
    if (!code) continue;
    const raw = code.textContent;
    for (const c of code.childNodes.slice()) code.removeChild(c);
    for (const n of parseHTML(doc, wrapLinesHtml(escapeHtml(raw)))) code.appendChild(n);
    const btn = doc.createElement("button"); btn.setAttribute("class", "code-copy"); btn.appendChild(doc.createTextNode("Copy"));
    pre.appendChild(btn);
  }
}
/** `.fileview-md > marked output`, filled and dressed as the Files pane's body is. */
function buildRendered(text: string): FakeElement {
  const box = undressed(text);
  dressCode(box);
  return box;
}
/** The same with every pre left as marked emits it: no rows (a stand-in, a renderer that cut none). */
function undressed(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);
  standInFill(box);
  return box;
}
const El = (n: FakeNode) => n as unknown as Element;
/** The elements of `tag` under root, document order. */
const allOf = (root: FakeNode, tag: string, out: FakeElement[] = []): FakeElement[] => { for (const c of root.childNodes) { if (c instanceof FakeElement) { if (c.tagName === tag) out.push(c); allOf(c, tag, out); } } return out; };
const hasClass = (n: FakeNode, cls: string): boolean => n instanceof FakeElement && (n.getAttribute("class") || "").split(" ").includes(cls);
/** The k-th occurrence of `s` in `src`, which must exist. */
const at = (src: string, s: string, k = 0): number => { let i = -1; for (let n = 0; n <= k; n++) { i = src.indexOf(s, i + 1); assert.ok(i >= 0, "in the source: " + JSON.stringify(s)); } return i; };
const del = (id: string, curFrom: number): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText: "gone", author: "web" });
/** Where a painted point stands: the index of the `<li>` holding it among the box's items (-1 for none), of the `<pre>` (-1), the
 *  cell (tag, column, and the body row, -1 for the header) or null, and the text of the item (or the top-level block) before and
 *  after the point, whitespace squashed, the formulas' glyphs as `<tex>`. */
type Place = { li: number; pre: number; cell: { tag: string; col: number; row: number } | null; before: string; after: string };
function locate(box: FakeElement, id: string): Place | null {
  const pt = allOf(box, "SPAN").find((s) => hasClass(s, "fc-del") && s.getAttribute("data-id") === id);
  if (!pt) return null;
  const up = (tag: string): FakeElement | null => { let p = pt.parentNode; while (p && !(p instanceof FakeElement && p.tagName === tag)) p = p.parentNode; return p as FakeElement | null; };
  const li = up("LI"), pre = up("PRE"), td = up("TD") || up("TH");
  let host: FakeNode = pt;
  if (li) host = li; else while (host.parentNode && host.parentNode !== box) host = host.parentNode;
  let before = "", after = "", seen = false;
  const visit = (n: FakeNode): void => {
    if (n === pt) { seen = true; return; }
    if (n.nodeType === 3) { if (seen) after += (n as FakeText).data; else before += (n as FakeText).data; return; }
    if (hasClass(n, "katex")) { const g = "<" + n.textContent + ">"; if (seen) after += g; else before += g; return; }
    for (const c of n.childNodes) visit(c);
  };
  visit(host);
  const sq = (s: string): string => s.replace(/\s+/g, " ").trim();
  let cell: Place["cell"] = null;
  if (td) {
    const tr = td.parentNode as FakeElement, section = tr.parentNode as FakeElement;
    const rows = section.childNodes.filter((r) => r instanceof FakeElement && r.tagName === "TR");
    cell = { tag: td.tagName, col: tr.childNodes.filter((c) => c instanceof FakeElement).indexOf(td), row: td.tagName === "TH" ? -1 : rows.indexOf(tr) };
  }
  return { li: li ? allOf(box, "LI").indexOf(li) : -1, pre: pre ? allOf(box, "PRE").indexOf(pre) : -1, cell, before: sq(before), after: sq(after) };
}
/** Paint one deletion point at `off` on a fresh box and say where it stands (null: card-only). */
function placeOf(box: FakeElement, src: string, off: number): Place | null {
  const r = paintChangesRendered(El(box), src, [del("p", off)], () => ({}));
  if (r.painted.length === 0) { assert.deepEqual(r, { painted: [], unpainted: ["p"] }); return null; }
  assert.deepEqual(r, { painted: ["p"], unpainted: [] });
  const w = locate(box, "p");
  assert.ok(w, "the painted point is in the body");
  return w;
}


// ── the round's helpers ──
/** The painted point with `id`, which must be in the body. */
function pointOf(box: FakeElement, id: string): FakeElement {
  const pt = allOf(box, "SPAN").find((s) => hasClass(s, "fc-del") && s.getAttribute("data-id") === id);
  assert.ok(pt, "the point " + id + " is in the body");
  return pt!;
}
/** The index of the `.cl` row holding the point among its code's rows (code-block.ts wrapLinesHtml), -1 outside every row. */
function rowIndexOf(pt: FakeElement): number {
  let row: FakeNode | null = pt;
  while (row && !hasClass(row, "cl")) row = row.parentNode;
  if (!row || !row.parentNode) return -1;
  return row.parentNode.childNodes.filter((c) => hasClass(c, "cl")).indexOf(row);
}
/** The text of `root` before and after the point, unsquashed (the whitespace tells a point after a line's last character from
 *  one before the next line's first), the point's own label left out. */
function textAround(root: FakeNode, pt: FakeElement): [string, string] {
  let before = "", after = "", seen = false;
  const visit = (n: FakeNode): void => {
    if (n === pt) { seen = true; return; }
    if (n.nodeType === 3) { if (seen) after += (n as FakeText).data; else before += (n as FakeText).data; return; }
    for (const c of n.childNodes) visit(c);
  };
  visit(root);
  return [before, after];
}
/** The offsets from right after `word` (the k-th occurrence) through the ending of its line: the adjacent offset, each trailing
 *  whitespace character's, the line feed's (the CR's of a CRLF, and the LF byte's after it). */
function offsetsPast(src: string, word: string, k = 0): Array<[string, number]> {
  const e = at(src, word, k) + word.length;
  let eol = e; while (eol < src.length && src[eol] !== "\n" && src[eol] !== "\r") eol++;
  const out: Array<[string, number]> = [];
  for (let o = e; o <= eol; o++) out.push([o === e ? "adjacent" : o === eol ? JSON.stringify(src[o]) + " (the line ending)" : "+" + (o - e) + " " + JSON.stringify(src[o]), o]);
  if (src[eol] === "\r" && src[eol + 1] === "\n") out.push(["the LF byte", eol + 1]);
  return out;
}

// ── item 4: the line before a table or a code block is the text's own ──

test("a deletion point on the LINE of the text before a nested fence or table, past the text's last character (its trailing whitespace, the line feed that ends it, both bytes of a CRLF), sits after that character, outside the block, in the text's own item or quote, as the Raw view keeps it on the text's row (the review's round 6; round 5 placed it before the block's first positioned character, inside the fence's first row or the table's first header cell, which round 4 and main 696229f84 had not): an item's `Run this:  ` then a nested fence; a quote's `Quoted:  ` then a quoted fence; the CRLF twin; an ordered item's `Run:  `, a blank line, then a fence; an item's `Text:  `, a blank line, then a table; an outer item's `Outer  ` then a sub-item's fence (since the build: inside the sub-item's pre; main: after `Outer`); an item's `text  `, a blank line, then an indented block (since the build: in the block's first row; main: after `text`); an item's `see note[^1]  `, a footnote reference ending the text, then a fence (after `note`, before the reference's number; a point inside the reference keeps its card); the controls, unchanged: the bytes past the line ending (the indent before the opener and the opener's first backtick, the start edge's, after the same item's text; a sub-item's opener before its own code, round 4's rule; the blank line before an indented block in the block's first row, round 5's rule, an indented block having no start edge), a text line then the same item's text line, and a top-level paragraph before a top-level fence; with the Files pane's rows and undressed alike", () => {
  const scenes: Array<[string, string, string, number]> = [
    // label, source, the text's last word, the index of the <li> holding the text (-1 for none)
    ["A an item's `Run this:  ` then a nested fence", "- Run this:  \n  ```\n  make\n  ```\n- Next item\n", "Run this:", 0],
    ["B a quote's `Quoted:  ` then a quoted fence", "> Quoted:  \n> ```\n> qcode\n> ```\n", "Quoted:", -1],
    ["C the CRLF twin of A", "- Run this:  \r\n  ```\r\n  make\r\n  ```\r\n- Next item\r\n", "Run this:", 0],
    ["D an ordered item's `Run:  `, a blank line, then a fence", "1. Run:  \n\n   ```\n   make\n   ```\n", "Run:", 0],
    ["E an item's `Text:  `, a blank line, then a table", "- Text:  \n\n  | a | b |\n  |---|---|\n  | c | d |\n", "Text:", 0],
    ["F an outer item's `Outer  ` then a sub-item's fence", "- Outer  \n  - ```\n    code\n    ```\n", "Outer", 0],
    ["G an item's `text  `, a blank line, then an indented block", "- text  \n\n      code\n", "text", 0],
    ["J an item's `see note[^1]  `, a footnote reference ending the text, then a nested fence", "- see note[^1]  \n  ```\n  make\n  ```\n\n[^1]: The note.\n", "see note", 0],
    ["H control: a text line then the same item's text line", "- Run this:  \n  and then\n- Next item\n", "Run this:", 0],
    ["I control: a top-level paragraph, a blank line, then a top-level fence (two blocks)", "Intro  \n\n```\nmake\n```\n", "Intro", -1],
  ];
  for (const dressed of [true, false]) {
    const mode = dressed ? " (rows)" : " (undressed)";
    for (const [label, src, word, item] of scenes) {
      for (const [what, off] of offsetsPast(src, word).slice(label.startsWith("J") ? 4 : 0)) {   // J: past the reference's `[^1]`
        const tag = label + mode + " at " + what + " past the word";
        const w = placeOf(dressed ? buildRendered(src) : undressed(src), src, off);
        assert.ok(w, tag + ": placed");
        assert.equal(w!.pre, -1, tag + ": outside every pre (before: inside the fence's first row, before its first character): " + JSON.stringify(w));
        assert.equal(w!.cell, null, tag + ": outside every cell (before: in the table's first header cell): " + JSON.stringify(w));
        assert.equal(w!.li, item, tag + ": in the text's own item: " + JSON.stringify(w));
        assert.ok(w!.before.endsWith(word), tag + ": right after the text's last character: " + JSON.stringify(w!.before));
      }
    }
    // the bytes past the line ending are the start edge's, unchanged: the indent before the opener and the opener's first
    // backtick after the same item's text (A), the blank line's line feed too (D, E)
    for (const [label, src, word, before, first] of [["A", scenes[0][1], "Run this:", "\n  ```", "```"], ["D", scenes[3][1], "Run:", "\n\n", "```"], ["E", scenes[4][1], "Text:", "\n\n", "| a |"]] as Array<[string, string, string, string, string]>) {
      for (const off of [at(src, before) + 1, at(src, first)]) {
        const w = placeOf(dressed ? buildRendered(src) : undressed(src), src, off);
        assert.deepEqual([w!.li, w!.pre, w!.cell, w!.before.endsWith(word)], [0, -1, null, true], label + mode + " control, the start edge at " + JSON.stringify(src.slice(off, off + 1)) + ": after the same item's text: " + JSON.stringify(w));
      }
    }
    // a sub-item's opener: before its own code, in the sub-item (round 4's rule for a fence that begins an item)
    const f = scenes[5][1], fw = placeOf(dressed ? buildRendered(f) : undressed(f), f, at(f, "```"));
    assert.deepEqual([fw!.li, fw!.pre, fw!.after.startsWith("code")], [1, 0, true], "F" + mode + " control, the sub-item's opener: before its own code: " + JSON.stringify(fw));
    // a point inside the footnote reference before the fence keeps its card, the hole rule's, unchanged
    const jSrc = scenes[7][1];
    assert.equal(placeOf(dressed ? buildRendered(jSrc) : undressed(jSrc), jSrc, at(jSrc, "[^1]") + 1), null, "J" + mode + " control: a point inside the footnote reference keeps its card");
    assert.ok(allOf(dressed ? buildRendered(jSrc) : undressed(jSrc), "SUP").length >= 1, "J: the reference renders as a superscript");
    // the blank line before an indented block: the block's first row, round 5's rule (an indented block has no start edge), the
    // same since the build
    const g = scenes[6][1], gOff = at(g, "\n\n") + 1;
    assert.equal(g.slice(gOff - 1, gOff + 1), "\n\n", "the blank line's line feed");
    const gw = placeOf(dressed ? buildRendered(g) : undressed(g), g, gOff);
    assert.deepEqual([gw!.li, gw!.pre, gw!.after.startsWith("code")], [0, 0, true], "G" + mode + " control, the blank line before an indented block: before the block's first character: " + JSON.stringify(gw));
  }
});

// ── item 4: an inner code line's edge is the line's own ──

test("a deletion point on an INNER code line past its last character (its trailing whitespace, a tab, the line feed that ends it, both bytes of a CRLF) sits after that character in the line's own row (the review's round 6; since the build it sat before the NEXT line's first character, one row down, or two rows down past a blank line, where the Raw view keeps it on its line; round 5 cured the last line alone): a top-level python fence's `second = 2   `, a plain fence's first line, a list item's fence, a quoted fence, the CRLF twin, a blank line after the line, a whitespace-only line after it, a trailing tab, an indented block, and the middle line of three; the controls, unchanged: the adjacent offset, the next line's first character, a point inside a line at a character, the LAST line's trailing whitespace and line feed (round 5's edge), and a line with no trailing whitespace; with the Files pane's rows the row is the line's, undressed the point sits between the character and the line's trailing bytes", () => {
  const scenes: Array<[string, string, string, number]> = [
    // label, source, the inner line's text through its last character, the row the line is
    ["S1 a top-level python fence", "Intro.\n\n```python\nfirst = 1\nsecond = 2   \nthird = 3\n```\n\nAfter.\n", "second = 2", 1],
    ["S2 a plain fence, its first line", "Intro.\n\n```\nfirst = 1   \nsecond = 2\n```\n\nAfter.\n", "first = 1", 0],
    ["S3 a list item's fence", "- Item:\n\n  ```python\n  first = 1\n  second = 2   \n  third = 3\n  ```\n\n  after\n", "second = 2", 1],
    ["S4 a quoted fence", "> Q:\n>\n> ```python\n> first = 1\n> second = 2   \n> third = 3\n> ```\n", "second = 2", 1],
    ["S5 the CRLF twin of S1", "Intro.\r\n\r\n```python\r\nfirst = 1\r\nsecond = 2   \r\nthird = 3\r\n```\r\n\r\nAfter.\r\n", "second = 2", 1],
    ["S6 a blank line after the line", "Intro.\n\n```\na2 = 1   \n\nb2 = 2\n```\n\nAfter.\n", "a2 = 1", 0],
    ["S7 a whitespace-only line after the line", "```\na2 = 1   \n   \nb2 = 2\n```\n", "a2 = 1", 0],
    ["S8 a trailing tab", "```\nfirst = 1\t\nsecond = 2\n```\n", "first = 1", 0],
    ["S9 an indented block", "Intro.\n\n    first = 1   \n    second = 2\n\nAfter.\n", "first = 1", 0],
    ["S10 the middle line of three", "```\na = 1\nb = 2   \nc = 3\n```\n", "b = 2", 1],
  ];
  const place = (box: FakeElement, src: string, off: number, id = "p"): FakeElement => {
    assert.deepEqual(paintChangesRendered(El(box), src, [del(id, off)], () => ({})), { painted: [id], unpainted: [] }, "the point at " + off + " places");
    return pointOf(box, id);
  };
  for (const [label, src, word, row] of scenes) {
    for (const [what, off] of offsetsPast(src, word)) {
      const tag = label + " at " + what + " past the line's last character";
      const box = buildRendered(src), pt = place(box, src, off);
      assert.equal(rowIndexOf(pt), row, tag + " (rows): in the line's own row (before: the next line's, one row down, or two past a blank line)");
      let rowEl: FakeNode = pt; while (!hasClass(rowEl, "cl")) rowEl = rowEl.parentNode!;
      assert.ok(textAround(rowEl, pt)[0].endsWith(word), tag + " (rows): right after the line's last character: " + JSON.stringify(textAround(rowEl, pt)));
      const ub = undressed(src), up = place(ub, src, off), pre = allOf(ub, "PRE")[0];
      const [before, after] = textAround(pre, up);
      assert.ok(before.endsWith(word), tag + " (undressed): right after the line's last character (before: after the line's ending, before the next line's first): " + JSON.stringify([before.slice(-12), after.slice(0, 12)]));
      assert.match(after, /^\s/, tag + " (undressed): the line's trailing bytes follow the point: " + JSON.stringify(after.slice(0, 12)));
    }
  }
  // the controls, the same on every tree
  const s1 = scenes[0][1], b1 = buildRendered(s1);
  const inLine = at(s1, "second = 2") + "second = ".length, next = at(s1, "third"), noWs = at(s1, "first = 1") + "first = 1".length;
  assert.equal(s1[noWs], "\n", "the first line ends right after its last character");
  const r1 = paintChangesRendered(El(b1), s1, [del("in", inLine), del("next", next), del("lf", noWs)], () => ({}));
  assert.deepEqual(r1, { painted: ["in", "next", "lf"], unpainted: [] });
  assert.deepEqual([rowIndexOf(pointOf(b1, "in")), rowIndexOf(pointOf(b1, "next")), rowIndexOf(pointOf(b1, "lf"))], [1, 2, 0], "the controls' rows: inside the second line at `2`, before `third`, after `first = 1`");
  let inRow: FakeNode = pointOf(b1, "in"); while (!hasClass(inRow, "cl")) inRow = inRow.parentNode!;
  assert.deepEqual(textAround(inRow, pointOf(b1, "in")), ["second = ", "2   "], "a point inside a line at a character: before that character");
  let nextRow: FakeNode = pointOf(b1, "next"); while (!hasClass(nextRow, "cl")) nextRow = nextRow.parentNode!;
  assert.deepEqual(textAround(nextRow, pointOf(b1, "next")), ["", "third = 3"], "the next line's first character: before it, in its row");
  let lfRow: FakeNode = pointOf(b1, "lf"); while (!hasClass(lfRow, "cl")) lfRow = lfRow.parentNode!;
  assert.deepEqual(textAround(lfRow, pointOf(b1, "lf")), ["first = 1", ""], "a line with no trailing whitespace: its line feed's point after its last character");
  const last = "```\nfirst = 1\nsecond = 2   \n```\n", bl = buildRendered(last);
  for (const [what, off] of offsetsPast(last, "second = 2")) {
    const pt = place(bl, last, off, "last-" + off);
    assert.equal(rowIndexOf(pt), 1, "the LAST line at " + what + ": its own row, round 5's edge");
  }
});

// ── items 1 and 4: a fenced block the reading could not place counts for the start edge ──

test("a deletion point at the first character of a fenced block the reading could not place (walkCode's hole, reached through a `fences` tokenizer override whose text does not lay out over the raw; marked's own tokenizer yields none), with a later fence in the same item, sits after the item's text before it, as main 696229f84 placed it (the review's round 6; round 5's start edge searched for the next fence by its opener's hole, which the hole has none of, latched onto the later fence, and kept the card, or, with the later fence right after, placed the point before that fence's code); the same in a quote, and at the indent and the blank line before the unplaceable fence; a point inside the hole keeps its card, the hole rule's (round 6; with the later fence right after, round 5's start edge placed it before that fence's code); the controls: with no later fence the point sat after the text on every tree, the later fence's own first character sits before its own code (round 5's rule for a fence after another code block's characters), and the same note with marked's own fence maps as before", () => {
  const ctrl = "Intro line.\n\n- Item text\n\n  ```python\n  hole_a = 1\n  hole_b = 2\n  ```\n\n  ```\n\n  ```\n\n  ```\n  plain_c = 3\n  ```\n- Second item\n\nAfter line.\n";
  const lexed = JSON.stringify(marked.lexer(ctrl));
  // the override: a fence whose info string is `hole` gets a text with one space more per line than its raw's lines carry, so
  // codeLineStarts finds no line laid out over the raw and walkCode makes the block one hole; every other fence is marked's
  marked.use({ tokenizer: { fences(src: string) {
    const rules = (this as unknown as { rules: { block: { fences: RegExp } } }).rules;
    const cap = rules.block.fences.exec(src);
    if (!cap || (cap[2] || "").trim() !== "hole") return false as unknown as undefined;
    return { type: "code", raw: cap[0], lang: "hole", text: (cap[3] || "").split("\n").map((l) => " " + l).join("\n") } as Tokens.Code;
  } } });
  assert.equal(JSON.stringify(marked.lexer(ctrl)), lexed, "the override leaves a note with no `hole` fence to marked");
  const hole = ctrl.replace("```python", "```hole");
  const box = undressed(hole);
  assert.equal(allOf(box, "PRE").length, 3, "three pres");
  assert.ok(allOf(box, "PRE")[0].textContent.startsWith(" hole_a = 1\n hole_b = 2"), "the override's text, one space more per line, is what the pre shows: " + JSON.stringify(allOf(box, "PRE")[0].textContent));
  const scenes: Array<[string, string, string, number]> = [
    // label, source, the text before the unplaceable fence, the index of the <li> holding it (-1 for none)
    ["A a hole fence, a blank fence and a plain fence in one item", hole, "Item text", 0],
    ["C a hole fence then a plain fence right after", "Intro line.\n\n- Item text\n\n  ```hole\n  hole_a = 1\n  ```\n\n  ```\n  plain_c = 3\n  ```\n- Second item\n\nAfter line.\n", "Item text", 0],
    ["Q the same in a quote", "Intro line.\n\n> Quote text\n>\n> ```hole\n> hole_a = 1\n> ```\n>\n> ```\n> plain_c = 3\n> ```\n\nAfter line.\n", "Quote text", -1],
    ["B control: a hole fence with no later fence", "Intro line.\n\n- Item text\n\n  ```hole\n  hole_a = 1\n  hole_b = 2\n  ```\n- Second item\n\nAfter line.\n", "Item text", 0],
  ];
  for (const dressed of [true, false]) {
    const mode = dressed ? " (rows)" : " (undressed)";
    for (const [label, src, word, item] of scenes) {
      const open = at(src, "```hole");
      // the opener's first character, the indent (or the quote's marker) before it, and the blank line's line feed before that
      for (const off of [open, open - 1, open - 2, open - 3]) {
        const tag = label + mode + " at " + JSON.stringify(src.slice(off, off + 1)) + " (" + (off === open ? "the opener's first character" : off === open - 3 ? "the blank line's line feed" : "before the opener") + ")";
        const w = placeOf(dressed ? buildRendered(src) : undressed(src), src, off);
        assert.ok(w, tag + ": placed (before: card-only, the search latched onto the later fence and the hole's characters stood between)");
        assert.deepEqual([w!.li, w!.pre, w!.cell, w!.before.endsWith(word)], [item, -1, null, true], tag + ": after the text before the fence (before: card-only, or before the later fence's code): " + JSON.stringify(w));
      }
      const inside = placeOf(dressed ? buildRendered(src) : undressed(src), src, at(src, "hole_a") + 2);
      assert.equal(inside, null, label + mode + ": a point inside the hole keeps its card (before, with a placed fence right after the hole: before that fence's code): " + JSON.stringify(inside));
    }
    // the later fence's own first character: before its own code, the text before it another code block's characters
    const a = scenes[0][1], aw = placeOf(dressed ? buildRendered(a) : undressed(a), a, at(a, "```\n  plain_c"));
    assert.deepEqual([aw!.li, aw!.pre, aw!.after.startsWith("plain_c")], [0, 2, true], "A" + mode + " control, the plain fence's opener: before its own code: " + JSON.stringify(aw));
    // marked's own fence in the same shape: after the text before it, as before this round
    const cw = placeOf(dressed ? buildRendered(ctrl) : undressed(ctrl), ctrl, at(ctrl, "```python"));
    assert.deepEqual([cw!.li, cw!.pre, cw!.cell, cw!.before.endsWith("Item text")], [0, -1, null, true], "the control" + mode + ": marked's own fence's opener after the item's text: " + JSON.stringify(cw));
  }
});

// ── items 1 and 4: a block after a line with no positioned character begins neither its item nor its quote ──

test("a deletion point on the line of a formula alone or a picture alone before a nested table or fence, past the hole (its trailing whitespace, the line feed that ends it), on the blank line, at the indent before the block and at the block's first character, keeps its card, as main 696229f84 kept it, its table a hole (the review's closing pass; rounds 2 to 6 placed it before the block's first positioned character, inside the table's first header cell or the fence's first row, a cell or a row the change is not in: the line before has no positioned character to place the point after, and the block begins neither its item nor its quote): an item's `$x$  `, a blank line, then a table; the same with no blank line; an item's picture alone; an item's display formula alone; a quote's formula alone; an item's formula alone then a fence; a second item's formula alone after a text item (rounds 2 to 6: in the second item's header cell; main: after the first item's text); the table with the item's prose after it; a footnote reference alone, a hole with a character and no positioned one, the same rule's; and a point inside the formula's TeX, which the hole rule does not catch, a formula's hole having no character (before: before the block's first character too); a sub-item's table under a formula-alone item, card-only since the PR review's round 1 (the fifth test; the closing pass: its first character before its own first cell, round 4's rule for a block that begins its item); the controls, unchanged: an item's `lead $x$  ` then a table (after `lead`, the line before's rule and the start edge's), and a top-level formula paragraph then a top-level table (the paragraph's line card-only, the table's first character before its first cell, the top-level rule); with the Files pane's rows and undressed alike", () => {
  const scenes: Array<[string, string, string, string]> = [
    // label, source, the hole's source text (its first occurrence), the block's first character's text
    ["A an item's formula alone, a blank line, then a table", "- $x$  \n\n  | a | b |\n  |---|---|\n  | c | d |\n", "$x$", "| a |"],
    ["B the same with no blank line", "- $x$  \n  | a | b |\n  |---|---|\n", "$x$", "| a |"],
    ["C an item's picture alone", "- ![p](a.png)  \n\n  | a | b |\n  |---|---|\n", "![p](a.png)", "| a |"],
    ["D an item's display formula alone", "- $$x = 1$$  \n\n  | a | b |\n  |---|---|\n", "$$x = 1$$", "| a |"],
    ["E a quote's formula alone", "> $x$  \n>\n> | a | b |\n> |---|---|\n", "$x$", "| a |"],
    ["F an item's formula alone then a fence", "- $x$  \n  ```\n  code\n  ```\n", "$x$", "```"],
    ["G a second item's formula alone after a text item", "- one\n- $x$  \n\n  | a | b |\n  |---|---|\n", "$x$", "| a |"],
    ["H the table with the item's prose after it", "- $x$  \n\n  | a | b |\n  |---|---|\n\n  after\n", "$x$", "| a |"],
    ["J a footnote reference alone", "- [^1]  \n\n  | a | b |\n  |---|---|\n\n[^1]: The note.\n", "[^1]", "| a |"],
  ];
  for (const dressed of [true, false]) {
    const mode = dressed ? " (rows)" : " (undressed)";
    const build = (src: string): FakeElement => dressed ? buildRendered(src) : undressed(src);
    for (const [label, src, hole, first] of scenes) {
      const e = at(src, hole) + hole.length, s = at(src, first);
      assert.ok(e < s, label + ": the hole ends before the block");
      const box = build(src);
      // the block renders, and the hole's rendering stands before it in the same item or quote: the formula's glyphs (a control the
      // walks skip), the picture (no text), the reference's number (a hole's character)
      const block = allOf(box, first === "```" ? "PRE" : "TABLE")[0];
      assert.ok(block, label + ": the block renders");
      const holder = label.startsWith("C") ? allOf(box, "IMG")[0] : label.startsWith("J") ? allOf(box, "SUP")[0] : allOf(box, "SPAN").find((n) => hasClass(n, "katex"));
      assert.ok(holder, label + ": the hole renders");
      let container: FakeNode | null = block.parentNode; while (container && !(container instanceof FakeElement && (container.tagName === "LI" || container.tagName === "BLOCKQUOTE"))) container = container.parentNode;
      assert.ok(container, label + ": the block is nested in an item or a quote");
      let up: FakeNode | null = holder!; while (up && up !== container) up = up.parentNode;
      assert.equal(up, container, label + ": the hole's rendering is in the block's own item or quote");
      for (let off = e; off <= s; off++) {
        const tag = label + mode + " at " + JSON.stringify(src[off]) + " (" + (off === e ? "adjacent to the hole" : off === s ? "the block's first character" : "+" + (off - e) + " past the hole") + ")";
        const w = placeOf(build(src), src, off);
        assert.equal(w, null, tag + ": card-only (before: inside the block, before its first positioned character): " + JSON.stringify(w));
      }
      // inside the formula's TeX (the hole rule does not catch a zero-text hole; before: before the block's first character too); a
      // point inside the picture's or the reference's source is the hole rule's or the picture's, not this test's
      if (hole.startsWith("$")) {
        const inside = at(src, hole) + (hole.startsWith("$$") ? 2 : 1);   // the TeX's first character
        assert.equal(placeOf(build(src), src, inside), null, label + mode + ": a point inside the formula's TeX keeps its card");
      }
    }
    // a sub-item's table under a formula-alone item: card-only since the PR review's round 1 (the fifth test), the outer item's formula
    // unpositioned content before a table that begins its sub-item; the closing pass placed it before its own first cell, round 4's
    // rule for a block that begins its item, and recorded the shape without a ruling
    const k = "- $x$\n  - | a | b |\n    |---|---|\n", kw = placeOf(build(k), k, at(k, "| a |"));
    assert.equal(kw, null, "K" + mode + ": a sub-item's table under a formula-alone item keeps its card (the closing pass: before its own first cell): " + JSON.stringify(kw));
    // an item's `lead $x$  ` then a table: after `lead`, the line before's rule for the offsets on the line and the start edge's for
    // the blank line and the table's first character, the formula's glyphs after the point
    const l = "- lead $x$  \n\n  | a | b |\n  |---|---|\n";
    for (const off of [at(l, "$x$") + 3, at(l, "$x$") + 5, at(l, "\n\n") + 1, at(l, "| a |")]) {
      const lw = placeOf(build(l), l, off);
      assert.deepEqual([lw!.li, lw!.cell, lw!.before, lw!.after.startsWith("<x>")], [0, null, "lead", true], "L" + mode + " control at " + JSON.stringify(l[off]) + ": after `lead`, outside the table: " + JSON.stringify(lw));
    }
    // a top-level formula paragraph then a top-level table, two blocks: the paragraph's line is card-only (the paragraph has no
    // mapped text), the table's first character sits before its first cell, the top-level rule
    const m = "$x$  \n\n| a | b |\n|---|---|\n";
    assert.equal(placeOf(build(m), m, at(m, "$x$") + 3), null, "M" + mode + " control: the top-level formula paragraph's trailing space keeps its card");
    const mw = placeOf(build(m), m, at(m, "| a |"));
    assert.deepEqual([mw!.li, mw!.cell, mw!.after.startsWith("a")], [-1, { tag: "TH", col: 0, row: -1 }, true], "M" + mode + " control: the top-level table's first character before its first cell: " + JSON.stringify(mw));
  }
});

// ── items 1 and 4: content of an ENCLOSING item or quote before a block that begins its own ──

test("a deletion point under an OUTER item holding a formula alone, at the outer line's line feed, on the sub-item's indent and its marker, and at the sub-item's table's first character, keeps its card, as main 929ae86e1 kept it, the table a hole (the PR review's round 1, on the maintainer's ruling over the closing pass's record: the closing pass placed every one of them before the first header cell's first character, bytes outside the cell painted inside it, the table beginning its own item and the pass's rule reading that item alone; now the rule reads the items and quotes enclosing the block's own, out to the block's node, so the outer item's formula is unpositioned content before the table): the outer item's `$x$` then a sub-item's table, with a blank line between too, the fence twin (before: before the first code character, in the pre's first row), and a list item's table in a quote holding a formula alone before the list; the controls, unchanged: an outer item's `one` then a sub-item's table (the line feed after `one` sits after `one`; the indent, the marker and the pipe before the first cell's text, round 4's rule for a table that begins its item), a formula-alone item then a table ITEM (a sibling's marker and pipe before the first cell's text, the same rule), and a point inside the cell in the cell; with the Files pane's rows and undressed alike", () => {
  const scenes: Array<[string, string, string, string, "TH" | "PRE"]> = [
    // label, source, the hole's source text, the block's first character's text, where the block's first character rendered
    ["K1 the outer item's `$x$` then a sub-item's table", "- $x$\n  - | ab | cd |\n    |----|----|\n", "$x$", "| ab |", "TH"],
    ["K2 the same with a blank line between", "- $x$\n\n  - | ab | cd |\n    |----|----|\n", "$x$", "| ab |", "TH"],
    ["K3 the fence twin", "- $x$\n  - ```\n    code\n    ```\n", "$x$", "```", "PRE"],
    ["K4 a list item's table in a quote holding a formula alone before the list", "> $x$\n>\n> - | ab | cd |\n>   |----|----|\n", "$x$", "| ab |", "TH"],
  ];
  for (const dressed of [true, false]) {
    const mode = dressed ? " (rows)" : " (undressed)";
    const build = (src: string): FakeElement => dressed ? buildRendered(src) : undressed(src);
    for (const [label, src, hole, first, where] of scenes) {
      const e = at(src, hole) + hole.length, s = at(src, first);
      assert.ok(e < s, label + ": the hole ends before the block");
      const box = build(src);
      const block = allOf(box, where === "PRE" ? "PRE" : "TABLE")[0];
      assert.ok(block, label + ": the block renders");
      // the block begins its own item, and the formula's glyphs stand in an item or a quote enclosing that item
      let item: FakeNode | null = block.parentNode; while (item && !(item instanceof FakeElement && item.tagName === "LI")) item = item.parentNode;
      assert.ok(item, label + ": the block is in a list item");
      assert.equal(item!.childNodes.findIndex((c) => c instanceof FakeElement) , item!.childNodes.indexOf(block), label + ": the block is its item's first element");
      const glyphs = allOf(box, "SPAN").find((n) => hasClass(n, "katex"));
      assert.ok(glyphs, label + ": the formula renders");
      let up: FakeNode | null = glyphs!; while (up && up !== item) up = up.parentNode;
      assert.equal(up, null, label + ": the formula is not in the block's own item");
      for (let off = e; off <= s; off++) {
        const tag = label + mode + " at " + JSON.stringify(src[off]) + " (" + (off === e ? "the outer line's line feed" : off === s ? "the block's first character" : "+" + (off - e) + " past the hole") + ")";
        const w = placeOf(build(src), src, off);
        assert.equal(w, null, tag + ": card-only (the closing pass: before the block's first positioned character, inside its first header cell or its first row): " + JSON.stringify(w));
      }
      // a point inside the cell or the line places in it, the cell's own
      const inside = at(src, where === "PRE" ? "code" : "ab") + 1, iw = placeOf(build(src), src, inside);
      assert.ok(iw && (where === "PRE" ? iw.pre >= 0 : iw.cell !== null && iw.cell.tag === "TH" && iw.cell.col === 0), label + mode + ": a point inside the cell or the line places in it: " + JSON.stringify(iw));
    }
    // the controls: an outer item's TEXT then a sub-item's table: the line feed after `one` after `one` (the line before's rule),
    // the indent, the marker and the pipe before `ab` (round 4's rule for a table that begins its item), as before
    const c1 = "- one\n  - | ab | cd |\n    |----|----|\n", lf = at(c1, "one") + 3;
    assert.equal(c1[lf], "\n");
    const lw = placeOf(build(c1), c1, lf);
    assert.deepEqual([lw!.li, lw!.cell, lw!.before], [0, null, "one"], "C1" + mode + " control, the line feed after `one`: after `one`: " + JSON.stringify(lw));
    for (const off of [lf + 1, lf + 2, lf + 3, at(c1, "| ab |")]) {
      const w = placeOf(build(c1), c1, off);
      assert.deepEqual([w!.li, w!.cell, w!.after.startsWith("ab")], [1, { tag: "TH", col: 0, row: -1 }, true], "C1" + mode + " control at " + JSON.stringify(c1[off]) + ": before the sub-item's first cell's text, round 4's rule: " + JSON.stringify(w));
    }
    // a formula-alone item then a table ITEM: a sibling's content is not content before the block, so the item's marker and the
    // pipe sit before `ab`, round 4's rule, as before
    const c2 = "- $x$\n- | ab | cd |\n  |----|----|\n", marker = at(c2, "- | ab");
    for (const off of [marker, marker + 1, marker + 2]) {
      const w = placeOf(build(c2), c2, off);
      assert.deepEqual([w!.li, w!.cell, w!.after.startsWith("ab")], [1, { tag: "TH", col: 0, row: -1 }, true], "C2" + mode + " control at " + JSON.stringify(c2[off]) + ": before the sibling table item's first cell's text, round 4's rule: " + JSON.stringify(w));
    }
  }
});
