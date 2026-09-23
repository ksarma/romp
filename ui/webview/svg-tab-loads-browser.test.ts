// The .svg tab road's executed witness (the fifth review round of the price-feed-off change, extra6-2): on the web dashboard a
// Cmd, Ctrl or middle click on a path link to an .svg in a viewed file reaches openFileTab (ui/webview/preview.ts), which opens the
// kernel's /file URL, or a remote session's /remote/<host>/file relay, in the browser's own tab; the tab is an svg document,
// sandboxed, that loads the hosts its own markup names. Two real servers on the loopback: the page server at http://localhost:P
// plays the kernel, answering /file and /remote/labhost/file for an .svg with the headers the kernel writes on that success,
// read from kernel/kernel.py's source and pinned by value below (Handler._send's four unconditional headers and
// _media_policy_headers' sandbox: a source pin, stated as such; the wire-level tie, the kernel's own Handler writing exactly
// these on both arms, is tests/test_security_price_feed.py); the media listener at http://127.0.0.1:Q records every request line
// with its Cookie, Referer, Origin and Sec-Fetch-Site. localhost and 127.0.0.1 are two sites, so of the two cookies set on
// 127.0.0.1 the SameSite=None; Secure one rides a cross-site load and the Lax one does not. The tab is opened by openFileTab
// itself, bundled from preview.ts and called from a real Control-click, so its URL is fileUrl's. The svg names seven loads: an
// image href and xlink:href, a CSS @import and a foreignObject img (loads the browser makes without CORS: the SameSite=None
// cookie rides), and a fill, a mask and a CSS fill paint reference (CORS mode: no cookie, Origin null); none carries a Referer,
// and an inline script's fetch never runs (the page's console reports the sandbox's block, the event waited on). Scene 2 is the
// relay's URL. Scene 3 is the control for the sandbox: the same svg without it runs its script, and its mask reference sends the
// page's origin as Referer, so the sandbox is what holds both. Every wait is on a request event or the page's own event, never a
// timer alone; the bounds are the failure. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs
// do. Synthetic values only: loopback URLs, invented cookie names, a placeholder session id and a TESTHOST path.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as http from "node:http";
import * as path from "node:path";
import type { AddressInfo } from "node:net";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KERNEL = fs.readFileSync(path.resolve(EXT, "..", "kernel", "kernel.py"), "utf8");
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");

// ── the headers, from the code that sends them ──────────────────────────────────────────────────────

/** Handler._send's unconditional two-literal send_header lines (the chat-media witness reads the same lines). */
function sendHeaders(): Record<string, string> {
  const m = /\n    def _send\(self, code, body, ctype, cache=None, headers=None\):\n([\s\S]*?)\n        for k, v in \(headers or \{\}\)\.items\(\):/.exec(KERNEL);
  assert.ok(m, "kernel/kernel.py Handler._send up to its caller-supplied headers loop");
  const out: Record<string, string> = {};
  for (const h of m![1].matchAll(/^        self\.send_header\("([^"]+)", "([^"]+)"\)/gm)) out[h[1]] = h[2];
  return out;
}
/** _media_policy_headers' return for image/svg+xml, the one pair it adds. */
function svgPolicy(): [string, string] {
  const m = /\ndef _media_policy_headers\(mime\):\n[\s\S]*?\n    return \{"([^"]+)": "([^"]+)"\} if mime == _IMG_MIME\["\.svg"\] else \{\}\n/.exec(KERNEL);
  assert.ok(m, "kernel/kernel.py _media_policy_headers' return");
  return [m![1], m![2]];
}
/** What a /file success for an .svg carries at this head, by value (tests/test_security_price_feed.py reads the same on the wire,
 *  both arms): the four every page carries, the sandbox beside the framing policy under the same name, the type and no-cache. */
export const SVG_FILE_HEADERS: [string, string][] = [
  ["Content-Type", "image/svg+xml"],
  ["X-Content-Type-Options", "nosniff"],
  ["X-Frame-Options", "SAMEORIGIN"],
  ["Content-Security-Policy", "frame-ancestors 'self'"],
  ["Referrer-Policy", "same-origin"],
  ["Content-Security-Policy", "sandbox"],
  ["Cache-Control", "no-cache"],
];
/** The seven loads the svg names, with whether the SameSite=None cookie rides (a load without CORS) or not (CORS mode). */
export const SEVEN: [string, boolean][] = [["image.png", true], ["ximage.png", true], ["import.css", true], ["fo-img.png", true],
  ["fill.svg", false], ["mask.svg", false], ["cssfill.svg", false]];
