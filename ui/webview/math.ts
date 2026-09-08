// TeX math for chat markdown: inline \( .. \) and $ .. $, display \[ .. \] and $$ .. $$
// (the user 2026-08-03). marked has no math syntax, so without this every formula an agent
// writes reaches the transcript as raw TeX source.
//
// Rendering happens AFTER the sanitizer, not inside marked (plans/markdown-viewer.md Slice 1 review,
// 2026-09-07). KaTeX carries every piece of vertical layout in inline `style` (a strut's height and
// vertical-align, a vlist row's top, a fraction line's border width, a radical's padding), and the
// shared sanitizer keeps only colour declarations in a `style` attribute (decision 6), so KaTeX's
// output passed through sanitizeMd came back flat: numerator and denominator on one line, a
// superscript at the baseline, the radical drawn over its radicand. The extensions therefore emit an
// INERT placeholder (class md-math-inline or md-math-display, a span inside a paragraph or a div for a
// display paragraph of its own, the TeX as its text, HTML-escaped) that the sanitizer treats as any
// element with text, and renderMathPlaceholders below renders KaTeX into each placeholder on the
// sanitized DOM, so its styles never meet DOMPurify. Nothing an author writes gains by hand-writing the
// placeholder markup: KaTeX renders only what TeX says, under `trust: false` (no \href, \url,
// \includegraphics, \htmlClass, \htmlStyle, \htmlData), which is KaTeX's own safety model, with its two
// bounds set as well (maxSize on the sizes a formula asks for, maxExpand on its macro expansion, computed per
// formula; the constants below say why) and this module's own bounds on the TeX it hands over (one formula's
// length, one message's total). KaTeX
// renders with output: "html" ONLY, no MathML twin. The KaTeX layout CSS ships via styles.css
// (@import "katex/dist/katex.min.css"; fonts emitted to dist/fonts/ by esbuild). chat-md.ts registers the
// post-pass with the sanitizer (md-sanitize.ts registerMdPostPass), so every sanitizeMd call in the chat
// bundle renders math, the file viewer's mdBlock included when it runs in the chat page; the files and feed
// bundles take the grammar, the fill and KaTeX together in Slice 4 (decision 1).
//
// The delimiter problem: `$` is everywhere in chat text that is NOT math (shell variables,
// prices), and a naive $..$ tokenizer strikes a formula through half a sentence the way the
// single-tilde del rule once did (render.ts). Code spans and fences are already safe: marked
// consumes them whole when the inline walker reaches the backtick, and a backtick never
// enters math content (rule below), so a candidate can never pair up across a code-span
// boundary either. The rules that disarm bare prose, for inline $ .. $ only:
//   - the opener $ must touch its content: "$x", "$5", never "$ x"
//   - content stays on one line and contains no $ and no backtick
//   - the closer $ must touch its content AND be followed by end-of-text, whitespace, or
//     closing punctuation. This is the rule that spares shell and price prose: "$HOME/$USER"
//     (closer followed by "U"), "$FOO,$BAR" (followed by "B"), "$5-$10" (followed by "1")
//     all stay literal, while "$x$-axis" and "**$O(n)$**" still render ("-", "*" are in
//     the set).
// \( \) / \[ \] / $$ $$ carry no real ambiguity and pass through with only a non-blank
// content check. Escaped \$ needs nothing: the walker meets the backslash first and marked's
// escape tokenizer consumes both characters before any math rule sees the $.
import katex from "katex";
import type { TokenizerAndRendererExtension, Tokens } from "marked";

type MathToken = Tokens.Generic & { text: string; display: boolean };

/** The placeholder classes: inline math, and display math (KaTeX's displayMode). The class is the whole
 *  contract between the extensions and renderMathPlaceholders; the tag (span in a paragraph, div for a
 *  display paragraph of its own) only keeps an unrendered placeholder in the flow it came from. */
export const MATH_INLINE_CLASS = "md-math-inline";
export const MATH_DISPLAY_CLASS = "md-math-display";

