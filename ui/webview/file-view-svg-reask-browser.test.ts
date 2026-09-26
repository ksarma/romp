// An svg picture's own load in the file viewer, in headless Chromium over the REAL viewer and the REAL Comments panel
// (real-viewer-leg.ts serves the page; its fetch stub answers the viewer's own GET of the file, and a route here answers the
// picture's own request to its /file address, which the page's stub never sees). The picture loads in a request of its own
// after the viewer's fetch lands, so: the romp loader waits inside the picture box, in the part of the body on screen, until
// the picture's load (a repaint at the same address has a loader exactly when the picture is not complete once its src is
// set, which depends on whether the page still holds it: one case forces a garbage collection first); a failed load asks the
// address again with the viewer's fetch, once, and the pane then shows that answer's own words (the relay's 502 text, the
// browser's text for a refused connection) with the path, or, when the bytes arrive and the picture fails again,
// SVG_PICTURE_FAILED, worded for both causes; the pane comes back to the picture on romp:wsup, hostUp and romp:hostRelayUp,
// and on a kernel message whose probe of the address loads (three probes sent, one at a time, across the panes their own
// fetches paint, counted at the send, with and without a forced garbage collection; a reconnect event refills them); a
// reconnect event that arrives while a fetch that asked the address again is out runs that fetch once more at once when it
// fails, and one that arrives while the picture such a fetch landed is still loading asks the address once more at once when
// that picture fails, in place of the pane; a press of the Source toggle while the re-ask's fetch is out leaves the Source view
// standing over its answer, and a picture failure after a press (the Source view still decoding) starts nothing, nor does a
// reload that lands in that window, whose landing paints no picture over the press; a press of the Source toggle ends the
// attempt of a fetch that asked again, so the picture shown when the person returns asks the address again once when it
// fails, a reconnect event heard before or after the press included; a png whose bytes do not decode keeps DECODE_FAILED
// with no second fetch; and with the Comments panel open the panel's wait for a reload's bytes ends when they land, while
// the picture's own load, or the Source view's decode of them, is still out, and a change card keeps its state from the
// landing until that paint (the deadline is faked with the page's clock, so no case waits 15 s). The
// chat modal's cases that count probes run with the page's markdown-image heal installed (preview.ts installMdImgHeal, which
// also hears the picture's error and skips the viewer's picture) and both of render.ts's retry drivers, its romp:wsup line and
// its retry on every kernel message, so the probes' count of three is measured in the chat page as it runs (the loader's case installs neither). After every road the picture's src is its /file address (the relay's for a remote session) and no object
// URL is made for the svg. Waits are for the page's own events or the picture's settling, never a timer. Skips LOUDLY without
// a playwright browser (CI installs none). Synthetic values only: /repo/notes-api paths, the placeholder sid, host TESTHOST.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, ROOT, REPORT, LONG, SID, MT2, type Mode } from "./real-viewer-leg";

const FIG = ROOT + "/figs/a.svg";
const PNG = ROOT + "/figs/b.png";
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="120"><rect width="200" height="120" fill="#336699"/></svg>';
const BAD_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="120"><rect width="200"';   // cut short: does not decode
const RELAY_502 = "tunnel to TESTHOST is not answering; re-dialing";
const SVG_PICTURE_FAILED = "this image failed to load or decode: the connection may have dropped, or the file may be mid-write or truncated";
const DECODE_FAILED = "this image failed to decode: it may be mid-write or truncated";
const REMOTE = "TESTHOST:" + SID;
/** The picture's /file address for a session: the local route, or the relay's with the bare sid; the key follows. */
const address = (sid: string): string => (sid === REMOTE ? "/remote/TESTHOST/file" : "/file") + "?path=" + encodeURIComponent(FIG) + "&sid=" + encodeURIComponent(SID) + "&v=";

type PicMode = "ok" | "bad" | "502" | "refuse" | "hold" | "hold502" | "holdRefuse" | "once502";
type Pic = { mode: PicMode; seq: PicMode[]; reqs: string[]; release: () => void; held: Promise<void>; once: boolean };
/** A page of the surface with the instruments this file reads, the report opened and closed, ready for the svg to open. The
 *  picture's requests (the local route and the relay's) go to `pic.mode`: the svg, bytes that do not decode, the relay's 502,
 *  a refused connection, held until `pic.release()` and then the svg (or, "hold502", the relay's 502, and "holdRefuse", a refused
 *  connection), or a 502 once and the svg after; while `pic.seq` holds modes, each request takes the next of them instead. In the page: `__asks` counts the viewer's GETs of the svg (the page's stub, never the picture's request); after
 *  `__okAsks` of them, `__fail` answers the rest up to the GET numbered `__failTo` (a status with its words, or "refuse": a real
 *  fetch the page's route refuses, so the browser's own words); `__gate`, a promise, holds the next GET, or with `__gateAt` set
 *  the GET of that number only, and `__released` is set when a held GET goes on; `__objectUrls` records the type of every
 *  object URL made; `__paneSeen` whether a failure pane ever showed, `__panes` how many were painted, and `__paneLog` the GETs
 *  so far and error() when each was painted (read in the pane paint's own microtask, before anything that paint started lands). `__probes` counts the
 *  detached pictures of the svg's address the page makes (the way back's probes, counted when each is sent, whether it then
 *  loads from the page's memory or asks the network) and `__probesSettled` those that loaded or failed; `__srcSet` records
 *  whether the viewer's picture was complete the moment its src was set; `__picErrs` counts the viewer picture's error events
 *  once each has run its listeners; `__textGate`, a promise, holds a decode of the fetched bytes (the Source view's).
 *  `heal`: the chat page's markdown-image heal and render.ts's two retry drivers (its romp:wsup line and its per-message retry;
 *  `__perMessage` counts the latter's runs), installed before the open. `clock`: the page's
 *  clock installed (it flows until a case moves it). */
