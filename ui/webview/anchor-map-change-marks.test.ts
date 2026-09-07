// Two properties of anchor-map.ts's change painters (plans/file-review.md Slice 2), driven over the
// viewer's two DOM shapes the way anchor-map.test.ts drives them: the Raw rows are file-view.ts's
// `.fv-cl > .fv-ct` split, the Rendered body is marked's output under the viewer's configuration, both
// parsed into a small structural stand-in (there is no jsdom in this tree).
//
//   1. The author chip. The plan's Raw view marks each change "with the author's session chip in the
//      session's color" (the `▍web` beside the marked text). The chip is generated content, like the
//      deletion's struck label: the LAST element painted for a change carries `data-fc-chip="<label>"`,
//      one per change, after its text, and no text node or extra element enters a row.
//   2. The Rendered fallback's occurrence. Inside a refused block (a table, a code fence, an HTML block)
//      a change is re-found by its text; a change's text is short and such blocks repeat tokens, so the
//      first occurrence is not the changed one. The painter takes the range's ordinal among the source's
//      own occurrences, when the rendering shows the text as many times as the source holds it, and
//      paints nothing otherwise (the change keeps its card and Reveal), never the wrong passage.
//
// Fixtures are synthetic (the notes-api world).
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import {
  mapRawSelection, paintRendered, paintChangesRaw, paintChangesRendered, unpaintChanges, chipLabel,
  type ChangePaint, type SelLike,
} from "./anchor-map";

// ── the viewer's marked configuration (file-view.ts; pinned by anchor-map.test.ts) ────────────────
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
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
    return e in NAMED ? NAMED[e] : m;
  });
}
/** The fragment parser a browser's innerHTML applies, reduced to what marked emits (anchor-map.test.ts's). */
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
const escapeHtml = (s: string): string => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
/** The viewer's Raw rows for a plain-text file (no highlighter): one `.fv-cl > .fv-ct` per line. */
function buildRaw(text: string): FakeElement {
  const doc = new FakeDocument();
  const lines = text.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  const code = doc.createElement("code"); code.setAttribute("class", "hljs");
  for (const n of parseHTML(doc, lines.map((ln) => `<span class="fv-cl"><span class="fv-ct">${escapeHtml(ln)}</span></span>`).join(""))) code.appendChild(n);
  return code;
}
/** The viewer's Rendered body: `div.fileview-md > marked output`. */
function buildRendered(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);
  return box;
}
const El = (n: FakeNode) => n as unknown as Element;

// ── helpers ────────────────────────────────────────────────────────────────────────────────────────
/** A structural serialization: every text node its own `#"..."`, every attribute shown. */
function serialize(n: FakeNode): string {
  if (n.nodeType === 3) return "#" + JSON.stringify((n as FakeText).data);
  const e = n as FakeElement;
  const attrs = [...e.attrs.entries()].sort().map(([k, v]) => ` ${k}=${JSON.stringify(v)}`).join("");
  return `<${e.tagName}${attrs}>` + e.childNodes.map(serialize).join("") + `</${e.tagName}>`;
}
const docOrder = (root: FakeNode): FakeNode[] => { const out: FakeNode[] = []; const visit = (n: FakeNode) => { out.push(n); n.childNodes.forEach(visit); }; visit(root); return out; };
const elements = (root: FakeNode): FakeElement[] => docOrder(root).filter((n) => n.nodeType === 1) as FakeElement[];
const withClass = (root: FakeNode, cls: string): FakeElement[] => elements(root).filter((e) => (e.getAttribute("class") || "").split(" ").includes(cls));
const withAttr = (root: FakeNode, name: string): FakeElement[] => elements(root).filter((e) => e.attrs.has(name));
const isRow = (el: FakeElement) => (el.getAttribute("class") || "").split(" ").includes("fv-cl");
const rowOf = (n: FakeNode): FakeElement | null => { let p: FakeNode | null = n; while (p) { if (p.nodeType === 1 && isRow(p as FakeElement)) return p as FakeElement; p = p.parentNode; } return null; };
/** The rows' text, in order: what every Raw walk reads as the file. */
function rowText(root: FakeNode): string {
  let out = "";
  const visit = (n: FakeNode, inRow: boolean) => {
    if (n.nodeType === 3) { if (inRow) out += (n as FakeText).data; return; }
    const here = inRow || isRow(n as FakeElement);
    for (const c of n.childNodes) visit(c, here);
  };
  visit(root, false);
  return out;
}
/** The text under `root` before `target` in document order. */
function textBefore(root: FakeNode, target: FakeNode): string {
  let out = ""; let done = false;
  const visit = (n: FakeNode) => {
    if (done || n === target) { done = true; return; }
    if (n.nodeType === 3) { out += (n as FakeText).data; return; }
    for (const c of n.childNodes) visit(c);
  };
  visit(root);
  return out;
}
/** The nearest ancestor with `tag`, and its index among same-tag siblings (the cell's column). */
function cellOf(n: FakeNode, tag: string): { el: FakeElement; index: number } {
  let p: FakeNode | null = n;
  while (p && !(p.nodeType === 1 && (p as FakeElement).tagName === tag)) p = p.parentNode;
  assert.ok(p, "inside a " + tag);
  const el = p as FakeElement;
  const sibs = (el.parentNode as FakeElement).childNodes.filter((c) => c.nodeType === 1 && (c as FakeElement).tagName === tag);
  return { el, index: sibs.indexOf(el) };
}
const sel = (a: FakeNode, ao: number, f: FakeNode, fo: number): SelLike =>
  ({ anchorNode: a as unknown as Node, anchorOffset: ao, focusNode: f as unknown as Node, focusOffset: fo, isCollapsed: a === f && ao === fo });
