// The anchor map's reading of a WRAPPED code block's lines (anchor-map.ts codeRuns, codeText; Slice 3 of
// plans/markdown-viewer.md). The viewer's fences are cut into per-line rows (code-block.ts wrapLinesHtml:
// `<span class="cl"><span class="ct">…</span></span>` per line) and the wrap drops the newline each row stands for, so a
// wrapped code element's textContent runs its lines together. The helpers put the newline back between adjacent rows,
// so a reader of the lines sees the source's structure whether the code was wrapped or not: paintRendered's fallback
// builds its hay from codeRuns (a comment across two code lines; the browser leg anchor-map-wrapped-code-browser.test.ts
// paints it over the real bundle); reader-place.ts keeps the code line at the body's top edge as the row under it, whose
// index among the rows is its line (one row per line; the Slice 3 review's round 3 retired its hit-test read of a code
// element with no rows, which the viewer never builds). Two more row helpers, codeLineAt and codeLineStart, the line of a
// DOM position and the position where a line starts, were exported here for Slice 8's exact mapping of code lines and had
// no caller in production; that mapping (anchor-map.ts walkCode) reads no row, the rows dropping only newlines the walk
// never emits, so Slice 8 deleted them, and the last test pins that nothing defines or calls them again. This node leg
// drives the helpers over a structural stand-in of the DOM (nodeType, childNodes, parentNode, data, getAttribute: the
// surface anchor-map.ts walks) built from wrapLinesHtml's own output and from the unwrapped shape, and checks the two
// shapes read alike. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import { codeRuns, codeText } from "./anchor-map";
import { wrapLinesHtml } from "./code-block";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

// ── a DOM stand-in: elements with a class attribute, text nodes with data ─────────────────────────
type N = { nodeType: number; childNodes: N[]; parentNode: N | null; data?: string; tagName?: string; cls?: string; getAttribute(n: string): string | null };
/** A node from its own fields and its children: the edges (childNodes, parentNode) are defined non-enumerable and every
 *  other object the node holds is hidden (hideEdges, ui/test-dom-shim.ts), so a failing assertion's dump of a node is its
 *  own primitives, never the tree it hangs in. */
const node = (own: Omit<N, "childNodes" | "parentNode">, kids: N[]): N => {
  const e = own as N;
  Object.defineProperty(e, "childNodes", { value: kids, writable: true, enumerable: false, configurable: true });
  Object.defineProperty(e, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
  for (const k of kids) k.parentNode = e;
  return hideEdges(e);
};
const text = (data: string): N => node({ nodeType: 3, data, getAttribute: () => null }, []);
const el = (tag: string, cls: string | null, kids: N[]): N =>
  node({ nodeType: 1, tagName: tag, cls: cls || undefined, getAttribute: (n) => (n === "class" ? cls : null) }, kids);
/** wrapLinesHtml's output (rows of one text run each, or empty; hljs spans inside a row) parsed into the stand-in. */
function parseRows(html: string): N {
  const rows: N[] = [];
  const OPEN = '<span class="cl"><span class="ct">', CLOSE = "</span></span>";
  const pieces = html.split(OPEN).slice(1);   // each piece is a row's content followed by the row's two closers
  for (const piece of pieces) {
    assert.ok(piece.endsWith(CLOSE), "a row ends with its closers: " + piece);
    const inner = piece.slice(0, -CLOSE.length);
    const kids: N[] = [];
    // a row's content: text and <span class="x">text</span> runs (enough for these fixtures)
    const parts = inner.split(/(<span class="[^"]*">[^<]*<\/span>)/).filter(Boolean);
    for (const p of parts) {
      const sm = /^<span class="([^"]*)">([^<]*)<\/span>$/.exec(p);
      kids.push(sm ? el("span", sm[1], sm[2] ? [text(sm[2])] : []) : text(p));
    }
    rows.push(el("span", "cl", [el("span", "ct", kids)]));
  }
  return el("code", "language-python", rows);
}
const D = (n: N) => n as unknown as Parameters<typeof codeRuns>[0];

const SRC = "# a comment\ndef f(x):\n    return x + 1  # trailing\n\nvalue = f(2)\n";
const HL = '<span class="hljs-comment"># a comment</span>\n<span class="hljs-keyword">def</span> f(x):\n    <span class="hljs-keyword">return</span> x + 1  <span class="hljs-comment"># trailing</span>\n\nvalue = f(2)\n';

