// lineStartOffset (file-comments-model.ts) inverts anchor-map's rawOffsetToLine: the composer's Switch to Raw offer
// (file-comments.ts switchToRaw) scrolls to `lineStartOffset(src, r.blockStartLine)` when the refused passage has no
// verbatim copy in the source (inline markup inside an HTML block, say), and `blockStartLine` is the row
// rawOffsetToLine counted for the block's start. Slice 7 of plans/markdown-viewer.md (item 7) taught the map and the
// Raw view to end a row at a CRLF, a lone CR or an LF, a CRLF as one ending, and left this walk on LF alone (the
// review's round 1): on a CR-only file it found no LF, answered source.length (its "past the last row" answer), and the
// offer centred the last rows of the file with the refused block out of view, where the LF and CRLF copies of the same
// note centred the block. The walk counts the three endings now. Pure functions, no DOM; the oracle is an independent
// split on the same three endings, and a seeded fuzz holds the two counters to each other over every offset.
// Synthetic text throughout (the doc screenshots' notes-api world).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { lineStartOffset } from "./file-comments-model";
import { rawOffsetToLine } from "./anchor-map";

/** The rows' start offsets by an independent count: each piece of the three-ending split starts where the previous
 *  piece's ending stopped (a trailing ending yields a last, empty row, as the map numbers it). */
function rowStarts(src: string): number[] {
  const starts = [0];
  const ending = /\r\n|\r|\n/g;
  let m: RegExpExecArray | null;
  while ((m = ending.exec(src)) !== null) starts.push(m.index + m[0].length);
  return starts;
}

test("an LF source: the row starts as before, past the last row the end", () => {
  assert.equal(lineStartOffset("ab\ncd\nef", 0), 0);
  assert.equal(lineStartOffset("ab\ncd\nef", 1), 3);
  assert.equal(lineStartOffset("ab\ncd\nef", 2), 6);
  assert.equal(lineStartOffset("ab\ncd\nef", 9), 8, "past the last row: the end");
  assert.equal(lineStartOffset("", 0), 0);
  assert.equal(lineStartOffset("", 3), 0);
});

test("a CRLF source: one ending per row, the row starts after the LF", () => {
  assert.equal(lineStartOffset("ab\r\ncd\r\nef", 0), 0);
  assert.equal(lineStartOffset("ab\r\ncd\r\nef", 1), 4);
  assert.equal(lineStartOffset("ab\r\ncd\r\nef", 2), 8);
  assert.equal(lineStartOffset("ab\r\ncd\r\nef", 9), 10, "past the last row: the end");
});

test("a CR-only source: a lone CR ends a row (the round 1 finding: LF alone found no row and answered the end)", () => {
  assert.equal(lineStartOffset("ab\rcd\ref", 0), 0);
  assert.equal(lineStartOffset("ab\rcd\ref", 1), 3, "row 1 starts after the first CR, not at the file's end");
  assert.equal(lineStartOffset("ab\rcd\ref", 2), 6);
  assert.equal(lineStartOffset("ab\rcd\ref", 9), 8, "past the last row: the end");
});

test("mixed endings, blank rows and a CR right before a CRLF", () => {
  // rows: "a" | "b" | "c" | "d"
  assert.deepEqual([0, 1, 2, 3].map((n) => lineStartOffset("a\r\nb\rc\nd", n)), [0, 3, 5, 7]);
  // rows: "a" | "" (the lone CR closes it; the CRLF that follows is one ending, not a CR and an LF) | "b"
  assert.deepEqual([0, 1, 2].map((n) => lineStartOffset("a\r\r\nb", n)), [0, 2, 4]);
  // blank rows: "" | "" | "" (the trailing ending yields an empty last row, as the map numbers it)
  assert.deepEqual([0, 1, 2, 3].map((n) => lineStartOffset("\n\n", n)), [0, 1, 2, 2]);
  assert.deepEqual([0, 1, 2, 3].map((n) => lineStartOffset("\r\r", n)), [0, 1, 2, 2]);
});

test("the Switch to Raw scene: the block's row start on a CR-only note is the block's offset, as on its LF and CRLF twins", () => {
  const para = (i: number) => `Paragraph ${i}: the api session measured the cache under load and wrote the numbers up.`;
  const block = '<div align="center"><p>harbor <b>bold</b> theta words</p></div>';
  const note = (nl: string) =>
    ["# Report", ...Array.from({ length: 25 }, (_, i) => para(i + 1)), block, ...Array.from({ length: 7 }, (_, i) => para(26 + i))].join(nl + nl) + nl;
  for (const [name, nl] of [["LF", "\n"], ["CRLF", "\r\n"], ["CR", "\r"]] as const) {
    const src = note(nl);
    const blockStartOffset = src.indexOf(block);
    const blockStartLine = rawOffsetToLine(src, blockStartOffset);         // what the refusal carries
    assert.equal(blockStartLine, 52, name + ": the block's row is the same in all three");
    assert.equal(lineStartOffset(src, blockStartLine), blockStartOffset, name + ": the offer scrolls to the block's row start, never the end");
    assert.notEqual(lineStartOffset(src, blockStartLine), src.length, name + ": not the file's end");
  }
});

test("seeded fuzz: lineStartOffset and rawOffsetToLine invert each other over every offset of sources mixing the three endings", () => {
  // A small LCG (seeded, so a red run names the source): sources over letters, a space and the three endings.
  let seed = 0x5eed7;
  const rnd = (n: number) => { seed = (seed * 1103515245 + 12345) >>> 0; return seed % n; };
  const alphabet = ["a", "b", " ", "\n", "\r", "\r\n"];
  for (let run = 0; run < 400; run++) {
    const len = rnd(24);
    let src = "";
    for (let i = 0; i < len; i++) src += alphabet[rnd(alphabet.length)];
    const starts = rowStarts(src), rows = starts.length;
    const shown = JSON.stringify(src);
    for (let k = 0; k < rows; k++) assert.equal(lineStartOffset(src, k), starts[k], `row ${k} of ${shown}`);
    assert.equal(lineStartOffset(src, rows), src.length, `past the last row of ${shown}`);
    assert.equal(lineStartOffset(src, rows + 3), src.length, `far past the last row of ${shown}`);
    // the round trip: a row's start lies on that row; every offset lies on the row whose start is at or before it and
    // before the next row's start (an offset on an ending's own character lies on the row the ending closes)
    for (let k = 0; k < rows; k++) assert.equal(rawOffsetToLine(src, lineStartOffset(src, k)), k, `row ${k}'s start maps back to row ${k} in ${shown}`);
    for (let off = 0; off <= src.length; off++) {
      const k = rawOffsetToLine(src, off);
      const start = lineStartOffset(src, k), next = lineStartOffset(src, k + 1);
      assert.ok(start <= off, `offset ${off} of ${shown}: row ${k} starts at ${start}, after it`);
      assert.ok(off < next || (k === rows - 1 && off === src.length), `offset ${off} of ${shown}: row ${k + 1} starts at ${next}, at or before it`);
    }
  }
});
