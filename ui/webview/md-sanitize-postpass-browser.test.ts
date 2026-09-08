// The sanitizer's DOM post-passes, in headless Chromium over the real modules (plans/markdown-viewer.md, Slice 1
// review, 2026-09-07). Two things a source pin cannot see:
//   • Math keeps its layout. KaTeX positions everything with inline style (a strut's height, a vlist row's top, a
//     radical's padding), and sanitizeMd keeps only colour in a `style` attribute, so KaTeX markup emitted by marked
//     and then sanitized came back flat: numerator and denominator on one line, the superscript at the baseline, the
//     radical a hairline. The chat's pipeline now sanitizes marked's inert placeholders and renders KaTeX into them
//     afterwards (math.ts renderMathPlaceholders); this leg runs that pipeline and MEASURES a fraction, a
//     superscript, a radical and a display sum, while an author's own `style` on the same message still loses
//     everything but its colour, and a hand-written placeholder gets only what KaTeX renders under trust: false.
//   • A checkbox an author writes by hand (not marked's `- [x]`) is forced `disabled`, and a real click leaves it
//     unchecked: the fixture the files browser leg renders has only marked's task items, which arrive disabled
//     already, so that leg passed with the forcing branch deleted.
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_DIST = path.join(EXT, "node_modules", "katex", "dist");
const KATEX_CSS = fs.readFileSync(path.join(KATEX_DIST, "katex.min.css"), "utf8");

// render.ts's md() minus the PR-link walk, over the real modules: the chat grammar on marked, sanitizeMd, then the
// math post-pass on the sanitized body, then the serialization to innerHTML. `renderMathPlaceholders?.` so the
// bundle also builds on a tree without the post-pass, where the pipeline is sanitize-only and the geometry
// assertions below show the collapse instead of an import error.
const ENTRY = `
import { marked } from "marked";
import { chatMdExtensions } from "./chat-md";
import { sanitizeMd } from "./md-sanitize";
import * as math from "./math";
marked.setOptions({ gfm: true, breaks: false });
marked.use(...chatMdExtensions);
const w = window as any;
w.__mdPipe = (src: string): string => {
  const clean = sanitizeMd(marked.parse(src) as string);
  (math as any).renderMathPlaceholders?.(clean);
  return clean.innerHTML;
};
w.__markedOnly = (src: string): string => marked.parse(src) as string;
w.__sanitizeOnly = (html: string): string => sanitizeMd(html).innerHTML;
`;

function bundleEntry(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: ENTRY, resolveDir: UI, loader: "ts", sourcefile: "md-sanitize-postpass-entry.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}

// a standards-mode page (KaTeX refuses quirks mode) with KaTeX's own sheet, its fonts served from the package
const PAGE_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${KATEX_CSS}</style></head><body>
<div id=out></div>
<script src=/dist/postpass.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (page: any, errors: string[]) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundleEntry();
    const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE_HTML });
      if (u.pathname === "/dist/postpass.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (u.pathname.startsWith("/fonts/")) {
        const f = path.join(KATEX_DIST, "fonts", path.basename(u.pathname));
        if (fs.existsSync(f)) return route.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => typeof (window as any).__mdPipe === "function", null, { timeout: 10000 });
    await page.evaluate(() => (document as any).fonts.ready);
    await body(page, errors);
  } finally {
    await browser.close();
  }
}

type Box = { top: number; bottom: number; height: number; width: number };

