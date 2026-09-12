// A deletion point on a code line that shows no character inside a fence whose EVERY line shows none (the Slice 8 review, round 2;
// plans/markdown-viewer.md Slice 8, item 4). Round 1 put a blank line's point into the line's own `.cl` row, finding the row from
// the nearest line of the same block that shows a character; a fence of one blank line (```\n\n```), or of whitespace-only lines,
// has no such line, so the point kept its card and the card offered Reveal while the pre showed the row and the Raw view placed the
// point on it. Now marked's empty text for the one-blank-line fence is told from the empty fence's by the raw (codeLineStarts), and
// a code block with no shown character finds its pre by ORDER, the block's k-th <pre> for its k-th code block (Block.codes records
// every code token in walk order; blankCodeLineSpot), and its row by index. Driven over the viewer's Rendered shape rebuilt as
// anchor-map-code-lines.test.ts rebuilds it: marked's output parsed into the DOM stand-in, every fence cut into `.cl` rows by the
// viewer's own wrapLinesHtml (no highlighter: these fences hold no glyph), the Copy button parked in the pre, the math fill stood
// in for so the belt's `pre` can make a block's pre count disagree. Fails before over d8a55bb7e at the one-blank-line fence's point
// (unpainted there). Synthetic values only: invented notes, no real session text.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { wrapLinesHtml } from "./code-block";
import { paintChangesRendered, unpaintChanges, type ChangePaint } from "./anchor-map";
import { hideEdges } from "../test-dom-shim";

applyMdConfig();

// ── a DOM stand-in: the structural surface anchor-map.ts walks, plus an HTML fragment parser (anchor-map-code-lines.test.ts's) ──
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
/** The fill's result stood in for (math.ts renderMathPlaceholders): a display formula's placeholder becomes `.katex-display > .katex`
 *  holding the glyphs; one whose TeX carries `\HUGE` becomes the belt's shape, `code.md-math-src` inside a `pre` the viewer then
 *  dresses with its Copy button (anchor-map-obsidian.test.ts's stand-in), a `<pre>` no code token emitted. */
function standInFill(root: FakeElement): void {
  for (const c of root.childNodes.slice()) {
    if (c.nodeType !== 1) continue;
    const el = c as FakeElement;
    const cls = el.getAttribute("class") || "";
    if (cls === "md-math-inline" || cls === "md-math-display") {
      const doc = el.ownerDocument, tex = el.textContent;
      let repl: FakeElement;
      if (tex.includes("\\HUGE")) {
        const code = doc.createElement("code"); code.setAttribute("class", "md-math-src"); code.appendChild(doc.createTextNode(tex));
        repl = doc.createElement("pre"); repl.setAttribute("class", "has-copy"); repl.appendChild(code);
      } else {
        const katex = doc.createElement("span"); katex.setAttribute("class", "katex");
        katex.appendChild(doc.createTextNode(tex.replace(/[\\^_{}]/g, "")));
        repl = katex;
        if (cls === "md-math-display") { repl = doc.createElement("span"); repl.setAttribute("class", "katex-display"); repl.appendChild(katex); }
      }
      root.replaceChild(repl, el);
    } else standInFill(el);
  }
}
/** mdBlock's dress of every fence (file-view.ts): cut into `.cl` rows by wrapLinesHtml (code-block.ts) with the line feeds dropped,
 *  the Copy button parked as the `<pre>`'s last child. No highlighter: the fences here show no glyph. */
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
/** `.fileview-md > marked output`, filled and dressed as the viewer's body is. */
function buildRendered(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);
  standInFill(box);
  dressCode(box);
  return box;
}
/** The same body with no fence dressed: a pre no renderer cut into rows. */
function undressed(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);
  return box;
}
const El = (n: FakeNode) => n as unknown as Element;
const allOf = (root: FakeNode, tag: string, out: FakeElement[] = []): FakeElement[] => { for (const c of root.childNodes) { if (c instanceof FakeElement) { if (c.tagName === tag) out.push(c); allOf(c, tag, out); } } return out; };
const hasClass = (n: FakeNode, cls: string): boolean => n instanceof FakeElement && (n.getAttribute("class") || "").split(" ").includes(cls);
const rowsOf = (pre: FakeElement): FakeElement[] => { const code = pre.childNodes.find((c) => c instanceof FakeElement && c.tagName === "CODE") as FakeElement; return code.childNodes.filter((c) => hasClass(c, "cl")) as FakeElement[]; };
const rowTexts = (pre: FakeElement): string[] => rowsOf(pre).map((r) => r.textContent);
/** The pre a point sits in and its row's index there, or null when the point is in no row. */
const placeOf = (box: FakeElement, pt: FakeNode): { pre: number; row: number } | null => {
  let p: FakeNode | null = pt;
  while (p && !hasClass(p, "cl")) p = p.parentNode;
  if (!p) return null;
  let pre: FakeNode | null = p;
  while (pre && !(pre instanceof FakeElement && pre.tagName === "PRE")) pre = pre.parentNode;
  return { pre: allOf(box, "PRE").indexOf(pre as FakeElement), row: rowsOf(pre as FakeElement).indexOf(p as FakeElement) };
};
/** The row text before and after a point inside a row cell. */
const around = (pt: FakeElement): [string, string] => {
  const cell = pt.parentNode as FakeElement;
  const i = cell.childNodes.indexOf(pt);
  return [cell.childNodes.slice(0, i).map((n) => n.textContent).join(""), cell.childNodes.slice(i + 1).map((n) => n.textContent).join("")];
};
const pointOf = (box: FakeElement, id: string): FakeElement => { const x = allOf(box, "SPAN").find((x) => hasClass(x, "fc-del") && x.getAttribute("data-id") === id); assert.ok(x, id + " painted"); return x!; };
const del = (id: string, curFrom: number): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText: "gone", author: "web" });
const at = (src: string, s: string, k = 0): number => { let i = -1; for (let n = 0; n <= k; n++) { i = src.indexOf(s, i + 1); assert.ok(i >= 0, "in the source: " + s); } return i; };

