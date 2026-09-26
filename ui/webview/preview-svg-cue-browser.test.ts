// The chat's svg preview in headless Chromium, over the REAL preview module under the chat page's own sheet (real-viewer-leg.ts
// serves the chat page with styles.css and bundles preview.ts's previewFull, the box the chat builds for a mentioned picture; the
// page's fetch stub answers the preview's managed fetch, and a route here answers the picture's own requests to its /file
// address). The first attempt's picture fails, so the box is the retrying swirl, whose tap pulses the wait element the tap is on
// (the sheet animates it; under reduced motion it stays still, as the chip and the note do). The tap's managed fetch lands, and
// the picture loads from its /file address beside the one swirl, the wait element out of the failure state while it loads: no
// retry title, no pointer cursor, no tap handler. The loading cue is keyed on the picture itself: a re-render while the page
// holds the loaded picture finds it complete once its src is set and shows it at once with no cue, and a re-render after the
// page has let it go (a forced garbage collection, Chromium's HeapProfiler.collectGarbage) finds it not complete and waits
// beside the swirl until its load. After every road the picture's src is its /file address and no object URL is made for the
// svg. Waits are for the page's own events or the picture's settling, never a timer. Skips LOUDLY without a playwright browser
// (CI installs none). Synthetic values only: /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, ROOT, REPORT, LONG, SID } from "./real-viewer-leg";

const FIG = ROOT + "/figs/cue.svg";
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="120"><rect width="200" height="120" fill="#336699"/></svg>';
/** The picture's /file address: the local route, the sid, no pin. */
const ADDRESS = "/file?path=" + encodeURIComponent(FIG) + "&sid=" + encodeURIComponent(SID);

type Pic = { mode: "refuse" | "hold" | "ok"; reqs: number; release: () => void };
/** A re-render of the mention, read the moment previewFull returns: whether the picture was complete when its src was set,
 *  whether the box shows the cue (the wait element and its swirl beside the picture, the picture hidden), and the address. */
type Read = { completeAtSrc: boolean | null; cue: boolean; swirls: number; loading: boolean; src: string | null };

/** A forced garbage collection in the page: the page may let go of the pictures it holds. */
async function forceGc(page: any): Promise<void> {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("HeapProfiler.collectGarbage");
  await cdp.detach();
}

/** A chat page with the route and the instruments, the viewer closed; `render(id)` builds a box for the mention as a turn's render
 *  does and reads it at once, `shown(id)` waits for that box to settle on its decoded picture, alone. The first attempt's picture
 *  is refused (`pic.mode` "refuse"), so the box starts as the retrying swirl. */
