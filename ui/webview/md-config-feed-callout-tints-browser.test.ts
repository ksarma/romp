// The callout tints on the FEED page, in headless Chromium (plans/markdown-viewer.md, Slice 4 item 5: "the sheets tint
// by class through the page's own tokens ... tip green, important teal"). The feed page loads feed.css alone
// (kernel.py serves one sheet there, and styles.css's :root never reaches it), and its bundle carries the file viewer, so
// a note opened in the Feed pane renders its callouts under feed.css. The slice's review round 2 found the tip and
// important rules reading `--st-awaitbg-bg` and `--st-compacting-bg`, two tokens feed.css declared only inside
// `body.theme-light`: in the two dark themes the callout's `--callout` was invalid at computed-value time, so the rail
// fell to 0px, the wash to transparent and the title to the body colour, less dressed than an unknown type's hairline,
// while note, warning and caution beside them kept their 3px tinted rails. Both sheets are built as the webview build
// builds them (esbuild.js's webview config, in memory, the KaTeX @import inlined) and the fixture goes through the real
// grammar (marked under applyMdConfig, then sanitizeMd), so the assertions read the computed dress of the elements the
// renderer emits: every GitHub alert wears a 3px rail whose tint is not the body colour, the five tints differ, the
// title reads in the body's ink (round 3 moved it off the tint: the tokens are rails and fills, and as text the hairline
// and the caution red were unreadable; md-config-callout-title-ink-browser.test.ts holds the contrast), and each type
// reads the SAME tint under feed.css as under styles.css (fileview-parity pins the
// rules byte-equal; this pins the tokens they name resolving alike). Three themes: classic (a bare body), yatharth and
// yatharth-light, the classes theme.ts applies. Skips LOUDLY without a playwright browser (CI installs none), as the
// other browser legs do. Synthetic text only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");

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
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "callout-tints-probe.ts" } });
  return r.outputFiles[0].text;
}
/** A sheet as the webview build emits it: esbuild.js's webview config, the KaTeX @import inlined, in memory. */
async function builtCss(sheet: string): Promise<string> {
  const { webview } = requireCjs("./esbuild.js") as { webview: Record<string, unknown> };
  const r = await (requireCjs("esbuild") as typeof import("esbuild")).build({ ...(webview as object), entryPoints: ["../ui/webview/" + sheet], write: false, logLevel: "silent" });
  return r.outputFiles!.find((f) => f.path.endsWith(".css"))!.text;
}

const ALERTS = ["tip", "important", "note", "warning", "caution"];   // GitHub's five
const TYPES = [...ALERTS, "custom"];                                  // plus an Obsidian type no rule names: the hairline
const NOTE = [
  "# Release notes", "",
  "A body paragraph before the callouts.", "",
  ...TYPES.flatMap((t) => [`> [!${t.toUpperCase()}] ${t} title`, `> Body of the ${t} callout.`, ""]),
  "> A plain quote for reference.", "",
].join("\n");

