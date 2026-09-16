// Every failure says what happened, in headless Chromium over the REAL viewer (plans/markdown-viewer.md, Slice 7: items 3, 5
// and 6 share this leg; real-viewer-leg.ts serves the page, its fetch stub answering a path missing from window.__docs with
// a 404 whose body is "no such file: " + the path, as the kernel's names the resolved path, and a text answer with the
// X-Romp-Text-Utf8 a test put in window.__utf8 for the path, "1" otherwise). Item 3's scene: a reload whose
// fetch fails is a paint the seam hears. Before Slice 7 the fetch chain's catch painted the pane and fired no hook, so the
// Comments panel, waiting on the reload its poll had asked for, kept its loader up until its 15 s deadline; now the catch
// fires the hooks AFTER the pane's swap (window.__paints grows by one) with the seam's error() answering the pane's words,
// while text() and mtimeNs() keep the last landing's and mode() its view. The file back under a new mtime, the landing
// paints again and error() is null. The wait is for the paint count (paintsReach), the event the panel keys on, never a
// timer. The panel scene (the last test): the Comments panel open over a seeded comment, a status whose mtime moved (the
// page's __mtime, the file gone from __docs; the panel's reopen asks it) has the panel ask the reload and hold its loader;
// the reload fails, and at the pane's paint the panel reads error() (contract C3) and the loader yields to the "bytes" row
// in the seam's words with Reload, within two frames of the pane and never the 15 s deadline; nothing is marked over the
// pane; the row's Reload over the file put back lands the bytes, and the pass paints the comment's highlight again (the
// hook ran to its end: the real fireRendered swallows a hook's throw, so the pass's own output is what says none was).
// Before contract C3's panel half: the loader stood until the deadline (red over a git archive of the branch with the
// panel's read of error() removed). Skips LOUDLY without a playwright browser (CI installs none), as the other legs do. Before Slice 7: __seam.error was not a function (red over a git archive of the base at the leg's first read
// of the seam, before the reload) and __paints did not move after a failed reload. Item 5's scene: a file the kernel
// decoded as Latin-1 (its text answer wearing X-Romp-Text-Utf8 "0") says why Edit is off in the note bar, LATIN1_NOTICE read
// off the source, the card's child above the body row (the notebar leg's reading: in the card, above the row, on screen at
// scrollTop 400), no button, the Edit button hidden and the text painted with error() null; the changed-on-disk bar takes the
// row when a window focus finds a moved mtime and its Reload's landing brings the line back over the new text; an open at a
// line past the end shows the past-the-end notice and not the line (the raise precedes landTarget), and a reload, which has
// no target, brings the line back. Before item 5: no bar at all over such a file (red at the scene's first read over a git
// archive of the branch before it, whose real-viewer-leg has no utf8 table either). Item 6's scene: an empty file says so in
// the body's own dress. A zero-byte file painted zero rows or an empty box and nothing else, a blank pane with Edit shown; now
// the text paint prepends the EMPTY_FILE line (read off the source) above the empty root, a child of the body outside code.hljs
// and .fileview-md and never a row, laid out in the pane's colour (var(--warn)) and padding, with Edit shown, the Outline hidden,
// error() null, text() "" and mode() following the buttons; the Raw click paints it above the empty rows' root; a reload that
// lands bytes repaints without it, and one that lands "" again brings it back; the URL viewer's renderBody does the same over an
// empty document. openViewer's default wait (a paragraph or a row) would time out over an empty document, so the scene waits on
// the line itself through the `waitFor` option. Before item 6: no line, the wait for it timed out (red over a git archive of the
// base with EMPTY_FILE stubbed). Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
// The Slice 7 review's round 1 (the manager's) added three readings: a same-bytes reload leaves the Latin-1 line's element standing
// (one announcement by assistive technology, not one per reload); a file whose only bytes are a BOM says so (BOM_ONLY_FILE) in
// the empty file's place, told from an empty file by the answer's Content-Length, which the page's stub writes as the kernel does,
// and in the URL viewer by its streamed read's own byte count; and the Comments panel over a note whose Rendered paint throws pairs
// its comment over the fallback Raw rows and moves the highlight into the Rendered box at the healed click (the claim source pins
// alone had held before).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, openPanel, closePanel, frames, paintsReach, PARA, LONG, LONG2, REPORT, MT, MT2, ORIGIN, UI } from "./real-viewer-leg";

/** The Latin-1 line's exported sentence, read off the viewer's source (contract C5), so the leg follows the constant. */
const LATIN1_NOTICE = (/^export const LATIN1_NOTICE = "([^"]+)";$/m.exec(fs.readFileSync(path.join(UI, "file-view.ts"), "utf8")) || [])[1];
/** The empty file's exported sentence (contract C5), read the same way. */
const EMPTY_FILE = (/^export const EMPTY_FILE = "([^"]+)";$/m.exec(fs.readFileSync(path.join(UI, "file-view.ts"), "utf8")) || [])[1];
/** The BOM-only file's exported sentence (the review's round 1), read the same way. */
const BOM_ONLY_FILE = (/^export const BOM_ONLY_FILE = "([^"]+)";$/m.exec(fs.readFileSync(path.join(UI, "file-view.ts"), "utf8")) || [])[1];
const MT3 = "1757145600000000011";

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

