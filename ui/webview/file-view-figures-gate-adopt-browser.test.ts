// Decision 8's placeholder (figure-gate.ts) is a promise about BYTES: while "Image from <host>. Click to load." stands, no
// request has left the page for that host. The instrument that observes bytes leaving is a server's request log, so this
// leg runs the REAL Files bundle in each of Playwright's three engines against real servers on 127.0.0.1 and reads their
// logs, never the page's request events and never a route (page.route answers a request inside the browser and can
// report one the network never carried, or miss one the engine issued before the route saw it). The unlisted host is a
// hostname no resolver knows, `remote.test`: the browser is launched with an HTTP forward proxy the test runs, which
// logs every request it is handed and forwards `romp.test` to the harness server and `remote.test` to the figure server,
// so the browser fetches under the unlisted name without DNS and every request it makes passes two logs on its way.
// The first scene: a note with one figure `![fig](http://remote.test/fig.png)` opens through the pane's own relay; the leg
// waits for the placeholder to be on screen, drains the network with a sentinel fetch, and asserts that neither log holds
// a request for fig.png; then it clicks the placeholder and asserts exactly one, with the method, the path and the Host
// header the figure server saw. Beside the scene, the premise the fix rests on, executed over the real sanitizeMd: the body
// it returns belongs to DOMPurify's own parse document, which has no browsing context (defaultView null) and never loads,
// so a figure in it fetches nothing; and the control that the instrument sees a fetch the page does make, an <img> of the
// live document with a src set and no place in the tree (the classic preloader), which every engine fetches. The second
// scene is the rewrite's half of the same rule: a note with a figure of its own folder, `![local](fig.png)`, whose src
// rewriteFigureSrcs repoints at /file; the harness log must hold that one request and none for the page-relative
// `/fig.png` the attribute named before the rewrite.
// Red before the fix in WebKit alone, both scenes: mdBlock adopted the sanitized nodes into a live-document element before
// the figure chain ran, and WebKit starts an <img>'s fetch synchronously when the element's node document becomes one
// with a render tree, so the figure server logged GET /fig.png while the placeholder stood, and the harness logged a
// GET /fig.png against the page before the one through /file; in Chromium and Firefox both logs held no line for either
// figure before the chain ran, so both scenes were green there (measured 2026-09-20 at the base 2d41e5c9b; the engines'
// scheduling of the fetch was not instrumented, the logs were read). Each engine is its own test
// and skips, saying so, when its binary is absent. Synthetic values only: an invented note, TESTHOST paths, a placeholder
// sid, .test hosts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as http from "node:http";
import * as path from "node:path";
import type { AddressInfo } from "node:net";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));   // playwright and esbuild from the extension, wherever this bundle was written
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");

const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/tmp/TESTHOST/notes-api";
const DIR = ROOT + "/docs/";
const REMOTE_NOTE_PATH = DIR + "figure.md";
const LOCAL_NOTE_PATH = DIR + "local.md";
const FIGURE = "http://remote.test/fig.png";
const REMOTE_NOTE = "# One figure\n\nBefore ![fig](" + FIGURE + ") after.\n\nLast para.\n";
const LOCAL_NOTE = "# A figure of the folder\n\nBefore ![local](fig.png) after.\n";
const LABEL = "Image from remote.test. Click to load.";
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "base64");
/** The /file URL rewriteFigureSrcs gives a figure of the note's folder (preview.ts fileUrl: the path encoded whole, then the sid). */
const FILE_URL = (name: string) => "/file?path=" + encodeURIComponent(DIR + name) + "&sid=" + SID;

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files pane's bundle plus the real sanitizer, for the premise probe. */
function filesBundle(): string {
  const contents = 'import "./files";\nimport { sanitizeMd } from "./md-sanitize";\n(window as any).__rompProbe = { sanitizeMd };\n';
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" } });
  return r.outputFiles[0].text;
}
// the pane's poster answers the comments panel's status asks with an empty status (file-view-figures-gate-browser.test.ts's shape)
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane>
<div id=files-empty></div>
<script>
window.acquireVsCodeApi = function () { return { postMessage: function (m) {
  if (m.type === "fileComments") {
    var root = ${JSON.stringify(ROOT)};
    var s = { verb: "status", root: root, storePath: root + "/.trackchanges/" + m.path.slice(root.length + 1) + ".json", trackedBy: null, agentTooling: "present",
      fileMtimeNs: "1", storeMtimeNs: null, configMtimeNs: null, store: null, hunks: [], unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null }, log: [] };
    setTimeout(function () { window.postMessage(Object.assign({ type: "fileCommentsResult", reqId: m.reqId }, s), "*"); }, 0);
  }
} }; };
</script>
<script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

