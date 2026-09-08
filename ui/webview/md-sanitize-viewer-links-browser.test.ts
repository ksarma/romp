// A note's links in the rendered file view, in BOTH document kinds, over the REAL files bundle in headless Chromium
// (plans/markdown-viewer.md, Slice 1: sanitize as GitHub does; the 2026-09-07 review). The sanitizer's svg profile keeps
// an inline SVG <a> (spelled `href` or `xlink:href`), and its html profile kept an image map's <area> until the slice
// forbade map, area and usemap (md-sanitize.ts: a prefixed map name can never bind, and GitHub drops image maps). mdBlock
// stamped target=_blank on `a[href]` only, and wrote it as a property, which an SVGAElement drops, so a click on an
// <area href> or an SVG anchor replaced the Files document with the URL, in the same frame: the defect class the slice
// closes for <form>. Two tests, one per document kind, because different code dresses their links after the shared
// sanitize (fork PR #347's split in mdBlock):
//   - a FILE document (viewFile): mdBlock copies an xlink-only href to a plain `href`, then linkMarkdownAnchors
//     (file-view-links.ts) walks every `a`, the SVG one included, and writes each stamp as an attribute. Clicked as a
//     person would: an absolute link of every surviving shape opens a new tab and location.href is unchanged; the picture
//     whose map was dropped is inert; an SVG anchor's `#fragment` scrolls to its heading; its relative `sibling.md` opens
//     the sibling in this viewer, through the same path link a relative <a> becomes.
//   - a URL document (openUrlView, the same viewer's other kind): mdBlock's OWN two passes over LINK_SEL, the resolution
//     against the document's URL and then the fv-anchor stamp or `target` and `rel` written with setAttribute. Today only
//     the chat page opens this kind (render.ts's delegate, for a same-origin .md), and that delegate opens and cancels a
//     click before the browser reads any stamp, so the stamps are the viewer's own layer and their defect never shows
//     through it. Here the document is opened in the Files page, where nothing stands in front of the browser's default
//     action: an SVG anchor whose `target` reached only the read-only property navigates this page in the same frame,
//     and the test says so. The chat page's layer is md-sanitize-chat-links-browser.test.ts's.
//   - the chat page's viewer (the render bundle, openFileView): the same FILE document under the chat's capture-phase link
//     delegate (render.ts), which keys on LINK_SEL (`a[*|href]`) and reads linkHref (`href`, else `xlink:href`). Round 3 of
//     the review: mdBlock copied an xlink-only href to `href` and left the XLink attribute in place, and linkMarkdownAnchors
//     removes `href` alone, so a path link and a dead link kept an xlink:href, which the browser follows when href is absent
//     and the delegate still matched. The relative SVG link opened http://<host>/sibling.md as a URL document (a 404 in
//     production) where the HTML one opened the sibling file, and the dead one opened a tab there and navigated the Files
//     document in the same frame. mdBlock removes the XLink spelling after the copy now, so a link is read one way by the
//     browser too; every leg here reads no xlink:href on any anchor, and the two SVG shapes are clicked in both pages.
// What a click does is read from EVENTS, never a sleep. Every synchronous consequence of a click has happened when
// page.mouse.click resolves (Chromium answers the input once the renderer has dispatched the click and run the anchor's
// activation), and both things a link click can start are on record by then: a navigation of this document fires the
// Navigation API's `navigate` event as the browser starts it (a recorder in both pages keeps the destination), and a new
// tab, opened by a followed link or by a script, is a target the browser reports (CDP Target.targetCreated) during the
// window creation the renderer waits on, so the report precedes the click's answer on the same connection (30 of 30 in a
// probe; playwright's own `page` event fires only once the tab is set up, after the answer in 30 of 30). The checks that
// nothing happened read those records (clickForNothing), and a tab that must open is awaited on the context's `page` event
// once its target is on record (clickForTab); an earlier draft slept 500 ms after each of 19 clicks, 9.5 s of an 11.7 s
// leg. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do.
// Synthetic values only: an invented note, TESTHOST paths, a placeholder sid, example.invalid URLs.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { chatBody, ATTACH_TITLE_WEB } from "../../vscode-extension/src/page-skeleton";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");

const SID = "11111111-2222-3333-4444-555555555555";
const DIR = "/tmp/TESTHOST/notes-api/";
const PATH = DIR + "report.md";
const SIBLING = DIR + "sibling.md";
const URL_DIR = "http://romp.test/docs/";                         // the same note as a URL document, on the dashboard's own host
const URL_PATH = URL_DIR + "report.md";
const URL_SIBLING = URL_DIR + "sibling.md";
const CHAT_URL_SIBLING = "http://romp.test/sibling.md";             // where `sibling.md` lands when resolved against the CHAT PAGE, the wrong base
const XLINK = "http://www.w3.org/1999/xlink";
// a valid 1x1 transparent PNG: a picture that decodes, so a map that DID survive would be live (a broken image shows its
// alt text and binds no map, which would pass the image case for the wrong reason; the precondition below checks it decoded)
const PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

