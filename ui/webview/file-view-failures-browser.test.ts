// Every failure says what happened, in headless Chromium over the REAL viewer (plans/markdown-viewer.md, Slice 7: items 3, 5
// and 6 share this leg; real-viewer-leg.ts serves the page, its fetch stub answering a path missing from window.__docs with
// a 404 whose body is "no such file: " + the path, as the kernel's names the resolved path, and a text answer with the
// X-Romp-Text-Utf8 a test put in window.__utf8 for the path, "1" otherwise). Item 3's scene: a reload whose
// fetch fails is a paint the seam hears. Before Slice 7 the fetch chain's catch painted the pane and fired no hook, so the
// Comments panel, waiting on the reload its poll had asked for, kept its loader up until its 15 s deadline; now the catch
// fires the hooks AFTER the pane's swap (window.__paints grows by one) with the seam's error() answering the pane's words,
// while text() and mtimeNs() keep the last landing's and mode() its view. The file back under a new mtime, the landing
// paints again and error() is null. The wait is for the paint count (paintsReach), the event the panel keys on, never a
// timer. The panel scene (openPanel, a status whose mtime moved, the loader yielding to the "bytes" row within two frames
// of the pane's paint) joins this leg once the panel reads error() at its paint (unit C's commit of the slice); until then
// the leg holds the seam-side assertions alone. Skips LOUDLY without a playwright browser (CI installs none), as the other
// legs do. Before Slice 7: __seam.error was not a function (red over a git archive of the base at the leg's first read
// of the seam, before the reload) and __paints did not move after a failed reload. Item 5's scene: a file the kernel
// decoded as Latin-1 (its text answer wearing X-Romp-Text-Utf8 "0") says why Edit is off in the note bar, LATIN1_NOTICE read
// off the source, the card's child above the body row (the notebar leg's reading: in the card, above the row, on screen at
// scrollTop 400), no button, the Edit button hidden and the text painted with error() null; the changed-on-disk bar takes the
// row when a window focus finds a moved mtime and its Reload's landing brings the line back over the new text; an open at a
// line past the end shows the past-the-end notice and not the line (the raise precedes landTarget), and a reload, which has
// no target, brings the line back. Before item 5: no bar at all over such a file (red at the scene's first read over a git
// archive of the branch before it, whose real-viewer-leg has no utf8 table either). Synthetic values only: an invented
// report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, frames, paintsReach, LONG, LONG2, REPORT, MT, MT2, UI } from "./real-viewer-leg";

/** The Latin-1 line's exported sentence, read off the viewer's source (contract C5), so the leg follows the constant. */
const LATIN1_NOTICE = (/^export const LATIN1_NOTICE = "([^"]+)";$/m.exec(fs.readFileSync(path.join(UI, "file-view.ts"), "utf8")) || [])[1];

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

type Bar = { present: boolean; words: string; parent: string; before: string | null; buttons: number; inCard: boolean; aboveRow: boolean; inViewport: boolean; bodyScrollTop: number; edit: boolean | null; rows: number; paints: number; error: string | null; text: string | null; bars: number };
/** The note bar as laid out (file-view-notebar-browser.test.ts's reading): its own words (text nodes, without a button's label),
 *  its parent and next sibling, its box against the card's, the body row's and the viewport; with the Edit button's hidden bit,
 *  the painted rows or blocks, the paint count, the seam's error() and text(), and how many bars the card holds. */
const readBar = (page: any): Promise<Bar> => page.evaluate(() => {
  const w = window as any;
  const bar = document.getElementById("fileview-save-err");
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const edit = (Array.from(document.querySelectorAll("#romp-fileview .fileview-acts button")) as HTMLButtonElement[]).find((x) => x.textContent === "Edit");
  const base = {
    bodyScrollTop: body.scrollTop, edit: edit ? edit.hidden : null, rows: body.querySelectorAll(".fileview-md > p, code.hljs .fv-cl").length,
    paints: w.__paints, error: w.__seam.error(), text: w.__seam.text(), bars: document.querySelectorAll("#fileview-save-err, .fileview > .fileview-err").length,
  };
  if (!bar) return { present: false, words: "", parent: "", before: null, buttons: 0, inCard: false, aboveRow: false, inViewport: false, ...base };
  const r = bar.getBoundingClientRect(), card = document.querySelector(".fileview")!.getBoundingClientRect(), main = document.querySelector(".fileview-main")!.getBoundingClientRect();
  return {
    present: true, words: Array.from(bar.childNodes).filter((x) => x.nodeType === 3).map((x) => x.textContent || "").join(""),
    parent: (bar.parentElement as HTMLElement).className, before: bar.nextElementSibling ? (bar.nextElementSibling as HTMLElement).className : null,
    buttons: bar.querySelectorAll("button").length,
    inCard: r.top >= card.top - 0.5 && r.bottom <= card.bottom + 0.5 && r.left >= card.left - 0.5 && r.right <= card.right + 0.5,
    aboveRow: r.bottom <= main.top + 0.5 && r.height > 0,
    inViewport: r.top >= 0 && r.bottom <= innerHeight && r.height > 0,
    ...base,
  };
});