async function scene(browser: any, mode: Mode, opts: { heal?: boolean; clock?: boolean; docs?: Record<string, string> } = {}): Promise<{ page: any; errors: string[]; pic: Pic }> {
  let release: () => void = () => {};
  const pic: Pic = { mode: "ok", seq: [], reqs: [], release: () => release(), held: new Promise<void>((r) => { release = r; }), once: false };
  const before = async (page: any): Promise<void> => {
    if (opts.clock) await page.clock.install();
    await page.route((u: URL) => (u.pathname === "/file" || u.pathname === "/remote/TESTHOST/file") && u.searchParams.get("path") === FIG && u.searchParams.has("v"), async (route: any) => {
      pic.reqs.push(route.request().url());
      let m = pic.seq.length ? pic.seq.shift()! : pic.mode;
      if (m === "once502") { m = pic.once ? "ok" : "502"; pic.once = true; }
      if (m === "hold" || m === "hold502" || m === "holdRefuse") { await pic.held; m = m === "hold" ? "ok" : m === "hold502" ? "502" : "refuse"; }
      if (m === "refuse") return route.abort("connectionrefused");
      if (m === "502") return route.fulfill({ status: 502, contentType: "text/plain", body: RELAY_502 });
      return route.fulfill({ status: 200, contentType: "image/svg+xml", body: m === "bad" ? BAD_SVG : SVG });
    });
    await page.route((u: URL) => u.pathname === "/refused", (route: any) => route.abort("connectionrefused"));
    await page.evaluate(([fig, png, heal]: [string, string, boolean]) => {
      const w = window as any;
      const stub = w.fetch;
      const frame = document.createElement("iframe");
      frame.style.display = "none";
      document.body.appendChild(frame);
      const pageFetch = (frame.contentWindow as any).fetch.bind(frame.contentWindow);   // the browser's own fetch, which the stub replaced here
      w.__asks = 0; w.__pngAsks = 0; w.__okAsks = Infinity; w.__failTo = Infinity; w.__fail = null; w.__gate = null; w.__gateAt = 0; w.__released = false; w.__objectUrls = []; w.__paneSeen = false; w.__panes = 0; w.__paneLog = [];
      w.__probes = 0; w.__probesSettled = 0; w.__srcSet = null; w.__picErrs = 0; w.__textGate = null;
      w.fetch = async function (url: string, init?: any) {
        const u = String(url);
        const m = /[?&]path=([^&]*)/.exec(u);
        const p = m ? decodeURIComponent(m[1]) : "";
        const get = !(init && init.method === "HEAD");
        if (p === fig && get) {
          w.__asks++;
          if (w.__gate && (!w.__gateAt || w.__asks === w.__gateAt)) { const g = w.__gate; w.__gate = null; await g; w.__released = true; }
          if (w.__asks > w.__okAsks && w.__asks <= w.__failTo && w.__fail) {
            if (w.__fail === "refuse") return pageFetch(location.protocol + "//" + location.host + "/refused");
            return new Response(w.__fail.body, { status: w.__fail.status, headers: { "Content-Type": "text/plain" } });
          }
        }
        if (p === png && get) w.__pngAsks++;
        if (p === png) return new Response(get ? new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x02]) : null, { status: 200, headers: { "Content-Type": "image/png", "X-Romp-Mtime-Ns": w.__mtime } });   // a png whose bytes do not decode
        return stub(url, init);
      };
      const mint = URL.createObjectURL.bind(URL);
      URL.createObjectURL = (b: any) => { w.__objectUrls.push(b && b.type || ""); return mint(b); };
      new MutationObserver((ms) => { for (const r of ms) for (const n of Array.from(r.addedNodes)) if (n.nodeType === 1 && ((n as Element).matches(".fileview-err") || (n as Element).querySelector(".fileview-err"))) { w.__paneSeen = true; w.__panes++; w.__paneLog.push({ asks: w.__asks, error: w.__seam ? w.__seam.error() : "no seam" }); } })
        .observe(document.body, { childList: true, subtree: true });
      // the probes, counted at the send: preview.ts probePicture makes each of a fresh Image and sets its src, so the page's
      // Image marks what it makes and the src setter counts a mark set to the svg's address; its settling is counted after the
      // probe's own handlers have run (a listener added after them)
      const Img = w.Image;
      const made = new WeakSet<object>();
      const Probe = function (width?: number, height?: number) { const i = new Img(width, height); made.add(i); return i; } as any;
      Probe.prototype = Img.prototype;
      w.Image = Probe;
      const proto = HTMLImageElement.prototype as any;
      const getSrc = proto.__lookupGetter__("src"), setSrc = proto.__lookupSetter__("src");
      Object.defineProperty(HTMLImageElement.prototype, "src", { configurable: true, get() { return getSrc.call(this); }, set(v: string) {
        setSrc.call(this, v);
        if (made.has(this) && String(v).indexOf("path=" + encodeURIComponent(fig) + "&") >= 0) {
          w.__probes++;
          const done = (): void => { w.__probesSettled++; };
          this.addEventListener("load", done, { once: true });
          this.addEventListener("error", done, { once: true });
        } else if (!this.isConnected && this.classList.contains("fileview-img")) w.__srcSet = { complete: this.complete };   // imgBlock sets the src before the box joins the body
      } });
      window.addEventListener("error", (e) => { const tg = e.target as Element | null; if (tg && tg.tagName === "IMG" && tg.classList.contains("fileview-img")) setTimeout(() => { w.__picErrs++; }, 0); }, true);   // counted once the event's own listeners (imgFailed) have run
      const decode = Blob.prototype.text;
      Blob.prototype.text = function (this: Blob) { const g = w.__textGate; return g ? g.then(() => decode.call(this)) : decode.call(this); };
      if (heal) {
        w.FV.installMdImgHeal();
        window.addEventListener("romp:wsup", () => { w.FV.retryFailedPreviews(); w.FV.refreshSettledPreviews(); });   // render.ts's romp:wsup line, less the path-image heal
        // render.ts's per-message driver (its window message handler), less the path-image heal: a copy faithful for the kernel
        // messages these cases send (type "sessions") and for hostUp, each running the per-message retry, and hostUp the settled drain as well
        window.addEventListener("message", (e) => {
          const m = (e as MessageEvent).data;
          if (!m || m.romp === "link" || m.type === "pipeState") return;
          w.__perMessage = (w.__perMessage || 0) + 1;
          w.FV.retryFailedPreviews();
          if (m.type === "hostUp") w.FV.refreshSettledPreviews();
        });
      }
    }, [FIG, PNG, !!opts.heal]);
  };
  const { page, errors } = await openViewer(browser, mode, 900, 520, { docs: opts.docs || { [REPORT]: LONG, [FIG]: SVG }, before });
  await page.evaluate(() => { (window as any).FV.closeFileView(); });
  return { page, errors, pic };
}
/** Open the svg (or `path`) in the viewer, the paint counters zeroed first (the report's paint came before). */
const openFig = (page: any, sid = SID, path = FIG): Promise<void> => page.evaluate(([p, s]: [string, string]) => { const w = window as any; w.__paints = 0; w.__reflows = 0; w.FV.openFileView(p, s, null); }, [path, sid]);
type State = { pane: string | null; hint: string | null; download: boolean; src: string | null; complete: boolean; width: number; loader: boolean; loaderInBox: boolean; error: string | null; asks: number; paints: number; objectUrls: string[]; paneSeen: boolean };
const state = (page: any): Promise<State> => page.evaluate(() => {
  const w = window as any;
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const pane = body.querySelector(".fileview-err") as HTMLElement | null;
  const img = body.querySelector("img.fileview-img") as HTMLImageElement | null;
  const load = body.querySelector(".fileview-load") as HTMLElement | null;
  return { pane: pane ? (pane.firstChild ? pane.firstChild.textContent : "") : null, hint: pane ? (pane.querySelector(".fileview-err-hint")?.textContent ?? null) : null,
    download: !!(pane && pane.querySelector(".fileview-err-dl")), src: img ? img.getAttribute("src") : null, complete: !!(img && img.complete), width: img ? img.naturalWidth : 0,
    loader: !!load, loaderInBox: !!(load && load.closest(".fileview-imgbox")), error: w.__seam ? w.__seam.error() : "no seam", asks: w.__asks, paints: w.__paints,
    objectUrls: w.__objectUrls.slice(), paneSeen: w.__paneSeen };
});
/** The body settled on a pane or on a picture that decoded. */
const settled = (page: any): Promise<unknown> => page.waitForFunction(() => {
  const body = document.querySelector(".fileview-body");
  if (!body) return false;
  if (body.querySelector(".fileview-err")) return true;
  const img = body.querySelector("img.fileview-img") as HTMLImageElement | null;
  return !!img && img.complete && img.naturalWidth > 0;
}, null, { timeout: 10000 });
/** The property after a road: the picture's src is its /file address, and no object URL was made for the svg. */
function onAddress(s: State, sid: string, road: string): void {
  assert.ok(s.src !== null && s.src.startsWith(address(sid)), road + ": the svg's picture is its /file address, not an object URL; got " + s.src);
  assert.ok(!s.objectUrls.includes("image/svg+xml"), road + ": no object URL made for the svg: " + JSON.stringify(s.objectUrls));
}
/** A kernel message of no kind the way back reads, as the kernel pushes many. */
const kernelMessage = (page: any): Promise<void> => page.evaluate(() => { window.dispatchEvent(new MessageEvent("message", { data: { type: "sessions", sessions: [] } })); });
/** Kernel messages over a pane whose probes fail (the picture's route answering 502): each of the first three sends one probe,
 *  whose request reaches the route, and the fourth sends none. */
async function spendProbes(page: any, pic: Pic, label: string): Promise<void> {
  for (let i = 0; i < 4; i++) {
    const n = pic.reqs.length;
    await kernelMessage(page);
    for (let k = 0; k < 40 && pic.reqs.length === n && i < 3; k++) await frames(page, 1);   // the probe's request reaching the route
    await frames(page, 6);                                                                  // its answer and the probe's error event
    assert.equal(pic.reqs.length, i < 3 ? n + 1 : n, label + ": kernel message " + (i + 1) + (i < 3 ? ", one probe" : ", none: the three probes are spent"));
  }
}
/** The Source toggle's press, in the page. */
const pressSource = (page: any): Promise<void> => page.evaluate(() => { (Array.from(document.querySelectorAll(".fileview-acts button")).find((b) => b.textContent === "Source") as HTMLElement).click(); });
/** A forced garbage collection in the page (Chromium's HeapProfiler.collectGarbage): the page may let go of the pictures it
 *  holds, so a picture at an address it has loaded may ask the network again. */
async function forceGc(page: any): Promise<void> {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("HeapProfiler.collectGarbage");
  await cdp.detach();
}
/** Every probe sent has settled and every fetch from the pane `s` on has painted its pane (the viewer's fetches here all fail
 *  until a case lets one answer): what a kernel message started is over. */
const quiet = (page: any, s: State): Promise<unknown> => page.waitForFunction((b: { asks: number; paints: number }) => {
  const w = window as any;
  return w.__probesSettled === w.__probes && w.__paints - b.paints === w.__asks - b.asks;
}, { asks: s.asks, paints: s.paints }, { timeout: 10000 });
/** The picture decoded in the body. */
const decoded = (page: any): Promise<unknown> => page.waitForFunction(() => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && img.complete && img.naturalWidth > 0; }, null, { timeout: 10000 });
/** One reconnect-class event, as the page hears each: romp:wsup (the pane shim's), hostUp (a message from federation) and
 *  romp:hostRelayUp (federation's CustomEvent). */
const reconnect = (page: any, way: string): Promise<void> => page.evaluate((w0: string) => {
  if (w0 === "hostUp") window.dispatchEvent(new MessageEvent("message", { data: { type: "hostUp", hosts: ["TESTHOST"] } }));
  else if (w0 === "romp:hostRelayUp") window.dispatchEvent(new CustomEvent("romp:hostRelayUp", { detail: { host: "TESTHOST" } }));
  else window.dispatchEvent(new Event("romp:wsup"));
}, way);

