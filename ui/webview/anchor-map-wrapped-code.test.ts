// The anchor map's reading of a WRAPPED code block's lines (anchor-map.ts codeRuns, codeText, codeLineAt, codeLineStart;
// Slice 3 of plans/markdown-viewer.md). The viewer's fences are cut into per-line rows (code-block.ts wrapLinesHtml:
// `<span class="cl"><span class="ct">…</span></span>` per line) and the wrap drops the newline each row stands for, so a
// wrapped code element's textContent runs its lines together. The helpers put the newline back between adjacent rows,
// so a reader of the lines sees the source's structure whether the code was wrapped or not: paintRendered's fallback
// builds its hay from codeRuns (a comment across two code lines; the browser leg anchor-map-wrapped-code-browser.test.ts
// paints it over the real bundle); codeLineAt and codeLineStart are exported for Slice 8's mapping and have no caller in
// production today (the last test pins that, and that anchor-map.ts's header says so); reader-place.ts keeps the code
// line at the body's top edge as the row under it, whose index among the rows is the line codeLineAt gives any position
// in that row (one row per line; the Slice 3 review's round 3 retired its hit-test read of a code element with no rows,
// which the viewer never builds). This node leg drives the helpers over a structural stand-in of the DOM (nodeType,
// childNodes, parentNode, data, getAttribute: the surface anchor-map.ts walks) built from wrapLinesHtml's own output and
// from the unwrapped shape, and checks the two shapes read alike. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { codeRuns, codeText, codeLineAt, codeLineStart } from "./anchor-map";
import { wrapLinesHtml } from "./code-block";

// ── a DOM stand-in: elements with a class attribute, text nodes with data ─────────────────────────
type N = { nodeType: number; childNodes: N[]; parentNode: N | null; data?: string; tagName?: string; cls?: string; getAttribute(n: string): string | null };
const text = (data: string): N => ({ nodeType: 3, childNodes: [], parentNode: null, data, getAttribute: () => null });
const el = (tag: string, cls: string | null, kids: N[]): N => {
  const e: N = { nodeType: 1, childNodes: kids, parentNode: null, tagName: tag, cls: cls || undefined, getAttribute: (n) => (n === "class" ? cls : null) };
  for (const k of kids) k.parentNode = e;
  return e;
};
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

test("codeLineAt: the line of a DOM position, real and row newlines alike; the end of a row and the start of the next are one character offset and two lines", () => {
  const wrapped = parseRows(wrapLinesHtml(HL));
  const rows = wrapped.childNodes;
  const texts = (row: N): N[] => { const out: N[] = []; const visit = (n: N) => { if (n.nodeType === 3) out.push(n); else n.childNodes.forEach(visit); }; visit(row); return out; };
  const L = (node: N, offset: number) => codeLineAt(D(wrapped), D(node), offset);
  const t0 = texts(rows[0])[0];   // "# a comment"
  assert.equal(L(t0, 0), 0, "the first character");
  assert.equal(L(t0, t0.data!.length), 0, "the end of row 0's text is line 0...");
  const t1 = texts(rows[1])[0];   // "def"
  assert.equal(L(t1, 0), 1, "...and the start of row 1's text is line 1, though the two are the same character offset once the newline is gone");
  assert.equal(L(texts(rows[2])[1], 0), 2, "inside row 2");
  assert.equal(L(texts(rows[4])[0], 3), 4, "past the empty row: line 4");
  // element positions, as caretRangeFromPoint gives them: before a row, inside the empty row, at the code's end
  assert.equal(L(wrapped, 1), 1, "the caret before row 1 (the code element, child index 1) is line 1");
  assert.equal(L(wrapped, 3), 3, "before the empty row: line 3");
  assert.equal(L(rows[3].childNodes[0], 0), 3, "inside the empty row's .ct: line 3");
  assert.equal(L(wrapped, rows.length), 4, "at the code's end: the last line");
  assert.equal(codeLineAt(D(wrapped), D(text("elsewhere")), 0), -1, "a position not under the code");
  // the unwrapped shape agrees line for line (one text node with real newlines)
  const plain = el("code", null, [text(SRC)]);
  const P = (offset: number) => codeLineAt(D(plain), D(plain.childNodes[0]), offset);
  assert.equal(P(SRC.indexOf("def")), 1);
  assert.equal(P(SRC.indexOf("return")), 2);
  assert.equal(P(SRC.indexOf("value")), 4);
  assert.equal(P(SRC.indexOf("\n\n") + 1), 3, "between the two newlines: the empty line");
  assert.equal(codeLineAt(D(plain), D(plain), 1), 5, "at the element's end: after every newline, the trailing one included (the line after the last, as a caret past it is)");
});

