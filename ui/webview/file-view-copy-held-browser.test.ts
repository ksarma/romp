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
// text the reader pressed on, the button acknowledges, and only then do the new bytes paint; the write REWROTE the fence,
// so after the swap no button on screen claims the copy: the acknowledgement follows the fence's source, and the fence
// with the copied text is gone (the final fixes after round 3; scenes 5 and 6 below have the fence kept and moved, and
// removed; file-view-copy-ack-browser.test.ts has the two clipboard paths over a write that keeps the fence); (2) the release paths: a
// press begun over the body and released over the title bar, and a blur while pressed (a release in another frame),
// each let the parked landing paint, once. Round 2 of the review added two more: (3) a right or middle press holds
// nothing (a right press's release commonly never reaches the page, the native context menu takes it on Linux and
// macOS, so a hold taken on one parked the landing until the reader's next click anywhere), so a reload under one
// paints at once, and a contextmenu while pressed (the browser ended the press itself) releases the hold; (4) a release
// and a second press on Copy back-to-back, before the release's zero timer fires (Chromium runs a pending input before
// a due timer): the landing waits for the second press's release too, and both presses copy. The fetch stub answers in
// microtasks, so two frames after the reload's fetch was made the landing has run: painted, or parked under the press.
// Skips LOUDLY without a playwright browser (CI installs none), as the other legs do. Synthetic values only: an
// invented note, the placeholder sid.
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
const MT4 = "1757145600000000029";

/** Record every clipboard write and every click that reaches the document (capture phase: a handler's stopPropagation
 *  cannot hide it), the order of the pointer events, the clicks and the seam's paints (`__log`), and remember the Copy
 *  button about to be pressed (a detached node keeps its text). */
const arm = (page: any): Promise<void> => page.evaluate(() => {
  const w = window as any;
  w.__copied = []; w.__clicks = 0; w.__log = [];
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: (t: string) => { w.__copied.push(t); return Promise.resolve(); } } });
  if (!w.__armed) {
    w.__armed = true;
    for (const type of ["pointerdown", "pointerup", "click"]) document.addEventListener(type, () => { w.__log.push(type); if (type === "click") w.__clicks++; }, true);
    w.__seam.onRendered(() => { w.__log.push("paint"); });
  }
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
    const onScreen = await page.evaluate(() => { const b = document.querySelector(".fileview-md pre > .code-copy")!; return { label: b.textContent, copied: b.classList.contains("copied") }; });
    assert.equal(onScreen.label, "Copy", "and the button on screen does not claim the copy: the write rewrote the fence, the clipboard holds the old text, and the acknowledgement follows the fence's source, not its index (code-block.ts acknowledge; round 3 marked the rewritten fence Copied)");
    assert.equal(onScreen.copied, false);
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