test("a deletion point on the one blank line of a fence (```, a blank line, ```) places in the pre's one row, the empty cell holding the point alone; the opener's second backtick and the closer keep their cards (the fence lines render nothing); the empty fence (```, ```), which marked's text does not tell from it, still takes no point anywhere (before: the one-blank-line fence had no line to place either, and its point kept its card while the Raw view put it on the line)", () => {
  const src = "Intro.\n\n```\n\n```\n\nAfter.\n";
  const box = buildRendered(src);
  const pre = allOf(box, "PRE")[0];
  assert.deepEqual(rowTexts(pre), [""], "the viewer's one row for the blank line");
  const open = at(src, "```"), blank = open + 4, closer = at(src, "```", 1);
  assert.equal(src[blank], "\n", "the blank line is its line feed alone");
  const res = paintChangesRendered(El(box), src, [del("blank", blank), del("in-open", open + 1), del("closer", closer), del("in-close", closer + 1), del("prose", at(src, "After."))], () => ({}));
  assert.deepEqual(res, { painted: ["blank", "prose"], unpainted: ["in-open", "closer", "in-close"] }, "the blank line's point places (before: unpainted); the fence lines keep their cards");
  const pt = pointOf(box, "blank");
  assert.deepEqual(placeOf(box, pt), { pre: 0, row: 0 }, "in the pre's one row");
  assert.ok(hasClass(pt.parentNode!, "ct") && (pt.parentNode as FakeElement).childNodes.length === 1, "the empty cell holds the point alone");
  assert.deepEqual(rowTexts(pre), [""], "the row's text is untouched");
  unpaintChanges(El(box));
  assert.equal(allOf(box, "SPAN").filter((e) => hasClass(e, "fc-del")).length, 0, "unpainted");
  // the empty fence: no content line, one hole over the whole block, no point anywhere, as before
  const empty = "Intro.\n\n```\n```\n\nAfter.\n";
  const eb = buildRendered(empty);
  assert.deepEqual(rowTexts(allOf(eb, "PRE")[0]), [""], "marked's floor: one empty row for the empty fence too");
  const eo = at(empty, "```");
  assert.deepEqual(paintChangesRendered(El(eb), empty, [del("e-open", eo), del("e-lf", eo + 3), del("e-close", at(empty, "```", 1)), del("e-prose", at(empty, "After."))], () => ({})), { painted: ["e-prose"], unpainted: ["e-open", "e-lf", "e-close"] }, "the empty fence takes no point");
});

