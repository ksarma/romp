// Where a change's zero-width point goes when it lands at the edge of another mark, and where a substitution's
// point goes when its tint came through the text-match fallback — two placements the review (2026-09-07) found
// the suite did not pin, both under the plan's rule that the Rendered view paints a change's point "as they do
// in Raw" (plans/file-review.md, the inline-display follow-on). Driven over marked's output under the viewer's
// configuration, parsed into the structural stand-in anchor-map.test.ts uses (there is no jsdom in this tree).
//
//   1. A point at an insertion mark's boundary sits OUTSIDE the mark, in both views and whichever change was
//      painted first. Before the fix, Rendered's "after" placement (renderedSpot) returned the last text node
//      INSIDE a preceding `mark.fc-ins`, and the point became the mark's last child: the struck old text of a
//      deletion right after an insertion wore the insertion's tint and author underline, while Raw, which puts
//      the same offset before the next text node, showed it after the tint. A deletion at the mark's START
//      nested by paint order in both views (insertion first: inside; deletion first: before); both now sit
//      before the mark. At a row's end Raw nested too; it no longer does.
//   2. A comment highlight's edges are boundaries as well (Raw placed a mid-row point after a highlight's end;
//      Rendered now agrees, and both put a point at its start before it), however a change mark and a
//      highlight over the same word nest. A substitution's point stays inside a highlight that covers its
//      tint, immediately before the tint; when the tint begins the highlight, before the highlight.
//   3. Two points at one offset keep their paint order (the hunk order) in both views: a later point goes after
//      the earlier one, as Raw's before-the-next-text-node rule always placed it.
//   4. A substitution whose tint was placed by the text-match fallback (inside a code fence, a table cell — blocks
//      the index map refuses) still gets its point immediately before the tint, and is reported painted: the
//      plan's "wherever the tint was found". Withholding the point inside a refused block left every test
//      green — with the change reported painted, the card would show no "not shown" tag and no Reveal, and the
//      struck old text would be reachable only by opening the card.
//
// Fixtures are synthetic (the notes-api world). The seams use two authors: the engine fuses one author's
// adjacent insertion and deletion into a single substitution, so an `ins` ending where a `del` begins reaches
// the painters only from two sessions.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";   // the one markdown configuration, applied here as the viewer applies it
import { paintChangesRaw, paintChangesRendered, paintRaw, paintRendered, unpaintChanges, type ChangePaint, type SourceRange } from "./anchor-map";

