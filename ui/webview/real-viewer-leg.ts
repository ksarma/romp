// The real viewer in a real page, first for the Slice 2 browser legs (plans/markdown-viewer.md, "layout follows the
// pane, reader keeps their place") and then for every browser leg after them: file-view.ts bundled from this tree as the
// webview build bundles it (and through it the REAL Comments panel, which the module registers itself), served into
// headless Chromium under each surface's own sheet (the chat modal: styles.css; the feed modal: feed.css; the Files
// pane: styles.css and files-pane.css under body.fileview-pane), with a fetch that answers the kernel's file route from
// a table the test edits (so a reload can bring different bytes under a new mtime) and a poster that answers the
// panel's status ask the way the kernel would, so the real aside opens on a click. A probe action stashes the seam
// (window.__seam) and counts its paints, the way file-view-text-size.test.ts's page does. Every value the page inlines
// into its script (the file table, the mtime, the status) is written with `<` as `\u003c` (scriptLiteral): an HTML
// tokenizer ends script data at the first `</script` whatever the JavaScript around it, so a fixture holding one used to
// cut the harness script off before the fetch stub, leaving the viewer to fetch the harness page itself as the note
// (file-view-leg-page-browser.test.ts pins the escape).
// The legs that measure over it include file-view-place-browser, file-view-notebar-browser,
// file-comments-float-scroll-browser and file-view-fold-browser, the Slice 2 review's file-view-place-*-browser legs,
// file-view-float-anchoring-browser and file-view-leg-page-browser, the focus follow-on's merge audit's
// file-view-focus-seat-browser, and Slice 3's file-view-copy-*, file-view-print-*, file-view-fence-*,
// file-view-landing-*, file-view-typescale, file-view-scrollbar, file-view-prose-leading and file-view-url-place-bottom
// legs. Those are examples, not the census: the census is the test modules that import ./real-viewer-leg
// (`grep -l real-viewer-leg ui/webview/*.test.ts` lists them), and a change to the page (its fetch stub, its paint
// counter, its sheets) is checked against every one of them, not against this list (a count kept here went stale by
// more than half the callers). This module exists so they do not each carry a copy of the same page. Test-only:
// no webview bundle imports it. playwright and esbuild are resolved from the extension's own package.json, so a
// single-file run (infra: the bundle written under TMPDIR) finds them too. The tree under test is the
// cwd's, ../ui/webview from the vscode-extension npm test runs in, as for every browser leg; to run a leg over another
// tree (a copy of the base commit's, say, to show it red there) run it from that tree's vscode-extension. No environment
// variable redirects the tree: one did, and a value left in a shell would have run these legs over another tree than the
// rest of the suite with nothing in the output saying so (file-view-leg-tree.test.ts pins this). Synthetic values only:
// an invented report, /repo/notes-api paths, the placeholder sid.
import * as assert from "node:assert/strict";
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
/** The viewer module as the webview build bundles it, in memory, as window.FV (openUrlView included, for the URL viewer's own swap;
 *  anchor-map's TRIM_STATS too, the trim's own pass counter, which the retrim-events leg reads to count the panel's trim calls;
 *  and preview.ts's heal for markdown-inline pictures, installMdImgHeal with the two retry drivers render.ts calls on a kernel
 *  message and on romp:wsup, so a leg can put the chat page's own retry of a failed figure under the viewer, as the figure
 *  label's leg does; nothing installs it unless a leg calls it). */
export function bundleViewer(): string {
  if (viewerBundle) return viewerBundle;
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'export { initFileView, openFileView, openUrlView, closeFileView, registerFileViewAction } from "./file-view"; export { TRIM_STATS } from "./anchor-map"; export { installMdImgHeal, retryFailedPreviews, refreshSettledPreviews } from "./preview";', resolveDir: UI, loader: "ts", sourcefile: "real-viewer-leg.ts" },
    bundle: true, write: false, format: "iife", globalName: "FV", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  viewerBundle = r.outputFiles[0].text as string;
  return viewerBundle;
}

