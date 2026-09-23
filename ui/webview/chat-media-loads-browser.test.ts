// The chat-media road's executed witness (the fourth review round of the price-feed-off change, tests-1; the fifth round adds the
// paint references, D and E, and the file preview and notice surfaces, A): on the web dashboard a rendered message's media loads
// from the host its URL names the moment the message renders, with no click, with whatever cookies that browser sends to that host
// and no Referer to any other origin; under the editor webviews' CSP the request does not go. An inline svg's paint references load the same way,
// on three surfaces (the chat's rendered markdown, the chat's file preview, a notice card's body); which paint attributes load is the
// engine's, read here from SECURITY.md's paint clause, not a literal of the seven in the test, and so is what each paint request
// carries in its Origin header: the clause's Origin half is parsed for the parts of the page's origin it names and for the part it
// leaves out when that part is the scheme's default (the port), and every paint request that arrives, in each scene of each engine,
// must carry exactly those parts, each the page's. The fixture's pages are served at a port that is not the scheme's default, so the
// port is carried; the default-port scene serves the chat page at http://dash.test (routed to the page server, http's default port 80)
// and holds each paint request's Origin to scheme and host, no port, in Chromium, Firefox and WebKit (Chromium's scene runs in a
// browser of its own with its local network access checks off: the fixture's media host is on the loopback, and Chromium refuses a
// request to the loopback from a page whose address it does not place there). Every other default port (https's 443 among them) rests
// on the Origin serialization rule, RFC 6454 section 6.2, which leaves out a port that is the scheme's default. Two real servers on the
// loopback: the
// page server at http://localhost:P answers /chat, /feed and /file under the headers Handler._send puts on every page the kernel
// serves, read from kernel/kernel.py's source and pinned by value below (a source pin, stated as such: the wire-level tie, the
// kernel's own Handler answering GET /chat with the same four headers, is tests/test_security_price_feed.py TheChatMediaRoadIsWitnessed);
// the media listener at http://127.0.0.1:Q records every request line and its headers and answers a 1x1 PNG, a 16-byte clip or a small
// svg. localhost and 127.0.0.1 are two sites (the registrable domain differs), so a cookie set on 127.0.0.1 with SameSite=Lax is
// withheld and one with SameSite=None; Secure is sent in Chromium and Firefox: the cookies that browser sends to a host on another
// site (WebKit sends that Secure cookie to this plain-http host on no cross-site load; see its test below). The message
// goes through md()'s pipeline as render.ts runs it (marked, sanitizeMd, linkifyPrRefs, mdImgPostPass); the file preview loads the real
// render.ts bundle and hovers (and focuses) a link the kernel allows to preview; the notice loads the real feed.ts bundle and posts a
// notice card. The exact code-line pin on md()'s body ties the probe to the source, so a statement added to it reds the tie and the
// probe must follow it before the scenes mean anything. Scene 2 serves the same pages under the editor's CSP (extension.ts buildHtml
// and buildFeedHtml, the webview's cspSource standing in as 'self') and reads the page's securitypolicyviolation events, the page's own
// signal, so the evidence of absence is event-based. The referrer control scene serves the chat page without Referrer-Policy: the same
// image sends the origin as Referer. Firefox and WebKit, when installed, run the three surfaces the clause's "On all three" names
// through the scene code the Chromium test runs (md() on the chat, the file preview by hover and by focus, the notice card), load at
// least the attribute the clause names for them (mask) and never the no-engine one, request no paint path twice, as the Chromium test
// holds, and hold each paint request to the Origin half. In every engine the one-request count and the per-request checks below
// (cookie, mode, Origin) are read once the scene's expected paint loads have arrived (in the Firefox and WebKit md() scene, at its
// 8 s bound, below), so they catch a request that arrives by then and not one that arrives later (a second request for a path, or a
// request for another paint attribute).
// Every paint request, in each scene of each engine, must be a CORS request by its Sec-Fetch-Mode (cors), the request kind the Origin
// half implies. The mode says nothing of cookies: a CORS request made with credentials can carry them. What keeps a paint request
// cookieless is its fetch's credentials mode, which the specifications set for paint fetches (same-origin, which sends no cookie on
// a cross-origin request, as each of these is) and which the wire does not show, so the no-cookie half is read against a load that
// carries the cookie. It is executed in Chromium and Firefox: each context holds two cookies for the media host, a load made without
// CORS carries the SameSite=None one (Chromium's media in scene 1; in Firefox the control image md() renders beside the paint
// references, mode no-cors), and each paint request must carry none, an assertion that reds on a credentialed request (in Firefox, a
// mask swapped for an svg image with crossorigin="use-credentials", a CORS request that carries the cookie; in Chromium, the same
// image beside a mask that names a local fragment, since the swap alone leaves no mask attribute and reds earlier, at the check that
// the sanitizer kept every paint attribute). WebKit cannot show it on this fixture: WebKit sends the fixture's cross-site cookie
// (SameSite=None, Secure) to the plain-http host on no cross-site load, so its control carries none and its no-cookie assertion
// cannot fail here; the WebKit half rests on the credentials mode the specifications set for paint fetches, which no run here
// observes. Every wait is on a request event or the page's own event, never a timer alone, and the bounds are the failure, with one
// timed read: the Firefox and WebKit md() scene resolves at its 8 s bound, since the attributes those engines do not load never
// arrive, and reads what arrived by then.
// Skips LOUDLY without a playwright browser, as the other browser legs do; in CI it skips because the vscode-extension job runs npm
// test before it installs Playwright's Chromium, and installs no Firefox or WebKit. Synthetic values only: loopback URLs, invented
// cookie names, a placeholder uuid, a TESTHOST path and a placeholder .test address routed inside the browser.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as http from "node:http";
import * as path from "node:path";
import type { AddressInfo } from "node:net";
import { createRequire } from "node:module";
import { chatBody, ATTACH_TITLE_WEB, FEED_BODY } from "../../vscode-extension/src/page-skeleton";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const ROOT = path.resolve(EXT, "..");
const noKatex = (s: string) => s.replace(/^@import [^\n]*\n/m, "");
const STYLES = noKatex(fs.readFileSync(path.join(UI, "styles.css"), "utf8"));
const FEED_STYLES = noKatex(fs.readFileSync(path.join(UI, "feed.css"), "utf8")) + "\n" + noKatex(fs.readFileSync(path.join(UI, "gear.css"), "utf8"));
const KERNEL = fs.readFileSync(path.join(ROOT, "kernel", "kernel.py"), "utf8");
const EXTENSION = fs.readFileSync(path.join(EXT, "src", "extension.ts"), "utf8");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
const FIGURE_GATE = fs.readFileSync(path.join(UI, "figure-gate.ts"), "utf8");
const SECURITY = fs.readFileSync(path.join(ROOT, "SECURITY.md"), "utf8");
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
const SVG_DOC = '<svg xmlns="http://www.w3.org/2000/svg"><defs><pattern id="p" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="2" height="2" fill="red"/></pattern>'
  + '<filter id="f"><feGaussianBlur stdDeviation="1"/></filter><clipPath id="c"><rect width="4" height="4"/></clipPath><mask id="m"><rect width="4" height="4" fill="white"/></mask>'
  + '<marker id="k" markerWidth="4" markerHeight="4" refX="2" refY="2"><circle cx="2" cy="2" r="2"/></marker></defs></svg>';
const TOKEN = "witness-token-0001";
const SID = "aaaaaaaa-1111-2222-3333-444444444444";

// ── the headers, from the code that sends them ──────────────────────────────────────────────────────

