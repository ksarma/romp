// A fold's open or closed state survives every paint of the rendered view, over the REAL Files bundle in headless
// Chromium (file-view.ts renderBody, both viewers; plans/markdown-viewer.md Slice 4, the front matter and the callout
// folds; ui/CLAUDE.md: an expand's state survives re-renders). Every text paint rebuilds the body from marked
// (`body.replaceChildren(mdBlock(...))`), and a <details> fold's only state is the DOM, so before this every fold went
// back to what the source says (`[!type]+` open, everything else closed) on the Rendered/Raw switch, on a reload's
// landing, on the editor taking and handing back the body: a fold the person had opened to read shut again, one they
// had closed opened again, and the block under the eye changed height under the reader's place (the Slice 4 review,
// round 1: 72px open to 39px closed on the folded tip; a fold a `#` click had just opened shut again on the next paint).
// renderBody records every fold's state before the swap (foldKeeper in file-view.ts) and re-applies it after, so the
// non-paint paths (a text-size step) and the paint paths agree. The leg drives the real gestures: clicks on the
// summaries, the Raw and Rendered buttons, Edit and Cancel with a stub editor chunk (the editor's take and handback are
// two paints of their own), a `#` click into a shut callout followed by a switch; then the URL viewer's own switch.
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only: an
// invented note, TESTHOST paths, a placeholder sid.
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

const SID = "11111111-2222-3333-4444-555555555555";
const DIR = "/tmp/TESTHOST/notes-api/docs/";
const FILE_PATH = DIR + "folds.md";
const URL_DOC = "http://romp.test/notes/folds.md";
// the front matter (closed as authored), a callout folded shut, one folded open, and one folded shut around a heading a link names
const NOTE = [
  "---", "title: Probe Note", "tags: [x]", "---", "",
  "Para one.", "",
  "> [!tip]- Folded tip", "> Hidden tip body.", "",
  "> [!important]+ Open important", "> Shown important body.", "",
  "> [!note]- Folded with heading", ">", "> ## Inner heading", ">", "> Inner body text.", "",
  "Link: [inner](#inner-heading).", "",
  "Last para.", "",
].join("\n");
const AUTHORED = [["md-frontmatter", false], ["md-callout md-callout-tip", false], ["md-callout md-callout-important", true], ["md-callout md-callout-note", false]];
const CHOSEN = [["md-frontmatter", true], ["md-callout md-callout-tip", true], ["md-callout md-callout-important", false], ["md-callout md-callout-note", false]];

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files pane's bundle plus the URL viewer, which the pane's page does not otherwise reach. */
function filesBundle(): string {
  const contents = 'import "./files";\nimport { openUrlView } from "./file-view";\n(window as any).__rompProbe = { openUrlView };\n';
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" } });
  return r.outputFiles[0].text;
}
// a stub editor chunk registered up front (file-view.ts editorChunk takes window.__rompEditor when it stands): a textarea
// that answers value(), so Edit takes the body and Cancel hands it back without the real CodeMirror chunk's script
const EDITOR_STUB = "window.__rompEditor={mount:function(host,o){var ta=document.createElement('textarea');ta.value=o.text;host.appendChild(ta);"
  + "return{value:function(){return ta.value;},destroy:function(){},focus:function(){}};}};";
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane>
<div id=files-empty></div>
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};${EDITOR_STUB}</script>
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

type Opened = { page: any; errors: string[] };
/** A page of the Files pane with the bundle and the note served from memory: the note as a file document through the pane's
 *  relay, or as a URL document through openUrlView. */
async function openNote(browser: any, js: string, how: "file" | "url"): Promise<Opened> {
  const ctx = await browser.newContext({ viewport: { width: 1200, height: 520 } });
  const page = await ctx.newPage();
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await ctx.route("**/*", (route: any) => {
    const u = new URL(route.request().url());
    if (u.host !== "romp.test") return route.fulfill({ status: 404, body: "" });
    if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FILES_HTML });
    if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
    if (u.pathname === "/version") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ fileEditing: true }) });   // Edit's consent read (ensureEditingAllowed): editing is on, no dialog
    if (u.pathname === "/file" && u.searchParams.get("path") === FILE_PATH) {
      return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: NOTE });
    }
    if (route.request().url() === URL_DOC) return route.fulfill({ status: 200, contentType: "text/markdown; charset=utf-8", body: NOTE });
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/files");
  if (how === "file") await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [FILE_PATH, SID] as [string, string]);
  else await page.evaluate((u: string) => { (window as any).__rompProbe.openUrlView(u); }, URL_DOC);
  await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 15000 });
  await settle(page);
  return { page, errors };
}
const settle = (page: any) => page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
/** Every fold under the rendered box: its class and whether it stands open. */
const folds = (page: any): Promise<Array<[string, boolean]>> => page.evaluate(() =>
  Array.from(document.querySelectorAll("#romp-fileview .fileview-md details")).map((d) => [d.className, d.hasAttribute("open")]));
/** The folds' laid-out heights, rounded: the block under the reader's eye keeps its height across a paint only if its fold does. */
const heights = (page: any): Promise<number[]> => page.evaluate(() =>
  Array.from(document.querySelectorAll("#romp-fileview .fileview-md details")).map((d) => Math.round(d.getBoundingClientRect().height)));
