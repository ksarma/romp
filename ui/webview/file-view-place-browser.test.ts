// The reader keeps their place across a paint of the viewer's body, in headless Chromium over the REAL module
// (plans/markdown-viewer.md, Slice 2; reader-place.ts). Before this slice a paint that replaced the body's children left
// the numeric scrollTop over new content: a reload after a session's write that inserted twenty paragraphs above the
// reader moved the top passage from paragraph 40 to 28 at 900px and 29 at 380px; the Rendered/Raw round trip came back
// 648 to 918px further on (the Raw view is taller; paragraph 40 became 53); and a reflow that kept the children moved the
// passage too: closing the Comments aside at 900px took the top paragraph from 40 to 73, a pane drag likewise (the
// slice's gap analysis, executed 2026-09-08). Each scene here scrolls paragraph 40 to the body's top edge, does the thing,
// and reads the top-visible block again: the same paragraph, within a pixel of the same height, whatever the scrollTop.
// The place is the file's own: a block's source span, followed through the edit, so a reload lands on the same block
// and a view switch on the same passage (the Raw row of the block's first line, or the block holding the row). A block
// the write rewrote is placed by the block before it, followed the same way, so the reader lands on what replaced it
// (the fourth scene: with twenty paragraphs inserted above, the block standing where the edit begins would be the first
// inserted one); with that block gone too, by the block after, then by the nearest block that stands
// (file-view-place-edits-browser.test.ts), and only with none standing does the place fall to where the edit begins. The
// URL viewer's Rendered/Raw switch shares the helper. The last scene puts the reader PARTWAY into the top block, where a reflow of the
// same text keeps the depth as a fraction of the block's height (reader-place.ts): the Comments aside opening held it in
// pixels instead (the browser's anchoring adjustment, read as the reader's place under the new width, left the repaint's
// seat nothing to move) while the close applied the fraction, so every toggle walked the words at the body's top edge
// toward the block's start, and a sized picture the reader was two thirds into went wholly above the edge on the first
// open (the Slice 2 review, round 2). Legs await frames and paint counts, never a timer. Skips LOUDLY without a
// playwright browser (CI installs none), as the other browser legs do. Synthetic values only: an invented report,
// /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, closePanel, frames, paintsReach, topBlock, putAtTop, LONG, LONG2, PARA, rewritten, REPORT, MT2, ORIGIN } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
const P40 = "Paragraph 40:";

