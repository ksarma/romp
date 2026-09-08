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
// inserted one); only with that block gone too does the place fall to where the edit begins. The URL viewer's
// Rendered/Raw switch shares the helper. Legs await frames and paint counts, never a timer. Skips LOUDLY without a
// playwright browser (CI installs none), as the other browser legs do. Synthetic values only: an invented report,
// /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, closePanel, frames, paintsReach, topBlock, putAtTop, LONG, LONG2, rewritten, REPORT, MT2, ORIGIN } from "./real-viewer-leg";

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
      // the plan's text asked for the same scrollTop across the round trip; the passage is what the reader keeps, and the Raw
      // view is the taller of the two (monospace rows, a row per blank line), so its scrollTop is larger by design; the
      // Rendered layout is the same on the way back, so there the number returns with the passage
      assert.ok(inRaw.scrollTop > start.scrollTop, cell + `: the Raw view's scrollTop is larger (rendered ${start.scrollTop}, raw ${inRaw.scrollTop})`);
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
