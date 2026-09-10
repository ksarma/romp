// The ==mark== wash and the comment marks in the Rendered view, in headless Chromium (plans/markdown-viewer.md, Slice 4
// item 6). The construct rule first shipped as `.md mark:not(.cmt-hl), .fileview-md mark`, and the `.fileview-md mark`
// half (0,1,1) outranks the viewer's own marks, single-class rules (0,1,0): anchor-map.ts makeMark paints a comment's
// highlight (`mark.fc-hl`), the composer's pending target (`mark.fc-presel`) and a pending insertion (`mark.fc-ins`) as
// <mark> elements, and inside `.fileview-md` every one of them took the ==mark== dress, a 35% amber wash with 0.15em side
// padding and 2px corners, in place of its own (the slice's review, round 1, seeded into round 3). The rule keys on the
// class the renderer emits now, `mark.md-mark`, so it names the ==mark== alone and no `:not()` list has to track the
// comment classes. The fixture goes through the real grammar (marked under applyMdConfig, then sanitizeMd) and the real
// painters (paintRendered, paintChangesRendered), twice on one page: inside `.fileview-md`, and in a plain root outside
// it, the reference. The assertion is the invariant: a comment mark inside the Rendered view is dressed exactly as the
// same mark outside it (background, padding, radius, ink, ring), the ==mark== keeps its wash and is not the browser's
// yellow, and the two washes differ. Both sheets (the feed page loads feed.css alone), both themes. Skips LOUDLY
// without a playwright browser (CI installs none), as the other browser legs do. Synthetic text only.
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
const sheet = (name: string) => fs.readFileSync(path.join(UI, name), "utf8").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);
const SHEETS: Array<[string, string]> = [["styles.css", sheet("styles.css")], ["feed.css", sheet("feed.css")]];

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The viewer's renderer (the singleton under md-config.ts, through sanitizeMd) and the comments panel's painters. */
function probeBundle(): string {
  const contents = [
    'import { marked } from "marked";',
    'import { applyMdConfig } from "./md-config";',
    'import { sanitizeMd } from "./md-sanitize";',
    'import { paintRendered, paintChangesRendered } from "./anchor-map";',
    "applyMdConfig();",
    "(window as any).__md = (s: string) => sanitizeMd(marked.parse(s) as string).innerHTML;",
    // the panel's paint calls (file-comments.ts): a located comment, the composer's target, an insertion and a deletion point
    "(window as any).__paint = (root: Element, src: string) => ({",
    "  hl: paintRendered(root, src, { start: 6, end: 11 }, 'fc-hl', { act: 'fcopen', id: 'c1' }),",
    "  presel: paintRendered(root, src, { start: 12, end: 19 }, 'fc-presel'),",
    "  changes: paintChangesRendered(root, src, [",
    "    { id: 'ch1', kind: 'ins', curFrom: 20, curTo: 25, oldText: '', author: 'web' },",
    "    { id: 'ch2', kind: 'del', curFrom: 26, curTo: 26, oldText: 'gone', author: 'web' },",
    "  ], () => ({ '--fc-author': 'rgb(10, 20, 30)' })),",
    "});",
  ].join("\n");
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "mark-classes-probe.ts" } });
  return r.outputFiles[0].text;
}

const SRC = "Alpha bravo charlie delta echo foxtrot.\n\nA ==golf== word.\n";   // bravo 6..11, charlie 12..19, delta 20..25, the point at 26

