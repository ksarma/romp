// The chat-media road's executed witness (the fourth review round of the price-feed-off change, tests-1): on the web
// dashboard a rendered message's media loads from the host its URL names the moment the message renders, with no click,
// with the cross-site cookies that browser sends to that host and no Referer; under the editor webviews' CSP the request
// does not go. Two real servers on the loopback: the page server at http://localhost:P answers /chat with the headers
// Handler._send puts on every page the kernel serves, read from kernel/kernel.py's source and pinned by value below (a
// source pin, stated as such: the wire-level tie, the kernel's own Handler answering GET /chat with the same four
// headers, is tests/test_security_price_feed.py TheChatMediaRoadIsWitnessed); the media listener at http://127.0.0.1:Q
// records every request line and its headers and answers a 1x1 PNG or a 16-byte clip. localhost and 127.0.0.1 are two
// sites (the registrable domain differs), so a cookie set on 127.0.0.1 with SameSite=Lax is withheld and one with
// SameSite=None; Secure is sent, which is what "the cross-site cookies that browser sends" means; the two loopback sites
// stand in for an https media host (a Secure cookie is honoured over http on the loopback, where a deployed media host
// is https; the rule shown is the browser's cross-site rule either way). The message goes through md()'s pipeline as
// render.ts runs it (marked, sanitizeMd, linkifyPrRefs, mdImgPostPass) for a session's reply and a postal body, and
// through userMd()'s (userMdHtml, the same three) for the user's own message; the probe composes the two pipelines from
// the same modules, and the exact code-line pin on md()'s and userMd()'s bodies ties the probe to the source, so a
// statement added to either (a gate, say) reds the tie and the probe must follow it before the scenes mean anything; a
// gate placed at the call sites instead (a wrapper around the innerHTML writes) would not red the scenes until the probe
// follows it. Scene 2 serves the same page under the editor's CSP (extension.ts buildHtml, its cspSource standing in as
// 'self', the page's own origin) and reads the page's securitypolicyviolation events, the page's own signal, so the
// evidence of absence is event-based. Scene 3 is the control for the Referrer-Policy header: the same page without it
// sends the origin as Referer. The landing page frames /chat under the same _send headers; the frame case is not
// executed separately. Every wait is on a request event or the page's own event, never a timer alone; the bounds are
// the failure. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic
// values only: loopback URLs and invented cookie names.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as http from "node:http";
import * as path from "node:path";
import type { AddressInfo } from "node:net";
import { createRequire } from "node:module";
import { chatBody, ATTACH_TITLE_WEB } from "../../vscode-extension/src/page-skeleton";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const ROOT = path.resolve(EXT, "..");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
const KERNEL = fs.readFileSync(path.join(ROOT, "kernel", "kernel.py"), "utf8");
const EXTENSION = fs.readFileSync(path.join(EXT, "src", "extension.ts"), "utf8");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");

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

/** The editor chat webview's CSP: buildHtml's `csp` array in extension.ts, each part with the webview's resource origin
 *  (`${webview.cspSource}`) standing in as 'self', the kernel base as the given origin and the nonce filled. */
