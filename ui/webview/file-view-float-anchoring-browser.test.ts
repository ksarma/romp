// The Comment float stays up when Chromium's scroll anchoring writes the body's scrollTop without moving the passage on
// screen, in headless Chromium over the REAL module and the REAL panel (plans/markdown-viewer.md Slice 2, item 8, and the
// slice's review, round 2; file-comments.ts hideFloatOnScroll). The float hides on the body's scroll because the passage it
// sat beside has moved from under it (file-comments-float-scroll-browser.test.ts). One body scroll moves nothing on screen:
// when an unsized picture ABOVE the viewport lands its bytes, Chromium's anchoring (the sheets declare no overflow-anchor,
// file-view-place.test.ts) grows scrollTop by the picture's height so the reader's text stays put, and fires a scroll event
// for that write. Round 1's listener hid the float on that event too: the selection within a pixel of where it was,
// scrollTop up by the picture, the button gone, and a reader who selected a passage while a figure above was still
// loading had to select again (a plain click on the standing selection collapses it). The listener now compares the
// subject's screen rect with the one the button was offered beside and keeps the float while the passage sits within a
// pixel of it (scrollTop is whole pixels, the growth above fractional). A reader's own scroll still hides it, which the
// second half of every cell states. The picture's request is held by a page route until the float is up, so the load is
// the leg's own event, never a timer. Skips LOUDLY without a playwright browser (CI installs none), as the other browser
// legs do. Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, paintsReach, putAtTop, REPORT, MT2, PARA } from "./real-viewer-leg";

