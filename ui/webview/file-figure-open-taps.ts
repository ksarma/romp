// The one gate's tap cells, one set for every engine (the file review's round 17, tests-1 with regression-1, and the coordinator's
// decisions 1 to 3 on it; its round 18, extra5-1, extra5-2 and correctness-1, with the coordinator's decisions on them), for the
// link-navigation follow-on of plans/markdown-viewer.md: file-figure-open-browser.test.ts runs them in Chromium, and
// file-figure-open-engines-browser.test.ts in WebKit and Firefox, a leg of its own that stays off the shared roster of browser legs,
// since the job that runs the roster installs Chromium alone. The gate (file-view.ts webGestureShown and the recorder above it)
// records a press's verdict at the window's pointerdown and fills a one-click slot at the pointerup, and a click by a pointer reads
// the record under its own pointerId or, with none, the press the slot handed it; a record ends at its own pointerup, which hands it
// to the slot, and every record ends at a dragstart and at a mousedown with no pointerdown of a mouse or a pen before it. The engines
// differ in what a tap's click carries, read off the page as each cell's precondition: Chromium gives the click the touch's own
// pointerId, Firefox its press's (0, a mouse's and a touch's alike), and WebKit under Playwright's touch emulation on Linux (a
// stand-in for WebKitGTK, and presumably WPE, on a touchscreen; no cell claims iOS Safari, whose click WebKit's iOS source gives the
// touch's own pointerId, read and not run on a device) pointerId 1 of type mouse while its press carried the touch's; in each the
// click finds its press in the slot. The cells, on the chat modal and the Files pane at 900 by 700, on a phone's pages (hasTouch and
// isMobile at a device scale of 1 with the kernel's viewport meta, which WebKit's mobile layout needs: without it a tap on the
// control lands off target) and on a hybrid page (hasTouch with a mouse), Firefox on the hybrid page alone since its engine takes no
// isMobile, each a count of [popups, document requests], the pictures from the web routed at the context and every value synthetic:
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
//   the picture: it opens nothing, the mouse's record having ended (the right press's at its own pointerup, the drag's at its
//   dragstart, and either at the tap's own primary press), so the tap's click reads its own press, and the next tap opens once;
// - the mouse's clicks after its drag of a picture, on the hybrid page and on a plain page (a mouse and no touchscreen): with the
//   control shown, a drag, then the flyout or the Outline popover opened over the control by a script's click, then a click of the
//   mouse on the picture opens nothing, and the next click opens once; and the cost cells, a drag, then a click of the mouse on the
//   same picture with its control shown and uncovered, or on another picture whose control is shown and uncovered: in WebKit the
//   first click opens nothing and the next opens once, and in Chromium and Firefox the first click opens once. Chromium and Firefox
//   end the drag's press with a pointercancel and send the next press's pointerdown; WebKit sends neither, and the next press
//   arrives as a mousedown with no pointerdown before it, each cell asserting its engine's shape as its precondition. The gate ends
//   every record at the drag's dragstart and at that mousedown, so WebKit's first click after the drag finds no press;
// - a drag in another pane, on the hybrid page and on a plain page: the dashboard's panes are same-origin frames, and a same-origin
//   frame put into the page, with a link dragged inside it, stands in for one, the viewer's window hearing nothing of the drag. A
//   right click on the picture with the control shown (F1, F2), or a press on the control released beside the picture (F3), then the
//   drag, then the text-size flyout over the control, opened by a script's click (F1, F3) or by Enter on its focused button (F2),
//   then a click of the mouse on the picture: it opens nothing, and the next click opens once; and the cost cells, no earlier press
//   (F5) or a right click (F6), then the drag, then a click with the control shown and uncovered: in WebKit the first click opens
//   nothing and the next opens once, and in Chromium and Firefox the first click opens once. WebKit keeps the button's pressed state
//   across the frames and sends the mouse's next press in the viewer as a mousedown with no pointerdown before it; Chromium and
//   Firefox end the frame's drag with a pointercancel and send that press's pointerdown;
// - Firefox's chord, on the hybrid page and on a plain page, in Firefox alone (Chromium and WebKit send no click after it): a left
//   press on the picture under the flyout or the Outline popover, each closed by that press, or begun with the control out of view
//   and the control then scrolled into view, then a middle or a right press chorded into it, whose mousedown comes with no
//   pointerdown of its own: the left press's click opens nothing, and the next click opens once;
// - a finger beside the mouse, in Chromium on the hybrid page (CDP touch): a finger held on the picture with the control shown, the
//   mouse's click beside it, the finger lifted, then the mouse's press on the picture with the control out of view or under the
//   flyout, a finger's swipe beside it while the mouse is held, and the release: its click opens nothing, with the finger's steps
//   before it or without them;
// - the clicks by no pointer: Enter on the control in view opens once, and so does Enter after a refused tap; a press with no click
//   after it begun with the control out of view, the control then scrolled into view with no pointer or key event, then Enter on it
//   opens once; the same press begun with the control shown, the flyout then shown over the control with no event, then a script's
//   click on the picture opens nothing. In Chromium that press is a real two-finger touch; in Firefox and WebKit no input
//   Playwright drives leaves a pointerup with no click on a picture, so there a script's pointerdown and pointerup stand in, which
//   the recorder hears as it hears a press, and the cell's name says so.
// Red at 0ab74924c in WebKit: the taps (every cell but the key cells opening nothing), the double tap there, the stale records and
// the clicks after a drag, whose reads there are a private witness kept out of the tree; the tap cells of Chromium and Firefox read
// the same at that head as at the fix, by design. The key cells are green at both heads by design, red under a gate that reads a
// key's click as a pointer's (the Enter cells) and under one that lets a key's or a script's click read the slot with the keydown's
// clear dropped (the press cells). The covered drag cells are red under A18-R in WebKit, the gate with the rule the file review's round
// 18 found reverted and no clear put in its place, whose click read the drag's record; WebKit's cost cells after a drag are red at
// ef686b029, whose gate took a verdict at the mousedown with no pointerdown before it, as they record the cost and guard no
// defect; the other pane's covered cells are red in WebKit at X, the gate with a dragstart clear and records ended at no pointerup,
// whose click read the record the right click or the released press left; Firefox's chord cells and Chromium's cells of a finger
// beside the mouse are red at ef686b029 and under A18-M, that gate restored; the reads of each of these reds are a private witness
// kept out of the tree. file-view-outline.test.ts drives the same orders over the stand-in in CI, where these legs launch no browser.
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
/** Two remote pictures above the floor, one after the other, each wearing its control in view at once. */
const TWO_TEXT = "# Report\n\n" + PARA(1) + "\n\n![first](" + WEB + "/first.svg)\n\n" + PARA(2) + "\n\n![second](" + WEB + "/second.svg)\n\n" + paras(3, 12) + "\n";
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
 *  capture record of every pointerdown, mousedown, pointerup, pointercancel, dragstart and click (pointerId, pointerType, detail,
 *  trusted), `__tread` (whether the sign is in
 *  view in the body's padding box and the window or wholly outside the body, two points on the picture's visible part with what each
 *  hit-tests to, the control's centre and whether the picture wears the mark or a control) and `__tplace`, which puts the sign's top
 *  `dy` px below the body's padding top by the body's scrollTop, no pointer or key event. */
const INSTALL = (): void => {
  const w = window as any;
  w.__timg = (alt: string) => Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLElement;
  w.__tctl = (alt: string) => { const n = w.__timg(alt).nextElementSibling; return n && n.hasAttribute("data-fv-figopen") ? n as HTMLElement : null; };
  w.__tsign = (alt: string) => w.__tctl(alt) || (w.__timg(alt).hasAttribute("data-fv-figweb") ? w.__timg(alt) : null);
  w.__tev = [];
  for (const type of ["pointerdown", "mousedown", "pointerup", "pointercancel", "dragstart", "click"]) window.addEventListener(type, (e: any) => { w.__tev.push({ type: e.type, pid: e.pointerId, ptype: e.pointerType, detail: e.detail, trusted: e.isTrusted }); }, true);
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
async function tapScene(browser: any, engine: TapEngine, device: TapDevice, surface: TapSurface, text: string, body: (s: Scene) => Promise<void>, mouseOnly = false): Promise<void> {
  const docReqs: string[] = [], popups: any[] = [];
  const before = async (pg: any): Promise<void> => {
    await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
      const req = route.request();
      if (req.resourceType() === "document") { docReqs.push(req.url()); return route.fulfill({ status: 200, contentType: "text/html", body: "<p>third party</p>" }); }
      const sz = SIZES[new URL(req.url()).pathname] || [300, 200];
      return route.fulfill({ status: 200, contentType: "image/svg+xml", body: sized(sz[0], sz[1], "#6a3d9a") });
    });
  };
  const host = mouseOnly ? browser : device === "phone" ? phonePages(browser) : hybridPages(browser);   // mouseOnly: a plain page, a mouse and no touchscreen
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
  assert.deepEqual(errors, [], engine + ", " + (mouseOnly ? "a plain page" : device) + ", " + surface + ": no page errors");
}

