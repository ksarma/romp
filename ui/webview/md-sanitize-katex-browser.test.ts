// What the math post-pass hands the chat is KaTeX's own output, untouched, in headless Chromium over the REAL modules
// (plans/markdown-viewer.md, Slice 1 review, 2026-09-07). The chat's md() is: marked with the chat grammar (chat-md.ts,
// math.ts), sanitizeMd (md-sanitize.ts), renderMathPlaceholders (math.ts) on the sanitized body, then innerHTML; userMd()
// the same over the breaks:true instance. KaTeX lays a formula out with inline `style` and inline <svg>, and sanitizeMd
// keeps only colour in a style attribute, so KaTeX output run THROUGH the sanitizer came back flat while the source pin
// that once stood for it (render-math.test.ts) stayed green. md-sanitize-postpass-browser.test.ts MEASURES the layout
// that survives (a fraction stacks, a superscript is raised, the radical has height, a display sum is taller than a
// line, an author's style beside it still loses everything but colour, hand-written placeholders under trust: false).
// This leg states the property behind those measurements once, exactly: the rendered .katex root is byte-identical to
// what katex.render produces on its own for the same TeX, so nothing of KaTeX's output passed through DOMPurify; and
// it covers what that leg does not run: the user bubble's path (userMd, newlines kept), an author's display
// placeholder and an empty one, and a second pass being a no-op. Skips LOUDLY without a playwright browser (CI
// installs none), as the other browser legs do. Synthetic values only.
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

// the chat's two renderers, rebuilt from the real modules exactly as render.ts composes them (md() and userMd()
// are not exported; render-math.test.ts pins render.ts to this order), plus KaTeX's own rendering for comparison
const ENTRY = `
import { Marked } from "marked";
import katex from "katex";
import { chatMdExtensions, userMdHtml } from "./chat-md";
import { sanitizeMd } from "./md-sanitize";
import { renderMathPlaceholders } from "./math";
const assistant = new Marked({ gfm: true, breaks: false }, ...chatMdExtensions);
function md(src: string): string { const clean = sanitizeMd(assistant.parse(src) as string); renderMathPlaceholders(clean); return clean.innerHTML; }
function userMd(src: string): string { const clean = sanitizeMd(userMdHtml(src)); renderMathPlaceholders(clean); return clean.innerHTML; }
function twice(src: string): { once: string; again: string } {
  const clean = sanitizeMd(assistant.parse(src) as string); renderMathPlaceholders(clean); const once = clean.innerHTML;
  renderMathPlaceholders(clean); return { once, again: clean.innerHTML };
}
// KaTeX's own output for the same TeX, by the same DOM path (katex.render into a fresh element, the browser serializing):
// renderToString differs in serialization only (no space after a colon, no empty class attribute), so it is not the reference
function direct(tex: string, display: boolean): string {
  const el = document.createElement("div"); katex.render(tex, el, { displayMode: display, throwOnError: false, output: "html", trust: false }); return el.innerHTML;
}
(window as any).__math = { md, userMd, twice, direct };
`;

function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: ENTRY, resolveDir: UI, loader: "ts" }, bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (page: any, errors: string[]) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    // KaTeX's sheet as styles.css imports it (fonts 404 here; the markup under test does not depend on them)
    await page.setContent(`<!DOCTYPE html><html><head><meta charset=utf-8><style>${KATEX_CSS}\nbody{font-size:16px}</style></head><body><div id=out></div></body></html>`);
    await page.addScriptTag({ content: bundle() });
    await body(page, errors);
  } finally {
    await browser.close();
  }
}

type Facts = { html: string; katex: number; display: number; placeholders: number; styled: number; inParagraph: boolean; atBlockLevel: boolean; exact: boolean };
/** Render `src` through the chat pipeline into #out and report: counts, where the rendered root stands (unwrapped, in
 *  the paragraph or at block level), and whether its markup equals what katex.render produces alone for `tex`. */
