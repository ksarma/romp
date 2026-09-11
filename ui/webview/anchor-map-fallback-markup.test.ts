// The Rendered fallback's occurrence when the quote carries markup of its own (anchor-map.ts paintRendered;
// plans/file-review.md: a comment inside a refused block "falls back to a whitespace-tolerant match of its
// quote stripped of inline markup"). The Slice 2 ordinal (anchor-map-change-marks.test.ts, part 2) picks the
// range's occurrence among the block's repeats of a token, and refuses when the rendering shows the text a
// different number of times than the source holds it. Counted over the RAW slice, that refused every quote
// whose markup wrapped it: a comment left from Raw on `` `GET /notes` `` (backticks included) in a table
// whose other cell says "GET /notes lists notes" occurs once in the source and twice, stripped, in the
// rendering — so a highlight Slice 1 painted on the right cell was dropped and its card fell to Reveal.
// The count is now taken over the block's source stripped the same way, with each surviving character
// mapped back to its origin (stripMarkupMapped), and the range's occurrence is the one whose characters
// map inside it. Driven over the viewer's two DOM shapes the way anchor-map.test.ts drives them; fixtures
// are synthetic (the notes-api world).
// Parts 3 and 4 (Slice 5 of plans/markdown-viewer.md, items 2 and 8) cover the two holes whose text the rendering
// shows differently from prose: a code block's lines are shown raw, so the strip that serves prose broke the needle
// (`total = a * b * 2` lost its asterisks to the emphasis rule and painted in Raw alone; `# a comment` lost its `# `
// and painted two characters in), and a table row's `|` delimiters are shown nowhere, so a quote across two cells,
// `cell one | cell two`, matched nothing. Inside a code hole the fallback reads the quote and the scope's source raw
// (fence lines dropped); inside a table hole it reads each unescaped `|` as a blank on both sides, with a blank in the
// hay between two adjacent table parts; the stored quote stays the exact source slice (the owner's ruling 5: the
// plan's "strip cell delimiters" is a paint-time rule). The browser leg anchor-map-code-table-paint-browser.test.ts
// drives both through the real viewer and panel, a Raw save and a fresh open.
// Round 3 of the Slice 5 review retired the hand-written strip (regexes per inline construct, line by line) for the markdown
// pipeline itself: the needle is the text marked's tokens show for the scope's blocks, written out with a source position per
// character (anchor-map.ts renderedBlocks), cut to the range. Part 5 below is that ruling's pin: a corpus of 300 seeded cells and
// every hand case of the three rounds, each read equal to marked's rendered text through the stand-in, and painted whole.
import { test } from "node:test";
import assert from "node:assert/strict";
import { inspect } from "node:util";
import { marked } from "marked";
import { applyMdConfig, resolveWikilink } from "./md-config";   // the one markdown configuration, applied here as the viewer applies it
import {
  mapRawSelection, paintRendered, paintChangesRendered, unpaintChanges, stripMarkupMapped, renderedQuote,
  type ChangePaint, type SelLike,
} from "./anchor-map";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

// ── the viewer's marked configuration: the one every bundle applies (md-config.ts; pinned by anchor-map.test.ts) ──
applyMdConfig();

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
/** The elements the sanitizer removes WITH their text (md-sanitize.ts against DOMPurify's FORBID_CONTENTS), stood in for: the
 *  stand-in parser keeps every element, so the cases that hold one drop it here as the viewer's DOM would. */
const DROP_WITH_TEXT = new Set(["SCRIPT", "STYLE", "IFRAME", "NOSCRIPT", "TEMPLATE"]);
function standInSanitize(root: FakeElement): void {
  for (const c of root.childNodes.slice()) {
    if (!(c instanceof FakeElement)) continue;
    if (DROP_WITH_TEXT.has(c.tagName)) { root.removeChild(c); continue; }
    standInSanitize(c);
  }
}
/** The viewer's Rendered body: `div.fileview-md > marked output`, the file kind's wikilink stamp applied as file-view-links.ts applies
 *  it (so `[[Note]]` shows `Note`, the surface comments are made on), the sanitizer's drops stood in for. */
function buildRendered(text: string): FakeElement {
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, marked.parse(text, { walkTokens: (t) => { resolveWikilink(t); } }) as string)) box.appendChild(n);
  standInSanitize(box);
  return box;
}
const El = (n: FakeNode) => n as unknown as Element;

// ── helpers ────────────────────────────────────────────────────────────────────────────────────────
function serialize(n: FakeNode): string {
  if (n.nodeType === 3) return "#" + JSON.stringify((n as FakeText).data);
  const e = n as FakeElement;
  const attrs = [...e.attrs.entries()].sort().map(([k, v]) => ` ${k}=${JSON.stringify(v)}`).join("");
  return `<${e.tagName}${attrs}>` + e.childNodes.map(serialize).join("") + `</${e.tagName}>`;
}
const docOrder = (root: FakeNode): FakeNode[] => { const out: FakeNode[] = []; const visit = (n: FakeNode) => { out.push(n); n.childNodes.forEach(visit); }; visit(root); return out; };
const elements = (root: FakeNode): FakeElement[] => docOrder(root).filter((n) => n.nodeType === 1) as FakeElement[];
const withClass = (root: FakeNode, cls: string): FakeElement[] => elements(root).filter((e) => (e.getAttribute("class") || "").split(" ").includes(cls));
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
const rangeOf = (source: string, s: string, from = 0) => { const start = at(source, s, from); return { start, end: start + s.length }; };
const noStyles = (): Record<string, string> => ({});
/** A comment highlight over `range`: the marks, their joined text, and the table cell they sit in. */
function highlight(source: string, range: { start: number; end: number }, tag = "TD") {
  const box = buildRendered(source);
  const marks = paintRendered(El(box), source, range, "fc-hl", { act: "fcopen", id: "k1" }) as unknown as FakeElement[] | null;
  return { box, marks, text: marks ? marks.map((m) => m.textContent).join("") : null, cell: marks && marks.length ? cellOf(marks[0], tag) : null };
}

// ── 1. the mapped strip: the rendering's own text ────────────────────────────────────────────────

/** The classes of the controls the viewer parks in the rendered markup, whose text is not the note's (anchor-map.ts CONTROL_CLASSES):
 *  every read of the rendered text below skips them, as the fallback's hay does. */
const CONTROL_CLASSES = ["code-copy", "katex", "katex-error", "md-math-src", "md-fnback", "md-frontmatter-head", "fv-gate"];
const isControl = (n: FakeNode): boolean => n instanceof FakeElement && (n.getAttribute("class") || "").split(" ").some((c) => CONTROL_CLASSES.includes(c));
/** The text under `n` less the controls': what the hay reads. */
const textShown = (n: FakeNode): string => n.nodeType === 3 ? (n as FakeText).data : isControl(n) ? "" : n.childNodes.map(textShown).join("");
/** The text the stand-in's DOM shows for `s`, whitespace runs collapsed (the fallback's match is whitespace-tolerant). */
const shownText = (s: string): string => norm(textShown(buildRendered(s)));
const norm = (s: string): string => s.replace(/\s+/g, " ").trim();

