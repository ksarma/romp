// paragraphAt and changeGroups (file-comments-model.ts) read line boundaries by the viewer's three-ending rule
// (LINE_ENDING: a CRLF as one ending, a lone CR, an LF), the rule the Raw rows, anchor-map's rawOffsetToLine (the Reveal
// title, the landing cue) and lineStartOffset followed since Slice 7 of plans/markdown-viewer.md (item 7). The Slice 7
// review's closing round found the two paragraph readers still on LF alone: on a CR-only file every pending change fell
// into ONE group titled by the document's first sixty characters flattened, and a blank line's "line N" title counted
// no row, where the Reveal title beside it and the rows it named counted every CR; on a CRLF file a paragraph ended
// between its CR and its LF. The cases run the pure functions over the notes-api note joined with each of the three
// endings: the CR copy's geometry is the LF copy's offset for offset (both endings are one character), the CRLF copy's
// is the LF copy's shifted by the endings before each bound; a seeded fuzz over texts mixing the three holds paragraphAt
// to an independent row-based oracle and a blank paragraph's line title to rawOffsetToLine and lineStartOffset. Pure
// functions, no DOM. Synthetic text throughout (the doc screenshots' notes-api world, placeholder ids).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { type Hunk, changeCards, changeGroups, paragraphAt, lineStartOffset } from "./file-comments-model";
import { rawOffsetToLine } from "./anchor-map";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const MODEL = web("file-comments-model.ts");

// ── fixtures: the notes-api note, joined with each ending ──────────────────────────────────────────
const LINES = ["# Report", "", "## Findings", "The api session cut p95 latency by 40% and the p99 by 10%.", "",
  "We recommend shipping the cache in v1.2.", "", "Risks remain in the fallback path.", "", "Next steps: measure again.", ""];