// ── the viewer's marked configuration: the one every bundle applies (md-config.ts; pinned by anchor-map.test.ts) ──
applyMdConfig();

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
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
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
const classes = (e: FakeElement): string[] => (e.getAttribute("class") || "").split(" ");
const withClass = (root: FakeNode, cls: string): FakeElement[] => elements(root).filter((e) => classes(e).includes(cls));
const withTag = (root: FakeNode, tag: string): FakeElement[] => elements(root).filter((e) => e.tagName === tag);
const inside = (n: FakeNode, tag: string): boolean => { let p = n.parentNode; while (p) { if (p.nodeType === 1 && (p as FakeElement).tagName === tag) return true; p = p.parentNode; } return false; };
const at = (source: string, s: string, from = 0): number => { const i = source.indexOf(s, from); assert.ok(i >= 0, "source has " + JSON.stringify(s)); return i; };
const COLORS: Record<string, string> = { web: "rgb(10, 20, 30)", api: "rgb(40, 50, 60)" };
const stylesFor = (c: ChangePaint): Record<string, string> => (COLORS[c.author] ? { "--fc-author": COLORS[c.author] } : {});
const del = (id: string, curFrom: number, oldText: string, author: string): ChangePaint => ({ id, kind: "del", curFrom, curTo: curFrom, oldText, author });
const ins = (id: string, curFrom: number, newText: string, author: string): ChangePaint => ({ id, kind: "ins", curFrom, curTo: curFrom + newText.length, oldText: "", author, newText });
const sub = (id: string, curFrom: number, newText: string, oldText: string, author: string): ChangePaint => ({ id, kind: "sub", curFrom, curTo: curFrom + newText.length, oldText, author, newText });
const point = (root: FakeNode, id: string): FakeElement => { const x = withClass(root, "fc-del").find((m) => m.getAttribute("data-id") === id); assert.ok(x, id + " painted"); return x!; };
const tint = (root: FakeNode, id: string): FakeElement => { const x = withClass(root, "fc-ins").find((m) => m.getAttribute("data-id") === id); assert.ok(x, id + " tinted"); return x!; };
const prev = (n: FakeNode): FakeNode | null => { const p = n.parentNode!; const i = p.childNodes.indexOf(n); return i > 0 ? p.childNodes[i - 1] : null; };
const next = (n: FakeNode): FakeNode | null => { const p = n.parentNode!; const i = p.childNodes.indexOf(n); return i + 1 < p.childNodes.length ? p.childNodes[i + 1] : null; };
/** The one `.fv-ct` text cell of a Raw row. */
const cellOf = (code: FakeElement, row: number): FakeElement => withClass(withClass(code, "fv-cl")[row], "fv-ct")[0];
/** The one paragraph of a rendered body. */
const paraOf = (box: FakeElement): FakeElement => { const ps = withTag(box, "P"); assert.equal(ps.length, 1); return ps[0]; };
/** Where the change marks sit in a container, as one line: text nodes quoted, marks by class and id, nesting kept. */
function shape(n: FakeNode): string {
  if (n.nodeType === 3) return JSON.stringify((n as FakeText).data);
  const e = n as FakeElement;
  const own = classes(e).find((c) => c === "fc-ins" || c === "fc-del" || c === "fc-hl" || c === "fc-presel");
  const inner = e.childNodes.map(shape).join(" ");
  return own ? `[${own}${e.getAttribute("data-id") ? " " + e.getAttribute("data-id") : ""}${inner ? " " + inner : ""}]` : inner;
}
/** Paints `changes` over a fresh Rendered body and a fresh Raw code element of `source`; returns both shapes
 *  (the paragraph's and the row's), asserting every change was painted and both views restore on unpaint. */
function bothViews(source: string, changes: ChangePaint[], row = 0): { rendered: string; raw: string; box: FakeElement; code: FakeElement } {
  const box = buildRendered(source), code = buildRaw(source);
  const b0 = serialize(box), c0 = serialize(code);
  const r = paintChangesRendered(El(box), source, changes, stylesFor);
  assert.deepEqual(r, { painted: changes.map((c) => c.id), unpainted: [] });
  const raw = paintChangesRaw(El(code), source, changes, stylesFor) as unknown as FakeElement[];
  assert.deepEqual([...new Set(raw.map((m) => m.getAttribute("data-id")))], changes.map((c) => c.id));
  const out = { rendered: shape(paraOf(box)), raw: shape(cellOf(code, row)), box, code };
  unpaintChanges(El(box)); unpaintChanges(El(code));
  assert.equal(serialize(box), b0, "Rendered restores"); assert.equal(serialize(code), c0, "Raw restores");
  return out;
}

// ── 1. a point at an insertion mark's boundary sits outside the mark, in both views, either order ──

