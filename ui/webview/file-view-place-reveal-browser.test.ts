// A scroll made on purpose in the same task as a change of the body's width is kept, not undone by the width reflow's
// seat, in headless Chromium over the REAL module (plans/markdown-viewer.md, Slice 2; reader-place.ts; the Slice 2
// review). The panel's reveal is the case a person meets: with the Comments panel closed, a click on a highlight opens
// the panel and centers the mark (file-comments.ts fcopen: openPanel, then showCard), so the aside mounts and the body
// scrolls in ONE task. The scroll-time read used to skip every scroll under a body width it had not seen (taking it for
// the reflow's own clamp), so the ResizeObserver's repaint seated the place read BEFORE the click and scrolled the body
// back one frame later: at 900px the mark was centered at 280 then sat at 181, with the pre-click paragraph on top again
// and a mark lower in the viewport pushed off the screen with its card; the reader saw the text jump twice. Now only the
// browser's own adjustments are skipped, each by its signature: the clamp (a scroll that lands the body at its end coming
// from above it) and the anchoring adjustment (the block the last read named with its top edge where it stood; round 2 of
// the review: read as the place, it held the reader's depth in pixels and the repaint moved nothing, so each open of the
// panel halved the depth the close had kept as a fraction; file-view-place-browser.test.ts drives that). Every other
// scroll under the new width is read, so the repaint holds the reveal. The second test drives the generic form (any
// scroll of the body plus a width change in one task) and the clamp the read still skips (the aside closing on a reader
// deep in the narrow body). Legs await frames and paint counts, never a timer. Skips LOUDLY without a playwright browser
// (CI installs none), as the other browser legs do. Synthetic values only: an invented report, /repo/notes-api paths, the
// placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, closePanel, pageHtml, frames, paintsReach, topBlock, putAtTop, LONG, REPORT, SID, MT, ORIGIN, STATUS, type Mode, type Opened } from "./real-viewer-leg";

const T0 = 1757145600000;
/** One comment anchored on paragraph `n`'s first words (the shape the kernel's status carries). */
const commentOn = (n: number) => ({ id: `${T0 + 1}-${n}`, author: "you", ts: T0 + 1, body: `Note on paragraph ${n}.`, anchor: { quote: `Paragraph ${n}: lorem ipsum`, prefix: "", suffix: " dolor sit amet" }, replies: [], resolved: false });

