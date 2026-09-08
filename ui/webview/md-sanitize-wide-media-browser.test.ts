// Wide inline media in a rendered note, over the REAL files bundle in headless Chromium (plans/markdown-viewer.md,
// Slice 1, review finding). `contain: layout` on .fileview-md turns anything wider than the md box into ink overflow:
// the body cannot scroll to it, so before the fix a 1500px <svg> diagram nested in a paragraph, a <canvas> or a
// <video> was painted, clipped at the body's edge and unreachable (the base commit scrolled the body sideways to
// it). The sheets now cap svg, canvas and video at the column the way `.fileview-md img` already was, with
// `height: auto` so each keeps its own ratio, and a direct child carries the prose measure like a direct-child
// <img> (at 380px the bare 860px cap would itself overflow). The rule sits at zero class specificity (:where) so
// KaTeX's own `.katex svg { height: inherit }` still wins over its stretchy glyphs once math renders here (Slice 4);
// the last step holds that cascade with the KaTeX sheet inlined where the built styles.css carries it. A 12-column
// table is the control: its own overflow-x scroll is untouched. Skips LOUDLY without a playwright browser (CI
// installs none), as the other browser legs do. Synthetic values only: an invented note, TESTHOST paths, a
// placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
// the built styles.css carries katex.min.css inlined where the source @imports it (esbuild.js); the page here does the same
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");
assert.ok(STYLES.includes(".katex svg{"), "the KaTeX sheet is inlined in the test page as it is in the built sheet");

const SID = "11111111-2222-3333-4444-555555555555";
const PATH = "/tmp/TESTHOST/notes-api/report.md";
const RATIO = 40 / 1500;                                          // every sized fixture is 1500 by 40

// the fixture note: a standalone <svg> block (a direct child of .fileview-md), the same nested in prose (marked puts a
// one-line tag inside a <p>), a canvas and a video sized 1500 by 40, a KaTeX-shaped stretchy glyph, a wide table
const NOTE = [
  "# Report",
  "",
  '<svg class="fx-block" width="1500" height="40" viewBox="0 0 1500 40">',
  '  <rect width="1500" height="40" fill="#08c"/>',
  "</svg>",
  "",
  'Diagram in prose: <svg class="fx-nested" width="1500" height="40" viewBox="0 0 1500 40"><rect width="1500" height="40" fill="#0a0"/></svg> end.',
  "",
  'Canvas: <canvas class="fx-canvas" width="1500" height="40"></canvas>',
  "",
  'Video: <video class="fx-video" src="/nope.mp4" width="1500" height="40"></video>',
  "",
  'Glyph: <span class="katex"><span class="hide-tail fx-tail"><svg class="fx-katex" width="400em" height="1.08em" viewBox="0 0 400000 1080" preserveAspectRatio="xMinYMin slice"><path d="M0 0h400000v1080H0z"/></svg></span></span>',
  "",
  "| " + Array.from({ length: 12 }, (_, i) => "column_" + (i + 1) + "_wide_header").join(" | ") + " |",
  "|" + Array.from({ length: 12 }, () => "---").join("|") + "|",
  "| " + Array.from({ length: 12 }, (_, i) => "cell_" + (i + 1)).join(" | ") + " |",
  "",
  "Last line.",
  "",
].join("\n");

function bundle(entry: string): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, entry)], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the Files page as the kernel serves it (_files_page): the chat's styles.css for the viewer's dress, files-pane.css
// after it for the pane layout, a fake acquireVsCodeApi (the shim's role), then the files bundle
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane>
<div id=files-empty></div>
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};</script>
<script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (page: any, errors: string[]) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const filesJs = bundle("files.ts");
    const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FILES_HTML });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: filesJs });
      if (u.pathname === "/file" && u.searchParams.get("path") === PATH) {
        return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: NOTE });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/files");
    await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [PATH, SID] as [string, string]);
    await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 10000 });
    await body(page, errors);
  } finally {
    await browser.close();
  }
}

type Box = { width: number; height: number; right: number; parent: string; present: boolean };
type Facts = {
  contain: string;
  body: { scrollWidth: number; clientWidth: number; maxScrollLeft: number; right: number };
  els: Record<string, Box>;
  table: { scrollWidth: number; clientWidth: number; maxScrollLeft: number; lastCellRight: number; right: number };
};
const MEDIA = ["fx-block", "fx-nested", "fx-canvas", "fx-video"];

