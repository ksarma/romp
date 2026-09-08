// The Comment float hides when the body scrolls, in headless Chromium over the REAL module and the REAL panel
// (plans/markdown-viewer.md, Slice 2; file-comments.ts hideFloatOnScroll). The float is a fixed-position button placed
// beside the selection on mouseup; before this slice nothing heard the body's scroll, so after a wheel of 300px it stood
// at its old screen position while the selected passage had left the body (the slice's gap analysis, executed
// 2026-09-08: the float visible at the same coordinates with the selection's rect 36px above the body). The listener sits
// with the float's other listeners in the panel's constructor, so it holds in the list layout (a narrow pane) and the
// margin layout alike; installLayout's scroll listeners were not the place: they feed the margin lock's mirrorScroll,
// which returns early unless the aside is open in the margin layout, while installLayout itself runs from the same
// constructor for every layout. In the margin layout the lock mirrors a scroll of the cards track onto the body with
// a write of body.scrollTop, and that write fires the same scroll event: the float hides then too, which the second
// scene states, since the passage has moved under the reader just the same. The selection itself stands after the
// scroll; only the button goes. The one body scroll that moves nothing on screen, Chromium's anchoring adjustment when
// a figure above the viewport lands, keeps the float: file-view-float-anchoring-browser.test.ts. Legs await frames,
// never a timer. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic
// values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames } from "./real-viewer-leg";

/** With the body at its top, drag across the first twelve characters of the paragraph starting with `text`, so the seam's
 *  mouseup offers the float. The first paragraph: it sits under the heading in every layout, inside the short body the
 *  stacked layout leaves, and clear of the body's top edge, where Chromium autoscrolls a selection drag. */
async function selectIn(page: any, text: string): Promise<void> {
  // a fresh gesture: a mousedown on text already selected starts a drag of that text, not a selection
  await page.evaluate(() => { getSelection()!.removeAllRanges(); (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 0; });
  await frames(page, 2);
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
type Scene = { floatHidden: boolean; selected: string; bodyScrollTop: number; flex: string };
const scene = (page: any): Promise<Scene> => page.evaluate(() => ({
  floatHidden: (document.querySelector(".fc-float") as HTMLElement).hidden,
  selected: String(getSelection()),
  bodyScrollTop: (document.querySelector(".fileview-body") as HTMLElement).scrollTop,
  flex: getComputedStyle(document.querySelector(".fileview-main")!).flexDirection,
}));

test("in a browser, the real module and panel: the float shown on a selection hides when the body scrolls, in the list layout (380px) and the margin layout (900px); the selection stands", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [width, flex] of [[380, "column"], [900, "row"]] as const) {
      const cell = width + "px";
      const { page, errors } = await openViewer(browser, "pane", width, 600);
      await openPanel(page);
      await selectIn(page, "Paragraph 1:");
      let s = await scene(page);
      assert.equal(s.flex, flex, cell + ": the layout the width gives");
      assert.equal(s.floatHidden, false, cell + ": the float is offered beside the selection");
      assert.equal(s.selected, "Paragraph 1:", cell + ": over the selected words");
      assert.equal(s.bodyScrollTop, 0, cell + ": the body at its top");
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop += 300; });
      await frames(page, 2);
      s = await scene(page);
      assert.equal(s.floatHidden, true, cell + ": the float is hidden once the body scrolled (before the slice it stayed at its old screen position)");
      assert.equal(s.selected, "Paragraph 1:", cell + ": the selection itself stands");
      assert.equal(s.bodyScrollTop, 300, cell + ": the body moved");
      // a mouseup over the standing selection offers the button again: nothing was lost but the stale position
      await selectIn(page, "Paragraph 1:");
      s = await scene(page);
      assert.equal(s.floatHidden, false, cell + ": offered again on the next selection");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module and panel: in the margin layout, a scroll of the cards track that the lock mirrors onto the body hides the float too (the same scroll event; the passage has moved)", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 600);
    await openPanel(page);
    await selectIn(page, "Paragraph 1:");
    let s = await scene(page);
    assert.equal(s.flex, "row", "the margin layout");
    assert.equal(s.floatHidden, false);
    const trackRange: number = await page.evaluate(() => { const tr = document.querySelector(".fc-sec-cards") as HTMLElement; return tr.scrollHeight - tr.clientHeight; });
    assert.ok(trackRange >= 200, "the track scrolls (the lock sizes it to the body's range): " + trackRange);
    assert.equal(s.bodyScrollTop, 0, "the body at its top");
    await page.evaluate(() => { (document.querySelector(".fc-sec-cards") as HTMLElement).scrollTop = 200; });
    await frames(page, 3);
    s = await scene(page);
    assert.equal(s.bodyScrollTop, 200, "the lock wrote the track's position onto the body");
    assert.equal(s.floatHidden, true, "and the float went with the body's scroll event, as stated: the passage moved under the reader");
    assert.equal(s.selected, "Paragraph 1:", "the selection stands");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
