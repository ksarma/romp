// Wide inline media in a rendered note, over the REAL files bundle in headless Chromium (plans/markdown-viewer.md,
// Slice 1, review finding). `contain: layout` on .fileview-md turns anything wider than the md box into ink overflow:
// the body cannot scroll to it, so before the fix a 1500px <svg> diagram nested in a paragraph, a <canvas> or a
// <video> was painted, clipped at the body's edge and unreachable (the base commit scrolled the body sideways to
// it). The sheets now cap svg, canvas and video at the column the way `.fileview-md img` already was, with
// `height: auto` on a PIXEL-sized one so it keeps its own ratio as it shrinks (a percentage-width element the cap
// never shrinks keeps the author's explicit height: the first cut's unconditional height: auto grew a full-width
// `<svg width="100%" height="30" viewBox>` to 258px and an unloaded `<video height="120">` to Chromium's default 150;
// review round 1), and a direct child carries the prose measure like a direct-child
// <img> (at 380px the bare 860px cap would itself overflow). Both rules sit at zero class specificity (:where) so
// KaTeX's own `.katex svg { height: inherit }` still wins over its stretchy glyphs once math renders here (Slice 4);
// the last step holds that cascade with the KaTeX sheet inlined where the built styles.css carries it. A <video> is
// the one of the three whose natural ratio can differ from its attributes: the browser maps `width="640"
// height="360"` to `aspect-ratio: auto 640 / 360`, and `auto` defers to the media's own ratio once a poster or the
// frames are there, so height: auto alone laid a 640 by 360 clip with a square poster out 640 by 640 in a pane that
// shrank nothing, and the box jumped to the frames' shape at play (review round 2). mdBlock (file-view.ts) writes the
// attributes' ratio as the video's inline aspect-ratio, so the box is the author's shape capped or not; the poster
// fixtures below hold that, in each spelling HTML's dimension rules and the browser's own mapping read as a length
// (`640`, `640.5`, `640px`; mdBlock parses the attributes itself, so a spelling it misread would leave that clip at
// the poster's ratio, and no other test carries a <video>), and a percentage width, which is not a length and gets
// no ratio written. Whitespace around a value never reaches either test: the sanitizer trims every attribute value
// (DOMPurify, all but `value`), and the leg pins that on a padded length and a padded percentage, since the sheet's
// `[width$="%"]` test and mdBlock's `%` test both rely on it. A witness video (a poster and no height attribute) tells the leg when the
// poster has been decoded, since a video fires no event for it. A 12-column table is the control: its own overflow-x
// scroll is untouched. Skips LOUDLY without a playwright browser (CI
// installs none), as the other browser legs do. Synthetic values only: an invented note, TESTHOST paths, a
// placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
// the built styles.css carries katex.min.css inlined where the source @imports it (esbuild.js); the page here does the same
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");
assert.ok(STYLES.includes(".katex svg{"), "the KaTeX sheet is inlined in the test page as it is in the built sheet");

