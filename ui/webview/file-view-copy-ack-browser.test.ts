// The Copied acknowledgement reaches the button ON SCREEN when a reload's landing swaps the fence out around the press
// (review of Slice 3 of plans/markdown-viewer.md, round 3, 2026-09-09). The landing a press holds (actions.ts pressHold)
// runs on a zero timer right after the release's click and rebuilds the body wholesale (file-view.ts renderBody), so the
// pressed Copy button is out of the document a tick after its click. The label change is Copy's acknowledgement (no
// flash() on it; the build note), and it was written to the button the click closed over: with the async Clipboard API
// (a secure context: the dashboard on localhost) the write answers after the swap, so Copied went to a detached node and
// the button on screen never changed; with the execCommand fallback (an insecure origin) it answers in a microtask, so
// Copied showed for a frame and the swap wiped it. The copy itself succeeded both ways, so the reader had a silent
// success and every reason to click again (ui/CLAUDE.md, always acknowledge). code-block.ts writes the acknowledgement
// to the button at the fence's POSITION under the nearest ancestor the swap left in place, and follows it across a swap
// inside the window on the swap's own event (a MutationObserver on the ancestors' child lists, alive for the window).
// The button is the one of the fence with the pressed fence's SOURCE (the final fixes after round 3: round 3 read the
// fence's index, which a fence inserted above shifted), so every write here rewrites the prose and keeps the fence; a
// write that rewrites or removes the fence acknowledges nothing (file-view-copy-held-browser.test.ts scenes 1, 5 and 6).
// Three scenes over the real viewer (real-viewer-leg.ts): (1) the real Clipboard API on a secure origin (localhost, the
// clipboard permissions granted), the pane: mousedown on Copy, the reload lands parked, mouseup: the clipboard holds the
// text the reader pressed on, the button on screen after the swap reads Copied, and the window's close resets THAT button;
// (2) the fallback path on the leg's insecure origin, the pane and the chat modal: the same press, the button on screen
// after the swap reads Copied, a second landing inside the window carries it to the newest button, and a landing whose
// note has no fence leaves nothing to write on and throws nothing. The secure scene opens its own page: openViewer opens
// on ORIGIN, where no Clipboard API exists. Skips LOUDLY without a playwright browser (CI installs none), as the other
// legs do. Synthetic values only: an invented note, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, pageHtml, frames, paintsReach, REPORT, SID, MT2, type Mode } from "./real-viewer-leg";

const F = "```";
const FENCE1 = "# a comment\ndef f(x):\n    return x + 1";
const note = (intro: string, fence: string): string => ["# Report", "", intro, "", F + "python", fence, F, "", "A paragraph after the fence.", ""].join("\n");
const INTRO2 = "An intro paragraph before the fence, rewritten by a session.";
const INTRO3 = "An intro paragraph before the fence, rewritten twice.";
const DOC1 = note("An intro paragraph before the fence.", FENCE1);
const DOC2 = note(INTRO2, FENCE1);   // the prose rewritten, the fence kept (header)
const DOC3 = note(INTRO3, FENCE1);
const DOC_NO_FENCE = ["# Report", "", "A rewrite with no fence in it.", ""].join("\n");
const MT3 = "1757145600000000019";
const MT4 = "1757145600000000029";
const SECURE = "http://localhost:8765";   // a secure context, where the async Clipboard API exists (the dashboard's case)
const BTN = ".fileview-md pre > .code-copy";