// each shape in its own <p> HTML block (marked passes a block opened by <p> through verbatim); the image map is spelled
// as an author spells it, the bare `usemap="#m"` against `<map name="m">`
const NOTE = [
  "# Figure",
  "",
  '<p>A <a href="https://example.invalid/ctl" class="fx-a">plain link</a> in prose.</p>',
  "",
  `<p><img src="${PNG}" width="240" height="40" usemap="#m" alt="map" class="fx-img"><map name="m"><area shape="rect" coords="0,0,240,40" href="https://example.invalid/area" alt="go"></map></p>`,
  "",
  '<p><svg width="240" height="40" class="fx-svg-href"><a href="https://example.invalid/svg"><text x="4" y="30" font-size="24">svg href</text></a></svg></p>',
  "",
  `<p><svg width="240" height="40" class="fx-svg-xlink" xmlns:xlink="${XLINK}"><a xlink:href="https://example.invalid/xlink"><text x="4" y="30" font-size="24">svg xlink</text></a></svg></p>`,
  "",
  `<p><svg width="240" height="40" class="fx-svg-frag" xmlns:xlink="${XLINK}"><a xlink:href="#tail"><text x="4" y="30" font-size="24">to the tail</text></a></svg></p>`,
  "",
  '<p><svg width="240" height="40" class="fx-svg-rel"><a href="sibling.md"><text x="4" y="30" font-size="24">to the sibling</text></a></svg></p>',
  "",
  // the same two destinations spelled xlink:href, whose stamps take the href OFF the anchor (a path link, a dead link), plus the
  // HTML control for the dead one: a host with a port, which reads as a scheme and is dressed dead (file-view-links.ts)
  `<p><svg width="240" height="40" class="fx-svg-xlink-rel" xmlns:xlink="${XLINK}"><a xlink:href="sibling.md"><text x="4" y="30" font-size="24">xlink to the sibling</text></a></svg></p>`,
  "",
  `<p><svg width="240" height="40" class="fx-svg-xlink-dead" xmlns:xlink="${XLINK}"><a xlink:href="127.0.0.1:3000"><text x="4" y="30" font-size="24">xlink to a port</text></a></svg></p>`,
  "",
  '<p><a href="127.0.0.1:3000" class="fx-a-dead">a port</a> in prose.</p>',
  "",
  ...Array.from({ length: 60 }, (_, i) => "Paragraph " + (i + 1) + " of the tail, so the fragment link has somewhere to go.\n"),
  "",
  "## Tail",
  "",
  // enough below the heading that it can reach the top of the body (a heading at the very end stops short of it)
  ...Array.from({ length: 40 }, (_, i) => "Tail paragraph " + (i + 1) + ".\n"),
  "",
  "The end.",
  "",
].join("\n");
const SIBLING_NOTE = "# Sibling\n\nOpened in the viewer.\n";
const URL_SIBLING_NOTE = "# URL Sibling\n\nFetched as a URL document.\n";   // a different heading, so the leg can say which document opened

// the three shapes an absolute href can take in a sanitized note, and where each must open
const ABSOLUTE = [
  { name: "the HTML anchor (control)", sel: ".fx-a", href: "https://example.invalid/ctl" },
  { name: "the SVG anchor with href", sel: ".fx-svg-href text", href: "https://example.invalid/svg" },
  { name: "the SVG anchor with xlink:href", sel: ".fx-svg-xlink text", href: "https://example.invalid/xlink" },
];

/** The Files pane's bundle, plus openUrlView handed to the page (file-view-links-browser.test.ts's idiom): the same viewer's
 *  URL kind, which the Files page never opens itself, called directly so its links meet the browser with no delegate in front. */
let filesJs: string | null = null;
function bundle(): string {
  if (filesJs !== null) return filesJs;
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'import "./files";\nimport { openUrlView } from "./file-view";\n(window as any).__rompProbe = { openUrlView };\n', resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  const text = r.outputFiles[0].text as string;
  filesJs = text;
  return text;
}
// the Files page as the kernel serves it (_files_page): the chat's styles.css for the viewer's dress, files-pane.css
// after it for the pane layout, a fake acquireVsCodeApi (the shim's role), the navigation recorder (the header above),
// then the files bundle
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane>
<div id=files-empty></div>
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};
window.__navStarts=[];navigation.addEventListener("navigate",function(e){window.__navStarts.push(e.destination.url);});</script>
<script src=/dist/files.js></script></body></html>`;

/** The chat page's bundle (render.ts hosts the same viewer, for the todo card's path links and a same-origin .md), plus
 *  openFileView handed to the page: a FILE document opened in the chat page's viewer, where the chat's capture-phase link
 *  delegate runs in front of the viewer's own click listener. */
let renderJs: string | null = null;
function chatBundle(): string {
  if (renderJs !== null) return renderJs;
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'import "./render";\nimport { openFileView } from "./file-view";\n(window as any).__rompProbe = { openFileView };\n', resolveDir: UI, loader: "ts", sourcefile: "render-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  renderJs = r.outputFiles[0].text as string;
  return renderJs;
}
// the chat page as the web dashboard serves it: the shared skeleton, the chat's sheet, a fake acquireVsCodeApi, window.open
// recorded instead of opened (what the chat's delegate hands it is the evidence), the navigation recorder, then the chat bundle
const CHAT_HTML = `<!DOCTYPE html><html lang=en><head><meta charset=utf-8><style>${STYLES}</style></head><body>
${chatBody(ATTACH_TITLE_WEB)}
<script>window.__opens=[];window.open=function(u,t,f){window.__opens.push([u,t,f]);return null;};
window.acquireVsCodeApi=function(){return{postMessage:function(){}}};
window.__navStarts=[];navigation.addEventListener("navigate",function(e){window.__navStarts.push(e.destination.url);});</script>
<script src=/dist/render.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Watch = { errors: string[]; navs: string[]; popups: string[]; tabs: string[]; fileRequests: string[]; docRequests: string[] };

