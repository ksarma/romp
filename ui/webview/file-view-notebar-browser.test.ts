// The viewer's notice bar survives the body's scroll and a swap of the body's children, in headless Chromium over the
// REAL module (plans/markdown-viewer.md, Slice 2). Before this slice noteBar (file-view.ts) prepended #fileview-save-err
// INTO .fileview-body, so it scrolled away with the text (at scrollTop 400 it sat 400px above the body's top), went with
// the next body.replaceChildren (a Rendered/Raw switch, a reload), and the "past the end" notice scrollToLine raises was
// never seen at all: the row it lands on is scrolled into view AFTER the notice is prepended, which puts the notice 6700px
// above the body's top (the slice's gap analysis, executed 2026-09-08). The bar is now a child of the card between the
// title bar and .fileview-main (box.insertBefore(bar2, main)), so it shows at any scroll position and outlives every
// swap; the editor's entry and exit remove it themselves. Two notices are driven here: the past-the-end notice of an
// open at a line the file lacks, and the Edit refusal the seam's setEditBlocked raises on a click; the third leg drives
// the changed-on-disk bar (plans/markdown-viewer.md Slice 6, item 5): a `focus` on the window runs the viewer's HEAD of
// the file (the page's stub answers a HEAD with the headers alone, `window.__heads` counting them), a moved mtime raises
// the bar with its Reload, the Reload's landing keeps the top block and clears it, and with the Comments panel open the
// panel's own poll reloads and clears it. A real `page.bringToFront` fires no window focus event in headless Chromium
// (measured while writing the leg: the page reports hasFocus() true throughout), so the leg dispatches the event the
// browser would. Legs await frames, paint counts and DOM mutations, never a timer. Skips LOUDLY without a playwright
// browser (CI installs none), as the other browser legs do. Synthetic values only: an invented report, /repo/notes-api
// paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, pageHtml, frames, paintsReach, topBlock, LONG, LONG2, rewritten, ORIGIN, REPORT, SID, MT, MT2 } from "./real-viewer-leg";

const MT3 = "1757145600000000012";
const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);

type Bar = { present: boolean; text: string; parent: string; before: string | null; inCard: boolean; aboveRow: boolean; inViewport: boolean; bodyScrollTop: number };
/** Where the notice bar is: its parent, the sibling after it, whether its box lies inside the card, above the body row, in the viewport. */
function readBar(): Bar {
  const bar = document.getElementById("fileview-save-err");
  const body = document.querySelector(".fileview-body") as HTMLElement;
  if (!bar) return { present: false, text: "", parent: "", before: null, inCard: false, aboveRow: false, inViewport: false, bodyScrollTop: body.scrollTop };
  const r = bar.getBoundingClientRect(), card = document.querySelector(".fileview")!.getBoundingClientRect(), main = document.querySelector(".fileview-main")!.getBoundingClientRect();
  return {
    present: true, text: bar.textContent || "", parent: (bar.parentElement as HTMLElement).className, before: bar.nextElementSibling ? (bar.nextElementSibling as HTMLElement).className : null,
    inCard: r.top >= card.top - 0.5 && r.bottom <= card.bottom + 0.5 && r.left >= card.left - 0.5 && r.right <= card.right + 0.5,
    aboveRow: r.bottom <= main.top + 0.5 && r.height > 0,
    inViewport: r.top >= 0 && r.bottom <= innerHeight && r.height > 0,
    bodyScrollTop: body.scrollTop,
  };
}

