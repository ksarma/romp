// TeX math for chat markdown: inline \( .. \) and $ .. $, display \[ .. \] and $$ .. $$
// (the user 2026-08-03). marked has no math syntax, so without this every formula an agent
// writes reaches the transcript as raw TeX source.
//
// Rendering happens AFTER the sanitizer, not inside marked (plans/markdown-viewer.md Slice 1 review,
// 2026-09-07). KaTeX carries every piece of vertical layout in inline `style` (a strut's height and
// vertical-align, a vlist row's top, a fraction line's border width, a radical's padding), and the
// shared sanitizer (md-sanitize.ts) keeps only colour declarations in a `style` attribute, so KaTeX's
// output passed through sanitizeMd would come back flat: numerator and denominator on one line, a
// superscript at the baseline, the radical drawn over its radicand. The extensions therefore emit an
// INERT placeholder (class md-math-inline or md-math-display, a span inside a paragraph or a div for a
// display paragraph of its own, the TeX as its text, HTML-escaped) that the sanitizer treats as any
// element with text, and renderMathPlaceholders below renders KaTeX into each placeholder on the
// sanitized DOM, so its styles never meet DOMPurify. Nothing an author writes gains by hand-writing the
// placeholder markup: KaTeX renders only what TeX says, under `trust: false` (no \href, \url,
// \includegraphics, \htmlClass, \htmlStyle, \htmlData), which is KaTeX's own safety model, with its two
// bounds set as well (maxSize on the sizes a formula asks for, maxExpand on its macro expansion, computed
// per formula; the constants below say why) and this module's own bounds on the TeX it hands over (one
// formula's length, one message's total). KaTeX renders with output: "html" ONLY, no MathML twin. The
// KaTeX layout CSS ships via styles.css AND feed.css, each with @import "katex/dist/katex.min.css" (esbuild
// inlines the sheet into both and emits the fonts to dist/fonts/ once, the same hashed names): styles.css
// dresses the chat page and the Files pane's page, feed.css the feed page, which links no styles.css and hosts
// the viewer too, so it took the import in Slice 4 of plans/markdown-viewer.md (render-math.test.ts and
// math-bundles.test.ts pin both sheets; a third sheet that hosts the viewer needs the same import). md-config.ts
// registers the post-pass with the sanitizer at load (md-sanitize.ts registerMdPostPass), and every bundle that
// hosts the chat or the viewer (render.js, files.js, feed.js) imports md-config.ts, so every sanitizeMd call
// renders math on every surface: the chat's md() and userMd(), and the viewer's mdBlock in the chat page, the
// Files pane and the feed (Slice 4, decision 1; before it files.js and feed.js had neither the grammar nor the
// fill nor KaTeX).
//
// KaTeX itself is not in those bundles (iOS item 6, 2026-10-02): it ships as its own on-demand bundle,
// dist/math-chunk.js (math-chunk.ts), and this module types the part it calls structurally and imports no
// KaTeX, not even a type (math-lazy.test.ts reads every import and every bundle's inputs). The grammar, the
// bounds and the fill stay here and need no KaTeX until a formula is about to be laid out. With the engine
// loaded the fill runs synchronously, exactly as before. Without it a formula that passes every bound stays
// as its placeholder, the TeX as text in the sheets' quiet pending dress (styles.css and feed.css, the
// .md-math-inline and .md-math-display rule), stamped with its call's group so the arrival can charge the
// per-message budget per message, and the fill asks for the chunk: one script tag, its URL and nonce taken
// from the page's own bundle tag (chunk-url.ts), added once the document has loaded (a tag added before its load
// event joins it, and a stalled chunk would hold the page's load), while the two common KaTeX faces load beside it (the sheet
// declares them font-display: block, so laying out before they arrive would show a blank formula). When the
// chunk has run and the faces have settled, the settle handlers run (onMathSettled: the chat keeps the
// reader's place around the swap, the viewer repaints a paint it held) and then one fill over the whole
// document renders every pending placeholder still in it. The fill lays out with KaTeX only once the load has
// SETTLED as a success: a chunk that has registered while its faces still load, or one that lands after the load
// failed, lays nothing out early (the review of iOS item 6, round 1: a formula met in either window was laid
// out at once, past the face wait and the viewer's hold). A load that fails, registers nothing or has not
// settled within MATH_CHUNK_BACKSTOP_MS is a failure: every pending formula becomes the source fallback with
// a title naming the failure, marked as one the failure made (MATH_FAILED_ATTR, with its call's group), the
// console says so once per failed attempt, and later formulas take the same fallback at once: nothing waits
// on a retry, so the chat shows the TeX and the viewer paints. A failed load is retried, and only events arm
// a retry, since renders repeat on every streaming delta and kernel push and must not be what asks: the page
// life's first failure, the shim's reconnect (romp:wsup) and the window's `online` each set one flag (it does
// not stack), and the next fill that meets a formula uses it up (not the failure's own fill, the arrival's
// fill over the document or the viewer's repaint the settle decided on, which run inside the settle, the
// repaint as if inside it when a press on the card parks it until the release: asSettleFill). So a chunk that
// 404s for good costs at most two requests per page life, plus one per reconnect or online event, at any render rate (the
// review of iOS item 6, round 1; the editor and PDF loaders retry the same way since 2026-09-06, on a gesture). A page
// with no bundle tag to derive the URL from fails the same way every time and arms nothing. Whichever attempt
// succeeds first, a retry or an earlier attempt landing after its backstop (the chunk, or the faces), runs the
// arrival, once: the marked fallbacks become placeholders again and the fill over the document lays out every
// formula, those included, while the chat keeps its reader's line; the viewers' bodies (MATH_REPAINT_ATTR) are left
// to their own settle handlers, which paint the note again, its place kept, once any press on the card is released.
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
import type { TokenizerAndRendererExtension, Tokens } from "marked";
import { frameOf, memoBlockStart, type Frame } from "./md-block-start";
import { chunkScript } from "./chunk-url";

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
 *  document meets it, and the worst case is bounded at a few seconds where it was unbounded. The cost per character
 *  depends on the shape as well as the volume (review round 6, measured): a one-row matrix of one-character cells
 *  (`a&a&...`) lays out about seven elements per character where a flat sum lays out three, and five of them at the
 *  cap took 4.7 to 5.5 s of render and layout where five flat sums of the same volume took 1.8 to 1.9 s (headless
 *  Chromium, KaTeX 0.18.1); it is the densest shape the review found, so that is the budget's worst case, while 673
 *  ordinary display equations totalling 99,000 characters took 1.2 s. The budget bounds volume, not time: a worker with
 *  a time budget (plans/markdown-viewer.md, the Slice 4 design note) is what bounds the time whatever the shape. */
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
 *  bound KaTeX throws, and the fill shows the formula as source with the reason and the count in its title, as it does
 *  over its own bounds (review round 5: KaTeX's red error text stood there before, and this is the one bound an ordinary
 *  formula can meet); the 200-use bomb and the chain both stop in about 10 ms. The value is the single-formula cap, so the most one formula lays out is
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

