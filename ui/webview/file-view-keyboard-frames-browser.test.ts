// The keyboard rule across the dashboard's frames, in headless Chromium over the REAL viewer (plans/markdown-viewer.md Slice 6,
// item 1: the body takes the keyboard unless the composer holds it; the review's round 2). The shell frames the chat and the Files
// pane as sibling same-origin iframes, and the chat composer beside a Files iframe is the composer too: this document's
// activeElement is its own body whenever the page's focus is in the chat frame, so takeKeyboard's same-document gate saw nothing to
// yield to and body.focus() pulled the page's focus into the Files frame, out of a box being typed in. Three hand-overs did it: the
// relayed open's landing (a middle-click on a path pill keeps the composer focused through the gesture), the changed-on-disk bar's
// Reload landing after the reader moved to the composer during the GET's flight, and the editor's exit at a Save's ack; the
// failed Reload's re-arm focused its button from the composer the same way. Now the gate also reads the focused frame's own active
// element through the top window (typingInPeerFrame), a typing target there keeps the keyboard, and a non-typing holder there (the
// chat's body after a plain click) yields as the document's body does, so the body still takes the keyboard for the acceptance
// (PageDown with no prior click). A shell stand-in holds a chat iframe (a textarea composer and a plain paragraph) and the Files
// pane's page (real-viewer-leg's, body.fileview-pane) beside it; the Files frame's fetch stub is wrapped to hold a GET for the
// mid-flight scenes (released by the test, never a timer). Before the fix: red at the first composer read over a git archive of
// c88444f85. Skips LOUDLY without a playwright browser (CI installs none), as the other legs do. Synthetic values only: the
// notes-api world, the placeholder sid, an invented origin.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, pageHtml, frames, ORIGIN, REPORT, SID, MT, MT2, LONG, LONG2 } from "./real-viewer-leg";

const CHAT = '<!DOCTYPE html><html><body style="margin:8px"><textarea id="composer-input" style="width:260px;height:80px"></textarea><p id="plain">chat pane stand-in</p></body></html>';
const TOP = `<!DOCTYPE html><html><body style="margin:0"><div id="shell" style="height:20px">shell stand-in</div><iframe id="f-chat" src="${ORIGIN}/a" style="width:300px;height:560px"></iframe><iframe id="f-files" src="${ORIGIN}/b" style="width:660px;height:560px"></iframe></body></html>`;

