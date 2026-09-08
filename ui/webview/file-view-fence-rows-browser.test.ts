// A fence's rows in the viewer (Slice 3 of plans/markdown-viewer.md, review round 1): three defects of one rule, the line-number
// gutter `.fileview-md pre code .cl::before` (the chat's `pre code .cl::before`, which the viewer copies declaration for
// declaration; code-block.test.ts pins the copy). (1) The gutter at 0.92em under `align-items: baseline` made every row
// 18.5625px against the code's 18px line-height: Chromium floors the half-leading it puts above a line box, so the smaller
// gutter's box hung 0.5625px further below the shared baseline than the text's did, and the row grew by that much (the Raw
// view's rows of the same lines are 18px; a 300-line fence was 169px taller in Rendered). (2) The same fraction crept the
// kept code line 1px per Rendered/Raw round trip at some widths: the row-aware seat maps an 18.5625px row onto an 18px one
// and back, and the integer scrollTop rounds the difference. (3) The gutter inherited `overflow-wrap: anywhere` from the code,
// so a four-digit number broke across two lines and every row from line 1000 on was double height, reading "100" over "0".
// The fix: `line-height: 1` on the gutter (its box never taller than the text's, both baselines still shared), `overflow-wrap:
// normal` (the number never breaks; past four digits the gutter grows instead), and a 2.5em basis that holds four digits.
// Measured over the real bundle and sheets on the pane. Skips loudly without a browser. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, REPORT, type Mode } from "./real-viewer-leg";

const F = "```";
const P = (i: number) => "Paragraph " + i + ": " + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(3).trim() + ".";
const LONG = ["# A long fence", "", "Prose before.", "", F + "python", ...Array.from({ length: 1200 }, (_, i) => `x_${i + 1} = ${i + 1}  # line ${i + 1}`), F, "", "Prose after.", ""].join("\n");
const CODE = ["# a comment line", "def f(x):", "    return x  # spaces", "y = f(1)", "z = f(2)", "print(y, z)"];
const NOTE = ["# Report", "", "## Section two", "", ...Array.from({ length: 5 }, (_, i) => P(i + 1) + "\n"), F + "python", ...CODE, F, "", ...Array.from({ length: 60 }, (_, i) => P(i + 6) + "\n")].join("\n");

type Facts = Record<string, any>;
function rowFacts(): Facts {
  const code = document.querySelector(".fileview-md pre code")!; const rows = Array.from(code.querySelectorAll(":scope > .cl")) as HTMLElement[];
  const hist: Record<string, number> = {}; for (const r of rows) { const k = r.getBoundingClientRect().height.toFixed(4); hist[k] = (hist[k] || 0) + 1; }
  const h = (i: number) => rows[i - 1].getBoundingClientRect().height; const b = getComputedStyle(rows[999], "::before");
  return { n: rows.length, hist, h1: h(1), h999: h(999), h1000: h(1000), h1200: h(1200), ct: (rows[0].querySelector(".ct") as HTMLElement).getBoundingClientRect().height,
    lineHeight: parseFloat(getComputedStyle(code).lineHeight), codeH: code.getBoundingClientRect().height, align: getComputedStyle(rows[0]).alignItems,
    before: { fontSize: b.fontSize, lineHeight: b.lineHeight, width: parseFloat(b.width), overflowWrap: b.overflowWrap, content: b.content } };
}
const rowTop = (page: any) => page.evaluate(() => { const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect(); const rows = Array.from(document.querySelectorAll(".fileview-md pre code > .cl")); const r = rows[3].getBoundingClientRect(); return { top: r.top - br.top, height: r.height, scrollTop: body.scrollTop }; });
const click = async (page: any, label: string, until: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await page.waitForFunction((s: string) => !!document.querySelector(s), until, { timeout: 5000 }); await frames(page, 3); };

test("every row of a 1200-line fence is exactly the code's line-height, at 100 and 150 percent, four- and five-digit numbers included; the number never breaks", { timeout: 120000 }, async (t) => {
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
    // five digits: restart the counter at 9998, so the first two rows read 9999 and 10000; the gutter grows rather than the row
    await page.evaluate(() => { (document.querySelector(".fileview-md pre code") as HTMLElement).style.counterReset = "ln 9998"; }); await frames(page, 2);
    const five = await page.evaluate(() => { const rows = Array.from(document.querySelectorAll(".fileview-md pre code > .cl")) as HTMLElement[]; const b = (i: number) => getComputedStyle(rows[i], "::before"); return { n1: b(0).content, n2: b(1).content, h1: rows[0].getBoundingClientRect().height, h2: rows[1].getBoundingClientRect().height, w1: parseFloat(b(0).width), w2: parseFloat(b(1).width) }; });
    assert.equal(five.h1, m.lineHeight, "row 9999 is one line"); assert.equal(five.h2, m.lineHeight, "row 10000 is one line: the gutter widened instead (" + five.w1 + " to " + five.w2 + "px)");
    assert.ok(five.w2 > five.w1 + 4, "...by about a digit (" + five.w1 + " to " + five.w2 + ")");
    await page.evaluate(() => { (document.querySelector(".fileview-md pre code") as HTMLElement).style.counterReset = ""; }); await frames(page, 2);
    // 150 percent: three steps of the text-size control; the rows follow the scaled line-height exactly
    for (let i = 0; i < 3; i++) await page.click('button[aria-label="Larger text"]');
    await page.waitForFunction(() => getComputedStyle(document.querySelector(".fileview-md")!).getPropertyValue("--fv-scale").trim() === "1.5", null, { timeout: 5000 }); await frames(page, 2);
    const big = await page.evaluate(rowFacts);
    assert.equal(big.lineHeight, 27, "18px line-height at 150 percent is 27px");
    assert.deepEqual(Object.keys(big.hist), ["27.0000"], "every row is 27px at 150 percent (before: 27.844 and 52.688): " + JSON.stringify(big.hist));
    assert.deepEqual(errors, [], "no script error");
    await page.close();
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