type Bar = { present: boolean; words: string; parent: string; before: string | null; buttons: number; inCard: boolean; aboveRow: boolean; inViewport: boolean; stamped: boolean; bodyScrollTop: number; edit: boolean | null; rows: number; paints: number; error: string | null; text: string | null; bars: number };
/** The note bar as laid out (file-view-notebar-browser.test.ts's reading): its own words (text nodes, without a button's label),
 *  its parent and next sibling, its box against the card's, the body row's and the viewport; with the Edit button's hidden bit,
 *  the painted rows or blocks, the paint count, the seam's error() and text(), and how many bars the card holds. */
const readBar = (page: any): Promise<Bar> => page.evaluate(() => {
  const w = window as any;
  const bar = document.getElementById("fileview-save-err");
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const edit = (Array.from(document.querySelectorAll("#romp-fileview .fileview-acts button")) as HTMLButtonElement[]).find((x) => x.textContent === "Edit" || x.getAttribute("aria-label") === "Edit");
  const base = {
    bodyScrollTop: body.scrollTop, edit: edit ? edit.hidden : null, rows: body.querySelectorAll(".fileview-md > p, code.hljs .fv-cl").length,
    paints: w.__paints, error: w.__seam.error(), text: w.__seam.text(), bars: document.querySelectorAll("#fileview-save-err, .fileview > .fileview-err").length,
  };
  if (!bar) return { present: false, words: "", parent: "", before: null, buttons: 0, inCard: false, aboveRow: false, inViewport: false, stamped: false, ...base };
  const r = bar.getBoundingClientRect(), card = document.querySelector(".fileview")!.getBoundingClientRect(), main = document.querySelector(".fileview-main")!.getBoundingClientRect();
  return {
    present: true, words: Array.from(bar.childNodes).filter((x) => x.nodeType === 3).map((x) => x.textContent || "").join(""),
    parent: (bar.parentElement as HTMLElement).className, before: bar.nextElementSibling ? (bar.nextElementSibling as HTMLElement).className : null,
    buttons: bar.querySelectorAll("button").length,
    inCard: r.top >= card.top - 0.5 && r.bottom <= card.bottom + 0.5 && r.left >= card.left - 0.5 && r.right <= card.right + 0.5,
    aboveRow: r.bottom <= main.top + 0.5 && r.height > 0,
    inViewport: r.top >= 0 && r.bottom <= innerHeight && r.height > 0,
    stamped: !!(bar as any).__stamp,   // a mark a test put on the element before a landing: still there means the same element stands
    ...base,
  };
});