test("in a browser, the real module: a line past the end raises a notice that is SEEN: above the body row, in the card and the viewport, still there after the body scrolls and after a Rendered/Raw switch; pane and chat", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as const) {
      const { page, errors } = await openViewer(browser, mode, 700, 600, { raw: true, openOpts: { at: { line: 9999 } } });   // the open's `at` (Slice 6 of plans/markdown-viewer.md; the former `line` option)
      let b: Bar = await page.evaluate(readBar);
      assert.ok(b.present, mode + ": the past-the-end notice is up");
      assert.equal(b.text, "Line 9999 is past the end of this file, which has 201 lines; showing the last line.", mode + ": in the viewer's words");
      assert.equal(b.parent, "fileview", mode + ": a child of the card, not of the body");
      assert.equal(b.before, "fileview-main", mode + ": right above the body row");
      assert.ok(b.aboveRow && b.inCard, mode + ": its box sits above the row, inside the card");
      assert.ok(b.inViewport, mode + ": and on screen, though the body was scrolled to its last row (before the slice the notice sat 6700px above the body's top)");
      assert.ok(b.bodyScrollTop > 1000, mode + ": the body is scrolled far down: " + b.bodyScrollTop);
      // the body scrolls: the notice stays where it is
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 400; });
      await frames(page, 2);
      b = await page.evaluate(readBar);
      assert.ok(b.present && b.inViewport && b.aboveRow, mode + ": at scrollTop 400 the notice is still on screen above the row (before: 400px above the body's top)");
      // the body's children are swapped: the notice outlives the swap
      await page.locator("#romp-fileview .fileview-btn", { hasText: /^Rendered$/ }).click();
      await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 5000 });
      await frames(page, 2);
      b = await page.evaluate(readBar);
      assert.ok(b.present, mode + ": the notice outlives the Rendered swap (before: gone with body.replaceChildren)");
      assert.equal(b.text, "Line 9999 is past the end of this file, which has 201 lines; showing the last line.", mode + ": with its words");
      assert.ok(b.inViewport && b.aboveRow, mode + ": still above the row, on screen");
      await page.locator("#romp-fileview .fileview-btn", { hasText: /^Raw$/ }).click();
      await page.waitForFunction(() => !!document.querySelector(".fileview-body .fv-cl"), null, { timeout: 5000 });
      await frames(page, 2);
      b = await page.evaluate(readBar);
      assert.ok(b.present && b.inViewport, mode + ": and the Raw swap");
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: the Edit refusal is a notice above the body row at any scroll position; a second notice replaces the first; a reload keeps it; pane and chat", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as const) {
      const { page, errors } = await openViewer(browser, mode, 700, 600);
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 1500; });
      await frames(page, 2);
      await page.evaluate(() => { (window as any).__seam.setEditBlocked("Edit is off here while 2 changes are pending in this file."); });
      await page.locator("#romp-fileview .fileview-btn", { hasText: /^Edit$/ }).click();
      await frames(page, 2);
      let b: Bar = await page.evaluate(readBar);
      assert.ok(b.present, mode + ": the refusal is up");
      assert.equal(b.text, "Edit is off here while 2 changes are pending in this file.", mode + ": in the seam's words");
      assert.equal(b.parent, "fileview", mode + ": a child of the card, not of the body");
      assert.equal(b.before, "fileview-main", mode + ": right above the body row");
      assert.ok(b.aboveRow && b.inCard && b.inViewport, mode + ": above the row, in the card, on screen, with the body scrolled to 1500");
      assert.equal(b.bodyScrollTop, 1500, mode + ": the body did not move for it");
      await page.evaluate(() => { (window as any).__seam.setEditBlocked("Edit is off here while 3 changes are pending in this file."); });
      await page.locator("#romp-fileview .fileview-btn", { hasText: /^Edit$/ }).click();
      await frames(page, 2);
      b = await page.evaluate(readBar);
      assert.equal(b.text, "Edit is off here while 3 changes are pending in this file.", mode + ": one notice at a time: the newer replaced the older");
      assert.equal(await page.evaluate(() => document.querySelectorAll("#fileview-save-err, .fileview > .fileview-err").length), 1, mode + ": exactly one bar in the card");
      const paints: number = await page.evaluate(() => (window as any).__paints);
      await page.evaluate(() => { (window as any).__seam.reload(); });
      await page.waitForFunction((k: number) => (window as any).__paints >= k, paints + 1, { timeout: 10000 });
      await frames(page, 2);
      b = await page.evaluate(readBar);
      assert.ok(b.present && b.inViewport && b.aboveRow, mode + ": a reload swaps the body's children and the notice stays above the row");
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

type Disk = { present: boolean; text: string; button: string | null; disabled: boolean; parent: string; before: string | null; inCard: boolean; aboveRow: boolean; inViewport: boolean; bodyScrollTop: number; heads: number; bars: number };
/** The changed-on-disk bar as laid out: its own words (the bar's text nodes; the button's label is a child), its one button
 *  and that button's state, its place in the card (readBar's geometry), the body's scrollTop, the HEAD count. */
