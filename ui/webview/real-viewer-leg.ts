// The real viewer in a real page, for the Slice 2 browser legs (plans/markdown-viewer.md, "layout follows the pane,
// reader keeps their place"): file-view.ts bundled from this tree as the webview build bundles it (and through it the
// REAL Comments panel, which the module registers itself), served into headless Chromium under each surface's own sheet
// (the chat modal: styles.css; the feed modal: feed.css; the Files pane: styles.css and files-pane.css under
// body.fileview-pane), with a fetch that answers the kernel's file route from a table the test edits (so a reload can
// bring different bytes under a new mtime) and a poster that answers the panel's status ask the way the kernel would,
// so the real aside opens on a click. A probe action stashes the seam (window.__seam) and counts its paints, the way
// file-view-text-size.test.ts's page does. Six legs measure over it (file-view-place-browser, file-view-notebar-browser,
// file-comments-float-scroll-browser, file-view-fold-browser, and the Slice 2 review's file-view-place-blocks-browser
// and file-view-place-reveal-browser); this module exists so they do not carry six copies of the same page. Test-only:
// no webview bundle imports it. playwright and esbuild are resolved from the extension's own package.json, so a
// single-file run (infra: the bundle written under TMPDIR) finds them too. The tree under test is the
// cwd's, ../ui/webview from the vscode-extension npm test runs in, as for every browser leg; to run a leg over another
// tree (a copy of the base commit's, say, to show it red there) run it from that tree's vscode-extension. No environment
// variable redirects the tree: one did, and a value left in a shell would have run these legs over another tree than the
// rest of the suite with nothing in the output saying so (file-view-leg-tree.test.ts pins this). Synthetic values only:
// an invented report, /repo/notes-api paths, the placeholder sid.
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

export const EXT = process.cwd();                                       // npm test runs in vscode-extension
export const requireCjs = createRequire(path.join(EXT, "package.json"));
export const UI = path.resolve(EXT, "..", "ui", "webview");             // the cwd's tree; no environment variable (header)
const web = (f: string) => fs.readFileSync(path.join(UI, f), "utf8").replace('@import "katex/dist/katex.min.css";', "");

export const ROOT = "/repo/notes-api";
export const REPORT = ROOT + "/docs/report.md";
export const SID = "11111111-2222-3333-4444-555555555555";
export const MT = "1757145600000000001";
export const MT2 = "1757145600000000009";
export const ORIGIN = "http://notes-api.test";                           // a synthetic origin: the viewer's localStorage needs one
export type Mode = "chat" | "feed" | "pane";

