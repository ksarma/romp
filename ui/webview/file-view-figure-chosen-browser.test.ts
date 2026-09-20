// A figure's open reads the candidate the browser chose (plans/markdown-viewer.md, "Follow-on: Link navigation", L3 and L6;
// the review's round 2) over the REAL viewer in headless Chromium (real-viewer-leg.ts: the chat modal, file-view.ts bundled
// from this tree, styles.css, the page's fetch stub for the viewer's own /file requests and a route for the figures' own). A
// synthetic report holds a `<picture>` whose `<source>` names one local file over an img src naming another, an img whose
// srcset's 1x candidate names a third over that same src, and a remote `<picture>` on an unlisted host (gated) whose source
// and src are two addresses. Read off the DOM, the routes and the page's fetch: the paint asked the kernel for the two chosen
// candidates and never for the src; the control on the <picture> opens the source's file (the bar names it; FAILS BEFORE:
// the src's file, which the paint never requested) through one GET of the URL the paint fetched the figure through; the plain
// click on the srcset figure opens its candidate the same way; a Ctrl-click hands window.open the /file URL of the candidate;
// the gated remote picture, once loaded, fetched its source alone (one request of type image, none while it was gated and
// none at the open), and its control and its plain click each open a NEW TOP-LEVEL TAB at that address, observed as one
// request of type document at a context-level route with the REAL window.open running (FAILS BEFORE: the src's address, one
// the page never requested; and the round-2 review: a leg that stubs window.open reads the string the code passed and not a
// request, so the tab's own document request, the one that carries the host's cookies, was never observed), with nothing else
// asked of the host. Skips LOUDLY
// without a playwright browser (CI installs none). Synthetic values only: the notes-api world, a placeholder session id,
// example.invalid addresses, /repo/notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, ROOT, REPORT, SID, ORIGIN, PARA } from "./real-viewer-leg";
import type { Served } from "./real-viewer-leg";