test("math keeps its KaTeX layout when rendered after the sanitizer, while an author's style still loses everything but colour", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (page, errors) => {
    const MSG = [
      "The ratio is $\\frac{a}{b}$ and $x^2$ and $\\sqrt{d}$ and $a<b$ here.",
      "",
      "$$\\sum_{i=0}^{n} i^2$$",
      "",
      'A <span class="fx-red" style="color: rgb(200, 0, 0); position: fixed; top: 0; font-size: 80px">red</span> word.',
      "",
    ].join("\n");
    // 1. what reaches the sanitizer is the placeholder, not KaTeX: no style attribute for the colour rule to strip
    const before = await page.evaluate((src: string) => {
      const w = window as any;
      const marked = w.__markedOnly(src) as string;
      const sanitized = w.__sanitizeOnly(marked) as string;
      return { markedHasKatex: /class="katex/.test(marked), markedStyles: (marked.match(/ style="/g) || []).length,
        sanitizedPlaceholders: (sanitized.match(/md-math-(inline|display)/g) || []).length, sanitizedStyles: (sanitized.match(/ style="/g) || []).length };
    }, MSG);
    assert.equal(before.markedHasKatex, false, "marked emits placeholders, never KaTeX markup");
    assert.equal(before.markedStyles, 1, "the one inline style in marked's output is the author's span; the math placeholders carry none");
    assert.equal(before.sanitizedPlaceholders, 5, "the five placeholders survive the sanitizer as spans/divs (4 inline + 1 display)");
    assert.equal(before.sanitizedStyles, 1, "the only style attribute left after the sanitizer is the author's colour");

    // 2. the full pipeline: render, then measure
    const facts = await page.evaluate((src: string) => {
      const out = document.getElementById("out") as HTMLElement;
      out.innerHTML = (window as any).__mdPipe(src);
      const box = (e: Element | null): Box | null => { if (!e) return null; const r = e.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height, width: r.width }; };
      const katex = Array.from(out.querySelectorAll(".katex")) as HTMLElement[];
      const frac = out.querySelector(".mfrac") as HTMLElement | null;
      const fracGlyphs = frac ? Array.from(frac.querySelectorAll(".mord.mathnormal")) as HTMLElement[] : [];
      const fracA = fracGlyphs.find((g) => g.textContent === "a") || null;
      const fracB = fracGlyphs.find((g) => g.textContent === "b") || null;
      const sup = katex[1] || null;
      const supBase = sup ? sup.querySelector(".mord.mathnormal") : null;
      const supScript = sup ? sup.querySelector(".msupsub .mord") : null;
      const sqrt = katex[2] || null;
      const svg = sqrt ? sqrt.querySelector("svg") : null;
      const sqrtRadicand = sqrt ? sqrt.querySelector(".mord.mathnormal") : null;
      const display = out.querySelector(".katex-display") as HTMLElement | null;
      const red = out.querySelector(".fx-red") as HTMLElement | null;
      return {
        placeholdersLeft: out.querySelectorAll(".md-math-inline, .md-math-display").length,
        katexCount: katex.length,
        katexStyled: out.querySelectorAll(".katex [style]").length,
        katexStrutStyle: (out.querySelector(".katex-strut") as HTMLElement | null)?.getAttribute("style") ?? null,
        inlineParent: katex[0] ? katex[0].parentElement?.tagName : null,
        fracA: box(fracA), fracB: box(fracB), fracText: frac ? frac.textContent : null,
        supBase: box(supBase), supScript: box(supScript),
        svg: box(svg), svgParentClass: svg ? svg.parentElement?.className : null, sqrtRadicand: box(sqrtRadicand),
        display: box(display), displayParentId: display ? display.parentElement?.id : null,
        inlineHeight: box(katex[0])?.height ?? null,
        relation: (out.querySelector(".mrel") as HTMLElement | null)?.textContent ?? null,
        redStyle: red ? red.getAttribute("style") : null,
        redPosition: red ? getComputedStyle(red).position : null,
        redFontSize: red ? getComputedStyle(red).fontSize : null,
        proseFontSize: red ? getComputedStyle(red.parentElement as HTMLElement).fontSize : null,
      };
    }, MSG);
    assert.equal(facts.placeholdersLeft, 0, "every placeholder was rendered and unwrapped");
    assert.equal(facts.katexCount, 5, "four inline formulas and the display sum");
    assert.ok(facts.katexStyled >= 10, "KaTeX's inline styles survive (the sanitizer never saw them): " + facts.katexStyled);
    assert.match(facts.katexStrutStyle || "", /height:/, "the strut keeps its height");
    assert.equal(facts.inlineParent, "P", "the .katex root stands where the placeholder stood, directly in the paragraph (no wrapper)");
    // the fraction is stacked: the numerator sits above the denominator
    assert.ok(facts.fracA && facts.fracB, "fraction glyphs a and b found: " + facts.fracText);
    assert.ok(facts.fracA!.top + 5 < facts.fracB!.top, "numerator a above denominator b: a@" + facts.fracA!.top + " b@" + facts.fracB!.top);
    // the superscript starts in the upper half of its base, not at the baseline
    assert.ok(facts.supBase && facts.supScript, "x^2 glyphs found");
    assert.ok(facts.supScript!.top < facts.supBase!.top + facts.supBase!.height / 2, "superscript raised: 2@" + facts.supScript!.top + " x@" + facts.supBase!.top + " h=" + facts.supBase!.height);
    // the radical is drawn (a real svg box), and the radicand sits inside its strut, not below it
    assert.ok(facts.svg, "\\sqrt draws an inline svg");
    assert.ok(facts.svg!.height > 5, "the radical svg has height: " + facts.svg!.height);
    assert.ok(facts.svg!.width > 5, "the radical svg has width: " + facts.svg!.width);
    assert.ok(facts.sqrtRadicand && facts.sqrtRadicand.top < facts.svg!.bottom, "the radicand sits under the radical, not under the line");
    // the display sum with limits is taller than an inline formula, and stands at block level
    assert.ok(facts.display, "$$..$$ renders as .katex-display");
    assert.ok(facts.display!.height > 35, "display sum with limits keeps its height: " + facts.display!.height + " (inline " + facts.inlineHeight + ")");
    assert.equal(facts.displayParentId, "out", "the display root stands at block level, no wrapper");
    // the TeX was escaped through the sanitizer: `a<b` renders its relation
    assert.equal(facts.relation, "<", "the < in the TeX reached KaTeX as a character");
    // and on the same message the author's own style keeps only its colour
    assert.equal(facts.redStyle, "color: rgb(200, 0, 0)");
    assert.equal(facts.redPosition, "static");
    assert.equal(facts.redFontSize, facts.proseFontSize, "font-size was dropped");

    // 3. a hand-written placeholder gets only what KaTeX renders from TeX under trust: false
    const hand = await page.evaluate(() => {
      const out = document.getElementById("out") as HTMLElement;
      out.innerHTML = (window as any).__mdPipe([
        '<span class="md-math-inline">\\href{javascript:alert(1)}{x}</span>',
        '<span class="md-math-display">\\htmlStyle{position:fixed;top:0;left:0}{y}</span>',
        '<span class="md-math-inline">\\includegraphics{https://example.test/p.png}</span>',
        '<span class="md-math-inline">\\htmlClass{ctx-menu}{z}</span>',
        "and bad TeX $\\frac{1}{$ here",
      ].join(" "));
      const positioned = Array.from(out.querySelectorAll("[style]")).filter((e) => /position/.test(e.getAttribute("style") || "")).length;
      return {
        anchorsOrImages: out.querySelectorAll("a, img").length,
        positioned,
        classCtx: out.querySelectorAll(".ctx-menu").length,
        katex: out.querySelectorAll(".katex").length,
        errors: out.querySelectorAll(".katex-error").length,
        placeholdersLeft: out.querySelectorAll(".md-math-inline, .md-math-display").length,
        text: out.textContent || "",
      };
    });
    assert.equal(hand.anchorsOrImages, 0, "\\href and \\includegraphics render no link and no image under trust: false");
    assert.equal(hand.positioned, 0, "\\htmlStyle adds no positioning");
    assert.equal(hand.classCtx, 0, "\\htmlClass adds no class an author could name");
    assert.equal(hand.katex, 4, "the four hand-written placeholders rendered (each as KaTeX's flagged unsupported command)");
    assert.equal(hand.errors, 1, "bad TeX is flagged in place as a bare .katex-error span (throwOnError: false), never thrown");
    assert.equal(hand.placeholdersLeft, 0, "no placeholder survives the pass");
    assert.deepEqual(errors, [], "no pageerror");
  });
});

