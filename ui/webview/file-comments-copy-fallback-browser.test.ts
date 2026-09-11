// The Comment float across a click on a fence's Copy button whose copy runs through the execCommand fallback, in headless Chromium
// over the REAL viewer and panel (plans/markdown-viewer.md Slice 5, item 9; code-block.ts fallbackCopy; the Slice 5 review, round 6;
// real-viewer-leg.ts: the Files pane, whose origin is no secure context, so navigator.clipboard is absent and every Copy takes the
// fallback, the path a denied permission or a refused write takes too). The press on the button hides the float (hideFloatOnDown)
// and the release re-offers it through the seam's mouseup (a mousedown on a button leaves the selection standing), and the click's
// copy then appended a textarea, focused it, selected its text, ran the command and removed it: the document's selection went with
// the textarea and came back collapsed outside the passage, the focus landed on the body, and no selectionchange reached the
// document, so the Comment button stood beside a passage nobody had selected, and a click on it did nothing but hide it (the
// review's fuzz: 27 steps in 5,040 on main, 3 on the slice's tree). Now the fallback clones the selection's ranges before the
// textarea takes the selection and puts them back after, and gives the focus back to the element that held it, as the Clipboard
// API path leaves both. Two scenes in one page: a real drag over a paragraph, a real click on the fence's Copy button, the
// selection and the float as they were and a click on the button opening the composer on the passage; then Space on the focused
// Copy button, which keeps the focus (before: lost to the body). Awaits the DOM's own states (the Copied label, the composer, the
// command count) and frames, never a timer. Skips LOUDLY without a playwright browser (CI installs none). Synthetic values only:
// an invented note, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, REPORT } from "./real-viewer-leg";

const F = "```";
const INTRO = "Intro paragraph with several words to select from, long enough to drag across a few of them.";
const NOTE = ["# Report", "", INTRO, "", F + "js", "const a = 1;", "console.log(a);", F, "", "Trailing paragraph with several words after the fence.", ""].join("\n");
const BTN = ".fileview-md pre.has-copy > .code-copy";

type Scene = { hidden: boolean; left: number; top: number; selected: string; collapsed: boolean; inBody: boolean; active: string; copyLabel: string | null; execs: number; selChanges: number; composer: boolean; composerRef: string };
/** The float's state and inline place, the selection's text, whether it is collapsed and whether both its ends lie in the body, the
 *  active element ("copy-button" for the fence's Copy button, whatever its class of the moment; else its tag), the Copy button's
 *  label, the count of copy commands run and of selectionchange events seen, whether a composer stands (the persistent box
 *  shown) and what its reference line says. */
const scene = (page: any): Promise<Scene> => page.evaluate((btn: string) => {
  const w = window as any; const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!; const body = document.querySelector(".fileview-body");
  const a = document.activeElement;
  return { hidden: f.hidden, left: parseFloat(f.style.left), top: parseFloat(f.style.top), selected: String(sel), collapsed: sel.isCollapsed,
    inBody: !!body && !!sel.anchorNode && !!sel.focusNode && body.contains(sel.anchorNode) && body.contains(sel.focusNode),
    active: a && a === document.querySelector(btn) ? "copy-button" : a ? a.tagName : "none",
    copyLabel: (document.querySelector(btn) as HTMLElement | null)?.textContent ?? null, execs: w.__execs as number, selChanges: w.__selChanges as number,
    composer: !!(document.querySelector(".fileview-aside .fc-composer") as HTMLElement | null && !(document.querySelector(".fileview-aside .fc-composer") as HTMLElement).hidden), composerRef: (document.querySelector(".fileview-aside .fc-composer-ref") as HTMLElement | null)?.textContent ?? "" };
}, BTN);
const centre = (page: any, sel: string): Promise<{ x: number; y: number }> => page.evaluate((s: string) => {
  const r = document.querySelector(s)!.getBoundingClientRect();
  return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
}, sel);
/** A real mouse drag over the first paragraph's text, from its character `from` to its character `to`; the seam's mouseup offers the float. */
async function dragOver(page: any, from: number, to: number): Promise<void> {
  const r = await page.evaluate(([a, b]: [number, number]) => {
    const t = (document.querySelector(".fileview-md > p") as HTMLElement).firstChild as Text;
    const ra = document.createRange(); ra.setStart(t, a); ra.setEnd(t, a + 1); const x = ra.getBoundingClientRect();
    const rb = document.createRange(); rb.setStart(t, b - 1); rb.setEnd(t, b); const y = rb.getBoundingClientRect();
    return { x1: x.left + 1, y1: x.top + x.height / 2, x2: y.right - 1, y2: y.top + y.height / 2 };
  }, [from, to]);
  await page.mouse.move(r.x1, r.y1); await page.mouse.down(); await page.mouse.move(r.x2, r.y2, { steps: 6 }); await page.mouse.up();
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await frames(page, 2);
}

test("in a browser, the real viewer and panel (the Files pane, no Clipboard API: the execCommand fallback): a drag offers Comment, a click on the fence's Copy button copies and leaves the selection and the float as they were (before: the selection collapsed outside the passage with no selectionchange, the float beside nothing), a click on the float opens the composer on the passage, and Space on the focused Copy button keeps the focus (before: lost to the body)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 700, 600, { docs: { [REPORT]: NOTE } });
    // the premise, checked rather than assumed: no async API on this origin, so copyText takes the fallback
    const env = await page.evaluate(() => ({ secure: window.isSecureContext, api: !!(navigator.clipboard && navigator.clipboard.writeText) }));
    assert.deepEqual(env, { secure: false, api: false }, "the leg's origin is no secure context and carries no Clipboard API: the fallback is the path that runs");
    await page.evaluate(() => {
      const w = window as any; w.__execs = 0; w.__selChanges = 0;
      const real = document.execCommand.bind(document);
      document.execCommand = (cmd: string, ui?: boolean, val?: string) => { const ok = real(cmd, ui, val); if (cmd === "copy") w.__execs++; return ok; };
      document.addEventListener("selectionchange", () => { w.__selChanges++; });
    });
    await openPanel(page);
    assert.equal(await page.evaluate((b: string) => document.querySelectorAll(b).length, BTN), 1, "one fence with its Copy button");
    // scene 1: a drag over the intro, the float offered beside it
    await dragOver(page, 6, 30);
    const s0 = await scene(page);
    assert.ok(s0.selected.length >= 20 && INTRO.includes(s0.selected), "the drag selected a passage of the intro: " + JSON.stringify(s0.selected));
    assert.deepEqual([s0.hidden, s0.collapsed, s0.inBody, s0.execs], [false, false, true, 0], "the drag's mouseup offers the float; nothing copied yet");
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
