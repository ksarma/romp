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
// landing until that paint (the deadline is faked with the page's clock, so no case waits 15 s). With the panel open the change
// card is also read along these roads of the card-state rule the Comments panel follows (file-comments.ts, #cardState's doc): a
// press of the Source toggle over a picture still loading, and a press to the picture and back while a reload under the Source
// view decodes; before the view's first paint, and a first open whose fetch fails; a landed svg whose re-ask fails, up to the
// way back's picture; a failed reload of the bytes the Source view shows, with the panel closed and opened or first opened over
// its pane, and Show changes inline flipped over it; a reload landing under the Source view with its decode held, a second
// reload's pane, and a render and two flips while a press waits for its picture; a png reload whose bytes do not decode; and a
// png's landing followed by a status, for its bytes or for the painted bytes whose sidecar moved. A click on the card's link or
// its Comment on this change over a pane answers in a row under the card and does nothing else (notInView). The
// chat modal's cases that count probes run with the page's markdown-image heal installed (preview.ts installMdImgHeal, which
// also hears the picture's error and skips the viewer's picture) and both of render.ts's retry drivers, its romp:wsup line and
// its retry on every kernel message, so the probes' count of three is measured in the chat page as it runs (the loader's case installs neither). After every road the picture's src is its /file address (the relay's for a remote session) and no object
// URL is made for the svg. Waits are for the page's own events or the picture's settling, never a timer. Skips LOUDLY without
// a playwright browser (CI installs none). Synthetic values only: /repo/notes-api paths, the placeholder sid, host TESTHOST.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, closePanel, frames, ROOT, REPORT, LONG, SID, MT, MT2, type Mode } from "./real-viewer-leg";

const FIG = ROOT + "/figs/a.svg";
const PNG = ROOT + "/figs/b.png";
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="120"><rect width="200" height="120" fill="#336699"/></svg>';
const BAD_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="120"><rect width="200"';   // cut short: does not decode
const RELAY_502 = "tunnel to TESTHOST is not answering; re-dialing";
const SVG_PICTURE_FAILED = "this image failed to load or decode: the connection may have dropped, or the file may be mid-write or truncated";
const DECODE_FAILED = "this image failed to decode: it may be mid-write or truncated";
const REMOTE = "TESTHOST:" + SID;
/** The picture's /file address for a session as a page with no page key builds it, with no cap (this leg's page holds no key):
 *  the local route, or the relay's with the bare sid; the version key follows the sid. The relay route and the version key's
 *  place in the address are pinned by this leg's no-key address check, not by tests/test_svg_picture_caps_served.py, which is
 *  the witness only for what it checks: the capped /file address and the load, on the viewer's and the preview's local roads.
 *  Its cap and version key checks do not depend on order, and this leg's page makes no cap, so neither checks that a signed-in
 *  page puts the cap before the version key. */
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
 *  once each has run its listeners; `__textGate`, a promise, holds a decode of the fetched bytes (the Source view's). The png's
 *  GETs answer `__pngBytes` when a case sets it (a picture that decodes), else bytes that do not decode, each at `__mtime`;
 *  `__pngGate`, a promise, holds the next of them.
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
      w.__probes = 0; w.__probesSettled = 0; w.__srcSet = null; w.__picErrs = 0; w.__textGate = null; w.__pngBytes = null; w.__pngGate = null;
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
        if (p === png && get) { w.__pngAsks++; if (w.__pngGate) { const g = w.__pngGate; w.__pngGate = null; await g; } }
        if (p === png) return new Response(get ? new Uint8Array(w.__pngBytes || [0x89, 0x50, 0x4e, 0x47, 0x02]) : null, { status: 200, headers: { "Content-Type": "image/png", "X-Romp-Mtime-Ns": w.__mtime } });   // a png whose bytes do not decode, unless a case set __pngBytes
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
/** The property after a road: the picture's src is its /file address, as a page with no page key builds it (address), and no
 *  object URL was made for the svg. The relay route and the absence of an object URL are pinned here, by this leg's no-key
 *  checks, and not by tests/test_svg_picture_caps_served.py: it makes no relay request and does not watch for an object URL
 *  being made, and it is the witness only for the capped /file address and the load, on the viewer's and the preview's local
 *  roads under the page key. */
function onAddress(s: State, sid: string, road: string): void {
  assert.ok(s.src !== null && s.src.startsWith(address(sid)), road + ": the svg's picture is its /file address as a page with no page key builds it, not an object URL (this leg's no-key check; tests/test_svg_picture_caps_served.py checks only the capped /file address and the load, on the local roads); got " + s.src);
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
      assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"], reveal: null }, road + ": the premise: the card claims no tag, no Reveal and no Comment on this change (file-comments.ts, #cardState's doc)");
      await page.evaluate(() => { (window as any).__open(); });
      await page.waitForFunction((m: string) => (window as any).__seam.mtimeNs() === m, MT2, { timeout: 10000 });   // the reload landed
      await frames(page, 2);
      if (under || pending) assert.equal(await page.evaluate(() => (window as any).__seam.mode()), under ? "raw" : "media", road + ": the decode is held: the view the landing found still shows");
      else assert.equal((await state(page)).complete, false, road + ": the bytes landed and the picture's own request is held");
      assert.equal(await bytesWait(), false, road + ": the panel's loader left at the landing");
      assert.deepEqual(await changeCard(), before, road + ": between the landing and the paint the card keeps its tags and buttons (file-comments.ts, #cardState's doc)");
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

test("in a browser, a picture still loading when the Source toggle is pressed runs no paint hooks at its load: in the Files pane with the Comments panel open and a pending insertion in a reload that lands while the press waits for its decode, the change card keeps its state through that picture's load and moves once, at the decode; with no landing, the load paints nothing and the decode paints once; pressed to the Source view and back while the picture still loads, the picture shown on the way back paints once when it loads; with no press, the load paints once", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const INS = ' fill="#996633"';
    const SVG2 = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120"><rect width="300" height="120"' + INS + '/></svg>';
    const at = SVG2.indexOf(INS);
    const HUNK = { id: "h1", author: "api", ts: 1757145600000, kind: "ins", curFrom: at, curTo: at + INS.length, baseFrom: at, baseTo: at, oldText: "", newText: INS, anchor: null };
    const MT_A = "1757145600000000005";
    type Card = { tags: string[]; buttons: string[] } | null;
    /** The seam's paints proper since the open (the probe's onRendered count less its reflows). */
    const paints = (page: any): Promise<number> => page.evaluate(() => { const w = window as any; return w.__paints - w.__reflows; });
    const complete = (page: any): Promise<boolean> => page.evaluate(() => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && img.complete && img.naturalWidth > 0; });
    const holdDecode = (page: any): Promise<void> => page.evaluate(() => { const w = window as any; w.__textGate = new Promise<void>((r) => { w.__textOpen = r; }); });
    const openDecode = (page: any): Promise<void> => page.evaluate(() => { const w = window as any; w.__textGate = null; w.__textOpen(); });
    {
      const road = "(i) a reload lands while the press waits for its decode";
      const { page, errors, pic } = await scene(browser, "pane", { clock: true });
      await page.evaluate(() => { const w = window as any; w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null }); });   // no sidecar or config to watch: the poll watches the file alone
      await openFig(page);
      await settled(page);
      await openPanel(page);
      const changeCard = (): Promise<Card> => page.evaluate(() => {
        const c = document.querySelector(".fileview-aside .fc-card.fc-change");
        return c ? { tags: Array.from(c.querySelectorAll(".fc-card-head .fc-tag")).map((x) => x.textContent || ""), buttons: Array.from(c.querySelectorAll(".fc-actions button")).map((x) => x.textContent || "") } : null;
      });
      // a first reload whose picture's own request is held: its bytes land, and the picture is still loading when the person presses
      await page.evaluate(() => { const w = window as any; w.__gate = new Promise<void>((r) => { w.__open = r; }); });
      pic.mode = "hold";
      await page.evaluate((m: string) => { (window as any).__mtime = m; }, MT_A);
      await page.waitForFunction(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]'), null, { timeout: 15000 });
      await page.evaluate(() => { (window as any).__open(); });
      await page.waitForFunction((m: string) => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && (img.getAttribute("src") || "").endsWith("&v=" + m); }, MT_A, { timeout: 10000 });
      await frames(page, 2);
      assert.equal(await complete(page), false, road + ": the first reload's picture is still loading");
      await holdDecode(page);
      await pressSource(page);                            // the Source view waits for the decode, and the loading picture stays up
      // the file moves again, with the insertion pending in the new bytes; the viewer's GET is held until the panel's wait is armed
      await page.evaluate(() => { const w = window as any; w.__gate = new Promise<void>((r) => { w.__open = r; }); });
      await page.evaluate(([m, f, b, h]: [string, string, string, unknown]) => { const w = window as any; w.__mtime = m; w.__docs[f] = b; w.__status = Object.assign({}, w.__status, { hunks: [h] }); }, [MT2, FIG, SVG2, HUNK]);
      await page.waitForFunction(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]') && !!document.querySelector(".fileview-aside .fc-card.fc-change"), null, { timeout: 15000 });
      const before = await changeCard();
      assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"] }, road + ": the premise: the card claims no tag, no Reveal and no Comment on this change (file-comments.ts, #cardState's doc)");
      await page.evaluate(() => { (window as any).__open(); });
      await page.waitForFunction((m: string) => (window as any).__seam.mtimeNs() === m, MT2, { timeout: 10000 });   // the reload landed
      await frames(page, 2);
      assert.equal(await page.evaluate(() => (window as any).__seam.mode()), "media", road + ": the decode is held: the picture the press was made over still shows");
      assert.deepEqual(await changeCard(), before, road + ": at the landing the card keeps its state");
      const p0 = await paints(page);
      pic.release();                                      // the pressed-over picture's own request ends
      await page.waitForFunction(() => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && img.complete; }, null, { timeout: 10000 });
      await frames(page, 3);
      assert.equal(await complete(page), true, road + ": the picture painted before the press has loaded, still in the body");
      assert.deepEqual(await changeCard(), before, road + ": through its load the card keeps its state, with no Reveal (file-comments.ts, #cardState's doc)");
      assert.equal(await paints(page), p0, road + ": its load runs no paint hook");
      await openDecode(page);
      await page.waitForFunction(() => (document.querySelector(".fileview-body code.hljs")?.textContent || "").includes('width="300"'), null, { timeout: 10000 });   // the Source view paints the landed bytes at their decode
      await frames(page, 2);
      assert.equal(await paints(page), p0 + 1, road + ": the decode's paint, the one the hooks hear");
      assert.deepEqual(await changeCard(), { tags: [], buttons: ["Accept", "Reject", "Comment on this change"] }, road + ": at the decode the Source view marks the insertion, and the card moves, once");
      assert.deepEqual(errors, [], road + ": no page errors");
      await page.close();
    }
    {
      const road = "(ii) no landing";
      const { page, errors, pic } = await scene(browser, "pane");
      pic.mode = "hold";                                  // the open's picture held
      await openFig(page);
      await page.waitForFunction(() => !!document.querySelector(".fileview-body img.fileview-img"), null, { timeout: 10000 });
      await frames(page, 2);
      assert.equal(await complete(page), false, road + ": the open's picture is still loading");
      await holdDecode(page);
      await pressSource(page);
      pic.release();
      await page.waitForFunction(() => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && img.complete; }, null, { timeout: 10000 });
      await frames(page, 3);
      assert.equal(await complete(page), true, road + ": the picture pressed over has loaded, still in the body");
      assert.equal(await paints(page), 0, road + ": its load runs no paint hook");
      await openDecode(page);
      await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs"), null, { timeout: 10000 });
      await frames(page, 2);
      assert.equal(await paints(page), 1, road + ": the decode's paint runs onRendered once");
      assert.deepEqual(errors, [], road + ": no page errors");
      await page.close();
    }
    {
      const road = "(iii) to the Source view and back while the picture still loads";
      const { page, errors, pic } = await scene(browser, "pane");
      pic.mode = "hold";
      await openFig(page);
      await page.waitForFunction(() => !!document.querySelector(".fileview-body img.fileview-img"), null, { timeout: 10000 });
      await page.evaluate(() => { (window as any).__pressedOver = document.querySelector(".fileview-body img.fileview-img"); });
      await pressSource(page);
      await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs"), null, { timeout: 10000 });
      await frames(page, 2);
      assert.equal(await paints(page), 1, road + ": the Source view painted at the decode");
      await pressSource(page);                            // back to the picture: a new picture at the same address, its request still held
      const back = await state(page);
      assert.equal(back.complete, false, road + ": the picture shown on the way back is still loading");
      assert.equal(await page.evaluate(() => document.querySelector(".fileview-body img.fileview-img") !== (window as any).__pressedOver), true, road + ": the way back paints a new picture");
      pic.release();
      await decoded(page);
      await frames(page, 3);
      assert.equal(await paints(page), 2, road + ": that picture paints once when it loads, never zero times and never twice");
      onAddress(await state(page), SID, road);
      assert.deepEqual(errors, [], road + ": no page errors");
      await page.close();
    }
    {
      const road = "(iv) no press";
      const { page, errors } = await scene(browser, "pane");
      await openFig(page);
      await settled(page);
      await frames(page, 3);
      assert.equal(await paints(page), 1, road + ": the picture's load paints once");
      onAddress(await state(page), SID, road);
      assert.deepEqual(errors, [], road + ": no page errors");
      await page.close();
    }
  });
});

