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
//   • One enormous formula cannot freeze the page. katex.render is synchronous on the main thread and its cost climbs
//     faster than the input past about 20,000 characters (a 100k-character sum took 6 to 17 s, 1M had not finished after
//     270 s), and no tokenizer bounds a formula, so the fill stops at MATH_TEX_MAX_CHARS and shows the TeX as source.
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { MATH_TEX_MAX_CHARS, MATH_TEX_BUDGET_CHARS, MATH_MAX_SIZE_EM, MATH_SOURCE_CLASS } from "./math";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_DIST = path.join(EXT, "node_modules", "katex", "dist");
const KATEX_CSS = fs.readFileSync(path.join(KATEX_DIST, "katex.min.css"), "utf8");

// render.ts's md() minus the PR-link walk, over the real modules: the chat grammar on marked (importing chat-md.ts
// registers the math fill as sanitizeMd's post-pass), sanitizeMd, then the serialization to innerHTML. No call to the
// fill here: the pipeline is exactly what every sanitizeMd caller in the chat bundle gets, and on a tree where the
// registration is missing the geometry assertions below show the collapse.
// `__sanitizeOnly` is the PROFILE alone (DOMPurify under MD_PURIFY with the style hook, no post-pass): what the sanitizer
// hands the fill, which sanitizeMd itself no longer exposes once the grammar's module has registered the fill.
const ENTRY = `
import { marked } from "marked";
import DOMPurify from "dompurify";
import { chatMdExtensions } from "./chat-md";
import { sanitizeMd, MD_PURIFY, installMdSanitizeHooks } from "./md-sanitize";
marked.setOptions({ gfm: true, breaks: false });
marked.use(...chatMdExtensions);
const w = window as any;
w.__mdPipe = (src: string): string => sanitizeMd(marked.parse(src) as string).innerHTML;
w.__markedOnly = (src: string): string => marked.parse(src) as string;
w.__sanitizeOnly = (html: string): string => { installMdSanitizeHooks(); return (DOMPurify.sanitize(html, { ...MD_PURIFY, RETURN_DOM: true }) as HTMLElement).innerHTML; };
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
    // 1. what reaches the sanitizer is the placeholder, not KaTeX: no style attribute for the colour rule to strip, and the
    //    profile alone (no post-pass) hands the placeholders on as the elements with text they are
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

test("a formula longer than MATH_TEX_MAX_CHARS is shown as its TeX source, so one enormous formula cannot freeze the page", { timeout: 60000 }, async (t) => {
  // The real pipeline over the three ways a formula reaches the fill: a $$ paragraph of its own (a block placeholder), an
  // inline $..$ (a span in the paragraph) and an author's hand-written placeholder, which no tokenizer sees. At the cap
  // KaTeX still renders; one character over, the source stands where the formula would have, as a code block for a
  // block placeholder and a code span in a paragraph, the TeX intact and the title saying why. The 200k-character case
  // is the freeze itself: before the cap it took about 20 s here, so the bound below is loose by orders of magnitude.
  await inBrowser(t, async (page, errors) => {
    const flat = (n: number) => "x+".repeat(Math.ceil(n / 2)).slice(0, n);
    const atCap = flat(MATH_TEX_MAX_CHARS), over = flat(MATH_TEX_MAX_CHARS + 1), big = flat(200000);
    const facts = await page.evaluate(([atCap, over, big]: [string, string, string]) => {
      const w = window as any;
      const out = document.getElementById("out") as HTMLElement;
      const run = (src: string): number => { const t0 = performance.now(); out.innerHTML = w.__mdPipe(src); return Math.round(performance.now() - t0); };
      const count = () => ({ katex: out.querySelectorAll(".katex").length, placeholders: out.querySelectorAll(".md-math-inline, .md-math-display").length, pre: out.querySelectorAll("pre").length, code: out.querySelectorAll("code").length });
      // 1. exactly at the cap: rendered
      run("Text\n\n$$\n" + atCap + "\n$$\n\nmore");
      const at = { ...count(), display: out.querySelectorAll(".katex-display").length };
      // 2. one over, a display paragraph of its own: a code block at block level, the TeX intact
      run("Text\n\n$$\n" + over + "\n$$\n\nmore");
      const pre = out.querySelector("pre");
      const block = { ...count(), codeInPre: pre?.firstElementChild?.tagName ?? null, text: pre?.textContent === over, title: pre?.getAttribute("title") ?? null, parentId: pre?.parentElement?.id ?? null };
      // 3. one over, inline in a sentence: a code span in the paragraph, the prose around it intact
      run("Total $" + over + "$ done.");
      const code = out.querySelector("p > code");
      const p = out.querySelector("p");
      const inline = { ...count(), text: code?.textContent === over, title: code?.getAttribute("title") ?? null, prose: (p?.textContent || "").startsWith("Total ") && (p?.textContent || "").endsWith(" done.") };
      // 4. an author's hand-written placeholder, ten times the cap: the same code span, in milliseconds
      const ms = run('<p>see <span class="md-math-inline">' + big + "</span> here</p>");
      const hand = { ...count(), text: out.querySelector("p > code")?.textContent === big, ms };
      return { at, block, inline, hand };
    }, [atCap, over, big]);
    assert.deepEqual(facts.at, { katex: 1, placeholders: 0, pre: 0, code: 0, display: 1 }, "at the cap the formula renders: " + JSON.stringify(facts.at));
    const why = new RegExp("^Not rendered: " + (MATH_TEX_MAX_CHARS + 1) + " characters of TeX; the limit is " + MATH_TEX_MAX_CHARS + "\\.$");
    assert.deepEqual({ ...facts.block, title: null }, { katex: 0, placeholders: 0, pre: 1, code: 1, codeInPre: "CODE", text: true, title: null, parentId: "out" }, "one over, block: a code block where the formula stood, its TeX intact: " + JSON.stringify({ ...facts.block, text: undefined }));
    assert.match(facts.block.title || "", why, "the block's title says why");
    assert.deepEqual({ ...facts.inline, title: null }, { katex: 0, placeholders: 0, pre: 0, code: 1, text: true, title: null, prose: true }, "one over, inline: a code span in the paragraph, the sentence intact: " + JSON.stringify({ ...facts.inline, text: undefined }));
    assert.match(facts.inline.title || "", why, "the span's title says why");
    assert.deepEqual({ ...facts.hand, ms: 0 }, { katex: 0, placeholders: 0, pre: 0, code: 1, text: true, ms: 0 }, "a hand-written placeholder over the cap is the same code span: " + JSON.stringify(facts.hand));
    assert.ok(facts.hand.ms < 5000, "200k characters of TeX cost milliseconds, not the seconds KaTeX would take: " + facts.hand.ms + " ms");
    assert.deepEqual(errors, [], "no pageerror");
  });
});

// ── review round 3: the bounds beyond one formula's length, run for real ─────────────────────────────────────────────
// The length cap measured the TeX as written, and three things it did not bound froze or reshaped the page: KaTeX expands
// `\def` and `\newcommand` bodies before layout (a 1,409-character formula was 200,000 of expansion and 20 s), the cap was
// per formula and a message of twenty near it blocked the page for 8 to 15 s, and KaTeX's default maxSize is Infinity, so
// `\rule{5000em}{5000em}` laid a 78,650 px square in the transcript. math.ts now hands katex.render a maxSize and a
// maxExpand computed from the formula's macro bodies, keeps a per-call total of the TeX it renders, and shows a formula
// whose macro repeats an argument as source before KaTeX sees it; the source fallback wears MATH_SOURCE_CLASS and the
// sheets dress it as unrendered source. Each is measured here over the real pipeline, with the bounds that matter to a
// reader (time, pixels, what rendered) and a generous margin for a loaded box.

/** The rules that dress the fallback and the code spans around it, lifted from styles.css by head (fileview-parity.test.ts
 *  holds feed.css byte-equal), plus the tokens they read, so the page computes what the chat page computes. */
function fallbackCss(): string {
  const css = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
  // each head at a line start: `.md :not(pre) > code {` is also the tail of the user bubble's selector list, whose rule is white text
  const rule = (head: string): string => { const at = css.indexOf("\n" + head) + 1; assert.ok(at > 0, head + " in styles.css"); return css.slice(at, css.indexOf("}", at) + 1); };
  return ":root{--dim:#b8b8b8;--code-fg:#e1c08d;--code-bg:rgba(217,119,87,0.10);--box-bg:rgba(255,255,255,0.03);--box-border:rgba(255,255,255,0.12);--mono:monospace}\n"
    + [".md :not(pre) > code {", ".md pre {", ".md pre code {", ".md code.md-math-src, .fileview-md code.md-math-src {"].map(rule).join("\n");
}

test("a macro bomb stops at once with KaTeX's own error, a macro that repeats an argument is shown as source, and a rule or a kern is capped at the column", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (page, errors) => {
    const long = "x+".repeat(500);                                                          // a 1,000-character body
    const bomb = "$$\\def\\a{" + long + "}" + "\\a".repeat(200) + "x$$";                    // 1,409 characters; 200,000 expanded; 20 s before
    const chain = "$$\\def\\a{" + long + "}\\def\\b{" + "\\a".repeat(10) + "}" + "\\b".repeat(20) + "x$$";   // 220 expansions; 22 s before
    const dup = "$\\def\\a#1{#1#1}\\a{\\a{\\a{\\a{\\a{\\a{\\a{\\a{\\a{" + "x+".repeat(2500) + "}}}}}}}}}$";   // 512 copies of 5,000 characters before
    const facts = await page.evaluate(([bomb, chain, dup, srcClass]: [string, string, string, string]) => {
      const w = window as any;
      const out = document.getElementById("out") as HTMLElement;
      const run = (src: string): number => { const t0 = performance.now(); out.innerHTML = w.__mdPipe(src); return Math.round(performance.now() - t0); };
      const err = () => { const e = out.querySelector(".katex-error"); return e ? (e.getAttribute("title") || "") : null; };
      const bombMs = run(bomb), bombErr = err(), bombKatex = out.querySelectorAll(".katex").length;
      const chainMs = run(chain), chainErr = err();
      const dupMs = run(dup);
      const dupCode = out.querySelector("p > code." + srcClass);
      const dupFacts = { code: !!dupCode, title: dupCode?.getAttribute("title") ?? null, katex: out.querySelectorAll(".katex").length, textLen: dupCode?.textContent?.length ?? 0 };
      // sizes: an inline rule and an inline kern, measured; the em is KaTeX's (its root is 1.21em of the 16px body here)
      run("before $\\rule{5000em}{5000em}$ after");
      const rule = (out.querySelector(".katex-rule") as HTMLElement | null)?.getBoundingClientRect();
      const em = parseFloat(getComputedStyle(out.querySelector(".katex") as HTMLElement).fontSize);
      run("$a\\kern{50000em}b$");
      const kern = (out.querySelector(".katex") as HTMLElement | null)?.getBoundingClientRect();
      return { bombMs, bombErr, bombKatex, chainMs, chainErr, dupMs, dupFacts, rule: rule ? { w: rule.width, h: rule.height } : null, em, kernW: kern ? kern.width : null };
    }, [bomb, chain, dup, MATH_SOURCE_CLASS]);
    assert.ok(facts.bombMs < 2000, "the 200-use bomb is stopped in well under the 20 s it took, on a loaded box too: " + facts.bombMs + " ms");
    assert.match(facts.bombErr || "", /Too many expansions/, "KaTeX's own visible error, the source shown in place: " + facts.bombErr);
    assert.equal(facts.bombKatex, 0, "nothing of the bomb rendered");
    assert.ok(facts.chainMs < 2000, "the nested chain is stopped the same way: " + facts.chainMs + " ms");
    assert.match(facts.chainErr || "", /Too many expansions/, "the chain: KaTeX's error too: " + facts.chainErr);
    assert.ok(facts.dupMs < 2000, "the argument-repeating macro never reaches KaTeX: " + facts.dupMs + " ms");
    assert.deepEqual({ ...facts.dupFacts, title: null }, { code: true, title: null, katex: 0, textLen: dup.length - 2 }, "a code span in the paragraph, the TeX intact: " + JSON.stringify(facts.dupFacts));
    assert.match(facts.dupFacts.title || "", /^Not rendered: a macro in this formula repeats one of its arguments/, "its title says why");
    assert.ok(facts.rule && facts.rule.w > 100 && facts.rule.w <= MATH_MAX_SIZE_EM * facts.em + 1 && facts.rule.h <= MATH_MAX_SIZE_EM * facts.em + 1,
      "the rule renders, capped at MATH_MAX_SIZE_EM ems each way (78,650 px before): " + JSON.stringify(facts.rule) + " at " + facts.em + " px/em");
    assert.ok(facts.kernW !== null && facts.kernW < MATH_MAX_SIZE_EM * facts.em + 3 * facts.em, "the kern is capped at the column (786,520 px before): " + facts.kernW + " px");
    assert.deepEqual(errors, [], "no pageerror");
  });
});

test("the cap is per message too: twenty formulas just under the length cap render five and show the rest as source within a bound, a short one after them still renders, and the fallback wears the sheets' dress", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (page, errors) => {
    const flat = (n: number) => "x+".repeat(Math.ceil(n / 2)).slice(0, n);
    const near = flat(MATH_TEX_MAX_CHARS - 10);
    const fits = Math.floor(MATH_TEX_BUDGET_CHARS / near.length);                            // how many of them the budget takes
    const src = Array.from({ length: 20 }, () => "$$\n" + near + "\n$$").join("\n\n") + "\n\nlast $x$ and `a code span` here.";
    const over = flat(MATH_TEX_MAX_CHARS + 1);
    const facts = await page.evaluate(([src, srcClass, css, over]: [string, string, string, string]) => {
      const w = window as any;
      const out = document.getElementById("out") as HTMLElement;
      const t0 = performance.now(); out.innerHTML = w.__mdPipe(src); const ms = Math.round(performance.now() - t0);
      const display = out.querySelectorAll(".katex-display").length;
      const inline = Array.from(out.querySelectorAll(".katex")).filter((k) => !k.closest(".katex-display")).length;
      const shown = Array.from(out.querySelectorAll("pre > code." + srcClass));
      const titles = Array.from(new Set(shown.map((c) => c.parentElement?.getAttribute("title") || "")));
      const prose = (out.lastElementChild as HTMLElement | null)?.textContent || "";
      // the dress: the sheets' rules over the page, the fallback beside an author's code span, both shapes
      const style = document.createElement("style"); style.textContent = css; document.head.appendChild(style);
      out.className = "md";
      out.innerHTML = w.__mdPipe("Total $" + over + "$ and `a code span` here.\n\n$$\n" + over + "\n$$\n\n```\nfenced\n```");
      const cs = (el: Element | null) => { if (!el) return null; const s = getComputedStyle(el); return { color: s.color, line: s.textDecorationLine, style: s.textDecorationStyle, font: s.fontFamily }; };
      const fallbackInline = cs(out.querySelector("p > code." + srcClass)), authorInline = cs(out.querySelector("p > code:not(." + srcClass + ")"));
      const fallbackBlock = cs(out.querySelector("pre > code." + srcClass)), authorBlock = cs(out.querySelector("pre > code:not(." + srcClass + ")"));
      return { ms, display, inline, shown: shown.length, titles, prose, fallbackInline, authorInline, fallbackBlock, authorBlock };
    }, [src, MATH_SOURCE_CLASS, fallbackCss(), over]);
    assert.equal(fits, 5, "the budget takes five formulas at ten under the cap (the constant's reason: five caps' worth)");
    assert.equal(facts.display, fits, "the first five render: " + JSON.stringify({ display: facts.display, shown: facts.shown }));
    assert.equal(facts.shown, 20 - fits, "the other fifteen are code blocks carrying their TeX");
    assert.deepEqual(facts.titles, ["Not rendered: the formulas above already total " + fits * near.length + " characters of TeX; the limit for one message or note is " + MATH_TEX_BUDGET_CHARS + "."], "every one titled with the total and the limit");
    assert.equal(facts.inline, 1, "a short formula after them still fits the budget and renders");
    assert.ok(facts.prose.startsWith("last ") && facts.prose.includes("a code span"), "the prose after the formulas is intact: " + facts.prose);
    assert.ok(facts.ms < 20000, "the whole message renders within a bound where twenty rendered formulas took 8 to 15 s of render and layout: " + facts.ms + " ms");
    // the dress: dim and dotted-underlined where an author's code span keeps the code tone and no underline, in both shapes
    for (const [name, fb, au] of [["inline", facts.fallbackInline, facts.authorInline], ["block", facts.fallbackBlock, facts.authorBlock]] as const) {
      assert.ok(fb && au, name + ": both elements found");
      assert.deepEqual([fb!.line, fb!.style], ["underline", "dotted"], name + ": the fallback is dotted-underlined: " + JSON.stringify(fb));
      assert.equal(au!.line, "none", name + ": the author's code span is not: " + JSON.stringify(au));
      assert.equal(fb!.color, "rgb(184, 184, 184)", name + ": the fallback wears the dim tier: " + JSON.stringify(fb));
      assert.equal(au!.color, "rgb(225, 192, 141)", name + ": the author's keeps the code tone: " + JSON.stringify(au));
      assert.equal(fb!.font, au!.font, name + ": the same mono face: the fallback is still source");
    }
    assert.deepEqual(errors, [], "no pageerror");
  });
});
