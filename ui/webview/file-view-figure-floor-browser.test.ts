// The figure control's floor against a body whose width changes (plans/markdown-viewer.md, "Follow-on: Link navigation",
// L3), driven through the REAL viewer in headless Chromium (real-viewer-leg.ts: the chat modal, file-view.ts bundled from
// this tree with the real Comments panel, styles.css, the /file fetch stub, a route for the figures' own requests). The
// floor (FIGOPEN_MIN_PX, 48 CSS px on either side) was read ONCE, at the picture's load, so a figure that loaded above it
// and was then narrowed under it (the pane dragged narrower, the Comments aside opening) kept its control, which hung
// over the 32 px figure and took the click meant for the prose, while the same note reopened at the narrow width had none.
// Read off the DOM and the layout: (1) a 761 by 76 figure at a 900 px viewport wears its control; the viewport narrowed so
// the column shrinks the figure under the floor, the control leaves at the body's ResizeObserver report (the DOM polled up
// to a second for the verdict); widened back, the control returns; a page opened at the narrow width never gets one; (2) the
// Comments aside opening narrows the body under the floor and the control leaves, closing the aside brings it back; (3) the
// hardening: a synthetic click dispatched on the img inside a gated placeholder (an element no pointer can reach) is the
// gate listener's, which prevents default as it restores the img; the figure listener, second on the same event, stands
// down (window.open not called, the trail unmoved), and the restored figure gets its control at its load and opens its tab
// from a real click on that control; (4) the file review's closing check: a picture the browser already holds (the viewer
// closed and the report re-opened; no request leaves for it) is complete at the paint and decided then, from its natural size,
// since mdBlock's box is not in the document yet, and its load event, which fires all the same, decides it again over the
// laid-out box, so at a 381 px re-open the paint's control leaves at the load and at 900 it stands (the record had said every
// figure is fetching at the paint, which a held picture is not; the first open's picture, on the wire at the paint, gets none
// until its load, and the leg records that too); (5) the text-size road (the file review's round 2): A- and Ctrl + wheel steps
// reflow a column-capped figure at a constant body width, and the control leaves under the floor and returns above it, since
// the decision hangs on the figure's own box (watchFigureBoxes) and not on the width watch alone; (6) a control holding the
// keyboard when the width's change removes it hands the keyboard to the viewer's body, so PageDown scrolls (the file review,
// ui-4); (7) the viewer hidden (display:none on its card, as the dashboard hides a pane at a narrow viewport): the observer's
// 0 by 0 report for the hidden figure runs no decision, so a figure under the floor at its real width gains no control while
// hidden, and the show's report of the real box decides it (before the guard, figureBox fell back to the natural size over the
// 0 by 0 report and a control was added while hidden, then removed at the show: an add and a remove the reader never saw).
// Skipped LOUDLY where playwright has no browser (CI installs none). Synthetic
// values only: the notes-api world, a placeholder session id, example.invalid addresses, /repo/notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, closePanel, frames, ROOT, REPORT, SID, PARA } from "./real-viewer-leg";