for (const gc of [false, true]) {
  test("in a browser, the Files pane and the chat modal: while the svg picture's own request is held the romp loader waits inside the picture box, in the part of the body on screen, and no paint has run; at its answer the loader is gone and the picture has decoded, from its /file address; a repaint at the same address (the Source view and back) has a loader exactly when the picture is not complete once its src is set" + (gc ? ", here with a forced garbage collection between the Source view and back" : ""), { timeout: 240000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      for (const mode of ["pane", "chat"] as Mode[]) {
        const { page, errors, pic } = await scene(browser, mode);
        pic.mode = "hold";
        await openFig(page);
        await page.waitForFunction(() => !!document.querySelector(".fileview-body .fileview-imgbox"), null, { timeout: 10000 });
        await frames(page, 2);
        const held = await page.evaluate(() => {
          const body = document.querySelector(".fileview-body") as HTMLElement;
          const load = body.querySelector(".fileview-imgbox .fileview-load") as HTMLElement | null;
          const img = body.querySelector("img.fileview-img") as HTMLImageElement;
          const b = body.getBoundingClientRect();
          const r = load ? load.getBoundingClientRect() : null;
          return { loader: !!load, onScreen: !!r && r.height > 0 && r.top >= b.top && r.bottom <= b.bottom && r.left >= b.left && r.right <= b.right, complete: img.complete, paints: (window as any).__paints };
        });
        assert.deepEqual(held, { loader: true, onScreen: true, complete: false, paints: 0 }, mode + ": held: the loader in the picture box, inside the body's visible rect, the picture not loaded and no paint yet (" + JSON.stringify(held) + ")");
        pic.release();
        await settled(page);
        await frames(page, 2);
        const s = await state(page);
        assert.equal(s.loader, false, mode + ": released: the loader is gone");
        assert.equal(s.width, 200, mode + ": and the picture has decoded");
        assert.equal(s.paints, 1, mode + ": its load is the one paint");
        onAddress(s, SID, mode + ", the first open");
        // the repaint at the same address: the Source view, then back to the picture. Whether the page still holds it decides
        // whether it is complete the moment its src is set (recorded then by the page's src setter), and the loader follows that
        await pressSource(page);
        await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs"), null, { timeout: 10000 });
        if (gc) await forceGc(page);
        const back = await page.evaluate(() => {
          const w = window as any;
          w.__srcSet = null;
          (Array.from(document.querySelectorAll(".fileview-acts button")).find((b) => b.textContent === "Source") as HTMLElement).click();
          const body = document.querySelector(".fileview-body") as HTMLElement;
          return { picture: !!body.querySelector("img.fileview-img"), loader: !!body.querySelector(".fileview-load"), completeAtSrc: w.__srcSet ? w.__srcSet.complete as boolean : null };
        });
        assert.equal(back.picture, true, mode + ": the Source view and back: the picture repaints");
        assert.notEqual(back.completeAtSrc, null, mode + ": its src was set in the press");
        assert.equal(back.loader, !back.completeAtSrc, mode + ": a loader exactly when the picture was not complete once its src was set (" + JSON.stringify(back) + ")");
        t.diagnostic(mode + (gc ? ", after a forced garbage collection" : "") + ": the repainted picture was " + (back.completeAtSrc ? "complete at its src (the page still held it)" : "not complete at its src (it asked the network)"));
        await settled(page);
        await frames(page, 2);
        const after = await state(page);
        assert.equal(after.loader, false, mode + ": the repainted picture shows with no loader beside it");
        assert.equal(after.width, 200, mode + ": decoded");
        onAddress(after, SID, mode + ", the Source view and back");
        assert.equal(pic.reqs.length, back.completeAtSrc ? 1 : 2, mode + ": the repaint asked for the picture only when it was not complete at its src");
        assert.deepEqual(errors, [], mode + ": no page errors");
        await page.close();
      }
    });
  });
}

test("in a browser, the chat modal with the page's heal: the viewer's fetch succeeds and the picture's own request fails, as the relay's 502 with its words and as a refused connection; the address is asked again once, meets the same failure, and the pane carries that answer's words and the path, never a decode sentence, with error() the pane's words and no paint while the loader waited; then the address answers and romp:wsup fires: the pane clears and the picture decodes", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [name, fail, words] of [["the relay's 502", { status: 502, body: RELAY_502 }, RELAY_502], ["a refused connection", "refuse", "Failed to fetch"]] as Array<[string, unknown, string]>) {
      const { page, errors, pic } = await scene(browser, "chat", { heal: true });
      pic.mode = name === "a refused connection" ? "refuse" : "502";
      await page.evaluate((f: unknown) => { const w = window as any; w.__okAsks = 1; w.__fail = f; }, fail);
      await openFig(page);
      await settled(page);
      await frames(page, 2);
      const s = await state(page);
      assert.equal(s.pane, words, name + ": the pane carries the answer's own words");
      assert.equal(s.hint, FIG, name + ": and the path");
      assert.ok(s.pane !== DECODE_FAILED && s.pane !== SVG_PICTURE_FAILED, name + ": never a decode sentence");
      assert.equal(s.error, words, name + ": error() is the pane's words");
      assert.equal(s.download, false, name + ": no Download over an answer that is not a 413 or a 415");
      assert.equal(s.asks, 2, name + ": the open's fetch and exactly one re-ask");
      assert.equal(s.paints, 1, name + ": one paint, the pane's: the loader's wait fired none");
      // the address answers again, and this page's socket comes back
      pic.mode = "ok";
      await page.evaluate(() => { (window as any).__fail = null; window.dispatchEvent(new Event("romp:wsup")); });
      await page.waitForFunction(() => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && img.complete && img.naturalWidth > 0; }, null, { timeout: 10000 });
      const back = await state(page);
      assert.equal(back.pane, null, name + ": romp:wsup: the pane cleared");
      assert.equal(back.width, 200, name + ": and the picture decoded");
      assert.equal(back.error, null, name + ": error() null over the picture");
      assert.equal(back.asks, 3, name + ": the way back asked once");
      onAddress(back, SID, name + ", the way back on romp:wsup");
      assert.deepEqual(errors, [], name + ": no page errors");
      await page.close();
    }
  });
});

test("in a browser, a remote session's svg in the chat modal: the picture fails on the relay's 502 and the re-ask meets it too; the pane carries the relay's words; with the pane's three probes spent first, so no kernel message's probe can bring the picture back, the address answers and hostUp (and in a second case romp:hostRelayUp) clears the pane and the picture decodes from the relay's address", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const way of ["hostUp", "romp:hostRelayUp"]) {
      const { page, errors, pic } = await scene(browser, "chat", { heal: true });
      pic.mode = "502";
      await page.evaluate((b: string) => { const w = window as any; w.__okAsks = 1; w.__fail = { status: 502, body: b }; }, RELAY_502);
      await openFig(page, REMOTE);
      await settled(page);
      const s = await state(page);
      assert.equal(s.pane, RELAY_502, way + ": the pane carries the relay's words");
      assert.equal(s.error, RELAY_502, way + ": error() is the pane's words");
      assert.equal(s.asks, 2, way + ": one re-ask");
      await spendProbes(page, pic, way);                  // spent first: hostUp is a kernel message too, and without its own branch a probe with budget left would bring the picture back
      assert.equal((await state(page)).asks, 2, way + ": the failed probes ran no fetch");
      assert.ok(pic.reqs.every((u) => new URL(u).pathname === "/remote/TESTHOST/file"), way + ": the picture and its probes asked the relay: " + pic.reqs.join(" | "));
      pic.mode = "ok";
      await page.evaluate((w0: string) => {
        (window as any).__fail = null;
        if (w0 === "hostUp") window.dispatchEvent(new MessageEvent("message", { data: { type: "hostUp", hosts: ["TESTHOST"] } }));
        else window.dispatchEvent(new CustomEvent("romp:hostRelayUp", { detail: { host: "TESTHOST" } }));
      }, way);
      await page.waitForFunction(() => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && img.complete && img.naturalWidth > 0; }, null, { timeout: 10000 });
      const back = await state(page);
      assert.equal(back.pane, null, way + ": the pane cleared");
      assert.equal(back.width, 200, way + ": and the picture decoded");
      assert.equal(back.asks, 3, way + ": the way back asked once");
      onAddress(back, REMOTE, way + ", the way back");
      assert.deepEqual(errors, [], way + ": no page errors");
      await page.close();
    }
  });
});