test("in a browser: a Latin-1 file says why Edit is off (Slice 7, item 5): opened over a text answer wearing X-Romp-Text-Utf8 \"0\", the note bar reads LATIN1_NOTICE above the body row, in the card and on screen at scrollTop 400, with no button, the Edit button hidden and the text painted (error() null); a window focus over a moved mtime raises the changed-on-disk bar in its place and its Reload's landing brings the line back over the new text; a reload of the same bytes leaves that element standing (the review's round 1); an open at a line past the end shows the past-the-end notice and not the line, and a reload brings the line back; pane and chat", { timeout: 180000 }, async (t) => {
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
      // a reload of the same bytes (the Comments panel's poll asks one at every status whose mtime moved; here the seam's own) finds
      // the line standing with the same words and leaves the element as it is: the bar is a role=status live region, and one
      // re-created at every landing was read out again by assistive technology each time (the review's round 1)
      await page.evaluate(() => { (document.getElementById("fileview-save-err") as any).__stamp = 1; (window as any).__seam.reload(); });
      await paintsReach(page, paints + 2);
      await frames(page, 2);
      b = await readBar(page);
      assert.equal(b.words, LATIN1_NOTICE, mode + ": the line stands"); assert.equal(b.bars, 1, mode + ": one bar");
      assert.equal(b.stamped, true, mode + ": the same element, not a fresh one (before: a new role=status element at every landing, announced again)");
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

type Empty = { kids: string[]; line: string | null; lineParent: string | null; inCode: boolean; isRow: boolean; blocks: number; rows: number; edit: boolean | null; outline: boolean | null; paints: number; error: string | null; text: string | null; mode: string; mt: string; bars: number; color: string; warn: string; padTop: string; height: number; onScreen: boolean };
/** The body over an empty file: its children's first class in order, the line's words when the body's own first-level child
 *  carries the dress, where the line stands (its parent, inside code.hljs or not, a row or not), the blocks and rows under it,
 *  the Edit and Outline buttons' hidden bits, the seam's numbers where a seam exists (the URL viewer mounts none), the bars in the
 *  card, and the line's computed colour against a probe painted var(--warn), its padding and its box. */
const seenEmpty = (page: any): Promise<Empty> => page.evaluate(() => {
  const w = window as any;
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const line = body.querySelector(":scope > .fileview-err") as HTMLElement | null;
  const acts = Array.from(document.querySelectorAll("#romp-fileview .fileview-acts button")) as HTMLButtonElement[];
  const edit = acts.find((x) => x.textContent === "Edit" || x.getAttribute("aria-label") === "Edit");
  const outline = document.querySelector("#romp-fileview .fileview-outline-btn") as HTMLButtonElement | null;
  const probe = document.createElement("div"); probe.style.color = "var(--warn)"; document.querySelector(".fileview")!.appendChild(probe);
  const warn = getComputedStyle(probe).color; probe.remove();
  const r = line ? line.getBoundingClientRect() : null;
  return {
    kids: Array.from(body.children).map((x) => x.classList[0] || ""),
    line: line ? line.textContent : null, lineParent: line ? (line.parentElement as HTMLElement).classList[0] : null,
    inCode: !!line && !!line.closest("code.hljs"), isRow: !!line && line.classList.contains("fv-cl"),
    blocks: body.querySelectorAll(".fileview-md > *").length, rows: body.querySelectorAll("code.hljs .fv-cl").length,
    edit: edit ? edit.hidden : null, outline: outline ? outline.hidden : null,
    paints: w.__paints, error: w.__seam ? w.__seam.error() : null, text: w.__seam ? w.__seam.text() : null, mode: w.__seam ? w.__seam.mode() : "", mt: w.__seam ? w.__seam.mtimeNs() : "",
    bars: document.querySelectorAll("#fileview-save-err, .fileview > .fileview-err").length,
    color: line ? getComputedStyle(line).color : "", warn, padTop: line ? getComputedStyle(line).paddingTop : "",
    height: r ? r.height : 0, onScreen: !!r && r.top >= 0 && r.bottom <= innerHeight && r.height > 0,
  };
});

test("in a browser: an empty file says so (Slice 7, item 6): opened over a zero-byte text answer, the body's first child is the EMPTY_FILE line above the empty Rendered box, in the pane's colour and padding, on screen, a child of the body and never inside code.hljs or a row, with zero blocks, Edit shown, the Outline hidden, error() null, text() \"\", mode() rendered and no bar; the Raw click paints it above the empty rows' root (zero rows, mode() raw); Rendered again; a reload that lands bytes repaints without it, and one that lands \"\" again brings it back; the URL viewer paints the same line over an empty document; pane and chat", { timeout: 180000 }, async (t) => {
  assert.ok(EMPTY_FILE, "the constant is read off the source");
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as const) {
      const { page, errors } = await openViewer(browser, mode, 700, 600, { docs: { [REPORT]: "" }, waitFor: ".fileview-body > .fileview-err" });
      let e = await seenEmpty(page);
      assert.equal(e.line, EMPTY_FILE, mode + ": the sentence in the body (before item 6: a blank pane, and the wait for the line timed out)");
      assert.deepEqual(e.kids, ["fileview-err", "fileview-md"], mode + ": the line above the empty Rendered box, nothing else");
      assert.equal(e.lineParent, "fileview-body", mode + ": the body's own child, a sibling of the root");
      assert.equal(e.inCode, false, mode + ": never inside code.hljs"); assert.equal(e.isRow, false, mode + ": never a row");
      assert.equal(e.blocks, 0, mode + ": zero blocks in the box"); assert.equal(e.rows, 0, mode + ": zero rows");
      assert.equal(e.edit, false, mode + ": Edit shown: an empty file is editable"); assert.equal(e.outline, true, mode + ": the Outline hidden: no heading");
      assert.equal(e.error, null, mode + ": error() null: the content shows"); assert.equal(e.text, "", mode + ": text() is the empty string, never null");
      assert.equal(e.mode, "rendered", mode + ": mode() follows the buttons"); assert.equal(e.mt, MT, mode + ": the landing took the mtime");
      assert.equal(e.bars, 0, mode + ": no bar: the line is in the body, not the one-bar row");
      assert.equal(e.color, e.warn, mode + ": the body's dress: the pane's colour (var(--warn))"); assert.equal(e.padTop, "18px", mode + ": and its padding");
      assert.ok(e.onScreen, mode + ": laid out and on screen");
      const p1 = e.paints;
      // the Raw click: the line above the empty rows' root
      await page.locator("#romp-fileview .fileview-acts button", { hasText: /^Raw$/ }).click();
      await paintsReach(page, p1 + 1); await frames(page, 2);
      e = await seenEmpty(page);
      assert.equal(e.line, EMPTY_FILE, mode + ": the line over the Raw view too"); assert.deepEqual(e.kids, ["fileview-err", "fileview-code"], mode + ": above the rows' root");
      assert.equal(e.rows, 0, mode + ": zero rows"); assert.equal(e.inCode, false); assert.equal(e.isRow, false);
      assert.equal(e.mode, "raw", mode + ": mode() follows the buttons"); assert.equal(e.edit, false, mode + ": Edit still shown"); assert.equal(e.paints, p1 + 1, mode + ": one paint for the click");
      assert.equal(e.color, e.warn); assert.ok(e.onScreen);
      await page.locator("#romp-fileview .fileview-acts button", { hasText: /^Rendered$/ }).click();
      await paintsReach(page, p1 + 2); await frames(page, 2);
      e = await seenEmpty(page);
      assert.equal(e.line, EMPTY_FILE); assert.deepEqual(e.kids, ["fileview-err", "fileview-md"]); assert.equal(e.mode, "rendered");
      // bytes land (a session wrote the file): the landing's paint carries no line
      await page.evaluate(([p, tx, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = tx; w.__mtime = m; w.__seam.reload(); }, [REPORT, LONG2, MT2]);
      await paintsReach(page, p1 + 3); await frames(page, 2);
      e = await seenEmpty(page);
      assert.equal(e.line, null, mode + ": the line went with the bytes"); assert.deepEqual(e.kids, ["fileview-md"], mode + ": the box alone");
      assert.ok(e.blocks > 0, mode + ": the note is painted"); assert.equal(e.text, LONG2); assert.equal(e.mt, MT2); assert.equal(e.edit, false); assert.equal(e.error, null);
      // and "" again (a session emptied it): the line is back
      await page.evaluate(([p, tx, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = tx; w.__mtime = m; w.__seam.reload(); }, [REPORT, "", MT3]);
      await paintsReach(page, p1 + 4); await frames(page, 2);
      e = await seenEmpty(page);
      assert.equal(e.line, EMPTY_FILE, mode + ": the line is back over the emptied file"); assert.deepEqual(e.kids, ["fileview-err", "fileview-md"]);
      assert.equal(e.text, ""); assert.equal(e.mt, MT3); assert.equal(e.blocks, 0);
      assert.deepEqual(errors, [], mode + ": no uncaught page error");
      await page.close();
    }
    // the URL viewer over an empty document (read through capped-read.ts): the same line above the empty root, no seam to read
    const u = await openViewer(browser, "pane", 700, 600, { url: "/notes/empty.md", urls: { [ORIGIN + "/notes/empty.md"]: "" }, waitFor: ".fileview-body > .fileview-err" });
    let e = await seenEmpty(u.page);
    assert.equal(e.line, EMPTY_FILE, "URL: the sentence in the body (before item 6: a blank pane)");
    assert.deepEqual(e.kids, ["fileview-err", "fileview-md"], "URL: above the empty Rendered box"); assert.equal(e.blocks, 0); assert.equal(e.bars, 0);
    assert.equal(e.inCode, false); assert.equal(e.isRow, false); assert.equal(e.color, e.warn, "URL: the pane's colour"); assert.ok(e.onScreen);
    await u.page.locator("#romp-fileview .fileview-acts button", { hasText: /^Raw$/ }).click();
    await frames(u.page, 2);
    e = await seenEmpty(u.page);
    assert.equal(e.line, EMPTY_FILE); assert.deepEqual(e.kids, ["fileview-err", "fileview-code"], "URL: above the empty rows' root"); assert.equal(e.rows, 0);
    assert.deepEqual(u.errors, [], "URL: no uncaught page error");
    await u.page.close();
  });
});

test("in a browser: a file whose only bytes are a byte order mark says so (Slice 7, item 6; the review's round 1): served as one U+FEFF under Content-Length 3, the way the kernel serves it, a real Response's decode strips the mark and the body's first child is the BOM_ONLY_FILE line where the empty file's stands, text() \"\", Edit shown, error() null, the pane's dress; a reload landing zero bytes paints EMPTY_FILE and one landing text after the mark paints no line; the URL viewer over a BOM-only document, its streamed read counting the three bytes, paints the same line; pane", { timeout: 180000 }, async (t) => {
  assert.ok(BOM_ONLY_FILE && EMPTY_FILE, "the constants are read off the source");
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 700, 600, { docs: { [REPORT]: "\uFEFF" }, waitFor: ".fileview-body > .fileview-err" });
    // the page's stub answers the kernel's shape: one U+FEFF under Content-Length 3, and the Response's own decode gives ""
    const served = await page.evaluate(async (p: string) => { const r = await fetch("/file?path=" + encodeURIComponent(p)); return { len: r.headers.get("Content-Length"), text: await r.text() }; }, REPORT);
    assert.deepEqual(served, { len: "3", text: "" }, "three bytes on the wire, an empty text after the browser's decode");
    let e = await seenEmpty(page);
    assert.equal(e.line, BOM_ONLY_FILE, "the true sentence (before: EMPTY_FILE over a file of three bytes)");
    assert.deepEqual(e.kids, ["fileview-err", "fileview-md"], "in the empty file's place, above the empty Rendered box"); assert.equal(e.blocks, 0);
    assert.equal(e.lineParent, "fileview-body"); assert.equal(e.inCode, false); assert.equal(e.isRow, false);
    assert.equal(e.text, "", "text() is the view's text, the mark stripped by the decode, never null"); assert.equal(e.edit, false, "Edit shown: a save writes the bytes back through the doors' BOM rule");
    assert.equal(e.error, null); assert.equal(e.mode, "rendered"); assert.equal(e.bars, 0); assert.equal(e.color, e.warn, "the pane's dress"); assert.ok(e.onScreen);
    const p1 = e.paints;
    // a session emptied the file: zero bytes, the empty file's words
    await page.evaluate(([p, tx, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = tx; w.__mtime = m; w.__seam.reload(); }, [REPORT, "", MT2]);
    await paintsReach(page, p1 + 1); await frames(page, 2);
    e = await seenEmpty(page);
    assert.equal(e.line, EMPTY_FILE, "zero bytes (Content-Length 0): the empty file's words"); assert.equal(e.mt, MT2); assert.equal(e.text, "");
    // a session wrote text after the mark: the decode strips the mark, the note paints, no line
    await page.evaluate(([p, tx, m]: [string, string, string]) => { const w = window as any; w.__docs[p] = tx; w.__mtime = m; w.__seam.reload(); }, [REPORT, "\uFEFF" + LONG2, MT3]);
    await paintsReach(page, p1 + 2); await frames(page, 2);
    e = await seenEmpty(page);
    assert.equal(e.line, null, "text after the mark: no line"); assert.ok(e.blocks > 0, "the note painted"); assert.equal(e.text, LONG2, "the view's text without the mark, as the browser hands it"); assert.equal(e.mt, MT3);
    assert.deepEqual(errors, [], "no uncaught page error");
    await page.close();
    // the URL viewer: no kernel header to read, but its streamed read (readTextCapped) counts the bytes itself and its decode strips the mark
    const u = await openViewer(browser, "pane", 700, 600, { url: "/notes/bom.md", urls: { [ORIGIN + "/notes/bom.md"]: "\uFEFF" }, waitFor: ".fileview-body > .fileview-err" });
    e = await seenEmpty(u.page);
    assert.equal(e.line, BOM_ONLY_FILE, "URL: the same sentence (three bytes counted, \"\" decoded)");
    assert.deepEqual(e.kids, ["fileview-err", "fileview-md"], "URL: above the empty Rendered box"); assert.equal(e.blocks, 0); assert.equal(e.bars, 0); assert.equal(e.color, e.warn);
    await u.page.locator("#romp-fileview .fileview-acts button", { hasText: /^Raw$/ }).click();
    await frames(u.page, 2);
    e = await seenEmpty(u.page);
    assert.equal(e.line, BOM_ONLY_FILE); assert.deepEqual(e.kids, ["fileview-err", "fileview-code"], "URL: above the empty rows' root after Raw"); assert.equal(e.rows, 0);
    assert.deepEqual(u.errors, [], "URL: no uncaught page error");
    await u.page.close();
  });
});

