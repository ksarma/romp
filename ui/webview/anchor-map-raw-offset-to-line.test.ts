// rawOffsetToLine (anchor-map.ts), the Raw row of a source offset counted over the three endings (Slice 7 of
// plans/markdown-viewer.md, contract C6), on the cost side: the count runs on the string's native search, never a walk
// over every character up to the offset. Slice 7's build counted with a charCodeAt loop, about twenty times the LF-only
// indexOf loop it replaced at the end of a 2 MB text (the viewer's cap), and the Comments panel computes this once per
// Reveal title on every render (file-comments.ts renderCard and renderChangeCard) and once per Reveal (landOn), so a
// panel over a large file with its cards near the end spent a quarter of a second per render where main spent ten
// milliseconds (review round 1). The bound is a same-run ratio against the pre-Slice 7 body, run interleaved over the
// same text, so load moves both legs together; the seeded cases pin that the faster count still answers the split's
// row at every offset of a text mixing CRLF, a lone CR and LF (anchor-map.test.ts pins the hand-written cases).
import { test } from "node:test";
import assert from "node:assert/strict";
import { rawOffsetToLine } from "./anchor-map";

/** The body before Slice 7 (LF alone, one native search per row): what main paid for a Reveal title, the ratio's reference. */
function lfOnlyLine(source: string, offset: number): number {
  const upto = Math.max(0, Math.min(offset, source.length));
  let line = 0, i = -1;
  while ((i = source.indexOf("\n", i + 1)) !== -1 && i < upto) line++;
  return line;
}
/** The row that holds `offset` by the viewer's split alone (contract C6): the endings whose last character lies before it. */
function rowBySplit(text: string, offset: number): number {
  let row = 0;
  for (const m of text.matchAll(/\r\n|\r|\n/g)) if ((m.index as number) + m[0].length <= offset) row++; else break;
  return row;
}
function flatText(lineText: string, ending: string, chars: number): string {
  return new Array(Math.ceil(chars / (lineText.length + ending.length))).fill(lineText + ending).join("");
}
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

test("at the end of a 2 MB text, rawOffsetToLine costs at most a few times the pre-Slice 7 LF-only native count, on an LF and on a CRLF file, for fifty Reveal titles in the file's last third (before: about twenty times, a per-character walk)", () => {
  const MB = 1024 * 1024;
  for (const [what, ending] of [["LF", "\n"], ["CRLF", "\r\n"]] as Array<[string, string]>) {
    const text = flatText("lorem ipsum dolor sit amet ".repeat(3), ending, 2 * MB);
    // fifty cards' offsets in the last third of the file: the panel's Reveal titles on one render
    const offsets = Array.from({ length: 50 }, (_, i) => Math.floor(text.length * (2 / 3 + i / 150)));
    for (const o of offsets) { assert.equal(rawOffsetToLine(text, o), rowBySplit(text, o), what + ": the row at " + o); lfOnlyLine(text, o); }   // warm both
    // eight interleaved passes; the best pass's ratio is the structural one, a pass the scheduler interrupted is ignored
    let best = Infinity;
    for (let pass = 0; pass < 8; pass++) {
      const t0 = performance.now();
      for (const o of offsets) lfOnlyLine(text, o);
      const t1 = performance.now();
      for (const o of offsets) rawOffsetToLine(text, o);
      const t2 = performance.now();
      best = Math.min(best, (t2 - t1) / Math.max(t1 - t0, 0.01));
    }
    assert.ok(best <= 6, what + ": rawOffsetToLine over fifty Reveal titles took " + best.toFixed(1) + "x the LF-only native count (a per-character walk takes about twenty times; two native searches take one to two, and six is the loose bound for a loaded box)");
  }
});

test("seeded texts mixing CRLF, a lone CR and LF: rawOffsetToLine answers the split's row at every offset, the ending's own characters on the row it closes and the LF of a CRLF counted once, at the LF", () => {
  const seed = 0x53_37_c6;   // fixed: the cases are the same in every run, a failure names the text
  const rnd = mulberry32(seed);
  const pick = <T>(xs: T[]): T => xs[Math.floor(rnd() * xs.length)];
  const alphabet = ["a", "b", " ", "\r", "\n", "\r\n", "\r", "\n"];
  for (let c = 0; c < 400; c++) {
    let text = "";
    for (let n = Math.floor(rnd() * 24); n > 0; n--) text += pick(alphabet);
    for (let n = 0; n <= text.length + 2; n++) {
      assert.equal(rawOffsetToLine(text, n), rowBySplit(text, n), "seed " + seed + ", case " + c + ", text " + JSON.stringify(text) + ", offset " + n);
    }
  }
  // one long text, the offsets sampled: the searches meet every ending kind many times
  let long = "";
  for (let n = 0; n < 20000; n++) long += pick(["word", "ab", "\r", "\n", "\r\n", "\r\r", "\n\r", "\r\n\r\n"]);
  for (let k = 0; k < 300; k++) {
    const n = Math.floor(rnd() * (long.length + 3));
    assert.equal(rawOffsetToLine(long, n), rowBySplit(long, n), "seed " + seed + ", long text, offset " + n);
  }
  assert.equal(rawOffsetToLine(long, -4), 0, "a negative offset is the first row");
  assert.equal(rawOffsetToLine(long, long.length + 99), rowBySplit(long, long.length), "past the end, the count over the whole text (the callers clamp to the last row)");
});