// The commands that define a macro in KaTeX 0.18.1 (katex.mjs: the `\def` handler, the `\newcommand` macros, and `\let`
// and `\futurelet`, which alias a command; `\global` and `\long` in front change nothing the scan needs, since the
// defining token still appears). Each is recognised by its TOKEN alone, whatever follows it: KaTeX's `\def` takes as the
// name the next token but `\ { } $ & # ^ _`, so a control word (`\a`), a control symbol (`\!`) and a single character
// (`1`) all name a macro, and a scan that required a word boundary after the definer, as JS's `\b` does, never saw
// `\def1{...}` (review round 5: the round-3 and round-4 bombs returned under a digit name). A control word ends where
// KaTeX's lexer ends it, at the first character outside [a-zA-Z@], so `\deficit` and `\def@` are other commands. `\edef`
// and `\xdef` are the two whose body KaTeX stores EXPANDED (the def handler: expandTokens before macros.set), so the
// group as written is no measure of what a use pushes; macroBounds flags them and the fill shows the formula as source.
// `\DeclareMathOperator` is not in KaTeX 0.18.1 (the formula fails as an undefined control sequence) and is listed for a
// KaTeX that adds it; `\newenvironment` is not in KaTeX either and defines no macro there.
const BODY_DEFINERS = new Set(["\\def", "\\gdef", "\\edef", "\\xdef", "\\newcommand", "\\renewcommand", "\\providecommand", "\\DeclareMathOperator"]);
const ALIASERS = new Set(["\\let", "\\futurelet"]);
const EXPANDED_AT_DEFINITION = new Set(["\\edef", "\\xdef"]);
/** A control sequence at a backslash, as KaTeX's lexer reads it: a control word of letters and `@`, else the backslash
 *  and the one character after it (a control symbol: `\!`, `\{`, `\\`), else the bare backslash ending the text. */
const CONTROL_SEQ = /\\(?:[a-zA-Z@]+|[^])?/y;
/** A `\newcommand` body after its name group: across whitespace and an optional `[n]` parameter count only, so a group
 *  further on in the formula is not read as a body. */