/** The panel's row for a reload that failed: its exported lead (contract C3) and the fixed tail, both read off file-comments.ts. */
const FC_SRC = fs.readFileSync(path.join(UI, "file-comments.ts"), "utf8");
const BYTES_FAILED = (/^export const BYTES_FAILED = "([^"]+)";$/m.exec(FC_SRC) || [])[1];
const BYTES_FAILED_TAIL = (/^const BYTES_FAILED_TAIL = "([^"]+)";$/m.exec(FC_SRC) || [])[1];
const T0 = 1757145600000;
/** One comment on the seventh paragraph (its quote occurs once in LONG and once in LONG2), so the pass has a highlight to paint
 *  over the note and none to paint over the pane. Synthetic: the demo report's own words. */
const COMMENTS = [{ id: T0 + "-1", author: "you", ts: T0, body: "A note on the seventh paragraph.", anchor: { quote: "Paragraph 7: lorem ipsum dolor", prefix: "", suffix: " sit amet" }, replies: [], resolved: false }];

type Panel = { aside: boolean; loaders: number; row: string | null; rowButtons: string[]; marks: number; paints: number; error: string | null; pane: boolean; mt: string };
/** The Comments panel as laid out: whether the aside stands, the loaders at the head of its cards (the "bytes" slot's among them),
 *  the "bytes" error row's words and its buttons' labels when one stands, the highlights painted over the body; with the seam's
 *  paint count, error() and mtimeNs(), and whether a pane stands in the body in place of the file. */
