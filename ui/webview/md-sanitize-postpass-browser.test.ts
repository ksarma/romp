// The chat's markdown pipeline in headless Chromium over the real modules: marked with the chat grammar (chat-md.ts,
// math.ts), then sanitizeMd (md-sanitize.ts), which runs renderMathPlaceholders as the post-pass chat-md.ts registers
// at load; userMd the same over the breaks:true instance. This is md() and userMd() as render.ts composes them,
// minus the PR-reference walk (render-math.test.ts and chat-md.test.ts pin render.ts to that order).
// What a source pin cannot see, and this leg measures:
//   • Math keeps its layout. KaTeX positions everything with inline style (a strut's height, a vlist row's top, a
//     radical's padding), and sanitizeMd keeps only colour in a `style` attribute, so KaTeX markup emitted by marked
//     and then sanitized would come back flat. The extensions emit an inert placeholder instead and KaTeX renders
//     into it after the sanitize: a fraction stacks, a superscript is raised, the radical has height, a display sum
//     stands at block level, and the rendered root is katex.render's own output byte for byte, so nothing of it
//     passed through DOMPurify. An author's own `style` beside the math still loses everything but its colour.
//   • A hand-written placeholder gets only what KaTeX renders under the fill's options: no link from \href, no image
//     (trust: false, KaTeX's own default, spelled out in math.ts and pinned by render-math.test.ts).
//   • An author's <style>, <form> and <button> in a message are gone, an author's id is prefixed, a checkbox written
//     by hand is forced disabled and a click leaves it unchecked.
//   • The registry: a pass registered twice runs once per sanitize; a second run of the fill is a no-op.
//   • One enormous formula cannot freeze the page. katex.render is synchronous on the main thread and its cost climbs
//     faster than the input past about 20,000 characters (a 100k-character sum took 6 to 17 s, 1M had not finished after
//     270 s), and no tokenizer bounds a formula, so the fill stops at MATH_TEX_MAX_CHARS and shows the TeX as source; the
//     three legs at the end run that bound, the macro bounds and the per-message budget for real (plans/markdown-viewer.md,
//     Slice 1 review rounds 3 to 5).
// Skips with a stated reason when no playwright browser is installed (CI installs none; tests/test_spend_modal_headless.py
// is the precedent, skipping without a playwright install). Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { MATH_TEX_MAX_CHARS, MATH_TEX_BUDGET_CHARS, MATH_MAX_SIZE_EM, MATH_SOURCE_CLASS } from "./math";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_DIST = path.join(EXT, "node_modules", "katex", "dist");
const KATEX_CSS = fs.readFileSync(path.join(KATEX_DIST, "katex.min.css"), "utf8");

const ENTRY = `
import { marked } from "marked";
import katex from "katex";
import { chatMdExtensions, userMdHtml } from "./chat-md";
import { sanitizeMd, registerMdPostPass } from "./md-sanitize";
import { renderMathPlaceholders } from "./math";
marked.setOptions({ gfm: true, breaks: false });
marked.use(...chatMdExtensions);
function md(src: string): string { return sanitizeMd(marked.parse(src) as string).innerHTML; }
function userMd(src: string): string { return sanitizeMd(userMdHtml(src)).innerHTML; }
function markedOnly(src: string): string { return marked.parse(src) as string; }
// KaTeX's own output for the same TeX by the same DOM path (katex.render into a fresh element, the browser serializing),
// under the options the fill uses
function direct(tex: string, display: boolean): string {
  const el = document.createElement("div"); katex.render(tex, el, { displayMode: display, throwOnError: false, output: "html", trust: false }); return el.innerHTML;
}
function twice(src: string): { once: string; again: string } {
  const clean = sanitizeMd(marked.parse(src) as string); const once = clean.innerHTML;
  renderMathPlaceholders(clean); return { once, again: clean.innerHTML };
}
// the registry: a pass registered twice runs once per sanitize; a second pass runs too, after the fill
function registry(): { runs: number; other: number; sawKatex: boolean } {
  let runs = 0, other = 0, sawKatex = false;
  const counting = (root: ParentNode) => { runs++; sawKatex = sawKatex || root.querySelectorAll(".katex").length > 0; };
  const second = () => { other++; };
  registerMdPostPass(counting); registerMdPostPass(counting); registerMdPostPass(second);
  sanitizeMd(marked.parse("one $x$ formula") as string);
  return { runs, other, sawKatex };
}
(window as any).__pipe = { md, userMd, markedOnly, direct, twice, registry };
`;