test("in a browser, the real module: a reload that inserts twenty paragraphs above the reader keeps the top block at its height, Rendered and Raw, in the pane at 900 and 380px and in the chat modal; with the Comments aside open too", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width, raw, panel] of [["pane", 900, false, false], ["pane", 380, false, false], ["chat", 900, false, false], ["pane", 900, true, false], ["pane", 900, false, true]] as const) {
      const cell = `${mode} ${width}px ${raw ? "Raw" : "Rendered"}${panel ? " with the aside" : ""}`;
      const { page, errors } = await openViewer(browser, mode, width, 600, { raw });
      if (panel) await openPanel(page);
      await putAtTop(page, P40);
      await frames(page, 2);
      const before = (await topBlock(page))!;
      assert.equal(before.text, P40, cell + ": the scene starts with paragraph 40 at the top");
      near(before.top, 0, cell + ": at the body's top edge", 1);
      const paints: number = await page.evaluate(() => (window as any).__paints);
      await page.evaluate(([p, t, m]: [string, string, string]) => { (window as any).__docs[p] = t; (window as any).__mtime = m; (window as any).__seam.reload(); }, [REPORT, LONG2, MT2]);
      await paintsReach(page, paints + 1);
      await frames(page, 2);
      const after = (await topBlock(page))!;
      assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT2, cell + ": the reload landed the new bytes");
      assert.equal(after.text, P40, cell + ": the top block is still paragraph 40 (before the slice: paragraph 28 at 900px, 29 at 380px)");
      near(after.top, before.top, cell + ": at the same height");
      assert.ok(after.scrollTop > before.scrollTop, cell + `: the scrollTop moved on by the inserted text (${before.scrollTop} to ${after.scrollTop}); the passage did not`);
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: Rendered to Raw to Rendered returns to the same passage (the Raw row of the block's first line, then the block again), pane and chat, 900 and 380px; the URL viewer's switch too", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width, url] of [["pane", 900, false], ["pane", 380, false], ["chat", 900, false], ["chat", 900, true]] as const) {
      const cell = `${mode} ${width}px${url ? " (URL viewer)" : ""}`;
      const { page, errors } = url
        ? await openViewer(browser, mode, width, 600, { url: "/docs/report.md", urls: { [ORIGIN + "/docs/report.md"]: LONG } })
        : await openViewer(browser, mode, width, 600);
      await putAtTop(page, P40);
      await frames(page, 2);
      const start = (await topBlock(page))!;
      assert.equal(start.text, P40, cell + ": paragraph 40 at the top");
      const click = async (label: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 2); };
      await click("Raw");
      const inRaw = (await topBlock(page))!;
      assert.equal(inRaw.view, "raw", cell + ": the Raw view is up");
      assert.equal(inRaw.text, P40, cell + ": the top row is paragraph 40's line (before the slice: paragraph 36 at 900px, 41 at 380px)");
      near(inRaw.top, start.top, cell + ": at the same height");
      await click("Rendered");
      const back = (await topBlock(page))!;
      assert.equal(back.view, "rendered", cell + ": the Rendered view is back");
      assert.equal(back.text, P40, cell + ": and paragraph 40 is the top block again (before the slice: paragraph 53 at 900px, 45 at 380px)");
      near(back.top, start.top, cell + ": at the same height");
      // the plan's text asked for the same scrollTop across the round trip; the passage is what the reader keeps, and the two
      // views are not the same height (the Raw view was the taller until Slice 3 of plans/markdown-viewer.md gave the prose
      // 15px in an 80ch column, which is taller than the 12px rows at the pane's width at 900), so the Raw scrollTop differs
      // by design; the Rendered layout is the same on the way back, so there the number returns with the passage
      assert.notEqual(inRaw.scrollTop, start.scrollTop, cell + `: the Raw view's scrollTop differs (rendered ${start.scrollTop}, raw ${inRaw.scrollTop})`);
      near(back.scrollTop, start.scrollTop, cell + ": back in Rendered the scrollTop is back too", 2);
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: the width reflow keeps the place, whichever way the body's width moves: the Comments aside opening and closing, the pane resized; and a text-size step keeps it too", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 600);
    await putAtTop(page, P40);
    await frames(page, 2);
    const start = (await topBlock(page))!;
    assert.equal(start.text, P40);
    const bodyWidth = () => page.evaluate(() => document.querySelector(".fileview-body")!.getBoundingClientRect().width);
    const w0 = await bodyWidth();
    // the aside opens: the body narrows, the text wraps taller, and the paragraph under the eye would slide down
    let paints: number = await page.evaluate(() => (window as any).__paints);
    await openPanel(page);
    await paintsReach(page, paints + 1);   // the reflow's own paint (the ResizeObserver's frame)
    await frames(page, 2);
    assert.ok((await bodyWidth()) < w0 - 200, "the body narrowed for the aside");
    let now = (await topBlock(page))!;
    assert.equal(now.text, P40, "paragraph 40 stays the top block as the aside opens");
    near(now.top, start.top, "at the same height");
    // the aside closes: the body widens, the text gets shorter, and the reader used to land on paragraph 73
    paints = await page.evaluate(() => (window as any).__paints);
    await closePanel(page);
    await paintsReach(page, paints + 1);
    await frames(page, 2);
    near(await bodyWidth(), w0, "the body is back to its width", 1);
    now = (await topBlock(page))!;
    assert.equal(now.text, P40, "paragraph 40 stays the top block as the aside closes (before the slice: paragraph 73)");
    near(now.top, start.top, "at the same height");
    // the pane dragged narrower (the viewport, here) and back
    for (const width of [600, 900]) {
      paints = await page.evaluate(() => (window as any).__paints);
      await page.setViewportSize({ width, height: 600 });
      await paintsReach(page, paints + 1);
      await frames(page, 2);
      now = (await topBlock(page))!;
      assert.equal(now.text, P40, `paragraph 40 stays the top block at ${width}px`);
      near(now.top, start.top, `at the same height at ${width}px`);
    }
    // a text-size step: the text grows around the reader
    paints = await page.evaluate(() => (window as any).__paints);
    await page.click('button[aria-label="Larger text"]');
    await paintsReach(page, paints + 1);
    await frames(page, 2);
    now = (await topBlock(page))!;
    assert.equal(now.text, P40, "paragraph 40 stays the top block after A+");
    near(now.top, start.top, "at the same height after A+");
    // the reader scrolls on after a reflow: the place read then is the one a later reflow keeps (the scroll-time read)
    await page.evaluate(() => { (window as any).putAtTop("Paragraph 60:"); });
    await frames(page, 3);
    paints = await page.evaluate(() => (window as any).__paints);
    await page.setViewportSize({ width: 700, height: 600 });
    await paintsReach(page, paints + 1);
    await frames(page, 2);
    now = (await topBlock(page))!;
    assert.equal(now.text, "Paragraph 60:", "the place the reader scrolled to after the earlier reflow is the one kept");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real module: when the write rewrote the block under the reader's eye, the reload lands on what replaced it, placed by the block before, also when the same write inserted twenty paragraphs above", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const above of [false, true]) {
      const cell = above ? "rewritten, with twenty paragraphs inserted above" : "rewritten in place";
      const { page, errors } = await openViewer(browser, "pane", 900, 600);
      await putAtTop(page, P40);
      await frames(page, 2);
      const before = (await topBlock(page))!;
      assert.equal(before.text, P40);
      const paints: number = await page.evaluate(() => (window as any).__paints);
      await page.evaluate(([p, t, m]: [string, string, string]) => { (window as any).__docs[p] = t; (window as any).__mtime = m; (window as any).__seam.reload(); }, [REPORT, rewritten(40, above), MT2]);
      await paintsReach(page, paints + 1);
      await frames(page, 2);
      const after = (await topBlock(page))!;
      assert.equal(after.text, "Rewritten 40:", cell + ": the rewritten paragraph stands at the top where paragraph 40 stood (before the slice, with the insertion: paragraph 28; the edit's own start would be the first inserted paragraph)");
      near(after.top, before.top, cell + ": at the same height");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

