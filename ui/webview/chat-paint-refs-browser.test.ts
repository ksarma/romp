// The render path's witness for the paint strip (paint-refs.ts dropRemoteRefs, run inside md-sanitize.ts sanitizeMd by
// default): an inline svg in a chat message whose paint attribute (`fill`, `stroke`, `mask`, `clip-path`, `filter`, a
// `marker-*`) holds a url() naming a document on another origin made Chromium request that document the moment the message
// rendered, with no click, because the sanitizer keeps all eight attributes and nothing after it on the chat's path read
// them. The instrument is two real servers' request logs, never the page's request events and never a route (the rule in
// file-view-figures-gate-adopt-browser.test.ts's header). The page server at http://localhost:P serves the chat page as
// the dashboard serves it (the shared skeleton, the chat's sheet, a fake acquireVsCodeApi, the chat bundle built from this
// tree) with the headers every kernel page carries, read from kernel/kernel.py's Handler._send (the reader PR 878's chat
// media witness uses), so a request carries the Referer the dashboard's `Referrer-Policy: same-origin` gives it. The remote
// logger at http://127.0.0.1:Q records the method, the path, the Referer and the Sec-Fetch-Dest of every request. A posted
// session frame puts one user message and one assistant reply through render.ts's own userMd() and md(). The reply holds
// every spelling the viewer gate's leg holds (md-config-svg-paint-gate-browser.test.ts), aimed at the remote logger, plus
// a style attribute with mask-image and background-image (the colour-only style hook removes those before the paint pass
// sees them) and a cursor attribute (DOMPurify drops it); the user message holds four of the shapes. The controls: a
// same-document `url(#g)`, a `data:` URL, and three references to the page's own origin (an absolute one in each message
// and a relative one), which the strip keeps and the browser requests from the page server. Those three requests are the
// positive control: the messages rendered and a paint fetch reaches a server log, so an empty remote log is the strip's
// work and not a render that never happened. The remote logger's own control follows the read: a no-cors fetch from the
// page to it, which must be its one line, so an empty log is not a server the page cannot reach. The wait is on the
// control's arrival (bounded), then a drain: one round trip to the page server and 250 ms (the viewer's legs' drain).
// Red before the fix, the same at the base 6cf6839ba (this leg run from a copy of that tree, paint-refs.ts copied beside it
// for the import alone, since the base's sanitizer never calls it) and with the pass removed from sanitizeMd (2026-09-23,
// Chromium 151): the remote logger held 19 requests within 30 ms of the page's own paint fetch, 16 from the reply (fill,
// stroke, clip-path, mask, the mask's image-set, the three markers, the root's fill, the group's fill, both escaped function
// names, the userinfo spelling, the quoted and the spaced url(), the protocol-relative one) and 3 from the user's message
// (fill, the mask's image-set, marker-end). Each carried no Referer but the three mask references, which carried the page's
// origin alone (`http://localhost:P/`), none its path. `filter`, on a rect and on the root, reached the logger in no run,
// as the design note's matrix found, and neither did the HTML span's names, the style attribute or the cursor, which the
// sanitizer already removes; the DOM still held 24 of the 26 remote values as written. Sub-tests 2, 3 and 5 red, the
// controls green. Each other sub-test's red is its own mutation, recorded with the branch's other reds.
// The second test is the browser census of paint-refs.ts's two sets: S_css (the CSS properties whose value takes a url(),
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

// ── the servers ──────────────────────────────────────────────────────────────────────────────────────

/** The headers every page the kernel serves carries: Handler._send's unconditional `send_header` lines with two literal
 *  arguments, up to its caller-supplied headers loop (the reader of PR 878's chat-media witness). Loud when the function's
 *  shape moves, so the page is never served without them in silence. */
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
  const data = 'url("data:image/svg+xml,%3Csvg%2F%3E#p")';
  const kept: Kept[] = [
    { cls: "px-local", el: "rect", attr: "fill", value: "url(#g)" },
    { cls: "px-own", el: "rect", attr: "fill", value: "url(" + P + "/own.svg#p)" },
    { cls: "px-rel", el: "rect", attr: "fill", value: "url(own-rel.svg#p)" },
    { cls: "px-data", el: "rect", attr: "fill", value: data },
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
    svgOf("px-data", rect('fill="url(&quot;data:image/svg+xml,%3Csvg%2F%3E#p&quot;)"')), "",
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
      await t.test("4. the controls are kept as written: a same-document url(#g), a data: URL, the page's own origin absolute and relative, a colour-only style", () => {
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
/** Names the attribute derivation adds to its candidates by hand: the other engines' prefixed and newer url()-taking properties,
 *  so a Chromium that gains one is read for it even when its style object does not list it. */
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