const FIGS = ROOT + "/docs/figs/";
const PLOT = FIGS + "plot.svg";        // the fallback src of both local figures: there and decodable, never asked for
const PLOT2 = FIGS + "plot2.svg";      // the <picture>'s source: the candidate the browser shows
const PLOT3 = FIGS + "plot3.svg";      // the srcset's 1x candidate: the candidate the browser shows
const REMOTE_A = "https://example.invalid/a.svg";   // the remote picture's source: the address the browser fetches
const REMOTE_B = "https://example.invalid/b.svg";   // its img src: an address the page never requests
const svg = (fill: string): string => '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200"><rect width="300" height="200" fill="' + fill + '"/></svg>';
const REPORT_TEXT = ["# Report", "",
  '<picture><source srcset="figs/plot2.svg"><img src="figs/plot.svg" alt="picture"></picture>', "",
  '<img src="figs/plot.svg" srcset="figs/plot3.svg 1x" alt="dense">', "",
  '<picture><source srcset="' + REMOTE_A + '"><img src="' + REMOTE_B + '" alt="remote"></picture>', "",
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

type Ctl = { alt: string; control: boolean; gated: boolean; shown: string; before: string | null };
/** Every img of the Rendered box: the control after its anchor (the img, its picture, the wrap or the link holding it), and currentSrc. */
const controls = (page: any): Promise<Ctl[]> => page.evaluate(() => {
  const box = document.querySelector(".fileview-md")!;
  return Array.from(box.querySelectorAll("img")).map((img) => {
    let a: Element = img;
    for (let p = a.parentElement; p && (p.localName === "a" || p.classList.contains("fc-imgwrap") || p.localName === "picture"); p = a.parentElement) a = p;
    const n = a.nextElementSibling;
    const c = n && n.hasAttribute("data-fv-figopen") ? n : null;
    return { alt: img.getAttribute("alt") || "", control: !!c, gated: !!img.closest('[data-act="fv-load"]'), shown: (img as HTMLImageElement).currentSrc || "", before: c ? c.previousElementSibling!.localName : null };
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
/** The next page the context opens (window.open's tab, opener or not), and its URL once loaded; the tab is closed after the read. */
async function nextTab(page: any, act: () => Promise<unknown>): Promise<string> {
  const [tab] = await Promise.all([page.context().waitForEvent("page", { timeout: 10000 }), act()]);
  await tab.waitForLoadState();
  const url = tab.url();
  await tab.close();
  return url;
}

test("in a browser: a <picture> figure and a srcset figure open the candidate the browser showed, through the URL the paint fetched it by, never the fallback src; a remote <picture> makes no request while gated, one image request at its load, and its control and its plain click each make exactly one document request at that address (a new top-level tab, the real window.open), never its src", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    asked.length = 0;
    // every request to the remote host, from this page or from a tab it opens, with its type: the context's route sees both
    const remote: string[] = [];
    const { page, errors } = await openViewer(browser, "chat", 900, 600, { docs: DOCS, serve });
    await page.context().route((u: URL) => u.href.startsWith("https://example.invalid/"), (route: any) => {
      const r = route.request();
      remote.push(r.resourceType() + " " + r.url());
      if (r.resourceType() === "document") return route.fulfill({ status: 200, contentType: "text/html", body: "<!DOCTYPE html><title>elsewhere</title>" });
      return route.fulfill({ status: 200, contentType: "image/svg+xml", body: svg("#333") });
    });
    await page.evaluate(() => {
      const w = window as any;
      w.__realOpen = window.open;   // kept for the remote picture below, whose tab is observed as a request and not as a stubbed string
      w.__opened = []; window.open = ((u: unknown) => { w.__opened.push(String(u)); return { opener: null }; }) as unknown as typeof window.open;
      const f = window.fetch; w.__fetched = [];
      window.fetch = function (u: any, i?: any) { w.__fetched.push({ u: String(u), m: (i && i.method) || "GET" }); return f.call(window, u, i); } as typeof window.fetch;
    });
    // every local figure's load, before anything is read
    await page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).filter((i) => !i.closest('[data-act="fv-load"]')).every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 10000 });
    await frames(page, 2);
    // the paint: the browser took the <source> and the 1x candidate, and asked the kernel for those two files alone
    const c = await controls(page);
    assert.deepEqual(c.map((x) => [x.alt, x.control, x.gated, leaf(x.shown)]), [["picture", true, false, "plot2.svg"], ["dense", true, false, "plot3.svg"], ["remote", false, true, ""]],
      "currentSrc names the candidate shown; the two local figures wear the control, the gated one none yet");
    assert.deepEqual(asked.map(leaf).sort(), ["plot2.svg", "plot3.svg"], "the paint asked for the two chosen candidates and never for plot.svg: " + JSON.stringify(asked));
    assert.deepEqual(remote, [], "zero requests to the remote host at the open: the gate holds");
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
    // the remote picture: the real window.open from here on (the stub above was for the /file tab, which this page's route serves;
    // a tab at the remote host is served by the context's route and observed there), no request while gated, its load fetching
    // the <source> alone; the control and the plain click each open a top-level tab at that address, one document request each.
    // FAILS BEFORE: b.svg, the src, an address the page never requested
    await page.evaluate(() => { const w = window as any; window.open = w.__realOpen; });
    assert.deepEqual(remote, [], "none while gated: nothing has left for the host through the local opens either");
    await page.evaluate(() => { document.querySelector('[data-act="fv-load"]')!.scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    await page.click('[data-act="fv-load"]');
    await page.waitForFunction(() => { const i = document.querySelectorAll(".fileview-md img")[2] as HTMLImageElement; const a = i.parentElement!; return !i.closest('[data-act="fv-load"]') && i.complete && i.naturalWidth > 0 && a.localName === "picture" && !!(a.nextElementSibling && a.nextElementSibling.hasAttribute("data-fv-figopen")); }, null, { timeout: 10000 });
    await frames(page, 2);   // the picture's box replacing the placeholder's settles the layout the control sits on
    const c2 = await controls(page);
    assert.deepEqual([c2[2].control, c2[2].gated, c2[2].before, c2[2].shown], [true, false, "picture", REMOTE_A], "loaded: the control stands after the picture, and the browser shows the source");
    assert.deepEqual(remote, ["image " + REMOTE_A], "the load made exactly one request of type image, for the source alone");
    // the control: a new top-level tab (the context's page event), its loaded URL the address, and exactly one document request
    const tab1 = await nextTab(page, () => page.locator(".fileview-md [data-fv-figopen]").nth(2).click());
    assert.equal(tab1, REMOTE_A, "the control's tab loaded the address the page fetched");
    assert.deepEqual(remote, ["image " + REMOTE_A, "document " + REMOTE_A], "one request of type document, the tab's own");
    assert.equal(await base(page), "report.md", "never in the viewer");
    assert.deepEqual(await opened(page), [], "the stub is out of the way: nothing recorded there");
    await page.evaluate(() => { document.querySelectorAll(".fileview-md img")[2].scrollIntoView({ block: "center" }); });
    await frames(page, 1);
    const r = await boxOf(page, ".fileview-md img", 2);
    const tab2 = await nextTab(page, () => page.mouse.click(r.left + r.width * 0.3, r.top + r.height * 0.6));
    assert.equal(tab2, REMOTE_A, "the plain click's tab loaded the same address");
    assert.deepEqual(remote, ["image " + REMOTE_A, "document " + REMOTE_A, "document " + REMOTE_A], "one more document request, the second tab's; b.svg was never asked of the host");
    assert.equal(await base(page), "report.md");
    assert.equal(remote.filter((x: string) => x.startsWith("image ")).length, 1, "one image request in all: the load's");   // the parameter typed: strict deepEqual's assertion signature narrows `remote` above
    assert.equal(remote.filter((x: string) => x.endsWith(REMOTE_B)).length, 0, "the src's address left for the host in no request");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});
