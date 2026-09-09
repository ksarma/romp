// The block-start hints' cost, and the memo that bounds it (md-block-start.ts, math.ts). marked 12 calls every block
// extension's `start` hint before EVERY top-level paragraph, on the whole remaining source, so a hint that scans the
// rest of the note made the lex quadratic in the paragraph count: a 272 KB note of 8,000 one-line paragraphs took 1.3 s
// on the singleton against 34 ms with no hint, and a 200 KB transcript-sized reply twice the base's time (the Slice 4
// review, round 2). The remedy is a per-frame memo of the hint's answer, exact because within one blockTokens call the
// sources are suffixes of one another, plus the same memo for the math tokenizer's closer search. These tests hold the
// memoised lex equal to the plain one on every shape that exercises the frames (quotes, callouts, list items, rejected
// and accepted candidates), the two-step block tokenizer equal to the lazy regex it replaced, the finder called once per
// frame (on a probe extension, and on the math hint itself through the frame it writes), and the lex linear in the
// paragraph count, timed as the median ratio of one large lex to as many small lexes as make up the same paragraphs, so
// contention falls on both sides of the ratio alike (the `linear` helper says what was measured). Synthetic notes only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { Marked, marked } from "marked";
import type { TokenizerAndRendererExtension } from "marked";
import { applyMdConfig, callout, mdExtensions } from "./md-config";
import { mathBlock, mathInline } from "./math";
import { frameOf, memoBlockStart } from "./md-block-start";

applyMdConfig();
type Ext = { start(this: unknown, src: string): number | undefined; tokenizer(this: unknown, src: string, tokens: unknown[]): { raw: string; text: string } | undefined };
const ext = mathBlock as unknown as Ext;
/** The extension's two functions called with no lexer: the plain path, no frame, no memo. */
const plainStart = (src: string): number | undefined => ext.start.call({}, src);
const plainTokenizer = (src: string): { raw: string; text: string } | undefined => ext.tokenizer.call({}, src, []);
/** The token's two fields the lazy regex also produced, for the comparison with it. */
const rawText = (t: { raw: string; text: string } | undefined): { raw: string; text: string } | undefined => (t ? { raw: t.raw, text: t.text } : undefined);

/** The singleton's grammar on a fresh instance whose block hint (the math one, the one hint the grammar registers: the
 *  callout has none, its `>` line being a paragraph interrupt marked's own rule knows, md-config.ts) and math tokenizer run
 *  the plain path every time: the hint called with no lexer, so no frame and no memo. */
function plainInstance(): Marked {
  const m = new Marked(...mdExtensions);
  m.setOptions({ gfm: true, breaks: false });
  const e = m.defaults.extensions as unknown as { startBlock: Array<(this: unknown, src: string) => number | undefined>; block: Array<(src: string, tokens: unknown[]) => unknown> };
  const ti = e.block.indexOf(ext.tokenizer as unknown as (src: string, tokens: unknown[]) => unknown);
  assert.ok(e.startBlock.includes(ext.start) && ti >= 0, "the instance carries the singleton's block hint and the math tokenizer");
  assert.equal(e.startBlock.length, 1, "the grammar's one block hint, the math one (a new one needs a memo and a place here; a construct whose line is already a paragraph interrupt takes none: a hint there only sets marked's clip flag, which joins paragraphs, md-config.ts callouts, round 3)");
  e.startBlock = e.startBlock.map((hint) => (src: string) => hint.call({}, src));
  e.block[ti] = plainTokenizer;
  return m;
}
const tiny = (n: number): string => Array.from({ length: n }, (_, i) => `Short paragraph number ${i} here.\n\n`).join("");
const prices = (n: number): string => Array.from({ length: n }, (_, i) => `$$5 and $$10 for item ${i}\n\n`).join("");
const sparse = (n: number): string => Array.from({ length: n }, (_, i) =>
  i % 50 === 0 ? `$$\n\\sum_{k=0}^{${i}} k\n$$\n\n` : i % 50 === 25 ? `> quoted line ${i}\n\n` : `Prose line ${i} with $x_${i}$ inline.\n\n`).join("");