function readDisk(): Disk {
  const w = window as any;
  const bar = document.getElementById("fileview-save-err");
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const bars = document.querySelectorAll("#fileview-save-err, .fileview > .fileview-err").length;
  if (!bar) return { present: false, text: "", button: null, disabled: false, parent: "", before: null, inCard: false, aboveRow: false, inViewport: false, bodyScrollTop: body.scrollTop, heads: w.__heads, bars };
  const btn = bar.querySelector("button");
  const r = bar.getBoundingClientRect(), card = document.querySelector(".fileview")!.getBoundingClientRect(), main = document.querySelector(".fileview-main")!.getBoundingClientRect();
  return {
    present: true, text: Array.from(bar.childNodes).filter((n) => n.nodeType === 3).map((n) => n.textContent || "").join(""),
    button: btn ? btn.textContent : null, disabled: !!(btn && btn.disabled),
    parent: (bar.parentElement as HTMLElement).className, before: bar.nextElementSibling ? (bar.nextElementSibling as HTMLElement).className : null,
    inCard: r.top >= card.top - 0.5 && r.bottom <= card.bottom + 0.5 && r.left >= card.left - 0.5 && r.right <= card.right + 0.5,
    aboveRow: r.bottom <= main.top + 0.5 && r.height > 0,
    inViewport: r.top >= 0 && r.bottom <= innerHeight && r.height > 0,
    bodyScrollTop: body.scrollTop, heads: w.__heads, bars,
  };
}

test("in a browser, the real module: a window focus runs one HEAD and the same mtime raises nothing; a moved mtime on the next focus raises the changed-on-disk bar above the body row at scrollTop 400, its words and Reload, no bytes fetched; Reload swaps the body with the top block kept and the bar gone; with the Comments panel open the bar shows and the panel's poll's reload clears it; pane at 700 and 380px and the chat modal", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width] of [["pane", 700], ["pane", 380], ["chat", 700]] as const) {
      const cell = `${mode} ${width}px`;
      const { page, errors } = await openViewer(browser, mode, width, 600);
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 400; });
      await frames(page, 2);
      const before = (await topBlock(page))!;
      assert.ok(before.top <= 0.5, cell + ": the scene starts with a block at the top edge at scrollTop 400: " + before.text);
      // the same mtime: one HEAD, no bar
      let heads: number = await page.evaluate(() => (window as any).__heads);
      assert.equal(heads, 0, cell + ": the open sent no HEAD");
      await page.evaluate(() => { window.dispatchEvent(new Event("focus")); });
      await page.waitForFunction((n: number) => (window as any).__heads > n, heads, { timeout: 5000 });
      await frames(page, 2);
      let d: Disk = await page.evaluate(readDisk);
      assert.equal(d.heads, 1, cell + ": one HEAD for the focus");
      assert.equal(d.present, false, cell + ": the same mtime raises nothing");
      // the file moved: the next focus raises the bar
      const paints: number = await page.evaluate(() => (window as any).__paints);
      await page.evaluate(([p, text, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = text; w.__mtime = m; window.dispatchEvent(new Event("focus")); }, [REPORT, LONG2, MT2]);
      await page.waitForFunction(() => !!document.getElementById("fileview-save-err"), null, { timeout: 5000 });
      await frames(page, 2);
      d = await page.evaluate(readDisk);
      assert.equal(d.heads, 2, cell + ": one more HEAD, no second while it was out");
      assert.equal(d.text, "Changed on disk.", cell + ": the bar's words");
      assert.equal(d.button, "Reload", cell + ": and its button"); assert.equal(d.disabled, false, cell + ": armed");
      assert.equal(d.bars, 1, cell + ": exactly one bar in the card");
      assert.equal(d.parent, "fileview", cell + ": a child of the card, not of the body");
      assert.equal(d.before, "fileview-main", cell + ": right above the body row");
      assert.ok(d.aboveRow && d.inCard && d.inViewport, cell + ": its box sits above the row, inside the card, on screen");
      assert.equal(d.bodyScrollTop, 400, cell + ": the body did not move for it");
      assert.equal(await page.evaluate(() => (window as any).__paints), paints, cell + ": nothing repainted: the probe fetched no bytes");
      assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT, cell + ": the view still shows the file the reader has");
      // Reload: the landing swaps the body with the top block kept (the reload's place rule) and takes the bar
      await page.locator("#fileview-save-err button", { hasText: /^Reload$/ }).click();
      await paintsReach(page, paints + 1);
      await frames(page, 2);
      d = await page.evaluate(readDisk);
      assert.equal(d.present, false, cell + ": the landing took the bar");
      assert.equal(d.bars, 0, cell + ": no bar left in the card");
      assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT2, cell + ": the reload landed the new bytes");
      const after = (await topBlock(page))!;
      assert.equal(after.text, before.text, cell + ": the top block is kept (before the slice a reload started the reader over)");
      near(after.top, before.top, cell + ": at its height");
      assert.ok(after.scrollTop > before.scrollTop, cell + `: the scrollTop moved on by the inserted text (${before.scrollTop} to ${after.scrollTop}); the passage did not`);
      // the Comments panel open: the probe still asks, the bar shows, and the panel's own poll reloads the file and clears it.
      // The bar is read by a MutationObserver on the card (a microtask, before any poll tick can land a reload), so the
      // reading cannot race the clearing; the clearing is awaited as the DOM event it is.
      await openPanel(page);
      const seen: { text: string; button: string | null; scrollTop: number } = await page.evaluate(([p, text, m]: [string, string, string]) => new Promise((resolve, reject) => {
        const card = document.querySelector(".fileview")!;
        const body = document.querySelector(".fileview-body") as HTMLElement;
        let frames = 0;
        const mo = new MutationObserver((recs) => {
          for (const r of recs) for (const n of Array.from(r.addedNodes)) if (n instanceof HTMLElement && n.id === "fileview-save-err") {
            mo.disconnect();
            const btn = n.querySelector("button");
            resolve({ text: Array.from(n.childNodes).filter((x) => x.nodeType === 3).map((x) => x.textContent || "").join(""), button: btn ? btn.textContent : null, scrollTop: body.scrollTop });
            return;
          }
        });
        mo.observe(card, { childList: true });
        const cap = () => { if (++frames > 600) { mo.disconnect(); reject(new Error("no bar within 600 frames")); return; } requestAnimationFrame(cap); };
        cap();
        const w = window as any; w.__docs[p] = text; w.__mtime = m; window.dispatchEvent(new Event("focus"));
      }), [REPORT, rewritten(60, true), MT3]);   // a paragraph far below the top block rewritten, so the kept block is the same one
      assert.equal(seen.text, "Changed on disk.", cell + ": the bar shows with the panel open too (the probe does not stand down for the poll)");
      assert.equal(seen.button, "Reload", cell + ": with its button");
      await page.waitForFunction(() => !document.getElementById("fileview-save-err"), null, { timeout: 15000 });
      await frames(page, 2);
      assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT3, cell + ": the panel's poll reloaded the file and that landing cleared the bar");
      const kept = (await topBlock(page))!;
      assert.equal(kept.text, after.text, cell + ": the top block kept through the poll's reload as well");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

