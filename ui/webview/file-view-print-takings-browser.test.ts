// Print's disabled phase AFTER a successful paint (file-print.ts, P7 of the print follow-on to plans/markdown-viewer.md's
// Slice 3, item 12), over the real viewer in headless Chromium through real-viewer-leg.ts. file-print-browser.test.ts
// case 6 drives the disabled phase for an open's own loader alone: the flow starts disabled and the first paint rests it.
// Since the third review (2026-09-19) the flow reads the body itself (file-print.ts bodyReady, over the body's children,
// through a MutationObserver and again at each press) instead of taking each paint's report: the viewer's loader as the
// body's content, the plain fallback editor and a failure pane alone disable it, and every other paint leaves it live.
// Before that each paint reported the body in or out by hand (`print.bodyIn`), and the roads nobody wired had the button
// live over a loader (the Comments panel's PDF pages flow) or over a control of which a print shows one clipped page (the
// plain fallback editor, reported in). This leg executes each taking and each seating:
// (1) a gated note on the pane, the bar armed and the keyboard on one of the line's word buttons, then a reload that fails
// (the file gone): the armed line goes, the button disables (aria-disabled and `data-print` reading disabled, the armed
// dress off, and never the `disabled` property, which would drop the keyboard on the document's body: the bar's own rule),
// the keyboard goes to the viewer's body through its own hand-over (takeKeyboard, as the changed-on-disk bar's Reload
// hands it), the chord is still prevented and prints nothing, a forced click and a programmatic click print nothing; the
// file back and its text seated, the button is live and the next press arms again. Then the wait: "Print without them"
// over a picture whose route is parked, the deadline shortened through the seam, and a reload that fails during the wait:
// the preparing line goes, the button disables, and neither the parked picture's release nor the deadline prints (the wait
// was cancelled, not orphaned); no request reached the other host through any of it. (2) the editor on the chat modal: Edit
// while armed puts the chunk's loader up (the chunk's request parked by the test, which serves the page a bundle script
// tag to derive it from): the line goes and the button disables, the chord prevented and printing nothing; the chunk
// answering with nothing registered takes the plain fallback, a textarea, which DISABLES too (a press there printed one
// clipped page of a scrollable control); Cancel repaints the text (live, and one press prints the Raw view); Edit again
// over the re-armed bar, the chunk answering with an editor, takes the real mount, which is LIVE and prints (the CodeMirror
// mount prints the whole file). (3) a picture opened directly on the pane: a reload whose bytes will not decode paints
// imgFailed's pane and disables; the chord over it prints nothing; good bytes seat the picture again and the chord prints.
// (4) the URL viewer over a document that fails to load: the button stands disabled over the pane, the chord prevented and
// printing nothing. (5) the Comments panel's PDF pages flow on the pane, the chunk stubbed with a render the test releases:
// the attempt over a kept frame leaves the button live (the frame stands under the loader inside its column) and a press
// takes the PDF road (no frame window in the headless shell, so the /file tab); page 1 mounted, live, the same road; a
// reload with the pages up puts the loader alone in the body with the kind known to be a PDF, and the button stays LIVE:
// a press and the chord take the PDF road (the /file tab) at once, since that road reads nothing from the body (the
// round-2 review, 2026-09-19: the derived readiness had closed it, disabling Print and swallowing the chord over the
// pages loader where the earlier build opened the tab; the loader-means-not-ready rule is the document kinds'). FAILS
// BEFORE (the code before the third review): case 1's `disabled` property read true and the keyboard landed on the
// document's body; case 2's plain fallback read live and a press printed; and, at the round-2 head, case 5's reload left
// the button disabled over the pages loader and the press opened no tab. Checked red against the viewer with one report
// removed while the first version of this leg was written (the fetch pane's report: case 1 fails at the standing line;
// imgFailed's: case 3 at the live button over the pane; the chunk wait's: case 2 at the standing line). Skips loudly
// without a browser. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, REPORT, ROOT, ORIGIN, SID } from "./real-viewer-leg";
import { WITH_WORDS, WITHOUT_WORDS, PRINT_SETTLE_MS, TAB_WORDS } from "./file-print";