const centre = (page: any, sel: string): Promise<{ x: number; y: number }> => page.evaluate((s: string) => {
  const r = document.querySelector(s)!.getBoundingClientRect();
  return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
}, sel);
const counts = (page: any): Promise<{ fetches: number; paints: number }> => page.evaluate(() => ({ fetches: (window as any).__fetches, paints: (window as any).__paints }));
/** A session's write: new bytes under a new mtime, and the reload the panel's poll would ask for. */
const reload = async (page: any, text: string, mtime: string): Promise<void> => {
  const before = await counts(page);
  await page.evaluate(([p, t, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = t; w.__mtime = m; w.__seam.reload(); }, [REPORT, text, mtime]);
  await page.waitForFunction((n: number) => (window as any).__fetches > n, before.fetches, { timeout: 10000 });
  await frames(page, 2);
};
/** The button on screen at the fence, its label and class, whether it is the pressed one and whether the pressed one is still in the document. */
type Shown = { label: string | null; copied: boolean; isPressed: boolean; pressedConnected: boolean; pressedLabel: string | null };
const shown = (page: any): Promise<Shown> => page.evaluate((sel: string) => {
  const w = window as any; const b = document.querySelector(sel) as HTMLElement | null;
  return { label: b ? b.textContent : null, copied: !!b && b.classList.contains("copied"), isPressed: b === w.__pressed, pressedConnected: w.__pressed.isConnected, pressedLabel: w.__pressed.textContent };
}, BTN);

/** The pane on the secure origin, the clipboard permissions granted, the report open and painted: openViewer's steps on
 *  a context of our own (permissions live on a context, and the real Clipboard API needs a secure origin). */
async function openSecure(browser: any): Promise<{ page: any; ctx: any; errors: string[] }> {
  const ctx = await browser.newContext({ viewport: { width: 900, height: 700 }, permissions: ["clipboard-read", "clipboard-write"] });
  const page = await ctx.newPage();
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: DOC1 });
  await page.route((u: URL) => u.href.startsWith(SECURE), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(SECURE + "/");
  await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await frames(page, 2);
  return { page, ctx, errors };
}

test("in a browser (the real Clipboard API, a secure origin): after a held landing the button on screen reads Copied, and the window's close resets that button", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, ctx, errors } = await openSecure(browser);
    // the premise, checked rather than assumed: a secure context with the async API, which answers after a round trip
    const env = await page.evaluate(() => ({ secure: window.isSecureContext, api: !!(navigator.clipboard && navigator.clipboard.writeText) }));
    assert.deepEqual(env, { secure: true, api: true }, "localhost is a secure context and carries the async Clipboard API (the dashboard's case)");
    // count the real API's writes and their settling (the real method, kept and called through), remember the pressed button
    await page.evaluate(() => {
      const w = window as any; w.__writes = 0; w.__settled = 0;
      const real = navigator.clipboard; const write = real.writeText.bind(real); const read = real.readText.bind(real);
      Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: (s: string) => { w.__writes++; return write(s).then(() => { w.__settled++; }); }, readText: read } });
      w.__pressed = document.querySelector(".fileview-md pre > .code-copy");
    });
    const b = await centre(page, BTN);
    await page.mouse.move(b.x, b.y); await frames(page, 1);
    await page.mouse.down(); await frames(page, 1);
    const pressed = await counts(page);
    await reload(page, DOC2, MT2);
    assert.equal((await counts(page)).paints, pressed.paints, "the landing waits under the press");
    await page.mouse.up();
    await page.waitForFunction(() => (window as any).__settled >= 1, null, { timeout: 10000 });   // the clipboard answered
    await paintsReach(page, pressed.paints + 1);                                                    // and the landing painted
    await frames(page, 1);                                                                          // the continuation ran before this frame
    const clip = await page.evaluate(() => navigator.clipboard.readText());
    assert.equal(clip.trimEnd(), FENCE1, "the clipboard holds the text the reader pressed on");
    assert.equal(await page.evaluate(() => (window as any).__writes), 1, "one write");
    const after = await shown(page);
    assert.equal(after.pressedConnected, false, "the pressed button went with the old body");
    assert.equal(after.isPressed, false, "a new button stands at the fence");
    assert.equal(after.label, "Copied", "the acknowledgement is on the button on screen: the clipboard answered after the swap, so it is written to the button at the fence's position under the ancestor the swap kept, not to the pressed node (code-block.ts acknowledge)");
    assert.equal(after.copied, true, "with the copied class");
    assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT2, "over the new bytes");
    assert.equal(await page.evaluate(() => (document.querySelector(".fileview-md p")!.textContent || "").trim()), INTRO2, "the write's prose is on screen: the swap happened");
    // the window closes on the button it acknowledged: the one on screen
    await page.waitForFunction((sel: string) => document.querySelector(sel)!.textContent === "Copy", BTN, { timeout: 5000 }).catch(() => null);
    const reset = await shown(page);
    assert.equal(reset.label, "Copy", "the window's close reset the button on screen (a reset on the detached node would leave Copied standing)");
    assert.equal(reset.copied, false, "and took the class off it");
    assert.deepEqual(errors, [], "no script error");
    await page.close(); await ctx.close();
  });
});