const PAGE = (css: string, bodyClass: string) => `<!DOCTYPE html><html><head><meta charset=utf-8><style>${css}</style></head><body class="${bodyClass}">
<div class="fileview-md" id=f></div>
<span id=tok-await style="color: var(--st-awaitbg-bg)">await</span>
<span id=tok-compact style="color: var(--st-compacting-bg)">compact</span>
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

type Dress = { rail: string; tint: string; wash: string; title: string };
type Scene = { body: string; plain: Dress; tokens: { await: string; compact: string }; types: Record<string, Dress | null> };
/** The computed dress of every callout under #f, keyed by type; a type the renderer did not emit reads null. */
const READ = `(function (types) {
  var root = document.getElementById("f");
  var dress = function (el) {
    var cs = getComputedStyle(el), title = el.querySelector(".md-callout-title");
    return { rail: cs.borderLeftWidth, tint: cs.borderLeftColor, wash: cs.backgroundColor, title: title ? getComputedStyle(title).color : "" };
  };
  var out = {};
  for (var i = 0; i < types.length; i++) {
    var el = root.querySelector("blockquote.md-callout.md-callout-" + types[i]);
    out[types[i]] = el ? dress(el) : null;
  }
  return {
    body: getComputedStyle(root.querySelector(":scope > p")).color,
    plain: dress(root.querySelector("blockquote:not(.md-callout)")),
    tokens: { await: getComputedStyle(document.getElementById("tok-await")).color, compact: getComputedStyle(document.getElementById("tok-compact")).color },
    types: out,
  };
})`;

const THEMES: Array<[string, string]> = [["classic", ""], ["yatharth", "chat-theme-yatharth"], ["yatharth-light", "chat-theme-yatharth theme-light"]];
const TRANSPARENT = "rgba(0, 0, 0, 0)";

async function scene(browser: any, css: string, bodyClass: string): Promise<Scene> {
  const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => errors.push(e.message));
  await page.setContent(PAGE(css, bodyClass), { waitUntil: "load" });
  assert.deepEqual(errors, [], "the probe bundle ran clean");
  assert.deepEqual(await page.evaluate("window.__pageErrors"), [], "no script error on the page");
  const s = await page.evaluate(READ + "(" + JSON.stringify(TYPES) + ")") as Scene;
  await page.close();
  return s;
}

function assertDressed(s: Scene, where: string): void {
  for (const t of TYPES) assert.ok(s.types[t], where + ": the " + t + " callout rendered");
  for (const t of ALERTS) {
    const d = s.types[t]!;
    assert.equal(d.rail, "3px", where + ": the " + t + " callout wears the 3px rail (a 0px rail is an unresolved tint)");
    assert.notEqual(d.tint, s.body, where + ": the " + t + " callout's rail is tinted, not the body colour");
    assert.notEqual(d.tint, s.plain.tint, where + ": the " + t + " callout's rail is not the plain quote's hairline");
    assert.notEqual(d.wash, TRANSPARENT, where + ": the " + t + " callout has its wash");
    assert.equal(d.title, s.body, where + ": the " + t + " callout's title reads in the body's ink (the tint is the rail and the wash)");
    assert.notEqual(d.title, d.tint, where + ": the " + t + " callout's title is not painted in the rail's token");
  }
  const tints = ALERTS.map((t) => s.types[t]!.tint);
  assert.equal(new Set(tints).size, ALERTS.length, where + ": the five alerts wear five tints: " + tints.join(" | "));
  // the two status tokens the tip and important rules name resolve on this page, and the callouts read them
  assert.notEqual(s.tokens.await, s.body, where + ": --st-awaitbg-bg resolves on this page");
  assert.notEqual(s.tokens.compact, s.body, where + ": --st-compacting-bg resolves on this page");
  assert.equal(s.types.tip!.tint, s.tokens.await, where + ": tip is the awaiting green");
  assert.equal(s.types.important!.tint, s.tokens.compact, where + ": important is the compacting teal");
  // an unknown type keeps the hairline rail: dressed less than an alert, never less than a plain quote
  assert.equal(s.types.custom!.rail, "3px", where + ": an unknown type keeps the 3px hairline rail");
}

test("under feed.css, the tip and important callouts are tinted in every theme, as the other alerts are and as styles.css tints them", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const feed = await builtCss("feed.css"), styles = await builtCss("styles.css");
    for (const [theme, cls] of THEMES) {
      const f = await scene(browser, feed, cls), s = await scene(browser, styles, cls);
      assertDressed(f, "feed.css " + theme);
      assertDressed(s, "styles.css " + theme);
      for (const ty of TYPES) {
        assert.equal(f.types[ty]!.tint, s.types[ty]!.tint, theme + ": the " + ty + " callout is tinted alike under feed.css and styles.css");
        assert.equal(f.types[ty]!.wash, s.types[ty]!.wash, theme + ": the " + ty + " callout's wash matches across the sheets");
      }
    }
  });
});
