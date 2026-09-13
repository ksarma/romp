// The Slice 8 review, round 5 (plans/markdown-viewer.md, Slice 8, items 1 and 4): where a change's deletion point sits at the
// EDGE of a table or a code block inside its block, the shapes the round's finders found wrong or unpinned and fixed in
// anchor-map.ts (renderedSpot's edgeSpot). Round 4 had gated the table-edge and fence-edge placement after the text before the
// block on that text standing in the same list item (sameItem), which cured a point at a table or a fence that BEGINS an item
// landing in the previous item, but applied the gate to a fence's closer edge too, so a point after trailing whitespace on the
// last code line of a fence that ENDS an item was painted in the NEXT item; the edge rules needed the block's first positioned
// character, which a table of formulas alone or a fence of blank lines has none of, so such a block beginning an item put its
// point after the previous item's text or before the next item's; a table whose first header cell shows nothing (a formula, a
// picture, an empty cell) placed the table's first character's point before the first POSITIONED character, in the second
// column or the body row; and two tables in one item with nothing between placed the second's first character inside the
// first's last cell. Now the closer edge is the fence's own (after its last code character, whatever follows), the start edge
// places after the same item's prose before the block, else before the block's first positioned character, and, with none
// where it looks (the first header cell, the code), keeps the card, and a character of another table or code block is never
// "the text before". A cell the per-cell fallback holds (an entity) keeps a point at its first or last position on its card,
// round 4's rule, pinned here (round 3 placed them in the neighbouring cells). Driven over the DOM stand-in the cells tests
// drive, marked's output under the one configuration parsed as a browser parses a fragment, the KaTeX fill stood in for, and
// every fence cut into rows as the Files pane cuts it (wrapLinesHtml) or left undressed where the scene says so. Every case that
// changes behaviour fails over a git archive of 8ae3fda02, round 4's fix commit, at the assertion its title names; the hole
// cell's pins fail over one of 90c6ff242, round 3's. Synthetic values only: invented notes, no real session text.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
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

// ── item 4: a fence's closer edge is the fence's own ──

test("a deletion point after the last code character of a fence that ENDS a list item, on the trailing whitespace of that line or at the line feed that ends it, sits after that character in the fence's own pre (the review's round 5; round 4 gated the closer edge on the same-item test meant for the opener, so the point was painted before the NEXT item's text, or inside the next item's pre, or before the outer item's text after a sub-item's fence; round 3 had it right): an ordered item's `make ` with one trailing space, then a text item; a fence item's `code ` then a text item; two trailing spaces then a fence item; a sub-item's fence then the outer item's text; the CRLF twin; an indented block ending an item; the controls, unchanged: no trailing whitespace, a top-level fence, a quote's fence, a fence then the same item's text, and a fence item with no item after; with the Files pane's rows and undressed alike", () => {
  const scenes: Array<[string, string, string, number]> = [
    // label, source, the last code word, the index of the <li> holding the fence (-1 for none)
    ["A an ordered item `make ` (one trailing space), then `2. Then check.`", "1. Run:\n\n   ```\n   make \n   ```\n\n2. Then check.\n", "make", 0],
    ["B a fence item `code ` (one trailing space), then a text item", "- ```\n  code \n  ```\n- Item two\n", "code", 0],
    ["C a fence item `code  ` (two trailing spaces), then a fence item", "- ```\n  code  \n  ```\n- ```\n  more\n  ```\n", "code", 0],
    ["D a sub-item's fence `code  ` (two trailing spaces), then the outer item's text", "- Outer\n  - ```\n    code  \n    ```\n\n  after\n", "code", 1],
    ["E the CRLF twin of B, two trailing spaces", "- ```\r\n  code  \r\n  ```\r\n- Item two\r\n", "code", 0],
    ["K an indented block ending an item, two trailing spaces, then a text item", "- text\n\n      code  \n- Item two\n", "code", 0],
    ["F control: no trailing whitespace", "- ```\n  code\n  ```\n- Item two\n", "code", 0],
    ["G control: a top-level fence", "```\ncode  \n```\n\nAfter\n", "code", -1],
    ["H control: a quote's fence", "> ```\n> code  \n> ```\n>\n> after\n", "code", -1],
    ["I control: a fence then the SAME item's text", "- ```\n  code  \n  ```\n  tail\n- Item two\n", "code", 0],
    ["J control: a fence item with no item after", "Intro\n\n- ```\n  code  \n  ```\n", "code", 0],
  ];
  for (const dressed of [true, false]) {
    for (const [label, src, word, item] of scenes) {
      const e = at(src, word) + word.length;
      let eol = e; while (src[eol] !== "\n" && src[eol] !== "\r") eol++;
      const offs: number[] = []; for (let o = e; o <= eol; o++) offs.push(o); if (src[eol] === "\r") offs.push(eol + 1);
      for (const off of offs) {
        const tag = label + (dressed ? " (rows)" : " (undressed)") + " at " + JSON.stringify(src.slice(e, off)) + " past the word" + (off === eol + 1 ? " (the LF byte)" : "");
        const w = placeOf(dressed ? buildRendered(src) : undressed(src), src, off);
        assert.ok(w, tag + ": placed");
        assert.ok(w!.pre >= 0, tag + ": inside a pre (before: in the next item's text, or the outer item's, outside every pre): " + JSON.stringify(w));
        assert.equal(w!.li, item, tag + ": in the fence's own item: " + JSON.stringify(w));
        assert.ok(w!.before.endsWith(word), tag + ": right after the last code character: " + JSON.stringify(w!.before));
      }
    }
  }
});