const SID = "11111111-2222-3333-4444-555555555555";
const PATH = "/tmp/TESTHOST/notes-api/report.md";
const RATIO = 40 / 1500;                                          // every wide fixture is 1500 by 40
const POSTER_URL = "http://romp.test/media/square.svg";           // an absolute poster URL, as a note pointing at a host would carry
const SQUARE_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120"><rect width="120" height="120" fill="#c60"/></svg>';

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
  // the square poster on the wide video: shrunk to the column, the box must keep the attributes' 1500:40, not the poster's 1:1
  'Video: <video class="fx-video" src="/nope.mp4" poster="' + POSTER_URL + '" width="1500" height="40"></video>',
  "",
  // sized by the author with a percentage width and an explicit height: the cap shrinks nothing, the height must stand
  'Banner: <svg class="fx-pct" width="100%" height="30" viewBox="0 0 100 30" preserveAspectRatio="none"><rect width="100" height="30" fill="#c60"/></svg>',
  "",
  'Square box: <svg class="fx-pct-sq" width="100%" height="40" viewBox="0 0 100 100"><rect width="100" height="100" fill="#606"/></svg>',
  "",
  'Wide video: <video class="fx-vidh" src="/nope.mp4" width="100%" height="120"></video>',
  "",
  'Tall video: <video class="fx-vidonly" src="/nope.mp4" height="120"></video>',
  "",
  // the author's shape on a video the cap does not touch: 640 by 360 with a square poster stays 640 by 360 (the
  // browser's `aspect-ratio: auto 640 / 360` alone made it 640 by 640 once the poster was decoded); at 380px it
  // shrinks to the column in that ratio
  'Clip: <video class="fx-poster" src="/nope.mp4" poster="' + POSTER_URL + '" width="640" height="360"></video>',
  "",
  // the same clip in the other spellings of a length: a fraction, a unit after the digits. The browser lays each out
  // 640 (or 640.5) wide and maps it to `aspect-ratio: auto W / H` exactly as it does "640", so each must get the same
  // inline ratio; one left at the browser's `auto` would sit square under its poster. The padded one reaches the viewer
  // trimmed (the sanitizer trims every attribute value), which the leg pins: no whitespace rule of the viewer's is ever met
  'Clip, padded: <video class="fx-poster-ws" src="/nope.mp4" poster="' + POSTER_URL + '" width=" 640 " height=" 360 "></video>',
  "",
  'Clip, fraction: <video class="fx-poster-frac" src="/nope.mp4" poster="' + POSTER_URL + '" width="640.5" height="360"></video>',
  "",
  'Clip, unit: <video class="fx-poster-px" src="/nope.mp4" poster="' + POSTER_URL + '" width="640px" height="360"></video>',
  "",
  // a percentage width with a poster: no cap, no ratio to keep, the height attribute stands as it does without one
  'Full-width clip: <video class="fx-pct-poster" src="/nope.mp4" poster="' + POSTER_URL + '" width="100%" height="120"></video>',
  "",
  // the same with the percentage padded: the sheet's `[width$="%"]` would miss "100% " and hand the poster's 1:1 to a
  // full-width box; the sanitizer's trim is what keeps the height attribute standing, so the leg holds it here
  'Full-width clip, padded: <video class="fx-pct-ws" src="/nope.mp4" poster="' + POSTER_URL + '" width="100% " height="120"></video>',
  "",
  // the witness: a poster and no height attribute, so its box follows the poster's ratio (200 by 100 before the poster
  // is decoded, 200 by 200 after); the leg waits on it before measuring the poster fixtures
  'Witness: <video class="fx-witness" src="/nope.mp4" poster="' + POSTER_URL + '" width="200"></video>',
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
      if (u.href === POSTER_URL) return route.fulfill({ status: 200, contentType: "image/svg+xml", body: SQUARE_SVG });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/files");
    await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [PATH, SID] as [string, string]);
    await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 10000 });
    // the poster is decoded (no event tells; the witness's box turns square), then two frames so every poster video has laid out
    await page.waitForFunction(() => {
      const v = document.querySelector("#romp-fileview .fileview-md .fx-witness");
      return !!v && Math.abs(v.getBoundingClientRect().height - v.getBoundingClientRect().width) < 1;
    }, null, { timeout: 10000 });
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r(null)))));
    await body(page, errors);
  } finally {
    await browser.close();
  }
}

type Box = { width: number; height: number; right: number; parent: string; present: boolean; parentWidth: number; aspect: string; widthAttr: string | null };
type Facts = {
  contain: string;
  body: { scrollWidth: number; clientWidth: number; maxScrollLeft: number; right: number };
  els: Record<string, Box>;
  table: { scrollWidth: number; clientWidth: number; maxScrollLeft: number; lastCellRight: number; right: number };
};
const MEDIA = ["fx-block", "fx-nested", "fx-canvas", "fx-video"];
// the author-sized shapes and the height each keeps: a percentage width the cap never shrinks, an explicit height
const SIZED: Record<string, number> = { "fx-pct": 30, "fx-pct-sq": 40, "fx-vidh": 120, "fx-vidonly": 120, "fx-pct-poster": 120, "fx-pct-ws": 120 };
// the author-shaped videos: each one's attributes' width, or the column when that is narrower, and always the attributes'
// ratio; the width attribute is spelled four ways a length can be (a spelling misread as no length gets no ratio written)
const POSTERS: Record<string, { width: number; height: number }> = {
  "fx-poster": { width: 640, height: 360 },                       // width="640"
  "fx-poster-ws": { width: 640, height: 360 },                    // width=" 640 ": padded, and trimmed by the sanitizer before the viewer reads it
  "fx-poster-frac": { width: 640.5, height: 360 },                // width="640.5": a fraction
  "fx-poster-px": { width: 640, height: 360 },                    // width="640px": a unit after the digits, which the rules ignore
};
// percentage-width videos: not a length, so no ratio is written and the browser's own value stays `auto` (its mapping
// stops at a percentage too); the height attribute stands (SIZED, above)
const PCT_VIDEOS = ["fx-vidh", "fx-pct-poster", "fx-pct-ws"];
// what the viewer reads after the sanitizer: every attribute value trimmed (DOMPurify trims all but `value`), so neither
// the sheet's `[width$="%"]` nor mdBlock's dimension parse meets whitespace, and a padded percentage still ends in `%`
const TRIMMED: Record<string, string> = { "fx-poster-ws": "640", "fx-pct-ws": "100%" };