const WIDE = ROOT + "/docs/figs/wide.svg";
const PROTO = "//example.invalid/pic.svg";
const PROTO_ABS = "http://example.invalid/pic.svg";   // the page's origin is http, so the browser and absUrl resolve `//` to it
const FLOOR = 48;                                       // FIGOPEN_MIN_PX, pinned at source by file-view-figure-shapes.test.ts
const svg = (w: number, h: number, fill: string): string => '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '"><rect width="' + w + '" height="' + h + '" fill="' + fill + '"/></svg>';
// the report: a wide, short figure (761 by 76: above the floor at a wide column, under it once the column falls below about
// 480 px), a sentence under it, a protocol-relative figure on an unlisted host (a gated placeholder), enough prose to scroll
const REPORT_TEXT = "# Report\n\n![wide](figs/wide.svg)\n\nA sentence under the figure.\n\n![proto](" + PROTO + ")\n\n"
  + Array.from({ length: 30 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const DOCS: Record<string, string> = { [REPORT]: REPORT_TEXT, [WIDE]: svg(761, 76, "#468") };

type Fig = { w: number; h: number; control: boolean; bodyW: number };
/** The wide figure (the box's first img): its laid-out box, whether a control stands after its anchor (the img, or the
 *  regions layer's wrap around it while the panel is open), and the body's width. */
const figure = (page: any): Promise<Fig> => page.evaluate(() => {
  const img = document.querySelector(".fileview-md img") as HTMLImageElement;
  const r = img.getBoundingClientRect();
  let a: Element = img;
  while (a.parentElement && (a.parentElement.classList.contains("fc-imgwrap") || a.parentElement.localName === "picture")) a = a.parentElement;
  const n = a.nextElementSibling;
  return { w: r.width, h: r.height, control: !!(n && n.hasAttribute("data-fv-figopen")), bodyW: (document.querySelector(".fileview-body") as HTMLElement).clientWidth };
});
/** Wait up to a second for the wide figure's control to be present (`want` true) or absent; the verdict is read after, by
 *  `figure`, so a miss fails on the measured state and not on the wait. */
async function settle(page: any, want: boolean): Promise<void> {
  try {
    await page.waitForFunction((w: boolean) => {
      const img = document.querySelector(".fileview-md img") as HTMLImageElement | null;
      if (!img) return false;
      let a: Element = img;
      while (a.parentElement && (a.parentElement.classList.contains("fc-imgwrap") || a.parentElement.localName === "picture")) a = a.parentElement;
      const n = a.nextElementSibling;
      return !!(n && n.hasAttribute("data-fv-figopen")) === w;
    }, want, { timeout: 1000 });
  } catch { /* read below */ }
  await frames(page, 1);
}
const fmt = (f: Fig): string => "body " + Math.round(f.bodyW) + ", figure " + Math.round(f.w) + "x" + Math.round(f.h) + ", control " + (f.control ? "present" : "absent");
const opened = (page: any): Promise<string[]> => page.evaluate(() => (window as any).__opened.splice(0));
const base = (page: any): Promise<string | null> => page.locator(".fileview-base").textContent();
const backDisabled = (page: any): Promise<string | null> => page.evaluate(() => { const b = document.querySelector(".fileview-nav-back"); return b ? b.getAttribute("aria-disabled") : "no button"; });

/** The report open in the chat modal at the viewport size, the wide figure served from the /file route and the web one from a
 *  route on its host, window.open stubbed to a record, the wide figure loaded. */
async function openReport(browser: any, width: number, height: number): Promise<{ page: any; errors: string[] }> {
  const o = await openViewer(browser, "chat", width, height, {
    docs: DOCS,
    serve: (u) => { const p = u.pathname === "/file" ? u.searchParams.get("path") || "" : ""; return DOCS[p] !== undefined && /\.svg$/.test(p) ? { status: 200, type: "image/svg+xml", body: DOCS[p] } : null; },
  });
  await o.page.context().route(/^https?:\/\/example\.invalid\//, (route: any) => route.fulfill({ status: 200, contentType: "image/svg+xml", body: svg(300, 200, "#333") }));
  await o.page.evaluate(() => { const w = window as any; w.__opened = []; window.open = ((u: unknown) => { w.__opened.push(String(u)); return { opener: null }; }) as unknown as typeof window.open; });
  await o.page.waitForFunction(() => { const i = document.querySelector(".fileview-md img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0; }, null, { timeout: 10000 });
  await frames(o.page, 2);
  return o;
}

test("in a browser: a 761 by 76 figure wears its control at a 900 px viewport, loses it when the viewport narrows the column so the figure falls under the floor, gets it back when the viewport widens, and a page opened at the narrow width never gets one", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReport(browser, 900, 600);
    await settle(page, true);
    const wide = await figure(page);
    t.diagnostic("wide: " + fmt(wide));
    assert.ok(wide.w >= FLOOR && wide.h >= FLOOR, "the figure is above the floor on both sides at the wide column: " + fmt(wide));
    assert.equal(wide.control, true, "the control stands at the wide column: " + fmt(wide));
    // the viewport narrowed: the column shrinks the figure in its own ratio, under the floor on its short side
    await page.setViewportSize({ width: 381, height: 600 });
    await settle(page, false);
    const narrow = await figure(page);
    t.diagnostic("narrowed: " + fmt(narrow));
    assert.ok(narrow.h < FLOOR, "the figure fell under the floor on its short side: " + fmt(narrow));
    // FAILS BEFORE: the floor was read once, at the load; the control stayed (present at 323 by 32) and hung over the figure
    assert.equal(narrow.control, false, "the control left at the width's report: " + fmt(narrow));
    // widened again: the figure is back above the floor and the control returns
    await page.setViewportSize({ width: 900, height: 600 });
    await settle(page, true);
    const again = await figure(page);
    t.diagnostic("widened: " + fmt(again));
    assert.ok(again.w >= FLOOR && again.h >= FLOOR, "above the floor again: " + fmt(again));
    assert.equal(again.control, true, "the control is back: " + fmt(again));
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
    // a page opened AT the narrow width: the load's read finds the figure under the floor and no control stands
    const fresh = await openReport(browser, 381, 600);
    await settle(fresh.page, false);
    const opened = await figure(fresh.page);
    t.diagnostic("reopened narrow: " + fmt(opened));
    assert.ok(opened.h < FLOOR, "under the floor from the first paint: " + fmt(opened));
    assert.equal(opened.control, false, "no control on a figure that loaded under the floor: " + fmt(opened));
    assert.deepEqual(fresh.errors, [], "no page errors");
    await fresh.page.close();
  });
});

test("in a browser: the Comments aside opening narrows the body so the figure falls under the floor and the control leaves; closing the aside brings the control back", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReport(browser, 800, 600);
    await settle(page, true);
    const closed = await figure(page);
    t.diagnostic("aside closed: " + fmt(closed));
    assert.ok(closed.w >= FLOOR && closed.h >= FLOOR, "above the floor with the aside closed: " + fmt(closed));
    assert.equal(closed.control, true, "the control stands with the aside closed: " + fmt(closed));
    await openPanel(page);
    await settle(page, false);
    const open = await figure(page);
    t.diagnostic("aside open: " + fmt(open));
    assert.ok(open.bodyW < closed.bodyW, "the aside took width from the body: " + fmt(open));
    assert.ok(open.h < FLOOR, "the figure fell under the floor beside the aside: " + fmt(open));
    // FAILS BEFORE: the control stayed on the narrowed figure
    assert.equal(open.control, false, "the control left at the aside's width report: " + fmt(open));
    await closePanel(page);
    await settle(page, true);
    const back = await figure(page);
    t.diagnostic("aside closed again: " + fmt(back));
    assert.ok(back.h >= FLOOR, "above the floor again: " + fmt(back));
    assert.equal(back.control, true, "the control is back: " + fmt(back));
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser: a synthetic click dispatched on the img inside a gated placeholder is the gate listener's alone; the figure listener, second on the same event, stands down (no tab, the trail unmoved), the restored figure gets its control at its load, and a real click on that control opens its tab", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReport(browser, 900, 600);
    const gated = await page.evaluate(() => {
      const i = document.querySelector('[data-act="fv-load"] img') as HTMLElement | null;
      return i ? { display: getComputedStyle(i).display, rects: i.getClientRects().length } : null;
    });
    assert.deepEqual(gated, { display: "none", rects: 0 }, "the placeholder's img is display:none with no box: no pointer can reach it, so the click below is synthetic by construction");
    await page.evaluate(() => { document.querySelector('[data-act="fv-load"] img')!.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true })); });
    // the gate's own work: the img restored in the placeholder's place, loaded from its host, its control added at the load
    await page.waitForFunction(() => { const i = document.querySelectorAll(".fileview-md img")[1] as HTMLImageElement | undefined; return !!i && !i.closest('[data-act="fv-load"]') && i.complete && i.naturalWidth > 0 && !!(i.nextElementSibling && i.nextElementSibling.hasAttribute("data-fv-figopen")); }, null, { timeout: 10000 });
    await frames(page, 3);
    // FAILS BEFORE: the figure listener read the restored img as a bare figure and opened its address in a tab
    assert.deepEqual(await opened(page), [], "the figure listener stood down on the click the gate listener answered: window.open was not called");
    assert.equal(await base(page), "report.md", "the viewer shows the report still");
    assert.equal(await backDisabled(page), "true", "the trail did not move");
    // the listener is live for a real click: the restored figure's control opens the tab at the address the browser resolved
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[1].scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    await page.locator(".fileview-md [data-fv-figopen]").nth(1).click();
    await frames(page, 3);
    assert.deepEqual(await opened(page), [PROTO_ABS], "a tab from the control's own click");
    assert.equal(await base(page), "report.md", "never the viewer");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

type Paint = { complete: boolean; naturalWidth: number; control: boolean; loadsBefore: number } | null;
type Load = { box: [number, number]; controlBefore: boolean };
type Probe = { paint: Paint; loads: Load[] };
/** The paint probe for the held picture's case (the header's (4)), installed before the first open (openViewer's `before`): a
 *  MutationObserver over the document's body records the wide figure's state the first time an open's Rendered box holds it
 *  (the records are delivered as a microtask after the paint's own run and before the load event's task, so the record is the
 *  paint's outcome: whether the browser already held the picture, `complete`, and whether the paint's decision put a control
 *  after it); a capture-phase load listener on the document, which runs before the body's own (armFigureControls), records at
 *  each of the figure's load events its laid-out box and whether a control stood before that load's decision. The width
 *  watch's first report describes the size at observe() and runs no repaint (openFileView), so between the paint and the load
 *  nothing else decides the figure. `window.__probeReset()` starts the next open's record. */
const armPaintProbe = (page: any): Promise<void> => page.evaluate(() => {
  const w = window as any;
  const wide = (i: HTMLImageElement): boolean => /wide\.svg/.test(i.currentSrc || i.src);
  const control = (img: Element): boolean => {
    let a: Element = img;
    while (a.parentElement && (a.parentElement.classList.contains("fc-imgwrap") || a.parentElement.localName === "picture")) a = a.parentElement;
    const n = a.nextElementSibling;
    return !!(n && n.hasAttribute("data-fv-figopen"));
  };
  w.__probeReset = () => { w.__probe = { paint: null, loads: [] }; };
  w.__probeReset();
  new MutationObserver(() => {
    if (w.__probe.paint) return;
    const img = (Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]).find(wide);
    if (!img) return;
    w.__probe.paint = { complete: img.complete, naturalWidth: img.naturalWidth, control: control(img), loadsBefore: w.__probe.loads.length };
  }).observe(document.body, { childList: true, subtree: true });
  document.addEventListener("load", (e) => {
    const img = e.target as HTMLImageElement;
    if (!(img instanceof HTMLImageElement) || !wide(img) || !img.closest(".fileview-md")) return;
    const r = img.getBoundingClientRect();
    w.__probe.loads.push({ box: [Math.round(r.width), Math.round(r.height)], controlBefore: control(img) });
  }, true);
});
const probe = (page: any): Promise<Probe> => page.evaluate(() => (window as any).__probe);
/** The viewer closed through its own export and the report opened again at the viewport size, the probe's record started over. */
async function reopen(page: any, width: number, height: number): Promise<void> {
  await page.evaluate(() => { (window as any).FV.closeFileView(); (window as any).__probeReset(); });
  await page.waitForFunction(() => !document.getElementById("romp-fileview"), null, { timeout: 5000 });
  await page.setViewportSize({ width, height });
  await frames(page, 2);
  await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
  await page.waitForFunction(() => (window as any).__probe.loads.length >= 1, null, { timeout: 10000 });
}

