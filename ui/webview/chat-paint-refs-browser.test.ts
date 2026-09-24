// The render path's witness for the paint strip (paint-refs.ts dropRemoteRefs, run inside md-sanitize.ts sanitizeMd by
// default): an inline svg in a chat message whose paint attribute (`fill`, `stroke`, `mask`, `clip-path`, `filter`, a
// `marker-*`) holds a url() naming a document on another origin made Chromium request that document the moment the message
// rendered, with no click, because the sanitizer keeps all eight attributes and nothing after it on the chat's path read
// them. The instrument is two real servers' request logs, never the page's request events and never a route (the rule in
// file-view-figures-gate-adopt-browser.test.ts's header). The page server at http://localhost:P serves the chat page as
// the dashboard serves it (the shared skeleton, the chat's sheet, a fake acquireVsCodeApi, the chat bundle built from this
// tree) with the headers every kernel page carries, read from kernel/kernel.py's Handler._send, so a
// request carries the Referer the dashboard's `Referrer-Policy: same-origin` gives it. The remote
// logger at http://127.0.0.1:Q records the method, the path, the Referer and the Sec-Fetch-Dest of every request. A posted
// session frame puts one user message and one assistant reply through render.ts's own userMd() and md(). The reply holds
// every spelling the viewer gate's leg holds (md-config-svg-paint-gate-browser.test.ts), aimed at the remote logger, plus
// a style attribute with mask-image and background-image (the colour-only style hook removes those before the paint pass
// sees them) and a cursor attribute (DOMPurify drops it); the user message holds four of the shapes. The controls: a
// same-document `url(#g)`, a raster `data:` mask, and three references to the page's own origin (an absolute one in each
// message and a relative one), which the strip keeps and the browser requests from the page server. Those three requests
// are the positive control: the messages rendered and a paint fetch reaches a server log, so an empty remote log is the
// strip's work and not a render that never happened. The remote logger's own control follows the read: a no-cors fetch
// from the page to it, which must be its one line, so an empty log is not a server the page cannot reach. The wait is on
// the control's arrival (bounded), then a drain: one round trip to the page server and 250 ms (the viewer's legs' drain).
// Red before the fix, the same at the fork point 6cf6839ba and at the base fa3ef54b5, the merge-base (this leg run from a
// copy of each tree, paint-refs.ts copied beside it for the import alone, since neither tree's sanitizer calls it) and with
// the pass removed from sanitizeMd (2026-09-23, Chromium 151): the remote logger held 19 requests within 30 ms of the
// page's own paint fetch, 16 from the reply (fill, stroke, clip-path, mask, the mask's image-set, the three markers, the
// root's fill, the group's fill, both escaped function names, the userinfo spelling, the quoted and the spaced url(), the
// protocol-relative one) and 3 from the user's message (fill, the mask's image-set, marker-end). Each carried no Referer
// but the three mask references, which carried the page's origin alone (`http://localhost:P/`), none its path. `filter`, on
// a rect and on the root, reached the logger in no run, as the design note's matrix found, and neither did the HTML span's
// names, the style attribute or the cursor, which the sanitizer already removes; the DOM still held 24 of the 26 remote
// values as written. Sub-tests 2, 3 and 5 red, the controls green. Each other sub-test's red is its own mutation, recorded
// with the branch's other reds.
// The second test is the witness of the data: rule (paint-refs.ts DATA_RASTER_TYPES and dataMediaType): in Firefox 153 a
// paint attribute that names a data: SVG, XHTML or XML document with a fragment loads it as a resource document, and that
// document's own @import fetches another host as the message renders. It drives Chromium always, and Firefox and WebKit
// when ROMP_BROWSER_ENGINES names them (a comma list; any other name fails the test, a named engine that does not launch
// fails it too, and the log names the engines that ran). In each engine the chat page gets one user message (userMd: the
// five attributes fill, stroke, mask, filter and clip-path, each naming a data: SVG document with its fragment and an
// @import of its own on the remote logger) and one reply (md(): the same five, the six other spellings Firefox loads the
// same way, each on a fill (upper case, a charset parameter, base64, application/xhtml+xml, text/xml and application/xml),
// and a data: URL with no type). The controls stay as written: url(#g), the page's own fill and mask (the mask is
// requested from the page server in every engine: the positive control), a raster data: mask, and a data: URL typed
// image/png whose body is an svg with an @import (kept by the rule and loaded by no engine). After the render the page
// sets the same documents, unsanitized, outside both bubbles, and the wait is for the loads the engine makes of them
// (CONTROL_LOADS: all eleven in Firefox, none in Chromium or WebKit, which load no data: paint document), then a drain of
// one round trip and 1.5 s. Asserted per engine: no request at the remote logger from either message's documents, every
// document reference removed from its element, the controls as written, the kept raster mask drawing (its left half red
// and its right half not, in Chromium and Firefox; WebKit 26.5 applies no data: mask) and no page error. Red with
// b4f9139b8's paint-refs.ts and md-sanitize.ts (2026-09-24, Playwright 1.62.1): in Firefox 153 the remote logger held the
// sixteen @imports of the messages' documents (the reply's eleven and the user's five, each with Sec-Fetch-Dest style
// and no Referer), and the removal sub-test was red in all three engines; the controls, the control loads and the drawing
// were green there, since the rule changes only what is removed.
// The third test is the browser census of paint-refs.ts's two sets: S_css (the CSS properties whose value takes a url(),
// by CSS.supports over every property the engine knows with eighteen value templates) and S_attr (the attribute names
// whose computed style on an svg rect carries a url() when set through innerHTML, over every known property plus
// DOMPurify's attribute lists), re-derived in the installed Chromium by the methods paint-refs.ts's header states, and
// held to be subsets of URL_PROPERTIES and URL_ATTRS, so an engine that starts reading a url() from a new name reds the
// data. Chromium alone, through the shared launcher (real-viewer-leg.ts inBrowser), which skips loudly without a browser
// (CI installs none before npm test); the node pins in paint-refs.test.ts, paint-refs-census.test.ts and
// md-sanitize.test.ts hold the strip where this leg skips. Synthetic values only: loopback servers, TESTHOST paths, .invalid
// hosts, placeholder uuids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as http from "node:http";
import * as path from "node:path";
import * as zlib from "node:zlib";
import type { AddressInfo } from "node:net";
import { chatBody, ATTACH_TITLE_WEB } from "../../vscode-extension/src/page-skeleton";
import { EXT, UI, requireCjs, inBrowser } from "./real-viewer-leg";
import { URL_ATTRS, URL_PROPERTIES } from "./paint-refs";

const REPO = path.resolve(EXT, "..");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace(/^@import [^\n]*\n/m, "");
const KERNEL = fs.readFileSync(path.join(REPO, "kernel", "kernel.py"), "utf8");
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
const TINY_SVG = '<svg xmlns="http://www.w3.org/2000/svg"><defs><pattern id="p" width="1" height="1"><rect width="1" height="1" fill="blue"/></pattern></defs></svg>';
const SID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
/** A 40 by 40 RGBA PNG, white, its left half opaque and its right half transparent: as a mask it shows the left half of what
 *  it masks. Built here (no binary fixture): each row is filter byte 0 and the pixels, deflated, in the three chunks. */
