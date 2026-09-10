// The ink of KaTeX's flagged text where the token's page value does not hold (Slice 4 of plans/markdown-viewer.md, review
// round 2). renderMathPlaceholders (math.ts) hands KaTeX `--math-err` as its errorColor, and KaTeX writes it verbatim into
// an inline `color: var(--math-err)` on TWO shapes: the `span.katex-error` a syntax error renders as under throwOnError:
// false, and the glyph spans of an unsupported command (`\BROKEN`) inside a formula that otherwise renders, which sit in a
// plain `.katex` root with no `.katex-error` ancestor (KaTeX's formatUnsupportedCmd builds a colour node). The token's
// :root and body.theme-light values are tuned to --bg (md-config-math-error-colour.test.ts, theme-parity.test.ts); two
// surfaces paint another ground and re-scope it:
//  1. PRINT. The print block prints black on white; round 1 overrode the token on `.fileview-md .katex-error` alone, so the
//     second shape kept the screen's red on the white page: rgb(255, 106, 106) at 2.79:1 in the dark theme, light grey on a
//     black-and-white printer, beside a `span.katex-error` and a `code.md-math-src` that printed black. The override sits on
//     `.fileview-md` now (a custom property inherits, so it reaches both shapes' inline var()), in both sheets, and this leg
//     reads both shapes under print media over the real viewer bundle on the pane, the chat modal and the feed modal, in
//     both themes, with the kernel's THEME_CSS after the sheet as the kernel's pages have it.
//  2. THE PERSON'S OWN BUBBLE. `.user-bubble` paints `background: var(--you)`, a saturated fill, and the page's alarm red
//     read at 1.67:1 on it in the dark theme and 1.28:1 in the light theme, close to invisible, where the same formula in a
//     reply reads at 5.97:1 and 5.51:1. In the bubble the token is `currentColor`, the bubble's own ink (#ffffff: 4.67:1 dark,
//     5.13:1 light), the white family the bubble's code spans and bold wear; the span's title still carries KaTeX's message.
//     Read here through the chat's two renderers (the singleton under applyMdConfig for a reply, userMdHtml for the bubble,
//     each through sanitizeMd, as render.ts's md() and userMd() do), in both themes.
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic text only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, frames, requireCjs, REPORT, UI, EXT, type Mode } from "./real-viewer-leg";

const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const KERNEL = fs.readFileSync(path.resolve(EXT, "..", "kernel", "kernel.py"), "utf8");
const THEME_CSS = (/\nTHEME_CSS = """([\s\S]*?)"""/.exec(KERNEL) || [])[1] || "";
// an unsupported command inside a formula that renders, a syntax error, and a formula that parses
const MATH_TEXT = "Inline $x \\BROKEN y$ then a syntax error $\\frac{1}{2$ and a fine $x^2$ here.";
const NOTE = ["# Math", "", MATH_TEXT, ""].join("\n");
const BLACK = "rgb(0, 0, 0)";