test("in a browser: a picture the browser already holds (the viewer closed and the report re-opened) is complete at the paint and decided then, from its natural size since the box is not in the document yet; its load event fires all the same and decides it again over the laid-out box, so at a 381 px re-open the paint's control leaves at the load and at 900 it stands; the first open's picture, on the wire at the paint, gets none until its load", async (t) => {
  await inBrowser(t, async (browser) => {
    let wideAsked = 0;   // the wide figure's requests at the /file route: the browser's own, from the img (the page's fetch stub never sees them)
    const { page, errors } = await openViewer(browser, "chat", 900, 600, {
      docs: DOCS,
      serve: (u) => { const p = u.pathname === "/file" ? u.searchParams.get("path") || "" : ""; if (p === WIDE) wideAsked++; return DOCS[p] !== undefined && /\.svg$/.test(p) ? { status: 200, type: "image/svg+xml", body: DOCS[p] } : null; },
      before: armPaintProbe,
    });
    await page.waitForFunction(() => (window as any).__probe.loads.length >= 1, null, { timeout: 10000 });
    await settle(page, true);
    const first = await probe(page);
    const firstFig = await figure(page);
    t.diagnostic("first open at 900: " + JSON.stringify(first) + "; " + fmt(firstFig) + "; wide asked " + wideAsked);
    // the first open: the picture was on the wire at the paint, so the paint decided against a control, and the load brought it
    assert.ok(first.paint, "the paint was recorded");
    assert.deepEqual([first.paint.complete, first.paint.control, first.paint.loadsBefore], [false, false, 0], "on the wire at the paint: not complete, no control, before any load: " + JSON.stringify(first.paint));
    assert.equal(first.loads.length, 1, "one load event");
    assert.equal(first.loads[0].controlBefore, false, "no control stood when the load arrived");
    assert.equal(firstFig.control, true, "the load's decision added it: " + fmt(firstFig));
    assert.equal(wideAsked, 1, "one request for the picture");
    // the viewer closed and the report re-opened at 381 px: the browser holds the picture
    await reopen(page, 381, 600);
    await settle(page, false);
    const narrow = await probe(page);
    const narrowFig = await figure(page);
    t.diagnostic("re-opened at 381: " + JSON.stringify(narrow) + "; " + fmt(narrowFig) + "; wide asked " + wideAsked);
    assert.equal(wideAsked, 1, "no request left for the picture at the re-open: the browser holds it");
    assert.ok(narrow.paint, "the paint was recorded");
    assert.deepEqual([narrow.paint.complete, narrow.paint.naturalWidth, narrow.paint.loadsBefore], [true, 761, 0], "complete at the paint, its natural size known, before any load event: " + JSON.stringify(narrow.paint));
    // the paint decided it from its natural size (761 by 76, above the floor): the box was not in the document, so figureBox had
    // no laid-out rect to read, and a control stands that the laid-out box (under the floor, below) would not get
    assert.equal(narrow.paint.control, true, "the paint's decision put a control after the held picture: " + JSON.stringify(narrow.paint));
    // the load event fired all the same, found the paint's control standing, and decided again over the laid-out box
    assert.equal(narrow.loads.length, 1, "one load event after the paint");
    assert.equal(narrow.loads[0].controlBefore, true, "the paint's control stood when the load arrived");
    assert.ok(narrow.loads[0].box[1] < FLOOR, "laid out under the floor at the load: " + JSON.stringify(narrow.loads[0].box));
    assert.equal(narrowFig.control, false, "the load's decision took the control away: " + fmt(narrowFig));
    // closed and re-opened at 900: the paint's control stands, and the load's decision leaves it
    await reopen(page, 900, 600);
    await settle(page, true);
    const again = await probe(page);
    const againFig = await figure(page);
    t.diagnostic("re-opened at 900: " + JSON.stringify(again) + "; " + fmt(againFig) + "; wide asked " + wideAsked);
    assert.equal(wideAsked, 1, "still no request: the browser holds it");
    assert.ok(again.paint, "the paint was recorded");
    assert.deepEqual([again.paint.complete, again.paint.control, again.paint.loadsBefore], [true, true, 0], "complete at the paint and decided then, a control after it: " + JSON.stringify(again.paint));
    assert.equal(again.loads.length, 1, "one load event after the paint");
    assert.equal(again.loads[0].controlBefore, true, "the paint's control stood when the load arrived");
    assert.ok(again.loads[0].box[0] >= FLOOR && again.loads[0].box[1] >= FLOOR, "laid out above the floor at the load: " + JSON.stringify(again.loads[0].box));
    assert.equal(againFig.control, true, "and the load's decision left it standing: " + fmt(againFig));
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

// ── the text-size road (the file review, correctness-1 with tests-1, regression-1, ui-1 and extra6-1: one defect) ──────────
// A text-size step (A- and A+ in the zoom flyout, Ctrl/Cmd + wheel over the body) reflows every column-capped figure at a
// CONSTANT body width: the prose column is 80ch of a font that carries --fv-scale, so the figure's laid-out box shrinks and
// grows with the step while the body's clientWidth never moves and the width watch reports nothing. The decision now hangs on
// the figure's own box (watchFigureBoxes: a ResizeObserver over the figures of the Rendered box), so a step that narrows the
// figure under the floor takes the control away and a step that widens it past brings it back, on the buttons and on the
// wheel alike, with no call from either road.
const BAND = ROOT + "/docs/figs/band.svg";
// the band: 1300 by 110, wider than the column at every size, so the column caps it; in the chat modal at 1200 px it is laid out
// 762 by 64.5 at 100% and 534 by 45.2 at 70% (measured before the fix, where the control stood on the 45 px figure)
const BAND_TEXT = "# Report\n\n![band](figs/band.svg)\n\nA sentence under the band.\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const BAND_DOCS: Record<string, string> = { [REPORT]: BAND_TEXT, [BAND]: svg(1300, 110, "#684") };
const pct = (page: any): Promise<string | undefined> => page.evaluate(() => (document.querySelector(".fileview") as HTMLElement).dataset.fvText);
/** The zoom flyout opened when it is shut (T367: A- and A+ ride it), so a press lands on a shown button. */
const openZoom = async (page: any): Promise<void> => { if (await page.evaluate(() => { const m = document.querySelector(".fileview .fileview-zoom-menu") as HTMLElement | null; return !m || m.hidden; })) await page.click(".fileview .fileview-zoom-btn"); };
/** `n` presses of A- (`dir` -1) or A+ (`dir` 1) in the flyout. */
async function stepText(page: any, dir: 1 | -1, n: number): Promise<void> {
  await openZoom(page);
  for (let i = 0; i < n; i++) { await page.click(dir < 0 ? 'button[aria-label="Smaller text"]' : 'button[aria-label="Larger text"]'); await frames(page, 2); }
}
/** `n` Ctrl + wheel steps over the body's middle, one WHEEL_STEP_PX (40 px of deltaY) each: down (`dir` -1) is smaller, up is larger. */
async function wheelText(page: any, dir: 1 | -1, n: number): Promise<void> {
  const at = await page.evaluate(() => { const r = (document.querySelector(".fileview-body") as HTMLElement).getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
  await page.mouse.move(at.x, at.y);
  await page.keyboard.down("Control");
  try { for (let i = 0; i < n; i++) { await page.mouse.wheel(0, dir < 0 ? 40 : -40); await frames(page, 2); } } finally { await page.keyboard.up("Control"); }
}

test("in a browser: a text-size step reflows the column-capped figure at a constant body width and the control follows it: the 1300 by 110 band at a 1200 px chat modal wears its control at 100%, loses it after three A- presses (70%, under the floor), gets it back after three A+ presses; Ctrl + wheel steps do the same", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "chat", 1200, 700, {
      docs: BAND_DOCS,
      serve: (u) => { const p = u.pathname === "/file" ? u.searchParams.get("path") || "" : ""; return BAND_DOCS[p] !== undefined && /\.svg$/.test(p) ? { status: 200, type: "image/svg+xml", body: BAND_DOCS[p] } : null; },
    });
    await page.waitForFunction(() => { const i = document.querySelector(".fileview-md img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0; }, null, { timeout: 10000 });
    await settle(page, true);
    const at100 = await figure(page);
    t.diagnostic("100%: " + fmt(at100));
    assert.equal(await pct(page), "100", "the default size");
    assert.ok(at100.w >= FLOOR && at100.h >= FLOOR, "above the floor at 100%: " + fmt(at100));
    assert.equal(at100.control, true, "the control stands at 100%: " + fmt(at100));
    // A- three times: 90, 80, 70. The body's width does not move; the column does, and the band with it
    await stepText(page, -1, 3);
    await settle(page, false);
    const at70 = await figure(page);
    t.diagnostic("70% by the buttons: " + fmt(at70));
    assert.equal(await pct(page), "70", "three steps down");
    assert.equal(at70.bodyW, at100.bodyW, "the body's width did not move: the step reflows the column alone");
    assert.ok(at70.h < FLOOR, "the band fell under the floor on its short side: " + fmt(at70));
    // FAILS BEFORE: the re-decision ran from the width watch alone, which a text-size step never fires; the control stayed on the 45 px band
    assert.equal(at70.control, false, "the control left at the step: " + fmt(at70));
    // A+ three times: back to 100, and the control returns
    await stepText(page, 1, 3);
    await settle(page, true);
    const back = await figure(page);
    t.diagnostic("100% again: " + fmt(back));
    assert.equal(await pct(page), "100");
    assert.ok(back.h >= FLOOR, "above the floor again: " + fmt(back));
    assert.equal(back.control, true, "the control is back: " + fmt(back));
    // the wheel road: Ctrl + wheel over the body steps the same table (foldWheel, WHEEL_STEP_PX)
    await wheelText(page, -1, 3);
    await settle(page, false);
    const wheel70 = await figure(page);
    t.diagnostic("70% by the wheel: " + fmt(wheel70));
    assert.equal(await pct(page), "70", "three wheel steps down");
    assert.ok(wheel70.h < FLOOR, "under the floor: " + fmt(wheel70));
    assert.equal(wheel70.control, false, "the control left at the wheel's step: " + fmt(wheel70));
    await wheelText(page, 1, 3);
    await settle(page, true);
    const wheel100 = await figure(page);
    t.diagnostic("100% by the wheel: " + fmt(wheel100));
    assert.equal(await pct(page), "100");
    assert.equal(wheel100.control, true, "and back at the wheel's steps up: " + fmt(wheel100));
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

// ── the keyboard when the control goes (the file review, ui-4) ────────────────────────────────────────────────────────────
test("in a browser: a control holding the keyboard when the width's change takes it away hands the keyboard to the viewer's body, so PageDown scrolls the report (before: the removal dropped the focus to the document's body, and the scroll keys did nothing until a click)", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReport(browser, 900, 600);
    await settle(page, true);
    // Tab from the body: the wide figure's control is the body's first focusable element
    await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).focus(); });
    await page.keyboard.press("Tab");
    assert.equal(await page.evaluate(() => !!document.activeElement && document.activeElement.hasAttribute("data-fv-figopen")), true, "Tab from the body lands on the control");
    // the viewport narrowed under the floor: the control leaves while it holds the keyboard
    await page.setViewportSize({ width: 381, height: 600 });
    await settle(page, false);
    const narrow = await figure(page);
    assert.equal(narrow.control, false, "the control left: " + fmt(narrow));
    const holder = await page.evaluate(() => { const a = document.activeElement; return a === null ? "none" : a === document.body ? "document.body" : a.classList.contains("fileview-body") ? "viewer body" : a.localName; });
    // FAILS BEFORE: "document.body", the browser's own fixup for a removed holder
    assert.equal(holder, "viewer body", "the keyboard went to the viewer's body");
    const top0: number = await page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
    await page.keyboard.press("PageDown");
    await frames(page, 3);
    const top1: number = await page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
    assert.ok(top1 > top0, "PageDown scrolls the report: " + top0 + " to " + top1);
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

// ── the hidden viewer's 0 by 0 report (found before the file review's round 3) ────────────────────────────────────────────
/** The wide figure's controls by count (`[data-fv-figopen]` after its anchor, 0 or 1), the viewer card's display and the
 *  figure's box, read together so a diagnostic names the state the count was read in. */
type Hidden = { controls: number; display: string; w: number; h: number };
const hiddenState = (page: any): Promise<Hidden> => page.evaluate(() => {
  const img = document.querySelector(".fileview-md img") as HTMLImageElement;
  const r = img.getBoundingClientRect();
  let a: Element = img;
  while (a.parentElement && (a.parentElement.classList.contains("fc-imgwrap") || a.parentElement.localName === "picture")) a = a.parentElement;
  const n = a.nextElementSibling;
  const card = document.getElementById("romp-fileview") as HTMLElement;
  return { controls: n && n.hasAttribute("data-fv-figopen") ? 1 : 0, display: getComputedStyle(card).display, w: r.width, h: r.height };
});
const fmtHidden = (h: Hidden): string => "card " + h.display + ", figure " + Math.round(h.w) + "x" + Math.round(h.h) + ", controls " + h.controls;
/** The viewer's card hidden (`display:none`) or shown again, then four frames, enough for the observer's report of the change
 *  (a ResizeObserver delivers in the frame after the layout that changed the box) and the decision it runs. */
async function setHidden(page: any, hidden: boolean): Promise<void> {
  await page.evaluate((h: boolean) => { (document.getElementById("romp-fileview") as HTMLElement).style.display = h ? "none" : ""; }, hidden);
  await frames(page, 4);
}

test("in a browser: the viewer hidden at 381 px, where the figure stands under the floor with no control, gets no control while hidden (the observer's 0 by 0 report runs no decision); shown again the figure keeps none; hidden and widened to 900 it still gets none while hidden, and the show's report of the real box brings the control; at 900 with the control standing, a hide removes nothing", async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReport(browser, 381, 600);
    await settle(page, false);
    const before = await hiddenState(page);
    t.diagnostic("shown at 381: " + fmtHidden(before));
    assert.ok(before.h < FLOOR, "under the floor at 381: " + fmtHidden(before));
    assert.equal(before.controls, 0, "no control stands at 381: " + fmtHidden(before));
    await setHidden(page, true);
    const hidden = await hiddenState(page);
    t.diagnostic("hidden at 381: " + fmtHidden(hidden));
    assert.deepEqual([hidden.display, hidden.w, hidden.h], ["none", 0, 0], "the card is display:none and the figure's box is 0 by 0: " + fmtHidden(hidden));
    // FAILS BEFORE: 1. The observer reported 0 by 0, figureBox fell back to the picture's natural size (761 by 76, above the
    // floor) and the decision added a control to a figure nobody could see, which the show's report then removed
    assert.equal(hidden.controls, 0, "no control added while hidden: " + fmtHidden(hidden));
    await setHidden(page, false);
    await settle(page, false);
    const shown = await hiddenState(page);
    t.diagnostic("shown again at 381: " + fmtHidden(shown));
    assert.ok(shown.h > 0 && shown.h < FLOOR, "laid out under the floor again: " + fmtHidden(shown));
    assert.equal(shown.controls, 0, "still none: " + fmtHidden(shown));
    // hidden, then widened while hidden: the report while hidden is 0 by 0 whatever the viewport, so still no control; the show
    // reports the real box at 900, above the floor, and the control follows it
    await setHidden(page, true);
    await page.setViewportSize({ width: 900, height: 600 });
    await frames(page, 4);
    const hiddenWide = await hiddenState(page);
    t.diagnostic("hidden, viewport 900: " + fmtHidden(hiddenWide));
    assert.deepEqual([hiddenWide.display, hiddenWide.controls], ["none", 0], "hidden at 900: no control while the box is 0 by 0: " + fmtHidden(hiddenWide));
    await setHidden(page, false);
    await settle(page, true);
    const shownWide = await hiddenState(page);
    t.diagnostic("shown at 900: " + fmtHidden(shownWide));
    assert.ok(shownWide.w >= FLOOR && shownWide.h >= FLOOR, "above the floor at the show: " + fmtHidden(shownWide));
    assert.equal(shownWide.controls, 1, "the show's real box brought the control: " + fmtHidden(shownWide));
    // the other direction: a standing control is not removed by a hide (the 0 by 0 report is skipped, not read as under the floor)
    await setHidden(page, true);
    const hiddenWith = await hiddenState(page);
    t.diagnostic("hidden at 900 with the control: " + fmtHidden(hiddenWith));
    assert.deepEqual([hiddenWith.display, hiddenWith.controls], ["none", 1], "the control stands through the hide: " + fmtHidden(hiddenWith));
    await setHidden(page, false);
    await settle(page, true);
    assert.equal((await hiddenState(page)).controls, 1, "and after the show");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});