function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: ENTRY, resolveDir: UI, loader: "ts", sourcefile: "md-sanitize-postpass-entry.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}

// a standards-mode page (KaTeX refuses quirks mode) with KaTeX's own sheet, its fonts served from the package
const PAGE_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${KATEX_CSS}\nbody{font-size:16px}</style></head><body>
<div id=out></div>
<script src=/dist/postpass.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (page: any, errors: string[]) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this machine; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
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
    await page.waitForFunction(() => typeof (window as any).__pipe === "object", null, { timeout: 10000 });
    await page.evaluate(() => (document as any).fonts.ready);
    await body(page, errors);
  } finally {
    await browser.close();
  }
}

type Box = { top: number; bottom: number; height: number; width: number };

test("math keeps its KaTeX layout when rendered after the sanitizer, and is KaTeX's own output byte for byte; an author's style beside it keeps only its colour", { timeout: 60000 }, async (t) => {
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
      const marked = (window as any).__pipe.markedOnly(src) as string;
      return { markedHasKatex: /class="katex/.test(marked), markedStyles: (marked.match(/ style="/g) || []).length,
        placeholders: (marked.match(/md-math-(inline|display)/g) || []).length };
    }, MSG);
    assert.equal(before.markedHasKatex, false, "marked emits placeholders, never KaTeX markup");
    assert.equal(before.markedStyles, 1, "the one inline style in marked's output is the author's span; the math placeholders carry none");
    assert.equal(before.placeholders, 5, "five placeholders (4 inline + 1 display)");

    // 2. the full pipeline: render, then measure
    const facts = await page.evaluate((src: string) => {
      const P = (window as any).__pipe;
      const out = document.getElementById("out") as HTMLElement;
      out.innerHTML = P.md(src);
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
      const display = out.querySelector(".katex-display") as HTMLElement | null;
      const red = out.querySelector(".fx-red") as HTMLElement | null;
      const line = red ? red.parentElement as HTMLElement : null;
      return {
        placeholdersLeft: out.querySelectorAll(".md-math-inline, .md-math-display").length,
        katexCount: katex.length,
        katexStyled: out.querySelectorAll(".katex [style]").length,
        inlineParent: katex[0] ? katex[0].parentElement?.tagName : null,
        fracA: box(fracA), fracB: box(fracB),
        supBase: box(supBase), supScript: box(supScript),
        svg: box(svg),
        display: box(display), displayParentId: display ? display.parentElement?.id : null, displayInParagraph: display ? !!display.closest("p") : null,
        exactFrac: katex[0] ? katex[0].outerHTML === P.direct("\\frac{a}{b}", false) : false,
        exactDisplay: display ? display.outerHTML === P.direct("\\sum_{i=0}^{n} i^2", true) : false,
        redStyle: red ? red.getAttribute("style") : null,
        redPosition: red ? getComputedStyle(red).position : null,
        redFontSize: red ? getComputedStyle(red).fontSize : null,
        lineFontSize: line ? getComputedStyle(line).fontSize : null,
        ltEscaped: (out.textContent || "").includes("a<b"),
      };
    }, MSG);
    assert.equal(facts.placeholdersLeft, 0, "every placeholder was rendered and unwrapped");
    assert.equal(facts.katexCount, 5, "five formulas rendered");
    assert.ok(facts.katexStyled >= 10, "KaTeX's inline layout styles are all there: " + facts.katexStyled);
    assert.equal(facts.inlineParent, "P", "an inline formula's .katex root stands in the paragraph where the placeholder stood");
    assert.ok(facts.fracA && facts.fracB && facts.fracA.bottom <= facts.fracB.top + 1, "the fraction stacks: the numerator sits above the denominator: " + JSON.stringify([facts.fracA, facts.fracB]));
    assert.ok(facts.supBase && facts.supScript && facts.supScript.top < facts.supBase.top, "the superscript is raised above its base: " + JSON.stringify([facts.supBase, facts.supScript]));
    assert.ok(facts.svg && facts.svg.height > 5 && facts.svg.width > 5, "the radical's stretchy glyph has a box: " + JSON.stringify(facts.svg));
    assert.ok(facts.display && facts.display.height > 20, "the display sum is taller than a line: " + JSON.stringify(facts.display));
    assert.equal(facts.displayParentId, "out", "the display formula stands at block level, unwrapped");
    assert.equal(facts.displayInParagraph, false);
    assert.ok(facts.exactFrac, "the inline formula is katex.render's own output byte for byte: nothing of it passed through DOMPurify");
    assert.ok(facts.exactDisplay, "and so is the display one");
    assert.equal(facts.redStyle, "color: rgb(200, 0, 0)", "the author's span keeps only its colour declaration");
    assert.equal(facts.redPosition, "static");
    assert.equal(facts.redFontSize, facts.lineFontSize, "font-size: 80px was dropped");
    assert.ok(facts.ltEscaped, "a formula's `<` is text, never markup");
    assert.deepEqual(errors, [], "no page errors");
  });
});