function halfMaskPng(w = 40, h = 40): string {
  const crc = (buf: Buffer): number => { let c = 0xffffffff; for (const b of buf) { c ^= b; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; } return (c ^ 0xffffffff) >>> 0; };
  const chunk = (tag: string, data: Buffer): Buffer => { const len = Buffer.alloc(4); len.writeUInt32BE(data.length); const body = Buffer.concat([Buffer.from(tag, "latin1"), data]); const sum = Buffer.alloc(4); sum.writeUInt32BE(crc(body)); return Buffer.concat([len, body, sum]); };
  const rows: number[] = [];
  for (let y = 0; y < h; y++) { rows.push(0); for (let x = 0; x < w; x++) rows.push(255, 255, 255, x < w / 2 ? 255 : 0); }
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 6;
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), chunk("IHDR", ihdr), chunk("IDAT", zlib.deflateSync(Buffer.from(rows))), chunk("IEND", Buffer.alloc(0))]).toString("base64");
}
const MASK_PNG = halfMaskPng();

// ── the servers ──────────────────────────────────────────────────────────────────────────────────────

/** The headers every page the kernel serves carries: Handler._send's unconditional `send_header` lines with two literal
 *  arguments, up to its caller-supplied headers loop. Loud when the function's shape moves, so the page is never served
 *  without them in silence. */
function kernelPageHeaders(): Record<string, string> {
  const m = /\n    def _send\(self, code, body, ctype, cache=None, headers=None\):\n([\s\S]*?)\n        for k, v in \(headers or \{\}\)\.items\(\):/.exec(KERNEL);
  assert.ok(m, "kernel/kernel.py Handler._send up to its caller-supplied headers loop (the page is served with the headers read there)");
  const out: Record<string, string> = {};
  for (const h of m![1].matchAll(/^        self\.send_header\("([^"]+)", "([^"]+)"\)/gm)) out[h[1]] = h[2];
  return out;
}

/** One request as a server saw it: the method, the path as sent, the Referer and the Sec-Fetch-Dest, and when it came. */
type Line = { method: string; path: string; referer: string | null; dest: string | null; at: number };
const lineOf = (req: http.IncomingMessage): Line => ({
  method: req.method || "", path: req.url || "", referer: typeof req.headers.referer === "string" ? req.headers.referer : null,
  dest: typeof req.headers["sec-fetch-dest"] === "string" ? req.headers["sec-fetch-dest"] as string : null, at: Date.now(),
});
/** The lines whose path, before any query, ends in `name` (a leading slash included). */
const forFile = (log: Line[], name: string): Line[] => log.filter((l) => l.path.split("?")[0].endsWith(name));
const show = (log: Line[]): string[] => log.map((l) => l.method + " " + l.path + " referer=" + String(l.referer) + " dest=" + String(l.dest));

async function listen(handler: http.RequestListener, host: string): Promise<{ server: http.Server; origin: string }> {
  const server = http.createServer(handler);
  await new Promise<void>((ok, bad) => { server.once("error", bad); server.listen(0, host, () => ok()); });
  return { server, origin: "http://" + host + ":" + (server.address() as AddressInfo).port };
}
async function shut(server: http.Server): Promise<void> {
  server.closeAllConnections();
  await new Promise<void>((r) => server.close(() => r()));
}
/** Waits until `count` lines name the file in `log`, or `ms` pass; the caller asserts the count afterwards either way. */
async function untilLogged(log: Line[], name: string, count: number, ms: number): Promise<void> {
  const until = Date.now() + ms;
  while (forFile(log, name).length < count && Date.now() < until) await new Promise((r) => setTimeout(r, 50));
}

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The chat bundle as the webview build bundles it, from this tree. */
function renderBundle(): string {
  const r = requireCjs("esbuild").buildSync({ ...BUILD, entryPoints: [path.join(UI, "render.ts")] });
  return r.outputFiles[0].text;
}
/** The chat page as the web dashboard serves it: the shared skeleton, the chat's sheet, the kernel shim's role played by a
 *  fake acquireVsCodeApi, then the chat bundle. */
const chatHtml = (): string => `<!DOCTYPE html><html lang=en><head><meta charset=utf-8><style>${STYLES}</style></head><body>
${chatBody(ATTACH_TITLE_WEB)}
<script>window.acquireVsCodeApi=function(){return{postMessage:function(){}}};</script>
<script src=/dist/render.js></script></body></html>`;

// ── the messages ─────────────────────────────────────────────────────────────────────────────────────

/** A remote shape: the class of the element that holds it (an svg, or an HTML span), the element inside it that carries
 *  the attribute (`""` for the classed element itself), the attribute, and the file its url() names on the remote logger. */
type Remote = { cls: string; el: string; attr: string; file: string };
/** A kept control: where it sits and the attribute's value as the page must still hold it. */
type Kept = { cls: string; el: string; attr: string; value: string };
/** An attribute as the page holds it: where (the bubble, the class, the element, the name) and its value, null when absent. */
type Read = { where: string; value: string | null };

const svgOf = (cls: string, inner: string, root = ""): string => '<svg class="' + cls + '" width="12" height="12"' + root + ">" + inner + "</svg>";
const rect = (attrs: string): string => '<rect width="12" height="12" ' + attrs + "/>";
const MARKER_PATH = (attrs: string): string => '<path d="M1 1 L6 6 L11 11" stroke="red" fill="none" ' + attrs + "/>";

/** The assistant's reply: every remote shape, each in a paragraph of its own, and the controls. `R` is the remote logger's
 *  origin, `P` the page's, `hostPort` the remote's host and port as written after a userinfo `@`. */