test("codeLineStart: where a line starts, in the wrapped and the unwrapped shape; an empty row is its element; past the end is null", () => {
  const wrapped = parseRows(wrapLinesHtml(HL));
  const rows = wrapped.childNodes;
  const firstText = (row: N): N => { let n = row; while (n.nodeType !== 3) n = n.childNodes[0]; return n; };
  const s0 = codeLineStart(D(wrapped), 0)!; assert.equal(s0.node as unknown as N, firstText(rows[0])); assert.equal(s0.offset, 0);
  const s1 = codeLineStart(D(wrapped), 1)!; assert.equal(s1.node as unknown as N, firstText(rows[1]), "line 1 starts at row 1's first text node"); assert.equal(s1.offset, 0);
  const s2 = codeLineStart(D(wrapped), 2)!; assert.equal((s2.node as unknown as N).data, "    ", "line 2's first run is its indent"); assert.equal(s2.offset, 0);
  const s3 = codeLineStart(D(wrapped), 3)!; assert.equal(s3.node as unknown as N, rows[3], "the empty line has no text node: its row stands for it"); assert.equal(s3.offset, 0);
  const s4 = codeLineStart(D(wrapped), 4)!; assert.equal((s4.node as unknown as N).data, "value = f(2)");
  assert.equal(codeLineStart(D(wrapped), 5), null, "no sixth line");
  // unwrapped: the character after the k-th newline, in the same text node or the next
  const plain = el("code", null, [text("a\nb"), text("\nc\n")]);
  assert.deepEqual(codeLineStart(D(plain), 1), { node: plain.childNodes[0], offset: 2 });
  assert.deepEqual(codeLineStart(D(plain), 2), { node: plain.childNodes[1], offset: 1 }, "a newline ending a node starts the line in the next node");
  assert.deepEqual(codeLineStart(D(plain), 3), { node: plain.childNodes[1], offset: 3 }, "the newline that ends the text: the end position");
  assert.equal(codeLineStart(D(plain), 4), null);
  assert.equal(codeLineStart(D(el("code", null, [])), 0), null, "no text, no line");
});

test("the Raw view's rows read the same way: `.fv-cl` rows are rows too", () => {
  const raw = el("code", "hljs", [el("span", "fv-cl", [el("span", "fv-ct", [text("one")])]), el("span", "fv-cl", [el("span", "fv-ct", [text("two")])])]);
  assert.equal(codeText(D(raw)), "one\ntwo");
  assert.equal(codeLineAt(D(raw), D(raw.childNodes[0].childNodes[0].childNodes[0]), 3), 0); assert.equal(codeLineAt(D(raw), D(raw.childNodes[1].childNodes[0].childNodes[0]), 0), 1);
});

test("codeLineAt and codeLineStart have no caller in production: exported for Slice 8's mapping, and anchor-map.ts's header says so", () => {
  // Round 3 of the Slice 3 review retired reader-place.ts's calls, the last in production, and wrote that the two stay
  // for paintRendered's fallback, which reads codeRuns and neither of them (the final fixes after round 3). The header
  // now says what is true; this pin keeps it true: a caller added later fails here until the header and the plan's
  // Slice 3 build note (item 9) are updated.
  const UI = path.resolve(process.cwd(), "..", "ui", "webview");
  const production = fs.readdirSync(UI).filter((f) => /\.(ts|js)$/.test(f) && !/\.test\.(ts|js)$/.test(f) && f !== "anchor-map.ts" && f !== "real-viewer-leg.ts");
  const callers = production.filter((f) => /\b(codeLineAt|codeLineStart)\s*\(/.test(fs.readFileSync(path.join(UI, f), "utf8")));
  assert.deepEqual(callers, [], "a production caller of codeLineAt or codeLineStart appeared: update anchor-map.ts's header (code lines under a wrap) and the plan");
  const header = fs.readFileSync(path.join(UI, "anchor-map.ts"), "utf8").split("\n").filter((l) => l.startsWith("//")).map((l) => l.replace(/^\/\/ ?/, "")).join(" ");
  assert.match(header, /codeLineAt and codeLineStart, the line of a DOM position and the position where a line starts, are exported for Slice 8's exact mapping of code lines and have no caller in production today/);
  assert.doesNotMatch(header, /codeLineAt and codeLineStart stay for paintRendered's fallback/, "the fallback reads codeRuns; the round 3 sentence was not true");
});