const note = (nl: string): string => LINES.join(nl);
const ENDINGS = [["LF", "\n"], ["CRLF", "\r\n"], ["CR", "\r"]] as const;
const T0 = 1757145600000;
const H = (id: string, kind: Hunk["kind"], from: number, to: number, oldText: string, newText: string, ts = T0 - 90000): Hunk =>
  ({ id, author: "api", ts, kind, curFrom: from, curTo: to, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const at = (src: string, needle: string): number => { const i = src.indexOf(needle); assert.ok(i >= 0, needle); return i; };
/** The changes suite's five changes, placed in `src` by their needles (on the CR copy the offsets are the LF copy's). */
function five(src: string): Hunk[] {
  return [
    H("h1", "sub", at(src, "cut"), at(src, "cut") + 3, "reduced", "cut"),
    H("h2", "ins", at(src, " and the p99"), at(src, " and the p99") + " and the p99 by 10%".length, "", " and the p99 by 10%", T0 - 80000),
    H("h3", "del", at(src, "shipping"), at(src, "shipping"), "quickly ", "", T0 - 70000),
    H("h4", "sub", at(src, "remain"), at(src, "remain") + 6, "persist", "remain", T0 - 60000),
    H("h5", "ins", at(src, " again"), at(src, " again") + 6, "", " again", T0 - 50000),
  ];
}
const TITLES = ["## Findings", "We recommend shipping the cache in v1.2.", "Risks remain in the fallback path.", "Next steps: measure again."];
const MEMBERS = [["h1", "h2"], ["h3"], ["h4"], ["h5"]];
const groupsOf = (src: string) => changeGroups(changeCards(null, five(src)), src);

test("the CR-only copy: the same paragraph as the LF copy at every offset (both endings are one character)", () => {
  const lf = note("\n"), cr = note("\r");
  assert.equal(cr.length, lf.length);
  assert.deepEqual(paragraphAt(cr, at(cr, "cut")), { start: at(cr, "## Findings"), end: at(cr, "10%.") + 4 }, "the heading and the line under it, one paragraph, as on the LF copy");
  assert.deepEqual(paragraphAt(cr, 9), { start: 9, end: 9 }, "a blank line is its own empty paragraph on a CR file too");
  for (let p = 0; p <= lf.length; p++) assert.deepEqual(paragraphAt(cr, p), paragraphAt(lf, p), "offset " + p);
});

test("the CR-only copy: four groups named by their first lines with the LF copy's members and bounds, and a blank line titled by its row", () => {
  const cr = note("\r"), lf = note("\n");
  const groups = groupsOf(cr);
  assert.deepEqual(groups.map((g) => g.title), TITLES, "one group per paragraph, never one group titled by the whole document flattened");
  assert.deepEqual(groups.map((g) => g.changes.map((c) => c.id)), MEMBERS);
  assert.deepEqual(groups.map((g) => [g.key, g.start, g.end]), groupsOf(lf).map((g) => [g.key, g.start, g.end]), "the same bounds offset for offset");
  const blank = changeGroups(changeCards(null, [H("d", "del", 9, 9, "gone\r", "")]), cr);
  assert.equal(blank[0].title, "line 2", "a deletion at a blank line: the row's number, every CR before it a row");
  assert.equal(blank[0].title, "line " + (rawOffsetToLine(cr, 9) + 1), "the number the Reveal title beside it carries");
});

test("the CRLF copy: the LF copy's groups with every bound shifted by the endings before it; a paragraph ends before its CRLF, never between the CR and the LF", () => {
  const crlf = note("\r\n"), lf = note("\n");
  const shift = (o: number): number => o + (lf.slice(0, o).match(/\n/g) || []).length;
  const groups = groupsOf(crlf);
  assert.deepEqual(groups.map((g) => g.title), TITLES);
  assert.deepEqual(groups.map((g) => g.changes.map((c) => c.id)), MEMBERS);
  assert.deepEqual(groups.map((g) => [g.start, g.end]), groupsOf(lf).map((g) => [shift(g.start), shift(g.end)]));
  const pr = paragraphAt(crlf, at(crlf, "cut"));
  assert.equal(crlf.slice(pr.start, pr.end), "## Findings\r\nThe api session cut p95 latency by 40% and the p99 by 10%.", "the paragraph's text holds its inner CRLF whole and stops before the closing one");
  assert.equal(crlf[pr.end], "\r", "the end is the CRLF's first character, not its LF with the CR inside the paragraph");
  const blankAt = at(crlf, "\r\n\r\n") + 2;
  const blank = changeGroups(changeCards(null, [H("d", "del", blankAt, blankAt, "gone\r\n", "")]), crlf);
  assert.equal(blank[0].title, "line 2");
  assert.deepEqual([blank[0].start, blank[0].end], [blankAt, blankAt], "the blank row is empty: its end is its start, not the LF of its CRLF");
});

test("an offset on an ending's own character lies on the line the ending closes, the LF of a CRLF included, as rawOffsetToLine places it", () => {
  for (const [name, nl] of ENDINGS) {
    const src = note(nl);
    const closing = at(src, "10%.") + 4;                      // the ending's first character
    const para = paragraphAt(src, at(src, "cut"));
    for (let k = 0; k < nl.length; k++) {
      assert.deepEqual(paragraphAt(src, closing + k), para, name + ": character " + k + " of the ending closing the Findings paragraph");
      assert.equal(rawOffsetToLine(src, closing + k), rawOffsetToLine(src, at(src, "cut")), name + ": the map agrees");
    }
    assert.deepEqual(paragraphAt(src, closing + nl.length), { start: closing + nl.length, end: closing + nl.length }, name + ": the blank row after starts past the whole ending");
    assert.deepEqual(paragraphAt(src, src.length), { start: src.length, end: src.length }, name + ": past the end, empty, never throws");
  }
});

/** The rows of `src` by an independent split: [start, end) per row, a trailing ending yielding a last, empty row. */
function rowsOf(src: string): { start: number; end: number }[] {
  const out: { start: number; end: number }[] = [];
  const ending = /\r\n|\r|\n/g;
  let at = 0, m: RegExpExecArray | null;
  while ((m = ending.exec(src)) !== null) { out.push({ start: at, end: m.index }); at = m.index + m[0].length; }
  out.push({ start: at, end: src.length });
  return out;
}
/** paragraphAt's rule over those rows: the row holding `p` (the last row starting at or before it) if blank, else the
 *  run of non-blank rows around it. */
function oracle(src: string, p: number): { start: number; end: number; blank: boolean } {
  const rows = rowsOf(src);
  const isBlank = (r: { start: number; end: number }) => /^\s*$/.test(src.slice(r.start, r.end));
  let k = 0;
  while (k + 1 < rows.length && rows[k + 1].start <= p) k++;
  if (isBlank(rows[k])) return { start: rows[k].start, end: rows[k].end, blank: true };
  let a = k, b = k;
  while (a > 0 && !isBlank(rows[a - 1])) a--;
  while (b + 1 < rows.length && !isBlank(rows[b + 1])) b++;
  return { start: rows[a].start, end: rows[b].end, blank: false };
}

test("seeded fuzz: paragraphAt matches the row oracle over every offset of texts mixing the three endings, and a blank paragraph's title is the map's row and lineStartOffset's inverse", () => {
  // A small LCG (seeded, so a red run names the source): letters, a space and the three endings.
  let seed = 0x5eed7;
  const rnd = (n: number) => { seed = (seed * 1103515245 + 12345) >>> 0; return seed % n; };
  const alphabet = ["a", "b", " ", "\n", "\r", "\r\n"];
  for (let run = 0; run < 400; run++) {
    const len = rnd(24);
    let src = "";
    for (let i = 0; i < len; i++) src += alphabet[rnd(alphabet.length)];
    const shown = JSON.stringify(src);
    for (let p = 0; p <= src.length; p++) {
      const want = oracle(src, p);
      assert.deepEqual(paragraphAt(src, p), { start: want.start, end: want.end }, "offset " + p + " of " + shown);
      if (!want.blank) continue;
      const [g] = changeGroups(changeCards(null, [H("d", "del", p, p, "", "")]), src);
      const row = rawOffsetToLine(src, p);
      assert.equal(g.title, "line " + (row + 1), "the blank paragraph's title at offset " + p + " of " + shown);
      assert.equal(lineStartOffset(src, row), want.start, "the row's start at offset " + p + " of " + shown);
    }
  }
});

test("one rule in the module: LINE_ENDING is the viewer's RAW_ROW_SPLIT, and the paragraph readers and lineStartOffset read it, no LF-only search left", () => {
  assert.match(MODEL, /\nexport const LINE_ENDING = \/\\r\\n\|\\r\|\\n\/;\n/, "the three endings, a CRLF first so it is one ending");
  assert.match(web("file-view.ts"), /\n(?:export )?const RAW_ROW_SPLIT = \/\\r\\n\|\\r\|\\n\/;\n/, "the Raw rows' split: the same three endings in the same order");
  const body = (name: string): string => {
    const i = MODEL.indexOf("export function " + name + "(");
    assert.ok(i >= 0, name);
    return MODEL.slice(i, MODEL.indexOf("\n}\n", i));
  };
  for (const fn of ["paragraphAt", "changeGroups", "lineStartOffset"]) {
    assert.doesNotMatch(body(fn), /(?:indexOf|lastIndexOf|split)\("\\n"\)|\/\\n\/g/, fn + " searches no LF alone");
  }
  assert.match(body("lineStartOffset"), /new RegExp\(LINE_ENDING\.source, "g"\)/, "the row walk reads the shared rule");
  assert.match(body("changeGroups"), /\.split\(LINE_ENDING\)\.map\(\(l\) => l\.trim\(\)\)/, "the title's first line by the shared rule");
  assert.match(body("changeGroups"), /const line = lineNumberAt\(text, pr\.start\);/, "the title's line by the shared rule");
  assert.match(MODEL, /const ending = new RegExp\(LINE_ENDING\.source, "g"\);\n\s*let n = 1, m: RegExpExecArray \| null;\n\s*while \(\(m = ending\.exec\(text\)\) !== null && m\.index < at\) n\+\+;/, "lineNumberAt counts the endings before a row start, a CRLF once");
});
