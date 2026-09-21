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
// (unpainted there). The review's round 3 added two cases and re-pinned one: a fence the note ends inside right after its
// opener's line feed (raw "```\n") has no content line and its point keeps its card (red over a git archive of 2136fa7d2, where
// round 2's guard read the raw's split artifact as the one-blank-line fence's line and placed the note's end in the pre's row); a
// fence's trailing blank line, whose row marked's renderer folds, goes to the END of the pre's last row (red over 2136fa7d2 with
// the point after `x = 1`, two rows above the rows the blank and whitespace lines between show; the second test's trail scene,
// card-only there, re-pinned to the same row's end). The review's round 4 added the sixth test and re-pinned one point of the
// third: the container's indent or `> ` marker before a fence's FIRST content line is that line's, in its row (red over a git
// archive of 90c6ff242, where the opener's hole ran to the first line's first character past the indent and those bytes kept
// their card while the same bytes before every later line placed in the line's row). Synthetic values only: invented notes, no
// real session text.
import { test } from "node:test";
import assert from "node:assert/strict";
import { viewerHtml } from "./file-view";   // the viewer's parse (mdBlock's recipe: marked's lexer, the literal-tags rule of md-literal-tags.ts, the per-call walk, its parser), the stand-in's too
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
  for (const n of parseHTML(doc, viewerHtml(text))) box.appendChild(n);
  standInFill(box);
  dressCode(box);
  return box;
}
/** The same body with no fence dressed: a pre no renderer cut into rows. */
function undressed(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, viewerHtml(text))) box.appendChild(n);
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

test("a deletion point on a whitespace-only line of a fence whose lines all show nothing places in the line's own row at its column among the spaces (before: the row was found from a line showing a character, and such a fence has none, so the point kept its card): one line of four spaces at columns 0, 2 and 4; two lines of whitespace each in their own row; a blank line then a whitespace line; a trailing blank line, whose row marked's renderer folds, goes to the end of the pre's last row, after the whitespace row's spaces (the review's round 3; before, the fence showing no character to place it against, it kept its card); a pre no renderer cut into rows keeps its card", () => {
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
  // a whitespace line then a trailing blank line: the renderer folds the trailing line's row, so its point goes to the END of the
  // pre's last row, the row nearest the line, after the shown spaces (the review's round 3; before, the fence showing no character
  // to place it against, the point kept its card)
  const trail = "Intro.\n\n```\n    \n\n```\n\nAfter.\n";
  const rb = buildRendered(trail);
  assert.deepEqual(rowTexts(allOf(rb, "PRE")[0]), ["    "], "the trailing blank line's row folded");
  const r0 = at(trail, "```") + 4;
  assert.equal(trail.slice(r0 + 4, r0 + 9), "\n\n```", "r0 + 5 is the trailing blank line, its line feed");
  assert.deepEqual(paintChangesRendered(El(rb), trail, [del("r-ws", r0 + 2), del("r-trail", r0 + 5)], () => ({})), { painted: ["r-ws", "r-trail"], unpainted: [] }, "the trailing line's point places (before: unpainted)");
  assert.deepEqual([placeOf(rb, pointOf(rb, "r-ws")), around(pointOf(rb, "r-ws")), placeOf(rb, pointOf(rb, "r-trail")), around(pointOf(rb, "r-trail"))], [{ pre: 0, row: 0 }, ["  ", "  "], { pre: 0, row: 0 }, ["    ", ""]], "the whitespace line's point at its column, the trailing line's at the end of the same row, the pre's last");
  unpaintChanges(El(rb));
  // undressed: no row to hold the point, no character to place it against
  const ub = undressed(ws);
  assert.equal(rowsOf(allOf(ub, "PRE")[0]).length, 0, "no rows");
  assert.deepEqual(paintChangesRendered(El(ub), ws, [del("u", w0 + 2)], () => ({})), { painted: [], unpainted: ["u"] }, "undressed: the point keeps its card");
});