async function render(page: any, kind: "md" | "userMd", src: string, tex: string | null, display: boolean): Promise<Facts> {
  return page.evaluate(([kind, src, tex, display]: [string, string, string | null, boolean]) => {
    const M = (window as any).__math;
    const out = document.getElementById("out") as HTMLElement;
    out.innerHTML = M[kind](src);
    const root = out.querySelector(display ? ".katex-display" : ".katex") as HTMLElement | null;
    return {
      html: out.innerHTML,
      katex: out.querySelectorAll(".katex").length,
      display: out.querySelectorAll(".katex-display").length,
      placeholders: out.querySelectorAll(".md-math-inline, .md-math-display").length,
      styled: out.querySelectorAll(".katex [style]").length,
      inParagraph: !!root && !!root.parentElement && root.parentElement.tagName === "P",
      atBlockLevel: !!root && root.parentElement === out,
      exact: !!root && tex !== null && root.outerHTML === M.direct(tex, display),
    };
  }, [kind, src, tex, display]);
}

test("the math the chat renders after the sanitizer is KaTeX's own output, byte for byte, on both renderers", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (page, errors) => {
    // 1. inline: the .katex root stands in the paragraph where the placeholder stood, and its markup is exactly
    //    what katex.render produces alone, inline styles included: nothing of it passed through DOMPurify
    const frac = await render(page, "md", "a fraction $\\frac{a}{b}$ in prose", "\\frac{a}{b}", false);
    assert.equal(frac.katex, 1, "one formula: " + frac.html);
    assert.equal(frac.placeholders, 0, "the placeholder is unwrapped once rendered");
    assert.ok(frac.inParagraph, "the .katex root stands in the paragraph (the comment highlighter's closest('.katex') pairing)");
    assert.ok(frac.styled >= 4, "KaTeX's inline layout styles are all there: " + frac.styled);
    assert.ok(frac.exact, "byte-identical to katex.render's own output: " + frac.html);
    const sqrt = await render(page, "md", "norm grows like $\\sqrt{d}$ here.", "\\sqrt{d}", false);
    assert.ok(sqrt.exact && sqrt.html.includes("<svg"), "the radical's inline svg is KaTeX's own too: " + sqrt.html);

    // 2. display: a paragraph of its own becomes KaTeX's .katex-display at block level, unwrapped, identical
    const sum = await render(page, "md", "Total:\n\n$$\\sum_{i=1}^{n} x_i$$\n\nafter", "\\sum_{i=1}^{n} x_i", true);
    assert.equal(sum.display, 1, "one display formula: " + sum.html);
    assert.ok(sum.atBlockLevel && !sum.html.includes("md-math-display"), "the block form stands on its own, no wrapper: " + sum.html);
    assert.ok(sum.exact, "display markup is KaTeX's own: " + sum.html);

    // 3. the user bubble's path: the breaks:true instance renders the same math and keeps the typed newline
    const user = await render(page, "userMd", "Euler: $e^{i\\pi}+1=0$\nnext line", "e^{i\\pi}+1=0", false);
    assert.ok(user.exact, "userMd: the same KaTeX output: " + user.html);
    assert.match(user.html, /<br>\s*next line/, "userMd: the newline after the formula is still a <br>: " + user.html);

    // 4. an author's own placeholders: a display one renders display math, an empty one is dropped, none survives
    const hand = await render(page, "md", '<div class="md-math-display">\\frac{c}{d}</div>\n\nthen <span class="md-math-inline"></span> end', "\\frac{c}{d}", true);
    assert.equal(hand.display, 1, "an author's display placeholder renders display math: " + hand.html);
    assert.ok(hand.exact, "and it is KaTeX's own output for that TeX: " + hand.html);
    assert.equal(hand.placeholders, 0, "the empty placeholder is dropped, no placeholder left: " + hand.html);
    assert.match(hand.html, /<p>then\s+end<\/p>/, "the prose around the empty one reads on: " + hand.html);

    // 5. a second pass over the same DOM changes nothing: no placeholder survives the first
    const again = await page.evaluate(() => (window as any).__math.twice("$\\frac{a}{b}$ and $$\\sum_i x_i$$"));
    assert.equal(again.again, again.once, "renderMathPlaceholders is idempotent");

    assert.deepEqual(errors, [], "no page errors");
  });
});