function replyOf(R: string, P: string, hostPort: string): { md: string; remote: Remote[]; kept: Kept[] } {
  const remote: Remote[] = [
    { cls: "px-fill", el: "rect", attr: "fill", file: "/fill.svg" },
    { cls: "px-stroke", el: "rect", attr: "stroke", file: "/stroke.svg" },
    { cls: "px-filter", el: "rect", attr: "filter", file: "/filter.svg" },
    { cls: "px-clip", el: "rect", attr: "clip-path", file: "/clip.svg" },
    { cls: "px-mask", el: "rect", attr: "mask", file: "/mask.svg" },
    { cls: "px-maskset", el: "rect", attr: "mask", file: "/maskset.png" },
    { cls: "px-marker", el: "path", attr: "marker-start", file: "/ms.svg" },
    { cls: "px-marker", el: "path", attr: "marker-mid", file: "/mm.svg" },
    { cls: "px-marker", el: "path", attr: "marker-end", file: "/me.svg" },
    { cls: "px-rootfill", el: "", attr: "fill", file: "/rootfill.svg" },
    { cls: "px-rootfilter", el: "", attr: "filter", file: "/rootfilter.svg" },
    { cls: "px-group", el: "g", attr: "fill", file: "/group.svg" },
    { cls: "px-escfn", el: "rect", attr: "fill", file: "/escfn.svg" },
    { cls: "px-crlf", el: "rect", attr: "fill", file: "/crlf.svg" },
    { cls: "px-escat", el: "rect", attr: "fill", file: "/escat.svg" },
    { cls: "px-quoted", el: "rect", attr: "fill", file: "/quoted.svg" },
    { cls: "px-spaces", el: "rect", attr: "fill", file: "/spaces.svg" },
    { cls: "px-protorel", el: "rect", attr: "fill", file: "/protorel.svg" },
    { cls: "px-span", el: "", attr: "fill", file: "/htmlfill.svg" },
    { cls: "px-span", el: "", attr: "mask", file: "/htmlmask.svg" },
    { cls: "px-cursor", el: "rect", attr: "cursor", file: "/cursor.png" },
    { cls: "px-stylerect", el: "rect", attr: "style", file: "/style-fill.svg" },
  ];
  const data = 'url("data:image/png;base64,' + MASK_PNG + '")';   // a raster data: mask, the one kind of data: URL that stays
  const kept: Kept[] = [
    { cls: "px-local", el: "rect", attr: "fill", value: "url(#g)" },
    { cls: "px-own", el: "rect", attr: "fill", value: "url(" + P + "/own.svg#p)" },
    { cls: "px-rel", el: "rect", attr: "fill", value: "url(own-rel.svg#p)" },
    { cls: "px-data", el: "rect", attr: "mask", value: data },
    { cls: "px-stylespan", el: "", attr: "style", value: "color: red" },
  ];
  const md = [
    "A reply with inline figures.", "",
    svgOf("px-fill", rect('fill="url(' + R + '/fill.svg#p)"')), "",
    svgOf("px-stroke", rect('fill="none" stroke="url(' + R + '/stroke.svg#p)" stroke-width="4"')), "",
    svgOf("px-filter", rect('fill="red" filter="blur(2px) url(' + R + '/filter.svg#f)"')), "",
    svgOf("px-clip", rect('fill="red" clip-path="url(' + R + '/clip.svg#c)"')), "",
    svgOf("px-mask", rect('fill="red" mask="url(' + R + '/mask.svg#m)"')), "",
    svgOf("px-maskset", rect('fill="red" mask="image-set(&quot;' + R + '/maskset.png&quot; 1x)"')), "",
    svgOf("px-marker", MARKER_PATH('marker-start="url(' + R + '/ms.svg#a)" marker-mid="url(' + R + '/mm.svg#b)" marker-end="url(' + R + '/me.svg#c)"')), "",
    svgOf("px-rootfill", rect(""), ' fill="url(' + R + '/rootfill.svg#p)"'), "",
    svgOf("px-rootfilter", rect('fill="red"'), ' filter="url(' + R + '/rootfilter.svg#f)"'), "",
    svgOf("px-group", '<g fill="url(' + R + '/group.svg#p)">' + rect("") + "</g>"), "",
    svgOf("px-escfn", rect('fill="\\75 rl(' + R + '/escfn.svg#p)"')), "",
    svgOf("px-crlf", rect('fill="\\75&#13;&#10;rl(' + R + '/crlf.svg#p)"')), "",
    svgOf("px-escat", rect('fill="url(' + P + "\\40 " + hostPort + '/escat.svg#p)"')), "",
    svgOf("px-quoted", rect('fill="url(&quot;' + R + '/quoted.svg#p&quot;)"')), "",
    svgOf("px-spaces", rect('fill="URL(   ' + R + '/spaces.svg#p   ) red"')), "",
    svgOf("px-protorel", rect('fill="url(//' + hostPort + '/protorel.svg#p)"')), "",
    '<span class="px-span" fill="url(' + R + '/htmlfill.svg#p)" mask="url(' + R + '/htmlmask.svg#m)">an HTML span</span>', "",
    svgOf("px-cursor", rect('fill="red" cursor="url(' + R + '/cursor.png), auto"')), "",
    svgOf("px-stylerect", rect('style="fill: url(' + R + '/style-fill.svg#p)"')), "",
    '<span class="px-stylespan" style="mask-image: url(' + R + "/style-mask.png); background-image: url(" + R + '/style-bg.png); color: red">styled</span>', "",
    svgOf("px-local", '<defs><linearGradient id="g"><stop offset="0" stop-color="red"/></linearGradient></defs>' + rect('fill="url(#g)"')), "",
    svgOf("px-own", rect('fill="url(' + P + '/own.svg#p)"')), "",
    svgOf("px-rel", rect('fill="url(own-rel.svg#p)"')), "",
    svgOf("px-data", rect('fill="red" mask="url(&quot;data:image/png;base64,' + MASK_PNG + '&quot;)"')), "",
    "Last paragraph.",
  ].join("\n");
  return { md, remote, kept };
}

/** The user's own message (userMd's grammar, line breaks kept): four remote shapes and the page's own origin. */
function userOf(R: string, P: string): { md: string; remote: Remote[]; kept: Kept[] } {
  const remote: Remote[] = [
    { cls: "pu-fill", el: "rect", attr: "fill", file: "/u-fill.svg" },
    { cls: "pu-maskset", el: "rect", attr: "mask", file: "/u-maskset.png" },
    { cls: "pu-marker", el: "path", attr: "marker-end", file: "/u-me.svg" },
    { cls: "pu-span", el: "", attr: "fill", file: "/u-htmlfill.svg" },
  ];
  const kept: Kept[] = [{ cls: "pu-own", el: "rect", attr: "fill", value: "url(" + P + "/own-user.svg#p)" }];
  const md = [
    "my figures", "",
    svgOf("pu-fill", rect('fill="url(' + R + '/u-fill.svg#p)"')), "",
    svgOf("pu-maskset", rect('fill="red" mask="image-set(&quot;' + R + '/u-maskset.png&quot; 1x)"')), "",
    svgOf("pu-marker", MARKER_PATH('marker-end="url(' + R + '/u-me.svg#c)"')), "",
    '<span class="pu-span" fill="url(' + R + '/u-htmlfill.svg#p)">mine</span>', "",
    svgOf("pu-own", rect('fill="url(' + P + '/own-user.svg#p)"')),
  ].join("\n");
  return { md, remote, kept };
}

const USER_BODY = "#content .turn-user .user-bubble";
const REPLY_BODY = "#content .turn-assistant .md";