/** The report open with `comment` in the status the poster answers, so its highlight is painted with the panel CLOSED. */
async function openWithComment(browser: any, mode: Mode, width: number, height: number, comment: ReturnType<typeof commentOn>): Promise<Opened> {
  const page = await browser.newPage({ viewport: { width, height } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml(mode, { [REPORT]: LONG }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  const status = { ...STATUS, store: { ...STATUS.store, comments: [comment] } };
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await page.waitForFunction((id: string) => !!document.querySelector('.fileview-body .fc-hl[data-id="' + id + '"]'), comment.id, { timeout: 10000 });
  await frames(page, 2);
  return { page, errors };
}

type MarkAt = { scrollTop: number; center: number; markTop: number; aside: boolean; bodyWidth: number };
/** The mark's top edge measured from the body's top, the body's vertical center, and whether the aside is up. */
const markAt = (page: any, id: string): Promise<MarkAt> => page.evaluate((id: string) => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const mark = document.querySelector('.fileview-body .fc-hl[data-id="' + id + '"]') as HTMLElement;
  return { scrollTop: body.scrollTop, center: body.clientHeight / 2, markTop: mark.getBoundingClientRect().top - body.getBoundingClientRect().top, aside: !!document.querySelector(".fileview-aside"), bodyWidth: body.clientWidth };
}, id);

test("in a browser, the real module: a click on a highlight with the panel closed opens the panel and centers the mark, and the width reflow's repaint leaves it centered (before: the body was scrolled back to the pre-click place one frame later), pane 900 and chat 1000", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width] of [["pane", 900], ["chat", 1000]] as const) {
      const cell = `${mode} ${width}px`;
      const c = commentOn(70);
      const { page, errors } = await openWithComment(browser, mode, width, 600, c);
      await putAtTop(page, "Paragraph 68:");
      await frames(page, 3);                                  // the scroll-time read: the place is paragraph 68, under the closed panel's width
      const before = (await topBlock(page))!;
      assert.equal(before.text, "Paragraph 68:", cell + ": the scene starts with paragraph 68 at the top");
      const w0 = (await markAt(page, c.id)).bodyWidth;
      const paints: number = await page.evaluate(() => (window as any).__paints);
      // the click, and the state it leaves in the SAME task: the aside mounted, the body narrowed, the mark at the body's center
      const right: MarkAt = await page.evaluate((id: string) => {
        (document.querySelector('.fileview-body .fc-hl[data-id="' + id + '"]') as HTMLElement).click();
        const body = document.querySelector(".fileview-body") as HTMLElement;
        const mark = document.querySelector('.fileview-body .fc-hl[data-id="' + id + '"]') as HTMLElement;
        return { scrollTop: body.scrollTop, center: body.clientHeight / 2, markTop: mark.getBoundingClientRect().top - body.getBoundingClientRect().top, aside: !!document.querySelector(".fileview-aside"), bodyWidth: body.clientWidth };
      }, c.id);
      assert.ok(right.aside, cell + ": the click opened the panel");
      assert.ok(right.bodyWidth < w0 - 200, cell + `: the body narrowed for the aside (${w0} to ${right.bodyWidth})`);
      assert.ok(Math.abs(right.markTop - right.center) <= 2, cell + `: the reveal centered the mark (mark at ${right.markTop}, center ${right.center})`);
      // the width reflow's repaint (the ResizeObserver's frame), then two more frames: the mark is still centered
      await paintsReach(page, paints + 1);
      await frames(page, 3);
      const settled = await markAt(page, c.id);
      assert.ok(Math.abs(settled.markTop - settled.center) <= 2, cell + `: the mark is still centered after the reflow's repaint (mark at ${settled.markTop}, center ${settled.center}; before the fix it sat at 181 in the pane, 140 in the chat, the pre-click paragraph on top again)`);
      assert.ok(Math.abs(settled.scrollTop - right.scrollTop) <= 2, cell + `: the body stayed where the reveal put it (${right.scrollTop} then ${settled.scrollTop})`);
      assert.notEqual((await topBlock(page))!.text, "Paragraph 68:", cell + ": the pre-click paragraph is not back on top");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: any scroll of the body in the same task as a width change is kept by the reflow's repaint (the generic form of the reveal), and the clamp of a body scrolled past its new end is still not read as the reader's move", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 600);
    await putAtTop(page, "Paragraph 40:");
    await frames(page, 3);
    assert.equal((await topBlock(page))!.text, "Paragraph 40:");
    let paints: number = await page.evaluate(() => (window as any).__paints);
    // one task: the body scrolled to paragraph 70, then the page narrowed under the viewer
    const w1: number = await page.evaluate(() => { (window as any).putAtTop("Paragraph 70:"); document.body.style.width = "700px"; return document.querySelector(".fileview-body")!.clientWidth; });
    assert.ok(w1 < 800, `the body narrowed in the task (${w1})`);
    await paintsReach(page, paints + 1);
    await frames(page, 3);
    let now = (await topBlock(page))!;
    assert.equal(now.text, "Paragraph 70:", "the block scrolled to in the same task as the width change is the one kept (before the fix: paragraph 40, the place read before the scroll)");
    assert.ok(Math.abs(now.top) <= 1.5, `at the top edge (${now.top})`);
    // the clamp, the one scroll under a new width the read still skips. Chromium's anchoring holds through a page-width
    // change (above), so the clamp needs the case where it does not: the Comments aside closing, whose layout pass changes
    // the body's padding (a suppression trigger for anchoring). The reader deep in the narrow body beside the aside
    // (paragraph 86 at the top, a scrollTop past the wider layout's end), the aside closed: the content gets shorter than the
    // scrollTop and the browser lands the body at its end, paragraph 89 on top there; the repaint seats the block read before
    // the width moved, which the wider layout still reaches. Read as the reader's move, the clamp's landing would be seated
    // instead (paragraph 89 on top; the no-gate variant of the read shows exactly that)
    await page.evaluate(() => { document.body.style.width = ""; });
    await frames(page, 3);
    await page.evaluate(() => { const b = document.querySelector(".fileview-body")!; (window as any).__wideMax = b.scrollHeight - b.clientHeight; });
    paints = await page.evaluate(() => (window as any).__paints);
    await openPanel(page);
    await paintsReach(page, paints + 1);
    await putAtTop(page, "Paragraph 86:");
    await frames(page, 3);
    const deep = (await topBlock(page))!;
    assert.equal(deep.text, "Paragraph 86:", "the narrow body beside the aside reaches paragraph 86 at its top");
    const maxWide: number = await page.evaluate(() => (window as any).__wideMax);
    paints = await page.evaluate(() => (window as any).__paints);
    await closePanel(page);
    await paintsReach(page, paints + 1);
    await frames(page, 3);
    now = (await topBlock(page))!;
    assert.ok(deep.scrollTop > maxWide, `the scene is a clamp: the narrow scrollTop ${deep.scrollTop} is past the wide layout's end ${maxWide}`);
    assert.equal(now.text, "Paragraph 86:", "paragraph 86 is the top block again after the aside closed (the clamp's landing, paragraph 89, was not taken for the reader's place)");
    assert.ok(Math.abs(now.top) <= 1.5, `at the top edge (${now.top})`);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