/** Every cell for an engine on a device and a surface, run in `browser`, each reading returned beside its wanted value; `note`
 *  receives each scene's record. The preconditions are asserted as they are read. */
export async function tapCells(browser: any, engine: TapEngine, device: TapDevice, surface: TapSurface, note: (m: string) => void): Promise<TapCell[]> {
  const cells: TapCell[] = [];
  const cell = (what: string, want: unknown, got: unknown): void => { cells.push([what, want, got]); };
  const at = (engine === "webkit" ? "WebKit (Playwright's, on Linux under touch emulation)" : engine) + ", " + (device === "phone" ? "a phone's pages" : "a hybrid page") + ", " + surface + ": ";
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
  if (device === "hybrid") for (const mouseOnly of [false, true]) {
    const on = at.replace("a hybrid page", mouseOnly ? "a plain page" : "a hybrid page");
    await dragThenClick(browser, engine, surface, mouseOnly, on, cell, note);
    await otherPane(browser, engine, surface, mouseOnly, on, cell, note);
    if (engine === "firefox") await chordCells(browser, engine, surface, mouseOnly, on, cell, note);
  }
  if (engine === "chromium" && device === "hybrid") await touchBesideMouse(browser, surface, at, cell, note);
  return cells;
}

type CellFn = (what: string, want: unknown, got: unknown) => void;
/** The events a gesture sent at the window, one word each: type(pointerId,pointerType,detail). */
const fmt = (evs: PtrEv[]): string => evs.map((e) => e.type + "(" + e.pid + "," + e.ptype + "," + e.detail + ")").join(" ");
/** A click of the mouse at `p`, and the events it sent; `after` names the press's shape the engine sends: "own", its pointerdown
 *  and its mousedown, or "lost", the mousedown alone, as WebKit sends the mouse's next press after a press whose pointerup never
 *  came, asserted as the cell's precondition. */