test("a hand-written placeholder renders under the fill's options (no link from \\href), an empty one is unwrapped, and the user's own words take the same path", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (page, errors) => {
    const facts = await page.evaluate(() => {
      const P = (window as any).__pipe;
      const out = document.getElementById("out") as HTMLElement;
      out.innerHTML = P.md('hand <span class="md-math-inline">\\href{javascript:alert(1)}{x}</span> and <span class="md-math-inline"> </span> empty\n\n<div class="md-math-display">\\int_0^1 f</div>');
      const hand = { katex: out.querySelectorAll(".katex").length, anchors: out.querySelectorAll("a").length, hasJs: out.innerHTML.includes("javascript:"),
        placeholders: out.querySelectorAll(".md-math-inline, .md-math-display").length, display: out.querySelectorAll(".katex-display").length,
        text: out.textContent };
      out.innerHTML = P.userMd("Euler: $e^{i\\pi}+1=0$\nnext line");
      const user = { katex: out.querySelectorAll(".katex").length, br: out.querySelectorAll("br").length, placeholders: out.querySelectorAll(".md-math-inline").length };
      const t = P.twice("a $x^2$ b");
      return { hand, user, twiceSame: t.once === t.again, twiceKatex: (t.once.match(/class="katex"/g) || []).length };
    });
    assert.equal(facts.hand.katex, 2, "the two non-empty hand-written placeholders rendered (KaTeX flags the untrusted command in red)");
    assert.equal(facts.hand.anchors, 0, "\\href mints no link under the fill's options (trust: false, which is also KaTeX's default)");
    assert.equal(facts.hand.hasJs, false, "and the URL is nowhere in the markup");
    assert.equal(facts.hand.placeholders, 0, "no placeholder is left, the empty one included");
    assert.equal(facts.hand.display, 1, "the hand-written display placeholder renders in display mode");
    assert.ok((facts.hand.text || "").includes("empty"), "the empty placeholder's neighbours are intact");
    assert.equal(facts.user.katex, 1, "the user's own words render math through the same fill");
    assert.equal(facts.user.br, 1, "and keep their line break");
    assert.equal(facts.user.placeholders, 0);
    assert.ok(facts.twiceSame, "a second run of the fill over the same body is a no-op");
    assert.equal(facts.twiceKatex, 1);
    assert.deepEqual(errors, [], "no page errors");
  });
});