test("a fence whose lines all show nothing finds its pre by ORDER among the block's (the k-th <pre> under the block's nodes for its k-th code block): in a list item holding such a fence before a fence with text the point goes into the FIRST pre, and after one into the SECOND, each in the right row; a `<pre>` no code token emitted (the fill's belt for a display formula past its bound) makes the count disagree and the point stays out of the belt's pre: the caller's rules place it against the nearest character, after the item's text, as main 696229f84 did for this fence (its hole put no character in the way)", () => {
  const before = "- Item:\n\n  ```\n  \n  ```\n\n  between\n\n  ```\n  a = 1\n  b = 2\n  ```\n\n  after\n";
  const bb = buildRendered(before);
  assert.deepEqual(allOf(bb, "PRE").map(rowTexts), [[""], ["a = 1", "b = 2"]], "the item's two pres: the blank fence's one row, the text fence's two");
  // the blank line's line feed, and the item's indent before it: the indent has no index in the item's view (its text lines are the
  // raw lines' suffixes), and since the review's round 4 the first line runs from the byte after the opener's line feed, so a point
  // on that indent is the line's and goes into its row as one on a later line's indent does (before: the opener's hole ran to the
  // line's first text index, the line feed, and the indent's point kept its card; the sixth test holds the shapes)
  const bBlank = at(before, "  ```") + 8;
  assert.equal(before.slice(bBlank - 3, bBlank + 1), "\n  \n");
  assert.deepEqual(paintChangesRendered(El(bb), before, [del("first", bBlank), del("first-indent", bBlank - 2), del("text", at(before, "b = 2") + 1)], () => ({})), { painted: ["first", "first-indent", "text"], unpainted: [] }, "the indent's point places too (before: unpainted)");
  assert.deepEqual([placeOf(bb, pointOf(bb, "first")), placeOf(bb, pointOf(bb, "first-indent")), placeOf(bb, pointOf(bb, "text"))], [{ pre: 0, row: 0 }, { pre: 0, row: 0 }, { pre: 1, row: 1 }], "the blank fence's point and its indent's in the first pre, the control in the second");
  assert.ok(hasClass(pointOf(bb, "first").parentNode!, "ct") && (pointOf(bb, "first").parentNode as FakeElement).childNodes.length === 2, "the empty cell holds the two points alone");
  unpaintChanges(El(bb));
  const after = "- Item:\n\n  ```\n  a = 1\n  b = 2\n  ```\n\n  between\n\n  ```\n    \n  ```\n\n  after\n";
  const ab = buildRendered(after);
  assert.deepEqual(allOf(ab, "PRE").map(rowTexts), [["a = 1", "b = 2"], ["  "]], "the text fence first, then the whitespace fence's one row (its line less the item's indent)");
  const aWs = at(after, "  ```", 2) + 6;   // the whitespace line's first character (the third fence line: the first fence's opener and closer come before)
  assert.equal(after.slice(aWs - 1, aWs + 5), "\n    \n");
  assert.deepEqual(paintChangesRendered(El(ab), after, [del("second", aWs + 3), del("text", at(after, "a = 1") + 2)], () => ({})), { painted: ["second", "text"], unpainted: [] });
  assert.deepEqual([placeOf(ab, pointOf(ab, "second")), around(pointOf(ab, "second")), placeOf(ab, pointOf(ab, "text"))], [{ pre: 1, row: 0 }, [" ", " "], { pre: 0, row: 0 }], "the whitespace fence's point in the second pre at its column among the shown spaces");
  unpaintChanges(El(ab));
  // the belt's pre beside the blank fence: two pres, one code block; the count disagrees, so the point is not placed by order (the
  // wrong pre would be the belt's) and falls to the caller's nearest-character rule, after the item's text, where main put it too
  // (the review's round 3 corrected this comment and the title, which had said the point keeps its card; the pins below never did)
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

test("a fence the note ends inside right after its opener's line feed (```, end of file) has no content line: the point at the note's end keeps its card as the fence lines' do, although the pre shows marked's one empty row for empty text (the review's round 3; before, round 2's guard read the raw's split artifact after the opener as the one-blank-line fence's line and placed that point in the row); the same with an info string; and the unclosed fence whose one content line is blank (```, a blank line, end of file) keeps the line's point and the end's card-only too, the line being one of the raw's trailing line feeds that ownRows treats as blank lines between blocks (pre-existing on main 696229f84, recorded in the plan's Slice 8 note and routed to a follow-up), so the two unclosed shapes agree while the closed one-blank-line fence places (the first test)", () => {
  for (const [label, src] of [["bare", "Intro.\n\n```\n"], ["info string", "Intro.\n\n```js\n"]] as const) {
    const box = buildRendered(src);
    assert.deepEqual(rowTexts(allOf(box, "PRE")[0]), [""], label + ": marked's floor, one empty row for empty text");
    const open = at(src, "```"), eof = src.length;
    assert.equal(src[eof - 1], "\n", label + ": the opener's line feed ends the note");
    assert.deepEqual(paintChangesRendered(El(box), src, [del("eof", eof), del("in-open", open + 1), del("open-lf", eof - 1), del("prose", at(src, "Intro."))], () => ({})), { painted: ["prose"], unpainted: ["eof", "in-open", "open-lf"] }, label + ": no point in the fence (before: the note's end in the pre's row)");
    unpaintChanges(El(box));
  }
  // the unclosed fence with one blank content line: the pre shows the row and the Raw view puts the point on the line, but the
  // line is one of the raw's trailing line feeds, which Placed strips off the block's text end and ownRows reads as blank lines
  // between blocks, so no block's rows hold the offset and the point keeps its card (the routed edge; pinned as today's behaviour)
  const blank = "Intro.\n\n```\n\n";
  const bb = buildRendered(blank);
  assert.deepEqual(rowTexts(allOf(bb, "PRE")[0]), [""], "one row for the blank line");
  const lf = at(blank, "```") + 4;
  assert.equal(blank.slice(lf - 1), "\n\n", "the blank line's line feed ends the note");
  assert.deepEqual(paintChangesRendered(El(bb), blank, [del("blank", lf), del("eof", blank.length), del("in-open", lf - 3)], () => ({})), { painted: [], unpainted: ["blank", "eof", "in-open"] }, "card-only, the two unclosed shapes agreeing");
});

test("a deletion point on a fence's trailing blank line, whose row marked's renderer folds, goes to the END of the pre's last row when blank or whitespace-only rows stand between the last line that shows a character and it (the review's round 3; before: after the nearest positioned character, two rows above, which read as the first line changed): after the whitespace row's spaces, beside the whitespace line's own point at its column; two trailing blank lines fold to one row and the second's point goes into that empty row with the first's; a fence whose last shown line has text places the trailing line's point after that text, the same row either way; the closer's backtick keeps its card", () => {
  const src = "Intro.\n\n```\nx = 1\n\n    \n\n```\n\nAfter.\n";
  const box = buildRendered(src);
  const pre = allOf(box, "PRE")[0];
  assert.deepEqual(rowTexts(pre), ["x = 1", "", "    "], "three rows: the trailing blank line's folded");
  const o = at(src, "x = 1");
  assert.equal(src.slice(o + 5, o + 14), "\n\n    \n\n`", "the blank line at o + 6, the whitespace line at o + 7 to o + 10, the trailing blank line at o + 12, the closer at o + 13");
  const res = paintChangesRendered(El(box), src, [del("blank", o + 6), del("ws", o + 9), del("trail", o + 12), del("closer", o + 13), del("text", o + 2)], () => ({}));
  assert.deepEqual(res, { painted: ["blank", "ws", "trail", "text"], unpainted: ["closer"] });
  assert.deepEqual(["blank", "ws", "trail", "text"].map((id) => placeOf(box, pointOf(box, id))), [{ pre: 0, row: 1 }, { pre: 0, row: 2 }, { pre: 0, row: 2 }, { pre: 0, row: 0 }], "the trailing line's point in the last row (before: row 0, after `x = 1`)");
  assert.deepEqual([around(pointOf(box, "ws")), around(pointOf(box, "trail"))], [["  ", "  "], ["    ", ""]], "the whitespace line's point at its column, the trailing line's after the row's spaces");
  assert.deepEqual(rowTexts(pre), ["x = 1", "", "    "], "the rows' text is untouched");
  unpaintChanges(El(box));
  // two trailing blank lines: the renderer folds the second's row, so its point goes into the first's, the empty last row
  const two = "Intro.\n\n```\ny = 2\n\n\n```\n";
  const tb = buildRendered(two);
  assert.deepEqual(rowTexts(allOf(tb, "PRE")[0]), ["y = 2", ""], "two rows: the second trailing blank line's folded");
  const y = at(two, "y = 2");
  assert.equal(two.slice(y + 5, y + 9), "\n\n\n`");
  assert.deepEqual(paintChangesRendered(El(tb), two, [del("first", y + 6), del("second", y + 7)], () => ({})), { painted: ["first", "second"], unpainted: [] });
  assert.deepEqual([placeOf(tb, pointOf(tb, "first")), placeOf(tb, pointOf(tb, "second"))], [{ pre: 0, row: 1 }, { pre: 0, row: 1 }], "both in the empty last row");
  assert.ok(hasClass(pointOf(tb, "second").parentNode!, "ct"), "the second's in the row's cell");
  unpaintChanges(El(tb));
  // the last shown line has text: the trailing line's point after it, the last row, as before
  const text = "Intro.\n\n```\nz = 3\n\n```\n";
  const xb = buildRendered(text);
  assert.deepEqual(rowTexts(allOf(xb, "PRE")[0]), ["z = 3"]);
  const z = at(text, "z = 3");
  assert.deepEqual(paintChangesRendered(El(xb), text, [del("t", z + 6)], () => ({})), { painted: ["t"], unpainted: [] });
  assert.deepEqual([placeOf(xb, pointOf(xb, "t")), around(pointOf(xb, "t"))], [{ pre: 0, row: 0 }, ["z = 3", ""]], "after the last character, as before");
});

test("a deletion point on the container's indent, or on a quote's `> ` marker, before a nested fence's FIRST content line places in that line's row, as one before every later line does (the review's round 4; before: those bytes lay strictly inside the opener's hole, whose end was the first line's first character past the indent, and kept their card, so a session's deletion of a blank first line's two spaces kept its card while the same deletion on a blank second line painted in its row, and the Raw view put both on their lines): a list item's fence, the indent before `a = 1` in row 0 before its first character and before a blank first line in the empty row 0; a quote's fence, the `>` and the space before `a = 1` in row 0; the opener's line feed, its backticks and the closer's indent keep their cards as before; the later lines' indent and marker in their own rows as before", () => {
  const S1 = "- item\n\n  ```\n  a = 1\n  b = 2\n  ```\n";
  const b1 = buildRendered(S1);
  assert.deepEqual(rowTexts(allOf(b1, "PRE")[0]), ["a = 1", "b = 2"]);
  const aInd = at(S1, "  a = 1"), bInd = at(S1, "  b = 2"), open1 = at(S1, "```"), close1 = at(S1, "  ```", 1);
  assert.equal(S1[open1 + 3], "\n", "the opener's line feed");
  const r1 = paintChangesRendered(El(b1), S1, [del("a-ind0", aInd), del("a-ind1", aInd + 1), del("a", aInd + 2), del("b-ind0", bInd), del("b-ind1", bInd + 1), del("open-lf", open1 + 3), del("open-tick", open1 + 1), del("close-ind", close1)], () => ({}));
  assert.deepEqual(r1, { painted: ["a-ind0", "a-ind1", "a", "b-ind0", "b-ind1"], unpainted: ["open-lf", "open-tick", "close-ind"] }, "the first line's indent places (before: unpainted); the fence lines and the closer's indent keep their cards");
  assert.deepEqual(["a-ind0", "a-ind1", "a", "b-ind0", "b-ind1"].map((id) => placeOf(b1, pointOf(b1, id))), [{ pre: 0, row: 0 }, { pre: 0, row: 0 }, { pre: 0, row: 0 }, { pre: 0, row: 1 }, { pre: 0, row: 1 }], "the first line's indent in row 0 (before: card-only), the second's in row 1 as before");
  for (const id of ["a-ind0", "a-ind1", "a"]) assert.deepEqual(around(pointOf(b1, id)), ["", "a = 1"], id + ": before the line's first character");
  for (const id of ["b-ind0", "b-ind1"]) assert.deepEqual(around(pointOf(b1, id)), ["", "b = 2"], id + ": before the line's first character");
  unpaintChanges(El(b1));
  const S2 = "- item\n\n  ```\n  \n  b = 2\n  ```\n";
  const b2 = buildRendered(S2);
  assert.deepEqual(rowTexts(allOf(b2, "PRE")[0]), ["", "b = 2"], "the blank first line's row is empty");
  const blankInd = at(S2, "```") + 4;
  assert.equal(S2.slice(blankInd, blankInd + 3), "  \n", "the blank first line: its indent, then its line feed");
  const r2 = paintChangesRendered(El(b2), S2, [del("bl-ind0", blankInd), del("bl-ind1", blankInd + 1), del("bl-lf", blankInd + 2), del("b-ind0", blankInd + 3), del("b-ind1", blankInd + 4)], () => ({}));
  assert.deepEqual(r2, { painted: ["bl-ind0", "bl-ind1", "bl-lf", "b-ind0", "b-ind1"], unpainted: [] }, "the blank first line's indent places (before: unpainted)");
  assert.deepEqual(["bl-ind0", "bl-ind1", "bl-lf", "b-ind0", "b-ind1"].map((id) => placeOf(b2, pointOf(b2, id))), [{ pre: 0, row: 0 }, { pre: 0, row: 0 }, { pre: 0, row: 0 }, { pre: 0, row: 1 }, { pre: 0, row: 1 }], "the blank first line's three bytes in its empty row 0, the second line's indent in row 1");
  assert.ok(hasClass(pointOf(b2, "bl-ind0").parentNode!, "ct") && (pointOf(b2, "bl-ind0").parentNode as FakeElement).childNodes.length === 3, "the empty cell holds the three points alone");
  unpaintChanges(El(b2));
  // the failure scenario: a session strips the blank first line's two spaces
  const hunk: ChangePaint = { id: "strip", kind: "del", curFrom: blankInd, curTo: blankInd, oldText: "  ", author: "web" };
  assert.deepEqual(paintChangesRendered(El(b2), S2, [hunk], () => ({})), { painted: ["strip"], unpainted: [] }, "the deletion of the blank first line's indent paints (before: card-only, while the same hunk on a blank second line painted)");
  assert.deepEqual(placeOf(b2, pointOf(b2, "strip")), { pre: 0, row: 0 });
  unpaintChanges(El(b2));
  const S4 = "> ```\n> a = 1\n> b = 2\n> ```\n";
  const b4 = buildRendered(S4);
  assert.deepEqual(rowTexts(allOf(b4, "PRE")[0]), ["a = 1", "b = 2"]);
  const aMark = at(S4, "> a = 1"), bMark = at(S4, "> b = 2");
  const r4 = paintChangesRendered(El(b4), S4, [del("a-mark", aMark), del("a-space", aMark + 1), del("a", aMark + 2), del("b-mark", bMark), del("b-space", bMark + 1), del("open-lf", aMark - 1), del("open-tick", 3)], () => ({}));
  assert.deepEqual(r4, { painted: ["a-mark", "a-space", "a", "b-mark", "b-space"], unpainted: ["open-lf", "open-tick"] }, "the first line's marker and space place (before: unpainted); the opener's line feed and backticks keep their cards");
  assert.deepEqual(["a-mark", "a-space", "a", "b-mark", "b-space"].map((id) => placeOf(b4, pointOf(b4, id))), [{ pre: 0, row: 0 }, { pre: 0, row: 0 }, { pre: 0, row: 0 }, { pre: 0, row: 1 }, { pre: 0, row: 1 }], "the first line's `> ` in row 0 (before: card-only), the second's in row 1 as before");
  for (const id of ["a-mark", "a-space"]) assert.deepEqual(around(pointOf(b4, id)), ["", "a = 1"], id + ": before the line's first character");
  unpaintChanges(El(b4));
  // the top-level control: the opener's line feed stays card-only, the first line's first character places in row 0
  const S0 = "```\na = 1\nb = 2\n```\n";
  const b0 = buildRendered(S0);
  assert.deepEqual(paintChangesRendered(El(b0), S0, [del("lf", 3), del("a", 4)], () => ({})), { painted: ["a"], unpainted: ["lf"] }, "a top-level fence: the opener's line feed card-only, the first character in the row");
  assert.deepEqual(placeOf(b0, pointOf(b0, "a")), { pre: 0, row: 0 });
  unpaintChanges(El(b0));
});
