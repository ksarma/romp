// A remembered place inside a fold, in headless Chromium over the REAL viewer (plans/markdown-viewer.md Slice 6, item 3; the
// review's round 1). A reopen paints every fold as authored (the viewer's foldKeeper is per open, and the record carries no
// fold state), so a place the reader read inside a fold they had opened met a shut fold on the reopen: the block had no shown
// box, the seat fell to the record's numeric scrollTop, and that number, read over the OPEN fold's layout, landed thirty
// paragraphs past the reader's in a document the shut fold had made thousands of pixels shorter (Paragraph 55 shown as the
// remembered Paragraph 25, at 900 and 380 px, in the pane and the chat modal); a folded callout, one block in the anchor map,
// seated its summary at the edge and then took the reader's depth into the open content over a box a summary tall. Now
// landRemembered opens the folds above the remembered block's elements before the seat, as the offset landing and a `#` link
// open them (revealFragmentTarget), and a fold that is the block itself when the record's edge was inside it. Through
// real-viewer-leg.ts's page, at 900 and 380 px: an author's <details> opened and read inside (the reopen shows the fold open and
// the same paragraph at the same edge, the scrollTop back within a pixel), an Obsidian `[!note]-` callout the same, a
// record read in Raw inside the fold's rows and reopened under the Rendered preference (the fold opened, the block at the
// edge), and the control: a fold left shut at the leave stays shut and the block after it comes back exactly. The reopen is
// the same page's (closeFileView, then openFileView of the path: the module's memory hands the record back, as a Recent row
// would through opts.place). Before the fix: red at the first "after" read over a git archive of d91f0c19d. Skips LOUDLY
// without a playwright browser (CI installs none), as the other legs do. Synthetic values only: an invented report,
// /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, paintsReach, PARA, REPORT, SID } from "./real-viewer-leg";

const paras = (a: number, b: number): string => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
/** Paragraphs 1 to 10, an author's closed <details> holding 11 to 40, then 41 to 70. */
const DETAILS_NOTE = "# Report\n\n" + paras(1, 10) + "\n\n<details>\n<summary>Closed one</summary>\n\n" + paras(11, 40) + "\n\n</details>\n\n" + paras(41, 70) + "\n";
/** The same shape as an Obsidian folded callout: one blockquote block holding paragraphs 11 to 40. */
const CALLOUT_NOTE = "# Report\n\n" + paras(1, 10) + "\n\n> [!note]- Closed one\n" + Array.from({ length: 30 }, (_, i) => "> " + PARA(11 + i)).join("\n>\n") + "\n\n" + paras(41, 70) + "\n";

type Shown = { text: string; top: number; scrollTop: number; scrollHeight: number; foldOpen: boolean | null } | null;
/** In the page: the first SHOWN paragraph, heading or summary whose box ends below the body's top edge (checkVisibility, so a
 *  shut fold's laid-out content does not count), its first characters and its top from the edge; the fold's state beside it. */
function shownTop(): Shown {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const br = body.getBoundingClientRect();
  const d = document.querySelector(".fileview-md details");
  const foldOpen = d ? d.hasAttribute("open") : null;
  const els = Array.from(body.querySelectorAll(".fileview-md p, .fileview-md h1, .fileview-md summary")) as HTMLElement[];
  for (const e of els) {
    if (typeof e.checkVisibility === "function" && !e.checkVisibility()) continue;
    const r = e.getBoundingClientRect();
    if (r.bottom > br.top + 0.5) return { text: (e.textContent || "").trim().slice(0, 12), top: Math.round((r.top - br.top) * 10) / 10, scrollTop: body.scrollTop, scrollHeight: body.scrollHeight, foldOpen };
  }
  return null;
}
/** In the page: scroll the body so the paragraph starting with `text` has its top `above` px above the body's edge. */
function putAbove([text, above]: [string, number]): void {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const p = (Array.from(body.querySelectorAll(".fileview-md p")) as HTMLElement[]).find((e) => (e.textContent || "").indexOf(text) === 0)!;
  body.scrollTop += p.getBoundingClientRect().top - body.getBoundingClientRect().top + above;
}
const read = (page: any): Promise<Shown> => page.evaluate(shownTop);
/** Close the viewer and open the same path again in the same page (the module's memory hands the record back), then wait for
 *  the reopen's paint. `raw` false switches the stored preference to Rendered first (a person's Rendered choice on the reopen). */
async function reopen(page: any, opts: { rendered?: boolean } = {}): Promise<void> {
  const before: number = await page.evaluate(() => (window as any).__paints);
  await page.evaluate(() => { (window as any).FV.closeFileView(); });
  if (opts.rendered) await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "rendered" })); });
  await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
  await paintsReach(page, before + 1);
  await frames(page, 3);
}
const near = (a: number, b: number, what: string, tol = 1) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);