test("in a browser, the Files pane with the Comments panel open over an svg picture whose first paint has not come (the page's clock installed): with the open's picture held, a press of the Source toggle and a reload bringing a pending insertion, the change card reads Accept and Reject alone until the view shows the new bytes, through the reload's landing and the pressed-over picture's load, and moves once, at the decode, for a local and a remote session; and with the panel's status in before the open's bytes land, no card moves at the landing and the card takes its Reveal at the picture's paint", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const INS = ' fill="#996633"';
    const SVG2 = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120"><rect width="300" height="120"' + INS + '/></svg>';
    const at = SVG2.indexOf(INS);
    const HUNK = { id: "h1", author: "api", ts: 1757145600000, kind: "ins", curFrom: at, curTo: at + INS.length, baseFrom: at, baseTo: at, oldText: "", newText: INS, anchor: null };
    type Card = { tags: string[]; buttons: string[] } | null;
    const cardOf = (page: any): Promise<Card> => page.evaluate(() => {
      const c = document.querySelector(".fileview-aside .fc-card.fc-change");
      return c ? { tags: Array.from(c.querySelectorAll(".fc-card-head .fc-tag")).map((x) => x.textContent || ""), buttons: Array.from(c.querySelectorAll(".fc-actions button")).map((x) => x.textContent || "") } : null;
    });
    for (const sid of [SID, REMOTE]) {
      const road = "the open's picture held, a press, a reload with an insertion, " + (sid === REMOTE ? "a remote" : "a local") + " session";
      const { page, errors, pic } = await scene(browser, "pane", { clock: true });
      await page.evaluate(() => { const w = window as any; w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null }); });   // no sidecar or config to watch: the poll watches the file alone
      pic.mode = "hold";                                  // the open's picture held: the view's first paint has not come
      await openFig(page, sid);
      await page.waitForFunction(() => !!document.querySelector(".fileview-body img.fileview-img"), null, { timeout: 10000 });
      await openPanel(page);
      assert.equal((await state(page)).complete, false, road + ": the open's picture is still loading");
      await page.evaluate(() => { const w = window as any; w.__textGate = new Promise<void>((r) => { w.__textOpen = r; }); });   // every decode of the fetched bytes held from here
      await pressSource(page);                            // the Source view waits for the decode, and the loading picture stays up
      await page.evaluate(() => { const w = window as any; w.__gate = new Promise<void>((r) => { w.__open = r; }); });
      await page.evaluate(([m, f, b, h]: [string, string, string, unknown]) => { const w = window as any; w.__mtime = m; w.__docs[f] = b; w.__status = Object.assign({}, w.__status, { hunks: [h] }); }, [MT2, FIG, SVG2, HUNK]);
      await page.waitForFunction(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]') && !!document.querySelector(".fileview-aside .fc-card.fc-change"), null, { timeout: 15000 });
      const before = await cardOf(page);
      assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"] }, road + ": before the reload lands the card claims no Reveal and no tag (file-comments.ts, #cardState's doc)");
      await page.evaluate(() => { (window as any).__open(); });
      await page.waitForFunction((m: string) => (window as any).__seam.mtimeNs() === m, MT2, { timeout: 10000 });   // the reload landed
      await frames(page, 2);
      assert.deepEqual(await cardOf(page), before, road + ": at the landing the card keeps its state");
      pic.release();                                      // the open's picture, pressed over, loads
      await page.waitForFunction(() => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && img.complete; }, null, { timeout: 10000 });
      await frames(page, 3);
      assert.deepEqual(await cardOf(page), before, road + ": through the pressed-over picture's load too");
      await page.evaluate(() => { const w = window as any; w.__textGate = null; w.__textOpen(); });
      await page.waitForFunction(() => (document.querySelector(".fileview-body code.hljs")?.textContent || "").includes('width="300"'), null, { timeout: 10000 });
      await frames(page, 2);
      assert.deepEqual(await cardOf(page), { tags: [], buttons: ["Accept", "Reject", "Comment on this change"] }, road + ": at the decode the view shows the new bytes, and the card moves, once");
      await pressSource(page);                            // back to the picture: the landed bytes' at the session's /file address
      await settled(page);
      onAddress(await state(page), sid, road + ", back to the picture");
      assert.deepEqual(errors, [], road + ": no page errors");
      await page.close();
    }
    {
      const road = "the panel's status in before the open's bytes land";
      const { page, errors, pic } = await scene(browser, "pane", { clock: true, docs: { [REPORT]: LONG, [FIG]: SVG2 } });
      await page.evaluate((h: unknown) => { const w = window as any; w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null, hunks: [h] }); w.__gate = new Promise<void>((r) => { w.__open = r; }); }, HUNK);   // the viewer's first GET held
      pic.mode = "hold";
      await openFig(page);
      await openPanel(page);                              // the status answered, the view's bytes not landed
      await page.waitForFunction(() => !!document.querySelector(".fileview-aside .fc-card.fc-change"), null, { timeout: 15000 });
      const before = await cardOf(page);
      assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), "", road + ": the premise: nothing has landed");
      await page.evaluate(() => { (window as any).__open(); });
      await page.waitForFunction(() => !!document.querySelector(".fileview-body img.fileview-img"), null, { timeout: 10000 });   // the bytes landed; the picture's own request is held
      await frames(page, 3);
      assert.deepEqual(await cardOf(page), before, road + ": the landing moves no card");
      assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"] }, road + ": before the first paint the card claims no Reveal and no tag (file-comments.ts, #cardState's doc)");
      pic.release();
      await decoded(page);
      await frames(page, 3);
      assert.deepEqual(await cardOf(page), { tags: [], buttons: ["Accept", "Reject", "Reveal"] }, road + ": at the picture's paint the card takes its Reveal: the picture marks no change");
      onAddress(await state(page), SID, road);
      assert.deepEqual(errors, [], road + ": no page errors");
      await page.close();
    }
  });
});