async function chatPage(browser: any): Promise<{ page: any; errors: string[]; pic: Pic; render: (id: string) => Promise<Read>; shown: (id: string) => Promise<unknown> }> {
  let release: () => void = () => {};
  let held = new Promise<void>((r) => { release = r; });
  const pic: Pic = { mode: "refuse", reqs: 0, release: () => release() };
  const before = async (page: any): Promise<void> => {
    await page.route((u: URL) => u.pathname === "/file" && u.searchParams.get("path") === FIG, async (route: any) => {
      pic.reqs++;
      const m = pic.mode;
      if (m === "refuse") return route.abort("connectionrefused");
      if (m === "hold") { await held; held = new Promise<void>((r) => { release = r; }); }
      return route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG });
    });
    await page.evaluate(() => {
      const w = window as any;
      w.__srcSet = [] as boolean[];
      w.__objectUrls = [] as string[];
      const mint = URL.createObjectURL.bind(URL);
      URL.createObjectURL = (b: any) => { w.__objectUrls.push(b && b.type || ""); return mint(b); };
      // whether each preview picture was complete the moment its src was set (previewFull's mkImg sets the class, then the src)
      const proto = HTMLImageElement.prototype as any;
      const getSrc = proto.__lookupGetter__("src"), setSrc = proto.__lookupSetter__("src");
      Object.defineProperty(HTMLImageElement.prototype, "src", { configurable: true, get() { return getSrc.call(this); }, set(v: string) {
        setSrc.call(this, v);
        if (this.classList.contains("path-full-img")) w.__srcSet.push(this.complete);
      } });
    });
  };
  const { page, errors } = await openViewer(browser, "chat", 900, 600, { docs: { [REPORT]: LONG, [FIG]: SVG }, before });
  await page.evaluate(() => { (window as any).FV.closeFileView(); });
  const render = (id: string): Promise<Read> => page.evaluate(([f, s, i]: [string, string, string]) => {
    const w = window as any;
    let host = document.getElementById("msgs");
    if (!host) { host = document.createElement("div"); host.id = "msgs"; document.body.appendChild(host); }
    const n = w.__srcSet.length;
    const b = w.FV.previewFull(f, s, true) as HTMLElement;
    b.id = i;
    host.appendChild(b);
    const img = b.querySelector("img.path-full-img") as HTMLImageElement | null;
    return { completeAtSrc: w.__srcSet.length > n ? w.__srcSet[w.__srcSet.length - 1] : null, cue: !!b.querySelector(".path-full-wait"),
      swirls: b.querySelectorAll(".path-load-spin").length, loading: !!img && img.classList.contains("path-img-loading"), src: img ? img.getAttribute("src") : null };
  }, [FIG, SID, id]);
  const shown = (id: string): Promise<unknown> => page.waitForFunction((i: string) => {
    const b = document.getElementById(i);
    const img = b && b.querySelector("img.path-full-img") as HTMLImageElement | null;
    return !!img && img.complete && img.naturalWidth > 0 && !b!.querySelector(".path-full-wait") && !img.classList.contains("path-img-loading");
  }, id, { timeout: 10000 });
  await render("box1");
  await page.waitForFunction(() => { const w = document.querySelector("#box1 .path-full-wait") as HTMLElement | null; return !!w && /tap to retry now/.test(w.title) && typeof w.onclick === "function"; }, null, { timeout: 10000 });
  return { page, errors, pic, render, shown };
}