type RGB = [number, number, number];
const rgb = (s: string): RGB => { const m = /rgba?\((\d+), (\d+), (\d+)/.exec(s); assert.ok(m, "a colour: " + s); return [+m![1], +m![2], +m![3]]; };
function lum(c: RGB): number {
  const ch = (x: number) => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
  return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2]);
}
function contrast(a: RGB, b: RGB): number {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// ── the sheets ─────────────────────────────────────────────────────────────────────────────────────

test("the print block re-scopes the token on .fileview-md, so both shapes print black, in both sheets; the bubble re-scopes it to its own ink", () => {
  for (const sheet of ["styles.css", "feed.css"]) {
    const css = read(sheet); const block = css.slice(css.indexOf("@media print {"));
    assert.ok(block.includes("\n  .fileview-md { --math-err: black; }\n"), sheet + ": the print block sets --math-err on .fileview-md (a custom property inherits: it reaches the inline var() on span.katex-error and on an unsupported command's glyphs alike)");
    assert.doesNotMatch(block, /\.katex-error \{ --math-err/, sheet + ": not on .katex-error alone, which misses an unsupported command's text inside a rendered formula");
  }
  assert.ok(read("styles.css").includes("\n.user-bubble.md { --math-err: currentColor; }\n"), "styles.css: KaTeX's flagged text in the person's bubble takes the bubble's own ink (the page's red read at 1.28:1 on the light fill)");
});

// ── print: both shapes, every surface, both themes ─────────────────────────────────────────────────

type Facts = Record<string, any>;
/** The two flagged shapes and a plain glyph under the viewer's body: their inline style, ancestry and computed ink. */
function mathFacts(): Facts {
  const cs = (e: Element) => getComputedStyle(e);
  const md = document.querySelector(".fileview-md")!;
  const broken = Array.from(md.querySelectorAll(".katex [style*='--math-err']")).filter((e) => !e.closest(".katex-error")) as HTMLElement[];
  const err = md.querySelector(".katex-error") as HTMLElement | null;
  const plain = Array.from(md.querySelectorAll(".katex .mord")).find((e) => !(e as HTMLElement).getAttribute("style")) as HTMLElement | null;
  const b0 = broken[0];
  return {
    matchesPrint: matchMedia("print").matches, katexRoots: md.querySelectorAll(".katex").length, brokenCount: broken.length,
    brokenText: broken.map((e) => e.textContent).join(""), brokenStyle: b0 ? b0.getAttribute("style") : null,
    brokenInErrorSpan: b0 ? !!b0.closest(".katex-error") : null, brokenColor: b0 ? cs(b0).color : null,
    errText: err ? err.textContent : null, errStyle: err ? err.getAttribute("style") : null, errColor: err ? cs(err).color : null,
    plainColor: plain ? cs(plain).color : null, mdColor: cs(md).color, bodyBg: cs(document.body).backgroundColor,
  };
}

test("under print media an unsupported command's text prints black, as the syntax-error span and the plain glyphs do, on the pane, the chat modal and the feed modal in both themes", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const cells: Array<[Mode, boolean]> = [["pane", false], ["pane", true], ["chat", false], ["feed", false], ["feed", true]];
    for (const [mode, light] of cells) {
      const cell = `${mode} ${light ? "light" : "dark"}`;
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: NOTE }, theme: THEME_CSS });
      if (light) { await page.evaluate(() => { document.body.classList.add("theme-light"); }); await frames(page, 2); }
      await page.waitForFunction(() => document.querySelectorAll(".fileview-md .katex").length >= 2 && !!document.querySelector(".fileview-md .katex-error"), null, { timeout: 10000 });
      await frames(page, 2);
      const screen = await page.evaluate(mathFacts) as Facts;
      assert.deepEqual(errors, [], cell + ": the viewer ran clean");
      assert.equal(screen.matchesPrint, false, cell + ": screen media first");
      assert.ok(screen.brokenCount > 0, cell + ": the unsupported command's glyphs carry the token inline (" + JSON.stringify(screen) + ")");
      assert.match(screen.brokenStyle, /var\(--math-err\)/, cell + ": ...as KaTeX's inline style");
      assert.equal(screen.brokenInErrorSpan, false, cell + ": ...inside a .katex root, not a .katex-error (the second shape)");
      assert.match(screen.brokenText, /\\BROKEN/, cell + ": the glyphs spell the command");
      assert.match(screen.errStyle, /var\(--math-err\)/, cell + ": the syntax-error span carries the token inline");
      assert.notEqual(screen.brokenColor, BLACK, cell + ": on screen the flagged text is not black");
      assert.equal(screen.brokenColor, screen.errColor, cell + ": on screen both shapes wear the same ink");

      await page.emulateMedia({ media: "print" }); await frames(page, 3);
      const pr = await page.evaluate(mathFacts) as Facts;
      assert.equal(pr.matchesPrint, true, cell + ": print media applied");
      assert.equal(pr.bodyBg, "rgb(255, 255, 255)", cell + ": the page prints white");
      assert.equal(pr.mdColor, BLACK, cell + ": the body prints black");
      assert.equal(pr.plainColor, BLACK, cell + ": a plain glyph prints black");
      assert.equal(pr.errColor, BLACK, cell + ": the syntax-error span prints black");
      assert.equal(pr.brokenColor, BLACK, cell + ": the unsupported command's text prints black too (was " + screen.brokenColor + ", " + contrast(rgb(screen.brokenColor), [255, 255, 255]).toFixed(2) + ":1 on the white page)");

      await page.emulateMedia({ media: "screen" }); await frames(page, 2);
      const back = await page.evaluate(mathFacts) as Facts;
      assert.equal(back.brokenColor, screen.brokenColor, cell + ": the screen ink returns under screen media");
      assert.equal(back.errColor, screen.errColor, cell + ": ...for the syntax-error span too");
      await page.close();
    }
  });
});

// ── the person's own bubble ────────────────────────────────────────────────────────────────────────