/** The report with an unsized figure under the heading: its box is 0x0 until the bytes land, 524x349 in a 900px pane after. */
const FIGURE_DOC = "# Report\n\n![late figure](figure.svg)\n\n" + Array.from({ length: 100 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"><rect width="600" height="400" fill="steelblue"/></svg>';

/** Drag across the first twelve characters of the paragraph starting with `text` (in view, below the body's top line, where
 *  Chromium autoscrolls a selection drag), so the seam's mouseup offers the float. A fresh gesture: the selection is cleared
 *  first, since a mousedown on selected text starts a drag of that text. */
async function selectIn(page: any, text: string): Promise<void> {
  await page.evaluate(() => { getSelection()!.removeAllRanges(); });
  await frames(page, 1);
  const r = await page.evaluate((t: string) => {
    const p = Array.from(document.querySelectorAll(".fileview-md > p")).find((e) => (e.textContent || "").startsWith(t)) as HTMLElement;
    const range = document.createRange(); range.setStart(p.firstChild!, 0); range.setEnd(p.firstChild!, 12);
    const b = range.getBoundingClientRect();
    return { x1: b.left + 1, x2: b.right - 1, y: b.top + b.height / 2 };
  }, text);
  await page.mouse.move(r.x1, r.y);
  await page.mouse.down();
  await page.mouse.move(r.x2, r.y, { steps: 4 });
  await page.mouse.up();
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
}

type Scene = { floatHidden: boolean; floatTop: number; selected: string; selTop: number; bodyScrollTop: number; scrolls: number; img: { w: number; h: number; complete: boolean } | null };
/** The float, the selection's screen rect, the body's position, the scroll events counted since the last reset, the picture's box. */
const scene = (page: any): Promise<Scene> => page.evaluate(() => {
  const f = document.querySelector(".fc-float") as HTMLElement;
  const sel = getSelection()!; const sr = sel.rangeCount ? sel.getRangeAt(0).getBoundingClientRect() : null;
  const img = document.querySelector(".fileview-md img") as HTMLImageElement | null; const ir = img ? img.getBoundingClientRect() : null;
  return {
    floatHidden: f.hidden, floatTop: f.getBoundingClientRect().top, selected: String(sel), selTop: sr ? sr.top : NaN,
    bodyScrollTop: (document.querySelector(".fileview-body") as HTMLElement).scrollTop, scrolls: (window as any).__scrolls as number,
    img: img && ir ? { w: Math.round(ir.width), h: Math.round(ir.height), complete: img.complete && img.naturalWidth > 0 } : null,
  };
});

test("in a browser, the real module and panel: the float offered beside a selection stays when a picture above the viewport lands and Chromium's anchoring writes scrollTop without moving the passage; the reader's own scroll still hides it", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, reader, pick] of [["pane", 3, 4], ["pane", 30, 31], ["chat", 3, 4]] as const) {
      const cell = mode + " 900 reader@Paragraph " + reader + " select@Paragraph " + pick;
      const readerAt = "Paragraph " + reader + ":", selectAt = "Paragraph " + pick + ":", words = PARA(pick).slice(0, 12);   // the twelve characters the drag selects
      const { page, errors } = await openViewer(browser, mode, 900, 600);          // the report without the picture: no request for it yet
      // the picture's request is held here until the leg releases it (registered after the page's own route, so it wins)
      let release: (route: any) => void = () => {};
      const held: Promise<any> = new Promise((resolve) => { release = resolve; });
      await page.route((u: URL) => u.href.includes("figure.svg"), (route: any) => { release(route); });
      const p0: number = await page.evaluate(() => (window as any).__paints);
      await page.evaluate(([path, text, m]: [string, string, string]) => { (window as any).__docs[path] = text; (window as any).__mtime = m; (window as any).__seam.reload(); }, [REPORT, FIGURE_DOC, MT2]);
      await paintsReach(page, p0 + 1);
      const route = await held;                                                      // the browser asked for the picture
      await frames(page, 3);
      await openPanel(page);
      await page.evaluate(() => { (window as any).__scrolls = 0; (document.querySelector(".fileview-body") as HTMLElement).addEventListener("scroll", () => { (window as any).__scrolls++; }, { passive: true }); });
      await putAtTop(page, readerAt);
      await frames(page, 2);
      await selectIn(page, selectAt);
      await frames(page, 2);
      await page.evaluate(() => { (window as any).__scrolls = 0; });                 // count the events between the offer and the load alone
      const s0 = await scene(page);
      assert.equal(s0.floatHidden, false, cell + ": the float is offered beside the selection");
      assert.equal(s0.selected, words, cell + ": over the selected words");
      assert.ok(s0.bodyScrollTop > 100, cell + ": the reader is scrolled into the report: " + s0.bodyScrollTop);
      assert.deepEqual(s0.img, { w: 0, h: 0, complete: false }, cell + ": the picture above the viewport has no bytes yet, so no box");
      await route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG });
      await page.waitForFunction(() => { const i = document.querySelector(".fileview-md img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0; }, null, { timeout: 5000 });
      await frames(page, 4);
      const s1 = await scene(page);
      // the scene is the one under test: the picture grew above the reader, anchoring wrote scrollTop by its height and fired a
      // body scroll event for the write, and the passage did not move on screen
      assert.ok(s1.img && s1.img.complete && s1.img.h > 200, cell + ": the picture laid out: " + JSON.stringify(s1.img));
      assert.ok(s1.bodyScrollTop - s0.bodyScrollTop > 200, cell + ": anchoring grew scrollTop by the picture: " + s0.bodyScrollTop + " -> " + s1.bodyScrollTop);
      assert.ok(s1.scrolls >= 1, cell + ": the anchoring adjustment fired a body scroll event: " + s1.scrolls);
      assert.ok(Math.abs(s1.selTop - s0.selTop) < 1, cell + ": the passage stayed put on screen: " + s0.selTop + " -> " + s1.selTop);
      assert.equal(s1.selected, words, cell + ": the selection stands");
      // what the round-2 fix states: the passage is still under the float, so the button stays where it was offered
      assert.equal(s1.floatHidden, false, cell + ": the float stays up beside the passage that did not move (round 1 hid it on this scroll event)");
      assert.ok(Math.abs(s1.floatTop - s0.floatTop) < 1, cell + ": at the same place: " + s0.floatTop + " -> " + s1.floatTop);
      // the reader's own scroll moves the passage from under the button, and the float goes as before
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop += 300; });
      await frames(page, 2);
      const s2 = await scene(page);
      assert.equal(s2.bodyScrollTop, s1.bodyScrollTop + 300, cell + ": the body moved");
      assert.equal(s2.floatHidden, true, cell + ": the float hides once the passage moved under the reader");
      assert.equal(s2.selected, words, cell + ": the selection itself stands");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});