const SECOND_GROUP = /\s*(?:\[[^\]]*\]\s*)?\{/y;

function controlSeqAt(tex: string, at: number): string {
  CONTROL_SEQ.lastIndex = at;
  return CONTROL_SEQ.exec(tex)![0];
}

/** The next token from `at`, whitespace skipped: a control sequence, else one character; "" at the end of the text. */
function tokenAt(tex: string, at: number): { text: string; end: number } {
  let i = at;
  while (i < tex.length && /\s/.test(tex[i])) i++;
  if (i >= tex.length) return { text: "", end: i };
  const text = tex[i] === "\\" ? controlSeqAt(tex, i) : tex[i];
  return { text, end: i + text.length };
}

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

/** The index of the first `{` at or after `at` that opens a group (a control symbol's `\{` is not one), or -1. */
function nextGroupOpen(tex: string, at: number): number {
  for (let i = at; i < tex.length; i++) {
    if (tex[i] === "\\") { i++; continue; }
    if (tex[i] === "{") return i;
  }
  return -1;
}

export type MacroBounds = { maxBody: number; argRepeat: boolean; expandedBody: boolean; unplacedBody: boolean };

/** What a formula's macro definitions let it expand to, read from the TeX as text. `maxBody` is the longest brace group
 *  that follows a defining command, in characters (0 when the formula defines no macro): the body of a `\def\a{...}`; of
 *  a `\newcommand{\a}[1]{...}`, whose first group is the name, so the two groups after a command are both read and the
 *  longer counts; the group is read wherever it starts, so nothing between the definer and the brace (a name, parameters,
 *  a delimiter) matters. `argRepeat` is true when any brace group uses one parameter more than once (`#1` twice): each
 *  use copies the argument, so `\def\a#1{#1#1}` nested nine deep over 5,000 characters is 512 copies of them, an
 *  amplification no expansion count bounds when the body is four characters long, and one no ordinary notation needs
 *  (`\newcommand{\abs}[1]{\left|#1\right|}` uses its argument once); every group is read, not only a definer's, so a
 *  body the scan cannot place (below) is still caught. `expandedBody` is true when a definer is `\edef` or `\xdef`:
 *  KaTeX stores their body expanded, charging its length once at the definition and one expansion per use however long
 *  it is, so `maxBody`, read as written, undercounts what a use pushes by the factor the body's own macros expand it (a
 *  20-character `\a` ten times over is a 200-character body: 788 uses of it under the default count were 157,600
 *  characters of formula). `unplacedBody` is true when a body is not where the scan reads it (review round 5), so
 *  `maxBody` bounds nothing and maxExpandFor prices every expansion at the formula's own length instead, which no body
 *  written in it exceeds: a definer with no brace group after it (the body is one token, or the formula is an error); a
 *  `\let` or `\futurelet` that aliases a definer, whose later uses put their bodies wherever they like
 *  (`\let\d\def \frac{a}{b} \d\b{<1,000>}` read `{a}` as the body, and 200 uses passed at KaTeX's default count); a
 *  definer or an aliaser inside a brace group, stored in a body and run at each use, where a body assembled from the
 *  arguments is up to nine groups long (`\def\d#1...#9{\def\b{#1...#9}}` over nine 2,000-character groups, 18,154
 *  characters of TeX under every bound, had not finished after two minutes). Exported for render-math.test.ts. */
export function macroBounds(tex: string): MacroBounds {
  let maxBody = 0, argRepeat = false, expandedBody = false, unplacedBody = false;
  let depth = 0;
  const params: Set<string>[] = [];          // per open brace group, the parameters seen inside it so far
  // the group after a definer, found and measured once however many definers stand before it
  let nextFrom = -1, nextOpen = -1, endOf = -1, endAt = -1;
  const groupAfter = (at: number): number => {
    if (nextFrom < 0 || nextFrom > at || (nextOpen >= 0 && nextOpen < at)) { nextFrom = at; nextOpen = nextGroupOpen(tex, at); }
    return nextOpen;
  };
  const groupEnd = (open: number): number => { if (open !== endOf) { endOf = open; endAt = braceGroupEnd(tex, open); } return endAt; };
  for (let i = 0; i < tex.length; i++) {
    const ch = tex[i];
    if (ch === "{") { depth++; params.push(new Set()); continue; }
    if (ch === "}") { if (depth > 0) { depth--; params.pop(); } continue; }
    if (ch === "#") {
      const d = tex[i + 1];
      if (d >= "1" && d <= "9") { for (const seen of params) { if (seen.has(d)) argRepeat = true; seen.add(d); } i++; }
      continue;
    }
    if (ch !== "\\") continue;
    const cs = controlSeqAt(tex, i);
    const after = i + cs.length;
    i = after - 1;
    if (BODY_DEFINERS.has(cs)) {
      if (EXPANDED_AT_DEFINITION.has(cs)) expandedBody = true;
      if (depth > 0) { unplacedBody = true; continue; }
      let at = after, read = 0;
      for (let group = 0; group < 2; group++) {
        let open = -1;
        if (group === 0) open = groupAfter(at);
        else { SECOND_GROUP.lastIndex = at; const next = SECOND_GROUP.exec(tex); if (next) open = next.index + next[0].length - 1; }
        if (open < 0) break;
        const end = groupEnd(open);
        const body = end - open - (tex[end - 1] === "}" ? 2 : 1);
        if (body > maxBody) maxBody = body;
        read++;
        at = end;
      }
      if (read === 0) unplacedBody = true;
    } else if (ALIASERS.has(cs)) {
      if (depth > 0) { unplacedBody = true; continue; }
      let t = tokenAt(tex, after);                                  // the name
      // \let: an optional `=`, then the token aliased; \futurelet: two tokens, the second of them aliased
      for (let n = cs === "\\let" ? 1 : 2; n > 0; n--) {
        t = tokenAt(tex, t.end);
        if (t.text === "=") t = tokenAt(tex, t.end);
        if (BODY_DEFINERS.has(t.text) || ALIASERS.has(t.text)) unplacedBody = true;
      }
    }
  }
  return { maxBody, argRepeat, expandedBody, unplacedBody };
}

/** The maxExpand for a formula: KaTeX's default when it defines no macro, else the expansion budget divided by its
 *  longest body, clamped to at least 1 and at most KaTeX's default (a body under 20 characters leaves the default in
 *  place rather than loosening it), so whatever the count of uses, the bodies it expands stay within the budget. The
 *  bodies are read as written, which is what KaTeX stores for `\def` and `\newcommand`; a formula with an `\edef` or
 *  `\xdef` body never reaches KaTeX (renderMathPlaceholders shows it as source), so the count is not asked to bound it;
 *  a formula with a body the scan cannot place (macroBounds's unplacedBody) is priced at its own length, which no body
 *  written in it exceeds, so it has the budget over its length in expansions and pushes at most the budget's worth.
 *  The bounds are read from the TeX unless the caller passes the ones it holds: the fill reads a formula's once, for
 *  its two refusals and this count (review round 6: three scans of the TeX per formula before). */
export function maxExpandFor(tex: string, bounds: MacroBounds = macroBounds(tex)): number {
  const { maxBody, unplacedBody } = bounds;
  const body = unplacedBody ? tex.length : maxBody;
  return body > 0 ? Math.max(1, Math.min(KATEX_DEFAULT_MAX_EXPAND, Math.floor(MATH_EXPANSION_BUDGET_CHARS / body))) : KATEX_DEFAULT_MAX_EXPAND;
}

/** The ink of KaTeX's flagged text: the `span.katex-error` a syntax error renders as under throwOnError: false, and the
 *  text of an unsupported command inside a formula. KaTeX writes the string verbatim into an inline `style` (its default
 *  is #cc0000, which read at 2.8:1 on the dark page, under the 4.5:1 the sheets hold reading text to; the Slice 4 review,
 *  as the fill reached the Files pane and the feed), so a theme token goes in its place: `--math-err`, declared in both
 *  theme blocks of styles.css and feed.css (theme-parity.test.ts holds it readable on --bg in both themes;
 *  md-config-math-error-colour.test.ts the token's presence). No fallback on purpose: where no sheet defines it the text
 *  inherits the page's ink and stays readable, and a page of ours always loads one of the two sheets. */
export const MATH_ERROR_COLOR = "var(--math-err)";

/** What every katex.render call here passes: KaTeX's html output only (no MathML twin), no trusted command (KaTeX's own
 *  safety model), the size cap and the error ink; the mode, the per-formula expansion count and whether to throw are the
 *  call's. trust: false is KaTeX's own default, spelled out so that enabling trust is a visible edit (render-math.test.ts
 *  pins the option): under it no TeX command mints a link, an image or an HTML attribute of the author's choosing. */
const KATEX_OPTIONS = { output: "html", trust: false, maxSize: MATH_MAX_SIZE_EM, errorColor: MATH_ERROR_COLOR } as const;

/** The part of KaTeX the fill calls, typed here by its shape: KaTeX belongs to the on-demand chunk (math-chunk.ts), which
 *  registers it as `globalThis.__rompKatex`, and nothing in this module imports it, a type included. */
type MathEngine = {
  render(tex: string, el: HTMLElement, options: object): void;
  ParseError: new (...args: never[]) => Error;
};

/** KaTeX once the chunk has run (or a test bundle imported math-chunk.ts for its side effect), else null. */
function engine(): MathEngine | null {
  const k = (globalThis as { __rompKatex?: MathEngine }).__rompKatex;
  return k && typeof k.render === "function" ? k : null;
}

/** The attribute a formula waiting for the engine carries: the number of the fill call that met it, so the fill that renders
 *  it later charges MATH_TEX_BUDGET_CHARS per original call (one message, one note) and not over everything pending in a view
 *  at once. Set after the sanitizer, which keeps no data-* attribute an author wrote (md-sanitize.ts ALLOW_DATA_ATTR: false),
 *  so no author picks a group. */
export const MATH_CALL_ATTR = "data-math-call";
const PLACEHOLDER_SEL = "." + MATH_INLINE_CLASS + ", ." + MATH_DISPLAY_CLASS;

/** How long the chunk may take to load, with the two common faces, before the load counts as failed: ui/CLAUDE.md's loading
 *  rule's backstop. The viewer holds its loader over a note with math until the engine arrives (file-view.ts holdOverBody puts
 *  it over what the body showed), and a chunk fetch that stalls without erroring fires no event at all, so this is the one end
 *  that has none. It counts from the chunk's request, and the request waits for the page's load event (attempt): before that
 *  event nothing bounds the wait, and the viewer's Raw view, or closing the viewer, is the way out. The size follows the PDF
 *  renderer's (file-view.ts PDF_RENDER_BACKSTOP_MS, twice the pane loader's 30 s that has never fired, because the wait
 *  includes a fetch), and it never fires in the load path: the chunk is about 86 KB served. */
export const MATH_CHUNK_BACKSTOP_MS = 60_000;

/** The attribute a source fallback carries when the load's failure made it, and not one of the fill's bounds: the formula's
 *  mode ("display" or "inline"), beside MATH_CALL_ATTR for its call's group, so a later success puts the placeholder back as it
 *  was and lays it out with the rest (restoreFailedFormulas). Set by the fill alone: the sanitizer keeps no data-* attribute an
 *  author wrote, so no author marks a code element of theirs as a formula. */
export const MATH_FAILED_ATTR = "data-math-failed";
const FAILED_SEL = "[" + MATH_FAILED_ATTR + "]";

/** The attribute a root carries when its owner repaints it at the renderer's arrival: both viewers' bodies (file-view.ts), whose
 *  settle handlers paint the note again from its text. The arrival leaves the failure's marked fallbacks under such a root as they
 *  are, so nothing in it moves before its owner's one repaint, which a press on the viewer's card holds until the release (the
 *  review of iOS item 6, round 2: re-filled in place under a press, a formula's growth moved the line under the still pointer, and
 *  the release clicked the paragraph instead of the link it pressed). The chat and the feed carry none: the arrival re-fills their
 *  fallbacks in place, and the chat keeps its reader's line around that. Set by the owner on its own element; the sanitizer keeps
 *  no data-* attribute an author wrote, so no author's markup opts out. */
export const MATH_REPAINT_ATTR = "data-math-repaints";
const REPAINTED_SEL = "[" + MATH_REPAINT_ATTR + "]";

let mathCalls = 0;                                        // the group numbers handed out so far
// The load, for the page's life: idle until the first formula, loading while the first attempt's chunk and faces are out, ready
// once an attempt has settled as a success, failed after a failure (until a success; a retry runs while the state stays failed,
// so nothing waits on it). The fill lays out with KaTeX only while idle (a bundle that imported the chunk for its side effect
// asks for nothing) or ready.
let engineLoad: "idle" | "loading" | "ready" | "failed" = "idle";
let engineFailure = "";                                   // what went wrong last, for the fallback's title
let failures = 0;                                         // attempts that have failed in this page life: the first arms a retry
let retryArmed = false;                                   // one retry, armed by an event, used by the next fill that meets a formula
let retryable = true;                                     // false once the page proved to have no bundle tag to derive the URL from
let settling = 0;                                         // inside engineSettled, or a viewer's parked repaint it decided on (asSettleFill): its fills use no retry
let leaving = false;                                      // the page is going: a reload through the reload core (latchOnLeave)
let leaveHooked = false;                                  // latchOnLeave's hooks are on (once per page life)
const settleHandlers: Array<() => (() => void) | void> = [];

/** Arm one retry of a failed load, the flag set and not counted (a second event before the next formula changes nothing). The
 *  events that arm it are the page life's first failure (in attemptFailed) and the two below, both a sign the network may be
 *  back: the pane shim's reconnect, romp:wsup, on a kernel page (the shim dispatches it at every reopen of the page's socket;
 *  a page without the shim, the VS Code webview, has the second only), and the window's `online`. A load that is not failed,
 *  or a page with no bundle tag to derive the URL from, arms nothing. */
function armRetry(): void {
  if (engineLoad === "failed" && retryable) retryArmed = true;
}
if (typeof window !== "undefined" && typeof window.addEventListener === "function") {
  window.addEventListener("romp:wsup", armRetry);
  window.addEventListener("online", armRetry);
}

/** A page that is leaving cancels a chunk request in flight, and WebKit fires the tag's error as the navigation starts: that is no
 *  failed load (the review of iOS item 6, round 2, extra5-1: the dying page logged a false failure line and turned every waiting
 *  formula into its source for the whole provisional load). The latch is set by a reload through the reload core: its fire step
 *  (kernel.py _RELOAD_CORE_JS fire) runs persist, which calls each window's __rompShimPersist, then location.reload, and the pane shim
 *  defines that hook on every kernel page that loads this module (the chat, the feed, the Files pane, Waiting); this chains onto it.
 *  That hook is the one sign of a reload romp started. A beforeunload sets nothing (the review's round 3, extra5-1): iOS Safari does not
 *  fire it, and in Chromium one that no unload follows (a navigation started from the browser's own controls that never commits: a
 *  download, a 204, a cancelled one) left the latch set for the rest of the page life, so a real load failure showed only at the
 *  backstop, under the backstop's reason. While the latch is set a tag's error fails nothing and the attempt's backstop stays its end,
 *  in case the page does not unload after all; pageshow, the page shown again from the back-forward cache, clears it. Hooked when the
 *  first attempt sends its request, after the page's load event, so the shim's hook exists by then; a page without the shim (the VS
 *  Code webview) has no reload core to latch on. What stays, in WebKit on iOS and on the desktop alike: a reload that does not go
 *  through the fire step still logs one false line on the dying page, the browser's own reload control and romp's direct
 *  location.reload() calls alike (kernel.py: the pane shim's Reload on its connection and build bars, the shell's stale-connection
 *  Reload with no offer standing, the update wait's and the boot poll's reloads; render.ts: the chat's federation-failure Reload); and
 *  a reload through the fire step that the browser refuses leaves the latch set (no pageshow follows), so a later attempt's tag error
 *  in that page life waits for its backstop. */
function latchOnLeave(): void {
  if (leaveHooked || typeof window === "undefined" || typeof window.addEventListener !== "function") return;
  leaveHooked = true;
  const w = window as unknown as { __rompShimPersist?: (...a: unknown[]) => unknown };
  const shim = w.__rompShimPersist;
  if (typeof shim === "function") w.__rompShimPersist = function (this: unknown, ...a: unknown[]) { leaving = true; return shim.apply(this, a); };
  window.addEventListener("pageshow", () => { leaving = false; });
}

/** Whether `root` holds a formula still waiting for the engine: after a fill, a placeholder that is left is one. */
export function mathPendingIn(root: ParentNode): boolean {
  return !!root.querySelector(PLACEHOLDER_SEL);
}

/** Whether `root` holds a formula the load's failure showed as its source, which the arrival of a later success lays out
 *  (restoreFailedFormulas): the chat's settle handler counts such a view with the ones that held a waiting formula, and the
 *  viewer repaints a paint that holds one, so the success keeps the reader's line and the viewer's place as a first arrival
 *  does. Never true before the load's first failure. */
export function mathFailedIn(root: ParentNode): boolean {
  return !!root.querySelector(FAILED_SEL);
}

/** Run `handler` when the engine's load settles, either way, BEFORE the fill over the document renders what is pending (or
 *  shows it as source); a function it returns runs AFTER that fill. The chat reads the reader's place before and writes it
 *  back after; the viewer repaints a paint it held. Returns the function that removes the handler. */
export function onMathSettled(handler: () => (() => void) | void): () => void {
  settleHandlers.push(handler);
  return () => { const i = settleHandlers.indexOf(handler); if (i >= 0) settleHandlers.splice(i, 1); };
}

/** Run a repaint a settle handler decided on, later, as a fill inside that settle: it uses no retry (settling, requestEngine). The
 *  viewers park the repaint their settle handler decides on while a press holds the card (file-view.ts mathHold) and run it at the
 *  release, outside engineSettled, so a failure met under a press spent the retry the failure armed at the release: a second
 *  request and a second console line, where the same failure with no press asks for nothing (the check of the round-2 pass of the
 *  review of iOS item 6). A retry an event arms meanwhile stays armed for the next fill after it. */
export function asSettleFill(run: () => void): void {
  settling++;
  try { run(); } finally { settling--; }
}

/** The two faces nearly every formula uses, loaded beside the chunk: katex.min.css declares every KaTeX face
 *  font-display: block, so a formula laid out before its face arrives is blank for the font's block period (a few seconds)
 *  and then drawn in a fallback face until its own lands. Settled either way, never thrown. */
function katexFaces(): Promise<unknown> {
  const faces = (document as { fonts?: { load(font: string): Promise<unknown> } }).fonts;
  if (!faces || typeof faces.load !== "function") return Promise.resolve();
  return Promise.all(["1em KaTeX_Main", "italic 1em KaTeX_Math"].map((f) => faces.load(f).catch(() => null)));
}

/** Ask for the chunk when the fill meets a formula it cannot lay out: the page life's first attempt (idle), or a retry while the
 *  load is failed and a retry is armed, which this uses up. A fill inside the settle (the failure's own fill over the document,
 *  the arrival's, a viewer's repaint in a settle handler, or that repaint parked under a press and run at the release through
 *  asSettleFill) uses none, so a failure cannot re-arm itself through its own render,
 *  and a persistent 404 costs the first request, the one retry the failure arms, and one per later event, at any render rate. */
function requestEngine(): void {
  if (typeof document === "undefined") return;
  if (engineLoad === "idle") engineLoad = "loading";
  else if (engineLoad === "failed" && retryArmed && settling === 0) retryArmed = false;
  else return;
  attempt();
}

/** One attempt: a script tag beside the page's bundle (chunk-url.ts), the faces in parallel. A retry while an earlier attempt is
 *  still out (stalled past its backstop) adds a fresh tag all the same, as the PDF loader does, and whichever attempt succeeds first
 *  runs the arrival. Whether that tag is a fresh request depends on the engine, as measured under Playwright's routing (the leg's
 *  stalled-first scene asserts the two tags and reports the request count per engine, math-chunk-leg.ts): Chromium serves a script
 *  URL already in flight from that one fetch, so there the retry waits on the stalled answer, while WebKit and Firefox send a new
 *  request. After an error or a 404 the first fetch is over, and the retry is a new request in every engine. Every end settles
 *  asynchronously, never inside the fill that asked, so a fill is never re-entered by its own attempt. The attempt fails once, at its
 *  first failure end (an error, a load that registered nothing, its backstop), and a later failure end of it is silent; an answer of
 *  it that SUCCEEDS after that (the chunk, or the faces, landing after the backstop) is a success all the same. A tag's error while
 *  the page is leaving is no failure end (latchOnLeave). */
function attempt(): void {
  const tag = chunkScript("math-chunk.js");
  if (!tag) {
    retryable = false;                                    // no URL now means no URL later: nothing a retry could change
    queueMicrotask(() => attemptFailed("no bundle script on this page to derive the math renderer's URL from"));
    return;
  }
  let failed = false, done = false;
  let backstop: ReturnType<typeof setTimeout> | undefined;
  const fail = (why: string): void => {
    if (failed || done) return;
    failed = true;
    clearTimeout(backstop);
    attemptFailed(why);
  };
  const succeed = (): void => {
    if (done) return;
    done = true;
    clearTimeout(backstop);
    if (engineLoad !== "ready") engineSettled(null);      // the first success runs the arrival; a second is a no-op
  };
  const request = (): void => {
    latchOnLeave();
    const faces = katexFaces();
    backstop = setTimeout(() => fail("the math renderer did not load within " + MATH_CHUNK_BACKSTOP_MS / 1000 + " seconds"), MATH_CHUNK_BACKSTOP_MS);
    const sc = document.createElement("script");
    sc.src = tag.src;
    if (tag.nonce) sc.nonce = tag.nonce;
    // a load that registers nothing (a script cut short, an engine too old to run it) is a failure, like an error
    sc.onload = () => { if (!engine()) fail("the math renderer loaded but registered nothing"); else void faces.then(succeed); };
    // an error while the page is leaving is the navigation's cancel, not a failed load: the backstop stays the end (latchOnLeave)
    sc.onerror = () => { if (!leaving) fail("the math renderer failed to load"); };
    (document.head || document.documentElement).appendChild(sc);
  };
  // The chunk and the two faces wait for the document's own load, an exact event: a script tag added before it joins that load,
  // so a chunk that stalled held the page's load event, on which the shell keys its pane steps (the review of iOS item 6,
  // round 1: Firefox lost that race in 4 of 6 page lives). The backstop is armed in the deferred step, so its 60 s count from
  // the request. The formulas wait in the pending dress meanwhile, as they do for the request itself.
  if (document.readyState === "complete") request();
  else window.addEventListener("load", request, { once: true });
}

/** An attempt failed (once: attempt's `fail`). Said on the console, one line per failed attempt, unless an attempt has already
 *  succeeded, which a stale failure does not contradict. The page life's first failure arms a retry, and the first failure of the
 *  load as a whole (from loading) settles it: the waiting formulas become their source, marked. A retry's failure finds nothing
 *  waiting (the fill shows the source at once while the load is failed), so it settles nothing. */
function attemptFailed(why: string): void {
  if (engineLoad === "ready") return;
  failures++;
  engineFailure = why;
  if (failures === 1 && retryable) retryArmed = true;   // the page life's first failure arms one retry
  const next = !retryable ? "" : failures === 1 ? "; the next formula asks for the renderer again" : "; a formula after the connection comes back asks for it again";
  console.error("math: " + why + "; formulas are shown as their TeX source" + next);
  if (engineLoad === "loading") engineSettled(why);
}

/** Each source fallback the load's failure made under `root` back to the placeholder it was (its tag, its mode, its TeX and its
 *  call's group), for the fill that follows a success to lay out. A fallback for one of the fill's bounds carries no mark and
 *  stays, and so does one under a root its owner repaints (MATH_REPAINT_ATTR: the viewers' bodies). */
function restoreFailedFormulas(root: ParentNode): void {
  root.querySelectorAll(FAILED_SEL).forEach((node) => {
    const shown = node as HTMLElement;
    if (shown.closest(REPAINTED_SEL)) return;              // its owner paints it again from its text (the viewers' settle handlers)
    const code = shown.tagName === "CODE" ? shown : shown.querySelector("code." + MATH_SOURCE_CLASS);
    if (!code) return;
    const ph = shown.ownerDocument.createElement(shown.tagName === "PRE" ? "div" : "span");
    ph.className = shown.getAttribute(MATH_FAILED_ATTR) === "display" ? MATH_DISPLAY_CLASS : MATH_INLINE_CLASS;
    ph.textContent = code.textContent || "";
    const call = shown.getAttribute(MATH_CALL_ATTR);
    if (call) ph.setAttribute(MATH_CALL_ATTR, call);
    shown.replaceWith(ph);
  });
}

/** The load is over, as a failure (the first of the page life's load) or a success (the first, whichever attempt it was): the
 *  handlers, then one fill over the document (each pending formula rendered, or shown as source on a failure), then what the
 *  handlers returned. A success after a failure first puts the failure's fallbacks back as placeholders (restoreFailedFormulas; not
 *  under a root its owner repaints, MATH_REPAINT_ATTR),
 *  so the fill lays out every formula, those included. The fills inside use no retry (settling, requestEngine). */
function engineSettled(failure: string | null): void {
  engineLoad = failure === null ? "ready" : "failed";
  if (failure === null) retryArmed = false;
  settling++;
  try {
    const after: Array<() => void> = [];
    for (const h of settleHandlers.slice()) {
      try { const a = h(); if (typeof a === "function") after.push(a); } catch (e) { console.error("math: a handler for the renderer's arrival threw", e); }
    }
    if (failure === null) restoreFailedFormulas(document);
    renderMathPlaceholders(document);
    for (const a of after) {
      try { a(); } catch (e) { console.error("math: a handler for the renderer's arrival threw", e); }
    }
  } finally {
    settling--;
  }
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
// otherwise be carved into a list or heading before the inline pass could see it). The block the
// tokenizer accepts is `^ {0,3}\$\$([\s\S]+?)\$\$ *(?:\n+|$)` or its `\[ .. \]` twin with non-blank
// content: an opener at a line start after up to three spaces, then the FIRST closer of the same
// family (`$$`, or `\]`, then spaces, then a line end or the end of the text) at least one character
// on, then the line's newlines. It is read in two steps below (the opener, then a search for the
// closer) rather than by that regex, so the closer search can be shared with the `start` hint and
// remembered per lexer frame: the lazy regex scanned to the end of the note at every block start
// that opened with `$$` and never closed, once per such paragraph (a note of 8,000 `$$5 and $$10`
// lines: 680 ms of lex with no hint at all, measured 2026-09-09).
const BLOCK_OPEN = /^ {0,3}(?:\$\$|\\\[)/;
const CLOSERS = [/\$\$ *(?=\n|$)/g, /\\\] *(?=\n|$)/g];   // by family: 0 for `$$`, 1 for `\[`

/** What a lexer frame remembers of the closer search, per family: true while a closer may still lie ahead, false once
 *  a search from some position found none. Sound for the rest of the frame because every later search in it starts at
 *  or after that position: within a frame the source only shrinks from the front, the hint visits candidate lines in
 *  order from the first one in its source, and a block start the tokenizer is tried at is a later candidate line
 *  (md-block-start.ts says why the frame's sources are suffixes of one another). Without a frame (a hint or tokenizer
 *  called outside a lex) the memo lives for one call. */
type ClosersLeft = [boolean, boolean];
const CLOSERS_LEFT = Symbol("mathBlock closers left");
function closersLeft(frame: Frame | undefined): ClosersLeft {
  if (!frame) return [true, true];
  let left = frame.get(CLOSERS_LEFT) as ClosersLeft | undefined;
  if (!left) { left = [true, true]; frame.set(CLOSERS_LEFT, left); }
  return left;
}
/** The first closer of `family` at or after `from`, or null when none is left, which `left` then records. */
function nextCloser(src: string, family: number, from: number, left: ClosersLeft): RegExpExecArray | null {
  if (!left[family]) return null;
  const re = CLOSERS[family];
  re.lastIndex = from;
  const m = re.exec(src);
  if (!m) left[family] = false;
  return m;
}

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

/** The display block at the start of `src`, if the block tokenizer accepts one there: either delimiter pair with
 *  non-blank content, read as the comment on BLOCK_OPEN says. `left` is the frame's closer memo (closersLeft). One
 *  reading for the tokenizer and for the `start` hint below, so the hint never names a position the tokenizer then
 *  rejects. */
function blockMath(src: string, left: ClosersLeft): { raw: string; text: string } | null {
  const o = BLOCK_OPEN.exec(src);
  if (!o) return null;
  const content = o[0].length;                                   // the content starts after the two-character opener
  const family = src.charCodeAt(content - 2) === 36 ? 0 : 1;    // "$" opens the dollar family, "\" the bracket family
  const cm = nextCloser(src, family, content + 1, left);        // at least one character of content before the closer
  if (!cm) return null;
  const text = src.slice(content, cm.index).trim();
  if (!text) return null;
  let end = cm.index + cm[0].length;                            // the closer and its trailing spaces, then the newlines
  while (src.charCodeAt(end) === 10) end++;
  return { raw: src.slice(0, end), text };
}
/** Where the next line begins that the block tokenizer (blockMath) would accept: the index of the "\n" before it, or
 *  -1. A candidate line is one that opens with `$$` or `\[` after up to three spaces; the tokenizer accepts it when the
 *  first closer of the same family after the opener has content before it that is not blank. So each candidate is
 *  judged against the first closer after its opener, which is searched for once per family and reused while it still
 *  lies past the opener at hand (the closers are in order: a later opener's first closer is the same one or a later
 *  one), and a family with no closer left rejects every later candidate without a search; once both families are out
 *  of closers the answer is none. `left` carries that "no closer left" across the frame's calls. Before any regex runs,
 *  indexOf asks whether either opener occurs at all and where the first one is: most paragraphs are followed by no
 *  opener, and indexOf is the cheapest scan there is, where a regex alternation over the same text cost ten times as
 *  much (the review's measurements are in md-block-start.ts). One pass over `src` per call at most, and with the
 *  frame's memo (mathBlock.start below) one pass per accepted block per frame. */
const NEXT_BLOCK_LINE = /\n(?= {0,3}(?:\$\$|\\\[))/g;
function nextBlockMath(src: string, left: ClosersLeft): number {
  const d = left[0] ? src.indexOf("$$") : -1;                   // a family out of closers has no candidate worth a look
  const b = left[1] ? src.indexOf("\\[") : -1;
  if (d < 0 && b < 0) return -1;
  const first = d < 0 ? b : b < 0 ? d : Math.min(d, b);
  NEXT_BLOCK_LINE.lastIndex = first > 4 ? first - 4 : 0;        // a candidate's "\n" is at most four characters before its opener
  const closer = [d < 0 ? -1 : -2, b < 0 ? -1 : -2];            // per family: the first closer found so far; -1 once none is left, -2 before any search
  for (let m = NEXT_BLOCK_LINE.exec(src); m; m = NEXT_BLOCK_LINE.exec(src)) {
    let open = m.index + 1;
    while (src.charCodeAt(open) === 32) open++;
    const family = src.charCodeAt(open) === 36 ? 0 : 1;
    const content = open + 2;
    let c = closer[family];
    if (c !== -1 && c < content + 1) {                          // the memo lies before this opener's content: search again
      const cm = nextCloser(src, family, content + 1, left);
      c = closer[family] = cm ? cm.index : -1;
    }
    if (c === -1) { if (closer[1 - family] === -1) return -1; continue; }
    if (src.slice(content, c).trim()) return m.index;
  }
  return -1;
}

export const mathBlock: TokenizerAndRendererExtension = {
  name: "mathBlock",
  level: "block",
  // marked's block lexer calls `start` on the source less its first character and clips the paragraph it is about to
  // read at the index returned plus one, so the extension is tried there next; the paragraph then RESUMES if the
  // tokenizer says no. Two things follow. The hint must name only a position where the tokenizer WILL match: on a
  // rejected line (`$$x$$ is inline here.`, `$$ not closed`, an escaped `\[TODO\]`, a blank `$$ $$`) the lexer
  // appends the line's "\n" to the clipped paragraph and, when the paragraph resumes, merges the rest with another
  // "\n" (marked 12's blockTokens never clears lastParagraphClipped), so the token's raw held one newline the source
  // did not, and the anchor map, which tiles the raws over the note, refused every block from that paragraph to the
  // end of the note and seated the reader's place wrong (the Slice 4 review, round 1). And the string's own start is
  // never a line start (it is one character into a line), so a match there made `A $$x$$` a paragraph "A" and a
  // display block " $$x$$": only a position after "\n" counts. md-config-math-block-start.test.ts executes both.
  // The lexer calls the hint before EVERY paragraph, on the whole remaining source, so the hint is memoised per lexer
  // frame (md-block-start.ts): nextBlockMath returns the first accepted line, and that answer holds for every later
  // paragraph of the frame until the line is consumed. md-config-block-start-memo.test.ts holds the memoised lex
  // equal to the plain one and the lex linear in the paragraph count (round 2 of the review: 8,000 one-line
  // paragraphs lexed in 1.3 s, a 200 KB reply took twice the base's time, from the hints alone).
  start: memoBlockStart((src, frame) => nextBlockMath(src, closersLeft(frame))),
  tokenizer(this: { lexer?: unknown } | undefined, src: string) {
    const m = blockMath(src, closersLeft(frameOf(this && this.lexer)));
    if (!m) return undefined;
    return { type: "mathBlock", raw: m.raw, text: m.text, display: true } as MathToken;
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
 *  highlighter's exemption, whichever shape it takes; the title sits on the outer element, the whole of what is shown. A
 *  fallback the load's failure made (`failedCall`, its call's group) is marked on the outer element with the formula's mode
 *  and that group (MATH_FAILED_ATTR, MATH_CALL_ATTR), so a later success can lay it out; a bound's fallback is not. */
function showSource(el: HTMLElement, tex: string, why: string, failedCall?: string): void {
  const doc = el.ownerDocument;
  const code = doc.createElement("code");
  code.className = MATH_SOURCE_CLASS;
  code.textContent = tex;
  let shown: HTMLElement = code;
  if (el.tagName === "DIV") { shown = doc.createElement("pre"); shown.appendChild(code); }
  shown.setAttribute("title", why);
  if (failedCall !== undefined) {
    shown.setAttribute(MATH_FAILED_ATTR, el.classList.contains(MATH_DISPLAY_CLASS) ? "display" : "inline");
    shown.setAttribute(MATH_CALL_ATTR, failedCall);
  }
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
 *  item 7): it renders under the same options, so it gains nothing, and in a bundle that carries the
 *  grammar such a paragraph's rendered text no longer equals its source and the anchor map refuses it
 *  with the Raw view offered, as it refuses a paragraph with `$x^2$` there today (Slice 5's math holes
 *  are where math meets the map); a bundle without the grammar has no fill and maps it as main did.
 *  Four bounds stand ahead of the one katex.render
 *  call, each shown as the source with its reason (showSource): a formula longer than MATH_TEX_MAX_CHARS;
 *  a formula that would take the call's rendered total past MATH_TEX_BUDGET_CHARS (the running total is
 *  this call's, so it is one message's or one note's, and a formula that waited for the engine is charged to
 *  the call that first met it, its MATH_CALL_ATTR group; a shorter formula after it still renders while it
 *  fits); a formula whose macro definitions repeat an argument; a formula that defines a body with `\edef`
 *  or `\xdef`, which KaTeX stores expanded (macroBounds; the two cases no expansion count over the bodies
 *  as written can bound). The call itself runs under maxSize and a maxExpand computed from the formula's
 *  macro bodies (maxExpandFor), so KaTeX's own bounds hold too, and it runs with throwOnError: true so the
 *  catch can read what stopped it: KaTeX's expansion stop (a ParseError saying "Too many expansions") is
 *  the fifth bound and wears the same fallback, the source with the reason and the count in its title
 *  (review round 5: KaTeX's red error text stood there before, and this is the one bound an ordinary
 *  formula can meet, since the count over-approximates); any other ParseError, a syntax error, is rendered
 *  again with throwOnError: false, KaTeX's own flagged text (span.katex-error, the TeX in the theme's error
 *  ink, MATH_ERROR_COLOR) as on main; a residual throw (an internal error)
 *  takes the belt, the source the same way and a word on the console once per call, so a formula can never
 *  blank a message. Until the load has settled as a success, a formula that passes the four bounds is left as
 *  its placeholder, stamped with this call's group, and the chunk is asked for (requestEngine); the fill over
 *  the document at the engine's arrival renders it, and after a failed load the fill shows it as source at once
 *  with the failure in its title, marked with its group so a later success lays it out (showSource), and uses
 *  an armed retry (requestEngine). With the
 *  engine loaded, a second run over the same root is a no-op: no placeholder survives the first. Plain and
 *  exported: md-config.ts registers it as sanitizeMd's post-pass, the arrival runs it over the document, and
 *  the tests call it directly. */
export function renderMathPlaceholders(root: ParentNode): void {
  // KaTeX only once the load has settled as a success: while the chunk or the faces are out, or after a failure, an engine the
  // chunk has registered is not used (a formula would skip the face wait and the viewer's hold, or render beside the failure's
  // fallbacks); idle with an engine is a bundle that imported the chunk for its side effect, which renders at once
  const katex = engineLoad === "loading" || engineLoad === "failed" ? null : engine();
  const meters = new Map<string, number>();   // characters of TeX handed to KaTeX so far, per call group: the budget's meters
  let group = "";            // this call's own group number, minted when its first formula waits for the engine
  let reported = false;      // the belt's console report, once per call
  root.querySelectorAll(PLACEHOLDER_SEL).forEach((node) => {
    const el = node as HTMLElement;
    const display = el.classList.contains(MATH_DISPLAY_CLASS);
    const tex = el.textContent || "";
    if (!tex.trim()) { el.replaceWith(...Array.from(el.childNodes)); return; }
    if (tex.length > MATH_TEX_MAX_CHARS) {
      showSource(el, tex, "Not rendered: " + tex.length + " characters of TeX; the limit is " + MATH_TEX_MAX_CHARS + ".");
      return;
    }
    const call = el.getAttribute(MATH_CALL_ATTR) || "";   // the call that first met this formula; "" for this one
    let rendered = meters.get(call) || 0;                 // that call's meter: one message's or one note's total
    if (rendered + tex.length > MATH_TEX_BUDGET_CHARS) {
      showSource(el, tex, "Not rendered: the formulas above already total " + rendered + " characters of TeX; the limit for one message or note is " + MATH_TEX_BUDGET_CHARS + ".");
      return;
    }
    const bounds = macroBounds(tex);          // one scan of the TeX serves the two refusals below and the count
    if (bounds.argRepeat) {
      showSource(el, tex, "Not rendered: a macro in this formula repeats one of its arguments, which can multiply the formula without bound.");
      return;
    }
    if (bounds.expandedBody) {
      showSource(el, tex, "Not rendered: a macro in this formula is defined with \\edef or \\xdef, whose stored body is its expansion; its uses can multiply the formula without bound.");
      return;
    }
    rendered += tex.length;
    meters.set(call, rendered);
    if (!katex) {
      if (engineLoad === "failed") {
        // the failure's fallback, at once (nothing waits on a retry), marked so a later success lays it out; an armed retry is
        // used here, by a fill that meets a formula outside the settle (requestEngine)
        showSource(el, tex, "Not rendered: " + engineFailure + ".", call || group || (group = String(++mathCalls)));
        requestEngine();
        return;
      }
      if (!call) el.setAttribute(MATH_CALL_ATTR, group || (group = String(++mathCalls)));
      requestEngine();
      return;
    }
    const maxExpand = maxExpandFor(tex, bounds);
    try {
      try {
        katex.render(tex, el, { ...KATEX_OPTIONS, displayMode: display, throwOnError: true, maxExpand });
      } catch (e) {
        if (!(e instanceof katex.ParseError)) throw e;
        if (/Too many expansions/.test(e.message)) {
          showSource(el, tex, "Not rendered: too many macro expansions; the limit for this formula is " + maxExpand + ", set by the longest macro body it defines.");
          return;
        }
        katex.render(tex, el, { ...KATEX_OPTIONS, displayMode: display, throwOnError: false, maxExpand });
      }
      el.replaceWith(...Array.from(el.childNodes));
    } catch (e) {
      if (!reported) { reported = true; console.error("math: KaTeX could not lay out a formula; its source is shown instead", e); }
      showSource(el, tex, "Not rendered: this formula could not be laid out.");
    }
  });
}