const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="black"/></svg>';
const QUICK = "fig.svg";                       // a local picture the route answers at once
const SLOW = "slow.svg";                       // a local picture whose route is parked until the test releases it
const REMOTE_HOST = "other.test";              // not in the gear's default list, not the page's origin: a placeholder
const REMOTE = "https://" + REMOTE_HOST + "/o.svg";
const GATED_NOTE = "# Figures\n\nA local picture ![](" + QUICK + ") and a slow one ![](" + SLOW + ").\n\nA remote one ![](" + REMOTE + ").\n\nLast line.\n";
const REMOTE_NOTE = "# Remote\n\nA remote picture ![](" + REMOTE + ") alone.\n\nLast line.\n";
const SHORT = "# A short note\n\nOne paragraph, and that is all.\n";
const PIC = ROOT + "/docs/pic.svg";            // a picture opened directly: the stub answers an .svg path as image/svg+xml
const BAD_BYTES = "not a picture";             // bytes the browser will not decode as an image
const MT_A = "1757145600000000011", MT_B = "1757145600000000012", MT_C = "1757145600000000013", MT_D = "1757145600000000014", MT_E = "1757145600000000015";
const PDF = ROOT + "/docs/paper.pdf";
const PDF_BYTES = "%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n";
const ARMED_ONE = "1 picture from another host is not loaded.";

type Print = { incomplete: number; pane: boolean; line: boolean; cm: boolean; editor: boolean };
type Key = { prevented: boolean; open: boolean };
type Bar = { present: boolean; disabled: boolean; ariaDisabled: string | null; phase: string | null; on: boolean; expanded: string | null; busy: boolean; ariaBusy: string | null; line: string | null; buttons: string[]; pane: boolean; loader: boolean; bodyLoader: boolean; cardUp: boolean; active: string; opens: number };

/** The page's record of the print stub's calls (with what held the body), the window's chords, window.open's calls (the PDF
 *  road's tab), the bar as it stands, and the keyboard's holder (the tag and its classes). */
const PAGE_PROBES = () => {
  const w = window as any;
  w.__prints = []; w.__keys = []; w.__opens = [];
  const imgs = () => Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[];
  w.print = () => { w.__prints.push({ incomplete: imgs().filter((i) => !i.complete).length, pane: !!document.querySelector("#romp-fileview .fileview-body > .fileview-err"), line: !!document.getElementById("fileview-print-line"), cm: !!document.querySelector("#romp-fileview .fileview-body > .fileview-cm"), editor: !!document.querySelector("#romp-fileview .fileview-body > textarea.fileview-editor") }); };
  w.open = (url: unknown, target: unknown) => { w.__opens.push({ url: String(url), target: String(target) }); return { opener: {} }; };
  window.addEventListener("keydown", (e) => { if (e.key.toLowerCase() === "p" && (e.ctrlKey || e.metaKey)) w.__keys.push({ prevented: e.defaultPrevented, open: document.body.classList.contains("fileview-open") }); });
  const describe = (a: Element | null): string => (a ? a.tagName + (a.className ? "." + String(a.className).split(" ").filter((c) => c && c !== "romp-acted").join(".") : "") : "null");
  w.__bar = (): Bar => {
    const b = document.querySelector("#romp-fileview .fileview-bar .fileview-print") as HTMLButtonElement | null;
    const line = document.getElementById("fileview-print-line");
    return { present: !!b, disabled: !!b && b.disabled, ariaDisabled: b ? b.getAttribute("aria-disabled") : null, phase: b ? (b.dataset.print || null) : null, on: !!b && b.classList.contains("on"), expanded: b ? b.getAttribute("aria-expanded") : null,
      busy: !!b && b.classList.contains("fileview-busy"), ariaBusy: b ? b.getAttribute("aria-busy") : null,
      line: line ? (line.firstChild && line.firstChild.nodeType === 3 ? (line.firstChild.textContent || "") : line.textContent) : null, buttons: line ? Array.from(line.querySelectorAll("button")).map((x) => x.textContent || "") : [],
      pane: !!document.querySelector("#romp-fileview .fileview-body > .fileview-err"), loader: !!document.querySelector("#romp-fileview .fileview-body .fileview-load"), bodyLoader: !!document.querySelector("#romp-fileview .fileview-body > .fileview-load"), cardUp: !!document.getElementById("romp-fileview"),
      active: describe(document.activeElement), opens: w.__opens.length };
  };
};
const bar = (page: any): Promise<Bar> => page.evaluate(() => (window as any).__bar());
const prints = (page: any): Promise<Print[]> => page.evaluate(() => (window as any).__prints);
const keys = (page: any): Promise<Key[]> => page.evaluate(() => (window as any).__keys);
/** The chord, and what the window heard of it: the driver's capture-phase listener runs first, so defaultPrevented is its word. */
async function chord(page: any): Promise<Key> {
  const n = (await keys(page)).length;
  await page.keyboard.press("Control+p");
  await frames(page, 1);
  const ks = await keys(page);
  assert.equal(ks.length, n + 1, "the window heard the chord");
  return ks[n];
}
/** A forced click (Playwright would otherwise wait for an enabled button) and a programmatic click: the browser dispatches
 *  neither to a disabled button, and the driver's disabled phase ignores a press that reaches it anyway. */
