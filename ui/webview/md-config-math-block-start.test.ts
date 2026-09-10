// The mathBlock extension's `start` hint (math.ts) against marked's block lexer, executed over the REAL singleton
// (applyMdConfig) and read the way the anchor map reads it (anchor-map.ts sourceBlockSpans tiles every top-level token's
// raw over the note). marked 12 calls a block extension's `start` on the source less its first character and clips the
// paragraph it is about to read at the index returned plus one, so the extension is tried there next. When the
// tokenizer then REJECTS the line, the clipped paragraph resumes with a "\n" the lexer's space branch had already
// appended, so the token's raw carries one newline the source does not have, and placeTokens marks that block and every
// block after it unplaceable: every selection from there to the end of the note is refused with the paragraph reason,
// and the reader's place is wrong (the Slice 4 review, round 1; the Files pane and the feed took the grammar in this
// slice, the chat page had it before). The hint therefore names only a position where the tokenizer WILL match, and
// never the string's own start, which is one character into a line: `A $$x$$` lexed as a paragraph "A" and a display
// block " $$x$$". Synthetic notes only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { Lexer, marked } from "marked";
import { applyMdConfig } from "./md-config";
import { mathBlock } from "./math";
import { sourceBlockSpans } from "./anchor-map";

applyMdConfig();
const raws = (src: string): string[] => Lexer.lex(src).map((t) => t.raw);
const types = (src: string): string[] => Lexer.lex(src).map((t) => t.type);
const spans = (src: string): number[][] => sourceBlockSpans(src).map((s) => [s.start, s.end]);
const html = (src: string): string => marked.parse(src) as string;
// marked types an extension as a union, so the two members are read through the shape math.ts gives them
const ext = mathBlock as unknown as { start(src: string): number | undefined; tokenizer(src: string, tokens: unknown[]): unknown };
const hint = (src: string): number | undefined => ext.start(src);
/** The block table a two-paragraph note must give: the first paragraph up to the blank line, then "Last." where it stands. */
const twoBlocks = (src: string): number[][] => { const last = src.indexOf("Last."); return [[0, last - 2], [last, last + 5]]; };

test("a continuation line the block tokenizer rejects stays in its paragraph: the raws tile the source and the block table is right", () => {
  const notes: Array<[string, string]> = [
    ["display delimiters with prose after them", "Line one\n$$x$$ is inline here.\n\nLast.\n"],
    ["an opener with no closer", "Line one\n$$ not closed here.\n\nLast.\n"],
    ["an escaped bracket line", "Line one\n\\[TODO\\] fix this.\n\nLast.\n"],
    ["two prices", "Line one\n$$5 and $$10 are prices.\n\nLast.\n"],
    ["a blank formula (the tokenizer's own non-blank check)", "Line one\n$$ $$\n\nLast.\n"],
    ["display delimiters one character into the first line", "A $$display$$ inline.\n\nLast.\n"],
  ];
  for (const [why, src] of notes) {
    assert.equal(raws(src).join(""), src, why + ": the raws tile the source (a doubled newline breaks every block after it)");
    assert.deepEqual(types(src), ["paragraph", "space", "paragraph"], why + ": one paragraph, the blank line, the last paragraph");
    assert.deepEqual(spans(src), twoBlocks(src), why + ": the block table places both paragraphs where they stand");
  }
  assert.match(html(notes[0][1]), /^<p>Line one\n<span class="md-math-display">x<\/span> is inline here\.<\/p>\n<p>Last\.<\/p>\n$/,
    "the formula renders inside its paragraph, as the inline pass always rendered it");
});