async function mouseClickAt(s: Scene, p: { x: number; y: number }, after: "own" | "lost", what: string): Promise<PtrEv[]> {
  await s.events();
  await s.page.mouse.click(p.x, p.y);
  await frames(s.page, 2);
  const evs = await s.events();
  const downs = evs.filter((e) => e.type === "pointerdown").length, mdowns = evs.filter((e) => e.type === "mousedown").length;
  assert.ok(evs.some((e) => e.type === "click") && mdowns === 1 && downs === (after === "lost" ? 0 : 1), what + ": the click's press sends " + (after === "lost" ? "a mousedown and no pointerdown" : "its pointerdown and its mousedown") + " (a precondition): " + fmt(evs));
  return evs;
}
const outlineOver = (s: Scene): Promise<{ open: boolean; overCentre: boolean }> => s.page.evaluate(() => { const w = window as any; const c = w.__tctl("w490").getBoundingClientRect(); const e = document.elementFromPoint((c.left + c.right) / 2, (c.top + c.bottom) / 2); return { open: !!document.querySelector(".fileview-outline"), overCentre: !!e && !!e.closest(".fileview-outline") }; });
const openFlyoutBy = async (s: Scene, how: "script" | "key"): Promise<void> => {
  if (how === "script") await s.page.evaluate(() => { (document.querySelector(".fileview-zoom-btn") as HTMLElement).click(); });
  else { await s.page.evaluate(() => { (document.querySelector(".fileview-zoom-btn") as HTMLElement).focus(); }); await s.page.keyboard.press("Enter"); }
  await frames(s.page, 3);
};
const openOutline = async (s: Scene): Promise<void> => { await s.page.evaluate(() => { (document.querySelector(".fileview-outline-btn") as HTMLElement).click(); }); await frames(s.page, 3); };
/** The flyout and the Outline popover closed, whichever stands. */
const closeCovers = async (s: Scene): Promise<void> => {
  await s.page.evaluate(() => { const m = document.querySelector(".fileview-zoom-menu") as HTMLElement | null; if (m && !m.hidden) (document.querySelector(".fileview-zoom-btn") as HTMLElement).click(); });
  await frames(s.page, 2);
  await s.page.evaluate(() => { if (document.querySelector(".fileview-outline")) (document.querySelector(".fileview-outline-btn") as HTMLElement).click(); });
  await frames(s.page, 2);
};

/** A mouse drag of a picture, then clicks of the mouse: on the hybrid page, and on a plain page (a mouse and no touchscreen). The
 *  drag ends in a dragstart and no click; in Chromium and Firefox it ends the press with a pointercancel and the next press sends its
 *  pointerdown, while WebKit sends neither, and sends the mouse's next press as a mousedown with no pointerdown before it, a
 *  precondition each cell asserts by engine. The gate (file-view.ts, the recorder above webGestureShown) ends every record at the
 *  drag's dragstart and at that mousedown, so in WebKit the mouse's first click after the drag finds no press and opens nothing,
 *  whatever covers or shows the control, and the click after it opens: the covered cells guard the closed direction, and the cells
 *  with the control shown record the cost, WebKit's first click refused where Chromium's and Firefox's open. */
