// The one gate's tap cells, one set for every engine (the file review's round 17, tests-1 with regression-1, and the coordinator's
// decisions 1 to 3 on it), for the link-navigation follow-on of plans/markdown-viewer.md: file-figure-open-browser.test.ts runs
// them in Chromium, and file-figure-open-engines-browser.test.ts in WebKit and Firefox, a leg of its own that stays off the shared
// roster of browser legs, since the job that runs the roster installs Chromium alone. The gate (file-view.ts webGestureShown and
// the recorder above it) records a press's verdict at the window's pointerdown and fills a one-click slot at the pointerup, and a
// click by a pointer reads the record under its own pointerId or, with none, the press the slot handed it. The engines differ in
// what a tap's click carries, read off the page as each cell's precondition: Chromium gives the click the touch's own pointerId,
// Firefox its press's (0, a mouse's and a touch's alike), and WebKit under Playwright's touch emulation on Linux (a stand-in for
// WebKitGTK, and presumably WPE, on a touchscreen; no cell claims iOS Safari, whose click WebKit's iOS source gives the touch's own
// pointerId, read and not run on a device) pointerId 1 of type mouse while its press carried the touch's, so there the click finds
// its press in the slot. The cells, on the chat modal and the Files pane at 900 by 700, on a phone's pages (hasTouch and isMobile
// at a device scale of 1 with the kernel's viewport meta, which WebKit's mobile layout needs: without it a tap on the control lands
// off target) and on a hybrid page (hasTouch with a mouse), Firefox on the hybrid page alone since its engine takes no isMobile,
// each a count of [popups, document requests], the pictures from the web routed at the context and every value synthetic:
// - a tap on a loaded remote picture with its control in view and uncovered opens once, and so does a tap on the control, and a
//   tap on a remote picture under the floor that wears the mark and no control;
// - the control out of view: the first tap opens nothing and leaves the control in view, and the next tap opens once;
// - a double tap 90 ms apart on that picture: in Chromium its second click carries detail 2 and opens nothing, the second click of
//   a refused run; in Firefox and WebKit each tap's click carries detail 1, so the second tap is read at its own start, after the
//   first tap's reveal, and opens once (the coordinator's decision 1);
// - the covered sign: with the text-size flyout, or the Outline popover, over the control, a tap on the picture opens nothing and
//   closes what covered it, and the next tap opens once;
// - the stale records, on the hybrid page: a right press of the mouse on the picture with the control shown, or a mouse drag of the
//   picture, then the flyout opened over the control by a script's click on its button, with no press of the mouse, then a tap on
//   the picture: it opens nothing, since its own primary press ended the mouse's record, and the next tap opens once;
// - the clicks by no pointer: Enter on the control in view opens once, and so does Enter after a refused tap; a press with no click
//   after it begun with the control out of view, the control then scrolled into view with no pointer or key event, then Enter on it
//   opens once; the same press begun with the control shown, the flyout then shown over the control with no event, then a script's
//   click on the picture opens nothing. In Chromium that press is a real two-finger touch; in Firefox and WebKit no input
//   Playwright drives leaves a pointerup with no click on a picture, so there a script's pointerdown and pointerup stand in, which
//   the recorder hears as it hears a press, and the cell's name says so.
// Red at 0ab74924c in WebKit: the taps (every cell but the key cells opening nothing), the double tap there, and the stale records,
// whose reads there are a private witness kept out of the tree; the cells of Chromium and Firefox read the same at that head as at
// the fix, by design. The key cells are green at both heads by design, red under a gate that reads a key's click as
// a pointer's (the Enter cells) and under one that lets a key's or a script's click read the slot with the keydown's clear dropped
// (the press cells). file-view-outline.test.ts drives the same orders over the stand-in in CI, where these legs launch no browser.
import * as assert from "node:assert/strict";
import { openViewer, frames, PARA, REPORT } from "./real-viewer-leg";

export type TapEngine = "chromium" | "firefox" | "webkit";
export type TapDevice = "phone" | "hybrid";
export type TapSurface = "chat" | "pane";
/** One cell's reading: its name, the wanted value and the value read. */
export type TapCell = [string, unknown, unknown];