/** The rendered box's identity, so a test can tell a paint (a new box) from no paint. */
const boxId = (page: any): Promise<number> => page.evaluate(() => {
  const md = document.querySelector("#romp-fileview .fileview-md") as any;
  if (!md) return -1;
  if (!md.__probeId) md.__probeId = ((window as any).__probeSeq = ((window as any).__probeSeq || 0) + 1);
  return md.__probeId as number;
});
const bar = (page: any, label: string) => page.locator("#romp-fileview .fileview-bar button", { hasText: new RegExp("^" + label + "$") });
/** The person's choice: the front matter and the shut tip opened, the open important closed. */
async function choose(page: any): Promise<void> {
  await page.click("#romp-fileview .fileview-md details.md-frontmatter > summary");
  await page.click("#romp-fileview .fileview-md details.md-callout-tip > summary");
  await page.click("#romp-fileview .fileview-md details.md-callout-important > summary");
  await settle(page);
}
/** Raw, then Rendered: two paints of the body. Returns whether the Raw view showed no rendered box and the Rendered one is a new box. */
async function switchViews(page: any): Promise<{ rawHadMd: boolean; newBox: boolean }> {
  const before = await boxId(page);
  await bar(page, "Raw").click();
  await settle(page);
  const rawHadMd = (await boxId(page)) !== -1;
  await bar(page, "Rendered").click();
  await settle(page);
  return { rawHadMd, newBox: (await boxId(page)) !== before };
}

test("Files pane: the folds the person opened or closed stand as chosen across the Rendered/Raw switch, the editor's take and handback, and a `#` reveal into a shut callout followed by a switch; the folds' heights are the same after the paint", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openNote(browser, filesBundle(), "file");
    assert.deepEqual(await folds(page), AUTHORED, "the first paint shows the folds as authored: front matter shut, `-` shut, `+` open");
    await choose(page);
    assert.deepEqual(await folds(page), CHOSEN, "the clicks took");
    const chosenHeights = await heights(page);

    // the Rendered/Raw round trip: a fresh box, the folds as chosen, the same heights (the reader's place seats over the same blocks)
    const sw = await switchViews(page);
    assert.deepEqual([sw.rawHadMd, sw.newBox], [false, true], "Raw showed no rendered box and Rendered painted a new one (the paint happened)");
    assert.deepEqual(await folds(page), CHOSEN, "after Raw and Rendered every fold stands as the person left it, not as authored");
    assert.deepEqual(await heights(page), chosenHeights, "the folds are laid out at the heights they had before the paint");

    // the editor takes the body (Edit; the Rendered view is left for Raw) and hands it back (Cancel, nothing changed), then Rendered again
    await bar(page, "Edit").click();
    await page.waitForSelector("#romp-fileview .fileview-cm textarea", { timeout: 15000 });
    await bar(page, "Cancel").click();
    await settle(page);
    assert.equal(await boxId(page), -1, "after Cancel the Raw view stands (Edit chose it)");
    await bar(page, "Rendered").click();
    await settle(page);
    assert.deepEqual(await folds(page), CHOSEN, "the folds chosen before Edit stand after the editor handed the body back");

    // a `#` click into the shut note callout reveals it (md-sanitize.ts revealFragmentTarget); the next paint keeps it revealed
    await page.locator("#romp-fileview .fileview-md a", { hasText: /^inner$/ }).click();
    await settle(page);
    const revealed = await page.evaluate(() => {
      const d = document.querySelector("#romp-fileview .fileview-md details.md-callout-note")!;
      const b = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect();
      const h = document.querySelector("#romp-fileview .fileview-md #md-inner-heading")!.getBoundingClientRect();   // the viewer's heading ids wear the md- prefix (mintHeadingIds)
      return { open: d.hasAttribute("open"), headingInView: h.top >= b.top - 1 && h.bottom <= b.bottom };
    });
    assert.deepEqual(revealed, { open: true, headingInView: true }, "the `#` click opened the fold and scrolled the heading into view");
    const sw2 = await switchViews(page);
    assert.equal(sw2.newBox, true);
    assert.deepEqual(await folds(page), [["md-frontmatter", true], ["md-callout md-callout-tip", true], ["md-callout md-callout-important", false], ["md-callout md-callout-note", true]],
      "the fold the reveal opened is still open after the switch, and the others stand as chosen");

    // the authored default is what a fold the person never touched shows: close everything, switch, and the `+` one stays closed too
    await page.click("#romp-fileview .fileview-md details.md-frontmatter > summary");
    await page.click("#romp-fileview .fileview-md details.md-callout-tip > summary");
    await page.click("#romp-fileview .fileview-md details.md-callout-note > summary");
    await settle(page);
    assert.deepEqual((await folds(page)).map((f) => f[1]), [false, false, false, false]);
    await switchViews(page);
    assert.deepEqual((await folds(page)).map((f) => f[1]), [false, false, false, false], "a `+` callout the person closed stays closed across the paint");

    assert.deepEqual(errors, [], "no page errors");
    await page.context().close();
  });
});

test("URL viewer: the folds stand as chosen across its Rendered/Raw switch", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openNote(browser, filesBundle(), "url");
    assert.deepEqual(await folds(page), AUTHORED, "the URL document's first paint shows the folds as authored");
    await choose(page);
    assert.deepEqual(await folds(page), CHOSEN);
    const chosenHeights = await heights(page);
    const sw = await switchViews(page);
    assert.deepEqual([sw.rawHadMd, sw.newBox], [false, true], "the URL viewer's switch painted a new box");
    assert.deepEqual(await folds(page), CHOSEN, "after Raw and Rendered the URL document's folds stand as the person left them");
    assert.deepEqual(await heights(page), chosenHeights);
    assert.deepEqual(errors, [], "no page errors");
    await page.context().close();
  });
});