/** Every page the kernel serves carries these: Handler._send's unconditional `send_header` lines with two literal
 *  arguments (Content-Type and Content-Length are per response; the cookie, CORS and Cache-Control lines are conditional
 *  and sit after the caller's headers loop). A source pin: the wire-level tie is the Python case named in the header. */
export function dashboardHeaders(): Record<string, string> {
  const m = /\n    def _send\(self, code, body, ctype, cache=None, headers=None\):\n([\s\S]*?)\n        for k, v in \(headers or \{\}\)\.items\(\):/.exec(KERNEL);
  assert.ok(m, "kernel/kernel.py Handler._send up to its caller-supplied headers loop");
  const out: Record<string, string> = {};
  for (const h of m![1].matchAll(/^        self\.send_header\("([^"]+)", "([^"]+)"\)/gm)) out[h[1]] = h[2];
  return out;
}
/** The four the dashboard's pages carry at this head, by value: a header added, dropped or reworded reds the witness
 *  (the road's cells say no Referer and no img-src or media-src; a Cross-Origin-* header would change what a media host
 *  learns and is asserted absent by this equality). */
export const DASHBOARD_HEADERS: Record<string, string> = {
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "SAMEORIGIN",
  "Content-Security-Policy": "frame-ancestors 'self'",
  "Referrer-Policy": "same-origin",
};

/** An editor webview's CSP: buildHtml's or buildFeedHtml's `csp` array in extension.ts, each part with the webview's
 *  resource origin (`${webview.cspSource}`) standing in as 'self', the kernel base as the given origin and the nonce filled. */
export function editorCsp(fnName: string, nonce: string, kernelBase: string): { csp: string; parts: string[] } {
  const fn = new RegExp("\\nfunction " + fnName + "\\(webview: vscode\\.Webview\\): string \\{\\n([\\s\\S]*?)\\n\\}\\n").exec(EXTENSION);
  assert.ok(fn, "vscode-extension/src/extension.ts " + fnName);
  const arr = /const csp = \[\n([\s\S]*?)\n  \]\.join\("; "\);/.exec(fn![1]);
  assert.ok(arr, fnName + "'s csp array");
  const parts = Array.from(arr![1].matchAll(/^\s*[`"]([^`"]+)[`"],?\s*$/gm)).map((x) => x[1]);
  const csp = parts.map((p) => p.replace("${webview.cspSource}", "'self'").replace("${kernelBase}", kernelBase).replace("${n}", nonce)).join("; ");
  return { csp, parts };
}

// ── the paint attributes, from figure-gate.ts, and the list each engine loads, from SECURITY.md ─────

/** The eight paint attributes the sanitizer keeps, ui/webview/figure-gate.ts PAINT_ATTRS: the population the scenes render. */
function paintAttrs(): string[] {
  const m = /export const PAINT_ATTRS = \[([^\]]*)\] as const;/.exec(FIGURE_GATE);
  assert.ok(m, "ui/webview/figure-gate.ts PAINT_ATTRS");
  return Array.from(m![1].matchAll(/"([^"]+)"/g)).map((x) => x[1]);
}
const PAINT = paintAttrs();
// SECURITY.md's paint clause, parsed for the list each engine loads: the set the scenes observe is asserted equal to what the
// section names, read from the text (never a second literal), so a wrong clause reds here and an earlier clause naming only
// fill, mask and filter matches nothing.
const PAINT_LIST_RE = /in Chromium a ((?:`[a-z-]+`, )*`[a-z-]+` or `[a-z-]+`) whose `url\(\)` names another host loads from that host/;
const PAINT_MIN_RE = /in Firefox and WebKit at least a `([a-z-]+)` does/;
const PAINT_NONE_RE = /and a `([a-z-]+)` does in no engine/;
// the Origin half: what each paint request carries in its Origin header, the parts of the page's origin the clause names captured,
// then the part it leaves out when that part is the scheme's default
const PAINT_ORIGIN_RE = /each such request carries [^;]*?the page's origin \(the dashboard's ((?:[a-z]+, )*[a-z]+ and [a-z]+)(?:, the ([a-z]+) omitted when it is the scheme's default)?\) in its Origin header/;
/** The parts of an origin the Origin half can name, each read from a parsed origin (an absent part reads as "": a URL's port reads
 *  as "" when it is the scheme's default, so a page at its scheme's default port has no port part). */
const ORIGIN_PART: Record<string, (u: URL) => string> = { scheme: (u) => u.protocol.replace(/:$/, ""), host: (u) => u.hostname, port: (u) => u.port };
type OriginHalf = { parts: string[]; omitted: string | null };
function paintFromSecurity(): { chromium: string[]; min: string; none: string; origin: OriginHalf } {
  const flat = SECURITY.replace(/\s+/g, " ");
  const cm = PAINT_LIST_RE.exec(flat);
  assert.ok(cm, "SECURITY.md's Network access section names the Chromium paint list (\"in Chromium a `fill`, ... whose `url()` names "
    + "another host loads from that host\"); an earlier clause that names only fill, mask and filter does not match");
  const chromium = Array.from(cm![1].matchAll(/`([a-z-]+)`/g)).map((x) => x[1]);
  const mn = PAINT_MIN_RE.exec(flat), no = PAINT_NONE_RE.exec(flat);
  assert.ok(mn && no, "SECURITY.md names the Firefox/WebKit attribute and the no-engine attribute");
  const og = PAINT_ORIGIN_RE.exec(flat);
  assert.ok(og, "SECURITY.md's paint clause says what each paint request carries in its Origin header (\"each such request carries ... the "
    + "page's origin (the dashboard's scheme, host and port, the port omitted when it is the scheme's default) in its Origin header\"); a clause "
    + "without that half does not match");
  const parts = og![1].split(/, | and /), omitted = og![2] ?? null;
  for (const part of parts) assert.ok(part in ORIGIN_PART, "SECURITY.md's Origin half names a part of the page's origin the witness reads: " + part);
  assert.ok(omitted === null || (omitted === "port" && parts.includes(omitted)), "the part SECURITY.md's Origin half leaves out at the scheme's default is the port it names: " + omitted);
  return { chromium, min: mn![1], none: no![1], origin: { parts, omitted } };
}
/** The clause's Origin half against one paint request: the header is present, is an origin's serialization, and carries exactly the
 *  parts of the page's origin the clause names, less the part it leaves out when the page's is the scheme's default, each equal to
 *  the page's (both read from the header and the page's own origin). */
function assertOrigin(hit: Hit, pageOrigin: string, half: OriginHalf, what: string): void {
  assert.ok(typeof hit.origin === "string" && hit.origin !== "null", what + " carries an Origin header that names an origin: " + JSON.stringify(hit));
  const got = new URL(hit.origin!), want = new URL(pageOrigin);
  assert.equal(got.origin, hit.origin, what + ": the Origin header is an origin and nothing else: " + hit.origin);
  const atDefault = half.omitted !== null && ORIGIN_PART[half.omitted](want) === "";
  const parts = half.parts.filter((k) => !(atDefault && k === half.omitted));
  const carried = Object.keys(ORIGIN_PART).filter((k) => ORIGIN_PART[k](got) !== "");
  assert.deepEqual(carried.slice().sort(), parts.slice().sort(), what + ": the Origin header carries the parts of the page's origin SECURITY.md "
    + "names (" + half.parts.join(", ") + (half.omitted ? "; the " + half.omitted + " omitted at the scheme's default" : "") + "), for this page ("
    + pageOrigin + ") " + parts.join(", ") + ", no more, no fewer: " + hit.origin);
  for (const k of parts) assert.equal(ORIGIN_PART[k](got), ORIGIN_PART[k](want), what + ": the Origin header's " + k + " is the page's (" + pageOrigin + "): " + hit.origin);
}

// ── the pipelines, as render.ts runs them ────────────────────────────────────────────────────────────

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
function bundle(entry: string): string {
  const r = requireCjs("esbuild").buildSync({ ...BUILD, entryPoints: [path.join(UI, entry)] });
  return r.outputFiles[0].text;
}
// md() and userMd() as render.ts:md and render.ts:userMd run them (the code-line pin below holds the steps to the source)
function probeBundle(): string {
  const contents = [
    'import { marked } from "marked";',
    'import { sanitizeMd } from "./md-sanitize";',
    'import { applyMdConfig } from "./md-config";',
    'import { linkifyPrRefs } from "./pr-links";',
    'import { mdImgPostPass } from "./preview";',
    'import { userMdHtml } from "./chat-md";',
    "applyMdConfig();",
    "(window as any).__md = (src: string) => { const clean = sanitizeMd(marked.parse(src) as string); linkifyPrRefs(clean, null); mdImgPostPass(clean); return clean.innerHTML; };",
    "(window as any).__userMd = (src: string) => { const clean = sanitizeMd(userMdHtml(src)); linkifyPrRefs(clean, null); mdImgPostPass(clean); return clean.innerHTML; };",
  ].join("\n");
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, sourcefile: "md-media-probe.ts", loader: "ts" } });
  return r.outputFiles[0].text;
}
function tsFunction(src: string, head: string): string {
  const i = src.indexOf("\n" + head); assert.ok(i >= 0, head);
  const j = src.indexOf("\n}\n", i); return src.slice(i, j + 3);
}
/** The statements of a function's body: each line with its trailing `//` comment cut, comment-only and blank lines dropped. */
function codeLines(fn: string): string[] {
  return fn.split("\n").slice(2, -2).map((l) => l.replace(/\s+\/\/.*$/, "").trim()).filter((l) => l && !l.startsWith("//"));
}
const MD_BODY = ["try {", "const dirty = marked.parse(src) as string;", "const clean = sanitizeMd(dirty);", "linkifyPrRefs(clean, repo);", "mdImgPostPass(clean);", "return clean.innerHTML;",
  '} catch { const d = document.createElement("div"); d.textContent = src; return d.innerHTML; }'];
