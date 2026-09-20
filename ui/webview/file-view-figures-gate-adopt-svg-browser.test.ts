// The second vector of the gate-before-adoption fix (file-view-figures-gate-adopt-browser.test.ts holds the first): an
// inline svg's `<image>`, whose `href` or `xlink:href` names a host outside the allowed list. The first leg's three scenes
// hold HTML <img> figures, and at the base 2d41e5c9b (the chain after the adoption) only WebKit fetched one; an svg image
// is loaded by another path, and at the base Firefox requested a gated one, in either spelling, while its placeholder
// stood when the chain's work between the adoption and that element's strip (the anchor pass over the note,
// rewriteFigureSrcs, the gate's walk to the element) was long, and WebKit requested the `xlink:href` spelling in every run
// and the `href` one in none: a probe in the review adopted an svg image alone and WebKit requested nothing in either
// spelling, then wrote `href` on the adopted element and WebKit requested it, so the fetch there is the repoint pass's
// fold of `xlink:href` into `href`, written over the adopted element before the gate's strip in the next statement. The
// note here is that shape: a long run of paragraphs, then one svg image spelt `href` on `remote.test` and one spelt
// `xlink:href` on `other.test`, a host each, since a click loads a HOST and restores every placeholder waiting on it
// (figure-gate.ts loadGatedHost). The instrument is the first leg's: the REAL Files bundle in each of Playwright's three
// engines, three real servers on 127.0.0.1 (one figure server answering for both unlisted hosts, a harness server for
// romp.test with the kernel's Referrer-Policy on every response, an HTTP forward proxy the browser is launched through,
// which logs every request and forwards by hostname), and the servers' request logs read, never page.route or
// context.route. The scene: the note opens through the pane's own relay, the leg waits for both placeholders to be on
// screen, drains the network with a sentinel fetch and asserts that neither log holds a request for either figure; then it
// clicks the placeholders one at a time and asserts exactly one request per click, with the method, the path and the Host
// header the figure server saw and no Referer, the other figure still unrequested between the clicks.
// Measured 2026-09-20 at the base 2d41e5c9b, this leg copied there: red in Firefox (both svg figures requested while the
// placeholders stood; the assertion names the engine and the lines) and red in WebKit (the `xlink:href` figure requested
// while its placeholder stood, the `href` one not), green in Chromium; at the fix, green in all three engines. Each engine
// is its own test and skips, saying so, when its binary is absent. Where it skips (CI installs no engine before npm test),
// file-view-figures-gate-adopt.test.ts executes the order under plain node, the attributes at the adoption and every write of
// one, with no bytes to see. Synthetic values only: an invented note, TESTHOST paths, a placeholder sid, .test hosts.
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
const NOTE_PATH = DIR + "drawings.md";
const HREF_FIGURE = "http://remote.test/drawing-href.png";
const XLINK_FIGURE = "http://other.test/drawing-xlink.png";
/** The paragraphs before the figures, a link in each: at the base the anchor pass over them (`a[*|href]`, between the adoption
 *  and the gate) is the chain's work that put the strip past Firefox's cancel window in the runs that sized this: 400 plain
 *  paragraphs, 2000 plain ones, 400 with a link, code and emphasis each, and forty svg figures before these two each left the
 *  request out in one run of three or none, 3000 paragraphs with a link each in three of three (the `href` figure, Firefox
 *  alone). The leg's own three base runs, both figures, are at the top of this file; the plan section "Fix: the gate before
 *  adoption (2026-09-20)" holds every count under "Run counts, the svg vectors". */
const PARAGRAPHS = 3000;
const NOTE = "# Drawings at the end of a long note\n\n"
  + Array.from({ length: PARAGRAPHS }, (_, i) => "Paragraph " + (i + 1) + " with a [link](https://example.test/p/" + (i + 1) + "), prose the reader scrolls past on the way to the drawings.\n\n").join("")
  + '<svg width="10" height="10"><image href="' + HREF_FIGURE + '" width="10" height="10"/></svg>\n\n'
  + '<svg width="10" height="10"><image xlink:href="' + XLINK_FIGURE + '" width="10" height="10"/></svg>\n';
const LABEL = (host: string) => "Image from " + host + ". Click to load.";
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "base64");

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files pane's bundle, as the kernel serves it. */
function filesBundle(): string {
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents: 'import "./files";\n', resolveDir: UI, loader: "ts", sourcefile: "files-entry.ts" } });
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
/** The lines naming a file: the request target ends in `/<name>`. */
const forPng = (lines: Line[], name: string): Line[] => lines.filter((l) => l.url.endsWith("/" + name));
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
/** Waits until `count` lines name the file in `log`, or `ms` pass; the caller asserts the count afterwards either way. */
async function untilLogged(log: Line[], name: string, count: number, ms: number): Promise<void> {
  const until = Date.now() + ms;
  while (forPng(log, name).length < count && Date.now() < until) await new Promise((r) => setTimeout(r, 50));
}