/** Paragraph i of the report: three sentences, so it wraps at every width the legs open. */
export const PARA = (i: number): string => `Paragraph ${i}: ` + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(3).trim() + ".";
/** The report: a heading and a hundred paragraphs. */
export const LONG = "# Report\n\n" + Array.from({ length: 100 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
/** The report after a session's write: twenty paragraphs inserted under the heading, the hundred unchanged after them. */
export const LONG2 = "# Report\n\n" + Array.from({ length: 20 }, (_, i) => `Inserted ${i + 1}: new text a session wrote above the reader's place, long enough to wrap once or twice in a narrow pane.`).join("\n\n") + "\n\n" + Array.from({ length: 100 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
/** The report with paragraph `n` rewritten in place (the block under the reader's eye edited away), and, with `above`, the
 *  twenty paragraphs of LONG2 inserted under the heading in the same write. */
export const rewritten = (n: number, above = false): string => "# Report\n\n"
  + (above ? Array.from({ length: 20 }, (_, i) => `Inserted ${i + 1}: new text a session wrote above the reader's place, long enough to wrap once or twice in a narrow pane.`).join("\n\n") + "\n\n" : "")
  + Array.from({ length: 100 }, (_, i) => (i + 1 === n ? `Rewritten ${n}: the session replaced this paragraph with a shorter one.` : PARA(i + 1))).join("\n\n") + "\n";

/** The kernel's status for a tracked file with nothing pending (the shape file-comments-margin-browser.test.ts answers). */
export const STATUS = {
  verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [] }, hunks: [], log: [],
  unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
};

let viewerBundle: string | null = null;
/** The viewer module as the webview build bundles it, in memory, as window.FV (openUrlView included, for the URL viewer's own swap). */
export function bundleViewer(): string {
  if (viewerBundle) return viewerBundle;
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'export { initFileView, openFileView, openUrlView, closeFileView, registerFileViewAction } from "./file-view";', resolveDir: UI, loader: "ts", sourcefile: "real-viewer-leg.ts" },
    bundle: true, write: false, format: "iife", globalName: "FV", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  viewerBundle = r.outputFiles[0].text as string;
  return viewerBundle;
}

/** The page: the surface's sheet, the bundle, the file table and fetch stub, the status-answering poster, the probe action.
 *  `window.__docs[path]` is the file's text and `window.__mtime` its mtime (both editable from a test); a URL the URL viewer
 *  fetches is answered from `window.__urls[url]` as text/markdown. The poster records every post in `window.__posted` and
 *  answers a `fileComments` ask with a `fileCommentsResult` carrying STATUS and the current mtime while `window.__autoReply`
 *  is on. `window.__paints` counts the seam's onRendered (one per text paint, and one per reflow). */
export function pageHtml(mode: Mode, docs: Record<string, string>, mtime = MT): string {
  const css = mode === "feed" ? web("feed.css") : mode === "pane" ? web("styles.css") + "\n" + web("files-pane.css") : web("styles.css");
  return `<!DOCTYPE html><html><head><meta charset=utf-8><style>${css}</style></head>
<body class="${mode === "pane" ? "fileview-pane" : ""}"><script>${bundleViewer()}</script><script>
window.__docs = ${JSON.stringify(docs)}; window.__urls = {}; window.__mtime = ${JSON.stringify(mtime)}; window.__fetches = 0; window.__posted = []; window.__status = ${JSON.stringify(STATUS)};
window.fetch = async function (url) {
  url = String(url); window.__fetches++;
  if (url.indexOf("/version") === 0) return new Response(JSON.stringify({ fileEditing: true }), { headers: { "Content-Type": "application/json" } });
  if (url.indexOf("/sessions") === 0) return new Response("[]", { headers: { "Content-Type": "application/json" } });
  if (window.__urls[url] !== undefined) return new Response(window.__urls[url], { status: 200, headers: { "Content-Type": "text/markdown; charset=utf-8" } });
  var m = /[?&]path=([^&]*)/.exec(url); var p = m ? decodeURIComponent(m[1]) : "";
  var text = window.__docs[p];
  if (text === undefined) return new Response("no such file: " + p, { status: 404 });
  return new Response(text, { status: 200, headers: { "Content-Type": "text/plain; charset=utf-8", "X-Romp-Mtime-Ns": window.__mtime, "X-Romp-Text-Utf8": "1" } });
};
window.__paints = 0; window.__seam = null; window.__autoReply = true;
FV.initFileView(function (m) {
  window.__posted.push(m);
  if (m && m.type === "fileComments" && window.__autoReply) {
    var reply = Object.assign({ type: "fileCommentsResult", reqId: m.reqId, fileMtimeNs: window.__mtime }, window.__status);
    setTimeout(function () { window.dispatchEvent(new MessageEvent("message", { data: reply })); }, 0);
  }
});
FV.registerFileViewAction({ id: "probe", mount: function (ctx) { window.__seam = ctx; ctx.onRendered(function () { window.__paints++; }); return null; } });
// what the legs read: the top-visible block of the Rendered view (the first child of .fileview-md whose box ends below the
// body's top edge) or row of the Raw view, its first characters and its top edge measured from the body's top
window.topBlock = function () {
  var body = document.querySelector(".fileview-body"); var br = body.getBoundingClientRect();
  var sel = document.querySelector(".fileview-md") ? ".fileview-md > *" : "code.hljs .fv-cl";
  var els = Array.prototype.slice.call(body.querySelectorAll(sel));
  for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect(); if (r.bottom > br.top + 0.5) return { text: (els[i].textContent || "").trim().slice(0, 14).trim(), top: Math.round((r.top - br.top) * 10) / 10, scrollTop: body.scrollTop, view: sel === ".fileview-md > *" ? "rendered" : "raw" }; }
  return null;
};
// scroll the body so the block whose text starts with the given text sits at the body's top edge
window.putAtTop = function (text) {
  var body = document.querySelector(".fileview-body");
  var sel = document.querySelector(".fileview-md") ? ".fileview-md > *" : "code.hljs .fv-cl";
  var k = Array.prototype.slice.call(body.querySelectorAll(sel)).filter(function (e) { return (e.textContent || "").indexOf(text) === 0; })[0];
  body.scrollTop += k.getBoundingClientRect().top - body.getBoundingClientRect().top;
};
</script></body></html>`;
}

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

/** Launch headless Chromium and run `body` with it, or skip LOUDLY (CI installs no browsers), as the other legs do. */
export async function inBrowser(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

export type Opened = { page: any; errors: string[] };
/** A page of the surface at the viewport size, the report open in it (Rendered, or Raw when `raw`: the preference is written
 *  first, as a person's earlier choice would stand), the first paint awaited. `docs` replaces the file table; `openOpts` is
 *  openFileView's third argument (a `line`, say); `url` opens the URL viewer on ORIGIN + url instead, answered from `urls`. */
export async function openViewer(browser: any, mode: Mode, width: number, height: number,
  opts: { docs?: Record<string, string>; mtime?: string; raw?: boolean; openOpts?: Record<string, unknown> | null; url?: string; urls?: Record<string, string> } = {}): Promise<Opened> {
  const page = await browser.newPage({ viewport: { width, height } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml(mode, opts.docs || { [REPORT]: LONG }, opts.mtime || MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  if (opts.raw) await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "raw" })); });
  if (opts.url) {
    await page.evaluate(([urls, u]: [Record<string, string>, string]) => { Object.assign((window as any).__urls, urls); (window as any).FV.openUrlView(u); }, [opts.urls || {}, ORIGIN + opts.url]);
  } else {
    await page.evaluate(([p, sid, o]: [string, string, Record<string, unknown> | null]) => { (window as any).FV.openFileView(p, sid, o); }, [REPORT, SID, opts.openOpts || null]);
  }
  await page.waitForFunction((raw: boolean) => !!document.querySelector(raw ? ".fileview-body .fv-cl" : ".fileview-md > p"), !!opts.raw, { timeout: 10000 });
  await frames(page, 2);
  return { page, errors };
}

/** `n` animation frames: the layout's own event, never a timer. */
export const frames = (page: any, n = 2): Promise<null> => page.evaluate((k: number) => new Promise<null>((r) => { const f = () => (k-- <= 0 ? r(null) : requestAnimationFrame(f)); f(); }), n);

/** Open the REAL Comments panel: the status auto-reply reveals the unit, a click on its button opens it (a second ask,
 *  answered the same way), and the aside mounts; then three frames, for the panel's own layout pass and the viewer's reflow. */
export async function openPanel(page: any): Promise<void> {
  await page.waitForFunction(() => { const u = document.querySelector(".fileview-fc"); return !!u && !(u as HTMLElement).hidden; }, null, { timeout: 5000 });
  await page.click(".fileview-fc button");
  await page.waitForFunction(() => !!document.querySelector(".fileview-aside"), null, { timeout: 5000 });
  await frames(page, 3);
}

/** Click the panel's button again to close it, and wait for the aside to leave. */
export async function closePanel(page: any): Promise<void> {
  await page.click(".fileview-fc button");
  await page.waitForFunction(() => !document.querySelector(".fileview-aside"), null, { timeout: 5000 });
  await frames(page, 3);
}

/** Wait until the seam has painted `n` times in all. */
export const paintsReach = (page: any, n: number): Promise<unknown> => page.waitForFunction((k: number) => (window as any).__paints >= k, n, { timeout: 10000 });

export type Top = { text: string; top: number; scrollTop: number; view: "rendered" | "raw" } | null;
export const topBlock = (page: any): Promise<Top> => page.evaluate(() => (window as any).topBlock());
export const putAtTop = (page: any, text: string): Promise<void> => page.evaluate((t: string) => (window as any).putAtTop(t), text);