const at = (source: string, s: string, from = 0): number => { const i = source.indexOf(s, from); assert.ok(i >= 0, "source has " + JSON.stringify(s)); return i; };
const COLORS: Record<string, string> = { web: "rgb(10, 20, 30)" };   // api has no live match: no colour (the plan's Risks entry)
const stylesFor = (c: ChangePaint): Record<string, string> => (COLORS[c.author] ? { "--fc-author": COLORS[c.author] } : {});
const ins = (id: string, author: string, source: string, from: number, newText: string, extra: Partial<ChangePaint> = {}): ChangePaint =>
  ({ id, kind: "ins", curFrom: from, curTo: from + newText.length, oldText: "", author, newText, ...extra });

// ── 1. the author chip ─────────────────────────────────────────────────────────────────────────────

test("Raw: the last element of each change carries the author's chip label — one per change, after its text, for an insertion across rows, a deletion's point and a substitution; two authors stay told apart with no colour for either", () => {
  const source = "alpha beta gamma\ndelta epsilon\nzeta\n";
  const code = buildRaw(source);
  const before = serialize(code);
  const text = rowText(code);
  const insNew = "beta gamma\ndelta";
  const changes: ChangePaint[] = [
    ins("c-ins", "web", source, at(source, insNew), insNew),
    { id: "c-sub", kind: "sub", curFrom: at(source, "epsilon"), curTo: at(source, "epsilon") + 7, oldText: "eps", author: "api", newText: "epsilon" },
    { id: "c-del", kind: "del", curFrom: at(source, "zeta"), curTo: at(source, "zeta"), oldText: "eta ", author: "api" },
  ];
  const painted = paintChangesRaw(El(code), source, changes, stylesFor) as unknown as FakeElement[];
  assert.equal(rowText(code), text, "no text node enters a row: the chip is an attribute");
  assert.equal(withAttr(code, "data-fc-chip").length, 3, "one chip per change");
  const order = docOrder(code);
  for (const c of changes) {
    const mine = painted.filter((m) => m.getAttribute("data-id") === c.id);
    assert.ok(mine.length >= 1, c.id + " painted");
    const chipped = mine.filter((m) => m.attrs.has("data-fc-chip"));
    assert.equal(chipped.length, 1, c.id + ": exactly one of its elements carries the chip");
    const last = mine.reduce((a, b) => (order.indexOf(a) > order.indexOf(b) ? a : b));
    assert.equal(chipped[0], last, c.id + ": the chip sits on the change's LAST element, after its text");
    assert.equal(chipped[0].getAttribute("data-fc-chip"), c.author, c.id + ": the chip reads the sidecar's author");
    for (const m of mine) {
      assert.equal(m.getAttribute("data-author"), c.author, "data-author stays on every element");
      assert.ok(!m.attrs.has("data-act") || m.getAttribute("data-act") === "fcchange");
    }
  }
  // the insertion crossed a row: two marks, the chip on the second row's slice
  const insMarks = painted.filter((m) => m.getAttribute("data-id") === "c-ins");
  assert.equal(insMarks.length, 2);
  assert.notEqual(rowOf(insMarks[0]), rowOf(insMarks[1]));
  assert.ok(!insMarks[0].attrs.has("data-fc-chip") && insMarks[1].attrs.has("data-fc-chip"));
  assert.equal(insMarks[1].textContent, "delta");
  // the substitution: the struck point first, unchipped; the new text's mark carries the chip
  const sub = painted.filter((m) => m.getAttribute("data-id") === "c-sub");
  assert.deepEqual(sub.map((m) => m.getAttribute("class")), ["fc-del", "fc-ins"]);
  assert.ok(!sub[0].attrs.has("data-fc-chip") && sub[1].attrs.has("data-fc-chip"));
  // the deletion: its point is its only element, so the chip rides the point beside the struck label
  const del = painted.filter((m) => m.getAttribute("data-id") === "c-del");
  assert.equal(del.length, 1);
  assert.equal(del[0].getAttribute("class"), "fc-del");
  assert.equal(del[0].getAttribute("data-fc-text"), "eta ");
  assert.equal(del[0].getAttribute("data-fc-chip"), "api");
  // the finding's scenario: api has no colour match, so its marks carry no style — the chip still names it,
  // and web's marks are told apart by their label, not only by an underline hue
  for (const m of [...sub, ...del]) assert.equal(m.getAttribute("style"), null, "no colour for an author with no live match");
  for (const m of insMarks) assert.equal(m.getAttribute("style"), "--fc-author: " + COLORS.web + ";");
  assert.deepEqual(withAttr(code, "data-fc-chip").map((m) => m.getAttribute("data-fc-chip")), ["web", "api", "api"]);
  // no element was added for the chip: every element carrying data-act is a mark or a point
  const controls = elements(code).filter((e) => e.attrs.has("data-act"));
  assert.equal(controls.length, painted.length);
  for (const e of controls) assert.ok(["fc-ins", "fc-del"].includes(e.getAttribute("class") || ""), "a chip is never a control of its own");
  // the Raw walks stay exact over the painted rows, chips and all: a selection over the insertion maps to it
  const t1 = insMarks[0].childNodes[0] as FakeText, t2 = insMarks[1].childNodes[0] as FakeText;
  const r = mapRawSelection(sel(t1, 0, t2, t2.data.length), El(code), source);
  assert.equal(r.ok, true, "expected ok: " + JSON.stringify(r));
  if (r.ok) { assert.deepEqual(r.range, { start: 6, end: 22 }); assert.equal(r.quote, insNew); }
  // unpaint leaves nothing behind, chip attributes included
  unpaintChanges(El(code));
  assert.equal(serialize(code), before);
  assert.equal(withAttr(code, "data-fc-chip").length, 0);
});