const PAGE = (css: string) => `<!DOCTYPE html><html><head><meta charset=utf-8><style>${css}</style></head><body>
<div class="fileview"><div class="fileview-body"><div class="fileview-md" id=f></div></div></div>
<div class="fileview-body"><div id=r></div></div>
<script>window.__pageErrors=[];window.addEventListener("error",function(e){window.__pageErrors.push(String(e.message));});</script>
<script>${probeBundle()}</script>
<script>
  var src = ${JSON.stringify(SRC)};
  var f = document.getElementById("f"), r = document.getElementById("r");
  f.innerHTML = window.__md(src); r.innerHTML = window.__md(src);
  window.__painted = { f: window.__paint(f, src), r: window.__paint(r, src) };
</script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

const UA_MARK_BG = "rgb(255, 255, 0)";   // the browser's default <mark>
const MARKS = ["mark.fc-hl", "mark.fc-presel", "mark.fc-ins", "span.fc-del"];
const PROPS = ["backgroundColor", "color", "paddingLeft", "paddingRight", "borderTopLeftRadius", "boxShadow"];
type Dress = Record<string, Record<string, string> | null>;
/** The computed dress of each mark under one root, keyed by selector; a missing element reads null. */
const READ = `(function (rootId, sels, props) {
  var root = document.getElementById(rootId), out = {};
  for (var i = 0; i < sels.length; i++) {
    var el = root.querySelector(sels[i]);
    if (!el) { out[sels[i]] = null; continue; }
    var cs = getComputedStyle(el), o = { text: el.textContent };
    for (var j = 0; j < props.length; j++) o[props[j]] = cs[props[j]];
    out[sels[i]] = o;
  }
  return out;
})`;

test("inside the Rendered view a comment highlight, the composer's target, an insertion and a deletion point are dressed exactly as outside it, and the ==mark== alone wears the amber wash, under both sheets and both themes", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [name, css] of SHEETS) {
      const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => errors.push(e.message));
      await page.setContent(PAGE(css), { waitUntil: "load" });
      assert.deepEqual(errors, [], name + ": the probe bundle ran clean");
      assert.deepEqual(await page.evaluate("window.__pageErrors"), [], name + ": no script error on the page");
      const painted = await page.evaluate("window.__painted") as any;
      for (const root of ["f", "r"]) {
        assert.equal(painted[root].hl && painted[root].hl.length, 1, name + " " + root + ": the comment highlight painted one mark");
        assert.equal(painted[root].presel && painted[root].presel.length, 1, name + " " + root + ": the composer's target painted one mark");
        assert.deepEqual(painted[root].changes, { painted: ["ch1", "ch2"], unpainted: [] }, name + " " + root + ": both changes painted");
      }
      for (const theme of ["dark", "light"]) {
        if (theme === "light") await page.evaluate("document.body.classList.add('theme-light')");
        const where = name + " " + theme;
        const args = JSON.stringify(MARKS.concat(["mark.md-mark"])) + ", " + JSON.stringify(PROPS);
        const inside = await page.evaluate(READ + '("f", ' + args + ")") as Dress;
        const outside = await page.evaluate(READ + '("r", ' + args + ")") as Dress;
        for (const sel of MARKS) {
          assert.ok(inside[sel] && outside[sel], where + ": " + sel + " is on the page in both roots");
          assert.deepEqual(inside[sel], outside[sel], where + ": " + sel + " inside .fileview-md is dressed as the same mark outside it (background, ink, padding, radius, ring)");
        }
        // the ==mark== itself: the renderer's class, the amber wash, never the browser's yellow, and not the comment's wash
        const md = inside["mark.md-mark"];
        assert.ok(md, where + ": the ==mark== renders as mark.md-mark (md-config.ts emits the class the sheets key on)");
        assert.equal(md!.text, "golf", where + ": the ==mark== holds its text");
        assert.notEqual(md!.backgroundColor, UA_MARK_BG, where + ": the ==mark== is not the browser's yellow");
        assert.notEqual(md!.backgroundColor, "rgba(0, 0, 0, 0)", where + ": the ==mark== has its wash");
        assert.notEqual(md!.backgroundColor, inside["mark.fc-hl"]!.backgroundColor, where + ": the comment highlight's wash is not the ==mark== wash");
        assert.notEqual(md!.backgroundColor, inside["mark.fc-presel"]!.backgroundColor, where + ": the composer's target is not the ==mark== wash");
        assert.notEqual(md!.backgroundColor, inside["mark.fc-ins"]!.backgroundColor, where + ": the insertion's tint is not the ==mark== wash");
        assert.equal(inside["mark.fc-ins"]!.paddingLeft, "0px", where + ": the insertion keeps its own padding (none), not the ==mark== side padding");
        assert.equal(inside["mark.fc-hl"]!.borderTopLeftRadius, "5px", where + ": the comment highlight keeps its 5px corners");
        assert.equal(inside["mark.fc-presel"]!.borderTopLeftRadius, "5px", where + ": the composer's target keeps its 5px corners");
      }
      await page.close();
    }
  });
});