test("stripMarkupMapped: the text is what the rendering shows for the source (marked's tokens under the one configuration, written out; the Slice 5 review's round 3 retired the hand-written strip), and every character maps to its origin in the source, never decreasing: the hand cases of rounds 1 and 2, and the shapes the rounds found the strip wrong on", () => {
  const cases: string[] = [
    "> quoted *text* here", "- [x] a task **done**", "1) numbered _item_", "## Heading with `code` ##", "```python",
    "![alt](img.png) and [label](http://x) and [ref][r]", "<https://example.com/x> and __also__ and ~~del~~", "\\*escaped\\* and \\#",
    "trailing two  ", "trailing backslash\\", "| `GET /notes` | GET /notes lists notes |", "| **cache** | cache |",
    "a * b * c", "*em* and a * b", "`__init__` and `f(*args, **kwargs)` and `a*b*c`", "`` a ` b `` and **`x`**", "\\`not code\\` *em*",
    // the review's round 2: nested emphasis of one delimiter, a delimiter at a strong's or a link's edge, the escapes
    "*a *b* c*", "**a **b** c**", "_a _b_ c_", "***a***", "*a **b***", "**a**_b_", "_a_**b**", "[link](http://x)_b_", "**Note:**_draft_",
    "\\*\\*kwargs", "\\*required\\*", "*a\\*b*", "\\*a*b*", "**a\\*\\*b**", "costs \\$5", "\\<b\\>", "\\&", "\\=a \\^2 \\%", "5 \\* 3",
    "Ctrl<kbd>C</kbd>", "H<sub>2</sub>O", "a<br>b", "a <!-- c --> b", "<span style=\"color:red\">r</span>",
    "==hl== and a ==b== c", "[[Topic]] and see[^1]\n\n[^1]: A note.", "<a@b.c> <mailto:a@b.c>", "[l](http://x/(a)) [m](http://y \"t (u)\")",
    // the review's round 3: the shapes the hand-written strip read differently from marked (each a finding, now the pipeline's own reading)
    "_snake_case_", "_my_var_ here", "__my_var__", "_a_b_", "___a___", "**5 * 3 = 15**", "**bold with * star**", "*use * as wildcard*", "~~a ~ b~~", "**a*b**",
    "*a * b*", "**a * b** and **c**", "*rate * time*", "_a _ b_", "~~a ~~b~~ c~~", "*a ** b*", "** not bold **", "*a**b* c*",
    "see `x\\`\nnext", "the path is `C:\\Users\\`\nmore", "foo\\\\\nnext",
    "Edit <path/to/file> first", "use <name, email> format", "x <a.b> y", "<key=value>", "<x.y.z>", "Map<K, V>", "List<String>", "set <VAR> to",
    "see[^9]", "cite[^missing] here", "[a][nodef] and matrix[i][j]", "[config][settings]", "![logo][idef] here", "knoll [![tango][idef]][rdef] knollx",
    "https://x.test/a/__init__.py zulu", "<https://x.test/_draft_>", "www.x.test/_isle_", "https://x.test/*star*", "https://x.test/~~strike~~",
    "<ftp://x.test/lagoon>", "<file:///cedar/a.md>", "<tel:+1555whiskey>", "<obsidian://open?vault=oscar>", "<vscode://file/whiskey>", "<user:pass> jade",
    "é_a_ and 日本_版_ and _b_é", "٣_a_", "2_a_ and a_b_",
    "Run this <script>alert(1)</script> then", "a <style>p{}</style> b <noscript>n</noscript> c <template>t</template> d", "<kbd>C</kbd> and <textarea>kept</textarea>",
    "a  \nb and c\\\nd", "It was released in\n2024. It was the last version.", "Count the # of items and > 5 means overflow and - beta gamma",
    "**an important\nphrase** and [the design\nnotes](http://x) and `sierra *zulu*\nuniform`", "[wildcard](http://x.test/files/*)*", "*[a](http://x.test/*)",
    "<div>costs \\$5 &amp; see \\& x and C:\\Temp\\</div>", "<div>path C:\\Temp\\<br>next</div>", "<div>a <script>x</script> b <template>t</template> c</div>",
    "<div>&#110;ote note</div>", "Fish &amp; chips &lt;3 &#120;",
    "# T\n\n| a | b |\n|---|---|\n| `x` | x |\n```\nfence\n```\n\nAfter.\n",
    "- one\n- two\n\n  more\n\n> quoted\n> lines\n\n1. first\n2. second\n",
  ];
  for (const s of cases) {
    const m = stripMarkupMapped(s);
    // the delimiter row of a table is kept as its dashes on purpose (a quote spanning it paints nothing, Slice 5 item 8): the stand-in shows none
    const shown = shownText(s).replace(/\|---\|---\| ?/g, "");
    assert.equal(norm(m.text).replace(/\|---\|---\| ?/g, ""), shown, JSON.stringify(s));
    assert.equal(m.map.length, m.text.length, JSON.stringify(s) + ": one origin per character");
    for (let i = 0; i < m.text.length; i++) {
      assert.ok(m.map[i] >= 0 && m.map[i] <= s.length, JSON.stringify(s) + ": character " + i + " maps into the source");
      if (i > 0) assert.ok(m.map[i] >= m.map[i - 1], JSON.stringify(s) + ": the map never decreases at " + i);
    }
  }
  // a few readings spelled out: what the rendering shows, byte for byte (the whitespace the DOM holds included)
  for (const [s, want] of [
    ["_snake_case_", "snake_case\n"], ["**5 * 3 = 15**", "5 * 3 = 15\n"], ["**a*b**", "a*b\n"], ["trailing backslash\\", "trailing backslash\\\n"],
    ["a  \nb", "ab\n"], ["see `x\\`\nnext", "see x\\\nnext\n"], ["Edit <path/to/file> first", "Edit <path/to/file> first\n"], ["see[^9]", "see[^9]\n"],
    ["<ftp://x.test/lagoon>", "ftp://x.test/lagoon\n"], ["Run this <script>alert(1)</script> then", "Run this  then\n"], ["<div>costs \\$5 &amp; x</div>", "costs \\$5 & x\n"],
    ["[[Topic]] here", "Topic here\n"], ["![alt](img.png) and [label](http://x)", " and label\n"],
  ] as const) assert.equal(stripMarkupMapped(s).text, want, JSON.stringify(s));
  // the map tells the two "GET /notes" apart: the first lives inside the backticks, the second is the plain one
  const row = "| `GET /notes` | GET /notes lists notes |";
  const m = stripMarkupMapped(row);
  const a = m.text.indexOf("GET /notes"), b = m.text.indexOf("GET /notes", a + 1);
  assert.equal(m.map[a], row.indexOf("`") + 1);
  assert.equal(m.map[b], row.lastIndexOf("GET /notes"));
  // an entity's decoded character maps to the entity's first character, an escape's to the character it escaped
  const ent = stripMarkupMapped("Fish &amp; \\*chips\\*");
  assert.equal(ent.text, "Fish & *chips*\n");
  assert.equal(ent.map[ent.text.indexOf("&")], "Fish &amp;".indexOf("&"));
  assert.equal(ent.map[ent.text.indexOf("*")], "Fish &amp; \\*".length - 1);
});

// ── 2. the finding: a marked-up quote whose plain text recurs in the block ─────────────────────────

const ROUTES = "# Routes\n\n| Route | Note |\n|-------|------|\n| `GET /notes` | GET /notes lists notes |\n\nDone.\n";
const CACHE = "# Cache\n\n| Term | Note |\n|---|---|\n| **cache** | the cache is shared |\n";
const ROUTES_REV = "# Routes\n\n| Note | Route |\n|---|---|\n| GET /notes lists notes | `GET /notes` |\n";