const WEB = "http://example.test";
const SIZES: Record<string, [number, number]> = { "/tall.svg": [300, 1400], "/w490.svg": [490, 900], "/tiny.svg": [20, 20] };
const sized = (w: number, h: number, fill: string): string => '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '"><rect width="' + w + '" height="' + h + '" fill="' + fill + '"/></svg>';
const paras = (from: number, n: number): string => Array.from({ length: n }, (_, i) => PARA(from + i)).join("\n\n");
/** A remote picture taller than the body, then a remote badge under the floor, which wears the mark and no control. */
const TALL_TEXT = "# Report\n\n" + PARA(1) + "\n\n![tall](" + WEB + "/tall.svg)\n\n" + paras(2, 8) + "\n\nA badge ![tiny](" + WEB + "/tiny.svg) in words.\n\n" + paras(10, 16) + "\n";
/** A remote picture 490 wide under three headings, so the Outline popover lists them and it and the text-size flyout can stand over its control. */
const COVER_TEXT = "# Report\n\n## Alpha\n\n" + PARA(1) + "\n\n![w490](" + WEB + "/w490.svg)\n\n## Beta\n\n" + paras(3, 12) + "\n\n## Gamma\n\n" + PARA(20) + "\n";

/** A browser whose pages are a phone's: hasTouch and isMobile at a device scale of 1 (hover none, a coarse pointer, touch events),
 *  the served page carrying the kernel pages' own viewport meta (`width=device-width, initial-scale=1`, which kernel.py writes on
 *  every dashboard page), so the layout viewport is the 900 px window at scale 1 and a screenshot pixel is a CSS pixel. The meta goes
 *  in after the page's `<meta charset=utf-8>`, and a page without that tag throws rather than open at the mobile default of a 980 px
 *  viewport scaled down. */
export function phonePages(browser: any): any {
  const META = '<meta name="viewport" content="width=device-width, initial-scale=1">';
  return {
    newPage: async (o: any) => {
      const pg = await browser.newPage({ ...o, hasTouch: true, isMobile: true, deviceScaleFactor: 1 });
      const route = pg.route.bind(pg);
      pg.route = (match: any, handler: any) => route(match, (r: any, req: any) => handler({
        request: () => r.request(),
        fulfill: (f: any) => {
          if (!(f && f.contentType === "text/html" && typeof f.body === "string")) return r.fulfill(f);
          assert.ok(f.body.includes("<meta charset=utf-8>"), "the served page carries <meta charset=utf-8>, after which the phone's viewport meta goes");
          return r.fulfill({ ...f, body: f.body.replace("<meta charset=utf-8>", "<meta charset=utf-8>" + META) });
        },
        continue: (...a: any[]) => r.continue(...a), fallback: (...a: any[]) => r.fallback(...a), abort: (...a: any[]) => r.abort(...a),
      }, req));
      return pg;
    },
  };
}
/** A browser whose pages have a touchscreen beside the mouse (hasTouch, no isMobile): the hybrid page. */
const hybridPages = (browser: any): any => ({ newPage: (o: any) => browser.newPage({ ...o, hasTouch: true }) });

/** In the viewer's document: the picture of an alt, its control, its sign (the control, else the picture wearing the mark), a window
 *  capture record of every pointerdown, pointerup and click (pointerId, pointerType, detail, trusted), `__tread` (whether the sign is in
 *  view in the body's padding box and the window or wholly outside the body, two points on the picture's visible part with what each
 *  hit-tests to, the control's centre and whether the picture wears the mark or a control) and `__tplace`, which puts the sign's top
 *  `dy` px below the body's padding top by the body's scrollTop, no pointer or key event. */