export function editorCsp(nonce: string, kernelBase: string): { csp: string; parts: string[] } {
  const fn = /\nfunction buildHtml\(webview: vscode\.Webview\): string \{\n([\s\S]*?)\n\}\n/.exec(EXTENSION);
  assert.ok(fn, "vscode-extension/src/extension.ts buildHtml");
  const arr = /const csp = \[\n([\s\S]*?)\n  \]\.join\("; "\);/.exec(fn![1]);
  assert.ok(arr, "buildHtml's csp array");
  const parts = Array.from(arr![1].matchAll(/^\s*[`"]([^`"]+)[`"],?\s*$/gm)).map((x) => x[1]);
  const csp = parts.map((p) => p.replace("${webview.cspSource}", "'self'").replace("${kernelBase}", kernelBase).replace("${n}", nonce)).join("; ");
  return { csp, parts };
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

// ── the page ────────────────────────────────────────────────────────────────────────────────────────

const NONCE = "witness-nonce-0001";
/** The chat page as the web dashboard serves it (the shared skeleton, the chat's sheet, the kernel shim's role played by a
 *  fake acquireVsCodeApi, window.open recorded), then the real chat bundle and the probe; `csp` adds the editor's meta. */
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

type Hit = { line: string; host?: string; referer: string | null; cookie: string | null; site?: string; dest?: string; range?: string };

async function listen(handler: http.RequestListener, host: string): Promise<{ server: http.Server; origin: string }> {
  const server = http.createServer(handler);
  await new Promise<void>((ok, bad) => { server.once("error", bad); server.listen(0, host, () => ok()); });
  const a = server.address() as AddressInfo;
  return { server, origin: `http://${host}:${a.port}` };
}

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

test("the chat-media road: a rendered message's image, video, audio, srcset, picture, poster and inline svg image load on the web dashboard with no click, no Referer and the cross-site cookies only; the editor's CSP blocks every one", { timeout: 120000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }

  const errors: string[] = [];
  let media: { server: http.Server; origin: string } | null = null, page: { server: http.Server; origin: string } | null = null;
  try {
    // the pipelines the probe composes are md()'s and userMd()'s, statement for statement (render.ts): a step added to
    // either body, a gate for instance, reds this tie, and the probe must follow it before the scenes mean anything
    const mdFn = tsFunction(RENDER, "function md(src: string, repo: string | null = prRepoFor()): string {");
    const userFn = tsFunction(RENDER, "function userMd(src: string, repo: string | null = prRepoFor()): string {");
    assert.deepEqual(codeLines(mdFn), MD_BODY, "md()'s body is the pipeline the probe composes");
    assert.deepEqual(codeLines(userFn), USER_MD_BODY, "userMd()'s body is the pipeline the probe composes");

    // the headers every page the kernel serves carries, read from Handler._send and pinned by value: no img-src or
    // media-src (a framing CSP alone), Referrer-Policy same-origin, and no Cross-Origin-* header (the set equality)
    const headers = dashboardHeaders();
    assert.deepEqual(headers, DASHBOARD_HEADERS, "the kernel's pages carry these four headers and no other unconditional one: " + JSON.stringify(headers));
    assert.ok(!Object.keys(headers).some((k) => /^cross-origin-/i.test(k)), "no Cross-Origin-* header on the dashboard's pages");

    const hits: Hit[] = [];
    const waiters: { paths: Set<string>; done: () => void }[] = [];
    media = await listen((req, res) => {
      const h = req.headers;
      hits.push({ line: `${req.method} ${req.url} HTTP/${req.httpVersion}`, host: h.host, referer: (h.referer as string) ?? null, cookie: (h.cookie as string) ?? null,
        site: h["sec-fetch-site"] as string, dest: h["sec-fetch-dest"] as string, range: h.range as string });
      for (const w of waiters) { w.paths.delete(req.url || ""); if (!w.paths.size) w.done(); }
      if ((req.url || "").endsWith(".png")) { res.writeHead(200, { "Content-Type": "image/png", "Content-Length": String(PNG.length) }); res.end(PNG); return; }
      if ((req.url || "").endsWith(".mp4")) { res.writeHead(200, { "Content-Type": "video/mp4", "Content-Length": "16" }); res.end(Buffer.alloc(16)); return; }
      if ((req.url || "").endsWith(".mp3")) { res.writeHead(200, { "Content-Type": "audio/mpeg", "Content-Length": "16" }); res.end(Buffer.alloc(16)); return; }
      res.writeHead(404); res.end();
    }, "127.0.0.1");
    // resolves when every path has arrived at the media host (the request event), rejects at the bound naming what came
    const arrived = (paths: string[], ms: number) => new Promise<void>((ok, bad) => {
      const pending = new Set(paths.filter((p) => !hits.some((h) => h.line.split(" ")[1] === p)));
      if (!pending.size) return ok();
      const w = { paths: pending, done: () => { clearTimeout(timer); ok(); } };
      const timer = setTimeout(() => { waiters.splice(waiters.indexOf(w), 1); bad(new Error("no request for " + Array.from(pending).join(", ") + " within " + ms + " ms; arrived: " + hits.map((h) => h.line).join(" | "))); }, ms);
      waiters.push(w);
    });

    const renderJs = bundle("render.ts"), probeJs = probeBundle();
    let editor = { csp: "", parts: [] as string[] };
    page = await listen((req, res) => {
      const withHeaders = (extra: Record<string, string>, drop?: string) => { const all = { ...headers, ...extra }; if (drop) delete all[drop]; return all; };
      const u = req.url || "";
      if (u === "/chat") { res.writeHead(200, withHeaders({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" })); res.end(chatHtml(null)); return; }
      if (u === "/chat-editor") { res.writeHead(200, withHeaders({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" })); res.end(chatHtml(editor.csp)); return; }
      if (u === "/chat-noref") { res.writeHead(200, withHeaders({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" }, "Referrer-Policy")); res.end(chatHtml(null)); return; }
      if (u === "/dist/render.js") { res.writeHead(200, withHeaders({ "Content-Type": "application/javascript" })); res.end(renderJs); return; }
      if (u === "/dist/probe.js") { res.writeHead(200, withHeaders({ "Content-Type": "application/javascript" })); res.end(probeJs); return; }
      res.writeHead(404, withHeaders({ "Content-Type": "text/plain" })); res.end("");
    }, "localhost");
    editor = editorCsp(NONCE, page.origin);   // the page server plays the kernel: connect-src names it, as the webview's names its kernel
    assert.ok(editor.parts.includes("default-src 'none'"), "the editor's CSP starts from default-src 'none': " + JSON.stringify(editor.parts));
    assert.ok(editor.parts.some((p) => p.startsWith("img-src ${webview.cspSource}")), "img-src is the webview's own resource origin (and data:): " + JSON.stringify(editor.parts));
    assert.ok(!editor.parts.some((p) => p.startsWith("media-src")), "no media-src: video and audio fall to default-src 'none'");

    const M = media.origin, P = page.origin;
    // the population: the three message kinds with a markdown image, and every media element the sanitizer's html
    // profile keeps (the road's trigger cell names them): video, audio, srcset, a picture's source, a video's poster, an
    // inline svg's image
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

    const context = await browser.newContext({ viewport: { width: 900, height: 700 } });
    // two cookies on the media host: the Lax one a top-level navigation would carry, the None; Secure one a cross-site
    // subresource carries (the loopback is a potentially trustworthy origin, so Secure is honoured over http)
    await context.addCookies([
      { name: "lax_only", value: "1", domain: "127.0.0.1", path: "/", sameSite: "Lax" },
      { name: "cross_site", value: "1", domain: "127.0.0.1", path: "/", sameSite: "None", secure: true },
    ]);
    const pg = await context.newPage();
    pg.on("pageerror", (e: Error) => { errors.push(e.message); });

    // scene 1: the dashboard's headers
    await pg.goto(P + "/chat");
    const dash = population("dash");
    for (const p of dash) { const html = await show(pg, p.kind, p.md); assert.ok(/<(img|video|audio|source|image)\b/.test(html), p.name + ": the sanitizer kept the media element: " + html); }
    await arrived(dash.flatMap((p) => p.paths), 8000);
    const dashHits = hits.filter((h) => h.line.includes(" /dash-"));
    console.log("scene 1 (dashboard headers " + JSON.stringify(headers) + ") request lines:");
    for (const h of dashHits) console.log("  " + JSON.stringify(h));
    for (const p of dash) for (const q of p.paths) {
      const these = dashHits.filter((x) => x.line.split(" ")[1] === q);
      assert.equal(these.length, 1, p.name + ": one request for " + q + " arrived at the media host on render: " + JSON.stringify(these));
      const h = these[0];
      assert.equal(h.referer, null, p.name + ": no Referer (Referrer-Policy same-origin)");
      assert.equal(h.site, "cross-site", p.name + ": the browser classes the request cross-site");
      assert.equal(h.cookie, "cross_site=1", p.name + ": the SameSite=None cookie rides, the Lax one is withheld");
    }
    const opens = await pg.evaluate(() => (window as any).__opens.length);
    assert.equal(opens, 0, "no click, no window.open: the loads are the render's own");

    // scene 2: the editor webview's CSP over the same page and the same messages: no request reaches the media host;
    // the page's securitypolicyviolation events are the signal waited on, one per planted URL
    await pg.goto(P + "/chat-editor");
    const ed = population("ed");
    for (const p of ed) { const html = await show(pg, p.kind, p.md); assert.ok(/<(img|video|audio|source|image)\b/.test(html), p.name + " under the editor CSP: the sanitizer kept the element: " + html); }
    await pg.waitForFunction(([n, m]: [number, string]) => (window as any).__csp.filter((v: any) => String(v.blocked).startsWith(m)).length >= n, [ed.length, M] as [number, string], { timeout: 8000 });
    const all = await pg.evaluate(() => (window as any).__csp);
    const violations = all.filter((v: any) => String(v.blocked).startsWith(M));   // the bundle's own fetches to the page origin are the harness's, not the road's
    console.log("scene 2 (editor CSP " + editor.csp + ") violations:");
    for (const v of violations) console.log("  " + JSON.stringify(v));
    const edHits = hits.filter((h) => h.line.includes(" /ed-"));
    console.log("scene 2 request lines at the media host: " + (edHits.length ? edHits.map((h) => h.line).join(" | ") : "(none)"));
    assert.deepEqual(edHits, [], "under the editor's CSP no request for the ed- media reached the host");
    for (const p of ed) for (const q of p.paths) assert.ok(violations.some((v: any) => v.blocked === M + q), p.name + " under the editor CSP: the browser reported the blocked load of " + q + ": " + JSON.stringify(violations));
    assert.ok(violations.some((v: any) => v.directive === "img-src") && violations.some((v: any) => v.directive === "media-src"), "img-src blocked the pictures, media-src (from default-src 'none') the clips: " + JSON.stringify(violations));

    // scene 3: the control for the header: without Referrer-Policy the browser's default sends the page's origin
    await pg.goto(P + "/chat-noref");
    await show(pg, "assistant", `![pic](${M}/noref-assistant.png)`);
    await arrived(["/noref-assistant.png"], 8000);
    const ctl = hits.find((h) => h.line.split(" ")[1] === "/noref-assistant.png")!;
    console.log("scene 3 (no Referrer-Policy) request line: " + JSON.stringify(ctl));
    assert.equal(ctl.referer, P + "/", "the control: with the header absent the browser's default sends the origin, so the header is what removes it");
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    await browser.close();
    if (media) media.server.close();
    if (page) page.server.close();
  }
});