/** The change card's tags and buttons, and the fixtures of the pane cases below: a reload's bytes with an insertion pending in them. */
const PANE_INS = ' fill="#996633"';
const PANE_SVG2 = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120"><rect width="300" height="120"' + PANE_INS + '/></svg>';
const PANE_HUNK = { id: "h1", author: "api", ts: 1757145600000, kind: "ins", curFrom: PANE_SVG2.indexOf(PANE_INS), curTo: PANE_SVG2.indexOf(PANE_INS) + PANE_INS.length, baseFrom: PANE_SVG2.indexOf(PANE_INS), baseTo: PANE_SVG2.indexOf(PANE_INS), oldText: "", newText: PANE_INS, anchor: null };
const changeCardOf = (page: any): Promise<{ tags: string[]; buttons: string[] } | null> => page.evaluate(() => {
  const c = document.querySelector(".fileview-aside .fc-card.fc-change");
  return c ? { tags: Array.from(c.querySelectorAll(".fc-card-head .fc-tag")).map((x) => x.textContent || ""), buttons: Array.from(c.querySelectorAll(".fc-actions button")).map((x) => x.textContent || "") } : null;
});
const paneUp = (page: any): Promise<unknown> => page.waitForFunction(() => !!document.querySelector(".fileview-body .fileview-err"), null, { timeout: 10000 });

test("in a browser, the Files pane with the Comments panel open (the page's clock installed): a first open whose fetch fails, the panel's status in first, keeps the change card at Accept and Reject over the pane and moves it once, at the reload's picture (file-comments.ts, #cardState's doc)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const SVG2 = PANE_SVG2, HUNK = PANE_HUNK, cardOf = changeCardOf;
    {
      const road = "a first open whose fetch fails, the status in first";
      const { page, errors } = await scene(browser, "pane", { clock: true, docs: { [REPORT]: LONG, [FIG]: SVG2 } });
      await page.evaluate(([h, fig]: [unknown, string]) => {
        const w = window as any;
        w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null, hunks: [h] });
        w.__gate = new Promise<void>((r) => { w.__open = r; });   // the open's GET held until the panel's status is in
        w.__okAsks = 0; w.__failTo = 1; w.__fail = { status: 404, body: "no such file: " + fig };   // and then answering 404
      }, [HUNK, FIG]);
      await openFig(page);
      await openPanel(page);
      await page.waitForFunction(() => !!document.querySelector(".fileview-aside .fc-card.fc-change"), null, { timeout: 15000 });
      const before = await cardOf(page);
      await page.evaluate(() => { (window as any).__open(); });
      await paneUp(page);
      await frames(page, 3);
      assert.equal((await state(page)).error, "no such file: " + FIG, road + ": the pane stands, error() its words");
      assert.deepEqual(await cardOf(page), before, road + ": the pane moves no card (file-comments.ts, #cardState's doc)");
      assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"] }, road + ": before any content paint, and over the pane, the card claims no Reveal and no tag (file-comments.ts, #cardState's doc)");
      await page.evaluate(() => { (window as any).__seam.reload(); });   // a reload, whose fetch answers
      await decoded(page);
      await frames(page, 3);
      assert.deepEqual(await cardOf(page), { tags: [], buttons: ["Accept", "Reject", "Reveal"] }, road + ": at the reload's picture the card moves, once: the picture marks no change, so a Reveal");
      onAddress(await state(page), SID, road + ", the reload's picture");
      assert.deepEqual(errors, [], road + ": no page errors");
      await page.close();
    }
  });
});