test("in a browser, at 900 and 380 px: a paragraph read inside an author's <details> the reader had opened comes back at the same edge on the reopen, the fold open and the scrollTop within a pixel (before the fix: the fold shut and a paragraph thirty past the reader's at the edge); the same for a folded callout; a fold left shut stays shut and the block after it comes back exactly", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [w, h] of [[900, 520], [380, 520]] as Array<[number, number]>) {
      const what = "pane " + w + "px";
      // the author's <details>: opened by a click on its summary, Paragraph 25 put 20 px above the edge
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: DETAILS_NOTE } });
        await page.click(".fileview-md details > summary");
        await frames(page, 2);
        await page.evaluate(putAbove, ["Paragraph 25", 20]);
        await frames(page, 2);
        const before = (await read(page))!;
        assert.equal(before.text, "Paragraph 25", what + ": the scene starts with Paragraph 25 at the edge inside the open fold");
        assert.equal(before.foldOpen, true, what + ": the fold is open");
        await reopen(page);
        const after = (await read(page))!;
        assert.equal(after.foldOpen, true, what + ": the reopen opened the fold the remembered block sits in (before the fix it painted shut)");
        assert.equal(after.text, "Paragraph 25", what + ": the remembered paragraph is at the edge again (before the fix: Paragraph 55, the numeric scrollTop over the shorter document)");
        near(after.top, before.top, what + ": at its height");
        near(after.scrollTop, before.scrollTop, what + ": the scrollTop is back (the same layout at the same width)");
        assert.deepEqual(errors, [], what + ": no page errors");
        await page.close();
      }
      // the folded callout: one block in the anchor map, so the seat found its box (the shut summary) and applied the reader's
      // depth into the open content over a box a summary tall
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: CALLOUT_NOTE } });
        assert.equal(await page.evaluate(() => !!document.querySelector(".fileview-md details.md-callout")), true, what + ": the callout rendered as a folded block");
        await page.click(".fileview-md details.md-callout > summary");
        await frames(page, 2);
        await page.evaluate(putAbove, ["Paragraph 25", 20]);
        await frames(page, 2);
        const before = (await read(page))!;
        assert.equal(before.text, "Paragraph 25", what + " (callout): the scene starts with Paragraph 25 at the edge inside the open callout");
        await reopen(page);
        const after = (await read(page))!;
        assert.equal(after.foldOpen, true, what + " (callout): the reopen opened the callout");
        assert.equal(after.text, "Paragraph 25", what + " (callout): the remembered paragraph is at the edge again (before the fix: the depth into the open content applied over the shut summary's box)");
        near(after.top, before.top, what + " (callout): at its height");
        assert.deepEqual(errors, [], what + " (callout): no page errors");
        await page.close();
      }
      // the control: the fold left shut, the block after it at the edge; the reopen changes nothing about the fold
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: DETAILS_NOTE } });
        await page.evaluate(putAbove, ["Paragraph 41", 12]);
        await frames(page, 2);
        const before = (await read(page))!;
        assert.equal(before.text, "Paragraph 41", what + " (control): Paragraph 41, the block after the shut fold, at the edge");
        assert.equal(before.foldOpen, false, what + " (control): the fold is shut");
        await reopen(page);
        const after = (await read(page))!;
        assert.equal(after.foldOpen, false, what + " (control): a fold the reader never opened stays shut on the reopen");
        assert.equal(after.text, "Paragraph 41", what + " (control): the block is back at the edge");
        near(after.top, before.top, what + " (control): at its height");
        near(after.scrollTop, before.scrollTop, what + " (control): the scrollTop is back");
        assert.deepEqual(errors, [], what + " (control): no page errors");
        await page.close();
      }
    }
  });
});

test("in a browser, at 900 px: a place read in the Raw view inside the fold's rows, reopened under the Rendered preference, opens the fold and puts the remembered block at the edge (the record's depth is the Raw view's, so the block's top is what is known)", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: DETAILS_NOTE }, raw: true });
    // the Raw row of Paragraph 25 (inside the fold's source) 5 px above the edge
    await page.evaluate(() => {
      const body = document.querySelector(".fileview-body") as HTMLElement;
      const row = (Array.from(body.querySelectorAll("code.hljs .fv-cl")) as HTMLElement[]).find((e) => (e.textContent || "").indexOf("Paragraph 25") === 0)!;
      body.scrollTop += row.getBoundingClientRect().top - body.getBoundingClientRect().top + 5;
    });
    await frames(page, 2);
    const rowAtEdge: string = await page.evaluate(() => {
      const body = document.querySelector(".fileview-body") as HTMLElement; const br = body.getBoundingClientRect();
      const rows = Array.from(body.querySelectorAll("code.hljs .fv-cl")) as HTMLElement[];
      const r = rows.find((e) => e.getBoundingClientRect().bottom > br.top + 0.5)!;
      return (r.textContent || "").trim().slice(0, 12);
    });
    assert.equal(rowAtEdge, "Paragraph 25", "the scene starts with Paragraph 25's row at the edge in Raw");
    await reopen(page, { rendered: true });
    const after = (await read(page))!;
    assert.equal(await page.evaluate(() => !!document.querySelector(".fileview-md > p")), true, "the reopen painted the Rendered view");
    assert.equal(after.foldOpen, true, "the fold holding the remembered block was opened (before the fix: shut, and Paragraph 54 at the edge)");
    assert.equal(after.text, "Paragraph 25", "the remembered block is at the edge");
    assert.ok(after.top <= 0.5 && after.top >= -1, "its top at the edge (the depth is the other view's and is not applied): read " + after.top);
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});