test("render path: a chat message's svg paint references to another origin reach no server, the page's own are requested, and the rendered bubbles hold no reference off the page's origin", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const headers = kernelPageHeaders();
    assert.equal(headers["Referrer-Policy"], "same-origin", "the kernel's pages carry Referrer-Policy: same-origin (the Referer the logs record is the dashboard's): " + JSON.stringify(headers));
    const pageLog: Line[] = [], remoteLog: Line[] = [];
    const renderJs = renderBundle();
    const remote = await listen((req, res) => {
      remoteLog.push(lineOf(req));
      const p = (req.url || "").split("?")[0];
      if (p.endsWith(".svg")) { res.writeHead(200, { "Content-Type": "image/svg+xml" }); res.end(TINY_SVG); return; }
      if (p.endsWith(".png")) { res.writeHead(200, { "Content-Type": "image/png", "Content-Length": String(PNG.length) }); res.end(PNG); return; }
      res.writeHead(404); res.end();
    }, "127.0.0.1");
    const pageSrv = await listen((req, res) => {
      pageLog.push(lineOf(req));
      const p = (req.url || "").split("?")[0];
      const send = (status: number, type: string, body: string | Buffer) => { res.writeHead(status, { ...headers, "Content-Type": type, "Cache-Control": "no-store" }); res.end(body); };
      if (p === "/chat") return send(200, "text/html; charset=utf-8", chatHtml());
      if (p === "/dist/render.js") return send(200, "application/javascript", renderJs);
      if (p === "/own.svg" || p === "/own-rel.svg" || p === "/own-user.svg") return send(200, "image/svg+xml", TINY_SVG);
      if (p.startsWith("/sentinel/")) return send(200, "text/plain", "ok");
      send(404, "text/plain", "");
    }, "localhost");
    const R = remote.origin, P = pageSrv.origin, hostPort = R.slice("http://".length);
    const errors: string[] = [];
    try {
      const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      await page.goto(P + "/chat");
      const reply = replyOf(R, P, hostPort), user = userOf(R, P);
      await page.evaluate(([sid, u, a]: [string, string, string]) => {
        window.postMessage({ type: "session", id: sid, name: "web", cwd: "/tmp/TESTHOST/notes-api", status: { state: "idle", sinceEpoch: null },
          events: [{ kind: "user", human: true, md: u, uuid: "11111111-2222-4333-8444-555555555551" }, { kind: "assistant", md: a, uuid: "11111111-2222-4333-8444-555555555552" }] }, "*");
      }, [SID, user.md, reply.md] as [string, string, string]);   // `human`: a typed prompt, so senderKind reads "user" and the bubble is userMd's
      await page.waitForSelector(REPLY_BODY + " .px-own", { state: "attached", timeout: 15000 });
      await page.waitForSelector(USER_BODY + " .pu-own", { state: "attached", timeout: 15000 });
      // the positive control arrives (bounded), then the drain: one round trip to the page server and 250 ms
      for (const f of ["/own.svg", "/own-rel.svg", "/own-user.svg"]) await untilLogged(pageLog, f, 1, 8000);
      const status = await page.evaluate(() => fetch("/sentinel/1", { cache: "no-store" }).then((r) => r.status));
      assert.equal(status, 200, "the drain's round trip reached the page server");
      await page.waitForTimeout(250);
      const remoteAtDrain = remoteLog.slice();
      const ownArrived = forFile(pageLog, "/own.svg")[0]?.at ?? null;
      console.log("remote logger, at the drain (" + remoteAtDrain.length + " lines; ms after the page's own paint fetch): " + JSON.stringify(remoteAtDrain.map((l) => show([l])[0] + (ownArrived !== null ? " +" + (l.at - ownArrived) + "ms" : ""))));

      // the DOM, read from the rendered bubbles: each remote shape's attribute, each control's value, and every value the
      // engine computes on every element of both bubbles for a property that takes a url() (the browser's own reading, not
      // the strip's reader), with any attribute or computed value naming the remote logger's host and port
      const all = [...reply.remote.map((s) => ({ ...s, body: REPLY_BODY })), ...user.remote.map((s) => ({ ...s, body: USER_BODY }))];
      const kept = [...reply.kept.map((s) => ({ ...s, body: REPLY_BODY })), ...user.kept.map((s) => ({ ...s, body: USER_BODY }))];
      const dom: { remote: Read[]; kept: Read[]; offenders: string[] } = await page.evaluate(([shapes, controls, bodies, props, attrs, hp]: [{ cls: string; el: string; attr: string; body: string }[], { cls: string; el: string; attr: string; body: string }[], string[], string[], string[], string]) => {
        const at = (s: { cls: string; el: string; body: string }): Element | null => {
          const host = document.querySelector(s.body + " ." + s.cls);
          return host && s.el ? host.querySelector(s.el) : host;
        };
        const read = (s: { cls: string; el: string; attr: string; body: string }) => { const e = at(s); return e ? e.getAttribute(s.attr) : "(no element)"; };
        const offenders: string[] = [];
        for (const sel of bodies) for (const body of Array.from(document.querySelectorAll(sel))) {
          for (const el of [body, ...Array.from(body.querySelectorAll("*"))]) {
            const name = el.tagName.toLowerCase() + (el.getAttribute("class") ? "." + el.getAttribute("class") : "");
            for (const a of [...attrs, "style"]) { const v = el.getAttribute(a); if (v !== null && v.includes(hp)) offenders.push(name + " [" + a + "] " + v); }
            const cs = getComputedStyle(el);
            for (const p of props) {
              const v = cs.getPropertyValue(p);
              if (!v) continue;
              if (v.includes(hp)) { offenders.push(name + " computed " + p + ": " + v); continue; }
              for (const m of v.matchAll(/url\("((?:[^"\\]|\\.)*)"\)/g)) {
                const u = m[1];
                if (u.startsWith("#") || u.startsWith("data:")) continue;
                let o = "";
                try { o = new URL(u, document.baseURI).origin; } catch { o = "(unparsable)"; }
                if (o !== location.origin) offenders.push(name + " computed " + p + ": " + v);
              }
            }
          }
        }
        return { remote: shapes.map((s) => ({ where: s.body + " ." + s.cls + (s.el ? " " + s.el : "") + " [" + s.attr + "]", value: read(s) })),
                 kept: controls.map((s) => ({ where: s.body + " ." + s.cls + (s.el ? " " + s.el : "") + " [" + s.attr + "]", value: read(s) })),
                 offenders: Array.from(new Set(offenders)) };
      }, [all, kept, [REPLY_BODY, USER_BODY], [...URL_PROPERTIES], [...URL_ATTRS], hostPort] as [typeof all, typeof kept, string[], string[], string[], string]);

      // the remote logger's own control, after its log was read: the page can reach it, so an empty log is not a dead server
      const reach = await page.evaluate((u: string) => fetch(u, { mode: "no-cors", cache: "no-store" }).then(() => "ok", (e) => String(e)), R + "/reach");
      await untilLogged(remoteLog, "/reach", 1, 5000);

      await t.test("1. the page's own paint references were kept and requested from the page server, the absolute one with the page's full URL as its Referer", () => {
        // guards the positive control: the messages rendered and a paint fetch reaches a server log, so an empty remote log is the strip's work
        for (const f of ["/own.svg", "/own-rel.svg", "/own-user.svg"]) {
          assert.equal(forFile(pageLog, f).length, 1, "the same-origin paint reference " + f + " fetched once from the page's own server: " + JSON.stringify(show(pageLog)));
        }
        assert.equal(forFile(pageLog, "/own.svg")[0].referer, P + "/chat", "a same-origin paint fetch carries the page's full URL (Referrer-Policy same-origin)");
      });
      await t.test("2. no request reached the remote logger for any paint reference on another origin", () => {
        // guards the fix: the sanitizer's paint pass removes every remote url() before the bubble's innerHTML is set
        assert.deepEqual(show(remoteAtDrain), [], "no request left the page for a paint reference on another origin");
      });
      await t.test("3. every remote shape's attribute is removed from its element, which stays", () => {
        // guards the DOM half of the fix: the attribute goes before the bubble is in the page, the element stays and paints
        assert.deepEqual(dom.remote.filter((r) => r.value !== null), [], "each remote reference is removed from its element (an element that went reads \"(no element)\")");
      });
      await t.test("4. the controls are kept as written: a same-document url(#g), a raster data: mask, the page's own origin absolute and relative, a colour-only style", () => {
        // guards the STAYS rule: a strip that also took these would be an over-strip the remote log cannot see
        assert.deepEqual(dom.kept.filter((k, i) => k.value !== kept[i].value), [], "each control keeps its value as written");
      });
      await t.test("5. no attribute or computed value in either bubble names the remote logger or resolves off the page's origin", () => {
        // guards the population: read by the engine's own computed style over every url()-taking property, not by the strip's reader
        assert.deepEqual(dom.offenders, [], "no attribute or computed value in either bubble names the remote logger or resolves off the page's origin");
      });
      await t.test("6. the remote logger's control: a fetch from the page reaches it, once, after the read", () => {
        // guards the harness: without it an empty remote log could be a server the page cannot reach
        assert.equal(reach, "ok", "the page's no-cors fetch to the remote logger completed");
        assert.deepEqual(show(remoteLog.slice(remoteAtDrain.length)).map((l) => l.split(" referer=")[0]), ["GET /reach"], "after the read the remote logger logged the control's fetch, once");
      });
      await t.test("7. no page errors", () => {
        // guards the render: a thrown render would leave the bubbles empty and every other check vacuous
        assert.deepEqual(errors, [], "no page errors");
      });
    } finally {
      await Promise.all([shut(remote.server), shut(pageSrv.server)]);
    }
  });
});