/** The longest formula the fill renders, in characters of TeX. katex.render runs synchronously on the page's main thread,
 *  and its cost climbs faster than the input once a formula passes about 20,000 characters (headless Chromium, KaTeX
 *  0.18.1, measured 2026-09-08 in the Slice 1 review: a flat sum of 20,000 characters took 0.23 s, 24,000 took 0.8 s,
 *  50,000 took 1 to 6 s, 100,000 took 6 to 17 s, and 1,000,000 had not finished after 270 s; a 60x60 numeric matrix is
 *  about 20,000 characters and took 40 ms), while marked and the sanitizer cost a few milliseconds per 100,000. KaTeX has
 *  no option for it (maxSize caps the sizes TeX asks for, maxExpand the number of macro expansions), neither tokenizer
 *  below bounds a formula, and a hand-written placeholder reaches the fill through no tokenizer at all, so a reply or a
 *  note carrying one enormous formula froze the chat page, every session tab in it, for as long as the render took. Over
 *  the cap the formula is shown as its source (showSource below), the belt a residual KaTeX throw takes. */
export const MATH_TEX_MAX_CHARS = 20000;

/** The most TeX one sanitizeMd call renders, in characters, summed over its formulas (review round 3). The cap above
 *  bounds one formula; a message or a note with twenty formulas just under it handed KaTeX 400,000 characters and blocked
 *  the chat page for 8 to 15 s (the render, then the style and layout of the 1,200,000 elements it produced). The cost is
 *  linear in the volume rendered whatever the split into formulas, so the bound is on the volume: once the formulas
 *  rendered in one call total this many characters, a formula that would pass the total is shown as its source instead,
 *  with a title saying why, and a smaller one that still fits renders. Five formulas at the cap, or several hundred
 *  display equations of ordinary size: a long paper's mathematics is 15,000 to 30,000 characters of TeX, so no real
 *  document meets it, and the worst case is bounded at a few seconds where it was unbounded. */
export const MATH_TEX_BUDGET_CHARS = 100000;

/** The largest size a formula may ask for, in ems (KaTeX's maxSize, review round 3). KaTeX's default is Infinity, and
 *  `\rule{5000em}{5000em}` in a reply laid a 78,650 px square in the transcript, `a\kern{50000em}b` a line 786,520 px
 *  wide that the page's overflow-x: hidden put beyond reach. 50 em is about the chat column (some 55 em at the chat's
 *  font size), so a rule or a space as wide as the column still renders and nothing reshapes the transcript; ordinary
 *  layout (a fraction, a radical, a matrix with a `\\[1em]` row gap) never nears it and renders byte for byte as it does
 *  without the option (md-sanitize-katex-browser.test.ts holds that identity against katex.render's own output).
 *  The cap is on each size a formula asks for, not on their sum: a row of a thousand capped rules is as wide as a row
 *  of that many characters, which the column clips as it clips any long inline formula (the transcript keeps its
 *  shape), and a column of a thousand capped rules is as tall as it says, some 776,000 px for 18,000 characters of
 *  TeX where a thousand plain rows are 19,000 px (review round 4, measured); the two length caps bound both. */
export const MATH_MAX_SIZE_EM = 50;

