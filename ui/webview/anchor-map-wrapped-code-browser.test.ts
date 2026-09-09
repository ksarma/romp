// The anchor map over a fence the viewer has WRAPPED into rows, in headless Chromium over the REAL files bundle (Slice 3
// of plans/markdown-viewer.md). mdBlock (file-view.ts) cuts every fence into per-line rows (code-block.ts) and the wrap
// drops the newlines, so before this slice's anchor-map change paintRendered's fallback matched a quote holding a newline
// ("comment\ndef") against a hay reading "commentdef" and painted NOTHING for a comment spanning two code lines (the gap
// analysis measured 0 marks where the unwrapped block painted 13). The fallback now reads the block's text through
// codeRuns, the newline put back between rows. Measured here: a range over two code lines paints marks inside both rows;
// a one-line range still paints; a change mark (paintChangesRendered, an insertion) across two lines paints; a Rendered
// selection inside the code is still refused with the Raw offer (Slice 8 maps it); the plain fence (no language) has
// rows and paints too. The fixture is anchor-map-fixtures/fenced.md, synthetic. Skips loudly without a browser.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const NOTE = fs.readFileSync(path.join(UI, "anchor-map-fixtures", "fenced.md"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', "");
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");
const SID = "11111111-2222-3333-4444-555555555555";
const PATH = "/tmp/TESTHOST/notes-api/fenced.md";
const ORIGIN = "http://romp.test";