// ── data: documents named by a paint attribute: Chromium always, Firefox and WebKit when ROMP_BROWSER_ENGINES names them ──

const ENGINE_NAMES = ["chromium", "firefox", "webkit"];
/** The engines the data: document test drives: Chromium always, then each engine ROMP_BROWSER_ENGINES names (a comma list),
 *  in its order. A name outside the three fails the test, so a misspelling is never a quiet Chromium-only run. */
function enginesToRun(): { engines: string[]; named: boolean } {
  const asked = (process.env.ROMP_BROWSER_ENGINES || "").split(",").map((e) => e.trim()).filter(Boolean);
  const bad = asked.filter((e) => !ENGINE_NAMES.includes(e));
  assert.deepEqual(bad, [], "ROMP_BROWSER_ENGINES names " + JSON.stringify(bad) + ", outside " + ENGINE_NAMES.join(", "));
  const engines = ["chromium"];
  for (const e of asked) if (!engines.includes(e)) engines.push(e);
  return { engines, named: engines.length > 1 };
}
let playwright: any = null;
try { playwright = requireCjs("playwright"); } catch { playwright = null; }

/** A data: document's markup: an svg whose `<style>` imports `importUrl`, and one element per paint fragment (#p a pattern,
 *  #m a mask, #c a clipPath, #f a filter), so each attribute's fragment names an element of the right kind. */
const docSvg = (importUrl: string): string => "<svg xmlns='http://www.w3.org/2000/svg'><defs><style>@import url(" + importUrl + ");</style>"
  + "<pattern id='p' width='1' height='1'><rect width='1' height='1' fill='blue'/></pattern>"
  + "<mask id='m'><rect width='1' height='1' fill='white'/></mask><clipPath id='c'><rect width='1' height='1'/></clipPath>"
  + "<filter id='f'><feFlood flood-color='blue'/></filter></defs></svg>";
/** The spellings of a data: document that Firefox 153 loaded as a resource document when a paint attribute named it with a
 *  fragment (measured 2026-09-24, on a page with no sanitizer, all five attributes each): the plain one, case, a charset
 *  parameter, base64, and the three XML types. */
const DOC_SPELLINGS: Record<string, (svg: string) => string> = {
  plain: (x) => "data:image/svg+xml," + encodeURIComponent(x),
  upper: (x) => "data:IMAGE/SVG+XML," + encodeURIComponent(x),
  charset: (x) => "data:image/svg+xml;charset=utf-8," + encodeURIComponent(x),
  base64: (x) => "data:image/svg+xml;base64," + Buffer.from(x).toString("base64"),
  xhtml: (x) => "data:application/xhtml+xml," + encodeURIComponent(x),
  textxml: (x) => "data:text/xml," + encodeURIComponent(x),
  appxml: (x) => "data:application/xml," + encodeURIComponent(x),
};
/** Each paint attribute and the fragment its reference names. */
const PAINT_FRAG: Array<[string, string]> = [["fill", "p"], ["stroke", "p"], ["mask", "m"], ["filter", "f"], ["clip-path", "c"]];
/** A data: document shape: the class of its svg, the attribute, the attribute's value as the page must hold it (or not), and
 *  the file its @import names on the remote logger (`""` for a shape whose document no engine loads). */