// ── the review's round 1: the keyboard around the changed-on-disk bar and the editor's exit ──────────────────────────────
const MT4 = "1757145600000000025";
const activeName = (page: any): Promise<string> => page.evaluate(() => { const a = document.activeElement as HTMLElement | null; return a ? a.tagName + "." + String(a.className).split(/\s+/).filter(Boolean).join(".") : "none"; });
/** Press PageDown and wait for the body's scrollTop to pass `from`; false when it never does (Chromium may animate the scroll). */
const pageDownMoves = (page: any, from: number): Promise<boolean> => page.keyboard.press("PageDown").then(() => page.waitForFunction((v: number) => (document.querySelector(".fileview-body") as HTMLElement).scrollTop > v, from, { timeout: 3000 }).then(() => true, () => false));
const scrollTopOf = (page: any): Promise<number> => page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
/** Move the file on disk and dispatch the window focus that runs the HEAD; wait for the bar. */
async function raiseBar(page: any, text: string, mtime: string): Promise<void> {
  await page.evaluate(([p, t, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = t; w.__mtime = m; window.dispatchEvent(new Event("focus")); }, [REPORT, text, mtime]);
  await page.waitForFunction(() => !!document.querySelector("#fileview-save-err button"), null, { timeout: 5000 });
  await frames(page, 1);
}
const BODY_EL = "DIV.fileview-body";

test("in a browser, the real module (review round 1): the Reload's click disables the button and the browser drops the focus off it at once, so the landing hands the keyboard to the body from the holder read AT THE CLICK, and PageDown scrolls (before: read at the landing, the hand-over never fired, and PageDown after every Reload scrolled nothing); Enter on the focused button the same; a failed Reload puts the keyboard back on the re-armed button; pane at 700 px and the chat modal", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as const) {
      const cell = mode + " 700px";
      const { page, errors } = await openViewer(browser, mode, 700, 600);
      // Chromium's rule, read on this page: a focused button that is disabled loses the focus synchronously
      const rule = await page.evaluate(() => { const b = document.createElement("button"); b.textContent = "t"; document.body.appendChild(b); b.focus(); const before = document.activeElement === b; b.disabled = true; const after = document.activeElement === b; b.remove(); return { before, after }; });
      assert.deepEqual(rule, { before: true, after: false }, cell + ": the browser drops the focus off a control the moment it is disabled");
      // a mouse click on Reload: the landing hands the keyboard to the body
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 300; });
      await raiseBar(page, LONG2, MT2);
      let paints: number = await page.evaluate(() => (window as any).__paints);
      await page.locator("#fileview-save-err button", { hasText: /^Reload$/ }).click();
      await paintsReach(page, paints + 1); await frames(page, 3);
      assert.equal(await page.evaluate(() => !!document.getElementById("fileview-save-err")), false, cell + ": the landing took the bar");
      assert.equal(await activeName(page), BODY_EL, cell + ": the body holds the keyboard after the Reload's landing (before the fix: the document's body)");
      let from = await scrollTopOf(page);
      assert.equal(await pageDownMoves(page, from), true, cell + ": PageDown scrolls the note after the Reload");
      // the keyboard path: the button focused (a Tab's outcome), Enter
      await raiseBar(page, rewritten(60, true), MT3);
      await page.evaluate(() => { (document.querySelector("#fileview-save-err button") as HTMLElement).focus(); });
      assert.equal(await activeName(page), "BUTTON.fileview-btn.fileview-err-dl", cell + ": the button holds the keyboard before Enter");
      paints = await page.evaluate(() => (window as any).__paints);
      await page.keyboard.press("Enter");
      await paintsReach(page, paints + 1); await frames(page, 3);
      assert.equal(await activeName(page), BODY_EL, cell + ": the body holds the keyboard after Enter's Reload");
      from = await scrollTopOf(page);
      assert.equal(await pageDownMoves(page, from), true, cell + ": PageDown scrolls the note after Enter's Reload");
      // a failed Reload: the file is gone by the time the GET runs; the button is re-armed and holds the keyboard again
      await raiseBar(page, rewritten(61, true), MT4);
      await page.evaluate((p: string) => { delete (window as any).__docs[p]; }, REPORT);
      await page.locator("#fileview-save-err button", { hasText: /^Reload$/ }).click();
      await page.waitForFunction(() => !!document.querySelector(".fileview-body .fileview-err"), null, { timeout: 5000 });
      await frames(page, 2);
      const failed = await page.evaluate(() => { const b = document.querySelector("#fileview-save-err button") as HTMLButtonElement | null; return { bar: !!b, disabled: b ? b.disabled : null, text: b ? b.textContent : null, active: document.activeElement === b }; });
      assert.deepEqual(failed, { bar: true, disabled: false, text: "Reload", active: true }, cell + ": the bar stands with its button re-armed and holding the keyboard (before the fix: the document's body held it)");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module (review round 1): with the changed-on-disk bar up, Edit takes it with the other notices and Cancel brings it back at once with no HEAD (before: the old text came back with no line above it until the next focus), and the exit's repaint hands the keyboard to the body so PageDown scrolls; pane at 700 px", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 700, 600);
    await raiseBar(page, LONG2, MT2);
    const heads0: number = await page.evaluate(() => (window as any).__heads);
    await page.locator("#romp-fileview .fileview-btn", { hasText: /^Edit$/ }).click();
    await page.waitForFunction(() => !!document.querySelector(".fileview-editor, .fileview-cm"), null, { timeout: 5000 });
    await frames(page, 2);
    const inEdit: Disk = await page.evaluate(readDisk);
    assert.notEqual(inEdit.text, "Changed on disk.", "the editor's entry took the bar (its own notice, or none, stands)");
    await page.locator("#romp-fileview .fileview-btn", { hasText: /^Cancel$/ }).click();
    await page.waitForFunction(() => !document.querySelector(".fileview-editor, .fileview-cm") && !!document.querySelector(".fileview-body .fv-cl, .fileview-md > p"), null, { timeout: 5000 });
    await frames(page, 3);
    const back: Disk = await page.evaluate(readDisk);
    assert.equal(back.text, "Changed on disk.", "Cancel brings the bar back at once: the text that shows is still the file it was raised under");
    assert.equal(back.button, "Reload", "…with its Reload"); assert.equal(back.disabled, false, "…armed");
    assert.equal(back.bars, 1, "one bar in the card");
    assert.equal(back.heads, heads0, "…and no HEAD was sent for it (nothing new is known; the next focus asks)");
    assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT, "the view still shows the file the reader had");
    assert.equal(await activeName(page), BODY_EL, "the exit's repaint gave the body the keyboard (before: the document's body, and PageDown scrolled nothing until a click)");
    assert.equal(await pageDownMoves(page, await scrollTopOf(page)), true, "PageDown scrolls the note after Cancel");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real module (review round 1): a relayed open into a Files iframe that did not hold the page's focus sends the open's GET and no HEAD (before: the landing's body.focus() moved the focus into the frame, its window fired `focus`, and the probe answered with a HEAD of the file it had just fetched); the probe is live for the next focus; a same-frame open sends one GET as before", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // a shell stand-in: a chat iframe holding a composer, and the Files pane's page (real-viewer-leg's, body.fileview-pane) beside it
    const chat = '<!DOCTYPE html><html><body style="margin:8px"><textarea id="composer-input"></textarea><p>chat pane stand-in</p></body></html>';
    const top = `<!DOCTYPE html><html><body style="margin:0"><div id="shell" style="height:20px">shell stand-in</div><iframe id="a" src="${ORIGIN}/a" style="width:300px;height:560px"></iframe><iframe id="b" src="${ORIGIN}/b" style="width:660px;height:560px"></iframe></body></html>`;
    const files = pageHtml("pane", { [REPORT]: LONG }, MT);
    for (const holder of ["chat", "files"] as const) {
      const cell = holder === "chat" ? "the chat iframe holds the focus (a relay open)" : "the Files iframe holds the focus (a same-frame open)";
      const page = await browser.newPage({ viewport: { width: 1000, height: 600 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => {
        const path = new URL(route.request().url()).pathname;
        return route.fulfill({ status: 200, contentType: "text/html", body: path === "/a" ? chat : path === "/b" ? files : top });
      });
      await page.goto(ORIGIN + "/");
      const fa = page.frames().find((f: any) => f.url() === ORIGIN + "/a"), fb = page.frames().find((f: any) => f.url() === ORIGIN + "/b");
      assert.ok(fa && fb, cell + ": both iframes loaded");
      await fb.waitForFunction(() => typeof (window as any).FV !== "undefined", null, { timeout: 10000 });
      if (holder === "chat") await fa.click("#composer-input"); else await fb.click("body", { position: { x: 5, y: 5 } });
      const before = await fb.evaluate(() => ({ hasFocus: document.hasFocus(), heads: (window as any).__heads }));
      assert.equal(before.hasFocus, holder === "files", cell + ": the Files document " + (holder === "files" ? "holds" : "does not hold") + " the focus before the open");
      assert.equal(before.heads, 0, cell + ": no HEAD before the open");
      await fb.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
      await fb.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
      await frames(fb, 3);
      const after = await fb.evaluate(() => ({ heads: (window as any).__heads, active: (document.activeElement as HTMLElement).className, hasFocus: document.hasFocus(), bar: !!document.getElementById("fileview-save-err") }));
      assert.equal(after.active, "fileview-body", cell + ": the open's landing gave the body the keyboard");
      assert.equal(after.hasFocus, true, cell + ": …so the Files document holds the page's focus after the open");
      assert.equal(after.heads, 0, cell + ": the open sent no HEAD (before the fix a cross-frame open cost GET then HEAD: the window focus the viewer's own focus call fired read as the reader's return)");
      assert.equal(after.bar, false, cell + ": no bar");
      // the probe is live: the reader's return (a window focus) asks once
      await fb.evaluate(() => { window.dispatchEvent(new Event("focus")); });
      await fb.waitForFunction(() => (window as any).__heads > 0, null, { timeout: 5000 });
      assert.equal(await fb.evaluate(() => (window as any).__heads), 1, cell + ": one HEAD for the focus event");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});
