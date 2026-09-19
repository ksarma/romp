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
// from a real click on that control. Skipped LOUDLY where playwright has no browser (CI installs none). Synthetic values
// only: the notes-api world, a placeholder session id, example.invalid addresses, /repo/notes-api paths.
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