test("the chip's label: the caller's label (the session's current name) over the sidecar's author, else the neutral word", () => {
  const base: ChangePaint = { id: "x", kind: "ins", curFrom: 0, curTo: 5, oldText: "", author: "web" };
  assert.equal(chipLabel(base), "web");
  assert.equal(chipLabel({ ...base, label: "web-2" }), "web-2", "a renamed session reads its current name");
  assert.equal(chipLabel({ ...base, label: "" }), "web", "an empty label is no label");
  assert.equal(chipLabel({ ...base, author: "" }), "unknown", "the panel's own fallback for a sidecar with no author");
  const source = "alpha beta\n";
  const code = buildRaw(source);
  const marks = paintChangesRaw(El(code), source, [
    ins("l1", "web", source, 0, "alpha", { label: "web-2" }),
    ins("l2", "api", source, 6, "beta"),
  ], stylesFor) as unknown as FakeElement[];
  assert.deepEqual(marks.map((m) => m.getAttribute("data-fc-chip")), ["web-2", "api"]);
  assert.deepEqual(marks.map((m) => m.getAttribute("data-author")), ["web", "api"], "data-author is the sidecar's label either way");
});

test("Rendered marks carry no chip: the plan gives the author chip to the Raw view", () => {
  const source = "# Latency\n\nThe api session cut p95 latency by 40%.\n";
  const box = buildRendered(source);
  const res = paintChangesRendered(El(box), source, [ins("r1", "web", source, at(source, "cut p95 latency"), "cut p95 latency")], stylesFor);
  assert.deepEqual(res, { painted: ["r1"], unpainted: [] });
  assert.equal(withClass(box, "fc-ins").length, 1);
  assert.equal(withAttr(box, "data-fc-chip").length, 0);
});

// ── 2. the Rendered fallback's occurrence ──────────────────────────────────────────────────────────

const TABLE = "# Latency\n\n| before | after |\n|---|---|\n| 10% | 10% |\n";