test("a message's own <style>, form and controls are gone, its ids are prefixed, and a hand-written checkbox is inert", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (page, errors) => {
    const facts = await page.evaluate(() => {
      const P = (window as any).__pipe;
      const out = document.getElementById("out") as HTMLElement;
      // the <style> comes AFTER a block: a document that OPENS with <style> has it hoisted into <head> by the HTML
      // parser, and DOMPurify hands back the <body>, so the case would pass with style allowed; here the sanitizer
      // is what removes it
      const src = [
        '<p id="top">top</p>',
        "",
        "<style>#out { display: none }</style>",
        "",
        '<form action="https://example.invalid/go"><button>Go</button></form>',
        "",
        "- [x] done",
        "",
        '<input type="checkbox" class="fx-hand"> <input type="text" class="fx-text">',
      ].join("\n");
      const dirty = P.markedOnly(src) as string;
      out.innerHTML = P.md(src);
      const hand = out.querySelector(".fx-hand") as HTMLInputElement | null;
      if (hand) hand.click();
      return {
        dirtyHasStyle: /<style>#out \{ display: none \}<\/style>/.test(dirty) && dirty.indexOf("<style>") > dirty.indexOf("<p id=\"top\">"),
        forbidden: out.querySelectorAll("style, form, button").length,
        outDisplay: getComputedStyle(out).display,
        goText: (out.textContent || "").includes("Go"),
        prefixed: out.querySelectorAll("p#user-content-top").length,
        raw: out.querySelectorAll("#top").length,
        task: out.querySelectorAll('li input[type="checkbox"][disabled]:checked').length,
        handDisabled: hand ? hand.disabled : null,
        handChecked: hand ? hand.checked : null,
        textInputs: out.querySelectorAll(".fx-text, input[type=text]").length,
      };
    });
    assert.ok(facts.dirtyHasStyle, "precondition: marked hands the sanitizer the <style>, after the paragraph");
    assert.equal(facts.forbidden, 0, "no style, form or button in the rendered message");
    assert.notEqual(facts.outDisplay, "none", "the message's <style> did not hide the transcript");
    assert.ok(facts.goText, "the button's text stays as prose");
    assert.equal(facts.prefixed, 1, "the author's id is prefixed user-content-");
    assert.equal(facts.raw, 0);
    assert.equal(facts.task, 1, "marked's task checkbox survives, disabled and ticked");
    assert.equal(facts.handDisabled, true, "a checkbox written by hand is forced disabled");
    assert.equal(facts.handChecked, false, "and a click leaves it unchecked");
    assert.equal(facts.textInputs, 0, "a text input does not survive");
    assert.deepEqual(errors, [], "no page errors");
  });
});

