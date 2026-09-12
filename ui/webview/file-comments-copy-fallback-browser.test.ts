// The Comment float across a click on a fence's Copy button whose copy runs through the execCommand fallback, in headless Chromium
// over the REAL viewer and panel (plans/markdown-viewer.md Slice 5, item 9; code-block.ts fallbackCopy; the Slice 5 review, rounds 6
// and 7; real-viewer-leg.ts: the Files pane, whose origin is no secure context, so navigator.clipboard is absent and every Copy takes
// the fallback, the path a denied permission or a refused write takes too). The press on the button hides the float (hideFloatOnDown)
// and the release re-offers it through the seam's mouseup (a mousedown on a button leaves the selection standing), and the click's
// copy then appended a textarea, focused it, selected its text, ran the command and removed it: the document's selection went with
// the textarea and came back collapsed outside the passage, the focus landed on the body, and no selectionchange reached the
// document, so the Comment button stood beside a passage nobody had selected, and a click on it did nothing but hide it (the
// review's fuzz: 27 steps in 5,040 on main, 3 on the slice's tree). Now the fallback keeps the selection's two ends, anchor and
// focus, before the textarea takes the selection and puts them back after with setBaseAndExtent, and gives the focus back to the
// element that held it, as the Clipboard API path leaves both. The ends, not a Range (round 7): round 6 put the selection back as a
// cloned Range, which has no direction, so a passage selected right to left came back forward, anchor and focus swapped; the panel
// knows the selection it offered Comment beside by its ends (offeredFor, atEnds), read the restored one as new and offered again,
// at the pane's top edge beside nothing when a scroll had taken the passage off the pane and hidden the button (hideFloatOnScroll),
// and the next Shift+ArrowLeft shrank the selection from the other end. Two legs. The first, two scenes in one page: a real drag
// over a paragraph, a real click on the fence's Copy button, the selection and the float as they were and a click on the button
// opening the composer on the passage; then Space on the focused Copy button, which keeps the focus (before: lost to the body). The
// second, over a longer note in a short pane: a right-to-left drag, the click on Copy keeping the selection's direction (before:
// forward), Shift+ArrowLeft extending it leftwards (before: shrinking it from the right), then a fresh drag, the pane scrolled past
// the passage (the float hides) and Space on the focused Copy button leaving the float hidden (before: shown at the top edge).
// Awaits the DOM's own states (the Copied label, the composer, the command count, the selectionchange count, the float's hidden
// bit) and frames, never a timer. Skips LOUDLY without a playwright browser (CI installs none). Synthetic values only: an invented
// note, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, REPORT } from "./real-viewer-leg";

const F = "```";
const INTRO = "Intro paragraph with several words to select from, long enough to drag across a few of them.";
const NOTE = ["# Report", "", INTRO, "", F + "js", "const a = 1;", "console.log(a);", F, "", "Trailing paragraph with several words after the fence.", ""].join("\n");
/** The same note with forty paragraphs after the fence, so a short pane can scroll the intro off. */
const FILLER = Array.from({ length: 40 }, (_, i) => `Filler paragraph ${i + 1}: words after the fence, enough of them for the intro to scroll off a short pane.`).join("\n\n");
const NOTE_LONG = ["# Report", "", INTRO, "", F + "js", "const a = 1;", "console.log(a);", F, "", FILLER, ""].join("\n");
const BTN = ".fileview-md pre.has-copy > .code-copy";

type Scene = { hidden: boolean; left: number; top: number; selected: string; collapsed: boolean; inBody: boolean; backwards: boolean; anchorOffset: number; focusOffset: number; offPane: boolean; active: string; copyLabel: string | null; execs: number; selChanges: number; composer: boolean; composerRef: string };
/** The float's state and inline place, the selection's text, whether it is collapsed and whether both its ends lie in the body,
 *  its direction (backwards: the anchor after the focus, the shape of a right-to-left drag) and its two offsets, whether its box lies
 *  wholly outside the body's (offPane), the active element ("copy-button" for the fence's Copy button, whatever its class of the
 *  moment; else its tag), the Copy button's label, the count of copy commands run and of selectionchange events seen, whether a
 *  composer stands (the persistent box shown) and what its reference line says. */