test("in a browser, the chat modal with the page's heal: the picture's own request answers 502 once and then the address answers: the re-ask lands, the picture decodes, no pane ever shows, error() stays null, and exactly one re-ask ran", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors, pic } = await scene(browser, "chat", { heal: true });
    pic.mode = "once502";
    await openFig(page);
    await page.waitForFunction(() => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && img.complete && img.naturalWidth > 0 || !!document.querySelector(".fileview-body .fileview-err"); }, null, { timeout: 10000 });
    await frames(page, 2);
    const s = await state(page);
    assert.equal(s.paneSeen, false, "no pane ever showed");
    assert.equal(s.width, 200, "the picture decoded");
    assert.equal(s.error, null, "error() null");
    assert.equal(s.asks, 2, "the open's fetch and exactly one re-ask");
    assert.equal(pic.reqs.length, 2, "two picture requests: the one that failed and the re-ask's");
    onAddress(s, SID, "the re-ask's picture");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser, the chat modal with the page's heal: an svg whose address serves bytes that do not decode ends, after one re-ask, on the pane worded for both causes (SVG_PICTURE_FAILED) with the path and Download, error() that sentence; a kernel message then probes the address off the page, three times in all, one at a time, and a probe that loads brings the picture back; a png whose bytes do not decode keeps DECODE_FAILED, with no second fetch", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors, pic } = await scene(browser, "chat", { heal: true, docs: { [REPORT]: LONG, [FIG]: SVG, [PNG]: "png" } });
    pic.mode = "bad";
    await openFig(page);
    await settled(page);
    const s = await state(page);
    assert.equal(s.pane, SVG_PICTURE_FAILED, "the pane is worded for both causes");
    assert.equal(s.hint, FIG, "with the path");
    assert.equal(s.download, true, "and Download");
    assert.equal(s.error, SVG_PICTURE_FAILED, "error() is that sentence");
    assert.equal(s.asks, 2, "one re-ask");
    assert.equal(pic.reqs.length, 2, "two picture requests");
    // the kernel's messages: one probe per message while none is out, three in all for this pane. Each pair is dispatched in one
    // evaluate, back to back in one task, so no probe can settle between its two messages and the second meets the first's probe
    // still out; the next pair waits until every probe sent has settled (the page's own count, an event, never a frame count)
    const message = async (): Promise<void> => { await page.evaluate(() => { window.dispatchEvent(new MessageEvent("message", { data: { type: "sessions", sessions: [] } })); }); };
    const pair = (): Promise<void> => page.evaluate(() => { for (let j = 0; j < 2; j++) window.dispatchEvent(new MessageEvent("message", { data: { type: "sessions", sessions: [] } })); });
    for (let i = 0; i < 5; i++) {
      const n: number = pic.reqs.length;
      await pair();                                       // the second message of the pair meets the first's probe still out and sends nothing
      for (let k = 0; k < 40 && pic.reqs.length === n && i < 3; k++) await frames(page, 1);   // the probe's request reaching the route
      await page.waitForFunction(() => (window as any).__probesSettled === (window as any).__probes, null, { timeout: 10000 });   // its answer and the probe's error event
      if (i < 3) assert.equal(pic.reqs.length, n + 1, "message pair " + (i + 1) + ": one probe");
      else assert.equal(pic.reqs.length, n, "message pair " + (i + 1) + ": the three probes are spent");
    }
    assert.equal((await state(page)).asks, 2, "a failed probe runs no fetch");
    // romp:wsup refills the budget: the way back asks again, meets the same bytes, and the next probe loads
    await page.evaluate(() => { window.dispatchEvent(new Event("romp:wsup")); });
    await page.waitForFunction(() => (window as any).__asks === 3 && !!document.querySelector(".fileview-body .fileview-err"), null, { timeout: 10000 });
    pic.mode = "ok";
    await message();
    await page.waitForFunction(() => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && img.complete && img.naturalWidth > 0; }, null, { timeout: 10000 });
    const back = await state(page);
    assert.equal(back.pane, null, "the probe loaded: the pane cleared");
    assert.equal(back.asks, 4, "the probe's load asked once");
    onAddress(back, SID, "the way back on a kernel message");
    // the png control: its picture is made from the fetched bytes, so its error is the bytes' verdict
    await page.evaluate(() => { (window as any).FV.closeFileView(); });
    await openFig(page, SID, PNG);
    await settled(page);
    const p = await state(page);
    assert.equal(p.pane, DECODE_FAILED, "a png whose bytes do not decode still shows DECODE_FAILED");
    assert.equal(p.error, DECODE_FAILED, "error() is that sentence");
    assert.ok(p.objectUrls.includes("image/png"), "the png's picture is an object URL of its bytes");
    assert.equal(await page.evaluate(() => (window as any).__pngAsks), 1, "and no second fetch: the png's one GET");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser, the Files pane with the Comments panel open over an svg picture (the page's clock installed): a reload whose bytes land while the picture's own request is held ends the panel's wait at the landing, the loader leaving with it, and 16 s later no row says the contents have not arrived; the control, a viewer fetch held past 15 s, still files that row", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const held of ["the picture", "the fetch"]) {
      const { page, errors, pic } = await scene(browser, "pane", { clock: true });
      await page.evaluate(() => { const w = window as any; w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null }); });   // no sidecar or config to watch: the poll watches the file alone
      await openFig(page);
      await settled(page);
      await openPanel(page);
      const bytesWait = (): Promise<boolean> => page.evaluate(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]'));
      const lateRow = (): Promise<boolean> => page.evaluate(() => (document.querySelector(".fileview-aside")?.textContent || "").includes("have not arrived"));
      // the file moves; the viewer's GET is held until the panel's status has armed its wait
      await page.evaluate(() => { const w = window as any; w.__gate = new Promise<void>((r) => { w.__open = r; }); });
      const open = (): Promise<void> => page.evaluate(() => { (window as any).__open(); });
      pic.mode = "hold";
      await page.evaluate((m: string) => { (window as any).__mtime = m; }, MT2);
      await page.waitForFunction(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]'), null, { timeout: 15000 });
      assert.equal(await lateRow(), false, held + ": the wait is armed, no row yet");
      if (held === "the picture") {
        await open();
        await page.waitForFunction((m: string) => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && (img.getAttribute("src") || "").endsWith("&v=" + m); }, MT2, { timeout: 10000 });
        await frames(page, 2);
        const at = await state(page);
        assert.equal(at.complete, false, held + ": the bytes landed and the picture's own request is held");
        assert.equal(await bytesWait(), false, held + ": the panel's loader left at the landing");
        await page.clock.fastForward(16000);
        await frames(page, 3);
        assert.equal(await lateRow(), false, held + ": 16 s on, no row says the contents have not arrived");
        pic.release();
        await settled(page);
        await frames(page, 2);
        assert.equal(await lateRow(), false, held + ": nor after the picture loads");
        onAddress(await state(page), SID, held + ", the reload");
      } else {
        await page.clock.fastForward(16000);
        await page.waitForFunction(() => (document.querySelector(".fileview-aside")?.textContent || "").includes("have not arrived"), null, { timeout: 10000 });
        assert.equal(await lateRow(), true, held + ": a fetch that has not landed 16 s on files the row");
        await open();
        pic.release();
      }
      assert.deepEqual(errors, [], held + ": no page errors");
      await page.close();
    }
  });
});

test("in a browser, the Files pane with the Comments panel open over an svg picture (the page's clock installed): a reload whose bytes go to the Source view ends the panel's wait at the landing, the loader leaving with it, and with their decode held, 16 s later no row says the contents have not arrived; at the decode the Source view shows the landed bytes' XML, and back to the picture it loads at the landed address; for a reload while a press of the Source toggle waits for its decode, and for a reload under the Source view", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const SVG2 = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120"><rect width="300" height="120" fill="#996633"/></svg>';
    for (const road of ["a reload while the press waits for its decode", "a reload under the Source view"]) {
      const { page, errors } = await scene(browser, "pane", { clock: true });
      await page.evaluate(() => { const w = window as any; w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null }); });   // no sidecar or config to watch: the poll watches the file alone
      await openFig(page);
      await settled(page);
      await openPanel(page);
      const bytesWait = (): Promise<boolean> => page.evaluate(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]'));
      const lateRow = (): Promise<boolean> => page.evaluate(() => (document.querySelector(".fileview-aside")?.textContent || "").includes("have not arrived"));
      const under = road === "a reload under the Source view";
      if (under) {
        await pressSource(page);
        await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs"), null, { timeout: 10000 });
      }
      await page.evaluate(() => { const w = window as any; w.__textGate = new Promise<void>((r) => { w.__textOpen = r; }); });   // every decode of the fetched bytes held from here
      if (!under) await pressSource(page);               // the Source view waits for the decode, and the picture is still up
      // the file moves to new bytes; the viewer's GET is held until the panel's status has armed its wait
      await page.evaluate(() => { const w = window as any; w.__gate = new Promise<void>((r) => { w.__open = r; }); });
      await page.evaluate(([m, f, b]: [string, string, string]) => { const w = window as any; w.__mtime = m; w.__docs[f] = b; }, [MT2, FIG, SVG2]);
      await page.waitForFunction(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]'), null, { timeout: 15000 });
      assert.equal(await lateRow(), false, road + ": the wait is armed, no row yet");
      await page.evaluate(() => { (window as any).__open(); });
      await page.waitForFunction((m: string) => (window as any).__seam.mtimeNs() === m, MT2, { timeout: 10000 });   // the reload landed
      await frames(page, 2);
      assert.equal(await page.evaluate(() => (window as any).__seam.mode()), under ? "raw" : "media", road + ": the decode is held: the view the landing found still shows");
      assert.equal(await bytesWait(), false, road + ": the panel's loader left at the landing, before the decode");
      await page.clock.fastForward(16000);
      await frames(page, 3);
      assert.equal(await lateRow(), false, road + ": 16 s on, the decode still held, no row says the contents have not arrived");
      await page.evaluate(() => { const w = window as any; w.__textGate = null; w.__textOpen(); });
      if (under) await page.waitForFunction(() => (document.querySelector(".fileview-body code.hljs")?.textContent || "").includes('width="300"'), null, { timeout: 10000 });   // the older XML stands until the landed bytes decode
      else await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs"), null, { timeout: 10000 });   // the Source view's first paint, at the decode
      await frames(page, 2);
      const xml: string = await page.evaluate(() => document.querySelector(".fileview-body code.hljs")?.textContent || "");
      assert.ok(xml.includes('width="300"'), road + ": at the decode the Source view shows the landed bytes' XML; got " + xml.slice(0, 80));
      assert.equal(await lateRow(), false, road + ": nor after the decode");
      assert.equal(await bytesWait(), false, road + ": and no loader");
      await pressSource(page);                            // back to the picture, at the landed mtime
      await settled(page);
      await frames(page, 2);
      const back = await state(page);
      onAddress(back, SID, road + ", back to the picture after a landing whose bytes went to the Source view");
      assert.ok(back.src !== null && back.src.endsWith("&v=" + MT2), road + ": at the landed mtime; got " + back.src);
      assert.equal(back.pane, null, road + ": back to the picture: no pane");
      assert.equal(back.width, 200, road + ": the picture decoded");
      assert.deepEqual(errors, [], road + ": no page errors");
      await page.close();
    }
  });
});

