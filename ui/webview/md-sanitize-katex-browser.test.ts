// What the math post-pass hands the chat is KaTeX's own output, untouched, in headless Chromium over the REAL modules
// (plans/markdown-viewer.md, Slice 1 review, 2026-09-07). The chat's md() is: marked with the chat grammar (chat-md.ts,
// math.ts), then sanitizeMd (md-sanitize.ts), which itself runs renderMathPlaceholders (math.ts) on the sanitized body as
// a post-pass chat-md.ts registers at load (render.ts calls no fill of its own; render-math.test.ts pins that), then the
// PR-reference walk, then innerHTML; userMd() the same over the breaks:true instance. KaTeX lays a formula out with inline
// `style` and inline <svg>, and sanitizeMd keeps only colour in a style attribute, so KaTeX output run THROUGH the
// sanitizer came back flat while the source pin that once stood for it (render-math.test.ts) stayed green.
// md-sanitize-postpass-browser.test.ts MEASURES the layout that survives (a fraction stacks, a superscript is raised, the
// radical has height, a display sum is taller than a line, an author's style beside it still loses everything but colour,
// hand-written placeholders under trust: false).
// This leg states the property behind those measurements once, exactly: the rendered .katex root is byte-identical to
// what katex.render produces on its own for the same TeX, so nothing of KaTeX's output passed through DOMPurify; and
// it covers what that leg does not run: the user bubble's path (userMd, newlines kept), an author's display
// placeholder and an empty one, and a second pass being a no-op. The second test lays the source fallback out under the
// WHOLE of styles.css, in the user's bubble beside the assistant's .md: the postpass leg computes the fallback's dress
// from four lifted rules under a bare .md, and the bubble's own code rule, which outranks the dress rule, was outside
// that lift (review round 4). Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs
// do. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { MATH_SOURCE_CLASS } from "./math";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
// the chat's whole sheet for the dress test below, its one @import dropped: KaTeX's sheet is inlined in the head already,
// and a bare specifier fetched from about:blank resolves to nothing
const STYLES_CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace(/^@import [^\n]*\n/m, "");