/** The figure server, answering for both unlisted hosts: logs every request, answers a PNG for any .png and 404 for the rest. */
function figureServer(log: Line[]): http.Server {
  return http.createServer((req, res) => {
    log.push(lineOf(req));
    if (/\.png$/.test(req.url || "")) { res.writeHead(200, { "content-type": "image/png", "content-length": String(PNG.length) }); res.end(PNG); return; }
    res.writeHead(404); res.end();
  });
}
/** The harness server (romp.test through the proxy): the pane page, its bundle, the note and the sentinel; every request
 *  logged, the kernel's Referrer-Policy on every response as the kernel sends it (kernel.py, the header's comment). */
function harnessServer(js: string, log: Line[]): http.Server {
  return http.createServer((req, res) => {
    log.push(lineOf(req));
    const u = new URL(req.url || "/", "http://romp.test");
    const head = (status: number, type: string, extra: Record<string, string> = {}) => res.writeHead(status, { "content-type": type, "referrer-policy": "same-origin", "cache-control": "no-store", ...extra });
    if (u.pathname === "/files") { head(200, "text/html; charset=utf-8"); res.end(FILES_HTML); return; }
    if (u.pathname === "/dist/files.js") { head(200, "application/javascript"); res.end(js); return; }
    if (u.pathname === "/file" && u.searchParams.get("path") === NOTE_PATH) { head(200, "text/plain; charset=utf-8", { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }); res.end(NOTE); return; }
    if (u.pathname.startsWith("/sentinel/")) { head(200, "text/plain"); res.end("ok"); return; }
    head(404, "text/plain"); res.end("");
  });
}
/** An HTTP forward proxy: every request the browser hands it is logged, then forwarded to the 127.0.0.1 port `map` gives
 *  its hostname, the Host header kept as the browser sent it; a hostname outside the map answers 502. Plain http only. */
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

type Scene = { page: any; errors: string[]; figureLog: Line[]; proxyLog: Line[]; open: (p: string) => Promise<void>; drain: () => Promise<void> };
/** The three servers, the engine launched through the proxy, the pane page open. `open` posts the pane's relay for a note and
 *  awaits a fresh rendered box; `drain` makes one round trip through the proxy to the harness and waits 250 ms, so a request
 *  the engine issued before it has reached the logs. */
async function inEngine(t: any, engine: "chromium" | "firefox" | "webkit", body: (s: Scene) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser legs need it (CI installs no browsers); file-view-figures-gate-adopt.test.ts, the node scene, is the guard that runs where this leg skips"); return; }
  const figureLog: Line[] = [], proxyLog: Line[] = [], harnessLog: Line[] = [];
  const figures = figureServer(figureLog);
  const harness = harnessServer(filesBundle(), harnessLog);
  const figurePort = await listen(figures), harnessPort = await listen(harness);
  const proxy = proxyServer({ "remote.test": figurePort, "other.test": figurePort, "romp.test": harnessPort }, proxyLog);
  const proxyPort = await listen(proxy);
  let browser: any = null;
  try {
    try { browser = await pw[engine].launch({ proxy: { server: "http://127.0.0.1:" + proxyPort } }); }
    catch (e) { t.skip("no playwright " + engine + " on this box; this leg needs it (CI installs none; file-view-figures-gate-adopt.test.ts, the node scene, runs where this leg skips): " + String((e as Error).message).split("\n")[0]); return; }
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
    await body({ page, errors, figureLog, proxyLog, open, drain });
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    if (browser) await browser.close();
    await Promise.all([shut(proxy), shut(harness), shut(figures)]);
  }
}

/** The placeholder naming `host`, in the rendered note. */
const GATE = (host: string) => '#romp-fileview .fileview-body .fileview-md .fv-gate[data-fv-host="' + host + '"]';
type Held = { gatedHref: string | null; href: string | null; xlink: string | null };
/** What the svg image under `host`'s placeholder carries: the moved value, and the two spellings of the live attribute (both must be gone). */
const heldUnder = (host: string): Held => {
  const img = document.querySelector('#romp-fileview .fv-gate[data-fv-host="' + host + '"] image') as Element;
  return { gatedHref: img.getAttribute("data-fv-gated-href"), href: img.getAttribute("href"), xlink: img.getAttributeNS("http://www.w3.org/1999/xlink", "href") };
};