const scene = (page: any): Promise<Scene> => page.evaluate((btn: string) => {
  const w = window as any; const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!; const body = document.querySelector(".fileview-body");
  const a = document.activeElement;
  const an = sel.anchorNode, fn = sel.focusNode;
  const backwards = !!an && !!fn && (an === fn ? sel.anchorOffset > sel.focusOffset : !!(an.compareDocumentPosition(fn) & Node.DOCUMENT_POSITION_PRECEDING));
  const rr = sel.rangeCount ? sel.getRangeAt(0).getBoundingClientRect() : null; const br = body ? body.getBoundingClientRect() : null;
  return { hidden: f.hidden, left: parseFloat(f.style.left), top: parseFloat(f.style.top), selected: String(sel), collapsed: sel.isCollapsed,
    inBody: !!body && !!an && !!fn && body.contains(an) && body.contains(fn),
    backwards, anchorOffset: sel.anchorOffset, focusOffset: sel.focusOffset,
    offPane: !!rr && !!br && (rr.bottom <= br.top || rr.top >= br.bottom),
    active: a && a === document.querySelector(btn) ? "copy-button" : a ? a.tagName : "none",
    copyLabel: (document.querySelector(btn) as HTMLElement | null)?.textContent ?? null, execs: w.__execs as number, selChanges: w.__selChanges as number,
    composer: !!(document.querySelector(".fileview-aside .fc-composer") as HTMLElement | null && !(document.querySelector(".fileview-aside .fc-composer") as HTMLElement).hidden), composerRef: (document.querySelector(".fileview-aside .fc-composer-ref") as HTMLElement | null)?.textContent ?? "" };
}, BTN);
const centre = (page: any, sel: string): Promise<{ x: number; y: number }> => page.evaluate((s: string) => {
  const r = document.querySelector(s)!.getBoundingClientRect();
  return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
}, sel);
/** A real mouse drag over the first paragraph's text, from its character boundary `from` to its boundary `to` (a `to` below `from`
 *  is a right-to-left drag, the selection's anchor at `from` and its focus at `to`); the seam's mouseup offers the float. The press
 *  and the release land a pixel inside the character on the drag's own side of each boundary. */
async function dragOver(page: any, from: number, to: number): Promise<void> {
  const r = await page.evaluate(([a, b, fwd]: [number, number, boolean]) => {
    const t = (document.querySelector(".fileview-md > p") as HTMLElement).firstChild as Text;
    const at = (k: number, side: "left" | "right"): { x: number; y: number } => {
      const ra = document.createRange(); ra.setStart(t, side === "right" ? k - 1 : k); ra.setEnd(t, side === "right" ? k : k + 1); const x = ra.getBoundingClientRect();
      return { x: side === "right" ? x.right - 1 : x.left + 1, y: x.top + x.height / 2 };
    };
    return { p: at(a, fwd ? "left" : "right"), q: at(b, fwd ? "right" : "left") };
  }, [from, to, to > from]);
  await page.mouse.move(r.p.x, r.p.y); await page.mouse.down(); await page.mouse.move(r.q.x, r.q.y, { steps: 6 }); await page.mouse.up();
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await frames(page, 2);
}
/** The premise, checked rather than assumed: no async API on this origin, so copyText takes the fallback; then the counters. */
async function armFallbackPage(page: any): Promise<void> {
  const env = await page.evaluate(() => ({ secure: window.isSecureContext, api: !!(navigator.clipboard && navigator.clipboard.writeText) }));
  assert.deepEqual(env, { secure: false, api: false }, "the leg's origin is no secure context and carries no Clipboard API: the fallback is the path that runs");
  await page.evaluate(() => {
    const w = window as any; w.__execs = 0; w.__selChanges = 0;
    const real = document.execCommand.bind(document);
    document.execCommand = (cmd: string, ui?: boolean, val?: string) => { const ok = real(cmd, ui, val); if (cmd === "copy") w.__execs++; return ok; };
    document.addEventListener("selectionchange", () => { w.__selChanges++; });
  });
}