/** One request as a server saw it: the method, the request target as sent, and the headers that say who asked for what. */
type Line = { method: string; url: string; host: string; referer: string | null; ua: string };
const lineOf = (req: http.IncomingMessage): Line => ({
  method: req.method || "", url: req.url || "", host: String(req.headers.host || ""),
  referer: typeof req.headers.referer === "string" ? req.headers.referer : null, ua: String(req.headers["user-agent"] || ""),
});
/** The lines naming a file: the request target ends in `/<name>`, or names it as a /file path (percent-encoded, the last segment). */
const forPng = (lines: Line[], name: string): Line[] => lines.filter((l) => l.url.endsWith("/" + name) || l.url.includes("%2F" + name + "&"));
const show = (lines: Line[]): string => JSON.stringify(lines.map((l) => l.method + " " + l.url + " host=" + l.host + (l.referer !== null ? " referer=" + l.referer : "") + " ua=" + l.ua));

function listen(server: http.Server): Promise<number> {
  return new Promise((resolve, reject) => {
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => resolve((server.address() as AddressInfo).port));
  });
}
async function shut(server: http.Server): Promise<void> {
  server.closeAllConnections();
  await new Promise<void>((r) => server.close(() => r()));
}

/** The figure server: logs every request, answers a PNG for any .png and 404 for the rest. */
function figureServer(log: Line[]): http.Server {
  return http.createServer((req, res) => {
    log.push(lineOf(req));
    if (/\.png$/.test(req.url || "")) { res.writeHead(200, { "content-type": "image/png", "content-length": String(PNG.length) }); res.end(PNG); return; }
    res.writeHead(404); res.end();
  });
}
/** The harness server (romp.test through the proxy): the pane page, its bundle, the two notes and the folder's figure through
 *  /file, and the sentinel; every request logged. The kernel's Referrer-Policy rides on every response, as it does on every
 *  page the kernel serves (kernel.py, the header's comment), so what the figure server sees in Referer is what it would see
 *  from the dashboard. */
function harnessServer(js: string, log: Line[]): http.Server {
  return http.createServer((req, res) => {
    log.push(lineOf(req));
    const u = new URL(req.url || "/", "http://romp.test");
    const head = (status: number, type: string, extra: Record<string, string> = {}) => res.writeHead(status, { "content-type": type, "referrer-policy": "same-origin", "cache-control": "no-store", ...extra });
    if (u.pathname === "/files") { head(200, "text/html; charset=utf-8"); res.end(FILES_HTML); return; }
    if (u.pathname === "/dist/files.js") { head(200, "application/javascript"); res.end(js); return; }
    if (u.pathname === "/file") {
      const p = u.searchParams.get("path") || "";
      const note = p === REMOTE_NOTE_PATH ? REMOTE_NOTE : p === LOCAL_NOTE_PATH ? LOCAL_NOTE : null;
      if (note !== null) { head(200, "text/plain; charset=utf-8", { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }); res.end(note); return; }
      if (p === DIR + "fig.png") { head(200, "image/png"); res.end(PNG); return; }
    }
    if (u.pathname.startsWith("/sentinel/")) { head(200, "text/plain"); res.end("ok"); return; }
    head(404, "text/plain"); res.end("");
  });
}
/** An HTTP forward proxy: every request the browser hands it is logged, then forwarded to the 127.0.0.1 port `map` gives
 *  its hostname, the Host header kept as the browser sent it; a hostname outside the map answers 502. Plain http only: the
 *  scene has no https, so no CONNECT arrives. */