// the chat's two renderers, rebuilt from the real modules exactly as render.ts composes them (md() and userMd()
// are not exported; render-math.test.ts pins render.ts to this order): marked with the chat grammar, then sanitizeMd,
// which runs the math fill itself (chat-md.ts registers renderMathPlaceholders as a sanitizeMd post-pass at load, so
// importing the grammar is what arms it; no call here by hand), plus KaTeX's own rendering for comparison
const ENTRY = `
import { Marked } from "marked";
import katex from "katex";
import { chatMdExtensions, userMdHtml } from "./chat-md";
import { sanitizeMd, registerMdPostPass } from "./md-sanitize";
import { renderMathPlaceholders, MATH_MAX_SIZE_EM, maxExpandFor } from "./math";
const assistant = new Marked({ gfm: true, breaks: false }, ...chatMdExtensions);
function md(src: string): string { return sanitizeMd(assistant.parse(src) as string).innerHTML; }
function userMd(src: string): string { return sanitizeMd(userMdHtml(src)).innerHTML; }
function twice(src: string): { once: string; again: string } {
  const clean = sanitizeMd(assistant.parse(src) as string); const once = clean.innerHTML;
  renderMathPlaceholders(clean); return { once, again: clean.innerHTML };
}
// the registry: a pass registered twice runs once per sanitize; a second pass runs too, after the sanitizer's own
function registry(): { runs: number; other: number; sawKatex: boolean } {
  let runs = 0, other = 0, sawKatex = false;
  const counting = (root: ParentNode) => { runs++; sawKatex = sawKatex || root.querySelectorAll(".katex").length > 0; };
  const second = () => { other++; };
  registerMdPostPass(counting); registerMdPostPass(counting); registerMdPostPass(second);
  sanitizeMd(assistant.parse("one $x$ formula") as string);
  return { runs, other, sawKatex };
}
// KaTeX's own output for the same TeX, by the same DOM path (katex.render into a fresh element, the browser serializing):
// renderToString differs in serialization only (no space after a colon, no empty class attribute), so it is not the reference.
// The options are the fill's happy-path call's (render-math.test.ts pins math.ts to them): KaTeX's two bounds included, since a
// size cap changes what a \\rule renders to; uncapped is the same call under KaTeX's defaults, the control that shows the bounds reach the call
function direct(tex: string, display: boolean): string {
  const el = document.createElement("div"); katex.render(tex, el, { displayMode: display, throwOnError: true, output: "html", trust: false, maxSize: MATH_MAX_SIZE_EM, maxExpand: maxExpandFor(tex) }); return el.innerHTML;
}
function uncapped(tex: string, display: boolean): string {
  const el = document.createElement("div"); katex.render(tex, el, { displayMode: display, throwOnError: false, output: "html", trust: false }); return el.innerHTML;
}
(window as any).__math = { md, userMd, twice, direct, uncapped, registry };
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

    // 6. the registry behind all of the above: a pass registered twice runs once per sanitize, a second pass runs as
    //    well, and each sees the body after the math fill registered before it (the fill is chat-md.ts's, at load)
    const reg = await page.evaluate(() => (window as any).__math.registry());
    assert.deepEqual(reg, { runs: 1, other: 1, sawKatex: true }, "registerMdPostPass: idempotent per function, every distinct pass runs, in registration order");

    // 7. KaTeX's bounds reach the call (review round 3): a rule that asks for 5,000 em renders byte-identical to katex.render
    //    under the fill's maxSize, and differs from the same call under KaTeX's defaults, where it is 5,000 em wide
    const rule = await render(page, "md", "a $\\rule{5000em}{5000em}$ b", "\\rule{5000em}{5000em}", false);
    assert.ok(rule.exact, "the rule is what katex.render gives under the fill's maxSize: " + rule.html);
    const bounds = await page.evaluate(() => { const M = (window as any).__math; return { capped: M.direct("\\rule{5000em}{5000em}", false), uncapped: M.uncapped("\\rule{5000em}{5000em}", false) }; });
    assert.notEqual(bounds.capped, bounds.uncapped, "the bound changes the output, so byte-identity above proves it reached the call");
    assert.ok(rule.html.includes("border-right-width: 50em") && !rule.html.includes("5000em"), "capped at 50 em: " + rule.html);

    assert.deepEqual(errors, [], "no page errors");
  });
});

type Dress = { color: string; line: string; style: string; deco: string } | null;
type DressFacts = { count: number; fallbackInline: Dress; authorInline: Dress; fallbackBlock: Dress; quote: Dress };

test("the source fallback in the user's own bubble wears the bubble's dim tier, not the white of a code span they typed, in both themes", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (page, errors) => {
    // an argument-repeating macro is shown as source before KaTeX sees it (math.ts macroBounds): the cheapest way past a
    // bound, and one a short typed formula can take. The same text in both roots, in both shapes, beside a code span the
    // author wrote and a quoted passage (the bubble's own dim tier, styles.css's .user-bubble blockquote rule).
    const dup = "\\def\\a#1{#1#1}\\a{x}";
    const src = "Formula $" + dup + "$ and `a code span` here.\n\n> quoted\n\n$$\n" + dup + "\n$$";
    const facts = await page.evaluate(([css, src, srcClass]: [string, string, string]) => {
      const M = (window as any).__math;
      const style = document.createElement("style"); style.textContent = css; document.head.appendChild(style);
      // the bubble as render.ts builds it (a div wearing user-bubble and md, in a user turn), and the assistant's .md
      document.body.innerHTML = '<div class="turn turn-user"><div id="ub" class="user-bubble md"></div></div><div class="turn turn-assistant"><div id="as" class="md"></div></div>';
      const ub = document.getElementById("ub") as HTMLElement, as = document.getElementById("as") as HTMLElement;
      ub.innerHTML = M.userMd(src); as.innerHTML = M.md(src);
      const cs = (root: Element, sel: string) => {
        const el = root.querySelector(sel); if (!el) return null;
        const s = getComputedStyle(el); return { color: s.color, line: s.textDecorationLine, style: s.textDecorationStyle, deco: s.textDecorationColor };
      };
      const read = (root: Element) => ({
        count: root.querySelectorAll("code." + srcClass).length,
        fallbackInline: cs(root, "p > code." + srcClass), authorInline: cs(root, "p > code:not(." + srcClass + ")"),
        fallbackBlock: cs(root, "pre > code." + srcClass), quote: cs(root, "blockquote"),
      });
      const out: Record<string, { bubble: any; assistant: any }> = {};
      for (const theme of ["dark", "theme-light"]) { document.body.className = theme === "dark" ? "" : theme; out[theme] = { bubble: read(ub), assistant: read(as) }; }
      return out;
    }, [STYLES_CSS, src, MATH_SOURCE_CLASS]) as Record<string, { bubble: DressFacts; assistant: DressFacts }>;
    for (const theme of ["dark", "theme-light"]) {
      const { bubble, assistant } = facts[theme];
      for (const [name, f] of [["bubble", bubble], ["assistant", assistant]] as const) {
        assert.equal(f.count, 2, theme + " " + name + ": the formula is shown as source in both shapes");
        assert.ok(f.fallbackInline && f.authorInline && f.fallbackBlock && f.quote, theme + " " + name + ": every element found: " + JSON.stringify(f));
        assert.deepEqual([f.fallbackInline!.line, f.fallbackInline!.style], ["underline", "dotted"], theme + " " + name + ": the fallback is dotted-underlined");
        assert.equal(f.authorInline!.line, "none", theme + " " + name + ": the author's code span is not");
      }
      // the assistant's .md: the code tone for the author's span, another colour for the fallback (the postpass leg names it)
      assert.notEqual(assistant.fallbackInline!.color, assistant.authorInline!.color, theme + ": in the assistant's .md the fallback is not the code tone");
      // the bubble: white-on-blue for a code span the user typed; the fallback wears the bubble's dim tier instead, the
      // blockquote's white tint, and so does its underline (var(--dim) grey sat near 1.7:1 on the fill, invisible)
      assert.equal(bubble.authorInline!.color, "rgb(255, 255, 255)", theme + ": a code span the user typed is white on the fill");
      assert.notEqual(bubble.fallbackInline!.color, bubble.authorInline!.color, theme + ": the fallback in the bubble is not dressed as a code span the user typed: " + JSON.stringify(bubble.fallbackInline));
      assert.equal(bubble.fallbackInline!.color, bubble.quote!.color, theme + ": it wears the bubble's dim tier, the quoted passage's tint: " + JSON.stringify({ fallback: bubble.fallbackInline, quote: bubble.quote }));
      assert.equal(bubble.fallbackInline!.deco, bubble.fallbackInline!.color, theme + ": the dotted underline wears the same tint, visible on the fill: " + JSON.stringify(bubble.fallbackInline));
      // the block shape stands in the bubble's page-coloured well (.user-bubble pre), where var(--dim) reads as it does in the .md
      assert.equal(bubble.fallbackBlock!.color, assistant.fallbackBlock!.color, theme + ": the block shape in the page-coloured well keeps the dim tier, as the assistant's does");
      assert.equal(bubble.fallbackBlock!.deco, bubble.fallbackBlock!.color, theme + ": and its underline with it");
    }
    assert.deepEqual(errors, [], "no page errors");
  });
});