test("change points at an insertion's END: a deletion right after an insertion (two authors) sits after the insertion's mark as its sibling, in Rendered as in Raw, whether the insertion or the deletion was painted first — never as the mark's last child, where the struck text would wear the insertion's tint", () => {
  const source = "We recommend shipping the cache.\n";
  const i = ins("i", at(source, "shipping"), "shipping", "web");
  const d = del("d", i.curTo, " quickly", "api");
  const want = '"We recommend " [fc-ins i "shipping"] [fc-del d] " the cache."';
  for (const order of [[i, d], [d, i]]) {
    const { rendered, raw } = bothViews(source, order);
    assert.equal(rendered, want, "Rendered, painted " + order.map((c) => c.id).join(" then "));
    assert.equal(raw, want, "Raw, painted " + order.map((c) => c.id).join(" then "));
  }
  // the same, spelled out on the live DOM: the point's parent is the paragraph / the row cell, its previous sibling the mark
  const box = buildRendered(source), code = buildRaw(source);
  paintChangesRendered(El(box), source, [i, d], stylesFor);
  paintChangesRaw(El(code), source, [i, d], stylesFor);
  for (const [view, root, container] of [["Rendered", box, paraOf(box)], ["Raw", code, cellOf(code, 0)]] as const) {
    const p = point(root, "d");
    assert.equal(p.parentNode, container, view + ": the point is not inside any mark");
    assert.equal(prev(p), tint(root, "i"), view + ": right after the insertion's mark");
    assert.equal((next(p) as FakeText).data, " the cache.", view + ": before the text that follows");
    assert.equal(tint(root, "i").childNodes.length, 1, view + ": the mark holds its text and nothing else");
  }
});

test("change points at an insertion's START: a deletion right before an insertion sits before the insertion's mark, in both views, whichever was painted first", () => {
  const source = "We recommend shipping the cache.\n";
  const i = ins("i", at(source, "shipping"), "shipping", "web");
  const d = del("d", i.curFrom, "quickly ", "api");
  const want = '"We recommend " [fc-del d] [fc-ins i "shipping"] " the cache."';
  for (const order of [[i, d], [d, i]]) {
    const { rendered, raw } = bothViews(source, order);
    assert.equal(rendered, want, "Rendered, painted " + order.map((c) => c.id).join(" then "));
    assert.equal(raw, want, "Raw, painted " + order.map((c) => c.id).join(" then "));
  }
});

test("change points at an insertion that ends its line: the deletion after it is the mark's sibling at the row's end in Raw and at the paragraph's end in Rendered, and a deletion inside the insertion still splits the mark", () => {
  const source = "We recommend shipping\n";
  const i = ins("i", at(source, "shipping"), "shipping", "web");
  const end = del("e", i.curTo, " quickly", "api");
  for (const order of [[i, end], [end, i]]) {
    const { rendered, raw } = bothViews(source, order);
    assert.equal(rendered, '"We recommend " [fc-ins i "shipping"] [fc-del e]', "Rendered, painted " + order.map((c) => c.id).join(" then "));
    assert.equal(raw, '"We recommend " [fc-ins i "shipping"] [fc-del e]', "Raw, painted " + order.map((c) => c.id).join(" then "));
  }
  // a point strictly inside the insertion's range is inside its mark: only the edges are outside
  const mid = del("m", at(source, "ping"), "s", "api");
  const { rendered, raw } = bothViews(source, [i, mid]);
  assert.equal(rendered, '"We recommend " [fc-ins i "ship" [fc-del m] "ping"]');
  assert.equal(raw, '"We recommend " [fc-ins i "ship" [fc-del m] "ping"]');
});

// ── 2. a comment highlight's edges are boundaries too, however the marks nest ─────────────────────