for (const engine of ["chromium", "firefox", "webkit"] as const) {
  test(engine + ": two inline svg images on unlisted hosts at the end of a long note, one spelt href and one xlink:href: while their placeholders are on screen the figure server and the proxy have logged no request for either; each click makes exactly one request, under that unlisted Host, with no Referer, and leaves the other figure unrequested", { timeout: 120000 }, async (t) => {
    await inEngine(t, engine, async (s) => {
      const { page } = s;
      await s.open(NOTE_PATH);
      const hrefLabel = page.locator(GATE("remote.test") + " [data-fv-label]"), xlinkLabel = page.locator(GATE("other.test") + " [data-fv-label]");
      await hrefLabel.waitFor({ state: "visible", timeout: 15000 });
      await xlinkLabel.waitFor({ state: "visible", timeout: 15000 });
      assert.equal(await page.evaluate(() => document.querySelectorAll("#romp-fileview .fv-gate").length), 2, "one placeholder per svg");
      assert.deepEqual([await hrefLabel.textContent(), await xlinkLabel.textContent()], [LABEL("remote.test"), LABEL("other.test")]);
      assert.deepEqual(await page.evaluate(heldUnder, "remote.test"), { gatedHref: HREF_FIGURE, href: null, xlink: null }, "the href figure's attribute is moved aside under the placeholder");
      assert.deepEqual(await page.evaluate(heldUnder, "other.test"), { gatedHref: XLINK_FIGURE, href: null, xlink: null }, "the xlink:href figure's attribute is moved aside under the placeholder");
      await s.drain();
      const both = (log: Line[]) => [...forPng(log, "drawing-href.png"), ...forPng(log, "drawing-xlink.png")];
      assert.equal(show(both(s.figureLog)), "[]", engine + ": the figure server logged a request for a figure while the placeholders stood; the proxy's lines for them: " + show(both(s.proxyLog)));
      assert.equal(show(both(s.proxyLog)), "[]", engine + ": the proxy logged a request for a figure while the placeholders stood");
      // the first click: the href figure loads, exactly once, under its host's name and with no Referer (the harness sends
      // the kernel's Referrer-Policy, same-origin, so a cross-origin figure request names no page); the other host's stands
      await page.click(GATE("remote.test"));
      await untilLogged(s.figureLog, "drawing-href.png", 1, 10000);
      await s.drain();
      let seen = forPng(s.figureLog, "drawing-href.png");
      assert.equal(seen.length, 1, "one request for the href figure after its click: " + show(s.figureLog));
      assert.deepEqual([seen[0].method, seen[0].url, seen[0].host, seen[0].referer], ["GET", "/drawing-href.png", "remote.test", null], "GET /drawing-href.png under Host remote.test, no Referer");
      assert.ok(seen[0].ua.length > 0, "the request names its user agent");
      assert.equal(forPng(s.proxyLog, "drawing-href.png").map((l) => l.method + " " + l.url).join(","), "GET " + HREF_FIGURE, "the proxy carried that one request and no other for the figure");
      assert.equal(show(forPng(s.figureLog, "drawing-xlink.png")), "[]", "the other figure is still unrequested");
      assert.equal(await page.evaluate(() => Array.from(document.querySelectorAll("#romp-fileview .fv-gate")).map((g) => g.getAttribute("data-fv-host")).join(",")), "other.test", "the other host's placeholder is the one left");
      assert.equal(await page.evaluate(() => (document.querySelector('#romp-fileview .fileview-md svg image[href]') as Element).getAttribute("href")), HREF_FIGURE, "the restored figure carries its href again");
      // the second click: the xlink:href figure, the same way (the gate moves either spelling to data-fv-gated-href and restores a plain href)
      await page.click(GATE("other.test"));
      await untilLogged(s.figureLog, "drawing-xlink.png", 1, 10000);
      await s.drain();
      seen = forPng(s.figureLog, "drawing-xlink.png");
      assert.equal(seen.length, 1, "one request for the xlink:href figure after its click: " + show(s.figureLog));
      assert.deepEqual([seen[0].method, seen[0].url, seen[0].host, seen[0].referer], ["GET", "/drawing-xlink.png", "other.test", null], "GET /drawing-xlink.png under Host other.test, no Referer");
      assert.equal(forPng(s.proxyLog, "drawing-xlink.png").map((l) => l.method + " " + l.url).join(","), "GET " + XLINK_FIGURE, "the proxy carried that one request and no other for the figure");
      assert.equal(forPng(s.figureLog, "drawing-href.png").length, 1, "the first figure was not requested again");
      assert.equal(await page.evaluate(() => document.querySelectorAll("#romp-fileview .fv-gate").length), 0, "the placeholders are gone");
    });
  });
}