test("in a browser, the Files pane with the Comments panel open (the page's clock installed): a reload whose bytes land and whose picture fails, the address asked again and meeting the relay's 502 too, keeps the change card through that pane and moves it once, at the way back's picture (file-comments.ts, #cardState's doc)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const SVG2 = PANE_SVG2, HUNK = PANE_HUNK, cardOf = changeCardOf;
    {
      const road = "a reload whose picture fails and whose re-ask fails too";
      const { page, errors, pic } = await scene(browser, "pane", { clock: true });
      await page.evaluate(() => { const w = window as any; w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null }); });   // no sidecar or config to watch: the poll watches the file alone
      await openFig(page);
      await settled(page);
      await openPanel(page);
      const asks = (await state(page)).asks;
      // the file moves, with the insertion pending in the new bytes: the reload's GET answers (held until the panel's wait is armed),
      // its picture meets the relay's 502, and the re-ask's GET meets it too
      pic.mode = "502";
      await page.evaluate(([n, b]: [number, string]) => { const w = window as any; w.__gate = new Promise<void>((r) => { w.__open = r; }); w.__okAsks = n + 1; w.__fail = { status: 502, body: b }; }, [asks, RELAY_502]);
      await page.evaluate(([m, f, b, h]: [string, string, string, unknown]) => { const w = window as any; w.__mtime = m; w.__docs[f] = b; w.__status = Object.assign({}, w.__status, { hunks: [h] }); }, [MT2, FIG, SVG2, HUNK]);
      await page.waitForFunction(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]') && !!document.querySelector(".fileview-aside .fc-card.fc-change"), null, { timeout: 15000 });
      const before = await cardOf(page);
      assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"] }, road + ": the premise: the view's bytes are not the status's");
      await page.evaluate(() => { (window as any).__open(); });
      await paneUp(page);
      await frames(page, 3);
      const s = await state(page);
      assert.equal(s.pane, RELAY_502, road + ": the re-ask's pane, in the relay's words");
      assert.equal(s.asks, asks + 2, road + ": the reload's fetch and one re-ask");
      assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT2, road + ": the reload's bytes landed");
      assert.deepEqual(await cardOf(page), before, road + ": the pane moves no card (file-comments.ts, #cardState's doc)");
      pic.mode = "ok";                                    // the address answers again, and this page's socket comes back: the way back
      await page.evaluate(() => { (window as any).__fail = null; window.dispatchEvent(new Event("romp:wsup")); });
      await decoded(page);
      await frames(page, 3);
      assert.deepEqual(await cardOf(page), { tags: [], buttons: ["Accept", "Reject", "Reveal"] }, road + ": at the way back's picture the card moves, once: the picture marks no change, so a Reveal");
      onAddress(await state(page), SID, road + ", the way back's picture");
      assert.deepEqual(errors, [], road + ": no page errors");
      await page.close();
    }
  });
});

/** The change card's tags, buttons and whether its reference links to a mark in the body. */
const changeCardLinkOf = (page: any): Promise<{ tags: string[]; buttons: string[]; link: boolean } | null> => page.evaluate(() => {
  const c = document.querySelector(".fileview-aside .fc-card.fc-change");
  return c ? { tags: Array.from(c.querySelectorAll(".fc-card-head .fc-tag")).map((x) => x.textContent || ""), buttons: Array.from(c.querySelectorAll(".fc-actions button")).map((x) => x.textContent || ""),
    link: !!(c.querySelector(".fc-ref") as HTMLElement | null)?.classList.contains("fc-link") } : null;
});

test("in a browser, the Files pane with the Comments panel open over an svg picture's Source view whose status is current, its pending insertion marked (the page's clock installed): a reload of the same bytes whose fetch answers 404 paints its pane, and over it the change card keeps the state the last content paint gave it, no not shown tag and no Reveal claimed and Comment on this change and the link to the mark kept; the same bytes landing after the pane paint the Source view again and move no card", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const road = "a reload of the Source view's bytes that fails, then the same bytes again";
    const { page, errors } = await scene(browser, "pane", { clock: true, docs: { [REPORT]: LONG, [FIG]: PANE_SVG2 } });
    await page.evaluate((h: unknown) => { const w = window as any; w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null, hunks: [h] }); }, PANE_HUNK);   // the status's bytes are the file's, the insertion pending in them; no sidecar or config to watch
    await openFig(page);
    await settled(page);
    await openPanel(page);
    await pressSource(page);
    const marked = (): Promise<unknown> => page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs") && document.querySelectorAll('.fileview-body [data-act="fcchange"]').length > 0, null, { timeout: 10000 });
    await marked();
    await frames(page, 3);
    const before = await changeCardLinkOf(page);
    assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], link: true }, road + ": the premise: the Source view marks the insertion, and the card links to the mark");
    const asks = (await state(page)).asks;
    await page.evaluate(([n, fig]: [number, string]) => { const w = window as any; w.__okAsks = n; w.__failTo = n + 1; w.__fail = { status: 404, body: "no such file: " + fig }; }, [asks, FIG]);   // the next GET answers 404
    await page.evaluate(() => { (window as any).__seam.reload(); });   // a reload the panel did not ask
    await paneUp(page);
    await frames(page, 3);
    const s = await state(page);
    assert.equal(s.error, "no such file: " + FIG, road + ": the pane stands, error() its words");
    assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT, road + ": the view's mtime is the status's under the pane");
    assert.deepEqual(await changeCardLinkOf(page), before, road + ": over the pane the card keeps the state the last content paint gave it: no not shown tag and no Reveal claimed, no Comment on this change and no link dropped");
    await page.evaluate(() => { (window as any).__seam.reload(); });   // a reload whose GET answers: the same bytes
    await marked();                                       // the Source view paints them again at their decode
    await frames(page, 3);
    assert.equal((await state(page)).error, null, road + ": a content paint");
    assert.deepEqual(await changeCardLinkOf(page), before, road + ": the same bytes' paint moves no card either");
    await pressSource(page);                              // back to the picture, at its /file address
    await settled(page);
    onAddress(await state(page), SID, road + ", back to the picture");
    assert.deepEqual(errors, [], road + ": no page errors");
    await page.close();
  });
});

test("in a browser, the Files pane with the Comments panel open over a png and a pending insertion in a reload's bytes (the page's clock installed): the reload's bytes do not decode, the view's mtime moving to the landed one before the decode fails and no landing told to the panel, and over the decode-failure pane the change card keeps the state the last content paint gave it; it moves once, at the picture of bytes that decode", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const road = "a png reload whose bytes do not decode, then bytes that do";
    const { page, errors } = await scene(browser, "pane", { clock: true, docs: { [REPORT]: LONG, [FIG]: SVG, [PNG]: "png" } });
    // a picture that decodes, made by the page's own canvas; no sidecar or config to watch: the poll watches the file alone
    await page.evaluate(() => {
      const w = window as any;
      const c = document.createElement("canvas"); c.width = 4; c.height = 4;
      const bin = atob(c.toDataURL("image/png").split(",")[1]);
      w.__pngOk = Array.from(bin, (ch: string) => ch.charCodeAt(0)); w.__pngBytes = w.__pngOk;
      w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null });
    });
    await openFig(page, SID, PNG);
    await decoded(page);
    await openPanel(page);
    // the file moves, with the insertion pending in the new bytes, which do not decode; the reload's GET held until the panel's wait is armed
    await page.evaluate(([m, h]: [string, unknown]) => { const w = window as any; w.__pngGate = new Promise<void>((r) => { w.__pngOpen = r; }); w.__pngBytes = null; w.__mtime = m; w.__status = Object.assign({}, w.__status, { hunks: [h] }); }, [MT2, PANE_HUNK]);
    await page.waitForFunction(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]') && !!document.querySelector(".fileview-aside .fc-card.fc-change"), null, { timeout: 15000 });
    const before = await changeCardLinkOf(page);
    assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"], link: false }, road + ": the premise: the view's bytes are not the status's");
    await page.evaluate(() => { (window as any).__pngOpen(); });
    await paneUp(page);
    await frames(page, 3);
    const s = await state(page);
    assert.equal(s.pane, DECODE_FAILED, road + ": the bytes do not decode: DECODE_FAILED's pane");
    assert.equal(await page.evaluate(() => (window as any).__seam.mtimeNs()), MT2, road + ": the view's mtime is the landed one, the status's, under the pane");
    assert.deepEqual(await changeCardLinkOf(page), before, road + ": the pane moves no card (file-comments.ts, #cardState's doc)");
    await page.evaluate(() => { const w = window as any; w.__pngBytes = w.__pngOk; w.__seam.reload(); });   // a reload whose bytes decode
    await decoded(page);
    await frames(page, 3);
    assert.deepEqual(await changeCardLinkOf(page), { tags: [], buttons: ["Accept", "Reject", "Reveal"], link: false }, road + ": at the picture of bytes that decode the card moves, once: the picture marks no change, so a Reveal");
    assert.ok((await state(page)).objectUrls.includes("image/png"), road + ": the png's picture is an object URL of its bytes");
    assert.deepEqual(errors, [], road + ": no page errors");
    await page.close();
  });
});

