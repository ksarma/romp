// A Space held on a fence's Copy survives a reload landing under it (review of Slice 3 of plans/markdown-viewer.md, round
// 2, 2026-09-08). A button's Space activation is native to the KEYUP (Chromium, WebKit and Gecko alike; Enter clicks on
// the keydown), so a keyboard press has the same window a pointer press has, the keydown to the keyup, and nothing held
// the body for it: the viewer's hold (actions.ts pressHold) reads pointer events, and the chat has no hold at all. The
// reload's fetch landing (the Comments panel's poll saw a session's write) swapped the body under the held key, the
// focused button went with the old body, and the keyup, on the pane's root now, clicked nothing: no copy, no Copied.
// code-block.ts closes the window from the button's side instead of holding the surface: the Copy button acts on the
// Space KEYDOWN, as Enter does natively, with the key's default prevented on both the keydown (the button is never put
// :active by the key, so the keyup clicks nothing) and the keyup, and a held key's repeats copy nothing more. Every
// surface with a Copy gets it, the chat's cards included. Two scenes over the real viewer (real-viewer-leg.ts), the pane
// and the chat modal: (1) Copy focused, Space down, the reload lands, Space up: one copy, of the text the reader pressed
// on, the pressed button acknowledges, the new bytes are on screen; (2) with no reload, Space copies exactly once (no
// second copy off the keyup), a held key's repeats copy nothing more, and Enter still copies once. The fetch stub answers
// in microtasks, so two frames after the reload's fetch was made the landing has run. Skips LOUDLY without a playwright
// browser (CI installs none), as the other legs do. Synthetic values only: an invented note, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, REPORT, MT2, type Mode } from "./real-viewer-leg";

const F = "```";
const FENCE1 = "# a comment\ndef f(x):\n    return x + 1";
const FENCE2 = "# a comment\ndef f(x):\n    return x + 2";
const note = (intro: string, fence: string): string => ["# Report", "", intro, "", F + "python", fence, F, "", "A paragraph after the fence.", ""].join("\n");
const DOC1 = note("An intro paragraph before the fence.", FENCE1);
const DOC2 = note("An intro paragraph before the fence, rewritten by a session.", FENCE2);

/** Record every clipboard write and every click that reaches the document (capture phase: a handler's stopPropagation
 *  cannot hide it), and focus the fence's Copy, remembered as the pressed button (a detached node keeps its text). */
const arm = (page: any): Promise<void> => page.evaluate(() => {
  const w = window as any;
  w.__copied = []; w.__clicks = 0;
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: (t: string) => { w.__copied.push(t); return Promise.resolve(); } } });
  if (!w.__armed) { w.__armed = true; document.addEventListener("click", () => { w.__clicks++; }, true); }
  w.__pressed = document.querySelector(".fileview-md pre > .code-copy");
  w.__pressed.focus();
});
const counts = (page: any): Promise<{ fetches: number; paints: number }> => page.evaluate(() => ({ fetches: (window as any).__fetches, paints: (window as any).__paints }));
/** A session's write: new bytes under a new mtime, and the reload the panel's poll would ask for. */
const reload = async (page: any, text: string, mtime: string): Promise<void> => {
  const before = await counts(page);
  await page.evaluate(([p, t, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = t; w.__mtime = m; w.__seam.reload(); }, [REPORT, text, mtime]);
  await page.waitForFunction((n: number) => (window as any).__fetches > n, before.fetches, { timeout: 10000 });
  await frames(page, 2);
};
const result = (page: any): Promise<{ copied: string[]; clicks: number; label: string; copiedClass: boolean; active: string }> => page.evaluate(() => {
  const w = window as any; const a = document.activeElement as HTMLElement | null;
  return { copied: w.__copied.slice(), clicks: w.__clicks, label: w.__pressed.textContent, copiedClass: w.__pressed.classList.contains("copied"), active: a ? a.className || a.tagName : "" };
});

for (const mode of ["pane", "chat"] as Mode[]) {
  test(`in a browser (${mode}): a Space held on Copy that a reload lands under still copies, the text the reader pressed on, and the new bytes are on screen`, { timeout: 180000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: DOC1 } });
      await arm(page);
      assert.equal((await result(page)).active, "code-copy", "the fence's Copy has focus");
      await page.keyboard.down("Space"); await frames(page, 1);
      const pressed = await counts(page);
      await reload(page, DOC2, MT2);
      await page.keyboard.up("Space"); await frames(page, 2);
      const after = await result(page);
      assert.equal(after.copied.length, 1, "the key press copied once: Copy acts on the Space keydown (code-block.ts addCopyBtn), before any landing can take the button");
      assert.equal(after.copied[0].trimEnd(), FENCE1, "the text the reader pressed on, not the write's");
      assert.equal(after.label, "Copied", "and the button acknowledged");
      assert.equal(after.copiedClass, true);
      const shown = await page.evaluate(() => { const w = window as any; return { mt: w.__seam.mtimeNs(), intro: (document.querySelector(".fileview-md p")!.textContent || "").trim(), code: (document.querySelector(".fileview-md pre code")!.textContent || "").trimEnd(), oldGone: !document.contains(w.__pressed), paints: w.__paints }; });
      assert.equal(shown.mt, MT2, "the reload landed");
      assert.equal(shown.intro, "An intro paragraph before the fence, rewritten by a session.", "the new bytes are on screen");
      assert.equal(shown.code, FENCE2.replace(/\n/g, ""), "the fence too (the rows drop the newlines)");
      assert.equal(shown.oldGone, true, "the pressed button went with the old body");
      assert.equal(shown.paints, pressed.paints + 1, "one paint for the one landing: a key holds nothing, the activation was already done");
      assert.deepEqual(errors, [], "no script error");
      await page.close();
    });
  });
}

test("in a browser: Space copies exactly once (nothing more off the keyup), a held key's repeats copy nothing more, and Enter still copies once", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: DOC1 } });
    // (a) one Space press: the keydown copies, the keyup adds nothing
    await arm(page);
    await page.keyboard.down("Space"); await frames(page, 1);
    const atKeydown = await result(page);
    assert.equal(atKeydown.copied.length, 1, "(a) the keydown copied");
    await page.keyboard.up("Space"); await frames(page, 2);
    const afterA = await result(page);
    assert.equal(afterA.copied.length, 1, "(a) the keyup copied nothing more: the key's default was prevented, so the button was never :active for it");
    assert.equal(afterA.clicks, 0, "(a) and no click was dispatched for the key");
    assert.equal(afterA.label, "Copied");
    // (b) a held Space repeats its keydown: one copy
    await page.evaluate(() => { const w = window as any; w.__copied = []; w.__pressed.textContent = "Copy"; w.__pressed.classList.remove("copied"); });
    await page.keyboard.down("Space"); await page.keyboard.down("Space"); await page.keyboard.down("Space"); await frames(page, 1);
    await page.keyboard.up("Space"); await frames(page, 2);
    assert.equal((await result(page)).copied.length, 1, "(b) three keydowns of a held key (the second and third repeats) copied once");
    // (c) Enter: the native click on the keydown, one copy, unchanged
    await page.evaluate(() => { const w = window as any; w.__copied = []; w.__clicks = 0; });
    await page.keyboard.press("Enter"); await frames(page, 2);
    const afterC = await result(page);
    assert.equal(afterC.copied.length, 1, "(c) Enter copied once");
    assert.equal(afterC.clicks, 1, "(c) through the button's own click");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