type Mounted = { page: any; fa: any; fb: any; errors: string[] };
/** The shell stand-in with both frames loaded and the viewer module up in the Files frame; a keydown recorder there says where a key lands. */
async function mount(browser: any): Promise<Mounted> {
  const page = await browser.newPage({ viewport: { width: 1000, height: 600 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const files = pageHtml("pane", { [REPORT]: LONG }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => {
    const path = new URL(route.request().url()).pathname;
    return route.fulfill({ status: 200, contentType: "text/html", body: path === "/a" ? CHAT : path === "/b" ? files : TOP });
  });
  await page.goto(ORIGIN + "/");
  const fa = page.frames().find((f: any) => f.url() === ORIGIN + "/a"), fb = page.frames().find((f: any) => f.url() === ORIGIN + "/b");
  assert.ok(fa && fb, "both iframes loaded");
  await fb.waitForFunction(() => typeof (window as any).FV !== "undefined", null, { timeout: 10000 });
  await fb.evaluate(() => { const w = window as any; w.__keys = []; document.addEventListener("keydown", (e) => { const t = e.target as HTMLElement; w.__keys.push(e.key + "@" + (t.className || t.tagName)); }); });
  return { page, fa, fb, errors };
}
type Holder = { active: string; hasFocus: boolean };
/** A frame's active element (tag, id, classes) and whether its document holds the page's focus. */
const holder = (frame: any): Promise<Holder> => frame.evaluate(() => { const a = document.activeElement as HTMLElement | null; return { active: a ? a.tagName + (a.id ? "#" + a.id : "") + (a.className ? "." + String(a.className).split(/\s+/).filter(Boolean).join(".") : "") : "none", hasFocus: document.hasFocus() }; });
const topActive = (page: any): Promise<string> => page.evaluate(() => { const a = document.activeElement; return a ? a.tagName + "#" + a.id : "none"; });
const composer = (fa: any): Promise<string> => fa.evaluate(() => (document.getElementById("composer-input") as HTMLTextAreaElement).value);
const filesKeys = (fb: any): Promise<string[]> => fb.evaluate(() => (window as any).__keys);
const noteScrollTop = (fb: any): Promise<number> => fb.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
/** Open the report in the Files frame as the shell's relay does (openFileView with no target) and wait for its paint. */
async function openReport(fb: any): Promise<void> {
  await fb.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
  await fb.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await frames(fb, 3);
}
/** In the Files frame: every GET of a file (never a HEAD) waits until the test releases it; the page's stub then answers as before. */
const holdGets = (fb: any): Promise<void> => fb.evaluate(() => {
  const w = window as any; w.__origFetch = w.__origFetch || w.fetch; w.__release = null;
  const gate = new Promise<void>((r) => { w.__release = r; });
  w.fetch = async (u: string, i?: RequestInit) => { if (!(i && i.method === "HEAD") && /[?&]path=/.test(String(u))) await gate; return w.__origFetch(u, i); };
});
const releaseGets = (fb: any): Promise<void> => fb.evaluate(() => { const w = window as any; w.fetch = w.__origFetch; w.__release(); });
/** The file moved on disk (new text, new mtime) and the window's focus fires the probe's HEAD: the bar with its Reload is up. */
async function raiseBar(fb: any, text: string, mtime: string): Promise<void> {
  await fb.evaluate(([t, m, p]: [string, string, string]) => { const w = window as any; w.__docs[p] = t; w.__mtime = m; window.dispatchEvent(new Event("focus")); }, [text, mtime, REPORT]);
  await fb.waitForFunction(() => !!document.querySelector("#fileview-save-err button"), null, { timeout: 5000 });
  await frames(fb, 1);
}
type BarState = { bar: boolean; text: string | null; disabled: boolean | null; focused: boolean; errPane: boolean; gets: number };
const barState = (fb: any): Promise<BarState> => fb.evaluate(() => {
  const b = document.querySelector("#fileview-save-err button") as HTMLButtonElement | null; const w = window as any;
  return { bar: !!document.getElementById("fileview-save-err"), text: b ? b.textContent : null, disabled: b ? b.disabled : null, focused: !!b && document.activeElement === b, errPane: !!document.querySelector(".fileview-body .fileview-err"), gets: w.__fetches - w.__heads };
});
const COMPOSER = "TEXTAREA#composer-input", BODY = "DIV.fileview-body";

test("in a browser (review round 2): a relayed open into the Files iframe while the chat composer in the sibling iframe is being typed in leaves the composer holding the keyboard, the typed letters reaching it (before: the landing's body.focus() pulled the page's focus into the Files frame, the letters landed on the viewer body and Space scrolled the note); a non-typing holder in the chat frame yields, and the body takes the keyboard as designed; the Outline popover closed by a click into the composer leaves the composer holding it", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // the composer holds the keyboard: the relayed open leaves it there
    {
      const { page, fa, fb, errors } = await mount(browser);
      await fa.click("#composer-input"); await page.keyboard.type("ab");
      assert.equal((await holder(fa)).active, COMPOSER, "the composer holds the keyboard before the open");
      const heads0: number = await fb.evaluate(() => (window as any).__heads);
      await openReport(fb);
      const a = await holder(fa), b = await holder(fb);
      assert.equal(a.active, COMPOSER, "the composer still holds the keyboard after the relayed open (before the fix: the chat's BODY, the page's focus gone to the Files frame)");
      assert.equal(a.hasFocus, true, "…and the chat document holds the page's focus");
      assert.equal(b.hasFocus, false, "the Files document does not");
      assert.equal(await topActive(page), "IFRAME#f-chat", "the top window's active frame is the chat");
      assert.equal(await fb.evaluate(() => (window as any).__heads), heads0, "no HEAD: no focus call fired the window's focus");
      await page.keyboard.type("z");
      assert.equal(await composer(fa), "abz", "the typed letter reaches the composer (before: the viewer body)");
      assert.deepEqual(await filesKeys(fb), [], "nothing landed on the Files document");
      const st0 = await noteScrollTop(fb);
      await page.keyboard.press("Space"); await frames(fb, 2);
      assert.equal(await noteScrollTop(fb), st0, "Space scrolls no note");
      assert.equal(await composer(fa), "abz ", "…it types into the composer");
      // the body is a Tab stop still, and takes the keyboard on its own gesture
      await fb.click(".fileview-body", { position: { x: 20, y: 40 } }); await frames(fb, 1);
      assert.equal((await holder(fb)).active, BODY, "a click in the note lands the keyboard on the body (its tabindex stands)");
      assert.deepEqual(errors, [], "no page errors (the composer scene)");
      await page.close();
    }
    // a non-typing holder in the chat frame (a click on its text): the body takes the keyboard, as the design says
    {
      const { page, fa, fb, errors } = await mount(browser);
      await fa.click("#plain");
      assert.equal((await holder(fa)).active, "BODY", "the chat's body holds the focus after a plain click");
      await openReport(fb);
      const b = await holder(fb);
      assert.equal(b.active, BODY, "the body took the keyboard: a plain holder in the chat frame yields as the document's body does");
      assert.equal(b.hasFocus, true, "…so the Files document holds the page's focus");
      await page.keyboard.press("PageDown"); await frames(fb, 3);
      assert.ok((await noteScrollTop(fb)) > 0, "PageDown scrolls the note with no prior click (the acceptance)");
      assert.deepEqual(errors, [], "no page errors (the plain-holder scene)");
      await page.close();
    }
    // the Outline popover, open and holding the keyboard: a click into the composer closes it, and the composer keeps the keyboard
    // (the focusout's relatedTarget is null for a move into another frame, and this document's active element is already its body)
    {
      const { page, fa, fb, errors } = await mount(browser);
      await fb.click("body", { position: { x: 5, y: 5 } });
      await openReport(fb);
      await fb.click(".fileview-acts .fileview-outline-btn"); await frames(fb, 1);
      assert.equal((await holder(fb)).active, "DIV.fileview-outline", "the popover holds the keyboard when open");
      await fa.click("#composer-input"); await frames(fb, 2);
      const st = await fb.evaluate(() => ({ popover: !!document.querySelector(".fileview-outline"), expanded: (document.querySelector(".fileview-outline-btn") as HTMLElement).getAttribute("aria-expanded"), active: (document.activeElement as HTMLElement).tagName }));
      assert.deepEqual(st, { popover: false, expanded: "false", active: "BODY" }, "the popover closed, the button reads collapsed, and this document's active element is its body: nothing was handed over");
      assert.equal((await holder(fa)).active, COMPOSER, "the composer keeps the keyboard");
      await page.keyboard.type("q");
      assert.equal(await composer(fa), "q", "the next letter reaches it");
      assert.deepEqual(errors, [], "no page errors (the Outline scene)");
      await page.close();
    }
  });
});