const equations = (n: number): string => Array.from({ length: n }, (_, i) => `Equation ${i} follows.\n$$\nE_${i} = m c^2\n$$\n\n`).join("");
/** Milliseconds for one run of `fn`. */
const once = (fn: () => unknown): number => { const t0 = process.hrtime.bigint(); fn(); return Number(process.hrtime.bigint() - t0) / 1e6; };
const median = (xs: number[]): number => [...xs].sort((a, b) => a - b)[xs.length >> 1];
const SMALL = 2000, LARGE = 16000, PAIRS = 7;
const SMALL_RUNS = LARGE / SMALL;   // 8: this many small lexes are the large note's paragraphs, equal work for a linear lex
const LINEAR_BOUND = 3;             // the large lex against the eight small ones: about 1 for a linear lex, 8 for a quadratic
const ABSOLUTE_MS = 1500;           // the large note's median; the cold first run may take twice that
/** Holds `lex` linear in the paragraph count on `note`'s shape: the LARGE-paragraph note lexed once against the SMALL
 *  one lexed SMALL_RUNS times, the same paragraphs on either side, so a linear lex takes about as long on each (the ratio
 *  measured 1.0 to 1.1 alone) and a quadratic one eight times as long on the large note. Measured on the pre-memo sources
 *  at 205f5f3d (git archive of ui/webview with HEAD's md-block-start.ts copied in): these two legs, with the absolute
 *  guard disabled so the ratio assertion is the one that fires, medians 7.33 to 7.50 over seven runs (review rounds 8
 *  and 9), least pair 6.91, one pair at 10.41 under a load burst; a probe of the helper's shape over the same sources,
 *  medians 7.48 to 7.75, no pair under 7.34. The two sides are timed back to back, PAIRS times over, and the median of
 *  the pair ratios is bounded at LINEAR_BOUND, under half the least quadratic pair. Equal work is what holds the ratio
 *  under contention: the review round 7 timed one small lex against one large one, bounded at three times their
 *  paragraph ratio (24), and a CPU quota (eight test workers in a 400% cgroup scope, the shape of a runner with a CPU
 *  limit) or nice-19 starvation under other load inflated that ratio three times, steadily across every pair, because
 *  the 6 ms small lex fit inside an unthrottled slice while the 60 ms large one spanned several and waited alone; a
 *  median of pairs discards a burst that lands on one pair, not a wait that lands on every large lex, and 7 of 24 file
 *  runs under the quota failed it (medians up to 30 in a probe of the same shape, 12 of 48 legs over 24). With both
 *  sides longer than a slice they wait alike, measured with a probe of this helper's shape (review round 8): under that
 *  quota, eight copies at once, medians 0.72 to 1.61 over 48 legs, worst single pair 2.18, and three rounds of eight
 *  copies of this file with no failure; this file at nice 19 under sixteen nice-19 spinners, medians 1.08 to 1.41 over
 *  six legs, worst pair 2.72, eight runs with no failure. An absolute bound stays as the coarse guard: the large note
 *  lexes in tens of milliseconds (190 under the quota; the round-7 recheck saw 640 at nice 19 on a box already at load
 *  18), where the quadratic lex took four to sixteen seconds. Test 7 below counts the finder's calls exactly, at no risk
 *  from load; these legs time the whole. Not a benchmark. */
function linear(lex: (src: string) => unknown, note: (n: number) => string, what: string): void {
  const small = note(SMALL), large = note(LARGE);
  lex(small);
  const first = once(() => lex(large));
  assert.ok(first < 2 * ABSOLUTE_MS, `${what}: ${LARGE.toLocaleString("en-US")} paragraphs took ${first.toFixed(0)} ms on the first run, a quadratic lex's seconds`);
  const ratios: number[] = [], larges: number[] = [], smalls: number[] = [];
  for (let i = 0; i < PAIRS; i++) {
    let s = 0;
    for (let k = 0; k < SMALL_RUNS; k++) s += once(() => lex(small));
    const l = once(() => lex(large));
    smalls.push(s); larges.push(l); ratios.push(l / s);
  }
  const shown = `${LARGE.toLocaleString("en-US")} paragraphs ${median(larges).toFixed(0)} ms against ${median(smalls).toFixed(0)} ms for ${SMALL_RUNS} lexes of ${SMALL.toLocaleString("en-US")}, pair ratios ${ratios.map((r) => r.toFixed(2)).join(" ")}`;
  assert.ok(median(larges) < ABSOLUTE_MS, `${what}: ${shown}: over a second for a lex of tens of milliseconds`);
  assert.ok(median(ratios) < LINEAR_BOUND, `${what}: ${shown}: not linear, the large note costs more than its share of paragraphs`);
}

