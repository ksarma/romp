// The one gate's stacking cells, one set for every engine (the file review's round 17, extra9-1, and the coordinator's decision 4 on
// it), for the link-navigation follow-on of plans/markdown-viewer.md: file-figure-open-browser.test.ts runs them in Chromium, and
// file-figure-open-engines-browser.test.ts in WebKit and Firefox, the leg that stays off the shared roster of browser legs, since the
// job that runs the roster installs Chromium alone. The picture's web control rests positioned at z-index 1, and that z-index keeps it
// above author content at z-index auto or 0 only where no stacking context stands around the picture; so the viewer's rule for a
// top-level table shifts it with a position and a left, which make no stacking context, and file-view.ts dropStackClasses takes off
// each figure and every element above it the page classes the sheets would make a stacking context there (SHEET_CONTEXT_CLASSES,
// held to the sheets both ways by file-figure-open.test.ts). The cells, on the chat modal and the Files pane at 900 by 700 on a page
// with a touchscreen beside the mouse, each a reading off the page or a count of [popups, document requests] taken by the gate's own
// calls (opensCounter, below), the pictures from the web routed at the context and every value synthetic:
// - the table road, two scenes: a loaded remote picture in a plain top-level table, then a kept positioned author element after the
//   table (fc-overlay, absolute over the Rendered box); and the same table, then a later author svg whose shadow is placed over
//   the control. In the first the table is positioned relative with no translate, no transform and z-index auto, a press at the
//   control's centre reaches the control, and a click on it, a tap on it, Enter and Space each open once; in the second no red pixel
//   of the shadow shows inside the control's box, the shadow standing there with the control hidden, and a click and Enter open once;
// - the class road, three scenes, each a remote picture inside an author element of a page class the list takes: a div of
//   romp-lightbox-img (a will-change of transform) before the positioned element, a div of meta-held-mark (a translate) before the
//   svg, and a span of path-full-wait (a min-width of 200px) inside a div of rail-hit (absolute at z-index 0) before the positioned
//   element, where the span holds the picture above the floor inside the narrow strip, so it wears its control; each element after
//   the paint holds none of those classes, and the cells read as the table's;
// - a class the sheets scale under :active (ask-btn), around the picture before the svg: with the mouse held on the control no red
//   pixel of the shadow shows inside the control's box, and the release opens once;
// - an author's marquee around the picture, before the positioned element and before the svg: the sanitizer removes the marquee
//   and keeps the picture where it stood (md-sanitize.ts MD_FORBID_TAGS), so no marquee stands around the picture after the paint,
//   and the cells read as the table's;
// - in each scene with the positioned element, a click on the picture's own body, off its control, where that element takes the
//   press: it opens nothing, a stated cost (the coordinator's decision 6), green by design, the control opening the picture there.
// Every scene is red at 0ab74924c in every engine and on both surfaces, where the table's shift was a translate, the page classes
// stood and the sanitizer kept the marquee; which of its cells, and their reads there, are a private witness kept out of the tree.
import * as assert from "node:assert/strict";
import * as zlib from "node:zlib";
import { openViewer, frames, PARA, REPORT } from "./real-viewer-leg";

export type StackEngine = "chromium" | "firefox" | "webkit";
export type StackSurface = "chat" | "pane";
/** One cell's reading: its name, the wanted value and the value read. */
export type StackCell = [string, unknown, unknown];