const panelSeen = (page: any): Promise<Panel> => page.evaluate(() => {
  const w = window as any;
  const aside = document.querySelector(".fileview-aside");
  const row = aside ? aside.querySelector('.fc-err[data-slot="bytes"]') : null;
  return {
    aside: !!aside, loaders: aside ? aside.querySelectorAll(".fc-load").length : 0,
    row: row ? (row.firstChild ? row.firstChild.textContent : "") : null,
    rowButtons: row ? (Array.from(row.querySelectorAll("button")) as HTMLElement[]).map((b) => b.textContent || "") : [],
    marks: document.querySelectorAll(".fileview-body mark.fc-hl").length,
    paints: w.__paints, error: w.__seam.error(), pane: !!document.querySelector(".fileview-body > .fileview-err"), mt: w.__seam.mtimeNs(),
  };
});

test("in a browser: the Comments panel's wait for a reload that fails ends at the pane's paint (Slice 7, item 3; contract C3): the panel open over a seeded comment, a status whose file mtime moved has it ask the reload and hold its loader; the reload fails, and within two frames of the pane's paint the loader is gone and the \"bytes\" row reads BYTES_FAILED with the seam's words and Reload, nothing marked over the pane, error() the pane's words and mtimeNs() the last landing's; the row's Reload over the file put back lands the bytes, the row and the loader go and the comment's highlight is painted again", { timeout: 180000 }, async (t) => {
  assert.ok(BYTES_FAILED && BYTES_FAILED_TAIL, "the row's words are read off the source");
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700);
    await page.evaluate((cs: unknown[]) => { const s = (window as any).__status; s.store.comments = cs; s.unsent.comments = (cs as Array<{ id: string }>).map((c) => c.id); }, COMMENTS);
    await openPanel(page);
    await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-hl").length > 0, null, { timeout: 10000 });
    await frames(page, 2);
    const p0 = await panelSeen(page);
    assert.ok(p0.aside, "the panel is open"); assert.equal(p0.loaders, 0, "no loader: the view shows the status's text"); assert.equal(p0.row, null, "no bytes row");
    assert.equal(p0.marks, 1, "the comment's highlight is painted over the note"); assert.equal(p0.error, null); assert.equal(p0.pane, false); assert.equal(p0.mt, MT);
    // a session removed the file, and the kernel's status names a newer mtime than the view's: the panel's next status (its
    // reopen's own ask, answered from the page's table) has it ask the viewer to re-fetch (syncBytes) and hold the loader
    // (awaitBytes); the fetch fails, the catch paints the pane and fires the hooks, and the panel reads error() at that paint
    await page.evaluate(([p, m]: [string, string]) => { const w = window as any; delete w.__docs[p]; w.__mtime = m; }, [REPORT, MT2]);
    await closePanel(page);
    await openPanel(page);
    await page.waitForFunction((words: string) => { const n = document.querySelector(".fileview-body > .fileview-err"); return !!n && n.textContent === words; }, "no such file: " + REPORT, { timeout: 10000 });   // the pane's paint, the event
    await frames(page, 2);
    const failed = await panelSeen(page);
    assert.equal(failed.loaders, 0, "the loader went at the pane's paint, within two frames (before contract C3's panel half: it stood until the 15 s deadline)");
    assert.equal(failed.row, BYTES_FAILED + " (no such file: " + REPORT + ")" + BYTES_FAILED_TAIL, "the bytes row says what happened in the seam's own words, the fixed shape");
    assert.deepEqual(failed.rowButtons, ["Reload", "\u2715"], "with Reload and the dismiss");
    assert.equal(failed.marks, 0, "nothing is marked over the pane (the pass stands down over a body with neither root)");
    assert.ok(failed.pane, "the pane stands in place of the file"); assert.equal(failed.error, "no such file: " + REPORT, "error() is the pane's words"); assert.equal(failed.mt, MT, "mtimeNs() keeps the last landing's");
    // the file back (a session wrote it again): the row's Reload re-fetches the bytes and re-asks status; the landing's paint clears
    // error(), the row and the loader go, and the pass paints the comment's highlight over the new text (the hook ran to its end)
    await page.evaluate(([p, tx]: [string, string]) => { const w = window as any; w.__docs[p] = tx; }, [REPORT, LONG2]);
    await page.locator('.fileview-aside .fc-err[data-slot="bytes"] button', { hasText: /^Reload$/ }).click();
    await page.waitForFunction(() => { const a = document.querySelector(".fileview-aside"); return !!a && !a.querySelector('.fc-err[data-slot="bytes"]') && !a.querySelector(".fc-load") && !document.querySelector(".fileview-body > .fileview-err") && document.querySelectorAll(".fileview-body mark.fc-hl").length > 0; }, null, { timeout: 10000 });
    await frames(page, 2);
    const back = await panelSeen(page);
    assert.equal(back.row, null, "the row went with the landing"); assert.equal(back.loaders, 0, "and no loader stands");
    assert.equal(back.marks, 1, "the comment's highlight is painted over the new text"); assert.equal(back.error, null, "error() null: the content shows");
    assert.equal(back.pane, false); assert.equal(back.mt, MT2, "the landing took the new mtime");
    assert.deepEqual(errors, [], "no uncaught page error");
    await page.close();
  });
});