// ── the reader partway into the top block ─────────────────────────────────────────────────────────
type Depth = { top: number; height: number; frac: number; isTop: boolean; width: number; scrollTop: number };
/** The box of the block found by `find` (the first `.fileview-md > *` whose text starts with `find.text`, or the element
 *  `find.sel` selects), measured from the body's top edge: its top, its height, the reader's depth into it as a fraction of
 *  its height (0 with its top at the edge, 1 with its bottom there), whether it is the top-visible block, and the body's
 *  width and scrollTop. */
const depthInto = (page: any, find: { text?: string; sel?: string }): Promise<Depth> => page.evaluate((f: { text?: string; sel?: string }) => {
  const body = document.querySelector(".fileview-body") as HTMLElement, br = body.getBoundingClientRect();
  const kids = Array.from(document.querySelectorAll(".fileview-md > *")) as HTMLElement[];
  const el = f.sel ? (document.querySelector(f.sel) as HTMLElement) : kids.filter((e) => (e.textContent || "").indexOf(f.text!) === 0)[0];
  const r = el.getBoundingClientRect();
  const top = kids.find((e) => e.getBoundingClientRect().bottom > br.top + 0.5);
  return { top: Math.round((r.top - br.top) * 10) / 10, height: Math.round(r.height * 10) / 10, frac: Math.round((br.top - r.top) / r.height * 1000) / 1000,
    isTop: top === el || (!!top && top.contains(el)), width: body.clientWidth, scrollTop: body.scrollTop };
}, find);
/** The block's top edge is where the fraction rule puts it: `frac` of its height now above the body's top edge. */
const keepsFraction = (d: Depth, frac: number, what: string) => near(d.top, -frac * d.height, `${what}: the block's top edge is ${frac} of its height (${d.height}) above the edge`, 2);