const USER_MD_BODY = ["try {", "const clean = sanitizeMd(userMdHtml(src));", "linkifyPrRefs(clean, repo);", "mdImgPostPass(clean);", "return clean.innerHTML;",
  '} catch { const d = document.createElement("div"); d.textContent = src; return d.innerHTML; }'];

// ── the content: one inline svg per paint attribute, and the media the strip removes ────────────────

const PAINT_EL: Record<string, (u: string) => string> = {
  "fill": (u) => `<rect width="8" height="8" fill="url(${u}#p)"/>`,
  "stroke": (u) => `<rect x="1" y="1" width="8" height="8" fill="none" stroke="url(${u}#p)"/>`,
  "filter": (u) => `<rect width="8" height="8" filter="url(${u}#f)"/>`,
  "clip-path": (u) => `<rect width="8" height="8" clip-path="url(${u}#c)"/>`,
  "mask": (u) => `<rect width="8" height="8" mask="url(${u}#m)"/>`,
  "marker-start": (u) => `<path d="M1 1 L5 5 L9 1" fill="none" stroke="black" marker-start="url(${u}#k)"/>`,
  "marker-mid": (u) => `<path d="M1 1 L5 5 L9 1" fill="none" stroke="black" marker-mid="url(${u}#k)"/>`,
  "marker-end": (u) => `<path d="M1 1 L5 5 L9 1" fill="none" stroke="black" marker-end="url(${u}#k)"/>`,
};
const paintPath = (tag: string, a: string) => `/${tag}-paint-${a}.svg`;
function paintMd(M: string, tag: string): string {
  return PAINT.map((a) => `<svg width="12" height="12">${PAINT_EL[a](M + paintPath(tag, a))}</svg>`).join("\n\n");
}
// the nine media shapes the road's trigger cell names; the strip removes them on the file preview and the notice
const MEDIA = ["md", "set", "source", "fallback", "clip-v", "poster", "clip-a", "svgimage", "svgxlink"];
function mediaMd(M: string, tag: string): string {
  return [
    `A picture ![pic](${M}/${tag}-media-md.png) in the text.`,
    `<img srcset="${M}/${tag}-media-set.png 1x" alt="set">`,
    `<picture><source srcset="${M}/${tag}-media-source.png"><img src="${M}/${tag}-media-fallback.png" alt="pic"></picture>`,
    `<video src="${M}/${tag}-media-clip-v.mp4" width="60" height="40"></video>`,
    `<video poster="${M}/${tag}-media-poster.png" width="60" height="40"></video>`,
    `<audio src="${M}/${tag}-media-clip-a.mp3" controls></audio>`,
    `<svg width="20" height="20"><image href="${M}/${tag}-media-svgimage.png" width="20" height="20"/></svg>`,
    `<svg width="20" height="20"><image xlink:href="${M}/${tag}-media-svgxlink.png" width="20" height="20"/></svg>`,
  ].join("\n\n");
}

// ── the page ────────────────────────────────────────────────────────────────────────────────────────

const NONCE = "witness-nonce-0001";
function chatHtml(csp: string | null): string {
  const meta = csp ? `<meta http-equiv="Content-Security-Policy" content="${csp}">` : "";
  return `<!DOCTYPE html><html lang=en><head><meta charset=utf-8>${meta}<style>${STYLES}</style></head><body>
${chatBody(ATTACH_TITLE_WEB)}
<script nonce="${NONCE}">window.__opens=[];window.open=function(u,t,f){window.__opens.push([u,t,f]);return null;};
window.acquireVsCodeApi=function(){return{postMessage:function(){}}};
window.__csp=[];document.addEventListener("securitypolicyviolation",function(e){window.__csp.push({blocked:e.blockedURI,directive:e.effectiveDirective});});</script>
<script nonce="${NONCE}" src="/dist/render.js"></script>
<script nonce="${NONCE}" src="/dist/probe.js"></script></body></html>`;
}
function feedHtml(csp: string | null): string {
  const meta = csp ? `<meta http-equiv="Content-Security-Policy" content="${csp}">` : "";
  return `<!DOCTYPE html><html lang=en><head><meta charset=utf-8>${meta}<style>${FEED_STYLES}</style></head><body>
${FEED_BODY}
<script nonce="${NONCE}">window.__rompGearOnSettingsPage=true;window.__posted=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posted.push(m);}}};
window.__csp=[];document.addEventListener("securitypolicyviolation",function(e){window.__csp.push({blocked:e.blockedURI,directive:e.effectiveDirective});});</script>
<script nonce="${NONCE}" src="/dist/feed.js"></script></body></html>`;
}

type Hit = { line: string; host?: string; referer: string | null; origin: string | null; cookie: string | null; site?: string; dest?: string; mode?: string; range?: string };

async function listen(handler: http.RequestListener, host: string): Promise<{ server: http.Server; origin: string }> {
  const server = http.createServer(handler);
  await new Promise<void>((ok, bad) => { server.once("error", bad); server.listen(0, host, () => ok()); });
  const a = server.address() as AddressInfo;
  return { server, origin: `http://${host}:${a.port}` };
}

// ── what every engine's test shares: the media host, the page routes, the cookies and the scenes ───────