async function dragThenClick(browser: any, engine: TapEngine, surface: TapSurface, mouseOnly: boolean, at: string, cell: CellFn, note: (m: string) => void): Promise<void> {
  const on = mouseOnly ? " (a plain page)" : " (the hybrid page)";
  const lost = engine === "webkit";   // WebKit sends the mouse's next press after its drag with no pointerdown
  const drag = async (s: Scene, p: { x: number; y: number }): Promise<PtrEv[]> => {
    await s.events();
    await s.page.mouse.move(p.x, p.y); await s.page.mouse.down(); await s.page.mouse.move(p.x + 40, p.y - 40, { steps: 5 }); await s.page.mouse.move(850, 650, { steps: 10 }); await s.page.mouse.up();
    await frames(s.page, 3);
    const evs = await s.events();
    assert.ok(evs.some((e) => e.type === "dragstart") && !evs.some((e) => e.type === "click"), at + "the drag starts a drag and clicks nothing (a precondition): " + fmt(evs));
    if (engine === "webkit") assert.ok(!evs.some((e) => e.type === "pointerup" || e.type === "pointercancel"), at + "WebKit's drag of the picture ends with no pointerup and no pointercancel (a precondition): " + fmt(evs));
    else assert.ok(evs.some((e) => e.type === "pointercancel"), at + engine + "'s drag of the picture ends its press with a pointercancel (a precondition): " + fmt(evs));
    return evs;
  };
  /** The first click after a drag with the control shown and uncovered: WebKit's opens nothing, the stated cost, and Chromium's and Firefox's open once. */
  const shownWant = lost ? [0, 0] : [1, 1];
  await tapScene(browser, engine, "hybrid", surface, COVER_TEXT, async (s) => {
    const rec: Record<string, unknown> = {};
    const covers: Array<[string, () => Promise<void>, number, () => Promise<{ open: boolean; overCentre: boolean }>]> = [
      ["the text-size flyout", () => openFlyoutBy(s, "script"), 3, s.flyout],
      ["the Outline popover", () => openOutline(s), 42, () => outlineOver(s)],
    ];
    for (const [what, open, dy, pre] of covers) {
      const r0 = await s.place("w490", dy);
      assert.ok(r0.inView && r0.hit === "the picture" && !(await pre()).open, at + "the control shown before the drag" + on + " (a precondition): " + JSON.stringify(r0));
      const dragEvs = await drag(s, r0.pt);
      const dragOpens = await s.opens();
      await s.place("w490", dy);
      await open();
      const p = await pre(), r = await s.read("w490");
      rec[what] = { dragEvs: fmt(dragEvs), flyout: p, read: r };
      assert.ok(p.open && p.overCentre && r.inView && r.hit === "the picture", at + "after the drag" + on + ", " + what + " opened by a script's click over the control's centre, the click's point on the picture (a precondition): " + JSON.stringify(rec[what]));
      await mouseClickAt(s, r.pt, lost ? "lost" : "own", at + "the click under " + what + " after the drag");
      cell("a mouse drag of the picture with the control shown" + on + ", then " + what + " over the control, then a click of the mouse on the picture: [the drag's opens, the click's]", [[0, 0], [0, 0]], [dragOpens, await s.opens()]);
      const r2 = await s.read("w490");
      rec[what + " after"] = { cover: await pre(), read: r2 };
      assert.ok(!(await pre()).overCentre && r2.inView && r2.hit2 === "the picture", at + "after the refused click" + on + ", nothing over the control, in view, the next click's point on the picture (a precondition): " + JSON.stringify(rec[what + " after"]));
      await mouseClickAt(s, r2.pt2, "own", at + "the next click after " + what);
      cell("a mouse drag" + on + ", then " + what + ", then the refused click: the next click's opens", [1, 1], await s.opens());
    }
    const r0 = await s.place("w490", 3);
    assert.ok(r0.inView && r0.hit === "the picture" && !(await s.flyout()).open, at + "the control shown before the drag with no cover after it" + on + " (a precondition): " + JSON.stringify(r0));
    const dragEvs = await drag(s, r0.pt);
    const dragOpens = await s.opens();
    const r1 = await s.place("w490", 3);
    assert.ok(r1.inView && r1.hit === "the picture" && !(await s.flyout()).open, at + "after the drag" + on + ", the control shown and uncovered (a precondition): " + JSON.stringify(r1));
    await mouseClickAt(s, r1.pt, lost ? "lost" : "own", at + "the first click after the drag, the control shown");
    const first = await s.opens();
    const r2 = await s.read("w490");
    assert.ok(r2.inView && r2.hit2 === "the picture", at + "the next click's point on the picture" + on + " (a precondition): " + JSON.stringify(r2));
    await mouseClickAt(s, r2.pt2, "own", at + "the click after it");
    cell("a mouse drag of the picture with the control shown" + on + ", then a click of the mouse on the same picture, the control shown and uncovered, a stated cost in WebKit: [the drag's opens, the click's, the next click's]", [[0, 0], shownWant, [1, 1]], [dragOpens, first, await s.opens()]);
    note("record " + JSON.stringify({ engine, surface, page: mouseOnly ? "plain" : "hybrid", scene: "drag-cover", ...rec, shown: fmt(dragEvs) }));
  }, mouseOnly);
  await tapScene(browser, engine, "hybrid", surface, TWO_TEXT, async (s) => {
    const a = await s.place("first", 60);
    const b = await s.read("second");
    assert.ok(a.inView && a.hit === "the picture" && b.inView && b.hit === "the picture", at + "both pictures' controls in view, each point on its picture" + on + " (a precondition): " + JSON.stringify([a, b]));
    const dragEvs = await drag(s, a.pt);
    const dragOpens = await s.opens();
    const b2 = await s.read("second");
    const clickEvs = await mouseClickAt(s, b2.pt, lost ? "lost" : "own", at + "the click on the second picture");
    const first = await s.opens();
    const b3 = await s.read("second");
    assert.ok(b3.inView && b3.hit2 === "the picture", at + "the next click's point on the second picture" + on + " (a precondition): " + JSON.stringify(b3));
    await mouseClickAt(s, b3.pt2, "own", at + "the click after it");
    cell("a mouse drag of one picture" + on + ", then a click of the mouse on another whose control is shown and uncovered, a stated cost in WebKit: [the drag's opens, the click's, the next click's]", [[0, 0], shownWant, [1, 1]], [dragOpens, first, await s.opens()]);
    note("record " + JSON.stringify({ engine, surface, page: mouseOnly ? "plain" : "hybrid", scene: "drag-other", dragEvs: fmt(dragEvs), clickEvs: fmt(clickEvs) }));
  }, mouseOnly);
}