function proxyServer(map: Record<string, number>, log: Line[]): http.Server {
  const server = http.createServer((req, res) => {
    let u: URL;
    try { u = new URL(req.url || ""); } catch { res.writeHead(400); res.end(); return; }
    log.push(lineOf(req));
    const port = map[u.hostname];
    if (!port) { res.writeHead(502); res.end(); return; }
    const headers: http.OutgoingHttpHeaders = { ...req.headers };
    delete headers["proxy-connection"];
    const out = http.request({ host: "127.0.0.1", port, method: req.method, path: u.pathname + u.search, headers }, (r) => {
      res.writeHead(r.statusCode || 502, r.headers);
      r.pipe(res);
    });
    out.on("error", () => { if (!res.headersSent) res.writeHead(502); res.end(); });
    req.on("error", () => { out.destroy(); });
    req.pipe(out);
  });
  server.on("clientError", (_e, socket) => { socket.destroy(); });
  return server;
}

type Scene = { page: any; errors: string[]; figureLog: Line[]; proxyLog: Line[]; harnessLog: Line[]; open: (p: string) => Promise<void>; drain: () => Promise<void> };
/** The three servers, the engine launched through the proxy, the pane page open. `open` posts the pane's relay for a note and
 *  awaits a fresh rendered box; `drain` makes one round trip through the proxy to the harness and waits a beat, so a request
 *  the engine issued before it has reached the logs. */
