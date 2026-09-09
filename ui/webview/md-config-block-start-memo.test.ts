// The block-start hints' cost, and the memo that bounds it (md-block-start.ts, math.ts). marked 12 calls every block
// extension's `start` hint before EVERY top-level paragraph, on the whole remaining source, so a hint that scans the
// rest of the note made the lex quadratic in the paragraph count: a 272 KB note of 8,000 one-line paragraphs took 1.3 s
// on the singleton against 34 ms with no hint, and a 200 KB transcript-sized reply twice the base's time (the Slice 4
// review, round 2). The remedy is a per-frame memo of the hint's answer, exact because within one blockTokens call the
// sources are suffixes of one another, plus the same memo for the math tokenizer's closer search. These tests hold the
// memoised lex equal to the plain one on every shape that exercises the frames (quotes, callouts, list items, rejected
// and accepted candidates), the two-step block tokenizer equal to the lazy regex it replaced, the finder called once per
// frame, and the lex linear in the paragraph count. Synthetic notes only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { Marked, marked } from "marked";
import type { TokenizerAndRendererExtension } from "marked";
import { applyMdConfig, callout, mdExtensions } from "./md-config";
import { mathBlock, mathInline } from "./math";
import { memoBlockStart } from "./md-block-start";

applyMdConfig();
type Ext = { start(this: unknown, src: string): number | undefined; tokenizer(this: unknown, src: string, tokens: unknown[]): { raw: string; text: string } | undefined };
const ext = mathBlock as unknown as Ext;
const calloutExt = callout as unknown as Ext;
/** The extension's two functions called with no lexer: the plain path, no frame, no memo. */
const plainStart = (src: string): number | undefined => ext.start.call({}, src);
const plainTokenizer = (src: string): { raw: string; text: string } | undefined => ext.tokenizer.call({}, src, []);
/** The token's two fields the lazy regex also produced, for the comparison with it. */
const rawText = (t: { raw: string; text: string } | undefined): { raw: string; text: string } | undefined => (t ? { raw: t.raw, text: t.text } : undefined);

/** The singleton's grammar on a fresh instance whose block hints (the math one and the callout's, every memoised hint the
 *  grammar registers) and math tokenizer run the plain path every time: each hint called with no lexer, so no frame and no
 *  memo. */
function plainInstance(): Marked {
  const m = new Marked(...mdExtensions);
  m.setOptions({ gfm: true, breaks: false });
  const e = m.defaults.extensions as unknown as { startBlock: Array<(this: unknown, src: string) => number | undefined>; block: Array<(src: string, tokens: unknown[]) => unknown> };
  const ti = e.block.indexOf(ext.tokenizer as unknown as (src: string, tokens: unknown[]) => unknown);
  assert.ok(e.startBlock.includes(ext.start) && e.startBlock.includes(calloutExt.start) && ti >= 0, "the instance carries the singleton's block hints and the math tokenizer");
  assert.equal(e.startBlock.length, 2, "the grammar's block hints: the math one and the callout's (a new one needs a memo and a place here)");
  e.startBlock = e.startBlock.map((hint) => (src: string) => hint.call({}, src));
  e.block[ti] = plainTokenizer;
  return m;
}
const tiny = (n: number): string => Array.from({ length: n }, (_, i) => `Short paragraph number ${i} here.\n\n`).join("");
const prices = (n: number): string => Array.from({ length: n }, (_, i) => `$$5 and $$10 for item ${i}\n\n`).join("");
const sparse = (n: number): string => Array.from({ length: n }, (_, i) =>
  i % 50 === 0 ? `$$\n\\sum_{k=0}^{${i}} k\n$$\n\n` : i % 50 === 25 ? `> quoted line ${i}\n\n` : `Prose line ${i} with $x_${i}$ inline.\n\n`).join("");
