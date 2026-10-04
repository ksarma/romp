// The reader's line (reading-point.ts; the review of iOS item 6, 2026-10-02) over synthetic turns in Chromium, through the
// shared launcher (real-viewer-leg.ts inBrowser). The chat keeps a scrolled-up reader's place across the math renderer's
// arrival and across a page reload by this point; render.ts's turn anchor alone kept the turn's top, and a reply's formulas
// above the reader inside that turn pushed the text being read down by their growth. Each scene puts a marker at a known offset
// under a scroller's top, takes the point, changes the turn the way the chat does (formulas laid out in place, taller; or the
// turn rebuilt in another of a formula's forms), applies the point's shift and reads the marker back:
//   - formulas in earlier blocks of the reader's own turn, every one above the viewport top: the line comes back within 1 px,
//     where the turn's top did not move at all, so the turn anchor would have left the marker where the swap pushed it;
//   - a display formula INSIDE the paragraph being read, above the reader's line (a model's "We have\n$$...$$\nwhere ..."
//     with no blank lines is one paragraph): the line comes back, where the paragraph's top would not have;
//   - a point taken over laid-out formulas, past a comment mark and a long inline formula in the reader's paragraph, lands on
//     the same line in a rebuilt turn whose formulas wait (the TeX as text) and in one whose formulas fell back to their source
//     (a reload's shape): formula text counts in no offset, and a mark adds none;
//   - the anchor is the first line at the top, not a later one: a paragraph straddling the top with a formula in view below it,
//     laid out taller, keeps its line where it was and the formula grows downward (a later anchor would have pushed the line up);
//   - a sticky header at the turn's top, stuck under the scroller's top, is never the anchor: it does not move with the text;
//   - a point the turn no longer holds, or a malformed one read back from storage, has no shift.
// Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";
import { inBrowser } from "./real-viewer-leg";

const EXT = process.cwd();                                               // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
let bundle: string | null = null;
/** reading-point.ts from this tree as one script, its two functions on window.RP. */
function readingPointBundle(): string {
  if (bundle) return bundle;
  const r = createRequire(path.join(EXT, "package.json"))("esbuild").buildSync({
    stdin: { contents: 'export { captureReadingPoint, readingPointShift } from "./reading-point";', resolveDir: UI, loader: "ts", sourcefile: "reading-point-leg.ts" },
    bundle: true, write: false, format: "iife", globalName: "RP", platform: "browser", target: "es2020", logLevel: "silent",
  });
  bundle = r.outputFiles[0].text as string;
  return bundle;
}

// A scroller under a 40 px bar, the chat's column width on a phone, its own scroll anchoring off (the phone's WebKit has none).
// The waiting dress is the sheets' own rule (styles.css: a display formula in KaTeX's display box); `.tall` stands in for
// KaTeX's taller layout of a formula.
const PAGE = `<!doctype html><html><head><style>
body { margin: 0; font: 16px/1.4 sans-serif; }
#bar { height: 40px; }
#sc { position: absolute; top: 40px; left: 0; width: 360px; height: 420px; overflow-y: auto; overflow-anchor: none; }
.md-math-display { display: block; margin: 1em 0; text-align: center; }
.katex-display { display: block; margin: 1em 0; text-align: center; }
.tall { display: inline-block; height: 120px; vertical-align: middle; }
.sticky { position: sticky; top: 0; background: #fff; height: 24px; }
</style></head><body><div id="bar"></div><div id="sc"><div id="turn" data-uuid="11111111-2222-4333-8444-000000000601"></div></div></body></html>`;

