// A note's math in the file viewer, in the two bundles that host the viewer, over the REAL bundles in headless Chromium
// (plans/markdown-viewer.md, Slice 1, review round 1). The viewer's mdBlock parses with the shared marked singleton, and
// in the chat bundle render.ts arms that singleton with the chat grammar (chat-md.ts: math placeholders KaTeX fills after
// the sanitize). Round 1's first cut ran the fill by hand in md() and userMd() only, so a note opened from the chat page
// (a same-origin .md link, openUrlView) showed bare TeX in inert placeholders where main rendered KaTeX. The fill is a
// sanitizeMd post-pass now, registered by the grammar's module (md-sanitize.ts registerMdPostPass), so every sanitizeMd
// call in the chat bundle renders math, mdBlock's included. The files bundle has no grammar, no fill and no KaTeX: the
// same note keeps its `$\frac{a}{b}$` as literal text there, exactly as on main (Slice 4 gives it the grammar, decision
// 1). Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only:
// an invented note, TESTHOST paths, a placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { chatBody, ATTACH_TITLE_WEB } from "../../vscode-extension/src/page-skeleton";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
// the built styles.css carries katex.min.css inlined where the source @imports it (esbuild.js); the pages here do the same
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");
assert.ok(STYLES.includes(".katex-html"), "the KaTeX sheet is inlined in the test pages as it is in the built sheet");

const SID = "11111111-2222-3333-4444-555555555555";
const FILE_PATH = "/tmp/TESTHOST/notes-api/report.md";
const NOTE = "# Note\n\nInline $\\frac{a}{b}$ and root $\\sqrt{x+1}$ in prose.\n\n$$\\sum_{i=0}^{n} i$$\n\nAfter.\n";

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
function bundle(entry: string): string {
  const r = requireCjs("esbuild").buildSync({ ...BUILD, entryPoints: [path.join(UI, entry)] });
  return r.outputFiles[0].text;
}
// the chat page as the web dashboard serves it, and the Files page as the kernel serves it (_files_page)
const CHAT_HTML = (styles: string) => `<!DOCTYPE html><html lang=en><head><meta charset=utf-8><style>${styles}</style></head><body>
${chatBody(ATTACH_TITLE_WEB)}
<script>window.__opens=[];window.open=function(u,t,f){window.__opens.push([u,t,f]);return null;};
window.acquireVsCodeApi=function(){return{postMessage:function(){}}};</script>
<script src=/dist/render.js></script></body></html>`;
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane>
<div id=files-empty></div>
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};</script>
<script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Facts = {
  katex: number; display: number; placeholders: number; styledInKatex: number; text: string; firstP: string;
  aTop: number | null; bTop: number | null; displayH: number | null;
};
// what the rendered note holds: KaTeX roots, placeholders, inline styles under .katex, the text, and the fraction's
// numerator and denominator tops (the layout the colour-only style rule would have flattened)
function measure(): Facts {
  const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
  const leaf = (t: string): HTMLElement | null => Array.from(md.querySelectorAll(".katex .mord")).find((e) => !e.querySelector(".mord") && (e.textContent || "").trim() === t) as HTMLElement | null;
  const a = leaf("a"), b = leaf("b");
  const disp = md.querySelector(".katex-display");
  return {
    katex: md.querySelectorAll(".katex").length,
    display: md.querySelectorAll(".katex-display").length,
    placeholders: md.querySelectorAll(".md-math-inline, .md-math-display").length,
    styledInKatex: md.querySelectorAll(".katex [style]").length,
    text: (md.textContent || "").replace(/\s+/g, " ").trim(),
    firstP: (md.querySelector("p") as HTMLElement | null)?.innerHTML || "",
    aTop: a ? a.getBoundingClientRect().top : null,
    bTop: b ? b.getBoundingClientRect().top : null,
    displayH: disp ? disp.getBoundingClientRect().height : null,
  };
}