async function pressHard(page: any): Promise<void> {
  await page.click("#romp-fileview .fileview-print", { force: true });
  await page.evaluate(() => { (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click(); });
  await frames(page, 1);
}
/** The disabled dress, whole: aria-disabled and never the property (the bar's rule: a button with the property drops the
 *  keyboard on the document's body and leaves the tab order), the phase, no armed or busy dress, no line. */
function assertDisabled(b: Bar, label: string): void {
  assert.equal(b.present, true, label + ": the button is in the bar");
  assert.equal(b.ariaDisabled, "true", label + ": aria-disabled");
  assert.equal(b.disabled, false, label + ": the `disabled` property is never set");
  assert.equal(b.phase, "disabled", label + ": data-print reads disabled");
  assert.equal(b.on, false, label + ": the armed dress is off"); assert.equal(b.expanded, null, label + ": not expanded");
  assert.equal(b.busy, false, label + ": the busy dress is off"); assert.equal(b.ariaBusy, null, label + ": not busy");
  assert.equal(b.line, null, label + ": no line under the bar"); assert.deepEqual(b.buttons, [], label + ": no line buttons");
  assert.equal(b.cardUp, true, label + ": the viewer stays up");
}
/** The resting dress: live, no phase, no line. */
function assertLive(b: Bar, label: string): void {
  assert.equal(b.disabled, false, label + ": live"); assert.equal(b.ariaDisabled, null, label + ": no aria-disabled");
  assert.equal(b.phase, null, label + ": at rest"); assert.equal(b.line, null, label + ": no line");
}
/** The file gone from the table, and a reload: the fetch chain's catch paints its pane. */
async function failReload(page: any, path: string): Promise<void> {
  await page.evaluate((p: string) => { const w = window as any; delete w.__docs[p]; w.__seam.reload(); }, path);
  await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body > .fileview-err"), null, { timeout: 10000 });
  await frames(page, 1);
}
/** The file back under a new mtime, and a reload: the landing seats it again; `sel` is the seating's own element. */
async function restore(page: any, path: string, text: string, mtime: string, sel: string): Promise<void> {
  await page.evaluate((a: [string, string, string]) => { const w = window as any; w.__docs[a[0]] = a[1]; w.__mtime = a[2]; w.__seam.reload(); }, [path, text, mtime]);
  await page.waitForFunction((s: string) => !!document.querySelector(s), sel, { timeout: 10000 });
  await frames(page, 1);
}
const waitPlaceholder = (page: any): Promise<unknown> => page.waitForFunction(() => document.querySelectorAll('[data-act="fv-load"]').length === 1, null, { timeout: 10000 });

// ── (1) the fetch chain's failure pane, while armed and during the wait ──────────────────────────────

test("case 1: a reload that fails while the bar is armed drops the line and disables; the chord is prevented and prints nothing; the file back, the button is live and arms again. A reload that fails during the wait drops the preparing line, disables, and cancels the wait: neither the parked picture's release nor the deadline prints", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const held: any[] = [];
    const requests: string[] = [];
    const { page, errors } = await openViewer(browser, "pane", 900, 700, {
      docs: { [REPORT]: GATED_NOTE },
      serve: (u) => { const p = u.searchParams.get("path") || ""; return u.pathname === "/file" && p.endsWith(QUICK) ? { status: 200, type: "image/svg+xml", body: SVG } : null; },
      before: async (pg: any) => {
        pg.on("request", (r: any) => { requests.push(r.url()); });
        await pg.route((u: URL) => u.origin === ORIGIN && u.pathname === "/file" && (u.searchParams.get("path") || "").endsWith(SLOW), (route: any) => { held.push(route); });   // parked: the <img> stays incomplete
        await pg.route("https://" + REMOTE_HOST + "/**", (route: any) => route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }));
        await pg.evaluate(PAGE_PROBES);
      },
    });
    await waitPlaceholder(page);
    for (let i = 0; i < 50 && held.length === 0; i++) await frames(page, 1);
    assert.equal(held.length, 1, "the slow picture's request is parked");
    // armed, the keyboard on the line's word button, then the file goes
    await page.click("#romp-fileview .fileview-print");
    let b = await bar(page);
    assert.equal(b.phase, "armed"); assert.equal(b.line, ARMED_ONE); assert.deepEqual(b.buttons, [WITH_WORDS, WITHOUT_WORDS]);
    await page.focus('#fileview-print-line button:has-text("' + WITHOUT_WORDS + '")');
    assert.equal((await bar(page)).active, "BUTTON.fileview-btn.fileview-err-act", "the word button holds the keyboard");
    await failReload(page, REPORT);
    b = await bar(page);
    assertDisabled(b, "armed, then the failure pane");
    assert.equal(b.pane, true, "the pane holds the body");
    assert.equal(b.active, "DIV.fileview-body", "FAILS BEFORE: the keyboard went to the viewer's body through its own hand-over (the line's button gone, the Print button not enabled); before, the button took the `disabled` property in the same tick and the keyboard landed on the document's body");
    let k = await chord(page);
    assert.equal(k.open, true); assert.equal(k.prevented, true, "the chord is still prevented over the pane: the browser's raw print would print the pane");
    await pressHard(page);
    assert.equal((await prints(page)).length, 0, "nothing printed over the pane: the chord, a forced click and a programmatic click change nothing");
    assertDisabled(await bar(page), "after the presses");
    // the file back: live, and the placeholder stands again, so the press arms again
    await restore(page, REPORT, GATED_NOTE, MT_A, "#romp-fileview .fileview-md > p");
    await waitPlaceholder(page);
    b = await bar(page);
    assertLive(b, "the text seated again");
    await page.click("#romp-fileview .fileview-print");
    b = await bar(page);
    assert.equal(b.phase, "armed", "the press arms again over the placeholder"); assert.equal(b.line, ARMED_ONE);
    await page.keyboard.press("Escape");
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.phase, null, "Escape disarmed"); assert.equal(b.cardUp, true);
    // the wait: the slow picture incomplete, the deadline shortened so a wait that survived the taking would print
    const incomplete = await page.evaluate(() => Array.from(document.querySelectorAll("#romp-fileview img")).filter((i: any) => !i.complete).length);
    assert.equal(incomplete, 1, "the slow picture is incomplete: its request is parked");
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), PRINT_SETTLE_MS, "the product's deadline before the seam");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(300); });
    await page.click("#romp-fileview .fileview-print");
    await page.click('#fileview-print-line button:has-text("' + WITHOUT_WORDS + '")');
    const t0 = await page.evaluate(() => performance.now());
    b = await bar(page);
    assert.equal(b.phase, "preparing"); assert.equal(b.busy, true); assert.equal(b.ariaBusy, "true");
    assert.equal(b.line, "Preparing 1 picture…", "the wait runs over the slow picture");
    await failReload(page, REPORT);
    b = await bar(page);
    assertDisabled(b, "preparing, then the failure pane");
    assert.equal(b.pane, true);
    assert.equal((await prints(page)).length, 0, "no print at the taking");
    for (const r of held.splice(0)) await r.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG });   // the parked picture lands: a wait still listening would print
    await page.waitForFunction((a: number) => performance.now() - a >= 700, t0, { timeout: 10000 });   // past the shortened deadline: a wait whose timer stood would print
    await frames(page, 2);
    assert.equal((await prints(page)).length, 0, "nothing printed: the wait was cancelled with the body (not orphaned to its deadline or the picture's load)");
    assertDisabled(await bar(page), "after the release and the deadline");
    k = await chord(page);
    assert.equal(k.prevented, true, "the chord over the pane is still prevented");
    assert.equal((await prints(page)).length, 0);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), PRINT_SETTLE_MS, "the seam restored");
    // the file back once more: live
    await restore(page, REPORT, GATED_NOTE, MT_B, "#romp-fileview .fileview-md > p");
    assertLive(await bar(page), "the text seated after the wait's taking");
    assert.ok(!requests.some((u) => u.indexOf("https://" + REMOTE_HOST + "/") === 0), "no request reached the other host through any of it");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