function svg(M: string, t: string): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="60">
<style>@import url("${M}/${t}-import.css"); .c { fill: url("${M}/${t}-cssfill.svg#p"); }</style>
<image href="${M}/${t}-image.png" width="10" height="10"/><image xlink:href="${M}/${t}-ximage.png" x="12" width="10" height="10"/>
<foreignObject x="24" width="20" height="20"><img xmlns="http://www.w3.org/1999/xhtml" src="${M}/${t}-fo-img.png" width="10" height="10"/></foreignObject>
<rect x="48" width="10" height="10" fill="url(${M}/${t}-fill.svg#p)"/><rect x="60" width="10" height="10" mask="url(${M}/${t}-mask.svg#m)"/><rect class="c" x="72" width="10" height="10"/>
<script>fetch("${M}/${t}-script-ran.png")</script></svg>`;
}

// ── the opener, as preview.ts runs it ────────────────────────────────────────────────────────────────

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
function openerBundle(): string {
  const contents = 'import { openFileTab, fileUrl } from "./preview";\n(window as any).__openFileTab = openFileTab; (window as any).__fileUrl = fileUrl;';
  return requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, sourcefile: "svg-tab-probe.ts", loader: "ts" } }).outputFiles[0].text;
}

type Hit = { path: string; cookie: string | null; referer: string | null; origin: string | null; site: string | null };
async function listen(handler: http.RequestListener, host: string): Promise<{ server: http.Server; origin: string }> {
  const server = http.createServer(handler);
  await new Promise<void>((ok, bad) => { server.once("error", bad); server.listen(0, host, () => ok()); });
  return { server, origin: `http://${host}:${(server.address() as AddressInfo).port}` };
}
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