async function inEngine(t: any, engine: "chromium" | "firefox" | "webkit", body: (s: Scene) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser legs need it (CI installs no browsers)"); return; }
  const figureLog: Line[] = [], proxyLog: Line[] = [], harnessLog: Line[] = [];
  const figures = figureServer(figureLog);
  const harness = harnessServer(filesBundle(), harnessLog);
  const figurePort = await listen(figures), harnessPort = await listen(harness);
  const proxy = proxyServer({ "remote.test": figurePort, "romp.test": harnessPort }, proxyLog);
  const proxyPort = await listen(proxy);
  let browser: any = null;
  try {
    try { browser = await pw[engine].launch({ proxy: { server: "http://127.0.0.1:" + proxyPort } }); }
    catch (e) { t.skip("no playwright " + engine + " on this box; this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    const errors: string[] = [];
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.goto("http://romp.test/files");
    let n = 0;
    const drain = async () => {
      n++;
      const status = await page.evaluate((k: number) => fetch("/sentinel/" + k, { cache: "no-store" }).then((r) => r.status), n);
      assert.equal(status, 200, "the sentinel went through the proxy to the harness");
      await page.waitForTimeout(250);
    };
    const open = async (p: string) => {
      await page.evaluate(() => { const md = document.querySelector("#romp-fileview .fileview-md"); if (md) (md as any).__old = true; });
      await page.evaluate(([f, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: f, sid }, "*"); }, [p, SID] as [string, string]);
      await page.waitForFunction(() => { const md = document.querySelector("#romp-fileview .fileview-body .fileview-md"); return !!md && !(md as any).__old; }, null, { timeout: 15000 });
    };
    await body({ page, errors, figureLog, proxyLog, harnessLog, open, drain });
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    if (browser) await browser.close();
    await Promise.all([shut(proxy), shut(harness), shut(figures)]);
  }
}

for (const engine of ["chromium", "firefox", "webkit"] as const) {
  test(engine + ": while the placeholder for a figure on an unlisted host is on screen, the figure server and the proxy have logged no request for it; the sanitizer's body is an inert document's and a figure in it fetches nothing, where a live-document img fetches; the click makes exactly one request, under the unlisted Host, with no Referer", { timeout: 120000 }, async (t) => {
    await inEngine(t, engine, async (s) => {
      const { page } = s;
      // the note opens through the pane's relay; the placeholder, and its label, on screen
      await s.open(REMOTE_NOTE_PATH);
      const label = page.locator('#romp-fileview .fileview-body .fileview-md .fv-gate[data-fv-host="remote.test"] [data-fv-label]');
      await label.waitFor({ state: "visible", timeout: 15000 });
      assert.equal(await label.textContent(), LABEL);
      const gated: string | null = await page.evaluate(() => (document.querySelector('#romp-fileview .fv-gate[data-fv-host="remote.test"] img') as HTMLElement).getAttribute("data-fv-gated-src"));
      assert.equal(gated, FIGURE, "the figure's src is moved aside under the placeholder");
      await s.drain();
      assert.equal(show(forPng(s.figureLog, "fig.png")), "[]", engine + ": the figure server logged a request for the figure while the placeholder stood; the proxy's lines for it: " + show(forPng(s.proxyLog, "fig.png")));
      assert.equal(show(forPng(s.proxyLog, "fig.png")), "[]", engine + ": the proxy logged a request for the figure while the placeholder stood");
      // the premise, over the real sanitizeMd: its body's document has no browsing context and never loads
      const premise: { other: boolean; view: boolean; src: string | null } = await page.evaluate((u: string) => {
        const body = (window as any).__rompProbe.sanitizeMd('<p><img src="' + u + '" alt="i"></p>') as HTMLElement;
        const doc = body.ownerDocument;
        return { other: doc !== document, view: doc.defaultView === null, src: body.querySelector("img")!.getAttribute("src") };
      }, "http://remote.test/inert-probe.png");
      assert.deepEqual(premise, { other: true, view: true, src: "http://remote.test/inert-probe.png" }, "the sanitized body belongs to another document, one with no window, and the img in it keeps its src");
      // the control: an img of the live document, never inserted, fetches in every engine, so a fetch the page makes reaches the logs
      await page.evaluate((u: string) => { const i = document.createElement("img"); i.src = u; (window as any).__rompControl = i; }, "http://remote.test/live-control.png");
      await s.drain();
      assert.equal(show(forPng(s.figureLog, "inert-probe.png")), "[]", "the inert document's figure fetched nothing");
      assert.equal(forPng(s.figureLog, "live-control.png").length, 1, "the live document's img fetched once, seen by the figure server: " + show(s.figureLog));
      assert.equal(forPng(s.proxyLog, "live-control.png").length, 1, "and by the proxy: " + show(s.proxyLog));
      // the click: the figure loads, exactly once, under the unlisted host's name and with no Referer (the harness sends the
      // kernel's Referrer-Policy, same-origin, so a cross-origin figure request names no page)
      await page.click('#romp-fileview .fv-gate[data-fv-host="remote.test"]');
      await page.waitForFunction((u: string) => { const i = document.querySelector('#romp-fileview .fileview-md img[alt="fig"]') as HTMLImageElement | null; return !!i && i.getAttribute("src") === u && i.complete && i.naturalWidth === 1; }, FIGURE, { timeout: 10000 });
      await s.drain();
      const seen = forPng(s.figureLog, "fig.png");
      assert.equal(seen.length, 1, "one request for the figure after the click: " + show(s.figureLog));
      assert.deepEqual([seen[0].method, seen[0].url, seen[0].host, seen[0].referer], ["GET", "/fig.png", "remote.test", null], "GET /fig.png under Host remote.test, no Referer");
      assert.ok(seen[0].ua.length > 0, "the request names its user agent");
      assert.equal(forPng(s.proxyLog, "fig.png").map((l) => l.method + " " + l.url).join(","), "GET " + FIGURE, "the proxy carried that one request and no other for the figure");
      assert.equal(await page.evaluate(() => document.querySelectorAll("#romp-fileview .fv-gate").length), 0, "the placeholder is gone");
    });
  });

  test(engine + ": a figure of the note's own folder is requested once, through /file as rewriteFigureSrcs repointed it, and never as the page-relative path the attribute named before the rewrite", { timeout: 120000 }, async (t) => {
    await inEngine(t, engine, async (s) => {
      const { page } = s;
      await s.open(LOCAL_NOTE_PATH);
      await page.waitForFunction(() => { const i = document.querySelector('#romp-fileview .fileview-md img[alt="local"]') as HTMLImageElement | null; return !!i && i.complete; }, null, { timeout: 15000 });
      const shown: { src: string | null; fv: string | null; w: number } = await page.evaluate(() => { const i = document.querySelector('#romp-fileview .fileview-md img[alt="local"]') as HTMLImageElement; return { src: i.getAttribute("src"), fv: i.getAttribute("data-fv-src"), w: i.naturalWidth }; });
      assert.deepEqual(shown, { src: FILE_URL("fig.png"), fv: "fig.png", w: 1 }, "the picture shows from /file, the authored src kept beside it");
      await s.drain();
      const lines = forPng(s.harnessLog, "fig.png").map((l) => l.method + " " + l.url);
      assert.deepEqual(lines, ["GET " + FILE_URL("fig.png")], engine + ": the harness saw exactly the one request through /file, and none for the page-relative /fig.png: " + JSON.stringify(lines));
      assert.equal(show(forPng(s.figureLog, "fig.png")), "[]", "nothing for the figure server: a figure of the folder names no other host");
    });
  });
}