const WEB = "http://example.test";
const PIC = '<img alt="pic" src="' + WEB + '/pic.svg">';
const sized = (w: number, h: number, fill: string): string => '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '"><rect width="' + w + '" height="' + h + '" fill="' + fill + '"/></svg>';
const OVERLAY = '<div id="later" class="fc-overlay"></div>';
const COVER = (dx: number, dy: number): string => 'Words <svg id="cover" width="50" height="50" filter="drop-shadow(' + dx + "px " + dy + 'px 0 rgb(255,0,0))"><rect width="50" height="50" fill="rgb(255,0,0)"/></svg> end.';
const TAIL = Array.from({ length: 12 }, (_, i) => PARA(i + 3)).join("\n\n");
const doc = (around: string, after: string): string => "# Report\n\n" + PARA(1) + "\n\n" + around + "\n\n" + after + "\n\n" + TAIL + "\n";
type Around = { key: string; what: string; md: string; wrapper: string | null; classes: string | null };
const TABLE: Around = { key: "table", what: "a remote picture in a plain top-level table", md: "| Figure |\n|---|\n| ![pic](" + WEB + "/pic.svg) |", wrapper: null, classes: null };
const LIGHTBOX: Around = { key: "lightbox", what: "a remote picture inside an author's div of romp-lightbox-img", md: '<div id="wrap" class="romp-lightbox-img keep">' + PIC + "</div>", wrapper: "wrap", classes: "keep" };
const HELD: Around = { key: "held", what: "a remote picture inside an author's div of meta-held-mark", md: '<div id="wrap" class="meta-held-mark keep">' + PIC + "</div>", wrapper: "wrap", classes: "keep" };
const RAIL: Around = { key: "rail", what: "a remote picture inside an author's span of path-full-wait inside a div of rail-hit", md: '<div id="wrap" class="rail-hit keep"><span class="path-full-wait">' + PIC + "</span></div>", wrapper: "wrap", classes: "keep" };
const PRESS: Around = { key: "press", what: "a remote picture inside an author's div of ask-btn", md: '<div id="wrap" class="ask-btn keep">' + PIC + "</div>", wrapper: "wrap", classes: "keep" };
const MARQUEE: Around = { key: "marquee", what: "a remote picture inside an author's marquee", md: 'A <marquee scrollamount="0">' + PIC + "</marquee> held.", wrapper: null, classes: null };

/** In the viewer's document: the picture, its control, the reading of a scene (`__sread`: the control's box, what a press at its
 *  centre reaches, the table's or the wrapper's state) and `__scentre`, which scrolls the control to the body's middle. */
const INSTALL = (): void => {
  const w = window as any;
  w.__simg = () => document.querySelector('.fileview-md img[alt="pic"]') as HTMLElement;
  w.__sctl = () => { let a: Element = w.__simg(); for (let p = a.parentElement; p && p.localName === "a" && p.children.length === 1; p = a.parentElement) a = p; const n = a.nextElementSibling; return n && n.hasAttribute("data-fv-figopen") ? n as HTMLElement : null; };
  w.__scentre = () => { const c = w.__sctl() as HTMLElement; c.scrollIntoView({ block: "center" }); };
  w.__sread = (wrapper: string | null) => {
    const c = w.__sctl() as HTMLElement | null, img = w.__simg() as HTMLElement;
    const r = c ? c.getBoundingClientRect() : null;
    const later = document.getElementById("user-content-later");
    const e = r ? document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2) : null;
    const table = img.closest("table") as HTMLElement | null, tcs = table ? getComputedStyle(table) : null;
    const wrap = wrapper ? document.getElementById("user-content-" + wrapper) : null;
    return {
      control: !!c, loaded: (img as HTMLImageElement).complete && (img as HTMLImageElement).naturalWidth > 0, web: !!c && c.classList.contains("fv-figopen-web"),
      box: r ? { x: r.left, y: r.top, w: r.width, h: r.height, cx: (r.left + r.right) / 2, cy: (r.top + r.bottom) / 2 } : null,
      hit: !e || !c ? "null" : e === c || c.contains(e) ? "the control" : later && (e === later || later.contains(e)) ? "the later element" : e.localName,
      topTable: !!table && !!table.parentElement && table.parentElement.classList.contains("fileview-md"),
      table: tcs ? [tcs.position, tcs.translate, tcs.transform, tcs.zIndex] : null,
      wrapper: wrap ? wrap.getAttribute("class") : null,
      marquee: !!img.closest("marquee"),
      later: later ? getComputedStyle(later).position : null,
      cover: (() => { const s = document.getElementById("user-content-cover"); if (!s) return null; const b = s.getBoundingClientRect(); return { x: b.left, y: b.top }; })(),
    };
  };
};
type Read = { control: boolean; loaded: boolean; web: boolean; box: { x: number; y: number; w: number; h: number; cx: number; cy: number } | null; hit: string; topTable: boolean; table: string[] | null; wrapper: string | null; marquee: boolean; later: string | null; cover: { x: number; y: number } | null };

/** A screenshot's pixels, as [r, g, b] each: the PNG Playwright writes (8 bits a channel, RGB or RGBA, no interlace) read here, in
 *  node, so no page policy on image sources stands between the read and the pixels. */
