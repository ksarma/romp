// A fence's rows in the viewer (Slice 3 of plans/markdown-viewer.md, review rounds 1 and 2): defects of one rule, the line-number
// gutter `.fileview-md pre code .cl::before` (the chat's `pre code .cl::before`, which the viewer copies declaration for
// declaration; code-block.test.ts pins the copy). Round 1: (1) The gutter at 0.92em under `align-items: baseline` made every
// row 18.5625px against the code's 18px line-height: Chromium floors the half-leading it puts above a line box, so the smaller
// gutter's box hung 0.5625px further below the shared baseline than the text's did, and the row grew by that much (the Raw
// view's rows of the same lines are 18px; a 300-line fence was 169px taller in Rendered). (2) The same fraction crept the
// kept code line 1px per Rendered/Raw round trip at some widths: the row-aware seat maps an 18.5625px row onto an 18px one
// and back, and the integer scrollTop rounds the difference. (3) The gutter inherited `overflow-wrap: anywhere` from the code,
// so a four-digit number broke across two lines and every row from line 1000 on was double height, reading "100" over "0".
// The fix: `line-height: 1` on the gutter (its box never taller than the text's, both baselines still shared), `overflow-wrap:
// normal` (the number never breaks), and a 2.5em basis that holds four digits.
// Round 2: (4) `line-height: 1` cut a BLANK line's row to the gutter's own 11px: the row is a flex line of an empty `.ct`
// (no line box, 0px) and the number, so nothing in it carried the code's line-height (the base sheet's blank rows were 16.5px,
// the gutter's inherited 1.5); a blank line inside a token that spans lines (a docstring's) leaves an empty hljs span in the
// `.ct` and collapsed the same way. The fix: the `.ct`'s ::before is a word joiner (U+2060, zero width, no break before or
// after it, outside the DOM's text), so an empty `.ct` has a line box of the code's line-height with the text's baseline and a
// text line is unchanged. (5) A five-digit number widened its own row's gutter alone (a flex item's min-content), so the text
// column stepped 5.6px right from line 10000 on: wrapCodeLines (code-block.ts) writes `--ln-digits` on the code element and
// the basis is max(2.5em, the digits in ch), so every row of the fence shares the wider gutter. Measured over the real bundle
// and sheets. Skips loudly without a browser. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, REPORT, type Mode } from "./real-viewer-leg";

const F = "```";
const P = (i: number) => "Paragraph " + i + ": " + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(3).trim() + ".";
const LONG = ["# A long fence", "", "Prose before.", "", F + "python", ...Array.from({ length: 1200 }, (_, i) => `x_${i + 1} = ${i + 1}  # line ${i + 1}`), F, "", "Prose after.", ""].join("\n");
const BIG_N = 10005;
const BIG = ["# A longer fence", "", "Prose before.", "", F + "python", ...Array.from({ length: BIG_N }, (_, i) => `x_${i + 1} = ${i + 1}  # line ${i + 1}`), F, "", "Prose after.", ""].join("\n");
const CODE = ["# a comment line", "def f(x):", "    return x  # spaces", "y = f(1)", "z = f(2)", "print(y, z)"];
const NOTE = ["# Report", "", "## Section two", "", ...Array.from({ length: 5 }, (_, i) => P(i + 1) + "\n"), F + "python", ...CODE, F, "", ...Array.from({ length: 60 }, (_, i) => P(i + 6) + "\n")].join("\n");
// blank lines: one, two in a row, and one inside a docstring (hljs paints the docstring as one string token across its lines,
// so the wrap leaves that line's .ct holding an empty span rather than nothing); the same shapes in an unnamed fence
const DOC = ["def f(x):", '    """Summary.', "", "    Details.", '    """', "", "    return x", "", "", "print(f(1))"];
const PLAIN = ["plain line", "", "another", "", "", "last"];
const BLANKS = ["# Report", "", "Prose before.", "", F + "python", ...DOC, F, "", F, ...PLAIN, F, "", "Prose after.", ""].join("\n");

type Facts = Record<string, any>;
function rowFacts(): Facts {
  const code = document.querySelector(".fileview-md pre code")!; const rows = Array.from(code.querySelectorAll(":scope > .cl")) as HTMLElement[];
  const hist: Record<string, number> = {}; for (const r of rows) { const k = r.getBoundingClientRect().height.toFixed(4); hist[k] = (hist[k] || 0) + 1; }
  const h = (i: number) => rows[i - 1].getBoundingClientRect().height; const b = getComputedStyle(rows[999], "::before");
  return { n: rows.length, hist, h1: h(1), h999: h(999), h1000: h(1000), h1200: h(1200), ct: (rows[0].querySelector(".ct") as HTMLElement).getBoundingClientRect().height,
    lineHeight: parseFloat(getComputedStyle(code).lineHeight), codeH: code.getBoundingClientRect().height, align: getComputedStyle(rows[0]).alignItems,
    before: { fontSize: b.fontSize, lineHeight: b.lineHeight, width: parseFloat(b.width), overflowWrap: b.overflowWrap, content: b.content } };
}
/** Every fence of the note: its rows' heights, each row's text (its .ct's textContent), whether the .ct holds an element and no
 *  text (the spanned blank line), the .ct's own box, its ::before's content, and where its first glyph starts. */