/** The note open in the viewer: in the Files page as a FILE document (viewFile, the pane's own route) or as a URL document
 *  (openUrlView), or in the CHAT page as a file document (openFileView, the render bundle). */
async function inBrowser(t: any, kind: "file" | "url" | "chat", body: (page: any, w: Watch) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box: the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const w: Watch = { errors: [], navs: [], popups: [], tabs: [], fileRequests: [], docRequests: [] };
  try {
    // every page target the browser creates, on record before the click that created it is answered (the header above);
    // cleared once the note is shown, so it holds the tabs the clicks open
    const cdp = await browser.newBrowserCDPSession();
    cdp.on("Target.targetCreated", (e: any) => { if (e.targetInfo.type === "page") w.tabs.push(e.targetInfo.url); });
    await cdp.send("Target.setDiscoverTargets", { discover: true });
    const onChat = kind === "chat";
    // the page and its bundle, by pathname
    const pages: Record<string, { type: string; body: string }> = onChat
      ? { "/chat": { type: "text/html; charset=utf-8", body: CHAT_HTML }, "/dist/render.js": { type: "application/javascript", body: chatBundle() } }
      : { "/files": { type: "text/html; charset=utf-8", body: FILES_HTML }, "/dist/files.js": { type: "application/javascript", body: bundle() } };
    const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
    page.on("pageerror", (e: Error) => { w.errors.push(e.message); });
    page.on("framenavigated", (f: any) => { if (f === page.mainFrame()) w.navs.push(f.url()); });
    page.context().on("page", (p: any) => { w.popups.push(p.url()); });
    // the whole context, so a new tab's request is answered from memory too and nothing reaches the network; a host other
    // than the dashboard's answers with a marker page, so a same-frame navigation (the defect) is unmistakable in the body
    await page.context().route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.hostname !== "romp.test") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: "EXTERNAL " + u.href });
      const served = pages[u.pathname];
      if (served) return route.fulfill({ status: 200, contentType: served.type, body: served.body });
      if (u.pathname === "/file") {                                 // the file kind's fetch: what the kernel serves for a text file
        const p = u.searchParams.get("path") || "";
        w.fileRequests.push(p);
        const text = p === PATH ? NOTE : p === SIBLING ? SIBLING_NOTE : null;
        if (text !== null) return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: text });
      }
      if (u.href === URL_PATH || u.href === URL_SIBLING || u.href === CHAT_URL_SIBLING) {   // the URL kind's fetch, a tab opened at the sibling, or the sibling resolved against the chat page
        w.docRequests.push(u.href);
        return route.fulfill({ status: 200, contentType: "text/markdown; charset=utf-8", body: u.href === URL_PATH ? NOTE : u.href === URL_SIBLING ? SIBLING_NOTE : URL_SIBLING_NOTE });
      }
      return route.fulfill({ status: 404, contentType: "text/html; charset=utf-8", body: "NOTFOUND " + u.href });
    });
    await page.goto(onChat ? "http://romp.test/chat" : "http://romp.test/files");
    await page.waitForFunction(() => !!(window as any).__rompProbe);
    if (kind === "file") await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [PATH, SID] as [string, string]);
    else if (kind === "url") await page.evaluate((u: string) => { (window as any).__rompProbe.openUrlView(u); }, URL_PATH);
    else await page.evaluate(([p, sid]: [string, string]) => { (window as any).__rompProbe.openFileView(p, sid); }, [PATH, SID] as [string, string]);
    await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 10000 });
    w.tabs.length = 0;
    await body(page, w);
  } finally {
    await browser.close();
  }
}

/** Scroll `sel` (inside the rendered note) into view; its centre, where a person would click. */
async function centreOf(page: any, sel: string): Promise<{ x: number; y: number }> {
  const box = await page.evaluate((s: string) => {
    const e = document.querySelector("#romp-fileview .fileview-md " + s);
    if (!e) return null;
    e.scrollIntoView({ block: "center" });
    const r = e.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height };
  }, sel);
  assert.ok(box && box.w > 0 && box.h > 0, sel + " is laid out in the note: " + JSON.stringify(box));
  return box;
}

/** The main frame's next navigation, armed before a click: its URL, or null after 10 s (a waiter that loses resolves null
 *  instead of rejecting unheard). Awaited only when a navigation IS under way (navStarted found the document gone). */
function armNav(page: any): Promise<string | null> {
  return page.waitForEvent("framenavigated", { predicate: (f: any) => f === page.mainFrame(), timeout: 10000 }).then((f: any) => f.url() as string, () => null);
}

/** Where the answered click sent this document, from the page's own record (the `navigate` recorder in both pages; each
 *  read clears it, so a click reads only its own), or, when the document is already gone before the record can be read,
 *  from the navigation that replaced it (`navP`). With every route answered from memory a cross-document navigation
 *  commits before the read reaches the page (8 of 8 in a probe), so that is the usual path for the defect this leg guards
 *  against, and the record is the path for a same-document one (a hash change). Empty when the click stayed. */