test("in a browser, the Files pane with the Comments panel open over an svg picture's Source view and a pending insertion in a reload that lands under it (the page's clock installed): with the landed bytes' decode held, a press to the picture and a press back paint no Source view of the older XML, so the change card keeps its state through both presses and the pressed-over picture's load, and moves once, at the decode, over the landed XML", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const INS = ' fill="#996633"';
    const SVG2 = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120"><rect width="300" height="120"' + INS + '/></svg>';
    const at = SVG2.indexOf(INS);
    const HUNK = { id: "h1", author: "api", ts: 1757145600000, kind: "ins", curFrom: at, curTo: at + INS.length, baseFrom: at, baseTo: at, oldText: "", newText: INS, anchor: null };
    type Card = { tags: string[]; buttons: string[] } | null;
    const cardOf = (page: any): Promise<Card> => page.evaluate(() => {
      const c = document.querySelector(".fileview-aside .fc-card.fc-change");
      return c ? { tags: Array.from(c.querySelectorAll(".fc-card-head .fc-tag")).map((x) => x.textContent || ""), buttons: Array.from(c.querySelectorAll(".fc-actions button")).map((x) => x.textContent || "") } : null;
    });
    const paints = (page: any): Promise<number> => page.evaluate(() => { const w = window as any; return w.__paints - w.__reflows; });
    const sourceXml = (page: any): Promise<string | null> => page.evaluate(() => document.querySelector(".fileview-body code.hljs")?.textContent ?? null);
    const road = "a reload under the Source view, to the picture and back while its decode is held";
    const { page, errors, pic } = await scene(browser, "pane", { clock: true });
    await page.evaluate(() => { const w = window as any; w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null }); });   // no sidecar or config to watch: the poll watches the file alone
    await openFig(page);
    await settled(page);
    await openPanel(page);
    await pressSource(page);
    await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs"), null, { timeout: 10000 });
    await page.evaluate(() => { const w = window as any; w.__textGate = new Promise<void>((r) => { w.__textOpen = r; }); });   // every decode of the fetched bytes held from here
    await page.evaluate(() => { const w = window as any; w.__gate = new Promise<void>((r) => { w.__open = r; }); });
    await page.evaluate(([m, f, b, h]: [string, string, string, unknown]) => { const w = window as any; w.__mtime = m; w.__docs[f] = b; w.__status = Object.assign({}, w.__status, { hunks: [h] }); }, [MT2, FIG, SVG2, HUNK]);
    await page.waitForFunction(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]') && !!document.querySelector(".fileview-aside .fc-card.fc-change"), null, { timeout: 15000 });
    const before = await cardOf(page);
    assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"] }, road + ": the premise: the view's bytes are not the status's");
    await page.evaluate(() => { (window as any).__open(); });
    await page.waitForFunction((m: string) => (window as any).__seam.mtimeNs() === m, MT2, { timeout: 10000 });   // the reload landed under the Source view
    await frames(page, 2);
    assert.ok(((await sourceXml(page)) || "").includes('width="200"'), road + ": the decode is held: the older XML still shows");
    assert.deepEqual(await cardOf(page), before, road + ": at the landing the card keeps its state");
    const p0 = await paints(page);
    pic.mode = "hold";                                    // the landed bytes' picture held
    await pressSource(page);                              // to the picture
    await page.waitForFunction((m: string) => { const img = document.querySelector(".fileview-body img.fileview-img"); return !!img && (img.getAttribute("src") || "").endsWith("&v=" + m); }, MT2, { timeout: 10000 });
    await frames(page, 2);
    assert.deepEqual(await cardOf(page), before, road + ": after the press to the picture, still loading, the card keeps its state");
    await pressSource(page);                              // back to the Source view
    await frames(page, 3);
    assert.deepEqual(await cardOf(page), before, road + ": after the press back the card keeps its state: no Source view of the older XML was painted at the landed mtime");
    assert.equal(await sourceXml(page), null, road + ": the press back paints no Source view of the older XML; the picture stays up while the landed bytes decode");
    pic.release();                                        // the pressed-over picture's own request ends
    await page.waitForFunction(() => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && img.complete; }, null, { timeout: 10000 });
    await frames(page, 3);
    assert.deepEqual(await cardOf(page), before, road + ": through the pressed-over picture's load too");
    assert.equal(await paints(page), p0, road + ": no paint yet");
    await page.evaluate(() => { const w = window as any; w.__textGate = null; w.__textOpen(); });
    await page.waitForFunction(() => (document.querySelector(".fileview-body code.hljs")?.textContent || "").includes('width="300"'), null, { timeout: 10000 });
    await frames(page, 3);
    assert.equal(await paints(page), p0 + 1, road + ": one paint, the Source view's at the decode");
    assert.deepEqual(await cardOf(page), { tags: [], buttons: ["Accept", "Reject", "Comment on this change"] }, road + ": at the decode the Source view marks the insertion over the landed XML, and the card moves, once");
    await pressSource(page);                              // back to the picture: the landed bytes' at their /file address
    await settled(page);
    onAddress(await state(page), SID, road + ", back to the picture");
    assert.deepEqual(errors, [], road + ": no page errors");
    await page.close();
  });
});

/** The change card as the person sees it, its Reveal's title with it. */
const changeCardFullOf = (page: any): Promise<{ tags: string[]; buttons: string[]; link: boolean; reveal: string | null } | null> => page.evaluate(() => {
  const c = document.querySelector(".fileview-aside .fc-card.fc-change");
  const rv = c ? c.querySelector('[data-act="fcreveal"]') as HTMLElement | null : null;
  return c ? { tags: Array.from(c.querySelectorAll(".fc-card-head .fc-tag")).map((x) => x.textContent || ""), buttons: Array.from(c.querySelectorAll(".fc-actions button")).map((x) => x.textContent || ""),
    link: !!(c.querySelector(".fc-ref") as HTMLElement | null)?.classList.contains("fc-link"), reveal: rv ? rv.title : null } : null;
});
/** The panel's status asks so far (the page's __posted). */
const statusAsks = (page: any): Promise<number> => page.evaluate(() => (window as any).__posted.filter((m: any) => m && m.type === "fileComments" && m.verb === "status").length);
/** The svg's Source view up over its current status, the insertion marked, the Comments panel open or not. */
async function markedSource(page: any, open: boolean): Promise<void> {
  await page.evaluate((h: unknown) => { const w = window as any; w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null, hunks: [h] }); }, PANE_HUNK);   // the status's bytes are the file's, the insertion pending in them; no sidecar or config to watch
  await openFig(page);
  await settled(page);
  if (open) await openPanel(page);
  await pressSource(page);
  await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs") && document.querySelectorAll('.fileview-body [data-act="fcchange"]').length > 0, null, { timeout: 10000 });
  await frames(page, 3);
}
/** The next GET of the svg answers 404, and a reload the panel did not ask paints its pane. */
async function reloadTo404(page: any): Promise<void> {
  const asks = (await state(page)).asks;
  await page.evaluate(([n, fig]: [number, string]) => { const w = window as any; w.__okAsks = n; w.__failTo = n + 1; w.__fail = { status: 404, body: "no such file: " + fig }; }, [asks, FIG]);
  await page.evaluate(() => { (window as any).__seam.reload(); });
  await paneUp(page);
  await frames(page, 3);
}