// measured in the page: the body's sideways scroll range, each fixture's box against the body's edge, the table's own scroll
function measure(): Facts {
  const body = document.querySelector("#romp-fileview .fileview-body") as HTMLElement;
  const md = body.querySelector(".fileview-md") as HTMLElement;
  body.scrollLeft = 100000; const maxScrollLeft = body.scrollLeft; body.scrollLeft = 0;
  const br = body.getBoundingClientRect();
  const els: Record<string, Box> = {};
  for (const cls of ["fx-block", "fx-nested", "fx-canvas", "fx-video", "fx-pct", "fx-pct-sq", "fx-vidh", "fx-vidonly", "fx-poster", "fx-poster-ws", "fx-poster-frac", "fx-poster-px", "fx-pct-poster", "fx-pct-ws", "fx-witness"]) {
    const el = md.querySelector("." + cls) as HTMLElement | null;
    if (!el) { els[cls] = { width: 0, height: 0, right: 0, parent: "", present: false, parentWidth: 0, aspect: "", widthAttr: null }; continue; }
    const r = el.getBoundingClientRect();
    const parent = el.parentElement as HTMLElement;
    els[cls] = { width: r.width, height: r.height, right: r.right, parent: parent.className || parent.tagName.toLowerCase(), present: true,
      parentWidth: parent.getBoundingClientRect().width, aspect: getComputedStyle(el).aspectRatio, widthAttr: el.getAttribute("width") };
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
    assert.ok(Math.abs(b.height - b.width * RATIO) <= 1, at + ": ." + cls + " keeps its 1500:40 ratio as it shrinks (height: auto, not a letterboxed 40px" + (cls === "fx-video" ? ", and not the square poster's 1:1" : "") + "): " + b.width + " by " + b.height);
  }
  // a pixel-sized video keeps the AUTHOR's shape whether the cap shrinks it or not: 640 wide where the column allows,
  // the column's width where it does not, and the attributes' 640:360 either way, though its poster is square. The
  // ratio is the viewer's inline declaration, not the browser's `auto 640 / 360`, which yields to the poster's ratio.
  // Every spelling of a length gets it: a clip whose width the viewer misread as no length would be left at `auto`.
  for (const [cls, dim] of Object.entries(POSTERS)) {
    const b = f.els[cls];
    assert.ok(b.present && b.parent === "p", at + ": ." + cls + " survives the sanitizer in its paragraph");
    const want = Math.min(dim.width, b.parentWidth);
    assert.ok(Math.abs(b.width - want) <= 0.5, at + ": ." + cls + " is " + want + " wide (its width attribute, or the column when narrower): " + b.width);
    assert.ok(Math.abs(b.height - b.width * dim.height / dim.width) <= 1, at + ": ." + cls + " keeps the author's " + dim.width + ":" + dim.height + ", not the square poster's ratio: " + b.width + " by " + b.height);
    assert.equal(b.aspect, dim.width + " / " + dim.height, at + ": ." + cls + "'s aspect-ratio is the attributes' ratio itself, without `auto` (which defers to the poster)");
    assert.ok(b.right <= f.body.right + 0.5, at + ": ." + cls + " ends inside the body");
  }
  {
    const w = f.els["fx-witness"];
    assert.ok(w.present && Math.abs(w.height - w.width) <= 1 && Math.abs(w.width - 200) <= 0.5, at + ": the witness (no height attribute) follows the decoded poster's 1:1, so the poster was applied before this measure: " + w.width + " by " + w.height);
  }
  // a percentage width is no length: the viewer writes nothing, so the box's aspect-ratio is the browser's `auto`
  // (a `100 / 120` here would mean the `%` was read as a number; the height attribute would still hold the box, so
  // only the declaration itself tells)
  for (const cls of PCT_VIDEOS) {
    const b = f.els[cls];
    assert.ok(b.present, at + ": ." + cls + " survives the sanitizer");
    assert.equal(b.aspect, "auto", at + ": ." + cls + " (a percentage width) gets no aspect-ratio written");
  }
  // the padded spellings arrive trimmed: the sanitizer's doing, and the reason a whitespace rule of the viewer's (the
  // sheet's `$="%"`, the parse's leading-whitespace skip) is never exercised through it
  for (const [cls, want] of Object.entries(TRIMMED)) {
    assert.equal(f.els[cls].widthAttr, want, at + ": ." + cls + "'s width attribute reaches the viewer trimmed by the sanitizer");
  }
  // an author's explicit height on a percentage-width element (or on an unloaded video with no width) stands: the cap
  // shrinks nothing there, so height: auto has no ratio to keep and would only discard the attribute
  for (const [cls, h] of Object.entries(SIZED)) {
    const b = f.els[cls];
    assert.ok(b.present && b.width > 0, at + ": ." + cls + " survives the sanitizer with a box");
    assert.ok(Math.abs(b.height - h) <= 1, at + ": ." + cls + " keeps its height attribute of " + h + "px: " + b.width + " by " + b.height);
    assert.ok(b.right <= f.body.right + 0.5, at + ": ." + cls + " ends inside the body");
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