test("a deletion point on a whitespace-only line of a fence whose lines all show nothing places in the line's own row at its column among the spaces (before: the row was found from a line showing a character, and such a fence has none, so the point kept its card): one line of four spaces at columns 0, 2 and 4; two lines of whitespace each in their own row; a blank line then a whitespace line; a trailing blank line, whose row marked's renderer folds, keeps its card as in every fence; a pre no renderer cut into rows keeps it too", () => {
  const ws = "Intro.\n\n```\n    \n```\n\nAfter.\n";
  const wb = buildRendered(ws);
  assert.deepEqual(rowTexts(allOf(wb, "PRE")[0]), ["    "], "one row of four spaces");
  const w0 = at(ws, "```") + 4;
  assert.equal(ws.slice(w0, w0 + 5), "    \n");
  assert.deepEqual(paintChangesRendered(El(wb), ws, [del("w-0", w0), del("w-2", w0 + 2), del("w-4", w0 + 4)], () => ({})), { painted: ["w-0", "w-2", "w-4"], unpainted: [] });
  for (const id of ["w-0", "w-2", "w-4"]) assert.deepEqual(placeOf(wb, pointOf(wb, id)), { pre: 0, row: 0 }, id + ": in the line's row");
  assert.deepEqual([around(pointOf(wb, "w-0")), around(pointOf(wb, "w-2")), around(pointOf(wb, "w-4"))], [["", "    "], ["  ", "  "], ["    ", ""]], "at their columns");
  unpaintChanges(El(wb));
  // two whitespace lines, each its own row
  const two = "Intro.\n\n```\n    \n  \n```\n\nAfter.\n";
  const tb = buildRendered(two);
  assert.deepEqual(rowTexts(allOf(tb, "PRE")[0]), ["    ", "  "]);
  const t0 = at(two, "```") + 4, t1 = t0 + 5;
  assert.equal(two.slice(t1, t1 + 3), "  \n");
  assert.deepEqual(paintChangesRendered(El(tb), two, [del("a", t0 + 1), del("b", t1 + 1), del("b-end", t1 + 2)], () => ({})), { painted: ["a", "b", "b-end"], unpainted: [] });
  assert.deepEqual([placeOf(tb, pointOf(tb, "a")), placeOf(tb, pointOf(tb, "b")), placeOf(tb, pointOf(tb, "b-end"))], [{ pre: 0, row: 0 }, { pre: 0, row: 1 }, { pre: 0, row: 1 }], "each in its own row");
  assert.deepEqual([around(pointOf(tb, "a")), around(pointOf(tb, "b")), around(pointOf(tb, "b-end"))], [[" ", "   "], [" ", " "], ["  ", ""]]);
  unpaintChanges(El(tb));
  // a blank line then a whitespace line
  const mixed = "Intro.\n\n```\n\n    \n```\n\nAfter.\n";
  const mb = buildRendered(mixed);
  assert.deepEqual(rowTexts(allOf(mb, "PRE")[0]), ["", "    "]);
  const m0 = at(mixed, "```") + 4;
  assert.deepEqual(paintChangesRendered(El(mb), mixed, [del("m-blank", m0), del("m-ws", m0 + 1 + 4)], () => ({})), { painted: ["m-blank", "m-ws"], unpainted: [] });
  assert.deepEqual([placeOf(mb, pointOf(mb, "m-blank")), placeOf(mb, pointOf(mb, "m-ws")), around(pointOf(mb, "m-ws"))], [{ pre: 0, row: 0 }, { pre: 0, row: 1 }, ["    ", ""]]);
  unpaintChanges(El(mb));
  // a whitespace line then a trailing blank line: the renderer folds the trailing line's row, so its point has no row and, the
  // fence showing no character to place it against, keeps its card
  const trail = "Intro.\n\n```\n    \n\n```\n\nAfter.\n";
  const rb = buildRendered(trail);
  assert.deepEqual(rowTexts(allOf(rb, "PRE")[0]), ["    "], "the trailing blank line's row folded");
  const r0 = at(trail, "```") + 4;
  assert.deepEqual(paintChangesRendered(El(rb), trail, [del("r-ws", r0 + 2), del("r-trail", r0 + 5)], () => ({})), { painted: ["r-ws"], unpainted: ["r-trail"] });
  assert.deepEqual([placeOf(rb, pointOf(rb, "r-ws")), around(pointOf(rb, "r-ws"))], [{ pre: 0, row: 0 }, ["  ", "  "]]);
  // undressed: no row to hold the point, no character to place it against
  const ub = undressed(ws);
  assert.equal(rowsOf(allOf(ub, "PRE")[0]).length, 0, "no rows");
  assert.deepEqual(paintChangesRendered(El(ub), ws, [del("u", w0 + 2)], () => ({})), { painted: [], unpainted: ["u"] }, "undressed: the point keeps its card");
});

