// Behavior tests for the TeX math extension (math.ts). The delimiter rules are the
// load-bearing part: in chat text a bare `$` means shell variables and prices far more often
// than math, so the stay-literal cases matter as much as the rendered ones. marked runs for
// real here (plain JS, no DOM needed). Since 2026-09-07 the extension emits a PLACEHOLDER per
// formula, an element carrying the TeX as text, and KaTeX renders into it AFTER the sanitizer
// (renderMathPlaceholders, a DOM post-pass), so what this file can execute is the placeholder
// contract: which text becomes a formula, which stays prose, and what the placeholder carries.
// That KaTeX's layout survives the sanitizer is executed in headless Chromium over the real
// modules: md-sanitize-postpass-browser.test.ts measures a fraction, a superscript, a radical
// and a display sum, md-sanitize-katex-browser.test.ts checks the rendered markup is KaTeX's
// own byte for byte, and md-sanitize-viewer-math-browser.test.ts opens a note with math in the
// chat page's viewer. The wiring (math.ts, chat-md.ts, render.ts) is source-pinned below. This
// is the ONE node file for the math contract: review round 2 folded md-sanitize-math.test.ts, a
// near-copy with three of these pins repeated, into it. The sanitizer's own shape (the registry
// and the loop that runs the passes) is md-sanitize.test.ts's.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { Marked } from "marked";
import katex from "katex";
import { mathBlock, mathInline, mathPlaceholder, MATH_INLINE_CLASS, MATH_DISPLAY_CLASS, MATH_TEX_MAX_CHARS, MATH_TEX_BUDGET_CHARS, MATH_MAX_SIZE_EM, MATH_EXPANSION_BUDGET_CHARS, MATH_SOURCE_CLASS, macroBounds, maxExpandFor } from "./math";

const m = new Marked({ gfm: true, extensions: [mathBlock, mathInline] });
const html = (src: string) => m.parse(src) as string;
const PLACEHOLDER = /<(span|div) class="(md-math-inline|md-math-display)">([\s\S]*?)<\/\1>/g;
const unescape = (s: string) => s.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
/** Every placeholder in marked's output, in order: its tag, its mode and the TeX it carries. */
const formulas = (out: string) => Array.from(out.matchAll(PLACEHOLDER)).map((x) => ({ tag: x[1], display: x[2] === MATH_DISPLAY_CLASS, tex: unescape(x[3]) }));
const hasMath = (s: string) => formulas(s).length > 0;
// the options renderMathPlaceholders hands katex.render (pinned against math.ts below); maxExpand is computed per formula
// there (maxExpandFor), so the fixed part is spread and a call adds it for the formula at hand
const KATEX = { throwOnError: false, output: "html", trust: false, maxSize: MATH_MAX_SIZE_EM } as const;

// --- becomes a formula: marked emits the placeholder, KaTeX does not run here ---

test("inline $..$ becomes an inline placeholder carrying the TeX", () => {
  const out = html("Euler: $e^{i\\pi}+1=0$ holds.");
  assert.deepEqual(formulas(out), [{ tag: "span", display: false, tex: "e^{i\\pi}+1=0" }]);
  assert.ok(!out.includes("$e^"), "the delimiters must not leak through");
  assert.ok(!out.includes('class="katex"'), "KaTeX runs after the sanitizer, never inside marked");
});

test("inline \\(..\\) becomes an inline placeholder", () => {
  assert.deepEqual(formulas(html("Ratio \\(\\tfrac{a}{b}\\) here.")), [{ tag: "span", display: false, tex: "\\tfrac{a}{b}" }]);
});

test("$$..$$ and \\[..\\] become display placeholders: a span inside a paragraph, a div for a paragraph of their own", () => {
  assert.deepEqual(formulas(html("Total: $$\\sum_i x_i$$ done.")), [{ tag: "span", display: true, tex: "\\sum_i x_i" }]);
  assert.deepEqual(formulas(html("\\[x^2\\]")), [{ tag: "div", display: true, tex: "x^2" }]);
  assert.ok(!html("\\[x^2\\]").includes("<p>"), "the block form is not wrapped in a paragraph");
});

test("a multi-line $$ paragraph beats markdown's block rules", () => {
  // The "- x" line would become a <li> if block tokenization carved the formula up first.
  const out = html("$$\n- x\n$$");
  assert.deepEqual(formulas(out), [{ tag: "div", display: true, tex: "- x" }]);
  assert.ok(!out.includes("<li>"), "list rule must not fire inside display math");
});

test("closing $ may touch trailing punctuation and emphasis", () => {
  assert.ok(hasMath(html("the $x$-axis")));
  const strong = html("**$O(n)$** cost");
  assert.ok(strong.includes("<strong>") && hasMath(strong));
});

test("the TeX is text: markup inside a formula is escaped, never emitted as HTML", () => {
  // The placeholder is the one place marked writes a formula, and the sanitizer sees it as an element
  // with text; a formula can therefore never smuggle an element past it.
  const out = html("$a<b \\& c>d$ and $<img src=x onerror=1>$");
  assert.deepEqual(formulas(out).map((f) => f.tex), ["a<b \\& c>d", "<img src=x onerror=1>"]);
  assert.ok(!out.includes("<img"), "escaped: the placeholder's text is not markup");
  assert.ok(out.includes("&lt;img src=x onerror=1&gt;"));
  assert.equal(mathPlaceholder("a<b", false, false), '<span class="md-math-inline">a&lt;b</span>');
  assert.equal(mathPlaceholder("x", true, true), '<div class="md-math-display">x</div>');
  assert.equal(mathPlaceholder("x", true, false), '<span class="md-math-display">x</span>', "display math inside a paragraph is a span: the placeholder stays in the flow it came from");
});