test("in a browser, the Files pane over an svg's Source view whose status is current, its pending insertion marked (the page's clock installed): a reload of the same bytes fails to a pane, and the Comments panel closed and opened over it, its status re-read unchanged, moves no change card; nor does the panel's first open over such a pane; the same bytes painted again move none (file-comments.ts, #cardState's doc)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const marked = (page: any): Promise<unknown> => page.waitForFunction(() => document.querySelectorAll('.fileview-body [data-act="fcchange"]').length > 0, null, { timeout: 10000 });
    for (const road of ["the panel closed and opened over the pane", "the panel's first open over the pane"]) {
      const first = road === "the panel's first open over the pane";
      const { page, errors } = await scene(browser, "pane", { clock: true, docs: { [REPORT]: LONG, [FIG]: PANE_SVG2 } });
      await markedSource(page, !first);
      const before = first ? null : await changeCardFullOf(page);
      if (!first) assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], link: true, reveal: null }, road + ": the premise: the Source view marks the insertion, and the card links to the mark");
      await reloadTo404(page);
      assert.equal((await state(page)).error, "no such file: " + FIG, road + ": the pane stands");
      if (!first) { assert.deepEqual(await changeCardFullOf(page), before, road + ": the pane moves no card"); await closePanel(page); }
      const asks = await statusAsks(page);
      await openPanel(page);
      await page.waitForFunction((n: number) => (window as any).__posted.filter((m: any) => m && m.type === "fileComments" && m.verb === "status").length > n, asks, { timeout: 10000 });   // the open's re-read of the status
      await frames(page, 6);                              // and its answer, the same status, applied
      assert.equal((await state(page)).error, "no such file: " + FIG, road + ": the pane still stands");
      assert.deepEqual(await changeCardFullOf(page), { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], link: true, reveal: null }, road + ": over the pane, after the open's re-read of the same status, the card shows what the last content paint gave it: Comment on this change and the link, no tag and no Reveal (file-comments.ts, #cardState's doc)");
      await page.evaluate(() => { (window as any).__seam.reload(); });   // a reload whose GET answers: the same bytes
      await marked(page);
      await frames(page, 3);
      assert.deepEqual(await changeCardFullOf(page), { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], link: true, reveal: null }, road + ": the same bytes' paint moves no card");
      await pressSource(page);
      await settled(page);
      onAddress(await state(page), SID, road + ", back to the picture");
      assert.deepEqual(errors, [], road + ": no page errors");
      await page.close();
    }
  });
});

test("in a browser, the Files pane with the Comments panel open over a png whose status is current and a pending insertion (the page's clock installed): the file moves, the poll asks the reload and the status together, the reload's bytes land and the status for them arrives while the landed bytes' picture decodes, the bytes then fail to decode, and a reload brings bytes that do: the change card moves at the status and at the paint of the bytes that decode; the landing and the pane move none (file-comments.ts, #cardState's doc)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const road = "a png's landing, the status for its bytes, the decode-failure pane, then bytes that decode";
    const { page, errors } = await scene(browser, "pane", { clock: true, docs: { [REPORT]: LONG, [FIG]: SVG, [PNG]: "png" } });
    await page.evaluate((h: unknown) => {
      const w = window as any;
      const c = document.createElement("canvas"); c.width = 4; c.height = 4;
      const bin = atob(c.toDataURL("image/png").split(",")[1]);
      w.__pngOk = Array.from(bin, (ch: string) => ch.charCodeAt(0)); w.__pngBytes = w.__pngOk;   // a picture that decodes, made by the page's own canvas
      w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null, hunks: [h] });   // the status of the png's bytes, the insertion pending in them; the poll watches the file alone
    }, PANE_HUNK);
    await openFig(page, SID, PNG);
    await decoded(page);
    await openPanel(page);
    await page.waitForFunction(() => !!document.querySelector(".fileview-aside .fc-card.fc-change"), null, { timeout: 15000 });
    const before = await changeCardFullOf(page);
    assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject", "Reveal"], link: false, reveal: "Show the change in the Raw view" }, road + ": the premise: the picture shows the status's bytes and marks no change, so a Reveal");
    // the file moves to bytes that do not decode: the poll's status ask is held unanswered, and the reload's GET until both are out
    const asks = await statusAsks(page);
    const gets = await page.evaluate(() => (window as any).__pngAsks);
    await page.evaluate((m: string) => { const w = window as any; w.__autoReply = false; w.__pngGate = new Promise<void>((r) => { w.__pngOpen = r; }); w.__pngBytes = null; w.__mtime = m; }, MT2);
    await page.waitForFunction(([n, g]: [number, number]) => { const w = window as any; return w.__posted.filter((m: any) => m && m.type === "fileComments" && m.verb === "status").length > n && w.__pngAsks > g; }, [asks, gets], { timeout: 15000 });
    // at the landing (the object URL of the new bytes is made after mtimeNs() moved, before the picture is put up): the status
    // for those bytes is answered there; the panel applies it once the landing's task ends, while the new picture decodes, and
    // every render of the card from then until the pane is recorded
    await page.evaluate(() => {
      const w = window as any;
      const ask = w.__posted.filter((m: any) => m && m.type === "fileComments" && m.verb === "status").pop();
      const read = () => { const c = document.querySelector(".fileview-aside .fc-card.fc-change"); return c ? { tags: Array.from(c.querySelectorAll(".fc-card-head .fc-tag")).map((x) => x.textContent || ""), buttons: Array.from(c.querySelectorAll(".fc-actions button")).map((x) => x.textContent || ""), link: !!(c.querySelector(".fc-ref") as HTMLElement | null)?.classList.contains("fc-link"), reveal: (c.querySelector('[data-act="fcreveal"]') as HTMLElement | null)?.title ?? null } : null; };
      w.__renders = [];
      const aside = document.querySelector(".fileview-aside")!;
      const seen = new MutationObserver(() => { if (w.__answered && !document.querySelector(".fileview-body .fileview-err")) w.__renders.push({ card: read(), mtime: w.__seam.mtimeNs() }); });
      seen.observe(aside, { childList: true, subtree: true, attributes: true, characterData: true });
      const mint = URL.createObjectURL;
      URL.createObjectURL = (b: any) => {
        const u = mint(b);
        if (b && b.type === "image/png") {
          URL.createObjectURL = mint;
          w.__atLanding = { mtime: w.__seam.mtimeNs(), card: read() };
          w.__answered = true;
          window.dispatchEvent(new MessageEvent("message", { data: Object.assign({ type: "fileCommentsResult", reqId: ask.reqId, fileMtimeNs: w.__mtime }, w.__status) }));
        }
        return u;
      };
      w.__pngOpen();
    });
    await paneUp(page);
    await frames(page, 3);
    const at = await page.evaluate(() => { const w = window as any; return { landing: w.__atLanding, renders: w.__renders }; });
    assert.equal(at.landing.mtime, MT2, road + ": the landing moved the view's mtime before the status arrived");
    assert.deepEqual(at.landing.card, before, road + ": the landing moves no card");
    assert.ok(at.renders.length > 0, road + ": the status was applied, and the card rendered, before the pane");
    for (const r of at.renders) assert.deepEqual(r.card, { tags: [], buttons: ["Accept", "Reject"], link: false, reveal: null }, road + ": at the status the card moves: no Reveal (file-comments.ts, #cardState's doc; at fe43d2c2a the landed mtime read as shown, and the Reveal stood over the landed bytes' picture, over the pane and past it)");
    const status = at.renders[at.renders.length - 1].card;
    assert.equal((await state(page)).pane, DECODE_FAILED, road + ": the bytes do not decode: DECODE_FAILED's pane");
    assert.deepEqual(await changeCardFullOf(page), status, road + ": the pane moves no card");
    await page.evaluate(() => { const w = window as any; w.__autoReply = true; w.__pngBytes = w.__pngOk; w.__seam.reload(); });   // a reload whose bytes decode
    await decoded(page);
    await frames(page, 3);
    assert.deepEqual(await changeCardFullOf(page), before, road + ": at the paint of bytes that decode the card moves: the picture marks no change, so a Reveal");
    assert.deepEqual(errors, [], road + ": no page errors");
    await page.close();
  });
});