function pngPixels(buf: Buffer): number[][] {
  assert.equal(buf.readUInt32BE(0), 0x89504e47, "a PNG");
  let pos = 8, width = 0, height = 0, bitDepth = 0, colorType = 0, interlace = 0;
  const idat: Buffer[] = [];
  while (pos + 8 <= buf.length) {
    const len = buf.readUInt32BE(pos), type = buf.toString("ascii", pos + 4, pos + 8), data = buf.subarray(pos + 8, pos + 8 + len);
    if (type === "IHDR") { width = data.readUInt32BE(0); height = data.readUInt32BE(4); bitDepth = data[8]; colorType = data[9]; interlace = data[12]; }
    else if (type === "IDAT") idat.push(data);
    else if (type === "IEND") break;
    pos += 12 + len;
  }
  assert.ok(bitDepth === 8 && interlace === 0 && (colorType === 6 || colorType === 2), "an 8-bit RGB or RGBA PNG with no interlace");
  const bpp = colorType === 6 ? 4 : 3, raw = zlib.inflateSync(Buffer.concat(idat)), stride = width * bpp, out = Buffer.alloc(stride * height);
  let p = 0;
  for (let y = 0; y < height; y++) {
    const f = raw[p++], row = y * stride, prev = row - stride;
    for (let x = 0; x < stride; x++) {
      const a = x >= bpp ? out[row + x - bpp] : 0, b = y > 0 ? out[prev + x] : 0, c = x >= bpp && y > 0 ? out[prev + x - bpp] : 0, v = raw[p++];
      const pa = Math.abs(b - c), pb = Math.abs(a - c), pc = Math.abs(a + b - 2 * c);
      const r = f === 0 ? v : f === 1 ? v + a : f === 2 ? v + b : f === 3 ? v + ((a + b) >> 1) : f === 4 ? v + (pa <= pb && pa <= pc ? a : pb <= pc ? b : c) : NaN;
      assert.ok(!Number.isNaN(r), "a PNG filter of 0 to 4");
      out[row + x] = r & 255;
    }
  }
  const px: number[][] = [];
  for (let i = 0; i < out.length; i += bpp) px.push([out[i], out[i + 1], out[i + 2]]);
  return px;
}
/** The page-side record of every window.open call, installed in the viewer's page before a scene's first gesture (the viewer opens a
 *  web picture's tab on the dashboard through openUrlTab's window.open alone): each call is recorded synchronously, as it is made,
 *  with whether it came inside an event's dispatch (window.event set, as it is while a gesture's listeners run) or outside one (a
 *  timer's), and the window.open it wraps still runs. */
export const RECORD_OPENS = (): void => {
  const w = window as any;
  if (w.__opensLog) return;
  w.__opensLog = [];
  const open = window.open;
  window.open = function (...a: unknown[]) { w.__opensLog.push({ inEvent: !!w.event, type: w.event ? String(w.event.type) : null }); return (open as any).apply(window, a); } as typeof window.open;
};
/** How long a read waits for the popups and document requests the recorded calls owe before it fails, loudly: a failure bound, which
 *  decides no count. */
const OPENS_BOUND = 20000;
/** A scene's opens counted by the gate's own calls (the file review's round 18, extra6-2): the counters of a time window (24
 *  animation frames and a 350 ms settle) charged a popup WebKit delivered later to the next cell, or lost it after the scene's last
 *  cell. `popups` and `docReqs` are the scene's, filled by its page listener and its route, each of which calls `wake`. `opens` reads
 *  the calls recorded since the last read (RECORD_OPENS) and, where there are any made inside an event's dispatch, waits, with a
 *  bound that fails loudly, until that many popups and document requests have arrived since the last read, so a late popup lands
 *  in its own cell; a read whose gesture made no call waits for nothing more, and reads what has arrived, its [0,0] exact; it returns
 *  [popups, document requests] since the last read, and closes the popups. `end`, after the scene's last cell, waits the same way for
 *  every call the scene recorded and holds the popups and document requests seen equal to the calls, every call one a cell read
 *  inside an event's dispatch, so a stray open made or delivered before `end` reads the record, a call outside a dispatch or after the
 *  last cell's read or a popup no call made, is charged to its scene; a call a timer makes after that read goes unseen, since the
 *  scene's page closes after `end`. */