test("in a browser: a right or middle press holds nothing, so a reload under it paints at once; a contextmenu while pressed releases the hold", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1 } });
    const p = await centre(page, ".fileview-md p", 10);
    await page.mouse.move(p.x, p.y); await frames(page, 1);
    // (a) a right press: headless Chromium delivers the pointerdown and the contextmenu, and the pointerup only at the
    // release, which is the most a page ever sees of one (a native menu takes the release outright)
    await page.mouse.down({ button: "right" }); await frames(page, 1);
    const pressedA = await counts(page);
    await reload(page, DOC2, MT2);
    assert.equal((await counts(page)).paints, pressedA.paints + 1, "(a) the landing painted under the right press: no hold is taken for a button that yields no click");
    assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT2, "(a) the new bytes are what shows");
    await page.mouse.up({ button: "right" }); await frames(page, 2);
    assert.equal((await counts(page)).paints, pressedA.paints + 1, "(a) the right button's release paints nothing more");
    // (b) a middle press, the same
    await page.mouse.down({ button: "middle" }); await frames(page, 1);
    const pressedB = await counts(page);
    await reload(page, DOC1, MT3);
    assert.equal((await counts(page)).paints, pressedB.paints + 1, "(b) the landing painted under the middle press");
    await page.mouse.up({ button: "middle" }); await frames(page, 2);
    // (c) a primary press that the browser ends itself with a contextmenu (ctrl+click on macOS, a long press on a touch
    // screen): the landing parks under the press and the contextmenu releases it, since no click follows one
    await page.mouse.down(); await frames(page, 1);
    const pressedC = await counts(page);
    await reload(page, DOC2, MT4);
    assert.equal((await counts(page)).paints, pressedC.paints, "(c) the landing waits under the primary press");
    await page.evaluate(() => { document.querySelector(".fileview-md p")!.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, button: 0 })); });
    await paintsReach(page, pressedC.paints + 1);
    assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT4, "(c) the contextmenu released the hold and the landing painted");
    await page.mouse.up(); await frames(page, 2);
    assert.equal((await counts(page)).paints, pressedC.paints + 1, "(c) the pointerup after the contextmenu paints nothing more");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser: a release and a second press on Copy back-to-back: the landing waits for the second press's release too, and both presses copy", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1 } });
    await arm(page);
    const b = await centre(page, ".fileview-md pre > .code-copy");
    await page.mouse.move(b.x, b.y); await frames(page, 1);
    await page.mouse.down(); await frames(page, 1);                      // press 1 on Copy
    const pressed = await counts(page);
    await reload(page, DOC2, MT2);                                       // the landing parks under press 1
    assert.equal((await counts(page)).paints, pressed.paints, "the landing waits under press 1");
    // the release and press 2, dispatched without a wait between them: the input that begins press 2 is pending when
    // the release's zero timer comes due, and Chromium runs the input first
    const cdp = await page.context().newCDPSession(page);
    const up = cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: b.x, y: b.y, button: "left", clickCount: 1 });
    const down = cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: b.x, y: b.y, button: "left", clickCount: 1 });
    await Promise.all([up, down]);
    await cdp.detach();
    await frames(page, 2);
    await page.mouse.up(); await frames(page, 2);                        // press 2 released
    await paintsReach(page, pressed.paints + 1);
    const after = await page.evaluate(() => { const w = window as any; return { copied: w.__copied.slice(), clicks: w.__clicks, log: w.__log.slice(), paints: w.__paints, mt: w.__seam.mtimeNs() }; });
    const pu1 = after.log.indexOf("pointerup");
    const pd2 = after.log.indexOf("pointerdown", pu1);
    const pu2 = after.log.indexOf("pointerup", pd2);
    const paint = after.log.indexOf("paint");
    assert.ok(pu1 >= 0 && pd2 > pu1 && pu2 > pd2 && paint >= 0, "two presses and a paint in the log: " + after.log.join(" "));
    assert.equal(paint > pd2 && paint < pu2, false, "the paint did not land under press 2 (the timer found the surface pressed again and parked the run): " + after.log.join(" "));
    assert.equal(after.clicks, 2, "both presses clicked: " + after.log.join(" "));
    assert.equal(after.copied.length, 2, "and both copied");
    assert.equal(after.paints, pressed.paints + 1, "one paint for the one landing");
    assert.equal(after.mt, MT2, "which is on screen");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

// The acknowledgement follows the fence's SOURCE, not its index (the final fixes after round 3, 2026-09-09): a landing
// under the press that inserts a fence above the pressed one, and one that removes the pressed fence with another fence
// standing at its old index. Round 3 read the fence's index among the fenced blocks under each ancestor, so the first
// scene marked the inserted fence Copied and the second marked the fence that took the pressed one's place.
const FENCE_B = "SELECT id FROM notes;";
const DOC_BA = ["# Report", "", "An intro paragraph, and a session put a second fence above the first.", "", F + "sql", FENCE_B, F, "", "Between the fences.", "", F + "python", FENCE1, F, "", "A paragraph after the fence.", ""].join("\n");
const DOC_B = ["# Report", "", "An intro paragraph before the fence, the first fence removed by a session.", "", F + "sql", FENCE_B, F, "", "A paragraph after the fence.", ""].join("\n");
type Fenced = { code: string; label: string | null; copied: boolean };
/** Every fenced block on screen, in order: its code (the rows drop the newlines), its button's label and class. */
const fenced = (page: any): Promise<Fenced[]> => page.evaluate(() => Array.from(document.querySelectorAll(".fileview-md pre.has-copy")).map((pre) => {
  const b = pre.querySelector(":scope > .code-copy")!;
  return { code: (pre.querySelector("code")!.textContent || "").trimEnd(), label: b.textContent, copied: b.classList.contains("copied") };
}));

