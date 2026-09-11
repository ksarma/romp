// The Comment offer follows a keyboard selection, in headless Chromium over the REAL viewer and panel (plans/markdown-viewer.md
// Slice 5, item 9; file-comments.ts onSelectionChange; real-viewer-leg.ts: the Files pane under styles.css and files-pane.css). The
// float rode the seam's mouseup alone, so after a drag offered it, Shift+ArrowLeft three times shrank the selection while the button
// stayed at its old position (the Slice 5 probe (i): the float shown at the drag's coordinates, the selection three words shorter).
// Now the panel hears the document's selectionchange: the shrunk selection moves the float to the shrunk selection's own rect, the
// same place the seam's mouseup would put it (showFloat's arithmetic over the selection's last range); a text-size step (A+) leaves
// the float hidden, since onRendered hides it on the reflow and the selection, whose nodes stand, fires no re-seat; Ctrl+A, whose
// anchor lands outside the body, hides a standing float and offers nothing for the page; and a drag still offers the button once, at
// mouseup. In the list layout (380 px) and the margin layout (900 px), as file-comments-float-scroll-browser.test.ts, whose scenes
// this leaves as they are (a scroll fires no selectionchange). In Chromium a keyboard selection needs an existing selection or
// caret browsing, so the drag comes first. The second test (the review's round 2): the press flag the listener reads is raised by the
// PRIMARY button alone and ends at a contextmenu too, since Chromium on Linux and macOS opens the native context menu on the right
// mousedown and the menu takes the release, so the page sees no mouseup, and the flag stood until the next left click while every
// keyboard change offered nothing; headless Chromium shows no menu, so the leg presses the right button and never releases it, the
// shape the page is left in. Legs await the DOM's own states and frames, never a timer. Skips LOUDLY without a playwright browser
// (CI installs none). Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames } from "./real-viewer-leg";

/** With the body at its top, drag across the first twelve characters of the paragraph starting with `text`, so the seam's mouseup
 *  offers the float (the float-scroll leg's gesture). */