const INSTALL = (): void => {
  const w = window as any;
  w.__timg = (alt: string) => Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLElement;
  w.__tctl = (alt: string) => { const n = w.__timg(alt).nextElementSibling; return n && n.hasAttribute("data-fv-figopen") ? n as HTMLElement : null; };
  w.__tsign = (alt: string) => w.__tctl(alt) || (w.__timg(alt).hasAttribute("data-fv-figweb") ? w.__timg(alt) : null);
  w.__tev = [];
  for (const type of ["pointerdown", "pointerup", "click"]) window.addEventListener(type, (e: any) => { w.__tev.push({ type: e.type, pid: e.pointerId, ptype: e.pointerType, detail: e.detail, trusted: e.isTrusted }); }, true);
  w.__tread = (alt: string) => {
    const s = w.__tsign(alt) as HTMLElement, img = w.__timg(alt) as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement;
    const sr = s.getBoundingClientRect(), ir = img.getBoundingClientRect(), br = b.getBoundingClientRect();
    const pl = br.left + b.clientLeft, pt = br.top + b.clientTop, pr = pl + b.clientWidth, pb = pt + b.clientHeight;
    const inView = sr.right > Math.max(pl, 0) && sr.left < Math.min(pr, innerWidth) && sr.bottom > Math.max(pt, 0) && sr.top < Math.min(pb, innerHeight);
    const top = Math.max(ir.top, pt), bottom = Math.min(ir.bottom, pb, innerHeight);
    const p1 = { x: Math.round(ir.left + Math.min(40, ir.width / 2)), y: Math.round(Math.max(top + 1, bottom - 30)) };
    const p2 = { x: Math.round(ir.left + Math.min(150, ir.width / 2)), y: Math.round(Math.min(top + 140, (top + bottom) / 2)) };
    const hit = (p: { x: number; y: number }) => { const e = document.elementFromPoint(p.x, p.y); return !e ? "null" : e === img ? "the picture" : s.contains(e) ? "the sign" : e.localName + (typeof e.className === "string" && e.className ? "." + e.className.trim().split(/\s+/).join(".") : ""); };
    const c = w.__tctl(alt) as HTMLElement | null, cr = c ? c.getBoundingClientRect() : null;
    return { inView, outside: sr.bottom <= pt || sr.top >= pb, pt: p1, pt2: p2, hit: hit(p1), hit2: hit(p2), ctl: cr ? { x: (cr.left + cr.right) / 2, y: (cr.top + cr.bottom) / 2 } : null, mark: img.hasAttribute("data-fv-figweb"), control: !!c };
  };
  w.__tplace = (alt: string, dy: number) => { const s = w.__tsign(alt) as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement; b.scrollTop += s.getBoundingClientRect().top - (b.getBoundingClientRect().top + b.clientTop) - dy; };
};
type Read = { inView: boolean; outside: boolean; pt: { x: number; y: number }; pt2: { x: number; y: number }; hit: string; hit2: string; ctl: { x: number; y: number } | null; mark: boolean; control: boolean };
type PtrEv = { type: string; pid: number; ptype: string; detail: number; trusted: boolean };
type Scene = {
  page: any;
  /** The opens since the last read, as [popups, document requests]. */
  opens: () => Promise<[number, number]>;
  read: (alt: string) => Promise<Read>;
  place: (alt: string, dy: number) => Promise<Read>;
  /** A finger's tap at a point, and the pointer events and clicks it sent at the window. */
  tap: (x: number, y: number) => Promise<PtrEv[]>;
  events: () => Promise<PtrEv[]>;
  /** A press with no click after it on the picture `alt` at two points: Chromium's real two-finger touch, else a script's pointerdown and pointerup. */
  pressNoClick: (alt: string, a: { x: number; y: number }, b: { x: number; y: number }) => Promise<string>;
  flyout: () => Promise<{ open: boolean; overCentre: boolean }>;
};
/** `text` open on the surface in a page of the device's, the remote pictures routed and loaded through the gate, the helpers
 *  installed, and `body` run with the scene; the page errors asserted empty after it. */
