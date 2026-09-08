// A message's href that names NO scheme, under the chat's link delegate, over the REAL render.ts bundle in headless
// Chromium at an http: origin (the web dashboard). The delegate used to hand every href that failed its scheme test to
// the browser's default action as "relative". DOMPurify keeps several hrefs that fail that test and still resolve to
// ANOTHER origin: protocol-relative `//host` and `/\host`, an `https:` preceded by a C0 control character (its trim
// removes only JavaScript whitespace, and its URI check strips controls for the test and writes the value back as
// written), and a tab or newline inside the scheme (`ht&#10;tps:`). A click on any of them navigated the chat document
// itself, in the same frame, to the other origin: every pane gone until a reload, and a page there free to imitate the
// dashboard. A plain relative link did the same to a same-origin page (the round-2 review of plans/markdown-viewer.md
// Slice 1; pre-existing on main, and misrecorded as same-origin only). The delegate now resolves a scheme-less href the
// way the browser's default action would, against the document (its URL parser, which is what strips the control and
// the whitespace and gives `//host` the page's scheme), and opens the RESOLVED web URL as it opens an absolute one: the
// tab for another origin or a same-origin page, the viewer for a same-origin .md; an empty href opens nothing. Whatever
// the shape, the chat document stays. Skips LOUDLY without a playwright browser (CI installs none), as the other browser
// legs do. Synthetic values only: example.invalid and romp.test URLs.
//
// The second leg is the other side of the same arm (the round-3 review): the delegate is document-wide, and the page ITSELF
// builds scheme-less anchors, `<a href="/file?..." download>`, for its three download controls (the lightbox's, the viewer's
// Download button and the file browser's download-only row, each a transient or chrome anchor the browser's own download
// UI answers). The arm as first written resolved those too and handed them to window.open: a popup where the download was,
// and nothing at all when the popup is blocked (the stub below returns null, that case), the lightbox's picture opened in a
// tab and never saved. The arm reads a MESSAGE's link only (`.md`, the scope the `#` resolver already had); an anchor the
// page built is the browser's, as on main. A message's own same-origin download link keeps the browser's download too;
// one to another origin, whose download attribute the browser ignores, opens as any link does and never moves the frame.
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

const CHAT = "http://romp.test/chat";
const XLINK = "http://www.w3.org/1999/xlink";
const NOTE = "# Note\n\nA line from the same-origin note.\n";
const TAB: [string, string] = ["_blank", "noopener,noreferrer"];