test("change points and a comment highlight: a deletion at the highlight's end sits after the highlight in both views, whether a word follows directly (Raw always placed it so) or a space does (the point was the highlight's last child in Rendered); a substitution whose tint begins the highlight has its point before the highlight, one whose tint is inside it keeps its point inside, immediately before the tint, in both views", () => {
  const source = "We recommend shipping the cache.\n";
  const s = sub("s", at(source, "shipping"), "shipping", "sending", "web");
  const cases: [SourceRange, ChangePaint, string][] = [
    // a comment on "recommend shipping": the deletion after it has a space next — the "after" placement, which climbs
    // out of the substitution's mark and then out of the highlight that ends with it; the tint is inside the highlight
    [{ start: at(source, "recommend"), end: s.curTo }, del("d", s.curTo, " quickly", "api"),
     '"We " [fc-hl "recommend " [fc-del s] [fc-ins s "shipping"]] [fc-del d] " the cache."'],
    // a comment on "shipping the cache": the deletion after it has "." next — the "before" placement; the tint begins
    // the highlight, so the substitution's point sits before the highlight
    [{ start: s.curFrom, end: at(source, "cache") + 5 }, del("d", at(source, "cache") + 5, " soon", "api"),
     '"We recommend " [fc-del s] [fc-hl [fc-ins s "shipping"] " the cache"] [fc-del d] "."'],
  ];
  for (const [quote, d, want] of cases) {
    const box = buildRendered(source), code = buildRaw(source);
    assert.ok(paintRendered(El(box), source, quote, "fc-hl"), "the highlight paints");
    paintRaw(El(code), source, quote, "fc-hl");
    const b0 = serialize(box), c0 = serialize(code);
    const r = paintChangesRendered(El(box), source, [s, d], stylesFor);
    assert.deepEqual(r, { painted: ["s", "d"], unpainted: [] });
    paintChangesRaw(El(code), source, [s, d], stylesFor);
    assert.equal(shape(paraOf(box)), want, "Rendered, " + JSON.stringify(source.slice(quote.start, quote.end)));
    assert.equal(shape(cellOf(code, 0)), want, "Raw, " + JSON.stringify(source.slice(quote.start, quote.end)));
    // unpainting the changes leaves the highlight as it was
    unpaintChanges(El(box)); unpaintChanges(El(code));
    assert.equal(serialize(box), b0); assert.equal(serialize(code), c0);
  }
});

test("change points where a change mark and a comment highlight cover the same word: whichever was painted first (a highlight repaint wraps the text inside the change's mark; a changes repaint wraps it inside the highlight), a deletion at either edge sits outside both, in both views", () => {
  const source = "We recommend shipping the cache.\n";
  const i = ins("i", at(source, "shipping"), "shipping", "web");
  const quote = { start: i.curFrom, end: i.curTo };
  const a = del("a", i.curFrom, "quickly ", "api"), b = del("b", i.curTo, " quickly", "api");
  for (const highlightFirst of [true, false]) {
    const box = buildRendered(source), code = buildRaw(source);
    const paintHl = () => { assert.ok(paintRendered(El(box), source, quote, "fc-hl")); paintRaw(El(code), source, quote, "fc-hl"); };
    const paintIns = () => { assert.deepEqual(paintChangesRendered(El(box), source, [i], stylesFor), { painted: ["i"], unpainted: [] }); paintChangesRaw(El(code), source, [i], stylesFor); };
    if (highlightFirst) { paintHl(); paintIns(); } else { paintIns(); paintHl(); }
    const nest = highlightFirst ? '[fc-hl [fc-ins i "shipping"]]' : '[fc-ins i [fc-hl "shipping"]]';
    assert.equal(shape(paraOf(box)), '"We recommend " ' + nest + ' " the cache."', "the nesting under test (Rendered)");
    assert.equal(shape(cellOf(code, 0)), '"We recommend " ' + nest + ' " the cache."', "the nesting under test (Raw)");
    assert.deepEqual(paintChangesRendered(El(box), source, [a, b], stylesFor), { painted: ["a", "b"], unpainted: [] });
    paintChangesRaw(El(code), source, [a, b], stylesFor);
    const want = '"We recommend " [fc-del a] ' + nest + ' [fc-del b] " the cache."';
    assert.equal(shape(paraOf(box)), want, "Rendered, highlight " + (highlightFirst ? "first" : "second"));
    assert.equal(shape(cellOf(code, 0)), want, "Raw, highlight " + (highlightFirst ? "first" : "second"));
  }
});

// ── 3. two points at one offset keep their paint order in both views ───────────────────────────────