test("in a browser, the Files pane with the Comments panel open over an svg picture and a pending insertion in a reload's bytes (the page's clock installed): from the reload's landing to the paint of its bytes the change card keeps the tags and buttons it had before the landing, while the panel's loader leaves at the landing and 16 s later no row says the contents have not arrived; at the paint the card moves; for a reload under the Source view and a reload while a press of the Source toggle waits for its decode (the decode held, the paint at the decode), and for a reload whose picture's own request is held (the paint at the picture's load)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const INS = ' fill="#996633"';
    const SVG2 = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120"><rect width="300" height="120"' + INS + '/></svg>';
    const at = SVG2.indexOf(INS);
    const HUNK = { id: "h1", author: "api", ts: 1757145600000, kind: "ins", curFrom: at, curTo: at + INS.length, baseFrom: at, baseTo: at, oldText: "", newText: INS, anchor: null };
    type Card = { tags: string[]; buttons: string[]; reveal: string | null } | null;
    for (const road of ["a reload under the Source view", "a reload while the press waits for its decode", "a reload whose picture's own request is held"]) {
      const { page, errors, pic } = await scene(browser, "pane", { clock: true });
      await page.evaluate(() => { const w = window as any; w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null }); });   // no sidecar or config to watch: the poll watches the file alone
      await openFig(page);
      await settled(page);
      await openPanel(page);
      const bytesWait = (): Promise<boolean> => page.evaluate(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]'));
      const lateRow = (): Promise<boolean> => page.evaluate(() => (document.querySelector(".fileview-aside")?.textContent || "").includes("have not arrived"));
      const changeCard = (): Promise<Card> => page.evaluate(() => {
        const c = document.querySelector(".fileview-aside .fc-card.fc-change");
        if (!c) return null;
        const rv = c.querySelector('[data-act="fcreveal"]') as HTMLElement | null;
        return { tags: Array.from(c.querySelectorAll(".fc-card-head .fc-tag")).map((x) => x.textContent || ""), buttons: Array.from(c.querySelectorAll(".fc-actions button")).map((x) => x.textContent || ""), reveal: rv ? rv.title : null };
      });
      const under = road === "a reload under the Source view", pending = road === "a reload while the press waits for its decode";
      if (under) {
        await pressSource(page);
        await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs"), null, { timeout: 10000 });
      }
      if (under || pending) await page.evaluate(() => { const w = window as any; w.__textGate = new Promise<void>((r) => { w.__textOpen = r; }); });   // every decode of the fetched bytes held from here
      if (pending) await pressSource(page);              // the Source view waits for the decode, and the picture is still up
      if (!under && !pending) pic.mode = "hold";          // the landed picture's own request held
      // the file moves to new bytes with the insertion pending in them; the viewer's GET is held until the panel's status has armed its wait
      await page.evaluate(() => { const w = window as any; w.__gate = new Promise<void>((r) => { w.__open = r; }); });
      await page.evaluate(([m, f, b, h]: [string, string, string, unknown]) => { const w = window as any; w.__mtime = m; w.__docs[f] = b; w.__status = Object.assign({}, w.__status, { hunks: [h] }); }, [MT2, FIG, SVG2, HUNK]);
      await page.waitForFunction(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]') && !!document.querySelector(".fileview-aside .fc-card.fc-change"), null, { timeout: 15000 });
      const before = await changeCard();
      assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"], reveal: null }, road + ": the premise: the view's bytes are not the status's, so the card claims no tag, no Reveal and no Comment on this change");
      await page.evaluate(() => { (window as any).__open(); });
      await page.waitForFunction((m: string) => (window as any).__seam.mtimeNs() === m, MT2, { timeout: 10000 });   // the reload landed
      await frames(page, 2);
      if (under || pending) assert.equal(await page.evaluate(() => (window as any).__seam.mode()), under ? "raw" : "media", road + ": the decode is held: the view the landing found still shows");
      else assert.equal((await state(page)).complete, false, road + ": the bytes landed and the picture's own request is held");
      assert.equal(await bytesWait(), false, road + ": the panel's loader left at the landing");
      assert.deepEqual(await changeCard(), before, road + ": between the landing and the paint the card keeps its tags and buttons: no Reveal, no not shown tag and no Comment on this change that the paint would take back");
      await page.clock.fastForward(16000);
      await frames(page, 3);
      assert.equal(await lateRow(), false, road + ": 16 s on, the paint still held, no row says the contents have not arrived");
      assert.deepEqual(await changeCard(), before, road + ": and the card still as before the landing");
      if (under || pending) {
        await page.evaluate(() => { const w = window as any; w.__textGate = null; w.__textOpen(); });
        await page.waitForFunction(() => (document.querySelector(".fileview-body code.hljs")?.textContent || "").includes('width="300"'), null, { timeout: 10000 });   // the Source view paints the landed bytes at their decode
      } else {
        pic.release();
        await decoded(page);                              // the picture's load paints it
      }
      await frames(page, 2);
      const moved = await changeCard();
      if (under || pending) assert.deepEqual(moved, { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], reveal: null }, road + ": at the decode the Source view marks the insertion, and the card moves: Comment on this change, and no Reveal");
      else assert.deepEqual(moved, { tags: [], buttons: ["Accept", "Reject", "Reveal"], reveal: "Show the change in the Raw view" }, road + ": at the picture's load the card moves: the picture marks no change, so a Reveal");
      assert.equal(await lateRow(), false, road + ": no row after the paint");
      assert.equal(await bytesWait(), false, road + ": and no loader");
      if (!under && !pending) onAddress(await state(page), SID, road + ", the reload's picture");
      assert.deepEqual(errors, [], road + ": no page errors");
      await page.close();
    }
  });
});