// ── (2) the editor: the chunk wait takes the body, the mount and the plain fallback seat it ─────────

/** The editor chunk the test serves: a textarea in the host, in the handle's shape (value, focus, destroy). */
const EDITOR_JS = "window.__rompEditor = { mount: function (host, opts) { var ta = document.createElement('textarea'); ta.className = 'probe-editor'; ta.value = opts.text; host.appendChild(ta); return { value: function () { return ta.value; }, focus: function () {}, destroy: function () { ta.remove(); } }; } };";

test("case 2: Edit while armed puts the chunk's loader up: the line goes and the button disables, the chord prevented and printing nothing; the plain fallback takes the body and the button stays DISABLED (a press changes nothing: FAILS BEFORE, it was reported in and printed one clipped page); Cancel repaints the text (live, one press prints); Edit again over the re-armed bar, the chunk answering, takes the real mount, which is live and prints the file", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const chunk: any[] = [];
    const parked = (): number => chunk.length;   // read through a call: an assert on the property narrows it to a literal, and the next wait loop would compare 1 with 0
    const { page, errors } = await openViewer(browser, "chat", 900, 700, {
      docs: { [REPORT]: REMOTE_NOTE },
      before: async (pg: any) => {
        // the viewer derives the editor chunk's URL from the page's bundle script tag (editorChunk in file-view.ts): the harness
        // page inlines its bundle, so a tag at /render.js is added for it, answered empty; the chunk's own request is parked
        await pg.route((u: URL) => u.origin === ORIGIN && u.pathname === "/render.js", (route: any) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
        await pg.route((u: URL) => u.origin === ORIGIN && u.pathname === "/editor-chunk.js", (route: any) => { chunk.push(route); });
        await pg.evaluate(() => { const s = document.createElement("script"); s.src = "/render.js?v=probe"; document.head.appendChild(s); });
        await pg.route("https://" + REMOTE_HOST + "/**", (route: any) => route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }));
        await pg.evaluate(PAGE_PROBES);
      },
    });
    await waitPlaceholder(page);
    await page.click("#romp-fileview .fileview-print");
    let b = await bar(page);
    assert.equal(b.phase, "armed"); assert.equal(b.line, ARMED_ONE);
    // Edit: the chunk's loader takes the body
    await page.locator("#romp-fileview .fileview-btn[aria-label='Edit']").click();
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body .fileview-load"), null, { timeout: 10000 });
    for (let i = 0; i < 50 && parked() === 0; i++) await frames(page, 1);
    assert.equal(parked(), 1, "the chunk's request is parked");
    b = await bar(page);
    assertDisabled(b, "the chunk's loader");
    assert.equal(b.loader, true, "the loader holds the body");
    let k = await chord(page);
    assert.equal(k.open, true); assert.equal(k.prevented, true, "the chord is prevented over the chunk's loader");
    await pressHard(page);
    assert.equal((await prints(page)).length, 0, "nothing printed over the loader");
    // the chunk answers with nothing registered: the plain fallback editor, a textarea, takes the body; a print there would be
    // one clipped page of a scrollable control, so the button stays disabled and a press changes nothing
    await chunk.splice(0)[0].fulfill({ status: 200, contentType: "application/javascript", body: "" });
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body textarea.fileview-editor"), null, { timeout: 10000 });
    await frames(page, 1);
    b = await bar(page);
    assertDisabled(b, "the plain fallback editor (FAILS BEFORE: live)");
    assert.equal(b.loader, false);
    await pressHard(page);
    assert.equal((await prints(page)).length, 0, "FAILS BEFORE: a press over the plain fallback printed; nothing prints there now");
    await page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); });   // the textarea took the keyboard at its mount; the chord from a text field is the browser's, so it is read with none focused
    k = await chord(page);
    assert.equal(k.prevented, true, "the chord over the fallback editor is prevented and prints nothing");
    assert.equal((await prints(page)).length, 0);
    assertDisabled(await bar(page), "the plain fallback editor, after the presses");
    // Cancel: the text is back (the Raw view, which Edit switched to), and a press prints it at once (no picture, no placeholder)
    await page.click('#romp-fileview .fileview-bar button:has-text("Cancel")');
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body .fv-cl"), null, { timeout: 10000 });
    await frames(page, 1);
    assertLive(await bar(page), "the text repainted after Cancel");
    const printed = await page.evaluate(() => { (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click(); return (window as any).__prints.length; });
    assert.equal(printed, 1, "one press printed the Raw view at once");
    // Rendered again: the placeholder is back, the press arms, and Edit takes the body once more
    await page.evaluate(() => { (window as any).__seam.setMode("rendered"); });
    await waitPlaceholder(page);
    await page.click("#romp-fileview .fileview-print");
    b = await bar(page);
    assert.equal(b.phase, "armed", "armed again over the placeholder");
    await page.locator("#romp-fileview .fileview-btn[aria-label='Edit']").click();
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body .fileview-load"), null, { timeout: 10000 });
    for (let i = 0; i < 50 && parked() === 0; i++) await frames(page, 1);
    assert.equal(parked(), 1, "the chunk is asked for again (a failed load clears the latch)");
    assertDisabled(await bar(page), "the second chunk wait");
    assert.equal((await prints(page)).length, 1, "nothing more printed");
    // the chunk answers with an editor: the real mount seats the body, and a press prints the file (the CodeMirror mount prints
    // the whole file, the review measured: 6 to 7 pages of a hundred paragraphs, so this road stays live)
    await chunk.splice(0)[0].fulfill({ status: 200, contentType: "application/javascript", body: EDITOR_JS });
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body .fileview-cm textarea.probe-editor"), null, { timeout: 10000 });
    await frames(page, 1);
    b = await bar(page);
    assertLive(b, "the editor's mount holds the body");
    assert.equal(b.loader, false);
    const printedCm = await page.evaluate(() => { (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click(); return (window as any).__prints.length; });
    assert.equal(printedCm, 2, "one press over the editor's mount printed at once");
    const pCm = await prints(page);
    assert.equal(pCm[1].cm, true, "…with the mount in the body at the print"); assert.equal(pCm[1].editor, false);
    await frames(page, 1);
    assertLive(await bar(page), "the editor's mount after the print");
    await page.click('#romp-fileview .fileview-bar button:has-text("Cancel")');
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body .fv-cl"), null, { timeout: 10000 });
    await frames(page, 1);
    assertLive(await bar(page), "the text repainted after the second Cancel");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

// ── (3) a picture opened directly: imgFailed's pane over bytes that will not decode ─────────────────

test("case 3: a picture opened directly, then a reload whose bytes will not decode: imgFailed's pane disables the button; the chord over it is prevented and prints nothing; good bytes seat the picture again and the chord prints", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: SHORT, [PIC]: SVG }, before: async (pg: any) => { await pg.evaluate(PAGE_PROBES); } });
    await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [PIC, SID]);   // a replace-open: the picture in place of the note
    await page.waitForFunction(() => { const i = document.querySelector("#romp-fileview img.fileview-img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0; }, null, { timeout: 10000 });
    await frames(page, 2);
    assertLive(await bar(page), "the picture seated");
    let k = await chord(page);
    assert.equal(k.prevented, true);
    let p = await prints(page);
    assert.equal(p.length, 1, "the chord printed the picture at once (one print: the replaced open's listener is gone)");
    assert.equal(p[0].incomplete, 0); assert.equal(p[0].pane, false);
    // bytes that will not decode: imgFailed's pane takes the body
    await page.evaluate((a: [string, string, string]) => { const w = window as any; w.__docs[a[0]] = a[1]; w.__mtime = a[2]; w.__seam.reload(); }, [PIC, BAD_BYTES, MT_C]);
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body > .fileview-err") && !document.querySelector("#romp-fileview img.fileview-img"), null, { timeout: 10000 });
    await frames(page, 1);
    const b = await bar(page);
    assertDisabled(b, "imgFailed's pane");
    assert.equal(b.pane, true, "the pane holds the body");
    k = await chord(page);
    assert.equal(k.open, true); assert.equal(k.prevented, true, "the chord is prevented over the pane");
    await pressHard(page);
    assert.equal((await prints(page)).length, 1, "nothing more printed over the pane");
    assertDisabled(await bar(page), "after the presses");
    // good bytes again: the picture seats, and the chord prints
    await page.evaluate((a: [string, string, string]) => { const w = window as any; w.__docs[a[0]] = a[1]; w.__mtime = a[2]; w.__seam.reload(); }, [PIC, SVG, MT_D]);
    await page.waitForFunction(() => { const i = document.querySelector("#romp-fileview img.fileview-img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0; }, null, { timeout: 10000 });
    await frames(page, 2);
    assertLive(await bar(page), "the picture seated again");
    k = await chord(page);
    assert.equal(k.prevented, true);
    p = await prints(page);
    assert.equal(p.length, 2, "the chord printed the picture again"); assert.equal(p[1].incomplete, 0); assert.equal(p[1].pane, false);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

// ── (4) the URL viewer's failure ────────────────────────────────────────────────────────────────────

test("case 4: the URL viewer over a document that fails to load: the button stands disabled over the pane, the chord prevented and printing nothing", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "chat", 900, 700, { url: "/notes/missing.md", urls: {}, waitFor: "#romp-fileview .fileview-body > .fileview-err", before: async (pg: any) => { await pg.evaluate(PAGE_PROBES); } });
    const b = await bar(page);
    assertDisabled(b, "the URL viewer's pane");
    assert.equal(b.pane, true);
    const k = await chord(page);
    assert.equal(k.open, true); assert.equal(k.prevented, true, "the chord is prevented over the pane");
    await pressHard(page);
    assert.equal((await prints(page)).length, 0, "nothing printed");
    assertDisabled(await bar(page), "after the presses");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

// ── (5) the Comments panel's PDF pages: the loader alone disables, a kept frame and the drawn pages are live ──────────

/** The PDF chunk the test serves: a render that waits on `window.__pdfGate` (a promise the test resolves through
 *  `window.__pdfRelease`) and then mounts one page shell in the chunk's shape (a `.fileview-pdf` root, a `.fileview-pdf-page`
 *  wrapper with its canvas) into the host, answering the handle the viewer expects; dispose removes the root. */
const PDF_CHUNK_JS = "window.__rompPdf = { render: function (bytes, host, opts) { var gate = window.__pdfGate || Promise.resolve(); return gate.then(function () { var root = document.createElement('div'); root.className = 'fileview-pdf'; var wrap = document.createElement('div'); wrap.className = 'fileview-pdf-page'; var c = document.createElement('canvas'); c.className = 'fileview-pdf-canvas'; c.width = 200; c.height = 260; wrap.appendChild(c); root.appendChild(wrap); host.appendChild(root); window.__pdfRenders = (window.__pdfRenders || 0) + 1; return { pages: 1, dispose: function () { root.remove(); } }; }); } };";

test("case 5: the Comments panel's PDF pages flow. The attempt over a kept frame leaves the button live and a press takes the PDF road (the /file tab); page 1 mounted, live and the same road; a reload with the pages up puts the loader alone in the body with the kind known to be a PDF: the button stays live, and a press and the chord each open the tab at once (FAILS BEFORE, at the round-2 head: disabled over the pages loader, the chord swallowed and no tab)", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, {
      docs: { [REPORT]: SHORT },
      before: async (pg: any) => {
        await pg.route((u: URL) => u.origin === ORIGIN && u.pathname === "/render.js", (route: any) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
        await pg.route((u: URL) => u.origin === ORIGIN && u.pathname === "/pdf-chunk.js", (route: any) => route.fulfill({ status: 200, contentType: "application/javascript", body: PDF_CHUNK_JS }));
        await pg.evaluate(() => { const s = document.createElement("script"); s.src = "/render.js?v=probe"; document.head.appendChild(s); });   // the viewer derives the chunk's URL from the page's bundle script tag (pdfChunkLoad)
        await pg.evaluate(PAGE_PROBES);
      },
    });
    // the PDF, through the page's fetch (the media leg's idiom): the kernel's Content-Type paints the frame
    await page.evaluate(([p, sid, pdf]: [string, string, string]) => {
      const w = window as any; const blob = new Blob([pdf], { type: "application/pdf" }); const prev = w.fetch;
      w.fetch = async function (url: any, init: any) { const m = /[?&]path=([^&]*)/.exec(String(url)); if (m && decodeURIComponent(m[1]) === p && !(init && init.method === "HEAD")) return new Response(blob, { status: 200, headers: { "Content-Type": "application/pdf", "X-Romp-Mtime-Ns": w.__mtime } }); return prev(url, init); };
      w.FV.openFileView(p, sid, null);
    }, [PDF, SID, PDF_BYTES]);
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview iframe.fileview-frame"), null, { timeout: 10000 });
    await frames(page, 3);
    let b = await bar(page);
    assertLive(b, "the frame seated");
    const renders = (): Promise<number> => page.evaluate(() => (window as any).__pdfRenders || 0);
    // the press is programmatic (the media leg's idiom): with the panel open its region overlay (.fc-overlay) stands over the
    // card and intercepts a pointer, which Playwright's click refuses to deliver through it
    const pressPrint = (): Promise<void> => page.evaluate(() => { (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click(); });
    const gate = (): Promise<void> => page.evaluate(() => { const w = window as any; w.__pdfGate = new Promise<void>((r) => { w.__pdfRelease = r; }); });
    const release = async (): Promise<void> => { await page.evaluate(() => { (window as any).__pdfRelease(); }); };
    // the panel opens over the frame: the attempt keeps the frame under the loader inside its column, so the body still holds the
    // document and the button is live; a press takes the PDF road: no frame window holds the PDF in the headless shell, so the tab
    await gate();
    await openPanel(page);
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body .fileview-pdffall > .fileview-load") && !!document.querySelector("#romp-fileview .fileview-body > .fileview-pdfhost"), null, { timeout: 10000 });
    b = await bar(page);
    assertLive(b, "the attempt over the kept frame");
    assert.equal(b.loader, true, "the loader stands inside the frame's column"); assert.equal(b.bodyLoader, false, "…not as the body's content");
    assert.equal(await renders(), 0, "page 1 is not drawn yet");
    await pressPrint();
    b = await bar(page);
    assert.equal(b.opens, 1, "the press took the PDF road: the /file tab opened"); assert.equal(b.line, TAB_WORDS); assert.equal(b.phase, null);
    assert.equal((await prints(page)).length, 0, "the page's own print never runs for a PDF");
    // page 1 drawn: the loader and the frame's column go, the pages are the body, and the button is live
    await release();
    await page.waitForFunction(() => (window as any).__pdfRenders === 1 && !document.querySelector("#romp-fileview .fileview-body .fileview-load") && !document.querySelector("#romp-fileview iframe.fileview-frame"), null, { timeout: 10000 });
    await frames(page, 2);
    b = await bar(page);
    assert.equal(b.line, TAB_WORDS, "the notice stands at rest until the next press"); assert.equal(b.ariaDisabled, null, "the pages seated: live"); assert.equal(b.disabled, false); assert.equal(b.phase, null);
    await pressPrint();
    b = await bar(page);
    assert.equal(b.opens, 2, "the press over the pages took the PDF road again"); assert.equal(b.line, TAB_WORDS);
    // a reload with the pages up: no frame to keep, so the loader and the empty host hold the body until page 1 is drawn again;
    // the kind is known to be a PDF, so the button stays live and a press or the chord takes the PDF road at once (the tab: no
    // frame stands to print through), as the build before the derived readiness did
    await gate();
    await page.evaluate((mt: string) => { const w = window as any; w.__mtime = mt; w.__seam.reload(); }, MT_E);
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body > .fileview-load") && !document.querySelector("#romp-fileview iframe.fileview-frame"), null, { timeout: 10000 });
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.ariaDisabled, null, "the pages loader in the body with the kind a PDF: live (FAILS BEFORE: disabled)"); assert.equal(b.disabled, false); assert.equal(b.phase, null, "at rest");
    assert.equal(b.line, TAB_WORDS, "the last press's notice stands until the next press");
    assert.equal(b.bodyLoader, true, "the loader is the body's content"); assert.equal(await renders(), 1, "page 1 of the reload is not drawn yet");
    await pressPrint();
    b = await bar(page);
    assert.equal(b.opens, 3, "FAILS BEFORE: the press over the pages loader took the PDF road and opened the tab"); assert.equal(b.line, TAB_WORDS); assert.equal(b.phase, null);
    let k = await chord(page);
    assert.equal(k.open, true); assert.equal(k.prevented, true, "the chord over the loader is prevented (the browser's raw print would print the loader page)");
    b = await bar(page);
    assert.equal(b.opens, 4, "FAILS BEFORE: the chord over the pages loader opened the tab too"); assert.equal((await prints(page)).length, 0, "the page's own print never runs for a PDF");
    assert.equal(b.line, TAB_WORDS); assert.equal(b.phase, null); assert.equal(b.ariaDisabled, null, "still live");
    // page 1 drawn again: live, and the PDF road
    await release();
    await page.waitForFunction(() => (window as any).__pdfRenders === 2 && !document.querySelector("#romp-fileview .fileview-body > .fileview-load"), null, { timeout: 10000 });
    await frames(page, 2);
    b = await bar(page);
    assert.equal(b.ariaDisabled, null, "page 1 drawn again: live"); assert.equal(b.phase, null); assert.equal(b.line, TAB_WORDS, "the last press's notice stands until the next press");
    await pressPrint();
    b = await bar(page);
    assert.equal(b.opens, 5, "the press took the PDF road"); assert.equal(b.line, TAB_WORDS);
    assert.equal((await prints(page)).length, 0, "the page's own print never ran");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