test("in a browser, the chat's svg preview under the chat page's sheet: a tap on the retrying swirl pulses the wait element it is on, which stays still under reduced motion; the tap's managed fetch lands and the picture loads from its /file address beside the one swirl, the wait element carrying no retry title, no pointer cursor and no tap handler while it loads", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors, pic, shown } = await chatPage(browser);
    // the tap on the retrying swirl: the class ackTap adds, and the animation the sheet runs for it; its managed fetch answers, and
    // the picture's own request is held
    pic.mode = "hold";
    const tap = await page.evaluate(() => {
      const wait = document.querySelector("#box1 .path-full-wait") as HTMLElement;
      wait.click();
      return { flash: wait.classList.contains("path-retry-flash"), animation: getComputedStyle(wait).animationName };
    });
    assert.deepEqual(tap, { flash: true, animation: "path-retry-flash" }, "the tap on the retrying swirl pulses the wait element it is on (before: the class had no rule there, and nothing on screen changed)");
    const motion = async (reduced: boolean): Promise<string> => {
      await page.emulateMedia({ reducedMotion: reduced ? "reduce" : "no-preference" });
      return page.evaluate(() => { const s = document.createElement("span"); s.className = "path-full-wait path-retry-flash"; document.body.appendChild(s); const a = getComputedStyle(s).animationName; s.remove(); return a; });
    };
    assert.equal(await motion(true), "none", "under reduced motion the pulse stays still, as the chip's and the note's do");
    assert.equal(await motion(false), "path-retry-flash", "and runs otherwise");
    await page.waitForFunction(() => !!document.querySelector("#box1 img.path-full-img.path-img-loading"), null, { timeout: 10000 });
    const loading = await page.evaluate(() => {
      const b = document.getElementById("box1")!;
      const wait = b.querySelector(".path-full-wait") as HTMLElement | null;
      const img = b.querySelector("img.path-full-img") as HTMLImageElement;
      return { wait: !!wait, swirls: b.querySelectorAll(".path-load-spin").length, title: wait ? wait.title : null, cursor: wait ? getComputedStyle(wait).cursor : null,
        tap: !!(wait && wait.onclick), src: img.getAttribute("src"), note: wait ? (wait.querySelector(".path-load-note")?.textContent ?? null) : null };
    });
    assert.equal(loading.wait, true, "the picture loads beside the wait element");
    assert.equal(loading.swirls, 1, "and its one swirl");
    assert.equal(loading.src, ADDRESS, "from its /file address");
    assert.equal(loading.title, "loading preview…", "the wait element's title says the picture is loading, with no retry wording (before: the failure's tap to retry now)");
    assert.notEqual(loading.cursor, "pointer", "no pointer cursor while the picture loads");
    assert.equal(loading.tap, false, "and no tap handler: a tap there would start nothing new");
    assert.equal(loading.note, "", "the note carries no transfer progress");
    pic.mode = "ok";
    pic.release();
    await shown("box1");
    const urls: string[] = await page.evaluate(() => (window as any).__objectUrls);
    assert.ok(!urls.includes("image/svg+xml"), "no object URL made for the svg: " + JSON.stringify(urls));
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser, the chat's svg preview: the loading cue is keyed on the picture itself; a re-render while the page holds the loaded picture finds it complete once its src is set and shows it at once with no cue, and a re-render after the page has let it go (a forced garbage collection) finds it not complete and waits beside the swirl until its load", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors, pic, render, shown } = await chatPage(browser);
    pic.mode = "ok";
    await page.evaluate(() => { (window as any).FV.retryFailedPreviews(); });   // a kernel message: the retrying box's managed fetch lands, and its picture loads
    await shown("box1");
    // a re-render while the page holds the loaded picture: complete once its src is set, so no cue
    const kept = await render("box2");
    t.diagnostic("re-render while the page holds the picture: " + JSON.stringify(kept));
    assert.equal(kept.src, ADDRESS, "the re-render's picture is the /file address");
    assert.equal(kept.completeAtSrc, true, "the page holds the loaded picture: complete once its src is set");
    assert.deepEqual({ cue: kept.cue, swirls: kept.swirls, loading: kept.loading }, { cue: false, swirls: 0, loading: false }, "so the re-render shows it at once, with no cue");
    // the page lets the picture go: the turn's boxes leave the document, the next kernel message's retry lets go of any it held
    // (render.ts runs it on every message; a box off the page is dropped, not rebuilt), and a garbage collection runs
    await page.evaluate(() => { document.getElementById("msgs")!.replaceChildren(); (window as any).FV.retryFailedPreviews(); });
    await frames(page, 2);
    await forceGc(page);
    const reqs = pic.reqs;
    const later = await render("box3");
    t.diagnostic("re-render after the page let the picture go: " + JSON.stringify(later));
    assert.equal(later.src, ADDRESS, "the re-render's picture is the /file address");
    assert.equal(later.completeAtSrc, false, "the premise: after the garbage collection the page no longer holds the picture, which is not complete once its src is set");
    assert.deepEqual({ cue: later.cue, swirls: later.swirls, loading: later.loading }, { cue: true, swirls: 1, loading: true }, "so the re-render shows the cue: the swirl beside the picture, hidden until its load (before: no swirl, the cue keyed on the address having loaded once)");
    await shown("box3");
    assert.equal(pic.reqs, reqs + 1, "the re-render's picture asked the network once, and its load took the cue away");
    const urls: string[] = await page.evaluate(() => (window as any).__objectUrls);
    assert.ok(!urls.includes("image/svg+xml"), "no object URL made for the svg: " + JSON.stringify(urls));
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});