async function selectIn(page: any, text: string): Promise<void> {
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
type Scene = { floatHidden: boolean; left: number; top: number; selected: string; expectedLeft: number; expectedTop: number; anchorInBody: boolean; flex: string };
/** The float's state and place (its inline left and top, in px), the selection's text, and where showFloat would put the button for
 *  the selection's last range now (its own arithmetic: beside the selection's end, above its line, kept on screen). */
const scene = (page: any): Promise<Scene> => page.evaluate(() => {
  const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!;
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const r = sel.rangeCount ? sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect() : null;
  return {
    floatHidden: f.hidden, left: parseFloat(f.style.left), top: parseFloat(f.style.top), selected: String(sel),
    expectedLeft: r ? Math.min(Math.max(8, r.right + 6), window.innerWidth - 90) : NaN, expectedTop: r ? Math.min(Math.max(8, r.top - 30), window.innerHeight - 34) : NaN,
    anchorInBody: !!sel.anchorNode && body.contains(sel.anchorNode),
    flex: getComputedStyle(document.querySelector(".fileview-main")!).flexDirection,
  };
});
/** Within the engine's rounding of an inline length (a hundredth of a pixel). */
const near = (a: number, b: number, what: string) => assert.ok(Math.abs(a - b) < 0.01, what + ": " + a + " against " + b);
/** Shift+ArrowLeft `n` times: the selection's focus steps back over the characters, the anchor standing. */
async function shrink(page: any, n: number): Promise<void> {
  await page.keyboard.down("Shift");
  for (let i = 0; i < n; i++) await page.keyboard.press("ArrowLeft");
  await page.keyboard.up("Shift");
}
/** Wait for `pred` in the page; on the timeout, fail with `what` and the scene as it stands, so the failing step names itself. */
async function waitFor(page: any, pred: () => boolean, what: string): Promise<void> {
  try { await page.waitForFunction(pred, null, { timeout: 5000 }); }
  catch (e) { throw new Error(what + " did not come about: " + JSON.stringify(await scene(page)) + " (" + String((e as Error).message).split("\n")[0] + ")"); }
}
/** The float shown beside the selection's last range as it stands now (the selectionchange task has run and the panel answered). */
const offeredAtSelection = (page: any, what: string): Promise<void> => waitFor(page, () => {
  const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!;
  if (f.hidden || !sel.rangeCount) return false;
  const r = sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect();
  return Math.abs(parseFloat(f.style.left) - Math.min(Math.max(8, r.right + 6), window.innerWidth - 90)) < 0.01;
}, what);

test("in a browser, the real module and panel: after a drag, Shift+ArrowLeft three times shrinks the selection and the float follows it to the shrunk selection's rect; a text-size step leaves it hidden; Ctrl+A hides it and offers nothing; in the list (380px) and margin (900px) layouts", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [width, flex] of [[380, "column"], [900, "row"]] as const) {
      const cell = width + "px";
      const { page, errors } = await openViewer(browser, "pane", width, 600);
      await openPanel(page);
      await selectIn(page, "Paragraph 1:");
      let s = await scene(page);
      assert.equal(s.flex, flex, cell + ": the layout the width gives");
      assert.equal(s.selected, "Paragraph 1:", cell + ": the drag selected twelve characters");
      assert.equal(s.floatHidden, false, cell + ": the drag's mouseup offers the float");
      near(s.left, s.expectedLeft, cell + ": beside the selection's end");
      const dragLeft = s.left;
      // the keyboard shrinks the selection: the float follows
      await shrink(page, 3);
      await waitFor(page, () => String(getSelection()) === "Paragraph", cell + ": the selection shrunk by three characters");
      await offeredAtSelection(page, cell + ": the float beside the shrunk selection");
      s = await scene(page);
      assert.equal(s.selected, "Paragraph", cell + ": three characters fewer at the end");
      assert.equal(s.floatHidden, false, cell + ": the float is shown for the keyboard's selection (before this slice it stood where the drag left it)");
      near(s.left, s.expectedLeft, cell + ": at the shrunk selection's own rect");
      near(s.top, s.expectedTop, cell + ": on its line");
      assert.ok(Math.abs(s.left - dragLeft) > 5, cell + ": and no longer where the drag put it (" + dragLeft + " against " + s.left + ")");
      // a text-size step: onRendered hides the float on the reflow, and nothing re-offers it (the selection's nodes stand, so the seam
      // re-seats nothing; a re-seat of the same ends would be no new offer either)
      const paints: number = await page.evaluate(() => (window as any).__paints);
      await page.click('.fileview-bar button[aria-label="Larger text"]');
      await page.waitForFunction((n: number) => (window as any).__paints > n, paints, { timeout: 10000 });
      await frames(page, 4);
      s = await scene(page);
      assert.equal(s.floatHidden, true, cell + ": a text-size step leaves the float hidden");
      assert.equal(s.selected, "Paragraph", cell + ": the selection itself stands through the reflow");
      await frames(page, 4);
      assert.equal((await scene(page)).floatHidden, true, cell + ": and it stays hidden");
      // a further keyboard change after the step offers again, beside the selection at its new size (the A+ button holds the focus
      // after its click, and the keys would go to it: the focus back on the document first, as a person's Escape or Tab away leaves it)
      await page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); });
      await shrink(page, 1);
      await waitFor(page, () => String(getSelection()) === "Paragrap", cell + ": the selection shrunk by one more");
      await offeredAtSelection(page, cell + ": the float beside the selection after the text-size step");
      s = await scene(page);
      assert.equal(s.floatHidden, false, cell + ": the next keyboard change offers the float again"); near(s.left, s.expectedLeft, cell + ": at the reflowed rect");
      // Ctrl+A: the selection spans the page, its anchor outside the body: the float goes and nothing is offered for the page
      await page.keyboard.press("Control+a");
      await waitFor(page, () => String(getSelection()).length > 100, cell + ": Ctrl+A selecting the page");
      await frames(page, 3);
      s = await scene(page);
      assert.equal(s.anchorInBody, false, cell + ": Ctrl+A puts the anchor outside the body");
      assert.equal(s.floatHidden, true, cell + ": the passage is no longer the selection: no float, and no offer for the whole page");
      // the drag still offers once, at mouseup (the first paragraph again: in the stacked layout the body is short, and the
      // second may sit under its fold)
      await selectIn(page, "Paragraph 1:");
      s = await scene(page);
      assert.deepEqual([s.floatHidden, s.selected], [false, "Paragraph 1:"], cell + ": a new drag offers the float beside its selection"); near(s.left, s.expectedLeft, cell + ": beside its end");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module and panel: a right-button press whose release the page never sees raises no press flag, so Shift+ArrowRight after it offers the float (before: nothing until the next left click); a primary press the browser ended with a contextmenu and no mouseup is over too", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 600);
    await openPanel(page);
    await page.evaluate(() => { const w = window as any; w.__ev = []; for (const type of ["mousedown", "mouseup", "contextmenu"]) document.addEventListener(type, (e) => w.__ev.push(type + ":" + (e as MouseEvent).button), true); });
    await selectIn(page, "Paragraph 1:");
    let s = await scene(page);
    assert.deepEqual([s.selected, s.floatHidden], ["Paragraph 1:", false], "the drag offers the float");
    // the right button pressed on the selection and never released (the native menu's release, on Linux and macOS): the float goes, as
    // for any press, and the selection stands
    const mid = await page.evaluate(() => { const r = getSelection()!.getRangeAt(0).getBoundingClientRect(); return { x: (r.left + r.right) / 2, y: r.top + r.height / 2 }; });
    await page.evaluate(() => { (window as any).__ev = []; });
    await page.mouse.move(mid.x, mid.y);
    await page.mouse.down({ button: "right" });
    await frames(page, 2);
    const events: string[] = await page.evaluate(() => (window as any).__ev);
    assert.ok(events.includes("mousedown:2") && !events.some((e) => e.startsWith("mouseup")), "the page saw the right mousedown and no mouseup: " + JSON.stringify(events));
    s = await scene(page);
    assert.equal(s.floatHidden, true, "a press of any button hides the float");
    assert.equal(s.selected, "Paragraph 1:", "the selection stands under the right press");
    // the keyboard widens the selection: offered (before: the flag raised by the right mousedown stood, and the change offered nothing)
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
    await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
    await waitFor(page, () => String(getSelection()) === "Paragraph 1: ", "the selection widened by one character");
    await offeredAtSelection(page, "the float beside the widened selection after a right press with no release");
    s = await scene(page);
    assert.equal(s.floatHidden, false, "offered"); near(s.left, s.expectedLeft, "beside the selection's end"); near(s.top, s.expectedTop, "on its line");
    await page.mouse.up({ button: "right" });
    await frames(page, 2);
    // a primary press the browser ended itself: the left button down on the selection (which stands: a press inside a selection collapses
    // it at the release, not before), then the contextmenu the browser fires when it opens its menu on the press (ctrl+click on macOS),
    // and no mouseup; the keyboard's next change offers (before: the flag stood)
    await page.evaluate(() => { (window as any).__ev = []; });
    await page.mouse.move(mid.x, mid.y);
    await page.mouse.down();
    await frames(page, 2);
    s = await scene(page);
    assert.equal(s.floatHidden, true, "the left press hides the float");
    assert.equal(s.selected, "Paragraph 1: ", "the selection stands under the press");
    await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, button: 0 })); });
    await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
    await waitFor(page, () => String(getSelection()) === "Paragraph 1: l", "the selection widened by one more");
    await offeredAtSelection(page, "the float beside the selection after a primary press the contextmenu ended");
    s = await scene(page);
    assert.equal(s.floatHidden, false, "offered after the contextmenu ended the press");
    assert.ok(!((await page.evaluate(() => (window as any).__ev)) as string[]).some((e) => e.startsWith("mouseup")), "and no mouseup reached the page meanwhile");
    await page.mouse.up();
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
