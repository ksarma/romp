// Print's disabled phase AFTER a successful paint (file-print.ts, P7 of the print follow-on to plans/markdown-viewer.md's
// Slice 3, item 12), over the real viewer in headless Chromium through real-viewer-leg.ts. file-print-browser.test.ts
// case 6 drives the disabled phase for an open's own loader alone: the flow starts disabled and the first paint rests it.
// The other reports the viewer makes, `print.bodyIn(false)` where a pane or a loader takes a body that HELD the file
// (file-view.ts: the fetch chain's failure pane, imgFailed's pane over a picture that would not decode, the editor's chunk
// wait, the URL viewer's failure) and `print.bodyIn(true)` where the editor's mount or its plain fallback seats the body
// again, were held by source-text pins (tools/markdown-viewer-plan-print.test.mjs) and by the machine's node tests, so a
// driver or viewer change that stopped taking the button down with the body left every test green (a copy of the driver
// with bodyIn ignoring false was green under the slice's three modules). This leg executes each taking and each seating:
// (1) a gated note on the pane, the bar armed, then a reload that fails (the file gone): the armed line goes, the button
// disables (the attribute, aria-disabled, `data-print` reading disabled, the armed dress off), the chord is still prevented
// and prints nothing, a forced click and a programmatic click print nothing; the file back and its text seated, the button
// is live and the next press arms again. Then the wait: "Print without them" over a picture whose route is parked, the
// deadline shortened through the seam, and a reload that fails during the wait: the preparing line goes, the button
// disables, and neither the parked picture's release nor the deadline prints (the wait was cancelled, not orphaned); no
// request reached the other host through any of it. (2) the editor on the chat modal: Edit while armed puts the chunk's
// loader up (the chunk's request parked by the test, which serves the page a bundle script tag to derive it from): the line
// goes and the button disables, the chord prevented and printing nothing; the chunk answering with nothing registered
// takes the plain fallback, which seats the body (live); Cancel repaints the text (live, and one press prints the Raw
// view); Edit again over the re-armed bar, the chunk answering with an editor, takes the real mount (live). (3) a picture
// opened directly on the pane: a reload whose bytes will not decode paints imgFailed's pane and disables; the chord over
// it prints nothing; good bytes seat the picture again and the chord prints. (4) the URL viewer over a document that fails
// to load: the button stands disabled over the pane, the chord prevented and printing nothing. Checked red against the
// viewer with one report removed while this leg was written (the fetch pane's report: case 1 fails at the standing line;
// imgFailed's: case 3 at the live button over the pane; the chunk wait's: case 2 at the standing line). Skips loudly
// without a browser. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, REPORT, ROOT, ORIGIN, SID } from "./real-viewer-leg";
import { WITH_WORDS, WITHOUT_WORDS, PRINT_SETTLE_MS } from "./file-print";

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
const MT_A = "1757145600000000011", MT_B = "1757145600000000012", MT_C = "1757145600000000013", MT_D = "1757145600000000014";
const ARMED_ONE = "1 picture from another host is not loaded.";

type Print = { incomplete: number; pane: boolean; line: boolean };
type Key = { prevented: boolean; open: boolean };
type Bar = { present: boolean; disabled: boolean; ariaDisabled: string | null; phase: string | null; on: boolean; expanded: string | null; busy: boolean; ariaBusy: string | null; line: string | null; buttons: string[]; pane: boolean; loader: boolean; cardUp: boolean };

/** The page's record of the print stub's calls and the window's chords, and the bar as it stands. */
const PAGE_PROBES = () => {
  const w = window as any;
  w.__prints = []; w.__keys = [];
  const imgs = () => Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[];
  w.print = () => { w.__prints.push({ incomplete: imgs().filter((i) => !i.complete).length, pane: !!document.querySelector("#romp-fileview .fileview-body > .fileview-err"), line: !!document.getElementById("fileview-print-line") }); };
  window.addEventListener("keydown", (e) => { if (e.key.toLowerCase() === "p" && (e.ctrlKey || e.metaKey)) w.__keys.push({ prevented: e.defaultPrevented, open: document.body.classList.contains("fileview-open") }); });
  w.__bar = (): Bar => {
    const b = document.querySelector("#romp-fileview .fileview-bar .fileview-print") as HTMLButtonElement | null;
    const line = document.getElementById("fileview-print-line");
    return { present: !!b, disabled: !!b && b.disabled, ariaDisabled: b ? b.getAttribute("aria-disabled") : null, phase: b ? (b.dataset.print || null) : null, on: !!b && b.classList.contains("on"), expanded: b ? b.getAttribute("aria-expanded") : null,
      busy: !!b && b.classList.contains("fileview-busy"), ariaBusy: b ? b.getAttribute("aria-busy") : null,
      line: line ? (line.firstChild && line.firstChild.nodeType === 3 ? (line.firstChild.textContent || "") : line.textContent) : null, buttons: line ? Array.from(line.querySelectorAll("button")).map((x) => x.textContent || "") : [],
      pane: !!document.querySelector("#romp-fileview .fileview-body > .fileview-err"), loader: !!document.querySelector("#romp-fileview .fileview-body .fileview-load"), cardUp: !!document.getElementById("romp-fileview") };
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
/** The disabled dress, whole: the attribute, aria-disabled, the phase, no armed or busy dress, no line. */
function assertDisabled(b: Bar, label: string): void {
  assert.equal(b.present, true, label + ": the button is in the bar");
  assert.equal(b.disabled, true, label + ": disabled");
  assert.equal(b.ariaDisabled, "true", label + ": aria-disabled");
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
    // armed, then the file goes
    await page.click("#romp-fileview .fileview-print");
    let b = await bar(page);
    assert.equal(b.phase, "armed"); assert.equal(b.line, ARMED_ONE); assert.deepEqual(b.buttons, [WITH_WORDS, WITHOUT_WORDS]);
    await failReload(page, REPORT);
    b = await bar(page);
    assertDisabled(b, "armed, then the failure pane");
    assert.equal(b.pane, true, "the pane holds the body");
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

test("case 2: Edit while armed puts the chunk's loader up: the line goes and the button disables, the chord prevented and printing nothing; the plain fallback seats the body (live); Cancel repaints the text (live, one press prints); Edit again over the re-armed bar, the chunk answering, takes the real mount (live)", { timeout: 120000 }, async (t) => {
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
    // the chunk answers with nothing registered: the plain fallback editor seats the body
    await chunk.splice(0)[0].fulfill({ status: 200, contentType: "application/javascript", body: "" });
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body textarea.fileview-editor"), null, { timeout: 10000 });
    await frames(page, 1);
    b = await bar(page);
    assertLive(b, "the plain fallback holds the body");
    assert.equal(b.loader, false);
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
    // the chunk answers with an editor: the real mount seats the body
    await chunk.splice(0)[0].fulfill({ status: 200, contentType: "application/javascript", body: EDITOR_JS });
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body .fileview-cm textarea.probe-editor"), null, { timeout: 10000 });
    await frames(page, 1);
    b = await bar(page);
    assertLive(b, "the editor's mount holds the body");
    assert.equal(b.loader, false);
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