for (const gc of [false, true]) {
  test("in a browser, a remote session's svg in the chat modal with the page's heal: over the re-ask's pane a kernel message's probe loads while the viewer's fetch still meets the relay's 502; over the next twelve kernel messages the probes sent from the pane on number three, the probes' budget, each later one meeting the relay's 502 or loading from the page's memory and running one fetch, one pane paint per fetch; romp:wsup refills the budget, and a probe that loads with a fetch that answers clears the pane" + (gc ? "; here with a forced garbage collection after the probe that loads, so the later probes may ask the network" : ""), { timeout: 240000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      const { page, errors, pic } = await scene(browser, "chat", { heal: true });
      pic.mode = "502";
      await page.evaluate((b: string) => { const w = window as any; w.__okAsks = 1; w.__fail = { status: 502, body: b }; }, RELAY_502);
      await openFig(page, REMOTE);
      await settled(page);
      const s = await state(page);
      assert.equal(s.pane, RELAY_502, "the re-ask's pane carries the relay's words");
      assert.equal(s.asks, 2, "the open's fetch and one re-ask");
      const probes = (): Promise<number> => page.evaluate(() => (window as any).__probes);
      assert.equal(await probes(), 0, "no probe before the first kernel message");
      // the picture's route answers once: the next message's probe loads over the network, and the fetch it runs meets the relay's 502 again
      pic.mode = "ok";
      const n0 = pic.reqs.length;
      await kernelMessage(page);
      await quiet(page, s);
      const one = await state(page);
      assert.equal(pic.reqs.length, n0 + 1, "the probe's one request, which loaded");
      assert.equal(one.asks, 3, "and ran one fetch, which met the relay's 502");
      if (gc) await forceGc(page);
      pic.mode = "502";
      // twelve kernel messages, one at a time, each given what its probe, its fetch and its pane take
      for (let i = 0; i < 12; i++) {
        await kernelMessage(page);
        await quiet(page, s);
      }
      const after = await state(page);
      const sent = await probes();
      const later = sent - 1, network = pic.reqs.length - (n0 + 1), fromMemory = after.asks - one.asks;
      t.diagnostic((gc ? "after a forced garbage collection: " : "") + "of the " + later + " later probes, " + network + " asked the network and " + fromMemory + " loaded from the page's memory");
      assert.equal(sent, 3, "three probes sent from the pane on, the probes' budget of three: the one that loaded over the network and the two the budget then left; the panes their fetches painted kept what was left, so the later messages sent none");
      assert.equal(network + fromMemory, later, "each later probe met the relay's 502 at the route or loaded from the page's memory and ran one fetch");
      assert.equal(after.paints - s.paints, after.asks - s.asks, "one pane paint per fetch");
      assert.equal(after.pane, RELAY_502, "the pane stands");
      // a reconnect-class event refills the budget: its fetch meets the relay's 502; then the address answers, and a probe that
      // loads, from the page's memory or over the network, runs a fetch that answers and clears the pane
      await page.evaluate(() => { window.dispatchEvent(new Event("romp:wsup")); });
      await quiet(page, s);
      const wsup = await state(page);
      assert.equal(wsup.asks, after.asks + 1, "romp:wsup ran the fetch once");
      assert.equal(wsup.pane, RELAY_502, "and it met the relay's 502");
      pic.mode = "ok";
      await page.evaluate(() => { (window as any).__fail = null; });
      await kernelMessage(page);
      await decoded(page);
      const back = await state(page);
      assert.equal(back.pane, null, "the probe loaded and the fetch answered: the pane cleared");
      assert.equal(back.width, 200, "and the picture decoded");
      assert.equal(back.asks, wsup.asks + 1, "the loaded probe's fetch");
      onAddress(back, REMOTE, "the way back on a kernel message after romp:wsup refilled the budget");
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
    });
  });
}

for (const sid of [REMOTE, SID]) {
  test("in a browser, " + (sid === REMOTE ? "a remote" : "a local") + " session's svg in the chat modal with the page's heal and both of render.ts's retry drivers (its retry on every kernel message and its romp:wsup line): over the re-ask's pane, the relay's 502 on the picture and on the viewer's fetch, the first three kernel messages send one probe of the picture's address each and the next three none; the markdown-image heal, which hears the picture's error, probes nothing of the viewer's picture, so the viewer's three are the page's", { timeout: 240000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      const { page, errors, pic } = await scene(browser, "chat", { heal: true });
      pic.mode = "502";
      await page.evaluate((b: string) => { const w = window as any; w.__okAsks = 1; w.__fail = { status: 502, body: b }; }, RELAY_502);
      await openFig(page, sid);
      await settled(page);
      const s = await state(page);
      assert.equal(s.pane, RELAY_502, "the premise: the re-ask's pane, in the relay's words");
      const probes = (): Promise<number> => page.evaluate(() => (window as any).__probes);
      const runs0: number = await page.evaluate(() => (window as any).__perMessage || 0);
      const per: number[] = [];
      for (let i = 0; i < 6; i++) {
        const p0 = await probes();
        await kernelMessage(page);
        await quiet(page, s);                             // every probe that message sent has settled
        per.push((await probes()) - p0);
      }
      const runs: number = await page.evaluate(() => (window as any).__perMessage || 0);
      assert.equal(runs - runs0, 6, "the chat page's per-message retry ran on each of the six kernel messages");
      assert.deepEqual(per, [1, 1, 1, 0, 0, 0], "probes per kernel message: one on each of the first three, none after, the viewer's budget alone (before: two on each of the first three, the heal's beside the viewer's)");
      assert.equal((await state(page)).asks, s.asks, "every probe met the relay's 502: no fetch ran");
      assert.deepEqual(errors, [], "no page errors");
      await page.close();
    });
  });
}

test("in a browser, the Files pane and the chat modal: the picture fails, and while the re-ask's fetch is held the person switches to the Source view; that fetch then fails, and its answer paints nothing: the Source view stands with Source pressed, mode() and error() the Source view's and no pane; back to the picture, it loads afresh from its /file address with no fetch", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as Mode[]) {
      const { page, errors, pic } = await scene(browser, mode, { heal: mode === "chat" });
      pic.mode = "502";
      await page.evaluate((b: string) => { const w = window as any; w.__okAsks = 1; w.__fail = { status: 502, body: b }; w.__gateAt = 2; w.__gate = new Promise<void>((r) => { w.__open = r; }); }, RELAY_502);
      await openFig(page);
      await page.waitForFunction(() => { const body = document.querySelector(".fileview-body"); return !!body && !!body.querySelector(".fileview-load") && !body.querySelector(".fileview-imgbox") && (window as any).__asks === 2; }, null, { timeout: 10000 });
      await pressSource(page);                            // the Source view, while the re-ask's fetch is held
      await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs"), null, { timeout: 10000 });
      await page.evaluate(() => { (window as any).__open(); });
      await page.waitForFunction(() => (window as any).__released, null, { timeout: 10000 });
      await frames(page, 6);                              // the 502's body read, the fetch chain's catch and its landing
      const src = await page.evaluate(() => {
        const w = window as any;
        const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Source") as HTMLElement;
        return { code: !!document.querySelector(".fileview-body code.hljs"), pane: !!document.querySelector(".fileview-body .fileview-err"), pressed: b.getAttribute("aria-pressed"), mode: w.__seam.mode(), error: w.__seam.error(), asks: w.__asks };
      });
      assert.deepEqual(src, { code: true, pane: false, pressed: "true", mode: "raw", error: null, asks: 2 }, mode + ": the re-ask's failure painted nothing: the Source view stands (" + JSON.stringify(src) + ")");
      // back to the picture: a fresh load at its /file address, which now answers
      pic.mode = "ok";
      await page.evaluate(() => { (window as any).__fail = null; });
      await pressSource(page);
      await settled(page);
      await frames(page, 2);
      const back = await state(page);
      assert.equal(back.pane, null, mode + ": back to the picture: no pane");
      assert.equal(back.width, 200, mode + ": the picture decoded");
      assert.equal(back.error, null, mode + ": error() null");
      assert.equal(back.asks, 2, mode + ": with no fetch: the picture's own load");
      onAddress(back, SID, mode + ", the Source view and back after the dropped answer");
      assert.deepEqual(errors, [], mode + ": no page errors");
      await page.close();
    }
  });
});

for (const way of ["romp:wsup", "hostUp", "romp:hostRelayUp"]) {
  test("in a browser, a remote session's svg in the chat modal with the page's heal: " + way + ", arriving while the re-ask's fetch is out, runs nothing then; that fetch meets the relay's 502 and paints its pane, and then runs once more at once, with no kernel message, so the picture comes back from the relay's address", { timeout: 240000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      const { page, errors, pic } = await scene(browser, "chat", { heal: true });
      pic.mode = "502";
      // the re-ask's fetch (the second GET) is held and then meets the relay's 502; the GETs after it answer
      await page.evaluate((b: string) => { const w = window as any; w.__okAsks = 1; w.__failTo = 2; w.__fail = { status: 502, body: b }; w.__gateAt = 2; w.__gate = new Promise<void>((r) => { w.__open = r; }); }, RELAY_502);
      await openFig(page, REMOTE);
      await page.waitForFunction(() => { const body = document.querySelector(".fileview-body"); return !!body && !!body.querySelector(".fileview-load") && !body.querySelector(".fileview-imgbox") && (window as any).__asks === 2; }, null, { timeout: 10000 });
      await reconnect(page, way);
      await frames(page, 2);
      assert.equal((await state(page)).asks, 2, way + ": nothing more runs while the re-ask's fetch is out");
      pic.mode = "ok";                                     // the address answers from here on
      const panes: number = await page.evaluate(() => (window as any).__panes);
      await page.evaluate(() => { (window as any).__open(); });
      await page.waitForFunction((n: number) => (window as any).__panes > n, panes, { timeout: 10000 });   // the held fetch's pane
      const at: { asks: number; error: string | null } = await page.evaluate((n: number) => (window as any).__paneLog[n], panes);   // as its paint left things
      assert.equal(at.error, RELAY_502, way + ": the held fetch met the relay's 502 and its pane carries the relay's words");
      assert.equal(at.asks, 3, way + ": the event heard while that fetch was out runs it once more at once, with no kernel message");
      await decoded(page);
      const back = await state(page);
      assert.equal(back.pane, null, way + ": the pane cleared");
      assert.equal(back.width, 200, way + ": and the picture decoded");
      assert.equal(back.error, null, way + ": error() null over the picture");
      assert.equal(back.asks, 3, way + ": one fetch more in all");
      onAddress(back, REMOTE, way + ", the fetch run once more after the event heard while the re-ask's fetch was out");
      assert.deepEqual(errors, [], way + ": no page errors");
      await page.close();
    });
  });
}