/** A value inlined into the page's script as a JavaScript literal: JSON with every `<` written `\u003c`, so a fixture
 *  holding `</script>` (or `<!--`, which puts the tokenizer in its escaped state) cannot end the script element early.
 *  JSON.stringify leaves `<` alone; JSON.parse and the engine read `\u003c` back as `<`. */
export const scriptLiteral = (x: unknown): string => JSON.stringify(x).replace(/</g, "\\u003c");

/** The page: the surface's sheet (and the kernel's inlined THEME_CSS after it when `theme` carries it), the bundle, the file
 *  table and fetch stub, the status-answering poster, the probe action.
 *  `window.__docs[path]` is the file's text and `window.__mtime` its mtime (both editable from a test); a URL the URL viewer
 *  fetches is answered from `window.__urls[url]` as text/markdown. The poster records every post in `window.__posted` and
 *  answers a `fileComments` ask with a `fileCommentsResult` carrying STATUS and the current mtime while `window.__autoReply`
 *  is on. `window.__fetches` counts every request the stub answers and `window.__heads` the `HEAD`s among them (the Comments
 *  panel's poll, the viewer's changed-on-disk probe; Slice 6, item 5): a HEAD is answered with the GET's headers and no
 *  body, as the kernel answers it. A 404 carries the kernel's one-word cause in X-Romp-Reason, `window.__reason` (the PR
 *  review's round 2): `missing` by default, a file gone from an absolute path, which the viewer's bar reads as a deletion; a
 *  leg sets another cause (`relative`, `detached`) or null for a kernel from before the header. `window.__paints` counts the seam's onRendered (one per text paint, and one per reflow), `window.__reflows` the
 *  reflows among them (`why` "reflow"), so `__paints - __reflows` is the paints proper. */
