// A figure's open reads the candidate the browser chose (plans/markdown-viewer.md, "Follow-on: Link navigation", L3 and L6;
// the review's round 2) over the REAL viewer in headless Chromium (real-viewer-leg.ts: the chat modal, file-view.ts bundled
// from this tree, styles.css, the page's fetch stub for the viewer's own /file requests and a route for the figures' own). A
// synthetic report holds a `<picture>` whose `<source>` names one local file over an img src naming another, an img whose
// srcset's 1x candidate names a third over that same src, a remote `<picture>` on an unlisted host (gated) whose source and
// src are two addresses, and a remote img of that host whose picture the host answers 404 for (a FAILED figure once the gate
// is lifted). Read off the DOM, the routes and the page's fetch: the paint asked the kernel for the two chosen candidates and
// never for the src; the control on the <picture> opens the source's file (the bar names it; FAILS BEFORE: the src's file,
// which the paint never requested) through one GET of the URL the paint fetched the figure through; the plain click on the
// srcset figure opens its candidate the same way; a Ctrl-click hands window.open the /file URL of the candidate; the gated
// remote figures, once loaded, fetched their sources alone (two requests of type image, none while gated and none at the open),
// and the loaded picture's control, its plain click AND its Ctrl-click (the file review, extra5-3: the record named two
// gestures) each open a NEW TOP-LEVEL TAB at that address, observed as one request of type document at a context-level route
// with the REAL window.open running (FAILS BEFORE: the src's address, one the page never requested; and the file review: a leg
// that stubs window.open reads the string the code passed and not a request, so the tab's own document request, the one that
// carries the host's cookies, was never observed), with nothing else asked of the host. The FAILED remote figure wears no
// control, and its plain click and its Ctrl-click open no tab and make no request (the file review, extra5-4 with
// regression-3: figureTarget refused the fetching state alone, so a failed figure kept its target and a plain click opened a
// tab at a host whose image request had answered 404; FAILS BEFORE: one document request and a tab). Three instruments hold
// the census (the file review, extra7-1, tests-2 and tests-3): the context's route and the page's fetch wrapper are installed
// BEFORE the report is opened (openViewer's before hook), so the open's own window is watched; the fetch wrapper keeps a second,
// never-drained list of every call to a host outside the page's origin, read beside the route's counts, since the harness
// owns window.fetch and the route never sees a fetch; and the route reads each request's Cookie header, with three cookies
// seated on the host before the open (SameSite=Lax, SameSite=Strict, and SameSite=None with Secure, the class a third-party
// host sets), so which classes ride the image request and which ride the tab's document request is measured here and not
// stated (this leg's table is Chromium's; the record says so). Skips LOUDLY without a playwright browser (in CI the Test step runs before the job's Chromium install, so the leg skips there; the launch is real-viewer-leg.ts's inBrowser, the shared helper).
// Synthetic values only: the notes-api world, a placeholder session id, example.invalid addresses, /repo/notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, ROOT, REPORT, SID, ORIGIN, PARA } from "./real-viewer-leg";
import type { Served } from "./real-viewer-leg";

const FIGS = ROOT + "/docs/figs/";
const PLOT = FIGS + "plot.svg";        // the fallback src of both local figures: there and decodable, never asked for
const PLOT2 = FIGS + "plot2.svg";      // the <picture>'s source: the candidate the browser shows
const PLOT3 = FIGS + "plot3.svg";      // the srcset's 1x candidate: the candidate the browser shows
const HOST = "example.invalid";
const REMOTE_A = "https://" + HOST + "/a.svg";         // the remote picture's source: the address the browser fetches
const REMOTE_B = "https://" + HOST + "/b.svg";         // its img src: an address the page never requests
const REMOTE_MISSING = "https://" + HOST + "/missing.svg";   // the failed remote figure's src: the host answers 404
const svg = (fill: string): string => '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200"><rect width="300" height="200" fill="' + fill + '"/></svg>';
const REPORT_TEXT = ["# Report", "",
  '<picture><source srcset="figs/plot2.svg"><img src="figs/plot.svg" alt="picture"></picture>', "",
  '<img src="figs/plot.svg" srcset="figs/plot3.svg 1x" alt="dense">', "",
  '<picture><source srcset="' + REMOTE_A + '"><img src="' + REMOTE_B + '" alt="remote"></picture>', "",
  '<img src="' + REMOTE_MISSING + '" alt="broken" width="300" height="200">', "",   // the alt gives the failed figure a box to click (Chromium lays a failed img with an alt out as its text, not by its attributes)
  PARA(1), ""].join("\n");