function blankFacts(): Facts[] {
  return (Array.from(document.querySelectorAll(".fileview-md pre code")) as HTMLElement[]).map((code) => {
    const lh = parseFloat(getComputedStyle(code).lineHeight); const rows = Array.from(code.querySelectorAll(":scope > .cl")) as HTMLElement[];
    const hist: Record<string, number> = {}; for (const r of rows) { const k = r.getBoundingClientRect().height.toFixed(4); hist[k] = (hist[k] || 0) + 1; }
    const sel = getSelection()!; sel.removeAllRanges(); const rg = document.createRange(); rg.selectNodeContents(code); sel.addRange(rg); const copied = sel.toString(); sel.removeAllRanges();
    return { lh, n: rows.length, hist, codeH: code.getBoundingClientRect().height, joinerInText: (code.textContent || "").indexOf("\u2060") >= 0, joinerInSelection: copied.indexOf("\u2060") >= 0,
      rows: rows.map((r) => { const ct = r.querySelector(".ct") as HTMLElement; const pb = getComputedStyle(ct, "::before"); const rr = r.getBoundingClientRect(), cr = ct.getBoundingClientRect();
        let glyphLeft: number | null = null; const tn = document.createTreeWalker(ct, NodeFilter.SHOW_TEXT).nextNode();
        if (tn && tn.textContent) { const g = document.createRange(); g.setStart(tn, 0); g.setEnd(tn, 1); glyphLeft = g.getBoundingClientRect().left - cr.left; }
        return { text: ct.textContent || "", spanned: ct.textContent === "" && ct.children.length > 0, h: rr.height, ctH: cr.height, beforeContent: pb.content, glyphLeft }; }) };
  });
}
const rowTop = (page: any) => page.evaluate(() => { const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect(); const rows = Array.from(document.querySelectorAll(".fileview-md pre code > .cl")); const r = rows[3].getBoundingClientRect(); return { top: r.top - br.top, height: r.height, scrollTop: body.scrollTop }; });
const click = async (page: any, label: string, until: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await page.waitForFunction((s: string) => !!document.querySelector(s), until, { timeout: 5000 }); await frames(page, 3); };
const scaleTo150 = async (page: any) => { for (let i = 0; i < 3; i++) await page.click('button[aria-label="Larger text"]'); await page.waitForFunction(() => getComputedStyle(document.querySelector(".fileview-md")!).getPropertyValue("--fv-scale").trim() === "1.5", null, { timeout: 5000 }); await frames(page, 2); };