test("a checkbox an author writes by hand is forced disabled: a real click leaves it unchecked", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (page, errors) => {
    const NOTE = [
      "- [x] done",
      "- [ ] later",
      "",
      '<input type="checkbox">',
      "",
      '<input type="CHECKBOX" checked>',
      "",
      '<input type="text" value="typed">',
      "",
    ].join("\n");
    const before = await page.evaluate((src: string) => {
      const out = document.getElementById("out") as HTMLElement;
      out.innerHTML = (window as any).__mdPipe(src);
      return Array.from(out.querySelectorAll("input")).map((i) => ({ type: i.getAttribute("type"), disabled: i.hasAttribute("disabled"), checked: (i as HTMLInputElement).checked }));
    }, NOTE);
    assert.equal(before.length, 4, "the text input is gone, the four checkboxes stay: " + JSON.stringify(before));
    assert.ok(before.every((i: { type: string | null }) => (i.type || "").toLowerCase() === "checkbox"));
    assert.ok(before.every((i: { disabled: boolean }) => i.disabled), "every checkbox is disabled, marked's and the author's alike: " + JSON.stringify(before));
    assert.deepEqual(before.map((i: { checked: boolean }) => i.checked), [true, false, false, true]);
    // a real mouse click on the author's raw checkbox (index 2) and on the checked one (index 3)
    const boxes = await page.evaluate(() => Array.from(document.querySelectorAll("#out input")).map((i) => { const r = i.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }));
    await page.mouse.click(boxes[2].x, boxes[2].y);
    await page.mouse.click(boxes[3].x, boxes[3].y);
    const after = await page.evaluate(() => Array.from(document.querySelectorAll("#out input")).map((i) => (i as HTMLInputElement).checked));
    assert.deepEqual(after, [true, false, false, true], "no checkbox toggled under a real click");
    assert.deepEqual(errors, [], "no pageerror");
  });
});