test("a fence's trailing blank line in a list item followed by another item, where the pre has no row for it (undressed), places after the fence's last character in the fence's own item (the review's round 5; round 4: before the next item's text, the same closer-edge gate); with the Files pane's rows the line goes to the end of the pre's last row as before, the control", () => {
  const src = "- Item one\n\n  ```\n  code\n\n  ```\n- Item two\n";
  const off = at(src, "  code\n") + 7;   // the blank line's line feed
  assert.equal(src.slice(off - 1, off + 1), "\n\n", "the offset is the blank line's line feed");
  const u = placeOf(undressed(src), src, off);
  assert.deepEqual([u!.li, u!.pre >= 0, u!.before.endsWith("code")], [0, true, true], "undressed: after `code` in item 1's pre (before: before `Item two`, in item 2): " + JSON.stringify(u));
  const d = placeOf(buildRendered(src), src, off);
  assert.deepEqual([d!.li, d!.pre >= 0, d!.before.endsWith("code")], [0, true, true], "with rows: the end of the pre's last row, after `code`, as before: " + JSON.stringify(d));
});

// ── items 1 and 4: the start edge of a table or a fence is that block's own ──

test("a table or a fence right after another table or fence in the SAME list item, nothing between: the point at its first character sits before its own first character, never inside the earlier block's last cell or row (the review's round 5; before, the earlier block's last character was `the text before` and the point sat after `b` inside the first table's last cell, or after `code` in the fence's row): two tables, a table then a fence, a fence then a table, two fences; the item's own text before a table keeps the after-the-text rule, the control", () => {
  const scenes: Array<[string, string, string, string, "TH" | "PRE", number]> = [
    // label, source, the block's first characters, the text right after the point, where it stands, the pre's index (for a fence)
    ["two tables", "- | a |\n  |---|\n  | b |\n\n  | c |\n  |---|\n  | d |\n", "| c |", "c", "TH", -1],
    ["a table then a fence", "- | a |\n  |---|\n  | b |\n\n  ```\n  code\n  ```\n", "```", "code", "PRE", 0],
    ["a fence then a table", "- ```\n  code\n  ```\n\n  | a |\n  |---|\n  | b |\n", "| a |", "a", "TH", -1],
    ["two fences", "- ```\n  a\n  ```\n  ```\n  b\n  ```\n", "```\n  b", "b", "PRE", 1],
  ];
  for (const [label, src, first, next, tag, pre] of scenes) {
    const w = placeOf(buildRendered(src), src, at(src, first));
    assert.ok(w, label + ": placed");
    assert.equal(w!.li, 0, label + ": in the item");
    if (tag === "TH") assert.deepEqual([w!.cell && w!.cell.tag, w!.cell && w!.cell.col, w!.pre], ["TH", 0, -1], label + ": in the block's own first header cell (before: inside the earlier block): " + JSON.stringify(w));
    else assert.deepEqual([w!.pre, w!.cell], [pre, null], label + ": in the block's own pre (before: inside the earlier block): " + JSON.stringify(w));
    assert.ok(w!.after.startsWith(next), label + ": right before the block's first character: " + JSON.stringify(w!.after));
  }
  const own = "- text\n\n  | a |\n  |---|\n  | b |\n\n  | c |\n  |---|\n  | d |\n";
  const w1 = placeOf(buildRendered(own), own, at(own, "| a |"));
  assert.deepEqual([w1!.cell, w1!.before], [null, "text"], "the item's own text before the first table: after the text, round 2's rule");
  const w2 = placeOf(buildRendered(own), own, at(own, "| c |"));
  assert.deepEqual([w2!.cell && w2!.cell.tag, w2!.after.startsWith("c")], ["TH", true], "the second table, after the first: before its own first cell");
});

