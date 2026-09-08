// The chat's link delegate over the REAL render.ts bundle in headless Chromium, at an http: origin (the web
// dashboard). Every navigating href a sanitized message can carry must go the way a plain `<a href>` goes: the
// document-level click handler (render.ts) opens it in the user's own browser and cancels the default action,
// so the chat document never leaves. Two shapes the old `closest("a[href]")` missed (the 2026-09-07 review of
// plans/markdown-viewer.md Slice 1): an image map's `<area href>` (not an anchor) and an SVG `<a xlink:href>`
// (`[href]` matches only the null-namespace attribute, and the XLink spelling is namespaced). Both survive the
// sanitizer's html + svg profiles, and a click on either took the chat page to the attacker's URL, losing the
// pane until a reload. Two legs: the delegate's contract over raw markup (what it must do with each shape,
// whatever the sanitizer lets through), and the chat's own markdown pipeline (marked + sanitizeMd, as md() runs
// it) end to end: whatever survives, a click never navigates the document. Skips LOUDLY without a playwright
// browser (CI installs none), as the other browser legs do. Synthetic values only: example.invalid URLs.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { chatBody, ATTACH_TITLE_WEB } from "../../vscode-extension/src/page-skeleton";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8");

// a valid 1x1 transparent PNG: a picture that decodes, so its image map is live (a broken image shows its alt
// text and binds no map, which would pass the area case for the wrong reason; the precondition below checks)
const PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";
const XLINK = "http://www.w3.org/1999/xlink";