test("the two-step block tokenizer is the lazy regex it replaced, on every candidate of the corpus", () => {
  // The reference is the base's reading: the first closer of the family after at least one character of content, the
  // line's newlines, non-blank content. The corpus is every three-line combination of the shapes, with and without a
  // trailing newline, so openers with no closer, closers before openers, blank bodies, a closer at the end of the text,
  // extra dollars around the delimiters and both families interleaved all meet.
  const BLOCK_DOLLARS = /^ {0,3}\$\$([\s\S]+?)\$\$ *(?:\n+|$)/;
  const BLOCK_BRACKET = /^ {0,3}\\\[([\s\S]+?)\\\] *(?:\n+|$)/;
  const reference = (src: string): { raw: string; text: string } | undefined => {
    const m = BLOCK_DOLLARS.exec(src) || BLOCK_BRACKET.exec(src);
    return m && m[1].trim() ? { raw: m[0], text: m[1].trim() } : undefined;
  };
  const lines = ["Line one", "$$x$$", "$$", "x$$", "$$x$$ tail", "\\[y\\]", "\\[", "y\\]", "$$ $$", "  $$z", "z $$", "\\[TODO\\] fix", "$$5 and $$10", "", "$$$", "$$x$$$", "$$x$$  ", "\\]", "\\[\\]", "$$$$", "$$$$$", "   $$", "    $$x$$", "$$ x\\]", "\\[ x$$"];
  let checked = 0, accepted = 0;
  for (const a of lines) for (const b of lines) for (const c of lines) {
    for (const src of [a + "\n" + b + "\n" + c, a + "\n" + b + "\n" + c + "\n"]) {
      const want = reference(src);
      assert.deepEqual(rawText(plainTokenizer(src)), want, "the tokenizer differs from the lazy regex on " + JSON.stringify(src));
      checked++; if (want) accepted++;
    }
  }
  assert.ok(checked > 30000 && accepted > 1000 && accepted < checked - 1000, `the corpus exercises both answers: ${accepted} accepted of ${checked}`);
});

test("the memoised lex is the plain lex: every three-line note of quotes, callouts, list items and candidates, and long notes of them", () => {
  const plain = plainInstance();
  const same = (src: string, why: string): void => {
    const got = marked.lexer(src), want = plain.lexer(src);
    assert.equal(JSON.stringify(got), JSON.stringify(want), why + ": the memoised lex differs from the plain one on " + JSON.stringify(src.length > 200 ? src.slice(0, 200) + "..." : src));
    assert.equal(got.map((t) => t.raw).join(""), src, why + ": the raws tile the source");
  };
  const lines = ["Line one", "$$x$$", "$$", "x$$", "$$5 and $$10", "\\[y\\]", "\\[TODO\\] fix", "> $$x$$", "> $$", "> x$$", "> quote", "> [!NOTE] t", "- $$x$$", "- item", "1. $$", "  $$", "", "# H", "\\[", "y\\]"];
  let n = 0;
  for (const a of lines) for (const b of lines) for (const c of lines) { same(a + "\n" + b + "\n" + c + "\n", "three lines"); n++; }
  assert.equal(n, lines.length ** 3);
  // longer notes: the memo answers many paragraphs from one scan, is invalidated by a consumed block, and is separate
  // in a nested frame (a quote or a callout whose body carries candidates of its own)
  const cycle = (k: number): string => Array.from({ length: k }, (_, i) => lines[(i * 7) % lines.length] + "\n" + lines[(i * 11 + 3) % lines.length] + "\n\n").join("");
  same(cycle(300), "a 300-paragraph cycle of the shapes");
  same("> " + cycle(60).replace(/\n/g, "\n> ") + "\n\nAfter the quote\n$$y$$\n", "the cycle inside one blockquote, then a display block after it");
  same("> [!NOTE] Folded\n> " + cycle(40).replace(/\n/g, "\n> ") + "\n\n" + cycle(40), "the cycle inside a callout and after it");
  same("- " + cycle(30).replace(/\n/g, "\n  ") + "\n\n" + cycle(30), "the cycle inside a list item and after it");
  const nested = Array.from({ length: 400 }, (_, i) => i % 4 === 0 ? `> Quote ${i}\n> $$\n> q_${i}\n> $$\n> tail $$5 and $$10\n\n` : i % 4 === 1 ? `- item ${i}\n  $$\n  l_${i}\n  $$\n- $$x_${i}$$\n\n` : i % 4 === 2 ? `Para ${i}\n$$5 and $$10 here\n\\[TODO\\] later\n\n` : `Para ${i}\n\\[\nb_${i}\n\\]\n\n`).join("");
  for (const [why, src] of [["tiny paragraphs", tiny(2000)], ["rejected candidates at every block start", prices(2000)], ["sparse math and quotes", sparse(2000)], ["a display block after every paragraph", equations(500)], ["quotes and list items with formulas and rejected lines in their bodies", nested]] as const) same(src, why);
});