async function tapScene(browser: any, engine: TapEngine, device: TapDevice, surface: TapSurface, text: string, body: (s: Scene) => Promise<void>): Promise<void> {
  const docReqs: string[] = [], popups: any[] = [];
  const before = async (pg: any): Promise<void> => {
    await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
      const req = route.request();
      if (req.resourceType() === "document") { docReqs.push(req.url()); return route.fulfill({ status: 200, contentType: "text/html", body: "<p>third party</p>" }); }
      const sz = SIZES[new URL(req.url()).pathname] || [300, 200];
      return route.fulfill({ status: 200, contentType: "image/svg+xml", body: sized(sz[0], sz[1], "#6a3d9a") });
    });
  };
  const host = device === "phone" ? phonePages(browser) : hybridPages(browser);
  const { page, errors } = await openViewer(host, surface, 900, 700, { docs: { [REPORT]: text }, before });
  try {
    for (let i = 0; i < 20 && await page.evaluate(() => !!document.querySelector('.fileview-md [data-act="fv-load"]')); i++) { await page.evaluate(() => { (document.querySelector('.fileview-md [data-act="fv-load"]') as HTMLElement).click(); }); await frames(page, 3); }
    await page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 15000 });
    await frames(page, 4);
    await page.evaluate(INSTALL);
    page.context().on("page", (p: any) => { popups.push(p); });
    const cdp = engine === "chromium" ? await page.context().newCDPSession(page) : null;
    let p0 = 0, d0 = 0;
    const read = (alt: string): Promise<Read> => page.evaluate((a: string) => (window as any).__tread(a), alt);
    const events = (): Promise<PtrEv[]> => page.evaluate(() => (window as any).__tev.splice(0));
    const scene: Scene = {
      page, read, events,
      opens: async () => {
        for (let i = 0; i < 12; i++) await frames(page, 2);
        await new Promise((r) => setTimeout(r, 350));   // a bounded settle for an open that must not come (a popup is a new page, no event of this one)
        const np = popups.slice(p0), nd = docReqs.slice(d0);
        p0 = popups.length; d0 = docReqs.length;
        for (const p of np) await p.close().catch(() => null);
        await page.bringToFront().catch(() => null);
        return [np.length, nd.length];
      },
      place: async (alt, dy) => { await page.evaluate(([a, d]: [string, number]) => (window as any).__tplace(a, d), [alt, dy]); await frames(page, 3); return read(alt); },
      tap: async (x, y) => { await events(); await page.touchscreen.tap(x, y); await frames(page, 2); return events(); },
      pressNoClick: async (alt, a, b) => {
        if (cdp) {
          await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: a.x, y: a.y, id: 1 }] });
          await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: a.x, y: a.y, id: 1 }, { x: b.x, y: b.y, id: 2 }] });
          await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
          await frames(page, 3);
          return "a two-finger touch";
        }
        await page.evaluate(([al, x, y]: [string, number, number]) => {
          const img = (window as any).__timg(al) as HTMLElement;
          const o = { bubbles: true, cancelable: true, composed: true, pointerId: 9, pointerType: "touch", isPrimary: true, clientX: x, clientY: y, button: 0 };
          img.dispatchEvent(new PointerEvent("pointerdown", o));
          img.dispatchEvent(new PointerEvent("pointerup", o));
        }, [alt, a.x, a.y]);
        await frames(page, 3);
        return "a script's pointerdown and pointerup, standing in";
      },
      flyout: () => page.evaluate(() => { const w = window as any; const c = w.__tctl("w490").getBoundingClientRect(); const e = document.elementFromPoint((c.left + c.right) / 2, (c.top + c.bottom) / 2); const m = document.querySelector(".fileview-zoom-menu") as HTMLElement; return { open: !m.hidden, overCentre: !!e && (!!e.closest(".fileview-zoom-menu") || !!e.closest(".fileview-size-reset")) }; }),
    };
    await body(scene);
  } finally {
    await page.close();
  }
  assert.deepEqual(errors, [], engine + ", " + device + ", " + surface + ": no page errors");
}

/** Every cell for an engine on a device and a surface, run in `browser`, each reading returned beside its wanted value; `note`
 *  receives each scene's record. The preconditions are asserted as they are read. */
