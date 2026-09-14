// The ring at a keyboard-driven open whose opener is no element, or is gone at the landing, over the REAL viewer in headless
// Chromium (plans/markdown-viewer.md Slice 6, item 1; the review's round 4). Round 3 named the ring through the focus call's
// focusVisible option, read off the holder the body takes the keyboard from, and passed none when there was no holder, which
// closed Chromium's misfire on the pointer opens (file-view-focus-ring-browser.test.ts) and also cost the ring at two keyboard
// gestures: Enter on a Tab-focused path link inside the note (the replace path removed the old viewer with the link before the
// fetch landed, so the landing read the document's body and passed none) and Enter on the file browser's active row (the rows
// are not focusable, so the document's body held the keyboard throughout). At 27c56fbf7 the browser's own heuristic, "a key
// was pressed since the last mouse press", drew the ring for both, and since the option's verdict is sticky for that focus, no
// PageDown or arrow brought it back. Now the replace path reads the ring off a holder inside the card it removes (ringInOld)
// and the open's first landing passes it, and a hand-over with no holder passes the kind of this document's last press, a key
// that is not a modifier alone or a pointer, recorded on the two events by initFileView (watchInputKind), while this document
// holds the page's focus (ringWithNoHolder). Measured here with real keys and presses: in the Files pane at 900 px and the chat
// modal at 900 px under render.ts's lifted key handlers, a Tab to the in-body link and Enter replace the viewer with the body
// holding the keyboard AND the accent ring, and a mouse click on the same link replaces it without; in the pane, the REAL file
// browser (file-browse.ts bundled beside the viewer, its onKey to onAct to openFileClick flow) opened by ArrowDown and Enter
// lands with the ring and by a mouse click on a row without; the controls of the round 3 leg hold in the same runs (a
// gestureless open and an open after a click on plain text show none). The second leg pins the changed-on-disk bar's Reload
// hand-over behaviourally, which round 3 pinned by source regexes alone: a Tab to the bar's Reload and Enter (the click's
// record, read before the disable drops the focus) lands the body with the ring in the pane and the chat modal at 700 px, and a
// mouse Reload without. Red over a git archive of 7fbced030 at the in-body link's Enter and the browser row's Enter (fv false,
// outline none); the Reload leg is green there (a coverage pin; an edit reading the ring at the drop alone turns it red). Skips
// LOUDLY without a playwright browser (CI installs none), as the other legs do. Synthetic values only: invented notes,
// /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { inBrowser, pageHtml, bundleViewer, chatKeysScript, frames, paintsReach, requireCjs, UI, EXT, ORIGIN, ROOT, REPORT, SID, MT, MT2, PARA, LONG, LONG2, rewritten, openViewer } from "./real-viewer-leg";

const NOTES = ROOT + "/docs/notes.md";
const INTRO = "See ./notes.md for the notes, and check the target words in this sentence before the release.";
const NOTE = "# Report\n\n" + INTRO + "\n\n## Alpha\n\n" + Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const NOTE2 = "# Notes\n\n" + Array.from({ length: 40 }, (_, i) => PARA(i + 101)).join("\n\n") + "\n";
const MT3 = "1757145600000000012";