test("a fence whose lines all show nothing finds its pre by ORDER among the block's (the k-th <pre> under the block's nodes for its k-th code block): in a list item holding such a fence before a fence with text the point goes into the FIRST pre, and after one into the SECOND, each in the right row; a `<pre>` no code token emitted (the fill's belt for a display formula past its bound) makes the count disagree and the point keeps its card rather than land in the wrong pre", () => {
  const before = "- Item:\n\n  ```\n  \n  ```\n\n  between\n\n  ```\n  a = 1\n  b = 2\n  ```\n\n  after\n";
  const bb = buildRendered(before);
  assert.deepEqual(allOf(bb, "PRE").map(rowTexts), [[""], ["a = 1", "b = 2"]], "the item's two pres: the blank fence's one row, the text fence's two");
  // the blank line's line feed: the item's indent before it has no index in the item's view (its text lines are the raw lines'
  // suffixes), so a fence's FIRST line begins, for the map, at its first text index, the line feed of a blank one, and the opener's
  // hole runs to there; a point on that indent keeps its card as one on any first line's indent does (round 1's rule, not this one's)
  const bBlank = at(before, "  ```") + 8;
  assert.equal(before.slice(bBlank - 3, bBlank + 1), "\n  \n");
  assert.deepEqual(paintChangesRendered(El(bb), before, [del("first", bBlank), del("first-indent", bBlank - 2), del("text", at(before, "b = 2") + 1)], () => ({})), { painted: ["first", "text"], unpainted: ["first-indent"] });
  assert.deepEqual([placeOf(bb, pointOf(bb, "first")), placeOf(bb, pointOf(bb, "text"))], [{ pre: 0, row: 0 }, { pre: 1, row: 1 }], "the blank fence's point in the first pre, the control in the second");
  assert.ok(hasClass(pointOf(bb, "first").parentNode!, "ct") && (pointOf(bb, "first").parentNode as FakeElement).childNodes.length === 1, "the empty cell holds the point alone");
  unpaintChanges(El(bb));
  const after = "- Item:\n\n  ```\n  a = 1\n  b = 2\n  ```\n\n  between\n\n  ```\n    \n  ```\n\n  after\n";
  const ab = buildRendered(after);
  assert.deepEqual(allOf(ab, "PRE").map(rowTexts), [["a = 1", "b = 2"], ["  "]], "the text fence first, then the whitespace fence's one row (its line less the item's indent)");
  const aWs = at(after, "  ```", 2) + 6;   // the whitespace line's first character (the third fence line: the first fence's opener and closer come before)
  assert.equal(after.slice(aWs - 1, aWs + 5), "\n    \n");
  assert.deepEqual(paintChangesRendered(El(ab), after, [del("second", aWs + 3), del("text", at(after, "a = 1") + 2)], () => ({})), { painted: ["second", "text"], unpainted: [] });
  assert.deepEqual([placeOf(ab, pointOf(ab, "second")), around(pointOf(ab, "second")), placeOf(ab, pointOf(ab, "text"))], [{ pre: 1, row: 0 }, [" ", " "], { pre: 0, row: 0 }], "the whitespace fence's point in the second pre at its column among the shown spaces");
  unpaintChanges(El(ab));
  // the belt's pre beside the blank fence: two pres, one code block; the count disagrees and the point keeps its card
  const belt = "- Item:\n\n  ```\n  \n  ```\n\n  $$\n  \\HUGE x\n  $$\n";
  const kb = buildRendered(belt);
  const pres = allOf(kb, "PRE");
  assert.equal(pres.length, 2, "the fence's pre and the belt's");
  assert.ok(allOf(pres[1], "CODE").some((c) => hasClass(c, "md-math-src")), "the second pre is the belt's");
  const gBlank = at(belt, "  ```") + 8;
  assert.equal(belt.slice(gBlank - 3, gBlank + 1), "\n  \n", "the blank line's line feed, the offset the scene before placed in the pre");
  assert.deepEqual(paintChangesRendered(El(kb), belt, [del("guard", gBlank)], () => ({})), { painted: ["guard"], unpainted: [] });
  const gp = pointOf(kb, "guard");
  assert.equal(placeOf(kb, gp), null, "the count guard: in no pre's row (the wrong pre would be the belt's)");
  assert.equal((gp.parentNode as FakeElement).textContent, "Item:", "...the caller's rules place it against the nearest character, after the item's text");
});