test("every row of a 1200-line fence is exactly the code's line-height, at 100 and 150 percent, four-digit numbers included; the number never breaks", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: LONG } });
    await page.waitForFunction(() => document.querySelectorAll(".fileview-md pre code .cl").length >= 1200, null, { timeout: 15000 }); await frames(page, 2);
    const m = await page.evaluate(rowFacts);
    assert.equal(m.n, 1200); assert.equal(m.align, "baseline", "the number still shares the text's baseline (flex-start would print it 2px high)");
    assert.equal(m.lineHeight, 18, "the code's line-height at 12px is 18px");
    assert.deepEqual(Object.keys(m.hist), [m.lineHeight.toFixed(4)], "every row is the line-height, no other height (before: 18.5625 for rows 1 to 999 and 35.125 from row 1000 on): " + JSON.stringify(m.hist));
    assert.equal(m.h999, m.h1000, "row 1000 is as tall as row 999"); assert.equal(m.h1200, m.h1); assert.equal(m.ct, m.lineHeight, "the text's box is the row's");
    assert.equal(m.codeH, 1200 * m.lineHeight, "the code element is exactly its rows (before: 25604px for 21600)");
    assert.equal(m.before.overflowWrap, "normal", "the number never breaks (the code's `anywhere` is not inherited)");
    assert.equal(m.before.lineHeight, m.before.fontSize, "the gutter's line-height is 1: its box is never taller than the text's");
    assert.ok(m.before.width >= 26.5, "four digits fit the gutter (" + m.before.width + "px; four mono digits at 11.04px are about 26.6)");
    // a five-digit number in a four-digit fence: restart the counter at 9998, so the first two rows read 9999 and 10000; neither
    // breaks (the fence-wide gutter for a REAL five-digit fence is the digits test below)
    await page.evaluate(() => { (document.querySelector(".fileview-md pre code") as HTMLElement).style.counterReset = "ln 9998"; }); await frames(page, 2);
    const five = await page.evaluate(() => { const rows = Array.from(document.querySelectorAll(".fileview-md pre code > .cl")) as HTMLElement[]; const b = (i: number) => getComputedStyle(rows[i], "::before"); return { n1: b(0).content, n2: b(1).content, h1: rows[0].getBoundingClientRect().height, h2: rows[1].getBoundingClientRect().height }; });
    assert.equal(five.h1, m.lineHeight, "row 9999 is one line"); assert.equal(five.h2, m.lineHeight, "row 10000 is one line: the number did not break");
    await page.evaluate(() => { (document.querySelector(".fileview-md pre code") as HTMLElement).style.counterReset = ""; }); await frames(page, 2);
    // 150 percent: three steps of the text-size control; the rows follow the scaled line-height exactly
    await scaleTo150(page);
    const big = await page.evaluate(rowFacts);
    assert.equal(big.lineHeight, 27, "18px line-height at 150 percent is 27px");
    assert.deepEqual(Object.keys(big.hist), ["27.0000"], "every row is 27px at 150 percent (before: 27.844 and 52.688): " + JSON.stringify(big.hist));
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("a blank line's row is the code's line-height like any other: one, two in a row and one inside a docstring, in a python and an unnamed fence, at 100 and 150 percent, on the pane and the feed", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as Mode[]) {
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: BLANKS } });
      await page.waitForFunction(() => document.querySelectorAll(".fileview-md pre code .cl").length >= 16, null, { timeout: 15000 }); await frames(page, 2);
      for (const [label, scale] of [["100%", 1], ["150%", 1.5]] as [string, number][]) {
        if (scale !== 1) await scaleTo150(page);
        const fences = await page.evaluate(blankFacts);
        assert.equal(fences.length, 2, mode + " " + label + ": the two fences");
        const [py, plain] = fences;
        assert.equal(py.n, DOC.length, mode + ": the python fence's rows"); assert.equal(plain.n, PLAIN.length, mode + ": the unnamed fence's rows");
        for (const [name, f] of [["python", py], ["unnamed", plain]] as [string, Facts][]) {
          const cell = mode + " " + label + " " + name;
          assert.equal(f.lh, 18 * scale, cell + ": the code's line-height");
          assert.deepEqual(Object.keys(f.hist), [f.lh.toFixed(4)], cell + ": every row is the line-height, the blank ones too (before: a blank row was 11.0469px at 100 percent, 16.5625 at 150): " + JSON.stringify(f.hist));
          assert.equal(f.codeH, f.n * f.lh, cell + ": the code element is exactly its rows (before: 87.14px for six lines with three blank)");
          const blanks = f.rows.filter((r: Facts) => r.text === "");
          assert.ok(blanks.length >= 3, cell + ": the fixture's blank rows are found (" + blanks.length + ")");
          for (const r of blanks) { assert.equal(r.h, f.lh, cell + ": a blank row is one line (" + r.h + ")"); assert.equal(r.ctH, f.lh, cell + ": ...because its empty .ct has a line box (before: 0px)"); }
          assert.ok(f.rows.every((r: Facts) => r.beforeContent === '"\u2060"'), cell + ": every .ct starts with the word joiner (" + f.rows[0].beforeContent + ")");
          // the joiner takes no room: a text row's first glyph sits at its .ct's left edge (an inline pseudo's computed width reads auto, so the glyph is the measure)
          for (const r of f.rows.filter((r: Facts) => r.text !== "")) assert.ok(r.glyphLeft !== null && Math.abs(r.glyphLeft) < 0.01, cell + ": a text row's first glyph sits at its .ct's left edge (" + r.glyphLeft + ")");
          assert.equal(f.joinerInText, false, cell + ": the joiner is not in the DOM's text (the anchor map reads the rows' textContent)");
          assert.equal(f.joinerInSelection, false, cell + ": ...nor in a selection of the whole fence");
        }
        const spanned = py.rows.find((r: Facts) => r.spanned);
        assert.ok(spanned, mode + " " + label + ": the docstring's blank line is a .ct holding an empty hljs span and no text");
        assert.equal(spanned.h, py.lh, mode + " " + label + ": ...and its row is one line too (a :empty rule would have missed it)");
      }
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

