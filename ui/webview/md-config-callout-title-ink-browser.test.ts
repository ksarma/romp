// A callout's title ink, in headless Chromium (plans/markdown-viewer.md, Slice 4 item 5). The title rule first painted
// the title text in `--callout`, the token the rail and the 8% wash take, and those tokens are rails and fills, not
// inks: any type the sheet does not map (`[!custom]`, a typo such as `[!warn]`) took the hairline `--box-border`, a
// title at 1.45:1 on the dark themes and 1.31:1 on the light one, unreadable beside a body at 10:1; the caution family
// took `--err`, 2.9:1 on the dark themes; and on the light theme the tip and important titles read at 2.1:1 and 2.0:1,
// since `--st-awaitbg-bg` and `--st-compacting-bg` are background fills whose inks are their `-fg` pairs (the slice's
// review, round 3). The title reads in the body's ink now (`color: inherit`), bold, and the type's tint stays on the
// rail and the wash. The fixture goes through the real grammar (marked under applyMdConfig, then sanitizeMd) into
// `.fileview-md`; for every callout, the five GitHub alerts, a custom type and a folded one, the assertion is WCAG's
// contrast of the title's ink composited over the wash and the page, at least 4.5:1, the bar the slice applied to
// KaTeX's flagged text (`--math-err`), and the title in the body's own ink. Round 5: with the title in the body's ink the
// rail and the wash are the type's one carrier, and the wash at 8% is 1.1:1 on any page, so the rail must read; the tip
// and important rails took the status chips' fills (`--st-awaitbg-bg`, `--st-compacting-bg`), the same hex in both
// themes, 6.15:1 and 6.70:1 on the dark page and 2.27:1 and 2.09:1 on the light one, under WCAG's 3:1 non-text floor,
// so on the light theme a titled `> [!tip]-` and `> [!important]-` were hard to tell from each other and from an unmapped
// type's hairline. The two tints are tokens of their own now, `--callout-tip` and `--callout-important`, the light block
// pointing them at inks of its own; the five alerts' rails are held here at 3:1 on the page. Both sheets, the three theme
// classes theme.ts applies. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do.
// Synthetic text only.
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
/** The viewer's renderer, minus the viewer's own passes: the singleton under md-config.ts, through sanitizeMd. */
function probeBundle(): string {
  const contents = [
    'import { marked } from "marked";',
    'import { applyMdConfig } from "./md-config";',
    'import { sanitizeMd } from "./md-sanitize";',
    "applyMdConfig();",
    "(window as any).__md = (s: string) => sanitizeMd(marked.parse(s) as string).innerHTML;",
  ].join("\n");
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "callout-title-ink-probe.ts" } });
  return r.outputFiles[0].text;
}

const TYPES = ["note", "tip", "important", "warning", "caution", "custom", "warn"];   // GitHub's five, an Obsidian type no rule names, a typo
const NOTE = [
  "# Rollout", "",
  "A body paragraph before the callouts.", "",
  ...TYPES.flatMap((t) => [`> [!${t}] ${t} title text`, `> Body of the ${t} callout.`, ""]),
  "> [!note]- folded title text", "> Hidden body.", "",
].join("\n");