type Waiter = { paths: Set<string>; done: () => void };
/** A wait on the media host's request events: it resolves once every path has arrived; at the bound it rejects, naming what never
 *  arrived and what did, or with atBound "resolve" it resolves (the Firefox and WebKit md() scene, whose unloaded attributes never
 *  arrive by design, so the bound ends that wait). */
function waitOn(hits: Hit[], waiters: Waiter[]) {
  return (paths: string[], ms: number, what = "", atBound: "reject" | "resolve" = "reject") => new Promise<void>((ok, bad) => {
    const pending = new Set(paths.filter((p) => !hits.some((h) => h.line.split(" ")[1] === p)));
    if (!pending.size) return ok();
    const w = { paths: pending, done: () => { clearTimeout(timer); ok(); } };
    const timer = setTimeout(() => {
      const i = waiters.indexOf(w); if (i >= 0) waiters.splice(i, 1);
      if (atBound === "resolve") { ok(); return; }
      bad(new Error((what ? what + ": " : "") + "no request for " + Array.from(pending).join(", ") + " within " + ms + " ms; arrived: " + hits.map((h) => h.line).join(" | ")));
    }, ms);
    waiters.push(w);
  });
}
/** The media listener at http://127.0.0.1:Q every test of this file uses: each request line recorded with its headers, the waits woken
 *  on it, and a 1x1 PNG, a 16-byte clip or the small svg answered. */
async function mediaHost() {
  const hits: Hit[] = [], waiters: Waiter[] = [];
  const host = await listen((req, res) => {
    const h = req.headers, u = req.url || "";
    hits.push({ line: `${req.method} ${u} HTTP/${req.httpVersion}`, host: h.host, referer: (h.referer as string) ?? null, origin: (h.origin as string) ?? null, cookie: (h.cookie as string) ?? null,
      site: h["sec-fetch-site"] as string, dest: h["sec-fetch-dest"] as string, mode: h["sec-fetch-mode"] as string, range: h.range as string });
    for (const w of waiters.slice()) { w.paths.delete(u); if (!w.paths.size) { waiters.splice(waiters.indexOf(w), 1); w.done(); } }
    if (u.endsWith(".png")) { res.writeHead(200, { "Content-Type": "image/png", "Content-Length": String(PNG.length) }); res.end(PNG); return; }
    if (u.endsWith(".mp4")) { res.writeHead(200, { "Content-Type": "video/mp4", "Content-Length": "16" }); res.end(Buffer.alloc(16)); return; }
    if (u.endsWith(".mp3")) { res.writeHead(200, { "Content-Type": "audio/mpeg", "Content-Length": "16" }); res.end(Buffer.alloc(16)); return; }
    if (u.endsWith(".svg")) { res.writeHead(200, { "Content-Type": "image/svg+xml", "Content-Length": String(Buffer.byteLength(SVG_DOC)) }); res.end(SVG_DOC); return; }
    res.writeHead(404); res.end();
  }, "127.0.0.1");
  return { ...host, hits, arrived: waitOn(hits, waiters) };
}
type Bundles = { render: string; probe: string; feed: string };
const bundles = (): Bundles => ({ render: bundle("render.ts"), probe: probeBundle(), feed: bundle("feed.ts") });
/** The routes every test's page server answers alike, under the dashboard's headers: /chat and /feed, their three bundles, and the file
 *  preview's slice of the markdown file (its text in slice.text). True when the path was one of them. */
function pageRoute(u: URL, res: http.ServerResponse, headers: Record<string, string>, js: Bundles, slice: { text: string }): boolean {
  const html = { ...headers, "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" }, script = { ...headers, "Content-Type": "application/javascript" };
  const p = u.pathname;
  if (p === "/chat") { res.writeHead(200, html); res.end(chatHtml(null)); return true; }
  if (p === "/feed") { res.writeHead(200, html); res.end(feedHtml(null)); return true; }
  if (p === "/dist/render.js") { res.writeHead(200, script); res.end(js.render); return true; }
  if (p === "/dist/probe.js") { res.writeHead(200, script); res.end(js.probe); return true; }
  if (p === "/dist/feed.js") { res.writeHead(200, script); res.end(js.feed); return true; }
  if (p === "/file" && u.searchParams.get("slice") === "1") {
    res.writeHead(200, { ...headers, "Content-Type": "application/json" });
    res.end(JSON.stringify({ kind: "markdown", title: "notes.md", allowed: true, text: slice.text, found: true, truncated: false, hit: true, size: slice.text.length }));
    return true;
  }
  return false;
}
// the two cookies every test's context holds for the media host: of the two, the Lax one is withheld on a cross-site load, and the
// SameSite=None; Secure one is the cookie Chromium and Firefox send cross-site to this host (WebKit sends it to the plain-http media
// host on no cross-site load)
const COOKIES = [
  { name: "lax_only", value: "1", domain: "127.0.0.1", path: "/", sameSite: "Lax" },
  { name: "cross_site", value: "1", domain: "127.0.0.1", path: "/", sameSite: "None", secure: true },
];
// what the Firefox and WebKit test's control image (a load made without CORS) carries, measured on it: the SameSite=None cookie in
// Firefox; none in WebKit, which sends that Secure cookie to the plain-http media host on no cross-site load. Only
// that test reads this; Chromium's cross_site=1 is asserted on scene 1's media population, as a literal there.
const CROSS_SITE_COOKIE: Record<string, string | null> = { firefox: "cross_site=1", webkit: null };

/** The file preview scene every engine runs: render.ts's own preview, opened by a pointer dwell (hover) or a keyboard focus on a link
 *  in a session frame to a markdown file the kernel allows to preview, the file's text (slice) an inline svg per paint attribute and
 *  the nine media shapes the strip removes. Resolves once the card shows its svg; the requests are the caller's to read. */
async function filePreviewScene(pg: any, P: string, M: string, tag: string, mode: string, slice: { text: string }): Promise<void> {
  await pg.goto(P + "/chat");
  await pg.waitForFunction(() => typeof (window as any).__md === "function", null, { timeout: 15000 });
  slice.text = "# Notes\n\nThe notes for the api.\n\n" + paintMd(M, tag) + "\n\n" + mediaMd(M, tag) + "\n";
  await pg.evaluate(([sid]: [string]) => {
    window.postMessage({ type: "session", id: sid, name: "web", cwd: "/tmp/TESTHOST/notes-api", status: { state: "idle", sinceEpoch: null },
      events: [{ kind: "assistant", md: "The notes are in docs/notes.md for the api.", uuid: "11111111-2222-4333-8444-555555555555",
                 pathLinks: { "docs/notes.md": "docs/notes.md" }, pathPreview: { "docs/notes.md": "markdown" } }] }, "*");
  }, [SID] as [string]);
  const sel = '#content .file-uri-link[data-preview="markdown"]';
  await pg.waitForSelector(sel, { timeout: 15000 });
  if (mode === "focus") await pg.locator(sel).first().focus(); else await pg.hover(sel);
  await pg.waitForFunction(() => { const p = document.getElementById("file-preview-pop"); return !!p && getComputedStyle(p).display !== "none" && !!p.querySelector(".fp-body.md svg"); }, null, { timeout: 10000 });
}
/** The notice card scene every engine runs: feed.ts's own notice card over a feed frame, its body the same content. Resolves once the
 *  card shows its svg, with the card's key. */