/** The viewer AND the file browser from this tree in ONE bundle (one file-view module instance, as the Files page has them). */
function bundleBoth(): string {
  const r = requireCjs("esbuild").buildSync({
    stdin: { contents: 'export { initFileView, openFileView, openUrlView, closeFileView, registerFileViewAction } from "./file-view"; export { TRIM_STATS } from "./anchor-map"; export { initFileBrowse, openFileBrowse, closeFileBrowse } from "./file-browse";', resolveDir: UI, loader: "ts", sourcefile: "focus-ring-openers-leg.ts" },
    bundle: true, write: false, format: "iife", globalName: "FV", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text as string;
}
/** The file browser's host wiring: the poster answers a listDir with two viewable rows under /repo/notes-api/docs. */
const BROWSE_WIRE = "<script>FV.initFileBrowse(function (m) { window.__posted.push(m); if (m && m.type === 'listDir') { var reply = { type: 'dirListing', reqId: m.reqId, base: m.path, parent: '/repo/notes-api', entries: ["
  + "{ name: 'report.md', isDir: false, isLink: false, size: 100, mtime: 1757145600, viewable: true }, { name: 'notes.md', isDir: false, isLink: false, size: 50, mtime: 1757145600, viewable: true }"
  + "] }; setTimeout(function () { window.dispatchEvent(new MessageEvent('message', { data: reply })); }, 0); } }, {});</script>";
/** The surface's page with the viewer and the browser bundled together, a plain paragraph outside the card, and in the chat a
 *  composer and a transcript box under render.ts's lifted key handlers. */
function pageWith(mode: "pane" | "chat"): string {
  let html = pageHtml(mode, { [REPORT]: NOTE, [NOTES]: NOTE2 }, MT);
  const vb = bundleViewer(); const i = html.indexOf(vb);
  assert.ok(i >= 0, "the viewer bundle is in the page");
  html = html.slice(0, i) + bundleBoth() + html.slice(i + vb.length);
  if (mode === "chat") html = html.replace('<body class="">', () => '<body class=""><textarea id="composer-input"></textarea><div id="content" style="height:120px;overflow:auto"><p id="plain">plain</p><div style="height:4000px"></div></div>');
  else html = html.replace('<body class="fileview-pane">', () => '<body class="fileview-pane"><p id="plain">plain text outside the viewer</p>');
  const wire = (mode === "chat" ? "<script>" + chatKeysScript() + "</script>" : "") + BROWSE_WIRE;
  const tail = html.lastIndexOf("</body></html>");
  assert.ok(tail > 0, "the page ends with </body></html>");
  return html.slice(0, tail) + wire + html.slice(tail);
}
type Ring = { active: string; fv: boolean; outline: string; outlineColor: string; accent: string; scrollTop: number; headline: string | null };
/** In the page: who holds the keyboard, whether the body matches :focus-visible, its computed outline beside the resolved accent, its scrollTop and the note's h1. */
function readRing(): Ring {
  const b = document.querySelector(".fileview-body") as HTMLElement | null;
  const a = document.activeElement as HTMLElement | null;
  const name = (n: Element | null): string => !n ? "none" : n.tagName + (n.id ? "#" + n.id : "") + (typeof (n as HTMLElement).className === "string" && (n as HTMLElement).className ? "." + (n as HTMLElement).className.split(/\s+/).filter(Boolean).join(".") : "");
  const probe = document.createElement("span"); probe.style.color = "var(--accent)"; document.body.appendChild(probe);
  const accent = getComputedStyle(probe).color; probe.remove();
  const cs = b ? getComputedStyle(b) : null;
  return { active: name(a), fv: b ? b.matches(":focus-visible") : false, outline: cs ? cs.outlineStyle : "no-body", outlineColor: cs ? cs.outlineColor : "no-body", accent, scrollTop: b ? b.scrollTop : -1, headline: document.querySelector(".fileview-md h1")?.textContent ?? null };
}
const ringOf = (page: any): Promise<Ring> => page.evaluate(readRing);
const BODY = "DIV.fileview-body";
function noRing(r: Ring, what: string): void {
  assert.equal(r.active, BODY, what + ": the body took the keyboard (read " + r.active + ")");
  assert.equal(r.fv, false, what + ": the body matches no :focus-visible (read fv " + r.fv + ", outline " + r.outline + ")");
  assert.equal(r.outline, "none", what + ": the computed outline is none (read " + r.outline + ")");
}
function ring(r: Ring, what: string): void {
  assert.equal(r.active, BODY, what + ": the body holds the keyboard (read " + r.active + ")");
  assert.equal(r.fv, true, what + ": the body matches :focus-visible (at 7fbced030 the hand-over passed focusVisible false with no holder to read, and the keyboard user got no ring; 27c56fbf7 drew it)");
  assert.notEqual(r.outline, "none", what + ": the ring shows (outline-style " + r.outline + ")");
  assert.equal(r.outlineColor, r.accent, what + ": the ring is the accent (var(--accent), never a status colour)");
}
const paints = (page: any): Promise<number> => page.evaluate(() => (window as any).__paints);
const painted = async (page: any, before: number): Promise<void> => { await paintsReach(page, before + 1); await frames(page, 3); };
const closed = (page: any): Promise<unknown> => page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 4000 });
async function pageOf(browser: any, w: number, h: number, html: string): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  return { page, errors };
}
const openByScript = async (page: any, p: string): Promise<void> => { const b = await paints(page); await page.evaluate(([q, sid]: [string, string]) => { (window as any).FV.openFileView(q, sid, null); }, [p, SID]); await painted(page, b); };
/** Tab until the active element matches `pred`; the number of Tabs it took, or -1. */
async function tabTo(page: any, pred: string, max = 20): Promise<number> {
  for (let i = 1; i <= max; i++) { await page.keyboard.press("Tab"); await frames(page, 1); if (await page.evaluate((p: string) => { const a = document.activeElement; return !!a && a.matches(p); }, pred)) return i; }
  return -1;
}
const LINK = ".fileview-md .file-uri-link";
/** Whether the current `.fileview-body` is another element than `old` (the replace path built a new card). */
const replacedFrom = (page: any, old: any): Promise<boolean> => page.evaluate((o: Element | null) => document.querySelector(".fileview-body") !== o, old);
const bodyHandle = (page: any): Promise<any> => page.evaluateHandle(() => document.querySelector(".fileview-body"));

