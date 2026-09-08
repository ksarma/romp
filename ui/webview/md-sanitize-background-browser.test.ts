// The HTML `background` attribute through the REAL shared sanitizer in headless Chromium (plans/markdown-viewer.md,
// Slice 1, review finding 2026-09-07). DOMPurify's html attribute list keeps `background` (and `bgcolor`), and
// `<td background=URL>` or `<table background=URL>` makes Chromium fetch the URL as a background image the moment
// the note renders: a tracking pixel with no click and no gate, on the chat and in the viewer alike, and outside
// every path decision 8's figure gate (rewriteFigureSrcs, `img[src]`) will ever see. GitHub's own allowlist has no
// `background`, so MD_PURIFY forbids it outright (FORBID_ATTR; `usemap`, the image map's binding, is the other); `bgcolor`
// fetches nothing and stays, the way a colour-only inline style does (decision 6). The leg adopts sanitizeMd's
// output into a live page and reads the page's own request events: a remote `<img src>` in the same fixture is the
// positive control (it still loads on open today; the plan's Low, Slice 4's gate), so the recorder is proven live
// by the request the attribute must not add. Skips LOUDLY without a playwright browser (CI installs none), as the
// other browser legs do. Synthetic values only: example.invalid URLs.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";
import { MD_FORBID_ATTR, MD_PURIFY } from "./md-sanitize";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");

const TD_BG = "https://example.invalid/td.gif";
const TABLE_BG = "https://example.invalid/table.gif";
const CONTROL_IMG = "https://example.invalid/control.gif";
const FIXTURE = [
  `<table class="fx-table" background="${TABLE_BG}"><tr><td class="fx-td" background="${TD_BG}" bgcolor="#f00">c</td></tr></table>`,
  `<p><img class="fx-ctl" src="${CONTROL_IMG}" alt="control"></p>`,
].join("\n");

// ── the profile (node) ──────────────────────────────────────────────────────────────────────────────

test("the profile forbids the `background` attribute outright (and `usemap`, the image map's binding), and nothing else", () => {
  assert.deepEqual([...MD_FORBID_ATTR], ["background", "usemap"], "id and name are prefixed, style is filtered by the hook; background is the attribute with no safe value, usemap binds a map the sanitizer drops (md-sanitize-viewer-links-browser.test.ts)");
  assert.deepEqual(MD_PURIFY.FORBID_ATTR, [...MD_FORBID_ATTR]);
  assert.ok(!MD_FORBID_ATTR.includes("bgcolor"), "bgcolor fetches nothing: a colour survives, as it does in an inline style");
});

// ── the browser leg ─────────────────────────────────────────────────────────────────────────────────

/** The real md-sanitize.ts bundled for a page, exposing sanitizeMd's serialized output and its live nodes. */
function bundleProbe(): string {
  const esbuild = requireCjs("esbuild");
  const contents = [
    'import { sanitizeMd } from "./md-sanitize";',
    "(window as any).__probe = {",
    "  html: (dirty: string) => sanitizeMd(dirty).innerHTML,",
    "  adopt: (dirty: string, into: HTMLElement) => { into.replaceChildren(...Array.from(sanitizeMd(dirty).childNodes)); },",
    "};",
  ].join("\n");
  const r = esbuild.buildSync({
    stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "md-sanitize-background-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}

const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8></head><body><div id=note></div><script src=/probe.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

test("`<td background=URL>` and `<table background=URL>` lose the attribute and fetch nothing on render; bgcolor and a remote img are untouched", { timeout: 60000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  const foreign: string[] = [];
  try {
    const probeJs = bundleProbe();
    const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("request", (r: any) => { const u = new URL(r.url()); if (u.protocol !== "data:" && u.host !== "romp.test") foreign.push(r.url()); });
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.host !== "romp.test") return route.fulfill({ status: 404, body: "" });   // recorded above; never served
      if (u.pathname === "/") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: probeJs });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/");

    // 1. the serialized verdict: background gone on both elements, bgcolor kept, the img and its src kept
    const html: string = await page.evaluate((dirty: string) => (window as any).__probe.html(dirty), FIXTURE);
    assert.doesNotMatch(html, /background=/, "no background attribute survives: " + html);
    assert.match(html, /<td class="fx-td" bgcolor="#f00">c<\/td>/, "the cell keeps its bgcolor and its text");
    assert.match(html, /<table class="fx-table">/, "the table keeps its class and loses only the attribute");
    assert.ok(html.includes(`<img class="fx-ctl" src="${CONTROL_IMG}" alt="control">`), "the remote image is not this rule's business (decision 8, Slice 4)");

    // 2. adopted into the live page: the cell paints its bgcolor and no background image, and the only request that
    //    left the page's host is the control image's (the recorder is live; the attribute added none)
    const facts = await page.evaluate(async (dirty: string) => {
      const note = document.getElementById("note") as HTMLElement;
      (window as any).__probe.adopt(dirty, note);
      const td = note.querySelector(".fx-td") as HTMLElement, table = note.querySelector(".fx-table") as HTMLElement;
      const img = note.querySelector(".fx-ctl") as HTMLImageElement;
      td.getBoundingClientRect();                                  // force style and layout: a background image would be requested here
      // the control image settles (load or error) before the leg reads the request log, so the wait is event-based
      await new Promise<void>((done) => { if (img.complete) done(); else { img.onload = () => done(); img.onerror = () => done(); } });
      return {
        tdBackgroundAttr: td.getAttribute("background"), tableBackgroundAttr: table.getAttribute("background"),
        tdBgImage: getComputedStyle(td).backgroundImage, tableBgImage: getComputedStyle(table).backgroundImage,
        tdBgColor: getComputedStyle(td).backgroundColor, withBackground: note.querySelectorAll("[background]").length,
      };
    }, FIXTURE);
    assert.equal(facts.tdBackgroundAttr, null);
    assert.equal(facts.tableBackgroundAttr, null);
    assert.equal(facts.withBackground, 0);
    assert.equal(facts.tdBgImage, "none", "no background image on the cell");
    assert.equal(facts.tableBgImage, "none", "no background image on the table");
    assert.equal(facts.tdBgColor, "rgb(255, 0, 0)", "bgcolor still paints");
    assert.ok(foreign.includes(CONTROL_IMG), "the control: a remote <img src> did request its URL, so the recorder sees requests that leave the page: " + JSON.stringify(foreign));
    assert.ok(!foreign.includes(TD_BG) && !foreign.includes(TABLE_BG), "neither background URL was requested: " + JSON.stringify(foreign));
    assert.deepEqual(foreign.filter((u) => u !== CONTROL_IMG), [], "the control image's is the only request that left romp.test");
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    await browser.close();
  }
});