const DOCS: Record<string, string> = { [REPORT]: REPORT_TEXT, [PLOT]: svg("#456"), [PLOT2]: svg("#654"), [PLOT3]: svg("#465") };
const FILE_URL = (p: string): string => "/file?path=" + encodeURIComponent(p) + "&sid=" + encodeURIComponent(SID);
/** The figs/ leaf of a /file URL (its path parameter); any other URL as is. */
const leaf = (u: string): string => { const m = /[?&]path=([^&]*)/.exec(u); if (!m) return u; const p = decodeURIComponent(m[1]); return p.startsWith(FIGS) ? p.slice(FIGS.length) : p; };
/** Every /file request the browser made for the figures, by URL (the route; the page's own fetch is stubbed and never reaches it). */
const asked: string[] = [];
const serve = (u: URL): Served | null => {
  if (u.pathname !== "/file") return null;
  asked.push(u.href);
  const p = u.searchParams.get("path") || "";
  return DOCS[p] !== undefined && /\.svg$/.test(p) ? { status: 200, type: "image/svg+xml", body: DOCS[p] } : null;
};

type Ctl = { alt: string; control: boolean; gated: boolean; shown: string; before: string | null; state: string };
/** Every img of the Rendered box: the control after its anchor (the img, its picture, the wrap or the link holding it), currentSrc,
 *  and the state as the viewer reads it (`complete` and `naturalWidth`). */
const controls = (page: any): Promise<Ctl[]> => page.evaluate(() => {
  const box = document.querySelector(".fileview-md")!;
  return Array.from(box.querySelectorAll("img")).map((img) => {
    let a: Element = img;
    for (let p = a.parentElement; p && (p.localName === "a" || p.classList.contains("fc-imgwrap") || p.localName === "picture"); p = a.parentElement) a = p;
    const n = a.nextElementSibling;
    const c = n && n.hasAttribute("data-fv-figopen") ? n : null;
    const i = img as HTMLImageElement;
    return { alt: img.getAttribute("alt") || "", control: !!c, gated: !!img.closest('[data-act="fv-load"]'), shown: i.currentSrc || "", before: c ? c.previousElementSibling!.localName : null,
      state: !i.complete ? "fetching" : i.naturalWidth > 0 ? "loaded" : "failed" };
  });
});
type Box = { left: number; top: number; width: number; height: number };
const boxOf = (page: any, sel: string, nth = 0): Promise<Box> => page.evaluate(([sel, nth]: [string, number]) => { const r = document.querySelectorAll(sel)[nth].getBoundingClientRect(); return { left: r.left, top: r.top, width: r.width, height: r.height }; }, [sel, nth]);
const base = (page: any): Promise<string | null> => page.locator(".fileview-base").textContent();
const backTitle = (page: any): Promise<{ title: string; disabled: string | null }> => page.evaluate(() => { const b = document.querySelector(".fileview-nav-back") as HTMLButtonElement; return { title: b.title, disabled: b.getAttribute("aria-disabled") }; });
/** The named file's paint: the bar's base name, and its body (a picture's img, or the Rendered box's first paragraph). */
async function painted(page: any, name: string): Promise<void> {
  await page.locator(".fileview-base", { hasText: name }).waitFor({ timeout: 10000 });
  await page.locator(/\.svg$/.test(name) ? "img.fileview-img" : ".fileview-md > p").first().waitFor({ timeout: 10000 });
  await frames(page, 3);
}
const opened = (page: any): Promise<string[]> => page.evaluate(() => (window as any).__opened.splice(0));
/** The GET /file requests the viewer's own fetch made since the last read, as absolute URLs (the probe's HEADs left out). */
const gotFiles = async (page: any): Promise<string[]> => {
  const got: Array<{ u: string; m: string }> = await page.evaluate(() => (window as any).__fetched.splice(0));
  return got.filter((r) => r.m === "GET" && /[?&]path=/.test(r.u)).map((r) => new URL(r.u, ORIGIN).href);
};
/** Every call of window.fetch to a host outside the page's origin since the page loaded: a list the drains above never touch
 *  (the file review, tests-2: the route cannot see a fetch, since the harness owns window.fetch, and the drained list lost
 *  entries at each drain). */