type DocShape = { cls: string; attr: string; value: string; file: string };
const docRect = (attr: string, value: string, size = 12): string => {
  const v = attr + '="' + value.replace(/"/g, "&quot;") + '"';
  const paint = attr === "fill" ? "" : attr === "stroke" ? 'fill="none" stroke-width="4" ' : 'fill="red" ';
  return '<rect width="' + size + '" height="' + size + '" ' + paint + v + "/>";
};
/** The five attributes, each naming the plain data: document with its fragment, whose @import names `prefix` + attribute. */
function fiveDocs(R: string, cls: string, prefix: string): DocShape[] {
  return PAINT_FRAG.map(([attr, frag]) => ({ cls: cls + "-" + attr, attr, file: "/" + prefix + attr + ".css",
    value: 'url("' + DOC_SPELLINGS.plain(docSvg(R + "/" + prefix + attr + ".css")) + "#" + frag + '")' }));
}
/** The six other spellings, each on a fill. */
function spellingDocs(R: string, cls: string, prefix: string): DocShape[] {
  return Object.keys(DOC_SPELLINGS).filter((k) => k !== "plain").map((k) => ({ cls: cls + "-" + k, attr: "fill", file: "/" + prefix + k + ".css",
    value: 'url("' + DOC_SPELLINGS[k](docSvg(R + "/" + prefix + k + ".css")) + '#p")' }));
}
/** What each engine loaded from the unsanitized control's shapes (the five plain documents and the six spellings), measured
 *  2026-09-24 in Playwright 1.62.1: Firefox 153 all eleven, Chromium 151 and WebKit 26.5 none (they load no data: paint
 *  document, sanitized or not, so in them this test is a DOM witness). */
const CONTROL_LOADS: Record<string, "all" | "none"> = { chromium: "none", firefox: "all", webkit: "none" };
/** The engines whose kept raster data: mask draws (measured 2026-09-24: Chromium 151 and Firefox 153 drew it; WebKit 26.5
 *  applied no data: mask, unsanitized either, so its pixels are not asserted). */
const MASK_DRAWS = ["chromium", "firefox"];
const OWN_MASK_SVG = '<svg xmlns="http://www.w3.org/2000/svg"><defs><pattern id="p" width="1" height="1"><rect width="1" height="1" fill="blue"/></pattern><mask id="m"><rect width="1" height="1" fill="white"/></mask></defs></svg>';

test("data: documents: a chat message's paint reference to a data: SVG, XHTML or XML document is removed before the bubble renders, in every engine that ran, while a raster data: mask stays and draws", { timeout: 300000 }, async (t) => {
  const { engines, named } = enginesToRun();
  if (!playwright) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  const headers = kernelPageHeaders();
  const pageLog: Line[] = [], remoteLog: Line[] = [];
  const renderJs = renderBundle();
  const remote = await listen((req, res) => {
    remoteLog.push(lineOf(req));
    const p = (req.url || "").split("?")[0];
    if (p.endsWith(".css")) { res.writeHead(200, { "Content-Type": "text/css" }); res.end("/* nothing */"); return; }
    res.writeHead(404); res.end();
  }, "127.0.0.1");
  const pageSrv = await listen((req, res) => {
    pageLog.push(lineOf(req));
    const p = (req.url || "").split("?")[0];
    const send = (status: number, type: string, body: string | Buffer) => { res.writeHead(status, { ...headers, "Content-Type": type, "Cache-Control": "no-store" }); res.end(body); };
    if (p === "/chat") return send(200, "text/html; charset=utf-8", chatHtml());
    if (p === "/dist/render.js") return send(200, "application/javascript", renderJs);
    if (/^\/own-d[a-z]+\.svg$/.test(p)) return send(200, "image/svg+xml", OWN_MASK_SVG);
    if (p.startsWith("/sentinel/")) return send(200, "text/plain", "ok");
    send(404, "text/plain", "");
  }, "localhost");
  const R = remote.origin, P = pageSrv.origin;
  // the witness: the reply carries the five attributes and the six spellings, the user's message the five attributes; a
  // data: URL with no type (text/plain, which no engine loads) is removed too and is read in the DOM alone
  const replyDocs = [...fiveDocs(R, "dr", "dr-"), ...spellingDocs(R, "dr", "dr-"),
    { cls: "dr-notype", attr: "fill", file: "", value: 'url("data:,' + encodeURIComponent(docSvg(R + "/dr-notype.css")) + '#p")' }];
  const userDocs = fiveDocs(R, "du", "du-");
  // the controls, kept as written: a same-document url(#g), the page's own fill and mask (the mask is requested in every
  // engine, the positive control that a paint fetch reaches a server log), a raster data: mask, and a raster-labelled data:
  // URL whose body is an svg with an @import (kept, since its type is a raster, and loaded by no engine)
  const rasterMask = 'url("data:image/png;base64,' + MASK_PNG + '")';
  const pngBody = 'url("data:image/png,' + encodeURIComponent(docSvg(R + "/dr-pngbody.css")) + '#p")';
  const kept: DocShape[] = [
    { cls: "dk-local", attr: "fill", value: "url(#g)", file: "" },
    { cls: "dk-ownfill", attr: "fill", value: "url(" + P + "/own-dfill.svg#p)", file: "" },
    { cls: "dk-ownmask", attr: "mask", value: "url(" + P + "/own-dmask.svg#m)", file: "" },
    { cls: "dk-raster", attr: "mask", value: rasterMask, file: "" },
    { cls: "dk-pngbody", attr: "fill", value: pngBody, file: "/dr-pngbody.css" },
  ];
  const userKept: DocShape[] = [
    { cls: "uk-ownmask", attr: "mask", value: "url(" + P + "/own-dumask.svg#m)", file: "" },
    { cls: "uk-raster", attr: "mask", value: rasterMask, file: "" },
  ];
  const svgFor = (s: DocShape): string => {
    const size = s.cls.endsWith("raster") ? 40 : 12;   // the raster mask's rect is the mask's own size, so its halves can be read
    const defs = s.cls === "dk-local" ? '<defs><linearGradient id="g"><stop offset="0" stop-color="red"/></linearGradient></defs>' : "";
    return '<svg class="' + s.cls + '" width="' + size + '" height="' + size + '">' + defs + docRect(s.attr, s.value, size) + "</svg>";
  };
  const replyMd = ["A reply with data: figures.", "", ...[...replyDocs, ...kept].flatMap((s) => [svgFor(s), ""]), "Last paragraph."].join("\n");
  const userMd = ["my data: figures", "", ...[...userDocs, ...userKept].flatMap((s) => [svgFor(s), ""]), "done"].join("\n");
  const controlHtml = [...fiveDocs(R, "dc", "dc-"), ...spellingDocs(R, "dc", "dc-")].map((s) => svgFor(s)).join("");
  const controlFiles = [...fiveDocs(R, "dc", "dc-"), ...spellingDocs(R, "dc", "dc-")].map((s) => s.file).sort();
  const witnessFiles = [...replyDocs, ...userDocs, ...kept].map((s) => s.file).filter(Boolean);
  const ran: string[] = [];
  try {
    for (const engine of engines) {
      let browser: any;
      try { browser = await playwright[engine].launch(); }
      catch (e) {
        const why = String((e as Error).message).split("\n")[0];
        if (!named) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + why); return; }
        assert.fail(engine + " did not launch, and ROMP_BROWSER_ENGINES names engines to run (a named run never skips one): " + why);
      }
      ran.push(engine + " " + browser.version());
      pageLog.length = 0; remoteLog.length = 0;   // one engine's lines at a time
      const errors: string[] = [];
      try {
        const page = await browser.newPage({ viewport: { width: 900, height: 900 } });
        page.on("pageerror", (e: Error) => { errors.push(e.message); });
        await page.goto(P + "/chat");
        await page.evaluate(([sid, u, a]: [string, string, string]) => {
          window.postMessage({ type: "session", id: sid, name: "web", cwd: "/tmp/TESTHOST/notes-api", status: { state: "idle", sinceEpoch: null },
            events: [{ kind: "user", human: true, md: u, uuid: "11111111-2222-4333-8444-555555555553" }, { kind: "assistant", md: a, uuid: "11111111-2222-4333-8444-555555555554" }] }, "*");
        }, [SID, userMd, replyMd] as [string, string, string]);
        await page.waitForSelector(REPLY_BODY + " .dk-raster", { state: "attached", timeout: 15000 });
        await page.waitForSelector(USER_BODY + " .uk-raster", { state: "attached", timeout: 15000 });
        for (const f of ["/own-dmask.svg", "/own-dumask.svg"]) await untilLogged(pageLog, f, 1, 8000);
        // the unsanitized control, outside both bubbles: the same documents set by innerHTML, so the engine's own loads of
        // them are seen at the logger; then the wait for the ones this engine makes (bounded), and the drain
        await page.evaluate((html: string) => { const d = document.createElement("div"); d.id = "data-doc-control"; d.innerHTML = html; document.body.appendChild(d); }, controlHtml);
        if (CONTROL_LOADS[engine] === "all") for (const f of controlFiles) await untilLogged(remoteLog, f, 1, 10000);
        const status = await page.evaluate(() => fetch("/sentinel/d", { cache: "no-store" }).then((r) => r.status));
        assert.equal(status, 200, engine + ": the drain's round trip reached the page server");
        await page.waitForTimeout(1500);
        const logAtDrain = remoteLog.slice();
        console.log(engine + " " + browser.version() + ": remote logger at the drain (" + logAtDrain.length + " lines): " + JSON.stringify(show(logAtDrain)));
        const read = (shapes: DocShape[], body: string): Promise<Read[]> => page.evaluate(([ss, b]: [DocShape[], string]) => ss.map((s) => {
          const e = document.querySelector(b + " ." + s.cls + " rect");
          return { where: b + " ." + s.cls + " rect [" + s.attr + "]", value: e ? e.getAttribute(s.attr) : "(no element)" };
        }), [shapes, body] as [DocShape[], string]);
        const docsRead = [...await read(replyDocs, REPLY_BODY), ...await read(userDocs, USER_BODY)];
        const keptRead = [...await read(kept, REPLY_BODY), ...await read(userKept, USER_BODY)];
        // the raster mask's pixels: a screenshot of each masked rect, decoded in the page; its left half painted, its right not
        const pixels: Array<{ where: string; left: number[]; right: number[] }> = [];
        for (const [body, cls] of [[REPLY_BODY, "dk-raster"], [USER_BODY, "uk-raster"]]) {
          const box = await page.locator(body + " ." + cls + " rect").boundingBox();
          assert.ok(box, engine + ": the masked rect " + body + " ." + cls + " has a box to read");
          const png: Buffer = await page.screenshot({ clip: box });
          const px = await page.evaluate(async (b64: string) => {
            const img = new Image(); img.src = "data:image/png;base64," + b64; await img.decode();
            const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
            const x = c.getContext("2d") as CanvasRenderingContext2D; x.drawImage(img, 0, 0);
            const at = (fx: number) => Array.from(x.getImageData(Math.floor(fx * img.width), Math.floor(img.height / 2), 1, 1).data);
            return { left: at(0.25), right: at(0.75) };
          }, png.toString("base64"));
          pixels.push({ where: body + " ." + cls, ...px });
        }
        const witnessLogged = logAtDrain.filter((l) => witnessFiles.includes(l.path.split("?")[0]));
        const controlLogged = [...new Set(logAtDrain.filter((l) => l.path.startsWith("/dc-")).map((l) => l.path.split("?")[0]))].sort();

        await t.test(engine + ": the page's own mask references were kept and requested from the page server", () => {
          // guards the positive control: both messages rendered and a paint fetch reaches a server log in this engine
          // (at least once: Firefox 153 asked for the same mask document twice in one run, under the page's no-store)
          for (const f of ["/own-dmask.svg", "/own-dumask.svg"]) assert.ok(forFile(pageLog, f).length >= 1, f + " was requested: " + JSON.stringify(show(pageLog)));
        });
        await t.test(engine + ": the unsanitized control's documents made the loads this engine makes (" + CONTROL_LOADS[engine] + ")", () => {
          // guards the harness: in an engine that loads a data: paint document the logger sees it, so an empty witness is the pass's work
          assert.deepEqual(controlLogged, CONTROL_LOADS[engine] === "all" ? controlFiles : [], engine + ": the control's @imports at the logger");
        });
        await t.test(engine + ": no request reached the remote logger from a data: document in either message", () => {
          // guards the fix: Firefox fetched each of these @imports as the bubble rendered, before the data: rule
          assert.deepEqual(show(witnessLogged), [], engine + ": a data: document in a message made a request to another host");
        });
        await t.test(engine + ": every data: document reference is removed from its element, which stays", () => {
          // guards the DOM half, in every engine: the attribute goes before the bubble's innerHTML is set
          assert.deepEqual(docsRead.filter((r) => r.value !== null), [], engine + ": each data: document reference is removed (an element that went reads \"(no element)\")");
        });
        await t.test(engine + ": the controls stay as written: url(#g), the page's own fill and mask, the raster mask, the raster-labelled svg body", () => {
          // guards the STAYS side of the data: rule: an over-strip here is a raster mask users lose
          const want = [...kept, ...userKept];
          assert.deepEqual(keptRead.filter((k, i) => k.value !== want[i].value), [], engine + ": each control keeps its value as written");
        });
        if (MASK_DRAWS.includes(engine)) {
          await t.test(engine + ": the kept raster data: mask draws: the masked rect's left half is painted red and its right half is not", () => {
            // guards the reason a raster stays: a data: mask users see, drawn after the real pipeline, in each message
            // a contrast between the halves, not pure red, the way the kernel-page scene reads a card drawn below full opacity
            const redness = (p: number[]) => p[0] - Math.max(p[1], p[2]);
            assert.deepEqual(pixels.filter((p) => redness(p.left) - redness(p.right) < 30 || redness(p.right) >= 15), [], engine + ": the masked rects' pixels (left, right): " + JSON.stringify(pixels));
          });
        }
        await t.test(engine + ": no page errors", () => {
          // guards the render: a thrown render would leave the bubbles empty and every other check vacuous
          assert.deepEqual(errors, [], engine + ": no page errors");
        });
      } finally { await browser.close(); }
    }
  } finally {
    console.log("data: documents: engines that ran: " + ran.join(", ") + " (ROMP_BROWSER_ENGINES=" + JSON.stringify(process.env.ROMP_BROWSER_ENGINES || "") + "; Firefox and WebKit run only when it names them)");
    await Promise.all([shut(remote.server), shut(pageSrv.server)]);
  }
  assert.deepEqual(ran.map((r) => r.split(" ")[0]), engines, "the engines that ran are the ones asked for: " + ran.join(", "));
});