test("codeRuns puts a newline between adjacent rows and nowhere else; codeText is the source's lines again", () => {
  const wrapped = parseRows(wrapLinesHtml(HL));
  assert.equal(wrapped.childNodes.length, 5, "five rows, the trailing newline no row");
  const runs = codeRuns(D(wrapped));
  assert.deepEqual(runs.filter((r) => !r.node).map((r) => r.text), ["\n", "\n", "\n", "\n"], "four row boundaries");
  assert.ok(runs.filter((r) => !r.node).every((r) => r.row && (r.row as unknown as N).cls === "cl"), "each boundary names the row it precedes");
  assert.equal(codeText(D(wrapped)), SRC.replace(/\n$/, ""), "the text reads as the source, less the trailing newline the wrap dropped");
  // the unwrapped shape (mdBlock before the wrap: hljs spans and text with real newlines) reads the same
  const plain = el("code", null, [el("span", "hljs-comment", [text("# a comment")]), text("\n"), el("span", "hljs-keyword", [text("def")]), text(" f(x):\n    "), el("span", "hljs-keyword", [text("return")]), text(" x + 1  "), el("span", "hljs-comment", [text("# trailing")]), text("\n\nvalue = f(2)\n")]);
  assert.equal(codeText(D(plain)), SRC);
  assert.deepEqual(codeRuns(D(plain)).filter((r) => !r.node), [], "no phantom newline where the real ones stand");
  // a text node alone is its one run
  const lone = text("abc"); const rs = codeRuns(D(lone));
  assert.equal(rs.length, 1); assert.equal(rs[0].node as unknown as N, lone); assert.equal(rs[0].text, "abc");
});

test("the Raw view's rows read the same way: `.fv-cl` rows are rows too", () => {
  const raw = el("code", "hljs", [el("span", "fv-cl", [el("span", "fv-ct", [text("one")])]), el("span", "fv-cl", [el("span", "fv-ct", [text("two")])])]);
  assert.equal(codeText(D(raw)), "one\ntwo");
  assert.deepEqual(codeRuns(D(raw)).filter((r) => !r.node).map((r) => (r.row as unknown as N).cls), ["fv-cl"], "one boundary, before the second Raw row");
});

test("codeLineAt and codeLineStart are gone (Slice 8, item 2: a code line maps by position and the mapping reads no row): no module under ui/webview defines or calls them, and anchor-map.ts's header says a cell and a code line map, not that code and tables refuse by design", () => {
  // Slice 3 exported the two for Slice 8's exact mapping of code lines and pinned here that no production module called
  // them (the Slice 3 review's round 3 had retired reader-place.ts's calls, the last). Slice 8's mapping (walkCode) needs no
  // row helper: the rows drop only the newlines, which the walk never emits, so descend and nthNonWs see through the rows to
  // the selected character, and the two were deleted with their cases here (the Slice 8 brief's open question 6, its
  // default). This pin keeps them gone and the header true: a definition or a call added later fails here until the header
  // and the plan's Slice 3 build note (item 9) say why, and the header's boundary sentence cannot drift back to the Slice 2
  // shape a cell and a code line have left.
  const UI = path.resolve(process.cwd(), "..", "ui", "webview");
  const modules = fs.readdirSync(UI).filter((f) => /\.(ts|js)$/.test(f) && f !== "anchor-map-wrapped-code.test.ts");
  const naming = modules.filter((f) => /\b(codeLineAt|codeLineStart)\s*\(/.test(fs.readFileSync(path.join(UI, f), "utf8")));
  assert.deepEqual(naming, [], "a definition or a call of codeLineAt or codeLineStart appeared under ui/webview: Slice 8 deleted the two (anchor-map.ts, code lines under a wrap); say why in the header and the plan's Slice 3 note");
  const header = fs.readFileSync(path.join(UI, "anchor-map.ts"), "utf8").split("\n").filter((l) => l.startsWith("//")).map((l) => l.replace(/^\/\/ ?/, "")).join(" ").replace(/\s+/g, " ");
  assert.match(header, /A table's cells and a code block's lines are positioned as prose is \(Slice 8 of plans\/markdown-viewer\.md: walkTable re-cuts each row as marked's splitCells does, walkCode finds each text line in its raw line\), so a selection inside a cell or a code line maps to the source/, "the header names the Slice 8 mapping");
  assert.doesNotMatch(header, /Code, tables, HTML, entity-bearing prose, and escaped link labels refuse by design/, "the Slice 2 boundary sentence: since Slice 8 a cell and a code line map, and only HTML, entity-bearing prose and escaped link labels refuse by design");
  assert.doesNotMatch(header, /have no caller in production today/, "the Slice 3 sentence about the two helpers: they are deleted, not kept");
});

// ── the stand-in's nodes inspect as their own projection (ui/test-dom-shim.ts) ────────────────────
test("a stand-in node enumerates its primitives alone, and a dump of one names neither parentNode nor childNodes", () => {
  const t = text("alpha"), row = el("span", "cl", [el("span", "ct", [t])]), code = el("code", null, [row]);
  for (const n of [code, row, t]) {
    for (const k of Object.keys(n)) assert.ok(staysEnumerable((n as any)[k]), k + " is enumerable and holds a " + typeof (n as any)[k]);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "a dump stays on the node: " + dump);
  }
  assert.ok(row.parentNode === code && code.childNodes[0] === row && t.parentNode === row.childNodes[0], "the edges still hold the tree");
  assert.equal(row.getAttribute("class"), "cl"); assert.equal(codeText(D(code)), "alpha");
});