// measured in the page: the body's sideways scroll range, each fixture's box against the body's edge, the table's own scroll
function measure(): Facts {
  const body = document.querySelector("#romp-fileview .fileview-body") as HTMLElement;
  const md = body.querySelector(".fileview-md") as HTMLElement;
  body.scrollLeft = 100000; const maxScrollLeft = body.scrollLeft; body.scrollLeft = 0;
  const br = body.getBoundingClientRect();
  const els: Record<string, Box> = {};
  for (const cls of ["fx-block", "fx-nested", "fx-canvas", "fx-video"]) {
    const el = md.querySelector("." + cls) as HTMLElement | null;
    if (!el) { els[cls] = { width: 0, height: 0, right: 0, parent: "", present: false }; continue; }
    const r = el.getBoundingClientRect();
    els[cls] = { width: r.width, height: r.height, right: r.right, parent: (el.parentElement as HTMLElement).className || (el.parentElement as HTMLElement).tagName.toLowerCase(), present: true };
  }
  const table = md.querySelector("table") as HTMLElement;
  table.scrollLeft = 100000; const tMax = table.scrollLeft;
  const cells = table.querySelectorAll("td");
  const lastCellRight = cells[cells.length - 1].getBoundingClientRect().right;
  const tr = table.getBoundingClientRect();
  table.scrollLeft = 0;
  return {
    contain: getComputedStyle(md).contain,
    body: { scrollWidth: body.scrollWidth, clientWidth: body.clientWidth, maxScrollLeft, right: br.right },
    els,
    table: { scrollWidth: table.scrollWidth, clientWidth: table.clientWidth, maxScrollLeft: tMax, lastCellRight, right: tr.right },
  };
}

function check(f: Facts, at: string): void {
  assert.equal(f.contain, "layout", at + ": the md box is layout-contained (the fixed-descendant rule this leg lives with)");
  assert.equal(f.body.scrollWidth, f.body.clientWidth, at + ": the body never scrolls sideways");
  assert.equal(f.body.maxScrollLeft, 0, at + ": scrollLeft stays pinned at 0");
  assert.equal(f.els["fx-block"].parent, "fileview-md", at + ": the standalone svg block is a direct child of the md box");
  assert.equal(f.els["fx-nested"].parent, "p", at + ": the one-line svg sits in a paragraph, where marked puts it");
  for (const cls of MEDIA) {
    const b = f.els[cls];
    assert.ok(b.present, at + ": ." + cls + " survives the sanitizer");
    assert.ok(b.width > 0 && b.height > 0, at + ": ." + cls + " has a box: " + b.width + " by " + b.height);
    assert.ok(b.right <= f.body.right + 0.5, at + ": ." + cls + " ends inside the body, right " + b.right + " vs body right " + f.body.right + " (past it, it is painted, clipped and unreachable)");
    assert.ok(b.width < 1500, at + ": ." + cls + " was capped at the column, not laid out at its 1500px: " + b.width);
  }
  for (const cls of MEDIA) {
    const b = f.els[cls];
    assert.ok(Math.abs(b.height - b.width * RATIO) <= 1, at + ": ." + cls + " keeps its 1500:40 ratio as it shrinks (height: auto, not a letterboxed 40px): " + b.width + " by " + b.height);
  }
  // the control: a 12-column table still scrolls inside its own box, and its last cell is reachable there
  assert.ok(f.table.scrollWidth > f.table.clientWidth, at + ": the wide table overflows its own box (" + f.table.scrollWidth + " > " + f.table.clientWidth + ")");
  assert.ok(f.table.maxScrollLeft > 0, at + ": the table's own scroll range is intact: " + f.table.maxScrollLeft);
  assert.ok(f.table.lastCellRight <= f.table.right + 0.5, at + ": scrolled, the table's last cell is reachable: " + f.table.lastCellRight + " vs " + f.table.right);
}

test("wide inline media in a rendered note fits the column instead of vanishing past the body's edge", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (page, errors) => {
    // 1. a 900px pane: the nested svg, canvas and video used to lay out at 1500px behind a body that could not scroll
    check(await page.evaluate(measure), "900px");
    // 2. a 380px pane (the Files column is often that narrow): the standalone block's 860px prose cap alone would overflow too
    await page.setViewportSize({ width: 380, height: 600 });
    check(await page.evaluate(measure), "380px");
    // 3. the cascade KaTeX needs: `.katex svg { height: inherit; position: absolute; width: 100% }` (katex.min.css,
    // inlined at the top of styles.css) still wins over the media rule for a stretchy glyph. Slice 4 renders math
    // into the note after the sanitize, and its wrapper carries the glyph's height inline; that is simulated here by
    // setting the wrapper's height by script, then reading what the svg inherits. A rule written at class
    // specificity in the sheet's later position would win the tie and hand the glyph an auto height instead.
    const glyph = await page.evaluate(() => {
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const tail = md.querySelector(".fx-tail") as HTMLElement;
      const svg = md.querySelector(".fx-katex") as SVGElement;
      tail.style.display = "inline-block"; tail.style.width = "200px"; tail.style.height = "30px";
      const cs = getComputedStyle(svg);
      return { present: !!tail && !!svg, position: cs.position, height: cs.height, width: cs.width };
    });
    assert.ok(glyph.present, "the KaTeX-shaped fixture survives the sanitizer (svg profile)");
    assert.equal(glyph.position, "absolute", "KaTeX's own svg rule applies inside the note");
    assert.equal(glyph.height, "30px", "the glyph inherits its wrapper's height: KaTeX's `.katex svg { height: inherit }` outranks the media rule's height: auto");
    assert.equal(glyph.width, "200px", "and fills its wrapper's width (max-width: 100% is a no-op there)");
    assert.deepEqual(errors, [], "no page errors");
  });
});