test("in a browser, in the Files pane and the chat modal at 900 px (review round 4): a Tab to the in-body `./notes.md` link (which wears the ring) and Enter replace the viewer with the new body holding the keyboard WITH the accent ring, and the keys that follow keep it; a mouse click on the same link replaces it without; in the pane the REAL file browser opened by ArrowDown and Enter (the rows are not focusable: the document's body held the keyboard) lands with the ring, and by a mouse click on a row without; a gestureless open and an open after a click on plain text still show none", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as const) {
      const what = mode + " 900px";
      const { page, errors } = await pageOf(browser, 900, 700, pageWith(mode));
      // the round 3 controls hold: a gestureless open, and one after a click on plain text
      await openByScript(page, REPORT);
      noRing(await ringOf(page), what + ", a gestureless open");
      await page.keyboard.press("Escape"); await closed(page);
      await page.click("#plain");
      await openByScript(page, REPORT);
      noRing(await ringOf(page), what + ", an open after a click on plain text");
      // A: Tab to the in-body link (it wears the ring), Enter: the replace path removes the old card with the link before the landing
      const tabs = await tabTo(page, LINK);
      assert.ok(tabs > 0, what + ": a Tab reaches the in-body path link (" + tabs + ")");
      const link = await page.evaluate(() => { const a = document.activeElement as HTMLElement; return { text: a.textContent, ring: a.matches(":focus-visible"), tabindex: a.getAttribute("tabindex"), rel: a.dataset.rel || null }; });
      assert.equal(link.text, "./notes.md", what + ": the link is the note's ./notes.md");
      assert.equal(link.ring, true, what + ": the Tab-focused link wears the ring");
      const oldA = await bodyHandle(page);
      { const b = await paints(page); await page.keyboard.press("Enter"); await painted(page, b); }
      assert.equal(await replacedFrom(page, oldA), true, what + ": Enter on the link replaced the viewer");
      const afterEnter = await ringOf(page);
      assert.equal(afterEnter.headline, "Notes", what + ": the linked note is up");
      ring(afterEnter, what + ", Enter on the Tab-focused in-body link");
      await page.keyboard.press("PageDown"); await frames(page, 3);
      const afterKey = await ringOf(page);
      assert.ok(afterKey.scrollTop > 0, what + ": PageDown scrolled the new body (" + afterKey.scrollTop + ")");
      ring(afterKey, what + ", after PageDown on the new body");
      // B: the control, a mouse click on the in-body link of THIS note (the press drops the span's tabindex and focuses the body,
      // mouse-focused). The open before it follows a click on plain text, so the body it replaces wears no ring: a body that
      // wore one (a keyboard arrival) passes it on through the replace as any holder wearing the ring does, and Escape then a
      // script open in this same document would have given it one (Escape is a key press, and the document holds the focus).
      await page.keyboard.press("Escape"); await closed(page);
      await page.click("#plain");
      await openByScript(page, REPORT);
      noRing(await ringOf(page), what + ", the open before the click control");
      const oldB = await bodyHandle(page);
      { const b = await paints(page); await page.click(LINK); await painted(page, b); }
      assert.equal(await replacedFrom(page, oldB), true, what + ": the click on the link replaced the viewer");
      const afterClick = await ringOf(page);
      assert.equal(afterClick.headline, "Notes", what + ": the linked note is up after the click");
      noRing(afterClick, what + ", a mouse click on the in-body link");
      if (mode === "pane") {
        // C: the real file browser: ArrowDown makes a row active (no element takes the focus), Enter opens it through onAct and openFileClick
        await page.keyboard.press("Escape"); await closed(page);
        await page.evaluate(([d, sid]: [string, string]) => { (window as any).FV.openFileBrowse(d, sid); }, [ROOT + "/docs", SID]);
        await page.waitForFunction(() => document.querySelectorAll(".fb-row[data-act=file]").length >= 2, null, { timeout: 5000 });
        await page.keyboard.press("ArrowDown"); await frames(page, 1);
        const rowState = await page.evaluate(() => { const r = document.querySelector(".fb-row.active") as HTMLElement | null; const a = document.activeElement; return { activeRow: r ? r.dataset.path : null, rowTabindex: r ? r.getAttribute("tabindex") : null, holder: a ? a.tagName : "none" }; });
        assert.equal(rowState.activeRow, REPORT, what + ": ArrowDown made the report's row active");
        assert.equal(rowState.rowTabindex, null, what + ": the row is not focusable");
        assert.equal(rowState.holder, "BODY", what + ": the document's body holds the keyboard at the Enter");
        { const b = await paints(page); await page.keyboard.press("Enter"); await painted(page, b); }
        const afterRow = await ringOf(page);
        assert.equal(afterRow.headline, "Report", what + ": Enter on the row opened the note over the listing");
        ring(afterRow, what + ", Enter on the file browser's active row");
        // the control: a mouse click on a row opens without the ring
        await page.keyboard.press("Escape"); await closed(page);
        assert.equal(await page.evaluate(() => !!document.getElementById("romp-filebrowse")), true, what + ": the listing is still up under the closed viewer");
        { const b = await paints(page); await page.click(".fb-row[data-act=file] >> nth=1"); await painted(page, b); }
        const afterRowClick = await ringOf(page);
        assert.equal(afterRowClick.headline, "Notes", what + ": the click on the second row opened the notes");
        noRing(afterRowClick, what + ", a mouse click on a file browser row");
      }
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
  });
});