test("in a browser, the Files pane with the Comments panel open over an svg's Source view whose status is current, its pending insertion marked (the page's clock installed): Show changes inline off moves the card at once; a reload of the same bytes fails to a pane, and Show changes inline on over the pane moves no change card; the paint of the same bytes takes the flip, marking the insertion again (file-comments.ts, #cardState's doc)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const road = "Show changes inline off, a pane, on over the pane, then the paint";
    const { page, errors } = await scene(browser, "pane", { clock: true, docs: { [REPORT]: LONG, [FIG]: PANE_SVG2 } });
    await markedSource(page, true);
    const inline = (): Promise<void> => page.evaluate(() => { (document.querySelector('.fileview-aside [data-act="fcinline"]') as HTMLElement).click(); });
    await inline();                                        // off, over the Source view
    await page.waitForFunction(() => document.querySelectorAll('.fileview-body [data-act="fcchange"]').length === 0, null, { timeout: 10000 });
    await frames(page, 3);
    const off = await changeCardFullOf(page);
    assert.equal(off!.link, false, road + ": off, the mark goes at once, and the link with it");
    assert.ok(off!.reveal !== null && off!.reveal.startsWith("Open the Raw view at the change") && off!.tags.length === 0, road + ": and the card offers the marks-off Reveal at once: " + JSON.stringify(off));
    await reloadTo404(page);
    await inline();                                        // on, over the pane
    await frames(page, 6);
    assert.equal((await state(page)).error, "no such file: " + FIG, road + ": the pane still stands");
    assert.deepEqual(await changeCardFullOf(page), off, road + ": the flip on over the pane moves no card: no not shown tag and no Reveal naming the marks (file-comments.ts, #cardState's doc; at fe43d2c2a both came at the flip, over the pane)");
    await page.evaluate(() => { (window as any).__seam.reload(); });   // the same bytes land and the Source view paints them
    await page.waitForFunction(() => document.querySelectorAll('.fileview-body [data-act="fcchange"]').length > 0, null, { timeout: 10000 });
    await frames(page, 3);
    assert.deepEqual(await changeCardFullOf(page), { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], link: true, reveal: null }, road + ": the paint takes the flip: the insertion marked again, the card linking to it");
    await pressSource(page);
    await settled(page);
    onAddress(await state(page), SID, road + ", back to the picture");
    assert.deepEqual(errors, [], road + ": no page errors");
    await page.close();
  });
});

test("in a browser, the Files pane with the Comments panel open over an svg's Source view (the page's clock installed): a reload with a pending insertion lands under it with its decode held, a second reload's fetch fails to a pane, the pane is left by a press of the Source toggle to a picture still loading, and then a render and Show changes inline off and on: no change card moves until the picture's load, the paint of the landed bytes (file-comments.ts, #cardState's doc)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const road = "a landing under the Source view, a pane, a press to the picture, then a render and two flips";
    const { page, errors, pic } = await scene(browser, "pane", { clock: true });
    await page.evaluate(() => { const w = window as any; w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null }); });   // no sidecar or config to watch: the poll watches the file alone
    await openFig(page);
    await settled(page);
    await openPanel(page);
    await pressSource(page);
    await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs"), null, { timeout: 10000 });
    await page.evaluate(() => { const w = window as any; w.__textGate = new Promise<void>((r) => { w.__textOpen = r; }); w.__gate = new Promise<void>((r) => { w.__open = r; }); });   // every decode held from here, and the reload's GET until the panel's wait is armed
    await page.evaluate(([m, f, b, h]: [string, string, string, unknown]) => { const w = window as any; w.__mtime = m; w.__docs[f] = b; w.__status = Object.assign({}, w.__status, { hunks: [h] }); }, [MT2, FIG, PANE_SVG2, PANE_HUNK]);
    await page.waitForFunction(() => !!document.querySelector('.fileview-aside .fc-load[data-slot="bytes"]') && !!document.querySelector(".fileview-aside .fc-card.fc-change"), null, { timeout: 15000 });
    const before = await changeCardFullOf(page);
    assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"], link: false, reveal: null }, road + ": the premise: the view's bytes are not the status's");
    await page.evaluate(() => { (window as any).__open(); });
    await page.waitForFunction((m: string) => (window as any).__seam.mtimeNs() === m, MT2, { timeout: 10000 });   // the reload landed under the Source view, its decode held
    await frames(page, 2);
    assert.deepEqual(await changeCardFullOf(page), before, road + ": the landing moves no card");
    await reloadTo404(page);                               // a second reload's GET answers 404: its pane
    assert.deepEqual(await changeCardFullOf(page), before, road + ": the pane moves no card");
    pic.mode = "hold";                                     // the landed bytes' picture held
    await pressSource(page);                               // from the pane to the picture: error() null, the picture still loading
    await page.waitForFunction(() => { const img = document.querySelector(".fileview-body img.fileview-img") as HTMLImageElement | null; return !!img && !img.complete && !document.querySelector(".fileview-body .fileview-err"); }, null, { timeout: 10000 });
    await frames(page, 2);
    assert.equal((await state(page)).error, null, road + ": the press left the pane: error() null, the picture not loaded");
    assert.deepEqual(await changeCardFullOf(page), before, road + ": the press moves no card");
    await page.evaluate(() => { (document.querySelector(".fileview-aside .fc-card.fc-change .fc-card-head") as HTMLElement).click(); });   // a render with nothing new: the card's head
    await frames(page, 2);
    assert.deepEqual(await changeCardFullOf(page), before, road + ": a render before the picture's load moves no card");
    for (const flip of ["off", "on"]) {
      await page.evaluate(() => { (document.querySelector('.fileview-aside [data-act="fcinline"]') as HTMLElement).click(); });
      await frames(page, 2);
      assert.deepEqual(await changeCardFullOf(page), before, road + ": Show changes inline " + flip + " before the picture's load moves no card");
    }
    pic.release();                                         // the picture's own request ends: its load, the content paint of the landed bytes
    await decoded(page);
    await frames(page, 3);
    assert.deepEqual(await changeCardFullOf(page), { tags: [], buttons: ["Accept", "Reject", "Reveal"], link: false, reveal: "Show the change in the Raw view" }, road + ": at the picture's load the card moves, once: the picture marks no change, so a Reveal");
    onAddress(await state(page), SID, road + ", the picture");
    await page.evaluate(() => { const w = window as any; w.__textGate = null; w.__textOpen(); });
    assert.deepEqual(errors, [], road + ": no page errors");
    await page.close();
  });
});