// ── the Slice 7 review's round 1: the URL viewer's own #fragment over a render that fell ───────────────────────────────────
/** The render catch's exported sentence (contract C5), read off the source as the other constants are. */
const RENDER_FELL = (/^export const RENDER_FELL = "([^"]+)";$/m.exec(fs.readFileSync(path.join(UI, "file-view.ts"), "utf8")) || [])[1];
/** A URL document with a section far down: sixty paragraphs, "## Later", forty more. */
const URL_DOC = "# Report\n\n" + Array.from({ length: 60 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n\n## Later\n\n" + Array.from({ length: 40 }, (_, i) => PARA(61 + i)).join("\n\n") + "\n";
const URL_PATH = "/notes/report.md";
/** The fault (real-viewer-leg's `before`, so it stands at the first paint): replaceChildren on the Rendered box throws, inside
 *  mdBlock and so inside the URL renderBody's try, which paints the RENDER_FELL line over the Raw rows; `__unfault` lifts it. */
const faultRenderedBox = (page: any): Promise<void> => page.evaluate(() => {
  const w = window as any; const orig = Element.prototype.replaceChildren; w.__threw = 0;
  w.__unfault = () => { Element.prototype.replaceChildren = orig; };
  Element.prototype.replaceChildren = function (this: Element, ...nodes: any[]) { if (this.classList && this.classList.contains("fileview-md")) { w.__threw++; throw new Error("synthetic render failure"); } return orig.apply(this, nodes); };
});
type UrlSeen = { kids: string[]; rows: number; paras: number; scrollTop: number; laterTop: number | null; threw: number; line: string | null; pressed: string[] };
const urlSeen = (page: any): Promise<UrlSeen> => page.evaluate(() => {
  const body = document.querySelector(".fileview-body") as HTMLElement; const br = body.getBoundingClientRect();
  const later = document.getElementById("md-later"); const err = body.querySelector(":scope > .fileview-err");
  return { kids: Array.from(body.children).map((k) => k.className.split(" ")[0]), rows: body.querySelectorAll(".fv-cl").length, paras: body.querySelectorAll(".fileview-md > p").length,
    scrollTop: body.scrollTop, laterTop: later ? Math.round(later.getBoundingClientRect().top - br.top) : null, threw: (window as any).__threw ?? 0, line: err ? err.textContent : null,
    pressed: Array.from(document.querySelectorAll('#romp-fileview .fileview-acts button[aria-pressed="true"]')).map((b) => b.textContent || "") };
});

test("in a browser, the URL viewer (the Slice 7 review's round 1): a document opened at its own #fragment whose Rendered paint throws shows the failure line over the Raw rows and keeps the fragment; the Raw click and a Rendered click that throws again keep it; the healed Rendered click lands the section at the body's top, where the control (no fault) lands at the open (before: landFragment spent the fragment against the rows and `landed` latched, so the healed paint rendered from the top)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const urls = { [ORIGIN + URL_PATH]: URL_DOC, [ORIGIN + URL_PATH + "#later"]: URL_DOC };
    const click = async (page: any, label: string): Promise<void> => { await page.locator("#romp-fileview .fileview-acts button", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 3); };
    // the control: no fault, the fragment lands at the open
    const c = await openViewer(browser, "pane", 700, 600, { url: URL_PATH + "#later", urls });
    await frames(c.page, 3);
    const ctl = await urlSeen(c.page);
    assert.deepEqual(ctl.kids, ["fileview-md"]); assert.equal(ctl.paras, 100);
    assert.ok(ctl.laterTop !== null && ctl.laterTop >= -1 && ctl.laterTop < 40, "control: the section at the body's top: " + JSON.stringify(ctl));
    assert.deepEqual(c.errors, []); await c.page.close();
    // the fault: the first paint falls to the rows, the fragment kept
    const { page, errors } = await openViewer(browser, "pane", 700, 600, { url: URL_PATH + "#later", urls, before: faultRenderedBox, waitFor: ".fileview-body > .fileview-err" });
    await frames(page, 3);
    let r = await urlSeen(page);
    assert.deepEqual(r.kids, ["fileview-err", "fileview-code"], "the failure line over the rows: " + JSON.stringify(r));
    assert.ok(r.line && r.line.startsWith(RENDER_FELL) && r.line.includes("synthetic render failure"), "the line names the error: " + r.line);
    assert.ok(r.rows > 100, "the document's rows: " + r.rows); assert.equal(r.threw, 1); assert.equal(r.scrollTop, 0); assert.equal(r.laterTop, null);
    assert.deepEqual(r.pressed, ["Rendered"], "the Rendered button pressed (item 1)");
    await click(page, "Raw");
    r = await urlSeen(page);
    assert.deepEqual(r.kids, ["fileview-code"], "rows alone after the Raw click"); assert.equal(r.scrollTop, 0);
    await click(page, "Rendered");   // still throwing
    r = await urlSeen(page);
    assert.deepEqual(r.kids, ["fileview-err", "fileview-code"], "the line over the rows again"); assert.equal(r.threw, 2);
    // healed: the Rendered click renders and the kept fragment lands
    await page.evaluate(() => { (window as any).__unfault(); });
    await click(page, "Rendered");
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await frames(page, 4);
    r = await urlSeen(page);
    assert.deepEqual(r.kids, ["fileview-md"], "the note rendered"); assert.equal(r.paras, 100); assert.equal(r.threw, 2, "no further throw");
    assert.ok(r.laterTop !== null && r.laterTop >= -1 && r.laterTop < 40, "the section at the body's top, as the control's (before: scrollTop 0 and the heading thousands of pixels down, the fragment spent over the rows): " + JSON.stringify(r));
    assert.ok(r.scrollTop > 1000, "the body scrolled to it: " + r.scrollTop);
    assert.deepEqual(errors, [], "no uncaught page error");
    await page.close();
  });
});