/** Move the file on disk and dispatch the window focus that runs the HEAD; wait for the bar (the notebar leg's helper). */
async function raiseBar(page: any, text: string, mtime: string): Promise<void> {
  await page.evaluate(([p, t, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = t; w.__mtime = m; window.dispatchEvent(new Event("focus")); }, [REPORT, text, mtime]);
  await page.waitForFunction(() => !!document.querySelector("#fileview-save-err button"), null, { timeout: 5000 });
  await frames(page, 1);
}
const RELOAD = "#fileview-save-err button";

test("in a browser, in the Files pane and the chat modal at 700 px (review round 4, a behavioural pin of round 3's Reload ring): with the changed-on-disk bar up, a Tab to its Reload (which wears the ring) and Enter land the body holding the keyboard WITH the accent ring, the bar gone (the click's record, read before the disable drops the focus, passed at the drop); the bar raised again and a mouse Reload land it without", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as const) {
      const what = mode + " 700px";
      const { page, errors } = await openViewer(browser, mode, 700, 600, { docs: { [REPORT]: LONG } });
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 300; });
      await raiseBar(page, LONG2, MT2);
      // the keyboard's way: the bar's X focused by script, Tabs to the Reload, which then wears the ring
      await page.evaluate(() => { (document.querySelector(".fileview-close") as HTMLElement).focus(); });
      const tabs = await tabTo(page, RELOAD, 12);
      assert.ok(tabs > 0, what + ": a Tab from the bar's close reaches the Reload (" + tabs + ")");
      assert.equal(await page.evaluate((s: string) => document.querySelector(s)!.matches(":focus-visible"), RELOAD), true, what + ": the Tab-focused Reload wears the ring");
      { const b = await paints(page); await page.keyboard.press("Enter"); await painted(page, b); }
      assert.equal(await page.evaluate(() => !!document.querySelector("#fileview-save-err")), false, what + ": the landing removed the bar");
      const afterKey = await ringOf(page);
      ring(afterKey, what + ", Enter on the Tab-focused Reload");
      // the mouse's way: the bar raised again, a click on Reload
      await raiseBar(page, rewritten(60, true), MT3);
      { const b = await paints(page); await page.locator(RELOAD, { hasText: /^Reload$/ }).click(); await painted(page, b); }
      assert.equal(await page.evaluate(() => !!document.querySelector("#fileview-save-err")), false, what + ": the second landing removed the bar");
      noRing(await ringOf(page), what + ", a mouse Reload");
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
  });
});