test("in a browser: a landing under the press inserts a fence above the pressed one: the pressed fence's new button reads Copied and the inserted fence's reads Copy", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1 } });
    await arm(page);
    const b = await centre(page, ".fileview-md pre > .code-copy");
    await page.mouse.move(b.x, b.y); await frames(page, 1);
    await page.mouse.down(); await frames(page, 1);
    const pressed = await counts(page);
    await reload(page, DOC_BA, MT2);
    assert.equal((await counts(page)).paints, pressed.paints, "the landing waits under the press");
    await page.mouse.up();
    await paintsReach(page, pressed.paints + 1);
    await frames(page, 2);
    const copied = await page.evaluate(() => (window as any).__copied.slice());
    assert.equal(copied.length, 1, "the press copied once");
    assert.equal(copied[0].trimEnd(), FENCE1, "the text the reader pressed on");
    assert.deepEqual(await fenced(page), [
      { code: FENCE_B, label: "Copy", copied: false },
      { code: FENCE1.replace(/\n/g, ""), label: "Copied", copied: true },
    ], "the acknowledgement is on the button of the fence with the pressed fence's source, now second; the inserted fence above it reads Copy (an index read marked the inserted one)");
    assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT2, "over the new bytes");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser: a landing under the press removes the pressed fence and another fence stands at its index: no button reads Copied", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1 } });
    await arm(page);
    const b = await centre(page, ".fileview-md pre > .code-copy");
    await page.mouse.move(b.x, b.y); await frames(page, 1);
    await page.mouse.down(); await frames(page, 1);
    const pressed = await counts(page);
    await reload(page, DOC_B, MT2);
    assert.equal((await counts(page)).paints, pressed.paints, "the landing waits under the press");
    await page.mouse.up();
    await paintsReach(page, pressed.paints + 1);
    await frames(page, 2);
    const copied = await page.evaluate(() => (window as any).__copied.slice());
    assert.equal(copied.length, 1, "the press copied once");
    assert.equal(copied[0].trimEnd(), FENCE1, "the text the reader pressed on, which the write removed");
    assert.deepEqual(await fenced(page), [{ code: FENCE_B, label: "Copy", copied: false }], "the fence at the pressed one's index has other text and does not claim the copy (an index read marked it Copied)");
    assert.equal(await page.evaluate(() => document.querySelectorAll(".code-copy.copied").length), 0, "nothing on screen reads Copied: the copied fence is gone");
    assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT2, "over the new bytes");
    assert.deepEqual(errors, [], "no script error: a fence the write removed is nothing to acknowledge on");
    await page.close();
  });
});

// Of several fences with the pressed fence's source, the pressed one's ordinal among them (identical fences, which
// nothing else tells apart): two fences of one text, the second pressed, a write puts a third fence above both.
const DOC_AA = ["# Report", "", "An intro paragraph before two fences of one text.", "", F + "python", FENCE1, F, "", "Between the fences.", "", F + "python", FENCE1, F, "", "A paragraph after the fences.", ""].join("\n");
const DOC_BAA = ["# Report", "", "An intro paragraph, and a session put a third fence above the two.", "", F + "sql", FENCE_B, F, "", "Between the fences.", "", F + "python", FENCE1, F, "", "Between the fences.", "", F + "python", FENCE1, F, "", "A paragraph after the fences.", ""].join("\n");

test("in a browser: two fences of one text, the second pressed, a landing under the press inserts a fence above both: the second of the two reads Copied", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC_AA } });
    await arm(page);
    const b = await centre(page, ".fileview-md > pre:nth-of-type(2) > .code-copy");
    await page.mouse.move(b.x, b.y); await frames(page, 1);
    await page.mouse.down(); await frames(page, 1);
    const pressed = await counts(page);
    await reload(page, DOC_BAA, MT2);
    assert.equal((await counts(page)).paints, pressed.paints, "the landing waits under the press");
    await page.mouse.up();
    await paintsReach(page, pressed.paints + 1);
    await frames(page, 2);
    assert.equal((await page.evaluate(() => (window as any).__copied.length)), 1, "the press copied once");
    const A = FENCE1.replace(/\n/g, "");
    assert.deepEqual(await fenced(page), [
      { code: FENCE_B, label: "Copy", copied: false },
      { code: A, label: "Copy", copied: false },
      { code: A, label: "Copied", copied: true },
    ], "the second fence of the pressed text carries the acknowledgement: the source decides which text, the pressed fence's ordinal among that text's fences which one (an index read marked the first of the two)");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