for (const [first, second] of [["hostUp", "romp:hostRelayUp"], ["romp:wsup", "romp:wsup"]]) {
  const name = first + " then " + second;
  test("in a browser, a remote session's svg in the chat modal with the page's heal, " + name + ": over the re-ask's pane the first event runs the fetch again, and the second arrives while that fetch is out and runs nothing then; the fetch meets the relay's 502 and paints its pane, and then runs once more at once, with no kernel message, so the picture comes back from the relay's address", { timeout: 240000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      const { page, errors, pic } = await scene(browser, "chat", { heal: true });
      pic.mode = "502";
      // the re-ask's fetch and the first event's meet the relay's 502; the GETs after them answer
      await page.evaluate((b: string) => { const w = window as any; w.__okAsks = 1; w.__failTo = 3; w.__fail = { status: 502, body: b }; }, RELAY_502);
      await openFig(page, REMOTE);
      await settled(page);
      const s = await state(page);
      assert.equal(s.pane, RELAY_502, name + ": the re-ask's pane in the relay's words");
      assert.equal(s.asks, 2, name + ": one re-ask");
      await page.evaluate(() => { const w = window as any; w.__gateAt = 3; w.__gate = new Promise<void>((r) => { w.__open = r; }); });
      await reconnect(page, first);
      await page.waitForFunction(() => (window as any).__asks === 3, null, { timeout: 10000 });   // the first event's fetch, held
      await reconnect(page, second);
      await frames(page, 2);
      assert.equal((await state(page)).asks, 3, name + ": the second event runs nothing while the first one's fetch is out");
      pic.mode = "ok";
      const panes: number = await page.evaluate(() => (window as any).__panes);
      await page.evaluate(() => { (window as any).__open(); });
      await page.waitForFunction((n: number) => (window as any).__panes > n, panes, { timeout: 10000 });
      const at: { asks: number; error: string | null } = await page.evaluate((n: number) => (window as any).__paneLog[n], panes);   // as its paint left things
      assert.equal(at.error, RELAY_502, name + ": the held fetch met the relay's 502 and its pane carries the relay's words");
      assert.equal(at.asks, 4, name + ": the second event, heard while that fetch was out, runs it once more at once, with no kernel message");
      await decoded(page);
      const back = await state(page);
      assert.equal(back.pane, null, name + ": the pane cleared");
      assert.equal(back.width, 200, name + ": and the picture decoded");
      assert.equal(back.error, null, name + ": error() null over the picture");
      onAddress(back, REMOTE, name + ", the fetch run once more after the second event");
      assert.deepEqual(errors, [], name + ": no page errors");
      await page.close();
    });
  });
}

for (const mode of ["pane", "chat"] as Mode[]) {
  test("in a browser, the " + (mode === "pane" ? "Files pane" : "chat modal with the page's heal") + ": the Source toggle is pressed while its bytes still decode (the decode held), and then the picture's own request fails; that failure starts nothing, so no re-ask runs, and the Source view paints at the decode and stands with Source pressed, mode() and error() the Source view's and no pane; back to the picture, it loads afresh from its /file address with no fetch", { timeout: 240000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      const { page, errors, pic } = await scene(browser, mode, { heal: mode === "chat" });
      pic.mode = "hold502";                                 // the picture's own request, held, then the relay's 502
      // any re-ask's fetch (the second GET) is held until the Source view has painted, and then meets the relay's 502
      await page.evaluate((b: string) => { const w = window as any; w.__okAsks = 1; w.__fail = { status: 502, body: b }; w.__gateAt = 2; w.__gate = new Promise<void>((r) => { w.__open = r; }); }, RELAY_502);
      await openFig(page);
      await page.waitForFunction(() => !!document.querySelector(".fileview-body .fileview-imgbox .fileview-load"), null, { timeout: 10000 });
      await page.evaluate(() => { const w = window as any; w.__textGate = new Promise<void>((r) => { w.__textOpen = r; }); });
      await pressSource(page);                            // the Source view waits for the decode, and the picture is still up
      pic.release();                                      // the picture's own request fails now
      await page.waitForFunction(() => (window as any).__picErrs >= 1, null, { timeout: 10000 });
      await page.evaluate(() => { (window as any).__textOpen(); });
      await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs"), null, { timeout: 10000 });
      await page.evaluate(() => { (window as any).__open(); });   // a held re-ask, if one ran, goes on and meets the relay's 502
      await frames(page, 6);
      const src = await page.evaluate(() => {
        const w = window as any;
        const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Source") as HTMLElement;
        return { code: !!document.querySelector(".fileview-body code.hljs"), pane: !!document.querySelector(".fileview-body .fileview-err"), pressed: b.getAttribute("aria-pressed"), mode: w.__seam.mode(), error: w.__seam.error(), asks: w.__asks };
      });
      assert.deepEqual(src, { code: true, pane: false, pressed: "true", mode: "raw", error: null, asks: 1 }, mode + ": the picture's failure after the press started nothing: no re-ask, and the Source view stands (" + JSON.stringify(src) + ")");
      // back to the picture: a fresh load at its /file address, which now answers
      pic.mode = "ok";
      await page.evaluate(() => { (window as any).__fail = null; });
      await pressSource(page);
      await settled(page);
      await frames(page, 2);
      const back = await state(page);
      assert.equal(back.pane, null, mode + ": back to the picture: no pane");
      assert.equal(back.width, 200, mode + ": the picture decoded");
      assert.equal(back.error, null, mode + ": error() null");
      assert.equal(back.asks, 1, mode + ": with no fetch: the picture's own load");
      onAddress(back, SID, mode + ", the Source view and back after the failure the press made moot");
      assert.deepEqual(errors, [], mode + ": no page errors");
      await page.close();
    });
  });
}

for (const mode of ["pane", "chat"] as Mode[]) {
  for (const way of ["romp:wsup", "hostUp", "romp:hostRelayUp"]) {
    const where = mode === "pane" ? "the Files pane, a local session whose picture meets a refused connection" : "the chat modal with the page's heal, a remote session whose picture meets the relay's 502";
    test("in a browser, " + where + ": the re-ask's fetch lands and its picture's own request is held; " + way + " arrives while that picture loads and runs nothing then; the request then fails, and the picture's failure asks the address once more at once, in place of the pane, so with no kernel message the picture comes back from its /file address and no pane ever shows", { timeout: 240000 }, async (t) => {
      await inBrowser(t, async (browser) => {
        const remote = mode === "chat";
        const sid = remote ? REMOTE : SID;
        const { page, errors, pic } = await scene(browser, mode, { heal: remote });
        // the first picture fails; the re-ask's picture is held and then fails the same way; every request after answers
        pic.seq = remote ? ["502", "hold502"] : ["refuse", "holdRefuse"];
        await openFig(page, sid);
        await page.waitForFunction(() => !!document.querySelector(".fileview-body .fileview-imgbox .fileview-load") && (window as any).__asks === 2, null, { timeout: 10000 });
        for (let k = 0; k < 40 && pic.reqs.length < 2; k++) await frames(page, 1);   // the re-ask's picture's request, held at the route
        assert.equal(pic.reqs.length, 2, way + ": the first picture's request and the re-ask's picture's, held");
        await reconnect(page, way);
        await frames(page, 2);
        assert.equal((await state(page)).asks, 2, way + ": nothing runs while the re-ask's picture loads");
        pic.release();                                     // that picture's request fails now, and the address answers from here on
        await settled(page);                               // the picture again, or a pane
        await frames(page, 2);
        const back = await state(page);
        t.diagnostic(way + " (" + mode + "): " + JSON.stringify({ asks: back.asks, paneSeen: back.paneSeen, picErrs: await page.evaluate(() => (window as any).__picErrs) }));
        assert.equal(back.paneSeen, false, way + ": no pane ever showed: the picture's failure after the event asked again in place of the pane");
        assert.equal(back.asks, 3, way + ": the event heard while the re-ask's picture loaded asks the address once more at once, with no kernel message");
        assert.equal(back.width, 200, way + ": and the picture decoded");
        assert.equal(back.error, null, way + ": error() null over the picture");
        onAddress(back, sid, way + ", the ask after the picture that failed once the event was heard");
        assert.deepEqual(errors, [], way + ": no page errors");
        await page.close();
      });
    });
  }
}