async function inBrowser(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

test("a note's math renders as KaTeX in the chat page's viewer (the render bundle) and stays literal TeX in the Files pane (the files bundle), as on main", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const renderJs = bundle("render.ts"), filesJs = bundle("files.ts");
    // the files bundle carries neither the grammar's placeholder class nor KaTeX: what the viewer does there cannot be math
    assert.ok(!filesJs.includes("md-math-inline") && !filesJs.includes("KaTeX parse error"), "files.js is free of the math grammar and of KaTeX (Slice 4 adds both, decision 1)");
    assert.ok(renderJs.includes("md-math-inline") && renderJs.includes("KaTeX parse error"), "render.js carries both");

    // 1. the chat page: a same-origin .md link in a message opens the note in the viewer (openUrlView), and its formulas are KaTeX
    {
      const page = await browser.newPage({ viewport: { width: 1000, height: 800 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      await page.route("**/*", (route: any) => {
        const u = new URL(route.request().url());
        if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
        if (u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: CHAT_HTML(STYLES) });
        if (u.pathname === "/dist/render.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: renderJs });
        if (u.pathname === "/docs/note.md") return route.fulfill({ status: 200, contentType: "text/markdown; charset=utf-8", body: NOTE });
        return route.fulfill({ status: 404, body: "" });
      });
      await page.goto("http://romp.test/chat");
      await page.evaluate(() => {
        const content = document.getElementById("content") as HTMLElement;
        const turn = document.createElement("div"); turn.className = "turn turn-assistant fx-turn";
        const body = document.createElement("div"); body.className = "assistant md fx-body";
        body.innerHTML = '<p>See <a href="http://romp.test/docs/note.md">the note</a>.</p>';
        turn.appendChild(body); content.appendChild(turn);
      });
      await page.click(".fx-body a");
      await page.waitForSelector("#romp-fileview .fileview-md", { timeout: 15000 });
      const f: Facts = await page.evaluate(measure);
      assert.equal(f.placeholders, 0, "no placeholder is left in the viewed note: " + f.firstP);
      assert.equal(f.katex, 3, "three formulas rendered as KaTeX: " + f.firstP);
      assert.equal(f.display, 1, "the display sum is a .katex-display block");
      assert.ok(f.styledInKatex >= 10, "KaTeX's inline layout styles are all there (they never met the colour-only rule): " + f.styledInKatex);
      assert.ok(!f.text.includes("\\frac") && !f.text.includes("$"), "no TeX source and no delimiter reads as text: " + f.text);
      assert.ok(f.aTop !== null && f.bTop !== null && f.aTop < f.bTop - 4, "the fraction's numerator sits above its denominator: a@" + f.aTop + " b@" + f.bTop);
      assert.ok(f.displayH !== null && f.displayH > 30, "the display sum has its limits' height: " + f.displayH);
      assert.deepEqual(errors, [], "no page errors on the chat page");
      await page.close();
    }

    // 2. the Files pane: the same note through the files bundle keeps its TeX as the literal text it was on main
    {
      const page = await browser.newPage({ viewport: { width: 1000, height: 800 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      await page.route("http://romp.test/**", (route: any) => {
        const u = new URL(route.request().url());
        if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FILES_HTML });
        if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: filesJs });
        if (u.pathname === "/file" && u.searchParams.get("path") === FILE_PATH) {
          return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: NOTE });
        }
        return route.fulfill({ status: 404, body: "" });
      });
      await page.goto("http://romp.test/files");
      await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [FILE_PATH, SID] as [string, string]);
      await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 10000 });
      const f: Facts = await page.evaluate(measure);
      assert.equal(f.katex, 0, "no KaTeX in the Files pane's viewer");
      assert.equal(f.placeholders, 0, "and no placeholder element either: the files bundle has no math grammar");
      assert.ok(f.text.includes("Inline $\\frac{a}{b}$ and root $\\sqrt{x+1}$ in prose.") && f.text.includes("$$\\sum_{i=0}^{n} i$$"), "the TeX is literal text, delimiters included, as on main: " + f.text);
      assert.deepEqual(errors, [], "no page errors on the Files page");
      await page.close();
    }
  });
});
