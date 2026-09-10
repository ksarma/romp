// The anchor map past a paragraph marked joined onto the one before it, over the REAL Files bundle in headless Chromium
// (anchor-map.ts sourceRaw; md-config-merged-paragraph.test.ts holds the shapes on the stand-in). marked 12 joins the
// next paragraph onto a paragraph the regex stopped early for its own reason (a header-looking line over a delimiter
// row with a different cell count, a lowercase `<prefix>` line, a bare `1. ` bullet) whenever a block hint has a hit
// anywhere later in the note, with a newline in the raw the source does not hold; with this slice's display formulas in
// files.js (and its callouts, until round 3 dropped their hint) the join reached the Files pane, and every selection
// from the join to the end of the note refused with "a paragraph the mapping could not place" (the Slice 4 review,
// rounds 2 and 3); and the code join, an indented line under a paragraph that a delimiter-row-shaped line follows, needs
// no hint and collapsed the rest of the note's spans alike (round 5). Here a synthetic note with all three triggers, a
// nested one inside a callout, the code join in its four-space and tab forms, a display formula and a callout below is
// opened as a file
// document through the pane's relay, so the text goes through marked under md-config.ts, DOMPurify, the viewer's passes
// and KaTeX's fill, and the page's own DOM is what the map reads: every top-level element is its own block, and a
// selection in each paragraph, the joined ones, the ones between and the last one well past the formula, maps to its
// offset in the note. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do.
// Synthetic values only: an invented note, TESTHOST paths, a placeholder sid.
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
const FILE_PATH = "/tmp/TESTHOST/notes-api/docs/merged.md";
/** The note: the seeded table shape, the html-looking line, the bare bullet, the code join (four spaces, then a tab), the
 *  same table shape inside a callout whose body ends in a formula, a display formula and a callout below, prose between
 *  and after. */
const NOTE = [
  "Intro line\nColumn A\n|---|---|",
  "After merged.",
  "Run the tool with\n<prefix>/bin/tool\nand check the output.",
  "Para line\n1. \nMore text.",
  "Results:\n    metric | value\n|---|---|",
  "Some prose\n\tan afterthought\n|---|",
  "> [!note] Title\n> Intro inside\n> Column A\n> |---|---|\n> After inside\n> $$\n> y\n> $$",
  "Middle para.",
  "$$\nx\n$$",
  "> [!tip] Tip\n> Callout body.",
  "Last one here.",
].join("\n\n") + "\n";

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files pane's bundle plus the anchor map's exports, for the mapping over the page's own rendered box. */
function filesBundle(): string {
  const contents = 'import "./files";\nimport { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex } from "./anchor-map";\n(window as any).__rompProbe = { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex };\n';
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

/** A page of the Files surface with the note open as a file document (the pane's relay), the first paint awaited. */
async function openNote(browser: any, js: string): Promise<{ page: any; errors: string[] }> {
  const ctx = await browser.newContext({ viewport: { width: 900, height: 400 } });
  const page = await ctx.newPage();
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await ctx.route("**/*", (route: any) => {
    const u = new URL(route.request().url());
    if (u.host !== "romp.test") return route.fulfill({ status: 404, body: "" });
    if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FILES_HTML });
    if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
    if (u.pathname === "/file" && u.searchParams.get("path") === FILE_PATH) {
      return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: NOTE });
    }
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/files");
  await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [FILE_PATH, SID] as [string, string]);
  await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 15000 });
  await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
  return { page, errors };
}

/** The anchor map over the page's own rendered box: each needle selected in the rendered text and mapped, the tags of the
 *  top-level children and the block each pairs with, the block table. */
function mapInPage({ needles, source }: { needles: string[]; source: string }) {
  const probe = (window as any).__rompProbe;
  const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
  const point = (needle: string, atEnd: boolean) => {
    const walker = document.createTreeWalker(md, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode() as Text | null; n; n = walker.nextNode() as Text | null) {
      const i = n.data.indexOf(needle);
      if (i >= 0) return { node: n, offset: atEnd ? i + needle.length : i };
    }
    throw new Error("not in the rendered text: " + needle);
  };
  const out: Record<string, unknown> = {};
  for (const t of needles) {
    const a = point(t, false), f = point(t, true);
    out[t] = probe.mapRenderedSelection({ anchorNode: a.node, anchorOffset: a.offset, focusNode: f.node, focusOffset: f.offset, isCollapsed: false }, md, source);
  }
  const kids = Array.from(md.children);
  return { map: out, tags: kids.map((k) => k.tagName), owners: kids.map((k) => probe.renderedBlockIndex(md, source, k)), spans: probe.sourceBlockSpans(source) as Array<{ start: number; end: number }> };
}

test("over the real Files bundle, a note whose paragraphs marked joined maps every paragraph, the joined ones and every one after them, to its own offset", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openNote(browser, filesBundle());
    const needles = ["Intro line", "Column A", "After merged.", "Run the tool", "and check the output.", "Para line", "More text.", "Results:", "metric | value", "Some prose", "an afterthought", "Intro inside", "After inside", "Middle para.", "Callout body.", "Last one here."];
    const r = await page.evaluate(mapInPage, { needles, source: NOTE });   // the function itself is what the page runs
    // one element per block, in order: the joined paragraphs render as ONE <p> each, the callouts as blockquotes, the formula as KaTeX's span
    assert.deepEqual(r.tags, ["P", "P", "P", "P", "P", "P", "BLOCKQUOTE", "P", "SPAN", "BLOCKQUOTE", "P"], JSON.stringify(r.tags));
    assert.deepEqual(r.owners, r.tags.map((_: string, i: number) => i), "element i is block i (the 1:1 pairing over the real DOM)");
    assert.equal(r.spans.length, r.tags.length, "as many blocks as top-level elements");
    // the block table reads the note: each span is its block's text, at its own offset, in order
    const blockTexts = r.spans.map((s: { start: number; end: number }) => NOTE.slice(s.start, s.end));
    assert.deepEqual(blockTexts, [
      "Intro line\nColumn A\n|---|---|", "After merged.", "Run the tool with\n<prefix>/bin/tool\nand check the output.", "Para line\n1. \nMore text.",
      "Results:\n    metric | value\n|---|---|", "Some prose\n\tan afterthought\n|---|",
      "> [!note] Title\n> Intro inside\n> Column A\n> |---|---|\n> After inside\n> $$\n> y\n> $$", "Middle para.", "$$\nx\n$$", "> [!tip] Tip\n> Callout body.", "Last one here.",
    ]);
    for (let i = 1; i < r.spans.length; i++) assert.ok(r.spans[i].start > r.spans[i - 1].end, "spans in order: " + JSON.stringify(r.spans));
    // every selection maps to its indexOf offset: inside the joined paragraphs (the code join's indented lines too), between them,
    // inside the callout, and past the formula
    const m = r.map as Record<string, any>;
    for (const s of needles) {
      assert.equal(m[s].ok, true, s + ": " + JSON.stringify(m[s]));
      const at = NOTE.indexOf(s);
      assert.deepEqual(m[s].range, { start: at, end: at + s.length }, s);
      assert.equal(m[s].quote, s);
    }
    assert.deepEqual(errors, [], "no page errors");
    await page.context().close();
  });
});
