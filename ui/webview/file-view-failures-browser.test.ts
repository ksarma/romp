// Every failure says what happened, in headless Chromium over the REAL viewer (plans/markdown-viewer.md, Slice 7: items 3, 5
// and 6 share this leg; real-viewer-leg.ts serves the page, its fetch stub answering a path missing from window.__docs with
// a 404 whose body is "no such file: " + the path, as the kernel's names the resolved path). Item 3's scene: a reload whose
// fetch fails is a paint the seam hears. Before Slice 7 the fetch chain's catch painted the pane and fired no hook, so the
// Comments panel, waiting on the reload its poll had asked for, kept its loader up until its 15 s deadline; now the catch
// fires the hooks AFTER the pane's swap (window.__paints grows by one) with the seam's error() answering the pane's words,
// while text() and mtimeNs() keep the last landing's and mode() its view. The file back under a new mtime, the landing
// paints again and error() is null. The wait is for the paint count (paintsReach), the event the panel keys on, never a
// timer. The panel scene (openPanel, a status whose mtime moved, the loader yielding to the "bytes" row within two frames
// of the pane's paint) joins this leg once the panel reads error() at its paint (unit C's commit of the slice); until then
// the leg holds the seam-side assertions alone. Skips LOUDLY without a playwright browser (CI installs none), as the other
// legs do. Before Slice 7: __seam.error was not a function (red over a git archive of the base at the leg's first read
// of the seam, before the reload) and __paints did not move after a failed reload. Synthetic values only: an invented
// report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, paintsReach, LONG, LONG2, REPORT, MT, MT2 } from "./real-viewer-leg";

type Seen = { paints: number; error: string | null; text: string | null; mt: string; mode: string; pane: string | null; paneInBody: boolean; mdBox: boolean };
/** What the page shows and what the seam says: the paint count, error(), text(), mtimeNs(), mode(), the pane's text when one
 *  is in the body and whether it is the body's own child, and whether the Rendered box stands. */
const seen = (page: any): Promise<Seen> => page.evaluate(() => {
  const w = window as any;
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const pane = body.querySelector(".fileview-err");
  return {
    paints: w.__paints, error: w.__seam.error(), text: w.__seam.text(), mt: w.__seam.mtimeNs(), mode: w.__seam.mode(),
    pane: pane ? pane.textContent : null, paneInBody: !!pane && pane.parentElement === body, mdBox: !!body.querySelector(".fileview-md"),
  };
});

test("in a browser: a failed reload (the file gone from the kernel's table) fires the seam's hooks once after the pane's paint: __paints grows by one, __seam.error() is the stub's 404 words, the pane in the body shows the same words, text() and mtimeNs() keep the last landing's and mode() its view; the file back under a new mtime, the landing paints again and error() is null", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700);
    const before = await seen(page);
    assert.equal(before.error, null, "a text view: no pane"); assert.equal(before.mt, MT); assert.equal(before.mode, "rendered");
    await page.evaluate((p: string) => { const w = window as any; delete w.__docs[p]; w.__seam.reload(); }, REPORT);   // a session removed the file; the panel's poll asks a reload
    await paintsReach(page, before.paints + 1);   // the pane's paint, the event the panel keys on (before Slice 7: never reached)
    await frames(page, 2);
    const failed = await seen(page);
    assert.equal(failed.paints, before.paints + 1, "one paint for the failure (before Slice 7: none, and the Comments panel's loader stood until its 15 s deadline)");
    assert.equal(failed.error, "no such file: " + REPORT, "error() is the stub's 404 words, the pane's own");
    assert.equal(failed.pane, failed.error, "the pane shows the same words (the message names the path, so no hint; a 404 offers no Download)");
    assert.ok(failed.paneInBody, "the pane is the body's child, in place of the note"); assert.equal(failed.mdBox, false, "the note left with the swap");
    assert.equal(failed.text, LONG, "text() still answers the last landing's text"); assert.equal(failed.mt, MT, "under its mtime: a failed landing lends none");
    assert.equal(failed.mode, "rendered", "mode() is the view's word and unchanged; error() is the pane's");
    // the file back under a new mtime (a session wrote it again): the landing's text paint clears the record and fires the hooks
    await page.evaluate(([p, t, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = t; w.__mtime = m; w.__seam.reload(); }, [REPORT, LONG2, MT2]);
    await paintsReach(page, before.paints + 2);
    await frames(page, 2);
    const back = await seen(page);
    assert.equal(back.paints, before.paints + 2, "the landing's paint");
    assert.equal(back.error, null, "a text view again: error() null"); assert.equal(back.pane, null, "and no pane");
    assert.equal(back.mdBox, true, "the note is back"); assert.equal(back.mt, MT2); assert.equal(back.text, LONG2);
    assert.deepEqual(errors, [], "no uncaught page error");
    await page.close();
  });
});