test("the callout registers no start hint: its line is a blockquote, an interrupt marked's paragraph rule already stops at, and a hint's one effect there was marked's clip flag", () => {
  // Round 2 gave the callout a memoised finder (nextCallout, the regex `/\n {0,3}> ?\[!/` by indexOf) and this test held the
  // two equal. Round 3 removed the hint: the paragraph rule's own blockquote interrupt ends a paragraph before a `>` line,
  // so the hint could shorten no paragraph, and what it did do was set marked's lastParagraphClipped for a `> [!` anywhere
  // later in the source, which joins a paragraph and its interrupt-rejected successor with a newline the source does not
  // hold (md-config.ts, the callouts section; md-config.test.ts holds the renders).
  assert.equal((callout as unknown as { start?: unknown }).start, undefined);
  assert.deepEqual(marked.lexer("text\n> [!note] b\n> body\n").map((t) => t.type), ["paragraph", "callout"], "a callout still interrupts a paragraph, hint or none");
  const src = "Intro line\nColumn A\n|---|---|\n\nAfter.\n\n> [!note] later\n";
  const toks = marked.lexer(src);
  assert.deepEqual(toks.filter((t) => t.type !== "space").map((t) => t.type), ["paragraph", "paragraph", "paragraph", "callout"], "the table interrupt cuts the first paragraph, the table tokenizer declines, and the two paragraphs stay two");
  assert.equal(toks.map((t) => t.raw).join(""), src, "the raws tile the source");
});

test("the finder runs once per frame until its answer is consumed: counted on a probe extension", () => {
  let finds = 0;
  const probe: TokenizerAndRendererExtension = {
    name: "probe", level: "block",
    start: memoBlockStart((src) => { finds++; return src.indexOf("\n@@"); }),
    tokenizer(src: string) { const m = /^@@[^\n]*(?:\n+|$)/.exec(src); return m ? { type: "probe", raw: m[0], text: m[0] } : undefined; },
    renderer() { return ""; },
  };
  const m = new Marked({ extensions: [probe] });
  const lex = (src: string): number => { finds = 0; const n = m.lexer(src).length; return n; };
  lex(tiny(2000));
  assert.equal(finds, 1, "2,000 paragraphs and no construct: one scan, then the remembered none");
  const three = "P\n\n@@a\n\nP\n\n@@b\n\nP\n\n@@c\n\nP\n";
  assert.equal(m.lexer(three).filter((t) => t.type === "probe").length, 3, "the probe blocks lex");
  lex(three);
  assert.equal(finds, 4, "one scan per accepted block, each invalidated as its block is consumed, then the none");
  lex("> P1\n>\n> P2\n>\n> P3\n\nP4\n\nP5\n");
  assert.equal(finds, 2, "a blockquote's body is its own frame: one scan for it, one for the top level");
  finds = 0;
  (probe.start as (this: unknown, src: string) => unknown).call({}, "a\n\nb"); (probe.start as (this: unknown, src: string) => unknown).call({}, "a\n\nb");
  assert.equal(finds, 2, "with no lexer the hint has no frame and scans every time");
});