test("a table of formulas alone, a table of pictures alone, a table whose first cell the per-cell fallback holds, a fence whose lines all show nothing, or an empty fence, BEGINNING a list item: the point at its first character keeps its card, there being no character of the block's own to place it before (the review's round 5; before: after the previous item's text, inside that item's pre or its table's last cell when the item was a fence or a table, or before the NEXT item's text, cells and items the change is not in; main 696229f84 kept the card for the table shapes after a fence or a table item); the blank line's own point goes into the pre's row as before; the controls, unchanged: the same item's text before such a table places after that text, a positioned table or fence beginning an item places before its first character, and the top-level twins keep their cards", () => {
  const scenes: Array<[string, string, string]> = [
    // label, source, the block's first characters (the point)
    ["R10 a fence item, then an item that is a table of formulas alone", "- ```\n  code\n  ```\n- | $x$ |\n  |---|\n  | $y$ |\n", "| $x$"],
    ["R11 a table item, then an item that is a table of formulas alone", "- | a |\n  |---|\n  | b |\n- | $x$ |\n  |---|\n  | $y$ |\n", "| $x$"],
    ["R5 a prose item, then a table whose first cell is an entity, the per-cell fallback's hole", "- Item one\n- | &amp; | b |\n  |---|---|\n  | c | d |\n", "| &amp;"],
    ["R1 a prose item, then a table of formulas alone, the last item", "- Item one\n- | $x$ |\n  |---|\n  | $y$ |\n", "| $x$"],
    ["R2 a prose item, then a table of formulas alone, an item after", "- Item one\n- | $x$ |\n  |---|\n  | $y$ |\n- Item three\n", "| $x$"],
    ["R6 a prose item, then a fence of one blank line, the last item", "- Item one\n- ```\n  \n  ```\n", "```"],
    ["R7 a prose item, then a fence of one blank line, an item after", "- Item one\n- ```\n  \n  ```\n- Item three\n", "```"],
    ["S3 a prose item, then a table of pictures alone", "- aaa\n- | ![p](p.png) |\n  |---|\n  | ![q](q.png) |\n", "| !["],
    ["S4 a prose item, then an empty fence, an item after", "- Item one\n- ```\n  ```\n- Item three\n", "```"],
  ];
  for (const [label, src, first] of scenes) {
    const box = buildRendered(src);
    assert.equal(placeOf(box, src, at(src, first)), null, label + ": card-only (before: painted in another item)");
  }
  // the blank line's own point, with rows: in the fence's pre, its one row (blankCodeLineSpot's pairing by order, round 2)
  for (const src of ["- Item one\n- ```\n  \n  ```\n", "- Item one\n- ```\n  \n  ```\n- Item three\n"]) {
    const off = at(src, "```\n  \n") + 6;   // the blank line's line feed, after its two spaces
    assert.equal(src.slice(off - 3, off + 1), "\n  \n");
    const w = placeOf(buildRendered(src), src, off);
    assert.deepEqual([w!.li, w!.pre], [1, 0], "the blank line's point in the fence's own pre, item 2: " + JSON.stringify(w));
  }
  // the controls
  const c3 = "- aaa\n- bbb\n\n  | $x$ |\n  |---|\n  | $y$ |\n";
  const w3 = placeOf(buildRendered(c3), c3, at(c3, "| $x$"));
  assert.deepEqual([w3!.li, w3!.cell, w3!.before], [1, null, "bbb"], "the same item's text before a table of formulas alone: after that text, as before");
  const c4 = "- Item one\n- | c |\n  |---|\n  | d |\n";
  const w4 = placeOf(buildRendered(c4), c4, at(c4, "| c |"));
  assert.deepEqual([w4!.li, w4!.cell && w4!.cell.tag, w4!.after], [1, "TH", "c d"], "a positioned table beginning an item: before its first cell's first character (round 4)");
  const c5 = "- Item one\n- ```\n  code\n  ```\n";
  const w5 = placeOf(buildRendered(c5), c5, at(c5, "```"));
  assert.deepEqual([w5!.li, w5!.pre, w5!.after.startsWith("code")], [1, 0, true], "a fence with code beginning an item: before the code's first character (round 4)");
  for (const src of ["Intro\n\n| $x$ |\n|---|\n| $y$ |\n\nAfter\n", "Intro\n\n```\n\n```\n\nAfter\n"]) assert.equal(placeOf(buildRendered(src), src, at(src, src.includes("|") ? "| $x$" : "```")), null, "the top-level twin keeps its card, as before");
});