const READS = (n: number, from = 1): string => Array.from({ length: n }, (_, i) => `<p>READ-${String(from + i).padStart(2, "0")}: plain text the reader is reading further down the same reply, long enough to wrap across a few lines of the column.</p>`).join("");
const WAIT_D = (tex: string): string => `<div class="md-math-display">${tex}</div>`;
const WAIT_I = (tex: string): string => `<span class="md-math-inline">${tex}</span>`;
const WAIT_D_IN_P = (tex: string): string => `<span class="md-math-display">${tex}</span>`;   // a display formula inside a paragraph is a span (math.ts)
const DONE_D = `<span class="katex-display"><span class="katex"><span class="tall">x</span></span></span>`;
const DONE_I = `<span class="katex">ab</span>`;
const SRC_D = (tex: string): string => `<pre title="Not rendered"><code class="md-math-src">${tex}</code></pre>`;
const SRC_I = (tex: string): string => `<code class="md-math-src">${tex}</code>`;
// the same block with the Copy button the chat gives a source block (render.ts addCopyBtn: the button inside the pre, after the code)
const SRC_D_COPY = (tex: string): string => `<pre title="Not rendered" class="has-copy"><code class="md-math-src">${tex}</code><button class="code-copy" type="button">Copy</button></pre>`;
// A formula whose TeX is far longer than KaTeX's text for it, so an offset that counted formula text would miss by lines.
const LONG_TEX = "\\sum_{i=1}^{n} \\frac{a_i + b_i}{c_i - d_i} + \\prod_{k=1}^{m} \\left(1 - \\frac{1}{k^2}\\right) + \\int_0^1 f(x)\\,dx";
/** A reply in one form: steps with an inline formula and a display formula after each, then the paragraphs being read. With
 *  `reader`, READ-03 holds a long inline formula and then, after a line break, MARK at the start of a line; `mark` wraps a few of
 *  its words before the formula in a comment mark. */
const REPLY = (d: (tex: string) => string, i: (tex: string) => string, mark = false, reader = false): string =>
  "<p>Here is the notes-api ranking derivation, step by step.</p>"
  + [1, 2, 3, 4].map((k) => `<p>STEP-0${k}: the term ${i("w_" + k + " = \\frac{a}{b}")} weighs the hits.</p>${d("\\sum_{i=1}^{n} x_" + k)}`).join("")
  + READS(2)
  + (reader ? `<p>READ-03: ${mark ? '<mark class="cmt-hl">plain text</mark>' : "plain text"} the reader is reading ${i(LONG_TEX)} and a few more words here<br><b>MARK</b> starts the line the reader is on, long enough to wrap across the column.</p>` : READS(1, 3))
  + READS(12, 4);   // enough below the reader that no landing here is clamped at the scroller's end

type Probe = { page: any; errors: string[] };
async function openPage(browser: any): Promise<Probe> {
  const page = await browser.newPage({ viewport: { width: 400, height: 500 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => errors.push(e.message));
  await page.setContent(PAGE, { waitUntil: "load" });
  await page.addScriptTag({ content: readingPointBundle() });
  await page.evaluate(() => {
    const w = window as any;
    const sc = document.getElementById("sc")!, turn = document.getElementById("turn")!;
    const find = (m: string): Element => Array.from(turn.querySelectorAll("p, b")).find((e) => (e.textContent || "").startsWith(m))!;
    w.set = (html: string) => { turn.innerHTML = html; };
    w.yOf = (m: string): number => find(m).getBoundingClientRect().top - sc.getBoundingClientRect().top;
    w.turnTop = (): number => turn.getBoundingClientRect().top - sc.getBoundingClientRect().top;
    w.put = (m: string, off: number) => { sc.scrollTop += w.yOf(m) - off; };
    w.cap = () => w.RP.captureReadingPoint(sc, turn);
    w.apply = (p: unknown): number | null => { const d = w.RP.readingPointShift(sc, turn, p); if (d !== null) sc.scrollTop += d; return d; };
    w.lastFormulaBottom = (): number => { const f = Array.from(turn.querySelectorAll(".md-math-display, .katex-display")); return f[f.length - 1].getBoundingClientRect().bottom - sc.getBoundingClientRect().top; };
    // the swap the math renderer's arrival makes: each waiting formula replaced in place by a taller layout
    w.swap = () => {
      for (const e of Array.from(turn.querySelectorAll(".md-math-display"))) e.outerHTML = '<span class="katex-display"><span class="katex"><span class="tall">x</span></span></span>';
      for (const e of Array.from(turn.querySelectorAll(".md-math-inline"))) e.outerHTML = '<span class="katex">ab</span>';
    };
  });
  return { page, errors };
}

test("chromium: formulas in earlier blocks of the reader's own turn, all above the viewport top, are laid out taller: the line comes back within 1 px where the turn's top never moved", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openPage(browser);
    const r = await page.evaluate(([html]: [string]) => {
      const w = window as any;
      w.set(html); w.put("READ-03", 60);
      const before = { marker: w.yOf("READ-03"), turn: w.turnTop(), lastFormula: w.lastFormulaBottom() };
      const p = w.cap();
      w.swap();
      const swapped = { marker: w.yOf("READ-03"), turn: w.turnTop() };
      const shift = w.apply(p);
      return { before, swapped, shift, after: w.yOf("READ-03"), p };
    }, [REPLY(WAIT_D, WAIT_I)]);
    assert.ok(r.before.turn < 0 && r.before.lastFormula < 0, "the reply begins above the viewport and its last formula is above the viewport top: " + JSON.stringify(r));
    assert.ok(r.swapped.marker - r.before.marker > 100, "the instrument: the swap pushed the marker down: " + JSON.stringify(r));
    assert.ok(Math.abs(r.swapped.turn - r.before.turn) < 1, "while the turn's top stayed put, so keeping it keeps nothing the reader sees: " + JSON.stringify(r));
    assert.ok(Math.abs(r.after - r.before.marker) <= 1, "the point's shift puts the line being read back: " + JSON.stringify(r));
    assert.deepEqual(errors, []);
  });
});