test("in a browser (review round 2): the changed-on-disk bar's Reload clicked, then the composer in the chat iframe clicked and typed in during the GET's flight: the landing leaves the composer holding the keyboard (before: the click's record handed it to the body through a gate that saw this document alone, and the page's focus jumped into the Files frame mid-sentence); a Reload that fails re-arms its button without taking the keyboard (before: the re-armed button took the page's focus, and a Space fired Reload again); the editor's exit at a Save's ack leaves the composer holding it too", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // the Reload's landing
    {
      const { page, fa, fb, errors } = await mount(browser);
      await fb.click("body", { position: { x: 5, y: 5 } });
      await openReport(fb);
      await raiseBar(fb, LONG2, MT2);
      await holdGets(fb);
      await fb.click("#fileview-save-err button");
      const mid = await barState(fb);
      assert.equal(mid.text, "Reloading", "the click's acknowledgement"); assert.equal(mid.disabled, true);
      await fa.click("#composer-input"); await page.keyboard.type("ab");
      assert.equal((await holder(fa)).active, COMPOSER, "the reader moved to the composer during the flight");
      await releaseGets(fb);
      await fb.waitForFunction(() => !document.getElementById("fileview-save-err"), null, { timeout: 10000 }); await frames(fb, 3);
      const a = await holder(fa), b = await holder(fb);
      assert.equal(a.active, COMPOSER, "the composer holds the keyboard after the landing (before the fix: the chat's BODY)");
      assert.equal(a.hasFocus, true, "…and the chat document holds the page's focus"); assert.equal(b.hasFocus, false, "the Files document does not");
      await page.keyboard.type("z");
      assert.equal(await composer(fa), "abz", "the next letter reaches the composer (before: the viewer body)");
      assert.deepEqual(await filesKeys(fb), [], "nothing landed on the Files document");
      assert.equal(await fb.evaluate(() => (window as any).__seam.mtimeNs()), MT2, "the reload landed the moved file");
      assert.deepEqual(errors, [], "no page errors (the landing scene)");
      await page.close();
    }
    // the failed Reload's re-arm
    {
      const { page, fa, fb, errors } = await mount(browser);
      await fb.click("body", { position: { x: 5, y: 5 } });
      await openReport(fb);
      await raiseBar(fb, LONG2, MT2);
      await holdGets(fb);
      await fb.click("#fileview-save-err button");
      await fa.click("#composer-input"); await page.keyboard.type("ab");
      await fb.evaluate((p: string) => { delete (window as any).__docs[p]; }, REPORT);   // gone by the time the GET answers: a 404
      await releaseGets(fb);
      await fb.waitForFunction(() => !!document.querySelector(".fileview-body .fileview-err"), null, { timeout: 10000 }); await frames(fb, 3);
      const st = await barState(fb);
      assert.equal(st.errPane, true, "the failure pane painted"); assert.equal(st.text, "Reload"); assert.equal(st.disabled, false, "the button is re-armed");
      assert.equal(st.focused, false, "…and did not take the keyboard (before the fix: focused, the page's focus pulled into the Files frame)");
      assert.equal((await holder(fa)).active, COMPOSER, "the composer holds it");
      await page.keyboard.type("c"); await page.keyboard.press("Space"); await frames(fb, 2);
      assert.equal(await composer(fa), "abc ", "the letter and the Space reach the composer");
      const after = await barState(fb);
      assert.equal(after.text, "Reload"); assert.equal(after.disabled, false); assert.equal(after.gets, st.gets, "Space fired no second Reload");
      assert.deepEqual(errors, [], "no page errors (the re-arm scene)");
      await page.close();
    }
    // the editor's exit at a Save's ack (an untracked file: Save posts saveFile to the kernel, and the ack is a fileSaved message)
    {
      const { page, fa, fb, errors } = await mount(browser);
      await fb.evaluate(() => { const w = window as any; w.__status = { ...w.__status, trackedBy: null, store: null, storePath: null, storeMtimeNs: null }; });
      await fb.click("body", { position: { x: 5, y: 5 } });
      await openReport(fb);
      await fb.locator(".fileview-acts button", { hasText: /^Edit$/ }).click();
      await fb.waitForFunction(() => !!document.querySelector(".fileview-body textarea.fileview-editor"), null, { timeout: 10000 }); await frames(fb, 2);
      await fb.evaluate(() => { const ta = document.querySelector(".fileview-body textarea.fileview-editor") as HTMLTextAreaElement; ta.focus(); ta.value = ta.value + "\nedited\n"; ta.dispatchEvent(new Event("input")); });
      const n0: number = await fb.evaluate(() => (window as any).__posted.length);
      await fb.locator(".fileview-acts button", { hasText: /^Save$/ }).click();
      await fb.waitForFunction((n: number) => (window as any).__posted.length > n, n0, { timeout: 10000 });
      const save: { reqId: number } | null = await fb.evaluate((n: number) => { const p = (window as any).__posted.slice(n).find((m: any) => m && m.type === "saveFile"); return p ? { reqId: p.reqId } : null; }, n0);
      assert.ok(save, "Save posted saveFile and waits for the ack");
      await fa.click("#composer-input"); await page.keyboard.type("ab");
      await fb.evaluate((reqId: number) => { window.dispatchEvent(new MessageEvent("message", { data: { type: "fileSaved", reqId, mtimeNs: "1757145600000000031", logged: true } })); }, save!.reqId);
      await fb.waitForFunction(() => !document.querySelector(".fileview-body textarea.fileview-editor"), null, { timeout: 10000 }); await frames(fb, 3);
      const a = await holder(fa), b = await holder(fb);
      assert.equal(a.active, COMPOSER, "the composer holds the keyboard after the ack's repaint (before the fix: the chat's BODY)");
      assert.equal(b.hasFocus, false, "the Files document does not hold the page's focus");
      await page.keyboard.type("z");
      assert.equal(await composer(fa), "abz", "the next letter reaches the composer");
      assert.deepEqual(errors, [], "no page errors (the Save scene)");
      await page.close();
    }
  });
});