// Each case: the message as md() receives it; where the click lands; the first code points of the href the sanitizer
// left in the DOM (the precondition: the hostile spelling reached the page as written, so the delegate, not the
// sanitizer, is what the leg proves); what the delegate must hand to window.open (the RESOLVED address), or none.
// The entities (&#1;, &#10;, &#9;) are how an author writes a control character or a line break into an attribute.
const CASES: { name: string; md: string; sel: string; hit: string; starts: string; opens: [string, string, string][]; viewer?: boolean }[] = [
  { name: "an absolute https href (control)", sel: ".fx-body a", hit: "A", starts: "https:",
    md: '<a href="https://example.invalid/ctl">ctl</a>', opens: [["https://example.invalid/ctl", ...TAB]] },
  { name: "a protocol-relative href in a markdown link", sel: ".fx-body a", hit: "A", starts: "//ex",
    md: "[pr](//example.invalid/pr)", opens: [["http://example.invalid/pr", ...TAB]] },
  { name: "a protocol-relative href spelled with a backslash", sel: ".fx-body a", hit: "A", starts: "/\\ex",
    md: '<a href="/\\example.invalid/bs">bs</a>', opens: [["http://example.invalid/bs", ...TAB]] },
  { name: "an https href behind a C0 control character", sel: ".fx-body a", hit: "A", starts: "https:",
    md: '<a href="&#1;https://example.invalid/c1">c1</a>', opens: [["https://example.invalid/c1", ...TAB]] },
  { name: "a newline inside the scheme", sel: ".fx-body a", hit: "A", starts: "ht\ntps:",
    md: '<a href="ht&#10;tps://example.invalid/nl">nl</a>', opens: [["https://example.invalid/nl", ...TAB]] },
  { name: "a tab inside the scheme", sel: ".fx-body a", hit: "A", starts: "ht\ttps:",
    md: '<a href="ht&#9;tps://example.invalid/tab">tab</a>', opens: [["https://example.invalid/tab", ...TAB]] },
  { name: "a protocol-relative xlink:href on an SVG anchor", sel: ".fx-body svg text", hit: "text", starts: "//ex",
    md: `<svg width="300" height="60" xmlns:xlink="${XLINK}"><a xlink:href="//example.invalid/svgpr"><text x="5" y="40" font-size="30">svgpr</text></a></svg>\n\nafter`,
    opens: [["http://example.invalid/svgpr", ...TAB]] },
  { name: "a root-relative href to a same-origin page", sel: ".fx-body a", hit: "A", starts: "/rel",
    md: "[rel](/rel)", opens: [["http://romp.test/rel", ...TAB]] },
  { name: "an empty href", sel: ".fx-body a", hit: "A", starts: "",
    md: "[empty]()", opens: [] },
  { name: "a relative href to a same-origin markdown file", sel: ".fx-body a", hit: "A", starts: "docs/",
    md: "[note](docs/note.md)", opens: [], viewer: true },
];

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
function bundle(entry: string): string {
  const r = requireCjs("esbuild").buildSync({ ...BUILD, entryPoints: [path.join(UI, entry)] });
  return r.outputFiles[0].text;
}
// md() as render.ts runs it, minus the PR-ref linkifier: marked with the chat's options and extensions, then sanitizeMd;
// and the page's own chrome openers (the lightbox, the viewer, the file browser) for the second leg, from the same source
// files the chat bundle is built from. They are a second instance of each module beside render.js's, which is what lets
// the leg bind its own poster: the DOM they build, and the anchors they click, are the ones render.js's delegate sees.
function probeBundle(): string {
  const contents = [
    'import { marked } from "marked";',
    'import { sanitizeMd } from "./md-sanitize";',
    'import { chatMdExtensions } from "./chat-md";',
    'import { openFileView, initFileView } from "./file-view";',
    'import { openLightbox } from "./preview";',
    'import { initFileBrowse, openFileBrowse } from "./file-browse";',
    "marked.setOptions({ gfm: true, breaks: false });",
    "marked.use(...chatMdExtensions);",
    "(window as any).__mdProbe = (s: string) => sanitizeMd(marked.parse(s) as string).innerHTML;",
    "(window as any).__chrome = { openFileView, initFileView, openLightbox, initFileBrowse, openFileBrowse };",
  ].join("\n");
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, sourcefile: "md-probe.ts", loader: "ts" } });
  return r.outputFiles[0].text;
}
// the chat page as the web dashboard serves it: the shared skeleton, the chat's sheet, a fake acquireVsCodeApi (the
// kernel's shim's role), window.open recorded instead of opened, then the chat bundle, a click recorder and the probe.
// The recorder reads each click's defaultPrevented flag as dispatch ends (md-sanitize-chat-links-browser.test.ts has
// the reasoning): following the link is the click's default action, run exactly when the flag is still false, so the
// flag says whether the document WILL navigate without waiting to see whether it did.
const CHAT_HTML = `<!DOCTYPE html><html lang=en><head><meta charset=utf-8><style>${STYLES}</style></head><body>
${chatBody(ATTACH_TITLE_WEB)}
<script>window.__opens=[];window.open=function(u,t,f){window.__opens.push([u,t,f]);return null;};
window.acquireVsCodeApi=function(){return{postMessage:function(){}}};</script>
<script src=/dist/render.js></script>
<script>(function(){window.__lastClick=null;window.__clicks=[];function rec(e){var t=e.target;var c={prevented:e.defaultPrevented,tag:t&&t.tagName,link:!!(t&&t.closest&&t.closest("a"))};window.__lastClick=c;window.__clicks.push(c);}
document.addEventListener("click",rec,true);window.addEventListener("click",rec);})();</script>
<script src=/dist/probe.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Row = { name: string; hit: string | null; starts: string | null; prevented: boolean | null; opens: unknown[]; url: string; viewer: boolean; gone?: string };

test("a scheme-less href in a message never navigates the chat document: //host, /\\host, a control character or whitespace around the scheme, a same-origin page and an empty href are resolved as the browser would and opened as any link is", { timeout: 120000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [], navs: string[] = [], rows: Row[] = [];
  try {
    const renderJs = bundle("render.ts"), probeJs = probeBundle();
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("framenavigated", (f: any) => { if (f === page.mainFrame()) navs.push(f.url()); });
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      // the other origin answers, so a navigation that does happen commits and is seen
      if (u.hostname === "example.invalid") return route.fulfill({ status: 200, contentType: "text/html", body: "<title>elsewhere</title>elsewhere" });
      if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: CHAT_HTML });
      if (u.pathname === "/dist/render.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: renderJs });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: probeJs });
      if (u.pathname === "/rel") return route.fulfill({ status: 200, contentType: "text/html", body: "<title>a same-origin page</title>rel" });
      if (u.pathname === "/docs/note.md") return route.fulfill({ status: 200, contentType: "text/markdown; charset=utf-8", body: NOTE });
      return route.fulfill({ status: 404, body: "" });
    });
    for (const c of CASES) {
      // a fresh chat page per case: no viewer left open, no recorded open, and a document that DID leave (the defect) comes back
      try { await page.goto(CHAT); } catch { await page.goto(CHAT); }
      const shown = await page.evaluate(([md, sel]: [string, string]) => {
        const content = document.getElementById("content") as HTMLElement;
        const turn = document.createElement("div"); turn.className = "turn turn-assistant fx-turn";
        const body = document.createElement("div"); body.className = "assistant md fx-body";
        body.innerHTML = (window as any).__mdProbe(md);
        turn.appendChild(body); content.appendChild(turn);
        const el = document.querySelector(sel);
        const a = el ? el.closest("a") : null;
        const href = a ? (a.getAttribute("href") ?? a.getAttributeNS("http://www.w3.org/1999/xlink", "href")) : null;
        return { href, html: body.innerHTML };
      }, [c.md, c.sel] as [string, string]);
      const box = await page.locator(c.sel).first().boundingBox();
      assert.ok(box, c.name + ": the link has a box; sanitized as " + shown.html);
      const x = box.x + box.width / 2, y = box.y + box.height / 2;
      const hit = await page.evaluate(([px, py]: [number, number]) => {
        (window as any).__lastClick = null; (window as any).__opens.length = 0;
        const e = document.elementFromPoint(px, py); return e ? e.tagName : null;
      }, [x, y] as [number, number]);
      await page.mouse.click(x, y);
      const row: Row = { name: c.name, hit, starts: shown.href === null ? null : shown.href.slice(0, c.starts.length), prevented: null, opens: [], url: "", viewer: false };
      try {
        if (c.viewer) await page.waitForSelector("#romp-fileview .fileview-md", { timeout: 15000 });
        const r = await page.evaluate(() => {
          const c = (window as any).__lastClick;
          const md = document.querySelector("#romp-fileview .fileview-md");
          return { prevented: c ? c.prevented as boolean : null, opens: (window as any).__opens as unknown[], viewer: !!md && /same-origin note/.test(md.textContent || "") };
        });
        row.prevented = r.prevented; row.opens = r.opens; row.viewer = r.viewer; row.url = page.url();
      } catch (e) {
        // an uncancelled navigation that committed destroys the context: the message says so, and the row records where the page went
        row.gone = String((e as Error).message).split("\n")[0]; row.url = page.url();
      }
      // the defect's path only: a click the delegate did not cancel has a navigation in flight (or just committed, with its
      // frame event still to come), and the next case's goto would be interrupted by it; the frame's own navigation event
      // (bounded) is what the loop waits on, never a sleep, and the goto below retries once if the event beat it
      if (row.prevented !== true) await page.waitForEvent("framenavigated", { timeout: 3000 }).catch(() => { /* none came: the browser followed nothing */ });
      rows.push(row);
    }
    const table = JSON.stringify(rows, null, 1);
    for (let i = 0; i < CASES.length; i++) {
      const c = CASES[i], r = rows[i];
      assert.equal(r.hit, c.hit, c.name + ": precondition, the click lands on the element (elementFromPoint)");
      assert.equal(r.starts, c.starts, c.name + ": precondition, the sanitizer left the href in the DOM as written (the delegate, not the sanitizer, is what the leg proves)");
      assert.equal(r.gone, undefined, c.name + ": the chat page was still there after the click (" + r.gone + "); it is at " + r.url + "\n" + table);
      assert.equal(r.prevented, true, c.name + ": the delegate cancelled the click's default action, so the chat document does not follow the href\n" + table);
      assert.deepEqual(r.opens, c.opens, c.name + ": what the delegate opened in the user's browser (the RESOLVED address, or nothing)\n" + table);
      assert.equal(r.viewer, !!c.viewer, c.name + (c.viewer ? ": the same-origin note opened in the viewer, rendered" : ": no viewer opened") + "\n" + table);
      assert.equal(r.url, CHAT, c.name + ": the chat page is where it was\n" + table);
    }
    // the belt: whatever the flags said, the main frame only ever loaded the chat page, over the whole leg
    assert.deepEqual(navs.filter((u) => u !== CHAT), [], "the main frame never navigated anywhere but the chat page (a same-origin /rel or /docs/note.md counts as leaving too)");
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    await browser.close();
  }
});

// ── the page's own download controls ──────────────────────────────────────────────────────────────────────────────────

const README = "# Readme\n\nA line of the readme.\n";
// a valid 1x1 PNG: the lightbox's picture decodes (its control is built either way; the bytes keep the leg honest)
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "base64");
const fileUrlOf = (p: string, dl?: boolean): string => "http://romp.test/file?path=" + encodeURIComponent(p) + (dl ? "&download=1" : "");
// a message body filled the way render.ts fills one (body.innerHTML = md(text)), as a statement the page runs
const message = (md: string): string =>
  "(function(){var c=document.getElementById('content');var t=document.createElement('div');t.className='turn turn-assistant fx-turn';"
  + "var b=document.createElement('div');b.className='assistant md fx-body';b.innerHTML=window.__mdProbe(" + JSON.stringify(md) + ");t.appendChild(b);c.appendChild(t);})()";

// Each case: what the page runs to put the control up (the REAL openers from preview.ts, file-view.ts and file-browse.ts, or a
// message through the chat's pipeline); the selector waited for and clicked; what the browser must be handed: its own anchor
// download (the URL and, where the anchor names one, the filename), or nothing; what the delegate must hand to window.open;
// and whether the anchor's click is cancelled. The file browser's listing is answered by the leg itself through the window
// message its listener reads (the kernel's dirListing reply), a download-only row (viewable: false) among the entries.
type DlCase = { name: string; setup: string; sel: string; download: { url: string; name?: string } | null; opens: [string, string, string][]; prevented: boolean };
const DL_CASES: DlCase[] = [
  { name: "the lightbox's download control (a real anchor, `download` naming the file)", setup: "window.__chrome.openLightbox('/notes-api/plot.png', null)",
    sel: "#romp-lightbox .romp-lightbox-dl", download: { url: fileUrlOf("/notes-api/plot.png"), name: "plot.png" }, opens: [], prevented: false },
  { name: "the viewer's Download button (a transient <a download> the button clicks)",
    setup: "window.__chrome.initFileView(function () {}); window.__chrome.openFileView('/notes-api/README.md', null)",
    sel: "#romp-fileview button.fileview-btn:has-text('Download')", download: { url: fileUrlOf("/notes-api/README.md", true) }, opens: [], prevented: false },
  { name: "the file browser's download-only row (the same transient anchor)",
    setup: "(function(){window.__chrome.initFileBrowse(function(m){if(m.type!=='listDir')return;window.postMessage({type:'dirListing',reqId:m.reqId,base:m.path,parent:'/',"
      + "entries:[{name:'data.bin',isDir:false,isLink:false,size:4096,mtime:0,viewable:false}]},'*');},{shellRestore:false});window.__chrome.openFileBrowse('/notes-api',null);})()",
    sel: "#romp-filebrowse .fb-row[data-act='dl']", download: { url: fileUrlOf("/notes-api/data.bin", true) }, opens: [], prevented: false },
  { name: "a message's download link to ANOTHER origin (the browser ignores the attribute cross-origin and would navigate the frame: opened as a link)",
    setup: message('<a href="//example.invalid/dl" download>save</a>'), sel: ".fx-body a", download: null, opens: [["http://example.invalid/dl", ...TAB]], prevented: true },
  { name: "a message's own same-origin download link (DOMPurify keeps `download`; the browser's download, as on main)",
    setup: message('<a href="/file?path=%2Fnotes-api%2Fplot.png&download=1" download>save the plot</a>'), sel: ".fx-body a",
    download: { url: fileUrlOf("/notes-api/plot.png", true) }, opens: [], prevented: false },
];

type DlRow = { name: string; hit: string | null; prevented: boolean | null; opens: unknown[]; downloads: { url: string; name: string }[]; url: string };

test("the page's own download controls keep the browser's anchor download: the lightbox's control, the viewer's Download button and the file browser's download row save the file with no popup, as does a message's same-origin download link; one to another origin opens as a link", { timeout: 120000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [], navs: string[] = [], rows: DlRow[] = [];
  let downloads: { url: string; name: string }[] = [];
  try {
    const renderJs = bundle("render.ts"), probeJs = probeBundle();
    // a context of its own: downloads are accepted (and cancelled as they are seen: the event is the evidence, never the bytes),
    // and the routes hold at the context so a download request, which the page's route table would not see, is answered too
    const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1000, height: 800 } });
    await context.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.hostname === "example.invalid") return route.fulfill({ status: 200, contentType: "text/html", body: "<title>elsewhere</title>elsewhere" });
      if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: CHAT_HTML });
      if (u.pathname === "/dist/render.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: renderJs });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: probeJs });
      if (u.pathname === "/file") {
        // the kernel's /file route: `download=1` is served as an attachment (its _file_download rule), a picture inline, a note as text
        const p = u.searchParams.get("path") || "";
        const base = p.slice(p.lastIndexOf("/") + 1);
        if (u.searchParams.get("download") === "1") return route.fulfill({ status: 200, contentType: "application/octet-stream", headers: { "Content-Disposition": 'attachment; filename="' + base + '"' }, body: "bytes of " + p });
        if (p.endsWith(".png")) return route.fulfill({ status: 200, contentType: "image/png", body: PNG });
        if (p.endsWith(".md")) return route.fulfill({ status: 200, contentType: "text/markdown; charset=utf-8", body: README });
        return route.fulfill({ status: 404, body: "" });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    const page = await context.newPage();
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("framenavigated", (f: any) => { if (f === page.mainFrame()) navs.push(f.url()); });
    page.on("download", (d: any) => { downloads.push({ url: d.url(), name: d.suggestedFilename() }); d.cancel().catch(() => { /* finished already: nothing to cancel */ }); });
    for (const c of DL_CASES) {
      downloads = [];
      await page.goto(CHAT);                                       // a fresh chat page per case: no control left up, no recorded open
      await page.evaluate(c.setup);
      const loc = page.locator(c.sel).first();
      await loc.waitFor({ state: "visible", timeout: 15000 });    // the viewer's fetch, the browser's listing: the control is up when it is
      const box = await loc.boundingBox();
      assert.ok(box, c.name + ": the control has a box");
      const x = box.x + box.width / 2, y = box.y + box.height / 2;
      const hit = await page.evaluate(([px, py]: [number, number]) => {
        (window as any).__clicks.length = 0; (window as any).__opens.length = 0;
        const e = document.elementFromPoint(px, py); return e ? e.tagName : null;
      }, [x, y] as [number, number]);
      // the browser's download is an event of the page; armed before the click, awaited after it (bounded), never a sleep
      const saved = c.download ? page.waitForEvent("download", { timeout: 15000 }).then(() => true, () => false) : Promise.resolve(false);
      await page.mouse.click(x, y);
      await saved;
      const r = await page.evaluate(() => {
        // the anchor's own click: the last one recorded on or inside an <a> (a button's handler clicks a transient anchor of its own
        // inside the button's click, so the button's click is the last recorded of all; the anchor's is the one that downloads)
        const clicks = (window as any).__clicks as { prevented: boolean; link: boolean }[];
        const link = clicks.filter((k) => k.link).pop();
        return { prevented: link ? link.prevented : null, opens: (window as any).__opens as unknown[] };
      });
      rows.push({ name: c.name, hit, prevented: r.prevented, opens: r.opens, downloads: downloads.slice(), url: page.url() });
    }
    const table = JSON.stringify(rows, null, 1);
    for (let i = 0; i < DL_CASES.length; i++) {
      const c = DL_CASES[i], r = rows[i];
      assert.ok(r.hit, c.name + ": precondition, the click landed on an element (elementFromPoint)\n" + table);
      assert.equal(r.prevented, c.prevented, c.name + (c.prevented ? ": the delegate cancelled the anchor's default action" : ": the anchor's click reached the browser uncancelled (its default action, the download, is what saves the file)") + "\n" + table);
      assert.deepEqual(r.opens, c.opens, c.name + (c.opens.length ? ": opened as a link, at the resolved address" : ": window.open never called (a popup is not a download, and a blocked one is nothing)") + "\n" + table);
      if (c.download) {
        assert.equal(r.downloads.length, 1, c.name + ": exactly one download event on the page\n" + table);
        assert.equal(r.downloads[0].url, c.download.url, c.name + ": the browser downloads the anchor's URL\n" + table);
        if (c.download.name) assert.equal(r.downloads[0].name, c.download.name, c.name + ": under the name the anchor's download attribute gives it\n" + table);
      } else {
        assert.deepEqual(r.downloads, [], c.name + ": nothing downloaded\n" + table);
      }
      assert.equal(r.url, CHAT, c.name + ": the chat page is where it was\n" + table);
    }
    assert.deepEqual(navs.filter((u) => u !== CHAT), [], "the main frame never navigated anywhere but the chat page");
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    await browser.close();
  }
});