test("marked's output holds no KaTeX markup, no inline style and no svg: nothing for the colour-only rule to strip", () => {
  // The complement of the executed test below (KaTeX's own output is inline styles and svg): none of it is
  // in what marked emits, so the sanitizer meets an element with text and nothing to strip.
  for (const src of ["$\\frac{a}{b}$", "$$\\sum_{i=0}^{n} i^2$$", "$\\sqrt{d}$", "$x^2$", "\\[\\int_0^1 f\\]"]) {
    const out = html(src);
    assert.ok(hasMath(out), "placeholder expected for " + src + ": " + out);
    assert.doesNotMatch(out, /class="katex/, "no KaTeX markup before the sanitizer: " + out);
    assert.doesNotMatch(out, /style=/, "no inline style before the sanitizer: " + out);
    assert.doesNotMatch(out, /<svg/, "no svg before the sanitizer: " + out);
  }
});

test("invalid TeX renders as flagged output under the options the post-pass uses, never a throw", () => {
  // renderMathPlaceholders needs a DOM (katex.render); the same options through renderToString are
  // KaTeX's same pipeline minus the node building, and the browser leg runs the real call.
  const out = katex.renderToString("\\frac{1}{", { ...KATEX, displayMode: false });
  assert.ok(out.includes("katex-error"), "throwOnError: false paints bad TeX as flagged source");
  const untrusted = katex.renderToString("\\href{javascript:alert(1)}{x}", { ...KATEX, displayMode: false });
  assert.ok(!untrusted.includes("<a ") && !untrusted.includes("javascript:"), "trust: false: no TeX command mints a URL");
});

// --- stays literal ---

const LITERAL = [
  ["prices: closer followed by a digit", "costs $5 and $10 today"],
  ["shell vars joined by a slash", "paths $HOME/$USER here"],
  ["shell vars joined by a comma (closer followed by a letter)", "set $FOO,$BAR now"],
  ["shell vars with space-preceded closers", "echo $FOO and $BAR"],
  ["opener must touch its content", "not math: $ x$ spaced"],
  ["content may not span lines", "a $x\ny$ b"],
] as const;

for (const [why, src] of LITERAL) {
  test(`literal: ${why}`, () => {
    const out = html(src);
    assert.ok(!hasMath(out), `must stay literal: ${src}\ngot: ${out}`);
    assert.ok(out.includes("$"), "the $ itself must survive as text");
  });
}

test("a code span is a wall: $ cannot pair across it", () => {
  const out = html("price $5 `a $b` end");
  assert.ok(!hasMath(out));
  assert.ok(out.includes("<code>a $b</code>"), "code span must render intact");
});

test("$..$ inside a code span or fence stays code", () => {
  const span = html("`$x$`");
  assert.ok(!hasMath(span) && span.includes("<code>$x$</code>"));
  const fence = html("```sh\necho $X and $Y$\n```");
  assert.ok(!hasMath(fence) && fence.includes("echo $X"));
});

test("escaped \\$ never opens math", () => {
  const out = html("\\$5 vs \\$10");
  assert.ok(!hasMath(out) && out.includes("$5"));
});

// --- source pins (the wiring that behavior tests can't reach) ---

const UI = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");

test("render.ts wires the math extensions into marked, through the one shared grammar (md-config.ts)", () => {
  // md-config.ts owns the extension list since Slice 4 of plans/markdown-viewer.md: ONE configuration for the chat's
  // singleton, the viewer (file-view.ts, so the files and feed bundles carry the grammar), the anchor map and the
  // breaks:true user-text instance (chat-md.ts), so a user message with math renders exactly as before. The list's
  // literal is pinned whole: an extension added or dropped changes what every bundle renders, and says so here.
  const grammar = UI("md-config.ts");
  assert.match(grammar, /import \{ mathBlock, mathInline, renderMathPlaceholders \} from "\.\/math";/);
  assert.match(grammar, /export const mdExtensions: MarkedExtension\[\] = \[\n\s*delDoubleTilde,\n\s*\{ extensions: \[mathBlock, mathInline, frontMatter, footnoteDef, footnoteRef, callout, mark, wikilink\] \},\n\];/);
  assert.match(grammar, /export function applyMdConfig\(\): void \{\n\s*if \(applied\) return;\n\s*applied = true;\n\s*marked\.setOptions\(\{ gfm: true, breaks: false \}\);\n\s*marked\.use\(\.\.\.mdExtensions\);\n\}/, "idempotent: the singleton is configured once however many modules call it");
  for (const f of ["render.ts", "file-view.ts", "anchor-map.ts"]) {
    const src = UI(f);
    assert.match(src, /import \{ applyMdConfig[^}]*\} from "\.\/md-config";/, f + " imports the one configuration");
    assert.match(src, /^applyMdConfig\(\);/m, f + " applies it at load");
    assert.doesNotMatch(src, /marked\.(setOptions|use)\(/, f + " configures nothing of its own");
  }
  assert.match(UI("chat-md.ts"), /import \{ mdExtensions \} from "\.\/md-config";/, "the user-text instance takes the same list");
  assert.doesNotMatch(UI("chat-md.ts"), /chatMdExtensions|from "\.\/math"/, "chat-md.ts no longer owns a grammar of its own");
});

test("KaTeX renders AFTER the sanitizer, as a post-pass sanitizeMd runs: chat-md.ts registers renderMathPlaceholders once, and no renderer calls it by hand", () => {
  // KaTeX's output is inline styles (height, top, vertical-align on struts and vlist rows) plus inline
  // <svg> for stretchy glyphs, and the shared sanitizer keeps only colour declarations in a style
  // attribute (md-sanitize.ts, decision 6), so KaTeX output run through it collapses. The extension
  // therefore emits a placeholder, and KaTeX is rendered into it on the DOM sanitizeMd returns, inside
  // sanitizeMd itself (a registered post-pass, md-sanitize.ts registerMdPostPass), BEFORE the PR-reference
  // walk (which then meets the .katex shape it always did) and the serialization. ONE mechanism: the
  // first cut had md() and userMd() call the fill by hand, and the viewer's mdBlock, which parses with the
  // same marked singleton inside the chat page, showed a note's formulas as bare TeX (review round 1;
  // md-sanitize-viewer-math-browser.test.ts opens such a note in both bundles). The grammar's module
  // registers the fill, so a bundle with the grammar has the fill and a bundle without it has neither.
  const math = UI("math.ts");
  assert.match(math, /export function renderMathPlaceholders\(root: ParentNode\): void \{/);
  assert.match(math, /const KATEX_OPTIONS = \{ output: "html", trust: false, maxSize: MATH_MAX_SIZE_EM \} as const;/, "every call is html-only and untrusted, under KaTeX's size cap");
  assert.match(math, /katex\.render\(tex, el, \{ \.\.\.KATEX_OPTIONS, displayMode: display, throwOnError: true, maxExpand \}\);/,
    "the one katex call on the happy path, under the per-formula expansion count, and thrown at, so the catch can tell KaTeX's expansion stop from a syntax error (review round 5)");
  assert.match(math, /if \(!\(e instanceof katex\.ParseError\)\) throw e;\n\s*if \(\/Too many expansions\/\.test\(e\.message\)\) \{\n\s*showSource\(el, tex, "Not rendered: too many macro expansions; the limit for this formula is " \+ maxExpand \+ ", set by the longest macro body it defines\."\);/,
    "the expansion stop wears the slice's fallback, the source with the reason and the count, where KaTeX's red text stood before");
  assert.match(math, /katex\.render\(tex, el, \{ \.\.\.KATEX_OPTIONS, displayMode: display, throwOnError: false, maxExpand \}\);\n\s*\}\n\s*el\.replaceWith\(\.\.\.Array\.from\(el\.childNodes\)\);/,
    "any other syntax error is rendered again with throwOnError: false, KaTeX's own red text as on main, and the placeholder is unwrapped right after either call: the .katex root stands where marked's output used to");
  assert.equal((math.match(/katex\.render\(/g) || []).length, 2, "two katex.render calls in the file: the happy path and the syntax-error rendering, no third");
  assert.doesNotMatch(math, /renderToString/, "marked's output holds no KaTeX markup: the extension emits placeholders only");
  const grammar = UI("md-config.ts");
  assert.match(grammar, /import \{ mathBlock, mathInline, renderMathPlaceholders \} from "\.\/math";/);
  assert.match(grammar, /import \{ registerMdPostPass \} from "\.\/md-sanitize";/);
  assert.equal((grammar.match(/registerMdPostPass\(renderMathPlaceholders\);/g) || []).length, 1, "registered once, at load, beside the extension list");
  assert.ok(grammar.indexOf("export const mdExtensions") < grammar.indexOf("registerMdPostPass(renderMathPlaceholders);"), "the fill is registered where the grammar is defined");
  assert.doesNotMatch(UI("chat-md.ts"), /registerMdPostPass|renderMathPlaceholders/, "chat-md.ts registers nothing: the grammar module does");
  const render = UI("render.ts");
  assert.doesNotMatch(render, /renderMathPlaceholders\(/, "render.ts calls no fill of its own: sanitizeMd runs it");
  assert.doesNotMatch(render, /from "\.\/math"/, "render.ts imports nothing from math.ts; the grammar module carries it");
  const view = UI("file-view.ts");
  assert.doesNotMatch(view, /from "\.\/math"|from "katex"|renderMathPlaceholders/, "the viewer imports no KaTeX and no fill of its own: the grammar module (md-config.ts) carries both into every bundle the viewer lands in, and the sanitize runs the fill (Slice 4)");
  // match on the two function bodies, not the file, so a failure prints the function and not render.ts
  const mdFn = render.match(/function md\(src: string[^\n]*?\): string \{[\s\S]*?\n\}/)?.[0] || "";
  assert.ok(mdFn, "md() must exist");
  assert.match(mdFn, /const clean = sanitizeMd\(dirty\);[^\n]*\n\s*linkifyPrRefs\(clean, repo\);/, "md(): sanitize (math rendered inside it), then link PR refs");
  // userMd carries an optional repo parameter and hands it to linkifyPrRefs, the same as md() above (the 2026-09-08
  // fold of upstream's converged userMd; chat-md.test.ts pins the same loose signature), so the match on it is loose
  const userFn = render.match(/function userMd\(src: string[^\n]*?\): string \{[\s\S]*?\n\}/)?.[0] || "";
  assert.ok(userFn, "userMd() must exist");
  assert.match(userFn, /const clean = sanitizeMd\(userMdHtml\(src\)\);[^\n]*\n\s*linkifyPrRefs\(clean, repo\);/, "userMd(): the same order");
  // The last link, that sanitizeMd runs every registered pass on the sanitized body before handing it back,
  // is the sanitizer's own contract and is pinned once, in md-sanitize.test.ts (the registry and the loop).
});

test("no source still claims KaTeX's output passes the sanitizer: the pre-placeholder comments are gone", () => {
  // Before the placeholder, math.ts and chat-md.ts explained that KaTeX's html-only output passed md()'s
  // DOMPurify profile untouched. It never did under the colour-only style rule, and a comment that says so
  // again would send the next reader back to rendering inside marked.
  assert.doesNotMatch(UI("chat-md.ts"), /passes through unchanged/);
  assert.doesNotMatch(UI("math.ts"), /passes md\(\)'s DOMPurify html profile untouched/);
  assert.match(UI("md-sanitize.ts"), /What does NOT pass through here: KaTeX/);
});

test("a formula longer than MATH_TEX_MAX_CHARS is shown as source before katex.render is reached", () => {
  // katex.render is synchronous on the main thread and superlinear in a flat formula's length (0.23 s at 20,000
  // characters, 0.8 s at 24,000, 6 to 17 s at 100,000, measured 2026-09-08; md-sanitize-postpass-browser.test.ts runs
  // the cap for real), and KaTeX has no option that bounds its input, so the fill checks the length itself, ahead of
  // the one katex.render call, and takes the belt a throw takes. The value is the knee of those measurements, not a
  // guess: change it with new numbers.
  assert.equal(MATH_TEX_MAX_CHARS, 20000);
  const math = UI("math.ts");
  const fill = math.slice(math.indexOf("export function renderMathPlaceholders("));
  const cap = fill.indexOf("if (tex.length > MATH_TEX_MAX_CHARS) {");
  const render = fill.indexOf("katex.render(");
  assert.ok(cap > 0 && cap < render, "the length check stands ahead of the one katex.render call");
  assert.match(fill.slice(cap, render), /showSource\(el, tex, "Not rendered: "/, "an over-long formula is shown as source, its title saying why");
  assert.match(fill.slice(render), /catch \(e\) \{\n\s*if \(!reported\) \{ reported = true; console\.error\("math: [^\n]*\n\s*showSource\(el, tex, "Not rendered: /,
    "the residual-throw belt is the same helper, and says so on the console once per call (the fail-loudly rule: a swallowed throw hides the breakage)");
});

test("the fill's bounds stand ahead of the one katex.render call, in order: the formula's length, the call's total, a macro that repeats an argument, a macro defined with \\edef or \\xdef; then KaTeX's own two, its expansion stop shown as source too", () => {
  // Review round 3. The length cap bounds one formula; a message of twenty formulas just under it blocked the page for
  // 8 to 15 s, so the call keeps a running total of the TeX it has rendered (its own local: one sanitizeMd call, so one
  // message or one note) and shows a formula that would pass MATH_TEX_BUDGET_CHARS as source, a shorter one still
  // rendering while it fits. KaTeX expands macro bodies before layout and its maxExpand counts expansions, not their
  // size, so a 1,409-character `\def\a{<1,000>}` and 200 uses was 200,000 characters of formula and 20 s: maxExpand is
  // computed per formula from the longest body it defines (maxExpandFor), and a body that repeats an argument, the one
  // amplification an expansion count cannot bound, takes the source fallback before KaTeX is reached, as does a body
  // defined with `\edef` or `\xdef` (review round 4): KaTeX stores those EXPANDED and charges one expansion per use
  // whatever the stored length, so the count over the bodies as written bounds nothing (the executed test below shows
  // the cost model). maxSize stops `\rule{5000em}{5000em}` from laying a 78,650 px square in the transcript. The values,
  // with their measurements, are math.ts's comments; the postpass browser leg runs each bound for real.
  assert.equal(MATH_TEX_BUDGET_CHARS, 100000, "five formulas at the cap; a long paper's mathematics is 15,000 to 30,000 characters");
  assert.equal(MATH_MAX_SIZE_EM, 50, "about the chat column");
  assert.equal(MATH_EXPANSION_BUDGET_CHARS, MATH_TEX_MAX_CHARS, "the expanded bodies of one formula are bounded by the same knee as its written length");
  const math = UI("math.ts");
  const fill = math.slice(math.indexOf("export function renderMathPlaceholders("));
  const cap = fill.indexOf("if (tex.length > MATH_TEX_MAX_CHARS) {");
  const budget = fill.indexOf("if (rendered + tex.length > MATH_TEX_BUDGET_CHARS) {");
  const scan = fill.indexOf("const bounds = macroBounds(tex);");
  const repeat = fill.indexOf("if (bounds.argRepeat) {");
  const expanded = fill.indexOf("if (bounds.expandedBody) {");
  const spend = fill.indexOf("rendered += tex.length;");
  const count = fill.indexOf("const maxExpand = maxExpandFor(tex, bounds);");
  const render = fill.indexOf("katex.render(");
  const stop = fill.indexOf("if (/Too many expansions/.test(e.message)) {");
  assert.ok(cap > 0 && cap < budget && budget < scan && scan < repeat && repeat < expanded && expanded < spend && spend < count && count < render && render < stop, "length cap, then the running total, then one read of the macro bounds, then the argument-repeat rule, then the expanded-body rule, then the total is charged, then the count is computed from the bounds read, then the one katex.render call, whose catch reads the expansion stop: " + JSON.stringify({ cap, budget, scan, repeat, expanded, spend, count, render, stop }));
  assert.equal((fill.match(/macroBounds\(/g) || []).length, 1, "the fill reads a formula's macro bounds once; the two refusals and the count share the scan (review round 6: three scans of the TeX per formula before)");
  assert.match(fill, /let rendered = 0;/, "the meter is the call's own local: one sanitizeMd call, one message or note");
  assert.match(fill.slice(budget, repeat), /showSource\(el, tex, "Not rendered: the formulas above already total " \+ rendered \+ " characters of TeX; the limit for one message or note is " \+ MATH_TEX_BUDGET_CHARS \+ "\."\);/, "over the total: the source, the title saying what was rendered and the limit");
  assert.match(fill.slice(repeat, expanded), /showSource\(el, tex, "Not rendered: a macro in this formula repeats one of its arguments/, "an argument repeated: the source, the title saying why");
  assert.match(fill.slice(expanded, spend), /showSource\(el, tex, "Not rendered: a macro in this formula is defined with \\\\edef or \\\\xdef, whose stored body is its expansion/, "an expanded-at-definition body: the source, the title saying why");
  assert.match(math, /code\.className = MATH_SOURCE_CLASS;/, "the fallback's code element wears the class the sheets dress (showSource)");
  assert.equal(MATH_SOURCE_CLASS, "md-math-src");
  // the sheets: one rule, byte-equal (fileview-parity.test.ts holds the equality), tokens only, dressing the fallback as
  // unrendered source: the dim tier and a dotted underline in place of the code tone
  for (const sheet of ["styles.css", "feed.css"]) {
    const css = UI(sheet);
    const at = css.indexOf(".md code.md-math-src, .fileview-md code.md-math-src {");
    assert.ok(at > 0, sheet + " dresses the fallback");
    const rule = css.slice(at, css.indexOf("}", at) + 1);
    assert.match(rule, /color: var\(--dim\); text-decoration: underline dotted; text-decoration-color: var\(--dim\);/, sheet + ": the dim tier, a dotted underline");
    assert.doesNotMatch(rule, /#[0-9a-fA-F]{3,8}\b/, sheet + ": no colour literal in the rule");
  }
  // render.ts's highlighter leaves the fallback alone (auto-detection over 20,000 characters of TeX cost 250 ms and dressed
  // it in a guessed grammar's tokens); it spells the class rather than importing it, since render.ts imports nothing from math.ts
  const render_ = UI("render.ts");
  const hl = render_.slice(render_.indexOf("function highlight(container: HTMLElement"), render_.indexOf("function copyText("));
  assert.match(hl, new RegExp('if \\(code\\.classList\\.contains\\("' + MATH_SOURCE_CLASS + '"\\)\\) \\{ const host = code\\.parentElement; if \\(host && host\\.tagName === "PRE"\\) addCopyBtn\\(host as HTMLElement, raw\\); return; \\}'),
    "the highlighter skips the fallback (its Copy button kept) before any tokenizing");
  assert.ok(hl.indexOf('classList.contains("' + MATH_SOURCE_CLASS + '")') < hl.indexOf("highlightHtml("), "the exemption stands ahead of the tokenizer");
});

test("executed: macroBounds reads a formula's macro bodies the way KaTeX will expand them, and maxExpandFor bounds the expansion by the longest", () => {
  const long = "x+".repeat(500);                                  // a 1,000-character body
  const none = { maxBody: 0, argRepeat: false, expandedBody: false, unplacedBody: false };
  assert.deepEqual(macroBounds("\\frac{a}{b} + \\sqrt{x}"), none, "no macro defined: nothing to bound");
  assert.equal(maxExpandFor("\\frac{a}{b}"), 1000, "KaTeX's default when no macro is defined (its built-ins have bodies of a few tokens)");
  assert.deepEqual(macroBounds("\\def\\a{" + long + "}" + "\\a".repeat(200)), { ...none, maxBody: 1000 }, "\\def: the body's length, stored as written");
  assert.equal(maxExpandFor("\\def\\a{" + long + "}" + "\\a".repeat(200)), 20, "20,000 / 1,000: twenty expansions of that body at most");
  assert.equal(maxExpandFor("\\def\\a{" + long + "}", macroBounds("\\def\\a{" + long + "}")), 20, "the bounds a caller already holds give the same count (the fill passes the ones it read for its refusals)");
  assert.deepEqual(macroBounds("\\newcommand{\\vect}[1]{\\mathbf{#1}} \\vect{x}"), { ...none, maxBody: 11 }, "\\newcommand: the first group is the name, the second (after [n]) the body; one use of #1 is no repeat");
  assert.equal(maxExpandFor("\\newcommand{\\vect}[1]{\\mathbf{#1}} \\vect{x}"), 1000, "a short body leaves KaTeX's default in place");
  assert.deepEqual(macroBounds("\\newcommand\\R{\\mathbb{R}}"), { ...none, maxBody: 10 }, "\\newcommand with an unbraced name");
  assert.deepEqual(macroBounds("\\def\\a#1{#1#1}\\a{\\a{\\a{x}}}"), { ...none, maxBody: 4, argRepeat: true }, "#1 twice in a body: the argument is copied at each use");
  assert.deepEqual(macroBounds("\\newcommand{\\pair}[2]{(#1, #2, #1)}"), { ...none, maxBody: 12, argRepeat: true }, "a repeat of any one parameter counts");
  assert.deepEqual(macroBounds("\\newcommand{\\f}[2]{#1 + #2}"), { ...none, maxBody: 7 }, "two different parameters once each: no repeat");
  assert.equal(macroBounds("\\expandafter\\def\\csname a\\endcsname{" + long + "}").maxBody, 1000, "whatever stands between the definer and the brace: the group after the command is read wherever it starts");
  assert.equal(macroBounds("\\def\\a{" + long + "}\\def\\b{\\a\\a\\a}\\b\\b").maxBody, 1000, "a chain: the longest body counts, every use of \\b costs \\a's expansions too");
  assert.equal(macroBounds("\\global\\def\\a{xy}\\long\\def\\b{xyz}").maxBody, 3, "\\global and \\long in front: the \\def still reads");
  for (const cmd of ["gdef", "edef", "xdef", "renewcommand", "providecommand", "DeclareMathOperator"]) {
    assert.equal(macroBounds("\\" + cmd + "\\a{xyz}").maxBody, 3, "\\" + cmd + " defines a body");
    assert.equal(macroBounds("\\" + cmd + "\\a{xyz}").expandedBody, cmd === "edef" || cmd === "xdef", "\\" + cmd + (cmd === "edef" || cmd === "xdef" ? " stores its body expanded" : " stores its body as written"));
  }
  assert.equal(macroBounds("\\global\\edef\\a{xyz}").expandedBody, true, "\\global in front: the \\edef still reads");
  assert.equal(macroBounds("\\def\\a{xyz}\\edefx").expandedBody, false, "\\edefx is a different command");
  assert.deepEqual(macroBounds("\\deficit{xyz} \\let\\b\\a"), none, "a word that starts with def is not \\def; \\let aliases a command and adds no body (the one it aliases is counted where it is defined)");
  assert.equal(macroBounds("\\def\\a{\\{x\\}}").maxBody, 5, "escaped braces are not braces: the body is the five characters between the real ones");
  assert.equal(macroBounds("\\def\\a{" + long).maxBody, 1000, "an unclosed body (KaTeX rejects the formula) counts to the end of the text");
  // review round 5: a definer is its TOKEN, whatever follows it. KaTeX's `\def` takes as the name the next token but
  // `\ { } $ & # ^ _`, so a digit, a control symbol and a control word all name a macro, and the scan once required a word
  // boundary after the definer, which `\def1` has not: the round-3 and round-4 bombs returned under a digit name
  assert.deepEqual(macroBounds("\\def1{" + long + "}" + "1".repeat(200)), { ...none, maxBody: 1000 }, "\\def1: a digit names the macro; the body reads as \\def\\a's does");
  assert.equal(maxExpandFor("\\def1{" + long + "}" + "1".repeat(200)), 20, "and bounds it the same");
  assert.deepEqual(macroBounds("\\def\\a{xy}\\edef1{\\a\\a}"), { ...none, maxBody: 4, expandedBody: true }, "\\edef1: flagged as \\edef\\b is");
  assert.equal(macroBounds("\\def\\!{" + long + "}").maxBody, 1000, "a control symbol names the macro");
  assert.equal(macroBounds("\\renewcommand1{xyz}").maxBody, 3, "\\renewcommand with a digit name (KaTeX refuses \\newcommand1: 1 is defined already)");
  assert.deepEqual(macroBounds("\\def@\\a{xyz}"), none, "\\def@ is another control word (KaTeX's lexer takes @ as a letter): the formula defines nothing and @ never expands");
  // a body the scan cannot place takes the strict bound (unplacedBody: maxExpandFor prices every expansion at the formula's
  // own length, the most any body written in it can be): a definer with no brace group after it; a `\let` or `\futurelet`
  // that aliases a definer, whose later uses put their bodies wherever they like (read as the group after `\def`, `{a}`
  // stood in for the body of `\let\d\def \frac{a}{b} \d\b{<1,000>}` and 200 uses passed at KaTeX's default count); a
  // definer inside a brace group, stored in a body and run at each use, where a body assembled from the arguments is up to
  // nine groups long (`\def\d#1...#9{\def\b{#1...#9}}` over nine 2,000-character groups, 18,154 characters of TeX under
  // every bound, had not finished after two minutes)
  const decoy = "\\let\\d\\def \\frac{a}{b} \\d\\b{" + long + "}" + "\\b".repeat(200);
  assert.deepEqual(macroBounds(decoy), { ...none, maxBody: 1, unplacedBody: true }, "\\let aliasing \\def: the scan reads the decoy group (1 character), and unplacedBody says the body is wherever a use of the alias puts it");
  assert.equal(maxExpandFor(decoy), Math.floor(20000 / decoy.length), "so the count is the budget over the whole formula");
  assert.equal(macroBounds("\\let\\d=\\gdef").unplacedBody, true, "the optional = before the aliased command");
  assert.equal(macroBounds("\\futurelet\\d\\relax\\newcommand").unplacedBody, true, "\\futurelet aliases the second token after the name");
  assert.equal(macroBounds("\\let\\e\\let \\e\\d\\def").unplacedBody, true, "an alias of \\let is caught at the first \\let");
  assert.deepEqual(macroBounds("\\def\\a{xyz}\\let1=\\a 111"), { ...none, maxBody: 3 }, "\\let1=\\a aliases a macro defined here: its body is counted where it is defined, nothing is unplaced");
  assert.equal(macroBounds("\\def\\d#1#2{\\def\\b{#1#2}}").unplacedBody, true, "a definer inside a body");
  assert.equal(macroBounds("\\@firstoftwo{\\def\\b}{} x{" + long + "}").unplacedBody, true, "a definer inside any brace group (pushed back and run later)");
  assert.equal(macroBounds("\\def\\d{\\let}").unplacedBody, true, "an aliaser inside a body");
  assert.equal(macroBounds("\\newcommand\\b\\a").unplacedBody, true, "no brace group after the definer: the body is one token, or the formula is an error; priced as unknown either way");
  assert.equal(maxExpandFor("\\newcommand\\b\\a"), 1000, "and a short formula still keeps the default: 20,000 over 16 characters clamps to it");
  // the argument-repeat rule reads every brace group, not only the group after a definer, so a hidden body cannot escape it
  assert.equal(macroBounds("\\let\\d\\def \\d\\b#1{#1#1}").argRepeat, true, "#1 twice in a body the alias defines");
  assert.equal(macroBounds("\\def\\a#1{\\frac{#1}{#1}}").argRepeat, true, "a repeat across the nested groups of one body");
  assert.equal(macroBounds("\\newcommand{\\f}[1]{#1} \\newcommand{\\g}[1]{#1}").argRepeat, false, "two bodies using #1 once each: no repeat");
  // executed against KaTeX itself: the 200-use bomb stops at once under the computed maxExpand, where the default let it run
  // for 20 s (KaTeX's own error through the string renderer here; the fill shows the source instead, and the postpass browser
  // leg runs that); the digit-named bomb and the alias decoy stop the same way; an ordinary formula with a short macro and a
  // hundred built-in macros, and one whose short macro is used a hundred times, render under the default count
  const bomb = "\\def\\a{" + long + "}" + "\\a".repeat(200) + "x";
  const t0 = performance.now();
  const stopped = katex.renderToString(bomb, { ...KATEX, displayMode: true, maxExpand: maxExpandFor(bomb) });
  const ms = performance.now() - t0;
  assert.ok(stopped.includes("katex-error") && stopped.includes("Too many expansions"), "the bomb is stopped by KaTeX's count: " + stopped.slice(0, 200));
  assert.ok(ms < 1000, "and it stops well under a second: " + Math.round(ms) + " ms");
  const digit = "\\def1{" + long + "}" + "1".repeat(200) + "x";
  const digitOut = katex.renderToString(digit, { ...KATEX, displayMode: true, maxExpand: maxExpandFor(digit) });
  assert.ok(digitOut.includes("Too many expansions"), "the bomb under a digit name stops under the same count (4,470,000 bytes of HTML from 30 uses at the default): " + digitOut.slice(0, 200));
  const decoyOut = katex.renderToString(decoy + "x", { ...KATEX, displayMode: true, maxExpand: maxExpandFor(decoy + "x") });
  assert.ok(decoyOut.includes("Too many expansions"), "the alias decoy stops under the strict count: " + decoyOut.slice(0, 200));
  const ordinary = "\\newcommand{\\vect}[1]{\\mathbf{#1}} \\vect{x} + " + "\\boxed{y}\\,".repeat(100);
  const fine = katex.renderToString(ordinary, { ...KATEX, displayMode: true, maxExpand: maxExpandFor(ordinary) });
  assert.ok(!fine.includes("katex-error"), "a short macro and a hundred built-in macros render under the default count: " + fine.slice(0, 200));
  const reals = "\\newcommand{\\RR}{\\mathbb{R}} " + "\\RR\\times".repeat(99) + "\\RR";
  const realsOut = katex.renderToString(reals, { ...KATEX, displayMode: true, maxExpand: maxExpandFor(reals) });
  assert.ok(!realsOut.includes("katex-error"), "a short macro used a hundred times renders under the default count: " + realsOut.slice(0, 200));
  // executed against KaTeX itself, the cost model behind the expanded-body rule (review round 4): `\edef\b{<10 uses of a
  // 20-character \a>}` stores a 200-character body and charges 210 expansions once (10 uses of \a, then the 200 tokens
  // stored); each use of \b is ONE expansion pushing all 200, so under the count maxExpandFor computes from the bodies as
  // written (20 characters: KaTeX's default, 1,000) 788 uses passed and laid 157,600 characters of formula, 31 s over the
  // pipeline. Small here: 50 uses fit under a count of 260 and are 10,000 characters of formula, where the same shape
  // spelled with \def\b (stored as written, every use of \b costing its ten \a's too) stops at that count. So the fill
  // never hands an \edef or \xdef formula to KaTeX (the pin above); macroBounds is where it is caught
  const twenty = "a".repeat(20);
  const edef = "\\def\\a{" + twenty + "}\\edef\\b{" + "\\a".repeat(10) + "}" + "\\b".repeat(50) + " x";     // the space: `\bx` would be one command
  const asDef = "\\def\\a{" + twenty + "}\\def\\b{" + "\\a".repeat(10) + "}" + "\\b".repeat(50) + " x";
  assert.deepEqual(macroBounds(edef), { ...none, maxBody: 20, expandedBody: true }, "the bodies as written are 20 characters; the \\edef is flagged");
  assert.equal(maxExpandFor(edef), 1000, "so the count over them would be KaTeX's default, which the 788-use form passes");
  const edefOut = katex.renderToString(edef, { ...KATEX, displayMode: true, maxExpand: 260 });
  assert.ok(!edefOut.includes("katex-error"), "the \\edef shape renders 50 uses under 260 expansions (210 at the definition, one per use)");
  const laid = (edefOut.replace(/<[^>]*>/g, "").match(/a/g) || []).length;
  assert.equal(laid, 10000, "and laid 10,000 characters of formula from " + edef.length + " characters of TeX (KaTeX joins adjacent glyphs into one span, so the HTML is about as long as the text)");
  const asDefOut = katex.renderToString(asDef, { ...KATEX, displayMode: true, maxExpand: 260 });
  assert.ok(asDefOut.includes("katex-error") && asDefOut.includes("Too many expansions"), "the same shape stored as written stops at that count: every use of \\b costs its \\a's");
  // maxSize, executed: the rule KaTeX's own option docs name is capped at the column; without the option it is 5,000 em
  const capped = katex.renderToString("\\rule{5000em}{5000em}", { ...KATEX, displayMode: false });
  assert.ok(capped.includes("border-right-width:50em") && capped.includes("border-top-width:50em"), "maxSize caps a user size at MATH_MAX_SIZE_EM: " + capped);
  const uncapped = katex.renderToString("\\rule{5000em}{5000em}", { ...KATEX, displayMode: false, maxSize: Infinity });
  assert.ok(uncapped.includes("border-right-width:5000em"), "control: KaTeX's default is no cap at all");
});

test("executed: why the order matters: KaTeX's own output is inline styles and svg", () => {
  // The facts the design above rests on, against the real package: \sqrt draws its radical as an inline
  // <svg> (the user 2026-08-19: rendered as a bare serif "d" when an html-only profile ate it), and every
  // construct lays out through style attributes that carry no colour, which the sanitizer would drop.
  const sqrt = katex.renderToString("\\sqrt{d}", { ...KATEX, displayMode: false });
  assert.ok(sqrt.includes("<svg"), "the radical is an inline svg even with output:html");
  assert.ok(!sqrt.includes("katex-mathml"), "html-only: no MathML twin for the comment marker to double-cover");
  const frac = katex.renderToString("\\frac{a}{b}", { ...KATEX, displayMode: false });
  const styles = Array.from(frac.matchAll(/style="([^"]*)"/g)).map((x) => x[1]);
  assert.ok(styles.length >= 4, "a fraction's layout is inline styles: " + styles.length);
  assert.ok(styles.every((s) => !/(^|;)\s*(background-)?color\s*:/.test(s)), "none of them is a colour, so the colour-only rule would strip them all");
  assert.equal(MATH_INLINE_CLASS, "md-math-inline");
  assert.equal(MATH_DISPLAY_CLASS, "md-math-display");
});

test("styles.css and feed.css import the KaTeX layout css (feed.css since Slice 4 of plans/markdown-viewer.md: the feed page hosts the viewer and its bundle carries the grammar)", () => {
  for (const sheet of ["styles.css", "feed.css"]) {
    const css = UI(sheet);
    assert.equal((css.match(/@import "katex\/dist\/katex\.min\.css";/g) || []).length, 1, sheet + " imports the KaTeX sheet once");
    assert.match(css, /^\.katex-display \{ overflow-x: auto; overflow-y: hidden; \}$/m, sheet + " lets a wide display formula scroll in its own box (byte-equal in both: fileview-parity.test.ts)");
  }
});

test("esbuild emits KaTeX woff2 fonts under dist/fonts/", () => {
  const build = fs.readFileSync(path.resolve(process.cwd(), "esbuild.js"), "utf8");
  assert.match(build, /"\.woff2": "file"/);
  assert.match(build, /assetNames: "fonts\/\[name\]-\[hash\]"/);
});

test("katex is a declared dependency", () => {
  const pkg = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), "package.json"), "utf8"));
  assert.ok(pkg.dependencies && pkg.dependencies.katex, "katex must be in dependencies");
});