const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const STYLES = read("styles.css").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);
/** The chat's two renderers, minus the PR-reference walk (md-config-chat-styles-browser.test.ts's bundle). */
function chatBundle(): string {
  const contents = [
    'import { marked } from "marked";',
    'import { applyMdConfig } from "./md-config";',
    'import { sanitizeMd } from "./md-sanitize";',
    'import { userMdHtml } from "./chat-md";',
    "applyMdConfig();",
    "(window as any).__md = (s: string) => sanitizeMd(marked.parse(s) as string).innerHTML;",
    "(window as any).__userMd = (s: string) => sanitizeMd(userMdHtml(s)).innerHTML;",
  ].join("\n");
  const r = requireCjs("esbuild").buildSync({ bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
    stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "math-inks-probe.ts" } });
  return r.outputFiles[0].text;
}
const CHAT_PAGE = () => `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}</style></head><body>
<div id=content>
  <div class="turn turn-assistant"><div class="assistant md" id=a></div></div>
  <div class="turn turn-user"><div class="user-bubble md" id=u></div></div>
</div>
<script>window.__pageErrors=[];window.addEventListener("error",function(e){window.__pageErrors.push(String(e.message));});</script>
<script>${chatBundle()}</script>
<script>
  var text = ${JSON.stringify(MATH_TEXT)};
  document.getElementById("a").innerHTML = window.__md(text);
  document.getElementById("u").innerHTML = window.__userMd(text);
</script></body></html>`;

/** Under one root: the root's ink and painted ground, and each flagged shape's computed ink (null when absent). */
const READ_INKS = `(function (rootId) {
  var root = document.getElementById(rootId);
  function ground(el) { for (var n = el; n; n = n.parentElement) { var bg = getComputedStyle(n).backgroundColor; if (bg !== "rgba(0, 0, 0, 0)" && bg !== "transparent") return bg; } return getComputedStyle(document.body).backgroundColor; }
  var err = root.querySelector(".katex-error");
  var broken = Array.prototype.filter.call(root.querySelectorAll(".katex [style*='--math-err']"), function (e) { return !e.closest(".katex-error") && /BROKEN/.test(e.textContent); })[0] || null;
  var cs = getComputedStyle(root);
  return { katex: root.querySelectorAll(".katex").length, rootColor: cs.color, ground: ground(root),
    err: err ? { color: getComputedStyle(err).color, style: err.getAttribute("style"), text: err.textContent } : null,
    broken: broken ? { color: getComputedStyle(broken).color, style: broken.getAttribute("style"), text: broken.textContent } : null };
})`;
type Inks = { katex: number; rootColor: string; ground: string; err: { color: string; style: string; text: string } | null; broken: { color: string; style: string; text: string } | null };

test("in the person's own bubble KaTeX's flagged text wears the bubble's ink and clears 4.5:1 on the fill, in both themes, while a reply's keeps the page's token", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => errors.push(e.message));
    await page.setContent(CHAT_PAGE(), { waitUntil: "load" });
    assert.deepEqual(errors, [], "the probe bundle ran clean");
    assert.deepEqual(await page.evaluate("window.__pageErrors"), [], "no script error on the page");
    for (const theme of ["dark", "light"]) {
      if (theme === "light") await page.evaluate("document.body.classList.add('theme-light')");
      const u = await page.evaluate(READ_INKS + '("u")') as Inks;
      const a = await page.evaluate(READ_INKS + '("a")') as Inks;
      for (const [where, r] of [["the bubble", u], ["the reply", a]] as const) {
        assert.equal(r.katex, 2, theme + ", " + where + ": the fill ran (two formulas rendered)");
        assert.ok(r.err && r.broken, theme + ", " + where + ": both flagged shapes present: " + JSON.stringify(r));
        assert.match(r.err!.style, /var\(--math-err\)/, theme + ", " + where + ": the syntax-error span carries the token inline");
        assert.match(r.broken!.style, /var\(--math-err\)/, theme + ", " + where + ": the unsupported command's glyphs carry the token inline");
        for (const [shape, ink] of [["the syntax-error span", r.err!.color], ["the unsupported command's text", r.broken!.color]]) {
          const ratio = contrast(rgb(ink), rgb(r.ground));
          assert.ok(ratio >= 4.5, `${theme}, ${where}: ${shape} reads ${ink} on ${r.ground} at ${ratio.toFixed(2)}:1, under 4.5`);
        }
      }
      assert.equal(u.err!.color, u.rootColor, theme + ": the bubble's flagged span takes the bubble's own ink (currentColor)");
      assert.equal(u.broken!.color, u.rootColor, theme + ": ...and so does the unsupported command's text");
      assert.notEqual(u.ground, a.ground, theme + ": (the bubble paints its own fill)");
      assert.notEqual(a.err!.color, a.rootColor, theme + ": in a reply the flagged text is still flagged, an ink apart from the body's");
      assert.equal(a.err!.color, a.broken!.color, theme + ": ...the same token on both shapes");
      assert.notEqual(u.err!.color, a.err!.color, theme + ": the bubble's ink is not the page's red");
    }
    await page.close();
  });
});