const equations = (n: number): string => Array.from({ length: n }, (_, i) => `Equation ${i} follows.\n$$\nE_${i} = m c^2\n$$\n\n`).join("");
/** Milliseconds for `fn`, the least of three runs after a warm-up: a bound on the work, not a benchmark. */
function ms(fn: () => unknown): number {
  fn();
  let best = Infinity;
  for (let i = 0; i < 3; i++) { const t0 = process.hrtime.bigint(); fn(); best = Math.min(best, Number(process.hrtime.bigint() - t0) / 1e6); }
  return best;
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

test("the callout's finder is the regex hint it replaced, on every corpus string", () => {
  // The hint's answer was `/\n {0,3}> ?\[!/.exec(src)`, a scan of the whole remaining source per paragraph; the finder
  // hops over each `[!` with indexOf and reads the line's prefix back (md-config.ts nextCallout). The corpus: every
  // prefix of up to four spaces or a tab, every quote marker spelling (none, `>`, one or two spaces, a tab), `[!` and
  // its near misses, at the string's start, one character in, after a newline, after a blank line, and with a second
  // marker later in the text (the first one wins), plus the shapes the round 1 fix named.
  const hint = calloutExt.start;
  const want = (src: string): number | undefined => { const m = /\n {0,3}> ?\[!/.exec(src); return m ? m.index : undefined; };
  let n = 0;
  const check = (src: string): void => { assert.equal(hint.call({}, src), want(src), "the finder differs from the regex on " + JSON.stringify(src)); n++; };
  for (const lead of ["", "a", "\n", "\na", "text\n", "\n\n", "> quote\n"])
    for (const pre of ["", " ", "  ", "   ", "    ", "\t"])
      for (const q of ["", ">", "> ", ">  ", ">\t"])
        for (const m of ["[!", "[", "!", "[!note] Title", "[![!", "x[!"])
          for (const tail of ["", " tail\n", " tail\n  > [!later]\n", "\n\n>[!x"]) check(lead + pre + q + m + tail);
  for (const s of ["a> [!note] b", "[!x", "\n[!x", "\n>[!", "\n    > [!x", "\n> [!a\n> [!b", "\n>\t[!t", "\n > [!\n", "no marker at all\n\nnone here"]) check(s);
  assert.ok(n > 5000, "the corpus was walked: " + n);
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
  // Before the memo: 8,000 one-line paragraphs 1.0 s from the math hint alone (the callout's added 0.3 s), 8,000
  // `$$5 and $$10` lines 3.9 s (the hint's candidate walk, then the tokenizer's lazy scan to the end at every one of
  // them, the base's own 0.7 s). After: tens of milliseconds, four times the 2,000-paragraph note's. The bounds leave
  // room for a loaded machine: quadratic cost is sixteen times at four times the length.
  const m = new Marked({ extensions: [mathBlock, mathInline] });
  m.setOptions({ gfm: true, breaks: false });
  const t2 = ms(() => m.lexer(tiny(2000))), t8 = ms(() => m.lexer(tiny(8000)));
  assert.ok(t8 < 400, `8,000 tiny paragraphs lexed in ${t8.toFixed(0)} ms`);
  assert.ok(t8 < 10 * Math.max(t2, 2), `8,000 tiny paragraphs took ${t8.toFixed(0)} ms against ${t2.toFixed(0)} ms for 2,000: not linear`);
  const p2 = ms(() => m.lexer(prices(2000))), p8 = ms(() => m.lexer(prices(8000)));
  assert.ok(p8 < 400, `8,000 rejected \`$$\` lines lexed in ${p8.toFixed(0)} ms`);
  assert.ok(p8 < 10 * Math.max(p2, 2), `8,000 rejected \`$$\` lines took ${p8.toFixed(0)} ms against ${p2.toFixed(0)} ms for 2,000: not linear`);
  assert.equal(m.lexer(prices(8000)).map((t) => t.raw).join(""), prices(8000), "the raws tile the source");
});

test("the whole grammar on the singleton lexes tiny paragraphs in time linear in their count: every block hint is bounded", () => {
  // The singleton carries every block hint (the math one and the callout's), and a reply's md() pays them all: this
  // is the finding's own shape (8,000 one-line paragraphs, 1.3 s on the singleton before the review). It holds only
  // when EVERY block hint in the grammar is bounded, the callout's included.
  const t2 = ms(() => marked.lexer(tiny(2000))), t8 = ms(() => marked.lexer(tiny(8000)));
  assert.ok(t8 < 400, `8,000 tiny paragraphs lexed in ${t8.toFixed(0)} ms on the singleton`);
  assert.ok(t8 < 10 * Math.max(t2, 2), `8,000 tiny paragraphs took ${t8.toFixed(0)} ms against ${t2.toFixed(0)} ms for 2,000 on the singleton: a block hint still scans per paragraph`);
});