test("the .svg tab road: openFileTab's tab of an .svg under the kernel's /file headers loads the seven hosts its markup names, the non-CORS loads with the cross-site cookie, the paint references without, none with a Referer; the sandbox is what stops its script", { timeout: 120000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  let media: { server: http.Server; origin: string } | null = null, page: { server: http.Server; origin: string } | null = null;
  try {
    const send = sendHeaders(), pol = svgPolicy();
    const read: [string, string][] = [["Content-Type", "image/svg+xml"], ...Object.entries(send), pol, ["Cache-Control", "no-cache"]];
    assert.deepEqual(read, SVG_FILE_HEADERS, "the /file success for an .svg carries these, read from _send and _media_policy_headers: " + JSON.stringify(read));
    const hits: Hit[] = [];
    const waiters: { paths: Set<string>; done: () => void }[] = [];
    media = await listen((req, res) => {
      const h = req.headers, u = req.url || "";
      hits.push({ path: u, cookie: (h.cookie as string) ?? null, referer: (h.referer as string) ?? null, origin: (h.origin as string) ?? null, site: (h["sec-fetch-site"] as string) ?? null });
      for (const w of waiters.slice()) { w.paths.delete(u); if (!w.paths.size) { waiters.splice(waiters.indexOf(w), 1); w.done(); } }
      if (u.endsWith(".png")) { res.writeHead(200, { "Content-Type": "image/png" }); res.end(PNG); return; }
      if (u.endsWith(".css")) { res.writeHead(200, { "Content-Type": "text/css" }); res.end("rect{}"); return; }
      if (u.endsWith(".svg")) { res.writeHead(200, { "Content-Type": "image/svg+xml" }); res.end('<svg xmlns="http://www.w3.org/2000/svg"/>'); return; }
      res.writeHead(404); res.end();
    }, "127.0.0.1");
    const arrived = (paths: string[], ms: number) => new Promise<void>((ok, bad) => {
      const pending = new Set(paths.filter((p) => !hits.some((h) => h.path === p)));
      if (!pending.size) return ok();
      const w = { paths: pending, done: () => { clearTimeout(timer); ok(); } };
      const timer = setTimeout(() => { waiters.splice(waiters.indexOf(w), 1); bad(new Error("no request for " + Array.from(pending).join(", ") + " within " + ms + " ms; arrived: " + hits.map((h) => h.path).join(" | "))); }, ms);
      waiters.push(w);
    });
    const M = media.origin;
    const TOKEN = "witness-token-0001";                           // the opener page's address carries it, as the shell's first load does
    page = await listen((req, res) => {
      const u = new URL(req.url || "/", "http://x");
      if (u.pathname === "/opener") { res.writeHead(200, [["Content-Type", "text/plain; charset=utf-8"], ...Object.entries(send)].flat()); res.end("the tab's opener\n"); return; }
      const bare = u.pathname === "/nosandbox/file";
      if (u.pathname !== "/file" && u.pathname !== "/remote/labhost/file" && !bare) { res.writeHead(404); res.end(); return; }
      const hs = SVG_FILE_HEADERS.filter(([k, v]) => !(bare && k === pol[0] && v === pol[1]));
      res.writeHead(200, hs.flat()); res.end(svg(M, path.basename(u.searchParams.get("path") || "", ".svg")));
    }, "localhost");
    const P = page.origin;
    const context = await browser.newContext({ viewport: { width: 900, height: 700 } });
    await context.addCookies([
      { name: "lax_only", value: "1", domain: "127.0.0.1", path: "/", sameSite: "Lax" },
      { name: "cross_site", value: "1", domain: "127.0.0.1", path: "/", sameSite: "None", secure: true },
    ]);
    const pg = await context.newPage();
    await pg.goto(P + "/opener?token=" + TOKEN);
    await pg.evaluate(openerBundle());
    await pg.evaluate(() => { const b = document.createElement("button"); b.id = "open"; b.textContent = "open"; document.body.appendChild(b);
      b.addEventListener("click", () => { const w = window as any; w.__opened = w.__openFileTab(w.__path, w.__sid); }); });
    const open = async (file: string, sid: string | null) => {
      await pg.evaluate(([p, s]: [string, string | null]) => { const w = window as any; w.__path = p; w.__sid = s; }, [file, sid] as [string, string | null]);
      const popup = context.waitForEvent("page", { timeout: 10000 });
      // the page's own report of the sandbox's block, listened for before the click so it cannot fire unheard
      const sandboxed = context.waitForEvent("console", { predicate: (m: any) => /Blocked script execution/.test(m.text()) && m.text().includes(encodeURIComponent(file)), timeout: 10000 });
      await pg.click("#open", { modifiers: ["Control"] });
      const tab = await popup;
      await tab.waitForLoadState("domcontentloaded");
      assert.equal(await pg.evaluate(() => (window as any).__opened), true, "openFileTab reports the tab opened");
      assert.equal(tab.url(), P + await pg.evaluate(([p, s]: [string, string | null]) => (window as any).__fileUrl(p, s), [file, sid] as [string, string | null]), "the tab's URL is fileUrl's");
      return { tab, sandboxed };
    };
    const check = (tag: string, scene: string) => {
      const these = hits.filter((h) => h.path.startsWith(`/${tag}-`));
      console.log(scene + " request lines:"); for (const h of these) console.log("  " + JSON.stringify(h));
      for (const [name, cookie] of SEVEN) {
        const one = these.filter((h) => h.path === `/${tag}-${name}`);
        assert.equal(one.length, 1, scene + ": one request for " + name + ": " + JSON.stringify(one));
        assert.equal(one[0].site, "cross-site", scene + ": " + name + " is cross-site");
        assert.equal(one[0].referer, null, scene + ": " + name + " carries no Referer");
        assert.equal(one[0].cookie, cookie ? "cross_site=1" : null, scene + ": " + name + (cookie ? " carries the SameSite=None cookie and not the Lax one" : " carries no cookie (CORS mode)"));
        if (!cookie) assert.equal(one[0].origin, "null", scene + ": " + name + " is a CORS request from the sandbox's opaque origin");
      }
      assert.ok(!these.some((h) => h.path.endsWith("-script-ran.png")), scene + ": the sandbox stops the svg's script");
      assert.ok(!these.some((h) => [h.path, h.referer, h.cookie].some((v) => v && v.includes(TOKEN))), scene + ": no request carries the serve token");
    };

    // scene 1: the local /file URL
    const f1 = "/tmp/TESTHOST/notes-api/docs/s1.svg";
    const { tab: tab1, sandboxed: b1 } = await open(f1, null);
    await arrived(SEVEN.map(([n]) => `/s1-${n}`), 10000);
    await b1;                                                     // the page's own report of the sandbox's block: its script never ran
    assert.ok(!tab1.url().includes("token="), "the tab's URL carries no serve token");
    check("s1", "scene 1 (/file)");
    await tab1.close();

    // scene 2: a remote session's file, the relay's URL (the same headers: the Python tie reads them on the relay's wire)
    const { tab: tab2, sandboxed: b2 } = await open("/tmp/TESTHOST/notes-api/docs/s2.svg", "labhost:11111111-2222-3333-4444-555555555555");
    assert.ok(tab2.url().startsWith(P + "/remote/labhost/file?"), "a host-prefixed session id opens the relay's URL: " + tab2.url());
    await arrived(SEVEN.map(([n]) => `/s2-${n}`), 10000);
    await b2;
    check("s2", "scene 2 (/remote/labhost/file)");
    await tab2.close();

    // scene 3: the control for the sandbox: without it the script runs and the mask reference sends the page's origin
    const tab3 = await context.newPage();
    await tab3.goto(P + "/nosandbox/file?path=" + encodeURIComponent("/tmp/TESTHOST/notes-api/docs/s3.svg"));
    await arrived([...SEVEN.map(([n]) => `/s3-${n}`), "/s3-script-ran.png"], 10000);
    const mask = hits.find((h) => h.path === "/s3-mask.svg")!;
    console.log("scene 3 (no sandbox) mask request: " + JSON.stringify(mask));
    assert.equal(mask.referer, P + "/", "the control: with the sandbox absent the mask reference sends the page's origin, so the sandbox is what removes it");
    await tab3.close();
  } finally {
    await browser.close();
    if (media) media.server.close();
    if (page) page.server.close();
  }
});