test("the math grammar lexes a note in time linear in its paragraph count: tiny paragraphs, and rejected `$$` lines at every block start", () => {
  // Before the memo: 8,000 one-line paragraphs 1.0 s from the math hint alone (the callout's, since removed, added 0.3 s), 8,000
  // `$$5 and $$10` lines 3.9 s (the hint's candidate walk, then the tokenizer's lazy scan to the end at every one of
  // them, the base's own 0.7 s), and 16,000 of either four times that. After: tens of milliseconds, eight times the
  // 2,000-paragraph note's. The prices leg and md-config-math-block-start.test.ts test 6 (1,500 rejected candidates
  // against prose, at eight times) are the pins on the tokenizer's closer memo (math.ts, closersLeft): the hint's count
  // is held exactly by the frame test below, the tokenizer's rescans only by timing.
  const m = new Marked({ extensions: [mathBlock, mathInline] });
  m.setOptions({ gfm: true, breaks: false });
  linear((src) => m.lexer(src), tiny, "tiny paragraphs");
  linear((src) => m.lexer(src), prices, "rejected `$$` lines");
  assert.equal(m.lexer(prices(8000)).map((t) => t.raw).join(""), prices(8000), "the raws tile the source");
});

test("the whole grammar on the singleton lexes tiny paragraphs in time linear in their count: every block hint is bounded", () => {
  // The singleton carries every block hint (the math one; the callout's went in round 3, its line being a paragraph
  // interrupt already), and a reply's md() pays them all: this is the finding's own shape (8,000 one-line paragraphs,
  // 1.3 s on the singleton before the review). It holds only when EVERY block hint in the grammar is bounded.
  linear((src) => marked.lexer(src), tiny, "tiny paragraphs on the singleton");
});

test("the math hint's own finder runs once per frame on the singleton's grammar, counted through the frame it writes", () => {
  // The probe test above counts memoBlockStart's calls to a probe's finder; this one counts the math hint's, the same
  // fact the two timing tests measure end to end, held exactly and at no risk from a loaded machine. marked calls the
  // block hints in registration order before every paragraph, with the lexer as `this.lexer`, so a probe hint registered
  // after the grammar reads the frame right after the math hint has written it. The frame is a Map keyed by each
  // memoised hint's finder, and every finder call stores a fresh answer object (md-block-start.ts, memoBlockStart), so
  // the distinct answers the probe has seen are the finder's calls; a memo that came to reuse its object would fail the
  // accepted-blocks count below, loudly, and this comment says what to update.
  const answers = new Set<unknown>(), keysPerCall = new Set<number>();
  let hints = 0;
  const probe: TokenizerAndRendererExtension = {
    name: "probe", level: "block",
    start(this: { lexer?: unknown } | undefined) {
      const frame = frameOf(this && this.lexer);
      assert.ok(frame, "the probe hint is called inside a frame");
      hints++;
      let keys = 0;
      for (const [k, v] of frame) if (typeof k === "function") { keys++; answers.add(v); }
      keysPerCall.add(keys);
      return undefined;
    },
    tokenizer() { return undefined; },
    renderer() { return ""; },
  };
  const m = new Marked(...mdExtensions, { extensions: [probe] });
  m.setOptions({ gfm: true, breaks: false });
  const count = (src: string): { finds: number; hints: number; blocks: number } => {
    answers.clear(); keysPerCall.clear(); hints = 0;
    const blocks = m.lexer(src).filter((t) => t.type === "mathBlock").length;
    assert.deepEqual([...keysPerCall], [1], "the grammar's one memoised hint, the math one, has its answer in the frame at every paragraph");
    return { finds: answers.size, hints, blocks };
  };
  assert.deepEqual(count(tiny(8000)), { finds: 1, hints: 8000, blocks: 0 }, "8,000 paragraphs and no candidate: the hint is asked before each, the finder scans once");
  assert.deepEqual(count(prices(8000)), { finds: 1, hints: 8000, blocks: 0 }, "8,000 rejected candidates: one scan, then the remembered none");
  assert.deepEqual(count(equations(500) + "After the last one.\n"), { finds: 501, hints: 501, blocks: 500 }, "one scan per accepted block, each invalidated as its block is consumed, then the none");
  assert.deepEqual(count("> P1\n>\n> P2\n>\n> P3\n\nP4\n\nP5\n"), { finds: 2, hints: 5, blocks: 0 }, "a blockquote's body is its own frame: one scan for it, one for the top level");
});