export function opensCounter(page: any, popups: any[], docReqs: string[], scene: string): { opens: () => Promise<[number, number]>; end: () => Promise<void>; wake: () => void } {
  const waiters: Array<() => void> = [];
  const wake = (): void => { for (const f of waiters.splice(0)) f(); };
  const until = async (np: number, nd: number, why: string): Promise<void> => {
    const stop = Date.now() + OPENS_BOUND;
    while (popups.length < np || docReqs.length < nd) {
      const left = stop - Date.now();
      assert.ok(left > 0, scene + ": " + why + ": " + popups.length + " popups and " + docReqs.length + " document requests of " + np + " and " + nd + " after " + OPENS_BOUND + " ms (a failure bound, which decides no count)");
      await new Promise<void>((r) => { waiters.push(r); setTimeout(r, left); });   // the next popup or request, or the bound
    }
  };
  const log = (): Promise<Array<{ inEvent: boolean; type: string | null }>> => page.evaluate(() => ((window as any).__opensLog || []).slice());
  let p0 = 0, d0 = 0, c0 = 0, stray = 0;
  const opens = async (): Promise<[number, number]> => {
    const all = await log();
    const fresh = all.slice(c0);
    c0 = all.length;
    const calls = fresh.filter((c) => c.inEvent).length;
    stray += fresh.length - calls;
    if (calls) await until(p0 + calls, d0 + calls, "the popups and document requests the cell's " + calls + " window.open call(s) owe");
    const np = popups.slice(p0), nd = docReqs.slice(d0);
    p0 = popups.length; d0 = docReqs.length;
    for (const p of np) await p.close().catch(() => null);
    await page.bringToFront().catch(() => null);
    return [np.length, nd.length];
  };
  const end = async (): Promise<void> => {
    const all = await log();
    stray += all.length - c0;   // a call after the last cell's read is no cell's
    c0 = all.length;
    await until(all.length, all.length, "the popups and document requests the scene's " + all.length + " window.open call(s) owe");
    assert.deepEqual({ stray, popups: popups.length, requests: docReqs.length }, { stray: 0, popups: all.length, requests: all.length }, scene + ": every window.open call was a gesture's, read by its cell, and the popups and document requests seen equal the " + all.length + " call(s) recorded (a stray open, charged to this scene)");
  };
  return { opens, end, wake };
}
/** The red pixels of the shadow inside the control's box, 4px in from each edge (clear of its rounded corners and its dashed line), and
 *  the pixels read. */
async function redInside(page: any, box: NonNullable<Read["box"]>): Promise<[number, number]> {
  const clip = { x: Math.ceil(box.x) + 4, y: Math.ceil(box.y) + 4, width: Math.floor(box.w) - 8, height: Math.floor(box.h) - 8 };
  assert.ok(clip.width > 4 && clip.height > 4, "the control's box leaves an inside to read (a precondition): " + JSON.stringify(box));
  const px = pngPixels(await page.screenshot({ clip }));
  return [px.filter(([r, g, b]) => r > 200 && g < 60 && b < 60).length, px.length];
}

/** `text` open on the surface in a page with a touchscreen beside the mouse, the remote picture routed and loaded through the gate, the
 *  helpers installed and the control scrolled to the body's middle, and `body` run with the page and an opens counter that counts by
 *  the gate's calls (opensCounter), its scene's end read after the last cell under `name`; the page errors asserted empty after it. */
