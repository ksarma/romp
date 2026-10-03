// The settings page's sign-in link, executed (the fourth review round of the price-feed-off change, extra7-2): on the
// dashboard's settings page (kernel /settings, ui/webview/settings-page.ts) the gear's sign-in anchor (gear.js lgRender:
// `a.href = f.url; a.target = '_blank'; a.rel = 'noreferrer'`) is a page-built anchor with a scheme in a document that
// installs no opener, so a click on it runs no site of this tree: no window.open, no openLink post, the browser's own
// open in a new tab. The clicked-link road's trigger cell and SECURITY.md say so per document, and this leg is the claim's
// executed proof (tests/test_security_price_feed.py's text pins name it). The page is served as the kernel serves it (the
// settings sheet, body.settings-page, feed.css and gear.css, the real settings-page bundle built from this tree), the
// kernel shim's role played by a fake acquireVsCodeApi that records every post, window.open replaced by a recorder, a
// click recorder at the document's capture phase (the login modal stops propagation, so a bubble-phase recorder at the
// window never sees the click), and the gear's init reads (/models, /palette, /tunnels, /logins, /defaults, /version)
// answered with minimal JSON; /version reports a sign-in flow at a synthetic host (example.invalid). The counters prove
// themselves first (one programmatic call each, then reset), so a zero afterwards is a zero the recorder can see. Waits
// are on the page's own events: the anchor's arrival in the DOM, the context's page event for the browser's own open.
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED_CSS = fs.readFileSync(path.join(UI, "feed.css"), "utf8");
const GEAR_CSS = fs.readFileSync(path.join(UI, "gear.css"), "utf8");
const SIGNIN = "https://example.invalid/sign-in?flow=synthetic";

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
function bundle(entry: string): string {
  const r = requireCjs("esbuild").buildSync({ ...BUILD, entryPoints: [path.join(UI, entry)] });
  return r.outputFiles[0].text;
}