test("in a browser: a Latin-1 file says why Edit is off (Slice 7, item 5): opened over a text answer wearing X-Romp-Text-Utf8 \"0\", the note bar reads LATIN1_NOTICE above the body row, in the card and on screen at scrollTop 400, with no button, the Edit button hidden and the text painted (error() null); a window focus over a moved mtime raises the changed-on-disk bar in its place and its Reload's landing brings the line back over the new text; an open at a line past the end shows the past-the-end notice and not the line, and a reload brings the line back; pane and chat", { timeout: 180000 }, async (t) => {
  assert.ok(LATIN1_NOTICE, "the constant is read off the source");
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as const) {
      const { page, errors } = await openViewer(browser, mode, 700, 600, { utf8: { [REPORT]: "0" } });
      let b = await readBar(page);
      assert.ok(b.present, mode + ": the line is up (before item 5: no bar, and Edit hidden with no word)");
      assert.equal(b.words, LATIN1_NOTICE, mode + ": the exported sentence, alone");
      assert.equal(b.parent, "fileview", mode + ": a child of the card, not of the body");
      assert.equal(b.before, "fileview-main", mode + ": right above the body row");
      assert.equal(b.buttons, 0, mode + ": no button in the line"); assert.equal(b.bars, 1, mode + ": one bar in the card");
      assert.ok(b.aboveRow && b.inCard && b.inViewport, mode + ": its box sits above the row, inside the card, on screen");
      assert.equal(b.edit, true, mode + ": the Edit button is hidden (the gate's verdict, unchanged)");
      assert.ok(b.rows > 0, mode + ": the text is painted"); assert.equal(b.text, LONG, mode + ": text() answers it"); assert.equal(b.error, null, mode + ": error() null: a notice, not a pane");
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 400; });
      await frames(page, 2);
      b = await readBar(page);
      assert.ok(b.present && b.inViewport && b.aboveRow && b.bodyScrollTop === 400, mode + ": at scrollTop 400 the line is still on screen above the row");
      // the changed-on-disk bar takes the row (raised later, the one-bar rule); its Reload's landing drops it and the line returns
      const paints = b.paints;
      await page.evaluate(([p, text, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = text; w.__mtime = m; window.dispatchEvent(new Event("focus")); }, [REPORT, LONG2, MT2]);
      await page.waitForFunction(() => { const n = document.getElementById("fileview-save-err"); return !!n && !!n.querySelector("button"); }, null, { timeout: 5000 });
      await frames(page, 2);
      b = await readBar(page);
      assert.equal(b.words, "Changed on disk.", mode + ": the bar took the row"); assert.equal(b.buttons, 1, mode + ": with its Reload"); assert.equal(b.bars, 1, mode + ": one bar");
      assert.equal(b.paints, paints, mode + ": the probe painted nothing");
      await page.locator("#fileview-save-err button", { hasText: /^Reload$/ }).click();
      await paintsReach(page, paints + 1);
      await frames(page, 2);
      b = await readBar(page);
      assert.equal(b.words, LATIN1_NOTICE, mode + ": the Reload's landing brought the line back (before item 5: nothing said why Edit stayed off)");
      assert.equal(b.buttons, 0, mode + ": the bar's Reload went with it"); assert.equal(b.bars, 1, mode + ": one bar");
      assert.ok(b.aboveRow && b.inCard && b.inViewport, mode + ": above the row, on screen");
      assert.equal(b.text, LONG2, mode + ": over the new text"); assert.equal(b.edit, true, mode + ": Edit still hidden");
      assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT2, mode + ": the reload landed the new bytes");
      assert.deepEqual(errors, [], mode + ": no uncaught page error");
      await page.close();
      // a target's notice wins: an open at a line past the end (the Raw view) shows the past-the-end notice, not the line, because
      // the raise precedes landTarget; a reload's landing has no target and raises the line again
      const second = await openViewer(browser, mode, 700, 600, { utf8: { [REPORT]: "0" }, raw: true, openOpts: { at: { line: 9999 } } });
      b = await readBar(second.page);
      assert.equal(b.words, "Line 9999 is past the end of this file, which has 201 lines; showing the last line.", mode + ": the target's notice took the row (the past-the-end line is raised inside landTarget, after the line's raise)");
      assert.equal(b.bars, 1, mode + ": one bar"); assert.equal(b.edit, true, mode + ": Edit hidden here too");
      const p2 = b.paints;
      await second.page.evaluate(() => { (window as any).__seam.reload(); });
      await paintsReach(second.page, p2 + 1);
      await frames(second.page, 2);
      b = await readBar(second.page);
      assert.equal(b.words, LATIN1_NOTICE, mode + ": a reload's landing has no target and raised the line again");
      assert.equal(b.bars, 1, mode + ": one bar"); assert.equal(b.edit, true);
      assert.deepEqual(second.errors, [], mode + ": no uncaught page error");
      await second.page.close();
    }
  });
});