const foreignFetches = (page: any): Promise<string[]> => page.evaluate(() => (window as any).__foreign.slice());
/** The next page the context opens (window.open's tab, opener or not), and its URL once loaded; the tab is closed after the read. */
async function nextTab(page: any, act: () => Promise<unknown>): Promise<string> {
  const [tab] = await Promise.all([page.context().waitForEvent("page", { timeout: 10000 }), act()]);
  await tab.waitForLoadState();
  const url = tab.url();
  await tab.close();
  return url;
}
/** A click with Control held (mouse.click takes no modifiers option: the key is held around it). */
async function ctrlClick(page: any, x: number, y: number): Promise<void> {
  await page.keyboard.down("Control"); await page.mouse.click(x, y); await page.keyboard.up("Control");
}

/** One request the remote host saw: its type, its URL, and the cookies it carried (the Cookie header's names, sorted). */
type Hit = { type: string; url: string; cookies: string[] };
const cookieNames = (header: string | null | undefined): string[] => (header || "").split(/;\s*/).map((c) => c.split("=")[0]).filter(Boolean).sort();
/** The census as "type URL" lines, the shape the counts read. */
const kinds = (hits: Hit[]): string[] => hits.map((h) => h.type + " " + h.url);

test("in a browser: a <picture> figure and a srcset figure open the candidate the browser showed, through the URL the paint fetched it by, never the fallback src; the remote figures make no request while gated (the route and the fetch wrapper installed before the open), two image requests at their load, and the loaded picture's control, plain click and Ctrl-click each make exactly one document request at that address (a new top-level tab, the real window.open), never its src; the failed remote figure has no control and its clicks open no tab; the image requests carried the SameSite=None cookie alone and each document request the Lax and None cookies and not the Strict one; nothing reached the host through window.fetch", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    asked.length = 0;
    // every request to the remote host, from this page or from a tab it opens, with its type and its cookies: the context's route
    // sees both, and it stands BEFORE the report is opened (openViewer's before hook), so the open's own window is watched too
    const remote: Hit[] = [];
    const tabs: string[] = [];   // every page the context opened, by URL at the event: the null after a click is read against this list
    const before = async (pg: any): Promise<void> => {
      await pg.context().addCookies([
        { name: "lax", value: "1", domain: HOST, path: "/", sameSite: "Lax" },
        { name: "strict", value: "1", domain: HOST, path: "/", sameSite: "Strict" },
        { name: "none", value: "1", domain: HOST, path: "/", sameSite: "None", secure: true },   // SameSite=None needs Secure, hence the https host
      ]);
      pg.context().on("page", (p: any) => { tabs.push(p.url()); });
      await pg.context().route((u: URL) => u.href.startsWith("https://" + HOST + "/"), async (route: any) => {
        const r = route.request();
        const headers = await r.allHeaders();
        remote.push({ type: r.resourceType(), url: r.url(), cookies: cookieNames(headers["cookie"]) });
        if (r.resourceType() === "document") return route.fulfill({ status: 200, contentType: "text/html", body: "<!DOCTYPE html><title>elsewhere</title>" });
        if (r.url() === REMOTE_MISSING) return route.fulfill({ status: 404, contentType: "text/plain", body: "no such picture" });
        return route.fulfill({ status: 200, contentType: "image/svg+xml", body: svg("#333") });
      });
      await pg.evaluate((origin: string) => {
        const w = window as any;
        w.__realOpen = window.open;   // kept for the remote picture below, whose tab is observed as a request and not as a stubbed string
        w.__opened = []; window.open = ((u: unknown) => { w.__opened.push(String(u)); return { opener: null }; }) as unknown as typeof window.open;
        const f = window.fetch; w.__fetched = []; w.__foreign = [];
        window.fetch = function (u: any, i?: any) {
          const s = String(u); const m = (i && i.method) || "GET";
          w.__fetched.push({ u: s, m });
          if ((/^https?:/i.test(s) && !s.startsWith(origin)) || s.startsWith("//")) w.__foreign.push(m + " " + s);   // a call to any host but the page's own, never drained
          return f.call(window, u, i);
        } as typeof window.fetch;
      }, ORIGIN);
    };
    const { page, errors } = await openViewer(browser, "chat", 900, 600, { docs: DOCS, serve, before });
    // every local figure's load, before anything is read
    await page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).filter((i) => !i.closest('[data-act="fv-load"]')).every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 10000 });
    await frames(page, 2);
    // the paint: the browser took the <source> and the 1x candidate, and asked the kernel for those two files alone
    const c = await controls(page);
    assert.deepEqual(c.map((x) => [x.alt, x.control, x.gated, leaf(x.shown)]), [["picture", true, false, "plot2.svg"], ["dense", true, false, "plot3.svg"], ["remote", false, true, ""], ["broken", false, true, ""]],
      "currentSrc names the candidate shown; the two local figures wear the control, the two gated ones none yet");
    assert.deepEqual(asked.map(leaf).sort(), ["plot2.svg", "plot3.svg"], "the paint asked for the two chosen candidates and never for plot.svg: " + JSON.stringify(asked));
    assert.deepEqual(kinds(remote), [], "zero requests to the remote host from before the open to here: the gate holds (the route stood before the open)");
    assert.deepEqual(await foreignFetches(page), [], "and nothing asked of any other host through window.fetch either");
    const paintUrls = asked.slice();
    await gotFiles(page);   // the report's own GET and anything since: not the open's
    // the control on the <picture>: the viewer opens the <source>'s file. FAILS BEFORE: plot.svg, the src the paint never requested
    await page.locator(".fileview-md [data-fv-figopen]").nth(0).click();
    await painted(page, "plot2.svg");
    assert.equal(await base(page), "plot2.svg", "the bar names the picture shown, the <source>'s file");
    assert.deepEqual(await backTitle(page), { title: "Back to report.md", disabled: null }, "the open is the trail's push");
    const open2 = await gotFiles(page);
    assert.deepEqual(open2, [ORIGIN + FILE_URL(PLOT2)], "the open's one GET of /file is the candidate's URL");
    assert.ok(paintUrls.includes(open2[0]), "and it is the URL the paint fetched the figure through: " + JSON.stringify(paintUrls));
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    await gotFiles(page);   // the report's re-open
    // the plain click on the srcset figure: its 1x candidate, the same way
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[1].scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    const d = await boxOf(page, ".fileview-md img", 1);
    await page.mouse.click(d.left + d.width * 0.3, d.top + d.height * 0.6);   // away from the control's corner
    await painted(page, "plot3.svg");
    assert.equal(await base(page), "plot3.svg", "the plain click opens the srcset candidate shown");
    const open3 = await gotFiles(page);
    assert.deepEqual(open3, [ORIGIN + FILE_URL(PLOT3)], "one GET, the candidate's URL");
    assert.ok(paintUrls.includes(open3[0]), "the paint's URL for that figure");
    await page.click(".fileview-nav-back");
    await painted(page, "report.md");
    // a Ctrl-click on the <picture>'s control: the /file URL of the candidate shown, in a tab; the viewer stays
    await page.locator(".fileview-md [data-fv-figopen]").nth(0).click({ modifiers: ["Control"] });
    await frames(page, 2);
    assert.deepEqual(await opened(page), [FILE_URL(PLOT2)], "the tab's URL is the candidate's, not the src's");
    assert.equal(await base(page), "report.md", "the viewer still shows the report");
    // the remote figures: the real window.open from here on (the stub above was for the /file tab, which this page's route serves;
    // a tab at the remote host is served by the context's route and observed there), no request while gated, the placeholder's
    // click loading every figure of the host: the <picture> fetches its <source> alone and the broken img its src, which the host
    // answers 404, so one figure is loaded and the other failed. FAILS BEFORE: b.svg, the src, an address the page never requested
    await page.evaluate(() => { const w = window as any; window.open = w.__realOpen; });
    assert.deepEqual(kinds(remote), [], "none while gated: nothing has left for the host through the local opens either");
    assert.deepEqual(await foreignFetches(page), [], "nor through window.fetch");
    await page.evaluate(() => { document.querySelector('[data-act="fv-load"]')!.scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    await page.click('[data-act="fv-load"]');
    await page.waitForFunction(() => {
      const imgs = document.querySelectorAll(".fileview-md img");
      const i = imgs[2] as HTMLImageElement; const a = i.parentElement!; const b = imgs[3] as HTMLImageElement;
      return !i.closest('[data-act="fv-load"]') && i.complete && i.naturalWidth > 0 && a.localName === "picture" && !!(a.nextElementSibling && a.nextElementSibling.hasAttribute("data-fv-figopen"))
        && !b.closest('[data-act="fv-load"]') && b.complete && b.naturalWidth === 0;
    }, null, { timeout: 10000 });
    await frames(page, 2);   // the pictures' boxes replacing the placeholders' settle the layout the control sits on
    const c2 = await controls(page);
    assert.deepEqual([c2[2].control, c2[2].gated, c2[2].before, c2[2].shown, c2[2].state], [true, false, "picture", REMOTE_A, "loaded"], "loaded: the control stands after the picture, and the browser shows the source");
    assert.deepEqual([c2[3].control, c2[3].gated, c2[3].state], [false, false, "failed"], "the broken figure failed and wears no control");
    assert.deepEqual(kinds(remote).sort(), ["image " + REMOTE_A, "image " + REMOTE_MISSING], "the load made exactly two requests of type image, one per figure, for the source and the src alone");
    assert.equal(remote.filter((h) => h.type === "document").length, 0, "no document request yet");
    // the FAILED figure: no control (above), and its plain click and its Ctrl-click open no tab and make no request. FAILS BEFORE: a
    // plain click opened a tab at missing.svg, one document request to a host whose image request had answered 404
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[3].scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    const broken = await boxOf(page, ".fileview-md img", 3);
    // Chromium lays a failed img with a non-empty alt out as its alt text (67 by 22 here, measured), not as its width and height
    // attributes: a box all the same, and the click lands on the img
    assert.ok(broken.width > 0 && broken.height > 0, "the failed figure's alt gives it a box to click on: " + JSON.stringify(broken));
    const at: [number, number] = [broken.left + broken.width / 2, broken.top + broken.height / 2];
    assert.equal(await page.evaluate(([x, y]: [number, number]) => { const e = document.elementFromPoint(x, y); return e ? e.localName : ""; }, at), "img", "the img is under the point clicked");
    await page.mouse.click(at[0], at[1]);
    await frames(page, 3);
    await ctrlClick(page, at[0], at[1]);
    await frames(page, 3);
    assert.deepEqual(tabs, [], "no tab from either click on the failed figure");
    assert.equal(remote.filter((h) => h.type === "document").length, 0, "and no document request: " + JSON.stringify(kinds(remote)));
    assert.equal(await base(page), "report.md", "the viewer still shows the report");
    assert.deepEqual(await backTitle(page), { title: "Back", disabled: "true" }, "the trail did not move");
    // the loaded picture's control: a new top-level tab (the context's page event), its loaded URL the address, and exactly one
    // document request; this is the positive control for the null above (the same instrument, a tab now)
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[2].scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    const tab1 = await nextTab(page, () => page.locator(".fileview-md [data-fv-figopen]").nth(2).click());
    assert.equal(tab1, REMOTE_A, "the control's tab loaded the address the page fetched");
    assert.deepEqual(kinds(remote).filter((k) => k.startsWith("document ")), ["document " + REMOTE_A], "one request of type document, the tab's own");
    assert.equal(tabs.length, 1, "the context opened one page: the instrument that read none above reads this one");
    assert.equal(await base(page), "report.md", "never in the viewer");
    assert.deepEqual(await opened(page), [], "the stub is out of the way: nothing recorded there");
    // the plain click: the same tab
    const r = await boxOf(page, ".fileview-md img", 2);
    const tab2 = await nextTab(page, () => page.mouse.click(r.left + r.width * 0.3, r.top + r.height * 0.6));
    assert.equal(tab2, REMOTE_A, "the plain click's tab loaded the same address");
    assert.deepEqual(kinds(remote).filter((k) => k.startsWith("document ")), ["document " + REMOTE_A, "document " + REMOTE_A], "one more document request, the second tab's");
    assert.equal(await base(page), "report.md");
    // the Ctrl-click on the remote picture: the picture's own address in a tab, not the kernel's /file URL (the file review, extra5-3:
    // the record named the plain click and the control alone)
    const tab3 = await nextTab(page, () => ctrlClick(page, r.left + r.width * 0.3, r.top + r.height * 0.6));
    assert.equal(tab3, REMOTE_A, "the Ctrl-click's tab loaded the picture's own address");
    assert.deepEqual(kinds(remote).filter((k) => k.startsWith("document ")), ["document " + REMOTE_A, "document " + REMOTE_A, "document " + REMOTE_A], "a third document request, the third tab's; b.svg was never asked of the host");
    assert.equal(await base(page), "report.md");
    assert.deepEqual(await backTitle(page), { title: "Back", disabled: "true" }, "a tab pushes nothing");
    assert.equal(remote.filter((h) => h.type === "image").length, 2, "two image requests in all: the two loads'");
    assert.equal(remote.filter((h) => h.url === REMOTE_B).length, 0, "the src's address left for the host in no request");
    assert.deepEqual(await foreignFetches(page), [], "nothing asked of the host through window.fetch at any point");
    // the cookies, as measured in Chromium (the record's table): the image requests carried the SameSite=None cookie alone, a
    // cross-site subresource; each tab's document request, a cross-site top-level navigation, carried the Lax and the None cookie
    // and not the Strict one
    const table = remote.map((h) => h.type + " " + h.url.slice(h.url.lastIndexOf("/") + 1) + ": " + (h.cookies.length ? h.cookies.join(",") : "(none)"));
    t.diagnostic("cookies by request: " + table.join(" | "));
    for (const h of remote.filter((x) => x.type === "image")) assert.deepEqual(h.cookies, ["none"], "the image request " + h.url + " carried the SameSite=None cookie and neither the Lax nor the Strict one");
    for (const h of remote.filter((x) => x.type === "document")) assert.deepEqual(h.cookies, ["lax", "none"], "the tab's document request carried the Lax and the None cookie and not the Strict one");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});