test("in a browser, the real module: a reader partway into the top block keeps the depth as a fraction of the block's height across the Comments aside opening as well as closing (before: the open held it in pixels, halving the fraction per toggle), across a pane drag both ways, and two thirds into a sized picture", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // a paragraph, 80px in with the aside open (the margin layout at 900px), the panel toggled three times
    let { page, errors } = await openViewer(browser, "pane", 900, 600);
    let paints: number = await page.evaluate(() => (window as any).__paints);
    await openPanel(page);
    await paintsReach(page, paints + 1);
    await putAtTop(page, "Paragraph 44:");
    await page.evaluate(() => { document.querySelector(".fileview-body")!.scrollTop += 80; });
    await frames(page, 3);                                                  // the scroll-time read
    const start = await depthInto(page, { text: "Paragraph 44:" });
    assert.ok(start.isTop && start.frac > 0.5 && start.frac < 1, `the scene starts deep in paragraph 44 (top ${start.top}, height ${start.height})`);
    for (let i = 1; i <= 3; i++) {
      paints = await page.evaluate(() => (window as any).__paints);
      await closePanel(page);
      await paintsReach(page, paints + 1);
      await frames(page, 2);
      const closed = await depthInto(page, { text: "Paragraph 44:" });
      assert.ok(closed.isTop, `close ${i}: paragraph 44 is the top block`);
      assert.ok(closed.width > start.width + 200, `close ${i}: the body widened (${start.width} to ${closed.width})`);
      keepsFraction(closed, start.frac, `close ${i}`);
      paints = await page.evaluate(() => (window as any).__paints);
      await openPanel(page);
      await paintsReach(page, paints + 1);
      await frames(page, 2);
      const opened = await depthInto(page, { text: "Paragraph 44:" });
      assert.ok(opened.isTop, `open ${i}: paragraph 44 is the top block`);
      assert.equal(opened.width, start.width, `open ${i}: the body is back to the aside's width`);
      keepsFraction(opened, start.frac, `open ${i} (before the fix: the pixel depth held, the fraction halved: 0.48 after the first open, 0.24 after the second)`);
      near(opened.top, start.top, `open ${i}: paragraph 44's top edge is back where the scene started (before the fix: 40px lower after the first toggle, 60 after the second)`, 2);
    }
    // a pane drag (the viewport, here) with the aside closed, 30px into paragraph 44: the fraction both ways; at 600px the
    // block is shorter than the pixel depth, so a pixel hold would leave it wholly above the edge with paragraph 45 on top
    // (the paragraph is three lines at 900px since Slice 3 of plans/markdown-viewer.md, two before, so the fraction there
    // is below a half now)
    paints = await page.evaluate(() => (window as any).__paints);
    await closePanel(page);
    await paintsReach(page, paints + 1);
    await putAtTop(page, "Paragraph 44:");
    await page.evaluate(() => { document.querySelector(".fileview-body")!.scrollTop += 30; });
    await frames(page, 3);
    const wide = await depthInto(page, { text: "Paragraph 44:" });
    assert.ok(wide.isTop && wide.frac > 0.3 && wide.frac < 1, `the drag starts 30px into paragraph 44 at 900px (top ${wide.top}, height ${wide.height})`);
    for (const width of [600, 900, 600, 900]) {
      paints = await page.evaluate(() => (window as any).__paints);
      await page.setViewportSize({ width, height: 600 });
      await paintsReach(page, paints + 1);
      await frames(page, 2);
      const d = await depthInto(page, { text: "Paragraph 44:" });
      assert.ok(d.isTop, `at ${width}px paragraph 44 is the top block`);
      keepsFraction(d, wide.frac, `at ${width}px (before the fix: the pixel depth held, 0.48 of the taller block at 600px)`);
      if (width === 900) near(d.top, wide.top, "back at 900px, paragraph 44's top edge is back where the drag started", 2);
    }
    assert.deepEqual(errors, [], "no script error");
    await page.close();
    // a sized picture (900 by 600, a 3:2 figure laid out at the column's width: 573px tall at 900px, 349 beside the aside)
    // the reader is two thirds into, the panel toggled twice: before the fix the first open held the pixel depth and the
    // picture went wholly above the edge, paragraph 31 on top, and no toggle brought it back
    const svg = encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600"><rect width="900" height="600" fill="#888"/></svg>');
    const FIGURE = "# Report\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 1)).join("\n\n") + `\n\n<img src="data:image/svg+xml,${svg}" width="900" height="600">\n\n` + Array.from({ length: 30 }, (_, i) => PARA(i + 31)).join("\n\n") + "\n";
    ({ page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: FIGURE } }));
    await page.waitForFunction(() => { const i = document.querySelector(".fileview-md img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0; }, null, { timeout: 10000 });
    await frames(page, 2);
    await page.evaluate(() => { const body = document.querySelector(".fileview-body")!, i = document.querySelector(".fileview-md img")!; const r = i.getBoundingClientRect(); body.scrollTop += r.top - body.getBoundingClientRect().top + r.height * 2 / 3; });
    await frames(page, 3);
    const pic = await depthInto(page, { sel: ".fileview-md img" });
    assert.ok(pic.isTop && pic.height > 500, `the picture is the top block, two thirds in (top ${pic.top}, height ${pic.height})`);
    near(pic.frac, 2 / 3, "two thirds in", 0.01);
    for (const step of ["open 1", "close 1", "open 2"]) {
      paints = await page.evaluate(() => (window as any).__paints);
      if (step.startsWith("open")) await openPanel(page); else await closePanel(page);
      await paintsReach(page, paints + 1);
      await frames(page, 2);
      const d = await depthInto(page, { sel: ".fileview-md img" });
      assert.ok(d.isTop, `${step}: the picture is still the top block (before the fix: wholly above the edge after the first open, paragraph 31 on top)`);
      keepsFraction(d, pic.frac, `${step}`);
    }
    assert.deepEqual(errors, [], "figure: no script error");
    await page.close();
  });
});