export function pageHtml(mode: Mode, docs: Record<string, string>, mtime = MT, theme = ""): string {
  // The sheets in the kernel's order (_chat_page, _feed_page and _files_page in kernel/kernel.py): the surface's sheet (a
  // <link> there), then a <style> holding THEME_CSS and, on the Files pane, files-pane.css after it. `theme` is that
  // inlined CSS; the print leg passes the kernel's own, since a page rule the sheet must outrank sits there and not in any
  // sheet (the Slice 3 review, round 3). With none the sheet and the pane's own share one <style>, as every leg had them.
  const sheet = mode === "feed" ? web("feed.css") : web("styles.css");
  const own = mode === "pane" ? "\n" + web("files-pane.css") : "";
  const head = theme ? `<style>${sheet}</style><style>${theme}${own}</style>` : `<style>${sheet}${own}</style>`;
  return `<!DOCTYPE html><html><head><meta charset=utf-8>${head}</head>
<body class="${mode === "pane" ? "fileview-pane" : ""}"><script>${bundleViewer()}</script><script>
window.__docs = ${scriptLiteral(docs)}; window.__urls = {}; window.__mtime = ${scriptLiteral(mtime)}; window.__reason = "missing"; window.__fetches = 0; window.__heads = 0; window.__posted = []; window.__status = ${scriptLiteral(STATUS)};
window.fetch = async function (url, init) {
  url = String(url); window.__fetches++;
  var head = !!(init && init.method === "HEAD"); if (head) window.__heads++;   // the kernel's HEAD /file: the headers alone
  if (url.indexOf("/version") === 0) return new Response(JSON.stringify({ fileEditing: true }), { headers: { "Content-Type": "application/json" } });
  if (url.indexOf("/sessions") === 0) return new Response("[]", { headers: { "Content-Type": "application/json" } });
  if (window.__urls[url] !== undefined) return new Response(window.__urls[url], { status: 200, headers: { "Content-Type": "text/markdown; charset=utf-8" } });
  var m = /[?&]path=([^&]*)/.exec(url); var p = m ? decodeURIComponent(m[1]) : "";
  var text = window.__docs[p];
  if (text === undefined) return new Response(head ? null : "no such file: " + p, { status: 404, headers: window.__reason ? { "X-Romp-Reason": window.__reason } : {} });   // the kernel's one-word cause on a 404 (the header above)
  if (/\.svg$/i.test(p)) return new Response(head ? null : text, { status: 200, headers: { "Content-Type": "image/svg+xml", "X-Romp-Mtime-Ns": window.__mtime } });   // an image: no text header, as the kernel sends it
  return new Response(head ? null : text, { status: 200, headers: { "Content-Type": "text/plain; charset=utf-8", "X-Romp-Mtime-Ns": window.__mtime, "X-Romp-Text-Utf8": "1" } });
};
window.__paints = 0; window.__reflows = 0; window.__seam = null; window.__autoReply = true;
FV.initFileView(function (m) {
  window.__posted.push(m);
  if (m && m.type === "fileComments" && window.__autoReply) {
    var reply = Object.assign({ type: "fileCommentsResult", reqId: m.reqId, fileMtimeNs: window.__mtime }, window.__status);
    setTimeout(function () { window.dispatchEvent(new MessageEvent("message", { data: reply })); }, 0);
  }
});
FV.registerFileViewAction({ id: "probe", mount: function (ctx) { window.__seam = ctx; ctx.onRendered(function (why) { window.__paints++; if (why === "reflow") window.__reflows++; }); return null; } });
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
/** What `serve` answers a request of the page's origin with, in place of the page: the status, the Content-Type and the body. */
export type Served = { status: number; type?: string; body?: string };
/** A page of the surface at the viewport size, the report open in it (Rendered, or Raw when `raw`: the preference is written
 *  first, as a person's earlier choice would stand), the first paint awaited. `docs` replaces the file table; `openOpts` is
 *  openFileView's third argument (a `line`, say); `url` opens the URL viewer on ORIGIN + url instead, answered from `urls`;
 *  `theme` is CSS inlined after the sheet as the kernel inlines THEME_CSS (pageHtml). `serve` answers the requests the page's
 *  own fetch stub never sees, the ones the browser makes from the DOM (a figure's `<img src>` at the kernel's /file route,
 *  rewriteFigureSrcs's URL): a Served answer for a URL of the origin is fulfilled as given (a 404 for a missing figure, a
 *  text/plain body the decoder refuses, an image/svg+xml that loads), null falls through to the page, as every request of the
 *  origin did before. `before` runs in node with the page after it is loaded and before the open, for a page global that must
 *  stand before the first paint (the chat page's heal, installMdImgHeal, registers a failed picture at its error event). */
export async function openViewer(browser: any, mode: Mode, width: number, height: number,
  opts: { docs?: Record<string, string>; mtime?: string; raw?: boolean; openOpts?: Record<string, unknown> | null; url?: string; urls?: Record<string, string>; theme?: string;
    serve?: (u: URL) => Served | null; before?: (page: any) => Promise<void> } = {}): Promise<Opened> {
  const page = await browser.newPage({ viewport: { width, height } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml(mode, opts.docs || { [REPORT]: LONG }, opts.mtime || MT, opts.theme || "");
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => {
    const a = opts.serve ? opts.serve(new URL(route.request().url())) : null;
    if (a) return route.fulfill({ status: a.status, contentType: a.type, body: a.body ?? "" });
    return route.fulfill({ status: 200, contentType: "text/html", body: html });
  });
  await page.goto(ORIGIN + "/");
  if (opts.before) await opts.before(page);
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

/** The chat page's own window keydown handlers, lifted from render.ts's source, for a leg that puts the viewer under them in the
 *  chat modal (file-view-focus-body-browser.test.ts, file-view-outline-browser.test.ts; Slice 6 of plans/markdown-viewer.md): the single-key shortcuts (the arrows, Enter)
 *  and the type-to-compose default, with a prelude standing in for the chat state they read: its setActive records each call
 *  in `window.__setActive` and moves activeId as the real one does, and `window.__chatScene(order, active)` seats a session
 *  list for a leg that presses ←/→ (the tab step needs two sessions and an active one). Every name the lift uses that
 *  render.ts imports or declares at its top level must be one the prelude declares or the lift itself declares, as
 *  file-view-links-browser.test.ts checks its lift, so a render.ts change surfaces here and not as a silent ReferenceError. */
export function chatKeysScript(): string {
  const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
  const a0 = RENDER.indexOf("\nconst NAV_SCROLL_STEP = 60;\n") + 1;
  const a1 = RENDER.indexOf('\n// The gates the two "from anywhere" defaults share', a0);
  const b0 = RENDER.indexOf("\nfunction typeFromAnywhereTarget(e: Event): HTMLTextAreaElement | null {", a1) + 1;
  const b1 = RENDER.indexOf("\n// SELECT → PASTE", b0);
  assert.ok(a0 > 0 && a1 > a0 && b0 > a1 && b1 > b0, "render.ts's shortcuts handler and its type-to-compose handler (the anchors moved; re-anchor)");
  const lifted = RENDER.slice(a0, a1) + "\n" + RENDER.slice(b0, b1) + "\n";
  const prelude = [
    "let activeId: string | null = null;", "const order: string[] = [];", "const visibleOrder = (): string[] => order;", "const collapsedTabIds = new Set<string>();",
    "const neighborOfFolded = (): string | null => null;", "const lastStripItems: unknown[] = [];",
    "const setActive = (id: string): void => { (window as any).__setActive.push(id); activeId = id; };", "(window as any).__setActive = [];",
    "(window as any).__chatScene = (ord: string[], active: string | null): void => { order.splice(0, order.length, ...ord); activeId = active; };",
    "const scrollContentBy = (content: HTMLElement, dy: number, _writer: string): void => { content.scrollTop += dy; (window as any).__contentScrolls++; };",
    "const transcriptSelection = (): null => null;", "const seedTranscriptQuote = (): void => {};",
    "const focusComposer = (): void => { (document.getElementById(\"composer-input\") as HTMLTextAreaElement).focus(); };",
    "const composerNoteHolds = (): boolean => false;", "const focusComposerOrAsk = (): boolean => { focusComposer(); return true; };",
    "const liveAsks = new Map<string, unknown>();", "const ctxMenuEl: HTMLElement | null = null;", "(window as any).__contentScrolls = 0;",
  ].join("\n") + "\n";
  const code = lifted.replace(/\/\*[\s\S]*?\*\/|\/\/.*$|"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`/gm, (m) => (m[0] === "/" ? "" : '""'));
  const locals = new Set(Array.from(code.matchAll(/\b(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)/g), (m) => m[1]));
  const named = new Set<string>();
  const addNamed = (list: string) => { for (const part of list.split(",")) { const name = part.trim().replace(/^type\s+/, "").split(/\s+as\s+/).pop()!.trim(); if (name) named.add(name); } };
  for (const m of RENDER.matchAll(/^import (?!type\b)(?:([A-Za-z_$][\w$]*)\s*,?\s*)?(?:\* as ([A-Za-z_$][\w$]*)|\{([^}]*)\})?\s*from "[^"]+";/gm)) { if (m[1]) named.add(m[1]); if (m[2]) named.add(m[2]); if (m[3]) addNamed(m[3]); }
  for (const m of RENDER.matchAll(/^(?:export )?(?:const|let|var|(?:async )?function\*?|class) ([A-Za-z_$][\w$]*)/gm)) named.add(m[1]);
  const declared = new Set(Array.from(prelude.matchAll(/^(?:const|let) ([A-Za-z_$][\w$]*)/gm), (m) => m[1]));
  const free = Array.from(named).filter((n) => !locals.has(n) && !declared.has(n) && new RegExp("(?<![.\\w$])" + n.replace(/\$/g, "\\$") + "\\b").test(code));
  assert.deepEqual(free, [], "render.ts's key handlers name these and the prelude defines none of them: define each in chatKeysScript's prelude, or the lifted handler throws where a key reaches it");
  return requireCjs("esbuild").transformSync(prelude + lifted, { loader: "ts", target: "es2020" }).code;
}

/** Wait until the seam has painted `n` times in all. */
export const paintsReach = (page: any, n: number): Promise<unknown> => page.waitForFunction((k: number) => (window as any).__paints >= k, n, { timeout: 10000 });

export type Top = { text: string; top: number; scrollTop: number; view: "rendered" | "raw" } | null;
export const topBlock = (page: any): Promise<Top> => page.evaluate(() => (window as any).topBlock());
export const putAtTop = (page: any, text: string): Promise<void> => page.evaluate((t: string) => (window as any).putAtTop(t), text);