// ── the browser census ───────────────────────────────────────────────────────────────────────────────

/** One of DOMPurify's attribute arrays in the installed dist, read by its literal head, loud by name when it is missing
 *  (the reader paint-refs-census.test.ts uses, here for the candidate names of the attribute derivation). */
function dompurifyList(dist: string, name: string): string[] {
  const head = "const " + name + " = freeze([";
  const at = dist.indexOf(head);
  assert.ok(at >= 0, "dompurify dist/purify.es.mjs: no `" + head + "` (the attribute derivation reads its candidate names there)");
  const end = dist.indexOf("]);", at);
  const names = [...dist.slice(at + head.length, end).matchAll(/'([^'\\]*)'/g)].map((m) => m[1]);
  assert.ok(names.length > 0, "dompurify's " + name + " list read empty");
  return names;
}

// the value templates of the two derivations (paint-refs.ts's header): %U is the URL
const CSS_FORMS = ['url("%U")', "url(%U)", 'url("%U#p")', 'image-set(url("%U") 1x)', 'url("%U"), auto', 'url("%U") red', 'url("%U") no-repeat',
  'url("%U") 30 round', 'square inside url("%U")', 'url("%U") 0px', 'url("%U") blur(2px)', '"a" url("%U")', 'url("%U") 10 / 10px',
  'red url("%U") no-repeat center / cover', 'url("%U") center / contain no-repeat', '-webkit-cross-fade(url("%U"), url("%U"), 50%)', 'image-set("%U" 1x)',
  'url("%U") format("woff2")'];
/** Names the attribute derivation adds to its candidates by hand, 25 of them: the url()-taking properties that URL_PROPERTIES's
 *  derivation found in WebKit 26.5 (2026-09-23), less the eight paint names, which DOMPurify's svg list already carries. Chromium
 *  151 knows 22 of them (not -webkit-backdrop-filter, mask-border or mask-border-source) and Firefox 153 knows 19, so the three
 *  lift Chromium's candidates from 985 to 988, and a Chromium that gains one is read for it even when its style object does not
 *  list it. */
