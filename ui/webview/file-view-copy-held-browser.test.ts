// A press on a fence's Copy survives a reload landing under it (review of Slice 3 of plans/markdown-viewer.md, round 1,
// 2026-09-08). Every text paint rebuilds the viewer's body wholesale (file-view.ts renderBody: body.replaceChildren(
// mdBlock(...)), every fence and its Copy button new nodes), and one paint has no gesture of the reader's behind it:
// the fetch landing of a reload the Comments panel asked for when its poll saw the file's mtime move (a session wrote
// the note being read). A press that straddles that swap lost its click: a pressed node removed before the mouseup
// dispatches no click at all, to the button or to any ancestor (Chromium 151, probed; so delegating the button's
// action, ui/CLAUDE.md's first option, would not help), and the reader copied nothing and saw no Copied. The rule's
// second option is the one that applies: the landing is HELD while a pointer is pressed over the body and runs on the
// release (actions.ts pressHold; file-view-copy-held.test.ts has the helper alone). Two scenes over the real viewer
// (real-viewer-leg.ts), the pane surface: (1) mousedown on Copy, the reload's fetch lands, mouseup: one copy, of the
// text the reader pressed on, the button acknowledges, and only then do the new bytes paint; (2) the release paths: a
// press begun over the body and released over the title bar, and a blur while pressed (a release in another frame),
// each let the parked landing paint, once. The fetch stub answers in microtasks, so two frames after the reload's
// fetch was made the landing has run: painted, or parked under the press. Skips LOUDLY without a playwright browser
// (CI installs none), as the other legs do. Synthetic values only: an invented note, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, paintsReach, REPORT, MT2 } from "./real-viewer-leg";

const F = "```";
const FENCE1 = "# a comment\ndef f(x):\n    return x + 1";
const FENCE2 = "# a comment\ndef f(x):\n    return x + 2";
const note = (intro: string, fence: string): string => ["# Report", "", intro, "", F + "python", fence, F, "", "A paragraph after the fence.", ""].join("\n");
const DOC1 = note("An intro paragraph before the fence.", FENCE1);
const DOC2 = note("An intro paragraph before the fence, rewritten by a session.", FENCE2);
const MT3 = "1757145600000000019";

/** Record every clipboard write and every click that reaches the document (capture phase: a handler's stopPropagation
 *  cannot hide it), and remember the Copy button about to be pressed (a detached node keeps its text). */
const arm = (page: any): Promise<void> => page.evaluate(() => {
  const w = window as any;
  w.__copied = []; w.__clicks = 0;
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: (t: string) => { w.__copied.push(t); return Promise.resolve(); } } });
  if (!w.__armed) { w.__armed = true; document.addEventListener("click", () => { w.__clicks++; }, true); }
  w.__pressed = document.querySelector(".fileview-md pre > .code-copy");
});
const centre = (page: any, sel: string, dx = 0): Promise<{ x: number; y: number }> => page.evaluate(([s, d]: [string, number]) => {
  const r = document.querySelector(s)!.getBoundingClientRect();
  return { x: d ? r.x + d : r.x + r.width / 2, y: r.y + r.height / 2 };
}, [sel, dx]);
const counts = (page: any): Promise<{ fetches: number; paints: number }> => page.evaluate(() => ({ fetches: (window as any).__fetches, paints: (window as any).__paints }));
/** A session's write: new bytes under a new mtime, and the reload the panel's poll would ask for. */
const reload = async (page: any, text: string, mtime: string): Promise<void> => {
  const before = await counts(page);
  await page.evaluate(([p, t, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = t; w.__mtime = m; w.__seam.reload(); }, [REPORT, text, mtime]);
  await page.waitForFunction((n: number) => (window as any).__fetches > n, before.fetches, { timeout: 10000 });
  await frames(page, 2);
};

test("in a browser: a press on Copy that a reload lands under still copies, the text the reader pressed on, and the new bytes paint after the release", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1 } });
    await arm(page);
    const b = await centre(page, ".fileview-md pre > .code-copy");
    await page.mouse.move(b.x, b.y); await frames(page, 1);
    await page.mouse.down(); await frames(page, 1);
    const pressed = await counts(page);
    await reload(page, DOC2, MT2);
    const landed = await counts(page);
    await page.mouse.up(); await frames(page, 2);
    const after = await page.evaluate(() => { const w = window as any; return { copied: w.__copied.slice(), clicks: w.__clicks, label: w.__pressed.textContent, copiedClass: w.__pressed.classList.contains("copied") }; });
    assert.equal(after.copied.length, 1, "the press copied once: a fetch landing waits while a pointer is pressed over the body (file-view.ts through actions.ts pressHold) so the pressed button lives to see its mouseup");
    assert.equal(after.copied[0].trimEnd(), FENCE1, "the text the reader pressed on, not the write's");
    assert.equal(after.clicks, 1, "one click reached the document");
    assert.equal(after.label, "Copied", "and the button acknowledged");
    assert.equal(after.copiedClass, true);
    assert.equal(landed.paints, pressed.paints, "the landing did not paint under the press");
    await paintsReach(page, pressed.paints + 1);
    const shown = await page.evaluate(() => { const w = window as any; return { mt: w.__seam.mtimeNs(), intro: (document.querySelector(".fileview-md p")!.textContent || "").trim(), code: (document.querySelector(".fileview-md pre code")!.textContent || "").trimEnd(), oldGone: !document.contains(w.__pressed), paints: w.__paints }; });
    assert.equal(shown.mt, MT2, "then the reload landed");
    assert.equal(shown.intro, "An intro paragraph before the fence, rewritten by a session.", "the new bytes are on screen");
    assert.equal(shown.code, FENCE2.replace(/\n/g, ""), "the fence too (the rows drop the newlines)");
    assert.equal(shown.oldGone, true, "the pressed button went with the old body, after its click");
    assert.equal(shown.paints, pressed.paints + 1, "one paint for the one landing");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser: a press released over the title bar, and a blur while pressed, each let the parked landing paint once", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1 } });
    // (a) the press begins over the note and ends over the title bar, outside the body
    const p = await centre(page, ".fileview-md p", 10);
    await page.mouse.move(p.x, p.y); await frames(page, 1);
    await page.mouse.down(); await frames(page, 1);
    const bar = await centre(page, ".fileview-bar");
    await page.mouse.move(bar.x, bar.y); await frames(page, 1);
    const pressedA = await counts(page);
    await reload(page, DOC2, MT2);
    assert.equal((await counts(page)).paints, pressedA.paints, "(a) the landing waits under the press");
    await page.mouse.up();
    await paintsReach(page, pressedA.paints + 1);
    assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT2, "(a) the release over the bar let it paint");
    await frames(page, 2);
    // (b) a blur while pressed: the release happened in another frame and never reaches this one
    const p2 = await centre(page, ".fileview-md p", 10);
    await page.mouse.move(p2.x, p2.y); await frames(page, 1);
    await page.mouse.down(); await frames(page, 1);
    const pressedB = await counts(page);
    await reload(page, DOC1, MT3);
    assert.equal((await counts(page)).paints, pressedB.paints, "(b) the landing waits under the press");
    await page.evaluate(() => { window.dispatchEvent(new Event("blur")); });
    await paintsReach(page, pressedB.paints + 1);
    assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT3, "(b) the blur released the hold and the landing painted");
    await page.mouse.up(); await frames(page, 2);
    assert.equal((await counts(page)).paints, pressedB.paints + 1, "(b) the mouseup after the blur paints nothing more");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
