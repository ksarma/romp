// The chat-media road's executed witness (the fourth review round of the price-feed-off change, tests-1; the fifth round adds the
// paint references, D and E, and the file preview and notice surfaces, A): on the web dashboard a rendered message's media loads
// from the host its URL names the moment the message renders, with no click, with whatever cookies that browser sends to that host
// and no Referer to any other origin; under the editor webviews' CSP the request does not go. An inline svg's paint references load the same way,
// on three surfaces (the chat's rendered markdown, the chat's file preview, a notice card's body); which paint attributes load is the
// engine's, read here from SECURITY.md's paint clause, not a literal of the seven in the test. Two real servers on the loopback: the
// page server at http://localhost:P answers /chat, /feed and /file under the headers Handler._send puts on every page the kernel
// serves, read from kernel/kernel.py's source and pinned by value below (a source pin, stated as such: the wire-level tie, the
// kernel's own Handler answering GET /chat with the same four headers, is tests/test_security_price_feed.py TheChatMediaRoadIsWitnessed);
// the media listener at http://127.0.0.1:Q records every request line and its headers and answers a 1x1 PNG, a 16-byte clip or a small
// svg. localhost and 127.0.0.1 are two sites (the registrable domain differs), so a cookie set on 127.0.0.1 with SameSite=Lax is
// withheld and one with SameSite=None; Secure is sent: the cookies that browser sends to a host on another site. The message
// goes through md()'s pipeline as render.ts runs it (marked, sanitizeMd, linkifyPrRefs, mdImgPostPass); the file preview loads the real
// render.ts bundle and hovers (and focuses) a link the kernel allows to preview; the notice loads the real feed.ts bundle and posts a
// notice card. The exact code-line pin on md()'s body ties the probe to the source, so a statement added to it reds the tie and the
// probe must follow it before the scenes mean anything. Scene 2 serves the same pages under the editor's CSP (extension.ts buildHtml
// and buildFeedHtml, the webview's cspSource standing in as 'self') and reads the page's securitypolicyviolation events, the page's own
// signal, so the evidence of absence is event-based. The referrer control scene serves the chat page without Referrer-Policy: the same
// image sends the origin as Referer. Firefox and WebKit run the paint scene when installed and load at least the attribute the clause
// names for them (mask). Every wait is on a request event or the page's own event, never a timer alone; the bounds are the failure.
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only: loopback URLs,
// invented cookie names, a placeholder session id and a TESTHOST path.
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
function paintFromSecurity(): { chromium: string[]; min: string; none: string } {
  const flat = SECURITY.replace(/\s+/g, " ");
  const cm = PAINT_LIST_RE.exec(flat);
  assert.ok(cm, "SECURITY.md's Network access section names the Chromium paint list (\"in Chromium a `fill`, ... whose `url()` names "
    + "another host loads from that host\"); an earlier clause that names only fill, mask and filter does not match");
  const chromium = Array.from(cm![1].matchAll(/`([a-z-]+)`/g)).map((x) => x[1]);
  const mn = PAINT_MIN_RE.exec(flat), no = PAINT_NONE_RE.exec(flat);
  assert.ok(mn && no, "SECURITY.md names the Firefox/WebKit attribute and the no-engine attribute");
  return { chromium, min: mn![1], none: no![1] };
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

type Hit = { line: string; host?: string; referer: string | null; cookie: string | null; site?: string; dest?: string; range?: string };

async function listen(handler: http.RequestListener, host: string): Promise<{ server: http.Server; origin: string }> {
  const server = http.createServer(handler);
  await new Promise<void>((ok, bad) => { server.once("error", bad); server.listen(0, host, () => ok()); });
  const a = server.address() as AddressInfo;
  return { server, origin: `http://${host}:${a.port}` };
}

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

test("the chat-media road: a rendered message's media and inline svg paint references load on the web dashboard with no click, no Referer and the cross-site cookies only; the file preview and a notice card load the paint references and strip the media; the editor's CSP blocks every one", { timeout: 120000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let chromium: any;
  try { chromium = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }

  const errors: string[] = [];
  let media: { server: http.Server; origin: string } | null = null, page: { server: http.Server; origin: string } | null = null;
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

    const hits: Hit[] = [];
    const waiters: { paths: Set<string>; done: () => void }[] = [];
    media = await listen((req, res) => {
      const h = req.headers, u = req.url || "";
      hits.push({ line: `${req.method} ${u} HTTP/${req.httpVersion}`, host: h.host, referer: (h.referer as string) ?? null, cookie: (h.cookie as string) ?? null,
        site: h["sec-fetch-site"] as string, dest: h["sec-fetch-dest"] as string, range: h.range as string });
      for (const w of waiters.slice()) { w.paths.delete(u); if (!w.paths.size) { waiters.splice(waiters.indexOf(w), 1); w.done(); } }
      if (u.endsWith(".png")) { res.writeHead(200, { "Content-Type": "image/png", "Content-Length": String(PNG.length) }); res.end(PNG); return; }
      if (u.endsWith(".mp4")) { res.writeHead(200, { "Content-Type": "video/mp4", "Content-Length": "16" }); res.end(Buffer.alloc(16)); return; }
      if (u.endsWith(".mp3")) { res.writeHead(200, { "Content-Type": "audio/mpeg", "Content-Length": "16" }); res.end(Buffer.alloc(16)); return; }
      if (u.endsWith(".svg")) { res.writeHead(200, { "Content-Type": "image/svg+xml", "Content-Length": String(Buffer.byteLength(SVG_DOC)) }); res.end(SVG_DOC); return; }
      res.writeHead(404); res.end();
    }, "127.0.0.1");
    const arrived = (paths: string[], ms: number) => new Promise<void>((ok, bad) => {
      const pending = new Set(paths.filter((p) => !hits.some((h) => h.line.split(" ")[1] === p)));
      if (!pending.size) return ok();
      const w = { paths: pending, done: () => { clearTimeout(timer); ok(); } };
      const timer = setTimeout(() => { waiters.splice(waiters.indexOf(w), 1); bad(new Error("no request for " + Array.from(pending).join(", ") + " within " + ms + " ms; arrived: " + hits.map((h) => h.line).join(" | "))); }, ms);
      waiters.push(w);
    });
    const paintOf = (tag: string) => PAINT.filter((a) => hits.some((h) => h.line.split(" ")[1] === paintPath(tag, a)));
    const hitFor = (p: string) => hits.filter((h) => h.line.split(" ")[1] === p);

    const renderJs = bundle("render.ts"), probeJs = probeBundle(), feedJs = bundle("feed.ts");
    let editorChat = { csp: "", parts: [] as string[] }, editorFeed = { csp: "", parts: [] as string[] };
    let slice = { text: "" };
    page = await listen((req, res) => {
      const withHeaders = (extra: Record<string, string>, drop?: string) => { const all = { ...headers, ...extra }; if (drop) delete all[drop]; return all; };
      const u = new URL(req.url || "/", "http://x");
      const p = u.pathname;
      if (p === "/chat") { res.writeHead(200, withHeaders({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" })); res.end(chatHtml(null)); return; }
      if (p === "/chat-editor") { res.writeHead(200, withHeaders({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" })); res.end(chatHtml(editorChat.csp)); return; }
      if (p === "/chat-noref") { res.writeHead(200, withHeaders({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" }, "Referrer-Policy")); res.end(chatHtml(null)); return; }
      if (p === "/feed") { res.writeHead(200, withHeaders({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" })); res.end(feedHtml(null)); return; }
      if (p === "/feed-editor") { res.writeHead(200, withHeaders({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" })); res.end(feedHtml(editorFeed.csp)); return; }
      if (p === "/dist/render.js") { res.writeHead(200, withHeaders({ "Content-Type": "application/javascript" })); res.end(renderJs); return; }
      if (p === "/dist/probe.js") { res.writeHead(200, withHeaders({ "Content-Type": "application/javascript" })); res.end(probeJs); return; }
      if (p === "/dist/feed.js") { res.writeHead(200, withHeaders({ "Content-Type": "application/javascript" })); res.end(feedJs); return; }
      if (p === "/file" && u.searchParams.get("slice") === "1") {
        res.writeHead(200, withHeaders({ "Content-Type": "application/json" }));
        res.end(JSON.stringify({ kind: "markdown", title: "notes.md", allowed: true, text: slice.text, found: true, truncated: false, hit: true, size: slice.text.length }));
        return;
      }
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
    await context.addCookies([
      { name: "lax_only", value: "1", domain: "127.0.0.1", path: "/", sameSite: "Lax" },
      { name: "cross_site", value: "1", domain: "127.0.0.1", path: "/", sameSite: "None", secure: true },
    ]);
    const pg = await context.newPage();
    pg.on("pageerror", (e: Error) => { errors.push(e.message); });

    // the per-request asserts a paint reference carries: exactly one, dest image, cross-site, no cookie; mask's Referer the origin
    const assertPaint = (tag: string, scene: string, chromiumList: string[]) => {
      for (const a of chromiumList) {
        const these = hitFor(paintPath(tag, a));
        assert.equal(these.length, 1, scene + ": one request for the " + a + " paint reference: " + JSON.stringify(these));
        assert.equal(these[0].dest, "image", scene + ": " + a + " is sec-fetch-dest image");
        assert.equal(these[0].site, "cross-site", scene + ": " + a + " is cross-site");
        assert.equal(these[0].cookie, null, scene + ": " + a + " carries no cookie (a CORS request)");
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
      await arrived(paint.chromium.map((a) => paintPath(tag, a)), 10000);
      console.log("file preview scene (" + mode + ") request lines:");
      for (const h of hits.filter((x) => x.line.includes(" /" + tag + "-"))) console.log("  " + JSON.stringify(h));
      assert.deepEqual(paintOf(tag).sort(), paint.chromium.slice().sort(), mode + ": the paint references arrive, the Chromium list SECURITY.md names");
      assertPaint(tag, "file preview (" + mode + ")", paint.chromium);
      for (const m of MEDIA) assert.equal(hits.filter((h) => h.line.split(" ")[1].startsWith(`/${tag}-media-${m}.`)).length, 0, mode + ": the media element " + m + " is stripped before the nodes join the page");
      const dom = await pg.evaluate(() => { const b = document.querySelector("#file-preview-pop .fp-body") as HTMLElement; return { media: /<(img|video|audio|source|image)\b/i.test(b.innerHTML), poster: /poster=/.test(b.innerHTML) }; });
      assert.ok(!dom.media && !dom.poster, mode + ": the file preview card holds no media element (the strip removed them)");
    }

    // the notice card scene: feed.ts's own notice card over a feed frame, the media stripped
    {
      const tag = "nt";
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
      await pg.waitForFunction((k: string) => { const c = Array.from(document.querySelectorAll("[data-key]")).find((x) => (x as HTMLElement).dataset.key === k) as HTMLElement | undefined; return !!c && !!c.querySelector(".fask-nbody svg"); }, "a:" + itemId, { timeout: 10000 });
      await arrived(paint.chromium.map((a) => paintPath(tag, a)), 10000);
      console.log("notice card scene request lines:");
      for (const h of hits.filter((x) => x.line.includes(" /" + tag + "-"))) console.log("  " + JSON.stringify(h));
      assert.deepEqual(paintOf(tag).sort(), paint.chromium.slice().sort(), "notice: the paint references arrive, the Chromium list SECURITY.md names");
      assertPaint(tag, "notice card", paint.chromium);
      for (const m of MEDIA) assert.equal(hits.filter((h) => h.line.split(" ")[1].startsWith(`/${tag}-media-${m}.`)).length, 0, "notice: the media element " + m + " is stripped");
      const noMedia = await pg.evaluate((k: string) => { const c = Array.from(document.querySelectorAll("[data-key]")).find((x) => (x as HTMLElement).dataset.key === k) as HTMLElement; const b = c.querySelector(".fask-nbody") as HTMLElement; return !/<(img|video|audio|source|image)\b/i.test(b.innerHTML) && !/poster=/.test(b.innerHTML); }, "a:" + itemId);
      assert.ok(noMedia, "the notice card body holds no media element (the strip removed them)");
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
  } finally {
    await chromium.close();
    if (media) media.server.close();
    if (page) page.server.close();
  }
});

// Firefox and WebKit: the paint scene through md(), the engine's own list (at least mask), skipping loudly per engine that cannot
// launch (CI installs none). The leg is the witness for those engines (the round ruled the leg carries them, no notes path).
for (const engineName of ["firefox", "webkit"]) {
  test(`the chat-media road on ${engineName}: an inline svg's paint references load (at least the attribute SECURITY.md names for Firefox and WebKit); the no-engine attribute does not`, { timeout: 120000 }, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[engineName].launch(); }
    catch (e) { t.skip("no " + engineName + " on this box; the leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    let media: { server: http.Server; origin: string } | null = null, page: { server: http.Server; origin: string } | null = null;
    try {
      const headers = dashboardHeaders();
      const paint = paintFromSecurity();
      const hits: Hit[] = [];
      const waiters: { paths: Set<string>; done: () => void }[] = [];
      media = await listen((req, res) => {
        const h = req.headers, u = req.url || "";
        hits.push({ line: `${req.method} ${u} HTTP/${req.httpVersion}`, referer: (h.referer as string) ?? null, cookie: (h.cookie as string) ?? null, site: h["sec-fetch-site"] as string, dest: h["sec-fetch-dest"] as string });
        for (const w of waiters.slice()) { w.paths.delete(u); if (!w.paths.size) { waiters.splice(waiters.indexOf(w), 1); w.done(); } }
        if (u.endsWith(".svg")) { res.writeHead(200, { "Content-Type": "image/svg+xml", "Content-Length": String(Buffer.byteLength(SVG_DOC)) }); res.end(SVG_DOC); return; }
        res.writeHead(404); res.end();
      }, "127.0.0.1");
      const arrived = (paths: string[], ms: number) => new Promise<void>((ok) => {
        const pending = new Set(paths.filter((p) => !hits.some((h) => h.line.split(" ")[1] === p)));
        if (!pending.size) return ok();
        const w = { paths: pending, done: () => { clearTimeout(timer); ok(); } };
        const timer = setTimeout(() => { const i = waiters.indexOf(w); if (i >= 0) waiters.splice(i, 1); ok(); }, ms);   // the no-engine and unloaded attributes never arrive; the bound ends the wait
        waiters.push(w);
      });
      const renderJs = bundle("render.ts"), probeJs = probeBundle();
      page = await listen((req, res) => {
        const u = new URL(req.url || "/", "http://x");
        const all = { ...headers, "Content-Type": u.pathname.startsWith("/dist/") ? "application/javascript" : "text/html; charset=utf-8", "Cache-Control": "no-cache" };
        if (u.pathname === "/chat") { res.writeHead(200, all); res.end(chatHtml(null)); return; }
        if (u.pathname === "/dist/render.js") { res.writeHead(200, all); res.end(renderJs); return; }
        if (u.pathname === "/dist/probe.js") { res.writeHead(200, all); res.end(probeJs); return; }
        res.writeHead(404); res.end();
      }, "localhost");
      const M = media.origin;
      const context = await browser.newContext({ viewport: { width: 900, height: 700 } });
      const pg = await context.newPage();
      await pg.goto(page.origin + "/chat");
      await pg.waitForFunction(() => typeof (window as any).__md === "function", null, { timeout: 15000 });
      await pg.evaluate((s: string) => { const c = document.getElementById("content") as HTMLElement; const b = document.createElement("div"); b.className = "assistant md"; b.innerHTML = (window as any).__md(s); c.appendChild(b); }, paintMd(M, "e"));
      await arrived(PAINT.map((a) => paintPath("e", a)), 8000);
      const got = PAINT.filter((a) => hits.some((h) => h.line.split(" ")[1] === paintPath("e", a)));
      console.log(engineName + " paint request lines: " + hits.map((h) => h.line + " dest=" + h.dest + " cookie=" + h.cookie).join(" | "));
      assert.ok(got.includes(paint.min), engineName + " loads at least the attribute SECURITY.md names for Firefox and WebKit (" + paint.min + "): arrived " + JSON.stringify(got));
      assert.ok(!got.includes(paint.none), engineName + ": the no-engine attribute (" + paint.none + ") makes no request");
      const maskHit = hits.find((h) => h.line.split(" ")[1] === paintPath("e", paint.min));
      if (maskHit) assert.equal(maskHit.cookie, null, engineName + ": the paint reference carries no cookie (a CORS request)");
      await context.close();
    } finally {
      await browser.close();
      if (media) media.server.close();
      if (page) page.server.close();
    }
  });
}