for (const mode of ["pane", "chat"] as Mode[]) {
  test(`in a browser (${mode}, the execCommand fallback): after a held landing the button on screen reads Copied, a second landing carries it, a fence-less landing leaves nothing to write on`, { timeout: 180000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: DOC1 } });
      // the premise: no async API on this origin, so copyText takes the fallback, which answers in a microtask; record its calls
      await page.evaluate(() => {
        const w = window as any; w.__exec = []; w.__api = !!(navigator.clipboard && navigator.clipboard.writeText);
        const real = document.execCommand.bind(document);
        document.execCommand = (cmd: string, ui?: boolean, val?: string) => { const ok = real(cmd, ui, val); w.__exec.push({ cmd, ok }); return ok; };
        w.__pressed = document.querySelector(".fileview-md pre > .code-copy");
      });
      assert.equal(await page.evaluate(() => (window as any).__api), false, "the leg's origin is not a secure context: the fallback path is the one that runs");
      const b = await centre(page, BTN);
      await page.mouse.move(b.x, b.y); await frames(page, 1);
      await page.mouse.down(); await frames(page, 1);
      const pressed = await counts(page);
      await reload(page, DOC2, MT2);
      assert.equal((await counts(page)).paints, pressed.paints, "the landing waits under the press");
      await page.mouse.up();
      await paintsReach(page, pressed.paints + 1);
      await frames(page, 2);
      const exec = await page.evaluate(() => (window as any).__exec.slice());
      assert.deepEqual(exec, [{ cmd: "copy", ok: true }], "the press copied once, through execCommand");
      const after = await shown(page);
      assert.equal(after.pressedConnected, false, "the pressed button went with the old body");
      assert.equal(after.label, "Copied", "the acknowledgement written to the pressed button a frame before the swap followed the fence to the button that replaced it (code-block.ts acknowledge, on the swap's own event)");
      assert.equal(after.copied, true, "with the copied class");
      // a second landing inside the window (no press: it paints at once): the acknowledgement stands at the fence's position
      await reload(page, DOC3, MT3);
      await paintsReach(page, pressed.paints + 2);
      const again = await shown(page);
      assert.equal(again.label, "Copied", "the newest button of the fence carries the acknowledgement for the rest of the window: the fence's source is what is acknowledged, not a node");
      assert.equal(await page.evaluate(() => (document.querySelector(".fileview-md p")!.textContent || "").trim()), INTRO3, "over the second write's bytes");
      await page.evaluate((sel: string) => { (window as any).__last = document.querySelector(sel); }, BTN);   // the button the window will close on
      // a landing whose note has no fence: nothing to write on, nothing thrown, and the window closes on the button it last acknowledged
      await reload(page, DOC_NO_FENCE, MT4);
      await paintsReach(page, pressed.paints + 3);
      assert.equal(await page.evaluate(() => document.querySelectorAll(".fileview-md pre").length), 0, "no fence on screen");
      await page.waitForFunction(() => (window as any).__last.textContent === "Copy", null, { timeout: 5000 }).catch(() => null);
      assert.equal(await page.evaluate(() => (window as any).__last.textContent), "Copy", "the window's close reset the button it last acknowledged (detached by then; a detached node takes the write)");
      assert.deepEqual(errors, [], "no script error: a fence that left the note is nothing to acknowledge on");
      await page.close();
    });
  });
}
