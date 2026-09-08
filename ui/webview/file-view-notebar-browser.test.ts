// The viewer's notice bar survives the body's scroll and a swap of the body's children, in headless Chromium over the
// REAL module (plans/markdown-viewer.md, Slice 2). Before this slice noteBar (file-view.ts) prepended #fileview-save-err
// INTO .fileview-body, so it scrolled away with the text (at scrollTop 400 it sat 400px above the body's top), went with
// the next body.replaceChildren (a Rendered/Raw switch, a reload), and the "past the end" notice scrollToLine raises was
// never seen at all: the row it lands on is scrolled into view AFTER the notice is prepended, which puts the notice 6700px
// above the body's top (the slice's gap analysis, executed 2026-09-08). The bar is now a child of the card between the
// title bar and .fileview-main (box.insertBefore(bar2, main)), so it shows at any scroll position and outlives every
// swap; the editor's entry and exit remove it themselves. Two notices are driven here: the past-the-end notice of an
// open at a line the file lacks, and the Edit refusal the seam's setEditBlocked raises on a click. Legs await frames,
// never a timer. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic
// values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames } from "./real-viewer-leg";

type Bar = { present: boolean; text: string; parent: string; before: string | null; inCard: boolean; aboveRow: boolean; inViewport: boolean; bodyScrollTop: number };
/** Where the notice bar is: its parent, the sibling after it, whether its box lies inside the card, above the body row, in the viewport. */
function readBar(): Bar {
  const bar = document.getElementById("fileview-save-err");
  const body = document.querySelector(".fileview-body") as HTMLElement;
  if (!bar) return { present: false, text: "", parent: "", before: null, inCard: false, aboveRow: false, inViewport: false, bodyScrollTop: body.scrollTop };
  const r = bar.getBoundingClientRect(), card = document.querySelector(".fileview")!.getBoundingClientRect(), main = document.querySelector(".fileview-main")!.getBoundingClientRect();
  return {
    present: true, text: bar.textContent || "", parent: (bar.parentElement as HTMLElement).className, before: bar.nextElementSibling ? (bar.nextElementSibling as HTMLElement).className : null,
    inCard: r.top >= card.top - 0.5 && r.bottom <= card.bottom + 0.5 && r.left >= card.left - 0.5 && r.right <= card.right + 0.5,
    aboveRow: r.bottom <= main.top + 0.5 && r.height > 0,
    inViewport: r.top >= 0 && r.bottom <= innerHeight && r.height > 0,
    bodyScrollTop: body.scrollTop,
  };
}

test("in a browser, the real module: a line past the end raises a notice that is SEEN: above the body row, in the card and the viewport, still there after the body scrolls and after a Rendered/Raw switch; pane and chat", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as const) {
      const { page, errors } = await openViewer(browser, mode, 700, 600, { raw: true, openOpts: { line: 9999 } });
      let b: Bar = await page.evaluate(readBar);
      assert.ok(b.present, mode + ": the past-the-end notice is up");
      assert.equal(b.text, "Line 9999 is past the end of this file, which has 201 lines; showing the last line.", mode + ": in the viewer's words");
      assert.equal(b.parent, "fileview", mode + ": a child of the card, not of the body");
      assert.equal(b.before, "fileview-main", mode + ": right above the body row");
      assert.ok(b.aboveRow && b.inCard, mode + ": its box sits above the row, inside the card");
      assert.ok(b.inViewport, mode + ": and on screen, though the body was scrolled to its last row (before the slice the notice sat 6700px above the body's top)");
      assert.ok(b.bodyScrollTop > 1000, mode + ": the body is scrolled far down: " + b.bodyScrollTop);
      // the body scrolls: the notice stays where it is
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 400; });
      await frames(page, 2);
      b = await page.evaluate(readBar);
      assert.ok(b.present && b.inViewport && b.aboveRow, mode + ": at scrollTop 400 the notice is still on screen above the row (before: 400px above the body's top)");
      // the body's children are swapped: the notice outlives the swap
      await page.locator("#romp-fileview .fileview-btn", { hasText: /^Rendered$/ }).click();
      await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 5000 });
      await frames(page, 2);
      b = await page.evaluate(readBar);
      assert.ok(b.present, mode + ": the notice outlives the Rendered swap (before: gone with body.replaceChildren)");
      assert.equal(b.text, "Line 9999 is past the end of this file, which has 201 lines; showing the last line.", mode + ": with its words");
      assert.ok(b.inViewport && b.aboveRow, mode + ": still above the row, on screen");
      await page.locator("#romp-fileview .fileview-btn", { hasText: /^Raw$/ }).click();
      await page.waitForFunction(() => !!document.querySelector(".fileview-body .fv-cl"), null, { timeout: 5000 });
      await frames(page, 2);
      b = await page.evaluate(readBar);
      assert.ok(b.present && b.inViewport, mode + ": and the Raw swap");
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: the Edit refusal is a notice above the body row at any scroll position; a second notice replaces the first; a reload keeps it", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 700, 600);
    await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 1500; });
    await frames(page, 2);
    await page.evaluate(() => { (window as any).__seam.setEditBlocked("Edit is off here while 2 changes are pending in this file."); });
    await page.locator("#romp-fileview .fileview-btn", { hasText: /^Edit$/ }).click();
    await frames(page, 2);
    let b: Bar = await page.evaluate(readBar);
    assert.ok(b.present, "the refusal is up");
    assert.equal(b.text, "Edit is off here while 2 changes are pending in this file.");
    assert.ok(b.aboveRow && b.inCard && b.inViewport, "above the row, in the card, on screen, with the body scrolled to 1500");
    assert.equal(b.bodyScrollTop, 1500, "the body did not move for it");
    await page.evaluate(() => { (window as any).__seam.setEditBlocked("Edit is off here while 3 changes are pending in this file."); });
    await page.locator("#romp-fileview .fileview-btn", { hasText: /^Edit$/ }).click();
    await frames(page, 2);
    b = await page.evaluate(readBar);
    assert.equal(b.text, "Edit is off here while 3 changes are pending in this file.", "one notice at a time: the newer replaced the older");
    assert.equal(await page.evaluate(() => document.querySelectorAll("#fileview-save-err, .fileview > .fileview-err").length), 1, "exactly one bar in the card");
    const paints: number = await page.evaluate(() => (window as any).__paints);
    await page.evaluate(() => { (window as any).__seam.reload(); });
    await page.waitForFunction((k: number) => (window as any).__paints >= k, paints + 1, { timeout: 10000 });
    await frames(page, 2);
    b = await page.evaluate(readBar);
    assert.ok(b.present && b.inViewport, "a reload swaps the body's children and the notice stays");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