/** The most characters of macro bodies one formula may expand to (review round 3). The cap above measures the TeX as
 *  written, and KaTeX expands `\def` and `\newcommand` bodies before layout: `\def\a{<1,000 characters>}` followed by
 *  200 uses of `\a` is 1,409 characters of TeX and 200,000 of formula, 20 s of render; a nested chain of 1,077
 *  characters took 22 s; 400 uses of a 2,000-character body had not finished after 60 s. KaTeX's maxExpand counts
 *  EXPANSIONS, not the characters they produce (one per macro use, whatever the body's length), so no fixed value
 *  bounds the work: 1,000, the default, allows 1,000 uses of a body under the cap, and a value low enough to matter
 *  breaks ordinary formulas, whose `\,`, `\dots` and `\boxed` are macros that count against it (100 `\boxed` fail at
 *  50). So the bound is computed per formula (maxExpandFor below): each expansion pushes at most the longest macro
 *  body the formula defines, so maxExpand = this budget divided by that length, never above KaTeX's default (a short
 *  body is no reason to allow MORE expansions than plain KaTeX does), keeps the expanded formula within the budget plus
 *  the TeX as written, and a formula that defines no macro keeps KaTeX's default, which its built-in macros, whose
 *  bodies are a few tokens, never turn into a cost (measured: 100 `\boxed{x}` in 9 ms). The bound is an
 *  over-approximation once a formula defines a body longer than 20 characters: every expansion is then priced at that
 *  body, the built-in macros' included (`\,` costs 3, `\dots` 2, `\boxed` 1), so a formula that defines a 200-character
 *  body has 100 expansions for everything, and one that spends them on thin spaces is refused although its real
 *  expansion is small (review round 4, measured: a 200-character body used once beside 34 `\,` is refused). Over the
 *  bound KaTeX stops with its own visible error ("Too many expansions"), the source shown in place: the 200-use bomb
 *  and the chain both stop in about 10 ms. The value is the single-formula cap, so the most one formula lays out is
 *  two caps' worth, measured at 0.9 s for 40,000 flat characters here (node, KaTeX 0.18.1). The premise, that an
 *  expansion pushes a body as WRITTEN, holds for `\def` and `\newcommand`, whose bodies KaTeX stores unexpanded, and
 *  fails for `\edef` and `\xdef`, which store the EXPANDED body (review round 4): KaTeX charges that body's length
 *  once, at the definition, and one expansion per later use, whatever the stored length, so `\def\a{<20 characters>}
 *  \edef\b{<10 uses of \a>}` and 788 uses of `\b`, 1,635 characters of TeX under every bound here, was 998
 *  expansions and 157,600 characters of formula, 31 s of freeze over the real pipeline. A formula that defines a macro
 *  with either is shown as its source before KaTeX sees it (macroBounds's expandedBody), as the argument repeat is:
 *  no ordinary notation needs an expanded-at-definition macro. */
export const MATH_EXPANSION_BUDGET_CHARS = MATH_TEX_MAX_CHARS;

/** The class the source fallback wears (a `code` element carrying the TeX), so the sheets can dress it as unrendered
 *  source rather than as a code span the author wrote (review round 3: the two were identical in every computed
 *  property, and the title, the only marker, is out of reach on a phone). styles.css and feed.css carry the one rule,
 *  byte-equal; render.ts's highlighter leaves the element alone (it is TeX, not code, and auto-detection over 20,000
 *  characters of it cost 250 ms). */
export const MATH_SOURCE_CLASS = "md-math-src";

/** KaTeX's default for maxExpand (katex.mjs Settings), the value a formula that defines no macro renders under. */
const KATEX_DEFAULT_MAX_EXPAND = 1000;

// The commands that give a macro a body KaTeX expands: TeX's `\def` family (with `\global` or `\long` in front, the
// `\def` still matches) and LaTeX's `\newcommand` family. `\let` and `\futurelet` alias an existing command and add no
// body of their own, so the body they alias is counted where it is defined. `\edef` and `\xdef` are the two whose body
// KaTeX stores EXPANDED (katex.mjs, the def handler: expandTokens before macros.set), so the group as written is no
// measure of what a use pushes; macroBounds flags them and the fill shows the formula as source.
const MACRO_DEFINER = /\\(?:g?def|[ex]def|newcommand|renewcommand|providecommand|DeclareMathOperator)\b/g;
const EXPANDED_AT_DEFINITION = /^\\[ex]def$/;

/** The brace group starting at `open` (the index of a `{`): the index one past its matching `}`, or the text's length
 *  when the group never closes (KaTeX would reject the formula; the rest of the text is counted as the body, which can
 *  only tighten the bound). A backslash escapes the character after it, so `\{` and `\}` in a body are not braces. */
function braceGroupEnd(tex: string, open: number): number {
  let depth = 0;
  for (let i = open; i < tex.length; i++) {
    const ch = tex[i];
    if (ch === "\\") { i++; continue; }
    if (ch === "{") depth++;
    else if (ch === "}" && --depth === 0) return i + 1;
  }
  return tex.length;
}