test("the post-pass registry: a pass registered twice runs once per sanitize, after the math fill", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (page, errors) => {
    const r = await page.evaluate(() => (window as any).__pipe.registry());
    assert.equal(r.runs, 1, "the counting pass ran once for one sanitize, though registered twice");
    assert.equal(r.other, 1, "the second pass ran too");
    assert.equal(r.sawKatex, true, "and by then the math fill had run: the passes see rendered math");
    assert.deepEqual(errors, [], "no page errors");
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
      const run = (src: string): number => { const t0 = performance.now(); out.innerHTML = w.__pipe.md(src); return Math.round(performance.now() - t0); };
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
// sheets dress it as unrendered source. Since review round 5 a macro definer is read by its token alone, whatever names the
// macro, and KaTeX's own expansion stop wears the same fallback. Each is measured here over the real pipeline, with the
// bounds that matter to a reader (time, pixels, what rendered) and a generous margin for a loaded box.

/** The rules that dress the fallback and the code spans around it, lifted from styles.css by head (fileview-parity.test.ts
 *  holds feed.css byte-equal), plus the tokens they read, so the page computes what the chat page computes. */
function fallbackCss(): string {
  const css = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
  // each head at a line start: `.md :not(pre) > code {` is also the tail of the user bubble's selector list, whose rule is white text
  const rule = (head: string): string => { const at = css.indexOf("\n" + head) + 1; assert.ok(at > 0, head + " in styles.css"); return css.slice(at, css.indexOf("}", at) + 1); };
  return ":root{--dim:#b8b8b8;--code-fg:#e1c08d;--code-bg:rgba(217,119,87,0.10);--box-bg:rgba(255,255,255,0.03);--box-border:rgba(255,255,255,0.12);--mono:monospace}\n"
    + [".md :not(pre) > code {", ".md pre {", ".md pre code {", ".md code.md-math-src, .fileview-md code.md-math-src {"].map(rule).join("\n");
}

type MacroCase = { name: string; src: string; expect: "stop" | "repeat" | "expanded" | "renders" | "error" };

test("every macro bound wears the source fallback (a bomb under any name, an argument repeated, an \\edef body, KaTeX's expansion stop), ordinary macro use and a syntax error render as on main, and a rule or a kern is capped at the column", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (page, errors) => {
    const long = "x+".repeat(500);                                                          // a 1,000-character body
    const body20 = "a".repeat(20);
    // each case: the message, and what the fill must make of it. `stop` is KaTeX's expansion stop under the computed count,
    // shown as source with the reason (review round 5; KaTeX's red text stood there before); `repeat` and `expanded` are the
    // two rules a formula meets before KaTeX; `renders` is one .katex root and nothing else; `error` is KaTeX's own red span
    // for a syntax error, as on main. Every case is handled in well under the seconds the bombs took, on a loaded box too.
    const cases: MacroCase[] = [
      { name: "the 200-use bomb", src: "$$\\def\\a{" + long + "}" + "\\a".repeat(200) + "x$$", expect: "stop" },        // 1,409 characters; 200,000 expanded; 20 s before round 3
      { name: "the nested chain", src: "$$\\def\\a{" + long + "}\\def\\b{" + "\\a".repeat(10) + "}" + "\\b".repeat(20) + "x$$", expect: "stop" },   // 220 expansions; 22 s before
      { name: "an argument repeated", src: "$\\def\\a#1{#1#1}\\a{\\a{\\a{\\a{\\a{\\a{\\a{\\a{\\a{" + "x+".repeat(2500) + "}}}}}}}}}$", expect: "repeat" },   // 512 copies of 5,000 characters before
      // \edef stores its body EXPANDED (review round 4): ten uses of a 20-character \a is a 200-character \b, charged once at the
      // definition and one expansion per use whatever its length, so 788 uses passed the count computed from the bodies as
      // written (20 characters: KaTeX's default) and laid 157,600 characters of formula, 31 s of freeze over this pipeline
      { name: "the \\edef bomb", src: "$$\\def\\a{" + body20 + "}\\edef\\b{" + "\\a".repeat(10) + "}" + "\\b".repeat(788) + " x$$", expect: "expanded" },   // the space keeps `\bx` from reading as one command
      // review round 5: a definer is read by its token alone, whatever names the macro (KaTeX's \def takes any next token but
      // `\ { } $ & # ^ _` as the name); the scan once required a word boundary after the definer, which `\def1` has not, and
      // both bombs above returned under a digit name at KaTeX's default count
      { name: "the bomb under a digit name", src: "$$\\def1{" + long + "}" + "1".repeat(200) + "x$$", expect: "stop" },
      { name: "the \\edef bomb under a digit name", src: "$$\\def\\a{" + body20 + "}\\edef1{" + "\\a".repeat(10) + "}" + "1".repeat(788) + " x$$", expect: "expanded" },
      { name: "a digit aliased to the bomb's macro", src: "$$\\def\\a{" + long + "}\\let1=\\a " + "1".repeat(200) + "x$$", expect: "stop" },
      { name: "\\global in front", src: "$$\\global\\def\\a{" + long + "}" + "\\a".repeat(200) + "x$$", expect: "stop" },
      { name: "a control symbol as the name", src: "$$\\def\\!{" + long + "}" + "\\!".repeat(200) + "x$$", expect: "stop" },
      // \let aliasing \def puts the body wherever a use of the alias is: read as the group after \def, `{a}` stood in for it
      { name: "\\def aliased behind a decoy group", src: "$$\\let\\d\\def \\frac{a}{b} \\d\\b{" + long + "}" + "\\b".repeat(200) + "x$$", expect: "stop" },
      // the count over-approximates a long linear body used many times (review round 4): plain KaTeX renders this one, and
      // the fill shows it as source with the reason, where it left KaTeX's red text before (review round 5)
      { name: "a 200-character body used 150 times", src: "$$\\def\\Q{" + "a+b+".repeat(50) + "}" + "\\Q".repeat(150) + "x$$", expect: "stop" },
      { name: "ordinary macro use", src: "$$\\newcommand{\\RR}{\\mathbb{R}} " + "\\RR\\times".repeat(99) + "\\RR$$", expect: "renders" },
      { name: "a plain syntax error", src: "$\\frac{a}{$", expect: "error" },
    ];
    const facts = await page.evaluate(([cases, srcClass]: [{ name: string; src: string }[], string]) => {
      const w = window as any;
      const out = document.getElementById("out") as HTMLElement;
      const run = (src: string): number => { const t0 = performance.now(); out.innerHTML = w.__pipe.md(src); return Math.round(performance.now() - t0); };
      const perCase = cases.map(({ name, src }) => {
        const ms = run(src);
        const code = out.querySelector("code." + srcClass);
        // the title sits on the pre for a display paragraph of its own (a code block), on the code span in a paragraph
        const shown = code ? (code.parentElement && code.parentElement.tagName === "PRE" ? code.parentElement : code) : null;
        const err = out.querySelector(".katex-error");
        return { name, ms, katex: out.querySelectorAll(".katex").length, error: err ? (err.getAttribute("title") || "") : null,
          source: code && shown ? { text: code.textContent || "", title: shown.getAttribute("title"), shape: shown.tagName } : null };
      });
      // sizes: an inline rule and an inline kern, measured; the em is KaTeX's (its root is 1.21em of the 16px body here)
      run("before $\\rule{5000em}{5000em}$ after");
      const rule = (out.querySelector(".katex-rule") as HTMLElement | null)?.getBoundingClientRect();
      const em = parseFloat(getComputedStyle(out.querySelector(".katex") as HTMLElement).fontSize);
      run("$a\\kern{50000em}b$");
      const kern = (out.querySelector(".katex") as HTMLElement | null)?.getBoundingClientRect();
      return { perCase, rule: rule ? { w: rule.width, h: rule.height } : null, em, kernW: kern ? kern.width : null };
    }, [cases.map(({ name, src }) => ({ name, src })), MATH_SOURCE_CLASS]);
    const titles = {
      stop: /^Not rendered: too many macro expansions; the limit for this formula is \d+, set by the longest macro body it defines\.$/,
      repeat: /^Not rendered: a macro in this formula repeats one of its arguments/,
      expanded: /^Not rendered: a macro in this formula is defined with \\edef or \\xdef, whose stored body is its expansion/,
    };
    for (const c of cases) {
      const f = facts.perCase.find((x: { name: string }) => x.name === c.name)!;
      const tag = c.name + " (" + f.ms + " ms): ";
      assert.ok(f.ms < 2000, tag + "handled in well under the seconds the bombs took, on a loaded box too");
      if (c.expect === "renders") {
        assert.deepEqual({ katex: f.katex, error: f.error, source: f.source }, { katex: 1, error: null, source: null }, tag + "one .katex root, no error, no fallback");
        continue;
      }
      if (c.expect === "error") {
        assert.match(f.error || "", /^ParseError: KaTeX parse error: /, tag + "KaTeX's own red span, as on main (a syntax error is not a bound)");
        assert.deepEqual({ katex: f.katex, source: f.source }, { katex: 0, source: null }, tag + "and nothing else");
        continue;
      }
      assert.equal(f.katex, 0, tag + "nothing rendered");
      assert.equal(f.error, null, tag + "no KaTeX error text: the bound wears the fallback");
      assert.ok(f.source, tag + "the source is shown");
      assert.equal(f.source!.text, c.src.replace(/^\$+|\$+$/g, ""), tag + "the TeX intact");
      assert.equal(f.source!.shape, c.src.startsWith("$$") ? "PRE" : "CODE", tag + "a code block where a display paragraph stood, a code span in a paragraph, the title on it");
      assert.match(f.source!.title || "", titles[c.expect], tag + "its title says why: " + f.source!.title);
    }
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
      const t0 = performance.now(); out.innerHTML = w.__pipe.md(src); const ms = Math.round(performance.now() - t0);
      const display = out.querySelectorAll(".katex-display").length;
      const inline = Array.from(out.querySelectorAll(".katex")).filter((k) => !k.closest(".katex-display")).length;
      const shown = Array.from(out.querySelectorAll("pre > code." + srcClass));
      const titles = Array.from(new Set(shown.map((c) => c.parentElement?.getAttribute("title") || "")));
      const prose = (out.lastElementChild as HTMLElement | null)?.textContent || "";
      // the dress: the sheets' rules over the page, the fallback beside an author's code span, both shapes
      const style = document.createElement("style"); style.textContent = css; document.head.appendChild(style);
      out.className = "md";
      out.innerHTML = w.__pipe.md("Total $" + over + "$ and `a code span` here.\n\n$$\n" + over + "\n$$\n\n```\nfenced\n```");
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
    // the time bound is a ceiling with a loaded-box margin, not what catches the budget's loss: the counts above do that (with
    // the check disabled, display 20 and shown 0). Measured in this window, render and innerHTML with no forced layout: 2.0 to
    // 3.1 s here, 5.9 to 9.9 s with the budget off, so a bound that split the two would sit under three times the fixed time
    // where this file allows four to six for the full suite's load; the 8 to 15 s the page froze for before adds the layout.
    assert.ok(facts.ms < 20000, "the whole message renders inside a ceiling generous for a loaded box (2 to 3 s alone here): " + facts.ms + " ms");
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