test("a deletion point at a table's first character whose FIRST header cell shows nothing (a formula alone, a picture alone, an empty cell) keeps its card (the review's round 5; before: placed before the table's first POSITIONED character, inside the second header cell or the body row's first cell, a cell the change is not in; main 696229f84: card-only, the table a hole): a two-column table with a formula first, a one-column table with a formula header, two table items with the second's first header cell a formula, a picture first, both header cells pictures, an empty first cell, and an entity first cell (the per-cell fallback's hole, card-only before too); the controls: a positioned first cell places before it, the same item's text before such a table places after that text, and a point inside the second header cell places in it", () => {
  const scenes: Array<[string, string, string]> = [
    ["P1 a formula-first header cell, top level", "Intro\n\n| $x$ | b |\n|---|---|\n| c | d |\n\nAfter\n", "| $x$"],
    ["P10 a one-column table, the header a formula", "Intro\n\n| $x$ |\n|---|\n| c |\n\nAfter\n", "| $x$"],
    ["P3 two table items, the second's first header cell a formula", "- | a | b |\n  |---|---|\n  | c | d |\n- | $x$ | c |\n  |---|---|\n  | e | f |\n", "| $x$"],
    ["a picture-first header cell", "| ![p](x.png) | b |\n|---|---|\n| c | d |\n", "| !["],
    ["both header cells pictures", "| ![p](x.png) | ![q](y.png) |\n|---|---|\n| ph-a | ph-b |\n", "| !["],
    ["an empty first header cell", "|  | b |\n|---|---|\n| c | d |\n", "|  |"],
    ["an entity first header cell, the per-cell fallback's hole", "| &amp; | b |\n|---|---|\n| c | d |\n", "| &amp;"],
  ];
  for (const [label, src, first] of scenes) assert.equal(placeOf(buildRendered(src), src, at(src, first)), null, label + ": card-only (before: before the table's first positioned character, in another cell)");
  const c1 = "Intro\n\n| a | b |\n|---|---|\n| c | d |\n\nAfter\n";
  const w1 = placeOf(buildRendered(c1), c1, at(c1, "| a |"));
  assert.deepEqual([w1!.cell, w1!.after.startsWith("a")], [{ tag: "TH", col: 0, row: -1 }, true], "a positioned first header cell: before its first character, round 2's rule");
  const c2 = "- text\n\n  | $x$ | b |\n  |---|---|\n  | c | d |\n";
  const w2 = placeOf(buildRendered(c2), c2, at(c2, "| $x$"));
  assert.deepEqual([w2!.li, w2!.cell, w2!.before], [0, null, "text"], "the same item's text before a formula-first table: after that text, as before");
  const c3 = "Intro\n\n| $x$ | b |\n|---|---|\n| c | d |\n\nAfter\n";
  const w3 = placeOf(buildRendered(c3), c3, at(c3, "b |"));
  assert.deepEqual([w3!.cell, w3!.after.startsWith("b")], [{ tag: "TH", col: 1, row: -1 }, true], "a point inside the second header cell: in that cell, as before");
});