test("in a browser, a remote session's svg in the chat modal with the page's heal: over the re-ask's pane hostUp runs the fetch again, which lands, and its picture's own request is held; romp:hostRelayUp arrives while that picture loads and runs nothing then; the request meets the relay's 502, and the picture's failure asks the address once more at once, in place of the pane, so the picture comes back from the relay's address with no kernel message", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors, pic } = await scene(browser, "chat", { heal: true });
    pic.seq = ["502", "hold502"];                          // the first picture fails; the way back's picture is held, then fails
    await page.evaluate((b: string) => { const w = window as any; w.__okAsks = 1; w.__failTo = 2; w.__fail = { status: 502, body: b }; }, RELAY_502);   // the re-ask's fetch meets the relay's 502
    await openFig(page, REMOTE);
    await settled(page);
    const s = await state(page);
    assert.equal(s.pane, RELAY_502, "the re-ask's pane in the relay's words");
    assert.equal(s.asks, 2, "one re-ask");
    const panes: number = await page.evaluate(() => (window as any).__panes);
    await reconnect(page, "hostUp");                       // the way back's fetch, which lands
    for (let k = 0; k < 40 && pic.reqs.length < 2; k++) await frames(page, 1);   // its picture's request, held at the route
    assert.equal(pic.reqs.length, 2, "the way back's picture's request, held");
    assert.equal((await state(page)).asks, 3, "hostUp ran the fetch again");
    await reconnect(page, "romp:hostRelayUp");
    await frames(page, 2);
    assert.equal((await state(page)).asks, 3, "romp:hostRelayUp runs nothing while that picture loads");
    pic.release();
    await settled(page);                                   // the picture again, or a pane
    await frames(page, 2);
    const back = await state(page);
    assert.equal(await page.evaluate(() => (window as any).__panes), panes, "no pane after the re-ask's: the picture's failure after the event asked again in place of the pane");
    assert.equal(back.asks, 4, "romp:hostRelayUp, heard while the way back's picture loaded, asks the address once more at once, with no kernel message");
    assert.equal(back.width, 200, "and the picture decoded");
    assert.equal(back.error, null, "error() null over the picture");
    onAddress(back, REMOTE, "the ask after the way back's picture that failed once the event was heard");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

for (const mode of ["pane", "chat"] as Mode[]) {
  test("in a browser, the " + (mode === "pane" ? "Files pane" : "chat modal with the page's heal") + ": the Source toggle is pressed while its bytes still decode (the decode held), and a reload lands in that window; at the decode the Source view paints and stands with Source pressed, mode() and error() the Source view's, no pane and no fetch but the reload's; back to the picture, it loads from its /file address at the landed mtime", { timeout: 240000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      const { page, errors, pic } = await scene(browser, mode, { heal: mode === "chat" });
      await openFig(page);
      await decoded(page);
      // a picture the reload's landing paints, if any, is held and then meets the relay's 502; a re-ask's fetch, if one runs
      // (the third GET), is held until the Source view has painted, and then meets the relay's 502
      pic.mode = "hold502";
      await page.evaluate((b: string) => { const w = window as any; w.__okAsks = 2; w.__fail = { status: 502, body: b }; w.__gateAt = 3; w.__gate = new Promise<void>((r) => { w.__open = r; }); }, RELAY_502);
      await page.evaluate(() => { const w = window as any; w.__textGate = new Promise<void>((r) => { w.__textOpen = r; }); });
      await pressSource(page);                            // the Source view waits for the decode, and the picture is still up
      await page.evaluate((m: string) => { const w = window as any; w.__mtime = m; w.__seam.reload(); }, MT2);
      await page.waitForFunction((m: string) => (window as any).__seam.mtimeNs() === m, MT2, { timeout: 10000 });   // the reload landed
      const painted: boolean = await page.evaluate((m: string) => { const img = document.querySelector(".fileview-body img.fileview-img"); return !!img && (img.getAttribute("src") || "").endsWith("&v=" + m); }, MT2);
      t.diagnostic(mode + ": the reload's landing painted a picture over the press: " + painted);
      if (painted) {                                      // a picture the landing painted over the press: its own request fails now, so the outcome below is read after it
        pic.release();
        await page.waitForFunction(() => (window as any).__picErrs >= 1, null, { timeout: 10000 });
      }
      await page.evaluate(() => { (window as any).__textOpen(); });
      await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs"), null, { timeout: 10000 });
      await page.evaluate(() => { (window as any).__open(); });   // a held re-ask, if one ran, goes on and meets the relay's 502
      await frames(page, 6);
      const src = await page.evaluate(() => {
        const w = window as any;
        const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Source") as HTMLElement;
        return { code: !!document.querySelector(".fileview-body code.hljs"), pane: !!document.querySelector(".fileview-body .fileview-err"), pressed: b.getAttribute("aria-pressed"), mode: w.__seam.mode(), error: w.__seam.error(), asks: w.__asks };
      });
      assert.deepEqual(src, { code: true, pane: false, pressed: "true", mode: "raw", error: null, asks: 2 }, mode + ": a reload landing while the press waits for its decode leaves the Source view standing, with no pane and no fetch but the reload's (" + JSON.stringify(src) + ")");
      // back to the picture, at the landed mtime, which answers
      pic.mode = "ok";
      pic.release();
      await page.evaluate(() => { (window as any).__fail = null; });
      await pressSource(page);
      await settled(page);
      await frames(page, 2);
      const back = await state(page);
      assert.equal(back.pane, null, mode + ": back to the picture: no pane");
      assert.equal(back.width, 200, mode + ": the picture decoded");
      assert.equal(back.error, null, mode + ": error() null");
      assert.equal(back.asks, 2, mode + ": with no fetch but the reload's");
      assert.ok(back.src !== null && back.src.endsWith("&v=" + MT2), mode + ": at the landed mtime; got " + back.src);
      onAddress(back, SID, mode + ", the Source view and back after a reload that landed while the press waited for its decode");
      assert.deepEqual(errors, [], mode + ": no page errors");
      await page.close();
    });
  });
}

for (const mode of ["pane", "chat"] as Mode[]) {
  for (const way of ["romp:wsup", "hostUp", "romp:hostRelayUp"]) {
    const where = mode === "pane" ? "the Files pane, a local session whose picture meets a refused connection" : "the chat modal with the page's heal, a remote session whose picture meets the relay's 502";
    test("in a browser, " + where + ": the picture the re-ask landed fails to SVG_PICTURE_FAILED, and the person switches to the Source view and back; " + way + " arrives while the returning picture's own request is out and runs nothing then; that request fails, and the picture, a first showing since the press, asks the address again once, so with no kernel message it comes back from its /file address; the same when " + way + " arrived before the press, while the re-ask's picture was loading, and the returning picture joins that request", { timeout: 240000 }, async (t) => {
      await inBrowser(t, async (browser) => {
        const remote = mode === "chat";
        const sid = remote ? REMOTE : SID;
        const fail: PicMode = remote ? "502" : "refuse";
        const holdFail: PicMode = remote ? "hold502" : "holdRefuse";
        for (const order of ["after the press", "before the press"]) {
          const label = way + ", " + order;
          const after = order === "after the press";
          const { page, errors, pic } = await scene(browser, mode, { heal: remote });
          pic.seq = after ? [fail, fail] : [fail, holdFail];   // the first picture fails, then the re-ask's picture (held until the release, when the event comes before the press)
          pic.mode = holdFail;                             // every later request is held, then fails the same way at the release
          await openFig(page, sid);
          if (after) {
            await settled(page);
            const s = await state(page);
            assert.equal(s.pane, SVG_PICTURE_FAILED, label + ": the re-ask's picture failed too: SVG_PICTURE_FAILED");
            assert.equal(s.asks, 2, label + ": one re-ask");
          } else {
            await page.waitForFunction(() => (window as any).__asks === 2, null, { timeout: 10000 });
            for (let k = 0; k < 40 && pic.reqs.length < 2; k++) await frames(page, 1);   // the re-ask's picture's request, held at the route
            assert.equal(pic.reqs.length, 2, label + ": the first picture's request and the re-ask's picture's, held");
            await reconnect(page, way);
            await frames(page, 2);
            assert.equal((await state(page)).asks, 2, label + ": nothing runs while the re-ask's picture loads");
          }
          const panes: number = await page.evaluate(() => (window as any).__panes);
          await pressSource(page);
          await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs"), null, { timeout: 10000 });
          const n = pic.reqs.length;
          await pressSource(page);                         // back to the picture
          if (after) {
            for (let k = 0; k < 40 && pic.reqs.length === n; k++) await frames(page, 1);   // the returning picture's own request, held at the route
            assert.equal(pic.reqs.length, n + 1, label + ": the returning picture's own request, held");
            await reconnect(page, way);
          }
          await frames(page, 2);
          assert.equal((await state(page)).asks, 2, label + ": nothing runs while the returning picture loads");
          pic.mode = "ok";                                 // the address answers from here on
          pic.release();                                   // the held request fails now
          await settled(page);                             // the picture again, or a pane
          await frames(page, 2);
          const back = await state(page);
          const panesNow: number = await page.evaluate(() => (window as any).__panes);
          t.diagnostic(label + " (" + mode + "): " + JSON.stringify({ asks: back.asks, pictureRequests: pic.reqs.length, panes: panesNow - panes }));
          assert.equal(panesNow, panes, label + ": no pane after the press: the returning picture's failure asked the address again in place of the pane");
          assert.equal(back.asks, 3, label + ": the returning picture, a first showing since the press, asks the address again once, with no kernel message");
          assert.equal(back.width, 200, label + ": and the picture decoded");
          assert.equal(back.error, null, label + ": error() null over the picture");
          onAddress(back, sid, label + ", the ask after the returning picture failed");
          assert.deepEqual(errors, [], label + ": no page errors");
          await page.close();
        }
      });
    });
  }
}