test("chromium: a display formula inside the paragraph being read, above the reader's line, is laid out taller: the line comes back where the paragraph's top would not have", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openPage(browser);
    const lead = "We have the ranking sum over every session's hits and reads, written out once in full here, ";
    const after = Array.from({ length: 14 }, (_, i) => `where clause ${i + 1} of the long explanation keeps going across the column and wraps, `).join("");
    const html = "<p>Intro paragraph before the long one.</p><p>" + lead + WAIT_D_IN_P("\\sum_{i=1}^{n} w_i h_i") + after + "<b>MARK</b> and the paragraph closes after a few more words of text.</p>" + READS(3);
    const r = await page.evaluate(([h]: [string]) => {
      const w = window as any;
      w.set(h); w.put("MARK", 200);
      const para = document.querySelectorAll("#turn p")[1] as HTMLElement;
      const sc = document.getElementById("sc")!;
      const before = { marker: w.yOf("MARK"), paraTop: para.getBoundingClientRect().top - sc.getBoundingClientRect().top, formula: w.lastFormulaBottom() };
      const p = w.cap();
      w.swap();
      const swapped = { marker: w.yOf("MARK"), paraTop: para.getBoundingClientRect().top - sc.getBoundingClientRect().top };
      w.apply(p);
      return { before, swapped, after: w.yOf("MARK"), p };
    }, [html]);
    assert.ok(r.before.paraTop < 0 && r.before.formula < 0, "the paragraph begins above the viewport top, its formula above it too: " + JSON.stringify(r));
    assert.ok(r.p && r.p.block >= 0, "the point names the paragraph's own block: " + JSON.stringify(r.p));
    assert.ok(r.swapped.marker - r.before.marker > 50, "the instrument: the swap pushed the marker down: " + JSON.stringify(r));
    assert.ok(Math.abs(r.swapped.paraTop - r.before.paraTop) < 1, "while the paragraph's top stayed put: " + JSON.stringify(r));
    assert.ok(Math.abs(r.after - r.before.marker) <= 1, "the line comes back: " + JSON.stringify(r));
    assert.deepEqual(errors, []);
  });
});

test("chromium: a point taken over laid-out formulas, a comment mark in the reader's paragraph, lands the same line in a rebuilt turn whose formulas wait and in one whose formulas fell back to their source, a source block's Copy button included", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openPage(browser);
    for (const [name, rebuilt] of [["waiting", REPLY(WAIT_D, WAIT_I, false, true)], ["source fallback", REPLY(SRC_D, SRC_I, false, true)],
      ["source fallback with the Copy button", REPLY(SRC_D_COPY, SRC_I, false, true)]] as const) {
      const r = await page.evaluate(([laid, again]: [string, string]) => {
        const w = window as any;
        w.set(laid); document.getElementById("sc")!.scrollTop = 0; w.put("MARK", -5);   // MARK's line, after the mark and the long formula, at the top
        const before = w.yOf("MARK");
        const turnBefore = w.turnTop();
        const p = w.cap();
        w.set(again);                                   // the fresh page's turn: the same text, the formulas in another form, no mark
        const sc = document.getElementById("sc")!;
        sc.scrollTop += w.turnTop() - turnBefore;       // landed by the turn's top first, as the old record did
        const byTurn = w.yOf("MARK");
        const shift = w.apply(p);
        return { before, byTurn, shift, after: w.yOf("MARK"), p };
      }, [REPLY(() => DONE_D, () => DONE_I, true, true), rebuilt]);
      assert.ok(r.p && r.p.char > 40, name + ": the point is past the mark and the formula in the reader's paragraph: " + JSON.stringify(r.p));
      assert.ok(Math.abs(r.before - r.byTurn) > 50, name + ": the instrument: the turn's top alone lands the line elsewhere: " + JSON.stringify(r));
      assert.ok(Math.abs(r.after - r.before) <= 1, name + ": the point lands the line where it was: " + JSON.stringify(r));
    }
    assert.deepEqual(errors, []);
  });
});