test("Rendered fallback: a repeated token in a table marks the changed cell — the second when the change is there, the first when it is there — for an insertion and a substitution; the reported paint is the right cell", () => {
  const second = TABLE.lastIndexOf("10%"), first = TABLE.indexOf("10%");
  assert.equal(second, 48); assert.equal(first, 42);
  for (const [label, change, want] of [
    ["ins in the second cell", ins("c", "web", TABLE, second, "10%"), 1],
    ["ins in the first cell", ins("c", "web", TABLE, first, "10%"), 0],
    ["sub in the second cell", { id: "c", kind: "sub", curFrom: second, curTo: second + 3, oldText: "8%", author: "web", newText: "10%" } as ChangePaint, 1],
  ] as [string, ChangePaint, number][]) {
    const box = buildRendered(TABLE);
    const before = serialize(box);
    const res = paintChangesRendered(El(box), TABLE, [change], stylesFor);
    assert.deepEqual(res, { painted: ["c"], unpainted: [] }, label);
    const marks = withClass(box, "fc-ins");
    assert.equal(marks.length, 1, label + ": one mark");
    assert.equal(marks[0].textContent, "10%");
    const cell = cellOf(marks[0], "TD");
    assert.equal(cell.index, want, label + ": the mark is in the changed cell, not the first occurrence");
    assert.equal(cell.el.textContent, "10%", "the whole cell is the token");
    unpaintChanges(El(box));
    assert.equal(serialize(box), before);
  }
});

test("Rendered fallback: a repeated token in a code fence marks the changed line, for a change and for a comment highlight; a leading blank in the changed text does not shift the count", () => {
  const source = "```\nretries = 3\ntimeout = 3\n```\n";
  const second = source.lastIndexOf("3"), first = source.indexOf("3");
  const box = buildRendered(source);
  const res = paintChangesRendered(El(box), source, [ins("c", "web", source, second, "3")], stylesFor);
  assert.deepEqual(res, { painted: ["c"], unpainted: [] });
  let marks = withClass(box, "fc-ins");
  assert.equal(marks.length, 1);
  assert.equal(textBefore(box, marks[0]), "retries = 3\ntimeout = ", "the second line's 3, not the first");
  unpaintChanges(El(box));
  // a comment (Slice 1) anchored on the first line's 3 paints the first
  const hl = paintRendered(El(box), source, { start: first, end: first + 1 }, "fc-hl", { id: "k1" }) as unknown as FakeElement[] | null;
  assert.ok(hl && hl.length === 1);
  assert.equal(textBefore(box, hl![0]), "retries = ");
  // the raw text of a change may begin with a blank (an insertion of " y" after "x"): the match starts at its
  // first non-blank, and the ordinal is still the range's
  const tbl = "| a | b |\n|---|---|\n| x y | x y |\n";
  const at2 = tbl.lastIndexOf(" y");
  const box2 = buildRendered(tbl);
  assert.deepEqual(paintChangesRendered(El(box2), tbl, [ins("w", "web", tbl, at2, " y")], stylesFor), { painted: ["w"], unpainted: [] });
  marks = withClass(box2, "fc-ins");
  assert.equal(marks.length, 1);
  assert.equal(cellOf(marks[0], "TD").index, 1);
  assert.equal(marks[0].textContent, "y");
});

test("Rendered fallback: when the rendering shows the text a different number of times than the source holds it, nothing is painted — the change keeps its card, never a mark on the wrong passage", () => {
  // an HTML block whose attribute repeats its text: the page shows one "note", the source holds two
  const source = "# Notes\n\n<div title=\"note\">note</div>\n";
  const attr = source.indexOf("note"), text = source.lastIndexOf("note");
  assert.ok(attr < text);
  for (const [label, from] of [["the visible text", text], ["the attribute", attr]] as [string, number][]) {
    const box = buildRendered(source);
    const before = serialize(box);
    const res = paintChangesRendered(El(box), source, [ins("h", "web", source, from, "note")], stylesFor);
    assert.deepEqual(res, { painted: [], unpainted: ["h"] }, label + ": the counts disagree, so the change is card-only");
    assert.equal(withClass(box, "fc-ins").length, 0);
    assert.equal(serialize(box), before);
  }
  // the same for a comment highlight
  const box = buildRendered(source);
  assert.equal(paintRendered(El(box), source, { start: text, end: text + 4 }, "fc-hl"), null);
  // and the unique case still paints through the fallback (the existing behaviour, a token the block holds once)
  const one = buildRendered(TABLE);
  assert.deepEqual(paintChangesRendered(El(one), TABLE, [ins("u", "web", TABLE, at(TABLE, "after"), "after")], stylesFor), { painted: ["u"], unpainted: [] });
  assert.equal(cellOf(withClass(one, "fc-ins")[0], "TH").index, 1);
});