// the settings page as the kernel serves it (_settings_page): the two sheets, the transparent body rule, the settings
// class on the body, then the recorders in the shim's place and the real bundle
const PAGE = `<!DOCTYPE html><html lang=en><head><meta charset=UTF-8><meta name=viewport content='width=device-width,initial-scale=1'>
<link href=/dist/feed.css rel=stylesheet><link href=/dist/gear.css rel=stylesheet><title>Romp · settings</title>
<style>html,body.settings-page{background:transparent}</style></head><body class=settings-page>
<script>window.__opens=[];window.open=function(u,t,f){window.__opens.push([u,t,f]);return null;};
window.__posts=[];window.__api={postMessage:function(m){window.__posts.push(m);}};window.acquireVsCodeApi=function(){return window.__api;};
window.__clicks=[];document.addEventListener("click",function(e){var t=e.target;window.__clicks.push({phase:e.eventPhase,prevented:e.defaultPrevented,tag:t&&t.tagName,href:t&&t.getAttribute&&t.getAttribute("href")});},true);</script>
<script src=/dist/settings-page.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

test("the settings page's sign-in link: a real click runs no window.open and posts no openLink; the browser's own open takes it to a new tab and the settings document stays", { timeout: 120000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [], requests: string[] = [];
  try {
    const settingsJs = bundle("settings-page.ts");
    const context = await browser.newContext({ viewport: { width: 1000, height: 800 } });
    context.on("request", (r: any) => { const u = new URL(r.url()); requests.push(r.method() + " " + u.host + u.pathname + u.search); });
    await context.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.hostname === "example.invalid") return route.fulfill({ status: 200, contentType: "text/html", body: "<title>far end (probe)</title>far end" });
      if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/settings") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/settings-page.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: settingsJs });
      if (u.pathname === "/dist/feed.css") return route.fulfill({ status: 200, contentType: "text/css", body: FEED_CSS });
      if (u.pathname === "/dist/gear.css") return route.fulfill({ status: 200, contentType: "text/css", body: GEAR_CSS });
      if (u.pathname === "/version") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ login: { state: "url", url: SIGNIN } }) });
      if (["/models", "/palette", "/tunnels", "/logins", "/defaults"].includes(u.pathname)) return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
      return route.fulfill({ status: 404, body: "" });
    });
    const page = await context.newPage();
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.goto("http://romp.test/settings");

    // the counters prove themselves: one programmatic window.open and one openLink post are recorded, then reset
    const self = await page.evaluate(() => {
      window.open("about:blank", "_blank"); (window as any).__api.postMessage({ type: "openLink", href: "about:blank" });
      const n = { opens: (window as any).__opens.length, posts: (window as any).__posts.filter((m: any) => m && m.type === "openLink").length };
      (window as any).__opens.length = 0; (window as any).__posts.length = 0;
      return n;
    });
    assert.deepEqual(self, { opens: 1, posts: 1 }, "precondition: both recorders count");

    // open the gear as the shell does (a window message), which fills the panel from /version and builds the sign-in
    // anchor (lgRender); then the Log in button shows the modal the anchor stands in (the flow is mid-run, so the
    // button reopens the modal and posts nothing)
    await page.evaluate(() => { window.postMessage({ romp: "openSettings", tab: "general" }, "*"); });
    await page.waitForSelector("#rs-login-url a[href]", { state: "attached", timeout: 8000 });
    await page.click("#rs-login-btn", { timeout: 8000 });
    await page.waitForSelector("#rs-login-url a[href]", { state: "visible", timeout: 8000 });
    const anchor = await page.evaluate(() => {
      const a = document.querySelector("#rs-login-url a[href]") as HTMLAnchorElement;
      const all = Array.from(document.querySelectorAll("a[href]")).map((x) => ({ href: x.getAttribute("href"), cls: x.className, target: x.getAttribute("target") }));
      return { href: a.getAttribute("href"), target: a.getAttribute("target"), rel: a.getAttribute("rel"), className: a.className, inMd: !!a.closest(".md"), dataAct: a.hasAttribute("data-act"), anchorsWithHref: all };
    });
    assert.equal(anchor.href, SIGNIN, "the anchor carries /version's sign-in URL");
    assert.deepEqual([anchor.target, anchor.rel, anchor.className, anchor.inMd, anchor.dataAct], ["_blank", "noreferrer", "", false, false],
      "the gear builds the anchor to open in a new tab, with noreferrer, no class, outside any message body and with no page action");
    assert.equal(anchor.anchorsWithHref.length, 1, "the settings document has one anchor with an href, this one: " + JSON.stringify(anchor.anchorsWithHref));
    // the Log in button's own click reached the recorder (a button, no href); the record is cleared so the count below
    // is the anchor's click alone
    const before = await page.evaluate(() => {
      const clicks = (window as any).__clicks.map((c: any) => c.tag); (window as any).__clicks.length = 0;
      return { opens: (window as any).__opens.length, posts: (window as any).__posts.length, clicks };
    });
    assert.deepEqual(before, { opens: 0, posts: 0, clicks: ["BUTTON"] }, "nothing opened or posted before the click under test; the one click so far was the Log in button's");

    // the click under test: the browser's own open is the context's page event (armed before the click; a bound, not a
    // sleep, and a miss is read below AFTER the counters, so an opener that swallowed the click is named as the opener)
    const popupP = context.waitForEvent("page", { timeout: 8000 }).catch(() => null);
    await page.click("#rs-login-url a[href]", { timeout: 8000 });
    const popup = await popupP;
    if (popup) await popup.waitForLoadState("load", { timeout: 8000 });
    const after = await page.evaluate(() => ({ opens: (window as any).__opens, posts: (window as any).__posts, clicks: (window as any).__clicks }));
    console.log("settings page: request lines seen: " + requests.join(" | "));
    console.log("settings page: after the click: " + JSON.stringify({ opens: after.opens, posts: after.posts, clicks: after.clicks, popup: popup ? popup.url() : null, main: page.url() }));
    assert.deepEqual(after.opens, [], "no window.open ran on the click: the settings page installs no opener");
    assert.deepEqual(after.posts.filter((m: any) => m && m.type === "openLink"), [], "no openLink post: the delegate that would post it is not in this document");
    assert.deepEqual(after.posts, [], "no post of any type on the click");
    assert.equal(after.clicks.length, 1, "one click reached the document: " + JSON.stringify(after.clicks));
    assert.deepEqual([after.clicks[0].phase, after.clicks[0].prevented, after.clicks[0].tag, after.clicks[0].href], [1, false, "A", SIGNIN],
      "the click reached the document's capture phase on the anchor with its default action intact");
    assert.ok(popup, "the browser's own open: the context saw a new page within the bound");
    assert.equal(popup.url(), SIGNIN, "the browser's own open: a new page at the anchor's href");
    assert.equal(page.url(), "http://romp.test/settings", "the settings document stays where it was");
    assert.ok(requests.some((r) => r === "GET example.invalid/sign-in?flow=synthetic"), "the sign-in host saw the new page's navigation and nothing else: " + requests.join(" | "));
    assert.equal(requests.filter((r) => r.includes("example.invalid")).length, 1, "one request to the sign-in host, the new tab's navigation");
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    await browser.close();
  }
});