test("Rendered fallback: a comment on a code-span or bold cell whose plain text recurs in the table paints the commented cell — the first when it comes first, the second when it comes second", () => {
  // the finding's scenario A: the quote is `GET /notes`, backticks included; the plain text recurs after it
  let h = highlight(ROUTES, rangeOf(ROUTES, "`GET /notes`"));
  assert.ok(h.marks && h.marks.length, "painted (filereview-s1 painted this; the raw-slice count refused it)");
  assert.equal(h.text, "GET /notes");
  assert.equal(h.cell!.index, 0, "the commented cell, not the plain recurrence");
  assert.equal(h.cell!.el.textContent, "GET /notes");
  // scenario B: a bold word, plain elsewhere in the row
  h = highlight(CACHE, rangeOf(CACHE, "**cache**"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "cache");
  assert.equal(h.cell!.index, 0);
  // the plain text comes FIRST: the ordinal lands on the second cell (filereview-s1 painted the first, the wrong one)
  h = highlight(ROUTES_REV, rangeOf(ROUTES_REV, "`GET /notes`"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "GET /notes");
  assert.equal(h.cell!.index, 1, "the second cell holds the commented code span");
  // and a comment on the PLAIN cell of the same row still paints the plain cell
  h = highlight(ROUTES_REV, rangeOf(ROUTES_REV, "GET /notes lists notes"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.cell!.index, 0);
  h = highlight(ROUTES, rangeOf(ROUTES, "GET /notes lists notes"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.cell!.index, 1);
});

test("Rendered fallback: markup INSIDE the quote (a code span mid-phrase, a bold word before plain text) is stripped on both sides, so the ordinal still finds the commented cell", () => {
  const mid = "# Routes\n\n| a | b |\n|---|---|\n| the `GET /notes` route | the GET /notes route |\n";
  let h = highlight(mid, rangeOf(mid, "the `GET /notes` route"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "the GET /notes route");
  assert.equal(h.cell!.index, 0);
  const midRev = "# Routes\n\n| a | b |\n|---|---|\n| the GET /notes route | the `GET /notes` route |\n";
  h = highlight(midRev, rangeOf(midRev, "the `GET /notes` route"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.cell!.index, 1);
  const bold = "# Routes\n\n| a | b |\n|---|---|\n| GET /notes | **GET** /notes |\n";
  h = highlight(bold, rangeOf(bold, "**GET** /notes"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "GET /notes");
  assert.equal(h.cell!.index, 1);
});

test("Rendered fallback: the scenario is reachable — a Raw selection over the backticked cell mints the range with the backticks, and that range paints in Rendered", () => {
  const code = buildRaw(ROUTES);
  const rowIndex = ROUTES.split("\n").findIndex((ln) => ln.includes("`GET /notes`"));
  const row = code.childNodes[rowIndex] as FakeElement;
  const t = (row.childNodes[0] as FakeElement).childNodes[0] as FakeText;
  const col = t.data.indexOf("`GET /notes`");
  const r = mapRawSelection(sel(t, col, t, col + "`GET /notes`".length), El(code), ROUTES);
  assert.equal(r.ok, true, "expected ok: " + JSON.stringify(r));
  if (!r.ok) return;
  assert.equal(r.quote, "`GET /notes`", "the backticks are part of the quote a Raw selection stores");
  const h = highlight(ROUTES, r.range);
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.cell!.index, 0);
});

test("Rendered fallback: a change whose new text is the marked-up cell paints, in the changed cell, and unpaint restores the DOM", () => {
  for (const [source, cell] of [[ROUTES, 0], [ROUTES_REV, 1]] as [string, number][]) {
    const box = buildRendered(source);
    const before = serialize(box);
    const from = at(source, "`GET /notes`");
    const change: ChangePaint = { id: "c", kind: "ins", curFrom: from, curTo: from + "`GET /notes`".length, oldText: "", author: "web", newText: "`GET /notes`" };
    const res = paintChangesRendered(El(box), source, [change], noStyles);
    assert.deepEqual(res, { painted: ["c"], unpainted: [] }, "the change is painted, not left to Reveal");
    const marks = withClass(box, "fc-ins");
    assert.equal(marks.length, 1);
    assert.equal(marks[0].textContent, "GET /notes");
    assert.equal(cellOf(marks[0], "TD").index, cell);
    unpaintChanges(El(box));
    assert.equal(serialize(box), before);
  }
});

test("Rendered fallback: the count guard still holds where the rendering shows the quote's text more often than the source's rendering does (a rendering that gained a copy of the passage): nothing is painted and the DOM is untouched; an HTML block's entity is the character it shows, so a quote on the plain `note` beside `&#110;ote` paints the plain one by ordinal and one on the entity's paints the first (the review's round 2 had refused both: the strip kept the entity's source form, so the counts disagreed); a code-span quote with no plain recurrence paints as before", () => {
  // the block is refused (an entity), so the paint takes the fallback; the DOM's paragraph for it shows the passage twice
  const source = "Alpha one.\n\nBeta &amp; two.\n\nGamma three.\n";
  const box = buildRendered("Alpha one.\n\nBeta &amp; two. Beta &amp; two.\n\nGamma three.\n");
  const before = serialize(box);
  assert.equal(paintRendered(El(box), source, rangeOf(source, "Beta &amp; two."), "fc-hl"), null, "two shown, one rendered from the source: the counts disagree in the block's node and over the whole text, so nothing is painted");
  assert.equal(serialize(box), before);
  // the entity in an html block: the rendering shows `note note`, and so does the block's reading now
  const html = "# Notes\n\n<div>&#110;ote note</div>\n";
  let h = highlight(html, rangeOf(html, "note"), "DIV");   // the plain word, after the entity
  assert.ok(h.marks && h.marks.length === 1, "the plain `note` paints (was null)");
  assert.equal(h.text, "note");
  assert.equal(textBefore(h.box, h.marks![0]), "Notes\nnote ", "the second shown `note`, the range's own");
  h = highlight(html, rangeOf(html, "&#110;ote"), "DIV");
  assert.ok(h.marks && h.marks.length === 1, "the entity's `note` paints too");
  assert.equal(textBefore(h.box, h.marks![0]), "Notes\n", "the first shown `note`");
  // the control: the quote's plain text occurs once in the rendering and once, rendered, in the source
  const one = "# Routes\n\n| Route | Note |\n|---|---|\n| `GET /notes` | lists notes |\n";
  h = highlight(one, rangeOf(one, "`GET /notes`"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "GET /notes");
  assert.equal(h.cell!.index, 0);
});

// ── 3. Slice 5, item 2: a quote inside a code block is read raw ────────────────────────────────────

/** The rendered text before `n` in document order (the code's earlier lines, for a repeated line's ordinal). */
function textBefore(root: FakeNode, n: FakeNode): string {
  let out = "";
  for (const x of docOrder(root)) { if (x === n) break; if (x.nodeType === 3) out += (x as FakeText).data; }
  return out;
}
const TOTALS = "# Totals\n\nIntro paragraph with several words in it.\n\n```python\ntotal = a * b * 2\nname_ = under_score  # trailing comment\n```\n\nAfter paragraph.\n";
const FENCED = "# Handler notes\n\nBefore paragraph.\n\n```python\n# a comment\ndef f(x):\n    return x + 1  # trailing\n\nvalue = f(2)\n```\n\nAfter paragraph.\n";

test("Rendered fallback, a code hole: `total = a * b * 2` paints inside the pre with the marks' text the raw line (the emphasis rule stripped its asterisks and nothing matched); `name_ = under_score` still paints; `# a comment` paints from its `#`; the whole fence, fence lines included, paints from the `#` too", () => {
  let h = highlight(TOTALS, rangeOf(TOTALS, "total = a * b * 2"), "PRE");
  assert.ok(h.marks && h.marks.length, "painted (was null: the needle read `total = a  b  2`)");
  assert.equal(norm(h.text!), "total = a * b * 2");
  assert.equal(h.cell!.el.tagName, "PRE");
  // the neighbouring line painted before too (the `_` rule's word-boundary guard spared it) and still does
  h = highlight(TOTALS, rangeOf(TOTALS, "name_ = under_score  # trailing comment"), "PRE");
  assert.ok(h.marks && h.marks.length);
  assert.equal(norm(h.text!), "name_ = under_score # trailing comment");
  // a comment line: the heading rule took its `# ` and the mark began at the `a`
  h = highlight(FENCED, rangeOf(FENCED, "# a comment"), "PRE");
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "# a comment", "the mark begins at the `#`, not two characters in");
  // the whole block, fence lines included: the fences render nothing and drop from the needle; the marks cover the code from its `#`
  const whole = { start: FENCED.indexOf("```python"), end: FENCED.indexOf("```\n\nAfter") + 3 };
  h = highlight(FENCED, whole, "PRE");
  assert.ok(h.marks && h.marks.length, "the whole block paints");
  assert.equal(norm(h.text!), norm("# a comment\ndef f(x):\n    return x + 1  # trailing\n\nvalue = f(2)"));
});

test("Rendered fallback, a code hole: a line repeated in the fence paints the range's own line by ordinal, the count taken raw on both sides", () => {
  const src = "```\ntotal = a * b * 2\ntotal = a * b * 2\n```\n";
  const second = src.lastIndexOf("total = a * b * 2"), first = src.indexOf("total = a * b * 2");
  let h = highlight(src, { start: second, end: second + "total = a * b * 2".length }, "PRE");
  assert.ok(h.marks && h.marks.length === 1, "one mark (was null)");
  assert.equal(textBefore(h.box, h.marks![0]), "total = a * b * 2\n", "the second line");
  h = highlight(src, { start: first, end: first + "total = a * b * 2".length }, "PRE");
  assert.ok(h.marks && h.marks.length === 1);
  assert.equal(textBefore(h.box, h.marks![0]), "", "the first line");
});

test("Rendered fallback, a code hole: an indented code block, a fence in a list item and a fence in a blockquote read raw too; a quoted fence's lines shed the quote's markers, so a two-line quote there still paints", () => {
  const indented = "Intro paragraph.\n\n    total = a * b * 2\n    next = total * 2\n\nAfter paragraph.\n";
  let h = highlight(indented, rangeOf(indented, "total = a * b * 2"), "PRE");
  assert.ok(h.marks && h.marks.length, "indented code (was null)");
  assert.equal(norm(h.text!), "total = a * b * 2");
  const two = { start: indented.indexOf("total ="), end: indented.indexOf("next = total * 2") + "next = total * 2".length };
  h = highlight(indented, two, "PRE");   // the range holds the second line's indentation: white space the match ignores
  assert.ok(h.marks && h.marks.length, "two indented lines (was null)");
  assert.equal(norm(h.text!), "total = a * b * 2 next = total * 2");
  const listed = "- Item text with `make` in it.\n\n  ```\n  x * y\n  ```\n\n- Second item.\n";
  h = highlight(listed, rangeOf(listed, "x * y"), "PRE");
  assert.ok(h.marks && h.marks.length, "a fence in a list item (was null)");
  assert.equal(norm(h.text!), "x * y");
  assert.equal(cellOf(h.marks![0], "LI").index, 0);
  const quoted = "> Quoted intro.\n>\n> ```\n> a = 1\n> b = 2\n> ```\n";
  const span = { start: quoted.indexOf("a = 1"), end: quoted.indexOf("b = 2") + "b = 2".length };
  h = highlight(quoted, span, "PRE");   // the raw slice is "a = 1\n> b = 2": the second line's marker is the quote's, not the code's
  assert.ok(h.marks && h.marks.length, "a two-line quote in a quoted fence paints (the strip took the markers before; the markers still come off)");
  assert.equal(norm(h.text!), "a = 1 b = 2");
  h = highlight(quoted, rangeOf(quoted, "b = 2"), "PRE");
  assert.ok(h.marks && h.marks.length);
  assert.equal(norm(h.text!), "b = 2");
});

test("Rendered fallback, a code hole nested in a list item: the item's prose keeps the strip while the code reads raw, so a code token the prose repeats in a link's label and URL counts the same on both sides and the code's copy paints (a control: green before too; the raw source alone would count the URL's copy and paint nothing)", () => {
  const src = "- See [make](https://example.invalid/make) first.\n\n      make\n\n- Second item.\n";
  const h = highlight(src, rangeOf(src, "make", src.indexOf("      make")), "PRE");
  assert.ok(h.marks && h.marks.length, "painted");
  assert.equal(h.text, "make");
  assert.equal(h.cell!.el.tagName, "PRE");
});

// ── 4. Slice 5, item 8: a quote across two cells reads its pipe as a blank ──────────────────────────

const CELLS = "# Table\n\n| Col A | Col B |\n|-------|-------|\n| cell one | cell two |\n| cell three | cell four |\n\nAfter paragraph.\n";
/** The marks with text of their own (a blank between two cells is a trim candidate in a browser, never the passage). */
const textMarks = (marks: FakeElement[]): FakeElement[] => marks.filter((m) => m.textContent.trim() !== "");

test("Rendered fallback, a table hole: `cell one | cell two` paints one mark in each of the row's two cells (was null: the needle kept the pipe); one cell still paints one; a quote spanning the delimiter row paints nothing; `\\|` stays the cell's own pipe", () => {
  let h = highlight(CELLS, rangeOf(CELLS, "cell one | cell two"));
  assert.ok(h.marks && h.marks.length, "painted");
  const tm = textMarks(h.marks!);
  assert.deepEqual(tm.map((m) => m.textContent), ["cell one", "cell two"]);
  assert.deepEqual(tm.map((m) => cellOf(m, "TD").index), [0, 1]);
  assert.equal(cellOf(tm[0], "TR").el, cellOf(tm[1], "TR").el, "the same row");
  assert.equal(h.marks!.length, 2, "the blank between the two cells is skipped, not wrapped (skipBlockWs: collapsible white space between two table cells)");
  // one cell: as before
  h = highlight(CELLS, rangeOf(CELLS, "cell one"));
  assert.ok(h.marks && textMarks(h.marks!).length === 1);
  assert.equal(h.cell!.index, 0);
  // across the delimiter row: its dashes stand in no rendered text
  const acrossDelim = { start: CELLS.indexOf("Col B"), end: CELLS.indexOf("cell one") + "cell one".length };
  const box = buildRendered(CELLS);
  const before = serialize(box);
  assert.equal(paintRendered(El(box), CELLS, acrossDelim, "fc-hl"), null, "the quote spans the delimiter row: nothing painted, the card keeps Reveal");
  assert.equal(serialize(box), before);
  // an escaped pipe is the cell's own character
  const esc = "| a \\| b | c |\n|---|---|\n| d | e |\n";
  h = highlight(esc, rangeOf(esc, "a \\| b"), "TH");
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "a | b");
  assert.equal(h.cell!.index, 0);
});

test("Rendered fallback, a table hole: cells with no whitespace between them in the DOM are kept apart by the hay's blank; a quote across two rows paints both cells; a repeated row paints the range's own by ordinal; a quoted table reads the same", () => {
  // a DOM with the newlines between tags gone (a minifying step): the cells' text nodes are adjacent
  const doc = new FakeDocument();
  const box = doc.createElement("div"); box.setAttribute("class", "fileview-md");
  for (const n of parseHTML(doc, (marked.parse(CELLS) as string).replace(/>\n</g, "><"))) box.appendChild(n);
  const marks = paintRendered(El(box), CELLS, rangeOf(CELLS, "cell one | cell two"), "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(marks && marks.length, "painted over adjacent cells");
  assert.deepEqual(textMarks(marks!).map((m) => m.textContent), ["cell one", "cell two"]);
  // two rows
  let h = highlight(CELLS, rangeOf(CELLS, "cell two |\n| cell three"));
  assert.ok(h.marks && h.marks.length, "two rows paint");
  const tm = textMarks(h.marks!);
  assert.deepEqual(tm.map((m) => m.textContent), ["cell two", "cell three"]);
  assert.notEqual(cellOf(tm[0], "TR").el, cellOf(tm[1], "TR").el, "two rows");
  // a repeated row: the ordinal picks the range's
  const rep = "| a | b |\n|---|---|\n| x | y |\n| x | y |\n";
  const second = rep.lastIndexOf("x | y"), first = rep.indexOf("x | y");
  h = highlight(rep, { start: second, end: second + "x | y".length });
  assert.ok(h.marks && h.marks.length, "the repeated row paints");
  assert.equal(cellOf(textMarks(h.marks!)[0], "TR").index, 1, "the second body row");
  h = highlight(rep, { start: first, end: first + "x | y".length });
  assert.ok(h.marks && h.marks.length);
  assert.equal(cellOf(textMarks(h.marks!)[0], "TR").index, 0, "the first body row");
  // a table in a blockquote: the quote's markers are the container's
  const quoted = "> | a | b |\n> |---|---|\n> | c | d |\n";
  h = highlight(quoted, rangeOf(quoted, "c | d"));
  assert.ok(h.marks && h.marks.length, "a quoted table's two cells paint");
  assert.deepEqual(textMarks(h.marks!).map((m) => m.textContent), ["c", "d"]);
});

// ── the Slice 5 review, round 1: a code span's content in a cell, and a quote begun inside a fence line ──

test("Rendered fallback, a table hole: a code span's content is read as the rendering shows it, so `__init__`, `f(*args, **kwargs)`, `_private_` and `a*b*c` in cells paint whole (before: the emphasis rules ran inside the backticks and the needle read `init`, `f(args, *kwargs)`, `private` and `abc`: a partial mark over `init`, or none, the card offering Reveal); a plain cell `x * y * z` paints too (before: its asterisks read as a pair); a bold cell and a code-span cell whose plain text recurs still paint their own cell", () => {
  const NAMES = "# Names\n\n| Name | Meaning |\n|------|---------|\n| `__init__` | the constructor |\n| `f(*args, **kwargs)` | a call |\n| `_private_` | hidden |\n| `a*b*c` | product |\n| x * y * z | stars |\n| **bold** `__x__` | both |\n| `GET /notes` | GET /notes lists notes |\n\nAfter.\n";
  for (const [quote, shown] of [["`__init__`", "__init__"], ["`f(*args, **kwargs)`", "f(*args, **kwargs)"], ["`_private_`", "_private_"], ["`a*b*c`", "a*b*c"], ["x * y * z", "x * y * z"], ["**bold** `__x__`", "bold __x__"]] as const) {
    const h = highlight(NAMES, rangeOf(NAMES, quote));
    assert.ok(h.marks && h.marks.length, quote + ": painted (was " + (quote === "`__init__`" || quote === "`_private_`" ? "a partial mark" : "null") + ")");
    assert.equal(norm(h.text!), shown, quote + ": the whole cell's text under the marks");
    assert.equal(h.cell!.index, 0, quote + ": the first cell");
  }
  // the ordinal over a recurring plain text still finds the commented cell (the control of part 2)
  const h = highlight(NAMES, rangeOf(NAMES, "`GET /notes`"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "GET /notes");
  assert.equal(h.cell!.index, 0);
});

test("Rendered fallback, a code hole: a quote begun inside the opening fence's info string (a Raw drag from the `p` of ```python, or from its second backtick, to the end of the first code line) paints the first code line (before: the sliced first line, `python`, was no fence by its text and stayed in the needle, which the code never holds: nothing painted, the card offering Reveal); one ending inside the closing fence's backticks paints the last line; a code line that itself opens with three backticks inside a four-backtick fence stays in the needle and paints (before: dropped as a fence line on the source side while the rendering shows it)", () => {
  const fence = TOTALS.indexOf("```python"), line1End = TOTALS.indexOf("total = a * b * 2") + "total = a * b * 2".length;
  let h = highlight(TOTALS, { start: fence + 3, end: line1End }, "PRE");
  assert.ok(h.marks && h.marks.length, "from the `p` of the info string (was null)");
  assert.equal(norm(h.text!), "total = a * b * 2");
  h = highlight(TOTALS, { start: fence + 1, end: line1End }, "PRE");
  assert.ok(h.marks && h.marks.length, "from the second backtick (was null)");
  assert.equal(norm(h.text!), "total = a * b * 2");
  const close = TOTALS.indexOf("```\n\nAfter");
  h = highlight(TOTALS, { start: TOTALS.indexOf("name_ ="), end: close + 2 }, "PRE");
  assert.ok(h.marks && h.marks.length, "to inside the closing fence (was null)");
  assert.equal(norm(h.text!), "name_ = under_score # trailing comment");
  const FOUR = "Intro paragraph.\n\n````\n```\ninner fence line\n```\n````\n\nAfter paragraph.\n";
  h = highlight(FOUR, rangeOf(FOUR, "```\ninner fence line"), "PRE");
  assert.ok(h.marks && h.marks.length);
  assert.equal(norm(h.text!), "``` inner fence line", "the three-backtick code line is in the needle (before: `inner fence line` alone)");
  // the whole block, fence lines included, still paints from its first character (part 3's pin, kept)
  const whole = { start: FENCED.indexOf("```python"), end: FENCED.indexOf("```\n\nAfter") + 3 };
  h = highlight(FENCED, whole, "PRE");
  assert.ok(h.marks && h.marks.length);
  assert.equal(norm(h.text!), norm("# a comment\ndef f(x):\n    return x + 1  # trailing\n\nvalue = f(2)"));
});

// ── the Slice 5 review, round 2: the strip's emphasis pass, the cell's escapes and pipes, the constructs it had no rule for ──

const NESTED = "# Nested\n\n| Cell | Note |\n|------|------|\n| *a *b* c* | nested |\n| **a **b** c** | strong |\n| _a _b_ c_ | under |\n| x * y * z | stars |\n\n```\n*a *b* c*\n```\n\nAfter.\n";

test("Rendered fallback, a table hole: same-delimiter nested emphasis in a cell, `*a *b* c*`, `**a **b** c**` and `_a _b_ c_`, paints the cell's text `a b c` whole (before: the single-asterisk rule paired the first `*` with the one after `b` and the needle read `a *b c*`, which the cell never shows: nothing painted, the card offering Reveal); `x * y * z`, the case the flanking rule fixed, still paints; the same line inside a code hole reads raw and paints as the code shows it", () => {
  for (const quote of ["*a *b* c*", "**a **b** c**", "_a _b_ c_"]) {
    const h = highlight(NESTED, rangeOf(NESTED, quote));
    assert.ok(h.marks && h.marks.length, quote + ": painted (was null)");
    assert.equal(norm(h.text!), "a b c", quote + ": the cell's text under the marks");
    assert.equal(h.cell!.index, 0);
  }
  let h = highlight(NESTED, rangeOf(NESTED, "x * y * z"));
  assert.ok(h.marks && h.marks.length);
  assert.equal(norm(h.text!), "x * y * z");
  const code = NESTED.indexOf("```\n") + 4;
  h = highlight(NESTED, { start: code, end: code + "*a *b* c*".length }, "PRE");
  assert.ok(h.marks && h.marks.length, "the code line paints");
  assert.equal(norm(h.text!), "*a *b* c*", "raw, as the code shows it");
});

const PIPES = "# Pipes\n\n| Cell | Note |\n|------|------|\n| `a \\| b` | span |\n| `string \\| number` | union |\n| `a\\|b` | tight |\n| a \\| b | plain |\n| `a \\\\| b` | parity |\n| c \\\\\\| d | three |\n\nAfter.\n";

test("Rendered fallback, a table hole: a code span holding an escaped pipe in a cell, `` `a \\| b` ``, `` `string \\| number` `` and `` `a\\|b` ``, paints whole as the code `a | b` the cell shows (the REGRESSION the review's round 1 left: the span's mask hid the escape from the escape rule and the needle kept the backslash; on main each painted); a plain `a \\| b` cell in the same table paints its own cell (the count guard had spread the loss to it); a `|` an even count of backslashes precedes is a delimiter, as marked's splitCells reads it (`\\\\|` splits the row, and the quote over the split paints both cells as they render); `\\\\\\|` is an escaped backslash and the pipe", () => {
  const box = buildRendered(PIPES);
  const cellText = (row: number, col: number): string => { const trs = elements(box).filter((e) => e.tagName === "TR"); const tds = trs[row].childNodes.filter((c) => c.nodeType === 1) as FakeElement[]; return tds[col].textContent; };
  assert.equal(cellText(1, 0), "a | b", "marked shows the code with its pipe");
  assert.equal(cellText(5, 0), "`a \\", "the parity row split at its `\\\\|`: the first cell ends in a backslash");
  assert.equal(cellText(5, 1), "b`");
  assert.equal(cellText(6, 0), "c \\| d", "three backslashes: an escaped backslash, then an escaped pipe");
  for (const [quote, shown] of [["`a \\| b`", "a | b"], ["`string \\| number`", "string | number"], ["`a\\|b`", "a|b"], ["a \\| b", "a | b"], ["c \\\\\\| d", "c \\| d"]] as const) {
    const h = highlight(PIPES, rangeOf(PIPES, quote, PIPES.indexOf("| " + quote + " |")));   // the quote's own row (the plain `a \| b` occurs inside the span's row too)
    assert.ok(h.marks && h.marks.length, quote + ": painted (was null)");
    assert.equal(norm(h.text!), shown, quote + ": the cell's text");
    assert.equal(h.cell!.index, 0, quote + ": the first cell");
  }
  // the parity row: the quote runs across the two cells marked made of it; the marks follow the split
  const h = highlight(PIPES, rangeOf(PIPES, "`a \\\\| b`"));
  assert.ok(h.marks && h.marks.length, "the split row paints");
  const tm = textMarks(h.marks!);
  assert.deepEqual(tm.map((m) => cellOf(m, "TD").index), [0, 1], "one mark in each cell of the split");
  assert.equal(norm(tm.map((m) => m.textContent).join(" ")), "`a \\ b`", "the cells' text as shown, the unmatched backticks with it (the strip's backtick rule had dropped them from the needle, round 3 reads the cells as marked shows them)");
});

const ESCAPES = "# Escapes\n\n| Cell | Note |\n|------|------|\n| \\*\\*kwargs | py |\n| \\*required\\* | req |\n| \\*escaped\\* | esc |\n| *a\\*b* | in |\n| costs \\$5 | price |\n| \\<b\\> | tag |\n| **Note:**_draft_ | adj |\n| _path_**index** | adj2 |\n| Ctrl<kbd>C</kbd> | kbd |\n| H<sub>2</sub>O | sub |\n| ==important== | mark |\n| C:\\Users\\ | path |\n| a\\ | bs |\n| *a | b* |\n\n<div>path C:\\Temp\\ here</div>\n\nAfter.\n";

test("Rendered fallback, a table hole: an escaped `*` or `_` is the character it shows (`\\*\\*kwargs`, `\\*required\\*`, `\\*escaped\\*`, `*a\\*b*`; before: the emphasis rules ran first and paired the escaped asterisks), every ASCII punctuation character is escapable (`costs \\$5`, `\\<b\\>`), an underscore emphasis beside a strong opens (`**Note:**_draft_`), inline html tags render nothing of their own (`Ctrl<kbd>C</kbd>`), a highlight's delimiters go (a wikilink's in test 1), a cell ending in a backslash keeps it (`C:\\Users\\`, `a\\`: the hard break is a line's, not a cell's), an asterisk in one cell pairs with none in another, and a quote in an html block cut mid-line keeps its trailing backslash", () => {
  const box = buildRendered(ESCAPES);
  const shownIn = (quote: string): string => { const tds = elements(box).filter((e) => e.tagName === "TD"); const i = ESCAPES.split("\n").filter((l) => l.startsWith("| ") && !l.startsWith("| Cell")).findIndex((l) => l.startsWith("| " + quote + " |")); assert.ok(i >= 0, "a row for " + quote); return tds[i * 2].textContent; };
  for (const [quote, shown] of [["\\*\\*kwargs", "**kwargs"], ["\\*required\\*", "*required*"], ["\\*escaped\\*", "*escaped*"], ["*a\\*b*", "a*b"], ["costs \\$5", "costs $5"], ["\\<b\\>", "<b>"],
                                ["**Note:**_draft_", "Note:draft"], ["_path_**index**", "pathindex"], ["Ctrl<kbd>C</kbd>", "CtrlC"], ["H<sub>2</sub>O", "H2O"], ["==important==", "important"],
                                ["C:\\Users\\", "C:\\Users\\"], ["a\\", "a\\"]] as const) {
    assert.equal(norm(shownIn(quote)), shown, quote + ": the fixture's cell renders as the case expects");
    const h = highlight(ESCAPES, rangeOf(ESCAPES, quote, ESCAPES.indexOf("| " + quote + " |")));   // the quote's own row (`a\` occurs inside `*a\*b*` too)
    assert.ok(h.marks && h.marks.length, quote + ": painted (was " + (quote.startsWith("C:") || quote === "a\\" ? "a partial mark" : "null") + ")");
    assert.equal(norm(h.text!), shown, quote + ": the whole cell's text under the marks");
    assert.equal(h.cell!.index, 0, quote + ": the first cell");
  }
  // a `*` opening in one cell and closing in the next: both show, and a quote on either cell paints it whole
  const split = ESCAPES.indexOf("| *a | b* |");
  let h = highlight(ESCAPES, rangeOf(ESCAPES, "*a", split));
  assert.ok(h.marks && h.marks.length, "`*a` paints (before: the row's rules paired it with the `*` in the next cell)");
  assert.equal(h.text, "*a");
  h = highlight(ESCAPES, rangeOf(ESCAPES, "b*", split));
  assert.ok(h.marks && h.marks.length);
  assert.equal(h.text, "b*");
  // an html block's text, a quote cut mid-line at a backslash
  h = highlight(ESCAPES, rangeOf(ESCAPES, "C:\\Temp\\"), "DIV");
  assert.ok(h.marks && h.marks.length, "the html block's text paints (the tags render nothing of their own)");
  assert.equal(h.text, "C:\\Temp\\", "the trailing backslash is kept: the quote ends mid-line, at no hard break");
});

test("Rendered fallback: when the range's blocks are paired to nodes that do not hold the quote (a rendering that gained a paragraph the source lacks pairs every later block one node early), the whole rendered text is searched, as when the blocks have no node, and the passage paints by ordinal (before: the scope's text alone was searched and nothing was found, the card offering Reveal where main had painted it)", () => {
  const source = "Alpha one.\n\nBeta two.\n\nGamma three.\n\nBeta two.\n";
  // the DOM of a rendering with a paragraph the source lacks: Beta's block pairs the stranger as a mismatch, Gamma's pairs Beta's <p>
  const box = buildRendered("Alpha one.\n\nChanged.\n\nBeta two.\n\nGamma three.\n\nBeta two.\n");
  const before = serialize(box);
  let marks = paintRendered(El(box), source, rangeOf(source, "Gamma three."), "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(marks && marks.length === 1, "Gamma paints (was null: its block's node was Beta's <p>)");
  assert.equal(marks![0].textContent, "Gamma three.");
  assert.equal(cellOf(marks![0], "P").index, 3, "the fourth paragraph, where the rendering shows it");
  // the ordinal over the whole text: the second Beta paints the second rendered Beta
  const second = source.lastIndexOf("Beta two.");
  marks = paintRendered(El(box), source, { start: second, end: second + "Beta two.".length }, "fc-hl") as unknown as FakeElement[] | null;
  assert.ok(marks && marks.length === 1, "the second Beta paints");
  assert.equal(cellOf(marks![0], "P").index, 4, "the last paragraph");
  // a quote the rendering holds nowhere stays unpainted, and the DOM is untouched
  const box2 = buildRendered("Alpha one.\n\nChanged.\n\nBeta two.\n\nGamma three.\n\nBeta two.\n");
  assert.equal(paintRendered(El(box2), source + "\n\nDelta four.\n", rangeOf(source + "\n\nDelta four.\n", "Delta four."), "fc-hl"), null);
  assert.equal(serialize(box2), before);
});

// ── 5. the Slice 5 review, round 3: the pipeline as the needle's oracle ────────────────────────────
//
// The hand-written strip is gone (anchor-map.ts, "the rendered text of the source"): the needle for a cell or a refused prose block is
// the text marked's tokens show, written out with a source position per character and cut to the range. The pin is a corpus: 300
// seeded cells over every inline construct the rounds argued about, plus every hand case they named, each read equal to the
// stand-in's rendered text and painted whole, as cells and as refused paragraphs; then the shapes only a cut range shows.

/** A small seeded generator (mulberry32), so the corpus is the same on every run and a failing cell can be named by its index. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
/** The inline constructs a corpus cell may hold, each over the cell's own words (so no cell's text recurs in another's): the emphasis
 *  shapes of rounds 1 and 2 and the lone-delimiter and intraword shapes of round 3, code spans, escapes, entities, links defined and
 *  not, images, autolinks of every scheme and bare URLs holding delimiters, inline tags kept, unwrapped and dropped, footnotes,
 *  highlights, wikilinks, non-ASCII neighbours of an underscore, lead-like text, stray delimiters. No construct holds a bare `|`
 *  (which cuts the row) or a line feed (a cell is one line). */
const CONSTRUCTS: Array<(a: string, b: string, c: string) => string> = [
  (a) => `*${a}*`, (a) => `**${a}**`, (a) => `_${a}_`, (a) => `__${a}__`, (a) => `~~${a}~~`, (a) => `***${a}***`,
  (a, b, c) => `*${a} *${b}* ${c}*`, (a, b, c) => `**${a} **${b}** ${c}**`, (a, b, c) => `_${a} _${b}_ ${c}_`, (a, b) => `*${a} **${b}***`,
  (a, b) => `**${a} * ${b}**`, (a, b) => `_${a}_${b}_`, (a, b) => `~~${a} ~ ${b}~~`, (a, b) => `**${a}*${b}**`, (a, b) => `*${a} * ${b}*`, (a) => `___${a}___`,
  (a, b, c) => `${a} * ${b} * ${c}`, (a, b, c) => `${a}_${b}_${c}`, (a, b) => `**${a}**_${b}_`, (a, b) => `_${a}_**${b}**`, (a, b) => `**${a}:**_${b}_`,
  (a, b) => `\`${a}_${b}_\``, (a, b) => `\`${a} \\| ${b}\``, (a, b) => `\`f(*${a}, **${b})\``, (a) => `\`${a}\\\``, (a, b) => `\`\` ${a} \` ${b} \`\``, (a) => `**\`${a}\`**`,
  (a) => `\\*${a}\\*`, (a) => `\\*\\*${a}`, (a, b) => `${a} \\$5 ${b}`, (a) => `\\<${a}\\>`, (a, b) => `${a} \\& ${b}`, (a, b) => `${a} \\| ${b}`, (a, b) => `${a}\\\` ${b}`, (a, b) => `*${a}\\*${b}*`,
  (a, b) => `${a} &amp; ${b}`, (a) => `&lt;${a}&gt;`, (a) => `&quot;${a}&quot;`, (a) => `&#39;${a}&#39;`, (a) => `&#120;${a}`,
  (a, b) => `[${a}](http://x.test/${b})`, (a) => `[${a}][rdef]`, (a) => `[${a}][nodef]`, (a, b) => `${a}[${b}][${b}]`, (a, b) => `[${a}](http://x.test/(${b}))`, (a, b) => `[${a}](http://x.test/${b} "t (u)")`,
  (a, b) => `<https://x.test/${a}_${b}_>`, (a) => `<${a}@x.test>`, (a) => `<mailto:${a}@x.test>`, (a) => `https://x.test/__${a}__.py`, (a) => `www.x.test/_${a}_`, (a) => `https://x.test/*${a}*`, (a) => `https://x.test/~~${a}~~`,
  (a) => `![${a}](http://x.test/i.png)`, (a) => `![${a}][idef]`, () => `![idef][]`, (a) => `[![${a}][idef]][rdef]`, (a) => `![[${a}.png]]`,
  (a) => `<ftp://x.test/${a}>`, (a) => `<file:///${a}/a.md>`, (a) => `<tel:+1555${a}>`, (a) => `<obsidian://open?vault=${a}>`, (a) => `<vscode://file/${a}>`, (a) => `<user:pass> ${a}`,
  (a) => `Ctrl<kbd>${a}</kbd>`, (a) => `H<sub>2</sub>${a}`, (a, b) => `${a}<br>${b}`, (a, b, c) => `${a} <!-- ${b} --> ${c}`, (a, b) => `<b>${a}</b> ${b}`, (a, b) => `<i>${a}</i><em>${b}</em>`,
  (a) => `Edit <path/to/${a}> first`, (a) => `Map<K, ${a}>`, (a) => `use <name, ${a}> format`, (a) => `<${a}=value>`, (a) => `List<${a}>`, (a, b) => `${a} <span style="color:red">${b}</span>`,
  (a, b, c) => `${a} <script>${b}</script> ${c}`, (a, b) => `${a} <style>p{}</style> ${b}`, (a, b) => `<noscript>${a}</noscript> ${b}`, (a, b, c) => `${a} <template>${b}</template> ${c}`, (a, b) => `<iframe>${a}</iframe> ${b}`,
  (a, b) => `<kbd>${a}</kbd> <textarea>${b}</textarea>`, (a, b) => `<button>${a}</button> ${b}`, (a, b) => `<label>${a}</label> ${b}`,
  (a) => `${a}[^1]`, (a, b) => `${a}[^${b}]`, (a, b) => `==${a}== ${b}`, (a, b) => `[[${a}]] ${b}`, (a, b) => `[[${a}\\|${b}]]`,
  (a) => `é_${a}_`, (a) => `日本_${a}_`, (a) => `_${a}_é`, (a) => `٣_${a}_`, (a) => `2_${a}_`, (a, b) => `${a}_${b}_`,
  (a) => `- ${a}`, (a) => `# ${a}`, (a) => `> ${a}`, (a) => `1. ${a}`, (a) => `2024. ${a}`, (a) => `10) ${a}`, (a) => `${a} ##`, (a) => `\`\`\`${a}\`\`\``, (a) => `~~~${a}~~~`,
  (a) => `${a}**`, (a) => `*${a}`, (a, b) => `${a} ** ${b}`, () => `** not bold **`, (a, b) => `*${a}**${b}* c*`, (a, b) => `${a}* ${b}*`, (a, b) => `[${a}](http://x.test/${b}*)*`, (a) => `*[${a}](http://x.test/*)`,
];
/** `n` corpus cells from `seed`: each its own nonce word, then one to three constructs over words of its own. */
function corpusCells(seed: number, n: number): string[] {
  const r = mulberry32(seed);
  const pick = <T>(xs: T[]): T => xs[Math.floor(r() * xs.length)];
  const out: string[] = [];
  for (let i = 0; i < n; i++) {
    const w = "cell" + String(i).padStart(3, "0");
    const parts = [w];
    const k = 1 + Math.floor(r() * 3);
    for (let j = 0; j < k; j++) parts.push(pick(CONSTRUCTS)(w + "a" + j, w + "b" + j, w + "c" + j));
    out.push(parts.join(" "));
  }
  return out;
}
/** The hand cases of rounds 1, 2 and 3, as cells: each finding's shape with a word of its own. */
const HAND_CELLS: string[] = [
  "_snake_case_", "_my_var_ here", "__my_var__", "_a_b_", "___a___", "**5 * 3 = 15**", "**bold with * star**", "*use * as wildcard*", "~~a ~ b~~", "**a*b**",
  "*a * b*", "**a * b** and **c**", "*rate * time*", "_a _ b_", "~~a ~~b~~ c~~", "*a ** b*", "** not bold **", "_max_retries_",
  "*a *b* c*", "**a **b** c**", "_a _b_ c_", "x * y * z", "**Note:**_draft_", "_path_**index**", "`__init__`", "`f(*args, **kwargs)`", "`_private_`", "`a*b*c`", "**bold** `__x__`",
  "`a \\| b`", "`string \\| number`", "`a\\|b`", "a \\| b", "c \\\\\\| d", "\\*\\*kwargs", "\\*required\\*", "\\*escaped\\*", "*a\\*b*", "costs \\$5", "\\<b\\>", "\\&", "\\=a \\^2 \\%",
  "Ctrl<kbd>C</kbd>", "H<sub>2</sub>O", "==important==", "C:\\Users\\", "a\\", "`x\\`",
  "Edit <path/to/file> first", "use <name, email> format", "x <a.b> y", "<key=value>", "<x.y.z>", "Map<K, V>", "List<String>", "set <VAR> to",
  "see[^9]", "cite[^missing] here", "see[^1]", "[whiskey][nodef]", "set matrix[i][j] to zero", "[alpha][rdef]", "[config][settings]",
  "amber ![birch][idef] amberx", "fjord ![idef][] fjordx", "alpha ![idef] alphax", "knoll [![tango][idef]][rdef] knollx", "lima ![lima](http://x.test/i.png) limax",
  "https://x.test/a/__init__.py", "<https://x.test/_draft_>", "www.x.test/_isle_", "https://x.test/*star*", "https://x.test/~~strike~~", "https://x.test/plain.py",
  "<ftp://x.test/lagoon>", "<file:///cedar/a.md>", "<tel:+1555whiskey>", "<irc://x.test/alpha>", "<obsidian://open?vault=oscar>", "<vscode://file/whiskey>", "<user:pass> jade", "<http://x.test/W>", "<W@x.test>", "<mailto:W@x.test>",
  "é_birch_", "日本_tango_", "_nectar_é", "日本_版_", "café_menu_v2_", "2_a_", "a_b_",
  "amber <script>alert(1)</script> amberx", "amber <style>p{}</style> amberx", "amber <iframe>frame</iframe> amberx", "amber <noscript>fallback</noscript> amberx", "amber <template>tpl</template> amberx", "amber <select><option>Opt</option></select> amberx",
  "[wildcard](http://x.test/files/*)*", "see [glob](http://x.test/p/*)* here", "[a](http://x.test/b)*", "*[a](http://x.test/b)*",
  "**bold words** more", "2024. It was romeo", "# of items", "> 5 means overflow", "- beta gamma", "a b ##", "```papa```", "#romeo", "2.0 romeo",
];
const DEFS = "\n[rdef]: http://x.test/r\n[idef]: http://x.test/i.png\n[settings]: http://x.test/s\n\n[^1]: A footnote.\n";
/** A note holding `cells` in a two-column table, with the definitions the reference forms need and a closing paragraph. */
const tableNote = (cells: string[]): string => "# Corpus\n\n| Cell | Note |\n|------|------|\n" + cells.map((c, i) => `| ${c} | nz${String(i).padStart(3, "0")} |`).join("\n") + "\n\nLast paragraph here.\n" + DEFS;
/** A note holding each of `cells` as a paragraph the walk refuses (an entity at its head), so a paint on it takes the fallback. */
const proseNote = (cells: string[]): string => "# Corpus\n\n" + cells.map((c) => `Fish &amp; chips ${c}`).join("\n\n") + "\n\nLast paragraph here.\n" + DEFS;
const cellsOf = (box: FakeNode): FakeElement[] => elements(box).filter((e) => e.tagName === "TD");
const parasOf = (box: FakeNode): FakeElement[] => box.childNodes.filter((n): n is FakeElement => n instanceof FakeElement && n.tagName === "P");
/** Every cell of `cells` in the table note and in the prose note: the needle (renderedQuote over the cell's source range) equals the
 *  shown text, and a paint over the range marks that text whole; a cell whose shown text is empty (a picture alone) is checked to
 *  have an empty needle and left unpainted. Returns the failures, one line each. */
function checkCorpus(cells: string[], what: string): string[] {
  const bad: string[] = [];
  const TABLE = tableNote(cells), PROSE = proseNote(cells);
  const tbox = buildRendered(TABLE), pbox = buildRendered(PROSE);
  const tds = cellsOf(tbox), ps = parasOf(pbox);
  assert.equal(tds.length, cells.length * 2, what + ": one row per cell");
  assert.equal(ps.length, cells.length + 1, what + ": one paragraph per cell, and the closing one");
  cells.forEach((c, i) => {
    for (const [note, root, shownEl, range] of [
      ["cell", tbox, tds[i * 2], rangeOf(TABLE, `| ${c} |`)] as const,
      ["prose", pbox, ps[i], rangeOf(PROSE, `Fish &amp; chips ${c}`)] as const,
    ]) {
      const r = note === "cell" ? { start: range.start + 2, end: range.end - 2 } : range;   // the cell's source, the delimiters left out
      const shown = norm(textShown(shownEl));
      const needle = norm(renderedQuote(note === "cell" ? TABLE : PROSE, r));
      if (needle !== shown) { bad.push(`${what} ${note} ${i} ${JSON.stringify(c)}: needle ${JSON.stringify(needle)}, shown ${JSON.stringify(shown)}`); continue; }
      if (shown === "") continue;
      const marks = paintRendered(El(root), note === "cell" ? TABLE : PROSE, r, "fc-hl", { act: "fcopen", id: "k" + i }) as unknown as FakeElement[] | null;
      const text = marks ? norm(marks.map((m) => m.textContent).join(" ")) : null;
      if (text === null) bad.push(`${what} ${note} ${i} ${JSON.stringify(c)}: not painted (shown ${JSON.stringify(shown)})`);
      else if (text.replace(/\s+/g, "") !== shown.replace(/\s+/g, "")) bad.push(`${what} ${note} ${i} ${JSON.stringify(c)}: painted ${JSON.stringify(text)}, shown ${JSON.stringify(shown)}`);
      else if (note === "cell" && marks!.some((m) => cellOf(m, "TD").el !== shownEl)) bad.push(`${what} cell ${i} ${JSON.stringify(c)}: a mark outside the cell`);
      for (const m of marks || []) { const p = m.parentNode as FakeElement; while (m.childNodes.length) p.insertBefore(m.childNodes[0], m); p.removeChild(m); }   // unwrap, so the next cell's paint reads the same DOM
    }
  });
  return bad;
}

test("the corpus: 300 seeded cells over every inline construct, as table cells and as refused paragraphs, each read as the stand-in's rendering shows it (renderedQuote) and painted whole; the strip that served before read 40 of them differently from marked (the review's round 3 census: lone delimiters, intraword underscores, undefined references, literal angle brackets, URLs holding delimiters, dropped tags)", () => {
  const cells = corpusCells(20260911, 300);
  assert.equal(new Set(cells).size, 300, "every cell its own");
  const bad = checkCorpus(cells, "corpus");
  assert.deepEqual(bad, [], bad.length + " of 300 cells read or paint differently from the rendering");
});

test("the hand cases of rounds 1, 2 and 3 as cells and as refused paragraphs: every seeded strip regression (`_snake_case_`, `**5 * 3 = 15**`, `~~a ~ b~~`, `_a_b_`, `___a___`, `**a*b**`, the escapes of every ASCII punctuation, the entities, `Edit <path/to/file> first`, `Map<K, V>`, the undefined footnote and reference link, the reference images, the URLs holding delimiters, the autolinks of every scheme, the non-ASCII neighbours of an underscore, the tags the sanitizer drops with their text) reads as the rendering shows it and paints whole (before: nothing painted, or a partial mark, the card offering Reveal)", () => {
  const bad = checkCorpus(HAND_CELLS, "hand");
  assert.deepEqual(bad, [], bad.length + " of " + HAND_CELLS.length + " hand cases read or paint differently from the rendering");
  // a few spelled out, as the cells show them
  const TABLE = tableNote(HAND_CELLS);
  for (const [cell, shown] of [["_snake_case_", "snake_case"], ["**5 * 3 = 15**", "5 * 3 = 15"], ["~~a ~ b~~", "a ~ b"], ["**a*b**", "a*b"], ["Edit <path/to/file> first", "Edit <path/to/file> first"], ["Map<K, V>", "Map<K, V>"],
                              ["see[^9]", "see[^9]"], ["[whiskey][nodef]", "[whiskey][nodef]"], ["https://x.test/a/__init__.py", "https://x.test/a/__init__.py"], ["<ftp://x.test/lagoon>", "ftp://x.test/lagoon"], ["<user:pass> jade", "user:pass jade"],
                              ["é_birch_", "é_birch_"], ["amber <script>alert(1)</script> amberx", "amber amberx"], ["amber ![birch][idef] amberx", "amber amberx"], ["[wildcard](http://x.test/files/*)*", "wildcard*"], ["C:\\Users\\", "C:\\Users\\"], ["`x\\`", "x\\"]] as const) {
    const r = rangeOf(TABLE, `| ${cell} |`);
    const h = highlight(TABLE, { start: r.start + 2, end: r.end - 2 });
    assert.ok(h.marks && h.marks.length, cell + ": painted");
    assert.equal(norm(h.text!), shown, cell + ": the cell's text");
    assert.equal(h.cell!.index, 0, cell + ": the first cell");
  }
});

test("prose shapes a cell cannot hold, in refused paragraphs: a quote across a hard break (two spaces or a backslash) paints, the break showing nothing (before: the needle kept the line feed against a hay with none); an emphasis pair, a link label and a link destination wrapped across a soft break strip (before: the strip read one line at a time and kept their markup); a code span across the wrap keeps its content; a code span ending in a backslash at a line end keeps it (round 2's HARD_BREAK had taken it)", () => {
  const P = (body: string): string => "# T\n\nFish &amp; " + body + "\n\nLast paragraph here.\n";
  for (const [body, quote, shown] of [
    ["Street 1  \nCity here.", "Street 1  \nCity", "Street 1City"], ["Street 1\\\nCity here.", "Street 1\\\nCity", "Street 1City"], ["orchid **ridge**   \nmike here.", "orchid **ridge**   \nmike", "orchid ridgemike"],
    ["xray\ngolf here.", "xray\ngolf", "xray golf"],
    ["uniform *nectar\ngolf* here.", "uniform *nectar\ngolf*", "uniform nectar golf"], ["**yankee\nvalley** here.", "**yankee\nvalley**", "yankee valley"],
    ["[charlie\npapa](http://x.test/bravo) here.", "[charlie\npapa](http://x.test/bravo)", "charlie papa"], ["[whiskey](http://x.test/grove\n\"T\") here.", "[whiskey](http://x.test/grove\n\"T\")", "whiskey"],
    ["`sierra *zulu*\nuniform` here.", "`sierra *zulu*\nuniform`", "sierra *zulu* uniform"],
    ["see `x\\`\nnext here.", "see `x\\`\nnext", "see x\\ next"], ["the path is `C:\\Users\\`\nmore here.", "`C:\\Users\\`", "C:\\Users\\"],
  ] as const) {
    const src = P(body);
    const h = highlight(src, rangeOf(src, quote), "P");
    assert.ok(h.marks && h.marks.length, JSON.stringify(quote) + ": painted (was null or one short)");
    assert.equal(norm(h.text!).replace(/\s+/g, " "), shown, JSON.stringify(quote) + ": the marks read what the paragraph shows");
  }
});

test("a range cut inside a construct reads as the rendering shows those characters, the block having been read whole (before: the raw slice was stripped on its own): a Raw drag begun after `**` or ended before it paints the words, in a cell and in a refused paragraph; one begun mid-line at `2024. `, `# `, `> ` or `- ` keeps them (the lead rules read the slice's start as a line's); a paragraph continuation line beginning `3. ` or `10) `, text to marked, stays; a quote over a cut escape keeps the character shown", () => {
  const CELL = "# T\n\n| Cell | Note |\n|---|---|\n| **bold words** more | n |\n| see foo\\*bar here | e |\n\nAfter.\n";
  let h = highlight(CELL, rangeOf(CELL, "bold words** more"));
  assert.ok(h.marks && h.marks.length, "after the opener (was null)"); assert.equal(norm(h.text!), "bold words more");
  h = highlight(CELL, rangeOf(CELL, "**bold words"));
  assert.ok(h.marks && h.marks.length, "before the closer (was null)"); assert.equal(norm(h.text!), "bold words");
  h = highlight(CELL, rangeOf(CELL, "see foo\\"));
  assert.ok(h.marks && h.marks.length, "cut inside the escape"); assert.equal(norm(h.text!), "see foo");
  const PROSE = "# T\n\nIntro &amp; lima 2024. It was romeo.\n\nCount &amp; the # of items today.\n\nA value &amp; > 5 means overflow.\n\nalpha &amp; - beta gamma.\n\nIt was &amp; released in\n3. The third cut was last.\n\nfirst &amp; line\n10) then more.\n\nTom &amp; **bold words** more here.\n\nLead &amp; ```papa``` tail.\n\nAfter.\n";
  for (const [quote, shown] of [["2024. It was romeo.", "2024. It was romeo."], ["# of items", "# of items"], ["> 5 means overflow", "> 5 means overflow"], ["- beta gamma", "- beta gamma"],
                                ["released in\n3. The third cut", "released in 3. The third cut"], ["3. The third cut was last.", "3. The third cut was last."], ["10) then more.", "10) then more."],
                                ["bold words** more", "bold words more"], ["**bold words", "bold words"], ["```papa```", "papa"]] as const) {
    h = highlight(PROSE, rangeOf(PROSE, quote), "P");
    assert.ok(h.marks && h.marks.length, JSON.stringify(quote) + ": painted (was null or missing its head)");
    assert.equal(norm(h.text!), shown, JSON.stringify(quote) + ": the whole quote as shown");
  }
});

test("an html block's text is the text between its tags as written, entities decoded and the elements the sanitizer drops with their text left out: a backslash escape there is the two characters it shows (`costs \\$5`, `see \\& x`; round 2 read them as escapes), a backslash right before a tag stays (`C:\\Temp\\</div>`, `C:\\Temp\\<br>`; round 2's mask read `\\<` as an escape and the needle and the scope disagreed), a `<script>` or `<template>` inside shows nothing, and a raw html table's cell reads the same", () => {
  const HTML = "# T\n\n<div>costs \\$5 raw here</div>\n\n<div>see \\& x here</div>\n\n<div>path C:\\Temp\\</div>\n\n<div>path C:\\Temp\\<br>next</div>\n\n<table><tr><td>C:\\Users\\</td><td>x</td></tr></table>\n\n<div>a <script>x</script> b <template>t</template> c</div>\n\n<div>\n\ncosts \\$5 nested here\n\n</div>\n\nAfter.\n";
  for (const [quote, shown, tag] of [["costs \\$5 raw", "costs \\$5 raw", "DIV"], ["see \\& x", "see \\& x", "DIV"], ["C:\\Temp\\", "C:\\Temp\\", "DIV"], ["path C:\\Temp\\<br>next", "path C:\\Temp\\next", "DIV"], ["C:\\Users\\", "C:\\Users\\", "TD"],
                                     ["a <script>x</script> b <template>t</template> c", "a b c", "DIV"], ["costs \\$5 nested", "costs $5 nested", "P"]] as const) {
    const h = highlight(HTML, rangeOf(HTML, quote), tag);
    assert.ok(h.marks && h.marks.length, JSON.stringify(quote) + ": painted (was null)");
    assert.equal(norm(h.text!), shown, JSON.stringify(quote) + ": the text as the block shows it");
  }
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