async function navStarted(page: any, navP: Promise<string | null>): Promise<string[]> {
  try { return await page.evaluate(() => (window as any).__navStarts.splice(0) as string[]); }
  catch (e) {
    const nav = await navP;
    return [nav ? nav + " (committed before the record could be read)" : "an unknown destination (" + String((e as Error).message).split("\n")[0] + ")"];
  }
}

/** Click `sel` with the mouse and wait for the new tab it must open: its target is on record when the click is answered
 *  (w.tabs), the tab itself arrives on the context's `page` event; a click that started a navigation of this document
 *  instead (the defect), opened two tabs, or opened nothing fails by name. Returns the tab's URL once it has loaded and
 *  closes the tab. */
async function clickForTab(page: any, w: Watch, sel: string, name: string): Promise<string> {
  const at = await centreOf(page, sel);
  const tabs0 = w.tabs.length;
  // armed before the click; the tab's `page` event comes after the click is answered (playwright sets the tab up first)
  const tabP = page.context().waitForEvent("page", { timeout: 10000 }).then((p: any) => p, () => null);
  const navP = armNav(page);
  await page.mouse.click(at.x, at.y);
  const started = await navStarted(page, navP);
  assert.deepEqual(started, [], name + ": the click navigated this document in the same frame instead of opening a new tab");
  const opened = w.tabs.slice(tabs0);
  if (opened.length === 0) assert.fail(name + ": no new tab and no navigation when the click was answered: the link is inert");
  assert.equal(opened.length, 1, name + ": one new tab, not " + opened.length + ": " + JSON.stringify(opened));
  const tab = await tabP;
  if (!tab) assert.fail(name + ": the tab's target is on record, but no page arrived within 10 s");
  await tab.waitForLoadState();
  const url: string = tab.url();
  await tab.close();
  return url;
}

/** Click `sel` with the mouse when the click must open nothing and go nowhere, and read that from the click's own record
 *  once it is answered: no navigation of this document started (navStarted), no tab's target was created (w.tabs). */
async function clickForNothing(page: any, w: Watch, sel: string): Promise<void> {
  const at = await centreOf(page, sel);
  const tabs0 = w.tabs.length;
  const navP = armNav(page);
  await page.mouse.click(at.x, at.y);
  const started = await navStarted(page, navP);
  assert.deepEqual(started, [], sel + ": the click started a navigation of this document");
  assert.deepEqual(w.tabs.slice(tabs0), [], sel + ": the click opened a tab");
}

type LinkFacts = { tag: string; ns: string | null; href: string | null; xlink: string | null; target: string | null; rel: string | null; act: string | null; path: string | null; frag: string | null; cls: string; title: string | null };
/** Every link element left in the note, with the stamps on it, plus the picture and what is left of its map. */
function readFacts(XL: string): { links: LinkFacts[]; imgs: { usemap: string | null; decoded: boolean }[]; maps: number; areas: number } {
  const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
  const links = Array.from(md.querySelectorAll("a, area")).map((n) => {
    const a = n as HTMLElement | SVGElement;
    return { tag: a.tagName.toLowerCase(), ns: a.namespaceURI, href: a.getAttribute("href"), xlink: a.getAttributeNS(XL, "href"),
             target: a.getAttribute("target"), rel: a.getAttribute("rel"), act: a.dataset.act ?? null, path: a.dataset.path ?? null, frag: a.dataset.frag ?? null,
             cls: a.getAttribute("class") || "", title: a.getAttribute("title") };
  });
  const imgs = Array.from(md.querySelectorAll("img")).map((i) => ({ usemap: i.getAttribute("usemap"), decoded: i.complete && i.naturalWidth > 0 }));
  return { links, imgs, maps: md.querySelectorAll("map").length, areas: md.querySelectorAll("area").length };
}
const SVG = "http://www.w3.org/2000/svg", HTML = "http://www.w3.org/1999/xhtml";

/** The Tail heading's place after a fragment click: the body scrolled, the heading at its top. */
function readLanding(): { scrollTop: number; tailTop: number; bodyHeight: number } {
  const body = document.querySelector("#romp-fileview .fileview-body") as HTMLElement;
  const tail = document.querySelector("#romp-fileview .fileview-md h2#md-tail") as HTMLElement;
  return { scrollTop: body.scrollTop, tailTop: tail.getBoundingClientRect().top - body.getBoundingClientRect().top, bodyHeight: body.clientHeight };
}