/** A drag in another pane, then clicks of the mouse in the viewer (the file review's round 18, with the coordinator's decisions on
 *  open item 1). The dashboard's chat, Files and feed panes are same-origin frames, and a drag in one sends the viewer's window
 *  nothing, so a same-origin frame put into the page, with a link dragged inside it, stands in for another pane. WebKit keeps the
 *  button's pressed state across the frames and sends the mouse's next press in the viewer as a mousedown with no pointerdown before
 *  it; Chromium and Firefox end the frame's drag with a pointercancel and send that press's pointerdown; each cell asserts its
 *  engine's shape as its precondition. Before the drag, with the control shown: a right click on the picture (F1, F2, F6), a press
 *  on the control released off it, beside the picture (F3), or nothing (F5); after it, the text-size flyout over the control, opened by a
 *  script's click (F1, F3) or by Enter on its focused button (F2), or no cover (F5, F6); then a click of the mouse on the picture,
 *  and the click after it. The covered cells refuse the first click in every engine; the uncovered ones record the cost, WebKit's
 *  first click refused where Chromium's and Firefox's open. */
async function otherPane(browser: any, engine: TapEngine, surface: TapSurface, mouseOnly: boolean, at: string, cell: CellFn, note: (m: string) => void): Promise<void> {
  const on = mouseOnly ? " (a plain page)" : " (the hybrid page)";
  const lost = engine === "webkit";
  await tapScene(browser, engine, "hybrid", surface, COVER_TEXT, async (s) => {
    const rec: Record<string, unknown> = {};
    const frame = await s.page.evaluate(async () => {
      const f = document.createElement("iframe");
      f.id = "tpane";
      f.style.cssText = "position:fixed;left:" + (innerWidth - 170) + "px;top:" + (innerHeight - 150) + "px;width:160px;height:140px;z-index:2147483647;border:1px solid #888;background:#fff";
      f.srcdoc = "<!doctype html><html><body style='margin:0'><a id=l href='http://drag.invalid/pane' style='display:block;font:18px sans-serif;padding:10px'>a link to drag</a><p style='font:14px sans-serif;padding:6px'>another pane</p></body></html>";
      document.body.appendChild(f);
      await new Promise((r) => { const ok = () => f.contentDocument && f.contentDocument.getElementById("l"); if (ok()) r(null); else f.addEventListener("load", () => r(null), { once: true }); });
      const d = f.contentDocument!, w = f.contentWindow as any;
      d.addEventListener("dragover", (e) => e.preventDefault()); d.addEventListener("drop", (e) => e.preventDefault());
      w.__fev = [];
      for (const type of ["pointerdown", "mousedown", "pointerup", "pointercancel", "dragstart", "click"]) w.addEventListener(type, (e: any) => { w.__fev.push(e.type); }, true);
      const r = f.getBoundingClientRect(), lr = (d.getElementById("l") as HTMLElement).getBoundingClientRect();
      return { x: Math.round(r.left + lr.left + 40), y: Math.round(r.top + lr.top + lr.height / 2), fx: Math.round(r.left), fy: Math.round(r.top) };
    });
    const frameDrag = async (): Promise<{ viewer: PtrEv[]; frame: string[] }> => {
      await s.events();
      await s.page.evaluate(() => { ((document.getElementById("tpane") as HTMLIFrameElement).contentWindow as any).__fev = []; });
      await s.page.mouse.move(frame.x, frame.y); await s.page.mouse.down();
      await s.page.mouse.move(frame.x + 20, frame.y + 20, { steps: 5 }); await s.page.mouse.move(frame.fx + 130, frame.fy + 110, { steps: 8 }); await s.page.mouse.up();
      await frames(s.page, 3);
      const fe = await s.page.evaluate(() => ((document.getElementById("tpane") as HTMLIFrameElement).contentWindow as any).__fev.splice(0));
      return { viewer: await s.events(), frame: fe };
    };
    const rightClick = async (r0: Read): Promise<string> => { await s.events(); await s.page.mouse.click(r0.pt.x, r0.pt.y, { button: "right" }); await frames(s.page, 2); return fmt(await s.events()); };
    const pressOff = async (r0: Read): Promise<string> => {
      await s.events();
      const c = r0.ctl!, q = { x: Math.round(c.x + 150), y: Math.round(c.y + 120) };
      const there = await s.page.evaluate(([x, y]: [number, number]) => { const e = document.elementFromPoint(x, y); return !!e && !e.closest("img, [data-fv-figopen]"); }, [q.x, q.y]);
      assert.ok(there, at + "the release point beside the picture, off the picture and the control" + on + " (a precondition): " + JSON.stringify(q));
      await s.page.mouse.move(c.x, c.y); await s.page.mouse.down(); await s.page.mouse.move(q.x, q.y, { steps: 8 }); await s.page.mouse.up();
      await frames(s.page, 3);
      return fmt(await s.events());
    };
    const nothing = async (): Promise<string> => "none";
    const chains: Array<[string, string, (r0: Read) => Promise<string>, "script" | "key" | null]> = [
      ["F1", "a right click on the picture", rightClick, "script"],
      ["F2", "a right click on the picture", rightClick, "key"],
      ["F3", "a press on the control released beside the picture", pressOff, "script"],
      ["F5", "no earlier press", nothing, null],
      ["F6", "a right click on the picture", rightClick, null],
    ];
    for (const [id, before, step, cover] of chains) {
      await closeCovers(s);
      const r0 = await s.place("w490", 3);
      assert.ok(r0.inView && r0.hit === "the picture" && r0.ctl && !(await s.flyout()).open, at + id + ": the control shown before the steps" + on + " (a precondition): " + JSON.stringify(r0));
      const stepEvs = await step(r0);
      const stepOpens = await s.opens();
      const fd = await frameDrag();
      assert.ok(fd.viewer.length === 0 && fd.frame.includes("dragstart"), at + id + ": the drag in the other frame starts a drag there and sends the viewer's window nothing (a precondition): " + JSON.stringify({ viewer: fmt(fd.viewer), frame: fd.frame }));
      if (!lost) assert.ok(fd.frame.includes("pointercancel"), at + id + ": " + engine + " ends the other frame's drag with a pointercancel (a precondition): " + JSON.stringify(fd.frame));
      const dragOpens = await s.opens();
      await s.place("w490", 3);
      if (cover) await openFlyoutBy(s, cover);
      const p = await s.flyout(), r1 = await s.read("w490");
      rec[id] = { stepEvs, frame: fd.frame, flyout: p, read: r1 };
      assert.ok((cover ? p.open && p.overCentre : !p.open) && r1.inView && r1.hit === "the picture", at + id + ": " + (cover ? "the flyout over the control's centre" : "nothing over the control") + ", the click's point on the picture (a precondition): " + JSON.stringify(rec[id]));
      const c1 = await mouseClickAt(s, r1.pt, lost ? "lost" : "own", at + id + ": the first click after the drag in the other frame");
      const first = await s.opens();
      const r2 = await s.read("w490");
      assert.ok(!(await s.flyout()).overCentre && r2.inView && r2.hit2 === "the picture", at + id + ": nothing over the control before the next click, its point on the picture (a precondition): " + JSON.stringify(r2));
      await mouseClickAt(s, r2.pt2, "own", at + id + ": the next click");
      const next = await s.opens();
      (rec[id] as Record<string, unknown>).click = fmt(c1);
      cell(id + ": with the control shown, " + before + on + ", then a drag in another pane, then " + (cover ? "the text-size flyout over the control, opened by " + (cover === "script" ? "a script's click" : "Enter on its focused button") : "no cover, a stated cost in WebKit") + ", then a click of the mouse on the picture: [the step's opens, the drag's, the click's, the next click's]", [[0, 0], [0, 0], cover ? [0, 0] : lost ? [0, 0] : [1, 1], [1, 1]], [stepOpens, dragOpens, first, next]);
    }
    note("record " + JSON.stringify({ engine, surface, page: mouseOnly ? "plain" : "hybrid", scene: "other-pane", ...rec }));
  }, mouseOnly);
}