// ── item 1: a cell the per-cell fallback holds keeps its edge points on the card (round 4's rule, pinned) ──

test("a cell the per-cell fallback holds (an entity): a deletion point at its first position or its last keeps its card, as a point strictly inside does (the review's round 4, read from the code then and pinned here in round 5: round 3 placed the first after the previous cell's last character and the last before the next cell's first, cells the change is not in), in a body row's first cell, in the header's first cell, in the table's last cell with no final line feed, in a list item's table's last cell, and in two entity cells of one column; the positioned cells beside them place in their own cells, the controls", () => {
  const A = "| H0 | A0 | B0 |\n|---|---|---|\n| x\\y &amp; | pa0 | pb0 |\n| ra0 | rb0 | rc0 |\n";
  const hole = "x\\y &amp;", hs = at(A, hole), he = hs + hole.length;
  const box = buildRendered(A);
  assert.deepEqual(allOf(box, "TD").slice(0, 3).map((t) => t.textContent), ["x\\y &", "pa0", "pb0"], "the entity cell shows its character, the fallback's text");
  const r = paintChangesRendered(El(box), A, [del("start", hs), del("inside", at(A, "&amp;")), del("end", he), del("pa0", at(A, "pa0")), del("B0-end", at(A, "B0") + 2)], () => ({}));
  assert.deepEqual(r, { painted: ["pa0", "B0-end"], unpainted: ["start", "inside", "end"] }, "the hole cell's first and last positions keep their cards with its inside (round 3: the first after `B0`, the last before `pa0`); the positioned cells' points place");
  assert.deepEqual([locate(box, "pa0")!.cell, locate(box, "pa0")!.after.startsWith("pa0")], [{ tag: "TD", col: 1, row: 0 }, true], "before `pa0` in its own cell");
  assert.deepEqual([locate(box, "B0-end")!.cell, locate(box, "B0-end")!.before.endsWith("B0")], [{ tag: "TH", col: 2, row: -1 }, true], "after `B0` in its own cell");
  const more: Array<[string, string, string, boolean]> = [
    // label, source, the hole cell's text, whether the point is at its end (else its start)
    ["the header's first cell, its end (round 3: before `A`)", "Lead.\n\n| &amp; H | A |\n|---|---|\n| a | b |\n\nTail.\n", "&amp; H", true],
    ["the table's last cell with no final line feed, its start (round 3: after `a`)", "| H | A |\n|---|---|\n| a | z &amp; |", "z &amp;", false],
    ["a list item's table's last cell, its start (round 3: after `1`)", "- Item one\n\n  | a | b |\n  |---|---|\n  | 1 | e &amp; |\n\n  after table\n", "e &amp;", false],
    ["the first of two entity cells in one column, its start (round 3: after `A`)", "| H | A |\n|---|---|\n| d1 &amp; | pa |\n| d2 &amp; | pb |\n", "d1 &amp;", false],
    ["the second of two entity cells in one column, its start (round 3: after `pa`)", "| H | A |\n|---|---|\n| d1 &amp; | pa |\n| d2 &amp; | pb |\n", "d2 &amp;", false],
  ];
  for (const [label, src, text, end] of more) assert.equal(placeOf(buildRendered(src), src, at(src, text) + (end ? text.length : 0)), null, label + ": card-only");
});