test("in a browser, the real viewer and panel (the Files pane, no Clipboard API: the execCommand fallback): a drag offers Comment, a click on the fence's Copy button copies and leaves the selection and the float as they were (before: the selection collapsed outside the passage with no selectionchange, the float beside nothing), a click on the float opens the composer on the passage, and Space on the focused Copy button keeps the focus (before: lost to the body)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 700, 600, { docs: { [REPORT]: NOTE } });
    await armFallbackPage(page);
    await openPanel(page);
    assert.equal(await page.evaluate((b: string) => document.querySelectorAll(b).length, BTN), 1, "one fence with its Copy button");
    // scene 1: a drag over the intro, the float offered beside it
    await dragOver(page, 6, 30);
    const s0 = await scene(page);
    assert.ok(s0.selected.length >= 20 && INTRO.includes(s0.selected), "the drag selected a passage of the intro: " + JSON.stringify(s0.selected));
    assert.deepEqual([s0.hidden, s0.collapsed, s0.inBody, s0.backwards, s0.execs], [false, false, true, false, 0], "the drag's mouseup offers the float; a left-to-right drag runs forward; nothing copied yet");
    // a real click on the fence's Copy button: the press hides the float, the release re-offers it (the selection stands under a
    // button's mousedown), and the click copies through the fallback
    const b = await centre(page, BTN);
    await page.mouse.click(b.x, b.y);
    await page.waitForFunction((btn: string) => (document.querySelector(btn) as HTMLElement).textContent === "Copied", BTN, { timeout: 5000 });
    await frames(page, 3);
    const s1 = await scene(page);
    assert.equal(s1.execs, 1, "the click copied once, through execCommand");
    assert.equal(s1.copyLabel, "Copied", "...and the button acknowledged it");
    assert.equal(s1.selected, s0.selected, "the passage stands selected after the copy (before: the selection went with the fallback's textarea and came back collapsed outside the passage)");
    assert.deepEqual([s1.collapsed, s1.inBody], [false, true], "...not collapsed, both ends in the body");
    assert.deepEqual([s1.backwards, s1.anchorOffset, s1.focusOffset], [s0.backwards, s0.anchorOffset, s0.focusOffset], "...its ends where they were");
    assert.equal(s1.hidden, false, "the float shows beside it");
    assert.deepEqual([s1.left, s1.top], [s0.left, s0.top], "...where the drag's offer put it: the same passage");
    assert.equal(s1.active, "copy-button", "the Copy button, which the click focused, holds the focus again (before: the body, once the focused textarea was removed)");
    // a click on the float: the composer opens on the passage (before: the click found a collapsed selection, and only hid the button)
    const f = await centre(page, ".fc-float");
    await page.mouse.click(f.x, f.y);
    await page.waitForFunction(() => { const b = document.querySelector(".fileview-aside .fc-composer") as HTMLElement | null; return !!b && !b.hidden; }, null, { timeout: 5000 }).catch(() => null);
    const s2 = await scene(page);
    assert.equal(s2.composer, true, "the Comment button opened the composer (before: nothing, the button beside a selection that was gone)");
    assert.ok(s2.composerRef.includes(s0.selected.slice(0, 20)), "...on the passage the person selected: " + JSON.stringify(s2.composerRef));
    assert.equal(s2.hidden, true, "the float went with the click, as ever");
    // scene 2: Escape closes the composer; Space on the focused Copy button copies and keeps the focus on the button
    await page.keyboard.press("Escape");
    await page.waitForFunction(() => { const b = document.querySelector(".fileview-aside .fc-composer") as HTMLElement | null; return !b || b.hidden; }, null, { timeout: 5000 });   // the box is persistent: closed, it is hidden in the slot
    await page.evaluate((btn: string) => (document.querySelector(btn) as HTMLElement).focus(), BTN);
    assert.equal((await scene(page)).active, "copy-button", "the Copy button focused from the keyboard");
    const s3 = await scene(page);
    await page.keyboard.press("Space");
    await page.waitForFunction(() => (window as any).__execs >= 2, null, { timeout: 5000 });
    await frames(page, 2);
    const s4 = await scene(page);
    assert.equal(s4.execs, 2, "Space copied once more, through the fallback");
    assert.equal(s4.active, "copy-button", "the button keeps the focus through the copy (before: the body, and the keyboard's place with it)");
    assert.equal(s4.selected, s3.selected, "the selection is as it was before the press");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the same pane over a longer note: a passage selected right to left keeps its direction across a click on the fence's Copy button (before: put back as a Range it came back forward, anchor and focus swapped), so Shift+ArrowLeft after the copy extends it leftwards (before: shrank it from the right); and Space on the focused Copy button after a scroll took the passage off the pane and hid the Comment button leaves the button hidden (before: the panel read the restored ends as a new selection and offered Comment at the pane's top edge beside nothing)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 700, 400, { docs: { [REPORT]: NOTE_LONG } });
    await armFallbackPage(page);
    await openPanel(page);
    assert.equal(await page.evaluate((b: string) => document.querySelectorAll(b).length, BTN), 1, "one fence with its Copy button");
    // scene 1: a right-to-left drag over the intro, the float offered beside it
    await dragOver(page, 30, 6);
    const s0 = await scene(page);
    assert.equal(s0.selected, INTRO.slice(6, 30), "the drag selected characters 6 to 30 of the intro");
    assert.deepEqual([s0.backwards, s0.anchorOffset, s0.focusOffset, s0.hidden, s0.collapsed, s0.inBody, s0.execs], [true, 30, 6, false, false, true, 0], "...right to left: the anchor at the press (30), the focus at the release (6); the float offered; nothing copied yet");
    // a real click on the fence's Copy button (the fallback path, as in the first leg)
    const b = await centre(page, BTN);
    await page.mouse.click(b.x, b.y);
    await page.waitForFunction((btn: string) => (document.querySelector(btn) as HTMLElement).textContent === "Copied", BTN, { timeout: 5000 });
    await frames(page, 3);
    const s1 = await scene(page);
    assert.deepEqual([s1.execs, s1.copyLabel], [1, "Copied"], "the click copied once, through execCommand, and the button acknowledged it");
    assert.equal(s1.selected, s0.selected, "the passage stands selected after the copy");
    assert.deepEqual([s1.backwards, s1.anchorOffset, s1.focusOffset], [true, 30, 6], "...and runs right to left still, its anchor at 30 and its focus at 6 (before: forward, anchor 6 and focus 30, a Range put back through addRange)");
    assert.equal(s1.hidden, false, "the float shows beside it");
    assert.deepEqual([s1.left, s1.top], [s0.left, s0.top], "...where the drag's offer put it");
    assert.equal(s1.active, "copy-button", "the Copy button holds the focus again");
    // Shift+ArrowLeft with the focus back in the document (a focused button takes the key): the selection's focus end moves left
    await page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); });
    await page.keyboard.press("Shift+ArrowLeft");
    await page.waitForFunction((n: number) => (window as any).__selChanges > n, s1.selChanges, { timeout: 5000 });
    await frames(page, 2);
    const s2 = await scene(page);
    assert.deepEqual([s2.backwards, s2.anchorOffset, s2.focusOffset, s2.selected], [true, 30, 5, INTRO.slice(5, 30)], "Shift+ArrowLeft extended the selection leftwards from its focus at 6 (before: the focus sat at the right end after the copy, and the key shrank the selection to 6..29)");
    // scene 2: a click on the heading collapses the selection (a drag begun inside a standing selection drags its text, and selects
    // nothing) and the float goes with the passage; then a fresh right-to-left drag, and the pane scrolled past the passage: the float
    // hides (hideFloatOnScroll), the selection stands
    const h = await centre(page, ".fileview-md > h1");
    await page.mouse.click(h.x, h.y);
    await page.waitForFunction(() => getSelection()!.isCollapsed && (document.querySelector(".fc-float") as HTMLElement).hidden, null, { timeout: 5000 });
    await frames(page, 2);
    await dragOver(page, 30, 6);
    const s3 = await scene(page);
    assert.deepEqual([s3.backwards, s3.anchorOffset, s3.focusOffset, s3.hidden], [true, 30, 6, false], "the drag's selection, right to left, the float offered");
    await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop += 600; });
    await page.waitForFunction(() => (document.querySelector(".fc-float") as HTMLElement).hidden, null, { timeout: 5000 });
    await frames(page, 2);
    const s4 = await scene(page);
    assert.deepEqual([s4.hidden, s4.offPane, s4.backwards, s4.selected], [true, true, true, s3.selected], "the scroll took the passage off the pane and hid the float; the selection stands");
    // the fence's Copy button focused from the keyboard (off the pane too: no scroll), Space copies through the fallback
    await page.evaluate((btn: string) => (document.querySelector(btn) as HTMLElement).focus({ preventScroll: true }), BTN);
    assert.equal((await scene(page)).active, "copy-button", "the Copy button focused from the keyboard");
    await page.keyboard.press("Space");
    await page.waitForFunction(() => (window as any).__execs >= 2, null, { timeout: 5000 });
    await frames(page, 3);
    const s5 = await scene(page);
    assert.equal(s5.execs, 2, "Space copied once more, through the fallback");
    assert.deepEqual([s5.selected, s5.backwards, s5.anchorOffset, s5.focusOffset, s5.offPane], [s4.selected, true, 30, 6, true], "the selection is as it was: the same passage, right to left, off the pane");
    assert.equal(s5.hidden, true, "the Comment button stays hidden: the restored selection is the one it was offered beside, and a scroll's hide holds until the selection changes (before: shown at the pane's top edge beside nothing, the restored ends read as a new selection)");
    assert.equal(s5.active, "copy-button", "the button keeps the focus through the copy");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
