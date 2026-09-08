// Math renders AFTER the sanitizer (plans/markdown-viewer.md, Slice 1 review, 2026-09-07). The shared sanitizer
// keeps only colour in an inline `style` (decision 6), and KaTeX's output carries its whole vertical layout in
// inline style, so KaTeX markup emitted by marked and then sanitized came back flat: every formula in the chat
// lost its fraction bars, limits, radicals and superscripts. The fix moves KaTeX out of marked's path: the math
// extensions (math.ts) emit an inert placeholder carrying the TeX as text, sanitizeMd runs, and
// renderMathPlaceholders renders KaTeX into each placeholder on the sanitized DOM. This file pins the placeholder
// contract and the wiring in node (marked runs for real, no DOM); the browser leg
// (md-sanitize-postpass-browser.test.ts) measures the layout that survives in Chromium.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { Marked } from "marked";
import { chatMdExtensions } from "./chat-md";
import { MATH_DISPLAY_CLASS, MATH_INLINE_CLASS, mathPlaceholder, renderMathPlaceholders } from "./math";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");

// the chat singleton's grammar, rebuilt on a private instance (render.ts: gfm, breaks false, chatMdExtensions)
const chat = new Marked({ gfm: true, breaks: false }, ...chatMdExtensions);
const html = (src: string) => chat.parse(src) as string;
const hasPlaceholder = (s: string) => s.includes(MATH_INLINE_CLASS) || s.includes(MATH_DISPLAY_CLASS);

// --- marked emits the placeholder, never KaTeX's markup ---

test("inline $..$ and \\(..\\) become an inline placeholder carrying the TeX as text", () => {
  assert.equal(html("Euler: $e^{i\\pi}+1=0$ holds."), '<p>Euler: <span class="md-math-inline">e^{i\\pi}+1=0</span> holds.</p>\n');
  assert.equal(html("Ratio \\(\\tfrac{a}{b}\\) here."), '<p>Ratio <span class="md-math-inline">\\tfrac{a}{b}</span> here.</p>\n');
});

test("$$..$$ and \\[..\\] become display placeholders: a span inside a paragraph, a div for a paragraph of their own", () => {
  assert.equal(html("Total: $$\\sum_i x_i$$ done."), '<p>Total: <span class="md-math-display">\\sum_i x_i</span> done.</p>\n');
  assert.equal(html("$$\n\\sum_{i=0}^{n} i^2\n$$"), '<div class="md-math-display">\\sum_{i=0}^{n} i^2</div>');
  assert.equal(html("\\[x^2\\]"), '<div class="md-math-display">x^2</div>');
});

