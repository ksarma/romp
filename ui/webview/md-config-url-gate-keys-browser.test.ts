// Decision 8's placeholder in the URL viewer, from the keyboard, over the REAL Files bundle in headless Chromium
// (figure-gate.ts; plans/markdown-viewer.md, the Slice 4 build note's item 9: the click is delegated on the body of both
// viewers, and "Enter and Space on a focused placeholder do the same"). The placeholder is a span with role=button and
// tabindex=0, so the browser synthesizes no click for its keys: the viewer has to read them. openFileView did, on its
// body; openUrlView wired the placeholder through `delegate(body, ...)`, which listens to clicks alone, so in a URL
// document a keyboard user reached a control that ignored Enter and Space (the round-1 review; the file kind's leg
// pressed Enter, the URL kind's clicked). Both viewers install the same key listener now (file-view.ts gateKeys). The
// leg opens a URL document holding two figures on two unlisted hosts, focuses one placeholder and presses Enter, the
// other and presses Space, and reads the page's own request events: nothing leaves the page until the key, and the
// figure loads on it. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do.
// Synthetic values only: an invented note, .test hosts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");

const URL_DOC = "http://romp.test/notes/note.md";
const URL_NOTE = '# Note\n\n<p><img class="fx-enter" src="https://remote-a.test/x.png" alt="a" width="120" height="80"></p>\n\n<p><img class="fx-space" src="https://remote-b.test/y.png" alt="b" width="120" height="80"></p>\n\nend.\n';
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "base64");

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files pane's bundle plus the URL viewer, which the pane's page does not otherwise reach. */
function filesBundle(): string {
  const contents = 'import "./files";\nimport { openUrlView } from "./file-view";\n(window as any).__rompProbe = { openUrlView };\n';
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" } });
  return r.outputFiles[0].text;
}
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane>
<div id=files-empty></div>
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};</script>
<script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

test("URL viewer: Enter on a focused placeholder loads its figure, Space loads another; nothing left the page before the key", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const js = filesBundle();
    const ctx = await browser.newContext({ viewport: { width: 900, height: 600 } });
    const page = await ctx.newPage();
    const errors: string[] = [];
    const requests: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("request", (r: any) => { requests.push(r.url()); });
    await ctx.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.host !== "romp.test") return route.fulfill({ status: 200, contentType: "image/png", body: PNG });   // any other host: a picture, and the log has it
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FILES_HTML });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (route.request().url() === URL_DOC) return route.fulfill({ status: 200, contentType: "text/markdown; charset=utf-8", body: URL_NOTE });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/files");
    await page.evaluate((u: string) => { (window as any).__rompProbe.openUrlView(u); }, URL_DOC);
    await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 15000 });
    await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
    const foreign = () => requests.filter((u) => !u.startsWith("http://romp.test/"));
    const gates = () => page.evaluate(() => Array.from(document.querySelectorAll("#romp-fileview .fileview-md .fv-gate")).map((g) => [g.getAttribute("data-fv-host"), g.getAttribute("role"), g.getAttribute("tabindex"), g.getAttribute("data-act")]));
    assert.deepEqual(await gates(), [["remote-a.test", "button", "0", "fv-load"], ["remote-b.test", "button", "0", "fv-load"]], "both figures are gated on open, each a focusable button");
    assert.deepEqual(foreign(), [], "nothing left the page on open");

    // Enter on the first placeholder: the figure loads (the request is the proof), the placeholder is gone, the other stands
    await page.focus('#romp-fileview .fileview-md .fv-gate[data-fv-host="remote-a.test"]');
    assert.equal(await page.evaluate(() => (document.activeElement as HTMLElement).getAttribute("data-fv-host")), "remote-a.test", "the placeholder took focus");
    const enterLoad = page.waitForRequest("https://remote-a.test/x.png", { timeout: 15000 });
    await page.keyboard.press("Enter");
    await enterLoad;
    await page.waitForFunction(() => document.querySelectorAll("#romp-fileview .fileview-md .fv-gate").length === 1, undefined, { timeout: 15000 });
    assert.deepEqual(await gates(), [["remote-b.test", "button", "0", "fv-load"]], "Enter restored the remote-a.test figure and left remote-b.test's placeholder");
    assert.equal(await page.evaluate(() => (document.querySelector("#romp-fileview .fileview-md img.fx-enter") as HTMLElement).getAttribute("src")), "https://remote-a.test/x.png", "the src is back under its name");
    assert.deepEqual(foreign(), ["https://remote-a.test/x.png"], "one request, for the figure the key loaded");

    // Space on the second
    await page.focus('#romp-fileview .fileview-md .fv-gate[data-fv-host="remote-b.test"]');
    const spaceLoad = page.waitForRequest("https://remote-b.test/y.png", { timeout: 15000 });
    await page.keyboard.press(" ");
    await spaceLoad;
    await page.waitForFunction(() => document.querySelectorAll("#romp-fileview .fileview-md .fv-gate").length === 0, undefined, { timeout: 15000 });
    assert.equal(await page.evaluate(() => (document.querySelector("#romp-fileview .fileview-md img.fx-space") as HTMLElement).getAttribute("src")), "https://remote-b.test/y.png");
    assert.deepEqual(foreign(), ["https://remote-a.test/x.png", "https://remote-b.test/y.png"], "Space loaded the second, and nothing else was fetched");
    assert.equal(await page.evaluate(() => document.querySelector("#romp-fileview") !== null), true, "the viewer is still open (Space did not scroll the page away or close anything)");
    assert.deepEqual(errors, [], "no page errors");
    await ctx.close();
  });
});