test("a FILE document: every link shape keeps the Files document: a new tab for an absolute href, a scroll for a fragment, the viewer for a sibling; an image map is dropped and its picture is inert", { timeout: 90000 }, async (t) => {
  await inBrowser(t, "file", async (page, w) => {
    const START = page.url();
    // the image decoded: a map that survived WOULD be live, so the inert click below is the sanitizer's doing, not a broken image's
    await page.waitForFunction(() => Array.from(document.querySelectorAll("#romp-fileview .fileview-md img")).every((i) => (i as HTMLImageElement).complete), null, { timeout: 5000 });

    // 1. an absolute href of every surviving shape: a click opens a new tab at the link's URL and the Files document stays where it was
    for (const c of ABSOLUTE) {
      const popups0 = w.popups.length, navs0 = w.navs.length;
      const tabUrl = await clickForTab(page, w, c.sel, c.name);
      assert.equal(tabUrl, c.href, c.name + ": the new tab is at the link's URL");
      assert.equal(page.url(), START, c.name + ": location.href is unchanged after the click");
      assert.deepEqual(w.navs.slice(navs0), [], c.name + ": no main-frame navigation");
      assert.equal(w.popups.length - popups0, 1, c.name + ": one new tab, not two");
      assert.ok(await page.evaluate(() => !!document.querySelector("#romp-fileview .fileview-md")), c.name + ": the note is still on screen");
    }
    // ...and the picture whose image map the sanitizer dropped: a click on it opens nothing and moves nothing
    {
      const popups0 = w.popups.length, navs0 = w.navs.length;
      await clickForNothing(page, w, ".fx-img");
      assert.equal(page.url(), START, "the mapped picture: location.href is unchanged after the click");
      assert.deepEqual(w.navs.slice(navs0), [], "the mapped picture: no main-frame navigation");
      assert.equal(w.popups.length, popups0, "the mapped picture: no new tab, the map is gone");
    }

    // 2. the SVG anchor's #fragment lands on its heading in this body: no tab, no navigation, a scroll
    const popups1 = w.popups.length, navs1 = w.navs.length;
    await page.evaluate(() => { (document.querySelector("#romp-fileview .fileview-body") as HTMLElement).scrollTop = 0; });
    await clickForNothing(page, w, ".fx-svg-frag text");
    const landed = await page.evaluate(readLanding);
    assert.equal(page.url(), START, "fragment: location.href is unchanged");
    assert.deepEqual(w.navs.slice(navs1), [], "fragment: no main-frame navigation");
    assert.equal(w.popups.length, popups1, "fragment: no new tab");
    assert.ok(landed.scrollTop > 0 && landed.tailTop >= -2 && landed.tailTop < 48, "the Tail heading is at the top of the body after the click: " + JSON.stringify(landed));

    // 3. what the sanitizer, mdBlock's href copy and linkMarkdownAnchors left (the stamps behind 1 and 2; read before 4 replaces
    //    the note). In a file document every stamp is the module's: mdBlock's part is the plain `href` on the xlink anchor,
    //    which is what puts that anchor in the module's walk over `a` and lets the browser follow one attribute.
    const facts = await page.evaluate(readFacts, XLINK);
    assert.deepEqual(facts.imgs, [{ usemap: null, decoded: true }], "the picture decoded, and its usemap is gone (FORBID_ATTR)");
    assert.equal(facts.maps + facts.areas, 0, "no <map> and no <area> survive the sanitizer (FORBID_TAGS): an image map is dropped as GitHub drops it");
    assert.equal(facts.links.length, 8, "eight links in the note, every one an anchor: " + JSON.stringify(facts.links));
    // no anchor carries xlink:href once mdBlock has run: the copy to `href` is followed by the XLink attribute's removal, so a
    // stamp that takes `href` off (a path link, a dead link) leaves the browser nothing to follow and LINK_SEL nothing to match
    assert.deepEqual(facts.links.map((l: LinkFacts) => l.xlink), facts.links.map(() => null), "no xlink:href survives on any anchor: " + JSON.stringify(facts.links.map((l: LinkFacts) => [l.cls, l.xlink])));
    const [ctl, svgHref, svgXlink, svgFrag, svgRel, svgXlinkRel, svgXlinkDead, aDead] = facts.links;
    assert.deepEqual([ctl.tag, ctl.ns, ctl.target, ctl.rel], ["a", HTML, "_blank", "noopener"], "control: the HTML anchor, as before");
    assert.deepEqual([svgHref.tag, svgHref.ns, svgHref.target, svgHref.rel], ["a", SVG, "_blank", "noopener"],
      "an SVG <a href> is stamped like the HTML one: linkMarkdownAnchors walks every `a` and writes attributes (an SVGAElement has no target property to write)");
    assert.deepEqual([svgXlink.tag, svgXlink.ns, svgXlink.href, svgXlink.xlink, svgXlink.target, svgXlink.rel],
      ["a", SVG, "https://example.invalid/xlink", null, "_blank", "noopener"], "an SVG <a xlink:href> gets a plain href copy and loses the XLink spelling (mdBlock, before the module's walk), and the same stamps");
    assert.deepEqual([svgFrag.tag, svgFrag.href, svgFrag.frag, /\bfv-frag\b/.test(svgFrag.cls), /\bfv-dead\b/.test(svgFrag.cls), svgFrag.target], ["a", "#tail", "tail", true, false, null],
      "an SVG fragment link is a section link of this document (file-view-links.ts): live, no tab");
    assert.deepEqual([svgRel.tag, svgRel.href, svgRel.act, svgRel.path, /\bfile-uri-link\b/.test(svgRel.cls), svgRel.title, svgRel.target], ["a", null, "openpath", SIBLING, true, "Open " + SIBLING, null],
      "an SVG anchor's relative href becomes the same path link a relative <a> does: the href off, the joined path and the title on it");
    assert.deepEqual([svgXlinkRel.tag, svgXlinkRel.ns, svgXlinkRel.href, svgXlinkRel.xlink, svgXlinkRel.act, svgXlinkRel.path, /\bfile-uri-link\b/.test(svgXlinkRel.cls), svgXlinkRel.title],
      ["a", SVG, null, null, "openpath", SIBLING, true, "Open " + SIBLING], "the same relative href spelled xlink:href becomes the same path link, with NEITHER attribute left on it");
    assert.deepEqual([svgXlinkDead.tag, svgXlinkDead.ns, svgXlinkDead.href, svgXlinkDead.xlink, /\bfv-dead\b/.test(svgXlinkDead.cls), /host with a port/.test(svgXlinkDead.title || ""), svgXlinkDead.act],
      ["a", SVG, null, null, true, true, null], "a host with a port spelled xlink:href is a dead link with the reason in its title and no href in either spelling");
    assert.deepEqual([aDead.tag, aDead.ns, aDead.href, aDead.xlink, /\bfv-dead\b/.test(aDead.cls)], ["a", HTML, null, null, true], "control: the HTML anchor to the same host with a port is dead the same way");

    // 3b. the two dead links: a plain click on either opens nothing and moves nothing. The SVG one kept its xlink:href after
    //     the module removed `href`, and the browser follows xlink:href when href is absent, so the click navigated the Files
    //     document in the same frame to http://<host>/127.0.0.1:3000 (round 3 of the review); the HTML one was inert all along
    for (const [sel, name] of [[".fx-svg-xlink-dead text", "the dead SVG xlink anchor"], [".fx-a-dead", "the dead HTML anchor (control)"]] as const) {
      const popups0 = w.popups.length, navs0 = w.navs.length;
      await clickForNothing(page, w, sel);
      assert.deepEqual(w.navs.slice(navs0), [], name + ": no main-frame navigation (the browser had no xlink:href left to follow)");
      assert.equal(page.url(), START, name + ": location.href is unchanged");
      assert.equal(w.popups.length, popups0, name + ": no new tab");
      assert.ok(await page.evaluate(() => !!document.querySelector("#romp-fileview .fileview-md")), name + ": the note is still on screen");
    }

    // 4. the SVG anchor's relative `sibling.md` opens the sibling in THIS viewer, through the body's one click listener
    const popups2 = w.popups.length, navs2 = w.navs.length;
    await clickForNothing(page, w, ".fx-svg-rel text");
    await page.waitForSelector("#romp-fileview .fileview-md h1#md-sibling", { timeout: 10000 });
    assert.ok(w.fileRequests.includes(SIBLING), "the viewer fetched the sibling over /file: " + JSON.stringify(w.fileRequests));
    assert.equal(page.url(), START, "sibling: location.href is unchanged");
    assert.deepEqual(w.navs.slice(navs2), [], "sibling: no main-frame navigation");
    assert.equal(w.popups.length, popups2, "sibling: no new tab");

    // 5. the note again (an open replaces the shown document), and the relative link spelled xlink:href: the same open of the
    //    sibling in this viewer, through the same path link, with no second attribute for the browser to follow
    await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [PATH, SID] as [string, string]);
    await page.waitForSelector("#romp-fileview .fileview-md h1#md-figure", { timeout: 10000 });
    const popups3 = w.popups.length, navs3 = w.navs.length, files3 = w.fileRequests.length;
    await clickForNothing(page, w, ".fx-svg-xlink-rel text");
    await page.waitForSelector("#romp-fileview .fileview-md h1#md-sibling", { timeout: 10000 });
    assert.ok(w.fileRequests.slice(files3).includes(SIBLING), "xlink sibling: the viewer fetched the sibling over /file: " + JSON.stringify(w.fileRequests.slice(files3)));
    assert.equal(page.url(), START, "xlink sibling: location.href is unchanged");
    assert.deepEqual(w.navs.slice(navs3), [], "xlink sibling: no main-frame navigation");
    assert.equal(w.popups.length, popups3, "xlink sibling: no new tab");

    assert.deepEqual(w.errors, [], "no page errors");
  });
});