async function noticeCardScene(pg: any, P: string, M: string, tag: string): Promise<string> {
  await pg.goto(P + "/feed");
  await pg.waitForFunction(() => (window as any).__posted.some((m: any) => m && m.type === "ready"), null, { timeout: 15000 });
  const now = Math.floor(Date.now() / 1000); const color = { bg: "#3366cc", fg: "#ffffff" };
  const itemId = `notice:${SID}:figure:2`;
  const card = { itemId, sid: SID, name: "web", color, text: "A new version of the accuracy figure is ready", t: now - 60, trgb: [96, 128, 160], live: false,
    turnId: itemId, column: "completed", summary: null, blockSummary: null, tree: [], blocked: null,
    notice: { producer: "figure", key: "figure", rev: 2, body: "Regenerated after the sweep on **tests** finished.\n\n" + paintMd(M, tag) + "\n\n" + mediaMd(M, tag),
              attachment: null, actions: [], expiresAt: null, dismissOnAction: false } };
  const frame = { type: "feed", now, nowAt: now * 1000, buildId: 1, asks: [card], working: [], awaiting: [], stateUnknown: [], order: [SID], selfHost: "TESTHOST",
    sessions: [{ sid: SID, name: "web", color }], userTodos: {}, bgServices: {} };
  await pg.evaluate((f: any) => { window.dispatchEvent(new MessageEvent("message", { data: f })); }, frame);
  const key = "a:" + itemId;
  await pg.waitForFunction((k: string) => { const c = Array.from(document.querySelectorAll("[data-key]")).find((x) => (x as HTMLElement).dataset.key === k) as HTMLElement | undefined; return !!c && !!c.querySelector(".fask-nbody svg"); }, key, { timeout: 10000 });
  return key;
}
// the default-port scene's page origin: http at its default port, a name routed inside the browser to the page server
const DASH = "http://dash.test";
/** The default-port scene every engine runs, in a context of its own: the chat page at DASH, every request to DASH answered by the page
 *  server's own route and headers, md() rendering the paint references (tag); resolves once the given paths have arrived at the media
 *  host, the bound the failure. The requests are the caller's to read. */
async function defaultPortScene(browser: any, P: string, M: string, arrived: ReturnType<typeof waitOn>, tag: string, paths: string[], what: string): Promise<void> {
  assert.equal(new URL(DASH).port, "", what + ": the page's origin (" + DASH + ") is at its scheme's default port");
  const context = await browser.newContext({ viewport: { width: 900, height: 700 } });
  await context.route(DASH + "/**", async (route: any) => {
    const u = new URL(route.request().url());
    await route.fulfill({ response: await route.fetch({ url: P + u.pathname + u.search }) });
  });
  const pg = await context.newPage();
  await pg.goto(DASH + "/chat");
  assert.equal(await pg.evaluate(() => location.origin), DASH, what + ": the chat page runs at " + DASH);
  await pg.waitForFunction(() => typeof (window as any).__md === "function", null, { timeout: 15000 });
  await pg.evaluate((s: string) => { const c = document.getElementById("content") as HTMLElement; const b = document.createElement("div"); b.className = "assistant md"; b.innerHTML = (window as any).__md(s); c.appendChild(b); },
    paintMd(M, tag));
  await arrived(paths, 10000, what);
  await context.unrouteAll({ behavior: "ignoreErrors" });   // a page fetch still routed when the context closes is dropped, not a rejection
  await context.close();
}
/** What the strip leaves on those two surfaces: no request for any of the nine media, and no media element or poster in the card's body
 *  (the file preview's card when card is null, else the notice card with that key). */
async function assertStripped(pg: any, hits: Hit[], tag: string, what: string, card: string | null): Promise<void> {
  for (const m of MEDIA) assert.equal(hits.filter((h) => h.line.split(" ")[1].startsWith(`/${tag}-media-${m}.`)).length, 0, what + ": the media element " + m + " is stripped before the nodes join the page");
  const held = await pg.evaluate((k: string | null) => {
    const b = (k === null ? document.querySelector("#file-preview-pop .fp-body")
      : (Array.from(document.querySelectorAll("[data-key]")).find((x) => (x as HTMLElement).dataset.key === k) as HTMLElement).querySelector(".fask-nbody")) as HTMLElement;
    return /<(img|video|audio|source|image)\b/i.test(b.innerHTML) || /poster=/.test(b.innerHTML);
  }, card);
  assert.ok(!held, what + ": the card's body holds no media element (the strip removed them)");
}

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }
// why the leg skips in CI: the vscode-extension job's order of steps, not an absent browser
const CI_SKIP = "in CI the vscode-extension job runs npm test before it installs Playwright's Chromium, and installs no Firefox or WebKit";