/** Firefox's chord (the file review's round 18, extra5-1): a left press on the picture, a middle or a right press chorded into it,
 *  then the chorded button's release and the left's. Firefox sends the chorded button's mousedown with no pointerdown of its own and
 *  then the left press's pointerup and click, a precondition each cell asserts (Chromium and WebKit send no click after such a chord,
 *  so the cells run in Firefox alone). Under the text-size flyout or the Outline popover over the control, each closed by the left
 *  press, and with the control out of view at the left press and scrolled into view by a script before the chord: the chord's click
 *  opens nothing, and the next click opens once. */
async function chordCells(browser: any, engine: TapEngine, surface: TapSurface, mouseOnly: boolean, at: string, cell: CellFn, note: (m: string) => void): Promise<void> {
  const on = mouseOnly ? " (a plain page)" : " (the hybrid page)";
  const chord = async (s: Scene, p: { x: number; y: number }, button: "middle" | "right", between: () => Promise<void>): Promise<PtrEv[]> => {
    await s.events();
    await s.page.mouse.move(p.x, p.y); await s.page.mouse.down({ button: "left" });
    await between();
    await s.page.mouse.down({ button }); await s.page.mouse.up({ button }); await s.page.mouse.up({ button: "left" });
    await frames(s.page, 3);
    const evs = await s.events();
    const n = (t: string) => evs.filter((e) => e.type === t).length;
    assert.ok(n("pointerdown") === 1 && n("mousedown") === 2 && n("click") === 1, at + "Firefox's chord sends one pointerdown, two mousedowns and the left press's click (a precondition): " + fmt(evs));
    return evs;
  };
  const rec: Record<string, unknown> = {};
  await tapScene(browser, engine, "hybrid", surface, COVER_TEXT, async (s) => {
    const covers: Array<[string, () => Promise<void>, number, () => Promise<{ open: boolean; overCentre: boolean }>]> = [
      ["the text-size flyout", () => openFlyoutBy(s, "script"), 3, s.flyout],
      ["the Outline popover", () => openOutline(s), 42, () => outlineOver(s)],
    ];
    for (const [what, open, dy, pre] of covers) for (const button of ["middle", "right"] as const) {
      await closeCovers(s);
      await s.place("w490", dy);
      await open();
      const p = await pre(), r = await s.read("w490");
      assert.ok(p.open && p.overCentre && r.inView && r.hit === "the picture", at + what + " open over the control's centre, the press's point on the picture" + on + " (a precondition): " + JSON.stringify({ p, r }));
      const evs = await chord(s, r.pt, button, async () => {});
      const first = await s.opens();
      const r2 = await s.read("w490");
      assert.ok(!(await pre()).overCentre && r2.inView && r2.hit2 === "the picture", at + "after the chord, nothing over the control, its next point on the picture" + on + " (a precondition): " + JSON.stringify(r2));
      await mouseClickAt(s, r2.pt2, "own", at + "the click after the chord");
      rec[what + " " + button] = fmt(evs);
      cell(what + " over the control" + on + ", then a left press on the picture chorded by a " + button + " press: [the chord's click's opens, the next click's]", [[0, 0], [1, 1]], [first, await s.opens()]);
    }
  }, mouseOnly);
  await tapScene(browser, engine, "hybrid", surface, TALL_TEXT, async (s) => {
    for (const button of ["middle", "right"] as const) {
      const out = await s.place("tall", -60);
      assert.ok(out.outside && out.hit === "the picture", at + "the control out of view above the body, the press's point on the picture" + on + " (a precondition): " + JSON.stringify(out));
      const evs = await chord(s, out.pt, button, async () => { await s.page.evaluate(() => (window as any).__tplace("tall", 120)); await frames(s.page, 3); });
      const first = await s.opens();
      const r2 = await s.read("tall");
      assert.ok(r2.inView && r2.hit2 === "the picture", at + "after the chord, the control in view, its next point on the picture" + on + " (a precondition): " + JSON.stringify(r2));
      await mouseClickAt(s, r2.pt2, "own", at + "the click after the chord");
      rec["out of view " + button] = fmt(evs);
      cell("the control out of view at a left press on the picture" + on + ", the control then scrolled into view, then a " + button + " press chorded into it: [the chord's click's opens, the next click's]", [[0, 0], [1, 1]], [first, await s.opens()]);
    }
  }, mouseOnly);
  note("record " + JSON.stringify({ engine, surface, page: mouseOnly ? "plain" : "hybrid", scene: "chord", ...rec }));
}