test("chromium: the anchor is the first line at the viewport top, not a later one: a formula in view below it grows downward and the line at the top stays", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openPage(browser);
    const html = "<p>Here is the notes-api ranking derivation, step by step.</p>" + READS(2) + WAIT_D("\\sum_{i=1}^{n} x_i") + READS(4, 3);
    const r = await page.evaluate(([h]: [string]) => {
      const w = window as any;
      w.set(h); w.put("READ-02", -25);              // the paragraph's second line at the top, the formula below it on screen
      const before = { top: w.yOf("READ-02"), next: w.yOf("READ-03"), formula: w.lastFormulaBottom() };
      const p = w.cap();
      w.swap();
      w.apply(p);
      return { before, after: { top: w.yOf("READ-02"), next: w.yOf("READ-03") }, p };
    }, [html]);
    assert.ok(r.before.top < 0 && r.before.formula > 0 && r.before.formula < 420, "the paragraph straddles the top and the formula is on screen below it: " + JSON.stringify(r));
    assert.ok(Math.abs(r.after.top - r.before.top) <= 1, "the line at the top stays: " + JSON.stringify(r));
    assert.ok(r.after.next - r.before.next > 50, "the formula grew downward, pushing what follows it: " + JSON.stringify(r));
    assert.deepEqual(errors, []);
  });
});

test("chromium: a sticky header stuck under the scroller's top is never the anchor; a point the turn no longer holds, or a malformed one, has no shift", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openPage(browser);
    const r = await page.evaluate(([html]: [string]) => {
      const w = window as any;
      w.set(html); w.put("READ-03", 60);
      const sc = document.getElementById("sc")!;
      const head = document.querySelector("#turn .sticky")!.getBoundingClientRect().top - sc.getBoundingClientRect().top;
      const before = w.yOf("READ-03");
      const p = w.cap();
      w.swap();
      w.apply(p);
      const after = w.yOf("READ-03");
      const gone = w.RP.readingPointShift(sc, document.getElementById("turn"), { block: 999, char: 0, y: 0 });
      const past = w.RP.readingPointShift(sc, document.getElementById("turn"), { block: p.block, char: 1e9, y: 0 });
      const bad = [null, {}, { block: "1", char: 0, y: 0 }, { block: 1.5, char: 0, y: 0 }, { block: 0, char: -1, y: 0 }, { block: 0, char: 0, y: null }, { block: -2, char: 0, y: 0 }]
        .map((x) => w.RP.readingPointShift(sc, document.getElementById("turn"), x));
      return { head, before, after, p, gone, past, bad };
    }, ['<div class="sticky">web · 2 min ago</div>' + REPLY(WAIT_D, WAIT_I)]);
    assert.ok(Math.abs(r.head) < 1, "the header is stuck at the scroller's top: " + JSON.stringify(r));
    assert.ok(r.p.block >= 0, "the point is the reader's paragraph, not the header's text: " + JSON.stringify(r.p));
    assert.ok(Math.abs(r.after - r.before) <= 1, "and the line comes back across the swap: " + JSON.stringify(r));
    assert.deepEqual([r.gone, r.past], [null, null], "a block the turn lacks, an offset past its text");
    assert.deepEqual(r.bad, [null, null, null, null, null, null, null], "malformed points");
    assert.deepEqual(errors, []);
  });
});