export async function tapCells(browser: any, engine: TapEngine, device: TapDevice, surface: TapSurface, note: (m: string) => void): Promise<TapCell[]> {
  const cells: TapCell[] = [];
  const cell = (what: string, want: unknown, got: unknown): void => { cells.push([what, want, got]); };
  const at = engine + ", " + device + ", " + surface + ": ";
  const own = engine !== "webkit";   // Chromium's and Firefox's tap click carries its press's pointerId; WebKit's carries the mouse's
  /** The tap's shape, asserted as the cell's precondition: one pointerdown and one click, trusted, the click's pointerId its press's in
   *  Chromium and Firefox and another in WebKit (1, of type mouse, where the press carried the touch's). */
  const shape = (evs: PtrEv[], what: string): PtrEv => {
    const downs = evs.filter((e) => e.type === "pointerdown"), clicks = evs.filter((e) => e.type === "click");
    assert.ok(downs.length === 1 && clicks.length === 1 && clicks[0].trusted, at + what + ": the tap sends one pointerdown and one trusted click (a precondition): " + JSON.stringify(evs));
    if (own) assert.equal(clicks[0].pid, downs[0].pid, at + what + ": the tap's click carries its press's pointerId in " + engine + " (a precondition): " + JSON.stringify(evs));
    else assert.ok(clicks[0].pid !== downs[0].pid && clicks[0].ptype === "mouse" && downs[0].ptype === "touch", at + what + ": the tap's click carries a pointerId other than its press's in Playwright's WebKit on Linux under touch emulation, of type mouse where the press's is touch (a precondition): " + JSON.stringify(evs));
    return clicks[0];
  };
  await tapScene(browser, engine, device, surface, TALL_TEXT, async (s) => {
    const rec: Record<string, unknown> = {};
    const r = await s.place("tall", 120);
    rec.inView = r;
    assert.ok(r.inView && r.hit === "the picture" && r.ctl, at + "the control in view and the tap's point on the picture (a precondition): " + JSON.stringify(r));
    shape(await s.tap(r.pt.x, r.pt.y), "a tap on the picture");
    cell("a tap on the picture, its control in view: opens", [1, 1], await s.opens());
    const c = (await s.read("tall")).ctl!;
    shape(await s.tap(c.x, c.y), "a tap on the control");
    cell("a tap on the control: opens", [1, 1], await s.opens());
    const m = await s.place("tiny", 120);
    rec.mark = m;
    assert.ok(m.mark && !m.control && m.inView, at + "the badge under the floor wears the mark and no control, in view (a precondition): " + JSON.stringify(m));
    const mp = await s.page.evaluate(() => { const b = (window as any).__timg("tiny").getBoundingClientRect(); return { x: (b.left + b.right) / 2, y: (b.top + b.bottom) / 2 }; });
    shape(await s.tap(mp.x, mp.y), "a tap on the mark");
    cell("a tap on the picture that wears the mark: opens", [1, 1], await s.opens());
    const out = await s.place("tall", -60);
    rec.out = out;
    assert.ok(out.outside && out.hit === "the picture", at + "the control out of view above the body and the tap's point on the picture (a precondition): " + JSON.stringify(out));
    shape(await s.tap(out.pt.x, out.pt.y), "the first tap, the control out of view");
    const o1 = await s.opens();
    const after = await s.read("tall");
    cell("the control out of view: the first tap's opens, and the control in view after it", [[0, 0], true], [o1, after.inView]);
    assert.equal(after.hit2, "the picture", at + "the next tap's point, read after the reveal, on the picture (a precondition): " + JSON.stringify(after));
    const next = shape(await s.tap(after.pt2.x, after.pt2.y), "the next tap");
    assert.equal(next.detail, 1, at + "the next tap's click carries detail 1, a new run (a precondition)");
    cell("the control out of view: the next tap's opens", [1, 1], await s.opens());
    const out2 = await s.place("tall", -60);
    assert.ok(out2.outside && out2.hit === "the picture", at + "the control out of view again (a precondition): " + JSON.stringify(out2));
    await s.events();
    await s.page.touchscreen.tap(out2.pt.x, out2.pt.y);
    await new Promise((res) => setTimeout(res, 90));
    await s.page.touchscreen.tap(out2.pt.x, out2.pt.y);
    await frames(s.page, 2);
    const dbl = (await s.events()).filter((e) => e.type === "click").map((e) => e.detail);
    rec.doubleTap = dbl;
    assert.deepEqual(dbl, engine === "chromium" ? [1, 2] : [1, 1], at + "a double tap 90 ms apart: two clicks, of detail " + (engine === "chromium" ? "1 and 2 in Chromium" : "1 and 1 in " + engine) + " (a precondition)");
    cell("a double tap on the picture, its control out of view: opens (" + (engine === "chromium" ? "the second click, of detail 2, a later click of the refused run" : "the second tap's click of detail 1, read at its own start after the first tap's reveal") + ")", engine === "chromium" ? [0, 0] : [1, 1], await s.opens());
    await s.place("tall", 120);
    await s.page.evaluate(() => (window as any).__tctl("tall").focus());
    await s.page.keyboard.press("Enter");
    cell("Enter on the control in view: opens", [1, 1], await s.opens());
    const out3 = await s.place("tall", -60);
    assert.ok(out3.outside, at + "the control out of view for the press with no click (a precondition): " + JSON.stringify(out3));
    await s.events();
    const how = await s.pressNoClick("tall", out3.pt, out3.pt2);
    const pressEvs = await s.events();
    rec.k1 = { how, pressEvs };
    assert.ok(pressEvs.some((e) => e.type === "pointerup") && !pressEvs.some((e) => e.type === "click"), at + "the press sends a pointerup and no click (a precondition): " + JSON.stringify(pressEvs));
    const k1press = await s.opens();
    const back = await s.place("tall", 120);
    assert.ok(back.inView, at + "the control scrolled into view with no pointer or key event (a precondition)");
    await s.page.evaluate(() => (window as any).__tctl("tall").focus());
    await s.page.keyboard.press("Enter");
    cell("a press with no click begun with the control out of view (" + how + "), the control then in view, then Enter on it: [the press's opens, Enter's]", [[0, 0], [1, 1]], [k1press, await s.opens()]);
    note("record " + JSON.stringify({ engine, device, surface, scene: "tall", ...rec }));
  });
  await tapScene(browser, engine, device, surface, COVER_TEXT, async (s) => {
    const rec: Record<string, unknown> = {};
    const openFlyout = async (): Promise<void> => { await s.page.evaluate(() => { (document.querySelector(".fileview-zoom-btn") as HTMLElement).click(); }); await frames(s.page, 3); };
    const covered = async (what: string, open: () => Promise<void>, dy: number, pre: () => Promise<{ open: boolean; overCentre: boolean }>, closed: () => Promise<boolean>): Promise<void> => {
      await s.place("w490", dy);
      await open();
      const p = await pre(), r = await s.read("w490");
      rec[what] = { ...p, read: r };
      assert.ok(p.open && p.overCentre && r.inView && r.hit === "the picture", at + what + " open over the control's centre, the control in view, the tap's point on the picture (a precondition): " + JSON.stringify(rec[what]));
      shape(await s.tap(r.pt.x, r.pt.y), "a tap under " + what);
      cell(what + " over the control, then a tap on the picture: [the tap's opens, " + what + " closed after it]", [[0, 0], true], [await s.opens(), await closed()]);
      const r2 = await s.read("w490");
      shape(await s.tap(r2.pt2.x, r2.pt2.y), "the next tap after " + what);
      cell(what + " over the control, then the refused tap: the next tap's opens", [1, 1], await s.opens());
    };
    await covered("the text-size flyout", openFlyout, 3, s.flyout, () => s.page.evaluate(() => (document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden));
    await covered("the Outline popover", async () => { await s.page.evaluate(() => { (document.querySelector(".fileview-outline-btn") as HTMLElement).click(); }); await frames(s.page, 3); }, 42,
      () => s.page.evaluate(() => { const w = window as any; const c = w.__tctl("w490").getBoundingClientRect(); const e = document.elementFromPoint((c.left + c.right) / 2, (c.top + c.bottom) / 2); return { open: !!document.querySelector(".fileview-outline"), overCentre: !!e && !!e.closest(".fileview-outline") }; }),
      () => s.page.evaluate(() => !document.querySelector(".fileview-outline")));
    await s.place("w490", 3);
    await openFlyout();
    const fr = await s.read("w490");
    assert.ok((await s.flyout()).overCentre && fr.hit === "the picture", at + "the flyout over the control before the refused tap (a precondition)");
    shape(await s.tap(fr.pt.x, fr.pt.y), "the refused tap before Enter");
    const refused = await s.opens();
    await s.page.evaluate(() => (window as any).__tctl("w490").focus());
    await s.page.keyboard.press("Enter");
    cell("a tap refused under the flyout, then Enter on the control: [the tap's opens, Enter's]", [[0, 0], [1, 1]], [refused, await s.opens()]);
    const k2 = await s.place("w490", 3);
    assert.ok(k2.inView && !(await s.flyout()).open && k2.hit === "the picture", at + "the control shown before the press with no click (a precondition): " + JSON.stringify(k2));
    await s.events();
    const how = await s.pressNoClick("w490", k2.pt, k2.pt2);
    const pressEvs = await s.events();
    rec.k2 = { how, pressEvs };
    const k2press = await s.opens();
    await s.page.evaluate(() => { (document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden = false; });
    await frames(s.page, 3);
    assert.ok((await s.flyout()).overCentre, at + "the flyout shown over the control with no event (a precondition)");
    await s.page.evaluate(() => (window as any).__timg("w490").click());
    cell("a press with no click begun with the control shown (" + how + "), the flyout then over the control, then a script's click on the picture: [the press's opens, the click's]", [[0, 0], [0, 0]], [k2press, await s.opens()]);
    await s.page.evaluate(() => { (document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden = true; });
    if (device === "hybrid") {
      const stale = async (what: string, press: (r: Read) => Promise<void>): Promise<void> => {
        const r0 = await s.place("w490", 3);
        assert.ok(r0.inView && !(await s.flyout()).open && r0.hit === "the picture", at + "the control shown before " + what + " (a precondition): " + JSON.stringify(r0));
        await s.events();
        await press(r0);
        await frames(s.page, 3);
        const pressEvs = await s.events();
        const pressOpens = await s.opens();
        await s.place("w490", 3);
        await openFlyout();
        const p = await s.flyout(), r = await s.read("w490");
        rec[what] = { pressEvs, pressOpens, flyout: p, read: r };
        assert.ok(p.open && p.overCentre && r.inView && r.hit === "the picture", at + "after " + what + ", the flyout opened by a script's click over the control's centre, the tap's point on the picture (a precondition): " + JSON.stringify(rec[what]));
        shape(await s.tap(r.pt.x, r.pt.y), "the tap after " + what);
        cell(what + " with the control shown, then the flyout over the control, then a tap on the picture: [the press's opens, the tap's, the flyout closed after the tap]", [[0, 0], [0, 0], true], [pressOpens, await s.opens(), await s.page.evaluate(() => (document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden)]);
        const r2 = await s.read("w490");
        shape(await s.tap(r2.pt2.x, r2.pt2.y), "the next tap after " + what);
        cell(what + ", then the flyout, then the refused tap: the next tap's opens", [1, 1], await s.opens());
      };
      await stale("a right press of the mouse on the picture", async (r) => { await s.page.mouse.move(r.pt.x, r.pt.y); await s.page.mouse.down({ button: "right" }); await s.page.mouse.up({ button: "right" }); });
      await stale("a mouse drag of the picture", async (r) => { await s.page.mouse.move(r.pt.x, r.pt.y); await s.page.mouse.down(); await s.page.mouse.move(r.pt.x + 40, r.pt.y - 40, { steps: 5 }); await s.page.mouse.move(850, 650, { steps: 10 }); await s.page.mouse.up(); });
    }
    note("record " + JSON.stringify({ engine, device, surface, scene: "cover", ...rec }));
  });
  return cells;
}