test("change points at one offset keep the order they were painted in, in both views: after a word, after an insertion's mark, and at a row's end", () => {
  const source = "We recommend shipping the cache.\n";
  const off = at(source, "shipping") + "shipping".length;
  const d1 = del("d1", off, " quickly", "web"), d2 = del("d2", off, " soon", "api");
  let v = bothViews(source, [d1, d2]);
  assert.equal(v.rendered, '"We recommend shipping" [fc-del d1] [fc-del d2] " the cache."');
  assert.equal(v.raw, '"We recommend shipping" [fc-del d1] [fc-del d2] " the cache."');
  const i = ins("i", at(source, "shipping"), "shipping", "web");
  v = bothViews(source, [i, d1, d2]);
  assert.equal(v.rendered, '"We recommend " [fc-ins i "shipping"] [fc-del d1] [fc-del d2] " the cache."');
  assert.equal(v.raw, '"We recommend " [fc-ins i "shipping"] [fc-del d1] [fc-del d2] " the cache."');
  const short = "We recommend shipping\n";
  v = bothViews(short, [d1, d2]);
  assert.equal(v.rendered, '"We recommend shipping" [fc-del d1] [fc-del d2]');
  assert.equal(v.raw, '"We recommend shipping" [fc-del d1] [fc-del d2]');
});

// ── 4. a substitution's point sits before its tint wherever the tint was found: the fallback path ──

test("Rendered change marks: a substitution inside a code fence or a table cell — blocks the index map refuses, so its tint came through the text-match fallback — still gets its point immediately before the tint and is reported painted; a deletion at the same offset is card-only, which proves the block is refused", () => {
  const cases: [string, string, string, string, string][] = [
    // source, the new text, the old text, the element the tint must be inside, a deletion's label
    ["# Report\n\n```\nrespond(request)\n```\n", "respond", "reply", "PRE", "await "],
    ["| step | verb |\n|------|------|\n| 1 | cut |\n", "cut", "reduced", "TD", "then "],
  ];
  for (const [source, newText, oldText, tag, delLabel] of cases) {
    const box = buildRendered(source);
    const before = serialize(box);
    const off = at(source, newText);
    // the block IS refused: a bare deletion here cannot be placed through the map
    assert.deepEqual(paintChangesRendered(El(box), source, [del("x", off, delLabel, "web")], stylesFor), { painted: [], unpainted: ["x"] }, tag + ": the map refuses the block");
    assert.equal(serialize(box), before);
    const s = sub("s", off, newText, oldText, "web");
    assert.deepEqual(paintChangesRendered(El(box), source, [s], stylesFor), { painted: ["s"], unpainted: [] }, tag + ": the substitution is painted");
    const m = tint(box, "s");
    assert.ok(inside(m, tag), tag + ": the tint is in the refused block, found by its text");
    assert.equal(m.textContent, newText);
    const points = withClass(box, "fc-del");
    assert.equal(points.length, 1, tag + ": the substitution's point is painted too");
    assert.equal(points[0].getAttribute("data-id"), "s");
    assert.equal(points[0].getAttribute("data-fc-text"), oldText, tag + ": labelled with the old text");
    assert.equal(points[0].getAttribute("data-act"), "fcchange");
    assert.equal(next(points[0]), m, tag + ": immediately before its tint");
    assert.ok(inside(points[0], tag), tag + ": inside the same block");
    unpaintChanges(El(box));
    assert.equal(serialize(box), before, tag + ": restores");
    // the Raw twin: the same point, the same place
    const code = buildRaw(source);
    const c0 = serialize(code);
    const raw = paintChangesRaw(El(code), source, [s], stylesFor) as unknown as FakeElement[];
    const rp = raw.filter((x) => x.getAttribute("class") === "fc-del"), rm = raw.filter((x) => x.getAttribute("class") === "fc-ins");
    assert.equal(rp.length, 1); assert.equal(rm.length, 1);
    assert.equal(next(rp[0]), rm[0], tag + ": Raw's point is immediately before its tint too");
    assert.equal(rp[0].getAttribute("data-fc-text"), oldText);
    unpaintChanges(El(code));
    assert.equal(serialize(code), c0);
  }
});