// ── the Slice 7 review's round 1: the Comments panel over the render catch's rows ─────────────────────────────────────────
type FellPanel = { kids: string[]; line: string | null; rowMarks: number; mdMarks: number; marks: number; asideErrs: number; loaders: number; mode: string; error: string | null; threw: number; rows: number; paras: number; pressed: string[] };
/** The body and the aside over a render that fell: the body's children, the failure line's words, the highlights inside Raw rows
 *  and inside the Rendered box, the aside's error rows and loaders, the seam's mode() and error(), the fault's count. */
const fellPanelSeen = (page: any): Promise<FellPanel> => page.evaluate(() => {
  const w = window as any;
  const body = document.querySelector(".fileview-body") as HTMLElement; const aside = document.querySelector(".fileview-aside");
  const err = body.querySelector(":scope > .fileview-err");
  return {
    kids: Array.from(body.children).map((k) => k.className.split(" ")[0]), line: err ? err.textContent : null,
    rowMarks: body.querySelectorAll("code.hljs .fv-cl mark.fc-hl").length, mdMarks: body.querySelectorAll(".fileview-md mark.fc-hl").length, marks: body.querySelectorAll("mark.fc-hl").length,
    asideErrs: aside ? aside.querySelectorAll(".fc-err").length : -1, loaders: aside ? aside.querySelectorAll(".fc-load").length : -1,
    mode: w.__seam.mode(), error: w.__seam.error(), threw: w.__threw ?? 0, rows: body.querySelectorAll(".fv-cl").length, paras: body.querySelectorAll(".fileview-md > p").length,
    pressed: Array.from(document.querySelectorAll('#romp-fileview .fileview-acts button[aria-pressed="true"]')).map((b) => b.textContent || "").filter((l) => l === "Rendered" || l === "Raw"),   // the format pair alone: the Comments button is pressed too while the aside is open
  };
});