/** What a formula's macro definitions let it expand to. `maxBody` is the longest brace group that follows a defining
 *  command, in characters (0 when the formula defines no macro): the body of a `\def\a{...}`; of a
 *  `\newcommand{\a}[1]{...}`, whose first group is the name, so the two groups after a command are both read and the
 *  longer counts; of a `\def\csname a\endcsname{...}`, since the group is read wherever it starts and a name KaTeX
 *  builds is no way round the count. `argRepeat` is true when a body uses one of its parameters more than once (`#1`
 *  twice): each use copies the argument, so `\def\a#1{#1#1}` nested nine deep over 5,000 characters is 512 copies of
 *  them, an amplification no expansion count bounds when the body is four characters long, and one no ordinary
 *  notation needs (`\newcommand{\abs}[1]{\left|#1\right|}` uses its argument once). `expandedBody` is true when a
 *  definer is `\edef` or `\xdef`: KaTeX stores their body expanded, charging its length once at the definition and one
 *  expansion per use however long it is, so `maxBody`, read as written, undercounts what a use pushes by the factor the
 *  body's own macros expand it (a 20-character `\a` ten times over is a 200-character body: 788 uses of it under the
 *  default count were 157,600 characters of formula). Exported for render-math.test.ts. */
export function macroBounds(tex: string): { maxBody: number; argRepeat: boolean; expandedBody: boolean } {
  let maxBody = 0, argRepeat = false, expandedBody = false;
  MACRO_DEFINER.lastIndex = 0;
  for (let m = MACRO_DEFINER.exec(tex); m; m = MACRO_DEFINER.exec(tex)) {
    if (EXPANDED_AT_DEFINITION.test(m[0])) expandedBody = true;
    let at = m.index + m[0].length;
    for (let group = 0; group < 2; group++) {
      // the first group: the next brace wherever it is, whatever spells the name before it; the second: only across
      // whitespace and an optional `[n]` parameter count, so a group further on in the formula is not read as a body
      let open = -1;
      if (group === 0) open = tex.indexOf("{", at);
      else { const next = /^\s*(?:\[[^\]]*\]\s*)?\{/.exec(tex.slice(at)); if (next) open = at + next[0].length - 1; }
      if (open < 0) break;
      const end = braceGroupEnd(tex, open);
      const body = tex.slice(open + 1, tex[end - 1] === "}" ? end - 1 : end);
      if (body.length > maxBody) maxBody = body.length;
      const seen = new Set<string>();
      for (const p of body.matchAll(/#([1-9])/g)) { if (seen.has(p[1])) argRepeat = true; seen.add(p[1]); }
      at = end;
    }
  }
  return { maxBody, argRepeat, expandedBody };
}

/** The maxExpand for a formula: KaTeX's default when it defines no macro, else the expansion budget divided by its
 *  longest body, clamped to at least 1 and at most KaTeX's default (a body under 20 characters leaves the default in
 *  place rather than loosening it), so whatever the count of uses, the bodies it expands stay within the budget. The
 *  bodies are read as written, which is what KaTeX stores for `\def` and `\newcommand`; a formula with an `\edef` or
 *  `\xdef` body never reaches KaTeX (renderMathPlaceholders shows it as source), so the count is not asked to bound it. */
export function maxExpandFor(tex: string): number {
  const { maxBody } = macroBounds(tex);
  return maxBody > 0 ? Math.max(1, Math.min(KATEX_DEFAULT_MAX_EXPAND, Math.floor(MATH_EXPANSION_BUDGET_CHARS / maxBody))) : KATEX_DEFAULT_MAX_EXPAND;
}

// Closing punctuation allowed right after the closing $ (plus whitespace / end-of-text).
// Includes markdown emphasis/strike markers so **$O(n)$** works, and the common CJK stops.
const AFTER_CLOSE = "[\\s.,;:!?)\\]}\"'*_~\\-、。，；：！？）】」]";

const INLINE_PAREN = /^\\\(([\s\S]+?)\\\)/;                 // \( .. \)   inline
const INLINE_BRACKET = /^\\\[([\s\S]+?)\\\]/;               // \[ .. \]   display
const INLINE_DOLLARS = /^\$\$([\s\S]+?)\$\$/;               // $$ .. $$   display
const INLINE_DOLLAR = new RegExp(
  "^\\$(?![\\s$])([^$\\n`]*?[^\\s$\\n`])\\$(?=" + AFTER_CLOSE + "|$)",
);

// Block-level display math: a $$ .. $$ or \[ .. \] paragraph of its own, so multi-line
// formulas never reach markdown's block rules (a "- " or "#" line inside a formula would
// otherwise be carved into a list or heading before the inline pass could see it).
const BLOCK_DOLLARS = /^ {0,3}\$\$([\s\S]+?)\$\$ *(?:\n+|$)/;
const BLOCK_BRACKET = /^ {0,3}\\\[([\s\S]+?)\\\] *(?:\n+|$)/;

function escapeText(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** The placeholder marked emits for a formula: the TeX as escaped text under the class that names the
 *  mode. `block` picks the tag, a div for a display paragraph of its own, a span inside a paragraph. */
export function mathPlaceholder(tex: string, display: boolean, block: boolean): string {
  const cls = display ? MATH_DISPLAY_CLASS : MATH_INLINE_CLASS;
  const tag = block ? "div" : "span";
  return `<${tag} class="${cls}">${escapeText(tex)}</${tag}>`;
}

export const mathBlock: TokenizerAndRendererExtension = {
  name: "mathBlock",
  level: "block",
  start(src: string) {
    const m = src.match(/(?:^|\n) {0,3}(?:\$\$|\\\[)/);
    return m ? m.index : undefined;
  },
  tokenizer(src: string) {
    const m = BLOCK_DOLLARS.exec(src) || BLOCK_BRACKET.exec(src);
    if (!m || !m[1].trim()) return undefined;
    return { type: "mathBlock", raw: m[0], text: m[1].trim(), display: true } as MathToken;
  },
  renderer(token) {
    return mathPlaceholder((token as MathToken).text, true, true);
  },
};

export const mathInline: TokenizerAndRendererExtension = {
  name: "mathInline",
  level: "inline",
  start(src: string) {
    const m = src.match(/\$|\\\(|\\\[/);
    return m ? m.index : undefined;
  },
  tokenizer(src: string) {
    let m: RegExpExecArray | null; let display = false;
    if ((m = INLINE_PAREN.exec(src))) display = false;
    else if ((m = INLINE_BRACKET.exec(src)) || (m = INLINE_DOLLARS.exec(src))) display = true;
    else m = INLINE_DOLLAR.exec(src);
    if (!m || !m[1].trim()) return undefined;
    return { type: "mathInline", raw: m[0], text: m[1].trim(), display } as MathToken;
  },
  renderer(token) {
    const t = token as MathToken;
    return mathPlaceholder(t.text, t.display, false);
  },
};

/** The belt under the fill: the TeX as text in a code element where the placeholder stood, its `title` saying why it is
 *  not a formula, so a formula can never blank a message and the reader still sees what was written. A block placeholder
 *  (the div a display paragraph of its own becomes) turns into a code block; a span, display mode or not, into a code
 *  span, so the paragraph it sits in survives the serialization to innerHTML (a <pre> inside a <p> splits the paragraph
 *  when the HTML is parsed again). The code element wears MATH_SOURCE_CLASS, the hook for the sheets' dress and the
 *  highlighter's exemption, whichever shape it takes; the title sits on the outer element, the whole of what is shown. */
function showSource(el: HTMLElement, tex: string, why: string): void {
  const doc = el.ownerDocument;
  const code = doc.createElement("code");
  code.className = MATH_SOURCE_CLASS;
  code.textContent = tex;
  let shown: HTMLElement = code;
  if (el.tagName === "DIV") { shown = doc.createElement("pre"); shown.appendChild(code); }
  shown.setAttribute("title", why);
  el.replaceWith(shown);
}

/** Render KaTeX into every math placeholder under `root`, the SANITIZED DOM (sanitizeMd's body), and
 *  unwrap each so the rendered `.katex` (or `.katex-display`) root stands where the placeholder stood,
 *  exactly where marked's own KaTeX output used to: the comment highlights' closest(".katex") pairing
 *  and the anchor map see the shape they always did. The markup is katex.render's, not KaTeX's string
 *  renderer's, which main used: the DOM builder sets class="" on a classless span and the browser serializes
 *  its styles with a space after each colon, so the bytes differ from main's while every rect and every
 *  text is the same, and nothing reads the bytes (the highlights pair on the .katex root, the anchor map
 *  on text; md-sanitize-katex-browser.test.ts takes the DOM path as the reference and says why). The
 *  selector reaches a placeholder an author typed by hand as well (no class name is special-cased; plan
 *  item 7), so in a bundle that carries the grammar such a paragraph's rendered text no longer equals
 *  its source and the anchor map refuses it with the Raw view offered, as it refuses a paragraph with
 *  `$x^2$` there today (Slice 5's math holes are where math meets the map); a bundle without the grammar
 *  has no fill and maps it as main did. Four bounds stand ahead of the one katex.render
 *  call, each shown as the source with its reason (showSource): a formula longer than MATH_TEX_MAX_CHARS;
 *  a formula that would take the call's rendered total past MATH_TEX_BUDGET_CHARS (the running total is
 *  this call's, so it is one message's or one note's; a shorter formula after it still renders while it
 *  fits); a formula whose macro definitions repeat an argument; a formula that defines a body with `\edef`
 *  or `\xdef`, which KaTeX stores expanded (macroBounds; the two cases no expansion count over the bodies
 *  as written can bound). The call itself runs under maxSize and a maxExpand computed from the formula's
 *  macro bodies (maxExpandFor), so KaTeX's own bounds hold too. throwOnError: false renders bad TeX as
 *  visibly-flagged source instead of throwing; the catch
 *  is a belt for the residual throws (an internal error), showing the source the same way and saying so
 *  on the console once per call, so a formula can never blank a message. A second run over the same
 *  root is a no-op: no placeholder survives the first. Plain and exported: chat-md.ts registers it as
 *  sanitizeMd's post-pass, and the tests call it directly. */
export function renderMathPlaceholders(root: ParentNode): void {
  let rendered = 0;          // characters of TeX handed to KaTeX so far in this call: the budget's meter
  let reported = false;      // the belt's console report, once per call
  root.querySelectorAll("." + MATH_INLINE_CLASS + ", ." + MATH_DISPLAY_CLASS).forEach((node) => {
    const el = node as HTMLElement;
    const display = el.classList.contains(MATH_DISPLAY_CLASS);
    const tex = el.textContent || "";
    if (!tex.trim()) { el.replaceWith(...Array.from(el.childNodes)); return; }
    if (tex.length > MATH_TEX_MAX_CHARS) {
      showSource(el, tex, "Not rendered: " + tex.length + " characters of TeX; the limit is " + MATH_TEX_MAX_CHARS + ".");
      return;
    }
    if (rendered + tex.length > MATH_TEX_BUDGET_CHARS) {
      showSource(el, tex, "Not rendered: the formulas above already total " + rendered + " characters of TeX; the limit for one message or note is " + MATH_TEX_BUDGET_CHARS + ".");
      return;
    }
    if (macroBounds(tex).argRepeat) {
      showSource(el, tex, "Not rendered: a macro in this formula repeats one of its arguments, which can multiply the formula without bound.");
      return;
    }
    if (macroBounds(tex).expandedBody) {
      showSource(el, tex, "Not rendered: a macro in this formula is defined with \\edef or \\xdef, whose stored body is its expansion; its uses can multiply the formula without bound.");
      return;
    }
    rendered += tex.length;
    try {
      katex.render(tex, el, { displayMode: display, throwOnError: false, output: "html", trust: false, maxSize: MATH_MAX_SIZE_EM, maxExpand: maxExpandFor(tex) });
      el.replaceWith(...Array.from(el.childNodes));
    } catch (e) {
      if (!reported) { reported = true; console.error("math: KaTeX could not lay out a formula; its source is shown instead", e); }
      showSource(el, tex, "Not rendered: this formula could not be laid out.");
    }
  });
}