const EXTRA_NAMES = ["-webkit-mask-image", "-webkit-mask", "-webkit-clip-path", "-webkit-filter", "-webkit-shape-outside", "-webkit-backdrop-filter",
  "-webkit-border-image", "-webkit-mask-box-image", "-webkit-mask-box-image-source", "mask-border", "mask-border-source", "cursor", "marker", "content", "offset",
  "offset-path", "shape-outside", "list-style", "list-style-image", "border-image", "border-image-source", "background", "background-image", "backdrop-filter", "mask-image"];
const ATTR_FORMS = ["url(%U)", 'url("%U")', "url(%U) red", "url(%U), auto", "url(%U) 30 round", "square inside url(%U)", "url(%U) 0px", '"a" url(%U)',
  "image-set(url(%U) 1x)", "url(%U) blur(2px)", "url(%U) no-repeat"];

test("browser census: S_css and S_attr re-derived in the installed Chromium are subsets of paint-refs.ts's URL_PROPERTIES and URL_ATTRS", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const dist = fs.readFileSync(path.join(EXT, "node_modules", "dompurify", "dist", "purify.es.mjs"), "utf8");
    const lists = [...dompurifyList(dist, "html"), ...dompurifyList(dist, "svg"), ...dompurifyList(dist, "xml"), ...dompurifyList(dist, "mathMl"), ...EXTRA_NAMES];
    const page = await browser.newPage();
    await page.setContent('<!doctype html><html><body><div id="probe"></div><div id="host"></div></body></html>');
    const t0 = Date.now();
    const derived: { known: number; candidates: number; sCss: string[]; sAttr: string[] } = await page.evaluate(([cssForms, attrForms, dpLists]: [string[], string[], string[]]) => {
      // every property the engine knows: the style object's names down its prototype chain (camelCase turned to CSS's
      // spelling, a vendor prefix lowered first) that CSS.supports accepts with `inherit`, plus the computed style's list
      const toKebab = (n: string): string => {
        if (n.includes("-")) return n;
        if (n === "cssFloat") return "float";
        const rest = (r: string) => r.charAt(0).toLowerCase() + r.slice(1).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
        let m: RegExpExecArray | null;
        if ((m = /^(webkit|Webkit|WebKit)([A-Z].*)$/.exec(n))) return "-webkit-" + rest(m[2]);
        if ((m = /^(moz|Moz)([A-Z].*)$/.exec(n))) return "-moz-" + rest(m[2]);
        if ((m = /^(ms|Ms)([A-Z].*)$/.exec(n))) return "-ms-" + rest(m[2]);
        if ((m = /^(epub|Epub)([A-Z].*)$/.exec(n))) return "-epub-" + rest(m[2]);
        if ((m = /^(apple|Apple)([A-Z].*)$/.exec(n))) return "-apple-" + rest(m[2]);
        return n.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
      };
      const known = new Set<string>();
      let o: object | null = document.documentElement.style;
      while (o && o !== Object.prototype) {
        for (const k of Object.getOwnPropertyNames(o)) { if (/^\d+$/.test(k)) continue; const kb = toKebab(k); if (CSS.supports(kb, "inherit")) known.add(kb); }
        o = Object.getPrototypeOf(o);
      }
      const cs0 = getComputedStyle(document.documentElement);
      for (let i = 0; i < cs0.length; i++) known.add(cs0[i]);
      // S_css: a property is in it when CSS.supports accepts any template with a URL in it
      const REMOTE_CSS = "https://example.invalid/x";
      const sCss = [...known].filter((n) => cssForms.some((f) => CSS.supports(n, f.split("%U").join(REMOTE_CSS)))).sort();
      // S_attr: a name is in it when, set as an attribute on an svg rect or path through innerHTML (or on a rect by
      // setAttribute), its computed style carries the url(), for a remote URL or a same-document one. A candidate that is
      // no property the engine knows has no computed value to read, so it can never be in the set; it is kept in the
      // candidate count and skipped in the loop.
      const candidates = new Set<string>([...known, ...dpLists]);
      const REMOTE_ATTR = "http://example.invalid/x.svg#p";
      const host = document.getElementById("host") as HTMLElement;
      const esc = (v: string) => v.replace(/"/g, "&quot;");
      const sAttr: string[] = [];
      for (const name of [...candidates].sort()) {
        if (!CSS.supports(name, "inherit")) continue;
        let hit = false;
        for (const f of attrForms) {
          for (const u of [REMOTE_ATTR, "#frag"]) {
            const v = f.split("%U").join(u);
            host.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect id="r" width="10" height="10" ' + name + '="' + esc(v) + '"></rect><path id="pth" d="M0 0 L10 10 L20 0" ' + name + '="' + esc(v) + '"></path></svg>';
            const r = document.getElementById("r") as Element, p = document.getElementById("pth") as Element;
            if (getComputedStyle(r).getPropertyValue(name).includes("url(") || getComputedStyle(p).getPropertyValue(name).includes("url(")) { hit = true; break; }
            host.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect id="r" width="10" height="10"></rect></svg>';
            const r3 = document.getElementById("r") as Element; r3.setAttribute(name, v);
            if (getComputedStyle(r3).getPropertyValue(name).includes("url(")) { hit = true; break; }
          }
          if (hit) break;
        }
        if (hit) sAttr.push(name);
      }
      host.innerHTML = "";
      return { known: known.size, candidates: candidates.size, sCss, sAttr };
    }, [CSS_FORMS, ATTR_FORMS, lists] as [string[], string[], string[]]);
    console.log("Chromium " + browser.version() + ": " + derived.known + " known properties, " + derived.candidates + " attribute candidates, derived in " + (Date.now() - t0) + " ms; S_css (" + derived.sCss.length + "): " + derived.sCss.join(" ") + "; S_attr (" + derived.sAttr.length + "): " + derived.sAttr.join(" "));
    // the floor: the derivations found what every engine reads, so the subset checks below are not over an empty set
    for (const n of ["fill", "stroke", "mask", "clip-path", "marker-end"]) assert.ok(derived.sAttr.includes(n), "the attribute derivation found " + n + " (a derivation that finds nothing would pass the subset check vacuously): " + JSON.stringify(derived.sAttr));
    for (const n of ["background-image", "mask-image", "list-style-image", "border-image-source", "content"]) assert.ok(derived.sCss.includes(n), "the property derivation found " + n + " (a derivation that finds nothing would pass the subset check vacuously): " + JSON.stringify(derived.sCss));
    assert.deepEqual(derived.sAttr.filter((n) => !URL_ATTRS.includes(n)), [], "an attribute the installed Chromium reads a url() from that paint-refs.ts URL_ATTRS does not carry: add it there (and re-run the three-engine derivation its header names)");
    assert.deepEqual(derived.sCss.filter((n) => !URL_PROPERTIES.includes(n)), [], "a CSS property the installed Chromium takes a url() in that paint-refs.ts URL_PROPERTIES does not carry: add it there (and re-run the three-engine derivation its header names)");
  });
});