test("a 10005-line fence: every row's gutter holds five digits, so rows 9999 and 10000 start their text at one edge; a 1200-line fence keeps the 2.5em gutter", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: BIG } });
    await page.waitForFunction((k: number) => document.querySelectorAll(".fileview-md pre code .cl").length >= k, BIG_N, { timeout: 90000 }); await frames(page, 2);
    const m = await page.evaluate((idx: number[]) => {
      const code = document.querySelector(".fileview-md pre code") as HTMLElement; const rows = Array.from(code.querySelectorAll(":scope > .cl")) as HTMLElement[];
      const lefts: Record<string, number> = {}; for (const r of rows) { const k = (r.querySelector(".ct") as HTMLElement).getBoundingClientRect().left.toFixed(3); lefts[k] = (lefts[k] || 0) + 1; }
      // five zero glyphs at the gutter's size, in the code's own font: what five digits need
      const sp = document.createElement("span"); sp.style.cssText = "font-size: 0.92em; white-space: nowrap"; sp.textContent = "00000"; code.appendChild(sp); const five = sp.getBoundingClientRect().width; sp.remove();
      return { n: rows.length, lefts, five, digits: getComputedStyle(code).getPropertyValue("--ln-digits").trim(),
        rows: idx.map((i) => { const r = rows[i - 1]; return { line: i, gutterW: parseFloat(getComputedStyle(r, "::before").width), h: r.getBoundingClientRect().height }; }) };
    }, [1, 9999, 10000, BIG_N]);
    assert.equal(m.n, BIG_N);
    assert.equal(m.digits, "5", "wrapCodeLines wrote the fence's digit count on the code element (--ln-digits)");
    assert.equal(Object.keys(m.lefts).length, 1, "one text edge for all " + BIG_N + " rows (before: 9999 rows at one edge and six 5.625px further right): " + JSON.stringify(m.lefts));
    for (const r of m.rows) { assert.ok(r.gutterW >= m.five && r.gutterW < m.five + 2, "row " + r.line + "'s gutter holds five digits (" + r.gutterW + " for " + m.five.toFixed(2) + ")"); assert.equal(r.h, 18, "row " + r.line + " is one line"); }
    assert.equal(m.rows[0].gutterW, m.rows[2].gutterW, "row 1's gutter is row 10000's");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
    // the 1200-line fence: four digits fit the 2.5em basis, which stays the floor (max(2.5em, 4ch + 0.05em) is 2.5em here)
    const small = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: LONG } });
    await small.page.waitForFunction(() => document.querySelectorAll(".fileview-md pre code .cl").length >= 1200, null, { timeout: 15000 }); await frames(small.page, 2);
    const s = await small.page.evaluate(() => { const code = document.querySelector(".fileview-md pre code") as HTMLElement; const r = code.querySelector(":scope > .cl")!; const b = getComputedStyle(r, "::before"); return { digits: getComputedStyle(code).getPropertyValue("--ln-digits").trim(), gutterW: parseFloat(b.width), em: parseFloat(b.fontSize) }; });
    assert.equal(s.digits, "4"); assert.ok(Math.abs(s.gutterW - 2.5 * s.em) < 0.1, "the 1200-line fence's gutter is 2.5em of the gutter's font (" + s.gutterW + " for " + (2.5 * s.em).toFixed(2) + ")");
    await small.page.close();
  });
});

test("a code row kept at the body's top edge comes back to the same pixel after Rendered to Raw to Rendered, three trips, at pane 380, pane 900 and pane 1000 with the aside", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width, aside] of [["pane", 380, false], ["pane", 900, false], ["pane", 1000, true]] as [Mode, number, boolean][]) {
      const cell = `${mode} ${width}px${aside ? " with the aside" : ""}`;
      const { page, errors } = await openViewer(browser, mode, width, 600, { docs: { [REPORT]: NOTE } });
      if (aside) await openPanel(page);
      const g0 = await rowTop(page);
      // the fence's fourth row to the body's top edge, on a whole pixel, as a person's scroll leaves it
      await page.evaluate((top: number) => { const b = document.querySelector(".fileview-body")!; b.scrollTop = Math.round(b.scrollTop + top); }, g0.top); await frames(page, 3);
      const start = await rowTop(page);
      assert.ok(Math.abs(start.top) < 1, cell + ": the row is at the edge (" + start.top + ")");
      for (let trip = 1; trip <= 3; trip++) {
        await click(page, "Raw", ".fileview-body .fv-cl");
        await click(page, "Rendered", ".fileview-md pre code > .cl");
        const back = await rowTop(page);
        assert.equal(back.top, start.top, cell + ": trip " + trip + " brings the row back to the same pixel (before: it crept a pixel a trip at 380 and beside the aside; scrollTop " + back.scrollTop + " vs " + start.scrollTop + ")");
      }
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});