// the shapes, each with the element the click lands on and the URL the delegate must hand to window.open
const SHAPES: { name: string; html: string; sel: string; hit: string; href: string }[] = [
  { name: "a plain anchor (control)", sel: ".fx-body a", hit: "A", href: "https://example.invalid/ctl",
    html: '<p>A <a href="https://example.invalid/ctl">plain link</a> in prose.</p>' },
  { name: "an image map's area", sel: ".fx-body img", hit: "AREA", href: "https://example.invalid/area",
    html: `<p><img src="${PNG}" width="200" height="200" usemap="#user-content-m" alt="pic"><map name="user-content-m"><area href="https://example.invalid/area" shape="default" alt="a"></map></p>` },
  { name: "an SVG anchor spelled xlink:href", sel: ".fx-body svg text", hit: "text", href: "https://example.invalid/xlink",
    html: `<p><svg width="300" height="60" xmlns:xlink="${XLINK}"><a xlink:href="https://example.invalid/xlink"><text x="5" y="40" font-size="30">xlink text</text></a></svg></p>` },
  { name: "an SVG anchor with a plain href (contrast)", sel: ".fx-body svg text", hit: "text", href: "https://example.invalid/svghref",
    html: '<p><svg width="300" height="60"><a href="https://example.invalid/svghref"><text x="5" y="40" font-size="30">svg href text</text></a></svg></p>' },
];
// the same two hostile shapes as a message's own HTML, for the pipeline leg
const MESSAGES: { name: string; md: string; sel: string }[] = [
  { name: "an image map", sel: ".fx-body img",
    md: `<img src="${PNG}" width="200" height="200" usemap="#m" alt="pic"><map name="m"><area href="https://example.invalid/area" shape="default" alt="a"></map>\n\nafter` },
  { name: "an SVG xlink anchor", sel: ".fx-body svg text",
    md: `<svg width="300" height="60" xmlns:xlink="${XLINK}"><a xlink:href="https://example.invalid/xlink"><text x="5" y="40" font-size="30">xlink text</text></a></svg>\n\nafter` },
];

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
function bundle(entry: string): string {
  const r = requireCjs("esbuild").buildSync({ ...BUILD, entryPoints: [path.join(UI, entry)] });
  return r.outputFiles[0].text;
}
// md() as render.ts runs it, minus the PR-ref linkifier: marked with the chat's options and extensions, then sanitizeMd
function probeBundle(): string {
  const contents = [
    'import { marked } from "marked";',
    'import { sanitizeMd } from "./md-sanitize";',
    'import { chatMdExtensions } from "./chat-md";',
    "marked.setOptions({ gfm: true, breaks: false });",
    "marked.use(...chatMdExtensions);",
    "(window as any).__mdProbe = (s: string) => sanitizeMd(marked.parse(s) as string).innerHTML;",
  ].join("\n");
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, sourcefile: "md-probe.ts", loader: "ts" } });
  return r.outputFiles[0].text;
}
// the chat page as the web dashboard serves it: the shared skeleton, the chat's sheet, a fake acquireVsCodeApi (the
// kernel's shim's role), window.open recorded instead of opened, then the chat bundle and the probe
const CHAT_HTML = `<!DOCTYPE html><html lang=en><head><meta charset=utf-8><style>${STYLES}</style></head><body>
${chatBody(ATTACH_TITLE_WEB)}
<script>window.__opens=[];window.open=function(u,t,f){window.__opens.push([u,t,f]);return null;};
window.acquireVsCodeApi=function(){return{postMessage:function(){}}};</script>
<script src=/dist/render.js></script><script src=/dist/probe.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (page: any, errors: string[], navs: string[]) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [], navs: string[] = [];
  try {
    const renderJs = bundle("render.ts"), probeJs = probeBundle();
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("framenavigated", (f: any) => { if (f === page.mainFrame()) navs.push(f.url()); });
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      // the attacker's host answers, so a navigation that does happen commits and is seen
      if (u.hostname === "example.invalid") return route.fulfill({ status: 200, contentType: "text/html", body: "<title>elsewhere</title>elsewhere" });
      if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: CHAT_HTML });
      if (u.pathname === "/dist/render.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: renderJs });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: probeJs });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/chat");
    await body(page, errors, navs);
  } finally {
    await browser.close();
  }
}

// fill a message body the way render.ts does (body.innerHTML = md(text)), alone in the transcript
async function show(page: any, html: string, throughMd: boolean): Promise<string> {
  return page.evaluate(([h, viaMd]: [string, boolean]) => {
    document.querySelectorAll(".fx-turn").forEach((n) => n.remove());
    const content = document.getElementById("content") as HTMLElement;
    const turn = document.createElement("div"); turn.className = "turn turn-assistant fx-turn";
    const body = document.createElement("div"); body.className = "assistant md fx-body";
    body.innerHTML = viaMd ? (window as any).__mdProbe(h) : h;
    turn.appendChild(body); content.appendChild(turn);
    (window as any).__opens.length = 0;
    return body.innerHTML;
  }, [html, throughMd] as [string, boolean]);
}
// one real click at the element's centre; what elementFromPoint names there, and whether the document left
async function clickCentre(page: any, sel: string): Promise<{ hit: string | null; left: boolean; opens: unknown[] }> {
  const box = await page.locator(sel).first().boundingBox();
  if (!box) return { hit: null, left: false, opens: [] };
  const x = box.x + box.width / 2, y = box.y + box.height / 2;
  const hit = await page.evaluate(([px, py]: [number, number]) => { const e = document.elementFromPoint(px, py); return e ? e.tagName : null; }, [x, y] as [number, number]);
  await page.mouse.click(x, y);
  // a navigation the delegate failed to cancel commits asynchronously: give it a bounded moment to show
  const left = await page.waitForURL((u: URL) => u.hostname === "example.invalid", { timeout: 1200 }).then(() => true, () => false);
  const opens = left ? [] : await page.evaluate(() => (window as any).__opens);
  return { hit, left, opens };
}

test("the chat's link delegate: an image map's area and an SVG xlink:href anchor open like a plain link, and the chat document never leaves", { timeout: 90000 }, async (t) => {
  await inBrowser(t, async (page, errors, navs) => {
    // 1. the delegate's contract, shape by shape, over raw markup
    for (const s of SHAPES) {
      await show(page, s.html, false);
      const r = await clickCentre(page, s.sel);
      assert.equal(r.hit, s.hit, s.name + ": precondition, the click lands on the element (elementFromPoint)");
      assert.equal(r.left, false, s.name + ": the chat document did not navigate to the link");
      assert.deepEqual(r.opens, [[s.href, "_blank", "noopener,noreferrer"]], s.name + ": the delegate opened the link in the user's browser");
      assert.equal(page.url(), "http://romp.test/chat", s.name + ": the chat page is where it was");
    }
    // 2. the chat's own pipeline: a message carrying either shape, through marked and sanitizeMd as md() runs
    //    them; whatever the sanitizer lets through, a click never moves the document
    for (const m of MESSAGES) {
      const html = await show(page, m.md, true);
      const r = await clickCentre(page, m.sel);
      assert.equal(r.left, false, m.name + " in a message: the chat document did not navigate; sanitized as " + html);
      for (const o of r.opens as string[][]) assert.match(o[0], /^https:\/\/example\.invalid\//, m.name + ": what did open was the link itself");
      assert.equal(page.url(), "http://romp.test/chat", m.name + " in a message: the chat page is where it was");
    }
    assert.deepEqual(navs.filter((u) => !u.startsWith("http://romp.test/")), [], "the main frame never navigated off the dashboard");
    assert.deepEqual(errors, [], "no page errors");
  });
});