test("a display block on the line after a paragraph still interrupts it: the hint's purpose", () => {
  for (const [why, src] of [
    ["$$ on the next line", "Line one\n$$x$$\n\nLast.\n"],
    ["\\[ on the next line", "Line one\n\\[x\\]\n\nLast.\n"],
    ["indented up to three spaces", "Line one\n   $$x$$\n\nLast.\n"],
    ["after a blank line", "Line one\n\n$$x$$\n\nLast.\n"],
  ] as const) {
    assert.equal(raws(src).join(""), src, why + ": the raws tile the source");
    assert.ok(types(src).includes("mathBlock"), why + ": lexed as a display block: " + types(src).join(","));
  }
  assert.deepEqual(spans("Line one\n$$x$$\n\nLast.\n"), [[0, 8], [9, 14], [16, 21]]);
  const multi = "Line one\n$$\n- x\n$$\n\nLast.\n";
  assert.equal(raws(multi).join(""), multi);
  assert.deepEqual(types(multi), ["paragraph", "mathBlock", "paragraph"], "a multi-line formula after a paragraph is one block");
  assert.doesNotMatch(html(multi), /<li>/, "the list rule never fires inside it");
  assert.deepEqual(types("$$x$$\n\nLast.\n"), ["mathBlock", "paragraph"], "a display block at the document's start needs no hint");
  // a rejected candidate is stepped over, a later one that the tokenizer accepts is named
  const later = "Line one\n$$5 prices.\n\nLast.\n\\[y\\]\n";
  assert.equal(raws(later).join(""), later);
  assert.deepEqual(types(later), ["paragraph", "space", "paragraph", "mathBlock"]);
});

test("a block construct one character into a line is not a block: the hint never names the string's own start", () => {
  for (const [why, src] of [["$$ after one character", "A $$x$$\n\nLast.\n"], ["\\[ after one character", "A \\[x\\]\n\nLast.\n"]] as const) {
    assert.deepEqual(types(src), ["paragraph", "space", "paragraph"], why + ": " + types(src).join(","));
    assert.equal(raws(src).join(""), src, why + ": the raws tile the source");
    assert.doesNotMatch(html(src), /<div class="md-math-display">/, why + ": no display block of its own");
    assert.match(html(src), /^<p>A <span class="md-math-display">x<\/span><\/p>\n/, why + ": the formula is inside the paragraph");
  }
});

test("the hint itself: the newline before a line the tokenizer accepts, undefined where it would reject, never index 0 of a line's tail", () => {
  // marked passes src.slice(1), so index 0 here is one character into the first line
  assert.equal(hint("$$x$$\n"), undefined, "the string's own start is never a line start");
  assert.equal(hint(" $$x$$\n"), undefined);
  assert.equal(hint("ne one\n$$x$$\n"), 6, "the newline before an accepted line");
  assert.equal(hint("ne one\n\\[x\\]\n"), 6);
  assert.equal(hint("ne one\n  $$x$$\n"), 6, "up to three spaces of indent");
  assert.equal(hint("ne one\n$$x$$ is inline here.\n"), undefined, "prose after the closer: the tokenizer would reject");
  assert.equal(hint("ne one\n$$ not closed\n\nLast.\n"), undefined, "no closer");
  assert.equal(hint("ne one\n$$ $$\n"), undefined, "a blank formula");
  assert.equal(hint("ne one\n\\[TODO\\] fix this.\n"), undefined, "an escaped bracket line");
  assert.equal(hint("ne one\n$$5 prices.\n\nLast.\n\\[y\\]\n"), "ne one\n$$5 prices.\n\nLast.".length, "a rejected candidate is stepped over for the next accepted one");
  assert.equal(hint("plain prose\nand more\n"), undefined);
});