test("a URL document, with nothing in front of mdBlock's own stamps: an absolute href of every shape opens a new tab (the SVG anchors' target is an ATTRIBUTE), the relative sibling resolves against the document's URL, the fragment scrolls through the body's fv-anchor delegate", { timeout: 90000 }, async (t) => {
  await inBrowser(t, "url", async (page, w) => {
    const START = page.url();
    assert.deepEqual(w.docRequests, [URL_PATH], "the viewer fetched the note from its URL");

    // 1. an absolute href of every surviving shape: a new tab at the link's URL, the Files document stays. No delegate runs here,
    //    so the tab is the `target` attribute's doing; a stamp that reached only the SVGAElement's read-only property leaves
    //    the browser to follow the anchor in this frame, and clickForTab names that navigation
    for (const c of ABSOLUTE) {
      const popups0 = w.popups.length, navs0 = w.navs.length;
      const tabUrl = await clickForTab(page, w, c.sel, c.name);
      assert.equal(tabUrl, c.href, c.name + ": the new tab is at the link's URL");
      assert.equal(page.url(), START, c.name + ": location.href is unchanged after the click");
      assert.deepEqual(w.navs.slice(navs0), [], c.name + ": no main-frame navigation");
      assert.equal(w.popups.length - popups0, 1, c.name + ": one new tab, not two");
      assert.ok(await page.evaluate(() => !!document.querySelector("#romp-fileview .fileview-md")), c.name + ": the note is still on screen");
    }

    // 2. the SVG anchor's relative `sibling.md`, in either spelling: the first LINK_SEL pass resolved it against the document's
    //    URL, the second stamped it, so it opens a tab at the sibling's URL (in the chat page the delegate would route that
    //    same-origin .md back into the viewer; there is no delegate here, and the tab is the stamps' own outcome)
    for (const [sel, name] of [[".fx-svg-rel text", "the SVG anchor's relative href"], [".fx-svg-xlink-rel text", "the SVG anchor's relative xlink:href"]] as const) {
      const popups0 = w.popups.length, navs0 = w.navs.length;
      const tabUrl = await clickForTab(page, w, sel, name);
      assert.equal(tabUrl, URL_SIBLING, name + ": resolved against the document's URL, not the page's");
      assert.equal(page.url(), START, name + ": location.href is unchanged");
      assert.deepEqual(w.navs.slice(navs0), [], name + ": no main-frame navigation");
      assert.equal(w.popups.length - popups0, 1, name + ": one new tab");
    }

    // 3. the SVG anchor's #fragment: stamped fv-anchor, so the body's delegate lands it on its heading; no tab, no navigation
    const popups1 = w.popups.length, navs1 = w.navs.length;
    await page.evaluate(() => { (document.querySelector("#romp-fileview .fileview-body") as HTMLElement).scrollTop = 0; });
    await clickForNothing(page, w, ".fx-svg-frag text");
    const landed = await page.evaluate(readLanding);
    assert.equal(page.url(), START, "fragment: location.href is unchanged");
    assert.deepEqual(w.navs.slice(navs1), [], "fragment: no main-frame navigation");
    assert.equal(w.popups.length, popups1, "fragment: no new tab");
    assert.ok(landed.scrollTop > 0 && landed.tailTop >= -2 && landed.tailTop < 48, "the Tail heading is at the top of the body after the click: " + JSON.stringify(landed));

    // 4. the stamps mdBlock's URL arm wrote, every one an attribute (the reason 1 held above)
    const facts = await page.evaluate(readFacts, XLINK);
    assert.equal(facts.maps + facts.areas, 0, "no <map> and no <area> in a URL document either: the same sanitize call");
    assert.deepEqual(facts.imgs, [{ usemap: null, decoded: true }], "the picture decoded, and its usemap is gone");
    assert.equal(facts.links.length, 8, "eight links in the note, every one an anchor: " + JSON.stringify(facts.links));
    assert.deepEqual(facts.links.map((l: LinkFacts) => l.xlink), facts.links.map(() => null), "no xlink:href survives on any anchor in a URL document either: " + JSON.stringify(facts.links.map((l: LinkFacts) => [l.cls, l.xlink])));
    const [ctl, svgHref, svgXlink, svgFrag, svgRel, svgXlinkRel, svgXlinkDead, aDead] = facts.links;
    assert.deepEqual([ctl.tag, ctl.ns, ctl.target, ctl.rel, ctl.act], ["a", HTML, "_blank", "noopener", null], "control: the HTML anchor");
    assert.deepEqual([svgHref.tag, svgHref.ns, svgHref.target, svgHref.rel, svgHref.act], ["a", SVG, "_blank", "noopener", null],
      "an SVG <a href> carries the target ATTRIBUTE, written with setAttribute (the property write was dropped by the SVGAElement)");
    assert.deepEqual([svgXlink.tag, svgXlink.ns, svgXlink.href, svgXlink.xlink, svgXlink.target, svgXlink.rel],
      ["a", SVG, "https://example.invalid/xlink", null, "_blank", "noopener"], "an SVG <a xlink:href> gets a plain href copy, loses the XLink spelling, and takes the same stamps");
    assert.deepEqual([svgFrag.tag, svgFrag.href, svgFrag.act, svgFrag.target, svgFrag.rel], ["a", "#tail", "fv-anchor", null, null],
      "an SVG fragment link is stamped fv-anchor and gets no tab, like an HTML one (md-url-view.test.ts pins the arm)");
    assert.deepEqual([svgRel.tag, svgRel.href, svgRel.target, svgRel.rel, svgRel.act], ["a", URL_SIBLING, "_blank", "noopener", null],
      "an SVG anchor's relative href is absolute against the document's URL, and stamped like every other");
    assert.deepEqual([svgXlinkRel.tag, svgXlinkRel.ns, svgXlinkRel.href, svgXlinkRel.xlink, svgXlinkRel.target, svgXlinkRel.rel], ["a", SVG, URL_SIBLING, null, "_blank", "noopener"],
      "the same relative href spelled xlink:href: absolute against the document's URL on the plain href, the XLink spelling gone");
    // a URL document has no file for a host with a port to be, so the reference resolves against the document as the browser
    // would resolve it (no scheme: `127.0.0.1` is not one) and opens a tab, in either spelling
    assert.deepEqual([svgXlinkDead.href, svgXlinkDead.xlink, svgXlinkDead.target, aDead.href, aDead.xlink, aDead.target],
      [URL_DIR + "127.0.0.1:3000", null, "_blank", URL_DIR + "127.0.0.1:3000", null, "_blank"], "a host with a port in a URL document: resolved against the document's URL, a tab, one attribute");

    assert.deepEqual(w.errors, [], "no page errors");
  });
});