async function stackScene(browser: any, engine: StackEngine, surface: StackSurface, text: string, body: (page: any, opens: () => Promise<[number, number]>, read: () => Promise<Read>) => Promise<void>, wrapper: string | null, name: string): Promise<void> {
  const docReqs: string[] = [], popups: any[] = [];
  let wake = (): void => { /* no counter yet */ };
  const before = async (pg: any): Promise<void> => {
    await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
      const req = route.request();
      if (req.resourceType() === "document") { docReqs.push(req.url()); wake(); return route.fulfill({ status: 200, contentType: "text/html", body: "<p>third party</p>" }); }
      return route.fulfill({ status: 200, contentType: "image/svg+xml", body: sized(300, 200, "#6a3d9a") });
    });
  };
  const host = { newPage: (o: any) => browser.newPage({ ...o, hasTouch: true }) };
  const { page, errors } = await openViewer(host, surface, 900, 700, { docs: { [REPORT]: text }, before });
  try {
    for (let i = 0; i < 20 && await page.evaluate(() => !!document.querySelector('.fileview-md [data-act="fv-load"]')); i++) { await page.evaluate(() => { (document.querySelector('.fileview-md [data-act="fv-load"]') as HTMLElement).click(); }); await frames(page, 3); }
    await page.waitForFunction(() => { const i = document.querySelector('.fileview-md img[alt="pic"]') as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0; }, null, { timeout: 15000 });
    await frames(page, 4);
    await page.evaluate(INSTALL);
    await page.evaluate(() => (window as any).__scentre());
    await page.mouse.move(2, 690);
    await frames(page, 4);
    await page.evaluate(RECORD_OPENS);
    const counter = opensCounter(page, popups, docReqs, engine + ", " + surface + ", the scene " + name);
    wake = counter.wake;
    page.context().on("page", (p: any) => { popups.push(p); wake(); });
    const read = (): Promise<Read> => page.evaluate((w: string | null) => (window as any).__sread(w), wrapper);
    await body(page, counter.opens, read);
    await counter.end();
  } finally {
    await page.close();
  }
  assert.deepEqual(errors, [], engine + ", " + surface + ": no page errors");
}

/** Every cell for an engine on a surface, run in `browser`, each reading returned beside its wanted value; `note` receives each scene's
 *  record. The preconditions are asserted as they are read. */
