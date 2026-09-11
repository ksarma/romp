// The URL viewer's Rendered/Raw round trip from the end of the note comes back to the same block at the same height
// (review of Slice 3 of plans/markdown-viewer.md, round 3, 2026-09-09). Round 1 gave the local viewer (openFileView) a
// held place: a seat the browser CLAMPS (the view swapped in is shorter than the one the place was read in, and the body
// stands at its end) keeps the place it was given instead of reading the body back, so the swap back seats the reader's
// passage and not the block the clamp showed (reader-place.ts seatPlaceOutcome; file-view-place-blocks-browser.test.ts's
// bottom scene). openUrlView, the same viewer for a same-origin .md link, read and seated through the plain seatPlace and
// had no hold, so from the end of the TALLER view (Rendered since this slice) its round trip came back a paragraph early or
// tens of pixels off (chat 900x600: Paragraph 94 at -1.9 came back as Paragraph 93 at -49.6; the pane at 900: 35px off)
// where the local viewer in the same cells returned exactly. The URL viewer keeps the held place now, as the local one
// does. Three cells over the real viewer (real-viewer-leg.ts), the URL viewer opened on the hundred-paragraph note: the
// chat modal and the pane from the end of the Rendered view (the clamped direction: the leg checks the Raw seat WAS
// clamped, so it is the hold that brings the reader back), and the chat modal from the end of the Raw view (the shorter
// view, no clamp; exact before the fix too, pinned so the hold costs the other direction nothing). The top block is named
// by text and position, its edge within 1.5px, and the scrollTop pin is EXACT, as the local viewer's bottom scene pins it.
// Skips LOUDLY without a playwright browser (CI installs none), as the other legs do. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, topBlock, putAtTop, LONG, ORIGIN, type Mode } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
const click = async (page: any, label: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 3); };
const toEnd = async (page: any) => { await page.evaluate(() => { const b = document.querySelector(".fileview-body")!; b.scrollTop = b.scrollHeight; }); await frames(page, 3); };
/** Whether the body stands at its end (the seat's write was clamped there). */
const atEnd = (page: any): Promise<boolean> => page.evaluate(() => { const b = document.querySelector(".fileview-body")!; return b.scrollTop >= b.scrollHeight - b.clientHeight - 1; });
/** The index of the top block among the view's blocks (a blank Raw row's text matches every blank row). */
const topIndex = (page: any): Promise<number> => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  const sel = document.querySelector(".fileview-md") ? ".fileview-md > *" : "code.hljs .fv-cl";
  return Array.from(body.querySelectorAll(sel)).findIndex((e) => e.getBoundingClientRect().bottom > br.top + 0.5);
});
const URL_PATH = "/docs/report.md";

test("in a browser, the URL viewer: the Rendered/Raw round trip from the end of the note comes back to the same block at the same height, chat and pane, from the taller view (clamped) and the shorter", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, raw] of [["chat", false], ["pane", false], ["chat", true]] as [Mode, boolean][]) {
      const cell = `URL viewer, bottom, ${mode}, from ${raw ? "Raw" : "Rendered"}`;
      const { page, errors } = await openViewer(browser, mode, 900, 600, { raw, url: URL_PATH, urls: { [ORIGIN + URL_PATH]: LONG } });
      await toEnd(page);
      const before = (await topBlock(page))!; const beforeAt = await topIndex(page);
      assert.equal(before.view, raw ? "raw" : "rendered", cell + ": the scene opens in the view named");
      assert.ok(beforeAt >= 0, cell + ": a top block is found");
      await click(page, raw ? "Rendered" : "Raw");
      const mid = (await topBlock(page))!;
      assert.equal(mid.view, raw ? "rendered" : "raw", cell + ": the other view is up");
      if (!raw) assert.equal(await atEnd(page), true, cell + ": the seat into the shorter view was clamped at its end (the case the held place exists for)");
      await click(page, raw ? "Raw" : "Rendered");
      const after = (await topBlock(page))!; const afterAt = await topIndex(page);
      assert.equal(after.text, before.text, cell + ": the same top block (the Slice 3 tree: Paragraph 93 for 94 on the chat from Rendered)");
      assert.equal(afterAt, beforeAt, cell + ": the same top block by position");
      near(after.top, before.top, cell + ": at the same height (the Slice 3 tree: 27 to 81px off from Rendered)");
      assert.equal(after.scrollTop, before.scrollTop, cell + ": the same scrollTop");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

// A text-size step is a reflow the reader did not ask to lose their place over: the URL viewer's textSizeControl call brackets the
// apply with its own keptPlace and seat, as the local viewer's does (the 2026-09-10 fold of the offer that landed the control in
// both viewers: upstream's URL viewer steps with no place keeping). Before the bracket, A+ at a passage in the middle of the note
// left scrollTop where it was while the text above the passage grew (the root's inline padding moves with the ch, so the browser's
// own scroll anchoring stands down), and the top block was an earlier paragraph; A- then brought the layout back and the reader
// with it, so the case pins BOTH stops: the top block after A+ and after A-. Two cells, the chat modal and the pane.
const stepSize = async (page: any, larger: boolean) => { await page.locator('#romp-fileview button[aria-label="' + (larger ? "Larger" : "Smaller") + ' text"]').click(); await frames(page, 3); };
const sizeOf = (page: any): Promise<string | undefined> => page.evaluate(() => (document.querySelector(".fileview") as HTMLElement).dataset.fvText);

test("in a browser, the URL viewer: the reader scrolled to a passage keeps its top block across A+ and then A-, chat and pane, as the local viewer does", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["chat", "pane"] as Mode[]) {
      const cell = `URL viewer, a passage, ${mode}`;
      const { page, errors } = await openViewer(browser, mode, 900, 600, { url: URL_PATH, urls: { [ORIGIN + URL_PATH]: LONG } });
      await putAtTop(page, "Paragraph 40:");
      await frames(page, 3);
      const before = (await topBlock(page))!; const beforeAt = await topIndex(page);
      assert.equal(before.view, "rendered", cell + ": the scene opens rendered");
      assert.ok(before.text.startsWith("Paragraph 40"), cell + ": the passage is at the top: " + before.text);
      assert.equal(await sizeOf(page), "100", cell + ": the default size");
      await stepSize(page, true);
      assert.equal(await sizeOf(page), "115", cell + ": one step up");
      const up = (await topBlock(page))!;
      assert.equal(up.text, before.text, cell + ": after A+ the passage's top block is still the one seated (the bracket read the place before the text grew and seated it after)");
      assert.equal(await topIndex(page), beforeAt, cell + ": ...by position too");
      await stepSize(page, false);
      assert.equal(await sizeOf(page), "100", cell + ": and back to the default");
      const after = (await topBlock(page))!; const afterAt = await topIndex(page);
      assert.equal(after.text, before.text, cell + ": after A- the same top block");
      assert.equal(afterAt, beforeAt, cell + ": the same top block by position");
      near(after.top, before.top, cell + ": at the same height");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});