test("marked's output holds no KaTeX markup and no inline style: nothing for the colour-only rule to strip", () => {
  for (const src of ["$\\frac{a}{b}$", "$$\\sum_{i=0}^{n} i^2$$", "$\\sqrt{d}$", "$x^2$", "\\[\\int_0^1 f\\]"]) {
    const out = html(src);
    assert.ok(hasPlaceholder(out), "placeholder expected for " + src + ": " + out);
    assert.doesNotMatch(out, /class="katex/, "no KaTeX markup before the sanitizer: " + out);
    assert.doesNotMatch(out, /style=/, "no inline style before the sanitizer: " + out);
    assert.doesNotMatch(out, /<svg/, "no svg before the sanitizer: " + out);
  }
});

test("the TeX inside a placeholder is HTML-escaped, so it reaches the sanitizer as text and comes back as the same TeX", () => {
  const out = html("$a<b \\& c>d$");
  assert.equal(out, '<p><span class="md-math-inline">a&lt;b \\&amp; c&gt;d</span></p>\n');
  assert.equal(mathPlaceholder("x<y & z>w", false, false), '<span class="md-math-inline">x&lt;y &amp; z&gt;w</span>');
  assert.equal(mathPlaceholder("x", true, true), '<div class="md-math-display">x</div>');
  assert.equal(mathPlaceholder("x", true, false), '<span class="md-math-display">x</span>');
});

test("a multi-line $$ paragraph still beats markdown's block rules", () => {
  const out = html("$$\n- x\n$$");
  assert.equal(out, '<div class="md-math-display">- x</div>');
  assert.ok(!out.includes("<li>"), "list rule must not fire inside display math");
});

// --- the delimiter rules are untouched: bare prose stays literal ---

for (const [why, src] of [
  ["prices: closer followed by a digit", "costs $5 and $10 today"],
  ["shell vars joined by a slash", "paths $HOME/$USER here"],
  ["shell vars joined by a comma", "set $FOO,$BAR now"],
  ["opener must touch its content", "not math: $ x$ spaced"],
  ["content may not span lines", "a $x\ny$ b"],
  ["a code span is a wall", "price $5 `a $b` end"],
  ["escaped \\$ never opens math", "\\$5 vs \\$10"],
] as const) {
  test("literal: " + why, () => {
    const out = html(src);
    assert.ok(!hasPlaceholder(out), "must stay literal: " + src + "\ngot: " + out);
    assert.ok(out.includes("$"), "the $ itself must survive as text");
  });
}

test("closing $ may still touch trailing punctuation and emphasis", () => {
  assert.ok(hasPlaceholder(html("the $x$-axis")));
  const strong = html("**$O(n)$** cost");
  assert.ok(strong.includes("<strong>") && hasPlaceholder(strong));
});

// --- the post-pass and its wiring ---

test("renderMathPlaceholders is a plain exported function (the file viewer reuses it in Slice 4)", () => {
  assert.equal(typeof renderMathPlaceholders, "function");
  assert.equal(renderMathPlaceholders.length, 1);
});

test("math.ts renders with katex.render into the sanitized DOM, html output, errors flagged, nothing trusted", () => {
  const src = read("math.ts");
  assert.match(src, /katex\.render\(tex, el, \{ displayMode: display, throwOnError: false, output: "html", trust: false \}\);/);
  assert.doesNotMatch(src, /renderToString/, "KaTeX markup is never built as a string for marked to emit: it would meet the sanitizer");
  assert.match(src, /el\.replaceWith\(\.\.\.Array\.from\(el\.childNodes\)\);/, "the placeholder is unwrapped: the .katex root stands where marked's output used to");
});

test("render.ts renders the math placeholders after sanitizeMd, in md() and in userMd(), before the PR-link walk", () => {
  // The chat is the surface that renders math today. Both renderers take the sanitized <body> back from sanitizeMd;
  // the math post-pass runs on it BEFORE linkifyPrRefs (the order KaTeX's output and the PR-link walk always had)
  // and before the serialization to innerHTML.
  const src = read("render.ts");
  const imports = src.split("\n").filter((l) => l.startsWith("import ")).join("\n");
  assert.match(imports, /import \{[^}]*\brenderMathPlaceholders\b[^}]*\} from "\.\/math";/, "render.ts imports the post-pass from math.ts");
  const md = src.slice(src.indexOf("function md("), src.indexOf("function userMd("));
  assert.match(md, /const clean = sanitizeMd\(dirty\);[^\n]*\n\s*renderMathPlaceholders\(clean\);\s*\n\s*linkifyPrRefs\(clean, repo\);/,
    "md(): sanitizeMd, then renderMathPlaceholders(clean), then linkifyPrRefs");
  const userMd = src.slice(src.indexOf("function userMd("), src.indexOf("function userMd(") + 800);
  assert.match(userMd, /const clean = sanitizeMd\(userMdHtml\(src\)\);[^\n]*\n\s*renderMathPlaceholders\(clean\);\s*\n\s*linkifyPrRefs\(clean, prRepoFor\(\)\);/,
    "userMd(): sanitizeMd, then renderMathPlaceholders(clean), then linkifyPrRefs");
});

test("chat-md.ts and math.ts no longer claim KaTeX's output passes the sanitizer unchanged", () => {
  assert.doesNotMatch(read("chat-md.ts"), /passes through unchanged/);
  assert.doesNotMatch(read("math.ts"), /passes md\(\)'s DOMPurify html profile untouched/);
  assert.match(read("md-sanitize.ts"), /What does NOT pass through here: KaTeX/);
});