test("the chat page's viewer (the render bundle): a file document's SVG anchors spelled xlink:href go where the HTML ones go: the relative one opens the sibling FILE in this viewer, never a URL document, and a dead one opens nothing", { timeout: 90000 }, async (t) => {
  await inBrowser(t, "chat", async (page, w) => {
    const START = page.url();
    assert.ok(w.fileRequests.includes(PATH), "the viewer fetched the note over /file: " + JSON.stringify(w.fileRequests));
    const opens = () => page.evaluate(() => (window as any).__opens as unknown[]);

    // 1. what mdBlock and the module left: the same eight anchors as in the Files page, and no xlink:href on any of them, so the
    //    chat's delegate (LINK_SEL, `a[*|href]`) matches exactly the anchors that carry a plain href
    const facts = await page.evaluate(readFacts, XLINK);
    assert.equal(facts.links.length, 8, "eight links in the note: " + JSON.stringify(facts.links));
    assert.deepEqual(facts.links.map((l: LinkFacts) => l.xlink), facts.links.map(() => null), "no xlink:href survives on any anchor: " + JSON.stringify(facts.links.map((l: LinkFacts) => [l.cls, l.xlink])));
    const [, , svgXlink, , , svgXlinkRel, svgXlinkDead, aDead] = facts.links;
    assert.deepEqual([svgXlink.href, svgXlink.target], ["https://example.invalid/xlink", "_blank"], "the absolute xlink anchor: a plain href, stamped for a tab");
    assert.deepEqual([svgXlinkRel.href, svgXlinkRel.act, svgXlinkRel.path], [null, "openpath", SIBLING], "the relative xlink anchor is a path link with no href");
    assert.deepEqual([svgXlinkDead.href, /\bfv-dead\b/.test(svgXlinkDead.cls), aDead.href, /\bfv-dead\b/.test(aDead.cls)], [null, true, null, true], "the two dead links have no href");

    // 2. the relative xlink anchor opens the sibling FILE, through the viewer's own listener (the path link's data-act). Before the
    //    fix the chat's delegate matched the anchor through its xlink:href, resolved `sibling.md` against the chat page and opened
    //    http://<host>/sibling.md as a URL document (a 404 in production), and its stopPropagation kept the click from the viewer
    {
      const popups0 = w.popups.length, navs0 = w.navs.length, files0 = w.fileRequests.length, docs0 = w.docRequests.length;
      await clickForNothing(page, w, ".fx-svg-xlink-rel text");
      await page.waitForSelector("#romp-fileview .fileview-md h1#md-sibling, #romp-fileview .fileview-md h1#md-url-sibling", { timeout: 10000 });
      const h1 = await page.evaluate(() => (document.querySelector("#romp-fileview .fileview-md h1") as HTMLElement).id);
      assert.equal(h1, "md-sibling", "the sibling FILE is shown, not the document at the page-relative URL: h1#" + h1);
      assert.ok(w.fileRequests.slice(files0).includes(SIBLING), "the viewer fetched the sibling over /file: " + JSON.stringify(w.fileRequests.slice(files0)));
      assert.deepEqual(w.docRequests.slice(docs0), [], "no URL document was fetched");
      assert.deepEqual(await opens(), [], "the chat's delegate opened nothing");
      assert.equal(page.url(), START, "xlink sibling: location.href is unchanged");
      assert.deepEqual(w.navs.slice(navs0), [], "xlink sibling: no main-frame navigation");
      assert.equal(w.popups.length, popups0, "xlink sibling: no new tab");
    }

    // 3. the note again, and the two dead links: nothing opens, nothing moves. Before the fix the SVG one still matched the delegate
    //    through its xlink:href and went to window.open at http://<host>/127.0.0.1:3000; with the delegate standing aside it is the
    //    browser's default action, a same-frame navigation of the chat document to that address
    await page.evaluate(([p, sid]: [string, string]) => { (window as any).__rompProbe.openFileView(p, sid); }, [PATH, SID] as [string, string]);
    await page.waitForSelector("#romp-fileview .fileview-md h1#md-figure", { timeout: 10000 });
    for (const [sel, name] of [[".fx-svg-xlink-dead text", "the dead SVG xlink anchor"], [".fx-a-dead", "the dead HTML anchor (control)"]] as const) {
      const popups0 = w.popups.length, navs0 = w.navs.length;
      await page.evaluate(() => { (window as any).__opens.length = 0; });
      await clickForNothing(page, w, sel);
      assert.deepEqual(w.navs.slice(navs0), [], name + ": no main-frame navigation");
      assert.equal(page.url(), START, name + ": location.href is unchanged");
      assert.deepEqual(await opens(), [], name + ": the chat's delegate opened nothing (window.open)");
      assert.equal(w.popups.length, popups0, name + ": no new tab");
      assert.ok(await page.evaluate(() => !!document.querySelector("#romp-fileview .fileview-md")), name + ": the note is still on screen");
    }

    // 4. the control the other way round: the ABSOLUTE xlink anchor still opens, through the chat's delegate, from its plain href
    {
      await page.evaluate(() => { (window as any).__opens.length = 0; });
      await clickForNothing(page, w, ".fx-svg-xlink text");
      assert.deepEqual(await opens(), [["https://example.invalid/xlink", "_blank", "noopener,noreferrer"]], "the absolute xlink anchor opens in the user's browser through the chat's delegate");
      assert.equal(page.url(), START, "absolute xlink: location.href is unchanged");
    }

    assert.deepEqual(w.errors, [], "no page errors");
  });
});