test("the chat-media road: a rendered message's media and inline svg paint references load on the web dashboard with no click, no Referer and the cross-site cookies only, each paint request with the page's origin in its Origin header (its port omitted for a page at http's default port); the file preview and a notice card load the paint references and strip the media; the editor's CSP blocks every one", { timeout: 120000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (" + CI_SKIP + ")"); return; }
  let chromium: any;
  try { chromium = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (" + CI_SKIP + "): " + String((e as Error).message).split("\n")[0]); return; }

  const errors: string[] = [];
  let media: Awaited<ReturnType<typeof mediaHost>> | null = null, page: { server: http.Server; origin: string } | null = null;
  try {
    // the pipeline the probe composes is md()'s, statement for statement (render.ts): a step added to the body, a gate for
    // instance, reds this tie, and the probe must follow it before the scenes mean anything
    const mdFn = tsFunction(RENDER, "function md(src: string, repo: string | null = prRepoFor()): string {");
    const userFn = tsFunction(RENDER, "function userMd(src: string, repo: string | null = prRepoFor()): string {");
    assert.deepEqual(codeLines(mdFn), MD_BODY, "md()'s body is the pipeline the probe composes");
    assert.deepEqual(codeLines(userFn), USER_MD_BODY, "userMd()'s body is the pipeline the probe composes");

    const headers = dashboardHeaders();
    assert.deepEqual(headers, DASHBOARD_HEADERS, "the kernel's pages carry these four headers and no other unconditional one: " + JSON.stringify(headers));
    assert.ok(!Object.keys(headers).some((k) => /^cross-origin-/i.test(k)), "no Cross-Origin-* header on the dashboard's pages");

    const paint = paintFromSecurity();   // the list each engine loads, from SECURITY.md's clause (never a literal here)
    assert.ok(paint.chromium.length >= 5 && !paint.chromium.includes(paint.none), "SECURITY.md names a Chromium paint list without the no-engine attribute: " + JSON.stringify(paint));

    media = await mediaHost();
    const { hits, arrived } = media;
    const paintOf = (tag: string) => PAINT.filter((a) => hits.some((h) => h.line.split(" ")[1] === paintPath(tag, a)));
    const hitFor = (p: string) => hits.filter((h) => h.line.split(" ")[1] === p);

    const js = bundles();
    let editorChat = { csp: "", parts: [] as string[] }, editorFeed = { csp: "", parts: [] as string[] };
    const slice = { text: "" };
    page = await listen((req, res) => {
      const withHeaders = (extra: Record<string, string>, drop?: string) => { const all = { ...headers, ...extra }; if (drop) delete all[drop]; return all; };
      const u = new URL(req.url || "/", "http://x");
      if (pageRoute(u, res, headers, js, slice)) return;
      const p = u.pathname;
      if (p === "/chat-editor") { res.writeHead(200, withHeaders({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" })); res.end(chatHtml(editorChat.csp)); return; }
      if (p === "/chat-noref") { res.writeHead(200, withHeaders({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" }, "Referrer-Policy")); res.end(chatHtml(null)); return; }
      if (p === "/feed-editor") { res.writeHead(200, withHeaders({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" })); res.end(feedHtml(editorFeed.csp)); return; }
      res.writeHead(404, withHeaders({ "Content-Type": "text/plain" })); res.end("");
    }, "localhost");
    editorChat = editorCsp("buildHtml", NONCE, page.origin);
    editorFeed = editorCsp("buildFeedHtml", NONCE, page.origin);
    assert.ok(editorChat.parts.includes("default-src 'none'"), "the editor's chat CSP starts from default-src 'none': " + JSON.stringify(editorChat.parts));
    assert.ok(editorChat.parts.some((p) => p.startsWith("img-src ${webview.cspSource}")), "img-src is the webview's own resource origin (and data:): " + JSON.stringify(editorChat.parts));
    assert.ok(!editorChat.parts.some((p) => p.startsWith("media-src")), "no media-src: video and audio fall to default-src 'none'");

    const M = media.origin, P = page.origin;
    const population = (tag: string) => [
      { name: "a markdown image in a session's reply", kind: "assistant", md: `A reply with a picture ![pic](${M}/${tag}-assistant.png) in it.`, paths: [`/${tag}-assistant.png`] },
      { name: "a markdown image in the user's own message", kind: "user", md: `my note\n![mine](${M}/${tag}-user.png)`, paths: [`/${tag}-user.png`] },
      { name: "a markdown image in a postal body", kind: "postal", md: `**peer**\n\n![from a peer](${M}/${tag}-postal.png)`, paths: [`/${tag}-postal.png`] },
      { name: "a video", kind: "assistant", md: `<video src="${M}/${tag}-clip.mp4" width="120" height="80"></video>`, paths: [`/${tag}-clip.mp4`] },
      { name: "an audio clip", kind: "assistant", md: `<audio src="${M}/${tag}-clip.mp3"></audio>`, paths: [`/${tag}-clip.mp3`] },
      { name: "an image with srcset", kind: "assistant", md: `<img srcset="${M}/${tag}-set.png 1x" alt="set">`, paths: [`/${tag}-set.png`] },
      { name: "a picture with a source", kind: "assistant", md: `<picture><source srcset="${M}/${tag}-source.png"><img src="${M}/${tag}-fallback.png" alt="pic"></picture>`, paths: [`/${tag}-source.png`] },
      { name: "a video's poster", kind: "assistant", md: `<video poster="${M}/${tag}-poster.png" width="120" height="80"></video>`, paths: [`/${tag}-poster.png`] },
      { name: "an inline svg's image", kind: "assistant", md: `<svg width="20" height="20"><image href="${M}/${tag}-svgimage.png" width="20" height="20"/></svg>`, paths: [`/${tag}-svgimage.png`] },
    ];
    const show = (pg: any, kind: string, md: string) => pg.evaluate(([k, s]: [string, string]) => {
      const content = document.getElementById("content") as HTMLElement;
      const turn = document.createElement("div"); const body = document.createElement("div");
      if (k === "assistant") { turn.className = "turn turn-assistant fx-turn"; body.className = "assistant md"; body.innerHTML = (window as any).__md(s); }
      else if (k === "user") { turn.className = "turn turn-user fx-turn"; body.className = "bubble"; body.innerHTML = (window as any).__userMd(s); }
      else { turn.className = "turn fx-turn"; body.className = "notice-md md"; body.innerHTML = (window as any).__md(s); }
      turn.appendChild(body); content.appendChild(turn);
      return body.innerHTML;
    }, [kind, md] as [string, string]);

    const context = await chromium.newContext({ viewport: { width: 900, height: 700 } });
    await context.addCookies(COOKIES);
    const pg = await context.newPage();
    pg.on("pageerror", (e: Error) => { errors.push(e.message); });

    // the per-request asserts a paint reference carries: exactly one, dest image, cross-site, no cookie (scene 1's media, loads made
    // without CORS, carry the SameSite=None cookie), a CORS request by its Sec-Fetch-Mode (the request kind the Origin half implies),
    // the Origin half; mask's Referer the origin. Called once the scene's Chromium paint loads (the list read from SECURITY.md) have
    // arrived, so the one-request count and the no-engine attribute's absence are read at that moment: a request made later, a second
    // one for a paint path or one for the no-engine attribute, would not be caught.
    const assertPaint = (tag: string, scene: string, chromiumList: string[]) => {
      for (const a of chromiumList) {
        const these = hitFor(paintPath(tag, a));
        assert.equal(these.length, 1, scene + ": one request for the " + a + " paint reference: " + JSON.stringify(these));
        assert.equal(these[0].dest, "image", scene + ": " + a + " is sec-fetch-dest image");
        assert.equal(these[0].site, "cross-site", scene + ": " + a + " is cross-site");
        assert.equal(these[0].cookie, null, scene + ": " + a + " carries no cookie (scene 1's media, loads made without CORS, carry the SameSite=None one): " + JSON.stringify(these[0]));
        assert.equal(these[0].mode, "cors", scene + ": " + a + " is a CORS request (Sec-Fetch-Mode cors), the request kind the Origin half implies: " + JSON.stringify(these[0]));
        assertOrigin(these[0], P, paint.origin, scene + ": " + a);
      }
      const maskHit = hitFor(paintPath(tag, "mask"))[0];
      if (maskHit) assert.equal(maskHit.referer, P + "/", scene + ": the mask reference carries the page origin as Referer");
      assert.equal(hitFor(paintPath(tag, paint.none)).length, 0, scene + ": the no-engine attribute (" + paint.none + ") makes no request");
    };

    // scene 1: the dashboard's headers, media and paint through md()
    await pg.goto(P + "/chat");
    const dash = population("dash");
    for (const p of dash) { const html = await show(pg, p.kind, p.md); assert.ok(/<(img|video|audio|source|image)\b/.test(html), p.name + ": the sanitizer kept the media element: " + html); }
    const paintHtml = await show(pg, "assistant", paintMd(M, "dash") + `\n\ncontrol ![ctl](${M}/dash-ctl.png)`);
    assert.ok(PAINT.every((a) => new RegExp("\\s" + a + '="url\\(').test(paintHtml)), "the sanitizer kept every paint attribute: " + paintHtml);
    // the one wait of scene 1: the media population's loads, the Chromium paint loads and the control image, all by request event
    await arrived(dash.flatMap((p) => p.paths).concat(paint.chromium.map((a) => paintPath("dash", a))).concat(["/dash-ctl.png"]), 10000);
    console.log("scene 1 (dashboard headers " + JSON.stringify(headers) + ") request lines:");
    for (const h of hits.filter((x) => x.line.includes(" /dash-"))) console.log("  " + JSON.stringify(h));
    for (const p of dash) for (const q of p.paths) {
      const these = hitFor(q);
      assert.equal(these.length, 1, p.name + ": one request for " + q + " arrived at the media host on render: " + JSON.stringify(these));
      assert.equal(these[0].referer, null, p.name + ": no Referer (Referrer-Policy same-origin)");
      assert.equal(these[0].site, "cross-site", p.name + ": the browser classes the request cross-site");
      assert.equal(these[0].cookie, "cross_site=1", p.name + ": the SameSite=None cookie rides, the Lax one is withheld");
    }
    assert.deepEqual(paintOf("dash").sort(), paint.chromium.slice().sort(), "the paint attributes whose request arrived are the Chromium list SECURITY.md names, no more, no fewer");
    assertPaint("dash", "scene 1 (md)", paint.chromium);
    assert.equal(await pg.evaluate(() => (window as any).__opens.length), 0, "no click, no window.open: the loads are the render's own");

    // scene 2: the editor chat webview's CSP over the same page: no request reaches the media host; img-src violations for the paint set
    await pg.goto(P + "/chat-editor");
    const edPaint = await show(pg, "assistant", paintMd(M, "ed") + `\n\ncontrol ![ctl](${M}/ed-ctl.png)`);
    assert.ok(PAINT.every((a) => new RegExp("\\s" + a + '="url\\(').test(edPaint)), "under the editor CSP the sanitizer kept the paint attributes");
    await pg.waitForFunction(([n, m]: [number, string]) => (window as any).__csp.filter((v: any) => String(v.blocked).startsWith(m)).length >= n, [paint.chromium.length, M] as [number, string], { timeout: 10000 });
    const edViolations = await pg.evaluate((m: string) => (window as any).__csp.filter((v: any) => String(v.blocked).startsWith(m)), M);
    console.log("scene 2 (editor chat CSP " + editorChat.csp + ") violations:");
    for (const v of edViolations) console.log("  " + JSON.stringify(v));
    const edHits = hits.filter((h) => h.line.includes(" /ed-"));
    console.log("scene 2 request lines at the media host: " + (edHits.length ? edHits.map((h) => h.line).join(" | ") : "(none)"));
    assert.deepEqual(edHits, [], "under the editor's CSP no request for the ed- content reached the host");
    for (const a of paint.chromium) assert.ok(edViolations.some((v: any) => v.blocked === M + paintPath("ed", a) && v.directive === "img-src"), "the editor CSP blocked the " + a + " paint reference (img-src): " + JSON.stringify(edViolations));
    assert.ok(!edViolations.some((v: any) => v.blocked === M + paintPath("ed", paint.none)), "the no-engine attribute (" + paint.none + ") made no attempt, so it drew no violation");

    // the file preview scene: render.ts's own hover (and keyboard focus) preview over a session frame, the media stripped
    for (const mode of ["hover", "focus"]) {
      const tag = "fp" + mode[0];
      await filePreviewScene(pg, P, M, tag, mode, slice);
      await arrived(paint.chromium.map((a) => paintPath(tag, a)), 10000);
      console.log("file preview scene (" + mode + ") request lines:");
      for (const h of hits.filter((x) => x.line.includes(" /" + tag + "-"))) console.log("  " + JSON.stringify(h));
      assert.deepEqual(paintOf(tag).sort(), paint.chromium.slice().sort(), mode + ": the paint references arrive, the Chromium list SECURITY.md names");
      assertPaint(tag, "file preview (" + mode + ")", paint.chromium);
      await assertStripped(pg, hits, tag, "file preview (" + mode + ")", null);
    }

    // the notice card scene: feed.ts's own notice card over a feed frame, the media stripped
    {
      const tag = "nt";
      const key = await noticeCardScene(pg, P, M, tag);
      await arrived(paint.chromium.map((a) => paintPath(tag, a)), 10000);
      console.log("notice card scene request lines:");
      for (const h of hits.filter((x) => x.line.includes(" /" + tag + "-"))) console.log("  " + JSON.stringify(h));
      assert.deepEqual(paintOf(tag).sort(), paint.chromium.slice().sort(), "notice: the paint references arrive, the Chromium list SECURITY.md names");
      assertPaint(tag, "notice card", paint.chromium);
      await assertStripped(pg, hits, tag, "notice card", key);
    }

    // the referrer control: the same page without Referrer-Policy sends the origin as Referer
    await pg.goto(P + "/chat-noref");
    await show(pg, "assistant", `![pic](${M}/noref-assistant.png)`);
    await arrived(["/noref-assistant.png"], 10000);
    const ctl = hitFor("/noref-assistant.png")[0];
    console.log("referrer control (no Referrer-Policy) request line: " + JSON.stringify(ctl));
    assert.equal(ctl.referer, P + "/", "the control: with the header absent the browser's default sends the origin, so the header is what removes it");
    assert.deepEqual(errors, [], "no page errors");
    await context.close();

    // the default-port scene: the chat page at http's default port, in a Chromium of its own with its local network access checks off
    // (the media host is on the loopback); each paint request's Origin is held to the Origin half for that page, the port omitted
    const dashBrowser = await pw.chromium.launch({ args: ["--disable-features=LocalNetworkAccessChecks"] });
    try {
      await defaultPortScene(dashBrowser, P, M, arrived, "dp", paint.chromium.map((a) => paintPath("dp", a)), "default-port scene");
      console.log("default-port scene request lines:");
      for (const h of hits.filter((x) => x.line.includes(" /dp-"))) console.log("  " + JSON.stringify(h));
      for (const a of paint.chromium) {
        const these = hitFor(paintPath("dp", a));
        assert.equal(these.length, 1, "default-port scene: one request for the " + a + " paint reference: " + JSON.stringify(these));
        assert.equal(these[0].mode, "cors", "default-port scene: " + a + " is a CORS request (Sec-Fetch-Mode cors): " + JSON.stringify(these[0]));
        assertOrigin(these[0], DASH, paint.origin, "default-port scene: " + a);
      }
      assert.equal(hitFor(paintPath("dp", paint.none)).length, 0, "default-port scene: the no-engine attribute (" + paint.none + ") makes no request");
    } finally {
      await dashBrowser.close();
    }
  } finally {
    await chromium.close();
    if (media) media.server.close();
    if (page) page.server.close();
  }
});

// Firefox and WebKit: the three surfaces the clause's "On all three" names, through the scene code the Chromium test runs (md() on the
// chat, the file preview by hover and by focus, the notice card), each engine's own list (at least mask, never filter), no paint path
// requested twice (the count read once the scene's expected paint loads have arrived, so a second request that arrives later is not
// caught) and the Origin half on every paint request that arrives, then the default-port scene, skipping loudly per engine that cannot
// launch (CI installs neither). The leg is the witness for those engines (the round ruled the leg carries them, no notes path). Each
// paint request must be a CORS request (Sec-Fetch-Mode cors), the request kind the Origin half implies; the mode says nothing of
// cookies. The context holds the Chromium test's two cookies, and md() renders a control image beside the paint references, a load
// made without CORS: in Firefox it carries the SameSite=None cookie (CROSS_SITE_COOKIE), so each paint request's no cookie is executed
// against a load that carries it and reds on a credentialed request; in WebKit, which sends the fixture's Secure cookie to the
// plain-http media host on no cross-site load, the control carries none and the no-cookie assertion cannot fail, so the WebKit half
// rests on the credentials mode the specifications set for paint fetches (same-origin, which sends no cookie on a cross-origin request,
// as each of these is), which no run here observes.
for (const engineName of ["firefox", "webkit"]) {
  test(`the chat-media road on ${engineName}: an inline svg's paint references load on the chat's rendered markdown, the file preview and a notice card (at least the attribute SECURITY.md names for Firefox and WebKit; the no-engine attribute never), each a CORS request with no cookie and the page's origin in its Origin header (its port omitted for a page at http's default port), beside a control image made without CORS; the file preview and the notice card strip the media`, { timeout: 120000 }, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (" + CI_SKIP + ")"); return; }
    let browser: any;
    try { browser = await pw[engineName].launch(); }
    catch (e) { t.skip("no " + engineName + " on this box; the leg needs one (" + CI_SKIP + "): " + String((e as Error).message).split("\n")[0]); return; }
    let media: Awaited<ReturnType<typeof mediaHost>> | null = null, page: { server: http.Server; origin: string } | null = null;
    try {
      const headers = dashboardHeaders();
      const paint = paintFromSecurity();
      media = await mediaHost();
      const { hits, arrived } = media;
      const js = bundles(), slice = { text: "" };
      page = await listen((req, res) => { if (pageRoute(new URL(req.url || "/", "http://x"), res, headers, js, slice)) return; res.writeHead(404); res.end(); }, "localhost");
      const M = media.origin, P = page.origin, sent = CROSS_SITE_COOKIE[engineName];
      const hitFor = (p: string) => hits.filter((h) => h.line.split(" ")[1] === p);
      const lineOf = (h: Hit) => h.line + " dest=" + h.dest + " mode=" + h.mode + " cookie=" + h.cookie + " origin=" + h.origin + " referer=" + h.referer;
      // no paint path twice: each paint path that arrived has exactly one request, as Chromium's assertPaint holds (measured: Firefox and
      // WebKit, like Chromium, request no paint path twice by the time the count is read, in every scene). The count is read when the
      // scene's wait for its expected paint loads ends (in md(), at its 8 s bound; in the other scenes, once the mask has arrived), so a
      // second request for the path that arrives by then, one made without CORS for instance, reds here, and one that arrives later is
      // not caught. Then each request of it with no cookie, read against the control image (in WebKit, where the control carries none,
      // this cannot fail: that half rests on the credentials mode the specifications set, which no run here observes), a CORS request by
      // its Sec-Fetch-Mode (the request kind the Origin half implies), then the clause's Origin half
      const assertEach = (tag: string, what: string, got: string[]) => {
        for (const a of got) {
          const these = hitFor(paintPath(tag, a));
          assert.equal(these.length, 1, what + ": one request for the " + a + " paint reference: " + these.map(lineOf).join(" | "));
          for (const h of these) {
            assert.equal(h.cookie, null, what + ": the " + a + " paint reference carries no cookie"
              + (sent ? ", where the control image made without CORS carries " + sent + ": " + lineOf(h)
                : "; in " + engineName + " the fixture's Secure cookie is sent to this plain-http host on no cross-site load, so this cannot fail here and the half rests on the credentials mode the specifications set for paint fetches, which no run here observes"));
            assert.equal(h.mode, "cors", what + ": the " + a + " paint reference is a CORS request (Sec-Fetch-Mode cors), the request kind the Origin half implies: " + lineOf(h));
            assertOrigin(h, P, paint.origin, what + ": " + a);
          }
        }
      };
      const context = await browser.newContext({ viewport: { width: 900, height: 700 } });
      await context.addCookies(COOKIES);
      const pg = await context.newPage();

      // md() on the chat: the paint references and the control image, a load made without CORS on the same host
      await pg.goto(P + "/chat");
      await pg.waitForFunction(() => typeof (window as any).__md === "function", null, { timeout: 15000 });
      await pg.evaluate((s: string) => { const c = document.getElementById("content") as HTMLElement; const b = document.createElement("div"); b.className = "assistant md"; b.innerHTML = (window as any).__md(s); c.appendChild(b); },
        paintMd(M, "e") + `\n\ncontrol ![ctl](${M}/e-ctl.png)`);
      await arrived(PAINT.map((a) => paintPath("e", a)).concat(["/e-ctl.png"]), 8000, engineName, "resolve");
      const got = PAINT.filter((a) => hitFor(paintPath("e", a)).length > 0);
      console.log(engineName + " md() request lines: " + hits.map(lineOf).join(" | "));
      const ctl = hitFor("/e-ctl.png");
      assert.equal(ctl.length, 1, engineName + ": one request for the control image: " + JSON.stringify(ctl));
      assert.equal(ctl[0].mode, "no-cors", engineName + ": the control image is a load made without CORS: " + lineOf(ctl[0]));
      assert.equal(ctl[0].cookie, sent, sent
        ? engineName + ": the control image, a load made without CORS, carries the SameSite=None cookie and not the Lax one, so each paint request's no cookie below can fail"
        : "in " + engineName + " the fixture's cross-site cookie (SameSite=None, Secure) is sent to the plain-http media host on no cross-site load: the control image carries none, so each paint request's no cookie below cannot fail here and rests on the credentials mode the specifications set for paint fetches (same-origin, which sends no cookie on a cross-origin request, as each of these is), which no run here observes");
      assert.ok(got.includes(paint.min), engineName + " loads at least the attribute SECURITY.md names for Firefox and WebKit (" + paint.min + "): arrived " + JSON.stringify(got));
      assert.ok(!got.includes(paint.none), engineName + ": the no-engine attribute (" + paint.none + ") makes no request");
      assertEach("e", engineName, got);

      // the file preview, by hover and by focus, and the notice card: the Chromium test's scenes; each waits by event for the engine's
      // attribute, its bound the failure, and the strip is read as in Chromium. The no-engine attribute's absence and the one-request
      // count, with the per-request checks, are read once that expected load (mask) has arrived, the same pattern as Chromium's
      // assertPaint: a request made later (a second one for the mask, one for the no-engine attribute, or one for any other paint
      // attribute) would not be caught.
      const surface = async (tag: string, what: string, card: string | null) => {
        await arrived([paintPath(tag, paint.min)], 10000, what);
        const these = PAINT.filter((a) => hitFor(paintPath(tag, a)).length > 0);
        console.log(what + " request lines: " + hits.filter((h) => h.line.includes(" /" + tag + "-")).map(lineOf).join(" | "));
        assert.ok(these.includes(paint.min) && !these.includes(paint.none), what + ": the engine's attribute (" + paint.min + ") arrives and the no-engine one ("
          + paint.none + ") does not: " + JSON.stringify(these));
        assertEach(tag, what, these);
        await assertStripped(pg, hits, tag, what, card);
      };
      for (const mode of ["hover", "focus"]) {
        const tag = "efp" + mode[0];
        await filePreviewScene(pg, P, M, tag, mode, slice);
        await surface(tag, engineName + " file preview (" + mode + ")", null);
      }
      const key = await noticeCardScene(pg, P, M, "ent");
      await surface("ent", engineName + " notice card", key);
      await context.close();

      // the default-port scene, in a context of its own: the chat page at http's default port; the engine's attribute arrives, the
      // no-engine one does not and no paint path is requested twice (each read once the expected load has arrived, so a request that
      // arrives later is not caught), and each request for a paint path is a CORS request whose Origin is held to the Origin half for
      // that page, the port omitted
      const dpWhat = engineName + " default-port scene";
      await defaultPortScene(browser, P, M, arrived, "edp", [paintPath("edp", paint.min)], dpWhat);
      const dp = PAINT.filter((a) => hitFor(paintPath("edp", a)).length > 0);
      console.log(dpWhat + " request lines: " + hits.filter((h) => h.line.includes(" /edp-")).map(lineOf).join(" | "));
      assert.ok(dp.includes(paint.min) && !dp.includes(paint.none), dpWhat + ": the engine's attribute (" + paint.min + ") arrives and the no-engine one ("
        + paint.none + ") does not: " + JSON.stringify(dp));
      for (const a of dp) {
        const these = hitFor(paintPath("edp", a));
        assert.equal(these.length, 1, dpWhat + ": one request for the " + a + " paint reference: " + these.map(lineOf).join(" | "));
        for (const h of these) {
          assert.equal(h.mode, "cors", dpWhat + ": the " + a + " paint reference is a CORS request (Sec-Fetch-Mode cors): " + lineOf(h));
          assertOrigin(h, DASH, paint.origin, dpWhat + ": " + a);
        }
      }
    } finally {
      await browser.close();
      if (media) media.server.close();
      if (page) page.server.close();
    }
  });
}