test("in a browser, the Files pane with the Comments panel open over a png whose status is current and a pending insertion (the page's clock installed): newer bytes land, their picture up and still decoding, and a status for the painted bytes whose sidecar moved arrives then: the change card moves at that status, the insertion's Reveal withheld over the landed bytes' picture, and the decode-failure pane moves it no further (file-comments.ts, #cardState's doc)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const road = "a png's landing, then a status for the painted bytes, then the decode-failure pane";
    const { page, errors } = await scene(browser, "pane", { clock: true, docs: { [REPORT]: LONG, [FIG]: SVG, [PNG]: "png" } });
    await page.evaluate((h: unknown) => {
      const w = window as any;
      const c = document.createElement("canvas"); c.width = 4; c.height = 4;
      const bin = atob(c.toDataURL("image/png").split(",")[1]);
      w.__pngBytes = Array.from(bin, (ch: string) => ch.charCodeAt(0));   // a picture that decodes, made by the page's own canvas
      w.__status = Object.assign({}, w.__status, { storeMtimeNs: null, configMtimeNs: null, hunks: [h] });   // the status of the png's bytes, the insertion pending in them; the poll watches the file alone
    }, PANE_HUNK);
    await openFig(page, SID, PNG);
    await decoded(page);
    await openPanel(page);
    await page.waitForFunction(() => !!document.querySelector(".fileview-aside .fc-card.fc-change"), null, { timeout: 15000 });
    const before = await changeCardFullOf(page);
    assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject", "Reveal"], link: false, reveal: "Show the change in the Raw view" }, road + ": the premise: the picture shows the status's bytes and marks no change, so a Reveal");
    // the file moves to bytes that do not decode: the poll's status ask is held unanswered, and the reload's GET until both are out
    const asks = await statusAsks(page);
    const gets = await page.evaluate(() => (window as any).__pngAsks);
    await page.evaluate((m: string) => { const w = window as any; w.__autoReply = false; w.__pngGate = new Promise<void>((r) => { w.__pngOpen = r; }); w.__pngBytes = null; w.__mtime = m; }, MT2);
    await page.waitForFunction(([n, g]: [number, number]) => { const w = window as any; return w.__posted.filter((m: any) => m && m.type === "fileComments" && m.verb === "status").length > n && w.__pngAsks > g; }, [asks, gets], { timeout: 15000 });
    // at the landing (the object URL of the new bytes is made after mtimeNs() moved, before their picture goes up) the held ask is
    // answered with a status for the painted bytes, the sidecar moved; the panel applies it once the landing's task ends, while the
    // landed bytes' picture decodes, and every render of the card from then until the pane is recorded
    await page.evaluate((mt: string) => {
      const w = window as any;
      const ask = w.__posted.filter((m: any) => m && m.type === "fileComments" && m.verb === "status").pop();
      const read = () => { const c = document.querySelector(".fileview-aside .fc-card.fc-change"); return c ? { tags: Array.from(c.querySelectorAll(".fc-card-head .fc-tag")).map((x) => x.textContent || ""), buttons: Array.from(c.querySelectorAll(".fc-actions button")).map((x) => x.textContent || ""), link: !!(c.querySelector(".fc-ref") as HTMLElement | null)?.classList.contains("fc-link"), reveal: (c.querySelector('[data-act="fcreveal"]') as HTMLElement | null)?.title ?? null } : null; };
      w.__renders = [];
      const aside = document.querySelector(".fileview-aside")!;
      new MutationObserver(() => { if (w.__answered && !document.querySelector(".fileview-body .fileview-err")) w.__renders.push({ card: read(), picture: !!document.querySelector(".fileview-body img.fileview-img") }); })
        .observe(aside, { childList: true, subtree: true, attributes: true, characterData: true });
      const mint = URL.createObjectURL;
      URL.createObjectURL = (b: any) => {
        const u = mint(b);
        if (b && b.type === "image/png") {
          URL.createObjectURL = mint;
          w.__atLanding = { mtime: w.__seam.mtimeNs(), card: read() };
          w.__answered = true;
          window.dispatchEvent(new MessageEvent("message", { data: Object.assign({ type: "fileCommentsResult", reqId: ask.reqId }, w.__status, { fileMtimeNs: mt, storeMtimeNs: "1757145600000000005" }) }));
        }
        return u;
      };
      w.__pngOpen();
    }, MT);
    await paneUp(page);
    await frames(page, 3);
    const at = await page.evaluate(() => { const w = window as any; return { landing: w.__atLanding, renders: w.__renders }; });
    assert.equal(at.landing.mtime, MT2, road + ": the landing moved the view's mtime before the status arrived");
    assert.deepEqual(at.landing.card, before, road + ": the landing moves no card");
    assert.ok(at.renders.length > 0 && at.renders.every((r: { picture: boolean }) => r.picture), road + ": the status was applied, and the card rendered, while the landed bytes' picture held the body: " + JSON.stringify(at.renders));
    for (const r of at.renders) assert.deepEqual(r.card, { tags: [], buttons: ["Accept", "Reject"], link: false, reveal: null }, road + ": at the status the card moves: no Reveal (file-comments.ts, #cardState's doc; as at fe43d2c2a, which read the landed mtime and withheld the Reveal too)");
    assert.equal((await state(page)).pane, DECODE_FAILED, road + ": the bytes do not decode: DECODE_FAILED's pane");
    assert.deepEqual(await changeCardFullOf(page), at.renders[at.renders.length - 1].card, road + ": the pane moves no card");
    assert.deepEqual(errors, [], road + ": no page errors");
    await page.close();
  });
});

const NOT_IN_VIEW_LINK = "This change is not in view right now. Its link works once it is.";   // file-comments.ts NOT_IN_VIEW_LINK
const NOT_IN_VIEW_COMMENT = "This change is not in view right now. Comment on this change works once it is.";   // file-comments.ts NOT_IN_VIEW_COMMENT
/** The row under the change card, the composer's visibility, the pane, and the panel's requests so far. */
const clickState = (page: any): Promise<{ row: string | null; composer: boolean; pane: boolean; posted: number }> => page.evaluate(() => {
  const r = document.querySelector(".fileview-aside .fc-card.fc-change .fc-err span");
  const box = document.querySelector(".fileview-aside .fc-composer") as HTMLElement | null;
  return { row: r ? r.textContent : null, composer: !!box && !box.hidden, pane: !!document.querySelector(".fileview-body .fileview-err"), posted: (window as any).__posted.filter((m: any) => m && m.type === "fileComments").length };
});

test("in a browser, the Files pane with the Comments panel open over an svg's Source view whose status is current, its pending insertion marked (the page's clock installed): a reload of the same bytes fails to a pane, and a click on the change card's link or on Comment on this change says in a row under the card that the change is not in view and does nothing else; after the same bytes' paint, Comment on this change opens the composer (file-comments.ts, #cardState's doc and notInView)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const road = "a pane over the marked Source view, then clicks on the card's link and its Comment on this change";
    const { page, errors } = await scene(browser, "pane", { clock: true, docs: { [REPORT]: LONG, [FIG]: PANE_SVG2 } });
    await markedSource(page, true);
    await reloadTo404(page);
    assert.deepEqual(await changeCardFullOf(page), { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], link: true, reveal: null }, road + ": the premise: over the pane the card keeps the link and Comment on this change the last content paint gave it");
    const before = await clickState(page);
    assert.deepEqual([before.row, before.composer, before.pane], [null, false, true], road + ": the premise: no row, no composer, the pane standing");
    await page.evaluate(() => { (document.querySelector(".fileview-aside .fc-card.fc-change .fc-ref") as HTMLElement).click(); });
    await frames(page, 3);
    assert.deepEqual(await clickState(page), { ...before, row: NOT_IN_VIEW_LINK }, road + ": the link's click shows the row and nothing else: no composer, the pane standing, no request");
    await page.evaluate(() => { (document.querySelector('.fileview-aside .fc-card.fc-change [data-act="fcchangecomment"]') as HTMLElement).click(); });
    await frames(page, 3);
    assert.deepEqual(await clickState(page), { ...before, row: NOT_IN_VIEW_COMMENT }, road + ": Comment on this change's click shows the row and opens no composer");
    await page.evaluate(() => { (window as any).__seam.reload(); });   // the same bytes land and the Source view paints them
    await page.waitForFunction(() => document.querySelectorAll('.fileview-body [data-act="fcchange"]').length > 0, null, { timeout: 10000 });
    await frames(page, 3);
    assert.equal((await clickState(page)).row, null, road + ": the content paint takes the row");
    await page.evaluate(() => { (document.querySelector('.fileview-aside .fc-card.fc-change [data-act="fcchangecomment"]') as HTMLElement).click(); });
    await frames(page, 3);
    const after = await clickState(page);
    assert.deepEqual([after.row, after.composer], [null, true], road + ": after the paint Comment on this change opens the composer");
    assert.deepEqual(errors, [], road + ": no page errors");
    await page.close();
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