test("in a browser: the Comments panel survives the render catch (Slice 7, item 1; the review's round 1): over a note whose Rendered paint throws at the open, a seeded comment pairs over the fallback Raw rows, one highlight inside a row and none elsewhere, no error row and no loader in the aside, the failure line the body's first child, mode() raw and error() null; the healed Rendered click renders the note and the pass paints the highlight inside .fileview-md with none left in a row; pane", { timeout: 180000 }, async (t) => {
  assert.ok(RENDER_FELL, "the line's constant is read off the source");
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { before: faultRenderedBox, waitFor: ".fileview-body code.hljs .fv-cl" });
    await page.evaluate((cs: unknown[]) => { const s = (window as any).__status; s.store.comments = cs; s.unsent.comments = (cs as Array<{ id: string }>).map((c) => c.id); }, COMMENTS);
    await openPanel(page);
    await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-hl").length > 0, null, { timeout: 10000 });   // the pass's paint over the rows, the event
    await frames(page, 2);
    const fell = await fellPanelSeen(page);
    assert.deepEqual(fell.kids, ["fileview-err", "fileview-code"], "the failure line first, the rows under it: " + JSON.stringify(fell));
    assert.ok(fell.line && fell.line.startsWith(RENDER_FELL) && fell.line.includes("synthetic render failure"), "the line names the error: " + fell.line);
    assert.equal(fell.threw, 1, "the open's paint threw once"); assert.equal(fell.mode, "raw", "mode() answers raw over the rows"); assert.equal(fell.error, null, "the rows are the content: error() null");
    assert.equal(fell.rowMarks, 1, "the comment's highlight is painted inside a Raw row (the panel pairs over code.hljs when mode() answers raw)");
    assert.equal(fell.marks, 1, "one highlight in the body"); assert.equal(fell.mdMarks, 0, "none in a Rendered box: there is none");
    assert.equal(fell.asideErrs, 0, "no error row in the aside"); assert.equal(fell.loaders, 0, "no loader held");
    assert.deepEqual(fell.pressed, ["Rendered"], "the Rendered button stays pressed (item 1)");
    // healed: the Rendered click tries again, the note renders, and the pass paints the highlight inside the Rendered box
    await page.evaluate(() => { (window as any).__unfault(); });
    await page.locator("#romp-fileview .fileview-acts button", { hasText: /^Rendered$/ }).click();
    await page.waitForFunction(() => !!document.querySelector(".fileview-md mark.fc-hl"), null, { timeout: 10000 });   // the pass over the rendered note, the event
    await frames(page, 2);
    const healed = await fellPanelSeen(page);
    assert.deepEqual(healed.kids, ["fileview-md"], "the note rendered, the line gone: " + JSON.stringify(healed)); assert.ok(healed.paras > 0, "paragraphs in the box"); assert.equal(healed.rows, 0, "no rows");
    assert.equal(healed.mdMarks, 1, "the highlight moved into the Rendered box"); assert.equal(healed.rowMarks, 0, "none left in a row"); assert.equal(healed.marks, 1, "one highlight");
    assert.equal(healed.mode, "rendered"); assert.equal(healed.error, null); assert.equal(healed.threw, 1, "no further throw"); assert.equal(healed.asideErrs, 0); assert.equal(healed.loaders, 0);
    assert.deepEqual(errors, [], "no uncaught page error");
    await page.close();
  });
});