/** Chromium's order on the hybrid page (the file review's round 18, extra5-2), a finger in CDP touch beside the mouse: a finger held
 *  on the picture with the control shown, the mouse's click on the body beside it, then the finger lifted (its compatibility
 *  mousedown and its click come after its pointerup); then the mouse's press on the picture with the control out of view, or under
 *  the text-size flyout, which its press closes, a finger's swipe beside the picture while the mouse is held (a touch's pointerdown
 *  and pointercancel, the swipe scrolling the control into view), then the mouse's release: its click opens nothing; and each of the
 *  two scenes with no finger and mouse click before it. */
async function touchBesideMouse(browser: any, surface: TapSurface, at: string, cell: CellFn, note: (m: string) => void): Promise<void> {
  await tapScene(browser, "chromium", "hybrid", surface, COVER_TEXT, async (s) => {
    const cdp = await s.page.context().newCDPSession(s.page);
    const rec: Record<string, unknown> = {};
    const beside = (): Promise<{ x: number; y: number }> => s.page.evaluate(() => { const w = window as any; const ir = w.__timg("w490").getBoundingClientRect(); return { x: Math.round(Math.min(ir.right + 80, innerWidth - 30)), y: Math.round(Math.max(ir.top, 80) + 60) }; });
    const touchEv = (type: string, pts: Array<{ x: number; y: number }>) => cdp.send("Input.dispatchTouchEvent", { type, touchPoints: pts.map((p, i) => ({ x: p.x, y: p.y, id: 7 + i })) });
    const heldFinger = async (): Promise<[number, number]> => {
      const r = await s.place("w490", 3), q = await beside();
      assert.ok(r.inView && r.hit === "the picture", at + "the control shown before the finger (a precondition): " + JSON.stringify(r));
      await s.events();
      await touchEv("touchStart", [r.pt]);
      await s.page.mouse.click(q.x, q.y);
      await touchEv("touchEnd", []);
      await frames(s.page, 3);
      const evs = await s.events();
      rec.finger = fmt(evs);
      assert.ok(evs.some((e) => e.type === "pointerup" && e.ptype === "touch") && evs.filter((e) => e.type === "mousedown").length === 2, at + "the finger's pointerup, then its compatibility mousedown after the mouse's (a precondition): " + fmt(evs));
      return s.opens();
    };
    const swipe = async (x: number, y0: number, dy: number): Promise<void> => {
      await touchEv("touchStart", [{ x, y: y0 }]);
      for (let i = 1; i <= 10; i++) { await touchEv("touchMove", [{ x, y: Math.round(y0 + (dy * i) / 10) }]); await frames(s.page, 1); }
      await touchEv("touchEnd", []);
      await frames(s.page, 4);
    };
    const press = async (covered: boolean): Promise<[number, number]> => {
      let p: { x: number; y: number };
      if (covered) {
        await s.place("w490", 3);
        await openFlyoutBy(s, "script");
        const fl = await s.flyout(), r = await s.read("w490");
        assert.ok(fl.open && fl.overCentre && r.hit === "the picture", at + "the flyout over the control's centre at the mouse's press (a precondition): " + JSON.stringify({ fl, r }));
        p = r.pt;
      } else {
        const out = await s.place("w490", -60);
        assert.ok(out.outside && out.hit === "the picture", at + "the control out of view at the mouse's press (a precondition): " + JSON.stringify(out));
        p = out.pt;
      }
      await s.events();
      await s.page.mouse.move(p.x, p.y); await s.page.mouse.down();
      const b = await beside();
      await swipe(b.x, covered ? 300 : 150, covered ? 40 : 260);
      await s.page.mouse.up();
      await frames(s.page, 3);
      const evs = await s.events();
      assert.ok(evs.some((e) => e.type === "pointercancel" && e.ptype === "touch") && evs.some((e) => e.type === "click" && e.ptype === "mouse"), at + "the swipe's touch ends in a pointercancel while the mouse is held, and the mouse's release clicks (a precondition): " + fmt(evs));
      if (!covered) assert.ok((await s.read("w490")).inView, at + "the swipe scrolled the control into view before the release (a precondition)");
      rec[(covered ? "covered" : "out of view")] = fmt(evs);
      const o = await s.opens();
      await closeCovers(s);
      return o;
    };
    for (const covered of [false, true]) {
      const where = covered ? "under the text-size flyout" : "with the control out of view";
      cell("the mouse's press on the picture " + where + ", a finger's swipe beside it while the mouse is held, the release: the click's opens", [0, 0], await press(covered));
      const fingerOpens = await heldFinger();
      cell("a finger held on the picture with the control shown, the mouse's click beside it, the finger lifted, then the mouse's press on the picture " + where + ", a swipe while it is held, the release: [the finger's opens, the click's]", [[0, 0], [0, 0]], [fingerOpens, await press(covered)]);
    }
    note("record " + JSON.stringify({ engine: "chromium", surface, scene: "touch-beside-mouse", ...rec }));
  });
}