test("the hint agrees with the tokenizer at every candidate: the one-pass closer memo is the same answer as running the tokenizer at each newline", () => {
  // The hint judges each `$$` or `\[` line by the first closer of its family after the opener (searched once per family
  // and reused while it lies past the opener), where the tokenizer runs its lazy regex from the line. The two must
  // agree on every string: the reference here IS the tokenizer, tried at each candidate newline in order, and the corpus
  // is every three-line combination of the shapes below, with and without a leading line, so openers with no closer, a
  // closer before an opener, a blank body, a closer at the very end of the text and both families interleaved all meet.
  const tokenize = (src: string): unknown => ext.tokenizer(src, []);
  const reference = (src: string): number | undefined => {
    for (const m of src.matchAll(/\n(?= {0,3}(?:\$\$|\\\[))/g)) if (tokenize(src.slice(m.index! + 1))) return m.index;
    return undefined;
  };
  const lines = ["Line one", "$$x$$", "$$", "x$$", "$$x$$ tail", "\\[y\\]", "\\[", "y\\]", "$$ $$", "  $$z", "z $$", "\\[TODO\\] fix", "$$5 and $$10", "", "$$$", "$$x$$$", "$$x$$  ", "\\]", "\\[\\]"];
  let checked = 0, accepted = 0;
  for (const a of lines) for (const b of lines) for (const c of lines) {
    for (const src of [a + "\n" + b + "\n" + c, a + "\n" + b + "\n" + c + "\n", "\n" + a + "\n" + b + "\n" + c]) {
      const want = reference(src);
      assert.equal(hint(src), want, "hint differs from the tokenizer on " + JSON.stringify(src));
      checked++; if (want !== undefined) accepted++;
    }
  }
  assert.ok(checked > 20000 && accepted > 1000 && accepted < checked - 1000, `the corpus exercises both answers: ${accepted} accepted of ${checked}`);
});

test("a note of candidate lines the tokenizer rejects lexes in the time of plain prose: the hint scans once per call, not once per candidate", () => {
  // What this bounds: the hint's own cost per call. A first cut of nextBlockMath ran the block tokenizer at every
  // candidate, each run scanning to the end of the note, and lexed 1,500 paragraphs whose second line opens with `$$`
  // and never closes in 13 s (round 1 of the Slice 4 review; it never shipped). The one-pass hint lexes the same note in
  // the time of plain prose, and one call over a whole note of 8,000 such paragraphs costs a fraction of a millisecond
  // (0.2 ms, measured 2026-09-09 at round 3) where the first cut scanned to the end of the note at each of the 8,000
  // candidates. The second leg calls the hint with no lexer, so no frame and no memo: the finder alone, one scan. What
  // it does NOT bound is the count of calls: marked calls every block start hint once per top-level paragraph on the
  // source that remains (marked.esm.js, the paragraph branch of blockTokens), so with round 1's hint the whole lex grew
  // as the square of the paragraph count: 8,000 paragraphs in 1.1 s plain and 3.7 s on this note against 21 ms with no
  // hints. md-block-start.ts (round 2) memoises each hint's answer per lexer frame, so every later paragraph is answered
  // from the first scan and the lex is linear: 8,000 paragraphs 38 ms plain, 53 ms on this note, 20 ms with no hints;
  // md-config-block-start-memo.test.ts holds the linearity, this test the per-call cost. The hint that shipped before
  // round 1, a bare regex match, was faster than this one and wrong: tests 1 to 5 fail on it, and so does the second
  // leg here, which it answers with a line the tokenizer rejects. Each timing is the smallest of three runs, so one
  // stall cannot fail a correct build; the bounds leave room for a loaded machine and are not benchmarks: the first cut
  // was two orders of magnitude over prose.
  const fastest = (f: () => number): { ms: number; got: number } => {
    let got = 0; const runs: number[] = [];
    for (let i = 0; i < 3; i++) { const t0 = process.hrtime.bigint(); got = f(); runs.push(Number(process.hrtime.bigint() - t0) / 1e6); }
    return { ms: Math.min(...runs), got };
  };
  const N = 1500;
  const plain = fastest(() => Lexer.lex("Line one\nline two here.\n\n".repeat(N)).length);
  const prices = fastest(() => Lexer.lex("Line one\n$$5 and $$10 are prices.\n\n".repeat(N)).length);
  const brackets = fastest(() => Lexer.lex("Line one\n\\[TODO\\] fix this.\n\n".repeat(N)).length);
  assert.equal(plain.got, N * 2); assert.equal(prices.got, N * 2); assert.equal(brackets.got, N * 2);
  const candidatesMs = Math.max(prices.ms, brackets.ms);
  assert.ok(candidatesMs < Math.max(1000, plain.ms * 8), `a note of rejected candidates took ${candidatesMs.toFixed(0)} ms per 1,500 paragraphs against ${plain.ms.toFixed(0)} ms for prose`);
  // the hint alone, one call over the whole note less its first character, as marked passes it: 8,000 candidates with
  // no closer, so a hint that scans to the end of the note per candidate pays for every one of them
  const big = 8000;
  for (const [why, para] of [["two prices", "Line one\n$$5 and $$10 are prices.\n\n"], ["an escaped bracket line", "Line one\n\\[TODO\\] fix this.\n\n"]] as const) {
    const note = para.repeat(big).slice(1);
    const call = fastest(() => hint(note) ?? -1);
    assert.equal(call.got, -1, why + ": no line of the note is a display block");
    assert.ok(call.ms < 100, `${why}: one call of the hint over ${big.toLocaleString("en-US")} rejected candidates took ${call.ms.toFixed(1)} ms`);
  }
});