export async function stackCells(browser: any, engine: StackEngine, surface: StackSurface, note: (m: string) => void): Promise<StackCell[]> {
  const cells: StackCell[] = [];
  const cell = (what: string, want: unknown, got: unknown): void => { cells.push([what, want, got]); };
  const at = engine + ", " + surface + ": ";
  const again = async (page: any): Promise<void> => { await page.evaluate(() => (window as any).__scentre()); await page.mouse.move(2, 690); await frames(page, 3); };
  // the positioned element after the picture: the element's state, the hit at the control's centre, and each gesture on the control
  for (const s of [TABLE, LIGHTBOX, RAIL, MARQUEE]) {
    await stackScene(browser, engine, surface, doc(s.md, OVERLAY), async (page, opens, read) => {
      const r = await read();
      const rec: Record<string, unknown> = { read: r };
      assert.ok(r.loaded && r.control && r.web && r.box && r.later === "absolute", at + s.key + ": the loaded picture wears its web control and the later element is positioned (a precondition): " + JSON.stringify(r));
      if (s === TABLE) {
        assert.ok(r.topTable, at + "the picture stands in a top-level table (a precondition)");
        cell(s.what + ", then a positioned element: the table's [position, translate, transform, z-index]", ["relative", "none", "none", "auto"], r.table);
      } else if (s === MARQUEE) cell(s.what + ", then a positioned element: the picture inside a marquee after the paint", false, r.marquee);
      else cell(s.what + ", then a positioned element: the element's classes after the paint", s.classes, r.wrapper);
      cell(s.what + ", then a positioned element: what a press at the control's centre reaches", "the control", r.hit);
      await page.mouse.click(r.box!.cx, r.box!.cy);
      cell(s.what + ", then a positioned element: a click on the control opens", [1, 1], await opens());
      await again(page);
      const r2 = await read();
      await page.touchscreen.tap(r2.box!.cx, r2.box!.cy);
      cell(s.what + ", then a positioned element: a tap on the control opens", [1, 1], await opens());
      for (const key of ["Enter", " "]) {
        await again(page);
        await page.evaluate(() => ((window as any).__sctl() as HTMLElement).focus({ preventScroll: true }));
        await frames(page, 2);
        await page.keyboard.press(key);
        cell(s.what + ", then a positioned element: " + (key === " " ? "Space" : key) + " on the control opens", [1, 1], await opens());
      }
      // the picture's own body under the positioned element (the coordinator's decision 6): a stated cost, green by design
      await again(page);
      const img = await page.evaluate(() => { const b = (window as any).__simg().getBoundingClientRect(); const x = Math.round(b.left + 40), y = Math.round(b.bottom - 30); const e = document.elementFromPoint(x, y), later = document.getElementById("user-content-later"); return { x, y, onLater: !!e && !!later && (e === later || later.contains(e)) }; });
      assert.ok(img.onLater, at + s.key + ": a press on the picture's own body, off its control, reaches the positioned element (a precondition): " + JSON.stringify(img));
      await page.mouse.click(img.x, img.y);
      rec.pictureBodyClick = await opens();
      cell(s.what + ", then a positioned element: a click on the picture's own body, which the element takes, opens", [0, 0], rec.pictureBodyClick);
      note("record " + JSON.stringify({ engine, surface, scene: s.key + "+later", ...rec }));
    }, s.wrapper, s.key + "+later");
  }
  // the svg whose shadow is placed over the control: first read where the control and the svg stand, then open with the shadow moved
  const place = async (s: Around): Promise<[number, number]> => {
    let off: [number, number] = [0, 0];
    await stackScene(browser, engine, surface, doc(s.md, COVER(0, 0)), async (page, _opens, read) => {
      const r = await read();
      assert.ok(r.box && r.cover, at + s.key + ": the control and the svg stand in the document (a precondition): " + JSON.stringify(r));
      off = [Math.round(r.box!.cx - r.cover!.x - 25), Math.round(r.box!.cy - r.cover!.y - 25)];
    }, s.wrapper, s.key + "+place");
    return off;
  };
  for (const s of [TABLE, HELD, PRESS, MARQUEE]) {
    const off = await place(s);
    await stackScene(browser, engine, surface, doc(s.md, COVER(off[0], off[1])), async (page, opens, read) => {
      const r = await read();
      const rec: Record<string, unknown> = { off, read: r };
      assert.ok(r.loaded && r.control && r.web && r.box && r.cover, at + s.key + ": the loaded picture wears its web control and the svg stands in the document (a precondition): " + JSON.stringify(r));
      await page.evaluate(() => { ((window as any).__sctl() as HTMLElement).style.visibility = "hidden"; });
      await frames(page, 3);
      const under = await redInside(page, r.box!);
      await page.evaluate(() => { ((window as any).__sctl() as HTMLElement).style.visibility = ""; });
      await frames(page, 3);
      rec.underHidden = under;
      assert.ok(under[0] >= under[1] * 0.9, at + s.key + ": with the control hidden the shadow fills the inside of its box, so it is placed over the control (a precondition): " + JSON.stringify(under));
      if (s === TABLE) cell(s.what + ", then an svg's shadow over the control: the table's [position, translate, transform, z-index]", ["relative", "none", "none", "auto"], r.table);
      else if (s === MARQUEE) cell(s.what + ", then an svg's shadow over the control: the picture inside a marquee after the paint", false, r.marquee);
      else cell(s.what + ", then an svg's shadow over the control: the element's classes after the paint", s.classes, r.wrapper);
      if (s === PRESS) {
        cell(s.what + ", then an svg's shadow over the control: the shadow's red pixels inside the control's box at rest", 0, (await redInside(page, r.box!))[0]);
        await page.mouse.move(r.box!.cx, r.box!.cy);
        await page.mouse.down();
        await frames(page, 6);
        await new Promise((res) => setTimeout(res, 150));   // the class's 0.08 s transition of its scale ends
        const held = await redInside(page, r.box!);
        rec.held = held;
        cell(s.what + ", then an svg's shadow over the control: the shadow's red pixels inside the control's box with the mouse held on the control", 0, held[0]);
        await page.mouse.up();
        cell(s.what + ", then an svg's shadow over the control: the release opens", [1, 1], await opens());
      } else {
        const shown = await redInside(page, r.box!);
        rec.shown = shown;
        cell(s.what + ", then an svg's shadow over the control: the shadow's red pixels inside the control's box", 0, shown[0]);
        await page.mouse.click(r.box!.cx, r.box!.cy);
        cell(s.what + ", then an svg's shadow over the control: a click on the control opens", [1, 1], await opens());
        await again(page);
        await page.evaluate(() => ((window as any).__sctl() as HTMLElement).focus({ preventScroll: true }));
        await frames(page, 2);
        await page.keyboard.press("Enter");
        cell(s.what + ", then an svg's shadow over the control: Enter on the control opens", [1, 1], await opens());
      }
      note("record " + JSON.stringify({ engine, surface, scene: s.key + "+cover", ...rec }));
    }, s.wrapper, s.key + "+cover");
  }
  return cells;
}