function bundle(o: Record<string, unknown>): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({ ...o, bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" });
  return r.outputFiles[0].text;
}
const HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane><div id=files-empty></div><script>window.acquireVsCodeApi=function(){return{postMessage:function(){}}};</script><script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

test("a comment across two wrapped code lines paints in both rows; one line still paints; a change across lines paints; the selection is still refused with the Raw offer", { timeout: 90000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const filesJs = bundle({ entryPoints: [path.join(UI, "files.ts")] });
    const amJs = bundle({ stdin: { contents: 'import { mapRenderedSelection, paintRendered, paintChangesRendered, codeText } from "./anchor-map"; (window as any).AM = { mapRenderedSelection, paintRendered, paintChangesRendered, codeText };', resolveDir: UI, loader: "ts", sourcefile: "am-probe.ts" } });
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route(ORIGIN + "/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html", body: HTML });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: filesJs });
      if (u.pathname === "/file") return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: NOTE });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto(ORIGIN + "/files");
    await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [PATH, SID] as [string, string]);
    await page.waitForSelector("#romp-fileview .fileview-md > pre", { timeout: 15000 });
    await page.addScriptTag({ content: amJs });

    // 1. the shape mdBlock built: both fences wrapped, the python one highlighted, the plain one not; no newline in the text
    const shape = await page.evaluate(() => {
      const pres = Array.from(document.querySelectorAll(".fileview-md > pre")) as HTMLElement[];
      return pres.map((pre) => { const code = pre.querySelector("code")!; return { cls: code.className, rows: code.querySelectorAll(":scope > .cl").length, nl: (code.textContent || "").indexOf("\n"), copy: !!pre.querySelector(":scope > .code-copy"), text: (window as any).AM.codeText(code) }; });
    });
    assert.equal(shape.length, 2);
    assert.equal(shape[0].cls, "language-python hljs"); assert.equal(shape[0].rows, 5, "five rows for five lines"); assert.equal(shape[0].nl, -1, "the wrap dropped the newlines"); assert.ok(shape[0].copy);
    assert.equal(shape[0].text, "# a comment\ndef f(x):\n    return x + 1  # trailing\n\nvalue = f(2)", "codeText reads the lines back");
    assert.equal(shape[1].cls, "", "the plain fence: no language class, and no hljs class (an unnamed fence is never guessed)");
    assert.equal(shape[1].rows, 2, "...but wrapped like any other"); assert.ok(shape[1].copy, "...and given Copy");

    // 2. paintRendered over a range spanning two code lines: marks inside BOTH rows (0 before this slice)
    const two = await page.evaluate((src: string) => {
      const root = document.querySelector(".fileview-md")!;
      const pre = root.querySelector("pre")!;
      const start = src.indexOf("# a comment"), end = src.indexOf("def f(x):") + "def f(x):".length;
      const marks = (window as any).AM.paintRendered(root, src, { start, end }, "fc-hl", { act: "fcopen", id: "c1" });
      const all = Array.from(root.querySelectorAll(".fc-hl")) as HTMLElement[];
      const rows = Array.from(pre.querySelectorAll(".cl")) as HTMLElement[];
      const rowOf = (m: HTMLElement) => rows.findIndex((r) => r.contains(m));
      return { returned: marks ? marks.length : null, marks: all.length, rows: Array.from(new Set(all.map(rowOf))).sort(), text: all.map((m) => m.textContent).join("|") };
    }, NOTE);
    assert.ok(two.returned && two.returned > 0, "paintRendered returns marks for a two-line range (was null after the wrap)");
    assert.deepEqual(two.rows, [0, 1], "the marks lie in the first two rows");
    assert.match(two.text, /a comment/); assert.match(two.text, /def/);
    // 3. a one-line range still paints
    const one = await page.evaluate((src: string) => {
      const root = document.querySelector(".fileview-md")!;
      const start = src.indexOf("return x + 1"), end = start + "return x + 1".length;
      const marks = (window as any).AM.paintRendered(root, src, { start, end }, "fc-hl2");
      return { returned: marks ? marks.length : null, text: Array.from(root.querySelectorAll(".fc-hl2")).map((m) => m.textContent).join("") };
    }, NOTE);
    assert.ok(one.returned && one.returned > 0); assert.equal(one.text.replace(/\s+/g, " "), "return x + 1");
    // 4. a range over the whole fence, fence lines included: painted across all five rows
    const whole = await page.evaluate((src: string) => {
      const root = document.querySelector(".fileview-md")!; const pre = root.querySelector("pre")!;
      const start = src.indexOf("```python"), end = src.indexOf("```\n\nAfter") + 3;
      const marks = (window as any).AM.paintRendered(root, src, { start, end }, "fc-hl3");
      const rows = Array.from(pre.querySelectorAll(".cl")) as HTMLElement[];
      const all = Array.from(root.querySelectorAll(".fc-hl3")) as HTMLElement[];
      return { returned: marks ? marks.length : null, rowsHit: rows.filter((r) => r.querySelector(".fc-hl3")).length, outsidePre: all.filter((m) => !pre.contains(m)).length };
    }, NOTE);
    assert.ok(whole.returned && whole.returned > 0, "the whole block paints");
    assert.equal(whole.rowsHit, 4, "every row with text carries a mark (the empty row has no text node)"); assert.equal(whole.outsidePre, 0);
    // 5. the plain fence: a two-line range paints across its rows too
    const plain = await page.evaluate((src: string) => {
      const root = document.querySelector(".fileview-md")!; const pre = root.querySelectorAll("pre")[1]!;
      const start = src.indexOf("no language"), end = src.indexOf("second line") + "second line".length;
      const marks = (window as any).AM.paintRendered(root, src, { start, end }, "fc-hl4");
      const rows = Array.from(pre.querySelectorAll(".cl")) as HTMLElement[];
      return { returned: marks ? marks.length : null, rowsHit: rows.filter((r) => r.querySelector(".fc-hl4")).length };
    }, NOTE);
    assert.ok(plain.returned && plain.returned > 0); assert.equal(plain.rowsHit, 2);
    // 6. a change mark across two lines (paintChangesRendered: an insertion whose text spans the newline)
    const change = await page.evaluate((src: string) => {
      const root = document.querySelector(".fileview-md")!; const pre = root.querySelector("pre")!;
      const from = src.indexOf("return x + 1"), to = src.indexOf("value = f(2)") + "value".length;
      const out = (window as any).AM.paintChangesRendered(root, src, [{ id: "ch1", kind: "ins", curFrom: from, curTo: to, oldText: "", author: "web" }], () => ({}));
      const rows = Array.from(pre.querySelectorAll(".cl")) as HTMLElement[];
      const ins = Array.from(root.querySelectorAll(".fc-ins")) as HTMLElement[];
      return { out: JSON.stringify(out).slice(0, 200), ins: ins.length, rowsHit: rows.filter((r) => r.querySelector(".fc-ins")).length };
    }, NOTE);
    assert.ok(change.ins > 0, "the insertion painted: " + change.out);
    assert.ok(change.rowsHit >= 2, "...across at least two rows (" + change.rowsHit + ")");
    // 7. mapping a selection inside the code is still refused, the Raw view offered (Slice 8's work, untouched here)
    const refused = await page.evaluate((src: string) => {
      const root = document.querySelector(".fileview-md")!; const code = root.querySelector("pre code")!;
      const walker = document.createTreeWalker(code, NodeFilter.SHOW_TEXT); let tn: Text | null = null;
      for (let n = walker.nextNode() as Text | null; n; n = walker.nextNode() as Text | null) { if (n.data.indexOf("def") >= 0) { tn = n; break; } }
      const sel = { anchorNode: tn, anchorOffset: 0, focusNode: tn, focusOffset: 3, isCollapsed: false };
      return (window as any).AM.mapRenderedSelection(sel, root, src);
    }, NOTE);
    assert.equal(refused.ok, false, "code refuses from Rendered");
    assert.equal(refused.rawHasQuote, true, "...with the Raw view offered");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  } finally { await browser.close(); }
});