const PAGE = (css: string, bodyClass: string) => `<!DOCTYPE html><html><head><meta charset=utf-8><style>${css}</style></head><body class="${bodyClass}">
<div class="fileview-md" id=f></div>
<script>window.__pageErrors=[];window.addEventListener("error",function(e){window.__pageErrors.push(String(e.message));});</script>
<script>${probeBundle()}</script>
<script>document.getElementById("f").innerHTML = window.__md(${JSON.stringify(NOTE)});</script>
</body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

// ── colour arithmetic: Chromium's computed colours as rgb(), rgba() or color(srgb r g b / a), composited, then WCAG 2 contrast ──
type RGBA = [number, number, number, number];
function parse(s: string): RGBA {
  let m = /^rgba?\(\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\s*\)$/.exec(s);
  if (m) return [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]];
  m = /^color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+))?\s*\)$/.exec(s);
  if (m) return [+m[1] * 255, +m[2] * 255, +m[3] * 255, m[4] === undefined ? 1 : +m[4]];
  throw new Error("a colour this test cannot read: " + s);
}
const over = (top: RGBA, under: RGBA): RGBA => [0, 1, 2].map((i) => top[i] * top[3] + under[i] * (1 - top[3])).concat([1]) as RGBA;
function luminance(c: RGBA): number {
  const lin = (v: number) => { const x = v / 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
  return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
}
function contrast(a: RGBA, b: RGBA): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

type Callout = { cls: string; tag: string; title: string; wash: string; rail: string; titleText: string; weight: string };
type Scene = { page: string; body: string; callouts: Callout[] };
const READ = `(function () {
  var root = document.getElementById("f");
  var pageBg = getComputedStyle(document.body).backgroundColor;
  return {
    page: pageBg,
    body: getComputedStyle(root.querySelector(":scope > p")).color,
    callouts: Array.from(root.querySelectorAll(".md-callout")).map(function (el) {
      var title = el.querySelector(".md-callout-title"), cs = getComputedStyle(el), ts = getComputedStyle(title);
      return { cls: el.className, tag: el.tagName.toLowerCase(), title: ts.color, wash: cs.backgroundColor, rail: cs.borderLeftColor, titleText: title.textContent, weight: ts.fontWeight };
    }),
  };
})`;

const THEMES: Array<[string, string]> = [["classic", ""], ["yatharth", "chat-theme-yatharth"], ["yatharth-light", "chat-theme-yatharth theme-light"]];
const BAR = 4.5;   // WCAG's minimum for reading text; the slice's own bar for KaTeX's flagged text (--math-err)
const RAIL_FLOOR = 3;   // WCAG's non-text floor (1.4.11), the sheets' own for informational chrome (the PDF page's wait cue holds it too)
const ALERTS = /md-callout-(note|tip|important|warning|caution)\b/;   // GitHub's five, the mapped types whose rail carries the type

test("every callout's title, the five alerts, an unknown type, a typo and a folded one, reads at 4.5:1 or better in the body's own ink, and the five alerts' rails at 3:1 or better on the page, under both sheets and the three themes", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [name, css] of SHEETS) {
      for (const [theme, cls] of THEMES) {
        const where = name + " " + theme;
        const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
        const errors: string[] = [];
        page.on("pageerror", (e: Error) => errors.push(e.message));
        await page.setContent(PAGE(css, cls), { waitUntil: "load" });
        assert.deepEqual(errors, [], where + ": the probe bundle ran clean");
        assert.deepEqual(await page.evaluate("window.__pageErrors"), [], where + ": no script error on the page");
        const s = await page.evaluate(READ + "()") as Scene;
        await page.close();
        assert.equal(s.callouts.length, TYPES.length + 1, where + ": every callout rendered, the folded one included");
        const pageBg = parse(s.page);
        assert.equal(pageBg[3], 1, where + ": the page paints an opaque ground (" + s.page + ")");
        const body = parse(s.body);
        const bodyContrast = contrast(over(body, pageBg), pageBg);
        assert.ok(bodyContrast >= BAR, where + ": the body text reads at " + bodyContrast.toFixed(2) + ":1 on the page (the reference)");
        // the contrast of every title first (the defect), then the shape of the fix
        const label = (c: Callout) => where + " " + c.cls + " (" + c.tag + ")";
        for (const c of s.callouts) {
          const ground = over(parse(c.wash), pageBg);
          const ink = over(parse(c.title), ground);
          const ratio = contrast(ink, ground);
          assert.ok(ratio >= BAR, label(c) + ": the title " + JSON.stringify(c.titleText) + " reads at " + ratio.toFixed(2) + ":1 over its wash (" + c.title + " on " + c.wash + " on " + s.page + "); the bar is " + BAR + ":1");
        }
        for (const c of s.callouts) {
          assert.equal(c.weight, "600", label(c) + ": the title is bold");
          assert.equal(c.title, s.body, label(c) + ": the title is in the body's own ink; the type's tint is the rail and the wash");
          assert.notEqual(c.rail, "rgba(0, 0, 0, 0)", label(c) + ": the rail is drawn (the tint moved to it, not lost)");
        }
        // the tint still tells the types apart on the rail: the five alerts wear five rails
        const alerts = s.callouts.filter((c) => ALERTS.test(c.cls) && c.tag === "blockquote");
        const rails = alerts.map((c) => c.rail);
        assert.equal(new Set(rails).size, 5, where + ": the five alerts wear five rail tints: " + rails.join(" | "));
        // ...and every one of them reads on the page (round 5: the tip and important rails at 2.27:1 and 2.09:1 on the light page)
        for (const c of alerts) {
          const rail = over(parse(c.rail), pageBg);
          const ratio = contrast(rail, pageBg);
          assert.ok(ratio >= RAIL_FLOOR, label(c) + ": the rail (" + c.rail + ") reads at " + ratio.toFixed(2) + ":1 on the page " + s.page + "; the non-text floor is " + RAIL_FLOOR + ":1");
        }
      }
    }
  });
});
